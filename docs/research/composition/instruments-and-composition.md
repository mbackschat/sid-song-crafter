# Instruments and composition

## Compose for available voices

Start with melody, bass, and an accompaniment role. A SID voice plays one oscillator pitch at a time; a tracker arpeggio creates an impression of harmony by rapidly changing pitch. It does not sustain several independent notes. Plan which notes must overlap before selecting instruments.

For a piano adaptation, preserve melody, harmonic bass, and phrase rhythm first. Reduce interior chord notes or turn them into broken chords when three voices are insufficient. Use a second chip to preserve musically important overlap, rather than adding constant doubling by default. These are arrangement recommendations, not hardware requirements.

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
