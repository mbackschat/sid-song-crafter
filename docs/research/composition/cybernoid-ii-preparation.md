# Cybernoid II: pinned title reference and bounded execution

This is bounded binary intake for Jeroen Tel's **Cybernoid II**, title subtune **1**, while Shades remains the sole active reconstruction under the [study plan](../study-plan.md). It establishes archive identity, bounded CPU/VICE execution under an explicit PAL host, executed reads of three source-labelled sound records and a rendered opening. It does not establish complete instrument semantics, original-host equivalence, complete form, reconstruction fidelity or a listening verdict. Consult the [composer account](../composers/huelsbeck-tel.md#jeroen-tel-arrangement-and-driver-collaboration), [listening catalogue](../composers/listening-catalogue.md) and [source-study boundary](../tools/source-studies.md) before extending this intake.

## Archive identity

The [optional `cybernoid-ii` asset](../../../config/local-assets.json) owns the [HVSC URL](https://www.hvsc.de/download/C64Music/MUSICIANS/T/Tel_Jeroen/Cybernoid_II.sid), SHA-256 `41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192` and ignored destination `.local/research/cybernoid-ii/Cybernoid_II.sid`. The downloaded file is 4,502 bytes. Its header credits **Jeroen Tel**, title `Cybernoid II`, release `1988 Hewson`. The [recovered source](https://github.com/realdmx/c64_6581_sid_players/blob/f215174fc4c983674808fcd47bc506f96b3d2d04/Tel_Jeroen_MON/Tel_Jeroen_Cybernoid2.asm) separately credits **Charles Deenen** for `MUSICFILE V01-07-1988`; retain music and driver credit separately.

| Actual archive field | Inspected value |
| --- | --- |
| Format / header size | PSID v2 / `$007C` bytes |
| Subtunes / default | 2 / 1 |
| Selected musical scope | #1 title; cached HVSC STIL labels #2 game over |
| Speed word | `$00000000`: VBI declaration for both subtunes |
| Flags / SID layout | `$0014`: explicit PAL, MOS6581, one SID; additional-SID fields zero |
| Header / embedded load | Header zero; embedded little-endian `$A600` |
| Init / play | `$A600` / `$A603` |
| Payload | 4,376 bytes, `$A600–$B717`; end `$B718` exclusive |
| Relocation fields | Start page and page count zero |

Reproduce acquisition and verification through the existing [setup workflow](../../setup/local-setup.md), without another downloader:

```sh
python3 scripts/setup-project.py --only references --include cybernoid-ii
python3 scripts/setup-project.py --check --only references --include cybernoid-ii
```

Both commands also select the two existing default DRAX references. Setup installs only verified bytes and preserves a modified local file rather than overwriting it. Reference binaries and WAVs remain outside Git.

## Bounded correspondence with the recovered listing

The existing cached listing `.local/downloads/tel-cybernoid2.asm` has SHA-256 `119b8cb1ecaf6a9700d1847c9879fa78d50229345dccaaa4f555d8354b73fe66` and the source revision linked above. It declares a generated `$1000` layout with init `$1000`, play `$1006`, two/default 1, zero speed word and PAL/6581 flags. The archive instead contains entry shims: `$A600→$A606` (`TAX`, then jump through `$A620→$A6CA`) and `$A603→$A626→$A716`. Do not reuse listing addresses as archive PCs.

| Static comparison | Result and limit |
| --- | --- |
| Literal initialization fragment, listing lines 190–194 | `STY $D416; INY; STY $D417; LDA #$1F; STA $D418` matches bytes `8c16d4c88c17d4a91f8d18d4` once at `$A6F5`. This is a code-byte match, not an observed store sequence. |
| Annotated nonempty eight-byte sound records, listing lines 1505–1522 | All 18 match once each, in source order, contiguously at `$B01C–$B0AB`. The 144-byte block has SHA-256 `25e907f6d8b97bb30b49d57e8d750032812a975ff892a409e4420fa958126377`. |
| Selected labels retained as navigation | `bass` at `$B01C`, `bassdrm` at `$B024`, `snardrm` at `$B02C`, `arp+filt` at `$B034`, first `melo-1` at `$B03C`. These are source labels attached to matching bytes, not proven title-instrument selections. |

The limited comparison makes the recovered listing a useful interpretation route. It does not prove that the entire player, score, tables or effect timing are byte-identical. The listing was not assembled during this intake. The [source-comparison receipt](../../../evidence/cybernoid-ii-intake/source-comparison.json) retains the exact record matches, bounded static disassembly and comparison limits; the [header receipt](../../../evidence/cybernoid-ii-intake/header.json) retains the inspected archive metadata. Separate bass and drum definitions do not establish actual voice time-sharing in a particular phrase.

## Reproduce the opening reference

Use the existing [audio renderer](../../workflows/audio-workflow.md), libsidplayfp **3.1.1 / SIDLite**, from initialization. Its `selectSong(0)` selects the archive's default #1. The render uses forced PAL, the declared MOS6581, power-on delay zero, 44,100 Hz mono PCM16, 30 seconds, unity gain, no normalization and no trimming. Choose a fresh output directory; the renderer does not protect an existing output from replacement.

```sh
mkdir build/cybernoid-ii-intake-new
.local/bin/render-sid .local/research/cybernoid-ii/Cybernoid_II.sid build/cybernoid-ii-intake-new/reference-opening.wav 30
shasum -a 256 build/cybernoid-ii-intake-new/reference-opening.wav
```

The [observed opening WAV](../../../build/cybernoid-ii-intake/reference-opening.wav) SHA-256 is `60c139597792fbe0251ecf563c6dfcd6c544c3486c7ff0c78e967b9723cd650c`. It contains 1,323,000 sample frames, peak 11,661, AC RMS approximately 3,186.94 and zero PCM rail samples. The renderer executable SHA-256 is `80c6e88730445f65e03e28a56bb251922461e6d4364897b0bd79195edb53fdfe`; its [source](../../../scripts/render-sid.cpp) SHA-256 is `c7bc5f7b0fe8d18a54ecde7338b6efa786f87f54ec258a00fb01025486bad5fc`. The [render receipt](../../../evidence/cybernoid-ii-intake/render-receipt.json) retains the command, settings and measurements. This is an opening reference, with no listening verdict or complete-form/ending claim.

## Selected-subtune execution

The shared [execution profile](../../validation/psid-audit.md#select-a-subtune-and-expose-ram-beneath-basic) now accepts the intact archive through `--profile pal-banked --subtune N`. It restores `$01=$36` before each call, exposing RAM beneath BASIC. This matches the address-dependent bank choice in the inspected [libsidplayfp 3.1.1 `iomap`](https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/psiddrv.cpp); its [song limit](https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/sidtune/SidTuneBase.h) is 256. Our parser rejects malformed song metadata rather than silently repairing it. No source header, code or table bytes are patched.

Init receives A=`subtune−1`, X/Y=0 and P=`$26`. Play receives A=`$FA`, retained X/Y and the successful raster comparison's C/Z set, N clear. This is the controlled polling host's contract; [libsidplayfp's IRQ driver](https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/psiddrv.a65) enters play with A=0. The bounded equality below establishes the declared host, not equivalence of those entry environments or synthesized PCM. The default strict profile and the separate [Shades CIA route](../../validation/cia-tracing.md) retain their existing scope.

On 2026-10-13, independent CPU execution and headless VICE agreed on every ordered `(phase, call, SID address, value)` in these windows, including initialization:

| Selected subtune / observed calls | Init stores / cycles | Play stores / maximum body cycles | VICE cadence |
| --- | --- | --- | --- |
| #1 title, 0–599 | 25 / 1,738 | 10,333 / 2,473 | 600 calls; phase deviation at most 5 cycles from the 19,656-cycle PAL grid |
| #2 game over, 0–63 | 25 / 1,738 | 1,253 / 2,599 | 64 calls; phase deviation at most 5 cycles from the same grid |

The polling tolerance is nine cycles; the CPU play-body budget is one PAL frame. Initialization writes `$D416=$FF`, `$D417=$00`, `$D418=$1F`, followed by zeroes to `$D415` down through `$D400`, in both selected runs. VICE captures stores from init entry through its return separately from outer play calls: init-internal calls to play remain initialization, including drivers with a shared init/play address. Executed fixtures guard these phase boundaries and subtune-dependent entry state. CPU instruction-start cycles and VICE post-instruction checkpoints remain distinct observations.

Reproduce into fresh directories after [dependency setup](../../setup/local-setup.md):

```sh
python3 scripts/psid_audit.py .local/research/cybernoid-ii/Cybernoid_II.sid --profile pal-banked --subtune 1 --ticks 600 --output build/cybernoid-title-new/audit.json
python3 scripts/trace-sid-vice.py .local/research/cybernoid-ii/Cybernoid_II.sid --profile pal-banked --subtune 1 --oracle build/cybernoid-title-new/audit.writes.json --first-call 0 --last-call 599 --output build/cybernoid-title-new/vice
python3 scripts/psid_audit.py .local/research/cybernoid-ii/Cybernoid_II.sid --profile pal-banked --subtune 2 --ticks 64 --output build/cybernoid-game-over-new/audit.json
python3 scripts/trace-sid-vice.py .local/research/cybernoid-ii/Cybernoid_II.sid --profile pal-banked --subtune 2 --oracle build/cybernoid-game-over-new/audit.writes.json --first-call 0 --last-call 63 --output build/cybernoid-game-over-new/vice
```

The [title report](../../../evidence/cybernoid-title-execution/vice/study.json), [game-over report](../../../evidence/cybernoid-game-over-execution/vice/study.json) and [execution receipt](../../../evidence/cybernoid-title-execution/provenance.json) index the source/tool hashes and exact scope. Full CPU store ledgers and parsed VICE traces are retained losslessly in the [evidence manifest](../../../evidence/manifest.json); use the [archive restoration workflow](../../workflows/build-cache.md) to recover their original working paths. Original SIDs, payload dumps and reference audio are excluded.

## Executed opening sound-record reads

The [instruction tracer](../tools/sid-program-analysis.md#trace-a-selected-subtune-in-banked-ram) records 40,415 instructions and 1,107 play stores for title calls 0–63, plus 25 initialization stores. VICE independently matches the call, address, value and writer PC for all 1,107 play stores in this window. Filtering executed `LDA`/`LDX`/`LDY` operand addresses through the 18 statically matched eight-byte records finds:

| Recovered label / actual archive address | Executed loads | Byte coverage |
| --- | --- | --- |
| `bass` / `$B01C` | 215 | All eight offsets; every observed value matches the pinned record |
| `bassdrm` / `$B024` | 215 | All eight offsets; every observed value matches the pinned record |
| `arp+filt` / `$B034` | 215 | All eight offsets; every observed value matches the pinned record |

The [read receipt](../../../evidence/cybernoid-title-instructions/table-reads.json) pins both the instruction trace and static lookup, records reader PCs and states the selection rule. These are actual table loads, rather than label matches alone; they do not yet establish field semantics, voice allocation, bass/drum time-sharing or a listening judgment. Preserve those distinctions when interpreting the listing.

```sh
PYTHONPATH=.tools/test-deps python3 scripts/trace-sid-program.py .local/research/cybernoid-ii/Cybernoid_II.sid --profile pal-banked --subtune 1 --first-call 0 --last-call 63 --output build/cybernoid-title-new/opening.trace.json
```

## Navigation for the complete-form probe

The [navigation receipt](../../../evidence/cybernoid-title-instructions/form-navigation.json.gz) separates executed opening observations from static branches that were not reached. These are actual archive addresses, not relocated listing addresses:

| State | Archive location / observation hook |
| --- | --- |
| Tempo reload / countdown | `$A629` / `$A682`; `$A720` decrements and `$A725` reloads 2 on calls 0, 3, …, 63 |
| Per-voice order / pattern cursors | `$A62D–$A62F` / `$A630–$A632`; `$A754` consumes order bytes |
| Per-voice row countdown / duration / repeats | `$A633–$A635` / `$A636–$A638` / `$A684–$A686` |
| Order pointers | Low/high banks `$AEFB–$AEFD` / `$AEFE–$AF00`; opening X=0/1/2 resolves to `$B0D8/$B14D/$B164` |
| Pattern pointers / scratch | Table `$AF01`, scratch `$46–$47`; `$A7A5/$A7AA` resolve and `$A7C0/$A936/$A8F6` consume bytes |
| Completed play body | `$AE2C` is the final `RTS` in all 64 observed calls |

At call 24, X=2 consumes pattern `$FF` at `$B284`, resets its pattern cursor 4→0 and decrements repeats 29→28 while retaining order cursor 3. This is a pattern repeat, not a song restart. Static code separately handles order `$FF` by resetting that voice's sequencing state, and order `$FE` by setting global play flag `$A717=1` and clearing SID; neither order-terminal branch executes in the opening window. Do not equate an individual voice wrap with a complete-state recurrence.

The recovered listing declares 33 pattern pointers, but its title orders include `$21`. The archive's prospective lookup at `$AF43/$AF44` yields `$B62D`; that selection was not executed in the retained opening. Consult actual consumed bytes before treating the listing's table layout as complete.

Next, use compact observations at these hooks to establish the complete title form, then connect selected records to changing synthesis state. Start with a bounded 2,048-call probe and extend only when its observations justify it. The existing 600-call title check is bounded execution evidence, not a complete-song analysis. Shades remains awaiting its independent reconstruction and transfer listening verdict.
