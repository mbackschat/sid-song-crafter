from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
from flashdance_compiler_test import fixture, identity
from flashdance_player import compute_writes
from psid_audit import AuditMemory, audit_psid
from verify_player import cpu_type


def load_script(filename, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


dual = load_script('compose-flashdance-dual.py', 'compose_flashdance_dual')
single = load_script('compose-flashdance.py', 'dual_single_compiler')


def descriptions():
    primary, secondary = fixture(), fixture()
    secondary['programs']['filter_owner'] = 2
    secondary['preloaded']['filter_owner'] = 2
    secondary['programs']['instruments']['0']['filter_command'] = 0
    secondary['programs']['instruments']['24']['filter_command'] = 0xb1
    secondary['initialRouting'] = 0
    secondary['initialVolume'] = 11
    secondary['programs']['filter_rows']['0']['step'] = 7
    secondary['preloaded']['filter']['cutoff'] = 83
    secondary['programs']['pwm_rows']['1']['step'] = 35
    for role in secondary['score']['roles'].values():
        for command in role['commands']:
            if command['kind'] == 'note':
                command['sourceNote'] += 3
    return primary, secondary


def expected_writes(primary, secondary, calls):
    voices = [compute_writes(description, calls=calls) for description in (primary, secondary)]
    result = []
    for tick in [None] + list(range(calls)):
        for bank, rows in enumerate(voices):
            for row in rows:
                if row['tick'] == tick:
                    result.append(dict(row, address=row['address'] + bank * 32))
    return result


def run_twice(sid, calls):
    load, init, play = (int.from_bytes(sid[index:index + 2], 'big') for index in (8, 10, 12))
    memory = AuditMemory((0xd400, 0xd420))
    memory.data[load:load + len(sid) - 124] = sid[124:]
    cpu = cpu_type()(memory=memory)
    result = []

    def call(address):
        cpu.stPushWord(0x01ff)
        cpu.pc = address
        first_cycle = cpu.processorCycles
        while cpu.pc != 0x0200:
            if cpu.processorCycles - first_cycle > 19656:
                raise AssertionError('Dual player exceeds the shared PAL frame')
            memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
            memory.instruction_cycle = cpu.processorCycles - first_cycle
            cpu.step()
        if cpu.sp != 255:
            raise AssertionError('Dual player corrupts the call stack')

    for _ in range(2):
        start = len(memory.writes)
        memory.phase, memory.tick = 'init', None
        call(init)
        memory.data[0xfb:0xfd] = [0xa7, 0x5c]
        memory.phase = 'play'
        for tick in range(calls):
            memory.tick = tick
            call(play)
            if memory.data[0xfb:0xfd] != [0xa7, 0x5c]:
                raise AssertionError('Dual player fails to preserve $FB/$FC')
        result.append(memory.writes[start:])
    return result


class FlashdanceDualCompilerTest(unittest.TestCase):
    def test_independent_chips_filters_and_endings_match_ordered_parallel_models(self):
        primary, secondary = descriptions()
        sid, built = dual.build(primary, secondary)
        report, actual = audit_psid(sid, 431)
        self.assertEqual(identity(expected_writes(primary, secondary, 431)), identity(actual))
        self.assertEqual((3, 0x54), tuple(int.from_bytes(sid[index:index + 2], 'big') for index in (4, 118)))
        self.assertEqual(bytes((0x42, 0)), sid[122:124])
        self.assertEqual(2, report['sidCount'])
        self.assertLessEqual(report['maximumPlayCycles'], 19656)
        players = built['players']
        self.assertLessEqual(players[0]['loadAddress'] + players[0]['payloadBytes'], players[1]['loadAddress'])
        self.assertLessEqual(players[1]['loadAddress'] + players[1]['payloadBytes'], 0xa000)
        silent = [(row['address'], row['value']) for row in actual if row['phase'] == 'play' and row['tick'] == 428]
        self.assertEqual([(base + offset, 0) for base in (0xd400, 0xd420) for offset in (4, 11, 18, 24)], silent)

    def test_editing_secondary_pitch_and_pulse_leaves_primary_values_unchanged(self):
        primary, secondary = descriptions()
        sid, _ = dual.build(primary, secondary)
        _, before = audit_psid(sid, 40)
        changed = deepcopy(secondary)
        changed['score']['roles']['lead']['commands'][1]['sourceNote'] += 2
        changed['programs']['pwm_rows']['1']['step'] += 5
        edited, _ = dual.build(primary, changed)
        _, after = audit_psid(edited, 40)
        bank = lambda rows, base: identity([row for row in rows if base <= row['address'] <= base + 24])
        self.assertEqual(bank(before, 0xd400), bank(after, 0xd400))
        self.assertNotEqual(bank(before, 0xd420), bank(after, 0xd420))
        self.assertEqual(identity(expected_writes(primary, changed, 40)), identity(after))

    def test_reinitialization_restores_both_engines_and_zero_page(self):
        primary, secondary = descriptions()
        sid, _ = dual.build(primary, secondary)
        first, second = run_twice(sid, 32)
        expected = identity(expected_writes(primary, secondary, 32))
        self.assertEqual(expected, identity(first))
        self.assertEqual(expected, identity(second))

    def test_mismatched_stop_ending_and_profiles_are_rejected(self):
        for field, change in (
            ('stop', lambda value: value['score']['range'].update(stopCall=301)),
            ('ending', lambda value: value['ending'].update(releaseCalls=65)),
            ('profile', lambda value: value['score']['profile'].update(chip='MOS8580')),
        ):
            with self.subTest(field=field):
                primary, secondary = descriptions()
                change(secondary)
                with self.assertRaisesRegex(ValueError, 'profile|stop|ending'):
                    dual.build(primary, secondary)

    def test_default_single_sid_export_remains_byte_identical(self):
        description = json.loads((ROOT / 'songs/flashdance-decoded.json').read_text())
        sid, _ = single.build(description)
        self.assertEqual('2e05683534fdbef75c6ac2ea3b55496b1a9b3a81a68d86ebbc516531a8cf912b',
                         hashlib.sha256(sid).hexdigest())

    def test_two_large_valid_scores_cannot_overrun_callable_ram(self):
        primary, secondary = descriptions()
        for description in (primary, secondary):
            for role in description['score']['roles'].values():
                role['commands'] = [{'call': 0, 'kind': 'hold', 'durationCalls': 4} for _ in range(1300)] + role['commands']
        with self.assertRaisesRegex(ValueError, 'RAM'):
            dual.build(primary, secondary)

    def test_malformed_score_shapes_are_rejected_before_pair_comparison(self):
        for side in (0, 1):
            for field in ('score', 'range'):
                with self.subTest(side=side, field=field):
                    pair = list(descriptions())
                    if field == 'score':
                        pair[side]['score'] = None
                    else:
                        pair[side]['score']['range'] = None
                    with self.assertRaises(ValueError):
                        dual.build(*pair)
                    with self.assertRaises(ValueError):
                        dual.compute_writes(*pair, calls=1)

    def test_two_individually_valid_workloads_exceeding_one_shared_frame_are_not_exported(self):
        primary = fixture()
        for role in primary['score']['roles'].values():
            extra = [{'call': 8, 'kind': 'hold', 'durationCalls': 4} for _ in range(50)]
            role['commands'] = role['commands'][:4] + extra + role['commands'][4:]
        secondary = deepcopy(primary)
        for description in (primary, secondary):
            sid, _ = single.build(description)
            report, _ = audit_psid(sid, 9)
            self.assertGreater(report['maximumPlayCycles'], 19656 // 2)
            self.assertLessEqual(report['maximumPlayCycles'], 19656)
        with tempfile.TemporaryDirectory(prefix='flashdance-dual-budget-') as directory:
            directory = Path(directory)
            paths = [directory / name for name in ('primary.json', 'secondary.json')]
            for path, description in zip(paths, (primary, secondary)):
                path.write_text(json.dumps(description))
            output = directory / 'export'
            with self.assertRaisesRegex(ValueError, '19656-cycle call budget'):
                dual.run(*paths, output, calls=9)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
