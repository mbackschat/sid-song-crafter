# SPACE-01 — deliberate left/right movement

**Status:** repertoire design option recorded from the user's request on 2026-10-15; no project demonstration or listening approval yet. The listener is generally not fond of repeated left/right movement, but permits it when it serves a clear musical purpose. This is not selected for the current [Rambo lead-centering revision](../../../../songs/studies/rambo-chord-expansion/README.md#center-the-lead-while-keeping-accompaniment-on-both-sides), whose lead should remain stable.

## Musical purpose

Use a brief spatial response, a phrase handoff or a movement into an arrival when the position itself helps articulate the music. Specify the affected role, start/end positions, musical boundary and duration. Keep stable anchors where they help the listener follow melody and bass. Continuous automatic oscillation between sides is not a default enhancement; test whether the movement distracts from the phrase or becomes tiring.

Placement remains a musical choice: additional parts may occupy the center if appropriate. Establish the role map before deciding how to realize it with the [two-chip hardware and mixer](../../sid/dual-sid.md#plan-the-sound-hardware-and-the-mix-together).

## SID realization and costs

| Method | Actual capability and constraint |
| --- | --- |
| Alternate phrase or note entries between chips | Produces spatial handoffs using two chip outputs. Preserve timing, appropriate release and local sync/ring dependencies. A new oscillator has its own phase and envelope history; an onset handoff is not a transparent continuous pan. |
| Duplicate a part across chips and vary its balance | Requires an oscillator on each side and any required modulators. SID has no independent per-voice volume/pan control; pulse width or envelope changes also alter articulation or tone. Do not claim general transparent native panning from these controls. |
| Animate an external chip-output mix | Can move a chip group smoothly, but moves every audible voice in that chip together. The PSID does not encode an arbitrary external pan trajectory; retain the mixer automation and reproduction route separately. |

Keep voice and filter ownership, phase history, CPU budget and the output matrix explicit. A second chip supplies another mono bus, not per-voice pan controls. Do not introduce phase inversion, delay or a synthetic widening treatment merely to manufacture motion without a musical brief.

## Verification and audition

For an implemented example, retain the position/time or note-entry map, source hashes, chip allocation, full execution evidence where synthesis changes, and the actual delivered channel gains. Verify complete releases, headroom and a mono fold-down. Compare the same phrase with fixed placement first and deliberate movement second, at one shared gain per stereo clip. Human review must establish whether the movement supports the phrase; measured width alone does not establish musical value.
