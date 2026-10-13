"""Retain measured Monty title audio and exact local reproduction settings."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from audio_comparison import Pcm16, read_pcm16, measure_pcm


def fingerprint(path):
    path = path.resolve()
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT / 'build/monty-independent-full')
    parser.add_argument('--recipe', type=Path, default=ROOT / 'docs/research/composition/monty-title-audio.json')
    args = parser.parse_args()
    output = args.root
    description = ROOT / 'songs/monty-title.json'
    code_paths = ['scripts/render-sid.cpp', 'scripts/audio_comparison.py', 'scripts/compare-audio.py',
                  'scripts/compose-monty.py', 'scripts/prepare-monty-title-ending.py',
                  'scripts/monty_title_player.py', 'scripts/monty_title_programs.py', 'scripts/monty_title_score.py',
                  'songs/players/monty.asm', 'songs/players/monty-effects.asm']
    roles = {}
    for role, relative, sid in [('reference', 'reference/reference.wav', ROOT / '.local/monty-source.sid'),
                                ('candidate', 'candidate/reconstructed.wav', output / 'candidate/reconstructed.sid')]:
        path = output / relative
        audio = read_pcm16(path)
        assert (audio.sample_rate, audio.channels, audio.frames) == (44100, 1, 15655500)
        tail = Pcm16(audio.sample_rate, 1, 44100, audio.samples[-44100:], '')
        roles[role] = dict(**fingerprint(path), sid=fingerprint(sid), full=measure_pcm(audio),
                           lastOneSecond=dict(sourceSeconds=[354, 355], **measure_pcm(tail)),
                           registerSnapshots=fingerprint(Path(str(path) + '.registers.tsv')))
        assert roles[role]['full']['clippedSamples'] == 0
    assert roles['candidate']['lastOneSecond']['acRms'] == 0
    comparisons = {}
    for role, name in [('opening', 'opening-reference-then-ours'), ('ending', 'ending-reference-then-ours')]:
        path = output / 'listening' / (name + '.comparison.json')
        receipt = json.loads(path.read_bytes())
        comparisons[role] = dict(receipt=fingerprint(path), **receipt)
    difference = comparisons['opening']['inputs'][1]['window']['acRmsDbfs'] - comparisons['opening']['inputs'][0]['window']['acRmsDbfs']
    assert abs(difference) < 1, 'Reassess the unity-gain opening before publishing this listening package'
    renderer = dict(executable=fingerprint(ROOT / '.local/bin/render-sid'),
                    source=fingerprint(ROOT / 'scripts/render-sid.cpp'),
                    library=dict(name='libsidplayfp', version='3.1.1', builder='SIDLite',
                                 staticLibrary=fingerprint(ROOT / '.local/tools/libsidplayfp/3.1.1/lib/libsidplayfp.a')),
                    settings=dict(clock='PAL', clockForced=True, sidModel='MOS6581', defaultSubtune=1,
                                  subtuneSelection='selectSong(0) selects the header default', powerOnDelay=0,
                                  sampleRate=44100, channels=1, format='PCM16', seconds=355, frames=15655500,
                                  gain=1, normalization=False, trim=None, voiceDiagnostic=False))
    rate = Fraction(17734475, 18) / 19656
    timing = dict(callRateHz=float(rate), musicCalls=17536, totalPlayCalls=17664, deliberateTailCalls=128,
                  releaseStartsSeconds=float(17536 / rate), fadeStartsSeconds=float(17600 / rate),
                  finalZeroVolumeStartsSeconds=float(17660 / rate), declaredEndSeconds=float(17664 / rate),
                  endingDifference='The original restarts its score; the candidate freezes the score, releases actual gates and fades to zero.')
    level = dict(method='Unity gain; original PCM retained', openingCandidateMinusReferenceAcRmsDb=difference,
                 rationale='The opening AC RMS differs by less than 1 dB; retain original levels without normalization or DC removal.')
    receipt = dict(schemaVersion=1, checkedOn='2026-10-13', description=fingerprint(description),
                   collector=fingerprint(Path(__file__)), codePins={path: fingerprint(ROOT / path) for path in code_paths},
                   rendering=renderer, roles=roles, comparisons=comparisons, timing=timing, levelDecision=level,
                   listeningReview=None, limits=['Signal health and ordered writes do not prove acoustic equivalence or musical quality.',
                                                'Same elapsed windows; no PCM alignment or within-call timing equivalence.',
                                                'Reference SID, WAVs and A/B audio remain local, outside Git and LFS.'])
    receipt_path = output / 'audio-evidence.json'
    save(receipt_path, receipt)
    fresh = 'build/monty-title-reproduce'
    commands = [
        ['python3', 'scripts/setup-project.py', '--only', 'references', '--include', 'monty-on-the-run'],
        ['python3', 'scripts/prepare-monty-title-ending.py', '--check'],
        ['python3', 'scripts/compose-monty.py', 'songs/monty-title.json', '--output', fresh + '/candidate'],
        ['mkdir', '-p', fresh + '/reference'],
        ['.local/bin/render-sid', '.local/monty-source.sid', fresh + '/reference/reference.wav', '355'],
        ['.local/bin/render-sid', fresh + '/candidate/reconstructed.sid', fresh + '/candidate/reconstructed.wav', '355'],
    ]
    for label, start, stop in [('opening', '0', '24'), ('ending', '340', '355')]:
        commands.append(['python3', 'scripts/compare-audio.py', 'window', fresh + '/reference/reference.wav',
                         fresh + '/candidate/reconstructed.wav', fresh + '/listening/' + label + '-reference-then-ours',
                         '--start-seconds', start, '--end-seconds', stop, '--gap-seconds', '0.5'])
    commands.append(['python3', 'evidence/monty-independent-full/package-audio.py', '--root', fresh,
                     '--recipe', fresh + '/audio-recipe.json'])
    recipe = dict(schemaVersion=1, kind='monty-title-reconstruction-listening-package', checkedOn='2026-10-13',
                  source=dict(title='Monty on the Run', music='Rob Hubbard', assetId='monty-on-the-run',
                              url='https://www.hvsc.de/download/C64Music/MUSICIANS/H/Hubbard_Rob/Monty_on_the_Run.sid',
                              **fingerprint(ROOT / '.local/monty-source.sid')),
                  description=receipt['description'], codePins=receipt['codePins'], rendering=renderer,
                  roles=roles, comparisons=comparisons, timing=timing, levelDecision=level,
                  audioReceipt=fingerprint(receipt_path), listeningReview=None,
                  reproduction=dict(workingDirectory='repository root', freshOutputRequired=True,
                                    pinnedRendererRequired=True, setup='docs/workflows/audio-workflow.md', commands=commands,
                                    notes=['Wait for each renderer to finish before reading its WAV.',
                                           'PCM hashes reproduce with the pinned renderer; path-specific JSON receipts change in fresh directories.']),
                  publication='Original SID, reference WAV and reference-containing A/B WAVs stay in ignored .local/ or build/, never Git or LFS.',
                  limits=receipt['limits'])
    save(args.recipe, recipe)
    print(json.dumps(dict(receipt=str(receipt_path), recipe=str(args.recipe), openingLevelDifferenceDb=difference)))


if __name__ == '__main__':
    main()
