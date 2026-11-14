# Pre-registration, Stage A

**Committed:** 2026-11-14 14:40 UTC (14 Nov 2026), before any calibration agreement was computed and before any main run.

`StageA_ScoringProtocol_2026-11-14.md` is the Stage A registration ("Scoring protocol" tab of the study's Master doc, rev 90), exported unchanged.

## Attachments

The registration is filed in this repository only.

It cites two tabs of the Master doc as attached: the Prompt and the Codebook. Both are filed here as PDF
exports, added 2026-11-14 15:04 UTC. Each is the same Master doc revision as when the registration was
committed, so the text is what the registration referred to.

| File | Tab | Master doc revision | SHA-256 |
| --- | --- | --- | --- |
| `StageA_Attachment_Prompt_v4_rev54.pdf` | Prompt (prompt v4; the harness file is `harness/prompts/turns.toml`) | 54 | `ded15364604a21182cbe87bcf8948d34682e0b647d405ef19e73ed99d1e2869c` |
| `StageA_Attachment_Codebook_rev27.pdf` | Codebook | 27 | `c76dd0cda3c3da2a0eec006bdaa94994b35fa6e0ad1f24dc9297fe1d1a754856` |

The other tabs of the Master doc are not part of Stage A. For the record, their revisions when the
registration was committed: Design: expectation timing 986; Scoring 4; Analysis plan 371. The full analysis
plan is filed in Stage B.

## Calibration materials as used

- Draw: branch `pilot3-calibration`, commit 3753992 (`exports/pilot3/key/calibration_sets.csv`, seeds 20261114, 20261115, 20261116).
- Scoring pages sent to scorers (SHA-256):

```
d89f41765601a086d0f55b4c9393b72511dd1cc5c4f71c29488f81cf5609302e  1_Practice.html
a7bec232e0ada6bd48cf7a8519b8daa016d14a3159cfad8edf0daff2607706a0  2_WholeSummary_Practice.html
97ffa263635de20bc75822b852fee36b874f7c923ade285a0d006e114462d625  3_FollowUp_Practice.html
068dc2e7ebb941d2444ae24e6a251f9c8659546ebc1a98e43e4312a5c9fe5191  4_Check1.html
af1e11a6bf18acc12be67cb03ea09b408a0f5ca83ceca0313d11a101f57c78ca  5_Check2_only_if_asked.html
```

Stage B (N, the negligible difference, the frozen judge prompts, the analysis script, deviations) follows before the main runs.
