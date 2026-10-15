# Retain build evidence without keeping bulky intermediates

`build/` is ignored by Git. Keep accepted listening files and working output there. Preserve canonical verification receipts and complete analysis records in [evidence](../../evidence/README.md), with compressed records in Git LFS and readable manifests in ordinary Git. Remove superseded scratch runs only after identifying their retained replacement. Original reference SIDs and reference WAVs stay out of Git and LFS; [the asset registry](../../config/local-assets.json), [download workflow](../setup/local-setup.md), [audio workflow](audio-workflow.md) and study-specific recipes retain their source URLs, fingerprints and exact reproduction settings.

## Automated cleanup and when to run it

Use the [cleanup script](../../scripts/cleanup-build.py) for repeatable local housekeeping. It previews by default; `--apply` executes a newly checked safe selection and writes a fresh report directory under `build/`.

```sh
python3 scripts/cleanup-build.py
python3 scripts/cleanup-build.py --apply --protect build/my-active-run
```

Replace the protection example with the actual active output paths; repeat `--protect` for multiple files or subtrees. Future output paths are valid protections. `--output build/cleanup-my-run` selects a fresh report directory; the default generates a unique timestamped name. Stop all independent build writers before either preview or apply, including writers to protected paths. Protection prevents cleanup selection but does not exempt those files from the final unchanged-files guard; an active VICE log caused a dry-run rejection on 2026-10-15 despite its protected directory. Identity/hash checks detect changes but do not lock independent producers.

Run cleanup after a substantial completed rendering/evidence batch, at musical-case closure, and before handing off a session that produced substantial build output. First preserve the listening deliverables and promote the evidence that must survive working-cache removal. Defer cleanup while rapid iterations still benefit from the same cached stages, and protect any ongoing/deferred work. Once a pass has reclaimed eligible files, a large remainder is not itself a reason to repeat it: unique audio needs a separate retention decision.

The script removes only cache WAVs whose size and SHA-256 match a retained regular WAV outside cache directories. It rechecks both files immediately before deletion and records the retained path. It delegates lossless compression of generated `.json`, `.jsonl`, `.log` and `.txt` files of at least 1 MiB to the existing [cache tool](../../scripts/build-cache.py); decompressed bytes are verified before the original is removed. Existing gzip destinations are skipped. Published listening directories, previous conventionally named cleanup reports, deferred paths, literal `build/` inputs in checked-in listening recipes and the local-asset registry, and explicit protections are excluded from mutation. It keeps all non-cache and unique WAVs and does not follow symlinks. It does not infer protections hidden in arbitrary scripts; declare those paths explicitly.

Each report retains before/after inventories with hashes, the exact selection and configuration pins, an operation journal written before each mutation, and `summary.json` with logical/allocated sizes and whether unselected files stayed unchanged. File allocation and volume free-space changes are separate observations on filesystems with snapshots or clones. A failure can leave already completed safe operations in place; inspect the journal and use a fresh report directory for a later pass. No original SID or audio is added to Git by cleanup.

Removing or compacting cached artifacts invalidates those stages. Restore a compressed text path with `python3 scripts/build-cache.py restore build/path/file.json.gz`, or regenerate it through the owning recipe. Keep stable listening paths outside the computation cache.

### Verified automated pass, 2026-10-15

The [apply report](../../build/cleanup-20261015-rambo-apply/summary.json) records 89 duplicate cache WAVs removed and 86 text files compressed, reclaiming 1,821,550,716 logical bytes. The inventoried build data decreased from 5,529,447,891 to 3,707,897,175 bytes, excluding the current report directory; all unselected pre-existing files retained their hashes. Retained data included 752 WAV files totaling 2,688,550,488 bytes, plus 410,511,133 bytes of gzip archives. These figures describe that pass, before subsequent generation, not a permanent size bound. The [selection](../../build/cleanup-20261015-rambo-apply/selection.json) and [operation journal](../../build/cleanup-20261015-rambo-apply/operations.jsonl) preserve the exact actions and retained copies.

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

