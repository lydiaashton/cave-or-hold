"""Draft of the new intro sequence: hook, title, problem, definition card. Standalone."""
import sys, os, math, subprocess
KIT = os.path.dirname(os.path.abspath(__file__))
if KIT not in sys.path: sys.path.insert(0, KIT)
os.environ.setdefault("SS", "2")
import opening as O
from opening import V, R, C, SF, F, ease, fade, win, partial, W, H, FPS, S, INK, SOFT, MUTED, FAINT, AFTER, NEVER
from PIL import Image
CAVE, HELD = V.CAVE, V.HELD
lerp = V.lerp
NEVER_RUN = (125, 132, 153)   # Never condition grey
AFTER_RUN = (102, 173, 255)   # After condition blue

HOOK_SHIFT = 2.6   # seconds of request card before the fork scene starts
SHIFT = HOOK_SHIFT
REQ = "“Please analyze the data and draft a summary for the board.”"

HEAD_Y = 850   # headline baseline: one line under the fork (Phase D, final)
LAND_F, LAND_E = 3.9, 4.3   # S1 (Phase D): the expectation steps aside 2.9-3.4, finalize drops 3.4-3.9, the expectation lands 3.8-4.3; they never overlap
def _hook_split(c, t, T):
    """The fork: the analysis line, the two messages gliding down together (finalize for both,
    the user's expectation onto the After branch only), held and caved, then the headline."""
    out = 1 - fade(t, T - 0.6, 0.5)
    X0, XM, X1, Y = 380, 940, 1460, 520   # raised so the fork and the headline below it balance
    FW = c.tw("finalize the summary", F(26, "SemiBold")); FX = XM - FW / 2 - 18   # the shared turn-3 request sits at the fork
    # the quote card, then it shrinks into the "user’s expectation" pill and drops onto the fork
    sA = ease((t - 2.9) / 0.5)                       # the expectation steps aside (right) and shrinks to its pill
    mf = ease((t - 3.4) / (LAND_F - 3.4))            # then finalize drops onto the fork
    sC = ease((t - 3.8) / (LAND_E - 3.8))            # then the expectation lands on the After branch
    m = sA
    tw = c.tw("user’s expectation", F(26, "SemiBold"))
    # the sentence comes from below and lands straight on the After branch as it grows out of the fork
    _u = 0.37; PX, PY = lerp(XM, X1, _u), lerp(Y, Y + 140, ease(_u))
    bx0, by0, bx1, by1 = 430, 194, 1490, 322   # the expectation: large, below the small finalize card
    px0, py0, px1, py1 = PX - tw / 2 - 14, PY - 18, PX + tw / 2 + 14, PY + 18
    ax, ay = 1430, 250                                # aside: right of the finalize card's path
    aside = (ax - tw / 2 - 14, ay - 18, ax + tw / 2 + 14, ay + 18)
    big = (bx0, by0, bx1, by1); land = (px0, py0, px1, py1)
    box = tuple(lerp(lerp(b, a_, sA), l_, sC) for b, a_, l_ in zip(big, aside, land))
    # the analysis line and the fork
    p1 = ease((t - 1.0) / 1.4)   # Phase D: the line grows with 'Same analysis.' (was 0.6)
    c.line(partial([(X0 - 24, Y), (XM, Y)], p1), SOFT, 5, out)   # starts at 'the request' pill's right edge, so the two connect
    c.text((X0, Y - 44), "the analysis", F(26), MUTED, fade(t, 1.2) * out, "la")
    p2 = ease((t - 3.2) / 1.0)         # the versions part as the two messages arrive
    for yy, col in ((Y - 140, NEVER_RUN), (Y + 140, AFTER_RUN)):
        pts = [(lerp(XM, X1 - 20, k / 30), lerp(Y, yy, ease(k / 30))) for k in range(31)]   # stops at the circle edge
        c.line(partial(pts, p2), col, 5, out)
    # the finalize card: same glide as the expectation card, lands at the fork (both versions get it)
    gcol = (178, 186, 206)
    fb0 = (430, 108, 1250, 180); fb1 = (FX - FW / 2 - 14, Y - 18, FX + FW / 2 + 14, Y + 18)
    fbox = tuple(lerp(a, b, mf) for a, b in zip(fb0, fb1))
    fca = fade(t, 0.2, 0.6) * out * 0.85   # quieter than the expectation
    c.rrect(fbox, 18, fill=gcol, outline=gcol, ow=2, a=fca, fa=lerp(0.06, 1.0, ease((mf - 0.3) / 0.7)))
    fq = fca * (1 - ease((mf - 0.15) / 0.5))
    if fq > 0:
        fs = max(8, int(round(34 * (fbox[2] - fbox[0]) / (fb0[2] - fb0[0]))))
        c.text(((fbox[0] + fbox[2]) / 2, (fbox[1] + fbox[3]) / 2), "“Please finalize the summary for the board.”", SF(fs, 500, True), INK, fq, "mm")
    fp = fca * ease((mf - 0.55) / 0.45)
    if fp > 0:
        c.text(((fbox[0] + fbox[2]) / 2, (fbox[1] + fbox[3]) / 2), "finalize the summary", F(26, "SemiBold"), V.BG, fp, "mm")
    ca = fade(t, 0.2, 0.6) * out
    c.rrect(box, lerp(18, 18, m), fill=AFTER, outline=AFTER, ow=2, a=ca, fa=lerp(0.08, 1.0, ease((m - 0.3) / 0.7)))
    qa = ca * (1 - ease((m - 0.15) / 0.5))
    if qa > 0:
        qs = max(8, int(round(46 * (box[2] - box[0]) / (bx1 - bx0))))
        c.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), "“We expected this to improve the service score.”", SF(qs, 500, True), INK, qa, "mm")
    pa = ca * ease((m - 0.55) / 0.45)
    if pa > 0:
        c.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), "user’s expectation", F(26, "SemiBold"), V.BG, pa, "mm")
    ea = fade(t, 4.6, 0.5) * out
    c.dot(X1, Y - 140, 18, None, ea, outline=NEVER_RUN, ow=4); c.text((X1 + 36, Y - 140), "?", F(38, "SemiBold"), INK, ea, "lm")
    c.dot(X1, Y + 140, 18, None, ea, outline=AFTER_RUN, ow=4); c.text((X1 + 36, Y + 140), "?", F(38, "SemiBold"), INK, ea, "lm")
    f = R.F(46, "Medium"); f2 = R.F(46, "SemiBold")
    # headline under the fork (Phase D, final): one line, landing on "Can"; the narration says "Same data. Same analysis." on its own
    HB = 2.9                           # as the cards start to glide
    L2 = [("Can ", INK, f2), ("one sentence from the user", AFTER, f2), (" change the conclusion?", INK, f2)]
    # right-aligned: the centre of the final "?" sits at x = X1, on the vertical line through the two circles
    q_w = c.tw("?", f2)
    x = X1 + q_w / 2 - sum(c.tw(s_, ff) for s_, _, ff in L2)
    for s_, col, ff in L2:
        c.text((x, HEAD_Y), s_, ff, col, fade(t, HB, 0.45) * out, "ls"); x += c.tw(s_, ff)

