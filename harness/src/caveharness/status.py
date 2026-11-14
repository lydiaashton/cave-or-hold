"""The run plan and what has been done of it, per machine (handoff section 8).

    uv run python -m caveharness.status --batch pilot1 \
        --model openai-api/adaption/qwen3.5-397b \
        --worlds underpowered,confounded --datasets first5 --runs-per-cell 5 --n-machines 2

Pass the same values as the -T arguments of the run. It rebuilds the exact plan
the task builds (plan.build + plan.deal, same seed), so every machine's share is
known in advance, and compares it with the run logs on disk (merge every
machine's runs/<batch>/ first). Writes runs/<batch>/plan_<model>.csv: one row
per planned run, in send order, with its machine and status. Prints, per
machine, how many runs count for the primary analysis (turn 4 on disk), how many
reached turn 8, the units still to run, and the command that re-runs only those.
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict

from caveharness import plan as planmod
from caveharness.config import RUNS_DIR
from caveharness.export import load_runs, write_csv


def status_rows(units: list[planmod.Unit], runs: dict[str, dict], model: str) -> list[dict]:
    """One row per planned run. A run log is matched to the plan by its header
    (model, unit_id, condition), not by file location."""
    found: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in runs.values():
        h = r["header"]
        if h["model"] == model:
            found[(h["unit_id"], h["condition"])].append(r)
    rows = []
    for u in sorted(units, key=lambda x: x.order_index):
        for c in u.conditions:
            logs = found.get((u.unit_id, c), [])
            best = max((r["completed_turn"] for r in logs), default=None)
            status = ("missing" if best is None else "complete" if best >= 8
                      else "primary_ok" if best >= 4 else "failed_before_turn4")
            rows.append({"order_index": u.order_index, "machine_index": u.machine_index,
                         "unit_id": u.unit_id, "condition": c, "world": u.world,
                         "dataset_seed": u.seed, "replicate": u.replicate, "status": status,
                         "completed_turn": "" if best is None else best,
                         "machines_seen": ",".join(sorted({r["header"]["machine"] for r in logs}))})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--batch", required=True)
    ap.add_argument("--model", required=True, help="model string as passed to inspect eval")
    ap.add_argument("--worlds", default="underpowered,confounded")
    ap.add_argument("--datasets", default="first5")
    ap.add_argument("--runs-per-cell", type=int, default=5)
    ap.add_argument("--conditions", default="never,before,after")
    ap.add_argument("--shuffle-seed", type=int, default=20261113)
    ap.add_argument("--n-machines", type=int, default=1)
    a = ap.parse_args()

    units = planmod.deal(planmod.build(a.worlds.split(","), a.datasets, a.runs_per_cell,
                                       a.conditions.split(","), a.shuffle_seed), a.n_machines)
    rows = status_rows(units, load_runs(a.batch), a.model)
    out = RUNS_DIR / a.batch / f"plan_{re.sub(r'[^A-Za-z0-9.-]+', '_', a.model)}.csv"
    write_csv(out, rows)

    print(f"{len(units)} units, {len(rows)} planned runs for {a.model} -> {out}\n")
    # A unit is re-run only if none of its runs counts yet: re-running a pair
    # replaces both logs, and a run with turn 4 on disk counts for the primary
    # analysis (handoff 1). Mixed pairs are listed for the study lead to decide.
    counts = {"complete", "primary_ok"}
    by_unit: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_unit[r["unit_id"]].append(r)
    redo: dict[int, set[str]] = defaultdict(set)
    mixed: dict[int, set[str]] = defaultdict(set)
    for unit, rs in by_unit.items():
        if any(r["status"] not in counts for r in rs):
            target = mixed if any(r["status"] in counts for r in rs) else redo
            target[rs[0]["machine_index"]].add(unit)

    print(f"{'machine':>7} {'planned':>7} {'turn 4 on disk':>14} {'turn 8':>6} {'to re-run':>9}")
    for m in range(a.n_machines):
        mine = [r for r in rows if r["machine_index"] == m]
        st = Counter(r["status"] for r in mine)
        print(f"{m:>7} {len(mine):>7} {st['complete'] + st['primary_ok']:>14} "
              f"{st['complete']:>6} {len(redo[m]):>9}")

    # Handoff 8: machine must not stand in for condition. Runs on disk, by the
    # machine that actually ran them.
    seen = Counter((r["machines_seen"], r["world"], r["condition"]) for r in rows
                   if r["status"] in ("complete", "primary_ok"))
    if seen:
        print("\nRuns with turn 4 on disk, by machine x world x condition:")
        for (mach, w, c), n in sorted(seen.items()):
            print(f"  {mach or '?':30} {w:13} {c:7} {n}")

    for m, ids in sorted(redo.items()):
        if ids:
            print(f"\nmachine {m}: {len(ids)} unit(s) with no run at turn 4. Re-run them with "
                  f"the same command and -T arguments as before (limit_units 0), plus:\n"
                  f"  --sample-id {','.join(sorted(ids))}\n"
                  f"  (old logs are kept as .prev-* and ignored)")
    for m, ids in sorted(mixed.items()):
        if ids:
            print(f"\nmachine {m}: {len(ids)} pair(s) where one run counts and the other has no "
                  f"turn 4: {', '.join(sorted(ids))}\n  Re-running a pair would replace the run "
                  f"that counts; decide with the study lead before re-running these.")


if __name__ == "__main__":
    main()
