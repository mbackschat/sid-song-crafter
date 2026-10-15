# Rambo: expand the source arpeggio into a held chord

This candidate develops an identifiable limit of the original three-voice arrangement: source voice 3 serializes chord tones through one oscillator during calls 2354–7474. The faithful loader remains unchanged on SID A. SID B supplies three simultaneous source chord tones while the original arpeggio keeps its motion and full chord colors. This is an arrangement experiment, not a reconstruction of missing intended notes or an assertion that Galway wanted sustained chords. The [88–104-second phrase comparison is accepted](listening-review.json): the listener hears useful added fullness while the melody stays clear. The complete arrangement is also liked; a centered-primary presentation is now requested.

The [first expanded ensemble](../rambo-ensemble/README.md#resource-informed-revision) remains the comparison baseline. Its B1 low pulse and B2 inner triangle keep their exact note, gate and lifetime calendars. Only B3's calendar changes: the same pulse patch, derived from source voice 3 at call 7986 with AD/SR `$38/$57` and its retained PWM, now enters at the start of every actual source chord region and occupies that region through its reserved release. No melody, drum attacks, envelope settings, pulse programs, pitch range or primary score are added or revised.

## Allocation and limits

| Chip/voice | Role and scope |
| --- | --- |
| A1/A2/A3 | Complete faithful source score, programs, sync/ring dependencies, Morse passage and natural ending. |
| B1 | Existing low moving-pulse anchor, including its previously declared entrance and closing anchor passages. |
| B2 | Existing inner triangle during the source chord section. |
| B3 | Remaining distinct chord tone in native pitch indices 43–54, once per source chord region, only during calls 2354–7474. |

The source contains 42 chord regions: 38 last 128 calls and four last 64 calls. B3 now covers all 42 regions rather than the previous 19 partial swells. B1, B2 and B3 supply three distinct pitch classes throughout each region, including the declared release portion; their sounding calendars occupy 5,120 calls of the source chord section. B3 keeps a 24-call reserved release and clears at call 7474. Consecutive regions can retrigger that oscillator at their shared boundary; this does not create independent overlapping tails.

Some source regions have four pitch classes. The secondary's three oscillators retain a declared three-tone reduction there, while the unchanged A3 arpeggio continues to emit the original complete chord table. The whole-span guard checks every chosen tone against the actual executed source chord set, including suspensions, augmented colors and dominant extensions; it does not substitute generic triads. The [configuration](arrangement.json) keeps the previous pitch ranges and voice-leading rule, so the selected three-tone reduction follows those explicit constraints.

This candidate uses the original source frequencies with their native tuning. Two PAL MOS6581 chips at `$D400/$D420` share one 19,656-cycle update budget. The raw listening render places chip A on the left and chip B on the right. Each chip has one mono output, so these are two groups rather than six independently pannable instruments; the earlier centered presentation matrix is not applied to this raw comparison. See the [hardware and mixing contract](../../../docs/research/sid/dual-sid.md#plan-the-sound-hardware-and-the-mix-together).

## Reproduce and verify

Use the [local setup](../../../docs/setup/local-setup.md), then generate fresh local outputs from the repository root:

```sh
python3 scripts/studies/rambo/prepare-ensemble.py songs/studies/rambo-chord-expansion/arrangement.json --output build/rambo-chord-expansion-preparation
PYTHONPATH=.tools/test-deps python3 scripts/compose-rambo-dual.py songs/rambo-loader.json build/rambo-chord-expansion-preparation/secondary.json --output build/rambo-chord-expansion-export
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps:tests python3 -m unittest rambo_chord_expansion_test rambo_ensemble_test -v
```

For the complete CPU, VICE, rendering and listening pipeline, first reproduce the [previous ensemble](../rambo-ensemble/README.md#reproduce) if its pinned raw reference is absent. Then run:

```sh
python3 scripts/listening-package.py config/listening/rambo-chord-expansion.json --output build/rambo-chord-expansion
python3 scripts/publish-listening.py build/rambo-chord-expansion/run.json --selection songs/studies/rambo-chord-expansion/audition.json --output build/rambo-chord-expansion-listening
```

Use a fresh publication directory; an unchanged recipe run reuses verified stages. The [recipe](../../../config/listening/rambo-chord-expansion.json) pins the prior raw render, source score and tool dependencies. Its comparison contains the prior raw arrangement first, then the held-chord candidate, at matched whole-clip level. Both use A-left/B-right; the first half is not the centered mix from the earlier human review. The 88–104-second passage yields a 32.5-second A/B including the half-second gap.

The unchanged composition engines consume the generated `secondary.json` alongside the tracked source graph. Preparation emits `arrangement-proof.json`, `source-note-events.json.gz` and `support-note-events.json.gz` with complete observed source note entries and support entries retained. The [case guards](../../../tests/rambo_chord_expansion_test.py) establish unchanged B1/B2 calendars and patches, three distinct supported tones over every source chord region, exact B3 section bounds and the final clear. The shared numeric verifier checks actual frequency, gate and remaining lifetime on each call. Generated SID/audio are local outputs, not tracked downloads.

The main comparison is source seconds 88–104: B3 was intermittent in the baseline and now spans the whole phrase. Compare the first expanded ensemble and this candidate at one scalar per complete stereo clip, preserving raw channel balance. Complete CPU/VICE execution, primary register-calendar preservation, ending coverage and rendered signal contribution require the owning listening recipe's separate receipts; numeric chord membership alone does not establish useful weight, natural release or an improved arrangement.

## Primary preservation and shared-host timing

The compiled candidate retains the primary engine's bytes and complete 87,534-store register sequence. The CPU instruction-start cycles and VICE write-checkpoint offsets within each primary call also match the prior ensemble. The secondary change increases peak play cost to 9,181 cycles within the shared 19,656-cycle PAL budget. The full 11,000-call candidate matches 113,001 ordered stores in CPU and VICE, with ten numeric state checkpoints.

An initial audio guard incorrectly required exact primary-channel and ending PCM identity. It rejected this candidate even though the source execution was preserved. VICE found the first different host-entry checkpoint at call 2355, immediately after the changed third support voice starts at 2354; later entry differences range from −8 to +8 cycles. Changing the secondary workload affects the shared host's instruction phase. The [timing checker](../../../scripts/studies/rambo/check-chord-expansion-timing.py) compares canonical retained CPU/VICE evidence and the tracked faithful primary payload. It uses the tracer's existing cadence contract: phase error relative to the first entry, not a new threshold on adjacent interval swings. Those monitor checkpoints establish the mechanism in the controlled harness; they are not exact SID bus timestamps or a reconstruction of the renderer's schedule.

The unchanged first 47 seconds of primary PCM and a byte-identical independent repeat of the full candidate render support a reproducible execution difference rather than random rendering. Preserve the source event sequence and within-call timing as the executable invariants, report the actual PCM differences, and verify complete closing sound and final decay separately. Do not align samples, suppress differences or claim a bit-identical ending. The reusable lesson is retained in the [dual-SID guide](../../../docs/research/sid/dual-sid.md#a-correct-matrix-can-still-miss-the-spatial-brief).

## Verified listening package

The [retained evidence](../../../evidence/rambo-chord-expansion/README.md) includes the complete execution and timing records, rendered health, role-omission diagnostic, exact comparison gains and submitted hashes. The full 225-second stereo render and its internal mono fold-down have no clipped samples, retain the 205–211-second closing body and settle to zero AC signal in the final second. A same-SID repeat reproduced the full WAV byte-for-byte. These checks establish delivery and signal contribution; the listener establishes musical value.

The original run stopped at the invalid PCM-identity assumption after 185.462 seconds. The corrected recovery reused CPU/VICE/render stages and completed in 52.306 seconds; its unchanged repeat reused all 15 stages in 1.076 seconds. These are recorded execution times, not total production effort or a fresh end-to-end timing for the revised recipe.

| Local audition | Content |
| --- | --- |
| `build/rambo-chord-expansion-listening/prior-raw-then-expanded-chord-phrase.ab.wav` | 32.5-second matched comparison: previous raw support first, sustained chord support second. Gains 1 and 0.951981886; raw chip balance preserved. |
| `build/rambo-chord-expansion-listening/expanded-chord-raw-full.wav` | Complete 225-second candidate, faithful trio left and added support right. |
| `build/rambo-chord-expansion-listening/previous-raw-ensemble-full.wav` | Complete prior raw six-voice arrangement, using the same channel mapping. |

On 2026-10-15, the listener first replied “wow, nice!” and then clarified: “second half adds useful fullness while keeping the  melody clear”. Retain this as the preferred direction. The initial verdict covers the compared phrase. Subsequent feedback on the complete version was “This is really nice, great”, with a request to move the main instrument from the left to the middle. Preserve this full arrangement as the liked baseline; the placement correction now requires a deliberate native voice allocation and is not yet accepted. The [review record](listening-review.json) pins the submitted audio and feedback.

## Center the lead while keeping accompaniment on both sides

After liking the complete performance, the listener identified the lead's hard-left position and requested it in the middle, with the other instruments distributed left and right. Centering the entire first chip would also center its bass and arpeggio. The user explicitly rejected that interpretation of the request; no whole-chip-centered audition was produced. Preserve the accepted six-part raw arrangement as the baseline. The user subsequently clarified that other parts may also be centered when useful: placement must be deliberate. The rejected shortcut was allowing existing chip grouping to decide the whole placement, not the presence of another instrument in the center.

The [implemented native revision](../rambo-centered-native/README.md) uses the following voice allocation: duplicate the lead across chips to establish a center component, while retaining independent accompaniment on each chip. This consumes an additional oscillator and may require its sync/ring modulator too. Six physical voices cannot retain all six previous independent roles plus a duplicate lead. Prefer sacrificing the extra low anchor before the newly accepted held chord tone, because the original bass remains present; verify this tradeoff in context rather than assuming unchanged fullness.

Source A1 depends on A3 for sync during calls 4915–5427 and ring modulation during 10035–10660. A copied lead must retain the required modulator behavior and oscillator history, not merely its onset pitch. The new candidate passes full CPU/VICE/render checks, and its compared phrase is accepted for centered lead with useful side space and fullness. Its physical phase is not claimed identical; full revised performance/ending review remains pending. A stable centered lead is the goal; the separately documented optional [spatial movement gesture](../../../docs/research/composition/gestures/stereo-movement.md) is not requested for this revision.

Human feedback and the actual two-chip constraints establish this design correction. Audio models are not qualified to choose the allocation or approve the spatial result; reassess after a verified audition.

## Rights and listening status

Music-derived scores and note records retain Martin Galway's credit, modification notice and the [Rambo loader's GPLv3 terms](../../../samples/rambo-loader/README.md). Reusable project tools retain [MIT](../../../LICENSE) separately. The loader grant does not clear other subtunes in the archive. Candidate SID/audio remain local pending musical review.

**Model-assistance checkpoint:** reviewed before the first chord-expansion audition. Reassessed after the positive human phrase feedback: current audio-model trials do not qualify a model to decide whether this held third tone improves the source's character, harmonic weight or articulation. Reassessed again after full-song feedback: the known hard-left source routing identifies a presentation correction without a model call. Human review remains authoritative; the [native revision](../rambo-centered-native/README.md) records the accepted phrase and current model-assistance review; reassess at full-song closure.
