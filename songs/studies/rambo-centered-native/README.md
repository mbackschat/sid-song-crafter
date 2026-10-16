# Rambo: native duplicated lead with accompaniment on both sides

This candidate follows the listener's request after liking the complete [held-chord arrangement](../rambo-chord-expansion/README.md): move the main instrument into the middle while deliberately placing accompaniment across the two sides. It preserves the faithful first chip and copies the complete source lead to the second chip. Each SID still has one mono output. Raw A-left/B-right rendering supplies the lead to both sides through native oscillators; it does not give individual voices synthetic pan controls. The listener accepts the centered phrase and complete revised performance; the scoped verdict is recorded below.

## Allocation and musical tradeoff

| Chip/voice | Role |
| --- | --- |
| A1 | Unchanged source lead, including its complete Morse passage and native pitch/PWM programs. |
| A2 | Unchanged source bass on the left. |
| A3 | Unchanged source arpeggio and lead modulator on the left. |
| B1 | Full source A1 graph and initial data/sound, including all four code hooks, on physical oscillator 1. |
| B2 | Exact accepted inner support from the held-chord arrangement, on the right. |
| B3 | Exact accepted held-third support for 37 complete chord regions; source A3 during the two bounded dependency handoffs. |

The extra lead replaces the earlier B1 low moving-pulse anchor, including its entrance and closing support. The original A2 bass remains. This removes a layer of sustained low weight; it does not claim unchanged fullness. At the 42 chord-region entrances, that previous low layer shares the original bass's pitch class. Two regions contain later bass motion, so this observation is not a claim of whole-span duplication. B2 and the retained held-third events keep their exact accepted patches, pitches, gates and lifetimes. No new melody, drum, harmony or synthesis patch is introduced.

The lead uses hard sync with oscillator 3 during calls 4915–5427, then ring modulation during 10035–10660. Copying the lead while keeping all three previous B support parts would require seven oscillators before accounting for the modulator. This allocation uses B3 as the required source modulator during the coupled passages. Other parts may deliberately occupy the middle too: the copied arpeggio is audible in these passages.

The first B3 source segment covers calls 4914–5554, five complete held-chord regions. Whole-region boundaries avoid one-frame held-tone fragments at the exact sync edges. The remaining 37 regions retain their complete original calendars. The second segment starts with the source's actual final note/program at call 10034 and retains every later frequency/lifetime poke through natural clear at 10814. It costs no held-chord region because the accepted B3 held section has already ended at 7474.

## Mechanism and limits

The [preparer](../../../scripts/studies/rambo/prepare-centered-native.py) uses the existing graph grammar and unchanged [dual compiler](../../../scripts/compose-rambo-dual.py). B1 keeps the source's physical voice index, initial score stack, patches and Morse workspace. Its `start-morse` hook re-enters all three voices' refresh schedules; the full-range guards check B2 and B3 after this interaction rather than assuming independent score counters.

B3 calls bounded source graph segments, preserving table-note bytes, transposes, live chord banks and the source's final `poke-sound` hooks. Each handoff initializes the complete software data/sound state from the independently computed source or accepted held-role entry state. This is editable score/program execution, not SID-store replay. The evidence retains the input graphs, entry patches, note ledgers, semantic operations and every post-call software state.

Software state restoration cannot restore the SID's physical oscillator or envelope history. Before the sync handoff, B3 has played different notes from A3; both carrier/modulator phase relationships and A-then-B execution timing can affect the sound. Identical logical source programs therefore do not establish coherent phase, identical PCM or a stable perceived center. Do not change TEST bits, remove coupling or align audio to conceal those differences. Review the complete sound and the 88–104-second handoff in context. The [dual-SID guide](../../../docs/research/sid/dual-sid.md) owns the shared-chip and mixing constraints.

## Reproduce and verify

From the repository root, using a fresh output directory:

```sh
python3 scripts/studies/rambo/prepare-centered-native.py songs/studies/rambo-centered-native/arrangement.json --output build/rambo-centered-native-preparation
PYTHONPATH=.tools/test-deps python3 scripts/compose-rambo-dual.py build/rambo-centered-native-preparation/primary.json build/rambo-centered-native-preparation/secondary.json --output build/rambo-centered-native-export
PYTHONPATH=.tools/test-deps:tests python3 -m unittest rambo_centered_native_test -v
```

Preparation emits `primary.json`, `secondary.json`, `arrangement-proof.json`, three complete `*-observations.json.gz` records and three `*-note-events.json.gz` ledgers for the source, accepted baseline and variant, plus `held-note-events.json.gz`. The primary JSON is identical to the retained source. The configuration pins both the source and accepted held-chord configuration by SHA-256; the proof pins all generated descriptions. Canonical JSON fingerprints use two-space indentation and a terminal newline.

