# SID Song Crafter study plan

## Product and outcome

**SID Song Crafter — a composition and sound-design workbench for the Commodore 64 SID chip, supporting single- and dual-SID music.** Turn musical ideas and existing songs into expressive single- and dual-SID arrangements. Its value is making the **next great-sounding song easier to create** through a growing, executable repertoire. The playback engine is one component alongside source preservation, SID-native authoring, program analysis, musical knowledge and listening comparisons.

Each study must leave reusable instruments, effects or arrangement methods, with evidence connecting **musical intention → editable description → SID programming** and back. Follow the [analysis procedure](tools/sid-program-analysis.md), [composition workflow](../workflows/decoded-song-workflow.md) and [technique index](technique-index.md). This plan owns priorities and completion state; owning studies retain findings and provenance.

## Scope and order

**Active: Flashdance.** Then study one signature tune from each of the six historical composers already researched. Follow those with **two additional 1980s pop songs, Airwolf and Ghostbusters**, as confirmed by the user. DRAX is our existing baseline; [Åkesson](composers/linus-akesson.md) remains a supplementary reference.

These are recognizable signature candidates, not an asserted “number one” ranking: no comparable popularity chart was verified. Choose the final archive variant and musical subtune at intake. Questions below are investigation targets, not claims that their mechanisms have already been decoded.

| Order / ID | Study and proposed reference | Learning target | State |
| --- | --- | --- | --- |
| 1 / F | [Flashdance: What a Feeling — DRAX](composition/flashdance-preparation.md), #1 | Staged waveform/PWM programs, evolving filtered bass, precise articulation; full arrangement and deliberate dual-SID expansion | Active: reconstruction and transfer reviewed; revised dual listening pending |
| 2 / M1 | [Shades — Chris Hülsbeck](composers/huelsbeck-tel.md), #1 | Soundmonitor's instrument model; expressive modulation and original/corrected filter intent | Queued |
| 3 / M2 | [Cybernoid II — Jeroen Tel](composers/huelsbeck-tel.md), title #1 | Groove, bass/drum time-sharing, delayed modulation; music/driver collaboration with Charles Deenen | Queued |
| 4 / M3 | [Monty on the Run — Rob Hubbard](composers/hubbard-galway.md), #1 | Articulated lead, percussion substitutions, pitch effects and phrase development | Queued |
| 5 / M4 | [Rambo: First Blood Part II — Martin Galway](composers/hubbard-galway.md), loader #1 | Sustained timbre evolution, introductory effects and original source-code hooks | Queued |
| 6 / M5 | [Ghouls ’n Ghosts — Tim Follin](composers/follin-daglish.md), provisional #1 | Contrasting sections, changing orchestration and instrument transformations | Queued; musical subtune label needs audition |
| 7 / M6 | [Deflektor — Ben Daglish](composers/follin-daglish.md), #1 | Cowbell-driven rhythmic identity and independent supporting parts | Queued |
| 8 / P1 | Take On Me — a-ha; PVL SID candidate | Fast recognizable hook, agile lead, accompaniment and section coverage | Queued |
| 9 / P2 | Billie Jean — Michael Jackson; Johannes Bjerregaard SID candidate | Bass/drum groove, articulation and a restrained but animated arrangement | Queued |
| 10 / T1 | Airwolf — Sylvester Levay; Mark Cooksey C64 arrangement | Repeating synth figures, sustained layers and tension; this is a TV theme | Queued |
| 11 / T2 | Ghostbusters — Ray Parker Jr.; Russell Lieblich C64 arrangement, #1 | Bass/hook interaction, voice allocation, speech integration and full-machine timing | Queued |

The six composer rows have archive and published-account routes in the [listening catalogue](composers/listening-catalogue.md). *Shades* is selected for its documented breakthrough and editor connection; *The Great Giana Sisters* is the alternate if intake favors a more familiar game theme. Preserve collaborators and source-composition credits at subtune level.

## Flashdance: next executable milestones

