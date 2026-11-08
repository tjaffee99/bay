"""Extract a quarry / landfill / plant outline from one USGS topo edition by colour.

  python -I tint.py CX CY HALF OUT.geojson URL MODE [--res 3] [--quad W,S,E,N] [--close 30]
                    [--min-ha 2] [--seed X,Y] [--preview out.png] [--keep-largest N]

MODE
  purple   photorevision overprint (1968-1980 editions): magenta lines / stipple of new
           disturbed ground, closed into areas
  tint     the brown-red "disturbed surface" tint of 1980s-90s editions (quarry pits,
           landfills, gravel pits)
  open     unwooded ground (white / pink, neither green tint nor ink): only with --seed,
           the open patch around a known quarry / plant on the older editions

The edition is resampled into the local metre frame (vanished-sites vt.render_topo: sheet
registration + NADCON, so outlines are WGS84), clipped to the sheet's quad (NAD27 corners,
--quad, so the collar and neighbouring sheets don't leak in), morphologically closed by
--close metres, holes filled, components under --min-ha dropped (or only the components
containing --seed / the N largest kept), simplified to ~res and written as lon/lat.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vanished_sites" / "tools"))
import vt  # noqa: E402

U = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/"


def colour_mask(img, mode, rg=40):
    r, g, b = (img[:, :, i].astype(int) for i in range(3))
    if mode == "purple":
        return (r - g > 35) & (b - g > 25) & (r > 120) & (b > 110)
    if mode == "tint":
        # salmon / brick tint, not the red section lines (darker, more saturated) or contours
        return (r > 185) & (r - g > rg) & (r - g < 110) & (r - b > 30) & (g > 110)
    if mode == "open":
        green = (g - r > 5) | ((g > 180) & (b < 150) & (r > 180) & (g - b > 50))  # green / yellow-green tint
        ink = (r + g + b) < 360
        return ~green & ~ink
    raise ValueError(mode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cx", type=float); ap.add_argument("cy", type=float); ap.add_argument("half", type=float)
    ap.add_argument("out"); ap.add_argument("url"); ap.add_argument("mode")
    ap.add_argument("--res", type=float, default=3.0); ap.add_argument("--quad", default="")
    ap.add_argument("--close", type=float, default=30.0); ap.add_argument("--open", type=float, default=0.0)
    ap.add_argument("--pre-open", type=float, default=0.0)
    ap.add_argument("--rg", type=float, default=40, help="tint: min red - green (lighter prints: ~18)")
    ap.add_argument("--min-ha", type=float, default=2.0); ap.add_argument("--seed", action="append", default=[])
    ap.add_argument("--keep-largest", type=int, default=0); ap.add_argument("--preview", default="")
    ap.add_argument("--clip", default="", help="geojson: keep only inside this outline")
    o = ap.parse_args()
    import cv2
    import shapely
    from rasterio import features
    from rasterio.transform import Affine
    from scipy import ndimage
    from shapely.geometry import shape, mapping, Polygon
    url = o.url if o.url.startswith(("http", "/")) else U + o.url
    img = vt.render_topo(url, o.cx, o.cy, o.half, o.res)
    m = colour_mask(img, o.mode, o.rg)
    n = img.shape[0]
    xs = -o.half + (np.arange(n) + 0.5) * o.res
    X, Y = np.meshgrid(xs, -xs)
    if o.quad:
        import pyproj
        w, s, e, nn = map(float, o.quad.split(","))
        lon, lat = vt.loc2ll(X, Y, o.cx, o.cy)
        with __import__("rasterio").open("/vsicurl/" + url if url.startswith("http") else url) as r:
            t_ll, _ = vt.nad27_tfs(r.crs.to_wkt())
        lo27, la27 = t_ll.transform(lon.ravel(), lat.ravel())
        lo27 = np.asarray(lo27).reshape(X.shape); la27 = np.asarray(la27).reshape(X.shape)
        m &= (lo27 >= w) & (lo27 <= e) & (la27 >= s) & (la27 <= nn)
    if o.pre_open > 0:  # drop thin linework (section lines, contours) before closing
        m = ndimage.binary_opening(m, structure=np.ones((3, 3)), iterations=max(1, int(round(o.pre_open / o.res))))
    k = max(1, int(round(o.close / o.res)))
    m = ndimage.binary_closing(m, structure=np.ones((3, 3)), iterations=k)
    m = ndimage.binary_fill_holes(m)
    if o.open > 0:
        m = ndimage.binary_opening(m, structure=np.ones((3, 3)), iterations=max(1, int(round(o.open / o.res))))
    lab, nl = ndimage.label(m)
    keep = np.zeros(nl + 1, bool)
    sizes = ndimage.sum(m, lab, range(nl + 1)) * o.res ** 2 / 1e4
    if o.seed:
        for sd in o.seed:
            sx, sy = map(float, sd.split(","))
            i = int((sx + o.half) / o.res); j = int((o.half - sy) / o.res)
            if 0 <= i < n and 0 <= j < n and lab[j, i] > 0:
                keep[lab[j, i]] = True
    elif o.keep_largest:
        keep[np.argsort(sizes)[::-1][:o.keep_largest]] = True
    else:
        keep = sizes >= o.min_ha
    keep[0] = False
    m = keep[lab]
    t = Affine(o.res, 0, -o.half, 0, -o.res, o.half)
    polys = [shape(g) for g, v in features.shapes(m.astype(np.uint8), mask=m, transform=t) if v == 1]
    polys = [p.simplify(o.res, preserve_topology=True) for p in polys]
    polys = [p for p in polys if p.area / 1e4 >= min(o.min_ha, 0.5)]
    if o.clip:
        cl = shapely.union_all([shape(f["geometry"]) for f in json.loads(Path(o.clip).read_text())["features"]])
        # clip outline given in lon/lat
        polys = [p for p in polys]
        ll = []
        for p in polys:
            x, y = np.asarray(p.exterior.coords).T
            lo, la = vt.loc2ll(x, y, o.cx, o.cy)
            q = Polygon(np.c_[lo, la]).intersection(cl)
            if not q.is_empty:
                ll.append(q)
    else:
        ll = []
        for p in polys:
            x, y = np.asarray(p.exterior.coords).T
            lo, la = vt.loc2ll(x, y, o.cx, o.cy)
            ll.append(Polygon(np.c_[lo, la]))
    feats = [{"type": "Feature", "properties": {"ha": round(shapely.area(vt_area(q, o.cx, o.cy)) / 1e4, 1)},
              "geometry": mapping(q)} for q in ll]
    Path(o.out).write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    print(o.out, len(feats), "parts", [f["properties"]["ha"] for f in feats])
    if o.preview:
        pv = img.copy()
        edge = m ^ ndimage.binary_erosion(m, iterations=2)
        pv[edge] = (0, 0, 255)
        cv2.imwrite(o.preview, pv[:, :, ::-1])


def vt_area(q, cx, cy):
    from shapely.geometry import Polygon
    from shapely.ops import transform
    return transform(lambda x, y, z=None: vt.ll2loc(x, y, cx, cy), q)


if __name__ == "__main__":
    main()
