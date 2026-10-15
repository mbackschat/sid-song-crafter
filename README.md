<p align="center">
  <img src="assets/branding/sid-song-crafter.webp" alt="SID Song Crafter — a musical note inside a SID chip" width="144" height="144">
</p>

# SID Song Crafter

A workbench for creative interpretations of existing musical scores on the **Commodore 64 SID chip**, supporting **single-SID and dual-SID stereo music**.

SID Song Crafter builds and uses a body of musical and technical knowledge to turn a given score into an inspiring SID performance. Creativity lies in choosing instruments, arranging the voices, shaping phrasing and applying effects or stereo to express the song's character. Making full use of the chip includes subtlety and restraint when the music calls for them. Original score composition is outside the current remit unless explicitly requested; see the [product purpose and scope](PRODUCTS.md).

Studies of SID composers, editors and drivers feed an executable library of instruments, arrangement techniques, examples and reusable tools, with listening evidence and limitations. Each new interpretation should apply and extend that knowledge so the next song benefits from what was learned. Original musical sources, common scores and SID arrangements remain separate so conversion does not erase source information or define the chip's expressive limits.

The working targets are PAL with one MOS6581/MOS8580 or two matching chips at `$D400/$D420`; native recipes default to MOS8580 and can select `sidModel: "MOS6581"`.

## Test-drive: build and hear Bach on SID

Start with our accepted **Toccata from Bach's BWV 565**: about 88 seconds combining organ-like weight, a moving pulse lead, rapid runs and a deliberate final cadence. This is the complete Toccata section, ending before the Fugue. The [case study](songs/studies/bach-toccata-full/README.md) records the arrangement and listening verdict.

The score and interpretation inputs are included. You can build and listen locally without a model account, model weights, live bridge or C64 hardware.

### 1. Prepare the native toolchain

```sh
git clone https://github.com/mbackschat/sid-song-crafter.git
cd sid-song-crafter
```

Run subsequent commands from this directory. You need Python 3.9+, uv, `curl`, `make` and a C/C++ compiler. The documented renderer setup was verified on Apple Silicon macOS; other platforms need a matching libsidplayfp build.

