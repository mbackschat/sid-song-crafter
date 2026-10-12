# Full Für Elise execution and audio evidence

Verified on 2026-10-12. The full three-voice arrangement in [the editable score](../songs/fuer-elise.json) runs to its ending in both the callable PSID player and the standalone C64 PRG. The evidence covers musical register writes, synthesized PCM and headless VICE execution. It does not establish playback through this restricted session's host speakers; the previously recorded `afplay` failure remains a separate result in [the audio guide](audio-workflow.md).

## Reproduce the complete workflow

The reusable front door is [song.py](../scripts/song.py), the score exporter is [build-arrangement.ts](../scripts/build-arrangement.ts), and [verify-arrangement.py](../scripts/verify-arrangement.py) verifies the exported manifest and binaries. Prerequisites and the player contract are described in [the three-voice player guide](three-voice-player.md) and [the audio guide](audio-workflow.md).

```sh
python3 scripts/song.py songs/fuer-elise.json
```

This builds `build/fuer-elise.{prg,sid,asm,events.json}`, renders `build/fuer-elise.wav`, checks exact callable CPU writes and sampled SID state, verifies PCM health and available isolated pitch anchors, executes the full PRG in headless VICE, and writes `build/fuer-elise.verification.json`. The manifest supplies the standalone entry, return, finished byte, delay counter and stream cursor addresses; the verifier has no Für Elise-specific addresses or note list.

For an additional independent reSID capture of the standalone PRG:

```sh
python3 scripts/song.py songs/fuer-elise.json --vice-audio
```

This uses ordinary emulation speed and adds `build/fuer-elise.vice.wav`. It takes approximately the piece's duration plus C64 bootstrap time. Default verification runs the native CPU in warp mode with sound disabled and obtains PCM separately from libsidplayfp/SIDLite. VICE 3.9's [sound flush implementation](../.tools/vice-headless-3.9/source/src/sound.c) discards playback samples in warp mode; `-soundwarpmode 1` retains chip emulation but does not make direct WAV playback write those samples.

The successful full reSID run in this session used an isolated copy of the exports under `build/native-validation/`, avoiding simultaneous writes to the main build outputs. Its complete evidence is `build/native-validation/fuer-elise.verification.json`; the resulting WAV was also copied to `build/fuer-elise.vice.wav`. All generated files remain ignored and can be recreated.

## Independent callable CPU oracle

[verify_player.py](../scripts/verify_player.py) derives the SID schedule independently from MIDI numbers, absolute beat positions, tempo, the PAL clock and the player's articulation contract. It then runs the actual PSID payload through py65 and compares every observed SID store with that schedule. This check includes one-frame grace notes, same-pitch retriggers, releases, simultaneous writes, the final volume change and the complete stream beyond 255 events. It checks initialization, stack, Y and zero-page preservation, absence of write-only SID reads, per-call cycle budget, the finished state, deterministic restart and no continuing writes after the ending.

| Full arrangement observation | Result |
| --- | ---: |
| Notes on voices 1 / 2 / 3 | 554 / 181 / 246 |
| Total notes | 981 |
| Scheduled playback SID writes | 3,928 |
| Initialization SID writes | 41 |
| PAL ticks including release tail | 7,857 |
| Checked play calls, including tick zero | 7,858 |
| Initialization cycles | 450 |
| Maximum play-call cycles | 1,334 |
| PAL frame cycle budget | 19,656 |
| Finished tick | 7,857 |

The exact-write regressions include corrupted gate-off and grace gate-on instructions, a wrong initialization envelope byte and an inconsistent manifest write. The CPU guard verifies articulation even when a frame-level snapshot cannot observe an intermediate gate edge.

## Rendered PCM and sampled SID state

[render-sid.cpp](../scripts/render-sid.cpp) forces PAL timing, renders one SID and uses the SID file's model preference, with MOS8580 as its default. The output is mono PCM16 at 44,100 Hz. Duration is bounded to 600 seconds; the frame-sized mixer buffer keeps working memory independent of song length. A regression renders an independent A4 fixture for 60.01 seconds, checks all 2,646,441 samples and checks audible oscillation and pitch at 59 seconds. Another regression rejects 600.01 seconds before creating output.

| Measurement | libsidplayfp 3.1.1 / SIDLite |
| --- | ---: |
| Manifest performance duration | 156.749464 seconds |
| Render duration, including verification tail | 157.749456 seconds |
| PCM samples | 6,956,751 |
| Peak absolute PCM value | 11,930 |
| Samples at either PCM clipping endpoint | 0 |
| Final 0.2-second AC RMS | 0.0 |
| Register snapshots | 8,608 |
| Observable onsets on voices 1 / 2 / 3 | 554 / 181 / 246 |

