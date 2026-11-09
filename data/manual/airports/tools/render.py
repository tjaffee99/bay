"""Render an airport on USGS topo editions (mosaic of 7.5' quads clipped at their neatlines).

  python -I render.py CX CY HALF RES OUT.png SHEET[,SHEET...] [--grid 250] [--geojson F] [--label L]

SHEET = a GeoTIFF file name under the HTMC staging folder (CA_..._geo.tif) or a full URL,
followed by ':W,S' = the quad's SW corner in NAD27 degrees (7.5' quads: 0.125 deg; 15' quads
':W,S,0.25'). Each pixel takes the sheet whose quad contains it (no collars). Frame and
conventions as ../../vanished_sites/tools/vt.py (north-up local metres around CX, CY).
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


def render(cx, cy, half, res, sheets):
    import pyproj
    n = int(round(2 * half / res))
    xs = -half + (np.arange(n) + 0.5) * res
    X, Y = np.meshgrid(xs, -xs)
    lon, lat = vt.loc2ll(X, Y, cx, cy)
    out = np.full((n, n, 3), 255, np.uint8)
    # NAD27 position of every pixel (quad bounds are NAD27 graticule lines)
    pyproj.datadir.append_data_dir(str(vt.PROJ_DIR))
    from pyproj.transformer import TransformerGroup
    tg = TransformerGroup("EPSG:4326", "EPSG:4267", always_xy=True,
                          area_of_interest=pyproj.aoi.AreaOfInterest(-123.5, 36.5, -121.0, 38.8))
    lo27, la27 = tg.transformers[0].transform(lon.ravel(), lat.ravel())
    lo27 = np.asarray(lo27).reshape(lon.shape); la27 = np.asarray(la27).reshape(lon.shape)
    for spec in sheets:
        name, _, q = spec.rpartition(":") if ":" in spec.split("/")[-1] else (spec, "", "")
        url = name if name.startswith("http") or name.startswith("/") else U + name.replace(" ", "%20")
        try:
            img = vt.render_topo(url, cx, cy, half, res)
        except Exception as e:  # noqa: BLE001
            print("fail", name, e)
            continue
        if q:
            v = list(map(float, q.split(",")))
            w, s = v[0], v[1]
            sz = v[2] if len(v) > 2 else 0.125
            m = (lo27 >= w) & (lo27 < w + sz) & (la27 >= s) & (la27 < s + sz)
        else:
            m = np.ones(lon.shape, bool)
        out[m] = img[m]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cx", type=float); ap.add_argument("cy", type=float)
    ap.add_argument("half", type=float); ap.add_argument("res", type=float)
    ap.add_argument("out"); ap.add_argument("sheets")
    ap.add_argument("--grid", type=float, default=250); ap.add_argument("--geojson", default="")
    ap.add_argument("--label", default=""); ap.add_argument("--npy", action="store_true")
    o = ap.parse_args()
    img = render(o.cx, o.cy, o.half, o.res, o.sheets.split(","))
    if o.npy:
        np.save(o.out.replace(".png", ".npy"), img)
    polys = []
    if o.geojson:
        from shapely.geometry import shape
        for f in json.loads(Path(o.geojson).read_text())["features"]:
            g = shape(f["geometry"])
            for p in getattr(g, "geoms", [g]):
                rings = [p.exterior, *p.interiors] if p.geom_type == "Polygon" else [p]
                for r in rings:
                    polys.append(vt.ll2loc(*np.asarray(r.coords).T, o.cx, o.cy))
    im = vt.annotate(img, o.cx, o.cy, o.half, o.res, o.grid, False, polys)
    if o.label:
        from PIL import ImageDraw
        ImageDraw.Draw(im).text((8, im.size[1] - 16), o.label, fill=(255, 0, 0))
    im.save(o.out)
    print(o.out, im.size)


if __name__ == "__main__":
    main()