- [x] **F1 — Pin musical scope.** The [selected form and ending contract](composition/flashdance-preparation.md#selected-form-and-ending-contract) pins calls 0–1537: startup, a four-bar opening variation and the first eight-bar Verse 1 span, with source omissions and arrangement differences documented. F4 verifies the declared release/fade. The deliverable remains the selected DRAX arrangement.
- [x] **F2 — Describe one complete opening phrase.** The [portable diagnostic tracer](tools/sid-program-analysis.md#trace-the-pinned-flashdance-opening) reproduces all 9,345 initialization/opening sound writes for calls 0–513. The [editable score and waveform/pitch/PWM/filter programs](composition/flashdance-preparation.md#editable-full-span-model) cover the opening and the entire selected cycle; the independent Python scheduler matches all 27,905 initialization/full-span writes. Runtime controls are separate from source annotations. The deferred local form-analysis script, its tests and study README remain untouched and unstaged; portable tracing uses the existing tracked tracer instead.
- [x] **F3 — Independently reconstruct and audition.** The [independent export](composition/flashdance-preparation.md#independent-export-and-listening) matches every selected reference sound-register write and passes headless VICE. The listener accepted the sound and phrasing on 2026-10-13: “yes, quite good.”
- [x] **F4 — Cover the declared full form.** Editable source, independent SID and comparison audio cover every selected block through call 1537. The authored release/fade passes execution and settled-tail checks, and the same listening response accepts its ending. The deliverable remains explicitly the abbreviated DRAX arrangement.
- [ ] **F5 — Compose dual SID (awaiting revised listening).** The [authored secondary parts and independent export](composition/flashdance-preparation.md#deliberate-dual-sid-interpretation) pass full CPU/VICE and stereo/mono health checks. After “I don't hear a difference” on the first mix, the revision raises the added parts' level and extends their articulation. The revised comparison, full mix and second-chip-only diagnostic are delivered; balance and musical preference remain pending.
- [x] **F6 — Prove reuse.** The [instrument card](composition/instruments/flashdance-decoded-programs.md) documents supported parameters and links the [original C-major transfer phrase](../../songs/flashdance-transfer.json), which changes notes, rhythm and legato while reusing the computed programs. CPU, full VICE and settled-audio checks pass. The listener says it “Works,” while noting it does not resemble Flashdance; the separate original phrase intentionally tests reuse, not recognition.

The [Flashdance owning study](composition/flashdance-preparation.md) records the concrete backend gaps. Its same-call restart and changing waveform/PWM programs differ from Elise; do not squeeze them into Elise's fixed preparation schedule.

## Completion contract for every study

1. **Identify and map.** Pin archive URL, bytes/hash, subtune, credits, chip/clock, cadence and complete musical form. Check interviews, manuals and original/commented sources alongside the binary; identify the composer's editor and driver where evidence permits.
2. **Explain mechanisms.** Connect executed instructions, state and ordered SID writes to instruments, effects and musical roles. Preserve initialization, release evolution, shared filters, oscillator dependencies and meaningful within-frame timing. Use a targeted intervention to test a causal explanation.
3. **Reproduce independently.** Generate the sound through our own code from editable musical/effect descriptions. Original driver reuse and captured-register replay do not satisfy this stage. Retain the original as a comparison oracle.
4. **Verify and listen.** Prove the supported execution contract, then compare the characteristic phrase in context and the complete selected form, including its ending. Record residual timing/model differences and listening feedback separately. A pleasing excerpt cannot close the complete-song task.
5. **Transfer and retain.** Apply each promoted mechanism to a new phrase or arrangement, with named parameters, constraints and an executable example. Update the owning library card and index; retain useful findings, not work diaries.

Mark a case **done** only when all five stages have linked evidence and its declared musical deliverable has been reviewed. Track stages as `queued`, `active`, `awaiting listening`, or `done`; a new artifact or rendered WAV alone does not advance the verdict.

## Reference acquisition and feasibility

| Later study | Archive candidate / evidence route | Pinning still required |
| --- | --- | --- |
| Take On Me | [PVL SID](https://www.hvsc.de/download/C64Music/MUSICIANS/P/PVL/Take_on_Me.sid); [release listing](https://csdb.dk/release/?id=3031) | Hash, header, subtune, quality and form |
| Billie Jean | [Bjerregaard SID](https://www.hvsc.de/download/C64Music/MUSICIANS/B/Bjerregaard_Johannes/Billie_Jean.sid); [HVSC STIL](https://www.hvsc.de/download/C64Music/DOCUMENTS/STIL.txt) identifies the original song | Hash, header, subtune, quality and form |
| Airwolf | [Cooksey SID](https://www.hvsc.de/download/C64Music/MUSICIANS/C/Cooksey_Mark/Airwolf.sid); [composer interview](https://remix64.com/interviews/interview-mark-cooksey.html) | Hash, header, musical subtune and form |
| Ghostbusters | [Lieblich SID](https://www.hvsc.de/download/C64Music/MUSICIANS/L/Lieblich_Russell/Ghostbusters.sid); [archive profile](https://csdb.dk/sid/?id=17398) | Hash and executable confirmation of archived NTSC/6581, default #1 of 5 and zero play address |

Cached HVSC STIL v85 confirms the pop/theme identities; the [Flashdance reference record](composition/flashdance-reference.md) owns that cache's checksum. Listed candidates are not all locally downloaded or auditioned. Fresh binary acquisition remains an intake task. *Ghostbusters* needs the full-machine path, not an assumed callable PAL routine; distinguish its Electronic Speech Systems speech from oscillator instruments. CIA/RSID, multispeed or sample techniques must receive suitable tracing support before making fidelity claims.

## Working rules and retained gap

Keep one reconstruction active. Use MEDIUM agents for bounded source research, independent mechanism analysis or review; the coordinator integrates musical choices and claims. Reuse existing tools and engines, extending them only for demonstrated requirements. Commit coherent milestones, keep large traces/audio in ignored output directories and link portable recipes/findings from the existing research folders. This is a milestone sequence, not an unsupported calendar estimate.

Für Elise remains a useful mechanism proof: [our reconstruction](../../songs/studies/drax-full-reconstruction/README.md) covers DRAX's roughly 40-second recurring theme. The listener finds it nice so far but unfinished. **A completed full Beethoven interpretation remains deferred while Flashdance takes priority**; the loop study must not be presented as satisfying that deliverable.
