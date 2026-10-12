# Validation and remaining questions

## Evidence levels

Use explicit labels: documented by author, inspected in source, calculated locally, executed locally, rendered, or heard on hardware. Do not upgrade one category into another. A successful MCP call or emulator process launch does not establish correct music.

## Proposed verification sequence

1. Check note values and target-clock frequency words against an independent calculation.
2. Validate events before export: durations, rests, repeats, voice conflicts, tempo changes, and ending.
3. Inspect binary/header structure and memory layout.
4. Run a one-note test, repeated-note test, explicit rest, and short phrase.
5. Trace register writes and compare scheduled events; use cycle-aware tracing where snapshot tools are insufficient.
6. Render the complete tune and compare musical timing, ending, clipping, balance, and pitch.
7. Repeat with the intended PAL/NTSC and SID model combinations, plus both chip addresses for dual SID.
8. Validate on real hardware when analogue timbre or hardware compatibility is a requirement.

When multiple tools share the same emulation engine, agreement is useful but not fully independent evidence. SIDDump's simplified execution is complementary to full C64 emulation, not a replacement for it. [S19](sources.md#s19), [S20](sources.md#s20)

## Research results and limits

- Primary specifications, selected player/compiler source, and maintainer documentation were inspected; source URLs and access dates are in [the register](sources.md).
- Note-frequency examples and timing arithmetic were calculated locally.
- Both candidate skill repositories were cloned by the user; exact revisions are recorded in [the integration guide](11-skills-and-integrations.md).
- Both skills are installed locally. The c64bridge MCP handshake, tool discovery, and platform resource read succeeded; the platform reports VICE active.
- The existing VICE installation was located. A command-line version probe failed with an executable-path/`argv[0]` error in this restricted session. This does not establish that VICE is broken outside the session.
- An actual MCP request initially failed during GTK startup. A subsequent genuine headless VICE build boots, but this session denies binary-monitor socket binding. No successful MCP emulator connection is claimed; see [the investigation](../vice-startup-investigation.md).
- The [first-song implementation](../first-song.md) exports a nine-note opening excerpt and passes independent 6502 execution checks for timing, articulation, rests, restart, and the standalone frame scheduler.
- Genuine headless VICE also executes the PRG through BASIC, reaches the standalone entry and return, restores the processor port, and finishes with master volume zero. File-based monitor evidence is recorded in [the audio workflow](../audio-workflow.md); this needs neither a window nor a listening socket.
- A separate hand-coded A4 fixture and the opening excerpt pass [headless audio checks](../audio-workflow.md) using libsidplayfp/SIDLite. A WAV was rendered; host audio playback failed, so no listening or physical SID verification is claimed.
- No complete classical arrangement or SID song corpus has been verified yet.

## Open decisions for the first song

Recommended baseline: PAL, one 8580, a short Für Elise opening phrase, editable source plus PRG and SID exports. This keeps the musical and playback contract small enough to verify. Add a second SID only after identifying overlap that materially improves the arrangement.

The excerpt establishes a pinned assembler, musical source, chosen tempo, CPU-level event behavior, and reproducible headless audio rendering. Remaining work includes MCP connectivity in a socket-capable runner, listening comparison, full arrangement and accompaniment, CPU-budget measurements, and dual-SID/hardware validation. The skill/server setup status belongs in [local setup](../local-setup.md), so research observations are not confused with installation success.
