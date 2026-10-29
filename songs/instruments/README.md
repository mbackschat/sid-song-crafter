# Instrument library

Selectable SID-Wizard Extra instruments with measured characterisation, and the listener verdicts that name them. The [instrument library contract](../../docs/proposals/instrument-library.md) owns the record and verdict formats, the probes and the selection procedure; selectors are at least the MEDIUM tier.

| Path | Content |
| --- | --- |
| `<id>@<version>.json` | One record per program version: interface, resources, measured character, fit and provenance. |
| [verdicts/](verdicts/) | One immutable file per listener verdict, with structured context and a verbatim quote from the owning study's listening record. |
| [index.json](index.json) | Generated: each version's verdicts from its own side, computed evidence level, accepted partners, reusability and every arrangement file that embeds the program. |

Records do not store evidence. Change a verdict or record, then regenerate the index:

```sh
python3 scripts/instrument_library.py check   # validate everything; fail when index.json is stale
python3 scripts/instrument_library.py index   # validate and rewrite index.json
python3 scripts/instrument_probe.py songs/instruments/<id>@<version>.json --output build/instrument-probe-<name>
python3 scripts/instrument_trace.py songs/instruments/<id>@<version>.json --output build/instrument-trace-<name>
```

The level probe prints a program's probe-level-v1 level and brightness. The interface probe executes probe-interface-v1 and derives the interface, waveforms, staged attack, body, motion and filter, coupling and volume use; its output directory keeps the raw facts behind each classification. `--write` stores either probe's fields. A version's program never changes; its measured claims may be filled in or re-measured, and each names its probe version. Existing arrangement files keep their embedded instruments as frozen evidence; the index lists where each library program occurs.
