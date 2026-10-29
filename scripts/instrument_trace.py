#!/usr/bin/env python3
"""Derive an instrument's interface, character and resources from an executed probe phrase (probe-interface-v1).

The probe is defined in docs/proposals/instrument-library.md: one standard phrase on one voice, converted, exported and
executed by the song pipeline (SID-Wizard tempo 1, PAL, MOS8580), with every classification read from the ordered SID
register states of the executed driver. Fields that need a render (level, brightness) belong to probe-level-v1; a field
the trace cannot settle is reported as not-established or unknown, never guessed.
"""

import argparse
from collections import namedtuple
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import instrument_library as library  # noqa: E402
from instrument_probe import load_script  # noqa: E402
from psid_audit import audit_psid  # noqa: E402
from sid_clock import clock_spec  # noqa: E402

PROBE_ID = 'probe-interface-v1'
NOT_ESTABLISHED = library.INTERFACE_UNSETTLED
UNKNOWN = {'basis': 'unknown'}
UNCLASSIFIED = 'unclassified'
PROBE_VOLUME = 15

# (label, start update, gated duration in updates, MIDI pitch); one voice, one update per beat, so every start is an exact tick.
# long: waveform, body, motion and the tie control; short2/short6: the shortest sounding notes; rep_gate: a new note after a
# gate-off cell; rep_nogate: a new note without one; reentry: a new note after a long rest; low/high: pitch tracking at two
# octaves either side; tie_*: a tie after 60 and after 4 updates; final: release behaviour, with a tail after it.
PHRASE = (
    ('long', 10, 140, 60),
    ('short2', 170, 2, 60), ('short6', 184, 6, 60),
    ('rep_gate1', 246, 12, 60), ('rep_gate2', 258, 12, 60), ('rep_gate3', 270, 12, 60),
    ('rep_nogate1', 300, 2, 60), ('rep_nogate2', 302, 2, 60), ('rep_nogate3', 304, 2, 60),
    ('reentry', 366, 30, 60), ('low', 420, 40, 36), ('high', 480, 40, 84),
    ('tie_late_a', 540, 60, 60), ('tie_late_b', 600, 70, 67),
    ('tie_early_a', 700, 4, 60), ('tie_early_b', 704, 46, 67),
    ('final', 780, 60, 60),
)
TIE_LEGS = (('tie_late_a', 'tie_late_b'), ('tie_early_a', 'tie_early_b'))
SCORE_UPDATES, TAIL_UPDATES = 850, 220
PITCH_NOTES = ('low', 'long', 'high')
# Notes that follow a gate-off cell. The first note is left out because registers before it are still zero, and the converter
# writes no gate-off cell between 2-update notes that abut (WITHOUT_GATE_OFF).
AFTER_GATE_OFF = ('short6', 'rep_gate2', 'rep_gate3', 'reentry', 'low', 'high', 'final')
WITHOUT_GATE_OFF = ('rep_nogate2', 'rep_nogate3')

Note = namedtuple('Note', 'start end gate_off midi')   # end: first update after the score duration; gate_off: update of the gate-off cell, None when a following note or tie replaces it
Onset = namedtuple('Onset', 'gate_before edge tests hard_restart')


@dataclass(frozen=True)
class Thresholds:
    """Conventions of this probe, echoed into every sidecar; none is a perceptual calibration."""
    # The converter's audit accepts a sounding note within one frequency word of the table entry (scripts/native-song.py).
    pitch_tolerance_words: int = 1
    # The low, long and high probe notes are two octaves apart; under a quarter octave from that spacing is tracking, from unison a fixed pitch.
    tracking_slack_octaves: float = 0.25
    # The median over the first body updates keeps a late vibrato or a bend from moving the settled pitch.
    pitch_median_updates: int = 40
    # A start frame that needs more updates than this to reach its pitch is not a normal note onset.
    onset_search_updates: int = 14
    # The registers of update 6 are past the start frame and the first table rows, so they hold the instrument's steady ADSR.
    steady_update: int = 6
    # Hard-restart writes precede the new note; the driver's tempo-3 restart spans two frames, so four is slack.
    hard_restart_lookback: int = 4
    # A TEST frame or gate edge belongs to a note start when it falls from one update before the row to one after it; the probe's abutting 2-update notes are two updates apart.
    onset_before: int = 1
    onset_after: int = 1
    # Longest first run of one waveform that still counts as a staged onset; a longer run is a waveform section of the sound.
    stage_max_updates: int = 4
    # Motion first visible at least this many updates after the row is delayed (a delayed vibrato, a startsAfterUpdates); earlier onsets are program setup, since pitch and tables land by update 2.
    delayed_onset_updates: int = 4
    # Deviation from the settled pitch beyond the pitch tolerance, so rounding never reads as vibrato.
    vibrato_min_words: int = 2
    # About two semitones; a larger excursion is a bend or an arpeggio step.
    vibrato_max_rel: float = 0.12
    # Frequency jumps above 4 % of the median are arpeggio steps; vibrato steps stay under 1 % in the library.
    arpeggio_jump_rel: float = 0.04
    arpeggio_min_jumps: int = 3
    arpeggio_max_distinct: int = 12
    # A bend is a monotonic frequency run this long that spans at least this fraction of the pitch.
    bend_min_run: int = 6
    bend_min_rel: float = 0.06
    # A pulse width or cutoff sequence is motion when it takes at least this many values; the note-start write plus a fixed value make two.
    table_motion_distinct: int = 3
    # Body updates sounding noise at or above this share make the body noise; a staged noise click is far below it.
    noise_share: float = 0.5
    # Compared updates after a tie; longer than the slowest vibrato delay in the library (22) plus one period.
    tie_window_updates: int = 40
    # A tie row skips one update of the pulse and filter tables, and the vibrato delay lags by two (lead.pulse-moving@1, measured 2026-10-29), so a continuing program may trail its untied control by up to this many updates.
    tie_stall_updates: int = 2
    # Updates that may still differ after the best stall.
    tie_allowed_mismatches: int = 1
    # Updates after a tie row inspected for a gate edge, TEST frame or ADSR rewrite.
    tie_inspect_updates: int = 3


