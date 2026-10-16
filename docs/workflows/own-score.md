# Bring a MIDI score to a playable SID

This walkthrough starts with an attributed MIDI, imports its complete polyphonic content, makes an explicit three-voice reduction, assigns native instrument programs, and builds SID, PRG and editable SID-Wizard files. It uses existing tools and the retained Bach source; it does not read an already arranged `score.json` or run the Bach-specific preparer. Reuse the configuration structure for your own MIDI.

The example covers source beats 0–10 of J. S. Bach's *Toccata and Fugue in D minor*, BWV 565: the opening gestures, pedal entrance, first held chord and resolution. It is a short technical intake example, not the [accepted complete Toccata interpretation](../../samples/bach-toccata/README.md). Its intent is recognizable manual gestures and a sustained pedal foundation, with restrained pulse movement on the lead. This reduction and its source-timed performance have no listening verdict.

## Prepare the tools and source

Run commands from the repository root. Follow [requirements and native setup](../../README.md#requirements-and-setup), including the [SID renderer](audio-workflow.md#pinned-library-setup), then install the pinned MIDI dependencies:

```sh
uv --cache-dir .local/uv-cache pip install --target .tools/arrangement-deps mido==1.3.3 packaging==24.2
python3 scripts/doctor.py --profile demo --sid-count 1
```

The build needs Python, Mido, py65, the single-SID native exporter and `.local/bin/render-sid`. A live bridge, agent plugin, audio-model service and research archive are unnecessary. [Local setup](../setup/local-setup.md) owns dependency acquisition and platform requirements. Independent standalone VICE verification is a separate step below.

The complete [source MIDI](../../songs/studies/bach-toccata-opening/source/ToccataFugue.mid) and [LilyPond notation](../../songs/studies/bach-toccata-opening/source/ToccataFugue.ly) are already in Git. Anonymous's Mutopia 1780 typesetting is based on the Bach-Gesellschaft Ausgabe, 1867, and declares Public Domain; preserve the credit and declaration. The [source record](../research/composition/bach-toccata.md#retained-source-files) owns the original URLs, hashes and edition limits; [third-party notices](../../THIRD_PARTY_NOTICES.md#retained-public-domain-score-editions) distinguishes the source's public-domain status, our MIT configuration and the native player's upstream terms. No recording or new download is needed for this example.

## Inspect the complete import

[The import configuration](../../config/own-score/import.json) pins the MIDI SHA-256 and assigns stable IDs to every sounding track: track 1 is `right-manual`, track 2 `left-manual`, and track 3 `pedal`. Track indices are zero-based; track 0 contains control metadata and no notes. Importing preserves all sounding tracks before any reduction:

```sh
PYTHONPATH=.tools/arrangement-deps python3 scripts/import-midi.py songs/studies/bach-toccata-opening/source/ToccataFugue.mid config/own-score/import.json build/own-score-inspect/full-common-score.json
```

The report identifies 3,651 notes, 384 ticks per quarter and quarter = 60. Inspect the imported parts and their first events:

```sh
python3 - <<'PY'
import json
from pathlib import Path
score = json.loads(Path("build/own-score-inspect/full-common-score.json").read_text())
for part in score["parts"]:
    print(part["id"], part["name"], len(part["events"]), part["events"][:2])
print(score["provenance"]["importReport"])
PY
```

The complete parts contain 1,905 right-manual, 1,417 left-manual and 329 pedal notes. Timing is retained as exact rational beat pairs. Program changes, key signatures, instrument names and text remain in the original MIDI and are reported as unmapped metadata. Velocity remains in the common score but does not choose SID dynamics. The MIDI does not perform printed fermatas, prall ornaments or expressive tempo changes; this example keeps its quarter = 60 rather than recreating the accepted arrangement's phrasing.

The current importer supports synchronous MIDI with a positive ticks-per-quarter division and a constant tempo and meter. It rejects varying tempo/meter maps, unmatched note endings and omitted sounding tracks. Printed/PDF notation requires a corresponding MIDI or transcription first. See [the source workflow](song-workflow.md#information-boundaries) for the preservation contract.

## Declare the reduction and sounds

[The reduction configuration](../../config/own-score/reduction.json) selects `[0, 10)` in source quarter beats, ending before the next pickup at 11.75. Notes ending at beat 10 are retained; a note crossing the selected boundary would be rejected. This is an excerpt ending, not the complete work's ending.

| Musical role | Source → physical voice | Explicit reduction | Native sound |
| --- | --- | --- | --- |
| Upper manual gestures | `right-manual` → `$D400`, voice 1 | Highest simultaneous note; omit lower octave/chord tones | `lead`: pulse waveform with a looping pulse-width program |
| Pedal foundation | `pedal` → `$D400`, voice 2 | Preserve the D2 from beat 6 through beat 10 | `bass`: sustained pulse and its shared-filter program |
| Lower manual gestures and resolution | `left-manual` → `$D400`, voice 3 | Highest simultaneous note; shorten an overlapping predecessor to the next onset | `harmony`: sustained triangle/pulse combination |

This projection retains 31 of the selected 50 source notes: 14 melody, one pedal and 16 harmony events. The 19 omitted notes remain in both the complete source and explicit omission records. Two left-manual durations change: G3 at beat 7 becomes two beats instead of 2¼, and D3 at beat 9 becomes ¼ beat instead of one. This preserves the following source onsets on one physical voice; it cannot preserve independent overlapping tails. Removing `overlapPolicy: "shorten-to-next-onset"` makes the preparer reject these overlaps rather than silently altering them. No pitch transposition, new notes or extra accompaniment is introduced.

[The native template](../../config/own-score/native.json) declares one MOS8580 at `$D400`, PAL timing, one player update per video frame, and a contiguous section assigning all three voices. It reuses the lead PWM and sustained support programs from the [Bach opening palette](../../songs/studies/bach-toccata-opening/hybrid.json). The bass program owns the shared filter changes; the other two have empty filter tables. There is no ring/sync dependency or stereo routing. The earlier palette's listening scope does not approve this new reduction or timing. Retrieve alternatives through the [technique index](../research/technique-index.md) and [instrument cards](../research/composition/instruments/README.md) before changing sounds.

The `instrument` entries in the reduction file satisfy the arranged-score format; native playback takes its actual sound programs from `native.json` and its `sections` mapping. [The plain template](../../config/own-score/plain.json) instead uses one sustained triangle program on all voices. It provides a same-notes, same-timing SID control of the reduced score; it is neither a full-polyphonic source rendition nor an organ-performance reference.

## Prepare and build the first playable output

Use fresh directories for the preparer and native builder:

```sh
PYTHONPATH=.tools/arrangement-deps python3 scripts/prepare-score-audition.py songs/studies/bach-toccata-opening/source/ToccataFugue.mid config/own-score/import.json --arrangement config/own-score/reduction.json --candidate config/own-score/native.json --reference config/own-score/plain.json --output build/own-score-inputs
python3 scripts/native-song.py build build/own-score-inputs/candidate.json --output build/own-score-native --excerpt-seconds 8
```

The preparer preserves unchanged `source.mid`, `import-recipe.json`, `full-common-score.json`, the selected `common-score.json`, reduced `score.json`, complete `adaptation.json`, and candidate/reference recipes pointing to that generated score. Review `adaptation.json` before treating the reduction as musically faithful. The source hash must match; never change the expected hash merely to bypass a mismatch.

The main outputs are `build/own-score-native/export/candidate.sid` and `build/own-score-native/export/candidate.prg`. Open the SID in a PSID-compatible player with PAL timing and MOS8580 selected. Autostart the PRG on a matching C64/VICE configuration; [playback instructions](../../README.md#playback-formats) also cover manual loading. `build/own-score-native/conversion/candidate.swm` is the editable native song. `native-song.wav` is an optional approximately 13.51-second preview, including the release and verification tail; `native-song.excerpt.wav` contains the first eight seconds. The explicit excerpt length matters because the builder's default is 20 seconds, longer than this example.

The build audits the complete native schedule and renders the SID, checking nonzero signal, clipping and the quiet ending. `verification.json`, `conversion.json` and `export.json` retain the evidence and target. These checks establish scheduling and emulated signal health; they do not establish speaker playback, a physical-chip match or musical acceptance. Native editor changes do not flow back into JSON; preserve them as a separate native version under the [native-source contract](native-song-workflow.md#frozen-release-source-and-publication).

For an NTSC target, build deliberately from the same prepared source:

```sh
python3 scripts/native-song.py build build/own-score-inputs/candidate.json --clock ntsc --output build/own-score-native-ntsc --excerpt-seconds 8
```

This recompiles note frequencies and timing for NTSC; it is not a renderer-only switch. Native per-frame modulation and envelope behavior retain the [regional-export limits](native-song-workflow.md#regional-export-targets). For MOS6581, copy the native template, change `sidModel`, and prepare/build a new candidate; select the corresponding model in playback.

With [headless VICE and ROMs](../setup/local-setup.md) installed, the `score` readiness profile additionally checks Mido and the emulator resources. Independently check the PAL standalone PRG against the CPU-write evidence, including a checkpoint after the stop at tick 626:

```sh
python3 scripts/doctor.py --profile score --sid-count 1 --vice-data .tools/vice-headless-3.9/source/data
python3 scripts/verify-native-vice.py build/own-score-native/export/candidate.prg build/own-score-native/native-song.writes.json --export-report build/own-score-native/export.json --data .tools/vice-headless-3.9/source/data --calls 1 3 301 451 626 650 --output build/own-score-vice
```

These commands select the project headless build and its resource directory explicitly. If installed elsewhere, pass the same executable with `--vice PATH` to both commands and its resource directory as doctor's `--vice-data PATH` and the verifier's `--data PATH`.

## Repeat the comparison through one recipe

[The own-score listening recipe](../../config/listening/own-score-midi.json) performs the same preparation, builds both native palettes, and creates phrase and ending comparisons. It uses repository-relative dependencies and needs no VICE installation or optional archive. Repeating it reuses only stages whose inputs and outputs still match their recorded hashes:

```sh
python3 scripts/listening-package.py config/listening/own-score-midi.json --output build/own-score-package
```

Open the generated `build/own-score-package/listening.md` for direct SID, PRG, SWM, full-render, comparison and receipt links. A is always the plain reduced-score control; B is the configured SID palette. Both comparisons preserve original amplitudes, with a half-second gap:

| File | Source window | Review purpose |
| --- | --- | --- |
| `plain-then-sid-phrase.ab.wav` | 0–8 seconds | Recognizable gesture and role balance |
| `plain-then-sid-ending.ab.wav` | 8–13 seconds | Resolution, release and termination |

The full reference and candidate WAV links remain alongside both comparisons. For an actual musical revision, follow the [listening-review contract](audio-comparisons.md#package-a-listening-review), state one clear judgment per comparison and retain the human verdict. Producing this onboarding package does not open another Bach listening round or change any existing verdict.

## Adapt the example to your MIDI

Copy the four files under [the example configuration](../../config/own-score/) to your own configuration directory. Preserve your original MIDI, attribution, usage terms and reference separately. Inspect its track names, note content, tempo, meter, repeats and final rest; replace `sourceFile`, `sourceSha256`, title, composer, provenance and every `parts` mapping in the import recipe. All sounding tracks must be imported. Change the source path in the preparation command and listening recipe as well.

Choose the intended mood and source roles before picking sounds. In the reduction recipe, change `spans`, map each part exactly once to a voice or document it in `omittedParts`, and choose the monophonic policies deliberately. `highest-at-onset` is this example's reduction, not a general solution for arbitrary polyphony. Explicit event omissions and successive part ownership are supported by [the preparer contract](song-workflow.md#prepare-a-multitrack-score-audition). Verify the adaptation report against your source, then update the native section endpoints and voice names to cover your reduced score completely. Set the phrase/ending windows to fit that score, not this ten-beat example.

New-score dual SID needs manual six-voice authoring by you or the assisting agent after intake: the generic preparer produces exactly three voices. Merely setting `sidCount` to 2 cannot expand them. Author the six-voice arranged score and native section map, record role → chip/voice → coupling/filter ownership → output matrix, and use the [native dual-SID workflow](native-song-workflow.md#reusable-two-chip-test) and [hardware/mixing contract](../research/sid/dual-sid.md#plan-the-sound-hardware-and-the-mix-together). The current native exporter uses the same SID model on both chips; each chip supplies one mono output and a shared filter.

## Verification record

On 2026-10-17, the commands above imported all 3,651 source notes, accounted for all 50 selected notes and completed PAL and NTSC native builds. The PAL audit checked 679 calls, all 31 note starts and cleared gates/volume after stop tick 626. Its 44.1 kHz mono preview contained zero clipped samples and final-half-second AC RMS 0. Independent headless VICE boot/register/cadence checkpoints passed through 650 completed calls; this is sampled standalone evidence, not continuous write identity. The five-stage listening recipe also completed; its reference uses the identical reduced score. The generated local receipts own exact hashes and timings. No human listening or physical-SID acceptance is claimed; cold-clone setup and host results are separate evidence.
