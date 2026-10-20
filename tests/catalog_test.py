import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("catalog", ROOT / "scripts/catalog.py")
catalog = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(catalog)


class CatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.curator = catalog.read_json(ROOT / "samples/catalog/curator.json")
        cls.index = catalog.generate(cls.curator, ROOT)

    def rejects(self, mutate, message):
        value = copy.deepcopy(self.index)
        mutate(value)
        with self.assertRaisesRegex(ValueError, message):
            catalog.validate_index(value)

    def test_generated_index_is_reproducible_and_committed(self):
        expected = (ROOT / "samples/catalog/index.json").read_bytes()
        self.assertEqual(catalog.encode(self.index), expected)
        self.assertEqual(catalog.encode(catalog.generate(self.curator, ROOT)), expected)

    def test_migrated_catalog_retains_order_scope_and_asset_identities(self):
        self.assertEqual([entry["id"] for entry in self.index["entries"]], [
            "rambo-loader-main", "bach-toccata", "mozart-minuet", "instrument-mix",
            "rambo-stereo-main", "bach-toccata-stereo"])
        self.assertEqual([item["id"] for item in self.index["materials"]], [
            "moon-river", "pink-panther", "axel-f", "ghostbusters"])
        self.assertEqual(sum(len(entry["files"]) for entry in self.index["entries"]), 21)
        self.assertEqual(sum(len(entry["analysis"]["annotations"]) for entry in self.index["entries"]), 3)
        self.assertEqual(self.index["source"]["revision"], "3db086b6963676ef75f34d7f77c3b67232a777fb")
        self.assertEqual(self.index["entries"][0]["files"]["sid"]["sha256"], "99c61d30de4a27e800d185709192de0af92e6d1f2b2350ff8b80f47d8dc4a8cc")
        self.assertGreater(self.index["entries"][4]["externalReference"]["bytes"], catalog.MAX_PREPARED_BYTES)

    def test_asset_fingerprints_match_independent_pinned_git_reads(self):
        for entry in self.index["entries"]:
            for asset in catalog.assets(entry):
                with self.subTest(path=asset["path"]):
                    data = subprocess.run(["git", "show", f"{self.index['source']['revision']}:{asset['path']}"],
                                          cwd=ROOT, capture_output=True, check=True, timeout=10).stdout
                    self.assertEqual(asset["sha256"], hashlib.sha256(data).hexdigest())
                    self.assertEqual(asset["bytes"], len(data))

    def test_unknown_fields_and_versions_fail_closed(self):
        cases = [
            (lambda v: v.update(extra=True), "unknown"),
            (lambda v: v.update(schemaVersion=2), "schemaVersion"),
            (lambda v: v["entries"][0]["files"]["sid"].update(url="https://example.com"), "unknown"),
            (lambda v: v["entries"][0]["rights"].update(correspondingSourceUrl="https://example.com"), "unknown"),
            (lambda v: v["materials"][0].update(files={}), "unknown"),
            (lambda v: v["entries"][0]["analysis"]["annotations"][0].update(extra=1), "unknown"),
        ]
        for mutate, message in cases:
            with self.subTest(message=message):
                self.rejects(mutate, message)

    def test_publication_and_reference_delivery_are_explicit(self):
        self.rejects(lambda v: v["entries"][0].update(publication="materials-only"), "publication")
        self.rejects(lambda v: v["materials"][0].update(publication="cleared"), "publication")
        self.rejects(lambda v: v["entries"][0]["files"]["sid"].update(delivery="link-only"), "delivery")
        self.rejects(lambda v: v["entries"][0]["stereo"]["sid"].update(delivery="prepared"), "delivery")
        self.rejects(lambda v: v["entries"][0].update(externalReference=v["entries"][4]["externalReference"]), "exactly one")
        self.rejects(lambda v: v["entries"][4].pop("externalReference"), "exactly one")

    def test_unsafe_paths_filenames_and_source_identity_fail(self):
        for path in ["../LICENSE", "/LICENSE", "samples/../LICENSE", "LICENSE#x", "LICENSE?raw=1", "samples//x", "https://example.com/file", "samples/%2e%2e/x", "samples/\\x"]:
            with self.subTest(path=path):
                self.rejects(lambda v: v["entries"][0]["files"]["sid"].update(path=path), "path")
        for filename in ["../a.sid", "/a.sid", "a#b.sid", "a?b.sid", "_foo.sid", ".foo.sid"]:
            self.rejects(lambda v: v["entries"][0]["files"]["sid"].update(filename=filename), "filename")
        self.rejects(lambda v: v["source"].update(revision="main"), "revision")
        self.rejects(lambda v: v["source"].update(repository="https://example.com/repo"), "repository")

    def test_prepared_names_are_unique_and_alias_fingerprints_consistent(self):
        self.rejects(lambda v: v["entries"][1]["files"]["sid"].update(filename=v["entries"][0]["files"]["sid"]["filename"]), "filename")
        self.rejects(lambda v: v["entries"][1]["stereo"]["sid"].update(sha256="0" * 64), "alias")
        self.rejects(lambda v: v["entries"][0]["files"]["sid"].update(bytes=catalog.MAX_PREPARED_BYTES + 1), "size")
        catalog.validate_index(self.index)

    def test_target_analysis_annotation_and_numeric_invariants(self):
        cases = [
            (lambda v: v["entries"][0]["target"].update(routing="sid-a-left-sid-b-right"), "routing"),
            (lambda v: v["entries"][4]["target"].pop("secondSidAddress"), "secondSidAddress"),
            (lambda v: v["entries"][0]["analysis"].update(sidSha256="0" * 64), "identity"),
            (lambda v: v["entries"][0]["analysis"].update(subtune=2), "identity"),
            (lambda v: v["entries"][0]["analysis"]["annotations"][0].update(endSeconds=1000), "span"),
            (lambda v: v["entries"][0]["analysis"]["annotations"][0].update(voices=[1, 1]), "voices"),
            (lambda v: v["entries"][0]["analysis"]["annotations"][0].update(voices=[4]), "voices"),
            (lambda v: v["entries"][0]["analysis"]["annotations"][1].update(id="restored-main-entry"), "duplicate"),
            (lambda v: v["entries"][0].update(durationSeconds=float("nan")), "durationSeconds"),
            (lambda v: v["entries"][0]["files"]["sid"].update(bytes=True), "bytes"),
        ]
        for mutate, message in cases:
            with self.subTest(message=message):
                self.rejects(mutate, message)

    def test_generation_rejects_unknown_curator_fields_and_missing_owner_fragment(self):
        value = copy.deepcopy(self.curator)
        value["entries"][0]["files"]["sid"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "unknown"):
            catalog.generate(value, ROOT)
        value = copy.deepcopy(self.curator)
        value["entries"][0]["rights"]["sourcePath"] += "#missing-catalog-heading"
        with self.assertRaisesRegex(ValueError, "fragment"):
            catalog.generate(value, ROOT)

    def test_lfs_pointers_and_symlinks_are_rejected(self):
        store = catalog.GitSource(ROOT, self.index["source"]["revision"])
        with patch.object(store, "_git", return_value=b"120000 blob deadbeef\tLICENSE\n"):
            with self.assertRaisesRegex(ValueError, "regular"):
                store.blob("LICENSE")
        with patch.object(store, "_git", side_effect=[b"100644 blob " + b"a" * 40 + b" 43\tLICENSE\n", b"version https://git-lfs.github.com/spec/v1\n"]):
            with self.assertRaisesRegex(ValueError, "LFS"):
                store.blob("LICENSE")

    def test_git_calls_are_bounded_and_do_not_use_a_shell(self):
        with patch.object(catalog.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"data", b"")) as run:
            self.assertEqual(catalog.GitSource(ROOT, "a" * 40)._git("show", "a"), b"data")
        self.assertEqual(run.call_args.kwargs["timeout"], 10)
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_generation_checks_declared_target_against_psid_header(self):
        value = copy.deepcopy(self.curator)
        value["entries"][0]["target"]["model"] = "MOS8580"
        with self.assertRaisesRegex(ValueError, "SID target"):
            catalog.generate(value, ROOT)

    def test_check_rejects_stale_output_without_rewriting_it(self):
        work = ROOT / "build/catalog"
        work.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as temporary:
            output = Path(temporary) / "index.json"
            stale = copy.deepcopy(self.index)
            stale["entries"][0]["title"] += " stale"
            original = catalog.encode(stale)
            output.write_bytes(original)
            result = subprocess.run([sys.executable, str(ROOT / "scripts/catalog.py"), "check", "--output", str(output)],
                                    cwd=ROOT, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertIn(b"generated index differs", result.stderr)
            self.assertEqual(output.read_bytes(), original)

    def test_manifest_fingerprints_and_non_commit_revisions_fail(self):
        with self.assertRaisesRegex(ValueError, "manifest fingerprint"):
            catalog.verify_manifest({"files": [{"filename": "a.sid", "sha256": "0" * 64, "bytes": 4}]},
                                    "samples/a", {"samples/a/a.sid": {"sha256": "1" * 64, "bytes": 4}})
        with patch.object(catalog.GitSource, "_git", return_value=b"tree\n"):
            with self.assertRaisesRegex(ValueError, "Git commit"):
                catalog.generate(self.curator, ROOT)

    def test_nonfinite_json_numbers_are_rejected(self):
        for value in ["NaN", "Infinity", "-Infinity"]:
            with self.assertRaisesRegex(ValueError, "invalid JSON number"):
                catalog.decode(value)

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            catalog.decode('{"schemaVersion": 1, "schemaVersion": 2}')


if __name__ == "__main__":
    unittest.main()
