# SID hardware and register programming

## Sound architecture

One SID provides three oscillator/envelope voices, a shared multimode filter, and master volume. Each voice supports triangle, sawtooth, pulse, and noise. Sync and ring modulation connect oscillators in a fixed cycle: voice 1 receives voice 3, voice 2 receives voice 1, and voice 3 receives voice 2. The modulator may be inaudible but must still oscillate. Ring modulation applies to the triangle waveform. [S01](../sources.md#s01)

## Register reference

Voice bases are `$D400`, `$D407`, and `$D40E`. Add these offsets to the selected base:

| Offset | Meaning |
| --- | --- |
| 0, 1 | Frequency word, low then high byte |
| 2, 3 | Pulse width, low byte then low four bits of high byte |
| 4 | Control: bits 0–7 = GATE, SYNC, RING, TEST, triangle, saw, pulse, noise |
| 5 | Attack in high nibble; decay in low nibble |
| 6 | Sustain level in high nibble; release rate in low nibble |

| Address | Meaning |
| --- | --- |
| `$D415`, `$D416` | Cutoff: low three bits, then remaining eight bits |
| `$D417` | Resonance in high nibble; filter routing for voices 1/2/3 and external input in low nibble |
| `$D418` | Master volume in low nibble; LP/BP/HP in bits 4/5/6; voice-3 direct-path mute in bit 7 |
| `$D419`–`$D41C` | POTX, POTY, OSC3, ENV3 readback |

Register layout is independently visible in reSID's read/write dispatch. Sound-control registers cannot be read back as stored values; maintain software shadows. Reading a write-only register exposes bus behaviour, not a reliable shadow. [S02](../sources.md#s02)

## Envelopes and articulation

A rising GATE starts attack from the envelope's current level. Clearing GATE starts release, which continues with GATE clear. Sustain specifies a level, not a duration. TEST resets oscillator-related state; it does not reset the envelope rate counter. Changing rates can encounter the ADSR delay bug when a new threshold has already been passed, delaying the next step until counter wrap. Treat hard restart as a player-specific timed write sequence, not a universal reset instruction. [S03](../sources.md#s03)

Practical consequence: changing pitch while GATE remains high makes a connected note, not a new attack. For repeated notes, reserve time for gate-off and any required restart sequence. Retest articulation after changing player rate or instrument parameters.

## Analogue behaviour and model differences

6581 and 8580 are distinct targets. Combined waveforms are not a simple digital mixture; modern reSIDfp models use measured behaviour. Cutoff register values are control inputs, not a portable frequency-in-hertz scale across individual chips and models. Treat emulator settings as part of a sound's specification. [S04](../sources.md#s04)

Voice-3 mute affects its direct output path; a voice routed through the filter can still be heard. Keep routing explicit when reserving voice 3 as a modulation source. The original datasheet is useful for the intended interface, while measured emulator implementations clarify silicon behaviour. [S01](../sources.md#s01)

## Initial instrument experiment

Project recommendation: begin with an unfiltered triangle, known frequency, audible sustain, and master volume 15. Then add gate articulation, pulse-width changes, modulation, and filtering one at a time. Record the exact register sequence and clock; “piano-like” is a timbral description, not a reproducible instrument definition.
