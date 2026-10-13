"""Verify independent caller/pitch primitives against original blocks and retained title state."""

from dataclasses import asdict
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import BankedAuditMemory
from psid_profile import psid_profile
from verify_player import cpu_type
from model import (BodyState, PitchStage, ScorePitchProgram, ScorePitchState,
                   advance_prelude, advance_score_pitch, initialize_score_pitch)

SOURCE_SHA = '606ad4cb19e29c060bb77a9b44253dee62d3d972724acb6cddf625fc2466d44d'
STATE_SHA = '3b5fc9904cdb384b2b2e214ba9cf709827e205b1be2d1270833ece542f518891'
source = ROOT / '.local/research/deflektor/Deflektor.sid'
data = source.read_bytes()
assert hashlib.sha256(data).hexdigest() == SOURCE_SHA
profile = psid_profile(data, profile='pal-banked', subtune=1, host_base=0x0400)
tools = {name: hashlib.sha256((ROOT / 'scripts' / name).read_bytes()).hexdigest()
         for name in ('psid_profile.py', 'psid_audit.py', 'sid_audit_host.py', 'verify_player.py')}


def memory():
    result = BankedAuditMemory((0xd400,), 0x0400)
    result.data[profile['loadAddress']:profile['endAddress']] = profile['payload']
    return result


initial = memory().data
words = {i: initial[0xc8cd + i] | initial[0xc92d + i] << 8 for i in range(256)}
programs = {}
for selector in (8, 16, 24, 32, 40):
    header = initial[0xc9d1 + selector]
    stages = tuple(PitchStage(value >> 3, value & 7)
                   for value in initial[0xc9d2 + selector:0xc9d2 + selector + (header & 7)])
    programs[selector] = ScorePitchProgram(((header & 0x78) >> 3) + 1, (header & 0x38) >> 3,
                                         bool(header & 128), stages)


def run(mem, voice, start, stops, accumulator=0):
    cpu = cpu_type()(memory=mem, pc=start)
    cpu.x, cpu.a, cpu.p = voice, accumulator, 0x26
    mem.data[0xc089], mem.data[0xc08a] = 7 * voice, voice
    while cpu.pc not in stops:
        assert cpu.processorCycles < 6000
        mem.instruction = cpu.disassemble[mem.data[cpu.pc]][0]
        assert mem.instruction not in ('???', 'BRK', 'RTI', 'RTS')
        mem.instruction_cycle = cpu.processorCycles
        cpu.step()
    assert cpu.sp == 255 and not mem.writes
    return cpu.pc


def set_frequency(ram, voice, value):
    ram[0xc095 + 7 * voice], ram[0xc096 + 7 * voice] = value & 255, value >> 8


def frequency(ram, voice):
    return ram[0xc095 + 7 * voice] | ram[0xc096 + 7 * voice] << 8


BODY_BYTES = {'remaining': 0xc0b1, 'rest': 0xc0e7, 'release_threshold': 0xc0b7,
              'glide_wait': 0xc0e1, 'glide_remaining': 0xc0d8, 'glide_flags': 0xc0e4}


def original_prelude(voice, before, skip):
    mem = memory()
    ram = mem.data
    for name, address in BODY_BYTES.items():
        ram[address + voice] = getattr(before, name)
    ram[0xc099 + 7 * voice] = before.control
    ram[0xc105] = int(skip)
    ram[0xc0db + voice], ram[0xc0de + voice] = before.glide_step & 255, before.glide_step >> 8
    set_frequency(ram, voice, before.frequency)
    exit_pc = run(mem, voice, 0xc529, {0xc59a, 0xc547}, before.remaining)
    after = BodyState(control=ram[0xc099 + 7 * voice], frequency=frequency(ram, voice),
                      glide_step=ram[0xc0db + voice] | ram[0xc0de + voice] << 8,
                      **{name: ram[address + voice] for name, address in BODY_BYTES.items()})
    return after, exit_pc == 0xc59a


def original_pitch(voice, selector, before, index, detune, *, loop, initialize=False):
    mem = memory()
    ram = mem.data
    ram[0xc0d5 + voice] = selector
    ram[0xc0ed + voice], ram[0xc0ea + voice] = before.countdown, before.position
    ram[0xc102 + voice], ram[0xc0c0 + voice] = index, detune
    set_frequency(ram, voice, before.frequency)
    if selector:
        ram[0xc9d1 + selector] = (ram[0xc9d1 + selector] & 127) | (128 if loop else 0)
    run(mem, voice, 0xc503 if initialize else 0xc726, {0xc51c if initialize else 0xc7c3})
    return ScorePitchState(ram[0xc0ed + voice], ram[0xc0ea + voice], frequency(ram, voice))


cases = []
for voice, remaining, rest, skip, wait, length, flags, value in itertools.product(
        range(3), (1, 3), (0, 2), (False, True), (0, 1), (0, 1, 255), (0, 32), (0, 65535)):
    before = BodyState(remaining, rest, 0x81, value, remaining, wait, length, flags, 257)
    expected = advance_prelude(before, global_skip=skip)
    assert original_prelude(voice, before, skip) == expected
    cases.append(dict(kind='prelude', voice=voice, before=asdict(before), globalSkip=skip,
                      after=asdict(expected[0]), runPrograms=expected[1]))

