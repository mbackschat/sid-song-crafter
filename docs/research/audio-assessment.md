# Automated musical assessment for SID

Published research checked: **2026-10-14**; project evidence through **2026-10-16**, with the standing review policy updated **2026-10-17**. This assessment concerns models that consume recorded music and return critiques, ratings or preferences. Published benchmark figures are author claims or independent benchmark findings, **not project measurements**. Measured project evidence includes the bounded OpenRouter pilots for Qwen3.8-Omni-Flash, Gemini 3.8 Flash and GPT Audio Mini and the local SongBench Metal/CPU trial below; the other specialist candidates remain untested here. The eighteen initial authorized audio requests cost $0.00526592 in total. SongBench was installed in an isolated local environment for the research trial.

## Recommendation and scope

**None of the tested models is accepted as a dependable musical judge.** Qwen3.8-Omni-Flash passed constrained elementary controls and scoped Trap calibration, and its short-speech trial passed controls, but the [Axel F follow-up](#axel-f-descriptive-follow-up-silence-failure) failed verified digital silence with the unchanged Trap prompt and configuration. That failure prevents treating the Trap pass as general eligibility for musical descriptions. SongBench runs locally on Metal and responds to deliberate dropouts, but its musicality ranking contradicts the retained human preference. Keep signal/execution checks and human artistic judgment; neither model-wide inability nor a routing defect follows from these bounded results.

Keep one hosted gateway for now. OpenRouter permits model comparisons without separate provider accounts; the local SongBench trial needs no hosted service. **MuseCritic**, **CMI-RM** and direct GPT-Audio-1.5 remain researched alternatives. Further model selection should address a measured capability gap through a bounded experiment.

The intended benefit is fewer routine listening requests: identify likely missing material, compare timbral animation and phrasing, and bring specific uncertain passages to the user. Separate known-source correctness from musical success. A trace or preserved score can establish that a note is absent; it cannot establish that an intentional omission improves an arrangement. Likewise, a musically preferred candidate need not reproduce the source. Keep [execution verification](validation/verification.md), [matched audio comparisons](../workflows/audio-comparisons.md) and the listener's verdict as distinct evidence.

## Use and reassess model assistance

Use model assistance for source research, arrangement hypotheses and advisory audio observations, checking claims against sources, scores, execution evidence or listening as appropriate. Eligibility belongs to a specific **task, model/version, prompt and preprocessing**, never to a model in general. An elementary perception pass does not qualify defect detection or musical preference. Human listening remains the authority for organ character, expression and acceptance. On 2026-10-14 the user explicitly confirmed the boundary: retain model outputs as experimental supporting signals until confidence improves. Corroborate any suggested issue before acting; keep model scores separate from acceptance, do not let them trigger arrangement changes on their own and do not optimize the music merely to raise them.

**Current eligibility, 2026-10-17:** no audio model is required for normal musical work. The following boundaries reflect the retained project evidence; future experiments need a concrete question that could improve the active [study-plan case](../PLAN.md#delivery-order-and-work-in-progress).

| Task and setup | Retained evidence | Current boundary |
| --- | --- | --- |
| Qwen constrained elementary categories and short recognizable speech | [8/8 elementary controls](#elementary-perception-and-presentation-follow-up); [Ghostbusters controls and descriptions](#ghostbusters-single-clip-speech-recognition) | Experimental supporting observations within the tested task/configuration; fresh uses require task-specific controls. No musical-acceptance authority follows. |
| Qwen rhythmic motion and local development | [Scoped Trap pass](#trap-melodic-motion-and-development-calibration), followed by [Axel F silence failure](#axel-f-descriptive-follow-up-silence-failure) with unchanged prompt/settings | The Trap pass does not establish transferable descriptive eligibility. Axel F descriptions remain excluded; another use needs task-specific calibration within the user's recorded authorization. |
| SongBench quality scores and defect sensitivity | [Reversed human musicality preference and unreviewed dropout hypothesis](#measured-local-songbench-trial) | Research only; no validated musical preference or useful defect detector. |
| Wrong notes, missing tails, subtle articulation, whole-song quality and stereo | No tested setup has passed project validation for these tasks | Use score/execution/PCM checks where they settle the question and human listening for musical judgments. |

When a musical case opens, record **one standing model-assistance decision** in its owning study: the relevant task and pinned setup, eligibility/evidence, whether a trial is useful and why, and the event that would justify reassessment. A decision not to call a model remains in effect through auditions, feedback and revisions unless a trigger occurs. Existing closed cases and their historical reviews remain intact.

Reassess when a concrete useful question arises, the relevant model/version, prompt or preprocessing changes, or the user explicitly requests model assistance. Listener feedback or a musical revision triggers reassessment only when it creates such a question. Update the standing decision and link any new trial outcome; retain earlier evidence. At closure, check that the decision still fits the completed case and every triggered trial has a recorded outcome. An unchanged decision satisfies this check without another skip record.

Use one compact standing row, linking retained evidence rather than copying trial details:

| Date / decision | Task and pinned setup | Eligibility / evidence | Use or defer / rationale | Reassess when |
| --- | --- | --- | --- | --- |
| YYYY-MM-DD / case opening or changed decision | Question; model/version, prompt and preprocessing receipt if relevant | Supported scope and retained results | Whether a trial could expose a useful issue or save work; link any run and its outcome | Concrete useful question, relevant configuration change or user request |

If human feedback is absent, record it as absent; a dropout hypothesis, score change or plausible description cannot supply that verdict. For an executed trial, assess whether assistance exposed a useful issue, saved work or misled the arrangement, and carry any eligibility change into the standing decision. Before a new trial, name the unresolved question and resulting musical action, freeze its criterion and retain the required identical-pair, known-difference, reversed-order and silence controls plus a held-out passage before relying on its task-specific results. Reuse cached results; skip repeated paid calls when no changed input or testable improvement addresses the known failure. A reassessment does not authorize an upload or paid request: stay within the user's existing provider, audio-selection and spending authorization. Use the existing bounded runners and owning records; no additional service, DSPy installation or evaluation framework is required.

Dated trial decisions below preserve their original findings and then-current next steps. Use the current eligibility and standing decision rule above for new work; historical checkpoint wording does not require repeated unchanged skip records or reopen closed musical cases.

## Candidates and access

| Candidate | Best initial role | Verified access and material constraint |
| --- | --- | --- |
| **GPT-Audio-1.5** | Fallback audio critique trial using existing OpenAI access | [Model](https://developers.openai.com/api/docs/models/gpt-audio-1.5) and [bounded audio chat requests](https://developers.openai.com/api/docs/guides/audio-chat-completions); audio input and text output; SID perception unvalidated |
| **MuseCritic**, paper 2026-08-12, revised 2026-10-01 | Explain perceived musical weaknesses before assigning five scores | [Code](https://github.com/WuqnEl/MuseCritic) and [Apache 2.0 checkpoint](https://huggingface.co/WuqnEl/MuseCritic); CUDA inference, no listed Hugging Face inference provider |
| **CMI-RM**, ICML 2026, paper revised 2026-06-11 | Rank musicality and instruction alignment separately | [Apache 2.0 code](https://github.com/Haiwen-Xia/CMI-RewardBench); [0.7B checkpoint](https://huggingface.co/HaiwenXia/CMI-RM) under CC BY-NC 4.0 |
| **Qwen3.8-Omni-Flash**, API released 2026-09-17 | Hosted audio descriptions and targeted listening questions | [Paid Model Studio API](https://www.alibabacloud.com/help/en/model-studio/qwen3-8-omni-flash), including Frankfurt; audio input, text output, multichannel option; downloadable weights not verified |
| **SongBench**, paper 2026-04-16 | Compare seven separate assessment dimensions | [Code and checkpoint](https://github.com/Tencent/SongBench); research-only, noncommercial use |
| **MOSS-Music-8B-Instruct**, released 2026-05-01 | Local music descriptions, instrument impressions and structure questions | [Code](https://github.com/OpenMOSS/MOSS-Music) and [Apache 2.0 weights](https://huggingface.co/OpenMOSS-Team/MOSS-Music-8B-Instruct); approximately 9.1B total parameters, CUDA/SGLang workflow |
| **CloudEar**, paper 2026-10-08 | Watchlist for pairwise musicality assessment | [Paper](https://arxiv.org/html/2610.11672v1) available; checkpoint, runnable release and paid API not verified |


## OpenRouter trial setup

Verified on **2026-10-13**: [OpenRouter lists Qwen3.8-Omni-Flash](https://openrouter.ai/qwen/qwen3.8-omni-flash/api), model ID `qwen/qwen3.8-omni-flash`, at $0.15 input / $0.47 output per million tokens. These posted rates are not a measured per-clip cost. [Audio requests](https://openrouter.ai/docs/guides/overview/multimodal/audio) use base64 `input_audio` content through Chat Completions; model access requires a live smoke test before treating integration as verified.

Use a dedicated `sid-audio-eval` inference key with a $5 total spending limit and no reset. [Key limits](https://openrouter.ai/docs/api/api-reference/api-keys/create-a-new-api-key) support no reset or daily, weekly and monthly resets. [Spend controls](https://openrouter.ai/docs/guides/best-practices/spend-controls) block requests once an applicable budget is reached and support model restrictions. Keep automatic credit top-ups disabled; [credit purchases carry a separate fee](https://openrouter.ai/docs/faq). Store the key only in ignored `.local/openrouter-api-key`, with owner-only permissions; never print it or include it in evidence. The runner should bound requests, retries and output length and preserve actual usage/cost without credentials.

First test one short audio request for connectivity, then a bounded anonymous A/A and Gauntlet pulse comparison with swapped order. Confirm available source audio before preparing probes. The live pilot verified an ordinary inference key with a $10 non-resetting cap and eight completed requests. Automatic top-up settings were not inspected; credential bytes are excluded from logs and evidence.

### Run the bounded pilot

The [pilot preparation script](../../scripts/studies/audio-assessment/prepare-trial.py) verifies the retained Gauntlet source hashes and uses the existing PCM window tool. It makes one four-second smoke clip and three 16.5-second comparisons: identical original A/A, stationary/original, and original/stationary. The last is byte-identical to the user's audition. All comparisons retain unity gain and a half-second gap. Anonymous filenames and prompts go to the model; the local provenance mapping and user's verdict do not. Reference-derived WAVs remain under ignored `build/`.

```sh
python3 scripts/studies/audio-assessment/prepare-trial.py --output build/audio-assessment-openrouter-20261013
python3 scripts/audio_assessment.py build/audio-assessment-openrouter-20261013/trial.json --output build/audio-assessment-openrouter-20261013/results --dry-run
python3 scripts/audio_assessment.py build/audio-assessment-openrouter-20261013/trial.json --output build/audio-assessment-openrouter-20261013/results
```

Preparation requires a fresh output directory; re-running the assessment uses its retained request cache. The [runner](../../scripts/audio_assessment.py) accepts a manifest containing `model`, `max_tokens` and `cases` with `id`, `prompt` and `wav` fields. WAV paths resolve relative to the manifest. The pilot uses temperature zero, no provider fallbacks and at most 1,200 output tokens. Baseline reasoning is disabled; optional manifest `reasoning: true` enables the follow-up configuration and changes the cache key. Optional `reasoning_effort` accepts `low`, `medium` or `high` only with reasoning enabled; Gemini uses low effort because its model metadata declares reasoning mandatory. It bounds files, duration and POST attempts, verifies the key's remaining allowance, reserves $0.01 before each new request against a $0.10 local trial threshold, and stops on unknown cost or an uncertain previous attempt. The reserve is a conservative admission policy, not a provider billing guarantee. No automatic retry occurs. Responses, input/payload fingerprints and usage receipts enable review without storing credentials or duplicating audio in request logs.

## Feasibility on the current computer

The project machine checked on **2026-10-13** is a **Mac mini, Apple M1, 16GB unified memory**. Hosted Qwen3.8, OpenAI and Gemini run remotely; local weight memory is not a constraint, although paid requests and audio upload remain separate actions.

Stock MOSS-Music is unsuitable: approximately 9.1B parameters require **18.2GB (about 17GiB) for 16-bit weights alone**, before runtime allocations. A quantized Mac deployment was not verified. [MuseCritic inference](https://raw.githubusercontent.com/WuqnEl/MuseCritic/main/infer/infer.py) defaults to CUDA with a BF16 backbone; its adapter count does not describe the complete model. Neither is recommended for immediate local installation.

[CMI-RM inference](https://raw.githubusercontent.com/Haiwen-Xia/CMI-RewardBench/main/baselines/inference.py) explicitly supports CPU/FP32 and 30-second chunks, but its approximately 2.8GB reward checkpoint understates stock setup requirements. Its [constructor](https://github.com/Haiwen-Xia/CMI-RewardBench/blob/main/models/cmi-rm/src/muq/muq_mulan/models/mymodel.py) first initializes MuQ-MuLan, whose [backbone configuration](https://huggingface.co/OpenMuQ/MuQ-MuLan-large/blob/2e01c796b71dca71b45251384c04cd7b237c9020/config.json) requires MuQ and XLM-RoBERTa. Public checkpoint sizes checked on **2026-10-14** total approximately **7.36 GiB of downloaded weights** across the reward model, MuQ-MuLan, MuQ and text tower, before dependencies and caches; this is disk/download demand, not measured peak RAM. Stock CMI-RM was excluded from the bounded local trial. [SongBench inference](https://raw.githubusercontent.com/Tencent/SongBench/main/eval.py) needs only its small scoring head and MuQ, about **1.34 GiB of weights combined**. Its explicit Metal path and CPU comparison are now measured in the [local trial below](#measured-local-songbench-trial), with roughly 2.87 GiB peak process RSS on Metal and close numerical agreement on one CPU input. All three assessors preprocess to mono by default, so their standard paths cannot assess dual-SID stereo imaging.

## What the evidence establishes

**OpenAI** documents actual audio input for GPT-Audio-1.5 through Chat Completions, allowing recorded WAV comparisons with text responses. Its positioning is voice-oriented; the inspected documentation does not establish musical judgment equivalent to the specialist models. [GPT-Realtime-2.1](https://developers.openai.com/api/docs/models/gpt-realtime-2.1) adds configurable reasoning in a voice-agent workflow, but no inspected music benchmark proves that the extra session machinery improves this task. Start with the simpler [file-audio chat interface](https://developers.openai.com/api/docs/guides/audio-chat-completions), testing the sound itself rather than a speech transcript.

**MuseCritic** produces a critique followed by coherence, musicality, memorability, structural clarity and vocal naturalness scores. Its authors report **71.35% pairwise preference accuracy on 733 MusicArena pairs**. This is closer to useful musical feedback than generic captioning, but it remains imperfect and trained around generated songs with vocals. Explanations can suggest where to listen; their fluency does not verify the claimed defect. [MuseCritic paper](https://arxiv.org/abs/2608.11755).

**CMI-RM** is a reward model, not a conversational listener. Its authors report **MusicEval musicality SRCC 0.8266** and **78.2% CMI-Pref musicality preference accuracy**, compared with Gemini 3 Pro's 65.8% in their evaluation. Its separate alignment output helps distinguish compliance with an instruction from enjoyable music. These scores justify a ranking trial, not an inferred ability to locate a missing note or explain organ character. [CMI-RewardBench paper](https://arxiv.org/abs/2603.00610).

**Qwen3.8-Omni-Flash** is a substantially newer candidate than Qwen2.5-Omni. Table 4 of its report gives **72.6 MuchoMusic-RUL, 75.8 HumMusQA and 50.6 MusTBench**, against Gemini 3.8 Flash's 53.7, 71.2 and 40.3 respectively. These are audio-input/text-output understanding tasks, not expert musical-quality ratings. The [release registry](https://www.alibabacloud.com/help/en/model-studio/newly-released-models) dates the API to September 17. Its hosted access makes it practical for a paid trial without local GPU setup. [Qwen3.8 technical report](https://arxiv.org/html/2609.25611v1).

**SongBench** scores vocal, instrument, melody, structure, arrangement, mixing and musicality using expert song annotations. The paper reports utterance-level musicality **SRCC 0.829**, versus SongEval's 0.593. More relevant to subtle comparisons, within-generator A/B accuracy is **62.24% for Suno and 64.13% for LeVo**, while the easier inter-generator comparison reaches 85.57%. Those differences argue against extrapolating broad model-ranking success to reliable discrimination between two closely related SID edits. Its instrument dimension includes realism and acoustic fidelity, which may penalize deliberate chip timbres. [SongBench paper](https://arxiv.org/html/2604.25937v1).

**MOSS-Music-8B-Instruct** reports **80.38 average accuracy across eight music QA/classification benchmarks**, compared with MusicFlamingo's 73.87 and Qwen3-Omni's 66.75 under its developers' protocol. Isolated-note NSynth results are reported separately, including 86.94% pitch accuracy. Instruct outperforms Thinking on the headline QA suite. Caption assessments are preliminary GPT-5.4 judgments; chord-transcription benchmark results are not yet supplied. Music QA leadership therefore supports trying it for descriptions, without establishing reliable polyphonic note checking or aesthetic critique. [Official evaluation](https://github.com/OpenMOSS/MOSS-Music).

**CloudEar** combines learned perception, signal diagnostics and prompt/instrument alignment. Its authors report **81.79% CMI-Test musicality preference accuracy and 76.57% MusicArena accuracy** in their own evaluation. It samples random 30-second clips and uses approximately 7,000 hours of in-house human-rated training music, mainly English generated songs. Random cropping is poorly suited to guaranteeing coverage of a specific ending; the paper leaves explanations of preference causes to future work. Its results cannot be directly compared with other papers' differently sampled evaluations. [CloudEar paper](https://arxiv.org/html/2610.11672v1).

## Perception and benchmark cautions

No candidate has passed musical project calibration. Qwen passed the elementary category gate below; that gate does not test subtle music discrimination. Vocal expectations, acoustic realism, production norms and genre priors may prefer smoother contemporary audio over intentional pulse motion, arpeggiation, noise attacks or sparse three-voice arrangements. “Organ-like” is a listener impression, not proof of instrument identity. The [instrument-grounding audit](https://arxiv.org/html/2606.31338v1) explicitly tests related keyboard candidates—accordion, organ, piano and synthesizer—and candidate-order variation, offering a useful design for testing this distinction.

Even expert-authored QA contains shortcuts. HumMusQA's authors found MusicFlamingo at **58.5% with real audio but 42.2% with silence**; Gemini 2.5 Flash reached 42.7% from text alone against 25% chance. Their analysis identifies weaker harmony, melody and performance reasoning and sensitivity to answer order. The [core music-perception study](https://proceedings.mlr.press/v303/carone26a.html) separately tests rhythm, transposition and chord quality using audio versus symbolic input. Neither general QA accuracy nor theoretical competence guarantees accurate listening. [HumMusQA findings](https://arxiv.org/html/2603.27877v1).

Temporal grounding is also coarse. [MusTBench](https://arxiv.org/html/2605.29300v2) accepts event timestamps within three seconds and finds difficult offset localization. This does not establish frame-level articulation or release-tail detection. A [2026-10-09 judge audit](https://arxiv.org/html/2610.13247v1) finds order-following in four smaller pairwise judges and prompt-dependent quality correlations across five open judges; it distinguishes quality from alignment rather than proving that every model fails.

[Music Flamingo 2601](https://huggingface.co/nvidia/music-flamingo-2601-hf) is a noncommercial baseline. [GPT Audio 1.5](https://developers.openai.com/api/docs/models/gpt-audio-1.5) and [Gemini](https://ai.google.dev/gemini-api/docs/audio) accept audio; SID quality remains unproven. [Cyanite catalogue classification](https://api-docs.cyanite.ai/docs/audio-analysis-v6-classifier/) is lower priority for fine critique. Generation or transcription alone does not qualify a listener.

## Proposed bounded project calibration

Reuse the listening-package runner and cached renders. The initial three OpenRouter pilots failed or abstained on controls below. A next experiment should establish reliable end-to-end perception before extending to the larger fixed set of reviewed cases. Pin each listening record and exact audio hash; prompts receive anonymous identifiers, audio and a narrow question, with filenames, composer names, source status and expected verdict hidden. Add a specialist only if the trial exposes a capability it could address.

| Existing anchor | Question the model must answer |
| --- | --- |
| Accepted [Ghouls phrase and ending](composition/ghouls-preparation.md#compiled-export-and-complete-listening-package) and [Rambo comparisons](composition/rambo-preparation.md) | Avoid inventing meaningful differences in the accepted passages; perceptual agreement is scoped, not PCM identity |
| Earlier [Monty finite-ending comparison](composition/monty-preparation.md#correct-the-reference-continuation) | Identify missing reference continuation; distinguish it from the separately accepted corrected version and an intentional finite arrangement |
| [Gauntlet pulse comparison](composition/follin-contrast.md) | Recover the listener's preference for the original moving-pulse animation; retain that the stationary control changes two parameters |
| [Arkanoid drum diagnostic](composition/galway-contrast.md#controlled-drum-diagnostic-and-listening) | Avoid claiming an audible improvement when the user detected no change; executed differences remain real |

Add identical **A/A** pairs, controlled wrong-note and omitted-tail examples, swapped A/B order, one neutral prompt rewording and a silence/no-audio baseline where supported. Derive objective controls from editable scores and verify the introduced changes through existing execution tools; [MusICA](https://arxiv.org/abs/2607.06015) supplies a relevant method for score-derived perception tests with nonaudio controls. Preserve original levels and record any gains; common gain is appropriate for contextual substitutions, while a separate controlled level comparison can expose loudness-driven preferences.

Split calibration examples from a held-out passage before adjusting prompts or thresholds. Preserve complete endings rather than depending on random crops. Record defect-detection hits/misses, A/A false positives, agreement with the user's scoped verdicts, order/rewording consistency, abstentions, runtime and actual cost. Cache requests and outputs by audio hashes, exact model/version, prompt, settings and preprocessing; preserve renderer/model/clock, subtune, duration and trim provenance under the existing [audio workflow](../workflows/audio-workflow.md) and [reference boundary](../workflows/publication-boundary.md).

Success means a measured, repeatable reduction in routine listening work while retaining the known negative cases and exposing uncertainty. Adopt only the model/task combinations that pass the local holdout. Scores remain calibrated to this user's examples and purposes; do not combine them into a universal quality score or replace human acceptance of a new arrangement. The broader calibration set remains proposed; the pilots and follow-ups below are implemented and measured.


## Measured OpenRouter pilot: not accepted

On **2026-10-13**, eight requests reached `qwen/qwen3.8-omni-flash` through OpenRouter's reported Alibaba provider. All returned `finish_reason: stop`; the reasoning-enabled requests reported nonzero reasoning tokens. The total **$0.00102047** from individual receipts matched the final key usage endpoint, leaving $9.99897953 of its $10 allowance. This is the measured inference charge, excluding credit-purchase fees. [Structured assessment](../../evidence/audio-assessment-openrouter/assessment.json), [raw responses and receipts](../../evidence/audio-assessment-openrouter/results/response-01.json), and [exact prompts](../../evidence/audio-assessment-openrouter/trial.json) preserve the experiment.

| Probe | Reasoning disabled | Reasoning enabled | Interpretation |
| --- | --- | --- | --- |
| Four seconds of real music | Plausible chiptune/music description; no speech | Not run | API accepted audio and returned a plausible description; not sufficient proof of reliable perception |
| Identical A/A | No difference, high confidence | No difference, high confidence | Both negative controls passed |
| Stationary then moving pulse | No difference, high confidence | No difference, high confidence | Missed the listener-confirmed timbral difference |
| Moving then stationary pulse | No difference, high confidence | No difference, high confidence | Reversing order did not recover the difference |
| Four seconds of all-zero PCM | Described a single sustained musical note | Not run | False positive on verified digital silence |

The changed pair uses the exact same bytes as the [accepted human comparison](composition/follin-contrast.md#reproduce-and-listen), including original levels; the window AC-RMS difference is only about 0.022 dB. The treatment changes pulse step and fallback width, not just a single parameter. The model receives one concatenated WAV with explicit segment times. This pilot does not test separate audio attachments, full endings, note errors, organ character or stereo, and cannot establish model-wide inability. It does establish that the tested setup is unsuitable as a dependable judge of this known audible effect. High-confidence wording did not track correctness. The API's audio-token subfield was zero even though audio was submitted and aggregate prompt usage was billed; retain this reporting ambiguity rather than claiming independent verification of provider preprocessing.

The additional prepared configurations reproduce the reasoning and silence checks without altering prompts:

```sh
python3 scripts/audio_assessment.py build/audio-assessment-openrouter-20261013/reasoning.json --output build/audio-assessment-openrouter-20261013/results
python3 scripts/audio_assessment.py build/audio-assessment-openrouter-20261013/silence.json --output build/audio-assessment-openrouter-20261013/results
python3 scripts/evidence.py verify --group audio-assessment-openrouter
```

The original live silence run used the identical manifest/audio in `build/audio-assessment-openrouter-repro-20261013`; receipts retain that actual path. A fresh preparation now generates all four manifests. Reusing the existing result directory replays cached responses without new charges; creating another result directory permits a separate paid trial and must not be used to bypass the trial bounds. Keep original reference audio and silence WAVs local. Full JSON responses, receipts, prompts and provenance were promoted with the generic evidence tool; no audio or key was promoted.


## Requested Gemini and GPT Audio Mini comparisons

The user requested [Gemini Flash Latest](https://openrouter.ai/~google/gemini-flash-latest) and [GPT Audio Mini](https://openrouter.ai/openai/gpt-audio-mini). On **2026-10-13**, the public model API resolved the Gemini alias to `google/gemini-3.8-flash`; the trial pins that concrete target rather than caching against a moving alias. Gemini requires reasoning, so it used enabled reasoning with low effort. GPT Audio Mini used the baseline request; it does not advertise reasoning support. Both received exactly the same PCM bytes and prompts as the Qwen controls, with temperature zero, 1,200 maximum output tokens and no provider fallback. These are comparisons of bounded supported configurations, not equal-compute benchmarks.

| Model and configuration | A/A control | Known pulse difference, both orders | Digital silence | Requests / measured USD |
| --- | --- | --- | --- | --- |
| Qwen3.8-Omni-Flash, reasoning off and on | Correct twice | Missed all four; high confidence | Invented sustained note, reasoning off | 8 / $0.00102047 |
| Gemini 3.8 Flash, low reasoning | Correct | Missed both; high confidence | Invented hard-rock music with guitars, drums and bass | 5 / $0.00302925 |
| GPT Audio Mini | Abstained | Correct with moving pulse second; abstained with moving pulse first | Abstained, without identifying silence | 5 / $0.00121620 |

All returned completed responses with `finish_reason: stop`, so these results are not output truncation. GPT Audio Mini also abstained on the real-music smoke clip. An abstention is preferable to fabricated detail but does not pass the listening task. Its single correct changed-pair answer does not establish repeatability or order bias without more trials. Gemini and GPT Audio Mini usage records reported audio tokens. The zero PCM was independently decoded from each exact outgoing request payload and checked against the billed request hash; no local wrong-file substitution was found. Provider preprocessing and actual internal audio perception remain unobserved.

Preserved evidence:

- [Gemini assessment](../../evidence/audio-assessment-gemini/assessment.json), [model/alias metadata](../../evidence/audio-assessment-gemini/model-metadata.json), [exact pilot prompts](../../evidence/audio-assessment-gemini/inputs/pilot.json), and [response directory entry](../../evidence/audio-assessment-gemini/results/response-01.json).
- [GPT Audio Mini assessment](../../evidence/audio-assessment-openai-mini/assessment.json), [model metadata](../../evidence/audio-assessment-openai-mini/model-metadata.json), [exact pilot prompts](../../evidence/audio-assessment-openai-mini/inputs/pilot.json), and [response directory entry](../../evidence/audio-assessment-openai-mini/results/response-01.json).

Reproduction with fresh input directories and one cached runner invocation per model:

```sh
python3 scripts/studies/audio-assessment/prepare-trial.py --model google/gemini-3.8-flash --reasoning --reasoning-effort low --output build/audio-assessment-gemini-new/inputs
python3 scripts/audio_assessment.py build/audio-assessment-gemini-new/inputs/pilot.json --output build/audio-assessment-gemini-new/results
python3 scripts/studies/audio-assessment/prepare-trial.py --model openai/gpt-audio-mini --output build/audio-assessment-openai-mini-new/inputs
python3 scripts/audio_assessment.py build/audio-assessment-openai-mini-new/inputs/pilot.json --output build/audio-assessment-openai-mini-new/results
```

Fresh output directories cause paid requests; use the recorded trial directories to review cached results instead. The initial eighteen-request total was **$0.00526592**, about half a US cent, excluding credit-purchase fees. Low price did not compensate for failed or inconsistent controls. The separately authorized follow-up below diagnoses the perception boundary before any further model expansion.

## Measured local SongBench trial

This trial is optional. The normal workbench setup, readiness checks, song builds and tests do not require SongBench, MuQ, model weights or ML dependencies. Follow [optional local model setup](../setup/local-setup.md#optional-local-audio-models) only when deliberately reproducing this experiment; skipping it does not block composition, execution verification or human listening review.

On **2026-10-14**, SongBench scored four anonymous eight-second clips on the **Apple M1 Metal GPU**, followed by one CPU comparison of the original clip. The [assessment](../../evidence/audio-assessment-songbench/assessment.json) records the decision; the [setup receipt](../../evidence/audio-assessment-songbench/setup.json) retains source revisions, asset fingerprints, package versions and machine checks. **SongBench is not accepted as a dependable musical preference judge:** its musicality score favors the stationary-pulse diagnostic over the listener-preferred original. This is one failed project preference anchor, not a model-wide accuracy estimate.

| Probe | Musicality score, 1–10 | Evidence and scope |
| --- | --- | --- |
| `q01`: original moving-pulse passage | 4.3716 | Retained human preference over `q02` |
| `q02`: same-material stationary-pulse diagnostic | 4.7919 | Model preference reverses that human verdict |
| `q03`: original with alternating 0.25-second dropouts | 2.6484 | Lower quality is a stated hypothesis without a separate human verdict |
| `q04`: eight seconds of digital silence | 1.1637 | Negative input control; no absolute musical-quality ground truth |

The original scores higher than the stationary diagnostic for melody, arrangement, vocal, instrumental and mixing, while the diagnostic scores higher for musicality and structure. All seven dimensions fall for the dropout and silence probes. These observations establish score sensitivity on these inputs; they do not establish a useful defect detector. SongBench returns numeric rewards and cannot verbally identify silence or explain a defect. Its vocal dimension has limited meaning for instrumental SID audio. The dropout changes both continuity and level: half the frames become zero, with abrupt boundaries and approximately 2.98 dB lower AC-RMS than the original. No combined score or acceptance threshold was selected after seeing the results.

The [probe preparation script](../../scripts/studies/audio-assessment/prepare-quality-probes.py) preserves the 16–24-second Gauntlet source window, unity gain and exact PCM, verifies source hashes and writes the anonymous cases, local oracle and provenance. All inputs are 44.1 kHz mono PCM16 WAVs. The [local runner](../../scripts/studies/audio-assessment/songbench-local.py) applies the official `librosa.load(..., sr=24000, mono=True)` preprocessing and MuQ hidden layer 6, with no crop or gain change. It loads both checkpoints strictly from local safetensors, disables network access in the inference process and provides explicit `--device mps` or `--device cpu`. Each case runs in a separate worker with a 180-second deadline; the runner rejects WAVs longer than ten seconds and duplicate case IDs and requires a fresh result directory. Reference-derived WAVs and downloaded weights remain in ignored local directories.

Review added complete-PCM and decoded-duration guards plus optional manifest audio fingerprints; freshly generated probe manifests always supply them. New results record wrapper and MuQ configuration hashes. The captured [generator](../../evidence/audio-assessment-songbench/inputs/generator-at-capture.py) and original oracle remain unchanged; the separately [bound oracle](../../evidence/audio-assessment-songbench/inputs/oracle-bound.json) matches every retained WAV, PCM fingerprint and Metal/CPU result input hash. These offline checks preserve the original scores without another inference run.

The four Metal cases took **62.2 seconds wall time**, including process startup and the first inference. Per-case retained times were 32.22, 8.09, 7.39 and 6.60 seconds. Maximum resident set size was **3,079,880,704 bytes, about 2.87 GiB**. Metal reported approximately 1.44 GB of current tensor allocations and 2.30–2.35 GB of driver allocations after inference; these are overlapping measurements of unified memory, not independent quantities to add to RSS. The CPU original took **6.50 seconds**, with **3,160,178,688 bytes, about 2.94 GiB**, peak RSS. Its largest difference from Metal across the seven scores was **0.00000191**, below 0.0001. This checks numerical agreement on one input; it establishes no GPU speedup, repeated A/A reliability or broader ranking accuracy.

PyTorch 2.7.0 was built with MPS support. This session's filesystem sandbox reported MPS unavailable, while a permitted run outside that sandbox reported availability and completed real GPU inference. No automatic MPS-to-CPU fallback was enabled. The [PyTorch MPS documentation](https://docs.pytorch.org/docs/2.7/notes/mps.html) describes the explicit device path. The CPU inference completed and retained its result; the surrounding `time -l` command subsequently returned an error because the sandbox denied its `kern.clockrate` reporting syscall.

The pinned [SongBench source](https://github.com/Tencent/SongBench/tree/9361b55ebff3fffcefbbc9a4653936ae6789c3c8) includes a 100,808,636-byte scoring checkpoint. The [MuQ backbone revision](https://huggingface.co/OpenMuQ/MuQ-large-msd-iter/tree/0562a57814f6f8bbd9fdea0a25921a2fce1a841a) supplies a 1,333,825,096-byte safetensors checkpoint: **1.34 GiB of weights combined**, plus Python dependencies and caches. The isolated environment uses Python 3.11.14, Torch/Torchaudio 2.7.0, MuQ 0.1.0, Librosa 0.11.0 and Transformers 4.46.1; the setup receipt records the complete package map and SHA-256 fingerprints. [SongBench's license](https://github.com/Tencent/SongBench/blob/9361b55ebff3fffcefbbc9a4653936ae6789c3c8/LICENSE.txt) permits academic research and prohibits commercial or production use; [MuQ's weight license](https://github.com/tencent-ailab/MuQ/blob/main/LICENSE_weights) is CC BY-NC 4.0. This installation is a research trial and does not authorize a production assessment service.

With the pinned assets and isolated environment restored, reproduce the four Metal cases in a fresh result directory, or the retained one-case CPU comparison:

```sh
.tools/songbench-venv/bin/python scripts/studies/audio-assessment/songbench-local.py build/songbench-trial-20261014/inputs/cases.json --output build/songbench-trial-20261014/mps-repeat --device mps
.tools/songbench-venv/bin/python scripts/studies/audio-assessment/songbench-local.py build/songbench-trial-20261014/inputs/q01-cpu.json --output build/songbench-trial-20261014/cpu-repeat --device cpu
```

For a fresh audio bundle, run `python3 scripts/studies/audio-assessment/prepare-quality-probes.py --output build/songbench-probes-new` after restoring the locally registered source renders, then pass its `cases.json` to the runner. Keep oracle and provenance as evaluation metadata; only the anonymous WAVs reach the model. These eight-second mono excerpts do not establish full-song structure, complete endings, stereo assessment or general musical judgment. No repeated Metal A/A probe or held-out passage was tested, and the dropout probe lacks a listening verdict. Keep human acceptance and execution verification separate from these experimental scores.

## Elementary perception and presentation follow-up

Measured on **2026-10-14** with anonymous PCM16 WAVs and a withheld oracle. The [control generator](../../scripts/studies/audio-assessment/prepare-controls.py) makes silence at two durations, two steady pitches, a rising sweep, seeded noise, three separated beeps and one offline synthesized sentence. Each request uses the same category/transcription prompt. The declared gate requires all eight categories and the distinctive speech words; it does not grade every descriptive detail or establish musical ability.

| Hosted configuration | Correct controls | Measured USD | Material observation |
| --- | --- | --- | --- |
| Qwen3.8-Omni-Flash, reasoning off | 8/8 | $0.00034067 | Exact speech; calls three beeps four in its explanation despite the correct category |
| Gemini 3.8 Flash, low reasoning | 5/8 | $0.00522300 | Invents speech in both silent clips and describes the second steady tone as changing |
| GPT Audio Mini, reasoning field omitted | 2/8 | $0.0014280 | Identifies beeps and transcribes speech; abstains without valid category JSON on the other six |

[Qwen](../../evidence/audio-assessment-controls/qwen/verified-assessment.json), [Gemini](../../evidence/audio-assessment-controls/gemini/verified-assessment.json) and [Mini](../../evidence/audio-assessment-controls/mini/verified-assessment.json) reports preserve exact content, scores, provider/model identity and cost. All speech transcriptions are correct, which supplies concrete evidence of audio perception on that task. It does not establish fine musical listening. Omitting unsupported reasoning from Mini did not remove its abstentions.

The [offline scorer](../../scripts/studies/audio-assessment/evaluate-controls.py) requires oracle-to-WAV, request-payload and raw-response fingerprints to match before grading. The originally captured oracle lacked audio hashes; [oracle-bound.json](../../evidence/audio-assessment-controls/inputs/oracle-bound.json) adds them from the pre-request provenance after checking the actual WAVs, without changing expected answers. The original oracle and exact generator remain preserved. Verified reports record the scorer hash; its [historical source](../../evidence/audio-assessment-controls/evaluator-at-verification.py) remains reproducible. Current receipt-bound reports for [Qwen](../../evidence/audio-assessment-controls/qwen/receipt-bound-assessment.json), [Gemini](../../evidence/audio-assessment-controls/gemini/receipt-bound-assessment.json) and [Mini](../../evidence/audio-assessment-controls/mini/receipt-bound-assessment.json) additionally bind exact receipt bytes and retain the same grades. Cached suite assessments are revalidated offline against their actual evidence, including changed scorer code; they are not trusted merely because a report exists.

### Isolate prompt and sample rate

The next eight Qwen requests kept model and reasoning unchanged. [Presentation preparation](../../scripts/studies/audio-assessment/prepare-presentation.py) verifies earlier source receipts, constructs a two-by-two silence comparison, and asks only about periodic changes in lead-tone brightness for the musical pairs. The original free-form silence request and the successful category silence request are exact earlier-payload replications.

| Input | Free-form description | Explicit categories |
| --- | --- | --- |
| Four seconds of silence, 44.1 kHz | Invents a sustained musical note again | Correctly reports silence |
| Four seconds of silence, 16 kHz | Invents a sustained electronic tone | Correctly reports silence again |

For the musical question, Qwen reports no difference for original/stationary, reversed stationary/original, identical original/original, and the 16 kHz original/stationary pair. Only the identical-pair answer meets the declared expectation. Every answer reports confidence 0.95. The narrower question therefore did not recover the listener's animation distinction, and confidence is not a useful acceptance threshold here. The narrower cue is an inference from the scoped human verdict; the resampled pair has no separate human acceptance. [Full assessment](../../evidence/audio-assessment-presentation/assessment.json), [withheld expectations](../../evidence/audio-assessment-presentation/inputs/oracle.json), and [raw response entry](../../evidence/audio-assessment-presentation/results/response-01.json) preserve these qualifications.

This single observation per cell supports a prompt-sensitive silence result, not a general causal or reliability estimate. Lowering the sample rate is not demonstrated to improve musical perception. The presentation requests cost **$0.00043682**; the 32-request follow-up cost **$0.00742849**, bringing all 50 hosted requests to **$0.01269441**, excluding credit-purchase fees.

### Reproduce and recheck

Prepare a fresh local bundle, validate all three profiles without network access, then explicitly execute only an authorized bounded trial:

```sh
python3 scripts/studies/audio-assessment/prepare-controls.py --output build/audio-controls-new/inputs
python3 scripts/studies/audio-assessment/run-control-suite.py --inputs build/audio-controls-new/inputs --output build/audio-controls-new
python3 scripts/studies/audio-assessment/run-control-suite.py --inputs build/audio-controls-new/inputs --output build/audio-controls-new --execute
```

Use `--model qwen` to restrict the suite. The shared runner still enforces eight attempts per model, recorded spending bounds, no retries and hash-based paid-request reuse. Explicit manifest `reasoning: null` omits the API field; missing or false preserves the original disabled-reasoning payload. The suite accepts `--oracle` for a separately bound historical oracle. To recheck captured Qwen evidence without any paid request:

```sh
python3 scripts/studies/audio-assessment/evaluate-controls.py build/audio-perception-controls-20261014/qwen/cases.json build/audio-perception-controls-20261013/inputs-local/oracle-bound.json build/audio-perception-controls-20261014/qwen/results --output build/audio-perception-controls-20261014/qwen/recheck.json
python3 scripts/studies/audio-assessment/prepare-presentation.py --output build/audio-presentation-new/inputs
python3 scripts/audio_assessment.py build/audio-presentation-new/inputs/cases.json --output build/audio-presentation-new/results --dry-run
```

Preparation is offline but needs retained sources at the documented capture paths; it is a study reproduction, not a portable production listener. macOS `say` returned successful exit status with zero PCM frames inside the agent sandbox for two tested voices. The generator rejects that output. The measured speech capture used macOS Samantha outside that restriction; provenance retains voice, speed, tool hashes and exact WAV hash. Never treat a successful speech-tool exit as sufficient audio validation.

## Improve assessment without overfitting

Keep this proportional to the musical project: the user explicitly rejects over-engineering. No new evaluation framework or service is planned. Start with one fixed prompt and a few checked examples; only add automation when repeated useful work justifies it. Keep the failed Gauntlet comparison as a regression case, but stop adjusting prompts against it and calling the outcome validation. The following are bounded options for a later capability test, not a new implementation milestone:

1. **Use the strongest existing evidence first.** Score/register checks settle intended notes and scheduled endings; PCM checks settle clipping, duration, silence, discontinuities and level differences. A missing source tail can be flagged by aligned reference energy even when an audio model invents a plausible description. None of those measurements decides whether an intentional arrangement change sounds good.
2. **Find the audibility boundary.** Prepare a single-voice SID probe with absent, moderate and strong modulation, preserving pitch, envelope and level. Verify the intervention through execution. Test one audible property with neutral choices, an uncertain option, A/A and reversed order. An isolated probe diagnoses masking; success there would not establish success in a full mix. Separate audio attachments are another untested presentation option, not an established fix.
3. **Validate transfer before adoption.** Freeze the prompt and criterion, then test a different passage and repeat selected requests. Measure false alarms, misses, order consistency and abstention rather than model confidence. Select a specialist dimension or threshold on calibration examples only; choosing whichever SongBench dimension agrees after seeing the answer would overfit this anchor.
4. **Keep user review consequential.** Once a detector passes a held-out task, use it to flag a specific passage and question. Reserve listening requests for uncertain detections and artistic choices such as organ impression, phrasing and endings. Automate preparation, bounded execution, scoring and evidence retention through the existing tools; avoid maintaining an agent-operated sequence of routine calls.

No additional hosted service is required for this next step. Qwen is eligible for further narrow perception experiments; SongBench is eligible for defect-sensitivity research. Neither is currently authorized by evidence to rank the Bach interpretation's musical success. Keep the Bach workbench trial next in the [study plan](../PLAN.md#bach-toccata-next-workbench-trial), rather than waiting for a universal music evaluator.

**DSPy: defer installation.** Its [audio type](https://github.com/stanfordnlp/dspy/blob/main/dspy/adapters/types/audio.py) supports audio payloads; our OpenRouter route remains untested in DSPy. [GEPA](https://github.com/stanfordnlp/dspy/blob/main/docs/docs/diving-deeper/gepa-in-depth.md) could automate prompt search once we have a stable scoring criterion and enough independent examples. For now, one fixed prompt and a small checked set are sufficient. Any later trial must preserve the existing spending/receipt guards and use explicit training, validation and untouched test passages; reversed or resampled versions of one passage stay together. No optimizer was installed or tested.

## Bach pacing calibration

The user requested a model trial after accepting the faster hybrid opening on 2026-10-14. The concrete question is whether the existing models can recognize the large phrasing change that addressed the listener's complaint. Use Qwen for narrow pairwise observations and local SongBench for an exploratory quality ranking; keep the accepted arrangement unchanged. No new provider, model installation or prompt optimizer is required.

**Protocol fixed before requests:** take the first eight seconds of the previous and driven hybrid renders at original gain, without resampling or time-stretching. Both are the same composition and sound palette but contain different amounts of the score: 11 versus 19 melody onsets, with initial holds of 2.1 versus 0.8 seconds. This measures the audible consequence of changed phrasing, not a uniform BPM change or an aligned same-note comparison. Qwen receives anonymous previous/driven, driven/previous, driven/driven and silence/silence pairs, with the same neutral structured question and explicit eight-second segment boundaries. Its gate requires the expected direction in both orders and correct identical/silence answers. SongBench receives the two separate excerpts, digital silence and an exact driven repeat; musicality is the preselected primary ranking dimension, while all seven dimensions are retained. Silence supplies a negative input control rather than a calibrated musical score.

The expected SongBench direction, driven above previous, is a contextual hypothesis inferred from the full-opening feedback. The user has not separately preferred these eight-second crops. This is one calibration passage, with no independent held-out test; reversed orders and duplicated audio do not create independent musical examples. Any agreement is promising evidence for this bounded question, not permission to delegate musical acceptance. Preserve source, PCM, payload and response fingerprints, costs and the frozen oracle separately from the submitted prompts.

### Measured result and practical use

The [receipt-bound assessment](../../evidence/audio-assessment-bach-pacing/assessment.json) retains the [frozen oracle](../../evidence/audio-assessment-bach-pacing/inputs/oracle.json), [provenance](../../evidence/audio-assessment-bach-pacing/inputs/provenance.json), exact hosted responses and every local score. **Qwen passed three of four cases and failed the declared gate.** It correctly identified the tighter excerpt in both orders and identified silence, but assigned longer gaps to B in the identical driven/driven control. Its explanation attributed the separator before B to that segment, despite the explicit segment bounds; this is its stated rationale, not proof of an internal mechanism. It also described continuous arpeggios/no pauses too strongly for the actual stepped gestures and retained gaps. Treat the coarse pacing direction as promising but retain the false positive and unsupported descriptive details.

| SongBench input | Musicality, preselected primary dimension |
| --- | --- |
| Previous opening, first eight seconds | 4.0543 |
| Driven opening, first eight seconds | 4.1347 |
| Digital silence | 1.1637 |
| Exact driven repeat | 4.1347 |

The driven-minus-previous difference is **+0.08044**, agreeing with the contextual hypothesis but supplying no calibrated effect-size or significance claim. The exact duplicate produced zero differences on all seven dimensions. This is same-input repeatability on this machine, not accuracy or general musical reliability. Other dimensions are retained without selecting a different primary measure after seeing them. The local Metal workers total **34.05 seconds** across four cases, excluding parent overhead; peak process RSS is approximately **2.87 GiB**. The four Qwen requests through Alibaba cost **$0.00026983** in total. No other paid requests were made for this trial.

The first local attempt stopped before returning any score: its guard assumed rational resampling length, while Librosa 0.11.0 computes a floating-ratio ceiling. Eight seconds at 44.1 kHz becomes 192001 samples at 24 kHz; a separate one-second 44.1 kHz input becomes 24001, while a one-second 48 kHz control remains 24000. The [wrapper](../../scripts/studies/audio-assessment/songbench-local.py) now admits the exact upstream computed length alongside rational rounding, preserving cropping/larger-padding and truncated-file rejection. The [pre-inference log](../../evidence/audio-assessment-bach-pacing/failed-preprocessing.log) records the resampling mismatch; it contains no model score. Model checkpoints and all prepared inputs remained unchanged.

**Decision:** use these results as bounded research observations, without changing the accepted Bach opening or adopting either model as a judge. A later musically motivated Bach revision can supply another independently reviewed passage, using the same frozen question and controls. Identical-pair handling remains unresolved; changing to separate attachments is a future presentation hypothesis, not an established fix. Do not spend additional calls tuning against this passage merely to obtain a pass. At the next expanded audition or musical revision, explicitly reassess whether a model can add a useful observation; retain the pre-closure review.

Reproduction uses the existing runners; fresh hosted output incurs paid requests and is a separate deliberate trial. Keep the current result directory to reuse completed requests:

```sh
python3 scripts/studies/audio-assessment/prepare-bach-pacing.py --output build/bach-model-pacing-new/inputs
python3 scripts/audio_assessment.py build/bach-model-pacing-20261014/inputs/qwen.json --output build/bach-model-pacing-20261014/qwen
.tools/songbench-venv/bin/python scripts/studies/audio-assessment/songbench-local.py build/bach-model-pacing-20261014/inputs/songbench.json --output build/bach-model-pacing-20261014/songbench-repeat --device mps
```

The preparation has eight focused tests for source identity, exact PCM windows, A/B reversal, controls, anonymous prompts and payload binding. The [capture assessment script](../../evidence/audio-assessment-bach-pacing/assessment-at-capture.py) retains executable receipt/response/weight checks for this frozen trial. It expects the recorded local paths and a fresh assessment output; it is a retained analysis artifact, not a general model judge. Raw audio remains ignored.

### SongBench has no assessor prompt

Checked against the upstream repository and pinned inference implementation on **2026-10-14**: SongBench's released assessor consumes an audio file (or audio features) and returns seven numeric dimensions. There is no text-instruction input to tune, no request for a written critique, and no way through that interface to specify a SID/game aesthetic. Its README's `Test Prompts` are prompts used to **generate benchmark songs**, not prompts sent to the assessor. [Official README](https://github.com/Tencent/SongBench#-test-prompts), [pinned inference code](https://github.com/Tencent/SongBench/blob/9361b55ebff3fffcefbbc9a4653936ae6789c3c8/eval.py).

The upstream audio path uses Librosa at 24 kHz (mono default), MuQ hidden layer 6, then the scoring head. Our local runner follows that preprocessing and records decoded length and model fingerprints. Clip choice, preprocessing consistency and predeclared score interpretation are the useful controls; better wording cannot correct a domain mismatch. Do not read vocal scores as meaningful for instrumental SID, or interpret an acoustic-realism dimension as an unconditional SID objective. Keep all dimensions, select any decision criterion before examining candidate scores, and never treat a small difference as listener acceptance. Qwen's text prompt can be improved experimentally; SongBench's scoring interface cannot be prompted that way.

## Trap melodic-motion and development calibration

Prepared on **2026-10-14**, following the user’s request to check models against two fresh [Trap observations](composition/daglish-contrast.md#transition-selection-and-listening-observations): mainly a moving melody at source seconds 24–34 and development at 40–52. The [preparation/evaluation script](../../scripts/studies/audio-assessment/prepare-trap-perception.py) uses exact, hash-verified single-source excerpts from the reviewed pairs. It sends one anonymous clip per request, with no source name or human verdict. This avoids the earlier concatenated-pair separator confound; it does not resolve the historical failed A/A and reversed-pair controls.

The [frozen oracle](../../evidence/audio-assessment-trap-perception/inputs/oracle.json) and [provenance](../../evidence/audio-assessment-trap-perception/inputs/provenance.json) retain the prompt and its predeclared criteria. Qwen3.8-Omni-Flash with reasoning enabled and Gemini 3.8 Flash with low reasoning each receive four cases: the two originals, 12 seconds of digital silence and the first two seconds of the later excerpt tiled six times. All retain original sample rate and unity gain. Score only rhythmic-motion classification on the first human example and development on the second; silence must be identified as no music, and the exact loop must be classified as repeating. Require a completed response, valid labels and clip-relative evidence bounds, and review the explanation separately. Agreement and control passes are reported separately. This is calibration on known examples, with no held-out validation or model adoption implied.

SongBench is omitted because its seven quality dimensions do not directly answer these descriptive questions. No new service or optimizer is introduced. Both hosted manifests share one result directory, retaining the existing runner’s eight-POST limit, no automatic retries, $0.01 request reserve and $0.10 cumulative trial admission guard. This is a spending guard rather than a provider billing guarantee.

**Completed after explicit upload authorization, 2026-10-14.** The user approved uploading these clips to OpenRouter; eight requests completed with `finish_reason: stop`, using the unchanged frozen inputs. Qwen’s reported provider was Alibaba and Gemini’s was Google. The [receipt-bound assessment](../../evidence/audio-assessment-trap-perception/assessment.json) retains every answer, scored field, response fingerprint and actual cost; the [completion review](../../evidence/audio-assessment-trap-perception/completion-review.json) records independent binding checks and narrative limits. The [earlier blocked record](../../evidence/audio-assessment-trap-perception/execution-status.json) is preserved as pre-authorization history, not current status.

| Frozen check | Human / controlled expectation | Qwen3.8-Omni-Flash | Gemini 3.8 Flash |
| --- | --- | --- | --- |
| Trap 24–34s: rhythmic motion | Mainly moving melody | Moving melody — agrees | Moving melody — agrees |
| Trap 40–52s: development | Develops during the excerpt | Develops — agrees | Repeats — disagrees |
| Digital silence | No music | No music — passes | Invents an electric-guitar riff and drum-kit groove — fails |
| Exact two-second loop, repeated six times | Repeats | Repeats — passes | Repeats — passes |

Qwen matches **2/2 human observations and 2/2 controls**, passing this calibration. Gemini matches **1/2 human observations and 1/2 controls**, failing it. Total measured inference cost is **$0.00466575**: Qwen **$0.00152550**, Gemini **$0.00314025**. No requests were repeated or prompts adjusted to obtain agreement.

**Decision:** prefer Qwen for experimental, short single-clip descriptions of melodic motion and local development. Its result is promising for this task, not validation of taste, instrument identification, exact event timing, wrong-note detection or whole-song quality. This is still two known passages from one work, with no independent held-out human test. The combined change of task, prompt and presentation prevents attributing the improvement to any one factor. Gemini’s silence fabrication rules out dependable use of this configuration here. Keep its failure and the older pairwise failures; do not optimize the music to match model prose.

Evidence spans passing numeric bounds are not verified temporal localization. Descriptions of pads, drums, absence of percussion or a particular pitch contour remain unverified unless independently grounded; only the declared labels and exact controls determine the calibration result. The next useful checkpoint is an independently reviewed passage with the same frozen prompt and controls, before broader eligibility. SongBench remains a separate defect/quality-score experiment and does not inherit this result.

Verify or replay cached requests with the same frozen bundle and shared result directory:

```sh
python3 scripts/studies/audio-assessment/prepare-trap-perception.py --output build/trap-model-perception-20261014 --verify
python3 scripts/audio_assessment.py build/trap-model-perception-20261014/inputs/qwen.json --output build/trap-model-perception-20261014/results
python3 scripts/audio_assessment.py build/trap-model-perception-20261014/inputs/gemini.json --output build/trap-model-perception-20261014/results
python3 -m json.tool build/trap-model-perception-20261014/assessment.json
```

If rebuilding the inputs after cache loss, first recreate the [Trap transition publication](composition/daglish-contrast.md#transition-selection-and-listening-observations), then prepare into a fresh directory and verify against the retained original hashes. A fresh result directory would permit fresh paid calls; it must not be used to bypass the recorded trial limits or approval boundary. Raw audio stays ignored. The evaluator’s `--assess` mode creates a fresh assessment only after the eight initial responses exist; review the retained result instead of overwriting it. Human musical observations remain authoritative.


## Ghostbusters single-clip speech recognition

On 2026-10-15, the [Ghostbusters study](composition/ghostbusters-preparation.md#planned-bounded-speech-recognition-check) reused the exact elementary-category prompt and Qwen configuration from the earlier verified controls: `qwen/qwen3.8-omni-flash`, reasoning disabled, temperature zero and 1,200 output tokens. Four single clips were submitted anonymously through OpenRouter, served by Alibaba: the independent opening, exact retained silence, exact retained ordinary speech, and original opening. The rendered openings were cropped to 4.45 seconds at unity gain and converted to mono 16 kHz PCM16; no title, expected transcription, user verdict or source/candidate identity appeared in the requests. The user explicitly approved this four-clip upload before requests ran.

| Case | Observed result | Permitted interpretation |
| --- | --- | --- |
| Exact digital silence | `silence`, empty transcript | Control passes |
| Known ordinary speech | `speech`, all eight words of “The blue lantern is beside seven wooden boxes.” | Control passes |
| Independent opening | `speech`, “Ghostbusters! [laughter]” | Descriptive transcription only |
| Original opening | `speech`, “Ghostbusters. [laughter]” | Descriptive transcription only |

Both controls pass. The two opening transcripts agree apart from punctuation, supporting recognition of the same phrase in this specific pair. They have no independent transcription oracle and do not establish equal intelligibility, naturalness, PCM identity or general musical judgment. The listener separately accepted recognizable speech and preserved musical sound/phrasing, then accepted the ending as “seems identical to me”; that feedback was withheld from the requests. Previous pairwise and pulse-animation failures remain relevant and are not superseded by this narrow result.

Four completed requests cost **$0.00017082** in total, with no retries or prompt changes. The [offline assessment](../../evidence/ghostbusters-speech-model/assessment.json) binds the controls and descriptive observations to [frozen cases](../../evidence/ghostbusters-speech-model/cases.json), [preprocessing provenance](../../evidence/ghostbusters-speech-model/provenance.json), raw responses and actual cost receipts. Audio remains local. The [preparer](../../scripts/studies/ghostbusters/prepare-speech-model-check.py) recreates anonymous crops from the full published WAVs and exact retained controls; use the existing bounded runner with the same result directory to reuse billed responses.

Reproduce the offline preparation and assessment using the retained controls and completed full-title run. Choose fresh preparation/assessment destinations when rebuilding; preserve the existing `results` directory for cached paid responses. Do not rerun requests merely to verify archived evidence.

```sh
python3 scripts/studies/ghostbusters/prepare-speech-model-check.py --reference build/ghostbusters-listening/reference.wav --candidate build/ghostbusters-listening/reconstructed.wav --run build/ghostbusters-independent-full/run-executed.json --output build/ghostbusters-speech-model-check-new
python3 scripts/studies/ghostbusters/assess-speech-model-check.py --inputs build/ghostbusters-speech-model-check --results build/ghostbusters-speech-model-check/results --output build/ghostbusters-speech-model-recheck/assessment.json
python3 scripts/evidence.py verify --group ghostbusters-speech-model
```

The [offline scorer](../../scripts/studies/ghostbusters/assess-speech-model-check.py) recomputes audio/request bindings, verifies complete unique responses and costs, and grades only the two controls. Three [focused guards](../../tests/ghostbusters_speech_model_check_test.py) cover false silence transcripts, missing speech words, truncated responses and hash/payload tampering. A failed control disables use of the descriptive observations; fluent matching transcripts cannot override it.

**Decision:** retain Qwen as an experimental supporting tool for short recognizable speech, conditional on passing task-specific controls. No arrangement change follows from this trial. SongBench is not used because its quality scores cannot answer the transcription question. Reassess on a new speech source or changed model/prompt/preprocessing before broader use; musical acceptance, instrument balance and subtle articulation remain human judgments. This result satisfies Ghostbusters’ pre-closure model-assistance review without qualifying either model as a musical judge.


## Axel F descriptive follow-up: silence failure

On 2026-10-16 the user approved four specific anonymous 10.5-second uploads to OpenRouter/Qwen: Hülsbeck’s original 9.5–20s passage, the first 10.5s of our kick/snare audition, digital silence, and the first 2.1s of the master clip tiled five times. The [preparer](../../scripts/studies/axel-f/prepare-model-perception.py) retains the exact Trap prompt and reasoning-enabled Qwen configuration, original mono PCM16 at 44.1 kHz and unity gain. The [frozen oracle](../../evidence/axel-f-model-perception/inputs/oracle.json) scores only the controls; title, source identity and listener preference were withheld. This changes the passage set, not the prompt. Different key, tempo, chip model and accompaniment preclude isolating causes of preference.

The [receipt-bound assessment](../../evidence/axel-f-model-perception/assessment.json) verifies four completed Alibaba-served requests, exact input/payload/response fingerprints and **$0.00179180** total cost. Qwen classified both musical clips as rhythmic motion from melody and percussion with predominant repetition. It passed the exact-loop control but **failed digital silence**, describing a sustained high tone. The exact outgoing silence payload was decoded independently: all 926,100 PCM bytes are zero. All responses completed and parsed with bounded timestamps; fluent descriptions are insufficient evidence of perception.

**Decision:** no descriptive result from this batch is eligible to guide the arrangement. The earlier Trap pass remains a scoped result, but its configuration did not reliably transfer to this fresh set; do not cite it as general eligibility for rhythmic-development descriptions. Retain both results, make no additional calls to tune against this failure, and continue the [Axel F correction](../../songs/axel-f/arrangement-review.md#master-derived-percussion-phrase-contrast) from human feedback and executed source evidence. Reassess only at a materially different, useful checkpoint; no further paid trial is authorized by this four-request approval.

Recreate inputs with `python3 scripts/studies/axel-f/prepare-model-perception.py --output build/axel-f-model-perception-new`. To inspect the billed cache, use `python3 scripts/audio_assessment.py build/axel-f-model-perception-20261016/inputs/qwen.json --output build/axel-f-model-perception-20261016/results`; a fresh results directory would make paid requests and requires new authorization. [Complete prompts and response receipts](../../evidence/axel-f-model-perception/inputs/qwen.json) are retained without audio or credentials.
