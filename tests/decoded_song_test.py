import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('compose', ROOT / 'scripts/compose-sid.py')
compose = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compose)


class DecodedSongTests(unittest.TestCase):
    def description(self):
        result = json.loads(compose.DEFAULT_SCORE.read_text())
        result['bassRecipe'] = str(ROOT / 'songs/studies/drax-bass-reconstruction/instrument.json')
        return result

    def build(self, description):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'song.json'
            path.write_text(json.dumps(description))
            return compose.build(path)[0]

    def frames(self, description, calls):
        _, writes = compose.audit_psid(self.build(description), calls)
        state, result = [0] * 25, []
        grouped = [[] for _ in range(calls)]
        for row in writes:
            if row['phase'] == 'init':
                state[row['address'] - 0xd400] = row['value']
            else:
                grouped[row['tick']].append(row)
        for rows in grouped:
            for row in rows:
                state[row['address'] - 0xd400] = row['value']
            result.append(state.copy())
        return result

    def test_word_scheduler_and_four_tone_chord_preserve_preparation_pitch(self):
        frames = self.frames(self.description(), 402)
        pitch = lambda t, offset: frames[t][offset] | frames[t][offset + 1] << 8
        self.assertEqual(pitch(171, 14), 4206)
        self.assertEqual([pitch(t, 14) for t in range(173, 181, 2)], [3536, 4206, 5000, 5611])
        self.assertEqual(frames[316][4], 9)
        self.assertEqual(frames[317][4], 129)
        self.assertEqual(frames[388][18], 9)
        self.assertEqual(frames[391][18], 81)
        self.assertEqual(frames[392][18], 80)
        self.assertEqual(frames[173][17], 0)
        self.assertEqual(frames[245][17], 6)

    def test_editable_score_and_patch_do_not_require_reference_sid(self):
        song = self.description()
        song['source']['path'] = '/not-present.sid'
        song['roles']['lead']['notes'][8]['frequency'] = 3747
        song['patches']['lead-pulse']['vibratoDeltas'] = [0, 64, 128, 64, 0, -64, -128, -64]
        song['roles']['chord']['notes'][0]['frequencies'] = [1873, 2228, 2805]
        frames = self.frames(song, 113)
        self.assertEqual(frames[101][7] | frames[101][8] << 8, 3747)
        self.assertEqual(frames[111][7] | frames[111][8] << 8, 3811)
        self.assertEqual(frames[101][14] | frames[101][15] << 8, 1873)

    def test_delayed_first_notes_do_not_repeat_initialization_at_byte_rollover(self):
        song = self.description()
        for role in song['roles'].values():
            for note in role['notes']:
                note['initCall'] += 256
                if 'gateOffCall' in note:
                    note['gateOffCall'] += 256
        song['range']['stopCall'] += 256
        song['range']['lastCallInclusive'] += 256
        frames = self.frames(song, 258)
        for frame in frames[256:]:
            self.assertEqual([frame[i] | frame[i + 1] << 8 for i in (0, 7, 14)], [557, 557, 557])

    def test_end_closes_all_gates_and_volume_without_restarting(self):
        frames = self.frames(self.description(), 2021)
        for frame in frames[2018:]:
            self.assertEqual([frame[i] for i in (4, 11, 18, 24)], [0, 0, 0, 0])

    def test_chord_width_is_an_executable_patch_parameter(self):
        song = self.description()
        song['patches']['chord-minor']['pulseInitial'] = 1024
        frames = self.frames(song, 103)
        self.assertEqual(frames[101][17], 4)

    def test_extra_role_or_misspelled_runtime_parameter_cannot_disappear_silently(self):
        song = self.description()
        song['roles']['drums'] = song['roles']['bass']
        with self.assertRaisesRegex(ValueError, 'three roles'):
            self.build(song)
        song = self.description()
        song['patches']['lead-pulse']['pulseStpe'] = 40
        with self.assertRaisesRegex(ValueError, 'unknown'):
            self.build(song)

    def test_unsupported_cadence_and_overlapping_preparations_are_rejected(self):
        song = self.description()
        song['profile']['callCycles'] = 9828
        with self.assertRaisesRegex(ValueError, 'profile'):
            self.build(song)
        song = self.description()
        song['roles']['lead']['notes'][1]['initCall'] = 5
        with self.assertRaisesRegex(ValueError, 'preparation'):
            self.build(song)


if __name__ == '__main__':
    unittest.main()
