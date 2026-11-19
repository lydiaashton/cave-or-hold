"""Music bed for the long cut (no narration).: no constant tone. A soft, decaying chord at each slide change, cycling D, Bm, G, A;
a hummingbird call when the user's sentence first appears; and a brighter chord when the 7 pairs light up."""
import sys, numpy as np, wave, os
KIT = os.path.dirname(os.path.abspath(__file__))
if KIT not in sys.path: sys.path.insert(0, KIT)
import build_long as B
SR = 48000
starts, acc = [], 0.0
for kind, k, T in B.SEGS:
    starts.append((kind, k, acc)); acc += round(T * B.FPS) / B.FPS
TOTAL = acc; n = int(SR * TOTAL); x = np.zeros(n)
def note(t0, f, amp, decay=2.0):
    i0 = int(t0 * SR); m = min(int(5.0 * SR), n - i0); tt = np.arange(m) / SR
    x[i0:i0 + m] += amp * (np.sin(2 * np.pi * f * tt) + 0.18 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt / decay) * np.clip(tt / 0.08, 0, 1) ** 2
def chord(t0, freqs, amp=0.05, decay=2.0):
    for j, f in enumerate(freqs): note(t0 + j * 0.10, f, amp, decay)
def chirp(t0, f0, f1, dur, amp):
    i0 = int(t0 * SR); m = int(dur * SR); tt = np.arange(m) / SR
    ph = 2 * np.pi * np.cumsum(f0 + (f1 - f0) * tt / dur) / SR
    x[i0:i0 + m] += amp * np.sin(ph) * np.sin(np.pi * tt / dur) ** 2
# voiced an octave up: phone speakers cannot play notes below ~200 Hz cleanly and rattle on them
CH = [(293.66, 440.0, 587.33), (246.94, 369.99, 493.88), (196.0 * 1.5, 392.0, 493.88), (220.0, 329.63, 440.0, 554.37)]
CODA = ("s_how", "s_next", "s_credits")   # silent closing slides: soft chirps instead of chords
coda = []
changes = []
for kind, k, t0 in starts:
    if kind == "story" and B.names[k] in CODA:
        coda.append(t0); continue
    changes.append(t0 + 0.15)
    if kind == "story" and B.names[k] == "s_story":
        hs = B.holds_for(kind, k)
        L7 = B.D.S7A_LEN                              # S7a sits at scene 17.0; later story times shift by its length
        for scene_t in (17.0, 17.0 + L7, 32.0 + L7, 46.5 + L7):   # design -> S7a -> grids -> caving test -> one pair
            changes.append(t0 + B.held_time(scene_t * B.K, hs))
        pairs = t0 + B.held_time((40.0 + L7) * B.K, hs)      # the 7 pairs light up
if os.environ.get("CHORDS_AT_VOICE_GAPS"):
    # narrated cut (Phase E): each slide-change chord sounds in the gap, 0.1 s after the old slide's last word,
    # so the music fills the change before the next line starts
    import json as _json
    _pl = sorted(_json.load(open(os.environ["CHORDS_AT_VOICE_GAPS"]))["items"], key=lambda it: it["at"])
    _gaps = [a["at"] + a["out"] - a["in"] + 0.1 for a, b in zip(_pl, _pl[1:]) if a["slide"] != b["slide"]]
    _last = _pl[-1]["at"] + _pl[-1]["out"] - _pl[-1]["in"]
    changes = [min(changes)] + _gaps + [c for c in changes if c > _last + 0.5]
for i, tc in enumerate(sorted(changes)):
    chord(tc, CH[i % 4])
chord(pairs, (440.0, 554.37, 659.26), 0.05, 1.6)
import intro as _I
_hk = B.holds_for("intro", 0)   # S1 starts at 0; its scene times go through its holds and retime map
chord(B.held_time(5.5, _hk) - 0.5, CH[2], 0.025, 2.5)   # soft G chord 0.5 s before the two cards start gliding (scene 5.5 s)
_tl = B.held_time(_I.HOOK_SHIFT + _I.LAND_E, _hk) + 0.35   # chirp: just after the user's expectation has landed on the After branch
chirp(_tl, 3200, 4200, 0.06, 0.03); chirp(_tl + 0.09, 3600, 4600, 0.05, 0.024)
# coda: one soft chirp as each box or person appears (scene times from story_draft)
CODA_EVENTS = {"s_how": [0.3, 2.8],                              # STRENGTHS box, LIMITATIONS box
               "s_next": [0.8, 2.0, 3.2],                        # the three question boxes
               "s_credits": [0.6 + k * 0.2 for k in range(9)]}   # each person's dot on the map
rng = np.random.default_rng(7)
for kind, k, t0 in starts:
    if kind != "story" or B.names[k] not in CODA_EVENTS: continue
    hs = B.holds_for("story", k)
    for u in CODA_EVENTS[B.names[k]]:
        t = t0 + B.held_time(u * B.D.K, hs) + 0.05
        f = rng.uniform(3200, 3800); a = rng.uniform(0.006, 0.009)
        chirp(t, f, f + 900, 0.05, a)
from scipy.signal import butter, sosfilt
x = sosfilt(butter(4, 200, 'highpass', fs=SR, output='sos'), x)   # nothing low enough to rattle a phone speaker
x = x / np.max(np.abs(x)) * 0.5
w = wave.open(sys.argv[1], "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((np.stack([x, x], 1) * 32767).astype("<i2").tobytes()); w.close()
print("coda", [round(c, 1) for c in coda]); print("total", round(TOTAL, 2), "chords at", [round(c, 1) for c in sorted(changes)], "pairs", round(pairs, 1))
