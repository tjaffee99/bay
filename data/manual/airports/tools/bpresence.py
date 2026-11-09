"""Footprint presence on rendered editions (npy renders of render.py, same frame).

  python -I bpresence.py CX CY HALF RES BLDG.geojson OUT.csv NAME=IMG.npy ...

Per footprint and edition: `solid` = share of the footprint (+4 m) covered by ink after a
6 m opening (solid building symbols, as the industrial-sites dating), `raw` = share of the
footprint (shrunk by 2 m) covered by raw ink (catches the cross-hatched symbol of large
buildings, which the opening removes). present = solid >= 0.30 or (area >= 1500 m2 and
raw >= 0.20) or (area >= 600 m2 and raw >= 0.35).
"""
import sys
from pathlib import Path

import cv2
import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vanished_sites" / "tools"))
import vt  # noqa: E402


def ink(img):
    r, g, b = (img[:, :, i].astype(int) for i in range(3))
    m = (r < 115) & (g < 115) & (b < 115) & (np.abs(r - g) < 40) & (np.abs(g - b) < 40)
    m |= ((r - g) > 38) & ((b - g) > 18) & (g < 175)
    return m.astype(np.uint8)


def main():
    a = sys.argv[1:]
    cx, cy, H, res = map(float, a[0:4])
    fps = gpd.read_file(a[4]); out = a[5]
    fps = fps[fps.geometry.geom_type == "Polygon"].reset_index(drop=True)
    area = fps.to_crs(32610).area.values
    rows = []
    eds = []
    for spec in a[6:]:
        name, _, f = spec.partition("=")
        img = np.load(f, mmap_mode="r")
        m = ink(np.asarray(img))
        k = max(1, int(round(6.0 / res)))
        mo = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
        blank = (np.asarray(img).astype(int).sum(2) >= 3 * 254)   # outside every sheet
        eds.append((name, m, mo, blank))
    n = eds[0][1].shape[0]
    for i, g in enumerate(fps.geometry.values):
        x, y = vt.ll2loc(*np.asarray(g.exterior.coords).T, cx, cy)
        px = np.c_[(x + H) / res, (H - y) / res]
        i0, j0 = int(max(0, px[:, 0].min() - 6)), int(max(0, px[:, 1].min() - 6))
        i1, j1 = int(min(n, px[:, 0].max() + 7)), int(min(n, px[:, 1].max() + 7))
        if i1 <= i0 or j1 <= j0:
            continue
        pm = np.zeros((j1 - j0, i1 - i0), np.uint8)
        cv2.fillPoly(pm, [np.round(px - [i0, j0]).astype(np.int32)], 1)
        pb = cv2.dilate(pm, np.ones((5, 5), np.uint8))
        ps = cv2.erode(pm, np.ones((3, 3), np.uint8))
        if ps.sum() < 3:
            ps = pm
        r = {"fi": i, "id": fps.id[i], "name": fps.get("name", pd.Series([None] * len(fps)))[i], "area_m2": round(area[i]),
             "lon": round(g.representative_point().x, 6), "lat": round(g.representative_point().y, 6)}
        for name, m, mo, blank in eds:
            if blank[j0:j1, i0:i1][pm > 0].mean() > 0.5:
                r[f"{name}"] = ""
                continue
            solid = mo[j0:j1, i0:i1][pb > 0].mean() if pb.any() else 0
            raw = m[j0:j1, i0:i1][ps > 0].mean() if ps.any() else 0
            pres = solid >= 0.30 or (area[i] >= 1500 and raw >= 0.20) or (area[i] >= 600 and raw >= 0.35)
            r[f"{name}"] = f"{'P' if pres else '-'}{solid:.2f}/{raw:.2f}"
        rows.append(r)
    pd.DataFrame(rows).to_csv(out, index=False)
    print(out, len(rows))


if __name__ == "__main__":
    main()
