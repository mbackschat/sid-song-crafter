# Web SID player and arrangement analyser

Status: proposal for later pickup, recorded 2026-10-16. This document preserves the review and brainstorming outcome; it does not authorize application implementation or publication. Technology stack and final playback-library selection remain open.

## Purpose and user requirements

Build a GitHub Pages application where visitors can select and play the project's published samples, in mono and native multi-SID stereo, while reading descriptions and musical analysis drawn from the project's material. Develop it toward the project's eventual web UI.

The application should help people understand instruments, arrangements and how master composers make SID music work. Ordinary player controls are necessary, but insufficient: the visitor should be able to connect what they hear to sound programs, phrasing, musical roles, voice allocation and changes across the song.

The user's requirements, rephrased without changing their scope:

- Write our own application, presentation, interactions and analysis features. Use an existing library for SID playback/emulation rather than implementing a SID player ourselves.
- Support both MOS6581 and MOS8580, each in single-SID and dual-SID stereo configurations, matching the project's scope. These are mandatory capabilities for catalog and locally opened songs, not optional library features.
- Treat correct dual-SID stereo as a decisive library-selection requirement. Generic claims of multi-SID or two-channel output are insufficient; preserve the actual arrangement's chip routing.
- Offer sample selection, playback, song descriptions and analysis from existing project research. Include instrument information, standard voice mute/unmute, spectrum visualization, a playhead, level meters and useful additional ways to see what is happening.
- Treat Safari on iOS and macOS as a hard requirement. Supporting only recent Safari versions is acceptable. A recording fallback does not satisfy the live SID requirement on these platforms.
- Prioritize the desktop experience. Mobile Safari should work, but initially avoid substantial iPhone-specific design, optimization or testing effort; support does not require an equally polished mobile workbench.
- Make instruments and arrangements central. Fill the gap between a regular SID player and an analyser that helps explain masters' songs; suggest useful views and interactions beyond the requested controls.
- Include useful seeking that preserves running state.
- Support optional analysis packages for studied songs, but make most features useful without one.
- Provide a file-opening/upload control so visitors can at least play their own mono and stereo SID files.
- Preserve findings, alternatives and recommendations with their rationale in this proposal. Leave technology-stack discussion open.

## Scope and priorities

### Required product capabilities

- A selectable public sample catalog, with mono/stereo variants, descriptions, analysis, attribution and available downloads.
- Local SID opening, including multi-SID files, without requiring an analysis package.
- Live playback, subtune selection, voice mute/unmute, navigation and synchronized audio/chip inspection on supported Safari versions.
- An arrangement overview and sound inspection that remain useful for unfamiliar files.
- Optional analysis packages that add verified instrument identities, musical roles, section boundaries, explanations and links to evidence.
- Clear separation of measured behavior, recovered source facts, musical interpretation and uncertain automatic detection.

The required hardware coverage is:

| Chip model | Single-SID | Dual-SID stereo |
| --- | --- | --- |
| MOS6581 | Required: three voices, one chip output. | Required: six voices, two chip outputs with the declared stereo routing. |
| MOS8580 | Required: three voices, one chip output. | Required: six voices, two chip outputs with the declared stereo routing. |

This matrix applies to live playback and the associated controls and inspection on supported Safari platforms, with or without an analysis package. The chosen engine must implement both chip models rather than merely relabel one emulation. Honor declared models and addresses, expose the actual configuration, and allow explicit overrides when declarations are absent or a visitor intentionally changes the playback setup.

### Recommended initial boundary

Include the catalog, local file opening, live mono/two-SID playback, voice mute/solo, state-preserving seeking, loops, playhead, output meters, spectrum, voice activity timeline and selected-sound inspector. Include instrument cards and named arrangement sections where annotations exist, while keeping raw inspection available without them.

Rationale: the first useful version must already explain sound and arrangement. Deferring every analyser feature would produce an ordinary player and postpone the project's defining purpose.

### Optional depth

Add richer dependency diagrams, recurring sound-pattern discovery, spectrograms, phrase comparisons, verified mechanism comparisons, personal annotations and score-following where source-backed note data exists. These remain proposals, not promises of automatic decoding for arbitrary drivers.

### Excluded from this proposal

