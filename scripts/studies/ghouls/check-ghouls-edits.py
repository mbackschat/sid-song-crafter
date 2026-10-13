"""Compare complete numeric SID stores for five editable, source-backed changes."""

import argparse
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from ghouls_player import GhoulsPlayer, compute_player
from psid_audit import audit_psid

SOURCE_SHA = "265644a66d6043e6fe5ddeeb0d87e9b4269386a73c3e26457c8d96ce3d042df4"
EDIT_CALLS = {"duration": 224, "note": 224, "repeat": 944, "gate-time": 224, "rest": 224}


def edit_cases(description):
    player = GhoulsPlayer(description)
    operations = []
    original_operation = player.operation

    def observe(voice, operation, state):
        operations.append(dict(operation, voice=voice))
        return original_operation(voice, operation, state)

    player.operation = observe
    player.play(0)
    first = next(op for op in operations if op["kind"] == "note" and op["voice"] == 0)
    repeat = next(op for op in operations if op.get("command") == "repeat-start")
    gate = next(op for op in operations if op.get("command") == "gate-time")
    cases = []
    for name in ("duration", "note", "repeat", "gate-time", "rest"):
        changed = deepcopy(description)
        selected = repeat if name == "repeat" else gate if name == "gate-time" else first
        node = changed["program"]["nodes"][selected["node"]]["variants"][selected["mode"]]
        metadata = changed["sourceEvidence"]["nodes"][selected["node"]][selected["mode"]]
        if name == "duration":
            before, after, path = node["duration"], node["duration"] + 1, ["duration"]
            node["duration"] = after
            address = metadata["reads"][1]["address"]
        elif name == "note":
            before, after, path = node["rawNote"], node["rawNote"] - 1, ["rawNote"]
            node["rawNote"] = after
            address = metadata["address"]
        elif name == "repeat":
            before, after, path = node["fields"]["count"], node["fields"]["count"] - 1, ["fields", "count"]
            node["fields"]["count"] = after
            address = metadata["reads"][1]["address"]
        elif name == "gate-time":
            before, after, path = node["fields"]["gateTime"], 2, ["fields", "gateTime"]
            node["fields"]["gateTime"] = after
            address = metadata["reads"][1]["address"]
        else:
            before, after, path = node["rawNote"], 0, ["kind", "rawNote"]
            node["kind"] = "rest"
            del node["rawNote"]
            address = metadata["address"]
        cases.append(dict(name=name, calls=EDIT_CALLS[name], description=changed,
            mutation=dict(node=selected["node"], mode=selected["mode"], path=path,
                before=before, after=after),
            ramEdits=[dict(address=address, expectedOriginal=before, value=after)]))
    return cases


def native_score(data, calls, edits):
    """Execute the unchanged SID with explicit private initialized-RAM edits."""
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA:
        raise ValueError("Pinned source fingerprint changed")
    reads, bodies, gates = [], [], []
    ranges = ((0x6356, 0x6421), (0x6543, 0x6610), (0x6732, 0x67ff), (0x6858, 0x6cb7))
    dispatch = (0x6362, 0x654f, 0x673e)
    gate_stores = (0x6348, 0x6535, 0x6724)
    edited = False

    def observe(cpu, memory):
        nonlocal edited
        if memory.phase != "play":
            return
        ram, pc, call = memory.data, cpu.pc, memory.tick
        if pc == 0x6234 and call == 0:
            for row in edits:
                if ram[row["address"]] != row["expectedOriginal"]:
                    raise ValueError("RAM intervention no longer matches its source byte")
                ram[row["address"]] = row["value"]
            edited = True
        if pc in gate_stores:
            voice = gate_stores.index(pc)
            gates.append(dict(call=call, voice=voice, address=0xd404 + 7 * voice, value=cpu.a))
        if any(first <= pc < end for first, end in ranges) and ram[pc] == 0xb1 and ram[pc + 1] in (0x21, 0x23, 0x25):
            voice = (ram[pc + 1] - 0x21) // 2
            pointer = ram[ram[pc + 1]] | ram[ram[pc + 1] + 1] << 8
            target = (pointer + cpu.y) & 65535
            reads.append(dict(kind="dispatchRead" if pc in dispatch else "streamOperandRead",
                call=call, voice=voice, address=target, value=ram[target],
                callDepth=ram[0x69 + voice], repeatRemaining=ram[0x2d + voice]))
        if pc == 0x6857 and cpu.sp == 0xfd:
            word = lambda address: ram[address] | ram[address + 1] << 8
            bodies.append(dict(call=call, streamPointers=[word(0x21 + 2 * v) for v in range(3)],
                durationRemaining=ram[0x27:0x2a], repeatRemaining=ram[0x2d:0x30],
                repeatPointers=[word(0x30 + 2 * v) for v in range(3)], callDepth=ram[0x69:0x6c],
                enableFlags=ram[0x7b:0x7e], transpose=ram[0x4e:0x51]))

    report, writes = audit_psid(data, calls, observer=observe, profile="pal-banked", subtune=1)
    if not edited or len(bodies) != calls:
        raise ValueError("Native intervention did not cover every requested call")
    return dict(reads=reads, bodies=bodies, gates=gates, audit=report, writes=writes)


