# Verifying a complete native SID-Wizard song

Use [native-song.py](../scripts/native-song.py) with an original native arrangement recipe to convert the retained three-voice score, export through the pinned SID-Maker Extra player, audit the complete driver schedule, render the full song, and cut an original-amplitude audition excerpt. This workflow complements [the baseline song workflow](song-workflow.md); its driver-specific oracle does not apply the baseline player's fixed-instrument or articulation rules to native instrument programs.

```sh
python3 scripts/native-song.py build songs/fuer-elise-sidwizard.json --output build/fuer-elise-native
```

The output directory must be fresh. Native editable source, conversion and export reports, PSID and standalone PRG, full WAV, the default first 20 seconds as `native-song.excerpt.wav`, and `verification.json` remain together. Set `--excerpt-start` and `--excerpt-seconds` to retain a fixed later passage. Excerpts use exact rounded source-frame bounds and unit gain; the full render is preserved. Use [the audio comparison tool](audio-comparisons.md) for separate, documented level matching.

Recipes select a retained three-voice arrangement, a contiguous section map that assigns an instrument to every source voice, and original native waveform/pulse/filter programs. The converter targets the 1x Extra player with one tick per row, chunks tracks at 248 rows or 249 uncompressed bytes including the delimiter per pattern, and must fit the native 100-pattern limit. The explicit short-note policy retains a full-pitch sounding frame by extending a one-frame grace into available silence or borrowing a frame from its following note; the conversion report records every timing change. Native `.swm` and `.swi` files remain editable in SID-Wizard, but these edits do not roundtrip into the recipe: keep such versions as separate native workfiles and export them independently.

## What the oracle measures

The conversion manifest maps every nonempty native note/off cell to its voice, play-call tick, pattern number, packed byte offset and instrument. It also lists every expected orderlist pattern entry and the terminal stop tick. The optional read-only instruction observer in [the PSID audit](psid-audit.md) inspects the pinned Extra driver's note-column reads, discrete sound-start state and orderlist reads. Label bytes must match the exporter build identity, native-source and PSID hashes must match the conversion/export evidence, and the Extra player must use its supported `$1000/$1003` callable layout.

The audit requires exact ordered cell consumption and discrete note starts on every voice, including repeated notes and the last note; every expected pattern transition; and the declared sequence volume command followed by `$FE` on all voices. The stopped 1x driver continues receiving calls and rereads its final plain gate-off cell and `$A0` volume-zero command; only that exact pattern, byte offset, code `$7E`, absent instrument selection and declared volume-zero ending is classified after the verified `$FE`. Any additional pitched start remains a failure. Gates and master volume must stay clear from the same declared stop call, as proved by the supplied three-voice recipe; a later volume-clear tick is rejected. For critical short notes listed by the converter, the declared body frame must have gate on, a pitched waveform, TEST/noise clear and the complete frequency word within one unit of the equal-tempered MIDI target at the declared PAL clock. This rejects a merely decoded grace, a TEST-only frame and a high-byte-only pitch approximation. The retained `.writes.json` records actual ordered SID stores with instruction-start cycles; `.frames.json` contains the 25 SID register values after each call; `.native-events.json` contains the driver observations. Instruction-start cycles are not SID bus-write timestamps.

The complete render must be mono PCM16 at 44100 Hz with the exact requested frame count, nonzero AC energy, no samples at the PCM rails, and a quiet final half-second. The renderer command, executable SHA-256, stdout, stderr and exit/timeout result are retained in `.render.json` before PCM guards run. Raw CPU evidence is retained before schedule guards run, so a rejected schedule remains diagnosable; `.schedule.json` and the final `verification.json` appear only after their respective guards pass. Both the audit subprocess and renderer have 120-second wall-clock deadlines; each CPU play call must separately fit one PAL frame's cycle budget. Audit duration follows the converted complete song plus a verification tail, rather than a short acceptance excerpt. Excerpt options must be finite and fit inside the planned full render; the workflow does not silently shorten the requested excerpt.

## Evidence limits

Decoded source notes and their scheduling do not by themselves prove exact audible onset pitch or ADSR reattack. SID-Wizard's first-frame and fast-row behaviour can differ from the baseline player's articulation, especially for adjacent short notes. Retain the conversion's explicit timing/articulation changes and the native instrument definitions alongside the evidence; see [the native Für Elise candidate](fuer-elise-native.md) for its concrete arrangement decisions and limitations.

The report's `listeningReview` is `null` and its evidence level is `rendered experiment`. It does not claim a musical preference, hardware fidelity, physical SID behaviour, or listening approval. [The independent native PRG check through headless VICE](native-vice-checks.md) is separate evidence; a RAM-only callable audit is not a complete C64 environment.

## Verification

```sh
python3 -m unittest discover -s tests -p 'native_song_test.py' -v
python3 -m unittest discover -s tests -p 'psid_audit_test.py' -v
```

The schedule guards reject missing, extra, wrong or mistimed cells; a fetched note that fails to start; wrong instruments; missing patterns; wrong stop ticks; loops; and gates/volume that persist after stop. Excerpt tests independently check exact sample selection and original preservation. CPU observer tests establish that read-only observations leave the original audit report and SID writes unchanged.
