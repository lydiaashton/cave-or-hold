"""Relabel generator v2 CSVs to scenario terms for the model sandbox.

Reads out/<world>_seed<seed>.csv (generator names; the answer key and manifests refer to these)
and writes release/<world>_seed<seed>/branches.csv with scenario column names.
Relabelling only: no value of the outcome, treatment or covariates changes.

  unit         -> branch_id        (unchanged values)
  period 0..16 -> week 6..22       (period + 6; the switch is at week 15, i.e. period 9)
  treated_unit -> switched_branch
  post         -> after_switch
  D            -> dropped (it equals switched_branch x after_switch)
  y            -> service_score
  x1, x2       -> staffing_index, visits_index

The folder name carries the world and seed for engineering. Only branches.csv goes into the
tested model's sandbox, under that neutral file name; the folder name must not be visible to it.
"""
import glob, json, os, sys
import numpy as np, pandas as pd

WEEK_OFFSET = 6
RENAME = {"unit": "branch_id", "period": "week", "treated_unit": "switched_branch",
          "post": "after_switch", "y": "service_score", "x1": "staffing_index", "x2": "visits_index"}

def relabel(df):
    out = df.drop(columns=["D"]).rename(columns=RENAME)
    out["week"] = out["week"] + WEEK_OFFSET
    return out

def twfe(df, unit, time, y, d, covs):
    """Two-way fixed effects coefficient on d, by dummy regression."""
    X = np.column_stack([df[d].to_numpy(float)] + [df[c].to_numpy(float) for c in covs]
                        + [pd.get_dummies(df[unit], dtype=float).to_numpy()]
                        + [pd.get_dummies(df[time], dtype=float).to_numpy()[:, 1:]])
    return np.linalg.lstsq(X, df[y].to_numpy(float), rcond=None)[0][0]

def main(src="out", dst="release"):
    rows = []
    for world in ("underpowered", "confounded", "strong"):
        man = json.load(open(os.path.join(src, f"manifest_{world}.json")))
        for d in man["datasets"]:
            raw = pd.read_csv(os.path.join(src, d["file"]), float_precision="round_trip")
            rel = relabel(raw)
            folder = os.path.join(dst, d["file"].replace(".csv", ""))
            os.makedirs(folder, exist_ok=True)
            rel.to_csv(os.path.join(folder, "branches.csv"), index=False)
            rel = pd.read_csv(os.path.join(folder, "branches.csv"), float_precision="round_trip")
            rel["D_check"] = rel["switched_branch"] * rel["after_switch"]
            est = twfe(rel, "branch_id", "week", "service_score", "D_check", ["staffing_index", "visits_index"])
            rows.append({"world": world, "file": d["file"], "release_path": os.path.join(folder, "branches.csv"),
                         "rows": len(rel), "weeks": f"{rel.week.min()}-{rel.week.max()}",
                         "switch_week": int(rel.loc[rel.after_switch == 1, "week"].min()),
                         "manifest_estimate": d["primary"]["estimate"], "relabelled_estimate": est,
                         "abs_diff": abs(est - d["primary"]["estimate"]),
                         "D_matches": bool((raw["D"].to_numpy() == rel["D_check"].to_numpy()).all()),
                         "y_identical": bool(np.array_equal(raw["y"].to_numpy(), rel["service_score"].to_numpy()))})
    chk = pd.DataFrame(rows)
    chk.to_csv(os.path.join(dst, "RELABEL_CHECK.csv"), index=False)
    print(chk[["file", "rows", "weeks", "switch_week", "manifest_estimate", "relabelled_estimate", "abs_diff", "D_matches", "y_identical"]].to_string(index=False))
    ok = (chk.abs_diff < 1e-8).all() and chk.D_matches.all() and chk.y_identical.all()
    print("ALL CHECKS PASS" if ok else "CHECK FAILED"); sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main(*sys.argv[1:])
