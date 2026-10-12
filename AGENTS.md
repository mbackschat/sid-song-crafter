# Repository Guidelines

## Musical Priority

Prioritize expressive SID sound. Treat songs as case studies for learning sound design and building reusable tools and methods. Study composers, published accounts, editors and drivers; preserve findings in [research](docs/research/README.md). Build an evidence-backed instrument repertoire. Record reusable findings, source provenance and reproduction instructions; do not keep debugging diaries. Technical playback success does not establish musical quality; record listening judgments separately.

## Project Structure & Module Organization

Research and provenance live in [docs/research](docs/research/README.md), scores/native instruments in `songs/`, tools in `scripts/`, tests in `tests/`, and installed skill sources in [skills](skills/README.md). Generated binaries, audio and traces go in ignored `build/`.

Keep third-party checkouts in ignored `.tools/`, runtime state in `.local/`, and machine configuration in `.codex/`; track portable examples in `config/`.

## Build, Test, and Development Commands

From the repository root, after dependency setup in [README.md](README.md):

- `bun scripts/build-song.ts`: assemble the opening excerpt and export PRG, PSID, and event manifest.
- `python3 scripts/song.py songs/fuer-elise.json`: build, render, and verify the full arrangement in headless VICE; see [the reusable workflow](docs/song-workflow.md).
- `python3 scripts/setup-sidwizard.py`, then `python3 scripts/run-instrument-trials.py --output build/instrument-trials`: prepare native Extra exports and [A/B trials](docs/instrument-trials.md). Use a fresh output directory.
- `python3 scripts/native-song.py build songs/fuer-elise-sidwizard.json --output build/fuer-elise-native`: build and audit the [native sound-design candidate](docs/native-song-workflow.md); [VICE checkpoints](docs/native-vice-checks.md) independently check its standalone PRG.
- `bun test tests/music.test.ts tests/fuer-elise.test.ts`: check timing, binaries, and deterministic builds.
- `PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 -m unittest discover -s tests -p '*_test.py' -v`: run importer, CPU, audio, and workflow tests.

Use c64bridge's pinned Bun lockfile. Native integration tests require SID-Wizard setup. Renderer setup is in [the audio guide](docs/audio-workflow.md).

## Coding Style & Naming Conventions

Use two-space TypeScript, four-space Python/C++, descriptive assembly labels, and `test_*` Python methods. No formatter is configured. Comments explain constraints. Keep Markdown paragraphs on single lines, link related documents, and organize research with folder READMEs.

## Testing Guidelines

Use red/green TDD. Verify register writes, timing, endings and binaries. Distinguish CPU, rendered audio, VICE and listening evidence. Preserve original sources and checksums; report conversion losses. Common scores must not constrain native SID expression. Label excerpts accurately.

Stock SID-Wizard Extra at tempo 1 initializes only the frequency high byte on a new note's first frame. Retain TEST silence there and verify the following full-pitch body; one-frame graces need an explicit timing adjustment. See [the reproduced constraint and policy](docs/fuer-elise-native.md).

## VICE Findings & Troubleshooting

Record reusable constraints, verified workarounds and reproduction commands in [local setup](docs/local-setup.md), [the VICE investigation](docs/vice-startup-investigation.md), and [the audio guide](docs/audio-workflow.md). Keep raw diagnostics in ignored output directories.

GTK VICE 3.9 opens in the user's Terminal but fails agent-launched OpenGL initialization; log-colour/minimization changes do not fix it. Its `-headless` is unsupported and `-console` still invokes GTK. Use the genuine headless build and file-based monitor; this session denies socket binding. c64bridge's dummy audio can produce empty recordings; capture directly to WAV without warp.

Select the default SID subtune before libsidplayfp playback; an unselected tune passes `$ff` to init. Keep this [regression finding](docs/audio-workflow.md) in future renderers.

## Commit & Pull Request Guidelines

Use Conventional Commits with an imperative subject; add a short body for non-obvious rationale. PRs describe behavior and verification. Respect `.gitignore`, retain dependency pins, and never create or switch worktrees without explicit instructions.
