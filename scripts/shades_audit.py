"""Audit callable single-SID CIA candidates with the Shades IRQ host contract."""

import hashlib
import importlib.util
from pathlib import Path

from verify_player import require


spec = importlib.util.spec_from_file_location('shades_candidate_trace', Path(__file__).with_name('trace-shades-vice.py'))
trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace)
MAX_CALLS = 100000
# harness timer_start spends 17 cycles reaching init and 7 after its RTS through CLI.
INIT_HOST_CYCLES = 24
# trace-shades-vice.harness has at most 134 cycles on ordinary IRQ/counting paths;
# 160 also covers its finite-stop stores and instruction-phase sampling without display DMA.
IRQ_HOST_CYCLES = 160
INITIAL_PERIOD = trace.BASELINE_LATCH + 1


class CandidateMemory(trace.LatchDiagnosticMemory):
    allowed_timer_writes = (0xdc05,)

    def __init__(self):
        super().__init__()
        self.minimum_timer_period = INITIAL_PERIOD

    def __setitem__(self, address, value):
        super().__setitem__(address, value)
        if address == 0xdc05:
            self.minimum_timer_period = min(self.minimum_timer_period, (value << 8 | 0x25) + 1)


def audit_candidate(data, calls, *, observer=None):
    """Return CPU evidence and ordered SID/high-latch stores for 1..100000 calls.

    The host retains timer low byte $25. Every emitted high byte contributes to
    the conservative shortest-window guard; the initial $4026 period also counts.
    CPU calls do not emulate CIA counters or establish interrupt/bus timestamps.
    """
    require(type(calls) is int and 1 <= calls <= MAX_CALLS, 'Candidate CPU audit supports 1..100000 play calls')
    profile = trace.psid_profile(data)
    memory = CandidateMemory()
    report, writes = trace._execute_oracle(data, calls, memory=memory, observer=observer,
                                           init_budget=INITIAL_PERIOD - INIT_HOST_CYCLES - 1,
                                           play_budget=INITIAL_PERIOD - IRQ_HOST_CYCLES - 1,
                                           require_irq_mask=True)
    require(report['maximumPlayCycles'] + IRQ_HOST_CYCLES < memory.minimum_timer_period,
            'Candidate play plus IRQ host allowance exceeds the shortest CIA timer window')
    report.update(schemaVersion=1, sourceSha256=hashlib.sha256(data).hexdigest(), executionProfile='cia-candidate',
                  profile={key: value for key, value in profile.items() if key != 'payload'},
                  timerLowByte=0x25, initialTimerPeriodCycles=INITIAL_PERIOD,
                  minimumTimerPeriodCycles=memory.minimum_timer_period,
                  initHostAllowanceCycles=INIT_HOST_CYCLES, irqHostAllowanceCycles=IRQ_HOST_CYCLES,
                  initCycleBudget=INITIAL_PERIOD - INIT_HOST_CYCLES - 1,
                  playCycleBudget=memory.minimum_timer_period - IRQ_HOST_CYCLES - 1,
                  initWriteCount=sum(row['phase'] == 'init' for row in writes),
                  playWriteCount=sum(row['phase'] == 'play' for row in writes),
                  limitations='Callable CPU execution with strict RAM/ROM/I/O guards plus a conservative CIA-host cost bound; only play-phase non-RMW $DC05 latch writes extend ordinary SID stores. No CIA counter emulation, bus timestamps, audio, source equivalence or musical quality claim. Real IRQ cadence requires run_candidate_trace in headless VICE.')
    return report, writes
