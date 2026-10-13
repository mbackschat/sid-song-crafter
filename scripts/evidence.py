#!/usr/bin/env python3
"""Promote selected build evidence, verify its hashes, and restore original bytes."""
import argparse
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = 'evidence/manifest.json'
CHUNK_BYTES = 1024 * 1024
LFS_HEADER = b'version https://git-lfs.github.com/spec/v1'
REFERENCE_SUFFIXES = {'.sid', '.psid', '.rsid', '.wav'}
COMPRESSED_SUFFIXES = {'.gz', '.gzip', '.bz2', '.xz', '.zst', '.zip', '.7z'}


def _safe_path(relative, root, prefix):
    if not isinstance(relative, str) or '\\' in relative or '\x00' in relative:
        raise ValueError(f'Invalid repository-relative path: {relative!r}')
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in ('', '.', '..') for part in relative.split('/')) \
            or len(path.parts) < 2 or path.parts[0] != prefix:
        raise ValueError(f'Path must be repository-relative under {prefix}/: {relative}')
    current = Path(os.path.abspath(root))
    if current.is_symlink():
        raise ValueError(f'Evidence root must not be a symlink: {root}')
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f'Evidence paths must not contain a symlink: {relative}')
    return current


def validate_manifest(manifest, *, root=ROOT):
    if not isinstance(manifest, dict) or type(manifest.get('version')) is not int or manifest['version'] != 1 \
            or not isinstance(manifest.get('files'), list):
        raise ValueError('Expected evidence manifest version 1 with a files list')
    paths, destinations = set(), set()
    for entry in manifest['files']:
        if not isinstance(entry, dict):
            raise ValueError('Manifest file entry must be an object')
        for field, prefix, used in (('path', 'evidence', paths), ('originalPath', 'build', destinations)):
            relative = entry.get(field)
            _safe_path(relative, root, prefix)
            if any(suffix.lower() in REFERENCE_SUFFIXES for suffix in PurePosixPath(relative).suffixes):
                raise ValueError(f'Reference SID/WAV files are excluded from evidence: {relative}')
            if relative in used:
                raise ValueError(f'Duplicate manifest {field}: {relative}')
            used.add(relative)
        for field in ('sha256', 'originalSha256'):
            if not isinstance(entry.get(field), str) or not re.fullmatch('[a-f0-9]{64}', entry[field]):
                raise ValueError(f'Invalid manifest {field}: {entry["path"]}')
        for field in ('bytes', 'originalBytes'):
            if type(entry.get(field)) is not int or entry[field] < 0:
                raise ValueError(f'Invalid manifest {field}: {entry["path"]}')
    return manifest


def load_manifest(*, root=ROOT, manifest_path=DEFAULT_MANIFEST):
    path = _safe_path(manifest_path, root, 'evidence')
    with path.open(encoding='utf-8') as source:
        return validate_manifest(json.load(source), root=root)


def _selected(manifest, paths, root, groups=()):
    manifest = load_manifest(root=root) if manifest is None else validate_manifest(manifest, root=root)
    if paths and groups:
        raise ValueError('Select either archive paths or groups, not both')
    if groups:
        available = {entry['group'] for entry in manifest['files'] if isinstance(entry.get('group'), str)}
        if any(not isinstance(group, str) or not group or group not in available for group in groups):
            raise ValueError('Requested evidence group is not listed in the manifest')
        return [entry for entry in manifest['files'] if entry.get('group') in groups]
    selected = set(paths)
    available = {entry['path'] for entry in manifest['files']}
    if selected - available:
        raise ValueError(f'Archive paths are not listed in the manifest: {sorted(selected - available)}')
    return [entry for entry in manifest['files'] if not selected or entry['path'] in selected]


