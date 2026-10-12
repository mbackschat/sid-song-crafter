"""Check exact PAL player writes with the independently implemented py65 CPU."""

import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
PAL_CLOCK = 17734475 / 18
CYCLES_PER_FRAME = 312 * 63
TICKS_PER_SECOND = PAL_CLOCK / CYCLES_PER_FRAME


def require(condition, message):
    if not condition:
        raise ValueError(message)


def cpu_type():
    try:
        from py65.devices.mpu6502 import MPU
    except ModuleNotFoundError:
        dependencies = ROOT / ".tools/test-deps"
        require((dependencies / "py65").is_dir(), "Exact CPU verification requires py65; install the documented dependencies in .tools/test-deps")
        sys.path.insert(0, str(dependencies))
        from py65.devices.mpu6502 import MPU
    return MPU


def rounded(value):
    return math.floor(value + 0.5)


def expected_schedule(manifest):
    require(math.isclose(manifest["clockHz"], PAL_CLOCK, rel_tol=1e-12), "Manifest does not use the PAL clock")
    require(math.isclose(manifest["ticksPerSecond"], TICKS_PER_SECOND, rel_tol=1e-12), "Manifest does not use PAL frame timing")
    bpm = manifest["quarterBpm"]
    require(math.isfinite(bpm) and bpm > 0, "Manifest tempo must be positive")
    require(len(manifest["voices"]) == 3, "Exact player verification requires three voices")
    writes = []
    order = 0
    counts = []
    for voice, part in enumerate(manifest["voices"]):
        count = 0
        base = 0xd400 + voice * 7
        waveform = part["instrument"]["waveform"]
        for event in part["events"]:
            start = rounded(event["startBeat"] * 60 / bpm * TICKS_PER_SECOND)
            end = rounded((event["startBeat"] + event["durationBeats"]) * 60 / bpm * TICKS_PER_SECOND)
            duration = end - start
            require(duration >= 1 and event["startTick"] == start and event["durationTicks"] == duration, "Manifest event disagrees with absolute PAL beat quantization")
            require(end <= manifest["scoreTicks"], "Manifest event exceeds the score boundary")
            if event["midi"] is None:
                require(event["frequencyWord"] == 0 and event["gateOffTick"] is None, "Manifest rest has a pitched frequency or gate edge")
                continue
            count += 1
            word = rounded(440 * 2 ** ((event["midi"] - 69) / 12) * 2**24 / PAL_CLOCK)
            gap = 0 if duration == 1 else min(2, max(1, rounded(duration * 0.1)))
            off = end - gap
            require(event["frequencyWord"] == word, "Manifest frequency disagrees with MIDI and the PAL clock")
            require(event["gateOffTick"] == off, "Manifest gate edge disagrees with the note articulation contract")
            for tick, address, value in [(start, base, word & 255), (start, base + 1, word >> 8), (start, base + 4, waveform | 1), (off, base + 4, waveform)]:
                writes.append((tick, order, address, value))
                order += 1
        counts.append(count)
    total = manifest["totalTicks"]
    require(isinstance(total, int) and total > manifest["scoreTicks"], "Manifest has no release tail")
    for voice, part in enumerate(manifest["voices"]):
        writes.append((total, order, 0xd404 + voice * 7, part["instrument"]["waveform"]))
        order += 1
    writes.append((total, order, 0xd418, 0))
    expected = [(tick, address, value) for tick, _, address, value in sorted(writes)]
    declared = [(write["tick"], write["address"], write["value"]) for write in manifest["writes"]]
    require(expected == declared, "Manifest writes disagree with the independently derived musical schedule")
    return expected, counts


def expected_initialization(manifest):
    writes = [(0xd400 + offset, 0) for offset in range(24, -1, -1)]
    for voice, part in enumerate(manifest["voices"]):
        base = 0xd400 + voice * 7
        instrument = part["instrument"]
        width = instrument.get("pulseWidth", 0x800)
        writes.extend([(base + 4, instrument["waveform"]), (base + 5, instrument["attackDecay"]), (base + 6, instrument["sustainRelease"]), (base + 2, width & 255), (base + 3, width >> 8)])
    writes.append((0xd418, manifest["volume"]))
    return writes


class SidMemory:
    def __init__(self):
        self.data = [0] * 65536
        self.tick = None
        self.writes = []
        self.reads = []

    def __getitem__(self, address):
        if 0xd400 <= address <= 0xd418:
            self.reads.append(address)
            return 0xff
        return self.data[address]

    def __setitem__(self, address, value):
        self.data[address] = value
        if 0xd400 <= address <= 0xd418:
            self.writes.append((self.tick, address, value))


