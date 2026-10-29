import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("instrument_trace", ROOT / "scripts/instrument_trace.py")
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)
LIBRARY_SPEC = importlib.util.spec_from_file_location("instrument_library", ROOT / "scripts/instrument_library.py")
library = importlib.util.module_from_spec(LIBRARY_SPEC)
LIBRARY_SPEC.loader.exec_module(library)

Note = tool.Note
STEADY = (0x08, 0xa5)
C4 = tool.target_word(60)
PULSE, SAW, TRIANGLE, NOISE = 0x40, 0x20, 0x10, 0x80


class Synth:
    """Per-update register states in the layout native-song frame_states returns, built from what the SID-Wizard driver leaves at tempo 1."""

    def __init__(self, updates):
        self.rows = [[0] * 25 for _ in range(updates)]
        for row in self.rows:
            row[24] = 0x0f

    def trace(self):
        return tool.Trace(self.rows)

    def put(self, update, control=None, frequency=None, pulse_width=None, adsr=None, cutoff=None, route=None, mode=None):
        row = self.rows[update]
        if control is not None:
            row[4] = control
        if frequency is not None:
            row[0], row[1] = frequency & 255, frequency >> 8
        if pulse_width is not None:
            row[2], row[3] = pulse_width & 255, pulse_width >> 8
        if adsr is not None:
            row[5], row[6] = adsr
        if cutoff is not None:
            row[21], row[22] = cutoff & 7, cutoff >> 3
        if route is not None:
            row[23] = route
        if mode is not None:
            row[24] = mode

    def hold(self, first, last, **registers):
        for update in range(first, last + 1):
            self.put(update, **registers)

    def note(self, note, until, wave=PULSE, first_wave=None, settle=1, adsr=STEADY, word=None):
        """A TEST frame on the row with the frequency's high byte only, the full pitch from update `settle`, the gate closed at the score gate-off."""
        word = tool.target_word(note.midi) if word is None else word
        off = note.gate_off if note.gate_off is not None else note.end
        for update in range(note.start, until):
            age = update - note.start
            gate = 1 if update < off else 0
            if age == 0:
                self.put(update, control=0x09, frequency=word & 0xff00, adsr=adsr)
            else:
                self.put(update, control=(first_wave if first_wave and age == 1 else wave) | gate, frequency=word if age >= settle else word & 0xff00, adsr=adsr)


def probe_notes():
    return {'long': Note(10, 150, 148, 60), 'short2': Note(170, 172, 172, 60), 'short6': Note(184, 190, 190, 60), 'reentry': Note(366, 396, 394, 60),
            'low': Note(420, 460, 458, 36), 'high': Note(480, 520, 518, 84), 'final': Note(780, 840, 838, 60)}


