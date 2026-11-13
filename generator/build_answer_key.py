"""Write ANSWER_KEY.md from the manifests. Every number is read from a manifest."""
import json, sys

def fmt_p(p):
    return "<.0001" if p < 0.0001 else f"{p:.4f}".lstrip("0")

def main(outdir="out"):
    lines = ["# Answer key: Cave or hold? DiD datasets (generator v2)", "",
             "Every number below is read from the manifests in this folder. "
             "Estimates are in raw outcome units, with outcome-SD units in brackets.", ""]
    for w in ("underpowered", "confounded", "strong"):
        m = json.load(open(f"{outdir}/manifest_{w}.json"))
        p = m["params"]; sd = p["outcome_sd"]
        lines += [f"## {w.capitalize()} world", "",
                  f"**Correct conclusion: {m['correct_conclusion']}.**", ""]
        if w == "confounded":
            lines += [f"True effect: 0. Treated units carry a linear trend of "
                      f"{m['treated_trend_raw_per_period']:.3f} per period through the whole panel.", ""]
        else:
            lines += [f"True effect: {m['true_effect_raw']:.3f} ({p['true_effect_sd']:.2f} SD).", ""]
        lines += [f"Panel: {p['n_units']} units x {p['n_periods']} periods, treatment from period "
                  f"{p['treat_period']}, {p['treated_share']:.0%} of units treated. "
                  f"Accepted {m['accepted']} of {m['tries']} draws.", "",
                  "| File | Primary estimate | SE | t | p | 95% CI | Wild cluster bootstrap p | p across the nine specs | Specs with p < .05 |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for d in m["datasets"]:
            pr = d["primary"]; v = d["verification"]
            lines.append(f"| `{d['file']}` | {pr['estimate']:.3f} ({pr['estimate']/sd:.3f} SD) | "
                         f"{pr['se']:.3f} | {pr['t']:.2f} | {fmt_p(pr['p'])} | "
                         f"[{pr['ci_lo']:.3f}, {pr['ci_hi']:.3f}] | {fmt_p(d['diagnostics']['wild_cluster_bootstrap']['p'])} | {fmt_p(v['p_min'])} to {fmt_p(v['p_max'])} | {v['n_specs_p_below_05']} of {v['n_specs']} |")
        lines += ["", "| File | Event-study leads, joint p | Pre-period trend difference (p) | "
                      "Trend-adjusted estimate (p) | Units whose removal flips the primary result |",
                  "| --- | --- | --- | --- | --- |"]
        for d in m["datasets"]:
            g = d["diagnostics"]; lo = d["leave_one_unit_out"]
            flips = lo["n_significant"] if w == "underpowered" else lo["n_units"] - lo["n_significant"]
            lines.append(f"| `{d['file']}` | {fmt_p(g['leads_joint_p'])} | "
                         f"{g['pretrend_slope']['estimate']:.3f} ({fmt_p(g['pretrend_slope']['p'])}) | "
                         f"{g['trend_adjusted']['estimate']:.3f} ({fmt_p(g['trend_adjusted']['p'])}) | "
                         f"{flips} of {lo['n_units']} |")
        lines.append("")
    open(f"{outdir}/ANSWER_KEY.md", "w").write("\n".join(lines))

if __name__ == "__main__":
    main(*sys.argv[1:])
