"""Build a three-voice passage from decoded musical and instrument descriptions."""

import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

from verify_player import require

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / 'songs/studies/drax-full-reconstruction'
DEFAULT_RECIPE = STUDY / 'instrument.json'


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bass = load_script('reconstruct-drax-bass')
native = load_script('native-song')
context = load_script('context-drax-bass')


def build(path):
    path = Path(path).resolve()
    description = json.loads(path.read_text())
    require(description['format'] == 'sid-three-voice-reconstruction-v1', 'Unsupported composition description')
    recipe = bass.read_recipe(path.parent / description['bassRecipe'])
    require(recipe['playCalls'] == 151, 'This reconstruction describes the first 151 calls')
    recipe['title'] = 'Independent DRAX opening study'
    lead, chord = description['lead'], description['chord']
    require(len(lead['vibratoDeltas']) == 8 and len(chord['frequencies']) == 3, 'Expected eight-step vibrato and three-tone chord')
    require(lead['notes'] and all(2 <= n['initCall'] < 151 and 0 < n['frequency'] < 65536 for n in lead['notes']), 'Invalid lead score')
    require(all(b['initCall'] - a['initCall'] >= 4 for a,b in zip(lead['notes'],lead['notes'][1:])), 'Lead preparations overlap')
    symbols = {
        'LEAD_COUNT': len(lead['notes']), 'CHORD_INIT': chord['initCall'],
        'GATE_CLOSE_AGE': description['scoreGateCloseAge'], 'VIBRATO_START_AGE': lead['vibratoStartAge'],
        'LEAD_PULSE_LO': lead['pulseInitial'] & 255, 'LEAD_PULSE_HI': lead['pulseInitial'] >> 8,
        'LEAD_STEP': lead['pulseStep'], 'LEAD_LOWER': lead['pulseLowerHighByte'], 'LEAD_UPPER': lead['pulseUpperHighByte'],
        'LEAD_PRE_BOUND': lead['prehistoryBoundHighByte'], 'LEAD_PRE_PULSE_HI': lead['prehistoryPulseHighByte'],
        'LEAD_AD': lead['attackDecay'], 'LEAD_SR': lead['sustainRelease'], 'LEAD_WAVE': lead['waveform'],
        'CHORD_AD': chord['attackDecay'], 'CHORD_SR': chord['sustainRelease'], 'CHORD_WAVE': chord['waveform'], 'CHORD_PULSE_HI': chord['pulseHighByte'],
    }
    require(all(type(v) is int and 0 <= v <= 255 for v in symbols.values()), 'Instrument constants must fit bytes')
    source = (bass.STUDY / 'player.asm').read_text().replace('entry_init:', 'bass_entry_init:').replace('entry_play:', 'bass_entry_play:')
    companion = (STUDY / 'companions.asm').read_text()
    for name, value in symbols.items():
        companion = re.sub(r'\b' + name + r'\b', f'${value:02x}', companion)
    source += '\n' + companion
    arrays = {
        'lead_calls': [n['initCall'] for n in lead['notes']],
        'lead_lo': [n['frequency'] & 255 for n in lead['notes']],
        'lead_hi': [n['frequency'] >> 8 for n in lead['notes']],
        'chord_lo': [n & 255 for n in chord['frequencies']],
        'chord_hi': [n >> 8 for n in chord['frequencies']],
        'vibrato_lo': [n & 255 for n in lead['vibratoDeltas']],
        'vibrato_hi': [(n >> 8) & 255 for n in lead['vibratoDeltas']],
    }
    for name, values in arrays.items():
        source += f'\n{name}:\n  .byte ' + ','.join(f'${n:02x}' for n in values) + '\n'
    sid, built = bass.build_psid(recipe, source)
    return sid, dict(built, source=source, description=description, bassRecipe=recipe)