T = Thresholds()

VOICE_REGISTERS = (0, 1, 2, 3, 5, 6)     # frequency, pulse width and ADSR; control (4) is compared without its gate bit
FILTER_REGISTERS = (21, 22, 23)          # cutoff low and high, resonance and routing
WAVEFORMS = ((0x10, 'triangle'), (0x20, 'saw'), (0x40, 'pulse'), (0x80, 'noise'))
MOTION_ORDER = ('pwm', 'vibrato', 'delayed-vibrato', 'pitch-bend', 'arpeggio', 'filter-sweep', 'waveform-change')


class Trace:
    """Register state of voice 1 and the shared filter after each update, as native-song frame_states returns it (SID offsets from $D400)."""

    def __init__(self, frames):
        self.frames = frames

    def register(self, update, offset):
        return self.frames[update][offset] if 0 <= update < len(self.frames) else 0

    def control(self, update):
        return self.register(update, 4)

    def gate(self, update):
        return self.control(update) & 1

    def test(self, update):
        return self.control(update) >> 3 & 1

    def waveform(self, update):
        return self.control(update) & 0xf0

    def frequency(self, update):
        return self.register(update, 0) | self.register(update, 1) << 8

    def pulse_width(self, update):
        return self.register(update, 2) | (self.register(update, 3) & 15) << 8

    def adsr(self, update):
        return self.register(update, 5), self.register(update, 6)

    def cutoff(self, update):
        return (self.register(update, 21) & 7) | self.register(update, 22) << 3

    def resonance_route(self, update):
        return self.register(update, 23)

    def mode_volume(self, update):
        return self.register(update, 24)

    def program_state(self, update):
        """Everything the program drives, without the gate bit that the score owns."""
        return tuple(self.register(update, offset) for offset in VOICE_REGISTERS + FILTER_REGISTERS) + (self.control(update) & 0xfe, self.mode_volume(update) & 0xf0)


def target_word(midi, clock_hz=clock_spec('pal').clock_hz):
    return round(440 * 2 ** ((midi - 69) / 12) * 2 ** 24 / clock_hz)


def runs(values):
    """Consecutive equal values as [value, count] pairs."""
    result = []
    for value in values:
        if result and result[-1][0] == value:
            result[-1][1] += 1
        else:
            result.append([value, 1])
    return result


def body_updates(trace, note):
    """Gated updates after the start frame, up to the score gate-off."""
    return [update for update in range(note.start + 1, note.gate_off if note.gate_off is not None else note.end) if trace.gate(update)]


def side(word, reference):
    """-1, 0 or +1 for a frequency word below, at or above the reference; the dead zone keeps rounding from reading as motion."""
    return 0 if abs(word - reference) < T.vibrato_min_words else (word > reference) - (word < reference)


def waveform_names(waveform):
    return [name for bit, name in WAVEFORMS if waveform & bit]


def sounds_at(trace, update, word):
    """A gated, non-TEST waveform frame whose frequency is the given word within the pitch tolerance."""
    return bool(trace.gate(update) and not trace.test(update) and trace.waveform(update) and abs(trace.frequency(update) - word) <= T.pitch_tolerance_words)


# --- pitch -------------------------------------------------------------------------------------------------------

def median_word(trace, note):
    """Median frequency word over the first body updates; 0 when the program has closed its gate before the body."""
    words = [trace.frequency(update) for update in body_updates(trace, note)[:T.pitch_median_updates]]
    return statistics.median(words) if words else 0


