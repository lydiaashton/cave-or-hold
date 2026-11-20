# Number-to-output trace

Every number that appears in the manuscript gets a row. A row is done when the
number has been traced to a specific analysis output and a second person has
re-run the trace.

| # | Number as printed | Section | Source (script function / export file) | Traced by | Second check | Status |
|---|---|---|---|---|---|---|
| 1 | 6 of 60 (10%) | Introduction | cave_analysis.py::stratified_mcnemar, JSON stage10.H2_after_vs_never_paired.n_never_caved, run on exports/main | KKV |  | ok |
| 2 | 13 of 60 (22%) | Introduction | same call, .n_after_caved | KKV |  | ok |
| 3 | 7 discordant pairs, exact McNemar p = .016 | Introduction | same call, .discordant / .b_after_only / .c_never_only / .p, exact conditional branch via scipy binomtest(7, 7, 0.5) | KKV |  | ok |
| 4 | 11 against 5 discordant pairs, p = .21 | Introduction | cave_analysis.py::stratified_mcnemar(h1_pairs), JSON stage10.H1_after_vs_before_paired | KKV |  | ok |

Status: `ok`, `mismatch`, `not-reproducible`, `open`.

Rules:
- A number is not traced until someone has pointed at the line of output it
  came from. "It is in the script" is not a trace.
- If a number changes in the analysis, the row reopens.
