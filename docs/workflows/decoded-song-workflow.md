# Compose from decoded SID instruments

Use this workflow to turn executed-program findings into editable music and our own 6502 player. Start with the [analysis procedure](../research/tools/sid-program-analysis.md) and [musical mechanism library](../research/composition/instruments/drax-decoded-trio.md). The first complete example is [DRAX's recurring Für Elise theme](../../songs/studies/drax-full-reconstruction/README.md); it is not Beethoven's complete formal score.

The [Cybernoid II compiled title](#cybernoid-ii-compiled-title) builds an independent C64 player from editable semantic rows and numeric programs. Its [owning study](../research/composition/cybernoid-ii-preparation.md#compose-the-complete-title-from-editable-data) retains source provenance, recovered mechanisms and validation boundaries.

## Deliver one musical case

Use the [study plan](../research/study-plan.md#delivery-order-and-work-in-progress) to select the case. Name the next musical deliverable and its acceptance question before starting work; an existing verified numeric model should lead to an audible export, rather than another broad decoding exercise.

1. Retrieve the relevant instrument cards and existing score/program model. Declare the selected full form, chip/clock/cadence and ending; retain source differences explicitly.
2. Implement only the missing export or expressive behavior that this deliverable requires. Preserve editable musical inputs and use existing verified components where their contracts fit. Do not force a different driver into an unsuitable shared format.
3. Verify the required ordered writes, compiled execution, real playback cadence and rendered signal health, including the complete ending. Use the owning study's CPU/VICE contract; a short audition does not reduce verification coverage. Reuse valid receipts for unchanged inputs instead of repeating passed checks.
4. Supply the [listening package](audio-comparisons.md#package-a-listening-review) and record sound/phrasing, complete-form and ending judgments separately. Revise against actual feedback; do not infer approval from rendering success.
5. Apply the promoted mechanisms to different musical material with explicit editable parameters. Prefer a familiar, source-backed phrase and provide a same-material reference so composition quality does not obscure the instrument comparison. Label a generated score reference as such; it is not an original recording. Verify it, add its listening file to the package, and request its separate musical and ending verdict. Acceptance of the reconstruction alone does not prove useful transfer.
6. Record the reuse outcome below, link the executable example and limitations from the owning card, and close the case only when the plan's completion contract is satisfied.

For additional investigation, follow the [analysis stopping rule](../research/tools/sid-program-analysis.md#bound-the-investigation). Preserve deferred experiments without allowing them to expand the active case.

## Record reuse and effort

Keep one compact outcome record in the owning study or [instrument card](../research/composition/instrument-card-template.md#reuse-outcome), linking it elsewhere rather than copying it. Record the transfer phrase and its source, named components reused unchanged or adapted, new components required, listening-driven revision count and the final verdict. This shows whether the mechanism can serve new music and what still makes reuse difficult.

Measure effort prospectively from the start of a transfer attempt to its accepted phrase. State the measurement basis: active work time excludes listener waiting; elapsed time includes it. Keep parallel-agent effort separate when available. If reliable timing or revision history is absent, write `not recorded`; do not invent historical estimates. Pending acceptance means the result is still pending, not a time-to-success measurement.

Compare similar completed transfers before claiming improved productivity. Use the record to choose a concrete improvement for the next phrase, such as removing repeated manual setup or exposing a needed parameter. Do not build a metrics subsystem or a general backend without a demonstrated need.

## Build, render and compare

Follow the project-wide [automation rule](../../CLAUDE.md#automate-routine-execution). If preparation, verification or packaging becomes a repeated sequence of tool calls or sub-agent handoffs, put that sequence into reusable code or a recipe with explicit inputs, deadlines, checks and retained outputs before repeating it. Reuse existing helpers; keep novel analysis and musical judgments outside the routine execution.

For repeatable deliveries, use the [listening-package runner](listening-package.md) to execute the existing driver-specific commands with timings and verified stage reuse. The [Monty recipe](../../config/listening/monty-reference-continuation.json) covers full CPU/source checks, a VICE restart check, renders, signal checks and A/B clips. Keep each backend’s declared coverage; cached results replace execution only when their input, tool and output fingerprints still match.

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
PYTHONPATH=.tools/test-deps python3 scripts/studies/flashdance/describe-flashdance-score.py .local/research/flashdance/drax-flashdance-conversion.sid --composition --output songs/flashdance-decoded.json --check
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

### Cybernoid II compiled title

The [editable title](../../songs/cybernoid-title.json), in `cybernoid-editable-title-v1` format, preserves the first complete title traversal at calls `[0,17280)` and adds a deliberate 128-call release/fade, for 17,408 total play calls. The source loops; this finite ending is an arrangement addition. [compose-cybernoid.py](../../scripts/compose-cybernoid.py) assembles our [scheduler and writers](../../songs/players/cybernoid.asm), [pitch engine](../../songs/players/cybernoid-pitch.asm) and [pulse/filter/wave engine](../../songs/players/cybernoid-effects.asm), with deduplicated semantic row payloads, per-voice call schedules and named initial state. It includes neither original driver instructions nor captured-register playback. See the [owning study](../research/composition/cybernoid-ii-preparation.md) for source constraints and evidence.

- The player targets one PAL MOS6581 at one update per 19,656 cycles. Its PSID v2 header declares VBI scheduling. The compiler accepts 1–65,535 declared calls and requires the complete payload to fit callable RAM `$0400–$9FFF`.
- Each row supplies an absolute `call`, `voiceIndex` 0–2, byte `transpose`, `patchSetup` (`initialize` or `preserve`) and ordered commands: `routing`, `sound`, `duration`, `extendDuration`, `arpeggio`, `glide` and a final `note`. There is at most one selected row per voice/call. Duration or tempo edits must reschedule later row calls consistently; compilation rejects disagreement with the retained countdowns.
- Editable runtime inputs include 257 frequency words, eight-byte sound records, vibrato waits, onset lengths/waves, eight-byte pulse slots, ten-byte filter programs, arpeggios, drum waveform/pitch programs, `initial_state` and `sid_init`. Note, transpose, arpeggio and glide-target indices use byte arithmetic; vibrato adjacency can read frequency index 256. Init and reinit restore the declared cold state and schedules, including voice 2's `$0800` pulse output.
- Optional `ending` contains positive `start_call`, nonnegative `release_calls` and `fade_step_calls` in 1–255. Rows must precede `start_call`, and `play_calls` must equal `start_call + release_calls + 16 * fade_step_calls`. Without `ending`, the declared range alone does not promise gate closure or silence.

During the ending, the row calendar and tempo countdown stay fixed while sound programs continue. Note age saturates at 255, and every voice gate is cleared after effects and before its final writer. All `$D418` stores retain their mode high nibble and use the current tail-volume low nibble, so filter updates cannot restore volume between fade steps; each tail call also writes the resulting mode/volume after the voices. The retained title uses 64 release calls at volume 15 followed by sixteen levels 15 through 0, four calls per level. After call 17,407, subsequent play calls emit no stores or change player state. This contract defines an ending; rendered signal health and musical acceptance require separate checks.

Check the canonical preparation and build into a fresh directory:

```sh
python3 scripts/studies/cybernoid/prepare-cybernoid-title.py --output songs/cybernoid-title.json --check
python3 scripts/compose-cybernoid.py songs/cybernoid-title.json --output build/cybernoid-independent-new
```

[prepare-cybernoid-title.py](../../scripts/studies/cybernoid/prepare-cybernoid-title.py) verifies the pinned decompressed evidence fingerprint, retains the first traversal and numeric programs/cold state, removes nested derivation annotations and declares the added ending. To create an editable copy, use `python3 scripts/studies/cybernoid/prepare-cybernoid-title.py --output build/cybernoid-prepared-new/title.json` with a fresh output path. Preparation and compilation require no original SID. `sourceEvidence` is nonexecuting provenance; changing it does not change synthesis. Original reference SIDs and WAVs remain under the [public repository boundary](../../AGENTS.md#public-repository-boundary).

The compiler writes `reconstructed.sid`, assembly/listing, `build.json`, `audit.json` and ordered `writes.json`. By default it independently executes all declared music and ending calls and compares every ordered SID store with [the Python model](../../scripts/cybernoid_player.py). `--calls` selects a diagnostic prefix in 1–`play_calls`; it does not shorten the compiled description. Use the [callable PSID audit](../validation/psid-audit.md), real VICE cadence checks and the [audio workflow](audio-workflow.md) for their respective evidence. CPU/model agreement does not establish within-call bus timing, rendered sound or a listening verdict; retain those results in the owning study.

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

### Monty packed-score player

The [editable Monty title](../../songs/monty-title.json) retains the first complete order cycle at calls `[0,17536)` and adds 128 release/fade calls. [compose-monty.py](../../scripts/compose-monty.py) compiles our [runtime scheduler](../../songs/players/monty.asm) and [sound programs](../../songs/players/monty-effects.asm), with packed orders/patterns, a shared mutable instrument bank and typed pointers into named voice state. Score rows are consumed at runtime; the binary contains neither an original driver nor a captured-register schedule. The [owning study](../research/composition/monty-preparation.md) owns evidence and current listening status.

- Target: one PAL MOS6581, one update per 19,656 cycles, PSID v2 VBI scheduling. The complete payload must fit callable RAM `$0400–$9FFF`.
- Inputs: `monty-editable-title-v1`, three voice orders, numeric patterns, twenty source instruments or an edited bank of 1–32 records, 96 frequency words, explicit beyond-table aliases and named initial state. Source annotations are ignored during synthesis. Unsupported transport/overlay paths and missing reachable lookup bytes reject before compilation.
- Packed control bit `$40` appends the current instrument without a new pitch; otherwise bit `$80` adds an instrument/portamento parameter before the pitch byte. The low five bits reload remaining score ticks, with the next row selected one tick later. A pattern's terminal `$FF` advances the order; an order `$FF` restarts sequencing while retaining sound state.
- Optional `ending` requires `start_call > 0`, `release_calls=64`, `fade_step_calls=4` and `play_calls=start_call+128`, with initial master volume 15. It freezes score/tempo/remaining lengths, closes the actual output gates and continues body effects with the global counter advancing. Every later control store is gate-masked while saved controls remain intact for pitch aliases. Volume fades through sixteen four-call levels, retaining mode bits. Subsequent calls after the finite tail emit no stores or change named state. A no-ending export guarantees only the declared diagnostic window; do not present it as an indefinitely verified musical player.

Prepare the declared first cycle and build it without accessing the original SID:

```sh
python3 scripts/studies/monty/prepare-monty-title-ending.py --check
python3 scripts/studies/monty/prepare-monty-title-ending.py --output build/monty-title-prepared-new/title.json
PYTHONPATH=.tools/test-deps python3 scripts/compose-monty.py build/monty-title-prepared-new/title.json --output build/monty-title-new
```

Preparation binds the known cycle boundary to the pinned [numeric source description](../../songs/monty-title-source.json); edit the result for new arrangements. Re-extracting that numeric source uses [prepare-monty-title.py](../../scripts/prepare-monty-title.py) and the pinned local original, as documented in the study. The compiler emits SID, assembly/listing, build and CPU receipts, ordered writes and named-state checkpoints. Its default audit covers every declared call; `--calls` selects a diagnostic prefix without changing the composition.

For instrument reuse, the [Monty familiar-transfer card](../research/composition/instruments/monty-decoded-programs.md) provides matching 53-note Für Elise descriptions and an honest generated plain reference. `python3 scripts/studies/monty/prepare-monty-elise.py --check` verifies both saved inputs. Native articulation and envelope/rest behavior remain explicit conversion limits; full execution and rendered signal health do not supply a musical verdict.

### Other drivers

[describe-drax-score.py](../../scripts/studies/drax/describe-drax-score.py) is a pinned, driver-specific transcriber, not a universal SID importer. It observes executed note consumption, instrument initialization and score gate-off, then verifies preparation and repeat behavior. Use `--check` to compare its output with the retained fixture. For another player, recover its corresponding readers and state transitions before adapting the decoder. [The Flashdance study](../research/composition/flashdance-preparation.md) demonstrates its own decoded mechanisms and independently authored dual-SID arrangement.

The [Shades study](../research/composition/shades-preparation.md#reconstruction-boundary) distinguishes source comparison, compiled execution, CIA cadence, rendered audio and listening. A computed store ledger alone remains diagnostic output; the compiled backend above supplies separate CPU and VICE evidence.

For an accepted transfer of the Shades instruments to familiar musical material, use the [Für Elise comparison](../research/composition/instruments/shades-decoded-programs.md#familiar-transfer-accepted) and its [exact recipe](../research/composition/shades-elise-audio.json). `python3 scripts/studies/shades/prepare-shades-elise.py --check` verifies the retained score and plain reference bank. The same 53 source events feed both renderings; this demonstrates reusable sound programs without requiring the listener to judge an invented composition. The older eight-bar invented transfer above remains historical evidence with an unaccepted ending.
