"""Per-feature presence on topo editions (crossing test).

For every runway / taxiway / apron of today (Overture / OSM), sample its centreline every
4 m (aprons: an interior grid every 12 m, 8 m in from the edge) and measure on each edition:
  hit   = share of samples with map ink (black outlines, purple revision lines, building
          fills) within 2.5 m — a pavement that existed lies in the white space between the
          outlines of the unpaved islands, so its samples are clear;
  water = share of samples on blue water / mud tint.
Prints a CSV: id, class, name, length, then hit/water per edition.

  python -I presence.py CX CY RES TODAY.geojson OUT.csv NAME=IMG.npy[,HALF] ...
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import shape, Point
from shapely.prepared import prep

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vanished_sites" / "tools"))
import vt  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from corridor import masks  # noqa: E402
from scipy.ndimage import binary_dilation


def samples(g, cx, cy):
    from shapely.ops import transform
    loc = transform(lambda x, y, z=None: vt.ll2loc(x, y, cx, cy), g)
    if loc.geom_type in ("LineString", "MultiLineString"):
        L = loc.length
        return np.array([loc.interpolate(d).coords[0] for d in np.arange(2, max(L - 2, 2.1), 4.0)]), L
    inner = loc.buffer(-8)
    if inner.is_empty:
        inner = loc
    x0, y0, x1, y1 = inner.bounds
    X, Y = np.meshgrid(np.arange(x0, x1, 12.0), np.arange(y0, y1, 12.0))
    pp = prep(inner)
    pts = [(x, y) for x, y in zip(X.ravel(), Y.ravel()) if pp.contains(Point(x, y))]
    if not pts:
        pts = [inner.representative_point().coords[0]]
    return np.array(pts), loc.area


def main():
    a = sys.argv[1:]
    cx, cy, res = map(float, a[0:3])
    feats = json.loads(Path(a[3]).read_text())["features"]
    out = a[4]
    eds = []
    for spec in a[5:]:
        name, _, f = spec.partition("=")
        f, _, H = f.partition(",")
        img = np.load(f, mmap_mode="r")
        ink, water = masks(np.asarray(img))
        k = max(1, int(round(2.5 / res)))
        ink = binary_dilation(ink, iterations=k)
        eds.append((name, ink, water, float(H) if H else img.shape[0] * res / 2))
    rows = []
    for ft in feats:
        p = ft["properties"]
        if p["class"] not in ("runway", "stopway", "taxiway", "taxilane", "apron"):
            continue
        pts, size = samples(shape(ft["geometry"]), cx, cy)
        r = [p["id"], p["class"], p.get("name") or "", round(size)]
        c = shape(ft["geometry"]).representative_point()
        r += [round(c.x, 6), round(c.y, 6)]
        for name, ink, water, H in eds:
            n = ink.shape[0]
            col = np.clip(((pts[:, 0] + H) / res).astype(int), 0, n - 1)
            row = np.clip(((H - pts[:, 1]) / res).astype(int), 0, n - 1)
            inside = (pts[:, 0] > -H) & (pts[:, 0] < H) & (pts[:, 1] > -H) & (pts[:, 1] < H)
            if not inside.any():
                r += ["", ""]; continue
            r += [round(float(ink[row, col][inside].mean()), 3), round(float(water[row, col][inside].mean()), 3)]
        rows.append(r)
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "class", "name", "size", "lon", "lat"] + [f"{e[0]}_{k}" for e in eds for k in ("hit", "water")])
        w.writerows(rows)
    print(out, len(rows))


if __name__ == "__main__":
    main()
