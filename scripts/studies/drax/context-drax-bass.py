"""Compare the original mix with an independent bass on one emulated PAL 6581."""

import argparse
from array import array
import importlib.util
import math
from pathlib import Path
import struct
import sys
import wave

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from audio_comparison import inspect_wav, read_pcm16
from psid_audit import audit_psid
from verify_player import require


BASS_LOAD = 0x8000
WRAPPER_INIT = 0x9000
WRAPPER_PLAY = 0x9020
COUNTER = 0x9050
TRAMPOLINES = 0x9060
PLAY_CALLS = 151
COMPANION_REGISTERS = set(range(0xd407, 0xd415))
VOICE_STORES = {
    0x1145: 0xd405, 0x114a: 0xd406,
    0x12b8: 0xd405, 0x12c7: 0xd406, 0x12cf: 0xd404,
    0x1421: 0xd402, 0x1427: 0xd403, 0x1433: 0xd400,
    0x1439: 0xd401, 0x143f: 0xd405, 0x1445: 0xd406,
    0x1450: 0xd404, 0x1458: 0xd404,
}
GLOBAL_STORES = {0x124d: 0xd417, 0x142d: 0xd416}

# A separate module namespace relocates the existing assembler without changing
# the standalone builder's $1000 contract (reconstruct-drax-bass.py: LOAD).
spec = importlib.util.spec_from_file_location("context_reconstruction", ROOT / "scripts/reconstruct-drax-bass.py")
reconstruction = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reconstruction)
reconstruction.LOAD = BASS_LOAD


def word(value):
    return value.to_bytes(2, "little")


def patch_instruction(payload, load, address, expected, replacement):
    offset = address - load
    require(0 <= offset <= len(payload) - len(expected), "Patch lies outside original payload")
    require(payload[offset:offset + len(expected)] == expected, f"Patch precondition failed at ${address:04x}")
    require(len(expected) == len(replacement), "Patch must preserve original instruction span")
    payload[offset:offset + len(expected)] = replacement


def build_context(original):
    require(reconstruction.digest(original) == reconstruction.SOURCE_SHA256, "DRAX source SHA-256 differs from the pinned reference")
    require(original[8:14] == bytes.fromhex("000010001003"), "Original init/play contract differs")
    require(original[118:120] == bytes.fromhex("0014"), "Original must declare one PAL MOS6581")
    load = int.from_bytes(original[124:126], "little")
    original_payload = original[126:]
    require(load == 0x0f00 and load + len(original_payload) < BASS_LOAD, "Original payload overlaps replacement RAM")
    recipe = reconstruction.read_recipe(reconstruction.STUDY / "instrument.json")
    require(recipe["playCalls"] == PLAY_CALLS and recipe["renderSeconds"] == 3, "Context comparison requires the bounded original bass recipe")
    source = (reconstruction.STUDY / "player.asm").read_text()
    independent_sid, bass_build = reconstruction.build_psid(recipe, source)
    bass = independent_sid[124:]
    require(BASS_LOAD + len(bass) < WRAPPER_INIT, "Independent bass overlaps wrapper")
    payload = bytearray(TRAMPOLINES + 12 * len(VOICE_STORES) - load)
    payload[:len(original_payload)] = original_payload
    payload[BASS_LOAD - load:BASS_LOAD - load + len(bass)] = bass
    init = b"\xa9\x00\x8d" + word(COUNTER) + b"\x20" + word(BASS_LOAD) + b"\xa9\x00\xaa\xa8\x20\x00\x10\x60"
    play = b"\xad" + word(COUNTER) + b"\xc9" + bytes([PLAY_CALLS]) + b"\xb0\x0a\x20\x03\x10\x20" + word(BASS_LOAD + 3) + b"\xee" + word(COUNTER) + b"\x60\x4c" + word(BASS_LOAD + 3)
    payload[WRAPPER_INIT - load:WRAPPER_INIT - load + len(init)] = init
    payload[WRAPPER_PLAY - load:WRAPPER_PLAY - load + len(play)] = play
    origins, patches = {}, []
    for index, (pc, register) in enumerate(VOICE_STORES.items()):
        address = TRAMPOLINES + index * 12
        expected = b"\x99" + word(register)
        # PHP/PLP retain flags: CPY must not alter the original driver's carry
        # or branch decisions. Only Y=0 is bass in the pinned writer trace.
        routine = b"\x08\xc0\x00\xf0\x05\x28" + expected + b"\x60\x28\x60"
        payload[address - load:address - load + len(routine)] = routine
        replacement = b"\x20" + word(address)
        patch_instruction(payload, load, pc, expected, replacement)
        origins[address + 6] = pc
        patches.append({"pc": pc, "from": expected.hex(), "to": replacement.hex(), "trampoline": address})
    for pc, register in GLOBAL_STORES.items():
        expected = b"\x8d" + word(register)
        patch_instruction(payload, load, pc, expected, b"\xea" * 3)
        patches.append({"pc": pc, "from": expected.hex(), "to": "eaeaea", "owner": "independent bass"})
    header = bytearray(original[:124])
    for offset, value in ((8, load), (10, WRAPPER_INIT), (12, WRAPPER_PLAY)):
        struct.pack_into(">H", header, offset, value)
    header[22:54] = b"DRAX mix / independent bass".ljust(32, b"\x00")
    sid = bytes(header) + payload
    return sid, {
        "sourceSha256": reconstruction.digest(original), "hybridSha256": reconstruction.digest(sid),
        "loadAddress": load, "originalPayloadEnd": load + len(original_payload),
        "bassLoadAddress": BASS_LOAD, "bassPayloadBytes": len(bass),
        "initAddress": WRAPPER_INIT, "playAddress": WRAPPER_PLAY,
        "patches": patches, "trampolineOrigins": origins,
        "independentSid": independent_sid, "independentListing": bass_build["listing"],
    }


