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

When multiple tools share the same emulation engine, agreement is useful but not fully independent evidence. SIDDump's simplified execution is complementary to full C64 emulation, not a replacement for it. [S19](../sources.md#s19), [S20](../sources.md#s20)

## Research results and limits

- Primary specifications, selected player/compiler source, and maintainer documentation were inspected; source URLs and access dates are in [the register](../sources.md).
- Note-frequency examples and timing arithmetic were calculated locally.
- Both candidate skill repositories were cloned by the user; exact revisions are recorded in [the integration guide](../tools/skills-and-integrations.md).
- Both skills are installed locally. The c64bridge MCP handshake, tool discovery, and platform resource read succeeded; the platform reports VICE active.
- The existing VICE installation was located. A command-line version probe failed with an executable-path/`argv[0]` error in this restricted session. This does not establish that VICE is broken outside the session.
- An actual MCP request initially failed during GTK startup. A subsequent genuine headless VICE build boots, but this session denies binary-monitor socket binding. No successful MCP emulator connection is claimed; see [the investigation](../../setup/vice-startup-investigation.md).
- The [first-song implementation](../../songs/first-song.md) exports a nine-note opening excerpt and passes independent 6502 execution checks for timing, articulation, rests, restart, and the standalone frame scheduler.
- Genuine headless VICE also executes the PRG through BASIC, reaches the standalone entry and return, restores the processor port, and finishes with master volume zero. File-based monitor evidence is recorded in [the audio workflow](../../workflows/audio-workflow.md); this needs neither a window nor a listening socket.
- A separate hand-coded A4 fixture and the opening excerpt pass [headless audio checks](../../workflows/audio-workflow.md) using libsidplayfp/SIDLite. A WAV was rendered; host audio playback failed, so no listening or physical SID verification is claimed.
- The complete three-voice [Für Elise arrangement](../../songs/fuer-elise-score.md) now passes exact CPU register-write checks, SIDLite rendering, and native headless VICE execution. A separate VICE/reSID recording passes clipping and ending checks. See [the dated measurements](../../validation/fuer-elise-validation.md) for timing, CPU cost, and limitations. No broad SID corpus, listening assessment, or physical SID validation is claimed.

## Next sound-quality checks

The PAL/8580 opening excerpt and complete arrangement establish reproducible correctness baselines. The full arrangement uses simple per-voice instruments; it does not yet demonstrate the chip's sound-design range. Compare native editor and exported-player audio using the [composition-tool trial](../tools/composition-tools.md), then develop the [instrument repertoire](../composition/sound-design-repertoire.md) with listening evidence.

The [native instrument trials](../../workflows/instrument-trials.md) and [complete native workflow](../../workflows/native-song-workflow.md) provide driver-aware schedule, register and audio checks, including an original six-voice/two-filter fixture. Remaining work includes broader comparative listening, further sound-design techniques, physical-chip validation and a complete dual-SID arrangement. Allocate the second chip deliberately for voice overlap and independent filter/volume control. The skill/server setup status belongs in [local setup](../../setup/local-setup.md), so research observations are not confused with installation success.
