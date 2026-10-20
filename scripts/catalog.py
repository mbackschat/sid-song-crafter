#!/usr/bin/env python3
"""Generate and validate the pinned, publication-scoped Explorer catalog."""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'https://github.com/mbackschat/sid-song-crafter'
MAX_PREPARED_BYTES = 25 * 1024 * 1024
MAX_SOURCE_BYTES = 256 * 1024 * 1024
MAX_JSON_BYTES = 2 * 1024 * 1024
IDENTIFIER = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
SHA256 = re.compile(r'[0-9a-f]{64}\Z')
PATH_COMPONENT = re.compile(r'[A-Za-z0-9_.-]+\Z')
FILENAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]*\Z')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def record(value, required, label, optional=()):
    require(type(value) is dict, f'{label}: expected object')
    require(not (set(value) - set(required) - set(optional)), f'{label}: unknown fields')
    require(not (set(required) - set(value)), f'{label}: missing fields')
    return value


def text(value, label):
    require(type(value) is str and bool(value.strip()), f'{label}: expected nonempty text')


def integer(value, label, minimum=1, maximum=None):
    require(type(value) is int and value >= minimum and (maximum is None or value <= maximum), f'{label}: invalid integer')


def number(value, label, minimum=0):
    require(type(value) in (int, float) and math.isfinite(value) and value >= minimum, f'{label}: invalid number')


def identifier(value, label):
    require(type(value) is str and IDENTIFIER.fullmatch(value), f'{label}: invalid identifier')


def source_path(value, label, fragment=False):
    text(value, label)
    parts = value.split('#')
    require(len(parts) == 1 or (fragment and len(parts) == 2 and re.fullmatch(r'[a-z0-9_-]+', parts[1])), f'{label}: invalid path fragment')
    components = parts[0].split('/')
    require(all(component not in ('', '.', '..') and PATH_COMPONENT.fullmatch(component) for component in components), f'{label}: unsafe path')
    return parts[0]


def filename(value):
    text(value, 'asset.filename')
    require(FILENAME.fullmatch(value), 'asset.filename: unsafe filename')


def assets(entry):
    yield from entry['files'].values()
    if 'externalReference' in entry:
        yield entry['externalReference']
    if 'stereo' in entry:
        yield from entry['stereo'].values()


