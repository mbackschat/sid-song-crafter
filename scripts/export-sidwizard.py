"""Run SID-Maker's native conversion routines without its interactive dialogs."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
TOOL_ROOT = ROOT / ".tools/sid-wizard-exporter"
MAX_ROUTINE_STEPS = 2_000_000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def validate_pattern(pattern, rows, instrument_count):
    index = total_rows = 0
    while index < len(pattern):
        value = pattern[index]
        index += 1
        if 0x70 <= value <= 0x77:
            total_rows += value - 0x6e
            continue
        require(value & 0x7f != 0x7f, "Invalid native pattern structure")
        total_rows += 1
        if value & 0x80:
            require(index < len(pattern), "Invalid native pattern structure")
            instrument = pattern[index]
            index += 1
            selected = instrument & 0x7f
            require(not 1 <= selected <= 0x3e or selected <= instrument_count, "Invalid native instrument reference")
            if instrument & 0x80:
                require(index < len(pattern), "Invalid native effect structure")
                effect = pattern[index]
                index += 1 + (effect < 0x20)
                require(index <= len(pattern), "Invalid native effect structure")
    require(total_rows == rows, "Native pattern structure disagrees with its saved row length")


def validate_sequence(sequence, pattern_count):
    for index, value in enumerate(sequence):
        if value < 0x80:
            require(1 <= value <= pattern_count, "Invalid native pattern reference")
        elif value == 0xfe:
            require(index == len(sequence) - 1, "Invalid native sequence ending structure")
            return
        elif value == 0xff:
            require(index == len(sequence) - 2, "Invalid native sequence jump structure")
            target = sequence[index + 1]
            require((target < 0x80 and target < len(sequence)) or target == 0x80, "Invalid native sequence jump reference")
            return
    raise ValueError("Invalid native sequence structure: missing ending")


def native_pattern_start(data, cursor, unpacked_size):
    """Follow SID-Maker depkptseq's decoded-size footer and packed-NOP discriminator."""
    index = cursor - 2
    remaining = unpacked_size - 1
    while remaining:
        index -= 1
        require(index >= 66, "Invalid native pattern structure")
        value = data[index]
        previous = data[index - 1]
        packed = 0x70 <= value <= 0x77 and (previous == 0 or 0x70 <= previous <= 0x77)
        remaining -= value - 0x6e if packed else 1
        require(remaining >= 0, "Native pattern structure disagrees with its unpacked byte size")
    return index


def inspect_module(data):
    require(len(data) >= 68 and data[2:6] in (b"SWM1", b"SWMS"), "Expected a native SWM1 or SWMS module with its two-byte load address")
    header = data[2:66]
    sid_count = 1 if header[:4] == b"SWM1" else 2
    pattern_limit, instrument_limit = (100, 36) if sid_count == 1 else (105, 29)
    require(header[4] == 1, "Batch trial supports 1x frame speed only")
    require(header[19] == 3, "Batch trial requires the Extra player (native driver type 3)")
    require(header[20] == 0, "Batch trial supports standard PAL tuning only")
    require(header[12] == sid_count * 3, f"Batch trial supports one subtune with {sid_count * 3} voice sequences")
    require(1 <= header[13] <= pattern_limit and 1 <= header[14] <= instrument_limit, "Unsupported native pattern or instrument count")
    require(sid_count == 1 or header[22] == 0, "Batch 2SID export requires the native SID2 address ID 0 ($D420)")
    cursor = len(data) - 2 - header[16] - header[15]
    instruments = []
    for _ in range(header[14]):
        require(cursor >= 75, "Invalid native instrument structure")
        size = data[cursor - 9] + 1
        start = cursor - size - 8
        require(19 <= size <= 120 and start >= 66, "Invalid native instrument structure")
        instrument = data[start:cursor - 8]
        require(16 <= instrument[10] < instrument[11] < size, "Invalid native instrument table structure")
        instruments.append({"name": data[cursor - 8:cursor].decode("latin-1").rstrip(" \x00"), "size": size})
        cursor = start
    for _ in range(header[13]):
        require(cursor >= 69, "Invalid native pattern structure")
        size, rows = data[cursor - 2:cursor]
        require(2 <= size <= 249 and 1 <= rows <= 248, "Invalid native pattern structure")
        start = native_pattern_start(data, cursor, size)
        validate_pattern(data[start:cursor - 2], rows, header[14])
        cursor = start
    for _ in range(header[12]):
        require(cursor > 66, "Invalid native sequence structure")
        size = data[cursor - 1]
        require(1 <= size <= 128 and cursor - size - 1 >= 66, "Invalid native sequence structure")
        validate_sequence(data[cursor - size - 1:cursor - 1], header[13])
        cursor -= size + 1
    require(cursor == 66, "Invalid native module structure or trailing data")
    return {"sidCount": sid_count, "patterns": header[13], "sequences": header[12], "instruments": list(reversed(instruments)), "chordBytes": header[15], "tempoBytes": header[16]}


