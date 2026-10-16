# Rambo: centered-lead stereo arrangement

[Main-music SID](rambo-stereo-main.sid) · [Main-music WAV](rambo-stereo-main.wav) (about 3:13) · [Main-entry manifest](main-manifest.json) · [GNU GPL v3](LICENSE)

The complete revised two-SID arrangement is accepted: “Complete revised version : sounds great.” The README demos now omit the original introduction in both SID and WAV. The listener dislikes the introduction in the original tune itself; this is not a criticism of the reconstruction. The [complete SID](rambo-stereo.sid), [complete WAV](rambo-stereo.wav), [historical 32–64-second preview](rambo-stereo-featured-32-64.wav) and [historical manifest](manifest.json) remain unchanged.

The loading music from *Rambo: First Blood Part II* was composed, arranged and programmed by **Martin Galway** in 1985; its historical source credits “(C) Ocean Software 1985”. Galway's [upstream README](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/README.md), dated 14 April 2026, states that he acquired the music and programming rights from Infogrames, permits reassembly and modification, and requests credit. His repository supplies the [loader source](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/rambload.asm) and [GPL v3 license](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/LICENSE). The three pinned upstream files were retrieved and their recorded SHA-256 fingerprints rechecked on 2026-10-15.

**Modified version, packaged 2026-10-15:** SID Song Crafter independently reconstructed an [editable symbolic score](../../songs/rambo-loader.json) and computed player, then added source-derived held harmony and duplicated the native lead across both chips. Bounded oscillator-3 handoffs preserve the lead's sync/ring dependencies. This package, its music-derived score and arrangement descriptions, and the combined generated SID/WAV files are distributed under [GNU GPL version 3](LICENSE), without warranty. Independently authored reusable tools retain their separate [MIT license](../../LICENSE) when used separately. Preserve Galway's attribution and these notices when redistributing. No original reference SID, upstream driver binary or reference recording is included. The earlier [faithful mono reconstruction](../rambo-loader/README.md) remains a separate package.

## Play

Use **PAL, two MOS6581 chips at `$D400` and `$D420`, subtune 1**, with one call per 19,656 cycles. A PSID v3 player must support the second chip. Route SID A to the left and SID B to the right: both carry the lead, while accompaniment has independent roles on each side. A player with a different output mix can change the image. The [arrangement study](../../songs/studies/rambo-centered-native/README.md) records the allocation, shared-chip constraints and listening scope; a perceived center does not establish coherent oscillator phase.

The full WAV is 225 seconds of stereo PCM16 at 44.1 kHz, original gain, including the natural release and ending silence. The featured WAV is 32 seconds in the same format. On macOS:

```sh
afplay samples/rambo-stereo/rambo-stereo-main.wav
```

## Reproduce the complete version from corresponding source

The [manifest](manifest.json) pins complete source and transitive local imports at commit `b22d5e13699da9e76e651b06033ca36d21e0a087`, including the [centered arrangement](../../songs/studies/rambo-centered-native/arrangement.json), its [held-chord baseline](../../songs/studies/rambo-chord-expansion/arrangement.json), [preparer](../../scripts/studies/rambo/prepare-centered-native.py), [dual compiler](../../scripts/compose-rambo-dual.py), assembly templates and renderer. Use that revision's source for an exact SID rebuild. From the repository root, after installing the [documented dependencies](../../README.md#requirements-and-setup), including py65 1.2.0, choose fresh output directories:

```sh
python3 scripts/studies/rambo/prepare-centered-native.py songs/studies/rambo-centered-native/arrangement.json --output build/rambo-stereo-public-preparation
PYTHONPATH=.tools/test-deps python3 scripts/compose-rambo-dual.py build/rambo-stereo-public-preparation/primary.json build/rambo-stereo-public-preparation/secondary.json --calls 11000 --output build/rambo-stereo-public-export
```

