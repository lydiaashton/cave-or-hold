# Number-to-output trace

Every number that appears in the manuscript gets a row. A row is done when the
number has been traced to a specific analysis output and a second person has
re-run the trace.

| # | Number as printed | Section | Source (script function / export file) | Traced by | Second check | Status |
|---|---|---|---|---|---|---|
| 1 |  |  |  |  |  |  |

Status: `ok`, `mismatch`, `not-reproducible`, `open`.

Rules:
- A number is not traced until someone has pointed at the line of output it
  came from. "It is in the script" is not a trace.
- If a number changes in the analysis, the row reopens.
