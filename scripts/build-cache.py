#!/usr/bin/env python3
"""Losslessly compact and restore generated text evidence under build/."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MIN_BYTES = 1024 * 1024
ELIGIBLE_SUFFIXES = {'.json', '.jsonl', '.log', '.txt'}
CHUNK_BYTES = 1024 * 1024


def _checked_path(path, root):
    build = Path(os.path.abspath(root)) / 'build'
    path = Path(os.path.abspath(path))
    if not path.is_relative_to(build):
        raise ValueError(f'Path must be under repository build/: {path}')
    if build.is_symlink():
        return None
    current = build
    for part in path.relative_to(build).parts:
        current = current / part
        if current.is_symlink():
            return None
    return path


def _compact_paths(paths, root, min_bytes):
    if min_bytes < 0:
        raise ValueError('Minimum byte size must be nonnegative')
    candidates = set()
    for path in paths:
        path = _checked_path(path, root)
        if path is None:
            continue
        if path.is_dir():
            for directory, directories, files in os.walk(path, followlinks=False):
                directories[:] = [name for name in directories if not (Path(directory) / name).is_symlink()]
                candidates.update(Path(directory) / name for name in files)
        else:
            candidates.add(path)
    selected = []
    for path in sorted(candidates):
        path = _checked_path(path, root)
        if path is None or path.suffix not in ELIGIBLE_SUFFIXES:
            continue
        info = path.lstat()
        if stat.S_ISREG(info.st_mode) and info.st_size >= min_bytes:
            selected.append(path)
    return selected


def _restore_paths(paths, root):
    selected = set()
    for path in paths:
        path = _checked_path(path, root)
        if path is None:
            continue
        if path.suffix != '.gz' or path.with_suffix('').suffix not in ELIGIBLE_SUFFIXES:
            raise ValueError(f'Restore requires an explicit text-evidence .gz file: {path}')
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError(f'Restore requires a regular file: {path}')
        selected.add(path)
    return sorted(selected)


def _fingerprint(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _unchanged(path, initial):
    try:
        current = path.lstat()
    except FileNotFoundError:
        raise ValueError(f'Source changed during processing: {path}') from None
    if _fingerprint(current) != _fingerprint(initial):
        raise ValueError(f'Source changed during processing: {path}')


def _stream(source, target=None):
    digest = hashlib.sha256()
    size = 0
    while True:
        chunk = source.read(CHUNK_BYTES)
        if not chunk:
            return digest.hexdigest(), size
        digest.update(chunk)
        size += len(chunk)
        if target is not None:
            target.write(chunk)


def _hash_file(path):
    with path.open('rb') as source:
        return _stream(source)


def _verify_gzip(path, expected_hash, expected_size):
    with gzip.open(path, 'rb') as source:
        actual = _stream(source)
    if actual != (expected_hash, expected_size):
        raise ValueError(f'Compressed evidence failed byte verification: {path}')


def _receipt(original, archive, original_digest, compressed_digest, root):
    return {'originalPath': str(original.relative_to(Path(os.path.abspath(root)))),
            'compressedPath': str(archive.relative_to(Path(os.path.abspath(root)))),
            'originalSha256': original_digest[0], 'compressedSha256': compressed_digest[0],
            'originalBytes': original_digest[1], 'compressedBytes': compressed_digest[1]}


def _convert(source_path, target_path, root, *, compress):
    if os.path.lexists(target_path):
        raise FileExistsError(f'Target already exists: {target_path}')
    initial = source_path.lstat()
    if not stat.S_ISREG(initial.st_mode):
        raise ValueError(f'Source must be a regular file: {source_path}')
    descriptor = os.open(source_path, os.O_RDONLY | os.O_NOFOLLOW)
    temporary = None
    published = False
    try:
        with os.fdopen(descriptor, 'rb') as source:
            if _fingerprint(os.fstat(source.fileno())) != _fingerprint(initial):
                raise ValueError(f'Source changed during processing: {source_path}')
            temporary_fd, temporary_name = tempfile.mkstemp(prefix='.build-cache-', suffix='.tmp', dir=target_path.parent)
            temporary = Path(temporary_name)
            with os.fdopen(temporary_fd, 'wb') as target:
                if compress:
                    with gzip.GzipFile(filename='', mode='wb', compresslevel=6, mtime=0, fileobj=target) as encoded:
                        original_digest = _stream(source, encoded)
                else:
                    compressed_digest = _stream(source)
                    source.seek(0)
                    with gzip.GzipFile(mode='rb', fileobj=source) as decoded:
                        original_digest = _stream(decoded, target)
                target.flush()
                os.fsync(target.fileno())
            if compress:
                _verify_gzip(temporary, *original_digest)
                compressed_digest = _hash_file(temporary)
            elif _hash_file(temporary) != original_digest:
                raise ValueError(f'Restored evidence failed byte verification: {source_path}')
            _unchanged(source_path, initial)
            # link publishes complete bytes atomically and cannot replace an existing target.
            os.link(temporary, target_path)
            published = True
            _unchanged(source_path, initial)
            source_path.unlink()
            published = False
        original, archive = (source_path, target_path) if compress else (target_path, source_path)
        return _receipt(original, archive, original_digest, compressed_digest, root)
    finally:
        if published:
            target_path.unlink()
        if temporary is not None:
            temporary.unlink()


def compact(paths, *, min_bytes=DEFAULT_MIN_BYTES, root=ROOT):
    """Verify and compress eligible files, deleting each unchanged source after publication."""
    root = Path(root)
    return [_convert(path, path.with_name(path.name + '.gz'), root, compress=True)
            for path in _compact_paths(paths, root, min_bytes)]


def restore(paths, *, root=ROOT):
    """Validate explicit archives and restore bytes without replacing existing files."""
    root = Path(root)
    return [_convert(path, path.with_suffix(''), root, compress=False)
            for path in _restore_paths(paths, root)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest='command', required=True)
    compact_parser = subcommands.add_parser('compact', help='Compress eligible files or directory trees')
    compact_parser.add_argument('paths', nargs='+', type=Path)
    compact_parser.add_argument('--min-bytes', type=int, default=DEFAULT_MIN_BYTES)
    restore_parser = subcommands.add_parser('restore', help='Restore explicit text-evidence .gz files')
    restore_parser.add_argument('paths', nargs='+', type=Path)
    args = parser.parse_args(argv)
    try:
        compress = args.command == 'compact'
        paths = _compact_paths(args.paths, ROOT, args.min_bytes) if compress else _restore_paths(args.paths, ROOT)
        for source in paths:
            target = source.with_name(source.name + '.gz') if compress else source.with_suffix('')
            receipt = _convert(source, target, ROOT, compress=compress)
            print(json.dumps(receipt, sort_keys=True), flush=True)
    except (OSError, EOFError, ValueError) as error:
        print(f'build-cache: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
