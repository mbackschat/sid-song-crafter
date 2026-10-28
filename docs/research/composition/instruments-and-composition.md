# Instruments and composition

## Compose for available voices

Start with melody, bass, and an accompaniment role. A SID voice plays one oscillator pitch at a time; a tracker arpeggio creates an impression of harmony by rapidly changing pitch. It does not sustain several independent notes. Plan which notes must overlap before selecting instruments.

For a piano adaptation, preserve melody, harmonic bass, and phrase rhythm first. Reduce interior chord notes or turn them into broken chords when three voices are insufficient. Use a second chip to preserve musically important overlap, rather than adding constant doubling by default. These are arrangement recommendations, not hardware requirements.

## Scores are written per voice, not per instrument part

The masters' players do not map instrument parts onto voices automatically. Each physical voice runs its own sequence, and a note in that sequence selects an instrument record that the driver executes on that voice. Deciding which voice carries which musical line is the composer's work, done while writing the data.

The documented working methods fit this. A keyboard, piano or paper was where ideas came from; entry into the C64 was typed per-voice data. Hubbard names keyboard experimentation, paper notation and byte editing in a machine-code monitor ([Hubbard](../composers/hubbard-galway.md#hubbard-composing-with-a-changing-synthesis-engine)). Galway wrote music commands in assembler source and reassembled to audition each change ([Galway](../composers/hubbard-galway.md)). Tel took ideas from the piano and entered notes, rests and sounds in assembler; Hülsbeck previewed melodies on an ESQ-1 and entered data through a monitor before writing Soundmonitor ([Hülsbeck and Tel](../composers/huelsbeck-tel.md)). Daglish's staff notation was first typed in by Crowther as letter names and durations ([Daglish](../composers/follin-daglish.md)). Soundmonitor's manual describes keyboard playing and recording, but this project has not established which voice receives recorded notes.

The executed players show the same structure: Galway's loader keeps a call/loop stack per voice, and our Rambo export gives each voice its own cursor into the program graph ([Rambo graph player](../../workflows/decoded-song-workflow.md#rambo-symbolic-graph-player)). The instrument a note selects is not independent of its voice: Monty shares a pulse-width record between voices while delay and direction stay per voice, and the Shades melody voice also owns filter triggering ([instruments as programs](instruments-as-programs.md#what-the-masters-make-concrete)). Composers also allocated deliberately: Hubbard fills a melodic rest with another function on the same channel, and Tel's arpeggios free two voices while percussion precedes bass on a third.

Represent allocation in this project as an explicit role → voice decision in the owning arrangement. The [Für Elise reduction policy](../../songs/fuer-elise-score.md#three-voice-arrangement-policy) and [multitrack audition projection](../../workflows/song-workflow.md#prepare-a-multitrack-score-audition) are narrow automatic reducers from source parts to three voices; they record omitted and shortened notes but do not reproduce a master's allocation choices. For two chips, follow the [dual-SID mapping contract](../sid/dual-sid.md#plan-the-sound-hardware-and-the-mix-together).

## An instrument is a program over time

Trackers commonly separate waveform/note, pulse-width, and filter tables from song patterns. A row selects an instrument and pitch; the player continues updating its tables between rows. A SID “wavetable” in this tradition is a sequence of oscillator-control operations, not a table of PCM samples. GoatTracker documents this organization; MIDIbox's author explains it through worked register sequences. [S08](../sources.md#s08), [S09](../sources.md#s09)

| Desired sound | Starting experiment | What to inspect |
| --- | --- | --- |
| Soft lead | Triangle, moderate attack, controlled release | Phrase endings and envelope overlap |
| Plucked accompaniment | Pulse or triangle, short decay, low sustain | Consistent attack on repeated notes |
| Bass | Pulse, restrained width modulation | Fundamental stability and mix balance |
| Percussive accent | Brief noise/tonal sequence with pitch movement | Length, clicks, and interference with melody |
| Bell-like effect | Triangle ring modulation | Fixed oscillator relationship and voice cost |

These are original experiment plans, not verified instrument presets. Save every successful experiment with its player version and clock.

## Shared controls require ownership

Filter cutoff, resonance, routing, and master volume are chip-wide resources. Assign one controller for their automation; independently written voice macros can overwrite each other. Furnace explicitly documents shared-parameter priority and model-specific SID behaviour. Its C64 system notes are useful even when choosing another editor. [S10](../sources.md#s10)

Master volume is not per-voice expression. Sustain changes are comparatively coarse and interact with the envelope. For musical dynamics, combine arrangement density, timbre, envelope choices, and deliberate filter movement.

## Articulation comes before ornament

Verify clean starts, releases, repeated notes, and rests before adding vibrato, portamento, pulse sweeps, or aggressive filtering. A two-frame restart at nominal 50 Hz occupies 40 ms—nearly half an 83 ms sixteenth note. Avoid assuming a tracker instrument will retain its character after export into a player with different restart rules. MiniPlayer2 explicitly documents conversion limits and NTSC caveats. [S11](../sources.md#s11)

For fast classical material, prioritize clear pitch changes and phrase accents. Continuous vibrato or portamento can blur a chromatic run even when every stored note is correct.
