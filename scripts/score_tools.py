from collections import Counter, defaultdict, deque
from fractions import Fraction
import hashlib


def beat(value):
    if isinstance(value, list) and len(value) == 2 and all(type(item) is int for item in value) and value[1] > 0:
        return Fraction(*value)
    if type(value) in (int, float):
        return Fraction(str(value))
    raise ValueError("A beat must be a number or an integer [numerator, positive denominator] pair")


def rational(value):
    return [value.numerator, value.denominator]


def import_midi(path, recipe):
    import mido

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if recipe.get("sourceSha256", digest) != digest:
        raise ValueError("Source SHA-256 does not match the import recipe")
    midi = mido.MidiFile(path)
    if midi.type == 2 or midi.ticks_per_beat <= 0:
        raise ValueError("Only synchronous MIDI with positive ticks per quarter is supported")
    ppq = midi.ticks_per_beat
    tracks = []
    tempo_events = []
    meter_events = []
    unmapped = Counter()
    controllers = Counter()
    end_tick = 0
    mapped = {"note_on", "note_off", "set_tempo", "time_signature", "track_name", "end_of_track"}
    for index, track in enumerate(midi.tracks):
        tick = 0
        name = "track-" + str(index)
        active = defaultdict(deque)
        notes = []
        for message in track:
            tick += message.time
            kind = message.type
            if kind not in mapped:
                unmapped[kind] += 1
                if kind == "control_change":
                    controllers[str(message.control)] += 1
            if kind == "track_name":
                name = message.name
            elif kind == "set_tempo":
                tempo_events.append((tick, message.tempo))
            elif kind == "time_signature":
                meter_events.append((tick, (message.numerator, message.denominator)))
            elif kind == "note_on" and message.velocity:
                active[(message.channel, message.note)].append((tick, message.velocity))
            elif kind == "note_off" or (kind == "note_on" and not message.velocity):
                key = (message.channel, message.note)
                if not active[key]:
                    raise ValueError("MIDI note-off has no matching note-on")
                start, velocity = active[key].popleft()
                if tick <= start:
                    raise ValueError("MIDI note duration must be positive")
                notes.append({
                    "start": Fraction(start, ppq),
                    "end": Fraction(tick, ppq),
                    "midi": message.note,
                    "velocity": velocity,
                })
        if any(active.values()):
            raise ValueError("MIDI contains an unterminated note")
        end_tick = max(end_tick, tick)
        tracks.append({
            "track": index,
            "name": name,
            "notes": sorted(notes, key=lambda note: (note["start"], note["midi"], note["end"])),
        })
    tempos = {value for tick, value in tempo_events}
    meters = {value for tick, value in meter_events}
    if not any(tick == 0 for tick, value in tempo_events):
        tempos.add(500000)
    if not any(tick == 0 for tick, value in meter_events):
        meters.add((4, 4))
    if len(tempos) > 1 or len(meters) > 1:
        raise ValueError("Common score v1 requires constant tempo and time signature; varying maps remain in the original MIDI")
    tempo = next(iter(tempos), 500000)
    time_signature = list(next(iter(meters), (4, 4)))
    source_end = Fraction(end_tick, ppq)
    performance = recipe.get("performance", {})
    total = beat(performance.get("sourceTotalBeats", rational(source_end)))
    if total < source_end:
        raise ValueError("Source total duration cannot truncate the MIDI timeline")
    spans = performance.get("spans", [{"startBeat": 0, "endBeat": rational(total)}])
    unfolded = [[] for _ in tracks]
    offset = Fraction(0)
    for span in spans:
        start, end = beat(span["startBeat"]), beat(span["endBeat"])
        if start < 0 or end <= start or end > total:
            raise ValueError("Performance span is outside the source timeline")
        for index, track in enumerate(tracks):
            for note in track["notes"]:
                if note["start"] < end and note["end"] > start:
                    if note["start"] < start or note["end"] > end:
                        raise ValueError("A MIDI note crosses a performance span boundary")
                    unfolded[index].append({
                        "startBeat": rational(offset + note["start"] - start),
                        "durationBeats": rational(note["end"] - note["start"]),
                        "midi": note["midi"],
                        "velocity": note["velocity"],
                    })
        offset += end - start
    selections = recipe.get("parts", [
        {"track": track["track"], "id": "track-" + str(track["track"])}
        for track in tracks if track["notes"]
    ])
    selected_tracks = [part["track"] for part in selections]
    if len(set(selected_tracks)) != len(selected_tracks) or any(index < 0 or index >= len(tracks) for index in selected_tracks):
        raise ValueError("Part tracks must be unique valid MIDI track indices")
    if any(track["notes"] and track["track"] not in selected_tracks for track in tracks):
        raise ValueError("All sounding MIDI tracks must be preserved in the common score")
    ids = [part["id"] for part in selections]
    if len(set(ids)) != len(ids):
        raise ValueError("Part IDs must be unique")
    provenance = dict(recipe.get("provenance", {}))
    provenance.update({
        "sourceFile": recipe.get("sourceFile", path.name),
        "sourceSha256": digest,
        "importer": "import-midi.py / common score v1",
        "performance": {"sourceTotalBeats": rational(total), "spans": spans},
        "importReport": {
            "ticksPerQuarter": ppq,
            "microsecondsPerQuarter": tempo,
            "sourceNotes": sum(len(track["notes"]) for track in tracks),
            "normalizedNotes": sum(len(notes) for notes in unfolded),
            "mappedEventTypes": sorted(mapped),
            "unmappedEventTypes": dict(sorted(unmapped.items())),
            "unmappedControllers": dict(sorted(controllers.items())),
            "unmappedFields": {
                "note_on": ["channel"],
                "note_off": ["channel", "velocity"],
                "time_signature": ["clocks_per_click", "notated_32nd_notes_per_beat"],
            },
            "notationNotEncodedByMidi": [
                "enharmonic spelling", "printed repeats and alternatives", "slurs",
                "articulation marks", "engraved dynamics", "pedal notation",
            ],
            "addedTrailingRestBeats": rational(total - source_end),
        },
    })
    score = {
        "schemaVersion": 1,
        "title": recipe.get("title", path.stem),
        "composer": recipe.get("composer", "Unknown"),
        "quarterBpm": recipe.get("quarterBpm", 60000000 / tempo),
        "timeSignature": time_signature,
        "totalBeats": rational(offset),
        "parts": [{
            "id": part["id"],
            "name": tracks[part["track"]]["name"],
            "events": unfolded[part["track"]],
        } for part in selections],
        "provenance": provenance,
    }
    if "work" in recipe:
        score["work"] = recipe["work"]
    return score


