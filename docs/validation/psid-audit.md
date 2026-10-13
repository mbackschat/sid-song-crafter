# Auditing a native PSID driver

[The audit tool](../../scripts/psid_audit.py) executes a driver with the independent py65 NMOS 6502 core and records SID register writes without requiring our score compiler's symbols or articulation rules. Install py65 as documented in [the first-song guide](../songs/first-song.md).

```sh
python3 scripts/psid_audit.py build/example.sid --ticks 250 --output build/example.audit.json
```

The JSON report contains call counts, initialization and peak playback cycle costs, register value ranges, and the input SHA-256. Its `.writes.json` sibling retains every observed SID write in order. Choose a new output path for each run; exclusive creation protects existing evidence, including files created after the initial path check. If either write fails, the tool removes only the files it created so an incomplete pair does not remain as successful evidence.

Timing-sensitive execution uses the shared CPU adapter. See the [opcode timing lookup and regression evidence](cpu-timing.md) for the py65 1.2.0 `DEC absolute` correction and the limits of older cached cycle reports.

## Supported execution contract

The default `strict` profile is a bounded RAM-only audit: one subtune, a payload within `$0400–$9fff`, callable init/play, and a per-play-call PAL cycle budget. It supports PSID v2NG with one explicitly declared PAL 6581/8580, or PSID v3 with two same-model PAL 6581s or 8580s at `$D400` and `$D420` (flags `$0054` or `$00A4`, second-chip byte `$42`, no third chip). Other layouts are rejected. Reports list the declared chips and keep their register addresses distinct. The parser accepts either header or embedded load addresses and resolves zero init to the load address. These conventions follow [the HVSC format specification](https://hvsc.c64.org/download/C64Music/DOCUMENTS/SID_file_format.txt). Actual call cadence requires a separate VICE observation.

Initialization starts with zero-filled RAM except CPU port `$2f/$37`, A/X/Y zero, and the normal py65 stack. Driver changes to RAM and registers persist across calls. The tool rejects unsupported opcodes, ROM/I/O reads, non-SID hardware writes, hidden I/O, missing returns, and excessive call budgets. Initialization has a separate million-cycle ceiling; playback across all declared chips must fit the same 19,656-cycle PAL frame; adding a chip does not double the CPU budget. Rejecting a driver means this restricted audit cannot model it; use full C64 emulation for broader contracts.

## Canonical SID write windows

Both `strict` and `pal-banked` retain every ordered store within each declared SID's canonical 32-byte window, `base` through `base+$1F`, including repeated stores and read-only/unused ports `$19–$1F`. The pinned reSID implementation updates its bus-value latch before active sound-register dispatch at offsets `$00–$18`; stores beyond `$18` therefore remain execution evidence even though they do not dispatch active sound controls. The [32-port semantics receipt](../../evidence/ghouls-sid-window/semantics.json) retains the primary-source basis and guards; the [Ghouls ’n Ghosts preparation](../research/composition/ghouls-preparation.md) owns the bounded original-driver comparison. This admission does not include undeclared chips or mirrored addresses outside the declared windows.

## Select a subtune and expose RAM beneath BASIC

The explicit `pal-banked` profile supports intact PSID headers with a one-based `--subtune` selection and payloads within `$0400–$CFFF` that do not overlap its selected host workspace. It uses the shared [header/profile parser](../../scripts/psid_profile.py); the header's declared subtunes/default, chip layout and VBI speed remain validated. The source bytes and hash do not change. An omitted selection is rejected in this profile; the default strict profile retains its original single-subtune and lower-RAM boundaries.

```sh
python3 scripts/psid_audit.py .local/research/cybernoid-ii/Cybernoid_II.sid --profile pal-banked --subtune 1 --ticks 600 --output build/cybernoid-title-new/audit.json
```

The API is `audit_psid(data, ticks, *, observer=None, subtune=None, profile='strict', host_base=None)`. The profile describes a controlled raster-polling host, with explicit entry state shared by the [VICE tracer](../../scripts/trace-sid-vice.py):

| Boundary | `pal-banked` contract |
| --- | --- |
| Mapping | Set CPU port `$01=$36` before init and each play call: BASIC hidden, KERNAL and SID I/O visible. Driver bank changes remain subject to guarded accesses. |
| Init entry | A=`subtune−1`, X=Y=0, status `$26`, SP=`$FF` before the callable return address is pushed. |
| Play entry | A=`$FA`; X/Y retain the preceding call's results. Set C/Z and clear N, retaining other status bits, matching the raster host's successful `CMP $D012` at line 250. |
| Memory isolation | The selected 512-byte host workspace rejects driver fetches, reads and writes; interrupt vectors `$0314–$0319` reject writes. Existing mapped-ROM, I/O-read, SID visibility and unsupported-store guards remain. |
| Call stack | Banked CPU execution pushes the actual host JSR return word from the [shared harness generator](../../scripts/sid_audit_host.py), including the selected host address. Stack-reading routines therefore see the same immediate return word as VICE. Strict retains its historical synthetic `$0200` return boundary. |
| Timing | Play-body costs retain the 19,656-cycle bound; actual call cadence is checked separately in VICE. The CPU oracle does not emulate the raster poll or SID bus timing. |

This entry contract is not libsidplayfp's IRQ entry: its inspected `psiddrv.a65` supplies A=0. Do not infer PCM or original-host identity from equality under the controlled raster host. [Cybernoid II's owning study](../research/composition/cybernoid-ii-preparation.md) retains the exact input, bank-selection basis and bounded execution evidence.

## Place the host around a high-RAM reference

The default banked host remains `$C000–$C1FF`. A payload overlapping that workspace is rejected before execution. An explicit `--host-base 0x0400` moves our host to `$0400–$05FF`; it does not relocate or patch the SID. Other explicit bases must be integer, page-aligned addresses from `$0400` through `$9E00`, keeping the entire workspace in RAM visible across permitted BASIC/KERNAL bank changes. The parser checks the complete source extent against the complete workspace; touching endpoints are allowed, overlapping bytes are not. Strict and Flashdance diagnostic profiles reject explicit host placement.

The shared generator derives code, return sites, the 16-bit counter at `hostBase+$100` and the init marker at `hostBase+$102` from one selected base. CPU reports and VICE profiles record `hostBase`. The banked VICE monitor clears RAM `$0002–$CFFF` and `$E000–$FFFF` before loading the unchanged payload and our host; the latter range matters when a driver banks out KERNAL and reads the underlying RAM. No I/O read model or original game environment follows from this controlled initialization.

The [Deflektor preparation](../research/composition/deflektor-preparation.md) owns the high-RAM reference and bounded comparison. Use the same `--host-base` for metadata admission, CPU audit, instruction tracing and VICE tracing; there is no automatic placement search. CPU auditing still accepts up to 100,000 calls, whereas the VICE counter supports at most 65,535 calls; shared return labels are derived from a representative valid host and do not extend the VICE counter's range.

## Evidence limits

`instructionStartCycle` identifies the start of the instruction performing a write, relative to its call. It is not a bus-cycle timestamp. SID reads and internal bus-latch behavior are not modeled; all I/O reads remain rejected. Read-modify-write instructions targeting SID are unsupported because py65 does not reproduce their NMOS dummy writes. The tool does not emulate sound, badlines, interrupts, timer changes, or analogue chip behaviour.

A completed audit establishes bounded execution and observed register trajectories in this declared environment. It does not establish note correctness, waveform quality, the song's ending, or listening approval. Compare the exported driver with its native source and render it through [the audio workflow](../workflows/audio-workflow.md); use a driver-specific expectation for the particular technique being tested.