def cpu_type():
    try:
        from py65.devices.mpu6502 import MPU
    except ModuleNotFoundError:
        dependencies = ROOT / ".tools/test-deps"
        require((dependencies / "py65").is_dir(), "Install py65 1.2.0 using the documented repository setup")
        sys.path.insert(0, str(dependencies))
        from py65.devices.mpu6502 import MPU
    return MPU


def call(cpu, labels, name, stop=None):
    cpu.sp = 0xff
    cpu.stPushWord(0x0200 - 1)
    cpu.pc = labels[name]
    endpoint = labels[stop] if stop else 0x0200
    initial_cycles = cpu.processorCycles
    for _ in range(MAX_ROUTINE_STEPS):
        opcode = cpu.memory[cpu.pc]
        require(opcode != 0 and cpu.disassemble[opcode][0] != "???", f"SID-Maker routine {name} reached an unsupported opcode at ${cpu.pc:04x}")
        cpu.step()
        if cpu.pc == endpoint:
            require(stop is not None or cpu.sp == 0xff, f"SID-Maker routine {name} returned with an unbalanced stack")
            return cpu.processorCycles - initial_cycles
    raise ValueError(f"SID-Maker routine {name} exceeded the bounded execution limit at ${cpu.pc:04x}")


def write_text_field(memory, address, text):
    encoded = text.encode("ascii")
    require(len(encoded) <= 31 and b"\x00" not in encoded, "Batch PSID metadata must fit 31 ASCII characters")
    memory[address:address + 32] = encoded.ljust(32, b"\x00")


