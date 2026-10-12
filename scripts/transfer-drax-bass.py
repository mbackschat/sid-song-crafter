"""Audition the decoded bass in an original SID-Wizard arrangement on one 6581."""

import argparse
from array import array
import copy
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys

from audio_comparison import Pcm16, inspect_wav, measure_pcm, read_pcm16
from verify_player import require


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


context = load_script("context-drax-bass")
reconstruction = context.reconstruction
comparison = load_script("compare-native-patch")
native = comparison.native_song
vice_trace = load_script("trace-sid-vice")
word = context.word
write_json = reconstruction.write_json
BASS_REGISTERS = set(range(0xd407, 0xd40e))
GLOBAL_REGISTERS = set(range(0xd415, 0xd419))
COMPANION_REGISTERS = set(range(0xd400, 0xd407)) | set(range(0xd40e, 0xd415))
VOICE_STORES = {0x1129: 0xd406, 0x112f: 0xd405, 0x1135: 0xd400, 0x113b: 0xd401, 0x1141: 0xd402, 0x1147: 0xd403, 0x114d: 0xd404}
GLOBAL_STORES = {0x115a: 0xd417, 0x1161: 0xd418, 0x1177: 0xd416, 0x117c: 0xd415}
INIT, PLAY, COUNTER, TRAMPOLINES = 0x9000, 0x9040, 0x9080, 0x90a0
CALLS = 226


def voice_interceptor(register):
    # Preserve flags around CPX: the Extra writer continues the same channel loop.
    return b"\x08\xe0\x07\xf0\x05\x28\x9d" + word(register) + b"\x60\x28\x60"


def build_bass(recipe):
    adapted = copy.deepcopy(recipe)
    adapted["instrument"]["filterRoutingResonance"] = (adapted["instrument"]["filterRoutingResonance"] & 0xf0) | 2
    source = (reconstruction.STUDY / "player.asm").read_text()
    # Only direct voice stores move. The indexed SID initialization still clears
    # $D400..$D417; moving it would write beyond the sound-register block.
    for register in range(0xd400, 0xd407):
        source = source.replace(f"STA ${register:04X}\n", f"STA ${register + 7:04X}\n")
    return reconstruction.build_psid(adapted, source)


def transfer_recipe(manifest, frames, calls):
    require(manifest["voices"][1]["name"] == "bass", "Transfer requires bass on native voice two")
    recipe = reconstruction.read_recipe(reconstruction.STUDY / "instrument.json")
    notes = []
    for note in manifest["voices"][1]["notes"]:
        tick = note["startTick"]
        if tick >= calls - 3:
            continue
        require(tick >= 2 and tick + 2 < len(frames), "Bass start needs setup and a traced pitched body")
        body = frames[tick + 2]
        frequency = body[7] | body[8] << 8
        require(frequency > 0 and body[11] & 0x70 and not body[11] & 0x88, "Native bass lacks a pitched body")
        notes.append({"initCall": tick, "frequency": frequency})
    require(notes, "Excerpt contains no bass notes")
    recipe.update(title="Elise decoded bass transfer", playCalls=calls, renderSeconds=5,
                  excerpt={"startSeconds": 0, "seconds": 4.5}, notes=notes)
    return recipe


def verify_independence(frames):
    require(all(frame[23] & 0x0f in (0, 2) and not frame[24] & 0x80 for frame in frames), "Companion voices depend on shared filter or voice-three disconnect")
    require(all(not frame[control] & 6 for frame in frames for control in (4, 18)), "Companion oscillator coupling prevents isolated bass substitution")


