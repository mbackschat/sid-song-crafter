# Existing C64/SID skills and integrations

## Recommended combination

Use `sunsided/c64-skills`'s `c64-sid` for hardware reference and `chrisgleissner/c64bridge`'s `sid-music` for selecting MCP playback operations. A skill supplies instructions; the c64bridge server supplies executable tools. Installing one does not implicitly install or connect the other. Local activation and VICE configuration are documented in [local setup](../../local-setup.md).

Both repositories were inspected locally after the user cloned them on 2026-10-12:

| Project | Exact revision | Relevant entry |
| --- | --- | --- |
| c64-skills | `480b253b147655fa6ff6eb74577d1a2523d512d4` | [c64-sid/SKILL.md](https://github.com/sunsided/c64-skills/blob/480b253b147655fa6ff6eb74577d1a2523d512d4/c64-sid/SKILL.md) |
| c64bridge | `0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18` | [.github/skills/sid-music/SKILL.md](https://github.com/chrisgleissner/c64bridge/blob/0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18/.github/skills/sid-music/SKILL.md) |

## Hardware skill assessment

`c64-sid` bundles register explanations, basic sound examples, and reference extracts from Commodore manuals. It is a useful source of targeted context. It also points to related memory-map, CIA, VIC-II, assembly, and other C64 skills. Only the SID skill from that collection is installed here; the rest remain in the source checkout. [S26](../sources.md#s26)

Two upstream descriptions needed correction: release continues after GATE becomes zero, and voice-3 mute excludes only the direct path, not its filtered signal. The staged copy corrects these using its bundled specification and the independently inspected hardware/emulator sources. Original upstream files remain unchanged. Note tables also need the intended PAL/NTSC clock; do not copy a table into a different target without checking it. [S01](../sources.md#s01), [S03](../sources.md#s03)

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

## Other discovered projects

| Candidate | Relevance | Inspection level |
| --- | --- | --- |
| [Project64 by nschneir](https://github.com/nschneir/Project64) | Python/VICE/cc65 workflow, CLI and MCP integration, skills | README inspected; not the similarly named Nintendo 64 emulator [S27](../sources.md#s27) |
| [c64-re-tools](https://github.com/henols/c64-re-tools) | Claude Code reverse-engineering plugin, skills, VICE broker | README inspected; dependencies between plugin skills matter [S28](../sources.md#s28) |
| [c64u](https://github.com/cybersorcerer/c64u) | Ultimate hardware CLI and associated knowledge/CLI skills | Discovery-level; no local runtime validation [S29](../sources.md#s29) |

The connected plugin marketplace search for `Commodore C64 SID VICE` returned no matching result on the research date. That is a limited search result, not proof that no relevant marketplace plugin exists. The GitHub projects above are directly inspectable leads; no marketplace plugin was installed.
