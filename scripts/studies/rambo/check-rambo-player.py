#!/usr/bin/env python3
"""Verify the independent numeric Rambo loader against its complete source ledger.

Compute the description's declared call range, compare every ordered SID store,
and independently measure its finite completion and unchanged stopped state.
Pinned audit/form records establish the original's 40,000-call coverage even
though its final 29,185 calls emit no stores. This produces numeric evidence;
it does not build a callable player, render audio or assess listening quality.
"""

import argparse
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from rambo_player import LoaderPlayer, sound_state


SOURCE_SHA256 = '88a2b538ee3d3d1d8b0b754bef77a63d9750812694786977ae8c539f6ecd000e'
WRITES_SHA256 = 'f9ef28f1a5a2b274236a3bc5513be1bfafdd897fbd6b600e0c705b12461a2c64'
AUDIT_SHA256 = 'd5787144b4502df6b4a994ad38e919575b4bf85b589f84ba770e35d32dd8818b'
FORM_SHA256 = '3216e2cc5d7a61b0b73aaf9079eb8b4985f227757e27efe716078b5236c7125c'
CANONICAL = ROOT / 'evidence/rambo-form/complete40000'
COMPONENTS = ('rambo_player.py', 'rambo_score.py', 'rambo_programs.py')


def fingerprint(path):
    path = path.resolve()
    raw = path.read_bytes()
    name = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    return dict(path=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def read_pinned_json(path, expected_sha256, *, compressed=False):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError(f'Canonical fingerprint changed: {path}')
    return json.loads(gzip.decompress(raw) if compressed else raw)


def validate_coverage(audit, form, calls):
    if type(calls) is not int or not 1 <= calls <= 100000:
        raise ValueError('Description auditCalls must be a bounded positive integer')
    if audit.get('sourceSha256') != SOURCE_SHA256 or audit.get('playCalls') != 40000:
        raise ValueError('Canonical audit must establish 40000 calls of the pinned source')
    if audit.get('selectedSubtune') != 1 or audit.get('executionProfile') != 'pal-banked' \
            or audit.get('sidModel') != 'MOS6581' or audit.get('sidCount') != 1 \
            or audit.get('frameCycleBudget') != 19656:
        raise ValueError('Canonical audit differs from the selected PAL/6581 loader contract')
    if form.get('executedCalls') != 40000 or not form.get('completeStoppedLoader') \
            or not form.get('sourceUnchanged') or form.get('firstZeroMusicTestCall') != 10815 \
            or form.get('confirmationCalls') != 29185 or form.get('lastPlayStoreCall') != 10814:
        raise ValueError('Canonical form does not establish the complete stopped loader')
    if calls < form['firstZeroMusicTestCall'] + 64:
        raise ValueError('Numeric range must include at least 64 quiet confirmation calls')


def compare_writes(expected, actual):
    fields = ('phase', 'tick', 'address', 'value')
    if len(expected) != len(actual):
        raise ValueError(f'Complete ordered store count differs: {len(actual)} != {len(expected)}')
    for index, (reference, computed) in enumerate(zip(expected, actual)):
        left = tuple(reference[key] for key in fields)
        right = tuple(computed[key] for key in fields)
        if left != right:
            raise ValueError(f'Complete ordered store mismatch at record {index}: {right} != {left}')


def named_state(player):
    return dict(activeMask=player.score.active_mask, morseActive=player.morse_active,
                morsePhase=player.morse_phase.value, score=deepcopy(player.score.voices),
                sounds=[sound_state(block) for block in player.sound])


def stopped(state):
    return state['activeMask'] == 0 and not state['morseActive'] \
        and all(voice['stackIndex'] == 8 for voice in state['score']) \
        and all(sound['life'] == 0 for sound in state['sounds'])


def compute_and_measure(description, calls):
    player = LoaderPlayer(description)
    initialized = named_state(player)
    first_zero, stopped_state, morse_returns = None, None, []
    for call in range(calls):
        # Archive AFEb tests music before REFRESH; retain that entry boundary
        # instead of inferring completion from the preceding final SID store.
        zero = player.score.active_mask == 0 and all(block[28] == 0 for block in player.sound)
        if zero and first_zero is None:
            first_zero, stopped_state = call, named_state(player)
            if not stopped(stopped_state):
                raise ValueError('Zero active/life status does not establish ordinary stopped score state')
        was_morse = player.morse_active
        write_start = len(player.writes)
        player.play(call)
        if was_morse and not player.morse_active:
            morse_returns.append(call)
        if first_zero is not None and (len(player.writes) != write_start or named_state(player) != stopped_state):
            raise ValueError(f'Numeric player changed its stopped state or emitted stores at call {call}')
    final = named_state(player)
    returns = [dict(call=event['call'], voice=event['voiceIndex'], newActiveMask=event['activeMask'])
               for event in player.score.operations if event['operation'] == 'topReturn']
    last_by_voice = [max((row['tick'] for row in player.writes if row['phase'] == 'play'
                         and 0xd400 + 7 * voice <= row['address'] < 0xd407 + 7 * voice), default=None)
                     for voice in range(3)]
    return player.writes, dict(firstZeroMusicTestCall=first_zero, morseDispatchReturnCalls=morse_returns,
                               topLevelReturns=returns, lastVoiceStoreCalls=last_by_voice,
                               initializedState=initialized, stoppedEntryState=stopped_state,
                               finalState=final, stoppedStatePreserved=stopped(final) and first_zero is not None)


def verify(description, expected, audit, form):
    calls = description.get('range', {}).get('auditCalls')
    validate_coverage(audit, form, calls)
    if len(expected) != audit['initWriteCount'] + audit['playWriteCount'] \
            or sum(row['phase'] == 'init' for row in expected) != audit['initWriteCount'] \
            or sum(row['phase'] == 'play' for row in expected) != audit['playWriteCount']:
        raise ValueError('Canonical complete ledger count disagrees with its pinned audit')
    writes, measurements = compute_and_measure(description, calls)
    compare_writes(expected, writes)
    reference_returns = [{key: row[key] for key in ('call', 'voice', 'newActiveMask')}
                         for row in form['topLevelReturns']]
    if measurements['firstZeroMusicTestCall'] != form['firstZeroMusicTestCall'] \
            or measurements['morseDispatchReturnCalls'] != form['morseDispatchReturnCalls'] \
            or measurements['topLevelReturns'] != reference_returns \
            or not measurements['stoppedStatePreserved']:
        raise ValueError('Numeric Morse/score/lifetime completion boundaries disagree with the original')
    quiet = calls - measurements['firstZeroMusicTestCall']
    last_play = max(row['tick'] for row in writes if row['phase'] == 'play')
    if quiet < 64 or last_play != form['lastPlayStoreCall']:
        raise ValueError('Numeric range does not retain the complete ending and quiet confirmation')
    result = dict(schemaVersion=1, sourceSha256=SOURCE_SHA256, originalObservedCalls=audit['playCalls'],
                  numericComputedCalls=calls, matchedOrderedStores=len(writes),
                  initStores=audit['initWriteCount'], playStores=audit['playWriteCount'],
                  orderedStoreProjection=['phase', 'tick', 'address', 'value'],
                  allOrderedStoresMatched=True, allCompletionBoundariesMatched=True,
                  quietConfirmationCalls=quiet, originalQuietConfirmationCalls=form['confirmationCalls'],
                  lastPlayStoreCall=last_play, declaredCallRateHz=audit['callRateHz'],
                  nominalMusicSeconds=measurements['firstZeroMusicTestCall'] / audit['callRateHz'],
                  measurements=measurements,
                  scope='One independent numeric traversal from editable initialization through the finite stop; all canonical original stores and Morse/score/lifetime boundaries match. Canonical hashes and audit establish the original 40000-call range, including calls without stores.',
                  excluded='No original driver execution in numeric runtime, instruction-start cycle comparison, compiled callable export, audio rendering, analogue tail, actual loader host cadence or listening judgment. Named SOUND state/store agreement is checked by the separate SOUND stage.')
    return writes, result


def prepare_output(path):
    output = path.absolute()
    if any(parent.is_symlink() for parent in (output, *output.parents)):
        raise ValueError('Output paths must not contain symlinks')
    output = output.resolve()
    if output.exists() or output == ROOT / 'build' or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('Choose a fresh output directory below build/')
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('description', type=Path)
    parser.add_argument('--output', type=Path, required=True, help='Fresh directory below build/')
    args = parser.parse_args(argv)
    try:
        output = prepare_output(args.output)
        paths = dict(description=args.description, sourceWrites=CANONICAL / 'writes.json.gz',
                     sourceAudit=CANONICAL / 'audit.json', sourceForm=CANONICAL / 'form.json',
                     checker=Path(__file__))
        paths.update({name: ROOT / 'scripts' / name for name in COMPONENTS})
        inputs = {name: fingerprint(path) for name, path in paths.items()}
        description = json.loads(args.description.read_text())
        expected = read_pinned_json(paths['sourceWrites'], WRITES_SHA256, compressed=True)
        audit = read_pinned_json(paths['sourceAudit'], AUDIT_SHA256)
        form = read_pinned_json(paths['sourceForm'], FORM_SHA256)
        writes, result = verify(description, expected, audit, form)
        if inputs != {name: fingerprint(path) for name, path in paths.items()}:
            raise ValueError('Verification inputs changed during numeric computation')
        output.mkdir(parents=True)
        (output / 'preflight.json').write_text(json.dumps(inputs, indent=2) + '\n')
        raw = (json.dumps(writes, separators=(',', ':')) + '\n').encode()
        model_path = output / 'model-writes.json.gz'
        model_path.write_bytes(gzip.compress(raw, mtime=0))
        result['inputs'] = inputs
        result['modelWrites'] = fingerprint(model_path)
        (output / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({key: result[key] for key in
                          ('originalObservedCalls', 'numericComputedCalls', 'matchedOrderedStores',
                           'lastPlayStoreCall', 'quietConfirmationCalls', 'allOrderedStoresMatched',
                           'allCompletionBoundariesMatched')}, indent=2))
        return 0
    except (OSError, EOFError, ValueError, KeyError, IndexError, TypeError) as error:
        print(f'rambo-player: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
