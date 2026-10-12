# Preparing level-matched audio comparisons

Use [compare-audio.py](../scripts/compare-audio.py) to inspect original PCM16 WAV renders and prepare an A/B audition with documented gain. It uses only the Python standard library and needs no player/event manifest, so native SID-Wizard instrument phrases and the repository player can share this measurement step. Retain the original-amplitude renders and their native workfiles as evidence. See [the sound-design repertoire](research/composition/sound-design-repertoire.md) for musical acceptance questions and [the audio workflow](audio-workflow.md) for rendering.

```sh
python3 scripts/compare-audio.py inspect build/baseline-phrase.wav
python3 scripts/compare-audio.py prepare build/baseline-phrase.wav build/native-instrument-phrase.wav build/lead-01-ab --individual-copies
```

The filenames above are example inputs, not a claim that these renders already exist. Render the same complete phrase, including the same rests and tail duration, at the same rate and channel count. The tool requires identical frame counts; it does not establish that notes, tempo, update cadence, SID model, alignment, or renderer settings agree. Record those source assumptions in the trial or [instrument card](research/composition/instrument-card-template.md).

## Measurement and matching contract

The input contract is nonempty, uncompressed 16-bit PCM WAV with one or two channels. Inspection reports frames, sample rate, duration, absolute sample peak, peak dBFS, PCM rail counts, per-channel DC mean, raw RMS and AC RMS, and pooled raw/AC RMS. Amplitudes use signed PCM sample units; dBFS uses 32768 as the reference. `clippedSamples` counts values equal to −32768 or 32767. These rails conservatively indicate possible hard clipping; a count of zero cannot detect distortion or clipping that occurred before the PCM render.

AC RMS subtracts each channel's own mean before pooling channel power. This prevents a DC offset, including opposing offsets in stereo, from inflating the matching level. The measurement covers the entire input file, including silence and release tails. This is amplitude matching for a controlled phrase comparison; it is not a perceptual loudness measurement. A long quiet tail or different duty cycle can influence the result.

By default, preparation chooses a shared AC RMS no greater than either source's AC RMS and no greater than either source can reach with the requested peak headroom. Each file gets one positive scalar gain; channels keep their balance and polarity, and DC is scaled with the signal. The default reserves 1 dB of peak headroom using the conservative symmetric sample limit `floor(32767 × 10^(−headroomDb/20))`. Gain never boosts either source in this mode. If transients or DC use the available peak range, both sources may be reduced below the quieter source's original RMS.

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

The tests use independent PCM fixtures to check exact A/B order and gaps, DC/AC separation, stereo balance, gain, both peak polarities, clipping and silence rejection, format/duration mismatches, quantization limits, source preservation and existing/concurrent output protection. They do not substitute for a listening review.
