# Songs, editable examples, and provenance

## Where to look

| Collection | What it contributes | What it does not establish |
| --- | --- | --- |
| HVSC | Searchable SID files, metadata, STIL commentary, song-length information | Editable source or blanket redistribution rights |
| SID Factory II maintainer downloads | Editable source tunes and driver examples | Uniform licensing across tunes |
| GoatTracker / SID-Wizard examples | Instruments, patterns, and native authoring workflows | Permission to reuse every melody in a new release |
| MiniPlayer2 repository | A small source example and converter/player relationship | A feature-complete tracker replacement |
| CGSC | Compute!'s Gazette music corpus, a distinct format tradition | Interchangeability with every PSID workflow |

HVSC's own information and FAQ explain tune rights, metadata, format distinctions, and the relationship to CGSC. The CGSC site itself was a discovery lead rather than an inspected archive in this pass. [S25](sources.md#s25), [S18](sources.md#s18), [S08](sources.md#s08), [S17](sources.md#s17), [S11](sources.md#s11)

## Small corpus before mass downloads

Proposed study set:

- One editable three-voice tracker example with simple instruments.
- One tune emphasizing waveform-table percussion.
- One tune using filter changes and a known intended chip model.
- One fast articulated melody suitable for testing repeated notes.
- One six-voice tune with documented second-SID address.
- One self-interrupting/RSID example to expose assumptions in simple players.

Select exact files through archive metadata; do not infer subtunes, composers, or original game versions from filenames alone. No six-file corpus has yet been downloaded and listened to here.

MIDIbox's wavetable tutorial includes an author-analysed bass-drum example from Auf Wiedersehen Monty. It is a useful starting point for tracing register sequences, with the distinction that the demonstrated analysis is the author's, not a local reproduction. [S09](sources.md#s09)

## Record per item

| Field | Purpose |
| --- | --- |
| Archive path, download URL, access date | Identify where the item came from |
| SHA-256 of exact bytes | Distinguish revisions or alternative rips |
| Title, composer, arranger, subtune | Separate music authorship and playback selection |
| STIL notes and original work | Preserve contextual and derivative-work information |
| Source/driver revision | Link editable data to the resulting player |
| PAL/NTSC, SID models, addresses | Reproduce timing and sound |
| Code license and tune permission | Track separate rights |
| Trace/render and tool versions | Make observations repeatable |

This is a proposed inventory schema, not an existing set of checksummed downloads. Keep code licenses, musical composition rights, arrangement rights, and recording rights separate. “Free to download” alone is insufficient evidence for reuse.
