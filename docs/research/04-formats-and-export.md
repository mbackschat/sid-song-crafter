# Song formats and export

## Keep source and delivery separate

| Format | Role | Important limit |
| --- | --- | --- |
| Tracker song, such as GoatTracker `.sng` | Editable order lists, patterns, instruments, tables | Editor/version-specific |
| MIDI | Notes, durations, tempo and performance events | Does not specify a SID instrument or voice allocation |
| PRG | C64 load address plus executable/data | Needs an appropriate startup and runtime environment |
| PSID/RSID `.sid` | Metadata and machine-code music payload | Usually not editable notation or a tracker source file |
| WAV | Rendered audio | Loses machine-code and synthesis editability |

GoatTracker's packed PRG/BIN/SID output cannot simply be loaded back as its editable song. Preserve `.sng` before packing. ChiptuneSAK provides score representations and conversion paths, but conversion still requires quantization and instrument/voice decisions. [S08](sources.md#s08), [S12](sources.md#s12)

## PSID and RSID

The HVSC specification defines header byte order, load/init/play addresses, subtunes, timing flags, clock and model information, and additional SID locations. Header numeric fields are big-endian; a PRG-style embedded load address is little-endian. Header song numbering and the player initialization convention must not be conflated. A zero play address is a special case, not permission to `JSR $0000`. RSID preserves stricter real-C64 execution requirements and restricts several header fields. [S13](sources.md#s13)

The speed field describes VBI/CIA playback conventions; it is not the composition's BPM. Wrapping arbitrary PRG bytes in a SID header is insufficient: callable entry points and initialization behaviour must actually satisfy the format's execution contract.

## Compatibility observation

The live HVSC specification inspected on 2026-10-12 includes version 5. The inspected libsidplayfp parser accepts PSID versions 1–4 and RSID versions 2–4. This is a source-level compatibility mismatch, not a locally executed rejection test. Check the exact player release before emitting newer headers. [S13](sources.md#s13), [S14](sources.md#s14)

Project recommendation: prefer established v2NG conventions for one SID and v3 for two SIDs when the chosen exporter/player supports them. Do not implement v5 merely because it appears in the current specification.

## Export checklist

1. Keep the exact editable song and instrument resources.
2. Record player/editor revision and license.
3. Specify PAL/NTSC, 6581/8580, and chip addresses.
4. Validate header fields, payload range, init/play behaviour, and every subtune.
5. Test PRG execution in a C64 emulator and SID playback in a SID player separately.
6. Compare the render against the source score and intended ending or loop.

A successful render is evidence of one playback path, not proof of correct native execution on every machine.
