"""Build an independent editable 6502 bass instrument and compare its execution."""

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import wave

from audio_comparison import inspect_wav, prepare_comparison, read_pcm16
from psid_audit import audit_psid
from verify_player import require


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "songs/studies/drax-bass-reconstruction"
SOURCE_SHA256 = "ea6b7eba46844d399e415368eae86c3ddf03bd9041ecba93e7bb53b384daa2a1"
LOAD = 0x1000
REGISTERS = {*range(0xd400, 0xd407), *range(0xd415, 0xd419)}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as output:
        json.dump(value, output, indent=2, allow_nan=False)
        output.write("\n")


def read_recipe(path):
    path = Path(path).resolve()
    recipe = json.loads(path.read_text())
    if "base" in recipe:
        base = path.parent / recipe.pop("base")
        require(base.resolve() != path, "Recipe cannot inherit itself")
        inherited = json.loads(base.read_text())
        require("base" not in inherited, "Use one explicit base instrument, without an inheritance chain")
        inherited.update(recipe)
        recipe = inherited
    require(recipe["schemaVersion"] == 1 and recipe["chip"] == "MOS6581" and recipe["clock"] == "PAL", "This study requires the pinned single PAL 6581 profile")
    require(recipe["sourceSha256"] == SOURCE_SHA256, "Recipe provenance differs from the decoded reference")
    require(type(recipe["playCalls"]) is int and 1 <= recipe["playCalls"] <= 255, "Select 1..255 play calls")
    require(0 < recipe["renderSeconds"] <= 5, "Select a bounded render of at most five seconds")
    notes = recipe["notes"]
    require(notes and len(notes) < 32, "Select a nonempty bounded note sequence")
    previous = None
    for note in notes:
        require(type(note["initCall"]) is int and 2 <= note["initCall"] < recipe["playCalls"] - 3, "Each note needs two setup frames and an observed release")
        require(previous is None or note["initCall"] >= previous + 6, "Notes must leave the previous attack/release sequence intact")
        require(type(note["frequency"]) is int and 1 <= note["frequency"] <= 65535, "Frequency must be a nonzero SID word")
        previous = note["initCall"]
    return recipe


def constants(recipe):
    instrument, pre = recipe["instrument"], recipe["silentPrehistory"]
    result = {
        "PLAY_CALLS": recipe["playCalls"], "NOTE_COUNT": len(recipe["notes"]),
        "AD": instrument["attackDecay"], "SR": instrument["sustainRelease"],
        "RESTART_AD": instrument["hardRestartAttackDecay"], "RESTART_SR": instrument["hardRestartSustainRelease"],
        "NOISE_CONTROL": instrument["noiseControl"], "PULSE_CONTROL": instrument["pulseControl"], "RELEASE_CONTROL": instrument["releaseControl"],
        "PULSE_STEP": instrument["pulseStep"], "PULSE_LOWER": instrument["pulseLowerHighByte"], "PULSE_UPPER": instrument["pulseUpperHighByte"],
        "ATTACK_CUTOFF": instrument["attackCutoffHigh"], "BODY_CUTOFF": instrument["bodyCutoffHigh"],
        "ROUTING": instrument["filterRoutingResonance"], "MODE_VOLUME": instrument["filterModeVolume"],
        "PRE_DIRECTION": pre["initialDirection"], "PRE_STEP": pre["pulseStep"], "PRE_LOWER": pre["pulseLowerHighByte"], "PRE_UPPER": pre["pulseUpperHighByte"],
    }
    for label, value in (("PULSE", instrument["pulseInitial"]), ("NOISE", instrument["noiseFrequency"]), ("PRE_PULSE", pre["initialPulse"]), ("PRE_FIRST", pre["firstFrequency"]), ("PRE_SECOND", pre["secondFrequency"]), ("PRE_BODY", pre["bodyFrequency"])):
        require(type(value) is int and 0 <= value <= 65535, f"{label} must fit a word")
        result[f"{label}_LO"], result[f"{label}_HI"] = value & 255, value >> 8
    require(all(type(value) is int and 0 <= value <= 255 for value in result.values()), "Instrument fields must fit bytes")
    require(0 <= instrument["pulseInitial"] < 4096 and 0 < instrument["pulseStep"] < 256, "Pulse width/step lies outside the instrument contract")
    require(0 <= instrument["pulseLowerHighByte"] < instrument["pulseUpperHighByte"] <= 15, "Main PWM needs distinct ascending high-byte bounds")
    require(instrument["pulseLowerHighByte"] <= instrument["pulseInitial"] >> 8 < instrument["pulseUpperHighByte"], "Initial ascending PWM must start between its reversal bounds")
    require(0 <= pre["initialPulse"] < 4096 and 0 <= pre["pulseLowerHighByte"] <= pre["pulseUpperHighByte"] <= 15 and pre["initialDirection"] in (0, 1), "Silent PWM must remain a valid 12-bit bounded state")
    pre_next = pre["initialPulse"] + (pre["pulseStep"] if pre["initialDirection"] == 0 else -pre["pulseStep"])
    require(pre["pulseLowerHighByte"] <= pre["initialPulse"] >> 8 <= pre["pulseUpperHighByte"] and 0 <= pre_next < 4096 and pre["pulseLowerHighByte"] <= pre_next >> 8 <= pre["pulseUpperHighByte"], "Initial silent PWM direction must reach a reversal bound before leaving its range")
    require(instrument["releaseControl"] & 1 == 0, "The instrument must close GATE during its body")
    return result


