# Flashdance: What a Feeling reference

Use DRAX's archived conversion as a sound-design study and an independent arrangement comparison. HVSC's [STIL](https://www.hvsc.de/download/C64Music/DOCUMENTS/STIL.txt) identifies both files below as **What a Feeling [from Flashdance]**, performed by Irene Cara; this distinguishes them from the soundtrack's other songs and unrelated tunes called Flashdance. The SID author field credits the C64 arrangement, not the original song's authors.

## Reference identity and availability

| Reference | Exact HVSC path and download | SID header | Playback contract |
|---|---|---|---|
| Preferred study | [MUSICIANS/D/DRAX/Worktunes/Flashdance_conversion.sid](https://www.hvsc.de/download/C64Music/MUSICIANS/D/DRAX/Worktunes/Flashdance_conversion.sid) | `Flashdance (conversion)`; `Thomas Mogensen (DRAX)`; `1990 Vibrants` | PSID v2NG; one subtune, default 1; PAL VBI; one 6581; load `$0f00`, init `$1000`, play `$1003` |
| Historical alternative | [MUSICIANS/K/Kleimeyer_Paul/Flashdance.sid](https://www.hvsc.de/download/C64Music/MUSICIANS/K/Kleimeyer_Paul/Flashdance.sid) | `Flashdance`; `Paul Kleimeyer <?>`; `1983 Access Software Inc.` | PSID v2NG; one subtune, default 1; CIA timing; unspecified clock; one 6581; load/init `$7580`, play `$7587` |

The DRAX file is 11,513 bytes, SHA-256 `2f5216ab8f4438d8ef20c0153ce4671afbc5bc6e66d3b0984bb112fdbf46794c`. The Kleimeyer file is 7,102 bytes, SHA-256 `46c13ffda2741ad60448f43844bf90c56838a916b3b7802cb7ca34abc7211972`. Identity was checked against STIL v85, June 28, 2026, cached STIL SHA-256 `b1ef3584a5b3501e2bbd2ef056d6539a1bbee7933a7828537c3946c1b16cde43`. Keep the `<?>` uncertainty and the distinction between a header release credit and independently established history. [CSDb's Flashdance release](https://csdb.dk/release/?id=223559) also associates the Kleimeyer archive path with that music credit; it does not remove the SID header's uncertainty.

Byte signatures from [sidid's pinned configuration](https://github.com/cadaver/sidid/blob/9f0cb6895a84232c59b1fa761424f4a42115e855/sidid.cfg), SHA-256 `744bc58ed0688df7a7faa02695418211fc0504479d053e734183090638638012`, match `JCH_NewPlayer` in the DRAX file and `Master_Composer` in the Kleimeyer file. This identifies player families, not an available editable source. No original native song/instrument workfile or reuse license for either arrangement was verified. A runnable SID or demo disk is not a SID-Wizard workfile and must not be presented as one. [HVSC's copyright notice](https://hvsc.de/info) states that archive availability and author attribution do not grant reuse rights; retain these reference binaries and derived audio only in ignored local storage.

## Measured sound-design lessons

The DRAX reference produced a non-silent, unclipped 20-second preview through libsidplayfp 3.1.1/SIDLite. Register analysis below concerns the opening; the preview has not been heard or accepted by the user, and no hardware result is claimed.

| Observed program behaviour | Useful lesson for original patches |
|---|---|
| Voice 1 starts with TEST `$09`, then noise `$81` at frequency word `$c4e0`, then a low pulse body `$41`, followed by gate-off `$40`. Pulse width continues moving during release. | A single oscillator can carry a percussion transient and a pitched bass body. Compare attack and body separately; gate-off does not mean all synthesis has stopped. |
| Voice 2 begins with triangle `$11`, two frames of saw `$21`, then pulse `$41`. Pulse width moves continuously; pitch modulation begins after the opening hold. | An evolving lead combines waveform staging, PWM and delayed vibrato. Test each feature's trajectory and coupled controls instead of judging only its first register state. |
| Voice 3 cycles the opening chord's B-flat3, D4, F4 and B-flat4 pitches every two PAL calls while pulse width moves. | Rapid arpeggiation supplies chord information on one voice. Do not mistake macro pitch steps for new score notes or treat its PCM as a single static pitch. |
| `$d417=$f1` routes only voice 1 through the filter at resonance 15; `$d418=$1f` selects low-pass and volume 15. The opening cutoff moves through 1280, 832, 512, 384 and 256. | Filter routing is a voice-allocation decision. An unfiltered lead can remain clear while the bass/percussion attack changes colour; preserve the shared-register interaction when reproducing the idea. |

The strict [RAM-only auditor](../../../scripts/psid_audit.py) rejects the DRAX init's zero writes to `$d419/$d41a`, SID paddle registers rather than writable sound controls. A local diagnostic adapter that ignored only those two writes completed 6,000 PAL calls without other unsupported I/O or ROM access. That conditional trace is not a normal audit pass. Prefer the full C64 renderer for this reference; do not weaken the production auditor or force the CIA-timed alternative into VBI calls.

## Reproduce and compare

Use the [renderer setup](../../audio-workflow.md) and an unused output filename:

```sh
mkdir -p .local/research/flashdance
curl -fL https://www.hvsc.de/download/C64Music/MUSICIANS/D/DRAX/Worktunes/Flashdance_conversion.sid -o .local/research/flashdance/drax-flashdance-conversion.sid
shasum -a 256 .local/research/flashdance/drax-flashdance-conversion.sid
.local/bin/render-sid .local/research/flashdance/drax-flashdance-conversion.sid .local/research/flashdance/drax.preview.wav 20
```

The local [preview](../../../.local/research/flashdance/drax.preview.wav) and its `.registers.tsv` sidecar are study evidence, not tracked assets. DeepSID offers [the DRAX entry](https://deepsid.chordian.net/?file=MUSICIANS/D/DRAX/Worktunes/Flashdance_conversion.sid) and [the Kleimeyer entry](https://deepsid.chordian.net/?file=MUSICIANS/K/Kleimeyer_Paul/Flashdance.sid) for an external player view.

For our own arrangement, first preserve the supplied MIDI/MusicXML identity, repeat form, notes and timing, and list any deliberate voice reduction. That source is still pending. Then align named musical phrases with the reference and compare melody intervals, rhythmic proportions, register/octave placement, articulation, voice allocation and macro trajectories. Differences in key, tempo, form or accompaniment may be arrangement choices; inspect them before calling them losses. Compare static and moving variants of our original patches with the same note/envelope inputs, retaining the reference as a design example rather than copying its instrument bytes.

For audition, render fixed-duration excerpts at their declared chip models, keep original tempo and startup behaviour, and level-match with the [A/B workflow](../../instrument-trials.md). Record model differences explicitly: this reference targets 6581, while our current native bank targets 8580. Exact PCM equality is meaningful only for the same binary, subtune, emulator/version, chip/filter configuration and render origin. Different arrangements and players require musical/register comparison and a separate user listening judgment.
