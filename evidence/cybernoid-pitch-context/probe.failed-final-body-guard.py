"""Verify the frozen independent pitch component in each intact title body."""

from collections import Counter
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'evidence/cybernoid-pitch-contract'))
from psid_audit import audit_psid
from model import PitchInputs, PitchParameters, PitchState, advance_pitch
import model

SOURCE = ROOT / '.local/research/cybernoid-ii/Cybernoid_II.sid'
SOURCE_SHA = '41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192'
MODEL = ROOT / 'evidence/cybernoid-pitch-contract/model.py'
MODEL_SHA = '1e31d9ffa9ea248f3030149ae5540962e0d7dff8e515354b504f4f0d02bbbf3b'
CANONICAL = ROOT / 'evidence/cybernoid-form-36000/audit.writes.json.gz'
FIELDS = dict(base_note=0xa63f, frequency=(0xa693, 0xa696),
              held_frequency=(0xa64b, 0xa645), vibrato_extent=0xa664,
              vibrato_direction=0xa667, vibrato_position=0xa66a,
              vibrato_age=0xa6a8, glide_enabled=0xa64e, glide_active=0xa651,
              glide_control=0xa690, glide_target=0xa68d)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_records(path):
    decoder, buffer, offset = json.JSONDecoder(), '', 0
    with gzip.open(path, 'rt') as stream:
        ended = False
        while True:
            buffer = buffer[offset:] + stream.read(65536)
            offset = 0
            if not buffer:
                break
            while True:
                while offset < len(buffer) and buffer[offset] in ' \r\n\t[,]':
                    if buffer[offset] == ']':
                        ended = True
                    offset += 1
                if offset == len(buffer):
                    break
                try:
                    record, after = decoder.raw_decode(buffer, offset)
                except json.JSONDecodeError:
                    break
                offset = after
                yield record
        assert ended and not buffer[offset:].strip()