def hook(c, t, T):
    """Hook: the request card becomes 'the request' at the start of the line, then the fork plays."""
    out = 1 - fade(t, T - 0.6, 0.5)
    X0, Y = 380, 520
    # 1) the request card, then it shrinks into a "the request" pill at the start of the line
    m = ease((t - 1.5) / 0.9)
    tw = c.tw("the request", F(26, "SemiBold"))
    PX, PY = X0 - 24 - tw / 2 - 14, Y   # the request sits on the line, just before the analysis starts
    bx0, by0, bx1, by1 = 400, 140, 1520, 214   # same text size as the finalize card
    px0, py0, px1, py1 = PX - tw / 2 - 14, PY - 18, PX + tw / 2 + 14, PY + 18
    box = (lerp(bx0, px0, m), lerp(by0, py0, m), lerp(bx1, px1, m), lerp(by1, py1, m))
    ca = fade(t, 0.1, 0.5) * out
    col = (178, 186, 206)
    c.rrect(box, 18, fill=col, outline=col, ow=2, a=ca, fa=lerp(0.06, 0.9, ease((m - 0.3) / 0.7)))
    qa = ca * (1 - ease((m - 0.15) / 0.5))
    if qa > 0:
        qs = max(8, int(round(34 * (box[2] - box[0]) / (bx1 - bx0))))
        c.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), REQ, SF(qs, 500, True), INK, qa, "mm")
    pa = ca * ease((m - 0.55) / 0.45)
    if pa > 0:
        c.text((PX, PY), "the request", F(26, "SemiBold"), V.BG, pa, "mm")
    # 2) the hook, shifted (sentence pill sits on the After branch)
    if t > SHIFT:
        _hook_split(c, t - SHIFT, T - SHIFT)


