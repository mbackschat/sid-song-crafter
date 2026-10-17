# SID Song Crafter Project Guide

This file is the canonical contributor and agent guide; [AGENTS.md](AGENTS.md) is a relative symlink to [CLAUDE.md](CLAUDE.md). Edit this file to update both entry points. Keep it to standing rules and routing: case status belongs in [PLAN.md](PLAN.md), detailed contracts in the linked owning documents. Every agent loads this file in full, so add a rule here only when it must apply before any owning document is read.

## Purpose and scope

[PRODUCTS.md](PRODUCTS.md) defines the musical purpose. SID Song Crafter is a composition and sound-design workbench for the Commodore 64 SID chip, supporting single- and dual-SID music; reusable playback code serves expressive music and an executable repertoire. Prioritize expressive SID interpretations: capture a song's character through phrasing, groove, improvisation and native chip effects. Correct notes and successful playback do not establish musical quality. Preserve source material separately from deliberate arrangement changes.

Treat songs as case studies for learning sound design and building reusable tools and methods. Study composers, published accounts, editors and drivers; preserve findings in [research](docs/research/README.md). Extend the [sound repertoire](docs/research/composition/sound-design-repertoire.md) and [musical gesture library](docs/research/composition/gestures/README.md) with editable examples, useful contexts, limitations and listening evidence.

The current task is creative interpretation of a given, attributed musical score, not original score composition. Keep the source melody, harmony and form as the musical foundation; express creativity through SID instruments, voicing and reduction, articulation, groove, modulation, effects and deliberate single- or dual-SID spatial roles. Retain the source separately and document arrangement departures. Use effects for a musical purpose, not merely to demonstrate every capability. Do not invent a replacement melody or harmonic progression unless the user explicitly requests original composition. Establish the intended mood before selecting instruments; follow the [score-interpretation workflow](docs/workflows/song-workflow.md) and treat prior patch acceptance as context-specific.

## Plan and case status