class NewNoteTest(unittest.TestCase):
    def onset_after_gate_off(self, new_row, hard_restart=False, test_frame=True):
        synth = Synth(60)
        synth.note(Note(10, 20, 20, 60), 30)
        synth.note(Note(new_row, 50, 48, 60), 60)
        if not test_frame:
            synth.put(new_row, control=0x41)
        if hard_restart:
            synth.hold(new_row - 2, new_row - 1, adsr=(0x0f, 0x00))
        return tool.onset(synth.trace(), Note(new_row, 50, 48, 60), STEADY, first=False)

    def test_test_frame_start_after_a_gate_off(self):
        item = self.onset_after_gate_off(30)
        self.assertEqual((item.gate_before, item.edge, item.tests, item.hard_restart), (0, 0, [0], []))
        self.assertEqual(tool.classify_new_note([item, item]), 'test-frame')

    def test_hard_restart_writes_precede_the_note_and_win_over_the_test_frame(self):
        item = self.onset_after_gate_off(30, hard_restart=True)
        self.assertEqual(item.hard_restart, [-2, -1])
        self.assertEqual(tool.classify_new_note([item]), 'hard-restart')

    def test_gate_edge_without_test_frame_is_a_retrigger(self):
        self.assertEqual(tool.classify_new_note([self.onset_after_gate_off(30, test_frame=False)]), 'retrigger')

    def test_a_note_without_a_gate_edge_is_legato(self):
        synth = Synth(60)
        synth.note(Note(10, 50, 50, 60), 60)
        synth.hold(30, 49, control=0x11)      # the gate never falls before the row
        item = tool.onset(synth.trace(), Note(30, 50, 50, 62), STEADY, first=False)
        self.assertEqual((item.gate_before, item.edge), (1, None))
        self.assertEqual(tool.classify_new_note([tool.Onset(0, None, [], [])]), 'legato')

    def test_mixed_or_missing_evidence_is_not_established(self):
        edge, no_edge, tested = tool.Onset(0, 0, [], []), tool.Onset(0, None, [], []), tool.Onset(0, 0, [0], [])
        self.assertEqual(tool.classify_new_note([]), 'not-established')
        self.assertEqual(tool.classify_new_note([edge, no_edge]), 'not-established')
        self.assertEqual(tool.classify_new_note([edge, tested]), 'not-established')
        self.assertEqual(tool.classify_new_note([tool.Onset(0, 0, [], [-1]), edge]), 'not-established')

    def test_new_note_without_gate_off_is_reported_apart_from_the_interface_field(self):
        held = tool.Onset(1, None, [0], [])
        self.assertEqual(tool.classify_without_gate_off([held, held]), 'envelope-continues-with-test-frame')
        self.assertEqual(tool.classify_without_gate_off([tool.Onset(1, None, [], [])]), 'envelope-continues-without-test-frame')
        self.assertEqual(tool.classify_without_gate_off([tool.Onset(1, 0, [0], [])]), 'envelope-restarts')


class PitchTest(unittest.TestCase):
    def tracking(self, shift=0, settle=1):
        notes = probe_notes()
        synth = Synth(900)
        for label, note in notes.items():
            synth.note(note, note.end + 10, settle=settle, word=tool.target_word(note.midi + shift))
        return synth.trace(), notes

    def test_pitch_that_follows_the_score_is_absolute(self):
        response, offset, _ = tool.pitch_response(*self.tracking())
        self.assertEqual((response, offset), ('absolute', 0))

    def test_a_constant_octave_offset_is_still_tracking(self):
        response, offset, _ = tool.pitch_response(*self.tracking(shift=12))
        self.assertEqual((response, offset), ('absolute', 12))

    def test_pitch_that_ignores_the_score_is_percussion(self):
        notes = probe_notes()
        synth = Synth(900)
        for note in notes.values():
            synth.note(note, note.end + 10, word=2400)
        response, offset, facts = tool.pitch_response(synth.trace(), notes)
        self.assertEqual((response, offset, facts['fixedPitch']), ('percussion', None, True))

    def test_pitch_that_neither_tracks_nor_stays_is_not_classified(self):
        notes = probe_notes()
        synth = Synth(900)
        for label, note in notes.items():
            synth.note(note, note.end + 10, word=tool.target_word(60 + {'low': -7, 'high': 7}.get(label, 0)))
        self.assertIsNone(tool.pitch_response(synth.trace(), notes)[0])

    def test_pitch_settles_on_the_update_after_the_first_full_pitch_frame(self):
        trace, notes = self.tracking(settle=1)
        value, facts = tool.pitch_settles(trace, notes, 0)
        self.assertEqual(value, 2)
        self.assertEqual(facts['shortNotesSoundFullPitch'], {'short2': True, 'short6': True})
        trace, notes = self.tracking(settle=3)
        value, facts = tool.pitch_settles(trace, notes, 0)
        self.assertEqual(value, 4)
        self.assertEqual(facts['shortNotesSoundFullPitch'], {'short2': False, 'short6': True})

    def test_a_pitch_that_does_not_track_has_no_settle_time(self):
        trace, notes = self.tracking()
        self.assertEqual(tool.pitch_settles(trace, notes, None)[0], None)


