import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_player import cpu_type


CYCLES_PER_FRAME = 312 * 63
PAL_CLOCK = 17734475 / 18
TICKS_PER_SECOND = PAL_CLOCK / CYCLES_PER_FRAME


class Memory:
    def __init__(self):
        self.data = [0] * 65536
        self.cpu = None
        self.tick = None
        self.sid_writes = []
        self.sid_reads = []

    def __getitem__(self, address):
        if address == 0xD011:
            raster = self.cpu.processorCycles % CYCLES_PER_FRAME
            return 0x1B | (0x80 if raster >= 256 * 63 else 0)
        if 0xD400 <= address <= 0xD418:
            self.sid_reads.append(address)
            return 0xFF
        return self.data[address]

    def __setitem__(self, address, value):
        self.data[address] = value
        if 0xD400 <= address <= 0xD418:
            tick = self.tick if self.tick is not None else self.cpu.processorCycles // CYCLES_PER_FRAME
            self.sid_writes.append((tick, address, value))


class Machine:
    def __init__(self, directory, name="fixture"):
        self.manifest = json.loads((directory / f"{name}.events.json").read_text())
        self.symbols = self.manifest["symbols"]
        self.memory = Memory()
        self.cpu = cpu_type()(memory=self.memory)
        self.memory.cpu = self.cpu
        prg = (directory / f"{name}.prg").read_bytes()
        load = int.from_bytes(prg[:2], "little")
        self.memory.data[load:load + len(prg) - 2] = prg[2:]
        self.play_frames = []

    def call(self, entry, max_steps=10000):
        self.cpu.stPushWord(0x01FF)
        self.cpu.pc = entry
        start_cycles = self.cpu.processorCycles
        for _ in range(max_steps):
            if self.cpu.pc == 0x0200:
                return self.cpu.processorCycles - start_cycles
            if self.cpu.pc == self.symbols["play"]:
                self.play_frames.append(self.cpu.processorCycles // CYCLES_PER_FRAME)
            self.cpu.step()
        raise AssertionError("Routine did not return within the instruction budget")


def build(score, directory):
    source = directory / "input.json"
    source.write_text(json.dumps(score))
    subprocess.run(["bun", "scripts/build-arrangement.ts", str(source), str(directory), "fixture"], cwd=ROOT, check=True, timeout=30, capture_output=True)
    return Machine(directory)


def instrument(waveform=16):
    return {"waveform": waveform, "attackDecay": 2, "sustainRelease": 0x92, "pulseWidth": 0x600}


def ticks(beat, bpm):
    return int(beat * 60 / bpm * TICKS_PER_SECOND + 0.5)


def expected_writes(score):
    writes = []
    sequence = 0
    for voice, track in enumerate(score["voices"]):
        waveform = track["instrument"]["waveform"]
        base = 0xD400 + voice * 7
        for event in track["events"]:
            if event["midi"] is None:
                continue
            start = ticks(event["startBeat"], score["quarterBpm"])
            end = ticks(event["startBeat"] + event["durationBeats"], score["quarterBpm"])
            gap = 0 if end - start == 1 else min(2, max(1, int((end - start) * 0.1 + 0.5)))
            frequency = int(440 * 2 ** ((event["midi"] - 69) / 12) * 2 ** 24 / PAL_CLOCK + 0.5)
            for tick, address, value in [(start, base, frequency & 255), (start, base + 1, frequency >> 8), (start, base + 4, waveform | 1), (end - gap, base + 4, waveform)]:
                writes.append((tick, sequence, address, value))
                sequence += 1
    total = ticks(score["totalBeats"], score["quarterBpm"]) + score["tailTicks"]
    for voice, track in enumerate(score["voices"]):
        writes.append((total, sequence, 0xD404 + voice * 7, track["instrument"]["waveform"]))
        sequence += 1
    writes.append((total, sequence, 0xD418, 0))
    return [(tick, address, value) for tick, _, address, value in sorted(writes)]


class ThreeVoiceCpuTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="three-voice-cpu-")
        cls.directory = Path(cls.temporary.name)
        cls.score = {
            "title": "Independent CPU fixture", "composer": "Test fixture", "quarterBpm": 72,
            "totalBeats": 151, "tailTicks": 25, "volume": 15,
            "voices": [
                {"instrument": instrument(), "events": [{"startBeat": i / 2, "durationBeats": 0.5, "midi": 76 if i % 2 == 0 else 75} for i in range(300)]},
                {"instrument": instrument(32), "events": [{"startBeat": 0, "durationBeats": 1, "midi": 45}, {"startBeat": 1, "durationBeats": 1, "midi": 45}, {"startBeat": 2, "durationBeats": 1, "midi": None}, {"startBeat": 5, "durationBeats": 0.125, "midi": 48}]},
                {"instrument": instrument(64), "events": [{"startBeat": 4, "durationBeats": 1 / 48, "midi": 57}, {"startBeat": 4 + 1 / 48, "durationBeats": 1, "midi": 60}]},
            ],
        }
        build(cls.score, cls.directory)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_init_restarts_pointer_countdown_and_finished_without_zero_page_or_sid_reads(self):
        machine = Machine(self.directory)
        machine.memory.data[:256] = list(range(256))
        before = machine.memory.data[:256]
        for symbol in ("ticks_left_low", "ticks_left_high", "finished"):
            machine.memory.data[machine.symbols[symbol]] = 0xEE
        machine.memory.data[machine.symbols["stream_read"] + 1:machine.symbols["stream_read"] + 3] = [0xAA, 0xAA]
        machine.call(machine.symbols["init"])
        self.assertEqual(machine.memory.data[:256], before)
        self.assertEqual(machine.memory.sid_reads, [])
        self.assertEqual(machine.memory.data[0xD418], 15)
        for voice, track in enumerate(self.score["voices"]):
            base = 0xD400 + voice * 7
            self.assertEqual(machine.memory.data[base + 5:base + 7], [2, 0x92])
            self.assertEqual(machine.memory.data[base + 4], track["instrument"]["waveform"])
        self.assertEqual(machine.memory.data[machine.symbols["finished"]], 0)
        self.assertEqual(machine.cpu.sp, 0xFF)

    def test_independent_cpu_executes_every_register_write_through_all_pages_and_the_nonlooping_end(self):
        machine = Machine(self.directory)
        machine.call(machine.symbols["init"])
        machine.memory.sid_writes.clear()
        total = ticks(self.score["totalBeats"], 72) + 25
        for tick in range(total + 6):
            machine.memory.tick = tick
            self.assertLess(machine.call(machine.symbols["play"]), CYCLES_PER_FRAME)
            self.assertEqual(machine.memory.data[machine.symbols["finished"]], int(tick >= total))
        expected = expected_writes(self.score)
        self.assertEqual(machine.memory.sid_writes, expected)
        self.assertEqual(machine.memory.sid_reads, [])
        pointer = int.from_bytes(bytes(machine.memory.data[machine.symbols["stream_read"] + 1:machine.symbols["stream_read"] + 3]), "little")
        self.assertEqual(pointer, machine.symbols["event_stream_end"])
        machine.call(machine.symbols["init"])
        machine.memory.sid_writes.clear()
        machine.memory.tick = 0
        machine.call(machine.symbols["play"])
        self.assertEqual(machine.memory.sid_writes, [write for write in expected if write[0] == 0])

    def test_a_16_bit_idle_delay_preserves_the_later_voice_start(self):
        score = {**self.score, "totalBeats": 100, "voices": [{"instrument": instrument(), "events": []}, {"instrument": instrument(), "events": []}, {"instrument": instrument(), "events": [{"startBeat": 80, "durationBeats": 1, "midi": 57}]}]}
        with tempfile.TemporaryDirectory(prefix="three-voice-long-gap-") as temporary:
            machine = build(score, Path(temporary))
            machine.call(machine.symbols["init"])
            machine.memory.sid_writes.clear()
            for tick in range(ticks(100, 72) + 26):
                machine.memory.tick = tick
                machine.call(machine.symbols["play"])
            self.assertEqual(machine.memory.sid_writes, expected_writes(score))

    def test_basic_wrapper_runs_once_per_frame_and_restores_cpu_ports_flags_and_zero_page(self):
        score = {**self.score, "title": "Short other arrangement", "quarterBpm": 120, "totalBeats": 2, "tailTicks": 5, "voices": [{"instrument": instrument(), "events": [{"startBeat": 0, "durationBeats": 1, "midi": 60}]}, {"instrument": instrument(32), "events": [{"startBeat": 0.5, "durationBeats": 1, "midi": 36}]}, {"instrument": instrument(64), "events": [{"startBeat": 1, "durationBeats": 1, "midi": 67}]}]}
        with tempfile.TemporaryDirectory(prefix="three-voice-wrapper-") as temporary:
            machine = build(score, Path(temporary))
            machine.memory.data[:256] = list(range(256))
            machine.memory.data[0:2] = [0x2F, 0x35]
            before = machine.memory.data[:256]
            machine.cpu.p = machine.cpu.UNUSED | machine.cpu.CARRY | machine.cpu.DECIMAL
            previous_flags = machine.cpu.p
            total = ticks(2, 120) + 5
            machine.call(machine.symbols["standalone"], max_steps=(total + 3) * CYCLES_PER_FRAME // 2)
            self.assertEqual(machine.play_frames, list(range(total + 1)))
            self.assertEqual(machine.memory.data[:256], before)
            self.assertEqual(machine.cpu.p & ~machine.cpu.BREAK, previous_flags)
            self.assertEqual(machine.cpu.sp, 0xFF)
            self.assertEqual(machine.memory.sid_reads, [])
            self.assertEqual(machine.memory.sid_writes[-4:], expected_writes(score)[-4:])


if __name__ == "__main__":
    unittest.main()
