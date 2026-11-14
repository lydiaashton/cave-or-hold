"""Export one batch into the repository (study lead's layout, 13 Nov).

    uv run python -m caveharness.export --batch pilot2

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
    scoring/
      batch1/summaries/<id>.txt   turn-4 summaries for human scorers
      batch2/summaries/<id>.txt   turn-6 and turn-8 summaries, released after batch 1
      round1/ round2/ round3/     with --scoring-per-world (main runs) instead of
                                  batch1/batch2: summaries/ and order.csv, in blocks
                                  of whole datasets (see write_scoring_rounds)
                                  Only the primary model's never, before_B and
                                  after_B cells (--primary-model, --scoring-wording,
                                  --scoring-per-cell). Other wordings go to judges only
    key/
      KEY.csv                     summary ID -> run, condition (kind and wording),
                                  turn, model, dataset, quotes_expectation_sentence
      scoring_sets.csv            which summaries went into each scoring batch
      id_secret.txt               the secret the summary IDs are made from
      run_stats.csv               per run: tokens, cost, completion, errors, tool use
      analysis_estimates.csv      per run x turn: the numbers behind each summary
      manifest.json, pilot_report.md
    judges/
      judge_items.jsonl           what the judges may see, per run x turn
    judging/                      written by caveharness.judge, never by the export:
                                  judgments, judge results and the judge report

Summary IDs are a keyed hash of (turn, run) under a secret made once per batch
and kept in key/: re-exporting gives every summary the same ID even if runs were
added since, and IDs never repeat across batches. An After run's turn 2 is its
Never run's, so each turn-2 summary is written once and the key lists both runs.

Batches exported before this scheme (pilot1) have no id_secret.txt. Re-exporting
one would rename every summary, so it is refused unless --replace-ids is given.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import hmac
import json
import re
import secrets
import shutil
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from caveharness.config import EXPORTS_DIR, HARNESS_DIR, RUNS_DIR
from caveharness.costs import cost, load_prices
from caveharness.estimates import OTHER_P, per_turn, table_estimates, without_tables
from caveharness.prompts import Prompts

TURNS = (2, 4, 6, 8)
EXPORT_OWNED = ("T2", "T4", "T6", "T8", "key", "judges", "scoring")   # never "judging"
PLACEHOLDER = "[model reasoning omitted]"
# <think>...</think> and <thinking>...</thinking>, with or without attributes.
THINK = re.compile(r"<(think(?:ing)?)\b[^>]*>.*?</\1>", re.S | re.I)
THINK_CLOSE = re.compile(r"</think(?:ing)?>", re.I)
THINK_OPEN = re.compile(r"<think(?:ing)?\b[^>]*>", re.I)
FIGURE_EXT = (".png", ".jpg", ".jpeg", ".pdf", ".svg")
JUDGE_LOG_CAP = 60_000   # characters; handoff 6: cap long logs and record truncation
# Characters kept from the start and from the end of each code call's output
# in what the judges see. A regression table's treatment row is often its last
# line (after 709 branch dummies in the confounded world), so a head-only cut
# would hide the estimate and every later check.
CALL_OUTPUT_KEEP = 4_000
ID_LENGTH = 10


# --------------------------------------------------------------------------
# Reading the runs
# --------------------------------------------------------------------------
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
    """The summary with any inline thinking replaced by a placeholder.

    Covers complete <think>/<thinking> blocks; the form some vLLM deployments
    return, where the opening tag is dropped and only the closing tag marks
    where the reasoning ended; and a reply cut off before its reasoning closed.
    """
    text = THINK.sub(PLACEHOLDER, text or "")
    closes = list(THINK_CLOSE.finditer(text))
    if closes:   # opening tag dropped: everything up to the last close is reasoning
        text = PLACEHOLDER + text[closes[-1].end():]
    opened = THINK_OPEN.search(text)
    if opened:   # cut off before the reasoning closed
        text = text[:opened.start()] + PLACEHOLDER
    return text.strip()


def inline_thinking(text: str | None) -> list[str]:
    """Thinking a model wrote into its reply text, which clean() removes."""
    text = text or ""
    found = [m.group(0) for m in THINK.finditer(text)]
    rest = THINK.sub("", text)
    closes = list(THINK_CLOSE.finditer(rest))
    if closes:
        found.append(rest[:closes[-1].start()])
        rest = rest[closes[-1].end():]
    opened = THINK_OPEN.search(rest)
    if opened:
        found.append(rest[opened.start():])
    tags = re.compile(r"</?think(?:ing)?\b[^>]*>", re.I)
    return [t for t in (tags.sub("", x).strip() for x in found) if t]


def gradeable(run: dict, turn: int) -> bool:
    """A model turn with a summary to grade: logged, no error, and some text
    besides reasoning (a reply cut off mid-thought has none)."""
    r = run["turns"].get(turn)
    return (bool(r) and not r.get("error")
            and bool(clean(r.get("text")).replace(PLACEHOLDER, "").strip()))


def _printed(call: dict) -> str:
    # Everything the code printed (handoff 5), not only what the model was shown.
    return call.get("output_full") or call.get("output") or ""


def _trim(text: str, keep: int | None) -> str:
    """The first and last `keep` characters, with a note of what was cut."""
    if keep is None or len(text) <= 2 * keep:
        return text
    return f"{text[:keep]}\n[... {len(text) - 2 * keep} characters omitted ...]\n{text[-keep:]}"


def analysis_log(run: dict, upto_turn: int, keep_per_call: int | None = None) -> str:
    """All code the model ran and everything it printed, up to and including a
    turn. Code and output only: no user messages, no thinking. keep_per_call:
    if set, each call's output keeps only its first and last characters."""
    parts = []
    for t in sorted(run["turns"]):
        if t > upto_turn:
            break
        r = run["turns"][t]
        calls = r.get("tool_calls", [])
        for i, c in enumerate(calls, 1):
            parts.append(f"=== Code run in turn {t}, call {i} of {len(calls)} ===\n"
                         f"{c.get('code') or ''}\n--- printed ---\n"
                         f"{_trim(_printed(c), keep_per_call)}"
                         + (f"\n--- error ---\n{c['error']}" if c.get("error") else ""))
        if r.get("files_saved"):
            parts.append(f"--- files saved in turn {t}: {', '.join(r['files_saved'])} ---")
    if not run["turns"].get(upto_turn, {}).get("tool_calls"):
        parts.append(f"(No code was run in turn {upto_turn}.)")
    return "\n\n".join(parts) if parts else "(No code was run.)"


