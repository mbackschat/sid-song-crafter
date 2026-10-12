# Native SID instrument trials

Verified on 2026-10-12: seven original editable SID-Wizard instruments, nine short native workfiles, and four controlled A/B comparisons now pass export, bounded CPU execution, signal-health and ending checks. The generated driver is SID-Wizard 1.97 Extra at one update per PAL frame, targeting MOS8580. The complete Für Elise baseline remains unchanged.

Listening record, 2026-10-12: mbackschat reported **“mix sounds ok”** after the candidate sample was supplied. This is an initial listener acceptance of that short mix, supporting use of the palette in a Für Elise candidate. Playback equipment, individual A/B preferences and a complete-song judgment were not supplied. The isolated instruments remain rendered experiments; this brief feedback does not establish a showcase-quality verdict or a hardware check.

## Hear and inspect the studies

Each comparison plays the reference for 10 seconds, leaves a 0.5-second gap, then plays the candidate for 10 seconds. Original renders are retained; full-file AC RMS matching controls amplitude without claiming equal perceived loudness. See [the comparison contract](audio-comparisons.md).

| Study | Audition | Controlled change |
| --- | --- | --- |
| Moving pulse | [A/B WAV](../build/instrument-trials/comparisons/pulse.ab.wav) | Pulse-width program; notes, ADSR and delayed vibrato unchanged |
| Pluck attack | [A/B WAV](../build/instrument-trials/comparisons/pluck.ab.wav) | One sawtooth attack frame before the triangle body |
| Bass/drum sharing | [A/B WAV](../build/instrument-trials/comparisons/bass.ab.wav) | Three-frame falling triangle transient before pulse bass |
| Three-voice mix | [A/B WAV](../build/instrument-trials/comparisons/mix.ab.wav) | All three changes combined in an original phrase |
| Candidate mix alone | [10-second WAV](../build/instrument-trials/mix-candidate/mix-candidate.wav) | Convenient sample without the reference |
| Dedicated kick | [10-second WAV](../build/instrument-trials/kick/kick.wav) | Original pitched triangle decay program |

Start with the mix to judge the palette in context, then use the isolated comparisons to identify which changes help. The pluck comparison is intentionally subtle: its sustained body and envelope are identical. Record preference, playback equipment, and specific reasons in the [instrument cards](research/composition/instruments/README.md); a numerical difference alone is not a musical improvement.

## Reproduce the bank

Prepare the [pinned native exporter](research/tools/sid-wizard-trial.md), [renderer](audio-workflow.md), and py65 dependency first. Then run:

```sh
python3 scripts/setup-sidwizard.py
python3 scripts/run-instrument-trials.py --output build/instrument-trials
```

Use a new output directory for another run. `--pair pulse`, `pluck`, `bass`, or `mix` runs a single pair. The script uses the checked-in [native workfiles and recipe](../songs/studies/sidwizard-repertoire/README.md), verifies that they agree, and preserves them. Regeneration is explicit:

```sh
python3 scripts/generate-native-instruments.py songs/studies/sidwizard-repertoire/repertoire.json --output-dir songs/studies/sidwizard-repertoire/native
```

This generator describes our trial bank; it is not a universal score format or a round-trip editor. Keep independently edited native songs as separate studies rather than overwriting them through a narrower recipe.

The output contains each SID/PRG, native-export provenance, CPU audit and ordered writes, original WAV and timestamped register snapshots, matched A/B files, and `trial.json`. That final report is written only after all selected trials and comparisons pass. A failed run retains diagnostics but produces no successful final report. The test suite exercises the actual native exporter and renderer, so setup is a prerequisite.

## What the checks establish

The nine renders each contain 441,000 mono PCM16 samples at 44.1 kHz. None reaches a PCM rail; each has nonzero AC energy and a quiet final half-second. All three final gates are closed. The CPU audit runs 501 calls per workfile; the largest measured call is 2,193 cycles for the mix, below the 19,656-cycle PAL frame budget. This audit omits VIC contention and is not a hardware raster-time guarantee.

Technique guards use ordered register states, not audio adjectives. They verify moving versus fixed pulse width while pitch trajectories remain identical, a saw attack followed by triangle, and a falling bass transient that returns to the reference pitch and gate. The bass comparison allows a one-register-unit rounding difference at body recovery. Guards state their checked tick windows in the report; they are not a complete native-score equivalence proof. Reversed attacks and a bass that never recovers are regression cases.

The phrases also exercise repeated notes, a held note, rest/re-entry, tied pitch changes, instrument changes and a three-voice mix. Native bytes retain waveform, pulse, filter, restart and vibrato programs. [Instrument cards](research/composition/instruments/README.md) contain the actual settings and measurements. Editor UI reopening, editor-versus-export listening, real chips, multispeed and two-SID trials remain unverified.

## Independent native VICE capture

The candidate mix's standalone PRG also ran in headless VICE 3.9 with reSID8580. The monitor reached `$1003` at cycle 2,374,739; the bounded 12-second capture contains bootstrap time plus the complete phrase and tail. It has peak 10,167, zero PCM rail samples, and final-half-second AC RMS 19.002 sample units. The independent [native WAV](../build/instrument-trials/native-vice/mix.vice.wav) has 529,184 samples; it is not aligned to the SIDLite WAV and is not included in the matched A/B comparisons.

To repeat this native smoke test, create a monitor file containing the following commands, with the appropriate PRG path:

```text
loadbasic "build/instrument-trials/mix-candidate/mix-candidate.prg" 0
keybuf run\n
until $1003
r
x
```

Use the headless executable and data directory from [local setup](local-setup.md), plus `-pal +logcolorize -initbreak ready -moncommands MONITOR_FILE -monlog -monlogname LOG_FILE -limitcycles 11822984 +warp -sounddev wav -soundarg OUTPUT.wav -sidenginemodel resid8580 -soundrate 44100`. Keep XDG configuration/state in writable local directories and unset display variables, as in [the audio guide](audio-workflow.md). The performed run's exact arguments are in [command.json](../build/instrument-trials/native-vice/command.json).

VICE deliberately exits with status 1 and `cycle limit reached.` at this boundary; its source uses `EXIT_FAILURE` for that limit. Accept this specific outcome only together with the recorded player-entry breakpoint, finalized nonempty WAV and expected duration. It does not mean that the PRG returns to BASIC. Warp mode must remain disabled for WAV capture. All probe processes were reaped.

The first trial also found and fixed a renderer subtune-selection error; [the root-cause record](audio-workflow.md) explains why successful CPU playback alone had missed it.
