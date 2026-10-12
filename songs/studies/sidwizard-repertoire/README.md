# Original SID-Wizard instrument studies

These are original project patches and short original phrases for SID-Wizard 1.97 Extra, one MOS8580 at `$D400`, PAL, one player call per video frame. The [declarative source](repertoire.json) preserves native instrument parameters and separate waveform, pulse, and filter programs. The generated SWM workfiles and SWI instruments are directly editable in SID-Wizard; no MIDI or common-score round trip is involved.

The bank contains four instrument families and three controlled solo comparisons. Evidence level: **rendered experiment**, verified on 2026-10-12. Upstream SID-Maker accepted all nine workfiles; the independent CPU audit completed 501 calls per export, and libsidplayfp 3.1.1/SIDLite produced each full ten-second PAL MOS8580 render. The mix pair changes the complete palette together and therefore measures interaction rather than isolating a single parameter. Successful playback does not establish musical quality. The [instrument cards](../../../docs/research/composition/instruments/README.md) record the measurements and questions for listening review.

| Comparison | Reference | Candidate | Changed parameter |
| --- | --- | --- | --- |
| Pulse lead | [Static width](native/pulse-reference.swm) | [Moving width](native/pulse-candidate.swm) | Pulse program only; ADSR, vibrato, notes and articulation match |
| Pluck | [Triangle attack](native/pluck-reference.swm) | [Saw attack](native/pluck-candidate.swm) | First waveform-table row only |
| Shared bass and kick | [Plain bass](native/bass-reference.swm) | [Kick-to-bass](native/bass-candidate.swm) | Three triangle pitch-fall rows before the pulse body |
| Three-voice palette | [Reference mix](native/mix-reference.swm) | [Candidate mix](native/mix-candidate.swm) | Lead motion, pluck attack and bass transient together |
| Dedicated kick | — | [Pitch-fall kick](native/kick.swm) | Standalone diagnostic, without an A/B reference |

All phrases last 64 rows at six PAL ticks per row, nominally 384 ticks, and their orderlists terminate rather than loop. The ten-second renders leave time to inspect the ending and release. The manifest declares `renderSeconds: 10`, `playTicks: 501`, `phraseTicks: 384`, `loopBoundaryTicks: null`, and `endPolicy: "stop"`. The native driver's continuous instrument/vibrato processing can continue after the sequence stops; ending success is established by closed gates and quiet PCM, not by the absence of register writes. Melodic phrases include fast repeated notes, a held note, a rest and re-entry, tied notes, an instrument change and a higher final note. Bass phrases include repeated arrivals, a hold, a rest and a change to the dedicated kick.

Measured on 2026-10-12: every render contains 441000 mono PCM16 samples at 44100 Hz, no clipped samples and final-half-second AC RMS zero. All gates are closed at audit tick 500. The RAM-only CPU call budget is 19656 cycles; these measurements do not include interrupt or VIC badline contention. The complete [trial report](../../../build/instrument-trials/trial.json), per-study `.audit.json`, exact `.writes.json` logs and renderer `.registers.tsv` snapshots remain in ignored `build/instrument-trials/`.

| Study | Peak PCM magnitude | Full-file AC RMS | Maximum play-call cycles |
| --- | ---: | ---: | ---: |
| Pulse reference / candidate | 4550 / 4550 | 2207.180 / 2187.485 | 1271 / 1271 |
| Pluck reference / candidate | 4532 / 4532 | 836.042 / 836.103 | 1269 / 1269 |
| Bass reference / candidate | 5189 / 4546 | 2386.311 / 2303.060 | 1269 / 1269 |
| Mix reference / candidate | 13079 / 12873 | 3221.786 / 3234.556 | 2193 / 2193 |
| Dedicated kick | 4236 | 369.053 | 1269 |

Prepared listening files play reference A for ten seconds, a half-second gap, then candidate B for ten seconds. Matching uses full-file AC RMS with DC removed, includes rests/tails and applies attenuation only. It is a reproducible comparison aid rather than a perceptual loudness verdict.

- [Pulse A/B](../../../build/instrument-trials/comparisons/pulse.ab.wav): A gain 0.991077 (-0.077853 dB), B gain 1; [matching report](../../../build/instrument-trials/comparisons/pulse.comparison.json).
- [Pluck A/B](../../../build/instrument-trials/comparisons/pluck.ab.wav): A gain 1, B gain 0.999927 (-0.000633 dB); [matching report](../../../build/instrument-trials/comparisons/pluck.comparison.json).
- [Bass A/B](../../../build/instrument-trials/comparisons/bass.ab.wav): A gain 0.965113 (-0.308435 dB), B gain 1; [matching report](../../../build/instrument-trials/comparisons/bass.comparison.json).
- [Full mix A/B](../../../build/instrument-trials/comparisons/mix.ab.wav): A gain 1, B gain 0.996052 (-0.034360 dB); [matching report](../../../build/instrument-trials/comparisons/mix.comparison.json).
- [Dedicated kick, original amplitude](../../../build/instrument-trials/kick/kick.wav).

The source renders remain beside their SID/PRG exports at original amplitude. On 2026-10-12, mbackschat reported **“mix sounds ok”** after receiving the candidate mix sample. This is an initial mix-level acceptance. The [later listening findings](../../../docs/research/composition/gestures/README.md) record audible pulse motion without a preference and little perceived bass-transient difference. Playback equipment, editor/export comparison and hardware checks remain unreported. The [listening record](../../../docs/instrument-trials.md) preserves that scope.

Native editable instruments:

- [Static pulse](native/instruments/pulse-static.swi) and [moving pulse](native/instruments/pulse-moving.swi).
- [Soft pluck](native/instruments/pluck-soft.swi) and [bright pluck](native/instruments/pluck-bright.swi).
- [Plain bass](native/instruments/bass-plain.swi) and [kick-to-bass](native/instruments/bass-kick.swi).
- [Dedicated kick](native/instruments/kick-fall.swi).

Regenerate the retained workfiles from the repository root:

```sh
python3 scripts/generate-native-instruments.py songs/studies/sidwizard-repertoire/repertoire.json --output-dir songs/studies/sidwizard-repertoire/native
python3 -m unittest discover -s tests -p native_instruments_test.py -v
```

After [setting up the pinned native exporter](../../../docs/research/tools/sid-wizard-trial.md) and [audio renderer](../../../docs/audio-workflow.md), reproduce the complete export/audit/render/comparison run:

```sh
python3 scripts/run-instrument-trials.py --output build/instrument-trials
```

The command requires a new output directory so existing evidence is preserved; choose another `--output` path for a subsequent run. `--pair pulse`, `--pair pluck`, `--pair bass` or `--pair mix` narrows a rerun to one controlled pair. Generated audio links above become available after the full run on a clean checkout.

The generator implements only the SWM1 subset needed by these studies. It checks native table and pattern limits, resolves table jumps to instrument-relative offsets, and preserves the editor's packed instrument and pattern delimiters. It does not import or translate other editors' patches. `SWM-spec.src`, `include/packdepack.inc` and `include/player.asm` in the [official 1.97 source archive](https://csdb.dk/getinternalfile.php/281063/SID-Wizard-1.97-sources-examples.tar.gz) are the format and execution basis; the acquired archive identity is recorded in [the tool assessment](../../../docs/research/tools/composition-tools.md).

The patches and phrases were designed for this project on 2026-10-12. No example instrument or tune bytes were copied. The repository currently declares no blanket project license, so these original files add no independent reuse grant. The upstream player/exporter retains Hermit's original notice; the original project patches should not be attributed to Hermit or presented as recovered historical presets.
