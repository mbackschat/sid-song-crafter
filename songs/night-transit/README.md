# Night Transit

An original single-SID space-flight theme: warm bass, a clear moving-pulse lead, sustained harmony, contrasting middle and resolved ending. E minor, 112 BPM, 32 bars. The three unchanged sounds come from the Bach work; [reuse and measured effort](reuse-and-effort.json) preserves exact sources and feedback. [Score](score.json) and [native arrangement](native.json) are editable musical inputs, using the existing native backend without new infrastructure.

## Current musical verdict: rejected and closed

The first theme received: “yes, feel engaging and melodic, with a warm bass and clear lead . But melody (composition) is not nice, however this was not your point!” After the melody-only revision, the user said: “I don't enjoy. The song is not harmonic, bad composition. Maybe use at least a existing music score, don't try to compose a score. That is a much harder task”.

Both compositions are rejected. The sounds and balance of the first audition were liked, which does not validate the notes or harmony. All melody, bass and harmony were invented for this trial; no existing score was used. This added an original-composition problem to the intended test of SID interpretation. Do not revise the piece further. The [next trial](../../PLAN.md#active-score-interpretation-trial) uses existing musical scores.

The complete PAL and NTSC drafts pass native CPU schedule/ending checks and sampled headless VICE checks. These establish playback, not good harmony or musical quality. The independent structural review was insufficient to judge the composition. Retain these findings and auditions as a rejected experiment, not an accepted repertoire composition or proof of productivity.

## Reproduce

```sh
python3 scripts/listening-package.py config/listening/night-transit.json --output build/night-transit-reproduction
python3 scripts/publish-listening.py build/night-transit-reproduction/run.json --selection config/listening/night-transit-audition.json --output build/night-transit-reproduction-listening
python3 scripts/listening-package.py config/listening/night-transit-ntsc.json --output build/night-transit-ntsc-reproduction
```

Prepare the existing [native tools](../../docs/workflows/native-song-workflow.md); local and hosted assessment models are optional and unused here. Keep output directories fresh to preserve old auditions and run hashes.

## Productivity and model assessment

The first audition was available 6 minutes 16 seconds after the first explicit timing marker; initial retrieval preceded that marker, and publishing/cleanup occurred concurrently. The first PAL recipe took 23.83 seconds. These are measured wall times, not active composition time or time to acceptance. There is no comparable prospective Bach baseline, so no percentage productivity gain is claimed. The first musical verdict shows that fast reuse of accepted sounds does not guarantee a good new melody.

Model assistance was reviewed at the first audition and after feedback. No inference was warranted: the available trials do not calibrate melody preference. At closure, no model inference was useful: the user rejected the music and clarified the task. No model score can override that verdict; reassess usefulness on the next score-backed interpretation.

## Second draft: melody-only revision

The second draft reduces the melody from 115 to 91 notes, repeats a question/answer contour, sustains the contrasting middle and returns the theme exactly. All bass/harmony notes, sounds, tempo and section lengths are unchanged. The retained internal section label “Homeward: theme varied” describes V1; V2's actual return is exact. This is a hypothesis about what may improve the tune, not a musical acceptance claim.

Listen to [previous then revised theme](../../build/night-transit-v2-listening/previous-then-revised.ab.wav) (36.5 seconds, equal unity gains), [revised theme](../../build/night-transit-v2-listening/main-theme.wav), or [complete revised piece](../../build/night-transit-v2-listening/night-transit.wav). V1 is retained at commit `a86b685` and in the original audition folder. V2 was rejected; the earlier complete-piece question is superseded and no further feedback is required for this closed trial.

PAL and NTSC builds took 25.10 and 28.60 seconds respectively while running concurrently. Both pass complete CPU schedule/stop checks and sampled standalone VICE checks. Independent score review confirms that only the melody changed, events do not overlap, the theme returns exactly and the final dominant resolves to E minor. These checks cannot establish pleasantness. The first V2 attempt correctly rejected unordered input events; sorting the editable score fixed the input without a compiler change.

[Canonical draft evidence](../../evidence/night-transit-drafts/night-transit-v2-ordered/run.json) retains both versions' complete numeric records and published audition hashes through the existing evidence tool. No model inference was added after revision: melody preference remains uncalibrated, and the closure review accepts the rejection and moves to a sourced score.
