"""Keep the blocks every panel scorer finished (Stage A section 7).

Usage:
  python3 complete_blocks.py <scorer_labels.csv> <order.csv> <out.csv> \
      --panel S1,S2,S3 [--round 1] [--questions bottom_claim,bottom_uncertainty]

Scoring stops by time, not by results. The analysis uses every block of whole
datasets that all panel scorers completed. A block is complete when every panel
scorer has a non-empty answer to every listed question for every summary in it.
Blocks are kept in the page order, so the kept set is always the first k blocks
plus any later block that happens to be complete; the number of complete blocks
and the first incomplete one are printed and should be reported.

Reads only order.csv (position, block, summary_id) and the scorers' answers: no
condition, so it runs before unblinding. Rows of other scorers (reserves) in kept
blocks are kept too, so agreement by role can still be computed.
"""
import csv
import sys
from collections import defaultdict

args = list(sys.argv[1:])


def opt(name, default):
    if name in args:
        i = args.index(name)
        v = args[i + 1]
        del args[i:i + 2]
        return v
    return default


panel = [c for c in opt("--panel", "").split(",") if c]
rnd = opt("--round", "")
questions = opt("--questions", "bottom_claim,bottom_uncertainty").split(",")
if len(args) != 3 or not panel:
    sys.exit(__doc__)
labels_path, order_path, out_path = args


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


order = sorted(read(order_path), key=lambda r: int(r["position"]))
block_of = {r["summary_id"]: int(r["block"]) for r in order}
members = defaultdict(set)
for r in order:
    members[int(r["block"])].add(r["summary_id"])

rows = [r for r in read(labels_path) if not rnd or str(r.get("round", "")) == rnd]
answered = defaultdict(set)          # (scorer, summary) -> questions answered
for r in rows:
    if r["grading_id"] in block_of and (r.get("answer") or "").strip():
        answered[(r["scorer_code"], r["grading_id"])].add(r["question"])
outside = sorted({r["grading_id"] for r in rows} - set(block_of))
if outside:
    sys.exit(f"{len(outside)} answered summaries are not in {order_path}, e.g. {outside[:3]}: wrong order file?")

complete = [b for b in sorted(members)
            if all(set(questions) <= answered[(s, sid)] for s in panel for sid in members[b])]
first_gap = next((b for b in sorted(members) if b not in complete), None)
keep = {sid for b in complete for sid in members[b]}
kept = [r for r in rows if r["grading_id"] in keep]

with open(out_path, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]) + ["block"] if rows else ["grading_id", "block"])
    w.writeheader()
    for r in kept:
        w.writerow(dict(r, block=block_of[r["grading_id"]]))

print(f"{len(complete)} of {len(members)} blocks complete for panel {','.join(panel)} "
      f"(questions: {', '.join(questions)}); {len(keep)} summaries kept -> {out_path}")
if first_gap is not None:
    late = [b for b in complete if b > first_gap]
    print(f"first incomplete block: {first_gap}"
          + (f"; {len(late)} complete block(s) after it are kept too: {late}" if late else ""))
