# Retain build evidence without keeping bulky intermediates

`build/` is ignored working output, not permanent storage for accepted material. Keep current listening files in place until a verified retention/restoration route is established and their links are preserved or explicitly updated. Preserve canonical verification receipts and complete analysis records in [evidence](../../evidence/README.md), with compressed records in Git LFS and readable manifests in ordinary Git. Remove superseded scratch runs only after identifying their retained replacement. Original reference SIDs and reference WAVs stay out of Git and LFS; [the asset registry](../../config/local-assets.json), [download workflow](../setup/local-setup.md), [audio workflow](audio-workflow.md) and study-specific recipes retain their source URLs, fingerprints and exact reproduction settings.

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

At the Axel F session close, the [cleanup summary](../../build/cleanup-session-close-axel/summary.json) records 29 duplicate cache WAVs removed and 51 generated text files compressed, reclaiming 333,207,297 logical bytes. The remaining inventory is 5,860,084,417 bytes, excluding the current cleanup report. All listening files, unique audio, native exports and deferred work remain; the selected full tonal palette and its selected-roles baseline are explicitly protected. The maracas trial is parked after feedback, so its large text evidence can now require lossless restoration and its duplicate cache WAVs can require regeneration; published audition WAVs remain at their original paths. Use the restoration command above when a historical receipt names a compacted file. All unselected pre-existing files passed unchanged-hash verification.

The [apply report](../../build/cleanup-20261015-rambo-apply/summary.json) records 89 duplicate cache WAVs removed and 86 text files compressed, reclaiming 1,821,550,716 logical bytes. The inventoried build data decreased from 5,529,447,891 to 3,707,897,175 bytes, excluding the current report directory; all unselected pre-existing files retained their hashes. Retained data included 752 WAV files totaling 2,688,550,488 bytes, plus 410,511,133 bytes of gzip archives. These figures describe that pass, before subsequent generation, not a permanent size bound. The [selection](../../build/cleanup-20261015-rambo-apply/selection.json) and [operation journal](../../build/cleanup-20261015-rambo-apply/operations.jsonl) preserve the exact actions and retained copies.

## Persistent evidence

