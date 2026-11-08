#!/usr/bin/env python3
"""Re-cut the Flow clips into shots, join them, grade, and render.  Refuses to overwrite unless --force.

  base   EDL.json OUT_BASE.mp4          builds the muted picture track + OUT_BASE.timing.json (shot starts, joins)
  sheet  BASE.mp4 STILLS_DIR OUT.png    contact sheet: frames from BASE at each still's time + the overlay still
  final  BASE.mp4 OVERLAY_DIR SONG.mp3 OUT.mp4    full render with the song + OUT_whatsapp720.mp4 (< 20 MB)

EDL.json:
{ "fps": 30, "size": [1920, 1080], "end_fade": 1.5, "grain": 5,
  "shots": [ {"clip": "clips/clip1.mp4", "in": 0.0, "out": 5.6, "speed": 1.0, "join": "glow", "xfade": 0.6,
              "note": "hands fold flowers"}, ... ] }
join = how this shot hands over to the NEXT one: "zoom" (zoom through an object), "glow" (flame glow),
"fade" (soft fade) or "bloom" (watercolour bloom). The glow / bloom light itself is drawn by the overlay.
"""
import json, os, subprocess, sys, tempfile

args = [a for a in sys.argv[1:] if not a.startswith("--")]
FORCE = "--force" in sys.argv
XFADE = {"zoom": "zoomin", "glow": "fade", "fade": "fade", "bloom": "fade"}

def guard(p):
    if os.path.exists(p) and not FORCE:
        sys.exit(f"REFUSING to overwrite {p} — ask the user, then re-run with --force")

def run(cmd):
    print("+", " ".join(cmd), file=sys.stderr)
    subprocess.run(cmd, check=True)

def probe(p, what="format=duration"):
    return subprocess.run(["ffprobe", "-v", "error", "-show_entries", what, "-of", "csv=p=0", p],
                          capture_output=True, text=True, check=True).stdout.strip()

mode = args[0] if args else ""

