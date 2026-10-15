# Ghostbusters instruments on the familiar Für Elise phrase

The [plain reference](reference.json) and [native candidate](transfer.json) use the same 53 preserved notes, NTSC A440 frequency bank and quarter-step schedule. The [preparation report](preparation.json) records source fingerprints, every timing/pitch conversion and native articulation limits. The [instrument card](../../../docs/research/composition/instruments/ghostbusters-decoded-programs.md#familiar-material-transfer-and-listening-verdict) owns the musical purpose, execution evidence and accepted listening verdict.

```sh
python3 scripts/studies/ghostbusters/prepare-elise.py --check --output songs/studies/ghostbusters-elise
python3 scripts/listening-package.py config/listening/ghostbusters-elise-transfer.json --output build/ghostbusters-elise-work
python3 scripts/publish-listening.py build/ghostbusters-elise-work/run.json --selection evidence/ghostbusters-elise/listening/audition-selection.json --output build/ghostbusters-elise-listening-new
python3 scripts/evidence.py verify --group ghostbusters-elise
```

Publication requires a fresh output directory. The recipe reuses only unchanged, fingerprint-matched stages. The [initial complete run](../../../evidence/ghostbusters-elise/run-executed.json) took 8.399 seconds on 2026-10-15; its [cached repeat](../../../evidence/ghostbusters-elise/run-reused.json) took 0.292 seconds. A [later 3.409-second revalidation](../../../evidence/ghostbusters-elise/run-revalidated.json) ran the strengthened seven-guard source-correspondence check and reused all other stages without rebuilding audio. Both WAVs are generated score renderings, not an original recording. Keep audio and exports in ignored `build/`.
