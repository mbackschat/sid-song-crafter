#!/usr/bin/env python3
"""Install checksum-pinned reference tunes and selected project-local skills."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def safe_path(root, relative):
    relative = PurePosixPath(relative)
    if relative.is_absolute() or '..' in relative.parts or str(relative) == '.':
        raise ValueError(f'Unsafe path: {relative}')
    target = root / relative
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Escaping path: {relative}')
    return target


def validate_manifest(manifest):
    if manifest.get('version') != 1:
        raise ValueError('Unsupported manifest version')
    ids = set()
    for kind in ('references', 'skills'):
        for item in manifest.get(kind, []):
            if item['id'] in ids:
                raise ValueError(f"Duplicate asset: {item['id']}")
            ids.add(item['id'])
            prefix = '.local/' if kind == 'references' else 'skills/'
            if not item['path'].startswith(prefix):
                raise ValueError(f'Invalid {kind} path')
            safe_path(ROOT, item['path'])
            files = [item] if kind == 'references' else item['files']
            for entry in files:
                if not re.fullmatch('[a-f0-9]{64}', entry['sha256']):
                    raise ValueError('Invalid checksum')
            if kind == 'references':
                if not item['url'].startswith('https://'):
                    raise ValueError('Reference URL must use HTTPS')
            else:
                if not re.fullmatch('[a-f0-9]{40}', item['revision']):
                    raise ValueError('Skill revision must be a full commit hash')
                if not re.fullmatch(r'https://github.com/[\w.-]+/[\w.-]+', item['repository']):
                    raise ValueError('Skill repository must be a GitHub HTTPS URL')
                if not item['activation'].startswith('.agents/skills/') or not item['checkout'].startswith('.tools/'):
                    raise ValueError('Invalid skill activation/checkout path')
                safe_path(ROOT, item['activation'])
                safe_path(ROOT, item['checkout'])
                paths = set()
                for entry in files:
                    safe_path(ROOT, entry['path'])
                    safe_path(ROOT, entry['source'])
                    if entry['path'] in paths:
                        raise ValueError('Duplicate skill file path')
                    paths.add(entry['path'])


def select_assets(manifest, only=None, include=()):
    validate_manifest(manifest)
    all_assets = [(kind, item) for kind in ('references', 'skills') for item in manifest.get(kind, [])]
    unknown = set(include) - {item['id'] for _, item in all_assets}
    if unknown:
        raise ValueError(f'Unknown assets: {", ".join(sorted(unknown))}')
    return [(kind, item) for kind, item in all_assets if (only is None or kind == only) and (item.get('default', False) or item['id'] in include)]


def verified(data, entry):
    if hashlib.sha256(data).hexdigest() != entry['sha256']:
        raise ValueError(f"checksum mismatch: {entry.get('path', entry.get('id'))}; preserve the file and investigate its source")
    return data


def download(url):
    with urlopen(url, timeout=20) as response:
        return response.read()


def install_reference(root, entry, offline=False):
    target = safe_path(root, entry['path'])
    if target.exists():
        verified(target.read_bytes(), entry)
        return
    if offline:
        raise OSError(f"Missing offline reference: {entry['id']}")
    data = verified(download(entry['url']), entry)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent) as temporary:
        temporary.write(data)
        temporary.flush()
        os.link(temporary.name, target)


def skill_source(root, skill, entry, offline=False):
    checkout = safe_path(root, skill['checkout'])
    if checkout.is_dir():
        result = subprocess.run(['git', '-C', str(checkout), 'show', f"{skill['revision']}:{entry['source']}"], capture_output=True, timeout=15)
        if result.returncode == 0:
            return result.stdout
    if offline:
        raise OSError(f"Pinned skill object unavailable offline: {skill['id']}/{entry['path']}")
    repo = skill['repository'].removeprefix('https://github.com/').removesuffix('.git')
    return download(f"https://raw.githubusercontent.com/{repo}/{skill['revision']}/{entry['source']}")


def skill_files(root, skill):
    target = safe_path(root, skill['path'])
    for entry in skill['files']:
        verified(safe_path(target, entry['path']).read_bytes(), entry)


def activation_path(root, skill):
    # Resolve the parent separately: an existing activation symlink is the object to inspect.
    return safe_path(root, str(PurePosixPath(skill['activation']).parent)) / PurePosixPath(skill['activation']).name


def install_skill(root, skill, offline=False):
    target = safe_path(root, skill['path'])
    activation = activation_path(root, skill)
    if os.path.lexists(activation) and (not activation.is_symlink() or activation.resolve() != target.resolve()):
        raise ValueError(f'Unrelated activation path: {activation}')
    if target.exists():
        skill_files(root, skill)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
            staged = Path(temporary) / 'skill'
            staged.mkdir()
            for entry in skill['files']:
                data = verified(skill_source(root, skill, entry, offline), entry)
                output = safe_path(staged, entry['path'])
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(data)
            staged.rename(target)
    if not activation.is_symlink():
        activation.parent.mkdir(parents=True, exist_ok=True)
        activation.symlink_to(os.path.relpath(target, activation.parent), target_is_directory=True)


def check_assets(root, manifest=None):
    manifest = manifest if manifest is not None else json.loads((root / 'config/local-assets.json').read_text())
    validate_manifest(manifest)
    checks = []
    for kind in ('references', 'skills'):
        for item in manifest.get(kind, []):
            try:
                target = safe_path(root, item['path'])
                if kind == 'references':
                    verified(target.read_bytes(), item)
                else:
                    skill_files(root, item)
                    activation = activation_path(root, item)
                    if not activation.is_symlink() or activation.resolve() != target.resolve():
                        raise ValueError('Missing or incorrect activation link')
                ok, detail = True, 'Pinned files verified'
            except (OSError, ValueError) as error:
                ok, detail = False, str(error)
            checks.append(dict(name=f"{'reference' if kind == 'references' else 'skill'}:{item['id']}", required=item.get('default', False), ok=ok, detail=detail, path=item['path']))
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true', help='Use existing files and pinned local Git objects only')
    parser.add_argument('--check', action='store_true', help='Verify selected assets without changing anything')
    parser.add_argument('--only', choices=('references', 'skills'))
    parser.add_argument('--include', action='append', default=[], metavar='ID', help='Also select an optional asset (repeatable)')
    args = parser.parse_args()
    try:
        manifest = json.loads((ROOT / 'config/local-assets.json').read_text())
        selected = select_assets(manifest, args.only, args.include)
        if args.check:
            names = {item['id'] for _, item in selected}
            checks = [row for row in check_assets(ROOT, manifest) if row['name'].split(':', 1)[1] in names]
            for row in checks:
                print(f"{'OK' if row['ok'] else 'FAIL'} {row['name']}: {row['detail']}")
            return int(any(not row['ok'] for row in checks))
        for kind, item in selected:
            (install_reference if kind == 'references' else install_skill)(ROOT, item, args.offline)
            print(f"OK {item['id']}: {item['path']}")
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f'Setup failed: {error}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
