# Cybernoid II: title form and executed command semantics

This prepares Jeroen Tel's **Cybernoid II**, title subtune **1**, while Shades remains the sole active reconstruction under the [study plan](../study-plan.md). It establishes archive identity, execution under an explicit PAL host, two complete order-list traversals, contextual score commands and executed opening pitch, waveform/PWM, filter and arpeggio mechanisms. Complete synthesis semantics, original-host equivalence, independent reconstruction and listening remain separate work. Consult the [composer account](../composers/huelsbeck-tel.md#jeroen-tel-arrangement-and-driver-collaboration), [listening catalogue](../composers/listening-catalogue.md) and [source-study boundary](../tools/source-studies.md) before extending this intake.

## Archive identity

The [optional `cybernoid-ii` asset](../../../config/local-assets.json) owns the [HVSC URL](https://www.hvsc.de/download/C64Music/MUSICIANS/T/Tel_Jeroen/Cybernoid_II.sid), SHA-256 `41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192` and ignored destination `.local/research/cybernoid-ii/Cybernoid_II.sid`. The downloaded file is 4,502 bytes. Its header credits **Jeroen Tel**, title `Cybernoid II`, release `1988 Hewson`. The [recovered source](https://github.com/realdmx/c64_6581_sid_players/blob/f215174fc4c983674808fcd47bc506f96b3d2d04/Tel_Jeroen_MON/Tel_Jeroen_Cybernoid2.asm) separately credits **Charles Deenen** for `MUSICFILE V01-07-1988`; retain music and driver credit separately.

| Actual archive field | Inspected value |
| --- | --- |
| Format / header size | PSID v2 / `$007C` bytes |
| Subtunes / default | 2 / 1 |
| Selected musical scope | #1 title; cached HVSC STIL labels #2 game over |
| Speed word | `$00000000`: VBI declaration for both subtunes |
| Flags / SID layout | `$0014`: explicit PAL, MOS6581, one SID; additional-SID fields zero |
| Header / embedded load | Header zero; embedded little-endian `$A600` |
| Init / play | `$A600` / `$A603` |
| Payload | 4,376 bytes, `$A600–$B717`; end `$B718` exclusive |
| Relocation fields | Start page and page count zero |

Reproduce acquisition and verification through the existing [setup workflow](../../setup/local-setup.md), without another downloader:

```sh
python3 scripts/setup-project.py --only references --include cybernoid-ii
python3 scripts/setup-project.py --check --only references --include cybernoid-ii
```

Both commands also select the two existing default DRAX references. Setup installs only verified bytes and preserves a modified local file rather than overwriting it. Reference binaries and WAVs remain outside Git.

## Bounded correspondence with the recovered listing

The existing cached listing `.local/downloads/tel-cybernoid2.asm` has SHA-256 `119b8cb1ecaf6a9700d1847c9879fa78d50229345dccaaa4f555d8354b73fe66` and the source revision linked above. It declares a generated `$1000` layout with init `$1000`, play `$1006`, two/default 1, zero speed word and PAL/6581 flags. The archive instead contains entry shims: `$A600→$A606` (`TAX`, then jump through `$A620→$A6CA`) and `$A603→$A626→$A716`. Do not reuse listing addresses as archive PCs.

| Static comparison | Result and limit |
| --- | --- |
| Literal initialization fragment, listing lines 190–194 | `STY $D416; INY; STY $D417; LDA #$1F; STA $D418` matches bytes `8c16d4c88c17d4a91f8d18d4` once at `$A6F5`. This is a code-byte match, not an observed store sequence. |
| Annotated nonempty eight-byte sound records, listing lines 1505–1522 | All 18 match once each, in source order, contiguously at `$B01C–$B0AB`. The 144-byte block has SHA-256 `25e907f6d8b97bb30b49d57e8d750032812a975ff892a409e4420fa958126377`. |
| Selected labels retained as navigation | `bass` at `$B01C`, `bassdrm` at `$B024`, `snardrm` at `$B02C`, `arp+filt` at `$B034`, first `melo-1` at `$B03C`. The static match attaches source labels to bytes; executed opening selection is established separately below. |

The limited comparison makes the recovered listing a useful interpretation route. It does not prove that the entire player, score, tables or effect timing are byte-identical. The listing was not assembled during this intake. The [source-comparison receipt](../../../evidence/cybernoid-ii-intake/source-comparison.json) retains the exact record matches, bounded static disassembly and comparison limits; the [header receipt](../../../evidence/cybernoid-ii-intake/header.json) retains the inspected archive metadata. Separate bass and drum definitions do not establish actual voice time-sharing in a particular phrase.

## Reproduce the opening reference

Use the existing [audio renderer](../../workflows/audio-workflow.md), libsidplayfp **3.1.1 / SIDLite**, from initialization. Its `selectSong(0)` selects the archive's default #1. The render uses forced PAL, the declared MOS6581, power-on delay zero, 44,100 Hz mono PCM16, 30 seconds, unity gain, no normalization and no trimming. Choose a fresh output directory; the renderer does not protect an existing output from replacement.

```sh
mkdir build/cybernoid-ii-intake-new
.local/bin/render-sid .local/research/cybernoid-ii/Cybernoid_II.sid build/cybernoid-ii-intake-new/reference-opening.wav 30
shasum -a 256 build/cybernoid-ii-intake-new/reference-opening.wav
```

The [observed opening WAV](../../../build/cybernoid-ii-intake/reference-opening.wav) SHA-256 is `60c139597792fbe0251ecf563c6dfcd6c544c3486c7ff0c78e967b9723cd650c`. It contains 1,323,000 sample frames, peak 11,661, AC RMS approximately 3,186.94 and zero PCM rail samples. The renderer executable SHA-256 is `80c6e88730445f65e03e28a56bb251922461e6d4364897b0bd79195edb53fdfe`; its [source](../../../scripts/render-sid.cpp) SHA-256 is `c7bc5f7b0fe8d18a54ecde7338b6efa786f87f54ec258a00fb01025486bad5fc`. The [render receipt](../../../evidence/cybernoid-ii-intake/render-receipt.json) retains the command, settings and measurements. This is an opening reference, with no listening verdict or complete-form/ending claim.

## Selected-subtune execution

The shared [execution profile](../../validation/psid-audit.md#select-a-subtune-and-expose-ram-beneath-basic) now accepts the intact archive through `--profile pal-banked --subtune N`. It restores `$01=$36` before each call, exposing RAM beneath BASIC. This matches the address-dependent bank choice in the inspected [libsidplayfp 3.1.1 `iomap`](https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/psiddrv.cpp); its [song limit](https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/sidtune/SidTuneBase.h) is 256. Our parser rejects malformed song metadata rather than silently repairing it. No source header, code or table bytes are patched.

Init receives A=`subtune−1`, X/Y=0 and P=`$26`. Play receives A=`$FA`, retained X/Y and the successful raster comparison's C/Z set, N clear. This is the controlled polling host's contract; [libsidplayfp's IRQ driver](https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/psiddrv.a65) enters play with A=0. The bounded equality below establishes the declared host, not equivalence of those entry environments or synthesized PCM. The default strict profile and the separate [Shades CIA route](../../validation/cia-tracing.md) retain their existing scope.

On 2026-10-13, independent CPU execution and headless VICE agreed on every ordered `(phase, call, SID address, value)` in these windows, including initialization:

| Selected subtune / observed calls | Init stores / cycles | Play stores / maximum body cycles | VICE cadence |
| --- | --- | --- | --- |
| #1 title, 0–599 | 25 / 1,738 | 10,333 / 2,473 | 600 calls; phase deviation at most 5 cycles from the 19,656-cycle PAL grid |
| #2 game over, 0–63 | 25 / 1,738 | 1,253 / 2,599 | 64 calls; phase deviation at most 5 cycles from the same grid |

The polling tolerance is nine cycles; the CPU play-body budget is one PAL frame. Initialization writes `$D416=$FF`, `$D417=$00`, `$D418=$1F`, followed by zeroes to `$D415` down through `$D400`, in both selected runs. VICE captures stores from init entry through its return separately from outer play calls: init-internal calls to play remain initialization, including drivers with a shared init/play address. Executed fixtures guard these phase boundaries and subtune-dependent entry state. CPU instruction-start cycles and VICE post-instruction checkpoints remain distinct observations.

Reproduce into fresh directories after [dependency setup](../../setup/local-setup.md):

```sh
python3 scripts/psid_audit.py .local/research/cybernoid-ii/Cybernoid_II.sid --profile pal-banked --subtune 1 --ticks 600 --output build/cybernoid-title-new/audit.json
python3 scripts/trace-sid-vice.py .local/research/cybernoid-ii/Cybernoid_II.sid --profile pal-banked --subtune 1 --oracle build/cybernoid-title-new/audit.writes.json --first-call 0 --last-call 599 --output build/cybernoid-title-new/vice
python3 scripts/psid_audit.py .local/research/cybernoid-ii/Cybernoid_II.sid --profile pal-banked --subtune 2 --ticks 64 --output build/cybernoid-game-over-new/audit.json
python3 scripts/trace-sid-vice.py .local/research/cybernoid-ii/Cybernoid_II.sid --profile pal-banked --subtune 2 --oracle build/cybernoid-game-over-new/audit.writes.json --first-call 0 --last-call 63 --output build/cybernoid-game-over-new/vice
```

The [title report](../../../evidence/cybernoid-title-execution/vice/study.json), [game-over report](../../../evidence/cybernoid-game-over-execution/vice/study.json) and [execution receipt](../../../evidence/cybernoid-title-execution/provenance.json) index the source/tool hashes and exact scope. Full CPU store ledgers and parsed VICE traces are retained losslessly in the [evidence manifest](../../../evidence/manifest.json); use the [archive restoration workflow](../../workflows/build-cache.md) to recover their original working paths. Original SIDs, payload dumps and reference audio are excluded.

## Executed opening sound-record reads

The [instruction tracer](../tools/sid-program-analysis.md#trace-a-selected-subtune-in-banked-ram) records 40,415 instructions and 1,107 play stores for title calls 0–63, plus 25 initialization stores. VICE independently matches the call, address, value and writer PC for all 1,107 play stores in this window. Filtering executed `LDA`/`LDX`/`LDY` operand addresses through the 18 statically matched eight-byte records finds:

| Recovered label / actual archive address | Executed loads | Byte coverage |
| --- | --- | --- |
| `bass` / `$B01C` | 215 | All eight offsets; every observed value matches the pinned record |
| `bassdrm` / `$B024` | 215 | All eight offsets; every observed value matches the pinned record |
| `arp+filt` / `$B034` | 215 | All eight offsets; every observed value matches the pinned record |

The [read receipt](../../../evidence/cybernoid-title-instructions/table-reads.json) pins both the instruction trace and static lookup, records reader PCs and states the selection rule. These are actual table loads, rather than label matches alone. The contextual lookup below additionally identifies their opening voice selections; complete synthesis semantics, bass/drum time-sharing and a listening judgment remain unproven. Preserve those distinctions when interpreting the listing.

```sh
PYTHONPATH=.tools/test-deps python3 scripts/trace-sid-program.py .local/research/cybernoid-ii/Cybernoid_II.sid --profile pal-banked --subtune 1 --first-call 0 --last-call 63 --output build/cybernoid-title-new/opening.trace.json
```

## Navigation for the complete-form probe

The [navigation receipt](../../../evidence/cybernoid-title-instructions/form-navigation.json.gz) separates executed opening observations from static branches that were not reached. These are actual archive addresses, not relocated listing addresses:

| State | Archive location / observation hook |
| --- | --- |
| Tempo reload / countdown | `$A629` / `$A682`; `$A720` decrements and `$A725` reloads 2 on calls 0, 3, …, 63 |
| Per-voice order / pattern cursors | `$A62D–$A62F` / `$A630–$A632`; `$A754` consumes order bytes |
| Per-voice row countdown / duration / repeats | `$A633–$A635` / `$A636–$A638` / `$A684–$A686` |
| Order pointers | Low/high banks `$AEFB–$AEFD` / `$AEFE–$AF00`; opening X=0/1/2 resolves to `$B0D8/$B14D/$B164` |
| Pattern pointers / scratch | Table `$AF01`, scratch `$46–$47`; `$A7A5/$A7AA` resolve and `$A7C0/$A936/$A8F6` consume bytes |
| Completed play body | `$AE2C` is the final `RTS` in all 64 observed calls |

At call 24, X=2 consumes pattern `$FF` at `$B284`, resets its pattern cursor 4→0 and decrements repeats 29→28 while retaining order cursor 3. This is a pattern repeat, not a song restart. Static code separately handles order `$FF` by resetting that voice's sequencing state, and order `$FE` by setting global play flag `$A717=1` and zeroing `$D400–$D415` while preserving `$D416–$D418`; neither order-terminal branch executes in the opening window. Do not equate an individual voice wrap with a complete-state recurrence.

The recovered listing declares 33 pattern pointers, but its title orders include `$21`. The archive's lookup at `$AF43/$AF44` yields `$B62D`: its 32 bytes through `$B64C` exactly match the commented former title `st1e` fragment at listing lines 1765–1768. A later, active game-over `st1e` at line 1809 separately matches archive index `$1E→$B6FE`; the missing title entry is `$21`. These static matches explain a concrete gap in the recovered build route. The `$21` selection is absent from the retained 64-call opening, but the 36,000-call probe executes it 24 times, first on voice 2 at call 16,416. Consult the archive's consumed bytes before treating the recovered listing as a complete build route.

The reusable probe below extends the initial 2,048-call check through two complete order traversals. The next mechanism work must connect selected records to changing synthesis state, including state retained across an order wrap. Shades remains awaiting its independent reconstruction and transfer listening verdict.


## Contextual score-command lookup

The [semantic source receipt](../../../evidence/cybernoid-form-source/semantics.json) retains pinned source/listing/trace hashes, exact archive PCs and instruction bytes, and distinguishes executed opening branches from static interpretations. It is a navigation aid for a future decoder, not an executable grammar: the same high-bit byte can mean something different when consumed as a parameter or continuation.

| Context / byte | Observed implementation or static contract | Constraint |
| --- | --- | --- |
| Order `$00–$3F` | Pattern pointer at `$AF01 + 2×byte`, loaded into `$46/$47` | Retains the current pattern cursor; opening selects patterns 1, 2 and 3 |
| Order `$40–$5F` | Additional repeats = byte & `$3F`; then advance order | A count N normally means N+1 passes; distinguish repeat decrement from order wrap |
| Order `$60–$7F` | Instrument-index offset = byte & `$0F` | Added to the later pattern sound selector |
| Order `$80–$FD` | Pitch-table offset = byte & `$1F` | Unsigned byte arithmetic; do not infer a signed transpose or MIDI key |
| Order `$FF` / `$FE` | Per-voice sequencing reset / global stop path | Static in the opening; neither resets every synthesis state |
| Pattern note `$00–$6F` after prefixes | Add pitch offset, then read frequency tables `$AE3F/$AE96` | `$00` is a pitch byte here, not an unconditional rest |
| Pattern `$70–$7F` in arpeggio context | Select arpeggio pointer, then consume pitch | Opening executes selector `$72` on voice 2; the listing defines eight choices, while the encoded range is wider |
| Pattern duration `$80–$BF`, with contextual continuations | Initial countdown = (byte & `$3F`) − 1; subsequent high-bit extension can add byte & `$7F` | Opening `$88→7`, `$A0→31`, `$A0,$A0→63`; retain the actual helper/branch sequence |
| Pattern instrument `$C0–$DF` | (byte & `$1F`) + order offset selects an eight-byte record from `$B014` | Opening voices 1/2/3 select records 1/4/2: `bass`, `arp+filt`, `bassdrm` |
| Pattern glide `$E0–$EF` | Consume packed glide control, base pitch and target pitch; add pitch offset | Opening voice 1 executes `$E0,$40,$0C,$18`; `$40` is packed control, not a 64-call delay; see the retained-pitch investigation below |
| Initial pattern `$F0–$FF` | Odd prefix consumes `$D417` routing; even prefix skips part of patch initialization after frequency update | Opening proves `$F1` routing. Even-prefix behavior is static, not a complete legato guarantee |
| Pattern end `$FF` at end-peek/helper | Reset pattern cursor; decrement repeat or advance order | Context differs from initial-prefix and order-stream `$FF`; preserve the helper's call-stack behavior |

The opening interpretation now connects sound-record reads to their selected voices, but does not establish full-title roles, bass/drum time-sharing or perceptual success. The first independent 2,048-call order probe still lies in early progression: voices 1 and 2 reach their next order entries at call 1,536; voice 3 changes from repeated pattern 3 to pattern 4 at call 1,440, then repeated pattern 5 at 1,536. Neither those events nor the initial 30-second WAV represents the complete title form.

## Reproduce and inspect the complete order cycle

The source-pinned [form observer](../../../scripts/analyze-cybernoid.py) executes the intact title through the shared `pal-banked` CPU profile. It records contextual order/pattern reads, repeat and wrap events, every ordered SID store, named sequencing state and full backing-RAM/CPU hashes at each completed play call. It records stopped and stop-clearing returns as well as ordinary returns; an unowned indirect read stays unclassified. It does not infer a musical recurrence from a pointer reset or stop early on a repeated sequencing tuple.

```sh
python3 scripts/analyze-cybernoid.py --ticks 36000 --output build/cybernoid-form-new
```

Choose a fresh output directory. The [receipt](../../../evidence/cybernoid-form-36000/receipt.json) pins source, toolchain, observation hooks, hash recipes and each output. Lossless events, call states and ordered writes are in the [manifest](../../../evidence/manifest.json); restore them through the [evidence workflow](../../workflows/build-cache.md). The [exact proof-version observer](../../../evidence/cybernoid-form-proof/analyze-cybernoid.py) retains the run's `bde6c5c…` source identity; the working script subsequently received only navigation and stop-return provenance-comment clarifications. The [independent prefix comparison](../../../evidence/cybernoid-form-36000/independent-prefix-comparison.json) matches a separately implemented narrow observer through call 16,383: all 4,171 order reads, all 294,487 initialization/play stores, final named sequencing state and CPU-cost measurements.

| Observation, calls 0–35,999 | Finding |
| --- | --- |
| Order-list boundaries | All three voices consume their order `$FF` at calls 17,280 and 34,560 |
| Duration under this PAL host | 17,280 calls / 50.12457321485099 Hz = 344.7410898828412 seconds per order traversal |
| Initialization and play | 25 initialization stores; 645,935 play stores; maximum play body 3,378 cycles, within the 19,656-cycle frame |
| Selected-pattern consumption | First and second traversals each select 4,331 pattern pointers and consume 12,406 indirect pattern bytes in identical relative-call/voice order |
| End and state | No order `$FE` global stop and no exact backing-RAM-plus-CPU recurrence in the observed 36,000 calls |

A complete **order cycle** is established; a finite source ending or identical synthesized repeat is not. The first two traversals consume the same patterns, while ordered SID address/value sequences differ in 6,792 relative calls. The first difference is relative call 13: voice 1's frequency-low write is `$E1` on the first traversal and `$D1` on the second. This shows that wrapping the order lists does not restore all pitch-producing state. The retained-pitch investigation below connects this first difference to vibrato phase with an executed state trace and a controlled intervention; it does not attribute all full-cycle differences to that mechanism. Whole-RAM hashes include stack and I/O shadows, and neither those hashes nor a register ledger represents SID oscillator/envelope state or rendered PCM.

The [full VICE report](../../../evidence/cybernoid-form-36000/vice-full/study.json) independently matches all **645,960** initialization/play stores across all **36,000** calls. Its maximum cadence deviation is five cycles against the nine-cycle polling tolerance. The [run provenance](../../../evidence/cybernoid-form-36000/vice-full/provenance.json) pins the tracer, parsed trace and deadline. Reproduce from the observer's ordered-write output:

```sh
python3 scripts/trace-sid-vice.py .local/research/cybernoid-ii/Cybernoid_II.sid --profile pal-banked --subtune 1 --oracle build/cybernoid-form-new/audit.writes.json --first-call 0 --last-call 35999 --timeout 180 --output build/cybernoid-form-new/vice
```

The default 60-second process deadline was too short for this long monitor capture; `--timeout` extends wall-clock allowance while preserving cycle limits and verification. A timed-out capture is incomplete evidence and produces no successful study. Retain the parsed VICE trace, not public monitor/process logs: successful monitor logs also contain a full source-payload dump. All originals, reference audio and such dumps remain local and ignored.

The [traversal comparison](../../../evidence/cybernoid-form-36000/traversal-comparison.json.gz) and its [reproducer](../../../evidence/cybernoid-form-proof/compare-traversals.py) preserve projections and input hashes. Raw order-read streams differ: 4,425 reads on the first traversal versus 4,428 on the second. Removing exactly the three second-traversal initial `$FF` reads, each linked to an executed voice wrap, makes the remaining streams equal. Both traversals have 310,561 play writes, with identical per-call write counts and register-address order across all 17,280 paired calls. The 10,878 differing values occur only in the six frequency registers. Instruction-start timing differs in 12,545 paired calls: 5,803 differ only in timing and 6,742 differ in both timing and values; another 50 differ only in values. These are CPU instruction-start comparisons, not SID bus-write timestamps.

After restoring the archived inputs to their indexed `build/` paths, reproduce the comparison with:

```sh
python3 build/cybernoid-form-proof/compare-traversals.py build/cybernoid-form-36000 --output build/cybernoid-form-36000/traversal-comparison-new.json
```

## Retained vibrato phase at the order wrap

The title's voice 1 keeps vibrato direction at `$A667` and position at `$A66A` when order `$FF` resets its sequencing cursors. The [compact observer](../../../evidence/cybernoid-wrap-pitch/probe.py) runs the unchanged source through call 17,300, retaining [named state and arithmetic](../../../evidence/cybernoid-wrap-pitch/observations.json.gz) in calls 0–20 and 17,280–17,300. The [oracle cross-check](../../../evidence/cybernoid-wrap-pitch/oracle-crosscheck.json) matches every one of its 736 ordered SID-store records against the corresponding full-span CPU ledger already checked by VICE. The original opening begins with direction/position `$00/0`; the first wrap preserves `$FF/1` before and after `$A75F→$A76A`.

| Executed point | Original opening | Opening after the first wrap |
| --- | --- | --- |
| First vibrato phase step, relative call 1 | Ascending position 0→1 | Descending position 1→0, then direction becomes ascending |
| Glide completes, relative call 12 | Working frequency `$08E1`; position 1 | Working frequency `$08E1`; position 0 |
| Next vibrato step, relative call 13 | Position 1→2 | Position 0→1 |
| Frequency arithmetic at `$AA62/$AA78` | Base `$08E1` − 2×`$0010` + 2×`$0010` = `$08E1` | Same base − 2×`$0010` + 1×`$0010` = `$08D1` |

The [diagnostic intervention](../../../evidence/cybernoid-wrap-pitch-intervention/run.py), with its [complete four-case results](../../../evidence/cybernoid-wrap-pitch-intervention/receipt.json.gz), seeds only these two voice-1 bytes before the first outer play call; it leaves the SID source and CPU registers unchanged. Four 21-call runs separate the control, each individual-byte change and the combined phase. The control matches every original-opening SID store. Seeding the retained pair `$FF/1` reproduces **all voice-1 ordered register writes** from calls 17,280–17,300, after subtracting the order period. Either single-byte change fails that comparison. This establishes causal sufficiency for that opening voice and window, not a reset recipe for the full song or an audible preference. The score's repeat marker should therefore preserve phase unless a deliberate arrangement change calls for restarting it.

The historical contextual-command receipt calls `$A690` `glideDelay` and records decimal 64. That is the raw `$40` parameter, not a duration in calls: the synthesis routine splits its nibbles, and the observed opening glide finishes at relative call 12. Preserve that raw evidence while using **packed glide control** in new descriptions. The [later named-state pitch component](#named-state-vibrato-and-glide-component) extends this opening explanation to general glide and modulation arithmetic; full-title contextual composition remains a separate check.

The independent [phase and centered-pitch model](../../../evidence/cybernoid-wrap-pitch/model.py) computes these two operations from editable numeric inputs. Its [verification](../../../evidence/cybernoid-wrap-pitch/model-verification.json) matches 18 recorded phase updates and the two detailed arithmetic paths. It preserves byte wrapping, asymmetric endpoints and the source's signed loop termination. The separate [isolated-routine checker](../../../evidence/cybernoid-wrap-pitch/edge-check.py) then executes `$AA20–$AA84` with 320 synthetic combinations of extent, direction, position and note age; [all results match](../../../evidence/cybernoid-wrap-pitch/edge-verification.json). This covers byte wrap, signed-loop edges and the zero-extent wait bypass without claiming those combinations occur in the score. Delta/depth selection, wait selection, glide and a complete instrument remain outside this helper.

Restore the selected evidence with [the archive workflow](../../workflows/build-cache.md). For a fresh execution, copy the exact probe/model into a fresh `build/` directory; their source paths resolve from the repository root. The intervention additionally reads the restored historical baseline at `build/cybernoid-wrap-pitch/observations.json`:

```sh
python3 scripts/evidence.py restore evidence/cybernoid-wrap-pitch/observations.json.gz
mkdir build/cybernoid-wrap-pitch-new
cp evidence/cybernoid-wrap-pitch/probe.py evidence/cybernoid-wrap-pitch/model.py evidence/cybernoid-wrap-pitch/edge-check.py build/cybernoid-wrap-pitch-new/
python3 build/cybernoid-wrap-pitch-new/probe.py
python3 build/cybernoid-wrap-pitch-new/model.py
python3 build/cybernoid-wrap-pitch-new/edge-check.py
mkdir build/cybernoid-wrap-intervention-new
cp evidence/cybernoid-wrap-pitch-intervention/run.py build/cybernoid-wrap-intervention-new/
python3 build/cybernoid-wrap-intervention-new/run.py
```

## Opening sound-record fields, shared filter and arpeggio

The [field/filter/arpeggio analysis](../../../evidence/cybernoid-filter-arp/analyze.py) reads the retained 64-call instruction trace and pinned archive. Its [lossless receipt](../../../evidence/cybernoid-filter-arp/receipt.json.gz) joins all 645 sound-record loads to the opening voice/record selections and preserves instruction indices, parameter reads and ordered sound writes. These are contextual fields, not eight independent knobs:

| Record offset / source label | Established interpretation and boundary |
| --- | --- |
| 0 / `pulsehi` | Low nibble initializes pulse high; retain the full byte for other flags. Bit `$10` has a separate end-of-row SR branch, static in this window. |
| 1 / `waveform` | Initial control byte; later onset/drum code can replace the working control. |
| 2–3 / `attdec`, `susrel` | Initial SID attack/decay and sustain/release writes at patch setup. |
| 4 / `filcount` | Low three bits select a filter pointer; high nibble shifted right twice participates in gate masking. Bit `$08` also enters a separate frequency-addition branch. |
| 5 / `fx1` | Pitch-effect control normally; low nibble instead selects a drum table when `fx3` bit `$10` is set. |
| 6 / `fx2` | Low three bits select a PWM table; upper nibble participates in PWM steps. Bit `$08` also affects remembered filter-owner fallback. |
| 7 / `fx3` | Effect flags: record 4's `$85` enables filter, tone arpeggio and onset behavior. Other flags select drum, sweep or pulse-run paths; do not infer executed coverage from a flag name alone. |

Opening voice 2 selects record 4, `arp+filt`, bytes `$04,$21,$00,$C8,$01,$00,$81,$85`. The score separately sends `$D417=$82` via `$F1`: resonance 8, only voice 2 routed through the shared filter. Record offset 4 selects filter program 1 at `$AFD6`; offset 7 enables its execution. Patch setup skips the synthesis body, so the first filter update is call 1. Calls 1–63 each write mode/volume `$3F` and cutoff high; cutoff low remains the initialization zero. Cutoff high starts `$A0`, falls by two per call through call 33, then rises by one on calls 34–63. Parameterized arithmetic matches all 126 ordered filter writes.

The remembered filter owner is voice index 1 at `$A683`. The driver processes voices 3, 2, 1, so multiple enabled voices would write the shared registers in that order; only one enabled owner is demonstrated here. The receipt separates static owner-fallback and later filter stages from the phases actually executed. Filter age is note age, not the row countdown. The [later title census](#full-title-mechanism-coverage) establishes owner changes and third/terminal stage execution; this opening receipt alone does not cover them.

Tone-arpeggio selector `$72` chooses table 2 at `$AF97`: header 2, offsets `0,5,8`. Its counter decrements before consumption, wraps through the signed test, and reads offsets in reverse order: **8,5,0**. With base pitch-table index 47, the generated indices are 55,52,47. The checker matches all 63 body updates, 21 counter wraps and 126 final voice-2 frequency stores. Later onset logic restores the base pitch on calls 5–6 while the arpeggio counter continues; the raw arpeggio calculation alone is therefore insufficient to predict the final register write. The default `$AF9B` address encoded in the self-modified instruction is not the selected opening table.

Reproduce the retained analysis without another CPU run:

```sh
python3 evidence/cybernoid-filter-arp/analyze.py --output build/cybernoid-filter-arp-new.json
```

The script needs the pinned local SID/listing and canonical instruction archive; the source URLs and hashes are in its receipt. It rejects an existing output. This analysis establishes executed programming behavior, not an independent complete instrument or listening approval.

## Opening waveform, onset and PWM programs

The opening `bass` and `bassdrm` records share neither a static waveform nor a generic pulse-width sweep. The [bounded checker](../../../evidence/cybernoid-wave-pwm/check-mechanisms.py), with its [lossless mechanism receipt](../../../evidence/cybernoid-wave-pwm/mechanisms-verified.json.gz), verifies four patch initializations, 63 bass PWM bodies, 63 bass onset bodies and 61 drum bodies against the retained instruction trace. Its program models take traced incoming buffers where upstream pitch or gate behavior is outside their scope; they are not a complete independent player.

| Program | Executed contract |
| --- | --- |
| Patch initialization | Bass call 0 and drum calls 0,24,48 initialize waveform, pulse and gate state, then go directly to the writer. They skip the synthesis macros at age 0. |
| Bass PWM | `fx2=$64` selects slot 4: lower high byte `$07`, upper `$0D`; age thresholds 3/6/9 use steps `$70/$60/$50`, then `$60` from age 10. Direction 1 adds and direction 0 subtracts with word arithmetic. Crossings reverse direction without clamping: widths `$0D40` at call 22, `$06E0` at 39 and `$0D40` at 56. |
| Bass onset | `fx3` bit `$80`, onset length 2. Age 1 replaces control with `$81` and only frequency high with `$FA`, retaining the incoming low byte (observed `$FACF`). Ages 2–3 restore control `$41` and the saved frequency; age 4 onward makes no onset override. |
| Drum | `fx3` bit `$10`, `fx1` selector 0. Ages 1–10 consume waveform `$81,$41,$40×8` and frequencies `$3400,$0A00,$0800,$0600,$0400,$0500,$0600,$0500,$0400,$0500`; waveform bit 0 selects gate mask `$FF` or `$FE`. From age 11 this macro stops changing its buffers, preserving `$40/$0500` in the observed passage. PWM selector zero leaves pulse width `$0800`. |
| Final writer | Writes `(waveform & gateMask)`, frequency low/high and pulse low/high, in that order. Earlier note-setup frequency and ADSR stores are separate and remain in the full ledger. |

PWM indexing has a carry dependency worth preserving: after masking selector 4 and shifting three times, carry is clear; `SBC #$07` therefore subtracts eight. The resulting offset 24 selects `$AFF4+24=$B00C`. A rewrite that blindly subtracts seven would read the wrong parameter bytes. The observed PWM mode reverses on threshold crossings and retains overshoot; static reset-to-lower and threshold direction-bit alternatives are excluded from this checker.

The archived drum waveform table at `$AF4D` differs from the recovered listing's `dwa0` table. Both start with length 11 and waveform `$81`, but at offset 2 the archive has `$41` while the listing has `$81`; later archive entries are `$40`, while the listing uses `$20` and `$10`. This is an executed sound-program difference, even though the eight-byte drum record matches. Preserve archive tables when reconstructing this pinned reference. The corresponding frequency-high table and the selected PWM/onset tables do match the inspected listing.

The [receipt checker](../../../evidence/cybernoid-wave-pwm/check-receipt.py) separately matches all 640 selected final-writer stores to the canonical ledger and checks that every listed contract PC executed. Its [negative controls](../../../evidence/cybernoid-wave-pwm/validation.json) detect a changed PWM threshold first at call 3 and substitution of the recovered drum waveform first at call 2. These are local arithmetic perturbations, distinct from the executed RAM intervention in the pitch study.

```sh
mkdir build/cybernoid-wave-pwm-new
cp evidence/cybernoid-wave-pwm/check-mechanisms.py evidence/cybernoid-wave-pwm/check-receipt.py build/cybernoid-wave-pwm-new/
python3 build/cybernoid-wave-pwm-new/check-mechanisms.py --output build/cybernoid-wave-pwm-new/mechanisms-verified.json
python3 build/cybernoid-wave-pwm-new/check-receipt.py
```

The next full-title model must retain ordering among pitch, PWM, filter, onset/drum and final writes. Opening checks do not cover every instrument, pulse wrap mode, relative drum pitch, owner change or later score role. They provide verified components and explicit gaps for that work, while Shades remains the active reconstruction awaiting listening.

## Reusable PWM and filter arithmetic

Use [cybernoid_programs.py](../../../scripts/cybernoid_programs.py) when editing these programs or implementing a caller that already owns note setup and macro ordering. The functions have no source-file dependency and do not replay captured register events. They validate numeric bounds and leave parameter tables unchanged.

| Function | Inputs and result | Caller responsibility |
| --- | --- | --- |
| `advance_pulse(width, direction, age, fx2, slot)` | A 16-bit accumulator, direction byte, note-age byte, FX2 byte and selected eight-byte slot; returns `(width, direction)`. Selector zero retains the state without requiring a slot. | Select the slot, initialize the voice, copy the accumulator into output buffers and apply later overrides. |
| `advance_filter(cutoff_high, age, program)` | Cutoff-high byte, note-age byte and ten-byte program; returns `(mode_volume, cutoff_high)`. | Filter enable, shared ownership, routing, fallback and actual register writes. Cutoff low is outside this operation. |

PWM retains overshoot, byte/word wrapping, stage-forced downward direction and the wrap header's low-byte reset to **one**. Filter stages follow descending table-index priority even when edited thresholds are nonmonotonic. Sorting thresholds or clamping pulse width would change the program.

The [isolated archive checker](../../../evidence/cybernoid-program-components/check.py) compares these functions with original `$AB8D–$AC53` and `$AC6E–$ACE1` execution. Its [complete receipt](../../../evidence/cybernoid-program-components/verification.json.gz) retains 2,048 PWM and 3,840 filter cases, including selector bypass, both directions, signed-looking direction bytes, boundary overshoot, word overflow, wrap headers, forced direction, every filter age byte and nonmonotonic thresholds. All 5,888 cases match; the receipt pins both implementation and verifier hashes. These synthetic caller states establish arithmetic behavior, not their occurrence in the title or complete-player/audio equivalence. The SID file is unchanged; synthetic parameters are supplied only in isolated RAM.

```sh
python3 -m unittest discover -s tests -p 'cybernoid_programs_test.py' -v
mkdir build/cybernoid-program-components-new
cp evidence/cybernoid-program-components/check.py build/cybernoid-program-components-new/
python3 build/cybernoid-program-components-new/check.py
```

The recovered listing also contains waveform-arpeggio, pulse-arpeggio and “strange filter” blocks that are absent from the actual archive between its pulse-buffer copy and drum dispatch (`$AC46–$AD44`). The archive there executes high-byte sweep, shared filter, pulse-run and packed-field frequency-addition branches. A reconstruction must follow the pinned archive, using the listing as an interpretation aid rather than importing every listed feature.

## Full-title mechanism coverage

The [executed census](../../../evidence/cybernoid-title-mechanism-coverage/probe.py) covers calls 0–17,280: the first complete title traversal and its first wrapped call. All 310,614 ordered initialization/play records match the corresponding prefix of the canonical 36,000-call ledger, including instruction-start timestamps; peak play cost is 3,297 cycles in this span. The [lossless census](../../../evidence/cybernoid-title-mechanism-coverage/coverage.json.gz) retains source-bound record fields, executed opcode pins, per-voice/record/variant counts and representative states. The [compact summary](../../../evidence/cybernoid-title-mechanism-coverage/summary.json) provides first/last calls for follow-up probes. The separate [opening cross-check](../../../evidence/cybernoid-title-mechanism-coverage/opening-crosscheck.json) matches 1,803 hook visits across 56 groups against the retained instruction trace.

| Scope | Executed evidence |
| --- | --- |
| Voice entry accounting | 51,843 entries: 4,334 patch initializers and 47,509 synthesis bodies; 1,266 explicit sound-record assignments. A retained record can initialize many notes. |
| Selected records, voice indices 0/1/2 | Voice 0: `0,1,11,15`; voice 1: `3,4,5,6,9,10,11,14`; voice 2: `2,3,7,8,12,18`. Names and eight-byte fields are in the census. |
| PWM | 37,760 selected arithmetic bodies and 9,749 selector-zero copies; 23,365 table steps and 14,395 fallback steps. Every selected body joins exactly one addition or subtraction path. |
| Shared filter | 625 initial, 13,565 additive and 2,072 terminal updates; 748 owner fallbacks. All three additive stages execute. Filter programs 0–3 and ownership changes require the full-title caller. |
| Drum | 5,848 waveform consumptions, all followed by absolute-frequency handling. No relative drum pitch executes in this traversal. |
| Pulse-run | Record 12, voice 2: 1,280 advances, one pulse-run initializer, 495 carries and 61 high wraps. Patch initialization does not imply resetting this separate state. |
| High-byte sweep | Record 9, voice 1: 608 executions, first call 1,441. |
| Pitch | 26,925 active vibrato bodies; 399 glide interpolations and 65 target completions. Records 15/18 exercise age-dependent high-delta addition late in the title. |

Counts above describe accepted-path instruction visits; looped arithmetic hooks in the full receipt can occur repeatedly within a call. The receipt separately counts distinct calls per voice/record/variant. PWM wrap-header reset, threshold-forced descent, relative drum pitch and packed-field-4 frequency addition have zero executed hooks here. Their absence in this title span is different from the listing-only code blocks that are absent from the archive itself. Synthetic component tests remain explicitly separate from title coverage.

For a fresh census, retrieve the pinned SID/listing and LFS evidence, then use a new directory:

```sh
mkdir build/cybernoid-title-mechanism-new
cp evidence/cybernoid-title-mechanism-coverage/{probe.py,summarize.py,check-opening.py} build/cybernoid-title-mechanism-new/
python3 build/cybernoid-title-mechanism-new/probe.py --ticks 17281 --output build/cybernoid-title-mechanism-new/coverage.json
python3 build/cybernoid-title-mechanism-new/summarize.py
python3 build/cybernoid-title-mechanism-new/probe.py --ticks 64 --output build/cybernoid-title-mechanism-new/smoke64.json
python3 build/cybernoid-title-mechanism-new/check-opening.py
```

This census selects the remaining synthesis contracts by actual use. It does not independently generate the title, model SID oscillator/envelope state or establish a listening verdict.

## Independent title score expansion

The [pure decoder](../../../evidence/cybernoid-score-contract/decode.py) expands the pinned order/pattern bytes into semantic rows without executing the original driver or consuming captured events as instructions. Its [contract and coverage](../../../evidence/cybernoid-score-contract/contract-final.json) and [lossless rows/action checks](../../../evidence/cybernoid-score-contract/verified-rows-final.json.gz) preserve the result. Over 36,000 calls it matches all 64,817 structural event projections and all 36,000 completed named sequencing states. It produces 8,760 semantic rows, including 4,331 in the first traversal. Separately, 7,276 executed accumulator contexts check sound, duration, arpeggio and glide-target actions; five opening pitch stores match the canonical instruction trace. Full-title base-pitch stores are not independently observed by the existing form hooks, so structural equality is not a complete synthesis proof.

Each row contains voice, generated call, pattern selection, ordered tagged commands, frequency-table pitch index, countdown reload, retained sound/arpeggio selection, patch-setup mode and source-event provenance. Pitch indices are archive table identities, not MIDI notes. Provenance locates evidence and is not an instruction stream for a future player.

| Sequencer rule | Independent contract |
| --- | --- |
| Scheduling | Decrement byte counters; their sign bit triggers reload/row consumption. Tempo reload 2 processes rows every three calls, voices 2→1→0. Observed row reloads are at most 67; their next row is `(reload + 1) × 3` calls later. |
| Parsing | Initial F prefix, glide, optional sound, duration/continuations, arpeggio, then note. Helper continuations re-enter particular stages; a range-only token lexer loses this context. |
| Glide source reads | Consecutive packed-control/base/target bytes are read in control/target/base order. Both pitches add transpose with byte wrapping. |
| Duration | Retained until changed. A first duration sets `(byte & $3F) − 1`; continuation priority includes exact `$E0` glide re-entry and high-bit extension/re-entry rules. |
| Row versus wrap | Each selected row resets glide flags, note/vibrato age and arpeggio counter. Order `$FF` resets row/order/pattern cursors and consumes order 0 immediately; it retains duration, repeat count, transpose, sound offset, sound/arpeggio selection and synthesis state. |
| End peek | After initialization the driver peeks at the next byte. `$FF` updates pattern/order state while the current row still plays its duration. Raw pitch zero remains a lookup index, not an inferred rest. |

The title contains 35 initial F prefixes, all `$F1`, and no `$FF` returned through the pattern helper. The decoder rejects even initial F prefixes and helper-`$FF` rather than claiming general support. Static code shows a nonzero even-F path can suppress patch setup, whereas a following zero falls into routing and clears that flag. The helper-`$FF` path also retains a return address while entering writer/voice traversal. These require focused fixtures before supporting edited scores that introduce them. Signed-duration edges, wider arpeggio selectors and global `$FE` stopping likewise remain outside demonstrated title coverage.

```sh
mkdir build/cybernoid-score-new
cp evidence/cybernoid-score-contract/decode.py build/cybernoid-score-new/
python3 build/cybernoid-score-new/decode.py --output build/cybernoid-score-new/rows.json --contract-output build/cybernoid-score-new/contract.json
```

This reads the local pinned SID/listing and canonical LFS event/state/instruction evidence. The [companion dependency checkpoint](../../../evidence/cybernoid-score-contract/dependency-checkpoint.json) pins the imported parser/guard implementations and their committed checkout; the historical receipt remains unchanged. It performs no CPU run or render. The score contract is ready for composition with independently verified synthesis components; complete independent title playback remains the next preparation milestone.

## Named-state vibrato and glide component

The source-independent [pitch model](../../../evidence/cybernoid-pitch-contract/model.py) advances named buffers for archive `$A9C1–$AB8C`; drum dispatch enters at `$AA97` and bypasses vibrato. Its [typed contract and source-address map](../../../evidence/cybernoid-pitch-contract/contract.json.gz) separates persistent voice state, record parameters and caller-supplied frequency-table words/timing. `advance_pitch` returns updated state and diagnostics for vibrato and disabled/waiting/interpolating/completed glide. The caller still owns scheduling, initial note setup, tone arpeggio and later output overrides.

| Operation | Retained byte-level behavior |
| --- | --- |
| Vibrato delta | Adjacent-minus-effective table difference, low-nibble shift and high-bit age growth. Age growth adds to the high byte with carry retained from the subtraction; it is not an ordinary linear scaling of the whole word. |
| Vibrato phase/wait | Preserve signed direction/position branches and the conditional centered-pitch wait established by the earlier wrap proof. Active glide suppresses vibrato. |
| Glide timing | Split packed control into length and offset; byte-wrapped row timing decides waiting, interpolation or target completion. Keep current and held frequency as distinct buffers. |
| Glide divisor | Repeated byte addition retains carry between iterations and uses signed `DEY` termination; `(length × (speed + 1)) mod 256` is not general enough. |
| Glide division/rounding | The routine divides the low 15 magnitude bits, retains bit 15 in the result and compares doubled remainder modulo 256. Conventional rounded 16-bit division gives different results for supported synthetic edge inputs. |

The [isolated checker](../../../evidence/cybernoid-pitch-contract/check.py) and [complete verification](../../../evidence/cybernoid-pitch-contract/verification.json.gz) match 512 component cases, 154 division cases and 40 divisor cases. Component cases exercise all three voice indices and verify untouched other-voice state; no SID store is permitted in this block. Source bytes, static frequency/wait tables and the original SID file remain unchanged. The earlier 320-case phase/centered-pitch proof complements these checks. This is synthetic caller-state verification; the linked title census establishes which branches occur in the song, not per-body equality of this model across the title.

The initial synthetic generator correlated control selection with active-glide state, so its `$10/$53/$F0/$FF` settings bypassed vibrato and did not enter centered subtraction. Preserve that receipt's actual scope. The [extended checker](../../../evidence/cybernoid-pitch-extended/check.py) breaks this correlation and guards the complete control × active-glide matrix, ordinary `$53` centered subtraction and its wait bypass using the archive's record-1 wait. These guards fail on the original generator. The [extended receipt](../../../evidence/cybernoid-pitch-extended/verification.json.gz) matches another 512 component cases, 154 divider cases and 40 divisor cases with the unchanged model. This makes branch coverage an executable requirement instead of inferring it from a large case count.

```sh
mkdir build/cybernoid-pitch-new
cp evidence/cybernoid-pitch-contract/{model.py,check.py,describe.py} build/cybernoid-pitch-new/
python3 build/cybernoid-pitch-new/check.py
python3 scripts/evidence.py restore evidence/cybernoid-title-mechanism-coverage/coverage.json.gz
python3 build/cybernoid-pitch-new/describe.py
mkdir build/cybernoid-pitch-extended-new
cp evidence/cybernoid-pitch-extended/{model.py,check.py} build/cybernoid-pitch-extended-new/
python3 build/cybernoid-pitch-extended-new/check.py
```

The description step joins the fresh verification to the restored historical census; its 143 selected-title pitch summaries retain exact provenance. The following contextual proof extends this isolated evidence. Later onset, drum and sweep behavior can change pitch after this block, so its buffer equality alone cannot establish final register or audio equivalence.

## Full-title contextual pitch verification

The [context probe](../../../evidence/cybernoid-pitch-context/probe.py) observes each eligible pitch-block entry during intact source execution, supplies its named state and lookup words to the unchanged independent model, and compares the complete result before `$AB8D`. All **47,509 bodies** in calls 0–17,280 match: 15,682 / 16,595 / 15,232 for voice indices 0 / 1 / 2. This includes 26,925 active vibrato bodies, 399 glide interpolations, 65 completions and 124 waiting bodies. The [receipt](../../../evidence/cybernoid-pitch-context/receipt.json) pins source, model, tools, variants and coverage; the [lossless per-body ledger](../../../evidence/cybernoid-pitch-context/bodies.jsonl.gz) retains input state, parameters, lookup words, predicted output, observed delta and instruction-cycle boundaries. Equality is asserted before a successful row is recorded.

The same execution matches every one of the 310,614 ordered initialization/play records against the canonical 36,000-call prefix, with no field, timing or value normalization. This verifies a component in actual caller context. The caller state and frequency-table words are observed inputs; the probe does not independently compute the surrounding score/arpeggio/init/output machinery or establish final synthesized audio equivalence.

```sh
python3 scripts/evidence.py restore evidence/cybernoid-title-mechanism-coverage/coverage.json.gz
mkdir build/cybernoid-pitch-context-new
cp evidence/cybernoid-pitch-context/probe.py build/cybernoid-pitch-context-new/
python3 build/cybernoid-pitch-context-new/probe.py
```

Completion guards must distinguish play calls from eligible macro bodies. Call 17,280 initializes all three notes and skips these macros; the last eligible pitch body is call 17,279. The retained [guard reproducer](../../../evidence/cybernoid-pitch-context/guard-reproducer.py) and [result](../../../evidence/cybernoid-pitch-context/guard-reproducer.json) derive this from the census. An [earlier observer](../../../evidence/cybernoid-pitch-context/probe.failed-final-body-guard.py) incorrectly required a body on the final call; its [failure receipt](../../../evidence/cybernoid-pitch-context/failed-final-body-guard.json) makes no write-prefix claim. The corrected successful run checks full audit length, no pending entries and expected per-voice body counts. Both runs produced byte-identical body ledgers, so only one canonical ledger is retained.

## Arpeggio, waveform and output components

The [editable output model](../../../evidence/cybernoid-output-contract/model.py) separates arpeggio, high-byte sweep, pulse-run, onset/drum dispatch and the final five-store writer. Its [isolated checker](../../../evidence/cybernoid-output-contract/check.py) executes the corresponding original routines with explicit synthetic caller state and table RAM replacements; [all 3,540 cases match](../../../evidence/cybernoid-output-contract/verification.json.gz) across all three voices. The model receives numeric parameters and has no original-source dependency.

| Helper | Contract needed by the caller |
| --- | --- |
| `advance_arpeggio` | Decrement the counter with byte wrapping, reload on its sign bit, consume the reverse table offset and add it to the base pitch index modulo 256. Return counter, current pitch index and lookup word; saved frequency is unchanged. |
| `sweep_high_byte` | Decrement the saved frequency high byte and copy it to output high, retaining both low bytes. Its `base_frequency` argument means the saved buffer at `$A64B/$A645`, not the note-table word. |
| `advance_pulse_run` | Maintain a separate initialization flag and low/high accumulator. Inactivity sets the flag; the next active body takes high from the PWM accumulator, resets low, then adds `$63`. A carry increments high; high 15 changes to 7. Only pulse output is overridden. |
| `apply_wave_program` | Drum dispatch takes precedence over onset, including after its age window expires. Onset can replace waveform/high pitch, restore base waveform and saved frequency, or expire. Its restore limit is `(length + 2) & 255`. |
| `apply_drum` | Consume waveform at age and frequency parameter at `(age − 1) & 255`; set gate mask from waveform bit 0. Relative pitch adds to the current pitch index without changing that index. Expiration preserves buffers. |
| `voice_writes` | Emit control `(wave & mask)`, frequency low/high, then pulse low/high. Earlier setup/ADSR and shared-filter stores are separate. |

The [opening checker](../../../evidence/cybernoid-output-contract/check-opening.py) makes no new CPU run. Its [accurate-input receipt](../../../evidence/cybernoid-output-contract/opening-verification-accurate-inputs.json.gz) matches 63 arpeggio bodies, 124 waveform bodies and 640 final-writer stores using retained incoming state and canonical instruction evidence. The 640 stores cover the waveform card's voice indices 0 and 2, not all three opening voices. Synthetic relative-drum, age-zero-drum and unusual counter/length cases do not establish their use in this title; real note initialization skips macro age zero.

Preserve this order when composing the caller: tone arpeggio → vibrato/glide → PWM → high-byte sweep → shared filter → pulse-run output override → packed-field frequency addition → drum/onset → final writer. Eligibility, initialization, gate state, shared-filter ownership and voice order 2→1→0 remain caller responsibilities. The packed-field frequency-addition path is outside these helpers and has no executed title cases in the census.

```sh
python3 scripts/evidence.py restore evidence/cybernoid-title-mechanism-coverage/coverage.json.gz
mkdir build/cybernoid-output-new
cp evidence/cybernoid-output-contract/{model.py,check.py,check-opening.py} build/cybernoid-output-new/
python3 build/cybernoid-output-new/check.py
python3 build/cybernoid-output-new/check-opening.py
```

These checks establish bounded component behavior. Joining observed incoming buffers is not yet a complete independently computed song or a listening verdict.

## Note setup, gate and filter-owner caller

The [caller primitives](../../../evidence/cybernoid-initialization-contract/model.py) preserve the state transitions that connect score rows to sound macros. Their [checker](../../../evidence/cybernoid-initialization-contract/check.py) and [204-case receipt](../../../evidence/cybernoid-initialization-contract/verification-final.json.gz) compare 26 named fields and exact ordered setup/fallback stores against short original-routine execution: three row resets, nine age increments, 48 note/patch setups, 96 gate/release/body preludes and 48 filter-owner decisions.

| Caller step | State and ordering |
| --- | --- |
| Every voice call | Increment note age modulo 256 before score dispatch. A newly selected row then resets note age, vibrato age and glide flags before commands can enable glide again. |
| Selected note | Reload row countdown, clear arpeggio counter, set base pitch and saved/output frequency. Write SID frequency **high before low**; optional patch initialization then writes AD/SR and sets waveform, pulse, PWM direction and packed filter fields. |
| Finish selected row | After score-owned peek/end processing, force gate mask `$FF` and go straight to the writer. Skip all synthesis macros. |
| Retained state | Note/patch setup retains effective pitch, vibrato direction/position, filter cutoff and pulse-run state. The next body prelude copies base pitch into effective pitch before tone arpeggio. |
| Gate on an existing row | Scheduled bodies recompute gate mask from remaining countdown versus `(current record field 4 & $F0) >> 2`; nonscheduled bodies retain it. Remaining at or below the threshold clears gate. Macros can continue and later drum handling can change the mask. |
| Shared filter ownership | An enabled filter claims ownership before running its program. Otherwise a matching remembered owner with FX2 bit `$08` clear writes `$D418=$1F`, then `$D416=$80`. It retains ownership, routing and cutoff low, so fallback can recur. |

The raw retained pulse flag `$10` has a special `$SR=$02` branch when remaining count is zero and tempo countdown is one. No selected title record carries that flag and the census contains no execution of that branch. It is synthetic coverage, as are patch-preservation flag cases and FX2-bit-`$08` fallback inhibition; this does not lift the score decoder's restriction on even-F grammar. Global PSID initialization, complete caller/score composition and full-title equality of these primitives remain separate work.

```sh
mkdir build/cybernoid-initialization-new
cp evidence/cybernoid-initialization-contract/{model.py,check.py} build/cybernoid-initialization-new/
python3 build/cybernoid-initialization-new/check.py --output build/cybernoid-initialization-new/verification.json
```

For integration, call `begin_voice_call` before score dispatch. On a selected row use `begin_row` → score commands → `initialize_note` → score peek/end → `finish_row` → writer. Otherwise use `body_prelude` → ordered macros → writer. The score decoder still owns scheduling and countdown decrement; each component's checks retain their own scope until the composed model is compared from initialization through the full title.
