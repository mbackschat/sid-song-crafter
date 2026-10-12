# Choosing a composition system for excellent SID sound

Research date: 2026-10-12. Recommendation: evaluate **SID-Wizard Normal/Extra as the sound-design reference**, **GoatTracker as the first interchange/automation candidate**, and **SID Factory II as a source-study and alternative authoring environment**. Keep the local simple player as a correctness baseline. This is a source-based assessment; none of these editors has yet passed a local import/edit/export acceptance trial.

Execution update: [SID-Wizard Extra now has a verified headless native export adapter](sid-wizard-trial.md). Nine original workfiles pass native packing, CPU checks and rendering; [four A/B pairs](../../instrument-trials.md) are prepared. This supports using its native instrument model for the next sound-design work. Editor UI round-trip and editor-versus-export listening remain open, so this does not yet complete the full acceptance trial below.

## What the masters' tools teach us

The [composer studies](../composers/README.md) show that an editor and a player form a musical system. Instrument programs, command languages, audition speed, and voice-sharing rules influence composition. Historical sophistication did not always mean a modern graphical tracker: custom assemblers, bytecode, helper programs, and a second machine could provide an effective working environment. Consequently, choosing a file format is not enough; we need the expressive authoring model and its actual C64 driver.

For this project, the native editable song should retain musical form and instrument programs. MIDI/common-score import can supply notes, but cannot become the authoritative representation of all subsequent SID expression. Do not repeatedly export a finished native arrangement through MIDI. Keep original sources, import reports, native workfiles, instrument definitions, driver version, and rendered evidence together.

## Candidate comparison

| System | Evidence for expressive authoring | Automation and project fit | Main qualification |
| --- | --- | --- | --- |
| GoatTracker 2 / Stereo | Separate waveform/arpeggio, pulse, and filter programs; configurable instruments and pattern commands | Documented song/instrument format; existing converter ecosystem; stereo branch offers an alternative two-chip backend | The inspected relocator is interactive; a batch exporter must be verified, not assumed |
| SID-Wizard Normal/Extra | Per-instrument tables and restart control, multispeed, detune, chord programs, keyboard tracking, multiple player variants | Native C64 and host editions; source and many editable instruments; MIDI/XM/SNG conversion | Conversion precision and player-variant differences require explicit tests; TUI is still interactive |
| SID Factory II | Multiple Laxity/JCH drivers, editable source tunes, waveform/pulse/filter programs and driver-specific commands | Native macOS ARM support; packer/relocator; useful human authoring and driver comparison | Capabilities belong to a selected driver/version; cross-tool import is not proof of equivalence |
| Composer-specific driver | Can encode the exact sound and scheduling a piece requires | Excellent for studying mechanisms or a capability absent from established tools | Original assembler dialects, relocation, integration, and licensing need component-level inspection |
| Current repository player | Fixed instruments and exact note scheduling | Deterministic headless baseline with independent tests | Not the intended final sound-design ceiling |

## GoatTracker: strongest initial interchange candidate

