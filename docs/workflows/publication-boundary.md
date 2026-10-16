# Public repository boundary

This guide owns the publication policy for samples, reference material and generated music. The [contributor guide](../../CLAUDE.md#public-repository-boundary) keeps only its standing summary.

Original project work is licensed under [MIT](../../LICENSE). Preserve the separate terms and attribution recorded in [third-party notices](../../THIRD_PARTY_NOTICES.md); the project license does not relicense upstream code, player binaries or musical sources.

## Two-tier sample packages

Every sample song must have a public, reusable package under this two-tier policy:

- **Always include:** our tools and reusable instruments, recipes without embedded notes, source references and hashes. Link shared tools and instruments instead of duplicating them. This requirement covers every worked-on sample, including copyrighted songs and rejected experiments; preserve each sample's actual musical verdict and scope. Only include material we have the right to share; a recovered third-party program is not automatically ours.
- **Additionally, only for original, public-domain or appropriately licensed music:** include the complete score and SWM (SWS for two chips) plus a pinned export manifest, and provide playable SID/PRG files and WAV recordings, provided the particular source arrangement or edition and included player code also permit distribution. This native format applies to SID-Wizard songs; other backends retain their equivalent editable source and export metadata without claiming an SWM exists. Follow [the native source contract](native-song-workflow.md#frozen-release-source-and-publication).

Check the [game-music permission review](../research/game-music-permissions.md) before classifying historical songs. A title-specific licence can permit a separately licensed sample alongside MIT tools; do not require every song to be MIT or public domain. The GPLv3 Rambo loader grant is scoped to the released loader, not its entire multi-subtune reference archive.

## Before staging a package

Record the composition and source-arrangement rights basis in its owning documentation, select the applicable tier and inspect the proposed files for embedded note sequences or equivalent encoded score data. Unknown rights use the always-included tier. Keep uncleared complete scores, native modules and generated song binaries/audio local under ignored output. Public URLs, attribution, hashes, file extensions and deterministic generation do not establish publication permission.

Retain reviewed, distributable SID/PRG/WAV samples in [samples](../../samples/README.md), with source and output hashes, reproduction instructions and applicable notices. Use explicit `.gitignore` exceptions for those SID files; do not force-add reference binaries. The restriction on uncleared material must not be extended to rights-cleared project samples. This is a publication requirement, not a claim that all historical samples have already been audited or packaged. Legacy tracked reconstructions, including `songs/flashdance-decoded.json` and `songs/shades-score.json`, contain musical note data and need a rights review before further publication; the policy change alone does not clear them.

## Reference binaries and audio

Keep original reference SID binaries out of the public repository, including history and LFS. Record each source URL and SHA-256 fingerprint in [the asset registry](../../config/local-assets.json); use [the verified downloader](../../scripts/setup-project.py) on demand. Keep reference WAVs out of Git under ignored `.local/` or `build/`; document exact reproduction commands, source hashes, subtune, renderer/version/settings, duration, gain, trim points and output hashes.

Analysis artifacts, traces, lookup tables, editable descriptions and reusable code may be tracked when useful. Preserve complete evidence alongside concise prose, with source hashes, settings and reproduction commands. Downloaded skills retain the ignored `skills/<name>/` installation layout. Never force-add original SID files; check tracked files and history before publishing.
