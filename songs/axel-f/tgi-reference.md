# Axel F: TGI and Hülsbeck reference intake

On 2026-10-15 the listener selected the TGI version as a “nice interpretation with a great lead. The only bad thing is the drums that are too load (the ones that start from the beginning on)”, then asked whether that drum description could be comprehended and reproduced. The bounded question is which opening signal survives oscillator muting and how prominent it remains when the lead enters. This informs the [current score interpretation](README.md); neither SID replaces its separately sourced score. The listener subsequently requested the Hülsbeck original, selected it for the master study, and judged it “Hülsbeck's version is really great”. This is a positive verdict on that reference interpretation, not acceptance of our generated version.

## Active master study

Use Hülsbeck as the principal sound-design reference for this Axel F interpretation. The bounded question is how its lead combines attack, audible body, release and modulation, and which of those mechanisms improves our preferred longer-release palette on the preserved score. The [executed lead study and native pulse trial](huelsbeck-study.md) trace actual CIA-timed execution and test one mechanism in a same-score comparison. Keep TGI’s added-digi balance finding separate. The existing Shades and Giana studies remain the prior Hülsbeck evidence; this song adds contextual evidence rather than redefining a composer-wide style.

## Sources and attribution

| Reference | Source and identity |
| --- | --- |
| TGI remix | Supplied `/Volumes/Buffer/retrogames/c64/C64Music/DEMOS/A-F/Axel_F_TGI.sid`; private copy `.local/research/axel-f/tgi.sid`; [HVSC source URL](https://www.hvsc.de/download/C64Music/DEMOS/A-F/Axel_F_TGI.sid). Header: David Pridie (Martial Artist), 1988 The Guardians International. RSID v2, subtune 1 of 1, PAL MOS6581 at `$D400`, machine-controlled timing, init `$C000`. SHA-256 `0c4ce734df21ceeb289ea6b7f313f606d6f518c62c49b6ab166d566f6dd7dbb9`, 19,313 bytes. |
| Hülsbeck original | `/Volumes/Buffer/retrogames/c64/C64Music/MUSICIANS/H/Huelsbeck_Chris/Axel_F.sid`; private copy `.local/research/axel-f/huelsbeck-original.sid`; [HVSC source URL](https://www.hvsc.de/download/C64Music/MUSICIANS/H/Huelsbeck_Chris/Axel_F.sid). Header: Chris Hülsbeck, 1986 64’er/Markt & Technik. PSID v2, subtune 1 of 1, PAL MOS6581 at `$D400`, CIA1 Timer A, init `$C000`, play `$C020`. SHA-256 `87e0a1e8ad618a497e54fc5d4228dee7be53ef6365a30900debcdafbcd21251b`, 11,346 bytes. |

The exact local STIL entry for TGI identifies it as a remix of `MUSICIANS/H/Huelsbeck_Chris/Axel_F.sid` with added digis; both entries credit Harold Faltermeyer for the underlying composition. The pinned STIL database SHA-256 is `b1ef3584a5b3501e2bbd2ef056d6539a1bbee7933a7828537c3946c1b16cde43`; the extracted TGI entry hash is `7ce963690a20455091c86481ef5faa8e2e12204fdf6c21ef1aae5454729cb143`, and the Hülsbeck entry hash is `c8b47c15e10cdec6b09a2fb5e5811907cc9fd38a7ce54dc7a8d33cbca92f3bf7`. Private extraction receipts are under `build/axel-f-tgi-stil/` and `build/axel-f-huelsbeck-stil/`. This establishes the documented relationship, without proving that added drums are the only musical or code change.

## What the opening controls establish

The [diagnostic recipe](../../config/listening/axel-f-tgi-diagnostics.json) initializes the unchanged TGI SID four times: intact, all three oscillators muted, voice 2 enabled, and voice 3 enabled. Muting masks oscillator waveform/GATE writes in the [existing renderer](../../docs/workflows/audio-workflow.md); it preserves the shared `$D418` volume path. Accordingly the latter three files retain volume-path samples and are diagnostics, not clean stems or revised arrangements.

The [aggregate verification](tgi-verification.json) pins all four 16-second WAV hashes and guards two exact PCM equalities over 0–7.5 seconds: intact equals voice 3 plus volume path, and voice 2 plus volume path equals volume path alone. Thus voice 2 adds no opening signal in that interval. The renderer snapshots place its lead entrance near 7.834 seconds. Voice 3 uses both triangle and noise controls in the captured opening; percussion is therefore not confined to the added volume-path samples.

| Rendered control | AC RMS, 0–7.5 s | AC RMS, 8–16 s |
| --- | ---: | ---: |
| Intact source | 1361.97 | 1985.90 |
| All oscillators muted: volume-path residual | 1197.83 | 1195.40 |
| Voice 2 plus volume path | 1197.83 | 1867.92 |
| Voice 3 plus volume path | 1361.97 | 1366.21 |

Values are PCM16 units at common unity gain. The residual reaches 87.9% of the intact opening’s AC RMS and remains substantial after the lead enters; that ratio is not an additive energy share. A bounded 10 ms AC-RMS threshold probe finds a starting burst around 0.01 seconds and subsequent strong bursts near 0.15, 0.39, 0.63, 0.87 seconds, continuing about every 0.24 seconds. `$D418` snapshots cover all 16 volume nibble values. These results reproduce a strong, recurring starting rhythm component through the volume path and corroborate the listener’s attribution technically. They do not decide whether the listener meant those samples, the voice-3 percussion, or their combination. “Too loud” and “great lead” remain the listener’s musical judgments; no simulated hearing or model preference is substituted for them.

## Reproduce and listen locally

Both sources use the [full-machine intake route](../../docs/workflows/reference-intake.md): TGI is RSID, and Hülsbeck declares CIA timing. The callable VBI audit is unsupported for both. Renders use explicit PAL, declared MOS6581, libsidplayfp 3.1.1/SIDLite, power-on delay zero, 44.1 kHz mono PCM16 and unity gain. All requested renders passed duration, nonzero-signal and no-clipping checks. These are modeled audio and renderer-iteration snapshots, without ordered CPU-write or original-hardware equivalence claims. Our current score interpretation targets MOS8580, so these references do not establish timbre fidelity to that implementation.

```sh
python3 scripts/setup-project.py --only references --include axel-f-tgi --include axel-f-huelsbeck
python3 scripts/reference-intake.py run config/reference-intake/axel-f-tgi.json --output build/axel-f-tgi-intake
python3 scripts/reference-intake.py run config/reference-intake/axel-f-huelsbeck.json --output build/axel-f-huelsbeck-intake
python3 scripts/listening-package.py config/listening/axel-f-tgi-diagnostics.json --output build/axel-f-tgi-diagnostics
python3 scripts/publish-listening.py build/axel-f-huelsbeck-intake/run.json --selection config/listening/axel-f-huelsbeck.audition.json --output build/axel-f-huelsbeck-listening
python3 scripts/publish-listening.py build/axel-f-tgi-diagnostics/run.json --selection config/listening/axel-f-tgi-diagnostics.comparisons.json --output build/axel-f-tgi-comparisons-8s
```

Publisher destinations must be fresh. The original Hülsbeck SID is playable in a SID player; `build/axel-f-huelsbeck-listening/huelsbeck-original-32s.wav` is its bounded 32-second preview, not a complete-song export. Preview SHA-256: `64f2edaf9ef84289cd9cbead27eac6458f3ace446ad911269990d086a90b4efd`. The TGI intake retains its own separate 32-second reference.

The two comparison files play source first, half-second silence, then the same interval with all oscillators muted, at unchanged gain: `build/axel-f-tgi-comparisons-8s/opening-full-then-volume-only.ab.wav` covers 0–8 seconds twice (SHA-256 `f46d24cc8f9c0b6b2777998a8ed6cbd37ddb88bacc054b0fdb6d6277e9871b79`); `lead-full-then-volume-only.ab.wav` covers 8–16 seconds twice (SHA-256 `d41f04ef0d2f2f139bbafbc497c4ab96ea2fb44ca8219bd4dcf313ab34b449fd`). The first clip includes the lead’s brief entrance near its end. Both files are diagnostics. The separate four-control publication is under `build/axel-f-tgi-listening/`.

No external audio model was called: existing calibration does not qualify a model to determine the listener’s intended balance or identify which percussion they dislike. Source SID/WAV bytes, samples, renderer snapshots and STIL text remain private; checked-in files contain provenance, recipes and note-free aggregate evidence only. No new source reconstruction, player, note extraction or timbre revision was undertaken.
