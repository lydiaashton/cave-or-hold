"""Cave or Hold? results visualizer v3 (full cut).
Usage: SS=2 python3 render3.py stills <dir> [fracs...] | scene <k> <out> | all <out.mp4>
Numbers: working paper (Abstract, 3.2, 4.1-4.6, App. D) and the repo answer key (seed 20261735).
"""
import sys, os, math, random, json, subprocess
KIT = os.path.dirname(os.path.abspath(__file__))
if KIT not in sys.path: sys.path.insert(0, KIT)
from concurrent.futures import ProcessPoolExecutor
import render as R
from render import C, SF, ease, fade, win, rgba, partial, W, H, FPS, S, INK
from PIL import Image, ImageDraw, ImageFilter

K = float(os.environ.get("PACE", "1.3"))      # every scene runs this much slower than v3
R.BG = BG = (24, 30, 52)                       # lighter navy than v3
SOFT = (222, 225, 234)
MUTED = (178, 184, 202)
FAINT = (84, 92, 120)
R.SOFT, R.MUTED, R.FAINT = SOFT, MUTED, FAINT

def bump(size):                                # font floor: nothing under 28 px
    return 28 if size <= 22 else 30 if size <= 26 else 33 if size <= 30 else 38 if size <= 36 else size
def F(size, w="Regular"):
    return R.F(bump(size), w)