def export_module(source, output_dir, title=None, author=None, released="2026"):
    data = Path(source).read_bytes()
    summary = inspect_module(data)
    sid_count = summary["sidCount"]
    tool_root = TOOL_ROOT if sid_count == 1 else ROOT / ".tools/sid-wizard-exporter-2sid"
    build_path = tool_root / "build.json"
    require(build_path.is_file(), f"Run python3 scripts/setup-sidwizard.py --sid-count {sid_count} before batch export")
    build = json.loads(build_path.read_text())
    require(build.get("sidCount", 1) == sid_count, "Prepared SID-Maker build has the wrong SID count; rerun setup")
    prg = (tool_root / "exporter.prg").read_bytes()
    label_data = (tool_root / "exporter.labels").read_bytes()
    require(sha256(prg) == build["exporterSha256"] and sha256(label_data) == build["labelsSha256"], "Prepared SID-Maker binary or labels have changed; rerun setup")
    labels = {name: int(value, 16) for value, name in re.findall(r"^al ([\da-fA-F]+) \.(.+)$", label_data.decode(), re.MULTILINE)}
    memory = [0] * 65536
    start = int.from_bytes(prg[:2], "little")
    memory[start:start + len(prg) - 2] = prg[2:]
    music = labels["MUSICDATA"]
    module_end = music + len(data) - 2
    require(module_end < labels["MUSICDATA_END"], "Native module exceeds SID-Maker's available data memory")
    memory[music:module_end] = data[2:]
    memory[labels["compzptr"]:labels["compzptr"] + 2] = module_end.to_bytes(2, "little")
    memory[labels["PALNTSC"]] = 1
    memory[labels["TuningType"]] = 0
    cpu = cpu_type()(memory=memory)
    routine_cycles = {}
    for name in ("setEXEdetails", "preparetunedata"):
        routine_cycles[name] = call(cpu, labels, name)
    if sid_count == 2:
        # Upstream's setexport2 UI normally resolves the saved ID before setplayer patches every SID2 operand.
        name = "SID23set:CalcSID2addID"
        routine_cycles[name] = call(cpu, labels, name)
        require(bytes(memory[labels["SID2add"]:labels["SID2add"] + 2]) == b"\x20\xd4", "SID-Maker did not resolve the native SID2 address to $D420")
    for name in ("setplayer", "SetSIDply", "SetSIDt"):
        routine_cycles[name] = call(cpu, labels, name)
    cpu.x = 1
    routine_cycles["dispMod"] = call(cpu, labels, "dispMod")
    if title is not None:
        write_text_field(memory, labels["SIDtitletx"], title)
    if author is not None:
        write_text_field(memory, labels["SIDauthrtx"], author)
    write_text_field(memory, labels["SIDreleatx"], released)
    end = int.from_bytes(bytes(memory[labels["expoendadd"]:labels["expoendadd"] + 2]), "little")
    require(0x1000 < end < labels["MUSICDATA_END"], "SID-Maker returned an invalid export boundary")
    sid_header = labels["SIDHEADER"]
    sid = bytes(memory[sid_header:sid_header + labels["SIDHEADERSIZE"]]) + b"\x00\x10" + bytes(memory[0x1000:end])
    memory[labels["outputformat"]] = 2
    routine_cycles["setsaveparam"] = call(cpu, labels, "setsaveparam", stop="SaveExp")
    starter = labels["EXEstarter"]
    standalone = b"\x01\x08" + bytes(memory[starter:end])
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    stem = Path(source).stem
    sid_path, prg_path = output / f"{stem}.sid", output / f"{stem}.prg"
    report = {
        "source": str(Path(source)), "sourceSha256": sha256(data), "module": summary,
        "sid": str(sid_path), "sidSha256": sha256(sid), "prg": str(prg_path), "prgSha256": sha256(standalone),
        "sidWizardVersion": "1.97", "player": "Extra", "driverType": 3, "clock": "PAL", "sidModel": "MOS8580",
        "sidCount": sid_count, "sids": [{"baseAddress": 0xd400 + index * 0x20, "model": "MOS8580"} for index in range(sid_count)], "psidVersion": 2 if sid_count == 1 else 3,
        "frameSpeed": 1, "loadAddress": 0x1000, "initAddress": 0x1000, "playAddress": 0x1003,
        "standaloneLoadAddress": 0x0801, "standaloneStartAddress": labels["start2"],
        "standalonePlayerInitAddress": 0x1000, "standalonePlayerPlayAddress": 0x1003,
        "exportEndAddress": end, "nativeSourceRetained": True, "exportLosses": ["Instrument names are omitted from playback payload by upstream SID-Maker; retained in SWM/SWI."],
        "nativeRoutineCycles": routine_cycles, "build": build,
    }
    if sid_count == 2:
        selector_return = labels["SID2keyExe:endplmi"]
        require(standalone[selector_return - 0x0801 + 2] == 0x60, "Native address-selector return is not the expected RTS")
        report["standaloneAddressSelector"] = {"entryAddress": labels["SetSID2address"], "returnAddress": selector_return, "baseAddress": 0xd420, "method": "At selector entry, VICE monitor sets PC to the existing RTS; native address application continues."}
    report_path = output / f"{stem}.export.json"
    payloads = [(sid_path, sid), (prg_path, standalone), (report_path, (json.dumps(report, indent=2) + "\n").encode())]
    for path, payload in payloads:
        require(path.resolve() != Path(source).resolve() and not path.is_symlink(), "Output path would overwrite the native source or follow a symlink")
        require(not path.exists() or path.read_bytes() == payload, "Output already exists with different evidence; choose a fresh output directory")
    for path, payload in payloads:
        path.write_bytes(payload)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--title")
    parser.add_argument("--author")
    parser.add_argument("--released", default="2026")
    args = parser.parse_args()
    print(json.dumps(export_module(args.source, args.output_dir, args.title, args.author, args.released), indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
