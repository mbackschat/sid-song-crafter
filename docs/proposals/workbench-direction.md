# SID Song Crafter: product interface, value and resource discipline

Status: agreed direction, implementation started 2026-10-17, incorporating external review and the user's storage/distribution clarifications. The evidence supports design choices, not a measured productivity advantage. [PLAN.md](../../PLAN.md) owns execution order and completion; finalizing this document does not claim implementation is complete.

Repository: [mbackschat/sid-song-crafter](https://github.com/mbackschat/sid-song-crafter). Relative links resolve from this document in the repository. Storage measurements describe the maintainer's local checkout.

## Implementation decisions

1. **Improve option A now; defer building an entry skill.** Make the existing CLI/documented workflow usable without maintainer context: portable configuration templates for both hosts, readiness checks scoped to the selected workflow, and one own-score MIDI-to-SID walkthrough. These are required before comparing A with a skill. **Rationale:** a skill should solve remaining workflow friction, not compensate for avoidable documentation and setup defects. Alternative: build B immediately; reject this because it would make the comparison unfair and may add unnecessary maintenance.
2. **Measure the next real musical case and run a fresh-agent walkthrough on each host.** Use a prospective effort ledger and cold-clone own-score tasks in Codex and Claude Code. Defer a controlled human comparison until a second independent operator is available; exclude a tracker/editor comparison from this assessment. **Rationale:** this fits the currently available person and produces useful cost and usability evidence without four extra listening cycles. It leaves comparative savings unproven. Alternative: staff the original pilot now; no second operator or independent listener has been arranged.
3. **Remove the unused SongBench/MuQ installation and its disposable package cache.** Retain pinned restoration metadata, source/license material and trial evidence; check shared cache use before removing it. **Rationale:** these installations occupy about 2.89 GiB and have no demonstrated normal-workflow role. Alternative: keep them ready for speculative trials; that conflicts with reducing waste. Normal song builds must still pass after removal.
4. **Separate disposable builds, local retention and material distributed to users.** Make `build/` disposable only after verified retention and recovery. Keep core tools, recipes, concise findings and a small curated sample set in the main repository; provide substantial shareable research material as optional versioned downloads with checksums; retain private references and listening history outside the checkout. **Rationale:** research value does not imply every cloner needs the bytes. The roughly 2 GB retention candidate is not a Git addition or a required installation. Prefer optional downloads over a new submodule; use LFS where appropriate for versioned binaries, with explicit download behavior.
5. **Replace repeated model-review skip records with one standing decision per case and event-driven reassessment.** Keep human acceptance, controls and request authorization unchanged. **Rationale:** documenting the same decision after every revision consumes effort without new evidence. Alternative: retain the current checkpoint policy if reviewers identify a concrete missed-risk benefit worth that cost.

Decision 5 replaces an explicit rule. [CLAUDE.md](../../CLAUDE.md#listening-and-retained-findings) previously required following the measured trials and recorded reviews “at each [model-assistance checkpoint](../research/audio-assessment.md#use-and-reassess-model-assistance).” The former owning rule said:

> Review usefulness **at the first representative audition, after listener feedback or a musical revision, and before closing each musical case**.

It also required a dated run or explicit skip at every checkpoint. The selected replacement records eligibility and rationale once when a case opens, reassesses when a concrete useful question, relevant model/prompt/preprocessing change or explicit user request occurs, and checks the standing decision at closure without repeating unchanged skip prose. The owning policy, contributor guide and workflow references now implement this replacement; historical trial records remain intact. Execution status belongs in [PLAN.md](../../PLAN.md).

## User input and constraints

The following restates the user's input and accepted direction. Detailed historical musical verdicts remain in their owning studies.

| Input | Requirement retained in this proposal |
| --- | --- |
| Measuring whether the workbench reduces total composition effort is now important. | Assess the project's actual value claim, including all work needed to reach an accepted result. Successful builds, fast rendering and accepted songs alone do not establish effort savings. |
| How would other people use the project: tools, scripts or agent skills? | Define a concrete newcomer workflow and compare public interfaces rather than assuming the maintainer's accumulated context transfers to others. |
| Evaluate and decide which skills, tools and models are relevant. | Give components an explicit role, evidence and retention decision; avoid keeping machinery merely because it was investigated or installed. |
| Get rid of waste; the project folder exceeding 6 GB is excessive. | Measure and reduce local footprint, including generated files, dependencies and research installations; preserve useful music, sources and reproducibility. Do not dismiss the complaint because much of the data is ignored by Git. |
| The primary supported user is an agent-assisted musician/developer. | The person supplies musical intent and listening judgments; an agent assists with source intake, arrangement configuration, research and execution. Neither an autonomous musical judge nor a GUI-only novice is the initial persona. |
| Support Codex and Claude Code. | Both are selected initial agent environments. Share the underlying workflow and tools, but verify discovery, activation and dependency behavior separately for each host. |
| The original idea was an agent skill set, but that is now uncertain; consider the current project name. | Treat SID Song Crafter as the product identity. Skill packaging remains a design choice, not a foregone conclusion or a reason to rename the product. |
| The project already uses C64 skills, so a single skill would require dependencies. | Account for existing upstream skills, their installation, discovery, corrections and availability. Distinguish one new entry skill from one self-contained deliverable and from a multi-skill installation. |
| Double-check the facts, ask about ambiguity and provide a Markdown proposal for external review. | Present current evidence, alternatives, recommendations and rationale; preserve unresolved choices rather than silently settling them. No external reviewer is contacted by this work. |
| The overall study plan must become root PLAN.md, the only source for “what remains?”. | Keep task status in [PLAN.md](../../PLAN.md). This proposal records a decision basis, not a competing backlog or completion claim. |
| Several GB of historical audio must not burden GitHub cloners. | Keep local retention separate from the default download. A local archive is not an instruction to add its contents to Git. |
| Split existing build material into disposable, valuable untracked and valuable tracked destinations. | Verify regeneration before deleting; retain private/local material outside the checkout; promote only missing reusable public material to appropriate repository directories, never track `build/` itself. |
| Does every user need retained research, and would submodules or LFS help? | Distinguish core users from researchers. Prefer optional versioned study downloads; a submodule is conditional on independent maintenance, and LFS alone does not make a download optional. |
| Wrap up the proposal so implementation can begin. | Close the design discussion with this agreed direction and executable completion criteria in PLAN.md. |

Earlier requirements remain in force: interpret attributed existing scores; support MOS6581/MOS8580 and stereo; retain organized mono/stereo SID/WAV samples with their materials. The [sample library](../../samples/README.md) owns the user's intro-trimming requirements, accepted versions and publication limits. Musical acceptance depends on role, phrasing and context, as the [Axel F verdicts](../../songs/axel-f/arrangement-review.md) demonstrate. Their detailed listening history stays with those owners.

The user's earlier approval of a specific four-clip OpenRouter/Qwen trial does not authorize new uploads. The [retained trial](../research/audio-assessment.md#axel-f-descriptive-follow-up-silence-failure) owns its selection, controls and silence failure; model observations remain experimental supporting evidence.

## Baseline audit and required repairs

| Pre-implementation finding (2026-10-16) | Required consequence for option A | Evidence |
| --- | --- | --- |
| The product is a CLI toolkit and reference library for interpreting scores. README states a reuse aim, but makes no measured or quantified productivity claim. | Preserve that factual description; distinguish measured production cost from savings. | [Product purpose](../../PRODUCTS.md), [README](../../README.md) |
| Bach starts from an existing arrangement. The generic MIDI preparer requires explicit import, part/span and reduction choices and produces exactly three voices. | Provide a complete own-score walkthrough from MIDI, including those configurations, sounds, build commands and outputs. The agent must be able to follow it without the maintainer's chat history. | [Preparer](../../scripts/prepare-score-audition.py), [score workflow](../workflows/song-workflow.md) |
| Both bridge examples contain maintainer-specific absolute paths. The bridge is optional. | Provide portable templates with explicit machine-local values for Codex and Claude Code; normal composition must not require bridge configuration. | [Codex configuration](../../config/codex.toml), [Claude configuration](../../config/claude-mcp.json) |
| Doctor checks the full environment, including VICE, while the demo needs less. | Offer readiness checks for shipped-sample listening, demo builds, full verified score work and optional integrations. Missing dependencies must identify the affected workflow. | [Doctor](../../scripts/doctor.py), [local setup](../setup/local-setup.md) |
| Setup pins upstream skills; `c64-sid` is default and `sid-music` optional. `.claude/skills` links to `.agents/skills`; local discovery has been checked in both hosts. | Preserve shared activation and corrections. Fresh-clone verification must check installation/discovery, not merely reuse this working checkout. | [Skills](../../skills/README.md), [setup evidence](../setup/local-setup.md#unified-local-setup), [corrections](../setup/skill-guidance.md) |
| Native export supports three/six voices, both chip models and explicit PAL/NTSC. A recipe runner already handles commands, fingerprints, caches and receipts. | Use these existing tools; retain their target and verification contracts beneath any later agent interface. | [Native workflow](../workflows/native-song-workflow.md), [recipe runner](../workflows/listening-package.md) |

The three repairs are now implemented and both-host onboarding results are recorded in the [assessment](../validation/workbench-assessment.md); the table preserves the decision’s original basis. The three baseline repairs in decision 1 are prerequisites, not optional improvements to be judged against a better-prepared skill. Their exact implementation and test tasks belong in [PLAN.md](../../PLAN.md). Keep the [SID Song Explorer proposal](web-player-and-analyser.md) separate; its playback/analysis application is not a dependency of this assessment.

## Can skills depend on skills?

There are three different mechanisms. Their distinction changes the packaging recommendation.

| Mechanism | Verified support | Consequence for Crafter |
| --- | --- | --- |
| Instructions referring to another skill or resource | Skill bodies can describe workflows and link supporting resources. This is agent guidance; it does not itself install a missing skill, resolve a version or prove the agent loaded it. | One entry skill can coordinate existing knowledge only if setup and the workflow check its required resources explicitly. |
| Portable skill dependency declaration | The Agent Skills specification lists compatibility text and arbitrary metadata, but no standardized skill dependency resolver. Codex's documented `agents/openai.yaml` dependency validation supports `dependencies.tools`; it is not a skill package manager. | Do not claim that a hypothetical `depends_on: c64-sid` field provides portable installation or enforcement. [Agent Skills specification](https://agentskills.io/specification), [OpenAI validation reference](https://developers.openai.com/plugins/deploy/submission-errors). |
| Plugin packaging and host-managed dependencies | OpenAI documents packaging multiple skills and MCP configuration together. Claude Code separately documents plugin dependencies with version constraints, including dependencies supplying skills. | A multi-skill plugin is feasible; Claude's plugin dependency mechanism must not be presented as a cross-host skill dependency standard. [OpenAI packaging](https://developers.openai.com/plugins/build/plugins), [Claude Code dependencies](https://code.claude.com/docs/en/plugins/dependencies). |

These official pages were checked on 2026-10-16; no plugin-dependency installation experiment was performed. Using Claude Code's dependency mechanism requires suitable upstream plugins and compatible releases; the presence of an upstream `SKILL.md` alone does not establish that packaging.

**Recommendation:** keep pinned project setup as the dependency boundary for A. If remaining friction warrants B, its entry skill uses the same installed supporting skills, corrections and canonical tools. A later plugin must respect upstream redistribution terms and test each host's installation behavior.

## Interface alternatives

| Option | Benefit and limitation | Recommendation and rationale |
| --- | --- | --- |
| A. Documented CLI/recipes with existing supporting skills | Smallest supported surface; requires a complete own-score path and useful setup diagnostics. | Improve now. It may meet the user need without another skill. |
| B. One composition entry skill alongside supporting skills | Discoverable agent workflow; adds instruction/dependency maintenance and can duplicate documentation. | Defer until repaired A's walkthrough exposes a specific guidance gap. Compare using equivalent content and tools. One entry skill still means multiple installed components. |
| C. Several composition, sound-design, analysis and playback skills | Independent invocation can help distinct tasks; overlapping triggers and contracts increase cost. | Defer until observed tasks justify separate boundaries. |
| D. Plugin bundling selected skills/integrations | Convenient installation and namespaces; host-specific manifests, versioning and licensing remain. | Consider if installation/discovery is the demonstrated problem. This packages A/B/C rather than replacing the workbench. |
| E. One self-contained skill with copied tools/reference material | Single bundle, but duplicate ownership and stale copies; executable prerequisites remain. | Reject initially. Reuse the repository's authoritative implementation and knowledge. |
| F. GUI or new MCP service | Could support interactive editing or clients without shell access; substantially enlarges scope. | Exclude here. Keep Explorer's independent proposal intact. |

## Public workflow and contract

**New-score input is MIDI.** The person supplies attribution, musical intent, declared form/ending, target model/count/clock and a reference where available. PDF notation needs transcription or a corresponding MIDI. Existing project JSON arrangements and SWM/SWS modules remain editable through their documented specialist workflows; this proposal does not promise arbitrary score-format import.

The agent prepares explicit source-part selection and reduction, retrieves appropriate sounds, creates editable configuration and runs the existing listening recipe. It asks about consequential missing musical choices and presents a small, labelled comparison when listening is needed. The person controls intent and acceptance; routine tool operation does not require repeated confirmation.

**Dual SID for a new score requires manual six-voice authoring** by the person or assisting agent after source intake; the generic MIDI preparer produces three voices. Record musical role → chip/voice → coupling/filter ownership → output matrix. Each chip has a mono output and shared processing, not per-voice pan. Retain MOS6581/MOS8580 and PAL/NTSC within the [native contract](../workflows/native-song-workflow.md); current dual exports use the same model on both chips. Mixed-model chips and automatic arbitrary six-voice reduction are outside the promised workflow.

Required outputs are preserved source/provenance, editable arrangement/instrument recipes, disclosed omissions/adaptations, playable SID/PRG, technical receipts and a reproducible listening package containing a phrase, ending and full WAV. SID-Wizard uses SWM/SWS; specialist backends retain equivalent editable score/program source. Listening decides musical success. Audio models and a live bridge are optional, and WAV alone is insufficient reusable source.

## Components to retain

| Component | Recommendation and rationale |
| --- | --- |
| Native export, renderer, score tools, CPU/VICE checks, comparisons and recipe runner | Keep for their supported stages; they already deliver verified outputs. |
| Repertoire, source provenance, technique index and accepted/rejected examples | Keep with selective retrieval; these contain the musical knowledge whose practical value is being assessed. |
| `c64-sid` | Keep pinned and available with corrections. Determine default necessity from use; native compilation does not depend on its Markdown. |
| `sid-music` and live c64bridge | Keep optional. Preserve the assembler source used by alternative Bun builds separately from live-server dependencies. |
| Specialist decoded backends and study programs | Keep outside the newcomer default path. Shared imports and frozen evidence make deletion by filename unsafe. |
| Coding/reasoning agent | Use for intake, source reading, configuration and verified execution. Record model/settings; tier assignments are not measured cost/quality rankings. |
| Hosted audio models and local SongBench/MuQ | Keep research evidence and bounded runners; no normal-path musical authority or automatic requests. The [recorded trials](../research/audio-assessment.md) contain both scoped successes and failures. Remove unused local ML installation under decision 3. |

## Affordable evaluation

**Next real case:** keep a prospective ledger of human active time, agent/tool time and exposed cost, setup, revisions/failures, and time to first playable and accepted complete output. Include troubleshooting and retention work. Use existing receipts where possible. Missing historical effort cannot be reconstructed from commit or render timings. Detailed logging fields belong in the execution plan, not a new metrics subsystem.

**Cold-clone walkthroughs:** after repairing A, give a fresh agent on each selected host the repository and the same attributed MIDI task absent a prepared arrangement. Use an isolated clone with no inherited project caches or conversation; declare preinstalled system tools and agent authentication prerequisites without recording secrets. Record setup requirements, interventions, failures, total time to first playable SID, and installation/output footprint. Do not create a worktree. Verify output through the existing technical checks; a successful agent run is an onboarding proxy, not human musical acceptance or a complete productivity study. These tasks require no additional full-song listening rounds.

The currently established staffing is one maintainer/listener; no second independent human is arranged. Defer the controlled pilot until that changes. A tracker/editor comparator is outside scope. README should continue describing demonstrated capabilities and the reuse aim without claiming measured productivity savings. The outcome of this assessment can be “usable workflow with recorded costs; comparative savings unproven.”

Only consider B if these walkthroughs leave a specific guidance problem that a skill addresses. Preserve the same underlying documentation, repertoire and tools when evaluating its added value. Fixing A may settle the interface decision without a comparison experiment.

## Storage and retention

### Distribution contract

No files under `build/`, `.local/` or `.tools/` are currently tracked. Cloning does not download this working history, and ordinary setup does not reproduce it. New builds create output only for the selected task. The three build categories are destinations to establish, not an already completed classification:

| Category | Content and audience | Destination and default download |
| --- | --- | --- |
| Disposable | Verified regenerable intermediates, caches and redundant copies | `build/`; excluded from Git and removable after verification. |
| Valuable, untracked | Selected private references, accepted audio and useful listening history for follow-up work | A local archive outside the checkout, with an index and restoration paths; excluded from public downloads. |
| Valuable, distributed | Missing reusable tools, editable recipes, findings, provenance and appropriate evidence for other users | Core material goes into existing repository directories; substantial research-only material becomes an optional package where redistribution permits. Existing tracked copies are reused. |

Core distribution includes documented tools, reusable instruments/recipes, concise knowledge/provenance, compact necessary evidence and a small curated sample set. Optional study packages are versioned and checksum-verified, identified by study and size, and downloaded only when selected. Normal setup and the own-score walkthrough must work without the research archive. Unavailable optional material must affect only the task that needs it, with a clear acquisition or regeneration route. Preserve current published sample promises; changing their distribution requires updating their working download/reproduction links.

| Storage mechanism | Decision and rationale |
| --- | --- |
| Ordinary Git | Keep small, broadly reusable source and knowledge here. Do not add the bulk listening archive. |
| Optional downloadable study packages | Preferred for substantial shareable research evidence/audio: explicit choice without adding another repository workflow. Keep manifests, attribution, checksums and owning documentation discoverable from the main project. |
| Git submodule | Defer unless the collection needs independent development/version history. It pins another repository, which users can leave uninitialized, but adds management complexity. [Git submodules](https://git-scm.com/docs/gitsubmodules). |
| Git LFS | Already used for compressed evidence. It separates binary objects from ordinary Git history, but configured checkouts normally fetch their contents unless filtered or skipped. It is not, by itself, an optional-download boundary. [LFS download behavior](https://raw.githubusercontent.com/git-lfs/git-lfs/main/docs/man/git-lfs-smudge.adoc). |
| Local external archive | Use for private or maintainer-specific material with no general distribution need. Moving bytes here reduces checkout size but does not reclaim disk space or create a backup. |

Review existing evidence/LFS and sample dependencies as well as possible new promotions: a default workflow must not silently fetch the optional study collection. Preserve published evidence identity and access while changing acquisition routes. No history rewrite, repository split, submodule creation, release upload or push is authorized merely by selecting this contract.

### Measured footprint and classification limits

A fresh 2026-10-16 `du -sk` check confirms approximately **10.44 GiB** for the checkout, including **6.41 GiB in `build/`**, **2.06 GiB in `.local/`**, **1.39 GiB in `.tools/`**, **0.19 GiB in evidence**, **0.13 GiB in samples** and **0.24 GiB in `.git/`**. These are allocated directory sizes, not download sizes. The earlier tracked working-file inventory was 338.84 MiB logical; measure fresh installation separately in the walkthroughs.

The build scan found **1,100 WAV files, 4.66 GiB allocated**. Of 514 immediate build directories, 501 contain less than 100 decimal MB of allocated file data each and total 4.30 GiB. This confirms the reviewer's long-tail diagnosis, although its 607/596 directory counts were not reproduced. Total WAV size alone does not establish which files are disposable.

| Removal selected by decision 3 | Allocated KiB | GiB | Retention boundary |
| --- | ---: | ---: | --- |
| MuQ directory | 1,302,568 | 1.242 | Remove weights; retain small configuration and restoration metadata. |
| SongBench checkpoints | 98,448 | 0.094 | Preserve fingerprints, source/license and trial evidence. |
| `.tools/songbench-venv` | 851,684 | 0.812 | Recreate from recorded packages if a new justified trial needs it. |
| `.local/uv-cache` | 779,380 | 0.743 | Disposable download/install cache; check shared use and active writers first. |
| Total | 3,032,080 | 2.892 | Directory accounting, not a promise of identical physical free-space recovery. |

The review's approximate 0.85/0.78 figures for the environment/cache are not GiB under this measurement; the table uses one consistent unit. [Restoration instructions and pins](../setup/local-setup.md#optional-local-audio-models) already exist. The separate 0.29 GiB bridge `node_modules` remains optional later cleanup, conditional on preserving the alternative assembler path and documenting live-server reinstallation.

A bounded content-hash scan on 2026-10-16 found the following candidates. Figures below use decimal MB and count exact file-content duplicates once in the distinct-content column; they are not a complete value classification.

| Selection | Distinct content | Current copies in build | Interpretation |
| --- | ---: | ---: | --- |
| Files matching hashes from 56 review/delivery records | 1,114 MB | 2,241 MB | Directly evidenced review/delivery content; about 60 MB already has an identical tracked copy elsewhere. |
| Broader listening/delivery collection, including the first row | 2,020 MB | 3,362 MB | Conservative retention candidate, not an indispensable archive; about 69 MB already matches tracked content elsewhere. |
| Files outside the broader selection | Not deduplicated for this row | 3,490 MB | Still unclassified; not automatically disposable. |

The scan matched build-file hashes against tracked song/sample review and selected-delivery records, then included files in listening-named paths and the selected Axel F delivery. This explains the selection's limits: it captures recorded evidence and listening locations, not every reusable source or every unsubmitted experiment. **No additional build artifacts have been selected for Git promotion, and their eventual size is unknown.** The 69 MB of existing tracked matches requires no new Git storage. Private audio remains private regardless of its usefulness.

**Retention contract:** preserve accepted final/native deliveries, essential references, editable source/recipes, provenance, canonical evidence and comparisons needed to substantiate reusable findings. Other listening history can be archived locally; every submitted clip need not become permanent core content. During classification, existing reviewed files and deferred work remain protected. Retiring a redundant or regenerable audition requires a recorded reason, recoverable inputs and a working retrieval/restoration route for affected listening links. Frozen provenance and unique evidence must remain intact.

For every retained item, record its case, role, hash, destination, publication status and reproduction/restoration route. Confirm a retained copy before removing an original. Verify representative regeneration with the pinned inputs and tools; a recipe filename alone is insufficient. Promote only missing useful source/knowledge or appropriate evidence, reuse existing tracked copies, and keep bulk audio out of Git. After migration, historical build paths must be reproducible or explicitly mapped to retained material; missing inputs remain a reported exception, not a deletion candidate.

Use the [existing cleanup contract](../workflows/build-cache.md) for exact duplicate WAVs and lossless text compression. Extend it only for verified regenerable intermediates and reviewed retention selections. The desired result is a disposable working directory with any remaining exceptions identified. Case closure must retain selected results/evidence and clean replaceable working output so growth does not repeat.

**Separate the budgets:** measure (1) default clone/download and supported setup, (2) optional study downloads, (3) active/generated build output, and (4) the external local archive. The former 6.0 GB checkout ceiling and 4.4 GiB build allowance were rough maintainer-cleanup estimates, not user installation requirements or a justification for permanently retaining that much build output. They are superseded by this separation. Set practical budgets from the classified inventory and cold-clone measurements; report deleted bytes, relocated bytes and total retained storage separately. Moving files must not be presented as disk-space reclamation.

**Alternative: lossless FLAC.** Consider it for local/optional retained audio only if worthwhile after deduplication and selection. Require decoded-PCM equality, metadata handling and usable restoration/links; original WAV container hashes will differ. Preserve current WAV sample downloads. Compression savings are unmeasured and not included in the footprint figures.

## Required, optional and excluded scope

**Required:** the three A repairs, both-host cold-clone walkthroughs, a ledger on the next real musical case, explicit component/dependency roles, unused ML removal, build classification/retention and the default-versus-optional distribution boundary. Reconcile the selected model-review policy with its owning instructions. [PLAN.md](../../PLAN.md) defines implementation stages and their completion evidence.

**Optional:** an entry skill or plugin justified by remaining friction, independently maintained research packaging if warranted, FLAC retention, and future explicitly authorized model experiments. A controlled human comparison remains deferred until staffing exists.

**Excluded:** a new backend/emulator/GUI/MCP service, tracker benchmarking, original composition by default, autonomous aesthetic acceptance, blanket cleanup, bulk listening-history additions to Git, rewriting Git history and automatic uploads/spending. Existing musical verdicts and publication restrictions remain intact.

## Review disposition

The external review led to explicit decisions, mandatory repair of A, affordable evaluation and a visible model-policy change. The subsequent user discussion establishes that local retention is separate from public distribution: useful research need not burden ordinary cloners, and `build/` becomes disposable through verified classification and migration. Optional versioned downloads are preferred over a new submodule; existing LFS use must have explicit acquisition behavior. The former aggregate storage target is replaced by separate measured footprints. Design is ready for implementation; cleanup, redistribution and effort results are not claimed complete.