class WaveformTest(unittest.TestCase):
    def test_staged_onset_leaves_for_good_after_a_few_updates(self):
        self.assertTrue(tool.staged_onset([[SAW, 1], [TRIANGLE, 139]]))
        self.assertFalse(tool.staged_onset([[TRIANGLE, 20], [PULSE, 120]]), "a long first section is a waveform change, not a staged onset")
        self.assertFalse(tool.staged_onset([[SAW, 1], [TRIANGLE, 3], [SAW, 5]]), "a returning waveform is a sequence")
        self.assertFalse(tool.staged_onset([[PULSE, 140]]))

    def test_test_frame_sounds_no_waveform_and_a_staged_wave_is_listed_first(self):
        synth = Synth(60)
        note = Note(10, 40, 40, 60)
        synth.note(note, 50, wave=TRIANGLE, first_wave=SAW)
        waves = tool.waveform_facts(synth.trace(), note)
        self.assertEqual(waves['runs'], [[SAW, 1], [TRIANGLE, 28]])
        self.assertEqual(waves['runStarts'], [1, 2])
        self.assertEqual(tool.waveform_sequence(waves['runs']), (['saw', 'triangle'], [[TRIANGLE, 28]]))

    def test_combined_waveform_bits_name_each_waveform(self):
        self.assertEqual(tool.waveform_names(0x50), ['triangle', 'pulse'])


