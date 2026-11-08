"""Stage: SFEI EcoAtlas baylands (circa 1800 and circa 1998) from the vector PDF poster.

Source: SFEI "Historical Baylands / Modern Baylands" poster (Bay Area EcoAtlas,
©2001 SFEI), data/raw/sfei/pastpres2.pdf (supplied by the project owner; sfei.org
blocks automated downloads). The poster is a vector PDF: every habitat patch is
a filled path whose colour is a legend class. We

  1. rebuild polygons from the paths of each panel and classify them by colour;
  2. map the left (c.1800) panel onto the right (c.1998) one via the two map
     frames (identical extent and scale);
  3. georeference the right panel to UTM 10N with an affine transform: first a
     least-squares fit to town-label anchors, then refined by maximising the
     overlap (IoU) between the poster's modern open water and Census TIGER water;
  4. write both panels as GeoJSON (WGS84) with class names.

Accuracy: the poster generalises the EcoAtlas GIS for print; expect ~50–150 m
positional error (reported in data/interim/reports/baylands_georef.json).

Outputs: data/interim/baylands_1800.geojson, data/interim/baylands_1998.geojson
"""
from __future__ import annotations

import json
from collections import defaultdict

import geopandas as gpd
import numpy as np
import pymupdf as fitz
import shapely
from rasterio import features
from rasterio.transform import from_origin
from scipy.optimize import minimize
from shapely.affinity import affine_transform
from shapely.geometry import Polygon, box

from common import INTERIM, RAW, log
from download_sf import BAY_COUNTIES

PDF = RAW / "sfei" / "pastpres2.pdf"
UTM = "EPSG:32610"
REPORTS = INTERIM / "reports"

# legend colours (rounded RGB 0-1) -> class
CLASSES = {
    (0.647, 0.773, 0.847): "deep_bay",
    (0.804, 0.878, 0.922): "shallow_bay",
    (0.365, 0.306, 0.329): "tidal_flat",
    (0.71, 0.71, 0.275): "tidal_marsh",
    (0.306, 0.353, 0.498): "tidal_marsh_pan",
    (0.247, 0.514, 0.624): "perennial_pond",
    (0.31, 0.482, 0.725): "lagoon",
    (0.945, 0.796, 0.737): "salt_pond",
    (0.325, 0.608, 0.388): "riparian_forest",
    (0.702, 0.808, 0.616): "moist_grassland",
    (0.949, 0.765, 0.455): "grassland_vernal_pool",
    (0.604, 0.502, 0.361): "agricultural_bayland",
    (0.686, 0.639, 0.412): "diked_wetland",
    (0.753, 0.576, 0.553): "storage_pond",
    (0.714, 0.729, 0.863): "undeveloped_fill",
    (0.545, 0.518, 0.624): "developed_fill",
}
WATER_MODERN = {"deep_bay", "shallow_bay", "tidal_flat", "lagoon", "salt_pond", "storage_pond", "perennial_pond"}

# legend blocks (PDF coords) — swatches there are not map features
LEGENDS = [(60, 425, 205, 640), (675, 415, 835, 700)]

# map frames (inner black rectangles)
LEFT = (58.68, 110.808, 557.784, 744.264)
RIGHT = (671.385, 110.808, 1169.64, 743.411)

# town-label anchors on the right panel (centre of the label text) -> lon/lat
LABELS = {
    "Petaluma": ((716.8, 168.5), (-122.6367, 38.2324)),
    "Napa": ((924.2, 126.5), (-122.2869, 38.2975)),
    "Novato": ((752.9, 251.9), (-122.5697, 38.1074)),
    "San Rafael": ((784.0, 341.3), (-122.5311, 37.9735)),
    "Fairfield": ((1056.4, 155.6), (-122.0400, 38.2494)),
    "Concord": ((1063.3, 340.9), (-122.0311, 37.9780)),
    "Richmond": ((896.0, 363.5), (-122.3477, 37.9358)),
    "Oakland": ((936.7, 449.5), (-122.2711, 37.8044)),
    "Hayward": ((1038.3, 549.6), (-122.0808, 37.6688)),
    "Fremont": ((1091.9, 625.7), (-121.9886, 37.5485)),
    "Redwood City": ((944.8, 680.8), (-122.2364, 37.4852)),
    "San Mateo": ((881.0, 619.0), (-122.3255, 37.5630)),
    "San Jose": ((1108.8, 737.5), (-121.8863, 37.3382)),
}