Read [PLAN.md](PLAN.md) whenever the user asks about the overall plan, what remains or what comes next. It is the sole authority for scope, priorities, active/queued/deferred work and completion; update it when those change. Its [score interpretation cases](PLAN.md#active-score-interpretation-trial), [completion audit](PLAN.md#completion-audit) and [deferred work](PLAN.md#deferred-work-and-unproven-outcomes) link each case's owning study. Owning studies hold evidence and scoped listening verdicts; this guide holds workflow rules. Do not infer overall completion from one case or keep a status summary here.

Preserve every accepted deliverable with its exact verdict scope, including qualified acceptance and recorded reservations. Do not reopen a closed case, resume a parked or deferred experiment, or queue a declined title without a new request.

A verified loop or pleasing excerpt does not complete a whole-song deliverable. A diagnosed failed trial does not complete an active musical request either: record the finding, choose the next bounded design correction and continue to a reviewable sound sample. Preserve the preferred baseline, but do not silently substitute it for an explicitly requested improvement. Pause for the relevant listening verdict, a genuine blocker or a user stop—not merely because the failed trial is documented.

## Finish musical deliverables

Keep one musical case active, in the [plan's delivery order](PLAN.md#delivery-order-and-work-in-progress). Finish its export, ending, listening review and transfer to different musical material before deepening another study. Numeric agreement is preparation; successful reuse in a listening-reviewed phrase from different musical material is the decisive test of the workbench's value. While feedback is pending, finish that case's reproducibility and reuse documentation; spare agent capacity is not a reason to open another investigation. Preserve deferred work.

Keep composer-wide claims provisional until a [second tune](PLAN.md#required-contrasting-references-for-the-six-composers) verifies or narrows them. Use the [reference-intake workflow](docs/workflows/reference-intake.md) for repeatable source checks, explicit subtune selection, bounded execution/rendering and labelled source comparisons. Record callable CPU writes and renderer snapshots as different evidence. Successful intake prepares the study; it does not settle mechanism claims or listening acceptance.

Before additional analysis, name the unresolved question, the deliverable or decision it blocks, and the evidence that will settle it. Once that evidence passes, advance to the next delivery stage. Reopen only for changed inputs, a demonstrated mismatch or an explicit expansion of the supported contract. Follow the [delivery and reuse workflow](docs/workflows/decoded-song-workflow.md#deliver-one-musical-case) without weakening required execution or full-form checks. Use a familiar, source-backed phrase as the default transfer test, with a same-material reference.

## Checkpoints and documentation

Make routine execution and workflow decisions autonomously after checking the recommendation against evidence and project constraints. Ask the user for sound-sample feedback, not routine choices or repeated confirmation of work already authorized. Carry an explicitly authorized bounded model trial through its existing provider, audio selection and spending guards without reconfirming the same upload.

For an authorized musical revision, research, a selected hypothesis and a technical checkpoint are intermediate work. Continue through a verified, reproducible listening comparison before handing back for feedback. If screening rejects a candidate, choose the next supported bounded experiment and continue; do not stop merely to announce a revised plan. Report a genuine blocker when no authorized path remains.

Commit autonomously after a coherent feature set or meaningful verified checkpoint. Batch related implementation, tests and findings into reviewable commits; avoid a commit for every small edit. Never push without authorization.

Keep sample package materials and reproduction recipes under [samples](samples/README.md); link owning scores and reusable tools instead of duplicating them, and preserve each sample's recorded acceptance.

Keep [README.md](README.md) focused on the project: identify the software, explain its rationale, list concrete features, then provide build/run instructions, a worked example and documentation links. Use factual technical prose without slogans, promotional claims or motivational filler. The walkthrough connects a supplied score and musical intent to editable SID choices, with executable commands and playback instructions. Feature the accepted Bach Toccata; the user finds Für Elise too dull for this introduction. Present playable SID/PRG files as the main outputs and WAV files as optional previews. README links must resolve to tracked repository content or public resources, never to ignored local build outputs; show generated filenames as command results and explain how to create and play them. Link to this guide and the workflows for contributor policies instead of repeating them.

Keep guides in task-oriented subfolders under [docs](docs/README.md), with navigation from its README, and research in its existing indexed folders. Use [local setup](docs/setup/local-setup.md) and `python3 scripts/doctor.py` for readiness; read [skill corrections](docs/setup/skill-guidance.md) before applying downloaded instructions. Follow the [tool boundaries](scripts/README.md): source-specific extractors, experiments and fixed examples belong under [scripts/studies](scripts/studies/README.md), separate from supported backends and shared validation APIs. Preserve documented compatibility exceptions and frozen evidence paths; relocation must not rewrite historical provenance.

## Retrieve before researching

Before SID technique explanations, arrangement, sound design or listening-feedback changes, start with the [technique lookup](docs/research/technique-index.md), then read the relevant owning study and reusable example. Search locally before new research. Choose methods by musical purpose and model, timing, voice and filter constraints; check their listening verdict before reuse. Retain useful decisions in the existing study or recipe documentation, and repair missing index routes or aliases.

The established master-composer studies are the primary repertoire and carry the strongest influence on sound and arrangement choices. Study how a master translates a piece into SID—voice-role priorities, entrances, phrasing and timbral/rhythmic contrasts—not only individual patches. Separate executed choices from inferred intention, and do not generalize one tune into a composer-wide rule. Popular-song and BASIC interpretations are supporting, context-specific evidence; they do not displace the masters merely because a patch is convenient or liked once.

For every stereo arrangement, apply the [SID hardware and mixing contract](docs/research/sid/dual-sid.md#plan-the-sound-hardware-and-the-mix-together) before assigning parts: each chip has one mono output, a shared filter and master volume, and no per-voice pan register. Choose positions by musical role first and record role → chip/voice → coupling/filter ownership → output matrix. When expanding a one-SID work to two chips, follow the [resource-informed arrangement principle](docs/research/sid/dual-sid.md#expand-the-musical-capacity-not-only-the-stereo-image); redistribution or extra backing alone does not satisfy that brief.

| Task | References |
| --- | --- |
| Understand the chip | [Hardware](docs/research/sid/hardware.md), [advanced techniques](docs/research/sid/advanced-techniques.md), [timing](docs/research/sid/playback-and-timing.md) |
| Study masters and their tools | [Composers](docs/research/composers/README.md), [commented sources and manuals](docs/research/tools/source-studies.md) |
| Reverse-engineer an instrument | [Execution-based procedure](docs/research/tools/sid-program-analysis.md), [DRAX reconstruction](songs/studies/drax-bass-reconstruction/README.md), [Cybernoid II](docs/research/composition/cybernoid-ii-preparation.md) and its [familiar transfer](docs/research/composition/instruments/cybernoid-decoded-programs.md) |
| Choose expressive material | [Sound repertoire](docs/research/composition/sound-design-repertoire.md), [instruments](docs/research/composition/instruments/README.md), [gestures](docs/research/composition/gestures/README.md) |
| Compose from decoded mechanisms | [Computed-player workflow](docs/workflows/decoded-song-workflow.md), [complete DRAX theme](songs/studies/drax-full-reconstruction/README.md), [Flashdance and dual-SID preparation](docs/research/composition/flashdance-preparation.md), [Shades CIA reconstruction and transfer](docs/research/composition/shades-preparation.md#independent-export-and-original-transfer) |
| Preserve shared PWM and live pitch aliases | [Monty integration](docs/research/composition/monty-preparation.md#independent-editable-score-and-sound-integration), [packed-score compiler](docs/workflows/decoded-song-workflow.md#monty-packed-score-player), [familiar transfer](docs/research/composition/instruments/monty-decoded-programs.md) |
| Reuse Galway tonal programs; distinguish volume-path percussion | [Rambo familiar transfer](docs/research/composition/instruments/rambo-decoded-programs.md), [graph-player contract](docs/workflows/decoded-song-workflow.md#rambo-symbolic-graph-player), [Arkanoid contrast](docs/research/composition/galway-contrast.md) |
| Preserve duration overrides, staged onsets and filter arithmetic | [Ghouls compiled player](docs/research/composition/ghouls-preparation.md#compiled-export-and-complete-listening-package), [familiar pulse/onset transfer](docs/research/composition/instruments/ghouls-decoded-programs.md) |
| Arrange and export | [Source preservation](docs/workflows/song-workflow.md), [native workflow](docs/workflows/native-song-workflow.md), [dual SID](docs/research/sid/dual-sid.md), [editor assessment](docs/research/tools/composition-tools.md) |
| Run and inspect headlessly | [Setup](docs/setup/local-setup.md), [audio](docs/workflows/audio-workflow.md), [callable PSID audit](docs/validation/psid-audit.md), [VICE checks](docs/validation/native-vice-checks.md), [verified capabilities](docs/research/tools/skills-and-integrations.md) |
| Prepare listening comparisons | [Comparison workflow](docs/workflows/audio-comparisons.md), [DRAX reference and feedback](docs/research/composition/fuer-elise-reference.md) |
| Find sources or skills | [Research index](docs/research/README.md), [provenance](docs/research/sources.md), [installed skills](skills/README.md) |
| Download references; restore evidence | [Source URLs and downloads](docs/setup/local-setup.md), [archive verification and cache restoration](docs/workflows/build-cache.md), [canonical evidence index](evidence/README.md) |

## Preserve sources and SID expression

Retain originals, provenance and checksums; disclose conversion losses and deliberate arrangement changes. Common scores are optional. MIDI can describe notes but must not constrain native waveform/pitch tables, envelopes, modulation, filters, timing or voice dependencies. Keep editable recipes/workfiles with exported players and follow the owning workflow's conversion contract; a WAV or register dump alone is insufficient reusable instrument source.

Declare clock, chip model/count, addresses and update cadence. For reference playback, explicitly select the declared source clock; unknown or PAL/NTSC-capable declarations need a recorded experimental choice. Do not force NTSC as an international default. Composition portability means deliberate PAL and NTSC export targets with correct pitch, tempo and effect timing; the [PAL/NTSC portability requirement](PLAN.md#required-palntsc-portability) separates NTSC reference rendering from export support, so never imply an NTSC render option makes a PAL standalone PRG portable. Account for shared filters, ring/sync dependencies, retriggering and modulation during release. Time-sharing percussion and bass on one voice can create additional instrument roles but cannot preserve independent overlapping tails. Choose effects through listening, including recorded rejected approaches.

## Learn mechanisms through execution

Follow the [analysis procedure](docs/research/tools/sid-program-analysis.md): pin tune/profile/passage → execute from initialization → trace ordered SID writes and their executed code/tables → test a causal intervention → independently implement editable behavior → compare in context → transfer to another phrase. Read interviews, manuals and commented sources alongside traces. Distinguish author statements, recovered code and inference. Captured-event replay does not prove an algorithm was understood. Register/code evidence explains programming; audio measurements support alignment, levels, clipping and endings. Remove superseded speculation.

Prefer verified headless VICE and file-monitor workflows. Use bridge tools only when actually connected. Instruction timestamps, checkpoints, frame snapshots and bus writes are different observations; separate bridge reads may resume execution between calls. Rendering does not prove speaker playback or listening.

## Listening and retained findings

Human listening is the authority for musical acceptance. For repeated build/render/comparison work, use the [recipe runner](docs/workflows/listening-package.md) with an owning checked-in recipe; change the recipe or fix the failed stage instead of recreating the pipeline by hand. Package reviews per the [comparison workflow](docs/workflows/audio-comparisons.md#package-a-listening-review): a representative phrase, a separate ending comparison and direct links to both full renders, few labelled clips with actual filenames and A/B order, and one clear question per judgment. Present the reference alongside every generated reconstruction or A/B candidate. Preserve shared audition files and stop iterating when asked to await feedback.

For short or repeated sounds, assess attack, audible body, release and next retrigger in the intended mix, and apply the [short-note ending guidance](docs/research/composition/sound-design-repertoire.md#shape-short-note-endings-in-context) when a sound is called clipped, abrupt, ticking or drum-like. A correct register trajectory or clean gate gap does not establish audible body or a useful added role; use a bounded subtraction comparison when attribution is uncertain, and diagnose before another audition when no difference is heard.

Record each listener verdict with its exact scope, as both a case verdict and any supported reusable lesson; perceptual agreement on one passage does not establish PCM identity, hardware equivalence or approval of another arrangement. Do not promote an unaccepted parameter choice as a general solution.

Model observations and scores are experimental supporting signals: they must not determine musical acceptance or trigger arrangement changes on their own. Record one [standing model-assistance decision](docs/research/audio-assessment.md#use-and-reassess-model-assistance) when a musical case opens; reassess for a concrete useful question, relevant model/prompt/preprocessing change or explicit user request, and check the decision at closure without repeating unchanged skip prose. Before any model listening trial, follow the [measured trials and bounded runners](docs/research/audio-assessment.md), including required controls, frozen criteria, task-specific eligibility and existing upload/spending authorization.

## Reconcile knowledge before handoff

Persist findings as they are established. Before a meaningful checkpoint, commit, handoff, context compaction or session completion, reconcile the conversation, delegated findings, code changes, failed approaches and verification results against the repository's owning documents and reusable tools:

- Record each reusable constraint, supported decision and rejected approach in its existing owner, with evidence, applicable scope and reproduction route. Keep hypotheses, execution results and human listening verdicts distinct; unresolved questions belong in the plan.
- Preserve detail in structured evidence, lookup tables or reusable code when prose would lose it, and add a guard for an executable invariant where meaningful. Promote repeatable probes into supported tools; prose explains and indexes evidence rather than replacing it.
- Link the owner from the relevant technique index or workflow and verify those links, so future agents find the finding before repeating the work.
- Require delegates to identify unpersisted findings in their handback; the coordinator checks integration and records remaining gaps in the plan.

Keep one canonical owner per fact, update stale guidance, and do not duplicate findings into this file or write session diaries. Report only newly retained lessons or material gaps, and do not claim an exhaustive audit of unavailable conversation or evidence.

## Automate routine execution

Whenever routine work involves many tool calls or repeated sub-agent coordination, automate the repeatable sequence with a reusable script, module or recipe before repeating it, with explicit inputs, bounded execution, meaningful checks, retained diagnostics and concrete output paths. Use existing tools first and add the smallest missing orchestration; record the command and its contract in the owning workflow. Agents investigate unknowns, make decisions, review results and resolve failures; they should not remain the manual scheduler for an established procedure.

Run the [automated build cleanup](docs/workflows/build-cache.md#automated-cleanup-and-when-to-run-it) after a substantial rendering/evidence batch, at musical-case closure and before a handoff that leaves substantial build output; follow that section's protection and writer-stop rules and report reclaimed bytes. Promote new canonical evidence only through the [explicit promotion workflow](docs/workflows/build-cache.md) with a reviewed file selection.

## Choose sub-agent tiers by task

**Model tiers are symbolic (HIGH, MEDIUM, LOW).** Resolve only the active CLI's rows through the tier table in your global instructions; the maintainer's table is [Model tier mappings](https://github.com/mbackschat/coding-setup/blob/main/CLAUDE.md#model-tier-mappings). Keep model selectors and effort settings there. Report a missing or unsupported configuration instead of substituting. Start a fresh agent when selecting a different tier so a fork cannot silently retain the parent's model.

Delegation is authorized. Choose the least expensive suitable tier by the task's uncertainty and consequences:

| Tier | Suitable work here | Required boundary and evidence |
| --- | --- | --- |
| LOW | Check links and path references in named files; extract specified facts from existing receipts; summarize an existing verifier's result; apply an exact documentation correction; check a small documentation diff against explicit repository rules. | Supply the files, authoritative facts and pass/fail criteria. Use existing checkers for hashes and schemas. Return precise paths/lines and discrepancies; do not infer musical acceptance, select evidence for publication, change frozen provenance or repair an unfamiliar failure. |
| MEDIUM | Implement an isolated player/compiler component; write meaningful regression tests; build a recipe with its dependency declarations; investigate a bounded source mechanism; compare a second reference against stated hypotheses; review implementation correctness. | Define the supported contract, file ownership and independent oracle. Preserve CPU, VICE, rendered and listening evidence as separate claims. Bring unresolved cross-component assumptions to the coordinator. |
| HIGH | Resolve architecture or supported-contract tradeoffs; diagnose persistent model/CPU/VICE disagreements spanning components; review whether a verification design actually proves the intended musical/execution scope; integrate conflicting findings and audit completion. | State the consequential unresolved question and the evidence that will settle it. Use bounded delegates for separable work; keep integration and final claims with the coordinator. Human listening remains the authority for musical acceptance. |

Keep small or tightly dependent work local, and do not duplicate work merely to use another tier. Tie every assignment to the active deliverable with minimal sufficient context, file ownership, acceptance criteria and a stopping condition. Reuse informed agents when their tier still fits. Hand a LOW task that needs causal inference or a substantive code change to MEDIUM; escalate MEDIUM to HIGH for demonstrated cross-component difficulty. Stop obsolete work.

## Choose validation that answers the question

This project permits judgment instead of mandatory red/green TDD everywhere. Define success and its oracle before implementation.

- **Reusable software/bugs:** prefer red/green guards covering meaningful behavior and the defect's mechanism.
- **Research:** use bounded experiments, instruction/register traces and independent execution; add focused tests when probes become tools.
- **Music:** verify exports/timing and listen in context; software checks cannot establish musical quality.
- **Documentation/configuration:** check links, parsing or a relevant smoke run; avoid artificial tests.

Distinguish proposed, implemented, rendered and listening-reviewed work, and label excerpts accurately. Repeat passed checks only when changes, failures or unresolved risks justify it. Stock SID-Wizard Extra at tempo 1 initializes only the frequency high byte on a new note's first frame; see [the reproduced constraint and policy](docs/songs/fuer-elise-native.md) before writing one-frame graces.

## Project Structure & Module Organization

Keep all project files and archives inside the project folder unless the user explicitly instructs otherwise. Use ignored `.local/archives/` for local retention. Do not create, move or use project material at an external location without that instruction; historical external locations do not establish permission.

Navigate operational guides through [docs/README.md](docs/README.md). Research and provenance live in [docs/research](docs/research/README.md), scores/native instruments in `songs/`, tools in `scripts/`, tests in `tests/`, and installed skill sources in [skills](skills/README.md). Working binaries, audio and traces go in ignored `build/`; sample packages, their recipes and material indexes live in [samples](samples/README.md); uncleared generated music stays local. Promote canonical analysis records to [evidence](evidence/README.md), with compressed records in Git LFS and readable hash manifests in ordinary Git.

Keep third-party checkouts in ignored `.tools/`, runtime state in `.local/`, and machine-local agent configuration in ignored `.codex/config.toml` and `.mcp.json`; track portable examples in `config/`. Skills activate through `.agents/skills/` (Codex) and the `.claude/skills` link to it (Claude Code); see [local setup](docs/setup/local-setup.md#unified-local-setup).

## Build, Test, and Development Commands

From the repository root, install pinned assets with `python3 scripts/setup-project.py` and check readiness with `python3 scripts/doctor.py`. After dependency setup in [README.md](README.md):

- `bun scripts/build-song.ts`: assemble the opening excerpt and export PRG, PSID, and event manifest.
- `python3 scripts/song.py songs/fuer-elise.json`: build, render, and verify the full arrangement in headless VICE; see [the reusable workflow](docs/workflows/song-workflow.md).
- `python3 scripts/setup-sidwizard.py`, then `python3 scripts/run-instrument-trials.py --output build/instrument-trials`: prepare native Extra exports and [A/B trials](docs/workflows/instrument-trials.md). Use a fresh output directory.
- `python3 scripts/native-song.py build songs/fuer-elise-sidwizard.json --output build/fuer-elise-native`: build and audit the [native sound-design candidate](docs/workflows/native-song-workflow.md); [VICE checkpoints](docs/validation/native-vice-checks.md) independently check its standalone PRG.
- `bun test tests/music.test.ts tests/fuer-elise.test.ts`: check timing, binaries, and deterministic builds.
- `PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 -m unittest discover -s tests -p '*_test.py' -v`: run importer, CPU, audio, and workflow tests.

Use c64bridge's pinned Bun lockfile. Native integration tests require SID-Wizard setup. Renderer setup is in [the audio guide](docs/workflows/audio-workflow.md).

## Coding Style & Naming Conventions

Use two-space TypeScript, four-space Python/C++, descriptive assembly labels, and `test_*` Python methods. No formatter is configured. Comments explain constraints. Keep Markdown paragraphs on single lines, link related documents, and organize research with folder READMEs.

## VICE Findings & Troubleshooting

Use the genuine headless VICE build and the file-based monitor for reproducible agent execution. GTK OpenGL failures and denied monitor-socket binding were observed in the restricted Codex runner and do not hold in every launch context; see [the VICE investigation](docs/setup/vice-startup-investigation.md#runtime-checks-and-limitations). c64bridge's dummy audio can produce empty recordings; capture directly to WAV without warp. Select the default SID subtune before libsidplayfp playback, because an unselected tune passes `$ff` to init ([audio guide](docs/workflows/audio-workflow.md)). Record new reusable constraints and reproduction commands in [local setup](docs/setup/local-setup.md), the VICE investigation or the audio guide, with raw diagnostics in ignored output.

## Public Repository Boundary

Original project work is [MIT](LICENSE)-licensed; preserve the separate terms in [third-party notices](THIRD_PARTY_NOTICES.md). The [publication boundary](docs/workflows/publication-boundary.md) owns the full policy. Standing rules:

- Every worked-on sample gets a public package of our tools, reusable instruments, note-free recipes, source references and hashes. Complete scores, SWM/SWS modules and SID/PRG/WAV files are published only when the composition, source arrangement and player code all permit it; unknown rights keep them local.
- Record the rights basis and inspect for embedded or encoded score data before staging. Public URLs, attribution, hashes and deterministic builds do not establish permission.
- Keep original reference SID binaries out of Git, history and LFS, and reference WAVs under ignored `.local/` or `build/`; register source URLs and SHA-256 in [the asset registry](config/local-assets.json). Never force-add original SID files.

## Commit & Pull Request Guidelines

Use Conventional Commits with an imperative subject; add a short body for non-obvious rationale. PRs describe behavior and verification. Respect `.gitignore`, retain dependency pins, and never create or switch worktrees without explicit instructions.
