# Repository Guidelines

## Musical Priority

Prioritize expressive, excellent SID sound. Study composers' music, interviews, analyses, editors, and drivers; preserve findings in [research](docs/research/README.md). Build a reusable, evidence-backed instrument repertoire. Technical playback success does not establish musical quality; record listening judgments separately.

## Project Structure & Module Organization

Research and provenance live in [docs/research](docs/research/README.md). Editable scores and the assembly player live in `songs/`, build/render tools in `scripts/`, tests in `tests/`, and installed skill sources in [skills](skills/README.md). Generated PRG, SID, WAV, and trace files go in ignored `build/`.

Keep third-party checkouts in ignored `.tools/`, runtime state in `.local/`, and machine configuration in `.codex/`; track portable examples in `config/`.

## Build, Test, and Development Commands

From the repository root, after dependency setup in [README.md](README.md):

- `bun scripts/build-song.ts`: assemble the opening excerpt and export PRG, PSID, and event manifest.
- `python3 scripts/song.py songs/fuer-elise.json`: build, render, and verify the full arrangement in headless VICE; see [the reusable workflow](docs/song-workflow.md).
- `bun test tests/music.test.ts tests/fuer-elise.test.ts`: check timing, binaries, and deterministic builds.
- `PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 -m unittest discover -s tests -p '*_test.py' -v`: run importer, CPU, audio, and workflow tests.

Use c64bridge's pinned Bun lockfile. Prefer `uv` for Python and `pnpm` for independent Node projects. Renderer setup is in [the audio guide](docs/audio-workflow.md).

## Coding Style & Naming Conventions

Use two-space TypeScript, four-space Python/C++, descriptive assembly labels, and `test_*` Python methods. No formatter is configured. Comments explain constraints. Keep Markdown paragraphs on single lines and link related documents. Organize research by topic with folder READMEs.

## Testing Guidelines

Use red/green TDD. Verify register writes, timing, rests, endings, and binaries. Distinguish CPU, rendered audio, VICE, and listening evidence; no coverage percentage is mandated. Preserve original sources, checksums, and provenance; report import losses and arrangement reductions. Common scores must not constrain SID-native expression. Label excerpts accurately.

## VICE Findings & Troubleshooting

Record commands, versions, logs, workarounds, and outcomes in [local setup](docs/local-setup.md), [the VICE investigation](docs/vice-startup-investigation.md), and [the audio guide](docs/audio-workflow.md).

The installed GTK VICE 3.9 opens in the user's Terminal but fails during OpenGL initialization when agent-launched. Disabling coloured logs and removing minimization did not fix it. `-headless` is unsupported by that binary; `-console` still invokes GTK. The genuine headless build runs the PRG; this session separately denies binary-monitor socket binding. Prefer file-based verification here. c64bridge defaults to dummy audio; use direct WAV output to avoid empty recordings.

## Commit & Pull Request Guidelines

Use Conventional Commits with an imperative subject; add a short body for non-obvious rationale. PRs describe behavior and verification. Respect `.gitignore`, retain dependency pins, and never create or switch worktrees without explicit instructions.
