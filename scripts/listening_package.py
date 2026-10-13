"""Execute trusted project recipes and retain content-verified stage attempts."""

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import string
import subprocess
import sys
import time
from urllib.parse import quote
import uuid


RUNNER_VERSION = 1
ROOT = Path(__file__).resolve().parents[1]
_FORMATTER = string.Formatter()
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*\Z')


class PackageError(RuntimeError):
    """A recipe, subprocess or retained artifact failed verification."""


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def _sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _timestamp():
    return datetime.now(timezone.utc).isoformat()


def _template_parts(template):
    try:
        parts = list(_FORMATTER.parse(template))
    except ValueError as error:
        raise PackageError(f'invalid placeholder in {template!r}: {error}') from error
    for _, field, spec, conversion in parts:
        if field is None:
            continue
        if conversion or (field != 'stage' and spec) or field not in ('out', 'root', 'python', 'stage'):
            raise PackageError(f'unknown placeholder in {template!r}')
        if field == 'stage' and not _ID.fullmatch(spec):
            raise PackageError(f'invalid stage placeholder in {template!r}')
    return parts


def _validate_template(template, previous, *, input_path=False, allow_empty=False):
    if not isinstance(template, str) or (not template and not allow_empty) or '\0' in template:
        raise PackageError('templates must be strings without NUL characters; paths and executables must be nonempty')
    for _, field, spec, _ in _template_parts(template):
        if field == 'stage' and spec not in previous:
            raise PackageError(f'{{stage:{spec}}} must reference a previous stage')
        if input_path and field in ('out', 'python'):
            raise PackageError(f'input path cannot use {{{field}}}')


def _render(template, root, attempts, out=None):
    values = {'root': str(root), 'python': sys.executable, 'out': str(out) if out is not None else '{out}'}
    pieces = []
    for literal, field, spec, _ in _template_parts(template):
        pieces.append(literal)
        if field is not None:
            pieces.append(str(attempts[spec]) if field == 'stage' else values[field])
    return ''.join(pieces)


def _relative_path(value, label, *, allow_base=False):
    path = Path(value)
    if not value or path.is_absolute() or '..' in path.parts or '\\' in value or (not allow_base and path == Path('.')):
        raise PackageError(f'{label} must be a relative path without traversal: {value!r}')
    return path


def _no_symlinks(base, path):
    if base.is_symlink():
        raise PackageError(f'symlink paths are unsupported: {base}')
    current = base
    for component in path.relative_to(base).parts:
        current = current / component
        if current.is_symlink():
            raise PackageError(f'symlink paths are unsupported: {current}')


def _input_location(template, root, attempts):
    stage = re.fullmatch(r'\{stage:([^}]+)\}(?:/(.*))?', template)
    if stage:
        base = attempts[stage.group(1)]
        relative = stage.group(2) or '.'
    elif template == '{root}' or template.startswith('{root}/'):
        base = root
        relative = template[len('{root}/'):] if template != '{root}' else '.'
    else:
        base = root
        relative = _render(template, root, attempts)
        if Path(relative).is_absolute():
            if '..' in Path(relative).parts or '\\' in relative:
                raise PackageError(f'input path must not contain traversal: {relative!r}')
            return Path(relative)
    path = base / _relative_path(relative, 'input', allow_base=True)
    return path


def _fingerprint_path(path):
    if path.is_symlink():
        raise PackageError(f'symlink paths are unsupported: {path}')
    if path.is_file():
        return {'type': 'file', 'sha256': _sha256(path)}
    if path.is_dir():
        files = []
        for entry in sorted(path.rglob('*')):
            if entry.is_symlink():
                raise PackageError(f'symlink paths are unsupported: {entry}')
            if entry.is_file():
                files.append({'path': entry.relative_to(path).as_posix(), 'sha256': _sha256(entry)})
            elif not entry.is_dir():
                raise PackageError(f'unsupported filesystem object: {entry}')
        return {'type': 'directory', 'sha256': hashlib.sha256(_json_bytes(files)).hexdigest(), 'files': files}
    raise PackageError(f'missing or unsupported file/directory: {path}')


