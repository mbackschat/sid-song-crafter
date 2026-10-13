# SID Song Crafter study plan

## Product and outcome

**SID Song Crafter — a composition and sound-design workbench for the Commodore 64 SID chip, supporting single- and dual-SID music.** Turn musical ideas and existing songs into expressive single- and dual-SID arrangements. Its value is making the **next great-sounding song easier to create** through a growing, executable repertoire. The playback engine is one component alongside source preservation, SID-native authoring, program analysis, musical knowledge and listening comparisons.

Each study must leave reusable instruments, effects or arrangement methods, with evidence connecting **musical intention → editable description → SID programming** and back. Follow the [analysis procedure](tools/sid-program-analysis.md), [composition workflow](../workflows/decoded-song-workflow.md) and [technique index](technique-index.md). This plan owns priorities and completion state; owning studies retain findings and provenance.

## Scope and order

**Active: Monty on the Run.** Cybernoid II is complete through its accepted title, authored ending and familiar-material transfer. Shades is complete through its accepted familiar-material transfer; Flashdance is complete for its declared DRAX arrangement, accepted dual-SID expansion and original transfer phrase. Continue with one signature tune from each of the six historical composers already researched. Follow those with **two additional 1980s pop songs, Airwolf and Ghostbusters**, as confirmed by the user. DRAX is our existing baseline; [Åkesson](composers/linus-akesson.md) remains a supplementary reference.

These are recognizable signature candidates, not an asserted “number one” ranking: no comparable popularity chart was verified. Choose the final archive variant and musical subtune at intake. Questions below are investigation targets, not claims that their mechanisms have already been decoded.

