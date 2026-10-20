# Run a repeatable listening package

Use [listening-package.py](../../scripts/listening-package.py) to execute a checked-in recipe, retain stage timings and reuse successful stages whose inputs, commands, tools and outputs still match. This handles routine build, verification, rendering and comparison commands; the [listening workflow](audio-comparisons.md) still owns musical judgments. Recipes invoke ordinary project commands, not a universal SID compiler.

## Reproduce the accepted Monty comparison

Prepare the [local tools and assets](../setup/local-setup.md), including the pinned Monty reference, headless VICE and [renderer](audio-workflow.md). Then run:

```sh
python3 scripts/listening-package.py config/listening/monty-reference-continuation.json --output build/monty-listening
```

Run the same command again to reuse verified stages. Open `build/monty-listening/listening.md` for the full reference, full candidate, opening A/B and ending A/B. Each comparison plays the reference first, followed by a half-second gap and ours. The recipe preserves the original restart; capture stops at 355 seconds. That capture boundary is not a composed ending. The [Monty study](../research/composition/monty-preparation.md) owns the accepted musical scope and the separate finite-fade variant.

The command verifies the source SID fingerprint, compiles and audits all 40,000 declared calls, compares the entire ordered store stream against the retained original ledger, checks the restart in headless VICE, renders both versions from initialization, checks WAV format/duration/clipping and prepares the two comparisons. VICE uses the local source checkout's data directory; no GUI application path is required. The example fingerprints the documented Apple Silicon Homebrew `libintl` dependency by its stable `/opt/homebrew/opt/gettext/lib/libintl.8.dylib` path; adapt that declared input when using a different VICE installation. Failed stages stop the package and retain their logs. The command never infers musical acceptance from a successful run.

## Verify a study before compiled playback

Recipes also automate preparation and numeric evidence. For Rambo, use one of these explicitly different modes after installing its pinned local source assets:

```sh
python3 scripts/listening-package.py config/listening/rambo-loader-verification.json --output build/rambo-verification
python3 scripts/listening-package.py config/listening/rambo-loader-retained-verification.json --output build/rambo-retained-verification
```

The [fresh-capture recipe](../../config/listening/rambo-loader-verification.json) checks extraction, runs focused guards, compares the independent numeric loader with the complete canonical store ledger, and executes the original to capture and verify every SOUND invocation. The [retained-evidence recipe](../../config/listening/rambo-loader-retained-verification.json) instead rechecks the archived SOUND capture against the current component; isolated original-routine checks still execute. Its proof records `captureReused: true`. Both modes retain exact inputs, state/completion checks and evidence paths. Neither produces a compiled player or establishes musical acceptance; the [Rambo study](../research/composition/rambo-preparation.md) owns its subsequently completed compiled delivery and listening verdicts.

An unchanged repeated invocation reuses verified stages in either mode. A cache hit for the fresh-capture recipe means reuse of its earlier fresh capture, not a new execution of the original. Read stage reuse in `run.json`; choose a new output directory when a genuinely new capture is required. The numeric check covers all 87,534 ordered stores, the declared 11,000 model calls and 185 quiet confirmation calls, while pinned canonical audit/form records establish the original's 40,000-call coverage.

The [2026-10-13 workflow benchmark](../../evidence/rambo-verification-workflow/timing-summary.json) measured **30.87 seconds** for fresh capture and **0.04 seconds** for unchanged reuse of all stages. Retained SOUND verification took **2.18 seconds** with the other stages reused. The [fresh proof](../../evidence/rambo-verification-workflow/fresh-sound-verification.json) and [retained proof](../../evidence/rambo-verification-workflow/retained-sound-verification.json) preserve their different capture provenance. These compare workflow modes on one host, not original execution speed or total engineering effort.

## Reuse and invalidation

| Change | Required work |
| --- | --- |
| Nothing | Verify input/output fingerprints and reuse successful stages |
| A/B window or gap | Rebuild that comparison from the retained full WAVs |
| Renderer binary or settings | Rerender affected audio, recheck its signal and rebuild comparisons |
| Score, sound program or compiler dependency | Rebuild and audit; downstream stages rerun only when their own declared input content or commands change |
| Missing or changed cached output | Rerun its stage in a new directory; preserve the previous attempt |
| Failed or timed-out stage | Do not cache success; retry in a fresh directory on the next invocation |

Each stage has an immutable attempt directory under the selected output's `cache/`. Receipts record declared input fingerprints, commands, settings, output fingerprints and execution duration. Cache hits also verify output contents. Changing a compiler without changing its resulting SID bytes can therefore reuse the prior render. Declared dependencies must cover the actual imported modules, binaries, data and settings: the runner cannot discover arbitrary file reads performed by a command.

Before saving a new success receipt, the runner verifies that the stage’s declared inputs, executable and runner/Python fingerprints still match. Before publishing listening links, it rechecks every stage's declared inputs and executable, including reused stages, and the runner/Python fingerprints. This catches an edit to an early dependency while a later stage is running. A changed dependency fails the package and suppresses its listening links; retained attempts remain available for inspection. These content checks do not lock the filesystem against concurrent edits or detect a change that is reverted between checks.

`run.json` describes the latest invocation, including status, stage timings, reuse and delivered paths. `listening.md` is its human-readable index; these two index files may change, while historical audio and stage outputs remain intact. Do not compress or modify files inside a live package cache: that invalidates its output fingerprints. Historical standalone receipts remain valid evidence but are not automatically imported as cache entries. A first run establishes the runner's own records.

