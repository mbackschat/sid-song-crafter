"""Run an editable symbolic Ghouls score without source code or native addresses."""

from dataclasses import asdict, dataclass, field, replace
from enum import Enum


class ScoreCommand(str, Enum):
    PULSE_PARAMETERS = "pulse-parameters"
    REPEAT_END = "repeat-end"
    REPEAT_START = "repeat-start"
    REST_PARAMETERS = "rest-parameters"
    DURATION_OVERRIDE = "duration-override"
    SID_STORE_LIST = "sid-store-list"
    DISABLE_VOICE = "disable-voice"
    FILTER_PARAMETERS = "filter-parameters"
    FILTER_OWNER = "filter-owner"
    CALL = "call"
    RETURN = "return"
    TRANSPOSE = "transpose"
    WAVEFORM = "waveform"
    FREQUENCY_MOTION = "frequency-motion"
    ONSET_PARAMETERS = "onset-parameters"
    GATE_TIME = "gate-time"
    NOTE_MOTION = "note-motion"
    GLIDE_RATE = "glide-rate"


COMMAND_FIELDS = {
    ScoreCommand.PULSE_PARAMETERS: ("pulseStep", "pulseDefaultLow", "pulseDefaultHigh"),
    ScoreCommand.REPEAT_END: (), ScoreCommand.REPEAT_START: ("count",),
    ScoreCommand.REST_PARAMETERS: ("restReload",),
    ScoreCommand.DURATION_OVERRIDE: ("durationOverride",),
    ScoreCommand.SID_STORE_LIST: ("stores",), ScoreCommand.DISABLE_VOICE: (),
    ScoreCommand.FILTER_PARAMETERS: ("filterStep", "filterRestartPhase", "filterDefaultLow", "filterDefaultHigh", "filterLowerLow", "filterLowerHigh", "filterUpperLow", "filterUpperHigh"),
    ScoreCommand.FILTER_OWNER: (), ScoreCommand.CALL: (), ScoreCommand.RETURN: (),
    ScoreCommand.TRANSPOSE: ("transpose",), ScoreCommand.WAVEFORM: ("waveform",),
    ScoreCommand.FREQUENCY_MOTION: ("frequencyDelayReload", "frequencyStep", "frequencyHalfReload", "frequencyDirectionDefault"),
    ScoreCommand.ONSET_PARAMETERS: ("onsetDelay", "onsetControl", "onsetFrequencyLow", "onsetFrequencyHigh"),
    ScoreCommand.GATE_TIME: ("gateTime",),
    ScoreCommand.NOTE_MOTION: ("noteStep", "notePositiveDuration", "noteNegativeDuration"),
    ScoreCommand.GLIDE_RATE: ("glideRate",),
}


def byte(value, name):
    if type(value) is not int or not 0 <= value <= 255:
        raise ValueError(f"{name} must be an unsigned byte")
    return value


@dataclass
class ScoreVoice:
    cursor: str
    duration_remaining: int = 1
    repeat_remaining: int = 0
    repeat_cursor: str = None
    stack: list = field(default_factory=list)
    enabled: int = 255
    duration_override: int = 0


def validate_program(program):
    nodes = program.get("nodes") if isinstance(program, dict) else None
    if not isinstance(nodes, dict) or not nodes:
        raise ValueError("program.nodes must be a nonempty symbolic graph")

    def link(node, name):
        value = node.get(name)
        if not isinstance(value, str) or value not in nodes:
            raise ValueError(f"Invalid symbolic {name} link: {value!r}")

    for node_id, wrapper in nodes.items():
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("Graph node IDs must be nonempty strings")
        variants = wrapper.get("variants") if isinstance(wrapper, dict) else None
        if not isinstance(variants, dict) or not variants or set(variants) - {"stream", "override"}:
            raise ValueError(f"Invalid grammar variants for {node_id}")
        for mode, node in variants.items():
            if not isinstance(node, dict):
                raise ValueError(f"Invalid graph operation in {node_id}")
            kind = node.get("kind")
            if kind in ("note", "rest"):
                if kind == "note" and not 1 <= byte(node.get("rawNote"), "rawNote") <= 127:
                    raise ValueError("rawNote must be in 1..127")
                if mode == "stream":
                    byte(node.get("duration"), "duration")
                elif "duration" in node:
                    raise ValueError("Override variants take their duration from live score state")
                link(node, "next")
                continue
            if kind != "command":
                raise ValueError(f"Unknown graph operation: {kind!r}")
            try:
                command = ScoreCommand(node.get("command"))
            except ValueError as error:
                raise ValueError(f"Unknown score command in {node_id}") from error
            fields = node.get("fields")
            if not isinstance(fields, dict) or set(fields) != set(COMMAND_FIELDS[command]):
                raise ValueError(f"Invalid fields for {command.value}")
            if command == ScoreCommand.SID_STORE_LIST:
                stores = fields["stores"]
                if not isinstance(stores, list) or not stores:
                    raise ValueError("SID-store list must contain at least one store")
                for store in stores:
                    if not isinstance(store, dict) or set(store) != {"address", "value"}:
                        raise ValueError("SID store requires address/value")
                    if type(store["address"]) is not int or not 0xd400 <= store["address"] <= 0xd41f:
                        raise ValueError("SID store must target the canonical SID window")
                    byte(store["value"], "SID value")
            else:
                for name, value in fields.items():
                    byte(value, name)
            if command not in (ScoreCommand.RETURN, ScoreCommand.DISABLE_VOICE):
                link(node, "next")
            if command == ScoreCommand.CALL:
                link(node, "target")
    return nodes


