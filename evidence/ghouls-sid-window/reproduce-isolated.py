"""Verify the frozen rejection using its pinned dependencies in a temporary root.

The original verifier checks dependency hashes in rejection.json. Isolating the
matching snapshots preserves that guard while current analysis tools evolve;
the source SID is copied privately only for the temporary verification.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GROUP = 'build/ghouls-sid-window'
ORIGINAL_FILES = ('rejection.json', 'reproduce-rejection.py',
                  'verify-rejection.py', 'psid_audit-before.py')


def pinned_bytes(path, expected):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f'Historical input SHA-256 differs: {path}')
    return data


def main():
    verification = json.loads((HERE / 'verification.json').read_text())
    originals = {name: pinned_bytes(HERE / name, verification['files'][f'{GROUP}/{name}']['sha256'])
                 for name in ORIGINAL_FILES}
    receipt = json.loads(originals['rejection.json'])
    snapshots = {
        'psid_profile.py': pinned_bytes(HERE / 'psid_profile-before.py', receipt['tools']['scripts/psid_profile.py']),
        'verify_player.py': pinned_bytes(HERE / 'verify_player-executed.py', receipt['tools']['scripts/verify_player.py']),
    }
    source_path = Path('.local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid')
    source = pinned_bytes(ROOT / source_path, receipt['sourceSha256'])
    dependencies = ROOT / '.tools/test-deps'
    if not (dependencies / 'py65').is_dir():
        raise ValueError('Install the documented py65 dependencies in .tools/test-deps')
    with TemporaryDirectory(prefix='ghouls-rejection-isolated-', dir=ROOT / 'build') as directory:
        isolated = Path(directory)
        scripts = isolated / 'scripts'
        scripts.mkdir()
        for name, data in snapshots.items():
            (scripts / name).write_bytes(data)
        evidence = isolated / GROUP
        evidence.mkdir(parents=True)
        for name, data in originals.items():
            (evidence / name).write_bytes(data)
        private_source = isolated / source_path
        private_source.parent.mkdir(parents=True)
        private_source.write_bytes(source)
        env = dict(os.environ, PYTHONPATH=str(dependencies), PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable, '-B', str(evidence / 'verify-rejection.py')],
                       cwd=isolated, env=env, check=True, timeout=60)
    print('Isolated historical verification passed; temporary source copy removed')


if __name__ == '__main__':
    main()
