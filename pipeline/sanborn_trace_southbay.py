"""Trace demolished buildings of downtown San José (and later Santa Clara / Palo Alto) from Library of Congress Sanborn maps.

Area (data/manual/sanborn/README_san_jose.md):
  san_jose_downtown   the 1915 "congested district" (Julian St -> Balbach St, Guadalupe River -> 5th St) and its edges:
                      Park Center Plaza / Almaden Blvd, the civic-auditorium / convention-centre blocks, the Market St /
                      First St commercial core, St James Park, the SR 87 (Guadalupe) and I-280 corridors.

This is an extension of pipeline/sanborn_trace_waterfront.py (SF) and reuses its georeferencing (similarity fits per
sheet or per block, SIFT registration of the 1950 plates onto the 1915 plates), colour segmentation and output schema.
What is new is the control geometry: San Francisco's control came from DataSF street centrelines; here it comes from
  * Overture transportation segments (all classes, cached as data/raw/overture/2026-10-21.0/roads_southbay_core.parquet)
    for street crossings and street lines (straight-line fits, extended across vanished blocks), and
  * Santa Clara County parcel polygons (data/raw/region_years/santa_clara_county) for property lines: a Sanborn sheet
    draws the block outline (property line), so a block corner is the crossing of the two property lines fitted to the
    parcel block next to the street crossing (`pc` control entries).
modern_overlap is measured against today's Overture footprints (data/raw/overture/2026-10-21.0/region5_building.parquet).

Inputs (committed, hand-measured):  data/manual/sanborn/control/san_jose/<key>.json (control / registration),
                                    attributes.json (storeys / use / names read off the sheets), areas.json
Downloads (cached, gitignored):     data/raw/sanborn_loc/san_jose/ (LOC item JSON, IIIF images)
Intermediates:                      data/interim/sanborn_southbay/
Outputs:                            data/manual/sanborn/san_jose_downtown_<year>.geojson, _coverage.geojson,
                                    san_jose_downtown_<year>_tracks.geojson

Usage:  python pipeline/sanborn_trace_southbay.py all                 # fetch + georef + extract + assemble
        python pipeline/sanborn_trace_southbay.py georef 004_0084     # one stage, some sheets
        python pipeline/sanborn_trace_southbay.py register 008_0084 004_0084
        python pipeline/sanborn_trace_southbay.py fetch 004_0084      # download (25 %)
        python pipeline/sanborn_trace_southbay.py grid 004_0084 [x0 y0 x1 y1]   # scratch overview with a pixel grid
Keys are <LOC item suffix>_<sheet>, e.g. 004_0084 = sanborn00817_004 (1915 vol. 1) sheet 84.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import sanborn_trace_waterfront as W  # noqa: E402

RAW = ROOT / "data/raw/sanborn_loc/san_jose"
INTERIM = ROOT / "data/interim/sanborn_southbay"
CONTROL = ROOT / "data/manual/sanborn/control/san_jose"
OUT = ROOT / "data/manual/sanborn"
SCRATCH = Path(os.environ.get("SANBORN_SCRATCH", str(INTERIM / "scratch")))
W.RAW, W.INTERIM, W.CONTROL = RAW, INTERIM, CONTROL  # the waterfront stages read / write through these globals
FT = W.FT
CITY = "00817"  # LOC Sanborn id of San José

VOLUMES = {  # LOC item suffix (sanborn00817_<sfx>) -> (map year, label)
    "001": (1884, "1884"),
    "002": (1891, "1891 Vol. 1"), "003": (1891, "1891 Vol. 2"),
    "004": (1915, "1915 Vol. 1"), "005": (1915, "1915 Vol. 2"),
    "008": (1950, "1915-Jan 1950 Vol. 1 (corrected to 1950)"), "007": (1950, "1915-Jan 1950 Vol. 2 (corrected to 1950)"),
}
EDITION_1950 = ("006", "007", "008", "009")
W.EDITION_1950 = EDITION_1950  # the waterfront colour rules for corrected (1950) plates
AREAS: dict[tuple[str, int], list[str]] = {}
ROADS = ROOT / "data/raw/overture/2026-10-21.0/roads_southbay_core.parquet"
PARCELS = ROOT / "data/raw/region_years/santa_clara_county/santa_clara_county.parquet"
BUILDINGS = ROOT / "data/raw/overture/2026-10-21.0/region5_building.parquet"
BBOX = (-121.925, 37.300, -121.850, 37.370)  # downtown San José (+ margin)


def log(*a):
    print("sanborn_southbay:", *a, flush=True)


def load_areas():
    p = CONTROL / "areas.json"
    if p.exists():
        for k, v in json.load(open(p)).items():
            a, y = k.rsplit("_", 1)
            AREAS[(a, int(y))] = v
    return AREAS


# ----------------------------------------------------------------------------------------------- LOC index / images
def index():
    """{vol: [{id, info, w, h}]} for the San José volumes, cached in data/raw/sanborn_loc/san_jose/index.json."""
    p = RAW / "index.json"
    idx = json.load(open(p)) if p.exists() else {}
    changed = False
    for vol in VOLUMES:
        if vol in idx:
            continue
        f = RAW / f"item_{vol}.json"
        for k in range(5):
            try:
                W.curl(f"https://www.loc.gov/item/sanborn{CITY}_{vol}/?fo=json", f, 20000)
                d = json.load(open(f))
                break
            except Exception as e:  # truncated transfers happen: retry
                log("index", vol, "retry", e)
                f.unlink(missing_ok=True)
                time.sleep(5 + 5 * k)
        else:
            log("index", vol, "FAILED")
            continue
        ids = []
        for fl in d["resources"][0]["files"]:
            jp = [x for x in fl if x.get("mimetype") == "image/jp2"]
            if jp:
                ids.append({"id": jp[0]["url"].rsplit("/", 1)[1][:-4], "info": jp[0]["info"], "w": jp[0]["width"], "h": jp[0]["height"]})
        idx[vol] = ids
        changed = True
        time.sleep(2)
    if changed:
        json.dump(idx, open(p, "w"))
    W._index = idx
    return idx


def image(key, pct=25):
    index()
    p = RAW / f"{key[:8]}_{pct}.jpg"
    if p.exists():
        return p
    out = W.image(key, pct)
    time.sleep(1.0)  # be polite to tile.loc.gov
    return out


def overlay(key, out=None, scale=0.5):
    """scratch check: traced footprints (outline colour by class) and block zones drawn on the sheet."""
    from PIL import ImageDraw
    G = json.load(open(INTERIM / f"{key}.M.json"))
    im = Image.open(G["img"]).convert("RGB")
    d = ImageDraw.Draw(im)
    col = {"frame": (255, 120, 0), "brick": (200, 0, 0), "stone": (0, 0, 255), "fireproof": (120, 60, 0), "iron": (90, 90, 90), "wharf": (0, 150, 0)}
    rows = json.load(open(INTERIM / f"{key}.json"))
    if (INTERIM / f"{key}.manual.json").exists():
        rows += json.load(open(INTERIM / f"{key}.manual.json"))
    for r in rows:
        d.line([tuple(q) for q in r["px_ring"]] + [tuple(r["px_ring"][0])], fill=col.get(r["cls"], (0, 200, 0)), width=3)
    for b in G.get("blocks", []):
        x0, y0, x1, y1 = b["rect_px"]
        d.rectangle([x0, y0, x1, y1], outline=(0, 170, 0), width=2)
    if scale != 1:
        im = im.resize((int(im.size[0] * scale), int(im.size[1] * scale)), Image.LANCZOS)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    out = out or SCRATCH / f"{key}_overlay.jpg"
    im.save(out, quality=85)
    return out


def grid(key, box=None, step=100, scale=1.0, out=None):
    """scratch overview of a sheet with a labelled pixel grid (for reading control pixels by eye)."""
    from PIL import ImageDraw
    im = Image.open(image(key)).convert("RGB")
    x0, y0, x1, y1 = box or (0, 0, im.size[0], im.size[1])
    im = im.crop((x0, y0, x1, y1))
    d = ImageDraw.Draw(im)
    for x in range((x0 // step + 1) * step, x1, step):
        d.line([(x - x0, 0), (x - x0, y1 - y0)], fill=(0, 160, 0) if x % 500 else (220, 0, 0), width=1)
        d.text((x - x0 + 2, 2), str(x), fill=(0, 0, 200))
    for y in range((y0 // step + 1) * step, y1, step):
        d.line([(0, y - y0), (x1 - x0, y - y0)], fill=(0, 160, 0) if y % 500 else (220, 0, 0), width=1)
        d.text((2, y - y0 + 2), str(y), fill=(0, 0, 200))
    if scale != 1.0:
        im = im.resize((int(im.size[0] * scale), int(im.size[1] * scale)), Image.LANCZOS)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    out = out or SCRATCH / f"{key}_grid_{x0}_{y0}.jpg"
    im.save(out, quality=88)
    return out


# ----------------------------------------------------------------------------------------------- street geometry
_roads = None
_blocks = None
_to_utm = None


def to_utm():
    global _to_utm
    if _to_utm is None:
        from pyproj import Transformer
        _to_utm = Transformer.from_crs(4326, 32610, always_xy=True)
    return _to_utm


DIRS = ("north ", "south ", "east ", "west ")


def norm_name(n):
    """'North 1st Street' -> '1st street', 'West San Carlos Street' -> 'san carlos street' (directional prefix dropped)."""
    n = (n if isinstance(n, str) else "").strip().lower()
    for d in DIRS:
        if n.startswith(d):
            n = n[len(d):]
    return n.replace("saint ", "st ").replace("  ", " ")


def roads():
    """Overture road segments (all classes) around downtown San José, in EPSG:32610, with a normalised name."""
    global _roads
    if _roads is None:
        import geopandas as gpd
        import pandas as pd
        df = pd.read_parquet(ROADS)
        g = gpd.GeoDataFrame(df, geometry=gpd.GeoSeries.from_wkb(df.geometry), crs=4326)
        g = g[g.geometry.geom_type.isin(["LineString", "MultiLineString"])].copy()
        g["key"] = g["name"].map(norm_name)
        _roads = g.to_crs(32610)
    return _roads


def street_rows(name):
    """segments of a street: `name` matched after normalisation ('1st street' matches North and South 1st Street);
    'Almaden Avenue' and 'Almaden Boulevard' stay different streets."""
    r = roads()
    k = norm_name(name)
    rows = r[r.key == k]
    if rows.empty:
        rows = r[r.key.str.startswith(k + " ")] if " " not in k else rows
    if rows.empty:
        raise KeyError(f"unknown street {name!r}")
    return rows


def xing(a, b, near=None):
    """crossing of two named streets (EPSG:32610); `near` (UTM) picks among several crossings; divided roads give a
    cluster of crossings, averaged."""
    import shapely
    from shapely.ops import nearest_points
    ga = shapely.union_all(street_rows(a).geometry.values)
    gb = shapely.union_all(street_rows(b).geometry.values)
    I = ga.intersection(gb)
    pts = [np.array(p.coords[0]) for p in getattr(I, "geoms", [I]) if not p.is_empty and p.geom_type == "Point"]
    if pts:
        pts = np.array(pts)
        ref = np.asarray(near, float) if near is not None else pts[0]
        d = np.hypot(*(pts - ref).T)
        c = pts[d <= d.min() + 35]
        return c.mean(axis=0), "node" if len(c) == 1 else f"node x{len(c)}"
    pa, pb = nearest_points(ga, gb)
    if near is not None:  # the streets cross more than once or not at all: closest approach near the hint
        from shapely.geometry import Point
        nb = Point(*near).buffer(150)
        ga2, gb2 = ga.intersection(nb), gb.intersection(nb)
        if not ga2.is_empty and not gb2.is_empty:
            pa, pb = nearest_points(ga2, gb2)
    mid = np.array([(pa.x + pb.x) / 2, (pa.y + pb.y) / 2])
    try:  # a street that stops short of the other (paseo, closed street): extend both as straight lines
        L1, L2 = street_line(a, mid, 90), street_line(b, mid, 90)
        if abs(L1[1] @ L2[1]) < 0.9:
            return line_x(L1, L2), f"lines extended (gap {pa.distance(pb):.0f}m)"
    except ValueError:
        pass
    return mid, f"closest-approach {pa.distance(pb):.0f}m"


def near_xy(near):
    if len(near) == 2 and all(isinstance(v, (int, float)) for v in near):
        return np.array(near, float)
    return xing(*near)[0]


def street_line(name, near, R=350, cnn=None):
    """least-squares straight line (point, unit dir) through the Overture centreline of `name` within R m of `near`."""
    pts = []
    near = np.asarray(near, float)
    for geom in street_rows(name).geometry:
        for gg in ([geom] if geom.geom_type == "LineString" else list(geom.geoms)):
            c = np.asarray(gg.coords)[:, :2]
            for a, b in zip(c[:-1], c[1:]):
                for t in np.linspace(0, 1, max(2, int(np.hypot(*(b - a)) / 5))):
                    p = a + t * (b - a)
                    if np.hypot(*(p - near)) < R:
                        pts.append(p)
    pts = np.asarray(pts)
    if len(pts) < 2:
        raise ValueError(f"no centreline of {name} within {R} m")
    m = pts.mean(axis=0)
    return m, np.linalg.svd(pts - m)[2][0]


def parcel_blocks():
    """blocks = connected unions of today's parcels (EPSG:32610), for property lines."""
    global _blocks
    if _blocks is None:
        import geopandas as gpd
        import pandas as pd
        import shapely
        from shapely.strtree import STRtree
        cache = INTERIM / "parcel_blocks.parquet"
        if cache.exists():
            b = gpd.read_parquet(cache)
        else:
            df = pd.read_parquet(PARCELS)
            g = gpd.GeoDataFrame(df, geometry=gpd.GeoSeries.from_wkb(df.geometry), crs=4326)
            g = g.cx[BBOX[0]:BBOX[2], BBOX[1]:BBOX[3]].to_crs(32610)
            u = shapely.union_all([x.buffer(0.4, join_style=2) for x in g.geometry.values]).buffer(-0.4, join_style=2)
            b = gpd.GeoDataFrame(geometry=[p for p in getattr(u, "geoms", [u]) if p.area > 50], crs=32610)
            INTERIM.mkdir(parents=True, exist_ok=True)
            b.to_parquet(cache)
        _blocks = (list(b.geometry.values), STRtree(list(b.geometry.values)))
    return _blocks


