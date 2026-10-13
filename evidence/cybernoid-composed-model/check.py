import argparse
from collections import deque
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main(description_path, calls, output, model_path=None):
    if output.exists() or output.is_symlink():
        raise ValueError('Choose a fresh receipt path')
    raw = description_path.read_bytes()
    description = json.loads(raw)
    model_path = model_path or HERE / 'model.py'
    spec = importlib.util.spec_from_file_location('cybernoid_composed_model', model_path)
    model = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = model
    spec.loader.exec_module(model)
    calls = description['play_calls'] if calls is None else calls
    canonical_path = ROOT / 'evidence/cybernoid-form-36000/audit.writes.json.gz'
    packed = canonical_path.read_bytes()
    canonical = json.loads(gzip.decompress(packed))
    fields = ('phase', 'tick', 'address', 'value')
    expected = [{name: row[name] for name in fields} for row in canonical
                if row['phase'] == 'init' or row['tick'] < calls]
    print(f'Computing {calls} calls from explicit semantic data', flush=True)
    actual = model.compute_writes(description, calls=calls)
    first = next((index for index, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1]), None)
    if first is None and len(actual) != len(expected):
        first = min(len(actual), len(expected))
    result = dict(schemaVersion=1, calls=calls, orderedProjection=list(fields), equal=first is None,
                  actualWriteCount=len(actual), expectedWriteCount=len(expected),
                  descriptionPath=str(description_path), descriptionSha256=sha(raw),
                  modelPath=str(model_path), modelSha256=sha(model_path.read_bytes()), checkerSha256=sha(Path(__file__).read_bytes()),
                  componentHashes={name: sha((ROOT / 'scripts' / name).read_bytes()) for name in
                      ('cybernoid_pitch.py', 'cybernoid_output.py', 'cybernoid_state.py', 'cybernoid_programs.py')},
                  canonicalPath=str(canonical_path.relative_to(ROOT)), canonicalCompressedSha256=sha(packed),
                  hashRecipe='SHA256(UTF8(json.dumps(projected_ordered_rows,separators=(",",":"))+"\\n")); no cycle field or other normalization.',
                  actualSha256=sha((json.dumps(actual, separators=(',', ':')) + '\n').encode()),
                  expectedSha256=sha((json.dumps(expected, separators=(',', ':')) + '\n').encode()),
                  command=f'python3 build/cybernoid-composed-model/check.py {description_path} --calls {calls} --model {model_path} --output {output}',
                  limits='Independent numeric score/program model; canonical original CPU writes are verification-only input. No original CPU execution, instruction-cycle equality, SID physical-state, PCM, render or listening claim.')
    if first is not None:
        actual_row = actual[first] if first < len(actual) else None
        expected_row = expected[first] if first < len(expected) else None
        tick = (expected_row or actual_row)['tick']
        ring = deque(maxlen=12)
        if tick is not None:
            model._compute_writes(description, calls=tick + 1, observer=lambda state: ring.append(state))
        result['firstMismatch'] = dict(writeIndex=first, actual=actual_row, expected=expected_row,
            actualContext=actual[max(0, first - 6):first + 7], expectedContext=expected[max(0, first - 6):first + 7],
            computedStateWindow=list(ring))
    with output.open('x') as target:
        json.dump(result, target, indent=2)
        target.write('\n')
    print(json.dumps({name: result[name] for name in ('calls', 'equal', 'actualWriteCount', 'expectedWriteCount', 'actualSha256', 'expectedSha256')}), flush=True)
    if first is not None:
        print(json.dumps(result['firstMismatch']['expected']), json.dumps(result['firstMismatch']['actual']), flush=True)
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('description', type=Path)
    parser.add_argument('--calls', type=int)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model', type=Path, help='Alternate public model file; defaults to this research model')
    args = parser.parse_args()
    main(args.description, args.calls, args.output, args.model)
