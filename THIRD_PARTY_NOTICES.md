# Third-party notices

The [MIT license](LICENSE) applies to SID Song Crafter's original code, tests, documentation, recipes and project artwork to the extent their authors hold the relevant rights. It does not relicense third-party software, musical compositions, arrangements, recordings, speech, source editions, quoted material or recovered third-party code/data. Existing upstream notices and separately stated terms continue to apply, including inside mixed research files and generated outputs.

The inventory below records the directly used components and source material checked on 2026-10-15. Downloaded tools, dependency packages, skills, ROMs, model weights and reference recordings live in ignored local directories; they are not bundled by adding this notice. Keep each dependency's complete license, copyright notices and any required corresponding source with a redistribution. This inventory does not replace those materials or establish permission to publish a musical reconstruction. Follow the [public repository boundary](CLAUDE.md#public-repository-boundary).

## Retained public-domain score editions

These source files retain their upstream public-domain declarations. The MIT grant does not place restrictions on the underlying public-domain material.

| Source | Retained material and attribution | Rights basis |
| --- | --- | --- |
| Ludwig van Beethoven, *Für Elise*, WoO 59; Mutopia 931 | [LilyPond source](songs/sources/fuer-elise.ly), [MIDI](songs/sources/fuer-elise.mid) and the derived score; typeset by Stelios Samelis from Breitkopf & Härtel, 1888; `Mutopia-2015/08/18-931` | The retained LilyPond header states `license = "Public Domain"` and includes the typesetter's dedication. Source URLs, unchanged-file hashes and the composition/edition basis are in the [score record](docs/songs/fuer-elise-score.md#original-sources). [Mutopia catalogue](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=931). |
| J. S. Bach, *Toccata and Fugue in D Minor*, BWV 565; Mutopia 1780 | [LilyPond source](songs/studies/bach-toccata-opening/source/ToccataFugue.ly), [MIDI](songs/studies/bach-toccata-opening/source/ToccataFugue.mid) and derived source notes; typesetter Anonymous, Bach-Gesellschaft Ausgabe, 1867; `Mutopia-2011/09/11-1780` | The retained LilyPond header states `copyright = "Public Domain"` and includes the typesetter's dedication. The [Bach study](docs/research/composition/bach-toccata.md#retained-source-files) records the composition/edition basis, original URLs and hashes. [Mutopia catalogue](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1780). |

Public-domain status of a composition does not clear a later arrangement, performance or recording. In particular, a DRAX SID arrangement of Beethoven is a separate source from the Mutopia score.

## Music, arrangements and research evidence

The [asset registry](config/local-assets.json) identifies reference SIDs and imported MIDI arrangements by title, credited C64 musician or arranger, source URL and SHA-256. The corresponding [composition studies](docs/research/composition/README.md) record the selected versions and scope. The references include DRAX, Chris Hülsbeck, Jeroen Tel, Rob Hubbard, Ben Daglish, Martin Galway, Tim and Geoff Follin, Pascal van Loosbroek, Johannes Bjerregaard, Mark Cooksey, Russell Lieblich, Karl Hörnell, Robert Lee Woodyard and Stan Kicak, plus the credited composers and arrangers of their source material. An unidentified credit remains unidentified; neither HVSC availability nor attribution is an open license.

The [game-music permission review](docs/research/game-music-permissions.md) records a scoped exception: Martin Galway’s published Rambo loader source is GPLv3-licensed. Its music, source-derived scores and combined reconstructed SID/WAV retain [GPL version 3](samples/rambo-loader/LICENSE), Galway’s credit and modification notices; they are not relicensed MIT. Independently authored reusable tools retain MIT separately. This does not clear other subtunes in the original Rambo archive.

- [Faithful loader sample](samples/rambo-loader/README.md): editable score and complete corresponding player/compiler sources are pinned in its manifest.
- [Accepted native stereo sample](samples/rambo-stereo/README.md): full two-SID/WAV export and labelled 32–64-second featured excerpt, with corresponding source and arrangement pins.
- Earlier [palette interpretation](songs/studies/rambo-interpretation/README.md) and [three-part stereo treatment](songs/studies/rambo-stereo/README.md): the same music terms cover their [palette evidence](evidence/rambo-interpretation/README.md) and [stereo evidence](evidence/rambo-stereo/README.md).
- [Expanded ensemble](songs/studies/rambo-ensemble/README.md), [held-chord expansion](songs/studies/rambo-chord-expansion/README.md) and [native centered-lead revision](songs/studies/rambo-centered-native/README.md): the same terms cover their source-derived programs and [ensemble records](evidence/rambo-ensemble/README.md), [complete source observations](evidence/rambo-resource-audit/README.md) and [centered-lead evidence](evidence/rambo-centered-native/README.md).

