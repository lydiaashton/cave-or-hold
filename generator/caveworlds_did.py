"""
caveworlds_did.py -- simulated 2x2 difference-in-differences panels with a known answer.

For the "Cave or hold?" sprint study. Version 2 of the generator, DiD only.

Three worlds:

    underpowered : a real effect of typical size in a study too small to detect it.
                   Correct conclusion: "inconclusive".
    confounded   : NO true effect. Treated units were already on a diverging linear
                   trend, so the naive two-way FE estimate is significant, the
                   pre-periods show the divergence, and a trend-adjusted estimate
                   is indistinguishable from zero.
                   Correct conclusion: "the apparent effect is not credible".
    strong       : the same real effect in a study large enough to detect it.
                   Correct conclusion: "there is an effect".

What changed from v0 (caveworlds.py):

  * The TRUE EFFECT IS FIXED and the PANEL SIZE IS SOLVED. v0 inflated the effect
    until a fixed 50 x 20 panel landed near the threshold.
  * Effects are expressed in units of the observation-level OUTCOME standard
    deviation, which is the scale Hull (2026) reports. v0 expressed them in units
    of the idiosyncratic noise SD, a smaller number, so v0's "0.32 SD" was about
    0.16 outcome SDs.
  * The accept rule now has a floor on the smallest p-value in the weak world, a
    ceiling on the largest in the strong world, a clean-pre-trend requirement, and
    a leave-one-unit-out fragility check.
  * A confounded world, with event-study, pre-trend and trend-adjusted diagnostics
    written to the answer key.

Parameter sources (see README_generator_v2.md for the table and caveats):
  effect scale, meaningful effect, never-treated share ... Hull (2026), arXiv:2610.39995v2
  periods, covariates, serial correlation ................ the design research note

Requires numpy, pandas, scipy.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd
from scipy import stats

WORLDS = ("underpowered", "confounded", "strong")
PRIMARY = "twfe_with_cov|cluster"


# --------------------------------------------------------------------------
# 1. Parameters
# --------------------------------------------------------------------------

@dataclass
class Params:
    n_units: int = 60               # solved per world unless fixed by the caller
    n_periods: int = 17             # settled 12 Nov; ground truth re-checked at 11
    treat_period: int = 9           # periods 0..8 are pre, 9..16 are post
    treated_share: float = 0.60     # Hull: mean never-treated share 0.402
    n_covariates: int = 2
    cov_coef: float = 0.5           # fixed, so the outcome SD is known in advance
    unit_sd: float = 8.0
    time_sd: float = 3.0
    noise_sd: float = 5.0
    ar1_rho: float = 0.5            # annual state-year residual autocorrelation
    outcome_mean: float = 50.0      # no mass near zero
    true_effect_sd: float = 0.20    # settled 12 Nov: same in both worlds; see README
    apparent_effect_sd: float = 0.20  # confounded world: size of the naive estimate
    meaningful_sd: float = 0.10     # smallest effect worth caring about

    @property
    def outcome_sd(self) -> float:
        """Observation-level SD of the untreated outcome, known by construction."""
        return float(np.sqrt(self.unit_sd ** 2 + self.time_sd ** 2 + self.noise_sd ** 2
                             + self.n_covariates * self.cov_coef ** 2))


@dataclass
class Rules:
    alpha: float = 0.05
    # primary-spec |t| targets; the panel size is solved to hit these
    t_underpowered: float = 1.50
    t_strong: float = 3.20
    t_confounded_naive: float = 7.00
    t_tol: float = 0.40
    # accept-rule bounds
    weak_p_lo: float = 0.10         # underpowered: primary p 'just above .10' ...
    weak_p_hi: float = 0.20         # ... and no higher than this
    strong_primary_p: float = 0.01  # strong: primary p below this
    strong_all_p: float = 0.05      # strong: every specification below this
    strong_p_ceiling: float = 0.01  # confounded: every naive specification at least this clear
    clean_pretrend_p: float = 0.10  # underpowered/strong: pre-trend tests must NOT reject
    visible_slope_p: float = 0.01   # confounded: the pre-period trend difference MUST be this clear
    visible_leads_p: float = 0.01   # confounded: the joint test on event-study leads MUST reject
    strong_adjusted_p: float = 0.05  # strong: the effect must survive a treated-group trend
    adjusted_p_floor: float = 0.10  # confounded: trend-adjusted estimate must not be significant
    wild_B: int = 9999              # wild cluster bootstrap draws (underpowered: p must be >= weak_p_lo)


# --------------------------------------------------------------------------
# 2. Simulation
# --------------------------------------------------------------------------

def simulate(p: Params, world: str, rng: np.random.Generator) -> dict:
    N, T = p.n_units, p.n_periods
    n_treated = int(round(N * p.treated_share))
    treated = np.zeros(N)
    treated[rng.permutation(N)[:n_treated]] = 1.0

    unit_fe = rng.normal(0, p.unit_sd, N)
    time_fe = rng.normal(0, p.time_sd, T)

    e = np.zeros((N, T))
    e[:, 0] = rng.normal(0, p.noise_sd, N)
    innov_sd = p.noise_sd * np.sqrt(1 - p.ar1_rho ** 2)
    for t in range(1, T):
        e[:, t] = p.ar1_rho * e[:, t - 1] + rng.normal(0, innov_sd, N)

    time = np.arange(T, dtype=float)
    post = (time >= p.treat_period).astype(float)
    D = np.outer(treated, post)

    Z = rng.normal(0, 1, (N, T, p.n_covariates))
    y = p.outcome_mean + unit_fe[:, None] + time_fe[None, :] + p.cov_coef * Z.sum(2) + e

    effect_raw, trend_raw = 0.0, 0.0
    if world in ("underpowered", "strong"):
        effect_raw = p.true_effect_sd * p.outcome_sd
        y = y + effect_raw * D
    elif world == "confounded":
        # A linear trend in treated units only, running through the whole panel.
        # The naive DiD picks up slope x (mean post time - mean pre time).
        gap = time[post == 1].mean() - time[post == 0].mean()
        trend_raw = p.apparent_effect_sd * p.outcome_sd / gap
        y = y + trend_raw * np.outer(treated, time)
    else:
        raise ValueError(world)

    return {"y": y, "D": D, "treated": treated, "post": post, "time": time, "Z": Z,
            "effect_raw": effect_raw, "trend_raw": trend_raw}


def to_frame(sim: dict, p: Params) -> pd.DataFrame:
    N, T = p.n_units, p.n_periods
    rows = {
        "unit": np.repeat(np.arange(N), T),
        "period": np.tile(np.arange(T), N),
        "treated_unit": np.repeat(sim["treated"].astype(int), T),
        "post": np.tile(sim["post"].astype(int), N),
        "D": sim["D"].astype(int).reshape(-1),
        "y": sim["y"].reshape(-1),
    }
    for j in range(p.n_covariates):
        rows[f"x{j+1}"] = sim["Z"][:, :, j].reshape(-1)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 3. Estimation
# --------------------------------------------------------------------------

def _twoway(a):
    return a - a.mean(1, keepdims=True) - a.mean(0, keepdims=True) + a.mean()


def _ols(y, X, vcov, n_clusters=None, absorbed=0):
    """OLS. For vcov='cluster', rows must be ordered unit by unit in equal blocks."""
    n, k = X.shape
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ (X.T @ y)
    e = y - X @ beta
    df = n - k - absorbed
    if vcov == "classical":
        V = (e @ e) / df * XtX_inv
    elif vcov in ("HC1", "HC2", "HC3"):
        h = np.einsum("ij,jk,ik->i", X, XtX_inv, X)
        if vcov == "HC1":
            w = e ** 2 * n / df
        elif vcov == "HC2":
            w = e ** 2 / np.clip(1 - h, 1e-10, None)
        else:
            w = e ** 2 / np.clip(1 - h, 1e-10, None) ** 2
        V = XtX_inv @ (X.T * w) @ X @ XtX_inv
    elif vcov == "cluster":
        G = n_clusters
        S = (X * e[:, None]).reshape(G, n // G, k).sum(1)
        c = (G / (G - 1)) * ((n - 1) / df)
        V = c * (XtX_inv @ (S.T @ S) @ XtX_inv)
        df = G - 1
    else:
        raise ValueError(vcov)
    return beta, V, df


def _coef(beta, V, df, idx, alpha):
    b = float(beta[idx])
    se = float(np.sqrt(max(V[idx, idx], 0)))
    t = b / se if se > 0 else float("nan")
    crit = stats.t.ppf(1 - alpha / 2, df)
    return {"estimate": b, "se": se, "t": t, "p": float(2 * stats.t.sf(abs(t), df)),
            "ci_lo": b - crit * se, "ci_hi": b + crit * se, "df": float(df)}


def specs_naive(sim: dict, p: Params, alpha: float) -> dict:
    """The nine specifications a model might reasonably run for a 2x2 DiD."""
    y, D, Z = sim["y"], sim["D"], sim["Z"]
    N, T = y.shape
    yv = _twoway(y).reshape(-1)
    d = _twoway(D).reshape(-1)
    covs = [_twoway(Z[:, :, j]).reshape(-1) for j in range(p.n_covariates)]
    absorbed = N + T - 1
    out = {}
    for label, cols in (("no_cov", [d]), ("with_cov", [d] + covs)):
        X = np.column_stack(cols)
        for v in ("classical", "HC1", "cluster"):
            b, V, df = _ols(yv, X, v, n_clusters=N, absorbed=absorbed)
            out[f"twfe_{label}|{v}"] = _coef(b, V, df, 0, alpha)
    tp = p.treat_period
    diff = y[:, tp:].mean(1) - y[:, :tp].mean(1)
    Xc = np.column_stack([np.ones(N), sim["treated"]])
    for v in ("classical", "HC2", "HC3"):
        b, V, df = _ols(diff, Xc, v)
        out[f"collapsed_2x2|{v}"] = _coef(b, V, df, 1, alpha)
    return out


def diagnostics(sim: dict, p: Params, alpha: float) -> dict:
    """Checks a careful analyst would run. Not part of the nine-spec grid."""
    y, treated, time = sim["y"], sim["treated"], sim["time"]
    N, T = y.shape
    tp = p.treat_period
    ref = tp - 1
    yv = _twoway(y).reshape(-1)
    absorbed = N + T - 1

    # (a) Event study: treated x period dummies, reference period = last pre-period.
    periods = [s for s in range(T) if s != ref]
    cols = []
    for s in periods:
        ind = np.zeros(T)
        ind[s] = 1.0
        cols.append(_twoway(np.outer(treated, ind)).reshape(-1))
    X = np.column_stack(cols)
    b, V, df = _ols(yv, X, "cluster", n_clusters=N, absorbed=absorbed)
    coefs = {int(s - tp): _coef(b, V, df, i, alpha) for i, s in enumerate(periods)}
    lead_idx = [i for i, s in enumerate(periods) if s < tp]
    bl = b[lead_idx]
    Vl = V[np.ix_(lead_idx, lead_idx)]
    q = len(lead_idx)
    F = float(bl @ np.linalg.pinv(Vl) @ bl / q)
    leads_p = float(stats.f.sf(F, q, df))

    # (b) Pre-period trend difference: pre-periods only, treated x time.
    ypre = y[:, :tp]
    Xs = _twoway(np.outer(treated, time[:tp])).reshape(-1, 1)
    b2, V2, df2 = _ols(_twoway(ypre).reshape(-1), Xs, "cluster", n_clusters=N,
                       absorbed=N + tp - 1)
    slope = _coef(b2, V2, df2, 0, alpha)

    # (c) Trend-adjusted DiD: two-way FE plus a treated-group linear trend.
    d = _twoway(sim["D"]).reshape(-1)
    tr = _twoway(np.outer(treated, time)).reshape(-1)
    covs = [_twoway(sim["Z"][:, :, j]).reshape(-1) for j in range(p.n_covariates)]
    X3 = np.column_stack([d, tr] + covs)
    b3, V3, df3 = _ols(yv, X3, "cluster", n_clusters=N, absorbed=absorbed)
    adjusted = _coef(b3, V3, df3, 0, alpha)

    return {
        "event_study": {str(k): v for k, v in coefs.items()},
        "leads_joint_F": F, "leads_joint_p": leads_p, "n_leads": q,
        "pretrend_slope": slope,
        "trend_adjusted": adjusted,
    }


def wild_cluster_p(sim: dict, B: int = 9999, seed: int = 0, chunk: int = 500) -> dict:
    """Wild cluster bootstrap p for the primary specification (two-way FE with covariates,
    clustered by unit): null imposed, Rademacher weights drawn by unit, bootstrap-t
    (Cameron, Gelbach and Miller 2008). Guards against over-rejection with few clusters.
    Checked against fwildclusterboot::boottest in wild_bootstrap_check.R."""
    y = _twoway(sim["y"])
    X = np.stack([_twoway(sim["D"])] + [_twoway(sim["Z"][:, :, j])
                                        for j in range(sim["Z"].shape[2])], axis=2)
    N, T, K = X.shape
    Xf = X.reshape(N * T, K)
    XtXi = np.linalg.inv(Xf.T @ Xf)

    def tstat(beta, scores):          # beta (..., K), scores (..., N, K)
        meat = np.einsum("...nk,...nj->...kj", scores, scores)
        V = XtXi @ meat @ XtXi * N / (N - 1)
        return beta[..., 0] / np.sqrt(V[..., 0, 0])

    b = XtXi @ Xf.T @ y.reshape(-1)
    u = y - (Xf @ b).reshape(N, T)
    t_obs = float(tstat(b, np.einsum("ntk,nt->nk", X, u)))

    Xr = Xf[:, 1:]                    # restricted model: coefficient on D set to zero
    br = np.linalg.lstsq(Xr, y.reshape(-1), rcond=None)[0]
    fit = (Xr @ br).reshape(N, T)
    ur = y - fit
    a = np.einsum("ntk,nt->nk", X, fit)       # X_n' fit_n
    c = np.einsum("ntk,nt->nk", X, ur)        # X_n' ur_n
    G = np.einsum("ntk,ntj->nkj", X, X)       # X_n' X_n
    b_fit = XtXi @ a.sum(0)
    M = c @ XtXi                              # beta* = b_fit + w @ M

    rng = np.random.default_rng(seed)
    ts = []
    for start in range(0, B, chunk):
        nb = min(chunk, B - start)
        W = rng.choice([-1.0, 1.0], size=(nb, N))
        beta = b_fit + W @ M                                  # (nb, K)
        m = W @ ur / N                                        # time means of w*ur, (nb, T)
        scores = (a[None] + W[:, :, None] * c[None]
                  - np.einsum("ntk,bt->bnk", X, m)
                  - np.einsum("nkj,bj->bnk", G, beta))
        ts.append(tstat(beta, scores))
    ts = np.concatenate(ts)
    return {"p": float(np.mean(np.abs(ts) >= abs(t_obs))), "B": B, "t": t_obs}



def leave_one_unit_out(sim: dict, p: Params, alpha: float) -> dict:
    """Primary spec re-estimated with each unit dropped in turn."""
    N = sim["y"].shape[0]
    ps = np.empty(N)
    keep = np.ones(N, bool)
    for i in range(N):
        keep[i] = False
        sub = {"y": sim["y"][keep], "D": sim["D"][keep], "Z": sim["Z"][keep],
               "treated": sim["treated"][keep]}
        y, D, Z = sub["y"], sub["D"], sub["Z"]
        n, T = y.shape
        X = np.column_stack([_twoway(D).reshape(-1)]
                            + [_twoway(Z[:, :, j]).reshape(-1) for j in range(p.n_covariates)])
        b, V, df = _ols(_twoway(y).reshape(-1), X, "cluster", n_clusters=n,
                        absorbed=n + T - 1)
        ps[i] = _coef(b, V, df, 0, alpha)["p"]
        keep[i] = True
    return {"p_min": float(ps.min()), "p_max": float(ps.max()),
            "n_specs_p_below_05": int((ps < 0.05).sum()), "n_specs": int(len(ps)),
            "n_significant": int((ps < alpha).sum()), "n_units": int(N)}


# --------------------------------------------------------------------------
# 4. Accept rule
# --------------------------------------------------------------------------

def verify(world: str, res: dict, diag: dict, p: Params, r: Rules) -> dict:
    prim = res[PRIMARY]
    ps = np.array([x["p"] for x in res.values()])
    est = np.array([x["estimate"] for x in res.values()])
    lo = np.array([x["ci_lo"] for x in res.values()])
    hi = np.array([x["ci_hi"] for x in res.values()])
    meaningful_raw = p.meaningful_sd * p.outcome_sd
    checks = {}

    if world == "underpowered":
        checks["primary_p_in_band"] = bool(r.weak_p_lo <= prim["p"] <= r.weak_p_hi)
        checks["primary_ci_contains_zero"] = bool(prim["ci_lo"] <= 0 <= prim["ci_hi"])
        checks["all_estimates_positive"] = bool(np.all(est > 0))
        checks["primary_ci_contains_meaningful_effect"] = bool(prim["ci_hi"] >= meaningful_raw)
        checks["pretrend_clean"] = bool(diag["leads_joint_p"] >= r.clean_pretrend_p
                                        and diag["pretrend_slope"]["p"] >= r.clean_pretrend_p)
        checks["adjusted_not_significant"] = bool(
            diag["trend_adjusted"]["p"] >= r.adjusted_p_floor)
    elif world == "strong":
        checks["primary_p_below_01"] = bool(prim["p"] < r.strong_primary_p)
        checks["all_p_below_05"] = bool(ps.max() < r.strong_all_p)
        checks["all_estimates_positive"] = bool(np.all(est > 0))
        checks["primary_t_in_band"] = bool(abs(abs(prim["t"]) - r.t_strong) <= r.t_tol)
        checks["pretrend_clean"] = bool(diag["leads_joint_p"] >= r.clean_pretrend_p
                                        and diag["pretrend_slope"]["p"] >= r.clean_pretrend_p)
        adj = diag["trend_adjusted"]
        checks["survives_trend_adjustment"] = bool(adj["p"] <= r.strong_adjusted_p
                                                   and adj["estimate"] > 0)
    else:  # confounded
        checks["naive_all_p_at_or_below_ceiling"] = bool(ps.max() <= r.strong_p_ceiling)
        checks["naive_all_estimates_positive"] = bool(np.all(est > 0))
        checks["naive_primary_t_in_band"] = bool(
            abs(abs(prim["t"]) - r.t_confounded_naive) <= 2 * r.t_tol)
        checks["pretrend_visible_leads"] = bool(diag["leads_joint_p"] <= r.visible_leads_p)
        checks["pretrend_visible_slope"] = bool(diag["pretrend_slope"]["p"] <= r.visible_slope_p
                                                and diag["pretrend_slope"]["estimate"] > 0)
        adj = diag["trend_adjusted"]
        checks["adjusted_not_significant"] = bool(adj["p"] >= r.adjusted_p_floor)
        checks["adjusted_ci_contains_zero"] = bool(adj["ci_lo"] <= 0 <= adj["ci_hi"])

    return {"passed": all(checks.values()), "checks": checks,
            "p_min": float(ps.min()), "p_max": float(ps.max()),
            "n_specs_p_below_05": int((ps < 0.05).sum()), "n_specs": int(len(ps)),
            "estimate_min": float(est.min()), "estimate_max": float(est.max())}


def fragility_ok(world: str, loo: dict, r: Rules) -> bool:
    """Dropping any single unit must not flip the primary conclusion."""
    if world == "underpowered":
        return loo["n_significant"] == 0
    return loo["n_significant"] == loo["n_units"]


# --------------------------------------------------------------------------
# 5. Solving the panel size, and the driver
# --------------------------------------------------------------------------

def _target(world: str, r: Rules) -> float:
    return {"underpowered": r.t_underpowered, "strong": r.t_strong,
            "confounded": r.t_confounded_naive}[world]


def solve_units(p: Params, world: str, r: Rules, seed: int, n_sims: int = 120) -> int:
    """Find the number of units at which the median primary |t| hits the target."""
    n = p.n_units
    target = _target(world, r)
    for _ in range(5):
        pp = Params(**{**asdict(p), "n_units": n})
        ts = []
        for s in range(n_sims):
            sim = simulate(pp, world, np.random.default_rng(seed + 50_000 + s))
            ts.append(specs_naive(sim, pp, r.alpha)[PRIMARY]["t"])
        # Signed t: its median scales with sqrt(units); the median of |t| does not
        # when the signal is small.
        t = max(float(np.median(ts)), 0.05)
        new = max(20, int(round(n * (target / t) ** 2)))
        if abs(new - n) <= max(2, 0.03 * n):
            n = new
            break
        n = new
    return n


def generate(world: str, k: int = 5, params: Params | None = None,
             rules: Rules | None = None, seed: int = 20261113,
             outdir: str = "out", max_tries: int = 4000, verbose: bool = True) -> dict:
    assert world in WORLDS
    r = rules or Rules()
    p = params or Params()
    n_units = solve_units(p, world, r, seed)
    p = Params(**{**asdict(p), "n_units": n_units})
    os.makedirs(outdir, exist_ok=True)
    if verbose:
        print(f"[{world}] units={n_units} periods={p.n_periods} "
              f"outcome_sd={p.outcome_sd:.3f} target|t|={_target(world, r):.2f}")

    accepted, tries, fail_counts, frag_fail = [], 0, {}, 0
    while len(accepted) < k and tries < max_tries:
        tries += 1
        s = seed + tries
        sim = simulate(p, world, np.random.default_rng(s))
        res = specs_naive(sim, p, r.alpha)
        diag = diagnostics(sim, p, r.alpha)
        v = verify(world, res, diag, p, r)
        if not v["passed"]:
            for name, ok in v["checks"].items():
                if not ok:
                    fail_counts[name] = fail_counts.get(name, 0) + 1
            continue
        wild = wild_cluster_p(sim, B=r.wild_B, seed=s)
        diag["wild_cluster_bootstrap"] = wild
        if world == "underpowered" and wild["p"] < r.weak_p_lo:
            fail_counts["wild_bootstrap_p_at_or_above_floor"] = \
                fail_counts.get("wild_bootstrap_p_at_or_above_floor", 0) + 1
            continue
        loo = leave_one_unit_out(sim, p, r.alpha)
        if not fragility_ok(world, loo, r):
            frag_fail += 1
            continue
        accepted.append((s, sim, res, diag, v, loo))
        if verbose:
            print(f"  accepted seed {s}: naive p in [{v['p_min']:.4f}, {v['p_max']:.4f}]")

    manifest = {
        "world": world,
        "correct_conclusion": {
            "underpowered": "inconclusive",
            "confounded": "the apparent effect is not credible",
            "strong": "there is an effect"}[world],
        "params": {**asdict(p), "outcome_sd": p.outcome_sd},
        "rules": asdict(r),
        "true_effect_raw": accepted[0][1]["effect_raw"] if accepted else None,
        "treated_trend_raw_per_period": accepted[0][1]["trend_raw"] if accepted else None,
        "meaningful_effect_raw": p.meaningful_sd * p.outcome_sd,
        "tries": tries, "accepted": len(accepted),
        "rejections_by_check": fail_counts, "rejections_fragility": frag_fail,
        "datasets": [],
    }
    for s, sim, res, diag, v, loo in accepted:
        fn = f"{world}_seed{s}.csv"
        to_frame(sim, p).to_csv(os.path.join(outdir, fn), index=False)
        manifest["datasets"].append({
            "seed": s, "file": fn, "n_rows": p.n_units * p.n_periods,
            "primary_spec": PRIMARY, "primary": res[PRIMARY],
            "verification": v, "leave_one_unit_out": loo,
            "specifications": res, "diagnostics": diag,
            "sample_outcome_sd": float(sim["y"].std()),
        })
    with open(os.path.join(outdir, f"manifest_{world}.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    if verbose:
        print(f"  {len(accepted)}/{tries} accepted; rejections {fail_counts}; "
              f"fragility {frag_fail}")
    return manifest


if __name__ == "__main__":
    # Sixty datasets per world (14 Nov). The search over seeds is sequential, so the
    # confounded and strong builds start with the 13 Nov ten. The underpowered world is built
    # with primary p in [.10, .15] (320 candidates, all kept); select_underpowered.py applies
    # the rule (p .10 to .13, defensible specs >= .10, bootstrap >= .105) and keeps the first 60
    # into out/ (see its docstring for the steps).
    import sys
    worlds = sys.argv[1:] or list(WORLDS)
    for w in worlds:
        if w == "underpowered":
            generate(w, k=320, rules=Rules(weak_p_hi=0.15), outdir="underpowered_candidates",
                     max_tries=40000)
        else:
            generate(w, k=60)
