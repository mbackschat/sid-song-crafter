# Instrument programs and native patches

## Choose a decoded reference program

- [DRAX trio mapping](drax-decoded-trio.md): releasing bass, pulse lead and chord mechanisms with arrangement constraints and an independent three-voice implementation.
- [Flashdance decoded programs](flashdance-decoded-programs.md): staged lead, evolving bass, moving four-tone chords and score-owned pitch effects, with an editable original transfer phrase and declared listening status.
- [Shades pulse and pitch programs](shades-decoded-programs.md): moving pulse, delayed vibrato, target glides and shared-filter ownership; reconstruction and familiar transfer accepted, with the invented fragment's rejected ending retained as a limitation.
- [Cybernoid pulse programs](cybernoid-decoded-programs.md): transient bass, filtered replies and moving-pulse lead on familiar material; accepted paired plain-reference transfer with explicit native timing/tuning limits.

- [Monty tonal programs](monty-decoded-programs.md): accepted familiar-phrase transfer with narrow pulse bass, harmonic replies and shared moving-pulse melody; matched plain reference and explicit timing, tuning, phase and ending limits.
- [Rambo tonal programs](rambo-decoded-programs.md): accepted moving pulse melody and bass with short pulse support on the same 53-note familiar phrase; native lifetime and gate scheduling, with balance, phrasing and ending reviewed.
- [Ghouls pulse and staged-onset programs](ghouls-decoded-programs.md): moving pulse and one-call noise-to-triangle attack on the same 53-note familiar phrase; instruments, balance and adapted ending accepted with a tentative tune reservation. All tonal notes match the source; the perception's cause remains unknown.

- [Deflektor tonal programs](deflektor-decoded-programs.md): accepted familiar 53-note transfer of moving-pulse melody, bass and support; computed low-byte PWM, delayed raw-word pitch and explicit release adaptation.

- [Take On Me tonal programs](take-on-me-decoded-programs.md): accepted matched A440 familiar transfer with one-way pulse lead, delayed vibrato, moving-pulse filtered bass and explicit native articulation limits.
- [Billie Jean pulse lead and filtered support](billie-jean-decoded-programs.md): matched A440 familiar transfer accepted (“plays nice”); inspect setup cutoff writes even for unfiltered voices.
- [Airwolf static pulse and triangle sounds](airwolf-static-tones.md): complete native palette on matched A440 familiar material, explicit gap gates and init-aware timing; familiar transfer accepted.

- [Ghostbusters static patches and shared-phase vibrato](ghostbusters-decoded-programs.md): verified NTSC music programs with score-owned gate/release, one-sided vibrato and retained restart state; familiar transfer is not yet listening-reviewed.

## Original SID-Wizard instruments

Research and design date: 2026-10-12. This bank implements the first small group of experiments from [the repertoire brief](../sound-design-repertoire.md) using SID-Wizard 1.97 Extra. The [editable study source and workfiles](../../../../songs/studies/sidwizard-repertoire/README.md) retain the original patches, phrases and controlled comparisons.

- [LEAD-02 — moving pulse lead](lead-02-moving-pulse.md): static versus moving width, with the same delayed vibrato and envelope.
- [LEAD-03 / PLUCK-01 — bright attack pluck](pluck-01-bright-attack.md): one saw transient versus a triangle-only attack.
- [BASS-02 — kick-to-bass shared voice](bass-02-kick-to-bass.md): a short triangle pitch fall before the same pulse bass body.
- [DRUM-01 — falling triangle kick](drum-01-falling-kick.md): an independent absolute-pitch percussion program.
- [CHORD-01 — sustained combined-waveform arpeggio](chord-01-sustained-arpeggio.md): waveform-preserving loops and continuing release, with separate layered/reply auditions and full-cycle guards.

All are original designs, not copied presets. The initial lead/pluck/bass/drum bank has evidence level **rendered experiment**, verified on 2026-10-12 through upstream SID-Maker export, 501 independent py65 play calls and ten-second libsidplayfp 3.1.1/SIDLite MOS8580 renders. [The generated trial report](../../../../build/instrument-trials/trial.json) retains checksums, CPU measurements, PCM checks and comparison gains; [the study README](../../../../songs/studies/sidwizard-repertoire/README.md) gives reproduction commands and links the audio. Every initial-bank render is complete and unclipped, with all gates closed at the last audited call and final-half-second AC RMS zero. The chord study has its own linked evidence. [Bounded listening feedback](../gestures/README.md) is available; editor/export listening equivalence, other SID models and physical hardware remain unreviewed.

The solo A/B pairs change one native program while preserving notes, row timing, envelope and the comparison's remaining instrument parameters. The mix pair changes all three families at once and is intended for evaluating a coherent palette after solo inspection. None is promoted to a listening-reviewed repertoire entry by these technical checks.
