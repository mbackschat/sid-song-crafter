# Normalized sample catalog

Crafter owns the curated, publication-scoped sample index consumed by [SID Song Explorer](https://github.com/mbackschat/sid-song-explorer). The [curator input](../../samples/catalog/curator.json) owns selected entries, order, descriptions, target declarations, rights and scoped listening/analysis records. [The generated index](../../samples/catalog/index.json) adds asset SHA-256, byte counts and the analysis SID fingerprint from one pinned Crafter source commit. Neither file establishes new musical acceptance or redistribution rights; the [publication boundary](publication-boundary.md) and linked package owners remain authoritative.

## Generate and check

Run from the Crafter checkout with Python 3 and Git; no Explorer checkout, runtime, renderer or downloaded dependency is required:

```sh
python3 scripts/catalog.py generate
python3 scripts/catalog.py check
python3 -m unittest discover -s tests -p catalog_test.py -v
```

The [producer and validator](../../scripts/catalog.py) also accept `--input PATH --output PATH`. `generate` writes deterministic UTF-8 JSON with a trailing newline. `check` validates the output, regenerates it in memory from the curator input and fails if the bytes differ; it does not rewrite files. The source commit must already exist locally, so a shallow producer checkout may need an explicit fetch of that commit first. All Git reads use argument arrays with ten-second deadlines; generation does not access the network or inspect mutable working-tree assets.

`source.repository` is the Crafter GitHub repository and `source.revision` is a full commit ID owning every asset and evidence link. This asset/evidence pin is independent of the later commit publishing the producer and index, avoiding a self-referential commit hash. Explorer pins that later producer/index revision and its index digest separately. Runtime asset and owner URLs derive from the source repository, revision and paths; corresponding source derives from `https://github.com/mbackschat/sid-song-crafter/archive/<source.revision>.tar.gz`.

## Version 1 contract

The index is an object containing only `schemaVersion: 1`, `source`, `entries` and `materials`. Unknown fields at every defined object boundary, duplicate JSON keys and unsupported versions fail validation. The curator input has the same contract except that each asset omits `sha256` and `bytes`, and analysis omits `sidSha256`; generation fills those identities from the pinned Git blobs. JSON input is bounded to 2 MiB. Source assets are bounded to 256 MiB each.

Each playable entry has a unique `id`, `title`, `description`, positive finite `durationSeconds`, `publication: "cleared"`, `files`, `target`, `rights`, `listening` and `analysis`. `files.sid` and `files.license` are required; `files.reference` and `files.notices` are optional. Exactly one of `files.reference` and `externalReference` is required. Optional `stereo` contains both `sid` and `reference` assets. Entry/material IDs share one namespace; annotation IDs are unique within each entry.

Each asset contains `path`, `sha256`, positive integer `bytes`, `filename`, `transport` and `delivery`. Asset paths are repository-relative without fragments, URL syntax, empty components or traversal; output filenames are plain basenames beginning with an ASCII letter or digit. `transport` is `raw` or `media`, and `delivery` is `prepared` or `link-only`. Every `files` value uses `prepared`; `externalReference` and both `stereo` assets use `link-only`. Prepared filenames are globally unique, and prepared assets respect Explorer's 25 MiB per-file limit. Links can exceed that preparation limit. Repeated path/filename aliases must agree on source path, hash, bytes and transport; the same bytes can therefore be linked and prepared independently.

Generation reads regular ordinary Git blobs and rejects symlinks and unresolved Git LFS pointers. The current source pin contains ordinary blobs only, so generation requires `transport: "raw"` and preserves their existing raw asset URLs. `media` is a reserved consumer transport; producing it requires a future materialized and verified LFS source route rather than publishing pointer bytes as music.

`target` declares `clock`, `model`, `sidCount`, `baseAddress`, `subtune` and `routing`, plus `secondSidAddress` for two chips. Generation checks the selected and linked stereo PSID headers against chip count/address, clock, model and subtune declarations. Version 1 retains the current player target: PAL, MOS6581 or MOS8580, base address 54272 and subtune 1. One chip requires `routing: "mono"` and no second address. Two chips require address 54304 and `routing: "sid-a-left-sid-b-right"`.

`rights` contains nonempty `license` and `attribution`, plus `sourcePath` and `licensePath`; the license path must match the prepared license asset. `listening` contains nonempty `status` and `scope`, plus `sourcePath`. Owner paths are repository-relative and may carry a Markdown heading fragment. Generation verifies the pinned file and fragment, and checks matching asset fingerprints recorded in JSON listening manifests. Rights and listening prose retain their package-specific scope.

`analysis` contains `schemaVersion: 1`, `sidSha256`, `subtune`, `clock`, `timeBasis: "seconds-from-init"` and `annotations`. Its SID hash, clock and subtune must match the selected SID/target. Each annotation contains `id`, `startSeconds`, `endSeconds`, `title`, `description`, `evidenceLevel`, `voices` and `sourcePath`. Spans are finite, positive-length and within the entry duration; physical voices are unique integers 1–3 or 1–6 according to chip count. Evidence levels are `verified`, `derived` or `interpretation`; they remain separate from listening acceptance and runtime observations.

Each materials item contains only `id`, `title`, `description`, `sourcePath` and `publication: "materials-only"`. It exposes the owning package without playable file fields. The initial catalog preserves Explorer's six playable entries, four materials items, 21 prepared files and three annotations; it imports no additional musical material.

The separate [Rambo composition package](composition-package.md) exports selected score/program relationships without adding fields to this version 1 index.

## Verification scope

The focused suite checks deterministic output, the migration identities/order, independent SHA-256 and byte counts from pinned Git reads, duplicate/unknown fields, unsafe paths, publication/delivery, aliases, target/analysis identity and PSID metadata, annotation spans/voices, owner fragments, manifest mismatches and rejected LFS/symlink sources. These are publication-data and software guards, separate from source rights decisions, rendered audio, browser playback and human listening.
