# Rambo stereo evidence

These records support the [faithful three-part stereo treatment](../../songs/studies/rambo-stereo/README.md), verified on 2026-10-15. The same source score and instrument programs run on two MOS6581 chips: voices 1 and 3 remain together, and the independent bass moves to the second chip. The [listener correction](../../songs/studies/rambo-stereo/listening-review.json) identifies a scope mismatch: redistribution alone did not fulfill the requested expanded arrangement. Retain this as a routing diagnostic, not an accepted interpretation. Music-derived records retain Martin Galway's [GPL v3 terms](../../samples/rambo-loader/LICENSE) and [source attribution](../../samples/rambo-loader/README.md).

| Question | Evidence |
| --- | --- |
| Which score and faithful reference were used? | [Score fingerprint](source.json), [faithful SID fingerprint](faithful.json) |
| What executed, and what was reused? | [Fresh run](first-run.json), [cached repeat](run.json), [focused regression results](focused-guards.log) |
| Does the compiled routing preserve the source behavior? | [CPU/state verification](cpu/build.json), [cycle audit](cpu/audit.json), [all ordered writes](cpu/writes.json.gz), [state checkpoints](cpu/state-checkpoints.json.gz) |
| Does independent VICE playback agree? | [Complete verification](vice/study.json), [complete trace](vice/trace.json.gz), [command](vice/command.json) |
| Are both channels and the complete ending present? | [Audio health, channel levels, closing body and final decay](signal.json) |
| Which audio was supplied for review? | [Local file hashes](listening-sources.json), [phrase matching](phrase-comparison.json), [ending matching](ending-comparison.json) |

No SID binary or audio is embedded here. The [recipe](../../config/listening/rambo-stereo.json) recreates both from tracked sources without downloading an original SID. Compressed records are lossless Git LFS objects; `python3 scripts/evidence.py verify --group rambo-stereo` verifies stored and original hashes. Follow the [evidence workflow](../../docs/workflows/build-cache.md) to restore them. Historical receipt paths identify the measured run, not public downloads. Technical checks do not establish a preferred stereo presentation, hardware equivalence or a six-part arrangement.
