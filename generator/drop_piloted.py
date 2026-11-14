"""Keep datasets used in pilots 1 and 2 out of the main set (study lead, 14 Nov 2026).

Confounded and strong worlds. (The underpowered world is handled by select_underpowered.py, which
applies the same exclusion inside its selection rule.)

For each world with seeds in piloted_seeds.json: build the generator's accepted datasets in seed
order, leave out the piloted ones and the pilot-3 set (out_pilot/), and keep the first 60 of what
remains. With five piloted and ten in the pilot-3 set, that is accepted datasets 6 to 60 and 71 to 75.

Before writing anything it checks that every dataset already in out/ or out_pilot/ comes out of the
fresh build byte-identical, with an equal manifest entry.

Usage (from generator/, after caveworlds_did.py and build_pilot_set.py):  python3 drop_piloted.py
"""
import filecmp
import json
import os
import shutil
import sys
import tempfile

import caveworlds_did as c

N_MAIN = 60


def main(out="out", pilot_out="out_pilot"):
    piloted = json.load(open("piloted_seeds.json"))
    for w in ("confounded", "strong"):
        drop = set(piloted.get(w, []))
        if not drop:
            print(w, "no piloted datasets; unchanged")
            continue
        main_man = json.load(open(f"{out}/manifest_{w}.json"))
        pilot3 = json.load(open(f"{pilot_out}/manifest_{w}.json"))["datasets"]
        pilot3_seeds = {d["seed"] for d in pilot3}
        need = N_MAIN + len(pilot3) + len(drop)
        with tempfile.TemporaryDirectory() as tmp:
            man = c.generate(w, k=need, outdir=tmp, verbose=False)
            fresh = {d["seed"]: d for d in man["datasets"]}
            for src, ds in ((out, main_man["datasets"]), (pilot_out, pilot3)):
                for d in ds:
                    if fresh.get(d["seed"]) != d or not filecmp.cmp(
                            f"{src}/{d['file']}", f"{tmp}/{d['file']}", shallow=False):
                        sys.exit(f"{w}: {d['file']} in {src}/ does not match a fresh build; stop")
            if not drop <= set(fresh):
                sys.exit(f"{w}: piloted seeds {sorted(drop - set(fresh))} are not accepted datasets")
            keep = [d for d in man["datasets"]
                    if d["seed"] not in drop and d["seed"] not in pilot3_seeds][:N_MAIN]
            if len(keep) < N_MAIN:
                sys.exit(f"{w}: only {len(keep)} datasets left; build more")
            keep_files = {d["file"] for d in keep}
            for f in os.listdir(out):
                if f.startswith(f"{w}_seed") and f.endswith(".csv") and f not in keep_files:
                    os.remove(f"{out}/{f}")
            for d in keep:
                shutil.copy2(f"{tmp}/{d['file']}", f"{out}/{d['file']}")
        man = {**man, "datasets": keep,
               "main_set": f"the first {N_MAIN} datasets the generator accepts, in seed order, leaving "
                           f"out the {len(drop)} used in pilots 1 and 2 (piloted_seeds.json) and the "
                           f"{len(pilot3)} in the pilot-3 set ({pilot_out}/); settled 14 Nov 2026, "
                           f"study lead"}
        json.dump(man, open(f"{out}/manifest_{w}.json", "w"), indent=2)
        print(w, "kept", len(keep), "dropped", sorted(drop),
              "added", sorted({d["seed"] for d in keep} - {d["seed"] for d in main_man["datasets"]}))


if __name__ == "__main__":
    main(*sys.argv[1:])
