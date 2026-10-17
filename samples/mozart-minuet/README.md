# Mozart Minuet and Trio: accepted sample package

The [owning case](../../songs/mozart-minuet/README.md) holds the musical brief, source reduction, native palette, spatial allocation and prospective effort ledger. The complete PAL MOS8580 single-SID and dual-SID renditions, stereo benefit and ending are accepted. NTSC exports pass technical checks; they have no separate listening verdict. The [source edition](../../songs/mozart-minuet/source/README.md) is public domain; our case tools and configuration are MIT. Native player code retains the separate [SID-Wizard notice](../../THIRD_PARTY_NOTICES.md).

| Material | Owner |
| --- | --- |
| Original MIDI, notation and source fingerprints | [Preserved source](../../songs/mozart-minuet/source/README.md) |
| Complete source form and mono/stereo note allocation | [Arrangement](../../songs/mozart-minuet/arrangement.json), [preparer](../../scripts/studies/mozart-minuet/prepare.py) |
| Editable instrument programs | [Single SID](../../songs/mozart-minuet/mono.json), [dual SID](../../songs/mozart-minuet/stereo.json) |
| Builds, complete execution checks and listening comparisons | [Listening recipe](../../config/listening/mozart-minuet.json), [audition selection](../../config/listening/mozart-minuet.audition.json) |

Run from the repository root after the documented [native setup](../../docs/setup/local-setup.md):

```sh
python3 scripts/listening-package.py config/listening/mozart-minuet.json --output build/mozart-minuet-work
python3 scripts/publish-listening.py build/mozart-minuet-work/run.json --selection config/listening/mozart-minuet.audition.json --output build/mozart-minuet-listening
```

The generated listening index identifies the SID/PRG outputs and complete WAVs. Friendly audition files include `mozart-minuet-single-sid.wav`, `mozart-minuet-stereo.wav` and `single-then-stereo-trio.ab.wav`. Eight SID/PRG files totaling 68,822 bytes and two accepted complete PAL WAVs totaling 38,731,654 bytes are included, with [fingerprints](manifest.json). The WAVs were added at the user’s request on 2026-10-17; they are exact copies of the accepted renders. NTSC WAVs and comparison clips are generated locally. The publication directory must be fresh.

## Playable exports

| Target | Single SID | Dual SID |
| --- | --- | --- |
| PAL MOS8580, listening accepted | [SID](mozart-minuet-mono.sid) · [WAV](mozart-minuet-mono.wav) · [PRG](mozart-minuet-mono.prg) | [SID](mozart-minuet-stereo.sid) · [WAV](mozart-minuet-stereo.wav) · [PRG](mozart-minuet-stereo.prg) |
| NTSC MOS8580, technically verified | [SID](mozart-minuet-mono-ntsc.sid) · [PRG](mozart-minuet-mono-ntsc.prg) | [SID](mozart-minuet-stereo-ntsc.sid) · [PRG](mozart-minuet-stereo-ntsc.prg) |

Mono uses `$D400`; stereo uses `$D400/$D420`, chip A left and B right. Use a two-SID-compatible player for stereo. Melody and bass are duplicated centrally; the independent second-violin and viola roles occupy opposite sides. The extra chip restores one source part beyond the mono reduction. For the maintainer’s archived auditions, use fresh output directories when rerunning; the [case retention notes](../../songs/mozart-minuet/README.md#retention-and-follow-up) describe exact recovery.