def ordered(writes):
    return [(row["phase"], row["tick"], row["address"], row["value"]) for row in writes]


def publish(directory, name, value, compressed=False):
    raw = (json.dumps(value, separators=(",", ":") if compressed else None,
        indent=None if compressed else 2) + "\n").encode()
    stored = gzip.compress(raw, mtime=0) if compressed else raw
    with (directory / name).open("xb") as output:
        output.write(stored)
    return dict(bytes=len(stored), sha256=hashlib.sha256(stored).hexdigest(),
        decodedBytes=len(raw), decodedSha256=hashlib.sha256(raw).hexdigest())


def verify(description, data, output):
    if output.exists() or output.is_symlink() or not output.resolve().is_relative_to(ROOT / "build"):
        raise ValueError("Choose a fresh output directory below build/")
    if any(parent.is_symlink() for parent in output.parents):
        raise ValueError("Output must not cross symlinks")
    cases = edit_cases(description)
    baselines = {calls: ordered(compute_player(description, calls=calls)["writes"])
        for calls in set(EDIT_CALLS.values())}
    output.mkdir(parents=True)
    files, comparisons = {}, []
    for case in cases:
        calls = case["calls"]
        native = native_score(data, calls, case["ramEdits"])
        model = compute_player(case["description"], calls=calls)
        expected, actual = ordered(native["writes"]), ordered(model["writes"])
        first_difference = next((dict(index=index, native=left, model=right)
            for index, (left, right) in enumerate(zip(expected, actual)) if left != right), None)
        matched = expected == actual
        changed = actual != baselines[calls]
        name = case["name"]
        for suffix, value, compressed in (("native.writes.json.gz", native["writes"], True),
                ("model.writes.json.gz", model["writes"], True),
                ("native.score.json.gz", {key: native[key] for key in ("reads", "bodies", "gates")}, True),
                ("native.audit.json", native["audit"], False)):
            filename = name + "." + suffix
            files[filename] = publish(output, filename, value, compressed)
        comparisons.append(dict(name=name, passed=matched and changed, calls=calls,
            nativeStores=len(expected), modelStores=len(actual), completeOrderedStoresMatch=matched,
            differsFromPrimary=changed, firstDifference=first_difference,
            mutation=case["mutation"], ramEdits=case["ramEdits"]))
    files["edits.json"] = publish(output, "edits.json", comparisons)
    return comparisons, files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--description", type=Path, default=ROOT / "songs/ghouls.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = ROOT / ".local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid"
    data = source.read_bytes()
    description = json.loads(args.description.read_text())
    comparisons, files = verify(description, data, args.output)
    unchanged = source.read_bytes() == data
    passed = unchanged and all(row["passed"] for row in comparisons)
    tools = ("ghouls_score.py", "ghouls_programs.py", "ghouls_player.py", "psid_audit.py", "psid_profile.py", "sid_audit_host.py", "verify_player.py")
    receipt = dict(passed=passed, sourceSha256=SOURCE_SHA, selectedSubtune=1,
        sourceBytesUnchanged=unchanged, callsByEdit=EDIT_CALLS, edits=len(comparisons),
        descriptionSha256=hashlib.sha256(args.description.read_bytes()).hexdigest(),
        verifierSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        tools={name: hashlib.sha256((ROOT / "scripts" / name).read_bytes()).hexdigest() for name in tools},
        completeOrderedStoreComparisons=comparisons, outputHashes=files,
        scope="Five symbolic/numeric description edits match complete initialized source CPU ordered SID stores over the retained per-case horizons. Private RAM interventions preserve the original SID bytes; the numeric player reads only editable data.",
        excluded="CPU-cycle identity, compiled-player/VICE execution, SID internals, rendered audio and listening acceptance.")
    publish(args.output, "receipt.json", receipt)
    if not passed:
        raise ValueError(f"Edited store comparison failed; diagnostics retained in {args.output}")
    print(json.dumps(dict(passed=True, edits=len(comparisons), callsByEdit=EDIT_CALLS,
        matchedStores={row["name"]: row["nativeStores"] for row in comparisons}, output=str(args.output))))


if __name__ == "__main__":
    main()
