# From source music to SID

The workflow preserves the original music and separates musical interpretation from SID programming. A common score is an intermediate view, not a lossless replacement for every source format or the limit of SID expression.

## Current musical contract

Start with a given, attributed score. Original score composition is outside the current remit. Verify source melody, harmonic parts, timing, repeats and ending before sound design; preserve them separately from the SID arrangement. A transcription or arrangement must be identified as such, not silently treated as the composer's original edition.

Choose SID instruments, voice allocation, reductions, articulation, groove, modulation and effects to express the score's character. Single- and dual-SID arrangements are both valid; choose stereo when its musical roles justify it. Record departures such as octave shifts, omitted inner voices, arpeggiated chords or altered phrasing so the listener can distinguish source content from interpretation. Technical note/cadence checks do not establish compelling music, as the [rejected Night Transit trial](../../songs/night-transit/README.md) demonstrated.

Establish the intended mood from the brief and a relevant performance or documented musical context before selecting patches. A plain score rendering checks the musical material; it does not establish an expressive performance reference. Prior acceptance of a patch is context-specific. Separate playback level, spectral brightness, articulation and accompaniment weight when diagnosing an unsuitable interpretation; turning down the WAV alone cannot correct all four. The [Moon River case](../research/composition/moon-river-preparation.md) records this distinction.

Present the source recording or a clearly labelled plain rendering of the same retained score alongside each SID audition. Judge source preservation and artistic interpretation separately. Reuse the existing repertoire and recipe tools, measure execution effort honestly, and require listening acceptance before claiming musical productivity.

## Repeatable song routine

