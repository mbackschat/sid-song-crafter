"""Retain source-pinned Monty metadata around the existing 64-call audit."""

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SOURCE_SHA256 = '528a7330817e4a0a0f75a505e9fe2444e07c5072ce5383ceaa89f183f0eee3ab'
STIL_SHA256 = 'b1ef3584a5b3501e2bbd2ef056d6539a1bbee7933a7828537c3946c1b16cde43'
STIL_ENTRY = '/MUSICIANS/H/Hubbard_Rob/Monty_on_the_Run.sid'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(output):
    manifest_path = ROOT / 'config/local-assets.json'
    manifest = json.loads(manifest_path.read_text())
    source = next(item for item in manifest['references'] if item['id'] == 'monty-on-the-run')
    if source['sha256'] != SOURCE_SHA256 or digest(ROOT / source['path']) != SOURCE_SHA256:
        raise ValueError('The registry and intact Monty source must match the intake pin')
    stil_path = ROOT / '.local/downloads/HVSC-STIL.txt'
    if digest(stil_path) != STIL_SHA256:
        raise ValueError('Cached STIL differs from the inspected v85 input')
    lines = stil_path.read_bytes().splitlines(keepends=True)
    start = next(index for index, line in enumerate(lines) if line.rstrip(b'\r\n') == STIL_ENTRY.encode())
    end = next(index for index in range(start + 1, len(lines)) if lines[index].startswith(b'/'))
    entry = b''.join(lines[start:end])
    header = json.loads((output / 'header.json').read_text())
    audit = json.loads((output / 'audit.json').read_text())
    writes = json.loads((output / 'audit.writes.json').read_text())
    if header['sha256'] != SOURCE_SHA256 or audit['sourceSha256'] != SOURCE_SHA256:
        raise ValueError('Existing receipts must refer to the intact pinned source')
    if (audit['executionProfile'], audit['selectedSubtune'], audit['playCalls']) != ('pal-banked', 1, 64):
        raise ValueError('This receipt owns only explicit subtune 1, calls 0..63')
    init = [row for row in writes if row['phase'] == 'init']
    play = [row for row in writes if row['phase'] == 'play']
    if len(init) != audit['initWriteCount'] or len(play) != audit['playWriteCount']:
        raise ValueError('Ledger lengths disagree with the audit report')
    if {row['tick'] for row in play} != set(range(64)):
        raise ValueError('The ordered ledger must cover each bounded play call')
    tree_path = ROOT / '.local/downloads/c64-sid-players-tree.json'
    tree = json.loads(tree_path.read_text())
    listing_path = 'Hubbard_Rob/Hubbard_Rob_Monty_on_the_Run.asm'
    listing = next(item for item in tree['tree'] if item['path'] == listing_path)
    tools = ('scripts/sid_intake.py', 'scripts/psid_profile.py', 'scripts/psid_audit.py', 'scripts/verify_player.py')
    if header['inspectorSha256'] != digest(ROOT / tools[0]) or header['profileSha256'] != digest(ROOT / tools[1]):
        raise ValueError('Inspector/profile files changed after the header receipt')
    report = dict(schemaVersion=1,
        scope='Intact archive metadata and RAM-only controlled-host calls 0..63 of subtune 1',
        source={**source, 'bytes': (ROOT / source['path']).stat().st_size},
        registry=dict(path='config/local-assets.json', sha256=digest(manifest_path)),
        stil=dict(path=str(stil_path.relative_to(ROOT)), sha256=STIL_SHA256,
            version='STIL v85, June 28, 2026', entryPath=STIL_ENTRY,
            firstLine=start + 1, lastLine=end, entrySha256=hashlib.sha256(entry).hexdigest(),
            entryHashRecipe='SHA-256 of original CRLF bytes from the path line through the blank lines before the next path',
            subtuneAnnotations=[dict(subtune=1, title="The Devil's Gallop [from the Dick Barton radio show]", artist='Charles Williams',
                meaning='Inspiration/original-piece attribution; not an independent archive subtune-role label')],
            subtunesWithoutEntryAnnotations=list(range(2, 20)),
            commentSummary='STIL attributes the energetic running character and use of newly written middle-section pitch-bend code to Hubbard.'),
        sourceRoutes=dict(
            attributedReconstruction=dict(url='https://www.neperos.com/article/rxmd9gd536b13923',
                attribution='Anthony McSweeney, 1993',
                status='Already inspected in the composer study; reverse-engineered routine with sound-effects code removed, not original labeled source'),
            cachedRepositoryListing=dict(treePath=str(tree_path.relative_to(ROOT)), treeSha256=digest(tree_path),
                revision=tree['sha'], path=listing_path, gitBlobSha1=listing['sha'], declaredBytes=listing['size'],
                url=f"https://github.com/realdmx/c64_6581_sid_players/blob/{tree['sha']}/{listing_path}",
                status='Path/blob identity observed in cached tree only; listing body not present in inspected cache and not downloaded, assembled or compared')),
        tools={path: digest(ROOT / path) for path in tools},
        collector=dict(path=str(Path(__file__).resolve().relative_to(ROOT)), sha256=digest(Path(__file__))),
        environment=dict(python=sys.version, py65Version=importlib.metadata.version('py65')),
        artifacts={name: dict(sha256=digest(output / name), bytes=(output / name).stat().st_size)
            for name in ('header.json', 'audit.json', 'audit.writes.json')},
        executedSummary=dict(initCycles=audit['initCycles'], maximumPlayCycles=audit['maximumPlayCycles'],
            meanPlayCycles=audit['meanPlayCycles'], frameCycleBudget=audit['frameCycleBudget'],
            initWriteCount=len(init), playWriteCount=len(play),
            initAddressValues=[[row['address'], row['value']] for row in init],
            playCallsWithMultipleStoresToSameRegister=sum(len(rows := [row['address'] for row in play if row['tick'] == tick]) != len(set(rows)) for tick in range(64)),
            perVoicePlayStores=[sum(0xd400 + voice * 7 <= row['address'] < 0xd407 + voice * 7 for row in play) for voice in range(3)],
            globalPlayStores=sum(row['address'] >= 0xd415 for row in play)),
        limitations='No original IRQ host, actual VBI cadence, VICE comparison, sound synthesis, complete form, instrument decode, other-subtune audit or listening verdict.')
    with (output / 'provenance.json').open('x') as target:
        json.dump(report, target, indent=2)
        target.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Directory containing fresh header.json and audit.json/.writes.json; exclusively creates provenance.json')
    report = collect(parser.parse_args().output)
    print(f"Pinned Monty intake: {report['executedSummary']['playWriteCount']} play stores, 64 calls")


if __name__ == '__main__':
    main()