def _validate_recipe(recipe):
    if not isinstance(recipe, dict) or type(recipe.get('schemaVersion')) is not int or recipe['schemaVersion'] != 1:
        raise PackageError('recipe requires schemaVersion 1')
    if set(recipe) - {'schemaVersion', 'stages', 'deliverables'}:
        raise PackageError('unknown recipe fields')
    stages = recipe.get('stages')
    if not isinstance(stages, list) or not stages:
        raise PackageError('stages must be a nonempty list')
    previous = set()
    definitions = {}
    for stage in stages:
        required = {'id', 'command', 'inputs', 'outputs', 'timeoutSeconds'}
        if not isinstance(stage, dict) or not required <= set(stage) or set(stage) - required - {'env'}:
            raise PackageError('stage requires id, command, inputs, outputs and timeoutSeconds; env is optional')
        stage_id = stage['id']
        if not isinstance(stage_id, str) or not _ID.fullmatch(stage_id):
            raise PackageError('stage id must contain only letters, digits, underscores or hyphens and start with a letter or digit')
        if stage_id in previous:
            raise PackageError('stage ids must be unique')
        command = stage['command']
        if not isinstance(command, list) or not command:
            raise PackageError(f'{stage_id}: command must be a nonempty argv list')
        for index, token in enumerate(command):
            _validate_template(token, previous, allow_empty=index > 0)
        for kind in ('inputs', 'outputs'):
            paths = stage[kind]
            if not isinstance(paths, list) or any(not isinstance(path, str) for path in paths) or len(set(paths)) != len(paths):
                raise PackageError(f'{stage_id}: {kind} must be a list of unique path strings')
        for template in stage['inputs']:
            _validate_template(template, previous, input_path=True)
            dummy = {name: Path(name) for name in previous}
            _input_location(template, Path('.'), dummy)
        for output in stage['outputs']:
            path = _relative_path(output, 'output')
            if '{' in output or '}' in output or path.parts[0] in ('stage.log', 'success.json'):
                raise PackageError(f'{stage_id}: output conflicts with a runner file or placeholder')
        timeout = stage['timeoutSeconds']
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise PackageError(f'{stage_id}: timeoutSeconds must be finite and positive')
        env = stage.get('env', {})
        if not isinstance(env, dict):
            raise PackageError(f'{stage_id}: env must map variable names to strings')
        for name, value in env.items():
            if not isinstance(name, str) or not name or '=' in name or '\0' in name:
                raise PackageError(f'{stage_id}: invalid env variable name')
            _validate_template(value, previous, allow_empty=True)
        previous.add(stage_id)
        definitions[stage_id] = stage
    deliverables = recipe.get('deliverables', {})
    if not isinstance(deliverables, dict):
        raise PackageError('deliverables must map labels to declared stage outputs')
    for label, template in deliverables.items():
        if not isinstance(label, str) or not label or '\n' in label or '\r' in label:
            raise PackageError('deliverable labels must be nonempty single-line strings')
        if not isinstance(template, str):
            raise PackageError('deliverables must reference declared stage outputs')
        match = re.fullmatch(r'\{stage:([^}]+)\}/(.+)', template)
        if not match or match.group(1) not in definitions or match.group(2) not in definitions[match.group(1)]['outputs']:
            raise PackageError(f'deliverable {label!r} must reference a declared stage output')


def _prepare_output(output, root):
    supplied = Path(output)
    output = supplied if supplied.is_absolute() else root / supplied
    output = Path(os.path.abspath(output))
    build = root / 'build'
    if output == build or build not in output.parents:
        raise PackageError('--output must be a directory beneath the ignored repository build/ directory')
    _no_symlinks(root, output)
    output.mkdir(parents=True, exist_ok=True)
    return output


def _runtime_fingerprint():
    source_paths = [Path(__file__), Path(__file__).with_name('listening-package.py')]
    return {
        'runnerVersion': RUNNER_VERSION,
        'runnerSources': {path.name: _sha256(path) for path in source_paths},
        'python': {'version': sys.version, 'implementation': sys.implementation.name,
                   'platform': sys.platform, 'executableSha256': _sha256(Path(sys.executable).resolve())},
    }


def _inputs(stage, root, attempts):
    records = []
    for template in stage['inputs']:
        path = _input_location(template, root, attempts)
        target = path.resolve() if path.is_file() else path
        records.append({'path': template, **_fingerprint_path(target)})
    return records


def _executable_fingerprint(token, env, root):
    if '/' in token:
        path = Path(token) if Path(token).is_absolute() else root / token
    else:
        found = shutil.which(token, path=env.get('PATH', os.defpath))
        if not found:
            raise PackageError(f'command executable not found: {token}')
        path = Path(found)
        if not path.is_absolute():
            path = root / path
    return _fingerprint_path(path.resolve())


