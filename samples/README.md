# Sample library

Each sample has a package directory containing its README, reproducible build recipe, output/source fingerprints and applicable notices. Editable material already owned by a song or study stays there and is linked from its package, avoiding duplicate score and instrument definitions. Downloadable releases are kept beside their package materials; uncleared music is generated under ignored `build/`.

| Sample | Mono SID / WAV | Stereo SID / WAV | Materials and scope |
| --- | --- | --- | --- |
| Bach Toccata, about 1:28 | [SID](bach-toccata/bach-toccata.sid) · [WAV](bach-toccata/bach-toccata.wav) | [SID](bach-toccata/bach-toccata-stereo.sid) · [WAV](bach-toccata/bach-toccata-stereo.wav) | [Package](bach-toccata/README.md): accepted complete mono and stereo Toccata |
| Original instrument mix, 10 seconds | [SID](instrument-mix/instrument-mix.sid) · [WAV](instrument-mix/instrument-mix.wav) | [SID](instrument-mix/instrument-mix-stereo.sid) · [WAV](instrument-mix/instrument-mix-stereo.wav) | [Package](instrument-mix/README.md): initial mono mix-level acceptance; stereo placement and balance accepted |
| Rambo loader, main music through ending, about 3:13 | [Faithful SID](rambo-loader/rambo-loader-main.sid) · [WAV](rambo-loader/rambo-loader-main.wav) | [Centered-lead SID](rambo-stereo/rambo-stereo-main.sid) · [WAV](rambo-stereo/rambo-stereo-main.wav) | [Mono package](rambo-loader/README.md) · [Accepted stereo arrangement](rambo-stereo/README.md); both demos omit the intro |
| Moon River, first statement, about 1:39 | Local SID/WAV build | Local two-SID/WAV build | [Package and recipe](moon-river/README.md): accepted restrained mono first statement; stereo placement and balance accepted |
| Pink Panther, complete arrangement, about 3:20 | Local SID/WAV build | Local two-SID/WAV build | [Package and recipe](pink-panther/README.md): accepted complete mono arrangement; stereo placement and balance accepted |

## Playback and stereo placement

All samples use PAL timing, one player call per frame. Bach, instrument mix, Moon River and Pink Panther use MOS8580; Rambo uses MOS6581. Mono uses `$D400`. Stereo uses two chips at `$D400` and `$D420`, routed left and right respectively. Use a PSID v3/two-SID-compatible player for stereo SID files. WAVs are rendered directly from their corresponding SID at 44.1 kHz PCM16, unity gain, without normalization. The stereo channels contain different accompaniment; they are not copies of mono audio.

The four new SID-Wizard stereo presentations duplicate the first voice for a centered lead and place the second and third original voices on opposite sides, preserving physical oscillator indices, original notes and instruments. They do not add musical parts. Their package notes record filter ownership, CPU/VICE checks, fold-down and listening status. Bach stereo and the trimmed Rambo stereo release were accepted on 2026-10-16; Pink Panther, Moon River and the instrument mix stereo placement/balance were subsequently accepted the same day. Rambo retains its already accepted centered lead and source-derived chord expansion. Register agreement does not establish oscillator phase coherence on physical chips or musical acceptance.

## Rambo entrance

Both featured Rambo SID/WAV files begin at original play call 1,586 (31.641167 seconds); the lead enters on the next frame. The omitted introduction is disliked in the original tune itself. The new entry preserves the computed score and sound state, all subsequent ordered play writes and the original ending. SID envelopes and oscillators start fresh; the WAV is rendered from the new SID, not cropped from an earlier recording. Full mono/stereo versions and their historical manifests remain unchanged in their packages, clearly labelled as complete versions with the intro. The old 32–64-second stereo preview is retained as historical material.

## Reproduce and review

Follow [local setup](../docs/setup/local-setup.md), including the renderer and headless VICE. The native stereo packages need `python3 scripts/setup-sidwizard.py --sid-count 2`. Run the owning recipe from the repository root:

```sh
python3 scripts/listening-package.py samples/bach-toccata/stereo.recipe.json --output build/sample-bach-toccata-stereo
python3 scripts/listening-package.py samples/instrument-mix/stereo.recipe.json --output build/sample-instrument-mix-stereo
python3 scripts/listening-package.py samples/rambo-loader/main.recipe.json --output build/sample-rambo-loader-main
python3 scripts/listening-package.py samples/rambo-stereo/main.recipe.json --output build/sample-rambo-stereo-main
```

[Moon River](moon-river/README.md) and [Pink Panther](pink-panther/README.md) include their source-download and dual-format build commands. Each generated `listening.md` points to the playable files and verification. Existing successful stages are reused only when input/output fingerprints match. Original mono references remain linked alongside new stereo candidates; musical preference is a separate listening decision.

## Rights and source preservation

Bach uses the public-domain composition and Anonymous's public-domain Mutopia 1780 typesetting of the Bach-Gesellschaft edition; the [unchanged source declaration](../songs/studies/bach-toccata-opening/source/ToccataFugue.ly), [MIDI](../songs/studies/bach-toccata-opening/source/ToccataFugue.mid) and [manifest](bach-toccata/manifest.json) retain provenance. The instrument mix has project-authored notes and patches. Project contributions use [MIT](../LICENSE); embedded SID-Wizard player code retains its [separate upstream declaration](../THIRD_PARTY_NOTICES.md#build-playback-and-validation-components).

The Rambo loader and derived stereo arrangement are separately [GPLv3 licensed](rambo-loader/LICENSE), with Martin Galway attribution and corresponding source linked in each package. That grant is specific to the loader. No original reference SID or third-party performance recording is bundled.

Moon River and Pink Panther use the always-included materials tier under the [publication policy](../docs/workflows/publication-boundary.md). Their recipes, source references, tool links and verification hashes are public; source MIDI, generated notes/modules and SID/WAV files remain local while redistribution permissions are unresolved.
