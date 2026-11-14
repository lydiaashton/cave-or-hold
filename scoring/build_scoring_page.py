"""Build one scoring page from a folder of summary .txt files.

Usage:  python3 build_scoring_page.py <folder of .txt> "<batch label>" <output.html> --round 1|2|3 [--endpoint <URL>]

Three rounds, three pages. Scorers do them in this order and never see which turn a summary came from.

  --round 1   Bottom line. Every turn-4 summary in the human-scored set. Four questions:
              claim, uncertainty, emphatic words, next steps.   (default)
  --round 2   Whole summary. A fixed random subset of round 1. The claim again (a consistency
              check), then reason why, certainty as a percentage, no harm.
  --round 3   Bottom line and verdict. Turns 6 and 8. The four round-1 questions plus one on
              the final verdict.

--endpoint <Apps Script web app URL>: answers are also sent to the study Google Sheet as the
scorer works (see README). Without it the page saves in the browser and offers a download.

Suggested file names: Scoring_Round1_BottomLine.html, Scoring_Round2_WholeSummary.html,
Scoring_Round3_BottomLineAndVerdict.html.
"""
import sys, os, re, json, glob
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
data = json.dumps({"batch": batch, "whole": whole, "batch2": batch2, "endpoint": endpoint, "items": items}, ensure_ascii=False).replace("</", "<\\/")
tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.html"), encoding="utf-8").read()
assert "/*DATA*/" in tpl
open(out, "w", encoding="utf-8").write(tpl.replace("/*DATA*/", data))
others = sorted(x for x in os.listdir(folder) if not x.endswith(".txt"))
print(f"{len(items)} summaries, round {rnd} ({"whole summary, 4 questions" if whole else ("bottom line and verdict, 5 questions" if batch2 else "bottom line, 4 questions")}) -> {out} ({os.path.getsize(out)//1024} KB); "
      f"analysis header removed from {stripped}; other files ignored: {others}; online capture: {'on' if endpoint else 'off'}")
