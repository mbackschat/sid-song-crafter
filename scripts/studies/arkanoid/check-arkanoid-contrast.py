"""Execute a bounded Galway contrast in Arkanoid's own IRQ/foreground host."""

import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from sid_intake import inspect_sid

SOURCE_URL = 'https://www.hvsc.de/download/C64Music/MUSICIANS/G/Galway_Martin/Arkanoid.sid'
SOURCE_SHA = '9a576463b6d9e46f35cf2c8fbf40b6b3915424b2207d7c44c73b36e6ce9bc1cd'
SOURCE_REVISION = 'a458a3687e27a63647bbe41968094f0e6d0965a0'
FRAME_CYCLES = 19656
spec = importlib.util.spec_from_file_location('callable_vice_trace', ROOT / 'scripts/trace-sid-vice.py')
trace_helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace_helpers)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def parse(log):
    """Reuse VICE's validated record grammar without imposing callable admission."""
    lines = log.splitlines()
    records = []
    for index, line in enumerate(lines):
        header = trace_helpers.TRACE_HEADER.fullmatch(line)
        if header is None:
            continue
        instruction = trace_helpers.INSTRUCTION.fullmatch(lines[index + 1])
        require(instruction is not None, 'Unsupported VICE instruction record')
        operation, address, raster, raster_cycle = header.groups()
        pc, encoded, assembly, a, x, y, sp, flags, cycle = instruction.groups()
        row = dict(operation=operation.lower(), address=int(address, 16), pc=int(pc, 16),
                   bytes=''.join(encoded.split()).lower(), assembly=assembly.strip(),
                   a=int(a, 16), x=int(x, 16), y=int(y, 16), sp=int(sp, 16), flags=flags,
                   rasterLine=int(raster), rasterCycle=int(raster_cycle), monitorCycle=int(cycle))
        require(0 <= row['rasterLine'] < 312 and 0 <= row['rasterCycle'] < 63,
                'Checkpoint is outside PAL raster geometry')
        if row['operation'] == 'store':
            opcode = bytes.fromhex(row['bytes'])
            require(len(opcode) == 3 and opcode[0] in (0x8d, 0x9d, 0x99, 0x8e, 0x8c),
                    'Store evidence requires a non-RMW absolute instruction')
            effective = int.from_bytes(opcode[1:], 'little')
            if opcode[0] == 0x9d:
                effective = (effective + row['x']) & 65535
            elif opcode[0] == 0x99:
                effective = (effective + row['y']) & 65535
            require(effective == row['address'], 'Traced store address disagrees with opcode/registers')
            row['value'] = row['x'] if opcode[0] == 0x8e else row['y'] if opcode[0] == 0x8c else row['a']
        records.append(row)
    entries = [row for row in records if row['operation'] == 'exec' and row['pc'] == 0x4141]
    entry_index = -1
    for row in records:
        if row['operation'] == 'exec' and row['pc'] == 0x4141:
            entry_index += 1
        row['refreshIndex'] = entry_index if entry_index >= 0 else None
    return records, entries


