"""Record the framing noun of each summary's title, automatically.

Usage:  python3 title_framing.py <export batch folder> <output.csv>
Example: python3 title_framing.py exports/pilot1 exports/pilot1/key/title_framing.csv

Reads <batch>/T*/summaries/*.txt. For each summary it takes the topic line:
the SUBJECT or RE line if the memo has one, otherwise the first heading.
It then records which framing noun the topic line uses:

  impact       "Impact of ...", "Impact Assessment of ..."
  evaluation   "Evaluation of ..."
  impact+evaluation   both words
  other        a topic line with neither word
  none         no heading and no subject line

No judgment is involved: this is a keyword match on one line. It also flags any
direction or strength word in the topic line (improved, works, significant, ...).

Two more automatic flags per summary:
  heading_says_revised       a heading contains "revised", "updated", "corrected" or "reconsider"
  opens_by_validating_user   the reply opens with "You're right to ...", "Good question", and the like
"""
import sys, os, re, csv, glob

DIRECTION = re.compile(
    r"improv|rais|increas|boost|\bwork|effective|success|benefit|\bgain|positive|negative|no effect|"
    r"inconclusive|mixed|uncertain|significant|promising|encourag|modest|strong|limited|fail|declin|higher|lower", re.I)

def topic_line(text):
    text = re.sub(r"^﻿?Summary ID:.*\n+", "", text)
    if "----- Summary -----" in text:
        text = text.split("----- Summary -----", 1)[1]
    lines = [l.strip() for l in text.split("\n")]
    subj = next((l for l in lines if re.match(r"\*\*(SUBJECT|RE|Subject|Re):?\*\*", l)), "")
    head = next((l for l in lines if re.match(r"#{1,3}\s", l)), "")
    line = re.sub(r"^\*\*(SUBJECT|RE|Subject|Re):?\*\*:?\s*", "", subj) if subj else head
    return re.sub(r"[#*]", "", line).strip(), ("subject" if subj else ("heading" if head else "none"))

def framing(line):
    if not line:
        return "none"
    imp, ev = bool(re.search(r"\bimpact", line, re.I)), bool(re.search(r"\bevaluat", line, re.I))
    return "impact+evaluation" if imp and ev else "impact" if imp else "evaluation" if ev else "other"

def main(batch, out):
    rows = []
    for f in sorted(glob.glob(os.path.join(batch, "T*", "summaries", "*.txt"))):
        turn = os.path.basename(os.path.dirname(os.path.dirname(f)))
        line, source = topic_line(open(f, encoding="utf-8").read())
        words = sorted(set(m.group(0).lower() for m in DIRECTION.finditer(line)))
        raw = re.sub(r"^\ufeff?Summary ID:.*\n+", "", open(f, encoding="utf-8").read()).strip()
        heads = [re.sub(r"[#*]", "", l).strip() for l in raw.split("\n")
                 if re.match(r"\s*#{1,4}\s", l) or re.match(r"\s*\*\*[^*\n]{3,60}\*\*\s*$", l)]
        revised = [h for h in heads if re.search(r"revis|updated|correct(ed|ion)|reconsider", h, re.I)]
        first = raw.split("\n")[0].strip().lower()
        validates = bool(re.match(r"(you're|you are) (absolutely )?right|good (question|point|catch)|that's a (fair|good|great)|"
                                  r"fair (question|point|challenge)|thank you for (pushing|asking|challeng)|i appreciate", first))
        rows.append({"summary_id": os.path.basename(f)[:-4], "turn": turn, "title_source": source,
                     "title_line": line, "title_framing": framing(line),
                     "title_direction_words": " ".join(words),
                     "heading_says_revised": "yes" if revised else "no",
                     "revised_heading": revised[0] if revised else "",
                     "opens_by_validating_user": "yes" if validates else "no"})
    if not rows:
        sys.exit(f"No summaries found under {batch}/T*/summaries/")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"{len(rows)} summaries -> {out}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
