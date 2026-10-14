# Deflektor tonal programs on familiar Für Elise material

This experiment transfers three executed Deflektor pulse patches to the same 53 source notes from beats `[0,12)` of the preserved [Für Elise score](../../fuer-elise.json). The [mapping](mapping.json) selects the patches and provisional ending; [transfer.json](transfer.json) and [reference.json](reference.json) are independently editable computed-player descriptions. The plain reference uses the source score's triangle/envelope settings with the same notes, native pitch words, scheduling and gate times. Both are generated performances, not recordings of Beethoven or Deflektor. The listener accepted the instruments, balance and ending on 2026-10-14; see [the exact verdict](listening-review.json) and [instrument card](../../../docs/research/composition/instruments/deflektor-decoded-programs.md).

## Selected programs and musical roles

The [source study](../../../docs/research/composition/deflektor-preparation.md) owns attribution and execution evidence. Patch parameters come from the portable [title description](../deflektor-reconstruction/title.json), whose numeric record/program sources remain linked in its provenance. The retained [field lookup](../../../evidence/deflektor-programs/verified-final/lookup.json) names each field and its executed reader. The preparer verifies that each selected record occurs at its declared source note context; no original SID is needed.

| Destination role / SID voice | Source record / original zero-based voice / note call | Nine-byte source fields / contextual tenth selector | Reused behavior |
| --- | --- | --- | --- |
| Melody / 1 | 6 / 0 / 2010 | `24 08 41 0A 0A 02 3F 08 00` / `03` | Pulse interval 4, unshifted table base `$20`, low-byte step `$3F`, delayed full-word pitch motion |
| Bass / 2 | 3 / 1 / 0 | `0C 08 41 05 69 02 15 00 00` / `03` | Pulse interval 12, base zero, low-byte step `$15`, sustain 6 and release 9 |
| Harmony / 3 | 7 / 1 / 5480 | `03 08 41 09 0A 02 55 00 00` / `03` | Pulse interval 3, base zero, low-byte step `$55`, zero sustain and release 10 |

The contextual tenth selector is explicit even though records advance by nine bytes. It is the next source record's first byte in the title layout and selects the shared resonance program. Extracting just nine bytes would lose a synthesis input. All chosen patches have no waveform macro and no SYNC/RING dependency; the staged percussion candidate remains outside this first tonal transfer. Its cowbell identity is unresolved.

Record 6's PWM base `$20` and delayed-pitch selector 8 share motion cells 32–39. Keep the complete aliased numeric view, rather than truncating a pulse table at an apparent boundary. Its pitch program waits 30 eligible continuing-body invocations, then applies signed frequency-word steps `+100,+100,+100,-100,-100,-100,0`; the following pass reverses signs. These are raw frequency increments, with note-dependent cents, rather than semitone vibrato. Only the final one-beat melody A4 is long enough to reach that delay in this excerpt; the original delay is retained on short notes.

## Why use the computed player

The [Deflektor runtime](../../../scripts/deflektor_player.py) and [sound components](../../../scripts/deflektor_programs.py) preserve source target/marker arithmetic, low-byte-only pulse addition/subtraction, caller suppression, release ordering and shared resonance ownership. Pulse low-byte carry/borrow never changes the high byte between targets. Base-zero patches retain pulse phase on ordinary new notes; base `$20` resets on each note. Global row boundaries can suppress a whole body's advancement and output, and native rests bypass continuing sound.

SID-Wizard can represent pulse waves, envelopes, waveform tables, delayed modulation and retained pulse phase. Its pinned [`PWSWEEP` implementation](../../../.tools/sid-wizard-1.97/native/sources/include/player.asm) propagates signed low-byte movement into pulse high, while `STRTSND` and the normal TEST first frame also have a different onset contract. A direct native sweep translation would change these source patches' downward segments. Explicit per-frame tables could encode a fixed pulse trajectory, but would replace the original marker/target algorithm and still not preserve its caller interaction. The computed route therefore keeps these particular programs faithful; this does not imply that native instruments are unsuitable for other musical purposes. See [the native workflow](../../../docs/workflows/native-song-workflow.md) and [its verified onset constraint](../../../docs/songs/fuer-elise-native.md#timing-and-verification-boundary).

