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


def property_corner(a, b, q, near=None, reach=(18, 75), R=150, wa=None, wb=None, ma=None, mb=None):
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
    mirrors = [ma, mb] if k == 0 else [mb, ma]  # ft: the property line across the street (opposite block) + this width
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
    def ring_rel(bk):
        ring = np.asarray(bk.exterior.coords)[:, :2]
        pp = []
        for p0, p1 in zip(ring[:-1], ring[1:]):
            n = max(2, int(np.hypot(*(p1 - p0)) / 0.5))
            pp += [p0 + t * (p1 - p0) for t in np.linspace(0, 1, n, endpoint=False)]
        return np.array(pp) - X

    def frontage(rr, e_al, n_ac, s_al, s_ac):
        al, ac = rr @ e_al * s_al, rr @ n_ac * s_ac
        sel = (al > reach[0]) & (al < reach[1]) & (ac > 0)
        if sel.sum() < 5:
            raise ValueError(f"property line not found at {a} x {b} {q}")
        acs = ac[sel]
        return float(np.median(acs[acs <= acs.min() + 2.0]))
    offs = []
    for i, ((e_al, n_ac, s_al, s_ac), w, mw) in enumerate(zip(((eN, nN, sN, sE), (eE, nE, sE, sN)), widths, mirrors)):
        if w:  # street whose today's property line is not the old one: centreline + half the mapped width
            offs.append(w * FT / 2)
            continue
        if mw:  # today's block on this side changed: the opposite block's frontage + the mapped street width
            pr = X + (-sE * 30 * eE + sN * 30 * eN if i == 0 else sE * 30 * eE - sN * 30 * eN)
            cand2 = [geoms[j] for j in tree.query(Point(*pr).buffer(25))]
            if not cand2:
                raise ValueError(f"no opposite block at {a} x {b} {q}")
            ob = min(cand2, key=lambda g: g.distance(Point(*pr)))
            offs.append(mw * FT - frontage(ring_rel(ob), e_al, n_ac, s_al, -s_ac))
            continue
        offs.append(frontage(rel, e_al, n_ac, s_al, s_ac))
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
    if "shift" in c:  # a corner across a street from a known one: moved along a street's direction by ft
        ft, street, sgn = c["shift"]
        p, lab = world_of({k: v for k, v in c.items() if k != "shift"})
        d = street_line(street, p, c.get("shift_R", 450))[1]
        d = d if d[1] > 0 else -d
        return p + sgn * ft * FT * d, f"{lab}, shifted {ft} ft along {street}"
    if "pc" in c:
        p, lab, offs = property_corner(c["pc"][0], c["pc"][1], c["q"], c.get("near"), tuple(c.get("reach", (18, 75))), c.get("R", 150),
                                       c.get("wa"), c.get("wb"), c.get("ma"), c.get("mb"))
        if c.get("wa") or c.get("wb"):
            lab += " (" + ", ".join(f"{n} centreline + {w} ft / 2" for n, w in zip(c["pc"], (c.get("wa"), c.get("wb"))) if w) + ")"
        if c.get("ma") or c.get("mb"):
            lab += " (" + ", ".join(f"{n}: opposite property line + {w} ft" for n, w in zip(c["pc"], (c.get("ma"), c.get("mb"))) if w) + ")"
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
    dropped = []

    def ok(e):  # control whose world position cannot be computed (street gone, no parcel block) is listed, not used
        try:
            world_of(e)
            return True
        except Exception as ex:
            dropped.append(dict(e, reason=str(ex)))
            return False
    if "blocks" in spec:
        cfg["blocks"] = [{"name": n, "corners": [e for e in (entry(c) for c in (cs["corners"] if isinstance(cs, dict) else cs)) if ok(e)],
                          **({"zone_px": cs["zone_px"]} if isinstance(cs, dict) and "zone_px" in cs else {})}
                         for n, cs in spec["blocks"].items()]
    if "points" in spec:
        cfg["points"] = [e for e in (entry(c) for c in spec["points"]) if ok(e)]
    if dropped:
        cfg["unresolved"] = dropped
        log(key, len(dropped), "control entries without a world position:", "; ".join(d["reason"] for d in dropped))
    cfg.setdefault("pct", 25)
    CONTROL.mkdir(parents=True, exist_ok=True)
    json.dump(cfg, open(CONTROL / f"{key}.json", "w"), indent=1)
    return cfg