def validate_index(value, curator=False):
    record(value, ('schemaVersion', 'source', 'entries', 'materials'), 'catalog')
    require(type(value['schemaVersion']) is int and value['schemaVersion'] == 1, 'catalog.schemaVersion: only version 1 is supported')
    source = record(value['source'], ('repository', 'revision'), 'source')
    require(source['repository'] == REPOSITORY, 'source.repository: unsupported repository')
    require(type(source['revision']) is str and re.fullmatch(r'[0-9a-f]{40}', source['revision']), 'source.revision: full Git commit required')
    require(type(value['entries']) is list and 0 < len(value['entries']) <= 1000, 'catalog.entries: expected bounded nonempty list')
    require(type(value['materials']) is list and len(value['materials']) <= 1000, 'catalog.materials: expected bounded list')
    ids = set()
    prepared_names = set()
    aliases = {}

    def validate_asset(asset, delivery):
        required = ('path', 'filename', 'transport', 'delivery') if curator else ('path', 'sha256', 'bytes', 'filename', 'transport', 'delivery')
        record(asset, required, 'asset')
        source_path(asset['path'], 'asset.path')
        filename(asset['filename'])
        require(asset['transport'] in ('raw', 'media'), 'asset.transport: unsupported transport')
        require(asset['delivery'] == delivery, 'asset.delivery: role does not permit this delivery')
        if not curator:
            require(type(asset['sha256']) is str and SHA256.fullmatch(asset['sha256']), 'asset.sha256: invalid SHA-256')
            integer(asset['bytes'], 'asset.bytes', maximum=MAX_SOURCE_BYTES)
            require(delivery != 'prepared' or asset['bytes'] <= MAX_PREPARED_BYTES, 'asset.size: prepared asset exceeds consumer limit')
        if delivery == 'prepared':
            require(asset['filename'] not in prepared_names, 'duplicate prepared filename')
            prepared_names.add(asset['filename'])
        identity = tuple(asset.get(key) for key in ('path', 'sha256', 'bytes', 'transport'))
        for key in ('path', 'filename'):
            alias_key = (key, asset[key])
            require(alias_key not in aliases or aliases[alias_key] == identity, 'asset alias: inconsistent fingerprint, path or transport')
            aliases[alias_key] = identity

    for entry in value['entries']:
        record(entry, ('id', 'title', 'description', 'durationSeconds', 'publication', 'files', 'target', 'rights', 'listening', 'analysis'), 'entry', ('externalReference', 'stereo'))
        identifier(entry['id'], 'entry.id')
        require(entry['id'] not in ids, 'duplicate catalog id')
        ids.add(entry['id'])
        for key in ('title', 'description'):
            text(entry[key], f'entry.{key}')
        number(entry['durationSeconds'], 'entry.durationSeconds')
        require(entry['durationSeconds'] > 0, 'entry.durationSeconds: must be positive')
        require(entry['publication'] == 'cleared', 'entry.publication: cleared required')
        record(entry['files'], ('sid', 'license'), 'entry.files', ('reference', 'notices'))
        require(('reference' in entry['files']) != ('externalReference' in entry), 'entry: exactly one reference is required')
        for asset in entry['files'].values():
            validate_asset(asset, 'prepared')
        if 'externalReference' in entry:
            validate_asset(entry['externalReference'], 'link-only')
        if 'stereo' in entry:
            record(entry['stereo'], ('sid', 'reference'), 'entry.stereo')
            for asset in entry['stereo'].values():
                validate_asset(asset, 'link-only')
        target = record(entry['target'], ('clock', 'model', 'sidCount', 'baseAddress', 'subtune', 'routing'), 'target', ('secondSidAddress',))
        require(target['clock'] == 'PAL' and target['model'] in ('MOS6581', 'MOS8580'), 'target: unsupported clock or model')
        require(type(target['sidCount']) is int and target['sidCount'] in (1, 2), 'target.sidCount: unsupported count')
        require(type(target['baseAddress']) is int and target['baseAddress'] == 54272 and type(target['subtune']) is int and target['subtune'] == 1, 'target: unsupported address or subtune')
        if target['sidCount'] == 1:
            require('secondSidAddress' not in target, 'target.secondSidAddress: mono has no second SID')
            require(target['routing'] == 'mono', 'target.routing: mono routing required')
        else:
            require(type(target.get('secondSidAddress')) is int and target['secondSidAddress'] == 54304, 'target.secondSidAddress: expected 54304')
            require(target['routing'] == 'sid-a-left-sid-b-right', 'target.routing: stereo routing required')
        rights = record(entry['rights'], ('license', 'attribution', 'sourcePath', 'licensePath'), 'rights')
        for key in ('license', 'attribution'):
            text(rights[key], f'rights.{key}')
        source_path(rights['sourcePath'], 'rights.sourcePath', True)
        source_path(rights['licensePath'], 'rights.licensePath', True)
        require(rights['licensePath'] == entry['files']['license']['path'], 'rights.licensePath: must own prepared license')
        listening = record(entry['listening'], ('status', 'scope', 'sourcePath'), 'listening')
        for key in ('status', 'scope'):
            text(listening[key], f'listening.{key}')
        source_path(listening['sourcePath'], 'listening.sourcePath', True)
        analysis_fields = ('schemaVersion', 'subtune', 'clock', 'timeBasis', 'annotations') if curator else ('schemaVersion', 'sidSha256', 'subtune', 'clock', 'timeBasis', 'annotations')
        analysis = record(entry['analysis'], analysis_fields, 'analysis')
        require(type(analysis['schemaVersion']) is int and analysis['schemaVersion'] == 1 and type(analysis['subtune']) is int and analysis['subtune'] == target['subtune'] and analysis['clock'] == target['clock'] and analysis['timeBasis'] == 'seconds-from-init', 'analysis identity: incompatible target')
        if not curator:
            require(analysis['sidSha256'] == entry['files']['sid']['sha256'], 'analysis identity: SID fingerprint differs')
        require(type(analysis['annotations']) is list and len(analysis['annotations']) <= 10000, 'analysis.annotations: expected bounded list')
        annotation_ids = set()
        for annotation in analysis['annotations']:
            record(annotation, ('id', 'startSeconds', 'endSeconds', 'title', 'description', 'evidenceLevel', 'voices', 'sourcePath'), 'annotation')
            identifier(annotation['id'], 'annotation.id')
            require(annotation['id'] not in annotation_ids, 'duplicate annotation id')
            annotation_ids.add(annotation['id'])
            for key in ('startSeconds', 'endSeconds'):
                number(annotation[key], f'annotation.{key}')
            require(annotation['startSeconds'] < annotation['endSeconds'] <= entry['durationSeconds'], 'annotation.span: outside performance')
            for key in ('title', 'description'):
                text(annotation[key], f'annotation.{key}')
            require(annotation['evidenceLevel'] in ('verified', 'derived', 'interpretation'), 'annotation.evidenceLevel: unsupported level')
            voices = annotation['voices']
            require(type(voices) is list and 0 < len(voices) <= target['sidCount'] * 3 and all(type(voice) is int and 1 <= voice <= target['sidCount'] * 3 for voice in voices) and len(set(voices)) == len(voices), 'annotation.voices: invalid physical voices')
            source_path(annotation['sourcePath'], 'annotation.sourcePath', True)
    for material in value['materials']:
        record(material, ('id', 'title', 'description', 'sourcePath', 'publication'), 'material')
        identifier(material['id'], 'material.id')
        require(material['id'] not in ids, 'duplicate catalog id')
        ids.add(material['id'])
        for key in ('title', 'description'):
            text(material[key], f'material.{key}')
        source_path(material['sourcePath'], 'material.sourcePath', True)
        require(material['publication'] == 'materials-only', 'material.publication: materials-only required')
    return value