def assemble(recipe, source):
    from py65.assembler import Assembler
    from py65.devices.mpu6502 import MPU
    from py65.utils.addressing import AddressParser

    statements = [line.split(";", 1)[0].strip() for line in source.splitlines()]
    statements = [line for line in statements if line]
    for name, values in (("note_calls", [note["initCall"] for note in recipe["notes"]]), ("note_frequency_lo", [note["frequency"] & 255 for note in recipe["notes"]]), ("note_frequency_hi", [note["frequency"] >> 8 for note in recipe["notes"]])):
        statements += [name + ":", ".byte " + ",".join(f"${value:02x}" for value in values)]
    symbols = constants(recipe)
    for line in statements:
        if line.endswith(":"):
            name = line[:-1]
            require(name not in symbols, f"Duplicate label {name}")
            symbols[name] = LOAD
    assembler = Assembler(MPU(), AddressParser(labels=symbols))
    pc = LOAD
    for line in statements:
        if line.endswith(":"):
            symbols[line[:-1]] = pc
        elif line.startswith(".byte "):
            pc += len(line[6:].split(","))
        else:
            pc += len(assembler.assemble(line, pc=pc))
    require(pc < 0xa000, "Payload must remain in callable RAM")
    parser = AddressParser(labels=symbols)
    assembler = Assembler(MPU(), parser)
    pc, payload, listing = LOAD, bytearray(), []
    for line in statements:
        if line.endswith(":"):
            continue
        if line.startswith(".byte "):
            encoded = [parser.number(token) for token in line[6:].split(",")]
        else:
            encoded = assembler.assemble(line, pc=pc)
            if line[:3] in {"BCC", "BCS", "BEQ", "BMI", "BNE", "BPL", "BVC", "BVS"}:
                require(-128 <= parser.number(line.split()[1]) - pc - 2 <= 127, f"Branch out of range: {line}")
        require(all(0 <= byte <= 255 for byte in encoded), "Data directive must contain bytes")
        listing.append(f"{pc:04x}  {bytes(encoded).hex():<12} {line}")
        payload.extend(encoded)
        pc += len(encoded)
    return bytes(payload), symbols, "\n".join(listing) + "\n"


def build_psid(recipe, source):
    payload, symbols, listing = assemble(recipe, source)
    header = bytearray(124)
    header[:4] = b"PSID"
    for offset, value in ((4, 2), (6, 124), (8, LOAD), (10, symbols["entry_init"]), (12, symbols["entry_play"]), (14, 1), (16, 1), (118, 0x14)):
        struct.pack_into(">H", header, offset, value)
    for offset, text in ((22, recipe["title"]), (54, "Independent mechanism study"), (86, "2026; DRAX-derived parameters")):
        header[offset:offset + 31] = text.encode("ascii")[:31].ljust(31, b"\x00")
    return bytes(header) + payload, {"symbols": symbols, "payloadBytes": len(payload), "listing": listing}


def projected_writes(writes):
    groups = defaultdict(list)
    for row in writes:
        if row["address"] in REGISTERS:
            groups[(row["phase"], row["tick"])].append(row)
    result = []
    for rows in groups.values():
        last_cutoff = max((index for index, row in enumerate(rows) if row["address"] == 0xd416), default=-1)
        result += [row for index, row in enumerate(rows) if row["address"] != 0xd416 or index == last_cutoff]
    return result


