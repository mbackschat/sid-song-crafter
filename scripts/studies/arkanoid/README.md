# Arkanoid: bounded Galway corroboration

Run [listening.json](listening.json) through the existing [listening-package runner](../../listening-package.py) to reproduce the [Galway contrast](../../../docs/research/composition/galway-contrast.md): initialized original RSID execution in its own raster/foreground host, a guarded one-byte tom arithmetic diagnostic, source/diagnostic renders and a labelled same-material comparison. Inputs remain pinned to title subtune 1, PAL and MOS6581. The probe does not admit arbitrary RSIDs or create a second music player.

```sh
python3 scripts/listening-package.py scripts/studies/arkanoid/listening.json --output build/arkanoid-corroboration/listening
```

For execution only, select a fresh output directory:

```sh
python3 scripts/studies/arkanoid/check-arkanoid-contrast.py --output build/arkanoid-corroboration/new-execution
```

[check-arkanoid-contrast.py](check-arkanoid-contrast.py) uses the existing SID metadata inspector and VICE record grammar. It captures every opening SID store through 512 completed refreshes, checks arithmetic inputs/output and retained PWM, and observes two later score hooks in a bounded 8,192-refresh run. That later observation is targeted, not a complete SID ledger. Store checkpoints and execution checkpoints have different timestamp conventions; neither is a bus-cycle trace. Human listening remains pending, and no transferable instrument is promoted by this diagnostic.

Keep generated original/modified SIDs, payload PRGs, raw traces and all reference/diagnostic WAVs in ignored `build/`. Promote only a reviewed analysis-file selection through the existing evidence workflow; exclude payload and audio bytes.
