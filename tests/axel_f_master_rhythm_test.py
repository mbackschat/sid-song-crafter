import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('master_rhythm', ROOT / 'scripts/studies/axel-f/prepare-master-rhythm.py')
MASTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MASTER)


class MasterRhythmTest(unittest.TestCase):
    def test_percussion_program_uses_elapsed_time_and_releases_in_native_wave_grammar(self):
        kick = MASTER.program('2050', 7493)
        self.assertEqual(['81'] * 4 + ['11'] * 9, [row[0] for row in kick['wave'][:-1]])
        self.assertEqual('10', kick['wave'][-1][0])
        self.assertTrue(all(int(row[1], 16) >= 0x81 for row in kick['wave']))
        snare = MASTER.program('2090', 35643)
        self.assertEqual(['80', '81', '00'], snare['wave'][-1])
        hat = MASTER.program('2020', 10002)
        self.assertEqual(['81'] * 4 + ['80'], [row[0] for row in hat['wave']])

    def test_extraction_rejects_unexpected_program_and_off_grid_onset(self):
        def snapshot(adsr):
            registers = bytearray(25)
            registers[14:16] = (7493).to_bytes(2, 'little')
            registers[19:21] = bytes.fromhex(adsr)
            return dict(sid=registers.hex())
        frames = [snapshot('2050')] * 16
        writes = [dict(writerPc=0xc8cf, tick=0), dict(writerPc=0xc8cf, tick=8)]
        events = MASTER.extract(writes, frames, 0, 16)
        self.assertEqual([0, .25], [event['beat'] for event in events])
        with self.assertRaisesRegex(ValueError, 'grid'):
            MASTER.extract([dict(writerPc=0xc8cf, tick=7)], frames, 0, 16)
        with self.assertRaisesRegex(ValueError, 'program'):
            MASTER.extract(writes, [snapshot('1234')] * 16, 0, 16)


if __name__ == '__main__':
    unittest.main()
