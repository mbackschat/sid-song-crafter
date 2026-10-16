<p align="center">
  <img src="assets/branding/sid-song-crafter.webp" alt="SID Song Crafter — a musical note inside a SID chip" width="144" height="144">
</p>

# SID Song Crafter

SID Song Crafter is a command-line toolkit and reference library for arranging existing musical scores for the Commodore 64 SID chip. It provides reusable instruments, documented arrangement techniques, and tools for producing playable SID files and standalone C64 programs.

## Rationale

Adapting a score to SID requires decisions about voice allocation, instrument design, phrasing and effects. Those decisions depend on the music, the chip and the playback driver. Converting note pitches and durations alone does not capture them.

This project studies how C64 composers such as Rob Hubbard, Martin Galway, Tim Follin, Ben Daglish, Chris Hülsbeck and Jeroen Tel used SID, and records the findings as editable instruments, worked arrangements and technical guides. The aim is to apply that knowledge to new scores without repeating the same research and implementation work. [PRODUCTS.md](PRODUCTS.md) describes the project scope.

A SID instrument can be a small program that shapes a note's attack, moving tone and release through waveform, pitch, pulse-width and filter changes. Its behavior also depends on timing, retrigger rules and shared chip resources. [Instruments as SID programs](docs/research/composition/instruments-as-programs.md) explains this model through verified master studies and the project's editable implementations.

## Features

- **Score preparation:** MIDI import with explicit track mappings, repeat handling and documented reductions into SID voices.
- **Instrument and arrangement library:** waveform, pulse-width, envelope, filter and pitch programs, with examples and listening findings.
- **Native export:** editable SID-Wizard songs (`.swm`/`.sws`), playable `.sid` files and standalone `.prg` programs.
- **Chip targets:** single-SID and dual-SID stereo, MOS6581/MOS8580, and explicit PAL or NTSC builds.
- **Build and comparison tools:** scripted rendering, cached listening packages, and A/B comparisons with recorded levels.
- **Verification:** checks for note scheduling, chip-register writes, clipping and endings, with separate VICE execution checks where configured.

The workflow uses scripts and editable JSON recipes. Instrument selection and arrangement are configured for each song; listening determines whether the result meets the musical brief.

## Downloads

These samples are included in the repository and can be played without building the project:

| Sample | Mono SID / WAV | Stereo SID / WAV | Materials |
| --- | --- | --- | --- |
| Bach Toccata — complete Toccata section, about 1:28 | [SID](samples/bach-toccata/bach-toccata.sid) · [WAV](samples/bach-toccata/bach-toccata.wav) | [Two-SID](samples/bach-toccata/bach-toccata-stereo.sid) · [WAV](samples/bach-toccata/bach-toccata-stereo.wav) | [Source, native modules, PRG and recipe](samples/bach-toccata/README.md) |
| Original instrument mix — 10-second three-part demo | [SID](samples/instrument-mix/instrument-mix.sid) · [WAV](samples/instrument-mix/instrument-mix.wav) | [Two-SID](samples/instrument-mix/instrument-mix-stereo.sid) · [WAV](samples/instrument-mix/instrument-mix-stereo.wav) | [Source, native modules, PRG and recipe](samples/instrument-mix/README.md) |
| Rambo loader — main music through the ending, about 3:13; intro omitted | [Faithful SID](samples/rambo-loader/rambo-loader-main.sid) · [WAV](samples/rambo-loader/rambo-loader-main.wav) | [Centered-lead arrangement](samples/rambo-stereo/rambo-stereo-main.sid) · [WAV](samples/rambo-stereo/rambo-stereo-main.wav) | [Mono materials](samples/rambo-loader/README.md) · [Stereo materials](samples/rambo-stereo/README.md) |

The Rambo demos start at the musical entrance at 31.64 seconds in the complete versions; both the SID and WAV omit the intro and retain the ending. Its stereo version is the accepted expanded arrangement. Bach and the instrument mix add stereo placement to the same three parts. The Bach stereo presentation and trimmed Rambo stereo release are listening-accepted; the instrument mix stereo presentation awaits listening review.

