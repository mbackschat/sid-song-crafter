# Headless SID audio workflow

[The renderer](../../scripts/render-sid.cpp) uses pinned libsidplayfp 3.1.1/SIDLite to write PCM16 audio at 44100 Hz without a window: mono for one SID, or stereo with one chip per channel for the supported two-SID profile. Its `.registers.tsv` sidecar records last-written SID register snapshots after each renderer iteration, timestamped by the emulation library. Snapshots are not individual bus writes or one-to-one video frames; use [the CPU audit](../validation/psid-audit.md) for ordered writes. The retained batch argument is `19656` for either clock: [libsidplayfp 3.1.1's `play()` implementation](https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/player.cpp#L241) dispatches that many scheduler events, which need not span that many CPU cycles. The selected C64 model determines emulation timing and pitch; changing the batch size does not retime the song or make snapshot rows video-frame boundaries.

The [audio integration tests](../../tests/render_audio_test.py) verify independent machine-code and ROM-backed BASIC A4, NTSC clock, two-subtune and two-chip fixtures, default and explicit clock/subtune selection, separate chip audibility/routing, the opening Für Elise pitches/onsets and the ending. The clock fixtures check actual PCM pitch and per-VBI counters against elapsed emulation time, including NTSC stereo with both MOS6581 and MOS8580; omitted and explicit PAL renders agree byte for byte, including the single-SID fixture whose source header declares NTSC. The [song guide](../songs/first-song.md) identifies the editable opening excerpt and its PRG/SID exports; [native instrument trials](instrument-trials.md) apply the same renderer to a different driver.

## Pinned library setup

The [Homebrew libsidplayfp package](https://formulae.brew.sh/formula/libsidplayfp) provides the pinned Apple Silicon bottle below. This `arm64_tahoe` package was verified for the local ARM64 macOS 27.0.1 host; other platforms need the matching package. Retain its GPL-2.0-or-later notice, authors and formula.

```sh
mkdir -p .local/downloads
curl --connect-timeout 10 --max-time 60 -fsSL -H 'Authorization: Bearer QQ==' 'https://ghcr.io/v2/homebrew/core/libsidplayfp/blobs/sha256:7e28827526f55a6b86db4ab3f6ec73d8444f0d0c70c1b2c1144928b19d8ce0dc' -o .local/downloads/libsidplayfp-3.1.1.arm64_tahoe.bottle.tar.gz
python3 -c 'import hashlib; from pathlib import Path; assert hashlib.sha256(Path(".local/downloads/libsidplayfp-3.1.1.arm64_tahoe.bottle.tar.gz").read_bytes()).hexdigest() == "7e28827526f55a6b86db4ab3f6ec73d8444f0d0c70c1b2c1144928b19d8ce0dc"'
tar -tf .local/downloads/libsidplayfp-3.1.1.arm64_tahoe.bottle.tar.gz
mkdir -p .local/tools
tar -xf .local/downloads/libsidplayfp-3.1.1.arm64_tahoe.bottle.tar.gz -C .local/tools
mkdir -p .local/bin
c++ -std=c++17 -O2 -Wall -Wextra -Werror -I.local/tools/libsidplayfp/3.1.1/include scripts/render-sid.cpp .local/tools/libsidplayfp/3.1.1/lib/libsidplayfp.a -o .local/bin/render-sid
```

The extracted dynamic library retains an unrelocated `@@HOMEBREW_PREFIX@@` installation ID. Linking the supplied static archive avoids relying on Homebrew relocation. The bottle supplies SIDLite, not reSIDfp or a `sidplayfp` command-line executable. `QQ==` is the public GHCR anonymous-access header for these bottles.

## Renderer contract and API findings

The renderer accepts `INPUT.sid OUTPUT.wav SECONDS [--subtune N] [--voices 1,3] [--clock pal|ntsc] [--assume-sid-model MOS6581|MOS8580] [--rom-dir DIRECTORY]` and permits durations greater than zero through 600 seconds. `--subtune N` selects a one-based subtune within the loaded tune's song count; omission selects the header default. `--clock pal|ntsc` forces the selected C64 model without modifying the input header; omission retains the existing PAL default for compatibility. Options may appear in any order, once each. Zero, out-of-range or malformed subtunes, invalid clock values, duplicate options and unknown options are rejected before creating or truncating the WAV and register sidecar. The console receipt reports the selected clock, subtune, total song count and effective SID model with its declaration/assumption origin. One-SID output remains mono, with the declared chip model honoured and MOS8580 as the fallback. The optional one-SID diagnostic selector retains the named tone voices; its limits are described below. Two-SID output requires a matching rendering clock, explicit PAL or NTSC declaration, and two same-model MOS6581 or MOS8580 chips at `$D400/$D420`. It admits PSID v3 with VBI timing for every subtune, or native RSID v3 with a 124-byte header, zero header load/play/speed fields and zero relocation fields. MUS/PlaySID/BASIC flags remain unsupported for two chips. Native RSID runs its own machine/timer program; its reserved zero speed word is not a VBI declaration. The loaded native profile must agree with libsidplayfp’s R64/CIA metadata, while PSID retains its VBI check. An NTSC dual-SID input therefore requires `--clock ntsc`; omitting the option still selects PAL and rejects the mismatch. Mismatched clocks, other second-chip addresses, malformed or duplicate address declarations, a third chip, mixed chip models and other two-chip timing/version contracts are rejected before output creation. A fixed power-on delay keeps startup reproducible. Output contains exactly the requested number of sample frames rounded to the nearest frame, with a minimum of one; stereo frames contain two interleaved samples. Rebuild the executable after changing its source.

Two-SID stereo uses the documented per-chip `buffers()` API at unity gain: chip 0 is left and chip 1 is right, with no crossfeed or summing. The pinned library's [default stereo matrix](https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/simpleMixer.h) mixes half of each chip into the opposite channel, so this renderer interleaves raw chip buffers instead. Independent 440/660 Hz fixtures and versions with either chip muted verify both channels and the absence of crossfeed; stereo output is not a duplicate of a mono render. The mono mixer path is unchanged. The [native RSID regression evidence](../../evidence/renderer-dual-rsid/compatibility.json) retains seven byte-identical pre/post-change WAV and snapshot comparisons covering existing mono PSID, mono native/BASIC RSID and PAL/NTSC PSID stereo targets. Independent native CIA IRQ fixtures use an 8,192-cycle period and separate 440/660 Hz chip signals to verify timer-driven playback, pitch and routing; [28 renderer tests](../../evidence/renderer-dual-rsid/renderer-tests.txt) pass. Header admission alone does not establish a song’s correct execution; the Ghostbusters case separately verifies its actual speech and music scheduling.

The mono snapshot header remains `time_ms\tregisters_hex`. Two-SID snapshots append `registers_sid2_hex`; each chip column contains its own 32 register bytes as hexadecimal. Readers that need two-chip state must use both columns rather than treating the first chip as the whole tune.

Two libsidplayfp integration rules are required:

- Call `tune.selectSong(0)` before `player.load()` for the header default, or `tune.selectSong(N)` for an explicitly validated one-based selection. [`SidTuneInfoImpl`](https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/sidtune/SidTuneInfoImpl.h) starts `currentSong` at zero, and [`psiddrv`](https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/psiddrv.cpp) passes `currentSong - 1` to init. Omitting selection passes `$FF`; a player that ignores A can hide the mistake. [`SidTuneBase::selectSong`](https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/sidtune/SidTuneBase.cpp) falls back to the default for an out-of-range number, so reject an invalid explicit choice before calling it. Independent fixtures for default songs 1 and 2 and explicit choices verify init A, distinct PCM pitches and identical omitted/explicit-default output.
- Treat `getBufSize()` as a sample count in 3.1.1 despite its header's byte description. [The pinned implementation](https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/player.cpp#L591) returns samples. Allocate that many `short` values and check capacity before mixing; dividing by `sizeof(short)` underallocates the buffer.

Measure ending silence using AC energy after subtracting the mean. A constant SIDLite DC offset is not continuing oscillator sound. Host speaker playback is a separate check: the restricted host can reject `afplay` with `AudioQueueStart failed (-66680)` even when file rendering succeeds.

## Render and validate

### Render an explicit unknown-model assumption

For a one-SID source whose model declaration is unknown, pass `--assume-sid-model MOS6581` or `--assume-sid-model MOS8580`. This selects the emulation model without modifying the source header. It is an experimental choice, not recovered authorship metadata. The option rejects concrete model declarations, the `any` declaration, multiple chips, invalid values and duplicates before creating or truncating output. Omission preserves the existing MOS8580 fallback; declared models continue to be honored.

```sh
.local/bin/render-sid .local/research/take-on-me/Take_on_Me.sid build/take-on-me-6581.wav 32 --subtune 1 --clock pal --assume-sid-model MOS6581
```

The console receipt reports the effective model and whether it was declared, assumed or a fallback. Retain that receipt with the source hash and explicit command. The [Take On Me recipe](../../config/listening/take-on-me-models.json) makes the two-model comparison reproducible. The [renderer guards](../../tests/render_audio_test.py) compare each assumed model's PCM against an independently declared fixture, verify unchanged register trajectories and source bytes, and exercise invalid-input output preservation. The [compatibility receipt](../../evidence/renderer-model-assumption/compatibility.json) confirms unchanged default WAV and register-sidecar bytes against the pre-change executable; the renderer suite covers existing clock, subtune and dual-SID contracts.

### Select the source clock

Reference renders must follow the source's declared clock: pass `--clock pal` for PAL and `--clock ntsc` for NTSC. A header declaring unknown or both clocks requires an explicit, documented assumption. The legacy PAL default preserves existing callers; it is not a universal reference choice. Record the selected clock alongside the source hash, chip model and subtune in render provenance and listening recipes.

For a supported single- or dual-SID NTSC reference, use:

```sh
.local/bin/render-sid SOURCE.sid build/reference-ntsc.wav 6 --clock ntsc --subtune 1
```

The clock option changes emulation speed and oscillator pitch according to that model. It does not retime or retune a PAL composition for NTSC. Composition targets require their own timing, tuning and export validation; see the [PAL/NTSC portability requirement](../PLAN.md#required-palntsc-portability). The renderer supports both clocks for one SID and the bounded two-SID profile above.

### Render BASIC RSID with C64 ROMs

RSID files marked as requiring BASIC need the real C64 interpreter and KERNAL. Without these ROMs, libsidplayfp can report successful playback while producing only the SIDLite DC offset. The renderer therefore rejects BASIC compatibility without an explicit `--rom-dir DIRECTORY`, before creating or truncating outputs. Other inputs retain the existing ROM-free path unless the option is supplied.

The directory must contain `kernal-901227-03.bin` (8192 bytes), `basic-901226-01.bin` (8192 bytes) and `chargen-901225-01.bin` (4096 bytes), as provided by the local VICE source tree. Missing files, wrong sizes and ROM contents unrecognized by libsidplayfp are rejected before output creation. The renderer calls `setRoms()` before loading the tune and includes the library's ROM descriptions in its console receipt. Keep ROM assets local; supplying this option does not alter the SID input.

```sh
.local/bin/render-sid SOURCE.sid build/basic-reference.wav 80 --clock ntsc --subtune 1 --rom-dir .tools/vice-headless-3.9/source/data/C64
```

Choose the clock and duration from the source; this example's NTSC selection is not a general BASIC requirement. Preserve machine startup in a raw capture, then document any verified trim in the listening copy. The independent tokenized BASIC regression fixture uses `POKE` statements to produce a measured 440 Hz triangle through the real interpreter; that audio test runs only when the local ROM files are available. Missing-ROM and malformed-ROM output-preservation guards always run and do not require copyrighted reference tunes.

### Select a subtune

Pass `--subtune 1` for an explicit first subtune, or another valid one-based number for the desired song. Omitting the option retains default playback. For example, after obtaining the pinned Rambo reference through [local setup](../setup/local-setup.md):

```sh
.local/bin/render-sid .local/rambo-source.sid build/rambo-loader-first.wav 6 --subtune 1
```

Use the selected subtune in render provenance and listening recipes. Subtune selection can be combined with one-SID diagnostics, for example `--subtune 1 --voices 1,3`; the diagnostic's oscillator/filter limitations still apply.

### Diagnostic voice selection

For a single SID, append `--voices 1`, `--voices 3` or `--voices 1,3` to compare selected tone voices. `--voices 1,2,3` agrees with default playback; `--voices none` suppresses the three tone voices but does not mute the separate volume-digi channel. Invalid lists, duplicate voices and two-chip use are rejected before output files are created.

This uses [libsidplayfp 3.1.1's actual mute implementation](https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/sidemu.cpp): it masks unselected voices' control writes with `$0e`, clearing GATE and waveform bits before synthesis. It is not output-only muting: muted envelopes, waveform/noise state and the filter's input can change. The implementation uses `true` to mute despite the public header's opposite wording. The `.registers.tsv` snapshots retain the original register-write shadow, so identical snapshots do not prove identical internal state after muting.

Use this as a bounded listening diagnostic after checking oscillator coupling, SID reads, shared-filter routing and volume/sample techniques. Do not assume isolated files add back to the original or use the option as a faithful solo for ring/sync-dependent instruments. The [DRAX fragment study](../research/composition/fuer-elise-reference.md) checks its particular independence assumptions and keeps the full mix as the authority. Independent three-pitch fixtures verify actual voice selection, quiet tone-only `none`, unchanged default output and argument rejection.

Post-call register equality does not establish sample-identical audio between separately compiled arrangements: changed player workload can shift otherwise identical writes within a frame. The [Axel F kick trial](../../songs/axel-f/arrangement-review.md#post-call-equality-does-not-isolate-an-audio-contribution) measured this and used a same-SID muted/unmuted pair after checking the independence constraints above. Keep whole-arrangement comparisons distinct from an isolated contribution test.

### Playback checks

After [building the opening excerpt](../songs/first-song.md):

```sh
python3 tests/render_audio_test.py
.local/bin/render-sid build/fuer-elise-opening.sid build/fuer-elise-opening.wav 3.2
ffprobe -v error -show_entries stream=codec_name,sample_rate,channels,bits_per_sample -show_entries format=duration -of json build/fuer-elise-opening.wav
```

The A4 oracle uses a hand-coded PSID independent of the song compiler. Opening-excerpt checks verify actual PCM pitches within 3 Hz, SID frequency words within 0.1 Hz, onsets within one PAL frame and a silent ending with zero final volume. The excerpt passes these checks through both SIDLite and headless VICE/reSID MOS8580. This validates playback and the tested pitches, not expressive instrument quality or physical SID behaviour.

## Full PRG execution in headless VICE

Use the [genuine headless VICE build](../setup/vice-startup-investigation.md) and writable configuration/state directories. `loadbasic` updates BASIC pointers, and lowercase `keybuf run\n` supplies the BASIC keyword through [VICE's ASCII-to-PETSCII keyboard parser](../../.tools/vice-headless-3.9/source/src/kbdbuf.c). Setting the program counter directly would bypass this boot check.

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

- Select `-sounddev wav -soundarg /absolute/output.wav -soundrate 44100` for offline capture, and disable warp with `+warp`. [VICE 3.9's dummy sound driver](../../.tools/vice-headless-3.9/source/src/arch/shared/sounddrv/sounddummy.c) has no initialization callback; [sound_open](../../.tools/vice-headless-3.9/source/src/sound.c) sets channel count inside that callback. Dummy playback combined with WAV recording can therefore produce an empty zero-channel header. [The WAV driver](../../.tools/vice-headless-3.9/source/src/arch/shared/sounddrv/soundwav.c) initializes output correctly.
- A deliberately reached cycle limit returns status 1 and `cycle limit reached.` in VICE 3.9. Accept it only when the expected entry breakpoint, finalized nonempty WAV and capture duration also pass. It is different from a monitor-driven successful exit and does not prove a return to BASIC.
- [c64bridge's process launcher](../../.tools/c64bridge/src/vice/process.ts) inserts `-sounddev dummy` before user arguments. The pinned [VICE argument parser](../../.tools/vice-headless-3.9/source/src/cmdline.c) applies options left to right, so later device options replace it. `VICE_ARGS` replaces configured `args`; `VICE_WARP=0` overrides configured warp.
- For host playback on a compatible macOS build, the device fragment is `-pal +logcolorize -sound -sounddev coreaudio -soundvolume 100`, with warp disabled. Recording uses `-soundrecdev wav -soundrecarg /absolute/output.wav`; configure playback and the output filename before enabling recording so changing resources does not truncate an active file. See [the VICE sound manual](https://vice-emu.sourceforge.io/vice_6.html).
- The pinned [offline VICE runner](../../.tools/c64bridge/src/viceRunner.ts) supplies repeated `-soundarg` values; the later `bits=16` replaces the filename, while the WAV driver expects a filename directly. Use the direct capture command above. SID files require `vsid`; giving one to `x64sc` is not the verified native PRG path. The [sidplayfp runner](../../.tools/c64bridge/src/sidplayRunner.ts) requires a separate executable that the local library package does not supply.

Live sound-resource operations are available in [the bridge tool](../../.tools/c64bridge/src/tools/vice.ts), but require a reachable binary monitor. Runtime CoreAudio selection and live bridge recording have not been verified in the restricted runner. [Local setup](../setup/local-setup.md) explains the separate socket and GTK constraints.

## Verify live SID writes

[c64bridge's memory reader](../../.tools/c64bridge/src/vice/viceClient.ts) requests side-effect-free binary-monitor memory in CPU bank zero. [VICE's SID peek](../../.tools/vice-headless-3.9/source/src/sid/sid.c) returns cached last-written register values, while [CPU bank mapping](../../.tools/vice-headless-3.9/source/src/c64/c64mem.c) exposes them only when `$0001` maps I/O. Read `$0001` with `$D400-$D418`. If the program banks out I/O, use [Banks available and Memory get](https://vice-emu.sourceforge.io/vice_13.html) to find and peek the `io` bank; the bridge's public memory operation does not expose a bank selector.

For continuing CPU write activity, create a non-stopping store checkpoint with `c64_debug`:

```json
{"op":"create_checkpoint","address":"$D400","endAddress":"$D418","stopOnHit":false,"operations":{"execute":false,"load":false,"store":true}}
```

Read `hitCount` using `get_checkpoint`, resume, read again, and remove the checkpoint using `delete_checkpoint`. An increasing count establishes address-write activity; register values and PCM establish its sound. Binary-monitor inspection pauses the CPU briefly, so resume through the monitor's Exit command. Tool discovery alone does not establish live emulator control.
