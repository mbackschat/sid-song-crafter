# Compose from decoded SID instruments

Use this workflow to turn executed-program findings into editable music and our own 6502 player. Start with the [analysis procedure](../research/tools/sid-program-analysis.md) and [musical mechanism library](../research/composition/instruments/drax-decoded-trio.md). The first complete example is [DRAX's recurring Für Elise theme](../../songs/studies/drax-full-reconstruction/README.md); it is not Beethoven's complete formal score.

The [Cybernoid II compiled title](#cybernoid-ii-compiled-title) builds an independent C64 player from editable semantic rows and numeric programs. Its [owning study](../research/composition/cybernoid-ii-preparation.md#compose-the-complete-title-from-editable-data) retains source provenance, recovered mechanisms and validation boundaries.

## Deliver one musical case

Use the [study plan](../../PLAN.md#delivery-order-and-work-in-progress) to select the case. Name the next musical deliverable and its acceptance question before starting work; an existing verified numeric model should lead to an audible export, rather than another broad decoding exercise.

1. Retrieve the relevant instrument cards and existing score/program model. Declare the selected full form, chip/clock/cadence and ending; retain source differences explicitly.
2. Implement only the missing export or expressive behavior that this deliverable requires. Preserve editable musical inputs and use existing verified components where their contracts fit. Do not force a different driver into an unsuitable shared format.
3. Verify the required ordered writes, compiled execution, real playback cadence and rendered signal health, including the complete ending. Use the owning study's CPU/VICE contract; a short audition does not reduce verification coverage. Reuse valid receipts for unchanged inputs instead of repeating passed checks.
4. Supply the [listening package](audio-comparisons.md#package-a-listening-review) and record sound/phrasing, complete-form and ending judgments separately. Revise against actual feedback; do not infer approval from rendering success.
5. Apply the promoted mechanisms to different musical material with explicit editable parameters. Prefer a familiar, source-backed phrase and provide a same-material reference so composition quality does not obscure the instrument comparison. Label a generated score reference as such; it is not an original recording. Verify it, add its listening file to the package, and request its separate musical and ending verdict. Acceptance of the reconstruction alone does not prove useful transfer.
6. Record the reuse outcome below, link the executable example and limitations from the owning card, and close the case only when the plan's completion contract is satisfied. Keep one [standing model-assistance decision](../research/audio-assessment.md#use-and-reassess-model-assistance) from case opening, reassess for a concrete useful question, relevant model/prompt/preprocessing change or explicit user request, and check it at closure. Do not repeat unchanged skip prose; retain task-specific controls, human musical acceptance and upload/spending authorization.

A “plain” transfer reference is not automatically a fixed cross-study baseline. Name its backend and disclose any envelope, gate/legato, tuning or timing differences from previously submitted references. A native-scheduler reference helps assess that case’s palette but cannot isolate instrument differences across different drivers. If a cross-study comparison is intended, reuse a fingerprinted common reference and declare the candidate’s articulation differences separately. See the [Ghostbusters listener observation and verified cause](../research/composition/instruments/ghostbusters-decoded-programs.md#familiar-material-transfer-and-listening-verdict).

For additional investigation, follow the [analysis stopping rule](../research/tools/sid-program-analysis.md#bound-the-investigation). Preserve deferred experiments without allowing them to expand the active case.

## Record reuse and effort

Keep one compact outcome record in the owning study or [instrument card](../research/composition/instrument-card-template.md#reuse-outcome), linking it elsewhere rather than copying it. Record the transfer phrase and its source, named components reused unchanged or adapted, new components required, listening-driven revision count and the final verdict. This shows whether the mechanism can serve new music and what still makes reuse difficult.

For the next authorized complete-song case, use the [prospective effort ledger](effort-ledger.md), covering source intake through accepted complete output and retention. For bounded transfers, measure effort prospectively from the start of the attempt to its accepted phrase. State the measurement basis: active work time excludes listener waiting; elapsed time includes it. Keep parallel-agent effort separate when available. If reliable timing or revision history is absent, write `not recorded`; do not invent historical estimates. Pending acceptance means the result is still pending, not a time-to-success measurement.

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

[prepare-cybernoid-title.py](../../scripts/studies/cybernoid/prepare-cybernoid-title.py) verifies the pinned decompressed evidence fingerprint, retains the first traversal and numeric programs/cold state, removes nested derivation annotations and declares the added ending. To create an editable copy, use `python3 scripts/studies/cybernoid/prepare-cybernoid-title.py --output build/cybernoid-prepared-new/title.json` with a fresh output path. Preparation and compilation require no original SID. `sourceEvidence` is nonexecuting provenance; changing it does not change synthesis. Original reference SIDs and WAVs remain under the [public repository boundary](publication-boundary.md).

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

### Rambo symbolic graph player

[compose-rambo.py](../../scripts/compose-rambo.py) consumes the editable `rambo-loader-composition-v1` [loader](../../songs/rambo-loader.json), [familiar transfer](../../songs/rambo-elise-transfer.json) or [plain reference](../../songs/rambo-elise-reference.json). The [owning study](../research/composition/rambo-preparation.md#independent-compiled-loader-and-musical-delivery) retains the complete source/CPU/VICE/audio evidence; the [instrument card](../research/composition/instruments/rambo-decoded-programs.md) owns the accepted reuse and articulation limits.

```sh
PYTHONPATH=.tools/test-deps python3 scripts/compose-rambo.py songs/rambo-loader.json --output build/rambo-compiled-new
python3 scripts/listening-package.py config/listening/rambo-loader-full.json --output build/rambo-independent-full
python3 scripts/listening-package.py config/listening/rambo-elise-transfer.json --output build/rambo-elise-transfer
```

The compiler emits our score/Morse and SOUND assembly, compact symbolic graph records, numeric banks, restored initial state and a PAL/6581 PSID with one update per 19,656 cycles. Runtime state includes three 49-byte data blocks, three 39-byte sound blocks, graph cursors, eight-slot call/loop stacks, transposes and the Morse dispatch phase. Node IDs become internal addresses; original source addresses remain nonexecuting annotations. Edits require neither the original SID nor recorded register events.

The default audit covers every declared `range.auditCalls` entry; `--calls` selects a CPU prefix but still validates numeric execution over the full declared range. Named-state checkpoints and every ordered SID write are compared independently. The binary preserves score returns and continuing sound lifetimes instead of adding a declared-range cutoff or automatic fade. Arbitrary edited graphs are guaranteed only within the verified range; a finite musical deliverable must reach its verified ending. Callable RAM bounds, supported numeric lookups, voice-specific grammar and directly decodable SID stores are checked before a successful build.

The opt-in `--stereo-bass` layout preserves the same score and patches while routing physical voice 2 to voice 2 of a second MOS6581 at `$D420`. Voices 1 and 3 stay at their original indices on `$D400`, preserving the loader's sync/ring relationship. One score/sound engine advances all three parts; the PSID v3 header declares both chips. This is three musical parts distributed across two chips, not a newly composed six-part arrangement. Both SID banks are initialized, and independent CPU comparison maps every source bass write to the second bank. The compiler rejects cross-chip oscillator dependencies, shared-filter changes and live global changes over the complete declared numeric range, including when `--calls` requests a shorter CPU diagnostic. The default mono binary remains unchanged. See the [stereo case and listening recipe](../../songs/studies/rambo-stereo/README.md) for rendering and musical status; physical hardware is unverified.

For an independently authored second group, use [compose-rambo-dual.py](../../scripts/compose-rambo-dual.py): `PYTHONPATH=.tools/test-deps python3 scripts/compose-rambo-dual.py PRIMARY.json SECONDARY.json --output build/new-rambo-dual`. Both descriptions retain the normal Rambo graph format and must share the PAL/6581 profile and audit range. The compiler assembles disjoint engines at `$D400/$D420`, with source-level register relocation and a wrapper that calls A then B under one PAL frame budget. Complete ordered writes and both mutable states are compared against independent numeric players; the primary engine's code bytes remain those of the same standalone description. Shared zero-page scratch is consumed within each complete call, not retained as cross-engine state. Prefix CPU checks do not shorten numeric validation of the declared range. Coupling is local to each chip; arbitrary source graphs still need their own full-form, budget, audio and ending checks.

The dual audit compares every ordered SID write over its declared execution range, with named mutable-state comparisons at selected checkpoints; it does not compare all internal state on every call. Source-level `sid_base` relocation supports only `$D400` and `$D420`, and cannot be combined with the earlier `--stereo-bass` routing mode. Independent engines retain the existing Rambo score grammar: separate initial master volumes do not establish support for new live filter or volume commands. The [dual compiler guards](../../tests/rambo_dual_compiler_test.py) cover isolation, initialization, primary-byte preservation and frame-budget rejection.

The [Rambo ensemble](../../songs/studies/rambo-ensemble/README.md) supplies three complementary support roles rather than duplicating the primary score. Its native export and centered listening presentation have separate contracts: both chip outputs exist in the PSID, while the [documented output matrix](../research/sid/dual-sid.md#plan-the-sound-hardware-and-the-mix-together) is applied by the reproducible audio workflow. Full CPU/VICE proof does not establish that the added roles improve the music.

### Ghouls variant graph player

[compose-ghouls.py](../../scripts/compose-ghouls.py) accepts `ghouls-composition-v1` descriptions: [the complete primary](../../songs/ghouls.json), [familiar transfer](../../songs/ghouls-elise-transfer.json) or [matched plain reference](../../songs/ghouls-elise-reference.json). [The study](../research/composition/ghouls-preparation.md#compiled-export-and-complete-listening-package) owns the complete execution/audio evidence; [the instrument card](../research/composition/instruments/ghouls-decoded-programs.md) owns reuse, articulation and listening limits.

```sh
PYTHONPATH=.tools/test-deps python3 scripts/compose-ghouls.py songs/ghouls.json --output build/ghouls-compiled-new
python3 scripts/listening-package.py config/listening/ghouls-full.json --output build/ghouls-independent-full
python3 scripts/listening-package.py config/listening/ghouls-elise-transfer.json --output build/ghouls-elise-transfer
```

The target is one PAL MOS6581 at `$D400`, updated every 19,656 cycles. The graph has symbolic node IDs and explicit `stream` and/or `override` variants. Live duration override chooses the variant: explicit stream durations occupy a field, while override notes use the current override value. Each enabled voice advances continuing sound before score consumption; shared filter processing follows all voices. Loops, calls, command setters, notes and rests execute from live state, without a per-call event schedule. `sourceEvidence` annotations do not affect synthesis.

Inputs retain three initial score voices, three named sound states, shared filter state, three filter restart phases, pulse fallback words and explicit numeric frequency lookup entries, including aliases. Missing initial score fields use the scheduler's dataclass defaults; the compiler lowers those normalized states. Missing accessed lookup entries, absent live grammar variants, nonterminating filter arithmetic or unsupported graph commands fail preflight. The [score module](../../scripts/ghouls_score.py) owns the supported command fields. Compiler bounds are eight saved return nodes per voice, 256 graph operations per call and at most 255 writes per SID-store-list command.

Every build numerically checks the complete declared `range.auditCalls` in 1–65,535. By default the compiled CPU proof covers every call and all named-state boundaries; optional `--calls` selects only a CPU diagnostic prefix while retaining the full numeric preflight. The payload must fit below `$A000`. Exported SID writes use directly decodable absolute/indexed stores. Init restores the complete mutable image, then performs the descending original 58-store SID reset. Explicit score disable stops that voice's effects; shared filter calls continue. No automatic musical ending or fade is inferred from the declared audit range.

Outputs are `reconstructed.sid`, standalone `reconstructed.prg`, generated assembly/listing, `verification.json`, `audit.json`, ordered `writes.json` and named checkpoints. The PRG uses BASIC `SYS 2061` and the shared fixed-PAL harness, then idles after its declared call count. A poisoned-state bootstrap check executes that actual image's init and first two calls with modeled VIC/CIA reads. The full recipe separately verifies callable SID execution in headless VICE. Neither check claims original-game timing, bus-cycle identity, real VICE autostart of the PRG, audio identity or musical acceptance.

### Deflektor packed-score player

[compose-deflektor.py](../../scripts/compose-deflektor.py) accepts the `sid-deflektor-player-v1` schema in the [editable title](../../songs/studies/deflektor-reconstruction/title.json). The [owning study](../research/composition/deflektor-preparation.md#compiled-export-and-listening-package) retains execution and listening evidence; the [source README](../../songs/studies/deflektor-reconstruction/README.md) describes reproduction and its boundary.

```sh
PYTHONPATH=.tools/test-deps python3 scripts/compose-deflektor.py songs/studies/deflektor-reconstruction/title.json --output build/deflektor-compiled-new
python3 scripts/listening-package.py config/listening/deflektor-full.json --output build/deflektor-independent-full
```

The target is one PAL MOS6581 at `$D400`, updated once per 19,656-cycle frame. Order/pattern bytes, instrument-slot mappings and numeric sound tables remain runtime data in newly authored 6502 code. No captured event schedule or original driver instructions are embedded. Numeric source pointer annotations do not become executable addresses. Keep source-specific synthesis constraints explicit: low-byte-only PWM carry behavior, shared table aliases, ordered resonance updates and whole-call body suppression at row boundaries are part of this backend's sound.

Optional `title` and `author` fields supply Latin-1 PSID metadata, truncated to 31 bytes with a terminating NUL; absent fields retain the original export bytes. Nontext, embedded NUL and non-Latin-1 input reject explicitly.

The compiler preflights the complete declared `play_calls` in 1–65,535; `--calls` narrows only the compiled CPU diagnostic prefix. The payload must fit below `$A000`. Cold initialization restores mutable state without SID writes. A terminal order marker clears all three controls and stops future stores; a call-count cap does not itself compose an ending. The verified title stops at call 8,480 without an added fade. Source-specific PAL tuning/cadence is retained; native regional export support does not automatically retune this backend.

Outputs include PSID, standalone PRG, generated assembly/listing, CPU audit, ordered writes, named checkpoints and a verification receipt. Verification checks complete callable boundaries, independently computed ordered stores, executed SID writer sites, cycle budget and poisoned-state reinitialization. The PRG's actual SYS 2061 bootstrap is separately checked with modeled raster/CIA reads. Full headless VICE execution in the recipe checks callable playback, not real-machine PRG autostart. Audio checks and human listening remain separate.

### Take On Me runtime score and sound programs

The study-specific [compiler](../../scripts/studies/take-on-me/compose.py) consumes `take-on-me-composition-v1` descriptions, including the [editable title](../../songs/studies/take-on-me-reconstruction/README.md). Its [owning study](../research/composition/take-on-me-preparation.md) separates source provenance, numeric verification and listening status. The working target is one PAL MOS8580 at `$D400`, updated every 19,656 cycles; the original archive's unspecified chip model remains unchanged.

```sh
python3 scripts/studies/take-on-me/prepare-title.py --check
PYTHONPATH=.tools/test-deps python3 scripts/studies/take-on-me/compose.py songs/studies/take-on-me-reconstruction/composition.json --output build/take-on-me-compiled-new
python3 scripts/listening-package.py config/listening/take-on-me-full.json --output build/take-on-me-full-work
```

The compiler lowers editable order/pattern rows, instrument records, frequency and modulation tables, and named initial state into our [scheduler](../../songs/players/take-on-me.asm) and [sound routines](../../songs/players/take-on-me-effects.asm). These execute score and modulation at runtime, without original driver instructions or captured-write replay. Score-owned countdown, note, glide and arpeggio fields share one physical state store with the sound routines. Source annotations do not control synthesis. Preserve the native pitch table for reconstruction; retuning for different material is an explicit adaptation, not an implied regional conversion.

Every build numerically executes the complete declared `range.auditCalls` in 1–65,535. The default compiled CPU comparison covers that whole range; `--calls` selects a diagnostic CPU prefix without shortening numeric admission or exported playback. Verification compares ordered stores and named state, checks writer sites and the PAL cycle budget, and poisons mutable state before testing reset. Outputs include SID, standalone PRG, assembly/listing, build metadata, audit, ordered writes, state checkpoints and a verification receipt. The actual PRG bootstrap has a separate modeled raster/CIA check; the recipe's headless VICE check covers callable playback, not real-machine PRG autostart.

Optional `ending` declares positive integer `startCall` and `releaseCalls`; the declared range must include the stop call and at least 64 subsequent confirmation calls. At the start, close the held gates and freeze score and modulation. Leave the held release untouched until the stop call, then clear controls and master volume while retaining filter-mode bits. Subsequent calls leave named state unchanged and emit no stores. This is a deliberate arrangement ending; the source loops. The full recipe compares only the preserved musical prefix against the original, verifies the entire candidate including its ending in CPU/VICE, and applies settled-tail audio checks to the candidate alone. Source-prefix equality does not prove the authored tail; signal health does not establish musical acceptance.

### Billie Jean runtime score and sound programs

The study-specific [compiler](../../scripts/studies/billie-jean/compose.py) accepts `billie-jean-composition-v1`, including the [editable reconstruction](../../songs/studies/billie-jean-reconstruction/README.md) and [matched familiar transfer](../../songs/studies/billie-jean-elise/README.md). The [owning study](../research/composition/billie-jean-preparation.md#compiled-export-and-listening-package) separates source-prefix identity, authored ending, complete compiled execution and accepted human judgments; the [palette card](../research/composition/instruments/billie-jean-decoded-programs.md) owns reuse and adaptation limits. The admitted target is one PAL MOS6581 at `$D400`, updated every 19,656 cycles.

```sh
python3 scripts/studies/billie-jean/prepare-title.py --check
PYTHONPATH=.tools/test-deps python3 scripts/studies/billie-jean/compose.py songs/studies/billie-jean-reconstruction/composition.json --output build/billie-jean-compiled-new
python3 scripts/listening-package.py config/listening/billie-jean-full.json --output build/billie-jean-full-work
python3 scripts/listening-package.py config/listening/billie-jean-elise-transfer.json --output build/billie-jean-elise-work
```

Editable order/pattern bytes, instrument parameters, paired 256-byte pitch/waveform banks and explicit frequency words remain runtime data in our [scheduler](../../songs/players/billie-jean.asm) and [generated sound routines](../../scripts/studies/billie-jean/billie_jean_effects_asm.py). The header alone owns row duration and flags; at reload 2, duration *d* spans three times *d+1* calls. Orders and encoded patterns including terminators each fit a 256-byte cursor; pattern IDs are 0–127. Shared score inputs have one owner: base note, remaining duration, hold and instrument offset. Sound-owned gate/glide state persists between row setters. Complete named sound/filter cold state is required; duplicate score fields reject. Source addresses and provenance annotations do not influence synthesis, and no original driver code or captured-write replay is embedded.

Each build numerically checks the complete declared `range.auditCalls` in **1–40,000**; default compiled CPU verification checks that whole range. Optional `--calls` narrows only the CPU diagnostic prefix, preserving full numeric admission and the exported host's declared call count. Accessed frequency holes and nonterminating pitch-table jumps fail admission. The payload must end at or below `$A000`. Optional Latin-1 `title`, `author` and `released` supply PSID metadata, truncated to 31 bytes plus NUL; embedded NUL, nontext and non-Latin-1 input reject.

Outputs include PAL/MOS6581 PSID2, standalone PRG, generated assembly/listing, build metadata, audit, ordered writes, named checkpoints and a verification receipt. Verification compares every ordered store and named init/play state, checks writer sites and the PAL budget, and tests poisoned mutable-image/workspace restoration. Init emits three control-zero stores; voices run in physical order 3, 2, 1 with age after each setup/body and global mode/volume last. The actual PRG `SYS 2061` check covers init and two calls with modeled raster/CIA reads. Full headless VICE in the recipe separately checks callable SID playback; it does not establish real-machine PRG autostart, original-host timing, bus-cycle identity or musical acceptance.

Optional `ending` contains positive integer `startCall` and `releaseCalls`, and the declared range must include the stop call plus at least 64 subsequent calls. Before the start call's score step, close GATE on the last actually emitted controls and freeze score/modulation. After the held release, zero controls/master volume while retaining filter-mode bits; later calls retain named state and emit no stores. Tracking actual controls matters because hard restart writes `$09` while cached waveform state is retained. The title preserves music calls 0–7105, releases at 7106 and stops at 7138 without a fade. The audit range itself does not compose an ending or promise indefinite edited playback. The recipe compares only the preserved source prefix, verifies the complete candidate in CPU/VICE and measures its rendered tail separately from human acceptance.

### Airwolf runtime rows and static patches

The study-specific [compiler](../../scripts/studies/airwolf/compose.py) accepts `airwolf-composition-v1`, including the [editable reconstruction](../../songs/studies/airwolf-reconstruction/README.md) and [matched familiar transfer](../../songs/studies/airwolf-elise/README.md). The [owning study](../research/composition/airwolf-preparation.md#compiled-export-and-listening-package) separates original-source preservation, authored ending, complete CPU/VICE checks and pending listening judgments. The [static palette card](../research/composition/instruments/airwolf-static-tones.md) owns reuse and inherited-state constraints. The admitted target is one PAL MOS6581 at `$D400`, updated every 19,656 cycles.

```sh
python3 scripts/studies/airwolf/prepare-title.py --check
PYTHONPATH=.tools/test-deps python3 scripts/studies/airwolf/compose.py songs/studies/airwolf-reconstruction/composition.json --output build/airwolf-compiled-new
python3 scripts/listening-package.py config/listening/airwolf-full.json --output build/airwolf-full-work
python3 scripts/listening-package.py config/listening/airwolf-elise-transfer.json --output build/airwolf-elise-work
```

Inputs contain **1–255 rows**, each with duration **1–255** and three `notes` entries: a direct frequency word **256–65,535**, `null` for hold, or authored `"off"` for GATE close. Duration `N` spans `N+1` updates; init consumes row zero, so its next row begins at play call `N`. Frequency-high zero remains a source hold sentinel; zero duration is the source restart marker, not an admitted musical row. The [runtime scheduler](../../songs/players/airwolf.asm) consumes lowered row records and patch data rather than original instructions or per-call store schedules. Source addresses and metadata do not affect synthesis.

`sound.voices` supplies three static AD/SR/control patches. Controls allow one waveform plus GATE (`$11`, `$21`, `$41` or `$81`); TEST, sync, ring and combined waveforms reject. Shared volume is 0–15, and `sound.pulseHigh` preserves two raw bytes for voices 1/2. Each native update writes volume, first pulse high and second pulse high before countdown processing. Pitched entries run in physical order 1, 2, 3 and emit AD, SR, control zero, selected control, frequency high, then low. Hold performs no row-level voice writes; off clears the last emitted GATE while preserving release waveform. A terminal rewind repeats the fixed writes within the same host call. There is no modulation engine, dynamic patch selection or shared-filter program.

Complete named software state derives from the same input; a duplicate editable initial image is unsupported. Cold reset restores software caches/workspace, then performs native fixed stores and consumes row zero. Pulse lows, voice 3 pulse width and filter cutoff/routing remain unwritten, so prior hardware state or renderer reset still matters. Software restoration does not claim a physical SID reset. The title retains native frequency words; familiar A440 retuning is an explicit adaptation, not NTSC export support.

Each build numerically executes the complete declared `range.auditCalls` in **1–65,535** and, by default, compares every compiled call and named init/play state. Optional `--calls` narrows only the CPU diagnostic prefix. Verification checks ordered stores, writer sites, PAL budget, poisoned restoration and decimal-mode entry. Payloads fit callable RAM below `$A000`. Optional Latin-1 `title`, `author` and `released` are truncated to 31 bytes plus NUL; unsupported metadata rejects. Outputs are SID, standalone PRG, assembly/listing, build metadata, audit, ordered writes, checkpoints and verification receipt. The actual PRG `SYS 2061` bootstrap check covers init and two calls with modeled raster/CIA reads. The recipe separately checks complete callable SID playback in headless VICE; neither claims original-host timing, real-machine PRG autostart, physical SID-state identity or indefinite edited playback.

Optional positive `ending.startCall`/`releaseCalls` intercept the start before fixed writes and score advancement, close held gates, suspend row processing and recurring fixed writes, then zero controls/master volume after the release. Subsequent calls retain musical state and emit no stores; the declared range must include the stop call and at least 64 later confirmation calls. The optional finite title preserves init and calls 0–1240, releases at 1241 and stops at 1273 without a fade; its premature cutoff was not accepted. The [source-continuation correction](../research/composition/airwolf-preparation.md#reference-continuation-correction) instead uses the existing composition without `ending`, preserving the restart and verifying all 2,500 calls. The audit range alone does not compose an ending, and a render capture boundary is not a musical stop. Original-prefix comparison, complete candidate CPU/VICE verification, pre-mute decay measurements and human acceptance remain separate checks.

### Other drivers

[describe-drax-score.py](../../scripts/studies/drax/describe-drax-score.py) is a pinned, driver-specific transcriber, not a universal SID importer. It observes executed note consumption, instrument initialization and score gate-off, then verifies preparation and repeat behavior. Use `--check` to compare its output with the retained fixture. For another player, recover its corresponding readers and state transitions before adapting the decoder. [The Flashdance study](../research/composition/flashdance-preparation.md) demonstrates its own decoded mechanisms and independently authored dual-SID arrangement.

The [Shades study](../research/composition/shades-preparation.md#reconstruction-boundary) distinguishes source comparison, compiled execution, CIA cadence, rendered audio and listening. A computed store ledger alone remains diagnostic output; the compiled backend above supplies separate CPU and VICE evidence.

For an accepted transfer of the Shades instruments to familiar musical material, use the [Für Elise comparison](../research/composition/instruments/shades-decoded-programs.md#familiar-transfer-accepted) and its [exact recipe](../research/composition/shades-elise-audio.json). `python3 scripts/studies/shades/prepare-shades-elise.py --check` verifies the retained score and plain reference bank. The same 53 source events feed both renderings; this demonstrates reusable sound programs without requiring the listener to judge an invented composition. The older eight-bar invented transfer above remains historical evidence with an unaccepted ending.
