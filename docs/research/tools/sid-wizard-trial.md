# SID-Wizard 1.97: native Extra export without a desktop

Research and execution date: 2026-10-12. The official SID-Maker exporter accepts this repository's original native SWM1 instrument studies, emits the Extra player, and produces callable PSID and standalone PRG files through a reproducible headless adapter. This establishes a usable native export path. Rendered signal and CPU checks remain separate from a listening judgment; no claim of musical superiority follows from successful export.

## Source and build identity

| Component | Pinned material | SHA-256 |
| --- | --- | --- |
| SID-Wizard 1.97 source/examples | [Author's release](https://csdb.dk/release/?id=262561), [official archive](https://csdb.dk/getinternalfile.php/281063/SID-Wizard-1.97-sources-examples.tar.gz) | `aeb265f4a778b2acb5aad13e8e98af882888292f749f29f4d18cbf49850e57bc` |
| 64tass 1.60.3243 source | [Maintainer's download and published checksum](https://sourceforge.net/projects/tass64/files/source/64tass-1.60.3243-src.zip/download) | `9d83be3d23a2c55e085b7c7a7856c2f96080447ea120a6a8c21a217ed76427f0` |

The SID-Wizard hash identifies the acquired archive; upstream did not independently publish that checksum in the inspected material. The 64tass hash matches the maintainer's SourceForge download page. [setup-sidwizard.py](../../../scripts/setup-sidwizard.py) verifies both archives, extracts them under ignored `.tools/`, builds 64tass using `make` and a C compiler, and assembles the unmodified native `exporter.asm` with its original includes. The build uses `EMULATOR=0`, `TUI_ONLY=0`, `SID_AMOUNT=1`, and the upstream `SWversion="1.9"` driver signature within the 1.97 release. Symbol listing lines are sorted before hashing because 64tass does not emit them in a stable order. Setup records the assembler version, archive identities, assembled PRG hash, and symbol-file hash in `.tools/sid-wizard-exporter/build.json`; build output is retained in `build.log` there. External build commands have explicit deadlines, and a failed setup invalidates the previous build receipt.

The archive's `native/README.txt` declares SID-Wizard a WTF-licensed tool. Preserve that notice and the author's attribution, Mihaly Horvath/Hermit Software. 64tass includes its GPL v2 license and additional component notices. The build uses the existing documented [py65 1.2.0 dependency](../../first-song.md); its license is BSD. The host editor's bundled SDL, ncurses, MIDI, and audio libraries are unnecessary for this export route and have separate upstream notices.

## Contract and original routines

[export-sidwizard.py](../../../scripts/export-sidwizard.py) accepts a native SWM1 file including its two-byte KERNAL load address. The trial contract is one SID, one subtune with three sequences, Extra driver information value `3`, frame speed `1`, standard PAL tuning, and MOS8580 metadata. It rejects unsupported variants and timing rather than silently changing the native header. Module structure, pattern/instrument references, sequence endings, and saved row lengths are checked before bounded CPU execution. The adapter does not alter the input SWM.

The adapter loads the assembled SID-Maker into py65 and calls these upstream routines in their original order:

1. `setEXEdetails` selects and copies the actual Extra player and its frequency table.
2. `preparetunedata` invokes SID-Maker's native depackers, crops playback-only data, and constructs the sequence, pattern, instrument, chord, and tempo pointers.
3. `setplayer` applies the original data-pointer patch tables.
4. `SetSIDply` and `SetSIDt` prepare the PSID callable entry points and metadata; `dispMod` selects the 8580 declaration.
5. `setsaveparam`, stopped before the `SaveExp` file-I/O routine, prepares the original standalone executable starter and its relocation-copy operands.

These are direct routine calls with explicit memory inputs. No TUI session, key simulation, disk directory dialog, or screen-reading automation is involved. Each routine has a bounded instruction count; unsupported opcodes and failed return-stack checks stop export. The adapter serializes the upstream 1x SID saving layout: PSID v2 header, embedded `$1000` load address, and native player/data bytes. Its callable init and play addresses are `$1000` and `$1003`. The standalone PRG loads at `$0801`, enters via `SYS 2061` (`$080D`), and uses those same player addresses after the upstream starter copies the tune into place.

The source contract is defined by the archive's `native/sources/SWM-spec.src`, `include/packdepack.inc`, `include/player.asm`, `include/altplayers.inc`, and `exporter.asm`. An SWM instrument contains 16 parameter bytes, waveform/arpeggio, pulse and filter tables, the offset replacing its final filter delimiter, and an eight-byte name. That offset is one less than the table byte count. SID-Maker restores the delimiter and removes names from the playback payload. Names and all editable instrument parameters remain in the retained SWM/SWI files. The exporter reports this deliberate name omission; native table programs are not converted into a fixed waveform or flattened score.

## Reproduce the original study export

Run from the repository root after the [Python dependency setup](../../first-song.md). Setup downloads the pinned archives only when their cached copies are missing; subsequent setup and export can use the local cache. It needs Python 3.9 or later, `curl`, `make`, a C compiler, and py65 1.2.0. It does not require a host editor build or a display server.

```sh
python3 scripts/setup-sidwizard.py
python3 -m unittest discover -s tests -p sidwizard_export_test.py -v
python3 scripts/export-sidwizard.py songs/studies/sidwizard-repertoire/native/pulse-candidate.swm --output-dir build/sidwizard/pulse-candidate --title 'Pulse candidate' --author 'Original study'
python3 scripts/export-sidwizard.py songs/studies/sidwizard-repertoire/native/mix-candidate.swm --output-dir build/sidwizard/mix-candidate --title 'Mix candidate' --author 'Original study'
```

Each export writes `<stem>.sid`, `<stem>.prg`, and `<stem>.export.json`. The report records input/output hashes, the native module's named instruments, player/model/timing choices, callable and standalone addresses, upstream routine cycle counts, build provenance, and documented export omissions. Explicit PSID text overrides accept at most 31 ASCII characters per field. Output paths cannot overwrite the source or follow symlinks; existing evidence can only be reused when its bytes are identical. Choose a fresh output directory after changing source data or metadata.

The [original repertoire source](../../../songs/studies/sidwizard-repertoire/repertoire.json), [native workfiles](../../../songs/studies/sidwizard-repertoire/native), and [generator](../../../scripts/generate-native-instruments.py) retain the musical phrases and instrument programs independently of the generated playback binaries. See the [repertoire guide](../../../songs/studies/sidwizard-repertoire/README.md) for each candidate/reference pair and the scope of its sound-design change.

## Verification and material limits

The adapter tests run an original minimal SWM through the actual native exporter, assert deterministic PSID/PRG bytes, native instrument table retention, metadata and callable addresses, and rejection of unsupported timing, bad references, truncated modules, source collisions, and changed output evidence. Setup is a test prerequisite because upstream source and compiled tools are intentionally ignored rather than vendored.

The original pulse candidate and three-voice mix each passed 501 calls through the separate [PSID CPU audit](../../../scripts/psid_audit.py). At that bound, the pulse reached 1,271 modeled cycles per play call and the mix 2,193, against a PAL frame budget of 19,656. Both used the native Extra ghost-register path, which produced 12,525 SID stores over 501 calls. This records functional CPU execution with an explicit environment; it does not measure hardware bus contention or establish the musical result.

The first independent audio render exposed a separate renderer bug: its default subtune had not been selected, so libsidplayfp passed `$FF` to an init routine whose accumulator selects the subtune. Native standalone VICE playback produced signal while that PSID render was silent. The [audio workflow](../../audio-workflow.md) records the renderer correction and independent regression guard. The corrected renderer allows the exported native driver to receive subtune `0`; no SID-Wizard player modification was needed.

### Compressed-pattern format

A pattern footer stores the **uncompressed** byte count, including its delimiter, after instrument/effect-column optimization. NOP-run compression reduces the file size but does not change that footer. Split generated patterns at either native limit: 248 rows or 249 uncompressed bytes including the delimiter. Keep packed and uncompressed sizes distinct in conversion reports.

SID-Maker walks patterns backward using that decoded count. A packed-length footer can corrupt sequence pointers, causing ROM reads or silent exports. The validator must follow the upstream NOP-expansion rules rather than subtracting the footer from the file position. The defining code is [the pinned packer/depacker](../../../.tools/sid-wizard-1.97/native/sources/include/packdepack.inc), specifically the pattern-compression block and `depkptseq`.

[Exporter regression tests](../../../tests/sidwizard_export_test.py) reject incorrect packed-length footers and run independently encoded 120- and 240-row sparse patterns through the original exporter and CPU playback. [Arrangement tests](../../../tests/sidwizard_arrangement_test.py) check adaptive chunking against the uncompressed size limit.

The adapter covers native file acceptance and export, not interactive editor audition or reopening/editing through the editor UI. It currently excludes multispeed/CIA timing, alternative players, nonstandard tuning, extra SID chips, SWP, ROM players, SFX, and digi-echo export. Those are explicit limits of this trial adapter, not inferred limits of SID-Wizard. Normal table-driven SID expression remains in the native format; broader backend adoption still depends on rendered comparisons and recorded listening judgments described in the [composition-system assessment](composition-tools.md).
