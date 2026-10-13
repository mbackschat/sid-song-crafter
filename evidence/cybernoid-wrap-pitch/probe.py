"""Observe named pitch state around the first intact Cybernoid title wrap."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid


SOURCE = ROOT / '.local/research/cybernoid-ii/Cybernoid_II.sid'
SOURCE_SHA = '41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192'
FIELDS = {
    'order_cursor': 0xa62d, 'pattern_cursor': 0xa630, 'row_countdown': 0xa633,
    'duration_reload': 0xa636, 'pitch_index': 0xa63c, 'base_pitch': 0xa63f,
    'sound_index': 0xa642, 'held_frequency_high': 0xa645, 'held_frequency_low': 0xa64b,
    'glide_enabled': 0xa64e, 'glide_active': 0xa651, 'note_age': 0xa65e,
    'pitch_offset': 0xa661, 'vibrato_extent': 0xa664, 'vibrato_direction': 0xa667,
    'vibrato_position': 0xa66a, 'repeat_count': 0xa684,
    'glide_target': 0xa68d, 'glide_parameters': 0xa690,
    'frequency_low': 0xa693, 'frequency_high': 0xa696, 'vibrato_age': 0xa6a8,
}
STATE_HOOKS = {0xa75f, 0xa76a, 0xa7af, 0xaa20, 0xaa43, 0xaa85, 0xab87, 0xae2c}
MATH_HOOKS = {0xaa20, 0xaa23, 0xaa25, 0xaa2f, 0xaa35, 0xaa43, 0xaa46,
              0xaa4b, 0xaa58, 0xaa5b, 0xaa62, 0xaa6f, 0xaa78, 0xaa85, 0xaa89, 0xae11}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    data = SOURCE.read_bytes()
    assert hashlib.sha256(data).hexdigest() == SOURCE_SHA
    states, arithmetic = [], []

    def observe(cpu, memory):
        if memory.phase != 'play':
            return
        tick, pc = memory.tick, cpu.pc
        if pc == 0xa603 and tick % 2048 == 0:
            print('call', tick, flush=True)
        if not (0 <= tick <= 20 or 17280 <= tick <= 17300):
            return
        if pc in STATE_HOOKS and (cpu.x == 0 or pc == 0xae2c):
            states.append(dict(call=tick, pc=pc, instructionStartCycle=memory.instruction_cycle,
                               a=cpu.a, x=cpu.x, y=cpu.y, status=cpu.p,
                               state={name: memory.data[address:address + 3] for name, address in FIELDS.items()}))
        if tick in (13, 17293) and cpu.x == 0 and pc in MATH_HOOKS:
            arithmetic.append(dict(call=tick, pc=pc, instructionStartCycle=memory.instruction_cycle,
                                   a=cpu.a, x=cpu.x, y=cpu.y, status=cpu.p,
                                   vibrato_direction=memory.data[0xa667], vibrato_position=memory.data[0xa66a],
                                   delta=memory.data[0x4f] | memory.data[0x4e] << 8,
                                   working_frequency=memory.data[0x4c] | memory.data[0x4d] << 8))

    audit, writes = audit_psid(data, 17301, subtune=1, profile='pal-banked', observer=observe)
    selected = [row for row in writes if row['phase'] == 'play' and
                (0 <= row['tick'] <= 20 or 17280 <= row['tick'] <= 17300)]
    result = dict(schemaVersion=1, classification='Read-only named-state and arithmetic observer; not a reconstruction',
                  sourceSha256=SOURCE_SHA, selectedSubtune=1, executionProfile='pal-banked', playCalls=17301,
                  windows=[[0, 20], [17280, 17300]], namedStateAddresses=FIELDS,
                  stateHooks=sorted(STATE_HOOKS), arithmeticHooks=sorted(MATH_HOOKS),
                  stateSnapshots=states, arithmetic=arithmetic, orderedWindowSidWrites=selected,
                  audit={name: audit[name] for name in ('initCycles', 'maximumPlayCycles', 'initWriteCount', 'playWriteCount')},
                  tools={name: digest(ROOT / 'scripts' / name) for name in
                         ('psid_audit.py', 'psid_profile.py', 'verify_player.py')}, probeSha256=digest(Path(__file__)),
                  limitations='Only the two declared windows retain named state/hooks. Original source is unchanged. Standard guarded CPU audit executes every preceding call; no I/O/ROM guard change, instruction dump, bus timing, SID-state, PCM or listening claim.')
    output = Path(__file__).with_name('observations.json')
    with output.open('x') as target:
        json.dump(result, target, separators=(',', ':'))
        target.write('\n')
    print('saved', output, 'states', len(states), 'math', len(arithmetic), 'writes', len(selected), flush=True)


if __name__ == '__main__':
    run()
