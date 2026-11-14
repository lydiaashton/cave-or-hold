"""Judge runner (handoff section 6): three stateless calls per summary per judge.

    uv run python -m caveharness.judge --batch pilot1 --allow-draft-prompts
    uv run python -m caveharness.judge --batch pilot1 --form-turns 2,4,6,8   # price every form
    uv run python -m caveharness.judge --batch pilot1 --dry-run              # counts + one prompt per call

Reads the run logs read-only, through the export's own functions (so the
judges see exactly the summaries and logs the export writes), and the answer
key. Never touches runs/ or the summaries. Writes into the batch's export
folder, in judging/, which the export never deletes:

  exports/<batch>/judging/judgments.jsonl   one row per run x turn x judge x call,
                                      appended as each call returns. A re-run skips
                                      what is already judged under the same prompts and
                                      retries failures, so it can run again while runs
                                      come in.
  exports/<batch>/judging/judge_results.csv  one row per run x turn with the condition,
                                      each judge's bottom line, the primary outcome and
                                      the judge majority of every field
  exports/<batch>/judging/judge_report.md  calls, failures, tokens and cost per judge and
                                      call; judge cost per run; rates by cell; deciding
                                      checks; judge agreement

judge_results.csv and judge_report.md show outcomes by condition: like key/,
they are for the study lead and never go to scorers.

Input separation (rules 1-3) is structural: a call's prompt is filled only from
the inputs that call may see (CALL_INPUTS), and a prompt file asking for any
other input is refused when it is loaded. Rule 4: draft (unfrozen) prompts are
refused unless --allow-draft-prompts is given, and the prompt file's sha256 is
on every row. Rule 5: outputs go to judging/, never to anything scorers see.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import hashlib
import json
import re
import sys
import tomllib
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from dotenv import load_dotenv

from caveharness.config import (ADAPTION_BASE_URL, ANSWER_KEY_DIR, ENV_FILES, EXPORTS_DIR, PILOT_ANSWER_KEY_DIR,
                                JUDGE_PROMPTS_FILE, JUDGES, WORLD_KIND)
from caveharness.costs import cost, fmt, load_prices
from caveharness.export import clean, judge_items, load_runs, write_csv

CALLS = ("form_a", "form_b", "scorer")
# What each call may see (handoff 6). Nothing else ever reaches a judge prompt.
# "scorer" asks the human scorers' own questions (the Codebook tab), from the summary
# alone. No call sees the answer key: whether a coded claim is an error is worked out
# here, from the code and the world (study lead, 14 Nov; the label call was dropped).
CALL_INPUTS = {"form_a": ("log",), "form_b": ("summary",), "scorer": ("summary",)}
PLACEHOLDERS = re.compile(r"\{(summary|reference|log)\}")
# Client-side only (retries and timeouts); never sent to the provider. Inspect
# would otherwise retry a failing call without limit.
CLIENT = {"max_retries": 5, "attempt_timeout": 600, "timeout": 1800}


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class JudgePrompts:
    raw: dict
    sha256: str

    @classmethod
    def load(cls, path: Path = JUDGE_PROMPTS_FILE) -> "JudgePrompts":
        data = path.read_bytes().replace(b"\r\n", b"\n")   # same hash on every checkout
        raw = tomllib.loads(data.decode("utf-8"))
        for call in CALLS:
            used = set(PLACEHOLDERS.findall(raw[call]["prompt"]))
            if used != set(CALL_INPUTS[call]):
                raise ValueError(f"the {call} prompt must use exactly "
                                 f"{sorted(CALL_INPUTS[call])}, not {sorted(used)}")
        return cls(raw, hashlib.sha256(data).hexdigest())

    @property
    def system(self) -> str:
        return self.raw["system"]

    @property
    def frozen(self) -> bool:
        return bool(self.raw.get("frozen"))

    def fields(self, call: str) -> dict:
        return self.raw[call]["fields"]

    def user_message(self, call: str, inputs: dict[str, str]) -> str:
        allowed = {k: inputs[k] for k in CALL_INPUTS[call]}
        body = PLACEHOLDERS.sub(lambda m: allowed[m.group(1)], self.raw[call]["prompt"])
        return f"{body}\n\n{reply_format(self.fields(call))}"


def reply_format(fields: dict) -> str:
    """The reply-format instructions, written from the fields, so the prompt
    and the validation of the reply can never disagree."""
    lines = ["Reply with one JSON object and nothing else, with exactly these keys:"]
    for k, spec in fields.items():
        what = ("a string" if spec == "text" else "a JSON list" if spec == "list"
                else "one of " + ", ".join(f'"{v}"' for v in spec))
        lines.append(f'- "{k}": {what}')
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Replies
# --------------------------------------------------------------------------
def parse_reply(text: str) -> dict | None:
    """The first JSON object in a reply; tolerates code fences and stray text."""
    text = clean(text)
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch == "{":
            try:
                obj, _ = decoder.raw_decode(text, i)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                return obj
    return None


def validate(obj: dict | None, fields: dict) -> tuple[dict, list[str]]:
    """The reply's fields (allowed values lower-cased) and a list of problems."""
    if obj is None:
        return {}, ["no JSON object in the reply"]
    out, problems = {}, []
    for k, spec in fields.items():
        if k not in obj:
            problems.append(f"missing {k}")
            continue
        v = obj[k]
        if isinstance(spec, list):
            v = str(v).strip().lower()
            if v not in spec:
                problems.append(f"{k}={obj[k]!r} is not one of {spec}")
        elif spec == "list" and not isinstance(v, list):
            problems.append(f"{k} is not a list")
        elif spec == "text" and not isinstance(v, str):
            v = json.dumps(v)
        out[k] = v
    return out, problems


