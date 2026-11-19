"""Assemble the long cut: intro (intro.py), data scene (data_scene.py), then design through credits (story_draft.py)."""
import sys, os, subprocess, math, json
KIT = os.path.dirname(os.path.abspath(__file__))
if KIT not in sys.path: sys.path.insert(0, KIT)
os.environ.setdefault("SS", "2")
from concurrent.futures import ProcessPoolExecutor
WORK = os.environ.get("WORK", os.path.join(KIT, "work")); os.makedirs(WORK, exist_ok=True)
from PIL import Image
import opening as O, intro as I, data_scene as DS, story_draft as D
AMBER = (255, 200, 87)
for m in (O, I, DS): m.AFTER = AMBER
O.KWCOL[3] = D.INK   # S3 heading: white; amber is only the user’s expectation
O.GOOD = (26, 140, 92)            # Kolibri emerald for the check marks
FPS = D.FPS
names = [s[0].__name__ for s in D.SCENES]
TAIL = ["s_story", "s_scoring", "s_timing", "s_sure", "s_close", "s_how", "s_next", "s_credits"]

def data_frame(t, T=DS.T):
    img = DS.frame(t)
    v = min(1.0, t / 0.35, (T - t) / 0.35)
    if v < 1:
        bg, _ = D.R.bgs(); img = Image.blend(bg.resize(img.size), img, max(0.0, v))
    return img

SEGS = [("intro", k, I.SEQ[k][1]) for k in range(len(I.SEQ))] + [("data", 0, DS.T)] + [("story", names.index(n), D.SCENES[names.index(n)][1] * D.K) for n in TAIL]

# Reading holds: (time in the segment's own unheld timeline, seconds to hold). The frame freezes while the text stays up.
K = D.K
# Reading holds live in holds.json: {"holds": {"<kind>:<key> <label>": [[scene_time, seconds], ...]}}.
# Story scenes use scene time (the numbers in story_draft.py); it is multiplied by K here.
_HJ = json.load(open(os.path.join(KIT, os.environ.get("HOLDS_FILE", "holds.json"))))["holds"]
HOLDS = {}
for _key, _lst in _HJ.items():
    _kind, _rest = _key.split(":", 1); _k = _rest.split(" ", 1)[0]
    _k = int(_k) if _kind != "story" else _k
    HOLDS[(_kind, _k)] = [(a * (K if _kind == "story" else 1.0), d) for a, d in _lst]
# Voice-led timing (Phase C) lives in retime.json: for each segment, a piecewise-linear map from the held timeline
# (seconds of the segment's own animation after the holds above; story scenes already multiplied by K) to output seconds.
# It moves animation events onto the narration's words. Segments without an entry run as before.
_RF = os.path.join(KIT, os.environ.get("RETIME_FILE", "retime.json"))
RETIME = json.load(open(_RF))["segments"] if os.path.exists(_RF) and os.environ.get("RETIME_FILE", "") != "none" else {}
class Timeline(list):
    """The holds of one segment, plus its retime map (or None)."""
    warp = None
def holds_for(kind, k):
    key = (kind, names[k]) if kind == "story" else (kind, k)
    tl = Timeline(sorted(HOLDS.get(key, [])))
    m = RETIME.get(f"{kind}:{names[k] if kind == 'story' else k}")
    if m: tl.warp = [tuple(p) for p in m["map"]]
    return tl
def _interp(x, pts, i, j):
    if x <= pts[0][i]: return pts[0][j] + (x - pts[0][i])
    for a, b in zip(pts, pts[1:]):
        if x <= b[i]:
            return a[j] if b[i] == a[i] else a[j] + (x - a[i]) * (b[j] - a[j]) / (b[i] - a[i])
    return pts[-1][j] + (x - pts[-1][i])
def unhold(r, hs):
    """Final (output) time in a segment -> time in its unheld timeline."""
    if getattr(hs, "warp", None): r = _interp(r, hs.warp, 1, 0)
    acc = 0.0
    for at, d in hs:
        if r < at + acc: return r - acc
        if r < at + acc + d: return at
        acc += d
    return r - acc
def held_time(u, hs):
    """Unheld time -> final (output) time (for cues and sound)."""
    v = u + sum(d for at, d in hs if at < u)
    return _interp(v, hs.warp, 0, 1) if getattr(hs, "warp", None) else v
def seg_len(kind, k, T):
    hs = holds_for(kind, k); v = T + sum(d for _, d in hs)
    return hs.warp[-1][1] + (v - hs.warp[-1][0]) if hs.warp else v
SEGS_RAW = SEGS
SEGS = [(kind, k, seg_len(kind, k, T)) for kind, k, T in SEGS]

def render(job):
    idx, (kind, k, T) = job
    out = os.path.join(WORK, f"long_{idx:02d}.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    hs = holds_for(kind, k)
    for f in range(int(round(T * FPS))):
        t = unhold(f / FPS, hs)
        O.CLOCK = D.CLOCK = f / FPS   # pulses run on real time, so holds don't freeze them
        img = I.frame(k, t) if kind == "intro" else data_frame(t) if kind == "data" else D.frame(k, t)
        p.stdin.write(img.tobytes())
    p.stdin.close(); p.wait(); return out

if __name__ == "__main__":
    starts, acc = {}, 0.0
    for kind, k, T in SEGS:
        starts[(kind, k)] = acc; acc += round(T * FPS) / FPS
    print("total", round(acc, 1), "s")
    print({f"{a}:{b}": round(v, 2) for (a, b), v in starts.items()})
    if len(sys.argv) > 1 and sys.argv[1] == "plan": sys.exit()
    import multiprocessing as mp
    with ProcessPoolExecutor(int(os.environ.get("JOBS", str(os.cpu_count() or 2))), mp_context=mp.get_context("spawn")) as ex:   # same behaviour on Mac and Linux
        outs = list(ex.map(render, list(enumerate(SEGS))))
    lst = os.path.join(WORK, "long_list.txt"); out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WORK, "long_video.mp4")
    open(lst, "w").write("".join(f"file '{o}'\n" for o in outs))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out], check=True)