def property_corner(a, b, q, near=None, reach=(18, 75), R=150, wa=None, wb=None):
    """block corner (property-line crossing) in quadrant q (NE/NW/SE/SW: N = along the more north-south street of the
    two, E = along the more east-west one) of the a x b street crossing, from today's parcel block in that quadrant:
    along each street the property line is the street's direction at the median normal offset of the block boundary
    points facing that street (18-75 m from the crossing, so a rounded or cut-off corner does not count), and the two
    property lines are intersected. Returns (point, label, [offset from the NS centreline, from the EW centreline])."""
    from shapely.geometry import Point
    X = xing(a, b, near)[0]
    ds = []
    for n in (a, b):
        d = street_line(n, X, R)[1]
        ds.append(d)
    k = int(np.argmax([abs(d[1]) / (abs(d[0]) + 1e-9) for d in ds]))  # the more north-south one
    widths = [wa, wb] if k == 0 else [wb, wa]  # ft, per (NS street, EW street): centreline + half width instead of parcels
    eN, eE = ds[k], ds[1 - k]
    eN = eN if eN[1] > 0 else -eN
    eE = eE if eE[0] > 0 else -eE
    sN = 1 if "N" in q else -1
    sE = 1 if "E" in q else -1
    probe = X + sN * 30 * eN + sE * 30 * eE
    geoms, tree = parcel_blocks()
    cand = [geoms[i] for i in tree.query(Point(*probe).buffer(25))]
    blk = min(cand, key=lambda g: g.distance(Point(*probe))) if cand else None
    if (blk is None or blk.distance(Point(*probe)) > 15) and not (wa and wb):
        raise ValueError(f"no parcel block in quadrant {q} of {a} x {b}")
    if wa and wb:
        blk = Point(*probe).buffer(1)
    ring = np.asarray(blk.exterior.coords)[:, :2]
    pts = []
    for p0, p1 in zip(ring[:-1], ring[1:]):
        n = max(2, int(np.hypot(*(p1 - p0)) / 0.5))
        pts += [p0 + t * (p1 - p0) for t in np.linspace(0, 1, n, endpoint=False)]
    rel = np.array(pts) - X
    nN = np.array([eN[1], -eN[0]]); nN = nN if nN @ eE > 0 else -nN  # normal of the NS street, toward +E
    nE = np.array([-eE[1], eE[0]]); nE = nE if nE @ eN > 0 else -nE  # normal of the EW street, toward +N
    offs = []
    for (e_al, n_ac, s_al, s_ac), w in zip(((eN, nN, sN, sE), (eE, nE, sE, sN)), widths):
        if w:  # street whose today's property line is not the old one: centreline + half the mapped width
            offs.append(w * FT / 2)
            continue
        al, ac = rel @ e_al * s_al, rel @ n_ac * s_ac
        sel = (al > reach[0]) & (al < reach[1]) & (ac > 0)
        if sel.sum() < 5:
            raise ValueError(f"property line not found at {a} x {b} {q}")
        acs = ac[sel]
        offs.append(float(np.median(acs[acs <= acs.min() + 2.0])))
    p = X + np.linalg.solve(np.array([nN, nE]), np.array([sE * offs[0], sN * offs[1]]))
    return p, f"property corner {q} of {a} x {b}", offs


