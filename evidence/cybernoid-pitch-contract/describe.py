"""Preserve the bounded pitch-component contract with exact proof provenance."""

from dataclasses import fields
import hashlib
import json
from pathlib import Path

from model import PitchInputs, PitchParameters, PitchState

ROOT = Path(__file__).resolve().parents[2]


def fingerprint(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def main():
    folder = Path(__file__).parent
    target = folder / 'contract.json'
    assert not target.exists()
    verification = json.loads((folder / 'verification.json').read_bytes())
    coverage_path = ROOT / 'build/cybernoid-title-mechanism-coverage/coverage.json'
    coverage = json.loads(coverage_path.read_bytes())
    source = ROOT / '.local/research/cybernoid-ii/Cybernoid_II.sid'
    listing = ROOT / '.local/downloads/tel-cybernoid2.asm'
    assert fingerprint(source)['sha256'] == coverage['source']['sha256'] == verification['sourceSha256']
    assert fingerprint(listing)['sha256'] == coverage['listing']['sha256']
    assert verification['modelSha256'] == fingerprint(folder / 'model.py')['sha256']

    state_addresses = dict(base_note=0xa63f, frequency=[0xa693, 0xa696], held_frequency=[0xa64b, 0xa645],
                           vibrato_extent=0xa664, vibrato_direction=0xa667, vibrato_position=0xa66a,
                           vibrato_age=0xa6a8, glide_enabled=0xa64e, glide_active=0xa651,
                           glide_control=0xa690, glide_target=0xa68d)
    mechanisms = [{name: row[name] for name in ('voiceIndex', 'recordIndex', 'mechanism', 'variant', 'visits',
                                               'distinctCalls', 'firstCall', 'lastCall', 'minimumAge', 'maximumAge')}
                  for row in coverage['mechanisms'] if row['mechanism'].startswith(('vibrato', 'glide'))]
    result = dict(
        schemaVersion=1,
        classification='Independent named-buffer pitch component; bounded research, not an independent song player',
        provenance=dict(source=fingerprint(source), sourceUrl=coverage['source']['url'], listing=fingerprint(listing),
                        listingUrl='https://github.com/realdmx/c64_6581_sid_players/blob/f215174fc4c983674808fcd47bc506f96b3d2d04/Tel_Jeroen_MON/Tel_Jeroen_Cybernoid2.asm',
                        sourceBasis='Pinned archive instructions settle arithmetic. Recovered listing supplies names and intent only; known table/build variants prevent treating it as the exact archive source.',
                        model=fingerprint(folder / 'model.py'), checker=fingerprint(folder / 'check.py'),
                        isolatedVerification=fingerprint(folder / 'verification.json'),
                        selectedTitleBranchCensus=fingerprint(coverage_path),
                        openingTrace=fingerprint(ROOT / 'evidence/cybernoid-title-instructions/opening.trace.json.gz'),
                        wrapModel=fingerprint(ROOT / 'evidence/cybernoid-wrap-pitch/model.py'),
                        wrapState=fingerprint(ROOT / 'evidence/cybernoid-wrap-pitch/observations.json.gz'),
                        addressMap=dict(stateArrays=state_addresses,
                                        inputs=dict(effective_note=0xa63c, note_age=0xa65e, row_remaining=0xa633,
                                                    row_duration=0xa636, speed=0xa629),
                                        parameters=dict(vibrato_control=0x40, selected_record=0xa642,
                                                        wait_table=0xb0ac, patched_wait_operand=0xaa5c),
                                        frequency_tables=dict(low=0xae3f, high=0xae96))),
        publicContract=dict(
            signature='advance_pitch(state: PitchState, parameters: PitchParameters, inputs: PitchInputs) -> PitchStep',
            stateFields=[f.name for f in fields(PitchState)], parameterFields=[f.name for f in fields(PitchParameters)],
            inputFields=[f.name for f in fields(PitchInputs)],
            bounds='frequency/held_frequency and every input ending frequency are unsigned 16-bit words; all other numeric fields are bytes; bool is rejected for numeric fields. drum_mode is a boolean. No runtime source, addresses, instruction replay, register ledger or frequency lookup dependency.',
            callerResponsibilities=['Supply working frequency after any tone arpeggio and persistent held frequency after previous late effects.',
                                    'Supply effective/adjacent, unmodulated base and glide-target table words independently; glide uses base, not effective arpeggio index.',
                                    'Supply note age, row counters and speed without incrementing them inside this component.',
                                    'Apply drum bypass from record fx3 bit $10; other record flags belong to other mechanisms.',
                                    'Handle new-row initialization/score consumption, tone-arpeggio counter, gate/ADSR, pulse/filter, onset/drum/sweep/detune overrides and ordered SID writer.'],
            returns='Updated immutable named state; vibrato_ran and delta; glide action disabled/wait/interpolate/complete, divisor and step where interpolation runs. It emits no SID stores.',
            sourceRange=dict(normalEntry=0xa9c1, drumBypassEntry=0xaa97, stopBefore=0xab8d),
            flags='glide flags are tested for zero/nonzero; interpolation sets active=1 and completion clears both to0. Direction is an arbitrary byte interpreted by its sign bit; it is not a bool.'),
        vibrato=dict(
            eligibility=dict(pcs=[0xa9c1, 0xa9c3, 0xa9c5, 0xa9c8], rule='Run iff drum bypass is false, control !=0 and glide_active ==0; glide_enabled alone does not suppress it.'),
            packedControl=dict(pcs=[0xa9d3, 0xa9d5, 0xa9d9, 0xa9db, 0xa9e8, 0xa9ea],
                               lowNibble='Logical right-shift count 0..15 for delta.', middleThreeBits='Extent=(control>>4)&7.',
                               bit7='Select ADC abs,X at $AA0D instead of LDY abs,X; age-dependent high-byte delta growth.'),
            age=dict(pcs=[0xa9f1, 0xa9f4, 0xa9f6, 0xa9f8], rule='Increment once while <48; if already>=48 retain the byte, including255.'),
            delta=dict(pcs=[0xa9fb, 0xa9fe, 0xaa02, 0xaa05, 0xaa07, 0xaa0a, 0xaa0d, 0xaa10, 0xaa12, 0xaa16, 0xaa18],
                       rule='Compute adjacent-effective modulo65536. If bit7: replace difference high with (high + updated_age + unsigned-subtraction-no-borrow) modulo256. Then logically shift the word right lowNibble times.',
                       carry='ADC at $AA0D consumes carry from high SBC; it adds an extra1 when adjacent_frequency>=effective_frequency.'),
            phase=dict(pcs=[0xaa20, 0xaa23, 0xaa25, 0xaa28, 0xaa2a, 0xaa2d, 0xaa2f, 0xaa35, 0xaa38, 0xaa3a, 0xaa3d, 0xaa40],
                       descending='Decrement position modulo256. If nonzero, stop. Ifzero increment direction modulo256; stop if new direction is nonnegative, otherwise fall through ascending.',
                       ascending='Increment position modulo256. If extent>=position, stop. Else set position=extent, decrement direction modulo256, decrement position modulo256.',
                       timing='Phase advances before age wait, but not while active glide bypasses vibrato.'),
            frequency=dict(pcs=[0xaa43, 0xaa46, 0xaa4b, 0xaa50, 0xaa55, 0xaa58, 0xaa5b, 0xaa5d, 0xaa62, 0xaa68, 0xaa6f, 0xaa72, 0xaa73, 0xaa78, 0xaa7e],
                           rule='Reload effective table word. If extent//2>0 and note_age<wait, retain that base. Otherwise subtract delta extent//2 times; add delta position times only for position0..128. All arithmetic wraps modulo65536.',
                           signedLoop='Initial position128 executes128 additions;129..255 executezero. Extent0/1 skip the subtraction loop and its age-wait check.',
                           output='Store to frequency and held_frequency; preserve base_note. Low/high stores use explicit borrow/carry across bytes.')),
        glide=dict(
            eligibility=dict(pcs=[0xaa97, 0xaa99, 0xaa9c], rule='Run iff glide_enabled !=0, including drum bypass cases.'),
            packedControl=dict(pcs=[0xaaa4, 0xaaa7, 0xaaad, 0xaab0, 0xaab3, 0xaab6, 0xaab9],
                               highNibble='Length0..15, patched into duration test and divisor accumulator.',
                               lowNibble='Timing offset=(lowNibble-1) modulo256; zero therefore means255, not no delay.'),
            timing=dict(pcs=[0xaabb, 0xaabc, 0xaabf, 0xaac2, 0xaac7, 0xaacb, 0xaacd, 0xaad0],
                        rule='timing=(remaining+offset) modulo256. If timing>=duration: wait, leaving bothflags unchanged. Else set active=1. If (timing+length) modulo256 <duration: complete; otherwise interpolate.',
                        carry='The first CMP-below clears carry before ADC length; discarded carry from the timing addition is not reused.',
                        completion='Set base_note=target, frequency=held_frequency=target word, clear enabled/active. Completion is based on row countdown, not frequency proximity or clamp.'),
            magnitude=dict(pcs=[0xaad2, 0xaad5, 0xaad9, 0xaadd, 0xaae5, 0xaaee, 0xaaf4, 0xaafa, 0xaafe, 0xab02, 0xab04, 0xab0a],
                           rule='Compare unmodulated base and target lookup words by unsigned subtraction. Magnitude=absolute difference. If base>=target use SEC/SBC; otherwise two-complement normalize and use CLC/ADC. Equal words choose subtraction.'),
            divisor=dict(pcs=[0xab0d, 0xab10, 0xab12, 0xab13, 0xab15, 0xab16, 0xab18],
                         rule='Start A=0,C=0; repeatedly add length plus previous carry, retaining only byte A. Iterations=speed+1 for speed0..128, otherwise1 because DEY/BPL tests the byte sign.',
                         limits='Typical speed2 gives3*length without overflow. Synthetic overflow examples: length15/speed17 yields14, not15; speed129 executesone addition.'),
            division=dict(pcs=[0xab1a, 0xab1b, 0xab1d, 0xab1f, 0xab23, 0xab27, 0xab28, 0xab2a, 0xab2e, 0xab30, 0xab31, 0xab34, 0xab38, 0xab39, 0xab3d, 0xab41],
                          rule='For divisor>0: q,r=divmod(magnitude&$7FFF,divisor); step=((magnitude&$8000)+q+int(((2*r)&255)>=divisor)) modulo65536. For divisor0: step=((magnitude&$8000)+$8000) modulo65536.',
                          basis='The initial word shift plus15 restoring rounds retain original bit15 in the quotient. Final ASL remainder discards bit8 before CMP; therefore rounding is not a general round-half-up division for divisors>128.',
                          differencesFromConventional=[dict(distance=32768, divisor=2, actual=32768, conventional=16384),
                                                       dict(distance=199, divisor=200, actual=0, conventional=1)]),
            interpolation=dict(pcs=[0xab4f, 0xab52, 0xab53, 0xab55, 0xab58, 0xab5b, 0xab5e, 0xab60, 0xab63],
                               rule='Add/subtract step to persistent held_frequency modulo65536; copy result to currentfrequency andheld. No overshoot clamp or target-proximity comparison. Base_note remains unchanged until completion.')),
        rowAndWrap=dict(
            newRow=dict(pcs=[0xa7af, 0xa7b1, 0xa7b4, 0xa7b7, 0xa7ba],
                        rule='Before contextual row consumption clear glide_enabled,glide_active,note_age,vibrato_age; preserve vibrato direction/position/extent. Resolved note setup reloads current/held table word; encoded glide supplies enabled/control/target.'),
            orderFF=dict(pcs=[0xa75f, 0xa761, 0xa764, 0xa767, 0xa76a],
                         rule='Clear only row_countdown,order_cursor,pattern_cursor, not retained vibrato phase or held pitch state. Existing wrap intervention proves phase sufficiency for its declared21-call voice1window.')),
        evidence=dict(
            isolated=dict(componentCases=len(verification['componentChecks']), divisionCases=len(verification['divisionChecks']),
                          divisorCases=len(verification['divisorChecks']), allMatch=True,
                          maximumComponentInstructions=max(c['instructions'] for c in verification['componentChecks']),
                          scope='Synthetic named caller states; exact state/delta equality with original bounded instructions across all3voiceindices and other-voice-state isolation. Source file/staticfrequencyandwaittable unchanged; no full-title per-body model comparison.'),
            intactSelectedTitle=dict(scope=coverage['scope'], orderedWriteComparison=coverage['orderedWriteComparison'],
                                    mechanismSummaries=mechanisms,
                                    distinction='Census proves occurrence and source execution of variants, not that this new model matched each title body. The two detailed opening arithmetic paths and phase model predate this expanded component.')),
        remainingWork=['Join this component with scheduler, tone arpeggio, post-pitch onset/drum/sweep/detune and complete pitch-table decoding.',
                       'Compare independently computed named states at every selected-title body, including later bit7 growth and downward/zero-length completion paths.',
                       'Validate musical behavior/audio/listening separately; no audio or complete instrument approval is established here.'],
        reproduction=dict(command='mkdir build/cybernoid-pitch-contract-repeat && cp build/cybernoid-pitch-contract/model.py build/cybernoid-pitch-contract/check.py build/cybernoid-pitch-contract-repeat/ && python3 build/cybernoid-pitch-contract-repeat/check.py',
                          dependencies='Pinned local SID installed; shared banked audit/parser and corrected py65 CPU loader in scripts; py65 installed under.tools/test-deps. Checker requires freshverification.json and does not run init or a full traversal.'),
    )
    with target.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(path=str(target.relative_to(ROOT)), sha256=fingerprint(target)['sha256'],
                          mechanisms=len(mechanisms), bytes=target.stat().st_size)))


if __name__ == '__main__':
    main()
