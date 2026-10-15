"""Guard native stereo allocation independently of a source-derived score."""

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gb_stereo_title_tests', ROOT / 'scripts/studies/ghostbusters/compile-title.py')
title = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = title
spec.loader.exec_module(title)
from ghostbusters_title_test import fixture


def example():
    composition, alignment, commands = fixture()
    composition['sound']['patches']['3'] = dict(pulse_low=0, pulse_high=8, control=129, attack_decay=0x14, sustain_release=0, vibrato_shift=0)
    composition['score']['initialState']['voices'][2]['instrument'] = 3
    composition['score']['patterns']['2'] = deepcopy(composition['score']['patterns']['0'])
    composition['score']['patterns']['2']['rows'][0]['parameter']['instrument'] = 3
    composition['score']['orders'][2] = dict(patterns=[2])
    composition['score']['patterns']['1'] = dict(rows=[dict(header=0x47)])
    composition['score']['orders'][1] = dict(patterns=[0, 1])
    composition['sound']['frequencies'].update({'36': 0x2468, '37': 0x2568})
    arrangement = json.loads((ROOT / 'songs/studies/ghostbusters-stereo/arrangement.json').read_text())
    arrangement['support']['patterns'] = [0]
    return composition, alignment, commands, arrangement


def articulated_example():
    composition, alignment, commands, arrangement = example()
    composition['range']['auditCalls'] = 300
    rows = [dict(header=0x83, note=24, parameter=dict(volume=15, instrument=0)),
        dict(header=5, note=24), dict(header=3, note=31), dict(header=0x51)]
    composition['score']['patterns']['0'] = dict(rows=rows)
    percussion = deepcopy(rows)
    percussion[0]['parameter']['instrument'] = 3
    composition['score']['patterns']['2'] = dict(rows=percussion)
    composition['score']['orders'] = [dict(patterns=[0]*4), dict(patterns=[0]*4), dict(patterns=[2]*4)]
    composition['sound']['frequencies'].update({'31': 0x1800, '32': 0x1900})
    arrangement['support']['articulation'] = 'source-root-prefix'
    return composition, alignment, commands, arrangement