Original reference SID binaries, uncleared MIDI arrangements and reference WAVs stay local; the explicitly public-domain score MIDIs listed above are retained in Git. Musical note data, instrument/table data, speech data, source excerpts and recovered programs in tracked reconstructions or evidence do not acquire an MIT license through analysis, transcription, independent playback or a change of file format. This exception applies to third-party expression wherever it appears, including under `songs/`, `scripts/studies/` and `evidence/`; the project's original analysis and tooling remain covered by MIT.

Legacy tracked musical reconstructions have not all been cleared for further publication. The [publication policy](CLAUDE.md#public-repository-boundary) explicitly identifies [Flashdance](songs/flashdance-decoded.json) and [Shades](songs/shades-score.json) as containing note data requiring rights review. This notice does not clear those files or other source-derived scores, native modules, players or exports. When no permission for the composition and the particular arrangement is established, retain the source references, hashes and reusable original tools without distributing uncleared musical material.

The local James Kibbie BWV 565 recording is separately attributed and licensed under CC BY-NC-ND 3.0 in the [Bach reference record](docs/research/composition/bach-toccata.md#organ-performance-reference). It is not part of the MIT grant. The alternative Ashtar Moïra recording's performance-rights grant remains unverified there. The imported Pink Panther and Moon River MIDI arrangements likewise have no redistribution/adaptation grant established by this project; see their [source studies](docs/research/composition/README.md).

## Build, playback and validation components

The tools and libraries below are acquired into ignored `.tools/` or `.local/` directories, or installed separately. The reviewed Bach and instrument-mix SID/PRG downloads in [samples](samples/README.md) embed SID-Wizard player code; its upstream declaration below applies to that code. The sample manifests identify the source music, our arrangement and the pinned player separately. The documented versions and pins identify the inspected sources; a newer version needs its own license check.

| Component and source | Version / use | Upstream terms and retained notice |
| --- | --- | --- |
| [c64bridge](https://github.com/chrisgleissner/c64bridge/tree/0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18) by Christian Gleissner | Commit `0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18`, package version 1.0.4; the TypeScript build imports its assembler; live bridge use is optional | Its pinned `package.json` declares `GPL-2.0-only` and its `LICENSE` contains GPL v2. The imported `src/tools/translation/assembler.ts` instead says “GNU General Public License v2.0 or later” and `Copyright (C) 2025 Christian Gleissner`. Preserve both upstream declarations; this notice does not resolve their difference or relicense that code. The optional `sid-music` skill is from the same revision and installs the upstream `LICENSE` alongside it. |
| [SID-Wizard](https://csdb.dk/release/?id=262561), Hermit Software / Mihaly Horvath, with help from Soci of Singular Crew | 1.97, [pinned source/examples archive](https://csdb.dk/getinternalfile.php/281063/SID-Wizard-1.97-sources-examples.tar.gz); native exporter and player | `native/README.txt` declares SID-Wizard a “WTF-licensed tool”; the exact declaration is retained below. No formal SPDX identifier is inferred. SID-Wizard player code embedded in exported SID/PRG files remains upstream code under its own declaration, rather than becoming project-authored MIT code. Example tunes and other bundled material need their own rights check before redistribution. |
| [64tass](https://sourceforge.net/projects/tass64/) by Marek Matula, BiGFooT/BReeZe and Soci/Singular, with other contributors | 1.60.3243; [pinned source archive](https://downloads.sourceforge.net/project/tass64/source/64tass-1.60.3243-src.zip), used to build the native exporter | GPL-2.0-or-later in `64tass.c`. The archive also retains `LICENSE-GPL-2.0`, `LICENSE-LGPL-2.0`, `LICENSE-LGPL-2.1`, `LICENSE-my_getopt` and per-file notices. These component terms are not replaced by MIT. |
| [libsidplayfp](https://github.com/libsidplayfp/libsidplayfp/tree/v3.1.1), including SIDLite | 3.1.1; the [renderer setup](docs/workflows/audio-workflow.md#pinned-library-setup) pins the Homebrew bottle and links its static library | GPL-2.0-or-later. The package retains `COPYING`, `AUTHORS.md` and its own dependency notices, including MIT-licensed hashlib. Its README credits Simon White (2000–2001), Antti Lankila (2007–2010) and Leandro Nini (2010–2026). The resulting linked renderer executable contains GPL software; distributing it requires the applicable GPL notices and corresponding-source provisions, even though our renderer source is MIT. See the [GNU linking FAQ](https://www.gnu.org/licenses/gpl-faq.en.html#GPLStaticVsDynamic). |
| [VICE](https://vice-emu.sourceforge.io/), VICE contributors | 3.9; [pinned official release and headless build](docs/setup/vice-startup-investigation.md#choose-the-headless-build-correctly) | GPL-2.0-or-later for VICE, with its `COPYING`, contributor notices and separately licensed components. Commodore ROMs have separate copyright notices in VICE's README and are not covered by either VICE's GPL grant or this project's MIT grant. Runtime ROMs come from a separately installed package. |
| [py65](https://pypi.org/project/py65/1.2.0/) | 1.2.0; independent CPU test oracle in `.tools/test-deps/` | BSD-3-Clause; `Copyright (c) 2008-2024, Mike Naberezny and contributors. All rights reserved.` The installed distribution retains `py65-1.2.0.dist-info/LICENSE.txt`. |
| [Mido](https://pypi.org/project/mido/1.3.3/) | 1.3.3; optional MIDI importer dependency in `.tools/arrangement-deps/` | MIT; `Copyright (c) Ole Martin Bjørndalen`. The installed distribution retains `mido-1.3.3.dist-info/LICENSE`. |
| [packaging](https://pypi.org/project/packaging/24.2/) | 24.2; Mido dependency in `.tools/arrangement-deps/` | Apache-2.0 OR BSD-2-Clause, as stated in the installed `LICENSE`. Keep `LICENSE`, `LICENSE.APACHE` and `LICENSE.BSD`; the BSD notice credits Donald Stufft and individual contributors. |

The native tool archives and fingerprints are declared in [setup-sidwizard.py](scripts/setup-sidwizard.py); reference/skill revisions and file hashes are declared in [local-assets.json](config/local-assets.json). Keep those pins and the upstream notices together when restoring tools.

The SID-Wizard 1.97 `native/README.txt` declaration is reproduced verbatim:

```text
;License: You know I'm not into licensing and legal stuff but for the sake of completeness
;let's declare SID-Wizard as a WTF-licensed tool, so you can do WTF you want with it.

; 2026 Hermit Software Hungary  - contact:   by Personal Message at CSDb
```

The headless VICE build additionally uses locally installed pkgconf 3.0.8, dos2unix 7.5.7 and xa 2.4.1. Their versions and bottle hashes are recorded in the [build guide](docs/setup/vice-startup-investigation.md#build-dependencies-and-pins). Keep their own `COPYING` files: pkgconf carries the pkgconf authors' permissive notice; dos2unix calls its terms a FreeBSD-style license; xa supplies GPL v2. System tools and the [branding export tools](assets/branding/README.md) are separately installed prerequisites, not bundled project assets.

## Downloaded instruction sets

| Skill source | Pin and local installation | License status |
| --- | --- | --- |
| [sunsided/c64-skills](https://github.com/sunsided/c64-skills/tree/480b253b147655fa6ff6eb74577d1a2523d512d4) | Commit `480b253b147655fa6ff6eb74577d1a2523d512d4`; selected SID instructions and references installed into ignored `skills/c64-sid/` | No top-level license was established at this revision. Bundled historical manual extracts can carry separate rights. Local installation and public availability do not establish permission to redistribute them; they are outside the MIT grant. |
| [c64bridge `sid-music`](https://github.com/chrisgleissner/c64bridge/tree/0781a7b6cfe7b92bbb6d68e048ad396bd3edfb18/.github/skills/sid-music) | Optional installation into ignored `skills/sid-music/`; same pinned revision as c64bridge above | Retains the upstream GPL v2 `LICENSE`. See the c64bridge declarations above. |

The tracked `.agents/skills/` entries, and the `.claude/skills` link to that directory, are activation symlinks; downloaded bodies remain local. [Skill provenance and corrections](skills/README.md) describe the installation contract and its rights limits.

## Optional audio-model research

Normal setup, song builds and validation do not require these models or ML packages. They are outside the MIT grant and are not installed by the normal asset installer. The [setup receipt](evidence/audio-assessment-songbench/setup.json) records source revisions, checkpoints, hashes and the isolated environment's package versions; the [local setup guide](docs/setup/local-setup.md#optional-local-audio-models) explains the opt-in boundary.

| Component | Recorded source and terms |
| --- | --- |
| [Tencent SongBench](https://github.com/Tencent/SongBench/tree/9361b55ebff3fffcefbbc9a4653936ae6789c3c8) | Commit `9361b55ebff3fffcefbbc9a4653936ae6789c3c8`; `Copyright (C) 2026 Tencent. All rights reserved.` Its custom `LICENSE.txt` permits academic use only and excludes commercial or production use. Keep its copyright and permission notice with copies. It is not the MIT license despite similar opening wording. |
| MuQ code and [MuQ-large-msd-iter weights](https://huggingface.co/OpenMuQ/MuQ-large-msd-iter/tree/0562a57814f6f8bbd9fdea0a25921a2fce1a841a) | The trial uses Python package `muq==0.1.0` and weight revision `0562a57814f6f8bbd9fdea0a25921a2fce1a841a`. The package distinguishes MIT-licensed code from CC BY-NC 4.0 model weights. The code license does not relicense the weights. |

Other packages in that isolated optional environment retain their individual upstream licenses. Hosted model responses and service access are governed separately by their provider terms; a recorded response does not grant rights to its musical input.
