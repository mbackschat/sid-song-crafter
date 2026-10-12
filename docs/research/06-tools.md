# Tools and open-source candidates

## Recommended roles

| Tool | Best use here | Evidence and limits |
| --- | --- | --- |
| GoatTracker 2 / Stereo | Author editable, native three-/six-voice tunes | Author-maintained tool page; readable older v2.72 mirror; verify current packer details [S08](sources.md#s08) |
| SID-Wizard | Compose on the C64, including emulator use | Author's 1.97 release lists sources/examples and native/host builds [S17](sources.md#s17) |
| SID Factory II | Study editable examples and established drivers | Maintainer provides many source tunes and driver-based editing [S18](sources.md#s18) |
| ChiptuneSAK | Import/transform score data and export supported tracker formats | MIT; alpha API; conversions are not lossless orchestration [S12](sources.md#s12) |
| MiniPlayer2 | Learn a compact 6502 player and conversion tradeoffs | MIT; intentionally limited feature set [S11](sources.md#s11) |
| VICE / `x64sc` / `vsid` | Run native programs and inspect C64 behaviour | GPL project; select machine and SID settings explicitly [S16](sources.md#s16) |
| libsidplayfp / libresidfp | SID file loading and high-quality emulation | GPL-family libraries; format and analogue emulation are separate layers [S04](sources.md#s04), [S19](sources.md#s19) |
| SIDDump | Inspect note/register evolution of compatible tunes | BSD-licensed command-line tool; limited execution environment [S20](sources.md#s20) |
| c64bridge | Agent-controlled VICE experiments and playback workflows | Local source inspected; skill/server installation and compiler limits matter [S24](sources.md#s24) |

## Tools that need qualification

Furnace supports SID sound design, but SID emulation or WAV export does not imply standalone C64 PRG/SID export. The inspected native-export documentation does not establish a C64 exporter. MIDIbox SID is valuable synthesis documentation and an external synthesizer platform, rather than a drop-in C64 song player. [S10](sources.md#s10), [S09](sources.md#s09)

SID-Wizard's author release includes a permissive-sounding license declaration, but inspect the downloaded source and dependencies before redistribution. SID Factory II's public repository does not by itself establish a reuse license. Likewise, a GPL editor's license does not automatically settle rights to every bundled song or exported player. Record licenses by component.

## Commands to learn, not results claimed

```sh
# Older GoatTracker manual: load a song, select 1x and 8580 emulation.
goattrk2 song.sng -s1 -e1

# Inspect ten seconds, initializing subtune argument A to zero.
siddump song.sid -a0 -t10

# Dedicated SID-player front end supplied by VICE.
vsid song.sid
```

These commands come from the referenced tool documentation and were not executed against a song here. A modern binary may have different switches. Use its own help and record the revision. For assembly, follow the chosen project's assembler dialect and build instructions; 64tass, ACME, DASM, and ca65 source are not automatically interchangeable. [S08](sources.md#s08), [S20](sources.md#s20), [S16](sources.md#s16)