def form_a_log(run: dict, upto_turn: int) -> tuple[str, bool]:
    """The analysis log as the judges see it, and whether anything was cut
    (handoff 6: a length cap, with "truncated" recorded). Each call's output is
    trimmed to its start and end, then the whole log is, so the code of later
    turns (re-analysis after turn 3) is kept as well."""
    full = analysis_log(run, upto_turn)
    log = _trim(analysis_log(run, upto_turn, CALL_OUTPUT_KEEP), JUDGE_LOG_CAP // 2)
    return log, log != full


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


def summary_id(secret: str, turn: int, owner_run_id: str) -> str:
    """A keyed hash of (turn, run): fixed for that summary whatever else is in
    the batch, different at every turn, and not traceable without the secret."""
    return hmac.new(secret.encode(), f"T{turn}|{owner_run_id}".encode(),
                    hashlib.sha256).hexdigest()[:ID_LENGTH]


def _norm(text: str) -> str:
    return " ".join(text.lower().replace("*", "").split()).rstrip(".")


EXPECTATION_SENTENCES = [_norm(s) for s in Prompts.load().all_expectation_sentences()]


def quotes_expectation_sentence(text: str | None) -> bool:
    """Whether the summary repeats one of the expectation sentences word for
    word (any wording, A to D). A narrow text check, not a disclosure measure:
    a paraphrase ("the team hoped for an effect") is not caught, and a Never
    summary saying "expected gains" is no longer counted, as the old
    "contains 'expect'" check did. Disclosure is judged by form B."""
    t = _norm(clean(text))
    return any(s in t for s in EXPECTATION_SENTENCES)


def write_turn_folders(runs: dict, root: Path, secret: str) -> list[dict]:
    """The T2/T4/T6/T8 folders. Returns the key rows (summary ID -> run)."""
    used, key = set(), []
    for t in TURNS:
        groups: dict[str, list[str]] = {}
        for rid, run in sorted(runs.items()):
            if gradeable(run, t):
                groups.setdefault(run["turns"][t].get("shared_with") or rid, []).append(rid)
        tdir = root / f"T{t}"
        for d in ("summaries", "analysis/logs", "analysis/thinking"):
            (tdir / d).mkdir(parents=True, exist_ok=True)
        values = []
        for owner, rids in sorted(groups.items()):
            sid = summary_id(secret, t, owner)
            if sid in used:
                raise SystemExit(f"summary ID collision ({sid}); this should not happen")
            used.add(sid)
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
                kind, _, wording = h["condition"].partition("_")
                key.append({"summary_id": sid, "turn": t, "run_id": rid,
                            "condition": h["condition"], "condition_kind": kind,
                            "expectation_wording": wording or h.get("expectation_option") or "",
                            "parent_run_id": h["parent_run_id"] or "",
                            "model": h["model"], "world": h["world"],
                            "dataset_seed": h["dataset_seed"], "replicate": h["replicate"],
                            "machine": h["machine"],
                            "quotes_expectation_sentence": quotes_expectation_sentence(rec["text"])})
        # Rows in ID order: the order carries no information about the runs.
        values.sort(key=lambda v: (v["summary_id"], v["row"]))
        write_csv(tdir / "analysis" / "analysis_values.csv", values)
    key.sort(key=lambda k: (k["turn"], k["summary_id"], k["run_id"]))
    return key


def write_scoring_sets(runs: dict, key: list[dict], root: Path, secret: str,
                       primary_model: str, wording: str, per_cell: int) -> list[dict]:
    """The summaries human scorers grade (study lead, 13 Nov): only the primary
    model's Never, before_<wording> and after_<wording> cells. Other wordings
    (D) go to the LLM judges only.

    scoring/batch1/summaries/ holds turn 4; scoring/batch2/summaries/ turns 6
    and 8 of the same runs, released only after every scorer finishes batch 1.
    Files and IDs are the T4/T6/T8 ones, so nothing new needs keying. With
    per_cell, the draw is pair-aware (analysis reviewer, 14 Nov): per world, the
    first per_cell datasets in an order fixed by the batch secret are taken, and
    for each of them the Never, before_<wording> and after_<wording> runs all go
    in, so the paired tests (After vs Never, After vs Before) keep every pair on
    human labels. Only datasets with a gradeable turn 4 in all three cells are
    eligible; the rest are skipped and counted. The same draw comes out on every
    re-export. Returns the rows for key/scoring_sets.csv."""
    cells = ("never", f"before_{wording}", f"after_{wording}")
    ids = {(k["run_id"], k["turn"]): k["summary_id"] for k in key}
    # one "match" = one dataset (and replicate) in one world, holding one run per cell
    matches: dict[tuple, dict[str, str]] = defaultdict(dict)
    for rid, run in runs.items():
        h = run["header"]
        if h["model"] == primary_model and h["condition"] in cells:
            m = (h["world"], h["dataset_seed"], h["replicate"])
            if h["condition"] in matches[m]:
                raise ValueError(f"two {h['condition']} runs for {m}: {matches[m][h['condition']]} and {rid}")
            matches[m][h["condition"]] = rid
    if not per_cell:
        drawn = {rid for m in matches.values() for rid in m.values()}
    else:
        draw = lambda m: hmac.new(secret.encode(), f"draw|{m[0]}|{m[1]}|{m[2]}".encode(),
                                  hashlib.sha256).hexdigest()
        drawn = set()
        for world in sorted({m[0] for m in matches}):
            ranked = sorted((m for m in matches if m[0] == world), key=draw)
            complete = [m for m in ranked if all(c in matches[m] and (matches[m][c], 4) in ids
                                                 for c in cells)]
            take = complete[:per_cell]
            skipped = sum(1 for m in ranked[:ranked.index(take[-1]) + 1] if m not in complete) if take else 0
            if len(take) < per_cell:
                print(f"scoring draw, {world}: only {len(take)} datasets have a gradeable turn 4 "
                      f"in all three cells (asked for {per_cell})")
            elif skipped:
                print(f"scoring draw, {world}: skipped {skipped} incomplete dataset(s) in the draw order")
            for m in take:
                drawn |= set(matches[m][c] for c in cells)
    ids = {(k["run_id"], k["turn"]): k["summary_id"] for k in key}
    rows = []
    for batch, turns in ((1, (4,)), (2, (6, 8))):
        out = root / "scoring" / f"batch{batch}" / "summaries"
        out.mkdir(parents=True, exist_ok=True)
        for rid in sorted(drawn):
            for t in turns:
                sid = ids.get((rid, t))
                if sid is None:          # that turn is not gradeable (failed, or blank)
                    continue
                shutil.copyfile(root / f"T{t}" / "summaries" / f"{sid}.txt", out / f"{sid}.txt")
                h = runs[rid]["header"]
                rows.append({"summary_id": sid, "scoring_batch": batch, "turn": t, "run_id": rid,
                             "condition": h["condition"], "world": h["world"],
                             "dataset_seed": h["dataset_seed"], "replicate": h["replicate"]})
    return sorted(rows, key=lambda r: (r["scoring_batch"], r["summary_id"]))


def _rank(secret: str, tag: str, m: tuple) -> str:
    return hmac.new(secret.encode(), f"{tag}|{m[0]}|{m[1]}|{m[2]}".encode(),
                    hashlib.sha256).hexdigest()


def write_scoring_rounds(runs: dict, key: list[dict], root: Path, secret: str,
                         primary_model: str, wording: str, per_world: dict[str, int],
                         n_round2: int, n_round3: int,
                         primary_world: str = "underpowered") -> list[dict]:
    """The three scoring pages, in blocks of whole datasets (Stage A section 7;
    study lead, 14 Nov). A block is one dataset's Never, before_<wording> and
    after_<wording> runs. Blocks come in an order fixed by the batch secret,
    the same for every scorer; the page shuffles only within a block. Scoring
    stops by time, so the analysis keeps the blocks every panel scorer finished,
    and any prefix of the order is a random draw with all cells balanced.

      round1  turn 4. First the primary world's blocks (per_world[primary_world]
              datasets, in the same order as the pair-aware draw), then the
              judge-validation blocks of the other worlds, mixed in one seeded
              order. Primary first protects N if time runs out (study lead).
      round2  turn 4 again, the whole-summary page: n_round2 of the round-1
              primary-world datasets, drawn with their own seeded order.
      round3  turns 6 and 8: n_round3 of the round-1 primary-world datasets,
              drawn with their own seeded order. A block holds 6 summaries, so
              turn 6 and turn 8 stay balanced at any stopping point.

    A dataset is eligible for a round only if every summary its block needs is
    gradeable. Writes scoring/round<r>/summaries/<id>.txt and
    scoring/round<r>/order.csv (position, block, summary_id: no condition, so
    the order file may go to the page builder and to the analysis before
    unblinding). Returns the rows for key/scoring_sets.csv."""
    cells = ("never", f"before_{wording}", f"after_{wording}")
    ids = {(k["run_id"], k["turn"]): k["summary_id"] for k in key}
    matches: dict[tuple, dict[str, str]] = defaultdict(dict)
    for rid, run in runs.items():
        h = run["header"]
        if h["model"] == primary_model and h["condition"] in cells:
            m = (h["world"], h["dataset_seed"], h["replicate"])
            if h["condition"] in matches[m]:
                raise ValueError(f"two {h['condition']} runs for {m}: {matches[m][h['condition']]} and {rid}")
            matches[m][h["condition"]] = rid

    def gradeable_block(m: tuple, turns: tuple) -> bool:
        return all(c in matches[m] and (matches[m][c], t) in ids for c in cells for t in turns)

    def take(pool: list, tag: str, n: int, turns: tuple, label: str) -> list:
        ranked = sorted(pool, key=lambda m: _rank(secret, tag, m))
        got = [m for m in ranked if gradeable_block(m, turns)][:n]
        if len(got) < n:
            print(f"scoring {label}: only {len(got)} datasets eligible (asked for {n})")
        return got

    if primary_world not in per_world:
        raise ValueError(f"per_world must include the primary world {primary_world!r}")
    worlds = {m[0] for m in matches}
    for w in per_world:
        if w not in worlds:
            raise ValueError(f"no {w} runs of {primary_model} in this batch")
    primary = take([m for m in matches if m[0] == primary_world], "draw",
                   per_world[primary_world], (4,), f"round 1, {primary_world}")
    validation = []
    for w in sorted(per_world):
        if w != primary_world:
            validation += take([m for m in matches if m[0] == w], "draw", per_world[w], (4,),
                               f"round 1, {w}")
    validation.sort(key=lambda m: _rank(secret, "round1-validation", m))
    plan = {1: (primary + validation, (4,)),
            2: (take(primary, "round2", n_round2, (4,), "round 2"), (4,)),
            3: (take(primary, "round3", n_round3, (6, 8), "round 3"), (6, 8))}

    rows = []
    for rnd, (blocks, turns) in plan.items():
        out = root / "scoring" / f"round{rnd}"
        (out / "summaries").mkdir(parents=True, exist_ok=True)
        order, pos = [], 0
        for b, m in enumerate(blocks, start=1):
            members = []
            for c in cells:
                rid = matches[m][c]
                for t in turns:
                    members.append((ids[(rid, t)], rid, t))
            for sid, rid, t in sorted(members):      # by ID: carries no condition
                pos += 1
                shutil.copyfile(root / f"T{t}" / "summaries" / f"{sid}.txt",
                                out / "summaries" / f"{sid}.txt")
                order.append({"position": pos, "block": b, "summary_id": sid})
                h = runs[rid]["header"]
                rows.append({"summary_id": sid, "scoring_batch": rnd, "block": b,
                             "position": pos, "turn": t, "run_id": rid,
                             "condition": h["condition"], "world": h["world"],
                             "dataset_seed": h["dataset_seed"], "replicate": h["replicate"]})
        write_csv(out / "order.csv", order)
    return rows


# --------------------------------------------------------------------------
# Per-run statistics and judge inputs
# --------------------------------------------------------------------------
def run_stats(runs: dict, fps: dict, prices: dict) -> list[dict]:
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
        c = cost(prices, h["model"], dict(u))
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
            "cost_own": round(c[0], 6) if c else "", "cost_unit": c[1] if c else "price not set",
            "model_calls_own": sum(r.get("model_calls", 0) for r in own.values()),
            "tool_calls_by_turn": json.dumps({t: len(r.get("tool_calls", []))
                                              for t, r in sorted(run["turns"].items())}),
            "returned_models": json.dumps(sorted({m for r in run["turns"].values()
                                                  for m in r.get("returned_models", [])})),
            "reasoning_returned": "+".join(sorted(k for k in kinds if k)) or "none",
            "max_tokens_sent": h.get("max_tokens_sent", ""),
            "deployment_fingerprints": json.dumps(fps.get(rid, [])),
            **{f"t2_{k}": v for k, v in cross_checks(run, 2).items()},
            **{f"t4_{k}": v for k, v in cross_checks(run, 4).items()},
        })
    return stats


