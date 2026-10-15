# Preparing audio comparisons

Use [compare-audio.py](../../scripts/compare-audio.py) to inspect original PCM16 WAV renders and prepare an A/B audition with documented gain, preserve a selected window at unity gain, or sequence two complete renders at unity gain. It uses only the Python standard library and needs no player/event manifest, so native SID-Wizard instrument phrases and the repository player can share this measurement step. Retain the original-amplitude renders and their native workfiles as evidence. See [the sound-design repertoire](../research/composition/sound-design-repertoire.md) for musical acceptance questions and [the audio workflow](audio-workflow.md) for rendering.

```sh
python3 scripts/compare-audio.py inspect build/baseline-phrase.wav
python3 scripts/compare-audio.py prepare build/baseline-phrase.wav build/native-instrument-phrase.wav build/lead-01-ab --individual-copies
```

The filenames above are example inputs, not a claim that these renders already exist. Render the same complete phrase, including the same rests and tail duration, at the same rate and channel count. The `prepare` mode requires identical frame counts; it does not establish that notes, tempo, update cadence, SID model, alignment, or renderer settings agree. Record those source assumptions in the trial or [instrument card](../research/composition/instrument-card-template.md).

## Package a listening review

Use the [recipe runner](listening-package.md) when the same build/render/comparison chain will run again. It creates the listening index and retains input/output hashes and stage timings automatically; this guide owns the musical comparison contract.

Prepare the review before asking for feedback. Link actual filenames and state the reference variant, A/B order, passage times, duration and any gain changes. Use a representative 10–20-second phrase where that captures the musical question; include more context when necessary. For the initial reconstruction review, offer the phrase, ending and both full renders together. Add the transfer and its same-material reference when ready for their separate review:

| Role | Suggested filename for new output | Purpose |
| --- | --- | --- |
| Phrase A/B | `phrase-reference-then-ours.ab.wav` | Sound and phrasing in the same musical context, reference first |
| Ending A/B | `ending-reference-then-ours.ab.wav` | Source ending or loop continuation, reference first; an authored stop is a separate arrangement review |
| Full reference | `reference.wav` | Immediate access to the selected original, including enough tail to compare its behavior |
| Full candidate | `reconstructed.wav` | Complete declared form, with source continuation or an explicitly labelled authored ending |
| Transfer pair | `transfer/reference.wav` and `transfer/reconstructed.wav` | Familiar material from another composition, rendered plainly and with the reused sounds |

These names describe roles, not new files already generated. Preserve filenames already shared with the listener; link them under these roles instead of renaming or duplicating large renders. Use fresh output prefixes for revised audio and retain the accepted or pending version.

Match variant, subtune, clock, model and renderer settings, and render from initialization. Use unity-gain `window` below for aligned passages. It selects the same time interval in both inputs; it cannot independently align different ending times. For source-fidelity review, preserve the reference behavior throughout the comparison window, including any restart. Present an authored stop/fade as a separate arrangement variant; do not substitute its silence for reference material in the fidelity comparison. If the reference loops while that variant stops, label the reference restart and the authored ending explicitly. When no meaningful common window exists, provide separately labelled ending excerpts with exact source bounds and reproduction commands, or full files with listening timestamps; do not manufacture equivalence through undocumented trimming, padding or fades.

