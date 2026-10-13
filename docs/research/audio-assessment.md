# Automated musical assessment for SID

Research checked: **2026-10-13**. This assessment concerns models that consume recorded music and return critiques, ratings or preferences. All model results below are published author claims or independent benchmark findings, **not project measurements**. The bounded OpenRouter pilots below are measured project evidence for Qwen3.8-Omni-Flash, Gemini 3.8 Flash and GPT Audio Mini; the other candidates remain untested here. Eighteen authorized audio requests cost $0.00526592 in total. No local model was installed.

## Recommendation and scope

**None of the three tested OpenRouter configurations is accepted as a dependable project listener.** Qwen3.8-Omni-Flash and Gemini 3.8 Flash passed identical-pair controls but missed the listener-confirmed pulse difference and hallucinated music in digital silence. GPT Audio Mini correctly detected the difference in one order but abstained on the reversed pair and other controls. Keep the local signal/execution checks and human artistic judgment. Before expanding model selection, verify end-to-end perception using unmistakable synthetic sound/silence controls and, if necessary, a direct-provider comparison. Do not infer a model-wide failure or a routing defect from this small test.

Keep one hosted gateway for now. OpenRouter permits model comparisons without separate provider accounts. **MuseCritic**, **CMI-RM**, **SongBench** and direct GPT-Audio-1.5 remain researched alternatives rather than required services. Only add one if a measured capability gap and a bounded experiment justify it.

The intended benefit is fewer routine listening requests: identify likely missing material, compare timbral animation and phrasing, and bring specific uncertain passages to the user. Separate known-source correctness from musical success. A trace or preserved score can establish that a note is absent; it cannot establish that an intentional omission improves an arrangement. Likewise, a musically preferred candidate need not reproduce the source. Keep [execution verification](validation/verification.md), [matched audio comparisons](../workflows/audio-comparisons.md) and the listener's verdict as distinct evidence.

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

