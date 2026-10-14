# Daglish contrast: Deflektor and Trap

The [required Daglish check](../study-plan.md#required-contrasting-references-for-the-six-composers) now has a pinned second reference, bounded source audio and executed register evidence. The first 6,000 calls distinguish the two works' waveform and filter choices and show separately timed articulation. The route-only diagnostic now has a listening observation: bypass sounds clearer/crisper and possibly louder. The listener hears the 24–34 second Trap excerpt as driven mostly by a moving melody and hears development in the 40–52 second excerpt. No cowbell identification, full Trap form or composer-wide synthesis signature is claimed.

## Source, subtune and credit boundary

The [download registry](../../../config/local-assets.json) pins the unchanged [HVSC Trap SID](https://www.hvsc.de/download/C64Music/MUSICIANS/D/Daglish_Ben/Trap.sid) at SHA-256 `c8954d2020bbd3b3d7dd75a6e376057e36816591042275ae864ea8ff2c034e20`, downloaded on 2026-10-14 into ignored `.local/research/trap/Trap.sid`. The [selected-source receipt](../../../evidence/daglish-contrast/sourceB-selection.json) preserves URL, bytes, metadata, admission and rendering settings.

| Field | Trap selection |
| --- | --- |
| Title / author / release | Trap / Ben Daglish / 1986 Alligata |
| Format / bytes | PSID v2 / 4,478 |
| Subtunes | Two; explicitly select default #1 |
| Declared model / clock / timing | MOS6581 / PAL / VBI, flags `$0014`, speed word zero |
| Payload | Embedded load `$BF00`, 4,352 bytes, end `$D000` exclusive |
| Init / play | `$BFE0` / `$C002` |
| Controlled callable host | `$0400–$05FF`, bank `$36`; default `$C000` host overlaps source |

Daglish describes Trap's introductory and concluding material and orchestral ambition in [Neil Carr's 2001 interview](https://remix64.com/interviews/interview-ben-daglish.html). This author account motivates the contrast; it does not map PSID subtunes or prove execution boundaries. Cached HVSC STIL v85 independently has an entry for **#1**, identifies its We M.U.S.I.C. *The Gladiator* demo connection, and attributes a passage at **3:35–3:54** to **Jeff Wayne's “Eve of the War” from War of the Worlds**. Preserve that source-composition credit alongside Daglish's C64 score credit. The [STIL provenance](../../../evidence/daglish-contrast/stil-provenance.json) retains the complete entry, original line boundaries and the cache SHA-256 `b1ef3584a5b3501e2bbd2ef056d6539a1bbee7933a7828537c3946c1b16cde43`. The attributed passage lies outside this 120-second capture and has not been matched by execution or listening here.

## Bounded execution and source comparison

The checked-in [intake spec](../../../config/reference-intake/trap-contrast.json) selects original Deflektor #1 as source A and original Trap #1 as source B, both with the low-RAM host, **6,000 controlled CPU calls** and separate **120-second initialized renders**. The [run receipt](../../../evidence/daglish-contrast/run.json) and [generated recipe](../../../evidence/daglish-contrast/recipe.json) retain the exact dependencies and outputs. An unchanged repeat reused all 11 stages. CPU calls span approximately **119.702 seconds** at the controlled host's 50.124573 Hz; renderer snapshots are observations after rendering iterations and are not the CPU ledger or bus timestamps.

| Evidence | Deflektor #1 | Trap #1 |
| --- | --- | --- |
| Initialization SID stores | 0 | 24 |
| Play SID stores, calls 0–5,999 | 114,928 | 150,147 |
| Maximum call cost | 2,480 cycles | 3,424 cycles |
| Declared host budget | 19,656 cycles | 19,656 cycles |
| Source render | 120 seconds, 44.1 kHz mono PCM16 | 120 seconds, 44.1 kHz mono PCM16 |
| Signal guard | Nonzero AC signal; zero PCM rail samples | Nonzero AC signal; zero PCM rail samples |

The [Deflektor audit](../../../evidence/daglish-contrast/sourceA-audit.json), [Trap audit](../../../evidence/daglish-contrast/sourceB-audit.json) and complete ordered [Deflektor stores](../../../evidence/daglish-contrast/sourceA.writes.json.gz) / [Trap stores](../../../evidence/daglish-contrast/sourceB.writes.json.gz) retain the executable observation. Separate [Deflektor rendering metadata](../../../evidence/daglish-contrast/sourceA-measure.json) and [Trap rendering metadata](../../../evidence/daglish-contrast/sourceB-measure.json) preserve audio fingerprints, settings and measurements. These are modeled source renders, with no original-game timing, physical-chip equivalence or listening verdict implied.

The private [listening index](../../../build/reference-intake/trap-contrast/listening.md) links both complete bounded renders and three original-source comparisons: **0–20 seconds**, **40–52 seconds** and **96–108 seconds**. Each plays Deflektor then a 0.5-second silence then Trap, retaining original levels and unity gain. The first window includes Deflektor's staged candidate beginning around call 641 and Trap's filtered voice-2 entrance around call 800. Equal time windows compare different works; they are not aligned reconstruction A/Bs or verified corresponding sections. The later windows are sampling points for listening, without assigned formal labels.

## Three falsifiable findings and their limits

| Primary finding / test | Executed Trap result | Current conclusion |
| --- | --- | --- |
| Deflektor has a recurring staged percussion candidate whose control progression includes noise → triangle → triangle with SYNC/RING → noise. Does the selected Trap passage use that same control-stage recipe? | Every captured Trap voice control is `$00`, `$40` or `$41`: no noise, triangle, SYNC or RING selection occurs in calls 0–5,999. | The specific staged recipe is **tune-specific within the compared passages**. The listener hears the moving melody as Trap’s main rhythmic carrier at 24–34 seconds: the exact Deflektor percussion recipe is not needed for that perceived drive. The precise historical cowbell identity remains unresolved. Absence here is not absence from the whole tune. |
| Deflektor's shared resonance macros write `$D417`, but its observed routing bits and `$D418` filter modes remain clear. Does that inactive filter path transfer to Trap? | Trap writes `$D418=$1F`, then `$D417=$82` on call 601; voice 2 subsequently has gated, nonzero-pitch pulse notes while low-pass routing remains active. | An inference that these two Daglish works share an inactive filter path is **contradicted**. Preserve the Deflektor-specific observation; do not infer sound from resonance writes without mode/routing. The route-only comparison below establishes an audible tone/prominence difference in one passage, without a preference or portability verdict. |
| Deflektor's independently scheduled score voices do not all articulate at the same calls. Does Trap likewise avoid one shared gate schedule? | Known gate rises are 10 / 104 / 30 for voices 1 / 2 / 3. Voice 2 has 95 rising-edge calls absent from voice 1; voice 3 has 21 absent from voice 1. For example, voice 2 rises at 800 and 815 while the other voices do not. | **Separate articulation is supported across these bounded captures.** Gate edges are not a decoded note score: legato pitch changes and release tails prevent these counts from identifying note totals, bass/lead roles or musical independence. The listener hears development at 40–52 seconds, alongside the executed changes described below. This supports a developing texture in the excerpt; it does not perceptually identify numbered voices or prove their full-song roles. |

The [complete census](../../../evidence/daglish-contrast/census.json.gz), generated by the [source-specific probe](../../../scripts/studies/deflektor/probe-contrast.py), retains control counts, ordered transitions, gate-edge records, pairwise call sets and filter intervals. Unwritten registers remain unknown; the probe does not infer reset state or count a first unknown gate-set store as a known rising edge. The primary waveform attribution remains the [Deflektor candidate and context evidence](deflektor-preparation.md#sound-record-fields-and-staged-waveform-candidate).

### Active filter, not initialization residue

The initialized [call-601 instruction trace](../../../evidence/daglish-contrast/filter-enable.trace.json.gz) locates all four filter stores at the shadow writer `$C01A`: `$D418=$1F` at instruction-start cycle 2,054, `$D417=$82` at 2,068, `$D416=$3C` at 2,082 and `$D415=$00` at 2,096. Mode and route are therefore simultaneously active from the second store; voice 2 is still ungated there. The source establishes cutoff **480** after a single change from zero and retains it for the rest of this captured interval. This is not evidence of a filter sweep.

The initialized [call-815 trace](../../../evidence/daglish-contrast/filtered-note.trace.json.gz) records a direct gate-clear store at `$C197`, then the writer's active mode/route/cutoff, `$D40B=$41`, and voice-2 frequency high/low `$06/$27` through `$C01A`. The resulting pitch word is `$0627`, with the filter route active; this is actual play-path configuration rather than untouched initialization state. The census retains 311 voice-2 control transitions during the active filter interval. Both narrow traces match their corresponding complete intake-ledger stores, including order and instruction-start cycles. They share the callable CPU oracle; they are not a separate VICE or hardware check. The route-only causal diagnostic below adds a distinct intervention to this initial observation.

### Route-only causal diagnostic and listening observation

The [diagnostic script](../../../scripts/studies/deflektor/trap-filter-diagnostic.py) now tests the configured voice-2 filter path through a private source-data intervention. At call 601, command `$17` at `$C935` dispatches to the `$C394` routing setter. Its parameter reader `$C080` consumes **`$C936=$82`** at instruction-start cycle 729, and the setter copies it to shadow `$C5B6` at cycle 743. The `$C017/$C01A` writer then emits that shadow as `$D417`. Clear only bit `$02` in that one source-data cell, **`$82→$80`**, retaining resonance, other routing bits, filter mode/cutoff and all source header bytes. The original pinned SID remains unchanged; the private bypass is an attribution diagnostic, with SHA-256 `7889b3331fcfa622d679e8f8b933c222fd7862bf809803b09f66d0a798fa481a`.

Fresh initialized executions of original and bypass each cover **1,600 controlled PAL calls**. The [execution receipt](../../../evidence/daglish-contrast/filter-diagnostic/receipt.json) and complete [original record](../../../evidence/daglish-contrast/filter-diagnostic/original.json.gz) / [bypass record](../../../evidence/daglish-contrast/filter-diagnostic/bypass.json.gz) verify all **40,047 store positions**, including 24 initialization stores. Exactly **999 routing values**, calls 601–1,599, change from `$82` to `$80`; every phase, call, instruction-start cycle, address and ordering position agrees. All other values—including every voice's frequency, pulse width, gate/control and ADSR, plus cutoff/mode/volume—agree. All **4,862 score-command reads** also agree in source address, value, order and timing. The [changed-routing record](../../../evidence/daglish-contrast/filter-diagnostic/changed-routing.json.gz) retains every changed store. This establishes the source byte's causal contribution to routing within this controlled scope; instruction-start agreement does not establish exact SID bus cycles or original-game scheduling.

The [diagnostic recipe](../../../config/listening/trap-filter-diagnostic.json) automates that execution proof, four focused guards, separate **32-second initialized PAL/MOS6581 renders**, signal checks and a **16–28 second same-material comparison**. Both full renders are 44.1 kHz mono PCM16 with nonzero AC signal and zero PCM rail samples. The [contextual difference](../../../evidence/daglish-contrast/filter-diagnostic/difference.json) measures 529,198 changed samples out of 529,200 in the phrase, with AC RMS difference **3,634.713 PCM16 units**. The [comparison receipt](../../../evidence/daglish-contrast/filter-diagnostic/comparison.json) confirms common unity gain, no normalization, original first, a 0.5-second gap and bypass second. This is a nonzero modeled signal contribution from the route intervention; audible usefulness and preference remain with the listener. No filter portability or extended-form claim follows.

Stable local audition files are [original Trap, initialized 32 seconds](../../../build/trap-filter-listening/trap-original-32s.wav), [voice-2 filter bypass, initialized 32 seconds](../../../build/trap-filter-listening/trap-voice2-filter-bypass-32s.wav), and [original then bypass, 16–28 seconds](../../../build/trap-filter-listening/trap-original-then-voice2-filter-bypass-16to28s.ab.wav). The [audition provenance](../../../evidence/daglish-contrast/filter-diagnostic/audition-sources.json) preserves their hashes and exact recipe inputs. Submitted listening question: **What difference do you hear in that supporting sound—tone, prominence or balance?** The comparison plays the original first and bypass second; the separate files retain the same material and levels for replay.

Reproduce the package and publish stable files into a fresh local folder:

```sh
python3 scripts/listening-package.py config/listening/trap-filter-diagnostic.json --output build/trap-filter-diagnostic
python3 scripts/publish-listening.py build/trap-filter-diagnostic/run.json --selection config/listening/trap-filter-diagnostic.audition.json --output build/trap-filter-listening-new
```

An unchanged repeat reused all seven stages. The [package receipt](../../../evidence/daglish-contrast/filter-diagnostic/run.json) preserves output fingerprints and reuse; original and private patched binaries and every source-containing WAV remain ignored. The [guard log](../../../evidence/daglish-contrast/filter-diagnostic/guards.log) covers one-byte source preservation, the route-only value boundary, ordered instruction timing, and rejection of identical/DC-only signal differences. Model-assistance review after feedback on 2026-10-14: the exact execution/signal guards and human observation answer this probe. No model call adds qualified evidence about subtle musical tone or balance; models remain experimental. Reassess at contrast closure or a musical revision.

### Listener observation and reusable lesson

On 2026-10-14 the listener reported: **“the voice 2’s filter bypassed seems clearer, crisp, maybe even loader.”** The [structured review](../../../evidence/daglish-contrast/filter-diagnostic/listening-review.json) retains the exact words and frozen comparison hash. Interpret this as clearer/crisper tone and possibly greater perceived loudness (“loader” likely means “louder”), without inferring a preference or an instruction to change Trap.

The same phrase’s [measurement receipt](../../../evidence/daglish-contrast/filter-diagnostic/comparison.json) gives full-mix AC RMS 2,873.426 for original and 2,891.375 for bypass: only **0.054 dB** higher, while the peak falls from 8,907 to 7,976. These are signal measurements, not perceptual loudness measurements. The listener’s clearer, possibly louder impression therefore must not be reduced to a large overall gain increase. In this modeled passage, routing one supporting voice through low-pass changes its audible character and prominence while the rest of the executed score and sound parameters stay fixed.

Reusable decision: when a support part needs to sit back or become clearer, test its filter route in the full mix before changing global gain or adding parts. Retain the original as the reference and judge the desired role; brighter/clearer is not automatically musically better. This is a demonstrated diagnostic and a bounded listening observation, not a newly accepted instrument or a universal 6581 filter setting.

## Transition selection and listening observations

The filter observation alone did not settle the planned comparison of recurring percussion, independent supporting roles and development. Two changes in the retained 6,000-call Trap ledger selected short listening windows, now reviewed, without expanding to another complete reconstruction:

| Controlled call / approximate time | Executed change | Selected source window and question |
| --- | --- | --- |
| 1,310 / 26.14 seconds | Voice 3 changes from pitch `$0209`, pulse `$0641`, AD `$FF` at call 1,309 to `$3138`, `$0300`, AD `$CC`, with a fresh gate. Voice 1 remains sustained; voice 2 continues its independently timed articulation. | 24–34 seconds: does the changed upper part enter as a distinct line, rhythmic support or another texture, and how does its role contrast with Deflektor’s recurring percussion? |
| 2,100 / 41.90 seconds | Voice 1 regates for the first time since call 0, changes pitch `$0421→$03A8` and resets pulse `$0950→$0000`. The other voices continue their score activity; voice 3 also changes pitch at this call. | 40–52 seconds: does this sound like a change in texture or phrase while the supporting pulse continues, or mostly repetition? |

These are executed parameter changes, not formal section labels or listener attribution to numbered voices. Call times use the controlled PAL cadence and are approximate positions in the initialized render. The two works’ clips compare arrangement choices; equal time windows do not imply corresponding score passages or reconstruction fidelity. Full Trap introduction/returns/ending and its later Jeff Wayne quotation remain outside the captured scope.

The [transition recipe](../../../config/listening/trap-transitions.json) reuses the verified initialized source renders and runs two narrow initialized instruction traces. The call-1,309–1,311 trace agrees with all **76** ordered source stores; the call-2,099–2,101 trace agrees with all **79**. The [retained trace agreement](../../../evidence/daglish-contrast/transitions/traceLedgerAgreement.json.gz) preserves both checks. This is fresh trace capture against a retained ledger, not a new complete source capture or an independent VICE proof. The source-window stage resolves the intake’s current receipt paths, checks their recorded hashes and lets the existing intake API verify each source WAV; no historical attempt path is embedded in the recipe.

The [fresh run](../../../evidence/daglish-contrast/transitions/cold-run.json) completed in **35.10 seconds**; the [unchanged repeat](../../../evidence/daglish-contrast/transitions/hot-run.json) took **0.29 seconds**, reusing all four stages. The 40–52 second pair is byte-identical to the prior intake clip. [Audition provenance](../../../evidence/daglish-contrast/transitions/audition-sources.json) retains the stable names and fingerprints.

Published originals are [Deflektor then Trap, 24–34 seconds](../../../build/trap-transitions-listening/deflektor-then-trap-24to34s.ab.wav) (20.5 seconds total) and [Deflektor then Trap, 40–52 seconds](../../../build/trap-transitions-listening/deflektor-then-trap-40to52s.ab.wav) (24.5 seconds total). Each retains unity gain and a 0.5-second gap; individual original excerpts are beside the pairs. The first question asks how Trap’s rhythm/support differs from Deflektor’s recurring percussion; the second asks whether Trap’s later passage develops in phrase/texture or mainly repeats. The [exact submitted questions and audition hashes](../../../evidence/daglish-contrast/transitions/listening-submission.json) preserve the review boundary. The [subsequent listening review](../../../evidence/daglish-contrast/transitions/listening-review.json) records both answers without altering that original submission. At 24–34 seconds: **“In Trap, mostly the  a moving melody”**. At 40–52 seconds: **“Trap develops during the excerpt”**. These observations establish perceived melodic drive and local development, without a preference between the songs or separate acceptance of every supporting part. Model-assistance review at first audition and after feedback: no call, because models remain unqualified to resolve these musical-role judgments; the human observations supply the missing perceptual evidence.

Reproduce after the pinned source setup described below, then publish into a fresh folder:

```sh
python3 scripts/reference-intake.py run config/reference-intake/trap-contrast.json --output build/reference-intake/trap-contrast
python3 scripts/listening-package.py config/listening/trap-transitions.json --output build/trap-transitions
python3 scripts/publish-listening.py build/trap-transitions/run.json --selection config/listening/trap-transitions.audition.json --output build/trap-transitions-listening-new
```

## Scoped corroboration outcome

The required second-reference musical observations are now present. Deflektor’s staged percussion recipe does not generalize to the captured pulse-only Trap passages. The listener describes Trap at 24–34 seconds mainly as a moving melody and hears development at 40–52 seconds. Separate articulation schedules are supported by execution, and the route-only diagnostic has an audible tonal effect. Together these refine the primary study into tune-specific sound choices and a broader arrangement lesson: musical drive and development can come from melodic motion and changing voice treatment, without reusing the same percussion patch.

This does not establish perceptual independence or usefulness of every background part, listener identification of numbered SID voices, timbre as the sole cause of development, or the form of the whole Trap tune. Those limits remain explicit; the bounded contrast does not require a second complete reconstruction. No new Trap instrument or gesture is promoted. The accepted Deflektor transfer remains the different-material demonstration for the existing reusable programs.

The user requested a blind model check against these observations on 2026-10-14 and explicitly approved the audio upload. The [completed single-clip calibration](../audio-assessment.md#trap-melodic-motion-and-development-calibration) found Qwen agreeing with both human observations and passing silence/repetition controls (4/4); Gemini disagreed about development and fabricated music on silence (2/4). This completes the requested model-assistance review, without granting either model musical acceptance authority. Prefer Qwen only for experimental coarse descriptions; reassess on an independent passage rather than tuning against these answers.

**M6 bounded corroboration is complete.** The primary reconstruction and familiar transfer retain their existing acceptance; this contrast narrows waveform/filter claims and supplies scoped articulation, transition and listening evidence. Full Trap form, exact cowbell identification and perceptual attribution of every background part remain unverified. Continue with the required [Shades/Giana contrast](huelsbeck-contrast.md).


## Reproduction and remaining evidence

Run the checked-in [verification recipe](../../../config/listening/daglish-contrast-verification.json) from the repository root, using the existing pinned renderer and CPU dependencies:

```sh
python3 scripts/setup-project.py --only references --include deflektor --include trap
python3 scripts/listening-package.py config/listening/daglish-contrast-verification.json --output build/daglish-contrast-verification
```

The recipe automates the source intake, initialized call-601 and call-815 traces, their agreement with the complete ordered ledger, the census and focused guards. Its first stage creates a fresh nested intake below its immutable attempt directory; the complete nested directory is a declared output, so outer cache reuse checks source audio, snapshots, ledgers and receipts together. The census declares that directory as an input because it reads the ledger paths recorded inside the nested run. Declared dependencies include the registered sources and pins, clock/profile/host/CPU modules, py65, renderer binary/source/library, intake/runner/audio modules, probe and tests. The runner disables bytecode writes for these fingerprinted dependencies.

Open `build/daglish-contrast-verification/listening.md` for the nested source-listening index, run receipt, traces and census. An unchanged repeat verifies and reuses all five outer stages; choose a fresh output directory for a genuinely new capture. The nested source renders retain the [same bounded source selections](../../../config/reference-intake/trap-contrast.json), and every result remains separate from listening acceptance. The earlier retained evidence documents the standalone intake; the wrapper is the repeatable command for future checks.

Verified on 2026-10-14: the [fresh wrapper run](../../../evidence/daglish-contrast/wrapper-cold-run.json) completed in **61.01 seconds**, and the [unchanged repeat](../../../evidence/daglish-contrast/wrapper-hot-run.json) completed in **0.19 seconds**, reusing all five stages. The [comparison receipt](../../../evidence/daglish-contrast/wrapper-validation.json) establishes byte identity with the earlier complete ordered ledgers, source renders and narrow traces, plus agreement of the complete numeric census. The [nested intake run](../../../evidence/daglish-contrast/wrapper-intake-run.json), [wrapper census](../../../evidence/daglish-contrast/wrapper-census.json.gz) and [guard log](../../../evidence/daglish-contrast/wrapper-guards.log) preserve those automated results without source audio. These are measured workflow times for this host and scope, not a synthesis-performance or listening claim.

The four focused guards cover unknown initial state, multiple gate edges within one call, simultaneous mode/routing admission and loss of ordered trace stores. Original SIDs, source WAVs and source-containing comparisons remain outside Git and LFS. The reviewed evidence selection retains metadata, complete ordered stores, renderer snapshots and the narrow instruction traces, with no audio or original payload.

The selected source windows now have the listening observations above. Map later Trap transitions, returns and ending before making an extended-form claim; the author account and first 120 seconds cannot settle that question. The Jeff Wayne passage also needs its separate attribution boundary when reaching that material. No new instrument or gesture is promoted from this intake; any later promotion still requires an editable different-material example, a same-material reference and listening acceptance.

Model-assistance reviews on 2026-10-14 account for the diagnostic audition, feedback and completed closure calibration above. No model replaces exact register evidence or human acceptance. Reassess on an independent musical passage or a substantive revision; use the [standing audio-assessment rule](../audio-assessment.md#use-and-reassess-model-assistance).
