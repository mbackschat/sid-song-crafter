# Für Elise: layered entrance and playful replies

Two original arrangements investigate the [DRAX accompaniment entrance](../../../docs/research/composition/fuer-elise-reference.md) with the listener's preferred [Weight bass](../elise-bass-presence/README.md). The melody's 70 notes and quarter-note tempo 72 remain unchanged. The new accompaniment and native programs are deliberately independent of the preserved source; each score retains source identities and arrangement provenance.

## Musical choices

| Version | Bass and harmony | Intended impression |
| --- | --- | --- |
| [Layered](layered.json), [score](layered-score.json) | Twelve low harmonic arrivals; bass and chord enter together. Combined triangle/pulse arpeggios continue through release `$a`. | A fuller accompaniment that supports a held melodic arrival without adding many bass attacks |
| [Playful replies](reply.json), [score](reply-score.json) | Sixteen bass and chord events. Most chords follow the bass by 3/16 quarter beat; selected fifth/octave bass answers and later chord replies add variation. Chord release is `$8`. | More rhythmic separation and answering motion |

Both use the exact Weight bass program, the preferred interpretation B's pulse lead, and unfiltered combined-waveform chords. Only bass owns the shared filter. A–C–E and G-sharp–B–E are implied by native pitch programs rather than expanding the score into rapid note retriggers. These are original arrangement choices, not a reconstruction of DRAX's tables. This pair compares musical treatments; several accompaniment variables change together.

## Reproduce and audition

With the [native toolchain](../../../docs/native-song-workflow.md) installed, use fresh output directories:

```sh
python3 scripts/native-song.py build songs/studies/elise-layered-entrance/layered.json --output build/elise-layered-entrance
python3 scripts/native-song.py build songs/studies/elise-layered-entrance/reply.json --output build/elise-playful-reply
python3 scripts/compare-audio.py prepare build/elise-layered-entrance/native-song.wav build/elise-playful-reply/native-song.wav build/elise-layered-listen/versions --individual-copies
```

- [A: layered entrance](../../../build/elise-layered-listen/versions.a.matched.wav)
- [B: playful replies](../../../build/elise-layered-listen/versions.b.matched.wav)
- [A then B](../../../build/elise-layered-listen/versions.ab.wav)

Both samples last approximately 22 seconds, including release and ending. Matching attenuates B by 0.328 dB; original-amplitude WAVs remain in the build directories. Listener verdict, mbackschat, 2026-10-13: **neither is close to the preferred DRAX fragment**, which sounds vibrant, like two things overlaid. These are not accepted matches. Correcting waveform continuity and changing accompaniment placement did not establish the desired timbral character. Use the precise [2.02–2.75-second reference](../../../docs/research/composition/fuer-elise-reference.md) to distinguish the bass's own evolving spectrum from the simultaneous chord contribution before another arrangement revision.

## Native behaviour and evidence

The earlier [short-burst study](../fuer-elise-interpretation/README.md) jumps into an arpeggio-delay row, which the pinned player's jump handler treats as a literal waveform. It clears waveform selection while pitches continue changing. These new tables instead repeat six explicit `$51` rows with relative pitches `[0,0,3,3,7,7]` or `[0,0,3,3,8,8]` and jump to their waveform-setting first row. This produces two PAL calls per tone and preserves the waveform during release as `$50`, without reopening gate. The original samples remain unchanged for comparison.

Both full exports pass 1,110 CPU calls, exact note scheduling, unclipped mono MOS8580 rendering and a quiet ending. The layered version schedules `[70,12,12]` events and the reply version `[70,16,16]`. Checks run at one update per PAL frame; RAM-only CPU limits exclude VIC contention. Native register checks establish pitch/control behaviour, not envelope amplitude or listening quality. Physical hardware and VICE checks of these specific arrangements remain outside this evidence.

The [sustained-chord guard](../../../scripts/verify-chord-programs.py) checks every held and release frame, ordered pitch/dwell, waveform preservation, no re-gating and final silence controls. It requires at least two complete held cycles per selected chord and records input hashes. Run against fresh report paths:

```sh
python3 scripts/verify-chord-programs.py build/elise-layered-entrance/conversion.json build/elise-layered-entrance/native-song.frames.json --instrument chord-minor=0,3,7 --instrument chord-major=0,3,8 --waveform 51 --dwell 2 --output build/elise-layered-entrance/chord-programs.json
python3 scripts/verify-chord-programs.py build/elise-playful-reply/conversion.json build/elise-playful-reply/native-song.frames.json --instrument chord-minor=0,3,7 --instrument chord-major=0,3,8 --waveform 51 --dwell 2 --output build/elise-playful-reply/chord-programs.json
```

The supplied frames and manifest must come from the matching successful native workflow; this focused guard does not independently establish their binary provenance. The [layered report](../../../build/elise-layered-entrance/chord-programs.json) covers 12 chords and the [reply report](../../../build/elise-playful-reply/chord-programs.json) covers 16.
