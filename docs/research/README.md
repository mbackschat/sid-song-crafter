# C64 SID research

Research baseline: 2026-10-12. The project aims to turn scores into playable Commodore 64 music for one SID, with a deliberate path to two SIDs. This library connects hardware behaviour, composition, player implementation, export formats, and reproducible verification. It is a researched starting point, not an exhaustive archive or a claim that every listed tool has been run.

## Read by task

| Task | Guide |
| --- | --- |
| Understand registers and synthesis | [SID hardware](01-sid-hardware.md) |
| Schedule notes accurately on a C64 | [Playback and timing](02-playback-and-timing.md) |
| Design instruments and allocate voices | [Instruments and composition](03-instruments-and-composition.md) |
| Export a runnable song | [Formats and export](04-formats-and-export.md) |
| Arrange for six voices | [Two SIDs](05-dual-sid.md) |
| Choose an editor, compiler, or player | [Tools](06-tools.md) |
| Learn from actual implementation code | [Source studies](07-source-studies.md) |
| Plan Für Elise or Hummelflug | [Classical arrangements](08-classical-arrangements.md) |
| Find songs and editable examples | [Study corpus and rights](09-study-corpus.md) |
| Verify a result and identify remaining gaps | [Validation](10-validation.md) |
| Combine existing agent skills with VICE | [Skills and integrations](11-skills-and-integrations.md) |
| Build and verify the first opening excerpt | [First song](../first-song.md), [headless audio](../audio-workflow.md) |
| Diagnose emulator startup and headless builds | [VICE investigation](../vice-startup-investigation.md) |
| Trace a statement to its evidence | [Source register](sources.md) |

## Recommended starting path

Use the `c64-sid` knowledge skill together with c64bridge's `sid-music` execution skill for guided experiments. For a complete, editable native tune, use GoatTracker; use its stereo variant when the arrangement genuinely needs a second chip. Study MiniPlayer2 to understand the runtime and tradeoffs before writing a new player. These are project recommendations, not claims that the tools are interchangeable.

Keep the editable score or tracker song, exported PRG/SID, target clock/model, compiler/player revision, and verification evidence together. A recording alone cannot reproduce a C64 song. c64bridge's inspected compiler has material limitations; see the [integration assessment](11-skills-and-integrations.md) before relying on it for complete classical arrangements.

## Evidence and acquisition

Each guide cites stable source IDs in the [register](sources.md). Entries distinguish original documentation, archival transcription, implementation evidence, maintainer claims, and discovery-only leads. Links to moving branches are observations on the access date, not pinned snapshots. The two locally cloned skill repositories have recorded commit IDs.

Prefer searchable HTML, plain text specifications, and source code. For PDF-only material, extract digital text to Markdown first; use OCR only for scanned pages, retain page references, and visually verify register tables, hexadecimal digits, accidentals, and timing diagrams. The available `pdf-to-markdown` skill supports this workflow. Do not mistake OCR text for corrected technical documentation. No PDF corpus was downloaded or converted during this research.
