from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CASE = 'songs/studies/rambo-centered-native/arrangement.json'


class RamboCenteredNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('rambo_centered_native', ROOT / 'scripts/studies/rambo/prepare-centered-native.py')
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.config = json.loads((ROOT / CASE).read_text())
        cls.source = json.loads((ROOT / cls.config['source']).read_text())
        cls.baseline_config = json.loads((ROOT / cls.config['baselineArrangement']).read_text())
        cls.primary, cls.secondary, cls.proof, cls.records = cls.module.prepare(cls.source, cls.baseline_config, cls.config, arrangement_path=CASE)

    def test_primary_and_full_lead_program_remain_faithful_including_morse(self):
        self.assertEqual(self.source, self.primary)
        self.assertTrue(self.proof['primaryUnchanged'])
        self.assertTrue(all(self.proof['lead'][key] for key in ('orderedStoresIdentical', 'dataAndSoundIdentical', 'scoreStateIdentical', 'morseIdentical')))
        hooks = {node['codeId'] for node in self.secondary['program'].values() if node['kind'] == 'code'}
        self.assertEqual({'start-morse', 'increment-transpose', 'morse-pitch-one', 'morse-pitch-two'}, hooks)

    def test_inner_keeps_accepted_notes_stores_and_sounding_state(self):
        self.assertTrue(all(self.proof['inner'][key] for key in ('orderedStoresIdentical', 'noteLedgerIdentical', 'dataAndSoundIdentical')))
        self.assertEqual(42, self.proof['inner']['noteCount'])

    def test_third_retains_37_whole_held_regions_and_exact_coupled_source_programs(self):
        third = self.proof['third']
        self.assertEqual(37, third['heldRegionsRetained'])
        self.assertEqual(5, third['heldRegionsReplaced'])
        self.assertEqual([(4914, 5554), (10034, 11000)], [(row['startCall'], row['endCall']) for row in third['sourceWindows']])
        self.assertTrue(all(row['orderedStoresIdentical'] and row['dataAndSoundIdentical'] and row['noteLedgerIdentical'] for row in third['sourceWindows']))
        self.assertEqual(10814, third['naturalClearCall'])
        self.assertEqual(0, self.proof['ending']['activeMask'])
        self.assertEqual([0, 0, 0], self.proof['ending']['remainingLifetimes'])
        self.assertFalse(self.proof['phaseHistoryIdentical'])

    def test_provenance_pins_source_baseline_configuration_and_new_case(self):
        self.assertEqual(self.module.digest(self.source), self.proof['sourceSha256'])
        self.assertEqual(self.module.digest(self.baseline_config), self.proof['baselineConfigSha256'])
        self.assertEqual(self.module.digest(self.config), self.proof['configSha256'])
        self.assertEqual(CASE, self.secondary['sourceEvidence']['arrangement'])
        self.assertTrue(self.proof['passed'])

    def test_guard_rejects_changed_lead_store_and_morse_state(self):
        changed = deepcopy(self.records['variant'])
        next(row for row in changed['writes'] if row['phase'] == 'play' and row['address'] == 0xd404)['value'] ^= 1
        with self.assertRaisesRegex(ValueError, 'Lead ordered stores'):
            self.module.verify(self.source, self.primary, changed, self.records['source'], self.records['baseline'], self.records['heldEvents'], self.config)
        changed = deepcopy(self.records['variant'])
        changed['states'][60]['morsePhase'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'Morse'):
            self.module.verify(self.source, self.primary, changed, self.records['source'], self.records['baseline'], self.records['heldEvents'], self.config)

    def test_guard_rejects_lost_final_lifetime_hook_and_wrong_held_note(self):
        changed = deepcopy(self.secondary)
        hook = next(node for name, node in changed['program'].items() if name.startswith('ending/') and node['kind'] == 'poke-sound' and node['offset'] == 28)
        hook['value'] -= 1
        with self.assertRaisesRegex(ValueError, 'Third source window'):
            self.module.verify(self.source, self.primary, self.module.observe(changed), self.records['source'], self.records['baseline'], self.records['heldEvents'], self.config)
        changed = deepcopy(self.secondary)
        note = next(node for name, node in changed['program'].items() if name.startswith('third/') and node['kind'] == 'row' and node['sourceNote'] != 191)
        note['sourceNote'] += 1
        with self.assertRaisesRegex(ValueError, 'Third held'):
            self.module.verify(self.source, self.primary, self.module.observe(changed), self.records['source'], self.records['baseline'], self.records['heldEvents'], self.config)

    def test_changed_source_or_coupling_window_is_rejected_before_build(self):
        changed = deepcopy(self.source)
        changed['initialData'][0][24] ^= 1
        with self.assertRaisesRegex(ValueError, 'source fingerprint'):
            self.module.prepare(changed, self.baseline_config, self.config)
        changed = deepcopy(self.config)
        changed['sourceWindows'][0]['startCall'] += 1
        with self.assertRaisesRegex(ValueError, 'window contract'):
            self.module.prepare(self.source, self.baseline_config, changed)

    def test_assembly_keeps_primary_payload_and_disjoint_callable_ram(self):
        from verify_player import cpu_type
        cpu_type()
        spec = importlib.util.spec_from_file_location('rambo_centered_dual', ROOT / 'scripts/compose-rambo-dual.py')
        dual = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dual)
        sid, built = dual._build(self.primary, self.secondary)
        mono, _ = dual.single._assemble_player(self.source, load_address=0x1000)
        start = 124 + 0x1000 - built['loadAddress']
        self.assertEqual(mono, sid[start:start + len(mono)])
        self.assertLessEqual(built['players'][0]['loadAddress'] + len(mono), built['players'][1]['loadAddress'])
        self.assertLessEqual(built['loadAddress'] + built['payloadBytes'], 0xa000)

    def test_guard_rejects_one_call_source_handoff_shift(self):
        changed = deepcopy(self.secondary)
        row = next(row for row in self.records['variant']['notes'] if row['voiceIndex'] == 2 and row['call'] == 4786)
        changed['program'][row['nodeId']]['duration'] -= 1
        with self.assertRaisesRegex(ValueError, 'Third source window'):
            self.module.verify(self.source, self.primary, self.module.observe(changed), self.records['source'], self.records['baseline'], self.records['heldEvents'], self.config)


if __name__ == '__main__':
    unittest.main()
