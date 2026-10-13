# Classical arrangement workflow

## Establish the musical source

Record the work, movement, edition/transcription, source URL, and intended excerpt before entering notes. Beethoven's Für Elise is the A-minor bagatelle WoO 59; Beethoven-Haus provides work information and the surviving sketch. Flight of the Bumblebee belongs to Rimsky-Korsakov's opera The Tale of Tsar Saltan; piano and instrumental arrangements may differ. [S22](../sources.md#s22), [S23](../sources.md#s23)

An old underlying composition does not settle rights to a modern recording, MIDI transcription, or edited score. For example, the inspected IMSLP page labels a 2023 MIDI contribution CC BY 4.0; that label applies to that contribution, not every download on the page. That MIDI has not been adopted here. The later [complete Für Elise baseline](../../songs/fuer-elise-score.md) uses separately identified Mutopia sources.

## Proposed Für Elise arrangement

Begin with the recognizable opening phrase, then expand only after pitch, rhythm, and articulation are verified against the chosen edition. The familiar pitch sequence `E5 D#5 E5 D#5 E5 B4 D5 C5 A4` is a useful sanity check; it is not a complete transcription with durations, pickup, pedal, or phrasing.

| Role | One SID | Two SIDs |
| --- | --- | --- |
| Melody | Voice 1, restrained triangle/pulse | Preserve melody; use an extra voice only when overlap requires it |
| Bass | Voice 2, clear short attack | Dedicated bass plus sustained support if musically needed |
| Accompaniment | Voice 3, selected broken-chord notes | Distribute chord tones and releases among remaining voices |

Use piano-like envelopes as an arrangement choice, without promising acoustic-piano realism. Avoid aggressive filter movement until the phrase is recognizable without it. Explicitly decide where pedal-induced overlap will be reduced, revoiced, or preserved by an additional voice.

The following PAL words are locally calculated using the clock in [the timing guide](../sid/playback-and-timing.md):

| Note | Word |
| --- | --- |
| E5 | `$2BDA` |
| D#5 | `$2964` |
| B4 | `$20DA` |
| D5 | `$2711` |
| C5 | `$22CE` |
| A4 | `$1D44` |

## Proposed Hummelflug arrangement

Preserve the rapid chromatic line, bass landmarks, and phrase accents. Decide tempo from the selected arrangement, not the title alone. First test a short chromatic run containing repeated notes and direction changes. Compare rhythmic drift and attack consistency at one and two player calls per nominal frame.

At 180 BPM, sixteenths are approximately 83.3 ms. Long restart gaps can dominate those notes. Legato pitch changes, shorter envelopes, or alternate-voice articulation are options to evaluate; none is an automatic solution for every instrument. On two SIDs, extra voices can preserve accompaniment and phrase overlap while keeping the lead clear.

## Deliverable definition

For an actual song implementation, retain the source/edition record, editable arrangement, instrument definitions, native export, exact target settings, and comparison evidence. Verify note order and duration independently of timbre. The [opening example](../../songs/first-song.md) remains a small learning fixture; the [complete Für Elise baseline](../../songs/fuer-elise-score.md) now includes both repeats and all episodes with [execution/audio evidence](../../validation/fuer-elise-validation.md). Its fixed instruments establish a reference for the [sound-design repertoire](sound-design-repertoire.md), not a finished showcase sound. Hummelflug remains unimplemented.
