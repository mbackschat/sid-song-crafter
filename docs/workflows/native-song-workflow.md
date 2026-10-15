# Verifying a complete native SID-Wizard song

Use [native-song.py](../../scripts/native-song.py) with an original native arrangement recipe to convert a retained three- or six-voice score, export through the pinned SID-Maker Extra player, audit the complete driver schedule, render the full song, and cut an original-amplitude audition excerpt. This workflow complements [the baseline song workflow](song-workflow.md); its driver-specific oracle does not apply the baseline player's fixed-instrument or articulation rules to native instrument programs.

```sh
python3 scripts/native-song.py build songs/fuer-elise-sidwizard.json --output build/fuer-elise-native
```

The output directory must be fresh. Native editable source, conversion and export reports, PSID and standalone PRG, full WAV, the default first 20 seconds as `native-song.excerpt.wav`, and `verification.json` remain together. Set `--excerpt-start` and `--excerpt-seconds` to retain a fixed later passage. Excerpts use exact rounded source-frame bounds and unit gain; the full render is preserved. Use [the audio comparison tool](audio-comparisons.md) for separate, documented level matching.

Recipes select a retained arrangement, a contiguous section map that assigns an instrument to every source voice, and original native waveform/pulse/filter programs. `sidCount` defaults to 1 (three voices); 2 requires six distinct ordered voices at `$D400/$D420`. Optional `sidModel` selects `"MOS6581"` or `"MOS8580"`, defaulting to MOS8580 for existing recipes and applying to both chips when `sidCount` is 2. Conversion and export reports retain the model; the PSID declares it and the renderer honors it. Native SWM/SWS files do not store this choice, so independent export requires `--sid-model MOS6581` for a 6581 target. A standalone PRG cannot declare or enforce physical SID hardware; its native starter retains an unused PSID header whose flags reflect the export choice. Voices 0–2 belong to the first chip, 3–5 to the second; each chip has its own shared filter. The converter targets the 1x Extra player with one tick per row and chunks tracks at 248 rows or 249 uncompressed bytes including the delimiter per pattern. One SID permits 100 patterns/36 instruments; two permit 105/29. Long six-voice scores can exceed this tick-grid capacity even when their packed file is small; such input is rejected, not shortened. See [the native format and exporter contract](../research/tools/sid-wizard-trial.md).

Optional `patternBeats` selects a positive finite beat interval for pattern boundaries, for example `"patternBeats": 8`. Boundaries start at beat zero and independently round each absolute beat multiple to the target clock's tick grid, avoiding accumulated rounding drift. The grid continues through the release tail, and the final interval retains every remaining row. The existing row and byte limits still split chunks within each interval. This can expose repeated phrases for pattern reuse without changing any note, gate, tick or release-tail cell; it does not raise the pattern or orderlist limits. The interval must span at least one target tick. Omit the option to retain the existing greedy packing and identical native bytes. The conversion manifest records `patternBeats`, using `null` for the default.

The explicit short-note policy retains a full-pitch sounding frame by extending a one-frame grace into available silence or borrowing a frame from its following note; the conversion report records every timing change. Native `.swm`/`.sws` songs and `.swi` instruments remain editable in SID-Wizard, but these edits do not roundtrip into the recipe: keep such versions as separate native workfiles and export them independently.

## Frozen release source and publication