for selector, program in [(0, None), *programs.items()]:
    for voice, countdown, position, index, detune, loop in itertools.product(
            range(3), (0, 1, 255), sorted({0, 1, len(program.stages) if program else 1, 254, 255}),
            (24, 60), (0, 255), (False, True)):
        selected = None if program is None else ScorePitchProgram(program.initial_wait, program.restart_wait, loop, program.stages)
        before = ScorePitchState(countdown, position, 65535)
        expected = advance_score_pitch(selected, before, pitch_index=index, detune=detune, frequency_words=words)
        assert original_pitch(voice, selector, before, index, detune, loop=loop) == expected
        cases.append(dict(kind='scorePitch', voice=voice, selector=selector, before=asdict(before),
                          index=index, detune=detune, loop=loop, after=asdict(expected)))
    for voice, position in itertools.product(range(3), (0, 7, 255)):
        before = ScorePitchState(0, position, 65535)
        expected = initialize_score_pitch(program, before)
        assert original_pitch(voice, selector, before, 24, 0, loop=True, initialize=True) == expected
        cases.append(dict(kind='scorePitchInit', voice=voice, selector=selector,
                          before=asdict(before), after=asdict(expected)))

raw = (ROOT / 'evidence/deflektor-form/full40000/states.json.gz').read_bytes()
assert hashlib.sha256(raw).hexdigest() == STATE_SHA
states = json.loads(gzip.decompress(raw))
contexts = []
for call in range(1, 8480):
    previous, current = states[call - 1], states[call]
    skip = any(v['rowCountdown'] == 1 for v in previous['voices'])
    for voice, old in enumerate(previous['voices']):
        if old['rowCountdown'] <= 1:
            continue
        new = current['voices'][voice]
        shadow = old['sidShadow']
        before = BodyState(old['rowCountdown'], old['restCountdown'], shadow[4], shadow[0] | shadow[1] << 8,
            old['releaseThreshold'], old['driverC0E1'], old['driverC0D8'], old['driverC0E4'],
            old['driverC0DB'] | old['driverC0DE'] << 8)
        expected, programs_run = advance_prelude(before, global_skip=skip)
        assert expected.remaining == new['rowCountdown'] and expected.rest == new['restCountdown']
        assert expected.glide_wait == new['driverC0E1'] and expected.glide_remaining == new['driverC0D8']
        if not programs_run:
            assert expected.control == new['sidShadow'][4]
            assert expected.frequency == new['sidShadow'][0] | new['sidShadow'][1] << 8
        context = dict(call=call, voice=voice, bodyBefore=asdict(before), bodyAfter=asdict(expected),
                       programsRun=programs_run, globalSkip=skip)
        if programs_run:
            selector = old['driverC0D5']
            before_pitch = ScorePitchState(old['driverC0ED'], old['driverC0EA'], expected.frequency)
            predicted = advance_score_pitch(programs.get(selector), before_pitch, pitch_index=old['pitchIndex'],
                                             detune=old['orderParameterC0C0'], frequency_words=words)
            assert selector == 0 or selector in programs
            assert (predicted.countdown, predicted.position) == (new['driverC0ED'], new['driverC0EA'])
            lookup = selector != 0 and before_pitch.countdown == 1 and (before_pitch.position < 128 or before_pitch.position == 255)
            if lookup:
                assert predicted.frequency == new['sidShadow'][0] | new['sidShadow'][1] << 8
            context.update(scorePitchBefore=asdict(before_pitch), scorePitchAfter=asdict(predicted),
                           scorePitchLookupCompared=lookup)
        contexts.append(context)

assert source.read_bytes() == data
for name, pin in tools.items():
    assert hashlib.sha256((ROOT / 'scripts' / name).read_bytes()).hexdigest() == pin
artifacts = {}
for name, value in [('isolated.json.gz', cases), ('contexts.json.gz', contexts)]:
    decoded = (json.dumps(value, separators=(',', ':')) + '\n').encode()
    stored = gzip.compress(decoded, mtime=0)
    with (HERE / name).open('xb') as output:
        output.write(stored)
    artifacts[name] = dict(sha256=hashlib.sha256(stored).hexdigest(), decodedSha256=hashlib.sha256(decoded).hexdigest())
receipt = dict(sourceSha256=SOURCE_SHA, sourceUnchanged=True, tools=tools, statesSha256=STATE_SHA,
    modelSha256=hashlib.sha256((HERE / 'model.py').read_bytes()).hexdigest(),
    checkerSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    isolatedCases=len(cases), retainedBodyContexts=len(contexts),
    exposedScorePitchLookups=sum(c.get('scorePitchLookupCompared', False) for c in contexts),
    programs={str(k): asdict(v) for k, v in programs.items()}, artifacts=artifacts,
    limits='Independent prelude and score-selected pitch only. Retained comparisons exclude scheduled rows; later motion can mask incoming frequency/control, so only exposed post-pitch lookups and skipped bodies assert those fields. Lookup words are numeric caller data, not a full player or audio model. Zero restart-delay headers are explicitly unsupported. No new full-title CPU run or original payload/RAM dump.')
with (HERE / 'verification.json').open('x') as output:
    json.dump(receipt, output, indent=2)
    output.write('\n')
print(json.dumps({k: receipt[k] for k in ('isolatedCases', 'retainedBodyContexts', 'exposedScorePitchLookups')}))