The expected `reconstructed.sid` SHA-256 is `33dfda271536ea1c97de204bc415a8ff619f5c326a536ec0be4f9dc3a0f1c889`. This build needs no downloaded original SID, reference WAV or evidence archive. It verifies the complete 11,000-call sequence against the independently computed score/player state. This custom player has no SID-Wizard module or standalone PRG export.

After [setting up the libsidplayfp 3.1.1/SIDLite renderer](../../docs/workflows/audio-workflow.md), render the full preview:

```sh
.local/bin/render-sid build/rambo-stereo-public-export/reconstructed.sid build/rambo-stereo-public-export/reconstructed.wav 225 --clock pal --subtune 1
```

The bundled full WAV's SHA-256 is `c72cfab792214947717e02f3ef3b931af27af6fcd9dfa789a5189d196fd80e6c`. The manifest pins the renderer source, executable, library and settings; another renderer/library build is not claimed to produce identical audio. The [optional comparison recipe](../../config/listening/rambo-centered-native.json) retains the original full validation and audition pipeline, including its earlier accepted independent-render prerequisite. The [canonical evidence](../../evidence/rambo-centered-native/README.md) records complete CPU/VICE execution and signal checks. Packaging copied the accepted SID and full WAV without regenerating either.

Recreate the featured WAV from the full render using Python's standard library:

```sh
python3 - <<'PY'
from pathlib import Path
import wave

directory = Path('build/rambo-stereo-public-export')
with wave.open(str(directory / 'reconstructed.wav'), 'rb') as source:
    assert source.getparams()[:3] == (2, 2, 44100)
    parameters = source.getparams()
    source.setpos(32 * 44100)
    frames = source.readframes(32 * 44100)
    assert len(frames) == 32 * 44100 * 2 * 2
with wave.open(str(directory / 'rambo-stereo-featured-32-64.wav'), 'wb') as output:
    output.setparams(parameters)
    output.writeframes(frames)
PY
```

Its expected SHA-256 is `485ca71c8255c5a38481c5c7deeef7bb75163aa6eab7dd3ae269f780951a0c40` when the full-render bytes match. The excerpt preserves the running song's envelopes and oscillator history because it copies rendered frames. The main-entry package below supplies a separate computed score/player entry state. It has fresh SID sound history and is not claimed to match this historical PCM crop.

## Main-music demo, 2026-10-16

The [main SID](rambo-stereo-main.sid) and [matching WAV](rambo-stereo-main.wav) start at source play call **1,586**, or **31.641167 seconds**. The lead starts on the next frame. Playback runs through the original ending; the WAV includes the retained release/quiet tail and lasts 193.358821 seconds. This is the default README demonstration. The complete versions above remain the fidelity baseline.

The [entry preparer](../../scripts/studies/rambo/prepare-main-entry.py) executes the editable score to that boundary and retains the data, sound-program state, score cursors, transposition and call/loop stacks. A small init wrapper restores the SID register values with controls last. Subsequent notes remain computed by the existing player; this is not captured-event replay or a silent 32-second pre-roll. The SID's internal envelopes, oscillators and filter history start fresh, so its opening is not promised to be PCM-identical to a crop of the complete render. The rendered WAV comes from this new SID.

```sh
python3 scripts/listening-package.py samples/rambo-stereo/main.recipe.json --output build/sample-rambo-stereo-main
```

The [recipe](main.recipe.json) creates the editable rebased chip descriptions, init assembly, SID, WAV and fingerprints. It checks all 9,414 remaining calls against the original ordered play stores, the normal frame-cycle budget, initial and ending execution in headless VICE, unclipped PCM and a quiet final second. The [main manifest](main-manifest.json) pins the corresponding sources, output files and verification. This modification retains the package's GPLv3 terms and attribution.

On 2026-10-16, after receiving the trimmed Rambo stereo and Bach stereo WAVs, the listener said: “Wow, these two are great stereo versins”. This accepts both presented stereo versions. The main-entry stereo release is now accepted alongside the complete arrangement.

Model-assistance review, 2026-10-16 / feedback and closure: no call. Human acceptance settles this release; current models cannot adjudicate stereo preference. Reassess only for a new musical revision.