def color_key(rgb):
    best, bd = None, 1e9
    for k, v in CLASSES.items():
        dd = sum((a - b) ** 2 for a, b in zip(rgb, k))
        if dd < bd:
            best, bd = v, dd
    return best if bd < 0.0004 else None


def bezier(p0, p1, p2, p3, n=6):
    t = np.linspace(0, 1, n)[1:]
    pts = ((1 - t) ** 3)[:, None] * p0 + (3 * (1 - t) ** 2 * t)[:, None] * p1 + (3 * (1 - t) * t ** 2)[:, None] * p2 + (t ** 3)[:, None] * p3
    return [tuple(p) for p in pts]


def drawing_polygon(dr):
    rings, cur = [], []
    last = None
    for it in dr["items"]:
        op = it[0]
        if op == "re":
            r = it[1]
            rings.append([(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)])
            last = None
            continue
        if op == "qu":
            q = it[1]
            rings.append([(q.ul.x, q.ul.y), (q.ur.x, q.ur.y), (q.lr.x, q.lr.y), (q.ll.x, q.ll.y)])
            last = None
            continue
        p0 = (it[1].x, it[1].y)
        if last is None or abs(p0[0] - last[0]) > 1e-3 or abs(p0[1] - last[1]) > 1e-3:
            if len(cur) >= 3:
                rings.append(cur)
            cur = [p0]
        if op == "l":
            p1 = (it[2].x, it[2].y)
            cur.append(p1)
            last = p1
        elif op == "c":
            pts = bezier(*(np.array([q.x, q.y]) for q in it[1:5]))
            cur.extend(pts)
            last = pts[-1]
    if len(cur) >= 3:
        rings.append(cur)
    geom = None
    for ring in rings:
        try:
            pg = shapely.make_valid(Polygon(ring))
        except Exception:
            continue
        if pg.is_empty:
            continue
        geom = pg if geom is None else geom.symmetric_difference(pg)  # even-odd fill
    return geom


def extract():
    doc = fitz.open(PDF)
    page = doc[0]
    out = {"left": defaultdict(list), "right": defaultdict(list)}
    for dr in page.get_drawings():
        f = dr.get("fill")
        if not f:
            continue
        cls = color_key(tuple(round(c, 3) for c in f))
        if cls is None:
            continue
        r = dr["rect"]
        cx = (r.x0 + r.x1) / 2
        cy = (r.y0 + r.y1) / 2
        if LEFT[0] < cx < LEFT[2] and LEFT[1] < cy < LEFT[3]:
            panel = "left"
        elif RIGHT[0] < cx < RIGHT[2] and RIGHT[1] < cy < RIGHT[3]:
            panel = "right"
        else:
            continue
        if r.width < 16 and r.height < 16 and len(dr["items"]) <= 2:
            continue  # legend swatch
        if r.width < 40 and r.height < 40 and any(lx0 < cx < lx1 and ly0 < cy < ly1 for lx0, ly0, lx1, ly1 in LEGENDS):
            continue  # legend block (swatches, scale bar)
        g = drawing_polygon(dr)
        if g is not None and not g.is_empty:
            out[panel][cls].append(g)
    merged = {p: {c: shapely.make_valid(shapely.union_all(gs)) for c, gs in d.items()} for p, d in out.items()}
    for p, d in merged.items():
        log(f"baylands: {p} panel classes: " + ", ".join(f"{c}={len(out[p][c])}" for c in sorted(d)))
    return merged


def left_to_right():
    sx = (RIGHT[2] - RIGHT[0]) / (LEFT[2] - LEFT[0])
    sy = (RIGHT[3] - RIGHT[1]) / (LEFT[3] - LEFT[1])
    return [sx, 0, 0, sy, RIGHT[0] - LEFT[0] * sx, RIGHT[1] - LEFT[1] * sy]


