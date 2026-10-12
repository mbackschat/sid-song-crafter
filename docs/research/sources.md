# Source register

Access date for all entries: **2026-10-12**, unless a source's publication date is stated separately. “Inspected” means the identified documentation or code was read; it does not mean built, rendered, listened to, or tested on hardware. Mutable branch links reflect the version served on that date. Exact local revisions are stated where available. Notes are original summaries, not full copies of the linked publications.

## S01

**MOS Technology, 6581 SID datasheet, HTML transcription by Simon Inns.** [Readable transcription](https://www.waitingforfriday.com/?p=661). Manufacturer documentation reproduced by a third party; inspected register, waveform, envelope, and filter sections. The transcriber describes OCR followed by manual editing, so transcription errors remain possible. Prefer this searchable text for navigation and compare critical details with implementation evidence. No PDF snapshot downloaded; reproduction rights not inferred.

## S02

**reSID, register dispatch.** [sid.cc](https://github.com/libsidplayfp/resid/blob/master/sid.cc). Primary emulator source; inspected `SID::read`, `SID::write`, and oscillator connections. GPL-2.0-or-later headers. Supports register layout and write-only/readback distinction; bus-decay details are model/version-specific.

## S03

**reSID, envelope implementation.** [envelope.cc](https://github.com/libsidplayfp/resid/blob/master/envelope.cc) and [envelope.h](https://github.com/libsidplayfp/resid/blob/master/envelope.h). Primary measured-model implementation; inspected rate counter, sustain levels, gate transitions, and ADSR delay discussion. GPL-2.0-or-later headers. Explains behaviour missing from simplified datasheet summaries.

## S04

**libresidfp project.** [Repository and README](https://github.com/libsidplayfp/libresidfp). Primary current emulator documentation; inspected claimed SID-model support, measured combined-waveform approach, and separation from libsidplayfp. GPL-family licensing; verify the exact version's license on adoption. Emulator modelling is evidence about hardware, not proof of identical output from all physical chips.

## S05

**libsidplayfp C64 model.** [c64.cpp](https://github.com/libsidplayfp/libsidplayfp/blob/master/src/c64/c64.cpp). Primary source; inspected PAL/NTSC clock constants and additional-SID address handling. Clock figures in this library were calculated from those constants. Moving `master`, not a locally pinned checkout.

## S06

**Michael Steil's c64ref memory reference.** [Combined memory map](https://www.pagetable.com/c64ref/c64mem/), [source repository](https://github.com/mist64/c64ref). Inspected processor-port/banking and vector references. Aggregates identifiable original manuals and source listings; authority and rights belong to each contributing source. Site showed revision `1295642`, dated 2026-04-05.

## S07

**Lasse Öörni, MiniPlayer2 PRG integration example.** [prgexample.s](https://github.com/cadaver/miniplayer2/blob/master/prgexample.s). Primary assembly example; inspected raster IRQ, initialization, border profiling, zero-page assignment, and KERNAL return. Repository MIT license. Not assembled or executed here.

## S08

**Lasse Öörni, GoatTracker tools and documentation.** [Author's tool page](https://cadaver.github.io/tools.html), [official source browser](https://sourceforge.net/p/goattracker2/code/HEAD/tree/), [readable v2.72 manual in a fork](https://github.com/leafo/goattracker2/blob/master/readme.txt). Author page and older manual inspected; official tree observed revision r172. Do not mistake the older mirror for the newest release. GPL editor; exported runtime and example-music rights require component-level inspection.

## S09

**Thorsten Klose, MIDIbox SID wavetable tutorial.** [Worked tutorial](https://www.ucapps.de/howto_sid_wavetables_1.html). Author's historical MIDIbox SID v1 documentation; inspected waveform sequencing and the Monty percussion analysis. Useful synthesis explanation; not a standalone C64 player specification. Musical example analysis is attributed to the author; reuse rights are separate.

## S10

**Furnace maintainers, C64 system and export documentation.** [C64 system](https://github.com/tildearrow/furnace/blob/master/doc/7-systems/c64.md), [C64 instruments](https://github.com/tildearrow/furnace/blob/master/doc/4-instrument/c64.md), [export guide](https://github.com/tildearrow/furnace/blob/master/doc/2-interface/export.md). Primary docs inspected for chip differences, shared parameters, and native-export support. A supported emulated chip does not establish a native exporter. See repository license and dependency notices before reuse.

## S11

**Lasse Öörni, MiniPlayer2.** [README/repository](https://github.com/cadaver/miniplayer2), [player.s](https://github.com/cadaver/miniplayer2/blob/master/player.s). Primary source inspected for pattern/table execution, self-modifying code, alignment, feature limits, and NTSC caveats. MIT license, copyright 2026 Lasse Öörni. Converter and examples are listed; no local conversion performed.

## S12

**David Youd and contributors, ChiptuneSAK.** [README](https://github.com/c64cryptoboy/ChiptuneSAK), [GoatTracker module](https://github.com/c64cryptoboy/ChiptuneSAK/blob/master/chiptunesak/goat_tracker.py), [MIT license](https://github.com/c64cryptoboy/ChiptuneSAK/blob/master/LICENSE), [examples](https://github.com/c64cryptoboy/ChiptuneSAK/tree/master/examples). README, license, and conversion module inspected. Example names discovered, not executed. Alpha status and proposed features must not be confused with implemented conversion paths.

## S13

**HVSC maintainers, SID file format specification.** [Live plain-text specification](https://www.hvsc.de/download/C64Music/DOCUMENTS/SID_file_format.txt). Primary format reference; inspected PSID/RSID headers, timing, flags, additional SID fields, and version descriptions. The live document includes v5. No immutable revision or checksum captured; recheck against the intended player release before implementation.

## S14

**libsidplayfp PSID/RSID parser.** [PSID.cpp](https://github.com/libsidplayfp/libsidplayfp/blob/master/src/sidtune/PSID.cpp). Primary source inspected for accepted versions, RSID restrictions, model flags, and extra-SID address validation. The accessed parser accepts versions only through v4; this observation is explicitly distinct from the live v5 specification. No parser acceptance test executed locally.

## S15

**FPGASID project, CONFIGURU.** [Configuration documentation](https://www.fpgasid.de/configuru), [documentation index](https://www.fpgasid.de/documentation). Manufacturer/project documentation inspected for true versus pseudo stereo and address configuration. Relevant to software targeting, not an instruction to wire or modify hardware.

## S16

**VICE team, machine-specific manual.** [Online manual](https://vice-emu.sourceforge.io/vice_7.html). Primary documentation inspected for additional SID configuration. Online options may differ from the installed 3.9 release. Local launcher/resource files were inspected separately under `/Applications/vice-arm64-gtk3-3.9`; the restricted-shell version probe failed. No emulation success claimed.

## S17

**Hermit, SID-Wizard 1.97 release.** [Author release on CSDb](https://csdb.dk/release/?id=262561), dated 2026-06-24. Release notes and linked source/examples package inspected as a listing, not downloaded or built. Includes ROM-safe player variants and native/host packages. Author's license declaration is recorded as such; dependency and tune licenses were not audited. [A public fork](https://github.com/anarkiwi/sid-wizard) is supplementary, not proof of parity with this release.

## S18

**Chordian and contributors, SID Factory II.** [Repository](https://github.com/Chordian/sidfactory2), [maintainer download page](https://blog.chordian.net/sf2/). README and example-source listings inspected; driver support and editable tune collections are maintainer claims. No unambiguous top-level reuse license established in this pass. Do not treat public source or example availability as an automatic permission grant.

## S19

**libsidplayfp maintainers, library and command-line player.** [Library README](https://github.com/libsidplayfp/libsidplayfp), [sidplayfp manual](https://github.com/libsidplayfp/sidplayfp/wiki/sidplayfp). Primary docs inspected for emulator/player roles, build requirements, and WAV output. GPL-family project; use the chosen release's build/license files. The initial research was documentary; subsequent execution evidence is recorded separately in [local setup](../local-setup.md).

## S20

**Lasse Öörni, SIDDump.** [Repository/README](https://github.com/cadaver/siddump), [siddump.c](https://github.com/cadaver/siddump/blob/master/siddump.c). v1.11 documentation and source inspected for command flags, cadence, and three-channel snapshots. BSD three-clause license. Execution-environment and sampling limits matter when interpreting traces.

## S21

**reSID, oscillator implementation.** [wave.cc](https://github.com/libsidplayfp/resid/blob/master/wave.cc). Primary source inspected for model-specific waveform handling, noise interactions, and TEST behaviour. GPL-2.0-or-later headers. Distinct from the newer standalone reSIDfp project.

## S22

**Beethoven-Haus, Für Elise source material.** [Surviving sketch, BH 116](https://www.beethoven.de/de/media/view/5010945952710656?page=0), [work entry, WoO 59](https://www.beethoven.de/de/work/view/5327609864912896/Bagatelle%20f%C3%BCr%20Klavier%20%28a-Moll%29%20WoO%2059?fromArchive=6299845270700032). Primary institutional catalogue inspected for identity and manuscript context. Not a completed note-by-note transcription or a blanket license for site images.

## S23

**IMSLP, Flight of the Bumblebee / The Tale of Tsar Saltan.** [Catalogue entry](https://imslp.org/wiki/Flight_of_the_Bumblebee). Source/edition catalogue inspected; redirects to the opera's material. A Charles A. Johnson MIDI contribution dated 2023 is labelled CC BY 4.0. File bytes, note accuracy, and suitability for this project were not validated. Check item-specific attribution and rights before adopting a file.

## S24

**Christian Gleissner, c64bridge.** [Repository at pinned revision](https://github.com/chrisgleissner/c64bridge/tree/0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18), [SID compiler](https://github.com/chrisgleissner/c64bridge/blob/0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18/src/sidwaveCompiler.ts), [preset implementation](https://github.com/chrisgleissner/c64bridge/blob/0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18/src/tools/meta/audio.ts). User cloned repository; README, skill, package/runtime configuration, and relevant compiler paths inspected locally. Package 1.0.4. Package metadata GPL-2.0-only; some source headers say or later. Preserve notices and resolve component licensing before redistribution. Runtime installation status is tracked in [local setup](../local-setup.md).

## S25

**HVSC, archive information and search.** [Information/rights](https://www.hvsc.c64.org/info), [FAQ](https://www.hvsc.c64.org/faq), [search](https://www.hvsc.c64.org/search). Archive-maintainer guidance inspected for tune rights, STIL, metadata, and format distinctions. [CGSC](https://www.c64music.co.uk/) is a related discovery lead; its archive was not inspected directly. No HVSC corpus downloaded in this pass.

## S26

**sunsided, C64 skills.** [Pinned repository](https://github.com/sunsided/c64-skills/tree/480b253b147655fa6ff6eb74577d1a2523d512d4), [SID skill](https://github.com/sunsided/c64-skills/blob/480b253b147655fa6ff6eb74577d1a2523d512d4/c64-sid/SKILL.md). User cloned repository; SID entry point and its bundled specification inspected locally. References are historical manual extracts. No top-level license established; historical availability does not prove public-domain status. Local adaptations are recorded in [the skill manifest](../../skills/README.md).

## S27

**nschneir, Project64.** [Repository](https://github.com/nschneir/Project64). README inspected: Python/C64/VICE tooling, cc65 workflow, skills and MCP; repository declares MIT, with VICE separately GPL. Candidate only, not installed or run. Do not confuse it with the Nintendo 64 emulator of the same name.

## S28

**henols, c64-re-tools.** [Repository](https://github.com/henols/c64-re-tools). README inspected for Claude Code plugin, reverse-engineering skills, VICE broker, and skill dependencies. Candidate only; no source/runtime/license audit or installation. Its own marketplace is separate from the connected marketplace queried here.

## S29

**cybersorcerer, c64u.** [Repository](https://github.com/cybersorcerer/c64u). Discovery-level README evidence for Ultimate CLI and skills. Hardware-oriented candidate; no local installation, detailed skill review, or compatibility claim.

## S30

**OpenAI, local skills and MCP configuration.** [Build skills](https://learn.chatgpt.com/docs/build-skills), [MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli). Official docs inspected for `.agents/skills`, symlink support, trusted-project `.codex/config.toml`, stdio command/cwd/env configuration, and reload behaviour. Applied only to project-local integration; no global configuration changed.

## S31

**Mutopia Project, Für Elise typesetting.** [Catalogue](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=931), [published LilyPond source](https://www.mutopiaproject.org/ftp/BeethovenLv/WoO59/fur_Elise_WoO59/fur_Elise_WoO59.ly). The opening pitches and durations were checked against the typesetter's source for the project's nine-note monophonic excerpt. The edition is identified as Breitkopf & Härtel, 1888, and the typesetting as public domain. The editable [project score](../../songs/fuer-elise-opening.json) records the transcription scope and provenance; it is not a complete piano arrangement.

## S32

**Homebrew, VICE formula.** [Formula source](https://github.com/Homebrew/homebrew-core/blob/master/Formula/v/vice.rb), [formula API](https://formulae.brew.sh/api/formula/vice.json). Inspected version 3.10, with `--enable-gtk3ui` hardcoded and no exposed build options. Its test invokes `-console`, which does not make the bottle a separate headless build. The formula provides a source for build-dependency names; project-local headless build evidence belongs in the [VICE investigation](../vice-startup-investigation.md).

## S33

**VICE team, official 3.9 source release.** [Source archive](https://sourceforge.net/projects/vice-emu/files/releases/vice-3.9.tar.gz/download). Archive SHA-256 verified against the release listing; configure, headless startup, macOS path lookup, and build rules inspected locally. A genuine headless ARM64 `x64sc` was built and exercised to a CPU-cycle limit. The [investigation](../vice-startup-investigation.md) retains exact source/tool checksums, commands, warnings, workaround mechanisms, and the separate socket-binding restriction. GPL-family source; no system VICE installation was changed.

## S34

**Homebrew and libsidplayfp maintainers, libsidplayfp 3.1.1 binary package.** [Formula](https://formulae.brew.sh/formula/libsidplayfp), [package metadata](https://formulae.brew.sh/api/formula/libsidplayfp.json), [pinned player implementation](https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/player.cpp). The Apple Silicon bottle was checksum-verified and extracted locally with its GPL-2.0-or-later notice. A small static-linked renderer executes its SIDLite engine; [audio evidence](../audio-workflow.md) records PCM and register verification, the mixer-buffer documentation mismatch, and the host playback failure. This is not a claim of reSIDfp or physical-SID output.

## S35

**py65 maintainers, independent 6502 interpreter 1.2.0.** [PyPI release](https://pypi.org/project/py65/1.2.0/), [release metadata](https://pypi.org/pypi/py65/1.2.0/json). The wheel was verified against its published SHA-256 and installed into the ignored project test-dependency directory. BSD-licensed CPU execution supplies an independent oracle for the assembled song; the [song guide](../first-song.md) specifies its modeled raster input and limits, rather than treating a CPU interpreter as full C64 hardware emulation.
