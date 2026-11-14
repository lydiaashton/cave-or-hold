# Cave or hold: run harness (Inspect)

Runs the eight-turn conversations from the Engineering handoff, branches each
Never run into its After run after turn 2 (sandbox files restored), logs every
turn as it finishes, exports each batch into the repository, runs the three LLM
judges on the saved summaries, and reports tokens and cost. How the pieces fit
together (Docker, API calls, where each file is saved and who may see it) is
drawn in [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).

## Check the harness (seconds; no Docker, no key)

    uv run pytest -q

## Setup (each machine)

1. Install [uv](https://docs.astral.sh/uv/) and Docker Desktop, and start Docker.
2. `cd harness && uv sync`
3. Build the sandbox image once: `cd sandbox && docker compose build && cd ..`
   Every package is pinned (`sandbox/requirements.txt`), so every machine's image
   is identical; the image also limits math libraries to one thread, see the Dockerfile.
4. Put the keys in `harness/.env` or in the repository root's `.env` (both
   gitignored; `harness/.env` wins): `ADAPTION_API_KEY=...` for the Adaption
   models and the Gemma and DeepSeek judges, `OPENAI_API_KEY` for the GPT judge,
   `ANTHROPIC_API_KEY` for the Claude models.
   On Windows PowerShell use `-Encoding ascii`; the default adds a byte-order
   mark that breaks the variable name.
5. On Windows, keep the repository near the top of a drive (e.g. `C:\work\cave-or-hold`):
   the `anthropic` package has files deep enough to pass the 260-character path
   limit from a deeply nested folder, and then fails to import. Enabling Windows
   long paths also fixes it.

## The pilot, end to end

1. `check_models` (model IDs) -> 2. `inspect eval` on every machine -> 3. merge
every machine's `runs/<batch>/` and `logs/` -> 4. `status` (anything to re-run?)
-> 5. `export` (exports/<batch>/: summaries by turn, analysis, key) -> 6. `judge` (judge
results and judge report). Each step is below; steps 4-6 can be repeated as
runs come in.

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

Real models run only in the Docker sandbox: the run refuses to start a unit in
the local sandbox (or under an Inspect `--sandbox` override) unless the model is
the offline fake, because there the model's code could read the answer key. One
unit that errors does not stop the others on the machine (`fail_on_error=False`).
Each sandbox takes up to 2 GB; if Docker Desktop has little memory, add
`--max-sandboxes 4`.

| Parameter | Meaning |
|---|---|
| `worlds` | comma list: underpowered, confounded, strong; default all three |
| `datasets` | `firstN`: the N lowest seeds per world (`first5`, `first20`, ...; refused if N exceeds what `release/` holds), or `all` (sixty per world). No dataset in `release/` was used in a pilot: the ones pilots 1 and 2 ran on were taken out on 14 Nov (`generator/piloted_seeds.json`) and each world topped back up to sixty. Underpowered: selected 14 Nov (primary p .10 to .13; `generator/select_underpowered.py`). `pilot` / `pilotN` read `release_pilot/` instead: ten pilot datasets per world that never appear in `release/` |
| `runs_per_cell` | runs per world x condition; must be a multiple of the datasets used |
| `conditions` | the kinds, default `never,before,after`; After needs Never |
| `wordings` | expectation wordings, each its own Before and After cell; default `B,D` (the main design): never, before_B, after_B, before_D, after_D. There is no fallback wording |
| `wording_worlds` | limits a wording to some worlds, e.g. `D:underpowered+confounded` (default: every wording in every world) |
| `shuffle_seed` | seed for the run order; recorded in every run |
| `n_machines`, `machine_index` | every machine passes the same plan and its own index (0-based) |
| `batch` | name for this set of runs; logs go to `runs/<batch>/` |
| `limit_units` | run only the first N units (smoke tests; breaks balance) |
| `sandbox_kind` | `docker` (required for real runs) or `local` (development only) |

A unit is one Inspect sample: a Never run plus one After run per wording, all
branched from its turn 2 with the sandbox restored for each, or a Before run.
The defaults (all three worlds, `B,D`) are the main design: every model runs every world and both wordings, 15 cells per model.

