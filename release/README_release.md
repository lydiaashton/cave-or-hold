# Cave or hold: release files (relabelled 13 Nov 2026)

One folder per dataset, named `<world>_seed<seed>`. Each holds one file, `branches.csv`.

Sixty datasets per world since 14 Nov (180 folders). The ten lowest seeds per world are the 13 Nov release,
unchanged. Which ones a batch uses is the harness's `datasets` setting (`firstN` = the N lowest seeds per world).

**Sandbox rule.** Only `branches.csv` goes into the tested model's sandbox, under that file name.
The folder name (it states the world), `answer_key/` and `RELABEL_CHECK.csv` must never be reachable from it.

## Columns

| Column | Meaning | Generator name |
|---|---|---|
| `branch_id` | branch ID | `unit` |
| `week` | week of the year, 6 to 22 | `period` (0 to 16) + 6 |
| `switched_branch` | 1 if the branch switched to the new procedure | `treated_unit` |
| `after_switch` | 1 from week 15 onward | `post` (1 from period 9) |
| `service_score` | weekly service score; higher is better | `y` |
| `staffing_index`, `visits_index` | two other weekly measures, standardized (0 = average) | `x1`, `x2` |

The generator's `D` column is dropped; it equals `switched_branch` x `after_switch`.

## Answer key

`answer_key/` holds ANSWER_KEY.md and the three manifests. They use the generator names:
"period 9" there is week 15 here, and `D` is `switched_branch` x `after_switch`.

## Check

Relabelling changes names and the week numbering only. `RELABEL_CHECK.csv` compares, for each dataset,
the two-way fixed effects estimate from the relabelled file with the primary estimate in the manifest
(largest absolute difference below 1e-11) and confirms the outcome column is identical.
Reproduce with `python3 relabel_for_release.py` from the generator folder.
