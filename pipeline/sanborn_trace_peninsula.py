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
        "R": 80,  # street directions fitted within 80 m of a crossing: B St bends at 1st Av (-55 deg north of it, -49 south)
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
_E_world_of = E.world_of


def world_of(c):
    """eastbay world_of with the town's default fitting radius for street directions at a crossing (CITIES[..]["R"])."""
    R = CITIES[CITY_NAME].get("R") if CITY_NAME else None
    if R and ("pc" in c or "oc" in c) and "R" not in c:
        c = dict(c, R=R)
    return _E_world_of(c)


E.world_of = world_of
W.world_of = world_of


def fit(px, w, lines=(), prior=None):
    """the waterfront similarity fit with the South Bay tool's optional rotation prior: prior = [scale, sigma] or
    [scale, sigma, rotation_deg, sigma_deg] (control along one street only, or a single corner)."""
    import math
    from scipy.optimize import least_squares
    px, w = np.asarray(px, float).reshape(-1, 2), np.asarray(w, float).reshape(-1, 2)

    def resid(v):
        M = W.M_of(v)
        r = list((W.apply(M, px) - w).ravel()) if len(px) else []
        r += [float(n @ (W.apply(M, [q])[0] - p0)) for q, p0, n in lines]
        if prior:
            r.append((v[0] - prior[0]) / prior[1])
            if len(prior) >= 4:
                r.append(((math.degrees(v[1]) - prior[2] + 180) % 360 - 180) / prior[3])
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


def set_zones(key, zones):
    """after `refine`: widen block zones (pixel rectangles [x0, y0, x1, y1]) over parts of a block with no drawn
    outline (private parks, plazas, yards), so their buildings take the block's fit and count as covered."""
    f = E.CONTROL / f"{key}.json"
    cfg = json.load(open(f))
    for b in cfg["blocks"]:
        if b["name"] in zones:
            b["zone_px"] = [float(v) for v in zones[b["name"]]]
    json.dump(cfg, open(f, "w"), indent=1)


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
    """control/<city>/storeys.json {key: [[x, y, stories], ...]} (storey numbers read off the scans by eye, pixel on the
    25 % scan inside the building) -> {footprint id: stories}: the footprint containing the pixel, else the nearest
    within 25 px."""
    from shapely.geometry import Point, Polygon
    p = E.CONTROL / "storeys.json"
    out = {}
    if not p.exists():
        return out
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
                out[hit[0]] = st
            else:
                E.log(key, "storey mark not placed:", x, y, st)
    return out


