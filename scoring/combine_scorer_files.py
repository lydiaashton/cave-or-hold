#!/usr/bin/env python3
"""Combine the scorers' files into one table for the analysis.

Usage:  python3 combine_scorer_files.py <folder of scorer .csv files> <scorers.csv> <output.csv>

Input files: the CSVs scorers download from the scoring pages, or the tabs of the study
Google Sheet saved as CSV. Any mix of rounds and scorers.

scorers.csv: two columns, scorer_code and role, one row per scorer; role is "blind" or "aware".
It is written by the study lead from the panel note.

Output: one row per scorer x summary x question:
  schema_version, grading_id, scorer_code, role, round, batch, question, answer, seconds, source_file

Rules. Nothing is guessed: any of these stops the script with a message and writes no output.
  - a scorer code that is not in scorers.csv, or a role that is not "blind" or "aware"
  - a row marked incomplete, or an empty answer
  - a file whose columns are not a scoring page's
When the same scorer has several rows for one summary in one round (the Google Sheet is
append-only), the last one is kept and the number of earlier rows dropped is reported.
"""
import csv, glob, os, sys

SCHEMA = "1"
FIXED = {"scorer_code", "round", "batch", "grading_id", "position_shown", "notes", "seconds", "complete",
         "claim_option_order", "next_option_order", "exported_at", "received_at", "client_time"}
QUESTIONS = {"1": ["bottom_claim", "bottom_uncertainty", "bottom_emphasis", "next_steps"],
             "2": ["bottom_claim_retest", "gives_reason", "certainty_as_percent", "says_no_harm"],
             "3": ["bottom_claim", "bottom_uncertainty", "bottom_emphasis", "next_steps", "verdict_claim"]}


def stop(msg):
    sys.exit("STOPPED, nothing written: " + msg)


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    folder, scorers_file, out = sys.argv[1:]
    roles = {}
    with open(scorers_file, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            code, role = (r.get("scorer_code") or "").strip(), (r.get("role") or "").strip()
            if role not in ("blind", "aware"):
                stop(f"{scorers_file}: scorer {code!r} has role {role!r}; it must be blind or aware")
            roles[code] = role
    if not roles:
        stop(f"{scorers_file} lists no scorers")
    latest, dropped = {}, 0
    files = sorted(glob.glob(os.path.join(folder, "*.csv")))
    if not files:
        stop(f"no .csv files in {folder}")
    for path in files:
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            stop(f"{path} has no rows")
        cols = set(rows[0])
        if "round" not in cols or "grading_id" not in cols or "scorer_code" not in cols:
            stop(f"{path} is not a scoring page file (needs scorer_code, round, grading_id)")
        for n, r in enumerate(rows, start=2):
            rnd = str(r["round"]).strip()
            if rnd not in QUESTIONS:
                stop(f"{path} line {n}: round {rnd!r} is not 1, 2 or 3")
            missing = [q for q in QUESTIONS[rnd] if q not in cols]
            if missing:
                stop(f"{path}: round {rnd} file lacks the column(s) {missing}")
            code = r["scorer_code"].strip()
            if code not in roles:
                stop(f"{path} line {n}: scorer code {code!r} is not in {scorers_file}")
            if (r.get("complete") or "").strip() != "yes":
                stop(f"{path} line {n}: summary {r['grading_id']} is marked incomplete for scorer {code}")
            for q in QUESTIONS[rnd]:
                if not (r[q] or "").strip():
                    stop(f"{path} line {n}: no answer to {q} for summary {r['grading_id']}")
            k = (code, rnd, r["grading_id"].strip())
            if k in latest:
                dropped += 1
            latest[k] = (r, os.path.basename(path))
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["schema_version", "grading_id", "scorer_code", "role", "round", "batch", "question",
                    "answer", "seconds", "source_file"])
        for (code, rnd, gid), (r, src) in sorted(latest.items()):
            for q in QUESTIONS[rnd]:
                w.writerow([SCHEMA, gid, code, roles[code], rnd, r.get("batch", ""), q, r[q].strip(),
                            r.get("seconds", ""), src])
    scorers = sorted({k[0] for k in latest})
    print(f"{len(latest)} scorer x summary rows from {len(files)} files, scorers {scorers}; "
          f"{dropped} earlier rows superseded -> {out}")


if __name__ == "__main__":
    main()
