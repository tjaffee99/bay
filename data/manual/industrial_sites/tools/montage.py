"""Render one site on several USGS topo editions side by side (scratch viewer for tracing).

  python -I montage.py CX CY HALF OUT.png URL[@label] [URL[@label] ...] [--res 4] [--grid 250]
                       [--geojson overlay.geojson] [--cols 3]

Uses the vanished-sites renderer (../../vanished_sites/tools/vt.py): every panel is the same
north-up local metre frame around (CX, CY) (x east, y north), grid lines every --grid m with
labels, so a feature can be read off as local x / y on every edition and converted with
vt.loc2ll. Panels that fail (outside a sheet) are left blank.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vanished_sites" / "tools"))
import vt  # noqa: E402

U = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cx", type=float); ap.add_argument("cy", type=float); ap.add_argument("half", type=float)
    ap.add_argument("out"); ap.add_argument("urls", nargs="+")
    ap.add_argument("--res", type=float, default=4.0); ap.add_argument("--grid", type=float, default=250)
    ap.add_argument("--geojson", default=""); ap.add_argument("--cols", type=int, default=3)
    o = ap.parse_args()
    from PIL import Image, ImageDraw
    import json
    from shapely.geometry import shape
    polys = []
    if o.geojson:
        for f in json.loads(Path(o.geojson).read_text())["features"]:
            g = shape(f["geometry"])
            for p in getattr(g, "geoms", [g]):
                for r in ([p.exterior, *p.interiors] if p.geom_type == "Polygon" else [p]):
                    polys.append(vt.ll2loc(*np.asarray(r.coords).T, o.cx, o.cy))
    panels = []
    n = int(round(2 * o.half / o.res))
    for spec in o.urls:
        url, _, label = spec.partition("@")
        if not url.startswith("http") and not url.startswith("/"):
            url = U + url
        try:
            img = vt.render_topo(url, o.cx, o.cy, o.half, o.res)
        except Exception as e:  # noqa: BLE001
            print("fail", spec, e)
            img = np.full((n, n, 3), 255, np.uint8)
        im = vt.annotate(img, o.cx, o.cy, o.half, o.res, o.grid, False, polys)
        ImageDraw.Draw(im).text((8, n - 18), label or Path(url).name[:40], fill=(255, 0, 0))
        panels.append(im)
    cols = min(o.cols, len(panels))
    rows = (len(panels) + cols - 1) // cols
    out = Image.new("RGB", (cols * n, rows * n), (255, 255, 255))
    for i, im in enumerate(panels):
        out.paste(im, ((i % cols) * n, (i // cols) * n))
    out.save(o.out)
    print(o.out, out.size)


if __name__ == "__main__":
    main()
