"""Compile editable notes and computed instrument families into a finite PAL SID."""

import argparse
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys

from audio_comparison import Pcm16, inspect_wav, measure_pcm, read_pcm16
from psid_audit import audit_psid
from sid_assembler import assemble
from verify_player import PAL_CLOCK, require

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / 'songs/studies/drax-full-reconstruction/full-composition.json'


def helper(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bass = helper('reconstruct-drax-bass')


def word(value, label, minimum=0):
    require(type(value) is int and minimum <= value <= 65535, f'{label} must fit a word')
    return value


def validate(description):
    require(description['format'] == 'sid-decoded-composition-v1', 'Unsupported composition format')
    require(description['profile'] == {'clock': 'PAL', 'chip': 'MOS6581', 'callCycles': 19656}, 'Unsupported profile: use one PAL MOS6581 at one call per frame')
    stop = word(description['range']['stopCall'], 'stopCall', 3)
    require(description['range']['firstCall'] == 0, 'Execute from initialization to preserve instrument history')
    require(description['range']['lastCallInclusive'] == stop - 1, 'Range and stopCall disagree')
    require(set(description['roles']) == {'bass', 'lead', 'chord'}, 'This backend supports exactly three roles: bass, lead, chord')
    for voice, role in enumerate(('bass', 'lead', 'chord'), 1):
        part = description['roles'][role]
        require(part['voice'] == voice, 'This backend assigns bass, lead, chord to voices 1, 2, 3')
        notes = part['notes']
        require(0 < len(notes) < 256, 'Each role requires 1..255 notes')
        for index, note in enumerate(notes):
            allowed = {'initCall', 'frequency', 'patch', 'sourceEvidence'}
            if role != 'bass':
                allowed.add('gateOffCall')
            if role == 'chord':
                allowed.add('frequencies')
            require(set(note) <= allowed, f'Unknown {role} note fields: {set(note) - allowed}')
            call = word(note['initCall'], 'initCall', 2)
            word(note['frequency'], 'frequency', 1)
            require(call < stop, 'Note starts after the ending')
            end = notes[index + 1]['initCall'] if index + 1 < len(notes) else stop + 2
            require(end - call >= (6 if role == 'bass' else 4), 'Overlapping preparation or attack')
            require(end - call < 255, 'Instrument age must not wrap; split long holds explicitly')
            require(note['patch'] in description['patches'], 'Unknown instrument patch')
            if 'gateOffCall' in note:
                require(role != 'bass', 'Bass gate belongs to its instrument')
                require(type(note['gateOffCall']) is int and call < note['gateOffCall'] < end - 2, 'Gate closure must precede the next preparation')
            if role == 'chord':
                require(1 <= len(note['frequencies']) <= 8, 'Chord needs 1..8 tones')
                for pitch in note['frequencies']:
                    word(pitch, 'chord frequency', 1)
    return stop


def build(path):
    path = Path(path).resolve()
    description = json.loads(path.read_text())
    stop = validate(description)
    parts, patches = description['roles'], description['patches']
    fields = {
        'bass': {'attackDecay', 'sustainRelease', 'pulseInitial', 'pulseStep', 'pulseLowerHighByte', 'pulseUpperHighByte', 'instrumentGateCloseAge', 'noiseControl', 'pulseControl', 'releaseControl', 'noiseFrequency', 'attackCutoffHigh', 'bodyCutoffHigh', 'filterRoutingResonance', 'filterModeVolume'},
        'lead': {'attackDecay', 'sustainRelease', 'pulseInitial', 'pulseStep', 'pulseLowerHighByte', 'pulseUpperHighByte', 'waveform', 'vibratoStartAge', 'vibratoDeltas'},
        'chord': {'attackDecay', 'sustainRelease', 'pulseInitial', 'pulseStep', 'waveform', 'toneDwellCalls'},
    }
    family = {}
    for role in ('bass', 'lead', 'chord'):
        used = [patches[n['patch']] for n in parts[role]['notes']]
        for patch in used:
            runtime_fields = set(patch) - {'sourceEvidence'}
            require(runtime_fields == fields[role], f'Invalid {role} patch fields: missing {fields[role] - runtime_fields}; unknown {runtime_fields - fields[role]}')
        family[role] = used[0]
        if role != 'chord':
            require(all(p == used[0] for p in used), f'This backend supports one {role} patch per song')
        else:
            for patch in used:
                require(all(patch[key] == used[0][key] for key in ('attackDecay', 'sustainRelease', 'waveform')), 'Chord variants must share envelope and waveform')
                require(type(patch['pulseInitial']) is int and 0 <= patch['pulseInitial'] < 4096 and patch['pulseInitial'] & 255 == 0, 'Chord pulse must be a 12-bit whole high-byte width')
                require(patch['pulseStep'] == 0 and patch['toneDwellCalls'] == 2, 'Chord backend supports static pulse and two-call tone dwell')
    lead, chord = family['lead'], family['chord']
    require(len(lead['vibratoDeltas']) == 8 and all(type(n) is int and -32768 <= n <= 32767 for n in lead['vibratoDeltas']), 'Lead vibrato needs eight signed word deltas')
    require(1 <= lead['vibratoStartAge'] < 255, 'Vibrato start must fit instrument age')
    require(0 < lead['pulseStep'] < 256 and 0 <= lead['pulseLowerHighByte'] < lead['pulseUpperHighByte'] <= 15, 'Invalid lead PWM bounds')
    word(lead['pulseInitial'], 'lead pulse')
    require(lead['pulseLowerHighByte'] <= lead['pulseInitial'] >> 8 <= lead['pulseUpperHighByte'], 'Lead PWM starts outside its bounds')
    require((lead['pulseInitial'] + lead['pulseStep']) >> 8 <= lead['pulseUpperHighByte'], 'Lead PWM first step must reach its upper reversal bound before passing it')
    require(all(p['waveform'] & 9 == 0 for p in (lead, chord)), 'Companion waveform must leave GATE and TEST to the scheduler')
    require(family['bass']['instrumentGateCloseAge'] == 3, 'Bass family closes GATE at age 3')
    recipe = json.loads((path.parent / description['bassRecipe']).read_text())
    for key in recipe['instrument']:
        if key in family['bass']:
            recipe['instrument'][key] = family['bass'][key]
    recipe['notes'], recipe['playCalls'] = parts['bass']['notes'], 1
    constants = bass.constants(recipe)
    constants.pop('PLAY_CALLS')
    constants.update({
        'STOP_LO': stop & 255, 'STOP_HI': stop >> 8,
        'LEAD_COUNT': len(parts['lead']['notes']), 'CHORD_COUNT': len(parts['chord']['notes']),
        'LEAD_PULSE_LO': lead['pulseInitial'] & 255, 'LEAD_PULSE_HI': lead['pulseInitial'] >> 8,
        'LEAD_STEP': lead['pulseStep'], 'LEAD_LOWER': lead['pulseLowerHighByte'], 'LEAD_UPPER': lead['pulseUpperHighByte'],
        'LEAD_PRE_BOUND': 4, 'LEAD_PRE_PULSE_HI': 8,
        'LEAD_AD': lead['attackDecay'], 'LEAD_SR': lead['sustainRelease'], 'LEAD_WAVE': lead['waveform'],
        'CHORD_AD': chord['attackDecay'], 'CHORD_SR': chord['sustainRelease'], 'CHORD_WAVE': chord['waveform'], 'CHORD_PULSE_HI': 6,
        'VIBRATO_START_AGE': lead['vibratoStartAge'],
    })
    require(all(type(v) is int and 0 <= v <= 255 for v in constants.values()), 'Instrument constants must fit bytes')
    arrays = {}
    def words(name, values):
        arrays[name + '_lo'] = [n & 255 for n in values]
        arrays[name + '_hi'] = [(n >> 8) & 255 for n in values]
    for role in ('bass', 'lead', 'chord'):
        notes = parts[role]['notes']
        for suffix, delta in (('restart', -2), ('prep', -1), ('init', 0)):
            words(role + '_' + suffix, [n['initCall'] + delta for n in notes])
        name = {'bass': 'note_frequency', 'lead': 'lead', 'chord': 'chord_note'}[role]
        words(name, [n['frequency'] for n in notes])
        if role != 'bass':
            arrays[role + '_gate_ages'] = [n['gateOffCall'] - n['initCall'] if 'gateOffCall' in n else 255 for n in notes]
    chord_notes = parts['chord']['notes']
    tones, starts = [], []
    for note in chord_notes:
        starts.append(len(tones))
        tones.extend(note['frequencies'])
    require(len(tones) <= 256, 'Chord tone bank must fit a byte index')
    words('chord', tones)
    words('vibrato', lead['vibratoDeltas'])
    arrays.update(chord_starts=starts, chord_lengths=[len(n['frequencies']) for n in chord_notes], chord_pulse_high=[patches[n['patch']]['pulseInitial'] >> 8 for n in chord_notes])
    source = (ROOT / 'songs/players/decoded-trio.asm').read_text()
    for name, values in arrays.items():
        source += '\n' + name + ':\n  .byte ' + ','.join(f'${v:02x}' for v in values) + '\n'
    payload, symbols, listing = assemble(source, constants)
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 2), (6, 124), (8, 0x1000), (10, symbols['entry_init']), (12, symbols['entry_play']), (14, 1), (16, 1), (118, 0x14)):
        struct.pack_into('>H', header, offset, value)
    for offset, text in ((22, description.get('title', 'Independent Elise theme')), (54, 'Independent computed trio'), (86, '2026; decoded DRAX parameters')):
        header[offset:offset + 32] = text.encode('ascii', errors='replace')[:31].ljust(32, b'\x00')
    return bytes(header) + payload, {'description': description, 'symbols': symbols, 'payloadBytes': len(payload), 'source': source, 'listing': listing}


