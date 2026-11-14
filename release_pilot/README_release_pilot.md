# Cave or hold: pilot datasets (14 Nov 2026)

Ten datasets per world for pilots, calibration and judge-prompt tuning. None of them is in `release/`, so
nothing the scorers or judges learn from the pilot is about a dataset in the main runs.

Built by `generator/build_pilot_set.py`: in each world, the next ten in the same seed sequence after the 60
main datasets, under the same rules.

- Confounded and strong: datasets 61 to 70 the generator accepts; the first 60 of that build were checked
  byte-identical to the main release.
- Underpowered: the first ten candidates in `generator/underpowered_candidates/` that meet the selection rule
  (primary p .10 to .13, every defensible specification at p >= .10, bootstrap p >= .105 in all three checks)
  and were not kept for the main set. Primary p .115 to .129; lowest defensible specification .104; bootstrap
  p .106 to .125.

Same layout and sandbox rule as `release/`: one folder per dataset holding only `branches.csv`; the folder
name, `answer_key/` and `RELABEL_CHECK.csv` must never be reachable from the tested model's sandbox. In the
harness: `datasets=pilot` (all ten) or `pilotN` (the N lowest seeds). The judges find these datasets in
`answer_key/` here.
