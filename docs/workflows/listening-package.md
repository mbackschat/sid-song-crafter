# Run a repeatable listening package

Use [listening-package.py](../../scripts/listening-package.py) to execute a checked-in recipe, retain stage timings and reuse successful stages whose inputs, commands, tools and outputs still match. This handles routine build, verification, rendering and comparison commands; the [listening workflow](audio-comparisons.md) still owns musical judgments. Recipes invoke ordinary project commands, not a universal SID compiler.

## Reproduce the accepted Monty comparison

Prepare the [local tools and assets](../setup/local-setup.md), including the pinned Monty reference, headless VICE and [renderer](audio-workflow.md). Then run:

```sh
python3 scripts/listening-package.py config/listening/monty-reference-continuation.json --output build/monty-listening
```

Run the same command again to reuse verified stages. Open `build/monty-listening/listening.md` for the full reference, full candidate, opening A/B and ending A/B. Each comparison plays the reference first, followed by a half-second gap and ours. The recipe preserves the original restart; capture stops at 355 seconds. That capture boundary is not a composed ending. The [Monty study](../research/composition/monty-preparation.md) owns the accepted musical scope and the separate finite-fade variant.

The command verifies the source SID fingerprint, compiles and audits all 40,000 declared calls, compares the entire ordered store stream against the retained original ledger, checks the restart in headless VICE, renders both versions from initialization, checks WAV format/duration/clipping and prepares the two comparisons. VICE uses the local source checkout's data directory; no GUI application path is required. The example fingerprints the documented Apple Silicon Homebrew `libintl` dependency by its stable `/opt/homebrew/opt/gettext/lib/libintl.8.dylib` path; adapt that declared input when using a different VICE installation. Failed stages stop the package and retain their logs. The command never infers musical acceptance from a successful run.

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

## Write a recipe

Recipes are trusted executable project configuration. Commands run as argument arrays without a shell, from the repository root, with explicit deadlines. The runner confines its managed output to ignored `build/`; it is not a sandbox for arbitrary commands. Keep reference SID/WAV files and all comparisons containing reference audio out of Git and LFS.

Use the [Monty recipe](../../config/listening/monty-reference-continuation.json) as the complete example. Each stage declares:

- `id`: a unique identifier, referenced by later stages.
- `command`: an argument array; use `{python}` for the current interpreter, `{root}` for the project root, `{out}` for this stage's fresh attempt directory and `{stage:ID}` for an earlier successful stage's directory.
- `inputs`: files or directories whose content affects the stage, including imported code and tool data. Directory fingerprints cover their file contents.
- `outputs`: relative file paths that must exist after success and retain their hashes for reuse. A read-only verifier may declare an empty list.
- `timeoutSeconds`: the process deadline. Optional `env` contains explicit environment overrides; Python recipes disable bytecode writes when dependency directories are inputs.

Optional top-level `deliverables` maps listening labels to declared stage outputs. Use it for reference and candidate audio and the small A/B set the listener actually needs. Every successful invocation emits those links automatically; agents should not recreate receipts, hand-build listening indexes or poll individual pipeline steps.

## Validation and performance

The runner's focused tests exercise cache reuse, changed inputs and commands, corrupt or missing outputs, failed and timed-out processes, preserved prior attempts and invalid dependency paths. The [listening checks](../../scripts/check-listening.py) independently verify asset pins, ordered register stores and WAV signal contracts.

Monty's numeric player captures requested state checkpoints in one traversal. Its compiler still validates the full declared input even for a diagnostic CPU prefix; the optimization removes repeated oracle computation without reducing the checked musical range. CPU, source-store, VICE, rendered-signal and listening evidence remain distinct.

Measure cold and repeated invocations using their `run.json` receipts. Stage execution times and cache-check overhead are different measurements; do not infer a rendering speedup from total workflow savings or compare runs with different verification coverage.

On 2026-10-13, the [recorded Monty benchmark](listening-package-benchmark.json) took **151.47 seconds** for a fresh nine-stage package, **0.39 seconds** when repeated unchanged, and **0.67 seconds** after changing only the ending window (only that comparison ran). Full reference/candidate PCM and the original ending A/B retained their accepted hashes. The cold run spent 97.76 seconds in the CPU audit; each full 355-second render took about 4.4 seconds. These are single local observations, not universal speed guarantees.

After review added the per-stage and final consistency checks, another full run on the same date passed in **141.28 seconds**, followed by an unchanged run in **0.53 seconds** with all nine stages reused and no stage subprocesses. All four delivered audio files retained the accepted SHA-256 values. The same benchmark record retains the new runner fingerprint, stage timings and local receipt hashes separately from the earlier measurements.
