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
from caveharness.export import PLACEHOLDER, clean
from caveharness.prompts import Prompts

TOOL_NAME = "python"
TOOL_DESCRIPTION = ("Run Python code in the working directory and return what it "
                    "printed. Each call starts a new Python process. Files written "
                    "to the working directory are kept between calls.")
TOOL_PARAMETER_DESCRIPTION = "The Python code to run."
COMPOSE = HARNESS_DIR / "sandbox" / "compose.yaml"
# Where the model's code can write. In Docker that is /work, /tmp and /dev/shm
# (the rest of the container is read-only, see sandbox/compose.yaml), all
# snapshotted for the After branch. The local sandbox is the host: only its
# working directory is ever touched. Which one applies is decided from the
# sandbox actually running (its working directory), never from a parameter,
# so an Inspect --sandbox override can never clear the host's /tmp.
WRITE_ROOTS = {"docker": (".", "/tmp", "/dev/shm"), "local": (".",)}
DOCKER_WORKDIR = "/work"
DATASET_HEADER = ("branch_id,week,switched_branch,after_switch,service_score,"
                  "staffing_index,visits_index")
OFFLINE_MODELS = ("cavefake/", "mockllm/")   # may use the local sandbox
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
# Both scripts take the write roots as arguments. Paths under "." are relative
# (as before), others absolute. Only regular files are listed (a link to a
# file is restored as a copy, as before; dangling links, sockets and pipes are
# skipped), and /tmp/mpl is matplotlib's cache, not the model's.
_LIST = """\
import json, os, sys
out = []
for root in sys.argv[1:]:
    for r, ds, fs in os.walk(root):
        if r == '/tmp':
            ds[:] = [d for d in ds if d != 'mpl']
        for f in fs:
            p = os.path.normpath(os.path.join(r, f))
            if os.path.isfile(p):
                st = os.stat(p)
                out.append([p, st.st_size, st.st_mtime])
print(json.dumps(sorted(out)))
"""
_CLEAR = """\
import os, shutil, sys
for root in sys.argv[1:]:
    for name in os.listdir(root):
        p = os.path.join(root, name)
        if root == '/tmp' and name == 'mpl':
            continue
        if os.path.isdir(p) and not os.path.islink(p):
            shutil.rmtree(p)
        else:
            os.remove(p)
"""


async def _files(roots: tuple[str, ...]) -> dict[str, tuple[int, float]]:
    r = await sandbox().exec(["python", "-c", _LIST, *roots])
    if not r.success:   # never read a failed listing as "no files"
        raise RuntimeError(f"listing the sandbox files failed: {r.stderr.strip()[-500:]}")
    return {p: (s, m) for p, s, m in json.loads(r.stdout)}


async def _snapshot(roots: tuple[str, ...]) -> dict[str, bytes]:
    return {p: await sandbox().read_file(p, text=False) for p in await _files(roots)}


async def _restore(snap: dict[str, bytes], roots: tuple[str, ...]) -> None:
    r = await sandbox().exec(["python", "-c", _CLEAR, *roots])
    if not r.success:
        raise RuntimeError(f"clearing the sandbox failed: {r.stderr.strip()[-500:]}")
    for p, data in snap.items():
        await sandbox().write_file(p, data)


