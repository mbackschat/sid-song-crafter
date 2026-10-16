# SID Song Crafter: product interface, value and resource discipline

Status: proposal for external review, 2026-10-16. Recommendations below are not adopted architecture, completed experiments or authorization to publish, install services or make paid model requests. [PLAN.md](../../PLAN.md) remains the sole authority for active work and completion. This document proposes the public contract and the evidence needed to choose it; it does not reopen accepted musical cases.

Repository: [mbackschat/sid-song-crafter](https://github.com/mbackschat/sid-song-crafter). Relative evidence links resolve from this file's location, `docs/proposals/workbench-direction.md`; review it with the repository snapshot when inspecting local evidence. The storage measurements describe the maintainer's working checkout, not the external reviewer's machine.

## Decision requested

Retain **SID Song Crafter as an agent-assisted composition and sound-design workbench**. Keep executable tools and reusable musical knowledge as its foundation. Evaluate a small composition-workflow skill alongside the existing supporting skills, with dependencies installed and checked explicitly. Choose a plugin or a larger skill collection only if it solves demonstrated distribution or workflow problems. Measure total effort to an accepted musical result before claiming productivity improvement.

This recommendation is provisional: the existing work demonstrates useful music and mechanisms, but neither an independently usable newcomer workflow nor reduced total composition effort has been established. The review should challenge the proposed boundaries and experimental design, including the possibility that simpler documentation suffices or that the workbench fails to save effort.

## User input and constraints

The following restates the user's input relevant to this decision. Recommendations elsewhere must not be mistaken for user decisions.

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

Earlier musical requirements still constrain the product: interpret attributed existing scores creatively through SID sound and arrangement; retain MOS6581, MOS8580 and stereo coverage; provide the README samples in mono/stereo SID and WAV with their source materials and recipes organized together. The Rambo demos omit roughly the first 32 seconds of unwanted introduction; complete accepted versions remain separate. The [sample library](../../samples/README.md) records the delivered packages, accepted presentations and redistribution limits. This proposal does not withdraw those outputs to make the installation smaller.

The Axel F work supplies relevant qualitative evidence: the user preferred varied rhythm over the plainer kick/snare attempt, and valued Hülsbeck's snappier lead, more forceful and varied percussion, and trailing chiptune quality. Changing only the SID model yielded no useful difference; shortened notes were objectionable; restoring the release helped. The trailing lead and quieter snare balance were accepted, then the complete rendition was accepted. The user selected the shorter ending despite hearing no clear difference. Maracas could have an accepted balance yet remain distracting and unsuitable, and triangle was faint. These findings require evaluation of musical roles, phrasing and context, rather than note correctness, volume, chip labels or isolated patch approval. Exact scoped verdicts and the earlier held-support/high-lead concerns remain in the [Axel F review](../../songs/axel-f/arrangement-review.md).

The user also asked whether models could help explain Hülsbeck's strengths and authorized one specific four-clip OpenRouter/Qwen trial: the master passage, our kick/snare opening, silence, and an exact short loop. That authorization was bounded, not general permission for future assessment uploads. The [retained trial](../research/audio-assessment.md#axel-f-descriptive-follow-up-silence-failure) failed its silence control. Model observations remain experimental supporting evidence; human musical acceptance remains decisive.

## Verified current product

This is a bounded repository and documentation audit, not a fresh installation test or a measured user study. Local facts and storage were checked on 2026-10-16.

| Area | Existing contract and material gap | Evidence |
| --- | --- | --- |
| Product | A command-line toolkit and reference library for expressive interpretations of existing scores. Original score composition is outside the default remit. | [Product purpose](../../PRODUCTS.md), [README](../../README.md) |
| Executable entry | The Bach walkthrough prepares an existing arrangement and builds SID/PRG, an editable native module and WAV. It is a worked example, not an automatic arranger for arbitrary scores. | [README walkthrough](../../README.md#walkthrough-from-score-to-sid-arrangement) |
| New score | MIDI importer plus explicit part/spans/reduction configuration; candidate/reference native templates are optional but must be supplied together when used. The generic projection requires exactly three named voices. | [Preparer](../../scripts/prepare-score-audition.py), [score workflow](../workflows/song-workflow.md) |
| Native targets | Three- or six-voice export, explicit PAL/NTSC and MOS6581/MOS8580. Current dual-SID recipes select the same model for both chips at `$D400`/`$D420`. Six-voice authoring is a separate step from the generic three-voice projection. | [Native contract](../workflows/native-song-workflow.md) |
| Hardware meaning | Each chip has one mono output, shared filter/volume and oscillator dependencies. Stereo placement comes from deliberate chip allocation and output mixing; six voices do not imply six independent pan controls. | [Dual-SID contract](../research/sid/dual-sid.md) |
| Repeatable execution | A recipe runner already manages commands, deadlines, input/output fingerprints, cache reuse, timing receipts and listening indexes. CPU, emulator and audio checks establish different properties. | [Recipe runner](../workflows/listening-package.md), [tool guide](../../scripts/README.md) |
| Skills | Setup installs pinned `c64-sid` by default; `sid-music` is optional. These provide hardware reference and connected playback guidance, not a project-owned score-to-delivery skill. | [Installed skills](../../skills/README.md), [manifest](../../config/local-assets.json) |
| Corrections and integration | Upstream prose needs project corrections. Installing a skill does not connect c64bridge. Alternative Bun builds use its assembler source separately from its live MCP server. | [Corrections](../setup/skill-guidance.md), [integration evidence](../research/tools/skills-and-integrations.md) |
| Readiness | `doctor.py` checks the full environment, including VICE; the minimal Bach walkthrough needs less. The tracked bridge configuration contains maintainer-specific absolute paths. | [Doctor](../../scripts/doctor.py), configuration examples for [Codex](../../config/codex.toml) and [Claude Code](../../config/claude-mcp.json), [setup](../setup/local-setup.md) |
| Evidence of value | Accepted songs and transfers demonstrate useful outputs and reuse. Recipe timings demonstrate execution savings. No complete comparative total-effort ledger was established by this audit. | [Plan and completion evidence](../../PLAN.md), [listening workflow](../workflows/listening-package.md) |

The existing [SID Song Explorer proposal](web-player-and-analyser.md) concerns a separate playback/analysis application and possible later browser-facing workbench. This proposal preserves that ownership boundary. A new UI, service or emulator is not required to answer Crafter's current value question.

## Can skills depend on skills?

There are three different mechanisms. Their distinction changes the packaging recommendation.

| Mechanism | Verified support | Consequence for Crafter |
| --- | --- | --- |
| Instructions referring to another skill or resource | Skill bodies can describe workflows and link supporting resources. This is agent guidance; it does not itself install a missing skill, resolve a version or prove the agent loaded it. | One entry skill can coordinate existing knowledge only if setup and the workflow check its required resources explicitly. |
| Portable skill dependency declaration | The Agent Skills specification lists compatibility text and arbitrary metadata, but no standardized skill dependency resolver. Codex's documented `agents/openai.yaml` dependency validation supports `dependencies.tools`; it is not a skill package manager. | Do not claim that a hypothetical `depends_on: c64-sid` field provides portable installation or enforcement. [Agent Skills specification](https://agentskills.io/specification), [OpenAI validation reference](https://developers.openai.com/plugins/deploy/submission-errors). |
| Plugin packaging and host-managed dependencies | OpenAI documents packaging multiple skills and MCP configuration together. Claude Code separately documents plugin dependencies with version constraints, including dependencies supplying skills. | A multi-skill plugin is feasible; Claude's plugin dependency mechanism must not be presented as a cross-host skill dependency standard. [OpenAI packaging](https://developers.openai.com/plugins/build/plugins), [Claude Code dependencies](https://code.claude.com/docs/en/plugins/dependencies). |

These official pages were checked on 2026-10-16; no installation experiment was performed. The earlier statement about unavailable skill dependencies was specific to Codex skill metadata and incomplete as a cross-platform answer. Claude Code's documented plugin mechanism is a real alternative. It still requires suitable upstream plugins and compatible releases; the presence of an upstream `SKILL.md` alone does not establish that packaging.

**Recommendation:** retain explicit project setup as the initial dependency boundary. It already pins upstream bytes and can report missing resources. Evaluate one composition entry skill with supporting skills installed alongside it. If distribution friction justifies a plugin, package the selected components with host-specific manifests and tested activation. Do not merge upstream skill text into a new monolithic skill or assume permission to redistribute it. Existing corrections and source/license ownership remain explicit.

## Interface alternatives

| Option | Benefit | Cost or limitation | Recommendation and reason |
| --- | --- | --- | --- |
| A. Documented CLI and recipes, with existing supporting skills | Smallest change; usable by people and agents; deterministic work stays in tools. | Newcomers must discover and connect several configuration files and guides. | Use as the baseline. It may be sufficient after improving the worked own-score example. |
| B. Workbench plus one composition entry skill and selected supporting skills | Gives an agent a discoverable workflow while reusing scripts, canonical guides and upstream expertise. | Requires dependency/discovery checks; can duplicate documentation or add prompt overhead if poorly scoped. | Preferred candidate to test against A. Retain it only if it improves task completion, effort or reliability. “One entry skill” does not mean “one installed skill.” |
| C. A collection of independent composition, sound-design, analysis and playback skills | Separate workflows could be invoked and reused independently. | More overlapping triggers, dependencies, instructions and maintenance; current task boundaries may not justify them. | Defer. Split only when distinct user tasks and observed reuse support the boundary. |
| D. A plugin bundling skills and relevant integrations | Provides a named installation unit and namespaces; can carry several skills. | Host-specific packaging, upstream licensing, version management and installation verification remain. It does not replace the compiler, renderer or local tools. | Consider as distribution for B or C, not as a competing music engine. Prefer it when installation is the demonstrated bottleneck. |
| E. A self-contained skill containing copied tools and reference material | Potentially convenient single bundle. | Duplicates ownership, encourages stale copies, inherits redistribution constraints and still needs executable dependencies. | Reject for the initial design; use the repository's authoritative tools and materials. |
| F. GUI/browser workbench or a new MCP API | Could improve interactive editing or access from agents without shell execution. | Introduces a substantial product surface before composition value is measured. | Keep outside this assessment; preserve the separate Explorer proposal. Reconsider a service only for a concrete access requirement. |

The user selected **Codex and Claude Code as initial support targets** on 2026-10-16. Use one shared workflow and test discovery for each. Codex-only would reduce support cost but does not meet the selected scope. Neither target gains a support claim merely from sharing Markdown. The tracked activation targets `.agents/skills/`, and the tracked `.claude/skills` directory link exposes the same activations to Claude Code; discovery of both pinned skills was checked in each host ([local setup](../setup/local-setup.md#unified-local-setup)). Claude Code also documents its own plugin conventions. [Claude Code skills](https://code.claude.com/docs/en/skills).

## Proposed public workflow and contract

**Required inputs:** an attributed MIDI or an explicitly supported editable score, musical intent, declared musical form/ending, target chip model/count and clock, and a reference where available. Source identity and publication rights are recorded separately. PDF notation needs transcription or a corresponding MIDI; automated notation recognition is not promised.

The person should be able to ask: “Interpret this score with a restrained, trailing lead and clear bass, for PAL MOS8580. Preserve the melody and form, show the reduction choices, and give me playable SID plus a full preview.” The agent asks about missing consequential musical choices, retrieves relevant instruments and constraints, prepares an explicit arrangement, and runs the existing build/listening recipe. Routine execution does not require repeated permission. Musical uncertainty returns as a small, labelled comparison with a reference and a clear listening question.

**Required outputs:** preserved source/provenance; editable arrangement and instrument recipes; recorded omissions and deliberate adaptations; playable SID and PRG; native SWM/SWS for the SID-Wizard path, or equivalent editable score/program source for specialist backends; technical verification receipts; representative phrase, separate ending and complete WAV preview; scoped listening decision and reproducible delivery. WAV is a preview, not the only reusable musical source. Default configuration must not require hosted audio services, local ML weights or a live bridge.

**Target guarantee:** retain both chip models, single/dual SID and explicit PAL/NTSC exports within their existing contracts. Begin an effort comparison on one fixed target to avoid confounding it with platform differences; this does not narrow the product to MOS8580 or mono. For dual SID, require musical role → chip/voice → coupling/filter ownership → output matrix. Mixed-model chips and automatic arbitrary six-voice reduction are not established capabilities.

**Readiness guarantee proposed for review:** clearly distinguish listening to shipped samples, building the supplied demo, full verified score work, optional live playback and optional research. Missing prerequisites should name the affected workflow rather than imply that every optional component is required. The exact setup interface remains an implementation choice after review.

## Component recommendations

| Component | Proposed disposition | Rationale and alternative |
| --- | --- | --- |
| Native export, renderer, CPU/VICE checks, score preparation, comparison and recipe runner | Core for their declared workflow stages | Already produce verified deliveries. Replacing them adds work without addressing a demonstrated gap. Direct commands remain available beneath any agent interface. |
| Repertoire, technique index, source provenance, accepted/rejected examples | Core, retrieved selectively | This is the proposed source of musical effort savings. Copying all studies into every prompt would undermine that benefit. |
| `c64-sid` | Keep pinned and available initially; test whether it must remain default | It offers targeted hardware reference, with known corrections. No audited evidence yet justifies either deleting it or requiring the entire upstream skill collection. Native builds are not runtime-dependent on its Markdown. |
| `sid-music` and live c64bridge | Optional connected-playback feature | The standard headless path works without a live server. Retain the bridge assembler source for existing Bun users; do not conflate its source imports with server packages. |
| Specialist decoded backends and study programs | Retain as specialist/research capabilities | Some have shared imports and frozen evidence paths. Removal by filename or age risks breaking useful mechanisms. Prefer a smaller supported default surface before deleting source. |
| General coding/reasoning models | Required capability for the selected agent-assisted mode; no mandated winner | Useful for reading, editing, hypotheses and execution. Fix model/settings in comparisons. Tier mappings are routing policy, not evidence of equivalent quality or lowest total cost. Compare cheaper configurations only against the same accepted-result contract. |
| Hosted audio models, including tested Qwen/Gemini/GPT audio configurations | Experimental, opt-in, outside normal acceptance | The latest Qwen trial hallucinated a tone in verified silence; earlier successes remain task-specific. Keep runners and evidence, not automatic critique calls. Untried models have no demonstrated project benefit. [Measured trials](../research/audio-assessment.md). |
| SongBench/MuQ installation | Research-only; candidate for local removal with restoration records retained | Ranking disagreed with a retained human preference; useful defect detection remains unvalidated. The recorded checkpoint licenses also constrain production use. Keep historical results and pinned restoration information. [Measured local trial](../research/audio-assessment.md#measured-local-songbench-trial). |
| Repeated model-review paperwork | Replace prospective per-revision “no call” records with one standing case decision and event-driven reassessment | Revisit when a useful concrete question, changed relevant configuration or user request warrants it. Preserve historical findings. This is a proposed policy change; current contributor requirements remain in force until reconciled. |

A component earns default inclusion through a necessary supported capability or observed benefit after installation, operation, correction and maintenance costs. A low per-request price alone is insufficient. No provider migration, new model download, automatic spending or upload follows from this recommendation.

## Measuring the claim

There are two different claims: **the whole workbench helps compared with an alternative way of making SID music**, and **curated knowledge or agent guidance improves use of this workbench**. They need different comparisons. “Total composition effort” here means producing an expressive interpretation of an existing score through an accepted declared form, including its ending; it does not silently expand the project into original melody composition.

| Evaluation option | What it can establish | Recommendation |
| --- | --- | --- |
| Retrospective timing from existing songs, commits or cached runs | Examples of outputs and tool execution cost; incomplete human/agent cost | Use as background only. Do not infer missing work or a productivity percentage. |
| Prospective ledger for the next complete task | Actual production cost and where effort goes | Start here. It supplies a cost baseline, not comparative savings. |
| Same backend, reference-only workflow versus curated repertoire/guidance | Incremental benefit of project knowledge and guidance | Recommended first controlled pilot. Keep the executable backend and technical gates constant. |
| Same curated knowledge, documentation versus an entry skill | Incremental benefit of skill packaging | Recommended interface comparison if walkthroughs reveal guidance friction. Keep the content and tools equivalent; do not attribute the combined benefit of better content and a skill to the skill alone. |
| Crafter versus a familiar tracker/editor or an independent existing workflow | Broader product-level effort advantage for that comparator and audience | Needed before a broad comparative claim. Select the comparator with an operator competent in it; forcing an unfamiliar editor would bias the result. Do not turn this into a multi-editor benchmark now. |

**Effort ledger:** record human active time for briefing, intake, arrangement, listening, revisions, troubleshooting and retention; agent model/configuration, wall time and tokens/cost where exposed; tool runtime and waiting; cold setup; new reusable engineering; failed attempts; first playable and first accepted output with fingerprints. Sum parallel resource use separately from elapsed time. Do not add overlapping human, agent and tool wall time into a misleading scalar. Report costs as a vector, including maintainer support; unavailable measurements remain unavailable. Report first-use cost and repeat-use cost separately, with explicit amortization assumptions.

**Pilot design:** two independent operators and two unfamiliar comparable short complete forms, four jobs. Each operator uses both conditions on different scores; each score appears in both conditions, with workflow order counterbalanced. Run only one contrast at a time. Freeze source/brief/rights, target, agent configuration, allowed material, technical gates, time limit and listening rubric before starting. Use isolated sessions and record unavoidable learning/carryover. A fresh agent is a useful walkthrough proxy, not an independent human newcomer, and does not reset an operator's learning. This small design cannot separate carryover or operator-by-score differences from a condition effect: it tests protocol viability, exposes friction and produces descriptive costs, not a causal savings estimate.

**Quality gate:** a listener blinded to condition judges source preservation, intended character, phrasing, balance and ending with consistent level treatment. Both conditions must meet the same technical contract. Report time to accepted form, rejected outputs, revisions and time-limit failures; do not drop failures or call a faster rejected result a win. Four jobs are a feasibility pilot, not a statistically reliable universal savings estimate, and short-form success does not establish full-song savings. If humans or a fair comparator are unavailable, record that limit and report only the narrower measured cost/usability result.

**Decision rule:** use the pilot to reject unusable designs and select a candidate for further testing, with the observed friction and costs stated. Before a stronger comparison, freeze the meaningful improvement criterion and use enough independent assignments to address operator/score variation and learning. Adopt a default based on demonstrated usefulness without sacrificing quality or concealing setup/maintenance work; a numerical difference across four pilot jobs is not proof. Report positive, negative and inconclusive results; a failed savings claim may leave a useful research library or specialist toolkit. Broader claims require the broader comparator, additional independent cases and full-length work.

## Storage and retention

The user's “over 6 GB” concern is confirmed and exceeded by the current local checkout. The following snapshot used `du -sk` on 2026-10-16; displayed GiB values are rounded allocated sizes. Rows beneath the total are contained within it and must not be added to it.

| Location | Allocated KiB | Approximate GiB | Meaning |
| --- | ---: | ---: | --- |
| Entire checkout | 10,948,600 | 10.44 | Local working environment, not a download-size measurement |
| `build/` | 6,722,384 | 6.41 | Generated outputs, caches and retained listening material |
| `.local/` | 2,164,304 | 2.06 | Local sources, model data, caches and tools |
| `.tools/` | 1,456,456 | 1.39 | Third-party source, environments and dependencies |
| `evidence/` | 197,956 | 0.19 | Canonical verification/research evidence |
| `samples/` | 139,592 | 0.13 | Packaged examples and locally generated sample outputs |
| `.git/` | 250,228 | 0.24 | Git history, metadata and local object storage |

A separate `git ls-files`/`lstat` sum found 355,302,807 logical bytes (338.84 MiB) in 3,304 tracked regular working-copy files, excluding symlink targets, ignored files and Git objects. This is not comparable to allocated `du` sizes and does not measure a fresh clone, LFS transfer or release download. A public installation footprint still needs its own measurement.

| Retention option | Tradeoff | Recommendation |
| --- | --- | --- |
| Keep everything local | Immediate access, but continued growth and ambiguous ownership | Reject as the default storage policy. |
| Remove reproducible unused installations and verified duplicate caches | Low musical risk; incurs download/rebuild cost when reused | First choice. Check exact paths, restoration pins and dependency use, then retain before/after receipts and run core checks. |
| Archive selected historical intermediate/listening packages | Larger savings, but less immediate listening access and potential broken links | Consider only after an explicit retention manifest preserves accepted versions, references and decision evidence. Moving data elsewhere is not equivalent to deleting waste. |
| Delete all build output or prune Git/LFS history | Quick reduction, but destroys unique local material or changes distribution history | Excluded from this proposal. Existing historical paths and publication limits matter. |

The measured MuQ directory, SongBench checkpoints, isolated ML environment and uv cache total about **2.89 GiB allocated**. They are candidates, not a guaranteed reclaimed amount: verify pinned weights and restoration metadata, shared cache use and active processes before removal; preserve small source/config/license files. Bridge `node_modules` adds about **0.29 GiB**, but removal requires checking the alternative Bun assembler/tests and documenting that live bridge use needs reinstallation. Filesystem sharing and hardlinks can make physical free-space changes differ from directory totals. No deletion was performed for this proposal.

Removing roughly these optional installations would still leave about 7.5 GiB by simple directory subtraction, chiefly generated audio/build material. It would not finish the waste assessment. Preserve accepted mono/stereo samples, selected native releases and editable materials, original sources, canonical evidence, scoped rejected/accepted comparisons and deferred user work. Use the [existing cleanup contract](../workflows/build-cache.md); it already handles exact duplicate cache WAVs and lossless text compression. Set storage budgets only after separating core installation, optional research, active work and retained releases. Repeated regeneration also costs time and belongs in the effort accounting.

## Required, optional and excluded scope

**Required for the proposed assessment:** a concrete supported user workflow; explicit tool/skill dependency boundaries; component retention decisions with evidence; measured local and distribution footprint; protected retention/recovery; and an honest, quality-gated effort evaluation. Root [PLAN.md](../../PLAN.md) owns sequencing and status.

**Optional, conditional on demonstrated need:** one composition entry skill, a multi-skill plugin, additional independent workflow skills, a cheaper agent-model comparison, an explicitly bounded audio-model experiment, or archiving selected historical intermediates. Each needs a stated benefit and acceptance criterion.

**Excluded:** a new composition backend, new emulator, mandatory live MCP, autonomous aesthetic acceptance, original score composition by default, indiscriminate cleanup, rewriting Git history, unapproved uploads/spending, and treating the separate Explorer application as a prerequisite. Existing musical deliverables and their qualifications remain intact.

## Questions for external review

1. Does the proposed workbench contract match an agent-assisted musician/developer? **Recommendation:** retain it; change it only if concrete target users need a different level of score preparation or musical control.
2. Is A sufficient, or does B offer a testable benefit? **Recommendation:** compare a documented own-score workflow with one entry skill that uses the same underlying knowledge; do not begin by producing a broad skill collection.
3. Should installation remain repository-based or become a plugin? **Recommendation:** use pinned project setup first; prefer a plugin only if it demonstrably reduces installation/discovery friction across the selected hosts.
4. Does the dependency design actually support the selected Codex and Claude Code targets? **Recommendation:** share workflow content and executable tools, with separate activation checks. A Codex-only shortcut would require an explicit scope change.
5. Does the effort design measure the claim without conflating tools, knowledge and packaging? **Recommendation:** keep those contrasts separate, include first-use and maintenance cost, and reserve broad product claims for a fair external comparator.
6. What evidence would justify retaining audio models? **Recommendation:** a useful task-specific result passing controls and held-out evaluation, plus reduced total effort. Current evidence does not justify normal-path inclusion or musical authority.
7. Does the retention policy remove waste without sacrificing the project's value? **Recommendation:** begin with reproducible unused installations and proven duplicates; require explicit manifests before retiring unique listening evidence. Do not promise a final size before that inventory.

External reviewers should identify unsupported factual claims, missing user requirements, dependency/installation assumptions, unfair comparisons, unnecessary components and any simpler design meeting the same musical contract. Distinguish blockers from optional improvements and provide a rationale for proposed changes.
