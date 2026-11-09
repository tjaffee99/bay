"""Vanished airport buildings from the topo editions: building symbols (solid, cross-hatched, purple
photorevision fills) inside the airport that no footprint of today covers, tracked across editions.

  python -I vanish.py AP CX CY HALF RES OUTLINE.geojson BLDG.geojson OUT.geojson NAME=IMG.npy ...

A symbol is kept when >= 150 m2 after a 6 m opening (drops lines and lettering) and less than 25 %
of it lies under today's footprints (+4 m). Symbols of successive editions are one building when
their IoU >= 0.3 (or one holds >= 60 % of the other). start = midpoint of the last edition without
it and the first with it (drawn on the first edition: that edition's year, flagged), end = midpoint
of the last edition with it and the next one without it (photorevisions rarely delete buildings:
a building still drawn on the last edition ends at that edition + 5, estimated). Output: local
polygons converted to lon/lat with the edition sequence in `note`.
"""
import json
import sys
from pathlib import Path

import cv2
import geopandas as gpd
import numpy as np
import shapely
from shapely.geometry import Polygon, shape, mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vanished_sites" / "tools"))
import vt  # noqa: E402


def bmask(img, res):
    r, g, b = (img[:, :, i].astype(int) for i in range(3))
    dark = (r < 120) & (g < 120) & (b < 120) & (np.abs(r - g) < 45) & (np.abs(g - b) < 45)
    purple = ((r - g) > 38) & ((b - g) > 18) & (g < 175)
    ink = (dark | purple).astype(np.float32)
    k = max(3, int(round(7 / res)) | 1)
    den = cv2.blur(ink, (k, k))
    m = ((den > 0.33) | (cv2.blur(ink, (3, 3)) > 0.9)).astype(np.uint8)
    o = max(1, int(round(6 / res)))
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (o, o)))


def main():
    a = sys.argv[1:]
    ap = a[0]; cx, cy, H, res = map(float, a[1:5])
    outline = shapely.union_all([shape(f["geometry"]) for f in json.loads(Path(a[5]).read_text())["features"]])
    bl = gpd.read_file(a[6]); out = a[7]
    eds = []
    for spec in a[8:]:
        n, _, f = spec.partition("=")
        eds.append((int(n), np.load(f, mmap_mode="r")))
    n = eds[0][1].shape[0]
    to_px = lambda x, y: np.c_[(np.asarray(x) + H) / res, (H - np.asarray(y)) / res]
    om = np.zeros((n, n), np.uint8)
    for p in getattr(outline, "geoms", [outline]):
        x, y = vt.ll2loc(*np.asarray(p.exterior.coords).T, cx, cy)
        cv2.fillPoly(om, [np.round(to_px(x, y)).astype(np.int32)], 1)
    fm = np.zeros((n, n), np.uint8)
    for g in bl.geometry.values:
        for p in getattr(g, "geoms", [g]):
            x, y = vt.ll2loc(*np.asarray(p.exterior.coords).T, cx, cy)
            cv2.fillPoly(fm, [np.round(to_px(x, y)).astype(np.int32)], 1)
    fm = cv2.dilate(fm, np.ones((max(1, int(4 / res)) * 2 + 1,) * 2, np.uint8))
    per = []
    for yr, img in eds:
        m = bmask(np.asarray(img), res) & om
        cnt, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
        polys = []
        for i in range(1, cnt):
            if st[i, cv2.CC_STAT_AREA] * res * res < 150:
                continue
            comp = (lab == i).astype(np.uint8)
            if (comp & fm).sum() / comp.sum() >= 0.25:
                continue
            cs, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            c = max(cs, key=cv2.contourArea)
            rect = cv2.minAreaRect(c)
            fill = comp.sum() / max(rect[1][0] * rect[1][1], 1)
            pts = cv2.boxPoints(rect) if fill > 0.8 else cv2.approxPolyDP(c, 1.5 / res, True)[:, 0, :].astype(float)
            if len(pts) < 3:
                continue
            P = Polygon([(-H + (px + 0.5) * res, H - (py + 0.5) * res) for px, py in pts]).buffer(0)
            if P.geom_type != "Polygon":
                P = max(getattr(P, "geoms", [P]), key=lambda q: q.area)
            if P.area < 150 or P.is_empty or P.area > 25000:
                continue
            if P.area / P.minimum_rotated_rectangle.area < 0.6:
                continue  # lettering, tints, irregular ink
            # skip long thin things (roads, runways edges)
            w, h = sorted(rect[1])
            if w * res < 6 or h / max(w, 1) > 12:
                continue
            polys.append(P)
        per.append((yr, polys))
        print(yr, len(polys), "symbols")
    # chains
    chains = []
    for k, (yr, polys) in enumerate(per):
        for P in polys:
            hit = None
            for ch in chains:
                Q = ch["polys"][-1]
                if ch["last_k"] < k - 2:
                    continue
                inter = P.intersection(Q).area
                if inter / P.union(Q).area >= 0.3 or inter / min(P.area, Q.area) >= 0.6:
                    hit = ch
                    break
            if hit and hit["last_k"] != k:
                hit["polys"].append(P); hit["ks"].append(k); hit["last_k"] = k
            elif not hit:
                chains.append(dict(polys=[P], ks=[k], last_k=k))
    years = [y for y, _ in per]
    feats = []
    for ch in chains:
        k0, k1 = ch["ks"][0], ch["ks"][-1]
        P0 = ch["polys"][0]
        fill0 = P0.area / P0.minimum_rotated_rectangle.area
        fills = [q.area / q.minimum_rotated_rectangle.area for q in ch["polys"]]
        if np.median(fills) < 0.75 or max(q.area for q in ch["polys"]) < 250:
            continue
        if len(ch["ks"]) == 1 and not (P0.area >= 1000 and fill0 >= 0.85):
            continue  # one-off blob: probably lettering or a symbol
        start = (years[k0 - 1] + years[k0]) / 2 if k0 > 0 else float(years[0])
        end = (years[k1] + years[k1 + 1]) / 2 if k1 + 1 < len(years) else years[k1] + 5.0
        P = max(ch["polys"], key=lambda q: q.area) if len(ch["polys"]) < 3 else ch["polys"][len(ch["polys"]) // 2]
        x, y = np.asarray(P.exterior.coords).T
        lon, lat = vt.loc2ll(x, y, cx, cy)
        feats.append({"type": "Feature", "geometry": mapping(Polygon(np.c_[lon, lat]).buffer(0)),
                      "properties": {"airport": ap, "start_year": round(start, 1), "end_year": round(end, 1),
                                     "first_drawn": years[k0], "last_drawn": years[k1],
                                     "drawn_on": ",".join(str(years[k]) for k in ch["ks"]),
                                     "area_m2": round(P.area), "starts_on_first_edition": k0 == 0}})
    Path(out).write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    print(out, len(feats), "vanished-building candidates")


if __name__ == "__main__":
    main()
