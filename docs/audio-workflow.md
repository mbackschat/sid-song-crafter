# Headless SID audio workflow

[The renderer](../scripts/render-sid.cpp) uses pinned libsidplayfp 3.1.1/SIDLite to write mono PCM16 audio at 44100 Hz without a window. Its `.registers.tsv` sidecar records last-written SID register snapshots after each renderer iteration, timestamped by the emulation library. Snapshots are not individual bus writes or one-to-one PAL frames; use [the CPU audit](psid-audit.md) for ordered writes.

The [audio integration tests](../tests/render_audio_test.py) verify independent A4 fixtures, default-subtune selection, the opening Für Elise pitches/onsets and the ending. The [song guide](first-song.md) identifies the editable opening excerpt and its PRG/SID exports; [native instrument trials](instrument-trials.md) apply the same renderer to a different driver.

## Pinned library setup

The [Homebrew libsidplayfp package](https://formulae.brew.sh/formula/libsidplayfp) provides the pinned Apple Silicon bottle below. This `arm64_tahoe` package was verified for the local ARM64 macOS 27.0.1 host; other platforms need the matching package. Retain its GPL-2.0-or-later notice, authors and formula.

```sh
curl --connect-timeout 4 --max-time 20 -fsSL -H 'Authorization: Bearer QQ==' 'https://ghcr.io/v2/homebrew/core/libsidplayfp/blobs/sha256:7e28827526f55a6b86db4ab3f6ec73d8444f0d0c70c1b2c1144928b19d8ce0dc' -o /private/tmp/c64-sid-libsidplayfp-3.1.1.arm64_tahoe.bottle.tar.gz
python3 -c 'import hashlib; from pathlib import Path; assert hashlib.sha256(Path("/private/tmp/c64-sid-libsidplayfp-3.1.1.arm64_tahoe.bottle.tar.gz").read_bytes()).hexdigest() == "7e28827526f55a6b86db4ab3f6ec73d8444f0d0c70c1b2c1144928b19d8ce0dc"'
tar -tf /private/tmp/c64-sid-libsidplayfp-3.1.1.arm64_tahoe.bottle.tar.gz
mkdir -p .local/tools
tar -xf /private/tmp/c64-sid-libsidplayfp-3.1.1.arm64_tahoe.bottle.tar.gz -C .local/tools
mkdir -p .local/bin
c++ -std=c++17 -O2 -Wall -Wextra -Werror -I.local/tools/libsidplayfp/3.1.1/include scripts/render-sid.cpp .local/tools/libsidplayfp/3.1.1/lib/libsidplayfp.a -o .local/bin/render-sid
```

The extracted dynamic library retains an unrelocated `@@HOMEBREW_PREFIX@@` installation ID. Linking the supplied static archive avoids relying on Homebrew relocation. The bottle supplies SIDLite, not reSIDfp or a `sidplayfp` command-line executable. `QQ==` is the public GHCR anonymous-access header for these bottles.

## Renderer contract and API findings

The renderer accepts `INPUT.sid OUTPUT.wav SECONDS`, forces PAL, supports one SID, and permits durations greater than zero through 600 seconds. It honours the SID's model preference, defaulting to MOS8580, and uses a fixed power-on delay for reproducibility. Output has exactly the requested sample count rounded to the nearest sample, with a minimum of one. Rebuild the executable after changing its source.

Two libsidplayfp integration rules are required:

- Call `tune.selectSong(0)` before `player.load()` to select the header's default subtune. [`SidTuneInfoImpl`](https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/sidtune/SidTuneInfoImpl.h) starts `currentSong` at zero, and [`psiddrv`](https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/psiddrv.cpp) passes `currentSong - 1` to init. Omitting selection passes `$FF`; a player that ignores A can hide the mistake. Independent fixtures for default songs 1 and 2 guard this contract.
- Treat `getBufSize()` as a sample count in 3.1.1 despite its header's byte description. [The pinned implementation](https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/player.cpp#L591) returns samples. Allocate that many `short` values and check capacity before mixing; dividing by `sizeof(short)` underallocates the buffer.

Measure ending silence using AC energy after subtracting the mean. A constant SIDLite DC offset is not continuing oscillator sound. Host speaker playback is a separate check: the restricted host can reject `afplay` with `AudioQueueStart failed (-66680)` even when file rendering succeeds.

## Render and validate

After [building the opening excerpt](first-song.md):

```sh
python3 tests/render_audio_test.py
.local/bin/render-sid build/fuer-elise-opening.sid build/fuer-elise-opening.wav 3.2
ffprobe -v error -show_entries stream=codec_name,sample_rate,channels,bits_per_sample -show_entries format=duration -of json build/fuer-elise-opening.wav
```

The A4 oracle uses a hand-coded PSID independent of the song compiler. Opening-excerpt checks verify actual PCM pitches within 3 Hz, SID frequency words within 0.1 Hz, onsets within one PAL frame and a silent ending with zero final volume. The excerpt passes these checks through both SIDLite and headless VICE/reSID MOS8580. This validates playback and the tested pitches, not expressive instrument quality or physical SID behaviour.

## Full PRG execution in headless VICE

Use the [genuine headless VICE build](vice-startup-investigation.md) and writable configuration/state directories. `loadbasic` updates BASIC pointers, and lowercase `keybuf run\n` supplies the BASIC keyword through [VICE's ASCII-to-PETSCII keyboard parser](../.tools/vice-headless-3.9/source/src/kbdbuf.c). Setting the program counter directly would bypass this boot check.

The following monitor file checks the opening PRG's entry, wrapper return, restored CPU ports, finished state, SID registers and return to BASIC:

```sh
mkdir -p .local/vice-headless-3.9/config .local/vice-headless-3.9/state/vice
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
env -u DISPLAY -u WAYLAND_DISPLAY XDG_CONFIG_HOME="$PWD/.local/vice-headless-3.9/config" XDG_STATE_HOME="$PWD/.local/vice-headless-3.9/state" .tools/vice-headless-3.9/build/src/x64sc -config /dev/null -directory /Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice -pal +warp -sounddev wav -soundarg "$PWD/build/fuer-elise-vice.wav" -sidenginemodel resid8580 -soundrate 44100 +logcolorize -limitcycles 10000000 -initbreak ready -monlogname "$PWD/.local/vice-headless-3.9/fuer-elise-prg-monitor.log" -monlog -moncommands "$PWD/.local/vice-headless-3.9/fuer-elise-prg.mon"
```

These addresses belong to the current opening player: `$0810` is its entry, `$083C` its wrapper RTS, `$1078-$107A` its event/tick/finished state and `$A474` the BASIC return point. Consult generated `build/fuer-elise-opening.asm` and `.events.json` when changing the player. A successful monitor `quit` produces exit status zero. Use a subprocess deadline as well as the emulated-cycle limit.

The raw VICE WAV includes machine bootstrap and may contain a startup transient; align the musical portion before comparing it with a SID render. Runtime warnings about unused keymaps/printer assets or the `/dev/null` configuration version do not by themselves invalidate a completed CPU and PCM check.

## VICE audio and bridge rules

- Select `-sounddev wav -soundarg /absolute/output.wav -soundrate 44100` for offline capture, and disable warp with `+warp`. [VICE 3.9's dummy sound driver](../.tools/vice-headless-3.9/source/src/arch/shared/sounddrv/sounddummy.c) has no initialization callback; [sound_open](../.tools/vice-headless-3.9/source/src/sound.c) sets channel count inside that callback. Dummy playback combined with WAV recording can therefore produce an empty zero-channel header. [The WAV driver](../.tools/vice-headless-3.9/source/src/arch/shared/sounddrv/soundwav.c) initializes output correctly.
- A deliberately reached cycle limit returns status 1 and `cycle limit reached.` in VICE 3.9. Accept it only when the expected entry breakpoint, finalized nonempty WAV and capture duration also pass. It is different from a monitor-driven successful exit and does not prove a return to BASIC.
- [c64bridge's process launcher](../.tools/c64bridge/src/vice/process.ts) inserts `-sounddev dummy` before user arguments. The pinned [VICE argument parser](../.tools/vice-headless-3.9/source/src/cmdline.c) applies options left to right, so later device options replace it. `VICE_ARGS` replaces configured `args`; `VICE_WARP=0` overrides configured warp.
- For host playback on a compatible macOS build, the device fragment is `-pal +logcolorize -sound -sounddev coreaudio -soundvolume 100`, with warp disabled. Recording uses `-soundrecdev wav -soundrecarg /absolute/output.wav`; configure playback and the output filename before enabling recording so changing resources does not truncate an active file. See [the VICE sound manual](https://vice-emu.sourceforge.io/vice_6.html).
- The pinned [offline VICE runner](../.tools/c64bridge/src/viceRunner.ts) supplies repeated `-soundarg` values; the later `bits=16` replaces the filename, while the WAV driver expects a filename directly. Use the direct capture command above. SID files require `vsid`; giving one to `x64sc` is not the verified native PRG path. The [sidplayfp runner](../.tools/c64bridge/src/sidplayRunner.ts) requires a separate executable that the local library package does not supply.

Live sound-resource operations are available in [the bridge tool](../.tools/c64bridge/src/tools/vice.ts), but require a reachable binary monitor. Runtime CoreAudio selection and live bridge recording have not been verified in the restricted runner. [Local setup](local-setup.md) explains the separate socket and GTK constraints.

## Verify live SID writes

[c64bridge's memory reader](../.tools/c64bridge/src/vice/viceClient.ts) requests side-effect-free binary-monitor memory in CPU bank zero. [VICE's SID peek](../.tools/vice-headless-3.9/source/src/sid/sid.c) returns cached last-written register values, while [CPU bank mapping](../.tools/vice-headless-3.9/source/src/c64/c64mem.c) exposes them only when `$0001` maps I/O. Read `$0001` with `$D400-$D418`. If the program banks out I/O, use [Banks available and Memory get](https://vice-emu.sourceforge.io/vice_13.html) to find and peek the `io` bank; the bridge's public memory operation does not expose a bank selector.

For continuing CPU write activity, create a non-stopping store checkpoint with `c64_debug`:

```json
{"op":"create_checkpoint","address":"$D400","endAddress":"$D418","stopOnHit":false,"operations":{"execute":false,"load":false,"store":true}}
```

Read `hitCount` using `get_checkpoint`, resume, read again, and remove the checkpoint using `delete_checkpoint`. An increasing count establishes address-write activity; register values and PCM establish its sound. Binary-monitor inspection pauses the CPU briefly, so resume through the monitor's Exit command. Tool discovery alone does not establish live emulator control.
