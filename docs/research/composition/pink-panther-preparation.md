# The Pink Panther Theme: source preparation

Source intake is ready; the SID interpretation is queued after Moon River. No SID arrangement, sound allocation or listening verdict is established. Follow the [source-to-SID workflow](../../workflows/song-workflow.md), keeping the complete source separate from later reductions and musical changes.

## Source and scope

The optional `pink-panther-score` entry in the [asset registry](../../../config/local-assets.json) pins the [public MIDI](https://www.dongrays.com/midi/archive/tv-film/ppanther.mid) at ignored `.local/research/pink-panther/dw-barnes-ppanther.mid`. Its embedded metadata and [catalogue entry](https://www.dongrays.com/midi/archive/tv-film/) credit Henry Mancini as composer and D. W. Barnes as sequencer. This is Barnes's arrangement, not an authenticated original edition. The archive's [legal notice](https://www.dongrays.com/midi/) does not establish redistribution or adaptation permission; public availability is not an open-license claim. Keep the original MIDI, imported notes and reference audio outside Git.

Inspection on 2026-10-15 verifies a format-1 MIDI with nine tracks, six sounding parts, 96 ticks per quarter, constant 4/4 and 540,540 microseconds per quarter (approximately 111 BPM). Its complete sequential timeline spans 364 quarter beats, or 196.75656 seconds. That covers the supplied arrangement through its ending; equivalence to the original film score's form has not been established. No repeat unfolding or source truncation is applied.

| MIDI track, zero-based | Preserved part | Source role |
| --- | --- | --- |
| 1 | `piano-lead` | Piano melody, including the introduction |
| 2 | `piano-accompaniment` | Polyphonic harmonic accompaniment |
| 3 | `alto-sax` | Later melody doubling |
| 4 | `baritone-sax` | Low accompaniment |
| 5 | `bass` | Independent bass part |
| 6 | `drums` | GM percussion; retain its drum mapping from the original MIDI |

Swing is already encoded: common offbeat attacks occur at tick 64 of each 96-tick quarter. Preserve exact rational onset and duration values instead of applying a second swing transform. Additional subdivisions occur, so a universal swung-eighth quantization would also lose source timing.

## Reproduce and inspect losses

Use the existing checksum-verifying downloader and [import recipe](../../../config/scores/pink-panther-import.json):

```sh
python3 scripts/setup-project.py --only references --include pink-panther-score
python3 scripts/setup-project.py --check --only references --include pink-panther-score
PYTHONPATH=.tools/arrangement-deps python3 scripts/import-midi.py .local/research/pink-panther/dw-barnes-ppanther.mid config/scores/pink-panther-import.json build/pink-panther-source-intake/source.common-score.json
```

The 2026-10-15 smoke import preserves all 2,113 source notes across the six sounding tracks, with matched positive-duration note pairs and no added trailing rest. The importer checks the source hash and requires every sounding track to remain represented. Its generated loss report retains 25 unmapped controller messages (volume, pan, reverb and chorus), six GM program changes and one instrument-name message. Channel identities and note-off velocities are not represented in common-score v1; the original MIDI retains them. There are no source pitch-bend or sustain-controller messages. Engraved spelling, slurs, articulation marks and repeat notation cannot be recovered from this MIDI alone.

The imported score proves source preservation within that contract. Musical fidelity, voice reduction, SID sound design and full-form listening remain work for the queued interpretation.
