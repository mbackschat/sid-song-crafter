import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("composition_package", ROOT / "scripts/composition-package.py")
producer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(producer)


class CompositionPackageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = producer.generate(ROOT)

    def test_generated_package_is_deterministic_and_committed(self):
        expected = (ROOT / "samples/composition/rambo-main.json").read_bytes()
        self.assertEqual(producer.encode(self.package), expected)
        self.assertEqual(producer.encode(producer.generate(ROOT)), expected)

    def test_exact_binding_matches_catalog_and_main_entry_receipt(self):
        source = producer.PinnedSource(ROOT)
        index = json.loads((ROOT / "samples/catalog/index.json").read_bytes())
        entry = next(e for e in index["entries"] if e["id"] == "rambo-loader-main")
        binding = self.package["binding"]
        self.assertEqual(binding["sidSha256"], entry["files"]["sid"]["sha256"])
        self.assertEqual(binding["sidSha256"], hashlib.sha256(source.blob(entry["files"]["sid"]["path"])).hexdigest())
        manifest = source.json("samples/rambo-loader/main-manifest.json")
        self.assertEqual(self.package["timing"]["sourceStartCall"], manifest["sourceStartCall"])
        self.assertEqual(self.package["timing"]["timeBasis"], "source-call-grid")
        for field in ("subtune", "clock", "sidCount", "baseAddress", "routing"):
            self.assertEqual(binding[field], entry["target"][field])

    def test_note_intervals_and_pitch_match_original_cpu_observations(self):
        source = producer.PinnedSource(ROOT)
        original = source.json(producer.CPU_PATH)
        fetches = {(e["call"], e["voice"], e["stream"]): e for e in original
                   if e["kind"] == "fetch" and e.get("rowKind") == "note"}
        rows = [e for e in original if e["kind"] == "row-duration-store"]
        for passage in self.package["passages"]:
            actual = passage["events"]
            for event in actual:
                voice = next(a["voice"] - 1 for a in self.package["allocations"] if a["partId"] == event["partId"])
                fetched = fetches[event["sourceCall"], voice, event["sourceAddress"]]
                raw = fetched["upcomingBytes"][0]
                transpose = fetched["state"]["voices"][voice]["transpose"]
                self.assertEqual(event["pitchIndex"], ((raw % 96) + transpose) & 255)
                following = next(r for r in rows if r["voice"] == voice and r["call"] > event["sourceCall"])
                self.assertEqual(event["endSourceCall"], following["call"])
                self.assertLess(event["sourceCall"], passage["sourceEndCall"])
                self.assertGreater(event["endSourceCall"], passage["sourceStartCall"])

    def test_coverage_contains_every_intersecting_original_note_row(self):
        original = producer.PinnedSource(ROOT).json(producer.CPU_PATH)
        rows = [e for e in original if e["kind"] == "row-duration-store"]
        for passage in self.package["passages"]:
            expected = set()
            for event in original:
                if event["kind"] != "fetch" or event.get("rowKind") != "note" or event["call"] >= passage["sourceEndCall"]:
                    continue
                later = next((r["call"] for r in rows if r["voice"] == event["voice"] and r["call"] > event["call"]), None)
                if later is not None and later > passage["sourceStartCall"]:
                    expected.add((event["call"], event["voice"] + 1, event["stream"]))
            actual = {(event["sourceCall"], next(a["voice"] for a in self.package["allocations"] if a["partId"] == event["partId"]), event["sourceAddress"]) for event in passage["events"]}
            self.assertEqual(actual, expected)

    def test_source_mismatches_fail_before_export(self):
        original_json = producer.PinnedSource.json
        for kind in ("profile", "pitch", "address"):
            def corrupted(instance, path):
                value = original_json(instance, path)
                if path == producer.SCORE_PATH and kind == "profile":
                    value["profile"]["clock"] = "NTSC"
                if path == producer.NOTE_PATH and kind in ("pitch", "address"):
                    event = next(e for e in value if e["call"] == 5427 and e["voiceIndex"] == 0)
                    event["pitchIndex" if kind == "pitch" else "sourceAddress"] += 1
                return value
            with self.subTest(kind=kind), patch.object(producer.PinnedSource, "json", corrupted):
                with self.assertRaises(ValueError):
                    producer.generate(ROOT)

    def test_numeric_player_independently_reproduces_selected_patch_and_note_entries(self):
        from rambo_player import LoaderPlayer
        source = producer.PinnedSource(ROOT)
        description = source.json(producer.SCORE_PATH)
        observed = {}
        class Observed(LoaderPlayer):
            def note(self, event):
                observed[event["call"], event["voiceIndex"]] = (event["pitchIndex"], copy.deepcopy(self.data[event["voiceIndex"]]), copy.deepcopy(self.sound[event["voiceIndex"]]))
                super().note(event)
        player = Observed(description)
        for call in range(5683):
            player.play(call)
        programs = {p["id"]: p for p in self.package["instruments"]}
        for passage in self.package["passages"]:
            for event in passage["events"]:
                voice = next(a["voice"] - 1 for a in self.package["allocations"] if a["partId"] == event["partId"])
                pitch, data, sound = observed[event["sourceCall"], voice]
                self.assertEqual((event["pitchIndex"], programs[event["instrumentId"]]["program"]["data"], event["entrySound"]), (pitch, data, sound))
                self.assertEqual(event["frequencyWord"], description["frequencyWords"][pitch])

    def test_recurrence_is_same_lead_phrase_with_changed_bass(self):
        first, second = self.package["passages"]
        def signature(passage, part):
            return [(e["sourceCall"] - passage["sourceStartCall"], e["nodeId"], e["pitchIndex"])
                    for e in passage["events"] if e["partId"] == part and e["sourceCall"] >= passage["sourceStartCall"]]
        self.assertEqual(signature(first, "lead"), signature(second, "lead"))
        a, b = signature(first, "bass"), signature(second, "bass")
        self.assertEqual([(t,n) for t,n,_ in a], [(t,n) for t,n,_ in b])
        self.assertEqual({y[2]-x[2] for x,y in zip(a,b)}, {8})
        self.assertEqual(second["recurrence"]["partIds"], ["lead"])

    def test_clock_matches_pinned_main_entry_timing_receipt(self):
        manifest = producer.PinnedSource(ROOT).json("samples/rambo-loader/main-manifest.json")
        timing = self.package["timing"]
        period = manifest["sourceStartSeconds"] / manifest["sourceStartCall"]
        self.assertAlmostEqual(timing["callCycles"] / timing["clockHz"], period, places=14)

    def test_zero_based_source_call_maps_without_a_one_frame_shift(self):
        manifest = producer.PinnedSource(ROOT).json("samples/rambo-loader/main-manifest.json")
        period = manifest["sourceStartSeconds"] / manifest["sourceStartCall"]
        for passage in self.package["passages"]:
            for event in passage["events"]:
                for call_key, seconds_key in (("sourceCall", "startSeconds"), ("endSourceCall", "endSeconds")):
                    self.assertAlmostEqual(event[seconds_key], (event[call_key] - 1586) * period, places=12)
        self.assertEqual(producer.seconds(1586), 0)
        self.assertAlmostEqual(producer.seconds(1587), period, places=14)

    def test_lfs_materialization_requires_exact_pinned_identity(self):
        payload = b"retained source evidence"
        pointer = ("version https://git-lfs.github.com/spec/v1\noid sha256:" + hashlib.sha256(payload).hexdigest() + "\nsize " + str(len(payload)) + "\n").encode()
        self.assertEqual(producer.materialize(pointer, payload, "source"), payload)
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            producer.materialize(pointer, payload + b"!", "source")
        with self.assertRaisesRegex(ValueError, "pointer"):
            producer.materialize(b"version broken", payload, "source")


if __name__ == "__main__":
    unittest.main()
