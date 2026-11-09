"""Edition crop with today's runway axes drawn with distance ticks (every 100 m, label every 500 m).

  python -I rwyticks.py IMG.npy CX CY HALF RES OUT.png x0 x1 y0 y1 NAME:LON0,LAT0,LON1,LAT1 ... [--zoom 1]
Axis distances are metres from the axis start (LON0, LAT0).
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vanished_sites" / "tools"))
import vt  # noqa: E402

a = [s for s in sys.argv[1:] if not s.startswith("--")]
zoom = float(next((s.split("=")[1] for s in sys.argv if s.startswith("--zoom=")), 1))
img = np.load(a[0], mmap_mode="r"); cx, cy, H, res = map(float, a[1:5]); out = a[5]
x0, x1, y0, y1 = map(float, a[6:10])
i0, i1 = int((x0 + H) / res), int((x1 + H) / res); j0, j1 = int((H - y1) / res), int((H - y0) / res)
im = Image.fromarray(np.ascontiguousarray(img[j0:j1, i0:i1]))
im = im.resize((int(im.size[0] * zoom), int(im.size[1] * zoom)), Image.LANCZOS); d = ImageDraw.Draw(im)
P = lambda x, y: (((x + H) / res - i0) * zoom, ((H - y) / res - j0) * zoom)
for spec in a[10:]:
    name, _, c = spec.partition(":")
    lo0, la0, lo1, la1 = map(float, c.split(","))
    (ax, ay), (bx, by) = [tuple(map(float, vt.ll2loc(lo, la, cx, cy))) for lo, la in ((lo0, la0), (lo1, la1))]
    L = np.hypot(bx - ax, by - ay); u = np.array([bx - ax, by - ay]) / L; n = np.array([-u[1], u[0]])
    d.line([P(ax, ay), P(bx, by)], fill=(255, 0, 0), width=1)
    for k in range(0, int(L) + 1, 100):
        p = np.array([ax, ay]) + k * u
        q1, q2 = p + n * (12 if k % 500 else 30), p - n * (12 if k % 500 else 30)
        d.line([P(*q1), P(*q2)], fill=(255, 0, 0), width=1)
        if k % 500 == 0:
            d.text(P(*(p + n * 38)), str(k), fill=(255, 0, 0))
    d.text(P(ax - 40 * u[0], ay - 40 * u[1]), name, fill=(200, 0, 0))
im.save(out); print(out, im.size)
