"""Verify the existing familiar Monty exports and retain their audio recipe."""

from array import array
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from audio_comparison import Pcm16, read_pcm16, measure_pcm
from psid_audit import audit_psid

BASE = ROOT / 'build/monty-elise-transfer'
RECIPE = ROOT / 'docs/research/composition/monty-elise-audio.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    path = Path(path)
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path.read_bytes()))


def save(path, value):
    with path.open('x') as target:
        json.dump(value, target, indent=2, ensure_ascii=False, allow_nan=False)
        target.write('\n')


inputs = json.loads((BASE / 'code-inputs.json').read_text())
for path, expected in inputs.items():
    assert sha((ROOT / path).read_bytes()) == expected, path
rendering = dict(executable='.local/bin/render-sid',
                 executableSha256=pin(ROOT / '.local/bin/render-sid')['sha256'],
                 source='scripts/render-sid.cpp', library='libsidplayfp 3.1.1', builder='SIDLite',
                 libraryArtifact=pin(ROOT / '.local/tools/libsidplayfp/3.1.1/lib/libsidplayfp.a'),
                 clock='PAL', chip='MOS6581', defaultSubtune=1, powerOnDelay=0,
                 sampleRate=44100, channels=1, format='PCM16', seconds=15, gain=1, normalization=False)
source = json.loads((ROOT / 'songs/fuer-elise.json').read_text())
transfer = json.loads((ROOT / 'songs/monty-elise-transfer.json').read_text())
reference = json.loads((ROOT / 'songs/monty-elise-reference.json').read_text())
assert transfer['play_calls'] == reference['play_calls'] == 630
assert transfer['ending'] == reference['ending'] == dict(start_call=502, release_calls=64, fade_step_calls=4)
measurements, roles, stopped = {}, {}, {}
raw_audio = []
for role, wav_name in (('reference', 'reference.wav'), ('candidate', 'reconstructed.wav')):
    directory = BASE / role
    wav_path = directory / wav_name
    audio = read_pcm16(wav_path)
    raw_audio.append(audio)
    assert (audio.sample_rate, audio.channels, audio.frames) == (44100, 1, 661500)
    full = measure_pcm(audio)
    tail = Pcm16(audio.sample_rate, audio.channels, audio.sample_rate,
                 audio.samples[-audio.sample_rate * audio.channels:], '')
    tail_metrics = dict(startSeconds=14, endSeconds=15, **measure_pcm(tail),
                        minimumSample=min(tail.samples), maximumSample=max(tail.samples))
    assert full['clippedSamples'] == 0 and full['acRms'] > 0
    assert tail_metrics['acRms'] == 0 and min(tail.samples) == max(tail.samples)
    measurements[role] = dict(wav=pin(wav_path), fullRender=full, lastSecond=tail_metrics,
                             health=dict(noPcmRailSamples=True, settledLastSecond=True,
                                         settledTailMeaning='Zero AC energy with constant SIDLite DC offset; no listening claim.'))
    build = json.loads((directory / 'build.json').read_text())
    audit = json.loads((directory / 'audit.json').read_text())
    vice = json.loads((directory / 'vice/study.json').read_text())
    expected = json.loads((directory / 'writes.json').read_text())
    stopped_audit, stopped_writes = audit_psid((directory / 'reconstructed.sid').read_bytes(), 632)
    projection = lambda rows: [{key: row[key] for key in ('phase', 'tick', 'address', 'value')} for row in rows]
    assert projection(stopped_writes) == projection(expected)
    assert not any(row['phase'] == 'play' and row['tick'] in (630, 631) for row in stopped_writes)
    stopped[role] = dict(declaredCalls=630, actualCalls=632, additionalStoppedCalls=[630, 631],
                         additionalSidStores=0, orderedWritesEqualFullDeclaredLedger=True,
                         sidSha256=pin(directory / 'reconstructed.sid')['sha256'], audit=stopped_audit)
    assert vice['verification']['playCalls'] == 632
    assert vice['verification']['matchedWrites'] == audit['playWriteCount']
    roles[role] = dict(path=str(wav_path.relative_to(ROOT)), sha256=audio.sha256,
                       sid=pin(directory / 'reconstructed.sid'),
                       description=('Generated plain triangle reference from the same 53 source events, calendar and native words; not an original performance.'
                                    if role == 'reference' else
                                    'Same 53 source events with native Monty records 2/6/15 on bass/harmony/melody; no drum, descent, octave or portamento pitch replacement.'),
                       buildReceipt=pin(directory / 'build.json'), cpuAudit=pin(directory / 'audit.json'),
                       orderedWrites=pin(directory / 'writes.json'), stateCheckpoints=pin(directory / 'state-checkpoints.json'),
                       generatedAssembly=pin(directory / 'player.asm'), generatedListing=pin(directory / 'player.listing'),
                       viceReceipt=pin(directory / 'vice/study.json'), viceTrace=pin(directory / 'vice/trace.json'),
                       rendererSnapshots=pin(directory / (wav_name + '.registers.tsv')),
                       verification=dict(compiledCalls=630, compiledStoresIncludingInit=audit['initWriteCount'] + audit['playWriteCount'],
                                         matchedNamedStateAndBankCheckpoints=build['stateComparison']['matchedCheckpoints'],
                                         maximumPlayCycles=audit['maximumPlayCycles'], viceCalls=632,
                                         viceMatchedPlayStores=vice['verification']['matchedWrites'],
                                         maximumCadenceErrorCycles=vice['verification']['maximumCadenceError']))

