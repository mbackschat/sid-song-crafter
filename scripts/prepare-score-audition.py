#!/usr/bin/env python3
import argparse
from collections import defaultdict
from enum import Enum
from fractions import Fraction
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_tools import beat, import_midi, rational


class MonophonicPolicy(str, Enum):
    REJECT_OVERLAP = "reject-overlap"
    HIGHEST_AT_ONSET = "highest-at-onset"


class OverlapPolicy(str, Enum):
    REJECT_OVERLAP = "reject-overlap"
    SHORTEN_TO_NEXT_ONSET = "shorten-to-next-onset"


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def source_origins(full, selected, spans):
    origins = defaultdict(list)
    offset = Fraction(0)
    for span_index, span in enumerate(spans):
        start, end = beat(span["startBeat"]), beat(span["endBeat"])
        for part in full["parts"]:
            for event_index, event in enumerate(part["events"]):
                onset = beat(event["startBeat"])
                if start <= onset < end:
                    origins[part["id"]].append({
                        "spanIndex": span_index,
                        "selectedStartBeat": rational(offset + onset - start),
                        "source": {"part": part["id"], "eventIndex": event_index, **event},
                    })
        offset += end - start
    for part in selected["parts"]:
        expected = [{
            "startBeat": origin["selectedStartBeat"],
            **{key: value for key, value in origin["source"].items() if key not in ("part", "eventIndex", "startBeat")},
        } for origin in origins[part["id"]]]
        if expected != part["events"]:
            raise ValueError("Selected notes do not match their complete-score origins")
    return origins


def voice_source_parts(voice):
    if ("sourcePart" in voice) == ("sourceParts" in voice):
        raise ValueError("Each voice requires either sourcePart or sourceParts: " + voice["name"])
    parts = voice["sourceParts"] if "sourceParts" in voice else [voice["sourcePart"]]
    if not isinstance(parts, list) or not parts or any(not isinstance(part, str) or not part.strip() for part in parts):
        raise ValueError("sourceParts must be a nonempty list of sourcePart IDs in voice " + voice["name"])
    if len(parts) != len(set(parts)):
        raise ValueError("sourceParts must contain distinct sourcePart IDs in voice " + voice["name"])
    return parts


def explicit_omissions(voice, source_events, origins):
    declarations = voice.get("omittedEvents", [])
    if not isinstance(declarations, list):
        raise ValueError("omittedEvents must be a list in voice " + voice["name"])
    selected_indices = {(origin["source"]["part"], origin["source"]["eventIndex"]) for origin in origins}
    reasons = {}
    for declaration in declarations:
        if not isinstance(declaration, dict):
            raise ValueError("Each omittedEvents entry must be an object in voice " + voice["name"])
        part = declaration.get("sourcePart")
        if "sourcePart" not in declaration and len(source_events) == 1:
            part = next(iter(source_events))
        if not isinstance(part, str) or part not in source_events:
            raise ValueError("Explicit omissions require an owned sourcePart in voice " + voice["name"])
        index, reason = declaration.get("sourceEventIndex"), declaration.get("reason")
        if type(index) is not int or index < 0:
            raise ValueError("sourceEventIndex must be a nonnegative integer in voice " + voice["name"])
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Explicit omissions require a nonblank reason in voice " + voice["name"])
        identity = (part, index)
        if identity in reasons:
            raise ValueError("Duplicate sourceEventIndex in voice " + voice["name"] + ": " + str(index))
        if index >= len(source_events[part]):
            raise ValueError("Omitted source event does not exist in voice " + voice["name"] + ": " + str(index))
        if identity not in selected_indices:
            raise ValueError("Omitted source event is not selected in voice " + voice["name"] + ": " + str(index))
        reasons[identity] = reason
    return reasons


