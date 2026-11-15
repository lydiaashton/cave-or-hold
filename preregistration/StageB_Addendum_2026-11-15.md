# Stage B addendum (15 Nov 2026)

Three changes were made on 15 Nov 2026, after Stage B was filed and before any main-run summary was scored by humans or judges. Each was committed to the study repository when it was made, at the time given below. The commits are the record of timing; this document collects them for filing on Zenodo and OSF. The filed Stage B documents are not changed. None of the three changes alters the hypotheses, the tests, the outcome definition or the decision rules.

## 1. Analysis script corrected (07:29 UTC)

**What changed.** The filed Stage B plan cites `analysis/cave_analysis.py` at commit 3bbbb99. That script reimplemented the Codebook's error mapping instead of calling the harness's implementation (`caveharness.judge.errs_toward_expectation`), and the two disagreed on inputs outside the normal answer set:

1. A judge claim of "no_majority" or an empty claim: the harness returns missing; the script scored it as "not an error".
2. A missing uncertainty answer in the confounded world: the harness ignores uncertainty there (any effect claim is an error); the script returned missing.
3. A missing uncertainty answer in the underpowered world for a claim that is not an effect or association: the harness returns "not an error"; the script returned missing.
4. Two loose aliases in the strong world ("cant tell", "cant attribute"): the script counted them as errors; the harness does not recognise them.

Commit f689be4 (PR #29, Krish) makes the script mirror the harness mapping. The mapping itself, as written in the Codebook and the registered plan, is unchanged; only the script's implementation of it is corrected.

**Check.** The corrected script agrees with the harness in every case tested: each claim code in both the scoring-page spelling and the judges' spelling, plus "no_majority", empty and missing claims, crossed with every uncertainty answer (yes, no, empty, missing) and all three worlds (240 comparisons, 0 disagreements). Krish's own check across the harness's codes also found none. The script's built-in self-test passes (29 cases). No outcome had been computed with either version.

**Registered analysis script from this point:** `analysis/cave_analysis.py` at f689be4 (merge commit ea457b5, 07:29 UTC), attached as `StageB_Addendum_Attachment_AnalysisScript_f689be4.py`.

## 2. Scoring page layout, display only (08:01 UTC)

**What changed.** The filed Stage B plan attaches the scoring page template, `scoring/template.html` at commit 17630fb. After reviewing a preview of the three pages, the study lead changed how the page is laid out (PR #30, merged as 5b0b14e):

1. The answer options have more space between them. The display glosses added after calibration (Codebook change log, 14 Nov) now sit on their own line under the code instead of in brackets after it. The words are the same.
2. The codebook column beside the questions is grouped by question: where to look, question 1 (the claim codes and the rules about the claim), each later question with its rule, and what is not the scorer's job. Before, the rules for the later questions were listed under one "Rules" heading. Every code and rule is shown once, with the same wording.
3. The progress bar under the page header is thicker.

**What did not change.** The questions and their wording, the answer options and the values saved for them, the codebook text, the block order and the within-block shuffle, and how answers reach the Sheet.

**Timing.** Before the main-run pages were built.

## 3. Save status and backup download on the scoring page (08:20 UTC)

**What changed.** Testing the built round-1 page, the study lead found that the save status in the page header read "All answers received" as soon as the answers given so far had reached the Sheet. A scorer could take that to mean the page was finished. It now reads "Saved: k of N", where k is the number of summaries answered and saved and N is the number on the page. The message shown while an answer is waiting to save was reworded, from a red "Not received yet … Keep working; the page will try again." to an amber "Waiting to save n · kept on this page, will retry" (PR #31).

**Two settings decided at the same time (study lead).**
- *Backup download on, shown when it is needed.* The main-run pages are built without `--no-download`. While answers are saving, scorers see only "Saved: k of N". If an answer has not reached the Sheet, a "Download a backup copy (CSV)" button appears beside the amber status. The end screen always offers the backup copy. The Sheet stays the main route. If a scorer's file and the Sheet both hold a summary, the combiner keeps the latest row by the page's own clock, as before.
- *Back button kept,* as at calibration, where scorer agreement was measured with it. The Sheet appends a row on every send, so every saved version of an answer is kept. We will report how often a summary's answers changed after their first complete save, comparing answers only, and if that is not rare, repeat the main tests on first complete answers as a robustness check.

**What did not change.** Everything else on the page and in the template, including what is saved and when, and the summary counter beside the questions.

**Timing.** Before page 1 was sent to any scorer. The pages built earlier that night with the template at 5b0b14e were rebuilt and were not sent.

**Template used for main-run scoring from this point:** `scoring/template.html` at 86b654a (PR #31, merged as 745d051).

*Filed by Lydia Ashton, study lead, 15 Nov 2026.*
