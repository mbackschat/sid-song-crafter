"""Export the bounded Rambo master-arrangement package from immutable evidence."""

import argparse
from bisect import bisect_right
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

from catalog import GitSource, REPOSITORY, encode, require, source_path, verify_sid
from sid_clock import PAL_CLOCK

ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVISION = "3db086b6963676ef75f34d7f77c3b67232a777fb"
SCORE_PATH = "songs/rambo-loader.json"
NOTE_PATH = "evidence/rambo-centered-native/preparation/source-note-events.json.gz"
CPU_PATH = "evidence/rambo-form/complete40000/events.json.gz"
SID_PATH = "samples/rambo-loader/rambo-loader-main.sid"
OWNER = "docs/research/composition/rambo-preparation.md#independent-numeric-loader"
PROGRAM_OWNER = "docs/research/composition/instruments/rambo-decoded-programs.md"
OUTPUT = ROOT / "samples/composition/rambo-main.json"
PART_IDS = ("lead", "bass", "arpeggio")


def materialize(pointer, payload, path):
    match = re.fullmatch(rb"version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize ([0-9]+)\n", pointer)
    require(match is not None, f"source pointer: unsupported LFS record: {path}")
    require(len(payload) == int(match[2]) and hashlib.sha256(payload).hexdigest().encode() == match[1],
            f"source fingerprint: materialized LFS bytes differ from pinned evidence: {path}")
    return payload


class PinnedSource(GitSource):
    def __init__(self, root):
        super().__init__(Path(root), SOURCE_REVISION)

    def blob(self, path):
        source_path(path, "source.path")
        if path not in self.cache:
            listing = self._git("ls-tree", "-l", self.revision, "--", path).decode().rstrip("\n")
            match = re.fullmatch(r"100644 blob ([0-9a-f]{40})\s+([0-9]+)\t" + re.escape(path), listing)
            require(match is not None and int(match[2]) < 2 * 1024 * 1024, f"source.path: missing or oversized regular blob: {path}")
            raw = self._git("cat-file", "blob", match[1])
            if raw.startswith(b"version"):
                local = self.root / path
                require(local.is_file() and not local.is_symlink(), f"source LFS materialization missing: {path}; restore the pinned evidence locally")
                require(local.resolve().is_relative_to(self.root.resolve()), f"source.path: materialization escapes repository: {path}")
                raw = materialize(raw, local.read_bytes(), path)
            self.cache[path] = raw
        return self.cache[path]

    def json(self, path):
        raw = self.blob(path)
        return json.loads(gzip.decompress(raw) if path.endswith(".gz") else raw)


def seconds(source_call):
    return (source_call - 1586) * 19656 / PAL_CLOCK


def byte_array(values, size, label):
    require(type(values) is list and len(values) == size and all(type(v) is int and 0 <= v <= 255 for v in values),
            f"{label}: expected {size} bytes")


def program_label(data, part):
    if data[24] & 2:
        return "Carried-in sync pulse", "A pulse state with oscillator sync enabled, carried into the selected boundary before the short lead phrase begins."
    if data[13] & 8:
        offsets = ", ".join(str(value) for value in sorted(set(data[:data[11] + 1])))
        return f"Descending saw chord: {offsets}", f"A sawtooth voice cycles source pitch offsets {offsets} semitones from its base note, one tone at a time."
    if part == "bass":
        return "Moving pulse bass", "The bass pulse width advances through two additive phases while the score supplies its low-note rhythm."
    return "Short pulse lead", "A short gate countdown articulates the repeating pulse lead; the entry selects no new PWM or pitch program."


def behavior(data):
    wave = "pulse" if data[24] & 64 else "sawtooth" if data[24] & 32 else "triangle" if data[24] & 16 else "other waveform"
    result = [f"{wave.capitalize()} control ${data[24]:02X}; attack/decay ${data[25]:02X}, sustain/release ${data[26]:02X}."]
    if data[17]:
        result.append(f"PWM program flags ${data[17]:02X}, delay {data[16]} calls, phase lengths {data[14]}/{data[15]} calls; additive steps are retained in the program data.")
    else:
        result.append("No newly selected PWM program; the event retains its exact entering sound state.")
    if data[13] & 8:
        result.append("Descending source chord-byte pitch program; its pitch sequence is computed after the base-note entry, not simultaneous independent notes.")
    elif data[13]:
        result.append(f"Sequential pitch program flags ${data[13]:02X}, delay {data[12]} calls; phase data and the entering sound state remain explicit.")
    else:
        result.append("No newly selected frequency program; this does not erase a retained entering program state.")
    result.append(f"Gate countdown {data[27]} calls and sound lifetime {data[28]} calls are separate; next-row boundaries do not measure the audible release.")
    return result