def project_score(full, selected, recipe):
    voices = recipe["voices"]
    if len(voices) != 3 or len({voice["name"] for voice in voices}) != 3:
        raise ValueError("Projection requires three distinctly named voices")
    voice_parts = [voice_source_parts(voice) for voice in voices]
    mapped_ids = [part for parts in voice_parts for part in parts]
    mapped = set(mapped_ids)
    if len(mapped_ids) != len(mapped):
        raise ValueError("Projection requires distinct sourcePart ownership across voices")
    parts = {part["id"]: part["events"] for part in full["parts"]}
    omitted = recipe.get("omittedParts", {})
    if mapped & set(omitted) or mapped | set(omitted) != set(parts) or any(not isinstance(reason, str) or not reason.strip() for reason in omitted.values()):
        raise ValueError("Every source part must be mapped once or explicitly omitted with a reason")
    origins = source_origins(full, selected, recipe["spans"])
    retained, losses, shortened, output_voices = [], [], [], []
    for part, reason in omitted.items():
        losses.extend({**origin, "reason": reason} for origin in origins[part])
    for voice_index, voice in enumerate(voices):
        try:
            policy = MonophonicPolicy(voice["monophonicPolicy"])
        except ValueError:
            raise ValueError("Unsupported monophonic policy: " + str(voice["monophonicPolicy"])) from None
        try:
            overlap_policy = OverlapPolicy(voice.get("overlapPolicy", "reject-overlap"))
        except ValueError:
            raise ValueError("Unsupported overlap policy: " + str(voice["overlapPolicy"])) from None
        source_parts = voice_parts[voice_index]
        voice_origins = sorted((origin for part in source_parts for origin in origins[part]), key=lambda origin: (beat(origin["selectedStartBeat"]), origin["source"]["midi"]))
        reasons = explicit_omissions(voice, {part: parts[part] for part in source_parts}, voice_origins)
        groups = defaultdict(list)
        for origin in voice_origins:
            reason = reasons.get((origin["source"]["part"], origin["source"]["eventIndex"]))
            if reason is not None:
                losses.append({**origin, "reason": reason})
            else:
                groups[beat(origin["selectedStartBeat"])].append(origin)
        chosen = []
        for group in groups.values():
            if policy is MonophonicPolicy.REJECT_OVERLAP:
                chosen.extend(group)
            elif policy is MonophonicPolicy.HIGHEST_AT_ONSET:
                highest = max(group, key=lambda origin: origin["source"]["midi"])
                if sum(origin["source"]["midi"] == highest["source"]["midi"] for origin in group) > 1:
                    raise ValueError("Cannot reduce tied highest pitches in voice " + voice["name"])
                chosen.append(highest)
                losses.extend({**origin, "reason": "Lower chord note omitted by highest-at-onset"} for origin in group if origin is not highest)
        events = []
        for index, origin in enumerate(chosen):
            start = beat(origin["selectedStartBeat"])
            duration = beat(origin["source"]["durationBeats"])
            output_origin = {**origin, "voice": voice["name"], "voiceIndex": voice_index, "outputEventIndex": len(events)}
            if index + 1 < len(chosen):
                next_start = beat(chosen[index + 1]["selectedStartBeat"])
                if start + duration > next_start:
                    if overlap_policy is OverlapPolicy.REJECT_OVERLAP:
                        raise ValueError("Selected notes overlap in voice " + voice["name"] + "; change the passage or projection policy")
                    if next_start <= start:
                        raise ValueError("Cannot shorten simultaneous onsets in voice " + voice["name"])
                    duration = next_start - start
                    output_origin["outputDurationBeats"] = rational(duration)
                    shortened.append(output_origin)
            retained.append(output_origin)
            events.append({"startBeat": float(start), "durationBeats": float(duration), "midi": origin["source"]["midi"]})
        output_voices.append({"name": voice["name"], "instrument": voice["instrument"], "events": events})
    reduction = {
        "sourceNotes": sum(len(part["events"]) for part in selected["parts"]),
        "retainedNotes": len(retained),
        "omittedNotes": len(losses),
        "shortenedNotes": len(shortened),
        "outputEvents": len(retained),
        "voices": [{key: voice[key] for key in ("name", "sourcePart", "sourceParts", "monophonicPolicy", "overlapPolicy") if key in voice} for voice in voices],
        "omittedParts": omitted,
        "retainedEvents": retained,
        "omittedEvents": losses,
        "shortenedEvents": shortened,
        "timing": "Retained source notes keep their exact rational timing in origin records; output beats use the existing arranged-score numeric format. Only an explicit shorten-to-next-onset policy may reduce durations to preserve later source onsets; original durations remain in source records and exact output durations are recorded for shortened events. No swing transform, note extension or transposition is applied.",
        "velocity": "Preserved in common score and origin records; fixed per-voice SID envelopes",
    }
    if reduction["sourceNotes"] != reduction["retainedNotes"] + reduction["omittedNotes"]:
        raise ValueError("Projection did not account for every selected source note")
    score = {
        "title": recipe.get("title", selected["title"]),
        "composer": recipe.get("composer", selected["composer"]),
        "quarterBpm": selected["quarterBpm"],
        "timeSignature": selected["timeSignature"],
        "totalBeats": float(beat(selected["totalBeats"])),
        "tailTicks": recipe.get("tailTicks", 25),
        "volume": recipe.get("volume", 15),
        "voices": output_voices,
        "provenance": {**selected["provenance"], "arrangementRecipe": recipe.get("recipeFile", ""), "reduction": reduction},
    }
    if "sections" in recipe:
        score["sections"] = recipe["sections"]
    return score


