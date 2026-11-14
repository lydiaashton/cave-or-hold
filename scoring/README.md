# Scoring page builder

Builds one self-contained HTML page that scorers open in a browser. No installs; Python 3 only.

    python3 build_scoring_page.py <folder of summary .txt files> "<batch label>" <output.html>

Example:

    python3 build_scoring_page.py export/T4/summaries "Batch 1 (turn 4)" scoring_batch1_T4.html

- Each `.txt` is one summary; the file name without `.txt` is the grading ID.
- A first line `Summary ID: ...` is removed. A block of analysis numbers above a
  `----- Summary -----` marker is removed. Other file types in the folder are ignored.
- The script stops with an error if a summary starts with analysis numbers and has no marker.
- `template.html` must sit in the same folder as the script.

What scorers get: the HTML file only. They enter a scorer code, answer four questions per summary,
and press "Download my results (CSV)". The order of summaries and of answer options is shuffled
per scorer code and recorded in the results file, along with seconds per summary.

Scorers must not receive the turn folders, `analysis_values.csv`, logs, thinking traces or the key.

## Title framing (automatic)

    python3 title_framing.py <export batch folder> <output.csv>

Example:

    python3 title_framing.py exports/pilot1 exports/pilot1/key/title_framing.csv

Writes one row per summary and turn: the title line and its framing noun
(`impact`, `evaluation`, `impact+evaluation`, `other`, `none`). A keyword match on one line;
no judge or scorer is involved. The output belongs with the key and analysis files, not with scorers.

## Three rounds, three pages

Scorers do the rounds in order. They never see which turn a summary came from, and the page titles say only the round.

| Round | Page title | Summaries | Questions | Build |
|---|---|---|---|---|
| 1 | Round 1: bottom line | Every turn-4 summary in the human-scored set | Claim, uncertainty, emphatic words, next steps | `--round 1` |
| 2 | Round 2: whole summary | A fixed random subset of round 1 | The claim again, then reason why, certainty as a percentage, no harm | `--round 2` |
| 3 | Round 3: bottom line and verdict | Turns 6 and 8 | The four round-1 questions, then the final verdict | `--round 3` |

    python3 build_scoring_page.py <folder of .txt> "<batch label>" Scoring_Round1_BottomLine.html --round 1

Round 2 is given only after a scorer has returned round 1, and round 3 after round 2. The subset for round 2 is drawn by the study lead with a recorded seed; put those files in their own folder. CSV columns follow the questions on the page. In round 2 the repeated claim is saved as bottom_claim_retest; in round 3 the verdict is saved as verdict_claim. The older flags --whole-summary and --batch2 still work and mean rounds 2 and 3.

## Automatic capture to a Google Sheet (optional)

Without this, scorers download a CSV and send it back. With it, the page also sends each summary's
answers to a Google Sheet whenever the scorer moves to another summary. Scorers need no account and
cannot see the sheet. The download stays as a backup and the page asks for it only if sending failed.

Set up once (study lead, about five minutes):
1. Create a new Google Sheet. Do not share it with scorers.
2. Extensions > Apps Script. Delete what is there, paste the contents of `sheet_receiver.gs`, save.
3. Deploy > New deployment > type "Web app". Execute as: Me. Who has access: Anyone. Deploy and authorize.
4. Copy the web app URL (it ends in /exec). Opening it in a browser should show: Scoring receiver is live.
5. Build the pages with it:
   `python3 build_scoring_page.py <folder> "<batch label>" main.html --endpoint <URL>`
   (add `--whole-summary` for the subsample page; the same URL serves both).
6. Test before sending to scorers: open the page, use scorer code TEST, answer two summaries, and
   check that rows appear in the sheet's "round1" tab. Delete the TEST rows afterwards.

What lands in the sheet: one tab per round ("round1", "round2", "round3"), the same columns as the CSV plus
`received_at` and `client_time`. It is append-only: a changed answer adds a new row. In the analysis
keep the last row per (scorer_code, batch, grading_id).

Things to know:
- The URL is inside the page, so anyone who has the page could send rows to the sheet. It cannot read
  the sheet. Rows are stored as text and cannot run as formulas.
- If you edit the script later, deploy it as a new version of the same deployment so the URL stays the same.
- The live connection has only been tested against a simulated sheet, not against Google.

## Combining scorer files for the analysis

    python3 combine_scorer_files.py <folder of scorer .csv files> scorers.csv scorer_labels.csv

`scorers.csv` has two columns, `scorer_code` and `role` (blind or aware), written by the study lead from the
panel note. The output has one row per scorer, summary and question:
`schema_version, grading_id, scorer_code, role, round, batch, question, answer, seconds, source_file`.
`grading_id` is the summary ID, the same ID the judge files carry, so human and judge labels join without the key.
The script stops and writes nothing if a scorer is not in `scorers.csv`, a role is missing, a row is incomplete or
an answer is empty. When a scorer has several rows for one summary (the Google Sheet is append-only), the last is kept.
