# Airwolf: editable reconstruction and tonal reuse

Airwolf is the active T1 case after the [accepted Billie Jean reconstruction and transfer](billie-jean-preparation.md#listening-verdicts-and-case-closure). The [shared intake](pop-theme-preparation.md#airwolf-score-cycle-and-independent-numeric-model) owns historical source execution, score decoding and the bounded VICE restart check. This document owns independent delivery and subsequent listening judgments. The source is Sylvester Levay’s *Airwolf Theme*, arranged for the C64 by Mark Cooksey, 1985 Elite; these are distinct composition and SID-arrangement credits.

Use the [registered HVSC download](https://www.hvsc.de/download/C64Music/MUSICIANS/C/Cooksey_Mark/Airwolf.sid), SHA-256 `03c602da9182759c78ca4d90ad3bd5b223b3eb61f34ea31c2205fffc589bf89f`, through the [pinned asset workflow](../../setup/local-setup.md). The single/default subtune 1 declares PAL/MOS6581 and VBI playback. Original SID bytes and rendered reference audio remain local.

## Reuse the complete source proof

The retained [numeric model](../../../evidence/airwolf-form/model.py) covers the selected source’s complete SID-write behavior, with [2,500-call evidence](../../../evidence/airwolf-form/complete/receipt.json) matching 11,253 ordered stores and both observed restarts. No further sound-engine probe is needed to build this declared arrangement: the source uses fixed pulse settings and note-triggered envelopes, without a separate continuing modulation program. The historical model and tool fingerprints remain frozen; new tools must recheck that evidence rather than silently repinning the old capture.

| Native mechanism | Exact behavior and reuse constraint |
| --- | --- |
| Initialization | Consume row zero during init. A subsequent play call is the next timing boundary; do not place a second copy of the first note at call zero. |
| Duration | Decrement the byte before comparing with `$FF`; duration `N` spans `N+1` update frames. Row zero begins during init, so its next row arrives at play call `N`. A sign test would mishandle durations above 127. |
| Fixed writes | Each native update writes volume `$D418=$0F`, then pulse highs `$D403=$28` and `$D40A=$0A`. Preserve raw bytes for source comparison; the SID ignores the upper four pulse-high bits. |
| Pitched entry | In ascending physical voice order, write AD, SR, control zero, control with GATE, frequency high, then frequency low. Voices 1/2 use AD `$0A`, SR zero and pulse `$41`; voice 3 uses AD `$09`, SR zero and triangle `$11`. |
| Hold | A zero frequency-high source field consumes no low byte and performs no voice writes. It preserves existing sound; it is not a rest or proof of silence. |
| Internal restart | Terminal duration zero re-enters init and play within the same host call, repeating the three fixed writes before row zero. Source calls 1241 and 2483 are the observed restart boundaries. |
| Unwritten SID state | Pulse lows, filter cutoff/routing and voice 3 pulse width are not initialized by this source contract. Numeric software-state reset is distinct from hardware register reset; controlled renders start with the renderer’s SID reset state. |

The selected complete first traversal has 138 rows of duration 8, totaling 1,242 update frames. Init consumes row zero; the export preserves init plus music calls 0–1240 and begins its authored release before the restart at 1241. Source recurrence and the deliberately finite ending retain separate proofs below.

## Editable numeric player and retained checkpoint

The [portable composition](../../../evidence/airwolf-player/composition.json) and [numeric player](../../../scripts/studies/airwolf/airwolf_player.py) use `airwolf-composition-v1`: explicit PAL/MOS6581 target, direct frequency words, editable per-voice AD/SR/control and shared volume/two raw pulse-high bytes. Each row contains duration 1–255 and three entries. A frequency word 256–65535 retriggers that voice in native store order; `null` holds without row-level voice writes. The separately authored `"off"` token clears GATE on the last emitted control while retaining the waveform for release. Native fixed writes still precede each update, including hold/off rows. There is no continuing effect engine, original code or captured-event replay.

Named software state is derived from the same row/patch input, with no duplicate editable initial sound image. Init restores software caches and consumes row zero; its resulting state is explicit in the [receipt](../../../evidence/airwolf-player/receipt.json). The [retained checker](../../../scripts/studies/airwolf/check-player.py) verifies source/archive fingerprints and recomputes all **2,500 calls, 11,253 stores, 1,738 reads and 2,501 actual pointer/countdown states**, including restarts at 1241 and 2483. It also matches both retained 128-call frequency/duration interventions. [Complete stores](../../../evidence/airwolf-player/writes.json.gz), [reads](../../../evidence/airwolf-player/reads.json.gz) and [play returns](../../../evidence/airwolf-player/returns.json.gz) retain the comparison. Register shadows describe emitted ports; they do not claim SID internal-state observations or arbitrary prior hardware-state independence.

```sh
python3 scripts/listening-package.py config/listening/airwolf-player.json --output build/airwolf-player-work
python3 scripts/evidence.py verify --group airwolf-player
```

The [numeric checkpoint run](../../../evidence/airwolf-player/run.json) took **0.500545209 seconds** on 2026-10-14. It combines [eleven bounded player/title guards](../../../evidence/airwolf-player/guards.txt) and the retained proof. This is fresh numeric computation with **no new original CPU/VICE capture**. Frozen source tools and their historical pins remain intact. Authored off/ending and editable patch parameters have separate numeric/compiled guards; the old source capture does not silently become evidence for those extensions.

## Compiled export and listening package

The [editable reconstruction](../../../songs/studies/airwolf-reconstruction/README.md), [compiler](../../../scripts/studies/airwolf/compose.py) and [runtime scheduler](../../../songs/players/airwolf.asm) preserve the initialized first traversal with native tuning and static patches. The compiler lowers rows into duration and three hold/off/pitch records, with numeric patch data consumed at runtime. No original executable or per-call store schedule is embedded. It emits PAL/MOS6581 PSID2 and standalone PRG under the [backend contract](../../workflows/decoded-song-workflow.md#airwolf-runtime-rows-and-static-patches).

The [complete compiled proof](../../../evidence/airwolf-compiled/candidate/verification.json) checks **1,338 play calls, 1,339 named init/play states and all 5,593 ordered stores**, including executed SID writer sites. Maximum play cost is **555 of 19,656 cycles**. Poisoned software-state/workspace restoration and decimal-mode callers are checked separately from hardware initialization. The frozen [assembly](../../../evidence/airwolf-compiled/candidate/player.asm.gz), [listing](../../../evidence/airwolf-compiled/candidate/player.listing.gz), [checkpoints](../../../evidence/airwolf-compiled/candidate/state-checkpoints.json.gz) and [ordered stores](../../../evidence/airwolf-compiled/candidate/writes.json.gz) retain the proof. The [source-prefix comparison](../../../evidence/airwolf-compiled/source-prefix.json) matches **5,586 stores**, including 21 init stores and music calls **0–1240**; the seven ending stores are deliberately excluded from source identity.

The [full controlled VICE run](../../../evidence/airwolf-compiled/vice/study.json) independently matches all 5,593 stores through play call 1337. Maximum entry-cadence error is **eight cycles against nine allowed**. This is complete callable exported-SID execution in the controlled PAL host. The actual PRG bootstrap check in the compiled receipt covers BASIC `SYS 2061`, poisoned init and **only the first two calls**, matching 27 stores with modeled raster/CIA reads and 19,657 cycles between entries. It is distinct from full controlled VICE playback and does not claim real VICE PRG autostart, original-host cadence or exact SID bus timestamps.

The ending closes the held controls at **1241** before native fixed writes, countdown decrement or the internal restart. It holds the resulting gate-low registers for **32 calls**, then at **1273** clears all controls and master volume. Calls 1274–1337 verify 64 further calls without stores. Score processing and recurring fixed writes remain suspended throughout the tail; held pitch and pulse settings stay unchanged. This is an authored release with **no fade**. The original continues looping, so the ending needs its own musical judgment.

The [27-second render checks](../../../evidence/airwolf-compiled/audio.json) find no clipping and pass candidate-only settled-tail checks. The [pre-mute window](../../../evidence/airwolf-compiled/pre-mute.comparison.json) over **25.1–25.3 seconds** measures **zero AC RMS with DC +157** before volume-zero; the [automated guard](../../../evidence/airwolf-compiled/pre-mute-guard.txt) enforces settling before mute. [Ending measurements](../../../evidence/airwolf-compiled/ending-measurements.json) bracket the final-volume transition between **25.390 and 25.408 seconds** and retain zero final-second AC RMS with DC −157. Snapshot times are renderer observations, not exact bus timestamps. A settled PCM window supports decay inspection; it does not establish a natural or musically complete ending.

```sh
python3 scripts/studies/airwolf/prepare-title.py --check
PYTHONPATH=.tools/test-deps python3 scripts/studies/airwolf/compose.py songs/studies/airwolf-reconstruction/composition.json --output build/airwolf-compiled-new
python3 scripts/listening-package.py config/listening/airwolf-full.json --output build/airwolf-full-work
python3 scripts/publish-listening.py build/airwolf-full-work/run.json --selection scripts/studies/airwolf/title-audition.json --output build/airwolf-listening
python3 scripts/evidence.py verify --group airwolf-compiled
```

The [standard title run](../../../evidence/airwolf-compiled/run-initial.json), before adding the explicit pre-mute stages, took **6.750912541 seconds** on 2026-10-14. The [current run](../../../evidence/airwolf-compiled/run.json) includes that guard, reuses earlier validated stages and took **0.279200834 seconds**. These are routine recipe execution times, not engineering effort or time to musical acceptance. Standalone export and publication destinations must be fresh; the recipe supports validated cache reuse. Original SID/reference audio and generated exports/audio remain in ignored local storage.

The [listening submission](../../../evidence/airwolf-compiled/listening/submission.json) binds the published files and hashes to the completed run. The [phrase comparison](../../../build/airwolf-listening/phrase-reference-then-ours.ab.wav) presents original then reconstruction over **3–19 seconds**; the [ending comparison](../../../build/airwolf-listening/ending-reference-then-ours.ab.wav) uses the same order over **15–27 seconds**. The [opening](../../../build/airwolf-listening/opening-reference-then-ours.ab.wav) covers 0–12 seconds, and the title README links the full 27-second recordings. Source-prefix register agreement, rendered signal health and human phrase/ending judgments remain separate.

## Familiar transfer and pending judgments

The [static tonal palette](instruments/airwolf-static-tones.md), [editable familiar example](../../../songs/studies/airwolf-elise/README.md) and [matched-transfer recipe](../../../config/listening/airwolf-elise-transfer.json) reuse pulse/pulse/triangle on physical melody/bass/harmony voices 1/2/3. Plain and candidate share **53 nominal Für Elise notes, 48 merged rows and 19 explicit gap/startup off commands**. Both preserve native AD/SR, volume 15 and raw pulse-high bytes 40/10; the plain reference substitutes triangles for the two pulse controls. Both use direct A440 words at the declared PAL clock. This is a deliberate familiar-material adaptation; the title retains its original frequency words.

The [preparation report](../../../songs/studies/airwolf-elise/preparation.json) records timing and initialization explicitly: musical frame zero is init, and later frame `q` maps to play call `q−1`. Absolute boundaries round to the nearest update. The 501-frame phrase begins its authored release at play **500**, stops at **532** and audits through 596 for **597 calls**. Maximum boundary error is **9.814 ms**, maximum duration error **17.661 ms**, and nominal pitch error is within **0.319 cents**. `null` holds; genuine gaps use off commands, which permit release rather than promising instantaneous acoustic silence. The implied pulse widths 2048/2560 assume unwritten low bytes start at zero, as in the controlled renderer reset.

The separate [plain](../../../evidence/airwolf-elise/reference/verification.json) and [candidate](../../../evidence/airwolf-elise/candidate/verification.json) CPU proofs each check **597 calls, 598 states and 1,847 stores**, with maximum play cost **456 of 19,656 cycles**. Complete callable [plain VICE](../../../evidence/airwolf-elise/reference-vice/study.json) and [candidate VICE](../../../evidence/airwolf-elise/candidate-vice/study.json) match those stores, each with maximum cadence error **six cycles against nine allowed**. The [two twelve-second render checks](../../../evidence/airwolf-elise/audio.json) find no clipping and zero final-second AC RMS; the [separate listening submission](../../../evidence/airwolf-elise/listening/submission.json) binds the [plain-then-Airwolf comparison](../../../build/airwolf-elise-listening/plain-then-airwolf.ab.wav), 24.5 seconds with the generated reference first. The [executed transfer recipe](../../../evidence/airwolf-elise/run.json) took **5.845379042 seconds** on 2026-10-14; the palette card owns reuse constraints and subsequent listening verdicts.

```sh
python3 scripts/studies/airwolf/prepare-elise.py --output songs/studies/airwolf-elise --check
python3 scripts/listening-package.py config/listening/airwolf-elise-transfer.json --output build/airwolf-elise-work
python3 scripts/publish-listening.py build/airwolf-elise-work/run.json --selection scripts/studies/airwolf/elise-audition.json --output build/airwolf-elise-listening
python3 scripts/evidence.py verify --group airwolf-elise
```

## Delivery boundary

Title and familiar-transfer technical pipelines are complete and published. **Three human judgments remain pending: reconstruction phrase, authored ending and familiar transfer.** Next comes listener feedback, any justified revision and case closure under the [delivery workflow](../../workflows/decoded-song-workflow.md#deliver-one-musical-case).

The [first representative audition model review](../../../evidence/airwolf-compiled/model-review.json) records **no model call**: fine fidelity, musical balance and natural endings remain outside calibrated eligibility. CPU/VICE and PCM checks settle execution and signal health; human feedback settles these musical judgments. Reassess after feedback or substantive revision and again before closure under the [standing rule](../audio-assessment.md#use-and-reassess-model-assistance). Models remain experimental supporting signals.
