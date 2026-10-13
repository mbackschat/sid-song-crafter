"""Expand the pinned title score without executing its driver or replaying events."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_profile import psid_profile
from verify_player import require

PIN = '41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192'
LISTING_PIN = '119b8cb1ecaf6a9700d1847c9879fa78d50229345dccaaa4f555d8354b73fe66'
SOURCE = ROOT / '.local/research/cybernoid-ii/Cybernoid_II.sid'
EVENTS = ROOT / 'evidence/cybernoid-form-36000/events.json.gz'
STATES = ROOT / 'evidence/cybernoid-form-36000/call-state.json.gz'
FIELDS = ('orderCursor', 'patternCursor', 'rowCountdown', 'durationReload',
          'repeatCount', 'transpose', 'instrumentIndexOffset')


def sha(data):
    return hashlib.sha256(data).hexdigest()


@dataclass
class Voice:
    orderCursor: int = 0
    patternCursor: int = 0
    rowCountdown: int = 0
    durationReload: int = 0
    repeatCount: int = 0
    transpose: int = 0
    instrumentIndexOffset: int = 0
    soundIndex: int = 0
    arpeggioIndex: int | None = None


class Decoder:
    def __init__(self, memory):
        self.memory = memory
        self.voices = [Voice() for _ in range(3)]
        self.orderPointers = [memory[0xaefb + v] | memory[0xaefe + v] << 8 for v in range(3)]
        self.patternPointers = [memory[0xaf01 + 2 * p] | memory[0xaf02 + 2 * p] << 8 for p in range(34)]
        self.tempoReload, self.tempoCountdown, self.playFlag = 2, 0, 0
        self.scratch = 0
        self.events, self.rows, self.calls = [], [], []

    def state(self, voice):
        result = {name: getattr(self.voices[voice], name) for name in FIELDS}
        return dict(result, voiceIndex=voice, orderPointer=self.orderPointers[voice])

    def event(self, kind, voice, pc, **extra):
        event = dict(kind=kind, call=self.call, voiceIndex=voice, pc=pc, **extra)
        if voice is not None:
            event['stateBefore'] = self.state(voice)
        self.events.append(event)
        return len(self.events) - 1

    def read(self, voice, pointer, pc, context, offset=None):
        cursor = self.voices[voice].patternCursor if offset is None else offset
        address = (pointer + cursor) & 65535
        value = self.memory[address]
        index = self.event('pointerRead', voice, pc, sourceAddress=address, sourceValue=value, context=context)
        return value, index

    def helper(self, voice, pointer):
        state = self.voices[voice]
        state.patternCursor = (state.patternCursor + 1) & 255
        value, index = self.read(voice, pointer, 0xa936, 'helper')
        require(value != 255, 'Unsupported executed helper-FF tail branch; needs a focused control-flow fixture')
        return value, index

    def end_pattern(self, voice):
        state = self.voices[voice]
        self.event('patternEnd', voice, 0xa8fc, sourceValue=255)
        state.patternCursor = 0
        if state.repeatCount:
            before = state.repeatCount
            after = (before - 1) & 255
            self.event('patternRepeat', voice, 0xa906, sourceAddress=0xa684 + voice, before=before, after=after)
            state.repeatCount = after
            if not after & 128:
                return
        before = state.orderCursor
        self.event('orderAdvance', voice, 0xa90b, sourceAddress=0xa62d + voice, before=before, after=(before + 1) & 255)
        state.orderCursor = (before + 1) & 255

    def row(self, voice, pattern):
        state, pointer = self.voices[voice], self.patternPointers[pattern]
        first_event = len(self.events)
        commands, patch = [], 'initialize'
        value, origin = self.read(voice, pointer, 0xa7c0, 'start')
        if value >= 240:
            require(value & 1, 'Even initial F prefix is statically known but absent from retained title; fixture required')
            state.patternCursor = (state.patternCursor + 1) & 255
            route, index = self.read(voice, pointer, 0xa7e1, 'continuation')
            commands.append(dict(kind='routing', value=route, origin=index))
            value, origin = self.helper(voice, pointer)
        while True:
            if value >= 224:
                glide_origin = origin
                state.patternCursor = (state.patternCursor + 1) & 255
                control, control_origin = self.read(voice, pointer, 0xa7fd, 'continuation')
                state.patternCursor = (state.patternCursor + 2) & 255
                target, target_origin = self.read(voice, pointer, 0xa80a, 'continuation')
                value, origin = self.read(voice, pointer, 0xa814, 'continuation', (state.patternCursor - 1) & 255)
                commands.append(dict(kind='glide', control=control, baseIndex=(value + state.transpose) & 255,
                                     targetIndex=(target + state.transpose) & 255,
                                     origins=[glide_origin, control_origin, target_origin, origin]))
                break
            if value >= 192:
                state.soundIndex = ((value & 31) + state.instrumentIndexOffset) & 255
                commands.append(dict(kind='sound', index=state.soundIndex, origin=origin))
                value, origin = self.helper(voice, pointer)
            if value >= 128:
                state.durationReload = ((value & 63) - 1) & 255
                commands.append(dict(kind='duration', reload=state.durationReload, origin=origin))
                value, origin = self.helper(voice, pointer)
                if value == 224:
                    continue
                if value >= 128:
                    state.durationReload = (state.durationReload + (value & 127)) & 255
                    commands.append(dict(kind='extendDuration', reload=state.durationReload, origin=origin))
                    value, origin = self.helper(voice, pointer)
                    if value >= 128:
                        continue
            if value >= 112:
                state.arpeggioIndex = value & 15
                commands.append(dict(kind='arpeggio', index=state.arpeggioIndex, origin=origin))
                value, origin = self.helper(voice, pointer)
            break
        commands.append(dict(kind='note', rawIndex=value, pitchIndex=(value + state.transpose) & 255, origin=origin))
        before = state.rowCountdown
        reload_event = self.event('rowReload', voice, 0xa877, sourceAddress=0xa633 + voice,
                                  before=before, value=state.durationReload)
        state.rowCountdown = state.durationReload
        state.patternCursor = (state.patternCursor + 1) & 255
        next_byte, peek = self.read(voice, pointer, 0xa8f6, 'peek')
        if next_byte == 255:
            self.end_pattern(voice)
        self.rows.append(dict(call=self.call, voiceIndex=voice, patternId=pattern, commands=commands,
                              pitchIndex=(value + state.transpose) & 255,
                              countdownReload=state.durationReload, soundIndex=state.soundIndex,
                              arpeggioIndex=state.arpeggioIndex, patchSetup=patch,
                              eventSpan=[first_event, len(self.events)], rowReloadEvent=reload_event,
                              nextPeekEvent=peek, patternEnds=next_byte == 255))

    def order(self, voice):
        state = self.voices[voice]
        for _ in range(256):
            address = (self.orderPointers[voice] + state.orderCursor) & 65535
            value = self.memory[address]
            self.event('orderByte', voice, 0xa754, sourceAddress=address, sourceValue=value, context='order')
            if value == 254:
                self.event('globalStop', voice, 0xa70f, sourceValue=value)
                self.playFlag = 1
                return
            if value == 255:
                self.event('orderWrap', voice, 0xa75f, sourceValue=value)
                state.rowCountdown = state.orderCursor = state.patternCursor = 0
                continue
            if value >= 128:
                state.transpose = value & 31
            elif value >= 96:
                state.instrumentIndexOffset = value & 15
            elif value >= 64:
                state.repeatCount = value & 63
            else:
                require(value < len(self.patternPointers), 'Unmapped pattern pointer index')
                pointer = self.patternPointers[value]
                self.scratch = pointer
                self.event('patternPointer', voice, 0xa7ad, sourceAddress=0xaf01 + 2 * value,
                           patternId=value, patternPointer=pointer)
                self.row(voice, value)
                return
            state.orderCursor = (state.orderCursor + 1) & 255
        raise ValueError('Unbounded order command loop')

    def expand(self, calls):
        for self.call in range(calls):
            if not self.playFlag:
                self.tempoCountdown = (self.tempoCountdown - 1) & 255
                if self.tempoCountdown & 128:
                    self.event('tempoReload', None, 0xa725, sourceAddress=0xa682,
                               before=self.tempoCountdown, value=self.tempoReload)
                    self.tempoCountdown = self.tempoReload
                if self.tempoCountdown == self.tempoReload:
                    for voice in (2, 1, 0):
                        state = self.voices[voice]
                        state.rowCountdown = (state.rowCountdown - 1) & 255
                        if state.rowCountdown & 128:
                            self.order(voice)
                            if self.playFlag:
                                break
            self.calls.append(dict(call=self.call, globals=dict(tempoReload=self.tempoReload,
                                                                tempoCountdown=self.tempoCountdown, playFlag=self.playFlag),
                                   voices=[self.state(v) for v in range(3)], patternScratchPointer=self.scratch))


def compare(predicted, observed):
    keys = ('kind', 'call', 'voiceIndex', 'pc', 'context', 'sourceAddress', 'sourceValue',
            'value', 'before', 'after', 'patternId', 'patternPointer', 'stateBefore')
    # Terminal marker addresses link to the consumed read in the oracle; this
    # projection checks actual marker execution and counter transitions instead.
    def project(row):
        ignored = {'sourceAddress'} if row['kind'] in ('patternEnd', 'orderWrap', 'globalStop') else set()
        return {k: row[k] for k in keys if k in row and k not in ignored}
    require(len(predicted) == len(observed), f'Event count differs: {len(predicted)} != {len(observed)}')
    for index, (a, b) in enumerate(zip(predicted, observed)):
        require(project(a) == project(b), f'Event {index} differs: {project(a)} != {project(b)}')


def check_actions(decoder, events, memory):
    checks = []
    for row in decoder.rows:
        for command in row['commands']:
            kind = command['kind']
            if kind in ('sound', 'duration', 'extendDuration', 'arpeggio'):
                index = command['origin'] + 1
                read = events[index]
                require(read['kind'] == 'pointerRead' and read['pc'] == 0xa936,
                        'Semantic action must join the following actual helper read')
                expected = (memory[0xaf87 + command['index']] if kind == 'arpeggio'
                            else command['index'] if kind == 'sound' else command['reload'])
                require(read['cpu']['a'] == expected, 'Semantic action disagrees with helper-entry accumulator')
                checks.append(dict(kind=kind, eventIndex=index, expectedAccumulator=expected))
            elif kind == 'glide':
                _, control_index, target_index, base_index = command['origins']
                target_read, base_read = events[target_index], events[base_index]
                require(target_read['cpu']['a'] == events[control_index]['sourceValue']
                        and base_read['cpu']['a'] == command['targetIndex'],
                        'Glide control/target assignment disagrees with actual read-entry accumulator')
                checks.append(dict(kind=kind, targetReadEvent=target_index, baseReadEvent=base_index,
                                   expectedControlAccumulator=command['control'],
                                   expectedTargetAccumulator=command['targetIndex']))
    path = ROOT / 'evidence/cybernoid-title-instructions/opening.trace.json.gz'
    trace_bytes = gzip.decompress(path.read_bytes())
    trace = json.loads(trace_bytes)
    require(trace['sourceSha256'] == PIN, 'Canonical opening source identity differs')
    opening = []
    for row in decoder.rows:
        if row['call'] > 63:
            continue
        matches = [(i, r) for i, r in enumerate(trace['instructions'])
                   if r['tick'] == row['call'] and r['x'] == row['voiceIndex'] and r['pc'] == 0xa885]
        require(len(matches) == 1 and matches[0][1]['a'] == row['pitchIndex'],
                'Opening note action disagrees with actual base-pitch store')
        opening.append(dict(call=row['call'], voiceIndex=row['voiceIndex'],
                            pitchIndex=row['pitchIndex'], instructionIndex=matches[0][0],
                            instruction=matches[0][1]))
    return dict(fullWindowActionAccumulatorChecks=checks, openingPitchStores=opening,
                openingTracePath=str(path.relative_to(ROOT)), openingTraceSha256=sha(trace_bytes))


def main(output, contract_output=None):
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh output')
    if contract_output is not None:
        require(not contract_output.exists() and not contract_output.is_symlink()
                and contract_output.resolve() != output.resolve(), 'Choose a separate fresh contract output')
    data = SOURCE.read_bytes()
    require(sha(data) == PIN, 'Original source pin mismatch')
    listing = ROOT / '.local/downloads/tel-cybernoid2.asm'
    require(sha(listing.read_bytes()) == LISTING_PIN, 'Recovered listing pin mismatch')
    profile = psid_profile(data, subtune=1, profile='pal-banked')
    memory = [0] * 65536
    memory[profile['loadAddress']:profile['endAddress']] = profile['payload']
    decoder = Decoder(memory)
    decoder.expand(36000)
    event_bytes, state_bytes = gzip.decompress(EVENTS.read_bytes()), gzip.decompress(STATES.read_bytes())
    events, states = json.loads(event_bytes), json.loads(state_bytes)
    compare(decoder.events, events)
    require(len(decoder.calls) == len(states), 'Completed call count differs')
    for predicted, observed in zip(decoder.calls, states):
        require(all(predicted[k] == observed[k] for k in ('call', 'globals', 'voices', 'patternScratchPointer')),
                f'Completed sequencing state differs at call {predicted["call"]}')
    action_checks = check_actions(decoder, events, memory)
    command_counts = Counter(c['kind'] for r in decoder.rows for c in r['commands'])
    coverage = dict(commandCounts=dict(command_counts),
                    selectedPatternIds=sorted({r['patternId'] for r in decoder.rows}),
                    selectedSoundIndices=sorted({r['soundIndex'] for r in decoder.rows}),
                    selectedArpeggioIndices=sorted({c['index'] for r in decoder.rows for c in r['commands'] if c['kind'] == 'arpeggio'}),
                    rowReloadValues=sorted({r['countdownReload'] for r in decoder.rows}),
                    initialFPrefixes=dict(Counter(str(e['sourceValue']) for e in events
                        if e['kind'] == 'pointerRead' and e['context'] == 'start' and e['sourceValue'] >= 240)),
                    helperFFReads=sum(e['kind'] == 'pointerRead' and e['context'] == 'helper' and e['sourceValue'] == 255 for e in events),
                    orderWrapCalls={str(v): [e['call'] for e in events if e['kind'] == 'orderWrap' and e['voiceIndex'] == v] for v in range(3)},
                    globalStopCalls=[e['call'] for e in events if e['kind'] == 'globalStop'])
    contract = dict(row=dict(voiceIndex='0|1|2', call='generated unsigned call index',
                            patternId='source selection ID', commands='ordered tagged semantic actions',
                            pitchIndex='uint8 source frequency-table index, not MIDI',
                            countdownReload='uint8', soundIndex='uint8 retained effective sound selection',
                            arpeggioIndex='uint4|null retained table selection',
                            patchSetup='initialize|preserve (preserve unobserved here)',
                            origins='canonical event indices for provenance only; never synthesis instructions'),
                    order=dict(pattern='00..3F selects pointer and retains pattern cursor',
                               repeat='40..5F sets additional repeats = byte&3F',
                               soundOffset='60..7F sets byte&0F', transpose='80..FD sets byte&1F',
                               wrap='FF resets row/order/pattern cursors only; then consumes order0 in the same call',
                               stop='FE enters global stop/clearing path; static only in this title window'),
                    scheduling=dict(tempo='Decrement uint8; reload2 on negative result. Process row counters only when countdown equals reload.',
                                    voiceOrder=[2, 1, 0], row='Decrement uint8; select a row when result has bit7 set. Otherwise perform body/gate path.',
                                    observedDuration='All reloads<=67: next row begins (reload+1)*3 calls later. Do not extrapolate that formula to signed-byte reloads>=128.'),
                    retention=dict(everySelectedRowResets=['glideEnabled', 'glideActive', 'noteAge', 'vibratoAge', 'arpeggioCounter'],
                                   everySelectedRowAssigns=['remainingCountdown from retained duration', 'basePitchIndex', 'saved/output frequency', 'gateMask FF'],
                                   initializedPatch=['AD/SR', 'base/working control', 'pulse accumulator/output', 'PWM direction1', 'packed filter selector'],
                                   retainedAcrossRows=['duration until explicit duration command', 'sound until explicit selector', 'arpeggio pointer until explicit selector', 'vibrato direction/position', 'per-voice filter cutoff', 'global filter owner/routing'],
                                   orderWrapRetains=['duration', 'repeat count', 'transpose', 'sound offset', 'instrument/arpeggio selection', 'synthesis state']),
                    contextualRules=dict(prefixPriority='Initial F -> glide -> optional sound -> duration/continuation -> arpeggio -> note; helper continuations re-enter specific stages, not a range-only lexer.',
                                         glide='Packed control, raw base, raw target occupy consecutive bytes, but executed reads are control,target,base. Both pitches add transpose modulo256.',
                                         duration='First high-bit duration sets (byte&3F)-1. Exact E0 after its helper re-enters glide. Otherwise one high-bit extension adds byte&7F; another high-bit helper value re-enters prefix parsing.',
                                         endPeek='After initialization, increment cursor and peek. FF immediately resets cursor and decrements repeat/advances order, while the new row still plays its duration.',
                                         zero='Raw pitch0 is a valid lookup index; no unconditional rest command is inferred.'),
                    missingFixtures=dict(helperFF='A936 FF branches to A8FC without returning through A93E; writer/voice traversal runs with the helper return still on stack. A focused execution must settle resumption effects before general support.',
                                         evenFNonzero='Static A7CE..A7DB sets patch-preserve flag, reads next byte directly and bypasses the normal flag clear when nonzero. No even initial F occurs in the title.',
                                         evenFZero='Static BNE at A7DB is not taken: falls into routing A7DD, reads another byte, calls helper and clears preserve flag. Must not model as ordinary legato.',
                                         otherEdges=['Helper stack tail path', 'even-prefix initialization suppression and zero fallthrough', 'duration signed-byte reloads and wrap', 'wider encoded arpeggio selection range', 'FE stop scheduling']))
    result = dict(schemaVersion=1, sourceSha256=PIN, listingSha256=LISTING_PIN,
                  profile='pal-banked', selectedSubtune=1, playCalls=36000,
                  analyzerSha256=sha(Path(__file__).read_bytes()),
                  inputs={str(EVENTS.relative_to(ROOT)): sha(event_bytes), str(STATES.relative_to(ROOT)): sha(state_bytes)},
                  checks=dict(eventCount=len(events), matchedEventProjections=True,
                              completedSequencingStates=len(states), matchedSequencingStates=True,
                              semanticRows=len(decoder.rows), firstOrderTraversalRows=sum(r['call'] < 17280 for r in decoder.rows),
                              semanticActionAccumulatorChecks=len(action_checks['fullWindowActionAccumulatorChecks']),
                              openingPitchStoreChecks=len(action_checks['openingPitchStores'])),
                  contract=contract, coverage=coverage, actionChecks=action_checks, rows=decoder.rows,
                  limits=['Pure decoding and scheduling from pinned source score bytes; no original driver execution, captured event playback or new render.',
                          'Comparison checks read context/bytes, selected pointers, row reloads, transitions and named sequencing state; not instruction timing, full CPU/RAM, synthesis or sound.',
                          'Helper FF tail branch and even initial F prefixes do not occur in the retained title. This decoder rejects them pending focused fixtures.',
                          'Semantic pitch indices are source lookup indices, not MIDI notes; glide control remains packed and instrument selection awaits the synthesis contract.'])
    with output.open('x') as stream:
        json.dump(result, stream, separators=(',', ':'))
        stream.write('\n')
    if contract_output is not None:
        raw = output.read_bytes()
        summary = {k: v for k, v in result.items() if k not in ('rows', 'actionChecks')}
        summary['rowArtifact'] = dict(path=str(output), sha256=sha(raw), bytes=len(raw))
        summary['actionCheckScope'] = ('Full-window helper-entry accumulators verify sound/duration/arpeggio assignments '
                                      'and glide target arithmetic; five opening note stores independently match canonical '
                                      'instruction rows. Exact row base-pitch stores outside the opening are not separately '
                                      'observed by the existing form hooks.')
        with contract_output.open('x') as stream:
            json.dump(summary, stream, indent=2)
            stream.write('\n')
    print(json.dumps(result['checks']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--contract-output', type=Path)
    args = parser.parse_args()
    main(args.output, args.contract_output)
