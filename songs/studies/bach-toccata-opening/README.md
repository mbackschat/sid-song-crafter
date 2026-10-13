# Bach Toccata: first opening audition

These two original single-SID arrangements cover Mutopia BWV 565 source beats 0–10: three octave gestures, the D2 pedal, the first diminished chord and its written G3–E3–F-sharp3 resolution. The next C-sharp pickup at beat 11.75 is excluded. This is an opening study, not the complete Toccata. Both versions have passed complete native scheduling, independent VICE checkpoints and rendered signal checks; the listener accepted the hybrid direction but found its pacing too slow, as recorded in the [owning study](../../../docs/research/composition/bach-toccata.md).

- [Restrained sustained SID reference](restrained.json): our reduced steady-tone palette; it is not an acoustic organ reference or a faithful full-voicing reproduction.
- [SID hybrid candidate](hybrid.json): the same [arranged score](score.json), with lead pulse width moving from `$6c0` to `$840` and back over approximately two seconds, plus selective G3/B-flat3/C-sharp4/E4 cycling during the diminished hold. One voice alternates these tones; it does not sustain four independent notes.
- [Preparation record](preparation.json): exact source hashes, complete pitch mapping, source omissions per palette, warp anchors, ornament decisions and the model-assistance review.
- [Complete source notes](source-notes.json), [complete public-domain LilyPond score](source/ToccataFugue.ly) and [complete source MIDI](source/ToccataFugue.mid): preserve the complete Toccata and Fugue separately from this arrangement.

The pacing is an original SID interpretation: expand the three opening A fermatas, keep their descents distinct, let the pedal announce the chord, and settle the cadence at 24 seconds. It does not match Kibbie's recording timing. The printed prall ornaments are omitted in this first audition; MIDI does not encode them or the fermatas. The chord begins as a simultaneous three-voice reduction instead of the engraved rolled onset. During the chord, the restrained palette omits more inner tones than the hybrid; this comparison tests both motion and harmonic fullness rather than isolating pulse movement. The written tied G3 is split at source beat 9 so the hybrid cycle ends before the G–E–F-sharp turn. No legato or acoustic organ equivalence is claimed.

Both recipes target one MOS8580, PAL, concert A=440 Hz, SID-Wizard 1.97 Extra at one call per video frame. Every patch keeps `frame1=$09` TEST silence and `timingPolicy=retain-full-pitch`; full pitch follows the first frame. Bass alone owns the static low-pass filter; neither palette uses noise, drums, vibrato, glide, sync or ring modulation. Sustains and release tails are balance choices requiring listening. Pulse motion follows the [LEAD-02 grammar](../../../docs/research/composition/instruments/lead-02-moving-pulse.md); the explicit waveform loop follows the [corrected CHORD-01 contract](../../../docs/research/composition/instruments/chord-01-sustained-arpeggio.md). Those cards' existing listening limits remain applicable; the hybrid direction now has bounded listener acceptance; its slow pacing does not. See the [faster revision](../bach-toccata-opening-driven/README.md).

Prepare a fresh bundle from the pinned intake with existing MIDI dependencies:

```sh
PYTHONPATH=.tools/arrangement-deps python3 scripts/studies/bach/prepare-opening.py --output build/bach-opening-inputs
```

Build, verify in VICE, render and prepare the level-matched comparison with the [cached listening recipe](../../../config/listening/bach-toccata-opening.json), then publish friendly local filenames:

```sh
python3 scripts/listening-package.py config/listening/bach-toccata-opening.json --output build/bach-toccata-opening-v1
python3 scripts/publish-listening.py build/bach-toccata-opening-v1/run.json --selection config/listening/bach-toccata-opening-audition.json --output build/bach-toccata-opening-listening
```

Publication requires a fresh destination; retain the existing audition files and their source manifest. Supply both full SID renders alongside the separately sourced actual organ performance. The useful listening question is whether the hybrid balances organ weight and dramatic pauses with appealing SID character, without letting chord cycling weaken the held-harmony impression. Check its ending separately. Preparation verifies source identity, source-backed pitches, event order/non-overlap and native instrument encoding; execution, rendered-signal and listening evidence remain separate.
