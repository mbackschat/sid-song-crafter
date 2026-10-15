# Axel F: learn from Hülsbeck's lead

The listener selected Chris Hülsbeck's original as the master reference on 2026-10-15 and said “Hülsbeck's version is really great”. The [reference intake](tgi-reference.md) owns its source URL, fingerprint, attribution and local playback files. This study asks how the lead's onset, movement and release can improve our [score-based interpretation](README.md). It does not replace the independently sourced MIDI with Hülsbeck's note data or claim that one instrument explains the whole musical preference.

## What the executed lead teaches

The opening lead is physical voice 2. Its pulse body uses control `$41`, attack/decay `$0A` and sustain/release `$49`, with `$D417=$08`: the external-input route bit is set, but no oscillator voice is routed through the filter in the bounded opening. A new onset resets pulse width to `$200`. A 32-call ascent and 16-call descent use step `$20`; the asymmetric cycle accumulates width rather than settling into a fixed triangle range. Subsequent note onsets reset the trajectory. Modulation continues while GATE is clear, so the release is still a changing sound.

The source writes CIA Timer A low/high bytes `$00/$46`, giving an inclusive period of `$4601` cycles, approximately 54.98 updates per second on PAL. These are driver calls, not PAL video frames. The existing Shades audit correctly rejects this different layout: its payload starts at `$A000`, and the callable wrapper changes banking during playback. The bounded source-specific probe retains strict I/O and execution guards; it does not weaken the production VBI or Shades profiles.

Articulation is a separate finding from pulse width. After the first audible lead onset, the source's gate-clear/set writes are about 49 CPU cycles apart, with no per-note TEST frame. Our native Extra arrangement uses a TEST onset frame and the preferred `$08A8` envelope. Copying a pulse width therefore cannot reproduce the source's envelope history or articulation. The source also uses delayed raw-frequency-word vibrato; importing its numeric step into another pitch range or driver would not preserve a constant musical interval.

These are bounded execution findings, not a universal Hülsbeck style. The [Shades instrument study](../../docs/research/composition/instruments/shades-decoded-programs.md) already establishes useful moving releases and delayed modulation; the [Giana contrast](../../docs/research/composition/huelsbeck-contrast.md) shows that related musical purposes can have different driver schedules. Keep the timing, retrigger and shared-filter contracts with each implementation.

## Execution and reproduction

The [source-specific probe](../../scripts/studies/axel-f/study-huelsbeck.py) executes the fingerprinted original and a working copy whose pulse-step byte alone is frozen. The [aggregate verification](huelsbeck-study-verification.json) records 1,600 real CIA-timed VICE calls and 17,659 matching ordered SID/timer stores for each version. The independent parameter/state model matches all 1,081 lead states after its entrance. There are 420 changing pulse states with GATE clear. Maximum interrupt-interval error is four cycles, and accumulated phase error is two; these observations use the declared controlled host, not original-game startup or SID bus timestamps.

Freezing the step at RAM `$AE37` (SID file offset `$0EB5`) changes 1,699 store values, confined to voice 2's pulse registers `$D409/$D40A`. Other register values, ordered store identities, recorded instruction-start times and callable play costs remain equal. This establishes the causal programming mechanism. The frozen source has no listening verdict and does not establish why the listener likes the complete reference.

```sh
python3 scripts/setup-project.py --only references --include axel-f-huelsbeck
python3 scripts/listening-package.py config/listening/axel-f-huelsbeck-study.json --output build/axel-f-huelsbeck-verification
```

The recipe records its dependencies and caches only fingerprint-matching evidence. It reuses the existing CIA host/trace helpers behind a pinned source-specific adapter; the normal auditors keep their narrower admission contracts. Source binaries, the modified source, detailed CPU/VICE observations and renderer files remain private under ignored output. The aggregate retains hashes and reproduction settings without the musical score or source payload.

## First transfer: change only the pulse program

The [native candidate](huelsbeck-pulse.json) starts from the listener's preferred [smoother palette](smoother.json). Only its lead pulse table changes. The source score, native note/gate schedule, envelope, vibrato, chip model, bass, accompaniment and filter ownership remain fixed.

The new independent program starts at `$200`, rises by 35 for 29 updates, then alternates 15 downward and 15 upward steps. Its nominal body bounds are `$3EA`–`$5F7`. Executed native snapshots place the 29-step initial rise at 0.579 seconds. Table transitions add calls: the settled loop descends in 17 frames, rises in 16 and repeats every 33 frames (0.658 seconds), rather than two bare 15-step durations. The initial rise is close to the reference's nominal 32-call rise. We deliberately bound the later movement instead of carrying over the reference's cumulative drift. This is a source-informed interpretation, not an exact reconstruction of Hülsbeck's instrument.

The musical hypothesis is that a narrower, moving onset supplies a more useful lead character than our previous `$400`–`$800` sweep. A different register trajectory does not establish that it sounds better. The listener accepted the same-score comparison on 2026-10-15: “Yes: second lead have a more appealing character while keeping the melody clear”. Select this pulse program for the complete arrangement while retaining the prior smoother version for comparison. This accepts the excerpt’s lead character and clarity, not the full song or an exact match to Hülsbeck. Lower sustain and source-like retrigger behavior remain separate hypotheses, not changes bundled into this trial.

The [audition recipe](../../config/listening/axel-f-huelsbeck-pulse.json) verifies 212 notes over 1,795 calls, sampled standalone VICE playback and quiet, unclipped renders. All post-call register differences are confined to the lead's pulse-width registers. The full observed loop includes release: the final lead resets at frame 696, its gate clears at 724, and the first upper bound arrives at 725. That state proof does not imply that the entire late loop is audible.

```sh
python3 scripts/listening-package.py config/listening/axel-f-huelsbeck-pulse.json --output build/axel-f-huelsbeck-pulse
python3 scripts/publish-listening.py build/axel-f-huelsbeck-pulse/run.json --selection config/listening/axel-f-huelsbeck-pulse.audition.json --output build/axel-f-huelsbeck-pulse-listening-new
```

The already reviewed files are in `build/axel-f-huelsbeck-pulse-listening/`: `previous-then-narrow-pulse.ab.wav` plays 16.1 seconds of the prior smoother lead, 0.5 seconds of silence, then the new pulse version. Both halves use unity gain; this controls playback gain, not perceived loudness. `previous.wav` and `narrow-pulse.wav` retain the full 35.773-second selected excerpt and tail. Hülsbeck's separately rendered `build/axel-f-huelsbeck-listening/huelsbeck-original-32s.wav` is a timbral reference with its own timing and arrangement, not the same-score A/B reference.

Model-assistance review: no audio-model call. The existing calibration does not qualify a model to judge this paired lead timbre or to attribute the listener's overall preference. Executed traces establish the mechanism; the listener judges its musical usefulness. At the positive listening verdict, no additional model call is useful: the human judgment settles this comparison. Reassess at the complete-arrangement audition.

## Full-arrangement limitation

The subsequent [full listening feedback and arrangement diagnosis](arrangement-review.md) reject applying this hook patch to every role. A long chord-support note becomes too persistent, and short high-register notes restart before the intended motion develops. The hook verdict remains valid within its tested scope; the overall arrangement needs distinct support/high-lead sounds and a deliberate rhythmic allocation.
