# Executed SID programs: listen, trace, intervene

Learn an instrument by following the player that produces it: locate a liked passage, identify the executed SID stores, trace their values back to the instrument program and its state, then change one mechanism and listen again. This connects audible character to editable programming choices. Register motion alone establishes execution, not its perceptual cause. Start with the [technique lookup](../technique-index.md) and preserve the [reference identity and listening attribution](../composition/fuer-elise-reference.md).

## Repeatable procedure for a master's instrument

Executed code and ordered SID writes are the primary evidence for how a sound is programmed. Audio analysis supports alignment, level matching and clipping checks; listening determines whether the reconstruction retains the desired character.

1. **Define a small audible target.** Preserve the exact SID, hash, subtune, chip model, clock and renderer settings. Identify the passage and the question in listening terms, such as “what makes this releasing bass vibrant?” Render from initialization before cutting an excerpt; entering halfway through loses oscillator, envelope and filter history.
2. **Locate the responsible voices.** Use diagnostic muting only after checking ring/sync dependencies, shared filtering and SID reads. Retain the full mix as context. A muted render is a diagnostic intervention, not necessarily an additive isolated track.
3. **Capture execution.** Record every SID write in order, including repeated writes within a frame, its instruction address and timing convention. Find the real update cadence before assuming once-per-frame playback. Cross-check a bounded section with VICE; the tools below currently support callable PAL VBI players, not arbitrary IRQ-driven tunes.
4. **Work backward from each write.** Follow the executed instructions into instrument tables and changing state. Separate note sequencing from waveform/pitch programs, PWM, gate/envelope control and shared filter ownership. Consult [commented sources and manuals](source-studies.md) to interpret commands, but require execution evidence before assigning a familiar driver's semantics to another binary. Mark descriptive labels and inferred intent as such.
5. **Test a causal explanation.** On a copy, change one declared mechanism and verify the actual register differences. Keep model, rendering and comparison level fixed. Account for changed execution time or earlier state. Ask whether the predicted audible property disappears; an observed sweep alone does not prove that the sweep explains the preference.
6. **Rebuild the mechanism independently.** Write a small editable instrument and scheduler in our own program. Generate modulation from parameters and state instead of replaying a captured register stream or embedding the original player. Compare attack, pitch, gate, pulse, filter, cadence and release with the reference. Record any deliberate simplification and unresolved timing/history mismatch.
7. **Prove transfer and retain the finding.** Audition original versus reconstruction, then exercise the instrument with another note or phrase to establish reuse. A reconstruction is a test of understanding, not a new composition. Promote the technique into the [instrument repertoire](../composition/sound-design-repertoire.md) only with its executable example, constraints and bounded listening verdict; add a route in the [technique lookup](../technique-index.md).

Each retained study needs source identity and source status, the audible target, the decoded mechanism with evidence locations, an executable reproduction command, editable implementation and comparison criteria. Keep generated traces and PCM in ignored build output. Separate **observed execution**, **causal listening result**, and **successful reuse**; do not silently promote one to another.

Use the [local capability assessment](skills-and-integrations.md) to select the tools for each step. Skills supply hardware and debugger guidance; the VICE monitor supplies executed machine evidence; the bounded Python tracer supplies searchable instruction/data records; the renderer supplies repeatable listening files. Inspect a driver's update schedule and hardware dependencies before choosing a RAM-only or controlled-harness experiment.

## Bounded DRAX bass experiment

This study concerns the bass entrance and release in the preferred 2.02–2.75-second Für Elise fragment. The exact input is the archived DRAX PSID, SHA-256 `ea6b7eba46844d399e415368eae86c3ddf03bd9041ecba93e7bb53b384daa2a1`: one declared MOS6581, PAL VBI, init `$1000`, play `$1003`. The recorded program window is zero-based play calls 99–150, reached by executing init and all preceding calls. Audio time and call number have a startup offset; use the identified attack sequence to align the fragment, rather than treating `call / PAL rate` as an exact WAV timestamp. The listener confirms vibrancy in the diagnostic bass alone and likes bass with chord; neither finding identifies a synthesis parameter by itself.

Two observers provide different, complementary evidence:

| Observer | Recorded evidence | Boundary |
| --- | --- | --- |
| [CPU instruction/data tracer](../../../scripts/trace-sid-program.py) | Pre-instruction PC, opcode bytes, disassembly, A/X/Y/SP/status, relative instruction-start cycle, resolved RAM operand address/value and the associated SID stores. | RAM-only callable execution; operand values are memory snapshots, not a bus-access trace. |
| [Headless VICE store tracer](../../../scripts/trace-sid-vice.py) | Executed SID writer PC/opcode, store-source CPU registers, effective SID address/value, raster line/cycle and full-machine monitor stopwatch; adjacent disassembly and RAM data remain in the log. | Original init/play inside a controlled 6510 harness, with interrupts, sprites and display DMA disabled; monitor checkpoint time is not the SID bus-write time. |

