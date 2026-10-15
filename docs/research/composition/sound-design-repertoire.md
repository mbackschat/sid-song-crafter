# A reusable SID sound-design repertoire

Research date: 2026-10-12. The aim is a library of expressive, editable instruments and arrangement techniques that make the next song easier and better. A list of hexadecimal presets is insufficient: each sound needs a musical use, a performance program, target assumptions, and evidence. Start with [the composer studies](../composers/README.md), [advanced techniques](../sid/advanced-techniques.md), and [the tool assessment](../tools/composition-tools.md).

The master-composer studies are the primary knowledge base and strongest influence on arrangement and sound selection. Supplemental popular-song interpretations can expose a useful contrast, but retain their narrower scope and do not outrank the masters by convenience. Use each source’s measured mechanisms and listening verdict, not reputation alone, to decide whether a technique fits the current role.

## Evidence levels

| Label | Meaning |
| --- | --- |
| Documented reference | A cited composer account, published analysis, manual, or source implementation explains the technique |
| Proposed experiment | An original design brief derived from that research; no audible result is claimed |
| Rendered experiment | Editable source and reproducible audio exist, with declared model and player |
| Listening-reviewed instrument | The rendered result has been judged in a phrase and in a mix, with the verdict recorded |
| Hardware-checked instrument | The actual declared chip/machine setup was tested and recorded |

The current [Für Elise baseline](../../validation/fuer-elise-validation.md) establishes note scheduling, complete playback, and rendered audio. Its fixed triangle instruments are not promoted to a showcase repertoire merely because those tests pass. The [original native bank](instruments/README.md) supplies rendered experiments for moving pulse with delayed vibrato, bright-attack pluck, kick-to-bass sharing and a falling kick, plus a three-voice mix. These have CPU and PCM evidence; the [listening findings](gestures/README.md) distinguish a cleaner preferred attack, audible pulse motion without a preference, and a bass transient with little perceived effect. The remaining briefs below are proposed.

Use the [musical gesture library](gestures/README.md) for groove, chord responses and phrase variation. The [sustained chord instrument](instruments/chord-01-sustained-arpeggio.md) supplies a rendered CHORD-01 example with complete pitch/waveform-cycle guards. Its paired arrangements were judged not close to the desired DRAX fragment; that verdict rejects those matches rather than settling every use of the chord mechanism. The [executed-program study](../tools/sid-program-analysis.md) now owns the DRAX bass explanation and controlled mechanism comparisons. A reusable repertoire includes how to improvise around a recognizable theme, not only how to synthesize its notes. Preserve the source separately and make intentional interpretation changes explicit.

## Reuse executed reference programs

| Family | Find the editable mechanisms and performance constraints |
| --- | --- |
| [DRAX decoded trio](instruments/drax-decoded-trio.md) | Releasing bass, pulse lead and chord cycle from the preferred Für Elise texture; the card owns its bounded listening findings. |
| [Flashdance decoded programs](instruments/flashdance-decoded-programs.md) | Staged lead, broad moving bass and four-tone pulse chords; the original C–F–D minor–G–C transfer has execution/audio evidence and was judged to work; its melody intentionally differs from Flashdance. |
| [Shades pulse and pitch programs](instruments/shades-decoded-programs.md) | Moving pulse, delayed vibrato and target portamento with shared-filter ownership; independent reconstruction and fade accepted; familiar Für Elise transfer and ending accepted; the invented transfer retains an unsuccessful ending as a limitation. |
| [Cybernoid pulse programs](instruments/cybernoid-decoded-programs.md) | Short noise-onset bass, shared-filter harmony and steady-pitch PWM lead; accepted 53-note familiar transfer with a matched plain reference and explicit native gate/tuning limits. |
| [Monty tonal programs](instruments/monty-decoded-programs.md) | Narrow pulse bass, harmonic replies and shared moving-pulse melody; accepted 53-note familiar transfer with native articulation, retained pulse phase and explicit rest/ending limits. |
| [Rambo tonal programs](instruments/rambo-decoded-programs.md) | Moving pulse melody and bass, plus short tonal support; matched 53-note transfer accepted for musical use, balance, phrasing and ending, with native lifetime/gate constraints. |
| [Ghouls pulse and staged-onset programs](instruments/ghouls-decoded-programs.md) | Moving pulse melody/support and a one-call noise-to-triangle bass attack; instruments, balance and adapted ending accepted with a tentative tune reservation. Independent review matches all 53 source notes; native tuning is about 35 cents sharp in both versions. |
| [Deflektor tonal programs](instruments/deflektor-decoded-programs.md) | Moving pulse trio with low-byte-only PWM and delayed raw-word pitch; familiar 53-note transfer accepted for instruments, balance and ending, with explicit native articulation and final-release adaptation. |
| [Take On Me tonal programs](instruments/take-on-me-decoded-programs.md) | One-way pulse lead and harmonic replies with delayed vibrato, plus moving-pulse filtered bass; matched A440 familiar transfer accepted for instruments, balance and ending. |
| [Billie Jean pulse lead and filtered support](instruments/billie-jean-decoded-programs.md) | Native pitch accents, delayed vibrato and shared-filter-compatible support; matched familiar transfer accepted (“plays nice”). An unfiltered patch can still reset shared cutoff at note setup. |
| [Airwolf static tones](instruments/airwolf-static-tones.md) | Fixed pulse widths and triangle support with note-triggered envelopes; matched familiar transfer accepted as “music is nice”. Preserve init timing and distinguish hold from a gated rest. |
| [Ghostbusters static patches and shared-phase vibrato](instruments/ghostbusters-decoded-programs.md) | Fixed pulse/saw/noise patches, one-sided shared-phase vibrato and native score-owned release; execution verified; familiar transfer accepted for instruments, balance and ending. |

