# Moon River source preparation

The selected source is an existing instrumental piano MIDI advertised as “Breakfast at Tiffany's – Moon River (Piano Version)” by [MIDIfind](https://midifind.com/files/movies_tv_show/other_movie_tv_midi/breakfast_at_tiffany_39_s_moon_river_piano_version/422-1-0-7695). Music is by Henry Mancini; the arranger is unidentified. The file contains no author, copyright, lyrics or edition metadata. This is a source-backed piano interpretation, not a verified transcription of the original film orchestration or an assertion that its harmony is Mancini's original published harmony.

## Source and rights boundary

| Item | Verified evidence |
| --- | --- |
| Public download | [Ordinary MIDI download linked by the catalogue page](https://midifind.com/files/0-0-1-7695-20) |
| Original SHA-256 | `6d6fd45feb2c2d81374403225cde28637c9382d39a6b6e6b3ce3f86b46294104` |
| Original size | 6,939 bytes |
| Original format | Synchronous MIDI type 1, 480 ticks per quarter, 3/4 throughout |
| Source parts | Track 0: 364 notes; track 1: 386 notes. Both are named Acoustic Piano; their registers and voicing support the right-hand/left-hand mapping. The right hand also contains chords. |
| Complete timeline | 234 quarter-note beats, 78 bars; original MIDI playback lasts 214.0926915 seconds |
| Source timing | 38 tempo events with an opening value of 857142 microseconds per quarter, approximately quarter = 70; phrase and ending rubato are encoded in the original |
| Usage evidence, checked 2026-10-15 | MIDIfind's page invites arranging, remaking and recording uses. Neither the unidentified arranger's permission nor the host's authority over the arrangement is established. |

Keep the original MIDI, derivative MIDI, common score, reduced score and reference audio in ignored local/build storage. The tracked [import recipe](../../../config/scores/moon-river-import.json) contains metadata and a hash, not the source's notes. Availability and the host's invitation do not establish an open redistribution license.

The initial alternative, [Roberto Di Marino's author-published saxophone quartet](https://di-marino.it/MoonRive.htm), has stronger arranger attribution but recasts the music in 2/4. It was not selected because that metric adaptation would add another variable to this first melody-and-harmony trial.

## Import and deliberate adaptation

Use the case adapter [prepare-source.py](../../../scripts/studies/moon-river/prepare-source.py) with the existing [common-score importer and reducer](../../../scripts/score_tools.py). The adapter verifies the original hash, copies the original unchanged, replaces every tempo value in a separate MIDI with the original opening value, and verifies message identity and event delta ticks before and after serialization, allowing only the tempo-value difference. It retains the complete original tempo map in `adaptation.json`.

The initial musical interpretation deliberately uses constant quarter = 70. This removes the source's rubato but preserves all note pitches, velocities, note-on/off ticks, track boundaries and non-tempo MIDI events in the derivative MIDI. All 750 notes remain in `full-common-score.json` over the complete 234-beat timeline; none are composed or substituted during import. The source's first complete statement through its tonic close is selected separately in `common-score.json`: 319 notes over beats 0–111, lasting 95.1428571 seconds at exact quarter = 70 before the player tail. Later source material remains preserved but is outside this interpretation.

The common-score importer reports both piano program changes as unmapped. It also omits MIDI channels and note-off velocities from its note view; the original and derivative MIDI retain them. The source has no controller events or encoded sustain pedal. MIDI does not settle engraved spelling, slurs, articulation marks or written dynamics. Its note durations are preserved literally, including short right-hand releases followed by longer gaps; changing those releases would be a separate articulation decision.

The [three-voice reduction recipe](../../../songs/moon-river/reduction.json) is separate from import and allocates lead, bass and one harmony voice. The machine-readable reduction report records every omission and shortening in ignored output. This is a disclosed reduction of existing source harmony, not newly authored accompaniment; listening must establish whether it retains enough of the piano texture.

## Reproduction

After the project dependency setup, prepare a fresh output directory:

```sh
PYTHONPATH=.tools/arrangement-deps:.tools/test-deps python3 scripts/studies/moon-river/prepare-source.py \
  .local/research/moon-river/moon-river-piano.mid \
  config/scores/moon-river-import.json \
  --output build/moon-river-prepared \
  --arrangement songs/moon-river/reduction.json \
  --candidate songs/moon-river/native.json \
  --reference songs/moon-river/plain.json
```

The adapter emits unchanged `source.mid`, verified `constant-tempo.mid`, `import-recipe.json`, complete `full-common-score.json`, selected `common-score.json`, `adaptation.json`, reduced `score.json`, and same-score `candidate.json`/`reference.json` native configurations. Omit the three optional template arguments for source import alone. The full-source derivative hash is `2348c5dbbf344360ae02f530d40c0a7a737d65365237d334092047b78647a87e` with the current pinned source and Mido serialization.

The selected endpoint is after bar 37, at beat 111, before bar 38's pivot into the next key. The right-hand tonic triad begins at beat 108 and releases at 109; the final left-hand tonic bass and third both release exactly at beat 111. No source note crosses this boundary, so all 319 notes of the selected statement are included without shortening its cadence, composing an ending or fading it out. The complete 234-beat arrangement exceeded the existing native backend's 100-pattern limit; this bounded complete statement preserves the ballad tempo without changing that backend contract.

For navigation, the opening 16 bars end at beat 48 with a source-written dominant turnaround, immediately before a higher-register theme restatement. That is a section boundary, not the complete statement's tonic ending. Formal labels and key relationships here are source-navigation inferences, not a claim to an authoritative published edition analysis.

## Verification and listening status

The focused source-adapter tests cover the pinned-hash and fresh-directory guards, unchanged note/controller timing through tempo normalization, and preservation of the full common score alongside an explicit section selection. Actual source preparation also verifies all serialized MIDI messages against the original except tempo values, retains the full 750-note source, selects the complete 319-note first statement and generates both native configurations from one reduced score. CPU execution, VICE execution, rendered audio and musical acceptance are separate later checks; source intake alone establishes none of them.

## First SID audition

The [editable SID interpretation and first listening package](../../../songs/moon-river/README.md#first-listening-package) preserve both the plain score rendering and the complete first-statement candidate. Full CPU scheduling and ending checks, sampled standalone VICE checks and PCM guards pass. The source-reduction losses and exact audio hashes are retained there. On **2026-10-15**, the listener recognized the tune and considered the score acceptable, but rejected the SID interpretation as bad, too loud and offensive. This is a musical rejection despite successful execution; recognition does not independently verify every imported note or harmonic choice.

## Mood brief and restrained revision

The listener accepted **tender, intimate, wistful and quietly hopeful** as the intended character. That agreement establishes the interpretation brief, not acceptance of an audio revision. [Monica Mancini's Library of Congress essay](https://lcweb2.loc.gov/static/programs/national-recording-preservation-board/documents/Moon-Rivier_Mancini.pdf) explains that the song was written for Audrey Hepburn and that Henry Mancini preferred her performance; Monica connects its dreaming with awareness of heartbreak. [PBS's account of the film scene](https://www.pbs.org/opb/thesixties/topics/culture/ontherecord.html) describes Holly's fire-escape performance as revealing her longings. The mood vocabulary is our interpretation of that context, confirmed by the listener, rather than a quoted composer's instruction.

**Reusable lesson:** establish the song's emotional role before selecting a palette or effects. A pulse lead and filtered bass that worked in another arrangement carry only that arrangement's listening verdict; their execution and earlier acceptance do not establish suitability for a quiet ballad. Keep the melody in the foreground and judge timbre, attack, sustained weight and supporting voices together in context. Lowering file gain alone would leave those musical choices untested.

The [restrained revision](../../../songs/moon-river/restrained.json) tests a triangle lead with gentler delayed vibrato and a shaped envelope, triangle bass and quieter triangle harmony, with reduced accompaniment sustain and no pulse-width or filter programs. It uses the same source, three-voice reduction, constant tempo and complete 111-beat statement. It does not restore the source rubato or change note lengths to create legato. The [published revision and reproduction recipe](../../../songs/moon-river/README.md#restrained-revision) retain this as the next candidate; its musical acceptance is pending in the [listening record](../../../songs/moon-river/listening-review.json).

**Model-assistance review after feedback:** no model call is useful for deciding this mood or preference change. The [existing calibrations](../audio-assessment.md#use-and-reassess-model-assistance) do not validate either model as a judge of tender phrasing, instrument balance or this listener's taste. Human feedback is decisive. Reassess model usefulness after the restrained audition and before closing the case; do not treat an automated score as acceptance.
