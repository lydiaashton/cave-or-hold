"""Draw the calibration sets for the human scorers from an exported pilot batch.

For each world x cell, the summaries of one turn are shuffled with a recorded seed and dealt into
the rounds in order, so the rounds never share a summary and every round has the same number of
summaries from every world and cell. Only the study lead's key says which summary came from where.

Usage (from the repository root):
    python3 scoring/draw_calibration.py --batch pilot3 --per-cell 3 \
        --rounds practice,fresh --seed 20261114

Fresh-set mode (study lead, 14 Nov): a short practice set and fresh sets of a fixed size, e.g.
    python3 scoring/draw_calibration.py --batch pilot3 --fresh-size 30 --fresh-sets 3 \
        --practice 3 --seed 20261114
Each fresh set takes the same number from every world; where that does not divide by the cells
(30 = 10 per world over 3 cells) the extra summary rotates over the cells from set to set, so every
cell also gives 10 to every set. The practice summaries come from the Certainty cells, which humans
never score in the study, so the practice uses none of the summaries the agreement bar is judged on.

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
PRACTICE_CELLS = ("before_D", "after_D")          # Certainty cells: never human-scored in the study


def _load(exp, turn, cells):
    key = exp / "key" / "KEY.csv"
    if not key.is_file():
        sys.exit(f"{key} not found: run the export first")
    strata = defaultdict(list)
    with open(key, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if int(r["turn"]) == turn and r["condition"] in cells:
                strata[(r["world"], r["condition"])].append(r)
    return strata


def _write(exp, turn, picks, seed):
    """picks: list of (round name, KEY row). Copies the summaries and writes the key."""
    for round_name in dict.fromkeys(n for n, _ in picks):
        d = exp / "calibration" / round_name
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    out_rows = []
    for round_name, r in picks:
        src = exp / f"T{turn}" / "summaries" / f"{r['summary_id']}.txt"
        shutil.copy2(src, exp / "calibration" / round_name / src.name)
        out_rows.append({"round": round_name, "summary_id": r["summary_id"],
                         "turn": turn, "world": r["world"], "cell": r["condition"],
                         "dataset_seed": r["dataset_seed"], "run_id": r["run_id"],
                         "draw_seed": seed})
    ids = [r["summary_id"] for r in out_rows]
    if len(ids) != len(set(ids)):
        sys.exit("a summary was drawn twice; stop")
    with open(exp / "key" / "calibration_sets.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0]))
        w.writeheader()
        w.writerows(out_rows)
    return out_rows


def fresh_sizes(n_worlds, n_cells, size, k):
    """How many summaries each world x cell gives to fresh set k (0-based) of `size`.
    Every world gives size / n_worlds. Where that does not divide by the cells, the extra
    ones rotate over the cells from set to set, so with as many cells as worlds every cell
    also gives the same number in every set."""
    if size % n_worlds:
        sys.exit(f"--fresh-size {size} is not a multiple of the {n_worlds} worlds")
    per_world = size // n_worlds
    base, extra = divmod(per_world, n_cells)
    return {(wi, ci): base + (1 if (ci - wi - k) % n_cells < extra else 0)
            for wi in range(n_worlds) for ci in range(n_cells)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--batch", required=True)
    ap.add_argument("--turn", type=int, default=4)
    ap.add_argument("--cells", default=",".join(HUMAN_CELLS))
    ap.add_argument("--per-cell", type=int,
                    help="equal-deal mode: summaries per world x cell in each round")
    ap.add_argument("--rounds", default="practice,fresh")
    ap.add_argument("--fresh-size", type=int,
                    help="fresh-set mode: summaries in each fresh set (e.g. 30)")
    ap.add_argument("--fresh-sets", type=int, default=3,
                    help="fresh-set mode: how many fresh sets to draw (fresh1, fresh2, ...)")
    ap.add_argument("--practice", type=int, default=0,
                    help="fresh-set mode: practice summaries, the same number from every world, "
                         "taken from --practice-cells so no fresh-set summary is used")
    ap.add_argument("--practice-cells", default=",".join(PRACTICE_CELLS))
    ap.add_argument("--seed", type=int, required=True)
    a = ap.parse_args(argv)
    if (a.per_cell is None) == (a.fresh_size is None):
        sys.exit("give exactly one of --per-cell (equal deal) or --fresh-size (fresh sets)")

    exp = REPO / "exports" / a.batch
    cells = [c for c in a.cells.split(",") if c]
    strata = _load(exp, a.turn, cells)
    if not strata:
        sys.exit(f"no turn-{a.turn} summaries in cells {cells}")
    rng = random.Random(a.seed)
    picks = []

    if a.per_cell is not None:
        rounds = [r for r in a.rounds.split(",") if r]
        need = a.per_cell * len(rounds)
        short = {k: len(v) for k, v in strata.items() if len(v) < need}
        if short:
            sys.exit(f"{need} needed per world x cell, but some have fewer: {short}")
        for stratum in sorted(strata):
            rows = sorted(strata[stratum], key=lambda r: r["summary_id"])
            rng.shuffle(rows)
            for i, round_name in enumerate(rounds):
                picks += [(round_name, r) for r in rows[i * a.per_cell:(i + 1) * a.per_cell]]
    else:
        worlds = sorted({w for w, _ in strata})
        missing = [(w, c) for w in worlds for c in cells if (w, c) not in strata]
        if missing:
            sys.exit(f"no turn-{a.turn} summaries for {missing}")
        shuffled = {}
        for stratum in sorted(strata):
            rows = sorted(strata[stratum], key=lambda r: r["summary_id"])
            rng.shuffle(rows)
            shuffled[stratum] = rows
        used = defaultdict(int)
        for k in range(a.fresh_sets):
            sizes = fresh_sizes(len(worlds), len(cells), a.fresh_size, k)
            for wi, w in enumerate(worlds):
                for ci, c in enumerate(cells):
                    n, start = sizes[(wi, ci)], used[(w, c)]
                    if start + n > len(shuffled[(w, c)]):
                        sys.exit(f"{w} x {c} has {len(shuffled[(w, c)])} summaries; fresh set "
                                 f"{k + 1} needs {start + n}")
                    picks += [(f"fresh{k + 1}", r) for r in shuffled[(w, c)][start:start + n]]
                    used[(w, c)] += n
        if a.practice:
            if a.practice % len(worlds):
                sys.exit(f"--practice {a.practice} is not a multiple of the {len(worlds)} worlds")
            pcells = [c for c in a.practice_cells.split(",") if c]
            if set(pcells) & set(cells):
                sys.exit("--practice-cells must not overlap --cells")
            pstrata = _load(exp, a.turn, pcells)
            per_world = a.practice // len(worlds)
            practice = []
            for w in worlds:
                rows = sorted((r for (pw, _), v in pstrata.items() if pw == w for r in v),
                              key=lambda r: r["summary_id"])
                rng.shuffle(rows)
                if len(rows) < per_world:
                    sys.exit(f"{w}: {len(rows)} practice summaries in {pcells}, need {per_world}")
                practice += [("practice", r) for r in rows[:per_world]]
            picks = practice + picks

    out_rows = _write(exp, a.turn, picks, a.seed)
    for round_name in dict.fromkeys(r["round"] for r in out_rows):
        rs = [r for r in out_rows if r["round"] == round_name]
        by_world = {w: sum(r["world"] == w for r in rs) for w in sorted({r["world"] for r in rs})}
        by_cell = {c: sum(r["cell"] == c for r in rs) for c in sorted({r["cell"] for r in rs})}
        print(f"{round_name}: {len(rs)} summaries -> exports/{a.batch}/calibration/{round_name}/"
              f"  by world {by_world}  by cell {by_cell}")
    print(f"key: exports/{a.batch}/key/calibration_sets.csv (study lead only)")


if __name__ == "__main__":
    main()