def run_vice(data, output, calls, vice, *, opening):
    output.mkdir()
    payload = output / 'payload.prg'
    payload.write_bytes(data[124:])
    commands = [
        'radix h', 'sidefx off', 'dummy off', 'bank ram', f'load "{payload}" 0',
        'r a=$00,x=$00,y=$00,sp=$ff,fl=$24', 'r pc=$4000',
        'trace exec $4141', 'break exec $4141', f'ignore 2 ${calls:04x}',
    ]
    if opening:
        commands += ['trace store $d400 $d418', 'trace exec $2c30', 'trace exec $2ee0',
                     'trace exec $42ed $42f9', 'trace exec $4198', 'trace store $42f8']
    else:
        commands += ['trace exec $2a46 $2a55', 'trace exec $374b', 'trace exec $3751', 'trace exec $41a0',
                     'trace store $3fff', 'trace store $d417', 'trace store $d418 if A > $0f']
    commands += ['g', 'r', 'quit', '']
    monitor = output / 'commands.mon'
    monitor.write_text('\n'.join(commands))
    command = [str(vice), '-config', '/dev/null', '-directory', str(ROOT / '.tools/vice-headless-3.9/source/data'),
               '-pal', '+logcolorize', '-initbreak', 'ready', '-moncommands', str(monitor),
               '-monlog', '-monlogname', str(output / 'monitor.log'), '-limitcycles', str(4_000_000 + calls * 25000),
               '-warp', '+sound', '-sidenginemodel', 'resid6581', '-cia1model', '1', '-cia2model', '1']
    env = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY'):
        env.pop(key, None)
    for key in ('XDG_CONFIG_HOME', 'XDG_STATE_HOME'):
        env[key] = str(output / key.lower())
        (Path(env[key]) / 'vice').mkdir(parents=True)
    write_json(output / 'command.json', command)
    with (output / 'process.log').open('w') as log:
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=60)
    rows, entries = parse((output / 'monitor.log').read_text(errors='replace'))
    require(len(entries) == calls + 1, 'VICE must stop at the following refresh before it executes')
    intervals = [b['monitorCycle'] - a['monitorCycle'] for a, b in zip(entries, entries[1:])]
    # The archived init enables an existing VIC raster request before its IRQ
    # selects line 246 ($4093); that startup interval is not a full PAL frame.
    require(max(abs(value - FRAME_CYCLES) for value in intervals[1:]) <= 12, 'Unexpected Arkanoid title cadence')
    retained = [row for row in rows if row['refreshIndex'] is None or row['refreshIndex'] < calls]
    with gzip.open(output / 'trace.json.gz', 'wt') as file:
        json.dump(retained, file, separators=(',', ':'))
    write_json(output / 'cadence.json', dict(completedRefreshes=calls, terminalEntryExecuted=False,
                                           startupInterval=intervals[0], intervalsAfterStartup=intervals[1:],
                                           maximumIntervalErrorAfterStartup=max(abs(value - FRAME_CYCLES) for value in intervals[1:])))
    return retained


def stores(rows):
    return [row for row in rows if row['operation'] == 'store' and 0xd400 <= row['address'] <= 0xd418]


def drum_proof(rows, increment):
    previous = total = None
    verified = []
    for row in rows:
        if row['operation'] == 'exec' and row['pc'] == 0x42ef:
            previous = row['a']
        elif row['operation'] == 'exec' and row['pc'] == 0x42f4:
            total = row['a']
            require(previous is not None and total == (previous + increment) & 255,
                    'Executed tom arithmetic disagrees with accumulator prediction')
        elif row['operation'] == 'store' and row['pc'] == 0x42f6:
            require(total is not None and row['value'] == total & 15,
                    'Tom volume store disagrees with arithmetic low nibble')
            verified.append(dict(refreshIndex=row['refreshIndex'], previous=previous, sum=total,
                                 value=row['value'], monitorCycle=row['monitorCycle']))
            previous = total = None
    require(verified and len(verified) % 150 == 0, 'Expected complete six-by-25 tom bodies')
    return verified


