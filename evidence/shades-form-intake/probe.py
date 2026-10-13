"""Bounded, pinned score-structure observation; no CIA scheduler or reconstruction."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / '.tools/test-deps'))
from psid_audit import AuditMemory
from py65.devices.mpu6502 import MPU
from verify_player import require


SOURCE = ROOT / '.local/research/shades/Shades_filter_corrected.sid'
PIN = 'ac7c91d0c4fef41bbc9d9e50840492269151075727efa7182a68dc1a26f1d708'
OUTPUT = ROOT / 'build/shades-form-intake'
PLAY_CALLS = 48770


def word(memory, address):
    return memory[address] | memory[address + 1] << 8


class DiagnosticMemory(AuditMemory):
    def __init__(self):
        super().__init__()
        self.cpu = None
        self.pc = None
        self.cia_writes = []
        self.io_reads = []
        self.flag_writes = []

    def __getitem__(self, address):
        if 0xd000 <= address <= 0xdfff:
            self.io_reads.append({'call': self.tick, 'pc': self.pc, 'address': address})
        return super().__getitem__(address)

    def __setitem__(self, address, value):
        if address == 0xdc05:
            require(self.phase == 'play' and self.pc == 0x7852 and self.instruction == 'STA'
                    and bytes(self.data[self.pc:self.pc + 3]) == b'\x8d\x05\xdc',
                    'Only pinned STA $DC05 at $7852 is diagnostic-only')
            info = word(self.data, 0xab)
            operand = info + self.cpu.y
            require(self.data[operand] == value, 'CIA value must match consumed pattern operand')
            self.cia_writes.append({'call': self.tick, 'pc': self.pc, 'info': info,
                                    'sourceAddress': operand, 'value': value})
            self.data[address] = value
            return
        if address in (0x033c, 0x033d, 0x033e, 0x0342, 0x036f, 0x0377, 0x0378, 0x0379):
            self.flag_writes.append({'call': self.tick, 'pc': self.pc, 'address': address,
                                    'before': self.data[address], 'value': value})
        super().__setitem__(address, value)


data = SOURCE.read_bytes()
require(hashlib.sha256(data).hexdigest() == PIN, 'Pinned source differs')
offset = int.from_bytes(data[6:8], 'big')
base = int.from_bytes(data[offset:offset + 2], 'little')
payload = data[offset + 2:]
memory = DiagnosticMemory()
memory.data[base:base + len(payload)] = payload
cpu = MPU(memory=memory)
cpu.a = cpu.x = cpu.y = 0
memory.cpu = cpu

inventory = []
for slot in range(128):
    pattern = memory.data[0x5580 + slot]
    ptrs = [word(memory.data, bank + pattern * 2) for bank in (0x5000, 0x5100, 0x5200, 0x5300)]
    require(pattern == slot and all(base <= pointer < base + len(payload) for pointer in ptrs),
            'Observed inventory must retain pinned identity order and in-payload pointers')
    info = ptrs[3]
    inventory.append({'slot': slot, 'orderSourceAddress': 0x5580 + slot, 'pattern': pattern,
                      'voicePatternPointers': ptrs[:3], 'infoPointer': info,
                      'rowLimit': memory.data[info + 0x32], 'timerHigh': memory.data[info + 14],
                      'fadeCommand': memory.data[info + 63],
                      'transposes': [memory.data[bank + slot] for bank in (0x5400, 0x5480, 0x5500)]})

selections, rows, wraps, fade_steps = [], [], [], []
per_call_state, cycle_costs = [], []
counts = Counter()
selected = None
sound_write_count = 0


def snapshot():
    m = memory.data
    return {'restartFlag': m[0x033c], 'playingFlag': m[0x033d], 'advanceFlag': m[0x033e],
            'nextOrder': m[0x033f], 'rowIndex': m[0x0340], 'rowCounter': m[0x0341],
            'rowReload': m[0x0342], 'transposes': m[0x0343:0x0346], 'rowLimit': m[0x036f],
            'previousRows': m[0x0371:0x0374], 'fade': m[0x0377:0x037a],
            'activePointers': [word(m, address) for address in (0xa5, 0xa7, 0xa9, 0xab)]}


def call(address):
    global selected, sound_write_count
    cpu.stPushWord(0x01ff)
    cpu.pc = address
    start = cpu.processorCycles
    while cpu.pc != 0x0200:
        require(cpu.processorCycles - start < 100000, 'Bounded diagnostic call does not return')
        memory.pc = cpu.pc
        memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
        memory.instruction_cycle = cpu.processorCycles - start
        require(memory.instruction not in ('???', 'BRK', 'RTI'), 'Unsupported executed opcode')
        counts[cpu.pc] += 1
        if cpu.pc == 0x77e9:
            slot = cpu.x
            selected = inventory[slot]
            selections.append({'call': memory.tick, **selected})
            if slot == 0 and memory.tick:
                wraps.append(memory.tick)
        if cpu.pc == 0x748b:
            m = memory.data
            state = snapshot()
            row = m[0x0340]
            pointers = state['activePointers'][:3]
            require(pointers == selected['voicePatternPointers'] and
                    state['activePointers'][3] == selected['infoPointer'],
                    'Live row operands disagree with executed selection')
            source_addresses = [pointer + row for pointer in pointers]
            consumed = [m[address] for address in source_addresses]
            signature = hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
            rows.append({'call': memory.tick, 'slot': selected['slot'], 'row': row,
                         'sourceAddresses': source_addresses, 'bytes': consumed,
                         'scoreState': state, 'scoreStateSha256': signature})
        if cpu.pc == 0x78dc:
            fade_steps.append({'call': memory.tick, 'value': cpu.a, 'fadeState': memory.data[0x0377:0x037a]})
        cpu.step()
    require(cpu.sp == 255, 'Callable stack mismatch')
    sound_write_count += len(memory.writes)
    memory.writes.clear()
    return cpu.processorCycles - start


init_cycles = call(0x7000)
memory.phase = 'play'
for tick in range(PLAY_CALLS):
    memory.tick = tick
    cycle_costs.append(call(0x742e))
    per_call_state.append({'call': tick, 'nextOrder': memory.data[0x033f],
                           'rowIndex': memory.data[0x0340], 'rowCounter': memory.data[0x0341],
                           'fade': memory.data[0x0377:0x037a], 'playing': memory.data[0x033d]})
    if tick and tick % 10000 == 0:
        print('Observed calls', tick, 'selections', len(selections), 'rows', len(rows), flush=True)

require(not memory.io_reads, 'No I/O reads or stubs are permitted')
require(len(wraps) >= 2 and wraps[1] - wraps[0] == 24384, 'Observed wrap differs from structural prediction')
period = wraps[1] - wraps[0]
by_call = {row['call']: row for row in rows}
matched, initial_differences = 0, []
for row in rows:
    following = by_call.get(row['call'] + period)
    if following is None:
        continue
    require((row['slot'], row['row'], row['sourceAddresses'], row['bytes']) ==
            (following['slot'], following['row'], following['sourceAddresses'], following['bytes']),
            'Consumed score row fails structural period')
    if row['scoreState'] != following['scoreState']:
        initial_differences.append({'firstCall': row['call'], 'followingCall': following['call'],
                                   'differentFields': {key: [row['scoreState'][key], following['scoreState'][key]]
                                                       for key in row['scoreState']
                                                       if row['scoreState'][key] != following['scoreState'][key]}})
    else:
        matched += 1

info_blocks = []
for address in sorted({entry['infoPointer'] for entry in inventory}):
    entries = [entry for entry in inventory if entry['infoPointer'] == address]
    info_blocks.append({'address': address, 'bytes': memory.data[address:address + 64],
                        'slots': [entry['slot'] for entry in entries], 'rowLimits': sorted({entry['rowLimit'] for entry in entries}),
                        'timerHighs': sorted({entry['timerHigh'] for entry in entries}),
                        'fadeCommands': sorted({entry['fadeCommand'] for entry in entries})})

summary = {'classification': 'Pinned score-structure diagnostic only; not production audit or CIA emulation',
           'source': {'path': str(SOURCE), 'sha256': PIN, 'load': base, 'init': 0x7000, 'play': 0x742e},
           'probeSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'generatedUtc': datetime.now(timezone.utc).isoformat(), 'playCalls': PLAY_CALLS,
           'initCycles': init_cycles, 'maximumPlayCycles': max(cycle_costs), 'soundWritesCountedNotRetained': sound_write_count,
           'allowedAdditionalIo': {'write': {'pc': 0x7852, 'address': 0xdc05, 'source': 'live ($AB),Y pattern operand'}, 'read': []},
           'ioReads': memory.io_reads, 'ciaWrites': memory.cia_writes,
           'inventory': inventory, 'patternInfoBlocks': info_blocks, 'selections': selections,
           'rowCount': len(rows), 'rowCalls': {'first': rows[0]['call'], 'last': rows[-1]['call']},
           'wrapCalls': wraps, 'scorePeriodCalls': period, 'rowsPerPeriod': sum(entry['rowLimit'] for entry in inventory),
           'comparison': {'matchingConsumedRows': matched + len(initial_differences),
                          'matchingRelevantScoreStates': matched, 'scoreStateDifferences': initial_differences},
           'fadeSteps': fade_steps, 'flagWrites': memory.flag_writes,
           'executedPcCounts': {f'{pc:04x}': count for pc, count in sorted(counts.items())},
           'boundaries': {'noElapsedSeconds': True, 'noInstrumentReconstruction': True,
                          'noTrackedChanges': True, 'noPlaybackReplacement': True},
           'limitations': 'All call numbers are explicit diagnostic invocations. Structural row/pointer/counter and fade evidence is not oscillator/envelope/analog state recurrence, native CIA timing, listening or editor-file compatibility.'}
for name, content in (('summary.json', summary), ('rows.json', rows), ('call-state.json', per_call_state)):
    with (OUTPUT / name).open('x') as handle:
        json.dump(content, handle, indent=2)
        handle.write('\n')
require(hashlib.sha256(SOURCE.read_bytes()).hexdigest() == PIN, 'Original file changed during probe')
try:
    AuditMemory()[0xdc05] = 48
except ValueError:
    pass
else:
    raise ValueError('Production memory guard changed')
print(json.dumps({'wrapCalls': wraps, 'period': period, 'rows': len(rows), 'scoreStateDifferenceCount': len(initial_differences),
                  'firstScoreStateDifferences': initial_differences[:2],
                  'fadeSteps': fade_steps, 'infoBlocks': len(info_blocks), 'maxCycles': max(cycle_costs)}, indent=2), flush=True)
