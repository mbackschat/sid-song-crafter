# DRAX decoded trio: musical roles and SID mechanisms

**Scope:** DRAX's preferred 2.02–2.75-second Für Elise selection, reconstructed from initialization through zero-based calls 0–150 on one PAL MOS6581. The [reference study](../fuer-elise-reference.md) owns provenance and listening attribution; the [executed analysis](../../tools/sid-program-analysis.md) owns tracing methods and bass evidence. Addresses below refer to that pinned binary, not recovered composer symbols.

Use this mapping in both directions: choose a program for a musical purpose, or interpret a measured program as a candidate musical gesture. An audible effect alone does not uniquely identify its mechanism.

| Musical role / desired effect | Editable SID program | Reverse reading and phrase constraint |
| --- | --- | --- |
| Bass: punctuate the entrance, then develop a resonant low tail | A1 `$03A9`; noise `$81/$C4E0` at init+1, pulse `$41` at +2, gate-clear pulse `$40` from +3; AD/SR `$02/$CA`; PWM starts `$600`, moves `$50` per call, reverses on high-byte bounds `$01/$0F`; bass-only low-pass routing `$F1`, cutoff-high `$F0→$08` | A short transient becomes one evolving releasing oscillator. Bass release belongs to the instrument. Retain pulse motion and waveform through release; close retriggering suppresses its development. The [bass study](../../../../songs/studies/drax-bass-reconstruction/README.md) owns its executable patch and spacing contract. |
| Lead: articulate the familiar opening, then animate the longer A4 | Pulse `$41`, AD/SR `$03/$3B`; width starts `$800`, first body writes `$850`, then subtracts `$50`; high-byte reversal bounds `$01/$08`; ten body calls without vibrato, then an eight-call triangle with `$80` increments and extrema ±`$100` | Short E5/D-sharp5 repetitions restart before vibrato begins; the A4 hold develops pitch and width motion. The score closes GATE at call 110, retaining pulse `$40`; modulation continues during release. Preserve the hold when seeking this particular development. |
| Chord: suggest A minor beneath the lead with one voice | Combined triangle/pulse `$51`, AD/SR `$00/$6B`, fixed width `$600`; A3/C4/E4 words `$0EA3/$1168/$15EB`, two calls per tone; no ring/sync | Three time-shared pitches imply harmony, without three independent envelopes. The score closes GATE at call 110; `$50` and the pitch cycle continue. Keep its two-call dwell and MOS6581 target when comparing this texture. |
| Style: coordinated entrance with distinct kinds of motion | Initialize all three at call 100; body entrance at 101; bass releases at 103, companions at 110 | A stable low pitch, moving lead and repeating chord create different concurrent trajectories. Treat richness as a listening question; adding these mechanisms does not certify the style. |

## Proof and implementation

Bass readers `$126B/$1271` consume PWM data `$1AA5/$1AA6`; `$1340/$1372` consume its pitch/wave program. Lead initialization reads `$1AB2–$1AB9`: envelope, bounds, step, width and modulation pointer. `$19A6–$19A8=$0A,$03,$20` define delay, direction counter and shifted vibrato increment; PCs `$13C4–$1413` execute it. Chord pitch offsets `$16A6–$16AB=[0,0,3,3,7,7]` and waveforms `$17A6–$17AB=$51` loop through `$1340/$1349/$1372`. Score zeros `$2CCB/$2DCB`, interpreted at `$1176–$117B`, explain companion gate closure; it is not their instrument program's release command.

The independent [recipe](../../../../songs/studies/drax-full-reconstruction/instrument.json) supplies notes and modulation; [companions.asm](../../../../songs/studies/drax-full-reconstruction/companions.asm) computes state alongside our bass player. Its `scoreGateCloseAge: 10` encodes this passage's score note-offs. The build uses neither the original driver nor register-dump playback.

## History and evidence boundary

Retain silent prehistory before cutting audio. Source init gives lead PWM bounds `$04/$04`, replaced by `$01/$08` at its first instrument initialization. The reconstruction retains both sets of bounds and switches at instrument initialization; this silent state is part of the description, even though the short prehistory reaches neither boundary. Chord holds silent pitch `$022D`, pulse `$600` and control `$40` from call 2 until preparation at 99.

Body writers visit voices 3, 2, 1: pulse, cutoff, frequency, ADSR, control. Shared cutoff writes are `$08,$08,$F0` at 101 and `$F0,$F0,$08` at 102. On 2026-10-13, all 3,507 initialization/play writes matched by call, address, value and order; VICE independently verified execution. Within-call timing and PCM differ.

The listener attributed vibrancy to reference bass alone, liked bass plus chord, and accepted the earlier bass substitution in original accompaniment. The independent trio received positive feedback (“Nice”); perceptual indistinguishability has not been explicitly confirmed.
