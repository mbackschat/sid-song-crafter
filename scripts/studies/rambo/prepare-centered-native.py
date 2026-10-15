"""Allocate the faithful Rambo lead to both native chips with bounded B3 handoffs."""

import argparse
from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from rambo_player import LoaderPlayer
from verify_player import require

spec = importlib.util.spec_from_file_location('rambo_ensemble_preparer', Path(__file__).with_name('prepare-ensemble.py'))
ensemble = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ensemble)
digest, encoded = ensemble.digest, ensemble.encoded

WINDOWS = [dict(startCall=4914, endCall=5554, entryNode='voice-3-row-0115', stopNode='voice-3-row-0181', prefix='sync'),
           dict(startCall=10034, endCall=11000, entryNode='voice-3-row-0336', stopNode=None, prefix='ending')]


def observe(description):
    notes = []

    class ObservedPlayer(LoaderPlayer):
        def note(self, event):
            voice = event['voiceIndex']
            notes.append(dict(event, patch=deepcopy(self.data[voice]), entrySound=deepcopy(self.sound[voice])))
            super().note(event)

    player, states, controls = ObservedPlayer(description), [], [0, 0, 0]
    write_cursor = len(player.writes)
    for call in range(description['range']['auditCalls']):
        player.play(call)
        for row in player.writes[write_cursor:]:
            if row['address'] in (0xd404, 0xd40b, 0xd412):
                controls[(row['address'] - 0xd404) // 7] = row['value']
        write_cursor = len(player.writes)
        states.append(dict(call=call, data=deepcopy(player.data), sound=deepcopy(player.sound),
                           score=deepcopy(player.score.voices), controls=controls.copy(),
                           activeMask=player.score.active_mask, morseActive=player.morse_active,
                           morsePhase=player.morse_phase.value))
    return dict(states=states, writes=player.writes, notes=notes, operations=player.score.operations)


def copy_graph(source, entry, *, prefix='', stop=None):
    graph, pending = {}, [entry]
    while pending:
        name = pending.pop()
        if name in graph or name == stop:
            continue
        node = deepcopy(source['program'][name])
        graph[name] = node
        pending.extend(node[key] for key in ('next', 'target') if key in node)
    result = {}
    for name, node in graph.items():
        for key in ('next', 'target'):
            if key in node:
                node[key] = prefix + node[key]
        result[prefix + name] = node
    if stop:
        result[prefix + stop] = dict(kind='return')
    return result


def third_graph(source, source_records, baseline_records, held_events):
    instructions, graph, banks, cursor = [], {}, {}, 0

    def hold(calls):
        while calls:
            duration = min(calls, 255)
            instructions.append(dict(kind='row', sourceNote=191, duration=duration))
            calls -= duration

    def restore(record, label):
        # Full software state makes the native window exact despite the previous
        # held role; it cannot restore analog envelopes or oscillator phase.
        bank = f'{label}-entry-data'
        banks[bank] = record['data'][2][:29]
        instructions.append(dict(kind='write-data', dataId=bank))
        instructions.extend(dict(kind='poke-data', offset=offset, value=value)
                            for offset, value in enumerate(record['data'][2]) if offset >= 29)
        instructions.append(dict(kind='poke-data', offset=73, value=record['score'][2]['transpose']))
        instructions.extend(dict(kind='poke-sound', offset=offset, value=value)
                            for offset, value in enumerate(record['sound'][2]))

    for event in held_events:
        first, last = event['startCall'], event['endCall']
        if first == 5554:
            window = WINDOWS[0]
            require(cursor == window['startCall'], 'Held/source handoff must occur at its whole-region boundary')
            restore(source_records['states'][cursor - 1], 'sync')
            graph.update(copy_graph(source, window['entryNode'], prefix='sync/', stop=window['stopNode']))
            instructions.append(dict(kind='call', target='sync/' + window['entryNode']))
            cursor = window['endCall']
            restore(baseline_records['states'][cursor - 1], 'held-return')
        hold(first - cursor)
        instructions.extend([dict(kind='poke-data', offset=27, value=event['gateCountdown']),
                             dict(kind='poke-data', offset=28, value=event['releaseLifetime']),
                             dict(kind='row', sourceNote=96 + event['pitchIndex'], duration=last - first)])
        cursor = last
    window = WINDOWS[1]
    hold(window['startCall'] - cursor)
    restore(source_records['states'][window['startCall'] - 1], 'ending')
    graph.update(copy_graph(source, window['entryNode'], prefix='ending/'))
    instructions.extend([dict(kind='call', target='ending/' + window['entryNode']), dict(kind='return')])
    for index, instruction in enumerate(instructions):
        if instruction['kind'] != 'return':
            instruction['next'] = f'third/{index + 1}'
        graph[f'third/{index}'] = instruction
    return graph, banks


def voice_writes(records, voice, first=0, last=11000):
    return [row for row in records['writes'] if 0xd400 + voice * 7 <= row['address'] < 0xd407 + voice * 7
            and (row['phase'] == 'init' and first == 0 or row['phase'] == 'play' and first <= row['tick'] < last)]


def note_ledger(records, voice, first=0, last=11000):
    return [{key: row[key] for key in ('call', 'sourceNote', 'transpose', 'pitchIndex')}
            for row in records['notes'] if row['voiceIndex'] == voice and first <= row['call'] < last]


def same_blocks(left, right, voice, first=0, last=11000):
    return all(left['states'][call][field][voice] == right['states'][call][field][voice]
               for call in range(first, last) for field in ('data', 'sound', 'controls'))


def verify(source, primary, variant, original, baseline, held_events, config):
    require(config['sourceWindows'] == WINDOWS, 'Centered-native source window contract changed')
    require(all(len(records['states']) == source['range']['auditCalls'] == 11000
                for records in (variant, original, baseline)), 'Complete source/variant state coverage is required')
    require(primary == source, 'Primary source changed')
    require(voice_writes(variant, 0) == voice_writes(original, 0), 'Lead ordered stores differ from the complete source')
    require(same_blocks(variant, original, 0), 'Lead data and sound state differ from the complete source')
    require(all(a['score'][0] == b['score'][0] for a, b in zip(variant['states'], original['states'])), 'Lead score state differs from the source')
    require(all((a['morseActive'], a['morsePhase']) == (b['morseActive'], b['morsePhase'])
                for a, b in zip(variant['states'], original['states'])), 'Morse dispatch differs from the source')
    require(voice_writes(variant, 1) == voice_writes(baseline, 1), 'Inner ordered stores differ from accepted support')
    require(note_ledger(variant, 1) == note_ledger(baseline, 1), 'Inner note ledger differs from accepted support')
    require(same_blocks(variant, baseline, 1), 'Inner data and sound differ from accepted support')
    window_proofs = []
    for window in WINDOWS:
        first, last = window['startCall'], window['endCall']
        require(voice_writes(variant, 2, first, last) == voice_writes(original, 2, first, last), 'Third source window ordered stores differ')
        require(same_blocks(variant, original, 2, first, last), 'Third source window data, sound or actual control differs')
        require(note_ledger(variant, 2, first, last) == note_ledger(original, 2, first, last), 'Third source window note ledger differs')
        window_proofs.append(dict(window, orderedStoresIdentical=True, dataAndSoundIdentical=True,
                                  noteLedgerIdentical=True, noteCount=len(note_ledger(original, 2, first, last))))
    outside = lambda call: not any(row['startCall'] <= call < row['endCall'] for row in WINDOWS)
    require([row for row in voice_writes(variant, 2) if row['phase'] == 'init' or outside(row['tick'])]
            == [row for row in voice_writes(baseline, 2) if row['phase'] == 'init' or outside(row['tick'])], 'Third held ordered stores differ')
    require(all(variant['states'][call][field][2] == baseline['states'][call][field][2]
                for call in range(source['range']['auditCalls']) if outside(call)
                for field in ('data', 'sound', 'controls')), 'Third held data, sound or actual control differs')
    actual_held = [row for row in note_ledger(variant, 2) if outside(row['call'])]
    expected_held = [row for row in note_ledger(baseline, 2) if outside(row['call'])]
    require(actual_held == expected_held and len(actual_held) == len(held_events) == 37, 'Third held note ledger differs')
    clear = next(row['call'] for row in variant['states'] if row['call'] >= 10034 and row['sound'][2][28] == 0)
    require(clear == 10814, 'Final copied source modulator lifetime does not clear naturally at 10814')
    final = variant['states'][-1]
    require(final['activeMask'] == 0 and not final['morseActive'] and all(block[28] == 0 for block in final['sound']), 'Variant does not stop naturally')
    return dict(primaryUnchanged=True,
                lead=dict(orderedStoresIdentical=True, dataAndSoundIdentical=True, scoreStateIdentical=True,
                          morseIdentical=True, noteCount=len(note_ledger(variant, 0)), storeCount=len(voice_writes(variant, 0))),
                inner=dict(orderedStoresIdentical=True, noteLedgerIdentical=True, dataAndSoundIdentical=True,
                           noteCount=len(note_ledger(variant, 1)), storeCount=len(voice_writes(variant, 1))),
                third=dict(sourceWindows=window_proofs, heldRegionsRetained=len(held_events), heldRegionsReplaced=5,
                           heldOrderedStoresIdentical=True, heldDataAndSoundIdentical=True, naturalClearCall=clear),
                ending=dict(activeMask=final['activeMask'], remainingLifetimes=[block[28] for block in final['sound']],
                            morseActive=final['morseActive']))


def prepare(source, baseline_config, config, *, arrangement_path='songs/studies/rambo-centered-native/arrangement.json'):
    require(config.get('format') == 'rambo-centered-native-v1', 'Expected centered-native arrangement config')
    require(digest(source) == config['sourceSha256'], 'Retained source fingerprint changed')
    require(digest(baseline_config) == config['baselineArrangementSha256'], 'Accepted baseline config fingerprint changed')
    require(config['sourceWindows'] == WINDOWS, 'Centered-native source window contract changed')
    require(source['range']['auditCalls'] == 11000, 'Centered-native requires the complete retained source range')
    baseline, baseline_proof, _, events = ensemble.prepare(source, baseline_config, arrangement_path=config['baselineArrangement'])
    original, accepted = observe(source), observe(baseline)
    held = [event for event in events if event['voiceIndex'] == 2
            and not WINDOWS[0]['startCall'] <= event['startCall'] < WINDOWS[0]['endCall']]
    third, banks = third_graph(source, original, accepted, held)
    secondary = deepcopy(baseline)
    secondary['program'] = copy_graph(source, source['voices'][0]['cursor'])
    secondary['program'].update(copy_graph(baseline, baseline['voices'][1]['cursor']))
    secondary['program'].update(third)
    secondary['dataBanks'] = {**deepcopy(source['dataBanks']), **banks}
    secondary['voices'][0] = deepcopy(source['voices'][0])
    secondary['voices'][2]['cursor'] = 'third/0'
    secondary['initialData'][0] = deepcopy(source['initialData'][0])
    secondary['initialSound'][0] = deepcopy(source['initialSound'][0])
    secondary['sourceEvidence'] = dict(source=config['source'], sourceSha256=digest(source), arrangement=arrangement_path,
                                       arrangementSha256=digest(config), baselineArrangement=config['baselineArrangement'],
                                       baselineArrangementSha256=digest(baseline_config), originalSource=deepcopy(source['sourceEvidence']),
                                       changes=['Copy the full source lead, including Morse hooks, to physical voice B1 instead of the former low anchor.',
                                                'Keep the accepted inner support on B2 and 37 complete held-third regions on B3.',
                                                'Use source A3 score segments and complete source software entry state on B3 during the declared sync and ring handoffs.'],
                                       listeningStatus='Pending human review; native duplicated lead does not guarantee coherent oscillator phase or a centered image.')
    variant = observe(secondary)
    proof = verify(source, source, variant, original, accepted, held, config)
    proof.update(schemaVersion=1, passed=True, checkedCalls=11000, sourceSha256=digest(source), configSha256=digest(config),
                 baselineConfigSha256=digest(baseline_config), baselineSecondarySha256=digest(baseline),
                 primarySha256=digest(source), secondarySha256=digest(secondary),
                 couplingWindows=[dict(kind='sync', startCall=4915, endCall=5427), dict(kind='ring', startCall=10035, endCall=10660)],
                 phaseHistoryIdentical=False, pcmIdentityClaimed=False, centeredImageEstablished=False,
                 hardware=dict(clock='PAL', sidModels=['MOS6581', 'MOS6581'], sidBases=[0xd400, 0xd420], callCycles=19656),
                 mainPhraseSeconds=config['mainPhraseSeconds'], modelAssistance=config['modelAssistance'],
                 scope='Exact source lead software state/stores, accepted inner support and bounded source-modulator programs; CPU budget, VICE execution, rendered balance and centered image require separate checks.')
    return deepcopy(source), secondary, proof, dict(source=original, baseline=accepted, variant=variant,
                                                    heldEvents=held, baselineProof=baseline_proof)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('arrangement', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    require(not args.output.exists(), 'Choose a fresh preparation output directory')
    config = json.loads(args.arrangement.read_text())
    source = json.loads((ROOT / config['source']).read_text())
    baseline = json.loads((ROOT / config['baselineArrangement']).read_text())
    primary, secondary, proof, records = prepare(source, baseline, config, arrangement_path=str(args.arrangement))
    args.output.mkdir(parents=True)
    for name, value in (('primary', primary), ('secondary', secondary), ('arrangement-proof', proof)):
        (args.output / f'{name}.json').write_bytes(encoded(value))
    for name in ('source', 'baseline', 'variant'):
        (args.output / f'{name}-observations.json.gz').write_bytes(gzip.compress(encoded(records[name]), mtime=0))
        (args.output / f'{name}-note-events.json.gz').write_bytes(gzip.compress(encoded(records[name]['notes']), mtime=0))
    (args.output / 'held-note-events.json.gz').write_bytes(gzip.compress(encoded(records['heldEvents']), mtime=0))
    print(f'Prepared native duplicate lead and {proof["third"]["heldRegionsRetained"]} held regions: {args.output}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(str(error))
