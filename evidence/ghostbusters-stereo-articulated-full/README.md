# Complete articulated Ghostbusters stereo evidence

The [accepted articulated phrase](../../songs/studies/ghostbusters-stereo/articulated-listening-review.json) is preserved in this technically verified complete 245-second render. The [complete-performance verdict](../../songs/studies/ghostbusters-stereo/articulated-full-listening-review.json) is qualified positive, with a right-side timbre revision active. Initial speech and continuation verdicts retain their separate scopes; no complete musical acceptance follows from these records.

| Question | Retained evidence |
| --- | --- |
| Which complete run and settings? | [Fresh nine-stage run](run-executed.json), [full recipe](recipe.json), [audition selection](audition-selection.json), unchanged [articulated arrangement](../ghostbusters-stereo-articulated/arrangement.json) |
| What executes? | [Allowlisted complete CPU/VICE/source proof](native-proof.json): 14,389 calls, 124,388 ordered stores across A/B, 45,410 non-nested NMIs, peak 85/102 cycles and zero SID reads |
| Do all releases settle? | [Every prefix's own pattern-boundary check](release.json), [final complete-scope admission](final-release-verification.json), [same-cycle gate-off intervention](support-control.json), [six final guard results](release-guards-final.txt) |
| Are the accepted phrase and continuation preserved? | [Exact accepted-phrase file identity](accepted-phrase-identity.json), [full signal/continuation checks](audio.json), [ending A/B bounds and hashes](ending-comparison.json) |
| Which files were submitted? | [Stable full reference/candidate and ending hashes](listening-submission.json) |

All 64 support prefixes have measured attack/body/declining release and zero contribution in each checked late-gap window before their own `startCall+128` source-pattern boundary. This includes section exits and the last prefix; zero capture-edge gaps are excluded. The complete source fade lowers the minimum body to 83.79 AC RMS and early release to 76.14, with early-release/body ratio below 0.909. Candidate/control left PCM remains exactly identical. Measurements establish rendered behavior, not preference or physical chip coherence.

The accepted 16–32-second articulated WAV export is byte-identical when extracted from the bounded and complete initialized renders at common gain 1.0. Full mono/candidate matching separately uses gains 0.9187188775 and 1.0, applied equally to each file's two channels. The 245-second boundary preserves source restart/continuation rather than a new finite ending.

## Exact stage dependency receipts

- [Private source pin](stages/source-pin.json)
- [Accepted mono pin](stages/accepted-mono-pin.json)
- [Complete native CPU/VICE/source execution](stages/complete-native.json)
- [Complete native render](stages/complete-render.json)
- [Support control preparation](stages/support-control.json)
- [Complete controlled render](stages/support-control-render.json)
- [Matched full listening preparation](stages/complete-listening.json)
- [Initial five release guards](stages/release-guards.json), [final six guards](stages/release-guards-final.json)
- [Initial all-prefix check](stages/release-check.json), [authoritative final-helper check](stages/release-check-final.json)

All nine stages executed freshly in 197.683 seconds. Review then strengthened the full-scope admission rule to reject an excluded capture-edge gap even when render duration is complete. The [final run](run-final-verified.json) took 10.396 seconds, freshly executing six guards and the release check while reusing seven unchanged stages. The [final binding](final-release-verification.json) verifies identical release-result bytes and accepted phrase; its stage receipt is authoritative for the current helper. The earlier five-test log and stage records remain historical execution provenance. No repeated cache benchmark is claimed.

Both explicit selections were inspected for source-note/checkpoint data and speech/audio payloads before promotion. Retained files contain aggregates, commands, settings and hashes only. Full private verification, source composition, support ledger, speech data, native traces, binaries and WAVs are excluded; the public proof binds private originals by hash.

Verify with `python3 scripts/evidence.py verify --group ghostbusters-stereo-articulated-full`. The [manifest](../manifest.json) owns exact archive paths, byte counts and hashes. Restore private assets and follow the [complete case reproduction](../../songs/studies/ghostbusters-stereo/README.md#complete-articulated-performance) for a new local run. Historical tool fingerprints identify the measured versions.
