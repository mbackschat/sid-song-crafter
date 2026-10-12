# Headless native-player checkpoints

The [native VICE verifier](../scripts/verify-native-vice.py) boots a SID-Wizard Extra single-speed PAL standalone PRG through BASIC and compares all 25 SID write-shadow registers with the independent CPU audit at selected completed play-call counts. It requires the [headless VICE installation](local-setup.md); no GUI, socket or audio device is needed.

```sh
python3 scripts/verify-native-vice.py \
  build/instrument-trials/mix-candidate/mix-candidate.prg \
  build/instrument-trials/mix-candidate/mix-candidate.writes.json \
  --calls 1 20 200 501 --output build/native-vice-check
```

Use a fresh output directory. `--vice` and `--data` override the executable and ROM-data paths. The output retains commands, logs, input hashes and the verification report. Execution is bounded by emulated cycles and a 60-second process timeout; unsuccessful runs retain diagnostics without a success report.

## Call counting and cadence

The initial breakpoint at `$1003` is after initialization and before the first play call, so it represents zero completed calls. Reaching completed call count 20 requires ignoring the next 19 crossings. Every later interval uses `nextCount - previousCount - 1`. Select decimal radix for ignore counts and hexadecimal radix for memory output; see the pinned [VICE 3.9 monitor manual](../.tools/vice-headless-3.9/source/doc/vice.texi).

PAL play entries must remain within seven cycles of `firstEntry + completedCalls × 19656`. This allows the instruction-phase jitter of the seven-cycle `$d012` polling loop in SID-Wizard 1.97's `exporter.asm`, `rast1st`, while rejecting raster-line or frame drift. The verifier requires a successful monitor exit; deliberate cycle-limit audio capture has a separate acceptance rule in [the audio guide](audio-workflow.md).

## Validation status and limits

The native mix and [complete Für Elise candidate](fuer-elise-native.md) pass register and cadence comparisons. Full-song checkpoints cover initialization, both critical grace bodies, later material and the silent ending. This checks standalone loading, sampled driver state and sustained native cadence. It does not compare every intervening bus write, measure audible pitch, establish envelope equivalence or supply a listening verdict. Use it alongside the [CPU audit](psid-audit.md), [rendered instrument trials](instrument-trials.md) and complete-song checks.
