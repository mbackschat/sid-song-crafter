#!/usr/bin/env python3
"""Validate the instrument library and generate its index.

The contract is docs/proposals/instrument-library.md. Records live at
songs/instruments/<id>@<version>.json and listener verdicts at
songs/instruments/verdicts/<verdict-id>.json. Everything a selector could
mistake for stored evidence (verdict lists, evidence level, accepted partners,
reusability, embedding locations) is computed here, never read from a record.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = Path('songs/instruments')
INDEX = LIBRARY / 'index.json'
IDENTIFIER = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
VERSIONED = re.compile(r'([a-z]+\.[a-z0-9]+(?:-[a-z0-9]+)*)@([1-9][0-9]*)\Z')
VERDICT_ID = re.compile(r'v-[a-z0-9]+(?:-[a-z0-9]+)*\Z')
NOTE = re.compile(r'[A-G](?:#|b)?-?[0-9]\Z')
PROBE = re.compile(r'probe-level-v[1-9][0-9]*\b')
# Datasheet envelope times in ms, before clock scaling (skills/c64-sid/references/sid-chip-spec.md).
ATTACK_MS = (2, 8, 16, 24, 38, 56, 68, 80, 100, 250, 500, 800, 1000, 3000, 5000, 8000)
RELEASE_MS = (6, 24, 48, 72, 114, 168, 204, 240, 300, 750, 1500, 2400, 3000, 9000, 15000, 24000)

ROLES = ('lead', 'countermelody', 'harmony', 'chord', 'bass', 'percussion', 'effect')
KNOWN_BASES = ('intent', 'measured', 'tested')
POSITIVE = ('accepted', 'preferred')
COMPARATIVE = ('preferred', 'not-preferred', 'no-preference')
RESULTS = ('accepted', 'qualified', 'rejected') + COMPARATIVE
INTERFACE_UNSETTLED = 'not-established'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, required, label, optional=()):
    require(type(value) is dict, f'{label}: expected object')
    require(not (set(value) - set(required) - set(optional)), f'{label}: unknown fields {sorted(set(value) - set(required) - set(optional))}')
    require(not (set(required) - set(value)), f'{label}: missing fields {sorted(set(required) - set(value))}')
    return value


def text(value, label):
    require(type(value) is str and bool(value.strip()), f'{label}: expected nonempty text')


def one_of(value, choices, label):
    require(value in choices, f'{label}: expected one of {list(choices)}')


def integer(value, label, minimum=0, maximum=None):
    require(type(value) is int and value >= minimum and (maximum is None or value <= maximum), f'{label}: invalid integer')


def number(value, label):
    require(type(value) in (int, float) and math.isfinite(value), f'{label}: invalid number')


def path(value, label, root):
    text(value, label)
    target = value.split('#', 1)[0]
    require('..' not in Path(target).parts and not Path(target).is_absolute(), f'{label}: unsafe path')
    require((root / target).is_file(), f'{label}: missing file {target}')


def subset(values, choices, label, nonempty=True):
    require(type(values) is list and (values or not nonempty) and len(set(values)) == len(values), f'{label}: expected a list without repeats')
    for item in values:
        one_of(item, choices, label)


def claim(value, label, root, check=None, known_only=False):
    require(type(value) is dict, f'{label}: expected object')
    if value.get('basis') == 'unknown' and not known_only:
        fields(value, ('basis',), label)
        return None
    fields(value, ('value', 'basis', 'detail'), label, ('record',) + (('startsAfterUpdates',) if known_only else ()))
    one_of(value['basis'], KNOWN_BASES, f'{label}.basis')
    text(value['detail'], f'{label}.detail')
    if 'record' in value:
        path(value['record'], f'{label}.record', root)
    if check:
        check(value['value'], f'{label}.value')
    return value


def validate_interface(value, label, root):
    fields(value, ('scoreSupplies', 'pitchResponse', 'parameters', 'scoreOwned', 'onNewNote', 'onTie', 'afterGateOff', 'lifetime', 'pitchSettlesAfterUpdates', 'state'), label)
    subset(value['scoreSupplies'], ('pitch', 'onset', 'gateOff', 'tie'), f'{label}.scoreSupplies')
    one_of(value['pitchResponse'], ('absolute', 'percussion'), f'{label}.pitchResponse')
    require(type(value['parameters']) is list, f'{label}.parameters: expected list')
    for index, parameter in enumerate(value['parameters']):
        item = f'{label}.parameters[{index}]'
        fields(parameter, ('name', 'type'), item, ('range', 'values', 'default'))
        text(parameter['name'], f'{item}.name')
        one_of(parameter['type'], ('int', 'pitch', 'enum'), f'{item}.type')
    require(type(value['scoreOwned']) is list, f'{label}.scoreOwned: expected list')
    for index, item in enumerate(value['scoreOwned']):
        text(item, f'{label}.scoreOwned[{index}]')
    one_of(value['onNewNote'], ('retrigger', 'hard-restart', 'test-frame', 'legato', INTERFACE_UNSETTLED), f'{label}.onNewNote')
    one_of(value['onTie'], ('keep-envelope-and-program', 'restart-program', INTERFACE_UNSETTLED), f'{label}.onTie')
    one_of(value['afterGateOff'], ('release-only', 'program-continues', INTERFACE_UNSETTLED), f'{label}.afterGateOff')
    lifetime = value['lifetime']
    if type(lifetime) is dict:
        integer(fields(lifetime, ('updates',), f'{label}.lifetime')['updates'], f'{label}.lifetime.updates', 1)
    else:
        one_of(lifetime, ('until-release-ends', 'until-next-note', INTERFACE_UNSETTLED), f'{label}.lifetime')
    claim(value['pitchSettlesAfterUpdates'], f'{label}.pitchSettlesAfterUpdates', root, lambda v, l: integer(v, l, 1))
    require(type(value['state']) is list, f'{label}.state: expected list')
    for index, item in enumerate(value['state']):
        fields(item, ('field', 'scope'), f'{label}.state[{index}]')
        text(item['field'], f'{label}.state[{index}].field')
        one_of(item['scope'], ('note', 'voice', 'instrument', 'chip'), f'{label}.state[{index}].scope')


def settled(interface):
    return all(interface[key] != INTERFACE_UNSETTLED for key in ('onNewNote', 'onTie', 'afterGateOff', 'lifetime'))


def validate_resources(value, label):
    fields(value, ('voices', 'coupling', 'filter', 'masterVolume', 'chipModels', 'clocks', 'updateRate'), label)
    one_of(value['voices'], (1, 2, 3), f'{label}.voices')
    if type(value['coupling']) is dict:
        fields(value['coupling'], ('kind', 'partner'), f'{label}.coupling')
        one_of(value['coupling']['kind'], ('sync', 'ring'), f'{label}.coupling.kind')
        one_of(value['coupling']['partner'], ('preceding-oscillator',), f'{label}.coupling.partner')
    else:
        one_of(value['coupling'], ('none',), f'{label}.coupling')
    one_of(value['filter'], ('none', 'owner', 'routed'), f'{label}.filter')
    one_of(value['masterVolume'], ('none', 'writes'), f'{label}.masterVolume')
    subset(value['chipModels'], ('MOS6581', 'MOS8580'), f'{label}.chipModels')
    subset(value['clocks'], ('PAL', 'NTSC'), f'{label}.clocks')
    rate = value['updateRate']
    if type(rate) is dict:
        fields(rate, ('hz', 'source'), f'{label}.updateRate')
        number(rate['hz'], f'{label}.updateRate.hz')
        one_of(rate['source'], ('cia',), f'{label}.updateRate.source')
    else:
        one_of(rate, ('frame',), f'{label}.updateRate')


def attack_category(milliseconds):
    return 'hard' if milliseconds <= 8 else 'medium' if milliseconds <= 24 else 'soft'


def release_category(milliseconds):
    return 'cut' if milliseconds <= 24 else 'short' if milliseconds <= 114 else 'medium' if milliseconds <= 300 else 'long'


def probe_values(keys, silent_allowed=False):
    def check(value, label):
        fields(value, keys, label)
        for key in keys:
            # null is a measured silent window (a drum that has decayed before the sustain window), not a missing value.
            if not (silent_allowed and value[key] is None):
                number(value[key], f'{label}.{key}')
    return check


def validate_character(value, label, root):
    fields(value, ('summary', 'waveforms', 'attack', 'body', 'release', 'level', 'brightness', 'motion'), label, ('envelope',))
    text(value['summary'], f'{label}.summary')
    claim(value['waveforms'], f'{label}.waveforms', root, lambda v, l: subset(v, ('triangle', 'saw', 'pulse', 'noise'), l))
    attack = claim(value['attack'], f'{label}.attack', root, lambda v, l: one_of(v, ('soft', 'medium', 'hard', 'staged'), l))
    claim(value['body'], f'{label}.body', root, lambda v, l: one_of(v, ('static', 'moving-pulse', 'moving-filter', 'arpeggio', 'pitch-animated', 'waveform-sequence', 'noise'), l))
    release = claim(value['release'], f'{label}.release', root, lambda v, l: one_of(v, ('cut', 'short', 'medium', 'long'), l))
    for key, check in (('level', probe_values(('onsetDb', 'sustainDb'), silent_allowed=True)), ('brightness', probe_values(('onset', 'body')))):
        measured = claim(value[key], f'{label}.{key}', root, check)
        # Probe values compare only within one probe version, so the version must be readable from the claim.
        require(measured is None or (measured['basis'] == 'measured' and PROBE.match(measured['detail'])), f'{label}.{key}: measured detail must start with the probe version')
    if 'envelope' in value:
        envelope = fields(value['envelope'], ('attack', 'decay', 'sustain', 'release', 'attackMs', 'releaseMs'), f'{label}.envelope')
        for key in ('attack', 'decay', 'sustain', 'release'):
            integer(envelope[key], f'{label}.envelope.{key}', 0, 15)
        require(envelope['attackMs'] == ATTACK_MS[envelope['attack']], f'{label}.envelope.attackMs: does not match the attack nibble')
        require(envelope['releaseMs'] == RELEASE_MS[envelope['release']], f'{label}.envelope.releaseMs: does not match the release nibble')
        # A measured value replaces an intent claim on the same trait.
        require(attack is not None and attack['basis'] == 'measured', f'{label}.attack: must be measured when the envelope is known')
        require(release is not None and release['basis'] == 'measured', f'{label}.release: must be measured when the envelope is known')
        require(attack['value'] == 'staged' or attack['value'] == attack_category(envelope['attackMs']), f'{label}.attack: category contradicts the threshold for {envelope["attackMs"]} ms')
        require(release['value'] == release_category(envelope['releaseMs']), f'{label}.release: category contradicts the threshold for {envelope["releaseMs"]} ms')
    require(type(value['motion']) is list, f'{label}.motion: expected list')
    for index, motion in enumerate(value['motion']):
        item = f'{label}.motion[{index}]'
        claim(motion, item, root, lambda v, l: one_of(v, ('pwm', 'vibrato', 'delayed-vibrato', 'glide', 'pitch-bend', 'arpeggio', 'filter-sweep', 'waveform-change'), l), known_only=True)
        if 'startsAfterUpdates' in motion:
            integer(motion['startsAfterUpdates'], f'{item}.startsAfterUpdates')


def note_range(value, label):
    fields(value, ('low', 'high'), label)
    require(all(type(value[key]) is str and NOTE.fullmatch(value[key]) for key in ('low', 'high')), f'{label}: expected note names such as A3')


def program_identity(program, label, root):
    """Return the bytes that define a program; a tracker label alone never makes a new version."""
    target = root / program['file']
    if 'record' not in program:
        data = target.read_bytes()
        require('sha256' not in program or hashlib.sha256(data).hexdigest() == program['sha256'], f'{label}.sha256: does not match the file')
        return hashlib.sha256(data).hexdigest()
    value = json.loads(target.read_text())
    for key in program['record'].split('.'):
        require(type(value) is dict and key in value, f'{label}: program record {program["record"]} not found in {program["file"]}')
        value = value[key]
    require(type(value) is dict, f'{label}: program record is not an instrument')
    return instrument_identity(value)


def instrument_identity(instrument):
    return json.dumps({key: item for key, item in instrument.items() if key != 'name'}, sort_keys=True)


def validate_record(value, root):
    label = f'record {value.get("id")}@{value.get("version")}'
    fields(value, ('id', 'version', 'name', 'program', 'interface', 'resources', 'character', 'fit', 'provenance'), label, ('nativeName',))
    require(type(value['id']) is str and VERSIONED.fullmatch(f'{value["id"]}@1'), f'{label}.id: expected <role>.<descriptor>')
    integer(value['version'], f'{label}.version', 1)
    text(value['name'], f'{label}.name')
    if 'nativeName' in value:
        require(type(value['nativeName']) is str and 0 < len(value['nativeName']) <= 8, f'{label}.nativeName: at most 8 characters')
    program = fields(value['program'], ('engine', 'file'), f'{label}.program', ('record', 'sha256'))
    text(program['engine'], f'{label}.program.engine')
    path(program['file'], f'{label}.program.file', root)
    validate_interface(value['interface'], f'{label}.interface', root)
    validate_resources(value['resources'], f'{label}.resources')
    validate_character(value['character'], f'{label}.character', root)
    fit = fields(value['fit'], ('roles', 'avoid'), f'{label}.fit', ('range',))
    subset(fit['roles'], ROLES, f'{label}.fit.roles')
    # The id prefix is a role so that a descriptive family name cannot suggest a role the record does not serve.
    require(value['id'].split('.')[0] in fit['roles'], f'{label}.id: prefix must be one of fit.roles')
    if 'range' in fit:
        claim(fit['range'], f'{label}.fit.range', root, note_range)
    require(type(fit['avoid']) is list, f'{label}.fit.avoid: expected list')
    for index, avoid in enumerate(fit['avoid']):
        item = f'{label}.fit.avoid[{index}]'
        fields(avoid, ('condition',), item, ('verdict', 'record'))
        text(avoid['condition'], f'{item}.condition')
        require('verdict' in avoid or 'record' in avoid, f'{item}: avoid needs a verdict or record')
        if 'record' in avoid:
            path(avoid['record'], f'{item}.record', root)
    provenance = fields(value['provenance'], ('origin', 'sourceWork', 'card', 'rights'), f'{label}.provenance', ('composer', 'derivedFrom'))
    one_of(provenance['origin'], ('original', 'derived', 'decoded', 'upstream'), f'{label}.provenance.origin')
    text(provenance['sourceWork'], f'{label}.provenance.sourceWork')
    path(provenance['card'], f'{label}.provenance.card', root)
    text(provenance['rights'], f'{label}.provenance.rights')
    return program_identity(program, f'{label}.program', root)


def strings(value):
    if type(value) is str:
        yield value
    elif type(value) is dict:
        for item in value.values():
            yield from strings(item)
    elif type(value) is list:
        for item in value:
            yield from strings(item)


def quote_in(quote, target):
    content = target.read_text()
    if target.suffix == '.json':
        return any(quote in item for item in strings(json.loads(content)))
    return quote in content


def validate_verdict(value, root):
    label = f'verdict {value.get("id")}'
    fields(value, ('id', 'attribution', 'members', 'context', 'result', 'quote', 'record'), label, ('comparedWith',))
    require(type(value['id']) is str and VERDICT_ID.fullmatch(value['id']), f'{label}.id: expected v-<kebab-case>')
    one_of(value['attribution'], ('isolated', 'group'), f'{label}.attribution')
    require(type(value['members']) is list and len(set(value['members'])) == len(value['members']), f'{label}.members: expected a list without repeats')
    for item in value['members']:
        require(type(item) is str and VERSIONED.fullmatch(item), f'{label}.members: expected <id>@<version>')
    compared = value.get('comparedWith', [])
    require(type(compared) is list and ('comparedWith' not in value or compared), f'{label}.comparedWith: expected a nonempty list')
    for index, item in enumerate(compared):
        if type(item) is dict:
            text(fields(item, ('description',), f'{label}.comparedWith[{index}]')['description'], f'{label}.comparedWith[{index}].description')
        else:
            require(type(item) is str and VERSIONED.fullmatch(item), f'{label}.comparedWith[{index}]: expected <id>@<version> or a description')
    one_of(value['result'], RESULTS, f'{label}.result')
    require(value['result'] not in COMPARATIVE or compared, f'{label}: {value["result"]} needs comparedWith')
    named = set(value['members']) | {item for item in compared if type(item) is str}
    require(named, f'{label}: names no library version as member or comparison')
    context = fields(value['context'], ('work', 'roles', 'tempoBpm', 'meter', 'moodBrief', 'material'), f'{label}.context')
    text(context['work'], f'{label}.context.work')
    require(type(context['roles']) is dict and set(context['roles']) <= named, f'{label}.context.roles: keys must be named versions')
    for item in context['roles'].values():
        text(item, f'{label}.context.roles')
    require(context['tempoBpm'] is None or (type(context['tempoBpm']) in (int, float) and context['tempoBpm'] > 0), f'{label}.context.tempoBpm: positive number or null')
    require(context['meter'] is None or (type(context['meter']) is str and re.fullmatch(r'[1-9][0-9]*/[1-9][0-9]*', context['meter'])), f'{label}.context.meter: such as 3/4, or null')
    require(context['moodBrief'] is None or (type(context['moodBrief']) is str and context['moodBrief'].strip()), f'{label}.context.moodBrief: text or null')
    one_of(context['material'], ('excerpt', 'phrase', 'complete'), f'{label}.context.material')
    path(value['record'], f'{label}.record', root)
    if value['quote'] is not None:
        text(value['quote'], f'{label}.quote')
        require(quote_in(value['quote'], root / value['record'].split('#', 1)[0]), f'{label}.quote: not found verbatim in {value["record"]}')
    return named


def read(path_):
    return json.loads(path_.read_text())


def load(root=ROOT):
    """Load and validate every record and verdict; raise ValueError on the first violation."""
    records, identities, verdicts = {}, {}, {}
    for target in sorted((root / LIBRARY).glob('*.json')):
        if target.name == INDEX.name:
            continue
        value = read(target)
        key = f'{value.get("id")}@{value.get("version")}'
        require(target.name == f'{key}.json', f'{target.name}: file name must be {key}.json')
        identity = validate_record(value, root)
        require(identity not in identities, f'record {key}: identical program to {identities.get(identity)}; byte-identical programs are one version')
        identities[identity] = key
        records[key] = value
    for target in sorted((root / LIBRARY / 'verdicts').glob('*.json')):
        value = read(target)
        require(target.name == f'{value.get("id")}.json', f'{target.name}: file name must be {value.get("id")}.json')
        for item in validate_verdict(value, root):
            require(item in records, f'verdict {value["id"]}: unknown instrument {item}')
        verdicts[value['id']] = value
    for key, value in records.items():
        for avoid in value['fit']['avoid']:
            require('verdict' not in avoid or avoid['verdict'] in verdicts, f'record {key}.fit.avoid: unknown verdict {avoid.get("verdict")}')
    return records, verdicts


def occurrences(records, root):
    """Every arrangement file embedding each record's program, found by program bytes."""
    by_identity = {program_identity(value['program'], key, root): key for key, value in records.items() if 'record' in value['program']}
    found = {key: [] for key in records}
    for target in sorted((root / 'songs').rglob('*.json')):
        if LIBRARY in target.relative_to(root).parents:
            continue
        try:
            value = read(target)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if type(value) is not dict or value.get('format') != 'sidwizard-arrangement-v1':
            continue
        for name, instrument in sorted(value.get('instruments', {}).items()):
            key = by_identity.get(instrument_identity(instrument))
            if key:
                found[key].append(f'{target.relative_to(root).as_posix()}#instruments.{name}')
    return found