def build_mix(original, original_writes, bass_recipe=None):
    profile = vice_trace.psid_profile(original)
    require((profile["loadAddress"], profile["initAddress"], profile["playAddress"]) == (0x1000, 0x1000, 0x1003), "Transfer requires the Extra $1000/$1003 PSID layout")
    require(profile["sidModel"] == "MOS6581", "Transfer requires one explicit PAL MOS6581")
    observed = {row["instructionPc"] for row in original_writes if row["phase"] == "play"}
    require(observed == set(VOICE_STORES) | set(GLOBAL_STORES), "Executed Extra writer inventory differs")
    load, original_end = profile["loadAddress"], profile["endAddress"]
    require(original_end < context.BASS_LOAD, "Native player overlaps replacement RAM")
    payload = bytearray(TRAMPOLINES + 12 * len(VOICE_STORES) - load)
    payload[:len(profile["payload"])] = profile["payload"]
    origins, patches, independent = {}, [], None
    bass_build = None
    if bass_recipe is not None:
        independent, bass_build = build_bass(bass_recipe)
        bass = independent[124:]
        require(context.BASS_LOAD + len(bass) < INIT, "Bass overlaps wrapper")
        payload[context.BASS_LOAD - load:context.BASS_LOAD - load + len(bass)] = bass
        for index, (pc, register) in enumerate(VOICE_STORES.items()):
            address = TRAMPOLINES + index * 12
            routine = voice_interceptor(register)
            payload[address - load:address - load + len(routine)] = routine
            expected = b"\x9d" + word(register)
            context.patch_instruction(payload, load, pc, expected, b"\x20" + word(address))
            origins[address + 6] = pc
            patches.append({"pc": pc, "expected": expected.hex(), "trampoline": address})
        for pc, register in GLOBAL_STORES.items():
            expected = b"\x8d" + word(register)
            context.patch_instruction(payload, load, pc, expected, b"\xea" * 3)
            patches.append({"pc": pc, "expected": expected.hex(), "replacement": "eaeaea"})
    init = (b"\x20" + word(context.BASS_LOAD)) if independent else b""
    init += b"\xa9\x00\xaa\xa8\x20\x00\x10\xa9\x00\x8d" + word(COUNTER)
    if independent:
        init += b"\xa9\x1f\x8d\x18\xd4"
    init += b"\x60"
    body = b"\x20\x03\x10"
    if independent:
        body += b"\x20" + word(context.BASS_LOAD + 3)
    body += b"\xee" + word(COUNTER) + b"\x60"
    play = b"\xad" + word(COUNTER) + b"\xc9" + bytes([CALLS]) + b"\xb0" + bytes([len(body)]) + body
    play += b"\xa9\x00\x8d\x18\xd4\x8d\x04\xd4\x8d\x0b\xd4\x8d\x12\xd4\x60"
    payload[INIT - load:INIT - load + len(init)] = init
    payload[PLAY - load:PLAY - load + len(play)] = play
    header = bytearray(original[:124])
    struct.pack_into(">HHH", header, 8, load, INIT, PLAY)
    return bytes(header) + payload, {"origins": origins, "patches": patches, "independent": independent, "bassBuild": bass_build}


def verify_transfer(original, independent, combined):
    runtime = lambda rows: [row for row in rows if row["phase"] == "play" and row["tick"] < CALLS]
    identity = lambda row: (row["tick"], row["address"], row["value"], row["instructionPc"])
    native_rows = [r for r in runtime(combined) if r["instructionPc"] < context.BASS_LOAD]
    require(all(r["address"] in COMPANION_REGISTERS for r in native_rows), "Native runtime overwrites bass or shared filter")
    expected = [r for r in runtime(original) if r["address"] in COMPANION_REGISTERS]
    require([identity(r) for r in native_rows] == [identity(r) for r in expected], "Companion call/address/value/order/writer changed")
    own = [r for r in runtime(combined) if context.BASS_LOAD <= r["instructionPc"] < INIT]
    require(all(r["address"] in BASS_REGISTERS | GLOBAL_REGISTERS for r in own), "Bass overwrites accompaniment")
    require([identity(r) for r in own] == [identity(r) for r in runtime(independent)], "Independent bass execution differs")
    require(len(runtime(combined)) == len(native_rows) + len(own), "Unexpected runtime SID writer")
    deltas = [b["instructionStartCycle"] - a["instructionStartCycle"] for a, b in zip(expected, native_rows)]
    return {"companionWrites": len(expected), "bassWrites": len(own), "orderedCompanionEquality": True,
            "orderedIndependentBassEquality": True, "withinFrameCompanionCycleDelta": [min(deltas), max(deltas)],
            "exactCycleEquality": False}


