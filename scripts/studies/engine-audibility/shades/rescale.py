"""Rescale the accepted CIA-timed Shades transfer to one driver call per PAL video frame.

The exact transfer calls its driver every 12,326 cycles (about 79.93 Hz) from CIA
Timer A. A frame-driven engine such as SID-Wizard 1.97 Extra calls once per
19,656-cycle PAL frame (about 50.12 Hz). Every count in the Shades programs and
score is measured in driver calls, so a naive reuse would stretch durations by
about 1.59. These pure functions rewrite each call-counted parameter so its
real-time duration and swept extent stay as close as integer counts allow.
Notes, pitch words, envelope codes, waveforms, fine tuning and filter ownership
are never touched.
"""

from copy import deepcopy
from fractions import Fraction
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'scripts'))

from shades_programs import FilterState, State, advance_filter  # noqa: E402
from verify_player import require  # noqa: E402


CLOCK_HZ = 985248
EXACT_PERIOD = 12326
# Timer latch $4025 gives call 0 -> 1 one longer interval (docs/validation/cia-tracing.md).
EXACT_FIRST_INTERVAL = 16422
FRAME = 19656
RHO = Fraction(EXACT_PERIOD, FRAME)
FILTER_SEARCH_RADIUS = 3
FILTER_MAX_COARSE = 8


def round_half_up(value):
    return math.floor(Fraction(value) + Fraction(1, 2))


def exact_call_cycle(call):
    return 0 if call == 0 else EXACT_FIRST_INTERVAL + (call - 1) * EXACT_PERIOD


def frame_call_cycle(call):
    return call * FRAME


def milliseconds(cycles):
    return float(Fraction(cycles) * 1000 / CLOCK_HZ)


def exact_ms(calls):
    return milliseconds(calls * EXACT_PERIOD)


def frame_ms(frames):
    return milliseconds(frames * FRAME)


def scaled_count(calls):
    """R-COUNT: nearest integer frame count for a call count; a nonzero count stays nonzero."""
    return 0 if calls == 0 else max(1, round_half_up(calls * RHO))


def percent(error, reference):
    return 0.0 if reference == 0 else float(Fraction(error) * 100 / Fraction(reference))


def rescale_pulse(voice, patch):
    """R-PULSE: scale both ramps of a pulse sweep, then rescale the step to keep the longer ramp's extent.

    A sweep of n_u ascending and n_d descending calls spends its final ascent and
    first descent in the same call (the driver tests the counter again after the
    ascent), so the audible ramps are L_u = n_u - 1 and L_d = n_d - 1 steps long.
    The shared step is the only extent control: the longer ramp keeps its
    steps x step product.
    """
    up, down, step = patch['pulse_up_calls'], patch['pulse_down_calls'], patch['pulse_step']
    require(up >= 1 or down == 0, 'Pulse rescaling requires an ascent before any descent')
    if step == 0 or (up == 0 and down == 0):
        return {}, []
    long_up, long_down = up - 1, down - 1
    new_long_up, new_long_down = round_half_up(long_up * RHO), round_half_up(long_down * RHO)
    new_up, new_down = new_long_up + 1, new_long_down + 1
    ramp, new_ramp = max(long_up, long_down), max(new_long_up, new_long_down)
    new_step = max(1, round_half_up(Fraction(ramp * step, new_ramp))) if ramp else step
    require(new_step <= 255, f'Voice {voice} pulse step {new_step} exceeds a byte')
    change = {'pulse_up_calls': new_up, 'pulse_down_calls': new_down, 'pulse_step': new_step}
    exact_end, frame_end = up + down - 1, new_up + new_down - 1
    rows = [
        row(voice, 'pulse ascent length', 'R-PULSE', 'calls', up, new_up,
            exact_ms(up), frame_ms(new_up), note='Counts include the ascent call that also starts the descent.'),
        row(voice, 'pulse descent length', 'R-PULSE', 'calls', down, new_down, exact_ms(down), frame_ms(new_down)),
        row(voice, 'pulse sweep end after note-on', 'R-PULSE', 'calls', exact_end, frame_end,
            exact_ms(exact_end), frame_ms(frame_end), note='Sweep ends in call n_u + n_d - 1; each ramp keeps its own rounding.'),
        row(voice, 'pulse step', 'R-PULSE', 'units per call', step, new_step, None, None,
            extent_exact=ramp * step, extent_frame=new_ramp * new_step,
            note=f'Longer ramp excursion: {ramp} steps x {step} -> {new_ramp} steps x {new_step}.'),
    ]
    return change, rows