def side(key, verdict):
    if key in verdict['members']:
        return 'member'
    return 'rejected-alternative' if verdict['result'] == 'preferred' else 'preferred-alternative' if verdict['result'] == 'not-preferred' else 'alternative'


def index(records, verdicts, root=ROOT):
    embedded = occurrences(records, root)
    instruments = {}
    for key, value in records.items():
        named = [item for item in verdicts.values() if key in item['members'] or key in item.get('comparedWith', [])]
        accepted = [item for item in named if key in item['members'] and item['result'] in POSITIVE]
        character = value['character']
        instruments[key] = {
            'name': value['name'], 'summary': character['summary'], 'roles': value['fit']['roles'],
            'engine': value['program']['engine'],
            'resources': {name: value['resources'][name] for name in ('voices', 'coupling', 'filter', 'chipModels', 'clocks')},
            'level': character['level'].get('value'), 'brightness': character['brightness'].get('value'),
            'verdicts': [{'id': item['id'], 'side': side(key, item), 'result': item['result'], 'attribution': item['attribution'], 'work': item['context']['work']} for item in named],
            'evidenceLevel': 'listening-reviewed' if named else 'rendered-experiment' if character['level']['basis'] == 'measured' else 'proposed-experiment',
            'acceptedWith': sorted({member for item in accepted for member in item['members'] if member != key}),
            'reusable': settled(value['interface']) and any(item['context']['work'] != value['provenance']['sourceWork'] for item in accepted),
            'occurrences': embedded[key],
        }
    return {'contract': 'docs/proposals/instrument-library.md', 'instruments': instruments}


def encode(value):
    return json.dumps(value, indent=2, ensure_ascii=False) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('command', choices=('check', 'index'), help='check: validate and require a current index; index: validate and rewrite the index')
    args = parser.parse_args()
    expected = encode(index(*load(ROOT), ROOT))
    if args.command == 'index':
        (ROOT / INDEX).write_text(expected)
        return
    current = (ROOT / INDEX).read_text() if (ROOT / INDEX).is_file() else None
    if current != expected:
        sys.exit(f'{INDEX} is stale; run: python3 scripts/instrument_library.py index')


if __name__ == '__main__':
    main()
