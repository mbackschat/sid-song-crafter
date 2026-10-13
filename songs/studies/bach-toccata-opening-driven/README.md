# Bach Toccata: faster hybrid opening

The listener accepted the [first hybrid sound](../bach-toccata-opening/README.md) but found the 24-second pacing too slow, almost boring, with unwanted pauses. This revision uses the same source pitches, voice allocation and native instruments, with a 12-second authored timing map. It is still only source quarter positions 0–10, not the complete Toccata. See the [owning study and model review](../../../docs/research/composition/bach-toccata.md#faster-opening-revision).

- [Score](score.json): three initial A holds shorten to 0.8 seconds each; main between-gesture gaps shorten to 0.3, 0.3 and 0.4 seconds. The three descending runs retain their previous durations of 1.0, 0.7 and 1.0 seconds.
- [Hybrid](hybrid.json): unchanged PWM lead, pedal sound and selective diminished-tone cycling. The pedal enters at 7.6 seconds, the diminished hold occupies 8.2–10.2 seconds, and the G–E–F-sharp resolution ends at 12 seconds. SID modulation runs at its original PAL rate; it is not sped up with the score.
- [Preparation](preparation.json): exact timing anchors, source mapping and linked complete-source hashes. Complete source material remains in the [original bundle](../bach-toccata-opening/README.md), without a duplicate full score.
- [Restrained recipe](restrained.json): the generator's matching steady-palette option, retained as editable data; this pacing audition renders the hybrid only.

The native player still uses one MOS8580, PAL, A=440 Hz, TEST silence on frame one, and the same 125-tick release tail. A shorter hold permits less PWM development; unchanged patch bytes do not imply an identical envelope or oscillator trajectory under the changed timing. This is an expressive pacing revision, not a Gyruss transcription or a claim of audio fidelity to the organ reference.

Regenerate into a fresh sibling directory (the output path determines relative source links):

```sh
PYTHONPATH=.tools/arrangement-deps python3 scripts/studies/bach/prepare-opening.py --source-dir songs/studies/bach-toccata-opening/source --source-bundle songs/studies/bach-toccata-opening --pacing driven --output build/bach-driven-inputs
python3 scripts/listening-package.py config/listening/bach-toccata-opening-driven.json --output build/bach-toccata-opening-driven-v1
python3 scripts/publish-listening.py build/bach-toccata-opening-driven-v1/run.json --selection config/listening/bach-toccata-opening-driven-audition.json --output build/bach-toccata-opening-driven-listening
```

The tracked driven bundle was prepared at its checked-in path; a temporary output has different relative source paths. To compare generated data, resolve those references before comparing hashes. The original pacing remains the generator default; its frozen preparation receipt retains the earlier script fingerprint, while its musical data remain reproducible.

Listen to [previous then driven](../../../build/bach-toccata-opening-driven-listening/previous-then-driven.ab.wav), [driven alone](../../../build/bach-toccata-opening-driven-listening/driven-hybrid.wav), or [previous alone](../../../build/bach-toccata-opening-driven-listening/previous-hybrid.wav). The A/B preserves both full renders at unity gain with a half-second separator; it does not pad the shorter version or stretch either performance. The [unchanged James Kibbie organ recording](../../../build/bach-source-intake/kibbie-bwv565.mp3), from the beginning, remains the separately timed interpretive reference. Revised musical acceptance is pending.
