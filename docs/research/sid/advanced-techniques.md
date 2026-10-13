# Advanced SID sound techniques

Research date: 2026-10-12. This is a technique map with evidence and experiment criteria, not a claim that every trick is implemented locally. Sound quality is the project priority: select techniques for a musical purpose, then verify the actual exported player. Read alongside the [composer studies](../composers/README.md), [tool assessment](../tools/composition-tools.md), and [sound-design repertoire](../composition/sound-design-repertoire.md).

## Instruments that evolve between notes

**Waveform programs and transient design.** A SID instrument can switch waveform and pitch during one note. Thorsten Klose's published reconstruction of an *Auf Wiedersehen Monty* drum identifies a triangle attack, a noise segment, and a falling pulse tail. His method combines channel isolation with register traces; MIDIbox control values require translation and must not be copied as SID register bytes. This is analysis by Klose, not a new measurement here. The useful principle is an instrument program with distinct attack, body, and release phases. [MIDIbox tutorial](https://www.ucapps.de/howto_sid_wavetables_1.html)

**Pulse-width movement.** Sweep or alternate the 12-bit pulse width while the note sounds. Treat sweep shape, speed, direction, restart phase, and pitch dependence as instrument parameters. SID-Wizard's manual specifies pulse programs, keyboard tracking, and choices about resetting programs at note start. The same nominal waveform can therefore behave differently across registers and articulations. [SID-Wizard manual, instrument parameters](https://github.com/anarkiwi/sid-wizard/blob/master/native/manuals/SID-Wizard-1.9-UserManual.txt)

**Vibrato, slides, and legato.** These are ongoing frequency changes, not extra MIDI notes. Cadaver's player-design article distinguishes tied notes, which change pitch without resetting gate or pulse programs, from restarted notes. It also separates sequence/pattern data from instrument behaviour. This is an important architectural precedent for keeping our intermediate score independent of the SID instrument engine. [Building a musicroutine](https://cadaver.github.io/rants/music.html)

**Arpeggios and time-shared voices.** Rapid pitch changes imply chords; short percussion attacks followed by bass or lead bodies let one oscillator fulfil several musical roles over time. Neither creates extra independently sustained oscillators. Evaluate chord inversion, arpeggio order, update rate, and register against the actual phrase. The [Hülsbeck/Tel study](../composers/huelsbeck-tel.md) connects these techniques to documented tools and working methods.

## Envelope timing is part of the instrument

The GATE bit changes envelope state; it does not clear the envelope level or rate counter. reSID's measured envelope model explains the delay bug: changing a rate can leave the counter beyond the new comparison value, delaying the next envelope step until the counter wraps. Consequently, a syntactically correct gate toggle does not guarantee a clean or timely audible attack. [reSID envelope implementation](https://github.com/libsidplayfp/resid/blob/master/envelope.h)

Hard restart is a deliberate sequence before a note, usually involving gate and ADSR changes. GoatTracker documents configurable restart settings, buffered versus unbuffered writes, and cases where register order or badlines affect ADSR behaviour. Its workarounds are player-specific, not universal magic bytes. Preserve the instrument's update rate and write order when moving it between players. [GoatTracker manual, compatibility notes and instrument timing](https://github.com/leafo/goattracker2/blob/master/readme.txt)

**Project experiment:** repeat the same pitch after silence, after a sustained note, and after a short grace note. Capture exact ordered stores and compare attack timing in audio across both SID models. Test the exported driver, including its intended screen/IRQ conditions. A per-frame snapshot can miss an intervening gate-off/on pair; our [full-song verification](../../validation/fuer-elise-validation.md) now uses a separate exact CPU-write oracle for the simple player.

## Coupled oscillators and combined waveforms

**Ring modulation and hard sync** make another oscillator part of an instrument. Voice allocation must therefore express modulator/carrier relationships, not merely assign independent notes. Ring modulation affects the triangle path; setting the bit while using only sawtooth is not a general FM synthesizer. The voice dependency cycle and control bits are documented in the [SID specification](../../../skills/c64-sid/references/sid-chip-spec.md).

