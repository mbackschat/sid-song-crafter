# Workbench usability, effort and resource assessment

Measured on 2026-10-17 against onboarding commit `a5ff295`. The documented CLI works for a bounded raw-MIDI task in fresh Codex and Claude Code sessions. The subsequent real case produced accepted complete single-SID and stereo renditions and records approximately 20 minutes of self-reported human effort. The agreed assessment is complete; comparative effort savings remain unproven. [PLAN.md](../PLAN.md#workbench-value-and-usability-assessment) owns overall status and the [proposal](../proposals/workbench-direction.md) owns the interface/distribution decisions.

## Supported path and observed cost

Both operators received the same task: use the included attributed Bach MIDI, source beats 0–10, and documented configuration templates to create PAL MOS8580 single-SID output. Neither received a prepared score or prior project conversation. They installed fresh project-local dependencies and used no research LFS payload, bridge or audio-model installation. The source import preserved 3,651 notes; the explicit reduction retained 31 of 50 selected notes, recorded 19 omissions and shortened two overlapping durations.

| Observation | Codex | Claude Code |
| --- | ---: | ---: |
| Agent configuration | `gpt-6.1-sol`, xhigh | `sonnet`, xhigh; resolved `claude-sonnet-5-5` |
| First playable, including native CPU/signal checks | 168.5 seconds | 88 seconds |
| Starting shallow clone, including Git metadata | 274.0 MB | 274.0 MB |
| Fresh local tools and downloads, allocated | 32.8 MB | 32.7 MB |
| Generated task output, allocated | 18.4 MB | 18.0 MB |
| First / repeated comparison recipe | Five fresh / five reused stages | Five fresh / five reused stages |
| Exposed monetary cost | Not exposed | $0.55875 CLI list-price estimate |

Figures use decimal MB. These were isolated shallow clones of the committed local repository over file transport; GitHub transfer size/time and a full-history clone were not measured. Existing macOS tools and host authentication remained available. Different interpreters, network/approval events and operator choices prevent interpreting these timings as a model-speed comparison. The first-playable clock excludes cloning. Cost estimates are not confirmed invoices; exact exposed token counters and coordinator-verified hashes are retained in the [verification receipt](../../evidence/workbench-assessment/onboarding-verification.json), alongside the [Codex report](../../evidence/workbench-assessment/codex-onboarding.json) and [Claude Code report](../../evidence/workbench-assessment/claude-onboarding.json).

Both hosts produced the same SID bytes. Complete native checks covered 679 player calls, all 31 note starts, clear gates/volume after stop, zero clipped samples and a silent final half-second. The operators did not install VICE; the [own-score walkthrough](../workflows/own-score.md) was separately verified in the maintainer checkout for PAL/NTSC exports and PAL VICE checkpoints through call 650. No new human musical verdict was requested.

The trials exposed three repairable setup problems: `uv` could select a different installed Python, the renderer guide used a shared temporary download path, and the exporter's five-second connection deadline rejected an observed 6.2-second connection. The documented install commands now select their Python and use project-local downloads. Exporter acquisition now makes at most two bounded attempts and verifies a temporary file before publishing it, so an interrupted download cannot poison the cache. Eight acquisition regressions pass, including partial download, checksum failure and conflicting-file preservation. The anonymous GHCR header remains necessary: a credential-free request returned HTTP 401; the fixed public marker passed re-review and the pinned hash check.

**Interface decision:** retain the repaired CLI, recipes and canonical documentation. These runs show no remaining guidance problem that warrants a new entry skill or plugin. Both hosts also installed and discovered `c64-sid` and `sid-music` in subsequent fresh sessions; this optional check followed the core measurements. The [skill-discovery receipt](../../evidence/workbench-assessment/skill-discovery.json) records pins, extra footprint and the initial Claude probe limitation. Optional integration readiness is separate from successful live emulator connectivity.

## Storage outcome and recovery

| Action | Verified outcome |
| --- | --- |
| Remove unused SongBench/MuQ weights, isolated environment and cache | 2,983 MB of file content removed; 3,105 MB previously allocated. Source/configuration, trial evidence and restoration pins retained. [Receipt](../../evidence/workbench-assessment/ml-removal.json) |
| Existing conservative cleanup | Four duplicate cache WAVs removed and 18 generated text files losslessly compressed; 182.5 MB logical bytes reclaimed. [Receipt](../../evidence/workbench-assessment/build-cleanup.json) |
| Retain and evict intermediate cache audio | 229 paths / 826.2 MB retained as 181 distinct gzip objects / 248.6 MB outside the checkout. [Archive receipt](../../evidence/workbench-assessment/cache-audio-archive.json) |
| Verify preservation | 1,864 protected/listening contents verified, following eight explicit cleanup recovery routes. Exact mono and stereo restoration passed; an affected sample recipe regenerated its stereo export and VICE proof. [Retention check](../../evidence/workbench-assessment/retained-file-verification.json), [round trip](../../evidence/workbench-assessment/archive-roundtrip.json), [regeneration](../../evidence/workbench-assessment/affected-regeneration.json) |

The first pass above reclaimed about 3.74 GB of logical content after its gzip archive. The subsequent complete migration retains all 13,541 then-current build files through three disjoint routes:

| Route | Original files / logical size | Result |
| --- | ---: | --- |
| Protected inputs, deferred work and linked metadata | 3,014 / 1,175.5 MB | Verified gzip snapshot; working files remain regular. |
| Historical WAVs | 822 / 3,333.5 MB | Verified read-only raw archive objects, with old playback paths preserved as links. |
| Other historical intermediates | 9,705 / 1,399.5 MB | Verified gzip archive; working copies evicted. Unknown reuse value is preserved locally. |

The migration also recovered **all 411 pre-existing broken listening-index targets** by their pinned bytes: 402 WAVs and nine metadata files. No historical output was guessed or regenerated. One restored WAV lies inside a recursively fingerprinted recipe input and remains regular; the others use playback links. Identical raw objects share read-only filesystem hardlinks across the listening archives, avoiding another 1,306.6 MB of duplicate objects.

Final verification covered all six data manifests, 10,030 distinct stored object inodes, every current build file, all 335 tracked-document targets and 1,042 unique historical listening-index targets. No links are missing; all 23 literal recipe inputs and their directory descendants remain usable without symlinks. SID, JSON, register-log and WAV restoration passed. The same-root own-score recipe then rebuilt all five stages in 3.95 seconds and reused all five in 0.053 seconds; all seven playback deliverables matched their prior hashes. Its 60 new files / 11.9 MB are classified as regenerable output. [Completion and verification receipt](../../evidence/workbench-assessment/build-retention-completion.json)

The source review retained 112 build-only code files / 3.14 MB as regular files plus external snapshots. They are generated case players, probes, frozen compatibility/debug implementations or third-party research captures; no additional public source promotion is required for the supported workflow. Some prototypes still depend on explicitly deferred untracked helpers. This does not claim that every prototype was independently promoted or superseded.

| Allocated storage | Before complete migration | After complete migration |
| --- | ---: | ---: |
| Maintainer checkout | 7.19 GB | **2.55 GB** |
| Included build directory | 5.94 GB | **1.25 GB** |
| Separate local archive | 0.25 GB | **3.93 GB** |
| Checkout plus archive | 7.44 GB | **6.48 GB** |

These decimal-GB measurements distinguish relocation from reclamation: the complete migration reduced combined allocated content by about 0.95 GB, including recovery of older missing targets. Raw-object hardlinks are counted once in the archive total. Filesystem snapshots and other activity can make volume free-space changes differ. [Measured footprint](../../evidence/workbench-assessment/footprint.json)

At the historical migration checkpoint, the archive at `~/Archives/sid-song-crafter/` had a readable README, `catalog.json`, six data manifests and compressed audit records. That catalog mapped 14,106 historical paths to their latest manifest and exact fingerprints, including older cache history. It avoids accidentally restoring an obsolete version of the two regenerated own-score indexes. The [archive tool](../../scripts/archive-build.py) restores selected bytes without overwriting different content; [recovery commands and playback-link precautions](../workflows/build-cache.md#external-local-build-archives) describe its contract. No bulk audio was added to Git.

The later user-requested [archive relocation](../../evidence/workbench-assessment/archive-relocation.json) brought the complete archive into ignored `.local/archives/sid-song-crafter-history/` and repaired its playback links. The table above remains a historical measurement; its separate archive is now part of the project folder, with no new Git payload or disk-space saving from relocation.

The inventoried historical build state is now recoverable. The remaining regular files are convenient working copies of protected inputs, metadata and deferred work; deleting them would require restoration before dependent workflows run. This is not a promise that every file can be regenerated from Git, or that future unarchived work is disposable. The project-local archive is local retention, not an off-machine backup.

For distribution, the README clone command skips the existing compressed research evidence: 539 LFS paths, 174.3 MB checked-out content / 172.2 MB distinct objects. They remain available through [explicit study acquisition](../workflows/build-cache.md#persistent-evidence). Included sample files and small evidence receipts stay in ordinary Git. No new research package, submodule, history rewrite or upload was performed.

The inventory also found two manifest-listed Daglish test logs hidden from Git by a global `*.log` rule. The repository now exempts canonical evidence logs at every nesting level; both receipts are tracked and match their original hashes. A regression verifies this boundary while keeping generated/private logs ignored.

## Real-case composition effort

At the user's request, the coordinator selected a complete source-backed piece and opened a prospective ledger. The initial Bach Invention No. 8 intake was set aside when the user required a modest instrumental ensemble: good on one SID, with a useful musical benefit from two. Mozart's Minuet and Trio from K. 525 supplied four source roles. The [owning case and ledger](../../songs/mozart-minuet/README.md) retain the source, decisions, failures, exact feedback and reproduction recipe; the [measurement receipt](../../evidence/mozart-minuet/verification.json) pins the outputs and timings.

| Observation | Measured result |
| --- | --- |
| First verified playable SID/PRG observed | 15m38s after the first recorded clock; initial reading before that clock was not timed |
| Complete technical package | 21m17s elapsed, including the abandoned selection, source intake, manual reduction, sound selection, packing correction and PAL/NTSC mono/stereo execution checks |
| Human musical result | Complete PAL single-SID and stereo renditions accepted; stereo Trio adds useful richness and space; ending accepted. Full stereo acceptance was recorded 29m13s after the first measured clock. |
| Human active time | Approximately **20 minutes**, self-reported for guidance, listening and replies. The coordinator selected the piece, guided by user input. No activity-level breakdown is available. |
| Monetary cost | Coding-agent cost not exposed; no paid audio-model request |
| New installations | None; existing MIDI/native/renderer/VICE tools reused |
| New case-specific work | Source/form intake, explicit mono/stereo allocation and note accounting, small preparation/listening scripts, palettes and recipe |
| Main technical friction | Tick-grid native pattern capacity; a declared 1.005% tempo reduction and eight-beat packing retained every selected note and the full form |
| Pipeline recovery | Input fingerprint checks caught a concurrent source-document change; exact dependency declarations removed that invalidation, and completed native stages were reused |

The source MIDI omitted all repeats and the da-capo return; following the score increased the performed form from 108 to 264 beats. The mono version retains melody and bass, switching the inner role by section. The stereo version restores the complementary source part and duplicates melody/bass for center placement. This required manual six-voice preparation, consistent with the supported workflow; the generic three-voice importer did not become an automatic orchestrator.

Existing repertoire, source-reading guidance, export backends, full-schedule verification and recipe caching materially supplied the implementation. The human verdict establishes usefulness for this particular interpretation. No comparable unaided or alternative-tool task was measured, so **total composition-effort savings remain unproven**. Keep the README's concrete capability/reuse claims and avoid a productivity percentage or speed claim.

The interface recommendation remains **CLI tools, editable recipes and task-oriented documentation for an agent-assisted musician/developer**, supported in Codex and Claude Code. A new entry skill would not remove the observed source-form and voice-allocation work or native capacity limit. Existing SID skills remain optional background aids with project corrections; the measured work provides no reason to restore unused ML installations or expand model-based musical judging.

## Closure

All four musical verdicts are recorded. The human estimate is separate from overlapping agent/tool elapsed time; 21m17s measures the technical package, not the full case. Retention, documentation and final verification continued after acceptance, with the final observation recorded in the [case receipt](../../evidence/mozart-minuet/verification.json). No agent active-time or monetary total can be inferred from these clocks.

The [case retention receipt](../../evidence/mozart-minuet/retention.json) verifies 56 archived paths: 24 WAV paths remain playable through links, and 32 generated traces are losslessly archived. These replace 439.4 MB of working content with 169.9 MB of external objects, reclaiming 269.5 MB of logical content before metadata. All seven submitted auditions and eight public SID/PRG files match their fingerprints. The external catalog now contains eight manifests and 14,162 recovery routes. Public playable exports total only 68,822 bytes; the new source/recipes and small receipts also belong in Git. No bulk audio is added.

The [overall plan](../PLAN.md#workbench-value-and-usability-assessment) closes V4 and V5. Keep the repaired CLI/recipe/documentation entry point, existing optional C64 skills and human musical authority. No additional musical experiment, new entry skill, audio-model trial or controlled human pilot is queued. A comparative study remains deferred until a second independent operator exists; this assessment makes no productivity claim.

### Subsequent sample-distribution change, 2026-10-17

After assessment closure, the user requested direct README links to single-SID and stereo SID/WAV samples in the repository. The [Mozart package](../../samples/mozart-minuet/README.md) now includes its two accepted PAL WAVs (38,731,654 bytes), verified against the original listening fingerprints. The clone measurements above predate this addition. Historical/intermediate audio remains local; this change does not add it to Git or change the listening verdicts. README distinguishes included downloads from rights-unresolved local builds and missing variants.
