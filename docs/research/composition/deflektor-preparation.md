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

The existing `pal-banked` audit rejects this file **before executing the driver**: its accepted payload range ends at `$BFFF`, and its own host uses `$C000–$C1FF`. Deflektor's player overlaps that workspace. This is a limitation of the current analysis host, not evidence of an invalid tune or a demonstrated CIA/IRQ dependency. Do not relocate the reference bytes or relax the collision guard to make it pass.

The next execution step needs a host placed outside `$C000–$CF72`, with its scratch, stack, vectors and code bounds checked against the unchanged source. Verify that host with controlled fixtures and headless VICE before assigning cadence or comparing source stores. The header alone does not prove that the player avoids other machine dependencies. The existing [banked execution contract](../../validation/psid-audit.md#select-a-subtune-and-expose-ram-beneath-basic) explains why these exclusions are deliberate.

## Reproduce intake

The download registry retains the URL/fingerprint; the original stays in ignored local storage:

```sh
python3 scripts/setup-project.py --only references --include deflektor
python3 scripts/sid_intake.py .local/research/deflektor/Deflektor.sid --subtune 1 --output build/deflektor-intake-new/header.json
```

Choose a fresh output path. [sid_intake.py](../../../scripts/sid_intake.py) reports PSID/RSID v2 declarations and the current audit's admission result separately. It performs no CPU execution and leaves the original untouched. Reference WAVs remain local; no render or listening assessment has been made for this intake.

After compatible execution is established, map the complete form and locate the recurring cowbell in context before choosing an intervention. Preserve its pitch/noise trajectory, articulation, shared-filter state and any voice dependencies. The study still needs independently computed sound, a complete declared arrangement and ending, listening, and an original transfer phrase.
