"""Draft of the new opening scene (long cut). Standalone; does not touch the video build."""
import sys, os, math, random, subprocess
KIT = os.path.dirname(os.path.abspath(__file__))
if KIT not in sys.path: sys.path.insert(0, KIT)
os.environ.setdefault("SS", "2")
import render4 as V
import render as R
from render import C, SF, ease, fade, win, rgba, partial, W, H, FPS, S, INK
F = V.F; SOFT, MUTED, FAINT, AFTER, BEFORE, NEVER = V.SOFT, V.MUTED, V.FAINT, V.AFTER, V.BEFORE, V.NEVER
from PIL import Image
lerp = V.lerp
GOOD = (92, 199, 150)

BEATS = [("Access", ["AI has opened the door to methods that used to need a trained analyst:", "regressions, causal estimates, policy evaluations."]),
         ("Decisions", ["Wider adoption could put evidence behind more decisions", "in agencies, businesses, and nonprofits."]),
         ("Stakes", ["What happens when the person asking has a stake in the answer", "and cannot verify the analysis?"]),
         ("Weak result, polished prose", ["A weak result can come back looking rigorous."])]
BL = 5.0   # seconds per beat
CLOCK = None   # set by the long-cut builder to the held (real) time
# keyword colors build from cool grey toward the amber of the expectation
KWCOL = [(170, 182, 210), (206, 204, 200), (238, 210, 150), (245, 186, 74)]
T = BL * 4 + 4.0   # beat 4 runs longer: correct claim, then the expectation turns it (Phase D: +1.5 s more for the inconclusive summary)

random.seed(5)
N = 54
CROWD = [(random.uniform(600, 1640), random.uniform(520, 810)) for _ in range(N)]
GROUPS = [(520, "agencies"), (960, "businesses"), (1400, "nonprofits")]
def group_xy(i):
    g = i % 3; k = i // 3
    ang = k * 2.4; rad = 27 * math.sqrt(k + 1)
    return GROUPS[g][0] + rad * math.cos(ang), 640 + rad * math.sin(ang) * 0.8
HERO = 4
HX, HY = 470, 670
BX0, BY0, BX1, BY1 = 780, 470, 1520, 880   # larger: the slide has room below the text
MINI_T = [44.387, 40.493, 40.109, 52.377, 46.834, 45.684, 41.94, 42.867, 50.527, 51.136, 47.242, 51.278, 51.399, 45.222, 42.082, 44.763, 48.906]
MINI_C = [46.817, 43.306, 46.03, 55.256, 52.178, 50.361, 46.033, 46.295, 52.071, 51.146, 47.235, 51.416, 54.686, 49.055, 46.137, 46.458, 47.431]

TURN = 19.5   # Phase D: 19.5 (was 18.0)   # the claim turns and the title changes from Stakes to Weak result
KB = [(0.45, BL + 0.05), (BL + 0.05, 2 * BL + 0.05), (2 * BL + 0.05, TURN), (TURN, BL * 4 + 4.0 + 1)]

