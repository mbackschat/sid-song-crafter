# Rambo: faithful parts across two SID chips

This bounded stereo trial retains Martin Galway's complete *Rambo: First Blood Part II* loader score and native instruments. The [accepted faithful mono reconstruction](../../../samples/rambo-loader/README.md) is the reference. The earlier [palette interpretation](../rambo-interpretation/README.md) did not establish an improvement: the listener found its benefit inconclusive and suggested stereo might be more useful. This candidate tests that spatial change. **This trial does not fulfill the expanded arrangement brief.** The [user correction](listening-review.json) calls for centered elements and using both chips for additional musical roles, rather than only distributing the original three parts. Retain this split as a routing diagnostic, not the selected interpretation.

The three existing parts are split across two PAL MOS6581 chips; this is a three-part arrangement using two chips. It adds no notes, instrument patches, effects or independent musical parts. Native voices 1 and 3 remain together on SID A at `$D400`, preserving their oscillator sync/ring relationship; native voice 2 moves to voice 2 of SID B at `$D420` (registers `$D427–$D42D`). The first audition uses the renderer's direct chip outputs: **SID A left, SID B right**, without crossfeed. The Morse entrance, note timing, modulation and source ending remain part of the complete arrangement.

Galway composed, arranged and programmed the loader in 1985; the source credits Ocean Software. The retained score and generated complete-song derivatives use the [same GPL v3 terms and attribution](../../../samples/rambo-loader/README.md), with the [license](../../../samples/rambo-loader/LICENSE). This is a modified independent reconstruction, not the upstream driver binary. Original references and pending audition audio remain local under ignored `build/`.

## Reproduce the audition

Install the [local Python, VICE and renderer dependencies](../../../docs/setup/local-setup.md), then run from the repository root:

```sh
python3 scripts/listening-package.py config/listening/rambo-stereo.json --output build/rambo-stereo-v1
python3 scripts/publish-listening.py build/rambo-stereo-v1/run.json --selection songs/studies/rambo-stereo/audition.json --output build/rambo-stereo-listening
```

The [recipe](../../../config/listening/rambo-stereo.json) pins the unedited [score](../../rambo-loader.json) and accepted faithful SID, runs the focused compiler/audio guards, compiles the stereo SID with all 11,000 calls audited, then verifies those complete calls in headless VICE. It renders both versions from initialization for exactly 225 seconds at 44.1 kHz PCM16 with explicit PAL subtune 1. The PSID declarations select MOS6581 for both candidate chips and MOS6581 for the mono reference. CPU register/state agreement, VICE agreement, rendered signal health and musical acceptance are separate claims.

The [case preparer](../../../scripts/studies/rambo/prepare-stereo-listening.py) duplicates every faithful mono sample into both reference channels at unity gain and preserves the candidate's raw stereo as the full listening version. It extracts the same initialized phrase and ending windows. The [shared comparison tool](../../../docs/workflows/audio-comparisons.md) applies one AC RMS matching gain to each whole stereo clip, preserving that clip's channel balance; it does not normalize channels independently. Each comparison contains faithful reference A, a half-second gap, then stereo candidate B. Full files retain original renderer levels.

The publisher creates these stable local filenames under `build/rambo-stereo-listening/`; they are generated outputs, not tracked downloads:

- `faithful-then-stereo-phrase.ab.wav`: source seconds 32–48. **Does stereo separation add useful space while preserving the faithful version's balance and phrasing?**
- `faithful-then-stereo-ending.ab.wav`: source seconds 205–225. **Does the final hold and release work in stereo?**
- `faithful-dual-mono-full.wav`: the complete accepted mono reference, duplicated left/right at unity gain.
- `stereo-raw-full.wav`: the complete direct left/right candidate at original renderer levels; review the full form before accepting the whole arrangement.
- `stereo-mono-sum-diagnostic-full.wav`: the complete arithmetic average `(left + right) / 2`, rounded to PCM16, for a separate mono balance check. It is a diagnostic, not the main candidate or a claim of exact mono PCM recovery; separate SID analog paths and level distribution can differ from one chip.

For this audition, whole-clip matching attenuates the faithful phrase to gain 0.702445 (−3.068 dB) and faithful ending to 0.709972 (−2.975 dB); the stereo candidate keeps unity gain in both comparisons. Each file uses the same scalar on both channels. The full faithful and stereo files keep original levels.

The generated `build/rambo-stereo-v1/listening.md` links the SID, full renders, comparisons and receipts; `run.json` records stage execution and reuse. The [publisher selection](audition.json) preserves submitted filenames. Use a fresh publisher destination for a later audition.

## Verification and scope

The audio guard requires complete 225-second inputs, nonzero AC signal in both candidate channels, no PCM rail samples, distinct left/right samples, a closing body on both chips during seconds 205–211, and a settled final second on every channel. It records each channel's levels, the arithmetic mono-sum measurements and its residual against the raw faithful mono render without interpreting that residual as fidelity or musical quality. Focused tests reject a missing channel, collapsed stereo, clipping, truncated inputs, a missing closing body on either chip and an unsettled tail; independent PCM fixtures verify exact reference duplication, mono averaging, window bounds, source preservation and whole-file matching.

**Technical verification, 2026-10-15:** all 11 focused compiler/audio tests passed. Complete CPU and VICE runs matched all 87,559 ordered stores through 11,000 calls; CPU state checks matched ten checkpoints. Peak play cost was 5,427 of 19,656 cycles; VICE's maximum cadence error was four checkpoint cycles. Both full renders contain exactly 9,922,500 frames with no PCM rail samples. The candidate's closing left/right AC RMS values are 493.301/583.177 PCM16 units, and every final-second channel has zero AC RMS. The stereo WAV SHA-256 is `e16c9cca85ba486e064ad7a3eef5bc34ae43d971cafa5057af8fe6e98d251ba8`; the candidate SID SHA-256 is `7d6e0c8f408faca576d01729f437fe913dae02c118466aa293e846c6da12558c`. The complete fresh recipe took 79.289 seconds; the unchanged repeat reused all ten stages. These are local automation timings, separate from creative effort and human listening.

The output is a PAL two-MOS6581 PSID at `$D400/$D420`, with one play call per 19,656 cycles (about 50.125 Hz). It requires matching two-SID playback configuration. Physical hardware, NTSC export, crossfeed alternatives and six-part arrangement expansion are outside this first trial.

**Model-assistance checkpoint:** no model call is useful for this stereo preference question. Existing audio models remain experimental supporting signals; the human phrase, ending and full-form verdict decides musical acceptance. No paid call is made. Reassess after listening feedback, before closing the case.

The [retained evidence](../../../evidence/rambo-stereo/README.md) preserves complete CPU/VICE traces, state checkpoints, fresh and cached execution receipts, signal measurements and the submitted audio hashes. Reused: the faithful score and patches, existing compiler/player, renderer, VICE verifier and comparison/publisher tools. New work: an opt-in fixed stereo routing mode with coupling guards and a small case-specific PCM preparation step. No second score engine or new musical material was required. Total creative effort and time to musical acceptance are not inferred from recipe runtime.
