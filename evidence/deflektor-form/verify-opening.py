"""Compare the form observer with the separately retained opening instruction trace."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path


def read_json(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.output.is_symlink(), 'Choose a fresh validation output')
    trace = read_json(args.trace)
    instructions = read_json(args.run / 'instructions.json.gz')
    writes = read_json(args.run / 'writes.json.gz')
    events = read_json(args.run / 'events.json.gz')
    selected = [row for row in instructions if row['phase'] == 'play' and row['call'] < 64]
    expected = trace['instructions']
    require(len(selected) == len(expected), 'Opening instruction count differs')
    for a, b in zip(selected, expected):
        require((a['call'], a['pc'], a['instructionStartCycle'], a['cpu']) ==
                (b['tick'], b['pc'], b['instructionStartCycle'], dict(a=b['a'], x=b['x'], y=b['y'],
                 sp=b['sp'], p=b['status'], pc=b['pc'])), 'Opening CPU instruction/register checkpoint differs')
    selected_writes = [row for row in writes if row['phase'] == 'init' or row['tick'] < 64]
    expected_writes = [{key: value for key, value in row.items() if key != 'instructionPc'}
                       for row in trace['initSidWrites'] + trace['sidWrites']]
    require(selected_writes == expected_writes, 'Opening SID ledger differs')
    indexed = {(row['tick'], row['instructionStartCycle']): row for row in expected}
    reads = [row for row in events if row['call'] < 64 and row['kind'] in ('patternRead', 'orderRead')]
    for row in reads:
        reference = indexed[(row['call'], row['instructionStartCycle'])]
        require((row['pc'], row['sourceAddress'], row['sourceValue']) ==
                (reference['pc'], reference['operandAddress'], reference['operandValueBefore']),
                'Opening score-read address/value differs from the instruction operand observation')
    paths = [args.trace, args.run / 'instructions.json.gz', args.run / 'writes.json.gz', args.run / 'events.json.gz']
    report = dict(schemaVersion=1, sourceSha256=trace['sourceSha256'], firstCall=0, lastCallInclusive=63,
                  instructionsMatched=len(selected), writesMatched=len(selected_writes),
                  consumptionReadsMatched=len(reads),
                  checkerSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  traceToolSha256=trace['toolSha256'],
                  dependencies=[dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in paths],
                  limits='The two observers share the guarded CPU implementation. This checks observation fidelity, not independent CPU execution or audio.')
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({name: report[name] for name in ('instructionsMatched', 'writesMatched', 'consumptionReadsMatched')}))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
