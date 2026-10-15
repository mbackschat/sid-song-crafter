# Two SID chips

## What changes

Two independently addressed chips provide six oscillator/envelope voices and two independent filter/master-volume groups. Their audio may be mixed or separated into stereo by the hardware. Stereo output alone does not establish six independent voices: pseudo-stereo duplication is a different configuration. FPGASID's configuration documentation makes this distinction explicit. [S15](../sources.md#s15)

Choose the intended musical positions before allocating voices to chips. Keeping melody and its coupled voices together can preserve the instrument, but it also groups their output position; a centered lead with separate side accompaniment needs a different allocation. Keep each chip’s filter ownership explicit. A six-voice arrangement should also have a documented three-voice reduction if standard C64 playback matters.

## Expand the musical capacity, not only the stereo image

The user's arrangement principle, clarified on 2026-10-15: study what a master achieved within one SID's limits, identify where musical roles had to share scarce resources, then use the second SID to develop those roles while preserving the work's character. Stereo placement is one part of that interpretation. Extra notes, louder backing or a wider copy alone do not demonstrate that the additional capacity serves the music.

Build a short constraint map before arranging: **source passage and role → observed resource sharing → musical consequence to test → additional voice/filter allocation → comparison that can settle its value**. Consult composer interviews, contemporary accounts and relevant literature alongside executable evidence; retain citations in the [composer studies](../composers/README.md). Separate a documented composer complaint, an observed implementation limit and our arrangement hypothesis. “What might the master do with two SIDs?” guides interpretation; it is not permission to attribute our decisions to the composer.

| Source constraint to establish | Possible use of the second chip | What must survive the change |
| --- | --- | --- |
| Bass and percussion take turns on one voice | Give a recovered percussion role its own oscillator so bass and drum bodies can overlap | Source groove, attack placement and balance; do not invent missing drums solely because capacity is available |
| A new note replaces a still-sounding envelope | Allocate overlapping notes to separate voices so a selected release can finish | Phrasing and harmonic compatibility throughout the overlap; a nonzero lifetime counter alone does not prove audible loss |
| One oscillator serializes chord tones | Sustain selected source chord tones independently, or separate chord articulation from its rhythmic arpeggio | Characteristic arpeggio motion and actual chord colors; a resource-saving gesture can also be an essential aesthetic choice |
| Sync/ring effects require another oscillator | Reserve the coupled pair and place other roles on the second chip | Correct physical coupling and source timbre |
| Shared filter prevents independent treatments | Give roles separate chip filters where the source and musical intent justify it | Target-chip behavior and balance; a second SID does not remove physical filter variability |

