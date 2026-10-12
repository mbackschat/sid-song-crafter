# C64 SID music laboratory

Research and reusable tools for composing expressive Commodore 64 music for one or two SIDs. Songs serve as case studies for learning sound design, preserving useful findings and improving the next arrangement. Sound quality is the priority: learn from the masters, study their editors and drivers, and build a tested instrument repertoire. The working targets are PAL with one MOS6581/MOS8580 or two matching chips at `$D400/$D420`; native recipes default to MOS8580 and can select `sidModel: "MOS6581"`. Original musical sources, common scores, and SID arrangements remain separate so conversion does not erase source information or define the chip's expressive limits.

## Start here

- [Research index](docs/research/README.md): hardware, composition, timing, formats, tools, and source provenance.
- [Composer studies](docs/research/composers/README.md): seven masters, published accounts, custom tools, and a listening catalogue.
- [Sound-design repertoire](docs/research/composition/sound-design-repertoire.md): proposed experiments and evidence required for reusable instruments.
- [Native instrument trials and samples](docs/instrument-trials.md): seven original patches, nine rendered studies, and four level-matched A/B comparisons.
- [Native Für Elise candidate](docs/fuer-elise-native.md): section-specific sound design, preserved source notes and explicit articulation changes.
- [Existing Für Elise comparison](docs/research/composition/fuer-elise-reference.md) and [Flashdance reference study](docs/research/composition/flashdance-reference.md): learn from archived arrangements, their players and register programs.
- [Native song workflow](docs/native-song-workflow.md): convert a retained score to editable SID-Wizard source, then export, audit and render it.
- [Native VICE checkpoints](docs/native-vice-checks.md): reproduce standalone-player register and cadence checks without a GUI.
- [Composition tools](docs/research/tools/composition-tools.md): established editors, their drivers, and a practical evaluation plan.
- [Song workflow](docs/song-workflow.md): source preservation, conversion boundaries, and one-command build/render/verification.
- [Full Für Elise source and arrangement](docs/fuer-elise-score.md): repeat expansion, musical landmarks, and explicit three-voice reductions.
- [Three-voice player](docs/three-voice-player.md): arrangement contract, capabilities, timing, and exported binaries.
- [Full-song validation](docs/fuer-elise-validation.md): rendering, native execution, and reproducible evidence.
- [Local setup](docs/local-setup.md): installed skills, pinned dependencies, c64bridge configuration, and VICE findings.
- [First song](docs/first-song.md): editable score, assembler, PRG/SID exports, and independent CPU verification.
- [Headless audio](docs/audio-workflow.md): SID-to-WAV rendering and pitch, timing, and ending checks.
- [VICE investigation](docs/vice-startup-investigation.md): GTK crash mechanism, desktop comparison, and genuine headless build.
- [Installed skills](skills/README.md): the roles, sources, adaptations, and licensing of `c64-sid` and `sid-music`.
- [Contributor guide](AGENTS.md): development and verification conventions.

## Repository and dependencies

Project sources and research belong in Git. `.tools/` contains reproducible third-party checkouts; `.local/` contains diagnostics and runtime state; `build/` contains generated output. These directories and the machine-local `.codex/` configuration are ignored. The relative skill symlinks in `.agents/skills/` point to the versioned copies in `skills/`.

The checked-in [configuration example](config/codex.toml) records this machine's installation paths. Adapt it before activating it on another computer. Follow [local setup](docs/local-setup.md) for exact upstream revisions and installation commands; use the upstream Bun lockfile for c64bridge.

## Native sound-design trials

After preparing the renderer and py65 dependency, build the pinned SID-Wizard exporter and run the original instrument bank:

```sh
python3 scripts/setup-sidwizard.py
python3 scripts/run-instrument-trials.py --output build/instrument-trials
```

Use a fresh output directory for a revised trial. The pipeline retains native SWM/SWI files, exports the actual Extra driver, audits its register writes, renders the phrases, and prepares amplitude-matched A/B audio. Start with the [candidate mix](build/instrument-trials/mix-candidate/mix-candidate.wav), then review the [individual comparisons and listening record](docs/instrument-trials.md). The user accepted the short mix as sounding OK; broader listening and hardware checks remain open.

To apply the palette to the complete Für Elise arrangement through the unmodified native Extra driver:

```sh
python3 scripts/native-song.py build songs/fuer-elise-sidwizard.json --output build/fuer-elise-native
```

This retains an editable SWM and instrument files alongside the SID, PRG, complete WAV, 20-second audition excerpt and conversion/verification reports. The [native recipe and timing record](docs/fuer-elise-native.md) explain the section contrasts and a one-frame grace-note adjustment. The original source and baseline arrangement remain available for comparison; native editing need not pass back through the common score.

For two SIDs, run `python3 scripts/setup-sidwizard.py --sid-count 2`, then use a recipe with `sidCount: 2` and six ordered voices. The [native workflow](docs/native-song-workflow.md) includes an original six-voice/two-filter fixture and commands that verify its PSID, separate stereo channels and standalone PRG in headless VICE. This is a reusable technical foundation; a complete dual-SID song and its listening assessment remain separate work.

## Prepare the assembler

The song build uses Bun and only the assembler from the pinned c64bridge checkout. On a fresh checkout, prepare that dependency:

```sh
git clone https://github.com/chrisgleissner/c64bridge.git .tools/c64bridge
git -C .tools/c64bridge checkout 0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18
(cd .tools/c64bridge && bun install --frozen-lockfile)
```

## Build and verify Für Elise

With the assembler, renderer, and headless VICE installed as described in [local setup](docs/local-setup.md) and [the audio guide](docs/audio-workflow.md):

```sh
python3 scripts/song.py songs/fuer-elise.json
```

This produces `build/fuer-elise.{sid,prg,wav}` plus assembly, register traces, and verification evidence. The arrangement covers the complete source with both printed repeats, reduced explicitly to three SID voices. It lasts approximately 157 seconds including the release and verification tails. Add `--vice-audio` for an independent VICE/reSID recording at normal emulation speed.

The checked-in arrangement can be built without MIDI dependencies. To regenerate it from the preserved original after installing Mido as documented in [the score guide](docs/fuer-elise-score.md):

```sh
PYTHONPATH=.tools/arrangement-deps python3 scripts/import-midi.py songs/sources/fuer-elise.mid songs/fuer-elise-import.json songs/sources/fuer-elise.score.json
python3 scripts/arrange-score.py songs/sources/fuer-elise.score.json songs/fuer-elise-arrangement.json songs/fuer-elise.json
```

The importer prints its information-loss report; the arranger prints its reduction report. Original MIDI and LilyPond sources remain unchanged. See [the workflow](docs/song-workflow.md) for the design boundaries and adapting the tools to another song; see [the player contract](docs/three-voice-player.md) for the currently supported SID subset.

## Opening excerpt and tests

The smaller original example remains useful for learning and independent pitch checks:

```sh
bun scripts/build-song.ts
bun test tests/music.test.ts tests/fuer-elise.test.ts
```

Edit [the score](songs/fuer-elise-opening.json) for pitches, durations, and instrument settings. The [assembly player](songs/player.asm) supplies callable SID initialization/play routines and the standalone C64 entry point. Output goes to `build/fuer-elise-opening.{prg,sid,asm,events.json}`. The excerpt contains the right-hand opening only; accompaniment and a second SID are outside this first example.

For independent CPU and audio checks, first follow dependency setup in [the song guide](docs/first-song.md) and [the audio guide](docs/audio-workflow.md), then run:

```sh
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 -m unittest discover -s tests -p '*_test.py' -v
.local/bin/render-sid build/fuer-elise-opening.sid build/fuer-elise-opening.wav 3.2
```

The resulting WAV can be played without an emulator window. Rendering and checking a file is separate from verifying access to the host's audio output.

## Verification status

The full three-voice arrangement passes binary/header guards, independent 6502 register-write checks, rendered audio checks, and genuine headless VICE execution through BASIC and back. An independent native VICE/reSID recording also passes clipping and ending checks; see [full-song evidence](docs/fuer-elise-validation.md). The complete [native SID-Wizard candidate](docs/fuer-elise-native.md) also passes source-note, grace-pitch, ending, rendered-audio and headless VICE checkpoint checks. Its listening verdict remains open; the user's initial short-mix feedback is recorded separately. Binary-monitor socket binding is denied in this session, and host audio playback failed; no live MCP emulator connection or assistant listening is claimed.