class ScoreRuntime:
    """Advance score state while callbacks apply each operation to live sound state.

    Continuing sound runs before begin_voice. The callback receives
    (voice, operation, sound_state) and returns the resulting sound dataclass,
    preserving same-call setter order. Only symbolic score state is retained here.
    """

    def __init__(self, description):
        if description.get("format") != "ghouls-composition-v1":
            raise ValueError("Unsupported Ghouls composition format")
        self.nodes = validate_program(description.get("program"))
        initial = description.get("voices")
        if not isinstance(initial, list) or len(initial) != 3:
            raise ValueError("Exactly three score voices are required")
        self.voices = []
        for row in initial:
            try:
                voice = ScoreVoice(**row)
            except (TypeError, ValueError) as error:
                raise ValueError("Invalid initial score voice") from error
            voice.stack = list(voice.stack)
            for name in ("duration_remaining", "repeat_remaining", "enabled", "duration_override"):
                byte(getattr(voice, name), name)
            if voice.cursor not in self.nodes or voice.repeat_cursor is not None and voice.repeat_cursor not in self.nodes:
                raise ValueError("Invalid initial score cursor")
            if any(cursor not in self.nodes for cursor in voice.stack):
                raise ValueError("Invalid initial score return stack")
            self.voices.append(voice)

    def snapshot(self):
        return [asdict(voice) for voice in self.voices]

    def begin_voice(self, voice, call, sound_state, apply_operation):
        if type(voice) is not int or not 0 <= voice < 3:
            raise ValueError("Voice index must be in 0..2")
        current = self.voices[voice]
        if current.enabled < 128:
            return sound_state
        current.duration_remaining = (current.duration_remaining - 1) & 255
        rest = sound_state.rest_remaining
        if current.duration_remaining == sound_state.gate_time or rest == 0:
            sound_state = apply_operation(voice, dict(kind="gate", call=call,
                address=0xd404 + 7 * voice, value=sound_state.waveform & 254), sound_state)
            rest = (rest + 1) & 255
        sound_state = replace(sound_state, rest_remaining=(rest - 1) & 255)
        if current.duration_remaining:
            return sound_state
        for _ in range(256):
            mode = "override" if current.duration_override else "stream"
            node_id = current.cursor
            try:
                node = self.nodes[node_id]["variants"][mode]
            except KeyError as error:
                raise ValueError(f"Node {node_id!r} lacks the {mode} grammar variant") from error
            operation = dict(kind=node["kind"], node=node_id, mode=mode, call=call,
                callDepth=len(current.stack), repeatRemaining=current.repeat_remaining)
            if node["kind"] in ("note", "rest"):
                duration = current.duration_override or node["duration"]
                current.duration_remaining = duration
                current.cursor = node["next"]
                operation["duration"] = duration
                if node["kind"] == "note":
                    operation.update(rawNote=node["rawNote"], transpose=sound_state.transpose)
                return apply_operation(voice, operation, sound_state)
            command = ScoreCommand(node["command"])
            fields = node["fields"]
            operation.update(command=command.value, fields=dict(fields))
            if command == ScoreCommand.REPEAT_START:
                current.repeat_remaining = fields["count"]
                current.repeat_cursor = node["next"]
                current.cursor = node["next"]
            elif command == ScoreCommand.REPEAT_END:
                current.repeat_remaining = (current.repeat_remaining - 1) & 255
                if current.repeat_remaining and current.repeat_cursor is None:
                    raise ValueError("Repeat end has no saved repeat target")
                current.cursor = current.repeat_cursor if current.repeat_remaining else node["next"]
            elif command == ScoreCommand.CALL:
                current.stack.append(node["next"])
                current.cursor = node["target"]
                operation["target"] = node["target"]
            elif command == ScoreCommand.RETURN:
                if not current.stack:
                    raise ValueError("Score return has no saved caller")
                current.cursor = current.stack.pop()
            elif command == ScoreCommand.DISABLE_VOICE:
                current.enabled = (current.enabled + 1) & 255
                return apply_operation(voice, operation, sound_state)
            else:
                if command == ScoreCommand.DURATION_OVERRIDE:
                    current.duration_override = fields["durationOverride"]
                current.cursor = node["next"]
            sound_state = apply_operation(voice, operation, sound_state)
        raise ValueError("Same-call score command budget exceeded")
