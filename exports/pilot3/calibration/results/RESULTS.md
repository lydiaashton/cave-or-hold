# Calibration result, 14 Nov 2026 (pilot-3 summaries)

Recomputed from the Google Sheet "Cave or hold – scorer answers" (downloaded 14 Nov, 17:10 CT) with
`scoring/combine_scorer_files.py --ignore-codes TEST --skip-unfinished` and
`scoring/calibration_agreement.py --round 1 --batch "Calibration: check 1" --panel S1,S2,S3`
(branch calibration-agreement; bootstrap 2,000 draws, seed 20261114). Scorers by code only.
Check-1 answers arrived 09:19 to 10:53 CT; all five scorers coded all 27 summaries.

## The registered gate: check 1, panel S1, S2, S3 (design-blind), 27 summaries

| Question | AC1 | 95% interval | Fleiss' kappa | Raw agreement | Bar |
| --- | --- | --- | --- | --- | --- |
| Q1 claim | 0.82 | 0.68 to 0.95 | 0.57 | 0.84 | target met |
| Q2 uncertainty | 0.91 | 0.77 to 1.00 | 0.89 | 0.95 | target met |
| Q3 emphasis (not in the bar) | 0.55 | 0.26 to 0.78 | 0.14 | 0.70 | |
| Q4 next steps (not in the bar) | 1.00 | 1.00 to 1.00 | 1.00 | 1.00 | |

Bar (Stage A): Gwet's AC1 on Q1 and Q2 separately, target 0.80, floor 0.667. Both met on the first
check set, so no second set was coded. Full output: `agreement_check1_panelS1S2S3.txt`.

Reserves against the panel majority: Q1 S4 25 of 26, S5 26 of 26 (one summary had no panel majority);
Q2 S4 26 of 27, S5 27 of 27.

## Supplementary (not the registered figure)

- All five scorers, check 1: Q1 AC1 0.88, Q2 0.93 (point estimates; intervals in the visual report).
- Practice and check 1 together (36 summaries), S1 to S3, not pre-specified: Q1 AC1 0.83 (0.70 to 0.93),
  Q2 0.90 (0.78 to 1.00).
- Q3 emphasis "yes" on check 1: S1 12, S2 1, S3 5, S4 3, S5 8 of 27. Decision (study lead, 14 Nov): Q3
  gets no majority label; it is reported per scorer, with cell comparisons within scorer only.

## Time per summary, check 1 (seconds)

| Scorer | Mean | Median |
| --- | --- | --- |
| S1 | 55 | 28 |
| S2 | 85 | 41 |
| S3 | 113 | 63 |
| S4 | 75 | 29 |
| S5 | 125 | 101 |

Planning figure: 2 minutes per summary.

No outcome is compared across conditions here (pilot rule).
