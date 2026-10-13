# Ghouls 'n' Ghosts: reference intake

This bounded preparation pins the C64 reference, preserves supported subtune attribution and verifies initialization plus 64 calls of selection 1 against headless VICE. It establishes no decoded score or synthesis mechanism, complete form, rendered audio or listening verdict. Read the [Follin composer study](../composers/follin-daglish.md), [technique lookup](../technique-index.md) and [execution procedure](../tools/sid-program-analysis.md) before choosing a passage or implementing an instrument.

## Reference identity

The [HVSC reference](https://www.hvsc.de/download/C64Music/MUSICIANS/F/Follin_Tim/Ghouls_n_Ghosts.sid) is retained privately at `.local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid`. The [header report](../../../evidence/ghouls-intake/header.json) and [intake receipt](../../../evidence/ghouls-intake/receipt.json) preserve metadata, source/tool fingerprints and the bounded execution result checked on 2026-10-13. The original SID and its payload are excluded from the evidence archive and Git.

| Declaration | Pinned value |
| --- | --- |
| SHA-256 / file size | `265644a66d6043e6fe5ddeeb0d87e9b4269386a73c3e26457c8d96ce3d042df4` / 19,005 bytes |
| Header | PSID v2, data offset `$007C`, embedded load address |
| Header title / author / release | `Ghouls 'n' Ghosts` / `Tim Follin` / `1989 US Gold/Capcom` |
| Load / init / play | `$2980` / `$6110` / `$6234` |
| Payload extent | 18,879 bytes; end `$733F` exclusive |
| Subtunes | 32; default 1 |
| Clock / SID / speed | PAL / MOS6581 / speed word `$00000000`, VBI declaration for all 32 entries |
| Flags | `$0014` |

These are header declarations, not measured call cadence or musical roles. The [download registry](../../../config/local-assets.json) supplies the exact URL, hash, private destination and non-default reference entry; it does not contain source bytes.

## Supported subtune labels and authorship

Cached [HVSC STIL v85](https://hvsc.c64.org/download/C64Music/DOCUMENTS/STIL.txt), dated June 28, 2026 and SHA-256 `b1ef3584a5b3501e2bbd2ef056d6539a1bbee7933a7828537c3946c1b16cde43`, identifies only two entries for this file. The receipt enumerates all 32 subtunes and preserves unknown labels explicitly.

| Entries | Supported label / original-source attribution |
| --- | --- |
| 8 | Stage 2: The Village of Decay; arcade source music credited to Tamayo Kawamoto |
| 10 | Stage 4: The Crystal Forest; arcade source music credited to Tamayo Kawamoto |
| 1–7, 9, 11–32 | Unlabeled in this cached STIL entry; neither musical purpose nor sound-effect status established |

The header credits Follin for the C64 soundtrack; the STIL credits above distinguish arcade source music from its C64 arrangement. Default selection 1 does not itself prove that entry is the title tune. Stage labels do not establish the complete form or duration of those entries.

In [Stephen Ruddy's first-hand interview](https://www.c64.com/interviews/ruddy.html), the Ghouls discussion identifies his music-driver programming with Tim Follin's design input. This supports game-specific collaboration. It does not identify the exact revision of the pinned HVSC driver or make other Follin platform drivers interchangeable. The receipt pins the cached interview and relevant source lines; the [composer study](../composers/follin-daglish.md#what-the-published-accounts-establish) retains the wider workflow evidence.

## Callable admission and execution boundary

The unchanged [PSID profile parser](../../../scripts/psid_profile.py) accepts this header with explicit `pal-banked` subtune 1. The initial intake's attempted 64-call audit failed with `Unsupported I/O write at $d41c`, before producing a report or ordered-write ledger. The subsequent [frozen rejection context](../../../evidence/ghouls-sid-window/rejection.json) identifies init PC `$61AC`, `STA $D400,Y`, A=`$08`, Y=`$1C`, at instruction-start cycle 117,661 and before any captured SID store. The requested 64 calls did not complete in that historical run.

The failure was a tool boundary error: the 25 sound-control registers do not exhaust the canonical 32-byte SID write window. The [primary-source receipt](../../../evidence/ghouls-sid-window/semantics.json) establishes that reviewed reSID writes update bus state before dispatching active controls; readback/unused ports are not safely described as inert. The [corrected common contract](../../validation/psid-audit.md#canonical-sid-write-windows) retains every ordinary store in each declared window. Reads, read-modify-write stores and undeclared mirrors remain rejected; no SID bus-state model was added.

On 2026-10-13 the [CPU report](../../../evidence/ghouls-sid-window/audit64.json), [complete ordered ledger](../../../evidence/ghouls-sid-window/audit64.writes.json.gz), [parsed VICE trace](../../../evidence/ghouls-sid-window/vice64/trace.json.gz) and [VICE verification](../../../evidence/ghouls-sid-window/vice64/study.json) establish:

| Scope | Observed result |
| --- | --- |
| Initialization | 119,552 CPU cycles; 58 stores: for Y=`$1C` down through `$00`, write `$08` then `$00` to `$D400+Y` from PCs `$61AC/$61B1`. Eight stores target readback ports `$D419–$D41C`; their order and values are retained. |
| Play calls 0–63 | 329 stores; maximum 2,022 and mean 399.5625 CPU cycles per call, within the 19,656-cycle budget. |
| Independent VICE comparison | All 387 init/play stores match in phase, call, address, value and order. Maximum observed call-cadence error is eight cycles against the nine-cycle polling tolerance. |

The [verification receipt](../../../evidence/ghouls-sid-window/verification.json) pins inputs, tools and all retained records. This proves bounded execution under the controlled raster host, not the original game's environment or selection 1's musical role. The CPU report's register summary covers playback; use its complete ledger for initialization. Monitor timestamps are checkpoints, not exact SID bus-write cycles. Raw monitor/process logs and executable payload files stay local.

## Reproduce the bounded checks

Acquire the exact linked SID into its private location and verify the SHA-256 above. The [download and evidence guide](../../setup/local-setup.md) owns private reference handling. Use fresh output paths; the inspector and auditor refuse existing output files.

```sh
python3 scripts/setup-project.py --only references --include ghouls-n-ghosts
python3 scripts/sid_intake.py .local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid --subtune 1 --output build/ghouls-sid-window-new/header.json
PYTHONPATH=.tools/test-deps python3 scripts/psid_audit.py .local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid --ticks 64 --profile pal-banked --subtune 1 --output build/ghouls-sid-window-new/audit64.json
python3 scripts/trace-sid-vice.py .local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid --oracle build/ghouls-sid-window-new/audit64.writes.json --profile pal-banked --subtune 1 --first-call 0 --last-call 63 --output build/ghouls-sid-window-new/vice64
```

To check the old failure, [restore the archived records](../../workflows/build-cache.md) and run `PYTHONPATH=.tools/test-deps python3 build/ghouls-sid-window/verify-rejection.py`. That verifier checks source/dependency hashes, loads the frozen pre-fix auditor and compares all 12 retained instruction contexts without overwriting the receipt. The original executed probe is preserved separately; do not run it against the corrected auditor expecting the old failure. No longer trace or render is claimed here.
