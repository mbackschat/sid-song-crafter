import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from flashdance_pitch import PitchEffects, SlideState, VibratoState, advance_pitch, note_changed


class FlashdancePitchTests(unittest.TestCase):
    def test_vibrato_counts_before_motion_and_retains_asymmetric_first_half_cycle(self):
        state = PitchEffects(vibrato=VibratoState(enabled=1, interval=4, remaining=3, shift=2))
        table = [1000, 1316]
        actual = [advance_pitch(state, 10000, 0, table) for _ in range(10)]
        self.assertEqual([10079, 10158, 10237, 10158, 10079, 10000, 9921, 9842, 9921, 10000], actual)

    def test_absolute_pitch_skips_slide_addition_but_preserves_accumulation(self):
        state = PitchEffects(slide=SlideState(enabled=1, step=40))
        self.assertEqual(50000, advance_pitch(state, 50000, 0, [100, 200], absolute=True))
        self.assertEqual(1080, advance_pitch(state, 1000, 0, [100, 200]))
        self.assertEqual(80, state.slide.offset)

    def test_new_note_cancels_one_shot_effects_without_resetting_their_phase(self):
        state = PitchEffects(slide=SlideState(enabled=1, step=40, offset=80),
                             vibrato=VibratoState(enabled=2, interval=4, remaining=2, offset=158))
        note_changed(state)
        self.assertEqual((0, 80), (state.slide.enabled, state.slide.offset))
        self.assertEqual((1, 2, 158), (state.vibrato.enabled, state.vibrato.remaining, state.vibrato.offset))

    def test_slide_has_priority_and_wraps_without_advancing_vibrato(self):
        state = PitchEffects(slide=SlideState(enabled=1, step=40, offset=65520),
                             vibrato=VibratoState(enabled=1, remaining=3))
        self.assertEqual(34, advance_pitch(state, 10, 0, [100, 200]))
        self.assertEqual(3, state.vibrato.remaining)
        state.slide.subtract = True
        self.assertEqual(65530, advance_pitch(state, 10, 0, [100, 200]))

    def test_vibrato_depth_adds_to_delta_high_byte_before_shift_and_wraps(self):
        state = PitchEffects(vibrato=VibratoState(enabled=1, interval=4, remaining=3,
                                                shift=2, depth=255, growth=2))
        self.assertEqual(10000, advance_pitch(state, 10000, 0, [1000, 1256]))
        self.assertEqual(1, state.vibrato.depth)
        self.assertEqual(10128, advance_pitch(state, 10000, 0, [1000, 1256]))


SOURCE = ROOT / '.local/research/flashdance/drax-flashdance-conversion.sid'


@unittest.skipUnless(SOURCE.exists(), 'Requires pinned local Flashdance source')
class FlashdanceExecutedPitchTests(unittest.TestCase):
    def test_effect_transitions_match_every_opening_original_body(self):
        spec = importlib.util.spec_from_file_location('pitch_reference', ROOT / 'scripts/study-drax-references.py')
        reference = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reference)
        data = SOURCE.read_bytes()
        reference.verify_reference('flashdance', data)
        diagnostic = reference.load_script('psid_audit.py', 'pitch_private_audit')
        diagnostic.AuditMemory = reference.FlashdanceDiagnosticMemory
        pending, checked = {}, []

        def capture(memory, x):
            word = lambda address: memory[address + x] | memory[address + x + 3] << 8
            return PitchEffects(
                slide=SlideState(enabled=memory[0x1704 + x], step=word(0x1753),
                                 subtract=bool(memory[0x1759 + x]), offset=word(0x175c)),
                vibrato=VibratoState(enabled=memory[0x1701 + x], interval=memory[0x171c + x],
                                    remaining=memory[0x1719 + x], direction=memory[0x1725 + x],
                                    shift=memory[0x172e + x], growth=memory[0x171f + x],
                                    depth=memory[0x1722 + x], offset=word(0x1728)))

        def observe(cpu, memory):
            if memory.phase != 'play':
                return
            ram, x = memory.data, cpu.x
            if cpu.pc == 0x1515:
                state = capture(ram, x)
                table = [ram[address] | ram[address + 1] << 8 for address in range(0x1628, 0x16e8, 2)]
                frequency = ram[0x100c + x] | ram[0x100f + x] << 8
                result = advance_pitch(state, frequency, ram[0x1014 + x], table,
                                       absolute=bool(ram[0x100b]))
                pending[x] = state, result
            if cpu.pc == 0x15f1:
                state, result = pending.pop(x)
                self.assertEqual(result, ram[0x100c + x] | ram[0x100f + x] << 8, (memory.tick, x))
                self.assertEqual(state, capture(ram, x), (memory.tick, x))
                checked.append((memory.tick, x))

        diagnostic.audit_psid(data, 514, observer=observe)
        self.assertEqual(1515, len(checked))
        self.assertFalse(pending)


if __name__ == '__main__':
    unittest.main()