Compressed research evidence is optional for the normal demo and own-score workflow. The [README clone command](../../README.md#requirements-and-setup) skips LFS payloads; ordinary Git receipts, manifests and included samples are still checked out. Install [Git LFS](https://git-lfs.com/) (`brew install git-lfs` on macOS) when a study needs its compressed evidence, then fetch its indexed directory explicitly:

```sh
git lfs install --local
git lfs pull --include="evidence/shades-form-intake/**" --exclude=""
python3 scripts/evidence.py verify --group shades-form-intake
```

Use the group and directory recorded in [the evidence index](../../evidence/README.md); group IDs need not equal directory names. Omit filtering only when intentionally acquiring the complete optional collection:

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

## External local build archives

Use [archive-build.py](../../scripts/archive-build.py) to retain an explicitly reviewed selection outside the checkout and, optionally, remove its working copies or retain WAV playback links. This is local retention, separate from public evidence promotion and Git/LFS distribution. The tool does not decide what is expendable or infer protected musical cases. Select only classified files whose retention/reproduction route is settled; preserve active/deferred work and current listening paths. Stop independent source, archive and restoration-destination writers before running it.

Supply a JSON object with `version: 1` and a nonempty `files` array. Each file entry has this contract:

| Field | Required value |
| --- | --- |
| `path` | Canonical relative path below `build/`, identifying one regular file; no traversal or symlink components |
| `bytes` | Measured nonnegative integer byte count |
| `sha256` | Measured SHA-256 of the original bytes, as 64 lowercase hexadecimal characters |
| `reason` | Nonempty explanation of why the file is retained and its working copy may be retired |

Duplicate source paths reject. Different paths with identical bytes share one content-addressed object within that archive. Select actual inventory paths and fingerprints rather than copying examples with invented hashes. The external archive directory must be fresh and outside the checkout, with an existing parent and no symlink components. These commands illustrate a reviewed selection and a separately chosen local archive location:

```sh
python3 scripts/archive-build.py archive build/reviewed-selection.json --archive /absolute/archive-parent/case-name
python3 scripts/archive-build.py archive build/another-reviewed-selection.json --archive /absolute/archive-parent/another-case --remove
python3 scripts/archive-build.py archive build/reviewed-wavs.json --archive /absolute/archive-parent/listening-history --link
python3 scripts/archive-build.py restore /absolute/archive-parent/another-case/manifest.json --path build/my-run/cache/preview.wav
python3 scripts/archive-build.py restore /absolute/archive-parent/listening-history/manifest.json --path build/my-run/accepted.wav
```

Archive without `--remove` or `--link` copies and verifies; it leaves every source in place. With `--remove`, it performs the same complete validation and only then evicts the selected source paths. With `--link`, it instead retains raw read-only objects (`objects/<sha256>.raw`, mode `0444`) and atomically replaces each selected source with an absolute playback symlink after verification. `--link` and `--remove` are mutually exclusive. Every invocation needs a fresh archive directory; it does not add entries to an existing archive or turn an earlier copy-only run into a removal run. Restore accepts repeated `--path` arguments for exact indexed file paths; omitting them restores all entries beneath the current checkout's `build/` at their recorded relative paths.

Before writing any archive data, the tool validates the complete selection against regular source files, their byte counts and hashes. It retains each source's file identity, stores deterministic gzip objects under `objects/<original-sha256>.gz`, flushes objects and directories, and writes a durable `manifest.json`. The manifest records every original path, byte count, SHA-256, reason and object path, plus the original checkout location for context. All stored objects are decoded and checked before any source deletion or link replacement. Each source's identity and hash are rechecked immediately before its removal. Shared build-path/identity/hash checks come from [cleanup-build.py](../../scripts/cleanup-build.py), which also loads [build-cache.py](../../scripts/build-cache.py); retain these tool dependencies together.

Restore validates the manifest, selected objects and existing-file conflicts before publishing any file. It verifies decoded bytes again into a temporary file beside the destination and publishes without overwriting. An identical existing file remains untouched; a changed existing file rejects. For raw archives, an exact owned playback link is verified and atomically materialized into an independent regular file. Unrelated links, changed links and symlinked parent directories reject; restoring never modifies the archive object. Corrupt/truncated gzip objects and valid gzip with the wrong original hash both fail. This preserves file bytes, not original timestamps, permissions or WAV-container reinterpretations.

The final `operation.json` records success/failure, whether the manifest and object verification completed, completed source removals/link replacements and logical byte totals. A partial failure preserves completed operations and all archive recovery material; it does not roll back deletions. If interrupted after removal begins, the already durable manifest still indexes every original, even when the final operation receipt is absent. Restore skips identical files, so retry after inspecting the failure and resolving conflicts. A failure before manifest publication removes no sources and can leave incomplete archive objects; inspect them before choosing a new destination. No uncertain output is automatically deleted or overwritten.

These are optimistic identity/content guards, not locks or an atomic filesystem compare-and-unlink/replace; stop writers rather than relying on the small interval between final checks and mutation. The tool requires local filesystem support for no-follow opens, directory fsync and non-overwriting hardlink publication. A filesystem operation failure is reported with the retained archive location. Keep an additional backup for irreplaceable local retention: an external directory on the same machine is not an off-machine backup. Copying increases total retained storage; evicting originals relocates bytes and is not equivalent to deleting them. Report source removal, compressed archive size and actual free-space changes separately.

### Choosing playback links safely

Use playback links only for inactive WAV history. Keep native recipe JSON and its companion scores regular: tools that resolve a recipe path locate relative inputs beside it. Keep package-root `run.json` and `listening.md` regular for atomic index updates. A recipe that fingerprints a directory requires every descendant to remain regular, including WAVs; preserve literal file/directory inputs, active work and deferred experiments as regular working copies with a verified external snapshot. Keep document-linked non-WAV evidence regular to preserve readers that resolve sidecars relative to the file.

Ordinary WAV readers follow the archived link, retaining old listening URLs without keeping another audio copy in the checkout. Before rerendering, editing or publishing that path, use `restore --path` to materialize it, or choose a fresh output directory. The renderer rejects symlinked WAV or register-log destinations before opening either output; publication deliberately rejects symlink sources. Do not make archive objects writable to bypass those guards. Read-only mode is an accidental-write guard, not filesystem immutability.

The absolute links depend on the external archive location. Keep its manifest and objects together; when moving to another machine, copy the archive and restore regular files from its new manifest location. Do not delete the archive merely because files still appear under `build/`. An archived historical snapshot makes its recorded bytes recoverable; future generated or edited files require a new retention pass.

### Maintainer archive and current recovery routes

The completed 2026-10-17 migration is recorded in the [workbench assessment](../validation/workbench-assessment.md#storage-outcome-and-recovery). Its local archive is `~/Archives/sid-song-crafter/`; the README there explains recovery and `catalog.json` maps historical paths to their latest manifest and exact fingerprint. Data manifests and compressed inventories/receipts stay outside Git. Use that catalog to choose a manifest and restore only the required paths. Do not restore every manifest indiscriminately: newer snapshots can contain changed package indexes, and different existing bytes correctly fail as conflicts.

The protected snapshot retains regular recipe inputs and deferred work; raw listening objects retain old WAV URLs; compressed history retains other generated/unknown-value material. A final snapshot also preserves recovered metadata and the current own-score indexes. Historical debug binaries `build/render-native-debug` and `build/renderer-dual-rsid/render-sid-before` need `chmod 0755` after byte restoration if execution is required. New builds and edits need fresh retention or verified regeneration routes; the dated snapshot does not cover future work.

### Archived deferred source experiments

On 2026-10-17, the user authorized retiring 12 untracked Flashdance, Monty and Elise experiment files from the working tree. Their 74,082 original bytes are retained in `~/Archives/sid-song-crafter/2026-10-17-deferred-source/`: `sources.tar.gz` (18,998 bytes), `manifest.json` (original paths, sizes, SHA-256 hashes and modes), and a recovery README. Every file was extracted to a fresh temporary directory and matched byte-for-byte before the originals were removed. The archive SHA-256 is `e4e262c637c9c3c14cb695ca3e81e96247482cd93bfe8e14f1aa4e9c5c015288`. This separate source archive is not indexed by the build-only catalog or restored by `archive-build.py`; it remains local and needs a separate backup.

| Retained material | Scope and recovery purpose |
| --- | --- |
| `scripts/analyze-flashdance.py`, `tests/flashdance_analysis_test.py`, `songs/studies/flashdance-reconstruction/README.md` | Exact historical form-analysis tool and supporting material; see the [Flashdance reproduction boundary](../research/composition/flashdance-preparation.md#selected-form-and-ending-contract). The archived README's pending milestones are historical. |
| `scripts/monty_player.py`, `scripts/monty_programs.py`, `tests/monty_player_test.py`, `tests/monty_score_test.py` | Superseded partial implementations. Their imported `monty_score.py` was already absent; supported integration uses tracked `monty_title_*` files. Do not restore these tests into routine discovery without resolving that missing dependency. |
| `songs/studies/elise-bass-multiplex/` containing `README.md`, `provenance.json`, `recipe-a.json`, `recipe-b.json`, `score.json` | Unaccepted experiment, with source recipes and provenance preserved; no new musical work is queued. |

For recovery, verify the archive hash, extract into a fresh empty directory, then verify each extracted file's size and SHA-256 against `manifest.json`. The archive preserves repository-relative paths. Copy only the needed files into the checkout after checking for conflicts; do not overwrite current implementations. For example:

```sh
shasum -a 256 ~/Archives/sid-song-crafter/2026-10-17-deferred-source/sources.tar.gz
recovery_dir=$(mktemp -d /tmp/sid-deferred-recovery.XXXXXX)
tar -xzf ~/Archives/sid-song-crafter/2026-10-17-deferred-source/sources.tar.gz -C "$recovery_dir"
```

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