def prepare_audio(output):
    clips = []
    for label in ("a", "b"):
        reconstruction.excerpt(output / f"{label}.full.wav", output / f"{label}.raw.wav", 0, 4.5)
        clips.append(read_pcm16(output / f"{label}.raw.wav"))
    metrics = [inspect_wav(output / f"{label}.raw.wav") for label in ("a", "b")]
    require(all(m["clippedSamples"] == 0 and m["acRms"] > 1 for m in metrics), "Silent or clipped comparison")
    gain = min(1.0, *(math.floor(32767 * 10 ** (-1 / 20)) / m["peak"] for m in metrics))
    scaled = [array("h", (round(sample * gain) for sample in clip.samples)) for clip in clips]
    for label, clip, samples in zip(("a", "b"), clips, scaled):
        context.write_wav(output / f"{label}.wav", clip, samples)
    gap = array("h", [0]) * round(clips[0].sample_rate * 0.5)
    context.write_wav(output / "bass.ab.wav", clips[0], scaled[0] + gap + scaled[1])
    return {"gain": gain, "gainDb": 20 * math.log10(gain), "policy": "One common scalar; no independent normalization",
            "a": "Previous bass, preferred own B arrangement rerendered on 6581", "b": "Same arrangement with independently computed bass",
            "segmentSeconds": 4.5, "gapSeconds": 0.5, "metrics": metrics}


