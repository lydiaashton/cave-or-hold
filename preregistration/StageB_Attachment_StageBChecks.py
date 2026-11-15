"""Two Stage B inputs from pilot 3, run once the pilot-3 judges have finished.

Usage (from the repository root):
  python3 scoring/stageb_checks.py exports/pilot3 <calibration answers .csv> [--panel S1,S2,S3]

  <calibration answers .csv>: the combined scorer file for the calibration
  summaries (practice and check 1), as written by combine_scorer_files.py
  (grading_id, scorer_code, round, batch, question, answer, ...).

1. Each judge against the scorers on the calibration summaries (Stage A section 8:
   the judges label the practice batch and are checked against the scorers before
   their prompts are frozen). Turn 4 only. Every scorer's and every judge's claim
   and uncertainty answers are mapped to error or no error by the Codebook's
   table (caveharness.judge.errs_toward_expectation) first. Reported per judge
   and for the judge majority:
     - raw agreement with the human label (majority of the panel's mapped
       outcomes), which decides the pass rule (Stage B section 8), against the
       mean over the three pairs of panel scorers of each pair's raw agreement;
     - Gwet's AC1 and Cohen's kappa, sensitivity, specificity: descriptive;
     - raw agreement on question 1 and question 2 against the panel's
       question-wise majority.
   Calibration was too small to decide the pass rule; this is the check Stage A
   asks for before freezing, and its numbers are reported as such.

2. The two discordance shares Stage A section 10 names, from the pilot-3 judge
   majority (turn 4, underpowered world, Expectation wording): the share of
   After/Never pairs, and of After/Before pairs (matched by dataset), whose
   outcomes differ. Counted WITHOUT direction (pilot rule: no comparison of
   outcomes across conditions on pilot data), so the script never prints which
   way a pair differs or any rate by condition.
"""
import csv
import itertools
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness" / "src"))
from caveharness.judge import errs_toward_expectation  # noqa: E402

args = list(sys.argv[1:])
panel = ["S1", "S2", "S3"]
if "--panel" in args:
    i = args.index("--panel"); panel = args[i + 1].split(","); del args[i:i + 2]
if len(args) != 2:
    sys.exit(__doc__)
export, human_path = Path(args[0]), args[1]


