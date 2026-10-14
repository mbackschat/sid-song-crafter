"""Verify a bounded register intervention in native post-call SID snapshots.

Offsets use the native audit's concatenated 25-byte sound-control banks, not
physical SID address gaps. Equality here does not prove bus timing or PCM identity.
"""

import argparse
import hashlib
import json
from pathlib import Path


def compare_frames(reference, candidate, allowed_offsets):
    if not isinstance(reference, list) or not reference or not isinstance(candidate, list) or len(reference) != len(candidate):
        raise ValueError('Expected nonempty frame lists of equal length')
    width = len(reference[0]) if isinstance(reference[0], list) else 0
    if width not in (25, 50):
        raise ValueError('Expected one or two concatenated 25-byte SID banks')
    allowed = set(allowed_offsets)
    if not allowed or any(type(offset) is not int or not 0 <= offset < width for offset in allowed):
        raise ValueError('Allowed offsets must name controls in the captured banks')
    changed_offsets, changed_frames = set(), []
    for tick, (before, after) in enumerate(zip(reference, candidate)):
        for row in (before, after):
            if not isinstance(row, list) or len(row) != width or any(type(value) is not int or not 0 <= value <= 255 for value in row):
                raise ValueError(f'Malformed register bank at frame {tick}')
        differences = {offset for offset in range(width) if before[offset] != after[offset]}
        outside = differences - allowed
        if outside:
            raise ValueError(f'Unexpected register change at frame {tick}, offset {min(outside)}')
        if differences:
            changed_frames.append(tick)
            changed_offsets.update(differences)
    if not changed_frames:
        raise ValueError('No register intervention was observed')
    return dict(frames=len(reference), bankBytes=width, allowedOffsets=sorted(allowed),
                changedOffsets=sorted(changed_offsets), changedFrames=len(changed_frames),
                firstChangedFrame=changed_frames[0], lastChangedFrame=changed_frames[-1],
                allOtherControlsEqual=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--allow-offset', type=int, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    before, after = args.reference.read_bytes(), args.candidate.read_bytes()
    result = dict(schemaVersion=1, referenceSha256=hashlib.sha256(before).hexdigest(),
                  candidateSha256=hashlib.sha256(after).hexdigest(),
                  comparison=compare_frames(json.loads(before), json.loads(after), args.allow_offset),
                  scope='Post-call sound controls only; not ordered bus timing, analogue state, PCM equality or musical acceptance')
    with args.output.open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['comparison']))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f'Native frame comparison failed: {error}')