def text_block(c, t):
    for k, (kw, lines) in enumerate(BEATS):
        a = win(t, KB[k][0], KB[k][1], 0.4)   # old line is gone before the new one starts
        if a <= 0: continue
        c.text((W // 2, 90), kw, SF(72, 600, k == 3), KWCOL[k], a, "ma")
        for j, ln in enumerate(lines):
            c.text((W // 2, 202 + j * 50), ln, F(36), SOFT, a, "ma")

def scene(c, t):
    text_block(c, t)
    b = t / BL
    # ---- beat 1: closed box of methods opens to a crowd ----
    box_a = 1 - fade(t, BL * 1 + 0.2, 0.8)
    if box_a > 0:
        c.rrect((90, 480, 490, 800), 20, fill=(255, 255, 255), outline=FAINT, ow=2, a=box_a * fade(t, 0.2), fa=0.05)
        c.text((290, 830), "trained analysts", F(28), MUTED, box_a * fade(t, 0.2), "ma")
        for j, m in enumerate(("regression", "causal estimate", "policy evaluation")):
            u = ease((t - (1.0 + j * 0.5)) / 1.6)
            x = lerp(290, 720 + j * 380, u); y = lerp(550 + j * 90, 455, u) - 70 * math.sin(math.pi * u)
            tw = c.tw(m, F(30, "SemiBold"))
            pa = box_a * fade(t, 0.3 + j * 0.15)
            c.rrect((x - tw / 2 - 20, y - 27, x + tw / 2 + 20, y + 27), 27, fill=BEFORE, a=pa, fa=0.9)
            c.text((x, y), m, F(30, "SemiBold"), (255, 255, 255), pa, "mm")
    # ---- the crowd: appears in beat 1, groups in beat 2, narrows to one in beat 3 ----
    for i, (cx, cy) in enumerate(CROWD):
        a = fade(t, 1.6 + i * 0.012, 0.5)
        gx, gy = group_xy(i)
        u2 = ease((t - BL * 1 - 0.3 - (i % 12) * 0.03) / 1.4)
        x, y = lerp(cx, gx, u2), lerp(cy, gy, u2)
        r = 7
        # beat 3: every group merges back into one person
        u3 = ease((t - BL * 2 - 0.2 - (0 if i == HERO else (i % 12) * 0.02)) / 1.2)
        x, y = lerp(x, HX, u3), lerp(y, HY, u3)
        if i == HERO:
            r = lerp(7, 26, u3)
        else:
            a *= 1 - fade(t, BL * 2 + 1.0, 0.45)
        person(c, x, y, r * 1.05, NEVER, a)
    # group labels and check marks
    ga = fade(t, BL * 1 + 1.6) * (1 - fade(t, BL * 2 + 0.1, 0.8))
    for gx, lab in GROUPS:
        c.text((gx, 795), lab, F(30, "SemiBold"), SOFT, ga, "ma")
        ca = fade(t, BL * 1 + 2.4) * ga   # all checks together
        c.line([(gx - 18, 492), (gx - 4, 507), (gx + 22, 474)], GOOD, 6, ca)
    # ---- beat 3: the stake ring and an opaque analysis box ----
    da = fade(t, BL * 2 + 2.4)   # Phase C: 12.4 (was 11.2), with the closed analysis box. the person asks: dashed line to the analysis
    if da > 0: c.dash((HX + 120, HY), (BX0 - 50, HY), SOFT, 2, da * 0.6, 10, 8)
    sa = fade(t, BL * 2 + 1.6)   # Phase C: 11.6 (was 16.0): the stake ring comes first, on "stake", as the voice says it
    if sa > 0:
        pulse = 1 + 0.08 * math.sin((CLOCK if CLOCK is not None else t) * 3)   # real clock: keeps pulsing through holds
        hy = HY - 26 * 1.05 * 1.15
        c.dot(HX, hy, 46 * pulse, None, sa, outline=AFTER, ow=6)
        c.dot(HX, hy, 72 * pulse, None, sa * 0.35, outline=AFTER, ow=2.5)
        c.text((HX, HY + 150), "a stake in the answer", F(30, "SemiBold"), AFTER, sa, "ma")
    ba = fade(t, BL * 2 + 2.4)   # Phase C: 12.4 (was 10.8); the closed analysis box enters after the stake ring
    if ba > 0:
        # wrap into a polished report in beat 4
        w4 = ease((t - 15.2) / 1.0)   # Phase C: 15.2 (was 13.8)   # lands on the results summary
        x0, y0, x1, y1 = lerp(BX0, BX0 - 40, w4), lerp(BY0, BY0 - 110, w4), lerp(BX1, BX1 + 40, w4), lerp(BY1, BY1 + 30, w4)
        c.rrect((x0, y0, x1, y1), 16, fill=(255, 255, 255), outline=FAINT if w4 < 0.5 else SOFT, ow=2, a=ba, fa=0.05 + 0.85 * w4)
        # weak chart inside, drawn in beat 4 before the wrap
        p = ease((t - 13.8) / 1.2)   # Phase C: 13.8 (was 12.4)   # the analysis runs
        cx0, cx1, cy0, cy1 = BX0 + 30, BX1 - 30, BY0 + 160, BY1 - 20
        Xm = lambda k: cx0 + k / 16 * (cx1 - cx0); Ym = lambda v: cy1 - (v - 38) / 20 * (cy1 - cy0)
        dark = w4 > 0.5
        lc1 = mix((96, 104, 130), BEFORE, 1 - w4); lc2 = mix((150, 156, 175), NEVER, 1 - w4)
        if p > 0:
            c.line(partial([(Xm(k), Ym(v)) for k, v in enumerate(MINI_C)], p), lc2, 3)
            c.line(partial([(Xm(k), Ym(v)) for k, v in enumerate(MINI_T)], p), lc1, 3)
        # fog = can't check (beat 3 only)
        fog = fade(t, BL * 2 + 2.4) * (1 - fade(t, 13.4, 0.4))   # Phase C: 12.4 / 13.4 (was 10.8 / 12.0)
        if fog > 0:
            c.rrect((BX0, BY0, BX1, BY1), 16, fill=V.BG, outline=SOFT, ow=2, a=fog, fa=0.92)   # outlined, so the hidden analysis reads as a box
            c.text(((BX0 + BX1) / 2, (BY0 + BY1) / 2 - 24), "the analysis", F(42, "Medium"), SOFT, fog, "mm")
            c.text(((BX0 + BX1) / 2, (BY0 + BY1) / 2 + 30), "cannot be verified", F(36), MUTED, fog, "mm")
        # report: first the correct claim with its caveat; then the user's expectation arrives and the claim turns
        if w4 > 0:
            ha = ease((w4 - 0.6) / 0.4)   # the report text arrives once the card has turned light
            TS = TURN                     # the moment the claim turns
            m_old = 1 - ease((t - TS) / 0.4); m_new = ease((t - TS - 0.45) / 0.5)   # old claim fully gone before the new one appears
            ink = (24, 30, 52)
            c.text((x0 + 44, y0 + 40), "RESULTS SUMMARY", F(24, "SemiBold"), (110, 116, 140), ha)
            # one sentence; only the verb turns ("increased" -> "improved") and the caveat goes
            pre = "The service score "; fw = SF(48, 700)
            wx = x0 + 44 + c.tw(pre, fw)
            c.text((x0 + 44, y0 + 100), pre, fw, ink, ha)
            c.text((wx, y0 + 100), "increased", fw, ink, ha * m_old)
            c.text((wx, y0 + 100), "improved", fw, ink, ha * m_new)
            c.text((x0 + 44, y0 + 156), "with the new procedure.", fw, ink, ha)
            c.text((x0 + 44, y0 + 216), "Inconclusive: the interval includes zero.", F(28, "Medium"), (96, 104, 130), ha * m_old)
            ia = fade(t, TS + 1.2)
            c.rrect((x0, y1 + 18, x0 + 200, y1 + 60), 21, fill=None, outline=MUTED, ow=1.5, a=ia)
            c.text((x0 + 100, y1 + 39), "illustration", F(22, "Medium"), MUTED, ia, "mm")
    # drawn last, so it sits on top of the card. The user's expectation: an amber pill comes out of the ring, travels the dashed line and lands at the card's edge
    pa = fade(t, TURN - 1.3, 0.3) * (1 - fade(t, TURN + 0.15, 0.35))   # Phase D: tied to TURN (was 16.7)
    if pa > 0:
        g = ease((t - (TURN - 1.1)) / 1.0)
        pul = 1 + 0.07 * math.sin((CLOCK if CLOCK is not None else t) * 6)
        ptw = c.tw("user’s expectation", F(30, "SemiBold")); hw, hh = (ptw / 2 + 18) * pul, 24 * pul
        _wx = BX0 - 40 + 44 + c.tw("The service score ", SF(48, 700)) + c.tw("increased", SF(48, 700)) / 2
        px = lerp(HX, _wx, g); py = lerp(HY - 26 * 1.05 * 1.15, BY0 - 110 + 128, g) - 60 * math.sin(math.pi * g)   # lands on "increased", which then turns
        c.rrect((px - hw, py - hh, px + hw, py + hh), hh, fill=AFTER, a=pa)
        c.text((px, py), "user’s expectation", F(30, "SemiBold"), V.BG, pa, "mm")

def person(c, x, y, r, col, a):
    """A small person: head plus shoulders. r is the head radius."""
    if a <= 0.004: return
    c.dot(x, y - r * 1.15, r, col, a)
    w = r * 1.9; h = r * 2.1
    c.d.chord(((x - w) * S, (y + r * 0.35) * S, (x + w) * S, (y + r * 0.35 + 2 * h) * S), 180, 360, fill=rgba(col, a))

def mix(c1, c2, u): return tuple(int(lerp(c1[i], c2[i], u)) for i in range(3))

def frame(t):
    bg, glow = R.bgs()
    img = bg.copy(); scene(C(img), t)
    v = min(fade(t, 0, 0.6), 1 - fade(t, T - 0.4, 0.4))
    if v < 1: img = Image.blend(Image.new("RGB", img.size, (0, 0, 0)), img, v)
    return img.resize((W, H), Image.BOX)

if __name__ == "__main__":
    if sys.argv[1] == "stills":
        for k, tt in enumerate((4.4, 9.4, 14.4, 19.2)):
            frame(tt).save(f"beat{k+1}.png")
    else:
        out = sys.argv[2]
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
        for f in range(int(T * FPS)): p.stdin.write(frame(f / FPS).tobytes())
        p.stdin.close(); p.wait()
