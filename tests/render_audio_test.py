import math
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import wave


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / ".local/bin/render-sid"
RATE = 44100
ROM_DIR = ROOT / ".tools/vice-headless-3.9/source/data/C64"
ROM_FILES = ("kernal-901227-03.bin", "basic-901226-01.bin", "chargen-901225-01.bin")


def read_samples(path):
    with wave.open(str(path), "rb") as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, RATE)
        data = wav.readframes(wav.getnframes())
    return struct.unpack("<" + "h" * (len(data) // 2), data)


def rms(samples):
    centre = sum(samples) / len(samples)
    return math.sqrt(sum((value - centre) ** 2 for value in samples) / len(samples))


def frequency(samples):
    centre = sum(samples) / len(samples)
    crossings = [index for index in range(1, len(samples)) if samples[index - 1] <= centre < samples[index]]
    return (len(crossings) - 1) * RATE / (crossings[-1] - crossings[0])


def write_a4_sid(path):
    # A separate PSID fixture settles pitch against 440 Hz without using the song compiler.
    init = bytes.fromhex("A9 0F 8D 18 D4 A9 45 8D 00 D4 A9 1D 8D 01 D4 A9 00 8D 05 D4 A9 F0 8D 06 D4 A9 11 8D 04 D4 60")
    header = bytearray(0x7C)
    header[:4] = b"PSID"
    struct.pack_into(">7HI", header, 4, 2, 0x7C, 0x1000, 0x1000, 0x1000 + len(init), 1, 1, 0)
    struct.pack_into(">H", header, 0x76, 0x24)
    path.write_bytes(header + init + b"\x60")


def write_basic_a4_sid(path):
    # Tokenized BASIC POKEs require the real interpreter rather than the PSID init/play driver.
    word = round(440 * 2**24 / (14318181.82 / 14))
    commands = [b"\x97" + f"{0xd400 + offset},{value}".encode()
                for offset, value in ((24, 15), (0, word & 255), (1, word >> 8), (5, 0), (6, 240), (4, 17))]
    first_line = b":".join(commands) + b"\0"
    program = struct.pack("<HH", 0x0801 + 4 + len(first_line), 10) + first_line
    program += struct.pack("<HH", 0x0801 + len(program) + 8, 20) + b"\x8920\0\0\0"
    header = bytearray(0x7c)
    header[:4] = b"RSID"
    struct.pack_into(">7HI", header, 4, 2, 0x7c, 0, 0, 0, 1, 1, 0)
    struct.pack_into(">H", header, 0x76, 0x1a)
    path.write_bytes(header + struct.pack("<H", 0x0801) + program)


def write_ntsc_clock_sid(path):
    # A triangle oscillator and a per-VBI counter independently expose clock pitch and update cadence.
    word = round(440 * 2**24 / (14318181.82 / 14))
    init = bytearray()
    for offset, value in ((24, 15), (0, word & 255), (1, word >> 8), (5, 0), (6, 0xf0), (4, 0x11)):
        init.extend((0xa9, value, 0x8d, offset, 0xd4))
    init.extend(bytes.fromhex("A9 00 8D 00 11 8D 02 D4 60"))
    play = bytes.fromhex("EE 00 11 AD 00 11 8D 02 D4 60")
    header = bytearray(0x7c)
    header[:4] = b"PSID"
    struct.pack_into(">7HI", header, 4, 2, 0x7c, 0x1000, 0x1000, 0x1000 + len(init), 1, 1, 0)
    struct.pack_into(">H", header, 0x76, 0x28)
    path.write_bytes(header + init + play)


def write_two_sid_fixture(path, default_song=1, left=True, right=True, clock="pal", model="8580", counter=False):
    # Hand-coded independent oscillators distinguish stereo routing from duplicated mono.
    init = bytearray((0xc9, default_song - 1, 0xf0, 1, 0x60))
    for base, hz, enabled in ((0xd400, 440, left), (0xd420, 660, right)):
        cpu_clock = 17734475 / 18 if clock == "pal" else 14318181.82 / 14
        word = round(hz * 2**24 / cpu_clock)
        for offset, value in ((24, 15 if enabled else 0), (0, word & 255), (1, word >> 8), (5, 0), (6, 0xf0), (4, 0x11)):
            address = base + offset
            init.extend((0xa9, value, 0x8d, address & 255, address >> 8))
    if counter:
        init.extend(bytes.fromhex("A9 00 8D 00 11 8D 02 D4 8D 22 D4"))
    init.append(0x60)
    play = bytes.fromhex("EE 00 11 AD 00 11 8D 02 D4 8D 22 D4 60") if counter else b"\x60"
    header = bytearray(0x7c)
    header[:4] = b"PSID"
    struct.pack_into(">7HI", header, 4, 3, 0x7c, 0x1000, 0x1000, 0x1000 + len(init), 2, default_song, 0)
    flags = (0xa0 if model == "8580" else 0x50) | (4 if clock == "pal" else 8)
    struct.pack_into(">H", header, 0x76, flags)
    header[0x7a] = 0x42
    path.write_bytes(header + init + play)


def write_native_cia_sid(path, clock="ntsc", model="6581", dual=True, left=True, right=True):
    # A RAM-vector CIA IRQ at 8192 cycles distinguishes native execution from a VBI play callback.
    init = bytearray(bytes.fromhex("78 A9 35 85 01 A9 7F 8D 0D DC 8D 0D DD A9 00 8D 0E DC 8D 0E DD 8D 1A D0 AD 0D DC AD 0D DD"))
    chips = [(0xd400, 440, left)] + ([(0xd420, 660, right)] if dual else [])
    cpu_clock = 17734475 / 18 if clock == "pal" else 14318181.82 / 14
    for base, hz, enabled in chips:
        word = round(hz * 2**24 / cpu_clock)
        for offset, value in ((24, 15 if enabled else 0), (0, word & 255), (1, word >> 8), (2, 0), (5, 0), (6, 0xf0), (4, 0x11)):
            address = base + offset
            init.extend((0xa9, value, 0x8d, address & 255, address >> 8))
    init.extend(bytes.fromhex("A9 00 8D 00 11"))
    vector = len(init)
    init.extend(bytes.fromhex("A9 00 8D FE FF A9 00 8D FF FF A9 FF 8D 04 DC A9 1F 8D 05 DC A9 81 8D 0D DC A9 11 8D 0E DC 58 60"))
    irq_address = 0x1000 + len(init)
    init[vector + 1], init[vector + 6] = irq_address & 255, irq_address >> 8
    irq = bytearray(bytes.fromhex("48 AD 0D DC EE 00 11 AD 00 11 8D 02 D4"))
    if dual:
        irq.extend(bytes.fromhex("8D 22 D4"))
    irq.extend(bytes.fromhex("68 40"))
    header = bytearray(0x7c)
    header[:4] = b"RSID"
    struct.pack_into(">7HI", header, 4, 3 if dual else 2, 0x7c, 0, 0x1000, 0, 1, 1, 0)
    flags = (0x50 if model == "6581" else 0xa0) if dual else (0x10 if model == "6581" else 0x20)
    struct.pack_into(">H", header, 118, flags | (4 if clock == "pal" else 8))
    header[122] = 0x42 if dual else 0
    path.write_bytes(header + struct.pack("<H", 0x1000) + init + irq)


def read_stereo_samples(path):
    with wave.open(str(path), "rb") as source:
        assert (source.getnchannels(), source.getsampwidth(), source.getframerate()) == (2, 2, RATE)
        frames = source.getnframes()
        samples = struct.unpack("<" + "h" * (frames * 2), source.readframes(frames))
    return frames, samples[0::2], samples[1::2]


def write_three_voice_sid(path):
    init = bytearray()
    for voice, hz in enumerate((330, 440, 660)):
        word = round(hz * 2**24 / (17734475 / 18))
        for offset, value in ((0, word & 255), (1, word >> 8), (5, 0), (6, 0xf0), (4, 0x11)):
            address = 0xd400 + voice * 7 + offset
            init.extend((0xa9, value, 0x8d, address & 255, address >> 8))
    init.extend(bytes.fromhex("A9 0F 8D 18 D4 60"))
    header = bytearray(0x7c)
    header[:4] = b"PSID"
    struct.pack_into(">7HI", header, 4, 2, 0x7c, 0x1000, 0x1000, 0x1000 + len(init), 1, 1, 0)
    struct.pack_into(">H", header, 0x76, 0x24)
    path.write_bytes(header + init + b"\x60")


def write_two_subtune_sid(path, default_song):
    # Hand-coded init exposes its incoming A and chooses pitch independently of the song compiler.
    init = bytearray(bytes.fromhex("8D 05 D4 AA"))
    table_loads = []
    for offset in (0, 1):
        table_loads.append(len(init))
        init.extend((0xbd, 0, 0, 0x8d, offset, 0xd4))
    init.extend(bytes.fromhex("A9 0F 8D 18 D4 A9 F0 8D 06 D4 A9 11 8D 04 D4 60"))
    words = [round(hz * 2**24 / (17734475 / 18)) for hz in (440, 660)]
    tables = bytes([word & 255 for word in words] + [word >> 8 for word in words])
    for offset, position in enumerate(table_loads):
        struct.pack_into("<H", init, position + 1, 0x1000 + len(init) + 1 + offset * 2)
    header = bytearray(0x7c)
    header[:4] = b"PSID"
    struct.pack_into(">7HI", header, 4, 2, 0x7c, 0x1000, 0x1000, 0x1000 + len(init), 2, default_song, 0)
    struct.pack_into(">H", header, 0x76, 0x24)
    path.write_bytes(header + init + b"\x60" + tables)


class HeadlessRenderTest(unittest.TestCase):
    def test_native_two_sid_rsid_executes_independent_cia_irq_at_the_declared_clock(self):
        for clock in ("pal", "ntsc"):
            for model in ("6581", "8580"):
                with self.subTest(clock=clock, model=model), tempfile.TemporaryDirectory() as directory:
                    sid, output = Path(directory) / "native.sid", Path(directory) / "native.wav"
                    write_native_cia_sid(sid, clock=clock, model=model)
                    original = sid.read_bytes()
                    result = subprocess.run([str(RENDERER), str(sid), str(output), "1.2", "--clock", clock],
                                            capture_output=True, text=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    frames, left, right = read_stereo_samples(output)
                    self.assertEqual(frames, round(1.2 * RATE))
                    for samples, expected in ((left, 440), (right, 660)):
                        self.assertGreater(rms(samples[RATE // 4:RATE]), 100)
                        self.assertAlmostEqual(frequency(samples[RATE // 4:RATE]), expected, delta=3)
                    rows = [row.split("\t") for row in Path(str(output) + ".registers.tsv").read_text().splitlines()]
                    self.assertEqual(rows[0], ["time_ms", "registers_hex", "registers_sid2_hex"])
                    snapshots = [(int(row[0]), bytes.fromhex(row[1]), bytes.fromhex(row[2])) for row in rows[1:]]
                    first, last = snapshots[4], snapshots[-1]
                    cpu_clock = 17734475 / 18 if clock == "pal" else 14318181.82 / 14
                    expected_updates = (last[0] - first[0]) * cpu_clock / (1000 * 8192)
                    for chip in (1, 2):
                        self.assertAlmostEqual(last[chip][2] - first[chip][2], expected_updates, delta=1.1)
                    self.assertEqual(sid.read_bytes(), original)

    def test_native_two_sid_rsid_keeps_raw_chip_outputs_separate(self):
        for enabled_left, enabled_right in ((True, False), (False, True)):
            with self.subTest(left=enabled_left, right=enabled_right), tempfile.TemporaryDirectory() as directory:
                sid, output = Path(directory) / "native.sid", Path(directory) / "native.wav"
                write_native_cia_sid(sid, left=enabled_left, right=enabled_right)
                result = subprocess.run([str(RENDERER), str(sid), str(output), "0.5", "--clock", "ntsc"],
                                        capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                _, left, right = read_stereo_samples(output)
                for samples, enabled in ((left, enabled_left), (right, enabled_right)):
                    if enabled:
                        self.assertGreater(rms(samples[RATE // 4:]), 100)
                    else:
                        self.assertLess(rms(samples[RATE // 4:]), 1)

    def test_native_two_sid_rsid_rejects_unsupported_header_profiles_before_output(self):
        mutations = (
            ("version", lambda data: struct.pack_into(">H", data, 4, 2)),
            ("third-chip version", lambda data: struct.pack_into(">H", data, 4, 4)),
            ("data offset", lambda data: struct.pack_into(">H", data, 6, 126)),
            ("header load", lambda data: struct.pack_into(">H", data, 8, 0x1000)),
            ("play callback", lambda data: struct.pack_into(">H", data, 12, 0x1000)),
            ("reserved speed", lambda data: data.__setitem__(21, 1)),
            ("relocation", lambda data: data.__setitem__(120, 0x20)),
            ("other address", lambda data: data.__setitem__(122, 0x44)),
            ("invalid address", lambda data: data.__setitem__(122, 0x41)),
            ("duplicate address", lambda data: data.__setitem__(122, 0x40)),
            ("third SID", lambda data: data.__setitem__(123, 0x44)),
            ("mixed models", lambda data: struct.pack_into(">H", data, 118, 0x98)),
            ("unknown clock", lambda data: struct.pack_into(">H", data, 118, 0x50)),
            ("BASIC", lambda data: struct.pack_into(">H", data, 118, 0x5a)),
            ("MUS", lambda data: struct.pack_into(">H", data, 118, 0x59)),
        )
        for name, mutate in mutations:
            for existing in (False, True):
                with self.subTest(name=name, existing=existing), tempfile.TemporaryDirectory() as directory:
                    sid, output = Path(directory) / "native.sid", Path(directory) / "preserved.wav"
                    write_native_cia_sid(sid)
                    raw = bytearray(sid.read_bytes())
                    mutate(raw)
                    sid.write_bytes(raw)
                    trace = Path(str(output) + ".registers.tsv")
                    if existing:
                        output.write_bytes(b"Existing audio")
                        trace.write_bytes(b"Existing trace")
                    result = subprocess.run([str(RENDERER), str(sid), str(output), "0.1", "--clock", "ntsc"],
                                            capture_output=True, text=True, timeout=20)
                    self.assertNotEqual(result.returncode, 0)
                    if existing:
                        self.assertEqual(output.read_bytes(), b"Existing audio")
                        self.assertEqual(trace.read_bytes(), b"Existing trace")
                    else:
                        self.assertFalse(output.exists())
                        self.assertFalse(trace.exists())

    def test_basic_requires_explicit_roms_before_creating_or_truncating_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            sid, output = Path(directory) / "basic.sid", Path(directory) / "basic.wav"
            write_basic_a4_sid(sid)
            trace = Path(str(output) + ".registers.tsv")
            for existing in (False, True):
                with self.subTest(existing=existing):
                    if existing:
                        output.write_bytes(b"Existing audio")
                        trace.write_bytes(b"Existing trace")
                    result = subprocess.run([str(RENDERER), str(sid), str(output), "0.1"],
                                            capture_output=True, text=True, timeout=20)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("RSID BASIC requires --rom-dir", result.stderr)
                    if existing:
                        self.assertEqual(output.read_bytes(), b"Existing audio")
                        self.assertEqual(trace.read_bytes(), b"Existing trace")
                    else:
                        self.assertFalse(output.exists())
                        self.assertFalse(trace.exists())

    @unittest.skipUnless(all((ROM_DIR / name).is_file() for name in ROM_FILES), "C64 ROMs are optional local assets")
    def test_basic_rom_backed_interpreter_produces_the_independent_a4_tone(self):
        with tempfile.TemporaryDirectory() as directory:
            sid, output = Path(directory) / "basic.sid", Path(directory) / "basic.wav"
            write_basic_a4_sid(sid)
            original = sid.read_bytes()
            result = subprocess.run([str(RENDERER), str(sid), str(output), "2", "--clock", "ntsc",
                                     "--rom-dir", str(ROM_DIR)], capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            samples = read_samples(output)
            self.assertEqual(len(samples), 2 * RATE)
            self.assertGreater(rms(samples[RATE:]), 100)
            self.assertAlmostEqual(frequency(samples[RATE:]), 440, delta=3)
            self.assertEqual(sid.read_bytes(), original)

    def test_missing_malformed_and_unrecognized_roms_preserve_outputs(self):
        sizes = (8192, 8192, 4096)
        cases = [(None, None)] + [(index, size + delta) for index, size in enumerate(sizes) for delta in (-1, 1)]
        cases += [(index, None) for index in range(3)]
        with tempfile.TemporaryDirectory() as directory:
            sid, output = Path(directory) / "basic.sid", Path(directory) / "basic.wav"
            write_basic_a4_sid(sid)
            roms = Path(directory) / "roms"
            roms.mkdir()
            trace = Path(str(output) + ".registers.tsv")
            for changed, changed_size in cases:
                for index, (name, size) in enumerate(zip(ROM_FILES, sizes)):
                    path = roms / name
                    path.unlink(missing_ok=True)
                    if changed != index or changed_size is not None:
                        path.write_bytes(bytes(changed_size if changed == index else size))
                for existing in (False, True):
                    with self.subTest(changed=changed, changed_size=changed_size, existing=existing):
                        if existing:
                            output.write_bytes(b"Existing audio")
                            trace.write_bytes(b"Existing trace")
                        else:
                            output.unlink(missing_ok=True)
                            trace.unlink(missing_ok=True)
                        result = subprocess.run([str(RENDERER), str(sid), str(output), "0.1", "--rom-dir", str(roms)],
                                                capture_output=True, text=True, timeout=20)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn("ROM", result.stderr)
                        if existing:
                            self.assertEqual(output.read_bytes(), b"Existing audio")
                            self.assertEqual(trace.read_bytes(), b"Existing trace")
                        else:
                            self.assertFalse(output.exists())
                            self.assertFalse(trace.exists())

    def test_rom_options_reject_empty_missing_duplicate_and_nonexistent_directories_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            sid, output = Path(directory) / "a4.sid", Path(directory) / "preserved.wav"
            write_a4_sid(sid)
            trace = Path(str(output) + ".registers.tsv")
            cases = [["--rom-dir"], ["--rom-dir", ""], ["--rom-dir", str(Path(directory) / "missing")],
                     ["--rom-dir", str(ROM_DIR), "--rom-dir", str(ROM_DIR)]]
            for options in cases:
                with self.subTest(options=options):
                    output.write_bytes(b"Existing audio")
                    trace.write_bytes(b"Existing trace")
                    result = subprocess.run([str(RENDERER), str(sid), str(output), "0.1", *options],
                                            capture_output=True, text=True, timeout=20)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("rom", result.stderr.lower())
                    self.assertEqual(output.read_bytes(), b"Existing audio")
                    self.assertEqual(trace.read_bytes(), b"Existing trace")

    def test_unknown_model_assumptions_match_declared_model_audio_and_preserve_source_and_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            sid = Path(directory) / "unknown.sid"
            write_a4_sid(sid)
            original = bytearray(sid.read_bytes())
            struct.pack_into(">H", original, 118, 0x04)
            sid.write_bytes(original)
            rendered = {}
            for model, flags in (("MOS6581", 0x14), ("MOS8580", 0x24)):
                with self.subTest(model=model):
                    declared = Path(directory) / f"declared-{model}.sid"
                    data = bytearray(original)
                    struct.pack_into(">H", data, 118, flags)
                    declared.write_bytes(data)
                    outputs = []
                    for source, options, origin in (
                        (sid, ["--assume-sid-model", model, "--subtune", "1", "--clock", "pal", "--voices", "1"], "assumed; declared unknown"),
                        (sid, ["--voices", "1", "--clock", "pal", "--subtune", "1", "--assume-sid-model", model], "assumed; declared unknown"),
                        (declared, ["--clock", "pal", "--voices", "1", "--subtune", "1"], "declared"),
                    ):
                        output = Path(directory) / f"model-{model}-{len(outputs)}.wav"
                        result = subprocess.run([str(RENDERER), str(source), str(output), "0.5", *options],
                                                capture_output=True, text=True, timeout=20)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertIn(f"SID model {model} ({origin})", result.stdout)
                        samples = read_samples(output)
                        self.assertEqual(len(samples), RATE // 2)
                        self.assertGreater(rms(samples[RATE // 4:]), 100)
                        self.assertAlmostEqual(frequency(samples[RATE // 4:]), 440, delta=3)
                        outputs.append((output.read_bytes(), Path(str(output) + ".registers.tsv").read_bytes()))
                    self.assertEqual(outputs[0], outputs[1])
                    self.assertEqual(outputs[0], outputs[2])
                    rendered[model] = outputs[0]
            output = Path(directory) / "fallback.wav"
            result = subprocess.run([str(RENDERER), str(sid), str(output), "0.5"],
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("SID model MOS8580 (fallback; declared unknown)", result.stdout)
            fallback = output.read_bytes(), Path(str(output) + ".registers.tsv").read_bytes()
            self.assertEqual(fallback, rendered["MOS8580"])
            self.assertNotEqual(rendered["MOS6581"][0], rendered["MOS8580"][0])
            self.assertEqual(rendered["MOS6581"][1], rendered["MOS8580"][1])
            self.assertEqual(sid.read_bytes(), original)

    def test_model_assumption_options_reject_invalid_missing_and_duplicate_values_before_output(self):
        arguments = [["--assume-sid-model", value] for value in
                     ("", "6581", "8580", "mos6581", "unknown", " MOS6581", "MOS8580 ")]
        arguments += [["--assume-sid-model"], ["--assume-sid-model", "MOS6581", "--assume-sid-model", "MOS8580"]]
        with tempfile.TemporaryDirectory() as directory:
            sid = Path(directory) / "unknown.sid"
            write_a4_sid(sid)
            data = bytearray(sid.read_bytes())
            struct.pack_into(">H", data, 118, 0x04)
            sid.write_bytes(data)
            for options in arguments:
                for existing in (False, True):
                    with self.subTest(options=options, existing=existing):
                        output = Path(directory) / "invalid.wav"
                        trace = Path(str(output) + ".registers.tsv")
                        if existing:
                            output.write_bytes(b"Existing audio")
                            trace.write_bytes(b"Existing trace")
                        else:
                            output.unlink(missing_ok=True)
                            trace.unlink(missing_ok=True)
                        result = subprocess.run([str(RENDERER), str(sid), str(output), "0.1", *options],
                                                capture_output=True, text=True, timeout=20)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn("model", result.stderr.lower())
                        if existing:
                            self.assertEqual(output.read_bytes(), b"Existing audio")
                            self.assertEqual(trace.read_bytes(), b"Existing trace")
                        else:
                            self.assertFalse(output.exists())
                            self.assertFalse(trace.exists())

    def test_model_assumptions_reject_declared_any_and_multiple_chips_without_truncation(self):
        fixtures = [("single", flags) for flags in (0x14, 0x24, 0x34)]
        fixtures += [("dual", flags) for flags in (0x54, 0xa4, 0x04)]
        for kind, flags in fixtures:
            for model in ("MOS6581", "MOS8580"):
                for existing in (False, True):
                    with self.subTest(kind=kind, flags=flags, model=model, existing=existing), tempfile.TemporaryDirectory() as directory:
                        sid, output = Path(directory) / "unsupported.sid", Path(directory) / "preserved.wav"
                        (write_a4_sid if kind == "single" else write_two_sid_fixture)(sid)
                        data = bytearray(sid.read_bytes())
                        struct.pack_into(">H", data, 118, flags)
                        sid.write_bytes(data)
                        trace = Path(str(output) + ".registers.tsv")
                        if existing:
                            output.write_bytes(b"Existing audio")
                            trace.write_bytes(b"Existing trace")
                        result = subprocess.run([str(RENDERER), str(sid), str(output), "0.1", "--assume-sid-model", model],
                                                capture_output=True, text=True, timeout=20)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn("SID model assumption requires", result.stderr)
                        self.assertEqual(sid.read_bytes(), data)
                        if existing:
                            self.assertEqual(output.read_bytes(), b"Existing audio")
                            self.assertEqual(trace.read_bytes(), b"Existing trace")
                        else:
                            self.assertFalse(output.exists())
                            self.assertFalse(trace.exists())

    def test_clock_selection_controls_actual_pitch_and_vbi_cadence_and_preserves_default_pal(self):
        with tempfile.TemporaryDirectory() as directory:
            sid = Path(directory) / "ntsc-clock.sid"
            write_ntsc_clock_sid(sid)
            source = sid.read_bytes()
            rendered = {}
            for clock in (None, "pal", "ntsc"):
                output = Path(directory) / f"clock-{clock}.wav"
                options = [] if clock is None else ["--clock", clock]
                result = subprocess.run([str(RENDERER), str(sid), str(output), "1.2", *options],
                                        capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                selected = "pal" if clock is None else clock
                self.assertIn(f"clock {selected.upper()}", result.stdout)
                samples = read_samples(output)
                self.assertEqual(len(samples), round(1.2 * RATE))
                middle = samples[RATE // 4:RATE]
                cpu_clock, cycles = ((17734475 / 18, 312 * 63) if selected == "pal"
                                     else (14318181.82 / 14, 263 * 65))
                word = round(440 * 2**24 / (14318181.82 / 14))
                self.assertGreater(rms(middle), 100)
                self.assertAlmostEqual(frequency(middle), word * cpu_clock / 2**24, delta=3)
                trace = Path(str(output) + ".registers.tsv").read_bytes()
                rows = [(int(line.split("\t")[0]), bytes.fromhex(line.split("\t")[1])[2])
                        for line in trace.decode().splitlines()[1:]]
                start, end = rows[4], rows[-1]
                expected_updates = (end[0] - start[0]) * cpu_clock / (1000 * cycles)
                self.assertAlmostEqual(end[1] - start[1], expected_updates, delta=1.1)
                rendered[clock] = output.read_bytes(), trace
            self.assertEqual(rendered[None], rendered["pal"])
            self.assertNotEqual(rendered["pal"][0], rendered["ntsc"][0])
            self.assertEqual(sid.read_bytes(), source)

    def test_clock_options_reject_invalid_missing_and_duplicate_values_before_output(self):
        arguments = [["--clock", value] for value in ("", "auto", "PAL", " ntsc", "ntsc ", "old-ntsc")]
        arguments += [["--clock"], ["--clock", "pal", "--clock", "ntsc"]]
        with tempfile.TemporaryDirectory() as directory:
            sid = Path(directory) / "clock.sid"
            write_ntsc_clock_sid(sid)
            for options in arguments:
                for existing in (False, True):
                    with self.subTest(options=options, existing=existing):
                        output = Path(directory) / "invalid.wav"
                        trace = Path(str(output) + ".registers.tsv")
                        if existing:
                            output.write_bytes(b"Existing audio")
                            trace.write_bytes(b"Existing trace")
                        else:
                            output.unlink(missing_ok=True)
                            trace.unlink(missing_ok=True)
                        result = subprocess.run([str(RENDERER), str(sid), str(output), "0.1", *options],
                                                capture_output=True, text=True, timeout=20)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn("clock", result.stderr.lower())
                        if existing:
                            self.assertEqual(output.read_bytes(), b"Existing audio")
                            self.assertEqual(trace.read_bytes(), b"Existing trace")
                        else:
                            self.assertFalse(output.exists())
                            self.assertFalse(trace.exists())

    def test_two_sid_rejects_mismatched_clocks_without_creating_or_truncating_output(self):
        for declared, selected in (("pal", "ntsc"), ("ntsc", "pal"), ("ntsc", None)):
            for existing in (False, True):
                with self.subTest(declared=declared, selected=selected, existing=existing), tempfile.TemporaryDirectory() as directory:
                    sid, output = Path(directory) / "dual.sid", Path(directory) / "preserved.wav"
                    write_two_sid_fixture(sid, clock=declared)
                    trace = Path(str(output) + ".registers.tsv")
                    if existing:
                        output.write_bytes(b"Existing audio")
                        trace.write_bytes(b"Existing trace")
                    options = [] if selected is None else ["--clock", selected]
                    result = subprocess.run([str(RENDERER), str(sid), str(output), "0.1", *options],
                                            capture_output=True, text=True, timeout=20)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("clock must match", result.stderr)
                    if existing:
                        self.assertEqual(output.read_bytes(), b"Existing audio")
                        self.assertEqual(trace.read_bytes(), b"Existing trace")
                    else:
                        self.assertFalse(output.exists())
                        self.assertFalse(trace.exists())

    def test_two_sid_ntsc_has_correct_pcm_pitches_duration_and_vbi_cadence_for_both_models(self):
        cpu_clock, cycles = 14318181.82 / 14, 263 * 65
        rendered = []
        for model in ("8580", "6581"):
            with self.subTest(model=model), tempfile.TemporaryDirectory() as directory:
                sid, output = Path(directory) / "ntsc-dual.sid", Path(directory) / "ntsc-dual.wav"
                write_two_sid_fixture(sid, clock="ntsc", model=model, counter=True)
                original = sid.read_bytes()
                result = subprocess.run([str(RENDERER), str(sid), str(output), "1.2", "--clock", "ntsc"],
                                        capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("clock NTSC", result.stdout)
                frames, left, right = read_stereo_samples(output)
                self.assertEqual(frames, round(1.2 * RATE))
                for samples, expected in ((left, 440), (right, 660)):
                    middle = samples[RATE // 4:RATE]
                    self.assertGreater(rms(middle), 100)
                    self.assertAlmostEqual(frequency(middle), expected, delta=3)
                    self.assertFalse(any(value in (-32768, 32767) for value in samples))
                rows = [line.split("\t") for line in Path(str(output) + ".registers.tsv").read_text().splitlines()]
                self.assertEqual(rows[0], ["time_ms", "registers_hex", "registers_sid2_hex"])
                snapshots = [(int(row[0]), bytes.fromhex(row[1]), bytes.fromhex(row[2])) for row in rows[1:]]
                start, end = snapshots[4], snapshots[-1]
                expected_updates = (end[0] - start[0]) * cpu_clock / (1000 * cycles)
                for chip in (1, 2):
                    self.assertAlmostEqual(end[chip][2] - start[chip][2], expected_updates, delta=1.1)
                self.assertEqual(sid.read_bytes(), original)
                rendered.append((output.read_bytes(), Path(str(output) + ".registers.tsv").read_bytes()))
        self.assertNotEqual(rendered[0][0], rendered[1][0])
        self.assertEqual(rendered[0][1], rendered[1][1])

    def test_explicit_subtunes_select_init_accumulator_and_pitch_and_preserve_default_output(self):
        for default_song in (1, 2):
            with self.subTest(default_song=default_song), tempfile.TemporaryDirectory() as directory:
                sid = Path(directory) / "two-subtunes.sid"
                write_two_subtune_sid(sid, default_song)
                rendered = {}
                for subtune in (None, 1, 2):
                    output = Path(directory) / f"subtune-{subtune}.wav"
                    command = [str(RENDERER), str(sid), str(output), "0.5"]
                    if subtune is not None:
                        command += ["--subtune", str(subtune)]
                    result = subprocess.run(command, capture_output=True, text=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    selected = default_song if subtune is None else subtune
                    self.assertIn(f"subtune {selected} of 2", result.stdout)
                    samples = read_samples(output)
                    self.assertEqual(len(samples), RATE // 2)
                    middle = samples[RATE // 4:]
                    self.assertGreater(rms(middle), 100)
                    self.assertAlmostEqual(frequency(middle), {1: 440, 2: 660}[selected], delta=3)
                    rows = Path(str(output) + ".registers.tsv").read_text().splitlines()[1:]
                    self.assertTrue(rows)
                    self.assertTrue(all(bytes.fromhex(row.split("\t")[1])[5] == selected - 1 for row in rows))
                    rendered[subtune] = output.read_bytes()
                self.assertEqual(rendered[None], rendered[default_song])
                self.assertNotEqual(rendered[1], rendered[2])

    def test_subtune_and_voice_options_work_in_either_order(self):
        with tempfile.TemporaryDirectory() as directory:
            sid = Path(directory) / "two-subtunes.sid"
            write_two_subtune_sid(sid, 1)
            for voices in ("1", "none"):
                rendered = []
                for order in (0, 1):
                    output = Path(directory) / f"order-{voices}-{order}.wav"
                    options = (["--clock", "pal", "--subtune", "2", "--voices", voices] if order == 0
                               else ["--voices", voices, "--subtune", "2", "--clock", "pal"])
                    result = subprocess.run([str(RENDERER), str(sid), str(output), "0.5", *options],
                                            capture_output=True, text=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("subtune 2 of 2", result.stdout)
                    middle = read_samples(output)[RATE // 4:]
                    if voices == "none":
                        self.assertLess(rms(middle), 1)
                    else:
                        self.assertGreater(rms(middle), 100)
                        self.assertAlmostEqual(frequency(middle), 660, delta=3)
                    rendered.append(output.read_bytes())
                self.assertEqual(*rendered)

    def test_subtune_options_reject_invalid_duplicate_and_unknown_arguments_without_truncation(self):
        options = [["--subtune", value] for value in
                   ("0", "3", "-1", "+1", "1.0", "", " 1", "1 ", "1junk", "nan", "42949672960")]
        options += [["--subtune"], ["--voices"], ["--subtune", "1", "--subtune", "2"],
                    ["--voices", "1", "--voices", "2"], ["--song", "1"],
                    ["--subtune", "1", "--unknown", "2"]]
        with tempfile.TemporaryDirectory() as directory:
            sid, output = Path(directory) / "two-subtunes.sid", Path(directory) / "preserved.wav"
            write_two_subtune_sid(sid, 1)
            trace = Path(str(output) + ".registers.tsv")
            for arguments in options:
                with self.subTest(arguments=arguments):
                    output.write_bytes(b"Existing audio")
                    trace.write_bytes(b"Existing trace")
                    result = subprocess.run([str(RENDERER), str(sid), str(output), "0.1", *arguments],
                                            capture_output=True, text=True, timeout=20)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertTrue(result.stderr.strip())
                    self.assertEqual(output.read_bytes(), b"Existing audio")
                    self.assertEqual(trace.read_bytes(), b"Existing trace")

    def test_renderer_honors_6581_declarations_for_one_and_two_chips(self):
        for count, fixture, flags in ((1, write_a4_sid, 0x14), (2, write_two_sid_fixture, 0x54)):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as directory:
                sid = Path(directory) / "model.sid"
                fixture(sid)
                outputs = []
                for model in ("8580", "6581"):
                    if model == "6581":
                        data = bytearray(sid.read_bytes())
                        struct.pack_into(">H", data, 118, flags)
                        sid.write_bytes(data)
                    output = Path(directory) / f"{model}.wav"
                    result = subprocess.run([str(RENDERER), str(sid), str(output), "0.5"], capture_output=True, text=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn(f"SID model MOS{model} (declared)", result.stdout)
                    with wave.open(str(output), "rb") as source:
                        self.assertEqual(source.getnchannels(), count)
                        self.assertEqual(source.getnframes(), RATE // 2)
                    outputs.append(output)
                self.assertNotEqual(outputs[0].read_bytes(), outputs[1].read_bytes())
                self.assertEqual(Path(str(outputs[0]) + ".registers.tsv").read_bytes(), Path(str(outputs[1]) + ".registers.tsv").read_bytes())

    def render(self, sid, seconds, directory):
        output = Path(directory) / "render.wav"
        subprocess.run([str(RENDERER), str(sid), str(output), str(seconds)], check=True, timeout=20, capture_output=True, text=True)
        return output, read_samples(output)

    def test_diagnostic_voice_masks_select_actual_audio_keep_trace_and_leave_default_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            sid = Path(directory) / "independent.sid"
            write_three_voice_sid(sid)
            rendered = {}
            for voices in (None, "1,2,3", "1", "2", "3", "1,3", "none"):
                output = Path(directory) / f"voices-{voices if voices is not None else 'default'}.wav"
                command = [str(RENDERER), str(sid), str(output), "0.5"]
                if voices is not None:
                    command += ["--voices", voices]
                result = subprocess.run(command, capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                rendered[voices] = output
                self.assertEqual(len(read_samples(output)), RATE // 2)
            original = rendered[None].read_bytes()
            trace = Path(str(rendered[None]) + ".registers.tsv").read_bytes()
            self.assertEqual(rendered["1,2,3"].read_bytes(), original)
            for voices, output in rendered.items():
                self.assertEqual(Path(str(output) + ".registers.tsv").read_bytes(), trace)
                middle = read_samples(output)[RATE // 4:]
                if voices == "none":
                    self.assertLess(rms(middle), 1)
                else:
                    self.assertGreater(rms(middle), 100)
                    self.assertFalse(any(value in (-32768, 32767) for value in middle))
                    if voices in ("1", "2", "3"):
                        self.assertAlmostEqual(frequency(middle), {"1": 330, "2": 440, "3": 660}[voices], delta=3)

    def test_diagnostic_voice_masks_reject_bad_lists_and_two_sid_use_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            mono, dual = Path(directory) / "one.sid", Path(directory) / "two.sid"
            write_three_voice_sid(mono)
            write_two_sid_fixture(dual)
            for sid, voices in [(mono, value) for value in ("", "0", "4", "1,1", "1,", ",1", "1 2", "all", "none,1")] + [(dual, "1"), (dual, "1,2,3")]:
                with self.subTest(sid=sid, voices=voices):
                    output = Path(directory) / "invalid.wav"
                    result = subprocess.run([str(RENDERER), str(sid), str(output), "0.1", "--voices", voices], capture_output=True, text=True, timeout=20)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertTrue(result.stderr.strip())
                    self.assertFalse(output.exists())
                    self.assertFalse(Path(str(output) + ".registers.tsv").exists())

    def test_independent_a4_fixture_has_expected_duration_and_pitch(self):
        with tempfile.TemporaryDirectory() as directory:
            sid = Path(directory) / "a4.sid"
            write_a4_sid(sid)
            _, samples = self.render(sid, 1, directory)
            self.assertEqual(len(samples), RATE)
            middle = samples[RATE // 4:3 * RATE // 4]
            self.assertGreater(rms(middle), 100)
            self.assertAlmostEqual(frequency(middle), 440, delta=3)

    def test_renderer_selects_the_declared_default_subtune_before_initialization(self):
        for default_song in (1, 2):
            with self.subTest(default_song=default_song), tempfile.TemporaryDirectory() as directory:
                sid = Path(directory) / "selected-subtune.sid"
                write_a4_sid(sid)
                data = bytearray(sid.read_bytes())
                guard = bytes((0xc9, default_song - 1, 0xf0, 1, 0x60))
                data[0x7c:0x7c] = guard
                struct.pack_into(">H", data, 12, int.from_bytes(data[12:14], "big") + len(guard))
                struct.pack_into(">2H", data, 14, 2, default_song)
                sid.write_bytes(data)
                _, samples = self.render(sid, 0.5, directory)
                self.assertGreater(rms(samples[RATE // 4:]), 100)
                self.assertAlmostEqual(frequency(samples[RATE // 4:]), 440, delta=3)

    def test_two_sid_fixture_has_distinct_stereo_pitches_and_exact_duration(self):
        for default_song in (1, 2):
            with self.subTest(default_song=default_song), tempfile.TemporaryDirectory() as directory:
                sid, output = Path(directory) / "two.sid", Path(directory) / "stereo.wav"
                write_two_sid_fixture(sid, default_song)
                result = subprocess.run([str(RENDERER), str(sid), str(output), "1.00001"], capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                frames, left, right = read_stereo_samples(output)
                self.assertEqual(frames, round(1.00001 * RATE))
                for samples, expected in ((left, 440), (right, 660)):
                    middle = samples[RATE // 4:3 * RATE // 4]
                    self.assertGreater(rms(middle), 100)
                    self.assertAlmostEqual(frequency(middle), expected, delta=3)
                    self.assertFalse(any(value in (-32768, 32767) for value in samples))
                rows = [line.split("\t") for line in Path(str(output) + ".registers.tsv").read_text().splitlines()]
                self.assertEqual(rows[0], ["time_ms", "registers_hex", "registers_sid2_hex"])
                first, second = bytes.fromhex(rows[-1][1]), bytes.fromhex(rows[-1][2])
                self.assertEqual(len(first), 32)
                self.assertEqual(len(second), 32)
                self.assertNotEqual(first[0:2], second[0:2])
                explicit = Path(directory) / "explicit-pal.wav"
                result = subprocess.run([str(RENDERER), str(sid), str(explicit), "1.00001", "--clock", "pal"], capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(output.read_bytes(), explicit.read_bytes())
                self.assertEqual(Path(str(output) + ".registers.tsv").read_bytes(), Path(str(explicit) + ".registers.tsv").read_bytes())

    def test_two_sid_muted_variants_prove_each_chip_contributes_only_to_its_channel(self):
        for clock in ("pal", "ntsc"):
            for enabled_left, enabled_right in ((True, False), (False, True)):
                with self.subTest(clock=clock, left=enabled_left, right=enabled_right), tempfile.TemporaryDirectory() as directory:
                    sid, output = Path(directory) / "isolated.sid", Path(directory) / "isolated.wav"
                    write_two_sid_fixture(sid, left=enabled_left, right=enabled_right, clock=clock)
                    result = subprocess.run([str(RENDERER), str(sid), str(output), "0.5", "--clock", clock], capture_output=True, text=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    _, left, right = read_stereo_samples(output)
                    for samples, enabled, expected in ((left, enabled_left, 440), (right, enabled_right, 660)):
                        middle = samples[RATE // 4:]
                        if enabled:
                            self.assertGreater(rms(middle), 100)
                            self.assertAlmostEqual(frequency(middle), expected, delta=3)
                        else:
                            self.assertLess(rms(middle), 1)

    def test_two_sid_rejects_unsupported_chip_addresses_models_versions_and_timing_before_output(self):
        mutations = (
            ("third chip", lambda data: data.__setitem__(0x7b, 0x44)),
            ("second address", lambda data: data.__setitem__(0x7a, 0x44)),
            ("invalid address", lambda data: data.__setitem__(0x7a, 0x41)),
            ("duplicate address", lambda data: data.__setitem__(0x7a, 0x40)),
            ("PSID version", lambda data: struct.pack_into(">H", data, 4, 4)),
            ("v2 extra SID", lambda data: struct.pack_into(">H", data, 4, 2)),
            ("both clocks", lambda data: struct.pack_into(">H", data, 0x76, 0xac)),
            ("unknown clock", lambda data: struct.pack_into(">H", data, 0x76, 0xa0)),
            ("CIA timing", lambda data: data.__setitem__(21, 1)),
            ("later-subtune CIA timing", lambda data: data.__setitem__(21, 2)),
            ("MUS", lambda data: struct.pack_into(">H", data, 0x76, 0xa5)),
            ("PlaySID", lambda data: struct.pack_into(">H", data, 0x76, 0xa6)),
            ("mixed models, second 6581", lambda data: struct.pack_into(">H", data, 0x76, 0x64)),
            ("mixed models, first 6581", lambda data: struct.pack_into(">H", data, 0x76, 0x94)),
        )
        for name, mutate in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                sid, output = Path(directory) / "unsupported.sid", Path(directory) / "unsupported.wav"
                write_two_sid_fixture(sid)
                data = bytearray(sid.read_bytes())
                mutate(data)
                sid.write_bytes(data)
                result = subprocess.run([str(RENDERER), str(sid), str(output), "0.1"], capture_output=True, text=True, timeout=20)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(result.stderr.strip())
                self.assertFalse(output.exists())
                self.assertFalse(Path(str(output) + ".registers.tsv").exists())

    def test_render_longer_than_one_minute_keeps_exact_length_and_final_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            sid = Path(directory) / "a4.sid"
            output = Path(directory) / "long.wav"
            write_a4_sid(sid)
            subprocess.run([str(RENDERER), str(sid), str(output), "60.01"], check=True, timeout=20, capture_output=True, text=True)
            with wave.open(str(output), "rb") as wav:
                self.assertEqual(wav.getnframes(), round(60.01 * RATE))
                wav.setpos(59 * RATE)
                tail = wav.readframes(RATE)
            samples = struct.unpack("<" + "h" * (len(tail) // 2), tail)
            self.assertGreater(rms(samples), 100)
            self.assertAlmostEqual(frequency(samples), 440, delta=3)

    def test_render_rejects_duration_above_ten_minutes_without_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            sid = Path(directory) / "a4.sid"
            output = Path(directory) / "oversized.wav"
            write_a4_sid(sid)
            result = subprocess.run([str(RENDERER), str(sid), str(output), "600.01"], timeout=20, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("at most 600", result.stderr)
            self.assertFalse(output.exists())

    def test_fuer_elise_has_nine_pitches_and_a_silent_ending(self):
        with tempfile.TemporaryDirectory() as directory:
            output, samples = self.render(ROOT / "build/fuer-elise-opening.sid", 3.2, directory)
            self.assertEqual(len(samples), round(3.2 * RATE))
            self.assertGreater(rms(samples[RATE // 10:2 * RATE]), 100)
            self.assertLess(rms(samples[3 * RATE:]), 2)
            rows = [(int(line.split("\t")[0]) / 1000, bytes.fromhex(line.split("\t")[1])) for line in Path(str(output) + ".registers.tsv").read_text().splitlines()[1:]]
            notes = []
            previous_gate = False
            for timestamp, state in rows:
                gate = bool(state[4] & 1)
                if gate and not previous_gate:
                    notes.append([timestamp, None, state[0] | (state[1] << 8)])
                if not gate and previous_gate:
                    notes[-1][1] = timestamp
                previous_gate = gate
            clock = 985248.6111111111
            expected_hz = [659.255, 622.254, 659.255, 622.254, 659.255, 493.883, 587.330, 523.251, 440]
            expected_ticks = [0, 10, 21, 31, 42, 52, 63, 73, 84]
            self.assertEqual(len(notes), len(expected_hz))
            for (onset, offset, word), expected, tick in zip(notes, expected_hz, expected_ticks):
                self.assertAlmostEqual(word * clock / 2**24, expected, delta=0.1)
                self.assertAlmostEqual(onset - notes[0][0], tick * 19656 / clock, delta=0.021)
                active = samples[round((onset + 0.04) * RATE):round((offset - 0.025) * RATE)]
                self.assertGreater(rms(active), 100)
                self.assertAlmostEqual(frequency(active), expected, delta=3)
            self.assertEqual(rows[-1][1][0x18] & 15, 0)


if __name__ == "__main__":
    unittest.main()
