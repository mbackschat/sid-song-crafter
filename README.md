<p align="center">
  <img src="assets/branding/sid-song-crafter.webp" alt="SID Song Crafter — a musical note inside a SID chip" width="144" height="144">
</p>

# SID Song Crafter

**Give a familiar score a new voice on the Commodore 64.** SID Song Crafter helps you turn existing music into expressive performances for one SID chip or two chips in stereo.

The creative work is in the interpretation: choosing a lead that suits the melody, giving the bass room, shaping the phrasing, and using the chip's distinctive effects where they serve the music. The project brings together instruments, arrangement techniques and lessons from studying SID composers, with editable examples and tools to build and hear the result. [Read the project vision](PRODUCTS.md).

## Walkthrough: give Bach a SID voice

Bach's Toccata makes a good challenge. An organ can sustain a huge chord while the melody moves above it; one SID has just three voices. We want to keep the music's weight and drama while giving it the pace and electronic character of game music.

In this walkthrough you'll build our 88-second interpretation, listen to it, and try a different set of instruments on the same arranged score. You'll finish with audio you can play on your computer, a SID file for a music player, and a program you can run on a C64. The piece covers the Toccata from BWV 565, stopping before the Fugue.

### Get ready

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

Once those tools are ready, you can complete this walkthrough without an emulator window, C64 hardware or an AI service. VICE and MIDI-import dependencies are needed only for some of the other examples below.

### Start with the music

