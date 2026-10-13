# C64 SID Project Guide

Read with [AGENTS.md](AGENTS.md), which owns contributor conventions, commands and repository layout. Prioritize expressive SID music and reusable knowledge. Correct notes and successful playback do not establish musical quality.

## Retrieve before researching

Start with the [technique lookup](docs/research/technique-index.md), then read only the relevant owning study. Search locally before new research. Reuse demonstrated methods after checking their model, timing, voice dependencies and listening verdict. Repair missing index routes.

| Task | References |
| --- | --- |
| Understand the chip | [Hardware](docs/research/sid/hardware.md), [advanced techniques](docs/research/sid/advanced-techniques.md), [timing](docs/research/sid/playback-and-timing.md) |
| Study masters and their tools | [Composers](docs/research/composers/README.md), [commented sources and manuals](docs/research/tools/source-studies.md) |
| Reverse-engineer an instrument | [Execution-based procedure](docs/research/tools/sid-program-analysis.md), [DRAX reconstruction](songs/studies/drax-bass-reconstruction/README.md) |
| Choose expressive material | [Sound repertoire](docs/research/composition/sound-design-repertoire.md), [instruments](docs/research/composition/instruments/README.md), [gestures](docs/research/composition/gestures/README.md) |
| Compose from decoded mechanisms | [Computed-player workflow](docs/decoded-song-workflow.md), [complete DRAX theme](songs/studies/drax-full-reconstruction/README.md), [Flashdance and dual-SID preparation](docs/research/composition/flashdance-preparation.md) |
| Arrange and export | [Source preservation](docs/song-workflow.md), [native workflow](docs/native-song-workflow.md), [dual SID](docs/research/sid/dual-sid.md), [editor assessment](docs/research/tools/composition-tools.md) |
| Run and inspect headlessly | [Setup](docs/local-setup.md), [audio](docs/audio-workflow.md), [VICE checks](docs/native-vice-checks.md), [verified capabilities](docs/research/tools/skills-and-integrations.md) |
| Prepare listening comparisons | [Comparison workflow](docs/audio-comparisons.md), [DRAX reference and feedback](docs/research/composition/fuer-elise-reference.md) |
| Find sources or skills | [Research index](docs/research/README.md), [provenance](docs/research/sources.md), [installed skills](skills/README.md) |

## Preserve sources and SID expression

Retain originals, provenance and checksums; disclose conversion losses and deliberate arrangement changes. Common scores are optional. MIDI can describe notes but must not constrain native waveform/pitch tables, envelopes, modulation, filters, timing or voice dependencies. The generated `fuer-elise.melody.json` is an onset report retaining exact `frequencyWord` values, not an instrument program.

Keep editable recipes/workfiles with exported players; follow the owning workflow's conversion contract. A WAV or register dump alone is insufficient reusable instrument source.

Declare clock, chip model/count, addresses and update cadence. Account for shared filters, ring/sync dependencies, retriggering and modulation during release. Time-sharing percussion and bass on one voice can create additional instrument roles, but cannot preserve independent overlapping tails. Give dual SID deliberate musical roles. Choose effects through listening, including recorded rejected approaches.

## Learn mechanisms through execution

Follow the linked procedure: pin tune/profile/passage → execute from initialization → trace ordered SID writes and their executed code/tables → test a causal intervention → independently implement editable behavior → compare in context → transfer to another phrase.

Read interviews, manuals and commented sources alongside traces. Distinguish author statements, recovered code and inference. Captured-event replay does not prove an algorithm was understood. Register/code evidence explains programming; audio measurements support alignment, levels, clipping and endings. Remove superseded speculation.

Prefer verified headless VICE and file-monitor workflows. Use bridge tools only when actually connected. Instruction timestamps, checkpoints, frame snapshots and bus writes are different observations; separate bridge reads may resume execution between calls. Rendering does not prove speaker playback or listening.

## Listening and retained findings

Offer few labelled clips with A/B order and one clear question. Identify originals, muted diagnostics, independent recreations and hybrids. Match phrase/model/settings; retain original levels and record gains. Use common gain for contextual substitutions. Preserve shared audition files and stop iterating when asked to await feedback.

Record the listener's verdict with its exact scope: perceptual agreement on one passage does not establish PCM identity, hardware equivalence or approval of another arrangement.

Keep reusable mechanisms, constraints, provenance and reproduction instructions in one owning document; link from indexes. Keep raw evidence in ignored outputs. No session diaries. Prefer searchable text/source; extract digital PDFs before OCR. Respect source redistribution limits. Promote instruments with editable parameters, purpose, target assumptions, demonstration, limitations and listening status.

## Use MEDIUM sub-agents selectively

**Model tiers are symbolic (HIGH, MEDIUM).** Resolve them through the tier table in your global instructions; the maintainer's table is [Model tier mappings](https://github.com/mbackschat/coding-setup/blob/main/CLAUDE.md#model-tier-mappings). Without such a table, run HIGH on your most capable model and MEDIUM on a faster, cheaper one, and say which models you used. Do not duplicate mappings or silently substitute unsupported configurations.

Delegation is authorized; prefer MEDIUM for bounded independent investigation, isolated implementation or consequential review. Keep small or tightly dependent work local. Give minimal sufficient context, file ownership and acceptance criteria. Reuse informed agents; batch related tasks and avoid duplicate research/testing. The coordinator owns integration and claims. Escalate only for demonstrated difficulty; stop obsolete work.

## Choose validation that answers the question

This project permits judgment instead of mandatory red/green TDD everywhere. Define success and its oracle before implementation.

- **Reusable software/bugs:** prefer red/green guards covering meaningful behavior and the defect's mechanism.
- **Research:** use bounded experiments, instruction/register traces and independent execution; add focused tests when probes become tools.
- **Music:** verify exports/timing and listen in context; software checks cannot establish musical quality.
- **Documentation/configuration:** check links, parsing or a relevant smoke run; avoid artificial tests.

Retain reproducible inputs/settings. Distinguish proposed, implemented, rendered and listening-reviewed work. Repeat passed checks only when changes, failures or unresolved risks justify it.
