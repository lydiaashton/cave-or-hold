"""Burn captions into the narrated cut, in the caption band the slides keep free (grid.py: y 955 to 1080).

  python make_captioned.py <narrated.mp4> <captions.srt> <out.mp4>

The picture stays full size. Captions are Inter Medium, 36 px by default (CAP_SIZE; grid.py's caption style is 42 px),
centred; one line on baseline 1028, two lines on 1010 and 1052. The narrated cut keeps the band empty except for two
brief moments that do not meet a caption (S3's "illustration" tag, 40.0 to 42.5 s, with no caption up; the timing test's
"Inconclusive", which reaches y 955 only). The audio is copied unchanged. ffmpeg here has no subtitles/drawtext filter,
so the captions are drawn with Pillow on a transparent strip and overlaid.
"""
import os, re, sys, subprocess
from PIL import Image, ImageDraw, ImageFont
KIT = os.path.dirname(os.path.abspath(__file__))
VID, SRT, OUT = sys.argv[1:4]
if os.path.exists(OUT): sys.exit(f"{OUT} exists; not overwriting")
FPS, W, BAND_Y, BAND_H = 30, 1920, 955, 125
INK = (238, 238, 243, 255)                     # the kit's INK
SIZE = int(os.environ.get("CAP_SIZE", "36"))
ONE, TWO = 1028, (1010, 1052)            # set low in the band, clear of the timing test's "Inconclusive" (bottom ~y 958)
font = ImageFont.truetype(os.path.join(KIT, "fonts", "Inter-Medium.otf"), SIZE)

def ts(s):
    h, m, rest = s.split(":"); sec, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000
cues = []
for block in re.split(r"\n\s*\n", open(SRT, encoding="utf-8").read().strip()):
    lines = block.strip().splitlines()
    a, b = [ts(x.strip()) for x in lines[1].split("-->")]
    if len(lines[2:]) > 2: sys.exit(f"cue at {lines[1]} has more than two lines")
    cues.append((a, b, lines[2:]))
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VID], capture_output=True, text=True).stdout)
n = int(round(dur * FPS))

def strip(lines):
    im = Image.new("RGBA", (W, BAND_H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for ln, y in zip(lines, [ONE] if len(lines) == 1 else TWO):
        d.text((W / 2, y - BAND_Y), ln, font=font, fill=INK, anchor="ms")
    return im.tobytes()
empty = strip([]); cache = {}

p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-i", VID,
                      "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{BAND_H}", "-r", str(FPS), "-i", "-",
                      "-filter_complex", f"[0:v][1:v]overlay=0:{BAND_Y}:shortest=1:format=auto[v]",
                      "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                      "-c:a", "copy", "-r", str(FPS), OUT], stdin=subprocess.PIPE)
for f in range(n):
    t = (f + 0.5) / FPS
    cur = next((c for c in cues if c[0] <= t < c[1]), None)
    if cur is None: p.stdin.write(empty)
    else:
        k = tuple(cur[2])
        if k not in cache: cache = {k: strip(cur[2])}
        p.stdin.write(cache[k])
p.stdin.close(); p.wait()
print("wrote", OUT, "cues", len(cues), "frames", n)
