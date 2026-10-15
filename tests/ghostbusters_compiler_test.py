"""Guard independent NTSC score consumption and sound output in compiled RAM."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name,
        ROOT / 'scripts/studies/ghostbusters' / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


compiler = load('ghostbusters_compiler_tests_backend', 'compiler.py')
player = compiler.player


def example(calls=48):
    scored = dict(schemaVersion=1, orders=[dict(patterns=[0])] * 3,
        patterns={'0': dict(rows=[dict(header=0x87, note=24,
            parameter=dict(volume=15, instrument=0)), dict(header=0x41)])},
        initialState=dict(phase=0, voices=[dict(orderCursor=0, patternCursor=0,
            remaining=0, note=0, header=0, instrument=0) for _ in range(3)]))
    sound = dict(schema='ghostbusters-sound-v1', target=deepcopy(player.TARGET),
        patches={'0': dict(pulse_low=0x23, pulse_high=8, control=65,
            attack_decay=0x2f, sustain_release=0xff, vibrato_shift=2)},
        frequencies={'0': 0x0100, '1': 0x0140, '24': 0x1234, '25': 0x12b4},
        volumePolicy=deepcopy(player.VOLUME_POLICY))
    return player.from_components(scored, sound, calls=calls)


class GhostbustersCompilerTest(unittest.TestCase):
    def test_full_runtime_rows_release_reset_and_retained_cache_match(self):
        value = example()
        sid, built = compiler.build(value)
        checked, writes = compiler.verify(value, sid, built)
        self.assertEqual(checked['namedStateBoundaries'], 49)
        self.assertEqual(checked['sidWriterValidation']['checkedStores'], len(writes))
        self.assertEqual(checked['resetCalls'], [40])
        self.assertTrue(checked['resetVerification']['restoredPoisonedState'])
        self.assertTrue(checked['resetVerification']['restoredWorkspace'])
        self.assertEqual([(row['address'], row['value']) for row in writes[:24]],
            [(address, 0) for address in range(0xd417, 0xd3ff, -1)])
        self.assertEqual([(row['address'], row['value']) for row in writes if row['tick'] == 0][:8],
            [(0xd418, 15), (0xd40f, 0x12), (0xd40e, 0x34),
             (0xd412, 65), (0xd410, 0x23), (0xd411, 8), (0xd413, 0x2f), (0xd414, 0xff)])
        reset = next(item['state'] for item in checked['checkpoints'] if item['call'] == 40)
        self.assertEqual(reset['cachedControls'], [65, 65, 65])
        self.assertEqual([voice['orderCursor'] for voice in reset['score']['voices']], [0, 0, 0])
        self.assertFalse(any(row['tick'] == 40 for row in writes))

    def test_volume_reads_saved_voice_zero_cursor_before_later_onset_advances_it(self):
        value = example(calls=4)
        value['score']['patterns']['0']['rows'] = [dict(header=0x80, note=24,
            parameter=dict(volume=15, instrument=0))]
        value['score']['orders'] = [dict(patterns=[0] * 100) for _ in range(3)]
        value['score']['initialState']['voices'][0]['orderCursor'] = 95
        sid, built = compiler.build(value)
        _, writes = compiler.verify(value, sid, built)
        self.assertEqual([row['value'] for row in writes if row['tick'] == 0 and row['address'] == 0xd418], [14, 14, 14])

    def test_global_reset_early_exit_retains_unprocessed_voice_and_control(self):
        value = example(calls=5)
        value['score']['initialState']['voices'][2]['orderCursor'] = 1
        value['score']['initialState']['voices'][0].update(note=24, header=0x27, remaining=3)
        value['initialSound']['cachedControls'] = [33, 129, 65]
        sid, built = compiler.build(value)
        _, writes = compiler.verify(value, sid, built)
        self.assertFalse(any(row['tick'] == 0 for row in writes))

    def test_signed_shift_arithmetic_and_inactive_nonquarter_body_match(self):
        for shift in (0, 2, 128, 129, 255):
            with self.subTest(shift=shift):
                value = example(calls=8)
                value['sound']['patches']['0']['vibrato_shift'] = shift
                value['sound']['frequencies'].update({'24': 0xffe0, '25': 0x0100})
                value['score']['initialState']['phase'] = 1
                for voice in value['score']['initialState']['voices']:
                    voice.update(remaining=255, note=24, header=7)
                sid, built = compiler.build(value)
                checked, _ = compiler.verify(value, sid, built)
                self.assertLess(checked['maximumPlayCycles'], 17095)

    def test_editable_note_and_pulse_parameters_change_only_their_ports(self):
        value = example()
        sid, built = compiler.build(value)
        _, baseline = compiler.verify(value, sid, built)
        for edit in ('note', 'pulse'):
            changed = deepcopy(value)
            if edit == 'note':
                changed['score']['patterns']['0']['rows'][0]['note'] = 25
                changed['sound']['frequencies']['26'] = 0x1334
                ports = {0xd400 + offset for offset in (0, 1, 7, 8, 14, 15)}
            else:
                changed['sound']['patches']['0']['pulse_low'] = 0x11
                ports = {0xd402, 0xd409, 0xd410}
            with self.subTest(edit=edit):
                sid, built = compiler.build(changed)
                _, written = compiler.verify(changed, sid, built)
                self.assertNotEqual(compiler.identity(baseline), compiler.identity(written))
                self.assertEqual(compiler.identity([row for row in baseline if row['address'] not in ports]),
                    compiler.identity([row for row in written if row['address'] not in ports]))

    def test_admission_rejects_wrong_clock_and_missing_late_patch(self):
        value = example(calls=1)
        value['target']['clock'] = 'pal'
        with self.assertRaisesRegex(ValueError, 'NTSC'):
            compiler.build(value)
        value = example(calls=1)
        value['score']['patterns']['0']['rows'].append(dict(header=0x80, note=24,
            parameter=dict(volume=6, instrument=8)))
        with self.assertRaisesRegex(ValueError, 'serialized selected patch'):
            compiler.build(value)

    def test_ntsc_psid_metadata_and_strict_rsid_boundary_are_explicit(self):
        value = example(calls=2)
        sid, built = compiler.build(value)
        self.assertEqual(sid[:4], b'PSID')
        self.assertEqual(int.from_bytes(sid[118:120], 'big'), 0x18)
        self.assertFalse(built['originalDriverIncluded'])
        self.assertFalse(built['registerDumpPlayback'])
        self.assertTrue(built['runtimeScoreScheduler'])
        altered = deepcopy(value)
        altered['sourceEvidence'] = dict(originalExecutable=[0xea], capturedStores=[1, 2])
        altered['score']['patterns']['0']['sourceEvidence'] = dict(address=0xffff)
        altered['title'] = 'Independent music component'
        changed, _ = compiler.build(altered)
        self.assertEqual(changed[124:], sid[124:])
        with self.assertRaisesRegex(ValueError, 'PSID header'):
            compiler.audit_psid(b'RSID' + sid[4:], 1, clock='ntsc')
        with self.assertRaisesRegex(ValueError, 'PAL'):
            compiler.audit_psid(sid, 1)

    def test_decimal_entries_and_actual_sys_bootstrap_restore_binary_state(self):
        value = example(calls=2)
        sid, built = compiler.build(value)
        memory = compiler.AuditMemory()
        memory.data[compiler.LOAD:compiler.LOAD + len(sid) - 124] = sid[124:]
        cpu = compiler.cpu_type()(memory=memory)
        for phase, tick, label in (('init', None, 'entry_init'), ('play', 0, 'entry_play')):
            memory.phase, memory.tick = phase, tick
            cpu.p |= cpu.DECIMAL
            cpu.stPushWord(0x01ff)
            cpu.pc = built['symbols'][label]
            began = cpu.processorCycles
            while cpu.pc != 0x0200:
                self.assertLess(cpu.processorCycles - began, 17095)
                memory.instruction = cpu.disassemble[memory.data[cpu.pc]][0]
                cpu.step()
            self.assertFalse(cpu.p & cpu.DECIMAL)
            self.assertEqual(cpu.sp, 255)
        self.assertEqual(compiler.identity(memory.writes), compiler.identity(player.compute(value, calls=1)['writes']))
        prg, labels = compiler.standalone_prg(sid, built, 2)
        checked = compiler.bootstrap_verification(prg, labels, value, built)
        self.assertEqual(checked['checkedPlayCalls'], 2)
        self.assertTrue(checked['passed'])

    def test_export_products_are_reviewable_and_output_must_be_fresh(self):
        value = example(calls=2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'composition.json'
            path.write_text(json.dumps(value))
            output = Path(directory) / 'compiled'
            checked = compiler.run(path, output)
            self.assertTrue(checked['completeCompiledRange'])
            self.assertEqual({item.name for item in output.iterdir()}, {'reconstructed.sid', 'reconstructed.prg',
                'player.asm', 'player.listing', 'build.json', 'audit.json', 'writes.json',
                'state-checkpoints.json', 'verification.json'})
            with self.assertRaisesRegex(ValueError, 'fresh directory'):
                compiler.run(path, output)

    def test_standalone_host_count_cannot_exceed_the_artifact_numeric_contract(self):
        value = example(calls=1)
        sid, built = compiler.build(value)
        for calls in (2, 16001, True, 0):
            with self.subTest(calls=calls):
                with self.assertRaisesRegex(ValueError, 'declared range'):
                    compiler.standalone_prg(sid, built, calls)
        prg, labels = compiler.standalone_prg(sid, built, 1)
        checked = compiler.bootstrap_verification(prg, labels, value, built)
        self.assertTrue(checked['passed'])
        self.assertEqual(checked['checkedPlayCalls'], 1)


if __name__ == '__main__':
    unittest.main()