The [focused guards](../../../tests/rambo_centered_native_test.py) compare the complete 11,000-call lead store sequence, data/sound/score state and Morse state against the source; compare B2 against the accepted support; compare B3's full source-window store/state trajectories and its retained held-role trajectories outside those windows; and check all final lifetime hooks and the natural stop. Negative cases change a lead store, Morse state, final lifetime hook, held note and handoff duration. Assembly checks preserve the primary payload and disjoint callable RAM. Full CPU budget, VICE, raw stereo/mono health and listening are separate delivery gates; a numeric preparation pass does not settle them. The completed execution and signal checks are recorded below.

**Listening and model-assistance status:** complete native candidate verified through CPU, VICE and rendering; the listener accepts the compared phrase’s center image, space and fullness and the complete revised performance. No paid audio-model call is justified: current trials do not qualify a model to approve this stereo image or the support tradeoff. The post-feedback and closure reviews find no justified model call; reassess only for a new revision. Preserve the accepted complete held-chord version as the comparison baseline.

Music-derived descriptions, software-state and note records retain Martin Galway credit and the [loader's GNU GPL v3 grant](../../../samples/rambo-loader/README.md). Reusable tool code retains [MIT](../../../LICENSE) separately. Accepted distributable demo packaging follows the loader’s GPLv3 terms; original reference files remain local.

## Verified listening package

The full 225-second PAL MOS6581 candidate passes 11,000 calls, 123,221 ordered stores and ten two-engine state checkpoints. Its peak play cost is 16,169 of 19,656 PAL cycles. Headless VICE matches the complete write sequence, with a maximum cadence error of seven cycles within the nine-cycle tolerance. Raw stereo and mono-fold diagnostics have no clipped samples; both buses retain the closing body and the final second has no alternating signal. These checks establish execution and signal health, not perceived centering or musical acceptance.

Run the [14-stage recipe](../../../config/listening/rambo-centered-native.json), then publish its selected outputs locally:

```sh
python3 scripts/listening-package.py config/listening/rambo-centered-native.json --output build/rambo-centered-native
python3 scripts/publish-listening.py build/rambo-centered-native/run.json --selection songs/studies/rambo-centered-native/audition.json --output build/rambo-centered-native-listening
```

Use fresh paths when the named publication directory already exists. The recipe requires the pinned previous full render at `build/rambo-chord-expansion-listening/expanded-chord-raw-full.wav`; recreate it through the [held-chord recipe](../rambo-chord-expansion/README.md#reproduce-and-verify) if absent.

- [Phrase comparison](../../../build/rambo-centered-native-listening/previous-then-native-centered-lead-phrase.ab.wav): 88–104 seconds, previous approved arrangement first, native duplicated-lead candidate second, 32.5 seconds total. One gain applies to each entire stereo excerpt: previous 1.0, candidate 0.984877034; channel balance is preserved.
- [Complete candidate](../../../build/rambo-centered-native-listening/native-centered-lead-raw-full.wav) and [complete previous arrangement](../../../build/rambo-centered-native-listening/previous-approved-raw-full.wav): 225 seconds each, original render levels.

The standalone lead diagnostics have almost equal A1/B1 power in the submitted passage (B/A AC RMS ratio 1.00001764). Two such channels contain about 3.01 dB more total lead power than one; this is not a coherent mono-sum measurement. They are independently initialized, control-masked one-chip renders, not exact dual-render stems, and do not prove phase agreement. No patch or per-channel gain was changed to hide that distinction. Listen for the desired center and retained space rather than treating matching power as an audible verdict.

The [canonical evidence](../../../evidence/rambo-centered-native/README.md) retains full preparation/state records, CPU and VICE traces, signal checks, comparison settings and source/output fingerprints. The emitted SID SHA-256 is `33dfda271536ea1c97de204bc415a8ff619f5c326a536ec0be4f9dc3a0f1c889`; the complete candidate WAV is `c72cfab792214947717e02f3ef3b931af27af6fcd9dfa789a5189d196fd80e6c`. The validated working audio and SID remain in ignored build output; the public demo package retains the accepted bytes and corresponding source separately.

The [recorded phrase verdict](listening-review.json) is: “yes, feels centered while the accompaniment retains useful left/right space and fullness”. The listener subsequently reviewed the complete version and confirmed “Complete revised version : sounds great.” This closes the requested native stereo interpretation. The demo presentation should begin with the main music at 32 seconds, preserving the full accepted export separately. Model assistance was reassessed at closure: no calibrated model adds a useful decision to these direct human verdicts.

## README main-music release, 2026-10-16

The user dislikes the introduction in the original tune itself and requests its omission from both README Rambo demos. The [sample package](../../../samples/rambo-stereo/README.md#main-music-demo-2026-10-16) now supplies a SID and matching WAV starting at call 1,586 (31.641167 seconds), through the original ending. Complete accepted files remain unchanged. The package owns the computed entry-state contract, fresh SID-history limitation, full suffix-store comparison and entry/ending VICE checks. The listener accepted the trimmed stereo release alongside Bach stereo on 2026-10-16; the package records the exact verdict. Model-assistance feedback/closure review: no call; human acceptance settles this release, and current models cannot adjudicate stereo preference. Reassess only for a new musical revision.