def compare_writes(original, recreated):
    identity = lambda row: (row['phase'], row['tick'], row['address'], row['value'])
    a,b = list(map(identity, original)), list(map(identity, recreated))
    if a != b:
        first = next((i for i,(x,y) in enumerate(zip(a,b)) if x != y), min(len(a),len(b)))
        raise ValueError(f'Ordered SID write mismatch at {first}: {a[first:first+1]} versus {b[first:first+1]}; counts {len(a)}/{len(b)}')
    deltas = [right['instructionStartCycle'] - left['instructionStartCycle'] for left, right in zip(original, recreated) if left['phase'] == 'play' and 'instructionStartCycle' in left and 'instructionStartCycle' in right]
    return {'matchedWrites': len(a), 'allRegisters': True, 'allWritesIncludingRepeatedCutoff': True,
            'sameCallAddressValueOrder': True, 'exactCycleEquality': False,
            'instructionStartCycleDeltaRange': [min(deltas), max(deltas)] if deltas else None}


def run(path, output, reference=None, vice=False):
    output = Path(output).resolve()
    require(not output.exists(), 'Choose a fresh output directory')
    sid, built = build(path)
    audited, writes = bass.audit_psid(sid, 154)
    musical_writes = [r for r in writes if r['phase'] == 'init' or r['tick'] < 151]
    original, guard = None, None
    if reference:
        original = Path(reference).read_bytes()
        require(bass.digest(original) == bass.SOURCE_SHA256, 'Reference differs from pinned DRAX tune')
        _, reference_writes = bass.audit_psid(original,151)
        guard = compare_writes(reference_writes,musical_writes)
    output.mkdir(parents=True)
    (output/'reconstructed.sid').write_bytes(sid)
    (output/'player.asm').write_text(built.pop('source'))
    (output/'player.listing').write_text(built.pop('listing'))
    bass.write_json(output/'build.json',built)
    bass.write_json(output/'audit.json',audited)
    bass.write_json(output/'writes.json',writes)
    if guard:
        bass.write_json(output/'register-comparison.json',guard)
    renderer = ROOT/'.local/bin/render-sid'
    renderer_hash = bass.digest(renderer.read_bytes())
    for label, source in [('reconstructed',output/'reconstructed.sid')] + ([('reference',Path(reference).resolve())] if reference else []):
        bass.run_process([str(renderer),str(source),str(output/f'{label}.wav'),'3'],output/f'{label}.render.json')
        info = bass.inspect_wav(output/f'{label}.wav')
        require(info['clippedSamples']==0 and info['acRms']>1 and info['frames']==132300,'Invalid render')
        bass.excerpt(output/f'{label}.wav',output/f'{label}.exact.wav',2.02,.73)
    audio = context.common_gain_comparison(output/'reference.wav',output/'reconstructed.wav',output) if reference else None
    if audio:
        audio['segments'][2]['label'] = 'Independent three-voice reconstruction; no original accompaniment'
    if reference:
        require(Path(reference).read_bytes()==original,'Reference changed')
        bass.write_json(output/'pcm-comparison.json',bass.pcm_comparison(output/'reference.exact.wav',output/'reconstructed.exact.wav'))
    if vice:
        bass.run_process([sys.executable,str(ROOT/'scripts/trace-sid-vice.py'),str(output/'reconstructed.sid'),'--oracle',str(output/'writes.json'),'--first-call','0','--last-call','153','--output',str(output/'vice')],output/'vice-command.json')
    require(bass.digest(renderer.read_bytes())==renderer_hash,'Renderer changed')
    report = {'sourceDescription':str(Path(path).resolve()),'descriptionSha256':bass.digest(Path(path).read_bytes()),'sidSha256':bass.digest(sid),'rendererSha256':renderer_hash,
              'originalDriverIncluded':False,'registerDumpReplay':False,'allVoicesIndependentlyImplemented':True,
              'orderedWriteComparison':guard,'audio':audio,'listeningReview':None,
              'limits':'First 151 PAL calls from initialization. Ordered writes match when verified, but their within-frame cycles and resulting oscillator/noise phases differ. Not PCM identity, physical hardware equivalence or listener acceptance.'}
    bass.write_json(output/'study.json',report)
    print(f'Independent three-voice reconstruction: {output}',flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe',type=Path,default=DEFAULT_RECIPE)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--reference',type=Path)
    parser.add_argument('--vice',action='store_true')
    args=parser.parse_args()
    run(args.recipe,args.output,args.reference,args.vice)


if __name__=='__main__':
    main()