1. **Establish the musical target.** Identify the score edition, complete form and ending; research the intended mood. Source selection and interpretation require judgment. Preserve the original separately with its URL and fingerprint.
2. **Configure the reduction and chip layout.** Reuse the importer and declare source parts, spans, omissions and single- or dual-SID roles. Apply the [hardware and output-mix decision table](../research/sid/dual-sid.md#plan-the-sound-hardware-and-the-mix-together): map roles to physical voices, same-chip oscillator dependencies, shared filters and the intended stereo matrix before choosing patches. Two chips provide six voices but only two mono outputs; centered material needs an explicit mixing/allocation plan. When expanding a master's one-SID arrangement, first make the [source constraint map](../research/sid/dual-sid.md#expand-the-musical-capacity-not-only-the-stereo-image): identify demonstrated compromises, consult composer accounts, and state which musical role the extra resources develop. Distinguish added musical roles from redistribution of existing parts. Automated accounting preserves the complete source and checks every retained or omitted event; choosing what the listener should hear remains a musical decision.
3. **Select the sound.** Retrieve the established master-study repertoire first, check listening scope and driver constraints, then choose instruments, articulation and effects for the brief. Use a representative source-backed audition to test the palette before extending the complete form.
4. **Execute one recipe.** The [listening runner](listening-package.md) prepares, builds, audits, renders, checks standalone playback and endings, and creates labelled comparisons. Cache unchanged stages by verified inputs and outputs; use the existing publisher for stable listening files.
5. **Review and retain.** Human feedback settles musical fit. Record the verdict with the reviewed file hash, fix only demonstrated gaps, and retain reusable findings and code. Apply [the two-tier public sample policy](publication-boundary.md): every sample retains public tools/instruments, recipes without embedded notes, source references and hashes; complete scores and native sources additionally require a recorded rights basis for both composition and source arrangement. Follow the [standing model-assistance decision](../research/audio-assessment.md#use-and-reassess-model-assistance), reassessing when a concrete useful question, relevant configuration change or user request occurs; models remain advisory.

For the next song, change source/import mappings, reduction, palette and recipe configuration before considering new infrastructure. Source compatibility, voice allocation, phrasing and instrument balance are not automatically solved. Pink Panther required two shared-tool extensions for explicit event omissions and repeat-aware storage; those cases now have reusable support. Its accepted complete song demonstrates musical reuse, while its roughly 161-second package execution and 0.49-second unchanged repeat measure execution only, not total production effort. See the [case evidence](../../songs/pink-panther/README.md#complete-sourced-arrangement). Measure exceptional investigation/implementation separately on the next case; do not claim a total productivity gain until comparable effort has been measured.

## Prepare a multitrack score audition

Use [prepare-score-audition.py](../../scripts/prepare-score-audition.py) when an existing MIDI import recipe has more parts than a three-voice audition needs. The [Pink Panther projection](../../songs/pink-panther/reduction.json) is a worked configuration; its [listening recipe](../../config/listening/pink-panther-theme.json) handles the rest of the pipeline.

```sh
PYTHONPATH=.tools/arrangement-deps python3 scripts/prepare-score-audition.py SOURCE.mid IMPORT.json --arrangement PROJECTION.json --candidate NATIVE.json --reference PLAIN.json --output build/new-score-audition
```

The import recipe pins the source hash and maps MIDI tracks. Projection `spans` select ordered exact-beat ranges. Exactly three uniquely named voices declare either `sourcePart: "theme"` or `sourceParts: ["theme", "later-lead"]`, never both. Each source part belongs to exactly one voice or has an explicit omission reason. Multiple parts merge chronologically while retaining their original part/event identities; this allows a chip voice to carry different source roles in successive sections.

Choose `monophonicPolicy: "reject-overlap"` or `"highest-at-onset"`. The latter keeps the uniquely highest simultaneous note; tied highest pitches are rejected rather than silently choosing a duration. Remaining overlaps reject by default. An explicit per-voice `overlapPolicy: "shorten-to-next-onset"` preserves each selected onset and pitch, trimming an overlapping predecessor to the next onset. This is a deliberate monophonic articulation change, not an implicit import correction. Equal-onset conflicts still reject; the policy never extends notes. Source notes crossing selected passage boundaries also reject. A boundary with no crossing notes still needs musical review before being called an ending.

A voice may declare `omittedEvents: [{"sourceEventIndex": 344, "reason": "Preserve the overlapping upper held note"}]` to remove specific notes before its monophonic policy runs. Each index identifies the zero-based event in its complete source part in `full-common-score.json`, not its position in the selected passage or reduced voice. When the voice maps multiple source parts, each omission must name its `sourcePart`, for example `{"sourcePart": "brass", "sourceEventIndex": 0, "reason": "Retain the longer simultaneous unison in the other part"}`. Indices must be nonnegative, unique within their part, present in the complete source part and selected by at least one span; each needs a nonblank reason. Repeated spans produce separate loss records for every occurrence. Undeclared notes still pass through the selected reduction policies.

Retained origin records always preserve the original rational duration. A shortened event additionally records `outputDurationBeats`; `shortenedEvents` and `shortenedNotes` expose every such change. This narrow contract does not solve arbitrary polyphonic reduction, invent accompaniment or translate GM drums into pitched voices. The [complete Axel F projection](../../songs/axel-f/full-reduction.json) demonstrates successive source roles and explicit monophonic overlap trimming.

The command retains the unchanged MIDI and complete imported common score alongside the selected common score and native-compatible `score.json`. `adaptation.json` accounts for every selected source note as retained or omitted, with source part, index, exact pitch/timing and velocity. Output beats use the existing numeric arrangement format; exact rational origins remain in the report. Source velocities are not automatically translated into SID dynamics, and the importer reports its own unsupported metadata. Optional candidate/reference templates must be supplied together and reference the same prepared score. Fresh output directories prevent overwriting retained evidence.

Run the [focused tests](../../tests/score_audition_test.py) with `PYTHONPATH=.tools/arrangement-deps python3 -m unittest discover -s tests -p 'score_audition_test.py'`. Independent synthetic input exercises the reusable contract; human review still selects the musical passage and roles.

## Information boundaries

| Layer | Responsibility | Retained evidence |
| --- | --- | --- |
| Original source | Preserve the supplied score or performance unchanged | Original files, URL, author/edition/license, checksum |
| Common musical score | Represent parts, pitches, exact musical timing, and supported metadata | Source linkage, import settings, unsupported-event report |
| SID arrangement | Choose voices, articulation, instruments, and reductions for a particular target | Arrangement recipe and explicit decisions about discarded or changed material |
| Executable player | Schedule chip register writes and export playable binaries | Assembly, register-event manifest, SID/PRG, rendered WAV, verification report |

Importing and arranging are different operations. A three-voice chord reduction must not overwrite the complete polyphonic score. Recovering notation, pedal intent, or other unrepresented information requires the preserved original; retaining the original does not make the intermediate representation lossless. Each new importer must disclose its supported subset and reject or report information it cannot map.

## SID expression

The chip-specific layer must remain independent of the common score. SID arrangements can be authored directly and need not pass through MIDI or a note-only representation; direct chip authoring does not change the requirement to retain the underlying musical source. Evolving waveforms, pulse-width modulation, frequency slides, vibrato, fast arpeggios, envelope changes, shared-filter automation, sync, and ring modulation belong at this layer; their timing and voice dependencies are musical data too. See [the hardware research](../research/sid/hardware.md) for chip semantics.

The current [three-voice exporter](../architecture/three-voice-player.md) implements a deliberately smaller subset: fixed instruments and frame-scheduled pitched notes on one PAL/8580 SID. Its assembly player consumes register writes, but the public score compiler does not yet expose arbitrary register automation. Neither this format nor its frame scheduler claims support for all SID techniques, cycle-timed sample playback, or two chips. Adding an effect requires an explicit player/compiler capability and verification, not silently flattening it into notes.

## Build an arranged song

After the dependency setup in [README](../../README.md), [the audio guide](audio-workflow.md), and [the VICE setup](../setup/vice-startup-investigation.md):

```sh
python3 scripts/song.py path/to/arrangement.json --name my-song
```

This builds PRG/SID/assembly/event files, renders a WAV, checks the register schedule and PCM, and runs the standalone PRG to completion in headless VICE. Outputs go to ignored `build/`; `my-song.verification.json` records the evidence. Use `--output DIRECTORY` to change the destination. `--renderer`, `--vice`, and `--vice-data` override local dependency paths.

Add `--vice-audio` for a separate full VICE/reSID WAV capture. This runs at normal emulation speed, so allow the song duration plus startup time. The default uses fast VICE execution with sound disabled and renders audio separately through libsidplayfp. Neither operation requires a window, network monitor, or host speaker access.

## Next-song checklist

1. Retain the original source and record its provenance and usage terms.
2. Select an existing importer or implement only the required adapter. Check its loss report, tempo, repeats, grace notes, and final rests against the source.
3. Keep the complete common score; create a separate SID arrangement with explicit voice allocation and reduction decisions.
4. Build and verify with `scripts/song.py`. Review the arrangement and listen to the resulting WAV: technical execution checks do not establish musical fidelity or artistic quality.
5. Record newly discovered limitations and reusable fixes alongside the relevant tool documentation.
6. Record one [standing model-assistance decision](../research/audio-assessment.md#use-and-reassess-model-assistance) when the case opens. Reassess for a concrete useful question, relevant model/prompt/preprocessing change or explicit user request; at closure, check that the decision remains current and triggered trials have recorded outcomes. An unchanged decision needs no repeated skip prose; task-specific controls, human musical acceptance and upload/spending authorization remain required.
