"""Burn the narrated cut's .srt into a captioned version, in the v15 _Narrated_Captioned layout.

  CAP_SIZE=40 CAP_BASE=1040 python make_captioned.py <narrated.mp4> <captions.srt> <out.mp4>   (v17 settings)

Layout (measured from v15's _Narrated_Captioned): the picture scaled to 85% (1632x918) at x = 144, y = 0, on #10152A;
captions in the band below, Inter Regular, 35 px by default (CAP_SIZE), centred; last line on baseline 1049, earlier lines 1.28 x size above.
The audio is copied from the narrated cut unchanged. ffmpeg here has no subtitles/drawtext filter, so the caption band
is drawn with Pillow and piped in as a second video stream.
"""
import os, re, sys, subprocess
from PIL import Image, ImageDraw, ImageFont
KIT = os.path.dirname(os.path.abspath(__file__))
VID, SRT, OUT = sys.argv[1:4]
if os.path.exists(OUT): sys.exit(f"{OUT} exists; not overwriting")
FPS, W, BAND_Y, BAND_H = 30, 1920, 918, 162
BG = (16, 21, 42); INK = (240, 242, 250)
SIZE = int(os.environ.get("CAP_SIZE", "35"))            # v15/v16 look: 35 px
BASE = int(os.environ.get("CAP_BASE", "1049"))           # baseline of the last line (v15/v16: 1049)
LINE = round(SIZE * 1.28)                                # line spacing (45 px at 35 px)
font = ImageFont.truetype(os.path.join(KIT, "fonts", "Inter-Regular.otf"), SIZE)

def ts(s):
    h, m, rest = s.split(":"); sec, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000
cues = []
for block in re.split(r"\n\s*\n", open(SRT, encoding="utf-8").read().strip()):
    lines = block.strip().splitlines()
    a, b = [ts(x.strip()) for x in lines[1].split("-->")]
    cues.append((a, b, lines[2:]))
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VID], capture_output=True, text=True).stdout)
n = int(round(dur * FPS))

def band(lines):
    im = Image.new("RGB", (W, BAND_H), BG); d = ImageDraw.Draw(im)
    bases = [BASE - LINE * (len(lines) - 1 - i) for i in range(len(lines))]
    for ln, y in zip(lines, bases):
        d.text((W / 2, y - BAND_Y), ln, font=font, fill=INK, anchor="ms")
    return im.tobytes()
empty = band([]); cache = {}

p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-i", VID,
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{BAND_H}", "-r", str(FPS), "-i", "-",
                      "-filter_complex", f"[0:v]scale=1632:918:flags=lanczos,pad=1920:1080:144:0:color=0x10152A[p];[p][1:v]overlay=0:{BAND_Y}:shortest=1[v]",
                      "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                      "-c:a", "copy", "-r", str(FPS), OUT], stdin=subprocess.PIPE)
ci = 0
for f in range(n):
    t = (f + 0.5) / FPS
    cur = next((c for c in cues if c[0] <= t < c[1]), None)
    if cur is None: p.stdin.write(empty)
    else:
        k = tuple(cur[2])
        if k not in cache: cache = {k: band(cur[2])}
        p.stdin.write(cache[k])
p.stdin.close(); p.wait()
print("wrote", OUT, "cues", len(cues), "frames", n)
