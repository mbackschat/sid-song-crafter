# Shades pulse and pitch programs

Use these programs for a moving pulse bass, short harmonic replies and a filtered melody with delayed vibrato or target glides. The [owning Shades study](../shades-preparation.md) connects the recovered mechanisms to executed instructions, state transitions and the original pulse intervention. The [reference intake](../../composers/huelsbeck-tel.md#shades-reference-intake) owns Chris Hülsbeck's attribution and the selected filter-corrected archive variant.

**Status:** source-free score/modulation models and both compiled exports pass CPU and real CIA-timed VICE execution; rendering is complete. On 2026-10-13 the listener accepted the independent reconstruction's sound/phrasing and fade ending; the [owning study](../shades-preparation.md#reproduce-and-review-listening) retains the exact verdict. This original transfer phrase still awaits listening approval. The earlier moving-pulse verdict, “little quieter and more vibrant” than the frozen-pulse version, applies separately to the reference intervention.

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

## Original transfer phrase

The eight-bar phrase uses C–A minor–F–G, then C–A minor–F–C. Voice 1 plays roots and fifths, voice 2 gives offbeat chord tones, and voice 3 develops an original melody around E4–C5 before resolving to C4. Each bar has 16 rows of ten calls, about two seconds. The first four bars use `pulse-trio`; the second four use `glide-trio`. This compares the gesture in related musical context, rather than claiming an isolated A/B experiment.

The final selection releases all voices and lowers volume every two five-call rows. Its 48 rows allow the fade to reach zero before four terminal silence stores at call 1521. The computed model can be inspected without a reference SID:

```sh
PYTHONPATH=.tools/test-deps python3 scripts/shades_player.py songs/shades-transfer.json --programs songs/shades-transfer-programs.json --output build/shades-transfer-model-new
```

Compile and render the same editable inputs through [the independent workflow](../../../workflows/decoded-song-workflow.md). The [transfer build receipt](../../../../evidence/shades-transfer/build.json) records a 2,370-byte payload, 10,734 matching stores over 1,522 calls and no original driver or replay data. The [VICE receipt](../../../../evidence/shades-transfer/vice/study.json.gz) verifies the full arrangement and ending. The [local 22-second render](../../../../build/shades-transfer/reconstructed.wav) has no clipped samples and a settled final half-second; [the audio recipe](../shades-independent-audio.json) preserves exact settings and hashes.

Use a fresh output directory. Model output is an ordered-write oracle, not captured-event playback or a listening verdict. Promote this as a listening-approved instrument example only after the compiled phrase and its ending have been reviewed.

## Reuse outcome

Baseline recorded on 2026-10-13 using the [reuse measurement rules](../../../workflows/decoded-song-workflow.md#record-reuse-and-effort). This records executable reuse; musical acceptance remains pending.

| Field | Evidence / outcome |
| --- | --- |
| Original phrase | [Eight-bar score](../../../../songs/shades-transfer.json), [program bank](../../../../songs/shades-transfer-programs.json) and [22-second listening file](../../../../build/shades-transfer/reconstructed.wav) |
| Reused components | Existing [compiler](../../../../scripts/compose-shades.py), [scheduler](../../../../songs/players/shades.asm) and [effect routines](../../../../songs/players/shades-effects.asm); the decoded `opening-pulse` patch is retained as `pulse-trio` |
| Adaptation and new material | New notes, rhythm, cold silent initialization and authored fade; `glide-trio` changes voice 3's portamento step to 96 within the existing program contract |
| Listening-driven revisions | None recorded for this transfer; first verdict pending |
| Effort to accepted phrase | Pending; historical active work time was not recorded |
| Transfer and ending verdict | Pending; reconstruction approval applies separately |
| Next improvement | Let transfer feedback identify any needed musical change before extending the mechanism or backend |