Register snapshots are emitted after renderer iterations and timestamped by the emulation library; they are not one-to-one with the score's PAL ticks. The 8,608 snapshot rows and 7,857 score ticks therefore count different things. The snapshot verifier compares timestamped states with the scheduled register states of all voices, including instrument configuration, frequency, control and final master volume. It allows one PAL frame of scheduling tolerance and valid intermediate states between ordered stores at the same tick. It reports scheduled notes separately from observable onsets. In this arrangement those counts coincide; they need not coincide for every valid score, especially when a same-pitch retrigger occurs within one sampled interval. Exact write validation supplies the stronger oracle.

Two sufficiently long, isolated E5 events provide independent PCM pitch anchors. MIDI 76 implies 659.255114 Hz; their measured rising-crossing frequencies are 659.455687 and 658.398541 Hz, within the three-hertz guard. The small independent three-voice fixture additionally checks isolated PCM anchors on each voice: C5, C3 and G4. Anchor selection includes the other voices' release times from [MOS 6581 specification Table 2](../skills/c64-sid/references/sid-chip-spec.md), corrected for the PAL clock and given a settling margin. A slow releasing voice therefore cannot be assumed silent merely because its gate is off. When a score provides no isolated pitched passage, the verifier reports an empty anchor list rather than inventing a polyphonic pitch measurement; exact MIDI-to-register validation still applies.

The renderer adds one second beyond the declared performance duration for the quiet-ending check. With only half a second added, the full score's final measurement included approximately 40 ms of a decaying DC transient, despite the final register trace already showing all gates off and volume zero. The longer verification tail produced a constant offset and AC RMS zero. Subtracting the mean distinguishes that offset from continuing audio.

## Complete standalone PRG in native VICE

The native verification uses the genuine [headless VICE 3.9 build](vice-startup-investigation.md), ordinary monitor command files and process logs. It launches no GUI and listens on no monitor socket. It loads the actual BASIC-wrapped PRG with `loadbasic`, enters lowercase `run` through the keyboard buffer, waits for the exported standalone entry and final RTS, then checks the finished byte, zero countdown, cursor at the stream end, restored stack and memory ports, all gates off and master volume zero.

The final monitor commands use `next` across the wrapper RTS and `return` across the SYS dispatcher before inspecting the BASIC caller. This matters because a pending IRQ can enter KERNAL before an ordinary single step, and SYS first returns through a KERNAL trampoline. VICE's [monitor implementation](../.tools/vice-headless-3.9/source/src/monitor/monitor.c) tracks interrupts while stepping over subroutines. The return check therefore follows the real caller path without fixing a BASIC return address or bypassing BASIC with a program-counter assignment.

| Native observation | Result |
| --- | ---: |
| Wrapper execution cycles | 154,439,071 |
| Wrapper execution duration | 156.751371 seconds |
| Difference from manifest duration | 0.001907 seconds |
| Default warp CPU verification wall time | approximately 12.5 seconds |
| Full reSID capture wall time | approximately 159.6 seconds |
| Full reSID WAV duration, including bootstrap | 158.941315 seconds |
| Full reSID PCM samples | 7,009,312 |
| Full reSID peak absolute PCM value | 9,025 |
| Full reSID samples at clipping endpoints | 0 |
| Full reSID final 0.2-second AC RMS | 15.782301 |

The reSID quiet-ending guard allows 32 PCM units, approximately -60 dB relative to full scale, to accommodate its measured residual signal. SIDLite retains the stricter ten-unit guard and measured zero AC RMS. The reSID capture includes machine bootstrap; its duration is also checked against native CPU cycles rather than equated with the musical duration. Both engines produced nonzero music without hard clipping, and the native SID state ended silently.

Every external renderer call has a 60-second deadline. Native warp CPU verification has a 60-second deadline; a full audio run has the declared performance duration plus 20 seconds. The verified full run completed before its deadline. All owned processes exited successfully and were reaped. No desktop VICE instance was changed.

## Resolved verifier boundary cases

- A sampled state at score tick 783 contained the new voice-1 frequency `$2964` while its control byte still held the previous gate-off value `$10`. The next snapshot had `$11`. This is a valid observation between frequency and gate stores in a cycle-bounded libsidplayfp call; a regression now covers the same mechanism on a different voice.
- VICE appends to its monitor log and includes raw character bytes in memory dumps. The verifier removes an old monitor log before launch and decodes those character columns with replacement; numeric checks use the ASCII address and hex-byte columns.
- A failed rerun must not leave a successful verification report appearing current. The verifier removes a prior report before running dependent checks and only writes a new report after all checks pass.

These checks establish complete execution, reproducible exports and synthesized audio. The study of richer musical instruments and authoring workflows continues in [the composer research](research/composers/README.md); its listening judgments remain separate from the automated guards described here.
