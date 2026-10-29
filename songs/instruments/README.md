# Instrument library

Selectable SID-Wizard Extra instruments with measured characterisation, and the listener verdicts that name them. The [instrument library contract](../../docs/proposals/instrument-library.md) owns the record and verdict formats, the probes and the selection procedure; selectors are at least the MEDIUM tier.

| Path | Content |
| --- | --- |
| `<id>@<version>.json` | One immutable record per program version: interface, resources, measured character, fit and provenance. |
| [verdicts/](verdicts/) | One immutable file per listener verdict, with structured context and a verbatim quote from the owning study's listening record. |
| [index.json](index.json) | Generated: each version's verdicts from its own side, computed evidence level, accepted partners, reusability and every arrangement file that embeds the program. |

Records do not store evidence. Change a verdict or record, then regenerate the index:

```sh
python3 scripts/instrument_library.py check   # validate everything; fail when index.json is stale
python3 scripts/instrument_library.py index   # validate and rewrite index.json
python3 scripts/instrument_probe.py songs/instruments/<id>@<version>.json --output build/instrument-probe-<name>
```

The probe prints a program's probe-level-v1 level and brightness; `--write` stores them, which is permitted only before a version is first committed. Existing arrangement files keep their embedded instruments as frozen evidence; the index lists where each library program occurs.