def pitch_response(trace, notes):
    """Whether the body pitch follows the score pitch, from the low, long and high notes. Returns (response, offset in semitones, facts); response is None when neither reading fits."""
    medians = {label: median_word(trace, notes[label]) for label in PITCH_NOTES}
    facts = {'medianWords': medians, 'probeMidi': {label: notes[label].midi for label in PITCH_NOTES}}
    if not all(medians.values()):
        return None, None, facts
    high_octaves = math.log2(medians['high'] / medians['long'])
    low_octaves = math.log2(medians['long'] / medians['low'])
    expected_high = (notes['high'].midi - notes['long'].midi) / 12
    expected_low = (notes['long'].midi - notes['low'].midi) / 12
    tracks = abs(high_octaves - expected_high) < T.tracking_slack_octaves and abs(low_octaves - expected_low) < T.tracking_slack_octaves
    fixed = abs(high_octaves) < T.tracking_slack_octaves and abs(low_octaves) < T.tracking_slack_octaves
    offset = round(12 * math.log2(medians['long'] / target_word(notes['long'].midi))) if tracks else None
    facts.update(octavesHighOverLong=round(high_octaves, 3), octavesLongOverLow=round(low_octaves, 3), expectedOctaves=[expected_low, expected_high],
                 tracksScorePitch=tracks, fixedPitch=fixed, offsetSemitones=offset)
    return 'absolute' if tracks else 'percussion' if fixed else None, offset, facts


def pitch_settles(trace, notes, offset):
    """Shortest note, in updates, that sounds at full pitch at every probe pitch, from the updates between a row and its first full-pitch frame. Returns (value or None, facts)."""
    if offset is None:
        return None, {'reason': 'the body pitch does not track the score pitch'}
    latencies = {}
    for label in (*PITCH_NOTES, 'reentry'):
        note = notes[label]
        word = target_word(note.midi + offset)
        latencies[label] = next((update - note.start for update in range(note.start, note.start + T.onset_search_updates) if sounds_at(trace, update, word)), None)
    short = {label: any(sounds_at(trace, update, target_word(notes[label].midi + offset)) for update in range(notes[label].start, notes[label].end)) for label in ('short2', 'short6')}
    value = None if None in latencies.values() else max(latencies.values()) + 1
    return value, {'latencyUpdates': latencies, 'shortNotesSoundFullPitch': short}


# --- note starts -------------------------------------------------------------------------------------------------

def onset(trace, note, steady, first):
    start = note.start
    edge = next((update - start for update in range(start, start + T.onset_after + 1) if trace.gate(update) and not trace.gate(update - 1)), None)
    tests = [update - start for update in range(start - T.onset_before, start + T.onset_after + 1) if trace.test(update)]
    # The first note has no predecessor: its preceding registers are still zero, so an ADSR difference there says nothing.
    restart = [] if first else [update - start for update in range(start - T.hard_restart_lookback, start) if trace.adsr(update) != steady]
    return Onset(int(trace.gate(start - 1)), edge, tests, restart)


def classify_new_note(onsets):
    """Behaviour of a new note that follows a gate-off, from the onsets of such notes."""
    if not onsets:
        return NOT_ESTABLISHED
    restarted = [bool(item.hard_restart) for item in onsets]
    if any(restarted):
        return 'hard-restart' if all(restarted) else NOT_ESTABLISHED
    edged = [item.edge is not None for item in onsets]
    if not any(edged):
        return 'legato'
    if not all(edged):
        return NOT_ESTABLISHED
    tested = [bool(item.tests) for item in onsets]
    return 'test-frame' if all(tested) else 'retrigger' if not any(tested) else NOT_ESTABLISHED


def classify_without_gate_off(onsets):
    """What a new note does to the envelope and the program when no gate-off precedes it: a fact for scoreOwned, not an interface field."""
    if not onsets or any(not item.gate_before for item in onsets):
        return NOT_ESTABLISHED
    if any(item.edge is not None for item in onsets):
        return 'envelope-restarts'
    return 'envelope-continues-with-test-frame' if all(item.tests for item in onsets) else 'envelope-continues-without-test-frame'


def new_note(trace, notes):
    steady = trace.adsr(notes['long'].start + T.steady_update)
    onsets = {label: onset(trace, notes[label], steady, first=label == 'long') for label in ('long', *AFTER_GATE_OFF, *WITHOUT_GATE_OFF)}
    after_gate_off = [onsets[label] for label in AFTER_GATE_OFF if not onsets[label].gate_before]
    facts = {'steadyAdsr': list(steady), 'onsets': {label: item._asdict() for label, item in onsets.items()},
             'onsetsFollowingGateOff': len(after_gate_off), 'withoutGateOff': classify_without_gate_off([onsets[label] for label in WITHOUT_GATE_OFF])}
    return classify_new_note(after_gate_off), facts


