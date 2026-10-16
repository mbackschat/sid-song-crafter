# Project-local SID skills

Install only the instruction sets needed for the work. Downloaded skill bodies and references belong in ignored local directories; the [asset manifest](../config/local-assets.json) records upstream commits and individual file hashes.

| Skill | Selection | Purpose and upstream |
| --- | --- | --- |
| `c64-sid` | Default | Register and sound-programming reference; [sunsided/c64-skills](https://github.com/sunsided/c64-skills/tree/480b253b147655fa6ff6eb74577d1a2523d512d4/c64-sid) |
| `sid-music` | Optional: `--include sid-music` | Playback instructions when c64bridge is actually connected; [chrisgleissner/c64bridge](https://github.com/chrisgleissner/c64bridge/tree/0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18/.github/skills/sid-music) |

```sh
python3 scripts/setup-project.py
python3 scripts/setup-project.py --only skills --include sid-music
python3 scripts/doctor.py
```

Setup retains upstream bytes under `skills/<name>/` and activates relative links under `.agents/skills/` for Codex. Claude Code reads the same links through the tracked `.claude/skills` → `../.agents/skills` directory link; see [local setup](../docs/setup/local-setup.md#unified-local-setup). It checks existing files before reuse and refuses changed files. `--offline` can recover skills from pinned Git objects already in `.tools/`. Restart the agent session if a newly installed skill is not discovered. Installing instructions does not install or connect the c64bridge server; follow [local setup](../docs/setup/local-setup.md) when that integration is needed.

Read [project-specific corrections](../docs/setup/skill-guidance.md) before applying these upstream instructions. Keep corrections there rather than editing checksum-pinned downloads. The bridge's upstream license is installed alongside its skill; local availability does not imply redistribution rights for either skill or its historical manual excerpts.
