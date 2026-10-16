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

The three operations reclaim about **3.74 GB of logical content after allowing for archived gzip objects**, before small manifests, restored test files and new verification outputs. Relocation alone is not reclamation or backup. Actual volume free space can differ because of filesystem allocation, snapshots and other activity.

The private archive is at `~/Archives/sid-song-crafter/2026-10-17-cache-audio/manifest.json`. The [archive tool](../../scripts/archive-build.py) restores an exact indexed path without overwriting different content; [commands and interruption recovery](../workflows/build-cache.md#external-local-build-archives) describe the contract. No audio from this archive was added to Git. The file-level classification remains in `.local/workbench-retention/inventory.json`, fingerprinted by the [compact inventory receipt](../../evidence/workbench-assessment/retention-inventory.json).

The post-pass maintainer checkout still occupies **7.19 GB allocated**, including **5.94 GB in build/**. Current listening paths, accepted deliveries, pinned inputs, deferred experiments and unclassified content remain in place. The pre-pass inventory included 2.41 GB of unclassified files; the cache selection removes some of that category, but does not establish that the remainder is disposable. **Deleting all of build/ is still unsafe.** Further reduction needs explicit recovery and current-link handling for these retained exceptions. [Measured footprint](../../evidence/workbench-assessment/footprint.json)

For distribution, the README clone command skips the existing compressed research evidence: 539 LFS paths, 174.3 MB checked-out content / 172.2 MB distinct objects. They remain available through [explicit study acquisition](../workflows/build-cache.md#persistent-evidence). Included sample files and small evidence receipts stay in ordinary Git. No new research package, submodule, history rewrite or upload was performed.

The inventory also found two manifest-listed Daglish test logs hidden from Git by a global `*.log` rule. The repository now exempts canonical evidence logs at every nesting level; both receipts are tracked and match their original hashes. A regression verifies this boundary while keeping generated/private logs ignored.

## Next evidence needed

Use the [effort ledger](../workflows/effort-ledger.md) at the next authorized real musical case, including human decisions, failed revisions, troubleshooting and retention through complete acceptance. No case has been opened solely for this measurement. Continue retention work from the recorded exceptions instead of treating the successful cache pass as permission to wipe the build directory. Neither activity requires a new skill collection, audio-model trial or controlled human pilot.
