"""Recheck this frozen trial against exact inputs, receipts and model responses."""
import hashlib
import json
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'scripts'))
from audio_assessment import _prepare
BASE = ROOT / 'build/bach-model-pacing-20261014'

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

oracle = read(BASE / 'inputs/oracle.json')
prepared = {case['id']: case for case in _prepare(BASE / 'inputs/qwen.json', BASE / 'qwen')}
receipts = {}
for path in sorted((BASE / 'qwen').glob('attempt-*.json')):
    record = read(path)
    assert record['status'] == 'complete' and record['id'] not in receipts
    receipts[record['id']] = (path, record)
qwen = []
for expected in oracle['qwen']['cases']:
    ident = expected['id']
    receipt_path, receipt = receipts[ident]
    assert expected['audio_sha256'] == receipt['audio_sha256'] == prepared[ident]['audio_sha256']
    assert expected['payload_sha256'] == receipt['payload_sha256'] == prepared[ident]['payload_sha256']
    response_path = BASE / 'qwen' / receipt['response_path']
    assert sha(response_path) == receipt['response_sha256']
    response = read(response_path)
    content = response['choices'][0]['message']['content']
    try:
        answer = json.loads(content)
    except (ValueError, TypeError):
        answer = {}
    fields = {key: answer.get(key) == value for key, value in expected['expected'].items()}
    qwen.append({'id': ident, 'expected': expected['expected'], 'answer': answer, 'content': content,
                 'field_matches': fields, 'pass': all(fields.values()), 'cost_usd': receipt['cost'],
                 'model': response['model'], 'provider': response.get('provider'),
                 'audio_sha256': expected['audio_sha256'], 'payload_sha256': expected['payload_sha256'],
                 'receipt_sha256': sha(receipt_path), 'response_sha256': sha(response_path)})
assert set(receipts) == set(prepared)
local = {}
setup = read(ROOT / 'evidence/audio-assessment-songbench/setup.json')
assets = {item['path']: item['sha256'] for item in setup['assets']}
wrapper = ROOT / 'scripts/studies/audio-assessment/songbench-local.py'
for expected in oracle['songbench']['cases']:
    ident = expected['id']
    path = BASE / 'songbench-v2' / (ident + '.json')
    result = read(path)
    audio = BASE / 'inputs' / (ident + '.wav')
    assert result['input']['sha256'] == expected['audio_sha256'] == sha(audio)
    assert result['wrapper_sha256'] == sha(wrapper)
    assert result['model_source_sha256'] == assets['.tools/songbench/model.py']
    assert result['head_sha256'] == assets['.tools/songbench/ckpt/songbench.safetensors']
    assert result['muq_sha256'] == assets['.local/audio-models/muq/model.safetensors']
    assert result['muq_config_sha256'] == assets['.local/audio-models/muq/config.json']
    local[ident] = {'result_sha256': sha(path), **result}
assert local['q02']['input']['sha256'] == local['q04']['input']['sha256']
deltas = {key: abs(local['q02']['scores'][key] - local['q04']['scores'][key]) for key in oracle['songbench']['retain_dimensions']}
report = {'date': '2026-10-14', 'oracle_sha256': sha(BASE / 'inputs/oracle.json'),
          'assessment_script_sha256': sha(Path(__file__)), 'scope': oracle['scope'],
          'qwen': {'cases': qwen, 'passed_cases': sum(case['pass'] for case in qwen), 'total_cases': len(qwen),
                   'cost_usd': str(sum(Decimal(str(case['cost_usd'])) for case in qwen)),
                   'declared_gate_pass': all(case['pass'] for case in qwen)},
          'songbench': {'cases': local, 'primary_dimension': 'musicality',
                       'driven_minus_previous': local['q02']['scores']['musicality'] - local['q01']['scores']['musicality'],
                       'repeat_absolute_differences': deltas},
          'held_out_passage': False, 'establishes_model_eligibility': False}
output = BASE / 'assessment.json'
with output.open('x') as stream:
    stream.write(json.dumps(report, indent=2) + '\n')
print(json.dumps({'qwen_passed':report['qwen']['passed_cases'], 'qwen_total':len(qwen), 'qwen_cost_usd':report['qwen']['cost_usd'],
                  'songbench_musicality':{key:case['scores']['musicality'] for key,case in local.items()}, 'repeat_deltas':deltas},indent=2))
