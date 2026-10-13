# Monty on the Run: bounded archive intake

This prepares Rob Hubbard's **Monty on the Run**, selected subtune **1**, while [Shades](shades-preparation.md) remains the active reconstruction awaiting listening. It establishes the intact reference, cached attribution, declared timing and 64 guarded CPU calls. Complete form, instruments, original-host behavior and listening remain unresolved. Start with the [Hubbard composer study](../composers/hubbard-galway.md#hubbard-composing-with-a-changing-synthesis-engine), [listening catalogue](../composers/listening-catalogue.md) and [source-study boundary](../tools/source-studies.md) before extending this intake.

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
| [Anthony McSweeney's 1993 Monty routine](https://www.neperos.com/article/rxmd9gd536b13923) | Already inspected in the composer study. It is reverse engineering with sound-effects code removed, not Hubbard's original labeled source. Its note/body split, eight-byte instruments, octave alternation, saved-high-byte descent and noise transient are predictions to test against this archive; byte/address correspondence has not been established. |
| [Recovered repository listing](https://github.com/realdmx/c64_6581_sid_players/blob/f215174fc4c983674808fcd47bc506f96b3d2d04/Hubbard_Rob/Hubbard_Rob_Monty_on_the_Run.asm) | The cached repository tree at revision `f215174fc4c983674808fcd47bc506f96b3d2d04` contains this 31,840-byte blob, Git SHA-1 `332b81b5ddd21d1ab20c7cd37c32ac786760a267`. Only tree metadata was inspected here; the listing body was not cached, downloaded, assembled or compared. Its relation to McSweeney's reconstruction and the pinned archive remains open. |
| [Hubbard's C64.COM account](https://www.c64.com/interviews/hubbard.html) and [contemporary April 1986 interview](https://www.muzines.co.uk/articles/techtalk-living-off-video/9284) | Existing composer research supplies the evolving-driver and delayed-vibrato/pitch-bend context. It does not assign exact records or executed mechanisms to this bounded Monty window. |

The next bounded technical task should map selected archive code/data to an attributed listing, then observe actual score consumption and instrument-selection PCs in a short window. Establish those addresses before a whole-form probe; do not carry reconstructed listing addresses or omitted sound-effects behavior into the archive by assumption. This preparation makes no independent mechanism or listening claim.

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
