"""Prepare a pinned, lead-only Pink Panther BASIC pulse-width diagnostic."""

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from native_frame_comparison import compare_frames


SOURCE_SHA256 = 'c4c641525b4a71bc28a316b8f10a8000cdc875187981e0ab75cd9f4c97bf6205'
INSTRUMENT_DATA = b'\x8310,41,15,55,65,9,34,15,55,65'
PATCH2_PREFIX = b'\x8310,41,15,55,65,9,34,'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def derive_width_diagnostic(data, *, expected_sha256=SOURCE_SHA256):
    require(sha256(data) == expected_sha256, 'Source SHA-256 differs from the pinned BASIC reference')
    require(len(data) >= 128 and data[:8] == b'RSID\0\x02\0\x7c' and data[8:10] == b'\0\0', 'Expected RSID v2 with embedded load address')
    load = int.from_bytes(data[124:126], 'little')
    require(load == 0x0801, 'Expected BASIC load address $0801')
    position = 126
    while position + 4 <= len(data):
        following = int.from_bytes(data[position:position + 2], 'little')
        require(following != 0, 'BASIC instrument DATA line 37 is missing')
        line = int.from_bytes(data[position + 2:position + 4], 'little')
        end = data.find(b'\0', position + 4)
        require(end >= 0 and following == load + end + 1 - 126, 'BASIC link differs from the terminated line boundary')
        if line == 37:
            require(data[position + 4:end] == INSTRUMENT_DATA, 'BASIC instrument DATA contract differs at line 37')
            start = position + 4 + len(PATCH2_PREFIX)
            changed = data[:start] + b'12,55' + data[start + 5:]
            offsets = [index for index, (before, after) in enumerate(zip(data, changed)) if before != after]
            require(offsets == [start + 1], 'Diagnostic changed bytes outside patch 2 width')
            return changed, dict(
                schemaVersion=1, sourceSha256=sha256(data), diagnosticSha256=sha256(changed),
                sourceBytes=len(data), diagnosticBytes=len(changed), basicLine=37,
                originalPulseWidth=0xf37, diagnosticPulseWidth=0xc37,
                changedBytes=[dict(fileOffset=index, c64Address=load + index - 126,
                                   original=data[index], diagnostic=changed[index]) for index in offsets],
                scope='Only the main melody instrument pulse width changes. Intro/accompaniment instrument, ADSR, waveform, score, BASIC links and header retain their bytes.',
                limits='A source-byte intervention alone does not prove unchanged interpreter timing, SID writes or audible cause; render and compare the initialized register trajectories.')
        position = end + 1
    raise ValueError('BASIC instrument DATA line 37 is missing')


def prepare_diagnostic(source, output):
    data, receipt = derive_width_diagnostic(Path(source).read_bytes())
    output = Path(output)
    require(not output.exists(), 'Output already exists; choose a fresh ignored build directory')
    output.mkdir(parents=True)
    diagnostic = output / 'lead-wide-diagnostic.sid'
    diagnostic.write_bytes(data)
    receipt.update(sourcePath=str(Path(source).resolve()), diagnosticPath=str(diagnostic.resolve()),
                   generatorSha256=sha256(Path(__file__).read_bytes()))
    (output / 'diagnostic.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def inspect_snapshots(reference, diagnostic):
    def read(path):
        data = Path(path).read_bytes()
        rows = [line.split('\t') for line in data.decode().splitlines()[1:]]
        return data, [(int(time), list(bytes.fromhex(registers)[:25])) for time, registers in rows]

    original_bytes, original = read(reference)
    diagnostic_bytes, modified = read(diagnostic)
    timestamps_equal = [time for time, row in original] == [time for time, row in modified]
    comparison, error = None, None
    try:
        comparison = compare_frames([row for time, row in original], [row for time, row in modified], [2, 3])
    except ValueError as failure:
        error = str(failure)
    return dict(schemaVersion=1, referenceSha256=sha256(original_bytes), diagnosticSha256=sha256(diagnostic_bytes),
                referenceSnapshots=len(original), diagnosticSnapshots=len(modified), timestampsEqual=timestamps_equal,
                snapshotValueCheck=comparison, snapshotValueCheckError=error,
                snapshotIsolationPassed=timestamps_equal and error is None,
                limits='Renderer snapshots can miss intervening writes. Failed equality prohibits an isolated width comparison; passed equality still does not establish exact bus timing, waveform state or musical preference.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='operation', required=True)
    prepare = commands.add_parser('prepare')
    prepare.add_argument('source', type=Path)
    prepare.add_argument('--output', type=Path, required=True)
    inspect = commands.add_parser('inspect')
    inspect.add_argument('reference', type=Path)
    inspect.add_argument('diagnostic', type=Path)
    inspect.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.operation == 'prepare':
        receipt = prepare_diagnostic(args.source, args.output)
        print(receipt['diagnosticPath'])
    else:
        receipt = inspect_snapshots(args.reference, args.diagnostic)
        with args.output.open('x') as stream:
            stream.write(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(receipt))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