An original SID emulator, automatic recovery of every instrument/score, automatic musical-quality judgments, server uploads/accounts, cloud storage, arbitrary audio stem separation, and a complete composition editor or build-service backend. The eventual web UI may grow into editing and export, but those contracts need a separate proposal. GitHub Pages cannot itself execute our existing Python/native toolchain.

## Application sketch

On desktop, use a persistent transport, a sample/file area, a central timeline and an inspector for the selected passage, voice or instrument. The following is a conceptual layout, not a framework or visual-style decision:

```text
SID Song Crafter                            [Open SID…]
──────────────────────────────────────────────────────────────
Samples / local file   Rambo — centered-lead arrangement
                       [Mono] [Stereo]   PAL · 2 × MOS6581
Bach Toccata           Description · Instruments · Analysis
Instrument mix
Rambo                  [Play] [Restart] [Loop A–B]  0:42 / 3:45
…                      ────────────────●─────────────────────
                       Intro | Main theme | … | Ending

                       Arrangement / voice timeline
                       Lead       ━━━━━━━  ━━━━━━━━━━━━━━━
                       Bass          ━━━━━━━━━━  ━━━━━━━━━
                       Support          ━━━━━━━━  ━━━━━━━━

                       Selected sound / phrase
                       Instrument · Pitch · Pulse · Gate
                       Waveform changes · Filter · Dependencies

                       Output: [L meter] [R meter] [Spectrum]
                       “Listen here…” · Sources · Downloads
```

Labels, time and section names above are illustrative. Actual duration, variants and verified form come from the selected file/package; do not assign the complete Rambo duration to its separately exported main-music version.

Use a basic responsive layout on smaller screens, retaining usable file/sample selection, transport and access to inspection panels. Essential controls must work by touch and not depend on hover. Stacking or collapsing the existing desktop panels is sufficient initially; a dedicated iPhone layout, custom gesture system and equivalent mobile workflow polish are outside the initial scope. Rationale: mobile compatibility is required, while design and development effort should concentrate on desktop exploration.

### Main interactions

| Visitor action | Application response |
| --- | --- |
| Select a project sample | Show its available variants, configuration, description and listening scope; make playback immediately accessible. |
| Choose mono or stereo | Load the corresponding export with its own identity and timeline. Do not imply every variant differs only in panning or can switch seamlessly. |
| Open a local SID | Read it locally, expose header metadata and subtunes, and offer playback and generic inspection immediately. Missing annotations do not block it. |
| Select a voice or sound occurrence | Highlight it on the timeline and show its parameter trajectories, instrument identity if known, and applicable mute/solo controls. |
| Select a phrase | Offer playback with context, a repeatable loop and inspection of its pitch, articulation and sound behavior. |
| Select an instrument card | Highlight its known occurrences and musical roles; jump to an example and open its recipe or owning study. |
| Select a guided listening marker | Seek to the passage, show a short explanation and link the supporting evidence. |
| Compare two passages | Inspect differences in instrument selection, register, articulation and accompaniment; preserve their separate timing and context. |
| Change mute/model/clock settings | Update live sound and measurements together; indicate when authored analysis no longer matches the reference configuration. |

Recommended file control: **Open SID…**, with desktop drag-and-drop and the iOS file picker. Although requested as an upload button, the proposed behavior is local file loading: no file leaves the device. Rationale: server storage is unnecessary for playback and would expand scope. Reload/session persistence is not yet specified.

## Views that explain the music

| View | Content and interaction | Musical value |
| --- | --- | --- |
| Arrangement timeline | Voice activity, entrances, gaps and register changes for any supported file; named roles and sections when available. Select and loop a span. | Shows density, contrast, recurring material and allocation of musical space. |
| Instrument palette | Verified programs and characteristic behavior when annotated; provisional recurring sound patterns when discovery is available. Select occurrences. | Connects sound identity to its use throughout an arrangement. |
| Sound microscope | Selected event's frequency/pitch, waveform controls, pulse-width motion, gate/retrigger events and filter settings over time. | Explains attack, body, movement, release and the next onset. |
| Voice allocation | Three or six physical voice lanes with time-dependent role labels where known. | Exposes voice borrowing, alternating bass/percussion and interrupted support. |
| Dependency map | Ring/sync relationships, shared filter routing and chip-output placement. | Explains why sounds cannot always be isolated or moved independently. |
| Phrase comparison | Two selected passages, with available note/program evidence and sound trajectories. | Distinguishes patch changes from changes in register, phrasing and context. |
| Audio monitor | Waveform scope, spectrum, optional spectrogram, L/R peak and RMS meters in dBFS and clipping indication. | Shows transients, brightness, balance and silence without claiming instrument identification. |
| Guided listening | Brief passage-specific observations linked to the owning study and its evidence scope. | Makes accumulated research usable while the relevant music is heard. |