def _sandbox_problem(model: str, cwd: str, first_line: str) -> str | None:
    """Why this sandbox must not run this model, or None (handoff 2, work plan 3).

    Real models need the Docker sandbox: the local one runs their code on the
    host, where the answer key, the world-named folders and the API keys are
    readable. This also catches an Inspect --sandbox override, which the run
    header would not show. And branches.csv must be a dataset file: if its
    host file vanished, Inspect would have written the host path (which names
    the world) into it instead."""
    if first_line != DATASET_HEADER:
        return "branches.csv in the sandbox is not a dataset file"
    if cwd != DOCKER_WORKDIR and not model.startswith(OFFLINE_MODELS):
        return ("real models must run in the Docker sandbox (harness/sandbox/compose.yaml); "
                "the local sandbox is for the offline fake model only")
    return None


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
                      user_turn: int, text: str, max_rounds: int,
                      roots: tuple[str, ...]) -> tuple[TaskState, dict]:
    """Send one user turn, run the tool loop, log the model turn. Returns its record."""
    state.messages.append(ChatMessageUser(content=text))
    store().set("full_outputs", [])   # nothing left over from an earlier failed turn
    rec: dict = {"record": "turn", "user_turn": user_turn, "turn": user_turn + 1,
                 "user_message": text, "started": _now(), "text": None,
                 "assistant_messages": [],
                 "tool_calls": [], "code_tool_called": False, "reasoning": [],
                 "usage": {}, "model_calls": 0, "returned_models": [],
                 "stop_reasons": [], "files_saved": [], "error": None}
    try:
        before = await _files(roots)
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
                # Every assistant message (handoff 5), including text written
                # next to a tool call; "text" below stays the turn's last reply.
                rec["assistant_messages"].append(
                    {"text": a.text, "tool_call_ids": [tc.id for tc in a.tool_calls or []]})
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
        # Inspect returns some provider failures (context length, content
        # filter) as ordinary replies whose text is the error message. That is
        # not a summary and must not be graded as one; nor is a blank reply.
        stop = state.output.stop_reason
        if rec["error"] is None:
            if stop in ("model_length", "content_filter"):
                rec["error"] = f"the provider ended the reply with stop_reason={stop}"
            elif not clean(rec["text"]).replace(PLACEHOLDER, "").strip():
                # blank, or only reasoning (e.g. cut off mid-thought): nothing to grade
                rec["error"] = "the final reply has no text besides reasoning"
            elif stop == "max_tokens":
                rec["reply_cut_off"] = True   # kept and graded, but flagged
    except Exception as ex:  # a failed turn ends the run; earlier turns stay logged
        rec["error"] = f"{type(ex).__name__}: {ex}"
    # The turn record must reach disk even if the sandbox has died, so a
    # failed file listing is recorded rather than raised.
    try:
        after = await _files(roots)
        rec["files_saved"] = sorted(p for p, v in after.items() if before.get(p) != v)
    except Exception as ex:
        rec["files_listing_error"] = f"{type(ex).__name__}: {ex}"
    rec["code_tool_called"] = bool(rec["tool_calls"])
    rec["ended"] = _now()
    log.write(rec)
    return state, rec


async def _run_turns(state, generate, log, turns, condition, world, ctx) -> TaskState:
    for t in turns:
        text = ctx["prompts"].user_turn(t, condition, world)
        state, rec = await _model_turn(state, generate, log, t, text, ctx["max_rounds"],
                                       ctx["roots"])
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


def _settings_sent() -> dict:
    """Generation settings in effect (handoff 3: record, don't set). The harness
    sets none. This records anything given on the command line, and the
    max_tokens Inspect itself sends where a provider requires one (Anthropic:
    32,000 for Claude 5); null means none is sent."""
    try:
        # Not exported publicly by Inspect; inspect-ai is pinned in uv.lock.
        from inspect_ai.model._generate_config import active_generate_config
        m = get_model()
        cfg = m.config.merge(active_generate_config())
        return {"generate_config_in_effect": cfg.model_dump(exclude_none=True),
                "max_tokens_sent": (cfg.max_tokens or m.api.max_tokens_for_config(cfg)
                                    or m.api.max_tokens())}
    except Exception as ex:   # reporting only: never fail a run over it
        return {"settings_sent_error": f"{type(ex).__name__}: {ex}"}


def _run_id(batch: str, model: str, unit_id: str, condition: str) -> str:
    return hashlib.sha256(f"{batch}|{model}|{unit_id}|{condition}".encode()).hexdigest()[:16]


