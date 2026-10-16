# Original instrument mix sample

[Mono SID](instrument-mix.sid) · [Mono WAV](instrument-mix.wav) · [Stereo SID](instrument-mix-stereo.sid) · [Stereo WAV](instrument-mix-stereo.wav)

The mono sample retains its [recorded listening scope](manifest.json). The new stereo presentation keeps the same notes, instruments and timing: pulse lead centered, pluck left, bass right. It has complete CPU register checks, sampled headless VICE checks and rendered signal checks; stereo placement and balance are accepted on 2026-10-16. No original reference recording is included.

## Materials

- [Score, provenance and study](../../docs/workflows/instrument-trials.md) and [editable recipe](../../songs/studies/sidwizard-repertoire/repertoire.json).
- [Frozen mono SWM](instrument-mix.swm) and [mono PRG](instrument-mix.prg).
- [Frozen stereo SWS](instrument-mix-stereo.sws) and [stereo PRG](instrument-mix-stereo.prg).
- [Mono manifest](manifest.json), [stereo manifest](stereo-manifest.json) and [stereo build recipe](stereo.recipe.json).
- [Shared stereo converter](../../scripts/sample_exports.py); original patterns/instruments are retained once in the frozen SWM.

## Stereo target and reproduction

PAL MOS8580, one call per video frame; SID A at `$D400` goes left and SID B at `$D420` goes right. A1 and B1 carry the same lead, A2 carries the original second voice, and B3 carries the original third voice. A3/B2 are silent. Physical oscillator indices stay unchanged; active filter state is checked on its owning chip. Sounding sync/ring programs are rejected by this fixed mapping. This is spatial redistribution with a duplicated lead, not a new six-part arrangement. Matching software programs does not establish physical phase coherence. A mono fold-down is included in the local listening package.

```sh
python3 scripts/setup-sidwizard.py --sid-count 2
python3 scripts/listening-package.py samples/instrument-mix/stereo.recipe.json --output build/sample-instrument-mix-stereo
```

Use the [setup guide](../../docs/setup/local-setup.md) for the renderer, Python dependencies and headless VICE. The generated `listening.md` links the stereo SID, WAV, SWS, fold-down and verification. The stereo WAV is rendered from that two-SID file at unity gain, 44.1 kHz PCM16; it is not duplicated mono audio.

The rights basis remains the [mono manifest](manifest.json): project-authored notes and instruments under MIT. SID-Wizard's embedded player retains its [separate notice](../../THIRD_PARTY_NOTICES.md#build-playback-and-validation-components). The stereo manifest pins outputs, source files and tool fingerprints.

Listening verdict, 2026-10-16: “All three accepted” in response to the Pink Panther, Moon River and instrument-mix stereo placement/balance review. This closes this sample presentation without extending its musical or hardware scope.

Model-assistance feedback/closure review: no call; the human verdict settles this presentation and existing models cannot adjudicate stereo preference. Reassess only for a new musical revision.
