# Deflektor preparation

This pins Ben Daglish's *Deflektor* for the [study plan](../study-plan.md). Shades remains the active reconstruction. The [composer account](../composers/follin-daglish.md#ben-daglish-a-memorable-instrument-can-organise-a-whole-piece) connects the piece's composition to a satisfying cowbell sound; the binary's precise cowbell mechanism remains unestablished. Apparent realism alone does not identify samples, ring modulation or oscillator allocation.

## Reference and execution boundary

The [source and admission receipt](../../../evidence/deflektor-intake/provenance.json) pins the [HVSC file](https://www.hvsc.de/download/C64Music/MUSICIANS/D/Daglish_Ben/Deflektor.sid), 4,081 bytes, SHA-256 `606ad4cb19e29c060bb77a9b44253dee62d3d972724acb6cddf625fc2466d44d`. The [header report](../../../evidence/deflektor-intake/header.json) records the declarations without exporting original payload bytes.

| Field | Pinned value |
| --- | --- |
| Title / author / release | Deflektor / Ben Daglish / 1987 Gremlin Graphics |
| Format and selection | PSID v2, one subtune, default and selected #1 |
| Declared target | PAL, MOS6581, flags `$0014`, VBI speed word zero |
| Payload | Embedded load `$C000`, 3,955 bytes, end `$CF73` exclusive |
| Entry points | Init `$C810`, play `$C106` |
| Cached STIL v85 | No entry for this exact Daglish path; the similarly named Harlequin file is a different reference |

The initial intake rejected this file **before executing the driver**: the earlier `pal-banked` payload ceiling was `$BFFF`, and its host occupied `$C000–$C1FF`. Deflektor overlaps that workspace. The retained intake receipt describes that historical tool boundary, not an invalid tune or a demonstrated CIA/IRQ dependency.

The [explicit host-placement contract](../../validation/psid-audit.md#place-the-host-around-a-high-ram-reference) now permits this unchanged source with `--host-base 0x0400`. Our code and scratch occupy `$0400–$05FF`; the source remains at `$C000–$CF72`, init `$C810`, play `$C106`. Default placement still rejects the overlap. The parser checks complete extents, and execution rejects accesses to the selected host workspace or protected interrupt vectors. CPU and VICE share generated JSR return sites, including their stack words, rather than assuming a synthetic caller address.

## Bounded CPU and VICE verification

On 2026-10-13 the [selected-host header report](../../../evidence/deflektor-host/header.json), [CPU audit](../../../evidence/deflektor-host/audit64.json), [complete ordered ledger](../../../evidence/deflektor-host/audit64.writes.json.gz), [parsed VICE trace](../../../evidence/deflektor-host/vice64/trace.json.gz) and [VICE result](../../../evidence/deflektor-host/vice64/study.json) establish:

| Scope | Observed result |
| --- | --- |
| Initialization | 1,407 CPU cycles; zero SID stores. VICE observes init entry and return separately. |
| Play calls 0–63 | 502 SID stores; maximum 1,878 and mean 605.953125 CPU cycles per call, within the 19,656-cycle budget. |
| Independent VICE comparison | All 502 stores match in phase, call, address, value and order; maximum call-cadence error is seven cycles against the nine-cycle polling tolerance. |
| Source preservation | Original SHA-256 still matches the pre-execution intake and both execution receipts; the private VICE payload equals the original embedded load word plus all 3,955 payload bytes. |
| Caller boundary | Host returns at `$043A` after init and `$044D` after play; the corresponding JSR stack words are `$0439/$044C` in both CPU and VICE. |

The [verification receipt](../../../evidence/deflektor-host/verification.json) pins source/header/payload hashes, tool revisions and retained records without exporting executable source bytes. Executed synthetic fixtures additionally check stack-return reads at hosts `$0400/$9E00`, zero RAM beneath KERNAL, workspace bounds and unchanged strict defaults. The [bounded regression receipt](../../../evidence/deflektor-host/regressions.json) preserves exact equality with the earlier Ghouls, Monty and Rambo 64-call ledgers after the common banked return-site correction.

This is a controlled raster-host comparison, not original-game execution or a complete song. CPU costs and monitor timestamps do not establish exact SID bus-write timing. No cowbell mechanism, arrangement form, audio or listening verdict follows from these checks. Raw monitor/process logs and source/host executable files remain in ignored local storage.

## Executed finite score form

The [source-pinned form observer](../../../evidence/deflektor-form/probe.py), [execution receipt](../../../evidence/deflektor-form/full40000/receipt.json), [CPU report](../../../evidence/deflektor-form/full40000/audit.json) and [form summary](../../../evidence/deflektor-form/full40000/summary.json) retain 40,000 initialized calls under `pal-banked`, subtune #1, host `$0400`. Calls **0–8,480 inclusive** cover the selected driver's score through its first global transport stop. The following 31,519 calls remain stopped; they extend the observation window rather than the arrangement. There are 166,845 ordered play stores, zero init stores and a maximum cost of 2,564 cycles per call. This is a finite selected-source boundary, not a song-loop inference.

| Navigation | Executed source basis |
| --- | --- |
| Three order streams | `$CA21–$CA26` selects `$CA27`, `$CA5B`, `$CA9B`; `$C2D6` consumes order bytes using per-voice cursors `$C08B–$C08D`. |
| Pattern selection | Split pointer tables at `$CAD1/$CAF5` contain 36 entries; `$C335` installs the selected per-voice pointer. All 36 pattern IDs are selected during the retained form. |
| Pattern consumption | `$C2B0/$C2B9/$C2BE` read tokens; `$C477/$C480/$C485` read note durations; `$C8BC/$C8C3/$C8C6` read contextual helper operands. Exact addresses, bytes, voice, cursor and incoming state remain in the [event ledger](../../../evidence/deflektor-form/full40000/events.json.gz). |
| Timed rows | `$C354` reloads a rest and `$C525` reloads a note. Encountered duration bytes range from 5 to 130 calls. The next row starts after that many play calls; source prefixes consume bytes within the same row boundary. |
| Pattern repeats | Pattern `$FF` at `$C2C4` either decrements a nonzero repeat counter at `$C2C9` and restarts the same pattern, or advances the order. There are 102 executed same-pattern restarts, distinct from the 87 order-selected pattern entries. |
| Instrument selection | `$C3DF` reads a mutable slot mapping at `$C058`; `$C3E3` selects a nine-byte record from `$C007`. The [retained tables](../../../evidence/deflektor-form/full40000/tables.json) and event ledger preserve actual slot/record bytes; they do not identify the cowbell or name the complete synthesis mechanism. |

| Voice / zero-based index | Order-selected patterns | Timed rows | Notes / rests | Selected record indices |
| --- | --- | --- | --- | --- |
| Voice 1 / 0 | 36 | 493 | 475 / 18 | 0, 1, 2, 6 |
| Voice 2 / 1 | 28 | 722 | 679 / 43 | 0, 1, 2, 3, 7 |
| Voice 3 / 2 | 23 | 690 | 666 / 24 | 0, 4, 5 |

On call **8,480**, voice 1 consumes the terminal order `$FF` at **`$CA5A`**, then executes **`$C2E0`** with the playing flag still `$0F`. The path clears `$C006`, writes `$00` to `$D404/$D40B/$D412` in that order, unwinds the channel call and reaches the outer return at `$C2F2`. Later calls return at `$C10B`, without score consumption or SID stores. Voice 1's final four rest rows start at 8,160, 8,240, 8,320 and 8,400 with duration 80. The other voices' last notes start at 8,460 with duration 20; voice 1's global stop prevents their pending pattern/order end markers from being consumed on 8,480. No master-volume fade is inferred: the retained mode/volume shadow remains `$0F`.

The [independent score expander](../../../evidence/deflektor-form/check-score.py) reads the exact retained numeric order/pattern/mapping tables, not captured events or SID stores as playback input. Its [comparison receipt](../../../evidence/deflektor-form/score-verification.json) matches all **5,100 source reads, 87 pattern selections, 1,905 row starts/durations, 1,820 note lookup indices and 663 mapped instrument selections**. Editing a consumed duration breaks equality. Transpose/repeat order commands are executed; pattern effect tokens `$90–$95` retain their observed consumption; their synthesis meaning is supplied by the [composed player](#compose-the-complete-finite-score-from-editable-data). Other statically mapped command branches and zero-duration scheduling lack separate executed validation. This is a pinned title grammar, not a general Daglish format specification.

The [opening observer check](../../../evidence/deflektor-form/opening-verification.json) matches all 10,284 instructions/register checkpoints, 502 stores and 30 score reads against the [separately retained instruction trace](../../../evidence/deflektor-form/opening-trace.json.gz). Both observers share the CPU implementation. Independently, the [VICE ending-window result](../../../evidence/deflektor-form/vice-stop/trace/study.json), [parsed trace](../../../evidence/deflektor-form/vice-stop/trace/trace.json.gz) and [provenance](../../../evidence/deflektor-form/vice-stop/provenance.json) match all 75 play stores in calls **8,476–8,488**, including the stop stores and subsequent absence of writes; init produces no stores. VICE executes from initialization through 8,489 play entries, with maximum cadence error seven cycles against the nine-cycle polling tolerance. This independently checks the ending window, not all 166,845 stores.

The [state ledger](../../../evidence/deflektor-form/full40000/states.json.gz) preserves named score/effect state plus SHA-256 fingerprints of all 65,536 backing-memory bytes and raw CPU registers immediately before each validated final callable RTS. The normal auditor then completes the return and checks its stack. No exact whole-memory/register checkpoint repeats before the stop; consecutive stopped checkpoints become identical starting at call 8,481. These hashes include stack and SID write shadows but omit physical oscillator, envelope, filter, CIA and VIC state. They neither establish a musical recurrence nor prove audible silence or the length of an acoustic release. The [bounded instruction record](../../../evidence/deflektor-form/full40000/instructions.json.gz) retains initialization, calls 0–63 and the stop call plus its next 64 calls; every other call still retains score events, state/hashes and stores in the [ordered ledger](../../../evidence/deflektor-form/full40000/writes.json.gz). No original SID, full payload or full RAM image is exported.

Reproduce with the pinned dependencies recorded in the receipt and a fresh output directory:

```sh
PYTHONPATH=.tools/test-deps python3 evidence/deflektor-form/probe.py .local/research/deflektor/Deflektor.sid --calls 40000 --output build/deflektor-form-new
python3 evidence/deflektor-form/check-score.py build/deflektor-form-new --output build/deflektor-form-new/score-verification.json
python3 evidence/deflektor-form/verify-opening.py evidence/deflektor-form/opening-trace.json.gz build/deflektor-form-new --output build/deflektor-form-new/opening-verification.json
python3 scripts/trace-sid-vice.py .local/research/deflektor/Deflektor.sid --profile pal-banked --subtune 1 --host-base 0x0400 --oracle evidence/deflektor-form/vice-stop/oracle.json --first-call 8476 --last-call 8488 --output build/deflektor-ending-new
```

After fetching the evidence's Git LFS objects, check the canonical score proof directly with `python3 evidence/deflektor-form/check-score.py evidence/deflektor-form/full40000 --output build/deflektor-score-check.json`. This checker consumes `.json.gz` and verifies the retained compressed-file hashes; restoring decompressed historical paths with the evidence helper does not provide those archive inputs.

Dependency mismatches fail explicitly rather than silently substituting a different observer environment. The form and ending proofs cover the selected driver under this controlled host; original-game execution, compiled synthesis, audio and listening remain separate work; the [numeric player](#compose-the-complete-finite-score-from-editable-data) separately verifies complete computed register output.

## Reusable score expansion

The supported [score module](../../../scripts/deflektor_score.py) exposes `expand_score(tables, *, calls)` using the numeric schema in the [retained tables](../../../evidence/deflektor-form/full40000/tables.json). It reads no files, original SID, CPU or observed-event ledger at runtime; input tables remain unchanged and returned instrument fields are copied. The exclusive call cap is separate from `firstStopCall`: 8,480 calls exclude the stop, while 8,481 include the stop at index 8,480. Editable notes, transposes, durations and pattern/order data drive expansion; opaque effects remain numeric commands. Zero durations reject explicitly because that edge lacks source verification.

Use its `operations` array when composing sound behavior: entries carry an `operation` tag (`command`, `instrument`, `note`, `row` or `stop`) and preserve cross-category consumption order within each call and voice. Existing category arrays remain available, with detached nested values. At call 1,280, voice index 2 consumes effect `$95`, then selects record 36, then starts its note; concatenating separate effect/instrument/note lists would lose this ordering. The terminal `stop` operation prevents later voices from processing that call. Pattern selections remain navigation metadata rather than synthesis operations.

```python
import json
from pathlib import Path
import sys
sys.path.insert(0, "scripts")
from deflektor_score import expand_score

tables = json.loads(Path("evidence/deflektor-form/full40000/tables.json").read_text())
expanded = expand_score(tables, calls=8481)
assert expanded["firstStopCall"] == 8480
```

The [executable guards](../../../tests/deflektor_score_test.py) compare complete consumption with the retained CPU ledger and check note edits, input preservation, cap/stop distinction, invalid data and unsupported zero durations. After fetching the required evidence's Git LFS objects, run `python3 -m unittest discover -s tests -p 'deflektor_score_test.py' -v`. This module expands the score; it does not implement the sound-record programs or acoustic release.

## Sound-record fields and staged waveform candidate

The [field/program lookup](../../../evidence/deflektor-programs/verified-final/lookup.json) maps every record to its actual reader and named parameter. Instrument mappings advance by **nine bytes**, but setup also reads a **tenth contextual byte** at $C010+recordOffset: it selects the shared resonance program and aliases the next record's first byte, or the following mapping byte after record 8. A nine-byte record alone therefore omits a synthesis input. Eight records are selected in the finite score; record 8 remains a static data entry without observed title selection.

| Offset | Executed setup meaning |
| --- | --- |
| 0 | Packed PWM: low nibble is the update interval; the **unshifted** high nibble is the table-base offset. Setup resets the interval counter to interval minus one and pulse position to zero. |
| 1 | Initial pulse high-byte shadow; the low byte is retained. |
| 2 | Initial control shadow; note setup sets GATE, and an enabled waveform program can replace the waveform. |
| 3 / 4 | Attack/decay and sustain/release shadows. |
| 5 | Incoming row-countdown value at which the body clears GATE. |
| 6 | Pulse low-byte step. Between table targets, addition/subtraction affects only that byte, without propagating carry/borrow to pulse high. |
| 7 | Delayed signed frequency-step program offset; zero disables this path. |
| 8 | Timed waveform/control program offset; zero disables this path. |
| 9, contextual lookahead | Timed shared $D417 resonance-high-nibble program offset, retaining routing low bits. |

On the encountered title paths, the body processes gate release → PWM → delayed pitch → waveform → score-selected pitch → shared resonance. Its [retained-context checks](../../../evidence/deflektor-programs/path-verification.json.gz) reenact 37 PWM and 16 delayed-pitch contexts with isolated original segments and compare the next named states to the complete form ledger. Record 3 uses interval 12, base 0 and low-byte step $15; its first body produces pulse shadow $0115. Record 6 uses interval 4, base $20 and step $3F: the PWM reads at $C9AD/$C9AE alias bytes also used by its pitch program, so a separately truncated PWM table would lose required data. Its delayed pitch starts with wait 30 eligible body invocations, then uses frequency-word steps +100,+100,+100,-100,-100,-100,0; the phase's high bit reverses the direction on the following pass. These are source-context checks, not independent PWM/pitch implementations or semitone-domain modulation.

**Record 0 is a recurring staged percussion candidate**, with 109 note onsets across the three voices. Its waveform program has header $04, packed stages $27,$10,$13,$17, and control progression **noise → triangle → triangle with SYNC and RING → noise**. AD/SR are $06/$0A, giving zero sustain; its own PWM and delayed-pitch offsets are disabled. The [offline context census](../../../evidence/deflektor-programs/context.json) retains all onsets and 109 coupled-triangle control stores. This identifies a candidate for listening, not Daglish's cowbell. The [SID coupling contract](../sid/hardware.md#sound-architecture) requires the preceding oscillator: voice 1 receives voice 3, voice 2 receives voice 1, and voice 3 receives voice 2. At the first coupled stage, call 644, this source has never written voice 3's frequency bytes; its nonzero loaded RAM shadow cannot establish on-chip frequency. The census preserves that value as unknown rather than assuming a reset or copying the software shadow.

The editable [waveform model](../../../evidence/deflektor-programs/model.py) uses named Stage, WaveProgram and WaveState values with initialize_wave, advance_wave and an ordered seven-register writer. It reads no files, original driver or captured events at runtime. Initialization forces GATE, selects stage zero, starts position one and adds one to the first duration. Body output is stage control bits OR incoming GATE; all retained stage controls have their GATE bit clear, so they preserve the caller's gate state. Body reloads use the duration without the initializer's extra call. A finite program holds its last control after position $FF; its byte countdown still decrements and wraps without restarting the lookup. Initializing another program replaces its previous position. Globally suppressed body calls do not advance the program.

The [verification](../../../evidence/deflektor-programs/verified-final/verification.json) and [receipt](../../../evidence/deflektor-programs/verified-final/receipt.json) preserve **624 isolated source cases**, **4,368 matching ordered writer stores**, and a new initialized 672-call ledger matching all **5,704 canonical stores**. The [real waveform boundaries](../../../evidence/deflektor-programs/verified-final/observed-wave.json.gz) match all 30 initializer/body invocations in calls 640–671 and all 28 voice-1 control stores. Note setup on 640 updates shadows while the global row-boundary path suppresses output: noise $81 reaches the SID on 641–642, triangle $11 on 643, coupled triangle $17 on 644, then noise again on 645. The next note repeats the coupled stage on 664. Removing SYNC/RING from that editable stage predicts and confirms $17→$11 at both 644 and 664. Gate-clear noise $80 is observed on 659. Four [model guards](../../../evidence/deflektor-programs/model_test.py) cover initialization replacement, finite hold/counter wrap, loop timing and disabled-state retention. The [complete narrow instruction record](../../../evidence/deflektor-programs/verified-final/instructions640-671.json.gz), [ordered initialized ledger](../../../evidence/deflektor-programs/verified-final/writes672.json.gz) and [isolated state/store records](../../../evidence/deflektor-programs/verified-final/isolated-cases.json.gz) retain the underlying evidence.

The census separates source writes from loaded shadows: written cutoff bytes are $00/$0A, $D417 takes $00/$30/$60/$80 with routing low bits always zero, and $D418 remains $0F with filter modes clear. Shared resonance macros update one shadow in voice-processing order; a future player must preserve that ordering. No moving-filter contribution, original-game boot state, oscillator-phase equivalence, acoustic similarity or cowbell identification follows from the numeric checks. Waveform advancement and the seven-register writer are independently modeled; the [caller](#body-admission-and-score-selected-pitch-components) and [motion](#pulse-delayed-pitch-and-shared-resonance-components) components below provide further numeric primitives. The [complete numeric composition](#compose-the-complete-finite-score-from-editable-data) separately verifies their integration.

Reproduce into fresh outputs with the pinned dependencies and fetched form evidence:

```sh
python3 evidence/deflektor-programs/model_test.py
PYTHONPATH=.tools/test-deps python3 evidence/deflektor-programs/check.py .local/research/deflektor/Deflektor.sid --output build/deflektor-programs-new
python3 evidence/deflektor-programs/context.py --output build/deflektor-context-new.json
PYTHONPATH=.tools/test-deps python3 evidence/deflektor-programs/paths.py .local/research/deflektor/Deflektor.sid --output build/deflektor-paths-new.json
```

The [checker](../../../evidence/deflektor-programs/check.py) and [path probe](../../../evidence/deflektor-programs/paths.py) execute bounded original segments privately; the [context census](../../../evidence/deflektor-programs/context.py) reads retained evidence without CPU execution. None exports an original SID, full payload or full RAM image. Rendering and listening attribution remain open; the [complete numeric player](#compose-the-complete-finite-score-from-editable-data) verifies integration separately.

## Body admission and score-selected pitch components

The independent [caller primitives](../../../evidence/deflektor-caller/model.py) compute named state without source files, CPU execution or event replay. They supply the body-entry decisions and late score-selected pitch operation needed to compose the waveform and motion components; they are not a complete scheduler or player.

| Component / native locus | Numeric contract |
| --- | --- |
| `advance_prelude`, `$C529–$C59A` | Check gate release against the incoming row countdown first. Decrement the row and any rest countdown; a rest returns before motion. Otherwise a global row-boundary flag suppresses all subsequent programs. Return the updated `BodyState` and whether later programs must run. |
| Three-byte score glide within the prelude | Decrement its wait before considering the active length. A nonzero length applies one 16-bit add/subtract step; length `$FF` persists, other lengths decrement. The direction comes from flag `$20`. This is separate from the instrument's delayed pitch program. |
| `initialize_score_pitch`, `$C503–$C51C` | Reset enabled score-pitch position to one and load the decoded initial delay. Disabled programs retain their state. |
| `advance_score_pitch`, `$C726–$C7C3` | Decrement its byte countdown, then apply the selected table-index offset to the base pitch index modulo 256. Add the unsigned detune byte to the caller-supplied frequency word modulo 65,536. Loop position zero supplies a base-pitch stage with its distinct restart delay. |
| Finite score-pitch completion | On the first expired `$FF` position, restore base pitch plus detune and change position to `$FE`. Later calls keep decrementing/wrapping the countdown without further lookups. |

The caller must perform the earlier global preparation: any row countdown equal to one is reset to zero, its rest flag is cleared, and that call suppresses continuing programs/output globally. It must then select row versus body processing. The prelude deliberately requires a nonzero incoming countdown and does not implement that earlier preparation itself. Release can still change a shadow during a suppressed body; a shadow change does not imply a SID store that call.

All five selected score-pitch programs, offsets **8, 16, 24, 32 and 40**, decode to initial wait **2**, restart wait **1**, a loop flag and one or two editable offset/duration stages. The model retains raw frequency words rather than inventing chromatic pitches for adjacent source data. A zero restart-delay header follows a different native special case and is explicitly unsupported by this component. Three-byte glide remains synthetic source coverage: the retained title contexts never enable its length field.

The [verification receipt](../../../evidence/deflektor-caller/verification.json) records **2,646 isolated original-block comparisons**: 576 preludes, 2,016 score-pitch bodies and 54 initializers. All match named output state with no unexpected SID stores or stack changes. The [complete isolated cases](../../../evidence/deflektor-caller/isolated.json.gz) include all three voices, wrap boundaries, rest/global suppression, delays, disabled programs and finite/looping pitch variants. Against existing full-form evidence, the helper matches **23,535** eligible body contexts and **5,791** exposed late pitch lookups; [all retained comparisons](../../../evidence/deflektor-caller/contexts.json.gz) preserve inputs, predictions and the checked scope. Scheduled rows are excluded. Later programs can overwrite earlier frequency/control results, so those values are compared only in skipped bodies or after an exposed final pitch lookup. No full-title CPU rerun, full synthesis, bus timing or listening claim follows.

Three [focused guards](../../../evidence/deflektor-caller/model_test.py) cover release-before-rest, global suppression before glide, the final wrapping glide step and finite pitch restoration. After obtaining the pinned reference and dependencies, copy the scripts to a fresh working directory; the [source checker](../../../evidence/deflektor-caller/check.py) creates its evidence exclusively:

```sh
mkdir build/deflektor-caller-new
cp evidence/deflektor-caller/model.py evidence/deflektor-caller/model_test.py evidence/deflektor-caller/check.py build/deflektor-caller-new/
python3 build/deflektor-caller-new/model_test.py
PYTHONPATH=.tools/test-deps python3 build/deflektor-caller-new/check.py
```

## Pulse, delayed pitch and shared resonance components

The pure [motion helpers](../../../evidence/deflektor-motion/model.py) consume immutable named state and explicit numeric tables, with the interface and source-field mapping in the [contract](../../../evidence/deflektor-motion/contract.json). They read no source file, original CPU, captured events or register ledger at runtime. Caller admission, row scheduling, patch selection and the ordered SID writer are separate responsibilities.

| Component / native locus | Numeric behavior |
| --- | --- |
| `advance_pwm`, `$C59A–$C640` | Increment an elapsed byte. On its interval, set the target high byte, clear the low byte and process direction/restart markers; interpolate toward the next target in that same invocation. Addition/subtraction changes only pulse low, without carrying or borrowing into high. |
| `initialize_pitch` / `advance_pitch`, `$C48D–$C49E` / `$C640–$C6CF` | Load the initial wait and position one. Positive waits decrement without stepping; negative waits run until their low seven bits expire, with `$80` holding. Signed byte steps update the full frequency word modulo 65,536; phase reversal reverses their sign. |
| `initialize_resonance` / `advance_resonance`, `$C4C8–$C4F0` / `$C7C3–$C80F` | The initializer adds one invocation to the first duration. Later stages use the literal low nibble, including zero; headers retain their literal low three bits, including zero. Each update replaces shared `$D417` high bits while preserving routing low bits. |

The [editable numeric tables](../../../evidence/deflektor-motion/verified-final/numeric-tables.json) retain required aliased ranges. PWM's unshifted base `$20` and delayed-pitch selector 8 share motion cells 32–39. PWM indexing wraps the byte addition; pitch applies its extra logical base 24 **after** that wrap. The resonance view also overlaps part of the retained motion range; their source mapping records that overlap, while each helper accepts an explicit editable mapping. Convert JSON object keys with `int(key)` before supplying a Python table. Missing/non-byte cells and non-terminating PWM marker chains reject explicitly.

The [verification receipt](../../../evidence/deflektor-motion/verified-final/verification.json) records **2,388 isolated original-segment comparisons**: 720 PWM, 750 delayed-pitch, 720 resonance, 54 pitch initializers and 144 resonance initializers. All three voices, low/word wrap, marker reversal, positive/negative waits, byte-index wrap, finite/loop positions and routing preservation are covered in the [complete isolated records](../../../evidence/deflektor-motion/verified-final/isolated-cases.json.gz); maximum segment cost is 225 cycles, with no SID stores or stack imbalance. The source oracles share the guarded py65 implementation, so this is independent arithmetic with a shared CPU oracle.

Against existing full-form evidence, [retained comparisons](../../../evidence/deflektor-motion/verified-final/contexts.json.gz) match **19,522** admitted body contexts, including **15,981 enabled PWM** and **4,863 exposed delayed-pitch** contexts and their final register pairs. PWM/pitch checks exclude row setup, rests and globally suppressed calls; enabled delayed pitch is checked only where the score glide and later score-pitch macro cannot hide its result. Shared resonance independently carries local timers/positions and one shared shadow through calls **0–8,480**, including **1,820 note initializers**, **663 patch-position resets** and **7,524 `$D417` writer checks**. Selectors and row/patch actions come from source evidence: this checks the composed resonance machinery, not an independent score scheduler.

The [mutation controls](../../../evidence/deflektor-motion/verified-final/mutation-controls.json.gz) detect pulse-step changes in 15,981 contexts, an altered pitch step in 159 contexts and reversed same-call voice order in 111 calls. First examples occur at 1/2 for pulse, 2,144/2,152 for pitch and 1,300/1,460 for voice order. These compare edited numeric inputs against retained incoming contexts; they are not edited full-source reruns. Eight [focused guards](../../../evidence/deflektor-motion/model_test.py) protect same-invocation PWM markers, low-only wrap, the aliased base, signed delay/reversal, literal zero resonance durations, voice order, disabled paths and rejected inputs.

After fetching the form evidence's Git LFS objects and installing the pinned reference/dependencies, reproduce into a fresh output directory:

```sh
python3 evidence/deflektor-motion/model_test.py
PYTHONPATH=.tools/test-deps python3 evidence/deflektor-motion/check.py .local/research/deflektor/Deflektor.sid --output build/deflektor-motion-new
```

The [checker](../../../evidence/deflektor-motion/check.py) pins the source, current guarded CPU dependencies and retained inputs before executing only bounded original segments. It exports numeric tables, named comparisons and bounded instruction evidence; no original SID, payload or full RAM image. The checkpoint adds no full-title CPU rerun, VICE run, render, acoustic comparison or listening judgment. The [complete numeric player](#compose-the-complete-finite-score-from-editable-data) composes these components without the original driver.

## Compose the complete finite score from editable data

The independent [numeric player](../../../scripts/deflektor_player.py) combines the [ordered score expander](../../../scripts/deflektor_score.py) and [reusable sound components](../../../scripts/deflektor_programs.py). Its [editable title description](../../../evidence/deflektor-player/title-runtime.json) supplies score bytes, instrument fields, decoded waveform/pitch programs, numeric frequency/motion tables and named cold software state. Runtime reads no original SID, CPU, files or captured event/register stream. The reference ledger is solely a comparison oracle.

The separately derived [cold/setup contract](../../../evidence/deflektor-setup/contract.json) checks 132 retained initialization RAM stores and selected native instruction semantics without a new original CPU run. Its [named cold state](../../../evidence/deflektor-setup/cold-state.json) and [256 frequency words](../../../evidence/deflektor-setup/frequency-words.json) exactly match the player description. To reproduce this auxiliary derivation, copy [retain.py](../../../evidence/deflektor-setup/retain.py) into a fresh one-level directory under `build/` and run it with the pinned reference and fetched evidence present; it creates its three JSON outputs exclusively. The contract distinguishes static branches from the selected title paths.

The [complete verification](../../../evidence/deflektor-player/verified/verification.json) matches all **166,845 ordered stores** over **40,000 calls**, projected to phase, call, address and value. This covers the entire finite score, its three control-zero stop stores at call **8,480**, and the following **31,519 calls without stores**. The [complete computed output](../../../evidence/deflektor-player/verified/computed-writes.json.gz) preserves the result. The exclusive caps 0, 1, 64, 8,480 and 8,481 yield 0, 13, 502, 166,842 and 166,845 stores respectively. Initialization emits none. These are register-order/value results; original instruction cycles, SID oscillator/envelope state, audible equivalence and an acoustic ending are not established by this model.

| Composed behavior | Contract |
| --- | --- |
| Cold state | Retain the source's loaded frequency/pulse/control/envelope shadows and global cutoff values. Row/rest counters must start at zero, matching the cold score cursors; this is not a resume-from-checkpoint API. Software shadows do not imply earlier hardware stores. |
| Row boundary | Prepare all voices before processing them in order 0, 1, 2. A countdown of one clears that voice's row/rest counters and suppresses the deferred writer and continuing programs globally, while row setup still runs. |
| Score effects and note setup | Preserve ordered commands/instrument/note/row operations. Effects `$90–$95` select the score-pitch program at `(token & 15) × 8`; the order detune parameter is an unsigned frequency-word addition. Base-zero PWM phase survives ordinary notes; nonzero-base note setup resets it. |
| Rest and stop | A rest immediately writes control zero for its voice, independently of the deferred writer. A terminal order stops processing immediately and emits control zero for all three voices; later voices cannot consume further score data that call. |
| Editable program data | Nine instrument fields have one authoritative copy, with a separate contextual resonance selector. Frequency, motion and resonance tables preserve source overlap on extraction, but are independent editable views; an edit to one does not silently change another. |
| Unsupported inputs | Unknown synthesis commands, missing programs, zero row durations and incompatible cold counters reject explicitly. The selected title's verified grammar is the supported scope, not every possible Daglish driver feature. |

Three [bounded edited-source comparisons](../../../evidence/deflektor-player/verified/edited-cases.json.gz) exercise the complete integration for 192 calls each: change pattern 2's first note **18→19**, its duration **10→12**, and record-offset 27's pulse step **21→22**. Each independently computed output exactly matches execution of the corresponding private source edit; differences from baseline occur in **10, 67 and 129 calls** respectively. The original file remains unchanged. The checker also rejects runtime file access, checks input preservation, and confirms 26 promoted component definitions match their frozen evidence implementations after validator renaming. Common byte/word validators are consolidated in the supported module.

Use `compute_writes(description, calls=...)` to generate ordered dictionaries with `phase`, `tick`, `address` and `value`; omit `calls` to use the description's `play_calls`. Source annotations are ignored. The [extractor](../../../evidence/deflektor-player/extract.py) pins the original and retained numeric inputs, preserving provenance separately from runtime fields. Reproduce with fetched evidence objects and the pinned private reference, into fresh paths:

```sh
python3 scripts/setup-project.py --only references --include deflektor
python3 evidence/deflektor-player/extract.py .local/research/deflektor/Deflektor.sid --output build/deflektor-player-new/title-runtime.json
PYTHONPATH=.tools/test-deps python3 evidence/deflektor-player/check.py build/deflektor-player-new/title-runtime.json --output build/deflektor-player-new/verified
python3 -m unittest discover -s tests -p 'deflektor_*_test.py' -v
```

The [checker](../../../evidence/deflektor-player/check.py) compares the full model against the retained original ledger and executes only the three short edited-source experiments. No original SID, full payload/RAM image or reference audio is archived. Independent compiled export, timing/VICE validation of that export, musical attribution, rendering/listening and original transfer remain separate milestones.

## Reproduce intake

The download registry retains the URL/fingerprint; the original stays in ignored local storage:

```sh
python3 scripts/setup-project.py --only references --include deflektor
python3 scripts/sid_intake.py .local/research/deflektor/Deflektor.sid --subtune 1 --host-base 0x0400 --output build/deflektor-host-new/header.json
PYTHONPATH=.tools/test-deps python3 scripts/psid_audit.py .local/research/deflektor/Deflektor.sid --profile pal-banked --subtune 1 --host-base 0x0400 --ticks 64 --output build/deflektor-host-new/audit64.json
python3 scripts/trace-sid-vice.py .local/research/deflektor/Deflektor.sid --profile pal-banked --subtune 1 --host-base 0x0400 --oracle build/deflektor-host-new/audit64.writes.json --first-call 0 --last-call 63 --output build/deflektor-host-new/vice64
```

Choose fresh output paths. [sid_intake.py](../../../scripts/sid_intake.py) reports PSID/RSID v2 declarations and selected-host admission separately; it performs no CPU execution. The following two commands execute the original under their declared controlled environments. To inspect instructions later, pass the same host selection to the [instruction tracer](../tools/sid-program-analysis.md#trace-a-selected-subtune-in-banked-ram). Reference WAVs remain local; no render or listening assessment has been made here.

Next attribute the recurring staged candidate by listening in context before choosing an intervention. Preserve its pitch/noise trajectory, articulation, shared-filter state and oscillator dependencies. The complete numeric player now computes the selected register sequence independently; the study still needs a compiled arrangement, acoustic ending, listening, and an original transfer phrase.
