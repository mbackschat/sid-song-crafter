# Bach Toccata: integrated lead motion

This separate original experiment returns to the [accepted driven opening](../bach-toccata-opening-driven/README.md) after the [added background replies were rejected](../bach-toccata-intention-blend/README.md#listening-rejection). It tests electronic animation inside the existing lead. **The listener accepted this opening on 2026-10-14:** “yes, better. I like it”. The [listening review](listening-review.json) pins the exact audio and verdict. This acceptance covers its 12-second opening and release tail; the [full-song extension](../bach-toccata-integrated-full/README.md) remains pending human review.

- [Score](score.json): byte-identical to the accepted score, with 21 melody, 20 bass and four harmony events. Its source mapping remains owned by the [accepted preparation](../bach-toccata-opening-driven/preparation.json).
- [Native recipe](hybrid.json): only `instruments.lead.pulse` changes. The existing pitched lead, waveform, envelope, bass, harmony, diminished cycle, shared filter and pacing retain their accepted values.
- [Preparation](preparation.json): pins the accepted inputs, original prose brief and exact pulse-width oracle, including native row-advance and jump calls. No Gyruss binary, traces, extracted notes, audio or program was consulted for this design.

The lead resets pulse width to `$400` (25% duty), adds `$40` for 16 sweep executions to `$800` (50%), then breathes more slowly: subtract `$18` for 32 executions to `$500` (31.25%), add `$18` for 32 executions back to `$800`, and jump to the descending body. The finite onset never repeats within a held note. Explicit lead instrument selection restarts it at each existing note. Extra consumes an unchanged-width call at each sweep-row advance and at the jump; the breathing loop therefore spans 67 PAL calls, approximately 1.34 seconds. The first note frame retains TEST silence, with pulse-body initialization on the next call. Motion can continue during release; the ending is checked separately.

The [moving-pulse lead card](../../../docs/research/composition/instruments/lead-02-moving-pulse.md) provides the one-oscillator method and scoped listening evidence; [FORM-02](../../../docs/research/composition/gestures/driven-organ-phrasing.md) preserves the accepted weight and pacing. Target: one MOS8580 at `$D400`, PAL, A=440 Hz, pinned SID-Wizard 1.97 Extra at 1x, and the inherited 125-tick release tail. These authored parameters test a musical hypothesis; register agreement does not establish that the motion is perceptually useful.

Build the accepted opening and candidate, render their full approximately 15.5-second spans, verify that only lead pulse-width frame registers differ, and run standalone VICE checkpoints with the [cached recipe](../../../config/listening/bach-toccata-integrated-motion.json):

```sh
python3 scripts/listening-package.py config/listening/bach-toccata-integrated-motion.json --output build/bach-integrated-motion
PYTHONPATH=.tools/test-deps PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.bach_integrated_motion_test -v
```

The [CPU integration test](../../../tests/bach_integrated_motion_test.py) executes the complete native candidate and checks the exact finite-onset/body trajectory throughout every gated lead note. The [listening index](../../../build/bach-integrated-motion/listening.md) links both full renders and the unity-gain accepted-then-candidate A/B with a half-second separator; the [run receipt](../../../build/bach-integrated-motion/run.json) pins native, CPU, PCM and VICE outputs. Review asks whether motion within the existing lead makes the opening feel more electronic and alive while retaining its accepted weight and gestures.

On 2026-10-14 the test verified 454 gated lead body frames. The paired package completed all five stages: 779 CPU calls and 45 note starts, gate/volume stop at tick 726, and peak play cost 2123 of 19656 PAL cycles. Only offsets 2 and 3 differ between the two complete frame streams; lead pitch/control/ADSR, both accompanying voices and the shared filter equal the accepted execution. The candidate render contains 683720 mono PCM16 samples at 44100 Hz (15.503855 seconds), peak magnitude 10627 and zero clipped samples. Seventeen VICE checkpoints, including post-stop call 750, pass the seven-cycle PAL tolerance. These results establish bounded execution and signal health separately from the later listening acceptance.

The scoped design lesson is that integrated timbral motion succeeds in this opening where added background replies were rejected. Listen to the accepted [integrated-motion.wav](../../../build/bach-integrated-motion-listening/integrated-motion.wav) or the [accepted-then-integrated A/B](../../../build/bach-integrated-motion-listening/accepted-then-integrated.ab.wav); the [review](listening-review.json) retains the audio fingerprint. No full-song approval follows from this opening verdict.

Model-assistance review after feedback, 2026-10-14: skip unvalidated preference inference because human listening settles the opening decision and no qualified model criterion adds evidence. The next checkpoint is the full-song extension and its feedback. Execution, PCM health and VICE evidence remain separate from the listening decision.


The listener subsequently described the difference as subtle and less experimental than Gyruss. This qualifies the aim, not the positive verdict: retain this version as the liked restrained option while testing a distinct, more expressive main-voice attack.
