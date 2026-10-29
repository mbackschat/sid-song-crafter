# Choose and use library instruments

The [instrument library](../../songs/instruments/README.md) turns every SID-Wizard instrument the project has built into a selectable record: what the program is, what a score must supply to play it, what it costs in voices and filter, how it measures, and what the listener said whenever it was heard. This guide shows how to choose instruments for an arrangement, use them by reference in a recipe, record what you hear, and add new instruments. The [contract](../proposals/instrument-library.md) owns the formats, probes and selection rules; this guide does not repeat them.

## What the library holds

| Part | What it tells you | Who writes it |
| --- | --- | --- |
| A record `songs/instruments/<id>@<version>.json` | The program reference; the interface (what happens on a new note, a tie and after gate-off); resources; measured character: waveforms, envelope, attack and release categories, body, motion, level and brightness | Probes measure it; a person names the role and source |
| A verdict `songs/instruments/verdicts/<id>.json` | One listener judgment: the instruments judged, whether one was isolated or a whole palette, what it was compared with, the work, tempo and mood brief, the result and the listener's exact words | A person, from a study's listening record |
| The index `songs/instruments/index.json` | Per version: every verdict from that version's side, the evidence level, partners it was accepted with, whether it is reusable, and every arrangement file that embeds it | Generated; never edited |

Records carry no mood words. A listener's "warm" or "too loud" stays inside the verdict that says where it was heard, because the same instrument can be right in one piece and wrong in another, as the case study below shows.

## Case study: the Bach Toccata palette

