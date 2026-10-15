"""Plan and compute a bounded Ghostbusters held-root stereo expansion."""

from copy import deepcopy


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(arrangement):
    require(arrangement.get('format') == 'ghostbusters-stereo-v1', 'Expected ghostbusters-stereo-v1')
    require(set(arrangement) <= {'format', 'intent', 'target', 'allocation', 'support', 'mix', 'modelAssistance', 'publication'}, 'Unknown stereo arrangement field')
    require(arrangement['target'] == dict(clock='ntsc', sidModel='MOS6581', sidBases=[0xd400, 0xd420]), 'Stereo requires NTSC matching MOS6581s at $D400/$D420')
    require(arrangement['mix'] == [[1, 0], [0, 1]], 'Stereo requires native raw A-left/B-right presentation')
    support = arrangement['support']
    require(set(support) == {'sourceVoice', 'patterns', 'transpose', 'requiredCompanionPatch', 'allowedLeadIntervals', 'patch'}, 'Unknown held-support configuration')
    require(support['sourceVoice'] == 1 and support['transpose'] == 12 and support['requiredCompanionPatch'] == 3, 'Support requires octave-up source bass under source noise percussion')
    require(isinstance(support['patterns'], list) and 1 <= len(support['patterns']) <= 8 and len(set(support['patterns'])) == len(support['patterns']) and all(type(x) is int and 0 <= x < 128 for x in support['patterns']), 'Choose 1..8 distinct source bass patterns')
    require(support['allowedLeadIntervals'] == [0, 2, 3, 4, 5, 7, 9, 10], 'Hold screening requires the declared source dominant/blues interval set')
    patch = support['patch']
    require(set(patch) == {'pulse_low', 'pulse_high', 'control', 'attack_decay', 'sustain_release'}, 'Support requires exactly five static SID fields')
    require(all(type(x) is int and 0 <= x <= 255 for x in patch.values()) and patch['pulse_high'] <= 15 and patch['control'] == 0x41, 'Support is an uncoupled static pulse with bounded numeric fields')
    return support


def compute(player, composition, arrangement, *, calls=None):
    support = validate(arrangement)
    roots = set()
    for pattern in support['patterns']:
        require(str(pattern) in composition['score']['patterns'], 'Support selects an absent source bass pattern')
        first = composition['score']['patterns'][str(pattern)]['rows'][0]
        require(not first['header'] & 64 and 'note' in first, 'Held support requires a pitched first bass row')
        roots.add(first['note'])
    require(len(roots) == 1, 'Consecutive selected bass patterns must share one held root')
    require(composition['sound']['patches'].get('3', {}).get('control') == 0x81, 'Support companion patch must remain source noise percussion')
    model = player.compute(composition, calls=calls)
    count = len(model['returns'])
    expanded = player.score.expand(composition['score'], max(1, count))
    by_call = {}
    for row in expanded['rows']:
        by_call.setdefault(row['tick'], []).append(row)
    source_writes = {}
    for row in model['writes']:
        source_writes.setdefault(row['tick'], []).append(row)
    result = deepcopy(model)
    result['writes'] = list(source_writes.get(None, [])) + [dict(phase='init', tick=None, address=a, value=0) for a in range(0xd437, 0xd41f, -1)]
    state = dict(pattern=255, active=0, note=0)
    result['initial']['stereoSupport'] = deepcopy(state)
    frequencies = {int(k): v for k, v in composition['sound']['frequencies'].items()}
    ledger, current = [], None
    for tick in range(count):
        for row in source_writes.get(tick, []):
            result['writes'].append(row)
            if 0xd400 <= row['address'] <= 0xd406 or row['address'] == 0xd418:
                result['writes'].append(dict(row, address=row['address'] + 32))
        for row in by_call.get(tick, []):
            if row['voice'] == 1:
                state['pattern'] = row['pattern']
        if tick in model['resetCalls']:
            state['pattern'] = 255
        voices = model['returns'][tick]['score']['voices']
        eligible = state['pattern'] in support['patterns'] and voices[2]['instrument'] == support['requiredCompanionPatch']
        emitted = []
        if eligible and not state['active']:
            require(voices[1]['note'] in roots, 'Support entered after the source bass root onset')
            state['note'] = voices[1]['note'] + support['transpose']
            require(state['note'] <= 95, 'Held root exceeds native frequency bank')
            word = player.programs.frequency(frequencies, state['note'])
            patch = support['patch']
            emitted = [(0xd428, word >> 8), (0xd427, word & 255), (0xd42b, patch['control']),
                (0xd429, patch['pulse_low']), (0xd42a, patch['pulse_high']),
                (0xd42c, patch['attack_decay']), (0xd42d, patch['sustain_release'])]
            state['active'] = 1
            current = dict(startCall=tick, rootNote=state['note'], sourceNote=voices[1]['note'], leadIntervals=set())
        elif not eligible and state['active']:
            emitted = [(0xd42b, 0x40), (0xd42d, 0)]
            state['active'] = 0
            current['endCall'] = tick
            ledger.append(current)
            current = None
        if eligible:
            lead = voices[0]
            if not lead['header'] & 64:
                interval = (lead['note'] - state['note']) % 12
                require(interval in support['allowedLeadIntervals'], f'Held root conflicts with source lead at call {tick}: interval {interval}')
                current['leadIntervals'].add(interval)
        result['writes'].extend(dict(phase='play', tick=tick, address=a, value=v) for a, v in emitted)
        result['returns'][tick]['stereoSupport'] = deepcopy(state)
    if current is not None:
        current['endCall'] = count
        ledger.append(current)
    for row in ledger:
        row['leadIntervals'] = sorted(row['leadIntervals'])
    result['supportLedger'] = ledger
    return result


