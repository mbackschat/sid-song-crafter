import hashlib
import json
import math
from pathlib import Path

root = Path.cwd()
folder = root / 'build/native-clock-verification-v1'
run = json.loads((folder / 'run.json').read_text())
assert run['status'] == 'completed'
rows = []
for name in ('bach-pal', 'bach-ntsc', 'dual-pal', 'dual-ntsc'):
    conversion = json.loads(Path(run['deliverables'][name + 'Conversion']).read_text())
    verification = json.loads(Path(run['deliverables'][name + 'Verification']).read_text())
    vice = json.loads(Path(run['deliverables'][name + 'Vice']).read_text())
    source = json.loads(Path(conversion['sourcePath']).read_text())
    ntsc = name.endswith('ntsc')
    oscillator = 14318181.82 / 14 if ntsc else 17734475 / 18
    cycles = 17095 if ntsc else 19656
    rate = oscillator / cycles
    errors = []
    for original, converted in zip(source['voices'], conversion['voices']):
        assert len(converted['notes']) == sum(e['midi'] is not None for e in original['events'])
        for note in converted['notes']:
            event = original['events'][note['eventIndex']]
            assert event['midi'] == note['midi']
            errors.append(abs(note['startTick'] / rate - event['startBeat'] * 60 / source['quarterBpm']))
    assert max(errors) <= 1.5 / rate
    source_seconds = source['totalBeats'] * 60 / source['quarterBpm']
    assert abs(conversion['scoreTicks'] / rate - source_seconds) <= 0.5 / rate
    expected_tail = source['tailTicks'] / ((17734475 / 18) / 19656)
    assert abs(conversion['tailTicks'] / rate - expected_tail) <= 0.5 / rate
    assert vice['frameCycles'] == cycles
    assert vice['checkpoints'][-1]['completedPlayCalls'] > conversion['stopTick']
    assert verification['schedule']['postStopGatesAndVolumeClear']
    assert verification['pcm']['clippedSamples'] == 0
    audio_hash = hashlib.sha256(Path(run['deliverables'][name + 'Audio']).read_bytes()).hexdigest()
    if name == 'bach-pal':
        assert audio_hash == '86e10f2cfe1341eb60d27f03e071dffb34181666bd605353378d5b48e0523b89'
    pitch_count = 0
    if name.startswith('dual'):
        frames = json.loads((Path(run['deliverables'][name + 'Conversion']).parent / 'native-song.frames.json').read_text())
        for voice, part in enumerate(conversion['voices']):
            offset = voice // 3 * 25 + voice % 3 * 7
            for note in part['notes']:
                state = frames[note['startTick'] + 2]
                word = state[offset] | state[offset + 1] << 8
                expected = round(440 * 2 ** ((note['midi'] - 69) / 12) * 2**24 / oscillator)
                assert abs(word - expected) <= 1
                pitch_count += 1
    rows.append(dict(target=name, notes=sum(verification['schedule']['noteCounts']), sourceSeconds=source_seconds,
                     scoreSeconds=conversion['scoreTicks'] / rate, maximumOnsetErrorSeconds=max(errors),
                     tailSeconds=conversion['tailTicks'] / rate, audioSeconds=verification['pcm']['durationSeconds'],
                     audioSha256=audio_hash, checkedFixturePitchBodies=pitch_count,
                     viceLastCall=vice['checkpoints'][-1]['completedPlayCalls'], stopCall=conversion['stopTick']))
report = {'date': '2026-10-14', 'runSha256': hashlib.sha256((folder/'run.json').read_bytes()).hexdigest(),
          'checks': rows, 'limits': 'Source beat/elapsed-time and static fixture pitch oracles plus full CPU schedules and sampled standalone VICE. Native effects advance at regional VBI rates; ADSR codes unchanged. No cross-region timbre identity, hardware test or new listening acceptance.'}
(folder/'cross-clock-check.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(rows, indent=2))