def main():
    folder = Path(__file__).parent
    ledger_path, receipt_path, mismatch_path = (folder / name for name in
                                               ('bodies.jsonl.gz', 'receipt.json', 'mismatch.json'))
    assert not any(p.exists() for p in (ledger_path, receipt_path, mismatch_path))
    data = SOURCE.read_bytes()
    assert hashlib.sha256(data).hexdigest() == SOURCE_SHA
    assert Path(model.__file__).resolve() == MODEL.resolve() and sha(MODEL) == MODEL_SHA
    pending, counts, variants = {}, Counter(), Counter()
    body_count, last_completed = 0, None
    plain_hash, plain_bytes = hashlib.sha256(), 0
    started = time.monotonic()

    def state_at(memory, voice):
        return PitchState(**{name: (memory.data[location[0] + voice] | memory.data[location[1] + voice] << 8
                                   if isinstance(location, tuple) else memory.data[location + voice])
                             for name, location in FIELDS.items()})

    def word_at(memory, note):
        return memory.data[0xae3f + note] | memory.data[0xae96 + note] << 8

    with ledger_path.open('xb') as ledger_file, gzip.GzipFile(filename='', fileobj=ledger_file, mode='wb', mtime=0) as ledger:
        def observe(cpu, memory):
            nonlocal body_count, last_completed, plain_bytes
            if memory.phase != 'play':
                return
            pc, call = cpu.pc, memory.tick
            if pc == 0xa603 and call % 2048 == 0:
                assert not pending
                print(json.dumps(dict(call=call, checkedBodies=body_count,
                                      elapsedSeconds=round(time.monotonic() - started, 1))), flush=True)
            if pc not in (0xa9c1, 0xaa97, 0xab8d):
                return
            voice = memory.data[0x48]
            assert 0 <= voice < 3
            if pc in (0xa9c1, 0xaa97):
                if pc == 0xaa97 and voice in pending:
                    return
                assert voice not in pending
                drum = bool(memory.data[0x42] & 16)
                assert (pc == 0xaa97) == drum
                state = state_at(memory, voice)
                note, record = memory.data[0xa63c + voice], memory.data[0xa642 + voice]
                parameters = PitchParameters(memory.data[0x40], memory.data[0xb0ac + record], drum)
                inputs = PitchInputs(word_at(memory, note), word_at(memory, note + 1),
                                     word_at(memory, state.base_note), word_at(memory, state.glide_target),
                                     memory.data[0xa65e + voice], memory.data[0xa633 + voice],
                                     memory.data[0xa636 + voice], memory.data[0xa629])
                prediction = advance_pitch(state, parameters, inputs)
                pending[voice] = dict(call=call, voice=voice, record=record, effectiveNote=note,
                                      entryPc=pc, entryInstructionCycle=memory.instruction_cycle,
                                      state=state, parameters=parameters, inputs=inputs, prediction=prediction)
                return
            entry = pending.pop(voice)
            assert entry['call'] == call
            actual = state_at(memory, voice)
            expected = entry['prediction']
            actual_delta = memory.data[0x4f] | memory.data[0x4e] << 8 if expected.vibrato_ran else None
            row = dict(call=call, voice=voice, record=entry['record'], effectiveNote=entry['effectiveNote'],
                       entryPc=entry['entryPc'], entryInstructionCycle=entry['entryInstructionCycle'],
                       exitPc=pc, exitInstructionCycle=memory.instruction_cycle,
                       state=asdict(entry['state']), parameters=asdict(entry['parameters']), inputs=asdict(entry['inputs']),
                       output=asdict(expected), actualVibratoDelta=actual_delta)
            if actual != expected.state or actual_delta != expected.vibrato_delta:
                row.update(actual=asdict(actual), stateEqual=actual == expected.state,
                           deltaEqual=actual_delta == expected.vibrato_delta)
                with mismatch_path.open('x') as mismatch:
                    json.dump(row, mismatch, indent=2)
                    mismatch.write('\n')
                raise ValueError(f'Pitch-component mismatch at call{call} voice{voice}; see {mismatch_path}')
            encoded = (json.dumps(row, separators=(',', ':')) + '\n').encode()
            ledger.write(encoded)
            plain_hash.update(encoded)
            plain_bytes += len(encoded)
            body_count += 1
            last_completed = call
            counts[f'voice{voice}'] += 1
            counts['vibrato' if expected.vibrato_ran else 'noVibrato'] += 1
            counts[f'glide:{expected.glide_action.value}'] += 1
            variants[f'{voice}:{entry["record"]}:{entry["parameters"].vibrato_control:02X}:{entry["state"].glide_control:02X}:{expected.glide_action.value}'] += 1

        audit, writes = audit_psid(data, 17281, profile='pal-banked', subtune=1, observer=observe)
        assert not pending and last_completed == 17280

    canonical = canonical_records(CANONICAL)
    ours_hash, canonical_hash = hashlib.sha256(b'['), hashlib.sha256(b'[')
    for index, actual in enumerate(writes):
        expected = next(canonical)
        assert actual == expected, (index, actual, expected)
        separator = b',' if index else b''
        ours_hash.update(separator + json.dumps(actual, separators=(',', ':')).encode())
        canonical_hash.update(separator + json.dumps(expected, separators=(',', ':')).encode())
    following = next(canonical)
    assert following['phase'] == 'play' and following['tick'] == 17281
    canonical.close()
    ours_hash.update(b']\n')
    canonical_hash.update(b']\n')
    assert ours_hash.digest() == canonical_hash.digest()
    assert SOURCE.read_bytes() == data and sha(MODEL) == MODEL_SHA
    receipt = dict(schemaVersion=1, classification='Full selected-title contextual pitch-component proof',
                   sourceSha256=SOURCE_SHA, modelPath=str(MODEL.relative_to(ROOT)), modelSha256=MODEL_SHA,
                   probeSha256=sha(Path(__file__)), tools={name: sha(ROOT / 'scripts' / name) for name in
                                                          ('psid_audit.py', 'psid_profile.py', 'verify_player.py')},
                   selectedSubtune=1, executionProfile='pal-banked', calls=dict(first=0, lastInclusive=17280, count=17281),
                   hooks=dict(normalEntry=0xa9c1, drumBypassEntry=0xaa97, exitBefore=0xab8d),
                   inputStateAddresses=FIELDS, bodyCount=body_count, counts=dict(counts), variants=dict(sorted(variants.items())),
                   everyCapturedBodyStateMatches=True, everyComputedVibratoDeltaMatches=True,
                   ledger=dict(path=str(ledger_path.relative_to(ROOT)), compressedBytes=ledger_path.stat().st_size,
                               compressedSha256=sha(ledger_path), originalBytes=plain_bytes, originalSha256=plain_hash.hexdigest(),
                               format='One lossless JSON object per body; input named state/parameters/table words/context, model output and actual source delta. Equality asserted before recording; actual state equals output.state.'),
                   orderedWritePrefix=dict(canonicalPath=str(CANONICAL.relative_to(ROOT)), canonicalCompressedSha256=sha(CANONICAL),
                                           recordCount=len(writes), exactRecordEquality=True,
                                           prefixSha256=ours_hash.hexdigest(), canonicalPrefixSha256=canonical_hash.hexdigest(),
                                           includes='Every initialization and selected play store; no cycle/address/value/field normalization.',
                                           hashRecipe='SHA256 of compact JSON ordered-record array plus newline.'),
                   audit=audit, elapsedSeconds=round(time.monotonic() - started, 3),
                   limits='Only the declared pitch block is independently computed; caller state/table words are observed inputs. This is neither a complete independent song player nor a proof of upstream arpeggio/row scheduling or later waveform/onset/drum/sweep/filter/PWM behavior. Guarded CPU instruction cycles are distinct from bus timing, SID state, rendered audio and listening. Source bytes/frozen model are unchanged; observer only reads backing state and writes evidence files.')
    with receipt_path.open('x') as output:
        json.dump(receipt, output, indent=2)
        output.write('\n')
    print(json.dumps(dict(saved=str(receipt_path.relative_to(ROOT)), checkedBodies=body_count,
                          orderedPrefixRecords=len(writes), allMatched=True, counts=dict(counts),
                          ledgerCompressedBytes=ledger_path.stat().st_size)), flush=True)


if __name__ == '__main__':
    main()
