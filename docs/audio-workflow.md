# Headless SID audio workflow

Verified on 2026-10-12: [the renderer](../scripts/render-sid.cpp) runs a SID file through libsidplayfp 3.1.1 and SIDLite without opening a window. It writes mono PCM16 audio at 44,100 Hz plus a `.registers.tsv` sidecar containing the emulated SID's last-written register values after each renderer iteration, timestamped by the emulation library. These snapshots are not one-to-one with PAL frames or individual register writes. [The integration tests](../tests/render_audio_test.py) independently verify A4, the nine Für Elise pitches, their onset timing, and the silent ending.

The generated [Für Elise WAV](../build/fuer-elise-opening.wav) is 3.2 seconds long; [its register trace](../build/fuer-elise-opening.wav.registers.tsv) records the execution evidence. Generated files live in `build/` and are recreated locally. See [the song guide](first-song.md) for the editable score and PRG/SID exports.

## Local library setup

The initial machine had `ffmpeg`/`ffprobe` 9.0.2 and `/usr/bin/afplay`, but no `sidplayfp` executable or libsidplayfp installation. [Homebrew's libsidplayfp formula](https://formulae.brew.sh/formula/libsidplayfp) supplies an Apple Silicon binary package. Its [formula JSON](https://formulae.brew.sh/api/formula/libsidplayfp.json) reported version 3.1.1 and no runtime package dependencies. The verified `arm64_tahoe` bottle is suitable for this arm64 machine running macOS 27.0.1; choose the matching Homebrew bottle when reproducing on another platform.

Download and verify the exact package before extracting it into the project:

```sh
curl --connect-timeout 4 --max-time 20 -fsSL -H 'Authorization: Bearer QQ==' 'https://ghcr.io/v2/homebrew/core/libsidplayfp/blobs/sha256:7e28827526f55a6b86db4ab3f6ec73d8444f0d0c70c1b2c1144928b19d8ce0dc' -o /private/tmp/c64-sid-libsidplayfp-3.1.1.arm64_tahoe.bottle.tar.gz
python3 -c 'import hashlib; from pathlib import Path; assert hashlib.sha256(Path("/private/tmp/c64-sid-libsidplayfp-3.1.1.arm64_tahoe.bottle.tar.gz").read_bytes()).hexdigest() == "7e28827526f55a6b86db4ab3f6ec73d8444f0d0c70c1b2c1144928b19d8ce0dc"'
tar -tf /private/tmp/c64-sid-libsidplayfp-3.1.1.arm64_tahoe.bottle.tar.gz
mkdir -p .local/tools
tar -xf /private/tmp/c64-sid-libsidplayfp-3.1.1.arm64_tahoe.bottle.tar.gz -C .local/tools
```

The package remains under `.local/tools/libsidplayfp/3.1.1`, including its GPL-2.0-or-later `COPYING`, authors, and Homebrew formula. The bottle contains SIDLite rather than reSIDfp. This workflow therefore verifies libsidplayfp/SIDLite output; it is a separate emulator from VICE and its SID engines.

The extracted dynamic library contains an unrelocated `@@HOMEBREW_PREFIX@@` installation ID. Linking the supplied static archive avoids modifying that library, changing system installation paths, or relying on Homebrew relocation. Build with the macOS command-line C++ compiler:

```sh
mkdir -p .local/bin
c++ -std=c++17 -O2 -Wall -Wextra -Werror -I.local/tools/libsidplayfp/3.1.1/include scripts/render-sid.cpp .local/tools/libsidplayfp/3.1.1/lib/libsidplayfp.a -o .local/bin/render-sid
```

This build completed in under one second in the verified session. The renderer accepts `INPUT.sid OUTPUT.wav SECONDS`, forces PAL timing, supports one SID chip, and bounds duration to more than zero and at most 600 seconds. The original 60-second limit was raised for complete songs; regression tests render 60.01 seconds and reject 600.01 seconds. It uses the SID file's model preference, defaulting to MOS8580 when unspecified. A fixed power-on delay removes the library's default startup randomization. Output contains exactly the requested number of samples rounded to the nearest sample, with a minimum of one.

## Render and verification

After building the song as described in [the song guide](first-song.md):

```sh
python3 tests/render_audio_test.py
.local/bin/render-sid build/fuer-elise-opening.sid build/fuer-elise-opening.wav 3.2
ffprobe -v error -show_entries stream=codec_name,sample_rate,channels,bits_per_sample -show_entries format=duration -of json build/fuer-elise-opening.wav
```

The tests first failed because the renderer did not exist, then passed with the implementation. Each renderer invocation has a 20-second subprocess deadline. The A4 test uses a separate hand-coded PSID fixture, so the pitch oracle is independent of the song compiler. The song test checks actual PCM pitch as well as the register trace; every onset is within one PAL frame of its expected position, and the final SID volume is zero.

| Note | Expected Hz | SIDLite PCM Hz | VICE/reSID PCM Hz |
| --- | ---: | ---: | ---: |
| E5 | 659.255 | 658.51 | 659.66 |
| D#5 | 622.254 | 621.37 | 622.51 |
| E5 | 659.255 | 658.36 | 659.50 |
| D#5 | 622.254 | 621.49 | 622.51 |
| E5 | 659.255 | 658.51 | 659.66 |
| B4 | 493.883 | 493.27 | 494.12 |
| D5 | 587.330 | 586.67 | 587.15 |
| C5 | 523.251 | 522.68 | 523.52 |
| A4 | 440.000 | 439.41 | 440.08 |

The PCM measurements use rising crossings around each note's mean, away from attack and release edges; the guard allows a 3 Hz difference. The SID register words correspond to the expected pitches within 0.1 Hz. The WAV contains 141,120 samples, and `ffprobe` independently reports `pcm_s16le`, one channel, 16 bits, 44,100 Hz, and 3.200000 seconds. The final 0.2 seconds have AC RMS zero. Their constant sample value is -157, a SIDLite DC offset rather than continuing oscillation; the silence check subtracts the mean.

An initial renderer attempt exposed a libsidplayfp 3.1.1 documentation mismatch: the header describes `getBufSize()` in bytes, but [the pinned implementation returns a sample count](https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/player.cpp#L591). Dividing that result by `sizeof(short)` underallocates the mixer output buffer and reproduced `SIGTRAP` with both the song and independent A4 fixture. The renderer allocates the returned count of `short` samples and checks capacity before mixing. The diagnostic report was `/Users/mbackschat/Library/Logs/DiagnosticReports/render-sid-2026-10-12-203830.ips`.

Host audio remains a separate check. A single `/usr/bin/afplay build/fuer-elise-opening.wav` attempt in the restricted session exited with code 1 and `AudioQueueStart failed (-66680)`. File rendering and pitch checks succeeded, but this attempt did not establish audible host playback. The WAV is available for playback outside that execution context.

## Full PRG execution in headless VICE

The separately built official VICE 3.9 headless executable also ran the PRG successfully without a window, display environment, or TCP monitor. The final run exited with code 0 through a file-based monitor `quit` command. Its output used reSID MOS8580 and produced [the VICE WAV](../build/fuer-elise-vice.wav), independently confirming all nine PCM pitches within the 3 Hz guard shown above. The raw capture is 210,112 mono PCM16 samples at 44,100 Hz, or 4.764444 seconds, including approximately 2.19 seconds of machine bootstrap before the song; it includes an initial audio startup transient.

The monitor file loads the actual BASIC-wrapped PRG through `loadbasic`, which updates BASIC pointers, then feeds `run` into the keyboard buffer. It waits for the standalone entry, the wrapper's final RTS, and the BASIC ROM's return path. No program-counter assignment bypasses BASIC. Reproduce the file from the project root:

```sh
cat > .local/vice-headless-3.9/fuer-elise-prg.mon <<'MONITOR'
loadbasic "build/fuer-elise-opening.prg" 0
keybuf run\n
until $0810
r
until $083c
r
m $0000 $0001
m $1078 $107a
bank io
m $d400 $d418
bank cpu
until $a474
r
quit
MONITOR
```

These addresses correspond to the generated excerpt verified on 2026-10-12: `$0810` is its standalone entry, `$083c` its wrapper RTS, `$1078-$107a` its event index/ticks/finished state, and `$a474` a BASIC ROM return point. See [the song guide](first-song.md) and generated `build/fuer-elise-opening.asm` / `.events.json` when changing the player.

Run the exact verified capture command; the agent additionally imposed a 15-second subprocess cancellation deadline:

```sh
env -u DISPLAY -u WAYLAND_DISPLAY XDG_CONFIG_HOME="$PWD/.local/vice-headless-3.9/config" XDG_STATE_HOME="$PWD/.local/vice-headless-3.9/state" .tools/vice-headless-3.9/build/src/x64sc -config /dev/null -directory /Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice -pal -sounddev wav -soundarg "$PWD/build/fuer-elise-vice.wav" -sidenginemodel resid8580 -soundrate 44100 +logcolorize -limitcycles 10000000 -initbreak ready -monlogname "$PWD/.local/vice-headless-3.9/fuer-elise-prg-monitor.log" -monlog -moncommands "$PWD/.local/vice-headless-3.9/fuer-elise-prg.mon" > .local/vice-headless-3.9/fuer-elise-prg-run.log 2>&1
```

The readable monitor log is `.local/vice-headless-3.9/fuer-elise-prg-monitor.log`; the complete process output is `fuer-elise-prg-run.log` in the same directory. CPU cycles were 2,157,474 at `$0810`, 4,694,349 at `$083c`, and 4,694,715 at `$a474`. The wrapper therefore ran for approximately 2.575 seconds. Its memory ports `$00/$01` were restored to `2f 37`; state bytes `$1078-$107a` were `0a 00 01`, including `finished=1`; the I/O-bank SID peek showed control `$D404=10`, ADSR `$D405/$D406=06 41`, and volume `$D418=00`. Assertions checked these states and all nine PCM pitches. The final 0.2 seconds have AC RMS approximately 2.50 PCM units, with samples between 7 and 12, below one percent of every active note's amplitude. This small residual is distinct from SIDLite's constant offset; its exact cause was not instrumented. Measurements are retained in `.local/vice-headless-3.9/fuer-elise-prg-audio-evidence.json`.

Two unsuccessful capture details were resolved before this result:

- `keybuf RUN\n` did not reach `$0810` and ended at the cycle limit. [VICE 3.9's keyboard parser](../.tools/vice-headless-3.9/source/src/kbdbuf.c) converts ASCII to PETSCII; using lowercase `run\n` supplies the BASIC keyword correctly. The unsuccessful output is `fuer-elise-prg-uppercase-keybuf.log` in the local diagnostic directory.
- `-sounddev dummy -soundrecdev wav -soundrecarg filename` created a 44-byte WAV with zero channels and no samples, despite opening the recorder and completing the CPU run. In [VICE 3.9 sound_open](../.tools/vice-headless-3.9/source/src/sound.c), `sound_output_channels` is assigned only inside the playback device's initialization callback, while [the dummy driver](../.tools/vice-headless-3.9/source/src/arch/shared/sounddrv/sounddummy.c) has a null callback. [The WAV driver](../.tools/vice-headless-3.9/source/src/arch/shared/sounddrv/soundwav.c) supplies initialization; selecting it directly with `-sounddev wav -soundarg filename` generated the valid capture. Both the first and second dummy-driver recordings exhibited the same empty-header mechanism. The failed WAV and process output are retained as `fuer-elise-prg-dummy-invalid.wav` and `fuer-elise-prg-dummy-recording.log` under `.local/vice-headless-3.9`.

The verified native run still reports missing headless keymaps, printer charset, unused drive ROMs, the `/dev/null` configuration version warning, and `SaveResourcesOnExit` during shutdown. These did not prevent BASIC execution, valid PCM output, or exit code 0. All agent-owned probe processes exited and were reaped.

## c64bridge and VICE audio findings

[c64bridge's process launcher](../.tools/c64bridge/src/vice/process.ts) inserts `-sounddev dummy` before user arguments. A no-emulator constructor probe verified that `VICE_ARGS` replaces configuration `args`, preserves quoted filenames, and that `VICE_WARP=0` overrides a configured `warp: true`. The [argument parser in the verified official VICE 3.9 release](../.tools/vice-headless-3.9/source/src/cmdline.c) applies resource options left to right, so a later `-sounddev coreaudio` replaces `dummy`. The release download and checksum are recorded in [the startup investigation](vice-startup-investigation.md). This precedence was established from source; runtime audio selection in the installed GTK build was not verified.

For a compatible VICE build, the relevant argument fragment is `-pal +logcolorize -sound -sounddev coreaudio -soundvolume 100`, with `VICE_WARP=false`. The [VICE sound manual](https://vice-emu.sourceforge.io/vice_6.html) identifies `dummy` as silent playback and `coreaudio` as macOS output. WAV recording uses `-soundrecdev wav -soundrecarg /absolute/output.wav -soundrate 44100`; the filename is passed directly. Installed executable strings confirmed CoreAudio and RIFF/WAV recording support.

[The upstream offline VICE runner](../.tools/c64bridge/src/viceRunner.ts) passes `-sounddev wav`, `-soundarg output=...`, `-soundarg bits=16`, and `-soundvol 100`, then gives a SID file to `x64sc`. The direct WAV device selection is supported by the verified 3.9 run above. Its driver expects a filename directly; the later `-soundarg bits=16` replaces the earlier argument, so the runner does not supply the requested output filename. This runner was not used as a verified render path. The dedicated VICE SID player is `vsid`. [The alternative sidplayfp runner](../.tools/c64bridge/src/sidplayRunner.ts) also needs a separately installed command-line executable; the local library package does not provide it.

[The c64_vice tool](../.tools/c64bridge/src/tools/vice.ts) allows `Sound*` resources, so a running emulator can be configured through `SoundDeviceName`, `SoundVolume`, `SoundSampleRate`, `SoundRecordDeviceArg`, and `SoundRecordDeviceName`. Configure playback and the recording filename before enabling recording to avoid reopening and truncating an active output file. These capabilities were confirmed from source, not through a working live monitor in this investigation.

The existing GTK3 installation rejects `-headless`; `-console` still reaches GTK initialization and is not a genuine headless substitute. The successful ordinary desktop launch establishes that its GUI can work in the user's Terminal. See [the VICE startup investigation](vice-startup-investigation.md) and [local setup](local-setup.md) for the separate headless VICE build and exact startup evidence.

## Verify live SID writes

[c64bridge's memory reader](../.tools/c64bridge/src/vice/viceClient.ts) requests binary-monitor memory with side effects disabled and CPU bank zero. In the [SID implementation from the verified official VICE 3.9 release](../.tools/vice-headless-3.9/source/src/sid/sid.c), a monitor peek returns the cached last-written SID register values; [the C64 memory implementation](../.tools/vice-headless-3.9/source/src/c64/c64mem.c) exposes them through bank zero when the current CPU configuration maps I/O. Read `$0001` along with `$D400` through `$D418` to check that assumption. For code that banks out I/O, use [Banks available and Memory get](https://vice-emu.sourceforge.io/vice_13.html) to discover the `io` bank and peek it explicitly; the bridge's public memory operation does not expose a bank selector.

To establish continuing CPU writes, create a non-stopping store checkpoint with `c64_debug`:

```json
{"op":"create_checkpoint","address":"$D400","endAddress":"$D418","stopOnHit":false,"operations":{"execute":false,"load":false,"store":true}}
```

Read its `hitCount` using `get_checkpoint`, resume execution, then read again and remove the checkpoint using `delete_checkpoint`. An increasing count establishes SID-address write activity; the register values and captured PCM establish the resulting pitches and audio. Binary monitor commands pause the CPU briefly, so always resume through the monitor's Exit command after inspection. These live checks require a reachable monitor and were not claimed as completed merely because MCP tool discovery succeeded.
