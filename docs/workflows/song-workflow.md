# From source music to SID

The workflow preserves the original music and separates musical interpretation from SID programming. A common score is an intermediate view, not a lossless replacement for every source format or the limit of SID expression.

## Current musical contract

Start with a given, attributed score. Original score composition is outside the current remit. Verify source melody, harmonic parts, timing, repeats and ending before sound design; preserve them separately from the SID arrangement. A transcription or arrangement must be identified as such, not silently treated as the composer's original edition.

Choose SID instruments, voice allocation, reductions, articulation, groove, modulation and effects to express the score's character. Single- and dual-SID arrangements are both valid; choose stereo when its musical roles justify it. Record departures such as octave shifts, omitted inner voices, arpeggiated chords or altered phrasing so the listener can distinguish source content from interpretation. Technical note/cadence checks do not establish compelling music, as the [rejected Night Transit trial](../../songs/night-transit/README.md) demonstrated.

Establish the intended mood from the brief and a relevant performance or documented musical context before selecting patches. A plain score rendering checks the musical material; it does not establish an expressive performance reference. Prior acceptance of a patch is context-specific. Separate playback level, spectral brightness, articulation and accompaniment weight when diagnosing an unsuitable interpretation; turning down the WAV alone cannot correct all four. The [Moon River case](../research/composition/moon-river-preparation.md) records this distinction.

Present the source recording or a clearly labelled plain rendering of the same retained score alongside each SID audition. Judge source preservation and artistic interpretation separately. Reuse the existing repertoire and recipe tools, measure execution effort honestly, and require listening acceptance before claiming musical productivity.

## Prepare a multitrack score audition

Use [prepare-score-audition.py](../../scripts/prepare-score-audition.py) when an existing MIDI import recipe has more parts than a three-voice audition needs. The [Pink Panther projection](../../songs/pink-panther/reduction.json) is a worked configuration; its [listening recipe](../../config/listening/pink-panther-theme.json) handles the rest of the pipeline.

```sh
PYTHONPATH=.tools/arrangement-deps python3 scripts/prepare-score-audition.py SOURCE.mid IMPORT.json --arrangement PROJECTION.json --candidate NATIVE.json --reference PLAIN.json --output build/new-score-audition
```

The import recipe pins the source hash and maps MIDI tracks. Projection `spans` select ordered exact-beat ranges. Exactly three uniquely named voices select distinct `sourcePart` IDs and either `reject-overlap` or `highest-at-onset`. The latter keeps the uniquely highest simultaneous note unchanged; tied highest pitches and any remaining overlap are rejected rather than silently choosing a duration. Every other source part needs an explicit omission reason. This deliberately narrow contract does not solve arbitrary polyphonic reduction, shorten overlapping notes or map drums to pitched voices automatically. Source notes crossing selected boundaries are rejected. A boundary with no crossing notes still needs musical review before being called an ending.

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
6. Account for the [model-assistance reviews](../research/audio-assessment.md#use-and-reassess-model-assistance) at the first audition, after listener feedback or a musical revision and before closure. Record useful findings or a reason to skip a model call in the owning study, with the next checkpoint; model use remains advisory unless validated for that particular task.
