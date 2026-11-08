"""Helpers for Sanborn / photo georeferencing in a site's local metre frame."""
import json, math, sys
from pathlib import Path
import numpy as np
import shapely
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, LineString, Point
HERE = Path(__file__).resolve().parent
OVT = Path('/home/user/bay/data/raw/overture/2026-10-21.0')

def kf(cy): return 111320 * math.cos(math.radians(cy))
def to_loc(g, cx, cy):
    k = kf(cy); return shapely.transform(g, lambda xy: np.column_stack([(xy[:, 0] - cx) * k, (xy[:, 1] - cy) * 110574]))
def to_ll(g, cx, cy):
    k = kf(cy); return shapely.transform(g, lambda xy: np.column_stack([cx + xy[:, 0] / k, cy + xy[:, 1] / 110574]))

_P = {}
def parcels(path=HERE / 'parcels_oak.parquet'):
    if path not in _P:
        _P[path] = gpd.read_parquet(path)
    return _P[path]

def blocks_near(cx, cy, half=400, path=HERE / 'parcels_oak.parquet'):
    """Blocks (unions of today's parcels, touching parcels merged) around (cx, cy), local metres."""
    p = parcels(path)
    k = kf(cy)
    box = shapely.box(cx - half / k, cy - half / 110574, cx + half / k, cy + half / 110574)
    q = p.iloc[p.sindex.query(box, predicate='intersects')]
    loc = [to_loc(g, cx, cy) for g in q.geometry]
    u = shapely.union_all([g.buffer(0.6, join_style=2) for g in loc]).buffer(-0.6, join_style=2)
    return [g for g in getattr(u, 'geoms', [u]) if g.area > 500]

def roads_near(cx, cy, half=400, files=('roads_local', 'roads_region')):
    import duckdb
    k = kf(cy); dl = half / k; dd = half / 110574
    out = []
    con = duckdb.connect(); con.execute('LOAD spatial;')
    for f in files:
        q = (f"select id, class, name, ST_AsWKB(geometry) g from read_parquet('{OVT / (f + '.parquet')}') "
             f"where ST_XMin(geometry) < {cx + dl} and ST_XMax(geometry) > {cx - dl} and ST_YMin(geometry) < {cy + dd} and ST_YMax(geometry) > {cy - dd}")
        for i, c, n, g in con.execute(q).fetchall():
            out.append((i, c, n, to_loc(shapely.from_wkb(bytes(g)), cx, cy), f))
    return out

def fit_similarity(src, dst):
    """least squares similarity (scale, rotation, translation) src -> dst (N x 2)."""
    src, dst = np.asarray(src, float), np.asarray(dst, float)
    ms, md = src.mean(0), dst.mean(0)
    a, b = src - ms, dst - md
    zs = a[:, 0] + 1j * a[:, 1]; zd = b[:, 0] + 1j * b[:, 1]
    c = (np.conj(zs) @ zd) / (np.conj(zs) @ zs)
    def f(p):
        p = np.asarray(p, float); z = (p[..., 0] - ms[0]) + 1j * (p[..., 1] - ms[1])
        w = c * z
        return np.stack([w.real + md[0], w.imag + md[1]], -1)
    res = f(src) - dst
    return f, abs(c), np.degrees(np.angle(c)), np.sqrt((res ** 2).sum(1))

def fit_affine(src, dst):
    src, dst = np.asarray(src, float), np.asarray(dst, float)
    A = np.column_stack([src, np.ones(len(src))])
    M, *_ = np.linalg.lstsq(A, dst, rcond=None)
    def f(p):
        p = np.asarray(p, float); return np.concatenate([p, np.ones(p.shape[:-1] + (1,))], -1) @ M
    res = f(src) - dst
    return f, M, np.sqrt((res ** 2).sum(1))

def fit_homography(src, dst):
    import cv2
    H, _ = cv2.findHomography(np.asarray(src, np.float64), np.asarray(dst, np.float64), 0)
    def f(p):
        p = np.asarray(p, float); q = np.concatenate([p, np.ones(p.shape[:-1] + (1,))], -1) @ H.T
        return q[..., :2] / q[..., 2:3]
    res = f(src) - np.asarray(dst)
    return f, H, np.sqrt((res ** 2).sum(1))

def poly_px_to_loc(coords_px, f):
    return Polygon(f(np.asarray(coords_px, float)))

def grid_crop(img_path, x0, y0, x1, y1, out, step=50, scale=1.0, marks=()):
    from PIL import Image, ImageDraw
    im = Image.open(img_path).convert('RGB').crop((x0, y0, x1, y1))
    if scale != 1.0:
        im = im.resize((int(im.size[0] * scale), int(im.size[1] * scale)))
    d = ImageDraw.Draw(im)
    for x in range((x0 // step + 1) * step, x1, step):
        X = (x - x0) * scale; d.line([(X, 0), (X, im.size[1])], fill=(255, 0, 0) if x % (step * 2) == 0 else (255, 150, 150)); d.text((X + 2, 2), str(x), fill=(200, 0, 0))
    for y in range((y0 // step + 1) * step, y1, step):
        Y = (y - y0) * scale; d.line([(0, Y), (im.size[0], Y)], fill=(255, 0, 0) if y % (step * 2) == 0 else (255, 150, 150)); d.text((2, Y + 2), str(y), fill=(200, 0, 0))
    for (x, y, c) in marks:
        X, Y = (x - x0) * scale, (y - y0) * scale; d.ellipse([X - 4, Y - 4, X + 4, Y + 4], outline=c, width=2)
    im.save(out)
