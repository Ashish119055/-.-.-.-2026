#!/usr/bin/env python3
"""Cut / join / grade / render with ffmpeg.  Refuses to overwrite unless --force.

  base   CLIP1 CLIP2 TIMELINE OUT_BASE.mp4      mute Flow audio, fit clips to the timeline,
                                                 0.5 s dissolve at `join` (glow is drawn by the overlay),
                                                 light paper grain, 1080x1920 @ 30 fps
  sheet  TIMELINE STILLS_DIR OUT.png (--base BASE.mp4 | --frames DIR_WITH_A-D)
                                                 contact sheet of stills with the overlay composited
  final  BASE.mp4 OVERLAY_DIR AUDIO TIMELINE OUT.mp4   full render + OUT_whatsapp720.mp4 (< 20 MB)
"""
import json, os, subprocess, sys, tempfile

FPS, W, H, XF = 30, 1080, 1920, 0.5
args = [a for a in sys.argv[1:] if not a.startswith("--")]
FORCE = "--force" in sys.argv

def opt(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None

def guard(path):
    if os.path.exists(path) and not FORCE:
        sys.exit(f"REFUSING to overwrite {path} — ask the user, then re-run with --force")

def run(cmd):
    print("+", " ".join(cmd), file=sys.stderr)
    subprocess.run(cmd, check=True)

def dur(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout)

def fit(idx, src, slot):
    """filter that makes clip `src` exactly `slot` seconds: gentle speed-up if a bit long, else trim"""
    d = dur(src)
    if d + 0.01 < slot:
        sys.exit(f"clip {src} is {d:.2f}s but needs {slot:.2f}s — move `join`, shorten duration, or ask the user for a longer clip")
    r = slot / d
    speed = f"setpts={r:.5f}*PTS," if r >= 0.75 else ""
    return (f"[{idx}:v]{speed}trim=0:{slot:.3f},setpts=PTS-STARTPTS,"
            f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},"
            f"fps={FPS},setsar=1,format=yuv420p[v{idx}]")

mode = args[0] if args else ""
if mode == "base":
    c1, c2, tlp, out = args[1:5]; guard(out)
    tl = json.load(open(tlp, encoding="utf-8"))
    D, J = tl["duration"], tl["join"]
    if not 10 <= D <= 15: sys.exit("duration must be 10–15 s")
    d1 = J + XF / 2; d2 = D - d1 + XF
    fc = ";".join([fit(0, c1, d1), fit(1, c2, d2),
                   f"[v0][v1]xfade=transition=fade:duration={XF}:offset={d1 - XF:.3f}[x]",
                   "[x]noise=alls=6:allf=t,format=yuv420p[out]"])
    run(["ffmpeg", "-y", "-v", "error", "-i", c1, "-i", c2, "-filter_complex", fc, "-map", "[out]", "-an",
         "-t", f"{D:.3f}", "-c:v", "libx264", "-crf", "15", "-preset", "medium", "-r", str(FPS), out])

elif mode == "sheet":
    from PIL import Image, ImageDraw
    tlp, stills, out = args[1:4]; guard(out)
    tl = json.load(open(tlp, encoding="utf-8"))
    D, J = tl["duration"], tl["join"]
    shots = sorted((f for f in os.listdir(stills) if f.startswith("still_")), key=lambda f: float(f[6:-4]))
    base, frames = opt("--base"), opt("--frames")
    tiles = []
    if frames:  # before the clips exist: show the four cut panels too
        for n in "ABCD":
            p = os.path.join(frames, f"{n}.png")
            if not os.path.exists(p): sys.exit(f"missing frame {p} — ask the user")
            tiles.append((Image.open(p).convert("RGBA"), f"panel {n}"))
    for f in shots:
        t = float(f[6:-4])
        if base:
            tmp = tempfile.mktemp(suffix=".png")
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", base, "-frames:v", "1", tmp])
            bg = Image.open(tmp).convert("RGBA")
        else:
            n = "A" if t < J / 2 else "B" if t < J else "C" if t < J + (D - J) / 2 else "D"
            bg = Image.open(os.path.join(frames, f"{n}.png")).convert("RGBA")
        bg.alpha_composite(Image.open(os.path.join(stills, f)).convert("RGBA"))
        tiles.append((bg, f"t={t:.2f}s"))
    tw, th, cols = 270, 480, 4
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * 12, rows * (th + 40) + 12), (24, 20, 40))
    d = ImageDraw.Draw(sheet)
    for i, (im, lab) in enumerate(tiles):
        x, y = 12 + (i % cols) * (tw + 12), 12 + (i // cols) * (th + 40)
        sheet.paste(im.convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
        # safe-area guides (scaled 0.25): top 250, bottom 420, right 150
        d.rectangle([x, y + 62, x + tw - 37, y + th - 105], outline=(0, 220, 255))
        d.text((x + 4, y + th + 8), lab, fill=(255, 230, 150))
    sheet.save(out); print(out)

elif mode == "final":
    base, ovdir, audio, tlp, out = args[1:6]
    wa = os.path.splitext(out)[0] + "_whatsapp720.mp4"
    guard(out); guard(wa)
    tl = json.load(open(tlp, encoding="utf-8")); D = tl["duration"]
    n = len([f for f in os.listdir(ovdir) if f[:4].isdigit()])
    if n < round(D * FPS): sys.exit(f"overlay has {n} frames, needs {round(D * FPS)} — render it first")
    run(["ffmpeg", "-y", "-v", "error", "-i", base, "-framerate", str(FPS), "-i", os.path.join(ovdir, "%04d.png"),
         "-i", audio, "-filter_complex",
         f"[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v];"
         f"[2:a]atrim=0:{D:.3f},asetpts=PTS-STARTPTS,afade=t=out:st={D - 0.4:.3f}:d=0.4[a]",
         "-map", "[v]", "-map", "[a]", "-t", f"{D:.3f}", "-r", str(FPS),
         "-c:v", "libx264", "-crf", "18", "-maxrate", "16M", "-bufsize", "32M", "-preset", "slow", "-profile:v", "high", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out])
    def wa_enc(extra):
        run(["ffmpeg", "-y", "-v", "error", "-i", out, "-vf", "scale=720:1280:flags=lanczos", "-r", str(FPS),
             "-c:v", "libx264", *extra, "-preset", "slow", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", wa])
    wa_enc(["-crf", "23"])
    if os.path.getsize(wa) >= 19.5e6:   # fall back to a bitrate that fits 19 MB
        kbps = int(19e6 * 8 / D / 1000) - 140
        wa_enc(["-b:v", f"{kbps}k", "-maxrate", f"{kbps}k", "-bufsize", f"{2 * kbps}k"])
    for f in (out, wa):
        print(f"{f}: {os.path.getsize(f) / 1e6:.1f} MB, {dur(f):.2f} s")
else:
    sys.exit(__doc__)
