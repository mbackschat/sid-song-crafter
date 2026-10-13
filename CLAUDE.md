# SID Song Crafter Project Guide

Read with [AGENTS.md](AGENTS.md), which owns contributor conventions, commands and repository layout. Prioritize expressive SID music and reusable knowledge. Correct notes and successful playback do not establish musical quality.

## Continue the workbench

Use the [study plan](docs/research/study-plan.md) for the active case and next milestone. SID Song Crafter is a composition and sound-design workbench for the Commodore 64 SID chip, supporting single- and dual-SID music; reusable playback code serves expressive music and an executable repertoire. A verified loop or pleasing excerpt does not complete a whole-song deliverable.

## Finish musical deliverables

Keep one musical case active, in the [plan's delivery order](docs/research/study-plan.md#delivery-order-and-work-in-progress). Finish its export, ending, listening review and transfer to different musical material before deepening another study. Numeric agreement is preparation; successful reuse in a listening-reviewed phrase from different musical material is the decisive test of the workbench's value. While feedback is pending, finish that case's reproducibility and reuse documentation; spare agent capacity is not a reason to open another investigation. Preserve deferred work.

Before additional analysis, name the unresolved question, the deliverable or decision it blocks, and the evidence that will settle it. Once that evidence passes, advance to the next delivery stage. Reopen only for changed inputs, a demonstrated mismatch or an explicit expansion of the supported contract. Follow the [delivery and reuse workflow](docs/workflows/decoded-song-workflow.md#deliver-one-musical-case) without weakening required execution or full-form checks.

Use a familiar, source-backed phrase as the default transfer test, with a same-material reference. This separates instrument usefulness from the quality of a newly invented composition. Original composition remains valuable but is a separate musical judgment, not a prerequisite for every instrument study.

## Checkpoints and documentation

Commit autonomously after a coherent feature set or meaningful verified checkpoint. Batch related implementation, tests and findings into reviewable commits; avoid a commit for every small edit. Never push without authorization.

Keep guides in task-oriented subfolders under [docs](docs/README.md), with navigation from its README. Keep research in its existing indexed folders. Use [local setup](docs/setup/local-setup.md) and `python3 scripts/doctor.py` for readiness; read [skill corrections](docs/setup/skill-guidance.md) before applying downloaded instructions.

Follow the [tool boundaries](scripts/README.md): source-specific extractors, experiments and fixed examples belong under [scripts/studies](scripts/studies/README.md). Keep supported composition backends and shared validation APIs separate from their case-study inputs. Preserve documented compatibility exceptions and frozen evidence paths; relocation must not rewrite historical provenance.

## Retrieve before researching

Start with the [technique lookup](docs/research/technique-index.md), then read only the relevant owning study. Search locally before new research. Reuse demonstrated methods after checking their model, timing, voice dependencies and listening verdict. Repair missing index routes.

| Task | References |
| --- | --- |
| Understand the chip | [Hardware](docs/research/sid/hardware.md), [advanced techniques](docs/research/sid/advanced-techniques.md), [timing](docs/research/sid/playback-and-timing.md) |
| Study masters and their tools | [Composers](docs/research/composers/README.md), [commented sources and manuals](docs/research/tools/source-studies.md) |
| Reverse-engineer an instrument | [Execution-based procedure](docs/research/tools/sid-program-analysis.md), [DRAX reconstruction](songs/studies/drax-bass-reconstruction/README.md), [Cybernoid II model, compiled title and finite ending](docs/research/composition/cybernoid-ii-preparation.md), [Cybernoid familiar transfer and native timing/tuning limits](docs/research/composition/instruments/cybernoid-decoded-programs.md) |
| Choose expressive material | [Sound repertoire](docs/research/composition/sound-design-repertoire.md), [instruments](docs/research/composition/instruments/README.md), [gestures](docs/research/composition/gestures/README.md) |
| Compose from decoded mechanisms | [Computed-player workflow](docs/workflows/decoded-song-workflow.md), [complete DRAX theme](songs/studies/drax-full-reconstruction/README.md), [Flashdance and dual-SID preparation](docs/research/composition/flashdance-preparation.md), [Shades CIA reconstruction and transfer](docs/research/composition/shades-preparation.md#independent-export-and-original-transfer) |
| Preserve shared PWM and live pitch aliases | [Monty independent integration](docs/research/composition/monty-preparation.md#independent-editable-score-and-sound-integration), [packed-score compiler contract](docs/workflows/decoded-song-workflow.md#monty-packed-score-player), [familiar transfer and native articulation limits](docs/research/composition/instruments/monty-decoded-programs.md) |
| Arrange and export | [Source preservation](docs/workflows/song-workflow.md), [native workflow](docs/workflows/native-song-workflow.md), [dual SID](docs/research/sid/dual-sid.md), [editor assessment](docs/research/tools/composition-tools.md) |
| Run and inspect headlessly | [Setup](docs/setup/local-setup.md), [audio](docs/workflows/audio-workflow.md), [callable PSID audit and SID port coverage](docs/validation/psid-audit.md), [VICE checks](docs/validation/native-vice-checks.md), [verified capabilities](docs/research/tools/skills-and-integrations.md) |
| Prepare listening comparisons | [Comparison workflow](docs/workflows/audio-comparisons.md), [DRAX reference and feedback](docs/research/composition/fuer-elise-reference.md) |
| Find sources or skills | [Research index](docs/research/README.md), [provenance](docs/research/sources.md), [installed skills](skills/README.md) |
| Download or inspect references; restore evidence | [Source URLs, fingerprints, downloads and metadata inspection](docs/setup/local-setup.md), [archive verification and cache restoration](docs/workflows/build-cache.md), [canonical evidence index](evidence/README.md) |

## Preserve sources and SID expression

Retain originals, provenance and checksums; disclose conversion losses and deliberate arrangement changes. Common scores are optional. MIDI can describe notes but must not constrain native waveform/pitch tables, envelopes, modulation, filters, timing or voice dependencies. The generated `fuer-elise.melody.json` is an onset report retaining exact `frequencyWord` values, not an instrument program.

Keep editable recipes/workfiles with exported players; follow the owning workflow's conversion contract. A WAV or register dump alone is insufficient reusable instrument source.

Declare clock, chip model/count, addresses and update cadence. Account for shared filters, ring/sync dependencies, retriggering and modulation during release. Time-sharing percussion and bass on one voice can create additional instrument roles, but cannot preserve independent overlapping tails. Give dual SID deliberate musical roles. Choose effects through listening, including recorded rejected approaches.

## Learn mechanisms through execution

Follow the linked procedure: pin tune/profile/passage → execute from initialization → trace ordered SID writes and their executed code/tables → test a causal intervention → independently implement editable behavior → compare in context → transfer to another phrase.

Read interviews, manuals and commented sources alongside traces. Distinguish author statements, recovered code and inference. Captured-event replay does not prove an algorithm was understood. Register/code evidence explains programming; audio measurements support alignment, levels, clipping and endings. Remove superseded speculation.

Prefer verified headless VICE and file-monitor workflows. Use bridge tools only when actually connected. Instruction timestamps, checkpoints, frame snapshots and bus writes are different observations; separate bridge reads may resume execution between calls. Rendering does not prove speaker playback or listening.

## Listening and retained findings

For repeated build/render/comparison work, use the [recipe runner](docs/workflows/listening-package.md) and an owning checked-in recipe. Let it manage commands, deadlines, receipts, stage timings and the listening index. Reuse successful stages only after their declared input and output fingerprints match; include imported modules, tool binaries and data in recipe inputs. Change the recipe or fix a failed stage instead of manually recreating the pipeline. Musical judgments remain separate.

Use the [listening package](docs/workflows/audio-comparisons.md#package-a-listening-review): a representative phrase, a separate ending comparison and direct links to both full renders. Offer few labelled clips with actual filenames, A/B order and one clear question per judgment. Identify originals, muted diagnostics, independent recreations and hybrids. Match phrase/model/settings; retain original levels and record gains. Use common gain for contextual substitutions. Preserve shared audition files and stop iterating when asked to await feedback.

Present the reference alongside every generated reconstruction or A/B candidate. For genuinely new music, say explicitly that it is an original composition and identify the reused sounds; there is no original recording of that phrase. Link the source tune when it helps compare those sounds, clearly labelled as a timbral reference.

Record the listener's verdict with its exact scope: perceptual agreement on one passage does not establish PCM identity, hardware equivalence or approval of another arrangement.

Keep reusable mechanisms, constraints, provenance and reproduction instructions in one owning document; link from indexes. Retain acquired knowhow as searchable lookup tables and tested scripts/modules where those make the next task easier; documentation and reusable code complement each other. Promote repeatable probes into supported tools instead of requiring the next session to rediscover or rebuild them. Preserve full evidence in the format that retains its detail: structured traces, state snapshots, tables, code and audio as appropriate. Prose should explain and index that evidence, not replace it with a lossy summary. Preserve canonical analysis archives through [Git LFS and readable manifests](evidence/README.md); use ignored `build/` for working output. Follow the [public repository boundary](AGENTS.md#public-repository-boundary) for original SIDs and reference WAVs, retaining source URLs and SHA-256 fingerprints in the download registry. No session diaries. Prefer searchable text/source; extract digital PDFs before OCR. Respect source redistribution limits. Promote instruments with editable parameters, purpose, target assumptions, demonstration, limitations and listening status.

## Use MEDIUM sub-agents selectively

**Model tiers are symbolic (HIGH, MEDIUM).** Resolve them through the tier table in your global instructions; the maintainer's table is [Model tier mappings](https://github.com/mbackschat/coding-setup/blob/main/CLAUDE.md#model-tier-mappings). Without such a table, run HIGH on your most capable model and MEDIUM on a faster, cheaper one, and say which models you used. Do not duplicate mappings or silently substitute unsupported configurations.

Delegation is authorized; prefer MEDIUM for bounded independent investigation, isolated implementation or consequential review. Keep small or tightly dependent work local. Keep every assignment tied to the active musical deliverable or a concrete dependency it needs. Give minimal sufficient context, file ownership and acceptance criteria, including a stopping condition. Reuse informed agents; batch related tasks and avoid duplicate research/testing. The coordinator owns integration and claims. Escalate only for demonstrated difficulty; stop obsolete work.

## Choose validation that answers the question

This project permits judgment instead of mandatory red/green TDD everywhere. Define success and its oracle before implementation.

- **Reusable software/bugs:** prefer red/green guards covering meaningful behavior and the defect's mechanism.
- **Research:** use bounded experiments, instruction/register traces and independent execution; add focused tests when probes become tools.
- **Music:** verify exports/timing and listen in context; software checks cannot establish musical quality.
- **Documentation/configuration:** check links, parsing or a relevant smoke run; avoid artificial tests.

Retain reproducible inputs/settings. Distinguish proposed, implemented, rendered and listening-reviewed work. Repeat passed checks only when changes, failures or unresolved risks justify it.