# --- body and motion ---------------------------------------------------------------------------------------------

def longest_monotonic_run(frequencies):
    """Length and relative span of the longest strictly rising or falling run of frequency changes."""
    best = (0, 0.0)
    length, direction = 0, 0
    for index in range(1, len(frequencies)):
        step = (frequencies[index] > frequencies[index - 1]) - (frequencies[index] < frequencies[index - 1])
        if step and step == direction:
            length += 1
            span = abs(frequencies[index] - frequencies[index - length]) / max(1, frequencies[index - length])
            if length >= best[0]:
                best = (length, span)
        else:
            length, direction = (1 if step else 0), step
    return best


def first_change(updates, reader):
    """First body update after the first one at which the register changes; the first body update carries the note's own setup write."""
    return next((update for update in updates[1:] if reader(update) != reader(update - 1)), None)


def waveform_facts(trace, note):
    """Waveform runs of one note over its gated, non-TEST updates, with the update (counted from the row) at which each run starts."""
    end = note.gate_off if note.gate_off is not None else note.end
    sounded = [update for update in range(note.start, end) if trace.gate(update) and not trace.test(update) and trace.waveform(update)]
    wave_runs = runs(trace.waveform(update) for update in sounded)
    starts, position = [], 0
    for _, count in wave_runs:
        starts.append(sounded[position] - note.start)
        position += count
    return {'runs': wave_runs, 'runStarts': starts, 'noiseShare': round(sum(1 for update in sounded if trace.waveform(update) & 0x80) / max(1, len(sounded)), 3)}


def body_facts(trace, note, reference):
    """Raw pulse, filter and pitch measurements of the sound between the start frame and the gate-off of one note; None when too few gated updates remain. Update numbers are counted from the row."""
    updates = body_updates(trace, note)
    if len(updates) <= T.table_motion_distinct:
        return None
    frequencies = [trace.frequency(update) for update in updates]
    base = statistics.median(frequencies) or 1
    reference = reference or base
    deviation = [side(word, reference) for word in frequencies]
    nonzero = [sign for sign in deviation if sign]
    jumps = [(b > a) - (b < a) for a, b in zip(frequencies, frequencies[1:]) if abs(b - a) / base > T.arpeggio_jump_rel]
    run, span = longest_monotonic_run(frequencies)
    pulse_widths, cutoffs = [trace.pulse_width(update) for update in updates], [trace.cutoff(update) for update in updates]

    def rel(update):
        return None if update is None else update - note.start

    return {
        'bodyUpdates': len(updates), 'referenceWord': reference,
        'pulseWidth': {'distinct': len(set(pulse_widths)), 'range': [min(pulse_widths), max(pulse_widths)], 'firstChange': rel(first_change(updates, trace.pulse_width))},
        'cutoff': {'distinct': len(set(cutoffs)), 'range': [min(cutoffs), max(cutoffs)], 'firstChange': rel(first_change(updates, trace.cutoff))},
        'pitch': {'maxRelDeviation': round(max(abs(word - reference) for word in frequencies) / reference, 4), 'signFlips': sum(1 for a, b in zip(nonzero, nonzero[1:]) if a != b),
                  'jumps': len(jumps), 'jumpReversals': sum(1 for a, b in zip(jumps, jumps[1:]) if a != b), 'distinct': len(set(frequencies)),
                  'monotonicRun': run, 'monotonicSpan': round(span, 3), 'firstDeviation': rel(next((update for update, sign in zip(updates, deviation) if sign), None))},
    }


def staged_onset(wave_runs):
    """True when the sound passes through one waveform for a few updates before settling on others, never returning to it."""
    return len(wave_runs) >= 2 and wave_runs[0][1] <= T.stage_max_updates and wave_runs[0][0] not in {wave for wave, _ in wave_runs[1:]}


def waveform_sequence(wave_runs):
    """Waveform names in order of first appearance, and the runs left after a staged onset."""
    names = []
    for wave, _ in wave_runs:
        names.extend(name for name in waveform_names(wave) if name not in names)
    return names, wave_runs[1:] if staged_onset(wave_runs) else wave_runs


def pitch_motions(pitch):
    """Pitch motion kinds of one body, [UNCLASSIFIED] when the pitch moves without fitting any."""
    if pitch['jumps'] >= T.arpeggio_min_jumps and pitch['jumpReversals'] >= 1 and pitch['distinct'] <= T.arpeggio_max_distinct:
        return ['arpeggio']
    kinds = []
    if pitch['signFlips'] >= 2 and pitch['maxRelDeviation'] <= T.vibrato_max_rel:
        kinds.append('vibrato')
    if pitch['monotonicRun'] >= T.bend_min_run and pitch['monotonicSpan'] >= T.bend_min_rel:
        kinds.append('pitch-bend')
    return kinds or ([UNCLASSIFIED] if pitch['firstDeviation'] is not None else [])