def verify_callable(manifest, sid_path):
    """Execute init and every PAL tick; require exact writes, ending and restart."""
    expected, counts = expected_schedule(manifest)
    sid = Path(sid_path).read_bytes()
    require(sid[:4] == b"PSID" and int.from_bytes(sid[4:6], "big") == 2, "Exact player verification requires PSID v2")
    data_offset = int.from_bytes(sid[6:8], "big")
    load = int.from_bytes(sid[8:10], "big")
    init = int.from_bytes(sid[10:12], "big")
    play = int.from_bytes(sid[12:14], "big")
    require(data_offset == 0x7c and (load, init, play) == (0x1000, 0x1000, 0x1003), "PSID does not use the arrangement player's load and entry addresses")
    require(int.from_bytes(sid[14:16], "big") == 1 and sid[18:22] == bytes(4), "PSID does not declare one VBI-scheduled song")
    require(int.from_bytes(sid[118:120], "big") == 0x24 and sid[122:124] == bytes(2), "PSID does not declare one PAL MOS8580")
    payload = sid[data_offset:]
    end = load + len(payload)
    require(end <= 0xa000 and end == manifest["payloadEndAddress"], "SID payload bounds disagree with the manifest")
    symbols = manifest["symbols"]
    require((symbols["init"], symbols["play"]) == (init, play), "Manifest entry addresses disagree with PSID")
    memory = SidMemory()
    memory.data[load:end] = payload
    memory.data[:256] = list(range(256))
    zero_page = memory.data[:256]
    cpu = cpu_type()(memory=memory)
    cpu.a = 0
    cpu.y = 0xa5

    def call(address):
        cpu.stPushWord(0x01ff)
        cpu.pc = address
        start_cycles = cpu.processorCycles
        for _ in range(CYCLES_PER_FRAME // 2):
            if cpu.pc == 0x0200:
                require(cpu.sp == 0xff, "Player did not preserve the caller's stack")
                require(cpu.y == 0xa5 and memory.data[:256] == zero_page, "Player did not preserve Y and zero page")
                require(not memory.reads, "Player read a write-only SID register")
                return cpu.processorCycles - start_cycles
            cpu.step()
        raise ValueError("Player did not return within one PAL frame's instruction budget")

    init_cycles = call(init)
    initialized = [(address, value) for _, address, value in memory.writes]
    require(initialized == expected_initialization(manifest), "Initialization writes differ from the manifest's instrument contract")
    memory.writes.clear()
    max_cycles = 0
    total = manifest["totalTicks"]
    for tick in range(total + 1):
        memory.tick = tick
        cycles = call(play)
        require(cycles < CYCLES_PER_FRAME, f"Player exceeds the PAL frame cycle budget at tick {tick}")
        max_cycles = max(max_cycles, cycles)
        require(memory.data[symbols["finished"]] == int(tick == total), f"Player finished at the wrong tick {tick}")
    if memory.writes != expected:
        for index, (actual, wanted) in enumerate(zip(memory.writes, expected)):
            if actual != wanted:
                raise ValueError(f"SID writes differ at record {index}: observed {actual}, expected {wanted}")
        raise ValueError(f"SID writes differ in count: observed {len(memory.writes)}, expected {len(expected)}")
    require(memory.data[symbols["ticks_left_low"]:symbols["ticks_left_high"] + 1] == [0, 0], "Player countdown did not reach zero")
    pointer = int.from_bytes(bytes(memory.data[symbols["stream_read"] + 1:symbols["stream_read"] + 3]), "little")
    require(pointer == symbols["event_stream_end"], "Player cursor did not reach the complete ending")
    final_state = memory.data[load:end]
    final_writes = list(memory.writes)
    for tick in range(total + 1, total + 4):
        memory.tick = tick
        call(play)
    require(memory.writes == final_writes and memory.data[load:end] == final_state, "Player mutates its finished state or continues writing SID registers")
    memory.tick = None
    memory.writes.clear()
    cpu.a = 0
    call(init)
    require([(address, value) for _, address, value in memory.writes] == initialized, "Player initialization does not restart deterministically")
    memory.writes.clear()
    memory.tick = 0
    call(play)
    require(memory.writes == [write for write in expected if write[0] == 0], "Player restart does not reproduce tick zero")
    return {"cpu": "py65 NMOS 6502", "noteCounts": counts, "initWriteCount": len(initialized), "playWriteCount": len(expected), "checkedTicks": total + 1, "initCycles": init_cycles, "maximumPlayCycles": max_cycles, "frameCycleBudget": CYCLES_PER_FRAME, "finishedAtTick": total, "zeroPagePreserved": True, "restartVerified": True, "postEndingStatePreserved": True}
