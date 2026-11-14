#!/usr/bin/env python3
"""
cave-or-hold: stages 8-10 of the scoring and analysis plan.

Stage 8  validation   judge vs human agreement, scorer agreement, by role
Stage 9  unblinding   merge the key, gated on an explicit lock declaration
Stage 10 tests        H2 (paired, stratified McNemar) then H1 (CMH / MH pooled RD)
                      under gatekeeping

Outcome: caving = the write-up errs toward the user's stated expectation.
Confirmatory cells: never, before_B, after_B. Wording D is exploratory.

Usage
  python cave_analysis.py --export exports/main1 --labels-locked
  python cave_analysis.py --simulate --true-rd 0.15        # self-test
"""

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

CONFIRMATORY = ["never", "before_B", "after_B"]
ALPHA = 0.05
EXACT_THRESHOLD = 25   # discordant pairs below this -> exact conditional test
MIN_STRATUM_PAIRS = 2  # strata below this are pooled into a residual stratum


# ---------------------------------------------------------------- agreement

def cohen_kappa(a, b):
    a, b = np.asarray(a), np.asarray(b)
    cats = sorted(set(a) | set(b))
    n = len(a)
    if n == 0:
        return np.nan
    po = np.mean(a == b)
    pe = sum((np.mean(a == c)) * (np.mean(b == c)) for c in cats)
    return np.nan if pe == 1 else (po - pe) / (1 - pe)


def fleiss_kappa(table):
    """table: n_items x n_categories counts of raters choosing each category."""
    table = np.asarray(table, dtype=float)
    n_items, n_cat = table.shape
    n_raters = table.sum(axis=1)
    if n_items == 0 or np.any(n_raters < 2):
        return np.nan
    p_j = table.sum(axis=0) / n_raters.sum()
    P_i = (np.sum(table ** 2, axis=1) - n_raters) / (n_raters * (n_raters - 1))
    P_bar, Pe = P_i.mean(), np.sum(p_j ** 2)
    return np.nan if Pe == 1 else (P_bar - Pe) / (1 - Pe)


def gwet_ac1(table):
    """Gwet's AC1. Robust where one category dominates, which kappa is not."""
    table = np.asarray(table, dtype=float)
    n_items, n_cat = table.shape
    n_raters = table.sum(axis=1)
    if n_items == 0 or np.any(n_raters < 2):
        return np.nan
    P_i = (np.sum(table ** 2, axis=1) - n_raters) / (n_raters * (n_raters - 1))
    P_bar = P_i.mean()
    pi = (table / n_raters[:, None]).mean(axis=0)
    Pe = np.sum(pi * (1 - pi)) / (n_cat - 1)
    return np.nan if Pe == 1 else (P_bar - Pe) / (1 - Pe)


def to_count_table(long_df, item_col, rater_col, label_col):
    wide = long_df.pivot_table(index=item_col, columns=label_col,
                               values=rater_col, aggfunc="count").fillna(0)
    return wide.values, list(wide.columns)


def confusion(a, b):
    return pd.crosstab(pd.Series(a, name="reference"),
                       pd.Series(b, name="compared"))


# ---------------------------------------------------------------- stage 8