The preferred exploration sequence is: **hear a phrase → select it → inspect the sound and allocation → compare another occurrence → read the explanation or reusable recipe**.

For example, the [Hülsbeck study](../../songs/axel-f/huelsbeck-study.md#targeted-role-study-lead-support-and-the-apparent-switch) records a perceived change near one minute while the executed lead program remains the same. Shorter articulation, higher register and surrounding development change the result. A useful UI highlights those changes and shows that short notes restart before the pulse trajectory develops fully. This is a bounded finding about that source passage, not a composer-wide rule or permission to publish its audio.

Other useful annotations include “the bass enters here,” “support yields to the lead's modulator,” and “this instrument returns in a higher register.” Each needs song-specific evidence; these examples are suggested editorial forms, not findings for arbitrary files.

## Useful without an analysis package

| Capability | Any supported SID | Added by a matching analysis package |
| --- | --- | --- |
| Playback | Transport, subtunes, voice mute/solo and configured mono/multi-SID output. | Suggested passages and retained listening comparisons. |
| Configuration | Header title/credits, chip declarations, addresses and clock where present; explicit overrides for unknown or alternative settings. | Verified configuration, intended mix and source identity. |
| Navigation | Elapsed time, state-preserving seek and user-selected loops. | Known duration, named sections and verified phrase boundaries. |
| Visualization | Audio displays and observable chip-state trajectories. | Interpretation of the behavior and links to recovered mechanisms. |
| Arrangement | Voice activity, frequency/register movement, entrances and gaps. | Source-backed notes, roles, instrument changes, harmony and form. |
| Instruments | Observable sound characteristics; optional detected patterns. | Recovered program identity, editable parameters, dependencies and reuse examples. |
| Notes | User bookmarks and descriptions, if included. | Curated commentary, evidence and scoped listening verdicts. |

“Any supported SID” means a file admitted by the chosen engine and declared format/profile support. Malformed files and unsupported formats should receive a useful explanation. Compatibility with ROM-dependent RSID, unusual timing, digi playback and three-SID files needs an explicit library decision; do not silently promise all SID files from mono/two-SID success.

### Automatic sound-pattern discovery

Recommendation: explore grouping recurring waveform sequences, pulse movement, pitch behavior and articulation into entries such as “Sound pattern 1,” with clickable occurrences and optional user names. Rationale: this bridges the gap between generic registers and an instrument-oriented experience for unfamiliar songs.

Treat these as provisional patterns. One instrument can produce different trajectories depending on pitch, duration and prior state; unrelated programs can produce similar ones. A verified instrument definition may replace or refine a pattern label, but detection must not claim recovered source identity. The feasibility and usefulness of grouping remain untested, and it should not block basic inspection.

## Analysis packages and evidence

An analysis package enriches a precise song/export identity. It should reference existing owners rather than duplicate score, instrument or research definitions. The representation and schema remain open; the semantic contract is:

| Information | Required meaning |
| --- | --- |
| Identity and configuration | File fingerprint, selected subtune, clock, chip models/addresses, engine/settings relevant to the evidence, and output routing. |
| Time reference and coverage | Event timestamps and their time basis; analysed regions; how they correspond to the playable export. |
| Musical annotations | Sections, phrases, instrument occurrences, role assignments and source-backed notes where available. |
| Mechanisms and dependencies | Recovered instrument behavior, physical voice allocation, coupling/filter ownership and links to editable examples. |
| Provenance and verdicts | Source attribution, owning studies, evidence references, publication scope and precisely scoped listening findings. |

Display three evidence categories: **verified** source/execution facts, **derived** measurements or detections, and **interpretation** of musical purpose/effect. An absence of evidence stays unknown. Automatic derived pitch is not necessarily the score note, especially during arpeggios, modulation or noise.

Live playback supplies sound and exposed chip state; retained score/program/execution records supply deeper explanation. Register snapshots are not complete ordered-write traces and may miss rapid changes. Keep observation cadence and coverage explicit in detailed inspection. Existing reference traces must be aligned to the declared configuration and time basis rather than presented as fresh live measurements.

Programmed ADSR settings are not measured envelope amplitude, GATE clear is not silence, and voice activity is not necessarily audible contribution. A shared nonlinear filter also prevents casually treating isolated voice recordings as additive stems. Output meters should report measured PCM; do not disguise a register-derived activity indicator as a per-instrument dB meter. The [instrument-program explanation](../research/composition/instruments-as-programs.md) and [execution workflow](../research/tools/sid-program-analysis.md) own these distinctions.

## Playback, routing and navigation contracts

### Voice controls and stereo

Standard voice mute/solo is required. Musical “mute lead” controls are optional and need verified time-dependent role mappings: a lead can occupy voices on both chips, and a voice can change roles. Muting must preserve oscillator execution and required dependencies where the engine permits; verify semantics before describing it as harmless isolation. Retain the full mix as context.

Each chip has one mono output and a shared filter; there is no native per-voice pan register. Preserve the declared chip-to-output matrix. Our accepted Rambo stereo rendering deliberately uses separate chip buffers because the native library's default mixer crossfeeds them. Multi-SID playback alone therefore does not establish the correct image. See the [hardware/mixing contract](../research/sid/dual-sid.md#plan-the-sound-hardware-and-the-mix-together) and [renderer](../../scripts/render-sid.cpp).

For unannotated files, identify the player-selected output routing as a playback setting, not recovered composer intent. Recommend a visible, deterministic chip-bus routing default; finalize its exact behavior with the engine's capabilities.

### Seeking and loops

Seeking must reach the state that continuous playback from initialization would have reached under the same configuration, including CPU/player, oscillator, envelope and filter history. Moving a counter or calling the music routine at the destination is insufficient. Execution to the destination is acceptable; complete emulator snapshots are an optimization only if supported and verified. Show progress when a seek takes time.

Offer click/touch seeking, named section jumps when known, previous/next annotated phrase, and A/B loops. Recommend study loops that re-enter the same passage state each time, so repeated listening is comparable. Account for any audio-boundary discontinuity separately; restoring state does not promise a seamless loop splice.

SID metadata generally lacks duration. Unknown-length playback should have elapsed time and a growing explored timeline, without invented completion percentages or endings. Reaching an unexplored destination can require additional emulation. Known project durations should come from the matching package rather than an unrelated database entry.

The playhead and inspection cursor must track audio heard, including buffering, rather than the furthest point already emulated. Seeking, muting and configuration changes must not leave stale inspection data presented as current.

### Live SID and accepted recording

Recommend two clearly labelled modes for catalog entries with both assets: **Live SID** for interaction and **Accepted recording** for the retained reviewed performance. Voice controls apply to live playback. Recording mode must not display unrelated live chip state; matching retained analysis can be shown with its provenance.

Rationale: the accepted WAV remains a useful reference and fallback, while engine/version/settings can affect live sound. A recording does not substitute for Safari live-player compatibility or prove emulator equivalence.

## Safari and hosting requirements

Safari on iOS and macOS is mandatory, with desktop as the primary design and validation target. Recommendation: initially target current stable Safari on each platform, with exact versions recorded when implementation begins; broader version coverage can follow if needed. Rationale: the user accepts recent Safari and explicitly wants limited iPhone-specific effort.

Recent Safari supports the needed [AnalyserNode](https://github.com/mdn/browser-compat-data/blob/main/api/AnalyserNode.json) and [AudioWorklet](https://github.com/mdn/browser-compat-data/blob/main/api/AudioWorklet.json) APIs. That establishes API availability, not the performance or reliability of the assembled app. Validate the full exploration workflow on Mac Safari. Use a bounded smoke check on a recent iPhone for local file opening, live mono/stereo playback, basic seek/mute controls, visible analysis and recovery after an interruption. Fix blocking compatibility defects, but defer a broad iPhone/device matrix, mobile performance tuning beyond usable operation and bespoke interaction polish. Background/locked-screen playback is not yet a promised capability.

[GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) supports a static application with browser-side playback and local file access. Select a browser execution approach compatible with the hosting environment; do not assume particular response headers or shared-memory facilities are available. No framework, language, bundler, UI toolkit, plotting library, worker arrangement or server architecture is selected here.

## Playback-library findings and alternatives

Findings include upstream documentation and the pinned source review below. No candidate was executed against our samples or tested in Safari during this review. Source inspection establishes specific API/mixing behavior, not runtime compatibility or musical equivalence.

| Candidate | Finding | Recommendation and rationale |
| --- | --- | --- |
| [libsidplayfp-wasm](https://github.com/chrisgleissner/libsidplayfp-wasm) | Independent WASM distribution with TypeScript bindings, PCM streaming, SIDLite/reSIDfp, multiple chips, muting, register readout and timestamped writes. Current binding uses a crossfeeding mixer and lacks raw chip output; its seek wrapper discards the final block remainder. | Preferred engine family, conditional on a small binding/transport correction and verification. The current package is not an exact-routing drop-in. |
| [WebSID](https://www.wothke.ch/websid/) | Browser SID engine, now maintained on [Bitbucket](https://bitbucket.org/wothke/websid/), with multi-chip emulation, explicit per-voice panning and visualization access. Its README declares CC BY-NC-SA 4.0. | Retain as an alternative, with a less suitable distribution license and a different sound path to assess. Panning controls alone do not establish our accepted chip-bus sound. |
| [jsSID](https://github.com/og2t/jsSID) | Small JavaScript implementation with multi-SID support; its README documents omitted digi playback and imperfect interrupt emulation. | Not the preferred foundation: those limitations narrow the range of masters' material we could inspect. Retain it as an evaluated alternative, not a selected fallback. |
| [DeepSID](https://github.com/Chordian/deepsid) | Complete player application whose documented setup uses PHP and MySQL. | Use as interaction inspiration rather than adopt its application: we want our own UI and static hosting with a library boundary. |

libsidplayfp-wasm declares GPL-2.0-or-later and supplies corresponding source; it is not an MIT dependency. Confirm the combined web distribution's terms before adoption. This does not change the project's existing tool or sample licenses. A small binding extension could remain within the library approach, but maintaining a custom player is outside scope.

### Dual-SID source review, 2026-10-16

The unresolved question was whether a browser library can reproduce our native dual-SID placement for both chip models while providing useful inspection. This blocks final engine selection. Review pinned libsidplayfp-wasm [commit c9622e9](https://github.com/chrisgleissner/libsidplayfp-wasm/tree/c9622e9ce7ffa2ddd3e0568e987b4c6614da8275), package version 1.1.0, whose [upstream manifest](https://github.com/chrisgleissner/libsidplayfp-wasm/blob/c9622e9ce7ffa2ddd3e0568e987b4c6614da8275/upstream.json) pins libsidplayfp 3.1.1 and libresidfp 1.2.3. This is a source-level review only; no playback, audio comparison or Safari validation is claimed.

**Concrete routing mismatch:** `SidPlayerContext::render()` calls `player.mix()`. The exported binding has no raw-chip-buffer or mixing-matrix method. The pinned upstream [SimpleMixer](https://github.com/libsidplayfp/libsidplayfp/blob/732fa8ec8131fc75aafc2eaea583ddcdeea2a3cc/src/simpleMixer.h) mixes two chips approximately as `L = (A + 0.5 B) / sqrt(2)` and `R = (0.5 A + B) / sqrt(2)`, with integer scaling/rounding. This is stereo, but not our required `L = A, R = B`. It places each chip in the opposite channel at roughly −6 dB relative to its contribution in the main channel. Both MOS6581 and MOS8580 use this host mixer. See the [binding source](https://github.com/chrisgleissner/libsidplayfp-wasm/blob/c9622e9ce7ffa2ddd3e0568e987b4c6614da8275/src/bindings/bindings.cpp#L796).

Recommendation: retain libsidplayfp as the leading engine family, but require raw per-chip PCM from one shared emulated C64 instance, or an equivalent verified output-matrix API. This is a binding/output integration requirement, not a new SID emulator. Prefer an upstreamable extension. Do not approximate dual-SID by running independent mono players, reconstruct raw buses by inverting rounded mixed PCM, or add artificial widening: those approaches weaken timing, signal or placement guarantees. Preserving complete chip buses also preserves shared-filter behavior within each chip.

**Inspection is stronger than initially established:** the binding exposes per-chip status and bounded timestamped write traces, including chip index, register address, value and `cyclePhi1`, plus a dropped-record count. The [trace-hook modification](https://github.com/chrisgleissner/libsidplayfp-wasm/blob/c9622e9ce7ffa2ddd3e0568e987b4c6614da8275/MODIFICATIONS.md) places the hook immediately before the emulated chip write. This offers a promising basis for inspecting unfamiliar songs without authored analysis. Drain traces with playback and disclose overflow. Since muting/filter bypass can modify writes before this hook, distinguish observed emulator input from the unmodified program's writes.

**Muting is an intervention:** upstream [sidemu.cpp](https://github.com/libsidplayfp/libsidplayfp/blob/732fa8ec8131fc75aafc2eaea583ddcdeea2a3cc/src/sidemu.cpp) masks waveform/GATE bits on subsequent control-register writes while preserving TEST/ring/sync bits. It is not a post-filter fader and may not act immediately on an already-held sound. Validate coupled passages and restoration before promising clean isolation; keep the application's six controls explicit about their voice and chip.

**Seeking needs a more precise contract than the method name suggests:** [player.ts](https://github.com/chrisgleissner/libsidplayfp-wasm/blob/c9622e9ce7ffa2ddd3e0568e987b4c6614da8275/src/player.ts#L719) reloads and emulates forward, which preserves evolving state in principle. However, `fastForwardContext()` discards whole blocks until the target is passed, then clamps the reported count without retaining the final block's remainder. Source inspection therefore predicts a block-boundary offset for non-aligned targets; the current tests establish advancement, not exact continuation samples. Require a seek comparison against continuous playback and retain the remainder in the transport before calling seeking sample-accurate. Record deterministic startup settings and reapply inspection/control state consistently after reload.

**Safari evidence is narrower than real-device audio:** the pinned [Playwright configuration](https://github.com/chrisgleissner/libsidplayfp-wasm/blob/c9622e9ce7ffa2ddd3e0568e987b4c6614da8275/playwright.config.ts) includes WebKit with an iPhone device profile. Its [browser tests](https://github.com/chrisgleissner/libsidplayfp-wasm/blob/c9622e9ce7ffa2ddd3e0568e987b4c6614da8275/test/browser/loader.spec.ts) check PCM generation from a test tone and worker operation. They do not certify actual Safari speaker playback, our two-SID material or our routing. Preserve the bounded mobile checks above; desktop Safari remains the main validation target.

**WebSID alternative:** inspected [revision 977457f](https://bitbucket.org/wothke/websid/src/977457f172bc52907953850827d110b8c4e9f31b/). Its [SID implementation](https://bitbucket.org/wothke/websid/src/977457f172bc52907953850827d110b8c4e9f31b/src/sid.cpp) handles per-chip model declarations and pans voice contributions into stereo. The [postprocessor](https://bitbucket.org/wothke/websid/src/977457f172bc52907953850827d110b8c4e9f31b/src/Postprocess.cpp) uses level 0 for panning without the enhancement effect; level −1 disables panning. Assigning all three voices of chip A left and chip B right is a plausible tonal routing setup, not yet a verified replacement for raw chip buses. Special digi paths can feed both channels, and the [documented limitations](https://bitbucket.org/wothke/websid/src/977457f172bc52907953850827d110b8c4e9f31b/src/KnownLimitations.txt) include filter/combined-waveform accuracy limitations. Its [CC BY-NC-SA declaration](https://bitbucket.org/wothke/websid/src/977457f172bc52907953850827d110b8c4e9f31b/README.md) adds a noncommercial restriction. These are material reasons to prefer resolving the bounded libsidplayfp binding gap first, without claiming WebSID is incapable of useful stereo.

### Evidence required before adopting the stereo backend

| Required property | Decisive check |
| --- | --- |
| Both chip models and counts | Load MOS6581 and MOS8580 single/dual exports; confirm actual installed models, addresses and independent activity on both chips. |
| Correct stereo separation | A-only/B-only diagnostic input must reach its assigned output without hidden crossfeed; verify gain and clipping separately from stereo width. |
| Real arrangement behavior | Compare [Bach stereo](../../samples/bach-toccata/README.md) for MOS8580 and [Rambo stereo](../../samples/rambo-stereo/README.md) for MOS6581 against their retained renders, including the duplicated lead, accompaniment separation, shared filtering and coupled Rambo passages. Full playback and endings must work; PCM identity is only a valid expectation under matched engine/build/settings. |
| Complete session controls | Verify all six voice controls, stop/reload, seek and loop behavior; check resumed audio against continuous playback with the same startup/configuration. |
| Synchronized analysis | Both chips' observations align with heard output and seek position; trace drops and diagnostic mutations are visible. |
| Safari usability | Validate the complete desktop audio path and the bounded recent-iPhone smoke check, not just successful WASM rendering. |

Correct dual-SID playback is a selection gate, not optional polish. Final library adoption remains open until these checks pass; neither reviewed candidate is currently certified for this app.

## Catalog and publication boundary

Use the [sample library](../../samples/README.md), its owning package READMEs and manifests as the current source of truth. The catalog expanded during this discussion: it now includes additional stereo exports and local-build-only material. Do not freeze the earlier four-entry inventory into application requirements.

Represent every sample package with its actual availability and scope. Offer online playback/downloads only for publication-cleared files. Materials-only entries can explain the work and point to reproducible local recipes; they must not expose uncleared music. A user may open a locally obtained file without it becoming part of the public catalog. Preserve the [publication boundary](../../CLAUDE.md#public-repository-boundary) and song-specific attribution/licenses.

Keep full versions, excerpts and separately exported entrances distinct. The [current Rambo packages](../../samples/README.md#rambo-entrance) include native main-music exports with fresh SID oscillator/envelope history; those are not equivalent to seeking through the complete original-introduction version. Both can be useful, but their timelines and explanations must match their exact files.

## Open decisions for later pickup

No further user clarification is required to retain this proposal. These decisions remain open rather than silently settled:

| Decision | Current recommendation and rationale | Evidence needed |
| --- | --- | --- |
| Playback library | Prefer the libsidplayfp family if the raw-output and seek gaps can be resolved with a bounded binding/transport change. | The stereo adoption checks above; licensing fit. Do not adopt the current mixed-output wrapper as an exact-routing solution. |
| Safari version floor | Current stable Safari on macOS and iOS initially; keep mobile effort bounded and extend coverage only when needed. | Full desktop validation and a recent-iPhone compatibility smoke check, with exact versions recorded. |
| File compatibility beyond required hardware coverage | Both MOS6581 and MOS8580 in single-SID and dual-SID stereo are fixed requirements; declare additional format/profile support individually. | Engine handling of PSID/RSID, ROM requirements, timing, digi and three-SID cases. |
| Sound-pattern discovery | Optional provisional grouping, with editable labels. | Useful results on unfamiliar material without false claims of recovered instruments. |
| Deeper inspection | Prefer exposed live state plus matching retained execution evidence. | Available event resolution, buffering alignment and missing binding capabilities. |
| Analysis-package format | Preserve the semantic contract above; reuse existing owners. | What the UI and existing manifests can share without duplicate sources of truth. |
| Technology stack | Leave open, as requested. | Compatibility with Safari, static hosting and the selected playback API. |

The decisive feasibility evidence is playback and inspection across the required MOS6581/MOS8580 × single-SID/dual-SID stereo matrix on Safari, covering annotated project samples and unannotated local files, correct model selection and routing, mute dependencies and a seek checked against continuous playback. Retain the desktop-focused validation and bounded mobile compatibility checks described above. The analyser must remain useful when annotations are absent. These are acceptance questions for later work, not an implementation schedule or authorization to start it.
