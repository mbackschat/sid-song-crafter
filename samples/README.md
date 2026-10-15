# Playable samples

Download the SID for a SID player, the PRG for a C64 or emulator, or the WAV for an ordinary audio player. All samples target one SID at `$D400`, PAL, with one player call per video frame. Bach and the instrument mix use MOS8580 and editable SID-Wizard SWM files; Rambo uses MOS6581 and an editable JSON score with a custom player. WAVs retain the original renderer level, including their release and ending silence: 44.1 kHz, mono PCM16, with no normalization or trimming.

| Sample | Playable downloads | Editable source and provenance |
| --- | --- | --- |
| **Toccata from BWV 565** — accepted complete mono interpretation; 88.123 seconds including release | [SID](bach-toccata/bach-toccata.sid) (8,898 bytes) · [PRG](bach-toccata/bach-toccata.prg) (9,770 bytes) · [WAV](bach-toccata/bach-toccata.wav) (7,772,486 bytes) | [SWM](bach-toccata/bach-toccata.swm) (5,964 bytes) · [Manifest](bach-toccata/manifest.json) · [Score, arrangement and instruments](../songs/studies/bach-toccata-full/README.md) |
| **Original instrument mix** — three-voice phrase; initial mix-level acceptance; 10 seconds including release | [SID](instrument-mix/instrument-mix.sid) (3,365 bytes) · [PRG](instrument-mix/instrument-mix.prg) (4,237 bytes) · [WAV](instrument-mix/instrument-mix.wav) (882,044 bytes) | [SWM](instrument-mix/instrument-mix.swm) (511 bytes) · [Manifest](instrument-mix/manifest.json) · [Complete original phrase and patches](../songs/studies/sidwizard-repertoire/repertoire.json) |
| **Rambo loader** — faithful reconstruction; accepted phrase and ending; 225 seconds | [SID](rambo-loader/rambo-loader.sid) (6,451 bytes) · [WAV](rambo-loader/rambo-loader.wav) (19,845,044 bytes) | [Editable score and build instructions](rambo-loader/README.md) · [Manifest](rambo-loader/manifest.json) · [GPLv3](rambo-loader/LICENSE) |

The Bach arrangement covers the Toccata through measure 30 beats 1–2 and ends before the Fugue. Its source is Anonymous's public-domain [Mutopia 1780](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1780) typesetting of the Bach-Gesellschaft Ausgabe, 1867; the unchanged [LilyPond declaration](../songs/studies/bach-toccata-opening/source/ToccataFugue.ly) and [MIDI](../songs/studies/bach-toccata-opening/source/ToccataFugue.mid) remain in the source bundle. The original instrument mix uses project-authored notes and patches. Project contributions use [MIT](../LICENSE); the underlying public-domain music retains that status.

The Bach and instrument-mix SID and PRG files embed Hermit Software / Mihaly Horvath's SID-Wizard player, whose separate declaration is retained in [third-party notices](../THIRD_PARTY_NOTICES.md#build-playback-and-validation-components):

```text
;License: You know I'm not into licensing and legal stuff but for the sake of completeness
;let's declare SID-Wizard as a WTF-licensed tool, so you can do WTF you want with it.

; 2026 Hermit Software Hungary  - contact:   by Personal Message at CSDb
```

These packages contain no third-party reference SID or performance recording. Their manifests record the exact copied files, SHA-256 hashes, pinned exporter/player/toolchain, source inputs, rendering settings, rights basis and scoped listening verdicts. The Bach WAV matches the accepted complete mono file; the mix WAV matches its retained trial receipt. Fresh exports of both SWMs reproduced the bundled SID and PRG bytes. Packaging reused the existing WAVs.

The [Rambo loader package](rambo-loader/README.md) is separately GPLv3-licensed, with Galway’s attribution and complete corresponding source. Its accepted reconstruction is distinct from the newly requested creative interpretation, whose listening verdict is pending.

## Play and reproduce

Open a SID in a PAL player using the chip model listed above, or load an available PRG in a PAL C64 emulator and run it. On macOS, `afplay samples/bach-toccata/bach-toccata.wav` plays the audio preview. See the [playback guide](../docs/workflows/native-song-workflow.md) for the native workflow.

From the repository root, [set up the pinned exporter](../docs/research/tools/sid-wizard-trial.md) with `python3 scripts/setup-sidwizard.py`. Export either frozen SWM into a fresh directory:

```sh
python3 scripts/export-sidwizard.py samples/bach-toccata/bach-toccata.swm --output-dir build/public-samples-reexport/bach-toccata --title 'Bach Toccata: full SID hybrid' --author 'Original SID arrangement' --released 2026 --clock pal --sid-model MOS8580
python3 scripts/export-sidwizard.py samples/instrument-mix/instrument-mix.swm --output-dir build/public-samples-reexport/instrument-mix --title mix-candidate --author 'Original SID study' --released 2026 --clock pal --sid-model MOS8580
```

The output stems match the bundled SWM names. The manifests supply exact render commands and authoring commands for rebuilding from the retained score or original phrase; [renderer setup](../docs/workflows/audio-workflow.md) is separate. Expected SID/PRG hashes are exact; reproducing WAV bytes also depends on the recorded renderer/library build. Original scores and recipes stay in their owning song directories rather than being duplicated here.
