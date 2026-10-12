# C64 SID Project Guide

Read this guide with [Repository Guidelines](AGENTS.md), which owns contributor conventions and routine build/test commands. This file defines how to conduct SID work, retrieve the project's knowledge, select tools, use feedback and delegate efficiently. Its testing policy is the project-specific exception to mandatory red/green TDD for every change.

## Purpose and musical standard

Build expressive music for one or two Commodore 64 SID chips, and make each song improve our reusable instruments, techniques and tools. The priority is outstanding SID sound: phrasing, groove, texture, contrast and deliberate use of the chip's capabilities. Correct pitches and successful playback establish a baseline; they do not establish an accomplished arrangement.

Treat Für Elise and Flashdance as learning cases as well as deliverables. Preserve the recognizable musical material while making intentional SID interpretations, including improvisation and changed accompaniment where appropriate. Keep those choices separate from source preservation. Study both how masters composed and how their editors and players made their sounds possible.

## Start each task with existing knowledge

1. Identify the musical or technical question, the requested scope and the evidence that would answer it. For a listening complaint, use the listener's vocabulary before translating it into a synthesis hypothesis.
2. Consult the [technique lookup](docs/research/technique-index.md), then the relevant owning study, instrument or workflow. Search locally with `rg` before starting new research. Read the necessary route, not the whole library on every turn.
3. Reuse a demonstrated method or editable example where it fits. Check its chip model, voice dependencies, player timing and listening verdict. If retrieval fails, repair the index so the next task is easier.
4. Complete a bounded experiment or musical change, verify the relevant behavior, and record the useful result in its owning document. Keep proposed, implemented, rendered and listening-reviewed work distinct.

## References by task

| Task | Start here |
| --- | --- |
| Find a technique from a musical need | [Technique lookup](docs/research/technique-index.md) and [research library](docs/research/README.md) |
| Understand registers, envelopes and chip quirks | [Hardware](docs/research/sid/hardware.md), [advanced techniques](docs/research/sid/advanced-techniques.md), [playback timing](docs/research/sid/playback-and-timing.md) |
| Study composers and their working tools | [Composer studies](docs/research/composers/README.md), [listening catalogue](docs/research/composers/listening-catalogue.md), [commented sources and manuals](docs/research/tools/source-studies.md) |
| Explain and recreate a master's instrument | [Executed-program procedure](docs/research/tools/sid-program-analysis.md), [DRAX reconstruction and contextual comparison](songs/studies/drax-bass-reconstruction/README.md) |
| Choose instruments and expressive gestures | [Sound repertoire](docs/research/composition/sound-design-repertoire.md), [native instrument bank](docs/research/composition/instruments/README.md), [gesture library](docs/research/composition/gestures/README.md) |
| Preserve a source and arrange a song | [Source-to-SID boundaries](docs/song-workflow.md), [Für Elise source/repeat study](docs/fuer-elise-score.md), [native song workflow](docs/native-song-workflow.md) |
| Choose an editor or exported player | [Composition-tool assessment](docs/research/tools/composition-tools.md), [SID-Wizard export contract](docs/research/tools/sid-wizard-trial.md) |
| Arrange for two chips | [Dual SID design](docs/research/sid/dual-sid.md) and [native one-/two-SID workflow](docs/native-song-workflow.md) |
| Run or inspect music headlessly | [Audio workflow](docs/audio-workflow.md), [CPU audit](docs/psid-audit.md), [native VICE checks](docs/native-vice-checks.md), [verified tool capabilities](docs/research/tools/skills-and-integrations.md) |
| Prepare a fair listening comparison | [Audio comparisons](docs/audio-comparisons.md), [instrument trials](docs/instrument-trials.md), [DRAX reference and listener attribution](docs/research/composition/fuer-elise-reference.md) |
| Reproduce the environment or troubleshoot VICE | [Local setup](docs/local-setup.md), [VICE investigation](docs/vice-startup-investigation.md), [installed skills](skills/README.md) |
| Establish provenance or locate study material | [Source register](docs/research/sources.md), [study corpus and rights](docs/research/composers/study-corpus.md), [Flashdance reference](docs/research/composition/flashdance-reference.md) |

