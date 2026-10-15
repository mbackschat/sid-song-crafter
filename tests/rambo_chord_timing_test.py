from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('rambo_chord_timing', ROOT / 'scripts/studies/rambo/check-chord-expansion-timing.py')
timing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(timing)


def sid(load, payload):
    header = bytearray(124)
    header[:4] = b'PSID'
    header[6:8] = (124).to_bytes(2, 'big')
    header[8:10] = load.to_bytes(2, 'big')
    return bytes(header) + payload


def fixture():
    primary = sid(0x1000, b'\x60\x60\x60')
    payload = bytearray(0x200a - 0x0400)
    payload[0xc00:0xc03] = b'\x60\x60\x60'
    candidate_sid = sid(0x0400, bytes(payload))
    source_hash = hashlib.sha256(candidate_sid).hexdigest()
    engine = dict(loadAddress=0x1000, payloadBytes=3,
                  symbols=dict(entry_init=0x1000, entry_play=0x1001), nodeLabels={'note': 'node'})
    secondary = dict(loadAddress=0x2000, payloadBytes=10,
                     symbols=dict(rb_state_begin=0x2000, rb_initial_state=0x2002, rb_restore_state=0x2004))
    built = dict(checkedPlayCalls=4, playCalls=4, sidBases=[0xd400, 0xd420],
                 compositions=[dict(sha256='faithful-source')], symbols=dict(entry_init=0x400, entry_play=0x407),
                 players=[engine, secondary], sidSha256=source_hash)
    initial = [dict(phase='init', tick=None, address=address, value=15, instructionStartCycle=offset)
               for address, offset in ((0xd418, 5), (0xd438, 6))]
    a_writes = initial + [dict(phase='play', tick=call, address=0xd400, value=call + 100, instructionStartCycle=10)
                          for call in range(4)]
    b_writes = deepcopy(a_writes)
    b_writes.insert(4, dict(phase='play', tick=1, address=0xd432, value=65, instructionStartCycle=20))
    profile = dict(loadAddress=0x400, initAddress=0x400, playAddress=0x407, sidModel='MOS6581',
                   sidBases=[0xd400, 0xd420], entryBank=54, profile='pal-banked', hostBase=0xc000)
    studies, traces = [], []
    for writes, shifts in ((a_writes, [0, 0, 0, 0]), (b_writes, [0, 0, 2, 1])):
        entries = [dict(tick=call, writerPc=0x407, monitorCycle=5000 + call * 19656 + shifts[call]) for call in range(4)]
        trace_writes = [dict(row, monitorCycle=(1000 if row['phase'] == 'init' else entries[row['tick']]['monitorCycle'])
                            + row['instructionStartCycle']) for row in writes]
        traces.append(dict(clock='pal', entries=entries, writes=trace_writes,
                           initEntry=dict(monitorCycle=1000), initReturn=dict(monitorCycle=1200)))
        studies.append(dict(profile=deepcopy(profile), harnessSha256='same-host', viceSha256='same-vice',
                            harnessLabels={'entry': 0xc000}, sourceSha256=source_hash, clock='pal',
                            verification=dict(playCalls=4, firstCall=0, lastCall=3, matchedWrites=len(writes),
                                              frameCycles=19656, maximumCadenceError=2, cadenceTolerance=9)))
    return dict(reference_build=deepcopy(built), reference_writes=a_writes, reference_study=studies[0], reference_trace=traces[0],
                candidate_build=deepcopy(built), candidate_writes=b_writes, candidate_study=studies[1], candidate_trace=traces[1],
                candidate_sid=candidate_sid, primary_reference=primary)


class RamboChordTimingTests(unittest.TestCase):
    def test_same_primary_execution_accepts_later_host_jitter_without_claiming_pcm_identity(self):
        proof, deltas = timing.compare(**fixture())
        self.assertTrue(proof['passed'])
        self.assertTrue(proof['primaryPayloadMatchesReference'])
        self.assertEqual(1, proof['firstSecondaryDifferenceCall'])
        self.assertEqual(2, proof['firstHostEntryDifferenceCall'])
        self.assertEqual(5, proof['matchedPrimaryStores'])
        self.assertEqual((0, 2), (proof['hostTiming']['minimumEntryDelta'], proof['hostTiming']['maximumEntryDelta']))
        self.assertEqual(4, len(deltas['entries']))
        self.assertEqual(5, len(deltas['primaryStores']))
        self.assertFalse(any(proof['claims'].values()))

    def test_primary_value_or_within_call_cycle_change_is_rejected(self):
        for field in ('value', 'instructionStartCycle'):
            with self.subTest(field=field):
                values = fixture()
                values['candidate_writes'][2][field] += 1
                with self.assertRaisesRegex(ValueError, 'Primary.*(stores|timing)'):
                    timing.compare(**values)

    def test_a_missing_vice_store_or_entry_cannot_hide_behind_receipt_counts(self):
        for key in ('writes', 'entries'):
            with self.subTest(key=key):
                values = fixture()
                values['candidate_trace'][key].pop()
                with self.assertRaisesRegex(ValueError, 'VICE.*(oracle|coverage)'):
                    timing.compare(**values)

    def test_vice_relative_store_shift_is_rejected_even_when_logical_values_match(self):
        values = fixture()
        values['candidate_trace']['writes'][-1]['monitorCycle'] += 1
        with self.assertRaisesRegex(ValueError, 'offset from its own entry'):
            timing.compare(**values)

    def test_host_jitter_before_secondary_intervention_is_rejected(self):
        values = fixture()
        values['candidate_trace']['entries'][1]['monitorCycle'] += 1
        for row in values['candidate_trace']['writes']:
            if row['tick'] == 1:
                row['monitorCycle'] += 1
        with self.assertRaisesRegex(ValueError, 'before the secondary intervention'):
            timing.compare(**values)

    def test_changed_primary_payload_or_controlled_host_is_rejected(self):
        values = fixture()
        changed = bytearray(values['candidate_sid'])
        changed[124 + 0xc00] = 0xea
        values['candidate_sid'] = bytes(changed)
        with self.assertRaisesRegex(ValueError, 'Primary payload'):
            timing.compare(**values)
        values = fixture()
        values['candidate_study']['harnessSha256'] = 'different-host'
        with self.assertRaisesRegex(ValueError, 'harnessSha256'):
            timing.compare(**values)

    def test_skipped_frame_is_rejected_by_the_existing_vice_cadence_contract(self):
        values = fixture()
        values['candidate_trace']['entries'][-1]['monitorCycle'] += 19656
        with self.assertRaisesRegex(ValueError, 'cadence contract'):
            timing.compare(**values)

    def test_existing_cadence_receipt_bounds_phase_not_adjacent_interval_swings(self):
        values = fixture()
        trace = values['candidate_trace']
        for call, adjustment in ((2, -9), (3, 6)):
            trace['entries'][call]['monitorCycle'] += adjustment
            for row in trace['writes']:
                if row['tick'] == call:
                    row['monitorCycle'] += adjustment
        values['candidate_study']['verification']['maximumCadenceError'] = 7
        proof, _ = timing.compare(**values)
        self.assertTrue(proof['passed'])
        self.assertEqual((-7, 7), (proof['hostTiming']['minimumEntryDelta'], proof['hostTiming']['maximumEntryDelta']))


if __name__ == '__main__':
    unittest.main()
