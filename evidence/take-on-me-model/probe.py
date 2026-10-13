"""Compare unchanged Take On Me execution under two explicit SID-model assumptions."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid

SOURCE_SHA = 'c7e45037d20c3b85d18fc955a1cdfb70041f08dfc171e9b12d1c3327300101e6'
TOOLS = {
    'psid_profile.py': 'c2c696db133ed024840cfa5edbc76e3a07ef1f30345cc1820c978a51a73c816d',
    'psid_audit.py': 'eeea11cdbb5159745f36802526ee2f2986d12fe19ce47b3609fedcf15f47e1bd',
    'trace-sid-vice.py': '18a21e373d7dcd679771c256fa6d930106718246cb3e0c7647329d985eb73352',
    'sid_audit_host.py': 'ea1949d711126b5150225f0d68a3462dbbfe9fffe094e448f9b758889808b0ed',
    'verify_player.py': 'c69317c5d781c175ef0cef39a6e2713187b17e1de5b3f144ad69d49e6a271aab',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    with path.open('x') as output:
        json.dump(value, output, indent=2)
        output.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = ROOT / '.local/research/take-on-me/Take_on_Me.sid'
    data = source.read_bytes()
    assert sha(data) == SOURCE_SHA
    assert int.from_bytes(data[118:120], 'big') == 4
    for name, expected in TOOLS.items():
        assert sha((ROOT / 'scripts' / name).read_bytes()) == expected, name
    args.output.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location('take_on_me_vice', ROOT / 'scripts/trace-sid-vice.py')
    trace = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trace)
    ledgers, comparisons, selected = [], {}, []
    for model in ('MOS6581', 'MOS8580'):
        output = args.output / model
        output.mkdir()
        report, writes = audit_psid(data, 64, profile='pal-banked', subtune=1, assume_sid_model=model)
        save(output / 'audit.json', report)
        save(output / 'writes.json', writes)
        checked = trace.run_trace(source, output / 'writes.json', output / 'vice', 0, 63,
            ROOT / '.tools/vice-headless-3.9/build/src/x64sc',
            Path('/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice'),
            profile='pal-banked', subtune=1, assume_sid_model=model)
        comparisons[model] = checked['verification']
        ledgers.append(writes)
        assert (output / 'vice/payload.prg').read_bytes() == data[124:]
        selected.extend(output / name for name in ('audit.json', 'writes.json', 'vice/study.json', 'vice/trace.json', 'vice/command.json'))
    assert ledgers[0] == ledgers[1]
    assert source.read_bytes() == data
    for name, expected in TOOLS.items():
        assert sha((ROOT / 'scripts' / name).read_bytes()) == expected, name
    receipt = dict(schemaVersion=1, sourceSha256=SOURCE_SHA,
        sourceUrl='https://www.hvsc.de/download/C64Music/MUSICIANS/P/PVL/Take_on_Me.sid',
        declaredSidModel='unknown', declaredFlags=4, selectedSubtune=1, playCalls=64,
        sourceUnchanged=True, modelLedgersEqual=True, exportedPayloadsEqualOriginal=True,
        tools=TOOLS, probeSha256=sha(Path(__file__).read_bytes()), comparisons=comparisons,
        artifacts={str(path.relative_to(args.output)): dict(sha256=sha(path.read_bytes()), bytes=path.stat().st_size) for path in selected},
        limits='Two explicit model assumptions, not a recovered model declaration or acoustic comparison. CPU execution is SID-model independent; VICE verifies ordered writes and cadence only. No full-form, original-host, render, listening or independent-reconstruction claim. Original SID and exported payloads remain private.')
    save(args.output / 'receipt.json', receipt)
    print(json.dumps({key: receipt[key] for key in ('sourceUnchanged', 'modelLedgersEqual', 'comparisons')}))


if __name__ == '__main__':
    main()
