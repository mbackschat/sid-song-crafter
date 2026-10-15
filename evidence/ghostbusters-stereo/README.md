# Ghostbusters initial native stereo evidence

This is the frozen initial held-support candidate for the [active stereo interpretation](../../songs/studies/ghostbusters-stereo/README.md). The [human record](../../songs/studies/ghostbusters-stereo/listening-review.json) rejects its persistent right-side phrase sound while accepting recognizable centered speech and intact complete continuation separately. No musical acceptance of the held support follows from the execution or signal checks. The active correction must preserve this submission.

| Question | Retained evidence |
| --- | --- |
| Which initial design and submission? | [Note-free arrangement](arrangement-initial.json), [listening recipe](listening-recipe-initial.json), [audition selection](audition-selection-initial.json), [submitted file hashes](listening-submission.json), [frozen scoped verdict](listening-review-initial.json) |
| Which source and baseline? | [Private source fingerprint](source-pin.json), [accepted mono fingerprint](accepted-mono-pin.json) |
| What actually executed? | [Allowlisted complete CPU/VICE/source proof](native-proof.json), [28 focused guards](focused-guards.txt), [48-second diagnostic proof](diagnostic/native-proof.json) |
| What was rendered and matched? | [Complete audio/gain/mono/continuation aggregates](audio.json), [diagnostic audio](diagnostic/audio.json), exact [opening](comparisons/opening.json), [phrase](comparisons/phrase.json) and [ending](comparisons/ending.json) A/B bounds and hashes |
| Does the added support contribute? | [Cycle-preserving one-byte gate-off control](support-control.json), [comparison bounds and hashes](comparisons/support-control.json), actual left equality and right difference in [audio checks](audio.json) |
| What was fresh or reused? | [Initial pre-review run](run-initial-pre-review.json), [corrected verified run](run-verified.json), [unchanged repeat](run-reused.json) |

The initial nine-stage run took 219.412 seconds. Its header hash described a normalized inspection image, and a guard input was undeclared; it also preceded the allowlisted public proof and causal control. Retain it only as historical provenance. The corrected run took 207.488 seconds, executing native proofs and the controlled render freshly while reusing both unchanged main renders and source/mono pins. The repeat took 0.768 seconds with all eleven stages reused. These measurements exclude implementation and listening.

The complete proof covers 14,389 music calls and 123,921 stores across both chips. CPU and actual NTSC VICE agree; NMI cost peaks at 85 of 102 cycles. The same-cycle support control leaves all left PCM and both channels before 15 seconds identical; right-channel AC difference in the 16–32-second phrase is 1,168.77 PCM units at the candidate's unchanged gain. This is a controlled whole-mix intervention, not an audio stem or evidence of musical usefulness.

## Exact stage dependency receipts

- [Source pin](stages/source-pin.json)
- [Accepted mono pin](stages/accepted-mono-pin.json)
- [Focused guards](stages/focused-guards.json)
- [48-second native execution](stages/diagnostic-native.json)
- [48-second main render](stages/diagnostic-render.json)
- [48-second listening preparation](stages/diagnostic-listening.json)
- [Complete native execution](stages/complete-native.json)
- [Complete main render](stages/complete-render.json)
- [Support control preparation](stages/support-control.json)
- [Support-disabled complete render](stages/support-control-render.json)
- [Complete listening preparation](stages/complete-listening.json)

All selected payloads were reviewed for source-note/checkpoint data, amplitude streams, native traces and executable/audio payloads. Retained JSON contains aggregate results, hashes, commands, settings and note-free selectors only. The complete private native `verification.json` contains source-bearing nested checkpoints and is deliberately excluded, along with composition, support ledger, SID/PRG, speech, raw logs, register snapshots and WAVs. The public projection binds its private original by hash; references to private filenames in receipts do not embed those files.

Run `python3 scripts/evidence.py verify --group ghostbusters-stereo` to verify the selection in [the manifest](../manifest.json). Historical tool fingerprints identify the measured source versions; later code must not be described as the same historical execution. Restore private assets and use the [case's reproduction instructions](../../songs/studies/ghostbusters-stereo/README.md#verification-and-reproduction) for a new local run. The manifest owns exact archive paths, sizes, hashes and retention reasons.
