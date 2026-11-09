"""Draw today's (Overture / OSM) runways, taxiways and aprons over a rendered edition.

  python -I overlay.py IMG.npy CX CY HALF RES TODAY.geojson OUT.png [x0 x1 y0 y1] [--ids]
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vanished_sites" / "tools"))
import vt  # noqa: E402

a = [s for s in sys.argv[1:] if not s.startswith("--")]
ids = "--ids" in sys.argv
img = np.load(a[0]); cx, cy, H, res = map(float, a[1:5]); feats = json.loads(Path(a[5]).read_text())["features"]
out = a[6]
x0, x1, y0, y1 = map(float, a[7:11]) if len(a) > 10 else (-H, H, -H, H)
i0, i1 = int((x0 + H) / res), int((x1 + H) / res); j0, j1 = int((H - y1) / res), int((H - y0) / res)
im = Image.fromarray(img[j0:j1, i0:i1].copy()); d = ImageDraw.Draw(im)
P = lambda x, y: ((x + H) / res - i0, (H - y) / res - j0)
COL = {"runway": (255, 0, 0), "stopway": (255, 120, 0), "taxiway": (200, 0, 200), "taxilane": (120, 0, 255),
       "apron": (0, 150, 255)}
g = 250
for v in np.arange(np.floor(min(x0, y0) / g) * g, max(x1, y1) + g, g):
    if x0 <= v <= x1:
        d.line([P(v, y0), P(v, y1)], fill=(0, 200, 200), width=1); d.text((P(v, y1)[0] + 2, 2), str(int(v)), fill=(0, 0, 200))
    if y0 <= v <= y1:
        d.line([P(x0, v), P(x1, v)], fill=(0, 200, 200), width=1); d.text((2, P(x0, v)[1] + 2), str(int(v)), fill=(0, 0, 200))
for f in feats:
    cl = f["properties"]["class"]
    if cl not in COL:
        continue
    gg = shape(f["geometry"])
    for p in getattr(gg, "geoms", [gg]):
        rings = [p.exterior] if p.geom_type == "Polygon" else [p]
        for r in rings:
            x, y = vt.ll2loc(*np.asarray(r.coords).T, cx, cy)
            d.line([P(u, v) for u, v in zip(x, y)], fill=COL[cl], width=1)
        if ids and cl in ("runway", "apron"):
            c = p.representative_point()
            x, y = vt.ll2loc(c.x, c.y, cx, cy)
            d.text(P(float(x), float(y)), f["properties"]["id"][:4], fill=COL[cl])
im.save(out); print(out, im.size)
