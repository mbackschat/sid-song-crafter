"""Reproduce bounded register studies of two pinned DRAX arrangements."""

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import psid_audit
from verify_player import CYCLES_PER_FRAME, PAL_CLOCK, require


ROOT = Path(__file__).resolve().parents[1]
PLAY_CALLS = 6000
SOURCE_SCORE_SHA256 = "a58bdad5e72a10c12b20913cf242e917b98bb010949ba3ea38f33cfe15b6368e"
ASSETS = {entry["id"]: entry for entry in json.loads((ROOT / "config/local-assets.json").read_text())["references"]}
REFERENCES = {
    "fuer-elise": {
        **{key: ASSETS["fuer-elise"][key] for key in ("sha256", "hvscPath")},
        "roles": ("percussion/bass", "melody", "chord arpeggiation"),
        "attackFrames": (12, 12, 12),
    },
    "flashdance": {
        **{key: ASSETS["flashdance"][key] for key in ("sha256", "hvscPath")},
        "roles": ("percussion/bass", "melody", "chord arpeggiation"),
        "attackFrames": (12, 40, 20),
    },
}


def load_script(filename, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


native_song = load_script("native-song.py", "drax_native_helpers")


def verify_reference(name, data):
    require(name in REFERENCES, f"Unknown reference: {name}")
    require(hashlib.sha256(data).hexdigest() == REFERENCES[name]["sha256"], f"{name} reference SHA-256 differs from the pinned archive file")


class FlashdanceDiagnosticMemory(psid_audit.AuditMemory):
    def __init__(self, sid_bases=(0xd400,)):
        super().__init__(sid_bases)
        self.ignored_writes = []

    def __setitem__(self, address, value):
        if address in (0xd419, 0xd41a):
            require(self.phase == "init" and value == 0, "Flashdance diagnostic permits only init zero writes to $d419/$d41a")
            self.ignored_writes.append({"phase": self.phase, "tick": self.tick, "address": address, "value": value})
            return
        super().__setitem__(address, value)


def audit_reference(name, data, play_calls):
    verify_reference(name, data)
    require(type(play_calls) is int and play_calls == PLAY_CALLS, "Reference claims require exactly 6000 play calls")
    if name == "fuer-elise":
        report, writes = psid_audit.audit_psid(data, play_calls)
        return report, writes, []

    # This pinned tune clears paddle registers during init; a private module keeps
    # its diagnostic exception out of the production auditor and candidate run.
    diagnostic = load_script("psid_audit.py", "drax_flashdance_diagnostic")
    memories = []

    def memory_factory(sid_bases):
        memory = FlashdanceDiagnosticMemory(sid_bases)
        memories.append(memory)
        return memory

    diagnostic.AuditMemory = memory_factory
    report, writes = diagnostic.audit_psid(data, play_calls)
    ignored = memories[0].ignored_writes
    require([row["address"] for row in ignored] == [0xd419, 0xd41a], "Pinned Flashdance init paddle-write sequence changed")
    return report, writes, ignored


def require_frames(frames):
    require(len(frames) == PLAY_CALLS, "Study claims require exactly 6000 reconstructed frames")
    require(all(len(state) == 25 and all(type(value) is int and 0 <= value <= 255 for value in state) for state in frames), "Study requires complete single-SID 25-register frames")


def midi_pitch(word):
    return round(69 + 12 * math.log2(word * PAL_CLOCK / 2**24 / 440))


def melody_events(frames):
    """Decode the pinned Für Elise pulse melody's TEST-to-body transitions.

    This player-specific boundary preserves repeated notes. It deliberately does
    not treat arpeggio steps, release modulation or noise as score-note onsets.
    """
    require_frames(frames)
    events = []
    for tick in range(1, len(frames)):
        state, previous = frames[tick], frames[tick - 1]
        word = state[7] | state[8] << 8
        if previous[11] & 8 and state[11] == 0x41 and word:
            events.append({"tick": tick, "midi": midi_pitch(word), "frequencyWord": word, "control": state[11]})
    return events


def melody_cycle(events):
    pitches = [event["midi"] for event in events]
    for size in range(1, len(events) // 2 + 1):
        ticks = events[size]["tick"] - events[0]["tick"]
        if ticks > 0 and all(pitch == pitches[index % size] for index, pitch in enumerate(pitches)) and all(events[index + size]["tick"] - event["tick"] == ticks for index, event in enumerate(events[:-size])):
            return {"notes": size, "ticks": ticks, "seconds": ticks * CYCLES_PER_FRAME / PAL_CLOCK, "completeCycles": len(events) // size, "partialCycleNotes": len(events) % size}
    return None


def episode_landmarks(events, score):
    pitches = [event["midi"] for event in events]
    source = score["voices"][0]["events"]
    result = {}
    # These boundaries belong to the pinned source form, documented in
    # docs/songs/fuer-elise-score.md; another score must not inherit them by default.
    for name, beat in (("F-major", 66.5), ("repeated-bass", 120.5)):
        indices = [index for index, note in enumerate(source) if note["startBeat"] >= beat]
        require(indices and len(source) - indices[0] >= 10, f"Source lacks the {name} landmark")
        index = indices[0]
        landmark = [note["midi"] for note in source[index:index + 10]]
        matches = [events[offset]["tick"] for offset in range(len(events) - 9) if pitches[offset:offset + 10] == landmark]
        result[name] = {"sourceBoundaryBeat": beat, "sourceEventIndex": index, "sourceFirstEventBeat": source[index]["startBeat"], "pitches": landmark, "referenceMatchTicks": matches}
    return result


def compare_fuer_elise(reference_frames, candidate_frames, manifest, score):
    require_frames(candidate_frames)
    require(manifest.get("format") == "sidwizard-arrangement-manifest-v1" and manifest.get("frameSpeed") == 1 and manifest.get("rowTicks") == 1 and manifest.get("clockHz") == PAL_CLOCK and manifest.get("ticksPerSecond") == PAL_CLOCK / CYCLES_PER_FRAME, "Candidate manifest lacks supported explicit PAL tempo-1 timing")
    require(type(score.get("quarterBpm")) in (int, float) and math.isfinite(score["quarterBpm"]) and score["quarterBpm"] > 0, "Source lacks an explicit valid tempo")
    require(len(manifest["voices"]) == len(score["voices"]) and manifest["voices"][0]["name"] == score["voices"][0]["name"] == "melody", "Candidate melody differs from source roles")
    for part, source_part in zip(manifest["voices"], score["voices"]):
        require(part["name"] == source_part["name"] and len(part["notes"]) == len(source_part["events"]), "Candidate note counts differ from source")
        for index, (note, event) in enumerate(zip(part["notes"], source_part["events"])):
            require(note["eventIndex"] == index and all(note[key] == event[key] for key in ("startBeat", "durationBeats", "midi")), "Candidate manifest notes differ from source")

    notes = manifest["voices"][0]["notes"]
    bodies = {}
    for index, note in enumerate(notes):
        require(type(note["startTick"]) is int and note["startTick"] >= 0, "Candidate source timing has an invalid start tick")
        tick = note["startTick"] + 1
        if tick >= PLAY_CALLS:
            continue
        state = candidate_frames[tick]
        control, word = state[4], state[0] | state[1] << 8
        require(control & 1 and control & 0x70 and not control & 0x88, f"Unsupported candidate study profile: melody event {index} body control is not gate-open pitched synthesis")
        expected = round(440 * 2 ** ((note["midi"] - 69) / 12) * 2**24 / PAL_CLOCK)
        require(abs(word - expected) <= 1, f"Unsupported candidate study profile: melody event {index} body pitch differs from the declared next-frame target")
        bodies[index] = {"tick": tick, "frequencyWord": word, "control": control}

    reference = melody_events(reference_frames)
    require(reference and bodies, "No observed melody events to compare")
    matched, difference = [], None
    for index, (event, note) in enumerate(zip(reference, notes)):
        if event["midi"] != note["midi"]:
            difference = {"eventIndex": index, "reference": event, "source": note, "nativeBody": bodies.get(index)}
            break
        if index not in bodies:
            break
        matched.append({"eventIndex": index, "midi": note["midi"], "startBeat": note["startBeat"], "referenceBody": event, "nativeBody": bodies[index]})
    intervals = sorted({reference[index + 1]["tick"] - reference[index]["tick"] for index in range(min(4, len(reference) - 1))})
    return {
        "candidateProfile": {"name": "Für Elise Extra next-frame melody body", "melodyVoice": 1, "bodyTickOffset": 1, "temperedWordTolerance": 1, "requirements": "One PAL SID, tempo-1 rows; melody body is gate-open pitched synthesis at onset + 1 with no TEST/noise. Intentional longer pitch transients or attack arpeggios need another study profile; rejection is not a musical-corruption verdict."},
        "method": "Pinned reference voice 2 pulse body after TEST; candidate voice 1 full-pitch body at declared onset + 1; MIDI-rounded reference pitch and candidate tempered word +/-1",
        "referenceMelodyEvents": len(reference), "nativeCoveredMelodyNotes": len(bodies), "nativeTotalMelodyNotes": len(notes),
        "consecutiveOpeningPitchMatches": len(matched), "matchedOpening": matched, "firstPositionalDifference": difference,
        "referenceOpeningSixteenthTicks": intervals,
        "referenceQuarterBpm": 60 * PAL_CLOCK / CYCLES_PER_FRAME / (intervals[0] * 4) if len(intervals) == 1 and intervals[0] > 0 else None,
        "nativeQuarterBpm": score["quarterBpm"], "observedMelodyCycle": melody_cycle(reference),
    }


def sound_design(name, frames):
    require(name in REFERENCES, f"Unknown reference: {name}")
    require_frames(frames)
    voices = []
    for voice, (role, count) in enumerate(zip(REFERENCES[name]["roles"], REFERENCES[name]["attackFrames"])):
        base = voice * 7
        attacks = [tick for tick, state in enumerate(frames) if state[base + 4] & 8 and (tick == 0 or not frames[tick - 1][base + 4] & 8)]
        samples = []
        for tick in range(attacks[0], min(attacks[0] + count, PLAY_CALLS)) if attacks else ():
            state = frames[tick]
            samples.append({"tick": tick, "frequencyWord": state[base] | state[base + 1] << 8, "control": state[base + 4], "pulseWidth": state[base + 2] | (state[base + 3] & 15) << 8, "attackDecay": state[base + 5], "sustainRelease": state[base + 6], "filterCutoff": (state[21] & 7) | state[22] << 3, "filterRoutingResonance": state[23], "filterModeVolume": state[24]})
        widths = [state[base + 2] | (state[base + 3] & 15) << 8 for state in frames]
        voices.append({"voice": voice + 1, "role": role, "controls": sorted({state[base + 4] for state in frames}), "pulseWidthRange": [min(widths), max(widths)], "firstAttack": samples})
    return {"observation": "Final register state after each play call, not bus-timed synthesis or decoded instrument source", "voices": voices}


def file_identity(path, data):
    return {"path": str(path.resolve()), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def sid_identity(path, data):
    require(len(data) >= 124 and data[:4] == b"PSID", "Study requires a complete PSID identity")
    word = lambda offset: int.from_bytes(data[offset:offset + 2], "big")
    result = file_identity(path, data)
    result.update({"title": data[22:54].split(b"\0")[0].decode("cp1252"), "author": data[54:86].split(b"\0")[0].decode("cp1252"), "released": data[86:118].split(b"\0")[0].decode("cp1252"), "version": word(4), "subtunes": word(14), "defaultSubtune": word(16), "speedBits": int.from_bytes(data[18:22], "big"), "headerFlags": word(118)})
    return result


def run_study(fuer_elise, flashdance, candidate_sid, candidate_manifest, source_score, output, play_calls):
    require(not output.exists() and not output.is_symlink(), "Choose a fresh study output directory")
    require(type(play_calls) is int and play_calls == PLAY_CALLS, "Reference claims require exactly 6000 play calls")
    inputs = {name: (path, path.read_bytes()) for name, path in (("fuer-elise", fuer_elise), ("flashdance", flashdance), ("candidate", candidate_sid), ("candidateManifest", candidate_manifest), ("sourceScore", source_score))}
    for name in REFERENCES:
        verify_reference(name, inputs[name][1])
    require(hashlib.sha256(inputs["sourceScore"][1]).hexdigest() == SOURCE_SCORE_SHA256, "Source score SHA-256 differs from the pinned Für Elise form")
    manifest, score = (json.loads(inputs[name][1]) for name in ("candidateManifest", "sourceScore"))
    require(manifest["sourceSha256"] == SOURCE_SCORE_SHA256, "Candidate manifest source identity differs from the supplied score")
    reports, artifacts = {}, {}
    for name in REFERENCES:
        audit, writes, ignored = audit_reference(name, inputs[name][1], play_calls)
        frames = native_song.frame_states(writes, play_calls)
        artifacts[f"{name}.writes.json"], artifacts[f"{name}.frames.json"] = writes, frames
        reports[name] = {"identity": sid_identity(*inputs[name]), "hvscPath": REFERENCES[name]["hvscPath"], "audit": audit, "auditClassification": "strict RAM-only" if name == "fuer-elise" else "diagnostic adapter; not a production audit pass", "ignoredInitPaddleWrites": ignored, "soundDesign": sound_design(name, frames)}
    audit, writes = psid_audit.audit_psid(inputs["candidate"][1], play_calls)
    require(audit["sidCount"] == 1, "Focused candidate study supports one SID only")
    frames = native_song.frame_states(writes, play_calls)
    artifacts["candidate.writes.json"], artifacts["candidate.frames.json"] = writes, frames
    comparison = compare_fuer_elise(artifacts["fuer-elise.frames.json"], frames, manifest, score)
    reference_events = melody_events(artifacts["fuer-elise.frames.json"])
    artifacts["fuer-elise.melody.json"] = reference_events
    comparison["episodeLandmarks"] = episode_landmarks(reference_events, score)
    report = {
        "schemaVersion": 1, "evidenceLevel": "CPU/register study", "playCalls": play_calls,
        "references": reports, "candidate": {"identity": sid_identity(*inputs["candidate"]), "audit": audit},
        "candidateManifest": file_identity(*inputs["candidateManifest"]), "sourceScore": file_identity(*inputs["sourceScore"]),
        "comparison": comparison, "artifacts": list(artifacts),
        "toolSha256": {name: hashlib.sha256((ROOT / "scripts" / name).read_bytes()).hexdigest() for name in ("study-drax-references.py", "psid_audit.py", "native-song.py")},
        "listeningReview": None,
        "limitations": "6000 PAL calls per input binary only; final register states omit within-call write order and bus timing. Für Elise extraction is specific to this pinned pulse melody, not general transcription. Candidate next-frame body checks apply to the declared study profile, not arbitrary expressive palettes. Nominal body pitch and source landmarks do not establish PCM audibility, ADSR equivalence, complete form equality, hardware fidelity or musical quality. Flashdance uses an explicitly bounded diagnostic exception; no native reference workfile or reuse license is established.",
    }
    output.mkdir(parents=True, exist_ok=False)
    for filename, value in artifacts.items():
        with (output / filename).open("x", encoding="utf-8") as file:
            json.dump(value, file, separators=(",", ":"), allow_nan=False)
            file.write("\n")
    native_song.write_json(output / "study.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("fuer-elise", "flashdance", "candidate-sid", "candidate-manifest", "source-score", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--play-calls", type=int, required=True, help="must be 6000; bounded coverage is part of this study's contract")
    args = parser.parse_args()
    report = run_study(args.fuer_elise, args.flashdance, args.candidate_sid, args.candidate_manifest, args.source_score, args.output, args.play_calls)
    print(f"Study: {args.output / 'study.json'}; opening pitch matches: {report['comparison']['consecutiveOpeningPitchMatches']}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f"Reference study failed: {error}")