def arrange_score(score, recipe):
    if score.get("schemaVersion") != 1:
        raise ValueError("Unsupported common score schema version")
    ids = [part["id"] for part in score["parts"]]
    if len(set(ids)) != len(ids):
        raise ValueError("Common score part IDs must be unique")
    melody_id, accompaniment_id = recipe["melodyPart"], recipe["accompanimentPart"]
    if melody_id == accompaniment_id or set(ids) != {melody_id, accompaniment_id}:
        raise ValueError("This arrangement policy requires exactly the named melody and accompaniment parts")
    instruments = recipe["instruments"]
    if len(instruments) != 3:
        raise ValueError("A SID arrangement requires exactly three instruments")
    priority = recipe.get("harmonyPriority", ["accompaniment", "melody"])
    if sorted(priority) != ["accompaniment", "melody"]:
        raise ValueError("Harmony priority must name accompaniment and melody exactly once")
    total = beat(score["totalBeats"])
    notes = []
    for part in score["parts"]:
        for event in part["events"]:
            start, duration = beat(event["startBeat"]), beat(event["durationBeats"])
            if start < 0 or duration <= 0 or start + duration > total:
                raise ValueError("Note start and duration must fit the common score timeline")
            if type(event["midi"]) is not int or not 0 <= event["midi"] <= 127:
                raise ValueError("A note pitch must be a MIDI integer from 0 to 127")
            notes.append({
                "id": len(notes),
                "part": part["id"],
                "start": start,
                "end": start + duration,
                "midi": event["midi"],
            })
    bass_policy = recipe["bass"]
    measure = beat(bass_policy["measureBeats"])
    measure_start = beat(bass_policy.get("firstMeasureBeat", 0))
    if measure <= 0:
        raise ValueError("Measure duration must be positive")
    accompaniment_onsets = defaultdict(list)
    for note in notes:
        if note["part"] == accompaniment_id:
            accompaniment_onsets[note["start"]].append(note)
    bass_ids = set()
    for start, group in accompaniment_onsets.items():
        lowest = min(group, key=lambda note: (note["midi"], note["id"]))
        on_measure_start = start >= measure_start and (start - measure_start) % measure == 0
        if lowest["midi"] < bass_policy["belowMidi"] or (bass_policy.get("onMeasureStart", False) and on_measure_start):
            bass_ids.add(lowest["id"])
    starts = defaultdict(list)
    ends = defaultdict(list)
    for note in notes:
        starts[note["start"]].append(note)
        ends[note["end"]].append(note)
    boundaries = sorted(set(starts) | set(ends))
    active = {}
    voices = [[], [], []]
    played = Counter()
    for start, end in zip(boundaries, boundaries[1:]):
        for note in ends[start]:
            active.pop(note["id"], None)
        for note in starts[start]:
            active[note["id"]] = note
        melody = [note for note in active.values() if note["part"] == melody_id]
        lead = max(
            melody,
            key=lambda note: (note["midi"], note["start"], note["id"]),
            default=None,
        )
        bass = min(
            (note for note in active.values() if note["id"] in bass_ids),
            key=lambda note: (note["midi"], -note["start"], note["id"]),
            default=None,
        )
        reserved = {note["id"] for note in (lead, bass) if note is not None}
        remaining = [note for note in active.values() if note["id"] not in reserved]
        harmony = min(
            remaining,
            key=lambda note: (
                priority.index("melody" if note["part"] == melody_id else "accompaniment"),
                -note["midi"], -note["start"], note["id"],
            ),
            default=None,
        )
        for index, note in enumerate((lead, bass, harmony)):
            if note is None:
                continue
            played[note["id"]] += end - start
            events = voices[index]
            if events and events[-1]["id"] == note["id"] and events[-1]["end"] == start:
                events[-1]["end"] = end
            else:
                events.append({"id": note["id"], "start": start, "end": end, "midi": note["midi"]})
    omitted = [note for note in notes if not played[note["id"]]]
    shortened = [note for note in notes if 0 < played[note["id"]] < note["end"] - note["start"]]
    provenance = dict(score.get("provenance", {}))
    provenance["arrangementRecipe"] = recipe.get("recipeFile", "")
    def source_event(note):
        return {
            "part": note["part"],
            "startBeat": rational(note["start"]),
            "durationBeats": rational(note["end"] - note["start"]),
            "midi": note["midi"],
            "retainedBeats": rational(Fraction(played[note["id"]])),
        }

    provenance["reduction"] = {
        "sourceNotes": len(notes),
        "retainedNotes": len(notes) - len(omitted),
        "omittedNotes": len(omitted),
        "shortenedNotes": len(shortened),
        "outputEvents": sum(len(events) for events in voices),
        "omittedPitches": dict(sorted(
            Counter(str(note["midi"]) for note in omitted).items(),
            key=lambda item: int(item[0]),
        )),
        "omittedEvents": [source_event(note) for note in omitted],
        "shortenedEvents": [source_event(note) for note in shortened],
        "velocity": "preserved in common score; fixed per-voice SID envelopes",
        "sustainPedal": "MIDI controllers remain in the original source; note-off timing only",
        "bassDurations": "preserved when selected; never extended",
    }
    arranged = {
        "title": recipe.get("title", score["title"]),
        "composer": recipe.get("composer", score["composer"]),
        "quarterBpm": recipe.get("quarterBpm", score["quarterBpm"]),
        "timeSignature": score["timeSignature"],
        "totalBeats": float(total),
        "tailTicks": recipe.get("tailTicks", 25),
        "volume": recipe.get("volume", 15),
        "voices": [{
            "name": name,
            "instrument": instruments[index],
            "events": [{
                "startBeat": float(event["start"]),
                "durationBeats": float(event["end"] - event["start"]),
                "midi": event["midi"],
            } for event in voices[index]],
        } for index, name in enumerate(("melody", "bass", "harmony"))],
        "provenance": provenance,
    }
    if "sections" in recipe:
        arranged["sections"] = recipe["sections"]
    return arranged
