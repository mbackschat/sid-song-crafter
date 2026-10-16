"""Freeze a four-request descriptive trial using the calibrated Trap prompt."""

import argparse
import importlib.util
from pathlib import Path
import wave

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('trap_perception', ROOT / 'scripts/studies/audio-assessment/prepare-trap-perception.py')
TRAP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRAP)
SOURCES = (
    ('build/axel-f-master-palette-matched-listening/huelsbeck-lead-and-beat-9.5-20s.wav',
     '79c8e2b6a52413e63b99c68f8bd724d030ea794a88aada3998073ebfc4be8325'),
    ('build/axel-f-drum-pair-listening/source-kick-and-snare.wav',
     '0119c2536f5db68eadbe06076575ed0c90ea276414058568dc16c214f97418e7'),
)
FRAMES = 463050


def read_crop(path, expected_sha):
    if TRAP._sha(path.read_bytes()) != expected_sha:
        raise ValueError('Source fingerprint changed')
    with wave.open(str(path), 'rb') as source:
        if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, 44100) or source.getnframes() < FRAMES:
            raise ValueError('Expected at least 10.5 seconds of mono 44.1 kHz PCM16')
        pcm = source.readframes(FRAMES)
    if not any(pcm):
        raise ValueError('Source is silent')
    return pcm


def control_cases(master, candidate):
    return dict(c01=master, c02=candidate, c03=bytes(FRAMES * 2), c04=master[:FRAMES * 2 // 5] * 5)


def prepare(output):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / 'build') or output.exists():
        raise ValueError('Choose a fresh private directory under build/')
    pcm = control_cases(*(read_crop(ROOT / path, digest) for path, digest in SOURCES))
    inputs = output / 'inputs'
    inputs.mkdir(parents=True)
    cases = []
    for case_id, audio in pcm.items():
        path = inputs / f'{case_id}.wav'
        TRAP._write_audio(path, audio)
        cases.append(dict(id=case_id, wav=path.name, audio_sha256=TRAP._sha(path.read_bytes()), prompt=TRAP.PROMPT))
    manifest = inputs / 'qwen.json'
    settings = dict(model='qwen/qwen3.8-omni-flash', reasoning=True, max_tokens=1200)
    TRAP._write(manifest, dict(**settings, cases=cases))
    binding = [{key: case[key] for key in ('id', 'audio_sha256', 'payload_sha256', 'duration_seconds')}
               for case in TRAP._prepare(manifest, output / 'results')]
    TRAP._write(inputs / 'oracle.json', dict(
        schema_version=1, models=dict(qwen=dict(settings=settings, cases=binding)),
        cases=[dict(id='c01', expected={}, basis='Unscored descriptive master observation'),
               dict(id='c02', expected={}, basis='Unscored descriptive candidate observation'),
               dict(id='c03', expected=dict(music_present='no', rhythmic_motion='no music', development='no music'), basis='Digital silence'),
               dict(id='c04', expected=dict(development='repeats'), basis='Exact 2.1-second source window tiled five times')],
        criterion='Require four completed responses with valid bounded evidence, and both controls passing before considering descriptions. Review descriptions against source execution separately. No preference score or automatic musical changes.',
        scope='New passage with unchanged Trap prompt/settings; known human feedback remains local. Not a blind held-out human preference test. Previous failed A/A and reversed-pair controls remain unresolved; this is a single-clip task.',
        budget=dict(post_attempts_total_max=4, local_admission_cap_usd='0.10', no_retries=True),
        authorization='User: OK, go ahead with your recommendations. 2026-10-16; four described Qwen requests through existing provider.'))
    TRAP._write(inputs / 'provenance.json', dict(
        sources=[dict(path=path, sha256=digest, localCropSeconds=[0, 10.5]) for path, digest in SOURCES],
        gain=1, normalization=False, resampling=False, prompt=TRAP.PROMPT,
        comparisonLimit='Different key, tempo, chip model and accompaniment: master PAL MOS6581 lead/drums; native PAL MOS8580 lead/bass/drums. Descriptions cannot isolate causes of preference.',
        dependencies={str(path.relative_to(ROOT)): TRAP._sha(path.read_bytes()) for path in
                      (Path(__file__), Path(TRAP.__file__), ROOT / 'scripts/audio_assessment.py', ROOT / 'scripts/audio_comparison.py')},
        submitted='Only anonymous clip, neutral prompt and fixed settings; no titles, user verdicts, oracle or provenance.'))
    TRAP._write(output / 'frozen-inputs.json', dict(files={path.name: TRAP._sha(path.read_bytes()) for path in inputs.iterdir()}))
    TRAP.verify_frozen_inputs(output)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.output))
