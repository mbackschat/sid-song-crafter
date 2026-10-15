# Rambo expanded ensemble evidence

The [six-voice arrangement](../../songs/studies/rambo-ensemble/README.md) retains the faithful trio on SID A and adds source-derived support on SID B. Verified on 2026-10-15; human musical review remains pending. Music-derived score and note records retain Martin Galway's [GPLv3 loader terms and attribution](../../samples/rambo-loader/README.md). Reusable tools retain MIT separately.

| Question | Retained evidence |
| --- | --- |
| Which sources and added notes? | [Source pin](source.json), [faithful pin](faithful.json), [editable secondary score](preparation/secondary.json), [whole-span harmony and lifetime proof](preparation/arrangement-proof.json), [source observations](preparation/source-note-events.json.gz), [support ledger](preparation/support-note-events.json.gz) |
| Which execution and regression checks? | [Fresh run](first-run.json), [cached repeat](run.json), [arrangement/audio guards](ensemble-focused-guards.txt), [dual compiler guards](compiler-focused-guards.txt) |
| Does the complete dual export execute correctly? | [CPU proof](cpu/build.json), [cycle audit](cpu/audit.json), [all ordered writes](cpu/writes.json.gz), [selected state checkpoints](cpu/state-checkpoints.json.gz), [VICE proof](vice/study.json), [complete trace](vice/trace.json.gz), [VICE invocation](vice/command.json) |
| Does the presentation implement the intended mix? | [Mix receipt](presentation.json), [all-frame matrix check, role contributions and ending measurements](signal.json) |
| What was submitted for listening? | [Stable audition hashes](listening-sources.json), [phrase bounds and gains](phrase-comparison.json), [ending bounds and gains](ending-comparison.json) |

The fresh 18-stage recipe completed in 245.240 seconds; the unchanged repeat reused all stages in 0.913 seconds. These are execution timings, not total musical production effort. CPU and VICE agree on 106,400 ordered stores across 11,000 calls; named state matches at ten checkpoints. The maximum compiled call uses 7,995 of 19,656 cycles. Every one of 9,922,500 presentation frames matches the declared quantized matrix. No PCM rail samples were detected, and the complete original closing body remains present before the final quiet tail. Role omission residuals establish signal contribution, not audibility or improvement.

No SID or audio is embedded here. The [recipe](../../config/listening/rambo-ensemble.json) regenerates both from tracked sources. Verify these lossless archives with `python3 scripts/evidence.py verify --group rambo-ensemble`; follow the [evidence workflow](../../docs/workflows/build-cache.md) for restoration. Historical absolute paths identify the measured run, not portable download locations.
