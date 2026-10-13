# Monty on the Run: independent title reconstruction

Rob Hubbard's **Monty on the Run**, selected subtune **1**, is complete for its declared first-cycle reconstruction, source continuation and familiar transfer in the [delivery plan](../study-plan.md). Its independent packed-score player, complete first-cycle export, optional finite ending and familiar instrument transfer pass CPU, VICE and rendered-signal checks. The [listening package](#listening-package-and-reproduction) has accepted opening and familiar-transfer verdicts; the corrected continuation is also accepted: “identical sound (ref vs ours) to me. nice”. The finite release/fade remains a separate arrangement choice, not a prerequisite for accepting the source-faithful reconstruction. Musical section labels and original-game host behavior remain outside the established scope. Start with the [Hubbard composer study](../composers/hubbard-galway.md#hubbard-composing-with-a-changing-synthesis-engine), [listening catalogue](../composers/listening-catalogue.md) and [source-study boundary](../tools/source-studies.md).

## Reference and subtune attribution

The existing optional `monty-on-the-run` entry in [the source registry](../../../config/local-assets.json) owns the [HVSC download](https://www.hvsc.de/download/C64Music/MUSICIANS/H/Hubbard_Rob/Monty_on_the_Run.sid), ignored destination `.local/monty-source.sid` and SHA-256 `528a7330817e4a0a0f75a505e9fe2444e07c5072ce5383ceaa89f183f0eee3ab`. The 5,694-byte archive header credits **Rob Hubbard**, title `Monty on the Run`, release `1985 Gremlin Graphics`. The original SID stays outside Git; use the existing [setup workflow](../../setup/local-setup.md) to obtain and verify it.

Cached **STIL v85, June 28, 2026**, at `.local/downloads/HVSC-STIL.txt`, annotates only **#1** in this archive's entry. Its `TITLE` identifies **The Devil's Gallop [from the Dick Barton radio show]**, `ARTIST` **Charles Williams**: this is the original-piece/inspiration attribution, distinct from Hubbard's SID credit. Its comment attributes the energetic running character and the middle section's newly written pitch-bend code to Hubbard. The entry supplies no labels or roles for **#2–#19**; do not assume these are nineteen complete musical tunes. The [provenance receipt](../../../evidence/monty-intake/provenance.json) retains the whole-STIL hash, exact entry lines 50,857–50,868, original-CRLF entry hash and annotation scope.

## Header and callable contract

The reusable [header inspector](../../../scripts/sid_intake.py) records declarations separately from execution-profile admission in the [header receipt](../../../evidence/monty-intake/header.json).

| Archive field | Inspected value |
| --- | --- |
| Format / data offset | PSID v2 / `$007C` |
| Subtunes / default / selected | 19 / 1 / 1 |
| Header / embedded load | Header zero; embedded little-endian `$8000` |
| Init / play | `$8000` / `$8012` |
| Payload | 5,568 bytes, `$8000–$95BF`; end `$95C0` exclusive |
| Speed word / selected declaration | `$00000000` / VBI |
| Flags / layout | `$0014`: PAL, MOS6581, one SID at `$D400` |

The existing [PAL banked execution profile](../../validation/psid-audit.md#select-a-subtune-and-expose-ram-beneath-basic) accepts the intact archive with explicit `--subtune 1`. Initialization receives A=0, X/Y=0, P=`$26`; each play entry receives A=`$FA`, retained X/Y, C/Z set and N clear, with `$01=$36` restored before the call. This is the controlled raster host's ABI, not evidence of the original game's interrupt entry state. The speed word declares VBI; the CPU auditor imposes a 19,656-cycle PAL-frame budget and does not measure actual VBI dispatch cadence. Default strict admission still rejects the multi-subtune archive.

## Executed calls 0–63

The [CPU report](../../../evidence/monty-intake/audit.json) records initialization at **165 cycles**, with exactly three ordered writes: `$D404=0`, `$D40B=0`, `$D412=0`. The 64 play calls produce **641 SID stores**: 133, 181 and 263 to the respective voice register groups, plus 64 `$D418=$0F` stores. Maximum play-body cost is **1,460 / 19,656 cycles**; mean cost is **1,272.921875 cycles**. These figures describe this bounded window, not the whole tune's maximum.

The [complete ordered ledger](../../../evidence/monty-intake/audit.writes.json.gz) preserves 644 initialization/play records with phase, call, address, value and instruction-start cycle. Calls 1–63 each store to at least one register more than once; preserve those intermediate writes when interpreting the routine. Initialization only clears the three controls in this observation; it does not establish a complete SID register reset. The bounded execution passes the existing RAM, ROM, I/O, stack and call-budget guards without a source/header patch. It supplies no VICE comparison, interrupt/badline timing, bus-write timestamps, synthesized sound, form boundary or listening verdict.

## Existing interpretation routes

| Route | Evidence and next-use boundary |
| --- | --- |
| [Anthony McSweeney's 1993 Monty routine](https://www.neperos.com/article/rxmd9gd536b13923) | Already inspected in the composer study. It is reverse engineering with sound-effects code removed, not Hubbard's original labeled source. Its note/body split, eight-byte instruments, octave alternation, saved-high-byte descent and noise transient are predictions to test against this archive. The bounded correspondence below uses the pinned ACME listing; the web article has not been byte-compared with that listing or this archive. |
| [Recovered repository listing](https://github.com/realdmx/c64_6581_sid_players/blob/f215174fc4c983674808fcd47bc506f96b3d2d04/Hubbard_Rob/Hubbard_Rob_Monty_on_the_Run.asm) | Revision `f215174fc4c983674808fcd47bc506f96b3d2d04`, 31,840 bytes, Git blob `332b81b5ddd21d1ab20c7cd37c32ac786760a267`, SHA-256 `52dbbf891b1a1d0f8750842ef91ebaf1fc62d65d7b46497ae6951576ece3ae6c`. The subsequently downloaded listing credits McSweeney's original disassembly/commenting and dmx87's ACME port. It forces one song and omits the archive's additional sound-effects tail. Bounded correspondence is established below; it was not assembled. |
| [Hubbard's C64.COM account](https://www.c64.com/interviews/hubbard.html) and [contemporary April 1986 interview](https://www.muzines.co.uk/articles/techtalk-living-off-video/9284) | Existing composer research supplies the evolving-driver and delayed-vibrato/pitch-bend context. It does not assign exact records or executed mechanisms to this bounded Monty window. |

Do not carry reconstructed listing addresses or omitted sound-effects behavior into the archive by assumption. The following executed mapping supplies actual archive PCs; the later independent implementation builds on these findings. Listing correspondence alone supplies no listening claim.

## Executed score navigation

The [navigation receipt](../../../evidence/monty-form/navigation.json) separates listing/data matches from executed hooks. All three complete listing title order lists match the archive uniquely: `montymaintr1` at `$8618` (65 bytes), `montymaintr2` at `$8659` (76 bytes), and `montymaintr3` at `$86A5` (132 bytes), including each terminal `$FF`. The 96 interleaved frequency words match at `$8400`. All twenty instrument records' fields 2–7 match at `$93B4`; loaded pulse bytes differ for records 0, 8, 9 and 12, and executed stores at `$8287/$828E` mutate those shared table bytes. These matches do not establish a byte-identical driver or sound state.

| Navigation task | Actual archive state / executed PC |
| --- | --- |
| Tempo scheduling | Countdown `$84EB`, reload `$84EC`; reload 1 in the opening gives one score tick per two calls |
| Voice sequencing | Order cursors `$84C4–$84C6`, pattern cursors `$84C7–$84C9`, remaining lengths `$84CA–$84CC`; voice dispatch 2, 1, 0 |
| Consume order byte | `$8089`, `LDA ($02),Y`; track pointer banks `$8566/$8569` |
| Resolve pattern pointer | `$80AB/$80B0`, low/high banks `$857E/$85CB`; pointer `$04/$05` |
| Consume row fields | `$80C2` control/duration, `$80DD` instrument-or-portamento, `$80EE` pitch; `$80E7` commits a new instrument |
| Append path / instrument initializer | `$8118` / `$811E`; instrument table at `$93B4`, eight-byte records |
| End peek / advance order | `$8163` reads the next pattern byte; `$8169` resets pattern cursor and `$816E` advances order |
| Order `$FF` / `$FE` | `$8099` resets that voice's sequencing cursors/remaining length; `$8096` exits toward the outer tail. Do not assume `$FE` mutes or sets a global stop flag |
| Completed callable body | Outer `RTS` `$838C`, SP=`$FD`, with the saved return word checked against the shared host |

The [512-call instruction window](../../../evidence/monty-form/boundary.trace.json.gz) executes append seven times on voice 1 and first advances all three order cursors at call **448**, after pattern `$FF` peeks at `$8BDD/$8BE8/$8BFA`. It does not yet execute an order restart. The [hook checker](../../../evidence/monty-form/check-hooks.py) matches all **180** compact hook events and **4,946** ordered init/play stores against this independently retained instruction window; its [receipt](../../../evidence/monty-form/hook-validation.json) distinguishes observer fidelity from independent-machine evidence.

Retain raw note operands separately from inferred pitch names: opening voice 1 consumes `$68` (104), whose byte-doubled lookup offset `$D0` addresses `$84D0/$84D1`, beyond the declared 96-word frequency table and inside voice-control state. The archive also contains the `$838D–$83FD` sound-effects tail omitted by the listing. These are source-variant boundaries, not permission to invent a chromatic extension or discard latent state.

## Two observed title order traversals

The source-pinned [compact probe](../../../evidence/monty-form/probe.py) executes the shared `pal-banked` audit from initialization with default host `$C000`, records exact order/pattern reads, command branches, instrument records and every ordered SID store, and processes the entire requested cap. Its [40,000-call summary](../../../evidence/monty-form/full40000/summary.json) covers calls **0–39,999**, with 3 initialization stores and **373,736** playback stores, maximum **1,692 / 19,656 cycles**. The [observations](../../../evidence/monty-form/full40000/observations.json.gz) and [complete ledger](../../../evidence/monty-form/full40000/audit.writes.json.gz) are retained losslessly, without a source payload or RAM dump.

All three voices execute the order `$FF` restart branch at calls **17,536** and **35,072**. Thus calls **0–17,535** are the first complete title order cycle, with a second traversal and confirming restart also observed. There are 12,301 row consumptions, 601 pattern advances and six order-restart branch executions across the complete cap; no `$FE` exit executes. This is an executed order-cycle boundary, not a musical-section labeling or ending assertion.

The [reproducible comparison](../../../evidence/monty-form/describe.py) and [traversal receipt](../../../evidence/monty-form/traversal-comparison.json) preserve the raw order comparison as unequal: the second traversal begins with three terminal `$FF` reads absent at startup. Removing exactly those reads gives equal relative-call/voice/PC/source-address/value order streams. Pattern pointer, row, instrument/portamento, pitch, end-peek and instrument-index events match in those same fields. CPU registers, instruction cycles and mutable instrument-record values are excluded from that consumption comparison.

The corresponding ordered SID address lists differ on **153** calls, so these traversals are not identical register-stream replays. Values and timing are compared only where the complete per-call address lists agree; the receipt does not zip mismatching shapes. Selected post-body backing-RAM/CPU fingerprints at calls 0, 17,536 and 35,072 also differ. The hash recipe includes all 65,536 backing-memory bytes and A/X/Y/SP/status/PC at the fixed pre-RTS boundary, without normalization; it excludes the monotonically increasing CPU cycle count and unmodeled SID internals. Neither score repetition nor these software-state checks establishes oscillator/envelope/PCM recurrence.

Independent VICE checks initialization and calls **17,530–17,543** against the retained CPU ledger: all **149** stores agree (3 init, 146 play). All 17,544 play-entry checkpoints stay within **7** cycles of the PAL grid, inside the nine-cycle polling tolerance. The [projection receipt](../../../evidence/monty-form/vice-wrap/projection.json), [VICE study](../../../evidence/monty-form/vice-wrap/trace/study.json) and [parsed trace](../../../evidence/monty-form/vice-wrap/trace/trace.json.gz) own that bounded result. This verifies the declared controlled host around the first wrap, not the original game's IRQ host, complete 40,000-call VICE equality or audio.

## Bounded note and continuing sound programs

The source-free [numeric helper](../../../evidence/monty-programs/model.py) computes immutable named voice/instrument state and ordered relative SID stores through `initialize_note(...)` and `advance_body(...)`. The [contract](../../../evidence/monty-programs/contract.json) maps its fields to actual archive bytes and separates static instruction loci from execution. Eight-byte instruments at `$93B4` contain shared pulse low/high, waveform, AD, SR, vibrato depth, packed PWM value and effect masks `$01/$02/$04` (drum, saved-high descent, octave alternation). The [selected-record inventory](../../../evidence/monty-programs/records.json) records fourteen actual title indices, their first executed values and every observed mutable pulse word; these are source indices, without guessed musical roles.

| Operation | Actual archive locus and established behavior | Executed visits in calls 0–511 |
| --- | --- | --- |
| New note / append setup | `$80ED–$8170`: new note emits frequency high→low, then control, pulse low→high, AD and SR; append retains pitch but reapplies control with gate masked off, pulse and ADSR. Both retain PWM delay/direction and skip the continuing body that call. There is no universal gate-off/TEST sequence proving every new note restarts ADSR. | 17 new-note setups; 7 appends |
| Scheduled release | `$8174–$81A2`: raw control bit `$20` clear and remaining length zero emits saved control `&$FE`, AD=0, SR=0. It does not change the saved control. | 8 at `$8190` |
| Vibrato | `$81A3–$822F`: eight-call phase `0,1,2,3,3,2,1,0`; unsigned adjacent-word difference is shifted using the actual signed depth loop. Enabled vibrato emits low→high without updating the held frequency. Raw control length below eight suppresses the displacement. | 1,512 at `$8227` |
| Shared PWM | `$8230–$8296`: nonzero packed value decrements per-voice delay; a negative result reloads `value&$1F` and adds/subtracts `value&$E0` modulo 12 bits. High-byte equality `$E`/`$8` changes direction, without clamping. Table high and SID high precede table low and SID low. | 78 at `$8287` |
| Portamento / drum | `$8297–$8319`: portamento changes the held word modulo 16 bits; drum can emit the old held high byte while decrementing its saved value, then change control. Exact edge cases are in the numeric contract/checker. | No active updates; synthetic source cases only |
| Saved-high descent | `$831A–$8335`: odd counter and nonzero held high decrement the saved byte, but the SID receives its old value because `LDA` precedes `DEC`. The hardware word can retain a low byte from an earlier vibrato write. | 65 at `$832D` |
| Octave alternation | `$8336–$8366`: parity selects raw note or byte-wrapped note+12, then byte-doubles the lookup index; high→low stores occur last and leave the held buffer unchanged. | 504 at `$835E` |

PWM updates the instrument bank, while delay/direction remain per voice. A caller must install the returned instrument before processing the next voice in order **2, 1, 0**, and retain both bank and voice state across note/append/order restarts. For actual record 12, onset pulse widths at the corresponding first rows are `$0BA0`, `$09E0` and `$0820` at calls **0**, **17,536** and **35,072**. Equal score consumption therefore does not imply equal onset sound parameters.

Native raw note **104** supplies a second concrete retained-state dependency: frequency loads `$8400+$D0` and `$8401+$D0` read saved voice controls `$84D0/$84D1` before the initializer replaces them. The observed word is `$4141` at call 0 and `$8141` at calls 17,536 and 35,072. The [context proof](../../../evidence/monty-programs/context-verification.json) forks only prior voice-1 control `$41→$81` in the original initializer; only its frequency-high store and held word change. An independent PWM control sets only packed pulse value `$81→0`, removing pulse stores while preserving other stores and pulse state. Neither control attributes all traversal differences or establishes an audible judgment.

The [main verification](../../../evidence/monty-programs/verification.json) matches **11,568** isolated original-block cases across all three voices, plus **17** note setups, **7** append setups and **1,512** continuing blocks from the retained 512-call trace. The [context checker](../../../evidence/monty-programs/context.py) adds **2,882** cases: 2,688 using title-selected record values, 192 synthetic shared-bank steps and two alias forks. Its [complete numeric cases](../../../evidence/monty-programs/context-cases.json.gz) retain input/output state, ordered stores and source-block cycles. Retained continuing comparisons begin at `$81A3`, after the release prelude; release arithmetic is checked separately against original blocks. The largest synthetic block takes 2,599 cycles, which is not a measured title maximum.

This bounded helper covers the title's enabled negative `$84FD` context. Its caller owns score scheduling, portamento setup/reset, lookup resolution at each stage, global writes and init/body selection; the positive sound-overlay branch and omitted listing sound-effects tail are outside this component proof. `PitchLookups` are numeric inputs resolved from current state, not an invented chromatic extension. The later full-player integration below adds the caller; the historical component receipts remain unchanged.

## Independent editable score and sound integration

The [numeric source description](../../../songs/monty-title-source.json) contains three packed orders, their reachable patterns, exactly 96 frequency words, twenty named instruments, cold voice/global state and typed lookup aliases. [prepare-monty-title.py](../../../scripts/prepare-monty-title.py) checks the original fingerprint, extracts these numeric fields and verifies cold state at the first play boundary through one guarded source call. It preserves the nonzero loaded PWM phases: initialization changes the named status to `$40`, while the first play call performs the sequence reset. The description contains no original driver or full-memory snapshot; playback uses neither the SID nor source annotations.

The [independent scheduler](../../../scripts/monty_title_score.py) computes packed row consumption and voice dispatch in order 2, 1, 0. Control bit `$40` selects a one-byte append; otherwise bit `$80` selects a parameter plus pitch, and an ordinary row consumes control plus pitch. The low five control bits reload duration; it takes one additional score tick to select the next row. The tempo countdown's negative decrement reloads the tempo, but the subsequent equality with the reload value decides score dispatch. These are distinct tests, including for edited initial countdowns. `$FF` order restarts retain sound/control state; unsupported `$FE`, negative-status and overlay contexts reject explicitly.

The [complete score proof](../../../evidence/monty-title-score/verification.json), reproduced by its [checker](../../../evidence/monty-title-score/check.py), agrees with all 51,508 retained consumed-byte reads over 40,000 calls, every pointer selection, all 12,301 initializer sequence states, 151 appends, 601 pattern advances, six voice-order restarts and the final sequence state. It checks all 120,000 voice dispatches without rerunning the original CPU. This establishes numeric score semantics, separately from sound stores and timing.

The [complete numeric player](../../../scripts/monty_title_player.py) integrates that scheduler with [typed sound programs](../../../scripts/monty_title_programs.py). Shared pulse widths update before the next voice; lookup aliases resolve from named state when each stage actually reads them. In particular, new-note frequency precedes replacement of the saved waveform, and octave frequency follows PWM, portamento, drum and descent. The stage-specific resolver is essential when a lookup aliases a pulse-direction byte changed by the same call. Source annotations remain nonexecuting provenance, and inputs remain unchanged.

The [full player proof](../../../evidence/monty-title-player/verification.json) matches all **373,739** ordered init/play stores across 40,000 calls with the retained original ledger, including both restarts. Four separate 192-call private-source interventions change a score pitch, packed pulse step, prior saved waveform and octave enable; the independently edited descriptions match all resulting stores. They affect 64, 26, 97 and 189 calls respectively. The octave intervention is synthetic coverage of a stage-specific alias, not a claim that the title itself enables that combination. The [checker](../../../evidence/monty-title-player/check.py), [complete computed ledger](../../../evidence/monty-title-player/computed-writes.json.gz) and [edited cases](../../../evidence/monty-title-player/edited-cases.json.gz) preserve the evidence without original payloads. Instruction cycles, SID internal state, PCM and musical quality are not inferred from ordered-store equality.

The independently written [6502 sound component](../../../songs/players/monty-effects.asm) uses the same named-state contract. Its [CPU guards](../../../tests/monty_effects_asm_test.py) compare ordered stores and resulting voice/shared-bank state with the numeric programs, covering all voices, retained append phase, signed vibrato-depth edges, adjacent lookup wrapping, PWM turning limits, portamento overflow, combined effect priority and late aliases. Writes outside the selected voice, shared pulse record, scratch, stack and SID are rejected by the test harness. Component behavior is established separately from the full compiled and cadence checks below.

Reproduce the numeric source description and retained proofs in fresh ignored paths:

```sh
PYTHONPATH=.tools/test-deps python3 scripts/prepare-monty-title.py --check songs/monty-title-source.json
mkdir build/monty-title-score-recheck
cp evidence/monty-title-score/check.py build/monty-title-score-recheck/check.py
python3 build/monty-title-score-recheck/check.py
PYTHONPATH=.tools/test-deps python3 evidence/monty-title-player/check.py --output build/monty-title-player-recheck
```

The extraction check and four causal interventions require the pinned local original; the scheduler proof and numeric playback use tracked numeric inputs and retained observations only. The original remains unchanged. `compute_player(description, calls=N)` returns ordered stores, final named state, shared instruments and finite-stop status; `compute_writes` returns only the stores. Caps are exclusive and cannot exceed declared `play_calls`. Existing deferred Monty files remain untouched; these supported modules use distinct `monty_title_*` names.

## Independent title export and finite ending

[prepare-monty-title-ending.py](../../../scripts/prepare-monty-title-ending.py) preserves the first complete title cycle `[0,17536)` in the [finite description](../../../songs/monty-title.json), then adds 64 release calls and sixteen four-call fade levels. Source music lasts approximately **349.848 seconds**; the declared 17,664 calls end at **352.402 seconds**. This ending replaces the original order restart and introduces no new score notes. It is an optional arrangement; the listener's request to preserve the reference's continuation supersedes it as the reconstruction candidate.

[compose-monty.py](../../../scripts/compose-monty.py) assembles our [scheduler](../../../songs/players/monty.asm) and sound component with 58 packed patterns, three order lists and twenty editable instruments. The **5,351-byte** payload loads at `$1000`; it consumes rows and computes synthesis at runtime. Typed pointer tables resolve declared lookup aliases to current named state, without embedding the source RAM layout. Initialization restores voice/global state, the shared instrument bank and output-control shadows. No zero-page workspace is claimed from the caller. See the [public compiler contract](../../workflows/decoded-song-workflow.md#monty-packed-score-player) and [integration guards](../../../tests/monty_compiler_test.py).

During the tail, score cursors, tempo countdowns and remaining durations freeze. The global counter and continuing sound programs advance. The first tail call closes the **actual last output controls**, which can differ from saved waveforms after a drum substitution; every subsequent control store remains gate-masked. Saved controls retain their values for state-dependent pitch lookups. `$D418` preserves mode bits and follows levels 15 through 0, reaching zero at call **17,660**. After call 17,663, play returns without further stores or named-state changes. [Ending guards](../../../tests/monty_ending_test.py) distinguish that explicit behavior from source equivalence or acoustic silence.

The [build receipt](../../../evidence/monty-independent-full/candidate/build.json) and [CPU audit](../../../evidence/monty-independent-full/candidate/audit.json) cover all 17,664 calls: **163,466** ordered init/play stores and **11** matching complete named-state checkpoints, including shared instruments and finite-stop state. Maximum play cost is **2,394 / 19,656 cycles**. The [source-prefix comparison](../../../evidence/monty-independent-full/source-comparison.json) matches all **162,695** original init/music stores before the ending; its remaining **771** stores belong to the explicitly checked arrangement tail. Instruction-start cycles are retained, not equated with the original driver.

The [full VICE receipt](../../../evidence/monty-independent-full/vice/study.json) agrees on **163,463 playback stores** over **17,666 host calls**, including two stopped calls without writes. The three initialization stores are covered by CPU evidence, outside this strict VICE playback comparison. Maximum cadence deviation is **7 cycles**, within the nine-cycle polling tolerance. [Complete CPU stores](../../../evidence/monty-independent-full/candidate/writes.json.gz), [named checkpoints](../../../evidence/monty-independent-full/candidate/state-checkpoints.json) and [VICE trace](../../../evidence/monty-independent-full/vice/trace.json.gz) remain lossless evidence. These results describe the controlled PAL host, not original-game IRQ timing or physical SID equivalence.

Compiling the 40,000-call source description without `ending` is a bounded diagnostic: preflight guarantees reads only inside the declared call window. Its binary is not an indefinitely verified music export. That supported window includes the first restart and supplies the corrected 355-second reference-continuation audition below. The finite title and transfer retain their separately checked stop behavior. A metadata-only compiler clarification after the initial export regenerates the exact same finite SID bytes, SHA-256 `afc976c6271652b2357523c98fd4b960509d3fdd8fcd54ed2555f647d7254522`.

## Listening package and reproduction

**Status, 2026-10-13: opening, corrected reference continuation and familiar transfer accepted.** Opening: “I don't hear a difference.” Für Elise: “music is spot on.” Earlier ending: “Identical, although the original played from 10:30s to 15:00s, while there is basically silence in ours from 25:80s onward (till end)”. After an explanation and waveform comparison, the listener requested that the ending WAV preserve the reference sound after restart. The correction therefore uses the source description without an imposed release/fade; the listener accepted it as “identical sound (ref vs ours) to me. nice”. The optional finite ending has no acceptance verdict and no longer blocks the reconstruction review. These verdicts cover the presented comparisons, not an additional uninterrupted full-title audition or PCM identity.

| Judgment | Ignored local samples and order |
| --- | --- |
| Title sound and phrasing | `build/monty-independent-full/listening/opening-reference-then-ours.ab.wav`: original first, independent version second, source seconds 0–24, 0.5-second gap, 48.5 seconds total |
| Corrected reference continuation | `build/monty-reference-continuation/listening/ending-reference-then-ours.ab.wav`: original first, independent continuation second, source seconds 340–355, 0.5-second gap, 30.5 seconds total; both preserve the restart |
| Complete corrected context | `build/monty-independent-full/reference/reference.wav` and `build/monty-reference-continuation/reconstructed.wav`, 355 seconds each |
| Earlier optional finite ending | `build/monty-independent-full/listening/ending-reference-then-ours.ab.wav`: original first, finite candidate second, source seconds 340–355, 30.5 seconds total; the original restarts while the candidate releases/fades. Its full render remains `build/monty-independent-full/candidate/reconstructed.wav` |
| Familiar instrument reuse | `build/monty-elise-transfer/listening/plain-then-monty.ab.wav`: generated plain Für Elise first, the same 53 notes with Monty instruments second, 30.5 seconds total |
| Transfer ending and separate full files | `build/monty-elise-transfer/listening/ending-plain-then-monty.ab.wav` covers seconds 8–14; separate files are `build/monty-elise-transfer/reference/reference.wav` and `build/monty-elise-transfer/candidate/reconstructed.wav` |

The earlier finite-ending A/B contains original audio at **0–15 seconds**, a **0.5-second gap**, then the finite candidate at **15.5–30.5 seconds**. Both halves cover full-render seconds 340–355, so subtract 15.5 seconds from candidate positions when comparing. At A **9.848 seconds** / B **25.348 seconds**, the original restarts its order cycle while the finite candidate closes its gates. B **25.8 seconds** therefore corresponds to A **10.3 seconds**: the original is already playing its next cycle while the finite candidate's envelopes are releasing. The master-volume fade starts at B **26.625 seconds** and reaches zero at **27.822 seconds**; envelope release makes it quiet before that. Equal comparison windows retain the resulting silent tail. These timings explain the optional finite arrangement; they are not the corrected reconstruction's behavior.

The listener’s subsequent waveform comparison correctly identifies reference audio absent from the candidate after that boundary. This is real changing audio, not merely a DC offset. Re-expanding the pinned [numeric source](../../../songs/monty-title-source.json) with [the scheduler](../../../scripts/monty_title_score.py) shows that call 17,536 selects the same opening note/instrument pairs as call 0: voice 2 `(19, 8)`, voice 1 `(104, 12)`, voice 0 `(86, 6)`. These are native note indices and record IDs. The original restarts its opening sound sequence; the finite candidate deliberately suppresses those new notes. Thus the entire earlier finite-ending A/B is **not a source-equivalent reconstruction comparison**: equivalence claims stop before the arranged tail. A waveform or listening report of that missing sound must not be dismissed merely because the cut was intentional.

The [finite-title audio recipe](monty-title-audio.json) pins the original URL/hash, renderer/library/settings, finite generated SID, PCM hashes, frame windows and reproduction commands. Both original/finite full title renders are mono PCM16 at 44,100 Hz, unclipped, with original levels retained. Opening AC RMS differs by approximately **−0.0022 dB**, so the comparison uses unity gain. The finite candidate's final second has **AC RMS zero** at constant −157 PCM; this is settled output, not literal PCM zero. [Audio evidence](../../../evidence/monty-independent-full/audio-evidence.json) retains those measurements and separate signal/listening scopes.

The [familiar-transfer card](instruments/monty-decoded-programs.md) owns records 2/6/15, editable controls and conversion limits; its [recipe](monty-elise-audio.json) labels the plain reference as generated, not an original recording. Both versions retain all 53 source notes and the same packed calendar. Their 630-call CPU and 632-call VICE runs pass, including two stopped calls, with maximum cadence deviation 7 cycles. Plain/Monty total CPU stores are 1,396/2,832; full renders are unclipped and settle to constant output. The full comparison attenuates Monty by **4.721 dB** for matching; the separate ending comparison retains unity gain. The listener accepted this familiar transfer: “music is spot on.” That verdict supports these programs on this matched phrase, not arbitrary material.

### Correct the reference continuation

Use the [numeric source description](../../../songs/monty-title-source.json), which contains no `ending`, with the existing compiler and renderer. The [corrected audio recipe](monty-reference-continuation-audio.json) pins inputs, settings and comparison scope. The corrected A/B keeps the same original reference and the same source seconds **340–355**: A **0–15 seconds**, gap **15–15.5**, B **15.5–30.5**. The independent player continues through call **17,536** with retained sound state; it does not substitute silence for the restarted opening. Review the sound after A **9.848 seconds** / B **25.348 seconds**. The renderer stops capture at 355 seconds; that file boundary is not an authored musical stop.

The fresh compiled source-description audit covers **40,000 calls**, matches all **373,739** ordered init/play stores directly against the retained original ledger and agrees at **nine** complete named-state checkpoints. The store comparison includes phase, call, address and value across both observed restarts. Headless VICE separately matches all 2,832 stores in calls 17,520–17,800 across the restart, with maximum cadence deviation seven cycles. The restored passage at seconds 350.3–355 has AC RMS −18.369 dBFS versus the reference’s −18.355 dBFS, with no clipped samples. The listener separately accepted this corrected comparison: “identical sound (ref vs ours) to me. nice”.

Reproduce in a fresh directory with the [pinned renderer setup](../../workflows/audio-workflow.md). Wait for each render to finish before preparing the comparison:

```sh
PYTHONPATH=.tools/test-deps python3 scripts/compose-monty.py songs/monty-title-source.json --output build/monty-reference-continuation-reproduce/candidate
mkdir -p build/monty-reference-continuation-reproduce/reference
.local/bin/render-sid .local/monty-source.sid build/monty-reference-continuation-reproduce/reference/reference.wav 355
.local/bin/render-sid build/monty-reference-continuation-reproduce/candidate/reconstructed.sid build/monty-reference-continuation-reproduce/candidate/reconstructed.wav 355
python3 scripts/compare-audio.py window build/monty-reference-continuation-reproduce/reference/reference.wav build/monty-reference-continuation-reproduce/candidate/reconstructed.wav build/monty-reference-continuation-reproduce/listening/ending-reference-then-ours --start-seconds 340 --end-seconds 355 --gap-seconds 0.5
```

### Reproduce the optional finite arrangement

Rebuild the earlier finite title, verify real cadence and render the original/candidate in fresh paths:

```sh
python3 scripts/prepare-monty-title-ending.py --check
PYTHONPATH=.tools/test-deps python3 scripts/compose-monty.py songs/monty-title.json --output build/monty-title-reproduce/candidate
python3 scripts/trace-sid-vice.py build/monty-title-reproduce/candidate/reconstructed.sid --oracle build/monty-title-reproduce/candidate/writes.json --first-call 0 --last-call 17665 --timeout 180 --output build/monty-title-reproduce/vice
mkdir -p build/monty-title-reproduce/reference
.local/bin/render-sid .local/monty-source.sid build/monty-title-reproduce/reference/reference.wav 355
.local/bin/render-sid build/monty-title-reproduce/candidate/reconstructed.sid build/monty-title-reproduce/candidate/reconstructed.wav 355
```

The recipe adds exact A/B and measurement commands. [compare-source.py](../../../evidence/monty-independent-full/compare-source.py) reproduces the source-prefix and arranged-tail checks from the pinned original ledger; [package-audio.py](../../../evidence/monty-independent-full/package-audio.py) retains signal measurements and reproduction settings. Reference SID/WAV and A/B files stay local in ignored `.local/` or `build/`, never Git or LFS. Canonical numeric evidence follows the [archive workflow](../../workflows/build-cache.md); useful audition files remain local.

### Reproduce the bounded sound checks

Copy the canonical gzip inputs unchanged to their historical ignored working paths, preserving any different existing files. The checkers read gzip directly; evidence restoration otherwise recreates decompressed JSON paths. Install the pinned original through the setup command below, then run in a fresh directory:

```sh
mkdir -p build/monty-form/full40000
cp -n evidence/monty-form/boundary.trace.json.gz build/monty-form/boundary.trace.json.gz
cp -n evidence/monty-form/full40000/observations.json.gz build/monty-form/full40000/observations.json.gz
cp -n evidence/monty-form/full40000/audit.writes.json.gz build/monty-form/full40000/audit.writes.json.gz
mkdir build/monty-programs-new
cp evidence/monty-programs/model.py evidence/monty-programs/check.py evidence/monty-programs/context.py evidence/monty-programs/retain-contract.py build/monty-programs-new/
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 build/monty-programs-new/check.py
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 build/monty-programs-new/context.py
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 build/monty-programs-new/retain-contract.py
```

Receipts pin the original, retained inputs, model/checker and shared CPU/profile/host tools. The source blocks execute only private synthetic RAM copies with the existing guarded CPU; the SID file remains unchanged. Archive selection is the four scripts, `contract.json`, `records.json`, both verification receipts and `context-cases.json.gz`; no original SID, complete payload/RAM image or third-party listing is included.

## Reproduce the form probe

Restore the retained scripts through the [evidence workflow](../../workflows/build-cache.md), or copy `probe.py` into a fresh ignored working directory as below. The listing stays private/ignored; retain only its attribution, URL and fingerprints in public evidence. The probe verifies both the intact SID and listing before execution and requires a fresh output directory.

```sh
mkdir build/monty-form-new
cp evidence/monty-form/probe.py build/monty-form-new/probe.py
curl -fsSL https://raw.githubusercontent.com/realdmx/c64_6581_sid_players/f215174fc4c983674808fcd47bc506f96b3d2d04/Hubbard_Rob/Hubbard_Rob_Monty_on_the_Run.asm -o build/monty-form-new/Hubbard_Rob_Monty_on_the_Run.asm
shasum -a 256 build/monty-form-new/Hubbard_Rob_Monty_on_the_Run.asm
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 build/monty-form-new/probe.py --ticks 40000 --output build/monty-form-new/full40000
gzip -dk build/monty-form-new/full40000/audit.writes.json.gz
python3 scripts/trace-sid-vice.py .local/monty-source.sid --profile pal-banked --subtune 1 --oracle build/monty-form-new/full40000/audit.writes.json --first-call 17530 --last-call 17543 --timeout 180 --output build/monty-form-new/vice-wrap
```

The archive restoration command writes decompressed JSON to the manifest’s working paths. To rerun `check-hooks.py` or `describe.py` against retained records, copy the canonical `.json.gz` files into the corresponding working subfolders unchanged: these checkers read gzip files and pin their stored bytes. Fresh probe runs already produce that layout.

Decompression restores the JSON oracle expected by VICE; the retained init-plus-window projection is also sufficient for this selected window. The existing source acquisition commands below install the SID, not the attributed listing. No reconstruction, render or listening question is part of this checkpoint.

## Reproduce without publishing the original

Run from the repository root after [local dependency setup](../../setup/local-setup.md). Choose a fresh directory: the inspector, auditor and intake collector create their output files exclusively.

```sh
python3 scripts/setup-project.py --only references --include monty-on-the-run
python3 scripts/setup-project.py --check --only references --include monty-on-the-run
python3 scripts/sid_intake.py .local/monty-source.sid --subtune 1 --output build/monty-intake-new/header.json
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 scripts/psid_audit.py .local/monty-source.sid --ticks 64 --profile pal-banked --subtune 1 --output build/monty-intake-new/audit.json
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 evidence/monty-intake/intake.py --output build/monty-intake-new
```

The retained [source-specific collector](../../../evidence/monty-intake/intake.py) requires the pinned cached STIL input and the existing repository tree, verifies source/header/profile pins and ledger coverage, and writes `provenance.json`. It does not implement another SID header parser or CPU. The receipt pins source URL/hash, registry, metadata inputs, tool hashes, Python/py65 versions and output hashes. The original 64-call ledger's uncompressed SHA-256 is `cbe755241603ab276b1f25877bbe63a98b1db571c51bb55273d7946af7a0e406`; use the [evidence restoration workflow](../../workflows/build-cache.md) for compressed working artifacts. No SID, WAV or payload dump belongs in this evidence set.
