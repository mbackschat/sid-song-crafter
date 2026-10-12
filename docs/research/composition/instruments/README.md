# Original native instrument bank

Research and design date: 2026-10-12. This bank implements the first small group of experiments from [the repertoire brief](../sound-design-repertoire.md) using SID-Wizard 1.97 Extra. The [editable study source and workfiles](../../../../songs/studies/sidwizard-repertoire/README.md) retain the original patches, phrases and controlled comparisons.

- [LEAD-02 — moving pulse lead](lead-02-moving-pulse.md): static versus moving width, with the same delayed vibrato and envelope.
- [LEAD-03 / PLUCK-01 — bright attack pluck](pluck-01-bright-attack.md): one saw transient versus a triangle-only attack.
- [BASS-02 — kick-to-bass shared voice](bass-02-kick-to-bass.md): a short triangle pitch fall before the same pulse bass body.
- [DRUM-01 — falling triangle kick](drum-01-falling-kick.md): an independent absolute-pitch percussion program.

All are original designs, not copied presets. Evidence level: **rendered experiment**, verified on 2026-10-12 through upstream SID-Maker export, 501 independent py65 play calls and ten-second libsidplayfp 3.1.1/SIDLite MOS8580 renders. [The generated trial report](../../../../build/instrument-trials/trial.json) retains checksums, CPU measurements, PCM checks and comparison gains; [the study README](../../../../songs/studies/sidwizard-repertoire/README.md) gives reproduction commands and links the audio. Every render is complete and unclipped, with all gates closed at the last audited call and final-half-second AC RMS zero. [Bounded listening feedback](../gestures/README.md) is available; editor/export listening equivalence, other SID models and physical hardware remain unreviewed.

The solo A/B pairs change one native program while preserving notes, row timing, envelope and the comparison's remaining instrument parameters. The mix pair changes all three families at once and is intended for evaluating a coherent palette after solo inspection. None is promoted to a listening-reviewed repertoire entry by these technical checks.