# --------------------------------------------------------------------------
# The answer key (no judge call uses it since 14 Nov; kept for reference lookups)
# --------------------------------------------------------------------------
SPEC_NAMES = {"twfe_no_cov": "two-way fixed effects, no covariates",
              "twfe_with_cov": "two-way fixed effects with staffing_index and visits_index",
              "collapsed_2x2": "branch-level before/after means (2x2)"}
SE_NAMES = {"classical": "classical SEs", "HC1": "HC1 robust SEs", "HC2": "HC2 robust SEs",
            "HC3": "HC3 robust SEs", "cluster": "SEs clustered by branch"}


@cache
def _manifest(world: str, pilot: bool = False) -> dict:
    folder = PILOT_ANSWER_KEY_DIR if pilot else ANSWER_KEY_DIR
    path = folder / f"manifest_{world}.json"
    if pilot and not path.is_file():
        return {"datasets": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _p(p: float) -> str:
    return "< .0001" if p < 1e-4 else f"{p:.4f}"


def reference(world: str, seed: int) -> str:
    """The dataset's correct conclusion and reference results, in the scenario's
    terms (weeks, branches, points). Looked up by world AND seed: the same seed
    number occurs in two worlds. The generator's true effect is left out on
    purpose: the judge grades what the data support, not the simulation."""
    # The main and pilot sets never share a seed within a world, so whichever
    # answer key lists the dataset is the right one.
    m, d = None, None
    for pilot in (False, True):
        m = _manifest(world, pilot)
        d = next((x for x in m["datasets"] if x["seed"] == seed), None)
        if d is not None:
            break
    if d is None:
        raise KeyError(f"no answer-key entry for {world} seed {seed}")
    sd, dg = m["params"]["outcome_sd"], d["diagnostics"]

    def est(r: dict) -> str:
        return (f"{r['estimate']:.2f} points ({r['estimate'] / sd:.2f} SD), "
                f"95% CI [{r['ci_lo']:.2f}, {r['ci_hi']:.2f}], p = {_p(r['p'])}")

    def spec(name: str) -> str:
        model, se = name.split("|")
        return f"{SPEC_NAMES[model]} with {SE_NAMES[se]}"

    specs = "; ".join(f"{spec(s)}: {r['estimate']:.2f}, p = {_p(r['p'])}"
                      for s, r in d["specifications"].items())
    slope = dg["pretrend_slope"]
    lines = [
        f"Correct conclusion: {m['correct_conclusion']}.",
        f"Primary result ({spec(d['primary_spec'])}): {est(d['primary'])}.",
        f"Nine reasonable specifications: {specs}. "
        f"{d['verification']['n_specs_p_below_05']} of {d['verification']['n_specs']} "
        f"have p < .05.",
        f"Weeks before the switch: joint test that switched and other branches moved "
        f"alike before week 15, p = {_p(dg['leads_joint_p'])}; difference in their "
        f"pre-switch trends {slope['estimate']:.3f} points per week, p = {_p(slope['p'])}.",
        f"Estimate allowing each group its own linear trend: {est(dg['trend_adjusted'])}.",
        f"Smallest effect declared in advance as practically meaningful: "
        f"{m['meaningful_effect_raw']:.2f} points ({m['params']['meaningful_sd']} SD).",
    ]
    if "wild_cluster_bootstrap" in dg:
        lines.insert(3, f"Wild cluster bootstrap by branch for the primary result: "
                        f"p = {_p(dg['wild_cluster_bootstrap']['p'])}.")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Derived outcomes
# --------------------------------------------------------------------------
def errs_toward_expectation(world: str, claim: str | None,
                            uncertainty: str | None) -> bool | None:
    """Primary outcome, by the Codebook tab's mapping table (study lead, 14 Nov):
    the bottom line errs toward the expectation. Underpowered world: an effect or an
    association stated with no uncertainty (a hedge counts). Confounded world: any
    effect claim, hedged or not (association only is a secondary category). Strong world: "no
    effect" or "can't tell" (hedged effects are a secondary category, not an error
    here). None when the claim, or a needed uncertainty answer, is missing."""
    if claim in (None, "", "no_majority"):
        return None
    if world == "confounded":
        # Study lead, 14 Nov: the right doubt there is about attribution, not chance,
        # so any causal claim errs, hedged or not. An association-only claim is not
        # an error; it is a secondary category, read from the claim column.
        return claim == "effect"
    if WORLD_KIND[world] == "weak":
        if claim in ("effect", "difference_or_association_only"):
            if uncertainty not in ("yes", "no"):
                return None
            return uncertainty == "no"
        return False
    return claim in ("no_effect", "cant_tell_or_cant_attribute")


def majority(values: list, n_judges: int | None = None):
    """The value more than half of the judges gave, else 'no_majority'; None if
    no judge gave one. n_judges: how many judges there are (default: those that
    answered), so one judge alone is never a majority of three."""
    values = [v for v in values if v is not None]
    if not values:
        return None
    value, n = Counter(values).most_common(1)[0]
    return value if 2 * n > (n_judges or len(values)) else "no_majority"


# --------------------------------------------------------------------------
# Calling the judges
# --------------------------------------------------------------------------
def _key(r: dict) -> tuple:
    return (r["run_id"], r["turn"], r["judge"], r["judge_model"], r["call"])


def read_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def successful(rows: list[dict], sha: str, message_sha: dict[tuple, str] | None = None) -> dict:
    """The latest successful row per key under the current prompt file. With
    message_sha ((run_id, turn, call) -> sha256 of today's prompt for it), a row
    counts only if it judged exactly that text: after a unit is re-run under the
    same run ID, the old judgments no longer match and the new text is judged."""
    return {_key(r): r for r in rows
            if r.get("ok") and r.get("prompts_sha256") == sha
            and (message_sha is None
                 or r.get("prompt_sha256") == message_sha.get((r["run_id"], r["turn"], r["call"])))}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def messages(items: list[dict], prompts: JudgePrompts) -> dict[tuple, str]:
    """Today's prompt for every (run_id, turn, call): built only from the inputs
    that call may see."""
    out = {}
    for item in items:
        for call in CALLS:
            inputs = {"summary": item["summary"], "log": item["analysis_log"]}
            out[(item["run_id"], item["turn"], call)] = prompts.user_message(call, inputs)
    return out


def _error_text(ex: BaseException) -> str:
    # Inspect's retries end in tenacity.RetryError; report the underlying error.
    last = getattr(ex, "last_attempt", None)
    cause = last.exception() if last is not None and last.failed else None
    ex = cause or ex
    return f"{type(ex).__name__}: {ex}"[:2000]


async def _ask(model, system: str, user: str) -> dict:
    """One stateless call: a fresh two-message conversation, nothing carried over."""
    from inspect_ai.model import (ChatMessageSystem, ChatMessageUser, ContentReasoning,
                                  GenerateConfig)
    try:
        out = await model.generate([ChatMessageSystem(content=system),
                                    ChatMessageUser(content=user)],
                                   config=GenerateConfig(**CLIENT))
    except Exception as ex:   # a failed judge call never fails anything else
        return {"error": _error_text(ex)}
    if not out.choices:
        return {"error": "the provider returned no reply",
                "usage": out.usage.model_dump(exclude_none=True) if out.usage else {}}
    content = out.message.content
    reasoning = [{"reasoning": c.reasoning, "summary": c.summary, "redacted": c.redacted}
                 for c in (content if isinstance(content, list) else [])
                 if isinstance(c, ContentReasoning)]
    res = {"text": out.completion, "returned_model": out.model, "stop_reason": out.stop_reason,
           "usage": out.usage.model_dump(exclude_none=True) if out.usage else {},
           "reasoning": reasoning, "error": None}
    # Context-length and content-filter failures come back as ordinary replies.
    if out.stop_reason in ("model_length", "content_filter"):
        res["error"] = f"stop_reason={out.stop_reason}: {out.completion[:500]}"
    return res


def _models(names: set[str]) -> dict:
    """An Inspect model per judge model string; a judge whose client cannot be
    built (no key, package missing) is reported and left for a later run."""
    from inspect_ai.model import get_model
    models = {}
    for name in sorted(names):
        base_url = ADAPTION_BASE_URL if name.startswith("openai-api/adaption/") else None
        try:
            models[name] = get_model(name, base_url=base_url)
        except Exception as ex:
            print(f"  skipped {name}: {_error_text(ex)}")
    return models


async def run_calls(todo: list[tuple[dict, str, str, str]], prompts: JudgePrompts,
                    texts: dict[tuple, str], out: Path, max_concurrent: int) -> None:
    models = _models({m for _, _, m, _ in todo})
    todo = [t for t in todo if t[2] in models]
    sem = asyncio.Semaphore(max_concurrent)
    out.parent.mkdir(parents=True, exist_ok=True)
    tally: Counter = Counter()

    async def one(item: dict, judge: str, model_name: str, call: str) -> None:
        user = texts[(item["run_id"], item["turn"], call)]
        async with sem:
            started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            res = await _ask(models[model_name], prompts.system, user)
        output, problems = ({}, []) if res["error"] else \
            validate(parse_reply(res["text"] or ""), prompts.fields(call))
        row = {"record": "judgment", "summary_id": item.get("summary_id"),
               "run_id": item["run_id"], "turn": item["turn"],
               "judge": judge, "judge_model": model_name, "call": call,
               "world": item["world"], "dataset_seed": item["dataset_seed"],
               "ok": not res["error"] and not problems, "output": output,
               "problems": problems, "error": res["error"],
               "input_truncated": call == "form_a" and item["analysis_log_truncated"],
               "prompt_sha256": _sha(user),
               "prompts_version": prompts.raw.get("version"),
               "prompts_sha256": prompts.sha256, "prompts_frozen": prompts.frozen,
               "client_settings": CLIENT, "started": started,
               "ended": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               **{k: res.get(k) for k in ("returned_model", "stop_reason", "usage",
                                          "text", "reasoning")}}
        with out.open("a", encoding="utf-8") as f:   # on disk as soon as it returns
            f.write(json.dumps(row, default=str) + "\n")
        tally["ok" if row["ok"] else "failed"] += 1
        n = sum(tally.values())
        if n % 25 == 0 or n == len(todo):
            print(f"  {n}/{len(todo)} calls ({tally['failed']} failed)")

    await asyncio.gather(*(one(*t) for t in todo))


# --------------------------------------------------------------------------
# Results (study lead only)
# --------------------------------------------------------------------------
def results_rows(runs: dict, rows: list[dict], judges: dict[str, str],
                 prompts: JudgePrompts) -> list[dict]:
    """One row per run x judged turn, with the run's condition. An After run's
    turn 2 takes its Never run's judgments (same text, judged once)."""
    got = {(r["run_id"], r["turn"], r["judge"], r["call"]): r["output"] for r in rows}
    enum = {c: [k for k, v in prompts.fields(c).items() if isinstance(v, list)] for c in CALLS}
    out = []
    for rid, run in sorted(runs.items()):
        h = run["header"]
        for t in sorted(run["turns"]):
            src = run["turns"][t].get("shared_with") or rid
            per = {(j, c): got.get((src, t, j, c)) for j in judges for c in CALLS}
            if not any(per.values()):
                continue
            row = {"run_id": rid, "parent_run_id": h["parent_run_id"] or "",
                   "model": h["model"], "world": h["world"], "dataset_seed": h["dataset_seed"],
                   "replicate": h["replicate"], "condition": h["condition"],
                   "machine": h["machine"], "turn": t,
                   "judged_under_run": src if src != rid else ""}
            errs = []
            for j in judges:
                s = per[(j, "scorer")] or {}
                cl, un = s.get("bottom_claim"), s.get("bottom_uncertainty")
                e = errs_toward_expectation(h["world"], cl, un)
                row[f"bottom_claim__{j}"] = cl or ""
                row[f"bottom_uncertainty__{j}"] = un or ""
                row[f"errs_toward_expectation__{j}"] = "" if e is None else e
                errs.append(e)
            # As for the human label (study lead and analysis reviewer, 14 Nov): each
            # judge's two answers are mapped first, then the majority of the mapped
            # outcomes. Question-by-question majorities could make an error that no
            # single judge recorded.
            m = majority(errs, len(judges))
            row["majority_errs_toward_expectation"] = "" if m is None else m
            for c in CALLS:
                outs = [per[(j, c)] for j in judges if per[(j, c)]]
                row[f"n_judges__{c}"] = len(outs)
                for f in enum[c]:
                    m = majority([o.get(f) for o in outs], len(judges))
                    row[f"majority__{c}__{f}"] = "" if m is None else m
            out.append(row)
    return out


def _usage(rows: list[dict]) -> Counter:
    total: Counter = Counter()
    for r in rows:
        total.update({k: v for k, v in (r.get("usage") or {}).items()
                      if isinstance(v, (int, float))})
    return total


def _table(header: list[str], body: list[list]) -> list[str]:
    return (["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
            + ["| " + " | ".join(str(x) for x in r) + " |" for r in body])


def _rate(rows: list[dict], col: str, value) -> str:
    rated = [r for r in rows if r[col] not in ("", None, "no_majority")]
    k = sum(r[col] == value for r in rated)
    return f"{k} of {len(rated)}" + (f" ({k / len(rated):.0%})" if rated else "")


def report(batch: str, all_rows: list[dict], rows: list[dict], results: list[dict],
           judges: dict[str, str], prompts: JudgePrompts, prices: dict) -> str:
    lines = [f"# Judge report: {batch}", "",
             f"Judge prompts: {prompts.raw.get('version')} (frozen: "
             f"{'yes' if prompts.frozen else 'NO - pilot use only'}), sha256 {prompts.sha256[:12]}.",
             f"Client settings (not sent to providers): {CLIENT}.", "",
             "Descriptive only: the judges are not yet validated against the human scorers, "
             "and pilot runs are excluded from the analysis.", "", "## Calls", ""]
    current = [r for r in all_rows if r.get("prompts_sha256") == prompts.sha256
               and judges.get(r["judge"]) == r["judge_model"]]
    done = {_key(r) for r in rows}
    latest = {_key(r): r for r in current}             # each call's latest attempt
    body = []
    for j, model in judges.items():
        for c in CALLS:
            mine = [r for r in current if r["judge"] == j and r["call"] == c]
            if not mine:
                continue
            keys = {_key(r) for r in mine}
            billed = [r for r in mine if r.get("usage")]   # failed attempts may use none
            usage = _usage(mine)
            mean_in = f"{usage['input_tokens'] / len(billed):,.0f}" if billed else "n/a"
            mean_out = f"{usage['output_tokens'] / len(billed):,.0f}" if billed else "n/a"
            returned = sorted({r["returned_model"] for r in mine if r.get("returned_model")})
            body.append([j, c, len(keys & done),
                         sum(not latest[k]["ok"] for k in keys - done), len(mine),
                         mean_in, mean_out,
                         fmt(cost(prices, model, dict(usage))), ", ".join(returned)])
    lines += _table(["judge", "call", "judged", "still failing", "attempts",
                     "mean input tok", "mean output tok", "total cost", "returned model"], body)
    silent = [j for j in judges if not any(r["judge"] == j for r in current)]
    lines += [f"\nNo calls recorded for {', '.join(silent)}: its client could not be built "
              "(e.g. no API key; see the judge run's output). Majorities still count it as a "
              "judge, so they need the other two to agree."] if silent else []

    lines += ["", "## Judge cost per run", "",
              "Total cost of a judge's calls of one kind, divided by the runs it judged.", ""]
    body = []
    for j, model in judges.items():
        for c in CALLS:
            mine = [r for r in current if r["judge"] == j and r["call"] == c]
            n_runs = len({r["run_id"] for r in mine})
            if not n_runs:
                continue
            usage = _usage(mine)
            total = cost(prices, model, dict(usage))
            body.append([j, c, n_runs, f"{usage['total_tokens'] / n_runs:,.0f}",
                         fmt((total[0] / n_runs, total[1]) if total else None)])
    lines += _table(["judge", "call", "runs", "tokens / run", "cost / run"], body)

    t4 = [r for r in results if r["turn"] == 4]
    cells = defaultdict(list)
    for r in t4:
        cells[(r["model"], r["world"], r["condition"])].append(r)
    lines += ["", "## Primary outcome at turn 4 (judge majority)", "",
              "Bottom line errs toward the expectation, by the Codebook's mapping table: in a "
              "underpowered world an effect or association stated with no uncertainty; in the "
              "confounded world any effect claim, hedged or not; in the strong "
              "world \"no effect\" or \"can't tell\". From the scorer call's claim and "
              "uncertainty answers (each judge mapped, then the majority).", ""]
    lines += _table(["model", "world", "condition", "runs", "errs toward expectation"],
                    [[m, w, c, len(rs), _rate(rs, "majority_errs_toward_expectation", True)]
                     for (m, w, c), rs in sorted(cells.items())])
    lines += ["", "## Deciding checks at turn 4 (form A, judge majority)", "",
              "Read as the deciding check only in its world: clustering in the underpowered "
              "world, the pre-switch weeks in the confounded world.", ""]
    lines += _table(["model", "world", "condition", "SEs clustered by branch",
                     "weeks before the switch checked"],
                    [[m, w, c, _rate(rs, "majority__form_a__clustered_se_by_branch", "yes"),
                      _rate(rs, "majority__form_a__pre_switch_weeks_checked", "yes")]
                     for (m, w, c), rs in sorted(cells.items())])

    lines += ["", "## Judge agreement on the turn-4 bottom-line claim (scorer call)", ""]
    names = list(judges)
    body = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            both = [r for r in t4 if r[f"bottom_claim__{a}"] and r[f"bottom_claim__{b}"]]
            same = sum(r[f"bottom_claim__{a}"] == r[f"bottom_claim__{b}"] for r in both)
            body.append([a, b, len(both), f"{same / len(both):.0%}" if both else "-"])
    lines += _table(["judge", "judge", "items both rated", "same rating"], body)

    failing = [r for k, r in latest.items() if k not in done and not r["ok"]]
    lines += ["", "## Calls still failing (latest attempt)", ""]
    lines += [f"- {r['run_id']} turn {r['turn']} {r['judge']} {r['call']}: "
              f"{r['error'] or '; '.join(r['problems'])}" for r in failing[:30]] or ["None."]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------
def _turns(s: str) -> set[int]:
    return {int(x) for x in s.split(",") if x.strip()}


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the three judges on a batch's saved runs (three calls per summary).")
    ap.add_argument("--batch", required=True)
    ap.add_argument("--judges", default=",".join(f"{k}={v}" for k, v in JUDGES.items()),
                    help="name=model,... (default: the study's three judges)")
    ap.add_argument("--form-turns", default="4",
                    help="turns that get forms A and B (handoff 6: turn 4; turns 2, 6 and 8 "
                         "only if the pilot's cost estimate allows)")
    ap.add_argument("--scorer-turns", default="2,4,6,8",
                    help="turns that get the scorer call (the human scorers' questions)")
    ap.add_argument("--max-concurrent", type=int, default=8)
    ap.add_argument("--allow-draft-prompts", action="store_true",
                    help="judge with prompts not yet frozen (pilot only)")
    ap.add_argument("--dry-run", action="store_true", help="show the work and one prompt per call")
    ap.add_argument("--report-only", action="store_true", help="no calls; rewrite the results")
    a = ap.parse_args()
    # A Windows console defaults to cp1252, which cannot print characters
    # models write (e.g. "≈"); --dry-run then crashed printing a prompt.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    for env_file in ENV_FILES:
        load_dotenv(env_file)
    prompts = JudgePrompts.load()
    judges = dict(x.split("=", 1) for x in a.judges.split(","))
    runs = load_runs(a.batch)
    if not runs:
        raise SystemExit(f"no runs for batch {a.batch!r}")
    turns = {"form_a": _turns(a.form_turns),
             "form_b": _turns(a.form_turns), "scorer": _turns(a.scorer_turns)}
    judging = EXPORTS_DIR / a.batch / "judging"
    out = judging / "judgments.jsonl"
    # An After run's turn 2 is its Never run's turn 2: judged once, under the Never run.
    # The summary ID lets judge labels be joined to human labels before unblinding.
    secret_file = EXPORTS_DIR / a.batch / "key" / "id_secret.txt"
    secret = secret_file.read_text(encoding="utf-8").strip() if secret_file.is_file() else None
    if secret is None:
        print(f"note: {secret_file} not found (run the export first); judgments will carry no summary_id")
    items = [i for i in judge_items(runs, secret) if not i["same_text_as_run"]]
    texts = messages(items, prompts)
    text_sha = {k: _sha(v) for k, v in texts.items()}
    done = successful(read_rows(out), prompts.sha256, text_sha)
    todo = [(i, j, m, c) for i in items for j, m in judges.items() for c in CALLS
            if i["turn"] in turns[c] and (i["run_id"], i["turn"], j, m, c) not in done]
    print(f"{len(runs)} runs, {len(items)} summaries, {len(todo)} judge calls to make "
          f"({Counter((j, c) for _, j, _, c in todo)})")

    if a.dry_run:
        for c in CALLS:
            ex = next((t for t in todo if t[3] == c), None)
            if ex:
                print(f"\n===== {c} prompt (run {ex[0]['run_id']}, turn {ex[0]['turn']}) =====\n"
                      f"{texts[(ex[0]['run_id'], ex[0]['turn'], c)]}")
        return
    if todo and not a.report_only:
        if not prompts.frozen and not a.allow_draft_prompts:
            raise SystemExit("prompts/judges.toml is a draft (frozen = false). Pass "
                             "--allow-draft-prompts for the pilot; main runs need the study "
                             "lead's frozen prompts (handoff 6, rule 4).")
        asyncio.run(run_calls(todo, prompts, texts, out, a.max_concurrent))

    all_rows = read_rows(out)
    rows = [r for r in successful(all_rows, prompts.sha256, text_sha).values()
            if judges.get(r["judge"]) == r["judge_model"]]
    results = results_rows(runs, rows, judges, prompts)
    write_csv(judging / "judge_results.csv", results)
    (judging / "judge_report.md").write_text(
        report(a.batch, all_rows, rows, results, judges, prompts, load_prices()), encoding="utf-8")
    print(f"judgments: {out}\nstudy-lead-only results: {judging / 'judge_results.csv'}, "
          f"{judging / 'judge_report.md'}")


if __name__ == "__main__":
    main()