def rescale_vibrato(voice, patch):
    """R-DELAY and R-VIBRATO: scale the delay by count; choose the extent whose cycle is nearest, then the step."""
    extent, step, delay = patch['vibrato_extent'], patch['vibrato_step'], patch['vibrato_delay']
    if extent == 0 or step == 0:
        return {}, []
    require(patch['portamento_step'] == 0, 'Vibrato rescaling does not model portamento flags in the delay count')
    new_delay = scaled_count(delay)
    # One cycle is `extent` rising writes, one turn call without a write and `extent` falling writes.
    cycle = 2 * extent + 1
    new_extent = max(1, round_half_up((cycle * RHO - 1) / 2))
    new_step = max(1, round_half_up(Fraction(extent * step, new_extent)))
    require(new_step <= 255, f'Voice {voice} vibrato step {new_step} exceeds a byte')
    new_cycle = 2 * new_extent + 1
    change = {'vibrato_delay': new_delay, 'vibrato_extent': new_extent, 'vibrato_step': new_step}
    rows = [
        row(voice, 'vibrato delay', 'R-COUNT', 'calls', delay, new_delay, exact_ms(delay), frame_ms(new_delay)),
        row(voice, 'vibrato extent', 'R-VIBRATO', 'steps per half cycle', extent, new_extent, None, None,
            note=f'Cycle = 2 x extent + 1 driver calls: {cycle} -> {new_cycle}.'),
        row(voice, 'vibrato cycle', 'R-VIBRATO', 'calls', cycle, new_cycle, exact_ms(cycle), frame_ms(new_cycle)),
        row(voice, 'vibrato step', 'R-VIBRATO', 'frequency units per call', step, new_step, None, None,
            extent_exact=extent * step, extent_frame=new_extent * new_step,
            note=f'Peak-to-peak excursion: {extent} x {step} -> {new_extent} x {new_step}. The two subtractions at delay expiry become 2 x {new_step}.'),
    ]
    return change, rows


def contour_trajectory(contour, calls, coarse, fine):
    """Return the 11-bit cutoff after each call, using the project's own filter stepping."""
    state = State()
    filt = state.filter
    filt.cutoff_low, filt.cutoff_high = contour['cutoff_low'], contour['cutoff_high']
    filt.up_calls, filt.down_calls = 0, calls
    filt.fine_step, filt.coarse_step = fine, coarse
    values = [(filt.cutoff_high << 3) | (filt.cutoff_low & 7)]
    for _ in range(calls):
        advance_filter(state)
        values.append((filt.cutoff_high << 3) | (filt.cutoff_low & 7))
    return values


