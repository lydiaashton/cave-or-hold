"""One entry point for the Cave or Hold? long cut.

  python cavekit.py beats                         beat map for the current holds  -> beats.md, beats.json
  python cavekit.py plan                          slide timings and words per second
  python cavekit.py check  placements.json        check narration placements against the beat map (no rendering)
  python cavekit.py preview --start 90 --end 120 [--placements placements.json] [--captions]
                                               quick low-resolution clip with sound -> out/preview_<start>-<end>.mp4
  python cavekit.py video  --version v10          render both cuts with the music bed only -> out/
  python cavekit.py mix    --version v10 --placements placements.json
                                               add the narration to already-rendered v10 video -> out/

Nothing here edits audio takes or overwrites an existing version: every output gets a new name.
Timing is changed only in holds.json (see README.md).
"""
import os, sys, json, argparse, subprocess, tempfile, wave
KIT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(KIT, "out"); WORK = os.path.join(KIT, "work")
os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
PY = sys.executable
SR = 48000
NAME = "LydiaAshton_CaveOrHold_LongCut"

def run(cmd, env=None):
    print("  $", " ".join(cmd) if isinstance(cmd, list) else cmd, flush=True)
    subprocess.run(cmd, check=True, env=env)

def ffmpeg(*args):
    run(["ffmpeg", "-y", "-loglevel", "error", *args])

def env(**kw):
    e = dict(os.environ); e.update({k: str(v) for k, v in kw.items()}); return e

def refuse_overwrite(path):
    if os.path.exists(path):
        sys.exit(f"{path} already exists. Pick a new --version; nothing was overwritten.")

