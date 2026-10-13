# Canonical study evidence

This directory retains the complete analysis records behind selected findings. Compressed records use Git LFS; [the manifest](manifest.json), receipts and explanatory source snapshots use ordinary Git. Original reference SIDs, reference WAVs and executable payload dumps are excluded. Source URLs and SHA-256 fingerprints belong to [the download registry](../config/local-assets.json).

Use [the archive and cache workflow](../docs/workflows/build-cache.md) to install LFS, fetch objects, verify both compressed and uncompressed hashes, and restore exact bytes to their historical `build/` paths. The archive remains intact during restoration. `build/` remains ignored and contains additional local listening material, diagnostic runs and replaceable exports.

## Find the owning interpretation

| Evidence | Interpretation and reproduction |
| --- | --- |
| Shades CIA timing, form, modulation and semantic model | [Shades study](../docs/research/composition/shades-preparation.md), [CIA validation](../docs/validation/cia-tracing.md) |
| Flashdance reconstruction, transfer and accepted stereo arrangement | [Flashdance study](../docs/research/composition/flashdance-preparation.md) |
| Cybernoid II source intake, selected-subtune CPU/VICE execution and reference recipe | [Cybernoid II preparation](../docs/research/composition/cybernoid-ii-preparation.md) |
| CPU timing correction | [Opcode timing finding](../docs/validation/cpu-timing.md) |

The manifest identifies every retained file, its original location, byte counts, hashes and retention reason. Historical receipts are preserved byte-for-byte: their old paths, machine paths and source hashes describe the original experiment. Restoring evidence does not install tools, retrieve reference music or rerun an experiment. Follow the owning study for those steps, and distinguish exact proof-version snapshots from later working code. Earlier CPU traces may use the superseded `$CE` cost; the timing correction explains the boundary.

The 2026-10-13 selection preserves canonical Shades/Flashdance proofs, including complete independent Shades and original-transfer CPU/CIA traces, audio measurements and the subsequent bounded Cybernoid II intake, both subtunes’ executed stores and the title’s opening instruction trace. The manifest owns file counts and byte sizes. Earlier DRAX/Elise experiments, redundant process logs and superseded traces remain local. A score receipt may also index unselected local diagnostics; the manifest, rather than every historical receipt reference, defines this archive's contents.

Register/state equality is execution evidence, not a musical verdict. Listening judgments remain in the owning studies, tied to the named local audio and reproduction settings. No new listening approval follows from archiving a record.

## Retention and backup

Preserve this manifest and the corresponding LFS objects together. A pointer-only clone or Git bundle cannot recover the compressed records. Upload to an LFS-capable remote or keep a separate off-machine backup before treating the archive as protected against loss of this computer. Keep immutable checkpoints when their byte identities underpin a finding; omit duplicated process logs and superseded scratch runs from canonical retention.
