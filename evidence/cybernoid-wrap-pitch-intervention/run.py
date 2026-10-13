"""Test whether retained vibrato phase explains the first wrapped opening's pitch."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    output = Path(__file__).with_name('receipt.json')
    assert not output.exists()
    source = ROOT / '.local/research/cybernoid-ii/Cybernoid_II.sid'
    data = source.read_bytes()
    assert sha(data) == '41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192'
    baseline_path = ROOT / 'build/cybernoid-wrap-pitch/observations.json'
    baseline_bytes = baseline_path.read_bytes()
    baseline = json.loads(baseline_bytes)
    assert baseline['sourceSha256'] == sha(data)
    expected = baseline['orderedWindowSidWrites']

    def projection(rows, offset=0, voice_only=False):
        return [[r['tick'] - offset, r['address'], r['value']] for r in rows
                if r['phase'] == 'play' and offset <= r['tick'] <= offset + 20
                and (not voice_only or 0xd400 <= r['address'] <= 0xd406)]

    cases = []
    for name, direction, position in [('initial', 0, 0), ('wrapped-direction', 255, 0),
                                      ('wrapped-position', 0, 1), ('wrapped-phase', 255, 1)]:
        mutations, states = [], []

        def observe(cpu, memory):
            if memory.phase != 'play':
                return
            if memory.tick == 0 and cpu.pc == 0xa603:
                assert not mutations
                before = {hex(a): memory.data[a] for a in (0xa667, 0xa66a)}
                assert list(before.values()) == [0, 0]
                memory.data[0xa667], memory.data[0xa66a] = direction, position
                mutations.append(dict(call=0, pc=cpu.pc, before=before,
                                      after={'0xa667': direction, '0xa66a': position}))
            if cpu.pc == 0xae2c:
                states.append(dict(call=memory.tick, direction=memory.data[0xa667],
                                   position=memory.data[0xa66a],
                                   frequency=memory.data[0xa693] | memory.data[0xa696] << 8))

        audit, writes = audit_psid(data, 21, profile='pal-banked', subtune=1, observer=observe)
        assert len(mutations) == 1 and len(states) == 21
        if name == 'initial':
            assert projection(writes) == projection(expected)
        ours, wrapped = projection(writes, voice_only=True), projection(expected, 17280, True)
        differences = [dict(index=i, ours=a, wrapped=b)
                       for i, (a, b) in enumerate(zip(ours, wrapped)) if a != b]
        assert len(ours) == len(wrapped)
        cases.append(dict(name=name, mutations=mutations, states=states, audit=audit,
                          orderedWrites=writes, voice1MatchesWrappedOpening=ours == wrapped,
                          comparedVoice1WriteCount=len(ours), differences=differences))
    assert cases[-1]['voice1MatchesWrappedOpening']
    assert not cases[0]['voice1MatchesWrappedOpening']
    assert source.read_bytes() == data
    receipt = dict(schemaVersion=1, classification='Diagnostic CPU RAM intervention; not an authored arrangement',
                   sourceSha256=sha(data), baselinePath=str(baseline_path.relative_to(ROOT)),
                   baselineSha256=sha(baseline_bytes), scriptSha256=sha(Path(__file__).read_bytes()),
                   tools={name: sha((ROOT / 'scripts' / name).read_bytes())
                          for name in ('psid_audit.py', 'psid_profile.py', 'verify_player.py')},
                   intervention='Before first outer play entry, seed only voice 1 vibrato direction $A667 and position $A66A; retain source bytes, CPU registers and all other initialized state.',
                   oracle='Every control opening SID store matches the independent named-state baseline. Compare all voice 1 ordered register writes for calls 0..20 with baseline calls 17280..17300 after subtracting the order period.',
                   cases=cases,
                   limits='Causal sufficiency for the declared 21-call voice-1 register window only. Individual-byte controls do not establish global necessity; no other voice, full traversal, instruction timing, original IRQ host, SID state, audio or listening equivalence claim.')
    with output.open('x') as target:
        json.dump(receipt, target, indent=2)
        target.write('\n')
    print(json.dumps([dict(name=c['name'], matches=c['voice1MatchesWrappedOpening'],
                           differences=len(c['differences']), call13=c['states'][13]) for c in cases], indent=2))


if __name__ == '__main__':
    main()