# ----------------------------------------------------------------------------------------------- control entries
_world_of = W.world_of


def line_of(street, near, R=300):
    p = xing(street, near)[0] if isinstance(near, str) else np.asarray(near, float)
    p0, d = street_line(street, p, R)
    if d[0] < -1e-9 or (abs(d[0]) <= 1e-9 and d[1] < 0):
        d = -d
    return p0, d


def line_x(L1, L2):
    A = np.array([L1[1], -L2[1]]).T
    t = np.linalg.solve(A, L2[0] - L1[0])
    return L1[0] + t[0] * L1[1]


def world_of(c):
    """control entry -> UTM point. Adds to the waterfront tool's entries:
    pc:  [street a, street b], q = quadrant: block corner on today's parcel (property) lines (`property_corner`);
         optional `near` [x, y] UTM hint where two streets cross twice.
    bcx: block corner where today's streets no longer meet: both centrelines fitted as straight lines near the given
         points, intersected, and offset by half of each street's width (ft) toward the block (sa / sb as in the
         industrial tool).
    xl:  crossing of two straight centreline fits (centre of the corridor)."""
    if "pc" in c:
        p, lab, offs = property_corner(c["pc"][0], c["pc"][1], c["q"], c.get("near"), tuple(c.get("reach", (18, 75))), c.get("R", 150),
                                       c.get("wa"), c.get("wb"))
        if c.get("wa") or c.get("wb"):
            lab += " (" + ", ".join(f"{n} centreline + {w} ft / 2" for n, w in zip(c["pc"], (c.get("wa"), c.get("wb"))) if w) + ")"
        return p, c.get("label", lab)
    if "bcx" in c:
        a, na, b, nb = c["bcx"]
        L1, L2 = line_of(a, na, c.get("R", 300)), line_of(b, nb, c.get("R", 300))
        X = line_x(L1, L2)
        return (X + c["sa"] * (c["wb"] * FT / 2) * L1[1] + c["sb"] * (c["wa"] * FT / 2) * L2[1],
                c.get("label", f"corner of {a} x {b} (centrelines extended)"))
    if "xl" in c:
        a, na, b, nb = c["xl"]
        return line_x(line_of(a, na, c.get("R", 300)), line_of(b, nb, c.get("R", 300))), c.get("label", f"{a} x {b} (centrelines extended)")
    if "a" in c:
        p, how = xing(c["a"], c["b"], c.get("near"))
        return p, f"{c['a']} x {c['b']} [{how}]"
    return _world_of(c)


