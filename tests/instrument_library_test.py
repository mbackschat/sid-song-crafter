import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("instrument_library", ROOT / "scripts/instrument_library.py")
library = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(library)

INSTRUMENT = {"adsr": "4676", "control": "0a", "filter": [], "frame1": "09", "hard_restart_adsr": "0f00", "name": "SOFTLEAD", "pulse": [], "wave": [["11", "00", "00"]]}
PROBE = "probe-level-v1: one note at MIDI 69"


def arrangement(instruments):
    return {"format": "sidwizard-arrangement-v1", "instruments": instruments}


def record():
    return {
        "id": "lead.triangle-soft",
        "version": 1,
        "name": "Soft triangle lead",
        "program": {"engine": "sidwizard-extra-1.97", "file": "songs/a/native.json", "record": "instruments.lead"},
        "interface": {
            "scoreSupplies": ["pitch", "onset", "gateOff"], "pitchResponse": "absolute", "parameters": [],
            "scoreOwned": ["gate-off timing"], "onNewNote": "test-frame", "onTie": "keep-envelope-and-program",
            "afterGateOff": "release-only", "lifetime": "until-release-ends",
            "pitchSettlesAfterUpdates": {"value": 2, "basis": "measured", "detail": "probe trace"}, "state": []},
        "resources": {"voices": 1, "coupling": "none", "filter": "none", "masterVolume": "none", "chipModels": ["MOS8580"], "clocks": ["PAL"], "updateRate": "frame"},
        "character": {
            "summary": "Gated triangle with a 38 ms attack.",
            "waveforms": {"value": ["triangle"], "basis": "measured", "detail": "wave table $11"},
            "envelope": {"attack": 4, "decay": 6, "sustain": 7, "release": 6, "attackMs": 38, "releaseMs": 204},
            "attack": {"value": "soft", "basis": "measured", "detail": "attack nibble 4"},
            "body": {"value": "static", "basis": "measured", "detail": "empty pulse and filter tables"},
            "release": {"value": "medium", "basis": "measured", "detail": "release nibble 6"},
            "level": {"value": {"onsetDb": -27.6, "sustainDb": -28.8}, "basis": "measured", "detail": PROBE},
            "brightness": {"value": {"onset": 1.0, "body": 1.0}, "basis": "measured", "detail": PROBE},
            "motion": [{"value": "delayed-vibrato", "basis": "measured", "detail": "probe trace", "startsAfterUpdates": 22}]},
        "fit": {"roles": ["lead"], "avoid": []},
        "provenance": {"origin": "original", "sourceWork": "Work A", "card": "songs/a/README.md", "rights": "MIT"},
    }


def verdict(work="Work A", result="accepted", quote="quite nice"):
    return {
        "id": "v-a-accepted", "attribution": "group", "members": ["lead.triangle-soft@1", "bass.triangle-plain@1"],
        "context": {"work": work, "roles": {"lead.triangle-soft@1": "melody", "bass.triangle-plain@1": "bass"},
                    "tempoBpm": 70, "meter": "3/4", "moodBrief": "tender", "material": "complete"},
        "result": result, "quote": quote, "record": "songs/a/listening-review.json"}


def bass():
    value = record()
    value.update(id="bass.triangle-plain", name="Plain triangle bass")
    value["program"] = {**value["program"], "record": "instruments.bass"}
    value["fit"] = {"roles": ["bass"], "avoid": []}
    return value


class CheckedInLibraryTest(unittest.TestCase):
    def test_checked_in_library_validates_and_its_index_is_current(self):
        records, verdicts = library.load(ROOT)
        self.assertEqual(library.encode(library.index(records, verdicts, ROOT)), (ROOT / library.INDEX).read_text())


class InstrumentLibraryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.write("songs/a/native.json", arrangement({"lead": INSTRUMENT, "bass": {**INSTRUMENT, "adsr": "0535", "name": "BASS"}}))
        self.write("songs/b/native.json", arrangement({"tune": {**INSTRUMENT, "name": "RELABEL"}}))
        self.write("songs/a/listening-review.json", {"feedback": "quite nice", "later": "I like ours better."})
        (self.root / "songs/a/README.md").write_text("# A\n")
        self.records = [record(), bass()]
        self.verdicts = [verdict()]

    def tearDown(self):
        self.temp.cleanup()

    def write(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value))

    def store(self):
        for value in self.records:
            self.write(f'songs/instruments/{value["id"]}@{value["version"]}.json', value)
        for value in self.verdicts:
            self.write(f'songs/instruments/verdicts/{value["id"]}.json', value)
        return library.load(self.root)

    def rejects(self, mutate, message):
        mutate(self.records, self.verdicts)
        with self.assertRaisesRegex(ValueError, message):
            self.store()

    def test_valid_library_derives_verdicts_level_partners_and_occurrences(self):
        entry = library.index(*self.store(), self.root)["instruments"]["lead.triangle-soft@1"]
        self.assertEqual(entry["verdicts"], [{"id": "v-a-accepted", "side": "member", "result": "accepted", "attribution": "group", "work": "Work A"}])
        self.assertEqual(entry["evidenceLevel"], "listening-reviewed")
        self.assertEqual(entry["acceptedWith"], ["bass.triangle-plain@1"])
        self.assertEqual(entry["occurrences"], ["songs/a/native.json#instruments.lead", "songs/b/native.json#instruments.tune"])
        self.assertFalse(entry["reusable"])

    def test_reusable_needs_acceptance_on_another_work_and_an_established_interface(self):
        self.verdicts = [verdict(work="Work B")]
        self.assertTrue(library.index(*self.store(), self.root)["instruments"]["lead.triangle-soft@1"]["reusable"])
        self.records[0]["interface"]["lifetime"] = "not-established"
        self.assertFalse(library.index(*self.store(), self.root)["instruments"]["lead.triangle-soft@1"]["reusable"])

    def test_evidence_level_is_computed_from_the_verdicts_present(self):
        # The stored level of the first contract survived the removal of every verdict behind it (S2v2).
        self.verdicts = []
        self.assertEqual(library.index(*self.store(), self.root)["instruments"]["lead.triangle-soft@1"]["evidenceLevel"], "rendered-experiment")

    def test_comparison_side_is_reported(self):
        self.verdicts = [{**verdict(result="preferred"), "members": ["bass.triangle-plain@1"], "comparedWith": ["lead.triangle-soft@1"],
                          "context": {**verdict()["context"], "roles": {"bass.triangle-plain@1": "bass"}}}]
        entry = library.index(*self.store(), self.root)["instruments"]["lead.triangle-soft@1"]
        self.assertEqual(entry["verdicts"][0]["side"], "rejected-alternative")

    def test_rejects_unknown_fields(self):
        self.rejects(lambda r, v: r[0].update(heardAs=[]), "unknown fields")

    def test_rejects_claims_based_on_hearing(self):
        self.rejects(lambda r, v: r[0]["character"].update(attack={"value": "soft", "basis": "heard", "detail": "x"}), "basis")

    def test_rejects_unknown_with_a_value(self):
        self.rejects(lambda r, v: r[0]["character"].update(body={"value": "static", "basis": "unknown"}), "unknown fields")

    def test_rejects_known_claim_without_detail(self):
        self.rejects(lambda r, v: r[0]["character"]["body"].pop("detail"), "missing fields")

    def test_rejects_attack_category_that_contradicts_the_thresholds(self):
        self.rejects(lambda r, v: r[0]["character"]["attack"].update(value="hard"), "attack.*threshold")

    def test_rejects_release_category_that_contradicts_the_thresholds(self):
        self.rejects(lambda r, v: r[0]["character"]["release"].update(value="long"), "release.*threshold")

    def test_rejects_envelope_times_that_do_not_match_the_nibbles(self):
        self.rejects(lambda r, v: r[0]["character"]["envelope"].update(attackMs=40), "attackMs")

    def test_rejects_intent_on_a_trait_the_envelope_measures(self):
        self.rejects(lambda r, v: r[0]["character"]["attack"].update(basis="intent"), "measured")

    def test_rejects_probe_values_without_probe_version(self):
        self.rejects(lambda r, v: r[0]["character"]["level"].update(detail="render"), "probe")

    def test_rejects_id_prefix_outside_the_roles(self):
        self.rejects(lambda r, v: r[0].update(id="pluck.triangle-soft"), "role")

    def test_rejects_file_name_that_differs_from_the_identity(self):
        self.store()
        (self.root / "songs/instruments/lead.triangle-soft@1.json").rename(self.root / "songs/instruments/lead.other@1.json")
        with self.assertRaisesRegex(ValueError, "file name"):
            library.load(self.root)

    def test_rejects_byte_identical_programs_in_two_records(self):
        def mutate(r, v):
            r[1]["program"] = {**r[1]["program"], "file": "songs/b/native.json", "record": "instruments.tune"}
        self.rejects(mutate, "identical program")

    def test_rejects_missing_program_reference(self):
        self.rejects(lambda r, v: r[0]["program"].update(record="instruments.missing"), "program")

    def test_rejects_paraphrased_quote(self):
        self.rejects(lambda r, v: v[0].update(quote="very nice"), "verbatim")

    def test_rejects_preference_without_comparison(self):
        self.rejects(lambda r, v: v[0].update(result="preferred"), "comparedWith")

    def test_rejects_verdict_naming_no_library_version(self):
        def mutate(r, v):
            v[0].update(members=[], comparedWith=[{"description": "another rendition"}])
            v[0]["context"]["roles"] = {}
        self.rejects(mutate, "names no library version")

    def test_rejects_unresolved_member(self):
        self.rejects(lambda r, v: v[0]["members"].append("lead.missing@1"), "unknown instrument")

    def test_rejects_avoid_without_basis(self):
        self.rejects(lambda r, v: r[0]["fit"]["avoid"].append({"condition": "a second filter owner"}), "avoid")

    def test_rejects_avoid_citing_unknown_verdict(self):
        self.rejects(lambda r, v: r[0]["fit"]["avoid"].append({"condition": "x", "verdict": "v-missing"}), "unknown verdict")


if __name__ == "__main__":
    unittest.main()
