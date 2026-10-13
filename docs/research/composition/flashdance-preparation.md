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

## Executed feasibility findings

A bounded execution study of the pinned binary identifies requirements beyond the Elise backend:

| Mechanism | Executed evidence and consequence |
| --- | --- |
| Same-call restart | Instrument initialization writes AD `$00`, SR `$0F`, TEST `$08` at PCs `$12D3/$12D8/$12DD`, followed by actual ADSR and TEST/GATE `$09` at `$1374/$1380/$1385`. Do not impose Elise's two preceding preparation calls. |
| Different body writer | PCs `$15F7–$1618` write pulse width, shared cutoff, frequency and control. ADSR belongs to initialization rather than being reasserted every body call. |
| Staged lead | Instrument offset `$10` selects AD/SR `$03/$3C`, triangle→saw→pulse stages and a looping body. PWM begins at `$D00`, bounds high `$A/$F`, step `$70`; a later row changes the step to `$10` without resetting width. Preserve row transitions and state, not just extrema. |
| Moving chord variants | Initializers at calls 2/130/258/386 select four chord programs. The opening has offsets `[0,0,4,4,7,7,12,12]`, AD/SR `$03/$34`, width `$040` and step `$0D`. Describe the four-tone cycle independently from the score note. |
| Per-voice fine tuning | PC `$14FB` adds the table `$1762,X` value: 0/1/2 for bass/lead/chord. The opening lead `$2710` becomes `$2711`; chord `$0F82` becomes `$0F84`. Preserve the exact programmed words alongside their musical interpretation. |

These are decoded local execution observations, not independent synthesis or listening acceptance. The first four-chord turn, calls 0–513, is the [plan's first reconstruction milestone](../study-plan.md#flashdance-next-executable-milestones). Continue through waveform/pitch tables `$187B/$197B`, PWM rows read at `$1399–$13DD`, movement `$13E0–$141A`, and score reader `$114B`; the existing pinned diagnostic adapter retains the production auditor's strict I/O boundary.

## Description → library → our code

Decode one chosen phrase from initialization, including silent preparation. Retain exact frequency words, initializer/off calls, attack stages, PWM arithmetic, vibrato phase/delay, arpeggio dwell, release evolution and shared-filter write order. Keep score events separate from instrument-owned gate closure. Promote each verified mechanism into an editable library card with provenance, constraints, demonstration and listening verdict; then implement it in our computed engine. Include neither the original driver nor captured-register playback. Require ordered-write equality and independent VICE execution for the single-SID reconstruction before arrangement changes.

## Deliberate dual-SID interpretation

Target two PAL MOS6581s at `$D400/$D420`, following [the address and validation contract](../sid/dual-sid.md).

- Chip A retains the reference roles: bass/percussion, lead and chord cycle. Bass alone owns its filter; companions remain unfiltered.
- Chip B adds separately authored drum accents, sustained harmonic support and selective answering phrases. Harmonic support alone owns its filter; added notes and timing are explicit arrangement decisions.

Validate six-voice addressing, independent filters, CPU budget, stereo/mono balance and both chips' ending. Compare the verified three-voice reconstruction with the expanded interpretation using common gain; record listening separately from execution. A source MIDI/MusicXML is required only if preserving the original song's form beyond DRAX's arrangement is requested.
