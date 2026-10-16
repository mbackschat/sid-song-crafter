"""Archive an explicit reviewed build selection outside the checkout, and restore exact bytes."""

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


def _entry(item, root):
    if not isinstance(item, dict):
        raise ValueError('Each selection entry must be an object')
    value = item.get('path')
    if not isinstance(value, str) or '\\' in value:
        raise ValueError('Each file needs a relative build path')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or path.as_posix() != value:
        raise ValueError(f'Choose a canonical relative build path without traversal: {value}')
    cleanup._build_path(value, root)
    if type(item.get('bytes')) is not int or item['bytes'] < 0:
        raise ValueError(f'Invalid byte count: {value}')
    if not isinstance(item.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', item['sha256']):
        raise ValueError(f'Invalid SHA-256: {value}')
    if not isinstance(item.get('reason'), str) or not item['reason'].strip():
        raise ValueError(f'Nonempty retention reason required: {value}')
    return {key: item[key] for key in ('path', 'bytes', 'sha256', 'reason')}


def _entries(value, root):
    if not isinstance(value, dict) or type(value.get('version')) is not int or value['version'] != 1:
        raise ValueError('Expected a version 1 selection or manifest')
    files = value.get('files')
    if not isinstance(files, list) or not files:
        raise ValueError('files must be a nonempty list')
    result, seen, sizes = [], set(), {}
    for item in files:
        entry = _entry(item, root)
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


def _write_object(record, directory, root):
    path = cleanup._build_path(record['path'], root)
    target = directory / 'objects' / (record['sha256'] + '.gz')
    with _regular_file(path) as source, target.open('xb') as output:
        with gzip.GzipFile(filename='', fileobj=output, mode='wb', mtime=0) as compressed:
            actual = _stream(source, compressed, record['bytes'])
        output.flush()
        os.fsync(output.fileno())
    if actual != (record['sha256'], record['bytes']):
        raise ValueError(f'Source changed while archiving: {record["path"]}')
    cleanup._recheck(record, root)


def _read_object(entry, directory, target=None):
    path = directory / entry['object']
    try:
        with _regular_file(path) as raw, gzip.GzipFile(fileobj=raw, mode='rb') as decoded:
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


def archive(selection, destination, *, remove=False, root=ROOT):
    """Verify the entire selection, durably retain its objects/manifest, then optionally evict sources.

    Stop independent writers first. Identity and content checks detect changes;
    they do not lock producers or provide atomic filesystem compare-and-unlink.
    """
    root = Path(root).resolve()
    entries = _entries(selection, root)
    records = []
    for entry in entries:
        record = cleanup._record(root / entry['path'], root)
        if (record['bytes'], record['sha256']) != (entry['bytes'], entry['sha256']):
            raise ValueError(f'Selection does not match source: {entry["path"]}')
        records.append(record)
    directory = _absolute(destination)
    _no_symlinks(directory)
    if directory.is_relative_to(root) or os.path.lexists(directory):
        raise ValueError('Choose a fresh archive directory outside the checkout')
    if not directory.parent.is_dir():
        raise ValueError('The external archive parent directory must already exist')
    manifest = dict(version=1, createdAt=datetime.now(timezone.utc).isoformat(), sourceRoot=str(root),
                    compression='gzip', files=[dict(entry, object='objects/' + entry['sha256'] + '.gz') for entry in entries])
    report = dict(version=1, manifest=str(directory / 'manifest.json'), passed=False,
                  removeRequested=remove, selectedFiles=len(entries), selectedBytes=sum(entry['bytes'] for entry in entries),
                  manifestReady=False, objectsVerified=False, removedPaths=[], removedSourceBytes=0)
    directory.mkdir()
    failure = None
    try:
        _fsync_directory(directory.parent)
        (directory / 'objects').mkdir()
        stored = set()
        for record in records:
            if record['sha256'] not in stored:
                _write_object(record, directory, root)
                stored.add(record['sha256'])
        _fsync_directory(directory / 'objects')
        _write_manifest(directory, manifest)
        report['manifestReady'] = True
        for entry in {entry['object']: entry for entry in manifest['files']}.values():
            _read_object(entry, directory)
        report['objectsVerified'] = True
        if remove:
            for record in records:
                _remove_source(record, root)
                report['removedPaths'].append(record['path'])
                report['removedSourceBytes'] += record['bytes']
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
        raise ValueError(f'Build archive failed: {failure}. Retained {directory}; inspect manifest.json and operation.json before recovery. No completed deletions were rolled back.') from failure
    return report


def _manifest(path, root):
    path = _absolute(path)
    _no_symlinks(path)
    if path.is_relative_to(root):
        raise ValueError('Restore from an archive outside the checkout')
    value = _json_file(path)
    entries = _entries(value, root)
    if value.get('compression') != 'gzip':
        raise ValueError('Unsupported archive compression')
    for original, entry in zip(value['files'], entries):
        expected = 'objects/' + entry['sha256'] + '.gz'
        if original.get('object') != expected:
            raise ValueError('Object path must match its content address')
        entry['object'] = expected
    return path.parent, entries


def _existing(entry, root):
    path = cleanup._build_path(entry['path'], root)
    if not os.path.lexists(path):
        return False
    actual = cleanup._record(path, root)
    if (actual['sha256'], actual['bytes']) != (entry['sha256'], entry['bytes']):
        raise ValueError(f'Restore conflict: existing file has different bytes: {entry["path"]}')
    return True


def _restore_entry(entry, directory, root):
    if _existing(entry, root):
        return False
    target = cleanup._build_path(entry['path'], root)
    target.parent.mkdir(parents=True, exist_ok=True)
    cleanup._build_path(entry['path'], root)
    temporary = target.with_name('.' + target.name + '.archive-restore-' + uuid.uuid4().hex)
    try:
        with temporary.open('xb') as output:
            _read_object(entry, directory, output)
            output.flush()
            os.fsync(output.fileno())
        cleanup._build_path(entry['path'], root)
        if _existing(entry, root):
            return False
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
        _existing(entry, root)
    result = dict(version=1, restoredPaths=[], unchangedPaths=[])
    try:
        for entry in selected:
            changed = _restore_entry(entry, directory, root)
            result['restoredPaths' if changed else 'unchangedPaths'].append(entry['path'])
    except (OSError, ValueError) as error:
        raise ValueError(f'Restore failed after {len(result["restoredPaths"])} published files: {error}. Already restored files and the external archive are retained; retry after resolving the conflict.') from error
    return result


def main(argv=None, *, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    save = commands.add_parser('archive', help='Retain a reviewed selection outside the checkout')
    save.add_argument('selection', type=Path)
    save.add_argument('--archive', required=True, type=Path)
    save.add_argument('--remove', action='store_true', help='Remove selected originals only after durable archive verification')
    recover = commands.add_parser('restore', help='Restore selected original build paths')
    recover.add_argument('manifest', type=Path)
    recover.add_argument('--path', action='append', default=[], help='Restore one exact indexed build path; repeatable; omitted restores all')
    args = parser.parse_args(argv)
    try:
        report = archive(_json_file(args.selection), args.archive, remove=args.remove, root=root) if args.command == 'archive' else restore(args.manifest, paths=args.path, root=root)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
