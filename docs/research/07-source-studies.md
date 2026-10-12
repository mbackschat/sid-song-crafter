# Source-code studies

## MiniPlayer2: from patterns to writes

Read `player.s` with the PRG wrapper and converter. `SetMusicData` patches runtime addresses, so the player needs writable memory and the module's documented alignment. `PlayRoutine` processes shared filter state and the three voice blocks. Pattern decoding selects notes and commands; waveform processing resolves pitch and writes frequency registers; pulse and filter tables progress independently. Optimized zero-page use has explicit tradeoffs. [S11](sources.md#s11)

The instructive boundary is score → pattern commands → instrument tables → timed register writes. A converter can preserve pitches while changing articulation or losing unsupported effects. The PRG example's IRQ and border-colour profiling make the scheduler/CPU budget visible. [S07](sources.md#s07)

Suggested exercise: annotate one instrument's gate-off, restart, frequency, waveform, and gate-on sequence across calls. Then trace a repeated note and a rest. This exercise is proposed, not completed with an audio capture.

## reSID: intended interface versus measured silicon

`sid.cc` provides register dispatch and oscillator connections. `envelope.cc` and `envelope.h` model gate transitions, rate counters, exponential decay, and the delay bug; their comments describe measurements through ENV3. `wave.cc` distinguishes chip models and models interactions involving combined waveforms/noise. [S02](sources.md#s02), [S03](sources.md#s03), [S21](sources.md#s21)

Use these as implementation evidence, not as permission to assume that every analogue chip sounds identical. Also distinguish this older reSID tree from the current standalone reSIDfp engine. [S04](sources.md#s04)

## ChiptuneSAK: score-to-tracker boundaries

The GoatTracker module encodes four-byte pattern rows: note, instrument, command, parameter. Its `GTS5` handling covers both three- and six-voice songs. A particularly important semantic distinction is that the token named `GT_REST` means no new note operation; key-off is a different token. Confusing the two creates unwanted sustained notes. Table pointers and zero-based host arrays also require careful translation. [S12](sources.md#s12)

Suggested exercise: round-trip a tiny song containing repeated notes, explicit releases, and a tempo change; compare events rather than only file size. MusicXML support listed as proposed work should not be treated as a working importer.

## SIDDump: traces have a sampling boundary

SIDDump combines a limited CPU execution environment with register snapshots and musical interpretation. It is useful for spotting pitch, waveform, pulse-width, and filter changes. It does not establish exact behaviour for every interrupt-driven or multi-SID tune; snapshots can miss several writes within one frame. Configure multispeed interpretation consciously. [S20](sources.md#s20)

## c64bridge: inspect before trusting generation

The local SIDWAVE compiler constructs three voices, caps frame tables at 255 frames, and emits GATE-on control values throughout the generated frames. Several advertised score concepts exceed what this compiler implements. This is a valuable small implementation to study, but an incomplete basis for complete classical arrangements. Detailed observations and pinned source links are in [the integration assessment](11-skills-and-integrations.md).
