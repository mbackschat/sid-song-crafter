import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import psid_audit

spec = importlib.util.spec_from_file_location('describe_flashdance_score', ROOT / 'scripts/describe-flashdance-score.py')
decoder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(decoder)
SOURCE = ROOT / '.local/research/flashdance/drax-flashdance-conversion.sid'


def fixture(pattern):
    memory = bytearray(65536)
    memory[0x1765:0x1775] = bytes(range(3, 64, 4))
    memory[0x1762:0x1765] = bytes((0, 1, 2))
    memory[0x1f7b:0x1f83] = bytes((0x82, 0, 0x60, 0x42, 0x10, 0x28, 0x10, 0x50))
    for index in range(96):
        memory[0x1628 + 2 * index:0x162a + 2 * index] = (1000 + index).to_bytes(2, 'little')
    for track in decoder.TRACK_ADDRESSES:
        memory[track:track + 3] = bytes((0x8b, 1, 0xff))
    memory[0x1d7c], memory[0x1e7c] = 0, 0x30
    memory[0x3000:0x3000 + len(pattern)] = bytes(pattern)
    return memory


class FlashdanceScoreDecoderTest(unittest.TestCase):
    def test_note_legato_hold_and_off_have_distinct_runtime_contracts(self):
        result = decoder.decode_score(fixture([0x80, 0xa2, 51, 0x90, 49, 0x80, 0x7e, 0x80, 0, 0x7f]), stop_call=18)
        commands = result['roles']['lead']['commands']
        self.assertEqual('instrument', commands[0]['kind'])
        self.assertEqual('record-10', commands[0]['instrument'])
        events = [row for row in commands if row['kind'] != 'instrument']
        self.assertEqual([(2, 'note'), (6, 'note'), (10, 'hold'), (14, 'off')],
                         [(row['call'], row['kind']) for row in events])
        self.assertTrue(events[0]['restart'])
        self.assertFalse(events[1]['restart'])
        self.assertEqual((51, 11), tuple(events[0][key] for key in ('sourceNote', 'transposeSemitones')))
        self.assertEqual((62, 1063), tuple(events[0]['sourceEvidence'][key] for key in ('pitchTableIndex', 'frequencyWord')))
        self.assertTrue(all(row['durationCalls'] == 4 for row in events))
        self.assertEqual([(2, 3), (2, 2), (2, 1)], result['initializers'])

    def test_effects_schedule_release_without_score_off_and_keep_pitch_effects_explicit(self):
        result = decoder.decode_score(fixture([0x80, 0xa0, 11, 0xc0, 0x7e, 0xc1, 0x7e, 0xc2, 0x7e, 0xc3, 0x7e, 0x7f]), stop_call=22)
        commands = result['roles']['bass']['commands']
        effects = [row for row in commands if row['kind'] == 'effect']
        self.assertEqual(['sustainReleaseAhead', 'vibrato', 'pitchOffset', 'pitchOffset'],
                         [row['effect'] for row in effects])
        self.assertEqual([0x28, 0x50], [row['parameters']['stepWord'] for row in effects[2:]])
        self.assertEqual(3, effects[1]['parameters']['initialCounter'])
        self.assertEqual(4, effects[1]['parameters']['reloadCounter'])
        self.assertEqual([(8, 3, 0), (8, 2, 0), (8, 1, 0)], result['sustainReleaseWrites'])
        self.assertFalse(any(row['kind'] == 'off' for row in commands))

    def test_loop_restore_precedes_next_pattern_and_recurrence_rejects_changed_commands(self):
        result = decoder.decode_score(fixture([0x80, 0xa0, 11, 0x7e, 0x7f]), stop_call=18)
        self.assertEqual([6, 14], [row['call'] for row in result['trackLoops'] if row['voice'] == 1])
        self.assertEqual([2, 10], [row['call'] for row in result['roles']['bass']['commands'] if row['kind'] == 'note'])
        decoder.verify_recurrence(result['roles'], first_call=2, cycle_calls=8)
        result['roles']['bass']['commands'][-1]['kind'] = 'off'
        with self.assertRaisesRegex(ValueError, 'recurring score'):
            decoder.verify_recurrence(result['roles'], first_call=2, cycle_calls=8)

    def test_unexecuted_effect_class_and_track_stop_are_rejected(self):
        memory = fixture([0x80, 0xa0, 11, 0xc4, 0x7e, 0x7f])
        memory[0x1f83:0x1f85] = bytes((0xc0, 0))
        with self.assertRaisesRegex(ValueError, 'Unsupported score effect'):
            decoder.decode_score(memory, stop_call=10)
        with self.assertRaisesRegex(ValueError, 'terminating track'):
            decoder.decode_score(fixture([0x80, 0xa0, 11, 0xfe]), stop_call=10)

    def test_source_identity_rejects_before_execution(self):
        with self.assertRaisesRegex(ValueError, 'pinned Flashdance'):
            decoder.describe_score(b'not the pinned source')


