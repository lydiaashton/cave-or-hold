"""Select the underpowered datasets for release (rule settled 14 Nov 2026).

Rule: primary p between .10 and .13; every defensible specification (two-way FE clustered by unit,
with and without covariates, and the collapsed 2x2 with classical, HC2 and HC3 SEs) at p >= .10;
and the wild cluster bootstrap p at or above .105 in all three implementations (the generator's
accept rule, wild_bootstrap_base_r.R and wild_bootstrap_check.py). Keep the first 60 that pass, in
seed order, leaving out any dataset used in a pilot: the seeds in piloted_seeds.json (pilots 1 and 2)
and the pilot-3 set in out_pilot/ (study lead, 14 Nov). Candidates come from the generator run with
primary p in [.10, .15]; every candidate is kept in underpowered_candidates/, inside the rule or not.

Usage (from generator/):
  python3 -c "import caveworlds_did as c; c.generate('underpowered', k=345, rules=c.Rules(weak_p_hi=0.15), outdir='underpowered_candidates', max_tries=40000)"
  python3 wild_bootstrap_check.py underpowered_candidates underpowered > underpowered_candidates/check_python.txt
  Rscript wild_bootstrap_base_r.R underpowered_candidates underpowered > underpowered_candidates/check_base_r.txt
  python3 select_underpowered.py underpowered_candidates underpowered_candidates out

Writes the kept CSVs and manifest_underpowered.json to <out>, and selection.csv (every candidate,
its four p-values and whether it was kept) to the selection folder.
"""
import csv
import json
import os
import re
import shutil
import sys

FLOOR = 0.105
N_KEEP = 60
P_LO, P_HI = 0.10, 0.13
DEFENSIBLE = ["twfe_no_cov|cluster", "twfe_with_cov|cluster",
              "collapsed_2x2|classical", "collapsed_2x2|HC2", "collapsed_2x2|HC3"]
SPEC_FLOOR = 0.10
PAT = r"(underpowered_seed\d+\.csv):.*wild bootstrap p ([0-9.]+)"


def read_checks(path):
    return {f: float(p) for f, p in re.findall(PAT, open(path).read())}


def main(build, seldir, out):
    man = json.load(open(os.path.join(build, "manifest_underpowered.json")))
    py = read_checks(os.path.join(seldir, "check_python.txt"))
    br = read_checks(os.path.join(seldir, "check_base_r.txt"))
    piloted = set(json.load(open("piloted_seeds.json"))["underpowered"])
    pilot3_path = os.path.join("out_pilot", "manifest_underpowered.json")
    pilot3 = ({d["seed"] for d in json.load(open(pilot3_path))["datasets"]}
              if os.path.exists(pilot3_path) else set())
    rows, kept = [], []
    for pos, d in enumerate(man["datasets"], start=1):
        f = d["file"]
        if f not in py or f not in br:
            sys.exit(f"missing check output for {f}")
        gen = d["diagnostics"]["wild_cluster_bootstrap"]["p"]
        prim = d["primary"]["p"]
        in_band = P_LO <= prim <= P_HI
        lowest_spec = min(d["specifications"][k]["p"] for k in DEFENSIBLE)
        specs_ok = lowest_spec >= SPEC_FLOOR
        clears = min(gen, py[f], br[f]) >= FLOOR
        in_pilot = d["seed"] in piloted or d["seed"] in pilot3
        keep = in_band and specs_ok and clears and not in_pilot and len(kept) < N_KEEP
        if keep:
            d = {**d, "bootstrap_checks": {"generator": gen, "base_r": br[f], "python": py[f]}}
            kept.append(d)
        rows.append({"search_position": pos, "seed": d["seed"], "file": f, "primary_p": prim,
                     "lowest_defensible_spec_p": lowest_spec,
                     "boot_generator": gen, "boot_base_r": br[f], "boot_python": py[f],
                     "in_band": in_band, "defensible_specs_ok": specs_ok, "clears_floor": clears,
                     "used_in_pilot_1_or_2": d["seed"] in piloted,
                     "in_pilot3_set": d["seed"] in pilot3, "kept": keep})
    if len(kept) < N_KEEP:
        sys.exit(f"only {len(kept)} pass; build more candidates")
    with open(os.path.join(seldir, "selection.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.startswith("underpowered_seed") and f.endswith(".csv"):
            os.remove(os.path.join(out, f))
    for d in kept:
        shutil.copy2(os.path.join(build, d["file"]), os.path.join(out, d["file"]))
    man_out = {**man, "datasets": kept,
               "selection": {"rule": f"primary p in [{P_LO}, {P_HI}]; every defensible specification "
                                     f"(clustered two-way FE, collapsed 2x2) p >= {SPEC_FLOOR}; wild "
                                     f"cluster bootstrap p >= {FLOOR} in the generator, base R and "
                                     f"Python checks; first {N_KEEP} passing, in seed order, leaving out "
                                     f"datasets used in pilots 1 and 2 (piloted_seeds.json) and the "
                                     f"pilot-3 set (out_pilot/)",
                             "candidates_built": man["accepted"], "draws_tried": man["tries"],
                             "kept": len(kept),
                             "candidates_meeting_rule": sum(r["in_band"] and r["defensible_specs_ok"]
                                                            and r["clears_floor"] for r in rows),
                             "meeting_rule_and_used_in_pilot_1_or_2": sum(
                                 r["in_band"] and r["defensible_specs_ok"] and r["clears_floor"]
                                 and r["used_in_pilot_1_or_2"] for r in rows),
                             "settled": "14 Nov 2026, study lead"}}
    json.dump(man_out, open(os.path.join(out, "manifest_underpowered.json"), "w"), indent=2)
    print(f"kept {len(kept)} of {len(rows)} candidates; last kept at search position "
          f"{next(r['search_position'] for r in rows if r['file'] == kept[-1]['file'])}")


if __name__ == "__main__":
    main(*sys.argv[1:])
