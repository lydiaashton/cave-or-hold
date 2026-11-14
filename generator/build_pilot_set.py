"""Build the pilot datasets: ten per world, never used in the main runs (study lead, 14 Nov 2026).

Each world's pilot set is the next ten in the same seed sequence after the 60 main datasets, under
the same rules, so the two sets cannot overlap:
  - confounded and strong: datasets 61 to 70 the generator accepts (generate(w, k=70)); the first
    60 of that build must be byte-identical to out/;
  - underpowered: the first ten candidates in underpowered_candidates/ that meet the selection rule
    (select_underpowered.py) but were not kept for the main set.

Usage (from generator/):  python3 build_pilot_set.py out_pilot
then  python3 build_answer_key.py out_pilot  and  python3 relabel_for_release.py out_pilot ../release_pilot
"""
import csv
import filecmp
import json
import os
import shutil
import sys
import tempfile

import caveworlds_did as c

N_MAIN, N_PILOT = 60, 10


def main(out="out_pilot"):
    os.makedirs(out, exist_ok=True)
    for w in ("confounded", "strong"):
        main_man = json.load(open(f"out/manifest_{w}.json"))
        with tempfile.TemporaryDirectory() as tmp:
            man = c.generate(w, k=N_MAIN + N_PILOT, outdir=tmp, verbose=False)
            if man["datasets"][:N_MAIN] != main_man["datasets"] or not all(
                    filecmp.cmp(f"out/{d['file']}", f"{tmp}/{d['file']}", shallow=False)
                    for d in main_man["datasets"]):
                sys.exit(f"{w}: the first {N_MAIN} do not match out/; stop")
            pilot = man["datasets"][N_MAIN:]
            for d in pilot:
                shutil.copy2(f"{tmp}/{d['file']}", f"{out}/{d['file']}")
        man = {**man, "datasets": pilot,
               "pilot_set": f"datasets {N_MAIN + 1} to {N_MAIN + N_PILOT} accepted by the generator, "
                            f"after the {N_MAIN} main datasets; never used in the main runs"}
        json.dump(man, open(f"{out}/manifest_{w}.json", "w"), indent=2)
        print(w, [d["seed"] for d in pilot])

    cand = json.load(open("underpowered_candidates/manifest_underpowered.json"))
    rows = list(csv.DictReader(open("underpowered_candidates/selection.csv")))
    main_seeds = {d["seed"] for d in json.load(open("out/manifest_underpowered.json"))["datasets"]}
    meets = [r for r in rows if r["in_band"] == r["defensible_specs_ok"] == r["clears_floor"] == "True"]
    extra = [r for r in meets if r["kept"] == "False" and int(r["seed"]) not in main_seeds][:N_PILOT]
    if len(extra) < N_PILOT:
        sys.exit(f"underpowered: only {len(extra)} candidates beyond the main set meet the rule")
    by_file = {d["file"]: d for d in cand["datasets"]}
    pilot = []
    for r in extra:
        d = by_file[r["file"]]
        pilot.append({**d, "bootstrap_checks": {"generator": float(r["boot_generator"]),
                                                "base_r": float(r["boot_base_r"]),
                                                "python": float(r["boot_python"])}})
        shutil.copy2(f"underpowered_candidates/{r['file']}", f"{out}/{r['file']}")
    main_up = json.load(open("out/manifest_underpowered.json"))
    man = {**cand, "datasets": pilot, "selection": main_up["selection"],
           "pilot_set": f"the first {N_PILOT} candidates meeting the selection rule after the "
                        f"{N_MAIN} main datasets; never used in the main runs"}
    json.dump(man, open(f"{out}/manifest_underpowered.json", "w"), indent=2)
    print("underpowered", [d["seed"] for d in pilot])


if __name__ == "__main__":
    main(*sys.argv[1:])
