# Pop songs and TV/film themes: pinned intake

This prepares the four later references in the [study plan](../study-plan.md) while Shades remains the active reconstruction. It establishes exact downloads, archive declarations and scoped attribution. Billie Jean and Airwolf also have bounded CPU/VICE comparisons. None has a decoded complete form, independent arrangement, rendered comparison or listening verdict yet.

## Sources and attribution

The [download registry](../../../config/local-assets.json) owns each original URL, SHA-256 and ignored cache destination. The [intake provenance](../../../evidence/pop-theme-intake/provenance.json) verifies the originals against those pins and retains exact entry fingerprints and line ranges from cached [HVSC STIL](https://hvsc.c64.org/download/C64Music/DOCUMENTS/STIL.txt) v85, June 28, 2026. Original SID files and their audio stay local; no executable payload or raw VICE dump is archived.

| Study / registered ID | Pinned archive and header credit | Source-song attribution from STIL | Selected scope |
| --- | --- | --- | --- |
| Take On Me / `take-on-me` | [PVL archive](https://www.hvsc.de/download/C64Music/MUSICIANS/P/PVL/Take_on_Me.sid); Pascal van Loosbroek (PVL), 1993 Slash Design; [header](../../../evidence/pop-theme-intake/take-on-me.header.json) | A-Ha, *Take On Me*, from *Hunting High and Low* | Single/default #1; musical form unmeasured |
| Billie Jean / `billie-jean` | [Bjerregaard archive](https://www.hvsc.de/download/C64Music/MUSICIANS/B/Bjerregaard_Johannes/Billie_Jean.sid); Johannes Bjerregaard, 1990; [header](../../../evidence/pop-theme-intake/billie-jean.header.json) | Michael Jackson, *Billie Jean*, from *Thriller* | Single/default #1; musical form unmeasured |
| Airwolf / `airwolf` | [Cooksey archive](https://www.hvsc.de/download/C64Music/MUSICIANS/C/Cooksey_Mark/Airwolf.sid); Mark Cooksey, 1985 Elite; [header](../../../evidence/pop-theme-intake/airwolf.header.json) | Sylvester Levay, *Airwolf Theme*, from the TV series | Single/default #1; musical form unmeasured |
| Ghostbusters / `ghostbusters` | [Lieblich archive](https://www.hvsc.de/download/C64Music/MUSICIANS/L/Lieblich_Russell/Ghostbusters.sid); Russell Lieblich, 1984 Activision; [header](../../../evidence/pop-theme-intake/ghostbusters.header.json) | #1: Ray Parker, Jr., *Ghostbusters*, from the film; all speech credited to Electronic Speech Systems | Default/selected #1 of five; #2–#5 have no labels in this cached STIL entry |

STIL's artist/original-song fields do not transfer SID-arrangement credit to the original performer. Conversely, archive header authorship does not establish original composition of the covered song. Airwolf is a TV theme; Ghostbusters combines music and separately credited speech, whose implementation remains unexamined.

## Declared execution contracts

All four use a 124-byte version-2 header with embedded load address. The table gives payload end addresses exclusively; these are declarations and extents, not measured song durations.

| Reference | Bytes / payload extent | Init / play | Declared clock/model | Admission |
| --- | --- | --- | --- | --- |
| Take On Me | 2,948 / `$1000–$1B06` | `$1B00` / `$1003` | PAL; SID model unspecified; flags `$0004`; VBI speed word zero | Callable audit rejects unspecified model; no execution attempted |
| Billie Jean | 3,883 / `$1000–$1EAD` | `$14A0` / `$1000` | PAL / 6581; flags `$0014`; VBI speed word zero | `pal-banked`, explicit #1, default host `$C000` |
| Airwolf | 1,280 / `$3ADD–$3F5F` | `$3B25` / `$3ADD` | PAL / 6581; flags `$0014`; VBI speed word zero | `pal-banked`, explicit #1, default host `$C000` |
| Ghostbusters | 6,310 / `$900D–$A835` | `$900D` / `$0000` | NTSC / 6581; RSID, flags `$0018` | Requires machine-controlled RSID execution; callable PAL audit rejects the format |

### Take On Me

The source has PAL timing but no declared chip model. Keep that uncertainty in the original header and every reference record. A future model selection must be an explicit experiment assumption, distinct from archive metadata, with model comparisons where they matter audibly. Patching the header or silently inheriting the 6581 target from another study would erase that distinction. No source or playback quality judgment follows from this intake.

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

These bounded costs do not establish whole-song maxima or form. Monitor checkpoints are not exact SID bus-write timestamps; the controlled raster caller is not the original release's environment. Next identify executed order/pattern consumption and complete section coverage before attributing an instrument or implementing an independent arrangement.

### Ghostbusters

This exact file is **RSID**, not a callable PSID. Its zero play address and reserved zero speed word do not declare PAL VBI playback. Use its NTSC machine-controlled environment to identify actual interrupts, update cadence, SID/speech writes and required machine state before applying an execution oracle. Existing fixed-PAL or Shades-specific CIA tools are not evidence of support for this file. The source remains intact, and no execution, speech decoding or rendering is claimed.

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

The retained [collector](../../../evidence/pop-theme-intake/intake.py) checks existing receipts, STIL entry fingerprints and source/export equality without rerunning the CPU. Its evidence dependencies are restored with the [archive workflow](../../workflows/build-cache.md). Complete form, decoded mechanisms, independent output, musical ending, listening and transfer remain required for every case.
