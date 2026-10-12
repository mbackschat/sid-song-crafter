# Auditing a native PSID driver

[The audit tool](../scripts/psid_audit.py) executes a driver with the independent py65 NMOS 6502 core and records SID register writes without requiring our score compiler's symbols or articulation rules. Install py65 as documented in [the first-song guide](first-song.md).

```sh
python3 scripts/psid_audit.py build/example.sid --ticks 250 --output build/example.audit.json
```

The JSON report contains call counts, initialization and peak playback cycle costs, register value ranges, and the input SHA-256. Its `.writes.json` sibling retains every observed SID write in order. Choose a new output path for each run; exclusive creation protects existing evidence, including files created after the initial path check. If either write fails, the tool removes only the files it created so an incomplete pair does not remain as successful evidence.

## Supported execution contract

This is a bounded RAM-only audit: one subtune, a payload within `$0400–$9fff`, callable init/play, and one call per PAL frame. It supports PSID v2NG with one explicitly declared PAL 6581/8580, or PSID v3 with two PAL 8580s at `$D400` and `$D420` (flags `$00A4`, second-chip byte `$42`, no third chip). Other layouts are rejected. Reports list the declared chips and keep their register addresses distinct. The parser accepts either header or embedded load addresses and resolves zero init to the load address. These conventions follow [the HVSC format specification](https://hvsc.c64.org/download/C64Music/DOCUMENTS/SID_file_format.txt).

Initialization starts with zero-filled RAM except CPU port `$2f/$37`, A/X/Y zero, and the normal py65 stack. Driver changes to RAM and registers persist across calls. The tool rejects unsupported opcodes, ROM/I/O reads, non-SID hardware writes, hidden I/O, missing returns, and excessive call budgets. Initialization has a separate million-cycle ceiling; playback across all declared chips must fit the same 19,656-cycle PAL frame; adding a chip does not double the CPU budget. Rejecting a driver means this restricted audit cannot model it; use full C64 emulation for broader contracts.

## Evidence limits

`instructionStartCycle` identifies the start of the instruction performing a write, relative to its call. It is not a bus-cycle timestamp. Read-modify-write instructions targeting SID are unsupported because py65 does not reproduce their NMOS dummy writes. The tool does not emulate sound, badlines, interrupts, timer changes, or analogue chip behaviour.

A completed audit establishes bounded execution and observed register trajectories in this declared environment. It does not establish note correctness, waveform quality, the song's ending, or listening approval. Compare the exported driver with its native source and render it through [the audio workflow](audio-workflow.md); use a driver-specific expectation for the particular technique being tested.