def delayed(update):
    return update is not None and update >= T.delayed_onset_updates


def motions(waves, body):
    """(kind, update the motion first shows) for each motion of one note, in contract order; the update is None when it cannot be told."""
    found = {}
    _, body_runs = waveform_sequence(waves['runs'])
    if body['pulseWidth']['distinct'] >= T.table_motion_distinct:
        found['pwm'] = body['pulseWidth']['firstChange']
    if body['cutoff']['distinct'] >= T.table_motion_distinct:
        found['filter-sweep'] = body['cutoff']['firstChange']
    for kind in pitch_motions(body['pitch']):
        if kind != UNCLASSIFIED:
            found['delayed-vibrato' if kind == 'vibrato' and delayed(body['pitch']['firstDeviation']) else kind] = body['pitch']['firstDeviation']
    if len(body_runs) > 1:
        found['waveform-change'] = waves['runStarts'][len(waves['runs']) - len(body_runs) + 1]
    return [(kind, found[kind]) for kind in MOTION_ORDER if kind in found]


def classify_body(waves, body):
    """Body category by priority noise > arpeggio > waveform sequence > filter > pulse > pitch bend > static; None when pitch moves in a way no category explains."""
    _, body_runs = waveform_sequence(waves['runs'])
    kinds = pitch_motions(body['pitch'])
    if waves['noiseShare'] >= T.noise_share:
        return 'noise'
    if 'arpeggio' in kinds:
        return 'arpeggio'
    if len(body_runs) > 2:
        return 'waveform-sequence'
    if body['cutoff']['distinct'] >= T.table_motion_distinct:
        return 'moving-filter'
    if body['pulseWidth']['distinct'] >= T.table_motion_distinct:
        return 'moving-pulse'
    if 'pitch-bend' in kinds:
        return 'pitch-animated'
    return None if UNCLASSIFIED in kinds else 'static'


# --- resources ---------------------------------------------------------------------------------------------------

def classify_filter(routes_voice, writes_parameters):
    """owner: the program sets cutoff or resonance and routes its voice; routed: it routes without setting them; none otherwise."""
    return 'owner' if routes_voice and writes_parameters else 'routed' if routes_voice else 'none'


def classify_coupling(ring, sync):
    """The contract holds one coupling kind; a program that sets both is not expressible, so it yields None."""
    if ring and sync:
        return None
    return {'kind': 'ring' if ring else 'sync', 'partner': 'preceding-oscillator'} if ring or sync else 'none'


def resource_facts(trace, stop):
    gated = [update for update in range(stop) if trace.gate(update)]
    return {
        'gatedUpdates': len(gated),
        'routesVoice': any(trace.resonance_route(update) & 1 for update in gated),
        'setsFilterParameters': any(trace.cutoff(update) or trace.resonance_route(update) >> 4 for update in gated),
        'ring': any(trace.control(update) & 4 for update in gated), 'sync': any(trace.control(update) & 2 for update in gated),
        'volumeNibbles': sorted({trace.mode_volume(update) & 15 for update in gated}),
        'cutoffRange': [min(trace.cutoff(update) for update in gated), max(trace.cutoff(update) for update in gated)] if gated else None,
    }


# --- release -----------------------------------------------------------------------------------------------------

def classify_after_gate_off(trace, gate_off, stop):
    """program-continues when any program-driven register changes from the gate-off update on, else release-only. Returns (value, facts)."""
    if gate_off is None or stop - gate_off < 2:
        return NOT_ESTABLISHED, {'reason': 'no observed tail after the gate-off'}
    changes = [update - gate_off for update in range(gate_off, stop) if trace.program_state(update) != trace.program_state(update - 1)]
    return 'program-continues' if changes else 'release-only', {'gateOffUpdate': gate_off, 'observedTailUpdates': stop - gate_off, 'changeCount': len(changes), 'firstChanges': changes[:6], 'lastChange': changes[-1] if changes else None}


def classify_lifetime(trace, note, stop):
    """How long the sound outlives the row, from the update at which the gate closes. Returns (value, facts).

    until-release-ends: the gate closes at the score gate-off. until-next-note: it never closes before the phrase stops.
    A program that closes its own gate or mutes its voice needs the envelope's audible end, which register states do not give.
    """
    closed = next((update for update in range(note.start + 1, stop) if not trace.gate(update)), None)
    muted = any(not trace.waveform(update) for update in body_updates(trace, note))
    facts = {'gateClosedAtUpdate': None if closed is None else closed - note.start, 'scoreGateOffUpdate': None if note.gate_off is None else note.gate_off - note.start, 'mutesWhileGated': muted}
    if muted or note.gate_off is None:
        return NOT_ESTABLISHED, facts
    if closed is None:
        return 'until-next-note', facts
    return ('until-release-ends' if closed == note.gate_off else NOT_ESTABLISHED), facts


