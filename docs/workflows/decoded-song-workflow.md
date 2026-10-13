# Compose from decoded SID instruments

Use this workflow to turn executed-program findings into editable music and our own 6502 player. Start with the [analysis procedure](../research/tools/sid-program-analysis.md) and [musical mechanism library](../research/composition/instruments/drax-decoded-trio.md). The first complete example is [DRAX's recurring Für Elise theme](../../songs/studies/drax-full-reconstruction/README.md); it is not Beethoven's complete formal score.

For preparation before a backend exists, the [Cybernoid II numeric model](../research/composition/cybernoid-ii-preparation.md#compose-the-complete-title-from-editable-data) demonstrates source-free score/program composition and complete ordered-register comparison. Its owning study provides the editable-data restoration and Python API; it does not yet export or render a C64 player.

## Deliver one musical case

Use the [study plan](../research/study-plan.md#delivery-order-and-work-in-progress) to select the case. Name the next musical deliverable and its acceptance question before starting work; an existing verified numeric model should lead to an audible export, rather than another broad decoding exercise.

1. Retrieve the relevant instrument cards and existing score/program model. Declare the selected full form, chip/clock/cadence and ending; retain source differences explicitly.
2. Implement only the missing export or expressive behavior that this deliverable requires. Preserve editable musical inputs and use existing verified components where their contracts fit. Do not force a different driver into an unsuitable shared format.
3. Verify the required ordered writes, compiled execution, real playback cadence and rendered signal health, including the complete ending. Use the owning study's CPU/VICE contract; a short audition does not reduce verification coverage. Reuse valid receipts for unchanged inputs instead of repeating passed checks.
4. Supply the [listening package](audio-comparisons.md#package-a-listening-review) and record sound/phrasing, complete-form and ending judgments separately. Revise against actual feedback; do not infer approval from rendering success.
5. Compose an original phrase using the promoted mechanisms, with changed musical material and explicit editable parameters. Verify it, add its listening file to the package, and request its separate musical and ending verdict. Acceptance of the reconstruction alone does not prove useful transfer.
6. Record the reuse outcome below, link the executable example and limitations from the owning card, and close the case only when the plan's completion contract is satisfied.

For additional investigation, follow the [analysis stopping rule](../research/tools/sid-program-analysis.md#bound-the-investigation). Preserve deferred experiments without allowing them to expand the active case.

## Record reuse and effort

Keep one compact outcome record in the owning study or [instrument card](../research/composition/instrument-card-template.md#reuse-outcome), linking it elsewhere rather than copying it. Record the original phrase, named components reused unchanged or adapted, new components required, listening-driven revision count and the final verdict. This shows whether the mechanism can serve new music and what still makes reuse difficult.

Measure effort prospectively from the start of a transfer attempt to its accepted phrase. State the measurement basis: active work time excludes listener waiting; elapsed time includes it. Keep parallel-agent effort separate when available. If reliable timing or revision history is absent, write `not recorded`; do not invent historical estimates. Pending acceptance means the result is still pending, not a time-to-success measurement.

Compare similar completed transfers before claiming improved productivity. Use the record to choose a concrete improvement for the next phrase, such as removing repeated manual setup or exposing a needed parameter. Do not build a metrics subsystem or a general backend without a demonstrated need.

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

The [secondary description](../../songs/flashdance-secondary.json) supplies harmonic support and backbeats while the primary retains its accepted score and programs. The dual compiler assembles each engine at a separate RAM address, then calls A followed by B once per PAL frame. Profiles, score stops and ending parameters must agree. The output is PSID v3 for two MOS6581 chips at `$D400/$D420`; source annotations cannot supply executable playback.

```sh
PYTHONPATH=.tools/test-deps python3 scripts/compose-flashdance-dual.py songs/flashdance-decoded.json songs/flashdance-secondary.json --output build/flashdance-dual-new
python3 scripts/trace-sid-vice.py build/flashdance-dual-new/reconstructed.sid --oracle build/flashdance-dual-new/writes.json --first-call 0 --last-call 1666 --output build/flashdance-dual-new/vice
.local/bin/render-sid build/flashdance-dual-new/reconstructed.sid build/flashdance-dual-new/raw-stereo.wav 35
python3 scripts/prepare-dual-listening.py build/flashdance-dual-new/raw-stereo.wav --output build/flashdance-dual-new/listening --start 8 --stop 16
```

The raw renderer output places chip A left and chip B right; this is the accepted stereo presentation for the current Flashdance arrangement. The listening tool makes a centered-primary stereo mix, mono downmix and three/six-voice comparison using explicit common gains, recording matrices and PCM measurements. It expects independent chip channels, not an arbitrary stereo master, and does not normalize each side separately. The [owning study](../research/composition/flashdance-preparation.md#deliberate-dual-sid-interpretation) records musical choices, execution limits and the separate listening verdict.

### Shades compiled CIA player

The [Shades score](../../songs/shades-score.json) and [program bank](../../songs/shades-programs.json) are separate editable inputs to [compose-shades.py](../../scripts/compose-shades.py). The compiler emits our [scheduler and writers](../../songs/players/shades.asm), [computed effects](../../songs/players/shades-effects.asm), compact pattern tokens, order records and named initial state. Neither the reference SID nor a captured store ledger is a build input. The unchanged full description uses 56 patterns, 3,520 tokens, 128 orders and 14 program blocks in an 8,282-byte payload. See the [owning study](../research/composition/shades-preparation.md#reconstruction-boundary) and [instrument card](../research/composition/instruments/shades-decoded-programs.md) for recovered mechanisms and musical limits.

Build the full traversal and the [independently authored transfer phrase](../../songs/shades-transfer.json) with its [edited program bank](../../songs/shades-transfer-programs.json), then establish real IRQ cadence in fresh directories:

```sh
python3 scripts/compose-shades.py songs/shades-score.json --programs songs/shades-programs.json --output build/shades-independent-new
PYTHONPATH=.tools/test-deps python3 scripts/trace-shades-vice.py build/shades-independent-new/reconstructed.sid --candidate --calls 24386 --output build/shades-independent-new/vice
python3 scripts/compose-shades.py songs/shades-transfer.json --programs songs/shades-transfer-programs.json --output build/shades-transfer-new
PYTHONPATH=.tools/test-deps python3 scripts/trace-shades-vice.py build/shades-transfer-new/reconstructed.sid --candidate --calls 1522 --output build/shades-transfer-new/vice
```

The compiler writes `reconstructed.sid`, assembly/listing, `build.json`, `audit.json` and ordered `writes.json`. Its default audit covers all score calls plus the one authored stop call and compares every SID and `$DC05` store against [the Python model](../../scripts/shades_player.py). `--calls` selects a bounded prefix through that stop. The shown VICE call counts belong to the unchanged retained inputs; timing edits require corresponding coverage. Rendering and listening use the [audio workflow](audio-workflow.md) and remain separate evidence.

- The PSID v2 header declares one PAL MOS6581 and CIA speed word `$00000001`. The host owns Timer A's low latch `$25`; each order supplies its high byte. Use the [CIA candidate auditor and tracer](../validation/cia-tracing.md#generated-candidate-api) rather than the VBI auditor or fixed-frame tracer.
- Init restores the complete named state and scheduler without SID or CIA stores. Call 0 selects the first block and writes only `$DC05`; the first score row is call 1. Effects continue through hold and release, before row fade, block selection and ordered voice/filter writers. At `range.stopCall`, the player writes zero to the three controls and master volume once; subsequent calls emit no stores. Reinitialization restores the same behavior.
- Orders support 1–256 rows and 1–256 calls per row, signed byte transposes and resolved frequency-table indices 0–95. The compiler checks the entire score and program inputs, uses absolute pattern pointers, permits at most 85 selected program blocks and rejects payloads outside callable RAM or overlapping the CIA host workspace. Provenance annotations do not affect bytes.

On 2026-10-13, the [full candidate VICE receipt](../../evidence/shades-independent-full/vice/study.json.gz) verifies 24,386 calls and 296,911 ordered stores, with maximum interval/phase errors of 4/2 cycles. The [transfer receipt](../../evidence/shades-transfer/vice/study.json.gz) verifies 1,522 calls and 10,734 stores, with errors of 4/3 cycles. These checks establish compiled execution and cadence in the declared host; they do not establish bus timing, PCM identity or a listening verdict.

### Other drivers

[describe-drax-score.py](../../scripts/describe-drax-score.py) is a pinned, driver-specific transcriber, not a universal SID importer. It observes executed note consumption, instrument initialization and score gate-off, then verifies preparation and repeat behavior. Use `--check` to compare its output with the retained fixture. For another player, recover its corresponding readers and state transitions before adapting the decoder. [The Flashdance study](../research/composition/flashdance-preparation.md) demonstrates its own decoded mechanisms and independently authored dual-SID arrangement.

The [Shades study](../research/composition/shades-preparation.md#reconstruction-boundary) distinguishes source comparison, compiled execution, CIA cadence, rendered audio and listening. A computed store ledger alone remains diagnostic output; the compiled backend above supplies separate CPU and VICE evidence.
