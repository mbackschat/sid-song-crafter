import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TurboOnsetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('turbo_onset', ROOT / 'scripts/studies/turbo-outrun/analyze-onset.py')
        cls.model = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.model)

    def store(self, address, value, cycle=100):
        return dict(operation='store', address=address, sidAddress=address, value=value,
                    pc=0x0967 if address == 0xd418 else 0x0e46, phase='play', irqIndex=1153,
                    monitorCycle=cycle)

    def test_noise_free_pulse_onset_changes_to_saw_with_gate_preserved(self):
        original = [self.store(0xd404, 0x41), self.store(0xd404, 0x40)]
        candidate = [self.store(0xd404, 0x21), self.store(0xd404, 0x20)]
        result = self.model.compare_stores(original, candidate)
        self.assertEqual(result['changedControlWrites'], 2)

    def test_sample_interleaving_can_move_but_sample_values_cannot_change(self):
        original = [self.store(0xd404, 0x41), self.store(0xd418, 0x37)]
        candidate = [self.store(0xd418, 0x37, 99), self.store(0xd404, 0x21)]
        self.model.compare_stores(original, candidate)
        candidate[0]['value'] = 0x38
        with self.assertRaisesRegex(ValueError, 'volume'):
            self.model.compare_stores(original, candidate)

    def test_gate_filter_other_voice_and_pitch_changes_are_rejected(self):
        for address, before, after in [(0xd404, 0x41, 0x20), (0xd417, 7, 6),
                                      (0xd40b, 0x41, 0x21), (0xd400, 50, 51)]:
            original = [self.store(0xd404, 0x41), self.store(address, before)]
            candidate = [self.store(0xd404, 0x21), self.store(address, after)]
            with self.subTest(address=address), self.assertRaises(ValueError):
                self.model.compare_stores(original, candidate)

    def test_missing_sid_store_or_no_effect_cannot_pass(self):
        baseline = [self.store(0xd404, 0x41), self.store(0xd400, 50)]
        for candidate in (baseline, [self.store(0xd404, 0x21)]):
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                self.model.compare_stores(baseline, candidate)

    def test_oscillator_schedule_must_remain_on_the_same_irq(self):
        candidate = [dict(self.store(0xd404, 0x21), irqIndex=1154)]
        with self.assertRaisesRegex(ValueError, 'schedule'):
            self.model.compare_stores([self.store(0xd404, 0x41)], candidate)

    def test_removal_must_cover_every_recorded_pulse_phase_and_no_other_irq(self):
        ledger = [dict(irqIndex=i, assignedWaveform=0x41, finalControl=0x41) for i in (1153, 1154)]
        complete = [dict(irqIndex=i, original=0x41, candidate=0x21) for i in (1153, 1154)]
        self.model.verify_removal(dict(changedControls=complete), ledger)
        for changes in (complete[:1], complete + [dict(irqIndex=1200, original=0x41, candidate=0x21)]):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, 'complete onset'):
                self.model.verify_removal(dict(changedControls=changes), ledger)


if __name__ == '__main__':
    unittest.main()
