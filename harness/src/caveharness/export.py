"""Export one batch into the repository (study lead's layout, 13 Nov).

    uv run python -m caveharness.export --batch pilot1 --seed 20261113

Reads runs/<batch>/<machine>/*.jsonl from every machine and writes
<repo>/exports/<batch>/, to be committed and pushed once per batch. Scorers
cannot see the repository; they receive only the scoring page built from a
summaries folder.

  exports/<batch>/
    T2/ T4/ T6/ T8/
      summaries/<id>.txt          the summary ID and the summary, nothing else
      analysis/
        analysis_values.csv       every estimate / 95% CI / p the code printed,
                                  one row each, for checking against the summary
        logs/<id>.txt             the code the model ran and everything it
                                  printed, up to this summary. No user messages,
                                  no thinking
        thinking/<id>.txt         the thinking trace and/or reasoning summary the
                                  provider returned for this turn
    key/
      KEY.csv                     summary ID -> run, condition, turn, model, dataset
      run_stats.csv               per run: tokens, completion, errors, tool use
      analysis_estimates.csv      per run x turn: the numbers behind each summary
      manifest.json, pilot_report.md
    judges/
      judge_items.jsonl           per run x turn: summary and analysis log, with
                                  no user messages, condition or thinking

Every summary gets a different random ID at each turn, drawn from the recorded
seed, so re-exporting gives identical IDs. An After run's turn 2 is its Never
run's, so each turn-2 summary is written once and the key lists both runs.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import random
import re
import shutil
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from caveharness.config import HARNESS_DIR, REPO_DIR, RUNS_DIR
from caveharness.estimates import OTHER_P, per_turn, table_estimates, without_tables

EXPORTS_DIR = REPO_DIR / "exports"
TURNS = (2, 4, 6, 8)
PLACEHOLDER = "[model reasoning omitted]"
THINK = re.compile(r"<think>.*?</think>", re.S | re.I)
FIGURE_EXT = (".png", ".jpg", ".jpeg", ".pdf", ".svg")
JUDGE_LOG_CAP = 60_000   # characters; handoff 6: cap long logs and record truncation


# --------------------------------------------------------------------------
# Reading the runs
# --------------------------------------------------------------------------
def load_runs(batch: str) -> dict[str, dict]:
    runs = {}
    for f in sorted((RUNS_DIR / batch).rglob("*.jsonl")):
        recs = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
        if not recs or recs[0].get("record") != "header":
            continue
        h = recs[0]
        turns = {r["turn"]: r for r in recs if r.get("record") == "turn"}
        end = next((r for r in reversed(recs) if r.get("record") == "end"), None)
        completed = max((t for t, r in turns.items() if not r.get("error")), default=0)
        runs[h["run_id"]] = {"header": h, "turns": turns, "end": end,
                             "completed_turn": completed, "file": str(f)}
    return runs


def clean(text: str | None) -> str:
    """The summary with any inline thinking replaced by a placeholder.

    Covers a complete <think>...</think> block, and the form some vLLM
    deployments return where the opening tag is dropped and only </think>
    marks where the reasoning ended.
    """
    text = text or ""
    low = text.lower()
    if "</think>" in low and "<think>" not in low:
        text = PLACEHOLDER + text[low.rindex("</think>") + len("</think>"):]
    return THINK.sub(PLACEHOLDER, text).strip()


def inline_thinking(text: str | None) -> list[str]:
    """Thinking a model wrote into its reply text, which clean() removes."""
    text = text or ""
    low = text.lower()
    if "</think>" in low and "<think>" not in low:
        return [text[: low.rindex("</think>")].strip()]
    return [m.group(0)[len("<think>"):-len("</think>")].strip() for m in THINK.finditer(text)]


def _printed(call: dict) -> str:
    # Everything the code printed (handoff 5), not only what the model was shown.
    return call.get("output_full") or call.get("output") or ""


def analysis_log(run: dict, upto_turn: int) -> str:
    """All code the model ran and everything it printed, up to and including a
    turn. Code and output only: no user messages, no thinking."""
    parts = []
    for t in sorted(run["turns"]):
        if t > upto_turn:
            break
        r = run["turns"][t]
        calls = r.get("tool_calls", [])
        for i, c in enumerate(calls, 1):
            parts.append(f"=== Code run in turn {t}, call {i} of {len(calls)} ===\n"
                         f"{c.get('code') or ''}\n--- printed ---\n{_printed(c)}"
                         + (f"\n--- error ---\n{c['error']}" if c.get("error") else ""))
        if r.get("files_saved"):
            parts.append(f"--- files saved in turn {t}: {', '.join(r['files_saved'])} ---")
    if not run["turns"].get(upto_turn, {}).get("tool_calls"):
        parts.append(f"(No code was run in turn {upto_turn}.)")
    return "\n\n".join(parts) if parts else "(No code was run.)"


def cross_checks(run: dict, upto_turn: int) -> dict:
    code = " ".join((c.get("code") or "") for t, r in run["turns"].items() if t <= upto_turn
                    for c in r.get("tool_calls", []))
    files = [f for t, r in run["turns"].items() if t <= upto_turn for f in r.get("files_saved", [])]
    return {"cluster_in_code": "cluster" in code.lower(),
            "figure_saved": any(f.lower().endswith(FIGURE_EXT) for f in files),
            "code_tool_called_after_turn3": any(r.get("code_tool_called")
                                                for t, r in run["turns"].items() if 4 <= t <= upto_turn)}


def fingerprints(log_dir: Path, run_ids: set[str]) -> dict[str, list[str]]:
    """Deployment fingerprints per run, read from the raw API responses that
    Inspect keeps in its .eval logs (the per-run logs do not see them)."""
    from inspect_ai.log import read_eval_log
    found: dict[str, set[str]] = defaultdict(set)
    for p in sorted(log_dir.glob("*.eval")):
        try:
            log = read_eval_log(str(p))
        except Exception:
            continue
        for s in log.samples or []:
            ids = [r for r in (s.store or {}).get("run_ids", {}).values() if r in run_ids]
            if not ids:
                continue
            fps = {(e.call.response or {}).get("system_fingerprint")
                   for e in s.events if e.event == "model" and getattr(e, "call", None)}
            for r in ids:
                found[r] |= {f for f in fps if f}
    return {r: sorted(v) for r, v in found.items()}


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig: Excel otherwise shows dashes and quotes in summaries as garbage.
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["summary_id"])
        w.writeheader()
        w.writerows(rows)


# --------------------------------------------------------------------------
# Per-summary files
# --------------------------------------------------------------------------
def _p_text(p: float) -> str:
    # Regression tables round p to three decimals: a printed 0.000 means below
    # 0.0005, never zero.
    return "<0.001 (printed 0.000)" if p == 0 else f"{p:.4g}"


def analysis_values(run: dict, upto_turn: int) -> list[dict]:
    """Every estimate the run's code printed in a table, up to and including a
    turn, in the order printed -- not one guess, because a model often runs
    several regressions and reports any one of them. A turn whose code also
    printed results in its own format gets a row saying so."""
    rows = []
    for t in sorted(run["turns"]):
        if t > upto_turn:
            break
        calls = run["turns"][t].get("tool_calls", [])
        if not calls:
            continue
        printed = "\n".join(_printed(c) for c in calls)
        when = "this turn" if t == upto_turn else f"turn {t}"
        for e in table_estimates(printed):
            rows.append({"kind": "other test (pre-trend, placebo or week-by-week)"
                         if e["pretrend_or_placebo"] else "treatment effect", "term": e["term"],
                         "estimate": e["estimate"], "ci_lo": e["ci_lo"], "ci_hi": e["ci_hi"],
                         "p": _p_text(e["p"]), "code_run_in": when, "note": ""})
        if OTHER_P.search(without_tables(printed)):
            rows.append({"kind": "not readable", "term": "", "estimate": "", "ci_lo": "",
                         "ci_hi": "", "p": "", "code_run_in": when,
                         "note": "this code printed results in its own format; see the log"})
    if not rows:
        rows.append({"kind": "none", "term": "", "estimate": "", "ci_lo": "", "ci_hi": "",
                     "p": "", "code_run_in": "", "note": "no estimate was printed by the code"})
    return rows


def thinking_text(sid: str, turn_rec: dict) -> str:
    """Whatever thinking the provider returned for this turn, labelled by kind."""
    blocks = []
    for i, b in enumerate(turn_rec.get("reasoning", []), 1):
        if b.get("redacted"):
            blocks.append(f"--- block {i}: redacted by the provider ---")
        if b.get("reasoning") and not b.get("redacted"):
            blocks.append(f"--- block {i}: thinking trace ---\n{b['reasoning']}")
        if b.get("summary"):
            blocks.append(f"--- block {i}: reasoning summary ---\n{b['summary']}")
    for j, t in enumerate(inline_thinking(turn_rec.get("text")), 1):
        blocks.append(f"--- inline thinking {j} (written into the reply text) ---\n{t}")
    body = "\n\n".join(blocks) if blocks else "(The provider returned no thinking for this turn.)"
    return f"Summary ID: {sid}\n\n{body}\n"


def write_turn_folders(runs: dict, root: Path, seed: int) -> list[dict]:
    """The T2/T4/T6/T8 folders. Returns the key rows (summary ID -> run)."""
    # Its own seeded stream: the IDs depend only on the seed and the runs.
    rng = random.Random(f"{seed}-summaries-by-turn")
    used, key = set(), []
    for t in TURNS:
        groups: dict[str, list[str]] = {}
        for rid, run in sorted(runs.items()):
            r = run["turns"].get(t)
            if not r or r.get("error") or r.get("text") is None:
                continue
            groups.setdefault(r.get("shared_with") or rid, []).append(rid)
        items = sorted(groups.items())
        rng.shuffle(items)
        tdir = root / f"T{t}"
        for d in ("summaries", "analysis/logs", "analysis/thinking"):
            (tdir / d).mkdir(parents=True, exist_ok=True)
        values = []
        for owner, rids in items:
            while True:
                sid = f"{rng.getrandbits(32):08x}"
                if sid not in used:
                    used.add(sid)
                    break
            run, rec = runs[owner], runs[owner]["turns"][t]
            (tdir / "summaries" / f"{sid}.txt").write_text(
                f"Summary ID: {sid}\n\n{clean(rec['text'])}\n", encoding="utf-8")
            (tdir / "analysis" / "logs" / f"{sid}.txt").write_text(
                f"Summary ID: {sid}\n\n{analysis_log(run, t)}\n", encoding="utf-8")
            (tdir / "analysis" / "thinking" / f"{sid}.txt").write_text(
                thinking_text(sid, rec), encoding="utf-8")
            values += [{"summary_id": sid, "row": i, **v}
                       for i, v in enumerate(analysis_values(run, t), 1)]
            for rid in rids:
                h = runs[rid]["header"]
                key.append({"summary_id": sid, "turn": t, "run_id": rid,
                            "condition": h["condition"], "parent_run_id": h["parent_run_id"] or "",
                            "model": h["model"], "world": h["world"],
                            "dataset_seed": h["dataset_seed"], "replicate": h["replicate"],
                            "machine": h["machine"],
                            "mentions_expectation": "expect" in clean(rec["text"]).lower()})
        write_csv(tdir / "analysis" / "analysis_values.csv", values)
    return key


# --------------------------------------------------------------------------
# Per-run statistics and judge inputs
# --------------------------------------------------------------------------
def run_stats(runs: dict, fps: dict) -> list[dict]:
    stats = []
    for rid, run in sorted(runs.items()):
        h = run["header"]
        own = {t: r for t, r in run["turns"].items() if not r.get("shared_with")}
        u: Counter = Counter()
        for r in own.values():
            u.update({k: v for k, v in r.get("usage", {}).items() if isinstance(v, (int, float))})
        kinds = {("trace" if x.get("reasoning") and not x.get("redacted") else "")
                 + ("summary" if x.get("summary") else "")
                 for r in run["turns"].values() for x in r.get("reasoning", [])}
        stats.append({
            "run_id": rid, "model": h["model"], "world": h["world"],
            "dataset_seed": h["dataset_seed"], "replicate": h["replicate"],
            "condition": h["condition"], "parent_run_id": h["parent_run_id"] or "",
            "machine": h["machine"], "order_index": h["order_index"],
            "completed_turn": run["completed_turn"],
            "counts_for_primary": run["completed_turn"] >= 4,
            "error": (run["end"] or {}).get("error") or "",
            "input_tokens_own": u.get("input_tokens", 0),
            "cache_read_tokens_own": u.get("input_tokens_cache_read", 0),
            "cache_write_tokens_own": u.get("input_tokens_cache_write", 0),
            "output_tokens_own": u.get("output_tokens", 0),
            "reasoning_tokens_own": u.get("reasoning_tokens", 0),
            "total_tokens_own": u.get("total_tokens", 0),
            "model_calls_own": sum(r.get("model_calls", 0) for r in own.values()),
            "tool_calls_by_turn": json.dumps({t: len(r.get("tool_calls", []))
                                              for t, r in sorted(run["turns"].items())}),
            "returned_models": json.dumps(sorted({m for r in run["turns"].values()
                                                  for m in r.get("returned_models", [])})),
            "reasoning_returned": "+".join(sorted(k for k in kinds if k)) or "none",
            "deployment_fingerprints": json.dumps(fps.get(rid, [])),
            **{f"t2_{k}": v for k, v in cross_checks(run, 2).items()},
            **{f"t4_{k}": v for k, v in cross_checks(run, 4).items()},
        })
    return stats


def judge_items(runs: dict) -> list[dict]:
    """Per run x model turn: what a judge may see. No user messages, no
    condition, no thinking."""
    items = []
    for rid, run in sorted(runs.items()):
        h = run["header"]
        for t in TURNS:
            r = run["turns"].get(t)
            if not r or r.get("error") or r.get("text") is None:
                continue
            log = analysis_log(run, t)
            items.append({"run_id": rid, "turn": t, "model": h["model"],
                          "world": h["world"], "dataset_seed": h["dataset_seed"],
                          "summary": clean(r["text"]),
                          "analysis_log": log[:JUDGE_LOG_CAP],
                          "analysis_log_truncated": len(log) > JUDGE_LOG_CAP,
                          "same_text_as_run": r.get("shared_with"),
                          **cross_checks(run, t)})
    return items


def pilot_report(stats: list[dict]) -> str:
    lines = ["# Pilot report (harness numbers; judge-form costs come from the judging step)", ""]
    by = defaultdict(list)
    for s in stats:
        by[(s["model"], s["world"], s["condition"])].append(s)
    lines += ["| model | world | condition | runs | reached turn 4 | reached turn 8 | "
              "mean own tokens / run | mean output tokens / run |", "|---|---|---|---:|---:|---:|---:|---:|"]
    for (m, w, c), rows in sorted(by.items()):
        lines.append(f"| {m} | {w} | {c} | {len(rows)} | "
                     f"{sum(r['completed_turn'] >= 4 for r in rows)} | "
                     f"{sum(r['completed_turn'] >= 8 for r in rows)} | "
                     f"{statistics.mean(r['total_tokens_own'] for r in rows):,.0f} | "
                     f"{statistics.mean(r['output_tokens_own'] for r in rows):,.0f} |")
    lines += ["", "Own tokens exclude an After run's shared turns 1-2, which are counted once, "
              "on its Never run."]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True)
    ap.add_argument("--seed", type=int, required=True, help="seed for the summary IDs, recorded")
    ap.add_argument("--logs", default=str(HARNESS_DIR / "logs"),
                    help="Inspect log folder, for deployment fingerprints")
    a = ap.parse_args()

    runs = load_runs(a.batch)
    if not runs:
        raise SystemExit(f"no runs under {RUNS_DIR / a.batch}")
    root = EXPORTS_DIR / a.batch
    if root.exists():
        shutil.rmtree(root)            # an export is regenerated whole, never merged
    root.mkdir(parents=True)

    key = write_turn_folders(runs, root, a.seed)
    write_csv(root / "key" / "KEY.csv", key)
    stats = run_stats(runs, fingerprints(Path(a.logs), set(runs)))
    write_csv(root / "key" / "run_stats.csv", stats)
    write_csv(root / "key" / "analysis_estimates.csv",
              [{"run_id": rid, "world": run["header"]["world"],
                "dataset_seed": run["header"]["dataset_seed"], **row}
               for rid, run in sorted(runs.items()) for row in per_turn(run)])
    (root / "key" / "pilot_report.md").write_text(pilot_report(stats), encoding="utf-8")
    judge = judge_items(runs)
    (root / "judges").mkdir()
    with (root / "judges" / "judge_items.jsonl").open("w", encoding="utf-8") as f:
        for row in judge:
            f.write(json.dumps(row) + "\n")
    counts = Counter(k["turn"] for k in key)
    per_turn_ids = {t: len({k["summary_id"] for k in key if k["turn"] == t}) for t in TURNS}
    (root / "key" / "manifest.json").write_text(json.dumps({
        "batch": a.batch,
        "exported_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "id_seed": a.seed, "models": sorted({r["header"]["model"] for r in runs.values()}),
        "runs": len(runs), "summaries_per_turn": per_turn_ids,
        "key_rows_per_turn": dict(counts), "judge_items": len(judge),
        "judge_log_cap_chars": JUDGE_LOG_CAP}, indent=1), encoding="utf-8")
    print(f"{len(runs)} runs -> {sum(per_turn_ids.values())} summaries "
          f"({', '.join(f'T{t}: {n}' for t, n in per_turn_ids.items())}), "
          f"{len(judge)} judge items\nwritten to {root}")


if __name__ == "__main__":
    main()
