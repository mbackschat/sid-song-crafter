# Source-code studies

## Choose evidence for a trace-and-recreate study

Read an instrument's source language beside the executed writes, then implement the smallest mechanism that explains the liked passage with editable notes and parameters. The [executed-program procedure](sid-program-analysis.md) owns reference identity, instruction/data tracing, controlled interventions and validation. The routes below supply names and contracts for interpreting that evidence; [composer studies](../composers/README.md) retain the accounts of how the composers worked, and the [composition-tool assessment](composition-tools.md) owns backend selection.

Primary files and repository paths checked on 2026-10-13:

| Study task | Source/manual and status | Useful contract to follow | Connect it to a reconstruction |
| --- | --- | --- | --- |
| Learn a composer's original command language | Galway's [Rambo loader source](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/rambload.asm) and [Ocean assembler notes](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/ocean_assembler_directives.txt), revision `a458a3687e27a63647bbe41968094f0e6d0965a0`. The [composer-owned README](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/README.md) identifies original music/player sources. The loader header limits this file to loading music and an SSI variant. | `Pulse`, `Freq` and `Chord` dispatch to state-loading routines; `call0` saves a return address, while `code0` enters a 6502 routine through an indirect jump with a prepared return. The assembler notes define `ENT` as execution after transfer and expand `ADD`/`SUB` into carry setup plus arithmetic. | Locate the command and state update behind a traced pulse/pitch change. Recreate a short stateful instrument separately from the tune's phrase calls. Preserve assembler expansions when comparing instruction addresses; source availability alone does not match this variant to every released Rambo SID. |
| Learn documented table timing with editable input | SID Factory II's [Driver 11 notes](https://github.com/Chordian/sidfactory2/blob/d6852faea2f8929df30e6f2ce008f93d974637d3/dist/documentation/notes_driver11.txt) and [editable music directory](https://github.com/Chordian/sidfactory2/tree/d6852faea2f8929df30e6f2ce008f93d974637d3/SIDFactoryII/music), revision `d6852faea2f8929df30e6f2ce008f93d974637d3`. These are maintained driver documentation and `.sf2` workfiles, including named Driver 11 arpeggio, filter and tie-note tests. They are a driver-family learning corpus, not an original workfile for an unrelated historical SID. | Wave-table pitch `$00–$7F` is relative to the sequence note; `$80–$DF` selects absolute semitones. Pulse rows encode width or addition plus a frame count. Instrument flag `$08` preserves the pulse program on note-on unless the instrument is explicitly selected. Driver versions change commands and restart behavior. | Open a test/workfile, retain its loaded driver version, and predict the writes before export. Compare a repeated note with an explicit instrument selection to test pulse continuation. Build an original instrument using the same timing contract; verify its exported driver rather than assuming another editor's rows advance identically. |
| Follow recovered historical effect routines | The [Cybernoid II listing](https://github.com/realdmx/c64_6581_sid_players/blob/f215174fc4c983674808fcd47bc506f96b3d2d04/Tel_Jeroen_MON/Tel_Jeroen_Cybernoid2.asm), revision `f215174fc4c983674808fcd47bc506f96b3d2d04`, credits Tel's music and Deenen's dated player. Treat it as a recovered/converted listing: the [maintainer](https://github.com/realdmx/c64_6581_sid_players/blob/f215174fc4c983674808fcd47bc506f96b3d2d04/README.md) describes mixed recovered and reverse-engineered material converted to ACME, with some build cleanup still needed. | Comments identify pitch arpeggio, vibrato and glide routines. Eight-byte sound records name pulse-high, waveform, AD, SR, filter-count and three effects fields, with separately named bass, bass-drum and snare records. These provide concrete data-to-effect routes. | Trace the selected sound index, effects fields and delay/counter state into the executed frequency/pulse/control stores. Separate sound definitions do not prove that bass and drums share a voice in a chosen phrase; settle that with ordered writes and listening before authoring an original shared-voice instrument. |

A reconstructed disassembly, such as the [attributed Hubbard routine](../composers/hubbard-galway.md#hubbard-composing-with-a-changing-synthesis-engine), can explain an algorithm but does not supply the composer's original labels or every omitted feature. Record which kind of source was used, its revision and file digest, and whether code/data correspondence to the selected SID was established. Source comments and manuals generate predictions; the trace settles which path ran, and a controlled audible recreation settles what the mechanism contributes. None of the source routes above has been rebuilt or auditioned in this inspection.

## MiniPlayer2: from patterns to writes

Read `player.s` with the PRG wrapper and converter. `SetMusicData` patches runtime addresses, so the player needs writable memory and the module's documented alignment. `PlayRoutine` processes shared filter state and the three voice blocks. Pattern decoding selects notes and commands; waveform processing resolves pitch and writes frequency registers; pulse and filter tables progress independently. Optimized zero-page use has explicit tradeoffs. [S11](../sources.md#s11)

The instructive boundary is score → pattern commands → instrument tables → timed register writes. A converter can preserve pitches while changing articulation or losing unsupported effects. The PRG example's IRQ and border-colour profiling make the scheduler/CPU budget visible. [S07](../sources.md#s07)

Suggested exercise: annotate one instrument's gate-off, restart, frequency, waveform, and gate-on sequence across calls. Then trace a repeated note and a rest. This exercise is proposed, not completed with an audio capture.

## reSID: intended interface versus measured silicon

`sid.cc` provides register dispatch and oscillator connections. `envelope.cc` and `envelope.h` model gate transitions, rate counters, exponential decay, and the delay bug; their comments describe measurements through ENV3. `wave.cc` distinguishes chip models and models interactions involving combined waveforms/noise. [S02](../sources.md#s02), [S03](../sources.md#s03), [S21](../sources.md#s21)

Use these as implementation evidence, not as permission to assume that every analogue chip sounds identical. Also distinguish this older reSID tree from the current standalone reSIDfp engine. [S04](../sources.md#s04)

## ChiptuneSAK: score-to-tracker boundaries

The GoatTracker module encodes four-byte pattern rows: note, instrument, command, parameter. Its `GTS5` handling covers both three- and six-voice songs. A particularly important semantic distinction is that the token named `GT_REST` means no new note operation; key-off is a different token. Confusing the two creates unwanted sustained notes. Table pointers and zero-based host arrays also require careful translation. [S12](../sources.md#s12)

Suggested exercise: round-trip a tiny song containing repeated notes, explicit releases, and a tempo change; compare events rather than only file size. MusicXML support listed as proposed work should not be treated as a working importer.

## SIDDump: traces have a sampling boundary

SIDDump combines a limited CPU execution environment with register snapshots and musical interpretation. It is useful for spotting pitch, waveform, pulse-width, and filter changes. It does not establish exact behaviour for every interrupt-driven or multi-SID tune; snapshots can miss several writes within one frame. Configure multispeed interpretation consciously. [S20](../sources.md#s20)

## c64bridge: inspect before trusting generation

The local SIDWAVE compiler constructs three voices, caps frame tables at 255 frames, and emits GATE-on control values throughout the generated frames. Several advertised score concepts exceed what this compiler implements. This is a valuable small implementation to study, but an incomplete basis for complete classical arrangements. Detailed observations and pinned source links are in [the integration assessment](skills-and-integrations.md).
