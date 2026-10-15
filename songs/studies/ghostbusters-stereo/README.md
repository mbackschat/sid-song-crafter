# Ghostbusters: centered hook and independent tonal support

This is an active two-SID interpretation of the accepted [245-second native title](../../../docs/research/composition/ghostbusters-preparation.md#complete-native-title-and-listening-package), preserving its complete score, patches, restart and explicit serialized speech adaptation. The initial held-support phrase is rejected for a persistent right-side sound; opening speech and complete ending/continuation are accepted separately. The [exact listening record](listening-review.json) owns those scopes. A bounded support-articulation revision remains active; preserve the original mono baseline and the initial stereo submission. The [initial arrangement](arrangement.json) contains selectors and sound parameters without embedded notes.

## Resource-informed design

The unresolved musical question is whether an independent, restrained tonal foundation adds useful body while the main instrument stays centered and the original rhythm section remains clear. The first comparison must settle that question in context before further expansion. This follows the [master constraint-to-arrangement method](../../../docs/research/sid/dual-sid.md#expand-the-musical-capacity-not-only-the-stereo-image), rather than treating every spare oscillator as a requirement to add a part.

The [executed source study](../../../docs/research/composition/ghostbusters-preparation.md#sound-programs) and [editable instrument card](../../../docs/research/composition/instruments/ghostbusters-decoded-programs.md) settle the relevant constraints. Source voice 0 carries the principal ostinato/melody, voice 1 carries the saw bass, and voice 2 starts with tonal support before selecting noise patch 3 at music call 512. Across the complete 14,389-call scope, voice 2 has 837 noise rows and only 18 later patch-2 tonal rows. Bass and percussion are independent source voices; there is no demonstrated bass/drum multiplex to “repair.” No source sync/ring dependency, continuing PWM or music filter program was found.

The observed resource change is tonal support yielding its oscillator to noise percussion. Our hypothesis develops that tonal capacity with one held source-bass root during the established riff. It does not recover a missing source part or claim what Lieblich would have written with another chip. [David Crane's firsthand production account](https://www.retrogamesmaster.co.uk/david-crane-interview/) identifies Lieblich's music and separate driver/title contributions; it provides no specific six-voice orchestration instruction. The repository's [composer accounts](../../../docs/research/composers/hubbard-galway.md#composer-accounts-for-expanding-limited-voices) support investigating concrete sharing before arranging, with their applicability kept separate from this source.

## Hardware and placement

The target is NTSC, two matching MOS6581s at `$D400/$D420`, one shared score engine, and one music update every 17,095 cycles. The native title remains machine controlled: CIA2 Timer B plays the decoded private speech stream every 102 cycles, then stops before CIA1 Timer A starts music. Native exports use RSID v3; the independently callable music component uses PSID v3. No PAL portability or physical hardware result is claimed.

| Musical role | Native allocation | Coupling/filter ownership | Raw output matrix |
| --- | --- | --- | --- |
| Complete principal instrument | A1 and B1, exact source register programs on both | No sync/ring; no filter routing; source shared-phase vibrato retained | Equal coefficient in left/right through A→L, B→R |
| Complete source bass | A2 | Original patch/articulation; A master volume | Left |
| Complete source tonal opening/percussion | A3 | Original role changes and articulation; A master volume | Left |
| Added held tonal foundation | B2 | Static uncoupled pulse; B master volume; no filter | Right |
| Spare oscillator | B3 silent | No invented role | Silent |
| Opening speech | Native volume writes on both chips | Decoded speech remains separate from oscillator instruments | Center through equal A/B writes |

Both chip buses retain all source music volume commands, including the descending-voice command order and order-cursor fade. The WAV uses the identity matrix `L=A`, `R=B`. Matching applies one scalar per complete file equally to its two channels; all excerpts retain those gains. A mono fold-down is `0.5A+0.5B`. Lead duplication consumes two oscillators, giving this candidate five occupied oscillators for four distinct musical parts. Identical register programs do not establish phase coherence or hardware identity; the phrase feedback does not establish a hook-centering verdict.

## Bounded held support

The [support module](../../../scripts/studies/ghostbusters/stereo.py) selects the executed bass patterns 44/45 only when source voice 2 uses noise patch 3. Their first pitched row must share one root. The added note is that source root one octave higher, below the main instrument, held across consecutive qualifying patterns. It stops at the first unsupported pattern, a source tonal return or global reset. It does not follow every bass leap or add an independent melodic contour.

The pulse uses the source bank's static, uncoupled pulse vocabulary, with explicitly authored held articulation: pulse width `$800`, control `$41`, AD `$24`, SR `$48`. These are candidate sound-design parameters, not recovered source bytes or a reusable accepted patch. Gate-off also clears SR to prevent a long release extending into the next unsupported harmony; articulation must be judged in the mix. No extra percussion, filter effect or replacement lead is added.

The whole held span is screened against every ongoing non-rest source lead state, using root-relative intervals `{0,2,3,4,5,7,9,10}` from the source's dominant/blues material. This is an explicit bounded harmonic admission rule, not an automated musical-quality verdict. Five complete source regions pass the 14,389-call screen, covering 8,192 calls; the private `support-ledger.json` retains exact source-derived notes and boundaries. The native support requires 45 play stores across those regions, with no periodic retrigger during a held body.

## Verification and reproduction

The [compiler](../../../scripts/studies/ghostbusters/compiler.py) applies guarded opt-in assembly additions to the unchanged mono template. A single shared score engine avoids copying the roughly 2.2 KiB music component: the accepted speech-bearing image already ended at `$C9FA`, leaving 1,542 bytes before SID I/O. The stereo image ends at `$CADE`, leaving 1,314 bytes. Unsupported clock, model, addresses, mix, source-root changes, non-noise companion patches and unsafe held intervals fail before export.

The [retained aggregate proof](../../../evidence/ghostbusters-stereo/native-proof.json) checks all 14,389 music calls, 14,390 named states and 123,921 ordered native stores: 71,934 on A and 51,987 on B. Actual NTSC VICE independently checks the same stores and call count, with zero SID reads and 45,410 non-nested speech NMIs. Maximum NMI cost is 85 cycles including entry, below the 102-cycle period; sample-entry jitter is −4 to +1 cycles. Music-entry intervals are 17,093–17,124 cycles, including the first handoff. Fresh isolated-source music and independently compiled music checks cover all 14,389 calls. The shorter [48-second diagnostic](../../../evidence/ghostbusters-stereo/diagnostic/native-proof.json) covers 2,600 calls before the complete run. Both banks are checked at physical addresses; no one-SID mirror alias discards B stores. Decoder values and command lengths remain pinned; changed setup time shifts no-write timeline padding. The [28 focused guards](../../../evidence/ghostbusters-stereo/focused-guards.txt) include accepted default mono SID, PRG and speech-stream byte hashes.

Both full renders contain 10,804,500 frames at 44.1 kHz and no PCM rail samples. The accepted mono is duplicated equally into both channels; its complete-file matching gain is 0.9379982389 (−0.55596 dB), while the native candidate remains at 1.0. The [signal receipt](../../../evidence/ghostbusters-stereo/audio.json) retains raw levels, output matrices, fold-down and comparison hashes. Source notes, encoded/decoded speech, binaries, native traces and audio remain under ignored `build/`; the public proof is an allowlisted aggregate projection bound to the actual private SID and full private-proof hashes. Do not publish the full native `verification.json`: its nested compiled checkpoints contain source notes.

The [held-support causal control](../../../scripts/studies/ghostbusters/prepare-support-control.py) changes only the immediate `$41` to `$40` in the labelled B2 control onset, checking the actual artifact hash, exact symbol, unique context and following accumulator/flag overwrite. Its [receipt](../../../evidence/ghostbusters-stereo/support-control.json) establishes unchanged opcode layout and CPU cycles; it is not a separate complete diagnostic CPU proof. Identical rendering and candidate gain leave the entire left PCM and both channels before 15 seconds exactly unchanged. The 16–32-second right difference has AC RMS 1,168.77 and peak 1,172 PCM units. This establishes an actual support contribution, not an isolated stem, audible usefulness or musical acceptance.

The initial nine-stage run took 219.412 seconds. Review then corrected an actual-versus-normalized header hash, an undeclared guard input and public-proof privacy, and added the gate-off control. The [corrected run](../../../evidence/ghostbusters-stereo/run-verified.json) took 207.488 seconds: native proofs, guards, preparation and the controlled render executed freshly, while source/mono pins and both unchanged main renders were reused. The [unchanged repeat](../../../evidence/ghostbusters-stereo/run-reused.json) took 0.768 seconds with all 11 stages reused. The [initial pre-review receipt](../../../evidence/ghostbusters-stereo/run-initial-pre-review.json) is historical provenance, not the current proof. These timings exclude implementation and listening.

After restoring the private source, pinned tools and [accepted mono baseline](../../../docs/research/composition/ghostbusters-preparation.md#complete-native-title-and-listening-package), reproduce the initial candidate in fresh local folders:

```sh
python3 scripts/listening-package.py config/listening/ghostbusters-stereo.json --output build/ghostbusters-stereo-native-workflow-new
python3 scripts/publish-listening.py build/ghostbusters-stereo-native-workflow-new/run.json --selection songs/studies/ghostbusters-stereo/audition.json --output build/ghostbusters-stereo-listening-new
python3 scripts/evidence.py verify --group ghostbusters-stereo
```

The [evidence index](../../../evidence/ghostbusters-stereo/README.md) retains exact initial configuration snapshots, stage dependencies and submission hashes. Historical tool fingerprints identify the measured versions; rerunning later working code is not a new execution of those exact historical versions.

## Initial listening verdict and active correction

Each A/B plays accepted mono first, then the initial native stereo candidate, with a half-second separator. All files below remain frozen under `build/ghostbusters-stereo-listening/`:

| Scope | Initial comparison | Human verdict |
| --- | --- | --- |
| Opening, 0–12 seconds | [opening-mono-then-stereo.ab.wav](../../../build/ghostbusters-stereo-listening/opening-mono-then-stereo.ab.wav) | Speech recognizable and centered |
| Phrase, 16–32 seconds | [phrase-mono-then-stereo.ab.wav](../../../build/ghostbusters-stereo-listening/phrase-mono-then-stereo.ab.wav) | Rejected persistent right-side sound |
| Continuation, 225–245 seconds | [ending-mono-then-stereo.ab.wav](../../../build/ghostbusters-stereo-listening/ending-mono-then-stereo.ab.wav) | Complete ending/continuation intact |

Full matched files are [faithful-mono-matched-full.wav](../../../build/ghostbusters-stereo-listening/faithful-mono-matched-full.wav) and [native-stereo-matched-full.wav](../../../build/ghostbusters-stereo-listening/native-stereo-matched-full.wav), 245 seconds each. The ending window retains source restart/continuation; its capture boundary is not a composed stop or fade.

The listener reports: “With the stereo one: there is a persistent sound on the right side, seems like a bug”. The separate reply is “Yes to : speech remain recognizable and centered, and does the complete ending/continuation remain intact”. Preserve these scopes separately; successful execution and the strong causal difference do not approve the held part.

The mechanism is the eligibility scheduler merging consecutive qualifying bass patterns into one uninterrupted gate. The first hold lasts 2,048 music calls (about 34.23 seconds), and the longest lasts 2,560 calls (about 42.79 seconds). The initial design explicitly allowed this, so its guards passed while the musical role failed. The next bounded correction retains the root and patch but articulates the source root prefix with a release/rest interval. Its actual attack, body, release and late gap must be checked against the same-cycle gate-off control before a revised phrase audition. Preserve the accepted speech and continuation verdicts for their unchanged scopes; the case remains active until the corrected musical role receives feedback.

The first-audition and post-feedback model-assistance reviews select no model call: existing calibration does not qualify a model to approve spatial placement, persistent-support benefit or balance. Human rejection remains authoritative. Reassess at the corrected phrase and before closure.

Publication uses the [always-included tier](../../../CLAUDE.md#public-repository-boundary): tools, note-free recipe, attribution, source hashes and reproducible safe summaries. Underlying composition, C64 arrangement and speech rights remain [unresolved](../../../docs/research/game-music-permissions.md); source-derived score ledgers, exports and audio stay private. No original SID, decoded speech stream or lossless source-audio trace is added to Git.
