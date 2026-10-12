# Headless native-player checkpoints

The [native VICE verifier](../scripts/verify-native-vice.py) boots a SID-Wizard Extra single-speed PAL standalone PRG through BASIC and compares all 25 SID write-shadow registers with the independent CPU audit at selected completed play-call counts. It requires the [headless VICE installation](local-setup.md); no GUI, socket, audio device or Computer Use is involved.

```sh
python3 scripts/verify-native-vice.py \
  build/instrument-trials/mix-candidate/mix-candidate.prg \
  build/instrument-trials/mix-candidate/mix-candidate.writes.json \
  --calls 1 20 200 501 --output build/native-vice-check
```

Use a fresh output directory. `--vice` and `--data` override the local executable and ROM-data paths. The tool retains the monitor commands, exact arguments, process/monitor logs, input hashes and successful verification report. It bounds execution by both emulated cycles and a 60-second process timeout; a failed run leaves diagnostic files without a success report.

## Counting calls correctly

The initial breakpoint at `$1003` is before play call zero, after initialization. After stopping there, reaching completed call count 20 requires ignoring the next 19 crossings. Every later interval similarly uses `nextCount - previousCount - 1`. The monitor explicitly selects decimal radix for ignore counts and hexadecimal radix for memory output. The contract is documented in the pinned [VICE 3.9 monitor manual](../.tools/vice-headless-3.9/source/doc/vice.texi), checkpoint and radix commands.

PAL play entries must remain within seven cycles of `firstEntry + completedCalls × 19656`. This accommodates the seven-cycle `$d012` polling loop in SID-Wizard 1.97's native `exporter.asm`, `rast1st`; it does not allow drift by a raster line or frame. Each checkpoint includes the measured error and exact register bytes. The verifier accepts only successful monitor exit, unlike a deliberately cycle-limited audio capture.

## Recorded evidence

On 2026-10-12, the native mix candidate matched at completed call counts 0, 1, 20, 200 and 501. Entry was cycle 2,374,739; subsequent timing errors were −2, 0, −3 and −1 cycles. All 25 write-shadow registers matched at every checkpoint. Evidence is in ignored [build/native-vice-verified](../build/native-vice-verified/verification.json).

This independently checks standalone loading, sampled driver state and sustained native cadence. It does not compare every intervening bus write, measure audible pitch, establish envelope equivalence or supply a listening verdict. Keep these results alongside the [CPU audit](psid-audit.md), [rendered instrument trials](instrument-trials.md) and any complete-song evidence.