W.world_of = world_of
W.xing = lambda a, b: xing(a, b)
W.street_line = street_line


_measured = W.measured


def measured(c, masks):
    """pixel of a control entry: stored if `norefine`; block corners (`pc`, `bcx`) snap to the nearest block lines."""
    if c.get("norefine") or masks is None:
        return c["x"], c["y"]
    if "pc" in c or "bcx" in c:
        return W.refine_corner(masks, c["x"], c["y"], win=c.get("win", 14), span=c.get("span", 70))
    return _measured(c, masks)


W.measured = measured


def freeze(key):
    """write the refined pixel positions of a georeferenced sheet back into its control file (norefine), so reruns
    reproduce the fit exactly."""
    f = CONTROL / f"{key}.json"
    cfg = json.load(open(f))
    G = json.load(open(INTERIM / f"{key}.M.json"))
    pts = {}
    for b in G.get("blocks", []):
        for q in b["points"]:
            pts.setdefault(b["name"], []).append(q["px"])
    n = 0
    for b in cfg.get("blocks", []):
        for c, px in zip(b["corners"], pts.get(b["name"], [])):
            if not c.get("norefine"):
                c["x0"], c["y0"] = c["x"], c["y"]
                c["x"], c["y"], c["norefine"] = round(px[0], 1), round(px[1], 1), 1
                n += 1
    sheet_pts = [q for q in G["points"] if q["label"] != "on street line"][:len(cfg.get("points", []))]
    for c, q in zip(cfg.get("points", []), sheet_pts):
        if not c.get("norefine"):
            c["x0"], c["y0"] = c["x"], c["y"]
            c["x"], c["y"], c["norefine"] = round(q["px"][0], 1), round(q["px"][1], 1), 1
            n += 1
    json.dump(cfg, open(f, "w"), indent=1)
    log(key, "froze", n, "control pixels")


