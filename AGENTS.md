# Repository Guidelines

## Project Structure & Module Organization

Research and provenance live in [docs/research](docs/research/README.md). Editable scores and the assembly player live in `songs/`, build/render tools in `scripts/`, tests in `tests/`, and installed skill sources in [skills](skills/README.md). Generated PRG, SID, WAV, and trace files go in ignored `build/`.

Third-party checkouts belong in ignored `.tools/`; local binaries, caches, and diagnostics belong in `.local/`. Track the relative skill symlinks in `.agents/skills/`. Keep machine-specific `.codex/` configuration untracked; [config/codex.toml](config/codex.toml) is the documented example.

## Build, Test, and Development Commands

From the repository root, after dependency setup in [README.md](README.md):

- `bun scripts/build-song.ts`: assemble the opening excerpt and export PRG, PSID, and event manifest.
- `bun test tests/music.test.ts`: check score, timing, pitch, binary headers, and deterministic builds.
- `PYTHONPATH=.tools/test-deps python3 -m unittest discover -s tests -p '*_test.py' -v`: run independent CPU and audio tests after installing their documented dependencies.

Use the pinned upstream Bun lockfile for c64bridge. Prefer `uv` for Python dependencies and `pnpm` for any future independent Node project. See [the audio guide](docs/audio-workflow.md) for renderer setup and commands.

## Coding Style & Naming Conventions

Use two-space TypeScript, four-space Python/C++, and descriptive `test_*` Python test methods. No formatter is configured. Keep assembly labels descriptive. Prefer enum-based switches where appropriate. Comments explain constraints and cite their basis. Write Markdown paragraphs on single physical lines and use regular links to other documentation.

## Testing Guidelines

Use red/green TDD. Verify observable register writes, timing, rests, endings, and exported binaries. Keep CPU execution, SID audio rendering, VICE execution, and physical playback evidence distinct; no coverage percentage is mandated. Preserve musical-source provenance and label excerpts accurately.

## VICE Findings & Troubleshooting

Record commands, versions, logs, workarounds, and outcomes in [local setup](docs/local-setup.md), [the VICE investigation](docs/vice-startup-investigation.md), and [the audio guide](docs/audio-workflow.md).

The installed GTK VICE 3.9 opens in the user's Terminal but fails during OpenGL initialization when agent-launched. Disabling coloured logs and removing minimization did not fix it. `-headless` is unsupported by that binary; `-console` still invokes GTK. The genuine headless build runs the PRG; this session separately denies binary-monitor socket binding. Prefer file-based verification here. c64bridge defaults to dummy audio; use direct WAV output to avoid empty recordings.

## Commit & Pull Request Guidelines

Use Conventional Commits with an imperative subject; add a short body for non-obvious rationale. PRs describe behavior and verification. Respect `.gitignore`, retain dependency pins, and never create or switch worktrees without explicit instructions.
