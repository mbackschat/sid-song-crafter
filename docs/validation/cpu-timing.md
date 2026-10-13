# CPU timing checks and opcode corrections

Use [`verify_player.cpu_type()`](../../scripts/verify_player.py) for timing-sensitive NMOS 6502/6510 execution. It supplies the shared py65 adapter used by the PSID auditor, SID-Wizard exporter and player checks. Importing py65's `MPU` directly bypasses repository corrections. The adapter copies the timing table into a subclass; it does not modify the installed dependency or its global class.

## Verified decrement lookup

These are instruction durations, not SID write bus timestamps. The [CPU timing guards](../../tests/cpu_timing_test.py) cover RAM addresses, wraparound data and indexed addressing across a page boundary. The independent `test_absolute_decrement_instruction_duration_matches_executed_vice` fixture in the [CIA tracer guards](../../tests/shades_vice_trace_test.py) measures the absolute instruction in headless VICE.

| Opcode | Instruction / addressing | CPU cycles | Repository treatment |
| --- | --- | --- | --- |
| `$C6` | `DEC zp` | 5 | Retain upstream timing; regression guarded |
| `$D6` | `DEC zp,X` | 6 | Retain upstream timing; regression guarded |
| `$CE` | `DEC abs` | 6 | Correct py65 1.2.0's value of 3 in the shared adapter |
| `$DE` | `DEC abs,X` | 7 | Retain upstream timing, including page crossing; regression guarded |

This is a lookup for the investigated instruction family, not a claim that every opcode or peripheral bus interaction has been independently verified. Read-modify-write instructions targeting SID remain unsupported by the [bounded PSID auditor](psid-audit.md), because matching instruction duration does not reproduce NMOS dummy writes.

## Why the correction matters

On 2026-10-13, the Shades CIA trace exposed a three-cycle disagreement on calls executing `DEC $0341` at `$7457`; row-processing calls without that decrement did not disagree. A separate VICE fixture confirmed six cycles for `$CE`. Correcting the common CPU adapter resolves the mechanism for every timing-sensitive caller rather than hiding it in the Shades tracer.

The regression workload executes 3,300 absolute decrements and returns. The faulty table reports 9,906 cycles, incorrectly accepting it within the 19,656-cycle PAL budget; the correct cost is 19,806, which the auditor rejects. Other tests ensure that an already-correct upstream dependency remains compatible and its table is never mutated.

```sh
PYTHONPATH=.tools/test-deps python3 -m unittest discover -s tests -p cpu_timing_test.py -v
PYTHONPATH=.tools/test-deps python3 -m unittest discover -s tests -p shades_vice_trace_test.py -v
```

The second command also exercises real CIA scheduling and requires the configured headless VICE installation. Keep CPU-only and full-machine evidence separate.

## Effect on retained evidence

Older py65 reports can undercount each executed `$CE` by three cycles. This affects call durations and later instruction-start timestamps. It does not by itself change register values/order, assembled binaries, rendered PCM or listening judgments. Re-run timing-sensitive evidence through the shared adapter before reusing an old budget or timestamp; do not silently rewrite historical receipts.

The [corrected Flashdance comparison receipt](../../build/cpu-timing-correction/summary.json) records unchanged source/export hashes and ordered writes. The accepted single-SID maximum changes from 2,228 to 2,231 cycles; the dual-SID maximum changes from 3,508 to 3,514; the original transfer phrase remains 1,768. All remain within their declared PAL budget. The full selected source comparison still matches 27,905 writes; its instruction-start difference range remains −235 to +418 cycles. Current figures and their receipts are linked from the [owning Flashdance study](../research/composition/flashdance-preparation.md).

When another opcode discrepancy appears, isolate it in a small independently executed fixture, correct the shared adapter only if needed, guard the affected instruction family and practical budget failure, and add the verified finding here. Avoid a second manually maintained copy of the CPU's complete opcode table.
