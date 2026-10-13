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

The [independent score expander](../../../evidence/deflektor-form/check-score.py) reads the exact retained numeric order/pattern/mapping tables, not captured events or SID stores as playback input. Its [comparison receipt](../../../evidence/deflektor-form/score-verification.json) matches all **5,100 source reads, 87 pattern selections, 1,905 row starts/durations, 1,820 note lookup indices and 663 mapped instrument selections**. Editing a consumed duration breaks equality. Transpose/repeat order commands are executed; pattern effect tokens `$90–$95` retain their observed consumption but remain unnamed synthesis effects. Other statically mapped command branches and zero-duration scheduling lack separate executed validation. This is a pinned title grammar, not a general Daglish format specification.

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

Dependency mismatches fail explicitly rather than silently substituting a different observer environment. The form and ending proofs cover the selected driver under this controlled host; original-game execution, independently synthesized instruments, audio and listening remain separate work.

## Reusable score expansion

The supported [score module](../../../scripts/deflektor_score.py) exposes `expand_score(tables, *, calls)` using the numeric schema in the [retained tables](../../../evidence/deflektor-form/full40000/tables.json). It reads no files, original SID, CPU or observed-event ledger at runtime; input tables remain unchanged and returned instrument fields are copied. The exclusive call cap is separate from `firstStopCall`: 8,480 calls exclude the stop, while 8,481 include the stop at index 8,480. Editable notes, transposes, durations and pattern/order data drive expansion; opaque effects remain numeric commands. Zero durations reject explicitly because that edge lacks source verification.

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

## Reproduce intake

The download registry retains the URL/fingerprint; the original stays in ignored local storage:

```sh
python3 scripts/setup-project.py --only references --include deflektor
python3 scripts/sid_intake.py .local/research/deflektor/Deflektor.sid --subtune 1 --host-base 0x0400 --output build/deflektor-host-new/header.json
PYTHONPATH=.tools/test-deps python3 scripts/psid_audit.py .local/research/deflektor/Deflektor.sid --profile pal-banked --subtune 1 --host-base 0x0400 --ticks 64 --output build/deflektor-host-new/audit64.json
python3 scripts/trace-sid-vice.py .local/research/deflektor/Deflektor.sid --profile pal-banked --subtune 1 --host-base 0x0400 --oracle build/deflektor-host-new/audit64.writes.json --first-call 0 --last-call 63 --output build/deflektor-host-new/vice64
```

Choose fresh output paths. [sid_intake.py](../../../scripts/sid_intake.py) reports PSID/RSID v2 declarations and selected-host admission separately; it performs no CPU execution. The following two commands execute the original under their declared controlled environments. To inspect instructions later, pass the same host selection to the [instruction tracer](../tools/sid-program-analysis.md#trace-a-selected-subtune-in-banked-ram). Reference WAVs remain local; no render or listening assessment has been made here.

Next locate the recurring cowbell in the executed form before choosing an intervention. Preserve its pitch/noise trajectory, articulation, shared-filter state and any voice dependencies. The study still needs independently computed sound, a complete declared arrangement and acoustic ending, listening, and an original transfer phrase.
