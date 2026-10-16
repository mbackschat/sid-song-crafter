# Pop songs and TV/film themes: pinned intake

This owns intake and retained preparation for the four later references in the [study plan](../../../PLAN.md). [Take On Me](take-on-me-preparation.md#familiar-transfer-and-case-closure) and [Billie Jean](billie-jean-preparation.md#listening-verdicts-and-case-closure) are complete for their accepted reconstructions, authored endings and familiar transfers. [Airwolf](airwolf-preparation.md#listening-verdicts-and-case-closure) is complete for its accepted phrase, corrected source continuation and familiar transfer. Ghostbusters is active. Source attribution and historical evidence below retain their original bounded scope.

## Sources and attribution

The [download registry](../../../config/local-assets.json) owns each original URL, SHA-256 and ignored cache destination. The [intake provenance](../../../evidence/pop-theme-intake/provenance.json) verifies the originals against those pins and retains exact entry fingerprints and line ranges from cached [HVSC STIL](https://hvsc.c64.org/download/C64Music/DOCUMENTS/STIL.txt) v85, June 28, 2026. Original SID files and their audio stay local; no executable payload or raw VICE dump is archived.

| Study / registered ID | Pinned archive and header credit | Source-song attribution from STIL | Selected scope |
| --- | --- | --- | --- |
| Take On Me / `take-on-me` | [PVL archive](https://www.hvsc.de/download/C64Music/MUSICIANS/P/PVL/Take_on_Me.sid); Pascal van Loosbroek (PVL), 1993 Slash Design; [header](../../../evidence/pop-theme-intake/take-on-me.header.json) | A-Ha, *Take On Me*, from *Hunting High and Low* | Single/default #1; [768-call introduction and 4,096-call loop](take-on-me-preparation.md#complete-score-form-and-editable-scheduler) |
| Billie Jean / `billie-jean` | [Bjerregaard archive](https://www.hvsc.de/download/C64Music/MUSICIANS/B/Bjerregaard_Johannes/Billie_Jean.sid); Johannes Bjerregaard, 1990; [header](../../../evidence/pop-theme-intake/billie-jean.header.json) | Michael Jackson, *Billie Jean*, from *Thriller* | Single/default #1; [7,104-call score cycle](billie-jean-preparation.md#complete-score-cycle-and-bounded-recurrence) |
| Airwolf / `airwolf` | [Cooksey archive](https://www.hvsc.de/download/C64Music/MUSICIANS/C/Cooksey_Mark/Airwolf.sid); Mark Cooksey, 1985 Elite; [header](../../../evidence/pop-theme-intake/airwolf.header.json) | Sylvester Levay, *Airwolf Theme*, from the TV series | Single/default #1; [138-row, 1,242-call score cycle](#airwolf-score-cycle-and-independent-numeric-model) |
| Ghostbusters / `ghostbusters` | [Lieblich archive](https://www.hvsc.de/download/C64Music/MUSICIANS/L/Lieblich_Russell/Ghostbusters.sid); Russell Lieblich, 1984 Activision; [header](../../../evidence/pop-theme-intake/ghostbusters.header.json) | #1: Ray Parker, Jr., *Ghostbusters*, from the film; all speech credited to Electronic Speech Systems | Default/selected #1 of five; #2–#5 have no labels in this cached STIL entry |

STIL's artist/original-song fields do not transfer SID-arrangement credit to the original performer. Conversely, archive header authorship does not establish original composition of the covered song. Airwolf is a TV theme; Ghostbusters combines music and separately credited speech, whose implementation remains unexamined.

## Declared execution contracts

All four use a 124-byte version-2 header with embedded load address. The table gives payload end addresses exclusively; these are declarations and extents, not measured song durations.

| Reference | Bytes / payload extent | Init / play | Declared clock/model | Admission |
| --- | --- | --- | --- | --- |
| Take On Me | 2,948 / `$1000–$1B06` | `$1B00` / `$1003` | PAL; SID model unspecified; flags `$0004`; VBI speed word zero | Unassumed audit rejects unknown model; explicit 6581/8580 experiments verified below |
| Billie Jean | 3,883 / `$1000–$1EAD` | `$14A0` / `$1000` | PAL / 6581; flags `$0014`; VBI speed word zero | `pal-banked`, explicit #1, default host `$C000` |
| Airwolf | 1,280 / `$3ADD–$3F5F` | `$3B25` / `$3ADD` | PAL / 6581; flags `$0014`; VBI speed word zero | `pal-banked`, explicit #1, default host `$C000` |
| Ghostbusters | 6,310 / `$900D–$A835` | `$900D` / `$0000` | NTSC / 6581; RSID, flags `$0018` | Requires machine-controlled RSID execution; callable PAL audit rejects the format |

### Take On Me

The [owning Take On Me study](take-on-me-preparation.md) now carries the explicit chip-model experiments, no-difference listening verdict, chosen MOS8580 working target and accepted independent reconstruction, authored ending and familiar transfer. The unchanged source header remains unknown-model; the existing 64-call CPU/VICE checks do not synthesize the chip or establish musical quality. Use its linked recipe to recreate the frozen original-source comparison.

### Billie Jean and Airwolf

On 2026-10-13 both complete initialization and calls 0–63 under the [controlled banked host](../../validation/psid-audit.md). Independent headless VICE matches every store in phase, call, address, value and order. Source hashes remain unchanged, and exported private payloads equal the originals with their load prefixes.

| Observation | Billie Jean | Airwolf |
| --- | --- | --- |
| Init cycles / SID stores | 203 / 3 | 327 / 21 |
| Play stores | 1,268 | 282 |
| Maximum play cycles / 19,656 budget | 1,241 | 306 |
| Mean play cycles | 880.625 | 105.609375 |
| VICE matched init + play stores | 1,271 | 303 |
| Maximum observed cadence error / nine-cycle tolerance | 8 | 7 |
| CPU report and complete ordered ledger | [Report](../../../evidence/pop-theme-intake/billie-jean.audit64.json), [ledger](../../../evidence/pop-theme-intake/billie-jean.audit64.writes.json.gz) | [Report](../../../evidence/pop-theme-intake/airwolf.audit64.json), [ledger](../../../evidence/pop-theme-intake/airwolf.audit64.writes.json.gz) |
| VICE report and parsed trace | [Report](../../../evidence/pop-theme-intake/billie-jean.vice64/study.json), [trace](../../../evidence/pop-theme-intake/billie-jean.vice64/trace.json.gz) | [Report](../../../evidence/pop-theme-intake/airwolf.vice64/study.json), [trace](../../../evidence/pop-theme-intake/airwolf.vice64/trace.json.gz) |

These 64-call costs do not establish whole-song maxima or form. Monitor checkpoints are not exact SID bus-write timestamps; the controlled raster caller is not the original release's environment. Airwolf's later complete-cycle evidence follows below; [Billie Jean's owning study](billie-jean-preparation.md) retains its full score cycle, independent numeric expansion and selected VICE wrap proof. Sound-program interpretation and independent arrangement remain separate milestones.

### Airwolf score cycle and independent numeric model

The [decoded score](../../../evidence/airwolf-form/complete/score.json) contains **138 rows**, each with duration byte 8. The driver decrements its countdown before testing `$FF`, so duration+1 is **nine callable updates** and the score cycle is **1,242 calls**. Initialization consumes the first row; zero-based play calls **1241 and 2483** consume the terminal zero duration and re-enter init `$3B25` and play `$3ADD` within the same host call. This is a repeating score, without a selected musical ending. A zero frequency-high field holds that voice and consumes no low byte; it performs no voice writes and does not establish silence.

Each update first writes `$D418=$0F`, `$D403=$28` and `$D40A=$0A`. A pitched entry then writes attack/decay, zero sustain/release, control zero, control `$41` for voices 1/2 or `$11` for voice 3, and frequency high then low. At a restart the fixed writes occur again before row zero. The independent [numeric model](../../../evidence/airwolf-form/model.py) computes this order from editable durations and frequency words, without original CPU code or captured-event replay; source addresses only label its modeled reads.

The [complete receipt](../../../evidence/airwolf-form/complete/receipt.json) proves **2,500 calls, 11,253 init/play stores and 1,738 consumed fields**, matching the [ordered ledger](../../../evidence/airwolf-form/complete/writes.json.gz) and [read observations](../../../evidence/airwolf-form/complete/reads.json.gz), including the retained 64-call opening. [Private source-copy interventions](../../../evidence/airwolf-form/edits.json.gz) separately change the first frequency low byte and duration; both match the model's changed stores while preserving the original. Equal [return-state hashes](../../../evidence/airwolf-form/complete/states.json.gz) at the two restarts cover all backing RAM plus A/X/Y/SP/P/PC, excluding absolute cycle counts. They do not establish physical SID/CIA/VIC state, full-machine recurrence or repeating audio.

The [VICE wrap proof](../../../evidence/airwolf-form/vice-wrap-fixed/trace/study.json), with [provenance](../../../evidence/airwolf-form/vice-wrap-fixed/provenance.json), matches **69 stores: 21 init and 48 play** across calls 1238–1246, with maximum cadence error seven cycles against nine allowed. The reusable [host-call marker](../../validation/psid-audit.md#distinguish-host-calls-from-internal-entry-jumps) counts the harness JSR rather than driver-internal init/play visits, preserving the wrap's stores under call 1241. Monitor checkpoints remain distinct from exact bus timing; original-game cadence and audible recurrence remain unproved.

Copy the retained tools into a fresh one-level directory below `build/` so their repository-relative paths and local imports remain valid. Their original-source and CPU-tool pins remain enforced; obtain the pinned asset using the intake commands below.

```sh
mkdir build/airwolf-new
cp evidence/airwolf-form/model.py evidence/airwolf-form/probe.py evidence/airwolf-form/check-edits.py build/airwolf-new/
PYTHONPATH=.tools/test-deps python3 build/airwolf-new/probe.py --output build/airwolf-new/complete
PYTHONPATH=.tools/test-deps python3 build/airwolf-new/check-edits.py --output build/airwolf-new/edits.json
python3 scripts/trace-sid-vice.py .local/research/airwolf/Airwolf.sid --profile pal-banked --subtune 1 --oracle evidence/airwolf-form/vice-wrap/oracle.json --first-call 1238 --last-call 1246 --output build/airwolf-new/vice-wrap
```

The probe generates the score needed by the edit checker. This historical research model is not itself a compiled arrangement/export. The [independent delivery study](airwolf-preparation.md) now owns the runtime player, complete export/ending checks and familiar transfer, with phrase, corrected source continuation and familiar transfer accepted. Prefer its current retained-proof recipe when rechecking unchanged evidence; the historical capture tools above keep their original pins.

### Ghostbusters

This exact file is **RSID**, not a callable PSID. Its zero play address and reserved zero speed word do not declare PAL VBI playback. Use its NTSC machine-controlled environment to identify actual interrupts, update cadence, SID/speech writes and required machine state before applying an execution oracle. Existing fixed-PAL or Shades-specific CIA tools are not evidence of support for this file. The source remains intact. The [owning Ghostbusters study](ghostbusters-preparation.md#bounded-initialized-render) now retains a bounded initialized NTSC render; separate machine instruction/store capture, speech decoding and full form remain open.

## Reproduce the intake

Acquire or verify the originals using the pinned downloader:

```sh
python3 scripts/setup-project.py --only references --include take-on-me --include billie-jean --include airwolf --include ghostbusters
python3 scripts/setup-project.py --check --only references --include take-on-me --include billie-jean --include airwolf --include ghostbusters
```

Use [sid_intake.py](../../../scripts/sid_intake.py) with each registry path and `--subtune 1` for fresh metadata; it performs no CPU execution. Reproduce the two supported comparisons in fresh output directories:

```sh
PYTHONPATH=.tools/test-deps python3 scripts/psid_audit.py .local/research/billie-jean/Billie_Jean.sid --profile pal-banked --subtune 1 --ticks 64 --output build/pop-theme-new/billie-jean.audit64.json
python3 scripts/trace-sid-vice.py .local/research/billie-jean/Billie_Jean.sid --profile pal-banked --subtune 1 --oracle build/pop-theme-new/billie-jean.audit64.writes.json --first-call 0 --last-call 63 --output build/pop-theme-new/billie-jean.vice64
PYTHONPATH=.tools/test-deps python3 scripts/psid_audit.py .local/research/airwolf/Airwolf.sid --profile pal-banked --subtune 1 --ticks 64 --output build/pop-theme-new/airwolf.audit64.json
python3 scripts/trace-sid-vice.py .local/research/airwolf/Airwolf.sid --profile pal-banked --subtune 1 --oracle build/pop-theme-new/airwolf.audit64.writes.json --first-call 0 --last-call 63 --output build/pop-theme-new/airwolf.vice64
```

The retained [collector](../../../evidence/pop-theme-intake/intake.py) checks existing receipts, STIL entry fingerprints and source/export equality without rerunning the CPU. Its evidence dependencies are restored with the [archive workflow](../../workflows/build-cache.md). Airwolf’s [independent export and familiar transfer](airwolf-preparation.md) are accepted for the phrase, corrected source continuation and familiar transfer. Ghostbusters still needs complete-form analysis in its machine-controlled environment. Take On Me and Billie Jean have completed their declared delivery scopes in their linked owning studies.
