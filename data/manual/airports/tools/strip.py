"""Runway strips: each edition resampled along a runway axis (axis horizontal), stacked.

  python -I strip.py CX CY RES OUT.png AX0,AY0,AX1,AY1 HALFW MARGIN NAME=IMG.npy[,HALF] ...

A = axis endpoints in the local frame (m). The strip runs from A0 - MARGIN to A1 + MARGIN,
+-HALFW across. Ticks every 100 m along the axis (label = metres from A0), red ticks at A0 / A1.
"""
import sys
import numpy as np
from PIL import Image, ImageDraw
import cv2

a = sys.argv[1:]
cx, cy, res = map(float, a[0:3]); out = a[3]
x0, y0, x1, y1 = map(float, a[4].split(",")); hw = float(a[5]); mg = float(a[6])
L = np.hypot(x1 - x0, y1 - y0); u = np.array([x1 - x0, y1 - y0]) / L; n = np.array([-u[1], u[0]])
s = np.arange(-mg, L + mg, res); t = np.arange(hw, -hw, -res)
S, T = np.meshgrid(s, t)
X = x0 + S * u[0] + T * n[0]; Y = y0 + S * u[1] + T * n[1]
rows = []
for spec in a[7:]:
    name, _, f = spec.partition("=")
    f, _, H = f.partition(",")
    img = np.load(f); H = float(H) if H else img.shape[0] * res / 2
    r = img.shape[0] * res / 2 / (img.shape[0] / 2)  # = res of the image (assumed same)
    col = (X + H) / res - 0.5; row = (H - Y) / res - 0.5
    st = cv2.remap(np.ascontiguousarray(img), col.astype(np.float32), row.astype(np.float32), cv2.INTER_LINEAR,
                   borderValue=(255, 255, 255))
    im = Image.fromarray(st); d = ImageDraw.Draw(im)
    for k in range(int(-mg // 100) * 100, int(L + mg) + 1, 100):
        px = (k + mg) / res
        d.line([(px, 0), (px, 6)], fill=(0, 120, 255)); d.line([(px, im.size[1] - 6), (px, im.size[1])], fill=(0, 120, 255))
        if k % 500 == 0:
            d.text((px + 2, 6), str(k), fill=(0, 0, 255))
    for k in (0, L):
        px = (k + mg) / res
        d.line([(px, 0), (px, im.size[1])], fill=(255, 0, 0))
    d.line([(0, im.size[1] / 2), (im.size[0], im.size[1] / 2)], fill=(255, 160, 160))
    d.text((4, im.size[1] - 14), name, fill=(255, 0, 0))
    rows.append(im)
W = rows[0].size[0]; Hh = sum(r.size[1] + 2 for r in rows)
o = Image.new("RGB", (W, Hh), (0, 0, 0)); yy = 0
for r in rows:
    o.paste(r, (0, yy)); yy += r.size[1] + 2
o.save(out); print(out, o.size, "axis length", round(L))
