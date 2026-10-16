# Ghouls 'n' Ghosts: reference intake

This preparation pins the C64 reference, preserves supported subtune attribution and establishes finite stream consumption for provisional selection **1**, followed by continued filter refresh. CPU execution covers 40,000 calls, with independent VICE comparisons at the opening and final stream stop. The complete editable numeric player, compiled export and full callable VICE comparison match the original ordered stores. The reconstruction's characteristic phrase and complete ending are accepted; the familiar transfer has accepted instruments, balance and ending with a tentative tune reservation and no detected note-mapping defect. Bounded Gauntlet III corroboration is complete, closing the declared Ghouls/Follin scope. Selection 1's musical role remains unidentified; no wider attribution claim follows. Read the [Follin composer study](../composers/follin-daglish.md), [technique lookup](../technique-index.md) and [execution procedure](../tools/sid-program-analysis.md) before reusing a finding.

## Reference identity

The [HVSC reference](https://www.hvsc.de/download/C64Music/MUSICIANS/F/Follin_Tim/Ghouls_n_Ghosts.sid) is retained privately at `.local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid`. The [header report](../../../evidence/ghouls-intake/header.json) and [intake receipt](../../../evidence/ghouls-intake/receipt.json) preserve metadata, source/tool fingerprints and the bounded execution result checked on 2026-10-13. The original SID and its payload are excluded from the evidence archive and Git.

| Declaration | Pinned value |
| --- | --- |
| SHA-256 / file size | `265644a66d6043e6fe5ddeeb0d87e9b4269386a73c3e26457c8d96ce3d042df4` / 19,005 bytes |
| Header | PSID v2, data offset `$007C`, embedded load address |
| Header title / author / release | `Ghouls 'n' Ghosts` / `Tim Follin` / `1989 US Gold/Capcom` |
| Load / init / play | `$2980` / `$6110` / `$6234` |
| Payload extent | 18,879 bytes; end `$733F` exclusive |
| Subtunes | 32; default 1 |
| Clock / SID / speed | PAL / MOS6581 / speed word `$00000000`, VBI declaration for all 32 entries |
| Flags | `$0014` |

These are header declarations, not measured call cadence or musical roles. The [download registry](../../../config/local-assets.json) supplies the exact URL, hash, private destination and non-default reference entry; it does not contain source bytes.

## Supported subtune labels and authorship

Cached [HVSC STIL v85](https://hvsc.c64.org/download/C64Music/DOCUMENTS/STIL.txt), dated June 28, 2026 and SHA-256 `b1ef3584a5b3501e2bbd2ef056d6539a1bbee7933a7828537c3946c1b16cde43`, identifies only two entries for this file. The receipt enumerates all 32 subtunes and preserves unknown labels explicitly.

| Entries | Supported label / original-source attribution |
| --- | --- |
| 8 | Stage 2: The Village of Decay; arcade source music credited to Tamayo Kawamoto |
| 10 | Stage 4: The Crystal Forest; arcade source music credited to Tamayo Kawamoto |
| 1–7, 9, 11–32 | Unlabeled in this cached STIL entry; neither musical purpose nor sound-effect status established |

The header credits Follin for the C64 soundtrack; the STIL credits above distinguish arcade source music from its C64 arrangement. Default selection 1 does not itself prove that entry is the title tune. Stage labels do not establish the complete form or duration of those entries.

In [Stephen Ruddy's first-hand interview](https://www.c64.com/interviews/ruddy.html), the Ghouls discussion identifies his music-driver programming with Tim Follin's design input. This supports game-specific collaboration. It does not identify the exact revision of the pinned HVSC driver or make other Follin platform drivers interchangeable. The receipt pins the cached interview and relevant source lines; the [composer study](../composers/follin-daglish.md#what-the-published-accounts-establish) retains the wider workflow evidence.

## Reproduce the source listening material

The [primary intake spec](../../../config/reference-intake/ghouls-primary.json) renders explicit subtune 1 from initialization for 265 seconds and prepares original excerpts at `[0,16)`, `[120,136)` and `[225,265)` seconds. This spans the observed finite score and leaves a post-stop window; it is not yet a reconstruction or a listener-approved ending. The spec also checks the opening 256 callable CPU entries rather than repeating the already retained 40,000-call form investigation.

```sh
python3 scripts/setup-project.py --only references --include ghouls-n-ghosts
python3 scripts/reference-intake.py run config/reference-intake/ghouls-primary.json --output build/reference-intake/ghouls-primary
```

Open the generated `build/reference-intake/ghouls-primary/listening.md` for the full source WAV and excerpts. The [source receipt](../../../evidence/ghouls-render-intake/sourceA-measure.json) retains the audio fingerprint and settings: libsidplayfp 3.1.1/SIDLite, forced PAL, MOS6581, power-on delay zero, unity gain, 44.1 kHz mono PCM16. All 11,686,500 requested frames were rendered with nonzero AC signal and no PCM rail samples. The [executed run](../../../evidence/ghouls-render-intake/run.json) took 6.56 seconds on 2026-10-13, including 3.08 seconds for rendering. These are source-render measurements, not independent-player verification or a musical judgment. Audio remains local; the checked-in spec and [current executed recipe](../../../evidence/ghouls-render-intake/ending-expanded-recipe.json) preserve reproduction details.

The ending window includes the final musical events before the long quiet tail. The [one-second source profile](../../../evidence/ghouls-render-intake/one-second-profile.json.gz) retains energy at `[231,234)`, `[235,237)` and `[246,247)`, separated by zero-AC intervals; all one-second windows from 247 to 265 seconds have zero AC RMS with a constant PCM16 offset of 157. Active score streams therefore do not imply continuous audible output. Preserve these gaps and compare from 225 seconds when checking the reconstruction; a final silent window alone cannot establish a complete ending. The [expanded-window receipt](../../../evidence/ghouls-render-intake/ending-expanded-window.json) pins this excerpt.

## Contrasting Gauntlet III intake

The [asset registry](../../../config/local-assets.json) pins the [HVSC Gauntlet III source](https://www.hvsc.de/download/C64Music/MUSICIANS/F/Follin_Tim/Gauntlet_III.sid) at `.local/research/gauntlet-iii/Gauntlet_III.sid`: SHA-256 `caec9549f437f6c1a1ee77edc9a034436fb66b2c8ba939adf45b889656c99328`, 6,642 bytes. Its header credits **Tim & Geoff Follin**, 1992 US Gold, with two subtunes, default 1, PAL/MOS6581 and VBI timing. The cached STIL contains no entry for this file. Joint authorship and unknown musical roles remain explicit.

The payload occupies `$AB00–$C473`, overlapping the auditor's default `$C000` host. The [subtune spec](../../../config/reference-intake/follin-subtunes.json) therefore uses the existing explicit host-placement option at `$8000`; source bytes remain unchanged. Both selections pass 256-call CPU audits and initialized 32-second source renders. Their [subtune 1](../../../evidence/gauntlet-render-intake/sourceA-measure.json) and [subtune 2](../../../evidence/gauntlet-render-intake/sourceB-measure.json) receipts retain the hashes, settings and signal checks. These bounded captures do not establish complete form, VICE agreement or shared synthesis mechanisms.

```sh
python3 scripts/setup-project.py --only references --include gauntlet-iii
python3 scripts/reference-intake.py run config/reference-intake/follin-subtunes.json --output build/reference-intake/follin-subtunes
```

The generated `build/reference-intake/follin-subtunes/listening.md` links both sources and an opening comparison: subtune 1 for 16 seconds, half a second of silence, then subtune 2 for 16 seconds. It compares two source selections, not a recreation. The [bounded mechanism contrast](follin-contrast.md) selects subtune 2 and verifies its first 1,604 calls; the onset and pulse diagnostics use passages around 6.4–7.7 and 16–24 seconds. That executed contrast and its subsequent listening verdict complete the bounded [contrasting-reference requirement](../../../PLAN.md#required-contrasting-references-for-the-six-composers): the listener finds the original moving pulse more animated. Rest continuation remains a controlled-edit finding because the selected original contains no rests.

## Callable admission and execution boundary

The unchanged [PSID profile parser](../../../scripts/psid_profile.py) accepts this header with explicit `pal-banked` subtune 1. The initial intake's attempted 64-call audit failed with `Unsupported I/O write at $d41c`, before producing a report or ordered-write ledger. The subsequent [frozen rejection context](../../../evidence/ghouls-sid-window/rejection.json) identifies init PC `$61AC`, `STA $D400,Y`, A=`$08`, Y=`$1C`, at instruction-start cycle 117,661 and before any captured SID store. The requested 64 calls did not complete in that historical run.

The failure was a tool boundary error: the 25 sound-control registers do not exhaust the canonical 32-byte SID write window. The [primary-source receipt](../../../evidence/ghouls-sid-window/semantics.json) establishes that reviewed reSID writes update bus state before dispatching active controls; readback/unused ports are not safely described as inert. The [corrected common contract](../../validation/psid-audit.md#canonical-sid-write-windows) retains every ordinary store in each declared window. Reads, read-modify-write stores and undeclared mirrors remain rejected; no SID bus-state model was added.

On 2026-10-13 the [CPU report](../../../evidence/ghouls-sid-window/audit64.json), [complete ordered ledger](../../../evidence/ghouls-sid-window/audit64.writes.json.gz), [parsed VICE trace](../../../evidence/ghouls-sid-window/vice64/trace.json.gz) and [VICE verification](../../../evidence/ghouls-sid-window/vice64/study.json) establish:

| Scope | Observed result |
| --- | --- |
| Initialization | 119,552 CPU cycles; 58 stores: for Y=`$1C` down through `$00`, write `$08` then `$00` to `$D400+Y` from PCs `$61AC/$61B1`. Eight stores target readback ports `$D419–$D41C`; their order and values are retained. |
| Play calls 0–63 | 329 stores; maximum 2,022 and mean 399.5625 CPU cycles per call, within the 19,656-cycle budget. |
| Independent VICE comparison | All 387 init/play stores match in phase, call, address, value and order. Maximum observed call-cadence error is eight cycles against the nine-cycle polling tolerance. |

The [verification receipt](../../../evidence/ghouls-sid-window/verification.json) pins inputs, tools and all retained records. This proves bounded execution under the controlled raster host, not the original game's environment or selection 1's musical role. The CPU report's register summary covers playback; use its complete ledger for initialization. Monitor timestamps are checkpoints, not exact SID bus-write cycles. Raw monitor/process logs and executable payload files stay local.

## Executed finite stream form

The [source-pinned probe](../../../evidence/ghouls-form/probe.py) uses the shared `pal-banked` auditor, explicit subtune 1 and default host `$C000`, without altering the SID. The [form receipt](../../../evidence/ghouls-form/form.json) retains actual byte-stream navigation, while [provenance](../../../evidence/ghouls-form/provenance.json) separates static native instructions and command tables from observed reads/dispatches. No exact recovered listing for this archive was found in the existing source routes; composer interviews do not settle its byte grammar.

Initialization copies `$2A44→$730E` (**5,083 bytes**) and `$3EAF→$958F` (**1,907 bytes**) using the native `$2999` routine under bank `$35`, before restoring the prior bank. The observed initial stream pointers are `$7338`, `$75F7` and `$77A8`. Their contents are initialized RAM data, rather than a guessed order/pattern format or the file's unchanged loaded bytes at those destinations. All **4,998** consumed stream/operand reads in the full run match the exact original source bytes through these executed copy mappings.

| Navigation task | Actual state / native locus |
| --- | --- |
| Per-voice byte stream | Pointer pairs `$21/$22`, `$23/$24`, `$25/$26`; dispatch reads `$6362`, `$654F`, `$673E`; voice order 0, 1, 2 |
| Command dispatch | Negative bytes index per-voice low/high command tables and patched `JMP` instructions `$6374/$6561/$6750`; nonnegative bytes take the note/rest path |
| Duration and repeat state | Remaining durations `$27–$29`, repeat counters `$2D–$2F`, saved repeat-pointer pairs `$30–$35` |
| Software score calls | Depth bytes `$69–$6B`; `$8A` saves stream return address+3, `$8B` restores it. These are score-stack operations, distinct from the CPU callable return stack |
| Repeat start/end | `$82` loads a count and saves the following stream address; `$81` decrements the count and selects the saved address or the next byte |
| Voice enable / terminal command | Signed enable flags `$7B–$7D`; `$86` selects `$698A/$698F/$6994`, whose `INC` changes that voice's `$FF` flag to zero and skips further stream work |
| Completed callable body | Outer `RTS` `$6857`, SP=`$FD`, saved return word `$C04C` checked against the shared host |

The [256-call instruction window](../../../evidence/ghouls-form/opening.trace.json.gz) independently checks the compact observer. Its [validation](../../../evidence/ghouls-form/opening-validation.json) matches **112** reads, **22** command dispatches, **256** outer returns and all **1,578** ordered init/play stores; its first 64 calls also match the prior 387-store canonical ledger, including instruction-start cycles. The full-span [control checker](../../../evidence/ghouls-form/describe.py) validates **305** observed repeat/call/return/disable transitions against the next consumed address, call depth and repeat counter. Calls and returns balance at 74 each, with maximum observed score-call depth one; this is not a complete independent note/instrument decoder. Command-table entries absent from the run, including `$87`, remain explicitly static/unexecuted in the provenance receipt.

The [40,000-call report](../../../evidence/ghouls-form/full40000/audit.json), [complete ordered ledger](../../../evidence/ghouls-form/full40000/audit.writes.json.gz) and [compact observations](../../../evidence/ghouls-form/full40000/observations.json.gz) cover every requested call **0–39,999**, with **58** init and **140,264** play stores. Maximum play-body cost is **2,915 / 19,656 cycles**. Each voice's final `$8D` waveform command consumes operand zero, then its `$86` terminal command disables that stream:

| Driver voice index | Terminal byte address | Dispatch target | Completed call / enable flags afterward |
| --- | --- | --- | --- |
| 0 | `$75E7` | `$698A` | 12,947 / `[0,$FF,$FF]` |
| 2 | `$798B` | `$6994` | 12,971 / `[0,$FF,0]` |
| 1 | `$77A7` | `$698F` | 12,995 / `[0,0,0]` |

This establishes finite score consumption through call **12,995**, including all three terminal dispatches. No stream event occurs afterward, and the retained named score states stay unchanged. Calls **12,996–39,999** still emit exactly **54,008** stores: `$D415=0`, then `$D416=0`, on each of 27,004 calls. The stopped score therefore retains a callable filter tail; it is not a no-store ending. No recurrence of the initial streams is observed.

Backing audit RAM and CPU snapshots at the fixed pre-RTS boundary match at calls **12,995** and **39,999**. The receipt hashes all 65,536 backing-memory bytes, then those bytes followed by A/X/Y/SP/status/PC-low/PC-high, without normalization or cycle count. This is equality of two sampled audit states, not a one-call fixed-point test, a complete C64 host state, SID oscillator/envelope recurrence or PCM/acoustic silence.

Independent VICE checks all initialization stores plus calls **12,989–13,002**: all **102** ordered stores agree (**58** init, **44** play), including post-stop filter writes. All 13,003 outer play-entry checkpoints stay within **eight** cycles of the PAL grid, inside the nine-cycle polling tolerance. The [projection](../../../evidence/ghouls-form/vice-stop/projection.json), [VICE study](../../../evidence/ghouls-form/vice-stop/trace/study.json) and [parsed trace](../../../evidence/ghouls-form/vice-stop/trace/trace.json.gz) own this bounded machine comparison. It does not establish full-span VICE equality, original-game IRQ behavior, rendered audio or selection 1's musical role.

## Independent score and sound boundaries

The [score probe](../../../scripts/studies/ghouls/score-probe.py) independently expands the initialized score data through all 12,996 calls ending at call 12,995. It matches 4,998 ordered stream reads and every retained named scheduler state, schedules 1,988 positive notes and 785 commands across 18 executed command codes, and verifies all 785 setter effects plus 7,659 scheduler gate writes against fresh native execution. That native execution also matches the existing 86,314-store initialization/play prefix, including instruction-start cycles. The [score receipt](../../../evidence/ghouls-components/score/receipt.json) and [machine-readable grammar](../../../evidence/ghouls-components/score/contract.json) own the precise coverage; `$87`, `$93` and `$94` remain outside the executed contract.

| Score rule | Proven behavior and authoring consequence |
| --- | --- |
| Per-call ordering | Each enabled voice runs continuing sound, decrements duration, processes gate/rest countdowns, then consumes score if duration reached zero. Commands execute in stream order during the same call until a note, rest or disable. Shared filter processing follows all voices. |
| Note duration | A nonzero duration `D` advances again at onset call `N+D`. A zero duration advances after 256 calls because decrement precedes the zero test. |
| Persistent duration override | `$84` with a nonzero operand supplies subsequent durations and omits their duration bytes. Zero restores explicit per-note duration bytes. Treating it as an ordinary one-note field loses stream alignment. |
| Rest versus gate-off | Note byte zero reloads the rest counter without positive-note pitch/onset setup or immediate SID writes. The separate scheduler gate condition still controls release. No zero-note rest occurs in the selected original traversal; this behavior is established by a private bounded intervention. |
| Pulse restart | Waveform commands set current and restart pulse directions; zero pulse defaults select a separate fallback word. Preserve these fields rather than replacing every note with a fixed pulse width. |

The negative duration-plus-one model first reads at call 41 instead of 40; ignoring the persistent override loses grammar. Separate controlled source edits prove rest behavior and zero-duration advancement. The [expanded events](../../../evidence/ghouls-components/score/expanded.json.gz), [native boundaries](../../../evidence/ghouls-components/score/native-boundaries.json.gz) and [setter records](../../../evidence/ghouls-components/score/command-setters.json.gz) preserve the full evidence without original driver code or RAM dumps.

The [sound probe](../../../scripts/studies/ghouls/sound-probe.py) supplies independent numeric helpers for delayed onset restoration, frequency-word motion, note-index alternation/glide, pulse motion, positive-note setup and shared cutoff motion. Each helper receives observed named input state, computes its new state and ordered stores, and compares them with the native routine boundary. All 170,648 contextual boundaries through call 12,995 and 18 isolated parameter checks pass; the fresh native ledger again matches the retained 86,314-store prefix. This is component verification, not yet an independently advancing complete player. The [sound receipt](../../../evidence/ghouls-components/sound/receipt.json), [boundary map](../../../evidence/ghouls-components/sound/boundary-map.json) and [full contextual proofs](../../../evidence/ghouls-components/sound/proofs.json.gz) retain the scope and actual state-changing paths separately from routine visits.

Pitch lookup must retain the actual numeric words: executed indices extend beyond the ordinary pitch-table portion into adjacent data. They cannot all be converted to conventional note names without changing the original behavior. The executed lookup uses 79 indices from 19 through 108, including the adjacent-data mappings `97→8961`, `99→12545`, `102→16385` and `108→26369`.

Pulse phase 1 disables its motion, while phases 0 and 255 admit the two directions; an admitted routine can still have a zero step. Use the boundary map's measured parameter and state changes when choosing a technique, then establish its musical value by listening.

Filter output stores alone do not demonstrate a moving cutoff. Retain three per-voice filter restart phases even though cutoff state is shared; the helper's `reset_direction` is the currently selected owner's phase, and the observed traversal keeps owner 1.

```sh
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 scripts/studies/ghouls/score-probe.py --output build/ghouls-score-new
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 scripts/studies/ghouls/sound-probe.py --output build/ghouls-sound-new
```

These source-specific research commands require fresh output directories and the pinned private source. They automate capture, independent calculations, retained-oracle comparisons and controlled checks. They do not export a production song. The complete numeric integration and [compiled delivery below](#compiled-export-and-complete-listening-package) advance those components together, with matched full renders and a familiar-material transfer. No reconstruction or instrument-reuse listening verdict follows from these component proofs.

## Independently advancing editable player

The [numeric description](../../../songs/ghouls.json) contains 930 symbolic graph nodes, named initial score/sound/filter state and explicit frequency words. [The scheduler](../../../scripts/ghouls_score.py) consumes graph operations using live duration, repeat and call-stack state. [The complete player](../../../scripts/ghouls_player.py) advances continuing sound before score processing for each enabled voice and then advances the shared filter. Runtime imports neither the private SID nor the original CPU, native code or captured event ledger. `sourceEvidence` retains extraction provenance and can be removed without changing playback.

The [complete verification](../../../evidence/ghouls-numeric/receipt.json) matches all **86,442 ordered initialization/play stores** against the original through 13,060 calls. Voice termination remains at calls 12,947, 12,971 and 12,995 in physical voice order 1, 3, 2. All 64 following calls preserve stopped named state while emitting `$D415=0`, then `$D416=0`. The [lossless numeric output](../../../evidence/ghouls-numeric/writes.json.gz) and [store comparison](../../../evidence/ghouls-numeric/ordered-store-comparison.json) retain that full scope. This is independently advancing numeric behavior; compiled CPU/VICE execution, SID internals, audio identity and musical acceptance are separate checks.

The promoted [sound module](../../../scripts/ghouls_programs.py) is also the implementation imported by the research probe, avoiding two maintained copies of its arithmetic. Its [fresh source receipt](../../../evidence/ghouls-numeric/sound/receipt.json) retains 170,648 passing native boundary contexts and 20 controlled checks. The contextual proof, native ledger, audit and boundary-map hashes are unchanged from [the component evidence](../../../evidence/ghouls-components/sound/receipt.json); those large records are reused rather than duplicated. The [expanded controls](../../../evidence/ghouls-numeric/sound/controls.json) add two cases needed when editing full-width filter words:

| Editable boundary | Proven arithmetic |
| --- | --- |
| Downward filter subtraction | Test the high-byte sign for reversal only after low-byte borrow. A negative high byte alone is insufficient. |
| Filter register output | Preserve native high-bit folding: with `lo = word & 255` and `hi = word >> 8`, `$D415 = lo` and `$D416 = ((hi & 7) << 5) | (hi >> 4) | (lo >> 3)`. A conventional eleven-bit shift differs for larger retained words. |

Sound admission validates byte/word fields and supported pulse phases; every accessed lookup index must exist. Same-call score consumption and oscillating filter arithmetic have bounded failure paths. Missing grammar variants fail explicitly: the extracted graph retains observed stream/override contexts, so an edit that changes grammar mode must supply its corresponding variant. Unsupported native opcodes remain outside this description's contract.

```sh
PYTHONPATH=.tools/test-deps python3 scripts/studies/ghouls/prepare-ghouls.py --output build/ghouls-description-new.json
python3 scripts/studies/ghouls/check-ghouls-player.py --output build/ghouls-numeric-new
python3 -m unittest discover -s tests -p ghouls_player_test.py -v
```

Extraction requires the pinned private SID and a fresh output path. Numeric verification requires only the editable description and canonical original ledger; it does not recapture or execute the original. The extractor stays under [study tools](../../../scripts/studies/README.md), while the source-free runtime serves editable compositions. The [full export and listening delivery](#compiled-export-and-complete-listening-package) establish the declared reconstruction scope; the familiar transfer separately tests musical reuse.

## Compiled export and complete listening package

[compose-ghouls.py](../../../scripts/compose-ghouls.py) compiles the editable graph into our [score scheduler](../../../songs/players/ghouls.asm) and [sound routines](../../../songs/players/ghouls-sound.asm). The original SID, driver instructions and captured register schedule are not build inputs. The [public compiler contract](../../workflows/decoded-song-workflow.md#ghouls-variant-graph-player) specifies live grammar variants, bounded score stacks, state restoration and the declared verification range.

| Evidence | Verified scope |
| --- | --- |
| [Complete compiled CPU proof](../../../evidence/ghouls-independent-full/compiled/verification.json) | All 13,060 calls, 86,442 ordered stores and 13,061 named-state boundaries agree with the independent numeric player. Peak play cost is 7,668 cycles against the 19,656-cycle PAL budget. |
| Reinitialization | The final mutated player restores cold state and reproduces all 58 initialization stores and 26 first-call stores. |
| Standalone PRG bootstrap | The actual `SYS 2061` entry restores poisoned mutable state, then runs its first two calls with six cycles of raster jitter under modeled VIC/CIA reads and bank `$37`. This is separate from a VICE autostart. |
| [Complete callable VICE proof](../../../evidence/ghouls-independent-full/vice/study.json) | All 86,442 stores and 13,060 calls agree under the PAL-banked host, with six-cycle maximum cadence error against a nine-cycle tolerance. |
| [Initialized full renders](../../../evidence/ghouls-independent-full/audio.json) | Both WAVs contain all 11,686,500 requested samples at 44.1 kHz mono PCM16, with no clipping and a zero-AC final second. They are not PCM-identical; no musical verdict is inferred. |

The primary payload is 12,691 bytes at `$1000–$4192`, with 930 graph variants and 210 cold-state bytes. The PSID remains callable after its finite score ends, retaining zero shared-filter writes. The standalone PRG runs its declared 13,060 calls and then idles; it does not reset or fade the SID at that boundary.

```sh
python3 scripts/listening-package.py config/listening/ghouls-full.json --output build/ghouls-independent-full
```

The [recipe](../../../config/listening/ghouls-full.json) pins the original, builds and audits the complete independent export, checks the original ledger, runs VICE, renders both versions for 265 seconds and creates original-first opening `[0,16)`, middle `[120,136)` and ending `[225,265)` comparisons. Open the generated `build/ghouls-independent-full/listening.md` for the full files and all three comparisons. The ending deliberately includes the sparse last musical events and their long quiet intervals; it has no added release or fade.

The [initial complete workflow](../../../evidence/ghouls-independent-full/cold-run.json) took 96.39 seconds; the [unchanged repeat](../../../evidence/ghouls-independent-full/cached-run.json) took 0.80 seconds with all ten stages reused and no stage subprocesses. The cold run spent 48.24 seconds compiling and verifying CPU execution, 27.60 seconds in VICE and 7.60 seconds rendering both full WAVs. These retained local measurements demonstrate orchestration/cache savings, not faster original playback or a musical verdict.

The [five controlled edits](../../../evidence/ghouls-numeric/edits/receipt.json) additionally compare complete continuous native/model output after changed notes, durations, repeat counts, gate timing and a rest. All five match the privately edited original execution and differ from the unchanged composition. Four checks cover 224 calls; the repeat needs 944 calls, with its first output difference at call 942. A shorter state-only difference would not prove the repeat's audible-output consequence. The original SID bytes remain unchanged.

```sh
PYTHONPATH=.tools/test-deps python3 scripts/studies/ghouls/check-ghouls-edits.py --output build/ghouls-edits-new
```

The submitted local audition lives in `build/ghouls-listening/`: `reference.wav`, `reconstructed.wav`, `opening-reference-then-ours.ab.wav`, `phrase-reference-then-ours.ab.wav` and `ending-reference-then-ours.ab.wav`. The [submission record](../../../evidence/ghouls-independent-full/listening-review.json) pins those exact files. Recreate a fresh stable folder with the [audition publisher](../../workflows/listening-package.md#preserve-stable-audition-filenames) and [selection](../../../config/listening/ghouls-full.audition.json).

The [familiar transfer card](instruments/ghouls-decoded-programs.md) supplies a separate same-score comparison using selected pulse and staged-onset programs. Its final-release adaptation belongs only to that new arrangement; it does not change the primary reconstruction. The listener accepted the characteristic phrase on 2026-10-13: “I can't hear a difference, nice”; the [scoped verdict](../../../evidence/ghouls-independent-full/phrase-review.json) pins its audio. The complete ending was also accepted: “ref and ours are the same, nice”; its [separate verdict](../../../evidence/ghouls-independent-full/ending-review.json) pins the ending comparison. Familiar-transfer instruments, balance and ending are accepted with a tentative tune reservation. The card's independent compiled-store review matches all 53 source notes and finds shared native tuning about 35 cents sharp; the perception's cause remains unknown.

## Reproduce the form investigation

Install the pinned reference through the setup command below, obtain the retained evidence scripts, and use a fresh working directory. The four research scripts create their outputs exclusively. The opening and full-span probes execute the existing guarded CPU; the control/provenance scripts only inspect retained observations and pinned source data.

```sh
mkdir build/ghouls-form-new
cp evidence/ghouls-form/probe.py evidence/ghouls-form/check-opening.py evidence/ghouls-form/describe.py evidence/ghouls-form/retain.py build/ghouls-form-new/
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 scripts/trace-sid-program.py .local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid --first-call 0 --last-call 255 --profile pal-banked --subtune 1 --output build/ghouls-form-new/opening.trace.json
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 build/ghouls-form-new/probe.py --ticks 256 --output build/ghouls-form-new/opening256
cp build/ghouls-form-new/probe.py build/ghouls-form-new/opening256/probe-executed.py
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 build/ghouls-form-new/check-opening.py
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 build/ghouls-form-new/probe.py --ticks 40000 --output build/ghouls-form-new/full40000
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 build/ghouls-form-new/describe.py
python3 scripts/trace-sid-vice.py .local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid --profile pal-banked --subtune 1 --oracle build/ghouls-form-new/vice-stop/oracle.json --first-call 12989 --last-call 13002 --timeout 180 --output build/ghouls-form-new/vice-stop/trace
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 build/ghouls-form-new/retain.py
```

The [manifest/evidence workflow](../../workflows/build-cache.md) restores historical paths when inspecting the canonical proof instead of repeating execution. The opening executed script is retained separately because the full-run script corrected one space in the hash-recipe text after opening validation; behavior is unchanged. Archive only the four scripts and opening script snapshot, bounded opening trace, validation/form/provenance receipts, both compact observation/ledger sets and reports, and stop-window projection/oracle/parsed trace/study. The original SID, whole payload/RAM image, executable VICE payload/host and raw monitor/process logs stay outside the archive.

Restoration expands gzip files to their original JSON paths. The Ghouls checkers additionally expect the historical `.gz` observation and ledger containers in `opening256/` and `full40000/`; when checking an archived run, copy those canonical containers unchanged into the matching working subdirectories. Do not recompress them: receipts pin their stored bytes. Run checkers only where their exclusively created output files do not yet exist. The fresh-execution recipe above already produces the required layout.

## Reproduce the bounded checks

Acquire the exact linked SID into its private location and verify the SHA-256 above. The [download and evidence guide](../../setup/local-setup.md) owns private reference handling. Use fresh output paths; the inspector and auditor refuse existing output files.

```sh
python3 scripts/setup-project.py --only references --include ghouls-n-ghosts
python3 scripts/sid_intake.py .local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid --subtune 1 --output build/ghouls-sid-window-new/header.json
PYTHONPATH=.tools/test-deps python3 scripts/psid_audit.py .local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid --ticks 64 --profile pal-banked --subtune 1 --output build/ghouls-sid-window-new/audit64.json
python3 scripts/trace-sid-vice.py .local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid --oracle build/ghouls-sid-window-new/audit64.writes.json --profile pal-banked --subtune 1 --first-call 0 --last-call 63 --output build/ghouls-sid-window-new/vice64
```

To check the old failure, [restore the archived records](../../workflows/build-cache.md) and run `python3 build/ghouls-sid-window/reproduce-isolated.py`. The companion pins the original verifier and its dependencies from checkpoint `57b371b`, builds a temporary private root and compares all 12 retained instruction contexts without overwriting historical receipts. It removes the temporary source copy afterward. The direct old verifier intentionally rejects changed dependency hashes; isolation keeps it reproducible as the current profile parser evolves. Do not run the original executed probe against the corrected auditor expecting the old failure. The historical failure recipe makes no additional execution or rendering claim.
