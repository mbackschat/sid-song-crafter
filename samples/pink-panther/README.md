# Pink Panther sample materials

This package produces **mono and stereo SID/WAV files locally**, with editable SWM/SWS modules. The [owning song study](../../songs/pink-panther/README.md) retains the source attribution, original score reduction and scoped mono acceptance. The new stereo presentation preserves those notes and instruments: melody centered, bass left, pulse accompaniment right. Stereo listening acceptance is pending.

Composition and source-arrangement redistribution permissions remain unresolved. This is the always-included materials tier: recipes, shared tools and source references are public; downloaded MIDI, generated score/modules and SID/WAV outputs remain in ignored local storage. The recipe contains no embedded notes.

## Build both versions

Follow [local setup](../../docs/setup/local-setup.md) for MIDI/Python dependencies, the renderer and headless VICE, then run:

```sh
python3 scripts/setup-project.py --only references --include pink-panther-score
python3 scripts/setup-sidwizard.py --sid-count 1
python3 scripts/setup-sidwizard.py --sid-count 2
python3 scripts/listening-package.py samples/pink-panther/stereo.recipe.json --output build/sample-pink-panther-stereo
```

Open `build/sample-pink-panther-stereo/listening.md` for the mono SID/WAV, stereo SID/WAV, stereo SWS, fold-down and verification receipts. The runner retains exact source/tool/output fingerprints and reuses unchanged stages.

## Materials and sound contract

- [Build recipe](stereo.recipe.json): source preparation, verified mono build, stereo conversion/render and VICE checks.
- [Source references and fingerprints](../../config/local-assets.json), [song materials](../../songs/pink-panther/README.md) and [stereo converter](../../scripts/sample_exports.py).
- [Verification manifest](stereo-manifest.json): output hashes and technical checks, without copyrighted note data.

Target PAL MOS8580, one call per video frame, chips at `$D400` and `$D420`. Route A left and B right. A1/B1 duplicate the melody; A2 keeps the original bass; B3 keeps the original harmony. A3/B2 are silent. Original physical oscillator indices and active filter settings are verified; sounding sync/ring programs are excluded. This expands stereo placement without composing additional parts. Rendered WAVs use 44.1 kHz stereo PCM16 at unity gain. Other players must reproduce the output routing; matching registers does not imply physical phase coherence.

Model-assistance review, 2026-10-16: no call. These exports need human placement feedback; current models have no demonstrated authority to settle it. Reassess after that feedback.