def fit(px, w, lines=(), prior=None):
    """the waterfront tool's similarity fit (points, point-on-line constraints, scale prior) plus an optional rotation
    prior: prior = [scale, sigma_scale] or [scale, sigma_scale, rotation_deg, sigma_deg]. The 1915 San José plates are
    drawn with the street grid axis-aligned and scanned at one resolution, so well-controlled blocks share a scale of
    ~0.2015 m/px and a rotation of ~-58.7 deg; sheets whose control is clustered or weak use both priors."""
    from scipy.optimize import least_squares
    px, w = np.asarray(px, float).reshape(-1, 2), np.asarray(w, float).reshape(-1, 2)

    def resid(v):
        M = W.M_of(v)
        r = list((W.apply(M, px) - w).ravel()) if len(px) else []
        r += [float(n @ (W.apply(M, [q])[0] - p0)) for q, p0, n in lines]
        if prior:
            r.append((v[0] - prior[0]) / prior[1])
            if len(prior) >= 4:
                d = (math.degrees(v[1]) - prior[2] + 180) % 360 - 180
                r.append(d / prior[3])
        return r
    s0 = prior[0] if prior else 0.2
    c0 = w.mean(axis=0) if len(w) else lines[0][1]
    pc = px.mean(axis=0) if len(px) else np.mean([q for q, _, _ in lines], axis=0)
    best = None
    for th in np.radians(np.arange(-180, 180, 15)):
        t = c0 - W.apply(W.M_of([s0, th, 0, 0]), [pc])[0]
        sol = least_squares(resid, [s0, th, t[0], t[1]])
        if best is None or sol.cost < best.cost:
            best = sol
    M = W.M_of(best.x)
    res = [float(np.hypot(*(W.apply(M, [p])[0] - q))) for p, q in zip(px, w)]
    res += [abs(float(n @ (W.apply(M, [q])[0] - p0))) for q, p0, n in lines]
    return M, np.array(res)


W.fit = fit


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
    if cfg.get("stone_low_sat") or ed in EDITION_1950:  # 1950 paste-over slips: paler blue (concrete) wash
        classes["stone"] = classes["stone"] | ((Hh >= 85) & (Hh <= 125) & (S >= 20) & (V >= 60) & (V <= pV - 12))
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
    # dark-ochre "fire proof construction" fills (hue <= 23, saturated) fall inside the yellow frame mask: re-class them
    # by the median colour inside the footprint (as the industrial tool's `reclass`)
    from PIL import ImageDraw
    nre = 0
    for f in feats:
        if f["cls"] != "frame":
            continue
        mk = Image.new("L", (rgb.shape[1], rgb.shape[0]), 0)
        ImageDraw.Draw(mk).polygon([tuple(q) for q in f["px_ring"]], fill=1)
        mk = cv2.erode(np.asarray(mk, np.uint8), np.ones((5, 5))).astype(bool)
        if mk.sum() < 15:
            continue
        if np.median(Hh[mk]) <= 23.5 and np.median(S[mk]) >= 100:
            f["cls"] = "fireproof"
            f["id"] = f["id"].replace(f"{key}_f", f"{key}_x", 1)
            nre += 1
    json.dump(feats, open(INTERIM / f"{key}.json", "w"))
    log(key, len(feats), "footprints", f"({nre} ochre fills re-classed fire-proof)" if nre else "")