def prepare_source(source, recipe_path, output, arrangement, candidate=None, reference=None):
    source, recipe_path, output, arrangement = Path(source), Path(recipe_path), Path(output), Path(arrangement)
    if output.exists():
        raise ValueError("Use a fresh output directory")
    if bool(candidate) != bool(reference):
        raise ValueError("Supply candidate and reference together")
    import_recipe = json.loads(recipe_path.read_text())
    if not import_recipe.get("sourceSha256"):
        raise ValueError("Import recipe must pin the source SHA-256")
    projection = json.loads(arrangement.read_text())
    projection["recipeFile"] = str(arrangement)
    if not projection.get("spans"):
        raise ValueError("Projection must select at least one source span")
    full_recipe = dict(import_recipe)
    full_recipe.pop("performance", None)
    full = import_midi(source, full_recipe)
    selected_recipe = {**full_recipe, "performance": {"sourceTotalBeats": full["totalBeats"], "spans": projection["spans"]}}
    selected = import_midi(source, selected_recipe)
    arranged = project_score(full, selected, projection)
    templates = {}
    if candidate:
        for name, path in (("candidate", candidate), ("reference", reference)):
            templates[name] = {**json.loads(Path(path).read_text()), "score": "score.json"}
    report = {
        "originalSourceSha256": full["provenance"]["sourceSha256"],
        "sourceNotes": full["provenance"]["importReport"]["sourceNotes"],
        "selectedNotes": selected["provenance"]["importReport"]["normalizedNotes"],
        "fullCommonScore": "full-common-score.json",
        "selectedCommonScore": "common-score.json",
        "selectedSpans": projection["spans"],
        "selectedTotalBeats": selected["totalBeats"],
        "selectedDurationSeconds": float(beat(selected["totalBeats"])) * 60 / selected["quarterBpm"],
        "importReport": full["provenance"]["importReport"],
        "reduction": arranged["provenance"]["reduction"],
    }
    output.mkdir(parents=True)
    shutil.copyfile(source, output / "source.mid")
    for name, value in (("full-common-score", full), ("common-score", selected), ("score", arranged), ("adaptation", report), ("import-recipe", import_recipe)):
        write_json(output / (name + ".json"), value)
    for name, template in templates.items():
        write_json(output / (name + ".json"), template)
    return report


def main():
    parser = argparse.ArgumentParser(description="Prepare a source-backed three-voice audition with explicit passage selection and note omissions")
    parser.add_argument("source", type=Path)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arrangement", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    try:
        report = prepare_source(args.source, args.recipe, args.output, args.arrangement, args.candidate, args.reference)
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))
    print(json.dumps({"output": str(args.output), "sourceNotes": report["sourceNotes"], "selectedNotes": report["selectedNotes"], "retainedNotes": report["reduction"]["retainedNotes"], "durationSeconds": report["selectedDurationSeconds"]}, sort_keys=True))


if __name__ == "__main__":
    main()
