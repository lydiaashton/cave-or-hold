# Cave or hold: run harness (Inspect)

Runs the eight-turn conversations from the Engineering handoff, branches each
Never run into its After run after turn 2 (sandbox files restored), logs every
turn as it finishes, and exports blinded sheets for scorers and judges.

## Check the harness (seconds; no Docker, no key)

    uv run pytest -q

## Setup (each machine)

1. Install [uv](https://docs.astral.sh/uv/) and Docker Desktop, and start Docker.
2. `cd harness && uv sync`
3. Build the sandbox image once: `cd sandbox && docker compose build && cd ..`
   Every package is pinned (`sandbox/requirements.txt`), so every machine's image
   is identical; the image also limits math libraries to one thread, see the Dockerfile.
4. Create `harness/.env` (gitignored) with `ADAPTION_API_KEY=...`.
   On Windows PowerShell use `-Encoding ascii`; the default adds a byte-order
   mark that breaks the variable name.

## Check model IDs (handoff section 3)

    uv run python -m caveharness.check_models

Writes `runs/model_check.json`. Providers without a key are reported as skipped.

## Run

    uv run inspect eval src/caveharness/task.py@cave_or_hold ^
        --model openai-api/adaption/qwen3.5-397b ^
        --model-base-url https://api.prod.adaptionlabs.ai/api/v1 ^
        -T worlds=underpowered,confounded -T datasets=first5 -T runs_per_cell=5 ^
        -T batch=pilot1 -T n_machines=1 -T machine_index=0 --log-dir logs

(`^` continues a line in Windows cmd; use `` ` `` in PowerShell and `\` in bash.)
`--model-base-url` is required for Adaption; `.env` needs only the key.

| Parameter | Meaning |
|---|---|
| `worlds` | comma list: underpowered, confounded, strong |
| `datasets` | `first5` (the five lowest seeds per world) or `all` (ten) |
| `runs_per_cell` | runs per world x condition; must be a multiple of the datasets used |
| `conditions` | default `never,before,after`; After needs Never |
| `shuffle_seed` | seed for the run order; recorded in every run |
| `n_machines`, `machine_index` | every machine passes the same plan and its own index (0-based) |
| `expectation_option` | A (default), B, C or D from the prompt draft |
| `batch` | name for this set of runs; logs go to `runs/<batch>/` |
| `limit_units` | run only the first N units (smoke tests; breaks balance) |
| `sandbox_kind` | `docker` (required for real runs) or `local` (development only) |

A unit is one Inspect sample: a Never run plus the After run branched from it,
or a Before run. Every machine builds the same shuffled plan from the same
seed and takes its share (round-robin within each world x condition stratum).

Other models: `openai-api/adaption/glm-5.2`; Claude needs `ANTHROPIC_API_KEY`
and `--model anthropic/claude-opus-5` (not yet tested).

## Export

    uv run python -m caveharness.export --batch pilot1 --seed <recorded seed>

Merge every machine's `runs/<batch>/` folder first. Scorer and judge files go
to `export/<batch>/`; the key and run statistics go to `export_key/<batch>/`
(study lead only). `export_key/<batch>/pilot_report.md` has the pilot numbers.

## What is logged

Per run, `runs/<batch>/<machine>/<run_id>.jsonl`: a header with every reporting
field (model, world, seed, replicate, condition, machine, prompts and their
sha256, system prompt, tool description, sandbox, versions), then one line per
model turn written when the turn ends -- so turn 4 is on disk before turn 5 is
sent. Each turn has the summary text, every tool call with its code and output,
files saved, thinking (kept separately; replaced by a placeholder in exports),
token usage and the returned model ID. The Inspect `.eval` log in `logs/` holds
the full transcript including raw API calls.

## Offline test (no key, no cost)

    uv run inspect eval src/caveharness/task.py@cave_or_hold --model cavefake/analyst \
        -T worlds=underpowered -T batch=offline_test -T limit_units=4 --log-dir logs