| Order / ID | Study and proposed reference | Learning target | State |
| --- | --- | --- | --- |
| 1 / F | [Flashdance: What a Feeling — DRAX](composition/flashdance-preparation.md), #1 | Staged waveform/PWM programs, evolving filtered bass, precise articulation; full arrangement and deliberate dual-SID expansion | Done: reconstruction, raw stereo dual arrangement and original transfer reviewed |
| 2 / M1 | [Shades — Chris Hülsbeck](composition/shades-preparation.md), #1 | Soundmonitor's instrument model; expressive modulation and original/corrected filter intent | Done: reconstruction/fade and familiar Für Elise transfer/ending accepted; rejected invented ending retained as a limitation |
| 3 / M2 | [Cybernoid II — Jeroen Tel](composition/cybernoid-ii-preparation.md), title #1 | Groove, bass/drum time-sharing, delayed modulation; music/driver collaboration with Charles Deenen | Done: full independent first title cycle, added release/fade and familiar 53-note transfer accepted; full CPU/VICE/audio evidence retained |
| 4 / M3 | [Monty on the Run — Rob Hubbard](composition/monty-preparation.md), #1 | Articulated lead, percussion substitutions, pitch effects and phrase development | Opening and familiar 53-note transfer accepted; corrected reference continuation awaiting listening; finite fade retained as an optional arrangement |
| 5 / M4 | [Rambo: First Blood Part II — Martin Galway](composition/rambo-preparation.md), loader #1 | Sustained timbre evolution, introductory effects and original source-code hooks | Preparation: finite loader and CPU/VICE final stores verified; independent lifetime/PWM/sequential-pitch component matches ending contexts; remaining mechanisms and reconstruction pending |
| 6 / M5 | [Ghouls ’n Ghosts — Tim Follin](composition/ghouls-preparation.md), provisional #1 | Contrasting sections, changing orchestration and instrument transformations | Preparation: finite streams end at call 12,995; CPU/VICE agree across terminal commands and continuing filter writes; #1 label, sound mechanisms and independent player remain |
| 7 / M6 | [Deflektor — Ben Daglish](composition/deflektor-preparation.md), #1 | Cowbell-driven rhythmic identity and independent supporting parts | Preparation: editable numeric player matches all 166,845 selected stores and stop behavior; compiled export, musical attribution, rendering and transfer remain |
| 8 / P1 | [Take On Me — a-ha; PVL SID](composition/pop-theme-preparation.md#take-on-me), #1 | Fast recognizable hook, agile lead, accompaniment and section coverage | Preparation: unknown header model preserved; explicit 6581/8580 CPU/VICE experiments pass 64 calls; full form and audible model choice remain |
| 9 / P2 | [Billie Jean — Michael Jackson; Johannes Bjerregaard SID](composition/billie-jean-preparation.md), #1 | Bass/drum groove, articulation and a restrained but animated arrangement | Preparation: independent score expansion matches two full cycles; CPU/VICE agree at wrap; sound mechanisms and independent player remain |
| 10 / T1 | [Airwolf — Sylvester Levay; Mark Cooksey C64 arrangement](composition/pop-theme-preparation.md#airwolf-score-cycle-and-independent-numeric-model), #1 | Repeating synth figures, sustained layers and tension; this is a TV theme | Preparation: full numeric score/store model matches two cycles; CPU/VICE agree at restart; independent export, authored ending and listening remain |
| 11 / T2 | [Ghostbusters — Ray Parker Jr.; Russell Lieblich C64 arrangement](composition/pop-theme-preparation.md#ghostbusters), #1 | Bass/hook interaction, voice allocation, speech integration and full-machine timing | Preparation: source pinned as NTSC/6581 RSID; full-machine execution remains |

The six composer rows have archive and published-account routes in the [listening catalogue](composers/listening-catalogue.md). *Shades* is selected for its documented breakthrough and editor connection; *The Great Giana Sisters* is the alternate if intake favors a more familiar game theme. Preserve collaborators and source-composition credits at subtune level.

## Delivery order and work in progress

Prioritize accepted musical deliverables over the number of decoded drivers. As of 2026-10-13, Flashdance, Shades and Cybernoid II are complete for their declared scopes; Monty on the Run is next, and eight cases retain preparation evidence. This establishes technical progress and some musical success; it does not yet establish a measured reduction in composition effort.

1. **Shades closed.** The familiar [Für Elise transfer and ending](composition/instruments/shades-decoded-programs.md#familiar-transfer-accepted) are accepted. Preserve the earlier invented fragment, whose instrument sound was accepted but ending rejected. Use familiar source-backed material by default to avoid conflating instrument reuse with new composition quality.
2. **Cybernoid II closed.** The listener accepted the title opening and authored ending (“both are really good, I can not spot any difference to original”) and separately the familiar transfer (“Cybernoid version works musically”). Preserve the [actual comparison scope](composition/cybernoid-ii-preparation.md#listening-package-and-reproduction), native conversion limits and reproducible evidence.
3. **Finish Monty's listening review, then the remaining cases in table order.** The [complete listening package](composition/monty-preparation.md#listening-package-and-reproduction) supplies original-first title/ending comparisons and a familiar plain-first transfer. Preserve the existing untracked Monty player/program files and tests untouched and unstaged; supported integration uses separate `monty_title_*` paths. Numeric composition, first-cycle independent export, optional finite ending and transfer checks are complete. Opening and familiar transfer are accepted; review the corrected ending WAV that preserves the original's sound after restart. The finite fade is a separate arrangement and its acceptance is no longer a completion requirement. Extra analysis must resolve a named gap in that delivery.

Keep one musical case active. Pending listener feedback permits completing that case's packaging, reproduction instructions and reusable examples, but does not authorize deepening later studies to keep agents busy. When those independent tasks are finished, wait for the verdict. This order governs resumed study work; a documentation update does not itself resume a paused run.

Use the [delivery workflow](../workflows/decoded-song-workflow.md#deliver-one-musical-case) and [listening package](../workflows/audio-comparisons.md#package-a-listening-review). Keep a compact [reuse outcome](../workflows/decoded-song-workflow.md#record-reuse-and-effort) in each owning study or instrument card: actual reused components, new work, listening revisions and observed effort. Historical effort was not measured; do not infer savings from trace counts or successful tests.

## Flashdance: completed milestones

- [x] **F1 — Pin musical scope.** The [selected form and ending contract](composition/flashdance-preparation.md#selected-form-and-ending-contract) pins calls 0–1537: startup, a four-bar opening variation and the first eight-bar Verse 1 span, with source omissions and arrangement differences documented. F4 verifies the declared release/fade. The deliverable remains the selected DRAX arrangement.
- [x] **F2 — Describe one complete opening phrase.** The [portable diagnostic tracer](tools/sid-program-analysis.md#trace-the-pinned-flashdance-opening) reproduces all 9,345 initialization/opening sound writes for calls 0–513. The [editable score and waveform/pitch/PWM/filter programs](composition/flashdance-preparation.md#editable-full-span-model) cover the opening and the entire selected cycle; the independent Python scheduler matches all 27,905 initialization/full-span writes. Runtime controls are separate from source annotations. The deferred local form-analysis script, its tests and study README remain untouched and unstaged; portable tracing uses the existing tracked tracer instead.
- [x] **F3 — Independently reconstruct and audition.** The [independent export](composition/flashdance-preparation.md#independent-export-and-listening) matches every selected reference sound-register write and passes headless VICE. The listener accepted the sound and phrasing on 2026-10-13: “yes, quite good.”
- [x] **F4 — Cover the declared full form.** Editable source, independent SID and comparison audio cover every selected block through call 1537. The authored release/fade passes execution and settled-tail checks, and the same listening response accepts its ending. The deliverable remains explicitly the abbreviated DRAX arrangement.
- [x] **F5 — Compose dual SID.** The [authored secondary parts and independent export](composition/flashdance-preparation.md#deliberate-dual-sid-interpretation) pass full CPU/VICE and stereo/mono health checks. Following audibility and cohesion revisions, the listener calls the full raw stereo arrangement “really good” and its stereo “convincing”. That A-left/B-right presentation is accepted; no separate preference is inferred for crossfed or mono alternatives.
- [x] **F6 — Prove reuse.** The [instrument card](composition/instruments/flashdance-decoded-programs.md) documents supported parameters and links the [original C-major transfer phrase](../../songs/flashdance-transfer.json), which changes notes, rhythm and legato while reusing the computed programs. CPU, full VICE and settled-audio checks pass. The listener says it “Works,” while noting it does not resemble Flashdance; the separate original phrase intentionally tests reuse, not recognition.

The [Flashdance owning study](composition/flashdance-preparation.md) records the concrete backend gaps. Its same-call restart and changing waveform/PWM programs differ from Elise; do not squeeze them into Elise's fixed preparation schedule.

## Shades: completed milestones

The [owning study](composition/shades-preparation.md) retains the complete first traversal, decoded mechanisms and opening pulse experiment. The [reference intake](composers/huelsbeck-tel.md#shades-reference-intake) owns variant provenance.

| Stage | State | Evidence / next action |
| --- | --- | --- |
| 1: Identify and map | Done | Calls 0–24,384, source fade and actual restart mapped; full real CIA dispatch verified |
| 2: Explain mechanisms | Done | Editable programs, 122,048 source-state transitions and causal PWM intervention; listener finds moving pulse quieter and more vibrant |
| 3: Reproduce independently | Done | Our compiled score/program player matches all 296,907 source stores, adds four finite-stop stores and passes full CIA-timed VICE execution |
| 4: Verify and listen | Done | Full 310-second reconstruction's sound/phrasing and fade ending accepted on 2026-10-13; exact verdict in the owning study |
| 5: Transfer and retain | Done | [Familiar-transfer card](composition/instruments/shades-decoded-programs.md#familiar-transfer-accepted): all 53 preserved Für Elise events, full CPU/CIA/audio proof and matched reference; listener accepts musical use and ending |

The [independent export section](composition/shades-preparation.md#independent-export-and-original-transfer) links receipts, local audio, exact reproduction recipes and accepted reconstruction feedback. The invented transfer has accepted instruments and a rejected ending; the familiar Für Elise replacement has its own accepted musical and ending verdict. All five stages are complete for the declared Shades scope.

## Cybernoid II: completed milestones

| Stage | State | Evidence / next action |
| --- | --- | --- |
| 1: Identify and map | Done | Pinned title #1, credits, PAL/6581, two observed order traversals and first-cycle boundary at call 17,280 |
| 2: Explain mechanisms | Done | Independent semantic score and sound programs match 645,960 original stores over 36,000 calls |
| 3: Reproduce independently | Done | Compiled first cycle matches all 310,586 original init/music stores; explicit 128-call release/fade, full CPU/VICE and post-stop checks |
| 4: Verify and listen | Done | [Full-title and ending package](composition/cybernoid-ii-preparation.md#listening-package-and-reproduction), with original reference; listener accepts both on 2026-10-13 and reports no perceptible difference |
| 5: Transfer and retain | Done | [Familiar 53-note Für Elise pair](composition/instruments/cybernoid-decoded-programs.md) accepted as musically working; plain reference, native timing/tuning limits and full CPU/VICE/audio evidence retained |

All five stages are complete for the declared first-cycle title and familiar-transfer scope. These verdicts do not establish PCM identity, physical hardware equivalence or suitability of every instrument on arbitrary material.

## Monty on the Run: current milestones

| Stage | State | Evidence / next action |
| --- | --- | --- |
| 1: Identify and map | Done | Pinned title #1, separate SID/inspiration credits, two complete order traversals and first-cycle boundary at call 17,536 |
| 2: Explain mechanisms | Done | Independent packed scheduler and sound programs match all 373,739 source stores across 40,000 calls; four controlled source edits agree |
| 3: Reproduce independently | Done | Compiled source continuation matches all 373,739 original stores across 40,000 calls and nine complete named-state checkpoints; earlier first-cycle/finite export retains all 162,695 original music stores, 128-call tail and full CPU/VICE stop checks |
| 4: Verify and listen | Awaiting listening | [Opening accepted](composition/monty-preparation.md#listening-package-and-reproduction): “I don't hear a difference.” Corrected comparison preserves the source sound after restart; review that continuation, with the earlier finite fade retained separately |
| 5: Transfer and retain | Done | [Familiar 53-note pair](composition/instruments/monty-decoded-programs.md) accepted: “music is spot on”; full CPU/VICE/audio checks, reusable code, scoped verdict and evidence retained |

Keep Monty active while awaiting the corrected reference-continuation verdict. The opening and familiar transfer have explicit listening acceptance; numerical equality and successful rendering remain separate evidence. Acceptance of an imposed finite stop is not required for this source-faithful comparison.

## Completion contract for every study

1. **Identify and map.** Pin archive URL, bytes/hash, subtune, credits, chip/clock, cadence and complete musical form. Check interviews, manuals and original/commented sources alongside the binary; identify the composer's editor and driver where evidence permits.
2. **Explain mechanisms.** Connect executed instructions, state and ordered SID writes to instruments, effects and musical roles. Preserve initialization, release evolution, shared filters, oscillator dependencies and meaningful within-frame timing. Use a targeted intervention to test a causal explanation.
3. **Reproduce independently.** Generate the sound through our own code from editable musical/effect descriptions. Original driver reuse and captured-register replay do not satisfy this stage. Retain the original as a comparison oracle.
4. **Verify and listen.** Prove the supported execution contract, then compare the characteristic phrase in context and the complete selected form, including its ending. Record residual timing/model differences and listening feedback separately. A pleasing excerpt cannot close the complete-song task.
5. **Transfer and retain.** Apply each promoted mechanism to different musical material, preferably a familiar source-backed phrase, with named parameters, constraints and an executable example. Supply a same-material reference and listen for musical usefulness and a suitable ending; a transposed note or matching register trace alone is insufficient. Record the reuse outcome, update the owning library card and index, and retain useful findings, not work diaries.

Mark a case **done** only when all five stages have linked evidence and its declared musical deliverable has been reviewed. Track stages as `queued`, `active`, `awaiting listening`, or `done`; a new artifact or rendered WAV alone does not advance the verdict.

## Reference acquisition and feasibility

| Later study | Pinned archive / evidence route | Remaining execution/form work |
| --- | --- | --- |
| Take On Me | [PVL SID](https://www.hvsc.de/download/C64Music/MUSICIANS/P/PVL/Take_on_Me.sid); [pinned intake](composition/pop-theme-preparation.md#take-on-me) | Full form, instrument mechanisms and audible model comparison |
| Billie Jean | [Bjerregaard SID](https://www.hvsc.de/download/C64Music/MUSICIANS/B/Bjerregaard_Johannes/Billie_Jean.sid); [full score-cycle proof](composition/billie-jean-preparation.md) | Sound mechanisms, independent player and listening quality |
| Airwolf | [Cooksey SID](https://www.hvsc.de/download/C64Music/MUSICIANS/C/Cooksey_Mark/Airwolf.sid); [full numeric cycle proof](composition/pop-theme-preparation.md#airwolf-score-cycle-and-independent-numeric-model) | Independent export, deliberate finite ending and listening quality |
| Ghostbusters | [Lieblich SID](https://www.hvsc.de/download/C64Music/MUSICIANS/L/Lieblich_Russell/Ghostbusters.sid); [RSID intake](composition/pop-theme-preparation.md#ghostbusters) | Execute actual NTSC machine-controlled cadence, identify music/speech and complete form |

Cached HVSC STIL v85 confirms the pop/theme identities; the [intake receipt](../../evidence/pop-theme-intake/provenance.json) retains that cache's fingerprint and exact entry boundaries. All four references are downloaded privately and registered by URL/hash, but remain unauditioned here. *Ghostbusters* needs the full-machine path, not an assumed callable PAL routine; distinguish its Electronic Speech Systems speech from oscillator instruments. CIA/RSID, multispeed or sample techniques must receive suitable tracing support before making fidelity claims.

## Working rules and retained gap

Follow the delivery order above. Use MEDIUM agents for bounded source research, independent mechanism analysis or review serving the active deliverable; the coordinator integrates musical choices and claims. Reuse existing tools and engines, extending them only for demonstrated requirements. Commit coherent milestones; retain canonical analysis in [the evidence archive](../../evidence/README.md), using [verified restoration](../workflows/build-cache.md) for working copies under ignored `build/`. Original SID sources use the [URL/fingerprint download registry](../../config/local-assets.json); reference audio stays local with reproduction recipes. Link portable recipes/findings from the existing research folders. This is a milestone sequence, not an unsupported calendar estimate.

Für Elise remains a useful mechanism proof: [our reconstruction](../../songs/studies/drax-full-reconstruction/README.md) covers DRAX's roughly 40-second recurring theme. The listener finds it nice so far but unfinished. **A completed full Beethoven interpretation remains deferred while the planned SID studies take priority**; the loop study must not be presented as satisfying that deliverable.
