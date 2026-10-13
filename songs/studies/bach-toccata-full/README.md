# Toccata from BWV 565: complete single-SID interpretation

This editable interpretation covers source quarter positions 0–118: measures 1–29 and measure 30 beats 1–2, ending before the Fugue. It preserves the [accepted twelve-second hybrid opening](../bach-toccata-opening-driven/README.md), then continues through the triplets, hand-crossing runs and final D-minor cadence. The [owning study](../../../docs/research/composition/bach-toccata.md#complete-single-sid-delivery) records technical delivery and the [complete mono listening acceptance](../../../docs/research/composition/bach-toccata.md#complete-mono-acceptance-and-gyruss-comparison) received on 2026-10-14.

- [Arrangement plan](arrangement.json): authored timing anchors, musical roles, explicit source-ID overrides, octave reductions, ornaments and chord cycles. Edit this to change phrasing or voicing.
- [Three-voice score](score.json): generated performance timing, encoded as seconds at quarter BPM 60, with melody, bass and harmony lanes.
- [Hybrid native recipe](hybrid.json): the accepted PWM lead, filtered bass, harmony and diminished cycle, plus four source-backed cadence cycles. The first four instruments retain their accepted definitions and numbering order.
- [Restrained native recipe](restrained.json): the same arranged score with our sustained SID palette; an editable patch comparison, not an acoustic organ reference or an unreduced organ transcription.
- [Preparation record](preparation.json): every arranged event's source ID and derivation, every source note's retained/cycled/partial/omitted disposition, source fingerprints, timing and declared review uncertainties.
- [Complete source notes](../bach-toccata-opening/source-notes.json), [LilyPond](../bach-toccata-opening/source/ToccataFugue.ly) and [MIDI](../bach-toccata-opening/source/ToccataFugue.mid): unchanged pinned Mutopia/Bach-Gesellschaft material, retained in the existing source bundle.

The arrangement uses one MOS8580 at PAL cadence and A=440 Hz. Authored pacing compresses the source MIDI's long rests; it does not claim alignment with an organ performance. The accepted opening's pitches and sound programs remain unchanged, including its early F-sharp resolution and omitted prall ornaments. Its former release tail becomes a continuation. The final cadence keeps the source's F natural.

| Source range | Voice allocation and deliberate reduction |
| --- | --- |
| 0–10 | Frozen accepted opening: octave gestures, pedal D2 and selective diminished-tone cycling. Preserve its existing chord reduction and omitted ornaments. |
| 10–38 | RH/LH triplets and broken intervals retain independent lanes. Compress the notated rests between the rising triplet statements. |
| 38–45 | Pedal retains the bass voice; the upper decorated line remains foreground. A harmony cycle supplies selected held chord tones while additional doublings are omitted. Realize the printed m. 11 F4 trill as seven F4/G4 notes, with its LilyPond locator and authored interpretation recorded. |
| 45–60.5 | RH owns melody throughout its descent. The repeated offbeat LH A4 becomes quiet A3 accompaniment, an explicit octave reduction that cannot displace the foreground. |
| 60.5–84 | Follow the newest moving manual onset across both hands; preserve dyads on the two manual voices when the pedal allows. Additional sustained chord tones are explicitly omitted. |
| 84–106 | Pedal and selected cycling harmony support the held diminished pillar. At beat 86, expose the tied C-sharp/E notes as the first triplet notes even though their MIDI onsets were at 84; later RH/LH triplets remain independent. |
| 106–114.5 | Retain the upper chord attacks and complete pedal run. Cycle source-backed interior tones during four longer replies; omit remaining upper octave doublings. |
| 114.5–118 | Preserve upper F4–E4–D4, pedal and inner D4–C-sharp4, followed by G3–F3–E3–F3. Shorten C-sharp4's last quarter-beat at 115.75 to expose G3. Omit the final D3/A3 doublings so the moving inner line remains audible; hold the final F3 for three authored seconds. |

The complete source remains separate from these reductions. The preparation ledger accounts for every scoped note, including the single shortened C-sharp sustain; it never silently drops an omitted pitch. The Fugue's A4 pickup at source beat 118.25 is excluded. Native note selections reset sound tables, and adjacent notes at tempo 1 may retain the envelope: neither organ legato nor independent overlapping tails is promised.

Regenerate with the [source-specific preparer](../../../scripts/studies/bach/prepare-toccata.py), then build through the [native workflow](../../../docs/workflows/native-song-workflow.md). Both output directories must be fresh:

```sh
python3 scripts/studies/bach/prepare-toccata.py --output build/bach-toccata-inputs
python3 scripts/native-song.py build build/bach-toccata-inputs/hybrid.json --output build/bach-toccata-fresh
python3 -m unittest discover -s tests -p 'bach_toccata_preparation_test.py' -v
```

The preparer requires only Python's standard library and verifies the existing pinned complete source. It writes an editable plan copy, score, both recipes and preparation ledger without duplicating source assets. The output directory determines relative provenance links, so resolve those paths when comparing a temporary bundle with these checked-in inputs. Fresh sibling outputs are deterministic.

On 2026-10-14, native conversion used 52 patterns and eight instruments for the hybrid, below the single-SID limits of 100 and 36. The score contains 84.6025 seconds of music; its declared stop is PAL call 4366 after the release tail. Every note reserves at least two calls, retaining TEST silence on the first and a full-pitch body thereafter; no borrowed timing is required. The [full recipe](../../../config/listening/bach-toccata-full.json) verified all 895 arranged notes, independent VICE through call 4400, a quiet ending and zero clipping. Its [opening-preservation evidence](../../../evidence/bach-toccata-full/opening-prefix.json) matches the accepted opening's first 611 post-call SID register states. These checks establish scheduling and export correctness; human listening settles the full interpretation.

Rebuild and publish the retained audition through the [listening-package workflow](../../../docs/workflows/listening-package.md):

```sh
python3 scripts/listening-package.py config/listening/bach-toccata-full.json --output build/bach-toccata-full-v2
python3 scripts/publish-listening.py build/bach-toccata-full-v2/run.json --selection config/listening/bach-toccata-full-audition.json --output build/bach-toccata-full-listening-v2
```

Listen to the [complete Toccata WAV](../../../build/bach-toccata-full-listening/toccata.wav), inspect the [native exports and verification receipts](../../../build/bach-toccata-full-v1/listening.md), and use the [unchanged James Kibbie organ recording](../../../build/bach-source-intake/kibbie-bwv565.mp3) as the separately timed interpretive reference. The [source and listening provenance](../../../docs/research/composition/bach-toccata.md) retains attribution, license and source fingerprints. The listener accepted this full mono arrangement on 2026-10-14 with “Yes, it is nice” after the complete 88.122925-second audition. Freeze commit `5b61384` and the accepted WAV, SHA-256 `86e10f2cfe1341eb60d27f03e071dffb34181666bd605353378d5b48e0523b89`, for the now-authorized C64 Gyruss audio comparison; music revisions and stereo remain outside that request.
