# Transfer the decoded bass to our Für Elise arrangement

This experiment applies the [independent DRAX bass mechanism](../drax-bass-reconstruction/README.md) to the listener-preferred [original interpretation B](../fuer-elise-interpretation/README.md). It retains our melody, finite chord bursts and seven bass note starts; no DRAX accompaniment, driver or captured-event replay is included.

## Listen

[A then B](../../../build/elise-decoded-bass-listen/bass.ab.wav): 4.5 seconds of the previous bass, a half-second gap, then the independently programmed bass in the same arrangement. Separate clips: [A](../../../build/elise-decoded-bass-listen/a.wav), [B](../../../build/elise-decoded-bass-listen/b.wav). Bass enters around 1.7 seconds within each clip. Does B give the bass more movement and presence while fitting the melody?

Both sides use PAL MOS6581 and one common gain, currently unity. The earlier preferred interpretation used MOS8580, so A is a controlled rerender rather than that earlier WAV. The listener reports that B is “much better”, but still not close to the richness of **2.02–2.75 seconds in [DRAX's reference.opening.wav](../../../build/reference-studies/drax/reference.opening.wav)**. This accepts an improvement over A, not attainment of the reference sound.

## Transfer finding: preserve time for the sound to develop

The executed traces expose a lost part of the instrument's motion. DRAX initializes the bass on call 100, reaches PWM `$F10` at call 129 and then sweeps downward while retaining the same pitch and releasing envelope. Our first note initializes on call 84, but preparation for the next note interrupts it on call 113: at age 29, where DRAX reaches the turnaround, our hard restart changes AD/SR to `$0F/$00`. At age 30 our TEST reset replaces the pitch; the next attack restarts PWM. Through age 28, the aligned attack/body control, ADSR, cutoff and pulse widths agree; the pitched frequency differs by one SID word (`936` versus `937`). The [reference writes](../../../build/reference-studies/drax/fuer-elise.writes.json) and [transfer writes](../../../build/elise-decoded-bass-listen/b.writes.json) retain the evidence.

Reusing the instrument parameters alone therefore does not preserve its complete audible evolution: note spacing and retrigger preparation belong to the sound-design contract. This is a demonstrated programming difference, not proof that it alone explains the listener's richness judgment; accompaniment and balance also differ. The [corrected phrasing policy](phrasing.json) retains roots at beats 2, 3.5 and 5 while removing the intervening bass answers. [The new comparison](../../../build/elise-bass-phrasing-listen/bass.ab.wav) presents the seven-note decoded bass first, then the same instrument with three roots; companion parts and sound parameters remain fixed. Listening judgment is pending.

Pass `--phrasing songs/studies/elise-decoded-bass/phrasing.json` to the transfer command below. The guard checks ordered instrument writes and states against uninterrupted single-note execution through age 36. Both complete root windows retain the PWM turnaround and descent; the final root has only 16 observed calls before the excerpt stop and is explicitly marked truncated. This preserves the selected reference window, not a complete PWM oscillation. The [three-voice reconstruction](../drax-full-reconstruction/README.md) separately reproduces DRAX's actual phrasing and accompaniment from our own code.

## Reuse and reproduce

After [native setup](../../../docs/workflows/native-song-workflow.md), run into a fresh directory:

```sh
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 scripts/transfer-drax-bass.py songs/studies/fuer-elise-interpretation/recipe-b.json --output build/elise-decoded-bass-listen/new --vice
PYTHONPATH=.tools/test-deps python3 -m unittest discover -s tests -p drax_bass_transfer_test.py -v
```

The [tool](../../../scripts/transfer-drax-bass.py) reuses the retained arrangement/export pipeline and decoded assembly. It obtains exact bass frequency words from executed native body frames and retains their note-start calls. The generated `bass.recipe.json` describes the source mechanism; `study.json` records its adaptation to hardware voice two, `$D407–$D40D`, filter routing `$F2`, and assembly at `$8000`. Editable parameters remain owned by the [instrument recipe](../drax-bass-reconstruction/instrument.json).

The musical change is the complete bass articulation: noise attack, broad computed PWM, bass-only filter and early GATE closure with continuing release. Original score gate lengths are intentionally replaced. Preserve this distinction when transferring the mechanism to another song.

## Evidence and boundaries

The CPU guard preserves all 3,164 companion writes and matches 1,738 independent bass writes over 226 musical calls. Headless VICE independently matches 4,914 runtime stores through 229 calls, including the explicit stop. The five-second full renders have quiet final 200 ms; the shorter audition excludes that ending. The maximum combined call uses 2,901 of 19,656 PAL cycles. Companion stores move by 31–463 cycles within a frame; exact phase or hardware equivalence is not claimed.

The reusable result is an editable instrument algorithm plus a guarded transfer procedure. This integration is deliberately bounded to the pinned Extra writer, voice-two bass, one PAL 6581 and a short opening. It rejects companion filter ownership and oscillator coupling. It is not yet a selectable instrument in the general song compiler, a complete-song exporter or a dual-SID adapter. Once its musical suitability is established, integrate the mechanism into that workflow with explicit voice/filter allocation and phrase-spacing constraints so Flashdance can select it instead of requiring another song-specific binary patch.

Detailed provenance, patches, timing evidence and rendering receipts remain in [generated evidence](../../../build/elise-decoded-bass-listen/study.json).