## Reference material worth learning from

The [Pink Panther BASIC contrast](../../../songs/pink-panther/README.md#learn-from-the-selected-basic-interpretation) is supporting evidence for static narrow pulse and selective articulation. The listener likes that source’s lead but finds the static-patch transfer much less vibrant. [Voice-isolation evidence](../../../songs/pink-panther/README.md#locate-the-missing-vibrato-like-character) investigates the missing motion; do not promote the patch bytes alone as the complete instrument. Its lack of PWM/filter/vibrato illustrates why “more effects” is not a sufficient selection rule.

The [organ-weight/forward-motion gesture](gestures/driven-organ-phrasing.md) records an original Bach application of moving pulse, filtered pedal foundation and selective chord cycling. The faster opening is accepted; its timing maps and native palette are editable. It also preserves the rejected slow pacing, so future reuse starts with the musical limitation as well as the patch settings.

The [post-acceptance Gyruss contrast](bach-gyruss-commentary.md#post-acceptance-arrangement-and-sound-analysis) adds an arrangement lesson: a dedicated electronic entrance effect, evolving voice roles and recurring bass can supply excitement beyond a sustained organ palette. The listener favors Gyruss’s effect-rich beginning for a game-music intention, while valuing our more source-faithful SID interpretation. Its bounded execution is understood. Our later [Bach trials](bach-toccata.md#integrated-lead-motion-opening-accepted-full-extension-rendered) liked stronger ongoing lead width motion but rejected short pitched replies and foreground attacks; no independently recreated Gyruss patch has been listening-approved. Select and test the musical timescale and role as well as the effect mechanism.

- [Hülsbeck and Tel](../composers/huelsbeck-tel.md): programmable instruments, shared voice roles, groove, and the relationship between Soundmonitor and custom drivers.
- [Hubbard and Galway](../composers/hubbard-galway.md): staged transients, larger-ensemble illusion, filter character, custom music languages, and original player sources.
- [Follin and Daglish](../composers/follin-daglish.md): expressive melodic lines, percussion identity, contrasting sections, and collaboration with tool programmers.
- [Åkesson](../composers/linus-akesson.md): coordinated timbre/form, cycle-sensitive synthesis, and using two chips as separate mix domains.
- [SID-Wizard's example instruments](https://github.com/anarkiwi/sid-wizard/tree/2bf1703dca907d59b587d7829989215ec855a009/native/examples/instruments): a concrete editable study collection. Inspect the original package and notices before adopting individual sounds; descriptive filenames are not proof of quality or suitability.
- [SID Factory II's source tunes](https://github.com/Chordian/sidfactory2/tree/d6852faea2f8929df30e6f2ce008f93d974637d3/SIDFactoryII/music): study instruments in arrangements, with the matching driver and source attribution.

## Initial experiment bank

These briefs are our proposed designs, not claims of recovered historical presets. Make short original phrases for each so the useful technique can be reused without copying a composer's melody.

| ID | Instrument or arrangement exercise | Variables to compare | Musical acceptance question |
| --- | --- | --- | --- |
| LEAD-01 | Singing lead | Delayed vibrato, selected slides, tied versus restarted notes | Does expression clarify the phrase while preserving its pitch and rhythm? |
| LEAD-02 | Moving pulse lead | Width range, sweep rate, reset phase, note-dependent width | Is movement audible without weakening low notes or making high notes abrasive? |
| LEAD-03 | Bright attack with softer body | Brief attack waveform, body waveform, transition timing | Does the transient add definition without a distracting click or false pitch? |
| PLUCK-01 | Percussive keyboard/pluck | Attack/body contrast, decay, release, repeated-note spacing | Are fast notes even and distinct across the actual melody register? |
| BASS-01 | Articulated bass | Gate length, pulse motion, occasional slide, filter contour | Is harmonic motion clear beneath the lead, including after a rest? |
| BASS-02 | Bass and drum on one voice | Transient duration, bass recovery, accent placement | Does the beat gain energy without losing important bass arrivals? |
| DRUM-01 | Programmed kick | Tonal/noise stages, falling pitch, envelope and tail | Is there a clear attack and useful low body without masking the bass? |
| DRUM-02 | Snare/hat contrast | Noise duration, pitched body, register, envelope | Are the sounds distinguishable at mix level without dominating the tune? |
| METAL-01 | Bell or cowbell-like accent | Sync/ring candidate, oscillator ratio, pitch trajectory | Is the character useful enough to justify the modulator voice it may consume? |
| CHORD-01 | Implied harmony | Arpeggio inversion, note order, timing, accent and register | Can the harmony be followed without a harsh, unvarying buzz? |
| SPACE-01 | Echo or answering voice | Delayed repeated notes, timbre change, sparse placement | Does the effect create depth without hiding the next phrase? |
| FORM-01 | Returning theme with a changed texture | Register, accompaniment density, instrument and filter scene | Is the return recognisable and emotionally different? |
| DUAL-01 | Two-chip mix groups | Independent filter/volume control, allocation, deliberate silence | Is the second chip adding musical control rather than only more notes? |
| ADV-01 | Cycle-sensitive sample experiment | Timing, sample method, model, CPU contention | Does it remain stable in its declared full-machine environment? |

Start with LEAD-01, LEAD-02, PLUCK-01, BASS-02, and DRUM-01. Together they test the expressive features missing from the baseline while remaining small enough to compare carefully. Do not add every effect to Für Elise at once: select a coherent palette and give different sections intentional roles.

## Multiplex instrument roles within three voices

The arrangement target is additional instrument roles through time-sharing of the existing voices. For example, keep melody on voice 1 and harmony on voice 2 while voice 3 alternates short percussion attacks with pitched bass bodies. Four perceptual roles do not require four simultaneous oscillators. This is distinct from adding a sample-based fourth channel.

[Linus Åkesson's Platform Hopping explanation](https://linusakesson.net/music/platform-hopping/index.php) documents replacing the first few milliseconds of pulse notes with noise for hi-hat attacks and reserving free voice time for longer cymbals. The useful principle is to place interruptions where their rhythmic benefit outweighs the missing pitched sound. A driver must coordinate waveform, pitch, pulse width, gate/envelope and filter routing at each handoff; two roles share one physical envelope and cannot retain independent audible tails.

For BASS-02, judge whether percussion reads as a distinct rhythmic part and whether the bass remains convincing after each handoff. A noise-to-pulse instrument is a building block, not proof of an independently perceived drum part. The [DRAX listening finding](fuer-elise-reference.md#identify-the-preferred-layer-by-listening) establishes that its preferred vibrancy is already present in the bass solo. Follow the [executed bass mechanism](../tools/sid-program-analysis.md#follow-the-bass-program) before using additional musical roles as a remedy for that timbre.

## Shape short-note endings in context

**Reusable lesson from listener feedback, 2026-10-14:** rhythmic separation and convincing acoustic decay are independent requirements. The [Bach groove feedback](../../../songs/studies/bach-toccata-groove-blend/listening-review.json) found a repeated accompaniment abruptly cut off even though the native audit verified clean gate gaps. Do not use gate-off, silence before the next note, or lack of clipping as an oracle for musical articulation. This evidence supports a workflow correction; it does not establish one preferred release value for all music.

| Listener description / musical need | Inspect first | Bounded response and acceptance check |
| --- | --- | --- |
| Repeated background tick, drum-like tone, abrupt cutoff | Identify the voice by register and repetition timing; compare at least two actual attacks, body frames, gate-off events and next retriggers. A tonal pulse may be perceived as percussion; do not infer the noise waveform from the word “noise”. | Preserve the rhythm and other voices, then isolate an envelope change. Compare in the mix with both the prior candidate and the accepted reference. |
| “Wanna be drum”; thin percussion; missing bass despite low notes | Separate perceived musical role and body/weight from attack or release quality. A voice named bass or a low MIDI note does not establish audible bass support. | If smoothing helps but the sound remains unwanted, subtract the suspected part in a matched mix before another timbral embellishment. Treat attribution as provisional until the listening comparison supports it. Removal is a diagnostic; if the brief requires rhythmic drive, use the result to design a better-supported rhythmic role rather than assuming emptiness is the artistic solution. |
| Clear groove without chopped-off notes | Consider gate duration and release separately, including hard restart, TEST or waveform changes at the next onset. Check the actual body after the player's onset delay. | Prefer the smallest change that improves decay while preserving definition; lengthening release is a hypothesis, not a guaranteed fix. Hear dense repetitions as well as the final pulse before a gap. |
| No difference heard after adding an instrument; inaudible kick; weak body | Verify the published A/B contains the intended distinct renders, then measure the actual in-context signal contribution around the intended events and inspect routing, envelope behavior and overlap with existing voices. | A gate-on low-frequency register sequence does not establish audible body. Retain the human no-difference verdict, distinguish PCM difference from perception, and diagnose before another audition or a louder replacement. Treat masking as a hypothesis until supported. |
| Louder beating; annoying accompaniment; competes with main tune | Check foreground hierarchy and repeated attack placement, not just low-body energy. | Preserve the preferred mix and reconsider the role or phrase the existing bass; do not continue raising level or harmonics. The [Bach pulse-body rejection](../../../songs/studies/bach-toccata-groove-punch/listening-review.json) demonstrates that a stronger measured body can make the music worse. |
| A technically clean instrument sounds detached from the music | Check the timescale and musical role of the effect, not merely its register correctness. | Audition the phrase in context. Preserve failed musical approaches so future work does not repeat them in another voice. |

Record the listener's words and approximate timestamps separately from measured event timing; state uncertainty when more than one voice could match. Retain the isolated intervention and its execution evidence, but promote a patch as musically useful only after a scoped listening verdict. The [Bach release-only example](../../../songs/studies/bach-toccata-groove-release/README.md) is editable and reproducible, with improved release but rejected overall musical use. The listener subsequently found the release better but rejected the sound overall as a “wanna be drum” missing bass; see the [scoped verdict](../../../songs/studies/bach-toccata-groove-release/listening-review.json). Its register comparison is a reusable check through the [native intervention workflow](../../workflows/native-song-workflow.md#check-a-controlled-register-change).

The [controlled subtraction verdict](../../../songs/studies/bach-toccata-groove-subtraction/listening-review.json) subsequently confirmed that removing the repeated upper part eliminated the unwanted sound and made the passage much better, with low bass and lead preserved. Once subtraction improves the music, preserve that version as the comparison baseline; a replacement must demonstrate a benefit rather than fill a vacant voice by default. This is a passage-specific result, not a rule against percussion.

A comparative “better” verdict can coexist with rejection of the whole sound. Preserve both rather than promoting the revised patch as accepted. Repeatedly smoothing or relocating an unwanted short effect can optimize the wrong musical idea; reassess its role and body before another parameter edit. This is a process lesson from the [Bach feedback](../../../songs/studies/bach-toccata-groove-release/listening-review.json), not a universal objection to SID percussion.

The subsequent [Bach kick feedback](../../../songs/studies/bach-toccata-groove-kick/listening-review.json) reported no difference despite executed low-pitch stages. This adds a separate requirement: verify actual contribution in the mix before presenting an added role as effective. Technical register boundaries, signal contribution, audibility and musical preference are four different claims.

## How to evaluate a candidate

Use the same notes, tempo, register, and arrangement when isolating an effect in an A/B comparison. A creative arrangement comparison may deliberately change them: declare those differences and judge the resulting phrase as a whole. Retain original-amplitude renders and document any gain adjustment used for level matching. A louder file should not win by default. Soloing helps diagnose a sound, but the full mix decides whether it belongs in the song.

When isolating a coupled instrument, preserve its ring/sync modulator's oscillator state and the intended shared-filter configuration. Muting a companion's output is different from stopping its oscillator or removing its register writes; the latter can change the sound being studied.

Judge each candidate on attack consistency, pitch intelligibility, rhythmic clarity, timbral interest, useful note range, sustained-note development, phrase endings, contrast with other voices, and fatigue over repeated phrases. Include fast repeated notes, a longer held note, a rest/re-entry, an instrument change, and the densest intended passage. Keep an explicit verdict with reasons, including rejected versions.

Separate musical judgments from measurements. Register traces establish parameter trajectories; exact write logs establish ordering; PCM checks catch clipping, missing output, and unexpected tails. None of those automatically establishes beauty, style, or a convincing performance. Record who listened and what playback was used; do not invent a listening verdict from a waveform plot.

The [instrument card template](instrument-card-template.md) specifies what to retain. Once a patch passes its phrase and mix review, keep the native instrument/workfile as the editable source, a short demonstration, and reproducible export instructions. Record the player version and update rate: a sound is not portable merely because another editor has fields with the same names.

## Applying the repertoire to Für Elise

Preserve the complete source and the verified baseline as references. Compare a clear plucked or singing lead with a moving pulse alternative over restrained bass and accompaniment. Use the F-major episode and later repeated-bass section to test contrasting textures, then make the final return sound intentional. The three-voice reduction remains an arrangement decision, separate from sound design.

The acceptance target is a complete, recognisable arrangement whose phrasing and timbres are interesting beyond its opening. A technically correct render is the starting point. A showcase claim requires an actual listening-reviewed version and retained evidence of the choices that improved it.
