import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_player import cpu_type
from shades_player import compute
from shades_audit import audit_candidate


def compiler():
    spec = importlib.util.spec_from_file_location('compose_shades', ROOT / 'scripts/compose-shades.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def identity(rows):
    return [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]


def execute(sid, calls, *, restart=False):
    class Memory:
        def __init__(self):
            self.data = [0] * 65536
            self.writes = []
            self.tick = None
            self.phase = 'init'

        def __getitem__(self, address):
            if 0xd000 <= address <= 0xdfff or address >= 0xa000:
                raise ValueError('Unexpected I/O or ROM read')
            return self.data[address]

        def __setitem__(self, address, value):
            if 0xd000 <= address <= 0xdfff:
                if not (0xd400 <= address <= 0xd418 or address == 0xdc05):
                    raise ValueError('Unexpected I/O write')
                self.writes.append(dict(phase=self.phase, tick=self.tick, address=address, value=value))
            self.data[address] = value

    word = lambda offset: int.from_bytes(sid[offset:offset + 2], 'big')
    memory = Memory()
    memory.data[word(8):word(8) + len(sid) - 124] = sid[124:]
    memory.data[:256] = list(range(256))
    zero_page = list(memory.data[:256])
    cpu = cpu_type()(memory=memory)

    def call(address):
        cpu.stPushWord(0x01ff)
        cpu.pc = address
        start = cpu.processorCycles
        while cpu.pc != 0x0200:
            if cpu.processorCycles - start > 100000:
                raise ValueError('Callable player did not return')
            cpu.step()
        if cpu.sp != 255:
            raise ValueError('Callable player damaged stack')
        if memory.data[:256] != zero_page:
            raise ValueError('Callable player damaged caller zero page')
        return cpu.processorCycles - start

    call(word(10))
    if memory.writes:
        raise ValueError('Initialization emitted I/O writes')
    cycles = []
    for tick in range(calls):
        memory.tick, memory.phase = tick, 'play'
        cycles.append(call(word(12)))
    first = list(memory.writes)
    if restart:
        memory.writes = []
        memory.phase, memory.tick = 'init', None
        call(word(10))
        if memory.writes:
            raise ValueError('Repeated initialization emitted I/O writes')
        for tick in range(calls):
            memory.tick, memory.phase = tick, 'play'
            call(word(12))
        if identity(first) != identity(memory.writes):
            raise ValueError('Repeated initialization failed to restore complete state')
    return first, cycles


class ShadesCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.score = json.loads((ROOT / 'songs/shades-score.json').read_text())
        cls.programs = json.loads((ROOT / 'songs/shades-programs.json').read_text())

    def fixture(self, *, rows=4, duration=2):
        score = copy.deepcopy(self.score)
        order = copy.deepcopy(score['orders'][2])
        score['orders'] = [order]
        order['rowCount'], order['rowDurationCalls'] = rows, duration
        order['patternIds'] = ['a', 'b', 'c']
        order['transposeSemitones'] = [0, 0, 0]
        order['fade'] = {'kind': 'cancel'}
        sequences = [
            [{'kind': 'note', 'sourceNote': 12, 'gate': 'on'}, {'kind': 'hold'},
             {'kind': 'note', 'sourceNote': 10, 'gate': 'off'}, {'kind': 'rest'}],
            [{'kind': 'note', 'sourceNote': 20, 'gate': 'on'}, {'kind': 'rest'},
             {'kind': 'hold'}, {'kind': 'rest'}],
            [{'kind': 'note', 'sourceNote': 30, 'gate': 'on'}, {'kind': 'hold'},
             {'kind': 'note', 'sourceNote': 29, 'gate': 'on'}, {'kind': 'rest'}],
        ]
        score['patterns'] = {name: {'rows': (sequence * 64)[:rows]}
                             for name, sequence in zip(('a', 'b', 'c'), sequences)}
        score['range']['stopCall'] = 1 + rows * duration
        return score, copy.deepcopy(self.programs)

    def assert_model(self, score, programs, *, restart=False):
        sid, built = compiler().build(score, programs)
        expected = compute(score, programs, include_stop=True)
        calls = score['range']['stopCall'] + 3
        if restart:
            actual, cycles = execute(sid, calls, restart=True)
        else:
            audit, actual = audit_candidate(sid, calls)
            cycles = audit['playCycles']
            self.assertEqual(0, audit['initWriteCount'])
            self.assertLess(audit['maximumPlayCycles'] + audit['irqHostAllowanceCycles'],
                            audit['minimumTimerPeriodCycles'])
        self.assertEqual(identity(expected), identity(actual))
        self.assertLess(max(cycles), 0x3000)
        self.assertLess(built['payloadBytes'], 0x9000)
        self.assertEqual(b'\x00\x00\x00\x01', sid[18:22])
        self.assertEqual(b'\x00\x14', sid[118:120])
        return sid, built

    def test_small_score_gate_hold_release_and_reinitialization(self):
        self.assert_model(*self.fixture(), restart=True)

    def test_byte_sentinel_keeps_256_rows_and_256_duration(self):
        for rows, duration in ((256, 1), (2, 256)):
            with self.subTest(rows=rows, duration=duration):
                score, programs = self.fixture(rows=rows, duration=duration)
                pattern = ([{'kind': 'hold'}] * 255 + [{'kind': 'note', 'sourceNote': 12, 'gate': 'on'}]
                           if rows == 256 else [{'kind': 'note', 'sourceNote': value, 'gate': 'on'}
                                               for value in (12, 13)])
                score['patterns']['boundary'] = {'rows': pattern}
                score['orders'][0]['patternIds'] = ['boundary'] * 3
                next_order = copy.deepcopy(score['orders'][0])
                next_order.update(rowCount=1, rowDurationCalls=1, patternIds=['next'] * 3, timerHigh=0x31)
                score['patterns']['next'] = {'rows': [{'kind': 'note', 'sourceNote': 14, 'gate': 'on'}]}
                score['orders'].append(next_order)
                score['range']['stopCall'] += 1
                self.assert_model(score, programs)

    def test_off_pitch_updates_history_even_when_row_writer_is_suppressed(self):
        score, programs = self.fixture()
        score['patterns']['a']['rows'] = [{'kind': 'note', 'sourceNote': 95, 'gate': 'off'},
                                         {'kind': 'rest'}, {'kind': 'hold'}, {'kind': 'rest'}]
        score['patterns']['c']['rows'] = copy.deepcopy(score['patterns']['a']['rows'])
        self.assert_model(score, programs)

    def test_selected_bank_limit_is_explicit_and_unused_blocks_do_not_count(self):
        score, programs = self.fixture(rows=1, duration=1)
        original = programs['programs']['blocks'][score['orders'][0]['instrument']]
        for index in range(86):
            programs['programs']['blocks'][f'new-{index}'] = copy.deepcopy(original)
        self.assert_model(score, programs)
        score['instrumentBlocks'] = [f'new-{index}' for index in range(86)]
        score['orders'] = [dict(copy.deepcopy(score['orders'][0]), instrument=name)
                           for name in score['instrumentBlocks']]
        score['range']['stopCall'] = 87
        with self.assertRaisesRegex(ValueError, '85 selected blocks'):
            compiler().build(score, programs)

    def test_payload_placement_respects_callable_ram_and_cia_host(self):
        score, programs = self.fixture()
        with self.assertRaisesRegex(ValueError, 'CIA host workspace'):
            compiler().assemble_player(score, programs, load_address=0x0800)
        with self.assertRaisesRegex(ValueError, 'callable RAM'):
            compiler().assemble_player(score, programs, load_address=0x9f00)
        payload, built = compiler().assemble_player(score, programs, load_address=0x4000)
        self.assertEqual(0x4000, built['symbols']['entry_init'])
        self.assertLessEqual(0x4000 + len(payload), 0xa000)

    def test_semantic_edits_and_source_annotations_are_independent(self):
        score, programs = self.fixture()
        block = programs['programs']['blocks'][score['orders'][0]['instrument']]
        block['voices'][0].update(pulse_width=65530, pulse_step=17, pulse_up_calls=1,
                                  pulse_down_calls=3, portamento_step=0x102,
                                  portamento_mode='up', vibrato_delay=1,
                                  vibrato_extent=3, vibrato_step=7)
        block['filter']['trigger_mask'] = 1
        block['filter']['contour'].update(cutoff_low=6, cutoff_high=255,
                                         up_calls=2, down_calls=3, fine_step=2, coarse_step=1)
        sid, _ = self.assert_model(score, programs)
        score.pop('sourceEvidence', None)
        programs.pop('sourceEvidence', None)
        self.assertEqual(sid, compiler().build(score, programs)[0])

    def test_preloaded_modulation_carries_and_target_descent_match_the_model(self):
        score, programs = self.fixture()
        for mode, current, target, step in (('target', 0x0300, 0x01e1, 0x0120),
                                            ('down', 1, 0, 0x0102),
                                            ('up', 65530, 0, 0x0102)):
            with self.subTest(mode=mode):
                edited = copy.deepcopy(programs)
                for voice in edited['preloaded']['voices']:
                    voice.update(frequency=current, target_frequency=target,
                                 portamento_mode=mode, portamento_step=step,
                                 vibrato_delay=1, vibrato_extent=3, vibrato_step=255,
                                 pulse_width=65530, pulse_up_calls=1,
                                 pulse_down_calls=2, pulse_step=17)
                edited['preloaded']['filter'].update(cutoff_low=0, cutoff_high=0,
                                                     up_calls=0, down_calls=2,
                                                     fine_step=255, coarse_step=3)
                self.assert_model(score, edited)

    def test_low_byte_zero_disables_portamento_even_with_nonzero_high_byte(self):
        score, programs = self.fixture()
        for voice in programs['preloaded']['voices']:
            voice.update(portamento_step=0x0100, portamento_mode='up')
        for voice in programs['programs']['blocks'][score['orders'][0]['instrument']]['voices']:
            voice.update(portamento_step=0x0100, portamento_mode='up')
        self.assert_model(score, programs)

    def test_resolved_percussion_threshold_and_low_byte_only_tuning(self):
        score, programs = self.fixture()
        order = score['orders'][0]
        order['voice1HighNotesAbsolute'] = False
        order['transposeSemitones'][0] = -8
        score['patterns']['a']['rows'][:2] = [{'kind': 'note', 'sourceNote': value, 'gate': 'on'}
                                            for value in (55, 56)]
        block = programs['programs']['blocks'][order['instrument']]
        block['percussion_control'] = 128
        block['filter']['trigger_mask'] = 1
        block['filter']['contour'].update(cutoff_low=6, cutoff_high=7)
        block['filter']['percussion_contour'].update(cutoff_low=1, cutoff_high=200)
        for voice in block['voices'][1:]:
            voice['fine_tune'] = 255
        programs['programs']['frequency_words'] = [0x12ff] * 96
        self.assert_model(score, programs)

    def test_complete_selected_form_matches_all_computed_stores(self):
        self.assert_model(copy.deepcopy(self.score), copy.deepcopy(self.programs))


if __name__ == '__main__':
    unittest.main()
