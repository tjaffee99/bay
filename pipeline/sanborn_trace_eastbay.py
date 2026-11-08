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

Usage:  python pipeline/sanborn_trace_eastbay.py all                  # fetch + georef + extract + tracks + assemble
        python pipeline/sanborn_trace_eastbay.py georef 005_0095      # one stage, some sheets
        python pipeline/sanborn_trace_eastbay.py register 015_0095 005_0095   # SIFT registration of a 1950/51 plate
        python pipeline/sanborn_trace_eastbay.py fetch 005_0095       # download (25 %)
        python pipeline/sanborn_trace_eastbay.py grid 005_0095 [x0 y0 x1 y1]   # scratch view with a pixel grid
        python pipeline/sanborn_trace_eastbay.py refine 005_0095      # new sheet: snap estimated block outlines (once)
        python pipeline/sanborn_trace_eastbay.py mosaic|overlay 005_0095       # scratch checks of corners / footprints
New sheet: write the control file with spec(key, {"blocks": {name: {"N", "S", "W", "E": streets, "px": [NW, NE, SE, SW]
pixel estimates (+-15 px on the 25 % image), "skip", "w", "with"}}}), then refine + georef; the control files hold the
refined pixels (norefine), so reruns reproduce the outputs.
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
    if n.startswith("west ") and n[5:] not in ("street", "st", "avenue", "ave"):  # but 'West Street' is a street
        n = n[5:]
    n = n.replace(" st", " street") if n.endswith(" st") else n
    n = n.replace(" ave", " avenue") if n.endswith(" ave") else n
    if n and (n[0].isdigit() or n == "west") and " " not in n:  # '7th' -> '7th street', 'West' -> 'west street'
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
    ds = []
    for n in (a, b):
        for r in (R, 2 * R, 4 * R):  # a street that ends short of the crossing: its direction from further away
            try:
                ds.append(street_line(n, X, r)[1])
                break
            except ValueError:
                if r == 4 * R:
                    raise
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
    if not all(2.5 <= o <= 24 for o in offs):  # not a street-side property line (superblock, plaza, freeway land)
        raise ValueError(f"implausible property-line offsets {np.round(offs, 1)} at {a} x {b} {q}")
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
    scale_prior, valid_px, valid_poly_px, confidence_cap, residential, notes)}. The pixel corners are estimates until
    `refine` moves the block sides onto the drawn block outline."""
    cfg = {k: v for k, v in s.items() if k != "blocks"}
    cfg["blocks"] = []
    for n, b in s["blocks"].items():
        e = {"name": n, "streets": {k: b[k] for k in "NSWE"}, "px4_est": b["px"], "corners": block4(n, b)}
        for k in ("w", "skip", "oc", "near", "no_refine", "with"):
            if k in b:
                e[k] = b[k]
        cfg["blocks"].append(e)
    cfg.setdefault("pct", 25)
    CONTROL.mkdir(parents=True, exist_ok=True)
    json.dump(cfg, open(CONTROL / f"{key}.json", "w"), indent=1)
    return cfg


def refine_block(gray, px4, R=16, inset=0.12):
    """move each side of an approximate block outline (4 pixel corners, ring order) onto the strongest long dark line
    within +-R px (darkness profile across the side over the central 76 % of its length, two halves fitted separately
    so a slightly rotated scan is followed); corners = crossings of adjacent sides. Returns (corners, peak darkness of
    each side: ~0.8 = a drawn block line along the whole side, < 0.35 = no line found)."""
    g = gray.astype(float)
    dark = (g < min(125, np.median(g) - 55)).astype(float)
    P = np.asarray(px4, float)
    lines, q = [], []
    for i in range(4):
        A, B = P[i], P[(i + 1) % 4]
        Ls = float(np.hypot(*(B - A)))
        u = (B - A) / Ls
        nrm = np.array([-u[1], u[0]])
        os_ = np.arange(-R, R + 0.01, 0.5)
        mids, offs, peaks = [], [], []
        for t0, t1 in ((inset, 0.5), (0.5, 1 - inset)):
            ts = np.arange(t0 * Ls, t1 * Ls, 1.5)
            prof = np.array([ndi.map_coordinates(dark, [(A + np.outer(ts, u) + o * nrm)[:, 1], (A + np.outer(ts, u) + o * nrm)[:, 0]],
                                                 order=1, mode="constant").mean() for o in os_])
            prof = np.convolve(prof, [0.25, 0.5, 0.25], mode="same")
            k = int(np.argmax(prof))
            peaks.append(float(prof[k])); offs.append(float(os_[k])); mids.append(A + (t0 + t1) / 2 * Ls * u)
        if abs(offs[1] - offs[0]) > 4:  # the halves disagree: the stronger half's offset, parallel to the estimate
            j = int(np.argmax(peaks))
            offs = [offs[j], offs[j]]
        p0, p1 = mids[0] + offs[0] * nrm, mids[1] + offs[1] * nrm
        lines.append((p0, (p1 - p0) / np.hypot(*(p1 - p0))))
        q.append(round(min(peaks), 2))
    corners = [line_x(lines[i - 1], lines[i]) for i in range(4)]
    return np.array(corners), q


def refine(key, weak=0.35):
    """snap the estimated block outlines of a control file onto the drawn block lines (once per new sheet; writes the
    refined pixels with norefine = 1, keeps the estimates). A corner on a side without a drawn line (peak < `weak`) is
    dropped from the fit when the block keeps two other corners."""
    f = CONTROL / f"{key}.json"
    cfg = json.load(open(f))
    gray = np.asarray(Image.open(image(key)).convert("L"))
    for b in cfg.get("blocks", []):
        if "px4_est" not in b:
            continue
        if b.get("no_refine"):
            c4, q = np.asarray(b["px4_est"], float), [None] * 4
        else:
            c4, q = refine_block(gray, b["px4_est"], R=b.get("refine_R", cfg.get("refine_R", 16)))
        b["px4"], b["edge_q"] = np.round(c4, 1).tolist(), q
        b["corners"] = b.get("corners_all", b["corners"])
        names = ("NW", "NE", "SE", "SW")
        weak_c = set()
        for i in range(4):  # side i runs from corner i to corner i+1
            if q[i] is not None and q[i] < weak:
                weak_c |= {names[i], names[(i + 1) % 4]}
        keep = [c for c in b["corners"] if c["corner"] not in weak_c]
        for c in b["corners"]:
            j = names.index(c["corner"])
            c["x"], c["y"], c["norefine"] = float(round(c4[j][0], 1)), float(round(c4[j][1], 1)), 1
            c["weak"] = c["corner"] in weak_c and len(keep) >= 2
        b["corners_all"] = b["corners"]
        b["corners"] = [c for c in b["corners"] if not c["weak"]]
        if any(qq is not None and qq < weak for qq in q):
            log(key, "block", b["name"], "weak sides", q, "-> corners used:", [c["corner"] for c in b["corners"]])
        xs, ys = c4[:, 0], c4[:, 1]
        b["zone_px"] = [float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())]
    # world positions: a corner whose control fails (no such crossing, implausible property line and no printed
    # width to fall back on) is dropped and logged
    for b in cfg.get("blocks", []):
        ok = []
        for c in b["corners"]:
            try:
                world_of(c)
                ok.append(c)
            except (ValueError, KeyError, np.linalg.LinAlgError) as e:
                c["drop"] = str(e)[:120]
                log(key, "block", b["name"], c["corner"], "dropped:", c["drop"])
        b["corners"] = ok
    # a block fitted together with its neighbours ("with": same strip of the sheet, streets drawn to scale there):
    # its zone keeps its own outline, the fit uses all their corners
    own = {b["name"]: [dict(c, block=b["name"]) for c in b["corners"]] for b in cfg.get("blocks", [])}
    def sim(cs):
        M, d = W.fit([(c["x"], c["y"]) for c in cs], [world_of(c)[0] for c in cs], prior=cfg.get("scale_prior"))
        return math.hypot(M[0, 0], M[1, 0]), math.degrees(math.atan2(M[1, 0], M[0, 0])), float(np.sqrt((d ** 2).mean()))
    for b in cfg.get("blocks", []):
        if not b.get("with"):
            continue
        grp = own[b["name"]] + [c for n in b["with"] for c in own[n]]
        if len(own[b["name"]]) >= 4 and len(grp) > len(own[b["name"]]):
            # a block with all four corners keeps its own fit if it agrees with the group's scale and rotation
            s0, r0, _ = sim(grp)
            s1, r1, e1 = sim(own[b["name"]])
            if abs(s1 / s0 - 1) < 0.015 and abs(r1 - r0) < 0.8 and e1 < 1.5:
                continue
            log(key, "block", b["name"], f"own fit off (scale {s1:.4f} vs {s0:.4f}, rot {r1:.2f} vs {r0:.2f}, RMS {e1:.2f}): group fit")
        b["corners"] = grp
    # outliers: refit without the worst corner while it is off by > 3 m and > 3x the median of the others
    # (a wrongly snapped side, a street realigned since the map); dropped corners are logged
    dropped = set()
    for b in cfg.get("blocks", []):
        while len(b["corners"]) >= 4:
            px = [(c["x"], c["y"]) for c in b["corners"]]
            wo = [world_of(c)[0] for c in b["corners"]]
            _, d = W.fit(px, wo, prior=cfg.get("scale_prior"))
            j = int(np.argmax(d))
            rest = np.delete(d, j)
            if d[j] > 3.0 and d[j] > 3 * max(np.median(rest), 0.3):
                c = b["corners"].pop(j)
                tag = (c.get("block", b["name"]), c["corner"])
                if tag not in dropped:
                    log(key, "block", b["name"], "outlier corner", tag, f"{d[j]:.1f} m dropped")
                dropped.add(tag)
            else:
                break
    json.dump(cfg, open(f, "w"), indent=1)


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


# ----------------------------------------------------------------------------------------------- footprints
def extract(key):
    """colour-segment the building fills (yellow frame, pink brick, blue stone / concrete, ochre fire-proof, grey iron)
    as in the waterfront tool, with the two changes of pipeline/sanborn_trace_southbay.py (San José): (1) the pink brick
    wash can be darker than on the SF plates, so drawn lines are found relative to their surroundings (darker than
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


def hsv_of(key):
    import cv2
    G = json.load(open(INTERIM / f"{key}.M.json"))
    rgb = np.asarray(Image.open(G["img"]).convert("RGB"))
    return G, rgb, cv2.cvtColor(cv2.medianBlur(rgb, 3), cv2.COLOR_RGB2HSV).astype(int)


def reclass(key):
    """brown 'fire proof construction' fills (dark ochre, hue 18-23) fall inside the waterfront tool's yellow class on
    the vol. 2 / 1950 scans (yellow frame is hue 25-31): split them off by the median hue inside the footprint."""
    import cv2
    from PIL import ImageDraw
    p = INTERIM / f"{key}.json"
    F = json.load(open(p))
    G, rgb, hsv = hsv_of(key)
    n = 0
    for f in F:
        if f["cls"] != "frame":
            continue
        m = Image.new("L", (rgb.shape[1], rgb.shape[0]), 0)
        ImageDraw.Draw(m).polygon([tuple(q) for q in f["px_ring"]], fill=1)
        m = cv2.erode(np.asarray(m, np.uint8), np.ones((5, 5))).astype(bool)
        if m.sum() < 15:
            continue
        h, s = np.median(hsv[m][:, 0]), np.median(hsv[m][:, 1])
        if h <= 23 and s >= 90:
            f["cls"] = "fireproof"
            n += 1
    json.dump(F, open(p, "w"))
    if n:
        log(key, n, "frame -> fireproof (brown) by hue")


def extract_regions(key):
    """second pass for the 1950 paste-over sheets: the colour classes miss faded fills on the correction slips, so take
    every region enclosed by drawn lines, classify it by its median colour (pink brick, blue concrete, brown fireproof,
    yellow frame, grey iron; paper-coloured = no building) and add those not already found. ids <key>_r<n>."""
    import cv2
    from shapely.geometry import Polygon
    G, rgb, hsv = hsv_of(key)
    Hh, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(int)
    pm = (V > np.percentile(V, 30)) & (S < np.percentile(S, 70))
    pS, pV = int(np.median(S[pm])), int(np.median(V[pm]))
    dark = gray < min(125, pV - 55)
    walls = ndi.binary_dilation(dark, iterations=1)
    lab, n = ndi.label(~walls)
    sizes = ndi.sum(np.ones_like(lab), lab, range(1, n + 1))
    objs = ndi.find_objects(lab)
    have = [Polygon(f["px_ring"]).buffer(0) for f in json.load(open(INTERIM / f"{key}.json"))]
    from shapely.strtree import STRtree
    tree = STRtree(have) if have else None
    M = np.array(G["M"]); blocks = G.get("blocks", []); zones_only = G.get("zones_only", False)
    vp = G.get("valid_px")
    out = []
    H_, W_ = lab.shape
    for i in range(n):
        if sizes[i] < 150 or sizes[i] > 120000:
            continue
        sl = objs[i]
        if sl[0].start < 12 or sl[1].start < 12 or sl[0].stop > H_ - 12 or sl[1].stop > W_ - 12:
            continue
        sub = ndi.binary_fill_holes(lab[sl] == i + 1)
        hh, ww = sub.shape
        if min(hh, ww) < 9 or ndi.distance_transform_edt(np.pad(sub, 1)).max() < 4.5:
            continue
        pix = hsv[sl][lab[sl] == i + 1]
        h, s, v = np.median(pix[:, 0]), np.median(pix[:, 1]), np.median(pix[:, 2])
        if (h >= 160 or h <= 8) and s >= max(38, pS - 5):
            cls = "brick"
        elif 55 <= h <= 130 and s >= 14 and v < pV + 5:
            cls = "stone"
        elif 17 <= h <= 23 and s >= max(85, pS + 35):
            cls = "fireproof"
        elif 24 <= h <= 34 and s >= max(95, pS + 45):
            cls = "frame"
        elif s <= pS + 2 and v <= pV - 28 and v >= 95:
            cls = "iron"
        else:
            continue
        ys, xs = np.nonzero(sub)
        hull = cv2.convexHull(np.column_stack([xs, ys]).astype(np.int32))
        solid = sub.sum() / max(cv2.contourArea(hull), 1)
        if solid < 0.6 or (cls == "iron" and (solid < 0.8 or sub.sum() < 400)):
            continue
        cs, _ = cv2.findContours(np.pad(sub, 2).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cs, key=cv2.contourArea)[:, 0, :].astype(float)
        c[:, 0] += sl[1].start - 2; c[:, 1] += sl[0].start - 2
        poly = Polygon(c).buffer(1.5, join_style=2).simplify(1.0)  # half the wall line back
        if poly.geom_type != "Polygon" or poly.area < 120:
            continue
        if tree is not None:
            hit = sum(have[j].intersection(poly).area for j in tree.query(poly))
            if hit > 0.3 * poly.area:
                continue
        cx, cy = poly.centroid.x, poly.centroid.y
        if vp and not (vp[0] <= cx <= vp[2] and vp[1] <= cy <= vp[3]):
            continue
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
    F = json.load(open(INTERIM / f"{key}.json")) + out
    json.dump(F, open(INTERIM / f"{key}.json", "w"))
    log(key, len(out), "region footprints added")


# ----------------------------------------------------------------------------------------------- outputs
def modern_footprints():
    """today's Overture footprints in the Oakland box (EPSG:32610), cached."""
    import geopandas as gpd
    cache = INTERIM / "overture_buildings.parquet"
    if cache.exists():
        return gpd.read_parquet(cache)
    g = _read_bbox(BUILDINGS, ["id"]).to_crs(32610)
    g.to_parquet(cache)
    return g


def block_polys(G):
    """world polygon of each fitted block zone (its refined outline, else its pixel rectangle)."""
    from shapely.geometry import Polygon
    out = []
    for b in G.get("blocks", []):
        q = b.get("px4") or [[b["rect_px"][0], b["rect_px"][1]], [b["rect_px"][2], b["rect_px"][1]],
                             [b["rect_px"][2], b["rect_px"][3]], [b["rect_px"][0], b["rect_px"][3]]]
        out.append((b["name"], Polygon(W.apply(np.array(b["M"]), q))))
    return out


def collinear(points):
    """True when the control points of a fit lie on (nearly) one line: the second principal spread < 8 m."""
    P = np.asarray(points, float)
    if len(P) < 3:
        return True
    sv = np.linalg.svd(P - P.mean(axis=0), compute_uv=False)
    return sv[1] / math.sqrt(len(P)) < 8.0


def assemble():
    import geopandas as gpd
    import shapely
    from pyproj import Transformer
    from shapely import make_valid
    from shapely.geometry import Point, Polygon, mapping
    from shapely.ops import unary_union
    from shapely.strtree import STRtree
    to_ll = Transformer.from_crs(32610, 4326, always_xy=True)

    def lonlat(g):
        return shapely.transform(g, lambda c: np.column_stack(to_ll.transform(c[:, 0], c[:, 1])))
    attrs = json.load(open(CONTROL / "attributes.json")) if (CONTROL / "attributes.json").exists() else {}
    # names / uses read off the sheets, by pixel position (control/oakland/labels.json: {key: [[x, y, name, use], ...]}):
    # the footprint containing the label point, else the nearest within 25 px
    labels = json.load(open(CONTROL / "labels.json")) if (CONTROL / "labels.json").exists() else {}
    for key, labs in labels.items():
        if not (INTERIM / f"{key}.json").exists():
            continue
        rows = json.load(open(INTERIM / f"{key}.json"))
        polys = [(r["id"], Polygon(r["px_ring"]).buffer(0)) for r in rows]
        for x, y, name, use in labs:
            pt = Point(x, y)
            hit = [rid for rid, pg in polys if pg.contains(pt)]
            if not hit:
                near = sorted((pg.distance(pt), rid) for rid, pg in polys)
                hit = [near[0][1]] if near and near[0][0] <= 25 else []
            if hit:
                attrs.setdefault(hit[0], {}).update({"name": name, **({"use": use} if use else {})})
            else:
                log(key, "label not placed:", name)
    fp = modern_footprints()
    fpg = list(fp.geometry.values)
    tree = STRtree(fpg)

    def overlap(g):
        parts = [fpg[i].intersection(g) for i in tree.query(g) if fpg[i].intersects(g)]
        return round(float(unary_union(parts).area / g.area), 2) if parts and g.area > 0 else 0.0

    rank = {"high": 0, "medium": 1, "low": 2}

    def conf_of(f):
        if f.get("n", 0) >= 4 and f.get("rms", 9) <= 1.5 and f.get("max", 9) <= 3:
            c = "high"
        elif f.get("n", 0) >= 3 and f.get("rms", 9) <= 3:
            c = "medium"
        elif f.get("n", 0) == 2 and "M" in f and abs(math.hypot(f["M"][0][0], f["M"][1][0]) - 0.2015) <= 0.003:
            c = "medium"  # two corners: exact fit, checked only by the plate scale (50 ft = 1 in: ~0.2015 m/px)
        else:
            c = "low"
        if c == "high" and f.get("collinear"):
            c = "medium"  # control along one street only: the across-street direction is extrapolated
        return c
    covers = {}
    for (area, year), keys in sorted(AREAS.items()):
        feats, cover = [], []
        for key in keys:
            vol, sheet = key.split("_")
            cfg = json.load(open(CONTROL / f"{key}.json"))
            base = json.load(open(CONTROL / f"{cfg['registered_to']}.json")) if "registered_to" in cfg else cfg
            G = json.load(open(INTERIM / f"{key}.M.json"))
            Gb = json.load(open(INTERIM / f"{G['registered_to']}.M.json")) if "registered_to" in G else G
            map_year, vlabel = VOLUMES[vol]
            rec = W.sheet_rec(key)
            rows = json.load(open(INTERIM / f"{key}.json"))
            blocks = {b["name"]: b for b in G.get("blocks", [])}
            bblocks = {b["name"]: b for b in Gb.get("blocks", [])}
            bpolys = block_polys(G)
            cv = unary_union([pg.buffer(12, join_style=2) for _, pg in bpolys]).buffer(15, join_style=2).buffer(-15, join_style=2)
            cover.append(cv)
            residential = bool(base.get("residential"))
            for r in rows:
                g = make_valid(Polygon(r["ring_utm"], r.get("holes_utm") or []))
                if g.geom_type != "Polygon":
                    polys = [q for q in getattr(g, "geoms", []) if q.geom_type == "Polygon"]
                    if not polys:
                        continue
                    g = max(polys, key=lambda q: q.area)
                if g.area < 6 or not cv.contains(g.representative_point()):
                    continue
                zone = r.get("zone", "sheet")
                fitq = dict(blocks[zone] if zone in blocks else {"rms": G.get("rms", 9), "n": G.get("n", 0), "max": G.get("max", 9)})
                if zone in bblocks:
                    fitq["M"] = bblocks[zone]["M"]
                    fitq["collinear"] = collinear([W.apply(np.array(bblocks[zone]["M"]), [q["px"]])[0] for q in bblocks[zone].get("points", [])])
                if "registered_to" in G:
                    fitq["rms"] = math.hypot(fitq.get("rms", 0), G.get("reg_rms_m", 0.3))
                cls, a = r["cls"], r["area_m2"]
                att = attrs.get(r["id"], {})
                if att.get("drop"):
                    continue
                material = {"frame": "frame", "brick": "brick", "stone": "concrete" if map_year >= 1950 else "stone",
                            "fireproof": "unknown" if map_year < 1900 else "concrete", "iron": "iron"}[cls]
                if cls == "frame":
                    st, us = ((1, "shed") if a < 30 else (2, "dwelling") if residential and a <= 300
                              else (1, "warehouse") if a >= 300 else (2, "dwelling") if residential else (2, "store"))
                elif cls == "iron":
                    st, us = 1, "shed"
                else:
                    st, us = (2, "warehouse") if residential else (2, "store")
                rule = "default (rule: material, size, district)"
                if att and "stories" in att:
                    stories, ssrc = att["stories"], "map (read from the sheet)"
                else:
                    stories, ssrc = st, rule
                use, usrc = (att["use"], "map (label)") if att.get("use") else (us, "default")
                conf = conf_of(fitq)
                if base.get("confidence_cap") and rank[conf] < rank[base["confidence_cap"]]:
                    conf = base["confidence_cap"]
                if G.get("zones_only") and zone == "sheet":
                    conf = "low"
                feats.append((g, {"id": r["id"], "map_year": map_year, "volume": f"sanborn{CITY}_{vol}", "volume_label": vlabel,
                                  "sheet": rec["id"], "sheet_no": int(sheet[:4].lstrip("0") or 0), "loc_url": f"https://www.loc.gov/item/sanborn{CITY}_{vol}/",
                                  "iiif": rec["info"].replace("/info.json", ""), "stories": stories, "stories_source": ssrc, "material": material,
                                  "use": use, "use_source": usrc, "name": att.get("name"), "sanborn_colour": cls,
                                  "confidence": conf, "georef": f"block {zone}" if zone in blocks else "sheet",
                                  "georef_rms_m": round(float(fitq.get("rms", 0)), 2), "extraction": r.get("method", "colour class"),
                                  "area_m2": round(float(g.area), 1), "modern_overlap": overlap(g)}))
        kept = []
        for i in sorted(range(len(feats)), key=lambda i: (rank[feats[i][1]["confidence"]], -feats[i][0].area)):
            g, p = feats[i]
            if not any(feats[j][1]["sheet"] != p["sheet"] and g.intersects(feats[j][0])
                       and g.intersection(feats[j][0]).area / min(g.area, feats[j][0].area) > 0.5 for j in kept):
                kept.append(i)

        def rnd(gj):
            from shapely.geometry import shape
            out = json.loads(json.dumps(gj), parse_float=lambda s: round(float(s), 7))
            g2 = shape(out)
            if g2.geom_type in ("Polygon", "MultiPolygon") and not g2.is_valid:  # rounding can pinch a ring
                g2 = shapely.set_precision(shape(gj), 1e-7)
                if out["type"] == "Polygon" and g2.geom_type == "MultiPolygon":
                    g2 = max(g2.geoms, key=lambda q: q.area)
                out = json.loads(json.dumps(mapping(g2)), parse_float=lambda s: round(float(s), 7))
            return out
        crs = {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}
        fc = {"type": "FeatureCollection", "name": f"{area}_{year}", "crs": crs,
              "features": [{"type": "Feature", "properties": feats[i][1], "geometry": rnd(mapping(lonlat(feats[i][0])))}
                           for i in sorted(kept, key=lambda i: feats[i][1]["id"])]}
        json.dump(fc, open(OUT / f"{area}_{year}.geojson", "w"))
        cu = unary_union(cover)
        covers.setdefault(area, []).append({"type": "Feature", "properties": {"area": area, "map_year": year, "sheets": keys, "features": len(kept)},
                                            "geometry": rnd(mapping(lonlat(cu)))})
        log(area, year, len(kept), "features")
    for area, fs in covers.items():
        json.dump({"type": "FeatureCollection", "name": f"{area}_coverage", "features": sorted(fs, key=lambda f: f["properties"]["map_year"])},
                  open(OUT / f"{area}_coverage.geojson", "w"))


def assemble_tracks():  # adapted from sanborn_trace_waterfront.assemble_tracks (Oakland volumes, 7th / 3rd St labels)
    """<area>_<year>_tracks.geojson: track centrelines per map year; overlaps between sheets kept once (best fit first)."""
    import shapely
    from pyproj import Transformer
    from shapely.geometry import LineString, Point, Polygon, mapping
    from shapely.ops import unary_union
    from shapely.strtree import STRtree
    to_ll = Transformer.from_crs(32610, 4326, always_xy=True)
    rank = {"high": 0, "medium": 1, "low": 2}
    down = {"high": "medium", "medium": "low", "low": "low"}
    rnd = lambda gj: json.loads(json.dumps(gj), parse_float=lambda s: round(float(s), 7))
    for (area, year), keys in AREAS.items():
        if not all((INTERIM / f"{k}.tracks.json").exists() for k in keys):
            continue
        info = []
        for key in keys:
            G = json.load(open(INTERIM / f"{key}.M.json"))
            kcfg = json.load(open(CONTROL / f"{key}.json"))
            base = json.load(open(CONTROL / f"{kcfg['registered_to']}.json")) if "registered_to" in kcfg else kcfg
            if G.get("zones_only"):
                q = dict(n=min(b["n"] for b in G["blocks"]), rms=max(b["rms"] for b in G["blocks"]), max=max(b["max"] for b in G["blocks"]))
                polys = [Polygon(W.apply(np.array(b["M"]), [[b["rect_px"][0], b["rect_px"][1]], [b["rect_px"][2], b["rect_px"][1]],
                                                          [b["rect_px"][2], b["rect_px"][3]], [b["rect_px"][0], b["rect_px"][3]]])) for b in G["blocks"]]
                cover = unary_union(polys).convex_hull.buffer(12)
            else:
                q = dict(n=G.get("n", 0), rms=G.get("rms", 9), max=G.get("max", 9))
                W_, H_ = Image.open(G["img"]).size
                x0, y0, x1, y1 = G.get("valid_px") or [30, 30, W_ - 30, H_ - 30]
                rect = Polygon([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
                if G.get("valid_poly_px"):
                    rect = rect.intersection(Polygon(G["valid_poly_px"]))
                cover = Polygon(W.apply(np.array(G["M"]), np.asarray(rect.exterior.coords)))
            if "registered_to" in G:
                q["rms"] = math.hypot(q["rms"], G.get("reg_rms_m", 0.3))
            if G.get("tie_rms"):
                q["rms"] = math.hypot(q["rms"], G["tie_rms"])
            conf = "high" if q["n"] >= 4 and q["rms"] <= 1.5 and q["max"] <= 3 else "medium" if q["n"] >= 3 and q["rms"] <= 3 else "low"
            if base.get("confidence_cap") and rank[conf] < rank[base["confidence_cap"]]:
                conf = base["confidence_cap"]
            info.append((rank[conf], q["rms"], key, conf, q, cover, G))
        info.sort(key=lambda t: (t[0], t[1]))
        claimed, feats = None, []
        for _, _, key, conf, q, cover, G in info:
            vol, sheet = key.split("_")
            rec = W.sheet_rec(key)
            tcfg = W.track_cfg(key)
            H_img = Image.open(G["img"]).size[1]
            for t in json.load(open(INTERIM / f"{key}.tracks.json")):
                ln = LineString(t["utm"])
                px = np.asarray(t["px"])
                d = px[-1] - px[0]
                if px[:, 1].min() > 0.88 * H_img and abs(d[1]) < 0.03 * abs(d[0]) + 2 and ln.length < 120:
                    continue  # the "Scale of Feet" bar at the foot of the sheet
                if claimed is not None:
                    ln = ln.difference(claimed.buffer(-1.0))
                for part in getattr(ln, "geoms", [ln]):
                    if part.is_empty or part.geom_type != "LineString" or part.length < 8:
                        continue
                    mid = px[len(px) // 2]
                    rr, rsrc = tcfg.get("railroad"), "map label" if tcfg.get("railroad") else None
                    for r in tcfg.get("railroads", []):
                        if Polygon(r["poly_px"]).contains(Point(*mid)):
                            rr, rsrc = r["name"], "map label"
                    is_main = any(Polygon(m).contains(Point(*mid)) for m in tcfg.get("main_px", []))
                    c = conf if t.get("share_in_blocks", 1) >= 0.6 else down[conf]
                    feats.append([part, {"id": f"{t['id']}" + (f"_{len(feats)}" if part.length < ln.length - 0.5 else ""), "map_year": VOLUMES[vol][0],
                                         "volume": f"sanborn{CITY}_{vol}", "volume_label": VOLUMES[vol][1], "sheet": rec["id"],
                                         "sheet_no": int(sheet[:4].lstrip("0") or 0), "loc_url": f"https://www.loc.gov/item/sanborn{CITY}_{vol}/",
                                         "iiif": rec["info"].replace("/info.json", ""), "railroad": rr, "railroad_source": rsrc,
                                         "kind": "main" if is_main else None, "kind_source": "map label" if is_main else None,
                                         "confidence": c, "georef": "blocks (rubber sheet)" if G.get("zones_only") else "sheet",
                                         "georef_rms_m": round(float(q["rms"]), 2), "length_m": round(part.length, 1)}])
            claimed = cover if claimed is None else claimed.union(cover)
        # kind by rule: a yard track has >= 2 parallel tracks 3-15 m to either side along most of its length
        geoms = [f[0] for f in feats]
        tree = STRtree(geoms)
        for i, (g, p) in enumerate(feats):
            if p["kind"]:
                continue
            hits = 0
            samples = [g.interpolate(d) for d in np.arange(2.5, g.length, 5.0)] or [g.interpolate(0.5, normalized=True)]
            for pt in samples:
                d0 = g.project(pt)
                a, b = g.interpolate(max(0, d0 - 2)), g.interpolate(min(g.length, d0 + 2))
                tv = np.array([b.x - a.x, b.y - a.y]); tv = tv / (np.hypot(*tv) or 1)
                par = 0
                for j in tree.query(pt.buffer(15)):
                    if j == i:
                        continue
                    o = geoms[j]
                    dist = o.distance(pt)
                    if not 3 <= dist <= 15:
                        continue
                    dj = o.project(pt)
                    a2, b2 = o.interpolate(max(0, dj - 2)), o.interpolate(min(o.length, dj + 2))
                    tv2 = np.array([b2.x - a2.x, b2.y - a2.y]); tv2 = tv2 / (np.hypot(*tv2) or 1)
                    par += abs(float(tv @ tv2)) > 0.98
                hits += par >= 2
            p["kind"] = "yard" if hits >= 0.5 * len(samples) else "spur"
            p["kind_source"] = "rule: parallel tracks" if p["kind"] == "yard" else "rule: default"
        for g, p in feats:  # railroad named on the sheets along these streets (most of the line within 20 m of the centreline)
            for street, name in (("7th", "Southern Pacific R.R. (electric), 7th St line"), ("3rd", "Western Pacific R.R. (3rd St spur track)")):
                try:
                    L = street_line(street, np.array([g.centroid.x, g.centroid.y]), 250)
                except ValueError:
                    continue
                nrm = np.array([-L[1][1], L[1][0]])
                cs = np.asarray(g.coords)
                if np.mean(np.abs((cs - L[0]) @ nrm) < 20) > 0.8 and p["railroad"] is None:
                    p["railroad"], p["railroad_source"] = name, f"map label along {street} St"
        fc = {"type": "FeatureCollection", "name": f"{area}_{year}_tracks",
              "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
              "features": [{"type": "Feature", "properties": p,
                            "geometry": rnd(mapping(shapely.transform(g, lambda c: np.column_stack(to_ll.transform(c[:, 0], c[:, 1])))))}
                           for g, p in sorted(feats, key=lambda f: f[1]["id"])]}
        json.dump(fc, open(OUT / f"{area}_{year}_tracks.geojson", "w"))
        log(area, year, len(feats), "track lines", round(sum(f[0].length for f in feats)), "m")


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
    if stage == "refine":
        for k in keys:
            refine(k)
    if stage in ("all", "extract"):
        for k in keys:
            extract(k)
            reclass(k)
            if k.split("_")[0] in EDITION_1950:
                extract_regions(k)
    if stage == "overlay":
        for k in keys:
            print(overlay(k, scale=float(os.environ.get("SCALE", 0.5))))
    if stage in ("all", "tracks"):
        for k in keys:
            W.tracks(k)
    if stage in ("all", "assemble"):
        assemble()
        assemble_tracks()
