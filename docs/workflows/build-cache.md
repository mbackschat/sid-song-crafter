# Retain build evidence without keeping bulky intermediates

`build/` is ignored by Git. Keep accepted listening files and working output there. Preserve canonical verification receipts and complete analysis records in [evidence](../../evidence/README.md), with compressed records in Git LFS and readable manifests in ordinary Git. Remove superseded scratch runs only after identifying their retained replacement. Original reference SIDs and reference WAVs stay out of Git and LFS; [the asset registry](../../config/local-assets.json), [download workflow](../setup/local-setup.md), [audio workflow](audio-workflow.md) and study-specific recipes retain their source URLs, fingerprints and exact reproduction settings.

## Persistent evidence

Install [Git LFS](https://git-lfs.com/) (`brew install git-lfs` on macOS), then initialize it for this checkout and fetch the retained objects from its configured remote:

```sh
git lfs install --local
git lfs pull
python3 scripts/evidence.py verify
python3 scripts/evidence.py restore evidence/shades-form-intake/rows.json.gz
```

Verification checks the compressed and uncompressed hashes and sizes recorded in [the manifest](../../evidence/manifest.json). Restoration writes exact original bytes to their historical `build/` paths without removing the archive. Matching existing files are accepted; different files are preserved and reported as conflicts. Select particular archive paths after `restore` to avoid expanding the complete collection; omitting paths restores everything. Small receipts can be restored too, so their historical relative paths remain meaningful. Missing LFS objects require `git lfs pull` before verification or restoration can succeed.

Select one or more indexed groups with `--group NAME` on `verify` or `restore`. Group selection and explicit archive paths are mutually exclusive; an unknown group fails before verification or restoration starts.

```sh
python3 scripts/evidence.py verify --group rambo-verification-workflow
python3 scripts/evidence.py restore --group rambo-verification-workflow
```

Frozen research checkers can deliberately reject newer tool hashes even when default behavior remains compatible. Reproduce them with their pinned implementation, rather than deleting the guards or rewriting historical receipts. Commit `8e45dbc` retains the CPU/profile tool versions used by the Airwolf form and Monty/Rambo/Deflektor component checkpoints; the later explicit-model option changes those files. Their source snapshots and receipts remain valid evidence of the original runs. Run historical code in an isolated ordinary directory with the same private assets and restored evidence; do not switch the active checkout or create a worktree for this.

Git LFS keeps pointers in ordinary Git and file contents in its object store. A Git-only backup or bundle does not preserve those contents. Keep an off-machine backup of the LFS objects as well, or upload them to an LFS-capable remote and verify a fresh checkout. Remote upload is separate from local retention; an unpushed local LFS archive is still only a local copy. [Git LFS documentation](https://git-lfs.com/)

## Promote reviewed working evidence

Use [the evidence tool](../../scripts/evidence.py) to retain an explicit reviewed selection of uncompressed working files. Save a version 1 selection JSON under `build/`; each entry names one source, a fresh archive path, its study group and the reason to retain it. For example, `build/evidence-promotion/selection.json` can contain:

```json
{
  "version": 1,
  "files": [
    {
      "source": "build/accepted-study/verification.json",
      "path": "evidence/accepted-study/verification.json",
      "group": "accepted-study",
      "reason": "Retain the complete numeric verification and source fingerprints."
    },
    {
      "source": "build/accepted-study/guards.log",
      "path": "evidence/accepted-study/guards.log.gz",
      "group": "accepted-study",
      "reason": "Retain the guard results supporting the verified contract."
    }
  ]
}
```

```sh
python3 scripts/evidence.py promote build/evidence-promotion/selection.json
python3 scripts/evidence.py verify --group accepted-study
```

Promotion validates the complete selection and existing manifest before staging output. Sources must be regular files under `build/`, and destinations must be fresh paths under `evidence/`. Duplicate source/archive paths, already indexed restore destinations, existing destinations, path traversal, symlinks and the manifest as an archive target are rejected. Every entry requires nonempty group and reason text. Original reference SID/WAV files are excluded by suffix and obvious PSID/RSID or RIFF/WAVE headers even when renamed. Already compressed sources are rejected by common suffixes and signatures; supply the uncompressed original so `originalPath` retains exact restoration semantics.

A destination ending in `.gz` receives deterministic gzip with timestamp zero and no stored filename; other destinations receive an exact byte copy. The tool checks stored and original SHA-256 fingerprints and byte sizes before publishing, checks the resulting archives again, and appends their records to [the manifest](../../evidence/manifest.json). Existing manifest fields and file records are preserved. Source bytes remain in place. Promotion never overwrites an archive, including one whose contents already match.

Stop independent source and manifest writers before promotion. A persistent ignored `build/.evidence-promotion-*.lock` serializes cooperating promotions for the same manifest; its operating-system lock is released when the process exits, so the lock file itself is not a stale-lock error. Sources are checked during copying and again before commitment. The manifest must still match its original bytes and file identity before atomic replacement; this check is optimistic and does not provide a filesystem compare-and-swap against independent editors.

An ordinary failure before manifest replacement rolls back unchanged archive files created by that invocation. Concurrent replacements or edits detected by the ownership/content checks are preserved, and empty created directories remain. Interruptions preserve published archives, including an interruption immediately after a successful manifest replacement. An interruption or process/power loss may leave unindexed archives; a hard exit may also leave staging files. Verify the manifest and inspect such files against the reviewed selection before retrying or removing them. The tool does not automatically delete uncertain files or working sources.

## Local cache compression

The [listening-package runner](listening-package.md) separately caches successful computations. Its active stage outputs are hash-verified on reuse: compressing or removing them invalidates that stage and triggers regeneration. Keep accepted standalone audio and historical evidence archives separate from that working computation cache.

Use [the cache tool](../../scripts/build-cache.py) to compress large generated text evidence losslessly. It considers `.json`, `.jsonl`, `.log` and `.txt` files of at least 1 MiB; it leaves WAVs, SID/PRG exports, source files and small receipts untouched. Stop writers before compacting their output directories.

```sh
python3 scripts/build-cache.py compact build/shades-intake
python3 scripts/build-cache.py restore build/shades-intake/vice-cia-corrected-full-final/trace.json.gz
```

Compression verifies the decompressed bytes against the original before removing the uncompressed file. Existing targets are never overwritten, symlinks are skipped, and operations are confined to `build/`. The JSON receipt records paths, sizes and both hashes. Retain that receipt with the cleanup evidence. Restoration recreates the original path and exact bytes so existing analysis tools and historical receipts remain usable.

Markdown links may point directly to the retained `.gz` file. To inspect without restoring a large file, use Python's `gzip.open(path, 'rt')`; for JSON, pass that stream to `json.load`. Restore a file before using a tool that expects an ordinary uncompressed path. Hashes in historical verification receipts describe the original bytes, not the compressed container.

For the current cache inventory and removed/compressed-file receipts, see the ignored `build/cleanup-2026-10-13/` directory. Canonical study documents own the meaning of the evidence; a cache inventory is storage bookkeeping, not a replacement for those findings.
