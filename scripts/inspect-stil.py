"""Extract one exact STIL entry into private build output with byte-level pins."""

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from reference_intake import managed_output


def extract(data, entry_path):
    if not entry_path or any(c in entry_path for c in ('\n', '\r', '\0')):
        raise ValueError('Choose one nonempty HVSC entry path')
    selector = '/' + entry_path.lstrip('/')
    target = selector.encode('utf-8')
    lines = data.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.rstrip(b'\r\n') == target]
    if len(starts) != 1:
        raise ValueError(f'Expected exactly one complete entry header; found {len(starts)}')
    start = starts[0]
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith(b'/')), len(lines))
    entry = b''.join(lines[start:end])
    return entry, dict(schemaVersion=1, entryPath=selector, firstLine=start + 1, lastLine=end,
                       sourceBytes=len(data), sourceSha256=hashlib.sha256(data).hexdigest(),
                       entryBytes=len(entry), entrySha256=hashlib.sha256(entry).hexdigest(),
                       scope='Exact source entry including original line endings; subtune credits and comments still require interpretation.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stil', type=Path, required=True)
    parser.add_argument('--entry', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    entry, receipt = extract(args.stil.read_bytes(), args.entry)
    output = managed_output(args.output, ROOT)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'entry.txt').write_bytes(entry)
    receipt['sourcePath'] = str(args.stil)
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