The board sentence ("The board will use your summary to decide...") is switched
in `prompts/turns.toml` (`include_board_sentence`, on since 13 Nov): it is part
of the wording the study lead signs off, so it lives with the prompts. Every machine builds the same shuffled plan from the same
seed and takes its share (round-robin within each world x condition stratum).

Other models: `openai-api/adaption/glm-5.2`; Claude needs `ANTHROPIC_API_KEY`
and `--model anthropic/claude-opus-5-5` or `anthropic/claude-sonnet-5-5` (not yet tested live).

## Status: what is done, what to re-run

    uv run python -m caveharness.status --batch pilot1 --model openai-api/adaption/qwen3.5-397b \
        --worlds underpowered,confounded --datasets first5 --runs-per-cell 5 --n-machines 2

Same plan arguments as the run (`--wordings`, `--wording-worlds` too). Rebuilds the plan, writes it with each run's
status to `runs/<batch>/plan_<model>.csv`, and prints per machine how many runs
have turn 4 on disk, the runs by machine x world x condition (handoff 8: machine
must not stand in for condition), and the `--sample-id` list that re-runs only
the units with no run at turn 4 (same command and `-T` arguments, `limit_units`
0); old logs are kept as `.prev-*` and ignored. A pair where one run already
counts and the other failed is listed apart: re-running it would replace the
run that counts, so that is the study lead's call. If the same run is logged on
two machines, the attempt that got further is used, with a warning.

## Export (once per batch, into the repository)

    uv run python -m caveharness.export --batch <batch>

Merge every machine's `runs/<batch>/` and `logs/` folders first (the logs carry
the deployment fingerprints). The export is written to `<repo>/exports/<batch>/`
and is committed and pushed once per batch. Scorers cannot see the repository;
they receive only the scoring page built from a `summaries/` folder.

    exports/<batch>/
      T2/ T4/ T6/ T8/
        summaries/<id>.txt          summary ID + summary, nothing else
        analysis/
          analysis_values.csv       every estimate / 95% CI / p the code printed, one row each
          logs/<id>.txt             the code the model ran and what it printed, up to this
                                    summary (no user messages, no thinking)
          thinking/<id>.txt         the thinking trace / reasoning summary the provider returned
      key/        KEY.csv (summary ID -> run, condition, turn, model, dataset), id_secret.txt,
                  run_stats.csv, analysis_estimates.csv, manifest.json, pilot_report.md
      scoring/    batch1/summaries (turn 4) and batch2/summaries (turns 6 and 8): what
                  human scorers grade. Only the primary model's never, before_B and
                  after_B cells; other wordings (D) go to the judges only
      judges/     judge_items.jsonl (what the judges may see: no user messages, condition
                  or thinking)
      judging/    written by the judge runner (below); the export never deletes it

Options: `--primary-model` (whose summaries humans score; default the batch's
only model), `--scoring-wording` (default `B`), `--scoring-per-cell N` (an equal
number of runs per world x cell, drawn the same way on every re-export; default
all). The scoring page is built from `scoring/batch1/summaries`; batch 2 is
released only after every scorer finishes batch 1. `key/scoring_sets.csv` lists
what went where. `quotes_expectation_sentence` in the key is a narrow text check
(the expectation sentence repeated word for word), not a disclosure measure.

Summary IDs are a keyed hash of (turn, run) under a secret made once per batch
(`key/id_secret.txt`). Every summary keeps its ID on every re-export, even when
runs are added later, and IDs never repeat across batches. An After run's turn 2
is its Never run's, so T2 holds each such summary once and the key lists both
runs against its ID.

`exports/pilot1/` was exported before keyed IDs and has no `id_secret.txt`:
re-exporting it would rename every summary, so the export refuses unless
`--replace-ids` is given. Leave it as it is.

Thinking files quote the user's messages and so reveal the condition, and
`key/` and `judging/` hold conditions and outcomes: none of them go to scorers.

## Judge

    uv run python -m caveharness.judge --batch pilot1 --allow-draft-prompts