def _outputs(stage, attempt):
    records = []
    for relative in stage['outputs']:
        path = attempt / relative
        _no_symlinks(attempt, path)
        records.append({'relativePath': relative, **_fingerprint_path(path)})
    return records


def _cached_attempt(base, stage, key):
    if not base.exists():
        return None
    for attempt in sorted(base.iterdir()):
        if attempt.is_symlink() or not attempt.is_dir() or not attempt.name.startswith('attempt-'):
            continue
        receipt_path = attempt / 'success.json'
        log = attempt / 'stage.log'
        if receipt_path.is_symlink() or log.is_symlink() or not log.is_file():
            continue
        try:
            receipt = json.loads(receipt_path.read_text())
            if receipt.get('schemaVersion') == 1 and receipt.get('key') == key and receipt.get('outputs') == _outputs(stage, attempt):
                return attempt, receipt['outputs']
        except (OSError, ValueError, PackageError, AttributeError):
            continue
    return None


def _atomic_text(path, text):
    if path.is_symlink():
        raise PackageError(f'symlink paths are unsupported: {path}')
    temporary = path.with_name(f'.{path.name}-{uuid.uuid4().hex}.tmp')
    temporary.write_text(text, encoding='utf-8')
    os.replace(temporary, path)


def _kill_group(process):
    try:
        if os.name == 'posix':
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except ProcessLookupError:
        pass
    process.wait()


def _execute(command, env, root, timeout, log, result):
    started = time.monotonic()
    try:
        with log.open('x', encoding='utf-8') as output:
            process = subprocess.Popen(command, cwd=root, env=env, shell=False,
                                       stdout=output, stderr=subprocess.STDOUT, start_new_session=os.name == 'posix')
            try:
                result['returnCode'] = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired as error:
                _kill_group(process)
                raise PackageError(f'timed out after {timeout:g} seconds') from error
            except BaseException:
                _kill_group(process)
                raise
            if result['returnCode'] != 0:
                raise PackageError(f'command returned exit status {result["returnCode"]}')
    finally:
        result['executionSeconds'] = time.monotonic() - started


def _artifacts(stage_id, attempt, outputs):
    return [{'stageId': stage_id, 'path': str(attempt / record['relativePath']), **record} for record in outputs]