More voices do not remove CPU, memory, driver or output-routing constraints. Empty passages are not automatically lost opportunities. Start with one demonstrated resource-sharing mechanism and one bounded musical comparison, then retain the result before expanding the treatment. For Rambo, the [source audit and next experiment](../../../songs/studies/rambo-ensemble/README.md#resource-informed-revision) replace generic added harmony as the basis for the next revision.

Before freeing a release from its next retrigger, check its actual ongoing pitch program against the changing harmony. In the [Rambo screening](../../../evidence/rambo-resource-audit/README.md#release-hypothesis-rejected-before-rendering), nominally matching onset pitches concealed a large descending bend, while other tails crossed chord changes. Resource availability does not justify extending every voice lifetime; retain deliberate phrase separation unless the new overlap has a musical purpose and listening support.

## Plan the sound hardware and the mix together

**Each SID has one mono audio output.** Its three oscillators are not three independently pannable outputs. Two SIDs supply six voices but only two chip-output buses. There is no SID pan register. These hardware constraints follow the [register map and output/filter model](hardware.md); the [renderer implementation](../../../scripts/render-sid.cpp) deliberately captures each chip's raw output separately instead of hiding the library's crossfeed.

| Musical decision | Hardware constraint and required arrangement decision |
| --- | --- |
| Center a melody or bass | Center the chip's output in the external/renderer mix, which also centers its other audible voices, or allocate matching material to both chips. Duplicating material consumes voices and must preserve modulation dependencies; do not assume free per-voice panning. |
| Spread accompaniment | Assign it to a separate chip bus and declare that bus's left/right gains. Independent left/right placement of every one of six instruments is not a native two-SID facility. |
| Use six voices creatively | Give added voices musical roles, source-derived pitches, articulation and phrase placement. Splitting an existing three-part score over two chips is a spatial diagnostic, not a six-part arrangement. All six voices need not sound continuously. |
| Preserve sync or ring modulation | Keep recipient and modulator on the same chip at compatible physical oscillator indices. Moving a voice can change its instrument even when its notes and register values are unchanged. |
| Shape balance and tone | Master volume and filter are shared within each chip. Coordinate filter ownership; envelope settings and register choices are not interchangeable with independent mixer gain controls. |
| Deliver the intended stereo sound | Record chip addresses/models, raw bus mapping and the actual output matrix. The project's PSID export declares the chip configuration, not the WAV's arbitrary mixing matrix. A player or hardware mixer must reproduce that matrix to reproduce the intended stereo presentation. |

**Placement is a deliberate musical choice.** The user's clarification on 2026-10-15 is to choose the position of each musical role for its function in the arrangement, then design the chip allocation to realize that map. A stable central lead does not prohibit a centered bass, another supporting part or a deliberately centered group. Left, right, center and movement should each serve a stated musical purpose; shared chip ownership must not silently choose those positions for us. Preserve useful contrast between the remaining roles and account for any voice duplication, coupling or reductions needed to realize it. This is neither a rule that only the lead may be centered nor a requirement to fill every position continuously.

Before adding notes or selecting patches, write the role → chip/voice → coupling/filter ownership → output mix map in the owning arrangement. Validate both the native export and the rendered presentation; do not infer one from the other. Preserve a mono fold-down, check that centered material has equal left/right coefficients, and compare at one shared gain per stereo clip so channel balance is not erased by independent normalization.

For example, the [Rambo ensemble](../../../songs/studies/rambo-ensemble/README.md) retains the faithful trio on chip A and adds three support roles on chip B. Its intended presentation is `left = 0.5 A + 0.35 B`, `right = 0.5 A + 0.65 B`: A is centered and B is biased right; this is not six independent pan positions. The [shared mixer](../../../scripts/prepare-dual-listening.py) implements that matrix and writes a hash-pinned receipt. The [earlier bass-only split](../../../songs/studies/rambo-stereo/listening-review.json) failed the user's intended scope because it only redistributed the original parts. That is a delivery lesson, not a verdict that raw stereo or three-part music is inherently inferior.

### A correct matrix can still miss the spatial brief

The [Rambo ensemble feedback](../../../songs/studies/rambo-ensemble/listening-review.json) reports uncertain added weight and no clearly left/right instrument despite verified six-voice execution and the exact matrix above. That matrix centers the entire primary trio; support is merely right-biased and no group favors the left. Before PCM rounding, its mid signal is `M = (L+R)/2 = 0.5 A + 0.5 B`, while its side signal is `S = (L-R)/2 = -0.15 B`. The dominant primary contributes nothing to side information. This explains the limited placement design; it is not a universal audibility threshold or proof that support is musically useful.

Write the intended perceptual placements before choosing the matrix: a centered part, a clearly left part and a clearly right part are different requirements. Centering every primary part with mild crossfeed from the support does not implement that map. First compare the existing raw chip separation at matched whole-clip level to isolate the mix decision; do not compensate by blindly raising accompaniment or adding notes. A direct A-left/B-right comparison offers two clear groups but no independently centered instrument. If the brief requires all three placements simultaneously, revise the native allocation with the voice and coupling costs made explicit.

Duplicating a part across chips consumes an oscillator on each; duplicating a coupled lead may also require its modulator. For example, duplicating the Rambo bass would leave only two second-chip voices for distinct added roles. Copying notes alone is insufficient when source hooks affect scheduling, and identical register programs on independent chips do not guarantee identical oscillator phase or envelope history. Verify the complete timing and resulting center image rather than promising sample identity.

A request for a centered lead with other instruments on both sides requires independent musical roles at those positions. Centering the whole chip that contains the lead also centers its other voices and does not satisfy that brief. The [Rambo feedback](../../../songs/studies/rambo-chord-expansion/README.md#center-the-lead-while-keeping-accompaniment-on-both-sides) explicitly rejected that substitution before an audition. Native lead duplication consumes an oscillator on each chip, plus any required same-chip modulators; document which former roles are reduced and verify oscillator history as well as register sequences. Keep optional [left/right movement](../composition/gestures/stereo-movement.md) separate from stable placement.

The [native Rambo revision](../../../songs/studies/rambo-centered-native/README.md) realizes this with a complete lead on A1/B1, original bass/arpeggio on A, and inner/held harmony on B. It replaces the former added low anchor and lends B3 to the source modulator during coupled passages, retaining 37 of 42 complete held regions. The compared phrase is accepted for centered lead, side separation and fullness; the complete revised performance is subsequently accepted. Software entry-state restoration preserves executed programs but cannot restore oscillator/envelope history. The accepted sound is the evidence for this particular spatial result, not a universal claim that duplicated programs are phase coherent.

The [Rambo held-chord trial](../../../songs/studies/rambo-chord-expansion/README.md) also separates score preservation from PCM identity. Changing the second engine's workload can alter the host's next entry phase even when the first engine's bytes, ordered register stores and within-call write offsets are unchanged. In this case VICE measured entry differences of −8 to +8 cycles after the changed support began. Do not promise bit-identical primary audio from an unchanged register calendar: retain host timing evidence, measure the rendered difference and verify complete ending coverage separately. This is a measured property of this shared host, not a universal two-SID jitter bound.

The [retained placement-only diagnostic](../../../evidence/rambo-ensemble-width/README.md) verifies this mapping distinction on the same initialized six-voice PCM, with matched whole-clip gains. Keep width measurements separate from listening and from the musical value of relieving a source constraint.

## Address agreement

The first SID normally lives at `$D400`. Common second-chip choices include `$D420`, `$D500`, and `$DE00`, but hardware decoding and expansion conflicts decide what is usable. Standard mirrored SID space does not create a second chip. The hardware, exported tune, and emulator must agree on the selected address. [S05](../sources.md#s05), [S15](../sources.md#s15)

PSID v3 encodes the second SID location in header byte `$7A`: `$42` means `$D420`, `$50` means `$D500`, and `$E0` means `$DE00`. Valid address codes are restricted; do not accept arbitrary bytes. v4 adds the third-chip field, which this project does not currently need. [S13](../sources.md#s13)

## Tools and execution

Implemented routes retain separate authoring contracts:

- [SID-Wizard's native two-chip Extra player](../tools/sid-wizard-trial.md): six ordered voices, two independent filters, editable `.sws` source and PSID v3 export for two 8580s at `$D400/$D420`. Follow [the shared native workflow](../../workflows/native-song-workflow.md) for its original six-voice fixture, stereo render and headless VICE checks.
- [Independently computed Flashdance programs](../../workflows/decoded-song-workflow.md#add-an-independently-authored-second-chip): two semantic descriptions compile to separate engines and a shared PAL wrapper, exporting PSID v3 for two 6581s at `$D400/$D420`. The [authored arrangement](../composition/flashdance-preparation.md#deliberate-dual-sid-interpretation) has full two-bank CPU/VICE, stereo/mono and ending evidence; its owning study retains listening feedback and limits.
- [Rambo spatial interpretation](../../../songs/studies/rambo-stereo/README.md): one score engine distributes the faithful three parts across two 6581s at `$D400/$D420`. The lead and its sync/ring modulator remain together; only the independent bass moves to chip B. No notes, instrument patches or extra musical parts are added. The compiler checks that future source edits do not introduce unsupported cross-chip dependencies or shared-filter behavior; listening acceptance belongs to the case, not to the routing mechanism.
- [Rambo expanded ensemble](../../../songs/studies/rambo-ensemble/README.md): two independent Rambo graph engines preserve the faithful trio and add three source-derived support roles. The [dual compiler](../../../scripts/compose-rambo-dual.py) keeps player RAM and chip registers separate under one frame budget. Its centered-primary WAV mix is explicit and checked separately from native PSID execution.

GoatTracker Stereo remains an alternative tracker backend. ChiptuneSAK's GoatTracker module recognizes three- and six-voice song structures. c64bridge's inspected SIDWAVE compiler explicitly constructs only voices 1–3, so dual-SID output is not an established capability there. [S08](../sources.md#s08), [S12](../sources.md#s12), [S24](../sources.md#s24)

VICE uses `-sidextra 1` and `-sid2address 0xd420` to select the additional chip. An illustrative interactive launch is:

```sh
x64sc -pal -sidextra 1 -sid2address 0xd420 -autostart song.prg
```

The [headless verifier](../../validation/native-vice-checks.md) uses these address flags with the local VICE 3.9 build, explicit 8580 selection and monitor-controlled startup. That tested route handles SID-Wizard's address selector without changing PRG bytes; the illustrative `-autostart` command above is not the tested unattended route. [S16](../sources.md#s16)

The [ordered-store VICE tracer](../tools/sid-program-analysis.md#reproduce-the-execution-evidence) also accepts callable PAL PSID v3 with two matching 6581s or 8580s at `$D400/$D420`. It compares both sound-register banks against the CPU oracle in a controlled harness, including independent filter values. Its [executed fixture](../../../tests/sid_vice_trace_test.py) validates this mechanism; full arrangement, audio and listening checks remain separate.

## Six-voice acceptance checks

- Play one test note on each voice independently and confirm both chip addresses respond.
- Verify that chip A's filter/volume changes do not change chip B's controls.
- Check channel routing and a mono downmix for balance.
- Test the declared SID models, including a mixed-model setup if supported and intended.
- Measure player CPU cost with all six voices and effects active.

Independent fixtures establish six distinct sounding frequency words, separate filter registers and simultaneous stops. Renderer tests use different pitches and either-chip-muted variants to verify independent stereo channels without crossfeed. The native fixture passes complete note scheduling, PCM health and sampled VICE register/cadence checks. Both chips share one PAL CPU-frame budget; adding a SID does not add CPU time.

Physical hardware and mixed chip models remain unverified. Full-arrangement stereo/mono balance and listening quality belong to each study's verdict, rather than following from short fixtures. The native converter's 105-pattern/29-instrument limit bounds long tick-grid arrangements; the computed two-engine route must instead fit callable RAM and one shared PAL frame budget. Successful short-fixture playback does not establish that an arbitrary six-voice score will fit.
