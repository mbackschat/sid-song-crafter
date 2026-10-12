# Independent DRAX bass reconstruction

This is an editable reconstruction of the bass program in DRAX's preferred 2.02–2.75-second Für Elise passage. [instrument.json](instrument.json) owns the decoded patch and the pinned A1 note. [player.asm](player.asm) is a new 6502 implementation with its own note scheduler, attack stages and pulse state. It does not embed DRAX's driver or replay a register dump. [transfer.json](transfer.json) inherits the same patch and applies it to A1 and E2, demonstrating that pitch and note placement remain editable.

The reconstruction basis is the [executed program study](../../../docs/research/tools/sid-program-analysis.md), including the RAM operand trace and independently checked VICE stores. The archived source is DRAX's single PAL MOS6581 PSID, SHA-256 `ea6b7eba46844d399e415368eae86c3ddf03bd9041ecba93e7bb53b384daa2a1`, at `.local/research/fuer-elise/drax-fuer-elise.sid`. Composer attribution, source provenance and listener judgments remain in the [reference study](../../../docs/research/composition/fuer-elise-reference.md). The original binary is not included here or copied into reconstruction outputs.

## Instrument contract

The scheduler calls one voice-one instrument per PAL frame. A note's `initCall` follows two setup calls; GATE closes three calls after init, as part of the instrument rather than a later score note-off. Consecutive init calls must be at least six calls apart so the next hard restart cannot suppress the preceding instrument's gate closure. Each body call computes pulse width by adding or subtracting an editable step, reverses direction when its high byte equals a declared bound, and retains the pulse waveform while the envelope releases. The shared filter belongs to bass. Frequencies in the recipe are SID words, not MIDI note numbers.

| Relative call | Bass action |
| --- | --- |
| Init − 2 | Write hard-restart AD/SR `$0F/$00`. |
| Init − 1 | Write the note's frequency, AD/SR `$00/$00` and TEST `$08`. |
| Init | Initialize internal PWM to `$600`, select routing/resonance `$F1`, write AD/SR `$02/$CA` and TEST plus GATE `$09`. The internal width is not written until the next call. |
| Init + 1 | Advance PWM to `$650`; write high-frequency noise `$C4E0`, cutoff `$780`, control `$81`. |
| Init + 2 | Advance PWM to `$6A0`; write the note's pitch, cutoff `$040`, pulse plus GATE `$41`. |
| Init + 3 onward | Keep the pitch and pulse waveform, close GATE with `$40`, continue PWM through release. |

The main PWM step is `$50`, with lower/upper high-byte bounds `$01/$0F`. The peak is `$F10` at source call 129, followed by subtraction. The silent bass prehistory uses the same arithmetic with bounds `$04/$04`, initial width `$4C0` and downward direction; it alternates `$470/$4C0` until the note setup. Its three introductory frequency stages are retained even though GATE is off. TEST resets the bass oscillator before the selected attack. Companion voices are excluded from the reconstruction.

The player explicitly silences master volume when `playCalls` is reached, so a host that continues calling play does not leave the study audible indefinitely. The transfer recipe includes this ending in its render. `reconstructed.prg` is a load-address-prefixed callable payload; it has no BASIC launcher or standalone interrupt installation.

## Reproduce and edit

After the repository's [dependency and renderer setup](../../../docs/audio-workflow.md), run from the repository root into fresh output directories:

```sh
PYTHONPATH=.tools/test-deps python3 scripts/reconstruct-drax-bass.py songs/studies/drax-bass-reconstruction/instrument.json --reference .local/research/fuer-elise/drax-fuer-elise.sid --output build/drax-bass-reconstruction --vice
PYTHONPATH=.tools/test-deps python3 scripts/reconstruct-drax-bass.py songs/studies/drax-bass-reconstruction/transfer.json --output build/drax-bass-reconstruction/transfer --vice
PYTHONPATH=.tools/test-deps python3 -m unittest discover -s tests -p drax_bass_reconstruction_test.py -v
```

Change `notes` to move or transpose the phrase; edit the `instrument` fields to change its mechanism. `transfer.json` overrides only the score and render window, keeping the patch in one place. The builder uses py65's assembler for the small handwritten program, resolves labels, rejects branch overflow and emits a readable listing. The build needs no original SID. Passing `--reference` separately audits and renders the archived reference for comparison; a deliberate patch change should omit that option because exact register equality is then no longer the success criterion.

| Output | Purpose |
| --- | --- |
| [reconstructed.sid](../../../build/drax-bass-reconstruction/reconstructed.sid) | Independent PAL MOS6581 PSID. |
| [reconstructed.exact.wav](../../../build/drax-bass-reconstruction/reconstructed.exact.wav) | Original-time 2.02–2.75-second reconstruction, with complete initialization before the cut. |
| [bass.ab.wav](../../../build/drax-bass-reconstruction/bass.ab.wav) | AC RMS matched A/B: diagnostic reference bass, a half-second gap, reconstruction. |
| [bass.a.matched.wav](../../../build/drax-bass-reconstruction/bass.a.matched.wav), [bass.b.matched.wav](../../../build/drax-bass-reconstruction/bass.b.matched.wav) | Separate matched comparison copies. |
| [transfer/reconstructed.exact.wav](../../../build/drax-bass-reconstruction/transfer/reconstructed.exact.wav) | Same instrument on the editable A1/E2 phrase. |
| [register-comparison.json](../../../build/drax-bass-reconstruction/register-comparison.json), [vice/study.json](../../../build/drax-bass-reconstruction/vice/study.json) | Ordered register projection, frame-state equality and independent execution guard. |
| [pcm-comparison.json](../../../build/drax-bass-reconstruction/pcm-comparison.json), [study.json](../../../build/drax-bass-reconstruction/study.json) | Secondary PCM measurements, provenance, renderer identity and evidence limits. |

## Verified boundary

On 2026-10-13, the independent 546-byte 6502 payload matched 1,209 projected writes and all bass/global frame states through 151 calls. The projection preserves each bass write and global filter/volume writes, while retaining only the last `$D416` store in each call. DRAX's companion writer slots repeat the preceding cutoff before bass updates it; their omitted timing matters at transitions and is not reproduced. VICE independently checks every reconstructed play call against the CPU audit, including the setup and prehistory. Focused tests execute the generated 6502 code and cover setup/attack/release, PWM reversal, two editable pitches, finite ending, valid earliest note initialization, prevention of overlapping setup/release and out-of-range PWM, and a comparison guard that rejects a changed GATE value.

The PCM is not sample-identical. [pcm-comparison.json](../../../build/drax-bass-reconstruction/pcm-comparison.json) retains measurements of the unshifted raw renders before amplitude matching; there is no offset search or phase correction. The new scheduler writes earlier within each call, and companion oscillator history, exact noise phase and analog state are not reproduced. Same register values do not establish sample equality. The diagnostic reference masks the other voices' waveform/GATE controls and is not an additive audio stem.

The listening question is whether the independently generated bass preserves the character heard in the reference. The A/B and transfer files are ready for that judgment; no listening acceptance, exact analog reconstruction or hardware fidelity is claimed.
