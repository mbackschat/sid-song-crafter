# Instruments as SID programs

A SID instrument is a set of instructions and parameters that develops a sound through time. “Pulse lead” names its oscillator waveform; the instrument also determines how it enters, moves, releases and responds to the next note. Its identity can depend on the playback driver, previous notes and other voices. That is the useful sense in which we treat an instrument as a program.

This does not require separate machine code for every sound. A shared interpreter can execute compact instrument records or tables. Nor does every instrument need elaborate motion: a fixed triangle with a carefully chosen hardware envelope is a valid sound. The distinction is between a description of one instant and the behavior that produces a musical gesture.

## What the program controls

The score supplies pitches, durations, rests and instrument selections. The instrument supplies behavior around those events. Drivers can let score commands alter that behavior, so the boundary is useful rather than absolute. The SID itself continues running its oscillators and envelopes between software updates; the player changes their controls at its scheduled cadence. See the [hardware contract](../sid/hardware.md) and [instrument programming overview](instruments-and-composition.md).

| Musical question | Program behavior |
| --- | --- |
| How does the note arrive? | Gate/retrigger sequence, ADSR settings, perhaps a brief noise or pitched attack before the body |
| What gives the held tone character? | Waveform changes, pulse-width motion, vibrato, bends, arpeggios or filter movement |
| What survives a pitch change? | A new attack, a tied envelope, retained modulation phase or a restarted table |
| What happens after note-off? | Hardware release, possibly continuing pitch/PWM, followed by a driver-specific stop |
| Which resources does it need? | One oscillator, a coupled modulator, shared filter control or a temporarily borrowed voice |

A tracker “wavetable” commonly means timed waveform/pitch operations, rather than recorded sample audio. Such a table is one possible language for the program. [Source and manual studies](../tools/source-studies.md) show why its row timing and restart rules must be learned for the particular driver.

An illustrative instrument might behave like this; these are invented instructions, **not recovered code from a master**:

```text
on note:
    set target pitch and envelope; perform this player's retrigger
    enter a brief noise attack, then restore pitched pulse
    restart vibrato delay; preserve pulse-program phase
each scheduled update:
    advance pulse width
    after the delay, add shallow vibrato to target pitch
on note-off:
    clear gate; continue motion while the envelope releases
on next note:
    apply the declared restart/continuation rules
```

Short notes might finish before vibrato begins. A releasing note can keep changing color. A following note can replace its tail. These consequences belong to the sound just as much as its initial waveform.

## What the masters make concrete

There is historical support for this perspective, but no single universal SID instrument language. Hubbard's contemporary interview describes an interpreter, software vibrato, pitch bending and changing waveform after a noise transient. Hülsbeck's Soundmonitor manual exposes pulse envelopes, vibrato delay, portamento and a filter-triggering voice. Galway's published loader source has pulse, frequency and chord programs alongside musical calls and loops. These are [documented accounts](../composers/hubbard-galway.md) and [historical tool descriptions](../composers/huelsbeck-tel.md), distinct from the executed findings below. They support the programming model without proving that every composer used identical abstractions.

### Hülsbeck: Shades keeps moving through release

Our initialized execution of the selected filter-corrected *Shades* variant verifies separate pulse trajectories, delayed vibrato and target glides. Pulse motion continues after gate-off; a hold preserves note work while modulation advances. The melody's physical voice also owns filter triggering. Moving its patch to another voice without moving that responsibility changes the instrument's context.

Its CIA timer supplies approximately 79.93 updates per second, so “delay 16” is not sixteen PAL video frames. The listener heard the moving pulse as more vibrant than the frozen diagnostic, and accepted the familiar-material transfer. Those are bounded verdicts, not approval of every glide: a separate invented ending was rejected. Follow the [Shades card](instruments/shades-decoded-programs.md) to the evidence, editable banks and [computed sound routines](../../../scripts/shades_programs.py).

### Galway: Rambo separates note length from sound lifetime

The executed loader has distinct score activity, gate-release countdown and sound lifetime. Returning from the score does not immediately stop the sound routine: PWM and pitch processing can continue until the lifetime expires. Copying its notes and waveform while discarding these counters would lose part of the ending gesture.

The independent implementation retains these rules as editable state and algorithms. Selected tonal programs were also accepted on a matched Für Elise phrase. The [Rambo card](instruments/rambo-decoded-programs.md), [lifetime proof](rambo-preparation.md#ongoing-sound-lifetime-and-programmed-motion) and [sound component](../../../scripts/rambo_programs.py) distinguish that reuse from the complete loader and its other effects.

### Hubbard: Monty can share an instrument's moving state

In the selected *Monty on the Run* player, pulse width belongs to a mutable instrument record; delay and direction belong to each voice. Two voices selecting that record can both change its width, in voice-processing order. New notes retain phases. The instrument is therefore more than a private patch freshly copied onto each note.

Our familiar transfer preserves this mechanism and was accepted, while the contrasting *Commando* execution narrows the generalization: its observed pulse arithmetic differs. The [Monty card](instruments/monty-decoded-programs.md) links editable records and the [sound helper](../../../scripts/monty_title_programs.py). “A Hubbard instrument” is not a sufficient runtime specification.

### Follin: Ghouls gives the attack its own stage

The selected *Ghouls ’n Ghosts* bass program starts with one PAL update of noise before restoring its pitched triangle body. Its moving-pulse programs can retain phase between notes. A note too short for the delayed body needs explicit handling; correct notation alone cannot make that body occur.

The [Ghouls card](instruments/ghouls-decoded-programs.md) links the [independent player](../../../scripts/ghouls_player.py), parameters and qualified listening acceptance. The bounded Gauntlet comparison corroborates selected behaviors while retaining joint Tim/Geoff credit; it does not establish a universal Follin recipe.

## How this project uses the idea

We retain source notes separately and choose instruments for the phrase's musical purpose. The [native workflow](../../workflows/native-song-workflow.md) represents original sound programs through editable SID-Wizard waveform, pulse and filter tables. The [decoded-player workflow](../../workflows/decoded-song-workflow.md) also uses named JSON data, Python state models and independently compiled routines to express recovered mechanisms. These are different representations with explicit contracts, not one interchangeable preset format.

Learning a mechanism means following initialized execution from a sound's parameters to its changing state and ordered register writes, then testing a causal change. Replaying captured writes reproduces an observation; it cannot by itself explain how the instrument would respond to new notes. We implement that response, compare it with the reference, and transfer it to different, source-backed material. [Execution procedure](../tools/sid-program-analysis.md)

Reuse must preserve clock, chip model, update cadence, retrigger rules and shared-resource ownership. ADSR codes and gate transitions have hardware behavior that software tables cannot wish away. Ring/sync can consume another same-chip oscillator; each SID has one shared filter and mono output. A second chip adds resources but requires an explicit allocation and mix. [Envelope constraints](../sid/advanced-techniques.md#envelope-timing-is-part-of-the-instrument), [dual-SID contract](../sid/dual-sid.md#plan-the-sound-hardware-and-the-mix-together)

Finally, execution agreement establishes behavior, not musical value. We audition attack, body, release and next retrigger in the intended accompaniment, with a labelled reference. The decisive question is whether that program helps the phrase express its intended character. A faithful mechanism can remain the wrong instrument for the song.
