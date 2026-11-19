"""Draft of the data scene in three beats: the data, what the analysis can say, the bottom line. Standalone."""
import sys, os, math, subprocess
KIT = os.path.dirname(os.path.abspath(__file__))
if KIT not in sys.path: sys.path.insert(0, KIT)
os.environ.setdefault("SS", "2")
import opening as O
from opening import V, R, C, SF, F, ease, fade, win, partial, W, H, FPS, S, INK, SOFT, MUTED, FAINT, AFTER, NEVER, BEFORE
from PIL import Image
import grid as G
lerp = V.lerp
T = 20.0   # Phase D: 20 (was 18): the overclaim is read before it is struck
B1, B2, B3 = 0.0, 6.0, 12.0

def scene(c, t):
    R.F  # noqa
    G.note(c, "The experiment", fade(t, 0.1))
    G.title(c, "Simulated policy data with a known answer", fade(t, 0.2))
    # chart box: full width in beat 1, shrinks to the left in beat 2
    s = ease((t - B2) / 1.2)
    x0, x1 = lerp(200, 110, s), lerp(1720, 860, s)
    yt, yb = lerp(300, 330, s), lerp(850, 770, s)
    ca = 1 - 0.45 * ease((t - B3) / 0.8)
    lo, hi = 38.0, 58.0
    X = lambda w: x0 + (w - 6) / 16 * (x1 - x0)
    Y = lambda v: yb - (v - lo) / (hi - lo) * (yb - yt)
    a = fade(t, 0.3) * ca
    for v in (40, 45, 50, 55):
        c.line([(x0, Y(v)), (x1, Y(v))], FAINT, 1, a * 0.7)
        c.text((x0 - 14, Y(v)), str(v), F(24), MUTED, a, "rm")
    for w in (6, 10, 14, 18, 22):
        c.text((X(w), yb + 14), str(w), F(24), MUTED, a, "ma")
    c.text(((x0 + x1) / 2, yb + 52), "week", F(24), MUTED, a * (1 - s), "ma")
    c.text((x0, yt - 34), "service score (branch average)", F(24), MUTED, a, "lm")
    p = ease((t - 0.6) / 2.6)
    c.line(partial([(X(w), Y(v)) for w, v in zip(R.WEEKS, R.CONTROL)], p), NEVER, lerp(5, 4, s), ca)
    c.line(partial([(X(w), Y(v)) for w, v in zip(R.WEEKS, R.TREATED)], p), BEFORE, lerp(5, 4, s), ca)
    sa = fade(t, 2.4) * ca
    c.dash((X(14.5), yt + 20), (X(14.5), yb), SOFT, 2, sa * 0.8)
    c.text((X(14.5) + 12, yt + 30), "new procedure starts", F(26, "Medium"), SOFT, sa, "lm")
    la = fade(t, 1.0) * (1 - fade(t, B2 - 0.4, 0.4))
    c.line([(x1 - 860, yt - 34), (x1 - 810, yt - 34)], BEFORE, 5, la); c.text((x1 - 796, yt - 34), "20 branches that switched", F(26), SOFT, la, "lm")
    c.line([(x1 - 380, yt - 34), (x1 - 330, yt - 34)], NEVER, 5, la); c.text((x1 - 316, yt - 34), "14 that did not", F(26), SOFT, la, "lm")
    # beat 2: what a careful analysis can say
    pa = fade(t, B2 + 0.8) * (1 - fade(t, B3 - 0.3, 0.5))
    px0, px1, py = 1010, 1790, 640
    PX = lambda v: px0 + (v + 2) / 9 * (px1 - px0)
    c.text((px0, 300), "What a careful analysis can say", F(30, "SemiBold"), MUTED, pa)
    c.text((px0, 350), "+2.4 points", F(84, "Bold"), INK, pa)
    c.text((px0, 456), "95% interval: −0.7 to +5.5   ·   p = .12", F(30), SOFT, pa)
    c.line([(px0, py), (px1, py)], FAINT, 2, pa)
    for v in (-2, 0, 2, 4, 6):
        c.line([(PX(v), py - 7), (PX(v), py + 7)], MUTED, 1.5, pa)
        c.text((PX(v), py + 18), ("+" if v > 0 else "−" if v < 0 else "") + str(abs(v)), F(24), MUTED, pa, "ma")
    c.dash((PX(0), py - 100), (PX(0), py + 8), SOFT, 2, pa, 6, 6)
    c.text((PX(0), py - 128), "no effect", F(24), SOFT, pa, "ma")
    g = ease((t - B2 - 2.0) / 1.2)   # Phase C: interval grows at B2+2.0 (was +1.4)
    if g > 0:
        c.line([(PX(R.EST + (R.CI_LO - R.EST) * g), py - 48), (PX(R.EST + (R.CI_HI - R.EST) * g), py - 48)], BEFORE, 9, pa)
    c.dot(PX(R.EST), py - 48, 14, BEFORE, pa, outline=V.BG, ow=2)
    ta = fade(t, B2 + 3.6) * pa / max(pa, 1e-6) * pa
    xt = PX(R.TRUE_EFF)
    if ta > 0.004:
        c.d.polygon([(xt * S, (py + 60) * S), ((xt - 12) * S, (py + 84) * S), ((xt + 12) * S, (py + 84) * S)], fill=V.rgba(INK, ta))
    c.text((xt, py + 96), "effect built into the simulation: +2.0", F(24, "Medium"), SOFT, ta, "ma")
    # beat 3: the bottom line, two ways
    ba = fade(t, B3 + 0.3)
    bx0, bx1 = 1000, 1800
    c.text((bx0, 300), "THE BOTTOM LINE", F(24, "SemiBold"), MUTED, ba)
    wa = fade(t, B3 + 1.0)   # Phase C: overclaim at B3+1.0 (was +0.6); strike and correct +0.4 too
    c.rrect((bx0, 340, bx1, 510), 16, fill=(255, 255, 255), outline=FAINT, ow=1.5, a=wa, fa=0.04)
    c.text((bx0 + 30, 366), "Overclaims  ·  a real After bottom line from the study", F(24, "SemiBold"), MUTED, wa)
    c.text((bx0 + 30, 470), "“The new procedure improved service scores.”", SF(32, 600), SOFT, wa, "ls")   # Phase D: readable (was MUTED)
    st = ease((t - B3 - 4.0) / 0.6)   # Phase D: struck through 3 s after it appears (was B3+2.0)
    if st > 0:
        tw = c.tw("“The new procedure improved service scores.”", SF(32, 600))
        c.line([(bx0 + 30, 458), (bx0 + 30 + tw * st, 458)], V.CAVE, 3, wa)
    ra = fade(t, B3 + 4.8)   # Phase D: then 'Inconclusive' (was B3+2.8)
    c.rrect((bx0, 550, bx1, 770), 16, fill=(255, 255, 255), outline=SOFT, ow=2, a=ra, fa=0.07)
    c.text((bx0 + 30, 576), "Correct", F(24, "SemiBold"), SOFT, ra)
    c.text((bx0 + 30, 676), "Inconclusive.", SF(52, 700), INK, ra, "ls")
    c.text((bx0 + 30, 738), "Positive estimate, but the interval includes zero.", F(26), SOFT, ra, "ls")
    # captions
    c.cap(t, 0.6, B2 - 0.3, [("34 library branches. 20 switch to a new procedure.", SOFT)])
    c.cap2(t, B2 + 0.8, B3 - 0.3, [("A signal, not an answer:", INK)], [("the interval includes both no effect and a meaningful one.", SOFT)])
    c.cap2(t, B3 + 0.6, T + 1, [("The correct bottom line: ", SOFT), ("inconclusive", INK), (".", SOFT)], [("The answer a hopeful user least wants to hear.", SOFT)])
    na = fade(t, 0.5)
    nw = c.tw("sample simulated dataset", F(24, "Medium"))
    c.rrect((W // 2 - nw / 2 - 18, 170, W // 2 + nw / 2 + 18, 208), 19, fill=None, outline=MUTED, ow=1.5, a=na)
    c.text((W // 2, 189), "sample simulated dataset", F(24, "Medium"), SOFT, na, "mm")

def frame(t):
    bg, glow = R.bgs()
    img = bg.copy(); scene(C(img), t)
    return img.resize((W, H), Image.BOX)

if __name__ == "__main__":
    if sys.argv[1] == "stills":
        im = Image.new("RGB", (1920, 1080))
        for i, tt in enumerate((5.5, 11.5, 13.0, 17.5)): im.paste(frame(tt).resize((960, 540)), ((i % 2) * 960, (i // 2) * 540))
        im.save("data_sheet.jpg", quality=88)
    else:
        out = sys.argv[2]
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
        for f in range(int(T * FPS)): p.stdin.write(frame(f / FPS).tobytes())
        p.stdin.close(); p.wait()