def check(source, output, vice):
    original = source.read_bytes()
    require(sha(original) == SOURCE_SHA, 'Arkanoid source fingerprint mismatch')
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh output directory')
    for path in (source, output, vice):
        require(not any(character in str(path) for character in ('"', '\n', '\r')), 'Unsafe monitor path')
    header = inspect_sid(original, subtune=1)
    require(header['format'] == 'RSID' and header['flags'] == 0x14 and header['loadAddress'] == 0x2000
            and header['initAddress'] == 0x4000 and header['playAddress'] == 0, 'Unexpected source machine contract')
    offset = 126 + 0x42f1 - 0x2000
    require(original[offset - 1:offset + 1] == b'\x69\x65', 'Tom intervention no longer points to ADC #$65')
    candidate = bytearray(original)
    candidate[offset] = 0x64
    output.mkdir(parents=True)
    (output / 'tom-increment-100.sid').write_bytes(candidate)
    baseline = run_vice(original, output / 'opening-original', 512, vice, opening=True)
    changed = run_vice(candidate, output / 'opening-increment-100', 512, vice, opening=True)
    original_stores, changed_stores = stores(baseline), stores(changed)
    require(len(original_stores) == len(changed_stores), 'Intervention changed SID store count')
    require([(r['pc'], r['address'], r['monitorCycle']) for r in original_stores]
            == [(r['pc'], r['address'], r['monitorCycle']) for r in changed_stores],
            'Immediate-byte intervention changed writer order or checkpoint timing')
    require([r for r in original_stores if r['address'] != 0xd418]
            == [r for r in changed_stores if r['address'] != 0xd418],
            'Tom intervention changed oscillator/filter stores')
    original_drums, changed_drums = drum_proof(baseline, 101), drum_proof(changed, 100)
    differences = [dict(pc=a['pc'], refreshIndex=a['refreshIndex'], original=a['value'], candidate=b['value'])
                   for a, b in zip(original_stores, changed_stores) if a['value'] != b['value']]
    require(differences and all(row['pc'] in (0x428a, 0x42bc, 0x42f6, 0x4328, 0x435a, 0x438c)
                                for row in differences), 'Differences must be computed drum-volume stores')
    pwm = [row for row in original_stores if row['pc'] in (0x30d1, 0x30d4)]
    require(len(pwm) == 2 * 374, 'Missing executed voice-1 PWM stores')
    pwm_words = []
    for index in range(0, len(pwm), 2):
        low, high = pwm[index:index + 2]
        require(low['pc'] == 0x30d1 and high['pc'] == 0x30d4
                and low['refreshIndex'] == high['refreshIndex'] == 138 + index // 2,
                'PWM low/high pair or update schedule differs')
        step = index // 2 % 100
        expected = 0x0800 + 10 * (step + 1 if step < 50 else 99 - step)
        actual = low['value'] | high['value'] << 8
        require(actual == expected, 'Executed PWM differs from the two-stage retained-width prediction')
        pwm_words.append(dict(refreshIndex=low['refreshIndex'], width=actual))
    note_rows = [row for row in baseline if row['operation'] == 'exec' and row['pc'] == 0x2c30]
    hooks = run_vice(original, output / 'hooks-original', 8192, vice, opening=False)
    hook_targets = [row for row in hooks if row['operation'] == 'exec' and row['pc'] in (0x374b, 0x3751)]
    require({row['pc'] for row in hook_targets} == {0x374b, 0x3751}, 'Both title code hooks must execute')
    indirect = [row for row in hooks if row['operation'] == 'exec' and row['pc'] == 0x2a55]
    require(len(indirect) == len(hook_targets), 'Every target must have an observed code-command indirect jump')
    mode_shadow = None
    restored_modes = []
    for row in hooks:
        if row['operation'] == 'store' and row['address'] == 0x3fff:
            mode_shadow = row['value']
        elif row['operation'] == 'exec' and row['pc'] == 0x41a0:
            require(row['bytes'] == '8d18d4' and mode_shadow is not None and row['a'] == mode_shadow | 15,
                    'Foreground volume restoration differs from the executed mode shadow')
            restored_modes.append(dict(refreshIndex=row['refreshIndex'], value=row['a']))
    require({row['value'] for row in restored_modes} == {15, 31}, 'Missing foreground mode restoration after hooks')
    sources = {}
    for name in ('arkanoid.asm', 'arkadrum.asm', 'README.md'):
        path = ROOT / '.tools/martin-galway-c64' / name
        sources[name] = dict(sha256=sha(path.read_bytes()),
                             url=f'https://github.com/MartinGalway/C64_music/blob/{SOURCE_REVISION}/{name}')
    result = dict(schemaVersion=1, source=dict(url=SOURCE_URL, sha256=SOURCE_SHA, subtune=1, header=header),
                  sourceCorrespondence=dict(revision=SOURCE_REVISION, files=sources,
                      limitation='Published source interprets related routines; archive has relocated/revised code and is not claimed source-build-identical.'),
                  tools=dict(probeSha256=sha(Path(__file__).read_bytes()), viceSha256=sha(vice.read_bytes()),
                             reusedTraceGrammarSha256=sha((ROOT / 'scripts/trace-sid-vice.py').read_bytes())),
                  host=dict(entry=0x4000, initA=0, initX=0, initY=0, initStack=255, initFlags=0x24,
                            timing='Original archived raster IRQ and foreground drum loop, entered after VICE KERNAL READY',
                            clock='PAL', sidModel='MOS6581', cpuPortAfterInit=0x35),
                  opening=dict(completedRefreshes=512, sidStoreCount=len(original_stores),
                      d418StoreCount=sum(row['address'] == 0xd418 for row in original_stores),
                      writerCounts={f'{pc:04x}': count for pc, count in Counter(row['pc'] for row in original_stores if row['address'] == 0xd418).items()},
                      voice1ScoreRows=[dict(refreshIndex=row['refreshIndex'], value=row['a']) for row in note_rows],
                      voice1PwmWrites=len(pwm), voice1PwmFirstRefresh=pwm[0]['refreshIndex'],
                      voice1PwmLastRefresh=pwm[-1]['refreshIndex'], voice1PwmPredictionVerified=True),
                  causalIntervention=dict(address=0x42f1, original=101, candidate=100, candidateSha256=sha(candidate),
                      meaning='Same-material diagnostic: change one tom accumulator increment, not recorded sample data.',
                      verifiedOriginalTomWrites=len(original_drums), verifiedCandidateTomWrites=len(changed_drums),
                      changedVolumeWrites=len(differences), writerOrderAndCheckpointTimingEqual=True,
                      allNonD418StoreRecordsEqual=True, comparisonScope='Initialization plus first 512 completed title refreshes'),
                  codeHooks=dict(completedRefreshes=8192,
                      targets=[dict(pc=row['pc'], refreshIndex=row['refreshIndex']) for row in hook_targets],
                      indirectJumpPc=0x2a55, modeShadow=0x3fff,
                      foregroundRestoresVerified=len(restored_modes), restoredModeValues=sorted({row['value'] for row in restored_modes}),
                      codeCommandTables=dict(voice1=dict(slot=0x3f18, target=int.from_bytes(original[126 + 0x3f18 - 0x2000:126 + 0x3f1a - 0x2000], 'little')),
                                             voice2=dict(slot=0x3f4a, target=int.from_bytes(original[126 + 0x3f4a - 0x2000:126 + 0x3f4c - 0x2000], 'little')),
                                             voice3=dict(slot=0x3f7c, target=0x2a46)),
                      shadowWrites=[dict(pc=row['pc'], value=row['value'], refreshIndex=row['refreshIndex'])
                                    for row in hooks if row['operation'] == 'store' and row['address'] == 0x3fff]),
                  listeningReview=None,
                  limits='This is bounded executed corroboration, not independent reconstruction, complete title form, original game-host equivalence, exact SID bus-cycle timing, hardware sound or musical acceptance. Store checkpoints follow instructions; execution checkpoints precede them. No renderer snapshots are used as a write ledger.')
    for name, value in [('verification.json', result), ('tom-arithmetic-original.json', original_drums),
                        ('tom-arithmetic-increment-100.json', changed_drums), ('changed-volume-values.json', differences),
                        ('voice1-pwm-prediction.json', pwm_words), ('foreground-mode-restores.json', restored_modes)]:
        write_json(output / name, value)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/arkanoid-source.sid')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--vice', type=Path, default=ROOT / '.tools/vice-headless-3.9/build/src/x64sc')
    args = parser.parse_args()
    result = check(args.source.resolve(), args.output.resolve(), args.vice.resolve())
    print(json.dumps(dict(verification=str(args.output.resolve() / 'verification.json'),
                          opening=result['opening'], causalIntervention=result['causalIntervention'],
                          codeHooks=result['codeHooks']), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Arkanoid corroboration: {error}')
