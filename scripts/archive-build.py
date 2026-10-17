"""Archive a reviewed build selection below .local/archives/ or externally, and restore exact bytes."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import uuid
import zlib


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('archive_build_cleanup', ROOT / 'scripts/cleanup-build.py')
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


def _no_symlinks(path):
    for current in (*reversed(path.parents), path):
        if current.is_symlink():
            raise ValueError(f'Symlink paths are not allowed: {current}')


def _absolute(value):
    path = Path(value).expanduser()
    if '..' in path.parts:
        raise ValueError(f'Path traversal is not allowed: {value}')
    return Path(os.path.abspath(path))


def _archive_directory(value, root):
    directory = _absolute(value)
    _no_symlinks(directory)
    local = root / '.local/archives'
    if directory.is_relative_to(root) and (directory == local or not directory.is_relative_to(local)):
        raise ValueError('Choose an archive directory below .local/archives/ or outside the checkout')
    return directory


@contextmanager
def _regular_file(path):
    _no_symlinks(path)
    initial = path.lstat()
    if not stat.S_ISREG(initial.st_mode):
        raise ValueError(f'Expected a regular file: {path}')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as source:
        identity = cleanup._identity(initial)
        if cleanup._identity(os.fstat(source.fileno())) != identity:
            raise ValueError(f'File changed before reading: {path}')
        yield source
        _no_symlinks(path)
        if cleanup._identity(os.fstat(source.fileno())) != identity or cleanup._identity(path.lstat()) != identity:
            raise ValueError(f'File changed while reading: {path}')


def _json_file(path):
    with _regular_file(_absolute(path)) as source:
        return json.load(source)


def _build_target(value, root, allow_leaf_link=False):
    path = root / value
    build = root / 'build'
    if path == build or not path.is_relative_to(build):
        raise ValueError(f'Choose a path below build/: {value}')
    _no_symlinks(path.parent)
    if not allow_leaf_link and path.is_symlink():
        raise ValueError(f'Symlink paths are not allowed: {path}')
    return path


def _entry(item, root, allow_leaf_links=False):
    if not isinstance(item, dict):
        raise ValueError('Each selection entry must be an object')
    value = item.get('path')
    if not isinstance(value, str) or '\\' in value:
        raise ValueError('Each file needs a relative build path')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or path.as_posix() != value:
        raise ValueError(f'Choose a canonical relative build path without traversal: {value}')
    _build_target(value, root, allow_leaf_links)
    if type(item.get('bytes')) is not int or item['bytes'] < 0:
        raise ValueError(f'Invalid byte count: {value}')
    if not isinstance(item.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', item['sha256']):
        raise ValueError(f'Invalid SHA-256: {value}')
    if not isinstance(item.get('reason'), str) or not item['reason'].strip():
        raise ValueError(f'Nonempty retention reason required: {value}')
    return {key: item[key] for key in ('path', 'bytes', 'sha256', 'reason')}


def _entries(value, root, allow_leaf_links=False):
    if not isinstance(value, dict) or type(value.get('version')) is not int or value['version'] != 1:
        raise ValueError('Expected a version 1 selection or manifest')
    files = value.get('files')
    if not isinstance(files, list) or not files:
        raise ValueError('files must be a nonempty list')
    result, seen, sizes = [], set(), {}
    for item in files:
        entry = _entry(item, root, allow_leaf_links)
        if entry['path'] in seen:
            raise ValueError(f'Duplicate build path: {entry["path"]}')
        seen.add(entry['path'])
        if sizes.setdefault(entry['sha256'], entry['bytes']) != entry['bytes']:
            raise ValueError('One content hash cannot have different byte counts')
        result.append(entry)
    return result


def _fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_manifest(directory, manifest):
    cleanup._write_json(directory / 'manifest.json', manifest)
    _fsync_directory(directory)


def _stream(source, target=None, limit=None):
    digest, size = hashlib.sha256(), 0
    for block in iter(lambda: source.read(1024 * 1024), b''):
        size += len(block)
        if limit is not None and size > limit:
            raise ValueError('Decoded object exceeds its declared byte count')
        digest.update(block)
        if target is not None:
            target.write(block)
    return digest.hexdigest(), size


def _object_name(digest, compression):
    suffixes = {'gzip': '.gz', 'none': '.raw'}
    if compression not in suffixes:
        raise ValueError('Unsupported archive compression')
    return 'objects/' + digest + suffixes[compression]


def _write_object(record, directory, root, compression='gzip'):
    path = cleanup._build_path(record['path'], root)
    target = directory / _object_name(record['sha256'], compression)
    with _regular_file(path) as source, target.open('xb') as output:
        if compression == 'none':
            actual = _stream(source, output, record['bytes'])
            os.fchmod(output.fileno(), 0o444)
        else:
            with gzip.GzipFile(filename='', fileobj=output, mode='wb', mtime=0) as compressed:
                actual = _stream(source, compressed, record['bytes'])
        output.flush()
        os.fsync(output.fileno())
    if actual != (record['sha256'], record['bytes']):
        raise ValueError(f'Source changed while archiving: {record["path"]}')
    cleanup._recheck(record, root)


def _read_object(entry, directory, target=None):
    compression = entry.get('compression', 'gzip')
    if entry['object'] != _object_name(entry['sha256'], compression):
        raise ValueError('Object path must match its content address and compression')
    path = directory / entry['object']
    try:
        with _regular_file(path) as raw:
            if compression == 'none':
                if stat.S_IMODE(os.fstat(raw.fileno()).st_mode) != 0o444:
                    raise ValueError(f'Raw archive object must remain read-only (0444): {path}')
                actual = _stream(raw, target, entry['bytes'])
            else:
                with gzip.GzipFile(fileobj=raw, mode='rb') as decoded:
                    actual = _stream(decoded, target, entry['bytes'])
    except (OSError, EOFError, zlib.error) as error:
        raise ValueError(f'Cannot verify archive object {path}: {error}') from error
    if actual != (entry['sha256'], entry['bytes']):
        raise ValueError(f'Archive object does not match original bytes: {path}')


def _remove_source(record, root):
    cleanup._recheck(record, root)
    path = cleanup._build_path(record['path'], root)
    if cleanup._identity(path.lstat()) != record['identity']:
        raise ValueError(f'Source changed immediately before deletion: {record["path"]}')
    path.unlink()


def _link_source(record, entry, directory, root):
    target = cleanup._build_path(record['path'], root)
    object_path = directory / entry['object']
    temporary = target.with_name('.' + target.name + '.archive-link-' + uuid.uuid4().hex)
    try:
        temporary.symlink_to(object_path)
        cleanup._recheck(record, root)
        cleanup._build_path(record['path'], root)
        if cleanup._identity(target.lstat()) != record['identity']:
            raise ValueError(f'Source changed immediately before link replacement: {record["path"]}')
        os.replace(temporary, target)
        _fsync_directory(target.parent)
    finally:
        if temporary.is_symlink() and os.readlink(temporary) == str(object_path):
            temporary.unlink()


def archive(selection, destination, *, remove=False, link=False, root=ROOT):
    """Verify the entire selection, durably retain its objects/manifest, then optionally evict sources.

    Stop independent writers first. Identity and content checks detect changes;
    they do not lock producers or provide atomic filesystem compare-and-unlink
    or compare-and-replace. Link mode retains raw 0444 objects for playback.
    """
    root = Path(root).resolve()
    if remove and link:
        raise ValueError('Link and remove modes are mutually exclusive')
    entries = _entries(selection, root)
    records = []
    for entry in entries:
        record = cleanup._record(root / entry['path'], root)
        if (record['bytes'], record['sha256']) != (entry['bytes'], entry['sha256']):
            raise ValueError(f'Selection does not match source: {entry["path"]}')
        records.append(record)
    directory = _archive_directory(destination, root)
    if os.path.lexists(directory):
        raise ValueError('Choose a fresh archive directory')
    if not directory.parent.is_dir():
        raise ValueError('The archive parent directory must already exist')
    compression = 'none' if link else 'gzip'
    manifest = dict(version=1, createdAt=datetime.now(timezone.utc).isoformat(), sourceRoot=str(root),
                    compression=compression, files=[dict(entry, object=_object_name(entry['sha256'], compression)) for entry in entries])
    report = dict(version=1, manifest=str(directory / 'manifest.json'), passed=False,
                  removeRequested=remove, selectedFiles=len(entries), selectedBytes=sum(entry['bytes'] for entry in entries),
                  manifestReady=False, objectsVerified=False, removedPaths=[], removedSourceBytes=0,
                  linkRequested=link, linkedPaths=[], linkedSourceBytes=0)
    directory.mkdir()
    failure = None
    try:
        _fsync_directory(directory.parent)
        (directory / 'objects').mkdir()
        stored = set()
        for record in records:
            if record['sha256'] not in stored:
                _write_object(record, directory, root, compression)
                stored.add(record['sha256'])
        _fsync_directory(directory / 'objects')
        _write_manifest(directory, manifest)
        report['manifestReady'] = True
        for entry in {entry['object']: entry for entry in manifest['files']}.values():
            _read_object(dict(entry, compression=compression), directory)
        report['objectsVerified'] = True
        if remove:
            for record in records:
                _remove_source(record, root)
                report['removedPaths'].append(record['path'])
                report['removedSourceBytes'] += record['bytes']
        if link:
            for record, entry in zip(records, manifest['files']):
                _link_source(record, entry, directory, root)
                report['linkedPaths'].append(record['path'])
                report['linkedSourceBytes'] += record['bytes']
        report.update(passed=True, storedObjects=len(stored), storedBytes=sum(path.stat().st_size for path in (directory / 'objects').iterdir()))
    except (OSError, ValueError) as error:
        failure = error
        report['error'] = str(error)
    try:
        cleanup._write_json(directory / 'operation.json', report)
        _fsync_directory(directory)
    except OSError as error:
        failure = failure or error
    if failure is not None:
        raise ValueError(f'Build archive failed: {failure}. Retained {directory}; inspect manifest.json and operation.json before recovery. No completed source changes were rolled back.') from failure
    return report


def _manifest(path, root):
    path = _absolute(path)
    _no_symlinks(path)
    directory = _archive_directory(path.parent, root)
    value = _json_file(path)
    compression = value.get('compression')
    if compression not in ('gzip', 'none'):
        raise ValueError('Unsupported archive compression')
    entries = _entries(value, root, allow_leaf_links=compression == 'none')
    for original, entry in zip(value['files'], entries):
        expected = _object_name(entry['sha256'], compression)
        if original.get('object') != expected:
            raise ValueError('Object path must match its content address')
        entry['object'] = expected
        entry['compression'] = compression
    return directory, entries


def _owned_link(entry, directory, root):
    path = _build_target(entry['path'], root, allow_leaf_link=entry.get('compression') == 'none')
    if not path.is_symlink():
        return None
    identity = cleanup._identity(path.lstat())
    link = os.readlink(path)
    target = path.parent / link
    if entry.get('compression') != 'none' or Path(os.path.abspath(target)) != directory / entry['object']:
        raise ValueError(f'Unrelated symlink is not an owned archive link: {path}')
    _no_symlinks(target)
    _read_object(entry, directory)
    _no_symlinks(target)
    _no_symlinks(path.parent)
    if cleanup._identity(path.lstat()) != identity or os.readlink(path) != link:
        raise ValueError(f'Archive link changed while verifying: {path}')
    return identity


def _existing(entry, root, directory=None):
    path = _build_target(entry['path'], root, allow_leaf_link=entry.get('compression') == 'none')
    if path.is_symlink():
        if directory is None:
            raise ValueError(f'Symlink paths are not allowed: {path}')
        _owned_link(entry, directory, root)
        return False
    if not os.path.lexists(path):
        return False
    actual = cleanup._record(path, root)
    if (actual['sha256'], actual['bytes']) != (entry['sha256'], entry['bytes']):
        raise ValueError(f'Restore conflict: existing file has different bytes: {entry["path"]}')
    return True


def _restore_entry(entry, directory, root):
    if _existing(entry, root, directory):
        return False
    target = _build_target(entry['path'], root, allow_leaf_link=entry.get('compression') == 'none')
    link_identity = _owned_link(entry, directory, root)
    target.parent.mkdir(parents=True, exist_ok=True)
    _build_target(entry['path'], root, allow_leaf_link=entry.get('compression') == 'none')
    temporary = target.with_name('.' + target.name + '.archive-restore-' + uuid.uuid4().hex)
    try:
        with temporary.open('xb') as output:
            _read_object(entry, directory, output)
            output.flush()
            os.fsync(output.fileno())
        _build_target(entry['path'], root, allow_leaf_link=entry.get('compression') == 'none')
        if _existing(entry, root, directory):
            return False
        if link_identity is not None:
            if _owned_link(entry, directory, root) != link_identity:
                raise ValueError(f'Archive link changed before materialization: {target}')
            os.replace(temporary, target)
        else:
            os.link(temporary, target)
        _fsync_directory(target.parent)
        return True
    finally:
        temporary.unlink(missing_ok=True)


def restore(manifest, paths=(), *, root=ROOT):
    """Preflight selected objects/conflicts, then recreate absent original build paths without overwriting."""
    root = Path(root).resolve()
    directory, entries = _manifest(manifest, root)
    requested = set(paths)
    unknown = requested - {entry['path'] for entry in entries}
    if unknown:
        raise ValueError('Unknown restore path: ' + ', '.join(sorted(unknown)))
    selected = [entry for entry in entries if not requested or entry['path'] in requested]
    for entry in selected:
        _read_object(entry, directory)
        _existing(entry, root, directory)
    result = dict(version=1, restoredPaths=[], unchangedPaths=[])
    try:
        for entry in selected:
            changed = _restore_entry(entry, directory, root)
            result['restoredPaths' if changed else 'unchangedPaths'].append(entry['path'])
    except (OSError, ValueError) as error:
        raise ValueError(f'Restore failed after {len(result["restoredPaths"])} published files: {error}. Already restored files and the archive are retained; retry after resolving the conflict.') from error
    return result


def main(argv=None, *, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    save = commands.add_parser('archive', help='Retain a reviewed selection below .local/archives/ or externally')
    save.add_argument('selection', type=Path)
    save.add_argument('--archive', required=True, type=Path)
    modes = save.add_mutually_exclusive_group()
    modes.add_argument('--remove', action='store_true', help='Remove selected originals only after durable archive verification')
    modes.add_argument('--link', action='store_true', help='Replace selected originals with playback links to read-only raw archive objects')
    recover = commands.add_parser('restore', help='Restore selected original build paths')
    recover.add_argument('manifest', type=Path)
    recover.add_argument('--path', action='append', default=[], help='Restore one exact indexed build path; repeatable; omitted restores all')
    args = parser.parse_args(argv)
    try:
        report = archive(_json_file(args.selection), args.archive, remove=args.remove, link=args.link, root=root) if args.command == 'archive' else restore(args.manifest, paths=args.path, root=root)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
