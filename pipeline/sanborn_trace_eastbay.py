"""Trace demolished buildings of Oakland (West Oakland, downtown, Chinatown) from Library of Congress Sanborn maps.

Areas (data/manual/sanborn/README_oakland.md):
  oakland_west       West Oakland: the 7th St corridor, the Cypress St freeway corridor, the Main Post Office / West
                     Oakland BART blocks, Acorn, the Brush / Castro (I-980) corridor
  oakland_downtown   City Center (12th-14th St, Broadway-Jefferson / Clay), the Convention Center / Marriott blocks,
                     Chinatown and the Lake Merritt BART / Oakland Museum / Laney College blocks

This is an extension of pipeline/sanborn_trace_waterfront.py (San Francisco) and reuses its georeferencing (similarity
fits per sheet or per block, SIFT registration of the corrected 1950/51 plates onto the 1911/12 plates), colour
segmentation and output schema. What is new is the control geometry. SF's control came from DataSF street centrelines;
here it comes from
  * Overture transportation segments (all road classes in the Oakland box, data/raw/overture/2026-10-21.0/
    roads_oakland_sanborn.parquet; roads_region.parquet holds only the main roads) for street crossings and straight
    street lines, extended across vanished blocks, and
  * Alameda County parcel polygons (data/raw/region_years/alameda_county_2021) for property lines: a Sanborn sheet draws
    the block outline (property line), so a block corner is the crossing of the two property lines fitted to today's
    parcel block next to the street crossing (`pc` control entries). Where the block is gone (superblocks of the
    clearances) the corner is the crossing of the extended centrelines offset by half of each street's width as printed
    on the sheet (`bcx`).
modern_overlap is measured against today's Overture footprints (data/raw/overture/2026-10-21.0/region5_building.parquet).

Inputs (committed, hand-measured):  data/manual/sanborn/control/oakland/<key>.json (control / registration),
                                    attributes.json (storeys / use / names read off the sheets), areas.json
Downloads (cached, gitignored):     data/raw/sanborn_loc_oakland/ (LOC item JSON, IIIF images)
Intermediates:                      data/interim/sanborn_eastbay/
Outputs:                            data/manual/sanborn/oakland_<area>_<year>.geojson, _coverage.geojson,
                                    oakland_<area>_<year>_tracks.geojson

Usage:  python pipeline/sanborn_trace_eastbay.py all                  # fetch + georef + extract + assemble
        python pipeline/sanborn_trace_eastbay.py georef 005_0095      # one stage, some sheets
        python pipeline/sanborn_trace_eastbay.py register 015_0095 005_0095
        python pipeline/sanborn_trace_eastbay.py fetch 005_0095       # download (25 %)
        python pipeline/sanborn_trace_eastbay.py grid 005_0095 [x0 y0 x1 y1]   # scratch view with a pixel grid
Keys are <LOC item suffix>_<sheet>, e.g. 005_0095 = sanborn00727_005 (1911-12 vol. 1) sheet 95.
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

RAW = ROOT / "data/raw/sanborn_loc_oakland"
INTERIM = ROOT / "data/interim/sanborn_eastbay"
CONTROL = ROOT / "data/manual/sanborn/control/oakland"
OUT = ROOT / "data/manual/sanborn"
SCRATCH = Path(os.environ.get("SANBORN_SCRATCH", str(INTERIM / "scratch")))
W.RAW, W.INTERIM, W.CONTROL = RAW, INTERIM, CONTROL  # the waterfront stages read / write through these globals
FT = W.FT
CITY = "00727"  # LOC Sanborn id of Oakland

VOLUMES = {  # LOC item suffix (sanborn00727_<sfx>) -> (map year, label)
    "001": (1889, "1889"),
    "002": (1902, "1902 Vol. 1"), "003": (1903, "1903 Vol. 2"), "004": (1903, "1903 Vol. 3"),
    "005": (1912, "1911-1912 Vol. 1 (1912)"), "006": (1911, "1911 Vol. 2"), "007": (1911, "1911-1912 Vol. 3 (1911)"),
    "015": (1951, "1912-Nov 1951 Vol. 1 (corrected to Nov 1951)"), "016": (1950, "1911-Nov 1950 Vol. 2 (corrected to Nov 1950)"),
    "017": (1950, "1911-Oct 1950 Vol. 3 (corrected to Oct 1950)"),
}
EDITION_1950 = ("015", "016", "017")
W.EDITION_1950 = EDITION_1950  # the waterfront colour rules for corrected (1950) plates
AREAS: dict[tuple[str, int], list[str]] = {}
ROADS = ROOT / "data/raw/overture/2026-10-21.0/roads_oakland_sanborn.parquet"
PARCELS = ROOT / "data/raw/region_years/alameda_county_2021/alameda_county_2021.parquet"
BUILDINGS = ROOT / "data/raw/overture/2026-10-21.0/region5_building.parquet"
BBOX = (-122.335, 37.780, -122.245, 37.840)  # West Oakland, downtown, Chinatown, Lake Merritt (+ margin)


def log(*a):
    print("sanborn_eastbay:", *a, flush=True)


def load_areas():
    p = CONTROL / "areas.json"
    if p.exists():
        for k, v in json.load(open(p)).items():
            a, y = k.rsplit("_", 1)
            AREAS[(a, int(y))] = v
    return AREAS


# ----------------------------------------------------------------------------------------------- LOC index / images
def index():
    """{vol: [{id, info, w, h}]} for the Oakland volumes, cached in data/raw/sanborn_loc_oakland/index.json."""
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
    if p.exists() and p.stat().st_size > 10000:
        return p
    out = W.image(key, pct)
    time.sleep(1.5)  # be polite to tile.loc.gov
    return out


def overlay(key, out=None, scale=0.5, box=None):
    """scratch check: traced footprints (outline colour by class) and block zones drawn on the sheet."""
    from PIL import ImageDraw
    G = json.load(open(INTERIM / f"{key}.M.json"))
    im = Image.open(G["img"]).convert("RGB")
    d = ImageDraw.Draw(im)
    col = {"frame": (255, 90, 0), "brick": (150, 0, 150), "stone": (0, 0, 255), "fireproof": (120, 60, 0), "iron": (60, 60, 60), "wharf": (0, 150, 0)}
    rows = json.load(open(INTERIM / f"{key}.json")) if (INTERIM / f"{key}.json").exists() else []
    if (INTERIM / f"{key}.manual.json").exists():
        rows += json.load(open(INTERIM / f"{key}.manual.json"))
    for r in rows:
        d.line([tuple(q) for q in r["px_ring"]] + [tuple(r["px_ring"][0])], fill=col.get(r["cls"], (0, 200, 0)), width=2)
    for b in G.get("blocks", []):
        x0, y0, x1, y1 = b["rect_px"]
        d.rectangle([x0, y0, x1, y1], outline=(0, 170, 0), width=2)
        for q in b.get("points", []):
            x, y = q["px"]
            d.ellipse([x - 5, y - 5, x + 5, y + 5], outline=(255, 0, 0), width=2)
    if (INTERIM / f"{key}.tracks.json").exists():
        for t in json.load(open(INTERIM / f"{key}.tracks.json")):
            d.line([tuple(q) for q in t["px"]], fill=(0, 160, 255), width=3)
    if box:
        im = im.crop(box)
    if scale != 1:
        im = im.resize((int(im.size[0] * scale), int(im.size[1] * scale)), Image.LANCZOS)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    out = out or SCRATCH / f"{key}_overlay.jpg"
    im.save(out, quality=85)
    return out


def grid(key, box=None, step=100, scale=1.0, out=None):
    """scratch view of a sheet with a labelled pixel grid (for reading control pixels by eye)."""
    from PIL import ImageDraw
    im = Image.open(image(key)).convert("RGB")
    x0, y0, x1, y1 = box or (0, 0, im.size[0], im.size[1])
    im = im.crop((x0, y0, x1, y1))
    d = ImageDraw.Draw(im)
    for x in range((x0 // step + 1) * step, x1, step):
        d.line([(x - x0, 0), (x - x0, y1 - y0)], fill=(0, 160, 0) if x % 500 else (220, 0, 0), width=1)
        for yy in range(0, y1 - y0, 300):
            d.text((x - x0 + 2, yy + 2), str(x), fill=(0, 0, 200))
    for y in range((y0 // step + 1) * step, y1, step):
        d.line([(0, y - y0), (x1 - x0, y - y0)], fill=(0, 160, 0) if y % 500 else (220, 0, 0), width=1)
        for xx in range(0, x1 - x0, 300):
            d.text((xx + 2, y - y0 + 2), str(y), fill=(0, 0, 200))
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
ALIASES = {  # street names on the 1911-12 / 1950 sheets -> today's names (Overture)
    "cypress street": "mandela parkway", "cypress": "mandela parkway",
    "grove street": "martin luther king junior way", "grove": "martin luther king junior way",
    "first street": "1st street", "second street": "2nd street", "third street": "3rd street", "fourth street": "4th street",
    "fifth street": "5th street", "sixth street": "6th street", "seventh street": "7th street", "eighth street": "8th street",
    "ninth street": "9th street", "tenth street": "10th street", "eleventh street": "11th street", "twelfth street": "12th street",
    "thirteenth street": "13th street", "fourteenth street": "14th street", "fifteenth street": "15th street",
    "sixteenth street": "16th street", "seventeenth street": "17th street", "eighteenth street": "18th street",
    "nineteenth street": "19th street", "twentieth street": "20th street",
}


def to_utm():
    global _to_utm
    if _to_utm is None:
        from pyproj import Transformer
        _to_utm = Transformer.from_crs(4326, 32610, always_xy=True)
    return _to_utm


def norm_name(n):
    """'West 14th Street' -> '14th street', 'Fifth Street' -> '5th street', '7th' -> '7th street', 'Cypress' ->
    'mandela parkway'. 'East 12th Street' (east of Lake Merritt) stays a different street."""
    n = (n if isinstance(n, str) else "").strip().lower().replace(".", "")
    if n.startswith("west "):
        n = n[5:]
    n = n.replace(" st", " street") if n.endswith(" st") else n
    n = n.replace(" ave", " avenue") if n.endswith(" ave") else n
    if n and n[0].isdigit() and " " not in n:
        n = n + " street"
    return ALIASES.get(n, n)


def _read_bbox(path, cols, batch=50000):
    """rows of a GeoParquet file whose geometry bbox meets BBOX (read in batches: the county files are large)."""
    import geopandas as gpd
    import pandas as pd
    import pyarrow.parquet as pq
    import shapely
    parts = []
    for b in pq.ParquetFile(path).iter_batches(batch_size=batch, columns=cols + ["geometry"]):
        df = b.to_pandas()
        g = shapely.from_wkb(df["geometry"].values)
        bx = shapely.bounds(g)
        m = (bx[:, 2] >= BBOX[0]) & (bx[:, 0] <= BBOX[2]) & (bx[:, 3] >= BBOX[1]) & (bx[:, 1] <= BBOX[3])
        if m.any():
            parts.append(gpd.GeoDataFrame(df.loc[m, cols].copy(), geometry=g[m], crs=4326))
    return gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), geometry="geometry", crs=4326)


def roads():
    """Overture road segments (all classes) in the Oakland box, in EPSG:32610, with a normalised name."""
    global _roads
    if _roads is None:
        g = _read_bbox(ROADS, ["id", "class", "name"])
        g = g[g.geometry.geom_type.isin(["LineString", "MultiLineString"])].copy()
        g = g[~g["class"].isin(["footway", "cycleway", "path", "steps", "pedestrian", "track"])]
        g["key"] = g["name"].map(norm_name)
        _roads = g.to_crs(32610)
    return _roads


def street_rows(name):
    r = roads()
    k = norm_name(name)
    rows = r[r.key == k]
    if rows.empty:
        rows = r[r.key.str.startswith(k + " ")] if " " not in k else rows
    if rows.empty:
        raise KeyError(f"unknown street {name!r}")
    return rows


def line_x(L1, L2):
    A = np.array([L1[1], -L2[1]]).T
    t = np.linalg.solve(A, L2[0] - L1[0])
    return L1[0] + t[0] * L1[1]


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


def xing(a, b, near=None):
    """crossing of two named streets (EPSG:32610); `near` (UTM) picks among several crossings; divided roads give a
    cluster of crossings (averaged); streets that no longer meet are extended as straight lines (fitted within 120 m
    of their closest approach, or of `near`)."""
    import shapely
    from shapely.geometry import Point
    from shapely.ops import nearest_points
    ga = shapely.union_all(street_rows(a).geometry.values)
    gb = shapely.union_all(street_rows(b).geometry.values)
    if near is not None:
        nb = Point(*near).buffer(400)
        ga, gb = ga.intersection(nb), gb.intersection(nb)
    I = ga.intersection(gb)
    pts = [np.array(p.coords[0]) for p in getattr(I, "geoms", [I]) if not p.is_empty and p.geom_type == "Point"]
    if pts:
        pts = np.array(pts)
        ref = np.asarray(near, float) if near is not None else pts[0]
        d = np.hypot(*(pts - ref).T)
        c = pts[d <= d.min() + 35]
        return c.mean(axis=0), "node" if len(c) == 1 else f"node x{len(c)}"
    pa, pb = nearest_points(ga, gb)
    mid = np.array([(pa.x + pb.x) / 2, (pa.y + pb.y) / 2]) if near is None else np.asarray(near, float)
    L1, L2 = street_line(a, np.array([pa.x, pa.y]), 120), street_line(b, np.array([pb.x, pb.y]), 120)
    if abs(L1[1] @ L2[1]) < 0.9:
        return line_x(L1, L2), f"lines extended (gap {pa.distance(pb):.0f} m)"
    return mid, f"closest approach {pa.distance(pb):.0f} m"


def near_xy(near):
    if len(near) == 2 and all(isinstance(v, (int, float)) for v in near):
        return np.array(near, float)
    return xing(*near)[0]


def parcel_blocks():
    """blocks = connected unions of today's parcels (EPSG:32610), for property lines."""
    global _blocks
    if _blocks is None:
        import geopandas as gpd
        import shapely
        from shapely.strtree import STRtree
        cache = INTERIM / "parcel_blocks.parquet"
        if cache.exists():
            b = gpd.read_parquet(cache)
        else:
            g = _read_bbox(PARCELS, ["APN"], 20000).to_crs(32610)
            g = g[g.geometry.area > 1]
            u = shapely.buffer(shapely.union_all(shapely.buffer(g.geometry.values, 0.4, join_style="mitre")), -0.4, join_style="mitre")
            b = gpd.GeoDataFrame(geometry=[p for p in getattr(u, "geoms", [u]) if p.area > 50], crs=32610)
            INTERIM.mkdir(parents=True, exist_ok=True)
            b.to_parquet(cache)
        _blocks = (list(b.geometry.values), STRtree(list(b.geometry.values)))
    return _blocks


