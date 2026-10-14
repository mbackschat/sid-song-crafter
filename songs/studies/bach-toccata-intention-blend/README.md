# Bach Toccata: original electronic answers

This bounded original experiment follows the listener's prose brief: preserve Bach's recognizable gestures, harmonic weight and dramatic shape, add a playful electronic entrance, keep sustained tones moving, and connect transitions while leaving the strongest notes clear. It uses the source-backed [accepted 12-second opening](../bach-toccata-opening-driven/README.md) and that brief. No Gyruss SID, extracted notes, audio or effect program was supplied to the candidate designer. Listening acceptance remains pending.

- [Score](score.json): all 45 accepted note events retain their pitches, onsets and durations; four authored events fill otherwise unused third-voice slots. They are additions to the arrangement, not recovered Bach source notes.
- [Native recipe](hybrid.json): retains the four accepted instruments and adds three original short pulse programs. The accepted lead PWM supplies motion during sustained melody notes; the inherited diminished cycle preserves the chord's harmonic weight.
- [Preparation](preparation.json): fingerprints the accepted inputs, records the prose intentions and exact authored deviations, and assigns each SID voice its role. It links inherited source mapping instead of repeating the accepted ledger as if it described the added effects.

| Authored third-voice slot | Pitch-table gesture | Musical role |
| --- | --- | --- |
| 0.14–0.42 seconds | A5–E6–A6–E6–A5 | Delayed sparkle after the opening octave A has spoken |
| 2.34–2.54 seconds | D5–A5–D5 | Short reply in the first existing breath |
| 4.64–4.84 seconds | D4–A4–D4 | Lower reply in the second existing breath |
| 7.26–7.54 seconds | D3–F3–A3–D4 | Rising connector that clears before the 7.6-second D2 pedal |

Voice 1 keeps the melody, voice 2 keeps octave foundation and pedal with sole shared-filter ownership, and voice 3 plays the four replies before returning to the unchanged diminished chord at 8.2 seconds and written G–E–F-sharp resolution. No harmonic support is removed. Each new program uses gated pure pulse with two PAL calls per pitch, then holds its final pitch. Pulse width starts at `$300`, rises by `$18` for 12 executions to `$420`, then holds through release. ADSR `$0132` supplies low sustain and a short release; native frame 1 retains TEST `$09`. There is no noise, ring/sync dependency, filter program, looping pitch cycle or added chip.

The [FORM-02 timing gesture](../../../docs/research/composition/gestures/driven-organ-phrasing.md), [selective answering gesture](../../../docs/research/composition/gestures/chord-bursts.md) and [moving-pulse card](../../../docs/research/composition/instruments/lead-02-moving-pulse.md) supply the relevant project constraints. The target remains one MOS8580 at `$D400`, PAL, A=440 Hz, the supported 1x Extra exporter, and the inherited 125-tick release tail. The source-backed opening lasts 12 seconds; the full verified render lasts approximately 15.5 seconds including release and confirmation silence. This is an opening experiment, not a complete-Toccata revision.

Build and render both inputs with the [cached recipe](../../../config/listening/bach-toccata-intention-blend.json):

```sh
python3 scripts/listening-package.py config/listening/bach-toccata-intention-blend.json --output build/bach-intention-blend
```

The [listening index](../../../build/bach-intention-blend/listening.md) links the accepted opening, original candidate and accepted-then-candidate A/B at unity gain with a half-second separator. The [run receipt](../../../build/bach-intention-blend/run.json) identifies exact native source, PSID, PRG, CPU schedule and PCM paths. Human review asks: do the short pulse replies make the entrance and breaths feel playful and connected while the Bach contour, pedal weight and chord arrival stay clear?

On 2026-10-14 the complete native oracle verified 49 note starts, 779 CPU calls, matching volume/gate stop at tick 726, and a peak play cost of 2167 of 19656 PAL cycles. The mono PCM16/44100 Hz render contains 683720 samples, has peak magnitude 11540, no clipped samples and zero final-half-second AC RMS. The [independent gesture check](../../../evidence/bach-intention-blend/gesture-verification.json) verifies all 30 finite pitch-table body frames within one PAL frequency-register unit of the intended MIDI pitches and checks the corresponding PWM steps. Every inherited melody, bass and shared-filter frame equals the accepted execution; inherited harmony frames equal it after the chord's TEST onset. The rebuilt reference WAV matches the previously published accepted opening byte for byte. These checks establish execution and signal health; the human listening question remains open.

The model-assistance review skips inference because no validated model criterion settles preference for these electronic replies. Reassess after human feedback. [Standalone VICE verification](../../../evidence/bach-intention-blend/vice.json) passes gesture checkpoints and post-stop call 750, separately from callable CPU and PCM evidence. The [stable paired audition](../../../build/bach-intention-blend-listening/accepted-then-blend.ab.wav) presents the accepted opening first and the candidate second; [publication provenance](../../../evidence/bach-intention-blend/audition.json) pins both files.
