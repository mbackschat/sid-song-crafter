"""Guard Ghostbusters patch setup, release and continuing pitch arithmetic."""

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ghostbusters_sound_helpers',
    ROOT / 'scripts/studies/ghostbusters/programs.py')
sound = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sound
spec.loader.exec_module(sound)


def patch(**values):
    return sound.Patch(**(dict(pulse_low=0x23, pulse_high=0x08, control=65,
        attack_decay=0x2f, sustain_release=0xff, vibrato_shift=2) | values))


def inputs(**values):
    return sound.VoiceInputs(**(dict(note=24, header=7, remaining=3, cached_control=33) | values))


class GhostbustersProgramsTest(unittest.TestCase):
    def test_note_setup_writes_pitch_high_low_then_patch_and_keeps_gated_cache(self):
        result = sound.onset(inputs(), patch(), {24: 0x1234}, voice=1)
        self.assertEqual(result.writes, [(0xd408, 0x12), (0xd407, 0x34),
            (0xd40b, 65), (0xd409, 0x23), (0xd40a, 8), (0xd40c, 0x2f), (0xd40d, 0xff)])
        self.assertEqual(result.cached_control, 65)
        self.assertEqual(result.path, 'note')

    def test_rest_has_no_pitch_fetch_and_masks_hardware_gate_without_masking_cache(self):
        result = sound.onset(inputs(header=0x47), patch(), {}, voice=2)
        self.assertEqual(result.writes, [(0xd412, 64), (0xd410, 0x23),
            (0xd411, 8), (0xd413, 0x2f), (0xd414, 0xff)])
        self.assertEqual(result.cached_control, 65)
        self.assertEqual(result.path, 'rest')

    def test_quarter_release_precedes_pitch_and_zeros_envelope_only_at_remaining_zero(self):
        bank = {24: 0x1200, 25: 0x1280}
        result = sound.body(inputs(remaining=0), patch(), bank, 0, phase=4)
        self.assertEqual(result.writes, [(0xd404, 32), (0xd405, 0), (0xd406, 0),
            (0xd400, 48), (0xd401, 0x12)])
        self.assertEqual(result.cached_control, 33)
        self.assertEqual(sound.body(inputs(), patch(vibrato_shift=0), {}, 0, phase=0).writes,
            [(0xd404, 32)])
        self.assertEqual(sound.body(inputs(header=0x27, remaining=0), patch(vibrato_shift=0), {}, 0, phase=0).writes, [])
        self.assertEqual(sound.body(inputs(remaining=0), patch(vibrato_shift=0), {}, 0, phase=1).writes, [])

    def test_vibrato_triangle_uses_adjacent_word_delta_and_low_high_writer_order(self):
        bank = {24: 0x1200, 25: 0x1280}
        for phase, multiplier in enumerate((0, 1, 2, 3, 3, 2, 1, 0)):
            with self.subTest(phase=phase):
                result = sound.body(inputs(header=0x27), patch(), bank, 2, phase=phase)
                word = 0x1200 + multiplier * 16
                self.assertEqual(result.writes, [(0xd40e, word & 255), (0xd40f, word >> 8)])

    def test_duration_threshold_is_independent_of_note_and_signed_shift_loop_is_exact(self):
        bank = {127: 0x1200, 128: 0x1280}
        state = inputs(note=255, header=4)
        self.assertEqual(sound.body(state, patch(), bank, 0, phase=3).writes,
            [(0xd400, 0), (0xd401, 0x12)])
        self.assertEqual(sound.body(replace(state, header=5), patch(), bank, 0, phase=3).writes,
            [(0xd400, 48), (0xd401, 0x12)])
        self.assertEqual(sound.body(replace(state, header=5), patch(vibrato_shift=128), bank, 0, phase=3).writes,
            [(0xd400, 0), (0xd401, 0x12)])
        self.assertEqual(sound.body(replace(state, header=5), patch(vibrato_shift=129), bank, 0, phase=3).writes,
            [(0xd400, 192), (0xd401, 0x12)])

    def test_unsigned_frequency_borrow_and_output_wrap_match_word_arithmetic(self):
        bank = {24: 0xffe0, 25: 0x0100}
        result = sound.body(inputs(header=7), patch(vibrato_shift=1), bank, 0, phase=3)
        self.assertEqual(result.writes, [(0xd400, 0xb8), (0xd401, 0)])

    def test_inactive_quarter_skips_body_but_other_phases_can_still_write_pitch(self):
        state = inputs(remaining=255)
        self.assertEqual(sound.body(state, patch(), {}, 0, phase=0).writes, [])
        self.assertEqual(sound.body(state, patch(), {24: 0x1200, 25: 0x1280}, 0, phase=1).writes,
            [(0xd400, 16), (0xd401, 0x12)])

    def test_mute_retains_setup_cache_and_required_pitch_reads_without_sid_stores(self):
        state = inputs()
        result = sound.onset(state, patch(), {24: 0x1234}, 0, mute=1)
        self.assertEqual((result.cached_control, result.writes), (65, []))
        self.assertEqual(sound.body(state, patch(), {24: 0x1200, 25: 0x1280}, 0, 4, mute=1).writes, [])
        with self.assertRaisesRegex(ValueError, 'frequency index 25'):
            sound.body(state, patch(), {24: 0x1200}, 0, 1, mute=1)
        self.assertEqual(state, inputs())

    def test_shared_volume_auto_fade_uses_byte_subtraction_then_optional_half(self):
        for cursor, expected in ((0, 15), (94, 15), (95, 14), (108, 1), (109, 0), (110, 15), (255, 15)):
            self.assertEqual(sound.volume_write(15, cursor), [(0xd418, expected)])
        self.assertEqual(sound.volume_write(6, 255, half=True), [(0xd418, 3)])

    def test_invalid_numeric_inputs_and_missing_onset_frequency_reject(self):
        with self.assertRaises(ValueError):
            sound.onset(inputs(note=True), patch(), {24: 0x1234}, 0)
        with self.assertRaisesRegex(ValueError, 'frequency index 24'):
            sound.onset(inputs(), patch(), {}, 0)
        with self.assertRaises(ValueError):
            sound.body(inputs(), patch(vibrato_shift=-1), {}, 0, 0)
        with self.assertRaises(ValueError):
            sound.volume_write(16, 0)

    def test_original_music_stages_exclude_init_clears(self):
        source = ROOT / '.local/research/ghostbusters/Ghostbusters.sid'
        oracle = ROOT / 'scripts/studies/ghostbusters/probe-form.py'
        if not source.exists() or not oracle.exists():
            self.skipTest('Pinned private source or shared music oracle is unavailable')
        probe_spec = importlib.util.spec_from_file_location('ghostbusters_component_probe',
            ROOT / 'scripts/studies/ghostbusters/sound-probe.py')
        probe = importlib.util.module_from_spec(probe_spec)
        sys.modules[probe_spec.name] = probe
        probe_spec.loader.exec_module(probe)
        result = probe.verify(source.read_bytes(), calls=128)
        self.assertEqual(result['originalInitStores'], 24)
        self.assertEqual(result['musicStores'], 85)
        self.assertGreaterEqual(result['boundaryComparisons'], 385)

    def test_parameter_controls_include_a_real_gated_patch_eight_vibrato_context(self):
        source = ROOT / '.local/research/ghostbusters/Ghostbusters.sid'
        oracle = ROOT / 'scripts/studies/ghostbusters/probe-form.py'
        if not source.exists() or not oracle.exists():
            self.skipTest('Pinned private source or shared music oracle is unavailable')
        probe_spec = importlib.util.spec_from_file_location('ghostbusters_eligible_sound_probe',
            ROOT / 'scripts/studies/ghostbusters/sound-probe.py')
        probe = importlib.util.module_from_spec(probe_spec)
        sys.modules[probe_spec.name] = probe
        probe_spec.loader.exec_module(probe)
        result = probe.verify(source.read_bytes(), calls=1700, controls=True, control_calls=1700)
        self.assertEqual(len(result['controls']), 4)
        self.assertTrue(all(control['onlyDeclaredPortsChanged'] for control in result['controls']))
        vibrato = next(control for control in result['controls'] if control['name'] == 'vibrato-shift')
        self.assertEqual(vibrato['sourceAddress'], 0xa834)
        self.assertEqual(vibrato['eligibleContext']['instrument'], 8)
        self.assertEqual(vibrato['eligibleContext']['call'], 1697)
        self.assertEqual(vibrato['eligibleContext']['lastWrittenControlBefore'] & 1, 1)


if __name__ == '__main__':
    unittest.main()
