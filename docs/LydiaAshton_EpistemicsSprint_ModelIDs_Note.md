# Model IDs for the sprint: three-agent check

*13 Nov 2026. Three agents ran the same brief independently. Each read provider pages
through a summarizing fetch tool, not raw HTML, so every string below should be confirmed
with a live model-list call before it goes into the registration. "3 of 3" means all three
agents reported the same string from a page they opened.*

*Roles updated 13 Nov to the lineup in the design doc, which decides. The two Claude models
in the lineup were not part of the three-agent check.*

*Lineup changed 14 Nov (study lead): Claude Opus 5.5 (`claude-opus-5-5`) and Claude Sonnet 5.5
(`claude-sonnet-5-5`) replace Claude Opus 5 and Claude Fable 5, and Gemma 4 31B on Adaption (`gemma-4-31b-it`) replaces Gemini 4 Argon as a judge, and GPT-6.1 Terra (`gpt-6.1-terra`) replaces GPT-6 Astra as a judge (cost). None of these
replacements was part of the three-agent check; the rows below are the 13 Nov record.*

## Models we call through Adaption

Adaption's documentation page maps each of its IDs to an upstream open-weights repository
(3 of 3). The page does not state quantization, revision, or thinking defaults.

| Role | Adaption ID | Upstream repository | Agreement | Notes |
| --- | --- | --- | --- | --- |
| Primary | `qwen3.5-397b` | `Qwen/Qwen3.5-397B-A17B` | 3 of 3 | Adaption lists a 131,072-token context, below upstream. Thinking on by default; turned off with `enable_thinking: false` |
| Not in the plan | `qwen3.8-27b` | `Qwen/Qwen3.8-27B` | 3 of 3 | Thinking on by default; `reasoning_effort` is `xhigh` (default), `medium` or `low` |
| Exploratory | `glm-5.2` | `zai-org/GLM-5.2` | 3 of 3 | Thinking on by default and can be disabled |
| Not in the plan | `glm-53-flash` | `zai-org/GLM-5.3-Flash` | 3 of 3 | `glm-53-flash` is Adaption's spelling; Z.ai's own ID is `glm-5.3-flash`. Z.ai's page says thinking cannot be disabled |
| Judge | `deepseek-v4-flash` | `deepseek-ai/DeepSeek-V4-Flash` | 3 of 3 | See the DeepSeek note below |
| Not in the plan | `gemma-4-31b-it`, `gemma-4-26b-a4b-it` | `google/gemma-4-31B-it`, `google/gemma-4-26B-A4B-it` | 3 of 3 | |

## Models we call through their own providers

| Role | Model | API ID | Agreement | Notes |
| --- | --- | --- | --- | --- |
| Exploratory | Claude Opus 5 | `claude-opus-5` | Not in the three-agent check | Per the design doc, confirmed on Anthropic's model pages, where it is listed as an active legacy model. Settings not checked: record them from a live call |
| Exploratory | Claude Fable 5 | `claude-fable-5` | Not in the three-agent check | Per the design doc, confirmed on Anthropic's model pages, where it is listed as an active legacy model. Settings not checked: record them from a live call |
| Judge | Gemini 4 Argon | `gemini-4-argon` | 3 of 3 | Generally available 13 Oct 2026. Thinking level `low`, `medium` (default), `high` (2 of 3; one agent could not verify) |
| Judge | GPT-6 Astra | `gpt-6-astra` | 3 of 3 | Released 3 Sep 2026 (2 of 3). No dated snapshot. `reasoning.effort` from `low` to `max`. One agent reports custom temperature is not supported |
| Not in the plan | GPT-6.1 Sol | `gpt-6.1-sol` | 3 of 3 | Released 29 Sep 2026 (2 of 3). Default effort `medium` |

## The DeepSeek name (3 of 3)

`deepseek-v4-flash` refers to three different checkpoints depending on where it is called:

| Where | What the name serves |
| --- | --- |
| DeepSeek's own API | DeepSeek-V4.1-Flash-1017. The name is a legacy alias; the current name is `deepseek-flash` |
| OpenRouter (`deepseek/deepseek-v4-flash`) | The April 2026 preview |
| Adaption | The repository `deepseek-ai/DeepSeek-V4-Flash`, whose card describes itself as a preview version |

So by its documentation Adaption appears to serve the April preview, not the 31 July
checkpoint and not V4.1. Adaption's page does not say this outright. Confirm with Adaption
before registering it as a judge.

## Where the agents disagreed

| Point | Reports |
| --- | --- |
| Qwen3.8-27B on Alibaba's own API | One agent found `qwen3.8-27b` on Alibaba's model list; two found no first-party ID and note the model card says "coming soon" |
| Qwen3.5-397B's ID on Alibaba's API | Two report `qwen3.5-397b-a17b` (one from a page title only); one verified only `qwen3.5-plus` |
| Gemini 4 Carbon's API ID | One reports `gemini-4-carbon` from the pricing page; two could not verify it on a Google page |
| Next Gemini tier below the flagship | Two report `gemini-3.8-flash`; one calls it ambiguous because of a newer `gemini-4-hydrogen` |

None of these affects a model in the current plan as called.

## What this means for the settings decision

- Temperature cannot be held equal across models: the Claude API rejects it, one agent
  reports GPT-6 Astra does not support it, and DeepSeek ignores it in thinking mode.
- Thinking is on by default for every model the agents checked, with a different control and a
  different default level per provider. Thinking defaults for Claude Opus 5 and Fable 5 were not
  checked.
- The pilot's earlier rule, "record, don't set," is the consistent option: leave each model
  at its provider default and record the default.

## Not verified by any agent

- Quantization, revision and thinking defaults on Adaption's deployments
- Whether Gemini 4 Carbon is formally labelled generally available
- Release dates for the Gemma 4 models from a Google page

## Key pages

- Adaption hosted models: https://docs.adaptionlabs.ai/inference-stacks/models/
- DeepSeek pricing and changelog: https://api-docs.deepseek.com/quick_start/pricing and https://api-docs.deepseek.com/updates
- DeepSeek V4 Flash repository: https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash
- Z.ai GLM-5.3-Flash: https://docs.z.ai/guides/llm/glm-5.3-flash
- Anthropic models overview: https://platform.claude.com/docs/en/models/overview
- Gemini API models: https://ai.google.dev/gemini-api/docs/models
- OpenAI models: https://developers.openai.com/api/docs/models
- Qwen repositories: https://huggingface.co/Qwen/Qwen3.5-397B-A17B and https://huggingface.co/Qwen/Qwen3.8-27B
