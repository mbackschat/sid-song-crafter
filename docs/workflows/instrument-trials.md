# Native SID instrument trials

Seven original editable SID-Wizard instruments, nine short native workfiles and four controlled A/B comparisons pass export, bounded CPU execution, signal-health and ending checks. The exported driver is SID-Wizard 1.97 Extra at one update per PAL frame, targeting MOS8580. The [complete Für Elise baseline](../songs/fuer-elise-score.md) remains the source reference.

Listening evidence from mbackschat, 2026-10-12: the short candidate mix “sounds ok”; pulse motion is distinguishable without a stated preference; the tested bass transient makes little or no perceived difference. The [native Für Elise attack comparison](../songs/fuer-elise-native.md) supports a cleaner triangle onset in that passage, but its arrangement remains too clinical compared with DRAX. See [reusable listening findings and creative direction](../research/composition/gestures/README.md). Playback equipment and a complete-song verdict were not supplied; broader listening and hardware checks remain open.

## Audition the palette

Each comparison plays reference A for 10 seconds, leaves a 0.5-second gap, then plays candidate B for 10 seconds. Original-amplitude renders are retained. Full-file AC RMS matching controls amplitude without claiming equal perceived loudness; see [the comparison contract](audio-comparisons.md).

| Study | Audition | Controlled change |
| --- | --- | --- |
| Moving pulse | [A/B WAV](../../build/instrument-trials/comparisons/pulse.ab.wav) | Pulse-width program; notes, ADSR and delayed vibrato unchanged |
| Pluck attack | [A/B WAV](../../build/instrument-trials/comparisons/pluck.ab.wav) | One sawtooth attack frame before the triangle body |
| Bass/drum sharing | [A/B WAV](../../build/instrument-trials/comparisons/bass.ab.wav) | Three-frame falling triangle transient before pulse bass |
| Three-voice mix | [A/B WAV](../../build/instrument-trials/comparisons/mix.ab.wav) | All three changes combined in an original phrase |
| Candidate mix alone | [10-second WAV](../../build/instrument-trials/mix-candidate/mix-candidate.wav) | Sample without the reference |
| Dedicated kick | [10-second WAV](../../build/instrument-trials/kick/kick.wav) | Original pitched triangle decay program |

Judge the mix in context, then use the isolated comparisons to identify useful changes. The pluck comparison preserves the sustained body and envelope, isolating its brief attack. Record preference, playback equipment and specific reasons in the [instrument cards](../research/composition/instruments/README.md); a numerical difference alone is not a musical improvement.

## Reproduce the studies

Prepare the [pinned native exporter](../research/tools/sid-wizard-trial.md), [renderer](audio-workflow.md) and py65 dependency, then run:

```sh
python3 scripts/setup-sidwizard.py
python3 scripts/run-instrument-trials.py --output build/instrument-trials
```

Use a new output directory for another run. `--pair pulse`, `pluck`, `bass` or `mix` selects one comparison. The script verifies that the checked-in [native workfiles agree with their recipe](../../songs/studies/sidwizard-repertoire/README.md) and preserves them. Regeneration is explicit:

```sh
python3 scripts/generate-native-instruments.py songs/studies/sidwizard-repertoire/repertoire.json --output-dir songs/studies/sidwizard-repertoire/native
```

The generator covers this trial bank, not arbitrary native songs. Keep independently edited workfiles as separate studies rather than overwriting them through a narrower recipe.

Each output includes SID/PRG files, export provenance, CPU audit and ordered writes, original WAV and register snapshots, and matched A/B audio. `trial.json` is written only after every selected check passes; unsuccessful runs retain diagnostics without a final success report. Exporter and renderer setup are prerequisites for the integration tests.

## Validation contract

The checks require complete mono PCM16 renders at 44.1 kHz, nonzero AC energy, no clipped samples, a quiet final half-second and closed final gates. RAM-only CPU calls must fit the 19656-cycle PAL frame budget; this excludes VIC contention and is not a hardware raster-time guarantee.

Ordered register guards verify moving versus fixed pulse width with identical pitch trajectories, saw attack followed by triangle, and a falling bass transient that returns to the reference pitch and gate. Bass recovery allows one frequency-register unit of rounding difference. Each report declares the checked tick windows; these checks are not complete native-score equivalence proofs.

The phrases cover repeated notes, a hold, rest/re-entry, tied pitch changes, instrument changes and a three-voice mix. Native sources retain waveform, pulse, filter, restart and vibrato programs. The [cards](../research/composition/instruments/README.md) hold instrument settings and focused evidence. Editor UI round-trip, editor-versus-export listening, physical chips, multispeed and two-chip mixes of this palette remain unverified. A separate [six-voice fixture](native-song-workflow.md) establishes the two-chip export, scheduling, stereo and VICE foundation.

## Independent VICE checks

The candidate mix's standalone PRG also produces nonempty phrase-and-tail audio in headless VICE 3.9 with reSID8580. Its raw capture includes machine bootstrap and is not aligned to the SIDLite render or included in the matched comparisons. Use [native register/cadence checkpoints](../validation/native-vice-checks.md) for sampled execution equivalence.

For a bounded audio smoke test, write a monitor file with the appropriate PRG path:

```text
loadbasic "build/instrument-trials/mix-candidate/mix-candidate.prg" 0
keybuf run\n
until $1003
r
x
```

Use the headless executable and resource directory from [local setup](../setup/local-setup.md) with `-pal +logcolorize -initbreak ready -moncommands MONITOR_FILE -monlog -monlogname LOG_FILE -limitcycles 11822984 +warp -sounddev wav -soundarg OUTPUT.wav -sidenginemodel resid8580 -soundrate 44100`. The cycle budget covers 12 seconds of emulated time, including bootstrap. Keep XDG configuration/state writable and unset display variables as in [the audio guide](audio-workflow.md).

VICE 3.9 returns status 1 with `cycle limit reached.` at a deliberate cycle boundary. Accept that outcome only with a confirmed player-entry breakpoint, finalized nonempty WAV and expected capture duration. It does not establish a return to BASIC. Keep warp disabled for WAV capture.
