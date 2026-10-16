# Local SID skills and VICE setup

## Components and current capabilities

The project installs ignored, checksum-pinned upstream skills under [skills](../../skills/README.md), third-party checkouts/builds under `.tools/`, runtime state under `.local/`, and machine-specific MCP configurations in ignored `.codex/config.toml` (Codex) and `.mcp.json` (Claude Code). Keep upstream revisions and notices intact.

| Component | Local source | Revision |
| --- | --- | --- |
| `c64-sid` | `.tools/c64-skills/c64-sid` | `480b253b147655fa6ff6eb74577d1a2523d512d4` |
| `sid-music` | `.tools/c64bridge/.github/skills/sid-music` | `0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18` |
| c64bridge server | `.tools/c64bridge` | Same revision; package version `1.0.4` |
| Desktop VICE | `/Applications/vice-arm64-gtk3-3.9` | VICE 3.9 |
| Headless VICE | `.tools/vice-headless-3.9/build/src/x64sc` | Official VICE 3.9 release; project-local build |

The maintainer's 2026-10-16 checks discovered both project skills and completed the c64bridge stdio handshake/tool discovery. That establishes server discovery in that environment, not emulator connectivity or readiness of a fresh checkout. Offline PRG/SID builds, independent CPU checks, SIDLite rendering and genuine headless VICE/reSID execution work. The restricted runner denies binary-monitor socket binding, so live bridge control remains unverified. See [audio rendering](../workflows/audio-workflow.md), [native checkpoints](../validation/native-vice-checks.md) and [headless build findings](vice-startup-investigation.md).

## Unified local setup

Run from the repository root:

```sh
python3 scripts/setup-project.py
python3 scripts/doctor.py
```

The [manifest](../../config/local-assets.json) owns URLs, credits, commit pins and hashes. Default setup installs two DRAX reference tunes and the hardware skill. `--include flashdance-historical` adds the historical alternative; `--include sid-music` adds bridge instructions. `--only references` or `--only skills` limits installation. `--offline` uses existing verified files and pinned objects from local Git checkouts; `--check` performs read-only verification. Modified files are preserved and rejected, not silently overwritten. Downloads are verified before publishing their destination.

Reference binaries live under ignored `.local/`; installed skill directories are ignored targets of the portable `.agents/skills/` links. Codex discovers skills there; Claude Code reads `.claude/skills/`, which is a tracked relative link to `../.agents/skills`, so both hosts share every activation and setup needs no host-specific step. A headless Claude Code 2.1.301 session discovered `c64-sid` and `sid-music` through this chained link on 2026-10-16; `tests/project_setup_test.py` guards the link. Claude-local settings stay in ignored `.claude/settings.local.json`. Read [skill corrections](skill-guidance.md) before using them. A new agent session may be needed for discovery.

### Original SID downloads on demand

Keep the original SID's source URL and SHA-256 in the [asset manifest](../../config/local-assets.json), then use [setup-project.py](../../scripts/setup-project.py) to acquire it when needed. The entries below are actual downloaded study inputs; research possibilities mentioned in the [listening catalogue](../research/composers/listening-catalogue.md) are not installed as part of this inventory. The registry pins the bytes checked on acquisition; each owning study records its source-verification date. Generated arrangements and patched diagnostic copies retain their own recipes rather than being registered as originals.

