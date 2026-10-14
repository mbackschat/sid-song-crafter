# Deflektor independent reconstruction

[title.json](title.json) is editable numeric score and sound-program data for the complete finite Deflektor title. The [owning study](../../../docs/research/composition/deflektor-preparation.md) records original-source provenance, executed mechanisms and listening status. The original SID is acquired privately through the [asset registry](../../../config/local-assets.json); it is not included in this source directory.

```sh
python3 scripts/setup-project.py --include deflektor
python3 scripts/listening-package.py config/listening/deflektor-full.json --output build/deflektor-independent-full
python3 scripts/publish-listening.py build/deflektor-independent-full/run.json --selection config/listening/deflektor-full.audition.json --output build/deflektor-listening
```

The [compiler](../../../scripts/deflektor_compiler.py) generates new 6502 score scheduling and sound computation from order/pattern bytes, instrument mappings, cold state and editable numeric programs. It embeds neither original driver instructions nor a captured per-call register schedule. The decoded grammar remains specific to the verified Deflektor driver; this is not a universal SID importer. Source pointer annotations are provenance, not executable addresses.

The target is one PAL MOS6581 at `$D400`, with one update per 19,656-cycle frame. Native PAL/NTSC export support elsewhere in the project does not convert this reconstructed driver. Initialization restores the cold state and emits no SID stores. The score's terminal order marker at call 8,480 writes zero to the three controls; following calls are quiet. No fade or musical continuation is added. The full 40,000-call CPU proof covers the stopped interval as well as all 166,845 source stores; rendering uses a shorter, explicitly declared window including the acoustic ending.

The recipe separately checks the original source pin, numeric model against retained source execution, compiled CPU output, full callable headless VICE playback through the stop, rendered signal and matched opening/phrase/ending clips. Its source-model checker reuses the canonical complete ledger and freshly executes three bounded edited-source probes; this is not a new full capture of the original. The standalone PRG has a separately executed SYS 2061 bootstrap and first-call cadence check with modeled VIC/CIA reads. Full callable VICE verification does not imply real-machine PRG autostart testing.

Ordered-store equality excludes instruction/bus-cycle identity and SID internal state. It does not prove identical PCM, physical-chip equivalence or musical acceptance. Read the owning study for the actual listening verdict; generated and reference audio remain in ignored `build/`.
