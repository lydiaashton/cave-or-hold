"""Blinded export from the per-run logs (handoff sections 6 and 7).

    uv run python -m caveharness.export --batch pilot1 --primary-model <model> --seed 1113

Reads runs/<batch>/<machine>/*.jsonl from every machine. Writes:

  export/<batch>/            -> may go to scorers (nothing else in it)
    scoring_batch1.csv         turn 4, primary model; grading ID + summary only
    formA_sheets.csv           human-scored subset: analysis log only
    formB_sheets.csv           human-scored subset: summary only
  export_key/<batch>/        -> study lead only
    KEY.csv                    grading ID -> run, model, world, seed, condition, turn
                               (an earlier KEY.csv is kept as KEY.csv.prev-<time>)
    grading_id_salt.txt        the secret behind the grading IDs (made once per batch)
    scoring_batch2.csv         turns 6 and 8, primary model; turn not shown. Released
                               to scorers only after every scorer has finished batch 1
    run_stats.csv              per run: tokens, cost, completion, tool use, cross-checks
    manifest.json              seeds, counts, inputs
    pilot_report.md            the numbers Lydia asked for from the pilot

The human subset is drawn with the recorded seed. Grading IDs are a keyed hash
of each item, so the same item keeps its ID on every re-export of a batch.
judge_items() is what the judge runner (caveharness.judge) gives the judges:
it holds run IDs, so it is never written to the scorer folder. Thinking: the
logs keep reasoning separately from the summary text; anything a model writes
inline as <think>...</think> is replaced by a placeholder here.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import hmac
import json
import random
import re
import secrets
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from caveharness.config import HARNESS_DIR, RUNS_DIR
from caveharness.costs import cost, fmt, load_prices

PLACEHOLDER = "[model reasoning omitted]"
# <think>...</think> and <thinking>...</thinking>, with or without attributes.
THINK = re.compile(r"<(think(?:ing)?)\b[^>]*>.*?</\1>", re.S | re.I)
THINK_CLOSE = re.compile(r"</think(?:ing)?>", re.I)
THINK_OPEN = re.compile(r"<think(?:ing)?\b[^>]*>", re.I)
FIGURE_EXT = (".png", ".jpg", ".jpeg", ".pdf", ".svg")
FORM_A_CAP = 60_000   # characters; handoff 6: cap long logs and record truncation
# Characters kept from the start and from the end of each code call's output
# in what form A sees. A regression table's treatment row is often its last
# line (after 709 branch dummies in the confounded world), so a head-only cut
# would hide the estimate and every later check.
CALL_OUTPUT_KEEP = 4_000


def _attempt_rank(run: dict) -> tuple:
    """Which of two logs of one run to keep: further first, then newer."""
    return run["completed_turn"], run["header"].get("access_time_utc") or ""


def load_runs(batch: str) -> dict[str, dict]:
    runs: dict[str, dict] = {}
    for f in sorted((RUNS_DIR / batch).rglob("*.jsonl")):
        recs = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
        if not recs or recs[0].get("record") != "header":
            continue
        h = recs[0]
        turns = {r["turn"]: r for r in recs if r.get("record") == "turn"}
        end = next((r for r in reversed(recs) if r.get("record") == "end"), None)
        completed = max((t for t, r in turns.items() if not r.get("error")), default=0)
        run = {"header": h, "turns": turns, "end": end, "completed_turn": completed, "file": str(f)}
        old = runs.get(h["run_id"])
        if old:
            # The same unit run on two machines (e.g. a re-run elsewhere): keep
            # the attempt that got further; on a tie the newer one, so a re-run
            # pair's Never and After come from the same attempt.
            keep, drop = (run, old) if _attempt_rank(run) > _attempt_rank(old) else (old, run)
            print(f"warning: two logs for run {h['run_id']}; keeping {keep['file']} "
                  f"(turn {keep['completed_turn']}), ignoring {drop['file']} "
                  f"(turn {drop['completed_turn']})")
            run = keep
        runs[h["run_id"]] = run
    for rid, run in runs.items():   # an After run must share turn 2 with its parent
        parent = runs.get(run["header"].get("parent_run_id") or "")
        mine, theirs = run["turns"].get(2), parent and parent["turns"].get(2)
        if mine and theirs and mine.get("text") != theirs.get("text"):
            print(f"warning: After run {rid} and its Never run come from different attempts "
                  f"({run['file']} vs {parent['file']})")
    return runs


def clean(text: str | None) -> str:
    """Replace thinking with a placeholder (handoff section 7).

    Covers complete <think>...</think> blocks; the form some vLLM deployments
    return, where the opening tag is dropped and only </think> marks where the
    reasoning ended; and a reply cut off before its reasoning closed.
    """
    text = THINK.sub(PLACEHOLDER, text or "")
    closes = list(THINK_CLOSE.finditer(text))
    if closes:   # opening tag dropped: everything up to the last close is reasoning
        text = PLACEHOLDER + text[closes[-1].end():]
    opened = THINK_OPEN.search(text)
    if opened:   # cut off before the reasoning closed
        text = text[:opened.start()] + PLACEHOLDER
    return text.strip()


def gradeable(run: dict, turn: int) -> bool:
    """A model turn with a summary to grade: logged, no error, and some text
    besides reasoning (a reply cut off mid-thought has none)."""
    r = run["turns"].get(turn)
    return (bool(r) and not r.get("error")
            and bool(clean(r.get("text")).replace(PLACEHOLDER, "").strip()))


def _trim(text: str, keep: int | None) -> str:
    """The first and last `keep` characters, with a note of what was cut."""
    if keep is None or len(text) <= 2 * keep:
        return text
    return f"{text[:keep]}\n[... {len(text) - 2 * keep} characters omitted ...]\n{text[-keep:]}"


def analysis_log(run: dict, upto_turn: int, keep_per_call: int | None = None) -> str:
    """All code run and everything it printed, up to and including a turn.

    keep_per_call: if set, each call's output keeps only its first and last
    keep_per_call characters (for form A; see CALL_OUTPUT_KEEP).
    """
    parts = []
    for t in sorted(run["turns"]):
        if t > upto_turn:
            break
        r = run["turns"][t]
        for i, c in enumerate(r.get("tool_calls", []), 1):
            # Everything the code printed (handoff 5), not only what the model was shown.
            printed = _trim(c.get("output_full") or c.get("output") or "", keep_per_call)
            parts.append(f"--- code run for summary {t // 2}, call {i} ---\n{c.get('code') or ''}"
                         f"\n--- output ---\n{printed}"
                         + (f"\n--- error ---\n{c['error']}" if c.get("error") else ""))
        if r.get("files_saved"):
            parts.append(f"--- files saved: {', '.join(r['files_saved'])} ---")
    return "\n\n".join(parts) if parts else "(no code was run)"


def form_a_log(run: dict, upto_turn: int) -> tuple[str, bool]:
    """The analysis log as form A sees it, and whether anything was cut
    (handoff 6: a length cap, with "truncated" recorded). Each call's output is
    trimmed to its start and end, then the whole log is, so the code of later
    turns (re-analysis after turn 3) is kept as well."""
    full = analysis_log(run, upto_turn)
    log = _trim(analysis_log(run, upto_turn, CALL_OUTPUT_KEEP), FORM_A_CAP // 2)
    return log, log != full


def judge_items(runs: dict[str, dict]) -> list[dict]:
    """One item per run x gradeable model turn: everything any judge call may
    use, and nothing else (no user messages, no condition, no thinking). An
    After run's turn 2 is its Never run's turn 2 (same_text_as_run names it)."""
    items = []
    for rid, run in runs.items():
        h = run["header"]
        for t in (2, 4, 6, 8):
            if not gradeable(run, t):
                continue
            log, truncated = form_a_log(run, t)
            items.append({"run_id": rid, "turn": t, "model": h["model"],
                          "world": h["world"], "dataset_seed": h["dataset_seed"],
                          "summary": clean(run["turns"][t]["text"]),
                          "analysis_log": log, "analysis_log_truncated": truncated,
                          "same_text_as_run": run["turns"][t].get("shared_with"),
                          **cross_checks(run, t)})
    return items


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
    rng = random.Random(a.seed)   # draws the human subset (the recorded seed)
    out, key_dir = HARNESS_DIR / "export" / a.batch, HARNESS_DIR / "export_key" / a.batch
    # Grading IDs are a keyed hash of the item under a random salt that stays
    # with the key (study lead only). The same item keeps its ID on every
    # re-export, IDs never repeat across batches, and neither the IDs nor the
    # row order on a sheet can be traced back to a condition without the salt.
    salt = _grading_salt(key_dir)
    key_rows, gid = [], set()

    def new_id(sheet: str, run: dict, turn: int) -> str:
        g = hmac.new(salt.encode(), f"{sheet}|{run['header']['run_id']}|{turn}".encode(),
                     hashlib.sha256).hexdigest()[:10]
        if g in gid:
            raise SystemExit(f"grading ID collision ({g}); export again")
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

    # Judge items are built by caveharness.judge from the same logs, with the
    # same function; only their number is reported here.
    judge = judge_items(runs)

    # ---- the human-scored set: primary model, an equal number of runs drawn at
    # random from each world x condition cell with the recorded seed (design:
    # "an equal number drawn at random from each cell"). Batch 1, batch 2 and
    # the form A / B sheets all come from these same runs. Cells are drawn in
    # sorted order, so After before Never; a Never run whose After run was drawn
    # is left out, because the pair's shared first analysis would show on the
    # form A sheet which two logs belong together (and so which are not Before).
    cells = defaultdict(list)
    for run in runs.values():
        h = run["header"]
        if h["model"] == primary and run["completed_turn"] >= 4 and gradeable(run, 4):
            cells[(h["world"], h["condition"])].append(run)
    subset, drawn_parents, cell_counts = [], set(), {}
    for k in sorted(cells):
        pool = sorted(cells[k], key=lambda r: r["header"]["run_id"])
        if a.subset_per_cell:
            pool = [r for r in pool if r["header"]["run_id"] not in drawn_parents]
        rng.shuffle(pool)
        take = pool[: a.subset_per_cell] if a.subset_per_cell else pool
        if a.subset_per_cell and len(take) < a.subset_per_cell:
            raise SystemExit(f"cell {k}: {len(cells[k])} runs reached turn 4, "
                             f"{len(cells[k]) - len(pool)} left out as the Never runs of drawn "
                             f"After runs; --subset-per-cell {a.subset_per_cell} needs more")
        drawn_parents |= {r["header"]["parent_run_id"] for r in take if r["header"]["parent_run_id"]}
        cell_counts["/".join(k)] = {"completed": len(cells[k]), "drawn": len(take)}
        subset += take
    if not a.subset_per_cell:
        print("note: every run is on the sheets (--subset-per-cell 0), so both runs of each "
              "Never/After pair are on formA_sheets.csv with the same turn-2 analysis; "
              "pass --subset-per-cell N for the main runs")

    def shuffled(rows: list, sheet: str) -> list:
        random.Random(f"{salt}:{sheet}").shuffle(rows)
        return rows

    def batch_rows(turns: tuple[int, ...], sheet: str) -> list[dict]:
        """Shuffled summaries; the sheet shows neither condition nor turn."""
        items = shuffled([(run, t) for run in subset for t in turns if gradeable(run, t)], sheet)
        rows = []
        for run, t in items:
            g = new_id(sheet, run, t)
            key(g, sheet, run, t)
            rows.append({"grading_id": g, "summary": clean(run["turns"][t]["text"])})
        return rows

    write_csv(out / "scoring_batch1.csv", batch_rows((4,), "batch1"))
    # Batch 2 is released only after every scorer has finished batch 1
    # (handoff 7), so it waits with the study lead, not in the scorer folder.
    write_csv(key_dir / "scoring_batch2.csv", batch_rows((6, 8), "batch2"))

    # ---- form A / B sheets for the same runs (turn 4)
    form_a, form_b = [], []
    for run in subset:
        ga, gb = new_id("formA", run, 4), new_id("formB", run, 4)
        key(ga, "formA", run, 4)
        key(gb, "formB", run, 4)
        log, truncated = form_a_log(run, 4)
        form_a.append({"grading_id": ga, "analysis_log": log, "truncated": truncated})
        form_b.append({"grading_id": gb, "summary": clean(run["turns"][4]["text"])})
    write_csv(out / "formA_sheets.csv", shuffled(form_a, "formA"))
    write_csv(out / "formB_sheets.csv", shuffled(form_b, "formB"))

    # ---- key and run stats: study lead only. A key that may already belong to
    # sheets sent out is never overwritten.
    previous = key_dir / "KEY.csv"
    if previous.exists():
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
        previous.rename(previous.with_name(f"KEY.csv.prev-{stamp}"))
    write_csv(key_dir / "KEY.csv", key_rows)
    fps = fingerprints(Path(a.logs), set(runs))
    prices = load_prices()
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
        c = cost(prices, h["model"], dict(u))
        stats.append({
            "run_id": rid, "model": h["model"], "world": h["world"],
            "dataset_seed": h["dataset_seed"], "replicate": h["replicate"],
            "condition": h["condition"], "parent_run_id": h["parent_run_id"] or "",
            # unit_id + machine_index: what `--sample-id` needs to re-run a unit
            "unit_id": h.get("unit_id", ""), "machine_index": h.get("machine_index", ""),
            "machine": h["machine"], "order_index": h["order_index"],
            "completed_turn": run["completed_turn"],
            "counts_for_primary": run["completed_turn"] >= 4,
            "error": (run["end"] or {}).get("error") or "",
            "turns_cut_off": json.dumps(sorted(t for t, r in run["turns"].items()
                                               if r.get("reply_cut_off"))),
            "est_cost_own": round(c[0], 6) if c else "",
            "cost_unit": c[1] if c else "price not set",
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
        "subset_per_cell": a.subset_per_cell, "subset_cells": cell_counts,
        "subset_rule": "equal draw per world x condition with the seed; After cells first, "
                       "and a Never run whose After run was drawn is left out",
        "grading_ids": "HMAC-SHA256(salt, sheet|run_id|turn)[:10]; the salt is "
                       "grading_id_salt.txt in this folder; sheets are shuffled with the salt",
        "form_a_cap_chars": FORM_A_CAP, "form_a_call_output_keep_chars": CALL_OUTPUT_KEEP},
        indent=1), encoding="utf-8")
    (key_dir / "pilot_report.md").write_text(pilot_report(stats), encoding="utf-8")
    print(f"{len(runs)} runs -> {len(judge)} judge items, "
          f"{sum(1 for k in key_rows if k['sheet'] == 'batch1')} batch-1 rows, "
          f"{sum(1 for k in key_rows if k['sheet'] == 'batch2')} batch-2 rows, "
          f"{len(form_a)} form A/B pairs")
    print(f"scorer files: {out}\nstudy-lead-only files (incl. batch 2): {key_dir}")


def _grading_salt(key_dir: Path) -> str:
    """The batch's grading-ID salt, made once and kept with the key."""
    f = key_dir / "grading_id_salt.txt"
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(secrets.token_hex(16), encoding="utf-8")
    return f.read_text(encoding="utf-8").strip()


