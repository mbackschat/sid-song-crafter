# FORM-02 — organ weight with forward motion

**Status:** the [Bach driven opening](../../../../songs/studies/bach-toccata-opening-driven/README.md) was listening-accepted on 2026-10-14 (“nice”); the earlier slow opening's hybrid sound direction was accepted but its pacing and long pauses were rejected. This verdict covers that opening, not every organ arrangement. Browse the [gesture library](README.md).

## Musical purpose and editable example

Keep pedal foundation and harmonic weight while giving a dramatic organ phrase the forward motion of game music. Shorten held statements and between-gesture gaps more strongly than the running notes. Preserve recognizable contours and harmonic arrivals; a uniform tempo increase can rush the runs while leaving proportionally excessive pauses.

The [opening generator](../../../../scripts/studies/bach/prepare-opening.py) exposes the authored `original` and `driven` timing maps separately from the preserved source. The revision reduced music from 24 to 12 seconds and written gaps from 5.7 to 1.3 seconds, while retaining the three descent durations, pitches and native instruments. Its [comparison recipe](../../../../config/listening/bach-toccata-opening-driven.json) reproduces both versions; the [owning study](../bach-toccata.md#accepted-faster-opening) pins the listening files, hashes and exact scope. This is performance timing, not an audio time-stretch or a reconstruction of an organist's tempo.

## Native dependencies and useful variations

The demonstrated palette uses three MOS8580 PAL voices: moving-pulse lead, pulse bass with sole ownership of the shared low-pass filter, and triangle/pulse harmonic support. A selective diminished pitch cycle implies several chord tones on one oscillator. It does not sustain independent chord tones. PWM continues at the player's update rate; shortening a musical hold changes how much of the program is heard without requiring a faster pulse sweep.

Adjust statement length, breathing space and running-note speed independently. Leave more space where a harmonic arrival benefits from it; tighten transitions where silence interrupts momentum. Preserve enough native ticks for onset and full pitch: the [native timing constraint](../../../songs/fuer-elise-native.md) still applies. An organ-like envelope does not make short retriggered SID notes equivalent to tied organ notes.

## Failure cases and review

Long diagnostic holds can expose sound-program motion yet weaken a performance. Dense chord cycling can obscure a moving inner line; keep that line explicit when it carries the cadence. Conversely, removing all breathing can erase the phrase's dramatic shape. Judge the complete transition in context, with the original score/performance available, and record intentional timing and voicing changes separately. No drums or extra chip are required by this gesture.