# --- ties --------------------------------------------------------------------------------------------------------

TIE_SERIES = ('pulse width', 'filter cutoff', 'waveform', 'pitch')


def pitch_cell(frequency, reference):
    """Semitones above the reference word and the side of the nearest semitone on which the frequency lies, so vibrato and arpeggio compare across pitches."""
    if not frequency or not reference:
        return (None, 0)
    semitones = round(12 * math.log2(frequency / reference))
    return (semitones, side(frequency, reference * 2 ** (semitones / 12)))


def series_value(trace, series, update, reference):
    if series == 'pulse width':
        return trace.pulse_width(update)
    if series == 'filter cutoff':
        return trace.cutoff(update)
    if series == 'waveform':
        return trace.control(update) & 0xf6    # without the gate and TEST bits
    return pitch_cell(trace.frequency(update), reference) if reference else trace.frequency(update)


def series_window(trace, series, first, reference):
    """Values of one series over the compared updates; pulse width and cutoff as per-update steps, because their absolute values depend on the pitch."""
    values = [series_value(trace, series, first + index, reference) for index in range(T.tie_window_updates + 1)]
    return [b - a for a, b in zip(values, values[1:])] if series in ('pulse width', 'filter cutoff') else values[:-1]


def mismatches(after, hypothesis):
    """Fewest differing updates and the stall that gives them, when the tied note trails the hypothesis by at most the stall tolerance."""
    return min((sum(1 for a, b in zip(after[stall:], hypothesis) if a != b), stall) for stall in range(T.tie_stall_updates + 1))


def tie_verdict(keeps, restarts):
    """continues or restarts when that hypothesis explains the series within the tolerance and clearly better than the other; indistinct when both explain it equally; neither when none does."""
    if keeps <= T.tie_allowed_mismatches and keeps < restarts:
        return 'continues'
    if restarts <= T.tie_allowed_mismatches and restarts < keeps:
        return 'restarts'
    return 'indistinct' if keeps == restarts and keeps <= T.tie_allowed_mismatches else 'neither'


def tie_point(trace, control, first, tied, offset):
    """Compare the series after one tie with the untied control note at the same age (continue) and at its start (restart)."""
    age = tied.start - first.start
    word = (lambda note: None) if offset is None else (lambda note: target_word(note.midi + offset))
    envelope_updates = range(tied.start, tied.start + T.tie_inspect_updates + 1)
    envelope_kept = (not any(trace.gate(update) and not trace.gate(update - 1) for update in envelope_updates) and not any(trace.test(update) for update in envelope_updates)
                     and len({trace.adsr(update) for update in range(tied.start - 1, tied.start + T.tie_inspect_updates + 1)}) == 1)
    verdicts = {}
    for series in TIE_SERIES:
        span = [series_value(trace, series, update, word(control)) for update in range(control.start + 1, control.start + age + T.tie_window_updates + 2)]
        if len(set(span)) < 2:
            verdicts[series] = {'verdict': 'static'}
            continue
        after = series_window(trace, series, tied.start + 1, word(tied))
        keeps, keep_stall = mismatches(after, series_window(trace, series, control.start + age + 1, word(control)))
        restarts, restart_stall = mismatches(after, series_window(trace, series, control.start + 1, word(control)))
        verdicts[series] = {'verdict': tie_verdict(keeps, restarts), 'mismatchVsContinue': keeps, 'stallVsContinue': keep_stall, 'mismatchVsRestart': restarts, 'stallVsRestart': restart_stall}
    return {'tieUpdate': tied.start, 'ageAtTie': age, 'envelopeKept': envelope_kept, 'series': verdicts}


def classify_tie(points):
    """onTie from the tie points. A restarted envelope is a restart; otherwise every series that moves must give the same clear verdict, and a program with nothing moving keeps by the absence of any restart sign."""
    if not points:
        return NOT_ESTABLISHED
    if not all(point['envelopeKept'] for point in points):
        return 'restart-program'
    verdicts = {item['verdict'] for point in points for item in point['series'].values()}
    clear = verdicts & {'continues', 'restarts', 'neither'}
    if not clear:
        return 'keep-envelope-and-program' if verdicts == {'static'} else NOT_ESTABLISHED
    return {'continues': 'keep-envelope-and-program', 'restarts': 'restart-program'}.get(next(iter(clear)), NOT_ESTABLISHED) if len(clear) == 1 else NOT_ESTABLISHED


# --- derivation --------------------------------------------------------------------------------------------------

def measured(value, detail, **extra):
    return {'value': value, 'basis': 'measured', 'detail': f'{PROBE_ID}: {detail}', **extra}


