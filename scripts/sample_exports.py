"""Make a fixed, note-preserving stereo presentation of a one-SID native module."""

import argparse
from array import array
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import wave

from audio_comparison import Pcm16, inspect_wav, measure_pcm, read_pcm16
from psid_audit import audit_psid
from verify_player import require

ROOT = Path(__file__).resolve().parents[1]
VOICE_MAP = (0, 1, None, 0, None, 2)


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


exporter = load_script('export-sidwizard')
native = load_script('native-song')


def split_module(data):
    exporter.inspect_module(data)
    header = bytearray(data[2:66])
    cursor = len(data) - 2 - header[16] - header[15]
    for _ in range(header[14]):
        cursor -= data[cursor - 9] + 9
    tail = data[cursor:]
    patterns = []
    for _ in range(header[13]):
        start = exporter.native_pattern_start(data, cursor, data[cursor - 2])
        patterns.insert(0, data[start:cursor])
        cursor = start
    sequences = []
    for _ in range(header[12]):
        start = cursor - data[cursor - 1] - 1
        sequences.insert(0, data[start:cursor])
        cursor = start
    require(cursor == 66, 'Native module boundaries disagree')
    return dict(header=header, sequences=sequences, patterns=patterns, tail=tail)


def stereo_module(data):
    parts = split_module(data)
    header = parts['header']
    require(header[:4] == b'SWM1', 'Stereo presentation requires one SID')
    require(header[14] <= 29 and header[13] < 105, 'Source exceeds two-SID module capacity')
    header[:4] = b'SWMS'
    header[21] = header[5]
    header[5:8] = header[8:11]
    header[12] = 6
    header[13] += 1
    header[22] = 0
    silent = bytes((header[13], 0xfe, 2))
    sequences = [silent if voice is None else parts['sequences'][voice] for voice in VOICE_MAP]
    result = (data[:2] + header + b''.join(sequences) + b''.join(parts['patterns'])
              + bytes((0, 2, 1)) + parts['tail'])
    exporter.inspect_module(result)
    return bytes(result)


def verify_frames(source, candidate, ticks):
    mono_audit, mono_writes = audit_psid(source, ticks)
    stereo_audit, stereo_writes = audit_psid(candidate, ticks)
    mono = native.frame_states(mono_writes, ticks)
    stereo = native.frame_states(stereo_writes, ticks, (0xd400, 0xd420))
    for tick, (before, after) in enumerate(zip(mono, stereo)):
        for target, origin in enumerate(VOICE_MAP):
            offset = native.voice_offset(target)
            if origin is None:
                require(not after[offset + 4] & 1, f'Unused voice gates at call {tick}')
                continue
            expected = before[origin * 7:origin * 7 + 7]
            require(after[offset:offset + 7] == expected,
                    f'Voice {origin + 1} differs at call {tick}, stereo voice {target + 1}')
            control = expected[4]
            require(not (control & 0xf0 and not control & 8 and control & 6),
                    'Fixed stereo mapping does not admit sounding sync/ring instruments')
        # Each voice keeps its original physical index; only its chip changes.
        # Filter equality is required whenever that voice actually uses the shared filter.
        for target, origin in enumerate(VOICE_MAP):
            if origin is not None and before[23] & (1 << origin):
                offset = (target // 3) * 25
                require(after[offset + 21:offset + 25] == before[21:25],
                        f'Active filter differs at call {tick}, voice {origin + 1}')
    return dict(checkedCalls=ticks, voiceMap=list(VOICE_MAP), writes=stereo_writes,
                monoAudit=mono_audit, stereoAudit=stereo_audit,
                guarantees='Mapped voice registers and each active filter agree at every call; no new notes.',
                listeningStatus='Stereo presentation awaiting listening review')


def build(source, reference_sid, output, seconds, ticks, title):
    output = Path(output)
    require(not output.exists(), 'Choose a fresh output directory')
    output.mkdir(parents=True)
    module = output / 'stereo.sws'
    module.write_bytes(stereo_module(Path(source).read_bytes()))
    exported = exporter.export_module(module, output / 'export', title=title,
                                      author='SID Song Crafter', clock='pal', sid_model='MOS8580')
    report = verify_frames(Path(reference_sid).read_bytes(), Path(exported['sid']).read_bytes(), ticks)
    (output / 'stereo.writes.json').write_text(json.dumps(report.pop('writes'), separators=(',', ':')) + '\n')
    wav = output / 'stereo.wav'
    subprocess.run([str(ROOT / '.local/bin/render-sid'), exported['sid'], str(wav), str(seconds),
                    '--clock', 'pal', '--subtune', '1'], check=True, timeout=120)
    pcm = read_pcm16(wav)
    metrics = inspect_wav(wav)
    require(pcm.channels == 2 and metrics['clippedSamples'] == 0, 'Expected unclipped stereo PCM')
    require(pcm.samples[::2] != pcm.samples[1::2], 'Stereo channels must carry distinct accompaniment')
    tail_frames = pcm.sample_rate // 2
    tail = Pcm16(pcm.sample_rate, 2, tail_frames, pcm.samples[-2 * tail_frames:], '')
    require(measure_pcm(tail)['acRms'] <= 2, 'Stereo ending must retain a quiet final half-second')
    folded = array('h', (round((left + right) / 2) for left, right in zip(pcm.samples[::2], pcm.samples[1::2])))
    with wave.open(str(output / 'fold-down.wav'), 'wb') as target:
        target.setparams((1, 2, pcm.sample_rate, 0, 'NONE', 'not compressed'))
        if sys.byteorder != 'little':
            folded.byteswap()
        target.writeframes(folded.tobytes())
    report.update(sourceSha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                  sidSha256=exported['sidSha256'], export=exported, audio=metrics,
                  outputMatrix=[[1, 0], [0, 1]], gain=1, tail=measure_pcm(tail),
                  foldDown=inspect_wav(output / 'fold-down.wav'))
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('reference_sid', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, required=True)
    parser.add_argument('--ticks', type=int, required=True)
    parser.add_argument('--title', required=True)
    args = parser.parse_args()
    build(args.source, args.reference_sid, args.output, args.seconds, args.ticks, args.title)