def label_fit():
    src = np.array([v[0] for v in LABELS.values()])
    dst = gpd.GeoSeries(gpd.points_from_xy([v[1][0] for v in LABELS.values()], [v[1][1] for v in LABELS.values()]), crs=4326).to_crs(UTM)
    dst = np.column_stack([dst.x, dst.y])
    A = np.column_stack([src, np.ones(len(src))])
    cx, *_ = np.linalg.lstsq(A, dst[:, 0], rcond=None)
    cy, *_ = np.linalg.lstsq(A, dst[:, 1], rcond=None)
    pred = A @ np.column_stack([cx, cy])
    rms = float(np.sqrt(((pred - dst) ** 2).sum(1).mean()))
    return [cx[0], cx[1], cy[0], cy[1], cx[2], cy[2]], rms  # shapely affine order a,b,d,e,xoff,yoff


def tiger_water(bounds):
    counties = gpd.read_file(f"zip://{RAW / 'tiger' / 'tl_2024_us_county.zip'}")
    counties = counties[(counties.STATEFP + counties.COUNTYFP).isin(BAY_COUNTIES)].to_crs(UTM)
    land = shapely.union_all(counties.geometry.values)
    waters = []
    for fips in BAY_COUNTIES:
        w = gpd.read_file(f"zip://{RAW / 'tiger' / f'tl_2024_{fips}_areawater.zip'}").to_crs(UTM)
        waters.append(w[w.area > 20000].geometry)
    water = shapely.union_all(np.concatenate([w.values for w in waters]))
    land = land.difference(water)
    return box(*bounds).difference(land)


def raster(geom, transform, shape):
    if geom is None or geom.is_empty:
        return np.zeros(shape, bool)
    return features.rasterize([(geom, 1)], out_shape=shape, transform=transform, fill=0).astype(bool)


