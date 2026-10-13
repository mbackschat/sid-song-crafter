# Canonical study evidence

This directory retains the complete analysis records behind selected findings. Compressed records use Git LFS; [the manifest](manifest.json), receipts and explanatory source snapshots use ordinary Git. Original reference SIDs, reference WAVs and executable payload dumps are excluded. Source URLs and SHA-256 fingerprints belong to [the download registry](../config/local-assets.json).

Use [the archive and cache workflow](../docs/workflows/build-cache.md) to install LFS, fetch objects, verify both compressed and uncompressed hashes, and restore exact bytes to their historical `build/` paths. The archive remains intact during restoration. `build/` remains ignored and contains additional local listening material, diagnostic runs and replaceable exports.

## Find the owning interpretation

| Evidence | Interpretation and reproduction |
| --- | --- |
| Shades CIA timing, form, modulation and semantic model | [Shades study](../docs/research/composition/shades-preparation.md), [CIA validation](../docs/validation/cia-tracing.md) |
| Flashdance reconstruction, transfer and accepted stereo arrangement | [Flashdance study](../docs/research/composition/flashdance-preparation.md) |
| Cybernoid II intake, execution, order traversals and opening mechanisms | [Cybernoid II preparation](../docs/research/composition/cybernoid-ii-preparation.md) |
| Cybernoid II full-title mechanism census and reusable arithmetic | [Executed coverage](../docs/research/composition/cybernoid-ii-preparation.md#full-title-mechanism-coverage), [PWM/filter components](../docs/research/composition/cybernoid-ii-preparation.md#reusable-pwm-and-filter-arithmetic) |
| Cybernoid II independent score and pitch models | [Contextual score expansion](../docs/research/composition/cybernoid-ii-preparation.md#independent-title-score-expansion), [named-state vibrato/glide](../docs/research/composition/cybernoid-ii-preparation.md#named-state-vibrato-and-glide-component) |
| Cybernoid II actual-title pitch comparison and output helpers | [Full-title pitch proof](../docs/research/composition/cybernoid-ii-preparation.md#full-title-contextual-pitch-verification), [arpeggio/waveform/output contract](../docs/research/composition/cybernoid-ii-preparation.md#arpeggio-waveform-and-output-components) |
| Cybernoid II note setup, retained state, gate and filter fallback | [Caller primitives](../docs/research/composition/cybernoid-ii-preparation.md#note-setup-gate-and-filter-owner-caller) |
| Cybernoid II cold initialization, editable data and complete numeric composition | [Source-free model and full-span register proof](../docs/research/composition/cybernoid-ii-preparation.md#compose-the-complete-title-from-editable-data) |
| Monty and Rambo archive intake, subtune attribution and bounded CPU execution | [Monty preparation](../docs/research/composition/monty-preparation.md), [Rambo preparation](../docs/research/composition/rambo-preparation.md) |
| Monty complete order traversals, navigation and first-wrap VICE proof | [Executed navigation and recurrence limits](../docs/research/composition/monty-preparation.md#executed-score-navigation) |
| Ghouls ’n Ghosts and Deflektor source intake and current audit limitations | [Ghouls preparation](../docs/research/composition/ghouls-preparation.md), [Deflektor preparation](../docs/research/composition/deflektor-preparation.md) |
| Ghouls canonical SID write-window correction, frozen rejection and 64-call CPU/VICE proof | [Bounded execution and reproduction](../docs/research/composition/ghouls-preparation.md#callable-admission-and-execution-boundary), [shared write-window contract](../docs/validation/psid-audit.md#canonical-sid-write-windows) |
| Deflektor high-RAM execution, unchanged source and shared-host regressions | [Deflektor CPU/VICE proof](../docs/research/composition/deflektor-preparation.md#bounded-cpu-and-vice-verification), [host placement and return sites](../docs/validation/psid-audit.md#place-the-host-around-a-high-ram-reference) |
| Take On Me, Billie Jean, Airwolf and Ghostbusters pinned intake | [Source attribution, bounded execution and remaining contracts](../docs/research/composition/pop-theme-preparation.md) |
| CPU timing correction | [Opcode timing finding](../docs/validation/cpu-timing.md) |

The manifest identifies every retained file, its original location, byte counts, hashes and retention reason. Historical receipts are preserved byte-for-byte: their old paths, machine paths and source hashes describe the original experiment. Its top-level implementation checkpoint belongs to the historical Shades semantic proof; later records carry their own hashes or companion checkpoints. Restoring evidence does not install tools, retrieve reference music or rerun an experiment. Follow the owning study for those steps, and distinguish exact proof-version snapshots from later working code. Earlier CPU traces may use the superseded `$CE` cost; the timing correction explains the boundary.

The 2026-10-13 selection preserves the study groups indexed above. The manifest owns file counts and byte sizes. Earlier DRAX/Elise experiments, redundant process logs and superseded traces remain local. A score receipt may also index unselected local diagnostics; the manifest, rather than every historical receipt reference, defines this archive's contents.

Register/state equality is execution evidence, not a musical verdict. Listening judgments remain in the owning studies, tied to the named local audio and reproduction settings. No new listening approval follows from archiving a record.

## Retention and backup

Preserve this manifest and the corresponding LFS objects together. A pointer-only clone or Git bundle cannot recover the compressed records. Upload to an LFS-capable remote or keep a separate off-machine backup before treating the archive as protected against loss of this computer. Keep immutable checkpoints when their byte identities underpin a finding; omit duplicated process logs and superseded scratch runs from canonical retention.
