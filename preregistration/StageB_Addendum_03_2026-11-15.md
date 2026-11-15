# Stage B addendum 3: save status on the scoring page (15 Nov 2026)

**What changed.** Testing the built round-1 page, the study lead found that the save status in the page header read "All answers received" as soon as the answers given so far had reached the Sheet. A scorer could take that to mean the page was finished. It now reads "Saved: k of N", where k is the number of summaries answered and saved and N is the number on the page. Template commit 8257195 (PR #31).

**Two settings decided at the same time (study lead).**
- *Backup download on.* The main-run pages are built without `--no-download`, so scorers have a "Download a backup copy (CSV)" button and the end screen asks for the file only if some answers did not reach the Sheet. The Sheet stays the main route. If a scorer's file and the Sheet both hold a summary, the combiner keeps the latest row by the page's own clock, as before.
- *Back button kept,* as at calibration, where scorer agreement was measured with it. The Sheet appends a row on every send, so every saved version of an answer is kept. We will report how often a summary's answers changed after its first complete save, and if that is not rare, repeat the main tests on first complete answers as a robustness check.

**What did not change.** Everything else on the page and in the template, including what is saved and when, and the summary counter beside the questions. The outcome definitions and the analysis are unaffected.

**Timing.** Made on 15 Nov 2026, before page 1 was sent to any scorer. The pages built earlier that night with the template at 5b0b14e were rebuilt with this one and were not sent.

**Template used for main-run scoring, from this date:** `scoring/template.html` at 8257195. This replaces the template named in addendum 2.

*Filed by Lydia Ashton, study lead, 15 Nov 2026, 08:10 UTC (commit time of this file).*