## Preserve sources without constraining SID expression

Retain original notation, MIDI, tracker workfiles or SID binaries with provenance and checksums. Disclose importer losses, repeat interpretation, reductions and deliberate arrangement changes. Never replace the original with a normalized score or infer that an archived arrangement is the authority for the original notation.

A common score is an optional musical view. MIDI may supply notes or convenient pitch labels; it must not become the compulsory representation of SID instruments. The generated `fuer-elise.melody.json`, for example, labels nearest notes with `midi` while retaining exact `frequencyWord` values; it is an onset-analysis report, not a sound program. Native waveform/pitch tables, modulation, gate/envelope logic, filters, timing and voice dependencies remain independently editable. Direct SID-native composition is allowed and expected when it fits the work.

Keep an editable recipe/workfile and its exported player together. A WAV alone cannot reproduce an instrument; a register dump alone does not explain its algorithm. Native editor changes do not automatically round-trip into our JSON recipes. Follow the owning workflow's authority and conversion contract instead of silently treating divergent copies as interchangeable.

## Compose for the actual chip and player

- Declare the clock, SID model, chip count, base addresses and update cadence. Current native targets support PAL with one MOS6581/MOS8580 or two matching chips at `$D400/$D420`; consult the workflow before assuming another profile works. Equal numeric filter settings are not acoustically equivalent across models.
- Design instrument behavior over time: preparation, attack, pitched body, modulation, release and retriggering. Gate-off does not silence the oscillator immediately; waveform and modulation can continue during envelope release. The DRAX study demonstrates an instrument-authored early gate closure with continuing broad PWM.
- Allocate hardware voices and shared filters explicitly. More than three perceived instrument roles can come from time-sharing: a brief drum followed by bass on one oscillator. Budget the delayed pitched entrance and shared envelope; independent tails cannot coexist on that voice. Do not confuse this with a sample-based fourth channel.
- Check ring-modulation and sync dependencies before borrowing or muting a voice. Preserve intentional chord/pitch and waveform cycling through sustain and release. Use the [instrument cards](docs/research/composition/instruments/README.md) for executable examples and constraints.
- Give dual SID a musical purpose: additional overlap, separate filter groups or deliberate spatial roles. Six available voices do not require six continuously sounding parts. Verify both chips rather than checking only the first register block.
- Choose techniques for the phrase. A bright transient, resonant bass or dense arpeggio is useful only when listening supports it. Consult the [recorded preferences](docs/research/composition/gestures/README.md) before repeating rejected approaches.

## Study masters through execution and reconstruction

Use [the detailed procedure](docs/research/tools/sid-program-analysis.md) as the working method:

1. Pin the exact tune/version, subtune, model, clock and passage. Execute from initialization before cutting audio so envelope, oscillator and filter history are retained.
2. Identify the relevant voice or interaction. Diagnostic muting can locate a component, but must respect coupling and shared-filter limitations; retain the full mix as context.
3. Trace ordered SID stores, executed writer instructions and update cadence. Work backward through actual instruction history, instrument tables and changing state. Frame snapshots can hide multiple writes and their order.
4. Read composer interviews, published studies, manuals and commented source alongside the trace. Distinguish original author source, recovered listings, reverse-engineered labels and a related driver family. A family signature does not identify an exact editable workfile or prove authorship of every routine.
5. Make a controlled intervention to test a proposed cause, preserving the original. Verify which registers and timings actually changed before interpreting the audible result.
6. Implement the understood mechanism independently with editable parameters and a new note/phrase example. Captured-event replay or embedding the original driver is not proof that we have learned to program the instrument.
7. Compare execution and listen in context. State timing/state differences and the bounded verdict, then make the reusable example discoverable through the index.