[CMI-RM inference](https://raw.githubusercontent.com/Haiwen-Xia/CMI-RewardBench/main/baselines/inference.py) explicitly supports CPU/FP32 and 30-second chunks: 0.7B implies approximately 2.8GB of weights, not peak RAM. [SongBench inference](https://raw.githubusercontent.com/Tencent/SongBench/main/eval.py) falls back to CPU, includes a MuQ backbone and processes the whole WAV. Both are plausible optional short-clip, batch-one CPU trials; speed, peak memory and MPS support remain unmeasured here. All three assessors preprocess to mono by default, so their standard paths cannot assess dual-SID stereo imaging.

## What the evidence establishes

**OpenAI** documents actual audio input for GPT-Audio-1.5 through Chat Completions, allowing recorded WAV comparisons with text responses. Its positioning is voice-oriented; the inspected documentation does not establish musical judgment equivalent to the specialist models. [GPT-Realtime-2.1](https://developers.openai.com/api/docs/models/gpt-realtime-2.1) adds configurable reasoning in a voice-agent workflow, but no inspected music benchmark proves that the extra session machinery improves this task. Start with the simpler [file-audio chat interface](https://developers.openai.com/api/docs/guides/audio-chat-completions), testing the sound itself rather than a speech transcript.

**MuseCritic** produces a critique followed by coherence, musicality, memorability, structural clarity and vocal naturalness scores. Its authors report **71.35% pairwise preference accuracy on 733 MusicArena pairs**. This is closer to useful musical feedback than generic captioning, but it remains imperfect and trained around generated songs with vocals. Explanations can suggest where to listen; their fluency does not verify the claimed defect. [MuseCritic paper](https://arxiv.org/abs/2608.11755).

**CMI-RM** is a reward model, not a conversational listener. Its authors report **MusicEval musicality SRCC 0.8266** and **78.2% CMI-Pref musicality preference accuracy**, compared with Gemini 3 Pro's 65.8% in their evaluation. Its separate alignment output helps distinguish compliance with an instruction from enjoyable music. These scores justify a ranking trial, not an inferred ability to locate a missing note or explain organ character. [CMI-RewardBench paper](https://arxiv.org/abs/2603.00610).

**Qwen3.8-Omni-Flash** is a substantially newer candidate than Qwen2.5-Omni. Table 4 of its report gives **72.6 MuchoMusic-RUL, 75.8 HumMusQA and 50.6 MusTBench**, against Gemini 3.8 Flash's 53.7, 71.2 and 40.3 respectively. These are audio-input/text-output understanding tasks, not expert musical-quality ratings. The [release registry](https://www.alibabacloud.com/help/en/model-studio/newly-released-models) dates the API to September 17. Its hosted access makes it practical for a paid trial without local GPU setup. [Qwen3.8 technical report](https://arxiv.org/html/2609.25611v1).

**SongBench** scores vocal, instrument, melody, structure, arrangement, mixing and musicality using expert song annotations. The paper reports utterance-level musicality **SRCC 0.829**, versus SongEval's 0.593. More relevant to subtle comparisons, within-generator A/B accuracy is **62.24% for Suno and 64.13% for LeVo**, while the easier inter-generator comparison reaches 85.57%. Those differences argue against extrapolating broad model-ranking success to reliable discrimination between two closely related SID edits. Its instrument dimension includes realism and acoustic fidelity, which may penalize deliberate chip timbres. [SongBench paper](https://arxiv.org/html/2604.25937v1).

**MOSS-Music-8B-Instruct** reports **80.38 average accuracy across eight music QA/classification benchmarks**, compared with MusicFlamingo's 73.87 and Qwen3-Omni's 66.75 under its developers' protocol. Isolated-note NSynth results are reported separately, including 86.94% pitch accuracy. Instruct outperforms Thinking on the headline QA suite. Caption assessments are preliminary GPT-5.4 judgments; chord-transcription benchmark results are not yet supplied. Music QA leadership therefore supports trying it for descriptions, without establishing reliable polyphonic note checking or aesthetic critique. [Official evaluation](https://github.com/OpenMOSS/MOSS-Music).

**CloudEar** combines learned perception, signal diagnostics and prompt/instrument alignment. Its authors report **81.79% CMI-Test musicality preference accuracy and 76.57% MusicArena accuracy** in their own evaluation. It samples random 30-second clips and uses approximately 7,000 hours of in-house human-rated training music, mainly English generated songs. Random cropping is poorly suited to guaranteeing coverage of a specific ending; the paper leaves explanations of preference causes to future work. Its results cannot be directly compared with other papers' differently sampled evaluations. [CloudEar paper](https://arxiv.org/html/2610.11672v1).

## Perception and benchmark cautions

No candidate has passed project calibration. **The three OpenRouter pilots were not accepted**; other candidates remain unvalidated on SID audio. Vocal expectations, acoustic realism, production norms and genre priors may prefer smoother contemporary audio over intentional pulse motion, arpeggiation, noise attacks or sparse three-voice arrangements. “Organ-like” is a listener impression, not proof of instrument identity. The [instrument-grounding audit](https://arxiv.org/html/2606.31338v1) explicitly tests related keyboard candidates—accordion, organ, piano and synthesizer—and candidate-order variation, offering a useful design for testing this distinction.

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

Split calibration examples from a held-out passage before adjusting prompts or thresholds. Preserve complete endings rather than depending on random crops. Record defect-detection hits/misses, A/A false positives, agreement with the user's scoped verdicts, order/rewording consistency, abstentions, runtime and actual cost. Cache requests and outputs by audio hashes, exact model/version, prompt, settings and preprocessing; preserve renderer/model/clock, subtune, duration and trim provenance under the existing [audio workflow](../workflows/audio-workflow.md) and [reference boundary](../../AGENTS.md#public-repository-boundary).

Success means a measured, repeatable reduction in routine listening work while retaining the known negative cases and exposing uncertainty. Adopt only the model/task combinations that pass the local holdout. Scores remain calibrated to this user's examples and purposes; do not combine them into a universal quality score or replace human acceptance of a new arrangement. The broader calibration set remains proposed; the eighteen requests in the pilots below are implemented and measured.


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

Fresh output directories cause paid requests; use the recorded trial directories to review cached results instead. The eighteen-request total is **$0.00526592**, about half a US cent, excluding credit-purchase fees. Low price did not compensate for failed or inconsistent controls. Stop here rather than expanding a model panel before diagnosing the perception boundary; no further paid run is implied by this research recommendation.
