#!/usr/bin/env python3
"""Cut a 2x2 Gemini sheet (thin black lines) into A.png B.png C.png D.png at 1080x1920.

usage: python3 cut_grid.py SHEET.png OUT_DIR
A = top-left, B = top-right, C = bottom-left, D = bottom-right.
Finds the divider lines near the centre, trims them plus any outer black border,
then cover-scales each panel to exactly 1080x1920 (Lanczos).
"""
import os, sys
import numpy as np
from PIL import Image

src, outdir = sys.argv[1:3]
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

boxes = {"A": (0, 0, col_x[0], row_y[0]), "B": (col_x[1], 0, W, row_y[0]),
         "C": (0, row_y[1], col_x[0], H), "D": (col_x[1], row_y[1], W, H)}
os.makedirs(outdir, exist_ok=True)
TW, TH = 1080, 1920
for name, box in boxes.items():
    x0, y0, x1, y1 = trim_border(box)
    p = img.crop((x0, y0, x1, y1))
    pw, ph = p.size
    s = max(TW / pw, TH / ph)
    p = p.resize((round(pw * s), round(ph * s)), Image.LANCZOS)
    l, t = (p.width - TW) // 2, (p.height - TH) // 2
    p.crop((l, t, l + TW, t + TH)).save(os.path.join(outdir, f"{name}.png"))
    print(f"{name}: src {x1-x0}x{y1-y0} (aspect {(x1-x0)/(y1-y0):.3f}, 9:16=0.5625) upscale x{s:.2f}")
print(f"sheet {W}x{H}, vertical line x={col_x}, horizontal line y={row_y}")
