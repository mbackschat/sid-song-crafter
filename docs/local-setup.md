# Local SID skills and VICE setup

## Components

The user supplied local checkouts under `.tools/` on 2026-10-12. The skill-installer's validation and copy helpers staged the requested skills under [skills](../skills/README.md); its network downloader could not resolve GitHub in this session. No global skill or configuration was changed.

**Skills and server installed:** the user activated both project skill symlinks, copied the original GTK-based MCP configuration, and installed the locked dependencies. A real MCP stdio handshake succeeded with c64bridge 1.0.4, listing 17 tools (including `c64_sound`) and 28 resources. This verifies discovery, not an emulator connection. The versioned configuration example has since been changed to the genuine headless build; the protected `.codex/config.toml` still contains the user's earlier GTK configuration.

**Current execution path:** the [opening excerpt](first-song.md) builds to PRG and SID and passes independent CPU checks. [Headless audio verification](audio-workflow.md) covers both a libsidplayfp/SIDLite render and a full PRG run through BASIC in genuine headless VICE 3.9 with reSID MOS8580 recording. Both captures contain the expected nine pitches; VICE returns to BASIC with the player finished and SID volume zero. The session separately denies binary-monitor socket binding. Detailed build commands, checksums, failures, and outcomes are in the [VICE investigation](vice-startup-investigation.md). No Computer Use is required by the file-based workflow.

| Component | Local source | Revision |
| --- | --- | --- |
| `c64-sid` | `.tools/c64-skills/c64-sid` | `480b253b147655fa6ff6eb74577d1a2523d512d4` |
| `sid-music` | `.tools/c64bridge/.github/skills/sid-music` | `0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18` |
| c64bridge server | `.tools/c64bridge` | Same revision; package version `1.0.4` |
| VICE | `/Applications/vice-arm64-gtk3-3.9` | User's successful desktop launch reports VICE 3.9 |
| Headless VICE | `.tools/vice-headless-3.9/build/src/x64sc` | Official VICE 3.9 release; project-local build |

## Activation from the user's Terminal

The session's filesystem policy makes `.agents` and `.codex` read-only. The user ran the commands below to complete installation outside that restricted session. They are retained for reproduction on another setup; do not rerun merely because they appear here. They preserve existing paths rather than overwrite them. If a destination exists, inspect it and merge deliberately.

```sh
cd /Users/mbackschat/Projects/c64-sid-skill
mkdir -p .agents/skills .codex
ln -s ../../skills/c64-sid .agents/skills/c64-sid
ln -s ../../skills/sid-music .agents/skills/sid-music
cp -n config/codex.toml .codex/config.toml
cd .tools/c64bridge
bun install --frozen-lockfile
```

Use Bun here because this third-party project declares and supplies a Bun lockfile; it is already installed at `/opt/homebrew/bin/bun`. The configuration launches its TypeScript entry point directly, so a source build is not required. This avoids replacing its package-manager contract with a newly generated pnpm lockfile.