def compact(key, spec):
    """control file from a compact spec: {"blocks": {name: [[x, y, street a, street b, q], ...]}, "points": [...],
    plus any other keys (zones_only, scale_prior, valid_px, confidence_cap, residential)}. A corner given as
    [x, y, a, b, q] is a property corner (`pc`); [x, y, {"bcx": ...}] passes the dict through."""
    def entry(c):
        if isinstance(c[2], dict):
            return dict(c[2], x=float(c[0]), y=float(c[1]))
        e = {"pc": [c[2], c[3]], "q": c[4], "x": float(c[0]), "y": float(c[1])}
        if len(c) > 5:
            e.update(c[5])
        return e
    cfg = {k: v for k, v in spec.items() if k not in ("blocks", "points")}
    if "blocks" in spec:
        cfg["blocks"] = [{"name": n, "corners": [entry(c) for c in cs]} for n, cs in spec["blocks"].items()]
    if "points" in spec:
        cfg["points"] = [entry(c) for c in spec["points"]]
    cfg.setdefault("pct", 25)
    CONTROL.mkdir(parents=True, exist_ok=True)
    json.dump(cfg, open(CONTROL / f"{key}.json", "w"), indent=1)
    return cfg


# ----------------------------------------------------------------------------------------------- footprints
def extract(key):
    """colour-segment the building fills (yellow frame, pink brick, blue stone / concrete, ochre fire-proof, grey iron)
    as in the waterfront tool, with two changes for the San José plates: (1) the pink brick wash is darker here
    (grey level ~105-115) than on the SF plates, so drawn lines are found relative to their surroundings (darker than
    the 7-px local median by 28+ and below grey 100), not by an absolute grey level; (2) every class is split along the
    drawn partition walls (long straight lines, 14 px = 2.8 m or more, axis-aligned on these sheets), so a row of
    brick stores becomes one feature per building, as drawn."""
    import cv2
    from shapely.geometry import Polygon
    G = json.load(open(INTERIM / f"{key}.M.json"))
    ed = key.split("_")[0]
    rgb = np.asarray(Image.open(G["img"]).convert("RGB"))
    hsv = cv2.cvtColor(cv2.medianBlur(rgb, 3), cv2.COLOR_RGB2HSV).astype(int)
    Hh, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    small = cv2.resize(hsv.astype(np.uint8), None, fx=1 / 8, fy=1 / 8, interpolation=cv2.INTER_AREA)
    bgV = cv2.resize(cv2.medianBlur(np.ascontiguousarray(small[..., 2]), 31), (S.shape[1], S.shape[0])).astype(int)
    dV = V - bgV
    pm = (V > np.percentile(V, 30)) & (S < np.percentile(S, 70))
    pH, pS, pV = int(np.median(Hh[pm])), int(np.median(S[pm])), int(np.median(V[pm]))
    cfg = json.load(open(CONTROL / f"{key}.json"))
    if ed in EDITION_1950:  # yellowed paper and paste-over slips: hue + saturation relative to the paper
        fr = ((Hh >= max(pH, 22)) & (Hh <= 36) & (S >= pS + 40) & (V >= 70)) | ((Hh >= 19) & (Hh <= 36) & (S >= 125) & (V >= 70))
    else:
        fr = (Hh >= 19) & (Hh <= 38) & (S >= max(80, pS + 40)) & (V >= 80)
    classes = {
        "frame": fr,
        "brick": ((Hh >= 155) | (Hh <= 7)) & (S >= 40) & (V >= 55),
        "stone": (Hh >= 80) & (Hh <= 130) & (S >= 30) & (V >= 55),
        "fireproof": (Hh >= 8) & (Hh <= 18) & (S >= 100) & (V >= 50),
        "iron": ((Hh >= 17) & (Hh <= 30) & (S <= pS + 4) & (V >= 80) & (V <= pV - 22) & (dV <= -10)),
    }
    if cfg.get("stone_low_sat"):
        classes["stone"] = classes["stone"] | ((Hh >= 85) & (Hh <= 125) & (S >= 20) & (V >= 60) & (V <= pV - 15))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.int16)
    med = cv2.medianBlur(gray.astype(np.uint8), 7).astype(np.int16)
    line = ((gray < med - 28) & (gray < 100)) | (gray < 60)
    L = int(cfg.get("wall_len", 14))
    part = ndi.binary_opening(line, structure=np.ones((L, 1))) | ndi.binary_opening(line, structure=np.ones((1, L)))
    part = ndi.binary_dilation(part, structure=np.ones((2, 2)))
    darkd = ndi.binary_dilation(line | (gray < 95), iterations=3)
    M = np.array(G["M"]); blocks = G.get("blocks", []); zones_only = G.get("zones_only", False)

    def transform_for(cx, cy):
        best, bd = None, 1e9
        for b in blocks:
            x0, y0, x1, y1 = b["rect_px"]
            d = max(x0 - cx, 0, cx - x1) + max(y0 - cy, 0, cy - y1)
            if d < bd:
                best, bd = b, d
        if best is not None and bd <= 40:
            return np.array(best["M"]), best["name"]
        return (None, None) if zones_only else (M, "sheet")
    feats = []
    for cls, m in classes.items():
        m = ndi.binary_opening(m, structure=np.ones((2, 2)))
        m = (ndi.binary_closing(m, structure=np.ones((3, 3))) | m) & ~part
        holes = ndi.binary_fill_holes(m) & ~m
        hl, hn = ndi.label(holes)
        if hn:
            hs = ndi.sum(holes, hl, range(1, hn + 1))
            m = m | np.isin(hl, np.nonzero(hs < 2500)[0] + 1)
        m = m & ~part
        lab, n = ndi.label(m)
        if not n:
            continue
        sizes = ndi.sum(m, lab, range(1, n + 1)); objs = ndi.find_objects(lab)
        for i in range(n):
            sl = objs[i]
            if sizes[i] < 90 or sl[0].start < 12 or sl[1].start < 12 or sl[0].stop > m.shape[0] - 12 or sl[1].stop > m.shape[1] - 12:
                continue
            if min(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) < 6:
                continue
            sub = lab[sl] == i + 1
            dist = ndi.distance_transform_edt(np.pad(sub, 1))
            if dist.max() < 3.5:
                continue
            hullA = cv2.contourArea(cv2.convexHull(np.argwhere(sub)[:, ::-1].astype(np.int32)))
            solid = sizes[i] / hullA if hullA > 0 else 0
            if cls == "iron" and (sizes[i] < 400 or dist.max() < 6 or solid < 0.75):
                continue
            ring_out = ndi.binary_dilation(np.pad(sub, 4), iterations=1) & ~np.pad(sub, 4)
            y0_, x0_ = max(0, sl[0].start - 4), max(0, sl[1].start - 4)
            dd = darkd[y0_:sl[0].stop + 4, x0_:sl[1].stop + 4]
            oy, ox = 4 - (sl[0].start - y0_), 4 - (sl[1].start - x0_)
            dd = np.pad(dd, ((oy, max(0, ring_out.shape[0] - dd.shape[0] - oy)), (ox, max(0, ring_out.shape[1] - dd.shape[1] - ox))))
            dd = dd[:ring_out.shape[0], :ring_out.shape[1]]
            edge_dark = float(dd[ring_out].mean()) if ring_out.any() else 0
            if edge_dark < (0.6 if cls == "iron" else 0.7) or (solid < 0.5 and edge_dark < 0.85):
                continue
            cs, _ = cv2.findContours(np.pad(sub, 2).astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
            rings = []
            for c in cs:
                c = c[:, 0, :].astype(float)
                if len(c) >= 4:
                    c[:, 0] += sl[1].start - 2; c[:, 1] += sl[0].start - 2
                    rings.append(c)
            if not rings:
                continue
            rings.sort(key=lambda c: -Polygon(c).area)
            outer = Polygon(rings[0]).buffer(1.2, join_style=2).simplify(1.0)  # half the partition wall back
            if outer.geom_type != "Polygon":
                outer = max(outer.geoms, key=lambda p: p.area)
            hol = [Polygon(r).buffer(-0.8, join_style=2).simplify(1.0) for r in rings[1:] if Polygon(r).area > 400]
            hol = [h for h in hol if h.geom_type == "Polygon" and outer.contains(h)]
            poly = Polygon(outer.exterior.coords, [h.exterior.coords for h in hol])
            cx, cy = poly.centroid.x, poly.centroid.y
            vp = G.get("valid_px")
            if vp and not (vp[0] <= cx <= vp[2] and vp[1] <= cy <= vp[3]):
                continue
            if G.get("valid_poly_px") and not Polygon(G["valid_poly_px"]).contains(poly.centroid):
                continue
            T, zone = transform_for(cx, cy)
            if T is None:
                continue
            ext = W.apply(T, np.asarray(poly.exterior.coords))
            hw = [W.apply(T, np.asarray(h.coords)) for h in poly.interiors]
            feats.append({"id": f"{key}_{cls[0]}{i + 1}", "cls": cls, "zone": zone, "px_centroid": [round(cx, 1), round(cy, 1)],
                          "px_ring": np.round(np.asarray(poly.exterior.coords), 1).tolist(), "area_m2": round(float(Polygon(ext, hw).area), 1),
                          "ring_utm": np.round(ext, 2).tolist(), "holes_utm": [np.round(h, 2).tolist() for h in hw]})
    json.dump(feats, open(INTERIM / f"{key}.json", "w"))
    log(key, len(feats), "footprints")


if __name__ == "__main__":
    load_areas()
    index()
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage == "grid":
        k = sys.argv[2]
        box = tuple(int(v) for v in sys.argv[3:7]) if len(sys.argv) >= 7 else None
        print(grid(k, box, step=int(os.environ.get("STEP", 100)), scale=float(os.environ.get("SCALE", 1.0))))
        sys.exit()
    keys = sys.argv[2:]
    if stage == "fetch":
        for k in keys:
            print(image(k, int(os.environ.get("PCT", 25))))