def waveform_text(waves):
    return ', '.join(f'{"+".join(waveform_names(wave))} x{count}' for wave, count in waves['runs'])


def motion_detail(kind, onset_update, waves, body, where):
    shows = '' if onset_update is None else f', first visible {onset_update} updates after the row'
    if kind == 'pwm':
        return f'{body["pulseWidth"]["distinct"]} distinct pulse widths in {body["pulseWidth"]["range"]} over the {where}{shows}'
    if kind == 'filter-sweep':
        return f'{body["cutoff"]["distinct"]} distinct filter cutoffs in {body["cutoff"]["range"]} over the {where}{shows}'
    if kind == 'waveform-change':
        return f'the waveform changes after the onset of the {where}: {waveform_text(waves)}{shows}'
    return f'frequency deviates up to {body["pitch"]["maxRelDeviation"] * 100:.2f} % from the settled pitch over the {where}, {body["pitch"]["signFlips"]} sign flips{shows}'


def character_fields(waves, body, where):
    """Waveforms, a staged attack, body and motion of the long note; unknown, or absent for motion, where the trace cannot settle them."""
    names, _ = waveform_sequence(waves['runs'])
    character = {'waveforms': measured(names, f'waveform bits of the gated, non-TEST updates of the {where}: {waveform_text(waves)}') if names else UNKNOWN}
    if staged_onset(waves['runs']):
        (first, count), (second, _) = waves['runs'][:2]
        character['attack'] = measured('staged', f'the {where} sounds {"+".join(waveform_names(first))} for {count} update(s) before it settles on {"+".join(waveform_names(second))}')
    if body is None:
        character['body'] = UNKNOWN
        return character
    category = classify_body(waves, body)
    character['body'] = UNKNOWN if category is None else measured(
        category, f'classified from the {body["bodyUpdates"]} gated body updates of the {where}: distinct pulse widths {body["pulseWidth"]["distinct"]}, distinct cutoffs {body["cutoff"]["distinct"]}, noise share {waves["noiseShare"]}')
    character['motion'] = [measured(kind, motion_detail(kind, update, waves, body, where), **({'startsAfterUpdates': update} if delayed(update) else {})) for kind, update in motions(waves, body)]
    return character


def resource_fields(resources):
    values = {'filter': classify_filter(resources['routesVoice'], resources['setsFilterParameters']), 'masterVolume': 'none' if resources['volumeNibbles'] in ([], [PROBE_VOLUME]) else 'writes'}
    coupling = classify_coupling(resources['ring'], resources['sync'])
    if coupling is not None:
        values['coupling'] = coupling
    return values


def derive(trace, notes, stop):
    """Derive every probe-interface-v1 field from one executed phrase. Returns (fields in record shape, raw facts); a field the trace cannot settle is absent, not-established or unknown."""
    long_note = notes['long']
    response, offset, pitch_facts = pitch_response(trace, notes)
    settles, settle_facts = pitch_settles(trace, notes, offset)
    new_note_value, new_note_facts = new_note(trace, notes)
    waves = waveform_facts(trace, long_note)
    body = body_facts(trace, long_note, None if offset is None else target_word(long_note.midi + offset))
    after_gate_off, after_facts = classify_after_gate_off(trace, notes['final'].gate_off, stop)
    lifetime, lifetime_facts = classify_lifetime(trace, notes['final'], stop)
    resources = resource_facts(trace, stop)
    ties = [tie_point(trace, long_note, notes[first], notes[tied], offset) for first, tied in TIE_LEGS]
    facts = {'pitch': pitch_facts, 'pitchSettles': settle_facts, 'newNote': new_note_facts, 'waves': waves, 'body': body, 'afterGateOff': after_facts, 'lifetime': lifetime_facts, 'resources': resources, 'ties': ties}

    interface = {'onNewNote': new_note_value, 'onTie': classify_tie(ties), 'afterGateOff': after_gate_off, 'lifetime': lifetime}
    if response:
        interface['pitchResponse'] = response
    interface['pitchSettlesAfterUpdates'] = UNKNOWN if settles is None else measured(
        settles, f'the first update at full pitch is {settles - 1} after the row for every probe pitch and after a rest (update 0 is the start frame), so a note of {settles} updates sounds at its pitch')
    where = f'long note MIDI {long_note.midi}, {long_note.gate_off - long_note.start} gated updates'
    return {'interface': interface, 'character': character_fields(waves, body, where), 'resources': resource_fields(resources)}, facts


# --- execution and records ---------------------------------------------------------------------------------------