Codex discovers project skills through `.agents/skills`, including symlinks. The skills should be available on the next turn; restart if they do not appear. Project MCP configuration requires a trusted project and a server reload/new session. These are client behaviours documented by [OpenAI's skill guide](https://learn.chatgpt.com/docs/build-skills) and [MCP guide](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

## VICE configuration

The original activated configuration selected the installed GTK launcher, PAL, visible/minimized mode, normal speed, and disabled prewarming. The current [configuration example](../config/codex.toml) selects the project-built headless binary, retains PAL and normal speed, disables Xvfb, and uses ROM resources from the existing installation. Diagnostics, the VICE log, and task state stay under `.local/c64bridge`.

Disabled prewarming does not guarantee lazy emulator startup in this pinned bridge. Its [server startup](../.tools/c64bridge/src/mcp-server.ts) independently calls `logConnectivity()`, which reads `$0000` when VICE is selected and can launch the emulator. The headless probe's diagnostics show that process-start request before the explicit resource read. `VICE_PREWARM = "0"` controls the separate prewarm path, not this connectivity probe.

`VICE_HEADLESS = "0"` is deliberate: the executable was compiled with `--enable-headlessui`, whereas setting the bridge variable to `1` injects a runtime `-headless` option that this workflow does not require. `VICE_VISIBLE = "false"` and `DISABLE_XVFB = "1"` prevent a virtual display launch. The bridge still defaults to dummy sound; use the [audio workflow](audio-workflow.md) for reproducible rendering.

The headless MCP probe used a separate port, `6512`, to avoid the user's desktop instance. It timed out; a direct bounded launch then exposed `vice_network_server(): bind() failed: Operation not permitted`. This is a socket permission failure, not a GTK failure or an absent headless build. Probe diagnostics are `.local/c64bridge/diagnostics/2026-10-12T18-43-24-649Z-28232-mcp-server.ndjson`; owned probe processes were stopped. MCP emulator control requires a runner that permits localhost sockets. Do not claim the new configuration is active: `.codex/` remains read-only to this session.

### Earlier GTK investigation

Initially, both the launcher and direct executable returned `failed to retrieve executable path` followed by `argv[0] is NULL` when probed with `-version` in the restricted session. The [subsequent investigation](vice-startup-investigation.md) traces this shortcut's initialization-order defect separately from the GTK startup crash. The later desktop launch and headless runtime banner establish version 3.9; reinstalling is unnecessary.

An early MCP `c64_vice` / `resource_get` request for `SidEngine` exercised actual emulator startup. VICE exited with code 139 before its monitor became ready, with repeated GTK `GDK_IS_MONITOR` assertions and a segmentation fault. Later crash-report and disassembly analysis identified a call through a null OpenGL shader function pointer; see the [investigation](vice-startup-investigation.md). The original diagnostic log is `.local/c64bridge/diagnostics/2026-10-12T18-04-53-082Z-88443-mcp-server.ndjson`. That probe started no song and verified no audio.

### Colour-log hypothesis

The user suggested coloured logging as a possible cause. VICE supports `+logcolorize` to disable colour logging; the plus sign is intentional. [Upstream bug 2259](https://sourceforge.net/p/vice-emu/bugs/2259/) reports a crash when coloured output goes to a pipe/file and a log file cannot be opened: the logging implementation can pass uninitialized null text pointers to its output routine. That report describes a 3.10 build, so applicability to this 3.9 installation needs testing. c64bridge does pipe the child process's output, making the hypothesis relevant.

An A/B MCP test on 2026-10-12 reproduced exit code 139 and GTK monitor assertions with both `-pal -minimized` and `-pal -minimized +logcolorize`. The colour-disabled run is recorded in `.local/c64bridge/diagnostics/2026-10-12T18-13-27-353Z-91203-mcp-server.ndjson`. Disabling colour did not resolve the observed startup failure; these tests do not establish its root cause. Configuration was not changed on the basis of an unsuccessful workaround.

A third run with `-pal +logcolorize` also failed in the same way, so removing the minimized-window option did not resolve it either.

### Desktop launch succeeds

On 2026-10-12 the user confirmed that this command opens the emulator window from their normal macOS Terminal:

```sh
/Applications/vice-arm64-gtk3-3.9/bin/x64sc -pal +logcolorize
```

The supplied output identifies `VICE Version 3.9`. It still reports `failed to retrieve executable path, falling back to getcwd() + argv[0]`, a missing `PetMe1282Y.ttf`, and failure to register the CBM font. Those warnings are nonfatal in this successful desktop launch. This establishes that the installation can start in the desktop context; it does not isolate which process-environment or access difference causes the restricted launch failure. Do not reinstall VICE to address these observations. Audible playback and the binary-monitor connection remain separate checks.

## First connected check

Discover `c64_sound` and read `c64://platform/status` to confirm the VICE backend. Read the bridge's binary-monitor resource before monitor operations. A skill file alone does not supply these tools; the MCP server must start successfully. For a preset demonstration, the upstream skill specifies `c64_sound` with `op: "play_preset"` and `preset: "fuer_elise"`.

Treat successful launch separately from audio or score correctness. Read the [compiler limitations](research/tools/skills-and-integrations.md) first; the preset is not a verified full transcription. Do not use microphone capture as evidence of a clean deterministic render.

## Reproducibility

Keep upstream checkouts separate from the staged skills and record any local skill adaptations in [the skill manifest](../skills/README.md). Do not update upstream branches silently. Review licenses before publishing vendored documentation or music. The root [AGENTS.md](../AGENTS.md) contains contributor guidance and VICE findings, as subsequently requested by the user.

The user initialized Git on 2026-10-12. The new `.gitignore` excludes downloaded tools, runtime files, generated outputs, and `.codex/`; those exclusions were checked. Initial compound shell commands that combined staging and read-only checks failed with `Unable to create .../.git/index.lock: Operation not permitted`. After the user explicitly renewed Git authorization, standalone `git add` commands succeeded; another compound attempt still failed. Run Git mutations separately from inspection commands in this environment. No third-party checkout modifications were included. Whitespace checks flag existing blank lines at EOF in four archived SID references; these files remain byte-identical to upstream rather than being reformatted.

Validation completed: skill frontmatter parsed with Bun's YAML parser; MCP configuration parsed with Bun's TOML parser; local Markdown links and source-register anchors checked; note-frequency examples independently recalculated; bundled SID reference bytes compared with upstream. The skill-creator's Python validator could not run because PyYAML was unavailable in the offline environment, so its full check is not claimed.
