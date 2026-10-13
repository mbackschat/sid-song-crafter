# Apply downloaded skills correctly

The [selected skills](../../skills/README.md) provide useful hardware reference and optional bridge instructions. They are installed unmodified from the [pinned manifest](../../config/local-assets.json); project findings below take precedence over inaccurate or incomplete upstream prose.

- **GATE and envelopes:** a rising GATE starts attack from the current envelope level, not necessarily zero. Clearing GATE starts release; sound can continue during release. See [SID hardware and sources](../research/sid/hardware.md).
- **Voice 3 disconnect:** `$D418` bit 7 removes voice 3 from the direct output path. Voice 3 remains audible through the filter when routed there. See [routing constraints](../research/sid/hardware.md).
- **Pitch tables:** check the intended PAL/NTSC clock before reusing frequency words.
- **Bridge fidelity:** a successful preset/PRG launch does not establish full score coverage, rests, articulation or six-voice support. Read the [inspected compiler limitations](../research/tools/skills-and-integrations.md#c64bridge-capabilities-and-limits) before composition.
- **Optional BASIC route:** the sid-music skill's sibling BASIC workflow belongs to `.tools/c64bridge/.github/skills/basic-program/SKILL.md` in the pinned checkout. Read it there only when needed; it is not installed by default.
- **Execution:** prefer [headless VICE](vice-startup-investigation.md) and file-based traces. Installed skills do not prove that live bridge tools are connected.

Retain reusable corrections here with links to their evidence. Do not modify installed upstream skill files or redistribute their prose as local patches.