def phrase_signature(passage, part):
    return [(event["sourceCall"] - passage["sourceStartCall"], event["nodeId"], event["pitchIndex"])
            for event in passage["events"] if event["partId"] == part and event["sourceCall"] >= passage["sourceStartCall"]]


def generate(root=ROOT):
    source = PinnedSource(root)
    description = source.json(SCORE_PATH)
    require(description["profile"] == {"clock": "PAL", "sidModel": "MOS6581", "sidBase": 54272, "callCycles": 19656}, "source profile changed")
    manifest = source.json("samples/rambo-loader/main-manifest.json")
    require(manifest["sourceStartCall"] == 1586, "source entry changed")
    require(abs(1586 * 19656 / PAL_CLOCK - manifest["sourceStartSeconds"]) < 1e-12, "source clock differs from main-entry timing receipt")
    sid = source.blob(SID_PATH)
    fingerprint = hashlib.sha256(sid).hexdigest()
    require(fingerprint == manifest["artifacts"]["main-sid"]["sha256"], "SID identity differs from main-entry manifest")
    verify_sid(sid, {"clock": "PAL", "model": "MOS6581", "sidCount": 1, "baseAddress": 54272, "subtune": 1, "routing": "mono"})
    notes = source.json(NOTE_PATH)
    cpu = source.json(CPU_PATH)
    rows = {voice: [row for row in cpu if row["kind"] == "row-duration-store" and row["voice"] == voice] for voice in range(3)}
    calls = {voice: [row["call"] for row in timeline] for voice, timeline in rows.items()}
    fetches = {(e["call"], e["voice"], e["stream"]): e for e in cpu if e["kind"] == "fetch" and e.get("rowKind") == "note"}
    programs, all_events = {}, []
    for note in notes:
        call, voice = note["call"], note["voiceIndex"]
        if call >= 5682:
            continue
        following = bisect_right(calls[voice], call)
        require(following < len(calls[voice]), "source row lacks a next transition")
        end = calls[voice][following]
        if end <= 5426:
            continue
        key = (call, voice, note["sourceAddress"])
        require(key in fetches, "note entry lacks original CPU evidence")
        fetched = fetches[key]
        pitch = ((fetched["upcomingBytes"][0] % 96) + fetched["state"]["voices"][voice]["transpose"]) & 255
        require(pitch == note["pitchIndex"], "note entry pitch differs from original CPU evidence")
        node = description["program"][note["nodeId"]]
        require(node["sourceAddress"] == note["sourceAddress"], "source graph address differs")
        byte_array(note["patch"], 49, "program data")
        byte_array(note["entrySound"], 39, "event entrySound")
        program_id = "state-" + hashlib.sha256(bytes(note["patch"])).hexdigest()[:16]
        title, summary = program_label(note["patch"], PART_IDS[voice])
        programs[program_id] = {"id": program_id, "title": title,
                                "kind": "source-program-state", "description": summary + " This label describes the observed program state, not a recovered instrument name.",
                                "evidenceLevel": "verified", "behavior": behavior(note["patch"]),
                                "program": {"data": note["patch"]}, "sourcePath": PROGRAM_OWNER}
        all_events.append({"id": f"note-{voice + 1}-{call}", "partId": PART_IDS[voice], "instrumentId": program_id,
                           "sourceCall": call, "endSourceCall": end, "startSeconds": seconds(call), "endSeconds": seconds(end),
                           "pitchIndex": pitch, "frequencyWord": description["frequencyWords"][pitch],
                           "nodeId": note["nodeId"], "sourceAddress": note["sourceAddress"],
                           "entrySound": note["entrySound"], "evidenceLevel": "verified"})
    passages = []
    for index, (first, last) in enumerate(((5426, 5554), (5554, 5682))):
        selected = [event for event in all_events if event["sourceCall"] < last and event["endSourceCall"] > first]
        selected.sort(key=lambda event: (event["sourceCall"], event["partId"]))
        require(selected and {event["partId"] for event in selected} == set(PART_IDS), "selected passage lacks a physical part")
        dependencies = [{"kind": "shared-chip-filter", "partIds": list(PART_IDS), "evidenceLevel": "verified",
                         "description": "These three physical voices share one chip's filter, master volume and mono output. The source uses no per-voice pan.",
                         "sourcePath": "docs/research/sid/dual-sid.md#plan-the-sound-hardware-and-the-mix-together"}]
        for event in selected:
            control = programs[event["instrumentId"]]["program"]["data"][24]
            if control & 6:
                modulator = PART_IDS[(PART_IDS.index(event["partId"]) - 1) % 3]
                coupling = {2: "sync", 4: "ring modulation", 6: "sync and ring modulation"}[control & 6]
                dependencies.append({"kind": "oscillator-coupling", "partIds": [event["partId"], modulator], "evidenceLevel": "verified",
                                     "description": f"The carried-in {event['partId']} has control ${control:02X}; its {coupling} dependency on {modulator} persists through source call {event['endSourceCall'] - 1}, before the next row replaces it.",
                                     "sourcePath": "songs/studies/rambo-centered-native/arrangement.json"})
        passages.append({"id": "lead-phrase" if index == 0 else "lead-phrase-return", "title": "Short pulse phrase over bass and arpeggio" if index == 0 else "The lead phrase repeats over a shifted bass",
                         "sourceStartCall": first, "sourceEndCall": last, "startSeconds": seconds(first), "endSeconds": seconds(last),
                         "recurrence": None if index == 0 else {"of": "lead-phrase", "partIds": ["lead"], "relationship": "same-source-phrase", "description": "The lead reuses the same graph nodes, relative entry times and base pitches. The bass reuses its rhythm and graph nodes eight semitones higher; this is not an identical whole-mix repeat."},
                         "description": ("Follow the short pulse lead against the moving pulse bass and the descending saw chord figures. The carried-in sync pulse hands over to the short-note lead at the next source call." if index == 0 else "Follow the same short pulse lead as the bass repeats its rhythm eight semitones higher; the chord-program state changes with the accompaniment. These are observed source relationships, without a claim about Galway's intention."),
                         "events": selected, "dependencies": dependencies, "evidenceLevel": "derived", "sourcePath": OWNER})
    used = {event["instrumentId"] for passage in passages for event in passage["events"]}
    first, second = passages
    require(phrase_signature(first, "lead") == phrase_signature(second, "lead"), "declared lead recurrence differs")
    bass = [phrase_signature(passage, "bass") for passage in passages]
    require(len(bass[0]) == len(bass[1]) and all(a[:2] == b[:2] and b[2] - a[2] == 8 for a, b in zip(*bass)), "declared bass shift differs")
    for owner in (OWNER, PROGRAM_OWNER, "samples/rambo-loader/README.md", "songs/studies/rambo-centered-native/arrangement.json",
                  "docs/research/sid/dual-sid.md#plan-the-sound-hardware-and-the-mix-together"):
        source.owner(owner)
    return {"schemaVersion": 1, "id": "rambo-loader-main-composition", "catalogEntryId": "rambo-loader-main", "title": "Rambo: master arrangement and source programs",
            "source": {"repository": REPOSITORY, "revision": SOURCE_REVISION, "scorePath": SCORE_PATH, "evidencePath": NOTE_PATH, "rightsPath": "samples/rambo-loader/README.md"},
            "binding": {"sidSha256": fingerprint, "subtune": 1, "clock": "PAL", "sidModel": "MOS6581", "sidCount": 1, "baseAddress": 54272, "routing": "mono"},
            "timing": {"sourceStartCall": 1586, "callCycles": 19656, "clockHz": PAL_CLOCK, "timeBasis": "source-call-grid", "rule": "(sourceCall-sourceStartCall)*callCycles/clockHz"},
            "coverage": {"scope": "selected-passages", "wholeSong": False, "description": "Two adjacent 128-call source units only. All note rows intersecting each unit are included, with program state at entry. Event ends are the next executed score transitions, not audible-tail boundaries. Role labels are editorial descriptions of source allocation. This is not whole-song form, a complete audible-state reconstruction, or composer-intent evidence."},
            "parts": [{"id": part, "title": title, "role": role, "evidenceLevel": "derived", "sourcePath": "songs/studies/rambo-centered-native/arrangement.json"} for part, title, role in
                      (("lead", "Lead", "Foreground pulse line on source physical voice 1"), ("bass", "Bass", "Lower pulse accompaniment on source physical voice 2"), ("arpeggio", "Arpeggio / modulator", "Computed chord program on source physical voice 3; also the lead's oscillator modulator during coupled source gestures"))],
            "instruments": [programs[key] for key in sorted(used)], "allocations": [{"partId": part, "chip": 1, "voice": voice + 1} for voice, part in enumerate(PART_IDS)],
            "passages": passages, "rights": {"license": "GPL-3.0-only", "attribution": "Composed, arranged and programmed by Martin Galway, 1985. Independent symbolic reconstruction and bounded export by SID Song Crafter. Retain Galway attribution and GPLv3 for the music-derived score/program material; independent tools retain MIT separately.", "sourcePath": "samples/rambo-loader/README.md"}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "check"))
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    expected = encode(generate())
    if args.command == "generate":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(expected)
    else:
        require(args.output.read_bytes() == expected, "composition package differs from deterministic pinned-source export")
    print(f"Composition package {args.command}: {args.output} ({len(expected)} bytes)")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