Before committing a promoted group, check that every new manifest archive is actually staged/tracked with `git ls-files`; successful promotion and hash verification do not establish Git inclusion. Global ignore rules also apply inside `evidence/`: the Rambo stereo verification log was initially omitted by a global `*.log` rule, corrected in commit `1237aa9` with a narrow repository exception. Inspect unexpected exclusions with `git check-ignore -v`, preserve the public-file boundary, and never force-add a directory to bypass it.

## Local cache compression

The [listening-package runner](listening-package.md) separately caches successful computations. Its active stage outputs are hash-verified on reuse: compressing or removing them invalidates that stage and triggers regeneration. Keep accepted standalone audio and historical evidence archives separate from that working computation cache.

Use [the cache tool](../../scripts/build-cache.py) to compress large generated text evidence losslessly. It considers `.json`, `.jsonl`, `.log` and `.txt` files of at least 1 MiB; it leaves WAVs, SID/PRG exports, source files and small receipts untouched. Stop writers before compacting their output directories.

```sh
python3 scripts/build-cache.py compact build/shades-intake
python3 scripts/build-cache.py restore build/shades-intake/vice-cia-corrected-full-final/trace.json.gz
```

Compression verifies the decompressed bytes against the original before removing the uncompressed file. Existing targets are never overwritten, symlinks are skipped, and operations are confined to `build/`. The JSON receipt records paths, sizes and both hashes. Retain that receipt with the cleanup evidence. Restoration recreates the original path and exact bytes so existing analysis tools and historical receipts remain usable.

Markdown links may point directly to the retained `.gz` file. To inspect without restoring a large file, use Python's `gzip.open(path, 'rt')`; for JSON, pass that stream to `json.load`. Restore a file before using a tool that expects an ordinary uncompressed path. Hashes in historical verification receipts describe the original bytes, not the compressed container.

The [2026-10-14 cleanup receipt](../../build/cleanup-2026-10-14/summary.json) records a reduction from 2.82 GB to 1.60 GB (decimal logical bytes, before subsequent work): 98 cache WAVs removed only after SHA-256 equality with retained non-cache copies, and 98 large text files losslessly compressed with the existing tool. All published listening files, unique audio, local source references, exports and small receipts remain. The [exact duplicate selection](../../build/cleanup-2026-10-14/deleted-duplicates.json) and [compression receipts](../../build/cleanup-2026-10-14/compression.jsonl) record paths and hashes. The earlier cleanup remains in ignored `build/cleanup-2026-10-13/`. Canonical study documents own the meaning of evidence; these receipts describe storage only.

After cleanup, a recipe may regenerate stages whose cached outputs were removed or compressed. Published auditions remain available independently. Restore compressed text with `scripts/build-cache.py restore` when inspecting an old path directly, or use `scripts/evidence.py restore` for the canonical archive. Do not assume an invalidated cache means missing study evidence.

## 2026-10-15 cleanup

Two verified passes reclaimed 1,598,605,682 bytes: 72 duplicate cache WAVs were removed only after matching retained copies by SHA-256, and 154 generated text files were losslessly compressed. The final inventory was 2,348,049,602 logical bytes before subsequent Night Transit revision outputs. Published listening files, unique audio, source assets, deferred Bach output and all active Night Transit files were retained. `build/` remains ignored; these are local working files, not repository additions.

The [final summary](../../build/cleanup-20261015/final-summary.json), [first-pass receipt](../../build/cleanup-20261015/summary.json), [second-pass receipt](../../build/cleanup-20261015/noncache-summary.json) and [round-trip verification](../../build/cleanup-20261015/noncache-restoration-verification.json) retain exact selections and hashes. The retained Ghostbusters model responses still pass their two controls without new API calls. Most remaining bulk is useful audio; further deletion would require selecting auditions to retire, rather than removing duplicate intermediates.