The [source MIDI and notation](songs/studies/bach-toccata-opening/source/) are included, along with their [provenance](docs/research/composition/bach-toccata.md#retained-source-files). The arrangement makes three choices that you can listen for:

| Musical intention | How this interpretation uses SID |
| --- | --- |
| Keep the organ's weight | Reserve a voice for the pedal bass when it matters, and use the remaining voices for melody and selected harmony. |
| Give the lead an electronic character | Vary its pulse width during a note, so its tone moves as it sounds. Selected chord tones also cycle rapidly to suggest a fuller harmony. |
| Keep the performance moving | Shorten long holds and gaps while allowing the fast runs and final cadence to keep their shape. |

These choices draw on the project's [sound repertoire](docs/research/composition/sound-design-repertoire.md) and its [organ phrasing example](docs/research/composition/gestures/driven-organ-phrasing.md). They are recorded in an editable [arrangement plan](songs/studies/bach-toccata-full/arrangement.json), separate from Bach's source notes.

Prepare that arrangement and build the song:

```sh
python3 scripts/studies/bach/prepare-toccata.py --output build/readme-toccata-inputs
python3 scripts/native-song.py build build/readme-toccata-inputs/hybrid.json --output build/readme-toccata
```

The first command prepares the three musical parts and their instrument recipes. The second creates the SID program and renders it to audio, checking note scheduling, clipping and the ending along the way. Each command prints progress. Use fresh output directories on subsequent runs to preserve earlier versions.

### Hear the result

Open `build/readme-toccata/native-song.wav` in your usual audio player. On macOS, you can play the opening first, then the whole piece:

```sh
afplay build/readme-toccata/native-song.excerpt.wav
afplay build/readme-toccata/native-song.wav
```

The excerpt lasts 20 seconds; the full performance lasts about 88 seconds. Press Ctrl+C to stop `afplay`, or use `open build/readme-toccata/native-song.wav` to launch your default player.

Follow the lead through the rapid passages, then listen to what the bass and harmony contribute underneath. Does the piece keep its weight without losing momentum? That is the musical goal behind the settings. This complete version has passed listening review; the [case study](songs/studies/bach-toccata-full/README.md) records the choices and their limits.

### Change the character without changing the score

A score alone does not determine the sound. Try the included sustained palette on the same arranged notes and timing:

```sh
python3 scripts/native-song.py build songs/studies/bach-toccata-full/restrained.json --output build/bach-sustained
python3 scripts/compare-audio.py prepare build/bach-sustained/native-song.excerpt.wav build/readme-toccata/native-song.excerpt.wav build/bach-palettes
```

Play `build/bach-palettes.ab.wav` in your audio player, or run `afplay build/bach-palettes.ab.wav` on macOS. You'll hear 20 seconds of the sustained palette, a short gap, then 20 seconds of the moving-pulse interpretation. The comparison adjusts their levels to make tone and texture easier to judge. Both are SID performances; the first is not an organ recording.

Notice how changing the instruments changes the impression of the same phrase. To explore further, open `build/readme-toccata-inputs/hybrid.json`: it contains the instrument programs and their assignments to the musical parts. Keep your experiments in a copy beside `score.json`, then build that recipe into another output directory. The [instrument cards](docs/research/composition/instruments/README.md) explain useful settings and the musical situations they suit.

Pacing and voicing live in `build/readme-toccata-inputs/arrangement.json`. To change those, edit a copy and regenerate with `python3 scripts/studies/bach/prepare-toccata.py --plan YOUR_PLAN.json --output A_FRESH_DIRECTORY`. This preparer knows the Bach arrangement; the shared native build tools can also build other songs.

### Take the song to a SID player or C64

You have more than a recording. The build also produced these files:

| File | How to use it |
| --- | --- |
| `build/readme-toccata/native-song.wav` | Open in a normal audio player. |
| `build/readme-toccata/export/hybrid.sid` | Open in a PSID-compatible music player. A normal WAV/MP3 player generally cannot play SID files. |
| `build/readme-toccata/export/hybrid.prg` | Open/autostart in VICE, or transfer to a C64 using your disk/SD device. |
| `build/readme-toccata/conversion/hybrid.swm` | Open in SID-Wizard to edit the native song. |

For VICE, select a PAL C64 with the MOS8580 SID model, then autostart the PRG. If it is loaded without autostart, type `RUN`. On a compatible real C64, use `LOAD"FILENAME",8,1`, substituting your filename and device number, then `RUN`. The hardware's SID model can affect the sound.

For NTSC playback, make a separate export:

```sh
python3 scripts/native-song.py build build/readme-toccata-inputs/hybrid.json --clock ntsc --output build/readme-toccata-ntsc
```

Play the SID or PRG from that new directory. [Regional export](docs/workflows/native-song-workflow.md#regional-export-targets) explains the timing and sound differences. Direct edits in SID-Wizard remain a separate native version; they do not flow back into the JSON recipe.

## Choose something else to play

These are the preferred listening files from the worked examples. **SID and WAV files are generated locally, not included in a fresh clone.** If a file already exists in your checkout, open it directly; otherwise use the build route below. On macOS, `afplay PATH.wav` plays any listed WAV.

| Example | Local WAV | Build route |
| --- | --- | --- |
| Bach Toccata — dramatic, moving pulse lead; 1:28 | [Complete performance](build/readme-toccata/native-song.wav) | Walkthrough above; SID: `build/readme-toccata/export/hybrid.sid` |
| Moon River — gentle triangle-led first statement; 1:39 | [Restrained interpretation](build/moon-river-restrained-listening/moon-river-sid.wav) | Commands below |
| Pink Panther — melody and lively pulse accompaniment; 3:20 | [Complete interpretation](build/pink-panther-full-listening/pulse-ensemble-complete.wav) | Commands below |
| Instrument mix — short three-voice sound demo; 0:10 | [Candidate mix](build/instrument-trials/mix-candidate/mix-candidate.wav) | `python3 scripts/run-instrument-trials.py --pair mix --output build/instrument-trials`; SID: `build/instrument-trials/mix-candidate/mix-candidate.sid` |

Moon River and Pink Panther additionally need [MIDI dependencies](docs/songs/fuer-elise-score.md#reproduce-and-verify) and [headless VICE with its data files](docs/setup/local-setup.md), because their recipes also run emulator checks. Their source MIDIs are downloaded separately. Once those prerequisites are ready:

```sh
# Moon River
python3 scripts/setup-project.py --only references --include moon-river-score
python3 scripts/listening-package.py config/listening/moon-river-restrained.json --output build/moon-river-restrained
python3 scripts/publish-listening.py build/moon-river-restrained/run.json --selection config/listening/moon-river-audition.json --output build/moon-river-restrained-listening

# Pink Panther
python3 scripts/setup-project.py --only references --include pink-panther-score
python3 scripts/listening-package.py config/listening/pink-panther-full.json --output build/pink-panther-full
python3 scripts/publish-listening.py build/pink-panther-full/run.json --selection config/listening/pink-panther-full.audition.json --output build/pink-panther-full-listening
```

The recipe runner reuses unchanged successful stages. The listening publisher needs a fresh destination; if the listed listening folder already exists, play it or choose another output folder. Each recipe's generated `listening.md` lists its audio and comparison files; the Pink Panther package also links its SID export. [Moon River's notes](songs/moon-river/README.md) and [Pink Panther's notes](songs/pink-panther/README.md) explain their musical briefs and source arrangements.

## Bring your own score

Start with a MIDI and, ideally, the notation or a reference performance. Give the interpretation a musical brief: intimate or forceful, spacious or driving, one SID or two. “Keep the melody clear and the bass warm” is a more useful starting point than “add more effects.”

The work follows the same sequence you explored with Bach: understand the music, choose which parts the chip will carry, select sounds for those roles, then build and listen. The [score workflow](docs/workflows/song-workflow.md#prepare-a-multitrack-score-audition) takes you through importing a multitrack MIDI and defining its reduction. The [repertoire](docs/research/composition/sound-design-repertoire.md) supplies techniques and examples to adapt. Printed/PDF notation needs transcription or a corresponding MIDI first; automatic sheet-music reading is not part of this workflow.

Once your reduced score and [native instrument recipe](docs/workflows/native-song-workflow.md) are ready:

```sh
python3 scripts/native-song.py build PATH_TO_YOUR_RECIPE.json --output build/my-song
```

Open `build/my-song/native-song.wav`. Compare the phrasing and balance with your musical brief, listen through the ending, and revise the arrangement or instruments where needed. Source selection and musical judgment remain part of the work; the build handles export, rendering and technical checks. For repeated comparisons, [listening recipes](docs/workflows/listening-package.md) automate the sequence and cache unchanged stages.

## Explore further

- [Technique lookup](docs/research/technique-index.md), [instruments](docs/research/composition/instruments/README.md) and [gestures](docs/research/composition/gestures/README.md): find a technique by musical purpose, with examples and listening evidence.
- [Study plan](docs/research/study-plan.md): composer studies, completed interpretations and the next musical task.
- [Two-SID workflow](docs/workflows/native-song-workflow.md#reusable-two-chip-test): six voices, separate chip roles and stereo output.
- [Setup guide](docs/setup/local-setup.md): optional reference downloads, dependency checks and platform details. `python3 scripts/doctor.py` reports readiness; it does not install missing tools.
- [Tool guide](scripts/README.md) and [documentation index](docs/README.md): supported workflows and detailed technical contracts.
- [Contributor guide](CLAUDE.md): development and publication rules. [AGENTS.md](AGENTS.md) links to the same guide.

Audio models are optional experiments; no model download or API account is required to build songs. Generated files live in ignored `build/`, third-party tools in `.tools/`, and local assets in `.local/`.

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