full_prefix = BASE / 'listening/plain-then-monty'
ending_prefix = BASE / 'listening/ending-plain-then-monty'
full_receipt = json.loads(Path(str(full_prefix) + '.comparison.json').read_text())
ending_receipt = json.loads(Path(str(ending_prefix) + '.comparison.json').read_text())
full_audio = read_pcm16(str(full_prefix) + '.ab.wav')
ending_audio = read_pcm16(str(ending_prefix) + '.ab.wav')
matched_copies = []
for index, role in enumerate(('reference', 'candidate')):
    row = full_receipt['inputs'][index]
    matched = read_pcm16(row['matchedCopy'])
    assert matched.samples == array('h', (round(value * row['gain']) for value in raw_audio[index].samples))
    segment = full_receipt['segments'][index * 2]
    assert full_audio.samples[segment['startFrame']:segment['endFrame']] == matched.samples
    ending_segment = ending_receipt['segments'][index * 2]
    assert ending_audio.samples[ending_segment['startFrame']:ending_segment['endFrame']] == raw_audio[index].samples[352800:617400]
    matched_copies.append(dict(**pin(Path(row['matchedCopy'])), role=role, gain=row['gain'], gainDb=row['gainDb']))
for receipt, audio in ((full_receipt, full_audio), (ending_receipt, ending_audio)):
    gap = receipt['segments'][1]
    assert not any(audio.samples[gap['startFrame']:gap['endFrame']])
comparisons = dict(
    full=dict(**pin(Path(str(full_prefix) + '.ab.wav')), seconds=30.5,
              order=['plain reference', 'Monty transfer'], method=full_receipt['method'],
              matching=full_receipt['matching'], gainDb=[row['gainDb'] for row in full_receipt['inputs']],
              gapSeconds=0.5, receipt=pin(Path(str(full_prefix) + '.comparison.json')), matchedCopies=matched_copies),
    ending=dict(**pin(Path(str(ending_prefix) + '.ab.wav')), seconds=12.5,
                order=['plain reference', 'Monty transfer'], windowSeconds=[8, 14], windowFrames=[352800, 617400],
                gainDb=[0, 0], normalization=False, gapSeconds=0.5,
                method='Unity-gain window of raw original-level renders; independent of full-file matching.',
                receipt=pin(Path(str(ending_prefix) + '.comparison.json'))))
health = dict(schemaVersion=1, checkedOn='2026-10-13',
              evidenceLevel='Measured complete PCM16 renders and verified comparison samples; no hearing claim.',
              measurementApi='scripts/audio_comparison.py:read_pcm16,measure_pcm,Pcm16',
              measurementCodeSha256=inputs['scripts/audio_comparison.py'], collector=pin(Path(__file__)),
              rendering=rendering, measurements=measurements,
              comparisonVerification=dict(fullComparison=pin(Path(str(full_prefix) + '.ab.wav')),
                                          endingComparison=pin(Path(str(ending_prefix) + '.ab.wav')),
                                          matchedCopiesEqualRoundedGainOfRawSamples=True,
                                          fullSegmentsEqualMatchedCopies=True,
                                          endingSegmentsEqualRawEightToFourteenSeconds=True,
                                          comparisonGapsContainOnlyZeroSamples=True,
                                          fullComparisonHealth=measure_pcm(full_audio),
                                          endingComparisonHealth=measure_pcm(ending_audio)),
              stoppedCallVerification=stopped, listeningReview=None)
save(BASE / 'audio-evidence.json', health)