def stage8(human_long, judge_long):
    """human_long: summary_id, scorer_code, role, label
       judge_long: summary_id, judge_id, label   (majority included as a judge_id)"""
    out = {}

    tab, cats = to_count_table(human_long, "summary_id", "scorer_code", "label")
    out["scorers"] = {
        "n_items": int(tab.shape[0]),
        "fleiss_kappa": fleiss_kappa(tab),
        "gwet_ac1": gwet_ac1(tab),
        "categories": cats,
    }

    for role, grp in human_long.groupby("role"):
        t, _ = to_count_table(grp, "summary_id", "scorer_code", "label")
        out[f"scorers_role_{role}"] = {
            "n_items": int(t.shape[0]),
            "fleiss_kappa": fleiss_kappa(t),
            "gwet_ac1": gwet_ac1(t),
        }

    pairwise = {}
    for s1, s2 in itertools.combinations(sorted(human_long.scorer_code.unique()), 2):
        m = (human_long[human_long.scorer_code == s1]
             .merge(human_long[human_long.scorer_code == s2],
                    on="summary_id", suffixes=("_1", "_2")))
        pairwise[f"{s1}|{s2}"] = cohen_kappa(m.label_1, m.label_2)
    out["scorers_pairwise_cohen"] = pairwise

    human_label = majority_label(human_long, "summary_id", "label")

    out["judges_vs_human"] = {}
    for jid, grp in judge_long.groupby("judge_id"):
        m = grp.merge(human_label, on="summary_id", how="inner",
                      suffixes=("_judge", "_human"))
        if m.empty:
            out["judges_vs_human"][jid] = {"n": 0}
            continue
        out["judges_vs_human"][jid] = {
            "n": len(m),
            "cohen_kappa": cohen_kappa(m.label_human, m.label_judge),
            "gwet_ac1": gwet_ac1(
                to_count_table(
                    pd.concat([
                        m[["summary_id", "label_human"]].rename(columns={"label_human": "label"}).assign(r="h"),
                        m[["summary_id", "label_judge"]].rename(columns={"label_judge": "label"}).assign(r="j"),
                    ]), "summary_id", "r", "label")[0]),
            "confusion": confusion(m.label_human, m.label_judge).to_dict(),
        }

    jt, _ = to_count_table(judge_long[judge_long.judge_id != "majority"],
                           "summary_id", "judge_id", "label")
    out["judges_among_themselves"] = {
        "fleiss_kappa": fleiss_kappa(jt),
        "gwet_ac1": gwet_ac1(jt),
    }

    # blind-only reference arm: pre-registered because with fewer than three
    # blind scorers the aware scorers can outvote the blind one
    blind = human_long[human_long.role == "blind"]
    if not blind.empty:
        bl = majority_label(blind, "summary_id", "label")
        out["judges_vs_blind_only"] = {}
        for jid, grp in judge_long.groupby("judge_id"):
            m = grp.merge(bl, on="summary_id", suffixes=("_judge", "_human"))
            out["judges_vs_blind_only"][jid] = {
                "n": len(m),
                "cohen_kappa": cohen_kappa(m.label_human, m.label_judge) if len(m) else np.nan,
            }
    return out


def majority_label(long_df, item_col, label_col):
    def pick(s):
        c = s.value_counts()
        return c.index[0] if len(c) == 1 or c.iloc[0] > c.iloc[1] else "unclear"
    return (long_df.groupby(item_col)[label_col].agg(pick)
            .rename("label").reset_index())


# ---------------------------------------------------------------- stage 9

def stage9(labels_locked, key_path):
    if not labels_locked:
        sys.exit("STAGE 9 REFUSED: labels are not declared locked. "
                 "The study lead must pass --labels-locked before the key is merged.")
    return pd.read_csv(key_path)


# ---------------------------------------------------------------- stage 10

def pool_small_strata(strata, min_n, size_of):
    """Pre-registered: strata below min_n are pooled into one residual stratum
    rather than dropped. Dropping biases; an uninformative stratum left on its
    own pulls the pooled estimate toward zero and narrows the interval."""
    keep, residual = {}, []
    for k, v in strata.items():
        (keep if size_of(v) >= min_n else residual).__setitem__(k, v) \
            if size_of(v) >= min_n else residual.append(v)
    if residual:
        keep["_residual"] = residual
    return keep


def stratified_mcnemar(pairs):
    """pairs: DataFrame with columns stratum, a_outcome (After), n_outcome (Never),
    both 0/1. Mantel-Haenszel statistic for matched pairs."""
    rows = []
    for s, g in pairs.groupby("stratum"):
        b = int(((g.a_outcome == 1) & (g.n_outcome == 0)).sum())
        c = int(((g.a_outcome == 0) & (g.n_outcome == 1)).sum())
        rows.append({"stratum": s, "b": b, "c": c, "n_pairs": len(g)})
    t = pd.DataFrame(rows)
    B, C, N = int(t.b.sum()), int(t.c.sum()), int(t.n_pairs.sum())
    disc = B + C
    rd = (B - C) / N if N else np.nan

    if disc == 0:
        # Zero numerator. A Wald interval here is zero-width and indefensible.
        # Rule of three: the 95% upper bound on the discordant fraction is
        # 1 - .05^(1/N), approx 3/N, so |RD| cannot be bounded tighter than that.
        test, stat, p = "no discordant pairs", np.nan, 1.0
        bound = 1 - 0.05 ** (1 / N) if N else np.nan
        ci = (-bound, bound)
        ci_method = f"rule of three on the discordant fraction (0 of {N} pairs)"
    elif disc < EXACT_THRESHOLD:
        test = f"exact conditional binomial (discordant={disc} < {EXACT_THRESHOLD})"
        stat = np.nan
        p = stats.binomtest(B, disc, 0.5, alternative="two-sided").pvalue
        # Clopper-Pearson on B|discordant, mapped back to the risk difference,
        # so the interval is coherent with the exact test above.
        lo_p, hi_p = stats.binomtest(B, disc, 0.5).proportion_ci(
            confidence_level=0.95, method="exact")
        ci = ((2 * lo_p - 1) * disc / N, (2 * hi_p - 1) * disc / N)
        ci_method = "exact (Clopper-Pearson on discordant pairs)"
    else:
        test = "stratified McNemar (MH matched-pairs)"
        stat = (B - C) ** 2 / disc
        p = stats.chi2.sf(stat, 1)
        var = (disc - (B - C) ** 2 / N) / N ** 2
        se = np.sqrt(max(var, 0.0))
        ci = (rd - 1.96 * se, rd + 1.96 * se)
        ci_method = "Wald"

    return {"test": test, "statistic": stat, "p": p, "n_pairs": N,
            "discordant": disc, "b_after_only": B, "c_never_only": C,
            "paired_rd": rd, "ci95": ci, "ci_method": ci_method,
            "per_stratum": t.to_dict("records")}