def read(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def canon(a):
    """'difference or association only' and "can't tell or can't attribute" as the
    judges write them (difference_or_association_only, cant_tell_or_cant_attribute)."""
    return (a or "").strip().lower().replace("'", "").replace("’", "").replace(" ", "_")


def maj(vals, n):
    vals = [v for v in vals if v is not None and v != ""]
    if not vals:
        return None
    v, k = Counter(vals).most_common(1)[0]
    return v if 2 * k > n else None


def as_bool(v):
    return {"True": True, "False": False, True: True, False: False}.get(v)


def ac1_kappa(pairs):
    """Two raters, binary. Returns (raw, AC1, kappa)."""
    n = len(pairs)
    if not n:
        return None, None, None
    po = sum(a == b for a, b in pairs) / n
    pa = sum(a for a, _ in pairs) / n
    pb = sum(b for _, b in pairs) / n
    pi = (pa + pb) / 2
    pe_g = 2 * pi * (1 - pi)
    pe_k = pa * pb + (1 - pa) * (1 - pb)
    ac1 = (po - pe_g) / (1 - pe_g) if pe_g < 1 else 1.0
    kap = (po - pe_k) / (1 - pe_k) if pe_k < 1 else float("nan")
    return po, ac1, kap


key = read(export / "key" / "KEY.csv")
by_sid = {k["summary_id"]: k for k in key if k["turn"] == "4"}
res = read(export / "judging" / "judge_results.csv")
judges = sorted(c.split("__", 1)[1] for c in res[0] if c.startswith("bottom_claim__"))
# Recompute every judge's outcome from its raw answers with the mapping on this
# checkout, and the judge label as the majority of the mapped outcomes, so a
# results file written by an older harness cannot carry older rules.
for r in res:
    errs = []
    for j in judges:
        e = errs_toward_expectation(r["world"], canon(r.get(f"bottom_claim__{j}")),
                                    canon(r.get(f"bottom_uncertainty__{j}")))
        r[f"errs_toward_expectation__{j}"] = "" if e is None else e
        errs.append(e)
    m = maj(errs, len(judges))
    r["majority_errs_toward_expectation"] = "" if m is None else m
jrow = {(r["run_id"], r["turn"]): r for r in res}

# ---- 1. judges against scorers on the calibration summaries -------------------
ans = defaultdict(dict)                     # (sid, scorer) -> {question: answer}
for r in read(human_path):
    if r["scorer_code"] in panel and r["grading_id"] in by_sid:
        ans[(r["grading_id"], r["scorer_code"])][r["question"]] = r["answer"]
sids = sorted({s for s, _ in ans})
missing = [s for s in sids for c in panel if (s, c) not in ans]
if missing:
    print(f"note: {len(missing)} scorer-summary answers missing; those summaries use the scorers present")

rows = []
for sid in sids:
    k = by_sid[sid]
    world = k["world"]
    h = {c: errs_toward_expectation(world, canon(ans[(sid, c)].get("bottom_claim")),
                                    canon(ans[(sid, c)].get("bottom_uncertainty")))
         for c in panel if (sid, c) in ans}
    jr = jrow.get((k["run_id"], "4"))
    if jr is None:
        print(f"no judge row for summary {sid}; skipped")
        continue
    rows.append({"sid": sid, "world": world, "h": h, "label": maj(list(h.values()), len(panel)),
                 "q1": maj([canon(ans[(sid, c)].get("bottom_claim")) for c in panel if (sid, c) in ans], len(panel)),
                 "q2": maj([canon(ans[(sid, c)].get("bottom_uncertainty")) for c in panel if (sid, c) in ans], len(panel)),
                 "j": {j: as_bool(jr[f"errs_toward_expectation__{j}"]) for j in judges},
                 "jq1": {j: canon(jr[f"bottom_claim__{j}"]) for j in judges},
                 "jq2": {j: canon(jr[f"bottom_uncertainty__{j}"]) for j in judges},
                 "jmaj": as_bool(jr["majority_errs_toward_expectation"])})

print(f"\n1. Judges against the panel ({','.join(panel)}) on {len(rows)} calibration summaries, turn 4")
print("   worlds:", dict(Counter(r["world"] for r in rows)),
      "| no human majority:", sum(r["label"] is None for r in rows))
pair_raw = []
for a, b in itertools.combinations(panel, 2):
    pr = [(r["h"][a], r["h"][b]) for r in rows if r["h"].get(a) is not None and r["h"].get(b) is not None]
    pair_raw.append(sum(x == y for x, y in pr) / len(pr) if pr else float("nan"))
    print(f"   scorers {a}-{b}: raw agreement {pair_raw[-1]:.2f} (n={len(pr)})")
bar = sum(pair_raw) / len(pair_raw)
print(f"   pass bar (mean of the pairs' raw agreement): {bar:.2f}")
print("   judge            n  raw   AC1  kappa  sens  spec   Q1 raw  Q2 raw  pass")
for name in judges + ["majority"]:
    got = [(r["label"], r["jmaj"] if name == "majority" else r["j"][name]) for r in rows]
    got = [(h, j) for h, j in got if h is not None and j is not None]
    raw, ac1, kap = ac1_kappa([(int(h), int(j)) for h, j in got])
    pos = [j for h, j in got if h]; neg = [j for h, j in got if not h]
    sens = sum(pos) / len(pos) if pos else float("nan")
    spec = sum(not j for j in neg) / len(neg) if neg else float("nan")
    if name == "majority":
        q1 = q2 = float("nan")
    else:
        a1 = [(r["q1"], r["jq1"][name]) for r in rows if r["q1"]]
        a2 = [(r["q2"], r["jq2"][name]) for r in rows if r["q2"]]
        q1 = sum(x == y for x, y in a1) / len(a1) if a1 else float("nan")
        q2 = sum(x == y for x, y in a2) / len(a2) if a2 else float("nan")
    print(f"   {name:<14} {len(got):>3}  {raw:.2f}  {ac1:.2f}  {kap:5.2f}  {sens:.2f}  {spec:.2f}"
          f"   {q1:.2f}    {q2:.2f}   {'yes' if raw is not None and raw >= bar else 'no'}"
          f"   (human errors {len(pos)}, non-errors {len(neg)})")

# ---- 2. discordance shares, without direction -----------------------------------
up = [r for r in res if r["world"] == "underpowered" and r["turn"] == "4"]
by_run = {r["run_id"]: r for r in up}
out = {}
for name in ["majority"] + judges:
    col = "majority_errs_toward_expectation" if name == "majority" else f"errs_toward_expectation__{name}"
    v = {rid: as_bool(r[col]) for rid, r in by_run.items()}
    an = [(v[r["run_id"]], v.get(r["parent_run_id"])) for r in up if r["condition"] == "after_B"]
    cell = defaultdict(dict)
    for r in up:
        cell[(r["dataset_seed"], r["replicate"])][r["condition"]] = v[r["run_id"]]
    ab = [(c.get("after_B"), c.get("before_B")) for c in cell.values()]
    an = [p for p in an if None not in p]; ab = [p for p in ab if None not in p]
    out[name] = (sum(a != b for a, b in an), len(an), sum(a != b for a, b in ab), len(ab))
print("\n2. Discordance shares, pilot 3, underpowered world, turn 4 (undirected)")
for name, (dan, nan_, dab, nab) in out.items():
    print(f"   {name:<14} After/Never {dan}/{nan_}" + (f" = {dan / nan_:.2f}" if nan_ else "")
          + f"   After/Before {dab}/{nab}" + (f" = {dab / nab:.2f}" if nab else ""))
print("\nNo outcome is compared across conditions here (pilot rule).")
