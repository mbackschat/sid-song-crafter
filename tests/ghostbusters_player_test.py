from copy import deepcopy
import importlib.util
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class GhostbustersPlayerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('ghostbusters_player_test_subject',
            ROOT / 'scripts/studies/ghostbusters/player.py')
        cls.player = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.player
        spec.loader.exec_module(cls.player)

    def example(self, calls=25):
        score = dict(schemaVersion=1, orders=[dict(patterns=[voice]) for voice in range(3)],
            patterns={'0': dict(rows=[dict(header=35, note=45), dict(header=35, note=46)]),
                      '1': dict(rows=[dict(header=63, note=45)]),
                      '2': dict(rows=[dict(header=63, note=45)])},
            initialState=dict(phase=0, voices=[dict(orderCursor=0, patternCursor=0,
                remaining=0, note=0, header=0, instrument=0) for _ in range(3)]))
        sound = dict(schema='ghostbusters-sound-v1', target=deepcopy(self.player.TARGET),
            patches={'0': dict(pulse_low=64, pulse_high=0, control=65, attack_decay=47,
                sustain_release=255, vibrato_shift=0),
                '1': dict(pulse_low=0, pulse_high=8, control=33, attack_decay=40,
                sustain_release=136, vibrato_shift=0)},
            frequencies={'45': 1000, '46': 1100, '47': 1200},
            volumePolicy=dict(autoNibble=15, subtractFrom=109, orderCursorVoice=0, halfVolume=False))
        return self.player.from_components(score, sound, [0, 0, 0], calls=calls)

    def play(self, result, tick=None):
        return [row for row in result['writes'] if row['phase'] == 'play'
                and (tick is None or row['tick'] == tick)]

    def test_init_clears_descending_ports_without_consuming_first_row_or_volume(self):
        description = self.example(1)
        initial = self.player.initial_state(description)
        result = self.player.compute(description)
        clears = [row for row in result['writes'] if row['phase'] == 'init']
        self.assertEqual([(row['address'], row['value']) for row in clears],
                         [(address, 0) for address in range(0xd417, 0xd3ff, -1)])
        self.assertEqual(initial, dict(score=description['score']['initialState'], cachedControls=[0, 0, 0]))
        self.assertEqual(len(self.play(result, 0)), 21)
        self.assertEqual([row['address'] for row in self.play(result, 0)[:7]],
                         [0xd40f, 0xd40e, 0xd412, 0xd410, 0xd411, 0xd413, 0xd414])

    def test_onset_and_vibrato_preserve_opposite_frequency_store_orders(self):
        description = self.example(2)
        description['sound']['patches']['0']['vibrato_shift'] = 1
        description['score']['patterns']['2']['rows'][0]['header'] = 6
        result = self.player.compute(description, contexts=True)
        self.assertEqual([(row['address'], row['value']) for row in self.play(result, 0)[:2]],
                         [(0xd40f, 3), (0xd40e, 232)])
        voice2 = [row for row in self.play(result, 1) if 0xd40e <= row['address'] <= 0xd414]
        self.assertEqual([(row['address'], row['value']) for row in voice2], [(0xd40e, 1), (0xd40f, 4)])

    def test_rest_masks_only_emitted_gate_and_keeps_cached_patch_control(self):
        description = self.example(5)
        description['score']['patterns']['0']['rows'] = [dict(header=0, note=45), dict(header=64)]
        result = self.player.compute(description)
        rest = self.play(result, 4)
        self.assertEqual([(row['address'], row['value']) for row in rest if row['address'] == 0xd404], [(0xd404, 64)])
        self.assertEqual(result['returns'][4]['cachedControls'][0], 65)
        self.assertFalse(any(row['address'] in (0xd400, 0xd401) for row in rest))

    def test_volume_precedes_onset_and_has_no_recurring_global_writer(self):
        description = self.example(2)
        description['score']['patterns']['2']['rows'] = [dict(header=0x83, note=45,
            parameter=dict(volume=9, instrument=1))]
        result = self.player.compute(description, contexts=True)
        self.assertEqual((self.play(result, 0)[0]['address'], self.play(result, 0)[0]['value']), (0xd418, 9))
        self.assertFalse(self.play(result, 1))
        volume = result['contexts'][0]
        self.assertEqual((volume['kind'], volume['packed'], volume['orderCursorVoice0']), ('volume', 0x91, 0))

    def test_reset_retains_cache_and_instrument_and_skips_all_sound_stages(self):
        description = self.example(25)
        description['score']['orders'] = [dict(patterns=[0]) for _ in range(3)]
        description['score']['patterns']['0']['rows'][1] = dict(header=0x80, note=47,
            parameter=dict(volume=6, instrument=1))
        result = self.player.compute(description, contexts=True)
        self.assertFalse(self.play(result, 20))
        self.assertEqual(result['returns'][20]['cachedControls'], [33] * 3)
        self.assertEqual(result['returns'][20]['score']['phaseAfter'], 21)
        self.assertEqual([row['instrument'] for row in result['returns'][20]['score']['voices']], [1] * 3)
        self.assertEqual([row['value'] for row in self.play(result, 24)
                          if row['address'] in (0xd404, 0xd40b, 0xd412)], [33] * 3)

    def test_middle_voice_reset_preserves_prior_action_and_skips_lower_voice(self):
        description = self.example(1)
        description['score']['initialState']['voices'][1]['orderCursor'] = 1
        result = self.player.compute(description)
        self.assertEqual(len(self.play(result, 0)), 7)
        self.assertTrue(all(0xd40e <= row['address'] <= 0xd414 for row in self.play(result, 0)))
        self.assertEqual(result['returns'][0]['cachedControls'], [0, 0, 65])
        self.assertEqual([row['remaining'] for row in result['returns'][0]['score']['voices']], [0, 0, 0])

    def test_volume_uses_action_cursor_before_later_voice_advances(self):
        description = self.example(1)
        description['score']['orders'][0]['patterns'] = [0] * 109
        description['score']['initialState']['voices'][0]['orderCursor'] = 100
        description['score']['patterns']['0']['rows'] = [dict(header=0, note=45)]
        description['score']['patterns']['2']['rows'] = [dict(header=0x83, note=45,
            parameter=dict(volume=15, instrument=1))]
        result = self.player.compute(description)
        self.assertEqual(next(row['value'] for row in self.play(result, 0) if row['address'] == 0xd418), 9)
        self.assertEqual(result['returns'][0]['score']['voices'][0]['orderCursor'], 101)

    def test_duration_and_note_edits_compute_new_output_without_changing_companions(self):
        original = self.example()
        baseline = self.player.compute(original, contexts=True)
        duration = deepcopy(original)
        duration['score']['patterns']['0']['rows'][0]['header'] += 1
        edited = self.player.compute(duration, contexts=True)
        self.assertEqual([row['call'] for row in baseline['contexts'] if row['kind'] == 'onset' and row['voice'] == 0], [0, 16])
        self.assertEqual([row['call'] for row in edited['contexts'] if row['kind'] == 'onset' and row['voice'] == 0], [0, 20])
        note = deepcopy(original)
        note['score']['patterns']['0']['rows'][0]['note'] += 1
        changed = self.player.compute(note)
        for result in (edited, changed):
            self.assertNotEqual(result['writes'], baseline['writes'])
            self.assertEqual([row for row in result['writes'] if row['address'] > 0xd406],
                             [row for row in baseline['writes'] if row['address'] > 0xd406])

    def test_sound_edit_changes_only_selected_patch_port_without_score_drift(self):
        description = self.example(5)
        baseline = self.player.compute(description)
        description['sound']['patches']['0']['pulse_low'] = 32
        edited = self.player.compute(description)
        ports = {0xd402, 0xd409, 0xd410}
        self.assertNotEqual(baseline['writes'], edited['writes'])
        self.assertEqual([row for row in baseline['writes'] if row['address'] not in ports],
                         [row for row in edited['writes'] if row['address'] not in ports])
        self.assertEqual(baseline['returns'], edited['returns'])

    def test_metadata_never_changes_runtime(self):
        description = self.example(5)
        baseline = self.player.compute(description)
        description.update(title='Different title', sourceEvidence=dict(arbitrary='annotation'))
        description['sound']['sourceEvidence'] = dict(sha256='annotation')
        description['score']['sourceEvidence'] = dict(arbitrary='annotation')
        description['score']['patterns']['0']['sourceEvidence'] = dict(address=0x1234)
        self.assertEqual(baseline, self.player.compute(description))

    def test_target_duplicate_state_and_missing_lookup_are_rejected(self):
        for change in ('clock', 'duplicate', 'frequency', 'patch', 'range', 'replay'):
            description = self.example(1)
            if change == 'clock':
                description['target']['clock'] = 'pal'
            elif change == 'duplicate':
                description['initialSound']['note'] = 45
            elif change == 'frequency':
                del description['sound']['frequencies']['45']
            elif change == 'patch':
                del description['sound']['patches']['0']
            elif change == 'range':
                description['range']['auditCalls'] = 0
            else:
                description['capturedWrites'] = []
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.player.compute(description)

    def checker(self):
        spec = importlib.util.spec_from_file_location('ghostbusters_player_checker_test',
            ROOT / 'scripts/studies/ghostbusters/check-player.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def test_retained_proof_rejects_changed_or_undeclared_dependency(self):
        checker = self.checker()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'helper.py'
            path.write_bytes(b'frozen helper')
            stage = dict(fingerprint=dict(inputs=[dict(path='helper.py', type='file',
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())]))
            checker.verify_dependencies(stage, {'helper.py'}, root=root)
            path.write_bytes(b'changed helper')
            with self.assertRaisesRegex(ValueError, 'fingerprint'):
                checker.verify_dependencies(stage, {'helper.py'}, root=root)
            with self.assertRaisesRegex(ValueError, 'declared'):
                checker.verify_dependencies(dict(fingerprint=dict(inputs=[])), {'helper.py'}, root=root)

    def test_compressed_retained_output_is_bound_to_original_stage_bytes(self):
        checker = self.checker()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = json.dumps(dict(value=45)).encode()
            path = root / 'rows.json.gz'
            path.write_bytes(gzip.compress(raw))
            stage = dict(outputs=[dict(relativePath='rows.json', type='file', sha256=hashlib.sha256(raw).hexdigest())])
            checker.verify_stage_outputs(stage, root)
            path.write_bytes(gzip.compress(json.dumps(dict(value=46)).encode()))
            with self.assertRaisesRegex(ValueError, 'hash'):
                checker.verify_stage_outputs(stage, root)


if __name__ == '__main__':
    unittest.main()
