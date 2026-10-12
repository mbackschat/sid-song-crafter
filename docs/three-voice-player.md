# Reusable three-voice PAL SID exporter

[build-arrangement.ts](../scripts/build-arrangement.ts) compiles an editable score JSON through the pinned c64bridge assembler into a BASIC-loadable PRG, a PSID v2 SID file, expanded assembly, and a register-event manifest. [player-three-voice.asm](../songs/player-three-voice.asm) is the reusable player template. The original [opening example](../songs/fuer-elise-opening.json) and its builder remain available.

```sh
bun scripts/build-arrangement.ts songs/fuer-elise.json
bun scripts/build-arrangement.ts tests/fixtures/three-voice-score.json build/demo demo
```

The CLI accepts `<score.json> [output-directory] [name]`. Output defaults to `build/`; the filename stem defaults to the input filename without `.json`. The four outputs are `<name>.prg`, `<name>.sid`, `<name>.asm`, and `<name>.events.json`. An explicit name accepts letters, numbers, underscores, and hyphens. The TypeScript API is `buildArrangement({ source: string, output?: string, name?: string })`.

## Score contract

This JSON is the current note-and-instrument subset for piano arrangements, not a universal representation of SID music. The exporter targets one MOS8580 at `$D400`, PAL 6569 raster timing, exactly three monophonic voices, and one fixed instrument per voice. Beat values count quarter notes, so a bar of 3/8 occupies 1.5 beats. The tempo is constant. Transcription, repeat expansion, chord reduction, and musical provenance belong in the input score or its importer rather than the assembly player.

```ts
type Instrument = {
  waveform: 16 | 32 | 64;
  attackDecay: number;      // Integer SID register byte, 0..255.
  sustainRelease: number;   // Integer SID register byte, 0..255.
  pulseWidth?: number;      // Integer 0..4095, defaults to 2048.
};
type Score = {
  title: string;
  composer: string;
  quarterBpm: number;
  totalBeats: number;
  tailTicks?: number;       // Integer 1..65535, defaults to 25.
  volume?: number;          // Integer 1..15, defaults to 15.
  voices: [Voice, Voice, Voice];
};
type Voice = {
  instrument: Instrument;
  events: {
    startBeat: number;
    durationBeats: number;
    midi: number | null;
  }[];
};
```

`title` and `composer` accept up to 31 printable ASCII characters because the PSID header reserves 32 bytes including its terminating zero. Tempo and total duration must be positive and finite. Event starts must be nonnegative, durations positive, and MIDI pitches integers 0..127 whose PAL SID frequency fits 16 bits. Each voice's events must be ordered, cannot overlap, and must end within `totalBeats`. A voice may contain no events. Unoccupied time is a rest; `midi: null` represents an explicit rest. Unknown metadata fields are ignored, allowing scores to retain source and reduction evidence.

Waveform 16 selects triangle, 32 sawtooth, and 64 pulse. Pulse width affects only pulse. Attack/decay and sustain/release are raw register bytes, with each rate or level occupying one nibble; see the [SID skill](../skills/c64-sid/SKILL.md). The filter is disabled. There is one global volume; voice balance is controlled by each instrument's envelope. This input does not describe noise instruments, changing waveforms or pulse widths, filter modulation, oscillator sync, ring modulation, or arbitrary frame-level register effects. Those are SID capabilities beyond this input subset, rather than features implemented by this score exporter.

## Timing and ending

The exact PAL clock is `17734475 / 18` Hz and one frame is `312 * 63` clock cycles. Each absolute start and end beat is rounded independently to a PAL frame. This avoids cumulative rounding drift across long scores and tuplets. A note that rounds to zero frames is rejected. Frequencies use equal temperament at A4 = 440 Hz and the exact PAL clock.

For notes lasting at least two frames, GATE goes low 10% of the quantized duration before the end, rounded and limited to one or two frames. A one-frame grace note goes low at its end. At a shared boundary its gate-off write precedes the following note's gate-on write, preserving the grace pitch and the retrigger within PAL's timing limit. Rests issue no pitch or gate-on writes. `totalBeats` determines the score boundary even when all voices finish earlier. After `tailTicks` additional frames, all gates go low, master volume becomes zero, and the player remains finished until initialization.

