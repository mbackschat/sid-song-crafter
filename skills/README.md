# Project-local SID skills

These skills are installed through verified project-local symlinks under `.agents/skills`. See [local setup](../docs/local-setup.md) for activation history, server configuration, and the unresolved VICE launch issue.

| Skill | Role | Upstream |
| --- | --- | --- |
| [c64-sid](c64-sid/SKILL.md) | SID register and sound-programming knowledge | [sunsided/c64-skills at 480b253](https://github.com/sunsided/c64-skills/tree/480b253b147655fa6ff6eb74577d1a2523d512d4/c64-sid) |
| [sid-music](sid-music/SKILL.md) | c64bridge playback/composition workflow | [chrisgleissner/c64bridge at 0781a7b](https://github.com/chrisgleissner/c64bridge/tree/0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18/.github/skills/sid-music) |

Installed from user-downloaded checkouts on 2026-10-12. Bundled reference files remain unchanged archival copies. Local skill adaptations correct envelope/voice-3 wording, link the project assessment, and resolve the bridge's optional BASIC workflow to its retained checkout. Entry-point prose was unwrapped and embedded table separators made renderable; reference links use Markdown. Upstream originals remain available in `.tools/` for comparison.

c64bridge includes a GPL-2.0 license file; its package metadata says GPL-2.0-only while some source headers say “or later.” The staged `sid-music` directory retains a copy of the upstream license. No explicit top-level license was found for c64-skills; its historical manual excerpts and the skill author's prose need separate rights review before redistribution. Local installation is not a claim that those materials are public domain.

The two skills can cooperate: `c64-sid` explains hardware semantics; `sid-music` selects bridge operations once its MCP tools are connected. Neither establishes that the bridge's compiler faithfully implements a complete score or dual-SID playback. See [the assessment](../docs/research/11-skills-and-integrations.md).
