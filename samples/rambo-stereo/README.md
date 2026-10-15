# Rambo: centered-lead stereo arrangement

[Featured WAV: 0:32–1:04](rambo-stereo-featured-32-64.wav) (32 seconds) · [Full SID](rambo-stereo.sid) (17,683 bytes) · [Full WAV](rambo-stereo.wav) (3:45) · [Manifest](manifest.json) · [GNU GPL v3](LICENSE)

The complete revised two-SID arrangement is accepted: “Complete revised version : sounds great.” The featured WAV starts at 0:32, where the listener finds the music becomes more engaging; the introduction was considered weak in the original too. It copies exactly seconds 32–64 from the accepted full render, at the original level, without fades or normalization. The full SID and full WAV retain the original introduction and complete ending. There is no separate excerpt SID.

The loading music from *Rambo: First Blood Part II* was composed, arranged and programmed by **Martin Galway** in 1985; its historical source credits “(C) Ocean Software 1985”. Galway's [upstream README](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/README.md), dated 14 April 2026, states that he acquired the music and programming rights from Infogrames, permits reassembly and modification, and requests credit. His repository supplies the [loader source](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/rambload.asm) and [GPL v3 license](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/LICENSE). The three pinned upstream files were retrieved and their recorded SHA-256 fingerprints rechecked on 2026-10-15.

**Modified version, packaged 2026-10-15:** SID Song Crafter independently reconstructed an [editable symbolic score](../../songs/rambo-loader.json) and computed player, then added source-derived held harmony and duplicated the native lead across both chips. Bounded oscillator-3 handoffs preserve the lead's sync/ring dependencies. This package, its music-derived score and arrangement descriptions, and the combined generated SID/WAV files are distributed under [GNU GPL version 3](LICENSE), without warranty. Independently authored reusable tools retain their separate [MIT license](../../LICENSE) when used separately. Preserve Galway's attribution and these notices when redistributing. No original reference SID, upstream driver binary or reference recording is included. The earlier [faithful mono reconstruction](../rambo-loader/README.md) remains a separate package.

## Play

Use **PAL, two MOS6581 chips at `$D400` and `$D420`, subtune 1**, with one call per 19,656 cycles. A PSID v3 player must support the second chip. Route SID A to the left and SID B to the right: both carry the lead, while accompaniment has independent roles on each side. A player with a different output mix can change the image. The [arrangement study](../../songs/studies/rambo-centered-native/README.md) records the allocation, shared-chip constraints and listening scope; a perceived center does not establish coherent oscillator phase.

The full WAV is 225 seconds of stereo PCM16 at 44.1 kHz, original gain, including the natural release and ending silence. The featured WAV is 32 seconds in the same format. On macOS:

```sh
afplay samples/rambo-stereo/rambo-stereo-featured-32-64.wav
```

## Reproduce from corresponding source

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

Its expected SHA-256 is `485ca71c8255c5a38481c5c7deeef7bb75163aa6eab7dd3ae269f780951a0c40` when the full-render bytes match. The excerpt preserves the running song's envelopes and oscillator history because it copies rendered frames. Starting a SID directly at 0:32 would require a separate score/player entry-state and sound-history contract, which the current full-song exporter does not provide.