def grid_axes(a, b, X, R=150):
    """unit vectors at a crossing: eN along the more north-south of the two streets (northward), eE along the other
    (eastward)."""
    ds = [street_line(n, X, R)[1] for n in (a, b)]
    k = int(np.argmax([abs(d[1]) / (abs(d[0]) + 1e-9) for d in ds]))
    eN, eE = ds[k], ds[1 - k]
    eN = eN if eN[1] > 0 else -eN
    eE = eE if eE[0] > 0 else -eE
    return eN, eE, k


def property_corner(a, b, q, near=None, reach=(18, 75), R=150):
    """block corner (property-line crossing) in quadrant q (NE/NW/SE/SW: N along the more north-south street of the
    two, E along the other) of the a x b crossing, from today's parcel block in that quadrant: along each street the
    property line is the street's direction at the median normal offset of the block boundary points facing that
    street (18-75 m from the crossing, so a rounded or cut-off corner does not count), and the two property lines are
    intersected."""
    from shapely.geometry import Point
    X = xing(a, b, near)[0]
    eN, eE, _ = grid_axes(a, b, X, R)
    sN = 1 if "N" in q else -1
    sE = 1 if "E" in q else -1
    probe = X + sN * 30 * eN + sE * 30 * eE
    geoms, tree = parcel_blocks()
    cand = [geoms[i] for i in tree.query(Point(*probe).buffer(25))]
    blk = min(cand, key=lambda g: g.distance(Point(*probe))) if cand else None
    if blk is None or blk.distance(Point(*probe)) > 15:
        raise ValueError(f"no parcel block in quadrant {q} of {a} x {b}")
    ring = np.asarray(blk.exterior.coords)[:, :2]
    pts = []
    for p0, p1 in zip(ring[:-1], ring[1:]):
        n = max(2, int(np.hypot(*(p1 - p0)) / 0.5))
        pts += [p0 + t * (p1 - p0) for t in np.linspace(0, 1, n, endpoint=False)]
    rel = np.array(pts) - X
    nN = np.array([eN[1], -eN[0]]); nN = nN if nN @ eE > 0 else -nN  # normal of the NS street, toward +E
    nE = np.array([-eE[1], eE[0]]); nE = nE if nE @ eN > 0 else -nE  # normal of the EW street, toward +N
    offs = []
    for e_al, n_ac, s_al, s_ac in ((eN, nN, sN, sE), (eE, nE, sE, sN)):
        al, ac = rel @ e_al * s_al, rel @ n_ac * s_ac
        sel = (al > reach[0]) & (al < reach[1]) & (ac > 0)
        if sel.sum() < 5:
            raise ValueError(f"property line not found at {a} x {b} {q}")
        acs = ac[sel]
        offs.append(float(np.median(acs[acs <= acs.min() + 2.0])))
    p = X + np.linalg.solve(np.array([nN, nE]), np.array([sE * offs[0], sN * offs[1]]))
    return p, f"property corner {q} of {a} x {b}", offs


