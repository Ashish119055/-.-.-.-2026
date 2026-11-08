#!/usr/bin/env python3
"""Cut a 2x2 Gemini sheet (thin black lines) into four named frames.

usage: python3 cut_grid.py SHEET.png OUT_DIR --names CFHI [--size 1920x1080]
--names gives the letters for top-left, top-right, bottom-left, bottom-right.
Finds the divider lines near the centre, trims them plus any outer black border,
then cover-scales each panel to exactly --size (Lanczos). Refuses to overwrite unless --force.
"""
import os, sys
import numpy as np
from PIL import Image

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opt = lambda n, d=None: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
src, outdir = args[0], args[1]
names = opt("--names", "ABCD")
TW, TH = map(int, opt("--size", "1920x1080").split("x"))
if len(names) != 4: sys.exit("--names needs 4 letters")
img = Image.open(src).convert("RGB")
W, H = img.size
g = np.asarray(img.convert("L"), dtype=np.float32)

def divider(profile, n):
    """dark band nearest the centre (search the middle 30%) -> (start, end)"""
    lo, hi = int(n * 0.35), int(n * 0.65)
    seg = profile[lo:hi]
    dark = seg < min(60, seg.min() + 25)
    c = int(np.argmin(seg))
    a = b = c
    while a > 0 and dark[a - 1]: a -= 1
    while b < len(seg) - 1 and dark[b + 1]: b += 1
    return lo + a, lo + b + 1

col_x = divider(g.mean(axis=0), W)
row_y = divider(g.mean(axis=1), H)

def trim_border(box):
    """strip outer black frame lines from a panel box"""
    x0, y0, x1, y1 = box
    p = g[y0:y1, x0:x1]
    while x1 - x0 > 10 and p[:, 0].mean() < 50: x0 += 1; p = p[:, 1:]
    while x1 - x0 > 10 and p[:, -1].mean() < 50: x1 -= 1; p = p[:, :-1]
    while y1 - y0 > 10 and p[0].mean() < 50: y0 += 1; p = p[1:]
    while y1 - y0 > 10 and p[-1].mean() < 50: y1 -= 1; p = p[:-1]
    m = 2  # small safety inset against anti-aliased line edges
    return x0 + m, y0 + m, x1 - m, y1 - m

boxes = {names[0]: (0, 0, col_x[0], row_y[0]), names[1]: (col_x[1], 0, W, row_y[0]),
         names[2]: (0, row_y[1], col_x[0], H), names[3]: (col_x[1], row_y[1], W, H)}
os.makedirs(outdir, exist_ok=True)
for n in names:
    if os.path.exists(os.path.join(outdir, f"{n}.png")) and "--force" not in sys.argv:
        sys.exit(f"REFUSING to overwrite {outdir}/{n}.png — ask the user, then re-run with --force")
for name, box in boxes.items():
    x0, y0, x1, y1 = trim_border(box)
    p = img.crop((x0, y0, x1, y1))
    pw, ph = p.size
    s = max(TW / pw, TH / ph)
    p = p.resize((round(pw * s), round(ph * s)), Image.LANCZOS)
    l, t = (p.width - TW) // 2, (p.height - TH) // 2
    p.crop((l, t, l + TW, t + TH)).save(os.path.join(outdir, f"{name}.png"))
    print(f"{name}: src {x1-x0}x{y1-y0} (aspect {(x1-x0)/(y1-y0):.3f}, target {TW/TH:.4f}) upscale x{s:.2f}")
print(f"sheet {W}x{H}, vertical line x={col_x}, horizontal line y={row_y}")