On 2026-10-13, the [CPU trace](../../../build/reference-studies/drax/program-cpu/trace.json) records 13,461 instructions and 1,212 SID stores in the window. The [VICE result](../../../build/reference-studies/drax/program-vice/final/study.json) independently reproduces every `(call, address, value, writer PC)` pair. Its 151 play-entry checkpoints follow the 19,656-cycle PAL frame period within six cycles of polling jitter. The [raw VICE log](../../../build/reference-studies/drax/program-vice/final/monitor.log) and [parsed trace](../../../build/reference-studies/drax/program-vice/final/trace.json) preserve the evidence; neither is a listening verdict.

The independent executed fixture in [the tests](../../../tests/sid_vice_trace_test.py) stores a changing counter at PC `$100C`, then loads another value before storing at `$1011`, then immediately changes A again. VICE associates each store with the store's PC and source A, rather than the following load. The first store checkpoint appears 14 cycles after play entry, after the fixture's six-cycle `INC`, four-cycle `LDA` and four-cycle `STA`. Consequently, `monitorCycle` describes the checkpoint after the executed instruction, while the CPU tracer's `instructionStartCycle` describes its beginning. Subtracting those timestamps without accounting for instruction duration and the hardware schedule would mix different meanings.

## Follow the bass program

Addresses below are observed locations in this pinned binary. The role names are descriptions of their executed behavior, not recovered composer symbols or an original editable instrument workfile. The original binary and derived evidence remain in ignored storage, consistent with the [reference provenance](../composition/fuer-elise-reference.md#provenance-and-playback).

| Mechanism | Executed program and state | SID result |
| --- | --- | --- |
| Pulse initialization and rate | At call 100, PC `$126B` reads `$1AA5=$50` into the rate state at `$1553`; PC `$1271` reads `$1AA6=$06`. The initializer sets width state `$1559/$155C` to `$00/$06`, giving width `$600`. | The body does not use the small, fast, symmetric PWM of the earlier original candidate. |
| Pulse evolution | PCs `$12D5–$1317` add or subtract `$1553` from `$1559/$155C`, carrying or borrowing between bytes. `$1556` selects direction; `$154D=$01` and `$1550=$0F` are the high-byte reversal bounds. The upper-bound comparison flips direction at call 129. | PCs `$1421/$1427` write pulse low/high via `$D402,Y/$D403,Y`. Bass has `Y=0`: `$650` at call 101, `$6A0` at 102, then steps of `$50` to `$F10` at 129 and back down. PWM continues through release. |
| Attack pitch | PC `$1340`, `LDA $16A2,Y`, consumes `$16A2=$DA` at call 101, selecting absolute high pitch through frequency-table bytes `$151C/$151D=$E0/$C4`; the following `$16A3=$00` restores relative base pitch via `$1492/$1493=$A9/$03`. | PCs `$1433/$1439` write `$D400,Y/$D401,Y`: high-frequency noise at `$C4E0`, then A1 at `$03A9`. The bass body thereafter holds that pitch. |
| Waveform and release | PC `$1372`, `LDA $17A2,Y`, consumes `$17A2=$81`, `$17A3=$41`, `$17A4=$40` at calls 101, 102, 103 through the program index at `$1544`. PC `$144D` applies gate mask `$101A=$FF` on all three calls. | PC `$1450` writes `$D404,Y`. The instrument program itself selects noise/gate, pulse/gate, then pulse/release. The early release is not a score note-off event. Waveform `$40` remains selected while AD/SR stays `$02/$CA`. |
| Filter attack and body | PC `$1321`, `LDA $18A2,Y`, consumes `$18A6=$F0` at call 101, then `$18A7=$08` at 102. PC `$124D` sets routing/resonance. | PC `$142D` writes cutoff high at `$D416`: `$F0` gives cutoff `$780` for the noise attack; `$08` gives `$040` throughout the pulse release. `$D417=$F1` routes only bass to the shared filter; `$D418=$1F` selects low-pass and volume 15. |

The shared writer loop visits channels with `Y=$0E,$07,$00`; it writes the shared cutoff register for each channel using the current global cutoff state. This explains repeated `$D416` stores within one call. A final frame snapshot hides their order, and the last value alone does not reconstruct the attack's complete timing. The executed trace supplies that order without claiming an exact analog reconstruction.

The programming lesson is a sustained transformation of one releasing oscillator: broad PWM, a held low pitch and an instrument-defined gate closure, following a short noise/filter attack. Keep these mechanisms distinct when implementing an original native bass. SID-Wizard's signed pulse sweeps and waveform rows can express broad motion and an explicit gate-clear pulse body; verify their actual table timing, including the separate advancement call after a sweep completes. Preserve the pulse waveform throughout release. The shared filter must keep a declared owner and routing policy.

## Reproduce the execution evidence

After the [local dependency setup](../../local-setup.md), regenerate into unused paths. The CPU command uses the existing py65 dependencies; the VICE command uses the genuine headless executable and file monitor described in [the audio workflow](../../audio-workflow.md).

```sh
PYTHONPATH=.tools/test-deps python3 scripts/trace-sid-program.py .local/research/fuer-elise/drax-fuer-elise.sid --first-call 99 --last-call 150 --output build/reference-studies/drax/program-cpu-new/trace.json
python3 scripts/trace-sid-vice.py .local/research/fuer-elise/drax-fuer-elise.sid --oracle build/reference-studies/drax/fuer-elise.writes.json --first-call 99 --last-call 150 --output build/reference-studies/drax/program-vice-new
python3 -m unittest discover -s tests -p sid_vice_trace_test.py -v
```

The VICE tracer deliberately supports only one explicitly declared PAL SID, one subtune, callable PSID v2 init/play, payload wholly inside RAM `$0400–$9FFF`, and a window ending by call 254. It rejects missing or extra calls, changed or reordered stores, malformed opcode/address context, unsupported read-modify-write stores, cadence overruns and existing output paths. The tracepoint filter groups each comparison explicitly because VICE 3.9's [local monitor manual](../../../.tools/vice-headless-3.9/source/doc/vice.texi) defines left-to-right condition evaluation. Store-source registers and matching opcode bytes determine each value; the independent oracle must agree before the study is reported as verified.

## Determine what causes the liked character

Follow execution tracing with controlled listening interventions on ignored copies of the exact reference, preserving the original binary and PCM. Freeze pulse movement while retaining attack, pitch, envelope, filter and model; separately bypass bass filtering while preserving the pulse program. The interventions below render diagnostic bass solos; retain the [original full mix](../composition/fuer-elise-reference.md) as listening context. Check the modified execution before interpreting what changed. Each comparison answers a bounded question about the reference mechanism; it does not establish that an original arrangement has achieved the same musical quality.

The [controlled bass experiment](../../../scripts/study-drax-bass.py) retains the exact byte interventions and generated audio identities in its [study manifest](../../../build/reference-studies/drax/bass-program-experiment/study.json). Its controls act on the executed data: freeze the pulse-rate byte `$1AA5`, set the initialization byte `$1AA6` for a declared stationary width, and separately change the filter-routing immediate at `$124C` from `$F1` to `$F0` while retaining resonance. Listening to these interventions is still required; successful execution guards do not supply their perceptual result.

```sh
PYTHONPATH=.tools/test-deps python3 scripts/study-drax-bass.py .local/research/fuer-elise/drax-fuer-elise.sid --output build/reference-studies/drax/bass-program-experiment-new
```

The generated controls preserve write order/counts, pitch, gate, ADSR and companion registers. Freezing PWM changes only pulse-width writes, but also changes pulse initialization before the body and shifts some instruction-start times by 38–51 cycles; this is not a bus-timing-exact isolation. Filter bypass changes one routing write and preserves instruction-start timing. The original diagnostic PCM is byte-identical to the previously auditioned bass solo. Both comparisons use the same matched original and a common AC-RMS target with headroom; this controls measured level, not perceived loudness.

- [PWM comparison](../../../build/reference-studies/drax/bass-program-experiment/comparisons/context-no-pwm.ab.wav): original, half-second gap, then stationary pulse width.
- [Filter comparison](../../../build/reference-studies/drax/bass-program-experiment/comparisons/context-filter-bypass.ab.wav): original, half-second gap, then bass filter bypassed.

Each side lasts 1.2 seconds and includes the bass entrance. Listening verdicts are pending; these files test the proposed explanation rather than certify it.

Chip model is another independent variable. The preferred render honors the declared 6581, whereas earlier original candidates used 8580. The pinned SIDLite implementation applies input-dependent cutoff modulation on its 6581 path and uses a different cutoff and resonance curve on 8580. Equal numeric settings therefore do not produce equivalent filtering. A model comparison should be explicit and separate from the PWM or routing intervention; a stronger 8580 cutoff sweep is not execution evidence for the static-cutoff 6581 release. Keep final acceptance grounded in the listener's judgments and retain useful original instrument decisions in their owning recipe/card.

## Recreate and reuse the decoded instrument

The [independent three-voice reconstruction](../../../songs/studies/drax-full-reconstruction/README.md) extends the procedure to the entire preferred texture. Its [musical mapping](../composition/instruments/drax-decoded-trio.md) connects roles to parameters and phrase constraints; its editable description generates all three voices without the original driver or register replay. The comparison checks every ordered register write, including companion cutoff repetitions. Within-frame timing remains a separately measured difference.

The [independent DRAX bass reconstruction](../../../songs/studies/drax-bass-reconstruction/README.md) supplies our own editable 6502 player, instrument parameters and A1/E2 reuse phrase. It computes pulse motion and sequences preparation, noise attack, pulse body and instrument-owned release. It neither embeds the reference player nor replays a register dump.

The reference comparison checks the ordered bass/global writes and frame states through the excerpt. It deliberately projects out companion-voice writes and retains only the last cutoff-high write per call; the original's intermediate cutoff writes and exact within-frame timing are not reproduced. A separate VICE run checks the new program against its own CPU audit. These checks establish the implemented mechanism under the declared profile. The listener's [accepted three-second in-context match](../../../songs/studies/drax-bass-reconstruction/README.md#listening-verdict) supplies bounded perceptual evidence for the replacement bass in the original accompaniment; solo and A1/E2 transfer verdicts remain pending. This is a bass-fragment reconstruction, not a recreation of DRAX's complete arrangement.