def offset_corner(a, b, q, wa, wb, near=None, R=200):
    """block corner from the centrelines (straight fits, extended where the street is gone) offset by half of each
    street's width in feet (as printed on the sheet) toward quadrant q."""
    X, how = xing(a, b, near)
    eN, eE, k = grid_axes(a, b, X, R)
    wNS, wEW = (wa, wb) if k == 0 else (wb, wa)
    sN = 1 if "N" in q else -1
    sE = 1 if "E" in q else -1
    nN = np.array([eN[1], -eN[0]]); nN = nN if nN @ eE > 0 else -nN
    nE = np.array([-eE[1], eE[0]]); nE = nE if nE @ eN > 0 else -nE
    p = X + np.linalg.solve(np.array([nN, nE]), np.array([sE * wNS * FT / 2, sN * wEW * FT / 2]))
    return p, f"offset corner {q} of {a} x {b} ({wa:g}/{wb:g} ft, {how})"


# ----------------------------------------------------------------------------------------------- control entries
_world_of = W.world_of


def world_of(c):
    """control entry -> UTM point. Adds to the waterfront tool's entries:
    pc:  [street a, street b], q: block corner on today's parcel (property) lines; if that block is gone and `w`
         [ft a, ft b] is given, falls back to the offset corner (`oc`).
    oc:  [street a, street b], q, w: [ft a, ft b]: centrelines (extended) offset by half the printed street widths.
    xl:  crossing of the two straight centreline fits."""
    if "pc" in c:
        try:
            p, lab, offs = property_corner(c["pc"][0], c["pc"][1], c["q"], c.get("near"), tuple(c.get("reach", (18, 75))), c.get("R", 150))
            return p, c.get("label", lab)
        except ValueError:
            if "w" not in c:
                raise
            return offset_corner(c["pc"][0], c["pc"][1], c["q"], c["w"][0], c["w"][1], c.get("near"))
    if "oc" in c:
        return offset_corner(c["oc"][0], c["oc"][1], c["q"], c["w"][0], c["w"][1], c.get("near"))
    if "xl" in c:
        a, b = c["xl"]
        X, how = xing(a, b, c.get("near"))
        return X, c.get("label", f"{a} x {b} [{how}]")
    if "a" in c:
        p, how = xing(c["a"], c["b"], c.get("near"))
        return p, f"{c['a']} x {c['b']} [{how}]"
    return _world_of(c)


