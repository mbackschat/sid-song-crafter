"""Launch the optional pinned c64bridge server from this checkout, for either agent host."""

import argparse
import json
import os
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV = {
    'C64_MODE': 'vice',
    'VICE_VISIBLE': 'false',
    'VICE_HEADLESS': '0',
    'VICE_WARP': 'false',
    'VICE_ARGS': '-pal +logcolorize',
    'VICE_MODE': 'pal',
    'VICE_PREWARM': '0',
    'DISABLE_XVFB': '1',
    'RAG_BUILD_ON_START': '0',
}


def local_path(root, value):
    path = Path(value).expanduser()
    return (path if path.is_absolute() else root / path).resolve()


def executable(path, name):
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError(f'{name} is missing or not executable: {path}')
    return str(path)


def prepare_launch(root=ROOT, environment=None):
    root = Path(root).resolve()
    env = dict(os.environ if environment is None else environment)
    bridge = root / '.tools/c64bridge'
    if not (bridge / 'src/index.ts').is_file() or not (bridge / 'node_modules').is_dir():
        raise ValueError('Prepare .tools/c64bridge at the pinned revision and run bun install --frozen-lockfile there; see docs/setup/local-setup.md')
    bun = env.get('C64BRIDGE_BUN') or shutil.which('bun', path=env.get('PATH'))
    if not bun:
        raise ValueError('Bun is missing from PATH; install Bun or set C64BRIDGE_BUN to its executable')
    bun = executable(local_path(root, bun), 'Bun')
    vice = executable(local_path(root, env.get('VICE_BINARY') or '.tools/vice-headless-3.9/build/src/x64sc'), 'VICE')
    if not env.get('VICE_DIRECTORY'):
        raise ValueError('Set VICE_DIRECTORY to the VICE resource directory containing C64 ROMs; see docs/setup/local-setup.md')
    data = local_path(root, env['VICE_DIRECTORY'])
    if not (data / 'C64').is_dir():
        raise ValueError(f'VICE_DIRECTORY has no C64 resource directory: {data}')
    for name, value in DEFAULT_ENV.items():
        env.setdefault(name, value)
    env['VICE_BINARY'], env['VICE_DIRECTORY'] = vice, str(data)
    state = root / '.local/c64bridge'
    for name, default in (('C64BRIDGE_DIAGNOSTICS_DIR', state / 'diagnostics'), ('C64_TASK_STATE_FILE', state / 'tasks.json')):
        env[name] = str(local_path(root, env.get(name) or default))
    return [bun, 'src/index.ts'], bridge, env


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Print resolved paths/settings without starting Bun or VICE or writing runtime state')
    args = parser.parse_args(argv)
    try:
        command, directory, env = prepare_launch()
        if args.check:
            names = (*DEFAULT_ENV, 'VICE_BINARY', 'VICE_DIRECTORY', 'C64BRIDGE_DIAGNOSTICS_DIR', 'C64_TASK_STATE_FILE')
            print(json.dumps(dict(command=command, cwd=str(directory), settings={name: env[name] for name in names}, connectivityTested=False), indent=2))
            return 0
        (ROOT / '.local/c64bridge').mkdir(parents=True, exist_ok=True)
        os.chdir(directory)
        os.execve(command[0], command, env)
    except (OSError, ValueError) as error:
        parser.exit(1, f'c64bridge setup incomplete: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
