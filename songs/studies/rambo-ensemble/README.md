# Rambo: expanded dual-SID ensemble

This interpretation keeps Martin Galway's complete *Rambo: First Blood Part II* loader score and native sound programs on SID A and adds subordinate parts on SID B. The [accepted faithful mono reconstruction](../../../samples/rambo-loader/README.md) remains the musical reference. The earlier [three-part stereo split](../rambo-stereo/README.md) did not fulfill the listener's request for centered elements and additional musical roles across both chips. This candidate uses all six oscillators where the score supports a fuller texture, with space elsewhere. **The first review found uncertain added weight and no clear left/right placement; revision is required.**

The intended character is the faithful loader's cinematic tension and drive with a broader harmonic body. The primary melody, bass articulation, coupled oscillators, Morse passage, timing and final long-release gesture stay together on SID A. Its generated listening mix places the whole faithful group in the center. SID B supplies three different roles rather than another melody: a low moving-pulse anchor, a soft sustained inner chord tone and spaced pulse swells drawn from the source chord rhythm. SID B forms a second stereo group; this is group placement, not independent per-voice panning.

The physical mapping preserves source voices 1, 2 and 3 as A1 (`$D400`), A2 (`$D407`) and A3 (`$D40E`). The added roles map to B1 (`$D420`), B2 (`$D427`) and B3 (`$D42E`) as listed below. A SID chip has one mixed audio output, so its three oscillators share that output placement. The intended listening WAV applies `L = 0.5 A + 0.35 B`, `R = 0.5 A + 0.65 B` through the [shared presentation helper](../../../scripts/prepare-dual-listening.py), checked by the [case audio guard](../../../scripts/studies/rambo/prepare-ensemble-listening.py). This centers the faithful group and gives the support group a rightward accent. The SID export declares the two chip addresses and score engines; this arbitrary listening matrix is not encoded as hardware per-voice panning. A hardware/player setup that routes chip A left and chip B right will therefore play the raw group separation until it applies the documented mix.

The [arrangement config](arrangement.json) names source sections, instrument entry points, register limits and articulation. The [preparer](../../../scripts/studies/rambo/prepare-ensemble.py) executes the retained [source graph](../../rambo-loader.json) from initialization, reads actual note-entry patch states and derives an independent secondary graph. The source's explicit voice-3 chord programs from calls 2354–7474 provide the harmonic contract. Suspensions, inversions, augmented colors and dominant sevenths remain their actual source pitch-class sets; the preparer does not replace them with assumed major/minor triads. Before that section, the low support follows the source voice-3 anchor classes. It returns during the closing voice-2 bass-root groups at calls 9010–10034. The opening effects, later alternating bass figure and final source release have room without added support.

## Musical roles and evidence

| SID B voice | Role and instrument basis | Calendar and departure |
| --- | --- | --- |
| B1 | Low sustained pulse using the source bass patch observed on voice 2 at call 2354. Preserve its computed PWM; use AD/SR `$48/$57` and disable pitch motion. | Revoice the existing anchor/chord tones into native pitch indices 24–35. Sustain across repeated source attacks instead of copying the bass rhythm. |
| B2 | Inner triangle using the source lead's note-entry mechanism at call 1763, with AD/SR `$68/$67`; disable pitch and irrelevant pulse motion. | Choose a different actual chord tone in indices 36–47, minimizing movement between chord bodies. Sound only during explicit source chord sections. |
| B3 | Pulse swell using the later tonal voice-3 patch at call 7986. Preserve its slower PWM; use AD/SR `$38/$57` and disable pitch motion. | Choose a third actual chord tone in indices 43–54 on a source chord-row onset halfway through alternate harmonic regions. Its 48–64-call span provides body and release rather than a ticking percussion attack. |

