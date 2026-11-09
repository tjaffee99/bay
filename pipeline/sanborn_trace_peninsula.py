"""Trace demolished buildings of the Peninsula towns (San Mateo, Palo Alto + Mayfield, Redwood City) from Library of
Congress Sanborn maps.

Areas (data/manual/sanborn/README_<city>.md):
  san_mateo_downtown    B St / 3rd Ave / Main St / Railroad Ave, the old town between El Camino Real and the tracks
  palo_alto_downtown    University Ave and the blocks around it (Alma St -> Cowper St, Palo Alto Ave -> Forest Ave)
  palo_alto_mayfield    the old town of Mayfield (California Ave / El Camino Real; annexed by Palo Alto in 1925)
  redwood_city_downtown Main St / Broadway / Middlefield Rd, the old courthouse town

Only editions published before 1926 have images on loc.gov (the 1924 / 1949 Palo Alto, 1925 / 1945 Mayfield, 1950 San
Mateo and 1950 Redwood City volumes are listed without images), so every map year here has its own plates and its own
control (no SIFT registration onto an earlier plate as for the 1950 corrected volumes of San José / Oakland).

This is a thin extension of pipeline/sanborn_trace_eastbay.py (which extends sanborn_trace_waterfront.py): the same
block specs (four streets + estimated pixel corners), `refine` (block sides snapped onto the drawn block lines),
property corners from today's parcels (`pc`), offset corners from centrelines + printed street widths (`oc`),
similarity fits per block / group, colour segmentation with partition-wall splitting, and the same output schema and
confidence rules. What changes is the per-city configuration:
  * street centrelines: Overture transportation segments, release 2026-10-21.0 (roads_local.parquet: residential /
    unclassified / service / living street, + roads_region.parquet: motorway -> tertiary), clipped to the town box;
  * property lines: San Mateo County active parcels (data/raw/region_years/san_mateo_parcels) for San Mateo and
    Redwood City, Santa Clara County parcels (data/raw/region_years/santa_clara_county) for Palo Alto and Mayfield;
  * names / uses read off the sheets by eye: control/<city>/labels.json {key: [[x, y, name, use], ...]}, storeys:
    storeys.json {key: [[x, y, stories], ...]} (pixels on the 25 % scan; the footprint containing it, else the nearest
    within 25 px).

Usage:  python pipeline/sanborn_trace_peninsula.py <city> all            # fetch + georef + extract + assemble
        python pipeline/sanborn_trace_peninsula.py <city> fetch 005_0003
        python pipeline/sanborn_trace_peninsula.py <city> grid 005_0003 [x0 y0 x1 y1]   # scratch view with a pixel grid
        python pipeline/sanborn_trace_peninsula.py <city> refine 005_0003   # new sheet: snap the estimated block outlines
        python pipeline/sanborn_trace_peninsula.py <city> georef|extract|overlay|mosaic 005_0003
        python pipeline/sanborn_trace_peninsula.py <city> assemble
<city> = san_mateo | palo_alto | mayfield | redwood_city. Keys are <LOC item suffix>_<sheet>, e.g. 005_0003 =
sanborn00824_005 (San Mateo, Apr 1908) sheet 3.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import sanborn_trace_eastbay as E  # noqa: E402
import sanborn_trace_waterfront as W  # noqa: E402

OV = ROOT / "data/raw/overture/2026-10-21.0"
CITIES = {
    "san_mateo": {
        "loc": "00824", "area": "san_mateo_downtown",
        "volumes": {"004": (1901, "Jul 1901"), "005": (1908, "Apr 1908"), "006": (1920, "May 1920")},
        "parcels": ROOT / "data/raw/region_years/san_mateo_parcels/san_mateo_parcels.parquet",
        "bbox": (-122.345, 37.548, -122.300, 37.585),
    },
    "palo_alto": {
        "loc": "00747", "area": "palo_alto_downtown",
        "volumes": {"003": (1901, "Aug 1901"), "004": (1904, "Jun 1904"), "005": (1908, "May 1908")},
        "parcels": ROOT / "data/raw/region_years/santa_clara_county/santa_clara_county.parquet",
        "bbox": (-122.180, 37.432, -122.140, 37.456),
    },
    "mayfield": {
        "loc": "00677", "area": "palo_alto_mayfield",
        "volumes": {"004": (1904, "Jun 1904"), "005": (1908, "May 1908")},
        "parcels": ROOT / "data/raw/region_years/santa_clara_county/santa_clara_county.parquet",
        "bbox": (-122.160, 37.415, -122.130, 37.437),
    },
    "redwood_city": {
        "loc": "00783", "area": "redwood_city_downtown",
        "volumes": {"005": (1907, "Apr 1907"), "006": (1919, "Jun 1919")},
        "parcels": ROOT / "data/raw/region_years/san_mateo_parcels/san_mateo_parcels.parquet",
        "bbox": (-122.245, 37.472, -122.215, 37.495),
    },
}
ORD = {"first": "1st", "second": "2nd", "third": "3rd", "fourth": "4th", "fifth": "5th", "sixth": "6th",
       "seventh": "7th", "eighth": "8th", "ninth": "9th", "tenth": "10th"}
SUFFIX = {" st": " street", " ave": " avenue", " av": " avenue", " rd": " road", " blvd": " boulevard"}
CITY_NAME = None


def setup(city):
    """point the eastbay / waterfront module globals at this town."""
    global CITY_NAME
    c = CITIES[city]
    CITY_NAME = city
    E.RAW = ROOT / "data/raw/sanborn_loc/peninsula" / city
    E.INTERIM = ROOT / "data/interim/sanborn_peninsula" / city
    E.CONTROL = ROOT / "data/manual/sanborn/control" / city
    E.SCRATCH = Path(os.environ.get("SANBORN_SCRATCH", str(E.INTERIM / "scratch")))
    E.CITY = c["loc"]
    E.VOLUMES = c["volumes"]
    E.EDITION_1950 = ()
    E.PARCELS = c["parcels"]
    E.BBOX = c["bbox"]
    E.ALIASES = dict(c.get("aliases", {}))
    E.AREAS.clear()
    E._roads = E._blocks = None
    W.RAW, W.INTERIM, W.CONTROL = E.RAW, E.INTERIM, E.CONTROL
    W.EDITION_1950 = ()
    W._index = None
    E.INTERIM.mkdir(parents=True, exist_ok=True)
    E.CONTROL.mkdir(parents=True, exist_ok=True)
    E.load_areas()
    al = E.CONTROL / "aliases.json"  # street names on the sheets -> today's names (Overture)
    if al.exists():
        E.ALIASES.update(json.load(open(al)))
    return c


def norm_name(n):
    """'North B Street' -> 'b street', 'East 3rd Avenue' -> '3rd avenue', 'Third Ave' -> '3rd avenue' (directional
    prefixes dropped: San Mateo's N / S B St and E / W 3rd Ave are one street each), then the town's aliases."""
    n = (n if isinstance(n, str) else "").strip().lower().replace(".", "")
    for s, full in SUFFIX.items():
        if n.endswith(s):
            n = n[: -len(s)] + full
    for d in ("north ", "south ", "east ", "west "):
        if n.startswith(d) and n[len(d):] not in ("street", "avenue", "road"):
            n = n[len(d):]
    w = n.split(" ")
    if w and w[0] in ORD:
        w[0] = ORD[w[0]]
    n = " ".join(w).replace("saint ", "st ").replace("  ", " ")
    return E.ALIASES.get(n, n)


def roads():
    """Overture road segments in the town box (local + main road classes), EPSG:32610, with a normalised name."""
    if E._roads is None:
        import geopandas as gpd
        import pandas as pd
        cache = E.INTERIM / "roads.parquet"
        if cache.exists():
            g = gpd.read_parquet(cache)
        else:
            parts = [E._read_bbox(OV / f, ["id", "class", "name"]) for f in ("roads_local.parquet", "roads_region.parquet")]
            g = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), geometry="geometry", crs=4326)
            g = g[g.geometry.geom_type.isin(["LineString", "MultiLineString"])].drop_duplicates("id").to_crs(32610)
            g.to_parquet(cache)
        g = g.copy()
        g["key"] = g["name"].map(norm_name)
        E._roads = g
    return E._roads


E.norm_name = norm_name
E.roads = roads


def refine_block(gray, px4, R=16, inset=0.12):
    """eastbay refine_block with a continuity test: the block lines on these small-town plates are thin (1-2 px at
    25 %, grey 180-200 after JPEG blur, often split over two pixel rows) and run beside dashed double lines (water
    pipes, street edges) that are as dark on average. Darkness is measured against the 7-px median (a pixel 25+ grey
    levels darker than its neighbourhood, or darker than 110, counts), and an offset scores the share of positions
    along the side where a dark pixel lies within +-1.5 px across: a solid block line scores ~0.9-1.0, a dashed line
    ~0.5-0.6, so the solid line wins."""
    import cv2
    g = gray.astype(np.uint8)
    med = cv2.medianBlur(g, 7).astype(int)
    dark = ((g.astype(int) < med - 25) | (g < 110)).astype(float)
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
            ts = np.arange(t0 * Ls, t1 * Ls, 1.0)
            base = A + np.outer(ts, u)
            ext = np.arange(-R - 2, R + 2.01, 0.5)
            S = np.array([E.ndi.map_coordinates(dark, [(base + o * nrm)[:, 1], (base + o * nrm)[:, 0]], order=1, mode="constant")
                          for o in ext])  # (offsets, positions)
            prof = []
            for o in os_:
                j = int(round((o - ext[0]) / 0.5))
                prof.append(float((S[j - 3:j + 4].max(axis=0) > 0.5).mean()))
            prof = np.asarray(prof)
            k = int(np.argmax(prof))
            # several offsets reach the peak (the line is 2-3 px wide): take the middle of the plateau
            top = np.nonzero(prof >= prof[k] - 0.02)[0]
            top = top[np.abs(top - k) <= 8]
            k = int(round(np.median(top)))
            peaks.append(float(prof[k])); offs.append(float(os_[k])); mids.append(A + (t0 + t1) / 2 * Ls * u)
        if abs(offs[1] - offs[0]) > 4:
            j = int(np.argmax(peaks))
            offs = [offs[j], offs[j]]
        p0, p1 = mids[0] + offs[0] * nrm, mids[1] + offs[1] * nrm
        lines.append((p0, (p1 - p0) / np.hypot(*(p1 - p0))))
        q.append(round(min(peaks), 2))
    corners = [E.line_x(lines[i - 1], lines[i]) for i in range(4)]
    return np.array(corners), q


E.refine_block = refine_block


def solid_lines(key, minlen=120, box=None):
    """scratch aid for writing block specs: long solid axis-aligned dark lines of a sheet (block outlines) as
    ('H', y, x0, x1) / ('V', x, y0, y1) runs, merged across 1-3 px of thickness; dashed lines have gaps and drop out."""
    import cv2
    g = np.asarray(E.Image.open(E.image(key)).convert("L"))
    med = cv2.medianBlur(g, 7).astype(int)
    dark = ((g.astype(int) < med - 25) | (g < 110))
    dark = E.ndi.binary_closing(dark, structure=np.ones((3, 3)))  # bridge 1-px JPEG breaks
    out = []
    for orient, D in (("H", dark), ("V", dark.T)):
        runs = []
        for r in range(D.shape[0]):
            row = D[r].astype(np.int8)
            d = np.diff(np.concatenate([[0], row, [0]]))
            st, en = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
            for a, b in zip(st, en):
                if b - a >= minlen:
                    runs.append((r, a, b))
        runs.sort()
        merged = []
        for r, a, b in runs:  # same line on adjacent rows
            for m in merged:
                if abs(m[0][-1] - r) <= 2 and min(b, m[2]) - max(a, m[1]) > 0.5 * min(b - a, m[2] - m[1]):
                    m[0].append(r); m[1] = min(m[1], a); m[2] = max(m[2], b)
                    break
            else:
                merged.append([[r], a, b])
        for rs, a, b in merged:
            c = float(np.mean(rs))
            if box and not (box[0] <= (a + b) / 2 <= box[2] if orient == "H" else box[1] <= (a + b) / 2 <= box[3]):
                pass
            out.append((orient, round(c, 1), int(a), int(b)))
    return out


def storeys_to_attributes():
    """control/<city>/storeys.json {key: [[x, y, stories], ...]} (storey numbers read off the 25 % scan by eye, pixel
    inside the building) -> attributes.json {footprint id: {"stories": n}} for the eastbay assemble: the footprint
    containing the pixel, else the nearest within 25 px."""
    from shapely.geometry import Point, Polygon
    p = E.CONTROL / "storeys.json"
    if not p.exists():
        return
    attrs = {}
    for key, marks in json.load(open(p)).items():
        f = E.INTERIM / f"{key}.json"
        if not f.exists():
            continue
        polys = [(r["id"], Polygon(r["px_ring"]).buffer(0)) for r in json.load(open(f))]
        for x, y, st in marks:
            pt = Point(x, y)
            hit = [rid for rid, pg in polys if pg.contains(pt)]
            if not hit:
                near = sorted((pg.distance(pt), rid) for rid, pg in polys)
                hit = [near[0][1]] if near and near[0][0] <= 25 else []
            if hit:
                attrs.setdefault(hit[0], {})["stories"] = st
            else:
                E.log(key, "storey mark not placed:", x, y, st)
    json.dump(attrs, open(E.CONTROL / "attributes.json", "w"), indent=1)


def assemble():
    """eastbay assemble (names / uses from labels.json, storeys via attributes.json)."""
    storeys_to_attributes()
    E.assemble()


def main():
    city = sys.argv[1]
    setup(city)
    E.index()
    stage = sys.argv[2] if len(sys.argv) > 2 else "all"
    if stage == "grid":
        k = sys.argv[3]
        box = tuple(int(v) for v in sys.argv[4:8]) if len(sys.argv) >= 8 else None
        print(E.grid(k, box, step=int(os.environ.get("STEP", 100)), scale=float(os.environ.get("SCALE", 1.0))))
        return
    if stage == "lines":  # long solid block lines (for writing specs)
        for ln in solid_lines(sys.argv[3], int(os.environ.get("MINLEN", 120))):
            print(*ln)
        return
    if stage == "sheets":  # list the sheets of each volume
        for vol, recs in E.index().items():
            print(vol, E.VOLUMES.get(vol), [r["id"].split("-")[-1] for r in recs])
        return
    keys = sys.argv[3:] or E.all_keys()
    if stage in ("all", "fetch"):
        for k in keys:
            print(E.image(k, int(os.environ.get("PCT", 25))))
    if stage == "refine":
        for k in keys:
            E.refine(k)
    if stage in ("all", "georef"):
        for k in E.base_first(keys):
            W.georef(k)
    if stage == "freeze":
        for k in keys:
            E.freeze(k)
    if stage == "mosaic":
        for k in keys:
            print(E.corner_mosaic(k))
    if stage in ("all", "extract"):
        for k in keys:
            E.extract(k)
            E.reclass(k)
    if stage == "overlay":
        for k in keys:
            print(E.overlay(k, scale=float(os.environ.get("SCALE", 0.5))))
    if stage in ("all", "assemble"):
        assemble()


if __name__ == "__main__":
    main()