def inputs(instrument, update_hz):
    """Score and sidewizard-arrangement-v1 recipe for the probe phrase, with one beat per update."""
    score = {
        'title': 'Interface probe', 'composer': 'Probe', 'quarterBpm': 60 * update_hz, 'totalBeats': SCORE_UPDATES, 'tailTicks': TAIL_UPDATES, 'volume': PROBE_VOLUME,
        'voices': [{'name': 'probe', 'events': [{'startBeat': start, 'durationBeats': duration, 'midi': midi} for _, start, duration, midi in PHRASE]},
                   {'name': 'idle-a', 'events': []}, {'name': 'idle-b', 'events': []}]}
    starts = {label: start for label, start, _, _ in PHRASE}
    recipe = {
        'format': 'sidwizard-arrangement-v1', 'score': 'score.json', 'title': 'Interface probe', 'author': 'Probe', 'released': '2026',
        'timingPolicy': 'retain-full-pitch', 'instruments': {'probe': instrument},
        'ties': [{'voice': 'probe', 'startBeat': starts[tied]} for _, tied in TIE_LEGS],
        'sections': [{'name': 'probe', 'startBeat': 0, 'endBeat': SCORE_UPDATES, 'voices': {'probe': 'probe', 'idle-a': 'probe', 'idle-b': 'probe'}}]}
    return score, recipe


def notes_from_manifest(manifest):
    """The phrase's notes as the converter placed them; fails when the converter changed the phrase."""
    placed = manifest['voices'][0]['notes']
    if len(placed) != len(PHRASE) or any(note['midi'] != midi or note['sourceStartTick'] != start for note, (_, start, _, midi) in zip(placed, PHRASE)):
        raise ValueError('The converter changed the probe phrase; its derivations would not describe it')
    return {label: Note(note['startTick'], note['startTick'] + note['durationTicks'], note['nativeGateOffTick'], note['midi']) for (label, *_), note in zip(PHRASE, placed)}


def execute(instrument, output):
    """Convert, export and execute the probe phrase in a fresh directory. Returns (trace, notes, stop update)."""
    output = Path(output)
    output.mkdir(parents=True)
    score, recipe = inputs(instrument, clock_spec('pal').ticks_per_second)
    (output / 'score.json').write_text(json.dumps(score, indent=1) + '\n')
    (output / 'recipe.json').write_text(json.dumps(recipe, indent=1) + '\n')
    manifest = load_script('arrange-sidwizard').arrange(output / 'recipe.json', output / 'conversion')
    exported = load_script('export-sidwizard').export_module(manifest['nativePath'], output / 'export', title='Interface probe', author='Probe', sid_model='MOS8580', clock='pal')
    updates = manifest['stopTick'] + 2
    _, writes = audit_psid(Path(exported['sid']).read_bytes(), updates, clock='pal')
    frames = load_script('native-song').frame_states(writes, updates)
    (output / 'frames.json').write_text(json.dumps(frames, separators=(',', ':')) + '\n')
    return Trace(frames), notes_from_manifest(manifest), manifest['stopTick']


def probe_record(path, output):
    """Execute one library record's program on the probe phrase. Returns (record, derived fields, facts)."""
    record = json.loads(Path(path).read_text())
    directory = Path(output) / f'{record["id"]}@{record["version"]}'
    trace, notes, stop = execute(library.program_instrument(record['program'], f'{record["id"]}@{record["version"]}'), directory)
    fields, facts = derive(trace, notes, stop)
    sidecar = {'probe': PROBE_ID, 'record': f'{record["id"]}@{record["version"]}', 'thresholds': asdict(T), 'phrase': [list(note) for note in PHRASE], 'notes': {label: note._asdict() for label, note in notes.items()}, 'stopUpdate': stop, 'derived': fields, 'facts': facts}
    (directory / 'derivation.json').write_text(json.dumps(sidecar, indent=1, ensure_ascii=False) + '\n')
    return record, fields, facts


def summary(fields):
    """The derived values without their claim wrappers, for the command line."""
    def plain(value):
        return value.get('value', value['basis']) if type(value) is dict and 'basis' in value else value
    return {f'{group}.{key}': ([[item['value'], item.get('startsAfterUpdates')] for item in value] if key == 'motion' else plain(value)) for group, values in fields.items() for key, value in values.items()}


def merge(record, fields):
    """The record with exactly the derived fields replaced; every other field and the key order stay."""
    for group, values in fields.items():
        record[group].update(values)
    library.validate_record(record, ROOT)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('records', nargs='+', type=Path, help='library records whose SID-Wizard program to probe')
    parser.add_argument('--output', type=Path, required=True, help='fresh directory for probe executions and sidecars')
    parser.add_argument('--write', action='store_true', help='store the derived fields in each record; the program itself never changes')
    args = parser.parse_args()
    if args.output.exists():
        sys.exit('Probe output already exists; choose a fresh directory to preserve evidence')
    for path in args.records:
        record, fields, _ = probe_record(path, args.output)
        print(json.dumps({f'{record["id"]}@{record["version"]}': summary(fields)}))
        if args.write:
            path.write_text(json.dumps(merge(record, fields), indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