prefix = 'build/monty-elise-reproduce-new'
commands = [
    ['python3', 'scripts/prepare-monty-elise.py', '--check'],
    ['python3', 'scripts/prepare-monty-elise.py', '--transfer-output', prefix + '/transfer.json',
     '--reference-output', prefix + '/reference.json'],
]
for role, description, wav_name in (('reference', 'reference', 'reference.wav'), ('candidate', 'transfer', 'reconstructed.wav')):
    directory = prefix + '/' + role
    commands.extend([
        ['env', 'PYTHONPATH=.tools/test-deps', 'python3', 'scripts/compose-monty.py', prefix + '/' + description + '.json', '--output', directory],
        ['env', 'PYTHONPATH=.tools/test-deps', 'python3', 'scripts/trace-sid-vice.py', directory + '/reconstructed.sid',
         '--oracle', directory + '/writes.json', '--first-call', '0', '--last-call', '631', '--timeout', '180', '--output', directory + '/vice'],
        ['.local/bin/render-sid', directory + '/reconstructed.sid', directory + '/' + wav_name, '15'],
    ])
commands.extend([
    ['python3', 'scripts/compare-audio.py', 'prepare', prefix + '/reference/reference.wav', prefix + '/candidate/reconstructed.wav',
     prefix + '/listening/plain-then-monty', '--individual-copies'],
    ['python3', 'scripts/compare-audio.py', 'window', prefix + '/reference/reference.wav', prefix + '/candidate/reconstructed.wav',
     prefix + '/listening/ending-plain-then-monty', '--start-seconds', '8', '--end-seconds', '14'],
])
tail_code = '''import json, sys
from audio_comparison import Pcm16, read_pcm16, measure_pcm
for path in sys.argv[1:]:
    audio = read_pcm16(path)
    tail = Pcm16(audio.sample_rate, audio.channels, audio.sample_rate,
                 audio.samples[-audio.sample_rate * audio.channels:], '')
    print(json.dumps({'path': path, 'windowSeconds': [audio.frames / audio.sample_rate - 1,
                                                   audio.frames / audio.sample_rate],
                      'minimumSample': min(tail.samples), 'maximumSample': max(tail.samples),
                      **measure_pcm(tail)}, indent=2))
'''
recipe = dict(schemaVersion=1, kind='monty-familiar-material-transfer-audio', checkedOn='2026-10-13',
              source=dict(score='songs/fuer-elise.json', scoreSha256=sha((ROOT / 'songs/fuer-elise.json').read_bytes()),
                          composer=source['composer'], edition=source['provenance']['edition'],
                          provenance='docs/songs/fuer-elise-score.md', excerptBeats=[0, 12],
                          retainedEvents=transfer['sourceEvidence']['retainedEvents'], totalRetainedEvents=53),
              inputs=inputs, rendering=rendering, roles=roles, comparisons=comparisons,
              execution=dict(musicCalls=502, declaredCalls=630, viceWindowInclusive=[0, 631],
                             additionalSilentCalls=[630, 631], tail=transfer['ending'],
                             compilerReproductionCheck=pin(BASE / 'compiler-reproduction-check.json'),
                             viceExecutable=pin(ROOT / '.tools/vice-headless-3.9/build/src/x64sc'),
                             viceVersion='3.9', viceDataDirectory='/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice'),
              audioHealth=pin(BASE / 'audio-evidence.json'), listeningReview=None,
              limits=['Generated same-material plain reference, not an original recording.',
                      'Source boundaries round to two-call PAL ticks; native gates release two calls before row ends, and silent rest records can shorten releases.',
                      'Native frequency words retain their base tuning; PWM and eligible vibrato are decoded timbre behavior.',
                      'Measured PCM and controlled CPU/VICE execution do not establish hearing, physical SID equivalence or musical approval.'],
              publication='All WAVs and compiled exports remain in ignored build/. Track editable inputs, code, hashes, reproduction instructions and analysis evidence.',
              reproduction=dict(workingDirectory='repository root', freshOutputRequired=True,
                                setup='docs/setup/local-setup.md', audioSetup='docs/workflows/audio-workflow.md', commands=commands,
                                healthMeasurement=dict(api='scripts/audio_comparison.py:read_pcm16,measure_pcm,Pcm16',
                                                       tailWindowSeconds=[14, 15],
                                                       settledCriterion='Last-second samples are identical and AC RMS zero; retain the DC value.',
                                                       fullInspectCommands=[['python3', 'scripts/compare-audio.py', 'inspect', prefix + '/reference/reference.wav'],
                                                                            ['python3', 'scripts/compare-audio.py', 'inspect', prefix + '/candidate/reconstructed.wav']],
                                                       tailInspectCommand=['env', 'PYTHONPATH=scripts', 'python3', '-c', tail_code,
                                                                           prefix + '/reference/reference.wav', prefix + '/candidate/reconstructed.wav'])))
save(RECIPE, recipe)
print(json.dumps(dict(recipe=pin(RECIPE), health=pin(BASE / 'audio-evidence.json'),
                      roles={role: data['verification'] for role, data in roles.items()},
                      fullGainDb=comparisons['full']['gainDb'], lastSecondSample={role: data['lastSecond']['minimumSample'] for role, data in measurements.items()}), indent=2))
