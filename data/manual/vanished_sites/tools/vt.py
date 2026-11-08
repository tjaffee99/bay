"""Vanished-sites tracing tools (scratch).

  python -I vt.py topos W S E N [scale]            -> list USGS HTMC sheets (+ revision years)
  python -I vt.py topo  TIF_URL CX CY HALF OUT.png [--res 1] [--roads] [--grid 50]
  python -I vt.py wb    RELEASE CX CY HALF OUT.png [--z 19] [--roads] [--grid 50]

Frames: every render is a north-up local frame in metres around (CX, CY) = lon, lat
(x east, y north, equirectangular at the centre latitude: x = (lon-CX)*k, y = (lat-CY)*110574,
k = 111320 cos(CY)) — the same frame as the landmark kit (lngLatToLocal). Pixel (i, j) ->
x = -HALF + (i+0.5)*res, y = HALF - (j+0.5)*res. Grid lines every --grid m, labelled.
"""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
CACHE.mkdir(exist_ok=True)
os.environ.setdefault("CURL_CA_BUNDLE", "/root/.ccr/ca-bundle.crt")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "4")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "2")
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("VSI_CACHE", "TRUE")
OVT = Path("/home/user/bay/data/raw/overture/2026-10-21.0")
PROJ_DIR = Path("/home/user/bay/data/raw/proj")


def curl(url, out=None, timeout=60):
    args = ["curl", "-sS", "-L", "-m", str(timeout), url]
    if out:
        args += ["-o", str(out)]
        subprocess.run(args, check=True)
        return out
    return subprocess.run(args, capture_output=True, check=True).stdout


# ------------------------------------------------------------------ frames
def kfac(cy):
    return 111320 * math.cos(math.radians(cy))


def ll2loc(lon, lat, cx, cy):
    return (np.asarray(lon) - cx) * kfac(cy), (np.asarray(lat) - cy) * 110574


def loc2ll(x, y, cx, cy):
    return cx + np.asarray(x) / kfac(cy), cy + np.asarray(y) / 110574


# ------------------------------------------------------------------ USGS topo
def topo_list(w, s, e, n, scale=None):
    key = CACHE / f"tnm_{w}_{s}_{e}_{n}.json"
    if not key.exists():
        u = ("https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Historical%20Topographic%20Maps"
             f"&bbox={w},{s},{e},{n}&outputFormat=JSON&max=200")
        key.write_bytes(curl(u, timeout=90))
    items = json.loads(key.read_text())["items"]
    out = []
    for it in items:
        if scale and f"1:{scale}-scale" not in it["title"]:
            continue
        out.append(it)
    return out


def topo_years(it):
    """Imprint / aerial photo / field check / photo revision years from the HTMC metadata."""
    key = CACHE / ("meta_" + it["vendorMetaUrl"].split("/")[-1])
    if not key.exists():
        try:
            key.write_bytes(curl(it["vendorMetaUrl"], timeout=40))
        except Exception:
            return {}
    x = key.read_text(errors="ignore")
    yrs = {}
    for desc, date in re.findall(r"<procdesc>([^<]*Year[^<]*)</procdesc>\s*<procdate>(\d{4})", x):
        yrs[desc.replace(" Year", "").strip()] = int(date)
    return yrs


_TO = {}


def nad27_tfs(crs_wkt):
    import pyproj
    if crs_wkt not in _TO:
        pyproj.datadir.append_data_dir(str(PROJ_DIR))
        crs = pyproj.CRS.from_wkt(crs_wkt)
        geo = crs.geodetic_crs
        from pyproj.transformer import TransformerGroup
        aoi = pyproj.aoi.AreaOfInterest(-123.5, 36.5, -121.0, 38.8)
        tg = TransformerGroup("EPSG:4326", geo, always_xy=True, area_of_interest=aoi)
        t_ll = tg.transformers[0]               # WGS84 -> NAD27 (NADCON)
        t_pr = pyproj.Transformer.from_crs(geo, crs, always_xy=True)
        _TO[crs_wkt] = (t_ll, t_pr)
    return _TO[crs_wkt]


