# Für Elise: existing SID comparison

DRAX's archived arrangement provides an independent comparison for [our native candidate](../../fuer-elise-native.md). The comparison checks actual pitches, timing and synthesis behaviour; the existing SID is not the authority for Beethoven's notation or our source-preservation contract. That authority remains [the original source and documented reduction](../../fuer-elise-score.md).

## Provenance and playback

[HVSC's `MUSICIANS/D/DRAX/Worktunes/Fuer_Elise.sid`](https://www.hvsc.de/download/C64Music/MUSICIANS/D/DRAX/Worktunes/Fuer_Elise.sid) is identified as Beethoven's Für Elise by [STIL](https://www.hvsc.de/download/C64Music/DOCUMENTS/STIL.txt). Its SID header credits `Thomas Mogensen (DRAX)`, `1990 Vibrants`. The 10,528-byte file has SHA-256 `ea6b7eba46844d399e415368eae86c3ddf03bd9041ecba93e7bb53b384daa2a1`. It is PSID v2NG, one subtune/default 1, PAL VBI, one 6581, load `$0f00`, init `$1000`, play `$1003`. [Pinned sidid signatures](https://github.com/cadaver/sidid/blob/9f0cb6895a84232c59b1fa761424f4a42115e855/sidid.cfg) identify the JCH NewPlayer family; no original editable workfile was verified. See the [Flashdance reference](flashdance-reference.md) for the STIL pin, signature pin and archive reuse boundary.

The existing renderer produced a non-silent, unclipped reference render, and the strict RAM-only CPU auditor accepts this file. Reference binary, audio, trace and analysis live only under ignored `.local/research/fuer-elise/`. No listening or hardware quality verdict follows from these checks.

## Actual opening comparison

Reference melody events are recovered from voice 2's transition from TEST to a gate-open pitched waveform. Our melody is checked at voice 1's full-pitch body frame, one PAL call after its scheduled onset, against the actual rendered candidate's CPU frames and its source manifest. Pitch is decoded using the PAL clock and rounded to MIDI identity; driver-specific frequency-table bytes are not expected to match exactly. This method establishes the opening pitch comparison, not a universal SID-to-score transcription.

| Aspect | Reference versus our native candidate | Consequence |
|---|---|---|
| Opening melody | The first 31 consecutive notes match, starting E5, D-sharp5, E5, D-sharp5, E5, B4, D5, C5, A4. | The recognizable theme is independently confirmed in the actual player output. This does not establish full-form equivalence. |
| First pitch discrepancy | Zero-based melody event 31: reference D4/MIDI 62, our E4/MIDI 64 at source beat 10.25. The original LilyPond source explicitly gives `r16 e' c'' b'` here. | Retain the source's E4. A different archived arrangement is not evidence of a conversion bug. |
| Tempo and relative rhythm | The reference's opening sixteenth intervals are 12 PAL calls, equivalent to approximately quarter = 62.66; ours follows source quarter = 72 using 10/11 calls. The opening A4-to-C4 spacing is 36 reference calls against 31/32 native calls, representing the same three-sixteenth span at different tempos. | Align by musical beat and pitch sequence when checking preservation. Equal elapsed time does not imply equal phrase position. |
| Articulation | Reference melody preparation uses TEST/gate-off `$08`, then TEST/gate-on `$09`, then pulse `$41` two calls after preparation. Our pluck uses one TEST `$09` frame, a saw `$21` body attack and triangle `$11` continuation. | Compare attack delay, waveform sequence and gate duration separately. Matching notes does not require identical articulation. |
| Voice allocation | Reference voices 1/2/3 carry percussion/bass, melody and chord arpeggiation. Ours uses melody, bass and independently scheduled harmony. | A reference can suggest oscillator sharing, but cannot determine the correct reduction of our complete polyphonic source. |

The 6,000-call reference trace contains two complete identical 123-note melody cycles and a matching partial third cycle, spaced by 2,016 PAL calls (approximately 40.22 seconds). Our F-major and repeated-bass episode opening landmarks do not occur in that trace. The verified comparison therefore covers returning thematic material and its texture, not the complete source form. An archived title match must never be used to assume complete arrangement coverage; establish the reference's repeated sections and episode landmarks before extending differential assertions.

## Reusable sound-design findings

The reference pulse melody resets near width 2128 on attack and then moves through its body; it differs substantially from our brief bright attack and triangle continuation. The reference's bass voice combines a high-frequency noise transient with a low pulse body, routes only that voice into a resonant low-pass filter, and clears gate shortly after the body begins. Our current recipe has a restrained filtered bass without that percussion attack. These are explicit texture choices to audition, not missing melody notes.

The reference's third voice combines triangle and pulse (`$51`) and cycles A3, C4 and E4 every two calls at the first accompaniment entry. Our harmony presents selected source notes individually. Combined waveforms and fast arpeggios are useful options for fuller harmony on one SID; their chip-dependent timbre and extra pitch motion should be evaluated in controlled original patches before adoption. They also show why static frequency comparisons and one snapshot per score event are insufficient for expressive SID instruments.

## Reproduce and audition

Use an unused output filename; [renderer setup](../../audio-workflow.md) provides the required tool:

```sh
mkdir -p .local/research/fuer-elise
curl -fL https://www.hvsc.de/download/C64Music/MUSICIANS/D/DRAX/Worktunes/Fuer_Elise.sid -o .local/research/fuer-elise/drax-fuer-elise.sid
shasum -a 256 .local/research/fuer-elise/drax-fuer-elise.sid
PYTHONPATH=.tools/test-deps python3 scripts/psid_audit.py .local/research/fuer-elise/drax-fuer-elise.sid --ticks 1000 --output .local/research/fuer-elise/drax.audit.json
.local/bin/render-sid .local/research/fuer-elise/drax-fuer-elise.sid .local/research/fuer-elise/drax.preview.wav 20
```

The prepared [opening A/B WAV](../../../.local/research/fuer-elise/opening.ab.wav) contains A = DRAX's 6581 reference, a half-second separator, then B = our 8580 native candidate. Each excerpt is 20 seconds from renderer time zero, at the original tempo and declared SID model; startup timing and the resulting phrase-position difference remain audible. [The comparison manifest](../../../.local/research/fuer-elise/opening.comparison.json) records source WAV hashes and attenuation, and [the register analysis](../../../.local/research/fuer-elise/opening.analysis.json) records the matching notes and discrepancy. Both inputs are unclipped and matched by AC RMS with peak headroom; this is not a guarantee of equal perceived loudness.

For a new candidate, regenerate the [native song](../../native-song-workflow.md), retain its source manifest and actual frame/write trace, and prepare fresh excerpts with [the level-matching workflow](../../instrument-trials.md). Keep preservation checks against our source, arrangement comparison against the identified reference, and user listening judgments separate. Full-form reference alignment, the reference's notation/source reconstruction and comparative listening remain unestablished; exact PCM equality between these different players and chip targets is not a success criterion.
