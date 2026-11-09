"""First-pass pavement dating from presence.py output + a QA map.

  python -I qa_map.py PRESENCE.csv TODAY.geojson BG.npy CX CY HALF RES OUT.png OUT_first.csv [--hit 0.08]

A feature is drawn on an edition when hit <= HIT and water <= 0.1. First edition = the
earliest from which it stays drawn on every later edition (one miss allowed). Map: today's
features coloured by that edition over the given background edition (faded).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vanished_sites" / "tools"))
import vt  # noqa: E402

a = [s for s in sys.argv[1:] if not s.startswith("--")]
HIT = float(next((s.split("=")[1] for s in sys.argv if s.startswith("--hit=")), 0.08))
d = pd.read_csv(a[0]); feats = json.loads(Path(a[1]).read_text())["features"]
bg = np.load(a[2], mmap_mode="r"); cx, cy, H, res = map(float, a[3:7]); out = a[7]; outcsv = a[8]
eds = [c[:-4] for c in d.columns if c.endswith("_hit")]
first = {}
for _, r in d.iterrows():
    pres = []
    for e in eds:
        h, w = r[f"{e}_hit"], r[f"{e}_water"]
        pres.append(None if pd.isna(h) else (h <= HIT and w <= 0.1))
    f = None
    for k, e in enumerate(eds):
        later = [p for p in pres[k:] if p is not None]
        if later and later[0] and sum(1 for p in later if not p) <= 1 and pres[-1] is not False:
            f = e; break
    first[r["id"]] = f
pd.DataFrame({"id": list(first), "first": list(first.values())}).to_csv(outcsv, index=False)
pal = {e: c for e, c in zip(eds, [(0, 0, 160), (0, 120, 255), (0, 170, 0), (200, 170, 0), (255, 110, 0), (220, 0, 0), (150, 0, 150)])}
im = Image.fromarray((np.asarray(bg) * 0.45 + 140).astype(np.uint8)); dr = ImageDraw.Draw(im)
P = lambda x, y: ((x + H) / res, (H - y) / res)
for ft in feats:
    p = ft["properties"]
    if p["class"] not in ("runway", "stopway", "taxiway", "taxilane", "apron"):
        continue
    f = first.get(p["id"])
    col = pal.get(f, (110, 110, 110))
    g = shape(ft["geometry"])
    for q in getattr(g, "geoms", [g]):
        ring = q.exterior if q.geom_type == "Polygon" else q
        x, y = vt.ll2loc(*np.asarray(ring.coords).T, cx, cy)
        dr.line([P(u, v) for u, v in zip(x, y)], fill=col, width=3 if q.geom_type != "Polygon" else 2)
for k, e in enumerate(eds):
    dr.rectangle([10, 10 + 22 * k, 30, 28 + 22 * k], fill=pal[e]); dr.text((36, 14 + 22 * k), e, fill=(0, 0, 0))
dr.rectangle([10, 10 + 22 * len(eds), 30, 28 + 22 * len(eds)], fill=(110, 110, 110)); dr.text((36, 14 + 22 * len(eds)), "never", fill=(0, 0, 0))
im.save(out); print(out, pd.Series(first).value_counts(dropna=False).to_dict())
