"""Recheck the four frozen speech requests offline and score only their controls."""

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from audio_assessment import _prepare

CASE_IDS = ('p01', 'p02', 'p03', 'p04')
REQUEST_FIELDS = ('id', 'audio_sha256', 'payload_sha256', 'duration_seconds',
    'model', 'max_tokens', 'reasoning', 'reasoning_effort')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fingerprint(path):
    raw = path.read_bytes()
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def parse_observation(content):
    try:
        text = content.strip()
        if text.startswith('```') and text.endswith('```'):
            text = text.split('\n', 1)[1].rsplit('```', 1)[0]
        parsed = json.loads(text)
        if not isinstance(parsed, dict) or not all(isinstance(parsed.get(field), str)
                for field in ('category', 'transcript', 'evidence')):
            return None
        return parsed
    except (AttributeError, ValueError, IndexError):
        return None


def grade_control(observation, expected, finish_reason):
    transcript = observation.get('transcript', '') if observation is not None else ''
    words = set(re.findall(r'\b\w+\b', transcript.lower()))
    if '7' in words:
        words.add('seven')
    missing = [word for word in expected.get('requiredWords', []) if word.lower() not in words]
    empty_matches = transcript == expected['requiredTranscript'] if 'requiredTranscript' in expected else None
    passed = observation is not None and finish_reason == 'stop' and \
        observation['category'] == expected['category'] and not missing and empty_matches is not False
    return dict(passed=passed, parsed=observation is not None, normalCompletion=finish_reason == 'stop',
        missingWords=missing, requiredTranscriptMatches=empty_matches)


def money(value):
    require(type(value) in (int, float), 'Recorded cost must be numeric')
    result = Decimal(str(value))
    require(result.is_finite() and result >= 0, 'Recorded cost must be finite and nonnegative')
    return result


def read_bound_response(path, expected):
    receipt = json.loads(path.read_text())
    require(receipt.get('status') == 'complete', 'Request receipt is not complete')
    for field in REQUEST_FIELDS:
        require(type(receipt.get(field)) is type(expected[field]) and receipt.get(field) == expected[field],
            f'Request binding differs: {field}')
    relative = Path(receipt['response_path'])
    require(not relative.is_absolute() and len(relative.parts) == 1 and relative.name.startswith('response-')
        and relative.suffix == '.json', 'Response path must be a flat response JSON filename')
    response_path = path.parent / relative
    require(not response_path.is_symlink(), 'Response must not be a symlink')
    response_pin = fingerprint(response_path)
    require(response_pin['sha256'] == receipt['response_sha256'], 'Response fingerprint differs')
    response = json.loads(response_path.read_text())
    require(response.get('model') == expected['model'] and isinstance(response.get('provider'), str)
        and response['provider'], 'Response model/provider differs')
    require(receipt['usage'] == response['usage'], 'Recorded response usage differs')
    cost = money(receipt['cost'])
    require(cost == money(response['usage']['cost']), 'Recorded response cost differs')
    choices = response.get('choices')
    require(isinstance(choices, list) and len(choices) == 1, 'Response requires one recorded choice')
    choice = choices[0]
    content = choice.get('message', {}).get('content')
    return dict(id=expected['id'], audio_sha256=expected['audio_sha256'], payload_sha256=expected['payload_sha256'],
        receipt=fingerprint(path), response=response_pin, responseModel=response['model'], provider=response['provider'],
        finishReason=choice.get('finish_reason'), costUsd=format(cost, 'f'),
        rawContent=content, observation=parse_observation(content))


