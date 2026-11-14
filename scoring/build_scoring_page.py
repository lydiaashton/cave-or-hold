"""Build one scoring page from a folder of summary .txt files.

Usage:  python3 build_scoring_page.py <folder of .txt> "<batch label>" <output.html> --round 1|2|3 [--endpoint <URL>] [--tab NAME] [--no-download]

Three rounds, three pages. Scorers do them in this order and never see which turn a summary came from.

  --round 1   Bottom line. Every turn-4 summary in the human-scored set. Four questions:
              claim, uncertainty, emphatic words, next steps.   (default)
  --round 2   Whole summary. A fixed random subset of round 1. The claim again (a consistency
              check), then reason why, certainty as a percentage, no harm.
  --round 3   Bottom line and verdict. Turns 6 and 8. The four round-1 questions plus one on
              the final verdict.

--endpoint <Apps Script web app URL>: answers are also sent to the study Google Sheet as the
scorer works (see README). Without it the page saves in the browser and offers a download.

--tab NAME: the Google Sheet tab the answers go to (default round1, round2 or round3 by round).
Use it to keep calibration apart, e.g. --tab cal_practice, --tab cal_check1.

--order <order.csv>: the main-run pages. The export's scoring/round<r>/order.csv (position,
block, summary_id). Summaries appear block by block in that order, the same for every scorer,
shuffled only within a block, and the page shows which block the scorer is in. Every file in
the folder must be in the order and the reverse. Without it (calibration) the whole page is
shuffled per scorer.

--no-download: no download buttons (final scoring; calibration pages keep them as a backup).
Needs --endpoint, since the sheet is then the only way answers come back.

Every page blocks copying the summary and codebook text and pasting into the notes box.

Suggested file names: Scoring_Round1_BottomLine.html, Scoring_Round2_WholeSummary.html,
Scoring_Round3_BottomLineAndVerdict.html.
"""
import sys, os, re, json, glob, csv
argv = list(sys.argv[1:])
rnd = "1"
if "--round" in argv:
    i = argv.index("--round"); rnd = argv[i + 1]; del argv[i:i + 2]
if "--whole-summary" in argv:      # older spelling of --round 2
    rnd = "2"; argv.remove("--whole-summary")
if "--batch2" in argv:             # older spelling of --round 3
    rnd = "3"; argv.remove("--batch2")
if rnd not in ("1", "2", "3"):
    sys.exit("--round must be 1, 2 or 3")
whole, batch2 = rnd == "2", rnd == "3"
args = argv
endpoint = ""
if "--endpoint" in args:
    i = args.index("--endpoint"); endpoint = args[i + 1]; del args[i:i + 2]
    if not endpoint.startswith("https://script.google.com/macros/s/") or not endpoint.endswith("/exec"):
        sys.exit("--endpoint must be the Apps Script web app URL: https://script.google.com/macros/s/.../exec")
tab = ""
if "--tab" in args:
    i = args.index("--tab"); tab = args[i + 1]; del args[i:i + 2]
    if not re.fullmatch(r"[A-Za-z0-9_]{1,30}", tab):
        sys.exit("--tab must be 1-30 letters, digits or underscores, e.g. cal_practice")
order_file = ""
if "--order" in args:
    i = args.index("--order"); order_file = args[i + 1]; del args[i:i + 2]
nodownload = "--no-download" in args
if nodownload:
    args.remove("--no-download")
    if not endpoint:
        sys.exit("--no-download needs --endpoint: without the sheet, the download is the only way answers come back.")
folder, batch, out = args[0], args[1], args[2]
MARK = "----- Summary -----"
items, stripped = [], 0
for f in sorted(glob.glob(os.path.join(folder, "*.txt"))):
    t = open(f, encoding="utf-8").read()
    t = re.sub(r"^﻿?Summary ID:.*\n+", "", t).strip()
    if MARK in t:
        t = t.split(MARK, 1)[1].strip()
        stripped += 1
    if re.match(r"(Estimate|95% CI|p-value)\s*:", t):
        sys.exit(f"{f}: starts with analysis numbers and has no '{MARK}' marker; page not built.")
    items.append({"id": os.path.basename(f)[:-4], "text": t})
if not items:
    sys.exit(f"No .txt files found in {folder}")
if order_file:
    with open(order_file, encoding="utf-8-sig", newline="") as f:
        order = list(csv.DictReader(f))
    by_id = {it["id"]: it for it in items}
    listed = [r["summary_id"] for r in order]
    if len(set(listed)) != len(listed):
        sys.exit(f"{order_file}: a summary is listed twice")
    if set(listed) != set(by_id):
        sys.exit(f"{order_file} and {folder} do not hold the same summaries: "
                 f"{len(set(listed) - set(by_id))} listed but missing, {len(set(by_id) - set(listed))} not listed")
    order.sort(key=lambda r: int(r["position"]))
    items = [dict(by_id[r["summary_id"]], block=int(r["block"])) for r in order]
    blocks = [it["block"] for it in items]
    if blocks != sorted(blocks) or sorted(set(blocks)) != list(range(1, max(blocks) + 1)):
        sys.exit(f"{order_file}: blocks must run 1, 2, 3 ... in position order")
data = json.dumps({"batch": batch, "whole": whole, "batch2": batch2, "endpoint": endpoint, "nodownload": nodownload, "tab": tab, "items": items}, ensure_ascii=False).replace("</", "<\\/")
tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.html"), encoding="utf-8").read()
assert "/*DATA*/" in tpl
open(out, "w", encoding="utf-8").write(tpl.replace("/*DATA*/", data))
others = sorted(x for x in os.listdir(folder) if not x.endswith(".txt"))
print(f"{len(items)} summaries, round {rnd} ({"whole summary, 4 questions" if whole else ("bottom line and verdict, 5 questions" if batch2 else "bottom line, 4 questions")}) -> {out} ({os.path.getsize(out)//1024} KB); "
      f"analysis header removed from {stripped}; other files ignored: {others}; online capture: {'on' if endpoint else 'off'}; download button: {'off' if nodownload else 'on'}; sheet tab: {tab or ('round2' if whole else ('round3' if batch2 else 'round1'))}")
