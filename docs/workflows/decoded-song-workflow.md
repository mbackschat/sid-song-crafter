# Compose from decoded SID instruments

Use this workflow to turn executed-program findings into editable music and our own 6502 player. Start with the [analysis procedure](../research/tools/sid-program-analysis.md) and [musical mechanism library](../research/composition/instruments/drax-decoded-trio.md). The first complete example is [DRAX's recurring Für Elise theme](../../songs/studies/drax-full-reconstruction/README.md); it is not Beethoven's complete formal score.

## Build, render and compare

After [headless audio setup](audio-workflow.md), choose a fresh output directory:

```sh
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 scripts/compose-sid.py songs/studies/drax-full-reconstruction/full-composition.json --output build/drax-full-listen --reference .local/research/fuer-elise/drax-fuer-elise.sid --vice
```

Omit `--reference` to build without the original SID; omit `--vice` to skip the independent emulator check. The compiler reads only the musical description, its referenced initialization profile and our [computed player](../../songs/players/decoded-trio.asm). Original bytes enter only the optional comparison stage. Outputs include `reconstructed.sid`, assembly/listing, CPU audit, ordered writes, WAVs and a concise validation receipt. Keep generated evidence under ignored `build/`.

The original reference loops; our export stops at `range.stopCall` and closes all gates and volume. Both WAVs retain identical renderer settings, duration and unity gain. The reference's final verification tail consequently begins its next cycle. Neither file is independently normalized or equalized.

## Editable contract

The [example description](../../songs/studies/drax-full-reconstruction/full-composition.json) uses `sid-decoded-composition-v1`:

- `roles` assigns exactly bass, lead and chord to hardware voices 1, 2 and 3. Each note supplies an absolute `initCall`, exact SID `frequency` word and named patch. Preparation occupies the two preceding calls.
- Lead/chord `gateOffCall` belongs to the score. Bass gate closure belongs to its patch. Modulation and chord cycling continue after gate-off.
- Chord `frequency` describes TEST preparation; `frequencies` contains the audible repeating pitch program, two calls per tone. These can differ because preparation inherits previous program state. Patch `pulseInitial` controls its width.
- Patches hold executable envelope, waveform, width, modulation and filter parameters. Eight signed `vibratoDeltas` describe a reusable cycle, not a recording. `sourceEvidence`, top-level provenance and boundary annotations are nonexecuting analysis; edit runtime fields to change sound.
- `bassRecipe` supplies hard-restart values and silent bass prehistory; the composition's bass patch owns its active instrument parameters. Lead/chord prehistory is part of this backend's documented DRAX family.

## Supported scope and guards

This backend supports one PAL MOS6581, one update per 19,656 cycles, one bass patch, one lead patch and static-width chord variants sharing an envelope/waveform. It rejects unsupported profiles, roles, unknown runtime fields, overlapping preparations, oversized banks and holds that could wrap instrument age. Each role accepts up to 255 notes; scheduling uses 16-bit calls. Chord widths use whole high bytes. Waveform staging, arbitrary update rates and dual SID require explicit backend work; the format does not claim universal chip coverage.

Compilation computes PWM, vibrato, attack stages, releases and arpeggios; it includes neither original driver instructions nor captured-register playback. Validation compares every ordered write, including repeated shared-filter writes, then independently executes the candidate in VICE. It also checks duration, clipping and a settled audio tail. Equal call/address/value/order does not establish equal within-call bus timing, oscillator phase, hardware sound or listener approval.

## Recover another arrangement

### Flashdance description

The separate [Flashdance composition](../../songs/flashdance-decoded.json) describes the selected arrangement's entire 1,536-call score cycle plus two startup calls. Its [owning study](../research/composition/flashdance-preparation.md) distinguishes this abbreviated arrangement from the original song. Regenerate or check the portable description from the pinned local reference:

```sh
PYTHONPATH=.tools/test-deps python3 scripts/describe-flashdance-score.py .local/research/flashdance/drax-flashdance-conversion.sid --composition --output songs/flashdance-decoded.json --check
```

Omit `--check` and choose a fresh output path to create a description. Importing verifies the reference identity and executed score consumption; subsequent model execution uses only JSON. `flashdance_player.compute_writes(description)` computes the selected comparison span, while an explicit `calls` includes the authored ending. These Python writes are a synthesis-model oracle, not a SID export or listening result.

- `score.roles` contains ordered instrument, note, hold, off and effect commands. Notes select a frequency-table index plus semitone transposition; `restart: false` preserves instrument progression. Instrument programs can clear gate independently of score-off.
- `programs` contains editable frequency words, waveform/pitch rows, PWM rows, filter rows and instrument bindings. Rows and retained state use checked byte/word arithmetic. PWM reverses on high-byte equality; filter reversal uses separate crossing rules.
- `initialEffects` and `preloaded` preserve the startup and retained modulation state needed before the first note. One declared voice owns the shared filter. `fineTuneWord` provides each voice's word offset.
- `ending.releaseCalls` continues modulation with gates cleared; `fadeStepCalls` determines the subsequent volume staircase. The default is 64 release calls and four calls per fade step. `sourceEvidence` and source addresses are annotations, so musical edits do not require rewriting provenance.

This description targets one PAL MOS6581 at one update per 19,656 cycles. Its program bank supports the decoded instrument/filter modes and checked links; it does not imply a universal importer. Run [the scheduler guards](../../tests/flashdance_player_test.py) with the score, program and pitch suites when changing these mechanisms.

Build our independent player, then verify and render it into fresh paths:

```sh
PYTHONPATH=.tools/test-deps python3 scripts/compose-flashdance.py songs/flashdance-decoded.json --output build/flashdance-new
python3 scripts/trace-sid-vice.py build/flashdance-new/reconstructed.sid --oracle build/flashdance-new/writes.json --first-call 0 --last-call 1666 --output build/flashdance-new/vice
.local/bin/render-sid build/flashdance-new/reconstructed.sid build/flashdance-new/reconstructed.wav 35
.local/bin/render-sid .local/research/flashdance/drax-flashdance-conversion.sid build/flashdance-new/reference.wav 35
```

The compiler emits SID, assembly/listing, build metadata, CPU audit and ordered writes. By default it audits the score, complete ending and first silent call against the model. `--calls` selects a bounded diagnostic override. The shown VICE window and render duration apply to the unchanged retained composition; edits to its score or ending require corresponding coverage. The compiler itself requires no reference file. See [measured differences and listening status](../research/composition/flashdance-preparation.md#independent-export-and-listening) before reusing its instruments as an accepted sound.

### Add an independently authored second chip

The [secondary description](../../songs/flashdance-secondary.json) supplies harmonic support, backbeats and replies while the primary retains its accepted score and programs. The dual compiler assembles each engine at a separate RAM address, then calls A followed by B once per PAL frame. Profiles, score stops and ending parameters must agree. The output is PSID v3 for two MOS6581 chips at `$D400/$D420`; source annotations cannot supply executable playback.

```sh
PYTHONPATH=.tools/test-deps python3 scripts/compose-flashdance-dual.py songs/flashdance-decoded.json songs/flashdance-secondary.json --output build/flashdance-dual-new
python3 scripts/trace-sid-vice.py build/flashdance-dual-new/reconstructed.sid --oracle build/flashdance-dual-new/writes.json --first-call 0 --last-call 1666 --output build/flashdance-dual-new/vice
.local/bin/render-sid build/flashdance-dual-new/reconstructed.sid build/flashdance-dual-new/raw-stereo.wav 35
python3 scripts/prepare-dual-listening.py build/flashdance-dual-new/raw-stereo.wav --output build/flashdance-dual-new/listening --start 8 --stop 16
```

The raw renderer output places chip A left and chip B right. The listening tool makes a centered-primary stereo mix, mono downmix and three/six-voice comparison using explicit common gains, recording matrices and PCM measurements. It expects independent chip channels, not an arbitrary stereo master, and does not normalize each side separately. The [owning study](../research/composition/flashdance-preparation.md#deliberate-dual-sid-interpretation) records musical choices, execution limits and the separate listening verdict.

### Other drivers

[describe-drax-score.py](../../scripts/describe-drax-score.py) is a pinned, driver-specific transcriber, not a universal SID importer. It observes executed note consumption, instrument initialization and score gate-off, then verifies preparation and repeat behavior. Use `--check` to compare its output with the retained fixture. For another player, recover its corresponding readers and state transitions before adapting the decoder. [Flashdance preparation](../research/composition/flashdance-preparation.md) identifies the next mechanisms and the separate dual-SID arrangement plan.
