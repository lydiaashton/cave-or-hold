"""Draw the calibration sets for the human scorers from an exported pilot batch.

For each world x cell, the summaries of one turn are shuffled with a recorded seed and dealt into
the rounds in order, so the rounds never share a summary and every round has the same number of
summaries from every world and cell. Only the study lead's key says which summary came from where.

Usage (from the repository root):
    python3 scoring/draw_calibration.py --batch pilot3 --per-cell 3 \
        --rounds practice,fresh --seed 20261114

Writes, for each round, exports/<batch>/calibration/<round>/<summary_id>.txt (the summary text as
exported, for the page builder), and exports/<batch>/key/calibration_sets.csv (round, summary ID,
world, cell, dataset seed: study lead only). Nothing in a round's folder names a world or a cell.
"""
import argparse
import csv
import random
import shutil
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HUMAN_CELLS = ("never", "before_B", "after_B")   # the Codebook: humans score Never and Expectation


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--batch", required=True)
    ap.add_argument("--turn", type=int, default=4)
    ap.add_argument("--cells", default=",".join(HUMAN_CELLS))
    ap.add_argument("--per-cell", type=int, required=True,
                    help="summaries per world x cell in each round")
    ap.add_argument("--rounds", default="practice,fresh")
    ap.add_argument("--seed", type=int, required=True)
    a = ap.parse_args(argv)

    exp = REPO / "exports" / a.batch
    key = exp / "key" / "KEY.csv"
    if not key.is_file():
        sys.exit(f"{key} not found: run the export first")
    cells = [c for c in a.cells.split(",") if c]
    rounds = [r for r in a.rounds.split(",") if r]
    strata = defaultdict(list)
    with open(key, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if int(r["turn"]) == a.turn and r["condition"] in cells:
                strata[(r["world"], r["condition"])].append(r)
    if not strata:
        sys.exit(f"no turn-{a.turn} summaries in cells {cells}")
    need = a.per_cell * len(rounds)
    short = {k: len(v) for k, v in strata.items() if len(v) < need}
    if short:
        sys.exit(f"{need} needed per world x cell, but some have fewer: {short}")

    rng = random.Random(a.seed)
    out_rows = []
    for round_name in rounds:
        d = exp / "calibration" / round_name
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    for stratum in sorted(strata):
        rows = sorted(strata[stratum], key=lambda r: r["summary_id"])
        rng.shuffle(rows)
        for i, round_name in enumerate(rounds):
            for r in rows[i * a.per_cell:(i + 1) * a.per_cell]:
                src = exp / f"T{a.turn}" / "summaries" / f"{r['summary_id']}.txt"
                shutil.copy2(src, exp / "calibration" / round_name / src.name)
                out_rows.append({"round": round_name, "summary_id": r["summary_id"],
                                 "turn": a.turn, "world": r["world"], "cell": r["condition"],
                                 "dataset_seed": r["dataset_seed"], "run_id": r["run_id"],
                                 "draw_seed": a.seed})
    with open(exp / "key" / "calibration_sets.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0]))
        w.writeheader()
        w.writerows(out_rows)
    for round_name in rounds:
        n = sum(r["round"] == round_name for r in out_rows)
        print(f"{round_name}: {n} summaries -> exports/{a.batch}/calibration/{round_name}/")
    print(f"key: exports/{a.batch}/key/calibration_sets.csv (study lead only)")


if __name__ == "__main__":
    main()