On GitHub, open a file and use **Download raw file**. Open a SID in a PSID-compatible player, a WAV in a normal audio player, or autostart a PRG in VICE. All samples target PAL; Bach and the instrument mix use MOS8580, Rambo uses MOS6581. Stereo SIDs require a two-SID player with `$D400` routed left and `$D420` right. [Sample details](samples/README.md) include source attribution, hashes and reproduction commands.

After cloning, macOS users can play the included Bach recording directly:

```sh
afplay samples/bach-toccata/bach-toccata.wav
```

## Build and run

The included Bach example builds an approximately 88-second interpretation of the Toccata from BWV 565, ending before the Fugue. Its score and arrangement are included in the repository.

### Requirements and setup

```sh
git clone https://github.com/mbackschat/sid-song-crafter.git
cd sid-song-crafter
```

You need Python 3.9+, uv, `curl`, `make` and a C/C++ compiler. Run the following commands from the repository directory:

```sh
uv --cache-dir .local/uv-cache pip install --target .tools/test-deps py65==1.2.0
python3 scripts/setup-sidwizard.py
```

Next, follow the [renderer setup](docs/workflows/audio-workflow.md#pinned-library-setup) to build `.local/bin/render-sid`, which turns the SID program into a WAV. That guide provides the verified Apple Silicon macOS setup; other platforms need a matching libsidplayfp build. A [checksum-verified Python dependency download](docs/songs/first-song.md#build-and-verify) is also available.

The Bach build runs from the command line. The other examples identify any additional MIDI or VICE dependencies they need.

### Build the demo

```sh
python3 scripts/studies/bach/prepare-toccata.py --output build/readme-toccata-inputs
python3 scripts/native-song.py build build/readme-toccata-inputs/hybrid.json --output build/readme-toccata
```

The first command prepares the three musical parts and their instrument recipes. The second creates the SID program and renders it to audio, checking note scheduling, clipping and the ending along the way. Each command prints progress. Use fresh output directories on subsequent runs to preserve earlier versions.

### Play the song

The main output is `build/readme-toccata/export/hybrid.sid`. Open it in a PSID-compatible player using PAL timing and the MOS8580 model. For a C64 or VICE, use `build/readme-toccata/export/hybrid.prg`; [playback instructions](#playback-formats) are below.

The build also renders a WAV preview, so you can listen without installing a SID player. On macOS:

```sh
afplay build/readme-toccata/native-song.wav
```

On other systems, open that WAV in your normal audio player. `native-song.excerpt.wav` in the same folder contains the first 20 seconds. These are rendered previews of the SID output.

## Walkthrough: from score to SID arrangement

The Bach example demonstrates how the score, arrangement and instrument definitions work together. Follow it to understand what to change when preparing another piece.

### 1. Select the parts and define the phrasing

The [source MIDI and notation](songs/studies/bach-toccata-opening/source/) are included, along with their [provenance](docs/research/composition/bach-toccata.md#retained-source-files). The organ score is reduced to three voices. The arrangement records these decisions:

| Musical intention | How this interpretation uses SID |
| --- | --- |
| Keep the organ's weight | Reserve a voice for the pedal bass when it matters, and use the remaining voices for melody and selected harmony. |
| Give the lead an electronic character | Vary its pulse width during a note, so its tone moves as it sounds. Selected chord tones also cycle rapidly to suggest a fuller harmony. |
| Keep the performance moving | Shorten long holds and gaps while allowing the fast runs and final cadence to keep their shape. |

These choices draw on the project's [sound repertoire](docs/research/composition/sound-design-repertoire.md) and its [organ phrasing example](docs/research/composition/gestures/driven-organ-phrasing.md). They are recorded in an editable [arrangement plan](songs/studies/bach-toccata-full/arrangement.json), separate from Bach's source notes.

### 2. Compare instrument choices

Build the alternative sustained instrument palette using the same arranged notes and timing:

```sh
python3 scripts/native-song.py build songs/studies/bach-toccata-full/restrained.json --output build/bach-sustained
python3 scripts/compare-audio.py prepare build/bach-sustained/native-song.excerpt.wav build/readme-toccata/native-song.excerpt.wav build/bach-palettes
```

Play `build/bach-palettes.ab.wav` in your audio player, or run `afplay build/bach-palettes.ab.wav` on macOS. You'll hear 20 seconds of the sustained palette, a short gap, then 20 seconds of the moving-pulse interpretation. The comparison adjusts their levels to make tone and texture easier to judge. Both are SID performances; the first is not an organ recording.

To change the instruments, edit `build/readme-toccata-inputs/hybrid.json`: it contains the instrument programs and their assignments to the musical parts. Keep your experiments in a copy beside `score.json`, then build that recipe into another output directory. The [instrument cards](docs/research/composition/instruments/README.md) explain useful settings and the musical situations they suit.

Pacing and voicing live in `build/readme-toccata-inputs/arrangement.json`. To change those, edit a copy and regenerate with `python3 scripts/studies/bach/prepare-toccata.py --plan YOUR_PLAN.json --output A_FRESH_DIRECTORY`. This preparer knows the Bach arrangement; the shared native build tools can also build other songs.

## Playback formats

Use the output appropriate to your player or editor:

| File | How to use it |
| --- | --- |
| `build/readme-toccata/export/hybrid.sid` | Open in a PSID-compatible music player. A normal WAV/MP3 player generally cannot play SID files. |
| `build/readme-toccata/export/hybrid.prg` | Open/autostart in VICE, or transfer to a C64 using your disk/SD device. |
| `build/readme-toccata/conversion/hybrid.swm` | Open in SID-Wizard to edit the native song. |
| `build/readme-toccata/native-song.wav` | Optional audio preview for a normal media player. |

For VICE, select a PAL C64 with the MOS8580 SID model, then autostart the PRG. If it is loaded without autostart, type `RUN`. On a compatible real C64, use `LOAD"FILENAME",8,1`, substituting your filename and device number, then `RUN`. The hardware's SID model can affect the sound.

For NTSC playback, make a separate export:

```sh
python3 scripts/native-song.py build build/readme-toccata-inputs/hybrid.json --clock ntsc --output build/readme-toccata-ntsc
```

Play the SID or PRG from that new directory. [Regional export](docs/workflows/native-song-workflow.md#regional-export-targets) explains the timing and sound differences. Direct edits in SID-Wizard remain a separate native version; they do not flow back into the JSON recipe.

## Examples

Bach, the original instrument mix and both the faithful and stereo Rambo arrangements have [ready-to-play downloads](#downloads). Moon River and Pink Panther have sample packages that build both mono and stereo SID/WAV files locally; their song files are not distributed here because composition and source-arrangement permissions remain unresolved.

| Example | Arrangement | Build and play |
| --- | --- | --- |
| [Bach Toccata](samples/bach-toccata/README.md) | Complete Toccata section; mono and stereo; about 1:28 | [Downloads](#downloads) and reproducible package above. |
| [Moon River](samples/moon-river/README.md) | Restrained first statement; mono and stereo; about 1:39 | Build below; both SID/WAV versions appear in `build/sample-moon-river-stereo/listening.md`. |
| [Pink Panther](samples/pink-panther/README.md) | Complete sourced arrangement with pulse accompaniment; mono and stereo; about 3:20 | Build below; both SID/WAV versions appear in `build/sample-pink-panther-stereo/listening.md`. |
| [Instrument mix](samples/instrument-mix/README.md) | Original three-part test phrase; mono and stereo; 10 seconds | [Downloads](#downloads) and package build recipe above. |

Moon River and Pink Panther additionally need [MIDI dependencies](docs/songs/fuer-elise-score.md#reproduce-and-verify) and [headless VICE with its data files](docs/setup/local-setup.md), because their recipes also run emulator checks. Prepare the stereo exporter with `python3 scripts/setup-sidwizard.py --sid-count 2`. Their source MIDIs are downloaded separately. Once those prerequisites are ready:

```sh
# Moon River
python3 scripts/setup-project.py --only references --include moon-river-score
python3 scripts/listening-package.py samples/moon-river/stereo.recipe.json --output build/sample-moon-river-stereo

# Pink Panther
python3 scripts/setup-project.py --only references --include pink-panther-score
python3 scripts/listening-package.py samples/pink-panther/stereo.recipe.json --output build/sample-pink-panther-stereo
```

The new stereo presentations retain the source notes and instruments, with the melody centered and accompaniment split between the chips; their listening review is pending. The recipe runner reuses unchanged successful stages. After a build, open its generated `listening.md` on your computer to find the SID and PRG exports, rendered audio and comparison files. [Moon River's notes](songs/moon-river/README.md) and [Pink Panther's notes](songs/pink-panther/README.md) explain their musical briefs and source arrangements.

## Use your own score

Start with a MIDI and, where available, the notation and a reference performance. Decide which parts to preserve, the intended character of the arrangement, and whether to target one SID or two.

The work follows the same sequence you explored with Bach: understand the music, choose which parts the chip will carry, select sounds for those roles, then build and listen. The [score workflow](docs/workflows/song-workflow.md#prepare-a-multitrack-score-audition) takes you through importing a multitrack MIDI and defining its reduction. The [repertoire](docs/research/composition/sound-design-repertoire.md) supplies techniques and examples to adapt. Printed/PDF notation needs transcription or a corresponding MIDI first; automatic sheet-music reading is not part of this workflow.

Once your reduced score and [native instrument recipe](docs/workflows/native-song-workflow.md) are ready:

```sh
python3 scripts/native-song.py build PATH_TO_YOUR_RECIPE.json --output build/my-song
```

The build writes SID and PRG files under `build/my-song/export/`, plus `build/my-song/native-song.wav` for previewing. Compare the phrasing and balance with your musical brief, listen through the ending, and revise the arrangement or instruments where needed. Source selection and musical judgment remain part of the work; the build handles export, rendering and technical checks. For repeated comparisons, [listening recipes](docs/workflows/listening-package.md) automate the sequence and cache unchanged stages.

## Explore further

- [Technique lookup](docs/research/technique-index.md), [instruments](docs/research/composition/instruments/README.md) and [gestures](docs/research/composition/gestures/README.md): find a technique by musical purpose, with examples and listening evidence.
- [Study plan](docs/research/study-plan.md): composer studies, completed interpretations and the next musical task.
- [Two-SID workflow](docs/workflows/native-song-workflow.md#reusable-two-chip-test): six voices, separate chip roles and stereo output.
- [Setup guide](docs/setup/local-setup.md): optional reference downloads, dependency checks and platform details. `python3 scripts/doctor.py` reports readiness; it does not install missing tools.
- [Tool guide](scripts/README.md) and [documentation index](docs/README.md): supported workflows and detailed technical contracts.
- [Contributor guide](CLAUDE.md): development and publication rules. [AGENTS.md](AGENTS.md) links to the same guide.

Audio models are optional experiments; no model download or API account is required to build songs. Working output lives in ignored `build/`, reviewed song downloads in `samples/`, third-party tools in `.tools/`, and local assets in `.local/`.

## Prepare the assembler

For the alternative Bun-based examples and their tests, prepare the pinned c64bridge assembler. The native Bach walkthrough above uses its own assembler and does not need this checkout:

```sh
git clone https://github.com/chrisgleissner/c64bridge.git .tools/c64bridge
git -C .tools/c64bridge checkout 0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18
(cd .tools/c64bridge && bun install --frozen-lockfile)
```

## Development checks

After installing the relevant [development dependencies](docs/setup/local-setup.md):

```sh
bun test tests/music.test.ts tests/fuer-elise.test.ts
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 -m unittest discover -s tests -p '*_test.py' -v
```

Integration tests need the tools named by their owning workflows. Running the full suite is not a prerequisite for listening to the examples.

## License

Original project work is available under the [MIT License](LICENSE). Music sources and third-party components retain their own terms; see [third-party notices](THIRD_PARTY_NOTICES.md).