def compare_registers(reference, candidate, ticks):
    left, right = projected_writes(reference), projected_writes(candidate)
    identity = lambda row: (row["phase"], row["tick"], row["address"], row["value"])
    require([identity(row) for row in left] == [identity(row) for row in right], "Independent bass writes differ in value, order or call from the reference projection")
    state = lambda rows: frame_projection(rows, ticks)
    require(state(reference) == state(candidate), "Frame-level bass/global states differ")
    deltas = [b["instructionStartCycle"] - a["instructionStartCycle"] for a, b in zip(left, right)]
    return {
        "playCalls": ticks,
        "orderedProjectedWrites": len(left),
        "orderedAddressValueCallEquality": True,
        "bassAndGlobalFrameStateEquality": True,
        "registerAddresses": sorted(REGISTERS),
        "projection": "Voice-one registers plus global filter/volume; retain the last cutoff-high store per call, because the original shared writer repeats its prior cutoff for companion voices before bass updates it.",
        "instructionStartCycleDeltas": {"minimum": min(deltas), "maximum": max(deltas)},
        "exactWithinFrameTiming": False,
        "companionVoiceEquality": False,
    }


def frame_projection(writes, ticks):
    state, frames = dict.fromkeys(sorted(REGISTERS), 0), []
    groups = defaultdict(list)
    for row in writes:
        if row["address"] in REGISTERS:
            if row["phase"] == "init":
                state[row["address"]] = row["value"]
            else:
                groups[row["tick"]].append(row)
    for tick in range(ticks):
        for row in groups[tick]:
            state[row["address"]] = row["value"]
        frames.append(list(state.values()))
    return frames


def excerpt(source, target, start, seconds):
    audio = read_pcm16(source)
    first, count = round(start * audio.sample_rate), round(seconds * audio.sample_rate)
    require(first >= 0 and count > 0 and first + count <= audio.frames, "Excerpt must fit the complete render")
    samples = audio.samples[first:first + count]
    if sys.byteorder != "little":
        samples.byteswap()
    with target.open("xb") as stream:
        with wave.open(stream, "wb") as output:
            output.setparams((1, 2, audio.sample_rate, 0, "NONE", "not compressed"))
            output.writeframes(samples.tobytes())
    return {"sourceStartFrame": first, "frames": count, **inspect_wav(target)}


