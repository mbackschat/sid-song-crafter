# Rambo loader: independent SID reconstruction

[Main-music SID](rambo-loader-main.sid) · [Main-music WAV](rambo-loader-main.wav) (about 3:13) · [Main-entry manifest](main-manifest.json) · [GNU GPL v3](LICENSE)

The featured files omit the introduction. The [complete SID](rambo-loader.sid), [complete WAV](rambo-loader.wav) and [historical manifest](manifest.json) remain unchanged. A [centered-lead stereo SID/WAV version](../rambo-stereo/README.md) is also available.

This is the loading music from *Rambo: First Blood Part II*, composed, arranged and programmed by **Martin Galway** in 1985. The historical source credits “(C) Ocean Software 1985”. Galway's [upstream README](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/README.md), dated 14 April 2026, states that he later acquired the music and programming rights from Infogrames, permits reassembly and modification, and requests credit. The same repository supplies [the original loader source](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/rambload.asm) and [GPL v3 license](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/LICENSE).

**Modified version, packaged 2026-10-15:** SID Song Crafter independently reconstructed the loader as an [editable symbolic score](../../songs/rambo-loader.json) and computed C64 player. The downloadable SID contains that independent player, rather than the downloaded upstream driver binary. This complete-song package, its retained score and the combined generated SID/WAV are distributed under [GNU GPL version 3](LICENSE), without warranty. Independently authored reusable tools retain their separate [MIT license](../../LICENSE) when used separately. Preserve Galway's attribution and these notices when redistributing; [third-party notices](../../THIRD_PARTY_NOTICES.md) record the wider project boundary.

The target is **PAL, one MOS6581 at `$D400`, subtune 1**, with one call per 19,656 cycles. The archived complete WAV preserves the full 225-second mono PCM16 render at 44.1 kHz, original gain, natural release and ending silence. No original reference SID or reference recording is included. This custom player has no SID-Wizard module or standalone PRG export.

The [owning study](../../docs/research/composition/rambo-preparation.md#independent-compiled-loader-and-musical-delivery) records acceptance of the characteristic phrase and natural ending on 2026-10-13: the listener heard no difference in those comparisons. This is a scoped listening verdict, not PCM or hardware identity. Packaging retained those SID/WAV bytes; a fresh full compile reproduced the SID exactly while checking all 11,000 calls, 87,534 ordered stores and ten state checkpoints. The WAV was not regenerated.

## Reproduce the complete version from corresponding source

The manifest lists the complete tracked score, assembly templates, compiler and transitive local imports with SHA-256 fingerprints at commit `23acbec4d2de99c0f950354694f5b6063ce001b7`. Those pins preserve the exact corresponding source as the compiler evolves; the optional stereo export also guards unchanged default mono SID bytes. Build from the repository root after installing the [documented Python dependencies](../../README.md#requirements-and-setup), including py65 1.2.0:

```sh
PYTHONPATH=.tools/test-deps python3 scripts/compose-rambo.py songs/rambo-loader.json --output build/rambo-public-rebuild
```

This produces `build/rambo-public-rebuild/reconstructed.sid` and verification receipts without downloading the original SID or reading evidence archives. Its expected SHA-256 is `9a6901e656f4de1888f9acc71c80abaf3608b9758b559b306b0b8b6eaa64aecd`. Use a fresh output directory for another run.

After [setting up the libsidplayfp 3.1.1/SIDLite renderer](../../docs/workflows/audio-workflow.md), render the full preview:

```sh
.local/bin/render-sid build/rambo-public-rebuild/reconstructed.sid build/rambo-public-rebuild/reconstructed.wav 225 --clock pal --subtune 1
```

The bundled WAV's SHA-256 is `8d4ff6dcadc1a6c63332b7227ddb96d566a4a5a8a56491a4c97ce7844b956efb`. Its historical renderer source is pinned at [commit c31fcdd](https://github.com/mbackschat/sid-song-crafter/blob/c31fcdd591e9b463fa7f3863f0308cb2cc245e00/scripts/render-sid.cpp), with source, executable and library fingerprints in the manifest. To rebuild that renderer source, recover it with `git show c31fcdd591e9b463fa7f3863f0308cb2cc245e00:scripts/render-sid.cpp > build/rambo-public-rebuild/render-sid.cpp`, then use that source in the audio workflow's compile command. A newer renderer or different library build is not claimed to produce identical WAV bytes.

## Main-music demo, 2026-10-16

The [main SID](rambo-loader-main.sid) and [matching WAV](rambo-loader-main.wav) start at source play call **1,586**, or **31.641167 seconds**. The lead starts on the next frame. Playback runs through the original ending; the WAV includes the retained release/quiet tail and lasts 193.358821 seconds. This is the default README demonstration. The complete versions above remain the fidelity baseline.

The [entry preparer](../../scripts/studies/rambo/prepare-main-entry.py) executes the editable score to that boundary and retains the data, sound-program state, score cursors, transposition and call/loop stacks. A small init wrapper restores the SID register values with controls last. Subsequent notes remain computed by the existing player; this is not captured-event replay or a silent 32-second pre-roll. The SID's internal envelopes, oscillators and filter history start fresh, so its opening is not promised to be PCM-identical to a crop of the complete render. The rendered WAV comes from this new SID.

```sh
python3 scripts/listening-package.py samples/rambo-loader/main.recipe.json --output build/sample-rambo-loader-main
```

The [recipe](main.recipe.json) creates the editable rebased chip descriptions, init assembly, SID, WAV and fingerprints. It checks all 9,414 remaining calls against the original ordered play stores, the normal frame-cycle budget, initial and ending execution in headless VICE, unclipped PCM and a quiet final second. The [main manifest](main-manifest.json) pins the corresponding sources, output files and verification. This modification retains the package's GPLv3 terms and attribution.

Model-assistance review: no call. The user explicitly selected omission of the intro; source timing, complete execution and audio checks settle this packaging change. Listening acceptance of the underlying arrangement is unchanged; the newly initialized opening has not received a separate listening verdict.