class GitSource:
    def __init__(self, root, revision):
        self.root = root
        self.revision = revision
        self.cache = {}

    def _git(self, *args):
        try:
            return subprocess.run(['git', *args], cwd=self.root, check=True, capture_output=True, timeout=10).stdout
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            raise ValueError(f'pinned Git read failed: {args[0]}') from error

    def blob(self, path):
        source_path(path, 'source.path')
        if path not in self.cache:
            listing = self._git('ls-tree', '-l', self.revision, '--', path).decode('utf-8').rstrip('\n')
            match = re.fullmatch(r'100644 blob ([0-9a-f]{40})\s+(\d+)\t' + re.escape(path), listing)
            require(match is not None, f'source.path: missing regular pinned blob: {path}')
            require(int(match[2]) <= MAX_SOURCE_BYTES, f'source.path: blob exceeds size bound: {path}')
            data = self._git('cat-file', 'blob', match[1])
            require(not data.startswith(b'version https://git-lfs.github.com/spec/v1\n'), f'source.path: unresolved LFS pointer: {path}')
            require(len(data) == int(match[2]), f'source.path: Git size mismatch: {path}')
            self.cache[path] = data
        return self.cache[path]

    def owner(self, path):
        name = source_path(path, 'owner.path', True)
        data = self.blob(name)
        if '#' in path:
            require(name.endswith('.md'), f'owner fragment: Markdown required: {path}')
            anchors = set()
            occurrences = {}
            fenced = False
            for line in data.decode('utf-8').splitlines():
                if re.match(r'^\s*(```|~~~)', line):
                    fenced = not fenced
                if fenced:
                    continue
                heading = re.match(r'^#{1,6}\s+(.+?)\s*#*$', line)
                if heading:
                    slug = unicodedata.normalize('NFC', heading[1]).lower()
                    slug = re.sub(r'[^\w\- ]', '', slug).replace(' ', '-')
                    count = occurrences.get(slug, 0)
                    occurrences[slug] = count + 1
                    anchors.add(slug if not count else f'{slug}-{count}')
            require(path.split('#')[1] in anchors, f'owner fragment: heading not found: {path}')
        return data


