# Final scorer Sheet, 15 Nov 2026

Downloaded from the study's Google Sheet ("Cave or hold – scorer answers") at 20:07 UTC on 15 Nov 2026, after scoring closed at 20:00 UTC.
Each main tab is written to CSV with values unchanged, except that the Sheet's timestamps (stored in the spreadsheet's time zone, US Central) are written in UTC, and numbers are written the way a Google CSV export writes them. The Sheet's address and the page endpoint are not included.

**Raw and append-only.** The scoring page sends the open summary every 30 seconds and again when the scorer moves on, so one summary has several rows. `scoring/combine_scorer_files.py` keeps the latest row per scorer and summary by the page's own clock (`client_time`). With `--order` it maps IDs the Sheet stored as numbers back to their summaries (here `2.59488E+24` -> `0259488e19`).

**Scoring window (lock rule 1, `scoring/main/LOCK_2026-11-15.md`).** Answers received after 20:00:00 UTC are excluded. `in_window/` holds the same rows with those removed; combine from `in_window/`.

| Tab | Rows | Rows by scorer | After 20:00 UTC | SHA-256 (raw) |
|---|---|---|---|---|
| round1 | 1405 | S1 281, S2 384, S3 641, S4 97, TEST 2 | 0 | `149c6dac599a68535efa25f5f1d0aef2ca7c5366976aed48b137d1ff4020ac8a` |
| round2 | 223 | S1 43, S2 62, S3 117, TEST 1 | 0 | `47183ca841815a0cbb713bf91061b28c8bfe1ff859d1c81d3f28b3c56e777a97` |
| round3 | 370 | S1 164, S2 36, S3 169, TEST 1 | 6 | `c00ae78febd5f379384d9b8b49ed81d38374463f6e27178c4738a0aaa6c7b77b` |

`in_window/` (rows received by 20:00:00 UTC):

| Tab | Rows | SHA-256 |
|---|---|---|
| round1 | 1405 | `149c6dac599a68535efa25f5f1d0aef2ca7c5366976aed48b137d1ff4020ac8a` |
| round2 | 223 | `47183ca841815a0cbb713bf91061b28c8bfe1ff859d1c81d3f28b3c56e777a97` |
| round3 | 364 | `32fa6419f5759b8681eb7e4ef9147974923970a4f852c58fc0167c4bb444e4ea` |

The 6 late rows are all S3, round 3 (three summaries, received 20:00:10 to 20:02:11 UTC).
TEST rows are typed by the study lead while testing the pages; the combiner drops them with `--ignore-codes TEST`.
