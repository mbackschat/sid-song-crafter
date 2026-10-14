# Shades pulse and pitch programs

Use these programs for a moving pulse bass, short harmonic replies and a filtered melody with delayed vibrato or target glides. The [owning Shades study](../shades-preparation.md) connects the recovered mechanisms to executed instructions, state transitions and the original pulse intervention. The [reference intake](../../composers/huelsbeck-tel.md#shades-reference-intake) owns Chris Hülsbeck's attribution and the selected filter-corrected archive variant.

**Status:** source-free score/modulation models and both compiled exports pass CPU and real CIA-timed VICE execution; rendering is complete. On 2026-10-13 the listener accepted the independent reconstruction's sound/phrasing and fade ending; the [owning study](../shades-preparation.md#reproduce-and-review-listening) retains the exact verdict. The listener accepts the original transfer instruments but rejects its last 2–4 seconds as wrong-sounding notes. The familiar Für Elise transfer below is accepted musically, including its ending. The earlier moving-pulse verdict, “little quieter and more vibrant” than the frozen-pulse version, applies separately to the reference intervention.

## Choose and edit the sound

The [transfer programs](../../../../songs/shades-transfer-programs.json) provide two named blocks. `pulse-trio` retains the decoded `opening-pulse` patch. `glide-trio` changes only voice 3's `portamento_step` from 0 to 96. The [original transfer score](../../../../songs/shades-transfer.json) uses a cold silent state instead of the reference's retained startup state, new notes and rhythm, and an authored fade. The complete reference reconstruction separately uses [the full program bank](../../../../songs/shades-programs.json).

| Voice / use | Parameters in `pulse-trio` | Performance constraint |
| --- | --- | --- |
| 1: bass with motion in its release | Pulse, AD/SR `$09/$0A`, initial width `$DFF`, step `$10`, 16 ascending and 16 descending calls | Motion continues after gate-off. Allow space before retriggering if the releasing shape is the purpose. |
| 2: offbeat harmonic replies | Pulse, AD/SR `$09/$0A`, initial width `$6FF`, step `$20`, one ascending and 16 descending calls | Fine tuning adds 5 to the frequency low byte without carrying into the high byte. It is not a cents offset. |
| 3: filtered melody | Pulse, AD/SR `$09/$0D`, width `$950`, step `$20`, 16 ascending and descending calls; vibrato delay 16, extent 8, step `$10` | Voice 3 owns filter triggering. Fine tuning adds 10 to the low byte. Glides delay vibrato through the retained source flag behavior. |

The shared filter uses routing `$F4` and mode/volume `$1F`: resonant low-pass for voice 3, with cutoff high `$A5`, low 0, 48 descending calls, fine step 7 and coarse step 1. Moving the melodic role to another voice requires an intentional change to filter routing and trigger ownership. These three voices use pulse without ring/sync coupling; other blocks in the full source bank have different dependencies.

## Timing and articulation contract

The demonstrated target is one PAL MOS6581, CIA Timer A with low latch `$25` and high `$30`, approximately 79.93 calls per second after the initial interval. Parameters measured in calls change duration if the timer changes. All pulse ascents run before eligible descents; a counter reaching zero can permit a descent in the same call. Width arithmetic retains 16-bit state rather than clamping to the SID's 12-bit width.

A hold preserves pitch/gate work while modulation continues. A rest requests gate-off, with voice-specific repeated-rest writes. A high-bit pitched command changes pitch/target and then requests gate-off; it is not ordinary legato. A new gated note still emits the source's control/retrigger sequence. Target portamento can preserve the preceding frequency when the previous row was a hold, so connected pitch does not imply an unbroken envelope.

The low byte of `portamento_step` enables the effect; a nonzero high byte alone does not. Target descent retains the source's unusual equal-high-byte comparison, and delayed vibrato emits two subtraction writes when its delay expires. The filter's fine-step carry threshold is seven. These are verified driver behaviors, not general SID rules; consult [the Python mechanisms](../../../../scripts/shades_programs.py) and owning study before reusing arithmetic in another driver.

The [Giana second-reference check](../huelsbeck-contrast.md) corroborates changing pulse widths while GATE is clear in its bounded in-game opening. It also shows why the filter schedule above must remain driver-specific: two voice paths can advance Giana's shared cutoff state in one raster refresh, whereas Shades advances one global contour per call. Keep routing, state-update ownership and update cadence separate when translating a sound. The listener confirms an original animation/tone difference in Giana's isolated 8–10-second passage; this check does not change the accepted Shades implementation or promote a new Giana instrument.

## Original transfer phrase

The eight-bar phrase uses C–A minor–F–G, then C–A minor–F–C. Voice 1 plays roots and fifths, voice 2 gives offbeat chord tones, and voice 3 develops an original melody around E4–C5 before resolving to C4. Each bar has 16 rows of ten calls, about two seconds. The first four bars use `pulse-trio`; the second four use `glide-trio`. This compares the gesture in related musical context, rather than claiming an isolated A/B experiment.

The final selection releases all voices and lowers volume every two five-call rows. Its 48 rows allow the fade to reach zero before four terminal silence stores at call 1521. The computed model can be inspected without a reference SID:

```sh
PYTHONPATH=.tools/test-deps python3 scripts/shades_player.py songs/shades-transfer.json --programs songs/shades-transfer-programs.json --output build/shades-transfer-model-new
```

Compile and render the same editable inputs through [the independent workflow](../../../workflows/decoded-song-workflow.md). The [transfer build receipt](../../../../evidence/shades-transfer/build.json) records a 2,370-byte payload, 10,734 matching stores over 1,522 calls and no original driver or replay data. The [VICE receipt](../../../../evidence/shades-transfer/vice/study.json.gz) verifies the full arrangement and ending. The [local 22-second render](../../../../build/shades-transfer/reconstructed.wav) has no clipped samples and a settled final half-second; [the audio recipe](../shades-independent-audio.json) preserves exact settings and hashes.

Use a fresh output directory. Model output is an ordered-write oracle, not captured-event playback or a listening verdict. Promote this as a listening-approved instrument example only after the compiled phrase and its ending have been reviewed.

## Reuse outcome

Baseline and feedback recorded on 2026-10-13 using the [reuse measurement rules](../../../workflows/decoded-song-workflow.md#record-reuse-and-effort). This records executable reuse and accepted instrument sound, but the ending is not accepted.

| Field | Evidence / outcome |
| --- | --- |
| Original phrase | [Eight-bar score](../../../../songs/shades-transfer.json), [program bank](../../../../songs/shades-transfer-programs.json) and [22-second listening file](../../../../build/shades-transfer/reconstructed.wav) |
| Reused components | Existing [compiler](../../../../scripts/compose-shades.py), [scheduler](../../../../songs/players/shades.asm) and [effect routines](../../../../songs/players/shades-effects.asm); the decoded `opening-pulse` patch is retained as `pulse-trio` |
| Adaptation and new material | New notes, rhythm, cold silent initialization and authored fade; `glide-trio` changes voice 3's portamento step to 96 within the existing program contract |
| Listening-driven revisions | One requested: final 2–4 seconds sound like wrong notes; use familiar material because the invented fragment confounds sound and composition judgment |
| Effort to accepted phrase | Pending; historical active work time was not recorded |
| Transfer and ending verdict | Instruments accepted: “The instruments are ok, though”; ending needs changes: “the last 2-4 s sound odd like wrong musical notes” |
| Next improvement | Compare the preserved Für Elise opening phrase with the same notes rendered plainly and through these programs |

## Choose glides by phrase, not by instrument name

The rejected invented ending uses `glide-trio` across every held-note transition in its final bar. A gated note following HOLD begins at the preceding frequency and moves toward the new target while its envelope restarts. In this cadence, E4→G4 takes 11 calls (about 138 ms), G4→E4 takes 10 (125 ms), E4→D4 takes five (63 ms), and D4→C4 takes four (50 ms). The 10-call glide occupies half its 20-call note. This is a plausible contributor to the listener's wrong-note impression, not a confirmed perceptual cause.

The model reaches the final C4 target at call 1245, releases at 1281, and keeps its normal vibrato range through the fade. There is no new score note during that fade. Selecting `pulse-trio` only for the release does not change the retained pitch trajectory; choose it before the relevant note-on to remove that glide. For a familiar phrase whose chromatic pitches must be clear immediately, use the existing `pulse-trio` and assess deliberate glides separately. Preserve source-verified driver arithmetic; a musical choice is not a driver bug.

The [diagnostic receipt](../../../../evidence/shades-ending-diagnosis/summary.json), [full states and ordered stores](../../../../evidence/shades-ending-diagnosis/states.json.gz) and [reproducer](../../../../evidence/shades-ending-diagnosis/reproduce.py) retain the three tested variants. Restore the reproducer through the [evidence workflow](../../../workflows/build-cache.md), then run `python3 build/shades-ending-diagnosis/reproduce.py` to regenerate its state and summary files from the fingerprinted editable inputs.

## Familiar transfer: accepted

The [editable transfer score](../../../../songs/shades-elise-transfer.json) retains all 53 events from beats `[0,12)` of the [preserved three-voice arrangement](../../../../songs/fuer-elise.json): 35 melody, six bass and 12 harmony events. This is the first repeat body and its A-minor first ending, about ten seconds of music plus release. Source provenance remains in the [score guide](../../../songs/fuer-elise-score.md). The [bounded adapter](../../../../scripts/studies/shades/prepare-shades-elise.py) reproduces the score and [plain reference bank](../../../../songs/shades-elise-reference-programs.json); run `python3 scripts/studies/shades/prepare-shades-elise.py --check` to check them.

Both versions use the same score, driver, frequency table and CIA cadence. The plain reference uses the source arrangement's triangle/envelope patches with modulation, fine tuning and filtering disabled; it is a generated score reference, not an original recording. The candidate reuses the unchanged `pulse-trio` block, placing bass, harmony and melody on voices 1, 2 and 3. No glide block is selected. Source event boundaries round independently to the nearest CIA call; the maximum measured onset error is 6.177 ms, with no accumulated tempo drift. This preserves the phrase's notes and rests, not source-driver bus timing or pedal behavior.

| Listen | File / interpretation |
| --- | --- |
| Complete matched pair | [plain-then-shades.ab.wav](../../../../build/shades-elise-transfer/listening/plain-then-shades.ab.wav): 13-second plain reference, 0.5-second gap, same phrase with Shades instruments |
| Ending pair | [ending-plain-then-shades.ab.wav](../../../../build/shades-elise-transfer/listening/ending-plain-then-shades.ab.wav): seconds 8–13 of each matched render, in the same order |
| Plain reference alone | [reference.wav](../../../../build/shades-elise-transfer/reference/reference.wav): original render level |
| Shades candidate alone | [reconstructed.wav](../../../../build/shades-elise-transfer/candidate/reconstructed.wav): original render level |

The A/B applies 0 dB to the reference and −5.356 dB to the Shades candidate for equal full-file AC RMS; original renders remain unchanged. [The audio recipe](../shades-elise-audio.json) pins source, outputs, settings, gains and exact fresh-directory reproduction commands. All audio stays local.

The [conversion receipt](../../../../evidence/shades-elise-transfer/conversion.json) and [focused guards](../../../../tests/shades_elise_transfer_test.py) verify source event preservation, absolute timing, gaps, direct pitch attacks, and the release/fade. Both compiled players match their numeric models and full real-CIA VICE execution over 961 calls: [candidate](../../../../evidence/shades-elise-transfer/candidate/vice/study.json.gz) matches 6,253 stores, [plain reference](../../../../evidence/shades-elise-transfer/reference/vice/study.json.gz) matches 1,619. Both have maximum interval/phase errors of four cycles. Final note-off is call 800, volume reaches zero at 950 and the finite stop is 960. Both renders are unclipped and their final half-second has zero AC RMS.

**Listening accepted on 2026-10-13:** “Works musically, including the ending.” This accepts the familiar phrase with the pulse instruments and delayed vibrato, and closes the bounded reuse test. It does not establish that arbitrary glides work musically, erase the invented ending's rejection, or complete the separately deferred full Beethoven interpretation.

| Reuse outcome | Evidence / result |
| --- | --- |
| Reused unchanged | Shades compiler, numeric model, 6502 scheduler/effects and `pulse-trio` bank |
| New work | Bounded source-score adapter, same-material plain reference bank and source-preservation guards; no new synthesis mechanism or notes |
| Listening revision | One replacement after feedback: use familiar source material and omit indiscriminate glides; first review of this pair accepted |
| Effort | Active time not recorded; no measured speedup claim |
| Next reuse lesson | Keep musical material familiar and fixed when assessing instruments; test compositional novelty separately |