W.world_of = world_of
W.xing = lambda a, b: xing(a, b)
W.street_line = street_line
W.near_xy = near_xy

_measured = W.measured


def measured(c, masks):
    """pixel of a control entry: stored if `norefine`; block corners snap to the nearest block lines."""
    if c.get("norefine") or masks is None:
        return c["x"], c["y"]
    if "pc" in c or "oc" in c:
        return W.refine_corner(masks, c["x"], c["y"], win=c.get("win", 12), span=c.get("span", 60))
    return _measured(c, masks)


W.measured = measured


def freeze(key):
    """write the refined pixel positions of a georeferenced sheet back into its control file (norefine), so reruns
    reproduce the fit exactly."""
    f = CONTROL / f"{key}.json"
    cfg = json.load(open(f))
    G = json.load(open(INTERIM / f"{key}.M.json"))
    pts = {b["name"]: [q["px"] for q in b["points"]] for b in G.get("blocks", [])}
    n = 0
    for b in cfg.get("blocks", []):
        for c, px in zip(b["corners"], pts.get(b["name"], [])):
            if not c.get("norefine"):
                c["x0"], c["y0"] = c["x"], c["y"]
                c["x"], c["y"], c["norefine"] = round(px[0], 1), round(px[1], 1), 1
                n += 1
    json.dump(cfg, open(f, "w"), indent=1)
    log(key, "froze", n, "control pixels")


