# Tracing a CIA-driven SID player

[The Shades tracer](../../scripts/trace-shades-vice.py) runs the unchanged, hash-pinned original or filter-corrected *Shades* payload in headless VICE; its explicit `--candidate` route also verifies independently compiled CIA players. CIA1 Timer A dispatches real IRQs through the ROM KERNAL prologue. A separate callable RAM oracle checks ordered stores and instruction durations; it does not schedule the CIA. Consult the [technique lookup](../research/technique-index.md) and [Shades reference intake](../research/composers/huelsbeck-tel.md#shades-reference-intake) for provenance and study status.

## Reproduce the timing proof

Install the [headless VICE and ROM data](../setup/local-setup.md) and the project's py65 dependencies. Keep reference binaries and generated evidence in ignored directories. Without `--candidate`, the CLI accepts only the two pinned Shades hashes; it preserves their CIA speed word and initializes default subtune 1 with A=0. Choose a fresh output directory.

```sh
PYTHONPATH=.tools/test-deps python3 scripts/trace-shades-vice.py .local/research/shades/Shades_filter_corrected.sid --calls 24385 --output build/shades-cia-primary-new
PYTHONPATH=.tools/test-deps python3 scripts/trace-shades-vice.py .local/research/shades/Shades.sid --calls 400 --output build/shades-cia-comparison-new
```

`--calls N` records N play entries numbered 0 through N−1. The pinned-source route retains its 1–65,535-call limit. The candidate host supports 1–65,536 calls, allowing the terminal call at `stopCall=65535`; a zero counter target represents the first completed 16-bit wrap, not an immediate stop. Both routes stop the timer after acknowledging the last call. `--vice PATH` and `--data PATH` override executable and ROM-data locations. The process uses file-monitor commands, warp mode, no sound device, a finite emulated-cycle limit and a 60-second VICE timeout. A failed run retains diagnostics without a successful study report.

| Output | Evidence |
|---|---|
| `study.json` | Payload, VICE and harness hashes; execution profile; host choices; call costs; cadence and ordered-store verification; timer-write inventory; limitations. |
| `trace.json` | Every play/ROM IRQ/host IRQ/return/acknowledgement checkpoint, ordered SID and timer stores, payload registers, raster context and monitor stopwatch. |
| `oracle.writes.json` | Ordered callable payload stores with phase, call, writer PC, instruction-start cycle, address and value. |
| `harness.prg`, `harness.listing`, `payload.prg` | The inspectable host and unchanged loaded input payload. Generated binaries remain ignored; reference payloads must never enter Git. |
| `commands.mon`, `command.json`, `monitor.log`, `process.log` | Exact VICE invocation, monitor recipe and raw machine observations. |

Execution checkpoints precede their instructions; store checkpoints follow them. `instructionStartCycle` belongs to the callable CPU oracle. None of these fields is an exact SID/CIA bus-write timestamp.

## Host and timer lookup

The host follows the timer setup and IRQ bank wrapper in the inspected libsidplayfp 3.1.1 `src/psiddrv.a65`, `cold` and `irqjob`. It explicitly selects VICE's new CIA model (`-cia1model 1 -cia2model 1`, MOS6526A), corresponding to libsidplayfp 3.1.1 `SidConfig.cpp`'s default new MOS8521 model. It starts with CPU port `$2F/$37`, zero-filled RAM, decimal mode clear, and the ROM KERNAL IRQ vector pointing to its handler. The host occupies `$0800–$0BFF`, within the pinned references' declared relocation space; every candidate payload must also remain outside that workspace.

| Register or locus | Established behavior |
|---|---|
| `$DC04` | The host writes low latch byte `$25`. Neither pinned source changes it in the verified span. |
| `$DC05` | The host writes high byte `$40`. The original executed `8D 05 DC`, `STA $DC05` at PC `$7852`, then writes `$30`; the preceding `$7850` instruction is `LDA ($AB),Y`, with Y=`$0E`. |
| `$DC0D` | Setup disables/acknowledges other CIA interrupts, then enables Timer A with `$81`. Every verified IRQ's acknowledgement read returns `$81`. |
| `$DC0E` | The host starts Timer A with `$01`; source control remains unchanged. The finite host stops it with `$00` after the last call. |
| ROM `$FF48` → host IRQ → play `$742E` | The measured KERNAL prologue takes 29 cycles and the bank-saving wrapper/indirect dispatch takes 26 cycles. |
| Source return → CIA acknowledgement | The wrapper restores `$01`, executes `DEC $D019`, then reads `$DC0D`, following the inspected `irqjob` order. The acknowledgement instruction takes four cycles. |

The timer's inclusive periods are `$4025+1 = $4026 = 16,422` cycles and `$3025+1 = $3026 = 12,326` cycles. The high-byte store in call 0 changes the latch after the first underflow has already reloaded the running counter with `$4025`. Consequently call 0→1 still spans 16,422 cycles; call 1→2 and later steady intervals span 12,326 cycles, subject to interrupt sampling phase. At the retained PAL clock of 985,248.611111 Hz, the steady entry rate is approximately 79.93255 Hz.

First ROM IRQ entry occurs 16,433 cycles after the timer-start store checkpoint; first play entry occurs after 16,488 cycles. The extra 11 cycles before ROM entry combine timer/IRQ startup and instruction sampling relative to that checkpoint. This probe does not separately observe the CIA underflow bus edge, so that difference is not an isolated hardware interrupt latency measurement.

## Reusable API

The script's hyphenated filename can be loaded with `importlib.util.spec_from_file_location`, as in [the tests](../../tests/shades_vice_trace_test.py). Its source-specific entry points are importable:

| Function | Contract |
|---|---|
| `source_profile(data)` | Verify a pinned source SHA-256 and return its validated explicit PAL/6581, single-subtune, CIA, callable-RAM profile. |
| `shades_oracle(data, calls, observer=None)` | Return `(report, ordered_writes)` for a pinned source. An optional read-only `observer(cpu, memory)` runs before each executed source instruction. |
| `run_trace(sid_path, output_path, calls, vice_path, data_directory)` | Run the pinned VICE proof, save its evidence and return the study dictionary. Arguments are `Path` objects. |

The observer can inspect `cpu.pc`, A/X/Y/SP/status and `memory.phase`, `tick`, `instruction`, `instruction_cycle`, `data`. Source RAM and zero page persist; each callable oracle play begins with the IRQ host's A=0, idle X/Y/status and bank `$37`. The guarded memory rejects source I/O/ROM reads, CIA control changes, hidden SID I/O, unsupported stores, writes into host RAM/vectors and missing returns. The source-specific oracle permits only the inspected `$7852` timer-high writer in addition to ordinary SID writes. Its 100,000-cycle per-call ceiling is an execution bound, not a CIA period guarantee; the full-machine cadence proof checks the timer schedule independently. CPU instruction timing uses the shared [verified loader and timing lookup](cpu-timing.md).

The lower-level `psid_profile`, `bounded_oracle`, `harness`, `parse_trace`, `verify_trace` and `run_profile` functions support independent fixtures with the same declared header/host contract. `LatchDiagnosticMemory` permits only play-phase non-RMW `$DC04/$DC05` latch stores beyond the strict auditor's SID writes. Production source intake remains hash-pinned; the [VBI auditor](psid-audit.md) and [fixed-PAL tracer](../../scripts/trace-sid-vice.py) retain their timing restrictions.

## Generated candidate API

[shades_audit.audit_candidate(data, calls, *, observer=None)](../../scripts/shades_audit.py) returns `(report, ordered_writes)` for 1–100,000 callable CPU play calls without loading an original reference or requiring its hash. The candidate input must declare PSID v2, one default subtune, PAL MOS6581 flags `$14`, CIA speed word `$00000001`, and callable RAM outside the host workspace. Its only timer-store allowance is play-phase non-RMW `STA $DC05`; it rejects `$DC04`, timer control, I/O or mapped-ROM reads, interrupt-vector/host writes, missing returns and play instructions that clear the IRQ mask. Ordinary SID stores retain the strict auditor's checks. Returned stores include phase, tick, writer PC, instruction-start cycle, address and value.

The monitor starts status at `fl=$24`; the host then executes `SEI`, `CLD` and zero-register loads. Init therefore begins with A=X=Y=0 and status `$26`: I/Z set, decimal/carry/negative/overflow clear. Timer A already runs during init. The candidate bound requires init plus a 24-cycle startup-host allowance to finish before the initial 16,422-cycle underflow. Each play enters with A=0, retained idle X/Y, IRQ masked and bank `$37`; the host's `RTI` restores idle status between calls. The independently compiled Shades player restores all named state in init with no SID/CIA writes, but that silence is its compiler/model contract rather than a generic auditor restriction on SID initialization.

The CPU audit assumes the host retains low latch byte `$25`, records the shortest period implied by the initial `$4025` latch and every emitted high byte, and requires `maximumPlayCycles + 160 < minimumTimerPeriodCycles`. The 160-cycle allowance conservatively covers IRQ dispatch, acknowledgement and finite counting in this controlled host. With minimum period 12,326, the admitted play budget is 12,165 cycles; init's budget is 16,397. These are cost guards, not CIA counter emulation or proof of actual cadence.

Candidate CPU auditing runs automatically in [compose-shades.py](../../scripts/compose-shades.py); there is no separate auditor CLI. For real interrupts, use `trace-shades-vice.py --candidate` or `run_candidate_trace(sid_path, output_path, calls, vice_path, data_directory)`. It returns the study dictionary and uses the candidate CPU auditor without changing the pinned source route. See the [source-free full and transfer build commands](../workflows/decoded-song-workflow.md#shades-compiled-cia-player).

## Compiled candidate evidence

On 2026-10-13, both independent candidates matched their semantic models and passed the real CIA host. Their compiled init emits no sound/timer stores; call 0 writes only the selected timer high byte. The finite score stop contributes four final stores, followed by silent calls in the compiler guards.

| Candidate and canonical VICE receipt | Play calls | Ordered SID/timer stores | Init cycles | Maximum play cycles | Maximum interval/phase error |
|---|---:|---:|---:|---:|---:|
| [Full decoded traversal](../../evidence/shades-independent-full/vice/study.json.gz) | 24,386 | 296,911 | 1,667 | 3,607 | 4 / 2 cycles |
| [Original transfer phrase](../../evidence/shades-transfer/vice/study.json.gz) | 1,522 | 10,734 | 1,643 | 3,138 | 4 / 3 cycles |

Both use a minimum 12,326-cycle timer window and pass the separate 12,165-cycle CPU play bound. Each VICE receipt checks every ordered store and call duration against the callable oracle, plus acknowledgement and latch-derived entry cadence. The [owning study](../research/composition/shades-preparation.md#reconstruction-boundary) retains input/output fingerprints and separate render/listening status; these timing receipts imply no listening acceptance or exact original within-call timing.

```sh
PYTHONPATH=.tools/test-deps python3 -m unittest discover -s tests -p shades_audit_test.py -v
PYTHONPATH=.tools/test-deps python3 -m unittest discover -s tests -p shades_compiler_test.py -v
```

## Retained proof and guards

On 2026-10-13, the [corrected full receipt](../../evidence/shades-intake/vice-cia-corrected-full-final/study.json.gz) verifies calls 0–24,384: 296,779 ordered SID stores plus 128 `$DC05=$30` stores at PC `$7852`, all 24,385 Timer A acknowledgements, and every source-call duration against the shared CPU oracle. Source calls take 670–2,831 cycles. High writes include calls 0, 193 and 385 and end at call 24,193. Maximum interval error is four cycles; cumulative phase stays within two cycles. The [current-oracle revalidation](../../evidence/shades-intake/vice-cia-corrected-full-final/current-oracle-revalidation.json) preserves agreement after tightening callable IRQ entry inputs. The [original comparison receipt](../../build/shades-intake/vice-cia-original-final/study.json) verifies 400 calls and 1,659 source stores, including the same first three timer writes and cadence bounds.

```sh
PYTHONPATH=.tools/test-deps python3 -m unittest discover -s tests -p shades_vice_trace_test.py -v
PYTHONPATH=.tools/test-deps python3 -m unittest discover -s tests -p shades_vice_trace_test.py -k absolute_decrement -v
```

The tracer guards cover a real changing-high-latch fixture, rejection of corrupted cadence/store evidence, bank restoration with preserved source zero page, final 16-bit counter transitions through the candidate's 65,536-call wrap, unsupported headers and hardware dependencies, both real pinned references, and a separate `DEC absolute` VICE fixture. The latter measures 26 cycles for its complete body and catches the installed py65 table's former three-cycle `$CE` declaration through the shared timing loader. The candidate auditor suite above adds IRQ-mask, init-entry/deadline and shortest-timer cost guards. VICE/reference integration guards skip explicitly when local ignored dependencies are absent.

The controlled environment disables display/sprite DMA and unrelated interrupts, adds call counting after acknowledgement, and omits libsidplayfp's reset, relocation and raster-synchronized startup. On the source route it preserves the original driver bytes, banking operations and zero-page swaps; the candidate route executes our independently generated payload under the same IRQ host. The proof establishes this host's ordered execution and cadence; it does not by itself establish libsidplayfp PCM alignment, decoded instruments, musical form, an audible ending or a listening judgment. Use the [audio workflow](../workflows/audio-workflow.md) for a separately identified render and retain musical findings in the owning study.
