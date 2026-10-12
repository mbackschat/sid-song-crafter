# Bass presence in the combined Elise interpretation

These original proposed timbres change only `bass-groove` in [creative B](../fuer-elise-interpretation/recipe-b.json). The lead, chord instruments, notes and timing stay intact, including the existing bass attack waveform. They explore bass presence; neither is an established improvement or a DRAX transcription.

- [Weight](weight.json): sustain `$8→$b`, release `$5→$9`, initial low-pass resonance `$8→$a`, cutoff `$580→$600`, initial pulse width `$700→$600`; remaining tables unchanged.
- [Resonant](resonant.json): sustain `$8→$c`, release `$5→$8`, low-pass resonance `$c` with initial cutoff `$680` then direct cutoff `$0c0`, initial pulse width `$580` and motion steps `$30/$d0` (±48).

Run the [controlled native patch comparison](../fuer-elise-attack/README.md) with fresh output directories:

```sh
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 scripts/compare-native-patch.py songs/studies/fuer-elise-interpretation/recipe-b.json songs/studies/elise-bass-presence/weight.json --output build/elise-bass-weight --seconds 20
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 scripts/compare-native-patch.py songs/studies/fuer-elise-interpretation/recipe-b.json songs/studies/elise-bass-presence/resonant.json --output build/elise-bass-resonant --seconds 20
python3 scripts/compare-audio.py prepare build/elise-bass-weight/b/excerpt.wav build/elise-bass-resonant/b/excerpt.wav build/elise-bass-listen/versions --individual-copies
```

Prepared samples:

- [Weight, level-matched](../../../build/elise-bass-listen/versions.a.matched.wav)
- [Resonant, level-matched](../../../build/elise-bass-listen/versions.b.matched.wav)
- [Weight → half-second gap → resonant](../../../build/elise-bass-listen/versions.ab.wav)

Each runner output compares creative B against one new bass and verifies the identical full converted schedule plus actual excerpt note and pattern consumption. The [weight report](../../../build/elise-bass-weight/comparison.json) and [resonant report](../../../build/elise-bass-resonant/comparison.json) each verify 1,004 calls, note counts `[70, 38, 17]` and 882,000 PCM frames without clipping; both use byte-identical baseline PCM and the same input recipe. Only the first 20 seconds plus one safety call are CPU-audited, so these are excerpt checks rather than full-song completion evidence.

Full-excerpt AC RMS matching reduces overall level differences; it does not equalize the bass against the other voices or establish musical quality. Original amplitudes remain in each `b/excerpt.wav`; the [comparison manifest](../../../build/elise-bass-listen/versions.comparison.json) retains gains and PCM checks. See the [matching contract](../../../docs/audio-comparisons.md). Listening feedback is the decision criterion.