def compact(key, spec):
    """control file from a compact spec: {"blocks": {name: [[x, y, street a, street b, q(, extra)], ...]}, plus any
    other keys (zones_only, scale_prior, valid_px, valid_poly_px, confidence_cap, residential)}. A corner given as
    [x, y, a, b, q] is a property corner (`pc`); extra = {"w": [ft a, ft b]} adds the fall-back widths, {"oc": 1, "w":
    [...]} forces the offset corner."""
    def entry(c):
        if isinstance(c[2], dict):
            return dict(c[2], x=float(c[0]), y=float(c[1]))
        extra = dict(c[5]) if len(c) > 5 else {}
        kind = "oc" if extra.pop("oc", None) else "pc"
        e = {kind: [c[2], c[3]], "q": c[4], "x": float(c[0]), "y": float(c[1])}
        e.update(extra)
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


QUAD = {"NW": ("W", "N", "SE"), "NE": ("E", "N", "SW"), "SE": ("E", "S", "NW"), "SW": ("W", "S", "NE")}


def block4(name, b):
    """corners of a block given by its four streets: {"N": street, "S": .., "W": .., "E": .., "px": [[x, y] of the NW,
    NE, SE, SW corner (compass sense of the grid, whatever the sheet's orientation)], "w": {"N": ft, ...} printed
    widths (fall-back where the parcel block is gone), "oc": [corners on the offset rule], "skip": [corners not used]}"""
    out = []
    w = b.get("w", {})
    for cn, px in zip(("NW", "NE", "SE", "SW"), b["px"]):
        if cn in b.get("skip", []) or px is None:
            continue
        sa, sb, q = QUAD[cn]
        e = {"x": float(px[0]), "y": float(px[1]), "q": q, "corner": cn}
        kind = "oc" if cn in b.get("oc", []) else "pc"
        e[kind] = [b[sa], b[sb]]
        if sa in w and sb in w:
            e["w"] = [w[sa], w[sb]]
        if kind == "oc" and "w" not in e:
            raise ValueError(f"block {name}: offset corner {cn} needs the widths of {b[sa]} and {b[sb]}")
        if b.get("near"):
            e["near"] = b["near"]
        out.append(e)
    return out


