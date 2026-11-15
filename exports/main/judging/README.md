# Main-batch judging outputs

Judge outputs for the main runs (900 runs, 3,240 judged summaries). All 15,120 judge calls succeeded;
`judge_report.md` lists no call still failing.

## Files

| File | What it is |
|---|---|
| `judgments.jsonl.gz` | Every judge call attempt, one JSON record per line (gzip -9 of `judgments.jsonl`). Each record carries the summary, run, turn, judge, call, world and dataset seed; `ok`, `error` and `problems`; the judge's output, text, reasoning and token usage; prompt hashes and client settings. |
| `judgments.jsonl` | The uncompressed file (116.8 MB). Not committed (over GitHub's 100 MB limit; listed in `.gitignore`). Recreate with `gunzip -k judgments.jsonl.gz`. |
| `judge_results.csv` | One row per run and turn (3,600 rows: 900 runs x turns 2, 4, 6, 8), joined to run metadata and condition: each judge's scorer-call ratings and the judge-majority form A and form B fields. |
| `judge_report.md` | Descriptive summary: calls, attempts, tokens and cost per judge and call; judge cost per run; primary outcome and deciding checks at turn 4 (judge majority); judge agreement on the turn-4 bottom-line claim; calls still failing. |

## Call counts

5,040 successful calls per judge, the same for each of `gpt-6.1-terra`, `gemma-4-31b-it` and `deepseek-v4-flash`:

| Call | Per judge | All three judges |
|---|---|---|
| scorer | 3,240 | 9,720 |
| form_a | 900 | 2,700 |
| form_b | 900 | 2,700 |
| Total | 5,040 | 15,120 |

`judgments.jsonl` includes failed attempts as well as the successful call: 15,193 rows for 15,120 calls.
Each call has exactly one successful record. The DeepSeek (`deepseek-v4-flash`) form_a call for summary
`02951ccb4a` (turn 4) succeeded on its 7th attempt, the most of any call.

## SHA-256

| File | Bytes | SHA-256 |
|---|---|---|
| `judgments.jsonl` (uncompressed, not committed) | 116,779,672 | `3128474e5e13054d70d05cdc09c0198a5ecdc530848473d5a74748e659cede2b` |
| `judgments.jsonl.gz` | 36,671,232 | `fa2dcdc6b5f17c0f494dc28c54e5f9e7cd0aba17e774684a62d9583aaa3794c4` |
| `judge_results.csv` | 1,103,326 | `c876c3fe4693264b1e875a915770bc4ba44fc56a63f80b4fce6c7320aebc8bd8` |
| `judge_report.md` | 6,437 | `67d5c99045a818c28806be9e626f2c35bd7d5dc6953f2af6e25dcaf10fef591c` |

Check after decompressing: `shasum -a 256 judgments.jsonl` should match the first row.
