# From source music to SID

The workflow preserves the original music and separates musical interpretation from SID programming. A common score is an intermediate view, not a lossless replacement for every source format or the limit of SID expression.

## Information boundaries

| Layer | Responsibility | Retained evidence |
| --- | --- | --- |
| Original source | Preserve the supplied score or performance unchanged | Original files, URL, author/edition/license, checksum |
| Common musical score | Represent parts, pitches, exact musical timing, and supported metadata | Source linkage, import settings, unsupported-event report |
| SID arrangement | Choose voices, articulation, instruments, and reductions for a particular target | Arrangement recipe and explicit decisions about discarded or changed material |
| Executable player | Schedule chip register writes and export playable binaries | Assembly, register-event manifest, SID/PRG, rendered WAV, verification report |

Importing and arranging are different operations. A three-voice chord reduction must not overwrite the complete polyphonic score. Recovering notation, pedal intent, or other unrepresented information requires the preserved original; retaining the original does not make the intermediate representation lossless. Each new importer must disclose its supported subset and reject or report information it cannot map.

## SID expression

The chip-specific layer must remain independent of the common score. SID compositions can be authored directly and need not pass through MIDI or a note-only representation. Evolving waveforms, pulse-width modulation, frequency slides, vibrato, fast arpeggios, envelope changes, shared-filter automation, sync, and ring modulation belong at this layer; their timing and voice dependencies are musical data too. See [the hardware research](../research/sid/hardware.md) for chip semantics.

The current [three-voice exporter](../architecture/three-voice-player.md) implements a deliberately smaller subset: fixed instruments and frame-scheduled pitched notes on one PAL/8580 SID. Its assembly player consumes register writes, but the public score compiler does not yet expose arbitrary register automation. Neither this format nor its frame scheduler claims support for all SID techniques, cycle-timed sample playback, or two chips. Adding an effect requires an explicit player/compiler capability and verification, not silently flattening it into notes.

## Build an arranged song

After the dependency setup in [README](../../README.md), [the audio guide](audio-workflow.md), and [the VICE setup](../setup/vice-startup-investigation.md):

```sh
python3 scripts/song.py path/to/arrangement.json --name my-song
```

This builds PRG/SID/assembly/event files, renders a WAV, checks the register schedule and PCM, and runs the standalone PRG to completion in headless VICE. Outputs go to ignored `build/`; `my-song.verification.json` records the evidence. Use `--output DIRECTORY` to change the destination. `--renderer`, `--vice`, and `--vice-data` override local dependency paths.

Add `--vice-audio` for a separate full VICE/reSID WAV capture. This runs at normal emulation speed, so allow the song duration plus startup time. The default uses fast VICE execution with sound disabled and renders audio separately through libsidplayfp. Neither operation requires a window, network monitor, or host speaker access.

## Next-song checklist

1. Retain the original source and record its provenance and usage terms.
2. Select an existing importer or implement only the required adapter. Check its loss report, tempo, repeats, grace notes, and final rests against the source.
3. Keep the complete common score; create a separate SID arrangement with explicit voice allocation and reduction decisions.
4. Build and verify with `scripts/song.py`. Review the arrangement and listen to the resulting WAV: technical execution checks do not establish musical fidelity or artistic quality.
5. Record newly discovered limitations and reusable fixes alongside the relevant tool documentation.