## Preserve stable audition filenames

After a completed run, use [publish-listening.py](../../scripts/publish-listening.py) to copy an explicitly selected set of verified WAVs into a fresh local folder. This keeps submitted sound samples stable while later recipe invocations update their indexes. It does not upload files or add audio to Git. For the complete Ghouls package:

```sh
python3 scripts/publish-listening.py build/ghouls-independent-full/run.json --selection config/listening/ghouls-full.audition.json --output build/ghouls-listening
```

The [selection](../../config/listening/ghouls-full.audition.json) maps existing deliverable labels to flat `.wav` filenames. Choose only the full reference, candidate and comparisons needed for feedback. The destination must be new and below ignored `build/`; use a new folder for a revised submission. Independent copies consume additional local space but preserve the submitted audio even when a cache is later cleaned.

The publisher requires a completed run with successful stages and matching file hashes in both the run and owning stage. It rejects missing or changed files, unknown labels, duplicate names, traversal, symlinks and existing destinations. It checks source, copied audio, run and selection hashes again before making the prepared folder available. `sources.json` records the original paths, fingerprints and chosen filenames. These content checks are not filesystem locks. Original reference audio and comparisons containing it remain local, outside Git and LFS.

## Write a recipe

Recipes are trusted executable project configuration. Commands run as argument arrays without a shell, from the repository root, with explicit deadlines. The runner confines its managed output to ignored `build/`; it is not a sandbox for arbitrary commands. Keep reference SID/WAV files and all comparisons containing reference audio out of Git and LFS.

Use the [Monty recipe](../../config/listening/monty-reference-continuation.json) as the complete example. Each stage declares:

- `id`: a unique identifier, referenced by later stages.
- `command`: an argument array; use `{python}` for the current interpreter, `{root}` for the project root, `{out}` for this stage's fresh attempt directory and `{stage:ID}` for an earlier successful stage's directory.
- `inputs`: files or directories whose content affects the stage, including imported code and tool data. Directory fingerprints cover their file contents.
- `outputs`: relative file paths that must exist after success and retain their hashes for reuse. A read-only verifier may declare an empty list.
- `timeoutSeconds`: the process deadline. Optional `env` contains explicit environment overrides; Python recipes disable bytecode writes when dependency directories are inputs.

Optional top-level `deliverables` maps listening labels to declared stage outputs. Use it for reference and candidate audio and the small A/B set the listener actually needs. Every successful invocation emits those links automatically; agents should not recreate receipts, hand-build listening indexes or poll individual pipeline steps.

For a declared finite ending, the `check-listening.py audio` stage can add `--tail-seconds 1 --max-tail-ac-rms 1`. Both arguments are required together. By default, `--tail-target both` checks the final rounded sample window in each render and rejects any channel above the AC RMS limit in PCM16 units. When the reference deliberately continues or restarts, select `--tail-target candidate` to check only the authored ending; `reference` is also available. A selected target requires both tail settings. The receipt names the selected target and retains per-channel AC RMS and DC; both full renders still receive format, duration, clipping and nonzero-signal checks. Silence alone does not establish a complete musical ending, so keep the matched ending comparison and listener verdict.

For an independently authored ending after an unchanged source passage, `check-listening.py writes --candidate-prefix --calls N` compares initialization and every ordered store in candidate calls `[0,N)` against the pinned source ledger. It validates syntax and tick ordering throughout the candidate, but excludes later stores from identity comparison and records their count as `excludedCandidateWrites`; `scope.candidatePrefix` makes that boundary explicit. Without the flag, extra candidate calls remain an error. This supports source-preservation evidence for the musical portion only; verify the complete candidate and ending separately through CPU/VICE execution and rendered audio.

## Validation and performance

The runner's focused tests exercise cache reuse, changed inputs and commands, corrupt or missing outputs, failed and timed-out processes, preserved prior attempts and invalid dependency paths. The [listening checks](../../scripts/check-listening.py) independently verify asset pins, ordered register stores and WAV signal contracts.

Monty's numeric player captures requested state checkpoints in one traversal. Its compiler still validates the full declared input even for a diagnostic CPU prefix; the optimization removes repeated oracle computation without reducing the checked musical range. CPU, source-store, VICE, rendered-signal and listening evidence remain distinct.

Measure cold and repeated invocations using their `run.json` receipts. Before the cached repeat overwrites that index, retain the completed fresh invocation as `first-run.json` (or another explicitly named fresh-run receipt); retain the repeat separately when promoting evidence. Stage execution times and cache-check overhead are different measurements; do not infer a rendering speedup from total workflow savings or compare runs with different verification coverage.

On 2026-10-13, the [recorded Monty benchmark](listening-package-benchmark.json) took **151.47 seconds** for a fresh nine-stage package, **0.39 seconds** when repeated unchanged, and **0.67 seconds** after changing only the ending window (only that comparison ran). Full reference/candidate PCM and the original ending A/B retained their accepted hashes. The cold run spent 97.76 seconds in the CPU audit; each full 355-second render took about 4.4 seconds. These are single local observations, not universal speed guarantees.

After review added the per-stage and final consistency checks, another full run on the same date passed in **141.28 seconds**, followed by an unchanged run in **0.53 seconds** with all nine stages reused and no stage subprocesses. All four delivered audio files retained the accepted SHA-256 values. The same benchmark record retains the new runner fingerprint, stage timings and local receipt hashes separately from the earlier measurements.
