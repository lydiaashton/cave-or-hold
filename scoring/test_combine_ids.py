#!/usr/bin/env python3
"""Checks for the summary-ID repair in combine_scorer_files.py.  Run: python3 scoring/test_combine_ids.py"""
import csv, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
COLS = ["received_at", "client_time", "scorer_code", "round", "batch", "grading_id", "position_shown",
        "bottom_claim", "bottom_uncertainty", "bottom_emphasis", "next_steps", "notes", "seconds", "complete"]


def run(order_ids, sheet_ids, extra=()):
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "order.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["position", "block", "summary_id"])
        for i, s in enumerate(order_ids, 1): w.writerow([i, (i - 1) // 3 + 1, s])
    os.mkdir(os.path.join(d, "in"))
    with open(os.path.join(d, "in", "round1.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(COLS)
        for i, s in enumerate(sheet_ids, 1):
            w.writerow(["", f"2026-11-15T10:00:{i:02d}Z", "S1", "1", "Main round 1", s, i,
                        "effect", "yes", "no", "roll out or keep", "", "60", "yes"])
    with open(os.path.join(d, "scorers.csv"), "w", newline="") as f:
        f.write("scorer_code,role\nS1,blind\n")
    p = subprocess.run([sys.executable, os.path.join(HERE, "combine_scorer_files.py"), os.path.join(d, "in"),
                        os.path.join(d, "scorers.csv"), os.path.join(d, "out.csv"),
                        "--order", os.path.join(d, "order.csv"), *extra], capture_output=True, text=True)
    ids = set()
    if p.returncode == 0:
        with open(os.path.join(d, "out.csv")) as f:
            ids = {r["grading_id"] for r in csv.DictReader(f)}
    return p, ids


ORDER = ["a3f9c21b07", "0259488e19", "1668273415", "4223943522", "33e1512819", "b81c0d9e4f"]
# 1. The forms Google Sheets gives these IDs (as seen on 15 Nov) are mapped back.
p, ids = run(ORDER, ["a3f9c21b07", "2.59488E+24", "1668273415.0", "4223943522", "33e1512819", "b81c0d9e4f"])
assert p.returncode == 0, p.stderr
assert ids == set(ORDER), ids
assert "repaired summary ID: '2.59488E+24'" in p.stdout and "-> 0259488e19" in p.stdout, p.stdout
# 2. An ID in no order file stops the script.
p, _ = run(ORDER, ["a3f9c21b07", "ffffffffff"])
assert p.returncode != 0 and "in none of the order files" in p.stderr, p.stderr
# 3. A value two known IDs share is not guessed.
p, _ = run(["1e5", "100000", "a3f9c21b07"], ["100000.0"])
assert p.returncode != 0, p.stdout
print("all ID-repair checks passed")