def observed_audit(sid, calls, trampoline_origins=None):
    origins = trampoline_origins or {}
    stores = {}

    def observe(cpu, memory):
        pc = cpu.pc
        instruction, mode = cpu.disassemble[memory.data[pc]]
        if instruction not in ("STA", "STX", "STY") or mode not in ("abs", "abx", "aby"):
            return
        address = memory.data[pc + 1] | memory.data[pc + 2] << 8
        if mode == "abx":
            address += cpu.x
        elif mode == "aby":
            address += cpu.y
        if 0xd400 <= address <= 0xd418:
            stores[(memory.phase, memory.tick, memory.instruction_cycle, address)] = pc

    report, writes = audit_psid(sid, calls, observer=observe)
    for row in writes:
        key = (row["phase"], row["tick"], row["instructionStartCycle"], row["address"])
        require(key in stores, "SID write lacks an observed absolute store")
        pc = stores[key]
        row.update(machinePc=pc, instructionPc=origins.get(pc, pc))
    return report, writes


def verify_execution(original, independent, hybrid, calls):
    original_hybrid = [row for row in hybrid if row["instructionPc"] < BASS_LOAD]
    require(all(row["address"] in COMPANION_REGISTERS for row in original_hybrid if row["phase"] == "play"), "Original runtime still writes bass or shared filter/volume")
    companion = lambda rows: [row for row in rows if row["address"] in COMPANION_REGISTERS]
    identity = lambda row: (row["phase"], row["tick"], row["address"], row["value"])
    left, right = companion(original), companion(original_hybrid)
    require([(*identity(row), row["instructionPc"]) for row in left] == [(*identity(row), row["instructionPc"]) for row in right], "Companion writes differ in call, address, value, order or original writer")
    own = [row for row in hybrid if BASS_LOAD <= row["instructionPc"] < WRAPPER_INIT and row["phase"] == "play"]
    expected = [row for row in independent if row["phase"] == "play"]
    require(all(row["address"] not in COMPANION_REGISTERS for row in own), "Independent runtime overwrites accompaniment")
    require([identity(row) for row in own] == [identity(row) for row in expected], "Independent bass writes differ in call, address, value or order")
    deltas = [b["instructionStartCycle"] - a["instructionStartCycle"] for a, b in zip(left, right) if "instructionStartCycle" in a and "instructionStartCycle" in b]
    return {
        "playCalls": calls, "companionWrites": len(left), "independentRuntimeWrites": len(own),
        "companionOrderedCallAddressValueEquality": True, "companionOriginalWriterEquality": True,
        "independentBassOrderedCallAddressValueEquality": True, "originalRuntimeBassAndGlobalWrites": 0,
        "companionInstructionStartCycleDeltas": {"minimum": min(deltas), "maximum": max(deltas)} if deltas else None,
        "exactWithinFrameTiming": False,
    }


