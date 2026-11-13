"""The Inspect task: eight turns per run, Never -> After branching, sandbox restore.

Run with, for example:
    uv run inspect eval src/caveharness/task.py@cave_or_hold \
        --model openai-api/adaption/qwen3.5-397b \
        --model-base-url https://api.prod.adaptionlabs.ai/api/v1 \
        -T worlds=underpowered,confounded -T runs_per_cell=5 -T batch=pilot1

Every model turn is appended to runs/<batch>/<machine>/<run_id>.jsonl the moment
it finishes, so turn 4 is on disk before turn 5 is sent (handoff section 1).
The Inspect .eval log keeps the full transcript as well.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import socket
import subprocess
from pathlib import Path

import inspect_ai
from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import (ChatMessageAssistant, ChatMessageSystem,
                              ChatMessageTool, ChatMessageUser,
                              ContentReasoning, GenerateConfig, ModelUsage,
                              get_model)
from inspect_ai.solver import Generate, TaskState, solver
from inspect_ai.tool import tool
from inspect_ai.util import OutputLimitExceededError, sandbox, store

from caveharness import plan as planmod
from caveharness.config import HARNESS_DIR, RUNS_DIR
from caveharness.prompts import Prompts

TOOL_NAME = "python"
TOOL_DESCRIPTION = ("Run Python code in the working directory and return what it "
                    "printed. Each call starts a new Python process. Files written "
                    "to the working directory are kept between calls.")
COMPOSE = HARNESS_DIR / "sandbox" / "compose.yaml"
TOOL_OUTPUT_CAP = 20_000              # characters the model is shown per tool call
INSPECT_MAX_TOOL_OUTPUT = 10_000_000  # bytes; keeps Inspect's own truncation out of the way
TASK_CONFIG = GenerateConfig(max_tool_output=INSPECT_MAX_TOOL_OUTPUT)
# Adaption's address is passed with --model-base-url (see README). Setting it
# from this module does not work: Inspect builds the model client before it
# imports the task file (checked 13 Nov).


# --------------------------------------------------------------------------
# The code-execution tool
# --------------------------------------------------------------------------
@tool(name=TOOL_NAME)
def python_tool(timeout: int = 180, max_output: int = TOOL_OUTPUT_CAP):
    async def execute(code: str) -> str:
        """Run Python code in the working directory and return what it printed. Each call starts a new Python process. Files written to the working directory are kept between calls.

        Args:
            code: The Python code to run.
        """
        try:
            r = await sandbox().exec(["python", "-"], input=code, timeout=timeout)
        except (TimeoutError, OutputLimitExceededError) as ex:
            # TimeoutError: Inspect can also signal a timeout by raising.
            # OutputLimitExceededError: over Inspect's 10 MiB exec limit.
            # Answer in our own words rather than letting Inspect's text reach
            # the model, and log the call like any other.
            msg = (f"Error: the code did not finish within {timeout} seconds."
                   if isinstance(ex, TimeoutError)
                   else "Error: the code printed too much output to return.")
            full = store().get("full_outputs", [])
            full.append({"code": code, "output": msg, "returncode": type(ex).__name__,
                         "truncated": False})
            store().set("full_outputs", full)
            return msg
        out = r.stdout
        if r.stderr:
            out = f"{out}\n{r.stderr}" if out else r.stderr
        # In Docker, Inspect enforces the timeout inside the container and
        # returns exit code 124 instead of raising, so the exit code is the
        # only signal that the code was stopped. Without this a timed-out or
        # killed process reached the model as "(no output)".
        if r.returncode == 124:
            out = f"{out}\nError: the code did not finish within {timeout} seconds." if out.strip() \
                else f"Error: the code did not finish within {timeout} seconds."
        elif r.returncode == 137:
            out = f"{out}\nError: the process was stopped." if out.strip() \
                else "Error: the process was stopped."
        # The log keeps everything the code printed (handoff section 5); the
        # model is shown at most max_output characters.
        full = store().get("full_outputs", [])
        full.append({"code": code, "output": out, "returncode": r.returncode,
                     "truncated": len(out) > max_output})
        store().set("full_outputs", full)
        if len(out) > max_output:
            out = out[:max_output] + f"\n[output truncated at {max_output} characters]"
        return out if out.strip() else "(no output)"
    return execute


# --------------------------------------------------------------------------
# Sandbox file listing, snapshot and restore
# --------------------------------------------------------------------------
_LIST = ("import os,json;print(json.dumps(sorted([[os.path.relpath(os.path.join(r,f)),"
         "os.path.getsize(os.path.join(r,f)),os.path.getmtime(os.path.join(r,f))]"
         " for r,_,fs in os.walk('.') for f in fs])))")
_CLEAR = ("import os,shutil\nfor p in os.listdir('.'):\n"
          "    shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)")


async def _files() -> dict[str, tuple[int, float]]:
    r = await sandbox().exec(["python", "-c", _LIST])
    return {p: (s, m) for p, s, m in json.loads(r.stdout or "[]")}


async def _snapshot() -> dict[str, bytes]:
    return {p: await sandbox().read_file(p, text=False) for p in await _files()}


async def _restore(snap: dict[str, bytes]) -> None:
    await sandbox().exec(["python", "-c", _CLEAR])
    for p, data in snap.items():
        await sandbox().write_file(p, data)


# --------------------------------------------------------------------------
# Per-run record, written to disk turn by turn
# --------------------------------------------------------------------------
def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=HARNESS_DIR,
                              capture_output=True, text=True, timeout=10).stdout.strip() or None
    except Exception:
        return None


class RunLog:
    def __init__(self, path: Path, header: dict):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            # Re-running a batch must never silently destroy an earlier log.
            # The backup's name does not end in .jsonl, so the export skips it.
            stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
            path.rename(path.with_name(f"{path.name}.prev-{stamp}"))
        path.write_text("", encoding="utf-8")
        self.write({"record": "header", **header})

    def write(self, rec: dict) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
            f.flush()


def _usage_dict(u: ModelUsage | None) -> dict:
    return u.model_dump(exclude_none=True) if u else {}


def _add_usage(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, (int, float)):
            out[k] = out.get(k, 0) + v
    return out


def _reasoning(m: ChatMessageAssistant) -> list[dict]:
    if isinstance(m.content, str):
        return []
    return [{"reasoning": c.reasoning, "summary": getattr(c, "summary", None),
             "redacted": c.redacted, "has_signature": bool(c.signature)}
            for c in m.content if isinstance(c, ContentReasoning)]


async def _model_turn(state: TaskState, generate: Generate, log: RunLog,
                      user_turn: int, text: str, max_rounds: int) -> tuple[TaskState, dict]:
    """Send one user turn, run the tool loop, log the model turn. Returns its record."""
    state.messages.append(ChatMessageUser(content=text))
    store().set("full_outputs", [])   # nothing left over from an earlier failed turn
    rec: dict = {"record": "turn", "user_turn": user_turn, "turn": user_turn + 1,
                 "user_message": text, "started": _now(), "text": None,
                 "tool_calls": [], "code_tool_called": False, "reasoning": [],
                 "usage": {}, "model_calls": 0, "returned_models": [],
                 "stop_reasons": [], "files_saved": [], "error": None}
    try:
        before = await _files()
    except Exception as ex:
        before = {}
        rec["files_listing_error"] = f"{type(ex).__name__}: {ex}"
    try:
        for _ in range(max_rounds):
            n = len(state.messages)
            state = await generate(state, tool_calls="single")
            out = state.output
            rec["model_calls"] += 1
            rec["usage"] = _add_usage(rec["usage"], _usage_dict(out.usage))
            if out.model and out.model not in rec["returned_models"]:
                rec["returned_models"].append(out.model)
            rec["stop_reasons"].append(out.stop_reason)
            new = state.messages[n:]
            results = {m.tool_call_id: m for m in new if isinstance(m, ChatMessageTool)}
            assistants = [m for m in new if isinstance(m, ChatMessageAssistant)]
            for a in assistants:
                rec["reasoning"] += _reasoning(a)
                for tc in a.tool_calls or []:
                    res = results.get(tc.id)
                    code = (tc.arguments or {}).get("code")
                    full = store().get("full_outputs", [])
                    hit = next((i for i, x in enumerate(full) if x["code"] == code), None)
                    printed = full.pop(hit) if hit is not None else None
                    store().set("full_outputs", full)
                    rec["tool_calls"].append({
                        "output_full": printed["output"] if printed and printed["truncated"] else None,
                        "output_truncated_for_model": bool(printed and printed["truncated"]),
                        "returncode": printed["returncode"] if printed else None,
                        "id": tc.id, "function": tc.function, "code": code,
                        "arguments": tc.arguments,
                        "output": res.text if res else None,
                        "error": res.error.message if res and res.error else None})
            last = assistants[-1] if assistants else None
            if last is None or not last.tool_calls:
                rec["text"] = last.text if last else ""
                break
        else:
            rec["error"] = f"tool-round cap of {max_rounds} reached before a final reply"
    except Exception as ex:  # a failed turn ends the run; earlier turns stay logged
        rec["error"] = f"{type(ex).__name__}: {ex}"
    # The turn record must reach disk even if the sandbox has died, so a
    # failed file listing is recorded rather than raised.
    try:
        after = await _files()
        rec["files_saved"] = sorted(p for p, v in after.items() if before.get(p) != v)
    except Exception as ex:
        rec["files_listing_error"] = f"{type(ex).__name__}: {ex}"
    rec["code_tool_called"] = bool(rec["tool_calls"])
    rec["ended"] = _now()
    log.write(rec)
    return state, rec


async def _run_turns(state, generate, log, turns, condition, world, ctx) -> TaskState:
    for t in turns:
        text = ctx["prompts"].user_turn(t, condition, world, ctx["option"])
        state, rec = await _model_turn(state, generate, log, t, text, ctx["max_rounds"])
        if rec["error"]:
            log.write({"record": "end", "completed_turn": t - 1, "error": rec["error"]})
            return state
    log.write({"record": "end", "completed_turn": 8, "error": None})
    return state


def _access(model: str) -> dict:
    """How the model was reached, for the report's reporting fields. The base
    URL is read from the live client, so it is what was actually called."""
    try:
        base_url = getattr(get_model().api, "base_url", None)
    except Exception:
        base_url = None
    if model.startswith("openai-api/"):
        return {"mode": "API: OpenAI-compatible chat completions via Inspect's "
                        "openai-api provider",
                "service": model.split("/")[1], "base_url": base_url}
    provider = model.split("/")[0]
    return {"mode": f"API via Inspect's {provider} provider", "service": provider,
            "base_url": base_url}


def _run_id(batch: str, model: str, unit_id: str, condition: str) -> str:
    return hashlib.sha256(f"{batch}|{model}|{unit_id}|{condition}".encode()).hexdigest()[:16]


# --------------------------------------------------------------------------
# The solver
# --------------------------------------------------------------------------
@solver
def eight_turns(prompts: Prompts, option: str, max_rounds: int, batch: str,
                machine: str, run_settings: dict):
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        md = state.metadata
        model = str(state.model)
        world = md["world"]
        ctx = {"prompts": prompts, "option": option, "max_rounds": max_rounds}
        outdir = RUNS_DIR / batch / machine

        def header(condition: str, run_id: str, parent: str | None) -> dict:
            return {
                "run_id": run_id, "parent_run_id": parent,
                "branched_after_turn": 2 if parent else None,
                "condition": condition, "model": model,
                "world": world, "dataset_seed": md["seed"],
                "dataset_rank": md["dataset_rank"], "replicate": md["replicate"],
                "unit_id": md["unit_id"], "order_index": md["order_index"],
                "machine_index": md["machine_index"], "machine": machine,
                "batch": batch, "access_time_utc": _now(),
                "expectation_option": option,
                "expectation_sentence": prompts.expectation(world, option),
                "prompts_version": prompts.raw.get("version"),
                "prompts_sha256": prompts.sha256,
                "system_prompt": prompts.system,
                "user_turns": {t: prompts.user_turn(t, condition, world, option)
                               for t in (1, 3, 5, 7)},
                "tool": {"name": TOOL_NAME, "description": TOOL_DESCRIPTION},
                "access": _access(model),
                "sampling_settings": "none set by the harness: provider defaults "
                                     "(no temperature, max tokens, seed or thinking "
                                     "parameter is sent)",
                "post_processing": "none in this log; exports replace inline "
                                   "<think> blocks with a placeholder",
                **run_settings,
            }

        state.messages = [ChatMessageSystem(content=prompts.system)]
        state.tools = [python_tool()]

        if md["kind"] == "before":
            rid = _run_id(batch, model, md["unit_id"], "before")
            log = RunLog(outdir / f"{rid}.jsonl", header("before", rid, None))
            state.store.set("run_ids", {"before": rid})
            return await _run_turns(state, generate, log, (1, 3, 5, 7), "before", world, ctx)

        # A pair: Never, then the After run branched from it after turn 2.
        never_id = _run_id(batch, model, md["unit_id"], "never")
        after_id = _run_id(batch, model, md["unit_id"], "after")
        state.store.set("run_ids", {"never": never_id, "after": after_id})
        never = RunLog(outdir / f"{never_id}.jsonl", header("never", never_id, None))

        state, t2 = await _model_turn(state, generate, never, 1,
                                      prompts.user_turn(1, "never", world, option),
                                      max_rounds)
        if t2["error"]:
            never.write({"record": "end", "completed_turn": 0, "error": t2["error"]})
            return state

        branch_messages = copy.deepcopy(state.messages)
        branch_files = await _snapshot()

        state = await _run_turns(state, generate, never, (3, 5, 7), "never", world, ctx)

        if "after" in md["conditions"]:
            await _restore(branch_files)
            state.messages = branch_messages
            after = RunLog(outdir / f"{after_id}.jsonl", header("after", after_id, never_id))
            after.write({**t2, "shared_with": never_id})   # turns 1-2 are the Never run's
            state = await _run_turns(state, generate, after, (3, 5, 7), "after", world, ctx)
        return state

    return solve


# --------------------------------------------------------------------------
# The task
# --------------------------------------------------------------------------
def _split(v) -> list[str]:
    return [x.strip() for x in v.split(",")] if isinstance(v, str) else list(v)


@task
def cave_or_hold(
    worlds: str = "underpowered,confounded",
    datasets: str = "first5",
    runs_per_cell: int = 5,
    conditions: str = "never,before,after",
    shuffle_seed: int = 20261113,
    n_machines: int = 1,
    machine_index: int = 0,
    expectation_option: str = "A",
    batch: str = "dev",
    sandbox_kind: str = "docker",
    max_tool_rounds: int = 30,
    limit_units: int = 0,
) -> Task:
    prompts = Prompts.load()
    if expectation_option not in prompts.raw["expectation"]:
        raise ValueError(f"expectation_option must be one of {list(prompts.raw['expectation'])}")
    if int(n_machines) < 1 or not 0 <= int(machine_index) < int(n_machines):
        raise ValueError(f"machine_index must be 0..{int(n_machines) - 1} for n_machines={n_machines}")
    if sandbox_kind not in ("docker", "local"):
        raise ValueError("sandbox_kind must be 'docker' or 'local'")
    units = planmod.deal(planmod.build(_split(worlds), datasets, int(runs_per_cell),
                                       _split(conditions), int(shuffle_seed)),
                         int(n_machines))
    mine = [u for u in units if u.machine_index == int(machine_index)]
    if limit_units:
        mine = mine[: int(limit_units)]
    machine = socket.gethostname()
    run_settings = {
        "shuffle_seed": int(shuffle_seed), "runs_per_cell": int(runs_per_cell),
        "datasets_used": datasets, "n_machines": int(n_machines),
        "n_units_in_full_plan": len(units),
        # Harness-side only: decides when Inspect itself truncates tool output.
        # Nothing here is sent to the provider.
        "generate_config_set_by_harness": TASK_CONFIG.model_dump(exclude_none=True),
        "sandbox": sandbox_kind,
        "sandbox_image": ("caveharness-sandbox:1 (harness/sandbox/Dockerfile; "
                          "Python 3.11.18, packages in sandbox/requirements.txt; "
                          "no network; 1 CPU; 2 GB memory)")
        if sandbox_kind == "docker" else "local (development only)",
        "session_state": "full conversation replayed every call; each tool call is a "
                         "fresh Python process; files persist in the working directory",
        "inspect_ai_version": inspect_ai.__version__,
        "harness_commit": _git_commit(),
        "max_tool_rounds_per_turn": int(max_tool_rounds),
        "tool_output_cap_chars": TOOL_OUTPUT_CAP,
        "tool_output_cap_message": f"[output truncated at {TOOL_OUTPUT_CAP} characters]",
        "tool_timeout_seconds": 180,
    }
    samples = [Sample(id=u.unit_id, input=prompts.user_turn(1, u.conditions[0], u.world,
                                                           expectation_option),
                      metadata=u.as_metadata(),
                      files={"branches.csv": u.path})
               for u in mine]
    sb = ("docker", str(COMPOSE)) if sandbox_kind == "docker" else "local"
    # Inspect wraps tool output over 16 KiB in its own wording ("The output of
    # your call to python was too long to be displayed...") that the model
    # reads. Raise its limit far above the tool's own cap so that only the
    # tool's cap, with its one neutral line, ever applies.
    return Task(config=TASK_CONFIG,
                dataset=MemoryDataset(samples, shuffled=False),
                solver=eight_turns(prompts, expectation_option, int(max_tool_rounds),
                                   batch, machine, run_settings),
                tools=None, sandbox=sb)
