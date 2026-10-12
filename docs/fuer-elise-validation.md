# Full Für Elise validation

The [baseline three-voice score](../songs/fuer-elise.json) has 981 selected notes and a 156.75-second performance including its release tail. Validation checks the complete callable PSID, synthesized audio and standalone PRG in headless VICE. These are separate checks; none establishes a listening preference or physical SID fidelity. The richer SID-Wizard candidate uses [its own native-driver oracle](native-song-workflow.md).

## Reproduce verification

With prerequisites from [the player guide](three-voice-player.md) and [audio guide](audio-workflow.md):

```sh
python3 scripts/song.py songs/fuer-elise.json
```

[song.py](../scripts/song.py) builds the SID/PRG and event manifest, renders audio, checks callable CPU writes and sampled SID state, verifies PCM health and isolated pitch anchors, and executes the full PRG through BASIC. Results go to `build/fuer-elise.verification.json`. The manifest supplies entry/return addresses, the finished byte, delay counter and stream cursor; the verifier does not hard-code Für Elise addresses or notes.

For an independent reSID recording:

```sh
python3 scripts/song.py songs/fuer-elise.json --vice-audio
```

This adds `build/fuer-elise.vice.wav` and takes approximately the piece's duration plus bootstrap time. Default VICE verification runs in warp with sound disabled; PCM comes separately from libsidplayfp/SIDLite. Keep warp disabled when capturing WAV: VICE's [sound flush implementation](../.tools/vice-headless-3.9/source/src/sound.c) discards playback samples during warp, even when chip emulation remains enabled.

## Callable CPU contract

[verify_player.py](../scripts/verify_player.py) independently derives the schedule from MIDI pitches, absolute beats, tempo, PAL clock and articulation rules, then compares every actual SID store with it. Required cases include one-frame grace notes, same-pitch retriggers, releases, simultaneous changes, the final volume change and streams exceeding 255 events.

The oracle checks initialization, stack/Y/zero-page preservation, absence of write-only SID reads, per-call cycle budget, finished state, deterministic restart and no writes after the ending. Regression tests corrupt representative instructions and manifest entries to ensure the guards fail.

| Baseline invariant | Expected value |
| --- | ---: |
| Voice note counts | 554 / 181 / 246 |
| Playback / initialization SID writes | 3,928 / 41 |
| Finished tick | 7,857 |
| Calls through the finished tick | 7,858 |
| Maximum measured play-call cycles | 1,334 |
| PAL frame budget | 19,656 |

## Audio and snapshot checks

[render-sid.cpp](../scripts/render-sid.cpp) produces mono PCM16 at 44,100 Hz, forces PAL and follows the file's SID-model preference. MOS8580 is the default. Rendering is bounded to 600 seconds and uses a frame-sized buffer. The verifier requires the exact requested sample count, nonzero AC energy, no PCM rail samples and a quiet ending.

Snapshots occur after renderer iterations, not once per score tick. Compare timestamps with scheduled states using one PAL frame of tolerance, including valid intermediate states between ordered SID stores. A frequency store followed by a gate store can be observed between those instructions. Count scheduled notes separately from observable onsets: sampled state can miss an intra-frame same-pitch retrigger, while the exact-write oracle still verifies it.

Use isolated sustained notes for PCM pitch checks. Anchor selection includes other voices' release times from [MOS 6581 specification Table 2](../skills/c64-sid/references/sid-chip-spec.md), corrected for PAL and given a settling margin. Gate-off alone does not mean silence. The baseline supplies isolated E5 anchors; a separate fixture covers each voice. The pitch guard allows three hertz. When no isolated passage exists, report no anchors rather than infer polyphonic pitch from a monophonic estimator.

Render one second beyond the performance for the ending check. SID output can retain a decaying DC transient after gates and volume close; subtract the mean and measure AC RMS. SIDLite uses a ten-unit ending threshold. The independent reSID capture allows 32 PCM units, approximately −60 dB relative to full scale, for residual signal. Both baseline engines pass these guards without hard clipping.

## Standalone C64 checks

Use [headless VICE](vice-startup-investigation.md) with a monitor command file. `loadbasic` and lowercase `run` exercise the actual BASIC wrapper. Check the exported entry and final RTS, finished byte, zero countdown, stream-end cursor, restored stack/memory ports, closed gates and zero SID volume.

Use monitor `next` across the wrapper RTS and `return` across the SYS dispatcher before inspecting the BASIC caller. A pending IRQ may otherwise enter KERNAL, and SYS returns through a KERNAL trampoline. VICE's [monitor implementation](../.tools/vice-headless-3.9/source/src/monitor/monitor.c) handles interrupts during subroutine stepping; follow that path instead of assuming a fixed BASIC return address.

Compare performance cycles with the score duration. A native WAV includes bootstrap time, so its duration must not be equated directly with musical duration. Renderer and warp verification calls have 60-second deadlines; native audio gets the performance duration plus 20 seconds.

## Reusable verifier safeguards

- VICE appends to monitor logs: remove an existing log before launching a new check.
- Memory dumps contain raw character bytes: decode with replacement and parse only ASCII address/hex columns.
- Invalidate an old success report before dependent checks and write a replacement only after every guard passes.
- Keep concurrent builds in separate output directories to prevent evidence from different binaries being mixed.
