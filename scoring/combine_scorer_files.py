#!/usr/bin/env python3
"""Combine the scorers' files into one table for the analysis.

Usage:  python3 combine_scorer_files.py <folder of scorer .csv files> <scorers.csv> <output.csv>
            [--ignore-codes TEST] [--batch "<batch label>"] [--skip-unfinished]

Input files: the CSVs scorers download from the scoring pages, or the tabs of the study
Google Sheet saved as CSV. Any mix of rounds and scorers.

scorers.csv: two columns, scorer_code and role, one row per scorer; role is "blind" or "aware".
It is written by the study lead from the panel note.

Output: one row per scorer x summary x question:
  schema_version, grading_id, scorer_code, role, round, batch, question, answer, seconds, source_file

Rules. Nothing is guessed: any of these stops the script with a message and writes no output.
  - a scorer code that is not in scorers.csv, or a role that is not "blind" or "aware"
  - a summary whose latest row is unfinished: not all questions answered, or (from the Google Sheet)
    answered but not yet submitted. With --skip-unfinished such summaries are left out and listed.
  - a file whose columns are not a scoring page's
The Google Sheet is append-only, and the page sends the summary a scorer has open every 30 seconds
(those rows show 0 seconds) and again when the scorer moves on (that row has the time). So one
summary has several rows. The latest by the page's own clock is kept, only that row is checked, and
the number of earlier rows is reported.
"""
import argparse, csv, glob, os, sys

SCHEMA = "1"
FIXED = {"scorer_code", "round", "batch", "grading_id", "position_shown", "notes", "seconds", "complete",
         "claim_option_order", "next_option_order", "exported_at", "received_at", "client_time"}
QUESTIONS = {"1": ["bottom_claim", "bottom_uncertainty", "bottom_emphasis", "next_steps"],
             "2": ["bottom_claim_retest", "gives_reason", "certainty_as_percent", "says_no_harm"],
             "3": ["bottom_claim", "bottom_uncertainty", "bottom_emphasis", "next_steps", "verdict_claim"]}


def stop(msg):
    sys.exit("STOPPED, nothing written: " + msg)


def _when(r, n):
    """Sort key for 'latest': the page's own clock when it sent or exported the row, then file order."""
    return ((r.get("client_time") or r.get("exported_at") or "").strip(), n)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", help="folder of scorer .csv files")
    ap.add_argument("scorers_file", help="scorers.csv: scorer_code, role")
    ap.add_argument("out", help="output .csv")
    ap.add_argument("--ignore-codes", default="",
                    help="comma list of scorer codes to leave out, e.g. TEST (rows typed while testing the page)")
    ap.add_argument("--batch", default="",
                    help="keep only rows whose batch label is exactly this, e.g. 'Calibration: check 1'")
    ap.add_argument("--skip-unfinished", action="store_true",
                    help="leave out a summary whose latest row is unfinished (not all questions answered, "
                         "or answered but not yet submitted) and list it, instead of stopping. For looking "
                         "at a round while scorers are still working; the final table is made without it.")
    a = ap.parse_args()
    folder, scorers_file, out = a.folder, a.scorers_file, a.out
    ignore = {c.strip() for c in a.ignore_codes.split(",") if c.strip()}
    roles = {}
    with open(scorers_file, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            code, role = (r.get("scorer_code") or "").strip(), (r.get("role") or "").strip()
            if role not in ("blind", "aware"):
                stop(f"{scorers_file}: scorer {code!r} has role {role!r}; it must be blind or aware")
            roles[code] = role
    if not roles:
        stop(f"{scorers_file} lists no scorers")
    latest, n_rows, n_ignored = {}, 0, 0
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
            code = (r["scorer_code"] or "").strip()
            if code in ignore or (a.batch and (r.get("batch") or "").strip() != a.batch):
                n_ignored += 1
                continue
            rnd = str(r["round"]).strip()
            if rnd not in QUESTIONS:
                stop(f"{path} line {n}: round {rnd!r} is not 1, 2 or 3")
            missing = [q for q in QUESTIONS[rnd] if q not in cols]
            if missing:
                stop(f"{path}: round {rnd} file lacks the column(s) {missing}")
            if code not in roles:
                stop(f"{path} line {n}: scorer code {code!r} is not in {scorers_file}")
            n_rows += 1
            k = (code, rnd, r["grading_id"].strip())
            # The page sends the open summary every 30 seconds and again when the scorer moves on, so
            # one summary has several rows. Keep the latest; only that row is checked.
            if k not in latest or _when(r, n) >= latest[k][2]:
                latest[k] = (r, os.path.basename(path), _when(r, n), n)
    unfinished = []
    for k, (r, src, _, n) in sorted(latest.items()):
        code, rnd, gid = k
        empty = [q for q in QUESTIONS[rnd] if not (r[q] or "").strip()]
        try:
            secs = float(r.get("seconds") or 0)
        except ValueError:
            stop(f"{src} line {n}: seconds is {r.get('seconds')!r}")
        why = ""
        if (r.get("complete") or "").strip() != "yes" or empty:
            why = "not all questions answered" + (f" ({', '.join(empty)})" if empty else "")
        elif "client_time" in r and secs == 0:
            # A row the page sent on its timer: the time is added only when the scorer moves on.
            why = "answered but not yet submitted (0 seconds)"
        if why:
            if not a.skip_unfinished:
                stop(f"{src} line {n}: summary {gid}, scorer {code}, round {rnd}: {why}. "
                     f"Use --skip-unfinished to leave such summaries out while a round is under way.")
            unfinished.append((code, rnd, gid, why))
    for code, rnd, gid, _ in unfinished:
        del latest[(code, rnd, gid)]
    if not latest:
        stop("no finished summaries to write")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["schema_version", "grading_id", "scorer_code", "role", "round", "batch", "question",
                    "answer", "seconds", "source_file"])
        for (code, rnd, gid), (r, src, _, _) in sorted(latest.items()):
            for q in QUESTIONS[rnd]:
                w.writerow([SCHEMA, gid, code, roles[code], rnd, r.get("batch", ""), q, r[q].strip(),
                            r.get("seconds", ""), src])
    scorers = sorted({k[0] for k in latest})
    print(f"{len(latest)} scorer x summary rows from {len(files)} files, scorers {scorers}; "
          f"{n_rows - len(latest) - len(unfinished)} earlier rows superseded; {n_ignored} rows left out by "
          f"--ignore-codes or --batch -> {out}")
    for code, rnd, gid, why in unfinished:
        print(f"  left out, unfinished: scorer {code}, round {rnd}, summary {gid}: {why}")


if __name__ == "__main__":
    main()
