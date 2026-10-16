# Workbench onboarding and resource assessment

Measured on 2026-10-17 against onboarding commit `a5ff295`. The documented CLI works for a bounded raw-MIDI task in fresh Codex and Claude Code sessions. This is an onboarding result; total effort to reach an accepted complete musical rendition remains unmeasured. [PLAN.md](../../PLAN.md#workbench-value-and-usability-assessment) owns remaining work and the [proposal](../proposals/workbench-direction.md) owns the interface/distribution decisions.

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

The archive is at `~/Archives/sid-song-crafter/`, with a readable README, `catalog.json`, six data manifests and compressed audit records. The catalog maps 14,106 historical paths to their latest manifest and exact fingerprints, including older cache history. It avoids accidentally restoring an obsolete version of the two regenerated own-score indexes. The [archive tool](../../scripts/archive-build.py) restores selected bytes without overwriting different content; [recovery commands and playback-link precautions](../workflows/build-cache.md#external-local-build-archives) describe its contract. No bulk audio was added to Git.

The inventoried historical build state is now recoverable. The remaining regular files are convenient working copies of protected inputs, metadata and deferred work; deleting them would require restoration before dependent workflows run. This is not a promise that every file can be regenerated from Git, or that future unarchived work is disposable. The external archive is local retention, not an off-machine backup.

For distribution, the README clone command skips the existing compressed research evidence: 539 LFS paths, 174.3 MB checked-out content / 172.2 MB distinct objects. They remain available through [explicit study acquisition](../workflows/build-cache.md#persistent-evidence). Included sample files and small evidence receipts stay in ordinary Git. No new research package, submodule, history rewrite or upload was performed.

The inventory also found two manifest-listed Daglish test logs hidden from Git by a global `*.log` rule. The repository now exempts canonical evidence logs at every nesting level; both receipts are tracked and match their original hashes. A regression verifies this boundary while keeping generated/private logs ignored.

## Next evidence needed

Use the [effort ledger](../workflows/effort-ledger.md) at the next authorized real musical case, including human decisions, failed revisions, troubleshooting and retention through complete acceptance. No case has been opened solely for this measurement. The authorized retention and onboarding work is complete. Keep the archive and apply its retention contract to future outputs. The remaining real-case measurement requires no new skill collection, audio-model trial or controlled human pilot.