[Cadaver's tool page](https://cadaver.github.io/tools.html) identifies the table-based editor and its stereo variant. The [older v2.72 manual mirror](https://github.com/leafo/goattracker2/blob/master/readme.txt) documents GTS5 song/instrument structures, waveform programs, restart choices, and runtime caveats. The inspected [`greloc.c`](https://github.com/leafo/goattracker2/blob/a78e7e5273bfbeb17c3777b1f5ceb63b8e6b4667/src/greloc.c) contains an interactive `relocator()` with SID/PRG/BIN selection; it is not evidence of a standalone `gt2reloc` CLI.

**Judgment:** a native `.sng` export is a promising bridge from our arrangement recipes because the file contract is documented and editable. Retain separate pitch, instrument, and command data. Verify one complete advanced instrument through the intended packer before implementing a whole-song exporter. Pin an official release for production; the inspected GitHub mirror is documentary evidence, not automatically the current upstream version.

MiniPlayer2 is an instructive alternative driver, but its author explicitly documents reduced capabilities, restart caveats, pulse-program skipping, and NTSC differences. Its converter cannot be assumed to preserve an advanced GoatTracker arrangement. For a sound-quality-first project, low raster cost alone is not a reason to choose it. [MiniPlayer2 README](https://github.com/cadaver/miniplayer2)

## SID-Wizard: strongest sound-design reference candidate

The [native manual](https://github.com/anarkiwi/sid-wizard/blob/2bf1703dca907d59b587d7829989215ec855a009/native/manuals/SID-Wizard-1.9-UserManual.txt) distinguishes player variants; Extra retains table execution and adds behaviour beyond the smaller players. It documents separate multispeed calls and SID-Maker export. The [author's 1.97 release](https://csdb.dk/release/?id=262561) includes native/source packages and a contributed Apple Silicon host build. Source inspection must distinguish that full release from the Vessel-oriented GitHub fork, which omits the host edition.

The official source archive's `resources/SID-Wizard-1.97-UserManual.txt` documents an ncurses TUI. In `SIDwizard.c`, `-cli` and `-tui` select that interactive interface; they do **not** identify an unattended conversion mode. This is valuable for avoiding a display, but is a different guarantee from headless batch export. The same manual documents an optional digi-echo exporter with chip, speed, raster-time, and memory constraints. [Official source archive](https://csdb.dk/getinternalfile.php/281063/SID-Wizard-1.97-sources-examples.tar.gz)

**Judgment:** use Normal/Extra and the editable instrument collection to learn what a capable instrument program should express. Trial the real export path and the supplied conversions before selecting SWM as our main generated native format. A TUI build could support terminal-based work, but our reproducible pipeline should prefer explicit file conversion or a small maintained export adapter over fragile keystroke automation.

## SID Factory II: drivers and editable repertoire

The [maintainer README](https://github.com/Chordian/sidfactory2/tree/d6852faea2f8929df30e6f2ce008f93d974637d3) lists Laxity/JCH drivers, source tunes, conversion, relocation, and macOS ARM support. Driver selection matters: [Driver 11 notes](https://github.com/Chordian/sidfactory2/blob/d6852faea2f8929df30e6f2ce008f93d974637d3/dist/documentation/notes_driver11.txt) specify instrument flags, restart-table indexing, waveform/pulse/filter programs, arpeggios, and version-dependent effects. For example, the driver notes distinguish local ADSR changes from changes retained until a different instrument is selected.

**Judgment:** this is particularly valuable for learning from editable compositions and comparing driver behaviour. It is also a credible authoring candidate if a desired sound fits its drivers well. Our automation must name the driver version, retain table data, and validate converted songs. Do not flatten a source tune into notes merely because a converter recognizes its extension.

The repository contains [GPL v2 text in `SIDFactoryII/COPYING`](https://github.com/Chordian/sidfactory2/blob/d6852faea2f8929df30e6f2ce008f93d974637d3/SIDFactoryII/COPYING). This improves the earlier inventory, which had not located a top-level license. It does not independently settle the reuse terms of every included tune or driver; retain their own notices.

## Acceptance trial before adopting a backend

Use the same short original musical fixture for each serious candidate. This is a proposed trial, not a completed benchmark:

1. Compose a bass/drum shared voice, an evolving pulse lead with delayed vibrato, and a filtered accompaniment. Include tied notes, repeated attacks, a rest, and an instrument change.
2. Save the native workfile and named instruments. Reopen and change one phrase and one sound parameter. Confirm the native format remains the editable source of truth.
3. Export SID and standalone playback using a recorded driver/version. Render with the declared SID model and verify update cadence and ending behaviour.
4. Compare editor playback and exported playback at matched listening level. Listen in isolation and in the full mix; compare attacks, pitch movement, rhythmic clarity, filter ownership, and sustained-note evolution.
5. Repeat the export without a desktop interaction where supported. Record the exact CLI/API or identify the missing adapter; do not call interactive TUI operation a completed batch pipeline.

Choose the backend on the audible result and retained musical control, then on reproducibility and editing cost. Change the recommendation if the trial exposes an unfixable expressive or export limitation. A custom engine remains appropriate for a concrete requirement that established systems cannot satisfy.

The current `verify_callable` CPU oracle validates this repository's particular exporter/player contract. Its symbols, memory layout, and articulation assumptions do not apply automatically to a tracker export. A native-tool trial needs driver-aware execution checks and the correct scheduling/PSID/RSID environment; retain generic PCM checks where suitable rather than forcing a different driver through our existing manifest schema.

## Reproducible source-inspection record

| Material inspected | Identity | Local status |
| --- | --- | --- |
| GoatTracker manual and relocator mirror | `leafo/goattracker2` at `a78e7e5273bfbeb17c3777b1f5ceb63b8e6b4667` | Manual read online; relocator read as source; not built |
| SID Factory II README, driver notes, license | `Chordian/sidfactory2` at `d6852faea2f8929df30e6f2ce008f93d974637d3` | Documentation/source inspected; not launched |
| SID-Wizard Vessel fork native manual | `anarkiwi/sid-wizard` at `2bf1703dca907d59b587d7829989215ec855a009` | Native documentation inspected; not treated as the full host release |
| Official SID-Wizard 1.97 source/examples | Archive SHA-256 `aeb265f4a778b2acb5aad13e8e98af882888292f749f29f4d18cbf49850e57bc` | Native exporter assembled unmodified and executed headlessly; host editor not built; [trial record](sid-wizard-trial.md) |

The archive and selected reading copies are cached under ignored `.local/research/composition-tools/`. The archive hash records the acquired bytes; it is not claimed to be an independently published upstream checksum. Keep research summaries here and preserve upstream licenses if adopting code.