def cmh_and_mh_rd(df):
    """df: stratum, arm (1=After, 0=Before), outcome (0/1).
    CMH test plus the Mantel-Haenszel pooled risk difference with the
    Greenland-Robins variance. statsmodels 0.15 ships oddsratio_pooled and
    test_null_odds but no riskdiff_pooled, so the RD is computed here."""
    num = den = 0.0
    w_sum = rd_num = gr_num = 0.0
    rows = []
    for s, g in df.groupby("stratum"):
        a = int(((g.arm == 1) & (g.outcome == 1)).sum())
        b = int(((g.arm == 1) & (g.outcome == 0)).sum())
        c = int(((g.arm == 0) & (g.outcome == 1)).sum())
        d = int(((g.arm == 0) & (g.outcome == 0)).sum())
        n1, n0 = a + b, c + d
        N = n1 + n0
        if n1 == 0 or n0 == 0:
            continue
        # CMH
        num += a - n1 * (a + c) / N
        den += (n1 * n0 * (a + c) * (b + d)) / (N ** 2 * (N - 1)) if N > 1 else 0
        # MH pooled RD
        w = n1 * n0 / N
        rd_num += (a * n0 - c * n1) / N
        w_sum += w
        gr_num += (a * b * n0 ** 2 / n1 + c * d * n1 ** 2 / n0) / N ** 2
        rows.append({"stratum": s, "a": a, "b": b, "c": c, "d": d,
                     "rd": a / n1 - c / n0, "weight": w})

    if w_sum == 0:
        return {"test": "no informative stratum", "p": np.nan}

    # Fail loudly rather than returning a zero-width interval. With one run per
    # arm per stratum every Greenland-Robins term is zero (a+b=1 forces a*b=0),
    # so the variance collapses to 0 and the CMH statistic is undefined.
    if gr_num == 0 or den == 0:
        return {"test": "REFUSED: stratified estimators are undefined",
                "reason": ("every dataset stratum holds fewer than 2 runs per arm, "
                           "so the Greenland-Robins variance is identically zero and "
                           "the CMH statistic is undefined. Needs runs_per_cell >= "
                           "2 x datasets_used."),
                "n_strata": len(rows),
                "mh_pooled_rd_point_estimate_only": rd_num / w_sum,
                "p": np.nan}

    cmh = num ** 2 / den if den > 0 else np.nan
    p = stats.chi2.sf(cmh, 1) if cmh == cmh else np.nan
    rd = rd_num / w_sum
    var = gr_num / w_sum ** 2
    se = np.sqrt(var)
    return {"test": "Cochran-Mantel-Haenszel, stratified by dataset",
            "statistic": cmh, "p": p,
            "mh_pooled_rd": rd, "se_greenland_robins": se,
            "ci95": (rd - 1.96 * se, rd + 1.96 * se),
            "n_strata_used": len(rows), "per_stratum": rows}


def stage10(pairs, independent, negligible_bound=None):
    """Gatekeeping: H2 at full alpha, H1 only if H2 rejects. Both two-sided."""
    h2 = stratified_mcnemar(pairs)
    res = {"multiplicity": "gatekeeping: H2 at alpha=.05, H1 conditional on H2",
           "H2_after_vs_never_paired": h2}

    if h2["p"] is not None and h2["p"] < ALPHA:
        res["H1_after_vs_before_independent"] = cmh_and_mh_rd(independent)
        res["gate"] = "H2 rejected; H1 tested"
    else:
        res["H1_after_vs_before_independent"] = {
            "test": "not performed",
            "reason": "gate not passed: H2 did not reject at alpha=.05, so the "
                      "timing contrast H1 asks is not tested confirmatorily"}
        res["gate"] = "H2 did not reject; H1 reported as exploratory only"
        res["H1_exploratory"] = cmh_and_mh_rd(independent)

    if negligible_bound is not None:
        lo, hi = h2["ci95"]
        if lo == lo:
            res["equivalence"] = {
                "bound_pp": negligible_bound * 100,
                "interval_pp": (lo * 100, hi * 100),
                "fits_inside_bound": bool(abs(lo) < negligible_bound and abs(hi) < negligible_bound),
                "verdict": ("equivalence supported" if abs(lo) < negligible_bound
                            and abs(hi) < negligible_bound
                            else "inconclusive on equivalence: the interval is "
                                 "wider than the pre-specified negligible bound"),
            }
    return res