def compare_writes(original, candidate):
    fields = ('phase', 'tick', 'address', 'value')
    a, b = [[tuple(row[k] for k in fields) for row in rows] for rows in (original, candidate)]
    if a != b:
        index = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        raise ValueError(f'Ordered SID write mismatch {index}: {a[index:index+1]} / {b[index:index+1]}; counts {len(a)}/{len(b)}')
    return {'matchedWrites': len(a), 'sameCallAddressValueOrder': True, 'exactCycleEquality': False}


def run(path, output, reference=None, vice=False):
    output = Path(output).resolve()
    require(not output.exists(), 'Choose a fresh output directory')
    sid, built = build(path)
    stop = built['description']['range']['stopCall']
    audited, writes = audit_psid(sid, stop + 3)
    guard = None
    if reference:
        original = Path(reference).read_bytes()
        require(bass.digest(original) == built['description']['source']['sha256'], 'Reference checksum differs from score provenance')
        _, original_writes = audit_psid(original, stop)
        guard = compare_writes(original_writes, [r for r in writes if r['phase'] == 'init' or r['tick'] < stop])
    output.mkdir(parents=True)
    (output / 'reconstructed.sid').write_bytes(sid)
    (output / 'player.asm').write_text(built.pop('source'))
    (output / 'player.listing').write_text(built.pop('listing'))
    bass.write_json(output / 'build.json', built)
    bass.write_json(output / 'audit.json', audited)
    bass.write_json(output / 'writes.json', writes)
    if guard:
        bass.write_json(output / 'register-comparison.json', guard)
    seconds = math.ceil(stop * 19656 / PAL_CLOCK) + 1
    renderer = ROOT / '.local/bin/render-sid'
    renderer_hash = bass.digest(renderer.read_bytes())
    audio_metrics = {}
    for label, source in [('reconstructed', output / 'reconstructed.sid')] + ([('reference', Path(reference).resolve())] if reference else []):
        bass.run_process([str(renderer), str(source), str(output / (label + '.wav')), str(seconds)], output / (label + '.render.json'))
        info = inspect_wav(output / (label + '.wav'))
        require(info['clippedSamples'] == 0 and info['acRms'] > 1 and info['durationSeconds'] == seconds, 'Render must have the expected duration and be audible and unclipped')
        audio_metrics[label] = info
    audio = read_pcm16(output / 'reconstructed.wav')
    tail_frames = round(audio.sample_rate * 0.5)
    tail = Pcm16(audio.sample_rate, audio.channels, tail_frames, audio.samples[-tail_frames * audio.channels:], '')
    tail_metrics = measure_pcm(tail)
    require(tail_metrics['acRms'] < 1, 'Rendered ending must settle to a quiet tail')
    if vice:
        bass.run_process([sys.executable, str(ROOT / 'scripts/trace-sid-vice.py'), str(output / 'reconstructed.sid'), '--oracle', str(output / 'writes.json'), '--first-call', '0', '--last-call', str(stop + 2), '--output', str(output / 'vice')], output / 'vice-command.json')
    require(bass.digest(renderer.read_bytes()) == renderer_hash, 'Renderer changed during the comparison')
    report = {'sourceDescription': str(Path(path).resolve()), 'descriptionSha256': bass.digest(Path(path).read_bytes()), 'sidSha256': bass.digest(sid), 'rendererSha256': renderer_hash, 'audio': audio_metrics, 'ending': tail_metrics, 'musicSeconds': stop * 19656 / PAL_CLOCK, 'renderSeconds': seconds, 'orderedWriteComparison': guard, 'originalDriverIncluded': False, 'registerDumpReplay': False, 'listeningReview': None, 'limits': 'One decoded thematic cycle, not the complete Beethoven score. Within-frame instruction timing and oscillator phases differ from the reference.'}
    bass.write_json(output / 'study.json', report)
    print(f'Built and rendered: {output}', flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('score', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--vice', action='store_true')
    args = parser.parse_args()
    run(args.score, args.output, args.reference, args.vice)


if __name__ == '__main__':
    main()