def extract_regions(key):
    """second pass for the 1950 (corrected) sheets, as in the industrial tool: the colour masks miss faded fills on
    paste-over slips, so every region enclosed by drawn lines is classified by its median colour (pink brick, blue
    concrete, ochre fire-proof, yellow frame, grey iron; paper-coloured = no building) and added where nothing was found
    yet. ids <key>_r<n>, method = region."""
    import cv2
    from shapely.geometry import Polygon
    from shapely.strtree import STRtree
    G = json.load(open(INTERIM / f"{key}.M.json"))
    rgb = np.asarray(Image.open(G["img"]).convert("RGB"))
    hsv = cv2.cvtColor(cv2.medianBlur(rgb, 3), cv2.COLOR_RGB2HSV).astype(int)
    V = hsv[..., 2]; S_ = hsv[..., 1]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.int16)
    pm = (V > np.percentile(V, 30)) & (S_ < np.percentile(S_, 70))
    pS, pV = int(np.median(S_[pm])), int(np.median(V[pm]))
    med = cv2.medianBlur(gray.astype(np.uint8), 7).astype(np.int16)
    walls = ndi.binary_dilation(((gray < med - 28) & (gray < 105)) | (gray < 70), iterations=1)
    lab, n = ndi.label(~walls)
    sizes = ndi.sum(np.ones_like(lab), lab, range(1, n + 1))
    objs = ndi.find_objects(lab)
    have = [Polygon(f["px_ring"]).buffer(0) for f in json.load(open(INTERIM / f"{key}.json"))]
    tree = STRtree(have) if have else None
    M = np.array(G["M"]); blocks = G.get("blocks", []); zones_only = G.get("zones_only", False)
    out = []
    H_, W_ = lab.shape
    for i in range(n):
        if sizes[i] < 150 or sizes[i] > 120000:
            continue
        sl = objs[i]
        if sl[0].start < 12 or sl[1].start < 12 or sl[0].stop > H_ - 12 or sl[1].stop > W_ - 12:
            continue
        sub = ndi.binary_fill_holes(lab[sl] == i + 1)
        if min(sub.shape) < 9 or ndi.distance_transform_edt(np.pad(sub, 1)).max() < 4.5:
            continue
        pix = hsv[sl][lab[sl] == i + 1]
        h, s, v = np.median(pix[:, 0]), np.median(pix[:, 1]), np.median(pix[:, 2])
        if (h >= 155 or h <= 8) and s >= max(38, pS - 5):
            cls = "brick"
        elif 80 <= h <= 130 and s >= 18 and v < pV - 8:
            cls = "stone"
        elif 9 <= h <= 23 and s >= max(90, pS + 40):
            cls = "fireproof"
        elif 22 <= h <= 36 and s >= max(85, pS + 38):
            cls = "frame"
        else:
            continue
        ys, xs = np.nonzero(sub)
        hull = cv2.convexHull(np.column_stack([xs, ys]).astype(np.int32))
        if sub.sum() / max(cv2.contourArea(hull), 1) < 0.6:
            continue
        cs, _ = cv2.findContours(np.pad(sub, 2).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cs, key=cv2.contourArea)[:, 0, :].astype(float)
        c[:, 0] += sl[1].start - 2; c[:, 1] += sl[0].start - 2
        poly = Polygon(c).buffer(1.5, join_style=2).simplify(1.0)
        if poly.geom_type != "Polygon" or poly.area < 120:
            continue
        if tree is not None and sum(have[j].intersection(poly).area for j in tree.query(poly)) > 0.3 * poly.area:
            continue
        cx, cy = poly.centroid.x, poly.centroid.y
        best, bd = None, 1e9
        for b in blocks:
            x0, y0, x1, y1 = b["rect_px"]
            d = max(x0 - cx, 0, cx - x1) + max(y0 - cy, 0, cy - y1)
            if d < bd:
                best, bd = b, d
        if best is not None and bd <= 40:
            T, zone = np.array(best["M"]), best["name"]
        elif zones_only:
            continue
        else:
            T, zone = M, "sheet"
        ext = W.apply(T, np.asarray(poly.exterior.coords))
        out.append({"id": f"{key}_r{i + 1}", "cls": cls, "zone": zone, "px_centroid": [round(cx, 1), round(cy, 1)],
                    "px_ring": np.round(np.asarray(poly.exterior.coords), 1).tolist(), "area_m2": round(float(Polygon(ext).area), 1),
                    "ring_utm": np.round(ext, 2).tolist(), "holes_utm": [], "method": "region"})
    json.dump(json.load(open(INTERIM / f"{key}.json")) + out, open(INTERIM / f"{key}.json", "w"))
    log(key, len(out), "region footprints added")