def render_topo(url, cx, cy, half, res=1.0, shift=(0.0, 0.0)):
    """Topo sheet resampled into the local frame (RGB uint8, H x W). shift = (dx, dy) m added
    to the map's positions (map feature at p appears at p + shift)."""
    import rasterio
    from rasterio.windows import Window
    import cv2
    n = int(round(2 * half / res))
    xs = -half + (np.arange(n) + 0.5) * res - shift[0]
    ys = half - (np.arange(n) + 0.5) * res - shift[1]
    X, Y = np.meshgrid(xs, ys)
    lon, lat = loc2ll(X, Y, cx, cy)
    src = url if url.startswith("/") else "/vsicurl/" + url
    with rasterio.open(src) as r:
        t_ll, t_pr = nad27_tfs(r.crs.to_wkt())
        lo27, la27 = t_ll.transform(lon.ravel(), lat.ravel())
        px, py = t_pr.transform(lo27, la27)
        inv = ~r.transform
        col, row = inv * (np.asarray(px), np.asarray(py))
        col = col.reshape(X.shape); row = row.reshape(X.shape)
        c0, c1 = int(max(0, np.floor(col.min()) - 2)), int(min(r.width, np.ceil(col.max()) + 2))
        r0, r1 = int(max(0, np.floor(row.min()) - 2)), int(min(r.height, np.ceil(row.max()) + 2))
        if c1 <= c0 or r1 <= r0:
            raise ValueError("outside sheet")
        arr = r.read(window=Window(c0, r0, c1 - c0, r1 - r0))
        arr = np.moveaxis(arr, 0, -1)[:, :, :3] if arr.shape[0] >= 3 else np.repeat(arr[0][:, :, None], 3, 2)
        if r.count == 1 and r.colormap(1):
            cm = r.colormap(1)
            lut = np.array([cm.get(i, (0, 0, 0, 0))[:3] for i in range(256)], np.uint8)
            arr = lut[arr[:, :, 0]]
    out = cv2.remap(np.ascontiguousarray(arr), (col - c0).astype(np.float32), (row - r0).astype(np.float32),
                    cv2.INTER_LINEAR, borderValue=(255, 255, 255))
    return out


# ------------------------------------------------------------------ Esri Wayback
WB = json.loads((HERE / "wayback.json").read_text()) if (HERE / "wayback.json").exists() else {}


