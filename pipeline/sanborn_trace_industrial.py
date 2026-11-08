"""Trace historical industrial buildings and railway tracks for San Francisco from Library of Congress Sanborn maps.

Areas (data/manual/sanborn/README_industrial.md):
  soma_industrial    South of Market warehouses / factories (Folsom -> Townsend, 2nd -> 7th St and the waterfront) and the
                     old Produce (Commission) Market around Washington / Davis / Front St
  butchertown        Islais Creek, Butchertown slaughterhouses, India Basin, Bayview industrial strip
  north_waterfront   Embarcadero bulkhead buildings / North Beach industrial strip east of the Fisherman's Wharf tracing
  hunters_point      Hunters Point dry docks / shipyard

This is an extension of pipeline/sanborn_trace_waterfront.py and reuses its georeferencing, SIFT registration, colour
segmentation and wharf flood fill unchanged; only the sheet lists, the control folder, the attributes, the clipping
against the areas already traced, and the railway tracks are new.

Inputs (committed, hand-measured):  data/manual/sanborn/control/industrial/<key>.json   (control / registration)
                                    <key>.tracks.json  (railway centrelines, pixel polylines on the 25 % image)
                                    <key>.wharves.json (deck seeds / clip polygons), attributes.json (storeys, use, names)
Downloads (cached, gitignored):     data/raw/sanborn_loc/ (shared with the waterfront tool; index_industrial.json)
Intermediates:                      data/interim/sanborn_industrial/
Outputs:                            data/manual/sanborn/<area>_<year>.geojson, <area>_<year>_tracks.geojson,
                                    <area>_coverage.geojson

Usage:  python pipeline/sanborn_trace_industrial.py all              # fetch + georef + extract + assemble
        python pipeline/sanborn_trace_industrial.py georef 016_0137  # one stage, some sheets
        python pipeline/sanborn_trace_industrial.py register 031_0137 016_0137
        python pipeline/sanborn_trace_industrial.py fetch 016_0137   # just download (25 %)
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import sanborn_trace_waterfront as W  # noqa: E402

RAW = W.RAW
INTERIM = ROOT / "data/interim/sanborn_industrial"
CONTROL = ROOT / "data/manual/sanborn/control/industrial"
OUT = ROOT / "data/manual/sanborn"
W.INTERIM = INTERIM  # the waterfront stages read / write through these module globals
W.CONTROL = CONTROL

VOLUMES = {  # LOC item suffix (sanborn00813_<sfx>) -> (map year, label)
    "008": (1899, "1899 Vol. 1"), "009": (1899, "1899 Vol. 2"), "010": (1899, "1899 Vol. 3"), "011": (1899, "1899 Vol. 4"),
    "012": (1900, "1900 Vol. 5"), "013": (1900, "1900 Vol. 6"),
    "015": (1913, "1913 Vol. 1"), "016": (1913, "1913 Vol. 2"), "017": (1913, "1913 Vol. 3"), "018": (1913, "1913 Vol. 4"),
    "019": (1914, "1914 Vol. 5"), "020": (1914, "1914 Vol. 6"), "021": (1914, "1914 Vol. 7"), "022": (1914, "1914 Vol. 8"),
    "023": (1915, "1915 Vol. 9"), "024": (1915, "1915 Vol. 10"),
    "030": (1950, "1913-1950 Vol. 1 (corrected to 1950)"), "031": (1950, "1913-Sep 1950 Vol. 2 (corrected)"),
    "032": (1950, "1913-1950 Vol. 3 (corrected)"), "033": (1950, "1913-1950 Vol. 4 (corrected)"),
    "034": (1950, "1914-1950 Vol. 5 (corrected)"), "035": (1950, "1914-Dec 1950 Vol. 6 (corrected)"),
    "036": (1950, "1914-1950 Vol. 7 (corrected)"), "037": (1950, "1914-1950 Vol. 8 (corrected)"),
    "038": (1950, "1915-1950 Vol. 9 (corrected)"),
}
AREAS: dict[tuple[str, int], list[str]] = {}   # filled from control/industrial/areas.json
# areas already traced by other tools: their coverage is cut out of ours (no double buildings)
EXCLUDE = ["fishermans_wharf", "mission_bay", "western_addition", "potrero_point", "dogpatch", "potrero"]


def log(*a):
    print("sanborn_industrial:", *a, flush=True)


def load_areas():
    p = CONTROL / "areas.json"
    if p.exists():
        for k, v in json.load(open(p)).items():
            a, y = k.rsplit("_", 1)
            AREAS[(a, int(y))] = v
    return AREAS


# ----------------------------------------------------------------------------------------------- LOC index
def index():
    """{vol: [{id, info, w, h}]} for all SF volumes, cached in data/raw/sanborn_loc/index_industrial.json."""
    p = RAW / "index_industrial.json"
    idx = json.load(open(p)) if p.exists() else {}
    changed = False
    for vol in VOLUMES:
        if vol in idx:
            continue
        f = RAW / f"item_{vol}.json"
        for k in range(5):
            try:
                W.curl(f"https://www.loc.gov/item/sanborn00813_{vol}/?fo=json", f, 20000)
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
    out = W.image(key, pct)
    time.sleep(0.5)
    return out


def sheet_ids(vol):
    return [s["id"] for s in index()[vol]]


# ----------------------------------------------------------------------------------------------- control geometry
def line_of(street, near, R=300):
    """straight-line fit (point, unit dir with dir_x >= 0) of a DataSF centreline within R m of `near`
    (a cross-street name, or a UTM point)."""
    p = W.xing(street, near)[0] if isinstance(near, str) else np.asarray(near, float)
    p0, d = W.street_line(street, p, R)
    if d[0] < -1e-9 or (abs(d[0]) <= 1e-9 and d[1] < 0):
        d = -d
    return p0, d


def line_x(L1, L2):
    A = np.array([L1[1], -L2[1]]).T
    t = np.linalg.solve(A, L2[0] - L1[0])
    return L1[0] + t[0] * L1[1]


_world_of = W.world_of


def world_of(c):
    """control entry -> UTM point; adds to the waterfront tool's entries:
    bcx: block corner where today's streets no longer meet (a street was closed, built over or realigned): both street
         centrelines are fitted as straight lines near the given points, intersected, and offset by half of each
         street's width; sa / sb = side of the block along street a / b (+1 = direction with positive x).
    xl:  street crossing from the same two line fits (centre of the corridor)."""
    if "bcx" in c:
        a, na, b, nb = c["bcx"]
        L1, L2 = line_of(a, na, c.get("R", 300)), line_of(b, nb, c.get("R", 300))
        X = line_x(L1, L2)
        return (X + c["sa"] * (c["wb"] * W.FT / 2) * L1[1] + c["sb"] * (c["wa"] * W.FT / 2) * L2[1],
                c.get("label", f"corner of {a} x {b} (centrelines extended)"))
    if "xl" in c:
        a, na, b, nb = c["xl"]
        return line_x(line_of(a, na, c.get("R", 300)), line_of(b, nb, c.get("R", 300))), c.get("label", f"{a} x {b} (centrelines extended)")
    return _world_of(c)


W.world_of = world_of


# ----------------------------------------------------------------------------------------------- footprints
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


# ----------------------------------------------------------------------------------------------- tracks

def dark_fraction(img, px, r=2):
    """share of samples (every 3 px) along a pixel polyline that have a dark (drawn) pixel within r px."""
    g = np.asarray(Image.open(img).convert("L"), dtype=float)
    D = ndi.minimum_filter(g, size=2 * r + 1) < min(120, np.median(g) - 50)
    px = np.asarray(px, float)
    pts = []
    for a, b in zip(px[:-1], px[1:]):
        pts += [a + t * (b - a) for t in np.linspace(0, 1, max(2, int(np.hypot(*(b - a)) / 3)))]
    pts = np.array(pts).round().astype(int)
    pts = pts[(pts[:, 0] >= 0) & (pts[:, 1] >= 0) & (pts[:, 0] < D.shape[1]) & (pts[:, 1] < D.shape[0])]
    return float(D[pts[:, 1], pts[:, 0]].mean()) if len(pts) else 0.0


def snap_line(img, px, reach=8, step=20):
    """move a hand-traced polyline onto the nearest drawn line: vertices every `step` px, each shifted along the normal
    to the closest dark ridge (profile averaged +-6 px along the track, so the cross-ticks of the railway symbol do not
    count) within `reach` px; the offsets are median-smoothed. Returns (polyline, share of vertices that found a line)."""
    g = np.asarray(Image.open(img).convert("L"), dtype=float)
    thr = np.median(g) - 35
    px = np.asarray(px, float)
    pts = [px[0]]
    for a, b in zip(px[:-1], px[1:]):
        n = max(1, int(np.hypot(*(b - a)) / step))
        pts += [a + t * (b - a) for t in np.linspace(0, 1, n + 1)[1:]]
    pts = np.array(pts)

    def normal(i):
        d = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        d = d / (np.hypot(*d) or 1)
        return d, np.array([-d[1], d[0]])
    offs = []
    os_ = np.arange(-reach, reach + 0.01, 0.5)
    for i, p in enumerate(pts):
        d, nrm = normal(i)
        prof = np.array([ndi.map_coordinates(g, [(q := p + o * nrm + np.outer(np.arange(-6, 7), d))[:, 1], q[:, 0]], order=1, mode="nearest").mean()
                         for o in os_])
        mins = [j for j in range(1, len(prof) - 1) if prof[j] <= prof[j - 1] and prof[j] <= prof[j + 1] and prof[j] < thr]
        offs.append(os_[min(mins, key=lambda j: abs(os_[j]))] if mins else np.nan)
    offs = np.array(offs)
    good = ~np.isnan(offs)
    if not good.any():
        return px, 0.0
    idx = np.arange(len(offs))
    offs = ndi.median_filter(np.interp(idx, idx[good], offs[good]), size=3, mode="nearest")
    return np.array([p + offs[i] * normal(i)[1] for i, p in enumerate(pts)]), float(good.mean())


def snap_tracks(key):
    """refine control/<key>.tracks.json in place (keeps the hand trace as px_hand); run once per new sheet."""
    f = CONTROL / f"{key}.tracks.json"
    img = image(key)
    tr = json.load(open(f))
    for t in tr:
        if "px_hand" in t:
            continue
        f0 = dark_fraction(img, t["px"])
        sp, found = snap_line(img, t["px"])
        f1 = dark_fraction(img, sp)
        if f1 > f0:
            t["px_hand"], t["px"], t["snapped"] = t["px"], sp.round(1).tolist(), round(found, 2)
        log(key, "track", f"{f0:.2f} -> {f1:.2f}")
    json.dump(tr, open(f, "w"), indent=0)


def carry_tracks(src, dst, keep=0.7):
    """1913/14 centrelines of base sheet `src` moved onto its 1950 sheet `dst` (inverse SIFT registration); those still
    drawn there (dark-line test >= keep) become dst's tracks. Tracks added or changed by 1950 must be traced separately
    (control/<dst>.tracks.json entries with "own": 1 are kept)."""
    T = np.array(json.load(open(CONTROL / f"{dst}.json"))["T"])
    Ti = np.linalg.inv(np.vstack([T, [0, 0, 1]]))[:2]
    img = image(dst)
    f = CONTROL / f"{dst}.tracks.json"
    own = [t for t in json.load(open(f)) if t.get("own")] if f.exists() else []
    out = []
    for t in json.load(open(CONTROL / f"{src}.tracks.json")):
        px = np.asarray(t["px"], float) @ Ti[:, :2].T + Ti[:, 2]
        sp = snap_line(img, px, reach=5)[0]  # registration (~1.5 px) and paste-over shifts
        px = sp if dark_fraction(img, sp) > dark_fraction(img, px) else px
        fr = dark_fraction(img, px)
        if fr >= keep:
            out.append({k: v for k, v in t.items() if k not in ("px_hand", "snapped")} | {"px": px.round(1).tolist(), "carried_from": src})
    if out or own:
        json.dump(own + out, open(f, "w"), indent=0)
    log(dst, "tracks carried from", src, len(out), "kept,", len(own), "own")


def tracks(key):
    """railway centrelines hand-traced on the 25 % image (control/industrial/<key>.tracks.json) -> UTM polylines."""
    f = CONTROL / f"{key}.tracks.json"
    if not f.exists():
        return
    G = json.load(open(INTERIM / f"{key}.M.json"))
    M = np.array(G["M"])
    blocks = G.get("blocks", [])
    out = []
    zones_only = G.get("zones_only", False)

    def dist(b, q):
        x0, y0, x1, y1 = b["rect_px"]
        return max(x0 - q[0], 0, q[0] - x1) + max(y0 - q[1], 0, q[1] - y1)
    for k, t in enumerate(json.load(open(f))):
        px = np.asarray(t["px"], float)
        if t.get("block"):
            b = [b for b in blocks if b["name"] == t["block"]][0]
            utm, zone, outside = W.apply(np.array(b["M"]), px), b["name"], 0.0
        elif blocks:
            # block-wise sheets: each vertex (densified to 10 px) takes the transform of the nearest block zone, so a
            # line keeps to the blocks beside it even where the map draws the street between them too wide
            dense = [px[0]]
            for a, c in zip(px[:-1], px[1:]):
                n = max(1, int(np.hypot(*(c - a)) / 10))
                dense += [a + u * (c - a) for u in np.linspace(0, 1, n + 1)[1:]]
            dense = np.array(dense)
            near = [min(blocks, key=lambda b: dist(b, q)) for q in dense]
            utm = np.array([W.apply(np.array(b["M"]), [q])[0] for b, q in zip(near, dense)])
            names = [b["name"] for b in near]
            zone = max(set(names), key=names.count)
            outside = float(np.mean([dist(b, q) > 40 for b, q in zip(near, dense)]))
            if not zones_only:
                utm = W.apply(M, dense)
                zone, outside = "sheet", 0.0
            px = dense
        else:
            utm, zone, outside = W.apply(M, px), "sheet", 0.0
        out.append({"id": f"{key}_t{k + 1}", "kind": t.get("kind", "spur"), "railroad": t.get("railroad"), "note": t.get("note"),
                    "confidence": t.get("confidence"), "zone": zone, "px": np.round(px, 1).tolist(), "utm": np.round(utm, 2).tolist(),
                    "outside_zones": round(outside, 2), "line_test": round(dark_fraction(G["img"], t["px"]), 2),
                    "carried_from": t.get("carried_from")})
    json.dump(out, open(INTERIM / f"{key}.tracks.json", "w"))
    log(key, len(out), "track lines")


# ----------------------------------------------------------------------------------------------- outputs
def assemble(areas=None):
    import glob
    import geopandas as gpd
    import pandas as pd
    import shapely
    from pyproj import Transformer
    from shapely import make_valid
    from shapely.geometry import LineString, Polygon, mapping
    from shapely.ops import unary_union
    from shapely.strtree import STRtree
    to_ll = Transformer.from_crs(32610, 4326, always_xy=True)

    def lonlat(g):
        return shapely.transform(g, lambda c: np.column_stack(to_ll.transform(c[:, 0], c[:, 1])))
    attrs = json.load(open(CONTROL / "attributes.json")) if (CONTROL / "attributes.json").exists() else {}
    fp = gpd.GeoDataFrame(pd.concat([gpd.read_file(p) for p in sorted(glob.glob(str(ROOT / "data/raw/sf_footprints/page-*.geojson")))]), crs=4326).to_crs(32610)
    fpg = list(fp.geometry.values)
    tree = STRtree(fpg)

    def overlap(g):
        parts = [fpg[i].intersection(g) for i in tree.query(g) if fpg[i].intersects(g)]
        return round(float(unary_union(parts).area / g.area), 2) if parts and g.area > 0 else 0.0

    # coverage of other traced areas, per map decade (1899/1900, 1913/14/15, 1950): cut out of ours
    others = {}
    for name in EXCLUDE:
        f = OUT / f"{name}_coverage.geojson"
        if not f.exists():
            continue
        cg = gpd.read_file(f).to_crs(32610)
        for _, r in cg.iterrows():
            y = int(r.get("map_year") or r.get("year") or 0)
            others.setdefault(edition(y), []).append(r.geometry)
    others = {k: unary_union(v) for k, v in others.items()}

    def conf_of(f):
        if f.get("n", 0) >= 4 and f.get("rms", 9) <= 1.5 and f.get("max", 9) <= 3:
            return "high"
        if f.get("n", 0) == 2 and "M" in f:
            # two corners on one street line (the other side of the zone has no surviving street): exact fit, checked
            # only by the scale between the two corners against the 50 ft = 1 in plate scale (0.2025 m/px +- 1 %)
            sc = math.hypot(f["M"][0][0], f["M"][1][0])
            return "medium" if abs(sc - 0.2025) <= 0.002 else "low"
        return "medium" if f.get("n", 0) >= 3 and f.get("rms", 9) <= 3 else "low"
    covers = {}
    for (area, year), keys in sorted(AREAS.items()):
        if areas and area not in areas:
            continue
        feats, cover, lines = [], [], []
        excl = others.get(edition(year))
        for key in keys:
            vol, sheet = key.split("_")
            cfg = json.load(open(CONTROL / f"{key}.json"))
            base = json.load(open(CONTROL / f"{cfg['registered_to']}.json")) if "registered_to" in cfg else cfg
            G = json.load(open(INTERIM / f"{key}.M.json"))
            map_year, vlabel = VOLUMES[vol]
            rec = W.sheet_rec(key)
            rows = json.load(open(INTERIM / f"{key}.json"))
            if (INTERIM / f"{key}.manual.json").exists():
                rows += json.load(open(INTERIM / f"{key}.manual.json"))
            blocks = {b["name"]: b for b in G.get("blocks", [])}
            bblocks = {b["name"]: b for b in json.load(open(INTERIM / f"{G['registered_to']}.M.json")).get("blocks", [])} if "registered_to" in G else blocks
            W_, H_ = Image.open(G["img"]).size
            # the part of the sheet that belongs to this area: valid_poly (world, from the base sheet's pixel polygon)
            if G.get("zones_only"):
                cv = unary_union([Polygon(W.apply(np.array(b["M"]), [[b["rect_px"][0], b["rect_px"][1]], [b["rect_px"][2], b["rect_px"][1]],
                                                                    [b["rect_px"][2], b["rect_px"][3]], [b["rect_px"][0], b["rect_px"][3]]]))
                                  for b in G["blocks"]])
            else:
                x0, y0, x1, y1 = G.get("valid_px") or [30, 30, W_ - 30, H_ - 30]
                x0, y0, x1, y1 = max(x0, 30), max(y0, 30), min(x1, W_ - 30), min(y1, H_ - 30)
                cv = Polygon(W.apply(np.array(G["M"]), [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]))
            if base.get("valid_poly_px"):
                Mb = np.array(json.load(open(INTERIM / f"{cfg.get('registered_to', key)}.M.json"))["M"])
                cv = cv.intersection(Polygon(W.apply(Mb, base["valid_poly_px"])))
            if excl is not None:
                cv = cv.difference(excl)
            cover.append(cv)
            residential = bool(base.get("residential"))
            for r in rows:
                g = make_valid(Polygon(r["ring_utm"], r.get("holes_utm") or []))
                if g.geom_type != "Polygon":
                    polys = [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]
                    if not polys:
                        continue
                    g = max(polys, key=lambda p: p.area)
                if g.area < 6 or not cv.contains(g.representative_point()):
                    continue
                zone = r.get("zone", "sheet")
                fitq = dict(blocks[zone] if zone in blocks else {"rms": G.get("rms", 9), "n": G.get("n", 0), "max": G.get("max", 9)})
                if zone in bblocks:
                    fitq["M"] = bblocks[zone]["M"]  # scale check on the base plate's own fit
                if "registered_to" in G:
                    fitq["rms"] = math.hypot(fitq.get("rms", 0), G.get("reg_rms_m", 0.3))
                cls, a = r["cls"], r["area_m2"]
                att = attrs.get(r["id"], {})
                if att.get("drop"):
                    continue
                if cls == "wharf":
                    material, use, stories, ssrc, usrc = "frame", att.get("use", "wharf"), 0, "deck (no storeys)", "map"
                else:
                    material = {"frame": "frame", "brick": "brick", "stone": "concrete" if map_year >= 1950 else "stone",
                                "fireproof": "unknown" if map_year < 1900 else "concrete", "iron": "iron"}[cls]
                    if cls == "frame":
                        st, us = ((1, "shed") if a < 30 else (2, "dwelling") if residential and a <= 300
                                  else (1, "warehouse") if a >= 300 else (1, "shed") if not residential else (2, "dwelling"))
                    else:
                        st, us = (1, "shed") if cls == "iron" else (2, "warehouse")
                    rule = "default (rule: material, size, district)"
                    if att and att.get("src") != "default" and "stories" in att:
                        stories, use, ssrc, usrc = att["stories"], att.get("use", us), "map (read from the sheet)", "map (label)" if att.get("use") else "default"
                    elif att:
                        stories, use, ssrc, usrc = att.get("stories", st), att.get("use", us), rule, "map (label)" if att.get("use") else "default"
                    else:
                        stories, use, ssrc, usrc = st, us, rule, "default"
                    material = att.get("material", material)
                conf = conf_of(fitq)
                if r.get("confidence") == "low" or (G.get("zones_only") and zone == "sheet") or (map_year < 1900 and cls == "fireproof"):
                    conf = "low"
                if base.get("confidence_cap") == "medium" and conf == "high":
                    conf = "medium"
                if base.get("confidence_cap") == "low":
                    conf = "low"
                feats.append((g, {"id": r["id"], "map_year": map_year, "volume": f"sanborn00813_{vol}", "volume_label": vlabel,
                                  "sheet": rec["id"], "sheet_no": int(sheet.lstrip("0") or 0), "loc_url": f"https://www.loc.gov/item/sanborn00813_{vol}/",
                                  "iiif": rec["info"].replace("/info.json", ""), "stories": stories, "stories_source": ssrc, "material": material,
                                  "use": use, "use_source": usrc, "name": att.get("name") or r.get("name") or None, "sanborn_colour": cls,
                                  "confidence": conf, "georef": f"block {zone}" if zone in blocks else "sheet",
                                  "georef_rms_m": round(float(fitq.get("rms", 0)), 2), "extraction": r.get("method", "colour class"),
                                  "area_m2": round(float(g.area), 1), "modern_overlap": overlap(g)}))
            if (INTERIM / f"{key}.tracks.json").exists():
                for t in json.load(open(INTERIM / f"{key}.tracks.json")):
                    ln = LineString(t["utm"])
                    fitq = blocks.get(t["zone"]) or {"rms": G.get("rms", 9), "n": G.get("n", 0), "max": G.get("max", 9)}
                    if "registered_to" in G:
                        fitq = dict(fitq, rms=math.hypot(fitq.get("rms", 0), G.get("reg_rms_m", 0.3)))
                    # hand-traced centrelines: never better than "medium" (+-1-3 m across the track on the 25 % image)
                    conf = max([t.get("confidence") or "medium", conf_of(fitq)], key={"high": 0, "medium": 1, "low": 2}.get)
                    # dark-line test on the sheet: < 0.45 of the centreline on a drawn line = not verifiable, dropped;
                    # 0.45-0.7 (gaps for lettering, crossings, faint lines) = low
                    if t["line_test"] < 0.45:
                        continue
                    if t["line_test"] < 0.7 or t.get("outside_zones", 0) > 0.5:
                        conf = "low"  # gaps in the drawn line, or mostly in a street the sheet draws wider than scale
                    if base.get("confidence_cap") == "medium" and conf == "high":
                        conf = "medium"
                    if base.get("confidence_cap") == "low":
                        conf = "low"
                    if excl is not None:
                        ln = ln.difference(excl)
                        if ln.is_empty:
                            continue
                        if ln.geom_type == "MultiLineString":
                            ln = max(ln.geoms, key=lambda q: q.length)
                    lines.append((ln, {"id": t["id"], "map_year": map_year, "volume": f"sanborn00813_{vol}", "sheet": rec["id"],
                                       "sheet_no": int(sheet.lstrip("0") or 0), "loc_url": f"https://www.loc.gov/item/sanborn00813_{vol}/",
                                       "kind": t["kind"], "railroad": t.get("railroad"), "note": t.get("note"), "confidence": conf,
                                       "georef_rms_m": round(float(fitq.get("rms", 0)), 2), "line_test": t["line_test"],
                                       "outside_zones": t.get("outside_zones", 0),
                                       "carried_from": t.get("carried_from"), "length_m": round(float(ln.length), 1)}))
        rank = {"high": 0, "medium": 1, "low": 2}
        kept = []
        for i in sorted(range(len(feats)), key=lambda i: (rank[feats[i][1]["confidence"]], -feats[i][0].area)):
            g, p = feats[i]
            if not any(feats[j][1]["sheet"] != p["sheet"] and g.intersects(feats[j][0])
                       and g.intersection(feats[j][0]).area / min(g.area, feats[j][0].area) > 0.5 for j in kept):
                kept.append(i)
        rnd = lambda gj: json.loads(json.dumps(gj), parse_float=lambda s: round(float(s), 7))
        fc = {"type": "FeatureCollection", "name": f"{area}_{year}", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
              "features": [{"type": "Feature", "properties": feats[i][1], "geometry": rnd(mapping(lonlat(feats[i][0])))}
                           for i in sorted(kept, key=lambda i: feats[i][1]["id"])]}
        json.dump(fc, open(OUT / f"{area}_{year}.geojson", "w"))
        if lines:
            tc = {"type": "FeatureCollection", "name": f"{area}_{year}_tracks", "crs": fc["crs"],
                  "features": [{"type": "Feature", "properties": p, "geometry": rnd(mapping(lonlat(g)))} for g, p in sorted(lines, key=lambda t: t[1]["id"])]}
            json.dump(tc, open(OUT / f"{area}_{year}_tracks.geojson", "w"))
        cu = unary_union(cover).buffer(20, join_style=2).buffer(-20, join_style=2)
        if excl is not None:
            cu = cu.difference(excl)
        covers.setdefault(area, []).append({"type": "Feature", "properties": {"area": area, "map_year": year, "sheets": keys, "features": len(kept),
                                                                             "track_lines": len(lines)},
                                            "geometry": rnd(mapping(lonlat(cu)))})
        log(area, year, len(kept), "features", len(lines), "track lines")
    for area, fs in covers.items():
        json.dump({"type": "FeatureCollection", "name": f"{area}_coverage", "features": sorted(fs, key=lambda f: f["properties"]["map_year"])},
                  open(OUT / f"{area}_coverage.geojson", "w"))


def edition(y):
    return 1899 if y < 1905 else 1913 if y < 1920 else 1950


def all_keys():
    return list(dict.fromkeys(k for ks in AREAS.values() for k in ks))


def base_first(keys):
    reg = [k for k in keys if "registered_to" in json.load(open(CONTROL / f"{k}.json"))]
    return [k for k in keys if k not in reg] + reg


if __name__ == "__main__":
    load_areas()
    index()
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    keys = sys.argv[2:] or all_keys()
    if stage == "register":
        W.register(sys.argv[2], sys.argv[3])
        sys.exit()
    if stage == "index":
        sys.exit()
    if stage in ("all", "fetch"):
        for k in keys:
            image(k, 25)
    if stage == "fetch50":
        for k in keys:
            image(k, 50)
    if stage in ("all", "georef"):
        for k in base_first(keys):
            W.georef(k)
    if stage in ("all", "extract"):
        for k in keys:
            W.extract(k); reclass(k)
            if k.split("_")[0] in W.EDITION_1950:
                extract_regions(k)
            W.wharves(k); tracks(k)
    if stage == "tracks":
        for k in keys:
            tracks(k)
    if stage == "snap":  # refine hand-traced track centrelines (control files, once)
        for k in keys:
            snap_tracks(k)
    if stage == "carry":  # python ... carry 016_0135 031_0135
        carry_tracks(sys.argv[2], sys.argv[3])
    if stage in ("all", "assemble"):
        assemble(sys.argv[2:] if stage == "assemble" and len(sys.argv) > 2 else None)
