# Complete Für Elise score and SID reduction

This arrangement covers Beethoven's complete Bagatelle in A minor, WoO 59, including both printed opening repeats, the F-major episode, the repeated-bass episode and triplet cadenza, the final return, and the written final eighth rest. At quarter note = 72 the musical timeline is 187½ quarter-note beats, or 156.25 seconds, followed by the player's release tail. This is a three-voice reduction for one SID; the [opening example](first-song.md) remains a separate nine-note excerpt.

## Original sources

The [Mutopia catalogue entry](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=931), checked on 2026-10-12, identifies Breitkopf & Härtel, 1888, as the edition and Stelios Samelis as the typesetter. Its music ID is Mutopia-2015/08/18-931. The entry and LilyPond header identify the typesetting as Public Domain; the [Mutopia license description](https://www.mutopiaproject.org/legal.html) explains that dedication. Beethoven's composition is also public domain. The original files below are retained unchanged, so the normalized score never becomes the sole source of truth.

| Original | Published source | SHA-256 |
| --- | --- | --- |
| [fuer-elise.ly](../songs/sources/fuer-elise.ly) | [Typesetter's LilyPond source](https://raw.githubusercontent.com/MutopiaProject/MutopiaProject/master/ftp/BeethovenLv/WoO59/fur_Elise_WoO59/fur_Elise_WoO59.ly) | `828a7bd1b42e441fe1b0eb0389ba46f1502dab28bbe488389e635fb446ba7a67` |
| [fuer-elise.mid](../songs/sources/fuer-elise.mid) | [Mutopia's published MIDI](https://www.mutopiaproject.org/ftp/BeethovenLv/WoO59/fur_Elise_WoO59/fur_Elise_WoO59.mid) | `1c12c21c7bbf4cf163896732672648a69d497636059837abd153c71abe50215a` |

Direct HTTPS downloading from the Mutopia host timed out in this environment. Fetching its HTTP MIDI URL followed the site's redirect and returned the 7,590-byte Standard MIDI File. GitHub's published LilyPond source supplied the 8,800-byte notation file. The MIDI identifies GNU LilyPond 2.18.2, has 384 ticks per quarter, and contains `up:` and `down:` note tracks plus a control track.

The LilyPond source hides its metronome marking but specifies quarter note = 72. Its MIDI encodes 833,333 microseconds per quarter, the integer-microsecond approximation of that tempo. The [import recipe](../songs/fuer-elise-import.json) explicitly chooses 72 rather than presenting the MIDI's rounded value as a different musical tempo. The imported meter is 3/8 throughout.

## Repeat and ending verification

The published MIDI does not unfold the two `repeat volta 2` passages. It plays each body once, then both of that repeat's alternative endings sequentially. Directly using that MIDI would therefore produce the wrong performance form. Its note-off timeline also ends at 156½ quarter beats, while both staves of the LilyPond source finish with an eighth-note rest after the last A. The recipe restores that rest, giving a source timeline of 157 quarter beats before repeats.

| Printed material | MIDI quarter-beat range |
| --- | --- |
| First repeat body, including the initial two-sixteenth pickup | `[0, 11)` |
| First repeat, first ending | `[11, 12)` |
| First repeat, second ending | `[12, 13½)` |
| Second repeat body | `[13½, 33)` |
| Second repeat, first ending | `[33, 34½)` |
| Second repeat, second ending | `[34½, 36)` |
| Complete remaining material, plus restored final rest | `[36, 157)` |

The explicit performance spans concatenate `[0,12)`, `[0,11)`, `[12,34½)`, `[13½,33)`, and `[34½,157)`. This adds exactly 11 + 19½ beats to the source timeline. The first repeated body starts at beat 12; the second repeat's first and repeated passes start at 24½ and 45½. The F-major episode starts at 66½, the repeated-bass episode at 120½, and the final thematic return at 155. Grace notes borrowing time before the F-major episode remain at the MIDI's exact tick positions; the shortest appoggiatura is 10/384 of a quarter beat.

The source MIDI contains 517 upper-staff and 388 lower-staff notes. Unfolding the first body adds 34 upper and 15 lower notes; unfolding the second adds 54 upper and 33 lower notes. The [normalized complete performance](../songs/sources/fuer-elise.score.json) therefore contains 605 upper and 436 lower notes, totaling 1,041. These counts and independent pitch/rhythm landmarks are guarded by [arrangement tests](../tests/arrangement_test.py).

## Common score boundary and import losses

[import-midi.py](../scripts/import-midi.py) produces common score schema version 1 through the small shared [score module](../scripts/score_tools.py). Quarter-note beat positions, durations, and total length use exact reduced `[numerator, denominator]` integer pairs. Each part retains its ID, MIDI track name, all sounding pitches as MIDI integers, simultaneous notes, note-on velocity, and note-off timing. Gaps represent rests. The common score has no SID instruments or three-voice constraint. The [song workflow](song-workflow.md) describes the reusable conversion boundary.

This view is deliberately narrower than either the notation or original MIDI. Its import report lists unmapped event categories and fields. For this source, three CC7 volume messages, two key-signature messages, and two text messages remain only in the original MIDI. Note channels, note-off velocity, and the time-signature click/32nd-note fields are not mapped into common events. MIDI does not encode the notation's enharmonic spelling, printed repeat structure, slurs, articulation marks, engraved dynamics, or pedal notation; the preserved LilyPond file supplies those details. The recipe supplies the verified performance order, rather than trying to recover repeat signs from MIDI. Both output layers carry `sourceDirectory: "songs/sources"`, relative to the repository root; resolve `sourceFile` and `notationFile` against that directory and verify their recorded SHA-256 values.

The published MIDI has no CC64 sustain-pedal messages. The typesetter's LilyPond pedal notation remains in the original source, while this arrangement uses literal MIDI note-off lengths without pedal overlap. Common score v1 currently rejects effective tempo or meter changes, including a sole late nondefault change after MIDI's initial 120 BPM or 4/4 defaults. It rejects asynchronous Type 2 files and unmatched or unterminated notes. A repeat span that cuts through a sounding note also fails instead of silently shortening it.

## Three-voice arrangement policy

[arrange-score.py](../scripts/arrange-score.py) accepts the common score and [SID arrangement recipe](../songs/fuer-elise-arrangement.json), then writes the editable [three-voice score](../songs/fuer-elise.json). This policy requires exactly the two named parts; another input can name its own melody and accompaniment parts and choose its own meter, pickup, bass threshold, harmony preference, instruments, and optional tempo override. It is a small deterministic arranger, not a universal orchestration engine.

- Melody selects the highest active upper-staff note.
- Bass selects the lowest lower-staff note at a measure start or below MIDI 48/C3. The first complete measure begins half a quarter beat after the initial pickup. Source durations are preserved when selected and are never extended.
- Harmony selects the highest remaining lower-staff note, then the highest remaining upper-staff note. Lower-staff treble exchanges remain audible when the upper staff rests. Sustained notes can enter an available voice after a competing note ends; their remaining source duration is used.

The selection runs at exact source note boundaries and merges adjacent intervals belonging to the same source note. New repeated notes remain distinct even when their pitches match. It introduces no pitches. The resulting voices contain 554 melody, 181 bass, and 246 harmony events. Sixty inner chord tones are omitted and one inner upper-staff C4, beginning at beat 132½, is shortened from 1½ to 1¼ quarter beats by competition for the harmony voice. Every omitted and shortened note is listed with its part, exact start, original duration, pitch, and retained duration in the score's reduction report. The full polyphonic source remains available for a different arrangement.

MIDI velocities remain in the common score. The SID recipe uses fixed voice envelopes and assigns instruments downstream; this is an explicit timbral reduction, not a reproduction of a piano recording. The current starting instruments use triangle waveforms, a stronger melody sustain, quieter bass/harmony sustains, and the shortest SID release. Native timing, gate behavior, and audio verification belong to the player/build workflow rather than this source-conversion evidence.

## Reproduce and verify

The import stage uses [Mido 1.3.3](https://pypi.org/project/mido/1.3.3/) and its dependency [packaging 24.2](https://pypi.org/project/packaging/24.2/). Arrangement itself uses only Python's standard library. Dependency directories remain ignored.

```sh
uv --cache-dir .local/uv-cache pip install --target .tools/arrangement-deps mido==1.3.3 packaging==24.2
PYTHONPATH=.tools/arrangement-deps python3 scripts/import-midi.py songs/sources/fuer-elise.mid songs/fuer-elise-import.json songs/sources/fuer-elise.score.json
python3 scripts/arrange-score.py songs/sources/fuer-elise.score.json songs/fuer-elise-arrangement.json songs/fuer-elise.json
PYTHONPATH=.tools/arrangement-deps python3 -m unittest discover -s tests -p 'arrangement_test.py' -v
bun scripts/build-arrangement.ts songs/fuer-elise.json build fuer-elise
```

The restricted session could download official wheels even when uv's package-index lookup failed. The local direct-wheel fallback used the [official Mido wheel](https://files.pythonhosted.org/packages/fd/28/45deb15c11859d2f10702b32e71de9328a9fa494f989626916db39a9617f/mido-1.3.3-py3-none-any.whl), SHA-256 `01033c9b10b049e4436fca2762194ca839b09a4334091dd3c34e7f4ae674fd8a`, and the [official packaging wheel](https://files.pythonhosted.org/packages/88/ef/eb23f262cca3c0c4eb7ab1933c3b1f03d021f2c48f54763065b6f0e321be/packaging-24.2-py3-none-any.whl), SHA-256 `09abb1bccd265c01f4a3aa3f7a7db064b36514d2cba19a2f694fe6150451a759`. Both digests were checked against PyPI metadata before installing with `uv pip install --no-deps --target .tools/arrangement-deps`.

On 2026-10-12, the import/arrangement tests first failed before implementation and later passed. An independently encoded tiny MIDI fixture checks polyphony, exact timing, velocity, trailing silence, repeat expansion, cross-hand treble, overlapping-note selection, explicit omissions, malformed inputs, and effective tempo/meter changes. Full-score tests regenerate both JSON stages identically from the unchanged originals, check both repeat entries and later episodes, preserve the shortest grace note and highest triplet pitch, and require three nonoverlapping voices plus the final written rest. These are musical-data tests; CPU execution and audible SID rendering are separate evidence.
