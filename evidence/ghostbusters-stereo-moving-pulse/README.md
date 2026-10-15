# Ghostbusters bounded moving-pulse timbre trial

The listener rejected this bounded pulse-motion trial: “Hmm. Different, but not suitable, too vibrant. Maybe stick with last (original) one.” The [scoped verdict](../../songs/studies/ghostbusters-stereo/moving-pulse-listening-review.json) selects the previous [complete static articulated performance](../ghostbusters-stereo-articulated-full/README.md), with its qualified positive verdict and plain-tone complaint retained. The selected configuration is [articulated-arrangement.json](../../songs/studies/ghostbusters-stereo/articulated-arrangement.json); no complete moving-pulse execution, render or further experiment is planned.

Both comparison halves retain the same source-root pitch, 40-call gate, 88-call gap, envelope, parts and placement. The first half uses the current full static-pulse baseline, not the rejected long hold. The second enables the `$600`–`$A00` pulse-width triangle through body and release. Both channels of both versions and the causal control use a common scalar gain of 1.0; no independent RMS matching changes their relative levels.

| Question | Retained evidence |
| --- | --- |
| Which settings and submitted files? | [Note-free arrangement](arrangement.json), [bounded recipe](recipe.json), [friendly filenames](audition-selection.json), [submission hashes](listening-submission.json), [static-then-moving bounds](comparison.json) |
| What actually executed? | [Aggregate native CPU/VICE proof](native-proof.json): 2,600 music calls, 73,410 ordered stores across both chips, 45,410 non-nested NMIs, peak 85/102 cycles |
| Does the animated support release? | [Causal audio measurements](audio.json), [same-cycle gate-off intervention](support-control.json), [six reused-contract guards](release-guards.txt) |
| Is the pulse change isolated over the complete score? | [Numeric-only comparison](numeric-isolation.json): 14,389 calls, 63,996 identical non-pulse stores, 64 identical gates and 28,778 added pulse-width stores; not full native/PCM proof |
| What was fresh? | [Seven-stage execution](run-executed.json), 44.155 seconds with no stages reused |

Candidate/control left PCM is exactly identical. All fifteen complete measured late gaps have zero right-difference RMS and peak. Minimum body AC RMS is 1,168.48 and early release 686.38 PCM units; maximum early-release/body ratio is 0.632. The capture-edge final gap and later harmony exits are excluded. These results establish bounded native/rendered behavior and contribution. The listener heard the difference but rejected its musical suitability; no complete moving-pulse claim follows.

## Stage fingerprints

- [Current static full baseline pin](stages/initial-stereo-pin.json)
- [Bounded native execution](stages/native.json)
- [Moving-pulse render](stages/render.json)
- [Same-cycle gate-off control](stages/support-control.json)
- [Control render](stages/support-control-render.json)
- [Release/gain/alignment guards](stages/release-guards.json)
- [Static-versus-moving phrase preparation](stages/prepare-listening.json)

Shared preparer output names inside the cache retain historical `initial-held`/`articulated` wording. The pinned input is the current static articulated full file; publication explicitly names the files `static-pulse-phrase.wav`, `moving-pulse-phrase.wav` and `static-then-moving-pulse.ab.wav`. The A/B uses initialized 16–32 seconds from each version, static first, a half-second separator, then moving pulse.

Selected payloads were inspected for source notes, checkpoints, speech and audio. Public evidence contains aggregate results, hashes, commands and note-free selectors only. Source composition, support ledger, speech, full private verification, native traces, binaries and WAVs remain local. Verify with `python3 scripts/evidence.py verify --group ghostbusters-stereo-moving-pulse`; [the manifest](../manifest.json) owns exact archive paths, sizes and hashes. Reproduce through the [case](../../songs/studies/ghostbusters-stereo/README.md) and [bounded recipe](../../config/listening/ghostbusters-stereo-moving-pulse.json).

The [reusable numeric probe](../../scripts/studies/ghostbusters/check-pulse-motion.py) compares the complete independent numeric store streams while excluding only `$D429/$D42A`; its two guards include rejection of an unrelated envelope change. Reproduce it with the pinned private composition restored:

```sh
PYTHONPATH=.tools/test-deps:scripts python3 scripts/studies/ghostbusters/check-pulse-motion.py --composition evidence/ghostbusters-independent-full/native/composition.json --baseline songs/studies/ghostbusters-stereo/articulated-arrangement.json --candidate songs/studies/ghostbusters-stereo/animated-arrangement.json --output build/ghostbusters-pulse-motion-recheck/summary.json
```

The closure model-assistance review selects no further model call: retained calibration does not qualify a model to override this timbral preference. Prior pulse-motion acceptance in another tune remains context-specific.
