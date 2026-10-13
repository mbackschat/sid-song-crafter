# SID technique lookup

Start here before selecting instruments, arranging voices, explaining a technique, or responding to listening feedback. This is a retrieval index: the linked studies and instrument cards own provenance, implementation details and verdicts. Browse the [research library](README.md) only when no route fits.

## Use knowledge before proposing a change

1. Name the musical need in the listener's terms and find a route below; search aliases if necessary.
2. Read the linked evidence and reusable example when available. Distinguish a documented method, an implemented experiment and a listening preference. A composer's use does not establish invention; a running patch does not establish musical success.
3. Check the actual voice, shared-filter, envelope, chip-model and update-rate constraints. Select a technique because it fits the phrase; explicitly reject it when its cost defeats the musical purpose.
4. Reuse an existing patch/tool when available; otherwise define a small experiment. Choose an audible acceptance question before editing. For a retained arrangement, put the chosen method and rationale in its existing recipe/study README; for an explanation, answer directly. Do not create a session log.
5. Verify execution and audition the phrase in context. Update the owning card with the bounded result, then change this index only if the retrieval route changes.

## Find a technique by musical need

| Need / search aliases | Candidate and fit constraint | Read and reuse |
| --- | --- | --- |
| More instruments; fourth instrument; multiplex; interleave; channel sharing; drum + bass | Time-share a voice: brief percussion followed by a pitched body. Budget the delayed bass arrival and shared envelope; independent tails cannot coexist. | [Hülsbeck/Tel accounts](composers/huelsbeck-tel.md), [BASS-02 patch and listening evidence](composition/instruments/bass-02-kick-to-bass.md) |
| Fuller harmony; one-voice chord; arpeggio | Cycle chord tones; choose inversion and dwell for the register. Preserve waveform and pitch cycles throughout sustain and release. | [CHORD-01 program and guard](composition/instruments/chord-01-sustained-arpeggio.md), [selective chord gestures](composition/gestures/chord-bursts.md) |
| Static or lifeless tone; moving pulse; PWM | Move pulse width through the note. Check useful range, restart phase and chip target. | [Shades PWM/release experiment and verdict](composition/shades-preparation.md#moving-pulse-through-release), [LEAD-02 editable pair](composition/instruments/lead-02-moving-pulse.md), [advanced synthesis](sid/advanced-techniques.md) |
| Harsh or noise-like attack; softer pluck; transient/body | Shape attack separately from body; compare on the same melody. A smooth patch alone cannot fix clinical phrasing. | [PLUCK-01](composition/instruments/pluck-01-bright-attack.md), [editable Elise attack comparison](../../songs/studies/fuer-elise-attack/README.md) |
| Singing lead; vibrato; glide; portamento; legato | Delay modulation and choose tied/restarted notes deliberately. Pitch glide, hold and envelope continuity are distinct contracts. | [Shades target-glide and delayed-vibrato programs](composition/instruments/shades-decoded-programs.md) (compiled CPU/CIA playback verified; listening pending), [instrument programming](sid/advanced-techniques.md), [LEAD-02 implementation](composition/instruments/lead-02-moving-pulse.md) |
| Staged attack; changing PWM rate; same-call restart; Flashdance | Preserve instrument position across legato notes, distinguish score-off from program-owned release, and retain the shared filter owner. | [Flashdance instrument card and transfer phrase](composition/instruments/flashdance-decoded-programs.md), [executed contracts](composition/flashdance-preparation.md#editable-full-span-model), [description workflow](../workflows/decoded-song-workflow.md#flashdance-description) (reconstruction accepted; original transfer judged to work) |
| Small bass; weight; vibrant; layered; DRAX | Examine the evolving bass body and filter/model before adding parts. Allow enough time before retriggering for the desired PWM/release movement. | [DRAX listener attribution](composition/fuer-elise-reference.md#identify-the-preferred-layer-by-listening), [executed mechanism](tools/sid-program-analysis.md#follow-the-bass-program), [editable reconstruction](../../songs/studies/drax-bass-reconstruction/README.md) (in-context match accepted), [transfer and phrase-spacing finding](../../songs/studies/elise-decoded-bass/README.md) (improved, still less rich than DRAX) |
| Clinical arrangement; playful; groove; improvisation | Use rhythmic answers, selective accompaniment and phrase variation; preserve the original score separately. | [Gesture selection and verdicts](composition/gestures/README.md), [editable interpretation](../../songs/studies/fuer-elise-interpretation/README.md) |
| Metallic; bell; ring modulation; hard sync | Allocate carrier and modulator together; voice dependencies can consume accompaniment capacity. | [Coupled oscillators](sid/advanced-techniques.md#coupled-oscillators-and-combined-waveforms), [hardware semantics](sid/hardware.md) |
| Filter movement; conflicting instruments; 6581 vs 8580 | Assign shared-filter ownership. Numeric settings do not guarantee the same sound across models. | [Filter design](sid/advanced-techniques.md#filter-and-mix-design), [BASS-02 routing example](composition/instruments/bass-02-kick-to-bass.md) |
| Inconsistent attack; missing grace note; hard restart; ADSR | Check ordered writes and the player's onset contract before changing notation. | [Envelope constraints](sid/advanced-techniques.md#envelope-timing-is-part-of-the-instrument), [native onset findings](../songs/fuer-elise-native.md) |
| Dual SID; six voices; separate filters; competing second melody; harmonic support | Arrange intentional mix groups; align sustained support to chord-body changes and check the whole held span and lead-register overlap. | [Accepted Flashdance raw stereo and arrangement lesson](composition/flashdance-preparation.md#deliberate-dual-sid-interpretation), [two-chip design](sid/dual-sid.md), [native build and fixture](../workflows/native-song-workflow.md) |

## Execute or assess the choice

| Task | Existing route |
| --- | --- |
| Map musical roles to executed SID programs and reconstruct a complete texture | [Bidirectional DRAX trio mapping](composition/instruments/drax-decoded-trio.md), [independent three-voice implementation](../../songs/studies/drax-full-reconstruction/README.md): [complete-theme workflow](../workflows/decoded-song-workflow.md): editable description to our own code; full ordered-write comparison |
| Understand a master's sound; reverse-engineer an instrument; register timing; 6502/6510; VICE debugger | [Executed SID program experiments](tools/sid-program-analysis.md): connect writes to instructions and instrument data, then audition controlled changes before translating the mechanism |
| CIA timing; non-video-frame cadence; timer latch; opcode cycle discrepancy | [CIA tracing contract](../validation/cia-tracing.md), [CPU opcode timing lookup](../validation/cpu-timing.md), [Shades form and source lookup](composition/shades-preparation.md) |
| Render editable instrument experiments | [Instrument trials](../workflows/instrument-trials.md) |
| Change one instrument while preserving the score | [Native patch comparison](../../scripts/compare-native-patch.py), [worked attack comparison](../../songs/studies/fuer-elise-attack/README.md) |
| Compare originals and matched audio | [Audio comparisons](../workflows/audio-comparisons.md); amplitude matching is not a musical verdict |
| Locate a reference's audible component | [Diagnostic voice selection and coupling limits](../workflows/audio-workflow.md#diagnostic-voice-selection) |
| Export and verify a whole arrangement | [Native song workflow](../workflows/native-song-workflow.md), [independent VICE checks](../validation/native-vice-checks.md) |

## Keep the index useful

Add a row when a reusable musical need lacks a route; otherwise extend an existing row with the listener's vocabulary. Link tracked source/cards rather than transient build output. Keep detailed evidence and listening verdicts in their owning documents, including rejected candidates. If a technique has no local implementation, leave its route at the documented mechanism; do not imply a ready patch.

If retrieval misses something already known, repair its aliases or entry point. Search locally before researching again, for example `rg -ni 'multiplex|interleav|shared.voice|drum.*bass' docs/research songs/studies`. Split growing topic groups into linked indexes when this page stops being easy to scan; avoid a second, manually synchronized database.