| Prepare once | How |
| --- | --- |
| Python CPU emulator | `uv --cache-dir .local/uv-cache pip install --target .tools/test-deps py65==1.2.0` ([checksum-verified wheel alternative](docs/songs/first-song.md#build-and-verify)) |
| Audio renderer at `.local/bin/render-sid` | Follow [the pinned renderer build commands](docs/workflows/audio-workflow.md#pinned-library-setup) |
| SID-Wizard exporter and assembler | Run `python3 scripts/setup-sidwizard.py`; it downloads, verifies and builds the pinned tools |

This native test drive does not require Bun, VICE, ROMs or MIDI-import packages. `setup-project.py` downloads study assets and skills; it does **not** install the renderer or this complete toolchain.

### 2. Prepare, build and render

```sh
python3 scripts/studies/bach/prepare-toccata.py --output build/readme-toccata-inputs
python3 scripts/native-song.py build build/readme-toccata-inputs/hybrid.json --output build/readme-toccata
```

The first command applies the retained arrangement plan to the preserved Bach source notes. The second exports an editable native song, checks the complete player schedule, renders audio, and checks clipping and the ending. The commands print progress; build time depends on your machine. Choose fresh output directories for another run, because existing evidence is preserved.

### 3. Listen now

On macOS:

```sh
afplay build/readme-toccata/native-song.excerpt.wav
afplay build/readme-toccata/native-song.wav
```

The first file plays the opening 20 seconds; the second plays the complete 88-second interpretation. Press Ctrl+C to stop playback. Listen for the lead's tone movement, the bass underneath the rapid passages, and the final cadence and decay.

Alternatively, open the WAV in your normal music player. On macOS, `open build/readme-toccata/native-song.wav` launches the default app; on other systems, open the same file in a WAV-capable player. These files exist locally after building; GitHub does not host the generated audio.

## Walkthrough: from the Bach score to a playable SID song

The path is **preserved source score → arrangement decisions → three SID voices and instruments → editable native module → SID, PRG and WAV**. The source supplies the musical material; the arrangement supplies pacing, voicing and chip expression.

### Start from an attributed score

The included [MIDI](songs/studies/bach-toccata-opening/source/ToccataFugue.mid), [LilyPond notation](songs/studies/bach-toccata-opening/source/ToccataFugue.ly) and [extracted source notes](songs/studies/bach-toccata-opening/source-notes.json) retain the Mutopia/Bach-Gesellschaft source. [The source record](docs/research/composition/bach-toccata.md#retained-source-files) identifies its edition and fingerprints. The interpretation uses the Toccata through source quarter position 118 and excludes the Fugue pickup.

### Decide how the score should sound on SID

[The arrangement plan](songs/studies/bach-toccata-full/arrangement.json) records the musical choices: shorten long pauses for forward motion, allocate melody/bass/harmony, preserve the pedal where it matters, and cycle selected chord tones when three voices cannot hold the full organ texture. Source notes remain separate from these deliberate changes.

The preparation command above generates these editable files in `build/readme-toccata-inputs/`:

| File | What to inspect or change |
| --- | --- |
| `arrangement.json` | Timing anchors, voicing, ornaments and source-backed chord cycles |
| `score.json` | The resulting three-voice performance |
| `hybrid.json` | Moving pulse lead, filtered bass, harmony and instrument assignments |
| `restrained.json` | The same reduced score with a more sustained SID palette |
| `preparation.json` | Source fingerprints and the accounting of retained, shortened, cycled and omitted notes |

This preparer is specific to the Bach case. The shared native compiler, exporter, renderer and checks work across songs; choosing a convincing reduction and palette remains musical work. To change pacing or voicing, edit a copy of `arrangement.json` and rerun `prepare-toccata.py --plan YOUR_PLAN.json --output A_FRESH_DIRECTORY`. To try another tone, edit the generated `hybrid.json` instrument programs and rebuild into a fresh output directory. [The sound repertoire](docs/research/composition/sound-design-repertoire.md) helps choose instruments by musical purpose.

### Build the native song and inspect the results

The native build command above consumes `hybrid.json` and its referenced `score.json`. It produces:

| Output | File |
| --- | --- |
| First 20 seconds to audition | `build/readme-toccata/native-song.excerpt.wav` |
| Complete performance | `build/readme-toccata/native-song.wav` |
| Playable SID | `build/readme-toccata/export/hybrid.sid` |
| Standalone C64 program | `build/readme-toccata/export/hybrid.prg` |
| Editable SID-Wizard song | `build/readme-toccata/conversion/hybrid.swm` |
| Editable instruments | `build/readme-toccata/conversion/instruments/` |
| Export settings and hashes | `build/readme-toccata/export.json` |
| Technical verification | `build/readme-toccata/verification.json` |

The build verifies scheduling and audio health. Listening establishes whether the interpretation works musically; a changed palette needs a new listening judgment.

### Play on a computer or C64

- **Normal audio player:** open `build/readme-toccata/native-song.wav`, or use the `afplay` commands above. No emulator is needed to listen to the WAV.
- **SID player:** open `build/readme-toccata/export/hybrid.sid` in a PSID-compatible player. This example targets PAL timing and MOS8580; honor those settings if the player asks. A SID file contains music data and playback code, so a normal WAV/MP3 player generally cannot play it.
- **VICE emulator:** configure a PAL C64 with MOS8580, then open/autostart `build/readme-toccata/export/hybrid.prg`. If loaded without autostart, type `RUN`.
- **Real C64:** transfer the PRG using your usual disk/SD device, load it with `LOAD"FILENAME",8,1` (substitute the device filename and number), then `RUN`. Use compatible PAL hardware for this export; a different SID model can change the sound.
- **SID-Wizard editor:** load `build/readme-toccata/conversion/hybrid.swm` to inspect or edit the native song. Keep direct editor changes as a separate version; they do not automatically update the JSON recipe. See [native editing and export](docs/workflows/native-song-workflow.md).

For an NTSC machine, build a separate target:

```sh
python3 scripts/native-song.py build build/readme-toccata-inputs/hybrid.json --clock ntsc --output build/readme-toccata-ntsc
```

Use the new directory's SID/PRG on that target. The [regional export guide](docs/workflows/native-song-workflow.md#regional-export-targets) explains timing and timbre differences; PAL listening acceptance does not imply an identical NTSC sound.

### Supply a different score

Start with an attributed MIDI and, where possible, the notation it represents. For a printed/PDF score, first obtain or transcribe a MIDI and verify it against the notation; this workflow does not automatically read sheet music. Keep the original source intact.

1. Define source identity, track mappings, tempo and performance order in an import recipe. [The multitrack MIDI workflow](docs/workflows/song-workflow.md#prepare-a-multitrack-score-audition) and [Pink Panther's import recipe](config/scores/pink-panther-import.json) provide a worked route; replace their source-specific values with your own.
2. Choose the melody, bass and supporting parts and record the reduction. Check repeats and the ending against the notation. The Bach-specific preparer is not a generic importer for an arbitrary MIDI.
3. Define a native recipe pointing to your reduced score, with sections covering its form. Select instruments and effects from [the repertoire](docs/research/composition/sound-design-repertoire.md) for the song's mood.
4. Run `python3 scripts/native-song.py build PATH_TO_YOUR_RECIPE.json --output build/my-song`, then play `build/my-song/native-song.wav`. Compare a representative passage with the supplied performance or a plain rendering, and check the complete ending before accepting the result.

[The song workflow](docs/workflows/song-workflow.md) explains conversion contracts and musical decisions. Once the arrangement is established, [listening recipes](docs/workflows/listening-package.md) combine preparation, rendering and comparisons into one command and reuse unchanged stages.

## Explore the project

- [Musical purpose and scope](PRODUCTS.md): interpreting supplied scores through SID sound design.
- [Technique lookup](docs/research/technique-index.md) and [sound repertoire](docs/research/composition/sound-design-repertoire.md): instruments, gestures, examples and listening evidence from the composer studies.
- [Completed Bach Toccata trial](docs/research/composition/bach-toccata.md#experiment-closure-and-reusable-outcome), [Moon River](songs/moon-river/README.md) and [Pink Panther](songs/pink-panther/README.md): larger interpretation case studies with reproduction instructions and scoped verdicts.
- [Study plan](docs/research/study-plan.md): completed studies and the next interpretation task.
- [Documentation](docs/README.md) and [tool guide](scripts/README.md): setup, supported workflows and validation.
- [Contributor guide](CLAUDE.md): contributor and publication rules; [AGENTS.md](AGENTS.md) links to the same file.

## Prepare local assets and check tools

```sh
python3 scripts/setup-project.py
python3 scripts/doctor.py
```

Setup downloads the pinned Elise/Flashdance references and the `c64-sid` hardware skill. Add `--include sid-music` only for bridge workflows; use `--offline` with existing caches/checkouts or `--check` for read-only hash verification. [Local setup](docs/setup/local-setup.md) explains prerequisites, optional selections and repairs. Doctor checks dependencies, renderer, VICE build configuration, ROM availability and asset hashes; it does not install tools or certify musical playback.

Local audio models, including SongBench/MuQ, are optional research tools. Normal setup, readiness checks, song builds and tests require no model weights or ML dependencies. Only follow [optional model setup](docs/setup/local-setup.md#optional-local-audio-models) for a deliberate evaluation trial; the [measured results](docs/research/audio-assessment.md#measured-local-songbench-trial) do not qualify SongBench as a dependable musical judge.

## Repository and dependencies

`.tools/` contains reproducible third-party checkouts; `.local/` contains local assets and runtime state; `build/` contains generated output. These directories and machine-local `.codex/` configuration are ignored. Installed skill sources also remain local; see [the skill guide](skills/README.md).

[Setup](docs/setup/local-setup.md) downloads and verifies reference assets using [the source registry](config/local-assets.json). Retained analysis is indexed in [evidence](evidence/README.md); [the cache workflow](docs/workflows/build-cache.md) explains verification and restoration. Contributor and publication rules live in [CLAUDE.md](CLAUDE.md).

The checked-in [configuration example](config/codex.toml) records this machine's installation paths. Adapt it before activating it on another computer. Follow [local setup](docs/setup/local-setup.md) for exact upstream revisions and installation commands; use the upstream Bun lockfile for c64bridge.

## Native sound-design trials

After preparing the renderer and py65 dependency, build the pinned SID-Wizard exporter and run the original instrument bank:

```sh
python3 scripts/setup-sidwizard.py
python3 scripts/run-instrument-trials.py --output build/instrument-trials
```

Use a fresh output directory for a revised trial. The pipeline retains native SWM/SWI files, exports the actual Extra driver, audits its register writes, renders the phrases, and prepares amplitude-matched A/B audio. Start with the [candidate mix](build/instrument-trials/mix-candidate/mix-candidate.wav), then review the [individual comparisons and listening record](docs/workflows/instrument-trials.md). The user accepted the short mix as sounding OK; broader listening and hardware checks remain open.

For a complete score-based native build and all output paths, follow [the Bach walkthrough above](#walkthrough-from-the-bach-score-to-a-playable-sid-song).

For two SIDs, run `python3 scripts/setup-sidwizard.py --sid-count 2`, then use a recipe with `sidCount: 2` and six ordered voices. The [native workflow](docs/workflows/native-song-workflow.md) includes an original six-voice/two-filter fixture and commands that verify its PSID, separate stereo channels and standalone PRG in headless VICE. This is a reusable technical foundation; a complete dual-SID song and its listening assessment remain separate work.

## Prepare the assembler

The song build uses Bun and only the assembler from the pinned c64bridge checkout. On a fresh checkout, prepare that dependency:

```sh
git clone https://github.com/chrisgleissner/c64bridge.git .tools/c64bridge
git -C .tools/c64bridge checkout 0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18
(cd .tools/c64bridge && bun install --frozen-lockfile)
```

## Additional examples and validation

- [Native instrument trials](docs/workflows/instrument-trials.md): short A/B comparisons for pulse motion, pluck attacks and bass transients.
- [Complete Für Elise score and reduction](docs/songs/fuer-elise-score.md): an additional worked MIDI-import example, including explicit repeat handling and conversion reports.
- [Baseline song workflow](docs/workflows/song-workflow.md) and [three-voice player](docs/architecture/three-voice-player.md): the simpler Bun-based backend; `python3 scripts/song.py songs/fuer-elise.json` additionally requires the renderer and headless VICE.
- [Native VICE checks](docs/validation/native-vice-checks.md): independent execution checks beyond the native test drive's CPU audit and rendered audio.
- [Two-SID workflow](docs/workflows/native-song-workflow.md#reusable-two-chip-test): an original six-voice fixture, stereo rendering and standalone verification.

After installing the relevant [development dependencies](docs/setup/local-setup.md), run:

```sh
bun test tests/music.test.ts tests/fuer-elise.test.ts
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 -m unittest discover -s tests -p '*_test.py' -v
```

Integration tests need the tools named by their owning workflows. For a first listen, the native test drive above is sufficient; running the whole development suite is not a prerequisite.
