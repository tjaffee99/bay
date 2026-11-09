"""Draw zone polygons (local metres) and today's pavement coloured by the zone holding most of it.

  python -I zcheck.py ZONES.json TODAY.geojson BG.npy CX CY HALF RES OUT.png x0 x1 y0 y1 [--scale 0.5]
Later zones in the file win (overrides are listed after extents).
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import shape, Polygon
from shapely.ops import transform

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vanished_sites" / "tools"))
import vt  # noqa: E402

a = [s for s in sys.argv[1:] if not s.startswith("--")]
sc = float(next((s.split("=")[1] for s in sys.argv if s.startswith("--scale=")), 0.5))
zones = json.load(open(a[0])); feats = json.loads(Path(a[1]).read_text())["features"]
bg = np.load(a[2], mmap_mode="r"); cx, cy, H, res = map(float, a[3:7]); out = a[7]
x0, x1, y0, y1 = map(float, a[8:12])
i0, i1 = int((x0 + H) / res), int((x1 + H) / res); j0, j1 = int((H - y1) / res), int((H - y0) / res)
im = Image.fromarray((np.asarray(bg[j0:j1, i0:i1]) * 0.5 + 127).astype(np.uint8))
im = im.resize((int(im.size[0] * sc), int(im.size[1] * sc)), Image.LANCZOS); d = ImageDraw.Draw(im)
P = lambda x, y: ((x - x0) / res * sc, (y1 - y) / res * sc)
zp = [(z, Polygon(z["xy"])) for z in zones]
for z, p in zp:
    pts = [P(x, y) for x, y in z["xy"]]
    d.line(pts + [pts[0]], fill=tuple(z["rgb"]), width=1)
    c = p.representative_point(); d.text(P(c.x, c.y), z["id"], fill=tuple(z["rgb"]))
for ft in feats:
    pr = ft["properties"]
    if pr["class"] not in ("runway", "stopway", "taxiway", "taxilane", "apron"):
        continue
    g = transform(lambda x, y, z=None: vt.ll2loc(x, y, cx, cy), shape(ft["geometry"]))
    best, bv = None, 0.0
    for z, p in zp:
        v = g.intersection(p).area if g.geom_type == "Polygon" else g.intersection(p).length
        tot = g.area if g.geom_type == "Polygon" else g.length
        if tot and v / tot >= 0.5:
            best = z  # later zones override
    col = tuple(best["rgb"]) if best else (255, 0, 0)
    for q in getattr(g, "geoms", [g]):
        ring = q.exterior if q.geom_type == "Polygon" else q
        x, y = np.asarray(ring.coords).T
        d.line([P(u, v) for u, v in zip(x, y)], fill=col, width=2)
for x in range(int(np.ceil(x0 / 500) * 500), int(x1) + 1, 500):
    for y in range(int(np.ceil(y0 / 500) * 500), int(y1) + 1, 500):
        d.text(P(x, y), f"{x},{y}", fill=(0, 0, 0))
im.save(out); print(out, im.size)
