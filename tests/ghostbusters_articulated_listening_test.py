from array import array
import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audio_comparison import Pcm16
from sid_clock import NTSC_CLOCK, NTSC_FRAME_CYCLES


def helper():
    spec = importlib.util.spec_from_file_location('ghostbusters_articulated_listening',
        ROOT / 'scripts/studies/ghostbusters/prepare-articulated-listening.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture():
    rate = 1000
    ledger = [dict(startCall=start, endCall=start + 40) for start in (640, 768, 896)]
    clock = lambda call: 4.53 + call * NTSC_FRAME_CYCLES / NTSC_CLOCK
    enabled, disabled = array('h'), array('h')
    for frame in range(48 * rate):
        at = frame / rate
        base = 1000 if frame % 2 else -1000
        support = 0
        for row in ledger:
            start, end = clock(row['startCall']), clock(row['endCall'])
            if start <= at < end:
                support = 400 if frame % 2 else -400
            elif end <= at < end + .08:
                support = round(400 * (1 - (at - end) / .08)) * (1 if frame % 2 else -1)
        enabled.extend((base, base + support))
        disabled.extend((base, base))
    proof = dict(cpu=dict(musicEntryFromInit=round(4.53 * NTSC_CLOCK)))
    return Pcm16(rate, 2, rate * 48, enabled, ''), Pcm16(rate, 2, rate * 48, disabled, ''), ledger, proof


class GhostbustersArticulatedListeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = helper()

    def test_requires_rendered_attack_body_release_and_settled_late_gap(self):
        enabled, disabled, ledger, proof = fixture()
        report = self.helper.check_release(enabled, disabled, ledger, proof)
        self.assertEqual(report['checkedCompleteGaps'], 2)
        self.assertGreater(report['minimumBodyAcRms'], 32)
        self.assertGreater(report['minimumEarlyReleaseAcRms'], 0)
        self.assertLessEqual(report['maximumLateGapRms'], 1)
        self.assertFalse(report['musicalAcceptanceEstablished'])

    def test_rejects_left_change_stuck_body_and_instant_release(self):
        enabled, disabled, ledger, proof = fixture()
        changed = Pcm16(enabled.sample_rate, 2, enabled.frames, array('h', enabled.samples), '')
        changed.samples[100] += 1
        with self.assertRaisesRegex(ValueError, 'left'):
            self.helper.check_release(changed, disabled, ledger, proof)
        for frame in range(17 * 1000, round(17.3 * 1000)):
            enabled.samples[frame * 2 + 1] += 100 if frame % 2 else -100
        with self.assertRaisesRegex(ValueError, 'late gap'):
            self.helper.check_release(enabled, disabled, ledger, proof)
        enabled, disabled, ledger, proof = fixture()
        first_end = (proof['cpu']['musicEntryFromInit'] + ledger[0]['endCall'] * NTSC_FRAME_CYCLES) / NTSC_CLOCK
        for frame in range(round((first_end + .005) * 1000), round((first_end + .1) * 1000)):
            enabled.samples[frame * 2 + 1] = disabled.samples[frame * 2 + 1]
        with self.assertRaisesRegex(ValueError, 'release body'):
            self.helper.check_release(enabled, disabled, ledger, proof)

    def test_rejects_renderer_alignment_outside_the_bounded_init_offset(self):
        enabled, disabled, ledger, proof = fixture()
        proof['cpu']['musicEntryFromInit'] += round(.1 * NTSC_CLOCK)
        with self.assertRaisesRegex(ValueError, 'alignment'):
            self.helper.check_release(enabled, disabled, ledger, proof)

    def test_common_gain_preserves_old_new_energy_difference_and_both_channel_balances(self):
        a = Pcm16(1, 2, 2, array('h', [20000, -10000, -20000, 10000]), '')
        b = Pcm16(1, 2, 2, array('h', [10000, -5000, -10000, 5000]), '')
        gain = self.helper.common_gain((a, b))
        self.assertEqual(gain, 1)
        a.samples[0] = 32000
        gain = self.helper.common_gain((a, b))
        self.assertLess(gain, 1)
        self.assertEqual(self.helper.scaled(b, gain).samples,
                         array('h', (round(value * gain) for value in b.samples)))


if __name__ == '__main__':
    unittest.main()
