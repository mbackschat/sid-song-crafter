# Existing C64/SID skills and integrations

## Recommended combination

Use `sunsided/c64-skills`'s `c64-sid` for hardware reference and `chrisgleissner/c64bridge`'s `sid-music` for selecting MCP playback operations. A skill supplies instructions; the c64bridge server supplies executable tools. Installing one does not implicitly install or connect the other. Local activation and VICE configuration are documented in [local setup](../../setup/local-setup.md).

Both repositories were inspected locally after the user cloned them on 2026-10-12:

| Project | Exact revision | Relevant entry |
| --- | --- | --- |
| c64-skills | `480b253b147655fa6ff6eb74577d1a2523d512d4` | [c64-sid/SKILL.md](https://github.com/sunsided/c64-skills/blob/480b253b147655fa6ff6eb74577d1a2523d512d4/c64-sid/SKILL.md) |
| c64bridge | `0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18` | [.github/skills/sid-music/SKILL.md](https://github.com/chrisgleissner/c64bridge/blob/0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18/.github/skills/sid-music/SKILL.md) |

## Hardware skill assessment

`c64-sid` bundles register explanations, basic sound examples, and reference extracts from Commodore manuals. It is a useful source of targeted context. It also points to related memory-map, CIA, VIC-II, assembly, and other C64 skills. Only the SID skill from that collection is installed here; the rest remain in the source checkout. [S26](../sources.md#s26)

Two upstream descriptions needed correction: release continues after GATE becomes zero, and voice-3 mute excludes only the direct path, not its filtered signal. The [project skill guidance](../../setup/skill-guidance.md) records these corrections with evidence; installed upstream files remain unchanged. Note tables also need the intended PAL/NTSC clock; do not copy a table into a different target without checking it. [S01](../sources.md#s01), [S03](../sources.md#s03)

## c64bridge: capabilities and limits

The server exposes grouped tools such as `c64_sound`, with operations selected through an `op` field. Its SID workflow includes direct voice control, score compilation, and a built-in `fuer_elise` preset. Backend support differs: Ultimate-specific file playback and audio streaming cannot be assumed to work through VICE. The skill itself says to distinguish a successful VICE launch from unavailable live audio analysis. [S24](../sources.md#s24)

Source inspection of [sidwaveCompiler.ts at the pinned revision](https://github.com/chrisgleissner/c64bridge/blob/0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18/src/sidwaveCompiler.ts) revealed limitations relevant to this project's goal:

- It generates voices 1–3 only, so this path is not a six-voice compiler.
- It caps the frame table at 255 and loops it. At nominal 50/60 Hz this represents approximately 5.1/4.25 seconds, regardless of a much longer score declaration.
- It assumes four beats per bar and rounds frames per beat. That is insufficient by itself to preserve arbitrary meter and detailed classical rhythm.
- Its groove/arpeggio index is incremented at frame zero before selecting the first note; the first stored pattern element is consequently skipped on that first step.
- It writes GATE-on controls for every generated frame. Unrecognized note text falls back to MIDI 48; therefore a `"-"` rest in the inspected preset reaches a pitched fallback rather than an explicit note-off in this path.
- The generated single-entry routine dispatches initialization using zero-page `$FC`; the host must establish that state and provide ongoing play calls. A PRG containing the routine alone is not a self-scheduling song.

These are source observations, not an end-to-end audio test. The inspected [preset definition](https://github.com/chrisgleissner/c64bridge/blob/0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18/src/tools/meta/audio.ts) contains the familiar melody material, but the preset name is not evidence of a faithful or complete Für Elise performance. Do not build a full song workflow on these compiler assumptions without fixing and independently testing them. Upstream implementation was not modified in this installation task.

Recommendation: retain the bridge for emulator integration and small experiments; use a mature tracker/exporter for complete deliverables initially. A focused future compiler repair would need tests for rests, first-note order, repeated-note articulation, duration beyond 255 frames, initialization, and player scheduling.

## Select tools for an executed-program study

Use these capabilities in the [listen, trace, intervene procedure](sid-program-analysis.md). On 2026-10-13, the installed instruction skills were `c64-sid` and `sid-music`; no c64bridge MCP tools were callable in the inspected session. Additional skills below were read in the existing checkouts, without installing them. A schema or skill describes an available method; the independent headless VICE probes establish which local executable operations actually work.

| Capability and evidence | Procedure phase | Verified limits and use |
| --- | --- | --- |
| [c64-disassembly instructions](https://github.com/sunsided/c64-skills/blob/480b253b147655fa6ff6eb74577d1a2523d512d4/c64-disassembly/SKILL.md); source inspected | Identify entry points; work backward from writes | Distinguish containers, reachable code, tables, banking and self-modification. Disassemble from an executed instruction boundary; a linear listing is not an execution trace. |
| [c64-memory-map](https://github.com/sunsided/c64-skills/blob/480b253b147655fa6ff6eb74577d1a2523d512d4/c64-memory-map/SKILL.md) and [c64-cia](https://github.com/sunsided/c64-skills/blob/480b253b147655fa6ff6eb74577d1a2523d512d4/c64-cia/SKILL.md); source inspected | Establish memory and update cadence | Track `$00/$01`, ROM/RAM/I/O mapping, IRQ/NMI vectors and CIA timer setup. The current callable-player tracer does not reproduce an arbitrary tune's original IRQ environment. |
| [memory-debug instructions](https://github.com/chrisgleissner/c64bridge/blob/0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18/.github/skills/memory-debug/SKILL.md); source inspected | Inspect instrument state; intervene | Guides `c64_memory` reads/writes and rereading patched bytes; it supplies no executable debugger itself. Use a disposable program copy and verify the intended change. |
| c64bridge [`c64_memory`](https://github.com/chrisgleissner/c64bridge/blob/0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18/src/tools/registry/memory.ts) / [`c64_debug`](https://github.com/chrisgleissner/c64bridge/blob/0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18/src/tools/debug.ts); source inspected | Read/disassemble memory; inspect registers, step and manage conditional checkpoints | The pinned schemas contain these operations, including `create_checkpoint` with load/store/execute filters and `stopOnHit`. They are not locally verified MCP calls. The [VICE client](https://github.com/chrisgleissner/c64bridge/blob/0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18/src/vice/viceClient.ts) requires a socket connection, unavailable in this session. |
| VICE `d`, `m`, `r`, `bank`; runtime verified | Inspect executed code and state | `bank cpu` follows live mapping; `bank ram` reads underlying RAM. `sidefx off` prevents monitor reads from clearing registers such as CIA ICR. SID write-only registers cannot be recovered by reading a memory dump; observe their stores. |
| VICE `step`, `next`, `return`; runtime verified | Follow a state update | The fixture verified stepping into instructions, over a JSR and out through RTS. A stopped file-monitor sequence allows coherent register/memory inspection. |
| VICE `break`, `watch`, conditional `trace`, `until`; runtime verified | Locate writers; capture ordered stores | Execution breaks and RAM-write watchpoints stop; tracepoints record without stopping. Set `dummy off` when excluding dummy accesses, and parenthesize comparisons because VICE 3.9 conditions evaluate left to right. Use the [validated store tracer](../../../scripts/trace-sid-vice.py) when asserting complete write order/value agreement. |
| VICE `cpuhistory`; runtime verified | Work backward from a SID writer | Retains executed opcode bytes and pre-instruction A/X/Y/SP/flags and CPU-cycle timestamps. The local build defines `FEATURE_CPUMEMHISTORY`. History is a finite cyclic buffer, not reverse execution or a log of operand memory values; stop near the event and recover values from adjacent register states and inspected data. |
| VICE `memmapzap`, `memmapshow`; runtime verified | Locate accessed code/state | Reports accumulated RAM/ROM/I/O access classes after clearing the map. It does not retain access order or values. |
| VICE raster/cycle display and `stopwatch`; runtime verified | Establish cadence and align observers | CPU-history timestamps identify instruction starts; store checkpoints occur after the instruction. `stopwatch reset` changes its origin without resetting history timestamps. Neither alone identifies an exact SID bus-write cycle. |

The bridge's [VICE backend](https://github.com/chrisgleissner/c64bridge/blob/0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18/src/device.ts) resumes execution when each monitor operation closes, and its durable `pause`/`resume` return unsupported; the [memory workflow](https://github.com/chrisgleissner/c64bridge/blob/0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18/src/tools/meta/memory.ts) consequently skips pause for VICE. Do not treat several separate MCP reads or steps as an atomic examination of one stopped state. The file monitor is the locally verified route. Command semantics and history storage were inspected in the pinned VICE 3.9 [manual](../../../.tools/vice-headless-3.9/source/doc/vice.texi), [history implementation](../../../.tools/vice-headless-3.9/source/src/monitor/mon_memmap.c) and [build configuration](../../../.tools/vice-headless-3.9/build/src/config.h). [S24](../sources.md#s24), [S26](../sources.md#s26), [S33](../sources.md#s33)

## Follow DRAX's waveform with VICE history

The [bounded monitor fixture](../../../build/tool-capabilities/vice-monitor-2026-10-13/monitor.log) exercised the facilities above in a separate headless process with a 30-second timeout. The [DRAX probe](../../../build/tool-capabilities/drax-history-2026-10-13/monitor.log) then reused the exact payload and controlled harness from the [verified execution study](sid-program-analysis.md#bounded-drax-bass-experiment), stopped before the bass control store at call 102, and printed recent executed history. It returned successfully within the same bound; this does not modify the user's desktop VICE instance.

The probe follows `$1372: LDA $17A2,Y` with `X=0,Y=1` to `$1375: STA $1541,X` with `A=$41`. Later `$144A` loads that state, `$144D` applies `AND $101A,X` with the inspected mask `$FF`, and `$1450` is ready to store `$41` through `$D404,Y` with `Y=0`. A single step executes the store and returns at `$1453`. This supplies an executed table → state → mask → SID chain without assuming a driver's command meanings. RAM inspection shows `$17A2–$17A4 = $81,$41,$40`; the [owning study](sid-program-analysis.md#follow-the-bass-program) records the attack/release interpretation and remaining listening question.

The retained history puts this store's instruction start at cycle `4,163,982`; the register display after stepping is `4,163,987`, matching the five-cycle absolute-indexed store. In the small fixture, the first store starts 19 cycles after the initial history entry and its trace checkpoint is at stopwatch 23. These observations establish the start/after-instruction distinction. The fixture also confirms that resetting the stopwatch leaves history on its original CPU-clock origin.

To reproduce after generating the source payload/harness with the [execution-study commands](sid-program-analysis.md#reproduce-the-execution-evidence), create a fresh output directory and retain the original monitor setup through its first `until`. The following adds only the bounded inspection; the generated setup contains absolute local payload paths.

```sh
python3 - <<'PY'
from pathlib import Path
source = Path('build/reference-studies/drax/program-vice/final/commands.mon')
output = Path('build/tool-capabilities/drax-history-new')
output.mkdir(parents=True, exist_ok=False)
for directory in ('xdg_config_home', 'xdg_state_home'):
    (output / directory / 'vice').mkdir(parents=True)
lines = source.read_text().splitlines()
setup = lines[:next(i for i, line in enumerate(lines) if line.startswith('until ')) + 1]
inspect = [
    'trace store $d400 $d418 if (@ram:$c100 == $66)',
    'break exec $1450 if (@ram:$c100 == $66) && (Y == $00)',
    'x', 'r', 'cpuhistory 300', 'bank ram',
    'm $101a $101a', 'm $17a2 $17a4',
    'd $1372 $1378', 'd $144a $1453',
    'step 1', 'r', 'cpuhistory 3', 'quit', '',
]
(output / 'commands.mon').write_text('\n'.join(setup + inspect))
PY
env -u DISPLAY -u WAYLAND_DISPLAY XDG_CONFIG_HOME="$PWD/build/tool-capabilities/drax-history-new/xdg_config_home" XDG_STATE_HOME="$PWD/build/tool-capabilities/drax-history-new/xdg_state_home" gtimeout 30s .tools/vice-headless-3.9/build/src/x64sc -config /dev/null -directory /Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice -pal +logcolorize -initbreak ready -moncommands build/tool-capabilities/drax-history-new/commands.mon -monlog -monlogname build/tool-capabilities/drax-history-new/monitor.log -limitcycles 5000000 -warp +sound -sidenginemodel resid6581 > build/tool-capabilities/drax-history-new/process.log 2>&1
```

The PC, counter and state addresses are specific to this pinned DRAX binary and harness. For another player, locate its executed writer and update cadence first. Use the [CPU tracer](../../../scripts/trace-sid-program.py) for fast machine-readable instruction/data records and the VICE store tracer for an independent ordered-write comparison; use monitor history to investigate a narrow execution chain. Keep execution findings separate from controlled listening and successful instrument reuse.

## Other discovered projects

| Candidate | Relevance | Inspection level |
| --- | --- | --- |
| [Project64 by nschneir](https://github.com/nschneir/Project64) | Python/VICE/cc65 workflow, CLI and MCP integration, skills | README inspected; not the similarly named Nintendo 64 emulator [S27](../sources.md#s27) |
| [c64-re-tools](https://github.com/henols/c64-re-tools) | Claude Code reverse-engineering plugin, skills, VICE broker | README inspected; dependencies between plugin skills matter [S28](../sources.md#s28) |
| [c64u](https://github.com/cybersorcerer/c64u) | Ultimate hardware CLI and associated knowledge/CLI skills | Discovery-level; no local runtime validation [S29](../sources.md#s29) |

The connected plugin marketplace search for `Commodore C64 SID VICE` returned no matching result on the research date. That is a limited search result, not proof that no relevant marketplace plugin exists. The GitHub projects above are directly inspectable leads; no marketplace plugin was installed.
