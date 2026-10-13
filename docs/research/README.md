# SID Song Crafter research

Research updated: 2026-10-12. The priority is distinctive, expressive SID music: study the masters, understand their tools, develop reusable instruments, and verify the results. Source conversion and correct playback support that goal. This is an evidence-based working library, not a claim of exhaustive knowledge or completed listening tests.

## Active work

Follow the [workbench study plan](study-plan.md): Flashdance, six composer studies, then two 1980s pop songs plus Airwolf and Ghostbusters. The plan owns sequence, completion criteria and remaining musical scope.

## Browse the library

| Area | Contents |
| --- | --- |
| [SID hardware and techniques](sid/README.md) | Chip behaviour, timing, advanced synthesis, export, and two-chip targets |
| [Composition and sound design](composition/README.md) | Arrangement, instrument repertoire, and musical quality criteria |
| [Composers and their methods](composers/README.md) | Hülsbeck, Tel, Hubbard, Galway, Follin, Daglish, and Åkesson; interviews, studies, and tools |
| [Tools and source code](tools/README.md) | Composition-tool assessment, player implementations, and automation |
| [Validation](validation/README.md) | Musical, execution, audio, and hardware evidence |
| [Source register](sources.md) | Shared provenance, evidence types, versions, and rights notes |

## Read by task

Start with the [technique lookup](technique-index.md) to connect a musical need or listening comment to documented methods, reusable patches and assessment tools. Read the linked evidence before selecting a method.

| Task | Guide |
| --- | --- |
| Understand registers and synthesis | [SID hardware](sid/hardware.md) |
| Schedule notes accurately on a C64 | [Playback and timing](sid/playback-and-timing.md) |
| Design instruments and allocate voices | [Instruments and composition](composition/instruments-and-composition.md) |
| Export a runnable song | [Formats and export](sid/formats-and-export.md) |
| Arrange for six voices | [Two SIDs](sid/dual-sid.md) |
| Choose an editor, compiler, or player | [Tools](tools/overview.md) |
| Learn from actual implementation code | [Source studies](tools/source-studies.md) |
| Explain how a master's instrument is programmed | [Executed SID program experiments](tools/sid-program-analysis.md): trace instructions, table data and SID stores, then test the audible consequence |
| Plan Für Elise or Hummelflug | [Classical arrangements](composition/classical-arrangements.md) |
| Find songs and editable examples | [Study corpus and rights](composers/study-corpus.md) |
| Verify a result and identify remaining gaps | [Validation](validation/verification.md) |
| Combine existing agent skills with VICE | [Skills and integrations](tools/skills-and-integrations.md) |
| Build and verify the first opening excerpt | [First song](../first-song.md), [headless audio](../audio-workflow.md) |
| Diagnose emulator startup and headless builds | [VICE investigation](../vice-startup-investigation.md) |
| Trace a statement to its evidence | [Source register](sources.md) |
| Study a composer's sound and working methods | [Composer studies](composers/README.md), [listening catalogue](composers/listening-catalogue.md) |
| Develop an expressive instrument | [Advanced techniques](sid/advanced-techniques.md), [sound-design repertoire](composition/sound-design-repertoire.md) |
| Reinterpret a theme with groove and variation | [Musical gesture library](composition/gestures/README.md) |
| Render and compare native instrument programs | [Original instrument bank](composition/instruments/README.md), [reproducible trials and samples](../instrument-trials.md) |
| Choose a composition system | [Tool assessment](tools/composition-tools.md) |

## Recommended starting path

Use the [technique lookup](technique-index.md) to identify relevant composer evidence and an existing patch for the musical question. Consult the [repertoire](composition/sound-design-repertoire.md) for experiment briefs and acceptance criteria. Compare established editors and their exported drivers in the [tool assessment](tools/composition-tools.md) before expanding the local player. Use the `c64-sid` knowledge skill for hardware semantics and `sid-music` where a working c64bridge connection is appropriate; local verification remains headless.

Keep the editable score or tracker song, exported PRG/SID, target clock/model, compiler/player revision, and verification evidence together. A recording alone cannot reproduce a C64 song. c64bridge's inspected compiler has material limitations; see the [integration assessment](tools/skills-and-integrations.md) before relying on it for complete classical arrangements.

## Evidence and acquisition

Each guide cites stable source IDs in the [register](sources.md). Entries distinguish original documentation, archival transcription, implementation evidence, maintainer claims, and discovery-only leads. Links to moving branches are observations on the access date, not pinned snapshots. The two locally cloned skill repositories have recorded commit IDs.

Prefer searchable HTML, plain text specifications, and source code. For PDF-only studies, extract digital text and retain page references; use OCR only for scanned pages and visually verify critical tables or notation. The composer studies cite published scholarship as well as interviews and code. Source documents may be cached locally for reading; repository notes retain original summaries and provenance rather than mirroring entire publications.

Keep new research in the appropriate subfolder and link it from that folder's README. Mark findings as author statements, published analysis, source inspection, local measurement, or proposed experiment. Promote a proposed sound into the verified repertoire only after its editable source and audio evidence exist.
