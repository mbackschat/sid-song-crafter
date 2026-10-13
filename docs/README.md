# Documentation

Use the [project overview](../README.md) for SID Song Crafter's purpose and current scope. Choose a guide by the task below; the linked documents own their contracts, evidence and limitations.

## Set up local tools

- [Skill corrections](setup/skill-guidance.md): hardware semantics and bridge limitations to apply alongside downloaded instructions.
- [Local setup](setup/local-setup.md): dependency pins, skill activation and c64bridge configuration.
- [Build and troubleshoot headless VICE](setup/vice-startup-investigation.md): verified startup constraints, build commands and workarounds.
- [Manage generated evidence](workflows/build-cache.md): lossless compression, exact restoration and retention of accepted audio.

## Compose and listen

- [Compose from decoded instruments](workflows/decoded-song-workflow.md): editable musical descriptions, computed players and reconstruction evidence.
- [Arrange preserved source music](workflows/song-workflow.md): source provenance, conversion boundaries and baseline builds.
- [Build a native SID-Wizard song](workflows/native-song-workflow.md): editable three- or six-voice arrangements, export, audit and rendering.
- [Try native instruments](workflows/instrument-trials.md): reproducible sound-design phrases and A/B trials.
- [Render and inspect audio](workflows/audio-workflow.md): SID-to-WAV setup, timing, pitch and ending checks.
- [Prepare listening comparisons](workflows/audio-comparisons.md): original-preserving excerpts, level matching and recorded evidence.

## Verify execution

- [Audit a callable PSID](validation/psid-audit.md): independent CPU execution and ordered register writes.
- [Trace CIA-driven playback](validation/cia-tracing.md): real timer IRQs, latch changes, host assumptions and callable source observation.
- [Check CPU instruction costs](validation/cpu-timing.md): verified opcode timings, the shared CPU adapter and corrections to retained evidence.
- [Check a native standalone player in VICE](validation/native-vice-checks.md): register checkpoints and PAL cadence.
- [Inspect complete Für Elise validation](validation/fuer-elise-validation.md): baseline binaries, rendered audio and standalone execution evidence.

## Understand the player

- [Three-voice baseline architecture](architecture/three-voice-player.md): arrangement contract, supported capabilities, timing and binary exports.

## Read the song studies

- [First-song opening](songs/first-song.md): editable score, assembler and independent CPU verification.
- [Complete Für Elise source and reduction](songs/fuer-elise-score.md): preserved source, repeats, landmarks and voice selection.
- [Native Für Elise interpretation](songs/fuer-elise-native.md): instrument choices, articulation changes and listening boundaries.

## Research and choose the next study

- [Technique lookup](research/technique-index.md): find an existing method by musical purpose and its recorded verdict.
- [Study plan](research/study-plan.md): active work, signature composer candidates and later song priorities.
- [Research library](research/README.md): hardware, composition, composers, tools and source provenance.
