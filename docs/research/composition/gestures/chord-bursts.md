# CHORD-01 — selective chord bursts

**Status:** original [Für Elise implementation](../../../../songs/studies/fuer-elise-interpretation/README.md) rendered; listening approval pending. The variations below remain design options unless implemented in that study. Browse the [gesture library](README.md).

## Musical purpose

Use a brief, evolving chord texture to answer a melody or reinforce a harmonic arrival. Let it release or leave silence before the next busy melodic run. In an A-minor/E-major passage, A–C–E and E–G-sharp–B are starting pitch sets; choose an inversion below the lead and vary the order when the phrase returns.

The [DRAX trace](../fuer-elise-reference.md) establishes triangle-plus-pulse and an A3/C4/E4 cycle with two calls per pitch at the first accompaniment entry. This demonstrates one-voice chord implication. It does not establish that copying that rate, register or waveform will improve another arrangement.

## SID realization and variations

Keep the chord root in the musical arrangement and preserve native relative-pitch programs as instrument data. Compare a restrained pulse arpeggio with a triangle-plus-pulse version; combined-waveform behaviour is chip-dependent. Define note order, dwell in player calls, gate/release and pulse movement explicitly. A faster musical broken chord scheduled as separate notes is a distinct option with different envelope articulation.

Vary one of burst length, inversion, rate or rhythm at a time when studying the mechanism. In a creative phrase, choose these together to shape the response. Do not continuously retrigger an identical bright burst under every lead note.

## Costs and acceptance

One oscillator alternates pitches; it does not sustain three independent chord tones. Repeating native pitch-table writes can interact with vibrato, so verify the intended trajectory in the exported driver. Keep chord filter routing independent of bass ownership unless a shared contour is deliberate.

The first interpretation demonstrates a finite burst, not a sustained arpeggio loop: all 17 chord starts in each palette retain pulse or triangle-plus-pulse for seven body calls, then lose waveform bits at the table jump until the next instrument selection. The audible tones match the intended voicings. Do not reuse that table as a continuous chord instrument. See the [original study's bounded verification](../../../../songs/studies/fuer-elise-interpretation/README.md).

The [layered-entrance study](../../../../songs/studies/elise-layered-entrance/README.md) uses explicit waveform rows at every step, including the jump target. Its corrected table retains triangle-plus-pulse through the repeated pitch cycle and release. It also contrasts longer coincident bass/chord tails against delayed, shorter answering gestures, using the preferred Weight bass unchanged. Evaluate this combined texture before increasing bass resonance again.

Accept when the harmony is clear and the texture supports the melody without an exhausting buzz. Verify all intended cycle pitches and their dwell times; a static root-frequency assertion cannot validate an arpeggiating body. Reference provenance and native timing constraints are in the [reference study](../fuer-elise-reference.md) and [advanced techniques](../../sid/advanced-techniques.md).
