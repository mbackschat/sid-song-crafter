import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
from psid_audit import AuditMemory, audit_psid
from rambo_compiler_test import compiler, fixture, identity
from rambo_player import LoaderPlayer
from verify_player import cpu_type


def expected_stereo_writes(description):
    player = LoaderPlayer(description)
    for call in range(description['range']['auditCalls']):
        player.play(call)
    secondary_init = [dict(phase='init', tick=None, address=0xd438,
                           value=description['initialization']['volume'])]
    secondary_init.extend(dict(phase='init', tick=None, address=0xd420 + offset, value=0)
                          for offset in range(23, -1, -1))
    return secondary_init + [dict(row, address=row['address'] + 32)
                             if row['phase'] == 'play' and 0xd407 <= row['address'] <= 0xd40d
                             else row for row in player.writes]


class RamboStereoCompilerTest(unittest.TestCase):
    def test_default_mono_export_retains_the_accepted_binary(self):
        description = json.loads((ROOT / 'songs/rambo-loader.json').read_text())
        sid, _ = compiler().build(description)
        self.assertEqual((ROOT / 'samples/rambo-loader/rambo-loader.sid').read_bytes(), sid)

    def test_split_preserves_native_voice_indices_coupled_lead_and_every_state(self):
        description = fixture()
        description['initialData'][0][24] = 0x43
        compiled = compiler()
        sid, built = compiled.build(description, stereo_bass=True)
        model = LoaderPlayer(description)
        expected_states = {None: compiled.model_state(model)}
        for call in range(description['range']['auditCalls']):
            model.play(call)
            expected_states[call] = compiled.model_state(model)
        states = {}

        def observer(cpu, memory):
            compiled.check_sid_writer(cpu, memory)
            boundary = (memory.phase == 'init' and cpu.pc == built['symbols']['rb_init_done']
                        or memory.phase == 'play' and cpu.pc == built['symbols']['rb_call_done'])
            if boundary and cpu.sp == 0xfd:
                states[memory.tick] = compiled.read_state(memory, built)

        audit, actual = audit_psid(sid, description['range']['auditCalls'], observer=observer)
        self.assertEqual(identity(expected_stereo_writes(description)), identity(actual))
        self.assertEqual(expected_states, states)
        self.assertEqual((3, 0x54), tuple(int.from_bytes(sid[index:index + 2], 'big')
                                       for index in (4, 118)))
        self.assertEqual(b'\x42\x00', sid[122:124])
        self.assertEqual([0, 39, 14], built['voiceSidOffsets'])
        self.assertEqual('stereo-bass', built['outputLayout'])
        self.assertEqual([0xd400, 0xd420], [chip['baseAddress'] for chip in audit['sids']])
        self.assertLess(audit['maximumPlayCycles'], audit['frameCycleBudget'])
        self.assertTrue(any(row['address'] == 0xd427 and row['value']
                            for row in actual if row['phase'] == 'play'))
        self.assertFalse(any(0xd407 <= row['address'] <= 0xd40d
                             for row in actual if row['phase'] == 'play'))

    def test_cross_chip_sync_or_ring_rejects_both_possible_recipients(self):
        for voice, flags in ((1, 2), (1, 4), (2, 2), (2, 4)):
            with self.subTest(voice=voice, flags=flags):
                description = fixture()
                description['initialData'][voice][24] |= flags
                with self.assertRaisesRegex(ValueError, 'cross-chip oscillator coupling'):
                    compiler().build(description, stereo_bass=True)

    def test_diagnostic_prefix_cannot_hide_later_unsupported_coupling(self):
        description = fixture(80)
        description['program'].update({
            'wait': dict(kind='row', sourceNote=191, duration=8, next='patch'),
            'patch': dict(kind='volume', dataId='coupled', next='note'),
        })
        description['voices'][1]['cursor'] = 'wait'
        description['dataBanks'] = {'coupled': [0x43, 17, 128, 2, 4]}
        with TemporaryDirectory() as directory:
            source = Path(directory) / 'description.json'
            source.write_text(json.dumps(description))
            output = Path(directory) / 'candidate'
            with self.assertRaisesRegex(ValueError, 'cross-chip oscillator coupling'):
                compiler().run(source, output, calls=1, stereo_bass=True)
            self.assertFalse(output.exists())

    def test_source_filter_routing_and_live_global_changes_are_unsupported(self):
        for address, value in ((0xd415, 1), (0xd416, 1), (0xd417, 2), (0xd418, 14)):
            with self.subTest(address=address):
                rows = [dict(phase='play', tick=9, address=address, value=value)]
                with self.assertRaisesRegex(ValueError, 'shared filter or live global'):
                    compiler().stereo_writes(rows, 15)

    def test_reinitialization_restores_both_chip_banks_and_score_state(self):
        description = fixture(16)
        compiled = compiler()
        payload, built = compiled.assemble_player(description, stereo_bass=True)
        memory = AuditMemory((0xd400, 0xd420))
        memory.data[built['loadAddress']:built['loadAddress'] + len(payload)] = payload
        for base in memory.sid_bases:
            memory.data[base:base + 25] = [0x55] * 25
        cpu = cpu_type()(memory=memory)

        def call(label):
            cpu.stPushWord(0x1ff)
            cpu.pc = built['symbols'][label]
            for _ in range(100000):
                if cpu.pc == 0x200:
                    return
                memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
                cpu.step()
            self.fail('Compiled stereo routine failed to return')

        call('entry_init')
        for base in memory.sid_bases:
            self.assertEqual([0] * 24 + [15], memory.data[base:base + 25])
        initial_state = compiled.read_state(memory, built)
        initial_writes = identity(memory.writes)
        memory.phase = 'play'
        for tick in range(16):
            memory.tick = tick
            call('entry_play')
        memory.writes.clear()
        memory.phase, memory.tick = 'init', None
        for base in memory.sid_bases:
            memory.data[base:base + 25] = [0x55] * 25
        call('entry_init')
        self.assertEqual(initial_state, compiled.read_state(memory, built))
        self.assertEqual(initial_writes, identity(memory.writes))
        for base in memory.sid_bases:
            self.assertEqual([0] * 24 + [15], memory.data[base:base + 25])


if __name__ == '__main__':
    unittest.main()
