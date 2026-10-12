# Linus Åkesson: composition through custom engines

Research date: 2026-10-12. This seventh composer study complements the six historical composers in the [study index](README.md). Evidence here comes from Åkesson's published technical explanations, linked code, and release pages. The pieces below are listening and implementation references; no new listening session or hardware reproduction is claimed.

## Why this study matters

Our project must support music that originates in a chip-specific program, not only convert external scores. Åkesson provides unusually detailed accounts of that approach. The three case studies also separate distinct meanings of sophistication: economical arrangement rules, cycle-sensitive synthesis, and a compositional language for larger forms.

## A Mind Is Born: a small engine with a composed trajectory

The [2017 release and annotated implementation](https://linusakesson.net/scene/a-mind-is-born/) provide a C64 executable, recordings, and an explanation of a 256-byte audiovisual production. Its melody generator is deliberately tuned, rather than presented as arbitrary randomness. A short script changes musical behaviour across sections; shared state also drives pulse width and a long filter movement. Waveform and sync changes are structural events. The author explicitly notes that ring modulation has no audible effect on a sawtooth-only step, despite the control bit being set.

**Project inference:** a memorable patch needs a phrase and a trajectory, not merely a pleasing held note. A compact engine can coordinate form and timbre, but extreme size coding is not the goal of our reusable toolchain. Extract the separation between local sound processes and larger musical sections; avoid inheriting fragile memory overlaps just because they save bytes.

**Proposed exercise:** use an original eight-bar phrase and hold its notes constant across three versions: static instrument, evolving pulse width, and a section-level change in waveform/filter. Listen for meaningful development rather than treating continuous motion as automatically better. Retain the editable automation and a note-identical comparison render.

## Platform Hopping: the player as a synthesis instrument

In the [2023 author walkthrough](https://linusakesson.net/music/platform-hopping/index.php), a C64 imitates a NES-inspired ensemble using SID voice sharing and software-generated audio. The SounDemoN technique uses oscillator timing and sample-and-hold behaviour; the article explains timer scheduling, badline avoidance, and interrupt-jitter correction. Brief noise attacks share channels with pulse notes, while another channel handles mixed software audio. The release page supplies the C64 PRG and MP3.

**Project inference:** this is strong evidence against making a MIDI-like event format the universal SID representation. The timing of the sound-generation algorithm is itself part of the instrument. A frame-based converter may preserve every note yet fail to reproduce the result.

**Proposed exercise:** begin with the simpler voice-sharing idea: compare a pulse note with and without a short noise attack, then place it in a bass/percussion phrase. Study the sample engine separately. Before attempting that route, require exact cycle scheduling and an appropriate full-machine playback environment; our present frame-only exporter and py65 harness are not sufficient evidence for it.

## Machine Yearning: a music language and two distinct chips

The [2023 release and implementation account](https://linusakesson.net/scene/machine-yearning/index.php) describe seven pieces in a 4 KB musicdisk for a modified C64 with both 6581 and 8580. Its custom virtual machine runs concurrent programs for sections, rhythms, and note events. Programs can launch, delay, and stop one another; tables and shift registers supply additional musical data. The sound architecture matters compositionally: the 8580's global volume provides rhythmic ducking, while the kick remains on the other chip. The release includes disk and audio downloads and declares CC BY-NC 4.0 for the album.

The 4 KB figure describes the compressed executable, not its RAM requirement; the author describes nearly 6 KB of decompressed program and data.

**Project inference:** two SIDs offer two filter/volume domains as well as more oscillators. A six-note abstraction alone misses that value. The engine also suggests a useful hierarchy for our authoring tools: song sections invoke patterns, patterns trigger instruments, and instruments execute sound programs.

**Proposed exercise:** for a later two-SID arrangement, compare six independent parts against a deliberate two-group mix. Keep the bass attack clear while the other group changes density or volume. Record chip models and addresses explicitly. Do not assume a composition designed around one 6581 plus one 8580 will translate unchanged to two identical chips.

## Lessons for choosing tools

These are custom musical systems, not evidence that we should immediately write another editor. The useful question is which required sound behaviours an established tool already expresses. Use [the composition-tool assessment](../tools/composition-tools.md) to select an editor/driver, and retain a custom-driver route for requirements outside its contract.

The strongest transferable practice is to keep sound, timing, and form editable together. For our project, that means an original source archive, a musical intermediate representation where useful, and an independently expressive native composition. Exporting to SID should preserve the chosen engine's behaviour rather than reduce it back to a list of pitches.
