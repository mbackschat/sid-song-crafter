import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import listening_publish


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ListeningPublishTest(unittest.TestCase):
    def setUp(self):
        self.fresh_fixture()

    def fresh_fixture(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.package = self.root / "build/package"
        self.attempt = self.package / "cache/audio/key/attempt-fixture"
        self.attempt.mkdir(parents=True)
        self.sources = {}
        artifacts = []
        for label, filename, data in (("opening", "opening.wav", b"RIFF opening audio"),
                ("fullReference", "reference.wav", b"RIFF reference audio"),
                ("fullCandidate", "candidate.wav", b"RIFF candidate audio"),
                ("proof", "proof.json", b"{}")):
            source = self.attempt / filename
            source.write_bytes(data)
            self.sources[label] = source
            artifacts.append(dict(stageId="audio", path=str(source), relativePath=filename,
                type="file", sha256=sha(source)))
        self.run = dict(schemaVersion=1, status="completed", startedAt="2026-10-13T00:00:00Z",
            finishedAt="2026-10-13T00:00:01Z", artifacts=artifacts,
            stages=[dict(id="audio", status="completed", returnCode=0,
                attemptDirectory=str(self.attempt), artifacts=artifacts.copy())],
            deliverables={label: str(source) for label, source in self.sources.items()})
        self.run_path = self.package / "run.json"
        self.selection_path = self.root / "selection.json"
        self.selection = {"opening": "opening-ab.wav", "fullReference": "reference.wav"}
        self.output = self.root / "build/audition"
        self.write_inputs()

    def write_inputs(self):
        self.run_path.write_text(json.dumps(self.run))
        self.selection_path.write_text(json.dumps(self.selection))

    def publish(self, **kwargs):
        return listening_publish.publish_listening(kwargs.get("run", self.run_path),
            kwargs.get("selection", self.selection_path), kwargs.get("output", self.output), root=self.root)

    def assert_unpublished(self):
        self.assertFalse(self.output.exists())
        self.assertFalse(any(path.name.startswith(".audition-") for path in self.output.parent.iterdir()))

    def test_selected_copies_are_independent_and_record_pinned_source_provenance(self):
        before = {label: source.read_bytes() for label, source in self.sources.items()}
        run_bytes = self.run_path.read_bytes()
        selection_bytes = self.selection_path.read_bytes()
        result = self.publish()
        self.assertEqual({p.name for p in self.output.iterdir()}, {"opening-ab.wav", "reference.wav", "sources.json"})
        manifest = json.loads((self.output / "sources.json").read_text())
        self.assertEqual(result, manifest)
        self.assertEqual(manifest["run"], dict(path=str(self.run_path), sha256=sha(self.run_path), bytes=len(run_bytes)))
        self.assertEqual(manifest["selection"]["sha256"], sha(self.selection_path))
        for record in manifest["files"]:
            target = self.output / record["filename"]
            source = self.sources[record["label"]]
            self.assertEqual(target.read_bytes(), before[record["label"]])
            self.assertEqual(record["sha256"], sha(target))
            self.assertEqual(record["sourcePath"], str(source))
            self.assertEqual(record["bytes"], target.stat().st_size)
            self.assertNotEqual(target.stat().st_ino, source.stat().st_ino)
        self.assertEqual({label: source.read_bytes() for label, source in self.sources.items()}, before)
        self.assertEqual(self.run_path.read_bytes(), run_bytes)
        self.assertEqual(self.selection_path.read_bytes(), selection_bytes)

    def test_failed_running_and_inconsistent_completed_runs_are_rejected(self):
        for status, stage_status, finished in (("failed", "completed", True),
                ("running", "completed", True), ("completed", "failed", True),
                ("completed", "running", True), ("completed", "completed", False)):
            with self.subTest(status=status, stage=stage_status, finished=finished):
                self.run["status"] = status
                self.run["stages"][0]["status"] = stage_status
                if finished:
                    self.run["finishedAt"] = "2026-10-13T00:00:01Z"
                else:
                    self.run.pop("finishedAt", None)
                self.write_inputs()
                with self.assertRaises(listening_publish.PublishError):
                    self.publish()
                self.assert_unpublished()

    def test_reused_successful_stage_is_admitted(self):
        self.run["stages"][0]["status"] = "reused"
        self.run["stages"][0].pop("returnCode")
        self.write_inputs()
        self.assertEqual(len(self.publish()["files"]), 2)

    def test_unknown_empty_and_duplicate_label_selections_are_rejected(self):
        for selection in ({"missing": "missing.wav"}, {}, []):
            with self.subTest(selection=selection):
                self.selection = selection
                self.write_inputs()
                with self.assertRaises(listening_publish.PublishError):
                    self.publish()
                self.assert_unpublished()
        self.selection_path.write_text('{"opening":"one.wav","opening":"two.wav"}')
        with self.assertRaisesRegex(listening_publish.PublishError, "(?i)duplicate"):
            self.publish()
        self.assert_unpublished()

    def test_filename_traversal_subdirectories_non_wavs_and_collisions_are_rejected(self):
        for name in ("../clip.wav", "/clip.wav", "sub/clip.wav", "sub\\clip.wav", ".wav", " clip.wav", "proof.json", "clip\n.wav"):
            with self.subTest(name=name):
                self.selection = {"opening": name}
                self.write_inputs()
                with self.assertRaises(listening_publish.PublishError):
                    self.publish()
                self.assert_unpublished()
        for first, second in (("same.wav", "same.wav"), ("Clip.wav", "clip.WAV"), ("é.wav", "e\u0301.wav")):
            with self.subTest(first=first, second=second):
                self.selection = {"opening": first, "fullReference": second}
                self.write_inputs()
                with self.assertRaisesRegex(listening_publish.PublishError, "collid"):
                    self.publish()
                self.assert_unpublished()

    def test_existing_output_outside_build_and_output_traversal_are_rejected(self):
        for output in (self.root / "elsewhere", self.root / "build/package/../escaped"):
            with self.subTest(output=output):
                with self.assertRaises(listening_publish.PublishError):
                    self.publish(output=output)
                self.assertFalse(output.exists())
        self.output.mkdir()
        sentinel = self.output / "keep.txt"
        sentinel.write_text("keep")
        with self.assertRaisesRegex(listening_publish.PublishError, "fresh"):
            self.publish()
        self.assertEqual(sentinel.read_text(), "keep")

    def test_publication_inside_live_attempt_cache_is_rejected(self):
        output = self.attempt / "audition"
        with self.assertRaisesRegex(listening_publish.PublishError, "cache"):
            self.publish(output=output)
        self.assertFalse(output.exists())

    def test_bad_hash_unknown_stage_and_ambiguous_artifact_are_rejected(self):
        for defect in ("hash", "stage", "duplicate", "stage-artifact"):
            with self.subTest(defect=defect):
                self.fresh_fixture()
                record = self.run["artifacts"][0]
                if defect == "hash":
                    record["sha256"] = "0" * 64
                elif defect == "stage":
                    record["stageId"] = "unknown"
                elif defect == "duplicate":
                    self.run["artifacts"].append(dict(record))
                else:
                    self.run["stages"][0]["artifacts"] = []
                self.write_inputs()
                with self.assertRaises(listening_publish.PublishError):
                    self.publish()
                self.assert_unpublished()

    def test_non_audio_and_directory_artifacts_are_rejected(self):
        self.selection = {"proof": "proof.wav"}
        self.write_inputs()
        with self.assertRaisesRegex(listening_publish.PublishError, "WAV"):
            self.publish()
        self.selection = {"opening": "opening.wav"}
        self.run["artifacts"][0]["type"] = "directory"
        self.write_inputs()
        with self.assertRaises(listening_publish.PublishError):
            self.publish()
        self.assert_unpublished()

    def test_symlink_sources_inputs_and_output_parents_are_rejected(self):
        source = self.sources["opening"]
        real = source.with_name("real.wav")
        source.rename(real)
        source.symlink_to(real)
        with self.assertRaisesRegex(listening_publish.PublishError, "(?i)symlink"):
            self.publish()
        source.unlink()
        real.rename(source)
        for original in (self.run_path, self.selection_path):
            link = original.with_name("link-" + original.name)
            link.symlink_to(original)
            with self.assertRaisesRegex(listening_publish.PublishError, "(?i)symlink"):
                self.publish(**{"run" if original == self.run_path else "selection": link})
            link.unlink()
        link = self.root / "build/link"
        link.symlink_to(self.package, target_is_directory=True)
        with self.assertRaisesRegex(listening_publish.PublishError, "(?i)symlink"):
            self.publish(output=link / "audition")
        self.assert_unpublished()

    def test_source_or_run_changes_during_copy_abort_without_partial_publication(self):
        copy = shutil.copyfile
        for changed in ("source", "run", "selection"):
            with self.subTest(changed=changed):
                self.fresh_fixture()

                def mutate(source, target):
                    result = copy(source, target)
                    if changed == "source":
                        Path(source).write_bytes(b"changed source")
                    elif changed == "run":
                        self.run_path.write_text(self.run_path.read_text() + " ")
                    else:
                        self.selection_path.write_text(self.selection_path.read_text() + " ")
                    return result

                with patch.object(listening_publish.shutil, "copyfile", side_effect=mutate):
                    with self.assertRaisesRegex(listening_publish.PublishError, "changed"):
                        self.publish()
                self.assert_unpublished()

    def test_copy_failure_cleans_staging_and_preserves_existing_sources(self):
        before = {label: source.read_bytes() for label, source in self.sources.items()}
        with patch.object(listening_publish.shutil, "copyfile", side_effect=OSError("copy failed")):
            with self.assertRaisesRegex(listening_publish.PublishError, "copy failed"):
                self.publish()
        self.assert_unpublished()
        self.assertEqual({label: source.read_bytes() for label, source in self.sources.items()}, before)

    def test_earlier_copy_corruption_before_publication_is_rejected(self):
        copy = shutil.copyfile

        def corrupt_earlier(source, target):
            result = copy(source, target)
            if Path(target).name == "reference.wav":
                (Path(target).parent / "opening-ab.wav").write_bytes(b"changed copied audio")
            return result

        with patch.object(listening_publish.shutil, "copyfile", side_effect=corrupt_earlier):
            with self.assertRaisesRegex(listening_publish.PublishError, "changed"):
                self.publish()
        self.assert_unpublished()

    def test_destination_created_during_copy_is_preserved(self):
        copy = shutil.copyfile

        def create_destination(source, target):
            result = copy(source, target)
            self.output.mkdir(exist_ok=True)
            (self.output / "keep.txt").write_text("another publication")
            return result

        with patch.object(listening_publish.shutil, "copyfile", side_effect=create_destination):
            with self.assertRaises(listening_publish.PublishError):
                self.publish()
        self.assertEqual({p.name for p in self.output.iterdir()}, {"keep.txt"})
        self.assertEqual((self.output / "keep.txt").read_text(), "another publication")
        self.assertFalse(any(p.name.startswith(".audition-") for p in self.output.parent.iterdir()))

    def test_cli_prints_friendly_paths_and_rejects_unknown_flags(self):
        command = [sys.executable, str(ROOT / "scripts/publish-listening.py"), str(self.run_path),
            "--selection", str(self.selection_path), "--output", str(self.output)]
        rejected = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("build", rejected.stderr)
        help_result = subprocess.run(command[:2] + ["--help"], capture_output=True, text=True)
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("--selection", help_result.stdout)
        unknown = subprocess.run(command + ["--upload"], capture_output=True, text=True)
        self.assertEqual(unknown.returncode, 2)


if __name__ == "__main__":
    unittest.main()