Three calls per summary per judge: the scorer call (summary only: the human
scorers' questions from the Codebook tab), form A (analysis log only) and form B
(summary only). No call sees the answer key: the primary outcome is worked out
from the scorer call's claim and uncertainty answers through the Codebook's
mapping table (the label call, which graded against the answer key, was dropped
on 14 Nov). Each call is stateless and sees only its own inputs; no judge sees
the user's messages, the condition or the thinking. Turn 4 gets all three; turns
2, 6 and 8 get the scorer call (`--form-turns 2,4,6,8` adds the forms). An After
run's turn 2 is its Never run's, judged once.

Every call is appended to `exports/<batch>/judging/judgments.jsonl` as it
returns; `judge_results.csv` and `judge_report.md` are written beside it. A
failed call is recorded and retried by running the command again; nothing
already judged is paid for twice (a summary whose text changed, e.g. after a
re-run, is judged again). `--dry-run` shows the work and one prompt per call.
Judging is a separate step from the runs on purpose, so a judge failure can
never touch a run; to judge each run soon after it is saved (handoff 6), keep
it running in a loop during the batch:

    while true; do uv run python -m caveharness.judge --batch pilot1 --allow-draft-prompts; sleep 300; done

A majority needs more than half of the configured judges (2 of 3), so one
judge alone is never reported as the majority.

The prompts are in `prompts/judges.toml`. **They are an engineering draft until
the study lead sends the frozen ones** (handoff 10): the runner refuses draft
prompts unless `--allow-draft-prompts` is given (pilot only). Once the study lead
signs them off, set `frozen = true` and judge again; every row
carries the prompt file's sha256.

## Cost

Fill `prices.toml` (per million tokens, per model, in any unit, e.g. Adaption
credits). The pilot report then shows the estimated cost per run of the tested
model, and the judge report the cost per run of each judge and call (scorer,
form A, form B). Models without a price show "price not set".

## Where everything is saved

| Path | What | Who may see it |
|---|---|---|
| `runs/<batch>/<machine>/<run_id>.jsonl` | one log per run, written turn by turn | engineering (gitignored) |
| `runs/<batch>/plan_<model>.csv` | the plan with each run's status | engineering (gitignored) |
| `logs/*.eval` | Inspect's full transcripts | engineering (gitignored) |
| `exports/<batch>/T*/summaries/` | the summaries; the scoring page is built from these | scorers get the page only |
| `exports/<batch>/T*/analysis/` | analysis values, logs, thinking | study lead, engineering |
| `exports/<batch>/key/` | the key, run stats, pilot report | study lead, engineering |
| `exports/<batch>/judges/`, `judging/` | judge inputs; judgments, results, report | study lead, engineering |
| `runs/model_check.json` | live model-list check | engineering (gitignored) |

`exports/` is committed to the repository, which scorers cannot see.

## What is logged

Per run, `runs/<batch>/<machine>/<run_id>.jsonl`: a header with every reporting
field (model, world, seed, replicate, condition, machine, prompts and their
sha256, system prompt, tool description, sandbox, versions, the generation
settings in effect and the max_tokens Inspect sends where a provider requires
one), then one line per model turn written when the turn ends -- so turn 4 is
on disk before turn 5 is sent. Each turn has the summary text, every assistant
message (including text written next to a tool call), every tool call with its
code and output, files saved, thinking (kept separately; replaced by a
placeholder in exports), token usage and the returned model ID. A turn whose
reply is a provider error (context length, content filter) or blank is logged
as an error, not as a summary; a reply cut off by the output limit is kept and
flagged. The Inspect `.eval` log in `logs/` holds the full transcript; raw API
calls are kept for the first 5 model calls of each unit.

## Offline test (no key, no cost)

    uv run inspect eval src/caveharness/task.py@cave_or_hold --model cavefake/analyst \
        -T worlds=underpowered -T batch=offline_test -T limit_units=4 --log-dir logs
    uv run python -m caveharness.export --batch offline_test
    uv run python -m caveharness.judge --batch offline_test --allow-draft-prompts \
        --judges j1=cavefake/judge,j2=cavefake/judge,j3=cavefake/judge

The analyst runs in Docker by default; add `-T sandbox_kind=local` to skip Docker.
