"""Check SID Song Crafter's local prerequisites without installing or changing them."""

import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VICE_DATA = Path('/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice')
REMEDY = 'python3 scripts/setup-project.py'
REPAIRS = {
    'py65': 'Verify/download the pinned wheel as in docs/songs/first-song.md, then run: uv --cache-dir .local/uv-cache pip install --no-deps --target .tools/test-deps .local/downloads/py65-1.2.0-py2.py3-none-any.whl',
    'renderer': 'Build/rebuild render-sid and its pinned library as in docs/workflows/audio-workflow.md',
    'vice': 'Build genuine headless VICE as in docs/setup/vice-startup-investigation.md, or select that build with --vice / VICE_BINARY',
    'vice-roms': 'Select the VICE resource directory containing C64 ROMs with --vice-data / VICE_DIRECTORY; see docs/setup/local-setup.md',
    'mido': 'Install the optional pinned MIDI dependencies as in docs/songs/fuer-elise-score.md',
    'bridge': 'Install optional c64bridge/Bun dependencies as in docs/setup/local-setup.md',
}


def _check(name, required, ok, detail, path=None):
    result = dict(name=name, required=required, ok=ok, detail=detail)
    if path is not None:
        result['path'] = str(path)
    return result


def _executable_error(path):
    if not path.is_file():
        return 'Executable is missing'
    if not os.access(path, os.X_OK):
        return 'File is not executable'
    return None


def _probe(command, env, timeout):
    try:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env, timeout=timeout, check=False)
        return result.returncode, (result.stdout + result.stderr).strip(), None
    except subprocess.TimeoutExpired:
        return None, '', f'Probe timed out after {timeout:g} seconds'
    except OSError as error:
        return None, '', str(error)


def _dependency(root, name, modules, required, env, timeout):
    dependency_env = env.copy()
    paths = [str(root / '.tools/test-deps'), str(root / '.tools/arrangement-deps')]
    if dependency_env.get('PYTHONPATH'):
        paths.append(dependency_env['PYTHONPATH'])
    dependency_env['PYTHONPATH'] = os.pathsep.join(paths)
    code = 'import importlib, sys; modules = [importlib.import_module(name) for name in sys.argv[1:]]; print(modules[0].__file__)'
    status, output, error = _probe([sys.executable, '-c', code, *modules], dependency_env, timeout)
    ok = status == 0
    return _check(name, required, ok, output if ok else error or output[-400:] or f'Import failed with exit status {status}')


def _renderer(path, env, timeout):
    error = _executable_error(path)
    if error:
        return _check('renderer', True, False, error, path)
    status, output, error = _probe([str(path)], env, timeout)
    ok = status == 1 and 'Usage: render-sid INPUT.sid OUTPUT.wav SECONDS' in output
    return _check('renderer', True, ok, 'Renderer usage probe passed' if ok else error or output[-400:] or f'Unexpected exit status {status}', path)


def _vice_roms(path):
    missing = []
    for prefix, size in (('basic', 8192), ('kernal', 8192), ('chargen', 4096)):
        try:
            found = any(candidate.is_file() and candidate.stat().st_size == size for candidate in (path / 'C64').glob(prefix + '*'))
        except OSError:
            found = False
        if not found:
            missing.append(f'{prefix} ({size} bytes)')
    return _check('vice-roms', True, not missing, 'C64 BASIC, KERNAL and character ROMs found' if not missing else 'Missing or incomplete C64 ROMs: ' + ', '.join(missing), path)


def _contains_headless_banner(path):
    markers = (b'initialising headless ui', b'initializing headless ui')
    tail = b''
    with path.open('rb') as executable:
        for block in iter(lambda: executable.read(65536), b''):
            text = (tail + block).lower()
            if any(marker in text for marker in markers):
                return True
            tail = text[-max(map(len, markers)):]
    return False


def _vice(path, data, env, timeout):
    error = _executable_error(path)
    if error:
        return _check('vice', True, False, error, path)
    config = path.parent / 'config.h'
    if config.is_file():
        try:
            text = config.read_text()
        except OSError as error:
            return _check('vice', True, False, f'Cannot read build configuration: {error}', path)
        if re.search(r'^\s*#\s*define\s+USE_(?:GTK3UI|SDL2UI|SDLUI)\b', text, re.MULTILINE):
            return _check('vice', True, False, 'GUI VICE build; install the documented headless UI build', path)
        if re.search(r'^\s*#\s*define\s+USE_HEADLESSUI\b', text, re.MULTILINE):
            # VICE 3.9's -version can fail before archdep_init; docs/setup/vice-startup-investigation.md owns the reproduced constraint.
            return _check('vice', True, True, f'Headless UI confirmed by {config}; emulator startup was not run', path)
    try:
        # VICE 3.9 src/arch/headless/ui.c owns this banner; -help can initialize a GUI, so establish the headless implementation before invoking it.
        if not _contains_headless_banner(path):
            return _check('vice', True, False, 'Headless UI is unverified; no emulator was launched because this may be a GUI build', path)
    except OSError as error:
        return _check('vice', True, False, f'Cannot inspect executable: {error}', path)
    command = [str(path), '-config', os.devnull, '+saveres', '-logfile', os.devnull, '-directory', str(data), '-help']
    status, output, error = _probe(command, env, timeout)
    headless = 'initialising headless ui' in output.lower() or 'initializing headless ui' in output.lower()
    ok = status == 0 and headless
    detail = 'Headless UI confirmed by bounded help probe' if ok else error or ('Help probe failed: ' + output[-400:] if status != 0 else 'Help output does not establish a headless UI; GUI builds are unsupported')
    return _check('vice', True, ok, detail, path)


