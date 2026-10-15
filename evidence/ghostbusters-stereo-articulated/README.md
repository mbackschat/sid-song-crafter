# Ghostbusters bounded articulated-support trial

The [active case](../../songs/studies/ghostbusters-stereo/README.md) replaces the rejected continuous held root with the source-root prefix and a natural release/rest. The [phrase verdict](../../songs/studies/ghostbusters-stereo/articulated-listening-review.json) is accepted: “yes, disappeared. all great now.” The initial speech and complete-continuation verdicts retain their separate scopes. This trial renders 48 seconds and submits only the initialized 16–32-second phrase; it does not verify a revised 245-second performance.

| Question | Retained evidence |
| --- | --- |
| Which settings and local clips? | [Note-free arrangement](arrangement.json), [recipe](recipe.json), [audition selection](audition-selection.json), [published submission hashes](listening-submission.json), [old-then-articulated bounds](comparison.json) |
| Does the new native code execute? | [Aggregate CPU/VICE proof](native-proof.json): 2,600 music calls and 68,210 stores on both chips, zero SID reads, 85-cycle peak NMI against the 102-cycle period |
| Does release actually decay? | [Causal audio measurements](audio.json), [same-cycle gate-off intervention](support-control.json), [four focused guard results](release-guards.txt) |
| What was fresh versus cached? | [Fresh native/main/control execution](run-native-executed.json), [final preparation with those stages reused](run-verified.json) |

The support gate lasts 40 calls, about 0.6686 seconds. A same-image gate-off control leaves the complete left PCM unchanged. The first right-channel causal contribution occurs at 15.231156 seconds versus the CPU-relative gate prediction at 15.227262 seconds; the measured 3.895 ms offset includes renderer startup and attack latency and stays below the frozen 25 ms bound. It anchors the prescribed native call grid rather than assuming that renderer time zero equals native initialization.

Across fifteen complete retrigger gaps in this first source region, minimum attack AC RMS is 1,527.41, body 1,168.58 and early release 685.46 PCM units. Early-release AC remains below 0.632 of body AC. Every checked late-gap window has zero right-difference RMS and peak, against limits of one and two PCM units. The final support at the 48-second capture edge and later harmony exits are excluded; these measurements do not establish complete-song release behavior or natural-sounding articulation.

The old and articulated phrase files use one common gain of 1.0 on both stereo channels. No independent loudness matching removes the change caused by shorter support. The A/B plays the rejected initial phrase first, a half-second separator, then the articulated phrase. The listener accepted the corrected phrase; complete-song scope remains pending.

## Stage fingerprints

- [Initial stereo pin](stages/initial-stereo-pin.json)
- [Bounded native execution](stages/native.json)
- [Main render](stages/render.json)
- [Gate-off control](stages/support-control.json)
- [Control render](stages/support-control-render.json)
- [Release guards](stages/release-guards.json)
- [Phrase preparation](stages/prepare-listening.json)

The fresh native/render invocation took 37.444 seconds. Final guard/preparation execution took 3.414 seconds with all five native/render/pin stages reused; this is not a new native execution. Exact dependency and artifact hashes are retained above. Source notes, the private support ledger, complete private proof, encoded speech, native traces, SID/PRG and WAV files are excluded. The public proof binds private originals by hash.

Run `python3 scripts/evidence.py verify --group ghostbusters-stereo-articulated` to check [the manifest](../manifest.json). Reproduce with the [bounded recipe](../../config/listening/ghostbusters-stereo-articulated.json) and [case instructions](../../songs/studies/ghostbusters-stereo/README.md). Promotion used the existing explicit-selection tool; no source or audio was added to Git.
