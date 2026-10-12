# Native Für Elise attack comparison

[triangle-attack.json](triangle-attack.json) changes only the first `melody-pluck` waveform-table byte from gated sawtooth `$21` to gated triangle `$11`. The TEST first frame, triangle body, ADSR, bass, accompaniment and score remain as in the [base recipe](../../fuer-elise-sidwizard.json). This is a controlled sound comparison, not a new canonical arrangement.

```sh
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 scripts/compare-native-patch.py songs/fuer-elise-sidwizard.json songs/studies/fuer-elise-attack/triangle-attack.json --output build/elise-attack-study --seconds 20
```

Use a fresh output directory and the [configured renderer/exporter](../../../docs/audio-workflow.md). The output retains the input recipe/patch/score, derived recipes, complete editable native modules and exported SID/PRG files. Only the requested opening excerpt plus one safety call is CPU-audited; both converted full schedules must be identical. It verifies every excerpt note-column read, discrete note start and pattern-order read. It does not verify full-song completion or musical quality; see the [full native workflow](../../../docs/native-song-workflow.md) for complete-song checks.

Play `opening.a.matched.wav` for the original attack, `opening.b.matched.wav` for the triangle attack, or `opening.ab.wav` for A, half a second of silence, then B. `a/excerpt.wav` and `b/excerpt.wav` retain original render amplitudes. [Level matching](../../../docs/audio-comparisons.md) attenuates to a shared safe full-excerpt AC RMS with 1 dB peak headroom; this includes silence and is not perceptual loudness matching. `comparison.json` records hashes, gains, PCM health and excerpt scope. Numerical checks do not establish which sound is musically better.

The reusable patch format names one existing instrument and explicit old/new leaf values. Scalar fields are `control`, `hard_restart_adsr`, `adsr`, `frame1`, `vibrato` and `vibrato_delay`; they must already exist. Table changes select an existing three-byte row in `wave`, `pulse` or `filter` by zero-based `row` and `column`. Several leaves of the same instrument may change. Names, routing, table lengths and jump rows cannot change. Stale preconditions, duplicate leaves, encoded no-ops and invalid native instrument values are rejected by the existing encoder. Excerpts must contain a PCM frame, last at most 60 seconds and end before the terminal song stop even after the safety call.
