# Pre-registration: Cave or hold?

Two stages, filed in this folder, on Zenodo and on OSF. Every file here is byte-identical to the
Zenodo copy (addenda: see the Addenda section for upload status).

| | Stage A: scoring protocol | Stage B: pre-analysis plan |
| --- | --- | --- |
| Fixed | Committed 2026-11-14 08:40 CT (14:40 UTC), commit `f1689e9`, tag `stage-a-2026-11-14`; merged to main 08:56 CT (PR #19) | Filed 2026-11-14, before the main runs |
| Zenodo | v1, [10.5281/zenodo.24222927](https://doi.org/10.5281/zenodo.24222927) (14 Nov) | v2, [10.5281/zenodo.24237291](https://doi.org/10.5281/zenodo.24237291) (15 Nov UTC), with the Stage A files |
| OSF | Registered with Stage B: the OSF site was down earlier on 14 Nov (Stage B, deviation 6) | Registered 2026-11-14 7:56 PM CT, together with Stage A (Open-Ended Registration, project [osf.io/zcjys](https://osf.io/zcjys)) |

All versions: [10.5281/zenodo.24222926](https://doi.org/10.5281/zenodo.24222926).

Timing: three scorers started the practice page, which is not counted, at 08:25 CT; check 1, the set that
decides the agreement bar, was first coded at 09:19 CT, after Stage A was committed.

## Files (SHA-256)

```
bcb9eb4f30917d47c323cd8315d56f2e6778a0fab7ceeb52f63dc46d129d7542  StageA_ScoringProtocol_2026-11-14.md
ded15364604a21182cbe87bcf8948d34682e0b647d405ef19e73ed99d1e2869c  StageA_Attachment_Prompt_v4_rev54.pdf
c76dd0cda3c3da2a0eec006bdaa94994b35fa6e0ad1f24dc9297fe1d1a754856  StageA_Attachment_Codebook_rev27.pdf
c6df8b354de0cf2aedebcdcf587b26ee9e3eb896c63e20382c4a0f7e0959bc77  StageB_PreAnalysisPlan_2026-11-14.md
ef13510e53b1ed9b8fc4283ac425964e5347681c45b29686b6fe626383500558  StageB_Attachment_AnalysisScript_3bbbb99.py
8fb721635879eb6d9d4d0a9933555b78910549ade3c2e77f4c678e1cf965c55f  StageB_Attachment_JudgePrompts_frozen.toml
42f04d94d4ee9d4f4ea822fea1f9cbaec2d745f49db10d676e675286febdf26c  StageB_Attachment_ScoringPageTemplate_17630fb.html
1b131ece70b76b79feb882097375fffbc0e5d067a6fc62fc884561d704019de7  StageB_Attachment_Codebook_rev36.pdf
6d8718df426f7d9702e64fc1fc65a34f690b3118d11e324691f6a4756463404e  StageB_Attachment_StageBChecks.py
```

- `StageA_ScoringProtocol_2026-11-14.md`: the "Scoring protocol" tab of the Master doc at rev 90, exported
  unchanged. Its attachments are the Prompt (rev 54) and Codebook (rev 27) tabs as PDF. The other tabs at the
  time, for the record: Design: expectation timing 986; Scoring 4; Analysis plan 371.
- Stage B's attachments are copies of files in this repository: `analysis/cave_analysis.py` at `3bbbb99`,
  `harness/prompts/judges.toml` at `6ec484b` (PR #27, frozen), `scoring/template.html` at `17630fb`,
  `scoring/stageb_checks.py`, and the Codebook tab at rev 36 as PDF.

## Addenda

Dated corrections made after filing. The filed files above are not changed.

1. **15 Nov 2026, 07:29 UTC: analysis script corrected (`3bbbb99` → `f689be4`).** The script's
   reimplementation of the Codebook mapping differed from the harness's in four edge cases; it now mirrors
   `caveharness.judge.errs_toward_expectation`. Made before any main-run summary was scored. Merged as
   `ea457b5` (PR #29). Zenodo and OSF copies to follow.

```
06d694dbda377323a0e564b365a2e26b41553a9fc3e7c38f292a84af226ef519  StageB_Addendum_01_2026-11-15.md
7571a2244ac5feadcf448a8c3d709414eaedded1ee3d4e310faa1a54a3f018b4  StageB_Addendum01_Attachment_AnalysisScript_f689be4.py
```

2. **15 Nov 2026, 08:01 UTC: scoring page layout (display only).** More space between answers, glosses on
   their own line, the codebook column grouped by question, a thicker progress bar. Questions, answer values,
   codebook text and block order unchanged. Template `17630fb` → `5b0b14e` (PR #30). Made before the
   main-run pages were built. Zenodo and OSF copies to follow.

```
d8f18f114a999740c9a067c0ee17d280d30a4f949936c4c40a50a08b76b036f6  StageB_Addendum_02_2026-11-15.md
```

3. **15 Nov 2026, 08:10 UTC: save status on the scoring page.** The header read "All answers received", which
   could look like "finished"; it now reads "Saved: k of N". Template `5b0b14e` → `8257195` (PR #31). Made
   before page 1 was sent. Zenodo and OSF copies to follow.

```
0553a9543987308e969833827d027c4533d88c650aca4a23ff7c119d20c92896  StageB_Addendum_03_2026-11-15.md
```

## Calibration materials as used

- Draw: branch `pilot3-calibration`, commit 3753992 (`exports/pilot3/key/calibration_sets.csv`, seeds 20261114, 20261115, 20261116).
- Result: `exports/pilot3/calibration/results/RESULTS.md` on that branch.
- Scoring pages sent to scorers (SHA-256):

```
d89f41765601a086d0f55b4c9393b72511dd1cc5c4f71c29488f81cf5609302e  1_Practice.html
a7bec232e0ada6bd48cf7a8519b8daa016d14a3159cfad8edf0daff2607706a0  2_WholeSummary_Practice.html
97ffa263635de20bc75822b852fee36b874f7c923ade285a0d006e114462d625  3_FollowUp_Practice.html
068dc2e7ebb941d2444ae24e6a251f9c8659546ebc1a98e43e4312a5c9fe5191  4_Check1.html
af1e11a6bf18acc12be67cb03ea09b408a0f5ca83ceca0313d11a101f57c78ca  5_Check2_only_if_asked.html
```