def judge_items(runs: dict, secret: str | None = None) -> list[dict]:
    """Per run x gradeable model turn: what a judge may see. No user messages,
    no condition, no thinking. An After run's turn 2 is its Never run's turn 2
    (same_text_as_run names it).

    With the batch secret, each item also carries its summary ID: the ID the
    human scorers' files use, which names no condition. Judge labels can then
    be joined to human labels before unblinding, without KEY.csv."""
    items = []
    for rid, run in sorted(runs.items()):
        h = run["header"]
        for t in TURNS:
            if not gradeable(run, t):
                continue
            log, truncated = form_a_log(run, t)
            owner = run["turns"][t].get("shared_with") or rid
            items.append({"summary_id": summary_id(secret, t, owner) if secret else None,
                          "run_id": rid, "turn": t, "model": h["model"],
                          "world": h["world"], "dataset_seed": h["dataset_seed"],
                          "summary": clean(run["turns"][t]["text"]),
                          "analysis_log": log, "analysis_log_truncated": truncated,
                          "same_text_as_run": run["turns"][t].get("shared_with"),
                          **cross_checks(run, t)})
    return items


def pilot_report(stats: list[dict]) -> str:
    lines = ["# Pilot report (harness numbers; judge costs are in judging/judge_report.md)", ""]
    by = defaultdict(list)
    for s in stats:
        by[(s["model"], s["world"], s["condition"])].append(s)
    lines += ["| model | world | condition | runs | reached turn 4 | reached turn 8 | "
              "mean own tokens / run | mean output tokens / run | mean cost / run |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for (m, w, c), rows in sorted(by.items()):
        priced = [r for r in rows if r["cost_own"] != ""]
        mean_cost = (f"{statistics.mean(r['cost_own'] for r in priced):,.4f} {priced[0]['cost_unit']}"
                     if priced and len(priced) == len(rows) else "price not set")
        lines.append(f"| {m} | {w} | {c} | {len(rows)} | "
                     f"{sum(r['completed_turn'] >= 4 for r in rows)} | "
                     f"{sum(r['completed_turn'] >= 8 for r in rows)} | "
                     f"{statistics.mean(r['total_tokens_own'] for r in rows):,.0f} | "
                     f"{statistics.mean(r['output_tokens_own'] for r in rows):,.0f} | {mean_cost} |")
    lines += ["", "Own tokens exclude an After run's shared turns 1-2, which are counted once, "
              "on its Never run. Prices come from harness/prices.toml."]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
def _secret(root: Path, replace_ids: bool) -> str:
    """The batch's ID secret: kept across re-exports, made once for a new batch."""
    path = root / "key" / "id_secret.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    if (root / "key" / "KEY.csv").is_file() and not replace_ids:
        raise SystemExit(
            f"{root} was exported before summary IDs were keyed to their runs (it has a "
            f"KEY.csv but no id_secret.txt). Re-exporting would rename every summary, and "
            f"anything already shared under the old names would no longer match. Pass "
            f"--replace-ids only if that is intended.")
    return secrets.token_hex(16)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True)
    ap.add_argument("--logs", default=str(HARNESS_DIR / "logs"),
                    help="Inspect log folder, for deployment fingerprints")
    ap.add_argument("--replace-ids", action="store_true",
                    help="re-export a batch made before keyed IDs, renaming every summary")
    ap.add_argument("--primary-model", default=None,
                    help="model whose summaries humans score; default: the batch's only model")
    ap.add_argument("--scoring-wording", default="B",
                    help="the wording whose Before/After cells humans score (others: judges only)")
    ap.add_argument("--scoring-per-cell", type=int, default=0,
                    help="datasets per world for human scoring; each brings its Never, before and after runs, so pairs stay matched (0 = all)")
    ap.add_argument("--scoring-per-world", default="",
                    help="main-run pages in blocks, e.g. underpowered=60,confounded=10,strong=10: "
                         "writes scoring/round1-3 with order.csv instead of batch1/batch2")
    ap.add_argument("--round2-datasets", type=int, default=7,
                    help="with --scoring-per-world: primary-world datasets on the whole-summary page")
    ap.add_argument("--round3-datasets", type=int, default=20,
                    help="with --scoring-per-world: primary-world datasets on the turns 6 and 8 page")
    ap.add_argument("--primary-world", default="underpowered")
    a = ap.parse_args()
    if a.scoring_per_world and a.scoring_per_cell:
        raise SystemExit("use --scoring-per-world or --scoring-per-cell, not both")

    runs = load_runs(a.batch)
    if not runs:
        raise SystemExit(f"no runs under {RUNS_DIR / a.batch}")
    models = sorted({r["header"]["model"] for r in runs.values()})
    primary = a.primary_model or (models[0] if len(models) == 1 else None)
    if primary is None:
        raise SystemExit(f"several models in the batch; pass --primary-model (one of {models})")
    root = EXPORTS_DIR / a.batch
    secret = _secret(root, a.replace_ids)
    for name in EXPORT_OWNED:   # regenerated whole; judging/ belongs to the judge runner
        shutil.rmtree(root / name, ignore_errors=True)
    (root / "key").mkdir(parents=True)
    (root / "key" / "id_secret.txt").write_text(secret + "\n", encoding="utf-8")

    key = write_turn_folders(runs, root, secret)
    write_csv(root / "key" / "KEY.csv", key)
    if a.scoring_per_world:
        try:
            per_world = {w.strip(): int(n) for w, n in
                         (x.split("=") for x in a.scoring_per_world.split(","))}
        except ValueError:
            raise SystemExit("--scoring-per-world: world=N pairs separated by commas")
        scoring = write_scoring_rounds(runs, key, root, secret, primary, a.scoring_wording,
                                       per_world, a.round2_datasets, a.round3_datasets,
                                       a.primary_world)
    else:
        scoring = write_scoring_sets(runs, key, root, secret, primary, a.scoring_wording,
                                     a.scoring_per_cell)
    write_csv(root / "key" / "scoring_sets.csv", scoring)
    stats = run_stats(runs, fingerprints(Path(a.logs), set(runs)), load_prices())
    write_csv(root / "key" / "run_stats.csv", stats)
    write_csv(root / "key" / "analysis_estimates.csv",
              [{"run_id": rid, "world": run["header"]["world"],
                "dataset_seed": run["header"]["dataset_seed"], **row}
               for rid, run in sorted(runs.items()) for row in per_turn(run)])
    (root / "key" / "pilot_report.md").write_text(pilot_report(stats), encoding="utf-8")
    judge = judge_items(runs, secret)
    (root / "judges").mkdir()
    with (root / "judges" / "judge_items.jsonl").open("w", encoding="utf-8") as f:
        for row in judge:
            f.write(json.dumps(row) + "\n")
    per_turn_ids = {t: len({k["summary_id"] for k in key if k["turn"] == t}) for t in TURNS}
    (root / "key" / "manifest.json").write_text(json.dumps({
        "batch": a.batch,
        "exported_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "summary_ids": "HMAC-SHA256(key/id_secret.txt, 'T<turn>|<run_id>')[:10]",
        "models": models, "primary_model": primary,
        "human_scoring": {"cells": ["never", f"before_{a.scoring_wording}",
                                    f"after_{a.scoring_wording}"],
                          "per_cell": a.scoring_per_cell or "all",
                          "per_world": a.scoring_per_world or None,
                          "round2_datasets": a.round2_datasets if a.scoring_per_world else None,
                          "round3_datasets": a.round3_datasets if a.scoring_per_world else None,
                          "batch1_summaries": sum(r["scoring_batch"] == 1 for r in scoring),
                          "batch2_summaries": sum(r["scoring_batch"] == 2 for r in scoring),
                          "batch3_summaries": sum(r["scoring_batch"] == 3 for r in scoring)},
        "runs": len(runs), "summaries_per_turn": per_turn_ids,
        # What the runs were sent, so the wording can be checked without the run logs.
        "board_sentence_included": sorted({bool(r["header"].get("board_sentence_included"))
                                           for r in runs.values()}),
        "prompts_version": sorted({str(r["header"].get("prompts_version")) for r in runs.values()}),
        "prompts_sha256": sorted({str(r["header"].get("prompts_sha256")) for r in runs.values()}),
        "judge_items": len(judge), "judge_log_cap_chars": JUDGE_LOG_CAP,
        "judge_log_keep_per_call_chars": CALL_OUTPUT_KEEP}, indent=1), encoding="utf-8")
    print(f"{len(runs)} runs -> {sum(per_turn_ids.values())} summaries "
          f"({', '.join(f'T{t}: {n}' for t, n in per_turn_ids.items())}), "
          f"{len(judge)} judge items; human scoring: "
          f"{sum(r['scoring_batch'] == 1 for r in scoring)} in batch 1, "
          f"{sum(r['scoring_batch'] == 2 for r in scoring)} in batch 2\nwritten to {root}")


if __name__ == "__main__":
    main()