The accepted [Bach Toccata](../../samples/bach-toccata/README.md) arrangement aims for "a fancy, grand balance of church-organ weight, sustained harmony and dramatic pacing with tasteful SID pulse motion, register contrast and selective arpeggiation" ([interpretation brief](../research/composition/bach-toccata.md)). Rebuilding its palette from the library shows each step of the [selection procedure](../proposals/instrument-library.md#selection-procedure). The selector, a person or an agent of at least the MEDIUM tier, reads the index:

```sh
python3 -c "
import json
index = json.load(open('songs/instruments/index.json'))['instruments']
for key, entry in index.items():
    if 'bass' in entry['roles']:
        print(key, entry['level'], entry['brightness'], [v['id'] + ':' + v['result'] for v in entry['verdicts']])
"
```

### 1. Filter by resources

One MOS8580, PAL, SID-Wizard Extra, three voices. Only one instrument may own the shared filter; in this palette that is the bass. Every lead, harmony and chord candidate with `resources.filter: "owner"` drops out.

### 2. Rank by measured fit

Organ weight wants a full, steady bass; the index shows it directly. On the standard probe note, `bass.pulse-filter-static@1` (fixed-width pulse through a static low-pass) sustains at −21.3 dBFS with brightness 2.3, while `bass.triangle-plain@1` sustains at −36.2 dBFS with brightness 1.0, the pure triangle. For a grand bass the filtered pulse, 15 dB louder, fits; for the moving lead line, `lead.pulse-moving@8` has pulse-width motion and a long sustain at −23 dBFS.

| Role | Version | Measured | Why it fits the brief |
| --- | --- | --- | --- |
| Lead | `lead.pulse-moving@8` | pulse, moving width, sustain −23.0 dBFS | "tasteful SID pulse motion" on held lines |
| Bass and pedal | `bass.pulse-filter-static@1` | filtered pulse, sustain −21.3 dBFS, long release | organ weight; it alone owns the filter |
| Harmony | `harmony.triangle-pulse-static@1` | combined triangle+pulse, static, −30.2 dBFS | sustained harmony a step below the lead |
| Chord cycles | `chord.triangle-pulse-arpeggio@1` … `@5` | arpeggio body, −30.3 dBFS | "selective arpeggiation" for diminished, dominant, minor and subdominant colours |

### 3. Weigh each verdict by its context

The bass carries nine verdicts. Its accepted ones come from this piece: the complete mono Toccata ("Yes, it is nice") and its stereo version ("Wow, these two are great stereo versins"). It also carries a rejection: the first Moon River palette, "too loud, offensive". That verdict is a whole-palette judgment of a tender 70 BPM ballad, an unlike context, so it never counts against the bass here; it is a caution that this bass dominates quiet material. The procedure exists for exactly this case: in a blind test, selectors that let a context-free "warm bass" verdict outrank fit picked this bass for Moon River and failed.

The lead shows how isolated evidence reads. In the integrated-motion study the listener compared two lead versions that differ only in their pulse program and preferred `lead.pulse-moving@7` ("yes, better. I like it"); the index lists that verdict on `@8` as `not-preferred-alternative`. A same-piece, isolated preference is strong evidence, so `@7` is the first lead to audition against `@8`. Two Toccata experiments also argue against additions: a saw-attack lead, `lead.saw-pulse-moving@1`, was rejected in isolation ("Not good. The expressive variant again just adds these odd short sounds."), and a quiet kick, `percussion.triangle-drum@1`, made "no difference in both". Neither earns a place in this palette.

### 4. Use the versions in the recipe and listen

Prepare the Toccata inputs, then point each instrument at its library version instead of embedding the program:

```sh
python3 scripts/studies/bach/prepare-toccata.py --output build/toccata-library-inputs
python3 -c "
import json
path = 'build/toccata-library-inputs/hybrid.json'
recipe = json.load(open(path))
recipe['instruments'] = {part: {'library': version} for part, version in {
    'lead': 'lead.pulse-moving@8', 'bass': 'bass.pulse-filter-static@1', 'harmony': 'harmony.triangle-pulse-static@1',
    'diminished-cycle': 'chord.triangle-pulse-arpeggio@1', 'dominant-cycle': 'chord.triangle-pulse-arpeggio@2',
    'minor-cycle': 'chord.triangle-pulse-arpeggio@3', 'subdominant-cycle': 'chord.triangle-pulse-arpeggio@4',
    'dominant-inner-cycle': 'chord.triangle-pulse-arpeggio@5'}.items()}
json.dump(recipe, open('build/toccata-library-inputs/library.json', 'w'), indent=1)
"
python3 scripts/native-song.py build build/toccata-library-inputs/library.json --output build/toccata-library
```

The converter resolves each reference to the program bytes, so `build/toccata-library/conversion/library.swm` is byte-identical to the module built from the embedded recipe, and `build/toccata-library/conversion.json` names the library version of every instrument. Play `build/toccata-library/export/library.sid` (or the `.prg` in VICE) as described in the [README](../../README.md#play-the-song). To audition the preferred lead motion, change `lead` to `lead.pulse-moving@7` and build into a fresh directory.

### 5. Record what you hear

When the listener judges the result, write the judgment as a verdict, so that the next selector sees it with its context. A palette judgment lists every library version in the render with `"attribution": "group"`; a comparison where only the lead changed is `"isolated"` and names the other version in `comparedWith`. The quote must be the listener's exact words from the study's listening record; the validator checks that.

## Add a new instrument

1. Design the program in an arrangement recipe and listen to it in context, as the [native workflow](native-song-workflow.md) describes.
2. Write its record with the role, source work, card and rights, its program reference (`"program": {"engine": "sidwizard-extra-1.97", "file": "<recipe>", "record": "instruments.<key>"}`), and every field the probes settle left as `{"basis": "unknown"}` or `"not-established"`. An existing record is the best template. Name it `<role>.<descriptor>` after what it does; if the id exists with a different program, use the next version.
3. Let the probes measure it, then validate:

```sh
python3 scripts/instrument_trace.py songs/instruments/<id>@<version>.json --output build/instrument-trace-<id> --write
python3 scripts/instrument_probe.py songs/instruments/<id>@<version>.json --output build/instrument-probe-<id> --write
python3 scripts/instrument_library.py index
python3 scripts/instrument_library.py check
```

The interface probe executes a 17-note phrase with ties and keeps the raw facts behind each classification in its output directory; the level probe renders one note at the role pitch. A program whose bytes already exist in the library is rejected; reference that version instead.

## Keep it consistent

- `python3 scripts/instrument_library.py check` fails on an unknown field, a claim based on hearing, an envelope category that contradicts its thresholds, a paraphrased quote, an unresolved reference, two records with the same program, or a stale index. `tests/instrument_library_test.py` runs the same check on the checked-in library.
- Existing arrangement files keep their embedded programs as frozen evidence; the index lists where each library program occurs. Do not rewrite them to references.
- A program never changes within a version. Measured claims may be re-measured under a newer probe version, which each claim's detail names.

## Limits

- Probe values describe one note at one pitch per role, so levels compare between candidates for one role; the arrangement's balance still decides prominence.
- Selection narrows candidates for audition; it does not replace listening. LOW-tier agents failed the blind selection test and are not supported selectors.
- The interface probe cannot yet run instruments with a large octave shift, because its high probe note would leave the converter's range; the library holds none today.
- Reusability is strict: an instrument counts as reusable only after an accepted verdict on a different work than the one it was written for and with its interface fully probed.