def assess(inputs, results, output):
    inputs, results, output = Path(inputs).resolve(), Path(results).resolve(), Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh assessment output file')
    output = output.resolve()
    require(output.is_relative_to((ROOT / 'build').resolve()), 'Assessment output must be under ignored build/')
    validation_path = inputs / 'validation.json'
    validation = json.loads(validation_path.read_text())
    require(validation.get('passed') is True and validation.get('dryRunOnly') is True,
        'Input preparation did not pass offline validation')
    for name in ('cases.json', 'oracle.json', 'provenance.json'):
        require(fingerprint(inputs / name)['sha256'] == validation['outputs'][name]['sha256'],
            f'Prepared input fingerprint differs: {name}')
    prepared = _prepare(inputs / 'cases.json', results)
    require(tuple(case['id'] for case in prepared) == CASE_IDS, 'Expected the four frozen cases in order')
    require(set(validation['cases']) == set(CASE_IDS), 'Validation case IDs differ')
    oracle = json.loads((inputs / 'oracle.json').read_text())
    controls = {case['id']: case for case in oracle['controls']}
    descriptive = {case['id']: case for case in oracle['descriptiveOnly']}
    require(len(oracle['controls']) == 2 and set(controls) == {'p02', 'p03'}
        and len(oracle['descriptiveOnly']) == 2 and set(descriptive) == {'p01', 'p04'},
        'Only the frozen two controls may be scored')
    require(controls['p02']['category'] == 'silence' and controls['p02']['requiredTranscript'] == ''
        and controls['p03']['category'] == 'speech' and len(controls['p03']['requiredWords']) == 8,
        'Frozen control criteria differ')
    require(all(case.get('expectedCategory') is None and case.get('expectedTranscript') is None
        for case in descriptive.values()), 'Rendered speech must remain without expected answers')
    for case in prepared:
        for bound in (validation['cases'][case['id']], (controls | descriptive)[case['id']]):
            require(all(case[field] == bound[field] for field in
                ('audio_sha256', 'payload_sha256', 'duration_seconds')), 'Prepared audio/payload binding differs')
    attempts = sorted(results.glob('attempt-*.json'))
    require(len(attempts) == 4, 'Frozen trial requires exactly four attempts without retries')
    by_id = {case['id']: case for case in prepared}
    records, seen = [], set()
    for path in attempts:
        case_id = json.loads(path.read_text()).get('id')
        require(case_id in by_id and case_id not in seen, 'Attempt case ID is missing, unknown or duplicated')
        seen.add(case_id)
        records.append(read_bound_response(path, by_id[case_id]))
    response_paths = {Path(record['response']['path']) for record in records}
    require(len(response_paths) == 4 and response_paths == set(results.glob('response-*.json')),
        'Recorded response files are missing, extra or reused')
    records.sort(key=lambda record: CASE_IDS.index(record['id']))
    outcomes = [dict(id=record['id'], expected=controls[record['id']],
        **grade_control(record['observation'], controls[record['id']], record['finishReason']))
        for record in records if record['id'] in controls]
    passed = all(outcome['passed'] for outcome in outcomes)
    total = sum((Decimal(record['costUsd']) for record in records), Decimal(0))
    report = dict(schemaVersion=1, offlineOnly=True, additionalApiRequests=0, completedAttempts=len(records),
        model=prepared[0]['model'], providers=sorted({record['provider'] for record in records}),
        totalActualCostUsd=format(total, 'f'), controlsPassed=passed,
        correctControls=sum(outcome['passed'] for outcome in outcomes), scoredControls=2,
        controlResults=outcomes, cases=records,
        descriptiveCaseIds=['p01', 'p04'], descriptiveObservationsUsable=passed,
        inputBindings={name: fingerprint(inputs / name) for name in
            ('cases.json', 'oracle.json', 'provenance.json', 'validation.json')},
        tools={str(path.relative_to(ROOT)): fingerprint(path) for path in
            (Path(__file__).resolve(), ROOT / 'scripts/audio_assessment.py')},
        claims=dict(renderedSpeechGroundTruth=False, intelligibilityAcceptance=False,
            musicalQualityAssessed=False, pcmIdentity=False),
        scope='Only retained silence/ordinary-speech controls are graded. If either fails, disregard rendered-speech observations. Original/candidate category/transcript remain descriptive; agreement is not ground truth, intelligibility acceptance or a musical judgment.')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as target:
        target.write(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True, help='Prepared cases/oracle/provenance/validation directory')
    parser.add_argument('--results', type=Path, required=True, help='Existing bounded-runner attempt/response directory')
    parser.add_argument('--output', type=Path, required=True, help='Fresh assessment JSON under build/')
    args = parser.parse_args()
    report = assess(args.inputs, args.results, args.output)
    print(json.dumps({key: report[key] for key in ('completedAttempts', 'controlsPassed', 'correctControls',
        'scoredControls', 'totalActualCostUsd', 'descriptiveCaseIds')}))


if __name__ == '__main__':
    main()
