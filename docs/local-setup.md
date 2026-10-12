# Local SID skills and VICE setup

## Components and current capabilities

The project stages portable skill sources under [skills](../skills/README.md), third-party checkouts/builds under `.tools/`, runtime state under `.local/`, and a machine-specific MCP configuration under `.codex/`. Keep upstream revisions and notices intact.

| Component | Local source | Revision |
| --- | --- | --- |
| `c64-sid` | `.tools/c64-skills/c64-sid` | `480b253b147655fa6ff6eb74577d1a2523d512d4` |
| `sid-music` | `.tools/c64bridge/.github/skills/sid-music` | `0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18` |
| c64bridge server | `.tools/c64bridge` | Same revision; package version `1.0.4` |
| Desktop VICE | `/Applications/vice-arm64-gtk3-3.9` | VICE 3.9 |
| Headless VICE | `.tools/vice-headless-3.9/build/src/x64sc` | Official VICE 3.9 release; project-local build |

Both project skills are active, and the c64bridge stdio handshake/tool discovery passes. That establishes server discovery, not emulator connectivity. Offline PRG/SID builds, independent CPU checks, SIDLite rendering and genuine headless VICE/reSID execution work. The restricted runner denies binary-monitor socket binding, so live bridge control remains unverified. See [audio rendering](audio-workflow.md), [native checkpoints](native-vice-checks.md) and [headless build findings](vice-startup-investigation.md).

## Activate on another checkout

From the user's Terminal, adapt the checkout path and inspect existing destinations before merging configuration:

```sh
cd /Users/mbackschat/Projects/c64-sid-skill
mkdir -p .agents/skills .codex
ln -s ../../skills/c64-sid .agents/skills/c64-sid
ln -s ../../skills/sid-music .agents/skills/sid-music
cp -n config/codex.toml .codex/config.toml
cd .tools/c64bridge
bun install --frozen-lockfile
```

Use Bun because the pinned bridge supplies its own Bun lockfile. Its TypeScript entry point runs directly; no source build or replacement Node lockfile is needed. The [configuration example](../config/codex.toml) contains this machine's executable/data paths and must be adapted elsewhere. Existing `.codex/config.toml` can differ from the example, and the restricted session cannot write that protected configuration.

Codex discovers skills through `.agents/skills`, including symlinks. A trusted project and server reload/new session are required for MCP configuration changes; see the [skill guide](https://learn.chatgpt.com/docs/build-skills) and [MCP guide](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

## Headless bridge configuration

The example selects the project-built headless executable, PAL and normal speed, with ROM resources from the installed desktop package. It disables Xvfb and keeps bridge state/diagnostics under `.local/c64bridge`.

- Keep `VICE_HEADLESS="0"` for this build: `--enable-headlessui` already selects its UI, whereas the bridge's `1` setting injects a runtime `-headless` flag that is unnecessary and unsupported by the GTK package.
- `VICE_VISIBLE="false"` and `DISABLE_XVFB="1"` avoid virtual-display startup. `VICE_WARP="false"` is required for normal-speed audio capture.
- `VICE_PREWARM="0"` disables only the dedicated prewarm path. The pinned [server startup](../.tools/c64bridge/src/mcp-server.ts) independently calls `logConnectivity()`, which reads `$0000` and can start VICE during server initialization.
- The bridge defaults to dummy audio. Use [direct WAV output](audio-workflow.md) for reproducible capture; server discovery is not proof that sound is audible.

The genuine headless build avoids the restricted GTK/OpenGL startup crash. The separate socket-binding denial still blocks live monitor readiness, while offline monitor files remain usable. Build/source pins and workarounds belong in [the headless guide](vice-startup-investigation.md).

## Desktop and connected checks

The installed GTK3 package works from the user's desktop Terminal:

```sh
/Applications/vice-arm64-gtk3-3.9/bin/x64sc -pal +logcolorize
```

Its executable-path fallback and font warnings can be nonfatal. It rejects runtime `-headless`; `-console` still initializes GTK. The `-version` initialization-order problem is separate from graphics startup and is explained in [the headless findings](vice-startup-investigation.md).

When a live monitor is available, discover `c64_sound`, read `c64://platform/status` and the binary-monitor resource before issuing commands. Require an actual monitor Info response; an open window or installed skill is insufficient. The upstream preset call is `c64_sound` with `op: "play_preset"`, `preset: "fuer_elise"`. Read [compiler/preset limitations](research/tools/skills-and-integrations.md): that preset is not the verified complete transcription. Use file renders rather than microphone capture as deterministic evidence.

## Reproducibility checks

The staged skills' frontmatter and MCP example parse successfully; local Markdown links, register anchors and recalculated note-frequency examples are checked, and archived SID references remain byte-identical to upstream. Full Python skill-creator validation requires PyYAML and was not part of the offline checks. Record adaptations in [the skill manifest](../skills/README.md), retain dependency locks and leave third-party/source reference formatting intact.

[AGENTS.md](../AGENTS.md) provides contributor guidance. Generated outputs, runtime state and machine configuration remain ignored; share useful findings and portable commands in tracked documentation.
