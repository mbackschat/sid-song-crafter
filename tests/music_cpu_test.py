import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from py65.devices.mpu6502 import MPU


ROOT = Path(__file__).resolve().parents[1]
CYCLES_PER_FRAME = 312 * 63


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
            word = self.data[0xD400] | (self.data[0xD401] << 8)
            self.sid_writes.append((tick, address, value, word))


class Machine:
    def __init__(self, prg, symbols):
        self.memory = Memory()
        self.cpu = MPU(memory=self.memory)
        self.memory.cpu = self.cpu
        load = int.from_bytes(prg[:2], "little")
        self.memory.data[load:load + len(prg) - 2] = prg[2:]
        self.symbols = symbols
        self.play_frames = []

    def call(self, entry, max_steps=2000):
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


def outputs(directory):
    manifest = json.loads((directory / "fuer-elise-opening.events.json").read_text())
    prg = (directory / "fuer-elise-opening.prg").read_bytes()
    return Machine(prg, manifest["symbols"]), manifest


class MusicCpuTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["bun", "scripts/build-song.ts"], cwd=ROOT, check=True, timeout=30, capture_output=True)

    def test_callable_init_clears_sid_without_register_readback_and_restarts_state(self):
        machine, manifest = outputs(ROOT / "build")
        machine.memory.data[0xD400:0xD419] = [0xFF] * 25
        for symbol in ("event_index", "ticks_left", "finished"):
            machine.memory.data[manifest["symbols"][symbol]] = 0xEE
        machine.cpu.a = 0
        machine.call(manifest["symbols"]["init"])
        registers = machine.memory.data[0xD400:0xD419]
        self.assertEqual(registers[5:7], [0x06, 0x41])
        self.assertEqual(registers[24], 15)
        self.assertTrue(all(value == 0 for i, value in enumerate(registers) if i not in (5, 6, 24)))
        self.assertEqual(machine.memory.sid_reads, [])
        for symbol in ("event_index", "ticks_left", "finished"):
            self.assertEqual(machine.memory.data[manifest["symbols"][symbol]], 0)
        self.assertEqual(machine.cpu.sp, 0xFF)

    def test_play_executes_all_expected_notes_gate_releases_and_the_nonlooping_end(self):
        machine, manifest = outputs(ROOT / "build")
        machine.call(manifest["symbols"]["init"])
        machine.memory.sid_writes.clear()
        for tick in range(140):
            machine.memory.tick = tick
            cycles = machine.call(manifest["symbols"]["play"])
            self.assertLess(cycles, 250)
            self.assertEqual(machine.memory.data[manifest["symbols"]["finished"]], int(tick >= 129))
        on = [(tick, word) for tick, address, value, word in machine.memory.sid_writes if address == 0xD404 and value == 0x11]
        self.assertEqual(on, list(zip([0, 10, 21, 31, 42, 52, 63, 73, 84], [0x2BDA, 0x2964, 0x2BDA, 0x2964, 0x2BDA, 0x20DA, 0x2711, 0x22CE, 0x1D44])))
        off = [tick for tick, address, value, _ in machine.memory.sid_writes if address == 0xD404 and value == 0x10]
        self.assertEqual(off, [8, 19, 29, 40, 50, 61, 71, 82, 102, 104, 127, 129])
        volume = [(tick, value) for tick, address, value, _ in machine.memory.sid_writes if address == 0xD418]
        self.assertEqual(volume, [(129, 0)])
        self.assertEqual(machine.memory.sid_reads, [])
        writes_at_end = list(machine.memory.sid_writes)
        machine.call(manifest["symbols"]["play"])
        self.assertEqual(machine.memory.sid_writes, writes_at_end)
        machine.call(manifest["symbols"]["init"])
        machine.memory.tick = 0
        machine.call(manifest["symbols"]["play"])
        self.assertEqual(machine.memory.sid_writes[-1], (0, 0xD404, 0x11, 0x2BDA))

    def test_standalone_prg_calls_the_player_once_per_pal_frame_and_restores_the_port(self):
        machine, manifest = outputs(ROOT / "build")
        machine.memory.data[0] = 0x2F
        machine.memory.data[1] = 0x35
        machine.cpu.p = machine.cpu.UNUSED | machine.cpu.CARRY | machine.cpu.DECIMAL
        previous_flags = machine.cpu.p
        machine.call(manifest["symbols"]["standalone"], max_steps=(manifest["totalTicks"] + 2) * CYCLES_PER_FRAME // 2)
        self.assertEqual(machine.play_frames, list(range(130)))
        on = [(tick, word) for tick, address, value, word in machine.memory.sid_writes if address == 0xD404 and value == 0x11]
        self.assertEqual(on, list(zip([0, 10, 21, 31, 42, 52, 63, 73, 84], [0x2BDA, 0x2964, 0x2BDA, 0x2964, 0x2BDA, 0x20DA, 0x2711, 0x22CE, 0x1D44])))
        self.assertEqual(machine.memory.sid_writes[-2][0], 129)
        self.assertEqual(machine.memory.data[0:2], [0x2F, 0x35])
        self.assertEqual(machine.cpu.p & ~machine.cpu.BREAK, previous_flags)
        self.assertEqual(machine.cpu.sp, 0xFF)
        self.assertEqual(machine.memory.sid_reads, [])

    def test_repeated_notes_and_explicit_rests_execute_after_255_total_ticks(self):
        score = json.loads((ROOT / "songs/fuer-elise-opening.json").read_text())
        score["notes"] = [{"pitch": "E5", "sixteenths": 16}, {"pitch": "E5", "sixteenths": 16}, {"pitch": None, "sixteenths": 4}, {"pitch": "A4", "sixteenths": 2}]
        with tempfile.TemporaryDirectory(prefix="c64-articulation-") as temporary:
            directory = Path(temporary)
            source = directory / "score.json"
            source.write_text(json.dumps(score))
            subprocess.run(["bun", "--eval", "import { buildSong } from './scripts/build-song.ts'; await buildSong({ source: process.argv[1], output: process.argv[2] });", str(source), str(directory)], cwd=ROOT, check=True, timeout=30, capture_output=True)
            machine, manifest = outputs(directory)
            machine.call(manifest["symbols"]["init"])
            machine.memory.sid_writes.clear()
            for tick in range(manifest["totalTicks"] + 5):
                machine.memory.tick = tick
                machine.call(manifest["symbols"]["play"])
            on = [(tick, word) for tick, address, value, word in machine.memory.sid_writes if address == 0xD404 and value == 0x11]
            self.assertEqual(on, [(0, 0x2BDA), (167, 0x2BDA), (376, 0x1D44)])
            self.assertEqual([(tick, word) for tick, address, _, word in machine.memory.sid_writes if address == 0xD401 and word == 0], [(334, 0), (397, 0)])
            self.assertEqual([tick for tick, address, value, _ in machine.memory.sid_writes if address == 0xD404 and value == 0x10][:4], [165, 332, 334, 374])
            self.assertEqual(machine.memory.data[0xD418], 0)


if __name__ == "__main__":
    unittest.main()