**Combined waveforms** are hardware interactions, not arithmetic mixing of separate instruments. libresidfp models them using real-chip measurements and distinguishes the digital combination from analogue pulldown effects. It also models filter distortion, 6581 DAC nonlinearity, and configurable combined-waveform strength. A patch that depends on these effects needs a stated chip model and calibration assumptions. [libresidfp project documentation](https://github.com/libsidplayfp/libresidfp)

Noise combined with other waveform bits can alter the noise shift register and lead to a locked state. TEST and oscillator history also affect behaviour. Do not promote an exotic combination to the reusable library after testing only one isolated note; include recovery, repeated notes, and the following instrument. [reSID oscillator implementation](https://github.com/libsidplayfp/resid/blob/master/wave.cc)

**Project experiment:** compare plain pulse, triangle+pulse, and a coupled-oscillator variant at matched perceived loudness. Use the same phrase and tempo. Record which additional voice is consumed and whether low notes, high notes, and repeated attacks remain usable.

## Filter and mix design

SID has one shared filter per chip. The score needs deliberate filter ownership, routing, resonance, and cutoff trajectories. Furnace documents shared-effect priority and the different 6581/8580 behaviour; a voice-local macro must not accidentally change every other filtered part. [Furnace C64 documentation](https://github.com/tildearrow/furnace/blob/master/doc/7-systems/c64.md)

**Project experiment:** compare a dry melody over filtered bass against all voices through the same moving filter. Judge melody intelligibility and transient definition, not just brightness. Save separate model-targeted variants when a single patch does not translate. For two chips, consider independent filter and volume groups as a compositional resource, rather than spending the extra voices on permanent doubling.

## Faster updates and sample techniques

**Multispeed instruments.** More than one player update per video frame can shorten transients or refine modulation. The host must schedule those calls at the intended intervals; calling a routine several times back-to-back is not equivalent. SID-Wizard exposes separate main and multispeed entry points and player variants with different feature sets. The update rate belongs in the patch and export contract. [SID-Wizard manual, player use](https://github.com/anarkiwi/sid-wizard/blob/master/native/manuals/SID-Wizard-1.9-UserManual.txt)

**Volume-DAC audio.** Fast changes to the volume register exploit model-dependent output behaviour. Furnace documents the 6581 software-PCM route and why the corresponding effect is much weaker on 8580. It shares the global volume resource with the music; it is not a free fourth oscillator. [Furnace C64 documentation](https://github.com/tildearrow/furnace/blob/master/doc/7-systems/c64.md)

**Oscillator sample-and-hold.** Linus Åkesson's *Platform Hopping* explains the SounDemoN method, using carefully timed oscillator operations for sample playback. Its jitter correction and badline scheduling show why this requires a different execution contract from a frame-only instrument table. See [the modern composer study](../composers/linus-akesson.md) and the [author's implementation explanation](https://linusakesson.net/music/platform-hopping/index.php).

The research library distinguishes sampled audio, algorithmically generated sample values, and changing oscillator parameters. They can sound similar while requiring quite different CPU schedules and playback environments. Original Galway source provides a particularly useful case in [the Hubbard/Galway study](../composers/hubbard-galway.md).

## What qualifies as a reusable technique

For every accepted instrument, retain its editable program, provenance, intended model/clock, update cadence, voice/filter dependencies, register-write order, CPU/memory cost, phrase demo, and known failure cases. Store dry and arranged examples with an explicit listening verdict. A demo that impresses once becomes a useful tool only when its behaviour can be reproduced and adapted.

The current [three-voice baseline](../../architecture/three-voice-player.md) does not implement most of these capabilities. Its successful execution validates the source pipeline, not a claim of master-level sound design. Prefer a suitable established editor/driver before extending it into another full music system.
