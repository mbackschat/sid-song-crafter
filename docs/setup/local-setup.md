# Local SID skills and VICE setup

## Components and current capabilities

The project installs ignored, checksum-pinned upstream skills under [skills](../../skills/README.md), third-party checkouts/builds under `.tools/`, runtime state under `.local/`, and a machine-specific MCP configuration under `.codex/`. Keep upstream revisions and notices intact.

| Component | Local source | Revision |
| --- | --- | --- |
| `c64-sid` | `.tools/c64-skills/c64-sid` | `480b253b147655fa6ff6eb74577d1a2523d512d4` |
| `sid-music` | `.tools/c64bridge/.github/skills/sid-music` | `0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18` |
| c64bridge server | `.tools/c64bridge` | Same revision; package version `1.0.4` |
| Desktop VICE | `/Applications/vice-arm64-gtk3-3.9` | VICE 3.9 |
| Headless VICE | `.tools/vice-headless-3.9/build/src/x64sc` | Official VICE 3.9 release; project-local build |

Both project skills are active, and the c64bridge stdio handshake/tool discovery passes. That establishes server discovery, not emulator connectivity. Offline PRG/SID builds, independent CPU checks, SIDLite rendering and genuine headless VICE/reSID execution work. The restricted runner denies binary-monitor socket binding, so live bridge control remains unverified. See [audio rendering](../workflows/audio-workflow.md), [native checkpoints](../validation/native-vice-checks.md) and [headless build findings](vice-startup-investigation.md).

## Unified local setup

Run from the repository root:

```sh
python3 scripts/setup-project.py
python3 scripts/doctor.py
```

The [manifest](../../config/local-assets.json) owns URLs, credits, commit pins and hashes. Default setup installs two DRAX reference tunes and the hardware skill. `--include flashdance-historical` adds the historical alternative; `--include sid-music` adds bridge instructions. `--only references` or `--only skills` limits installation. `--offline` uses existing verified files and pinned objects from local Git checkouts; `--check` performs read-only verification. Modified files are preserved and rejected, not silently overwritten. Downloads are verified before publishing their destination.

Reference binaries live under ignored `.local/`; installed skill directories are ignored targets of the portable `.agents/skills/` links. Read [skill corrections](skill-guidance.md) before using them. A new agent session may be needed for discovery.

### Original SID downloads on demand

Keep the original SID's source URL and SHA-256 in the [asset manifest](../../config/local-assets.json), then use [setup-project.py](../../scripts/setup-project.py) to acquire it when needed. The entries below are actual downloaded study inputs; research possibilities mentioned in the [listening catalogue](../research/composers/listening-catalogue.md) are not installed as part of this inventory. The listed source URLs returned bytes matching their registered fingerprints on 2026-10-13. Generated arrangements and patched diagnostic copies retain their own recipes rather than being registered as originals.

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

Doctor supports `--json`, `--vice PATH`, `--vice-data PATH` and `--renderer PATH`, or `VICE_BINARY`, `VICE_DIRECTORY` and `SID_RENDERER`. It checks py65, renderer loading, headless VICE identification, expected ROM sizes and asset hashes; Mido and the bridge are optional. VICE identification from adjacent `config.h` is build evidence, not an emulator startup test. Use [native checkpoints](../validation/native-vice-checks.md) for actual execution. Setup does not install system packages or build VICE: use [the headless build instructions](vice-startup-investigation.md) and [renderer/dependency setup](../workflows/audio-workflow.md).

For optional live bridge use, prepare the pinned checkout described in the [project README](../../README.md#prepare-the-assembler), run `bun install --frozen-lockfile` there, and adapt [the configuration example](../../config/codex.toml) before activating it. Keep the upstream Bun lockfile. A skill installation alone neither installs the server nor establishes emulator connectivity.

## Headless bridge configuration

The example selects the project-built headless executable, PAL and normal speed, with ROM resources from the installed desktop package. It disables Xvfb and keeps bridge state/diagnostics under `.local/c64bridge`.

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

[AGENTS.md](../../AGENTS.md) provides contributor guidance. Downloaded material must also be absent from published Git history; adding ignore rules does not remove previously tracked files or historical blobs.

## Before publishing

Ignore rules do not untrack an existing installation. If `git ls-files skills/c64-sid skills/sid-music` lists downloaded files, remove only their index entries, preserving local installations:

```sh
git rm --cached -r skills/c64-sid skills/sid-music
```

Keep `skills/README.md`, the asset manifest and activation links tracked. Audit history as well: `git log --all -- skills/c64-sid skills/sid-music` reveals earlier vendored copies. A removal commit does not erase them; publication requires a separately reviewed history cleanup or a clean publication history. Never push the existing history while it contains excluded downloads.
