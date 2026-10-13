"""Compute the isolated phase and centered-pitch steps observed in the title bass."""

import hashlib
import json
from pathlib import Path


def advance_phase(direction, position, extent):
    """Retain byte wrapping and the asymmetric endpoints at archive $AA20–$AA42."""
    if direction & 128:
        position = (position - 1) & 255
        if position:
            return direction, position
        direction = (direction + 1) & 255
        if not direction & 128:
            return direction, position
    position = (position + 1) & 255
    if position > extent:
        position = (extent - 1) & 255
        direction = (direction - 1) & 255
    return direction, position


def centered_pitch(base, delta, extent, position, note_age, wait):
    """Compute $AA43–$AA84 after phase advance; caller owns delta, eligibility and glide.

    DEY/BMI at $AA78 adds zero times for positions129..255, including the
    diagnostic descending-zero underflow. The wait check is inside the
    subtraction loop, so an extent below2 skips it (recovered listing
    labels subval/addval; this edge is static, not demonstrated by the bass).
    """
    center = extent // 2
    if center and note_age < wait:
        return base
    additions = position if position <= 128 else 0
    return (base + (additions - center) * delta) & 65535


def main():
    folder = Path(__file__).parent
    data = (folder / 'observations.json').read_bytes()
    observed = json.loads(data)
    assert observed['sourceSha256'] == '41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192'
    snapshots = {(r['call'], r['pc']): r for r in observed['stateSnapshots']}
    phase_checks, pitch_checks = [], []
    for (call, pc), row in snapshots.items():
        if pc != 0xaa20:
            continue
        before, after = row['state'], snapshots[call, 0xaa43]['state']
        inputs = [before[name][0] for name in ('vibrato_direction', 'vibrato_position', 'vibrato_extent')]
        predicted = advance_phase(*inputs)
        expected = tuple(after[name][0] for name in ('vibrato_direction', 'vibrato_position'))
        assert predicted == expected
        phase_checks.append(dict(call=call, inputs=inputs, expected=expected, predicted=predicted))
    for call in (13, 17293):
        rows = [r for r in observed['arithmetic'] if r['call'] == call]
        start = snapshots[call, 0xaa20]['state']
        _, position = advance_phase(start['vibrato_direction'][0], start['vibrato_position'][0], start['vibrato_extent'][0])
        base = next(r['working_frequency'] for r in rows if r['pc'] == 0xaa58)
        delta = rows[0]['delta']
        predicted = centered_pitch(base, delta, start['vibrato_extent'][0], position, start['note_age'][0], 12)
        expected = next(r['working_frequency'] for r in rows if r['pc'] == 0xaa85)
        assert predicted == expected
        pitch_checks.append(dict(call=call, base=base, delta=delta, extent=start['vibrato_extent'][0],
                                 position=position, noteAge=start['note_age'][0], wait=12,
                                 expected=expected, predicted=predicted))
    result = dict(schemaVersion=1, sourceSha256=observed['sourceSha256'],
                  observationsSha256=hashlib.sha256(data).hexdigest(),
                  modelSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  phaseChecks=phase_checks, pitchChecks=pitch_checks,
                  limits='Independent isolated arithmetic only. Dynamic checks cover recorded bass-phase steps and two pitch arithmetic paths. Byte-edge and extent-zero behavior is statically derived; full delta/depth/wait selection, eligibility, glide, other instruments, full title and audio are not implemented or verified by this model.')
    with (folder / 'model-verification.json').open('x') as target:
        json.dump(result, target, indent=2)
        target.write('\n')
    print(json.dumps(dict(phaseChecks=len(phase_checks), pitchChecks=len(pitch_checks), matched=True)))


if __name__ == '__main__':
    main()
