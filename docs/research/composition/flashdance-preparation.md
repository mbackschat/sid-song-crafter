# Flashdance preparation

Use DRAX's **Flashdance (conversion)** as the next reference for **What a Feeling**. Its staged lead, evolving bass and moving chord extend the mechanisms learned from the positively received [independent Elise trio](../../../songs/studies/drax-full-reconstruction/README.md). This makes it a useful study candidate; musical preference is still pending. Audition the existing [20-second preview](../../../.local/research/flashdance/drax.preview.wav) before choosing the first phrase to reconstruct.

## Pinned evidence

The [reference study](flashdance-reference.md) owns attribution, cached [HVSC STIL](https://www.hvsc.de/download/C64Music/DOCUMENTS/STIL.txt) identity and the [archived SID](https://www.hvsc.de/download/C64Music/MUSICIANS/D/DRAX/Worktunes/Flashdance_conversion.sid): DRAX, `1990 Vibrants`, one PAL MOS6581, default subtune 1. Pinned local SHA-256: `2f5216ab8f4438d8ef20c0153ce4671afbc5bc6e66d3b0984bb112fdbf46794c`.

The retained [frames](../../../build/reference-studies/drax/flashdance.frames.json) and [ordered writes](../../../build/reference-studies/drax/flashdance.writes.json) cover 6,000 calls. Their diagnostic adapter permits only the pinned initialization's two zero paddle-register writes; this is not a production-auditor pass or a complete-song coverage claim.

| Opening observation | Difference from decoded Elise |
| --- | --- |
| Bass: TEST at call 2, noise `$C4E0/$81` at 3, pitched pulse at 4, gate clear at 5; AD/SR `$02/$5F`; width advances `$40`. Cutoff descends 1280→832→512→384→256. | Different envelope, narrower step and several filter stages; retain the releasing body. |
| Lead: triangle at 3, saw at 4–5, pulse from 6. Width rises `$70`, reverses, then changes to `$10` descent at 12. Pitch first moves by 79 at 30. | Waveform staging and changing PWM rate replace the simple pulse lead; modulation needs its own decoded contract. |
| Chord: B-flat3/D4/F4/B-flat4, two calls per tone, plain pulse and width movement `$0D` per opening call. | Four-tone moving pulse replaces the fixed-width triangle/pulse triad. |

These are measured trajectories, not recovered algorithms. Trace the responsible instructions and RAM operands before identifying bounds, delays, reset rules or reusable parameters.

## Description → library → our code

Decode one chosen phrase from initialization, including silent preparation. Retain exact frequency words, initializer/off calls, attack stages, PWM arithmetic, vibrato phase/delay, arpeggio dwell, release evolution and shared-filter write order. Keep score events separate from instrument-owned gate closure. Promote each verified mechanism into an editable library card with provenance, constraints, demonstration and listening verdict; then implement it in our computed engine. Include neither the original driver nor captured-register playback. Require ordered-write equality and independent VICE execution for the single-SID reconstruction before arrangement changes.

## Deliberate dual-SID interpretation

Target two PAL MOS6581s at `$D400/$D420`, following [the address and validation contract](../sid/dual-sid.md).

- Chip A retains the reference roles: bass/percussion, lead and chord cycle. Bass alone owns its filter; companions remain unfiltered.
- Chip B adds separately authored drum accents, sustained harmonic support and selective answering phrases. Harmonic support alone owns its filter; added notes and timing are explicit arrangement decisions.

Validate six-voice addressing, independent filters, CPU budget, stereo/mono balance and both chips' ending. Compare the verified three-voice reconstruction with the expanded interpretation using common gain; record listening separately from execution. A source MIDI/MusicXML is required only if preserving the original song's form beyond DRAX's arrangement is requested.