# ----------------------------------------------------------------------------------------------- footprints
def extract(key):
    """colour segmentation of the building fills, as the eastbay / South Bay extract (partition-wall splitting, outline
    test, holes filled), with thresholds for these plates: the yellow frame wash is pale (saturation 60-95 on paper of
    ~12), the 'gray' iron wash is a grey-green (hue ~72, saturation 15-25, value 140-190), and the drawn lines are thin
    and light after JPEG blur (grey 100-200), so a line pixel is one 25+ levels darker than its 7-px median and below
    grey 200 (or below 110); the blue stone wash is pale on some sheets (saturation 15-30). Classes (1901-1920 keys): yellow frame, red / pink brick, blue stone, gray iron, brown
    adobe (1908) / fire-proof (1920), green specials (rare; kept as `special`)."""
    import cv2
    from shapely.geometry import Polygon
    G = json.load(open(E.INTERIM / f"{key}.M.json"))
    rgb = np.asarray(E.Image.open(G["img"]).convert("RGB"))
    hsv = cv2.cvtColor(cv2.medianBlur(rgb, 3), cv2.COLOR_RGB2HSV).astype(np.int16)
    Hh, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    del hsv
    pm = (V > np.percentile(V, 30)) & (S < np.percentile(S, 70))
    pS, pV = int(np.median(S[pm])), int(np.median(V[pm]))
    del pm
    cfg = json.load(open(E.CONTROL / f"{key}.json"))
    classes = {
        "frame": (Hh >= 17) & (Hh <= 36) & (S >= max(40, pS + 28)) & (V >= 150),
        "brick": ((Hh >= 150) | (Hh <= 7)) & (S >= 35) & (V >= 100),
        "stone": (Hh >= 85) & (Hh <= 130) & (S >= 15) & (V >= 90) & (V <= pV - 12),
        "fireproof": (Hh >= 8) & (Hh <= 16) & (S >= 70) & (V >= 80) & (V < 215),
        "iron": (S <= pS + 16) & (V >= 105) & (V <= pV - 45) & (Hh >= 25) & (Hh <= 110),
        "special": (Hh >= 40) & (Hh <= 80) & (S >= 35) & (V >= 90),
    }
    del Hh, S, V
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.int16)
    med = cv2.medianBlur(gray.astype(np.uint8), 7).astype(np.int16)
    line = ((gray < med - 25) & (gray < 200)) | (gray < 110)
    del med
    L = int(cfg.get("wall_len", 14))
    part = E.ndi.binary_opening(line, structure=np.ones((L, 1))) | E.ndi.binary_opening(line, structure=np.ones((1, L)))
    part = E.ndi.binary_dilation(part, structure=np.ones((2, 2)))
    darkd = E.ndi.binary_dilation(line | (gray < 150), iterations=3)
    del gray
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
    ndi = E.ndi
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
            if cls in ("iron", "special") and (sizes[i] < 300 or dist.max() < 5 or solid < 0.75):
                continue
            if cls == "stone" and sizes[i] > 2500 and solid < 0.6:  # a reach of creek between its drawn banks
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
            feats.append({"id": f"{key}_{cls[:2] if cls == 'special' else cls[0]}{i + 1}", "cls": cls, "zone": zone,
                          "px_centroid": [round(cx, 1), round(cy, 1)],
                          "px_ring": np.round(np.asarray(poly.exterior.coords), 1).tolist(), "area_m2": round(float(Polygon(ext, hw).area), 1),
                          "ring_utm": np.round(ext, 2).tolist(), "holes_utm": [np.round(h, 2).tolist() for h in hw]})
        del m, lab
    # one building can be caught by two classes (a yellow frame wing beside a grey iron shed overlapping at the wall):
    # drop the smaller of two footprints overlapping by more than half
    from shapely.strtree import STRtree
    pg = [Polygon(f["px_ring"]).buffer(0) for f in feats]
    tree = STRtree(pg) if pg else None
    drop = set()
    for i in sorted(range(len(feats)), key=lambda i: -pg[i].area):
        if i in drop:
            continue
        for j in tree.query(pg[i]):
            if j != i and j not in drop and pg[j].area <= pg[i].area and pg[i].intersection(pg[j]).area > 0.5 * pg[j].area:
                drop.add(j)
    feats = [f for k, f in enumerate(feats) if k not in drop]
    json.dump(feats, open(E.INTERIM / f"{key}.json", "w"))
    E.log(key, len(feats), "footprints", {c: sum(f["cls"] == c for f in feats) for c in classes})


