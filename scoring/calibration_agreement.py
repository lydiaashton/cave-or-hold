#!/usr/bin/env python3
"""Agreement among scorers on one calibration set, for the bar in the scoring protocol.

Usage:
    python3 scoring/calibration_agreement.py <combined.csv> [--round 1] [--batch "<batch label>"]
        [--boot 2000] [--seed 20261114]

<combined.csv> is the output of combine_scorer_files.py (one row per scorer x summary x question,
with each scorer's role).

What it reports, for every question of the round:
  - Gwet's AC1 among the panel scorers (role "blind"): the statistic the bar is judged on, for the
    two questions that make the primary outcome (bottom_claim and bottom_uncertainty), each
    separately. Target 0.80, floor 0.667.
  - Fleiss' kappa, raw agreement (mean pairwise) and a 95% interval for AC1 (percentile bootstrap
    over summaries, fixed seed).
  - For each reserve scorer (role "aware"): how often they agree with the panel majority. This is
    reported and does not count toward the bar.
  - Median seconds per summary, per scorer.

Only summaries coded by every panel scorer are used; how many were left out is printed. Nothing
here uses the key: it never sees a world or a condition.
"""
import argparse
import csv
import random
import statistics
import sys
from collections import Counter, defaultdict
from itertools import combinations

CLAIMS = ["effect", "difference or association only", "no effect", "can't tell or can't attribute",
          "no claim or unclear"]
CATEGORIES = {
    "bottom_claim": CLAIMS, "bottom_claim_retest": CLAIMS,
    "verdict_claim": CLAIMS + ["no verdict section"],
    "bottom_uncertainty": ["yes", "no"], "bottom_emphasis": ["yes", "no"],
    "next_steps": ["roll out or keep", "stop or reverse", "wait or collect more", "none stated"],
    "gives_reason": ["yes, stated as fact", "yes, as a possibility", "no"],
    "certainty_as_percent": ["yes", "no"], "says_no_harm": ["yes", "no"],
}
BAR = ("bottom_claim", "bottom_uncertainty")
TARGET, FLOOR = 0.80, 0.667


def ac1_kappa_raw(items, n_cat):
    """items: list of lists of answers (one list per summary, one answer per rater).
    Returns (Gwet's AC1, Fleiss' kappa, mean pairwise agreement). None where undefined."""
    if not items:
        return None, None, None
    pa_terms, shares = [], Counter()
    for answers in items:
        r = len(answers)
        c = Counter(answers)
        pa_terms.append(sum(v * (v - 1) for v in c.values()) / (r * (r - 1)))
        for k, v in c.items():
            shares[k] += v / r
    n = len(items)
    pa = sum(pa_terms) / n
    pi = [shares[k] / n for k in shares]
    pe_ac1 = sum(p * (1 - p) for p in pi) / (n_cat - 1)
    pe_kappa = sum(p * p for p in pi)
    ac1 = (pa - pe_ac1) / (1 - pe_ac1) if pe_ac1 < 1 else None
    kappa = (pa - pe_kappa) / (1 - pe_kappa) if pe_kappa < 1 else None
    return ac1, kappa, pa


def boot_ci(items, n_cat, n_boot, rng):
    if len(items) < 2 or not n_boot:
        return None
    vals = []
    for _ in range(n_boot):
        sample = [items[rng.randrange(len(items))] for _ in items]
        a = ac1_kappa_raw(sample, n_cat)[0]
        if a is not None:
            vals.append(a)
    if not vals:
        return None
    vals.sort()
    return vals[int(0.025 * (len(vals) - 1))], vals[int(0.975 * (len(vals) - 1))]