@unittest.skipUnless(SOURCE.exists(), 'Requires the pinned local Flashdance SID')
class FlashdanceCompleteScoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_bytes()
        cls.production_memory = psid_audit.AuditMemory
        cls.score = decoder.describe_score(cls.source)

    def test_complete_selected_form_is_verified_from_bytes_and_original_execution(self):
        self.assertEqual({'bass': 37, 'lead': 44, 'chord': 13}, self.score['evidence']['noteCounts'])
        self.assertEqual((0, 1537, 1538, 1536),
                         tuple(self.score['range'][key] for key in ('firstCall', 'lastCallInclusive', 'stopCall', 'cycleCalls')))
        self.assertTrue(self.score['evidence']['executedScoreMatches'])
        self.assertTrue(self.score['evidence']['secondScoreCycleMatches'])
        self.assertEqual(3074, self.score['evidence']['verifiedPlayCalls'])
        self.assertEqual(8, len(self.score['instruments']))
        self.assertEqual(96, len(self.score['frequencyTable']))

    def test_opening_two_pitch_changes_preserve_program_and_release_is_separate(self):
        lead = self.score['roles']['lead']['commands']
        notes = {row['call']: row for row in lead if row['kind'] == 'note'}
        self.assertFalse(notes[102]['restart'])
        self.assertFalse(notes[274]['restart'])
        self.assertTrue(notes[98]['restart'])
        self.assertEqual(10001, notes[2]['sourceEvidence']['frequencyWord'])
        effects = {row['call']: row for row in lead if row['kind'] == 'effect'}
        self.assertEqual('sustainReleaseAhead', effects[94]['effect'])
        self.assertEqual([478, 482, 486, 490, 494, 498, 502, 506, 510],
                         [row['call'] for row in lead if row['kind'] == 'off' and row['call'] <= 513])

    def test_diagnostic_execution_leaves_the_production_auditor_strict(self):
        self.assertIs(self.production_memory, psid_audit.AuditMemory)
        with self.assertRaisesRegex(ValueError, 'Unsupported I/O write'):
            psid_audit.AuditMemory()[0xd419] = 0
        receipt = self.score['evidence']['diagnostic']['ignoredInitPaddleWrites']
        self.assertEqual([(0xd419, 0), (0xd41a, 0)], [(row['address'], row['value']) for row in receipt])

    def test_source_annotations_are_separate_from_runtime_controls(self):
        for role in self.score['roles'].values():
            for command in role['commands']:
                self.assertIn('sourceEvidence', command)
                self.assertNotIn('sourceAddress', command)
                self.assertNotIn('value', command)
                if command['kind'] == 'note':
                    self.assertNotIn('frequencyWord', command)
                    self.assertNotIn('pitchTableIndex', command)
                    index = command['sourceEvidence']['pitchTableIndex']
                    self.assertEqual((self.score['frequencyTable'][index] + role['fineTuneWord']) & 65535,
                                     command['sourceEvidence']['frequencyWord'])
        for instrument in self.score['instruments'].values():
            self.assertEqual({'attackDecay', 'sustainRelease', 'sourceEvidence'}, set(instrument))
        self.assertNotIn('sidWrites', self.score)
        self.assertFalse(self.score['evidence']['registerDumpPlayback'])


if __name__ == '__main__':
    unittest.main()