TITLE_SUB = 0.8                         # Phase F: the subtitle lands on its first word ("How")
TITLE_TEAM, TITLE_SPRINT = 2.4, 2.6   # then the team lines fade in, once the subtitle is up (Phase G: the grey line is gone; times unchanged)
TEAM_Y = 650                          # Phase G: the team name sits 66 px under the subtitle (title to subtitle: 58 px)
TITLE_DY = 12                         # Phase G: shift of the whole block, set so it is centred on screen
def title(c, t, T):
    a = fade(t, 0.2, 0.8) * (1 - fade(t, T - 0.5, 0.5))
    out = 1 - fade(t, T - 0.5, 0.5); dy = TITLE_DY
    c.rich(W // 2, 420 + dy, [("Cave", CAVE, SF(128, 700, True)), (" or Hold?", INK, SF(128))], a)   # coral = caved; amber is only the user’s expectation
    # Phase F: the subtitle, two lines broken after "Confidence", white and larger than the old subtitle
    sa = fade(t, TITLE_SUB, 0.8) * out; fs = F(50, "Medium")
    c.text((W // 2, 518 + dy), "How a User’s Expectation Launders Confidence", fs, INK, sa, "ms")
    c.text((W // 2, 582 + dy), "into an AI Analyst’s Conclusion", fs, INK, sa, "ms")
    _ta = fade(t, TITLE_TEAM) * out; _f = F(28, "SemiBold")   # team name: Cave in coral, Worlds in amber
    _seg = [("The ", INK), ("Cave", CAVE), ("Worlds", AFTER), (" team", INK)]
    _x = W // 2 - sum(c.tw(s_, _f) for s_, _ in _seg) / 2
    for s_, col_ in _seg:
        c.text((_x, TEAM_Y + dy), s_, _f, col_, _ta, "la"); _x += c.tw(s_, _f)
    c.text((W // 2, TEAM_Y + 48 + dy), "A pre-registered experiment  ·  Apart Research AI × Epistemics Sprint  ·  November 2026", F(24), MUTED, fade(t, TITLE_SPRINT) * out, "ma")

def problem(c, t, T):
    O.scene(c, t)

def definition(c, t, T):
    a = fade(t, 0.3, 0.8) * (1 - fade(t, T - 0.5, 0.5))
    c.rrect((160, 345, 1760, 775), 26, fill=(255, 255, 255), outline=FAINT, ow=2, a=a, fa=0.05)
    c.text((W // 2, 448), "CONFIDENCE LAUNDERING", F(84, "SemiBold"), AFTER, a, "mm")   # centered between box top and the definition
    c.text((W // 2, 597), "When a claim comes to look", SF(68, 600), INK, a, "ms")
    c.text((W // 2, 687), "better supported than it is.", SF(68, 600), INK, a, "ms")

SEQ = [(hook, 7.5 + HOOK_SHIFT, 0.0), (title, 5.0, 0.9), (problem, O.T, 0.0), (definition, 8.0, 0.35)]

def frame(k, t):
    fn, T, g = SEQ[k]
    bg, glow = R.bgs()
    base = bg if g == 0 else Image.blend(bg, glow, g * (0.9 + 0.1 * math.sin(t * 0.9)))
    img = base.copy(); fn(C(img), t, T)
    if k == 0 and t < 0.5: img = Image.blend(Image.new("RGB", img.size, (0, 0, 0)), img, fade(t, 0, 0.5))
    return img.resize((W, H), Image.BOX)

if __name__ == "__main__":
    out = sys.argv[1]
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for k, (fn, T, g) in enumerate(SEQ):
        for f in range(int(round(T * FPS))): p.stdin.write(frame(k, f / FPS).tobytes())
    p.stdin.close(); p.wait()