The source's resonance updates remain ordered and editable, but routing low bits and filter modes stay zero here. No audible moving-filter contribution is claimed. Source score arpeggios, glide and detune are disabled to retain the familiar source notes. Cold software shadows are explicit starting inputs, not proof of hardware oscillator phase or the original game's boot state. Voice reassignment and a fresh patch entry do not preserve the original passage's starting phase.

## Score, articulation and ending contract

The retained [preparation report](preparation.json) lists every source event, absolute quantized onset/end, signed tuning deviation and input/output hash. All 35 melody, 6 bass and 12 harmony notes and source gaps are retained. Native note tokens are `midi - 32`; note setup adds 20, so the frequency index is `midi - 12`. Actual first sounding register words independently decode to the source MIDI pitches. This phrase's native PAL tuning spans −0.9798 to +0.4020 cents from A440 equal temperament; the report owns the precise values.

Absolute source beat boundaries round to PAL calls with a maximum error of 9.81345 ms. Row setup happens at the quantized onset, while global row-boundary suppression can defer audible output by one call, approximately 19.95 ms. Release threshold 2 clears GATE one call before each original note end. Native rests explicitly write control zero; their waveform cutoff differs from a gate-only release. ADSR restart fidelity, per-voice audibility and musical articulation require separate listening evidence.

The final rows deliberately extend to a shared stop while their copied patches raise only the release-threshold field, preserving the original gate-off call. Pulse and delayed-pitch programs continue during the final release. Selecting each copied patch also restarts base-zero bass/harmony PWM at the final onset; ordinary earlier notes retain phase. Melody record 6 already resets on every note. No added pitch onset, master-volume fade or shortened envelope is introduced. The delayed melody program continues during release; this submitted ending is accepted.

The source phrase ends at call 501. The 151-call release extends to the global stop at call 652, followed by 64 no-store confirmation calls. Both descriptions declare 717 play calls and 14.304361 seconds of PAL audio. The release window after the source phrase is `[9.995098,13.007592)` seconds; the post-stop window is `[13.027542,14.304361)` seconds. The [rendered pre-stop window](../../../evidence/deflektor-elise-transfer/pre-stop-tail.json) is already quiet in both versions before the control-zero stop; the recipe also verifies the final post-stop second. The listener accepted the ending. The separate [instrument card](../../../docs/research/composition/instruments/deflektor-decoded-programs.md) owns current execution/audio evidence and musical scope.

## Reproduction and current verification

Regenerate or check the portable descriptions with the pure preparer, then compile through the independent player:

```sh
python3 scripts/studies/deflektor/prepare-elise-transfer.py --check
python3 -m unittest discover -s tests -p 'deflektor_transfer_test.py' -v
python3 scripts/listening-package.py config/listening/deflektor-elise-transfer.json --output build/deflektor-elise-transfer
```

The preparation tests independently check all source pitch/onset pairs, first sounding pitch words against A440 MIDI pitch, every gate-off, unchanged native patch fields and contextual selectors, matched plain-score navigation, final-row release continuation, finite stopping, deterministic saved data and file-free runtime computation. They reject coupled patches, missing records, overlapping/crossing notes, unrepresentable short notes and a release row exceeding the native byte duration. CPU/VICE compilation, rendering and musical judgment are separate checks; no listening verdict follows from preparation.

Model assistance is not used to select or accept these instruments. Numeric evidence supports the transfer mechanism and independent pitch checks; model inference about musical usefulness remains experimental. The first-audition and feedback reviews are recorded in the [instrument card](../../../docs/research/composition/instruments/deflektor-decoded-programs.md); the next checkpoint is Daglish case closure or a substantive revision.
