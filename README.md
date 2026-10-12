# C64 SID music laboratory

Research and practical tools for composing Commodore 64 music for one SID, with a later path to two chips. The initial target is a short Für Elise opening excerpt on a PAL C64 with an 8580 SID.

## Start here

- [Research index](docs/research/README.md): hardware, composition, timing, formats, tools, and source provenance.
- [Local setup](docs/local-setup.md): installed skills, pinned dependencies, c64bridge configuration, and VICE findings.
- [First song](docs/first-song.md): editable score, assembler, PRG/SID exports, and independent CPU verification.
- [Headless audio](docs/audio-workflow.md): SID-to-WAV rendering and pitch, timing, and ending checks.
- [VICE investigation](docs/vice-startup-investigation.md): GTK crash mechanism, desktop comparison, and genuine headless build.
- [Installed skills](skills/README.md): the roles, sources, adaptations, and licensing of `c64-sid` and `sid-music`.
- [Contributor guide](AGENTS.md): development and verification conventions.

## Repository and dependencies

Project sources and research belong in Git. `.tools/` contains reproducible third-party checkouts; `.local/` contains diagnostics and runtime state; `build/` contains generated output. These directories and the machine-local `.codex/` configuration are ignored. The relative skill symlinks in `.agents/skills/` point to the versioned copies in `skills/`.

The checked-in [configuration example](config/codex.toml) records this machine's installation paths. Adapt it before activating it on another computer. Follow [local setup](docs/local-setup.md) for exact upstream revisions and installation commands; use the upstream Bun lockfile for c64bridge.

## Build the opening excerpt

The song build uses Bun and only the assembler from the pinned c64bridge checkout. On a fresh checkout, prepare that dependency:

```sh
git clone https://github.com/chrisgleissner/c64bridge.git .tools/c64bridge
git -C .tools/c64bridge checkout 0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18
(cd .tools/c64bridge && bun install --frozen-lockfile)
```

With the existing dependency already installed, run:

```sh
bun scripts/build-song.ts
bun test tests/music.test.ts
```

Edit [the score](songs/fuer-elise-opening.json) for pitches, durations, and instrument settings. The [assembly player](songs/player.asm) supplies callable SID initialization/play routines and the standalone C64 entry point. Output goes to `build/fuer-elise-opening.{prg,sid,asm,events.json}`. The excerpt contains the right-hand opening only; accompaniment and a second SID are outside this first example.

For independent CPU and audio checks, first follow dependency setup in [the song guide](docs/first-song.md) and [the audio guide](docs/audio-workflow.md), then run:

```sh
PYTHONPATH=.tools/test-deps python3 -m unittest discover -s tests -p '*_test.py' -v
.local/bin/render-sid build/fuer-elise-opening.sid build/fuer-elise-opening.wav 3.2
```

The resulting WAV can be played without an emulator window. Rendering and checking a file is separate from verifying access to the host's audio output.

## Verification status

The binary/header guards, independent 6502 execution tests, and SID-to-WAV pitch/timing checks pass. Genuine headless VICE also executes the standalone PRG through BASIC and returns after the excerpt. Binary-monitor socket binding is denied in this session, and host audio playback failed; neither a live MCP emulator connection nor listening verification is claimed. See the dated evidence in [local setup](docs/local-setup.md) and the [validation guide](docs/research/10-validation.md).
