"""Retain bounded Rambo loader admission, execution and source-attribution evidence."""

from collections import Counter, deque
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid
from psid_profile import psid_profile

SID = ROOT / '.local/rambo-source.sid'
SID_SHA = '88a2b538ee3d3d1d8b0b754bef77a63d9750812694786977ae8c539f6ecd000e'
STIL = ROOT / '.local/downloads/HVSC-STIL.txt'
SOURCE = ROOT / '.tools/martin-galway-c64/rambload.asm'
REVISION = 'a458a3687e27a63647bbe41968094f0e6d0965a0'


def fingerprint(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    folder = Path(__file__).parent
    paths = {name: folder / filename for name, filename in
             [('receipt', 'receipt.json'), ('audit', 'audit64.json'), ('writes', 'audit64.writes.json'),
              ('hooks', 'hooks.json'), ('attribution', 'attribution.json')]}
    assert not any(path.exists() for path in paths.values())
    data = SID.read_bytes()
    assert hashlib.sha256(data).hexdigest() == SID_SHA
    primary = SOURCE.read_text()
    stil = STIL.read_text(encoding='latin-1')
    marker = '/MUSICIANS/G/Galway_Martin/Rambo_First_Blood_Part_II.sid'
    entry = stil.split(marker + '\n', 1)[1].split('\n/MUSICIANS/', 1)[0].strip()
    assert '(#1)' in entry and '(#2)' in entry and '(#11)' in entry
    assert 'only the Loading Music' in primary and 'Composed, Arranged & Programmed' in primary
    secret_source = primary.split('Secret              DFB', 1)[1].split('CodeTab             DFW', 1)[0]
    secret = ''.join(re.findall(r'2\*"([A-Z])"', secret_source))
    encoded_secret = bytes([2 * ord(letter) for letter in secret]) + b'\x00'
    code_words = re.findall(r'\$([0-9A-Fa-f]{4})', primary.split('CodeTab             DFW', 1)[1].split(';\nDE', 1)[0])
    code_table = b''.join(int(word, 16).to_bytes(2, 'little') for word in code_words)
    assert len(code_table) == 26 and code_table[8] == 0x10
    profile = psid_profile(data, profile='pal-banked', subtune=1)
    secret_offset = profile['payload'].find(encoded_secret)
    code_offset = profile['payload'].find(code_table)
    attribution = dict(schemaVersion=1, selectedSubtune=1, scope='Original Morse-code loader, not the entire24subtune collection',
                       sourceSid=fingerprint(SID), stil=fingerprint(STIL), stilVersion='85, June28 2026',
                       stilEntryPath=marker, primarySource=fingerprint(SOURCE), primaryRevision=REVISION,
                       primaryUrl=f'https://github.com/MartinGalway/C64_music/blob/{REVISION}/rambload.asm',
                       composerOwnedReadme=fingerprint(SOURCE.with_name('README.md')),
                       assemblerNotes=fingerprint(SOURCE.with_name('ocean_assembler_directives.txt')),
                       primaryCredit='Loading music composed, arranged and programmed by Martin Galway; Ocean Software1985; limited SSI version.',
                       stilRole=dict(subtune1='Creator-name Morse-code intro; source-composer comment discusses I/E error.',
                                     subtune2='Same as1, corrected Morse code.'),
                       separateSourceCompositions=dict(JerryGoldsmith=[3, 6, 7, 8, 10, 11, 21], RichardWagner=[22],
                                                       subtune11='Main Title credited to Goldsmith; STIL identifies Brian Carter/First Patrol disco version as the covered version.'),
                       conclusion='Loader1 has direct Galway composition/arrangement/programming credit in the original loader source. STIL assigns other listed subtunes to film/classical source compositions; do not transfer those credits to loader1 or call all24 tracks original Galway compositions.',
                       correspondence=dict(secretText=secret, sourceSecretSha256=hashlib.sha256(encoded_secret).hexdigest(),
                                           sourceSecretLength=len(encoded_secret), archiveSecretAddress=profile['loadAddress'] + secret_offset if secret_offset >= 0 else None,
                                           sourceCodeTableSha256=hashlib.sha256(code_table).hexdigest(), sourceCodeTableLength=len(code_table),
                                           archiveCodeTableAddress=profile['loadAddress'] + code_offset if code_offset >= 0 else None,
                                           primaryIByte=code_table[8]),
                       limits='Matching declared credit/intro data is not byte-identical source build or full musical analysis; published source explicitly describes an SSI variant. No source assembly or listening was performed.')
    entries, initial_prefix, counts, ring = [], [], Counter(), deque(maxlen=24)
    error = None

    def observe(cpu, memory):
        pc = cpu.pc
        counts[memory.phase, pc] += 1
        row = dict(phase=memory.phase, call=memory.tick, pc=pc, instructionStartCycle=memory.instruction_cycle,
                   a=cpu.a, x=cpu.x, y=cpu.y, status=cpu.p, instruction=memory.instruction)
        ring.append(row)
        if memory.phase == 'init' and len(initial_prefix) < 48:
            initial_prefix.append(row)
        if pc == profile['initAddress'] or pc == profile['playAddress'] or memory.phase == 'init' and pc == 0xb021:
            entries.append(dict(row, bank=memory.data[1], morseIByte=memory.data[0x80dd],
                                playJumpTarget=memory.data[0xafe9] | memory.data[0xafea] << 8))

    try:
        audit, writes = audit_psid(data, 64, profile='pal-banked', subtune=1, observer=observe)
    except ValueError as failure:
        audit, writes = None, None
        error = str(failure)
    assert SID.read_bytes() == data
    hooks = dict(schemaVersion=1, sourceSha256=SID_SHA, profile='pal-banked', selectedSubtune=1,
                 entries=entries, initFirst48Instructions=initial_prefix,
                 pcVisits=[dict(phase=phase, pc=pc, visits=count) for (phase, pc), count in sorted(counts.items())],
                 failureContext=list(ring) if error else [],
                 limits='PC/entry observations and a bounded instruction prefix only; no relocation copy bytes, full payload/RAM, instrument decoding, bus timestamps or audio are retained.')
    receipt = dict(schemaVersion=1, source=fingerprint(SID), selectedSubtune=1, profile='pal-banked',
                   profileAdmission='accepted', auditSucceeded=audit is not None, executionFailure=error,
                   sourceFileUnchanged=True, probeSha256=fingerprint(Path(__file__))['sha256'],
                   tools={name: fingerprint(ROOT / 'scripts' / name)['sha256'] for name in
                          ('sid_intake.py', 'psid_profile.py', 'psid_audit.py', 'verify_player.py')},
                   cadence='Header/profile declares PAL VBI; successful audit schedules64controlled calls at one perPALframe. This does not independently measure original hardware/VICE cadence.',
                   referenceScope='Preparation only; Shades remains active reconstruction. No renderer/full-song run, source rebuild, independent instrument/player, intervention, listening or approval claim.')
    for name, value in [('attribution', attribution), ('hooks', hooks), ('audit', audit), ('writes', writes)]:
        if value is None:
            continue
        with paths[name].open('x') as stream:
            json.dump(value, stream, indent=2 if name != 'writes' else None,
                      separators=(',', ':') if name == 'writes' else None)
            stream.write('\n')
    receipt['artifacts'] = {name: fingerprint(path) for name, path in paths.items() if name != 'receipt' and path.exists()}
    with paths['receipt'].open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(auditSucceeded=receipt['auditSucceeded'], executionFailure=error,
                          sourceUnchanged=True, auditSummary={name: audit[name] for name in
                              ('playCalls', 'initCycles', 'maximumPlayCycles', 'initWriteCount', 'playWriteCount')} if audit else None,
                          secretMatch=attribution['correspondence']['archiveSecretAddress'],
                          codeTableMatch=attribution['correspondence']['archiveCodeTableAddress'],
                          receiptSha256=fingerprint(paths['receipt'])['sha256'])))


if __name__ == '__main__':
    main()
