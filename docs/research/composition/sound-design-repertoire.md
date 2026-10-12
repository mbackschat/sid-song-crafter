# A reusable SID sound-design repertoire

Research date: 2026-10-12. The aim is a library of expressive, editable instruments and arrangement techniques that make the next song easier and better. A list of hexadecimal presets is insufficient: each sound needs a musical use, a performance program, target assumptions, and evidence. Start with [the composer studies](../composers/README.md), [advanced techniques](../sid/advanced-techniques.md), and [the tool assessment](../tools/composition-tools.md).

## Evidence levels

| Label | Meaning |
| --- | --- |
| Documented reference | A cited composer account, published analysis, manual, or source implementation explains the technique |
| Proposed experiment | An original design brief derived from that research; no audible result is claimed |
| Rendered experiment | Editable source and reproducible audio exist, with declared model and player |
| Listening-reviewed instrument | The rendered result has been judged in a phrase and in a mix, with the verdict recorded |
| Hardware-checked instrument | The actual declared chip/machine setup was tested and recorded |

The current [Für Elise baseline](../../fuer-elise-validation.md) establishes note scheduling, complete playback, and rendered audio. Its fixed triangle instruments are not promoted to a showcase repertoire merely because those tests pass. The [original native bank](instruments/README.md) supplies rendered experiments for moving pulse with delayed vibrato, bright-attack pluck, kick-to-bass sharing and a falling kick, plus a three-voice mix. These have CPU and PCM evidence; the [listening findings](gestures/README.md) distinguish a cleaner preferred attack, audible pulse motion without a preference, and a bass transient with little perceived effect. The remaining briefs below are proposed.

Use the [musical gesture library](gestures/README.md) for groove, chord responses and phrase variation. The [sustained chord instrument](instruments/chord-01-sustained-arpeggio.md) supplies a rendered CHORD-01 example with complete pitch/waveform-cycle guards. Its paired arrangements were judged not close to the desired DRAX fragment; that verdict rejects those matches rather than settling every use of the chord mechanism. The [executed-program study](../tools/sid-program-analysis.md) now owns the DRAX bass explanation and controlled mechanism comparisons. A reusable repertoire includes how to improvise around a recognizable theme, not only how to synthesize its notes. Preserve the source separately and make intentional interpretation changes explicit.

## Reference material worth learning from

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

## How to evaluate a candidate

Use the same notes, tempo, register, and arrangement when isolating an effect in an A/B comparison. A creative arrangement comparison may deliberately change them: declare those differences and judge the resulting phrase as a whole. Retain original-amplitude renders and document any gain adjustment used for level matching. A louder file should not win by default. Soloing helps diagnose a sound, but the full mix decides whether it belongs in the song.

When isolating a coupled instrument, preserve its ring/sync modulator's oscillator state and the intended shared-filter configuration. Muting a companion's output is different from stopping its oscillator or removing its register writes; the latter can change the sound being studied.

Judge each candidate on attack consistency, pitch intelligibility, rhythmic clarity, timbral interest, useful note range, sustained-note development, phrase endings, contrast with other voices, and fatigue over repeated phrases. Include fast repeated notes, a longer held note, a rest/re-entry, an instrument change, and the densest intended passage. Keep an explicit verdict with reasons, including rejected versions.

Separate musical judgments from measurements. Register traces establish parameter trajectories; exact write logs establish ordering; PCM checks catch clipping, missing output, and unexpected tails. None of those automatically establishes beauty, style, or a convincing performance. Record who listened and what playback was used; do not invent a listening verdict from a waveform plot.

The [instrument card template](instrument-card-template.md) specifies what to retain. Once a patch passes its phrase and mix review, keep the native instrument/workfile as the editable source, a short demonstration, and reproducible export instructions. Record the player version and update rate: a sound is not portable merely because another editor has fields with the same names.

## Applying the repertoire to Für Elise

Preserve the complete source and the verified baseline as references. Compare a clear plucked or singing lead with a moving pulse alternative over restrained bass and accompaniment. Use the F-major episode and later repeated-bass section to test contrasting textures, then make the final return sound intentional. The three-voice reduction remains an arrangement decision, separate from sound design.

The acceptance target is a complete, recognisable arrangement whose phrasing and timbres are interesting beyond its opening. A technically correct render is the starting point. A showcase claim requires an actual listening-reviewed version and retained evidence of the choices that improved it.
