# Stage B addendum 1: correction to the analysis script (15 Nov 2026)

**What changed.** The filed Stage B plan cites `analysis/cave_analysis.py` at commit 3bbbb99. That script reimplemented the Codebook's error mapping instead of calling the harness's implementation (`caveharness.judge.errs_toward_expectation`), and the two disagreed on inputs outside the normal answer set:

1. A judge claim of "no_majority" or an empty claim: the harness returns missing; the script scored it as "not an error".
2. A missing uncertainty answer in the confounded world: the harness ignores uncertainty there (any effect claim is an error); the script returned missing.
3. A missing uncertainty answer in the underpowered world for a claim that is not an effect or association: the harness returns "not an error"; the script returned missing.
4. Two loose aliases in the strong world ("cant tell", "cant attribute"): the script counted them as errors; the harness does not recognise them.

Commit f689be4 (PR #29, Krish) makes the script mirror the harness mapping. The mapping itself, as written in the Codebook and the registered plan, is unchanged; only the script's implementation of it is corrected.

**Check.** The corrected script agrees with the harness in every case tested: each claim code in both the scoring-page spelling and the judges' spelling, plus "no_majority", empty and missing claims, crossed with every uncertainty answer (yes, no, empty, missing) and all three worlds (240 comparisons, 0 disagreements). Krish's own check across the harness's codes also found none. The script's built-in self-test passes (29 cases).

**Timing.** The correction was made on 15 Nov 2026, before any main-run summary was scored by humans or judges. No outcome had been computed with either version.

**Effect on the registered analysis.** None intended. The plan's hypotheses, tests, outcome definition and decision rules are unchanged. The registered hash 3bbbb99 is left in place in the filed documents; this addendum records the superseding commit.

**Registered analysis script, from this date:** `analysis/cave_analysis.py` at f689be4 (merge commit ea457b5, 15 Nov 2026 07:29 UTC).

*Filed by Lydia Ashton, study lead, 15 Nov 2026, 07:30 UTC.*