# ----------------------------------------------------------------------------------------------- outputs
SCALE_NOMINAL = 0.2010  # m/px of the 25 % scans of the 1915 plates (median of the well-controlled block fits)


def modern_footprints():
    """today's footprints (Overture, OSM + ML outlines) around downtown San José, EPSG:32610, for modern_overlap."""
    import geopandas as gpd
    import pandas as pd
    import pyarrow.parquet as pq
    t = pq.read_table(BUILDINGS, columns=["px", "py", "geometry"],
                      filters=[("px", ">", BBOX[0]), ("px", "<", BBOX[2]), ("py", ">", BBOX[1]), ("py", "<", BBOX[3])]).to_pandas()
    return gpd.GeoDataFrame(t, geometry=gpd.GeoSeries.from_wkb(t.geometry), crs=4326).to_crs(32610)


def conf_of(f):
    """high: >= 4 control points, RMS <= 1.5 m, max <= 3 m; medium: >= 3 points and RMS <= 3 m, or a 2-corner block whose
    scale is within 1.5 % of the plate scale; low otherwise."""
    n, rms, mx = f.get("n", 0), f.get("rms", 9), f.get("max", 9)
    if n >= 4 and rms <= 1.5 and mx <= 3:
        return "high"
    if n == 2 and "M" in f:
        sc = math.hypot(f["M"][0][0], f["M"][1][0])
        return "medium" if abs(sc - SCALE_NOMINAL) <= 0.015 * SCALE_NOMINAL else "low"
    return "medium" if n >= 3 and rms <= 3 else "low"