Executed SID programming is the primary evidence for how the sound works. Audio measurements support alignment, level, clipping and ending checks. They do not establish an instrument algorithm, creative intent or musical quality. Remove superseded speculative explanations when stronger evidence settles the question; retain useful findings and listening preferences.

## Use tools according to verified capabilities

| Tool | Role and boundary |
| --- | --- |
| [c64-sid skill](skills/c64-sid/SKILL.md) | Hardware semantics and register reference; check the declared model and timing. |
| [sid-music skill](skills/sid-music/SKILL.md) | Select c64bridge playback operations when its MCP tools are actually connected. Installing instructions does not establish a working server connection. |
| [CPU program tracer](scripts/trace-sid-program.py) | Searchable instruction, RAM-operand and SID-write evidence for the supported callable-player profile; no full-machine IRQ or bus-cycle claim. |
| [VICE store tracer](scripts/trace-sid-vice.py) | Independent execution and ordered-store checks in a controlled headless harness. |
| VICE monitor history, checkpoints and memory inspection | Follow an executed write back to its cause using the [verified commands](docs/research/tools/skills-and-integrations.md#follow-draxs-waveform-with-vice-history). History is a finite buffer, not reverse execution. |
| [SID renderer](scripts/render-sid.cpp) | Reproducible WAVs under the [declared rendering contract](docs/audio-workflow.md); its register snapshots are not a complete write trace. |
| Native SID-Wizard exporter and workflow | Editable instrument/song production and actual driver execution; consult [export limits](docs/research/tools/sid-wizard-trial.md) before extending the compiler. |

Prefer headless operation; computer use is not required for the verified workflows. Use the genuine headless VICE build and file monitor described in setup. GTK startup flags and coloured-log options did not solve the restricted-host display failure. Socket restrictions can prevent bridge access even when file-monitor execution works. Verify the capabilities exposed in the current session rather than assuming a previously discovered MCP tool is connected.

Keep timing definitions explicit: instruction start, post-instruction monitor checkpoint, frame snapshot and SID bus write are different observations. Source-inspected c64bridge operations can resume execution between calls; separate reads need not describe one stopped state. Renderer success does not establish host-speaker playback. Supply usable WAV links and never claim to have heard a sample without actual listening evidence.

## Make listening feedback actionable

Present a small, clearly labelled set of clips with the comparison question and A/B order. Explain whether each file is the original full mix, a muted-voice diagnostic, our independent recreation, or a hybrid retaining original accompaniment. The first half of a diagnostic A/B must not be described as though the composer published a separate isolated recording.

Use the same phrase, model and rendering settings when testing one mechanism. Preserve original-amplitude audio and record gains. For a bass substitution inside otherwise retained accompaniment, use common gain so separate normalization does not change accompaniment levels. Include enough musical context to hear the entrance and release; [the DRAX contextual comparison](songs/studies/drax-bass-reconstruction/README.md#hear-the-reconstruction-in-the-original-accompaniment) is the worked example.

Record the listener's actual verdict with the named clip and its scope. “These sound the same” supports perceptual agreement in that audition, not identical PCM, hardware equivalence or approval of the complete arrangement. Keep separately unreviewed samples unreviewed. When asked to wait for feedback, deliver the samples and stop musical iteration until it arrives.

## Maintain findings and reusable assets

Keep useful learned mechanisms, constraints, rejected approaches, provenance and reproduction instructions. Do not keep a diary of failed commands, session chronology or every measurement. Generated evidence can retain detail without copying it into prose. Consolidate overlapping explanations into one owning study and link it; update or remove stale claims when stronger evidence appears.

| Location | Keep here |
| --- | --- |
| `docs/research/` | Findings and provenance, organized by topic with folder README indexes |
| `songs/` and `songs/studies/` | Retained musical sources, editable instruments/recipes, assembly and bounded study READMEs |
| `scripts/` and `tests/` | Reusable tools and meaningful executable guards |
| Ignored `build/`, `.local/`, `.tools/` | Generated audio/binaries/traces, local state and pinned third-party checkouts |

Prefer searchable HTML, text and source code. For PDF-only material, extract digital text first; use OCR for scans and verify critical notation/tables. Retain URLs, revisions/digests and page or code references as appropriate, and distinguish author statements from local inference. Source availability is not a blanket redistribution permission; keep derived reference binaries in the documented ignored locations.

Use fresh experiment output paths and preserve audition files already sent to the user. Promote a reusable instrument with its [card requirements](docs/research/composition/instrument-card-template.md): editable source, musical purpose, target/player assumptions, behavior, demonstration, limits and listening verdict. A successful narrow recreation is a useful building block, not proof that every register, phrase or mix is suitable.

## Use MEDIUM sub-agents selectively

**Model tiers are symbolic (HIGH, MEDIUM).** Resolve them through the tier table in your global instructions; the maintainer's table is [Model tier mappings](https://github.com/mbackschat/coding-setup/blob/main/CLAUDE.md#model-tier-mappings). Without such a table, run HIGH on your most capable model and MEDIUM on a faster, cheaper one, and say which models you used. Do not duplicate the mappings here or silently substitute an unsupported mapped configuration.

Delegation is authorized for this project. Prefer MEDIUM for delegated work. Optimize for useful progress per cost, including the coordinator's briefing, waiting and review overhead.

- **Delegate bounded work with a clear payoff:** independent source/code investigation, an implementation with isolated file ownership, or review of consequential parser, timing or evidence claims. Parallelize independent tasks that advance the current deliverable.
- **Keep small or tightly dependent work local:** short explanations, routine commands, small documentation edits and changes that require continuous shared context usually cost less to finish directly. Do not spawn an agent merely because a slot is available.
- **Brief once, precisely:** give the question or outcome, relevant paths and evidence, constraints, file ownership and acceptance criteria. Pass the smallest sufficient context. Reuse an existing agent when it already knows the topic; batch related small tasks instead of creating one agent per search or file.
- **Avoid duplicate effort:** consult the research index first, assign different questions/files, share findings, and reuse adequate test results. Repeat checks when changes, failures or unresolved concerns justify them. Independent review should target a material risk, not automatically repeat every investigation.
- **Keep coordination economical:** the primary agent owns scope, integration and final claims. Limit concurrent work to what can be usefully reviewed; stop obsolete branches when the task changes. Escalate beyond MEDIUM only for demonstrated difficulty that the current agent cannot resolve, respecting the global tier mappings.

## Choose validation that answers the question

Use judgment: red/green TDD is a tool, not a required ceremony for every change. Define the intended outcome and the evidence that can establish it before substantial implementation.

- **Reusable software and bug fixes:** prefer red/green tests for parsers, formats, scheduling, conversion, export, provenance, output protection and validation logic. Reproduce a defect and guard its mechanism when practical. Tests should reject meaningful wrong behavior rather than restate the implementation.
- **SID research and reverse engineering:** begin with bounded experiments, actual instruction/register traces, source inspection and independent emulator comparisons. Exploratory probes do not require unit tests first. Add focused tests when turning a probe into a reusable tool, especially for trace interpretation and evidence claims.
- **Music, instrument programs and arrangements:** use reproducible exports, relevant register/timing checks and short listening comparisons. Preserve source material and declare intentional arrangement differences. Do not require test-first development for changing timbre, groove or phrasing; passing software checks does not establish musical quality.
- **Documentation, indexes and routine configuration:** use proportionate checks such as link validation, configuration parsing or a smoke run. Do not add tests solely to satisfy a process rule.

Retain editable inputs, relevant tool/chip settings and reproduction commands. Document reusable findings and bounded listening judgments; keep raw traces in ignored build output rather than writing a diary. State what the evidence does and does not establish. Once relevant checks pass, repeat or broaden them only when changes or unresolved risks justify it.