def run_process(command, receipt_path):
    result = subprocess.run(command, text=True, capture_output=True, timeout=120, check=False)
    receipt = {"command": command, "returnCode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip(), "deadlineSeconds": 120}
    write_json(receipt_path, receipt)
    require(result.returncode == 0, f"Command failed; see {receipt_path}")
    return receipt


def pcm_comparison(reference, candidate):
    left, right = read_pcm16(reference), read_pcm16(candidate)
    require((left.sample_rate, left.channels, left.frames) == (right.sample_rate, right.channels, right.frames), "PCM check requires the same timestamp, duration and format")
    centers = [sum(audio.samples) / len(audio.samples) for audio in (left, right)]
    left_ac = [sample - centers[0] for sample in left.samples]
    right_ac = [sample - centers[1] for sample in right.samples]
    powers = [sum(sample * sample for sample in samples) for samples in (left_ac, right_ac)]
    require(all(power > 0 for power in powers), "PCM check requires nonzero AC energy")
    return {
        "samePcm": left.samples == right.samples,
        "sameTimestampAcCorrelation": sum(a * b for a, b in zip(left_ac, right_ac)) / math.sqrt(powers[0] * powers[1]),
        "unmatchedAcDifferenceRms": math.sqrt(sum((a - b) ** 2 for a, b in zip(left_ac, right_ac)) / len(left_ac)),
        "reconstructionAcRmsDeltaDb": 10 * math.log10(powers[1] / powers[0]),
        "alignment": "Same source-time cut; no offset search, resampling, time stretch or phase correction",
        "interpretation": "PCM is secondary diagnostic evidence. Correlation and AC RMS are not timbre equivalence or a listening verdict.",
    }


def run_study(recipe_path, output, reference=None, *, renderer=ROOT / ".local/bin/render-sid", vice=False):
    recipe_path, output = Path(recipe_path).resolve(), Path(output).resolve()
    require(not output.exists() and not output.is_symlink(), "Choose a fresh output directory")
    recipe = read_recipe(recipe_path)
    source = (STUDY / "player.asm").read_text()
    sid, built = build_psid(recipe, source)
    audit, writes = audit_psid(sid, recipe["playCalls"])
    original = Path(reference).read_bytes() if reference else None
    if original is not None:
        require(digest(original) == SOURCE_SHA256, "Original reference SHA-256 differs")
        _, original_writes = audit_psid(original, recipe["playCalls"])
        guard = compare_registers(original_writes, writes, recipe["playCalls"])
    else:
        guard = None
    output.mkdir(parents=True)
    sid_path = output / "reconstructed.sid"
    sid_path.write_bytes(sid)
    (output / "reconstructed.prg").write_bytes(LOAD.to_bytes(2, "little") + sid[124:])
    (output / "player.listing").write_text(built.pop("listing"))
    write_json(output / "recipe.json", recipe)
    write_json(output / "build.json", {**built, "sidSha256": digest(sid), "assemblySha256": digest(source.encode()), "recipePath": str(recipe_path)})
    write_json(output / "audit.json", audit)
    write_json(output / "audit.writes.json", writes)
    write_json(output / "registers.json", {"addresses": sorted(REGISTERS), "frames": frame_projection(writes, recipe["playCalls"])})
    if guard:
        write_json(output / "register-comparison.json", guard)
    print(f"Built {built['payloadBytes']} independent 6502 bytes; audited {recipe['playCalls']} calls", flush=True)
    renderer = Path(renderer).resolve()
    renderer_sha = digest(renderer.read_bytes())
    wav_path = output / "reconstructed.full.wav"
    run_process([str(renderer), str(sid_path), str(wav_path), str(recipe["renderSeconds"]), "--voices", "1"], output / "render.json")
    pcm = inspect_wav(wav_path)
    require(pcm["clippedSamples"] == 0 and pcm["acRms"] > 1 and pcm["frames"] == round(44100 * recipe["renderSeconds"]), "Render is silent, clipped or incomplete")
    selected = recipe["excerpt"]
    cut = excerpt(wav_path, output / "reconstructed.exact.wav", selected["startSeconds"], selected["seconds"])
    comparison, pcm_check = None, None
    if reference:
        reference_wav = output / "reference.bass.full.wav"
        run_process([str(renderer), str(Path(reference).resolve()), str(reference_wav), str(recipe["renderSeconds"]), "--voices", "1"], output / "reference-render.json")
        excerpt(reference_wav, output / "reference.bass.exact.wav", selected["startSeconds"], selected["seconds"])
        comparison = prepare_comparison(output / "reference.bass.exact.wav", output / "reconstructed.exact.wav", output / "bass", individual_copies=True)
        pcm_check = pcm_comparison(output / "reference.bass.exact.wav", output / "reconstructed.exact.wav")
        write_json(output / "pcm-comparison.json", pcm_check)
        require(Path(reference).read_bytes() == original, "Archived reference changed")
    vice_report = None
    if vice:
        run_process([sys.executable, str(ROOT / "scripts/trace-sid-vice.py"), str(sid_path), "--oracle", str(output / "audit.writes.json"), "--first-call", "0", "--last-call", str(recipe["playCalls"] - 1), "--output", str(output / "vice")], output / "vice-command.json")
        vice_report = json.loads((output / "vice/study.json").read_text())
    require(digest(renderer.read_bytes()) == renderer_sha, "Renderer changed during comparison")
    report = {
        "schemaVersion": 1,
        "evidenceLevel": "Independent editable 6502 reconstruction from executed instrument mechanisms",
        "referenceSha256": SOURCE_SHA256,
        "referenceDriverIncluded": False,
        "registerDumpPlayback": False,
        "ending": "At playCalls the player writes master volume zero; the instrument closes GATE three calls after each init, before this explicit excerpt ending.",
        "sid": str(sid_path),
        "sidSha256": digest(sid),
        "rendererSha256": renderer_sha,
        "registerComparison": guard,
        "audit": audit,
        "audio": {"full": pcm, "excerpt": cut, "comparison": comparison, "pcmCheck": pcm_check},
        "vice": vice_report,
        "listeningReview": None,
        "limitations": "When present, the reference comparison covers bass/global register values and ordered bass writes by play call, after dropping companion cutoff stores. Those omitted stores repeat the prior cutoff before the bass transition and their timing is not reproduced. The independent scheduler executes stores at different cycles; companion oscillators, exact noise/oscillator phase and analog initial state are not reconstructed. The diagnostic reference uses control masking of voices two/three; this is not an additive stem. Same-renderer, same-time cuts and AC RMS matching provide a listening comparison when requested, not sample equality, hardware fidelity or musical acceptance.",
    }
    write_json(output / "study.json", report)
    print(f"Retained reconstruction and listening comparison: {output / 'study.json'}", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--renderer", type=Path, default=ROOT / ".local/bin/render-sid")
    parser.add_argument("--vice", action="store_true")
    args = parser.parse_args()
    run_study(args.recipe, args.output, args.reference, renderer=args.renderer, vice=args.vice)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, SyntaxError, subprocess.TimeoutExpired) as error:
        raise SystemExit(f"Bass reconstruction failed: {error}")