def run_transfer(recipe_path, output, vice=False):
    recipe_path, output = Path(recipe_path).resolve(), Path(output).resolve()
    require(not output.exists() and not output.is_symlink(), "Choose a fresh output directory")
    recipe_bytes = recipe_path.read_bytes()
    recipe = json.loads(recipe_bytes)
    score_path = (recipe_path.parent / recipe["score"]).resolve()
    score_bytes = score_path.read_bytes()
    require(recipe.get("sidCount", 1) == 1, "Transfer supports one SID")
    output.mkdir(parents=True)
    (output / "source.recipe.json").write_bytes(recipe_bytes)
    (output / "score.json").write_bytes(score_bytes)
    recipe.update(score=str(output / "score.json"), sidModel="MOS6581")
    write_json(output / "recipe.json", recipe)
    converter, exporter = (load_script(name) for name in ("arrange-sidwizard", "export-sidwizard"))
    manifest = converter.arrange(output / "recipe.json", output / "conversion")
    write_json(output / "conversion.json", manifest)
    require(CALLS < manifest["stopTick"], "Comparison must remain inside the arrangement")
    exported = exporter.export_module(manifest["nativePath"], output / "export", title=manifest["title"], author=manifest["author"], released=manifest["released"], sid_model="MOS6581")
    write_json(output / "export.json", exported)
    native_evidence = output / "native"
    native_evidence.mkdir()
    comparison.audit_excerpt(manifest, exported, native_evidence, CALLS)
    original = Path(exported["sid"]).read_bytes()
    _, original_writes = context.observed_audit(original, CALLS)
    frames = native.frame_states(original_writes, CALLS)
    verify_independence(frames)
    bass_recipe = transfer_recipe(manifest, frames, CALLS)
    write_json(output / "bass.recipe.json", bass_recipe)
    bass_recipe = reconstruction.read_recipe(output / "bass.recipe.json")
    baseline, _ = build_mix(original, original_writes)
    candidate, built = build_mix(original, original_writes, bass_recipe)
    _, independent_writes = context.observed_audit(built["independent"], CALLS)
    baseline_audit, baseline_writes = context.observed_audit(baseline, CALLS + 3)
    candidate_audit, candidate_writes = context.observed_audit(candidate, CALLS + 3, built["origins"])
    guard = verify_transfer(original_writes, independent_writes, candidate_writes)
    identity = lambda rows: [(r["phase"], r["tick"], r["address"], r["value"], r["instructionPc"]) for r in rows if r["phase"] == "init" or r["tick"] < CALLS]
    require(identity(baseline_writes) == identity(original_writes), "Bounded baseline changes original writes")
    for writes in (baseline_writes, candidate_writes):
        stopped = native.frame_states(writes, CALLS + 3)[CALLS:]
        require(all(frame[24] == 0 and all(frame[r] & 1 == 0 for r in (4, 11, 18)) for frame in stopped), "Bounded player does not stop")
    guard.update(baselineAudit=baseline_audit, candidateAudit=candidate_audit, boundedEnding=True)
    write_json(output / "execution.json", guard)
    write_json(output / "patches.json", built["patches"])
    (output / "bass.listing").write_text(built["bassBuild"]["listing"])
    renderer = ROOT / ".local/bin/render-sid"
    renderer_sha = reconstruction.digest(renderer.read_bytes())
    endings = {}
    for label, sid, writes in (("a", baseline, baseline_writes), ("b", candidate, candidate_writes)):
        sid_path = output / f"{label}.sid"
        sid_path.write_bytes(sid)
        write_json(output / f"{label}.writes.json", writes)
        reconstruction.run_process([str(renderer), str(sid_path), str(output / f"{label}.full.wav"), "5"], output / f"{label}.render.json")
        pcm = inspect_wav(output / f"{label}.full.wav")
        require(pcm["frames"] == 220500 and pcm["clippedSamples"] == 0, "Incomplete or clipped full render")
        full = read_pcm16(output / f"{label}.full.wav")
        tail_frames = round(full.sample_rate * 0.2)
        tail = Pcm16(full.sample_rate, full.channels, tail_frames, full.samples[-tail_frames:], "")
        endings[label] = measure_pcm(tail)["acRms"]
        require(endings[label] < 16, "Full render lacks a quiet ending")
    audio = prepare_audio(output)
    if vice:
        reconstruction.run_process([sys.executable, str(ROOT / "scripts/trace-sid-vice.py"), str(output / "b.sid"), "--oracle", str(output / "b.writes.json"), "--first-call", "0", "--last-call", str(CALLS + 2), "--output", str(output / "vice")], output / "vice-command.json")
    require(renderer_sha == reconstruction.digest(renderer.read_bytes()), "Renderer changed")
    require(recipe_path.read_bytes() == recipe_bytes and score_path.read_bytes() == score_bytes, "Retained inputs changed")
    report = {"sourceRecipe": str(recipe_path), "recipeSha256": reconstruction.digest(recipe_bytes), "scoreSha256": reconstruction.digest(score_bytes),
              "instrumentSource": "songs/studies/drax-bass-reconstruction/instrument.json", "rendererSha256": renderer_sha,
              "instrumentSha256": reconstruction.digest((reconstruction.STUDY / "instrument.json").read_bytes()),
              "assemblySha256": reconstruction.digest((reconstruction.STUDY / "player.asm").read_bytes()),
              "adaptation": {"hardwareVoice": 2, "voiceBase": 0xd407, "filterRoutingResonance": bass_recipe["instrument"]["filterRoutingResonance"] & 0xf0 | 2, "loadAddress": context.BASS_LOAD},
              "profile": "One PAL MOS6581, 226 musical calls, explicit stop, five-second full render",
              "fullRenderFinal200msAcRms": endings,
              "bassNotes": bass_recipe["notes"], "audio": audio, "execution": guard, "viceChecked": vice,
              "listeningReview": None,
              "limitations": "Short transfer only. Both sides rerender the previously preferred MOS8580 palette on MOS6581. Native melody/chord writes are preserved, with added within-frame latency. Bass starts and executed pitches transfer; early GATE closure and longer release intentionally replace score gate lengths. Shared filter belongs to bass. No DRAX player, accompaniment or captured-event replay is included. Callable PSIDs, not standalone PRGs. No hardware or listening approval is claimed."}
    write_json(output / "study.json", report)
    print(f"Prepared {len(bass_recipe['notes'])}-note bass transfer: {output / 'bass.ab.wav'}", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--vice", action="store_true")
    args = parser.parse_args()
    run_transfer(args.recipe, args.output, args.vice)


if __name__ == "__main__":
    main()