# --------------------------------------------------------------------------
# The solver
# --------------------------------------------------------------------------
@solver
def eight_turns(prompts: Prompts, max_rounds: int, batch: str,
                machine: str, run_settings: dict):
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        md = state.metadata
        model = str(state.model)
        world = md["world"]
        outdir = RUNS_DIR / batch / machine

        # Before anything is sent or logged: is this a sandbox the model may use?
        probe = await sandbox().exec(["python", "-c", "import os; print(os.getcwd()); "
                                      "print(open('branches.csv').readline().strip())"])
        cwd, first_line = (probe.stdout.splitlines() + ["", ""])[:2]
        problem = _sandbox_problem(model, cwd, first_line)
        if problem:
            raise RuntimeError(problem)
        sandbox_in_use = "docker" if cwd == DOCKER_WORKDIR else "local"
        write_roots = WRITE_ROOTS[sandbox_in_use]
        ctx = {"prompts": prompts, "max_rounds": max_rounds, "roots": write_roots}
        settings_sent = _settings_sent()

        def header(condition: str, run_id: str, parent: str | None) -> dict:
            kind, wording = Prompts.split_condition(condition)
            return {
                "run_id": run_id, "parent_run_id": parent,
                "branched_after_turn": 2 if parent else None,
                # condition carries the wording (before_B, after_D); the two
                # fields after it split it out for convenience
                "condition": condition, "condition_kind": kind,
                "expectation_wording": wording, "model": model,
                "world": world, "dataset_seed": md["seed"],
                "dataset_rank": md["dataset_rank"], "replicate": md["replicate"],
                "unit_id": md["unit_id"], "order_index": md["order_index"],
                "machine_index": md["machine_index"], "machine": machine,
                "batch": batch, "access_time_utc": _now(),
                "expectation_sentence": prompts.expectation(world, wording) if wording else None,
                "board_sentence_included": bool(prompts.raw.get("include_board_sentence")),
                "prompts_version": prompts.raw.get("version"),
                "prompts_sha256": prompts.sha256,
                "system_prompt": prompts.system,
                "user_turns": {t: prompts.user_turn(t, condition, world)
                               for t in (1, 3, 5, 7)},
                "tool": {"name": TOOL_NAME, "description": TOOL_DESCRIPTION,
                         "parameters": {"code": TOOL_PARAMETER_DESCRIPTION}},
                "access": _access(model),
                "sampling_settings": "none set by the harness: provider defaults. "
                                     "generate_config_in_effect lists anything given on "
                                     "the command line; max_tokens_sent is the value "
                                     "Inspect itself sends where the provider requires "
                                     "one (null: none sent)",
                **settings_sent,
                # what actually ran (an Inspect --sandbox override can differ
                # from -T sandbox_kind, which run_settings records)
                "sandbox_in_use": sandbox_in_use, "restored_paths": list(write_roots),
                "post_processing": "none in this log; exports replace inline "
                                   "<think> blocks with a placeholder",
                **run_settings,
            }

        state.messages = [ChatMessageSystem(content=prompts.system)]
        state.tools = [python_tool()]

        if md["kind"].startswith("before"):
            condition = md["conditions"][0]                     # before_B, before_D, ...
            rid = _run_id(batch, model, md["unit_id"], condition)
            log = RunLog(outdir / f"{rid}.jsonl", header(condition, rid, None))
            state.store.set("run_ids", {condition: rid})
            return await _run_turns(state, generate, log, (1, 3, 5, 7), condition, world, ctx)

        # A pair: Never, then one After run per wording, each branched from the
        # Never run's turn 2 with the sandbox files restored.
        never_id = _run_id(batch, model, md["unit_id"], "never")
        after_ids = {c: _run_id(batch, model, md["unit_id"], c)
                     for c in md["conditions"] if c.startswith("after")}
        state.store.set("run_ids", {"never": never_id, **after_ids})
        never = RunLog(outdir / f"{never_id}.jsonl", header("never", never_id, None))

        state, t2 = await _model_turn(state, generate, never, 1,
                                      prompts.user_turn(1, "never", world),
                                      max_rounds, write_roots)
        if t2["error"]:
            never.write({"record": "end", "completed_turn": 0, "error": t2["error"]})
            for c, aid in after_ids.items():   # logged, so failure counts per cell stay complete
                RunLog(outdir / f"{aid}.jsonl", header(c, aid, never_id)).write(
                    {"record": "end", "completed_turn": 0,
                     "error": "the Never run it branches from failed before turn 2"})
            return state

        branch_messages = copy.deepcopy(state.messages)
        try:
            branch_files, branch_error = await _snapshot(write_roots), None
        except Exception as ex:   # the Never run goes on; its After runs cannot
            branch_files, branch_error = {}, f"snapshot at turn 2 failed: {type(ex).__name__}: {ex}"

        state = await _run_turns(state, generate, never, (3, 5, 7), "never", world, ctx)

        for c, aid in after_ids.items():
            after = RunLog(outdir / f"{aid}.jsonl", header(c, aid, never_id))
            after.write({**t2, "shared_with": never_id})   # turns 1-2 are the Never run's
            try:
                if branch_error:
                    raise RuntimeError(branch_error)
                await _restore(branch_files, write_roots)
            except Exception as ex:
                after.write({"record": "end", "completed_turn": 2,
                             "error": f"sandbox restore failed: {ex}"})
                continue                                   # the next wording may still run
            # A fresh copy per branch: After-B's turns must never reach After-D.
            state.messages = copy.deepcopy(branch_messages)
            state = await _run_turns(state, generate, after, (3, 5, 7), c, world, ctx)
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
    wordings: str = "B",
    wording_worlds: str = "",
    shuffle_seed: int = 20261113,
    n_machines: int = 1,
    machine_index: int = 0,
    batch: str = "dev",
    sandbox_kind: str = "docker",
    max_tool_rounds: int = 30,
    limit_units: int = 0,
) -> Task:
    """conditions: the kinds (never, before, after). wordings: the expectation
    wordings, each its own Before and After cell (main runs: B,D). wording_worlds:
    limits a wording to some worlds, e.g. D:underpowered+confounded."""
    prompts = Prompts.load()
    wording_list = _split(wordings) if wordings else []
    unknown = set(wording_list) - set(prompts.wordings)
    if unknown:
        raise ValueError(f"wordings {sorted(unknown)} are not in prompts/turns.toml "
                         f"(have {prompts.wordings})")
    if int(n_machines) < 1 or not 0 <= int(machine_index) < int(n_machines):
        raise ValueError(f"machine_index must be 0..{int(n_machines) - 1} for n_machines={n_machines}")
    if sandbox_kind not in ("docker", "local"):
        raise ValueError("sandbox_kind must be 'docker' or 'local'")
    units = planmod.deal(planmod.build(_split(worlds), datasets, int(runs_per_cell),
                                       _split(conditions), int(shuffle_seed), wording_list,
                                       planmod.parse_wording_worlds(wording_worlds)),
                         int(n_machines))
    mine = [u for u in units if u.machine_index == int(machine_index)]
    if limit_units:
        mine = mine[: int(limit_units)]
    machine = socket.gethostname()
    run_settings = {
        "shuffle_seed": int(shuffle_seed), "runs_per_cell": int(runs_per_cell),
        "datasets_used": datasets, "n_machines": int(n_machines),
        "worlds": _split(worlds), "conditions": _split(conditions),
        "wordings": wording_list, "wording_worlds": wording_worlds,
        "limit_units": int(limit_units),
        "n_units_in_full_plan": len(units),
        # Harness-side only: decides when Inspect itself truncates tool output.
        # Nothing here is sent to the provider.
        "generate_config_set_by_harness": TASK_CONFIG.model_dump(exclude_none=True),
        "sandbox": sandbox_kind,
        "sandbox_image": ("caveharness-sandbox:1 (harness/sandbox/Dockerfile; "
                          "Python 3.11.18, packages in sandbox/requirements.txt; "
                          "no network; 1 CPU; 2 GB memory; read-only except /work, "
                          "/tmp and /dev/shm, all restored for the After branch)")
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
    samples = [Sample(id=u.unit_id, input=prompts.user_turn(1, u.conditions[0], u.world),
                      metadata=u.as_metadata(),
                      files={"branches.csv": u.path})
               for u in mine]
    sb = ("docker", str(COMPOSE)) if sandbox_kind == "docker" else "local"
    # Inspect wraps tool output over 16 KiB in its own wording ("The output of
    # your call to python was too long to be displayed...") that the model
    # reads. Raise its limit far above the tool's own cap so that only the
    # tool's cap, with its one neutral line, ever applies.
    # fail_on_error=False: one unit whose sandbox dies must not stop every other
    # unit on this machine. Turn errors are logged by the solver anyway; units
    # that error out are re-run with `inspect eval-retry` or `--sample-id`.
    return Task(config=TASK_CONFIG,
                dataset=MemoryDataset(samples, shuffled=False),
                solver=eight_turns(prompts, int(max_tool_rounds), batch, machine, run_settings),
                tools=None, sandbox=sb, fail_on_error=False)