| Reference ID | Local cache path | Selection |
| --- | --- | --- |
| `fuer-elise` | `.local/research/fuer-elise/drax-fuer-elise.sid` | Default |
| `flashdance` | `.local/research/flashdance/drax-flashdance-conversion.sid` | Default |
| `flashdance-historical` | `.local/research/flashdance/kleimeyer-flashdance.sid` | `--include flashdance-historical` |
| `shades-filter-corrected` | `.local/research/shades/Shades_filter_corrected.sid` | `--include shades-filter-corrected` |
| `shades` | `.local/research/shades/Shades.sid` | `--include shades` |
| `cybernoid-ii` | `.local/research/cybernoid-ii/Cybernoid_II.sid` | `--include cybernoid-ii` |
| `monty-on-the-run` | `.local/monty-source.sid` | `--include monty-on-the-run` |
| `commando` | `.local/commando-source.sid` | `--include commando` |
| `auf-wiedersehen-monty` | `.local/monty-wiedersehen-source.sid` | `--include auf-wiedersehen-monty` |
| `rambo-first-blood-part-ii` | `.local/rambo-source.sid` | `--include rambo-first-blood-part-ii` |
| `arkanoid` | `.local/arkanoid-source.sid` | `--include arkanoid` |
| `ghouls-n-ghosts` | `.local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid` | `--include ghouls-n-ghosts` |
| `deflektor` | `.local/research/deflektor/Deflektor.sid` | `--include deflektor` |
| `trap` | `.local/research/trap/Trap.sid` | `--include trap`; [explicit #1 contrast and credit boundary](../research/composition/daglish-contrast.md) |
| `take-on-me` | `.local/research/take-on-me/Take_on_Me.sid` | `--include take-on-me` |
| `billie-jean` | `.local/research/billie-jean/Billie_Jean.sid` | `--include billie-jean` |
| `airwolf` | `.local/research/airwolf/Airwolf.sid` | `--include airwolf` |
| `ghostbusters` | `.local/research/ghostbusters/Ghostbusters.sid` | `--include ghostbusters` |

The older composer caches keep their existing `.local/` paths. `--include` adds the requested optional entries to the default selection and can be repeated. Fetch both Shades variants, or verify their existing copies without network access:

```sh
python3 scripts/setup-project.py --only references --include shades-filter-corrected --include shades
python3 scripts/setup-project.py --check --only references --include shades-filter-corrected --include shades
```

Acquire the earlier Hubbard/Galway inputs with the same downloader:

```sh
python3 scripts/setup-project.py --only references --include monty-on-the-run --include commando --include auf-wiedersehen-monty --include rambo-first-blood-part-ii --include arkanoid
```

Existing matching files are reused. Missing files are downloaded and checked before installation; a changed cached file or changed upstream response fails its fingerprint check. Original SID bytes remain ignored and outside Git. Deleting a local cache does not remove its provenance; rerunning the appropriate command restores the pinned file while the source URL still serves the recorded bytes.

### Inspect a selected reference before execution

[sid_intake.py](../../scripts/sid_intake.py) reads PSID/RSID v2 metadata without executing the original or retaining payload bytes in its report. Select a one-based subtune explicitly and use a fresh output path:

```sh
python3 scripts/sid_intake.py .local/monty-source.sid --subtune 1 --output build/monty-intake-new/header.json
```

The report separates declared clock/model/timing from `callableProfile`, the current `pal-banked` audit's header admission result. Acceptance is not successful execution: additional I/O or host dependencies can still reject at runtime. RSID's reserved zero speed word is reported as machine-controlled rather than VBI. Other SID format versions are explicitly unsupported by this small intake tool; it is not a complete format validator. The report includes source/tool fingerprints and preserves raw entry addresses. Use the owning study for subtune labels, attribution and subsequent execution evidence.

To assess an explicit low-RAM host without changing the reference, add `--host-base 0x0400`; `callableProfile` records the requested address and, on acceptance, the selected `hostBase`. Without that option, admission uses the default `$C000` host. The [placement contract](../validation/psid-audit.md#place-the-host-around-a-high-ram-reference) owns workspace bounds and runtime checks; use the same selection for subsequent CPU and VICE execution.

### Readiness and bridge setup

Choose the workflow with `python3 scripts/doctor.py --profile NAME`. Each report identifies its profile and gives a repair for every missing prerequisite. Checks do not install dependencies, perform a song build or award a listening verdict.

| Profile | Required checks | What passing means |
| --- | --- | --- |
| `samples` | Readable included Bach PCM16 WAV | A representative shipped preview is available locally. No tool subprocesses run; player/speaker playback and every other sample are outside this check. |
| `demo` | py65 imports, renderer loading, native exporter/labels matching their build receipt | The native Bach demo's runtime dependencies are available. MIDI import, VICE, bridge and historical research assets are not required. |
| `score` | `demo` checks plus Mido, headless VICE identification and complete-sized C64 ROMs | Prerequisites for the MIDI-to-native workflow and independent standalone verification are available. Source compatibility, musical reductions and successful execution of a particular song still need their own checks. |
| `bridge` | Executable Bun, c64bridge source and `node_modules`, headless VICE identification and C64 ROMs | The optional local VICE bridge installation is present. The server is not started and live connectivity is not tested. |
| `full` (default) | Original environment check: py65, renderer, VICE/ROMs and default pinned assets; Mido and bridge remain optional | Compatible broad diagnostics for existing users. This legacy profile does not replace the native-exporter check in `demo`/`score`. |

```sh
python3 scripts/doctor.py --profile samples
python3 scripts/doctor.py --profile demo
python3 scripts/doctor.py --profile score --json
```

For a two-SID native build, use `--sid-count 2` with `demo` or `score`; prepare that exporter with `python3 scripts/setup-sidwizard.py --sid-count 2`. Normal composition does not require a live bridge, audio models, downloaded reference SIDs or installed skill Markdown. The `full` profile still checks its historical default asset selection for compatibility; use the narrower profile for your actual workflow.

Doctor also supports `--json`, `--vice PATH`, `--vice-data PATH`, `--renderer PATH` and bounded `--timeout SECONDS` (up to 60 seconds per probe). Explicit paths override `VICE_BINARY`, `VICE_DIRECTORY` and `SID_RENDERER`. The renderer defaults to `.local/bin/render-sid`, VICE to `.tools/vice-headless-3.9/build/src/x64sc`, and new profiles use `.tools/vice-headless-3.9/source/data` for ROM data. The compatible `full` profile retains the prior `/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice` fallback; other installations should set `--vice-data` or `VICE_DIRECTORY` explicitly. VICE identification from adjacent `config.h` is build evidence, not an emulator startup test. Use [native checkpoints](../validation/native-vice-checks.md) for actual execution. Setup does not install system packages or build VICE: follow [headless setup](vice-startup-investigation.md) and [renderer/dependency setup](../workflows/audio-workflow.md).

For optional live bridge use, prepare the pinned checkout described in the [project README](../../README.md#prepare-the-assembler), run `bun install --frozen-lockfile` there, and copy the host's template: [Codex](../../config/codex.toml) to `.codex/config.toml`, or [Claude Code](../../config/claude-mcp.json) to `.mcp.json` (or pass the edited local file with `claude --mcp-config`). Merge with an existing configuration rather than replacing other servers. Replace the launcher path with the absolute path to this checkout's [launch-c64bridge.py](../../scripts/launch-c64bridge.py), and `VICE_DIRECTORY` with the resource directory containing `C64/`. These are literal placeholders; neither host is expected to expand them. Do not activate the unedited examples.

Both templates invoke the same Python launcher. It finds Bun on `PATH`, derives source, VICE and runtime-state paths from its own checkout, and runs Bun in `.tools/c64bridge` without a shell. The agent's initial working directory does not matter, and paths with spaces remain individual arguments. A desktop agent whose `PATH` lacks Python or Bun needs an absolute Python `command` in its local host configuration and/or `C64BRIDGE_BUN` set to the absolute Bun executable. `VICE_BINARY` can select another executable. Relative launcher path settings resolve against the checkout; use absolute paths in host templates to avoid host-dependent resolution.

Check the installation and resolved launcher settings before activating the server:

```sh
VICE_DIRECTORY=/absolute/path/to/vice/data python3 scripts/doctor.py --profile bridge
VICE_DIRECTORY=/absolute/path/to/vice/data python3 scripts/launch-c64bridge.py --check
```

The launcher check does not start Bun/VICE or write runtime state. Normal launch defaults to PAL, invisible headless VICE, normal-speed audio, disabled Xvfb/prewarm/RAG build, and state beneath `.local/c64bridge`; explicit environment values can override settings. For another clock, set both `VICE_MODE` and the matching `VICE_ARGS`. Readiness and resolved settings do not establish an MCP handshake or monitor connection. The earlier 2026-10-16 Claude Code 2.1.301 handshake used the previous machine-specific configuration; it does not validate these templates on a fresh host. Keep the upstream Bun lockfile. A skill installation alone neither installs the server nor establishes emulator connectivity.

### Optional local audio models

SongBench and its MuQ backbone are an opt-in research experiment. Contributors can skip the model source, checkpoints, isolated Python environment and all ML packages: `setup-project.py` does not download them, `doctor.py` does not probe them, and normal song builds and tests do not require them. Hosted assessment is also a separate deliberate trial; no model account or API credential is needed for normal setup. The [measured assessment](../research/audio-assessment.md#measured-local-songbench-trial) records the limited value, resource use and noncommercial research license constraints. Human listening determines musical acceptance.

Only to repeat the local experiment, acquire the exact source and checkpoint files from the URLs in the [setup receipt](../../evidence/audio-assessment-songbench/setup.json), verifying their recorded SHA-256 fingerprints. The receipt lists each local destination: SongBench source and scoring weights under `.tools/songbench/`, MuQ configuration and weights under `.local/audio-models/muq/`. The runner's `--source` and `--muq` options accept other local directories. These files are intentionally outside the ordinary asset installer and remain ignored.

Prepare an isolated environment from the recorded package versions rather than adding ML packages to the workbench's test dependencies. These commands install optional dependencies; the recorded trial used Python 3.11 on Apple Silicon, and the package receipt is a reproduction record rather than a cross-platform support guarantee:

```sh
uv venv --python 3.11 .tools/songbench-venv
python3 - <<'PY'
import json
from pathlib import Path

receipt = json.loads(Path("evidence/audio-assessment-songbench/setup.json").read_text())
requirements = Path(".local/songbench-requirements.txt")
requirements.parent.mkdir(parents=True, exist_ok=True)
requirements.write_text("".join(f"{name}=={version}\n" for name, version in sorted(receipt["packages"].items())))
PY
uv --cache-dir .local/uv-cache pip install --python .tools/songbench-venv/bin/python -r .local/songbench-requirements.txt
.tools/songbench-venv/bin/python -c 'import librosa, torch, torchaudio, muq, transformers, safetensors; print("ML imports ready; Metal available:", torch.backends.mps.is_available())'
.tools/songbench-venv/bin/python scripts/studies/audio-assessment/songbench-local.py --help
```

The import check establishes package availability; it does not load checkpoints or validate an evaluation result. Use the [bounded runner commands](../research/audio-assessment.md#measured-local-songbench-trial) only after restoring those assets and an explicit input manifest. Missing packages or checkpoints can fail that opted-in invocation without affecting ordinary readiness. There is no automatic download or device fallback in the inference worker.

## Headless bridge configuration

The shared launcher selects the project-built headless executable, PAL and normal speed, with explicitly configured ROM resources. It disables Xvfb and keeps bridge state/diagnostics under `.local/c64bridge`.

- Keep `VICE_HEADLESS="0"` for this build: `--enable-headlessui` already selects its UI, whereas the bridge's `1` setting injects a runtime `-headless` flag that is unnecessary and unsupported by the GTK package.
- `VICE_VISIBLE="false"` and `DISABLE_XVFB="1"` avoid virtual-display startup. `VICE_WARP="false"` is required for normal-speed audio capture.
- `VICE_PREWARM="0"` disables only the dedicated prewarm path. The pinned [server startup](../../.tools/c64bridge/src/mcp-server.ts) independently calls `logConnectivity()`, which reads `$0000` and can start VICE during server initialization.
- The bridge defaults to dummy audio. Use [direct WAV output](../workflows/audio-workflow.md) for reproducible capture; server discovery is not proof that sound is audible.

The genuine headless build avoids the restricted GTK/OpenGL startup crash. The separate socket-binding denial still blocks live monitor readiness, while offline monitor files remain usable. Build/source pins and workarounds belong in [the headless guide](vice-startup-investigation.md).

## Desktop and connected checks

The installed GTK3 package works from the user's desktop Terminal:

```sh
/Applications/vice-arm64-gtk3-3.9/bin/x64sc -pal +logcolorize
```

Its executable-path fallback and font warnings can be nonfatal. It rejects runtime `-headless`; `-console` still initializes GTK. The `-version` initialization-order problem is separate from graphics startup and is explained in [the headless findings](vice-startup-investigation.md).

When a live monitor is available, discover `c64_sound`, read `c64://platform/status` and the binary-monitor resource before issuing commands. Require an actual monitor Info response; an open window or installed skill is insufficient. The upstream preset call is `c64_sound` with `op: "play_preset"`, `preset: "fuer_elise"`. Read [compiler/preset limitations](../research/tools/skills-and-integrations.md): that preset is not the verified complete transcription. Use file renders rather than microphone capture as deterministic evidence.

## Reproducibility checks

Run `python3 scripts/setup-project.py --check --include sid-music` when both skills are wanted, followed by `python3 scripts/doctor.py`. The installer tests cover failed downloads, changed files, safe paths and activation; doctor checks are read-only and bounded. Keep raw diagnostics in ignored output directories and retain reusable constraints here or in the linked owning guide.

[CLAUDE.md](../../CLAUDE.md) provides contributor guidance; [AGENTS.md](../../AGENTS.md) is its symlink for agent discovery. Downloaded material must also be absent from published Git history; adding ignore rules does not remove previously tracked files or historical blobs.

## Before publishing

Ignore rules do not untrack an existing installation. If `git ls-files skills/c64-sid skills/sid-music` lists downloaded files, remove only their index entries, preserving local installations:

```sh
git rm --cached -r skills/c64-sid skills/sid-music
```

Keep `skills/README.md`, the asset manifest and activation links tracked. Audit history as well: `git log --all -- skills/c64-sid skills/sid-music` reveals earlier vendored copies. A removal commit does not erase them; publication requires a separately reviewed history cleanup or a clean publication history. Never push the existing history while it contains excluded downloads.
