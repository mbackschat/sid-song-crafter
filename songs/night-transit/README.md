# Night Transit

An original single-SID space-flight theme: warm bass, a clear moving-pulse lead, sustained harmony, contrasting middle and resolved ending. E minor, 112 BPM, 32 bars. The three unchanged sounds come from the Bach work; [reuse and measured effort](reuse-and-effort.json) preserves exact sources and feedback. [Score](score.json) and [native arrangement](native.json) are editable musical inputs, using the existing native backend without new infrastructure.

## Current musical verdict

The first 18-second theme audition received: “yes, feel engaging and melodic, with a warm bass and clear lead . But melody (composition) is not nice, however this was not your point!” This supports the sound palette and balance, but rejects the composition. A pleasing composition is part of this trial's goal; this is not a successful finished piece yet. Revise the melody while preserving the sounds and accompaniment, so the next audition tests that question directly.

The first complete PAL and NTSC drafts pass native CPU schedule/ending checks and sampled headless VICE checks. These establish playback, not musical quality. Original auditions remain in `build/night-transit-listening/`. No source recording exists for this original composition.

## Reproduce

```sh
python3 scripts/listening-package.py config/listening/night-transit.json --output build/night-transit-reproduction
python3 scripts/publish-listening.py build/night-transit-reproduction/run.json --selection config/listening/night-transit-audition.json --output build/night-transit-reproduction-listening
python3 scripts/listening-package.py config/listening/night-transit-ntsc.json --output build/night-transit-ntsc-reproduction
```

Prepare the existing [native tools](../../docs/workflows/native-song-workflow.md); local and hosted assessment models are optional and unused here. Keep output directories fresh to preserve old auditions and run hashes.

## Productivity and model assessment

The first audition was available 6 minutes 16 seconds after the first explicit timing marker; initial retrieval preceded that marker, and publishing/cleanup occurred concurrently. The first PAL recipe took 23.83 seconds. These are measured wall times, not active composition time or time to acceptance. There is no comparable prospective Bach baseline, so no percentage productivity gain is claimed. The first musical verdict shows that fast reuse of accepted sounds does not guarantee a good new melody.

Model assistance was reviewed at the first audition and after feedback. No inference was warranted: the available trials do not calibrate melody preference. Preserve the user's judgment, make a bounded musical revision, and reassess at the next audition and closure.
