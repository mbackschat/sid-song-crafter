from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cybernoid_compiler_test import compiler, identity
from cybernoid_player_test import opening_fixture
from cybernoid_player import compute_writes


def invalid_programs():
    pulse = opening_fixture()
    pulse['pulse_slots'] = pulse['pulse_slots'][:3]
    filt = opening_fixture()
    filt['filter_programs'] = filt['filter_programs'][:1]
    onset_length = opening_fixture()
    onset_length['onset_lengths'] = onset_length['onset_lengths'][:4]
    onset_wave = opening_fixture()
    onset_wave['onset_waves'] = onset_wave['onset_waves'][:4]
    drum_bank = opening_fixture()
    drum_bank['records'][2]['fx1'] = 1
    drum_bank['drums'] = drum_bank['drums'][:1]
    drum_wave = opening_fixture()
    drum_wave['drums'][0]['waves'] = [3]
    drum_pitch = opening_fixture()
    drum_pitch['play_calls'] = 3
    drum_pitch['drums'][0]['pitch_values'] = [52]
    tail_pitch = opening_fixture()
    tail_pitch['ending'] = dict(start_call=2, release_calls=1, fade_step_calls=1)
    tail_pitch['play_calls'] = 19
    tail_pitch['drums'][0]['pitch_values'] = [52]
    arp = opening_fixture()
    arp['arpeggios'][2] = [3, 0]
    return (
        (pulse, 'Pulse slot lacks selection 3'),
        (filt, 'Filter program lacks selection 1'),
        (onset_length, 'Onset length lacks selection 4'),
        (onset_wave, 'Onset wave lacks selection 4'),
        (drum_bank, 'Drum program lacks selection 1'),
        (drum_wave, 'Drum wave table lacks index 1'),
        (drum_pitch, 'Drum pitch table lacks index 1'),
        (tail_pitch, 'Drum pitch table lacks index 1'),
        (arp, 'Arpeggio table lacks index 4'),
    )


class CybernoidCompilerValidationTests(unittest.TestCase):
    def test_public_compile_boundaries_reject_all_reachable_missing_program_data(self):
        module = compiler()
        for description, message in invalid_programs():
            before = deepcopy(description)
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    compute_writes(description)
                for boundary in (module.assemble_player, module.build):
                    with self.subTest(boundary=boundary.__name__):
                        with patch.object(module, 'assemble', side_effect=AssertionError('Invalid data reaches assembly')):
                            with self.assertRaisesRegex(ValueError, message):
                                boundary(description)
                self.assertEqual(before, description)

    def test_expired_drum_and_wrapped_arpeggio_accept_short_tables(self):
        module = compiler()
        description = opening_fixture()
        description['drums'][0]['waves'] = [1]
        description['drums'][0]['pitch_values'] = [255]
        description['arpeggios'][2] = [255]
        expected = compute_writes(description)
        before = deepcopy(description)
        payload, report = module.assemble_player(description)
        self.assertTrue(payload)
        self.assertEqual(description['play_calls'], report['playCalls'])
        sid, _ = module.build(description)
        self.assertEqual(b'PSID', sid[:4])
        self.assertEqual(expected, compute_writes(description))
        self.assertEqual(before, description)

    def test_partial_run_validates_future_program_reads_before_assembly(self):
        module = compiler()
        description, message = next((description, message) for description, message in invalid_programs()
                                    if message == 'Drum pitch table lacks index 1')
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'description.json'
            output = Path(directory) / 'output'
            source.write_text(json.dumps(description))
            with patch.object(module, 'assemble', side_effect=AssertionError('Invalid future data reaches assembly')):
                with self.assertRaisesRegex(ValueError, message):
                    module.run(source, output, calls=1)
            self.assertFalse(output.exists())

    def test_partial_run_reuses_complete_validation_stream(self):
        module = compiler()
        description = opening_fixture()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'description.json'
            output = Path(directory) / 'output'
            source.write_text(json.dumps(description))
            with patch.object(module, 'compute_writes', wraps=compute_writes) as numeric:
                report = module.run(source, output, calls=1)
            numeric.assert_called_once_with(description)
            self.assertEqual(1, report['checkedPlayCalls'])
            written = json.loads((output / 'writes.json').read_text())
            self.assertEqual(identity(compute_writes(description, calls=1)), identity(written))

    def test_load_and_payload_must_remain_below_basic_rom(self):
        module = compiler()
        for load in (0x03ff, 0xa000, True, 1.5, 0x9ff0):
            with self.subTest(load=load), self.assertRaisesRegex(ValueError, 'callable RAM'):
                module.assemble_player(opening_fixture(), load_address=load)


if __name__ == '__main__':
    unittest.main()
