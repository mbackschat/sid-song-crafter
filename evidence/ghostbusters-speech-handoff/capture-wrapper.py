"""Observe the first speech producer/consumer handoff in one bounded VICE run."""

import argparse
from contextlib import contextmanager
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('ghostbusters_handoff_machine', Path(__file__).with_name('probe-machine.py'))
machine = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(machine)

EXEC_POINTS = (0xf0f5, 0xf0fb, 0xf101, 0xf103, 0xf08e, 0xf090,
               0xf092, 0xf095, 0xf09f, 0xf0a2)
EXTRA_CHECKPOINTS = [('trace', 'exec', pc, None) for pc in EXEC_POINTS] + [
    ('trace', 'store', 0xfd, 0xff), ('trace', 'store', 0xf085, None), ('trace', 'store', 0xf0a6, None)]
MEMORY_RANGES = ((0xfd, 3), (0xf085, 1), (0xf0a6, 1), (0xf4db, 2))
RAM_COMMAND = '; '.join(f'm ${address:04x} ${address + length - 1:04x}' for address, length in MEMORY_RANGES)
STATE_FIELDS = dict(forwardCount=0xfd, reverseCount=0xfe, gapCount=0xff,
    forwardPointer=0xf085, reversePointer=0xf0a6, currentBase=0xf4db, length=0xf4dc)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fingerprint(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


@contextmanager
def extended_monitor():
    checkpoints, terminal, original_commands = machine.CHECKPOINTS, machine.TERMINAL_CHECKPOINT, machine.monitor_commands
    machine.CHECKPOINTS = list(checkpoints) + EXTRA_CHECKPOINTS
    machine.TERMINAL_CHECKPOINT = len(machine.CHECKPOINTS) + 1
    selected = {index for index, (_, operation, address, _) in enumerate(machine.CHECKPOINTS, 1)
        if index > len(checkpoints) or operation == 'exec' and address in (0xf083, 0xf0a4)
        or index == machine.NMI_VECTOR_CHECKPOINT}

    def commands(payload, host, refreshes):
        lines = original_commands(payload, host, refreshes).splitlines()
        first_run = lines.index('g')
        # VICE 3.9 vice.texi "Checkpoint commands" permits read-only commands
        # at trace hits; RAM snapshots settle RMW values without patching code.
        lines[first_run:first_run] = [f'command {index} "{RAM_COMMAND}"' for index in sorted(selected)]
        return '\n'.join(lines) + '\n'

    machine.monitor_commands = commands
    try:
        yield selected
    finally:
        machine.CHECKPOINTS, machine.TERMINAL_CHECKPOINT, machine.monitor_commands = checkpoints, terminal, original_commands


def parse_snapshots(log, rows, selected):
    cursor, captured, pending = -1, [], {}

    def finish():
        if cursor >= 0 and rows[cursor]['checkpoint'] in selected:
            require(set(pending) == set(STATE_FIELDS.values()), f'Missing handoff RAM snapshot at row {cursor}')
            row = deepcopy(rows[cursor])
            row['traceRow'] = cursor
            row['state'] = {name: pending[address] for name, address in STATE_FIELDS.items()}
            captured.append(row)

    for line in log.splitlines():
        if machine.HEADER.fullmatch(line):
            finish()
            cursor += 1
            pending = {}
            require(cursor < len(rows), 'Snapshot trace has too many checkpoint headers')
        elif cursor >= 0 and rows[cursor]['checkpoint'] in selected:
            for address, length in MEMORY_RANGES:
                match = re.match(rf'^>C:{address:04x}\s+' + r'\s+'.join([r'([0-9a-f]{2})'] * length) + r'(?:\s|$)', line, re.IGNORECASE)
                if match:
                    for offset, value in enumerate(match.groups()):
                        require(address + offset not in pending, 'Repeated handoff RAM byte')
                        pending[address + offset] = int(value, 16)
    finish()
    require(cursor + 1 == len(rows), 'Snapshot trace checkpoint count differs')
    return captured


def annotate_commands(observed, rows):
    markers = [(index, row) for index, row in enumerate(rows)
        if row['operation'] == 'exec' and row['pc'] in (0x9097, 0x93e2)]
    require([row['a'] for _, row in markers if row['pc'] == 0x9097] == [1, 3], 'Speech command markers differ')
    lookup = {row['traceRow']: row for row in observed}
    for (first, command), (last, _) in zip(markers, markers[1:]):
        if command['pc'] != 0x9097:
            continue
        nmi = -1
        for index in range(first + 1, last):
            row = rows[index]
            if row['operation'] == 'exec' and row['pc'] in machine.NMI_ENTRIES:
                nmi += 1
            if index in lookup:
                lookup[index]['command'], lookup[index]['nmiIndex'] = command['a'], nmi
    return [row for row in observed if 'command' in row]


def find_lost_decrements(rows):
    proofs = []
    for index, publication in enumerate(rows):
        if not (publication['operation'] == 'store' and publication['pc'] == 0xf0f5
                and publication['address'] == 0xfffa and publication['value'] == 0x83):
            continue
        later = rows[index + 1:]
        reset_index = next((i for i, row in enumerate(later) if row['operation'] == 'store'
            and row['pc'] == 0xf101 and row['address'] == 0xfd), None)
        require(reset_index is not None, 'Published forward handler lacks observed counter initialization')
        reset, window = later[reset_index], later[:reset_index]
        nested = [row for row in window if row['operation'] == 'exec' and row['pc'] == 0xf083]
        if not nested:
            continue
        require(len(nested) == 1, 'Counter handoff has multiple nested entries outside this focused proof')
        entry = nested[0]
        base = entry['state']['forwardPointer']
        length = reset['value']
        require(entry['command'] == reset['command'] == publication['command'], 'Handoff crosses commands')
        require(entry['sp'] == publication['sp'] - 3 and reset['sp'] == publication['sp'],
            'Observed stack does not prove return to the interrupted outer handler')
        pointer = next((row for row in window if row['operation'] == 'store' and row['pc'] == 0xf0fb
            and row['address'] == 0xf085), None)
        decrement = next((row for row in window if row['operation'] == 'store' and row['pc'] == 0xf08e
            and row['address'] == 0xfd), None)
        increment = next((row for row in window if row['operation'] == 'store' and row['pc'] == 0xf092
            and row['address'] == 0xf085), None)
        require(pointer is not None and decrement is not None and increment is not None, 'Incomplete nested counter/pointer observations')
        require(publication['monitorCycle'] < pointer['monitorCycle'] < entry['monitorCycle']
            < decrement['monitorCycle'] < increment['monitorCycle'] < reset['monitorCycle'], 'Handoff instruction order differs')
        require(publication['state']['forwardCount'] == entry['state']['forwardCount'] == 0
            and decrement['state']['forwardCount'] == 255
            and reset['state']['forwardCount'] == length, 'Lost-decrement counter values differ')
        require(pointer['value'] == pointer['state']['forwardPointer'] == base
            and increment['state']['forwardPointer'] == reset['state']['forwardPointer'] == (base + 1) & 255,
            'Nested pointer increment was not preserved across counter initialization')
        handoff = next((row for row in later[reset_index + 1:] if row['operation'] == 'store'
            and row['pc'] == 0xf09f and row['address'] == 0xf0a6), None)
        require(handoff is not None and handoff['command'] == entry['command'], 'Missing observed reverse pointer handoff')
        require(handoff['value'] == handoff['state']['reversePointer'] == handoff['state']['forwardPointer'] == (base + length) & 255,
            'Reverse handoff does not include the nested forward increment')
        require(handoff['state']['forwardCount'] == 0 and handoff['state']['reverseCount'] == length,
            'Reverse handoff counters differ')
        proofs.append(dict(command=entry['command'], nestedNmiIndex=entry['nmiIndex'],
            length=length, forwardCounterValues=[0, 255, length], forwardPointerValues=[base, (base + 1) & 255, handoff['value']],
            reverseStartPointer=handoff['value'], serializedReverseStartPointer=(base + length - 1) & 255,
            vectorPublicationCycle=publication['monitorCycle'], nestedEntryCycle=entry['monitorCycle'],
            counterResetCycle=reset['monitorCycle'], reverseHandoffCycle=handoff['monitorCycle'],
            outerStackPointer=publication['sp'], nestedStackPointer=entry['sp'],
            observationRows={name: row.get('traceRow') for name, row in
                (('publication', publication), ('pointerSetup', pointer), ('nestedEntry', entry),
                 ('decrement', decrement), ('increment', increment), ('counterReset', reset), ('reverseHandoff', handoff))}))
    return proofs


def dependencies(source, vice):
    paths = {Path(__file__).resolve(), Path(machine.__file__).resolve(), Path(machine.trace_helpers.__file__).resolve(), source.resolve(), vice.resolve()}
    for module in tuple(sys.modules.values()):
        path = getattr(module, '__file__', None)
        if path:
            path = Path(path).resolve()
            if path.is_relative_to(ROOT) and path.is_file():
                paths.add(path)
    paths.update(path for path in (ROOT / '.tools/vice-headless-3.9/source/data/C64').rglob('*') if path.is_file())
    return {str(path): fingerprint(path) for path in sorted(paths)}


def probe(source, output, vice):
    output = machine.managed_output(output, ROOT)
    require(not output.exists(), 'Choose a fresh handoff output directory')
    original = source.read_bytes()
    machine.admit_source(original)
    before = dependencies(source, vice)
    with extended_monitor() as selected:
        captured = machine.probe(source, output / 'capture', vice, 2)
        log = gzip.decompress((output / 'capture/monitor.log.gz').read_bytes()).decode('latin-1')
        rows = machine.parse_records(log)
        observed = annotate_commands(parse_snapshots(log, rows, selected), rows)
    proofs = find_lost_decrements(observed)
    require(proofs and proofs[0]['command'] == 1 and proofs[0]['nestedNmiIndex'] == 321
        and proofs[0]['forwardCounterValues'] == [0, 255, 16]
        and proofs[0]['forwardPointerValues'] == [96, 97, 112], 'Expected first command-1 counter race was not observed')
    require(source.read_bytes() == original, 'Original source changed')
    require(dependencies(source, vice) == before, 'Handoff dependencies changed during capture')
    private = output / 'handoff-observations.json.gz'
    with gzip.open(private, 'wt') as file:
        json.dump(observed, file, separators=(',', ':'))
    summary = dict(schemaVersion=1, sourceSha256=machine.SOURCE_SHA,
        evidence='Executed NTSC VICE checkpoint order and RAM snapshots, including nested counter initialization.',
        focusedCapture=dict(completedPostIdleMusicBodies=2, initializedSeconds=captured['capture']['initializedSeconds'],
            nmiEntries=captured['speech']['nmiEntryCount'], speechCommands=captured['speech']['verifiedOpeningCommands']),
        extension=dict(baseProbe='scripts/studies/ghostbusters/probe-machine.py', extraCheckpoints=EXTRA_CHECKPOINTS,
            snapshotRanges=MEMORY_RANGES, snapshotCount=len(observed), sourcePatched=False),
        provenLostDecrements=proofs, independentlyCorroboratedOccurrences=len(proofs),
        dependencies=list(before.values()), privateArtifacts={
            'handoff-observations.json.gz': fingerprint(private),
            'capture/verification.json': fingerprint(output / 'capture/verification.json')},
        recommendation='Source-matching speech needs an interruptible producer/consumer schedule: handler publication, counter setup, pointer traversal and buffer work are not atomic. Decoder parameters plus one serialized output per tick do not reproduce this executed handoff. Preserve the existing serialized decoder proof; an atomic native sampler is an explicitly serialized timing adaptation until independently verified against machine events.',
        limitations='One unchanged original-source NTSC KERNAL-READY capture with two completed post-idle music bodies. Trace RAM peeks are read-only. Exec checkpoints precede instructions and store snapshots follow accesses; no exact SID bus timestamps, whole-machine/renderer state, PCM identity or explanation of all later speech mismatches. Full amplitude traces/payload/monitor logs remain private under build; only this aggregate summary is suitable for public retention.')
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/research/ghostbusters/Ghostbusters.sid')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/ghostbusters-speech-handoff')
    parser.add_argument('--vice', type=Path, default=ROOT / '.tools/vice-headless-3.9/build/src/x64sc')
    args = parser.parse_args()
    result = probe(args.source.resolve(), args.output.resolve(), args.vice.resolve())
    print(json.dumps(dict(summary=str(args.output.resolve() / 'summary.json'),
        provenLostDecrements=len(result['provenLostDecrements']), first=result['provenLostDecrements'][0]), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Ghostbusters speech handoff: {error}')

