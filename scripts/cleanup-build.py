#!/usr/bin/env python3
"""Plan or apply conservative build cleanup; stop writers and protect active work first."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import uuid


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_cache', ROOT / 'scripts/build-cache.py')
build_cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_cache)


def _build_path(value, root):
    path = Path(value)
    if '..' in path.parts:
        raise ValueError(f'Path traversal is not allowed: {value}')
    path = Path(os.path.abspath(path if path.is_absolute() else root / path))
    build = root / 'build'
    if path == build or not path.is_relative_to(build):
        raise ValueError(f'Choose a path below build/: {path}')
    if build.is_symlink():
        raise ValueError('build/ must not be a symlink')
    current = build
    for part in path.relative_to(build).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f'Symlink paths are not allowed: {current}')
    return path


def _identity(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def _record(path, root):
    _build_path(path, root)
    initial = path.lstat()
    if not stat.S_ISREG(initial.st_mode):
        raise ValueError(f'Expected a regular file: {path}')
    digest = hashlib.sha256()
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as source:
        if _identity(os.fstat(source.fileno())) != _identity(initial):
            raise ValueError(f'File changed before hashing: {path}')
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
        if _identity(os.fstat(source.fileno())) != _identity(initial):
            raise ValueError(f'File changed during hashing: {path}')
    _build_path(path, root)
    if _identity(path.lstat()) != _identity(initial):
        raise ValueError(f'File changed after hashing: {path}')
    return dict(path=str(path.relative_to(root)), bytes=initial.st_size,
                allocatedBytes=initial.st_blocks * 512, identity=_identity(initial), sha256=digest.hexdigest())


def _recheck(record, root):
    current = _record(root / record['path'], root)
    if current != record:
        raise ValueError(f'File changed since inventory: {record["path"]}')


def _write_json(path, value):
    with path.open('x', encoding='utf-8') as target:
        json.dump(value, target, indent=2, allow_nan=False)
        target.write('\n')
        target.flush()
        os.fsync(target.fileno())


def _journal(target, value):
    target.write(json.dumps(value, sort_keys=True) + '\n')
    target.flush()
    os.fsync(target.fileno())


def _pinned_inputs(root):
    paths, configs = set(), []
    candidates = sorted((root / 'config/listening').glob('*.json'))
    assets = root / 'config/local-assets.json'
    if assets.exists():
        candidates.append(assets)
    for path in candidates:
        raw = path.read_bytes()
        value = json.loads(raw)
        configs.append(dict(path=str(path.relative_to(root)), sha256=hashlib.sha256(raw).hexdigest()))
        values = [item for stage in value.get('stages', []) for item in stage.get('inputs', [])]
        if path == assets:
            values.extend(item.get('path') for item in value.get('references', []))
        for value in values:
            if isinstance(value, str) and value.startswith('build/'):
                paths.add(_build_path(value, root))
    return paths, configs


def _protected(path, root, protections):
    parts = path.relative_to(root / 'build').parts
    return any('listening' in part.lower() or part.startswith('cleanup-') or 'deferred' in part.lower()
               for part in parts) or any(path == item or path.is_relative_to(item) for item in protections)


def _inventory(root, output):
    rows, skipped = [], []
    build = root / 'build'
    if build.is_symlink():
        raise ValueError('build/ must not be a symlink')
    for directory, directories, files in os.walk(build, followlinks=False):
        kept = []
        for name in directories:
            path = Path(directory) / name
            if path == output:
                continue
            if path.is_symlink():
                skipped.append(str(path.relative_to(root)))
            else:
                kept.append(name)
        directories[:] = kept
        for name in files:
            path = Path(directory) / name
            if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
                skipped.append(str(path.relative_to(root)))
            else:
                rows.append(_record(path, root))
    rows.sort(key=lambda item: item['path'])
    allocated = int(subprocess.check_output(['du', '-sk', str(build)], text=True).split()[0]) * 1024 if build.exists() else 0
    usage = shutil.disk_usage(build if build.exists() else root)
    return dict(createdAt=datetime.now(timezone.utc).isoformat(), files=rows, skippedPaths=sorted(skipped),
                logicalBytes=sum(row['bytes'] for row in rows), allocatedFileBytes=sum(row['allocatedBytes'] for row in rows),
                duAllocatedBytes=allocated,
                volume=dict(totalBytes=usage.total, usedBytes=usage.used, freeBytes=usage.free),
                inventoryScope='Regular files below build/, excluding this report directory; symlinks are not followed. du includes report-directory blocks.')


def _selection(inventory, root, protections):
    copies = defaultdict(list)
    for row in inventory['files']:
        path = Path(row['path'])
        if path.suffix.lower() == '.wav' and 'cache' not in path.parts:
            copies[(row['bytes'], row['sha256'])].append(row)
    duplicates, text, existing = [], [], []
    for row in inventory['files']:
        path = root / row['path']
        if _protected(path, root, protections):
            continue
        if path.suffix.lower() == '.wav' and 'cache' in path.relative_to(root / 'build').parts:
            matches = copies.get((row['bytes'], row['sha256']), [])
            if matches:
                retained = min(matches, key=lambda item: ('listening' not in item['path'], item['path']))
                duplicates.append(dict(source=row, retained=retained,
                                       reason='Exact SHA-256 and size match with retained regular WAV outside all cache directories'))
        if path.suffix in build_cache.ELIGIBLE_SUFFIXES and row['bytes'] >= build_cache.DEFAULT_MIN_BYTES:
            if os.path.lexists(path.with_name(path.name + '.gz')):
                existing.append(row['path'])
            else:
                text.append(row)
    return dict(version=1, duplicates=duplicates, text=text, skippedExistingArchives=existing,
                protectedPaths=sorted(str(path.relative_to(root)) for path in protections),
                policy='Preserve listening directories, prior cleanup reports, deferred paths, literal configured build inputs, non-cache WAVs, unique audio and non-text exports. Other generated text >=1 MiB is losslessly compacted.')


def cleanup(output, *, apply=False, protect=(), root=ROOT):
    """Retain a fresh plan and proofs; apply only exact audio deduplication and verified text compression.

    Caller-specified protections may name future paths. Stop writers to existing
    selected files; identity and content checks detect changes but do not lock
    independent producers. Published listening audio is never a deletion target.
    """
    root = Path(os.path.abspath(root))
    output = _build_path(output, root)
    if output.exists():
        raise ValueError(f'Choose a fresh report directory: {output}')
    protections = {_build_path(value, root) for value in protect}
    pinned, configs = _pinned_inputs(root)
    protections.update(pinned)
    before = _inventory(root, output)
    selection = _selection(before, root, protections)
    output.mkdir(parents=True)
    _write_json(output / 'inventory-before.json', before)
    selection['configurationInputs'] = configs
    _write_json(output / 'selection.json', selection)
    deleted, compressed, error = [], [], None
    try:
        with (output / 'operations.jsonl').open('x', encoding='utf-8') as journal:
            if apply:
                for config in configs:
                    if hashlib.sha256((root / config['path']).read_bytes()).hexdigest() != config['sha256']:
                        raise ValueError(f'Cleanup configuration changed: {config["path"]}')
                for item in selection['duplicates']:
                    source, retained = item['source'], item['retained']
                    _recheck(source, root)
                    _recheck(retained, root)
                    proof = dict(operation='delete-duplicate', path=source['path'], sha256=source['sha256'],
                                 bytes=source['bytes'], retained=retained['path'], retainedSha256=retained['sha256'])
                    _journal(journal, dict(status='verified-before-delete', **proof))
                    for record in (source, retained):
                        path = _build_path(record['path'], root)
                        if _identity(path.lstat()) != record['identity']:
                            raise ValueError(f'File changed before deletion: {record["path"]}')
                    (root / source['path']).unlink()
                    deleted.append(source)
                    _journal(journal, dict(status='completed', **proof))
                for record in selection['text']:
                    _recheck(record, root)
                    _journal(journal, dict(status='verified-before-compression', operation='compress', **record))
                    receipts = build_cache.compact([root / record['path']], root=root)
                    if len(receipts) != 1 or receipts[0]['originalSha256'] != record['sha256']:
                        raise ValueError(f'Unexpected compression receipt: {record["path"]}')
                    compressed.append(receipts[0])
                    _journal(journal, dict(status='completed', operation='compress', **receipts[0]))
    except (OSError, ValueError) as failure:
        error = failure
    after = _inventory(root, output)
    _write_json(output / 'inventory-after.json', after)
    changed = {row['path'] for row in deleted} | {row['originalPath'] for row in compressed}
    after_by_path = {row['path']: row for row in after['files']}
    unexpectedly_changed = [row['path'] for row in before['files'] if row['path'] not in changed and
                            (row['path'] not in after_by_path or after_by_path[row['path']]['sha256'] != row['sha256'])]
    if unexpectedly_changed and error is None:
        error = ValueError('Unselected files changed during cleanup; inspect summary.json')
    summary = dict(version=1, mode='apply' if apply else 'dry-run', passed=error is None,
                   selectedDuplicateWavs=len(selection['duplicates']), selectedDuplicateBytes=sum(row['source']['bytes'] for row in selection['duplicates']),
                   selectedTextFiles=len(selection['text']), selectedTextBytes=sum(row['bytes'] for row in selection['text']),
                   deletedDuplicateWavs=len(deleted), compressedTextFiles=len(compressed),
                   controlledLogicalBytesReclaimed=sum(row['bytes'] for row in deleted) + sum(row['originalBytes'] - row['compressedBytes'] for row in compressed),
                   before={key: before[key] for key in ('logicalBytes', 'allocatedFileBytes', 'duAllocatedBytes', 'volume')},
                   after={key: after[key] for key in ('logicalBytes', 'allocatedFileBytes', 'duAllocatedBytes', 'volume')},
                   unselectedFilesUnchanged=not unexpectedly_changed, unexpectedlyChanged=unexpectedly_changed,
                   error=str(error) if error else None,
                   consequence='Removed or compacted cache outputs invalidate their stages. Restore text with build-cache.py restore or regenerate via the owning recipe. No unique audio is retired.',
                   physicalSizeNote='du and file blocks report filesystem allocation; volume free space can change independently and APFS snapshots/clones can affect actual reclamation.')
    _write_json(output / 'summary.json', summary)
    if error is not None:
        raise error
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Fresh report directory below build/ (default: timestamped cleanup directory)')
    parser.add_argument('--apply', action='store_true', help='Apply the recorded safe selection; otherwise report only')
    parser.add_argument('--protect', action='append', default=[], type=Path, help='Preserve this build file or subtree, including a future path; repeatable')
    args = parser.parse_args()
    output = args.output or ROOT / 'build' / ('cleanup-' + datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8])
    try:
        summary = cleanup(output, apply=args.apply, protect=args.protect)
    except (OSError, ValueError) as error:
        raise SystemExit(f'Build cleanup failed: {error}')
    print(json.dumps(summary, indent=2))
    print(f'Report: {output}')


if __name__ == '__main__':
    main()