if mode == "base":
    edlp, out = args[1:3]
    tmeta = os.path.splitext(out)[0] + ".timing.json"
    guard(out); guard(tmeta)
    edl = json.load(open(edlp, encoding="utf-8"))
    fps, (W, H) = edl.get("fps", 30), edl.get("size", [1920, 1080])
    shots = edl["shots"]
    if len(shots) < 2: sys.exit("need at least 2 shots")
    ins, fc, durs = [], [], []
    for i, s in enumerate(shots):
        if not os.path.exists(s["clip"]): sys.exit(f"missing clip {s['clip']} — ask the user for it")
        cd = float(probe(s["clip"]))
        if s["out"] > cd + 0.01 or s["in"] < 0 or s["out"] <= s["in"]:
            sys.exit(f"shot {i}: in/out {s['in']}–{s['out']} outside clip length {cd:.2f}s")
        sp = s.get("speed", 1.0)
        if not 0.85 <= sp <= 1.15:
            print(f"WARNING shot {i}: speed {sp} — the brief wants close to real speed (0.85–1.15)", file=sys.stderr)
        d = (s["out"] - s["in"]) / sp
        durs.append(d)
        ins += ["-i", s["clip"]]
        fc.append(f"[{i}:v]trim={s['in']:.3f}:{s['out']:.3f},setpts=(PTS-STARTPTS)/{sp},"
                  f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},"
                  f"fps={fps},setsar=1,format=yuv420p[s{i}]")
    # chain xfades; offset = running length - xfade
    starts, joins, cur, length = [0.0], [], "s0", durs[0]
    for i in range(1, len(shots)):
        prev = shots[i - 1]
        style = prev.get("join", "fade")
        if style not in XFADE: sys.exit(f"shot {i-1}: join must be one of {list(XFADE)}")
        xf = prev.get("xfade", 0.6 if style != "zoom" else 0.45)
        if xf >= min(durs[i - 1], durs[i]): sys.exit(f"xfade {xf}s too long for shot {i-1}/{i}")
        off = length - xf
        fc.append(f"[{cur}][s{i}]xfade=transition={XFADE[style]}:duration={xf}:offset={off:.3f}[j{i}]")
        joins.append({"t": round(off + xf / 2, 3), "style": style, "dur": xf, "after_shot": i - 1})
        starts.append(round(off, 3)); cur = f"j{i}"; length = off + durs[i]
    ef = edl.get("end_fade", 1.5)
    fc.append(f"[{cur}]noise=alls={edl.get('grain', 5)}:allf=t,fade=t=out:st={length - ef:.3f}:d={ef},format=yuv420p[out]")
    run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(fc), "-map", "[out]", "-an",
         "-c:v", "libx264", "-crf", "15", "-preset", "medium", "-r", str(fps), out])
    meta = {"duration": round(length, 3), "fps": fps, "size": [W, H], "end_fade": ef,
            "shots": [{"start": st, "dur": round(d, 3), "note": s.get("note", "")} for st, d, s in zip(starts, durs, shots)],
            "joins": joins}
    json.dump(meta, open(tmeta, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for i, (st, d, s) in enumerate(zip(starts, durs, shots)):
        print(f"shot {i:2d} {st:7.2f}s +{d:5.2f}s  {s['clip']} {s['in']}-{s['out']}  {s.get('note','')}")
    print(f"total {length:.2f}s -> {out}, {tmeta}")

elif mode == "sheet":
    from PIL import Image, ImageDraw
    base, stills, out = args[1:4]; guard(out)
    shots = sorted((f for f in os.listdir(stills) if f.startswith("still_")), key=lambda f: float(f[6:-4]))
    if not shots: sys.exit("no stills — render them with render_overlay.js --times")
    vd = float(probe(base))
    late = [f for f in shots if float(f[6:-4]) > vd - 0.05]
    if late: print(f"skipping stills past the end ({vd:.2f}s):", late, file=sys.stderr)
    shots = [f for f in shots if f not in late]
    tw, th, cols, pad = 480, 270, 4, 12
    rows = (len(shots) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * pad, rows * (th + 30) + pad), (22, 20, 36))
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(shots):
        t = float(f[6:-4])
        tmp = tempfile.mktemp(suffix=".png")
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", base, "-frames:v", "1", tmp])
        bg = Image.open(tmp).convert("RGBA"); os.remove(tmp)
        ov = Image.open(os.path.join(stills, f)).convert("RGBA").resize(bg.size)
        bg.alpha_composite(ov)
        x, y = pad + (i % cols) * (tw + pad), pad + (i // cols) * (th + 30)
        sheet.paste(bg.convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 4, y + th + 6), f"t={t:.2f}s", fill=(255, 230, 150))
    sheet.save(out); print(out)

elif mode == "final":
    base, ovdir, song, out = args[1:5]
    wa = os.path.splitext(out)[0] + "_whatsapp720.mp4"
    guard(out); guard(wa)
    meta = json.load(open(os.path.splitext(base)[0] + ".timing.json", encoding="utf-8"))
    D, fps, ef = meta["duration"], meta["fps"], meta["end_fade"]
    sd = float(probe(song))
    if abs(sd - D) > 0.5:
        print(f"WARNING: song is {sd:.2f}s but picture is {D:.2f}s — the render follows the picture", file=sys.stderr)
    n = len([f for f in os.listdir(ovdir) if f[:5].isdigit()])
    if n < round(D * fps): sys.exit(f"overlay has {n} frames, needs {round(D * fps)} — render it first")
    run(["ffmpeg", "-y", "-v", "error", "-i", base, "-framerate", str(fps), "-i", os.path.join(ovdir, "%05d.png"),
         "-i", song, "-filter_complex",
         f"[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v];"
         f"[2:a]atrim=0:{D:.3f},asetpts=PTS-STARTPTS,afade=t=out:st={max(0, D - ef):.3f}:d={ef}[a]",
         "-map", "[v]", "-map", "[a]", "-t", f"{D:.3f}", "-r", str(fps),
         "-c:v", "libx264", "-crf", "18", "-maxrate", "16M", "-bufsize", "32M", "-preset", "slow",
         "-profile:v", "high", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out])
    def wa_enc(extra):
        run(["ffmpeg", "-y", "-v", "error", "-i", out, "-vf", "scale=1280:720:flags=lanczos", "-r", str(fps),
             "-c:v", "libx264", *extra, "-preset", "slow", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", wa])
    wa_enc(["-crf", "24", "-maxrate", f"{int(18.5e6 * 8 / D / 1000) - 140}k", "-bufsize", "6000k"])
    if os.path.getsize(wa) >= 19.5e6:
        kbps = int(18e6 * 8 / D / 1000) - 140
        wa_enc(["-b:v", f"{kbps}k", "-maxrate", f"{kbps}k", "-bufsize", f"{2 * kbps}k"])
    for f in (out, wa):
        print(f"{f}: {os.path.getsize(f) / 1e6:.1f} MB, {float(probe(f)):.2f} s")
else:
    sys.exit(__doc__)
