# Cave or hold? When a user's expectation enters the analysis

Data, generator and answer key for an Apart Research AI x Epistemics sprint project (13–15 Nov 2026).
The study asks whether the timing of a user's stated expectation (before the analysis, after it, or never)
changes what an AI analyst's final write-up claims, scored against simulated data with a known answer.

**This repository is public while the sprint is judged, so the results can be checked against the code and data.** It holds the answer key next to the data on purpose. It may be made private for a period while the manuscript is drafted.

Pre-registered on OSF ([10.17605/OSF.IO/75CTN](https://doi.org/10.17605/OSF.IO/75CTN)) and Zenodo
([10.5281/zenodo.24222926](https://doi.org/10.5281/zenodo.24222926)); see `preregistration/README.md`.

## Layout

| Path | What it is | Goes into the tested model's sandbox? |
|---|---|---|
| `release/<world>_seed<seed>/branches.csv` | The 300 main datasets (100 per world; 60 per world until 14 Nov, 11:30 CT, and those 60 are unchanged), with scenario column names. None was used in a pilot. How many are used is set by a pre-registered rule (below) | **Only this file**, one per run, copied in as `branches.csv` |
| `release/README_release.md` | Column dictionary and the sandbox rule | No |
| `release/RELABEL_CHECK.csv` | Check that relabelling changed names and week numbering only | No |
| `release_pilot/` | Ten more datasets per world for pilot 3, with their own answer key; none is in `release/` | Only `branches.csv`, in pilot runs |
| `release/answer_key/` | `ANSWER_KEY.md` and the three manifests: each dataset's correct conclusion and reference results | **Never.** The judges and the scorers need it |
| `generator/` | Generator, answer-key builder, relabel script, wild cluster bootstrap checks, generator README | No |
| `generator/out/` | The same datasets under generator column names, with manifests and answer key | **Never** |
| `generator/out_11periods_check/` | The same build at 11 periods: a ground-truth check only, not used in runs | **Never** |
| `docs/` | Notes for engineering (see `docs/README.md`) | No |

The folder names state the world. The model must see only the file `branches.csv`, never its folder name,
the answer key, the manifests or anything in `generator/`.

## The three worlds

| World | Correct conclusion | Units × weeks | Rows per file |
|---|---|---|---|
| Underpowered | Inconclusive | 34 × 17 | 578 |
| Confounded | The apparent effect is not credible | 709 × 17 | 12,053 |
| Strong | There is an effect | 150 × 17 | 2,550 |

## Which datasets are used

Sixty datasets were built per world. The study uses the first R per world in seed order, one run per
dataset in each cell; R is fixed before the main runs (see the design doc). No main dataset was used in a
pilot: the ones pilots 1 and 2 ran on (`generator/piloted_seeds.json`: five underpowered, five confounded)
were taken out on 14 Nov and each world topped back up to sixty, and pilot 3 runs on `release_pilot/`.

Full figures per dataset are in `release/answer_key/ANSWER_KEY.md`; the accept rule and known limits
are in `generator/README_generator_v2.md`.

## Reproduce

From `generator/`, with Python 3, numpy and pandas:

```
python3 caveworlds_did.py                 # confounded and strong into out/; underpowered candidates
# underpowered: the two bootstrap checks, then select_underpowered.py (steps in its docstring)
python3 drop_piloted.py                   # confounded: leaves out the datasets pilots 1 and 2 used
python3 build_answer_key.py out           # rewrites out/ANSWER_KEY.md from the manifests
python3 relabel_for_release.py            # writes release/ from out/ and RELABEL_CHECK.csv
Rscript wild_bootstrap_check.R out underpowered   # optional cross-check (fwildclusterboot)
Rscript wild_bootstrap_base_r.R out underpowered  # same check without fwildclusterboot
```

The 11-period check: `python3 -c "import caveworlds_did as c; [c.generate(w, k=10, outdir='out_11periods_check', params=c.Params(n_periods=11, treat_period=6)) for w in c.WORLDS]"`

Checked 14 Nov 2026 (Python 3.13, NumPy 2.5.3): a fresh build reproduces byte for byte the first 320
underpowered candidates, every confounded dataset in `out/` and `out_pilot/`, and the strong sixty and their
pilot ten; `relabel_for_release.py` leaves every `branches.csv` that was already in `release/` unchanged.

## Design, prompts and harness spec

These are still changing and live in the project's design doc, not in this repository:
the Technical note, Prompt, Codebook, Scoring and Analysis plan tabs.
See `docs/README.md`.
