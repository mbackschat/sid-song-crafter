"""Prepare the preserved first Für Elise phrase for matched Shades timbre listening."""

import argparse
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))

from shades_player import score_module
from shades_programs import Programs, State
from verify_player import require


PAL_CLOCK = 985248
TIMER_PERIOD = 12326
END_BEAT = Fraction(12)
PHYSICAL_ROLES = ('bass', 'harmony', 'melody')
RELEASE_ROWS = 32
RELEASE_ROW_CALLS = 5


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def description_hash(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def rational(value, label):
    require(type(value) in (int, float), f'{label} must be a finite number')
    try:
        return Fraction(str(value))
    except ValueError:
        raise ValueError(f'{label} must be a finite number') from None


def call_at(beat, bpm):
    exact = beat * 60 * PAL_CLOCK / (bpm * TIMER_PERIOD)
    # describe-shades-score.py:expand_score reserves call zero for selection;
    # round absolute boundaries so quarter-beat errors never accumulate.
    return 1 + (2 * exact.numerator + exact.denominator) // (2 * exact.denominator)


def excerpt_voices(source):
    require(type(source) is dict and type(source.get('voices')) is list, 'Source requires three named roles')
    roles = {voice.get('name'): voice for voice in source['voices'] if type(voice) is dict}
    require(len(source['voices']) == len(roles) == 3 and set(roles) == set(PHYSICAL_ROLES),
            'Source requires exactly melody, bass and harmony roles')
    require(rational(source.get('totalBeats'), 'Source totalBeats') >= END_BEAT,
            'Source does not contain the complete excerpt')
    events = {}
    for role in PHYSICAL_ROLES:
        voice = roles[role]
        instrument = voice.get('instrument')
        require(type(instrument) is dict and set(instrument) == {'waveform', 'attackDecay', 'sustainRelease'}
                and instrument['waveform'] == 16, 'Plain reference requires the source triangle instruments')
        for key in ('attackDecay', 'sustainRelease'):
            require(type(instrument[key]) is int and 0 <= instrument[key] <= 255,
                    f'Source instrument {key} must be a byte')
        require(type(voice.get('events')) is list, f'Source {role} requires events')
        selected = []
        for event in voice['events']:
            require(type(event) is dict, f'Source {role} event must be an object')
            start = rational(event.get('startBeat'), 'Event startBeat')
            require(start >= 0, 'Events must not begin before the excerpt')
            if start >= END_BEAT:
                continue
            require(set(event) == {'startBeat', 'durationBeats', 'midi'}, 'Unsupported excerpt event fields')
            duration = rational(event['durationBeats'], 'Event duration')
            require(duration > 0, 'Event duration must be positive')
            end = start + duration
            require(end <= END_BEAT, 'An event crosses the excerpt boundary; clipping is unsupported')
            require((start * 4).denominator == (end * 4).denominator == 1,
                    'Excerpt events require quarter-beat onset and end boundaries')
            midi = event['midi']
            require(type(midi) is int and 13 <= midi <= 107,
                    'Excerpt pitch must map to Shades note indices 1..95 (MIDI 13..107)')
            selected.append({'start': start, 'end': end, 'midi': midi})
        selected.sort(key=lambda event: event['start'])
        for previous, following in zip(selected, selected[1:]):
            require(previous['end'] <= following['start'], f'Unsupported {role} event overlap')
        events[role] = selected
    return roles, events


def reference_programs(roles, programs):
    neutral = deepcopy(programs['programs']['blocks']['pulse-trio'])
    for role, patch in zip(PHYSICAL_ROLES, neutral['voices']):
        instrument = roles[role]['instrument']
        for key in patch:
            patch[key] = 'target' if key == 'portamento_mode' else 0
        patch.update(control=instrument['waveform'], attack_decay=instrument['attackDecay'],
                     sustain_release=instrument['sustainRelease'])
    filt = neutral['filter']
    for key in ('routing', 'mode_volume', 'trigger_mask', 'percussion_mode_volume'):
        filt[key] = 0
    filt['mode_volume'] = 15
    for name in ('contour', 'percussion_contour'):
        filt[name] = {key: 0 for key in filt[name]}
    neutral['percussion_control'] = 0
    return {
        'format': 'sid-shades-programs-v1',
        'programs': {'frequency_words': list(programs['programs']['frequency_words']),
                     'blocks': {'pulse-trio': neutral}},
        'preloaded': State().to_dict(),
        'sourceEvidence': {
            'identity': 'Generated score reference from the preserved Für Elise arrangement; not an original performance.',
            'source': 'songs/fuer-elise.json',
            'instrumentRoles': list(PHYSICAL_ROLES),
            'basis': 'Source triangle waveform and AD/SR envelopes, unchanged Shades frequency table, driver and score; no modulation, filter or fine tuning.',
            'listeningStatus': 'Pending',
        },
    }


def prepare_elise(source, programs):
    """Transfer beats [0, 12) without note edits to the PAL Shades pulse trio.

    This bounded adapter accepts three monophonic roles and quarter-beat event
    boundaries. It rejects overlaps, clipping, unrepresentable pitches and a
    calendar outside the existing driver's row range. Adjacent notes use that
    driver's same-call gate-off/on retrigger; rests mark real gaps and note ends.
    The generated plain reference uses the same score and pitch lookup, with
    source triangle/envelope patches, so it is not the original performance.
    """
    require(type(programs) is dict and programs.get('format') == 'sid-shades-programs-v1',
            'Unsupported Shades programs format')
    bank = Programs.from_dict(programs.get('programs'))
    require('pulse-trio' in bank.blocks, 'Target programs require pulse-trio')
    require(all(patch.portamento_step == 0 for patch in bank.blocks['pulse-trio'].voices),
            'This transfer requires pulse-trio without glide')
    require(programs.get('preloaded') == State().to_dict(), 'This transfer requires a cold silent state')
    roles, events = excerpt_voices(source)
    bpm = rational(source.get('quarterBpm'), 'Source quarterBpm')
    require(bpm > 0, 'Source quarterBpm must be positive')
    boundaries = [Fraction(index, 4) for index in range(int(END_BEAT * 4) + 1)]
    calls = [call_at(beat, bpm) for beat in boundaries]
    durations = [end - start for start, end in zip(calls, calls[1:])]
    require(all(1 <= duration <= 256 for duration in durations),
            'Unsupported CIA calendar: quarter-beat rows must occupy 1..256 calls')
    patterns, pattern_names, orders = {}, {}, []

    def pattern_id(rows):
        key = json.dumps(rows, sort_keys=True)
        if key not in pattern_names:
            name = f'pattern-{len(patterns):03d}'
            pattern_names[key] = name
            patterns[name] = {'rows': rows}
        return pattern_names[key]

    for beat, duration in zip(boundaries, durations):
        ids = []
        for role in PHYSICAL_ROLES:
            active = next((event for event in events[role] if event['start'] <= beat < event['end']), None)
            if active is None:
                row = {'kind': 'rest'}
            elif active['start'] == beat:
                row = {'kind': 'note', 'sourceNote': active['midi'] - 12, 'gate': 'on'}
            else:
                row = {'kind': 'hold'}
            ids.append(pattern_id([row]))
        orders.append({'patternIds': ids, 'instrument': 'pulse-trio', 'transposeSemitones': [0, 0, 0],
                       'voice1HighNotesAbsolute': False, 'rowCount': 1, 'rowDurationCalls': duration,
                       'timerHigh': 0x30, 'fade': {'kind': 'cancel'}})
    release_id = pattern_id([{'kind': 'rest'} for _ in range(RELEASE_ROWS)])
    orders.append({'patternIds': [release_id] * 3, 'instrument': 'pulse-trio', 'transposeSemitones': [0, 0, 0],
                   'voice1HighNotesAbsolute': False, 'rowCount': RELEASE_ROWS,
                   'rowDurationCalls': RELEASE_ROW_CALLS, 'timerHigh': 0x30,
                   'fade': {'kind': 'start', 'rowInterval': 2}})
    stop = calls[-1] + RELEASE_ROWS * RELEASE_ROW_CALLS
    timing = {
        'clockHz': PAL_CLOCK, 'timerLatch': 0x3025, 'periodCycles': TIMER_PERIOD,
        'sourceQuarterBpm': source['quarterBpm'],
        'boundaryRounding': 'Nearest CIA call, half up, from each absolute source beat; add 1 for score call-zero selection.',
        'beatZeroCall': 1, 'lastNoteOffCall': calls[-1], 'finiteStopCall': stop,
        'maximumBoundaryErrorSeconds': TIMER_PERIOD / PAL_CLOCK / 2,
        'finiteStopSecondsFromCallZero': stop * TIMER_PERIOD / PAL_CLOCK,
        'releaseFade': 'All voices rest at beat 12; 32 five-call rows fade every two rows, reaching zero before the terminal silence stores.',
    }
    counts = {role: len(events[role]) for role in ('melody', 'bass', 'harmony')}
    score = {
        'format': 'sid-shades-score-v1', 'profile': dict(score_module.PROFILE),
        'range': {'firstCall': 0, 'firstRowCall': 1, 'lastCallInclusive': stop - 1,
                  'stopCall': stop, 'cycleCalls': stop - 1},
        'instrumentBlocks': ['pulse-trio'], 'patterns': patterns, 'orders': orders,
        'sourceEvidence': {
            'identity': 'Preserved Für Elise arrangement, first repeat body and complete A-minor first ending; Shades instrument transfer.',
            'source': 'songs/fuer-elise.json', 'sourceDescriptionSha256': description_hash(source),
            'excerptBeats': [0, 12], 'retainedEvents': counts,
            'voiceMapping': {'bass': 1, 'harmony': 2, 'melody': 3},
            'pitchMapping': 'frequency_words[0] is C0; pitch-table index = MIDI - 12.',
            'timing': timing,
            'deliberateChanges': ['Shades pulse-trio timbres replace source triangle instruments; no glide block is selected.',
                                  'CIA-call quantization and a separate release/fade after the preserved phrase.'],
            'listeningStatus': 'Pending; numeric preparation does not establish musical quality.',
        },
    }
    reference = reference_programs(roles, programs)
    score_module.expand_score(score)
    Programs.from_dict(reference['programs'])
    receipt = {
        'evidenceLevel': 'Deterministic score conversion; no compiled CPU, CIA execution, audio or listening claim',
        'sourceDescriptionSha256': description_hash(source),
        'transferProgramsDescriptionSha256': description_hash(programs),
        'generatedScoreSha256': description_hash(score),
        'generatedReferenceProgramsSha256': description_hash(reference),
        'excerptBeats': [0, 12], 'retainedEvents': counts,
        'totalRetainedEvents': sum(counts.values()), 'omittedExcerptEvents': 0,
        'timing': timing, 'orders': len(orders), 'patterns': len(patterns),
        'limits': ['Only the first 12 beats of the preserved three-role arrangement.',
                   'Monophonic quarter-beat event boundaries, without clipping or note edits.',
                   'MIDI 13..107 maps to native note indices 1..95; index zero is the native rest token.',
                   'Driver retriggers adjacent notes within one call; this preserves score gate timing, not source bus timing.',
                   'Plain reference is generated through the Shades driver, not an original performance.'],
    }
    return score, reference, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'songs/fuer-elise.json')
    parser.add_argument('--programs', type=Path, default=ROOT / 'songs/shades-transfer-programs.json')
    parser.add_argument('--score-output', type=Path, default=ROOT / 'songs/shades-elise-transfer.json')
    parser.add_argument('--reference-programs-output', type=Path,
                        default=ROOT / 'songs/shades-elise-reference-programs.json')
    parser.add_argument('--check', action='store_true', help='Check both saved fixtures without changing files')
    args = parser.parse_args()
    source_data, program_data = args.source.read_bytes(), args.programs.read_bytes()
    score, reference, receipt = prepare_elise(json.loads(source_data), json.loads(program_data))
    outputs = [(args.score_output, score), (args.reference_programs_output, reference)]
    if args.check:
        for path, value in outputs:
            require(path.read_bytes() == encoded(value), f'Saved fixture differs from generated output: {path}')
    else:
        require(args.score_output.resolve() != args.reference_programs_output.resolve(), 'Choose distinct output paths')
        require(all(not path.exists() and not path.is_symlink() for path, _ in outputs),
                'Choose fresh outputs; use --check to verify existing fixtures')
        for path, value in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(encoded(value))
    receipt.update(sourceFileSha256=hashlib.sha256(source_data).hexdigest(),
                   transferProgramsFileSha256=hashlib.sha256(program_data).hexdigest())
    print(json.dumps(receipt, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