def _mean_cost(rows: list[dict]) -> str:
    """Mean cost per run, if every run is priced in one unit."""
    units = {r["cost_unit"] for r in rows}
    if len(units) != 1 or "price not set" in units:
        return "price not set"
    return fmt((statistics.mean(r["est_cost_own"] for r in rows), units.pop()))


def pilot_report(stats: list[dict]) -> str:
    lines = ["# Pilot report (harness numbers; judge-form costs are in the judge report)", ""]
    by = defaultdict(list)
    for s in stats:
        by[(s["model"], s["world"], s["condition"])].append(s)
    lines += ["| model | world | condition | runs | reached turn 4 | reached turn 8 | "
              "mean own tokens / run | mean output tokens / run | est. cost / run |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for (m, w, c), rows in sorted(by.items()):
        lines.append(f"| {m} | {w} | {c} | {len(rows)} | "
                     f"{sum(r['completed_turn'] >= 4 for r in rows)} | "
                     f"{sum(r['completed_turn'] >= 8 for r in rows)} | "
                     f"{statistics.mean(r['total_tokens_own'] for r in rows):,.0f} | "
                     f"{statistics.mean(r['output_tokens_own'] for r in rows):,.0f} | "
                     f"{_mean_cost(rows)} |")
    lines += ["", "Own tokens exclude an After run's shared turns 1-2, which are counted once, "
              "on its Never run. Cost uses harness/prices.toml.", "",
              "## Under Never: did the code cluster by branch? (underpowered)", ""]
    nv = [s for s in stats if s["condition"] == "never" and s["world"] == "underpowered"]
    for m in sorted({s["model"] for s in nv}):
        mine = [s for s in nv if s["model"] == m]
        k = sum(bool(s["t2_cluster_in_code"]) for s in mine)
        lines.append(f"- {m}: 'cluster' appears in the code by the first summary in {k} of "
                     f"{len(mine)} Never runs.")
    lines.append("\nA text check: it counts any mention of clustering. The judges' form A "
                 "field 'clustered_se_by_branch' is in the judge report." if nv else
                 "No Never runs in the underpowered world in this batch.")
    lines += ["", "## Pre-switch weeks checked (confounded)", "",
              "Not detectable from a text match; form A's 'pre_switch_weeks_checked' field "
              "is in the judge report.", "", "## Runs that stopped before turn 8", ""]
    stopped = sorted((s for s in stats if s["completed_turn"] < 8),
                     key=lambda s: (s["model"], s["completed_turn"], s["run_id"]))
    lines += [f"- {s['run_id']} ({s['model']}, {s['world']}, {s['condition']}, unit "
              f"{s['unit_id']}, machine {s['machine']}): completed turn {s['completed_turn']}; "
              f"{s['error'] or 'no error recorded (still running, or the log was cut)'}"
              for s in stopped] or ["None."]
    cut = [s for s in stats if s["turns_cut_off"] != "[]"]
    if cut:
        lines += ["", "Replies cut off by the provider's output limit (kept, flagged): "
                  + ", ".join(f"{s['run_id']} turns {s['turns_cut_off']}" for s in cut)]
    # Handoff 8: machine must not stand in for condition, and that can be checked.
    lines += ["", "## Runs by machine x world x condition", "",
              "| machine | world | condition | runs |", "|---|---|---|---:|"]
    lines += [f"| {mach} | {w} | {c} | {n} |" for (mach, w, c), n in
              sorted(Counter((s["machine"], s["world"], s["condition"]) for s in stats).items())]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