# ---------- audio helpers ----------
def read_audio(path, start=0.0, end=None):
    """Any audio file -> mono float32 at 48 kHz (via ffmpeg)."""
    import numpy as np
    args = ["ffmpeg", "-loglevel", "error", "-ss", str(start)]
    if end is not None: args += ["-to", str(end)]
    args += ["-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    raw = subprocess.run(args, check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype="<f4").astype("float64")

def write_wav(path, x, channels=2):
    import numpy as np
    x = np.clip(x, -1, 1)
    data = np.stack([x] * channels, 1) if channels == 2 else x
    w = wave.open(path, "wb"); w.setnchannels(channels); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((data * 32767).astype("<i2").tobytes()); w.close()

def loudnorm(src, dst, I, tp=-1.5):
    """Two-pass loudness normalisation (measure, then apply exactly)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", src, "-af", f"loudnorm=I={I}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    m = json.loads(r[r.rindex("{"):r.rindex("}") + 1])
    af = (f"loudnorm=I={I}:TP={tp}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    ffmpeg("-i", src, "-af", af, "-ar", str(SR), dst)

# ---------- placements ----------
def load_placements(path):
    p = json.load(open(path)); base = os.path.dirname(os.path.abspath(path))
    for it in p["items"]:
        it["path"] = it["file"] if os.path.isabs(it["file"]) else os.path.normpath(os.path.join(base, it["file"]))
    return p

def check_placements(path, quiet=False):
    """Compare placements with the beat map. Returns a list of problems (empty = all good)."""
    run([PY, os.path.join(KIT, "export_beats.py")])
    beats = json.load(open(os.path.join(KIT, "beats.json"))); R = beats["rules"]
    p = load_placements(path)
    slides = {s["slide"]: s for s in beats["slides"]}
    probs, rows = [], []
    items = sorted(p["items"], key=lambda it: it["at"])
    prev_end = None
    for it in items:
        if not os.path.exists(it["path"]): probs.append(f"missing file: {it['file']}"); continue
        if it.get("join_previous"):                                   # a pickup spliced onto the previous piece with a crossfade
            s = slides.get(it["slide"]); end = it["at"] + it["out"] - it["in"]
            if prev_end is None or abs(it["at"] - (prev_end - it["join_previous"])) > 0.005:
                probs.append(f"{it['slide']} {it['parts']}: join_previous piece must start {it['join_previous']} s before the previous piece ends")
            if s and end > s["end"] - R["slide_tail"]: probs.append(f"{it['slide']} {it['parts']}: runs {end - (s['end'] - R['slide_tail']):.2f} s past the end of the slide")
            if rows: rows[-1] = (rows[-1][0], end, rows[-1][2])
            prev_end = end; continue
        s = slides.get(it["slide"])
        if not s: probs.append(f"unknown slide name: {it['slide']}"); continue
        length = it["out"] - it["in"]; end = it["at"] + length
        first = s["parts"][int(it["parts"].split("-")[0].lstrip("P")) - 1]
        last = s["parts"][int(it["parts"].split("-")[-1].lstrip("P")) - 1]
        if it["at"] < s["start"] + R["slide_lead_in"]: probs.append(f"{it['slide']} {it['parts']}: starts {s['start'] + R['slide_lead_in'] - it['at']:.2f} s before the slide is ready")
        if p.get("voice_led"):                                       # Phase C: the picture follows the voice
            pi = int(it["parts"].split("-")[0].lstrip("P")) - 1
            shared = pi > 0 and s["parts"][pi - 1]["cue"] == first["cue"]
            if first["cue"] > end + R["voice_led_cue_after_part_end"]:
                probs.append(f"{it['slide']} {it['parts']}: its cue comes {first['cue'] - end:.2f} s after the part ends ({first['shows']})")
            if not shared and first["cue"] < it["at"] - R["latest_start_after_cue"]:
                probs.append(f"{it['slide']} {it['parts']}: its cue comes {it['at'] - first['cue']:.2f} s before the part starts ({first['shows']})")
            if end > s["end"] - R["slide_tail"]: probs.append(f"{it['slide']} {it['parts']}: runs {end - (s['end'] - R['slide_tail']):.2f} s past the end of the slide")
            rows.append((it["at"], end, it)); prev_end = end; continue
        if it["at"] < first["cue"] - R["earliest_start_before_cue"]: probs.append(f"{it['slide']} {it['parts']}: starts {first['cue'] - it['at']:.2f} s before its cue ({first['shows']})")
        if end > s["end"] - R["slide_tail"]: probs.append(f"{it['slide']} {it['parts']}: runs {end - (s['end'] - R['slide_tail']):.2f} s past the end of the slide")
        lag = it["at"] - first["cue"]
        if lag > R["latest_start_after_cue"]:
            probs.append(f"{it['slide']} {it['parts']}: starts {lag:.2f} s after its cue, so the voice trails the picture ({first['shows']})")
        for pn, off in it.get("part_offsets", {}).items():          # optional: where later parts start inside this piece
            part = s["parts"][int(pn.lstrip("P")) - 1]; t = it["at"] + off - it["in"]
            if t < part["cue"] - R["earliest_start_before_cue"]: probs.append(f"{it['slide']} {pn}: heard {part['cue'] - t:.2f} s before its cue ({part['shows']})")
            if t > part["cue"] + R["latest_start_after_cue"]: probs.append(f"{it['slide']} {pn}: heard {t - part['cue']:.2f} s after its cue ({part['shows']})")
        rows.append((it["at"], end, it)); prev_end = end
    for (a0, a1, A), (b0, b1, Bi) in zip(rows, rows[1:]):
        if b0 < a1 + R["min_gap_between_parts"]: probs.append(f"{A['slide']} {A['parts']} and {Bi['slide']} {Bi['parts']}: overlap or gap under {R['min_gap_between_parts']} s")
    if not quiet:
        print("\n".join(probs) if probs else "Placements fit the beat map.")
    return probs

def write_srt(path, dst):
    """Subtitles that follow the narration exactly: one cue per part, at most two lines of 42 characters."""
    beats = json.load(open(os.path.join(KIT, "beats.json"))); slides = {s["slide"]: s for s in beats["slides"]}
    cues = []
    merged = []
    for it in sorted(load_placements(path)["items"], key=lambda i: i["at"]):
        it = dict(it); it["_dur"] = it["out"] - it["in"]
        if it.get("join_previous") and merged:
            m = merged[-1]; m["_dur"] = it["at"] + it["_dur"] - m["at"]
            ps = m["parts"].split("-")[0], it["parts"].split("-")[-1]; m["parts"] = ps[0] if ps[0] == ps[1] else f"{ps[0]}-{ps[1]}"
            continue
        merged.append(it)
    for it in merged:
        s = slides[it["slide"]]; ps = it["parts"].split("-"); a, b = int(ps[0].lstrip("P")), int(ps[-1].lstrip("P"))
        parts = s["parts"][a - 1:b]; t0 = it["at"]; dur = it["_dur"]; words = sum(p["words"] for p in parts)
        offs = it.get("part_offsets", {})
        for i, p in enumerate(parts):
            st = t0 + (offs[p["part"]] - it["in"] if p["part"] in offs else dur * sum(q["words"] for q in parts[:i]) / words)
            nxt = parts[i + 1]["part"] if i + 1 < len(parts) else None
            en = t0 + (offs[nxt] - it["in"] if nxt and nxt in offs else dur * sum(q["words"] for q in parts[:i + 1]) / words)
            cues.append((st, en - 0.05, p["text"]))
    def wrap(t, n=42):
        out, line = [], ""
        for w in t.split():
            if len(line) + len(w) + 1 > n and line: out.append(line); line = w
            else: line = (line + " " + w).strip()
        out.append(line); return out
    def ts(x): h, r = divmod(x, 3600); m, s = divmod(r, 60); return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}"
    k = 0; lines = []
    for st, en, txt in cues:
        ls = wrap(txt)
        chunks = [ls[i:i + 2] for i in range(0, len(ls), 2)]; span = (en - st) / len(chunks)
        for j, ch in enumerate(chunks):
            k += 1; lines += [str(k), f"{ts(st + j * span)} --> {ts(st + (j + 1) * span)}", *ch, ""]
    open(dst, "w").write("\n".join(lines))

def narration_track(path, total):
    import numpy as np
    p = load_placements(path)
    x = np.zeros(int(total * SR) + SR)
    items = sorted(p["items"], key=lambda i: i["at"])
    for k, it in enumerate(items):
        a = read_audio(it["path"], it["in"], it["out"]) * (10 ** (it.get("gain_db", 0) / 20))
        nxt = items[k + 1] if k + 1 < len(items) else {}
        fi = int((it.get("join_previous") or 0.012) * SR); fo = int((nxt.get("join_previous") or 0.012) * SR)
        a[:fi] *= np.linspace(0, 1, fi); a[-fo:] *= np.linspace(1, 0, fo)   # 12 ms fades (no clicks); a crossfade where a pickup joins
        i0 = int(round(it["at"] * SR)); x[i0:i0 + len(a)] += a[: len(x) - i0]
    return x[: int(total * SR)]

def mix_audio(music_wav, placements, out_wav, total):
    """Voice at -17 LUFS, music bed under it and ducked about 10 dB while the voice speaks, whole mix at -16 LUFS."""
    import numpy as np
    with tempfile.TemporaryDirectory() as td:
        v_raw = os.path.join(td, "v.wav"); v_n = os.path.join(td, "vn.wav"); m_n = os.path.join(td, "mn.wav"); mix = os.path.join(td, "mix.wav")
        write_wav(v_raw, narration_track(placements, total), 1)
        loudnorm(v_raw, v_n, -17); loudnorm(music_wav, m_n, -30)
        v = read_audio(v_n); m = read_audio(m_n)
        n = int(total * SR); v = np.pad(v, (0, max(0, n - len(v))))[:n]; m = np.pad(m, (0, max(0, n - len(m))))[:n]
        # voice envelope in 10 ms blocks, smoothed with a fast attack (50 ms) and slow release (450 ms)
        B = SR // 100; nb = n // B + 1
        rms = np.array([np.sqrt(np.mean(v[i * B:(i + 1) * B] ** 2)) if i * B < n else 0.0 for i in range(nb)])
        ref = np.percentile(rms[rms > 1e-4], 90) if (rms > 1e-4).any() else 1.0
        act = np.clip(rms / (0.25 * ref), 0, 1)                    # 1 while speaking
        # Phase E: the duck holds 0.25 s after the voice, looks 0.15 s ahead (so the music dips just before the voice returns)
        # and releases in about 0.12 s, so the music rises audibly in slide changes and longer pauses
        HOLD, LOOK = 25, 15
        act_h = np.array([act[max(0, i - HOLD):i + LOOK + 1].max() for i in range(nb)])
        sm = np.empty(nb); e = 0.0
        for i in range(nb):
            k = 0.3 if act_h[i] > e else 0.08
            e += k * (act_h[i] - e); sm[i] = e
        duck = np.repeat(1 - 0.68 * sm, B)[:n]                       # about -10 dB under the voice
        write_wav(mix, np.clip(v + m * duck, -1, 1))
        loudnorm(mix, out_wav, -16)

# ---------- commands ----------
def cmd_plan(_):
    run([PY, os.path.join(KIT, "narration.py")])

def cmd_beats(_):
    run([PY, os.path.join(KIT, "export_beats.py")])

def cmd_check(a):
    sys.exit(1 if check_placements(a.placements) else 0)

MUSIC_TIMING = {"HOLDS_FILE": "holds_music.json", "RETIME_FILE": "none"}   # music-only cuts: v12-style reading timing, no voice-led retime
NARR_TIMING = {"HOLDS_FILE": "holds.json", "RETIME_FILE": "retime.json"}       # narrated cut: voice-led timing

def cmd_video(a):
    caps = os.path.join(OUT, f"{NAME}_{a.version}.mp4"); nocaps = os.path.join(OUT, f"{NAME}_{a.version}_NoCaptions.mp4")
    refuse_overwrite(caps); refuse_overwrite(nocaps)
    run([PY, os.path.join(KIT, "export_beats.py")], env=env(**NARR_TIMING))
    music = os.path.join(OUT, f"{NAME}_{a.version}_music.wav")            # music-only timing
    music_narr = os.path.join(OUT, f"{NAME}_{a.version}_music_narr.wav")  # voice-led timing, under the narration
    vid = {}
    for tag, extra, timing in (("caps", {}, MUSIC_TIMING), ("nocaps", {"NOCAPS": "1"}, MUSIC_TIMING),
                               ("narr", {"NOCAPS": "1", "NARRATED": "1"}, NARR_TIMING)):   # narr: the narrated cut's picture (credits name the AI voice)
        vid[tag] = os.path.join(WORK, f"video_{a.version}_{tag}.mp4")
        e = env(SS=2, **extra, **timing)
        for v_ in ("NOCAPS", "NARRATED"):
            if v_ not in extra: e.pop(v_, None)
        run([PY, os.path.join(KIT, "build_long.py"), vid[tag]], env=e)
    run([PY, os.path.join(KIT, "sound.py"), music], env=env(**MUSIC_TIMING))
    run([PY, os.path.join(KIT, "sound.py"), music_narr], env=env(CHORDS_AT_VOICE_GAPS=os.path.join(KIT, "placements_C.json"), **NARR_TIMING))
    for tag, dst in (("caps", caps), ("nocaps", nocaps)):
        ffmpeg("-i", vid[tag], "-i", music, "-af", "loudnorm=I=-24:TP=-1.5", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", dst)
    print("Wrote", caps, "and", nocaps)

def cmd_mix(a):
    vids = {t: os.path.join(WORK, f"video_{a.version}_{t}.mp4") for t in ("caps", "nocaps", "narr")}
    music = os.path.join(OUT, f"{NAME}_{a.version}_music_narr.wav")
    for f in [vids["narr"], music]:
        if not os.path.exists(f): sys.exit(f"Missing {f}. Run: python cavekit.py video --version {a.version}")
    probs = check_placements(a.placements)
    if probs and not a.force: sys.exit("Fix the problems above (or adjust holds.json and re-render), then mix again.")
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", vids["narr"]], capture_output=True, text=True).stdout)
    voice_mix = os.path.join(OUT, f"{NAME}_{a.version}_narrated_audio.wav"); refuse_overwrite(voice_mix)
    mix_audio(music, a.placements, voice_mix, total)
    srt = os.path.join(OUT, f"{NAME}_{a.version}_Narrated.srt"); refuse_overwrite(srt); write_srt(a.placements, srt)
    print("Wrote", srt, "(upload it as the video's captions; it follows the narration word for word)")
    for t, suffix in (("narr", "_Narrated"),):
        dst = os.path.join(OUT, f"{NAME}_{a.version}{suffix}.mp4"); refuse_overwrite(dst)
        ffmpeg("-i", vids[t], "-i", voice_mix, "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", dst)
        print("Wrote", dst)

def cmd_preview(a):
    import numpy as np
    sys.path.insert(0, KIT)
    os.environ["SS"] = "1"
    if not a.captions: os.environ["NOCAPS"] = "1"
    import build_long as B
    starts, acc = [], 0.0
    for kind, k, T in B.SEGS:
        starts.append((acc, kind, k)); acc += round(T * B.FPS) / B.FPS
    total = acc; t0 = max(0.0, a.start); t1 = min(total, a.end)
    vid = os.path.join(WORK, "preview_video.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080", "-r", str(B.FPS), "-i", "-",
                          "-vf", "scale=960:-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p", vid], stdin=subprocess.PIPE)
    for f in range(int(t0 * B.FPS), int(t1 * B.FPS)):
        t = f / B.FPS
        s0, kind, k = [s for s in starts if s[0] <= t][-1]
        r = t - s0; u = B.unhold(r, B.holds_for(kind, k))
        B.O.CLOCK = B.D.CLOCK = r
        img = B.I.frame(k, u) if kind == "intro" else B.data_frame(u) if kind == "data" else B.D.frame(k, u)
        p.stdin.write(img.tobytes())
    p.stdin.close(); p.wait()
    music = os.path.join(WORK, "preview_music.wav")
    run([PY, os.path.join(KIT, "sound.py"), music], env=env(CHORDS_AT_VOICE_GAPS=a.placements) if a.placements else None)
    audio = music
    if a.placements:
        audio = os.path.join(WORK, "preview_mix.wav"); mix_audio(music, a.placements, audio, total)
    dst = os.path.join(OUT, f"preview_{int(t0)}-{int(t1)}.mp4")
    ffmpeg("-i", vid, "-ss", str(t0), "-to", str(t1), "-i", audio, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", dst)
    print("Wrote", dst)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("plan"); sp.add_parser("beats")
    c = sp.add_parser("check"); c.add_argument("placements")
    v = sp.add_parser("video"); v.add_argument("--version", required=True)
    m = sp.add_parser("mix"); m.add_argument("--version", required=True); m.add_argument("--placements", required=True); m.add_argument("--force", action="store_true")
    pv = sp.add_parser("preview"); pv.add_argument("--start", type=float, required=True); pv.add_argument("--end", type=float, required=True)
    pv.add_argument("--placements"); pv.add_argument("--captions", action="store_true")
    a = ap.parse_args()
    {"plan": cmd_plan, "beats": cmd_beats, "check": cmd_check, "video": cmd_video, "mix": cmd_mix, "preview": cmd_preview}[a.cmd](a)
