# Compose from decoded SID instruments

Use this workflow to turn executed-program findings into editable music and our own 6502 player. Start with the [analysis procedure](research/tools/sid-program-analysis.md) and [musical mechanism library](research/composition/instruments/drax-decoded-trio.md). The first complete example is [DRAX's recurring Für Elise theme](../songs/studies/drax-full-reconstruction/README.md); it is not Beethoven's complete formal score.

## Build, render and compare

After [headless audio setup](audio-workflow.md), choose a fresh output directory:

```sh
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 scripts/compose-sid.py songs/studies/drax-full-reconstruction/full-composition.json --output build/drax-full-listen --reference .local/research/fuer-elise/drax-fuer-elise.sid --vice
```

Omit `--reference` to build without the original SID; omit `--vice` to skip the independent emulator check. The compiler reads only the musical description, its referenced initialization profile and our [computed player](../songs/players/decoded-trio.asm). Original bytes enter only the optional comparison stage. Outputs include `reconstructed.sid`, assembly/listing, CPU audit, ordered writes, WAVs and a concise validation receipt. Keep generated evidence under ignored `build/`.

The original reference loops; our export stops at `range.stopCall` and closes all gates and volume. Both WAVs retain identical renderer settings, duration and unity gain. The reference's final verification tail consequently begins its next cycle. Neither file is independently normalized or equalized.

## Editable contract

The [example description](../songs/studies/drax-full-reconstruction/full-composition.json) uses `sid-decoded-composition-v1`:

- `roles` assigns exactly bass, lead and chord to hardware voices 1, 2 and 3. Each note supplies an absolute `initCall`, exact SID `frequency` word and named patch. Preparation occupies the two preceding calls.
- Lead/chord `gateOffCall` belongs to the score. Bass gate closure belongs to its patch. Modulation and chord cycling continue after gate-off.
- Chord `frequency` describes TEST preparation; `frequencies` contains the audible repeating pitch program, two calls per tone. These can differ because preparation inherits previous program state. Patch `pulseInitial` controls its width.
- Patches hold executable envelope, waveform, width, modulation and filter parameters. Eight signed `vibratoDeltas` describe a reusable cycle, not a recording. `sourceEvidence`, top-level provenance and boundary annotations are nonexecuting analysis; edit runtime fields to change sound.
- `bassRecipe` supplies hard-restart values and silent bass prehistory; the composition's bass patch owns its active instrument parameters. Lead/chord prehistory is part of this backend's documented DRAX family.

## Supported scope and guards

This backend supports one PAL MOS6581, one update per 19,656 cycles, one bass patch, one lead patch and static-width chord variants sharing an envelope/waveform. It rejects unsupported profiles, roles, unknown runtime fields, overlapping preparations, oversized banks and holds that could wrap instrument age. Each role accepts up to 255 notes; scheduling uses 16-bit calls. Chord widths use whole high bytes. Waveform staging, arbitrary update rates and dual SID require explicit backend work; the format does not claim universal chip coverage.

Compilation computes PWM, vibrato, attack stages, releases and arpeggios; it includes neither original driver instructions nor captured-register playback. Validation compares every ordered write, including repeated shared-filter writes, then independently executes the candidate in VICE. It also checks duration, clipping and a settled audio tail. Equal call/address/value/order does not establish equal within-call bus timing, oscillator phase, hardware sound or listener approval.

## Recover another arrangement

[describe-drax-score.py](../scripts/describe-drax-score.py) is a pinned, driver-specific transcriber, not a universal SID importer. It observes executed note consumption, instrument initialization and score gate-off, then verifies preparation and repeat behavior. Use `--check` to compare its output with the retained fixture. For another player, recover its corresponding readers and state transitions before adapting the decoder. [Flashdance preparation](research/composition/flashdance-preparation.md) identifies the next mechanisms and the separate dual-SID arrangement plan.
