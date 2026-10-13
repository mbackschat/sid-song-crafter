#!/usr/bin/env python3
"""Verify indexed evidence and restore its original bytes under build/."""
import argparse
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


def _safe_path(relative, root, prefix):
    if not isinstance(relative, str) or '\\' in relative or '\x00' in relative:
        raise ValueError(f'Invalid repository-relative path: {relative!r}')
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in ('', '.', '..') for part in relative.split('/')) \
            or len(path.parts) < 2 or path.parts[0] != prefix:
        raise ValueError(f'Path must be repository-relative under {prefix}/: {relative}')
    current = Path(os.path.abspath(root))
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


def _selected(manifest, paths, root):
    manifest = load_manifest(root=root) if manifest is None else validate_manifest(manifest, root=root)
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


def verify(manifest=None, paths=(), *, root=ROOT):
    """Verify both stored and original hashes without changing evidence or build files."""
    results = []
    for entry in _selected(manifest, paths, root):
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


def restore(manifest=None, paths=(), *, root=ROOT):
    """Restore indexed originals, retaining evidence and accepting identical destinations."""
    return [_restore_entry(entry, root) for entry in _selected(manifest, paths, root)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', choices=('verify', 'restore'), default='verify')
    parser.add_argument('paths', nargs='*', help='Manifest archive paths; omit to select all')
    parser.add_argument('--manifest', default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(root=ROOT, manifest_path=args.manifest)
        for entry in _selected(manifest, args.paths, ROOT):
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
