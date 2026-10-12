import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('full_reconstruction', ROOT / 'scripts/reconstruct-drax-full.py')
full = importlib.util.module_from_spec(spec)
spec.loader.exec_module(full)

class FullReconstructionTests(unittest.TestCase):
    def test_editing_the_description_changes_pitch_without_changing_the_engine(self):
        description = json.loads(full.DEFAULT_RECIPE.read_text())
        description['bassRecipe'] = str(full.bass.STUDY / 'instrument.json')
        description['lead']['notes'][8]['frequency'] = 3747
        description['chord']['frequencies'] = [1873, 2228, 2805]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'description.json'
            path.write_text(json.dumps(description))
            sid, _ = full.build(path)
        _, writes = full.bass.audit_psid(sid, 120)
        frames = full.native.frame_states(writes, 120)
        self.assertEqual(frames[101][7] | frames[101][8] << 8, 3747)
        self.assertEqual(frames[111][7] | frames[111][8] << 8, 3747 + 128)
        self.assertEqual([frames[t][14] | frames[t][15] << 8 for t in (101, 103, 105)], [1873, 2228, 2805])
        self.assertEqual(frames[110][18], 0x50)

    def test_all_three_instruments_evolve_from_own_code(self):
        sid, _ = full.build(full.DEFAULT_RECIPE)
        _, writes = full.bass.audit_psid(sid, 153)
        frames = full.native.frame_states(writes, 153)
        self.assertEqual([frames[t][4] for t in (100,101,102,103)], [9,129,65,64])
        self.assertEqual([frames[t][11] for t in (100,101,109,110)], [9,65,65,64])
        self.assertEqual([frames[t][18] for t in (100,101,109,110)], [9,81,81,80])
        self.assertEqual([frames[t][14] | frames[t][15]<<8 for t in range(101,107)], [3747,3747,4456,4456,5611,5611])
        self.assertEqual([frames[t][7] | frames[t][8]<<8 for t in range(110,119)], [7494,7622,7750,7622,7494,7366,7238,7366,7494])
        self.assertEqual(frames[151][24],0)

    def test_exact_write_guard_rejects_changed_order_or_value(self):
        rows = [dict(phase='play',tick=1,address=0xd404,value=65),dict(phase='play',tick=1,address=0xd405,value=2)]
        self.assertEqual(full.compare_writes(rows,copy.deepcopy(rows))['matchedWrites'],2)
        with self.assertRaisesRegex(ValueError,'write'):
            full.compare_writes(rows,list(reversed(rows)))

if __name__ == '__main__':
    unittest.main()