The instrument mechanisms come from [Galway's executed Rambo programs](../../../docs/research/composition/instruments/rambo-decoded-programs.md). The [accepted Flashdance stereo lesson](../../../docs/research/composition/flashdance-preparation.md#deliberate-dual-sid-interpretation) guides the arrangement boundary: validate sustained support through the entire chord span and avoid an independent rising reply. Its acceptance does not establish that these new Rambo patches or parts work musically.

The deterministic arrangement contains 56 low notes, 42 inner notes and 19 swells. These are deliberate sustained/revoiced source-derived additions, not three copies of the original parts. The main phrase is seconds 88–104, where B1 and B2 each have 802 active calls and B3 has 192. Seconds 32–48 provide an additional sparse entrance comparison. Exact pitch indices retain the source table's native tuning rather than claiming concert-pitch retuning.

Each support note declares its gate-off and lifetime boundary. The whole sounding span, including its reserved release, must stay inside contemporaneous source harmony. The numeric model checks the actual frequency, gate bit and active lifetime on every call against that calendar. A following note may replace a prior tail at the boundary; otherwise the native lifetime clears the oscillator. The support's final per-voice writes occur at calls 10034, 7474 and 7346, so the source's final held/releasing gesture remains exposed. These checks establish execution and pitch membership, not natural-sounding articulation or musical quality.

## Reproduce

Install the [local dependencies](../../../docs/setup/local-setup.md). From the repository root, derive the editable secondary score and its proof into a fresh local directory:

```sh
python3 scripts/studies/rambo/prepare-ensemble.py songs/studies/rambo-ensemble/arrangement.json --output build/rambo-ensemble-preparation
PYTHONPATH=.tools/test-deps python3 scripts/compose-rambo-dual.py songs/rambo-loader.json build/rambo-ensemble-preparation/secondary.json --output build/rambo-ensemble-export
```

The preparer writes `secondary.json`, `arrangement-proof.json`, `source-note-events.json.gz` and `support-note-events.json.gz`. The proof retains every source row used by each harmonic region, patch origins, the note calendar, ending state and representative phrase coverage. The compressed ledgers retain the complete source note/patch observations and all pitched additions. The compiler runs two independent engines and relocates the secondary chip to `$D420`; these files are generated local outputs, not tracked downloads.

The target is PAL, two MOS6581 chips at `$D400/$D420`, subtune 1, one play call per 19,656 cycles. Both descriptions retain the complete 11,000-call verification range; full renders cover 225 seconds. The [listening recipe](../../../config/listening/rambo-ensemble.json) and [publisher selection](audition.json) prepare a matched three-voice/six-voice phrase, a separate ending and both complete versions. Full CPU/VICE agreement, audio contribution checks, final silence and human acceptance are separate evidence.

Run the complete verification/render/presentation pipeline and publish the local listening filenames with:

```sh
python3 scripts/listening-package.py config/listening/rambo-ensemble.json --output build/rambo-ensemble-v1
python3 scripts/publish-listening.py build/rambo-ensemble-v1/run.json --selection songs/studies/rambo-ensemble/audition.json --output build/rambo-ensemble-listening
```

The faithful full comparison has gain 0.5 in both channels, matching the centered candidate primary contribution. No independent channel or stem normalization changes the ensemble. Phrase A/B matching uses one scalar for each complete stereo clip. The main audition files are `three-then-six-phrase.ab.wav`, `three-then-six-ending.ab.wav`, `faithful-dual-mono-full.wav` and `ensemble-centered-full.wav`; the raw two-chip render and chip-B omission comparisons are diagnostics.

The role-contribution diagnostic renders SID B from initialization for 104 seconds, once unchanged and once with each role's control mask omitted. Its CPU prefix covers 5,300 calls; the main two-chip export separately covers all 11,000 calls. Residual energy in seconds 88–104 shows that each role changes the rendered signal; shared chip behavior means these differences are not isolated stems, and signal contribution does not prove perceptual benefit. The B/A RMS review band of 0.2–0.8 is a warning for this audition only, not a general balance target. No automatic per-role or per-chip normalization follows from it. See the [comparison contract](../../../docs/workflows/audio-comparisons.md#verify-a-two-chip-presentation).

## Verified delivery

The [retained evidence](../../../evidence/rambo-ensemble/README.md) records the complete 2026-10-15 run: 106,400 ordered stores across 11,000 calls agree in CPU and VICE, with ten named-state checkpoints and a maximum 7,995 cycles per 19,656-cycle frame. All 9,922,500 centered PCM frames match the declared matrix; clipping, source closing-body coverage and final-tail checks pass. The 18-stage fresh run took 245.240 seconds and its unchanged cached repeat 0.913 seconds. This measures pipeline execution, not total arrangement effort or musical success.

The local review package is `build/rambo-ensemble-listening/`: `three-then-six-phrase.ab.wav` contains the faithful version first and expanded ensemble second over source seconds 88–104, with a half-second separator; `three-then-six-ending.ab.wav` compares seconds 205–225. Full files are `faithful-dual-mono-full.wav` and `ensemble-centered-full.wav`. Phrase matching applies one scalar to each stereo clip: reference 1.0, ensemble 0.8720819675; the full files retain their declared mix gains. Raw chip separation and support-only audio are separately labelled diagnostics. That package is the first reviewed baseline; see the subsequent feedback and revision below.

## Resource-informed revision

The [listener's feedback](listening-review.json) on the first ensemble was: “Not too much added weight and space, I am not sure actually. And all sound is centered, no instrument clearly left or right.” This does not approve the added roles or establish an ending verdict. The original matrix puts the whole faithful trio in the center and no group distinctly left. A separate placement-only diagnostic keeps the same six-voice render and compares its current mix with direct chip separation; it is internal evidence, not the proposed musical solution.

The user clarified the stronger purpose: understand the compromises the master faced on one SID and use extra resources to develop the constrained musical roles. Follow the [standing arrangement method](../../../docs/research/sid/dual-sid.md#expand-the-musical-capacity-not-only-the-stereo-image) and [composer accounts](../../../docs/research/composers/hubbard-galway.md#composer-accounts-for-expanding-limited-voices). The [retained resource audit](../../../evidence/rambo-resource-audit/README.md) establishes these candidates:

| Executed mechanism | Possible musical expansion and its limit |
| --- | --- |
| Source voice 3 serializes chord tones through one oscillator during calls 2354–7474; repeated notes share its envelope. | Independently sustain selected actual chord tones while preserving the characteristic arpeggio. Four-pitch-class harmonies still require declared allocation/reduction; the source does not prescribe sustained voicings. |
| Lead attacks at calls 2483 and 2611 replace a released but still-live prior sound program. | **Rejected before rendering:** moving the 2483 attack would expose tails across incompatible chord changes. Other bounded candidates also fail harmony or introduce a large pitch bend against the held note. Software lifetime is not evidence that the release should be extended. |
| Eleven short pulse attacks starting at calls 2227–2299 descend by 80 frequency-word units per call. | Investigate a tonal-percussion role before proposing drum expansion. No noise or volume stream does not mean no percussion; the source passage has no explicit drum label. |
| Later A1 sync and final ring modulation use A3. | Preserve the pair. Extra voices must not destroy the timbral dependency to achieve spatial separation. |

The [bounded release screening](../../../evidence/rambo-resource-audit/README.md#release-hypothesis-rejected-before-rendering) rejected the first hypothesis before a new audition. The resulting comparison extends B3 from spaced swells to a held third source chord tone across all chord regions; B1, B2 and the complete faithful trio remain unchanged. This directly tests independent chord bodies while retaining the original arpeggio. Both versions use raw chip separation for the causal comparison, so width and added sustain are not conflated. The previous generic support remains an unaccepted baseline. Centered individual roles remain a separate native-allocation requirement; the hard split is not presented as solving that requirement.

**Model-assistance review after feedback:** no model call is useful here. Human spatial feedback, explicit matrix algebra, source execution and composer testimony identify the next test; current models are not qualified to decide its musical merit. The subsequent review is recorded with the [chord-body trial](../rambo-chord-expansion/README.md#rights-and-listening-status).

The [completed chord-body trial](../rambo-chord-expansion/README.md#verified-listening-package) received positive phrase feedback: the added support supplies useful fullness while keeping the melody clear. Retain that direction; the complete arrangement is available for full-song review. Its raw chip grouping and measured shared-host PCM differences are documented separately from source-score preservation.

## Rights and review

Galway composed, arranged and programmed the loader in 1985; the historical source credits Ocean Software. This derivative loader arrangement and its generated secondary score and complete note ledgers retain Galway's credit, modification notice and [GNU GPL version 3](../../../samples/rambo-loader/LICENSE) under the [title-specific loader grant](../../../samples/rambo-loader/README.md). Independently authored reusable tools retain [MIT](../../../LICENSE) separately. This does not clear other subtunes from the original Rambo archive. Complete audition SID/audio stay local while listening review is pending.

**Model-assistance checkpoint:** reviewed before the first ensemble audition; no model call is useful for deciding the weight, phrasing or spatial value of these additions. Existing bounded audio-model trials do not qualify a model for that preference judgment. Human review of the representative phrase, separate ending and complete performance remains authoritative. Reassess after feedback and before closing the case.