class BodyTest(unittest.TestCase):
    NOTE = Note(10, 150, 148, 60)

    def analyse(self, shape=None, wave=PULSE, first_wave=None):
        """Facts of a long note after `shape(synth, age_of_update)` has written its modulation into the body."""
        synth = Synth(200)
        synth.note(self.NOTE, 160, wave=wave, first_wave=first_wave)
        for update in range(self.NOTE.start + 1, self.NOTE.gate_off):
            if shape:
                shape(synth, update, update - self.NOTE.start)
        trace = synth.trace()
        waves = tool.waveform_facts(trace, self.NOTE)
        return waves, tool.body_facts(trace, self.NOTE, C4)

    def test_moving_pulse_width_makes_a_moving_pulse_body_with_an_immediate_pwm(self):
        waves, body = self.analyse(lambda synth, update, age: synth.put(update, pulse_width=1024 + 32 * (age - 1)))
        self.assertEqual(tool.classify_body(waves, body), 'moving-pulse')
        self.assertEqual(tool.motions(waves, body), [('pwm', 2)])

    def test_a_fixed_pulse_width_is_a_static_body_without_motion(self):
        waves, body = self.analyse(lambda synth, update, age: synth.put(update, pulse_width=1536))
        self.assertEqual((tool.classify_body(waves, body), tool.motions(waves, body)), ('static', []))

    @staticmethod
    def vibrato_from(start, depth=11):
        offsets = (depth, 0, -depth, 0)
        return lambda synth, update, age: synth.put(update, frequency=C4 + offsets[(age - start) % 4]) if age >= start else None

    def test_a_delayed_vibrato_reports_the_update_it_starts_at_and_leaves_the_body_static(self):
        waves, body = self.analyse(self.vibrato_from(22))
        self.assertEqual(tool.motions(waves, body), [('delayed-vibrato', 22)])
        self.assertEqual(tool.classify_body(waves, body), 'static')

    def test_a_vibrato_from_the_start_is_not_delayed(self):
        waves, body = self.analyse(self.vibrato_from(2))
        self.assertEqual(tool.motions(waves, body), [('vibrato', 2)])

    def test_a_sweeping_cutoff_makes_a_moving_filter_body(self):
        waves, body = self.analyse(lambda synth, update, age: synth.put(update, cutoff=max(640, 1024 - 16 * (age - 1)), route=0x41))
        self.assertEqual(tool.classify_body(waves, body), 'moving-filter')
        self.assertEqual(tool.motions(waves, body), [('filter-sweep', 2)])

    def test_stepping_between_chord_pitches_is_an_arpeggio(self):
        steps = (C4, round(C4 * 2 ** (4 / 12)), round(C4 * 2 ** (7 / 12)))
        waves, body = self.analyse(lambda synth, update, age: synth.put(update, frequency=steps[age % 3]))
        self.assertEqual(tool.classify_body(waves, body), 'arpeggio')
        self.assertEqual([kind for kind, _ in tool.motions(waves, body)], ['arpeggio'])

    def test_a_falling_pitch_is_a_bend_and_a_pitch_animated_body(self):
        waves, body = self.analyse(lambda synth, update, age: synth.put(update, frequency=round(C4 * 0.98 ** min(age, 16))))
        self.assertEqual(tool.classify_body(waves, body), 'pitch-animated')
        self.assertEqual([kind for kind, _ in tool.motions(waves, body)], ['pitch-bend'])

    def test_a_pitch_step_that_fits_no_category_leaves_the_body_unestablished(self):
        waves, body = self.analyse(lambda synth, update, age: synth.put(update, frequency=round(C4 * 1.1)) if age >= 20 else None)
        self.assertIsNone(tool.classify_body(waves, body))

    def test_noise_dominating_the_body_is_a_noise_body(self):
        waves, body = self.analyse(wave=NOISE)
        self.assertEqual(tool.classify_body(waves, body), 'noise')

    def test_alternating_waveforms_are_a_sequence_and_a_waveform_change(self):
        waves, body = self.analyse(lambda synth, update, age: synth.put(update, control=(SAW if age // 5 % 2 else PULSE) | 1))
        self.assertEqual(tool.classify_body(waves, body), 'waveform-sequence')
        self.assertEqual(tool.motions(waves, body)[-1], ('waveform-change', 5))

    def test_a_staged_onset_is_not_a_waveform_change(self):
        waves, body = self.analyse(wave=TRIANGLE, first_wave=SAW)
        self.assertEqual((tool.classify_body(waves, body), tool.motions(waves, body)), ('static', []))

    def test_a_note_whose_gate_closes_at_once_has_no_body_facts(self):
        synth = Synth(60)
        synth.note(Note(10, 50, 12, 60), 60)
        self.assertIsNone(tool.body_facts(synth.trace(), Note(10, 50, 12, 60), C4))


class ResourcesTest(unittest.TestCase):
    def test_a_program_that_sets_the_filter_and_routes_its_voice_owns_it(self):
        self.assertEqual(tool.classify_filter(True, True), 'owner')
        self.assertEqual(tool.classify_filter(True, False), 'routed')
        self.assertEqual(tool.classify_filter(False, True), 'none')
        self.assertEqual(tool.classify_filter(False, False), 'none')

    def test_resource_facts_read_routing_cutoff_coupling_and_volume_from_gated_updates(self):
        synth = Synth(40)
        note = Note(10, 30, 30, 60)
        synth.note(note, 40)
        synth.hold(11, 29, cutoff=1024, route=0x41, mode=0x1f, control=0x45)
        facts = tool.resource_facts(synth.trace(), 40)
        self.assertEqual((facts['routesVoice'], facts['setsFilterParameters'], facts['ring'], facts['sync'], facts['volumeNibbles']), (True, True, True, False, [15]))
        self.assertEqual(tool.resource_fields(facts), {'filter': 'owner', 'masterVolume': 'none', 'coupling': {'kind': 'ring', 'partner': 'preceding-oscillator'}})

    def test_a_program_that_changes_the_volume_writes_the_master_volume(self):
        synth = Synth(40)
        synth.note(Note(10, 30, 30, 60), 40)
        synth.hold(11, 29, mode=0x0a)
        self.assertEqual(tool.resource_fields(tool.resource_facts(synth.trace(), 40))['masterVolume'], 'writes')

    def test_ring_and_sync_together_are_not_expressible(self):
        self.assertIsNone(tool.classify_coupling(True, True))
        self.assertEqual(tool.classify_coupling(False, True), {'kind': 'sync', 'partner': 'preceding-oscillator'})
        self.assertEqual(tool.classify_coupling(False, False), 'none')


class ReleaseTest(unittest.TestCase):
    FINAL = Note(100, 160, 158, 60)

    def tail(self, program=None, stop=300):
        synth = Synth(stop + 2)
        synth.note(self.FINAL, stop)
        for update in range(self.FINAL.gate_off, stop):
            if program:
                program(synth, update)
        return synth.trace()

    def test_a_program_that_keeps_changing_registers_after_the_gate_off_continues(self):
        trace = self.tail(lambda synth, update: synth.put(update, pulse_width=1024 + 32 * (update % 20)))
        value, facts = tool.classify_after_gate_off(trace, self.FINAL.gate_off, 300)
        self.assertEqual(value, 'program-continues')
        self.assertEqual(facts['lastChange'], 300 - 1 - self.FINAL.gate_off)

    def test_registers_that_stay_put_after_the_gate_off_are_release_only(self):
        self.assertEqual(tool.classify_after_gate_off(self.tail(), self.FINAL.gate_off, 300)[0], 'release-only')

    def test_the_gate_bit_alone_is_not_a_program_change(self):
        trace = self.tail()
        self.assertNotEqual(trace.control(self.FINAL.gate_off), trace.control(self.FINAL.gate_off - 1))
        self.assertEqual(tool.classify_after_gate_off(trace, self.FINAL.gate_off, 300)[0], 'release-only')

    def test_without_a_tail_nothing_is_established(self):
        self.assertEqual(tool.classify_after_gate_off(self.tail(), self.FINAL.gate_off, self.FINAL.gate_off + 1)[0], 'not-established')

    def test_a_gate_that_closes_with_the_score_ends_when_the_release_ends(self):
        self.assertEqual(tool.classify_lifetime(self.tail(), self.FINAL, 300)[0], 'until-release-ends')

    def test_a_gate_that_stays_open_lasts_until_the_next_note(self):
        trace = self.tail(lambda synth, update: synth.put(update, control=0x41))
        self.assertEqual(tool.classify_lifetime(trace, self.FINAL, 300)[0], 'until-next-note')

    def test_a_program_that_closes_its_own_gate_cannot_be_timed_from_registers(self):
        synth = Synth(302)
        synth.note(self.FINAL, 300)
        synth.hold(103, 157, control=0x40)
        value, facts = tool.classify_lifetime(synth.trace(), self.FINAL, 300)
        self.assertEqual((value, facts['gateClosedAtUpdate']), ('not-established', 3))

    def test_a_program_that_mutes_its_voice_while_gated_is_not_timed_either(self):
        synth = Synth(302)
        synth.note(self.FINAL, 300)
        synth.hold(120, 157, control=0x01)
        self.assertEqual(tool.classify_lifetime(synth.trace(), self.FINAL, 300)[0], 'not-established')


class TieTest(unittest.TestCase):
    CONTROL, FIRST, TIED = Note(10, 150, 148, 60), Note(200, 260, None, 60), Note(260, 330, 328, 67)

    @staticmethod
    def sweep(age):
        """A pulse width that rises for 20 updates and falls for 20, so a restart and a continuation differ."""
        phase = age % 40
        return 1000 + 32 * (phase if phase <= 20 else 40 - phase)

    def leg(self, tied_age, stall=0, retrigger=False, program=True):
        """Control note, a first note and its tied successor whose pulse program is `tied_age(updates after the tie row)`."""
        synth = Synth(400)
        for note in (self.CONTROL, self.FIRST, self.TIED):
            synth.note(note, note.end + 10)
        synth.put(self.TIED.start, control=0x41, frequency=C4)     # a tie writes no TEST frame and sets the new pitch one update later
        if program:
            for update in range(self.CONTROL.start + 1, self.CONTROL.gate_off):
                synth.put(update, pulse_width=self.sweep(update - self.CONTROL.start))
            for update in range(self.FIRST.start + 1, self.FIRST.end):
                synth.put(update, pulse_width=self.sweep(update - self.FIRST.start))
            for update in range(self.TIED.start + 1, self.TIED.gate_off):
                synth.put(update, pulse_width=self.sweep(tied_age(update - self.TIED.start)))
        if retrigger:
            synth.put(self.TIED.start + 2, control=0x09)
        return tool.tie_point(synth.trace(), self.CONTROL, self.FIRST, self.TIED, 0)

    def test_a_program_that_keeps_running_across_the_tie_continues(self):
        point = self.leg(lambda k: 60 + k)
        self.assertEqual((point['envelopeKept'], point['series']['pulse width']['verdict']), (True, 'continues'))
        self.assertEqual(tool.classify_tie([point]), 'keep-envelope-and-program')

    def test_a_tie_row_that_stalls_the_program_by_an_update_still_continues(self):
        point = self.leg(lambda k: 60 + k - 1)
        self.assertEqual(point['series']['pulse width']['verdict'], 'continues')
        self.assertEqual(point['series']['pulse width']['stallVsContinue'], 1)

    def test_a_program_that_starts_over_at_the_tie_restarts(self):
        point = self.leg(lambda k: k)
        self.assertEqual(point['series']['pulse width']['verdict'], 'restarts')
        self.assertEqual(tool.classify_tie([point]), 'restart-program')

    def test_a_program_that_does_neither_leaves_the_tie_unestablished(self):
        point = self.leg(lambda k: 11 * k)
        self.assertEqual(point['series']['pulse width']['verdict'], 'neither')
        self.assertEqual(tool.classify_tie([point]), 'not-established')

    def test_a_restarted_envelope_is_a_restart_whatever_the_program_does(self):
        point = self.leg(lambda k: 60 + k, retrigger=True)
        self.assertFalse(point['envelopeKept'])
        self.assertEqual(tool.classify_tie([point]), 'restart-program')

    def test_a_program_with_nothing_moving_keeps_by_the_absence_of_a_restart_sign(self):
        point = self.leg(None, program=False)
        self.assertEqual({item['verdict'] for item in point['series'].values()}, {'static'})
        self.assertEqual(tool.classify_tie([point]), 'keep-envelope-and-program')

    def test_a_series_that_cannot_tell_continue_from_restart_is_no_evidence_alone(self):
        point = {'envelopeKept': True, 'series': {'pulse width': {'verdict': 'indistinct'}, 'pitch': {'verdict': 'static'}}}
        self.assertEqual(tool.classify_tie([point]), 'not-established')
        point['series']['pitch'] = {'verdict': 'continues'}
        self.assertEqual(tool.classify_tie([point]), 'keep-envelope-and-program')
        point['series']['waveform'] = {'verdict': 'restarts'}
        self.assertEqual(tool.classify_tie([point]), 'not-established')


def static_instrument():
    record = json.loads((ROOT / "songs/instruments/lead.static-pulse@1.json").read_text())
    return tool.program_instrument(record)


def converted_notes(directory):
    score, recipe = tool.inputs(static_instrument(), tool.clock_spec("pal").ticks_per_second)
    directory = Path(directory)
    (directory / "score.json").write_text(json.dumps(score))
    (directory / "recipe.json").write_text(json.dumps(recipe))
    manifest = tool.load_script("arrange-sidwizard").arrange(directory / "recipe.json", directory / "conversion")
    return manifest, tool.notes_from_manifest(manifest)


def driven(notes, stop, first_wave=None):
    """The registers a static SID-Wizard instrument leaves for the whole probe phrase: a TEST frame on each untied row, the pitch one update later, the gate closed at each gate-off cell."""
    synth = Synth(stop + 2)
    tied = {label for _, label in tool.TIE_LEGS}
    starts = {note.start: label for label, note in notes.items()}
    gate_offs = {note.gate_off for note in notes.values() if note.gate_off is not None}
    gate = word = sounded = 0
    landing = None      # (update at which the pitch lands, its word, whether the note is tied)
    for update in range(stop + 2):
        control = (PULSE | gate) if sounded else 0
        if update in starts:
            label = starts[update]
            landing = (update + 1, tool.target_word(notes[label].midi), label in tied)
            if label not in tied:
                gate = sounded = 1
                control, word = 0x09, landing[1] & 0xff00
        elif landing and update == landing[0]:
            word = landing[1]
            control = (PULSE if landing[2] else first_wave or PULSE) | gate
            landing = None
        if update in gate_offs:
            gate, control = 0, PULSE
        synth.put(update, control=control, frequency=word, adsr=STEADY)
    return synth.trace()


class DeriveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.manifest, cls.notes = converted_notes(cls.temp.name)
        cls.stop = cls.manifest["stopTick"]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_converter_places_the_phrase_as_declared(self):
        self.assertEqual(self.notes["long"], Note(10, 150, 148, 60))
        self.assertIsNone(self.notes["tie_late_a"].gate_off, "a tie withholds the previous note's gate-off")
        self.assertEqual([note["tied"] for note in self.manifest["voices"][0]["notes"] if note.get("tied")], [True, True])
        changed = copy.deepcopy(self.manifest)
        changed["voices"][0]["notes"][3]["midi"] += 1
        with self.assertRaisesRegex(ValueError, "changed the probe phrase"):
            tool.notes_from_manifest(changed)

    def test_a_static_instrument_derives_the_whole_standard_interface(self):
        fields, facts = tool.derive(driven(self.notes, self.stop), self.notes, self.stop)
        interface = fields["interface"]
        self.assertEqual({key: interface[key] for key in ("onNewNote", "onTie", "afterGateOff", "lifetime", "pitchResponse")},
                         {"onNewNote": "test-frame", "onTie": "keep-envelope-and-program", "afterGateOff": "release-only", "lifetime": "until-release-ends", "pitchResponse": "absolute"})
        self.assertEqual(interface["pitchSettlesAfterUpdates"]["value"], 2)
        self.assertEqual(facts["newNote"]["withoutGateOff"], "envelope-continues-with-test-frame")
        self.assertEqual(fields["resources"], {"filter": "none", "masterVolume": "none", "coupling": "none"})
        character = fields["character"]
        self.assertEqual((character["waveforms"]["value"], character["body"]["value"], character["motion"]), (["pulse"], "static", []))
        self.assertNotIn("attack", character, "a plain onset leaves the envelope category in place")

    def test_derived_fields_satisfy_the_library_contract(self):
        for staged in (False, True):
            with self.subTest(staged=staged):
                fields, _ = tool.derive(driven(self.notes, self.stop, first_wave=SAW if staged else None), self.notes, self.stop)
                record = json.loads((ROOT / "songs/instruments/lead.static-pulse@1.json").read_text())
                keys = [list(record[group]) for group in ("interface", "character", "resources")]
                merged = tool.merge(copy.deepcopy(record), fields)
                library.validate_interface(merged["interface"], "interface", ROOT)
                library.validate_character(merged["character"], "character", ROOT)
                library.validate_resources(merged["resources"], "resources")
                self.assertEqual([[key for key in merged[group] if key in record[group]] for group in ("interface", "character", "resources")], keys, "merge keeps the record's key order")
                for claim in (fields["interface"]["pitchSettlesAfterUpdates"], fields["character"]["waveforms"], *fields["character"]["motion"]):
                    self.assertTrue(claim["detail"].startswith(tool.PROBE_ID))
                    self.assertEqual(claim["basis"], "measured")
                self.assertEqual(fields["character"].get("attack", {}).get("value"), "staged" if staged else None)

    def test_summary_flattens_claims_and_motion(self):
        fields = {"interface": {"pitchSettlesAfterUpdates": tool.measured(2, "x"), "onTie": "keep-envelope-and-program"}, "character": {"body": tool.UNKNOWN, "motion": [tool.measured("delayed-vibrato", "x", startsAfterUpdates=22), tool.measured("pwm", "x")]}}
        self.assertEqual(tool.summary(fields), {"interface.pitchSettlesAfterUpdates": 2, "interface.onTie": "keep-envelope-and-program", "character.body": "unknown",
                                                "character.motion": [["delayed-vibrato", 22], ["pwm", None]]})

    def test_command_refuses_an_existing_output_directory(self):
        with tempfile.TemporaryDirectory() as existing:
            done = subprocess.run([sys.executable, str(ROOT / "scripts/instrument_trace.py"), str(ROOT / "songs/instruments/lead.static-pulse@1.json"), "--output", existing], capture_output=True, text=True)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("fresh directory", done.stderr)


if __name__ == "__main__":
    unittest.main()
