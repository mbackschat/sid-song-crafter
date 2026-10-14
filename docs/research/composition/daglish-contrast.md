# Daglish contrast: Deflektor and Trap

The [required Daglish check](../study-plan.md#required-contrasting-references-for-the-six-composers) now has a pinned second reference, bounded source audio and executed register evidence. The first 6,000 calls distinguish the two works' waveform and filter choices and show separately timed articulation. This is preparation and a scoped technical comparison; the required musical contrast remains open until listening establishes the recurring-percussion role, supporting parts and sectional development. No cowbell identification, full Trap form or composer-wide synthesis signature is claimed.

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
| Deflektor has a recurring staged percussion candidate whose control progression includes noise → triangle → triangle with SYNC/RING → noise. Does the selected Trap passage use that same control-stage recipe? | Every captured Trap voice control is `$00`, `$40` or `$41`: no noise, triangle, SYNC or RING selection occurs in calls 0–5,999. | The specific staged recipe is **tune-specific within the compared passages**. Its cowbell identity and whether another Trap texture serves the same rhythmic purpose remain unverified by listening. Absence here is not absence from the whole tune. |
| Deflektor's shared resonance macros write `$D417`, but its observed routing bits and `$D418` filter modes remain clear. Does that inactive filter path transfer to Trap? | Trap writes `$D418=$1F`, then `$D417=$82` on call 601; voice 2 subsequently has gated, nonzero-pitch pulse notes while low-pass routing remains active. | An inference that these two Daglish works share an inactive filter path is **contradicted**. Preserve the Deflektor-specific observation; do not infer sound from resonance writes without mode/routing. This does not establish the audible value or portability of Trap's filter. |
| Deflektor's independently scheduled score voices do not all articulate at the same calls. Does Trap likewise avoid one shared gate schedule? | Known gate rises are 10 / 104 / 30 for voices 1 / 2 / 3. Voice 2 has 95 rising-edge calls absent from voice 1; voice 3 has 21 absent from voice 1. For example, voice 2 rises at 800 and 815 while the other voices do not. | **Separate articulation is supported across these bounded captures.** Gate edges are not a decoded note score: legato pitch changes and release tails prevent these counts from identifying note totals, bass/lead roles or musical independence. Supporting-voice usefulness and sectional roles remain unverified. |

The [complete census](../../../evidence/daglish-contrast/census.json.gz), generated by the [source-specific probe](../../../scripts/studies/deflektor/probe-contrast.py), retains control counts, ordered transitions, gate-edge records, pairwise call sets and filter intervals. Unwritten registers remain unknown; the probe does not infer reset state or count a first unknown gate-set store as a known rising edge. The primary waveform attribution remains the [Deflektor candidate and context evidence](deflektor-preparation.md#sound-record-fields-and-staged-waveform-candidate).

### Active filter, not initialization residue

The initialized [call-601 instruction trace](../../../evidence/daglish-contrast/filter-enable.trace.json.gz) locates all four filter stores at the shadow writer `$C01A`: `$D418=$1F` at instruction-start cycle 2,054, `$D417=$82` at 2,068, `$D416=$3C` at 2,082 and `$D415=$00` at 2,096. Mode and route are therefore simultaneously active from the second store; voice 2 is still ungated there. The source establishes cutoff **480** after a single change from zero and retains it for the rest of this captured interval. This is not evidence of a filter sweep.

The initialized [call-815 trace](../../../evidence/daglish-contrast/filtered-note.trace.json.gz) records a direct gate-clear store at `$C197`, then the writer's active mode/route/cutoff, `$D40B=$41`, and voice-2 frequency high/low `$06/$27` through `$C01A`. The resulting pitch word is `$0627`, with the filter route active; this is actual play-path configuration rather than untouched initialization state. The census retains 311 voice-2 control transitions during the active filter interval. Both narrow traces match their corresponding complete intake-ledger stores, including order and instruction-start cycles. They share the callable CPU oracle; they are not a separate VICE or hardware check, and no causal filter intervention has been performed.

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

Listen to the prepared source windows to assign actual rhythmic and supporting roles, then choose the smallest targeted execution/intervention needed for any uncertain mechanism. Map later Trap transitions, returns and ending before making an extended-form claim; the author account and first 120 seconds cannot settle that question. The Jeff Wayne passage also needs its separate attribution boundary when reaching that material. No new instrument or gesture is promoted from this intake; any later promotion still requires an editable different-material example, a same-material reference and listening acceptance.

Model-assistance review on 2026-10-14: no model audition is useful for these exact register questions, and model observations remain unqualified for musical acceptance. Reassess at the first representative human audition or after a musical revision; use the [standing audio-assessment rule](../audio-assessment.md#use-and-reassess-model-assistance).