def audit_context(original, sid, built):
    original_audit, original_writes = observed_audit(original, PLAY_CALLS)
    own_audit, own_writes = observed_audit(built["independentSid"], PLAY_CALLS)
    hybrid_audit, hybrid_writes = observed_audit(sid, PLAY_CALLS, built["trampolineOrigins"])
    observed = {row["instructionPc"] for row in original_writes if row["phase"] == "play"}
    require(observed == set(VOICE_STORES) | set(GLOBAL_STORES), "Executed original writer inventory differs from patch preconditions")
    guard = verify_execution(original_writes, own_writes, hybrid_writes, PLAY_CALLS)
    guard.update(originalAudit=original_audit, independentAudit=own_audit, hybridAudit=hybrid_audit)
    return guard


def write_wav(path, audio, samples):
    values = array("h", samples)
    if sys.byteorder != "little":
        values.byteswap()
    with Path(path).open("xb") as stream:
        with wave.open(stream, "wb") as output:
            output.setparams((audio.channels, 2, audio.sample_rate, 0, "NONE", "not compressed"))
            output.writeframes(values.tobytes())


def common_gain_comparison(original_wav, hybrid_wav, output):
    audio = [read_pcm16(path) for path in (original_wav, hybrid_wav)]
    require((audio[0].sample_rate, audio[0].channels, audio[0].frames) == (audio[1].sample_rate, audio[1].channels, audio[1].frames), "Context renders must have identical format and duration")
    metrics = [inspect_wav(path) for path in (original_wav, hybrid_wav)]
    require(all(item["clippedSamples"] == 0 and item["acRms"] > 1 for item in metrics), "Context render is silent or clipped")
    peak_limit = math.floor(32767 * 10 ** (-1 / 20))
    gain = min(1.0, *(peak_limit / item["peak"] for item in metrics))
    copies = [output / "original.wav", output / "reconstructed-in-context.wav"]
    scaled = [array("h", (round(sample * gain) for sample in value.samples)) for value in audio]
    for path, value, samples in zip(copies, audio, scaled):
        write_wav(path, value, samples)
    rate, channels = audio[0].sample_rate, audio[0].channels
    gap_frames = round(rate * 0.5)
    write_wav(output / "full.ab.wav", audio[0], scaled[0] + array("h", [0]) * (gap_frames * channels) + scaled[1])
    for label, start, seconds in (("context", 1.8, 1.2), ("exact", 2.02, 0.73)):
        first, frames = round(start * rate), round(seconds * rate)
        cuts = [samples[first * channels:(first + frames) * channels] for samples in scaled]
        for suffix, samples in zip(("original", "reconstructed"), cuts):
            write_wav(output / f"{label}.{suffix}.wav", audio[0], samples)
        write_wav(output / f"{label}.ab.wav", audio[0], cuts[0] + array("h", [0]) * (gap_frames * channels) + cuts[1])
    return {
        "method": "One common scalar gain, chosen over both complete mixes for 1 dB peak headroom; no independent level matching",
        "gain": gain, "gainDb": 20 * math.log10(gain), "inputs": metrics,
        "outputs": [inspect_wav(path) for path in copies], "gapFrames": gap_frames,
        "fullComparison": inspect_wav(output / "full.ab.wav"),
        "segments": [{"label": "original", "startFrame": 0, "endFrame": audio[0].frames}, {"label": "gap", "startFrame": audio[0].frames, "endFrame": audio[0].frames + gap_frames}, {"label": "reconstructed bass in context", "startFrame": audio[0].frames + gap_frames, "endFrame": 2 * audio[0].frames + gap_frames}],
        "listeningReview": None,
    }