def verify_manifest(value, parent, fingerprints):
    if type(value) is dict:
        path = value.get('path')
        if path is None and type(value.get('filename')) is str:
            path = f'{parent}/{value["filename"]}'
        if type(path) is str and path in fingerprints and 'sha256' in value and 'bytes' in value:
            asset = fingerprints[path]
            require(value['sha256'] == asset['sha256'] and value['bytes'] == asset['bytes'], f'manifest fingerprint: mismatch for {path}')
        for child in value.values():
            verify_manifest(child, parent, fingerprints)
    elif type(value) is list:
        for child in value:
            verify_manifest(child, parent, fingerprints)


def verify_sid(data, target):
    require(len(data) >= 124 and data[:4] == b'PSID', 'SID target: PSID header required')
    version = int.from_bytes(data[4:6], 'big')
    flags = int.from_bytes(data[118:120], 'big')
    model = 1 if target['model'] == 'MOS6581' else 2
    require(version in (2, 3) and int.from_bytes(data[14:16], 'big') >= target['subtune'], 'SID target: unsupported version or subtune')
    require((flags >> 2) & 3 == 1 and (flags >> 4) & 3 == model, 'SID target: declared clock or chip model differs from PSID')
    if target['sidCount'] == 1:
        require(data[122:124] == b'\0\0', 'SID target: declared mono differs from PSID chip addresses')
    else:
        require(version == 3 and data[122:124] == b'\x42\0' and (flags >> 6) & 3 == model, 'SID target: declared stereo differs from PSID chip addresses or model')


def generate(curator, root=ROOT):
    validate_index(curator, curator=True)
    result = copy.deepcopy(curator)
    source = GitSource(root, result['source']['revision'])
    require(source._git('cat-file', '-t', source.revision) == b'commit\n', 'source.revision: expected Git commit')
    for entry in result['entries']:
        for asset in assets(entry):
            data = source.blob(asset['path'])
            asset['sha256'] = hashlib.sha256(data).hexdigest()
            asset['bytes'] = len(data)
            require(asset['transport'] == 'raw', 'ordinary pinned Git blobs require raw transport; media needs materialized LFS support')
        verify_sid(source.blob(entry['files']['sid']['path']), entry['target'])
        if 'stereo' in entry:
            verify_sid(source.blob(entry['stereo']['sid']['path']), {**entry['target'], 'sidCount': 2})
        entry['analysis']['sidSha256'] = entry['files']['sid']['sha256']
        for path in (entry['rights']['sourcePath'], entry['rights']['licensePath'], entry['listening']['sourcePath']):
            source.owner(path)
        for annotation in entry['analysis']['annotations']:
            source.owner(annotation['sourcePath'])
        listening_path = entry['listening']['sourcePath'].split('#')[0]
        if listening_path.endswith('.json'):
            manifest = decode(source.blob(listening_path).decode('utf-8'))
            verify_manifest(manifest, listening_path.rsplit('/', 1)[0], {asset['path']: asset for asset in assets(entry)})
    for material in result['materials']:
        source.owner(material['sourcePath'])
    return validate_index(result)


def decode(value):
    def unique(pairs):
        result = {}
        for key, item in pairs:
            require(key not in result, f'duplicate JSON key: {key}')
            result[key] = item
        return result
    def reject_constant(value):
        raise ValueError(f'invalid JSON number: {value}')
    return json.loads(value, object_pairs_hook=unique, parse_constant=reject_constant)


def read_json(path):
    require(path.stat().st_size <= MAX_JSON_BYTES, 'catalog JSON exceeds size bound')
    return decode(path.read_text(encoding='utf-8'))


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('generate', 'check'))
    parser.add_argument('--input', type=Path, default=ROOT / 'samples/catalog/curator.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'samples/catalog/index.json')
    args = parser.parse_args()
    try:
        expected = encode(generate(read_json(args.input)))
        if args.command == 'generate':
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(expected)
        else:
            validate_index(read_json(args.output))
            require(args.output.read_bytes() == expected, 'generated index differs; run scripts/catalog.py generate')
        print(f'catalog {args.command}: {len(expected)} bytes, SHA-256 {hashlib.sha256(expected).hexdigest()}')
        return 0
    except (OSError, ValueError) as error:
        print(f'catalog: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