def assemble(areas=None):
    import geopandas as gpd
    import shapely
    from pyproj import Transformer
    from shapely import make_valid
    from shapely.geometry import MultiPoint, Point, Polygon, mapping
    from shapely.ops import unary_union
    from shapely.strtree import STRtree
    to_ll = Transformer.from_crs(32610, 4326, always_xy=True)
    lonlat = lambda g: shapely.transform(g, lambda c: np.column_stack(to_ll.transform(c[:, 0], c[:, 1])))
    attrs = json.load(open(CONTROL / "attributes.json")) if (CONTROL / "attributes.json").exists() else {}
    fp = modern_footprints()
    fpg = list(fp.geometry.values)
    tree = STRtree(fpg)

    def overlap(g):
        parts = [fpg[i].intersection(g) for i in tree.query(g) if fpg[i].intersects(g)]
        return round(float(unary_union(parts).area / g.area), 2) if parts and g.area > 0 else 0.0
    rank = {"high": 0, "medium": 1, "low": 2}
    down = {"high": "medium", "medium": "low", "low": "low"}
    covers = {}
    for (area, year), keys in sorted(AREAS.items()):
        if areas and area not in areas:
            continue
        feats, cover = [], []
        for key in keys:
            vol, sheet = key.split("_")
            cfg = json.load(open(CONTROL / f"{key}.json"))
            base_key = cfg.get("registered_to", key)
            base = json.load(open(CONTROL / f"{base_key}.json"))
            G = json.load(open(INTERIM / f"{key}.M.json"))
            Gb = json.load(open(INTERIM / f"{base_key}.M.json"))
            map_year, vlabel = VOLUMES[vol]
            rec = W.sheet_rec(key)
            rows = json.load(open(INTERIM / f"{key}.json"))
            blocks = {b["name"]: b for b in G.get("blocks", [])}
            bblocks = {b["name"]: b for b in Gb.get("blocks", [])}
            W_, H_ = Image.open(G["img"]).size
            if G.get("zones_only"):  # block-wise sheets: the blocks and the streets between them
                rects = [Polygon(W.apply(np.array(b["M"]), [[b["rect_px"][0], b["rect_px"][1]], [b["rect_px"][2], b["rect_px"][1]],
                                                            [b["rect_px"][2], b["rect_px"][3]], [b["rect_px"][0], b["rect_px"][3]]])) for b in G["blocks"]]
                cv = unary_union(rects).convex_hull
            else:
                x0, y0, x1, y1 = G.get("valid_px") or [30, 30, W_ - 30, H_ - 30]
                x0, y0, x1, y1 = max(x0, 30), max(y0, 30), min(x1, W_ - 30), min(y1, H_ - 30)
                rect = Polygon([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
                if G.get("valid_poly_px"):
                    rect = rect.intersection(Polygon(G["valid_poly_px"]))
                cv = Polygon(W.apply(np.array(G["M"]), np.asarray(rect.exterior.coords)))
            cover.append(cv)
            # error of the neighbouring sheets this one is tied to: the fit of the block (tie_block) or sheet the tie used
            tie_rms = 0.0
            for e in base.get("points", []) + [c for b in base.get("blocks", []) for c in b["corners"]]:
                if "tie" in e:
                    Gt = json.load(open(INTERIM / f"{e['tie']}.M.json"))
                    tb = [b for b in Gt.get("blocks", []) if b["name"] == e.get("tie_block")]
                    tie_rms = max(tie_rms, tb[0]["rms"] if tb else Gt.get("rms", 0))
            # control extent of a sheet fit (for the extrapolation rule), in the base plate's pixels
            ctrl = [q["px"] for q in Gb.get("points", []) if q["label"] != "on street line"]
            hull = MultiPoint(ctrl).convex_hull.buffer(1) if len(ctrl) >= 3 else None
            if "registered_to" in cfg:
                T = np.array(cfg["T"])  # this scan -> base scan pixels
            for r in rows:
                g = make_valid(Polygon(r["ring_utm"], r.get("holes_utm") or []))
                if g.geom_type != "Polygon":
                    polys = [q for q in getattr(g, "geoms", []) if q.geom_type == "Polygon"]
                    if not polys:
                        continue
                    g = max(polys, key=lambda q: q.area)
                if g.area < 6:
                    continue
                zone = r.get("zone", "sheet")
                fitq = dict(blocks[zone] if zone in blocks else {"rms": G.get("rms", 9), "n": G.get("n", 0), "max": G.get("max", 9)})
                if zone in bblocks:
                    fitq["M"] = bblocks[zone]["M"]
                if "registered_to" in G:
                    fitq["rms"] = math.hypot(fitq.get("rms", 0), G.get("reg_rms_m", 0.3))
                if tie_rms:  # tied to a neighbouring sheet: its fit error adds
                    fitq["rms"] = math.hypot(fitq.get("rms", 0), tie_rms)
                cls, a = r["cls"], r["area_m2"]
                att = attrs.get(r["id"], {})
                if att.get("drop"):
                    continue
                material = {"frame": "frame", "brick": "brick", "stone": "concrete" if map_year >= 1950 else "stone",
                            "fireproof": "unknown" if map_year < 1900 else "concrete", "iron": "iron"}[cls]
                residential = bool(base.get("residential"))
                if cls == "frame":
                    st, us = ((1, "shed") if a < 30 else (1, "dwelling") if residential and a <= 300
                              else (1, "warehouse") if a >= 400 else (2, "store") if not residential else (1, "dwelling"))
                elif cls == "iron":
                    st, us = 1, "shed"
                else:
                    st, us = 2, "store" if not residential else "store"
                rule = "default (rule: material, size, district)"
                if att and "stories" in att:
                    stories, ssrc = att["stories"], "map (read from the sheet)"
                else:
                    stories, ssrc = st, rule
                use, usrc = (att["use"], "map (label)") if att.get("use") else (us, "default")
                material = att.get("material", material)
                conf = conf_of(fitq)
                if zone not in blocks and hull is not None:  # far outside the control points of a sheet fit
                    c0 = np.asarray(r["px_centroid"], float)
                    if "registered_to" in cfg:
                        c0 = T[:, :2] @ c0 + T[:, 2]
                    if hull.distance(Point(*c0)) > 600:
                        conf = down[conf]
                if (G.get("zones_only") and zone == "sheet") or r.get("confidence") == "low":
                    conf = "low"
                cap = base.get("confidence_cap")
                if cap and rank[conf] < rank[cap]:
                    conf = cap
                feats.append((g, {"id": r["id"], "map_year": map_year, "volume": f"sanborn{CITY}_{vol}", "volume_label": vlabel,
                                  "sheet": rec["id"], "sheet_no": int(sheet[:4].lstrip("0") or 0), "loc_url": f"https://www.loc.gov/item/sanborn{CITY}_{vol}/",
                                  "iiif": rec["info"].replace("/info.json", ""), "stories": stories, "stories_source": ssrc, "material": material,
                                  "use": use, "use_source": usrc, "name": att.get("name"), "sanborn_colour": cls, "confidence": conf,
                                  "georef": f"block {zone}" if zone in blocks else "sheet", "georef_rms_m": round(float(fitq.get("rms", 0)), 2),
                                  "extraction": r.get("method", "colour class"), "area_m2": round(float(g.area), 1), "modern_overlap": overlap(g)}))
        kept = []
        for i in sorted(range(len(feats)), key=lambda i: (rank[feats[i][1]["confidence"]], -feats[i][0].area)):
            g, p = feats[i]
            if not any(feats[j][1]["sheet"] != p["sheet"] and g.intersects(feats[j][0])
                       and g.intersection(feats[j][0]).area / min(g.area, feats[j][0].area) > 0.5 for j in kept):
                kept.append(i)

        def rnd(gj):
            out = json.loads(json.dumps(gj), parse_float=lambda v: round(float(v), 7))
            from shapely.geometry import shape
            g2 = shape(out)
            if g2.geom_type in ("Polygon", "MultiPolygon") and not g2.is_valid:
                g2 = shapely.set_precision(shape(gj), 1e-7)
                if out["type"] == "Polygon" and g2.geom_type == "MultiPolygon":
                    g2 = max(g2.geoms, key=lambda q: q.area)
                out = json.loads(json.dumps(mapping(g2)), parse_float=lambda v: round(float(v), 7))
            return out
        crs = {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}
        fc = {"type": "FeatureCollection", "name": f"{area}_{year}", "crs": crs,
              "features": [{"type": "Feature", "properties": feats[i][1], "geometry": rnd(mapping(lonlat(feats[i][0])))}
                           for i in sorted(kept, key=lambda i: feats[i][1]["id"])]}
        json.dump(fc, open(OUT / f"{area}_{year}.geojson", "w"))
        cu = unary_union(cover).buffer(20, join_style=2).buffer(-20, join_style=2)
        covers.setdefault(area, []).append({"type": "Feature", "properties": {"area": area, "map_year": year, "sheets": keys, "features": len(kept)},
                                            "geometry": rnd(mapping(lonlat(cu)))})
        log(area, year, len(kept), "features")
    for area, fs in covers.items():
        json.dump({"type": "FeatureCollection", "name": f"{area}_coverage", "features": sorted(fs, key=lambda f: f["properties"]["map_year"])},
                  open(OUT / f"{area}_coverage.geojson", "w"))


def all_keys():
    return list(dict.fromkeys(k for ks in AREAS.values() for k in ks))


if __name__ == "__main__":
    load_areas()
    index()
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage == "grid":
        k = sys.argv[2]
        box = tuple(int(v) for v in sys.argv[3:7]) if len(sys.argv) >= 7 else None
        print(grid(k, box, step=int(os.environ.get("STEP", 100)), scale=float(os.environ.get("SCALE", 1.0))))
        sys.exit()
    if stage == "register":
        W.register(sys.argv[2], sys.argv[3])
        sys.exit()
    keys = sys.argv[2:] or all_keys()
    if stage in ("all", "fetch"):
        for k in keys:
            print(image(k, int(os.environ.get("PCT", 25))))
    if stage in ("all", "georef"):
        for k in W.base_first(keys):
            W.georef(k)
    if stage in ("all", "extract"):
        for k in keys:
            extract(k)
            if k.split("_")[0] in EDITION_1950:
                extract_regions(k)
    if stage == "overlay":
        for k in keys:
            print(overlay(k))
    if stage in ("all", "assemble"):
        assemble(sys.argv[2:] if stage == "assemble" and len(sys.argv) > 2 else None)
