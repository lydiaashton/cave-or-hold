"""Wild cluster bootstrap check on the primary specification (two-way FE with covariates,
clustered by unit). Restricted (null-imposed) bootstrap with Rademacher weights drawn by
unit, bootstrap-t p-value (Cameron, Gelbach and Miller 2008).
Usage: python3 wild_bootstrap_check.py out underpowered [B]"""
import json, sys
import numpy as np, pandas as pd

def twoway(a):  # balanced panel, shape (N, T)
    return a - a.mean(1, keepdims=True) - a.mean(0, keepdims=True) + a.mean()

def cluster_t(y, X):
    """y (N,T) and X (N,T,K), already two-way demeaned. Returns beta[0] and its cluster t."""
    N, T, K = X.shape
    Xf, yf = X.reshape(N * T, K), y.reshape(N * T)
    XtXi = np.linalg.inv(Xf.T @ Xf)
    b = XtXi @ Xf.T @ yf
    u = (yf - Xf @ b).reshape(N, T)
    s = np.einsum("ntk,nt->nk", X, u)            # score by unit
    V = XtXi @ (s.T @ s) @ XtXi * N / (N - 1)
    return b[0], b[0] / np.sqrt(V[0, 0])

def wcr_p(df, B=9999, seed=1):
    N, T = df.unit.nunique(), df.period.nunique()
    df = df.sort_values(["unit", "period"])
    g = lambda c: twoway(df[c].to_numpy(float).reshape(N, T))
    y, X = g("y"), np.stack([g("D"), g("x1"), g("x2")], axis=2)
    b, t = cluster_t(y, X)
    Xr = X[:, :, 1:]                               # restricted model: effect of D set to 0
    Xrf = Xr.reshape(N * T, 2)
    br = np.linalg.lstsq(Xrf, y.reshape(N * T), rcond=None)[0]
    fit = (Xrf @ br).reshape(N, T); ur = y - fit
    rng = np.random.default_rng(seed)
    ts = np.empty(B)
    for i in range(B):
        w = rng.choice([-1.0, 1.0], N)[:, None]
        ts[i] = cluster_t(fit + twoway(w * ur), X)[1]
    return b, t, float(np.mean(np.abs(ts) >= abs(t)))

if __name__ == "__main__":
    outdir, world = sys.argv[1], sys.argv[2]
    B = int(sys.argv[3]) if len(sys.argv) > 3 else 9999
    m = json.load(open(f"{outdir}/manifest_{world}.json"))
    print(f"{world}: {m['params']['n_units']} units, B={B}")
    for d in m["datasets"]:
        b, t, p = wcr_p(pd.read_csv(f"{outdir}/{d['file']}"), B)
        print(f"  {d['file']}: t {t:.2f} (manifest {d['primary']['t']:.2f}), "
              f"analytic cluster p {d['primary']['p']:.4f}, wild bootstrap p {p:.4f}")
