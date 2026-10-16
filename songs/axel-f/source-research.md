# Axel F: source intake and musical target

The source composition is Harold Faltermeyer's **Axel F**, from *Beverly Hills Cop*. The intended reference is Faltermeyer's original electronic instrumental, as credited in the [UMG recording on his Official Artist Channel](https://www.youtube.com/watch?v=jEXGuemSLBQ). This is a score interpretation; an existing SID rendition is not its note source. Intake was verified on 2026-10-15. The [repeatable song routine](../../docs/workflows/song-workflow.md#repeatable-song-routine) governs the separate reduction, native sound design and listening review.

## Musical target and evidence

Faltermeyer recalls director Martin Brest asking for the minimal electronic aesthetic of Yazoo and Afrika Bambaataa. He describes the record as an assembly of separate main-theme, stab and marimba cues, with the marimba associated with the clumsy policemen in the banana scene. He also explains that the original cue tempos differed slightly and that period keyboard dynamics differ from modern velocity-sensitive performance. These are the composer's retrospective statements, not recovered performance data. [Red Bull Music Academy interview, Tokyo 2014](https://www.redbullmusicacademy.com/lectures/harold-faltermeyer-tokyo-2014/)

The working interpretation target is therefore an agile, playful, rhythmically assertive synth groove: a clear hook, springy bass, short rhythmic stabs and contrasting marimba-like material, with space between the roles. This is an arrangement inference from the documented brief. It is not a listening verdict or an instruction to imitate every original synthesizer patch. Roland's account independently identifies the cutting lead and bouncy chordal support in the recording. [Roland, “Sound Behind the Song,” 2024](https://articles.roland.com/axel-f-by-harold-faltermeyer/)

## Retained score source

The selected source is an anonymous web MIDI arrangement labelled **WinJammer Demo** in every track-name field, bundled as `Axelf.mid` with Glen's [MIDI-2-CoCo Converter](https://github.com/nowhereman999/MIDI-2-CoCo-Converter). The [author's converter article](https://nowhereman999.wordpress.com/2017/12/15/midi-2-coco-converter/) also names that file as an example input. This establishes the download's context; it does not identify the MIDI arranger or make the arrangement Faltermeyer's original manuscript.

| Field | Verified value |
| --- | --- |
| Source file | Private `.local/research/axel-f/winjammer-axelf.mid` |
| Download | [Commit-pinned MIDI](https://raw.githubusercontent.com/nowhereman999/MIDI-2-CoCo-Converter/af8c1c987d16f5affc91d8308addc3b228727195/Axelf.mid) |
| Source commit | `af8c1c987d16f5affc91d8308addc3b228727195`, uploaded 2021-06-09 |
| SHA-256 | `8bf2fa73160461e13ace1609393879e12929ada5241e80f397cd3c0e4dfe429d` |
| Bytes / format | 35,333 bytes; synchronous MIDI type 1; 96 ticks per quarter |
| Tempo / meter | Constant 504,201 microseconds per quarter, approximately 119.00016 BPM; 4/4 |
| Musical extent | 353.3125 quarter-note beats; 178.140516 seconds |
| Imported notes | 5,199 notes across ten sounding tracks; all preserved in the complete common score |
| Key | Theme and main bass center on F minor; the MIDI's C-major key-signature event is not a reliable description |
| Import mapping | [Notes-free importer configuration](../../config/scores/axel-f-import.json) |

The F-minor center and roughly three-minute form agree with an independently offered [Faltermeyer-style original-theme arrangement](https://d-o-o.de/4119-ai-axel-f-%281984%29-beverly-hills-cop-soundtrack-harold-faltermeyer-midi-midifile-style.html), which lists F minor, 117 BPM and 3:04. This is a coarse identity check, not note-by-note verification against that publisher's score. The selected MIDI has the recognizable original hook, separate chord-stab and marimba-like sections, main bass and a finite final theme/percussion passage. Its edition and exact original-recording fidelity remain unverified; it must be labelled as this particular web arrangement.

| MIDI track | Source instrument-name metadata | Imported part ID | Notes | Role and reduction consideration |
| --- | --- | --- | --- | --- |
| 1 | Drums | `drums` | 3,055 | Dense percussion; preserve privately and disclose omission from a pitched three-voice audition. |
| 2 | Synth Bass | `synth-bass` | 478 | Monophonic throughout; main continuous bass from beat 36. Contains expressive pitch-wheel events. |
| 3 | Bright Strings | `theme` | 207 | Recognizable hook. Opening includes an octave doubling; beats 68–100 are monophonic. |
| 4 | Bright Strings 2 | `chord-stabs` | 441 | Short simultaneous chord tones; highest-at-onset is an explicit possible three-voice reduction. |
| 5 | Bright Strings 3 | `held-chord-and-descent` | 10 | Held chord and later high descent, including overlapping durations. |
| 6 | Synth Bass 2 | `second-bass` | 141 | Later layered bass role; simultaneous/overlapping notes require a declared reduction. |
| 7 | Light Bongy thing | `marimba-like` | 112 | Independent monophonic later figure, beginning at beat 208. |
| 8 | Bright Lead (Picc/Trump) | `high-lead` | 100 | Later high-register melody, with some overlapping durations. |
| 9 | Whoooosh | `noise-sweep` | 619 | Repeated percussion-channel note events forming a sweep; ordinary pitched-note rendering does not recreate its sound. |
| 10 | Hit Brass | `brass-stabs` | 36 | Later monophonic short stabs, beginning at beat 256. |

Part IDs describe the source's musical roles; the source metadata's generic GM patch names are not a verified list of the original recording's synthesizers. Tracks 3–5 share MIDI channel 3 and its GM program; keeping them as separate score parts preserves the file's authored separation without implying independent original instruments.

## Representative audition and full-form boundary

The recommended first passage is source beats **68–132**, exactly 64 beats or 32.268864 seconds before release/tail. It preserves a complete 32-beat theme region followed by the 32-beat chord-stab region over the continuous main bass. The theme and chord stabs alternate in this edition; their silence in the other region is source content, not missing accompaniment to fill with invented notes. Use `theme`, `chord-stabs` and `synth-bass` as distinct physical voice roles. Preserve all ten source parts in the complete common score and report every audition omission separately.

This passage tests the hook, bass and stab palette but omits the later marimba-like and high-lead material and the arrangement's ending. It is a palette audition, not a complete-song deliverable or proof that the ending works. The full source includes the initial hook, bass/percussion entry, theme return, stabs, transition, further theme return, marimba/high-lead contrast, further stabs and final theme/percussion tail. A complete arrangement must account for those roles and the finite source ending separately.

## Import losses and rights boundary

The existing importer succeeds without source modification and retains exact note onsets, durations, pitches and velocities at 96 PPQ. It reports 780 unmapped pitch-wheel events, all on `synth-bass`, including 208 inside the first selected passage. The note score consequently omits the source's bass bends. It also reports 333 aftertouch events, 28 controller events, six GM program changes, ten instrument-name messages, eleven MIDI-port messages and the stale key-signature message. MIDI channel identity, pan and GM performance settings are not retained as executable expression in the common score. The original file remains the authority for those features; neither plain rendering nor native reduction should be presented as a lossless source performance.

The source's constant tempo also omits the small cue-dependent changes described by Faltermeyer. Slurs, engraved articulation, enharmonic spelling, printed repeat directions and pedal notation cannot be recovered from this MIDI. A score-based audition can assess the retained musical material, while the official original recording remains the expressive reference.

No permission to redistribute the composition or this MIDI arrangement has been established. Apply the [always-included public package tier](../../docs/workflows/publication-boundary.md): source references, hash, notes-free recipes, our tools and reusable instruments may be public; downloaded MIDI, imported scores, native musical sources, SID/PRG files and rendered song audio remain private under ignored directories. The converter repository's availability does not clear the embedded musical arrangement.

Reproduce the complete private import with the existing tool:

```sh
PYTHONPATH=.tools/arrangement-deps python3 scripts/import-midi.py .local/research/axel-f/winjammer-axelf.mid config/scores/axel-f-import.json build/axel-f-source-intake/full-common-score.json
```

The import report is embedded in that private common score. The native audition's existing recipe should call the shared score-preparation tool so that selection, explicit omissions, compiled timing, audio and playback checks remain reproducible together. Source intake settles viability and documented conversion scope; human listening still settles whether the SID interpretation carries the intended character.