def _fingerprint(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _stream(source, target=None):
    digest, size = hashlib.sha256(), 0
    while True:
        chunk = source.read(CHUNK_BYTES)
        if not chunk:
            return digest.hexdigest(), size
        digest.update(chunk)
        size += len(chunk)
        if target is not None:
            target.write(chunk)


def _hash_file(path):
    initial = path.lstat()
    if not stat.S_ISREG(initial.st_mode):
        raise FileExistsError(f'Destination is not a regular file: {path}')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as source:
        result = _stream(source)
        if _fingerprint(initial) != _fingerprint(os.fstat(source.fileno())) \
                or _fingerprint(initial) != _fingerprint(path.lstat()):
            raise ValueError(f'File changed during verification: {path}')
        return result


def _read_verified(entry, root, target=None):
    path = _safe_path(entry['path'], root, 'evidence')
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        raise FileNotFoundError(f'Missing evidence object {entry["path"]}; run git lfs pull and check the checkout') from None
    with os.fdopen(descriptor, 'rb') as source:
        initial = os.fstat(source.fileno())
        if not stat.S_ISREG(initial.st_mode):
            raise ValueError(f'Evidence must be a regular file: {entry["path"]}')
        if source.read(256).startswith(LFS_HEADER):
            raise ValueError(f'Missing Git LFS object for {entry["path"]}; run git lfs pull')
        source.seek(0)
        if _stream(source) != (entry['sha256'], entry['bytes']):
            raise ValueError(f'Evidence stored hash/size mismatch: {entry["path"]}')
        source.seek(0)
        if path.suffix == '.gz':
            with gzip.GzipFile(mode='rb', fileobj=source) as decoded:
                original = _stream(decoded, target)
        else:
            original = _stream(source, target)
        if original != (entry['originalSha256'], entry['originalBytes']):
            raise ValueError(f'Evidence original hash/size mismatch: {entry["path"]}')
        _safe_path(entry['path'], root, 'evidence')
        if _fingerprint(initial) != _fingerprint(os.fstat(source.fileno())) \
                or _fingerprint(initial) != _fingerprint(path.lstat()):
            raise ValueError(f'Evidence changed during verification: {entry["path"]}')


def _report(entry, status):
    return dict(entry, status=status)


def verify(manifest=None, paths=(), *, root=ROOT, groups=()):
    """Verify both stored and original hashes without changing evidence or build files."""
    results = []
    for entry in _selected(manifest, paths, root, groups):
        _read_verified(entry, root)
        results.append(_report(entry, 'verified'))
    return results


def _existing_target(entry, root):
    target = _safe_path(entry['originalPath'], root, 'build')
    if _hash_file(target) != (entry['originalSha256'], entry['originalBytes']):
        raise FileExistsError(f'Existing destination differs; preserve it: {entry["originalPath"]}')
    return _report(entry, 'identical')


def _restore_entry(entry, root):
    target = _safe_path(entry['originalPath'], root, 'build')
    if os.path.lexists(target):
        _read_verified(entry, root)
        return _existing_target(entry, root)
    target.parent.mkdir(parents=True, exist_ok=True)
    _safe_path(entry['originalPath'], root, 'build')
    descriptor, name = tempfile.mkstemp(prefix='.evidence-', suffix='.tmp', dir=target.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            _read_verified(entry, root, output)
            output.flush()
            os.fsync(output.fileno())
        if _hash_file(temporary) != (entry['originalSha256'], entry['originalBytes']):
            raise ValueError(f'Restored file failed byte verification: {entry["originalPath"]}')
        _safe_path(entry['originalPath'], root, 'build')
        try:
            # link publishes verified bytes atomically without replacing a concurrent destination.
            os.link(temporary, target)
        except FileExistsError:
            return _existing_target(entry, root)
        return _report(entry, 'restored')
    finally:
        temporary.unlink()


def restore(manifest=None, paths=(), *, root=ROOT, groups=()):
    """Restore indexed originals, retaining evidence and accepting identical destinations."""
    return [_restore_entry(entry, root) for entry in _selected(manifest, paths, root, groups)]


@contextmanager
def _regular_source(path):
    initial = path.lstat()
    if not stat.S_ISREG(initial.st_mode):
        raise ValueError(f'Evidence input must be a regular file: {path}')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as source:
        if _fingerprint(initial) != _fingerprint(os.fstat(source.fileno())):
            raise ValueError(f'Input changed before reading: {path}')
        yield source, initial
        if _fingerprint(initial) != _fingerprint(os.fstat(source.fileno())) \
                or _fingerprint(initial) != _fingerprint(path.lstat()):
            raise ValueError(f'Input changed during reading: {path}')


def _manifest_snapshot(root, manifest_path):
    path = _safe_path(manifest_path, root, 'evidence')
    with _regular_source(path) as (source, initial):
        raw = source.read()
    return validate_manifest(json.loads(raw), root=root), raw, _fingerprint(initial)


def _reference_name(relative):
    if any(suffix.lower() in REFERENCE_SUFFIXES for suffix in PurePosixPath(relative).suffixes):
        raise ValueError(f'Reference SID/WAV files are excluded from evidence: {relative}')


def _source_record(relative, root):
    path = _safe_path(relative, root, 'build')
    _reference_name(relative)
    if any(suffix.lower() in COMPRESSED_SUFFIXES for suffix in PurePosixPath(relative).suffixes):
        raise ValueError(f'Promotion requires an uncompressed original source: {relative}')
    with _regular_source(path) as (source, initial):
        header = source.read(256)
        if header[:4] in (b'PSID', b'RSID') or (header[:4] in (b'RIFF', b'RIFX', b'RF64')
                                               and header[8:12] == b'WAVE'):
            raise ValueError(f'Reference SID/WAV magic is excluded from evidence: {relative}')
        if header.startswith((b'\x1f\x8b', b'BZh', b'\xfd7zXZ\x00', b'PK\x03\x04',
                              b'\x28\xb5\x2f\xfd', b'7z\xbc\xaf\x27\x1c')):
            raise ValueError(f'Promotion requires uncompressed source bytes: {relative}')
        if header.startswith(LFS_HEADER):
            raise ValueError(f'Missing Git LFS source object: {relative}')
        source.seek(0)
        digest, size = _stream(source)
    _safe_path(relative, root, 'build')
    return dict(originalSha256=digest, originalBytes=size), _fingerprint(initial)


def _promotion_plan(selection, manifest, root, manifest_path):
    if not isinstance(selection, dict) or set(selection) != {'version', 'files'} \
            or type(selection.get('version')) is not int or selection['version'] != 1 \
            or not isinstance(selection.get('files'), list) or not selection['files']:
        raise ValueError('Expected promotion selection version 1 with a nonempty files list')
    destinations = {entry['path'] for entry in manifest['files']}
    originals = {entry['originalPath'] for entry in manifest['files']}
    plan = []
    for item in selection['files']:
        if not isinstance(item, dict) or set(item) != {'source', 'path', 'group', 'reason'}:
            raise ValueError('Promotion entries require source, path, group and reason')
        source = _safe_path(item['source'], root, 'build')
        target = _safe_path(item['path'], root, 'evidence')
        _reference_name(item['source'])
        _reference_name(item['path'])
        if item['path'] == manifest_path:
            raise ValueError('The manifest cannot be a promoted archive destination')
        if item['source'] in originals or item['path'] in destinations:
            raise ValueError(f'Duplicate promotion source or archive path: {item["source"]}, {item["path"]}')
        if any(PurePosixPath(other) in PurePosixPath(item['path']).parents
               or PurePosixPath(item['path']) in PurePosixPath(other).parents for other in destinations):
            raise ValueError(f'Conflicting promotion archive destinations: {item["path"]}')
        if os.path.lexists(target):
            raise FileExistsError(f'Archive destination already exists; preserve it: {item["path"]}')
        for parent in target.parents:
            if parent == Path(os.path.abspath(root)):
                break
            if parent.exists() and not parent.is_dir():
                raise ValueError(f'Archive parent is not a directory: {parent}')
        for field in ('group', 'reason'):
            if not isinstance(item[field], str) or not item[field].strip():
                raise ValueError(f'Promotion {field} must be nonempty text')
        original, source_fingerprint = _source_record(item['source'], root)
        entry = dict(path=item['path'], originalPath=item['source'], group=item['group'],
                     reason=item['reason'], **original)
        plan.append(dict(entry=entry, sourceFingerprint=source_fingerprint))
        destinations.add(item['path'])
        originals.add(item['source'])
    return plan


@contextmanager
def _promotion_lock(root, manifest_path):
    name = hashlib.sha256(manifest_path.encode()).hexdigest()[:16]
    relative = f'build/.evidence-promotion-{name}.lock'
    path = _safe_path(relative, root, 'build')
    path.parent.mkdir(parents=True, exist_ok=True)
    _safe_path(relative, root, 'build')
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError('Promotion lock must be a regular file')
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another evidence promotion holds the manifest lock') from None
        yield
    finally:
        os.close(descriptor)


def _check_manifest(root, manifest_path, raw, initial):
    path = _safe_path(manifest_path, root, 'evidence')
    if _fingerprint(path.lstat()) != initial \
            or _hash_file(path) != (hashlib.sha256(raw).hexdigest(), len(raw)):
        raise ValueError('Manifest changed during promotion; preserve the concurrent update')


def _check_source(item, root):
    source = _safe_path(item['entry']['originalPath'], root, 'build')
    if _fingerprint(source.lstat()) != item['sourceFingerprint']:
        raise ValueError(f'Source changed during promotion: {item["entry"]["originalPath"]}')


def _stage_entry(item, root, temporary):
    entry = item['entry']
    path = _safe_path(entry['originalPath'], root, 'build')
    _check_source(item, root)
    with _regular_source(path) as (source, initial), temporary.open('xb') as output:
        if _fingerprint(initial) != item['sourceFingerprint']:
            raise ValueError(f'Source changed before copying: {entry["originalPath"]}')
        if entry['path'].endswith('.gz'):
            # Gzip's filename and clock fields must not alter an evidence object's hash.
            with gzip.GzipFile(filename='', mode='wb', fileobj=output, mtime=0) as compressed:
                original = _stream(source, compressed)
        else:
            original = _stream(source, output)
        output.flush()
        os.fsync(output.fileno())
    if original != (entry['originalSha256'], entry['originalBytes']):
        raise ValueError(f'Source changed while copying: {entry["originalPath"]}')
    _check_source(item, root)
    entry['sha256'], entry['bytes'] = _hash_file(temporary)
    staged = dict(entry, path=temporary.relative_to(Path(os.path.abspath(root))).as_posix())
    _read_verified(staged, root)


def _rollback_archives(published, root):
    for target, identity, content in reversed(published):
        try:
            relative = target.relative_to(Path(os.path.abspath(root))).as_posix()
            _safe_path(relative, root, 'evidence')
            if not os.path.lexists(target) or _fingerprint(target.lstat())[:4] != identity:
                continue
            if _hash_file(target) == content and _fingerprint(target.lstat())[:4] == identity:
                target.unlink()
        except (OSError, ValueError):
            # A moved, replaced or edited archive belongs to the concurrent writer;
            # the publication-failure tests lock preservation over aggressive cleanup.
            pass


def promote(selection, *, root=ROOT, manifest_path=DEFAULT_MANIFEST):
    """Append a fully checked explicit selection, retaining all working sources.

    Entries select one uncompressed build source, a fresh evidence path, group
    and reason. A .gz destination compresses deterministically; other paths copy
    exact bytes. Both stored/original fingerprints are verified before any
    archive is published. Existing manifest fields and entries are retained.

    Cooperating promotions use a persistent ignored build lock. Ordinary exceptions
    before manifest replacement roll back only unchanged archives created by
    this invocation. Independent writers must remain stopped: the final manifest
    check is optimistic, not a filesystem compare-and-swap. Interruptions and
    process/power loss retain published archives, possibly unindexed; hard exits
    may also retain staging files. Empty created directories are not removed.
    """
    manifest, raw, initial = _manifest_snapshot(root, manifest_path)
    plan = _promotion_plan(selection, manifest, root, manifest_path)
    manifest_target = _safe_path(manifest_path, root, 'evidence')
    with _promotion_lock(root, manifest_path):
        _check_manifest(root, manifest_path, raw, initial)
        with tempfile.TemporaryDirectory(prefix='.evidence-promote-', dir=manifest_target.parent) as folder:
            staging = Path(folder)
            published = []
            committed = False
            try:
                for index, item in enumerate(plan):
                    temporary = staging / f'{index}-{PurePosixPath(item["entry"]["path"]).name}'
                    _stage_entry(item, root, temporary)
                    item['temporary'] = temporary
                updated = deepcopy(manifest)
                updated['files'].extend(item['entry'] for item in plan)
                validate_manifest(updated, root=root)
                staged_manifest = staging / 'manifest.json'
                with staged_manifest.open('x', encoding='utf-8') as output:
                    output.write(json.dumps(updated, indent=2) + '\n')
                    output.flush()
                    os.fsync(output.fileno())
                for item in plan:
                    _check_source(item, root)
                _check_manifest(root, manifest_path, raw, initial)
                for item in plan:
                    entry = item['entry']
                    target = _safe_path(entry['path'], root, 'evidence')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    _safe_path(entry['path'], root, 'evidence')
                    identity = _fingerprint(item['temporary'].lstat())[:4]
                    # Hard links publish checked bytes without replacing a racing destination.
                    os.link(item['temporary'], target)
                    published.append((target, identity, (entry['sha256'], entry['bytes'])))
                for item in plan:
                    _check_source(item, root)
                    _read_verified(item['entry'], root)
                _check_manifest(root, manifest_path, raw, initial)
                os.replace(staged_manifest, manifest_target)
                committed = True
                return [_report(item['entry'], 'promoted') for item in plan]
            except Exception:
                if not committed:
                    _rollback_archives(published, root)
                raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', choices=('verify', 'restore', 'promote'), default='verify')
    parser.add_argument('paths', nargs='*', help='Archive paths, or one build selection JSON for promote')
    parser.add_argument('--manifest', default=DEFAULT_MANIFEST)
    parser.add_argument('--group', action='append', default=[], help='Select an indexed group for verify/restore')
    args = parser.parse_args(argv)
    try:
        if args.command == 'promote':
            if len(args.paths) != 1 or args.group:
                raise ValueError('Promotion requires one build selection JSON and no group filter')
            path = _safe_path(args.paths[0], ROOT, 'build')
            with _regular_source(path) as (source, _):
                selection = json.load(source)
            for report in promote(selection, root=ROOT, manifest_path=args.manifest):
                print(json.dumps(report, sort_keys=True), flush=True)
            return 0
        manifest = load_manifest(root=ROOT, manifest_path=args.manifest)
        for entry in _selected(manifest, args.paths, ROOT, args.group):
            if args.command == 'restore':
                report = _restore_entry(entry, ROOT)
            else:
                _read_verified(entry, ROOT)
                report = _report(entry, 'verified')
            print(json.dumps(report, sort_keys=True), flush=True)
    except (OSError, EOFError, ValueError) as error:
        print(f'evidence: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
