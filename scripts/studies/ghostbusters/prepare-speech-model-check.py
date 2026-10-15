"""Prepare four anonymous speech-check clips offline; never make model requests.

The elementary Qwen prompt/settings and exact two controls stay frozen. Only
the two rendered openings are cropped/resampled. Oracle and provenance remain
local, outside cases.json and the runner's requests; rendered speech has no
transcription ground truth. Run scripts/audio_assessment.py separately when
the prepared trial is authorized, using its existing budget/cache guards.
"""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import wave


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from audio_assessment import _prepare
from audio_comparison import _pcm_bytes, _write_wav, read_pcm16

QWEN = ROOT / 'evidence/audio-assessment-controls/qwen'
CONTROLS = ROOT / 'build/audio-perception-controls-20261013/inputs-local'
GENERATOR = ROOT / 'scripts/studies/audio-assessment/prepare-controls.py'
AFCONVERT = Path('/usr/bin/afconvert')
CROP_SECONDS = 4.45
SAMPLE_RATE = 16000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fingerprint(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return dict(path=str(path), sha256=digest.hexdigest(), bytes=path.stat().st_size)


def write_json(path, value):
    with path.open('x') as target:
        target.write(json.dumps(value, indent=2, allow_nan=False) + '\n')


def speech_text():
    for statement in ast.parse(GENERATOR.read_text()).body:
        if isinstance(statement, ast.Assign) and any(isinstance(target, ast.Name)
                and target.id == 'SPEECH_TEXT' for target in statement.targets):
            value = ast.literal_eval(statement.value)
            require(isinstance(value, str) and value.strip(), 'Control speech text is invalid')
            return value
    raise ValueError('Control generator has no literal SPEECH_TEXT')


def load_protocol(controls=CONTROLS):
    manifest_path, verified_path = QWEN / 'cases.json', QWEN / 'verified-assessment.json'
    manifest, verified = json.loads(manifest_path.read_text()), json.loads(verified_path.read_text())
    require(fingerprint(manifest_path)['sha256'] == verified['manifest_sha256'], 'Frozen Qwen manifest fingerprint differs')
    require(verified['passed'] is True and manifest['model'] == verified['model'], 'Prior Qwen control verification differs')
    require(manifest['model'] == 'qwen/qwen3.8-omni-flash' and manifest['max_tokens'] == 1200
        and manifest['reasoning'] is False, 'Frozen Qwen settings differ')
    prompts = {case['prompt'] for case in manifest['cases']}
    require(len(prompts) == 1, 'Frozen controls do not use one unchanged prompt')
    records = {}
    for case_id in ('c01', 'c06'):
        matching = [case for case in verified['cases'] if case['id'] == case_id]
        require(len(matching) == 1 and matching[0]['passed'] is True, 'Prior control result is missing')
        expected, path = matching[0], Path(controls) / (case_id + '.wav')
        record = fingerprint(path)
        require(record['sha256'] == expected['audio_sha256'] == expected['expected']['audio_sha256'],
            f'Exact retained control fingerprint differs: {case_id}')
        audio = read_pcm16(path)
        require(audio.sample_rate == SAMPLE_RATE and audio.channels == 1, 'Retained control format differs')
        if case_id == 'c01':
            require(not any(audio.samples), 'Silence control contains nonzero PCM')
        records[case_id] = dict(record, frames=audio.frames, sampleRate=SAMPLE_RATE, channels=1,
            verifiedExpected=expected['expected'])
    text = speech_text()
    captured = json.loads((CONTROLS / 'provenance.json').read_text())
    require(captured['cases']['c06']['synthesis']['text'] == text, 'Known speech text differs from captured provenance')
    require(set(records['c06']['verifiedExpected']['required_words']) <= set(re.findall(r'\b\w+\b', text.lower())),
        'Verified speech words differ from control text')
    return manifest, prompts.pop(), records, text


def bind_run(path, sources):
    if path is None:
        return None
    document = json.loads(path.read_text())
    require(document.get('schemaVersion') == 1 and document.get('status') == 'completed'
        and document.get('finishedAt'), 'Source run is not a completed listening recipe')
    require(all(stage.get('status') in ('completed', 'reused') for stage in document['stages']),
        'Source run has an incomplete stage')
    bindings = {}
    for role, label in (('reference', 'fullReference'), ('candidate', 'fullCandidate')):
        source_path = document['deliverables'][label]
        matching = [artifact for artifact in document['artifacts'] if artifact.get('path') == source_path
            and artifact.get('type') == 'file']
        require(len(matching) == 1 and matching[0]['sha256'] == sources[role]['sha256'],
            f'{role} WAV does not match its completed-run artifact')
        bindings[role] = matching[0]
    return dict(receipt=fingerprint(path), artifacts=bindings)


def convert_crop(source, case_id, output):
    audio = read_pcm16(source)
    frames = round(CROP_SECONDS * audio.sample_rate)
    require(frames <= audio.frames, 'Rendered WAV is shorter than the frozen 4.45-second crop')
    crop, converted = output / 'work' / (case_id + '.crop.wav'), output / 'work' / (case_id + '.converted.wav')
    samples = audio.samples[:frames * audio.channels]
    _write_wav(crop, audio, [samples], [])
    require(read_pcm16(crop).samples == samples, 'Unity-gain crop changed PCM')
    command = [str(AFCONVERT), '-f', 'WAVE', '-d', 'LEI16@16000', '-c', '1', str(crop), str(converted)]
    subprocess.run(command, check=True, capture_output=True, timeout=30)
    resampled = read_pcm16(converted)
    require((resampled.sample_rate, resampled.channels, resampled.frames) ==
        (SAMPLE_RATE, 1, round(CROP_SECONDS * SAMPLE_RATE)), 'Converted crop format/duration differs')
    final = output / 'clips' / (case_id + '.wav')
    # afconvert can add filename metadata; only its PCM reaches model inputs.
    _write_wav(final, resampled, [resampled.samples], [])
    require(read_pcm16(final).samples == resampled.samples, 'Plain WAV re-encoding changed PCM')
    return dict(source=fingerprint(source), sourceSampleRate=audio.sample_rate, sourceChannels=audio.channels,
        sourceFrames=audio.frames, startFrameInclusive=0, endFrameExclusive=frames,
        requestedSeconds=CROP_SECONDS, actualCropSeconds=frames / audio.sample_rate,
        gain=1, gainDb=0, normalization=False, crop=fingerprint(crop),
        cropPcmSha256=hashlib.sha256(_pcm_bytes(samples)).hexdigest(), conversionCommand=command,
        converted=fingerprint(converted), final=fingerprint(final), containerMetadataRemoved=True)


def prepare(reference, candidate, output, run=None):
    reference, candidate = Path(reference).resolve(), Path(candidate).resolve()
    output = Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh preparation output directory')
    output = output.resolve()
    require(output.is_relative_to((ROOT / 'build').resolve()), 'Preparation output must be under ignored build/')
    protocol, prompt, controls, text = load_protocol()
    sources = {role: fingerprint(path) for role, path in (('reference', reference), ('candidate', candidate))}
    source_run = bind_run(Path(run).resolve() if run is not None else None, sources)
    for path in (reference, candidate):
        audio = read_pcm16(path)
        require(audio.frames >= round(CROP_SECONDS * audio.sample_rate), 'Rendered WAV is shorter than the frozen 4.45-second crop')
    require(AFCONVERT.is_file(), 'Required /usr/bin/afconvert is unavailable')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'clips').mkdir()
    (output / 'work').mkdir()
    crops = {'p01': convert_crop(candidate, 'p01', output), 'p04': convert_crop(reference, 'p04', output)}
    for case_id, original in (('p02', 'c01'), ('p03', 'c06')):
        target = output / 'clips' / (case_id + '.wav')
        shutil.copyfile(controls[original]['path'], target)
        require(fingerprint(target)['sha256'] == controls[original]['sha256'], 'Control copy changed WAV bytes')
    cases = dict(model=protocol['model'], max_tokens=protocol['max_tokens'], reasoning=protocol['reasoning'],
        cases=[dict(id=case_id, wav='clips/' + case_id + '.wav', prompt=prompt)
            for case_id in ('p01', 'p02', 'p03', 'p04')])
    write_json(output / 'cases.json', cases)
    prepared = _prepare(output / 'cases.json', output / 'results')
    bindings = {case['id']: {key: case[key] for key in
        ('audio_sha256', 'payload_sha256', 'duration_seconds')} for case in prepared}
    oracle = dict(schemaVersion=1, controls=[
        dict(id='p02', category='silence', requiredTranscript='', **bindings['p02']),
        dict(id='p03', category='speech', requiredText=text,
            requiredWords=re.findall(r'\b\w+\b', text.lower()), **bindings['p03'])],
        descriptiveOnly=[dict(id=case_id, expectedCategory=None, expectedTranscript=None, **bindings[case_id])
            for case_id in ('p01', 'p04')],
        gate=dict(requireAllControls=True, requireSilenceEmptyTranscript=True,
            speechWordMatching='Case and punctuation ignored; 7 is equivalent to seven; require every SPEECH_TEXT word.',
            onControlFailure='Disregard descriptive render classifications/transcripts.',
            renderedSpeechGroundTruth=False, intelligibilityAcceptance=False),
        budget=dict(runner='scripts/audio_assessment.py', requestCount=4, noRetries=True, promptTuning=False),
        boundary='Withheld local oracle only. Neither this file nor provenance may be attached to model requests.')
    write_json(output / 'oracle.json', oracle)
    provenance = dict(schemaVersion=1, sources=sources, completedSourceRun=source_run,
        caseRoles=dict(p01='candidate opening', p02='exact retained c01 silence',
            p03='exact retained c06 ordinary speech', p04='original reference opening'),
        crops=crops, controls=controls, promptSha256=hashlib.sha256(prompt.encode()).hexdigest(),
        protocol=dict(manifest=fingerprint(QWEN / 'cases.json'), verifiedAssessment=fingerprint(QWEN / 'verified-assessment.json'),
            controlProvenance=fingerprint(CONTROLS / 'provenance.json')),
        tools={str(path): fingerprint(path) for path in (Path(__file__).resolve(), GENERATOR,
            ROOT / 'scripts/audio_assessment.py', ROOT / 'scripts/audio_comparison.py',
            Path(wave.__file__), Path(sys.executable).resolve(), AFCONVERT)},
        platform=dict(python=sys.version, macos=platform.mac_ver()[0]),
        modelInputs=dict(anonymousSingleClips=True, originalIdentitySupplied=False,
            expectedWordsSupplied=False, containerMetadataRemovedFromCrops=True),
        scope='Offline preprocessing and existing-runner validation only; no API calls, transcription ground truth or musical acceptance.')
    for role, path in (('reference', reference), ('candidate', candidate)):
        require(fingerprint(path) == sources[role], 'A full rendered input changed during preparation')
    for original, record in controls.items():
        require(fingerprint(record['path'])['sha256'] == record['sha256'], 'A retained control changed during preparation')
    write_json(output / 'provenance.json', provenance)
    validation = dict(schemaVersion=1, passed=True, dryRunOnly=True, apiRequests=0, cases=bindings,
        outputs={name: fingerprint(output / name) for name in ('cases.json', 'oracle.json', 'provenance.json')})
    write_json(output / 'validation.json', validation)
    return validation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run', type=Path, help='Optional completed main listening recipe binding both full WAVs')
    args = parser.parse_args()
    result = prepare(args.reference, args.candidate, args.output, args.run)
    print(json.dumps(dict(passed=result['passed'], dryRunOnly=True, apiRequests=0, cases=result['cases'])))


if __name__ == '__main__':
    main()
