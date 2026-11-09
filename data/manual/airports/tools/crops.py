"""Same crop of several renders (same frame), today's pavement drawn thin, in a grid.

  python -I crops.py CX CY HALF RES TODAY.geojson OUT.png LON LAT CHALF NAME=IMG.npy ... [--cols 3] [--zoom 2] [--noov]
Crop grid every 50 m labelled with local metres of the crop centre (x east, y north).
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
opt = {s.split("=")[0]: s.split("=", 1)[1] if "=" in s else True for s in sys.argv[1:] if s.startswith("--")}
cx, cy, H, res = map(float, a[0:4]); feats = json.loads(Path(a[4]).read_text())["features"]; out = a[5]
lon, lat, ch = map(float, a[6:9]); specs = a[9:]
cols = int(opt.get("--cols", 3)); zoom = float(opt.get("--zoom", 2)); ov = "--noov" not in opt
cls = opt.get("--classes", "runway,stopway").split(","); gstep = float(opt.get("--grid", 100))
ox, oy = vt.ll2loc(lon, lat, cx, cy); ox, oy = float(ox), float(oy)
COL = {"runway": (255, 0, 0), "stopway": (255, 140, 0), "taxiway": (220, 0, 220), "taxilane": (140, 0, 255),
       "apron": (0, 160, 255)}
panels = []
for spec in specs:
    name, _, f = spec.partition("=")
    img = np.load(f, mmap_mode="r")
    i0, i1 = int((ox - ch + H) / res), int((ox + ch + H) / res); j0, j1 = int((H - oy - ch) / res), int((H - oy + ch) / res)
    im = Image.fromarray(np.ascontiguousarray(img[max(j0, 0):j1, max(i0, 0):i1]))
    im = im.resize((int(im.size[0] * zoom), int(im.size[1] * zoom)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    P = lambda x, y: (((x - ox) + ch) / res * zoom, (ch - (y - oy)) / res * zoom)
    for v in np.arange(-(ch // gstep) * gstep, ch + 1, gstep):
        c = (150, 220, 220) if v % 500 else (0, 120, 255)
        d.line([P(ox + v, oy - ch), P(ox + v, oy + ch)], fill=c, width=1)
        d.line([P(ox - ch, oy + v), P(ox + ch, oy + v)], fill=c, width=1)
        if v % (2 * gstep) == 0:
            d.text((P(ox + v, 0)[0] + 2, 2), str(int(v)), fill=(0, 0, 200))
            d.text((2, P(0, oy + v)[1] + 2), str(int(v)), fill=(0, 0, 200))
    if ov:
        for ft in feats:
            cl = ft["properties"]["class"]
            if cl not in COL or cl not in cls:
                continue
            g = shape(ft["geometry"])
            for p in getattr(g, "geoms", [g]):
                rings = [p.exterior] if p.geom_type == "Polygon" else [p]
                for r in rings:
                    x, y = vt.ll2loc(*np.asarray(r.coords).T, cx, cy)
                    d.line([P(u, v) for u, v in zip(x, y)], fill=COL[cl], width=1)
    if opt.get("--bldg"):
        for ft in json.loads(Path(opt["--bldg"]).read_text())["features"]:
            g = shape(ft["geometry"])
            for p in getattr(g, "geoms", [g]):
                x, y = vt.ll2loc(*np.asarray(p.exterior.coords).T, cx, cy)
                d.line([P(u, v) for u, v in zip(x, y)], fill=(0, 170, 0), width=1)
    d.rectangle([0, im.size[1] - 16, 60, im.size[1]], fill=(255, 255, 255)); d.text((3, im.size[1] - 14), name, fill=(255, 0, 0))
    panels.append(im)
w, h = panels[0].size; rows = (len(panels) + cols - 1) // cols
o = Image.new("RGB", (cols * (w + 3), rows * (h + 3)), (0, 0, 0))
for k, p in enumerate(panels):
    o.paste(p, ((k % cols) * (w + 3), (k // cols) * (h + 3)))
o.save(out); print(out, o.size)