def spec(key, s):
    """control file from a block spec: {"blocks": {name: block4 dict}, other keys passed through (zones_only,
    scale_prior, valid_px, valid_poly_px, confidence_cap, residential, notes)}."""
    cfg = {k: v for k, v in s.items() if k != "blocks"}
    cfg["blocks"] = [{"name": n, "corners": block4(n, b), "streets": {k: b[k] for k in "NSWE"}} for n, b in s["blocks"].items()]
    cfg.setdefault("pct", 25)
    CONTROL.mkdir(parents=True, exist_ok=True)
    json.dump(cfg, open(CONTROL / f"{key}.json", "w"), indent=1)
    return cfg


def corner_mosaic(key, half=40, zoom=3, out=None):
    """scratch check of the refined control pixels: a crop around each corner (cross = the pixel used), labelled with
    block, corner and residual."""
    from PIL import ImageDraw
    G = json.load(open(INTERIM / f"{key}.M.json"))
    im = Image.open(G["img"]).convert("RGB")
    tiles = []
    for b in G.get("blocks", []):
        for q in b["points"]:
            x, y = q["px"]
            t = im.crop((int(x - half), int(y - half), int(x + half), int(y + half))).resize((2 * half * zoom, 2 * half * zoom), Image.NEAREST)
            d = ImageDraw.Draw(t)
            c = half * zoom
            d.line([(c - 25, c), (c + 25, c)], fill=(255, 0, 0), width=1)
            d.line([(c, c - 25), (c, c + 25)], fill=(255, 0, 0), width=1)
            d.rectangle([0, 0, 2 * c - 1, 14], fill=(255, 255, 255))
            d.text((2, 1), f"{b['name']} {q['label'][:28]} {q['res_m']}m", fill=(0, 0, 0))
            tiles.append(t)
    if not tiles:
        return None
    n = len(tiles)
    cols = min(6, n)
    rows = (n + cols - 1) // cols
    s = 2 * half * zoom
    M = Image.new("RGB", (cols * s + cols * 4, rows * s + rows * 4), (255, 255, 255))
    for i, t in enumerate(tiles):
        M.paste(t, ((i % cols) * (s + 4), (i // cols) * (s + 4)))
    SCRATCH.mkdir(parents=True, exist_ok=True)
    out = out or SCRATCH / f"{key}_corners.jpg"
    M.save(out, quality=88)
    return out


# ----------------------------------------------------------------------------------------------- driver
def all_keys():
    return list(dict.fromkeys(k for ks in AREAS.values() for k in ks))


def base_first(keys):
    reg = [k for k in keys if "registered_to" in json.load(open(CONTROL / f"{k}.json"))]
    return [k for k in keys if k not in reg] + reg


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
            image(k, int(os.environ.get("PCT", 25)))
    if stage in ("all", "georef"):
        for k in base_first(keys):
            W.georef(k)
    if stage == "mosaic":
        for k in keys:
            print(corner_mosaic(k))
    if stage == "freeze":
        for k in keys:
            freeze(k)
    if stage in ("all", "extract"):
        for k in keys:
            extract(k)
            reclass(k)
            if k.split("_")[0] in EDITION_1950:
                extract_regions(k)
    if stage == "overlay":
        for k in keys:
            print(overlay(k, scale=float(os.environ.get("SCALE", 0.5))))
    if stage in ("all", "assemble"):
        assemble()
