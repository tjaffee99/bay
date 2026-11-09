"""QA map of the built pavement_dates.csv: today's features coloured by start year over an edition,
with the zones of pavement_zones.geojson.

  python -I tools/qa_build.py AP BG.npy HALF RES OUT.png x0 x1 y0 y1 [--scale 0.45]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
a = [s for s in sys.argv[1:] if not s.startswith("--")]
sc = float(next((s.split("=")[1] for s in sys.argv if s.startswith("--scale=")), 0.45))
ap = a[0]; bg = np.load(a[1], mmap_mode="r"); H, res = float(a[2]), float(a[3]); out = a[4]
x0, x1, y0, y1 = map(float, a[5:9])
d = pd.read_csv(HERE / "pavement_dates.csv"); d = d[d.airport == ap]
yr = d.groupby("overture_id").start_year.min().to_dict()
import pyarrow.parquet as pq, geopandas as gpd
t = pd.read_parquet(build.OVT); g = gpd.GeoDataFrame(t, geometry=gpd.GeoSeries.from_wkb(t.geometry), crs=4326)
g = g[g.id.isin(yr)]
i0, i1 = int((x0 + H) / res), int((x1 + H) / res); j0, j1 = int((H - y1) / res), int((H - y0) / res)
im = Image.fromarray((np.asarray(bg[j0:j1, i0:i1]) * 0.45 + 140).astype(np.uint8))
im = im.resize((int(im.size[0] * sc), int(im.size[1] * sc)), Image.LANCZOS); dr = ImageDraw.Draw(im)
P = lambda x, y: ((x - x0) / res * sc, (y1 - y) / res * sc)
def col(y):
    stops = [(1927, (120, 0, 0)), (1944, (0, 0, 180)), (1955, (0, 140, 255)), (1965, (0, 170, 0)),
             (1975, (220, 170, 0)), (1990, (255, 100, 0)), (2010, (230, 0, 160))]
    for k in range(len(stops) - 1, -1, -1):
        if y >= stops[k][0]:
            return stops[k][1]
    return (100, 100, 100)
for z in json.loads((HERE / "pavement_zones.geojson").read_text())["features"]:
    if z["properties"]["airport"] != ap or z["properties"]["kind"] != "zone":
        continue
    p = shape(z["geometry"])
    for q in getattr(p, "geoms", [p]):
        if q.geom_type != "Polygon":
            continue
        x, y = build.ll2loc(ap, *np.asarray(q.exterior.coords).T)
        dr.line([P(u, v) for u, v in zip(x, y)], fill=col(z["properties"]["start_year"]), width=1)
    c = p.representative_point(); cx_, cy_ = build.ll2loc(ap, c.x, c.y)
    dr.text(P(float(cx_), float(cy_)), f'{z["properties"]["zone"]} {z["properties"]["start_year"]}', fill=(0, 0, 0))
for _, r in g.iterrows():
    gg = r.geometry
    ring = gg.exterior if gg.geom_type == "Polygon" else gg
    x, y = build.ll2loc(ap, *np.asarray(ring.coords).T)
    dr.line([P(u, v) for u, v in zip(x, y)], fill=col(yr[r.id]), width=2)
for k, (yy, lab) in enumerate([(1927, "<1944"), (1944, "1944-54"), (1955, "1955-64"), (1965, "1965-74"),
                               (1975, "1975-89"), (1990, "1990-2009"), (2010, "2010-")]):
    dr.rectangle([8, 8 + 18 * k, 24, 22 + 18 * k], fill=col(yy)); dr.text((30, 10 + 18 * k), lab, fill=(0, 0, 0))
im.save(out); print(out, im.size)