def _write_report(output, report, started):
    report['finishedAt'] = _timestamp()
    report['wallSeconds'] = time.monotonic() - started
    _atomic_text(output / 'run.json', json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    lines = ['# Listening package', '']
    if report['status'] == 'completed':
        for label, path in report['deliverables'].items():
            escaped_label = label.replace('\\', '\\\\').replace('[', '\\[').replace(']', '\\]')
            lines.append(f'- [{escaped_label}]({quote(os.path.relpath(path, output), safe="/")})')
        if not report['deliverables']:
            lines.append('No listening deliverables were declared in this recipe.')
    else:
        lines.append('The latest run failed. See [run.json](run.json) for the stage and log path.')
    _atomic_text(output / 'listening.md', '\n'.join(lines) + '\n')


def run_recipe(recipe_path, output, *, root=ROOT, progress=print):
    """Run stages in order, reusing only receipts whose output content still matches.

    Recipes are trusted commands, not a sandbox. The runner restricts its own writes
    to build/ and never changes a previous stage attempt. Declared inputs and env
    must cover dependencies used by those commands.
    """
    root = Path(root).resolve()
    recipe_path = Path(recipe_path)
    try:
        recipe = json.loads(recipe_path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise PackageError(f'cannot read recipe: {error}') from error
    _validate_recipe(recipe)
    output = _prepare_output(output, root)
    started = time.monotonic()
    report = {'schemaVersion': 1, 'recipe': str(recipe_path.resolve()), 'recipeSha256': _sha256(recipe_path),
              'startedAt': _timestamp(), 'status': 'running', 'stages': [], 'artifacts': [], 'deliverables': {}}
    attempts = {}
    fingerprints = {}
    try:
        runtime = _runtime_fingerprint()
        for stage in recipe['stages']:
            stage_started = time.monotonic()
            result = {'id': stage['id'], 'status': 'running', 'cacheHit': False, 'executionSeconds': 0, 'artifacts': []}
            report['stages'].append(result)
            try:
                inputs = _inputs(stage, root, attempts)
                template_env = stage.get('env', {})
                env = os.environ.copy()
                env.update({name: _render(value, root, attempts) for name, value in template_env.items()})
                key_data = {'command': stage['command'], 'env': template_env, 'inputs': inputs, 'outputs': stage['outputs'],
                            'timeoutSeconds': stage['timeoutSeconds'], 'runtime': runtime,
                            'executable': _executable_fingerprint(_render(stage['command'][0], root, attempts), env, root)}
                key = hashlib.sha256(_json_bytes(key_data)).hexdigest()
                fingerprints[stage['id']] = key_data
                result['cacheKey'] = key
                base = output / 'cache' / stage['id'] / key
                _no_symlinks(output, base)
                cached = _cached_attempt(base, stage, key)
                if cached:
                    attempt, records = cached
                    result.update(status='reused', cacheHit=True)
                else:
                    attempt = base / f'attempt-{uuid.uuid4().hex}'
                    attempt.mkdir(parents=True)
                    result['attemptDirectory'] = str(attempt)
                    result['log'] = str(attempt / 'stage.log')
                    command = [_render(token, root, attempts, attempt) for token in stage['command']]
                    env.update({name: _render(value, root, attempts, attempt) for name, value in template_env.items()})
                    progress(f'{stage["id"]}: starting')
                    _execute(command, env, root, stage['timeoutSeconds'], attempt / 'stage.log', result)
                    records = _outputs(stage, attempt)
                    if _inputs(stage, root, attempts) != inputs:
                        raise PackageError('declared input content changed during execution')
                    if _executable_fingerprint(command[0], env, root) != key_data['executable']:
                        raise PackageError('executable changed during execution')
                    if _runtime_fingerprint() != runtime:
                        raise PackageError('runner or Python runtime changed during execution')
                    receipt = {'schemaVersion': 1, 'key': key, 'fingerprint': key_data, 'inputs': inputs, 'outputs': records, 'command': command,
                               'completedAt': _timestamp(), 'executionSeconds': result['executionSeconds']}
                    (attempt / 'success.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
                    result['status'] = 'completed'
                attempts[stage['id']] = attempt
                result.update(attemptDirectory=str(attempt), log=str(attempt / 'stage.log'),
                              artifacts=_artifacts(stage['id'], attempt, records))
                report['artifacts'].extend(result['artifacts'])
            except (PackageError, OSError, subprocess.SubprocessError) as error:
                result.update(status='failed', error=str(error))
                raise PackageError(f'{stage["id"]}: {error}') from error
            finally:
                result['wallSeconds'] = time.monotonic() - stage_started
                action = 'reused' if result['cacheHit'] else 'run' if result['status'] == 'completed' else 'failed'
                progress(f'{stage["id"]}: {action} ({result["wallSeconds"]:.3f}s)')
        for stage in recipe['stages']:
            fingerprint = fingerprints[stage['id']]
            if _inputs(stage, root, attempts) != fingerprint['inputs']:
                raise PackageError(f'{stage["id"]}: declared input content changed before package completion')
            env = os.environ.copy()
            env.update({name: _render(value, root, attempts) for name, value in stage.get('env', {}).items()})
            executable = _executable_fingerprint(_render(stage['command'][0], root, attempts), env, root)
            if executable != fingerprint['executable']:
                raise PackageError(f'{stage["id"]}: executable changed before package completion')
        if _runtime_fingerprint() != runtime:
            raise PackageError('runner or Python runtime changed before package completion')
        for label, template in recipe.get('deliverables', {}).items():
            path = Path(_render(template, root, attempts))
            artifact = next(item for item in report['artifacts'] if item['path'] == str(path))
            expected = {key: artifact[key] for key in ('type', 'sha256')}
            actual = _fingerprint_path(path)
            if any(actual[key] != value for key, value in expected.items()):
                raise PackageError(f'deliverable changed after its stage completed: {label}')
            report['deliverables'][label] = str(path)
        report['status'] = 'completed'
    except (PackageError, OSError, subprocess.SubprocessError) as error:
        report.update(status='failed', error=str(error), deliverables={})
        _write_report(output, report, started)
        raise PackageError(f'{error}; see {output / "run.json"}') from error
    _write_report(output, report, started)
    for label, path in report['deliverables'].items():
        progress(f'{label}: {path}')
    progress(f'Listening links: {output / "listening.md"}')
    return report
