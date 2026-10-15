"""Prepare a cycle-preserving B2 gate-off diagnostic from a verified title."""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONTEXT = bytes.fromhex('a9 41 8d 2b d4 a9 00 8d 29 d4')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def patch_image(data, build, expected_sha):
    require(sha(data) == expected_sha, 'Candidate differs from its complete native verification receipt')
    require(data[:6] == b'RSID\x00\x03' and data[6:10] == bytes.fromhex('007c 0000')
        and data[118:124] == bytes.fromhex('0058 0000 4200'), 'Diagnostic requires the declared native two-SID NTSC/MOS6581 title')
    require(build['profile'] == dict(clock='ntsc', sidModel='MOS6581', sidBases=[0xd400, 0xd420]), 'Diagnostic profile differs')
    require(build['arrangement']['support']['patch']['control'] == 0x41, 'Diagnostic requires the selected held-pulse source control')
    address = build['stereoSupport']['controlOnsetAddress']
    load = int.from_bytes(data[124:126], 'little')
    require(load == build['loadAddress'] == 0x0801 and 0x1000 <= address < build['streamAddress'] - len(CONTEXT), 'Support symbol escapes generated music code')
    offset = 126 + address - load
    require(data[offset:offset + len(CONTEXT)] == CONTEXT, 'Support symbol instruction/context differs')
    first, last = 126 + 0x1000 - load, 126 + build['streamAddress'] - load
    require(data[first:last].count(CONTEXT) == 1, 'Support onset instruction context is not unique in music')
    changed = bytearray(data)
    changed[offset + 1] = 0x40
    changed = bytes(changed)
    differences = [index for index, pair in enumerate(zip(data, changed)) if pair[0] != pair[1]]
    require(len(changed) == len(data) and differences == [offset + 1], 'Diagnostic changes more than one immediate byte')
    return changed, dict(schemaVersion=1, diagnostic='B2 held-support gate disabled; not an isolated audio stem or musical verdict',
        originalSha256=sha(data), diagnosticSha256=sha(changed), bytes=len(data),
        controlOnsetAddress=address, changedFileOffset=offset + 1, originalValue=0x41, diagnosticValue=0x40,
        contextHex=CONTEXT.hex(), changedBytes=1, identicalInstructionLayout=True,
        semantics='Only GATE changes in LDA #$41; STA $D42B. The next LDA #$00 overwrites A/N/Z before another use; addressing, instruction lengths, branches and CPU cycles remain unchanged.',
        requiredPcmCheck='Same render settings and candidate gain; left PCM exactly unchanged and right difference nonzero during a held-support window.')


def run(candidate, metadata, verification, output):
    require(not output.exists() and output.resolve().is_relative_to((ROOT / 'build').resolve()), 'Choose a fresh private build/ diagnostic output')
    checked = json.loads(verification.read_text())
    require(checked['cpu']['allOrderedStoresMatch'] and checked.get('vice', {}).get('passed'), 'Diagnostic requires completed main-candidate CPU and VICE proof')
    image, receipt = patch_image(candidate.read_bytes(), json.loads(metadata.read_text()), checked['privateArtifacts']['reconstructed.sid']['sha256'])
    output.mkdir(parents=True)
    (output / 'support-disabled.sid').write_bytes(image)
    (output / 'support-disabled.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--verification', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.candidate, args.build, args.verification, args.output)))


if __name__ == '__main__':
    main()
