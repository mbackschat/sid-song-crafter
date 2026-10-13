# Ghouls 'n' Ghosts: reference intake

This bounded intake pins the C64 reference, preserves supported subtune attribution and records a rejected callable audit. It establishes no decoded score or synthesis mechanism, complete form, rendered audio or listening verdict. Read the [Follin composer study](../composers/follin-daglish.md), [technique lookup](../technique-index.md) and [execution procedure](../tools/sid-program-analysis.md) before choosing a passage or implementing an instrument.

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

The unchanged [PSID profile parser](../../../scripts/psid_profile.py) accepts this header with explicit `pal-banked` subtune 1. The attempted 64-call [CPU audit](../../../scripts/psid_audit.py) then rejects execution with the exact message `Unsupported I/O write at $d41c`. No audit report or ordered-write ledger was produced, and the requested 64 calls are not evidence that 64 calls completed. The CLI failure does not capture the failing phase or instruction PC.

`$D41C` is the SID voice-3 envelope readback address, within the [SID readback register range](../sid/hardware.md#register-reference); the current callable auditor permits SID stores only through `$D418`. The rejection does not establish why the driver writes there or justify ignoring that write. Production guards remain unchanged. Header admission and successful execution are separate findings; a future execution contract needs independently supported handling and emulator coverage before any form or instrument claims.

## Reproduce the bounded checks

Acquire the exact linked SID into its private location and verify the SHA-256 above. The [download and evidence guide](../../setup/local-setup.md) owns private reference handling. Use fresh output paths; the inspector and auditor refuse existing output files.

```sh
python3 scripts/setup-project.py --only references --include ghouls-n-ghosts
python3 scripts/sid_intake.py .local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid --subtune 1 --output build/ghouls-intake/header.json
PYTHONPATH=.tools/test-deps python3 scripts/psid_audit.py .local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid --ticks 64 --profile pal-banked --subtune 1 --output build/ghouls-intake/audit64.json
```

The audit command reproduces the recorded rejection with the pinned tool revisions in the receipt. No compatibility exception, longer trace or render is part of this intake.
