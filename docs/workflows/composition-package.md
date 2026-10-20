# Rambo composition package

Crafter exports the cleared Rambo mono sample's bounded musical relationships for SID Song Explorer through [the composition producer](../../scripts/composition-package.py) and [its generated package](../../samples/composition/rambo-main.json). This separate version 1 sidecar leaves [the strict catalog](catalog.md) unchanged. It connects two source passages to their note rows, actual note-entry program states, editorial part labels and physical allocation. It does not reopen the musical study or modify any score, player, SID or recording.

## Generate and check

Run from this checkout with Python 3.9 or newer and Git:

```sh
python3 scripts/composition-package.py generate
python3 scripts/composition-package.py check
python3 -m unittest discover -s tests -p composition_package_test.py -v
```

Both commands accept `--output PATH`. Generation writes deterministic UTF-8 JSON with a trailing newline; checking regenerates in memory and fails on different bytes. The producer reads ordinary source blobs from the existing catalog asset/evidence revision `3db086b6963676ef75f34d7f77c3b67232a777fb`. Retained compressed evidence uses Git LFS: local materializations must exactly match that revision's pointer SHA-256 and byte count, or generation fails. Missing materializations require the existing [evidence restoration workflow](build-cache.md); generation never fetches or silently consumes unverified working-tree input. Git reads have ten-second deadlines.

The generated package is small enough to vendor directly into Explorer. Its producer/package commit and digest are independent of the source/evidence revision and must be pinned by the consumer. A sibling checkout is an editing convenience, never a runtime dependency.

## Musical scope and evidence

The package binds `catalogEntryId: "rambo-loader-main"` to the cleared mono SID's exact SHA-256, subtune, PAL/MOS6581 profile, address and mono routing. It is ineligible for the separately authored [stereo arrangement](../../samples/rambo-stereo/README.md) or an arbitrary local SID. [The main-entry manifest](../../samples/rambo-loader/main-manifest.json) owns the source start at call 1586. Source calls are zero-based: source call 1586 maps to selected-file play call zero and timestamp zero; source call 1587 maps to one period. All timestamps use `(sourceCall - 1586) * 19656 / (17734475 / 18)`, with no added frame, using the canonical PAL clock from [sid_clock.py](../../scripts/sid_clock.py) and checked against the pinned entry receipt. `timing.timeBasis` is `source-call-grid`: these positions are independent of an engine, not bus-cycle timestamps or measured audible onset times. A consumer must project them through its verified renderer clock and startup anchor before aligning them with PCM or an audible playhead. In particular, Explorer's SIDLite PCM clock is quantized and cannot be replaced by the nominal PAL oscillator clock. Fresh SID oscillator, envelope and filter history remains the sample's existing limitation.

The selected source intervals are `[5426, 5554)` and `[5554, 5682)`. The short pulse lead repeats the same source nodes, relative entry times and base pitches. The bass repeats its graph/rhythm eight semitones higher in the second unit. The descending saw program states retain their actual source chord offsets. This establishes a lead recurrence with changed accompaniment, not an identical whole-mix repeat or a composer's intention. The first boundary carries one call of a sync-enabled lead; its source voice-3 oscillator dependency is explicit.

The producer joins [retained independent-player note/patch entries](../../evidence/rambo-centered-native/preparation/source-note-events.json.gz) with [original executed CPU rows](../../evidence/rambo-form/complete40000/events.json.gz) and the [pinned symbolic score](../../songs/rambo-loader.json). Every selected note must have an original note fetch with the same call, physical voice, source address and transposed pitch. Event ends come from the next executed row transition on that voice, including a rest/hold transition, rather than summed nominal durations. Carry-in and outgoing events can extend outside a passage while intersecting it; consumers clip drawings at the passage bounds without altering the recorded interval. A row interval is not a measured audible tail or a sustained-state reconstruction.

## Version 1 fields

- `source` identifies the repository, immutable evidence revision, score, note/patch evidence and rights owner. Every `sourcePath` resolves against this revision; exact execution and source correspondence remain in the [Rambo study](../research/composition/rambo-preparation.md#independent-numeric-loader).
- `binding`, `timing` and `coverage` identify the selected SID/profile, source-to-file time map and selected-passages scope. `wholeSong` is false. No musical content is claimed outside the two intervals.
- `parts` names the lead, bass and arpeggio/modulator as editorial musical roles, with derived evidence. `allocations` separately maps these parts to one-based chip/physical-voice numbers. These labels refer to source reconstruction allocation; the linked stereo study documents that source allocation without making its added parts original Galway work.
- `instruments` are actual source program states, keyed by a digest of the 49-byte note-entry data block. Human titles and `behavior` explain waveform, ADSR, PWM, pitch and articulation; they are descriptive labels rather than recovered names or a universal instrument bank. Each `program.data` retains all 49 integer bytes. The event's separate 39-byte `entrySound` preserves the sound state that can survive a note selection; patch data alone does not reconstruct every trajectory.
- `passages` carry source calls, selected-file seconds, explanatory roles, dependency records and `events`. Nullable `recurrence` names the earlier passage, the repeated part IDs, `same-source-phrase` and the exact scope of that relation. Passage descriptions and roles are derived; factual event rows and declared hardware/program dependencies are verified source observations.
- Each event contains an opaque ID, part/program references, actual `sourceCall`/`endSourceCall`, matching `startSeconds`/`endSeconds`, integer `pitchIndex`, 16-bit `frequencyWord`, graph `nodeId`, integer `sourceAddress`, `entrySound` and evidence level. Pitch indices address the source frequency table; its tuning is not silently replaced by equal temperament. The base frequency word does not flatten an arpeggio or other moving pitch program into a sustained note.
- `rights` retains the title-specific GNU GPL version 3 and Galway attribution boundary. This music-derived score/program content is covered by [the Rambo package terms](../../samples/rambo-loader/README.md); independently authored reusable producer tools retain MIT separately. No original SID binary or reference recording is added.

## Verification scope

The focused tests independently enumerate every original CPU note row intersecting each passage, check its next transition and pitch, and execute the existing numeric player to verify selected note-entry data/sound states. They guard exact catalog/main-entry binding, both recurrence and bass change, native frequency lookup, zero-based timing, deterministic bytes, source mismatches and altered/malformed LFS materializations. The canonical exact PAL clock is checked against the immutable main-entry timing receipt; a rounded 985248 Hz substitute does not satisfy that guard.

These are source-data and software checks; they establish no new musical acceptance, browser behavior, rendered audio or hardware equivalence. Existing scoped listening verdicts remain in the owning sample package.
