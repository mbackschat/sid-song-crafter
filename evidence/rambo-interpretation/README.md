# Rambo interpretation evidence

These records support the [complete palette interpretation](../../songs/studies/rambo-interpretation/README.md), verified on 2026-10-15. They establish source-note/timing identity, independent compiled execution and measured audio properties. The receipts predate listening; [subsequent feedback](../../songs/studies/rambo-interpretation/listening-review.json) is inconclusive and redirects the work toward stereo with the faithful palette. The score and music-derived records retain Martin Galway's [GPLv3 terms](../../samples/rambo-loader/LICENSE), attribution and [source provenance](../../samples/rambo-loader/README.md); they are not MIT relicensing of his music. Our palette changes and preservation rules are documented in the owning case.

| Question | Retained evidence |
| --- | --- |
| What exactly was generated? | [Candidate description](candidate.json), [recipe run and fingerprints](run.json), [local audition file hashes](listening-sources.json) |
| Are source notes, timing and important gestures preserved? | [Invariants and four negative controls](score-invariants.json), [complete normalized event ledger](score-events.json.gz) |
| Does the compiled player execute the model? | [CPU verification](cpu/build.json), [audit](cpu/audit.json), [ordered writes](cpu/writes.json.gz), [state checkpoints](cpu/state-checkpoints.json.gz) |
| Does independent VICE execution agree? | [Complete check](vice/study.json), [trace](vice/trace.json.gz), [command](vice/command.json) |
| Are renders healthy and the closing passage present? | [Audio health](audio.json), [role contribution and pre-clear decay](contribution.json) |
| What did the listening comparisons contain? | [Window selection](windows.json), [phrase gains and measurements](phrase-comparison.json), [ending gains and measurements](ending-comparison.json) |

No SID binary or audio is stored in this evidence group. Reproduce those with the [case recipe](../../config/listening/rambo-interpretation.json); the separate original reference is downloaded by fingerprint. The compressed records are lossless Git LFS objects. Verify their stored and original bytes with `python3 scripts/evidence.py verify --group rambo-interpretation`; restore using the [evidence workflow](../../docs/workflows/build-cache.md). Paths inside historical receipts describe the measured local run, not public downloads.