def rescale_filter(contour):
    """R-FILTER: pick the call count and fine/coarse pair minimising the larger relative error.

    The driver subtracts a fine step (0..7) and borrows one coarse step from the
    high byte, so a per-call drop other than 0..7 or a multiple of 8 alternates
    between two sizes. A search over counts near the nearest-integer scale and
    over representable pairs, scored on the simulated 11-bit cutoff, keeps both
    the sweep time and its total drop close.
    """
    require(contour['up_calls'] == 0 and contour['down_calls'] > 0, 'Filter rescaling supports one descending contour')
    calls = contour['down_calls']
    exact_path = contour_trajectory(contour, calls, contour['coarse_step'], contour['fine_step'])
    exact_drop = exact_path[0] - exact_path[-1]
    require(exact_drop > 0, 'Filter contour does not descend')
    centre = scaled_count(calls)
    best = None
    for new_calls in range(max(1, centre - FILTER_SEARCH_RADIUS), centre + FILTER_SEARCH_RADIUS + 1):
        for coarse in range(1, FILTER_MAX_COARSE + 1):
            for fine in range(0, 8):
                path = contour_trajectory(contour, new_calls, coarse, fine)
                drop = path[0] - path[-1]
                if drop <= 0 or any(b > a for a, b in zip(path, path[1:])):
                    continue
                time_error = abs(Fraction(new_calls * FRAME - calls * EXACT_PERIOD, calls * EXACT_PERIOD))
                extent_error = abs(Fraction(drop - exact_drop, exact_drop))
                key = (max(time_error, extent_error), time_error, coarse, -fine)
                if best is None or key < best[0]:
                    best = (key, new_calls, coarse, fine, drop)
    _, new_calls, coarse, fine, drop = best
    change = {'down_calls': new_calls, 'fine_step': fine, 'coarse_step': coarse}
    rows = [
        row('filter', 'cutoff sweep length after voice-3 note-on', 'R-FILTER', 'calls', calls, new_calls,
            exact_ms(calls), frame_ms(new_calls)),
        row('filter', 'cutoff fine step', 'R-FILTER', '11-bit cutoff units', contour['fine_step'], fine, None, None),
        row('filter', 'cutoff coarse step', 'R-FILTER', 'high-byte units', contour['coarse_step'], coarse, None, None,
            extent_exact=exact_drop, extent_frame=drop,
            note='Total simulated cutoff drop in 11-bit units; the fine/coarse pair cannot express every per-call step uniformly.'),
    ]
    return change, rows


def row(scope, parameter, rule, unit, exact, frame, exact_time_ms, frame_time_ms, *,
        extent_exact=None, extent_frame=None, note=None):
    entry = {'scope': scope, 'parameter': parameter, 'rule': rule, 'unit': unit, 'exact': exact, 'frame': frame}
    if exact_time_ms is not None:
        entry.update(exactMs=round(exact_time_ms, 3), frameMs=round(frame_time_ms, 3),
                     errorMs=round(frame_time_ms - exact_time_ms, 3),
                     errorPercent=round(percent(frame_time_ms - exact_time_ms, exact_time_ms), 3))
    if extent_exact is not None:
        entry.update(extentExact=extent_exact, extentFrame=extent_frame, extentErrorUnits=extent_frame - extent_exact,
                     extentErrorPercent=round(percent(extent_frame - extent_exact, extent_exact), 3))
    if note:
        entry['note'] = note
    return entry


def rescale_block(block):
    """Return the frame-rate copy of one program block and its per-parameter table."""
    result, table = deepcopy(block), []
    for index, patch in enumerate(result['voices']):
        voice = f'voice {index + 1}'
        require(patch['portamento_step'] == 0, f'{voice} enables portamento; glide blocks are outside this comparison')
        for change, rows in (rescale_pulse(voice, patch), rescale_vibrato(voice, patch)):
            patch.update(change)
            table.extend(rows)
    contour = result['filter']['contour']
    change, rows = rescale_filter(contour)
    contour.update(change)
    table.extend(rows)
    # Percussion contour and its mode are unreachable while percussion_control is zero.
    require(result['percussion_control'] == 0, 'Percussion paths are outside this comparison')
    return result, table


