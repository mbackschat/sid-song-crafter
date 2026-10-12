# CHORD-01 — combined-waveform chord with continuing release

**Evidence:** rendered experiment with full-cycle register verification; its two arrangement auditions were judged not close to the desired DRAX sound. Target: SID-Wizard 1.97 Extra, one MOS8580, PAL, one call per frame. The original [layered-entrance study](../../../../songs/studies/elise-layered-entrance/README.md) retains editable recipes, musical examples, comparison audio and reproduction commands. Design and verification: 2026-10-13.

## Musical role and native program

Use one unfiltered oscillator to imply an accompaniment chord below a moving lead. Retain the waveform through release so the chord can support the bass between attacks. This consumes one voice; the bass alone owns the shared filter. It does not create independently sustained chord tones.

- Waveform: combined triangle/pulse `$51`, after the standard TEST `$09` onset.
- Relative pitch cycle: `[0,0,3,3,7,7]` from A3 for A–C–E, or `[0,0,3,3,8,8]` from G-sharp3 for G-sharp–B–E. Each explicit waveform row lasts one PAL call; the doubled entries give two calls per tone.
- Loop: jump to the first explicit waveform row. Every body row reasserts waveform; the player's gate mask preserves release as `$50`.
- Pulse width: fixed `$600`; no sync, ring modulation or vibrato.
- ADSR: `$034a` for the layered example; `$0348` for the shorter answering texture. The envelope's actual amplitude depends on its history; release settings are not proof of audible duration.

## Findings and limitations

The [pinned player source](../../../../.tools/sid-wizard-1.97/native/sources/include/player.asm) shows `WFAJUMP` bypassing the ordinary delay-row decoder and entering `SEWFARP`. A target beginning `$01` becomes literal waveform/control `$01`, clearing waveform bits even while arpeggio pitch changes continue. [Native-export regression tests](../../../../tests/chord_programs_test.py) reproduce this in both earlier minor and major programs and verify the corrected loops. Explicit waveform loop anchors avoid that mechanism. A gate-on frequency trace alone cannot establish an audible chord.

The [guard](../../../../scripts/verify-chord-programs.py) checks ordered pitches and waveform through every held cycle, release and following rest. At least two held cycles are required; use a different profile for intentionally short stabs. These checks do not measure analogue envelope amplitude or guarantee musical quality. Combined-waveform timbre on MOS6581 and physical chips needs separate audition.

Choose longer tails for a coincident bass/chord entrance, or shorter tails and delayed onsets for [answering gestures](../gestures/chord-bursts.md). Listen for a fuller accompaniment without obscuring the melody. The inspiration is [DRAX's measured layered entrance](../fuer-elise-reference.md); the retained programs and phrase timing are original designs.
