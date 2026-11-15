# Main scoring: after the 20:00 UTC deadline (15 Nov 2026)

Order matters: nothing that uses the key runs before step 5. Rehearsed on page 1 at 16:40 UTC
(all steps ran; ID repair worked; 80 of 80 blocks complete for S1, S2, S3).

1. **Save the final Sheet** (20:06 UTC, scheduled): rounds 1-3 as CSV in
   `exports/main/scoring/sheet_final_2026-11-15/`, with SHA-256 and row counts. Raw and append-only.
2. **Combine**, from the repo root:

       python3 scoring/combine_scorer_files.py exports/main/scoring/sheet_final_2026-11-15 \
           scoring/main/scorers.csv exports/main/scoring/scorer_labels_all.csv --ignore-codes TEST \
           --order exports/main/scoring/round1/order.csv --order exports/main/scoring/round2/order.csv \
           --order exports/main/scoring/round3/order.csv --skip-unfinished

   `--skip-unfinished` is needed: summaries open at the deadline are unfinished by design and are
   listed. Check the "repaired summary ID" lines (expected: 2.59488E+24 -> 0259488e19).
3. **Complete blocks**, per round, panel S1-S3 (Stage A section 7):

       python3 scoring/complete_blocks.py exports/main/scoring/scorer_labels_all.csv \
           exports/main/scoring/round1/order.csv exports/main/scoring/scorer_labels_r1.csv --panel S1,S2,S3 --round 1

   and the same with `round2`, `--round 2` (questions `bottom_claim_retest`) and `round3`, `--round 3`.
   Record the number of complete blocks and the first incomplete one for each round.
4. **Main-set agreement** (no key):

       python3 scoring/calibration_agreement.py exports/main/scoring/scorer_labels_all.csv --round 1 --batch "Main round 1"

5. **Declare the labels locked** (study lead, dated note in the Scoring tab and the addendum record).
   Reserve rule: not triggered if every panel scorer has 80 complete page-1 blocks.
6. **Then** release the key to the analysis: judge validation (`scoring/stageb_checks.py`), then
   `analysis/cave_analysis.py --labels-locked` (H2 caving test first, then H1).
7. After the judges from all machines are merged into `exports/main/judging/judgments.jsonl`,
   rebuild the judge results with `--report-only`.
