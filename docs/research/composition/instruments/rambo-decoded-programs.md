# Rambo tonal programs on familiar material

Use the [Rambo loader study](../rambo-preparation.md) for the source, execution evidence and complete reconstruction. This card owns the different-material transfer: the same 53 notes of the preserved [Für Elise arrangement](../../../../songs/fuer-elise.json), beats `[0,12)`, rendered with plain source triangles and with selected Rambo tonal programs. Both are generated performances. The listener accepted musical use, balance, phrasing and ending on 2026-10-13.

## Musical purpose and selected patches

| Role / physical voice | Selected source note entry, zero-based physical voice and call | Reused behavior |
| --- | --- | --- |
| Melody / 1 | Voice 0, call 1763 | Pulse with two additive PWM phases, delayed balanced pitch motion and the source envelope |
| Bass / 2 | Voice 1, call 2354 | Fast pulse attack and two-stage pulse motion; frequency replacement disabled by the source patch |
| Harmony / 3 | Voice 0, call 5427, reassigned to voice 3 | Short, bright tonal pulse without frequency or pulse motion; supports the preserved accompaniment notes |

These are selected native patches, not a claim that every Rambo sound fits every melody. The introductory sweeps, sync patch and chord pitch replacements are excluded from this same-note transfer. A delayed program may never begin on a short note; that retains the program's native articulation rather than accelerating it to force an effect.

Classify a pitch program by its flags as well as its phase shape before changing vibrato. In [the executed frequency implementation](../../../../scripts/rambo_programs.py), flag bit `$02` applies the fourth signed step during the delay; shortening that delay changes the entrance bend, even when the following three phases form a balanced vibrato cycle. The published loader's `UP01` and `BEND01` are such programs. A palette edit that promises to retain these gestures must preserve their delay/step data explicitly. An unchanged note/timing ledger cannot prove unchanged pitch effects. This constraint was independently checked during the 2026-10-15 interpretation preparation; it is a programming finding, not a listening verdict.

Likewise, unchanged note timing does not preserve audible articulation. The [complete palette interpretation](../../../../songs/studies/rambo-interpretation/README.md) initially silenced the closing passage early by substituting ordinary envelopes for the source's long-release patches. Preserve the source envelope, gate countdown and lifetime as a coherent ending gesture when those settings sustain the closing phrase. Check actual final-note state and rendered sound before the lifetime clear, not merely silence at the file boundary. The pinned case now guards those properties and its 205–211-second closing body; this is verified ending preservation, not acceptance of the new palette.

## Editable example and reproduction

[prepare-rambo-elise.py](../../../../scripts/studies/rambo/prepare-rambo-elise.py) observes the selected note-entry data in the independent numeric loader, then creates the [transfer description](../../../../songs/rambo-elise-transfer.json) and [plain reference](../../../../songs/rambo-elise-reference.json). It requires no original SID. The selected patch bytes remain editable `initialData`; the explicit symbolic graph supplies every note, gap, release countdown and terminal return. The compiled runtime computes sound from those parameters, using the [sound program](../../../../songs/players/rambo-sound.asm), rather than replaying a register schedule.

```sh
python3 scripts/studies/rambo/prepare-rambo-elise.py --check
python3 scripts/listening-package.py config/listening/rambo-elise-transfer.json --output build/rambo-elise-transfer
```

The [recipe](../../../../config/listening/rambo-elise-transfer.json) checks preparation, independently compiles and CPU-verifies both descriptions, checks all declared calls in VICE, renders both initialized performances and creates the plain-first comparison. Read its generated `listening.md` for the exact files and its `run.json` for execution or cache reuse. Source interpretation, execution, signal health and musical judgment remain distinct.

## Timing, tuning and ending limits

Both descriptions preserve all 35 melody, 6 bass and 12 harmony notes, source gaps and note order. Each absolute source beat boundary rounds to the nearest PAL call, with a measured maximum error of 9.814 ms for this phrase. Both use the exact same source frequency words; their closest pitch matches deviate from equal temperament by at most 26.192 cents. This is native table tuning, not retuning to concert pitch.

Each note's release countdown is set to its quantized duration. SOUND decrements the countdown on the onset call, so the gate closes one call (19.950 ms) before the next duration boundary. Native lifetime and modulation continue through rests and after the final score return. The same-voice next note can replace a previous release tail. The source melody lifetime remains 255 calls, while the bass and harmony retain their shorter lifetimes; these are deliberate articulation constraints of the reused player.

The graph ends at call 501; the audit covers 822 calls. The final per-voice stores occur at calls 756, 520 and 503, leaving 65 no-store calls after the final clear. No extra ending notes or volume fade are added. Quiet registers and rendered tail measurements do not decide whether the musical ending sounds natural.

The plain reference retains the same score, tuning, gate timing and lifetimes, replaces the three patches with the source triangle/envelope settings, and disables modulation. Its provenance names the source patches only for their retained lifetimes; it is not presented as a recording of Beethoven or the original Rambo.

## Reuse outcome

The listener's verdict on `plain-then-rambo.ab.wav` was: “Yes: Rambo version work musically—especially the balance, phrasing and ending”. The [retained verdict](../../../../evidence/rambo-elise-transfer/listening-review.json) pins the submitted audio. This accepts the selected patches on the matched familiar phrase, not every Rambo patch or the separate loader reconstruction. Both full renders and the plain-first comparison passed complete CPU/VICE execution, duration/clipping checks and the final one-second per-channel AC RMS limit of one PCM16 unit before review; see [candidate CPU](../../../../evidence/rambo-elise-transfer/candidate/build.json), [candidate VICE](../../../../evidence/rambo-elise-transfer/candidate/vice/study.json), [plain-reference VICE](../../../../evidence/rambo-elise-transfer/reference/vice/study.json) and [audio measurements](../../../../evidence/rambo-elise-transfer/audio.json).

Reused unchanged: the numeric score scheduler, note setup, lifetime, PWM and frequency components, and three observed tonal patch bodies. New work: deterministic familiar-phrase preparation and the independent compiler shared with the loader reconstruction. Adaptations: per-note release counters and the short pulse's reassignment to harmony. Listening revisions: zero; the first submitted phrase was accepted. Active effort and time to acceptance were not reliably timed; no productivity improvement is inferred from this result alone.
