# Reproduce a selected reference intake

Use [reference-intake.py](../../scripts/reference-intake.py) for repeatable source selection, bounded execution and source listening excerpts. A small spec is converted to a [cached runner recipe](listening-package.md); immutable attempts retain source hashes, registry URLs, subtunes, header declarations, settings, diagnostics and outputs. This prepares evidence for the [required composer contrasts](../PLAN.md#required-contrasting-references-for-the-six-composers). It does not decode a driver or establish causal corroboration, listening acceptance or a complete song.

## Run the checked-in examples

Prepare the pinned [renderer and local tools](audio-workflow.md), including its explicit `--subtune` and `--clock` support. Acquire sources on demand through the existing [download registry workflow](../setup/local-setup.md#original-sid-downloads-on-demand), then run:

```sh
python3 scripts/setup-project.py --only references --include rambo-first-blood-part-ii --include arkanoid
python3 scripts/reference-intake.py run config/reference-intake/rambo-subtunes.json --output build/reference-intake/rambo-subtunes
python3 scripts/reference-intake.py run config/reference-intake/galway-contrast.json --output build/reference-intake/galway-contrast
```

The [Rambo subtune spec](../../config/reference-intake/rambo-subtunes.json) checks the original #1 and corrected-Morse #2 selection. These are variants of one work, so their comparison does not satisfy the different-work Galway requirement. The [Galway contrast spec](../../config/reference-intake/galway-contrast.json) captures Rambo #1 and Arkanoid title #1 through their different declared execution routes. Its opening is a pipeline demonstration; selecting passages that settle the study's hypotheses, instruction-level causal evidence and listening judgments remain required separately.

Open the selected output's `listening.md` for both complete **bounded renders**, source receipts and the sourceA-then-sourceB clip. “Complete bounded render” means all requested seconds, not a complete song. `run.json` retains stage outcomes, durations, input/output fingerprints and reuse. Run the same command again to reuse verified stages; changed sources, dependencies, settings or outputs invalidate affected stages. Missing sources produce an acquisition instruction; the intake runner performs no networking or source-header modification.

## Pin the exact STIL entry

Use [inspect-stil.py](../../scripts/inspect-stil.py) when interpreting tune or subtune credits from a locally retained STIL database:

```sh
python3 scripts/inspect-stil.py --stil .local/downloads/HVSC-STIL.txt --entry MUSICIANS/H/Hubbard_Rob/Commando.sid --output build/commando-stil-entry
```

The output directory must be fresh and inside ignored `build/`. `entry.txt` preserves the original bytes and line endings; `receipt.json` pins the database and entry hashes, byte counts and line bounds. Match a complete entry header: a substring search can select another tune's comment that merely mentions this path. Reading bytes also avoids assuming UTF-8 for older database text. Missing or duplicate headers fail explicitly.

Interpret the selected subtune's credits separately from the C64 arranger and from other subtunes. The extractor identifies the source entry; it does not resolve attribution or verify STIL timestamps against playback. Keep the database and extracted text local, and retain source URLs, hashes and a scoped paraphrase in the study.

## Specification contract

Specs require `schemaVersion: 1`, one or two ordered `selections`, one to eight `windows`, and an optional `gapSeconds` from 0 to 60, default 0.5. Each selection requires a registered `assetId`, a source-only `role`, an explicit one-based `subtune`, `route` and `renderSeconds`. Render duration must be positive and at most 600 seconds. Roles record the intake decision; archive metadata and published accounts must establish a subtune's musical identity independently.

| Route | Required fields and admission | Retained observation |
| --- | --- | --- |
| `pal-banked` | `calls`: integer 1–40,000; optional page-aligned `hostBase` in `$0400–$9E00`; declared PAL; intact source must pass the existing [callable profile](../validation/psid-audit.md#select-a-subtune-and-expose-ram-beneath-basic) | CPU audit and ordered initialization/play stores under the controlled host, plus initialized modeled audio and renderer-iteration snapshots |
| `full-machine-render` | No `calls` or `hostBase`; declared PAL or NTSC; choose this explicitly for CIA/RSID or other machine-controlled playback admitted by the renderer | libsidplayfp initialized source audio and renderer-iteration register snapshots; no callable CPU ledger, bus-write timing or causal proof |

The contract accepts PSID/RSID version 2, exactly one SID, explicitly declared PAL or NTSC and MOS6581 or MOS8580 with standard flags. Declared NTSC is admitted only through `full-machine-render`; `pal-banked` remains PAL-only. Unknown, mixed or incompatible model/clock declarations are rejected. There are no implicit experimental assumptions, fallback to callable execution or patched source headers. A renderer error remains a failed stage with its log; an unsupported source requires a documented suitable route rather than weakening admission. Source audio uses libsidplayfp 3.1.1/SIDLite, explicit `--clock pal` or `--clock ntsc` matching the header declaration, the declared model, selected subtune, power-on delay zero, 44.1 kHz mono PCM16 and unity gain. The forced renderer clock and retained declaration do not establish interrupt cadence, physical frame timing or original-host equivalence.

Each window has a unique path-safe `id`, `startSeconds` and exclusive `endSeconds`; it must contain PCM frames and fit every selected render. A single selection produces an original excerpt. Two selections produce the same time interval from sourceA, a recorded silence gap, then sourceB. This is a **source contrast**, not a reconstruction fidelity A/B: the two works need not share musical material, onset alignment or form. The tool retains original levels and source render hashes; it performs no normalization, resampling or independent alignment.

## Evidence and dependency boundaries

The command loads and validates the spec once, retaining its operative selection values and window settings as literal arguments in an immutable generated recipe. Selection receipts verify the snapshotted registry fingerprint and source pin before audit or rendering. The runner declares the registry, source bytes, imported Python modules, py65 dependency for callable auditing, renderer source/binary and linked libsidplayfp archive. Its final consistency checks reject dependencies that changed during the package. Editing the spec after invocation does not steer that loaded snapshot; rerun the command to apply an edit. Changing only a window retains cached source selection, audit, render and measurements, then regenerates that window. Historical audio and successful stage attempts remain intact; recipe creation and managed outputs are confined to ignored `build/` and reject symlink paths.

Source receipts separately identify callable admission, whether ordered CPU stores were requested, the explicitly forced declared renderer clock, and renderer snapshots. The successful CPU audit and ordered ledger have their own listening-index links; `run.json` determines whether every requested stage completed. A selection receipt alone is admission evidence. Snapshot rows observe the renderer's current SID registers after each rendering iteration, which is not a one-to-one C64-frame trace; they cannot retain all intervening volume-register writes, instruction causality or original bus timing. WAV checks establish requested format/duration, nonzero AC signal and absence of PCM rail samples. They do not establish sound quality, original-hardware equivalence or perceptual agreement. Source and window receipts keep `listeningReview: null`.

Keep original SIDs, source WAVs and every excerpt/contrast containing source audio outside Git and LFS. [The asset registry](../../config/local-assets.json) owns source acquisition pins; [canonical evidence retention](build-cache.md) remains a separate operation. Do not publish these private runner caches as analysis archives.

## Validate the orchestration

```sh
python3 -m unittest discover -s tests -p 'reference_intake_test.py' -v
```

The tests cover mismatched source pins before outputs, explicit subtune/clock propagation, declared NTSC RSID render-only receipts, PAL-only callable admission, CIA/RSID admission distinctions, model/clock/layout rejection, bounds, source-only labels, immutable reuse, changed binary dependencies and output confinement. Real source recipes independently exercise Rambo's two subtunes and Arkanoid's RSID renderer route; their receipts prove the declared bounded capture only.

The 2026-10-13 verification covers both checked-in specs' six-second initialized source renders, with nonzero AC signal and no PCM rail samples. Rambo #1 and #2 produced different audio and each passed its 128-call audit; Arkanoid completed the explicit machine-render route without a callable ledger. These orchestration checks establish no causal corroboration or listening acceptance.

The [retained validation](../../evidence/reference-intake-workflow/validation.json) records source hashes, selections, routes and audio measurements without audio bytes. A separate preserved nine-stage Rambo benchmark took [2.92 seconds cold](../../evidence/reference-intake-workflow/rambo-cold.json), [0.07 seconds unchanged](../../evidence/reference-intake-workflow/rambo-hot.json) and [0.30 seconds for a window-only edit](../../evidence/reference-intake-workflow/rambo-window.json). These measure the specified six-second excerpts on this host, not full-song rendering performance.