Before publishing a source-fidelity ending comparison, verify source behavior through the **end of both selected windows**, including any restart. A source-prefix check that ends before an authored stop cannot cover the remaining comparison. Use the source-continuation export for that review; keep a finite stop in a separately labelled arrangement audition. If the listener reports missing sound, map the A/B timestamp back to source time and check the affected interval for source activity versus candidate silence before extending a release. The [Monty correction](../research/composition/monty-preparation.md#correct-the-reference-continuation) and [Airwolf correction](../research/composition/airwolf-preparation.md#reference-continuation-correction) demonstrate why post-mute silence and pre-mute decay checks alone cannot settle source coverage.

Ask separately whether sound/phrasing is preserved, the ending works, and the transfer is musically useful. Name the familiar source phrase and reused sounds before asking for transfer feedback, and supply its same-material reference. For an optional original-composition exercise, explicitly label the music as newly composed; it has no original recording of the same phrase, so a standalone original is acceptable when that distinction is clear. When supplying the source tune to compare instrument character, label it as a timbral reference rather than a same-melody A/B. Always supply the reference alongside a generated reconstruction. Give the full reference and candidate links in the first request so an ending judgment never requires another request for the original. Full-form review remains required for completion, but routine revisions can target the affected passage. Record answered questions with their exact scope and do not ask them again without a relevant change.

Keep reference renders and every comparison containing reference audio outside Git and LFS. Retain reproducible commands, hashes, settings, gains and segment boundaries in the owning recipe; record listening judgments separately from immutable generated receipts.

## Verify a two-chip presentation

Apply the [hardware and mixing contract](../research/sid/dual-sid.md#plan-the-sound-hardware-and-the-mix-together): raw chip buses and the final stereo presentation are separate artifacts. For a fixed matrix, verify the actual quantized PCM against the source samples and declared coefficients, not only a receipt or output hash. A changed file with a refreshed hash can still implement the wrong mix. The [Rambo ensemble guard](../../scripts/studies/rambo/prepare-ensemble-listening.py) and [negative tests](../../tests/rambo_ensemble_listening_test.py) demonstrate this check across every output frame. Match the faithful reference's primary-bus coefficients to the candidate before any documented whole-clip level matching.

To check that added roles contribute signal, render an initialized baseline and one omission per role over a passage where those roles actually play. Preserve the same render settings and compare residuals. These are causal diagnostics, not exact isolated stems: shared filters, modulation and chip nonlinearities can change other sound when a voice is omitted. Nonzero residual energy proves a signal change, not audibility or musical value. Treat any energy review band as a case-specific warning, never a universal acceptance threshold or instruction to normalize each role separately. The [Rambo case](../../songs/studies/rambo-ensemble/README.md) records its bounded diagnostic coverage separately from full-arrangement proof.

## Compare an initialized window at original levels

Use `window` when the reference and reconstruction have different total lengths but contain the same desired passage:

```sh
python3 scripts/compare-audio.py window build/reference.wav build/reconstructed.wav build/phrase-ab --start-seconds 24 --end-seconds 36
```

Both inputs must have the same sample rate and channel count and contain the entire selected interval. Bounds are rounded to PCM frames, with the end exclusive. This mode copies the selected PCM exactly, with no gain, normalization, fades or resampling; it measures rail samples and silence without rejecting or altering them. The output contains A, a half-second gap by default, then B. `--gap-seconds` changes the gap. Matching time coordinates alone does not establish musical alignment; choose the passage from initialized renders and document the clock, chip, subtune and renderer.

The output prefix produces `.ab.wav` and `.comparison.json`. The receipt pins complete input hashes, requested seconds, actual frame bounds, window measurements, unity gain, exact A/gap/B segment boundaries and output hash. `listeningReview` remains null. Exclusive output creation and rollback follow the preservation contract below. [The Shades reconstruction recipe](../research/composition/shades-independent-audio.json) demonstrates this mode with a corrected reference and independent player. Comparisons containing reference audio stay outside Git and LFS.

## Sequence complete renders at original levels

Use `sequence` for a complete A/B audition when the inputs have different durations, such as a tempo revision:

```sh
python3 scripts/compare-audio.py sequence build/before.wav build/after.wav build/full-tempo-ab --gap-seconds 0.5
```

Both inputs must be nonempty PCM16 WAVs with the same sample rate and channel count. The output contains every frame of A, the explicit gap, then every frame of B. This mode preserves source PCM exactly at unity gain, including leading/trailing silence, DC and rail samples; it performs no matching, trimming, per-input padding, fades or resampling. The gap defaults to 0.5 seconds and is rounded to output frames. Use fresh output prefixes for revisions and state the source identities and A/B order when sharing the audition.

The output prefix produces `.ab.wav` and `.comparison.json`. The receipt pins complete input hashes and measurements, unity gain, exact A/gap/B segment boundaries and output hash. Different durations remain explicit in each input's `original.frames` and `original.durationSeconds`. `listeningReview` remains null. Exclusive output creation and rollback follow the preservation contract below; existing `prepare` and `window` modes retain their own duration and passage restrictions. Comparisons containing reference audio stay outside Git and LFS.

## Measurement and matching contract

The input contract is nonempty, uncompressed 16-bit PCM WAV with one or two channels. Inspection reports frames, sample rate, duration, absolute sample peak, peak dBFS, PCM rail counts, per-channel DC mean, raw RMS and AC RMS, and pooled raw/AC RMS. Amplitudes use signed PCM sample units; dBFS uses 32768 as the reference. `clippedSamples` counts values equal to −32768 or 32767. These rails conservatively indicate possible hard clipping; a count of zero cannot detect distortion or clipping that occurred before the PCM render.

AC RMS subtracts each channel's own mean before pooling channel power. This prevents a DC offset, including opposing offsets in stereo, from inflating the matching level. The measurement covers the entire input file, including silence and release tails. This is amplitude matching for a controlled phrase comparison; it is not a perceptual loudness measurement. A long quiet tail or different duty cycle can influence the result.

By default, preparation chooses a shared AC RMS no greater than either source's AC RMS and no greater than either source can reach with the requested peak headroom. Each file gets one positive scalar gain; channels keep their balance and polarity, and DC is scaled with the signal. The default reserves 1 dB of peak headroom using the conservative symmetric sample limit `min(32766, floor(32767 × 10^(−headroomDb/20)))`. Even zero requested headroom leaves one sample unit below the positive rail, so safe-target advice does not require creating rail samples. Gain never boosts either source in this mode. If transients or DC use the available peak range, both sources may be reduced below the quieter source's original RMS.

An explicit target allows amplification if both files can reach it safely:

```sh
python3 scripts/compare-audio.py prepare build/a.wav build/b.wav build/explicit-target --target-ac-rms-dbfs -24 --peak-headroom-db 2 --gap-seconds 0.75
```

Preparation rejects source rail samples, silence or DC-only audio, mismatched formats/durations, an explicit target beyond either file's peak allowance, and gains that quantize all AC energy away. It scales the original samples and rounds to PCM16, then remeasures the results and checks both polarities against the peak limit. Output AC RMS can differ slightly after integer rounding; the manifest retains the actual values. It does not resample, trim, pad individual phrases, remove DC, limit peaks, or repair already clipped inputs.

## Audition files and evidence

For output prefix `build/lead-01-ab`, preparation creates:

| File | Content |
| --- | --- |
| `lead-01-ab.ab.wav` | Matched A, silence, then matched B; no leading or trailing padding |
| `lead-01-ab.comparison.json` | Source paths and SHA-256, original/matched measurements, gain in scalar and dB form, target and headroom, comparison hash, and exact segment frame boundaries |
| `lead-01-ab.a.matched.wav` | Matched A alone, when `--individual-copies` is requested |
| `lead-01-ab.b.matched.wav` | Matched B alone, when `--individual-copies` is requested |

The gap defaults to 0.5 seconds and may be set from 0 to 60 seconds. Its duration is rounded to the nearest output frame and recorded as both frames and seconds. Segment `endFrame` values are exclusive. No labels, tones, fades, or music are added. Loop the A/B file in the chosen player if repeated listening helps.

Original files remain byte-for-byte intact. The tool refuses existing output paths and paths that resolve to either source; use a new prefix for a revised comparison. If writing fails, it cleans up only files created by that invocation. The originals' WAV container metadata is preserved in the original files; the comparison copies contain freshly written PCM WAV headers.

The JSON `listeningReview` is `null`: the tool has not listened or made a musical judgment. Listen to both the phrase and the intended mix, then record who listened, playback equipment, preference and reasons in the trial/instrument card. Measurements can establish signal health and explain level changes; they cannot establish expressive phrasing, timbral quality, authenticity, or suitability.

## Verification

```sh
python3 -m unittest discover -s tests -p 'audio_comparison_test.py' -v
```

The tests include exact unity-window and complete-sequence copying, different full input lengths, frame bounds and rollback, and use independent PCM fixtures to check exact A/B order and gaps, DC/AC separation, stereo balance, gain, both peak polarities, clipping and silence rejection in matching mode, format/duration mismatches, quantization limits, source preservation and existing/concurrent output protection. They do not substitute for a listening review.
