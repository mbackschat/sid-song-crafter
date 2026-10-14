"""Prepare a source-backed A ostinato beneath the accepted Bach foreground."""

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
START, END = 30.71, 41.9725
BASE = ROOT / "songs/studies/bach-toccata-full"


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def prepare(output):
    score, recipe = read(BASE / "score.json"), read(BASE / "hybrid.json")
    original = copy.deepcopy(score)
    mapping = read(BASE / "preparation.json")["mapping"]
    changes = []
    harmony = next(v for v in score["voices"] if v["name"] == "harmony")
    for index, event in enumerate(harmony["events"]):
        if START <= event["startBeat"] < END:
            assert event["midi"] == 57
            source = next(x for x in mapping if x["voice"] == "harmony" and x["eventIndex"] == index)
            before = copy.deepcopy(event)
            event["durationBeats"] = min(0.10, event["durationBeats"])
            changes.append(dict(kind="shorten-existing-A3", sourceId=source["sourceId"], sourceMidi=69, acceptedMidi=57, before=before, after=copy.deepcopy(event)))
    bass = next(v for v in score["voices"] if v["name"] == "bass")
    assert not any(START <= x["startBeat"] < END for x in bass["events"])
    supporting_ids = [x["sourceId"] for x in mapping if x["voice"] == "harmony" and START <= x["startBeat"] < END]
    for index in range(28):
        event = dict(startBeat=round(31.0975 + index * 0.375, 9), durationBeats=0.24 if index % 2 == 0 else 0.13, midi=45)
        bass["events"].append(event)
        changes.append(dict(kind="authored-eighth-A2", sourceBasis="Repeated written LH A4; no written pedal in this passage", sourceMidi=69, transposeSemitones=-24, supportingSourceIds=supporting_ids, quarterAccent=index % 2 == 0, after=copy.deepcopy(event)))
    bass["events"].sort(key=lambda event: event["startBeat"])
    assert score["voices"][0] == original["voices"][0]
    for before, after in zip(original["voices"], score["voices"]):
        assert [x for x in before["events"] if not START <= x["startBeat"] < END] == [x for x in after["events"] if not START <= x["startBeat"] < END]
    score["title"] = "Bach Toccata: bounded accompaniment groove"
    score["provenance"]["preparation"] = "preparation.json"
    score["provenance"]["completeSource"] = os.path.relpath((BASE / original["provenance"]["completeSource"]).resolve(), output)
    score["provenance"]["arrangementPlan"] = os.path.relpath(BASE / "arrangement.json", output)
    score["provenance"]["acceptedScore"] = os.path.relpath(BASE / "score.json", output)
    recipe["title"] = "Bach Toccata: A groove blend"
    recipe["authorinfo"] = "ORIGINAL:BACH A GROOVE BLEND"
    recipe["instruments"]["groove-bass"] = dict(name="BCHGRBS", control="0a", hard_restart_adsr="0f00", adsr="0392", frame1="09", wave=[["41", "00", "00"]], pulse=[["85", "00", "00"]], filter=copy.deepcopy(recipe["instruments"]["bass"]["filter"]))
    recipe["instruments"]["groove-harmony"] = dict(name="BCHGRHM", control="0a", hard_restart_adsr="0f00", adsr="0351", frame1="09", wave=[["41", "00", "00"]], pulse=[["84", "00", "00"]], filter=[])
    for section in recipe["sections"]:
        if section["startBeat"] == START and section["endBeat"] == END:
            section["name"] = "Written RH run over source-backed A groove"
            section["voices"].update(bass="groove-bass", harmony="groove-harmony")
    assert list(recipe["instruments"])[:8] == list(read(BASE / "hybrid.json")["instruments"])
    output.mkdir(parents=True, exist_ok=False)
    write(output / "score.json", score)
    write(output / "hybrid.json", recipe)
    write(output / "preparation.json", dict(date="2026-10-14", intention="Sustained game-like propulsion through a running Bach passage, preserving recognizable foreground and organ weight", decision="Short offbeat A3 pulse articulation plus a low A2 eighth-note ostinato with longer quarter accents; no new counterline or pitch effects", acceptedScoreSha256=hashlib.sha256((BASE / "score.json").read_bytes()).hexdigest(), sourceBeatRange=[45, 60.5], performedWindowSeconds=[START, END], newBassWindowSeconds=[31.0975, 41.3525], foregroundEventsUnchanged=True, outsideWindowScoreEventsUnchanged=True, acceptedInstrumentDefinitionsAndOrderUnchanged=True, target=dict(clock="PAL", sidModel="MOS8580", sidCount=1), deviations=changes, listeningReview=None, limitations="The new A2 pulse is authored accompaniment derived from the written A4 ostinato, not a written pedal. Short-gate rhythm and sound balance require human audition; native scheduling and PCM health do not settle musical quality.", modelAssistanceReview="Skip unvalidated model preference inference; this paired human audition is the next checkpoint."))
    print(json.dumps(dict(output=str(output), articulatedA3Notes=sum(x["kind"] == "shorten-existing-A3" for x in changes), authoredA2Notes=sum(x["kind"] == "authored-eighth-A2" for x in changes), foregroundUnchanged=True)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    prepare(parser.parse_args().output.resolve())