def rescale_orders(orders):
    """R-ROW and R-RELEASE: place every row boundary on the frame nearest the exact boundary time.

    A one-row order starts at an absolute exact call; its frame boundary is the
    nearest frame to that call's time, so rounding never accumulates. A multi-row
    order keeps a uniform row length, scaled by R-COUNT, with `rowInterval` and
    `rowCount` unchanged so the fade still reaches zero before the stop.
    """
    result, table = deepcopy(orders), []
    exact_cursor, frame_cursor = 1, 1
    for index, order in enumerate(result):
        rows, duration = order['rowCount'], order['rowDurationCalls']
        next_exact = exact_cursor + rows * duration
        if rows == 1:
            nearest = round_half_up(Fraction(exact_call_cycle(next_exact), FRAME))
            next_frame = max(frame_cursor + 1, nearest)
            new_duration = next_frame - frame_cursor
        else:
            new_duration = scaled_count(duration)
            next_frame = frame_cursor + rows * new_duration
        order['rowDurationCalls'] = new_duration
        order['instrument'] = order['instrument'] + '-frame'
        table.append({'orderIndex': index, 'rows': rows,
                      'exactStartCall': exact_cursor, 'frameStartCall': frame_cursor,
                      'exactStartMs': round(milliseconds(exact_call_cycle(exact_cursor)), 3),
                      'frameStartMs': round(milliseconds(frame_call_cycle(frame_cursor)), 3),
                      'startErrorMs': round(milliseconds(frame_call_cycle(frame_cursor) - exact_call_cycle(exact_cursor)), 3),
                      'exactRowCalls': duration, 'frameRowCalls': new_duration})
        exact_cursor, frame_cursor = next_exact, next_frame
    return result, table, exact_cursor, frame_cursor


def rescale_score(score):
    """Return the frame-rate score; ranges and timing evidence describe the new cadence."""
    result = deepcopy(score)
    orders, table, exact_stop, frame_stop = rescale_orders(score['orders'])
    require(exact_stop == score['range']['stopCall'], 'Exact score range disagrees with its row timing')
    result['orders'] = orders
    result['instrumentBlocks'] = [name + '-frame' for name in score['instrumentBlocks']]
    result['range'] = {'firstCall': 0, 'firstRowCall': 1, 'lastCallInclusive': frame_stop - 1,
                       'stopCall': frame_stop, 'cycleCalls': frame_stop - 1}
    return result, table


RULES = [
    {'id': 'R-COUNT', 'applies': 'Vibrato delay; release row length',
     'rule': 'frames = round-half-up(calls x 12326 / 19656); a nonzero count never becomes zero.'},
    {'id': 'R-ROW', 'applies': 'Row lengths of the 48 one-row orders',
     'rule': 'Each row boundary is the frame nearest the exact transfer\'s own boundary time (call 1 = 16,422 cycles, then 12,326 per call). Rounding is absolute, so errors never accumulate; a row lasts 10 or 11 frames.'},
    {'id': 'R-RELEASE', 'applies': 'Final 32-row release and fade',
     'rule': 'Row length 5 calls -> 3 frames (R-COUNT); rowCount 32 and the two-row fade interval are unchanged, so the master volume still reaches zero before the authored stop and each volume step lasts 6 frames.'},
    {'id': 'R-PULSE', 'applies': 'Pulse sweep counts and step per voice',
     'rule': 'Ramp lengths L = count - 1 (the last ascent and first descent share a call) are scaled by R-COUNT and the counts restored as L + 1. The shared step is rescaled so the longer ramp keeps its steps x step excursion, rounded half up.'},
    {'id': 'R-VIBRATO', 'applies': 'Voice 3 vibrato extent and step',
     'rule': 'A cycle lasts 2 x extent + 1 calls. The extent whose cycle is nearest 17 x 12326 cycles is chosen, then the step is the nearest integer keeping extent x step.'},
    {'id': 'R-FILTER', 'applies': 'Shared filter contour (voice-3 triggered)',
     'rule': 'Search call counts within 3 of the nearest-integer scale and every fine (0..7) / coarse (1..8) pair on the simulated 11-bit cutoff; pick the pair minimising the larger of relative duration error and relative total-drop error, then the smaller duration error, then the smaller coarse step.'},
    {'id': 'UNCHANGED', 'applies': 'Notes, pitch words, ADSR codes, waveforms, initial pulse widths, fine tuning, filter routing/mode/trigger/start cutoff, portamento (disabled), fade interval and row count, inert percussion contour',
     'rule': 'Copied verbatim. Only the cadence-dependent counts and per-call steps listed above change.'},
]
