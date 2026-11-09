"""Gridded view of a render (for reading zone corners): local metres, grid every G, labels every 2G.

  python -I gridview.py IMG.npy HALF RES OUT.png x0 x1 y0 y1 [--g 250] [--scale 0.6] [--zones zones.json]
"""
import json
import sys
import numpy as np
from PIL import Image, ImageDraw

a = [s for s in sys.argv[1:] if not s.startswith("--")]
opt = {s.split("=")[0]: s.split("=", 1)[1] for s in sys.argv[1:] if s.startswith("--")}
img = np.load(a[0], mmap_mode="r"); H, res = float(a[1]), float(a[2]); out = a[3]
x0, x1, y0, y1 = map(float, a[4:8]); G = float(opt.get("--g", 250)); sc = float(opt.get("--scale", 0.6))
i0, i1 = int((x0 + H) / res), int((x1 + H) / res); j0, j1 = int((H - y1) / res), int((H - y0) / res)
im = Image.fromarray(np.ascontiguousarray(img[j0:j1, i0:i1]))
im = im.resize((int(im.size[0] * sc), int(im.size[1] * sc)), Image.LANCZOS); d = ImageDraw.Draw(im)
P = lambda x, y: ((x - x0) / res * sc, (y1 - y) / res * sc)
for v in np.arange(np.ceil(x0 / G) * G, x1 + 1, G):
    d.line([P(v, y0), P(v, y1)], fill=(0, 190, 255) if v % (2 * G) else (0, 90, 255), width=1)
for v in np.arange(np.ceil(y0 / G) * G, y1 + 1, G):
    d.line([P(x0, v), P(x1, v)], fill=(0, 190, 255) if v % (2 * G) else (0, 90, 255), width=1)
for xv in np.arange(np.ceil(x0 / (2 * G)) * 2 * G, x1 + 1, 2 * G):
    for yv in np.arange(np.ceil(y0 / (2 * G)) * 2 * G, y1 + 1, 2 * G):
        px, py = P(xv, yv)
        d.rectangle([px + 1, py + 1, px + 62, py + 11], fill=(255, 255, 255))
        d.text((px + 2, py), f"{int(xv)},{int(yv)}", fill=(0, 0, 220))
if "--zones" in opt:
    for z in json.load(open(opt["--zones"])):
        pts = [P(x, y) for x, y in z["xy"]]
        d.line(pts + [pts[0]], fill=tuple(z.get("rgb", (255, 0, 0))), width=2)
        cxp = np.mean([p[0] for p in pts]); cyp = np.mean([p[1] for p in pts])
        d.text((cxp, cyp), z["id"], fill=tuple(z.get("rgb", (255, 0, 0))))
im.save(out); print(out, im.size)