Default to the editable SWM module (SWS for two SID chips) plus an export manifest as the frozen native release source. Preserve the module hash, exporter/player/toolchain identities, exact export command, clock, SID model, title/author/release metadata and expected SID/PRG hashes. Verify a fresh export against the accepted binaries before claiming exact-byte reproducibility. Keep the upstream score and authoring recipes separately so later musical edits remain reproducible. This contract applies to the SID-Wizard backend; other backends retain their own editable sources. See [Pink Panther's independently verified re-export](../../songs/pink-panther/README.md#source-of-truth-and-exact-byte-export).

Publication is a separate rights decision. Publish a complete native module only when the composition and incorporated arrangement/source permit that distribution. Otherwise retain the score, SWM/SWS, SID/PRG and audio locally under ignored output, and publish independently shareable tools, original instrument programs, recipes without embedded score data, provenance and checksums. Contributors supply an appropriately obtained source themselves; a download link or a deterministic build does not grant publication rights. See [the repository boundary](../../CLAUDE.md#public-repository-boundary).

## Regional export targets

Use recipe `"clock": "pal"` or `"clock": "ntsc"`, or override it with `native-song.py build … --clock ntsc`. Omitted targets preserve PAL. Both one- and two-SID native exports use the same target contract. This is explicit regional export, not automatic cross-region playback: use each PRG on its named machine timing. Independent native-module export also needs `export-sidwizard.py … --clock ntsc`; the editable SWM/SWS does not carry that choice.

Absolute source beat positions are rounded onto the selected machine's VBI grid. PAL uses 19,656 cycles at 17734475/18 Hz; 263-line NTSC uses 17,095 cycles at 14318181.82/14 Hz. Musical tempo is retained within grid quantization, and legacy score `tailTicks` retain their PAL wall-time meaning when converted to NTSC. Conversion and export metadata must agree; the renderer receives the target explicitly and the CPU audit uses its frame budget. Unknown targets and clock/header mismatches fail.

Effect tables advance once per target video frame, so their real-time speed differs between PAL and NTSC. SID ADSR codes remain unchanged; envelope times also vary with the chip clock. This policy preserves native program semantics, not identical timbre across regions. Native short-note adjustment remains explicit in the conversion receipt. PAL tuning and payload bytes remain unchanged; NTSC uses an equal-tempered frequency table rather than the upstream approximate NTSC table. Do not relabel existing PAL exports or reuse PAL tick counts as NTSC timing.

The [regional verification recipe](../../config/listening/native-clock-verification.json) checks complete mono and dual native deliveries on both clocks. The [retained outcome](../../evidence/native-clock-export/cross-clock-check.json) verifies the complete 895-note Bach schedule, twelve static dual-fixture pitch bodies per region and source-time/tail quantization; standalone VICE checkpoints extend beyond each final stop. The accepted PAL Toccata WAV is unchanged. [Renderer evidence](../../evidence/native-clock-export/renderer.json) separately measures stereo pitch and cadence on both SID models. This technical evidence does not award a new musical verdict. Existing accepted PAL listening remains the musical baseline.

## Reusable two-chip test

The [original six-voice fixture](../../tests/fixtures/sidwizard-2sid/recipe.json) exercises distinct pitches, independent filter programs, complete stops and stereo rendering without depending on a particular song. It is a functional test, not an approved musical palette.

```sh
python3 scripts/setup-sidwizard.py --sid-count 2
python3 scripts/native-song.py build tests/fixtures/sidwizard-2sid/recipe.json --output build/dual-native-validation --excerpt-seconds 2
python3 scripts/verify-native-vice.py build/dual-native-validation/export/recipe.prg build/dual-native-validation/native-song.writes.json --export-report build/dual-native-validation/export.json --calls 1 25 100 226 277 --output build/dual-native-validation/vice
```

Both chip counts use the same workflow. Their separate exporter receipts prevent one setup from replacing the other's player labels. Conversion, export and audited PSID layouts must agree before schedule verification. The fixture passes the complete pipeline and independent headless VICE register/cadence checks; [the VICE guide](../validation/native-vice-checks.md) explains unattended address selection and its limits.

## What the oracle measures

The conversion manifest maps every nonempty native note/off cell to its voice, play-call tick, pattern number, packed byte offset and instrument. It also lists every expected orderlist pattern entry and the terminal stop tick. The optional read-only instruction observer in [the PSID audit](../validation/psid-audit.md) inspects the pinned Extra driver's note-column reads, discrete sound-start state and orderlist reads. Label bytes must match the exporter build identity, native-source and PSID hashes must match the conversion/export evidence, and the Extra player must use its supported `$1000/$1003` callable layout.

The audit requires exact ordered cell consumption and discrete note starts on every voice, including repeated notes and the last note; every expected pattern transition; and the declared sequence volume command followed by `$FE` on all voices. The stopped 1x driver continues receiving calls and rereads its final plain gate-off cell and `$A0` volume-zero command; only that exact pattern, byte offset, code `$7E`, absent instrument selection and declared volume-zero ending is classified after the verified `$FE`. Any additional pitched start remains a failure. All gates and each chip’s master volume must stay clear from the same declared stop call; a later volume-clear tick is rejected. For critical short notes listed by the converter, the declared body frame must have gate on, a pitched waveform, TEST/noise clear and the complete frequency word within one unit of the equal-tempered MIDI target at the declared target clock. This rejects a merely decoded grace, a TEST-only frame and a high-byte-only pitch approximation. The retained `.writes.json` records actual ordered SID stores with instruction-start cycles; `.frames.json` contains 25 writable sound-register values per chip after each call, concatenated in declared chip order (50 for two SIDs, without the physical address gap); `.native-events.json` contains the driver observations. Instruction-start cycles are not SID bus-write timestamps.

The complete render must be PCM16 at 44100 Hz with the exact requested frame count: mono for one SID, stereo for two. Each chip channel must have nonzero AC energy and a quiet final half-second; no sample may reach the PCM rails. Stereo maps SID1 left and SID2 right without crossfeed, as specified by [the renderer contract](audio-workflow.md). The renderer command, executable SHA-256, stdout, stderr and exit/timeout result are retained in `.render.json` before PCM guards run. Raw CPU evidence is retained before schedule guards run, so a rejected schedule remains diagnosable; `.schedule.json` and the final `verification.json` appear only after their respective guards pass. Both the audit subprocess and renderer have 120-second wall-clock deadlines; each CPU play call must separately fit one target frame's cycle budget. Audit duration follows the converted complete song plus a verification tail, rather than a short acceptance excerpt. Excerpt options must be finite and fit inside the planned full render; the workflow does not silently shorten the requested excerpt.

## Check a controlled register change

For same-score sound experiments, [native_frame_comparison.py](../../scripts/native_frame_comparison.py) verifies that a nonempty pair of complete post-call captures differs only at explicitly allowed offsets. This automates the repeated intervention check; it does not establish musical improvement or ordered bus-write equality.

```sh
python3 scripts/native_frame_comparison.py build/reference/native-song.frames.json build/candidate/native-song.frames.json --allow-offset 2 --allow-offset 3 --output build/intervention.json
```

Offsets 2 and 3 select the first voice's pulse width. Native captures concatenate 25 sound-control bytes per SID, so second-chip offsets begin at 25, not the physical address gap. The checker rejects empty/malformed captures, unequal lengths, any unexpected register change, and an entirely unchanged candidate. It records input hashes and change counts. Use fresh output paths and declare both captures plus the checker as recipe inputs. Schedule, pitch-program and PCM checks remain separate.

## Evidence limits

Decoded source notes and their scheduling do not by themselves prove exact audible onset pitch or ADSR reattack. SID-Wizard's first-frame and fast-row behaviour can differ from the baseline player's articulation, especially for adjacent short notes. Retain the conversion's explicit timing/articulation changes and the native instrument definitions alongside the evidence; see [the native Für Elise candidate](../songs/fuer-elise-native.md) for its concrete arrangement decisions and limitations.

The report's `listeningReview` is `null` and its evidence level is `rendered experiment`. It does not claim a musical preference, hardware fidelity, physical SID behaviour, or listening approval. [The independent native PRG check through headless VICE](../validation/native-vice-checks.md) is separate evidence; a RAM-only callable audit is not a complete C64 environment.

## Verification

```sh
python3 -m unittest discover -s tests -p 'native_song_test.py' -v
python3 -m unittest discover -s tests -p 'psid_audit_test.py' -v
```

The schedule guards reject missing, extra, wrong or mistimed cells; a fetched note that fails to start; wrong instruments; missing patterns; wrong stop ticks; loops; and gates/volume that persist after stop. Excerpt tests independently check exact sample selection and original preservation. CPU observer tests establish that read-only observations leave the original audit report and SID writes unchanged.

For short or repeated accompaniment, native body/gate checks establish execution only. Include the release and next onset in the in-context audition; a clean silent gap can still sound abruptly cut off. Follow the [short-note ending decision table](../research/composition/sound-design-repertoire.md#shape-short-note-endings-in-context) to isolate gate duration, release and retrigger changes and retain the scoped listening verdict.