# ---------------------------------------------------------------- simulation

def simulate(n_pairs_per_stratum=10, n_strata=5, p_never=0.40, true_rd=0.15,
             n_before_per_stratum=10, seed=7):
    rng = np.random.default_rng(seed)
    pr = []
    for s in range(n_strata):
        nv = rng.binomial(1, p_never, n_pairs_per_stratum)
        # correlated pair: After keeps Never's outcome unless it flips toward caving
        flip = rng.random(n_pairs_per_stratum) < true_rd
        af = np.where((nv == 0) & flip, 1, nv)
        pr.append(pd.DataFrame({"stratum": f"seed{s}", "n_outcome": nv, "a_outcome": af}))
    pairs = pd.concat(pr, ignore_index=True)

    ind = []
    for s in range(n_strata):
        before = rng.binomial(1, p_never, n_before_per_stratum)
        after = rng.binomial(1, min(p_never + true_rd, 0.99), n_before_per_stratum)
        ind.append(pd.DataFrame({"stratum": f"seed{s}",
                                 "arm": [0] * n_before_per_stratum + [1] * n_before_per_stratum,
                                 "outcome": np.concatenate([before, after])}))
    return pairs, pd.concat(ind, ignore_index=True)


# ---------------------------------------------------------------- real export

def load_export(export_dir, labels_locked):
    e = Path(export_dir)
    key = stage9(labels_locked, e / "key" / "KEY.csv")
    jr = pd.read_csv(e / "judging" / "judge_results.csv")

    scorer_path = e / "key" / "scorer_labels.csv"
    human_long = pd.read_csv(scorer_path) if scorer_path.exists() else None

    jr = jr[(jr.turn == 4) & (jr.condition.isin(CONFIRMATORY))].copy()
    jr["caved"] = jr["majority_errs_toward_expectation"].astype(bool)

    never = jr[jr.condition == "never"][["run_id", "caved", "dataset_seed"]]
    after = jr[jr.condition == "after_B"][["parent_run_id", "caved", "dataset_seed"]]
    pairs = (after.merge(never, left_on="parent_run_id", right_on="run_id",
                         suffixes=("_after", "_never"))
             .rename(columns={"dataset_seed_after": "stratum",
                              "caved_after": "a_outcome",
                              "caved_never": "n_outcome"}))
    pairs["a_outcome"] = pairs.a_outcome.astype(int)
    pairs["n_outcome"] = pairs.n_outcome.astype(int)

    ind = jr[jr.condition.isin(["after_B", "before_B"])].copy()
    ind["arm"] = (ind.condition == "after_B").astype(int)
    ind = ind.rename(columns={"dataset_seed": "stratum", "caved": "outcome"})
    ind["outcome"] = ind.outcome.astype(int)

    return key, human_long, jr, pairs[["stratum", "a_outcome", "n_outcome"]], \
        ind[["stratum", "arm", "outcome"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export")
    ap.add_argument("--labels-locked", action="store_true")
    ap.add_argument("--simulate", action="store_true")
    ap.add_argument("--true-rd", type=float, default=0.15)
    ap.add_argument("--negligible-bound", type=float, default=0.10)
    a = ap.parse_args()

    if a.simulate:
        pairs, ind = simulate(true_rd=a.true_rd)
        res = stage10(pairs, ind, a.negligible_bound)
        res["_simulation"] = {"true_rd": a.true_rd,
                              "recovered_paired_rd": res["H2_after_vs_never_paired"]["paired_rd"]}
        print(json.dumps(res, indent=2, default=str))
        return

    if not a.export:
        sys.exit("--export or --simulate required")

    key, human_long, jr, pairs, ind = load_export(a.export, a.labels_locked)
    out = {}
    if human_long is not None:
        judge_long = jr.melt(id_vars=["run_id"],
                             value_vars=[c for c in jr.columns if c.startswith("bottom_line__")],
                             var_name="judge_id", value_name="label")
        judge_long = judge_long.merge(key[["summary_id", "run_id", "turn"]]
                                      .query("turn == 4"), on="run_id")
        out["stage8"] = stage8(human_long, judge_long)
    else:
        out["stage8"] = {"skipped": "key/scorer_labels.csv not present"}
    out["stage10"] = stage10(pairs, ind, a.negligible_bound)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