def render_wb(release, cx, cy, half, z=19, res=None):
    import cv2
    from PIL import Image
    tmpl = WB[str(release)]["itemURL"]
    mpp = 156543.03392 * math.cos(math.radians(cy)) / 2 ** z
    res = res or mpp
    n = int(round(2 * half / res))
    xs = -half + (np.arange(n) + 0.5) * res
    ys = half - (np.arange(n) + 0.5) * res
    X, Y = np.meshgrid(xs, ys)
    lon, lat = loc2ll(X, Y, cx, cy)
    N = 256 * 2 ** z
    gx = (lon + 180) / 360 * N
    s = np.sin(np.radians(lat))
    gy = (0.5 - np.log((1 + s) / (1 - s)) / (4 * np.pi)) * N
    tx0, tx1 = int(gx.min() // 256), int(gx.max() // 256)
    ty0, ty1 = int(gy.min() // 256), int(gy.max() // 256)
    mos = np.zeros(((ty1 - ty0 + 1) * 256, (tx1 - tx0 + 1) * 256, 3), np.uint8)
    tdir = CACHE / f"wb{release}"
    tdir.mkdir(exist_ok=True)
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            fn = tdir / f"{z}_{tx}_{ty}.jpg"
            if not fn.exists() or fn.stat().st_size < 200:
                try:
                    curl(tmpl.format(level=z, row=ty, col=tx), fn, timeout=40)
                except Exception:
                    continue
            try:
                im = np.asarray(Image.open(fn).convert("RGB"))
            except Exception:
                continue
            mos[(ty - ty0) * 256:(ty - ty0 + 1) * 256, (tx - tx0) * 256:(tx - tx0 + 1) * 256] = im
    return cv2.remap(mos, (gx - tx0 * 256).astype(np.float32), (gy - ty0 * 256).astype(np.float32), cv2.INTER_LINEAR)


# ------------------------------------------------------------------ overlays
def roads_local(cx, cy, half):
    import duckdb
    dl = half / kfac(cy) * 1.2
    dd = half / 110574 * 1.2
    out = []
    for f in ("roads_local", "roads_region"):
        q = (f"select id, class, ST_AsWKB(geometry) g from read_parquet('{OVT / (f + '.parquet')}') "
             f"where ST_XMin(geometry) < {cx + dl} and ST_XMax(geometry) > {cx - dl} "
             f"and ST_YMin(geometry) < {cy + dd} and ST_YMax(geometry) > {cy - dd}")
        con = duckdb.connect()
        con.execute("LOAD spatial;")
        try:
            out += con.execute(q).fetchall()
        except Exception as e:
            print("roads", f, e)
    return out


def annotate(img, cx, cy, half, res, grid=50, roads=False, polys=(), color=(255, 0, 0), labels=True):
    from PIL import Image, ImageDraw
    import shapely.wkb
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    n = img.shape[0]

    def P(x, y):
        return ((x + half) / res, (half - y) / res)
    if grid:
        k = int(half // grid)
        for i in range(-k, k + 1):
            v = i * grid
            c = (0, 160, 255) if i else (0, 255, 255)
            d.line([P(v, -half), P(v, half)], fill=c, width=1)
            d.line([P(-half, v), P(half, v)], fill=c, width=1)
            if labels and i % 2 == 0:
                d.text((P(v, half)[0] + 2, 2), str(int(v)), fill=(0, 0, 200))
                d.text((2, P(0, v)[1] + 2), str(int(v)), fill=(0, 0, 200))
    if roads:
        for rid, cls, g in roads_local(cx, cy, half):
            ln = shapely.wkb.loads(bytes(g))
            x, y = ll2loc(*np.asarray(ln.coords).T, cx, cy)
            d.line([P(a, b) for a, b in zip(x, y)], fill=(255, 0, 255), width=1)
    for p in polys:
        x, y = p
        d.line([P(a, b) for a, b in zip(x, y)], fill=color, width=2)
    return im


def main():
    a = sys.argv[1:]
    if a[0] == "topos":
        w, s, e, n = map(float, a[1:5])
        scale = a[5] if len(a) > 5 else None
        for it in sorted(topo_list(w, s, e, n, scale), key=lambda x: x["title"]):
            print(it["title"].replace("USGS ", "").replace("-scale Quadrangle for", ""), "|",
                  topo_years(it), "|", it["urls"].get("GeoTIFF"))
        return
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("mode"); ap.add_argument("src"); ap.add_argument("cx", type=float); ap.add_argument("cy", type=float)
    ap.add_argument("half", type=float); ap.add_argument("out")
    ap.add_argument("--res", type=float, default=1.0); ap.add_argument("--z", type=int, default=19)
    ap.add_argument("--grid", type=float, default=50); ap.add_argument("--roads", action="store_true")
    ap.add_argument("--shift", default="0,0"); ap.add_argument("--geojson", default="")
    o = ap.parse_args(a)
    if o.mode == "topo":
        img = render_topo(o.src, o.cx, o.cy, o.half, o.res, tuple(map(float, o.shift.split(","))))
        res = o.res
    else:
        img = render_wb(o.src, o.cx, o.cy, o.half, o.z, o.res if o.res != 1.0 else None)
        res = 2 * o.half / img.shape[0]
    polys = []
    if o.geojson:
        import shapely
        from shapely.geometry import shape
        for f in json.loads(Path(o.geojson).read_text())["features"]:
            g = shape(f["geometry"])
            for p in getattr(g, "geoms", [g]):
                rings = [p.exterior, *p.interiors] if p.geom_type == "Polygon" else [p]
                for r in rings:
                    polys.append(ll2loc(*np.asarray(r.coords).T, o.cx, o.cy))
    im = annotate(img, o.cx, o.cy, o.half, res, o.grid, o.roads, polys)
    im.save(o.out)
    print(o.out, im.size, "res", round(res, 3))


if __name__ == "__main__":
    main()
