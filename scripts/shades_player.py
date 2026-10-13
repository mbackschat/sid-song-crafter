"""Compute ordered Shades stores from editable score and instrument descriptions."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

from shades_programs import (Gate, Programs, RowKind, State, advance_filter,
                            advance_portamento, advance_pulse, advance_vibrato,
                            consume_row, load_block)
from verify_player import require


spec = importlib.util.spec_from_file_location('shades_score', Path(__file__).with_name('describe-shades-score.py'))
score_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score_module)


class Player:
    def __init__(self, score, description):
        require(type(description) is dict and description.get('format') == 'sid-shades-programs-v1',
                'Unsupported Shades programs format')
        require({'programs', 'preloaded'} <= description.keys(), 'Programs and preloaded state are required')
        expanded = score_module.expand_score(score)
        self.programs = Programs.from_dict(description['programs'])
        self.state = State.from_dict(description['preloaded'])
        self.stop_call = score['range']['stopCall']
        self.selections = {row['call']: row for row in expanded['selections']}
        self.rows = {}
        for command in expanded['commands']:
            self.rows.setdefault(command['call'], []).append(command)
        require(all(row['instrument'] in self.programs.blocks for row in expanded['selections']),
                'Score selects an undefined instrument block')
        self.block = None
        self.fade_interval = 0
        self.fade_countdown = 0
        self.fade_volume = 0
        self.tick = -1
        self.writes = []

    def write(self, address, value):
        self.writes.append(dict(phase='play', tick=self.tick, address=address, value=value))

    def word(self, address, value):
        self.write(address, value & 255)
        self.write(address + 1, value >> 8)

    def select(self, selection):
        self.block = self.programs.blocks[selection['instrument']]
        load_block(self.state, self.block)
        self.write(0xdc05, selection['timerHigh'])
        fade = selection['fade']
        kind = score_module.FadeKind(fade['kind'])
        if kind == score_module.FadeKind.CANCEL:
            self.fade_interval = self.fade_countdown = 0
        elif kind == score_module.FadeKind.START:
            self.fade_interval = fade['rowInterval']
            self.fade_countdown = self.fade_interval - 1
            self.fade_volume = self.state.filter.mode_volume

    def advance_fade(self):
        if not self.fade_interval:
            return
        if self.fade_countdown:
            self.fade_countdown -= 1
        else:
            self.fade_countdown = self.fade_interval - 1
            if self.fade_volume & 15:
                self.fade_volume -= 1
                self.write(0xd418, self.fade_volume)

    def write_filter(self):
        filt = self.state.filter
        self.write(0xd415, filt.cutoff_low)
        self.write(0xd416, filt.cutoff_high)
        self.write(0xd417, filt.routing)
        if not self.fade_interval:
            self.write(0xd418, filt.mode_volume)

    def write_voice(self, index):
        voice = self.state.voices[index]
        base = 0xd400 + index * 7
        # Source writer $76E3 emits voice one's SR before the voice-two body.
        if index == 1:
            self.write(0xd406, self.state.voices[0].sustain_release)
        self.word(base, voice.frequency)
        self.word(base + 2, voice.pulse_width)
        self.write(base + 5, voice.attack_decay)
        if index != 0:
            self.write(base + 6, voice.sustain_release)
        self.write(base + 4, voice.control)
        self.write_filter()

    def step(self):
        self.tick += 1
        if self.tick == self.stop_call:
            for address in (0xd404, 0xd40b, 0xd412, 0xd418):
                self.write(address, 0)
            return
        require(self.tick < self.stop_call, 'Player has already stopped')
        if self.tick == 0:
            self.select(self.selections[0])
            return
        for advance in (advance_portamento, advance_vibrato):
            for voice, word in advance(self.state):
                self.word(0xd400 + voice * 7, word)
        if advance_filter(self.state):
            self.write(0xd415, self.state.filter.cutoff_low)
            self.write(0xd416, self.state.filter.cutoff_high)
        for voice, width in advance_pulse(self.state):
            self.word(0xd402 + voice * 7, width)
        commands = self.rows.get(self.tick)
        if commands is None:
            return
        # The executed row path at $7467 advances the old fade before loading a new block.
        self.advance_fade()
        if self.tick in self.selections:
            self.select(self.selections[self.tick])
        for command in commands:
            voice = command['voice'] - 1
            kind = RowKind(command['kind'])
            result = consume_row(self.state, self.block, voice, kind,
                                 note_index=command.get('pitchTableIndex'),
                                 gate=Gate(command.get('gate', 'on')), programs=self.programs)
            if result.initial_control is not None:
                self.write(0xd404 + voice * 7, result.initial_control)
            if result.write_voice:
                self.write_voice(voice)


def compute(score, programs, *, calls=None, include_stop=False):
    """Compute a bounded traversal, optionally followed by an authored silent stop.

    No reference payload or captured events are runtime inputs. Values and order
    are modeled; instruction durations and bus timing require an exported player.
    """
    player = Player(score, programs)
    limit = player.stop_call + int(include_stop)
    count = limit if calls is None else calls
    require(type(count) is int and 1 <= count <= limit, 'Requested calls exceed the declared score span')
    for _ in range(count):
        player.step()
    return player.writes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('score', type=Path)
    parser.add_argument('--programs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reference', type=Path)
    args = parser.parse_args()
    require(not args.output.exists() and not args.output.is_symlink(), 'Choose a fresh output directory')
    score_data, program_data = args.score.read_bytes(), args.programs.read_bytes()
    score, programs = json.loads(score_data), json.loads(program_data)
    writes = compute(score, programs, include_stop=True)
    report = dict(evidenceLevel='Computed semantic model; no compiled CPU, CIA or audio claim',
                  scoreSha256=hashlib.sha256(score_data).hexdigest(),
                  programsSha256=hashlib.sha256(program_data).hexdigest(),
                  implementationSha256={name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                        for name in ('shades_player.py', 'shades_programs.py', 'describe-shades-score.py')},
                  sourceCalls=score['range']['stopCall'], finiteStopCall=score['range']['stopCall'],
                  computedStores=len(writes), authoredStopStores=4)
    if args.reference is not None:
        data = args.reference.read_bytes()
        _, expected = score_module.load_reference().shades_oracle(data, score['range']['stopCall'])
        actual = [row for row in writes if row['tick'] < score['range']['stopCall']]
        require(len(expected) == len(actual), f'Store count differs: source {len(expected)}, computed {len(actual)}')
        project = lambda row: (row['tick'], row['address'], row['value'])
        for index, (source, computed) in enumerate(zip(expected, actual)):
            require(project(source) == project(computed),
                    f'Ordered store {index} differs: source {project(source)}, computed {project(computed)}')
        report['referenceComparison'] = dict(sha256=hashlib.sha256(data).hexdigest(),
                                             matchedOrderedStores=len(actual),
                                             comparisonFields=['tick', 'address', 'value'])
    args.output.mkdir(parents=True)
    for name, value in (('computed.writes.json', writes), ('verification.json', report)):
        (args.output / name).write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