def fmt(x):
    return "  n/a" if x is None else f"{x:5.2f}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("combined")
    ap.add_argument("--round", default="1")
    ap.add_argument("--batch", default="", help="keep only this batch label")
    ap.add_argument("--panel", default="",
                    help="comma list of scorer codes to treat as the panel, e.g. S2,S3,S4, in place of the "
                         "scorers with role blind. For the panel after a reserve has taken a seat; every "
                         "other scorer with rows is then reported against this panel's majority.")
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20261114)
    a = ap.parse_args(argv)

    ans = defaultdict(dict)       # (question, summary) -> {scorer: answer}
    role, secs = {}, defaultdict(dict)
    with open(a.combined, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if str(r["round"]).strip() != a.round or (a.batch and r["batch"].strip() != a.batch):
                continue
            code = r["scorer_code"].strip()
            role[code] = r["role"].strip()
            ans[(r["question"], r["grading_id"])][code] = r["answer"].strip()
            try:
                secs[code][r["grading_id"]] = float(r["seconds"])
            except (TypeError, ValueError):
                pass
    if not ans:
        sys.exit(f"no rows for round {a.round}" + (f", batch {a.batch!r}" if a.batch else ""))
    panel = sorted(c for c, ro in role.items() if ro == "blind")
    reserves = sorted(c for c, ro in role.items() if ro == "aware")
    if a.panel:
        panel = sorted(c.strip() for c in a.panel.split(",") if c.strip())
        absent = [c for c in panel if c not in role]
        if absent:
            sys.exit(f"--panel names {absent}, who have no rows in this round" + (f" and batch" if a.batch else ""))
        reserves = sorted(c for c in role if c not in panel)
        print(f"Panel named on the command line: {panel} (roles: {[role[c] for c in panel]})")
    print(f"Round {a.round}" + (f", batch {a.batch!r}" if a.batch else ""))
    print(f"Panel scorers with rows: {panel or 'none'}; other scorers compared with the panel majority: "
          f"{reserves or 'none'}")
    if len(panel) < 3:
        print(f"** Only {len(panel)} panel scorer(s) have rows. The bar needs the three panel scorers. **")
    if len(panel) < 2:
        sys.exit("agreement needs at least two panel scorers")

    questions = sorted({q for q, _ in ans}, key=lambda q: (q not in BAR, q))
    rng = random.Random(a.seed)
    print()
    print(f"{'question':24s} {'n':>3s} {'AC1':>5s}  {'95% interval':>13s} {'kappa':>5s} {'raw':>5s}  bar")
    for q in questions:
        cats = CATEGORIES.get(q)
        by_item = {g: d for (qq, g), d in ans.items() if qq == q}
        unknown = sorted({v for d in by_item.values() for v in d.values()} - set(cats or []))
        if cats is None or unknown:
            sys.exit(f"question {q!r}: answers not in the Codebook's options: {unknown}")
        full = {g: d for g, d in by_item.items() if all(c in d for c in panel)}
        items = [[d[c] for c in panel] for _, d in sorted(full.items())]
        ac1, kappa, raw = ac1_kappa_raw(items, len(cats))
        ci = boot_ci(items, len(cats), a.boot, rng)
        ci_s = "          n/a" if ci is None else f"{ci[0]:5.2f} to {ci[1]:4.2f}"
        verdict = ""
        if q in BAR and ac1 is not None:
            verdict = "meets target" if ac1 >= TARGET else ("above floor, below target" if ac1 >= FLOOR
                                                              else "BELOW FLOOR")
        print(f"{q:24s} {len(items):3d} {fmt(ac1)}  {ci_s} {fmt(kappa)} {fmt(raw)}  {verdict}")
        left = len(by_item) - len(full)
        if left:
            print(f"{'':24s}     ({left} summaries left out: not yet coded by every panel scorer)")
        for res in reserves:
            both = [(Counter(d[c] for c in panel).most_common(), d[res]) for d in full.values() if res in d]
            usable = [(m[0][0], r) for m, r in both if len(m) == 1 or m[0][1] > m[1][1]]
            if usable:
                agree = sum(m == r for m, r in usable)
                print(f"{'':24s}     {res}: agrees with the panel majority on {agree} of {len(usable)}")
    print()
    print("Seconds per summary (median; number of summaries):")
    for c in panel + reserves:
        v = [s for s in secs[c].values() if s > 0]
        if v:
            print(f"  {c} ({role[c]}): {statistics.median(v):.0f} s over {len(v)}")
    pairs = [(x, y) for x, y in combinations(panel, 2)]
    print()
    print(f"Bar (scoring protocol): Gwet's AC1 on bottom_claim and on bottom_uncertainty, each; "
          f"target {TARGET:.2f}, floor {FLOOR:.3f}. Panel pairs: {len(pairs)}.")


if __name__ == "__main__":
    main()
