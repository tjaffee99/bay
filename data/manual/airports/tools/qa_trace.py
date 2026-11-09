"""QA: vanished_buildings.geojson (red) over an edition crop. python -I tools/qa_trace.py AP NPY HALF OUT.png x0 x1 y0 y1 [--scale 1]"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import shape
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
HERE = Path(__file__).resolve().parents[1]
a = [s for s in sys.argv[1:] if not s.startswith("--")]
sc = float(next((s.split("=")[1] for s in sys.argv if s.startswith("--scale=")), 1))
ap, img, H, out = a[0], np.load(a[1], mmap_mode="r"), float(a[2]), a[3]
x0, x1, y0, y1 = map(float, a[4:8]); res = 2.0
i0, i1 = int((x0 + H) / res), int((x1 + H) / res); j0, j1 = int((H - y1) / res), int((H - y0) / res)
im = Image.fromarray(np.ascontiguousarray(img[j0:j1, i0:i1])); im = im.resize((int(im.size[0] * sc), int(im.size[1] * sc)))
d = ImageDraw.Draw(im); P = lambda x, y: ((x - x0) / res * sc, (y1 - y) / res * sc)
for f in json.loads((HERE / "vanished_buildings.geojson").read_text())["features"]:
    if f["properties"]["site_id"] != f"airport_{ap.lower()}":
        continue
    g = shape(f["geometry"]); x, y = build.ll2loc(ap, *np.asarray(g.exterior.coords).T)
    d.line([P(u, v) for u, v in zip(x, y)], fill=(255, 0, 0), width=2)
    c = g.centroid; cx_, cy_ = build.ll2loc(ap, c.x, c.y)
    d.text(P(float(cx_), float(cy_)), f'{int(f["properties"]["start_year"])}-{int(f["properties"]["end_year"])}', fill=(200, 0, 0))
im.save(out); print(out, im.size)