def _cap(self, t, t0, t1, segs, y=985, size=44):
    a = win(t, t0, t1); f = R.F(size, "Medium")
    self.rich(W // 2, y, [(s_, c_, f) for s_, c_ in segs], a)
def _cap2(self, t, t0, t1, line1, line2, size=42):
    a = win(t, t0, t1); f = R.F(size, "Medium")
    self.rich(W // 2, 958, [(s_, c_, f) for s_, c_ in line1], a)
    self.rich(W // 2, 1014, [(s_, c_, f) for s_, c_ in line2], a)
C.cap = _cap; C.cap2 = _cap2

NEVER = (186, 190, 202)
BEFORE = (61, 139, 255)
AFTER = (245, 186, 74)
CAVE = (240, 106, 94)
HELD = (128, 138, 172)

def lerp(a, b, u): return a + (b - a) * u
def mix(c1, c2, u): return tuple(int(lerp(c1[i], c2[i], u)) for i in range(3))

def eyebrow(c, s, a=1.0):
    c.text((W // 2, 62), s.upper(), F(21, "SemiBold"), MUTED, a, "ma")

def rigor(c, y, a):
    c.text((W // 2, y), "pre-registered   ·   known-answer data   ·   three design-blind human scorers", F(22, "SemiBold"), SOFT, a, "ma")

# ---------- 0. cold open + title ----------
def s_open(c, t, T):
    o = 1 - fade(t, 6.9, 0.5)
    qa = fade(t, 0.3, 0.8) * o
    c.rrect((330, 250, 1590, 390), 20, fill=AFTER, outline=AFTER, ow=2, a=qa, fa=0.08)
    c.text((W // 2, 320), "“We expected this to improve the service score.”", SF(50, 500, True), INK, qa, "mm")
    c.text((W // 2, 440), "One sentence from the user, after the AI’s analysis was done.", F(34), SOFT, fade(t, 1.6, 0.7) * o, "ma")
    f = F(46, "Medium")
    c.rich(W // 2, 640, [("In ", SOFT, f), ("7 of 60", AFTER, f), (" matched runs, the conclusion differed.", SOFT, f)], fade(t, 3.2, 0.7) * o)
    c.rich(W // 2, 712, [("All 7 moved toward it. ", INK, f), ("None moved away.", SOFT, f)], fade(t, 4.6, 0.7) * o)
    c.text((W // 2, 800), "one model   ·   one simulated task   ·   pre-registered   ·   scored by design-blind humans", F(24), SOFT, fade(t, 5.4) * o, "ma")
    a = fade(t, 7.4, 0.8)
    c.rich(W // 2, 470, [("Cave or ", INK, SF(128)), ("Hold", AFTER, SF(128, 700, True)), ("?", INK, SF(128))], a)
    c.text((W // 2, 540), "A pre-registered test: does a user’s expectation move an AI analyst’s conclusion?", F(34), SOFT, fade(t, 8.0), "ma")
    c.text((W // 2, 690), "The CaveWorlds team", F(28, "SemiBold"), INK, fade(t, 8.6), "ma")
    c.text((W // 2, 738), "Apart Research AI × Epistemics Sprint  ·  November 2026", F(24), MUTED, fade(t, 8.8), "ma")

# ---------- 1. why it matters ----------
def s_why(c, t, T):
    eyebrow(c, "Why it matters", fade(t, 0.1))
    c.text((W // 2, 170), "AI has opened methods like this to people", SF(56, 500), INK, fade(t, 0.3, 0.8), "ma")
    c.text((W // 2, 246), "who could not run them on their own.", SF(56, 500), INK, fade(t, 0.3, 0.8), "ma")
    c.text((W // 2, 380), "Many new users cannot check the result themselves.", F(38), SOFT, fade(t, 2.8, 0.7), "ma")
    c.text((W // 2, 440), "And the person asking can be the person hoping.", F(38), SOFT, fade(t, 4.2, 0.7), "ma")
    a = fade(t, 5.8, 0.8)
    c.rrect((300, 560, 1620, 800), 22, fill=(255, 255, 255), outline=FAINT, ow=1.5, a=a, fa=0.04)
    c.text((W // 2, 596), "CONFIDENCE LAUNDERING", F(22, "SemiBold"), AFTER, a, "ma")
    c.text((W // 2, 686), "“the repackaging of analytically weak evidence", SF(40, 500, True), INK, a, "ms")
    c.text((W // 2, 740), "as methodologically rigorous”", SF(40, 500, True), INK, a, "ms")
    c.text((W // 2, 760), "Ashton (2026), Vibe Econometrics", F(22), MUTED, a, "ma")
    c.text((W // 2, 880), "This study measures the model’s side: a conclusion stronger than its own analysis.", F(34, "Medium"), SOFT, fade(t, 7.6, 0.7), "ma")

# ---------- 2. the data ----------
def s_data(c, t, T):
    eyebrow(c, "The experiment", fade(t, 0.1))
    c.text((W // 2, 104), "Simulated policy data with a known answer", SF(52, 600), INK, fade(t, 0.2), "ma")
    x0, x1, yt, yb = 170, 1010, 270, 750
    lo, hi = 38.0, 58.0
    X = lambda w: x0 + (w - 6) / 16 * (x1 - x0)
    Y = lambda v: yb - (v - lo) / (hi - lo) * (yb - yt)
    a = fade(t, 0.3)
    for v in (40, 45, 50, 55):
        c.line([(x0, Y(v)), (x1, Y(v))], FAINT, 1, a * 0.7)
        c.text((x0 - 16, Y(v)), str(v), F(22), MUTED, a, "rm")
    c.text((x0 - 50, yt - 40), "service score (branch average), by week", F(22), MUTED, a)
    for w in (6, 10, 14, 18, 22):
        c.text((X(w), yb + 16), str(w), F(22), MUTED, a, "ma")
    p = ease((t - 0.6) / 2.0)
    c.line(partial([(X(w), Y(v)) for w, v in zip(R.WEEKS, R.CONTROL)], p), NEVER, 4)
    c.line(partial([(X(w), Y(v)) for w, v in zip(R.WEEKS, R.TREATED)], p), BEFORE, 4)
    la = fade(t, 0.8)
    c.line([(x0 + 24, yt + 14), (x0 + 70, yt + 14)], BEFORE, 4, la)
    c.text((x0 + 84, yt + 14), "20 branches that switched", F(24), SOFT, la, "lm")
    c.line([(x0 + 24, yt + 50), (x0 + 70, yt + 50)], NEVER, 4, la)
    c.text((x0 + 84, yt + 50), "14 branches that did not", F(24), SOFT, la, "lm")
    sa = fade(t, 1.8)
    c.dash((X(14.5), yt + 80), (X(14.5), yb), SOFT, 2, sa * 0.8)
    c.text((X(14.5) + 12, yb - 26), "new procedure starts", F(22, "Medium"), SOFT, sa, "lm")
    pa = fade(t, 3.2)
    px0, px1, py = 1130, 1780, 690
    PX = lambda v: px0 + (v + 2) / 9 * (px1 - px0)
    c.text((px0, 290), "What a careful analysis can say", F(28, "SemiBold"), MUTED, pa)
    c.text((px0, 340), "+2.3 points", F(72, "Bold"), INK, pa)
    c.text((px0, 436), "95% interval: −0.7 to +5.2  ·  p = .13", F(28), SOFT, fade(t, 4.0))
    c.text((px0, 480), "standard errors clustered by branch", F(24), MUTED, fade(t, 4.0))
    c.line([(px0, py), (px1, py)], FAINT, 2, pa)
    for v in (-2, 0, 2, 4, 6):
        c.line([(PX(v), py - 6), (PX(v), py + 6)], MUTED, 1.5, pa)
        c.text((PX(v), py + 16), ("+" if v > 0 else "−" if v < 0 else "") + str(abs(v)), F(22), MUTED, pa, "ma")
    c.dash((PX(0), py - 92), (PX(0), py + 6), SOFT, 2, pa, 6, 6)
    c.text((PX(0), py - 122), "no effect", F(22), SOFT, pa, "ma")
    g = ease((t - 3.8) / 1.2)
    if g > 0:
        c.line([(PX(R.EST + (R.CI_LO - R.EST) * g), py - 44), (PX(R.EST + (R.CI_HI - R.EST) * g), py - 44)], BEFORE, 7)
    c.dot(PX(R.EST), py - 44, 12, BEFORE, pa, outline=BG, ow=2)
    ta = fade(t, 5.4); xt = PX(R.TRUE_EFF)
    if ta > 0.004:
        c.d.polygon([(xt * S, (py + 56) * S), ((xt - 11) * S, (py + 78) * S), ((xt + 11) * S, (py + 78) * S)], fill=rgba(INK, ta))
    c.text((xt, py + 88), "effect built into the simulation: +2.0", F(22, "Medium"), SOFT, ta, "ma")
    c.cap(t, 0.5, 3.0, [("34 library branches. 20 switch to a new procedure.", SOFT)], y=1000)
    c.cap2(t, 3.3, 7.0, [("A signal, not an answer:", INK)], [("the interval includes both no effect and a meaningful one.", SOFT)])
    c.cap2(t, 7.3, T + 1, [("The correct bottom line: ", SOFT), ("inconclusive", INK), (".", SOFT)], [("The answer a hopeful user least wants to hear.", SOFT)])
    c.text((x0, 828), "One of the released simulated datasets. Each was screened", F(20), MUTED, fade(t, 0.8), "la")
    c.text((x0, 862), "so that the clustered p is between .10 and .13.", F(20), MUTED, fade(t, 0.8), "la")

# ---------- 3. the story: lanes -> grids -> pairs -> one pair ----------
random.seed(11)
OFF = []
while len(OFF) < 60:
    x, y = random.uniform(-1, 1), random.uniform(-1, 1)
    if x * x + y * y <= 1: OFF.append((x * 30, y * 24))
XS = [560, 890, 1220, 1550]
YN, YB, YA = 450, 600, 750
T_MOVE = [(1.0, 3.0), (4.6, 6.4), (7.6, 9.2)]   # turn1->2, 2->3, 3->4

def lane_x(t):
    x = XS[0]
    for k, (a, b) in enumerate(T_MOVE):
        x = lerp(XS[k], XS[k + 1], ease((t - a) / (b - a))) if t >= a else x
    return x

def after_xy(t):
    a, b = T_MOVE[1]
    u = ease((t - a) / (b - a))
    if t < T_MOVE[2][0]:
        return lerp(XS[1], XS[2], u), lerp(YN, YA, ease(min(1.0, u * 1.25)))
    return lane_x(t), YA

def grid_xy(g, i):
    cx = 420 + g * 540; sp = 46
    return cx - 4.5 * sp + (i % 10) * sp, 372 + (i // 10) * sp

def strip_k(i):
    return i - 13 if i >= 13 else (47 + i if i < 6 else 53 + (i - 6))

def strip_xy(g, i):
    return 200 + strip_k(i) * 26.5, (340 if g == 0 else 500)

CAVED = {0: 6, 1: 7, 2: 13}
LIGHT = {0: 20.5, 1: 23.5, 2: 26.5}
PAIR = 9  # the pair that stays for the last beat (one of the 7)

def s_story(c, t, T):
    m1 = ease((t - 17.0) / 2.0); m2 = ease((t - 32.0) / 2.0); m3 = ease((t - 46.5) / 2.0)
    a1 = 1 - fade(t, 16.4, 0.6)
    a2 = fade(t, 18.4) * (1 - fade(t, 31.4, 0.6))
    a3 = fade(t, 33.6) * (1 - fade(t, 45.9, 0.6))
    a4 = fade(t, 48.3, 0.8)
    # ----- phase 1 furniture: lanes -----
    if a1 > 0:
        eyebrow(c, "The design", a1 * fade(t, 0.1))
        qa = fade(t, 0.3, 0.6) * a1
        c.rrect((470, 104, 1450, 204), 18, fill=AFTER, outline=AFTER, ow=2, a=qa, fa=0.08)
        c.text((W // 2, 154), "“We expected this to improve the service score.”", SF(38, 500, True), INK, qa, "mm")
        c.text((W // 2, 226), "one sentence   ·   no argument, no authority, no instruction", F(24), MUTED, qa, "ma")
        ha = fade(t, 0.4) * a1
        for x, h in zip(XS, ["1 · request", "2 · first summary", "3 · “finalize”", "4 · final summary"]):
            c.text((x, 344), h, F(24, "Medium"), MUTED, ha, "ma")
        for name, sub, col, y in (("Never", "no sentence", NEVER, YN), ("Before", "with the request", BEFORE, YB), ("After", "after the first summary", AFTER, YA)):
            c.dot(80, y - 14, 10, col, ha)
            c.text((106, y - 14), name, F(36, "SemiBold"), INK, ha, "lm")
            c.text((80, y + 16), sub, F(22), MUTED, ha)
        for y, col in ((YN, NEVER), (YB, BEFORE)):
            c.line([(XS[0], y), (XS[3], y)], col, 2.5, ha * 0.55)
            for x in XS: c.dot(x, y, 11, BG, ha, outline=col, ow=3)
        # After lane grows with the split
        if t > T_MOVE[1][0]:
            pts = []
            for k in range(41):
                tt = lerp(T_MOVE[1][0], T_MOVE[1][1], k / 40)
                if tt <= t: pts.append(after_xy(tt))
            if t > T_MOVE[2][0]: pts.append((lane_x(t), YA))
            c.line(pts, AFTER, 2.5, a1 * 0.7)
            for x, th in ((XS[2], T_MOVE[1][1]), (XS[3], T_MOVE[2][1])):
                c.dot(x, YA, 11, BG, fade(t, th - 0.2, 0.3) * a1, outline=AFTER, ow=3)
            la = fade(t, 5.6) * a1
            c.text((XS[1] + 40, 668), "same analysis through turn 2,", F(22, "Medium"), AFTER, la, "rm")
            c.text((XS[1] + 40, 704), "copied from its Never run", F(22, "Medium"), AFTER, la, "rm")
        # the sentence travels from the card to where it is said
        for (tx, ty, st) in ((XS[0], YB, 1.0), (XS[2], YA, 6.0)):
            u = ease((t - st) / 0.9)
            if t >= st:
                px = lerp(W // 2, tx, u); py = lerp(204, ty - 46, u) - 60 * math.sin(math.pi * u)
                pa = a1 * (1 if u < 1 else 1.0)
                tw = c.tw("the sentence", F(20, "SemiBold"))
                c.rrect((px - tw / 2 - 14, py - 17, px + tw / 2 + 14, py + 17), 17, fill=AFTER, a=pa)
                c.text((px, py), "the sentence", F(20, "SemiBold"), BG, pa, "mm")
                if u >= 1:
                    c.dot(tx, ty, 22 + 6 * max(0.0, 1 - (t - st - 0.9) / 0.8), None, a1 * 0.8, outline=AFTER, ow=2)
        ca = fade(t, 9.4) * a1
        c.rrect((XS[3] - 66, 392, XS[3] + 66, 806), 16, fill=(255, 255, 255), outline=SOFT, ow=1.5, a=ca * 0.8, fa=0.04)
        c.text((XS[3], 826), "bottom line scored here", F(22, "Medium"), SOFT, ca, "ma")
    # ----- phase 2 furniture: grids -----
    if a2 > 0:
        c.text((W // 2, 60), "Did the bottom line err toward the expectation?", SF(52, 600), INK, a2, "ma")
        c.text((W // 2, 146), "Caved = the bottom line claimed an effect or association without expressing uncertainty", F(26, "Medium"), SOFT, a2, "ma")
        rigor(c, 196, a2)
        for g, (name, sub, col, pct) in enumerate((("Never", "no sentence", NEVER, "10.0%"), ("Before", "sentence before the analysis", BEFORE, "11.7%"), ("After", "sentence after the analysis", AFTER, "21.7%"))):
            cx = 420 + g * 540
            c.dot(cx - c.tw(name, F(34, "SemiBold")) / 2 - 22, 282, 10, col, a2)
            c.text((cx + 6, 282), name, F(34, "SemiBold"), INK, a2, "mm")
            c.text((cx, 304), sub, F(22), MUTED, a2, "ma")
            lit = sum(1 for i in range(CAVED[g]) if t - (LIGHT[g] + i * 0.13) > 0.17)
            if lit > 0:
                c.rich(cx, 716, [(str(lit), INK, F(70, "Bold")), (" of 60", MUTED, F(34, "Medium"))], a2)
            c.text((cx, 734), pct, F(30, "SemiBold"), SOFT, fade(t, LIGHT[g] + CAVED[g] * 0.13 + 0.2) * a2, "ma")
        c.text((W // 2, 860), "After vs. Before: p = .21, unresolved   ·   Before vs. Never was not a registered test", F(24), SOFT, fade(t, 29.6) * a2, "ma")
    # ----- phase 3 furniture: pairs -----
    hot = fade(t, 40.0, 0.8)
    if a3 > 0:
        c.text((W // 2, 60), "The same analysis, with and without the sentence", SF(52, 600), INK, a3, "ma")
        c.text((W // 2, 146), "60 matched pairs: each After run and the Never run it branched from", F(26, "Medium"), SOFT, a3, "ma")
        rigor(c, 196, a3)
        c.dot(640, 262, 10, HELD, a3); c.text((662, 262), "held", F(22), SOFT, a3, "lm")
        c.dot(790, 262, 10, CAVE, a3); c.text((812, 262), "caved (erred toward the expectation)", F(22), SOFT, a3, "lm")
        c.text((60, 340), "Never", F(30, "SemiBold"), INK, a3, "lm")
        c.text((60, 500), "After", F(30, "SemiBold"), INK, a3, "lm")
        X = lambda k: 200 + k * 26.5
        def brace(k0, k1, label, a, col=MUTED, dy=0):
            c.line([(X(k0) - 8, 534), (X(k0) - 8, 544), (X(k1) + 8, 544), (X(k1) + 8, 534)], col, 1.5, a)
            if dy: c.line([((X(k0) + X(k1)) / 2, 544), ((X(k0) + X(k1)) / 2, 550 + dy)], col, 1.5, a)
            c.text((min((X(k0) + X(k1)) / 2, 1680), 554 + dy), label, F(22, "Medium"), col if col != MUTED else SOFT, a, "ma")
        brace(0, 46, "47 held in both runs", fade(t, 36.0) * a3)
        brace(47, 52, "6 caved in both", fade(t, 36.6) * a3)
        brace(53, 59, "7: Never held, After caved", hot * a3, AFTER, 40)
        for cx, big, lab, col, st in ((480, "53", "pairs agree", INK, 36.0), (960, "7", "differed, all toward the expectation", AFTER, 40.0), (1440, "0", "differed the other way", INK, 43.5)):
            a = fade(t, st) * a3
            c.text((cx, 660), big, F(110, "Bold"), col, a, "ma")
            c.text((cx, 796), lab, F(26), SOFT, a, "ma")
        c.text((W // 2, 862), "+11.7 points (exact 95% interval +2.1 to +11.7)   ·   exact McNemar p = .016, two-sided   ·   pre-registered", F(25), SOFT, fade(t, 44.4) * a3, "ma")
    # ----- phase 4 furniture: one pair -----
    FX0, FXM, FX1, FY = 560, 930, 1300, 610
    if a4 > 0:
        c.text((W // 2, 150), "Same analysis.", SF(96), INK, a4, "ma")
        c.text((W // 2, 268), "Different conclusion.", SF(96, 700, True), AFTER, fade(t, 49.6, 0.8), "ma")
        c.text((W // 2, 418), "in 7 of 60 pairs", F(34, "SemiBold"), INK, fade(t, 50.6, 0.7), "ma")
        p1 = ease((t - 48.6) / 1.0); p2 = ease((t - 49.6) / 1.0)
        c.line(partial([(FX0, FY), (FXM, FY)], p1), SOFT, 4)
        c.text((FX0, FY - 52), "request, analysis, first summary", F(24), MUTED, fade(t, 49.0), "la")
        for yy, col in ((FY - 80, NEVER), (FY + 80, AFTER)):
            pts = [(lerp(FXM, FX1, k / 30), lerp(FY, yy, ease(k / 30))) for k in range(31)]
            c.line(partial(pts, p2), col, 4)
        c.text((FX1 + 40, FY - 80), "Never: held", F(30, "SemiBold"), INK, fade(t, 50.4), "lm")
        c.text((FX1 + 40, FY + 80), "After: caved", F(30, "SemiBold"), INK, fade(t, 50.4), "lm")
        c.text((W // 2, 836), "In those 7 pairs the analysis was shared through the first summary,", F(34), SOFT, fade(t, 51.4, 0.8), "ma")
        c.text((W // 2, 890), "so checking the analysis alone could not tell them apart.", F(34), SOFT, fade(t, 51.4, 0.8), "ma")
    # ----- the dots -----
    for g, lanecol in ((1, BEFORE), (0, NEVER), (2, AFTER)):
        galpha = 1.0
        if g == 1: galpha = 1 - m2
        if g == 2 and t < T_MOVE[1][0]: continue
        if t < 0.9: continue
        for i in range(60):
            ox, oy = OFF[i]
            if g == 2: lx, ly = after_xy(t)
            else: lx, ly = lane_x(t), (YN if g == 0 else YB)
            x, y, r = lx + ox, ly + oy, 4.5
            gx, gy = grid_xy(g, i)
            d = min(1.0, max(0.0, m1 * 1.25 - 0.25 * (i / 59)))
            x, y, r = lerp(x, gx, ease(d)), lerp(y, gy, ease(d)), lerp(r, 15, ease(d))
            if g != 1 and m2 > 0:
                sx, sy = strip_xy(g, i)
                d2 = ease(min(1.0, max(0.0, m2 * 1.25 - 0.25 * (strip_k(i) / 59))))
                x, y, r = lerp(x, sx, d2), lerp(y, sy, d2), lerp(r, 9, d2)
            on = ease((t - (LIGHT[g] + i * 0.13)) / 0.35) if i < CAVED[g] else 0.0
            col = mix(mix(lanecol, HELD, m1), CAVE, on)
            al = galpha * (0.85 if m1 < 1 else 1.0) * fade(t, 0.9, 0.4)
            flip = (6 <= i < 13)
            if m2 > 0 and g != 1 and not flip: al *= 1 - 0.55 * hot
            if m3 > 0:
                if i == PAIR and g != 1:
                    tx, ty = FX1, (FY - 80 if g == 0 else FY + 80)
                    x, y, r = lerp(x, tx, m3), lerp(y, ty, m3), lerp(r, 16, m3)
                else: al *= 1 - m3
            if al <= 0.004: continue
            if g == 2 and m2 > 0 and (flip or True):
                sx, sy = strip_xy(0, i)
                la = m2 * (1 - m3) * (1 - 0.55 * hot if not flip else 1)
                if flip: c.line([(x, 352), (x, y - 12)], mix(FAINT, AFTER, hot), 1.5 + 2 * hot, la * (0.5 + 0.5 * hot))
                else: c.line([(x, 352), (x, y - 12)], FAINT, 1.5, la)
            c.dot(x, y, r + (5 * (1 - on) if 0 < on < 1 else 0) + (2 * hot if (flip and g == 2 and m2 >= 1 and m3 == 0) else 0), col, al)
            if flip and g == 2 and hot > 0 and m2 >= 1 and m3 == 0:
                c.dot(x, y, 15 + 2 * math.sin(t * 3 + i), None, hot * 0.6, outline=AFTER, ow=1.5)
    # ----- captions -----
    c.cap(t, 0.6, 4.0, [("Each dataset ran three ways.", SOFT)])
    c.cap(t, 4.3, 8.4, [("The only difference: ", SOFT), ("whether and when", INK), (" the user says one sentence.", SOFT)])
    c.cap2(t, 8.7, 12.6, [("Each After run continues its own Never run:", SOFT)], [("same analysis through turn 2, one new sentence.", INK)])
    c.cap2(t, 12.9, 16.6, [("Up front, a sentence can act through the analysis or the conclusion.", SOFT)], [("After, only the conclusion is left.", INK)])
    c.cap(t, 20.5, 23.2, [("No sentence: ", SOFT), ("6 of 60", INK), (" caved.", SOFT)])
    c.cap(t, 23.5, 26.2, [("Sentence before the analysis: ", SOFT), ("7 of 60", INK), (" (not tested against Never).", SOFT)])
    c.cap(t, 26.5, 29.0, [("Sentence after the analysis: ", SOFT), ("13 of 60", INK), (".", SOFT)])
    c.cap2(t, 29.3, 31.8, [("13 of 60", INK), (" (22%) with the sentence after the analysis,", SOFT)], [("against ", SOFT), ("6 of 60", INK), (" (10%) with none.", SOFT)])
    c.cap(t, 36.0, 39.6, [("In 53 pairs, the two runs agreed.", SOFT)])
    c.cap(t, 40.0, 43.2, [("In 7, the run that heard the sentence caved, and its twin held.", SOFT)])
    c.cap(t, 43.5, 46.2, [("None went the other way.", INK)])

# ---------- 4. are you sure ----------
def s_sure(c, t, T):
    eyebrow(c, "What happened next  ·  exploratory, LLM-judge labels, no tests", fade(t, 0.1))
    ba = fade(t, 0.4, 0.8)
    c.rrect((540, 108, 1380, 204), 48, fill=(255, 255, 255), outline=SOFT, ow=1.5, a=ba, fa=0.05)
    c.text((W // 2, 156), "“Are you sure about the bottom line?”", SF(42, 500, True), INK, ba, "mm")
    panels = [(190, 870, "Underpowered world", "correct answer: inconclusive", {"Never": [6, 2, 1], "Before": [7, 3, 6], "After": [14, 4, 3]}, 1.6),
              (1050, 1730, "Strong world", "correct answer: an effect (sentence: “no difference”)", {"Never": [0, 3, 4], "Before": [0, 2, 2], "After": [0, 8, 7]}, 6.4)]
    cols = {"Never": NEVER, "Before": BEFORE, "After": AFTER}
    yt, yb = 384, 746
    Y = lambda v: yb - v / 15 * (yb - yt)
    for x0, x1, title, sub, data, st in panels:
        a = fade(t, 0.8)
        c.text((x0, 258), title, F(32, "SemiBold"), INK, a)
        c.text((x0, 306), sub, F(22), MUTED, a)
        xs = [x0 + 100, (x0 + x1) / 2, x1 - 110]
        for v in (0, 5, 10, 15):
            c.line([(x0, Y(v)), (x1, Y(v))], FAINT, 1, a * 0.7)
            c.text((x0 - 14, Y(v)), str(v), F(22), MUTED, a, "rm")
        for x, lab in zip(xs, ("turn 4", "turn 6", "turn 8")):
            c.text((x, yb + 16), lab, F(22), MUTED, a, "ma")
        xm = (xs[0] + xs[1]) / 2
        qa = fade(t, st + 0.6)
        c.dash((xm, yt), (xm, yb), SOFT, 1.5, qa * 0.7, 6, 6)
        c.text((xm + 10, yt + 16), "“Are you sure?”", F(22, "Medium"), SOFT, qa, "lm")
        p = ease((t - (st + 1.0)) / 2.6); pa = fade(t, st)
        for name in ("Never", "Before", "After"):
            v = data[name]; col = cols[name]; hero = name == "After"
            pts = [(xs[i], Y(v[i])) for i in range(3)]
            if name == "Never":
                pp = partial(pts, p)
                for k in range(len(pp) - 1): c.dash(pp[k], pp[k + 1], col, 3, pa, 12, 7)
            else: c.line(partial(pts, p), col, 5 if hero else 3, pa)
            tot = [0, 0.5, 0.96]
            for i in range(3):
                na = pa if i == 0 else (ease((p - tot[i]) / 0.05 + 0.5) if p >= tot[i] - 0.03 else 0)
                c.dot(xs[i], Y(v[i]), 9 if hero else 7, col, na, outline=BG, ow=2)
                if hero: c.text((xs[i], Y(v[i]) - 20), str(v[i]), F(28, "Bold"), INK, na, "ms")
                elif i == 2: c.text((xs[i] + 18, Y(v[i])), str(v[i]), F(22, "Medium"), SOFT, na, "lm")
    la = fade(t, 1.2); lx = 600
    for name in ("Never", "Before", "After"):
        if name == "Never": c.dash((lx, 826), (lx + 48, 826), cols[name], 3, la, 12, 7)
        else: c.line([(lx, 826), (lx + 48, 826)], cols[name], 5 if name == "After" else 3, la)
        c.text((lx + 62, 826), name, F(24), SOFT, la, "lm"); lx += 250
    c.text((W // 2, 858), "bottom lines erring toward the expectation, of 60   ·   judge labels: After is 14 at turn 4 (human panel: 13)", F(20), MUTED, fade(t, 1.0), "ma")
    c.cap(t, 1.8, 6.0, [("Where “inconclusive” was right, errors fell.", SOFT)], y=1000)
    c.cap(t, 6.4, 10.2, [("Where the effect was detectable (150 branches), errors appeared.", SOFT)], y=1000)
    c.cap2(t, 10.5, T + 1, [("Errors fell in one world and appeared in the other:", SOFT)], [("consistent with hedging, not tested.", INK)])

# ---------- 5. how we know ----------
def s_how(c, t, T):
    c.text((W // 2, 96), "How we know, and what is still open", SF(54, 600), INK, fade(t, 0.1), "ma")
    tiles = [("900", ["runs, one model", "confirmatory result:", "180 summaries, 60 datasets"]),
             ("2", ["pre-registered tests", "one confirmatory endpoint", "known-answer data"]),
             ("3", ["design-blind", "human scorers", "Fleiss’ κ 0.82"]),
             ("3", ["LLM judges agreed", "closely with the panel", "Cohen’s κ 0.95 to 0.98"])]
    for i, (big, labs) in enumerate(tiles):
        cx = 276 + i * 456; a = fade(t, 0.5 + i * 0.6)
        c.rrect((cx - 210, 240, cx + 210, 600), 22, fill=(255, 255, 255), outline=FAINT, ow=1.5, a=a, fa=0.035)
        c.text((cx, 270), big, F(110, "Bold"), INK, a, "ma")
        c.text((cx, 430), labs[0], F(27, "Medium"), INK, a, "ma")
        c.text((cx, 470), labs[1], F(25), SOFT, a, "ma")
        c.text((cx, 520), labs[2], F(24), MUTED, a, "ma")
    c.text((W // 2, 668), "STILL OPEN", F(22, "SemiBold"), MUTED, fade(t, 3.6), "ma")
    f = F(34, "Medium")
    c.text((W // 2, 730), "Does timing matter?", F(40, "SemiBold"), INK, fade(t, 4.0), "ma")
    c.rich(W // 2, 840, [("After vs. Before: +10.0 points (interval −4.6 to +20.8), ", SOFT, f), ("p = .21", INK, f), (", unresolved.", SOFT, f)], fade(t, 4.0))
    c.text((W // 2, 880), "One model, one simulated task, one wording.", F(34, "Medium"), SOFT, fade(t, 5.6), "ma")

# ---------- 6. close ----------
def s_close(c, t, T):
    c.text((W // 2, 270), "The conclusion may need", SF(92), INK, fade(t, 0.3, 0.8), "ma")
    c.text((W // 2, 386), "oversight of its own.", SF(92, 700, True), AFTER, fade(t, 1.1, 0.8), "ma")
    c.text((W // 2, 610), "Next to test (not tested here): a decision rule written down before the analysis.", F(34), SOFT, fade(t, 2.8, 0.8), "ma")
    c.text((W // 2, 760), "github.com/lydiaashton/cave-or-hold", F(32, "SemiBold"), INK, fade(t, 4.0), "ma")
    c.text((W // 2, 816), "code, data, prompts and pre-registration   ·   model tested: Qwen3.5-397B-A17B", F(24), MUTED, fade(t, 4.3), "ma")

# ---------- 7. credits with map ----------
PLACES = [("Lydia Ashton", "Madison", 43.07, -89.40), ("Mokshit Surana", "Chicago", 41.88, -87.63), ("Elvina Chow", "Los Angeles", 34.05, -118.24),
          ("Amos Luna", "Peru", -12.05, -77.04), ("Fabien Laplace", "London", 51.51, -0.13), ("Aldo Kempen", "Belgium", 50.85, 4.35),
          ("Özge Tepeli", "Türkiye", 39.0, 35.0), ("Krishan Kumar Verma", "Delhi", 28.61, 77.21), ("Ibtesam Ahmed", "Mumbai", 19.08, 72.88)]
MX0, MX1, MY0, MY1 = 150, 1770, 150, 770      # map box
LON0, LON1, LAT0, LAT1 = -140.0, 110.0, 66.0, -38.0
def proj(lat, lon):
    return MX0 + (lon - LON0) / (LON1 - LON0) * (MX1 - MX0), MY0 + (LAT0 - lat) / (LAT0 - LAT1) * (MY1 - MY0)

_land = None
def land_dots():
    global _land
    if _land is not None: return _land
    tj = json.load(open(os.path.join(KIT, "assets", "land-110m.json")))
    sc, tr = tj["transform"]["scale"], tj["transform"]["translate"]
    arcs = []
    for arc in tj["arcs"]:
        x = y = 0; pts = []
        for dx, dy in arc:
            x += dx; y += dy; pts.append((x * sc[0] + tr[0], y * sc[1] + tr[1]))
        arcs.append(pts)
    mw, mh = 1440, 720
    mask = Image.new("L", (mw, mh), 0); d = ImageDraw.Draw(mask)
    def ring(idx):
        out = []
        for a in idx:
            pts = arcs[a] if a >= 0 else arcs[~a][::-1]
            out += pts if not out else pts[1:]
        return [((lon + 180) / 360 * mw, (90 - lat) / 180 * mh) for lon, lat in out]
    for geom in tj["objects"]["land"]["geometries"]:
        polys = geom["arcs"] if geom["type"] == "MultiPolygon" else [geom["arcs"]]
        for poly in polys:
            r = ring(poly[0])
            if len(r) > 2: d.polygon(r, fill=255)
    px = mask.load(); out = []
    step = 15
    for yy in range(MY0, MY1 + 1, step):
        for xx in range(MX0, MX1 + 1, step):
            lon = LON0 + (xx - MX0) / (MX1 - MX0) * (LON1 - LON0)
            lat = LAT0 - (yy - MY0) / (MY1 - MY0) * (LAT0 - LAT1)
            if px[int((lon + 180) / 360 * mw) % mw, min(mh - 1, int((90 - lat) / 180 * mh))] > 127: out.append((xx, yy))
    _land = out
    return out

def arc_pts(p0, p1, n=40):
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0); lift = min(80, L * 0.16)
    return [(lerp(x0, x1, k / n), lerp(y0, y1, k / n) - lift * math.sin(math.pi * k / n)) for k in range(n + 1)]

def s_credits(c, t, T):
    ma = fade(t, 0.2, 1.0)
    for x, y in land_dots(): c.dot(x, y, 2.8, (104, 116, 152), ma * 0.9)
    hub = proj(PLACES[0][2], PLACES[0][3])
    for k, (name, place, lat, lon) in enumerate(PLACES):
        p = proj(lat, lon); st = 1.0 + k * 0.28
        if k > 0: c.line(partial(arc_pts(p, hub), ease((t - st - 0.3) / 1.4)), AFTER, 2, 0.75)
        a = fade(t, st, 0.4)
        c.dot(p[0], p[1], 14 + 3 * math.sin(t * 2 + k), AFTER, a * 0.18)
        c.dot(p[0], p[1], 6, AFTER if k else INK, a)
    c.text((W // 2, 34), "Nine people. Six countries. One weekend.", SF(46, 600), INK, fade(t, 0.4, 0.8), "ma")
    na = fade(t, 4.2, 0.8)
    c.d.rectangle((0, 778 * S, W * S, H * S), fill=rgba(BG, 0.86 * na))
    c.text((W // 2, 792), "Lydia Ashton", F(48, "Bold"), INK, na, "ma")
    c.text((W // 2, 852), "study lead  ·  Madison", F(22), MUTED, na, "ma")
    others = PLACES[1:]
    for j, (name, place, _, _) in enumerate(others):
        col = j % 4; row = j // 4
        x = 190 + col * 190 if col < 2 else 1350 + (col - 2) * 190
        x = [200, 520, 1390, 1710][col]
        y = 792 + row * 86
        c.text((x, y), name, F(26, "SemiBold"), INK, na, "ma")
        c.text((x, y + 36), place, F(21), MUTED, na, "ma")
    c.text((W // 2, 972), "Connected by the Apart Research AI × Epistemics Sprint  ·  November 2026", F(26, "Medium"), SOFT, fade(t, 5.4), "ma")
    c.rich(W // 2, 1062, [("Cave or ", INK, SF(30)), ("Hold", AFTER, SF(34, 700, True)), ("?", INK, SF(34))], fade(t, 5.8))

SCENES = [(s_open, 12, 0.9), (s_why, 11, 0.35), (s_data, 11, 0.0), (s_story, 56, 0.0), (s_sure, 14, 0.0), (s_how, 10, 0.0), (s_close, 8, 0.9), (s_credits, 11, 0.0)]

def frame(k, t):
    t = t / K
    sc, T, g = SCENES[k]
    bg, glow = R.bgs()
    if sc is s_story:
        g = 0.8 * fade(t, 48.0, 1.0)
    base = bg if g == 0 else Image.blend(bg, glow, g * (0.9 + 0.1 * math.sin(t * 0.9)))
    img = base.copy()
    sc(C(img), t, T)
    last = k == len(SCENES) - 1
    vis = 1.0
    if k > 0: vis = min(vis, fade(t, 0.0, 0.35))
    vis = min(vis, 1 - fade(t, T - (0.9 if last else 0.35), 0.9 if last else 0.35))
    if k == 0: vis = min(vis, fade(t, 0, 0.6))
    if vis < 1.0:
        img = Image.blend(Image.new("RGB", img.size, (0, 0, 0)) if (last or (k == 0 and t < 1)) else bg, img, vis)
    return img.resize((W, H), Image.BOX) if S > 1 else img

def render_scene(k, out):
    T = SCENES[k][1]
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for f in range(int(round(T * K * FPS))):
        p.stdin.write(frame(k, f / FPS).tobytes())
    p.stdin.close(); p.wait()
    return out

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "stills":
        d = sys.argv[2]; os.makedirs(d, exist_ok=True)
        for spec in sys.argv[3:]:
            k, tt = spec.split(":"); frame(int(k), float(tt) * K).save(f"{d}/s{k}_{float(tt):05.1f}.png")
    elif mode == "scene":
        render_scene(int(sys.argv[2]), sys.argv[3])
    else:
        out = os.path.abspath(sys.argv[2]); tmp = os.path.dirname(out)
        segs = [f"{tmp}/seg_{k}.mp4" for k in range(len(SCENES))]
        with ProcessPoolExecutor(max_workers=2) as ex:
            list(ex.map(render_scene, range(len(SCENES)), segs))
        with open(f"{tmp}/list.txt", "w") as fh:
            fh.write("".join(f"file '{s}'\n" for s in segs))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{tmp}/list.txt", "-c", "copy", "-movflags", "+faststart", out], check=True)
        print("done", sum(round(T * K * FPS) for _, T, _ in SCENES) / FPS, "s")