def replace_once(source, anchor, replacement):
    require(source.count(anchor) == 1, f'Stereo assembly anchor changed: {anchor!r}')
    return source.replace(anchor, replacement)


def assembly(source, arrangement):
    support = validate(arrangement)
    source = replace_once(source, 'gb_init_done:\n', '  JSR gb_stereo_init\ngb_init_done:\n')
    source = replace_once(source, 'gb_selected_pattern:\n', 'gb_selected_pattern:\n  CPX #$01\n  BNE gb_stereo_pattern_saved\n  STA gb_support_pattern\ngb_stereo_pattern_saved:\n')
    source = replace_once(source, '  JMP gb_advance_phase\ngb_selected_pattern:', '  LDA #$ff\n  STA gb_support_pattern\n  JMP gb_advance_phase\ngb_selected_pattern:')
    source = replace_once(source, 'gb_advance_phase:\n', 'gb_advance_phase:\n  JSR gb_stereo_support\n')
    require(source.count('  STA $d418') == 1, 'Stereo music volume site changed')
    lines = source.splitlines()
    output, index = [], 0
    for line in lines:
        output.append(line)
        if line == '  STA $d418':
            output.append('  STA $d438')
        elif line.startswith('  STA $d4') and line.endswith(',Y'):
            address = int(line.split('$')[1].split(',')[0], 16)
            if 0xd400 <= address <= 0xd406:
                index += 1
                output += ['  CPX #$00', f'  BNE gb_stereo_skip_{index}', f'  STA ${address + 32:04x},Y', f'gb_stereo_skip_{index}:']
    require(index == 12, 'Stereo expected all twelve distinct voice-output instruction sites')
    patch = support['patch']
    generated = '''
gb_stereo_init:
  LDA #$00
  STA gb_support_active
  STA gb_support_note
  LDA #$ff
  STA gb_support_pattern
  LDA #$00
  LDX #$17
gb_stereo_clear:
  STA $d420,X
  DEX
  BPL gb_stereo_clear
  RTS
gb_stereo_support:
  LDA gb_instrument+2
  CMP #$03
  BNE gb_support_off
  LDA gb_support_pattern
'''
    for pattern in support['patterns']:
        generated += f'  CMP #${pattern:02x}\n  BEQ gb_support_eligible\n'
    generated += '''  JMP gb_support_off
gb_support_eligible:
  LDA gb_support_active
  BNE gb_support_done
  LDA gb_note+1
  CLC
  ADC #$0c
  STA gb_support_note
  TAY
  LDA gb_frequency_hi,Y
  STA $d428
  LDA gb_frequency_lo,Y
  STA $d427
'''
    for port, field in ((0xd42b, 'control'), (0xd429, 'pulse_low'), (0xd42a, 'pulse_high'), (0xd42c, 'attack_decay'), (0xd42d, 'sustain_release')):
        if field == 'control':
            generated += 'gb_support_control_onset:\n'
        generated += f'  LDA #${patch[field]:02x}\n  STA ${port:04x}\n'
    generated += '''  LDA #$01
  STA gb_support_active
  RTS
gb_support_off:
  LDA gb_support_active
  BEQ gb_support_done
  LDA #$40
  STA $d42b
  LDA #$00
  STA $d42d
  STA gb_support_active
gb_support_done:
  RTS
gb_support_pattern:
  .byte $00
gb_support_active:
  .byte $00
gb_support_note:
  .byte $00
'''
    return '\n'.join(output) + '\n' + generated
