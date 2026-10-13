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

## Reproduce intake

The download registry retains the URL/fingerprint; the original stays in ignored local storage:

```sh
python3 scripts/setup-project.py --only references --include deflektor
python3 scripts/sid_intake.py .local/research/deflektor/Deflektor.sid --subtune 1 --host-base 0x0400 --output build/deflektor-host-new/header.json
PYTHONPATH=.tools/test-deps python3 scripts/psid_audit.py .local/research/deflektor/Deflektor.sid --profile pal-banked --subtune 1 --host-base 0x0400 --ticks 64 --output build/deflektor-host-new/audit64.json
python3 scripts/trace-sid-vice.py .local/research/deflektor/Deflektor.sid --profile pal-banked --subtune 1 --host-base 0x0400 --oracle build/deflektor-host-new/audit64.writes.json --first-call 0 --last-call 63 --output build/deflektor-host-new/vice64
```

Choose fresh output paths. [sid_intake.py](../../../scripts/sid_intake.py) reports PSID/RSID v2 declarations and selected-host admission separately; it performs no CPU execution. The following two commands execute the original under their declared controlled environments. To inspect instructions later, pass the same host selection to the [instruction tracer](../tools/sid-program-analysis.md#trace-a-selected-subtune-in-banked-ram). Reference WAVs remain local; no render or listening assessment has been made here.

Next map the complete form and locate the recurring cowbell in context before choosing an intervention. Preserve its pitch/noise trajectory, articulation, shared-filter state and any voice dependencies. The study still needs independently computed sound, a complete declared arrangement and ending, listening, and an original transfer phrase.