The SID-native boundary is the ordered register-write stream consumed by the player. The note JSON is one upstream way to produce that stream; SID-native compositions do not need to pass through notes or round-trip through this score format. The stream stores fixed four-byte records `[delayLow, delayHigh, registerOffset, value]`. A delay is measured from the previous register write; simultaneous writes have delay zero. Register offset 255 marks the end. The cursor and countdown are 16 bits, so neither note count nor song duration is limited to 255. Each individual interval between writes must fit 65535 frames. The complete payload must end at or before `$A000`; oversized scores fail before any output is written because the PRG wrapper keeps BASIC ROM visible. The current format uses 16 bytes per sounding note, plus the player and ending, with no pattern compression.

## Calling contract

The SID payload loads at `$1000`. Call `init` at `$1000` with A = 0, then `play` at `$1003` once per PAL frame. The first play call represents tick zero. Both routines return with RTS, clobber A, X and status flags, preserve Y and the entire zero page, and use the caller's stack. They require writable player RAM and visible SID I/O. The stream cursor is an operand modified within player RAM. `init` clears SID registers and resets the cursor, countdown, first-tick state, and `finished` flag, so replay is deterministic. No routine reads write-only SID registers.

The PRG starts at `$0801` with `10 SYS 2064`. Its standalone entry saves processor status and the `$00`/`$01` ports, enables SID I/O, disables interrupts, calls initialization, and waits for both edges of VIC-II raster bit 7 before every play call. It restores the ports and status before returning to BASIC. Playback owns the machine during this wait loop. The PSID v2 header declares PAL, MOS8580, one song, and VBI scheduling; it contains only the callable payload, while the PRG also includes the BASIC wrapper.

## Manifest and verification

The manifest records `title`, `composer`, `target`, `clockHz`, `ticksPerSecond`, `quarterBpm`, `volume`, `scoreTicks`, `totalTicks`, `durationSeconds`, `payloadEndAddress`, and assembly `symbols`. `voices` contains normalized instruments and per-voice compiled events; `events` is the same material flattened by voice. Each event retains `voice`, `midi`, `startBeat`, `durationBeats`, `startTick`, `durationTicks`, `frequencyWord`, and nullable `gateOffTick`. `writes` gives the ordered play-time trace as `{ tick, address, value }`, including the final gate and volume writes. Initialization writes are separate from that trace.

Useful symbols include `init`, `play`, `standalone`, `standalone_return`, `finished`, `first_tick`, `ticks_left_low`, `ticks_left_high`, `stream_read`, `event_stream`, and `event_stream_end`. The operand bytes at `stream_read + 1` and `stream_read + 2` hold the current cursor. `payloadEndAddress` is the first unused byte, rather than the last occupied address.

```sh
bun test tests/fuer-elise.test.ts
PYTHONPATH=.tools/test-deps python3 -m unittest discover -s tests -p 'fuer_elise_cpu_test.py' -v
```

The exporter tests cover over 255 notes, over two minutes, absolute timing, pitch, rests, repeated notes, one-frame grace notes, memory limits, deterministic outputs, and an unrelated arrangement with different tempo, waveform, and metadata. Independent py65 execution checks every SID write for a 300-note arrangement, initial rests longer than 255 frames, stream page crossings, restart, cycle budget, zero-page preservation, and the standalone wrapper's PAL scheduling and return. See the [audio workflow](audio-workflow.md) for separate SID-renderer and native VICE evidence.

[verify_player.py](../scripts/verify_player.py) exposes `verify_callable(manifest, sid_path)` for exact validation of any exported arrangement. It derives pitch, beat timing, articulation and the complete ordered write schedule independently from the manifest's musical events, checks the manifest trace, then runs the actual binary's initialization and every play call through py65. It checks initial instruments, each gate edge including same-frame grace/retrigger writes, cycle budget, finished state, cursor, zero page, restart, and inactivity after the ending. This fills the gap in frame-sampled renderer snapshots, which may omit intermediate register writes or a brief gate edge. The helper uses an installed py65 package or the documented `.tools/test-deps` installation; no `PYTHONPATH` is needed when invoked through the workflow.

```sh
python3 -m unittest discover -s tests -p 'player_trace_test.py' -v
```

These guards corrupt the actual binary to remove a repeated-pitch gate-off, remove a one-frame grace gate-on, and change an initial envelope, and require the verifier to reject each case. They also reject manifest writes that disagree with independently quantized musical events.
