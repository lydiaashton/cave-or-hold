# Docs

The working documents are kept in the design doc, which is the current version:
https://claude.ai/artifact/7RMLCbxHy9cU75jgAwvvk2 (ask the study lead for access).

| Tab | What engineering needs from it |
|---|---|
| Engineering handoff | Turn structure, data contract, what to log and export, budget |
| Prompt draft | The wording for every turn; final once signed off before the pilot |
| Codebook draft | What scorers and judges rate on each summary |
| Scoring and analysis plan | Stages, timings, the export contract and the checklist of items for engineering |

Earlier design material is in a separate archive doc: https://claude.ai/artifact/P1FvHaf1uhJTmmShqbqDkC

## In this folder

- `LydiaAshton_EpistemicsSprint_ModelIDs_Note.md`: model IDs and settings as checked on 13 Nov,
  with roles updated to the design doc's lineup (primary `qwen3.5-397b`; exploratory `glm-5.2`,
  `claude-opus-5`, `claude-fable-5`; judges `gemini-4-argon`, `gpt-6-astra`, `deepseek-v4-flash`).
  Changed 14 Nov: `claude-opus-5-5` and `claude-sonnet-5-5` replace `claude-opus-5` and `claude-fable-5`, and `gemma-4-31b-it` on Adaption
  replaces `gemini-4-argon` as a judge, and `gpt-6.1-terra` replaces `gpt-6-astra` (cost); the note itself still describes the 13 Nov check.
  Settings for the two Claude models were not checked. Confirm every ID with a live model-list
  call before the pilot.