# ----------------------------------------------------------------------------------------------- outputs
def assemble():
    """the eastbay assemble (block zones as coverage, overlap between sheets, confidence by fit) with the town's plate
    scale for 2-corner fits, the small-town storey defaults and storeys read off the sheets (storeys.json)."""
    import math
    import shapely
    from pyproj import Transformer
    from shapely import make_valid
    from shapely.geometry import Point, Polygon, mapping
    from shapely.ops import unary_union
    from shapely.strtree import STRtree
    to_ll = Transformer.from_crs(32610, 4326, always_xy=True)

    def lonlat(g):
        return shapely.transform(g, lambda c: np.column_stack(to_ll.transform(c[:, 0], c[:, 1])))
    c = CITIES[CITY_NAME]
    plate = c.get("plate_scale", 0.2060)
    storeys = storeys_to_attributes()
    attrs = {}
    labels = json.load(open(E.CONTROL / "labels.json")) if (E.CONTROL / "labels.json").exists() else {}
    for key, labs in labels.items():
        if not (E.INTERIM / f"{key}.json").exists():
            continue
        rows = json.load(open(E.INTERIM / f"{key}.json"))
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
                E.log(key, "label not placed:", name)
    fp = E.modern_footprints()
    fpg = list(fp.geometry.values)
    tree = STRtree(fpg)

    def overlap(g):
        parts = [fpg[i].intersection(g) for i in tree.query(g) if fpg[i].intersects(g)]
        return round(float(unary_union(parts).area / g.area), 2) if parts and g.area > 0 else 0.0
    rank = {"high": 0, "medium": 1, "low": 2}

    def conf_of(f):
        if f.get("n", 0) >= 4 and f.get("rms", 9) <= 1.5 and f.get("max", 9) <= 3:
            q = "high"
        elif f.get("n", 0) >= 3 and f.get("rms", 9) <= 3:
            q = "medium"
        elif f.get("n", 0) == 2 and "M" in f and abs(math.hypot(f["M"][0][0], f["M"][1][0]) - plate) <= 0.015 * plate:
            q = "medium"  # two corners: exact fit, checked only by the plate scale
        else:
            q = "low"
        if q == "high" and f.get("collinear"):
            q = "medium"
        return q
    covers = {}
    for (area, year), keys in sorted(E.AREAS.items()):
        feats, cover = [], []
        for key in keys:
            vol, sheet = key.split("_")
            cfg = json.load(open(E.CONTROL / f"{key}.json"))
            G = json.load(open(E.INTERIM / f"{key}.M.json"))
            map_year, vlabel = E.VOLUMES[vol]
            rec = W.sheet_rec(key)
            rows = json.load(open(E.INTERIM / f"{key}.json"))
            blocks = {b["name"]: b for b in G.get("blocks", [])}
            bpolys = E.block_polys(G)
            cv = unary_union([pg.buffer(12, join_style=2) for _, pg in bpolys]).buffer(15, join_style=2).buffer(-15, join_style=2)
            if cfg.get("cover_extra_px"):  # parts of a block zone with no drawn outline (plazas, yards) - pixel polygons
                for name, ring in cfg["cover_extra_px"]:
                    cv = cv.union(Polygon(W.apply(np.array(blocks[name]["M"]), ring)))
            cover.append(cv)
            res_blocks = set(cfg.get("residential_blocks", []))
            com_blocks = set(cfg.get("commercial_blocks", []))
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
                residential = zone in res_blocks or (bool(cfg.get("residential")) and zone not in com_blocks)
                fitq = dict(blocks[zone] if zone in blocks else {"rms": G.get("rms", 9), "n": G.get("n", 0), "max": G.get("max", 9)})
                if zone in blocks:
                    fitq["collinear"] = E.collinear([W.apply(np.array(blocks[zone]["M"]), [q["px"]])[0] for q in blocks[zone].get("points", [])])
                cls, a = r["cls"], r["area_m2"]
                att = attrs.get(r["id"], {})
                if att.get("drop"):
                    continue
                material = {"frame": "frame", "brick": "brick", "stone": "stone", "iron": "iron", "special": "unknown",
                            "fireproof": "adobe" if map_year < 1915 else "concrete"}[cls]
                # storeys not read: small-town defaults (rule documented in the README)
                if cls == "frame":
                    if a < 30:
                        st, us = 1, "shed"
                    elif residential:
                        st, us = (1, "dwelling") if a < 110 else (2, "dwelling") if a <= 300 else (1, "warehouse")
                    else:
                        st, us = (1, "store") if a < 150 else (2, "store") if a < 400 else (1, "warehouse")
                elif cls == "iron":
                    st, us = 1, "shed"
                elif cls == "special":
                    st, us = 1, "other"
                else:
                    st, us = (1, "warehouse") if residential else (2, "store")
                rule = "default (rule: material, size, district)"
                if r["id"] in storeys:
                    stories, ssrc = storeys[r["id"]], "map (read from the sheet)"
                else:
                    stories, ssrc = st, rule
                use, usrc = (att["use"], "map (label)") if att.get("use") else (us, "default")
                conf = conf_of(fitq)
                if cfg.get("confidence_cap") and rank[conf] < rank[cfg["confidence_cap"]]:
                    conf = cfg["confidence_cap"]
                if G.get("zones_only") and zone == "sheet":
                    conf = "low"
                feats.append((g, {"id": r["id"], "map_year": map_year, "volume": f"sanborn{E.CITY}_{vol}", "volume_label": vlabel,
                                  "sheet": rec["id"], "sheet_no": int(sheet[:4].lstrip("0") or 0), "loc_url": f"https://www.loc.gov/item/sanborn{E.CITY}_{vol}/",
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
            out = json.loads(json.dumps(gj), parse_float=lambda s_: round(float(s_), 7))
            g2 = shape(out)
            if g2.geom_type in ("Polygon", "MultiPolygon") and not g2.is_valid:
                g2 = shapely.set_precision(shape(gj), 1e-7)
                if out["type"] == "Polygon" and g2.geom_type == "MultiPolygon":
                    g2 = max(g2.geoms, key=lambda q: q.area)
                out = json.loads(json.dumps(mapping(g2)), parse_float=lambda s_: round(float(s_), 7))
            return out
        cu = unary_union(cover)
        crs = {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}
        fc = {"type": "FeatureCollection", "name": f"{area}_{year}", "crs": crs,
              "features": [{"type": "Feature", "properties": feats[i][1], "geometry": rnd(mapping(lonlat(feats[i][0])))}
                           for i in sorted(kept, key=lambda i: feats[i][1]["id"])]}
        json.dump(fc, open(E.OUT / f"{area}_{year}.geojson", "w"))
        covers.setdefault(area, []).append({"type": "Feature", "properties": {"area": area, "map_year": year, "sheets": keys, "features": len(kept)},
                                            "geometry": rnd(mapping(lonlat(cu)))})
        E.log(area, year, len(kept), "features")
    for area, fs in covers.items():
        json.dump({"type": "FeatureCollection", "name": f"{area}_coverage", "features": sorted(fs, key=lambda f: f["properties"]["map_year"])},
                  open(E.OUT / f"{area}_coverage.geojson", "w"))


def check(out=None):
    """validation of the town's outputs: valid geometries, every footprint inside its year's coverage, map years, and
    a check PNG (scratch) of the traced footprints (by map year) over today's Overture footprints."""
    import geopandas as gpd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    area = sorted({a for a, _ in E.AREAS})
    fp = E.modern_footprints()
    fig, axes = plt.subplots(1, len({y for _, y in E.AREAS}), figsize=(9 * len({y for _, y in E.AREAS}), 10))
    axes = np.atleast_1d(axes)
    report = []
    for a in area:
        cov = gpd.read_file(E.OUT / f"{a}_coverage.geojson").to_crs(32610)
        for ax, ((aa, y), _) in zip(axes, sorted((k, v) for k, v in E.AREAS.items() if k[0] == a)):
            g = gpd.read_file(E.OUT / f"{a}_{y}.geojson").to_crs(32610)
            cv = cov[cov.map_year == y].geometry.union_all()
            inside = g.geometry.within(cv.buffer(0.5))
            report.append(f"{a} {y}: {len(g)} footprints, valid {bool(g.geometry.is_valid.all())}, inside coverage "
                          f"{int(inside.sum())}/{len(g)}, map_year {sorted(g.map_year.unique())}, confidence "
                          f"{g.confidence.value_counts().to_dict()}")
            x0, y0, x1, y1 = cv.bounds
            fp.cx[x0 - 30:x1 + 30, y0 - 30:y1 + 30].plot(ax=ax, color="#bbbbbb", edgecolor="none")
            col = {"frame": "#e8a33c", "brick": "#c0392b", "stone": "#2e6fd1", "concrete": "#2e6fd1", "iron": "#555555",
                   "adobe": "#8b5a2b", "unknown": "#2a9d4b"}
            g.plot(ax=ax, color=[col.get(m, "#999999") for m in g.material], alpha=0.75, edgecolor="#222222", linewidth=0.3)
            gpd.GeoSeries([cv], crs=32610).boundary.plot(ax=ax, color="#2a9d4b", linewidth=1)
            ax.set_xlim(x0 - 30, x1 + 30); ax.set_ylim(y0 - 30, y1 + 30)
            ax.set_title(f"{a} {y}: {len(g)} traced footprints (colour = material) over today's buildings (grey)")
            ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    E.SCRATCH.mkdir(parents=True, exist_ok=True)
    out = out or E.SCRATCH / f"{CITY_NAME}_check.png"
    fig.tight_layout(); fig.savefig(out, dpi=110); plt.close(fig)
    for r in report:
        E.log(r)
    return out


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
            extract(k)
    if stage == "overlay":
        for k in keys:
            print(E.overlay(k, scale=float(os.environ.get("SCALE", 0.5))))
    if stage in ("all", "assemble"):
        assemble()
    if stage in ("all", "check"):
        print(check())


if __name__ == "__main__":
    main()