def _assets(root):
    installer = root / 'scripts/setup-project.py'
    if not installer.is_file():
        return [_check('assets', True, False, 'Asset checker is missing', installer)]
    bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location('sid_project_setup_doctor', installer)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.check_assets(root)
    except (OSError, ValueError, KeyError, ImportError) as error:
        return [_check('assets', True, False, f'Cannot check pinned assets: {error}', installer)]
    finally:
        sys.dont_write_bytecode = bytecode


def check_project(root=ROOT, *, vice=None, vice_data=None, renderer=None, timeout=5.0, asset_checks=None):
    """Return required/optional readiness checks using bounded, read-only probes.

    Explicit paths take precedence over VICE_BINARY, VICE_DIRECTORY and
    SID_RENDERER. Missing optional MIDI/bridge assets do not block readiness.
    Installed references and skills are checked by the installer's read-only
    check_assets helper unless the caller supplies those checks explicitly.
    """
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 60:
        raise ValueError('Probe timeout must be greater than zero and at most 60 seconds')
    root = Path(root).resolve()
    vice = Path(vice or os.environ.get('VICE_BINARY') or root / '.tools/vice-headless-3.9/build/src/x64sc').expanduser().resolve()
    data = Path(vice_data or os.environ.get('VICE_DIRECTORY') or DEFAULT_VICE_DATA).expanduser().resolve()
    renderer = Path(renderer or os.environ.get('SID_RENDERER') or root / '.local/bin/render-sid').expanduser().resolve()
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    for key in ('DISPLAY', 'WAYLAND_DISPLAY'):
        env.pop(key, None)
    for key in ('XDG_CONFIG_HOME', 'XDG_STATE_HOME', 'XDG_CACHE_HOME'):
        env[key] = os.devnull
    checks = [
        _dependency(root, 'py65', ('py65.devices.mpu6502', 'py65.assembler'), True, env, timeout),
        _renderer(renderer, env, timeout),
        _vice(vice, data, env, timeout),
        _vice_roms(data),
    ]
    checks.extend(_assets(root) if asset_checks is None else asset_checks)
    checks.append(_dependency(root, 'mido', ('mido',), False, env, timeout))
    bridge = root / '.tools/c64bridge'
    bridge_ok = (bridge / 'src/index.ts').is_file() and (bridge / 'node_modules').is_dir() and shutil.which('bun') is not None
    checks.append(_check('bridge', False, bridge_ok, 'Bridge and Bun installed; live connectivity was not tested' if bridge_ok else 'Optional bridge/Bun dependencies are not installed; offline workflows remain available', bridge))
    checks = [dict(check) for check in checks]
    for check in checks:
        if not check['ok']:
            check['remedy'] = REPAIRS.get(check['name'], REMEDY + '; preserve and investigate any existing file whose checksum differs')
    return dict(schemaVersion=1, root=str(root), ok=all(check['ok'] for check in checks if check['required']), checks=checks, remedy=REMEDY)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--vice', type=Path, help='Headless x64sc executable; defaults to VICE_BINARY or the project build')
    parser.add_argument('--vice-data', type=Path, help='VICE resource directory; defaults to VICE_DIRECTORY or the documented desktop ROM bundle')
    parser.add_argument('--renderer', type=Path, help='render-sid executable; defaults to SID_RENDERER or .local/bin/render-sid')
    parser.add_argument('--timeout', type=float, default=5.0, help='Seconds per executable/import probe (default: 5)')
    parser.add_argument('--json', action='store_true', help='Print the complete machine-readable report')
    args = parser.parse_args(argv)
    try:
        report = check_project(args.root, vice=args.vice, vice_data=args.vice_data, renderer=args.renderer, timeout=args.timeout)
    except ValueError as error:
        parser.error(str(error))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print('SID Song Crafter: ' + ('ready' if report['ok'] else 'setup incomplete'))
        for check in report['checks']:
            status = 'OK' if check['ok'] else 'MISSING' if check['required'] else 'OPTIONAL'
            print(f'{status:8} {check["name"]}: {check["detail"]}')
            if not check['ok']:
                print(f'         Repair: {check["remedy"]}')
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
