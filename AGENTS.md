# Repository Guidelines

## Musical Priority

**SID Song Crafter** is a composition and sound-design workbench for the Commodore 64 SID chip, supporting single- and dual-SID music.

Prioritize expressive SID interpretations: capture a song's character through phrasing, groove, improvisation and native chip effects. Preserve source material separately from deliberate arrangement changes. Treat songs as case studies for learning sound design and building reusable tools and methods. Study composers, published accounts, editors and drivers; preserve findings in [research](docs/research/README.md). Extend the [sound repertoire](docs/research/composition/sound-design-repertoire.md) and [musical gesture library](docs/research/composition/gestures/README.md) with editable examples, useful contexts, limitations and listening evidence. Record reusable findings, source provenance and reproduction instructions; do not keep debugging diaries. Technical playback success does not establish musical quality; record listening judgments separately.

## Retrieve and Apply Knowledge

Before SID technique explanations, arrangement, sound design or listening-feedback changes, consult the [technique lookup](docs/research/technique-index.md), then read the relevant evidence and any reusable example. Search existing knowledge before new research. Choose methods by musical purpose and voice/filter/model constraints; check the owning card's listening verdict before reuse. Retain useful decisions in the existing study/recipe documentation, not a diary. When retrieval fails, improve the index's route or aliases.

## Project Structure & Module Organization

Navigate operational guides through [docs/README.md](docs/README.md); use task-oriented subfolders. Research and provenance live in [docs/research](docs/research/README.md), scores/native instruments in `songs/`, tools in `scripts/`, tests in `tests/`, and installed skill sources in [skills](skills/README.md). Generated binaries, audio and working traces go in ignored `build/`. Promote canonical analysis records to [evidence](evidence/README.md), with compressed records in Git LFS and readable hash manifests in ordinary Git.

Keep third-party checkouts in ignored `.tools/`, runtime state in `.local/`, and machine configuration in `.codex/`; track portable examples in `config/`.

Follow [tool boundaries](scripts/README.md): shared workflows and supported composition backends remain in `scripts/`; source-specific extractors, experiments and fixed examples belong in [scripts/studies](scripts/studies/README.md). Document compatibility exceptions instead of breaking existing consumers or rewriting frozen provenance.

## Build, Test, and Development Commands

From the repository root, install pinned assets with `python3 scripts/setup-project.py` and check readiness with `python3 scripts/doctor.py`. Read [skill corrections](docs/setup/skill-guidance.md) before using installed upstream instructions. After dependency setup in [README.md](README.md):

- `bun scripts/build-song.ts`: assemble the opening excerpt and export PRG, PSID, and event manifest.
- `python3 scripts/song.py songs/fuer-elise.json`: build, render, and verify the full arrangement in headless VICE; see [the reusable workflow](docs/workflows/song-workflow.md).
- `python3 scripts/setup-sidwizard.py`, then `python3 scripts/run-instrument-trials.py --output build/instrument-trials`: prepare native Extra exports and [A/B trials](docs/workflows/instrument-trials.md). Use a fresh output directory.
- `python3 scripts/native-song.py build songs/fuer-elise-sidwizard.json --output build/fuer-elise-native`: build and audit the [native sound-design candidate](docs/workflows/native-song-workflow.md); [VICE checkpoints](docs/validation/native-vice-checks.md) independently check its standalone PRG.
- `bun test tests/music.test.ts tests/fuer-elise.test.ts`: check timing, binaries, and deterministic builds.
- `PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 -m unittest discover -s tests -p '*_test.py' -v`: run importer, CPU, audio, and workflow tests.

Use c64bridge's pinned Bun lockfile. Native integration tests require SID-Wizard setup. Renderer setup is in [the audio guide](docs/workflows/audio-workflow.md).

## Coding Style & Naming Conventions

Use two-space TypeScript, four-space Python/C++, descriptive assembly labels, and `test_*` Python methods. No formatter is configured. Comments explain constraints. Keep Markdown paragraphs on single lines, link related documents, and organize research with folder READMEs.

## Testing Guidelines

Apply the [project-specific testing policy](CLAUDE.md#choose-validation-that-answers-the-question): use red/green TDD where it adds meaningful protection, and experiment, trace or listen where those provide the relevant evidence. Verify register writes, timing, endings and binaries as appropriate. Distinguish CPU, rendered audio, VICE and listening evidence. Preserve original sources and checksums; report conversion losses. Common scores must not constrain native SID expression. Label excerpts accurately.

Stock SID-Wizard Extra at tempo 1 initializes only the frequency high byte on a new note's first frame. Retain TEST silence there and verify the following full-pitch body; one-frame graces need an explicit timing adjustment. See [the reproduced constraint and policy](docs/songs/fuer-elise-native.md).

## VICE Findings & Troubleshooting

Record reusable constraints, verified workarounds and reproduction commands in [local setup](docs/setup/local-setup.md), [the VICE investigation](docs/setup/vice-startup-investigation.md), and [the audio guide](docs/workflows/audio-workflow.md). Keep raw diagnostics in ignored output directories.

GTK VICE 3.9 opens in the user's Terminal but fails agent-launched OpenGL initialization; log-colour/minimization changes do not fix it. Its `-headless` is unsupported and `-console` still invokes GTK. Use the genuine headless build and file-based monitor; this session denies socket binding. c64bridge's dummy audio can produce empty recordings; capture directly to WAV without warp.

Select the default SID subtune before libsidplayfp playback; an unselected tune passes `$ff` to init. Keep this [regression finding](docs/workflows/audio-workflow.md) in future renderers.

## Public Repository Boundary

Keep original reference SID binaries out of the public repository, including history and LFS. Record each source URL and SHA-256 fingerprint in [the asset registry](config/local-assets.json); use [the verified downloader](scripts/setup-project.py) on demand. Keep reference WAVs out of Git under ignored `.local/` or `build/`; document exact reproduction commands, source hashes, subtune, renderer/version/settings, duration, gain, trim points and output hashes. Analysis artifacts, traces, lookup tables, editable descriptions and reusable code may be tracked when useful. Preserve complete evidence alongside concise prose, with source hashes, settings and reproduction commands. Downloaded skills retain the ignored `skills/<name>/` installation layout. Never force-add original SID files; check tracked files and history before publishing.

## Commit & Pull Request Guidelines

Use Conventional Commits with an imperative subject; add a short body for non-obvious rationale. PRs describe behavior and verification. Respect `.gitignore`, retain dependency pins, and never create or switch worktrees without explicit instructions.
