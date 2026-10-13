# Bach Toccata workbench trial

The [active trial](../study-plan.md#bach-toccata-next-workbench-trial) aims for a fancy, grand balance of church-organ weight, sustained harmony and dramatic pacing with tasteful SID pulse motion, register contrast and selective arpeggiation. Held chords must retain substance. The first listening question is: **Does the opening feel grand and expressive, with the right organ/chiptune balance?** This is a musical brief, not an accepted sound design. Organ score and performance are the source inputs; [written Gyruss commentary](bach-gyruss-commentary.md) may inform the brief under the user's later authorization, while its SID/audio remains excluded.

## Selected score and exact scope

Source intake on **2026-10-14** selected [Mutopia 1780](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1780): Anonymous's public-domain organ typesetting, based on the **Bach-Gesellschaft Ausgabe, 1867**, reference `Mutopia-2011/09/11-1780`. Preserve its complete LilyPond, MIDI and PDF. The source declares LilyPond `2.12.2`; the catalogue reports the published engraving used `2.14.2`. The independent comparison scan is [IMSLP #01335](https://imslp.org/wiki/File:BWV0565.pdf): Wilhelm Rust, Bach-Gesellschaft Ausgabe, volume 15, Leipzig: Breitkopf und Härtel, 1867, pp. 267–275, plate B.W. XV; IMSLP labels the edition public domain. Opening notation and the section boundary were visually compared with scan pages 267 and 269. This is not a note-by-note audit of the entire typesetting.

**The Toccata comprises measures 1–29 and measure 30 beats 1–2.** The final cadence continues into that half-measure: pedal D2 and manual D3/A3/D4 sustain while the lower manual line resolves G3–F3–E3–F3. Stop at **measure 30 beat 3**, retain a deliberate final hold/decay, and omit the Fugue's following sixteenth-rest pickup and A4–G4–A4–F4 subject. The boundary is visible on BGA p. 269, third system, third measure, and Mutopia PDF p. 3, fourth system, third measure. With zero-based quarter positions it is `118`; in the downloaded MIDI it is tick **45312** at 384 ticks per quarter. The first Fugue A4 occurs at quarter `118.25`, tick **45408**. A cutoff after measure 29 would lose the cadence; a cutoff after all of measure 30 would include the Fugue. Label the deliverable **Toccata from BWV 565**, not the complete Toccata and Fugue.

## Retained source files

Files are unchanged downloads under ignored `build/bach-source-intake/`. The complete public-domain [LilyPond](../../../songs/studies/bach-toccata-opening/source/ToccataFugue.ly) and [MIDI](../../../songs/studies/bach-toccata-opening/source/ToccataFugue.mid) are also retained with the opening study; all reference recordings remain ignored. Re-download each linked asset with `curl -fLsS --compressed --max-time 60 URL -o build/bach-source-intake/FILENAME`, then verify its SHA-256. No source audio has been committed or played during this intake.

| Local filename / direct source | SHA-256 |
| --- | --- |
| [ToccataFugue.ly](https://www.mutopiaproject.org/ftp/BachJS/BWV565/ToccataFugue/ToccataFugue.ly) | `1640bbd2bf11a95e18db03fea285d30718254af0a694e1c36533d8109d71718c` |
| [ToccataFugue.mid](https://www.mutopiaproject.org/ftp/BachJS/BWV565/ToccataFugue/ToccataFugue.mid) | `1aabd00967aded08d6633482c211af46f679d97f01cfeaca43c83a59dfeeeb6b` |
| [ToccataFugue-a4.pdf](https://www.mutopiaproject.org/ftp/BachJS/BWV565/ToccataFugue/ToccataFugue-a4.pdf) | `85cda3cfbe08bb1b9e2ebcea04c79891b686b4393a35429aeb43b77ab5dc9367` |
| [bwv565-bga-1867.pdf](https://ks15.imslp.org/files/imglnks/usimg/f/f4/IMSLP01335-BWV0565.pdf) | `668d55b0cc54201400c32e5c93ec13c496a7057229c453da20ee2c8491729d2e` |
| [kibbie-bwv565.mp3](https://files.freemusicarchive.org/storage-freemusicarchive-org/music/ccCommunity/James_Kibbie/Bach_Organ_Works_Fantasias_and_Fugues_Toccatas_and_Fugues/James_Kibbie_-_13_-_BWV_565_Toccata_and_Fugue_in_D_Minor.mp3) | `0f9575da2318c6856913df802078a35c10b815db7b988af8defd4e24137f9c43` |

The MIDI contains RH, LH and pedal tracks plus a control track, and one constant tempo event, quarter = 60. It does **not** perform the source's fermatas, prall ornaments or textual Adagio/Prestissimo changes. Its exact durations provide notation coordinates, not an organist's interpretation. The bounded extraction `build/bach-source-intake/opening-events.json` retains 348 original MIDI note events from source measures 1–12 with tick onset, duration, pitch, track and velocity; its source fingerprint is embedded. Use the LilyPond/scan for missing ornaments and performance decisions. Preserve any imported source score separately from reductions, octave changes and authored timing.

## Opening musical map

The following map comes from the source score and downloaded MIDI; the opening pitches and chord placements were checked against the historical scan. Durations below are notation coordinates. Performed pauses and tempo have not been measured or listening-reviewed.

| Source passage | Material and audition purpose |
| --- | --- |
| m. 1, opening | A5/A4 octave statement with prall and fermata, then G–F–E–D–C♯–D in octaves and a fermata pause. A lower A4/A3 answer moves E–F–C♯–D. Preserve attack clarity, octave weight and the space between gestures. |
| m. 2–3 | Another octave descent begins on A3/A2. Pedal D2 enters at quarter position 6 and lasts to 10; the rolled manual chord enters at position 7: C♯3/E3/G3/B♭3/C♯4/E4, largely tied to position 9, then D3/A3/D4 resolution with inner G3–E3–F♯3, adding a major-third color. Preserve that F♯, which differs from the F natural in the final pre-Fugue cadence. This is the early held-harmony stress test; the chord has seven simultaneous pitches with pedal, requiring an explicit three-voice reduction. |
| m. 4–7 | Prestissimo repeated triplet cells D–E–C♯, F–G–E, A–B♭–G rise in register, break at fermatas, then repeat higher. Contrast fast motion with the held material; do not apply the MIDI's quarter = 60 to this passage as an interpreted tempo. |
| m. 8–12 | Descending broken intervals lead to a second dense chord over D2 at m. 10–11; a decorated upper voice and m. 12 D-minor arrival complete a more demanding audition than the opening motif alone. Keep pauses and sustained bass audible. |

The initial audition uses **the opening material from m. 1–3 through the cadence at quarter position 10**, with the octave gestures, rapid ornamental descents, held chord and final decay; omit the next C♯ pickup at position 11.75. This is a short sound/phrasing gate, not the complete Toccata. **m. 1–12** is a useful next expansion for the second chord span and faster register movement. Start the unaltered organ recording from its beginning; an exact score-aligned ending cue is not yet verified. Do not compare equal timestamps from the score MIDI and the organ performance or imply an exact musical alignment.

## Organ performance reference

Recommended local interpretive reference: **James Kibbie, “BWV 565: Toccata and Fugue in D Minor,” The Complete Organ Works of J. S. Bach**, [FMA track](https://freemusicarchive.org/music/James_Kibbie/Bach_Organ_Works_Fantasias_and_Fugues_Toccatas_and_Fugues/BWV0565/), from the [University of Michigan project](https://smtd.umich.edu/bach-organ-works/). The official project identifies performances on original baroque organs in Germany and gives its license as [CC BY-NC-ND 3.0](https://creativecommons.org/licenses/by-nc-nd/3.0/); the downloaded MP3's copyright tag agrees. Local file: 44.1 kHz stereo, 256 kbps MP3, measured container duration **556.072563 s**. The original file retains its level, complete duration, pitch and room sound. Use it unchanged with passage playback cues for shared reference access. The license permits noncommercial attributed sharing but prohibits distributing modified material; retain attribution and the license alongside it. Venue, registration and exact opening cue remain unverified. A preliminary spectral observation near **466–468 Hz** in the opening's A4 region suggests a higher reference pitch than modern A4 = 440 Hz; it does not establish the organ's exact tuning or venue. Keep reference pitch and SID tuning separate until checked.

An alternative local download, `ashtar-moira-bwv565.ogg`, comes from [Ashtar Moïra's personal Tamburini-organ recording on Commons](https://commons.wikimedia.org/wiki/File:Toccata_et_Fugue_BWV565.ogg), dated 2006-12-29: 44.1 kHz stereo Ogg Vorbis, **513.560091 s**, SHA-256 `12bfa09ff64f6c59267302f37b3d74de55af2e01f8cf6ce1e8b33742846630b8`. Commons displays a public-domain mark, but its original `PD-old` tag establishes the composition's age rather than an explicit modern performance-rights grant. Prefer Kibbie's explicit license for this trial's reference; do not treat the alternative's tag as verified permission for edited redistribution.

## Model-assistance reviews

Apply [use and reassess model assistance](../audio-assessment.md#use-and-reassess-model-assistance) at the first representative audition, after listener feedback or a musical revision and before closure. Assess usefulness at each checkpoint; a paid call is not mandatory. Qwen remains advisory only, and SongBench is eligible for defect research, not musical acceptance. Human listening settles the organ/chiptune balance.

| Date / checkpoint | Decision and basis | Next checkpoint |
| --- | --- | --- |
| 2026-10-14 / source intake | Defer audio-model assessment: no candidate audio exists yet. Score provenance and MIDI metadata checks do not require an audio judge. | First representative audition; then listener feedback or a musical revision and pre-closure review. |

## First single-SID audition: rendered, awaiting feedback

The [editable opening study](../../../songs/studies/bach-toccata-opening/README.md) contains one source-backed 24-second score and two original palettes. Both cover source quarter positions 0–10, ending before the following C-sharp pickup. The restrained version supplies sustained reduced harmony; the hybrid adds gentle lead PWM and a G3/B-flat3/C-sharp4/E4 cycle only during the diminished hold at arrangement seconds 18–22. The printed prall ornaments and rolled chord onset are omitted in this first version. Full notes, omissions, authored timing and instrument choices remain separate in the [preparation record](../../../songs/studies/bach-toccata-opening/preparation.json). This comparison changes both timbre and represented harmony; it is not a pure PWM experiment.

Local listening files:

- [Restrained then hybrid](../../../build/bach-toccata-opening-listening/restrained-then-hybrid.ab.wav), **55.53 seconds**, with a half-second separator and documented level matching. Both halves are our SID interpretations.
- [Hybrid candidate](../../../build/bach-toccata-opening-listening/hybrid.wav) and [restrained version](../../../build/bach-toccata-opening-listening/restrained.wav), **27.51 seconds each**, including release and verification silence; original renderer levels are preserved.
- [Actual organ reference: James Kibbie](../../../build/bach-source-intake/kibbie-bwv565.mp3), unchanged full recording, from the beginning. It has its own phrasing, tuning and acoustic space; a precisely score-aligned ending cue is not verified, so no cropped reference/candidate A/B is claimed. The organ recording is an interpretive reference, not a target for PCM equality.

The [five-stage recipe](../../../config/listening/bach-toccata-opening.json) completed in **19.79 seconds** on 2026-10-14. It uses the existing native converter/exporter, CPU audit, renderer, VICE verifier and comparison tool. Both versions consume all 21 melody, 20 bass and four harmony events, stop at tick 1328 and retain clear gates/volume afterward. Independent VICE checkpoints reach call 1350, beyond the stop. Both renders have zero clipped samples and zero AC RMS in the final half-second. [Native hybrid evidence](../../../evidence/bach-toccata-opening/hybrid/verification.json), [VICE evidence](../../../evidence/bach-toccata-opening/hybrid/vice.json), [full run](../../../evidence/bach-toccata-opening/run.json) and [comparison gains](../../../evidence/bach-toccata-opening/comparison.json) retain the exact scope.

The [hybrid sound check](../../../evidence/bach-toccata-opening/hybrid/sound-check.json) observes pulse movement and four chord-frequency values where the [restrained check](../../../evidence/bach-toccata-opening/restrained/sound-check.json) remains static. Complete store/state archives allow reinspection. These checks establish that the intended programs execute, not that the musical balance succeeds. No physical SID or human acceptance is claimed. The native onset and rearticulation limits remain as described in the opening README.

| Date / checkpoint | Task and setup | Run or skip / evidence | Useful action and limits | Next checkpoint |
| --- | --- | --- | --- | --- |
| 2026-10-14 / first opening audition | Organ/chiptune balance; Qwen and SongBench remain unvalidated for this task | Skip audio-model inference: no validated criterion would improve this decision. Use source, complete CPU schedule, VICE and PCM checks above; request human listening. | Model-assisted source review retained the written F-sharp opening resolution and the exact later Toccata/Fugue boundary. Those claims were checked against the score; no audio-model quality claim or time-saving estimate follows. | After this audition's feedback or a musical revision, then before single-SID closure. Choose any next bounded audio-model experiment from a concrete discrepancy rather than repeat the known failed pulse question. |

The first model-assistance review is accounted for; it does not grant model eligibility for artistic judgment. Continue to the wider fast-motion sections and complete Toccata only after this initial direction has a listening verdict. Full-form, final-cadence and optional stereo reviews remain pending.