def run_context(reference, output, renderer=ROOT / ".local/bin/render-sid"):
    reference, output, renderer = map(lambda path: Path(path).resolve(), (reference, output, renderer))
    build_root = (ROOT / "build/drax-bass-context").resolve()
    require(output == build_root or build_root in output.parents, "Derived original driver must remain in ignored build/drax-bass-context")
    require(not output.exists() and not output.is_symlink(), "Choose a fresh output directory")
    original = reference.read_bytes()
    sid, built = build_context(original)
    guard = audit_context(original, sid, built)
    renderer_sha = reconstruction.digest(renderer.read_bytes())
    output.mkdir(parents=True)
    (output / "hybrid.sid").write_bytes(sid)
    (output / "independent.relocated.sid").write_bytes(built["independentSid"])
    (output / "independent.relocated.prg").write_bytes(word(BASS_LOAD) + built["independentSid"][124:])
    (output / "independent.listing").write_text(built["independentListing"])
    reconstruction.write_json(output / "build.json", {key: value for key, value in built.items() if key not in ("independentSid", "independentListing")})
    reconstruction.write_json(output / "execution-guard.json", guard)
    _, hybrid_writes = observed_audit(sid, PLAY_CALLS, built["trampolineOrigins"])
    reconstruction.write_json(output / "hybrid.writes.json", hybrid_writes)
    for label, source in (("original", reference), ("hybrid", output / "hybrid.sid")):
        reconstruction.run_process([str(renderer), str(source), str(output / f"{label}.full.raw.wav"), "3"], output / f"{label}.render.json")
    audio = common_gain_comparison(output / "original.full.raw.wav", output / "hybrid.full.raw.wav", output)
    require(reference.read_bytes() == original, "Archived original changed")
    require(reconstruction.digest(renderer.read_bytes()) == renderer_sha, "Renderer changed during comparison")
    report = {
        "schemaVersion": 1, "source": {"path": str(reference), "sha256": built["sourceSha256"], "preserved": True},
        "rendererSha256": renderer_sha, "hybridSha256": built["hybridSha256"],
        "profile": "One PAL MOS6581; one original play and one independent bass play per frame, through 151 calls",
        "filterOwner": "Original init clears/configures the SID after independent initialization; independent bass owns all runtime filter/volume writes",
        "ending": "After 151 calls the wrapper stops the original driver and calls the independent player's explicit volume-zero ending",
        "execution": guard, "audio": audio,
        "referenceDriverIncluded": True, "derivedDriverStorage": "Ignored local build output only",
        "limitations": "Bounded 3-second in-context experiment, not a whole-song replacement. The original init and companion calculations remain active; only its runtime bass and global SID stores are suppressed. Trampolines preserve A/X/Y/flags, companion writer order, addresses and values, but add cycles. Independent bass executes after accompaniment, so within-frame timing, oscillator/noise phase and analog state can differ. All voices run on one emulated SID with its shared-filter routing; no PCM stems are summed. Common gain preserves relative mix levels and does not establish perceived loudness or a listening verdict.",
        "listeningReview": None,
    }
    reconstruction.write_json(output / "study.json", report)
    print(f"Verified {guard['companionWrites']} original companion writes and {guard['independentRuntimeWrites']} independent bass/global writes; full comparison: {output / 'full.ab.wav'}")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--renderer", type=Path, default=ROOT / ".local/bin/render-sid")
    args = parser.parse_args()
    run_context(args.reference, args.output, args.renderer)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f"Bass context comparison failed: {error}")
