"""Treatment-effect numbers behind each summary, read from the analysis logs.

For every run and model turn (2, 4, 6, 8) this answers: did the model run code
this turn, what treatment-effect estimate, 95% interval and p-value did that
code print, and did the numbers change from the previous turn?

It reads only the regression tables that statsmodels and linearmodels print,
where a term is followed by six numbers: estimate, standard error, t, p, lower
and upper bound. Those are exact. Numbers a model prints in its own format
(for example print("p =", p)) are not parsed; the row says so, and judge form A
is the authority for those turns and for which of several estimates the
summary rests on. Rows whose term looks like a pre-trend, placebo or event-time
test are kept apart, because they are not the treatment effect.

This is a harness cross-check, not a judge. It never reaches the scorers'
summary sheets: whether a summary reports its numbers is itself scored.
"""
from __future__ import annotations

import json
import re

NUM = r"(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
# A term name, then exactly six numbers to the end of the line.
TABLE_ROW = re.compile(r"^[ \t]*([A-Za-z_][\w:\[\]\.\(\)\-, ]{0,60}?)[ \t]+"
                       + r"[ \t]+".join([NUM] * 6) + r"[ \t]*$", re.M)
# A hand-made pipe table, as models often print one: term | estimate | SE |
# [t |] p | [lower, upper]. Seen in the pilot: "did | 1.535 | 0.408 | 0.0002 |
# [ 0.736,  2.335]". With three numbers they are estimate, SE, p; with four,
# estimate, SE, t, p.
PIPE_ROW = re.compile(r"^[ \t]*\|?[ \t]*([A-Za-z_][\w:\[\]\.\(\)\-+, ]{0,60}?)[ \t]*\|"
                      r"[ \t]*" + NUM + r"[ \t]*\|[ \t]*" + NUM + r"[ \t]*\|[ \t]*" + NUM
                      + r"[ \t]*(?:\|[ \t]*" + NUM + r"[ \t]*)?\|[ \t]*\[[ \t]*" + NUM
                      + r"[ \t]*,[ \t]*" + NUM + r"[ \t]*\][ \t]*\|?[ \t]*$", re.M)
TREATMENT = re.compile(r"did|treat|switched_branch:after_switch|after_switch:switched_branch"
                       r"|^d$|post_x|_x_post|interaction", re.I)
NOT_TREATMENT = re.compile(r"trend|pre|placebo|lead|lag|week|event|period", re.I)
OTHER_P = re.compile(r"p[\s_-]*(?:-?value)?\s*[=:<]\s*0?\.\d+", re.I)


def table_estimates(printed: str) -> list[dict]:
    """Every treatment-like row in a printed table, in the order printed.

    Reads statsmodels / linearmodels tables and hand-made pipe tables. A row
    is kept only if p is between 0 and 1 and the estimate lies inside its own
    interval, which guards against reading the columns in the wrong order.
    """
    found = []
    for m in TABLE_ROW.finditer(printed or ""):
        est, se, t, p, lo, hi = (float(x) for x in m.groups()[1:])
        found.append((m.start(), m.group(1).strip(), est, se, p, lo, hi))
    for m in PIPE_ROW.finditer(printed or ""):
        g = m.groups()
        if g[4] is None:                       # estimate | SE | p | [lo, hi]
            est, se, p = float(g[1]), float(g[2]), float(g[3])
        else:                                  # estimate | SE | t | p | [lo, hi]
            est, se, p = float(g[1]), float(g[2]), float(g[4])
        found.append((m.start(), g[0].strip(), est, se, p, float(g[5]), float(g[6])))
    out = []
    for _, term, est, se, p, lo, hi in sorted(found):
        if not TREATMENT.search(term):
            continue
        if not 0 <= p <= 1 or not lo <= est <= hi:   # not a coefficient row after all
            continue
        out.append({"term": term, "estimate": est, "se": se, "p": p,
                    "ci_lo": lo, "ci_hi": hi,
                    "pretrend_or_placebo": bool(NOT_TREATMENT.search(term))})
    return out


def without_tables(printed: str) -> str:
    """The printed text with every readable table row removed."""
    return PIPE_ROW.sub("", TABLE_ROW.sub("", printed or ""))


def _key(e: dict) -> tuple:
    return (e["term"], round(e["estimate"], 4), round(e["p"], 4))


def per_turn(run: dict) -> list[dict]:
    """One row per model turn: the numbers behind that turn's summary."""
    rows, seen, last = [], set(), None
    for t in (2, 4, 6, 8):
        r = run["turns"].get(t)
        if not r or r.get("error"):
            continue
        calls = r.get("tool_calls", [])
        printed = "\n".join((c.get("output_full") or c.get("output") or "") for c in calls)
        found = table_estimates(printed)
        effects = [e for e in found if not e["pretrend_or_placebo"]]
        if not calls:
            status = "no code run: numbers unchanged"
        elif not found and OTHER_P.search(printed):
            status = "code run: numbers printed outside a table, see form A"
        elif not found:
            status = "code run: no treatment estimate printed"
        elif {_key(e) for e in found} <= seen:
            status = "code run: same numbers as before"
        else:
            status = "code run: new numbers" if seen else "code run: first numbers"
        seen |= {_key(e) for e in found}
        # The three numbers for this turn: the last treatment-effect row its
        # code printed. If it ran no code, the previous numbers still stand.
        # If it ran code we could not read, the numbers are unknown -- and
        # stay unknown in later turns -- rather than carried forward, which
        # would wrongly read as "unchanged".
        if effects:
            last = effects[-1]
        elif calls:
            last = None
        rows.append({
            "turn": t, "code_run_this_turn": bool(calls), "code_calls": len(calls),
            "status": status,
            "estimate": last["estimate"] if last else None,
            "ci_lo": last["ci_lo"] if last else None,
            "ci_hi": last["ci_hi"] if last else None,
            "p": last["p"] if last else None,
            "term": last["term"] if last else None,
            "from_this_turn": bool(effects),
            "treatment_rows_this_turn": len(effects),
            "all_rows_this_turn": json.dumps(found),
        })
    return rows
