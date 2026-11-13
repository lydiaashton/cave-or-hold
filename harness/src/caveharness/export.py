"""Blinded export from the per-run logs (handoff sections 6 and 7).

    uv run python -m caveharness.export --batch pilot1 --primary-model <model> --seed 1113

Reads runs/<batch>/<machine>/*.jsonl from every machine. Writes:

  export/<batch>/            -> may go to scorers and judges
    scoring_batch1.csv         turn 4, primary model; grading ID + summary only
    scoring_batch2.csv         turns 6 and 8, primary model; turn not shown
    formA_sheets.csv           human-scored subset: analysis log only
    formB_sheets.csv           human-scored subset: summary only
    judge_items.jsonl          one row per run x model turn, for the judges:
                               summary, analysis log, cross-checks. No user
                               messages, no condition, no thinking.
  export_key/<batch>/        -> study lead only
    KEY.csv                    grading ID -> run, model, world, seed, condition, turn
    run_stats.csv              per run: tokens, completion, tool use, cross-checks
    manifest.json              seeds, counts, inputs
    pilot_report.md            the numbers Lydia asked for from the pilot

Thinking: the logs keep reasoning separately from the summary text. Anything a
model writes inline as <think>...</think> is replaced by a placeholder here.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import random
import re
import secrets
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from caveharness.config import HARNESS_DIR, RUNS_DIR

PLACEHOLDER = "[model reasoning omitted]"
THINK = re.compile(r"<think>.*?</think>", re.S | re.I)
FIGURE_EXT = (".png", ".jpg", ".jpeg", ".pdf", ".svg")
FORM_A_CAP = 60_000   # characters; handoff 6: cap long logs and record truncation


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
    """Replace thinking with a placeholder (handoff section 7).

    Covers a complete <think>...</think> block, and the form some vLLM
    deployments return where the opening tag is dropped and only </think>
    marks where the reasoning ended.
    """
    text = text or ""
    low = text.lower()
    if "</think>" in low and "<think>" not in low:
        text = PLACEHOLDER + text[low.rindex("</think>") + len("</think>"):]
    return THINK.sub(PLACEHOLDER, text).strip()


def analysis_log(run: dict, upto_turn: int) -> str:
    """All code run and everything it printed, up to and including a turn."""
    parts = []
    for t in sorted(run["turns"]):
        if t > upto_turn:
            break
        r = run["turns"][t]
        for i, c in enumerate(r.get("tool_calls", []), 1):
            # Everything the code printed (handoff 5), not only what the model was shown.
            printed = c.get("output_full") or c.get("output") or ""
            parts.append(f"--- code run for summary {t // 2}, call {i} ---\n{c.get('code') or ''}"
                         f"\n--- output ---\n{printed}"
                         + (f"\n--- error ---\n{c['error']}" if c.get("error") else ""))
        if r.get("files_saved"):
            parts.append(f"--- files saved: {', '.join(r['files_saved'])} ---")
    return "\n\n".join(parts) if parts else "(no code was run)"


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
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["grading_id"])
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True)
    ap.add_argument("--primary-model", default=None,
                    help="model string as logged; default: the only model in the batch")
    ap.add_argument("--seed", type=int, required=True, help="shuffle seed, recorded")
    ap.add_argument("--subset-per-cell", type=int, default=0,
                    help="human-scored set: N runs per world x condition (0 = all)")
    ap.add_argument("--logs", default=str(HARNESS_DIR / "logs"),
                    help="Inspect log folder, for deployment fingerprints")
    a = ap.parse_args()

    runs = load_runs(a.batch)
    if not runs:
        raise SystemExit(f"no runs under {RUNS_DIR / a.batch}")
    models = sorted({r["header"]["model"] for r in runs.values()})
    primary = a.primary_model or (models[0] if len(models) == 1 else None)
    if primary is None:
        raise SystemExit(f"several models in the batch, pass --primary-model: {models}")
    rng = random.Random(a.seed)
    out, key_dir = HARNESS_DIR / "export" / a.batch, HARNESS_DIR / "export_key" / a.batch
    key_rows, gid = [], set()

    def new_id() -> str:
        while True:
            g = secrets.token_hex(4)
            if g not in gid:
                gid.add(g)
                return g

    def key(g, sheet, run, turn):
        h = run["header"]
        key_rows.append({"grading_id": g, "sheet": sheet, "run_id": h["run_id"],
                         "model": h["model"], "world": h["world"],
                         "dataset_seed": h["dataset_seed"], "replicate": h["replicate"],
                         "condition": h["condition"], "turn": turn,
                         "parent_run_id": h["parent_run_id"] or "", "machine": h["machine"],
                         "mentions_expectation": "expect" in clean(run["turns"][turn].get("text")).lower()})

    # ---- judge items: every run x model turn, no condition, no user messages
    judge = []
    for rid, run in runs.items():
        h = run["header"]
        for t in (2, 4, 6, 8):
            r = run["turns"].get(t)
            if not r or r.get("error") or r.get("text") is None:
                continue
            log = analysis_log(run, t)
            judge.append({"run_id": rid, "turn": t, "model": h["model"],
                          "world": h["world"], "dataset_seed": h["dataset_seed"],
                          "summary": clean(r["text"]),
                          "analysis_log": log[:FORM_A_CAP],
                          "analysis_log_truncated": len(log) > FORM_A_CAP,
                          "same_text_as_run": r.get("shared_with"),
                          **cross_checks(run, t)})
    out.mkdir(parents=True, exist_ok=True)
    with (out / "judge_items.jsonl").open("w", encoding="utf-8") as f:
        for row in judge:
            f.write(json.dumps(row) + "\n")

    # ---- the human-scored set: primary model, an equal number of runs drawn at
    # random from each world x condition cell with the recorded seed (design:
    # "an equal number drawn at random from each cell"). Batch 1, batch 2 and
    # the form A / B sheets all come from these same runs.
    cells = defaultdict(list)
    for run in runs.values():
        h = run["header"]
        if h["model"] == primary and run["completed_turn"] >= 4:
            cells[(h["world"], h["condition"])].append(run)
    subset = []
    for k in sorted(cells):
        pool = sorted(cells[k], key=lambda r: r["header"]["run_id"])
        rng.shuffle(pool)
        subset += pool[: a.subset_per_cell] if a.subset_per_cell else pool

    def batch_rows(turns: tuple[int, ...], sheet: str) -> list[dict]:
        """Shuffled summaries; the sheet shows neither condition nor turn."""
        items = [(run, t) for run in subset for t in turns
                 if t in run["turns"] and not run["turns"][t].get("error")
                 and run["turns"][t].get("text") is not None]
        rng.shuffle(items)
        rows = []
        for run, t in items:
            g = new_id()
            key(g, sheet, run, t)
            rows.append({"grading_id": g, "summary": clean(run["turns"][t]["text"])})
        return rows

    write_csv(out / "scoring_batch1.csv", batch_rows((4,), "batch1"))
    write_csv(out / "scoring_batch2.csv", batch_rows((6, 8), "batch2"))

    # ---- form A / B sheets for the same runs (turn 4)
    form_a, form_b = [], []
    for run in subset:
        ga, gb = new_id(), new_id()
        key(ga, "formA", run, 4)
        key(gb, "formB", run, 4)
        log = analysis_log(run, 4)
        form_a.append({"grading_id": ga, "analysis_log": log[:FORM_A_CAP],
                       "truncated": len(log) > FORM_A_CAP})
        form_b.append({"grading_id": gb, "summary": clean(run["turns"][4]["text"])})
    rng.shuffle(form_a)
    rng.shuffle(form_b)
    write_csv(out / "formA_sheets.csv", form_a)
    write_csv(out / "formB_sheets.csv", form_b)

    # ---- key and run stats: study lead only
    write_csv(key_dir / "KEY.csv", key_rows)
    fps = fingerprints(Path(a.logs), set(runs))
    stats = []
    for rid, run in runs.items():
        h = run["header"]
        own = {t: r for t, r in run["turns"].items() if not r.get("shared_with")}
        u: Counter = Counter()
        for r in own.values():
            u.update({k: v for k, v in r.get("usage", {}).items() if isinstance(v, (int, float))})
        reasoning_kinds = {("trace" if x.get("reasoning") and not x.get("redacted") else "")
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
            "reasoning_returned": "+".join(sorted(k for k in reasoning_kinds if k)) or "none",
            "deployment_fingerprints": json.dumps(fps.get(rid, [])),
            **{f"t2_{k}": v for k, v in cross_checks(run, 2).items()},
            **{f"t4_{k}": v for k, v in cross_checks(run, 4).items()},
        })
    write_csv(key_dir / "run_stats.csv", stats)
    (key_dir / "manifest.json").write_text(json.dumps({
        "batch": a.batch, "exported_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "shuffle_seed": a.seed, "primary_model": primary, "models": models,
        "runs": len(runs), "judge_items": len(judge), "key_rows": len(key_rows),
        "subset_per_cell": a.subset_per_cell, "form_a_cap_chars": FORM_A_CAP}, indent=1),
        encoding="utf-8")
    (key_dir / "pilot_report.md").write_text(pilot_report(stats), encoding="utf-8")
    print(f"{len(runs)} runs -> {len(judge)} judge items, "
          f"{sum(1 for k in key_rows if k['sheet'] == 'batch1')} batch-1 rows, "
          f"{sum(1 for k in key_rows if k['sheet'] == 'batch2')} batch-2 rows, "
          f"{len(form_a)} form A/B pairs")
    print(f"scorer/judge files: {out}\nstudy-lead-only files: {key_dir}")


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
              "on its Never run.", "", "## Under Never: did the code cluster by branch? (underpowered)", ""]
    nv = [s for s in stats if s["condition"] == "never" and s["world"] == "underpowered"]
    if nv:
        k = sum(bool(s["t2_cluster_in_code"]) for s in nv)
        lines.append(f"'cluster' appears in the code by the first summary in {k} of {len(nv)} Never runs. "
                     "A text check, not the judge's form A field: it counts any mention of clustering.")
    lines += ["", "## Pre-switch weeks checked (confounded)", "",
              "Not detectable from a text match; this is form A's 'weeks before the switch "
              "checked' field from the judging step."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
