# Cave or Hold? The video (long cut, v15)

A short animated explainer of the study: what we tested, how the bottom lines were scored, and what we found. Every frame is drawn in Python (Pillow) and encoded with ffmpeg; the music is synthesized by the kit.

The MP4s are not in the repo. They are attached to the release [`video-v15`](https://github.com/lydiaashton/cave-or-hold/releases/tag/video-v15).

## The cuts

All are 1920×1080, 30 fps.

| File | Length | Sound | Captions |
|---|---|---|---|
| `LydiaAshton_CaveOrHold_LongCut_v15_Narrated.mp4` | 4:43 (283.5 s) | narration and music, −16 LUFS | none |
| `LydiaAshton_CaveOrHold_LongCut_v15_Narrated_CC.mp4` | 4:43 | narration and music | subtitle track (English, can be turned off) |
| `LydiaAshton_CaveOrHold_LongCut_v15_Narrated_Captioned.mp4` | 4:43 | narration and music | burned in |
| `LydiaAshton_CaveOrHold_LongCut_v15.mp4` | 5:05 (304.7 s) | music only | on-screen caption panels |
| `LydiaAshton_CaveOrHold_LongCut_v15_NoCaptions.mp4` | 5:05 | music only | none |

The narrated cuts follow the voice: each on-screen event is timed to the word that names it. The music-only cuts keep their own, slower reading timing, so every caption stays up long enough to read at 3 words per second or slower.

**The narration is an AI voice** (ElevenLabs), reading the script in [`script/`](script/). The narrated cuts say so in the closing credits.

Captions for the narrated cut: [`captions/`](captions/) (`.srt` and `.vtt`).

## Where the numbers come from

Every number in the video comes from a file in this repo.

| In the video | Value | Source |
|---|---|---|
| The data: estimate, interval, p | +2.4 points, 95% interval −0.7 to +5.5, p = .12 | [`release/answer_key/manifest_underpowered.json`](../release/answer_key/manifest_underpowered.json), seed 20271027, primary spec `twfe_with_cov\|cluster` (2.4186; −0.7010 to 5.5383; p = 0.1243) |
| The data: chart and built-in effect | weekly means; +2.0 | [`release/underpowered_seed20271027/branches.csv`](../release/underpowered_seed20271027/branches.csv) (34 branches, 20 switched; built-in effect 1.985) |
| Caving by condition (human scorers) | Never 6 of 60, Before 7 of 60, After 13 of 60 | [`analysis/cave_analysis.py`](../analysis/cave_analysis.py) on [`exports/main/scoring/scorer_labels_all.csv`](../exports/main/scoring/scorer_labels_all.csv) with [`exports/main/key/KEY.csv`](../exports/main/key/KEY.csv): majority of the three scorers (`scorer_long_to_errors`, then `majority_label`), underpowered world, conditions `never`, `before_B`, `after_B` |
| The caving test (After vs. Never, paired) | 53 pairs the same; 7 only After caved, 0 only Never; about 12 points; p = .016 | same run: `stage10.H2_after_vs_never_paired` (paired RD 0.117, exact test) |
| The timing test (After vs. Before) | 10 points higher, interval includes zero | same run: `stage10.H1_after_vs_before_paired` (RD 0.10, 95% CI −0.046 to 0.208, p = .21) |
| Scorers with each other | 0.82 | same run: `stage8.scorers_role_blind.fleiss_kappa` (0.822, 3 scorers, 240 summaries) |
| Each scorer with themselves | 0.90; same answer on 96.8% of repeated summaries | `intra_rater_retest()` in `analysis/cave_analysis.py` on the same file (62 retests; κ 0.904; 96.77%) |
| AI judges with the scorers | 0.95 (κ), 0.98 (AC1); the judges' majority differed on 3 of 240 | same run: `stage8.judges_vs_human.majority` |
| Judge labels reach the same conclusions | | `cave_analysis.py --labels judge`: H2 rejected (8 vs 0, p = .008), H1 inconclusive |
| "Are you sure?" panels (AI-judge counts, exploratory) | errors out of 60 at steps 4, 6, 8 | [`exports/main/judging/judge_results.csv`](../exports/main/judging/judge_results.csv), `majority_errs_toward_expectation`, conditions `never`, `before_B`, `after_B`, worlds `underpowered` and `strong` |

To reproduce the analysis numbers:

```bash
cd analysis
python cave_analysis.py --export ../exports/main --labels-locked
python cave_analysis.py --export ../exports/main --labels-locked --labels judge
```

## Re-rendering v15

Tested with Python 3.11.18, ffmpeg 9.0.2, Pillow 13.0.0, NumPy 2.4.6 and SciPy 1.17.1, on macOS.

**The audio is not in the repo.** The narrated cut reads three ElevenLabs files, which `render-kit/placements_C.json` expects in an `audio/` folder at the repo root (`../../audio/` from `render-kit/`):

| File | Size | Used for |
|---|---|---|
| `narration_v2.mp3` | 3.7 MB | 42 of the 48 narration parts |
| `newlines_v1.mp3` | 0.55 MB | 5 parts (S4 P1, S10 P1 to P3, S11 P1) |
| `s9_p1_fix_alt.mp3` | 54 KB | S9 P1 |

The music-only cuts need no audio files: `sound.py` synthesizes every chord and chirp.

```bash
cd video/render-kit
pip install -r requirements.txt          # faster-whisper is only needed for transcribing new takes
python cavekit.py check placements_C.json # narration placements against the beat map
python cavekit.py video --version v15     # all three pictures and both music beds -> out/
python cavekit.py mix --version v15 --placements placements_C.json   # narrated cut and its .srt -> out/
```

A quick low-resolution check of any stretch, with sound:

```bash
python cavekit.py preview --start 0 --end 10 --placements placements_C.json
```

Nothing overwrites an earlier output: if `out/` already holds a version, pick a new `--version`.

The `_Narrated_CC` file is the narrated cut with `captions/…_Narrated_CC.srt` added as an English subtitle track; `_Narrated_Captioned` has the same captions burned in. Neither step is part of the kit.

### What is in `render-kit/`

| File | What it does |
|---|---|
| `cavekit.py` | entry point: `check`, `plan`, `beats`, `preview`, `video`, `mix` |
| `build_long.py` | renders the long cut segment by segment, applying the holds and the voice-led time map |
| `intro.py`, `opening.py`, `data_scene.py`, `story_draft.py`, `render.py`, `render4.py`, `grid.py` | the scenes |
| `sound.py` | the synthesized music bed |
| `narration.py`, `beats_def.py`, `export_beats.py` | the script by slide and part, and the beat map |
| `holds.json`, `retime.json` | narrated timing (holds on still frames; scene time to video time) |
| `holds_music.json` | music-only timing |
| `placements_C.json` | where each narration part sits (file, in/out, start, gain) |
| `assets/land-110m.json` | world land outline for the credits map (TopoJSON, Natural Earth 1:110m, public domain) |
| `fonts/` | Inter and Lora, both under the SIL Open Font License 1.1 (license texts included) |