def local_offsets(params, water_pdf, frame_utm, n=(4, 5), res=100.0):
    """Per-window translation corrections (rubber-sheeting) blended by inverse distance."""
    gw = affine_transform(water_pdf, params)
    truth_all = tiger_water(frame_utm.bounds)
    minx, miny, maxx, maxy = frame_utm.buffer(-3000).bounds
    offs = []
    for i in range(n[0]):
        for j in range(n[1]):
            x0 = minx + (maxx - minx) * i / n[0]
            x1 = minx + (maxx - minx) * (i + 1) / n[0]
            y0 = miny + (maxy - miny) * j / n[1]
            y1 = miny + (maxy - miny) * (j + 1) / n[1]
            win = box(x0, y0, x1, y1)
            tr = from_origin(x0, y1, res, res)
            shp = (int((y1 - y0) / res), int((x1 - x0) / res))
            truth = raster(truth_all.intersection(win), tr, shp)
            frac = truth.mean()
            if not 0.12 < frac < 0.88:
                continue
            sub = gw.intersection(win.buffer(4000))

            def iou(t):
                m = raster(shapely.affinity.translate(sub, t[0], t[1]), tr, shp)
                return (m & truth).sum() / max((m | truth).sum(), 1)

            base = iou((0, 0))
            best = (0.0, 0.0, base)
            for step in (800, 300, 100):
                cx, cy, cb = best
                for dx in (-2, -1, 0, 1, 2):
                    for dy in (-2, -1, 0, 1, 2):
                        v = iou((cx + dx * step, cy + dy * step))
                        if v > cb + 1e-4:
                            best = (cx + dx * step, cy + dy * step, v)
                            cb = v
            if best[2] > base + 0.005 and np.hypot(best[0], best[1]) < 2500:
                offs.append(((x0 + x1) / 2, (y0 + y1) / 2, best[0], best[1], base, best[2]))
    pts = np.array([[o[0], o[1]] for o in offs]) if offs else np.zeros((0, 2))
    vec = np.array([[o[2], o[3]] for o in offs]) if offs else np.zeros((0, 2))

    def warp(coords):
        if not len(pts):
            return coords
        d2 = ((coords[:, None, :] - pts[None, :, :]) ** 2).sum(-1) + 4e6
        w = 1.0 / d2 ** 1.5
        w /= w.sum(1, keepdims=True)
        return coords + w @ vec

    return warp, offs


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    panels = extract()
    l2r = left_to_right()
    params0, rms = label_fit()
    log(f"baylands: label fit RMS {rms:.0f} m")

    right_water = shapely.union_all([g for c, g in panels["right"].items() if c in WATER_MODERN])
    # evaluation window: the poster's bay interior (avoid edges where TIGER counties end)
    frame_utm = affine_transform(box(*RIGHT), params0)
    win = frame_utm.buffer(-3000)
    res = 250.0
    minx, miny, maxx, maxy = win.bounds
    tr = from_origin(minx, maxy, res, res)
    shape = (int((maxy - miny) / res), int((maxx - minx) / res))
    truth = raster(tiger_water(frame_utm.bounds).intersection(win), tr, shape)
    winmask = raster(win, tr, shape)
    simple_water = right_water.simplify(0.15)

    def iou(p):
        m = raster(affine_transform(simple_water, p), tr, shape) & winmask
        inter = (m & truth).sum()
        uni = (m | truth).sum()
        return inter / max(uni, 1)

    # refine as a similarity tweak around the label fit: shift (m), log-scale,
    # rotation (rad), aspect — the poster is an affine of UTM up to small errors
    a, b, d, e, xo, yo = params0
    M0 = np.array([[a, b], [d, e]])
    c0 = np.array([(RIGHT[0] + RIGHT[2]) / 2, (RIGHT[1] + RIGHT[3]) / 2])
    w0 = M0 @ c0 + np.array([xo, yo])

    def compose(x):
        tx, ty, ls, th, asp = x
        S = np.exp(ls) * np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]]) @ np.diag([np.exp(asp), np.exp(-asp)])
        M = S @ M0
        off = w0 + np.array([tx, ty]) - M @ c0
        return [M[0, 0], M[0, 1], M[1, 0], M[1, 1], off[0], off[1]]

    def loss(x):
        return -iou(compose(x))

    log(f"baylands: IoU with label fit {iou(params0):.3f}; refining…")
    best = np.zeros(5)
    for step in (np.array([1500, 1500, 0.02, 0.02, 0.02]), np.array([400, 400, 0.006, 0.006, 0.006])):
        simplex = [best] + [best + np.eye(5)[i] * step[i] for i in range(5)]
        r = minimize(loss, best, method="Nelder-Mead", options={"maxiter": 400, "initial_simplex": simplex, "xatol": 1, "fatol": 1e-4})
        best = r.x
        log(f"baylands:   step -> IoU {-r.fun:.3f} shift=({best[0]:.0f},{best[1]:.0f}) m scale={np.exp(best[2]):.4f} rot={np.degrees(best[3]):.2f}°")
    params = compose(best)
    final_iou = iou(params)
    shift = float(np.hypot(best[0], best[1]))
    log(f"baylands: refined IoU {final_iou:.3f} (moved centre {shift:.0f} m)")

    warp, local = local_offsets(params, simple_water, frame_utm)
    log(f"baylands: local corrections at {len(local)} windows: median |shift| "
        f"{np.median([np.hypot(o[2], o[3]) for o in local]) if local else 0:.0f} m")

    for panel, name in (("left", "baylands_1800"), ("right", "baylands_1998")):
        feats = []
        for cls, g in panels[panel].items():
            if panel == "left":
                g = affine_transform(g, l2r)
            g = affine_transform(g, params)
            g = shapely.transform(g, warp)
            gs = gpd.GeoSeries([g], crs=UTM).to_crs(4326)
            feats.append({"class": cls, "geometry": gs.iloc[0]})
        gdf = gpd.GeoDataFrame(feats, crs=4326)
        out = INTERIM / f"{name}.geojson"
        gdf.to_file(out, driver="GeoJSON")
        log(f"baylands: wrote {out}")
    (REPORTS / "baylands_georef.json").write_text(json.dumps({
        "label_fit_rms_m": rms, "iou_label_fit": iou(params0), "iou_refined": final_iou,
        "affine_right_panel_to_utm10n": params, "left_to_right": l2r,
        "local_offsets_m": [[float(v) for v in o] for o in local]}, indent=2))


if __name__ == "__main__":
    main()
