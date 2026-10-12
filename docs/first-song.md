# First song: Für Elise opening excerpt

This is a short monophonic arrangement of Beethoven's WoO 59, using voice 1 of one SID. It contains the two sixteenth-note pickup notes, the six sixteenths in the first complete bar, and the following A4 eighth. Accompaniment, pedal, later phrases, and the remainder of that measure are excluded. It plays once and ends; it is not the complete composition.

## Editable source and provenance

- [fuer-elise-opening.json](../songs/fuer-elise-opening.json) holds the note names, durations in sixteenths, tempo, articulation, instrument, and provenance.
- [player.asm](../songs/player.asm) holds the small assembly player and standalone C64 wrapper.
- [build-song.ts](../scripts/build-song.ts) quantizes absolute note boundaries, creates tables, assembles the program, and exports the SID file.
- [music.test.ts](../tests/music.test.ts) guards the score, pitch, timing, binary/header structure, and deterministic build.
- [music_cpu_test.py](../tests/music_cpu_test.py) executes the assembled program with an independent 6502 interpreter.

The note list was entered manually and checked on 2026-10-12 against the [Mutopia typesetter's published LilyPond source](https://raw.githubusercontent.com/MutopiaProject/MutopiaProject/master/ftp/BeethovenLv/WoO59/fur_Elise_WoO59/fur_Elise_WoO59.ly), opening of the upper staff. The [Mutopia entry](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=931) identifies Breitkopf & Härtel, 1888, as its source, Stelios Samelis as maintainer, and the typesetting as Public Domain. This check used the published transcription, not a historical score scan. Beethoven's underlying composition is public domain; no MIDI file, recording, or score image was incorporated. Quarter note = 72 matches the typesetter's hidden MIDI tempo and is retained as an arrangement choice.

| Passage | Pitches | Durations |
| --- | --- | --- |
| Pickup | E5, D#5 | Two sixteenths |
| First bar, 3/8 | E5, D#5, E5, B4, D5, C5 | Six sixteenths |
| Start of next bar | A4 | One eighth |

## Build and verify

The build requires Bun and the existing c64bridge checkout at the [recorded revision](research/tools/skills-and-integrations.md). It imports only that checkout's assembler, not its SID score compiler or MCP server. No standalone assembler was installed. Bun 1.4.3 was used for the local build and tests; Python 3.9 or newer and uv are needed only for the CPU tests. Python test code uses the standard library's `unittest` with [py65 1.2.0](https://pypi.org/project/py65/1.2.0/), a BSD-licensed 6502 interpreter.

From the repository root:

```sh
bun scripts/build-song.ts
bun test tests/music.test.ts
```

Install the pinned CPU test dependency locally. The direct wheel path also works when uv cannot resolve the package index in the restricted session. The checksum command fails on a mismatch; install only after it succeeds.

```sh
mkdir -p .local/downloads
curl --fail --location --max-time 30 https://files.pythonhosted.org/packages/f6/3d/7171f8401bb3cf058d233af314d3e314a348488bd22b2143b3591566a172/py65-1.2.0-py2.py3-none-any.whl -o .local/downloads/py65-1.2.0-py2.py3-none-any.whl
python3 -c 'import hashlib, pathlib; p = pathlib.Path(".local/downloads/py65-1.2.0-py2.py3-none-any.whl"); assert hashlib.sha256(p.read_bytes()).hexdigest() == "8e51f149647f2c2b44e5eb54350057771ccaef97f5f3d593fa3737e44c1ce4b7", "py65 wheel checksum mismatch"'
uv --cache-dir .local/uv-cache pip install --no-deps --target .tools/test-deps .local/downloads/py65-1.2.0-py2.py3-none-any.whl
PYTHONPATH=.tools/test-deps python3 -m unittest discover -s tests -p 'music_cpu_test.py' -v
```

The wheel digest was checked against the [official PyPI release metadata](https://pypi.org/pypi/py65/1.2.0/json). Generated files and local dependencies are kept outside the editable song sources. Tests use temporary output directories; CPU tests also rebuild the normal output before execution.

The build writes `build/fuer-elise-opening.prg`, `build/fuer-elise-opening.sid`, the fully generated assembly, and an event manifest with addresses and timing. These outputs are reproducible from the two song sources and build script; preserve those editable files when copying the delivery files.

## Playback contract

Target: PAL 6569 timing, one MOS8580 at `$D400`, A4 = 440 Hz. Frequency words use 985248.611111 Hz and scheduling uses 312 × 63 CPU cycles per frame, following [libsidplayfp's PAL clock constants](https://github.com/libsidplayfp/libsidplayfp/blob/master/src/c64/c64.cpp) and the [timing guide](research/sid/playback-and-timing.md). This is approximately 50.124573 calls per second. Independently rounding each duration would introduce drift, so the build rounds cumulative absolute boundaries instead.

The chosen sound is triangle, attack/decay `$06`, sustain/release `$41`, master volume 15, with no filter. GATE drops two ticks before each note ends, leaving approximately 39.9 ms before the next onset. After the final A, a 25-frame silent tail precedes master volume zero. Total scheduling length is 129 PAL frames, approximately 2.574 seconds from the first play call.

For a C64 program, load `fuer-elise-opening.prg` at its embedded `$0801` address and `RUN`; its BASIC stub calls `SYS 2064` (`$0810`). The wrapper exposes I/O, disables maskable interrupts, initializes the player, and polls both edges of `$D011` raster bit 7 to make one play call per frame. It restores processor-port direction, processor-port value, and saved flags before returning to BASIC. It takes exclusive CPU control during the excerpt; it does not install an IRQ or require a host playback loop. PAL is required for its intended pitch and tempo.

For a SID player, the PSID v2NG header requests PAL, MOS8580, one subtune, and VBI playback. The music payload starts at `$1000`; call init at `$1000` with A = 0, then play at `$1003` once per PAL frame. Init and play return with `RTS`. They clobber A, X, and flags, preserve Y, use no zero page, require visible I/O and a normal working stack, and do not modify interrupts or memory banking. Play becomes a silent no-op after completion; another init restarts the excerpt. The manifest records the exact payload addresses for each build.

The driver accepts at most 254 source notes/rests plus the final tail. Each quantized event fits in 1–255 ticks and must exceed the configured release gap; total length can exceed 255 ticks. A JSON `null` pitch is an explicit rest. Invalid pitch text fails rather than producing a fallback note. Only the triangle instrument is supported by this first arrangement.

## Verification evidence

Independent fixtures verify the nine-note transcription, sixteenth/eighth timing, PAL pitch words, gate-off schedule, header flags and addresses, payload identity, longer source handling, rejection of invalid input, and deterministic output bytes.

The py65 tests execute the assembled bytes and verify initialization from dirty state, note order, durations, release edges, a nonlooping silent end, restart, repeated-note retriggering, explicit rests, and events beyond 255 total ticks. They also execute the standalone wrapper with a CPU-cycle-derived raster input and verify exactly one play call per PAL frame, stack balance, and restored ports/flags. Callable play paths execute in fewer than 250 modeled CPU cycles in these tests. This functional 6502 check does not model VIC-II bus contention, SID envelopes, ROM execution, or hardware interrupts; it does not establish a measured real-C64 CPU budget.

Native VICE startup and audible playback are tracked in [local setup](local-setup.md). Independent SID-to-WAV rendering is described in [the audio workflow](audio-workflow.md). The CPU tests alone do not establish envelope quality, audible articulation, or physical-SID compatibility.