class GhostbustersStereoTest(unittest.TestCase):
    def test_runtime_duplicates_complete_lead_and_volume_and_independent_hold(self):
        composition, _, _, arrangement = example()
        sid, built = title.compiler.build(composition, arrangement=arrangement)
        self.assertEqual(hashlib.sha256(sid).hexdigest(), '21253861c96fa97dc6b658b91e6f0396b54d5e57c6a32928f06dc96fc8a7b2b1')
        verified, writes = title.compiler.verify(composition, sid, built)
        self.assertEqual(int.from_bytes(sid[4:6], 'big'), 3)
        self.assertEqual(sid[118:120], b'\x00\x58')
        self.assertEqual(sid[122:124], b'\x42\x00')
        self.assertEqual(verified['namedStateBoundaries'], 49)
        mono = title.compiler.player.compute(composition)
        self.assertEqual(title.compiler.identity([r for r in writes if r['address'] < 0xd420]), title.compiler.identity(mono['writes']))
        a = [(r['phase'], r['tick'], r['address'] + 32, r['value']) for r in writes if 0xd400 <= r['address'] <= 0xd406 or r['address'] == 0xd418]
        b = [(r['phase'], r['tick'], r['address'], r['value']) for r in writes if 0xd420 <= r['address'] <= 0xd426 or r['address'] == 0xd438]
        self.assertEqual(a, b)
        support = [(r['tick'], r['address'], r['value']) for r in writes if r['phase'] == 'play' and 0xd427 <= r['address'] <= 0xd42d]
        self.assertEqual(support[:7], [(0,0xd428,0x24),(0,0xd427,0x68),(0,0xd42b,0x41),(0,0xd429,0),(0,0xd42a,8),(0,0xd42c,0x24),(0,0xd42d,0x48)])
        self.assertEqual(support[7:9], [(40,0xd42b,0x40),(40,0xd42d,0)])
        self.assertEqual([r[0] for r in support[9:]], [44] * 7)
        self.assertTrue(verified['resetVerification']['restoredPoisonedState'])
        self.assertLess(verified['maximumPlayCycles'], 17095)

    def test_native_speech_is_on_both_chips_without_missing_timer_ticks(self):
        composition, alignment, commands, arrangement = example()
        with patch.object(title, 'decode_commands', return_value=(commands, [])):
            built = title.build(composition, bytes(65536), alignment, seconds=5, arrangement=arrangement)
        checked = title.verify_native(built, 48)
        self.assertLess(checked['maximumNmiCyclesIncludingEntry'], 102)
        self.assertTrue(checked['allOrderedStoresMatch'])
        self.assertEqual(title.admit_rsid(built['rsid'])['sidCount'], 2)
        self.assertEqual(title.admit_rsid(built['rsid'])['sha256'], hashlib.sha256(built['rsid']).hexdigest())
        self.assertEqual(title.verify_native(built, 2, poisoned=True)['checkedMusicCalls'], 2)

    def test_invalid_mix_and_changed_template_are_rejected(self):
        composition, _, _, arrangement = example()
        arrangement['mix'] = [[0.5,0.5],[0.5,0.5]]
        with self.assertRaisesRegex(ValueError, 'raw A-left'):
            title.compiler.build(composition, arrangement=arrangement)
        _, _, _, arrangement = example()
        with self.assertRaisesRegex(ValueError, 'anchor changed'):
            title.compiler.stereo.assembly('entry_init:\n  RTS\n', arrangement)

    def test_hold_screen_checks_later_lead_and_rejects_non_noise_companion(self):
        composition, _, _, arrangement = example()
        composition['score']['patterns']['0']['rows'][1] = dict(header=1, note=25)
        composition['sound']['frequencies']['26'] = 0x1300
        with self.assertRaisesRegex(ValueError, 'conflicts with source lead at call 32'):
            title.compiler.build(composition, arrangement=arrangement)
        composition, _, _, arrangement = example()
        composition['sound']['patches']['3']['control'] = 0x41
        with self.assertRaisesRegex(ValueError, 'source noise percussion'):
            title.compiler.build(composition, arrangement=arrangement)

    def test_default_mono_payload_matches_frozen_accepted_export(self):
        composition = json.loads((ROOT / 'evidence/ghostbusters-independent-full/native/composition.json').read_text())
        sid, _ = title.compiler.build(composition)
        self.assertEqual(hashlib.sha256(sid[124:]).hexdigest(), '7ebcc77aa57e79ce0ff8ac19c8437a8f0994c918c9cba3be765153dae2727567')

    def test_source_root_prefix_releases_before_nonroot_and_rearticulates_next_pattern(self):
        composition, _, _, arrangement = articulated_example()
        sid, built = title.compiler.build(composition, arrangement=arrangement)
        _, writes = title.compiler.verify(composition, sid, built)
        control = [(r['tick'], r['value']) for r in writes if r['phase'] == 'play' and r['address'] == 0xd42b]
        self.assertEqual(control, [(0,65),(40,64),(128,65),(168,64),(256,65),(296,64)])
        releases = [r for r in writes if r['phase'] == 'play' and r['address'] == 0xd42d]
        self.assertEqual([(r['tick'],r['value']) for r in releases], [(0,0x48),(128,0x48),(256,0x48)])
        model = title.compiler.numeric(composition, arrangement)
        self.assertEqual([(r['startCall'],r['endCall']) for r in model['supportLedger']], [(0,40),(128,168),(256,296)])
        original = title.compiler.player.compute(composition)
        self.assertEqual(title.compiler.identity([r for r in writes if r['address'] < 0xd420]), title.compiler.identity(original['writes']))

    def test_source_root_prefix_rejects_long_gate_short_gap_and_later_root_reentry(self):
        for defect in ('long gate','short gap','later root'):
            composition, _, _, arrangement = articulated_example()
            rows = composition['score']['patterns']['0']['rows']
            if defect == 'long gate':
                rows[1]['header'] = 31
            elif defect == 'short gap':
                rows[3]['header'] = 0x40
                rows[2]['header'] = 0
            else:
                rows.insert(3, dict(header=0, note=24))
            with self.subTest(defect=defect), self.assertRaisesRegex(ValueError, 'root prefix|following gap'):
                title.compiler.build(composition, arrangement=arrangement)

    def test_animated_support_changes_only_b2_width_and_continues_after_gate_off(self):
        composition, _, _, arrangement = articulated_example()
        plain_sid, plain_built = title.compiler.build(composition, arrangement=arrangement)
        self.assertEqual(hashlib.sha256(plain_sid).hexdigest(), '8f50013799b6923469f685de3eb19f9e5bc65dba4f0d83f67550663bbcda9ff6')
        _, plain = title.compiler.verify(composition, plain_sid, plain_built)
        animated = deepcopy(arrangement)
        animated['support']['pulseMotion'] = 'triangle-600-a00'
        sid, built = title.compiler.build(composition, arrangement=animated)
        _, writes = title.compiler.verify(composition, sid, built)
        self.assertEqual(title.compiler.identity([r for r in writes if r['address'] not in (0xd429,0xd42a)]),
            title.compiler.identity([r for r in plain if r['address'] not in (0xd429,0xd42a)]))
        widths = {}
        for row in writes:
            if row['phase'] == 'play' and row['address'] in (0xd429,0xd42a):
                widths.setdefault(row['tick'], {})[row['address']] = row['value']
        words = {tick: values[0xd429] | values[0xd42a] << 8 for tick,values in widths.items()}
        self.assertEqual([words[t] for t in (0,1,8,16,24,31,32,40,48,64,128)],
            [0x600,0x640,0x800,0xa00,0x800,0x640,0x600,0x800,0xa00,0x600,0x600])
        self.assertEqual((min(words.values()),max(words.values())), (0x600,0xa00))
        self.assertNotEqual(words[40],words[48])
        self.assertEqual(title.compiler.numeric(composition,animated)['supportLedger'],
            title.compiler.numeric(composition,arrangement)['supportLedger'])

    def test_animated_support_rejects_unknown_motion_and_section_hold(self):
        composition, _, _, arrangement = articulated_example()
        arrangement['support']['pulseMotion'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'pulse motion'):
            title.compiler.build(composition, arrangement=arrangement)
        arrangement['support']['pulseMotion'] = 'triangle-600-a00'
        del arrangement['support']['articulation']
        with self.assertRaisesRegex(ValueError, 'source-root-prefix'):
            title.compiler.build(composition, arrangement=arrangement)


if __name__ == '__main__':
    unittest.main()
