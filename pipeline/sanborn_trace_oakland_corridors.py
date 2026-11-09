"""Trace the buildings that stood in Oakland's freeway rights-of-way from Library of Congress Sanborn maps.

Areas (data/manual/sanborn/README_oakland.md, section "Freeway corridors"):
  oakland_sr24    SR-24 Grove-Shafter freeway (c.1966-70): the I-980 / I-580 junction along Grove St (MLK Jr Way),
                  27th -> 40th St, then Grove St -> Shattuck Ave 40th -> 52nd St, Temescal (Shattuck / Telegraph /
                  Claremont Ave, 52nd -> 58th St) and the Rockridge stretch (Hudson / Forest / Miles Ave -> College Ave
                  -> Broadway); whole blocks the freeway cut
  oakland_i580    I-580 MacArthur freeway (c.1963-66) east of the MacArthur Maze
  oakland_i980n   I-980 north of 11th St (Brush St -> Castro St, 11th -> 27th St) beyond oakland_west / oakland_downtown

Volumes: Oakland 1911-12 vol. 1 (sanborn00727_005, West Oakland + downtown up to 38th St / Moss Ave) and vol. 3
(sanborn00727_007, North Oakland and Emeryville: 36th St -> the Berkeley line), and their corrected editions: vol. 1
1912 - Nov 1951 (_015) and vol. 3 1911 - Oct 1950 (_017), the same engraved plates with paste-over corrections,
registered onto the 1911-12 scans by SIFT as in README_oakland.md.

This module only configures pipeline/sanborn_trace_eastbay.py (block specs, `refine`, property corners from today's
parcels, offset corners, similarity fits, SIFT registration, colour segmentation with partition walls, assembly,
confidence rules) through pipeline/sanborn_trace_eastbay_cities.py (Overture roads_region + roads_local for street
lines, `cap_blocks`, `commercial_fronts`). Its own control lives in data/manual/sanborn/control/oakland_corridors/ (the
West Oakland / downtown control in control/oakland/ belongs to sanborn_trace_eastbay.py, central Oakland east of
Broadway to sanborn_trace_oakland_central.py). What is added here:
  * `predict`: a block spec from two or more street crossings read by eye: a similarity from those crossings
    (Overture centrelines) places every block corner (today's property corner, else the centreline crossing offset by
    the printed street widths) on the sheet as the estimate that `refine` snaps onto the drawn block outline;
  * `check`: the validation PNG with today's freeway (Overture motorway) lines;
  * storeys read off the sheets by eye: control/oakland_corridors/storeys.json {key: [[x, y, stories], ...]} (pixel on
    the 25 % scan inside the building; the footprint containing it, else the nearest within 25 px).

Usage:  python pipeline/sanborn_trace_oakland_corridors.py <stage> [keys]
  stages: fetch | grid <key> [x0 y0 x1 y1] | predict <key> <json> | spec <key> <json> | respec <key> [json] | refine
          | georef | register <src> <dst> | mosaic | extract | overlay | assemble | check | all
Keys are <LOC item suffix>_<sheet>: 007_0346 = sanborn00727_007 (1911-12 vol. 3, 1911) sheet 346; 017_0346 = the same
plate in the 1911 - Oct 1950 corrected vol. 3.
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
import sanborn_trace_eastbay_cities as C  # noqa: E402
import sanborn_trace_waterfront as W  # noqa: E402

NAME = "oakland_corridors"
OAK_ALIASES = dict(E.ALIASES)  # Grove St -> MLK Jr Way, Cypress St -> Mandela Pkwy, ordinal streets
C.CITIES[NAME] = {
    "loc": "00727",
    "volumes": {"005": (1912, "1911-1912 Vol. 1 (1912)"), "006": (1911, "1911 Vol. 2"), "007": (1911, "1911-1912 Vol. 3 (1911)"),
                "015": (1951, "1912-Nov 1951 Vol. 1 (corrected to Nov 1951)"),
                "016": (1950, "1911-Nov 1950 Vol. 2 (corrected to Nov 1950)"),
                "017": (1950, "1911-Oct 1950 Vol. 3 (corrected to Oct 1950)")},
    "edition_1950": ("015", "016", "017"),
    "parcels": ROOT / "data/raw/region_years/alameda_county_2021/alameda_county_2021.parquet",
    "parcel_cols": ["APN"],
    "bbox": (-122.300, 37.795, -122.195, 37.862),
    # street names on the sheets -> today's names (Overture); more in control/oakland_corridors/aliases.json
    "aliases": OAK_ALIASES | {
        "moss avenue": "macarthur boulevard", "moss": "macarthur boulevard",
        "telegraph": "telegraph avenue", "shattuck": "shattuck avenue", "claremont": "claremont avenue",
        "college": "college avenue", "broadway": "broadway", "market": "market street", "west": "west street",
    },
    "commercial_streets": {"telegraph avenue": 35, "broadway": 40, "college avenue": 30, "san pablo avenue": 35},
    "railroad_streets": [],
}
FREEWAYS = ("Grove Shafter Freeway", "MacArthur Freeway", "John B. Williams Freeway", "Nimitz Freeway")


def configure():
    c = C.configure(NAME)
    # the LOC images and item index of Oakland are shared with sanborn_trace_eastbay.py (cached by key)
    E.RAW = ROOT / "data/raw/sanborn_loc_oakland"
    W.RAW = E.RAW
    al = E.CONTROL / "aliases.json"
    if al.exists():
        E.ALIASES.update(json.load(open(al)))
    return c


# ----------------------------------------------------------------------------------------------- block estimates
def world_corner(b, cn):
    """world position of block corner cn (NW/NE/SE/SW) of block spec b: today's property corner, else the centreline
    crossing offset by the printed widths (b['w'], default 80 ft), else the bare centreline crossing."""
    sa, sb, q = E.QUAD[cn]
    a, bb = b[sa], b[sb]
    try:
        return E.property_corner(a, bb, q, b.get("near"))[0], "pc"
    except (ValueError, KeyError, np.linalg.LinAlgError):
        pass
    w = b.get("w", {})
    try:
        return E.offset_corner(a, bb, q, w.get(sa, 80), w.get(sb, 80), b.get("near"))[0], "oc"
    except (ValueError, KeyError, np.linalg.LinAlgError):
        return None, None


def predict(key, s, M=None):
    """block spec from crossings read by eye: s = {"xings": [[x, y, street a, street b(, near)], ...] (centreline
    crossings, pixels on the 25 % scan, two or more), "blocks": {name: {"N", "S", "W", "E": streets, optional "w",
    "skip", "oc", "with", "near"}}, other top-level keys as for `spec`}. The similarity crossing pixels -> Overture
    crossings (or the sheet fit M of a first pass) places each block corner on the sheet; the corners are estimates
    for `refine`. A block cut by the sheet edge keeps the part on this sheet; its corners beyond the edge are not
    control, and it is fitted with the blocks of its row / column (`with`)."""
    xs = s["xings"]
    if M is None:
        px = [(float(x[0]), float(x[1])) for x in xs]
        wo = [E.xing(x[2], x[3], x[4] if len(x) > 4 else None)[0] for x in xs]
        if len(px) >= 2:
            M, d = W.fit(px, wo, prior=(s.get("scale", 0.2015), 0.0008))
        else:  # one crossing + the sheet's rotation (deg, image x-axis vs east)
            M = W.M_of([s.get("scale", 0.2015), np.radians(s["rot"]), 0, 0])
            M[:, 2] = np.asarray(wo[0]) - W.apply(M, [px[0]])[0]
            d = np.zeros(1)
        E.log(key, "crossing fit", W.describe(M), "residuals (m):", np.round(d, 1).tolist())
        if s.get("match", True):
            M = chamfer(key, M, shift=s.get("match_shift", 60), rot_span=s.get("match_rot", 4.0))
    A = np.vstack([np.asarray(M, float), [0, 0, 1]])
    Ai = np.linalg.inv(A)
    from PIL import Image
    Wi, Hi = Image.open(E.image(key)).size
    mg = s.get("margin", 10)

    def inside(p):
        return mg <= p[0] <= Wi - mg and mg <= p[1] <= Hi - mg
    out = {k: v for k, v in s.items() if k not in ("xings", "blocks", "group", "margin", "scale", "match", "match_shift", "match_rot", "rot")}
    out["blocks"] = {}
    out["predicted_from"] = [x[:4] for x in xs]
    o = ("NW", "NE", "SE", "SW")
    est = {}
    for n, b in s["blocks"].items():
        if "px" in b:  # outline drawn by hand (irregular block, zone only): passed through
            est[n] = dict(b)
            continue
        pts, kinds = {}, {}
        for cn in o:
            p, k = world_corner(b, cn)
            if p is not None:
                pts[cn] = Ai[:2, :2] @ p + Ai[:2, 2]
                kinds[cn] = k
        missing = [cn for cn in o if cn not in pts]
        if len(missing) == 1:  # complete the parallelogram
            i = o.index(missing[0])
            pts[missing[0]] = pts[o[(i + 1) % 4]] + pts[o[(i + 3) % 4]] - pts[o[(i + 2) % 4]]
        elif missing:
            E.log(key, "block", n, "corners not found:", missing, "-> skipped")
            continue
        off = [cn for cn in o if not inside(pts[cn])]
        if len(off) > 2:
            E.log(key, "block", n, "mostly off the sheet:", off, "-> skipped")
            continue
        for cn in off:
            i = o.index(cn)
            src = next((x for x in (o[(i + 1) % 4], o[(i + 3) % 4]) if x not in off), None)
            if src is None:
                continue
            a, p = pts[src], pts[cn]
            # out to the sheet edge along the image axis nearest to the predicted direction (Sanborn sheets draw the
            # street grid square to the plate; the predicted off-sheet corner may lean where its control is weak)
            u = p - a
            dp = np.array([np.sign(u[0]), 0.0]) if abs(u[0]) >= abs(u[1]) else np.array([0.0, np.sign(u[1])])
            p = a + dp * 6000.0
            lo, hi = 0.0, 1.0
            for _ in range(40):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if inside(a + mid * (p - a)) else (lo, mid)
            pts[cn] = a + lo * (p - a)
        if s.get("square", True) and not b.get("diagonal"):
            # Sanborn sheets draw the street grid square to the plate: a side within 8 deg of an image axis is made
            # axis-parallel (today's widened streets lean the predicted sides)
            q = np.array([pts[cn] for cn in o], float)
            for _ in range(2):
                for i in range(4):
                    a_, b_ = q[i], q[(i + 1) % 4]
                    dx, dy = b_ - a_
                    ang = np.degrees(np.arctan2(abs(dy), abs(dx)))
                    if ang < 8:
                        q[i][1] = q[(i + 1) % 4][1] = (a_[1] + b_[1]) / 2
                    elif ang > 82:
                        q[i][0] = q[(i + 1) % 4][0] = (a_[0] + b_[0]) / 2
            pts = {cn: q[i] for i, cn in enumerate(o)}
        e = {k: b[k] for k in ("N", "S", "W", "E")}
        e["px"] = [[round(float(pts[cn][0]), 1), round(float(pts[cn][1]), 1)] for cn in o]
        skip = set(b.get("skip", [])) | set(missing) | set(off)
        if skip:
            e["skip"] = sorted(skip)
        for k in ("w", "oc", "with", "near", "no_refine", "control_only"):
            if k in b:
                e[k] = b[k]
        est[n] = e
        E.log(key, "block", n, {cn: kinds.get(cn, "fill") for cn in o}, e["px"], "off sheet" if off else "")
    # groups: every block is fitted with the blocks of its row (same N and S street) and column (same W and E street),
    # else with all blocks of the sheet; a block with four good corners of its own keeps its own fit (regroup)
    if s.get("group", True):
        for n, e in est.items():
            if "with" in e:
                continue
            nb = [m for m, f in est.items() if m != n and ((f["N"], f["S"]) == (e["N"], e["S"]) or (f["W"], f["E"]) == (e["W"], e["E"]))]
            e["with"] = nb or [m for m in est if m != n]
    out["blocks"] = est
    E.spec(key, out)
    mark_blocks(key, est)
    return out


def mark_blocks(key, blocks, keys=("control_only", "confidence_cap")):
    """per-block keys that E.spec does not carry into the control file (control_only, confidence_cap)."""
    f = E.CONTROL / f"{key}.json"
    cfg = json.load(open(f))
    for b in cfg["blocks"]:
        for k in keys:
            if k in blocks.get(b["name"], {}):
                b[k] = blocks[b["name"]][k]
    json.dump(cfg, open(f, "w"), indent=1)


def regroup(key, max_rms=1.0, max_scale_dev=0.025):
    """after E.refine: a block whose own (non-weak, plausible) corners number four or more and fit a similarity with
    RMS <= max_rms and a scale within max_scale_dev of the plate scale (0.2015 m/px at 25 %) keeps its own fit, even
    where it disagrees with its group (Sanborn blocks are drawn to scale, the streets between them not always)."""
    f = E.CONTROL / f"{key}.json"
    cfg = json.load(open(f))
    n = 0
    for b in cfg.get("blocks", []):
        own = [c for c in b.get("corners_all", []) if not c.get("weak") and "drop" not in c]
        if len(own) < 4 or all(c.get("block", b["name"]) == b["name"] for c in b["corners"]) and len(b["corners"]) >= 4:
            continue
        try:
            Mb, d = W.fit([(c["x"], c["y"]) for c in own], [E.world_of(c)[0] for c in own], prior=cfg.get("scale_prior"))
        except (ValueError, KeyError, np.linalg.LinAlgError):
            continue
        sc = float(np.hypot(Mb[0, 0], Mb[1, 0]))
        rms = float(np.sqrt((d ** 2).mean()))
        if rms <= max_rms and abs(sc / 0.2015 - 1) <= max_scale_dev:
            b["corners"] = [dict(c, block=b["name"]) for c in own]
            n += 1
            E.log(key, "block", b["name"], f"own fit kept (scale {sc:.4f}, RMS {rms:.2f} m)")
    json.dump(cfg, open(f, "w"), indent=1)
    return n


def setcorner(key, block, cn, x, y, regroup_after=True):
    """hand correction after `refine`: block corner cn (NW/NE/SE/SW) is at pixel (x, y) (read on a zoomed grid view):
    the control entry, the block outline (px4) and its zone move there; the corner is used even if its side was weak."""
    f = E.CONTROL / f"{key}.json"
    cfg = json.load(open(f))
    b = next(b for b in cfg["blocks"] if b["name"] == block)
    o = ("NW", "NE", "SE", "SW")
    b["px4"][o.index(cn)] = [float(x), float(y)]
    xs = [q[0] for q in b["px4"]]; ys = [q[1] for q in b["px4"]]
    b["zone_px"] = [min(xs), min(ys), max(xs), max(ys)]
    hit = False
    for c in b.get("corners_all", []):
        if c.get("corner") == cn:
            c.update(x=float(x), y=float(y), norefine=1, weak=False, hand=1)
            c.pop("drop", None)
            hit = True
    if not hit:
        raise KeyError(f"{key} block {block}: no control entry for corner {cn} (skipped or off the sheet)")
    for bb in cfg["blocks"]:  # the same corner wherever it is used (own corners and the corners of a group fit)
        bb["corners"] = [c for c in bb["corners"] if not (c.get("block", bb["name"]) == block and c.get("corner") == cn)]
    c = next(c for c in b["corners_all"] if c.get("corner") == cn)
    for bb in cfg["blocks"]:
        if bb["name"] == block or block in bb.get("with", []):
            bb["corners"].append(dict(c, block=block))
    json.dump(cfg, open(f, "w"), indent=1)


def crops(key, pts, half=70, zoom=2, step=20, out=None):
    """scratch aid for reading corners: 1:1 crops (x zoom) around the given pixels with a labelled 20 px grid."""
    from PIL import Image, ImageDraw
    im = Image.open(E.image(key)).convert("RGB")
    tiles = []
    for x, y in pts:
        x, y = int(x), int(y)
        t = im.crop((x - half, y - half, x + half, y + half)).resize((2 * half * zoom, 2 * half * zoom), Image.LANCZOS)
        d = ImageDraw.Draw(t)
        for g in range((x - half) // step * step + step, x + half, step):
            X = (g - x + half) * zoom
            d.line([(X, 0), (X, 2 * half * zoom)], fill=(0, 160, 0) if g % 100 else (220, 0, 0), width=1)
            d.text((X + 1, 1), str(g), fill=(0, 0, 200))
        for g in range((y - half) // step * step + step, y + half, step):
            Y = (g - y + half) * zoom
            d.line([(0, Y), (2 * half * zoom, Y)], fill=(0, 160, 0) if g % 100 else (220, 0, 0), width=1)
            d.text((1, Y + 1), str(g), fill=(0, 0, 200))
        tiles.append(t)
    n = len(tiles)
    cols = min(4, n)
    rows = (n + cols - 1) // cols
    s_ = 2 * half * zoom
    M = Image.new("RGB", (cols * (s_ + 4), rows * (s_ + 4)), (255, 255, 255))
    for i, t in enumerate(tiles):
        M.paste(t, ((i % cols) * (s_ + 4), (i // cols) * (s_ + 4)))
    E.SCRATCH.mkdir(parents=True, exist_ok=True)
    out = out or E.SCRATCH / f"{key}_crops.jpg"
    M.save(out, quality=88)
    return out


def chamfer(key, M0, scale=0.2015, rot_span=4.0, shift=60, out=None):
    """refine a rough similarity (image px -> UTM) by matching today's property lines (boundaries of the parcel
    blocks, sampled every 1 m) to the dark lines drawn on the sheet: minimise the mean distance (px, clipped) from the
    projected property-line points to the nearest dark pixel, over rotation, shift and scale (+-1.5 % around the plate
    scale). Coarse to fine (clip 40 -> 15 -> 6 px). Most block outlines of a residential sheet survive today as
    property lines, so the cleared blocks (freeway land) do not need to match."""
    from PIL import Image
    from scipy.optimize import minimize
    from shapely.geometry import box
    gray = np.asarray(Image.open(E.image(key)).convert("L"), dtype=float)
    H, Wd = gray.shape
    dark = gray < min(125, np.median(gray) - 55)
    dark = ndi_open_lines(dark)
    from scipy import ndimage as ndi
    dt = ndi.distance_transform_edt(~dark)
    M0 = np.asarray(M0, float)
    corners = W.apply(M0, [[0, 0], [Wd, 0], [Wd, H], [0, H]])
    x0, y0 = corners.min(axis=0) - 80; x1, y1 = corners.max(axis=0) + 80
    geoms, tree = E.parcel_blocks()
    pts = []
    for i in tree.query(box(x0, y0, x1, y1)):
        g = geoms[i]
        for ring in [g.exterior] + list(g.interiors):
            c = np.asarray(ring.coords)[:, :2]
            for a, b in zip(c[:-1], c[1:]):
                L = float(np.hypot(*(b - a)))
                for t in np.arange(0, L, 1.0):
                    pts.append(a + (b - a) * t / L)
    P = np.asarray(pts)
    s0 = math_hypot(M0[0, 0], M0[1, 0])
    th0 = np.arctan2(M0[1, 0], M0[0, 0])
    pc = np.array([Wd / 2, H / 2])
    wc = W.apply(M0, [pc])[0]

    def Mof(v):
        sc, th, dx, dy = scale * (1 + v[0]), th0 + np.radians(v[1]), v[2], v[3]
        A = W.M_of([sc, th, 0, 0])
        t = wc - W.apply(A, [pc + np.array([dx, dy])])[0]  # (dx, dy): the image point that maps to the rough centre
        A[:, 2] = t
        return A

    def score(v, clip):
        A = Mof(v)
        Ai = np.linalg.inv(np.vstack([A, [0, 0, 1]]))[:2]
        q = P @ Ai[:, :2].T + Ai[:, 2]
        m = (q[:, 0] > 8) & (q[:, 0] < Wd - 8) & (q[:, 1] > 8) & (q[:, 1] < H - 8)
        if m.sum() < 200:
            return 1e3
        d = ndi.map_coordinates(dt, [q[m, 1], q[m, 0]], order=1)
        return float(np.minimum(d, clip).mean()) + 0.0 * v[0]
    best = None
    v0 = [s0 / scale - 1 if abs(s0 / scale - 1) < 0.015 else 0.0, 0.0, 0.0, 0.0]
    for dth in np.arange(-rot_span, rot_span + 0.01, 1.0):
        for dx in range(-shift, shift + 1, 20):
            for dy in range(-shift, shift + 1, 20):
                v = [v0[0], dth, dx, dy]
                sc = score(v, 40)
                if best is None or sc < best[0]:
                    best = (sc, v)
    v = best[1]
    for clip in (40, 15, 6):
        r = minimize(lambda u: score([float(np.clip(u[0], -0.015, 0.015)), u[1], u[2], u[3]], clip), v, method="Powell",
                     options={"xtol": 1e-3, "ftol": 1e-4, "maxiter": 4000})
        v = [float(np.clip(r.x[0], -0.015, 0.015)), r.x[1], r.x[2], r.x[3]]
    A = Mof(v)
    Ai = np.linalg.inv(np.vstack([A, [0, 0, 1]]))[:2]
    q = P @ Ai[:, :2].T + Ai[:, 2]
    m = (q[:, 0] > 8) & (q[:, 0] < Wd - 8) & (q[:, 1] > 8) & (q[:, 1] < H - 8)
    dd = ndi.map_coordinates(dt, [q[m, 1], q[m, 0]], order=1)
    inl = dd <= 6
    rms_m = float(np.sqrt((dd[inl] ** 2).mean()) * np.hypot(A[0, 0], A[1, 0])) if inl.any() else 9.0
    info = {"M": A.tolist(), "dist_px": round(score(v, 6), 2), "inlier_share": round(float(inl.mean()), 2), "rms_m": round(rms_m, 2),
            "n_points": int(m.sum())}
    E.log(key, "chamfer match:", W.describe(A), f"mean line distance {info['dist_px']:.2f} px (clip 6), inliers {info['inlier_share']:.0%}",
          f"of {int(m.sum())} property-line points, inlier RMS {rms_m:.2f} m; shift from the rough fit {np.hypot(v[2], v[3]):.0f} px, rot {v[1]:+.2f} deg")
    return (A, info) if out == "info" else A


def ndi_open_lines(dark):
    """keep long thin dark structures (block / lot lines, building walls), drop lettering specks."""
    from scipy import ndimage as ndi
    h = ndi.binary_opening(dark, structure=np.ones((1, 9)))
    v = ndi.binary_opening(dark, structure=np.ones((9, 1)))
    return h | v


def math_hypot(a, b):
    return float(np.hypot(a, b))


def store_chamfer(key, starts=()):
    """chamfer match from the current sheet fit (and any other start, e.g. the match of the previous pass), the best
    one stored in the control file (`chamfer`: M, line distance, RMS)."""
    G = json.load(open(E.INTERIM / f"{key}.M.json"))
    best = None
    for M0 in [G["M"]] + [np.asarray(m).tolist() for m in starts]:
        A, info = chamfer(key, M0, shift=20, rot_span=1.0, out="info")
        if best is None or info["dist_px"] < best[1]["dist_px"]:
            best = (A, info)
    A, info = best
    f = E.CONTROL / f"{key}.json"
    cfg = json.load(open(f))
    cfg["chamfer"] = info
    json.dump(cfg, open(f, "w"), indent=1)
    return info


def apply_chamfer(key, max_rms=1.5, max_max=3.0):
    """after W.georef: (1) blocks marked control_only lose their zone; (2) every block zone is its outline (px4 of the
    control file: the refined outline, or the polygon drawn by hand), not the bounding box of it (blocks on rotated
    or diagonal streets); (3) blocks without a good corner fit (fewer than 3 control corners, RMS > max_rms or max >
    max_max: control lost to re-platted or widened streets, partial blocks on the sheet edge) take the sheet's
    chamfer match to today's property lines (`chamfer` in the control file) instead; their `georef_rms_m` is the
    match's inlier RMS (at least 1 m) and their confidence at most medium (n = 3, no collinearity test). A sheet in
    mode `chamfer_only` (hand-drawn zones, no usable corners) is placed by the chamfer match alone. Registered
    (corrected-edition) sheets inherit all of it from their base plate; their zone outlines are mapped through the
    registration."""
    cfg = json.load(open(E.CONTROL / f"{key}.json"))
    p = E.INTERIM / f"{key}.M.json"
    if "registered_to" in cfg:
        G = json.load(open(p))
        T = np.vstack([np.array(cfg["T"]), [0, 0, 1]])
        Ti = np.linalg.inv(T)[:2]
        for bl in G.get("blocks", []):
            if bl.get("px4_base"):
                q = np.asarray(bl["px4_base"], float)
                bl["px4"] = np.round(q @ Ti[:, :2].T + Ti[:, 2], 1).tolist()
        json.dump(G, open(p, "w"), indent=1)
        return 0
    if cfg.get("mode") == "chamfer_only":
        ch = cfg["chamfer"]
        from PIL import Image
        img = E.image(key)
        A = np.array(ch["M"])
        rms = max(ch["rms_m"], 1.0)
        if ch.get("inlier_share") is not None and ch["inlier_share"] < 0.45:
            rms = 3.5  # a weak match (< 45 % of today's property lines on drawn lines): low confidence
        blocks = []
        for bl in cfg["blocks"]:
            q = np.asarray(bl["px4"], float)
            blocks.append({"name": bl["name"], "M": ch["M"], "rect_px": [float(q[:, 0].min()), float(q[:, 1].min()), float(q[:, 0].max()), float(q[:, 1].max())],
                           "rms": rms, "max": 2.5 * rms, "n": 3, "points": [], "fit": "chamfer"})
        json.dump({"M": ch["M"], "pct": 25, "img": str(img), "rms": rms, "max": 2.5 * rms, "n": 3, "scale": W.describe(A), "blocks": blocks,
                   "zones_only": True, "valid_px": cfg.get("valid_px"), "valid_poly_px": cfg.get("valid_poly_px"), "tied_to": [], "tie_rms": 0.0,
                   "points": [], "chamfer": {k: v for k, v in ch.items() if k != "M"}}, open(p, "w"), indent=1)
    G = json.load(open(p))
    co = {bl["name"] for bl in cfg.get("blocks", []) if bl.get("control_only")}
    if co:
        G["blocks"] = [bl for bl in G.get("blocks", []) if bl["name"] not in co]
        G["control_only"] = sorted(co)
    outl = {bl["name"]: bl.get("px4") or bl.get("px4_est") for bl in cfg.get("blocks", [])}
    for bl in G.get("blocks", []):
        if outl.get(bl["name"]):
            bl["px4"] = bl["px4_base"] = outl[bl["name"]]
    n = 0
    ch = cfg.get("chamfer")
    if ch and cfg.get("mode") != "chamfer_only":
        good_match = (ch.get("inlier_share") or 0) >= 0.45
        for bl in G.get("blocks", []):
            sc_ok = abs(float(np.hypot(bl["M"][0][0], bl["M"][1][0])) / 0.2015 - 1) <= 0.025  # plate scale 50 ft = 1 in
            good = bl["n"] >= 3 and bl["rms"] <= max_rms and bl["max"] <= max_max and sc_ok
            fair = bl["n"] >= 3 and bl["rms"] <= 3.0 and sc_ok
            if cfg.get("chamfer_all") or (not good and (good_match or not fair)):
                # a weak match (< 45 % of today's property lines on drawn lines) is low confidence (RMS 3.5 m)
                r = max(ch["rms_m"], 1.0) if good_match else 3.5
                bl.update(M=ch["M"], rms=r, max=max(2.5 * r, 2.5), n=3, points=[], fit="chamfer",
                          corner_fit={"n": bl["n"], "rms": round(bl["rms"], 2), "max": round(bl["max"], 2)})
                n += 1
        if n:
            G["chamfer"] = {k: v for k, v in ch.items() if k != "M"}
            E.log(key, n, "blocks take the chamfer match", {k: v for k, v in ch.items() if k != "M"})
        if good_match and (G.get("rms", 9) > max_rms or G.get("max", 9) > max_max):
            # the sheet-wide fit (footprints near no block zone) likewise
            r = max(ch["rms_m"], 1.0)
            G.update(M=ch["M"], rms=r, max=2.5 * r, n=3, sheet_fit="chamfer")
    json.dump(G, open(p, "w"), indent=1)
    return n


def zones(key, s):
    """sheet in `chamfer_only` mode: s = {"xings": [[x, y, a, b], ...] (+ "rot" for a single crossing), "zones": {name:
    [[x, y], ...] polygon drawn by hand on the 25 % scan}, other keys}: the chamfer match to today's property lines places
    the sheet; the zones are the blocks."""
    xs = s["xings"]
    px = [(float(x[0]), float(x[1])) for x in xs]
    wo = [E.xing(x[2], x[3], x[4] if len(x) > 4 else None)[0] for x in xs]
    if len(px) >= 2:
        M, d = W.fit(px, wo, prior=(s.get("scale", 0.2015), 0.0008))
    else:
        M = W.M_of([s.get("scale", 0.2015), np.radians(s["rot"]), 0, 0])
        M[:, 2] = np.asarray(wo[0]) - W.apply(M, [px[0]])[0]
        d = np.zeros(1)
    E.log(key, "crossing fit", W.describe(M), "residuals (m):", np.round(d, 1).tolist())
    if s.get("match", True):
        M = chamfer(key, M, shift=s.get("match_shift", 60), rot_span=s.get("match_rot", 4.0))
        A, info = chamfer(key, M, shift=20, rot_span=1.0, out="info")
    else:  # the crossings read by eye are the control (the chamfer match fails where most property lines changed)
        rms = float(np.sqrt((d ** 2).mean()))
        info = {"M": np.asarray(M).tolist(), "dist_px": None, "inlier_share": None, "rms_m": round(max(rms, 1.5 if len(px) >= 3 else 2.5), 2),
                "n_points": 0, "from": f"{len(px)} street crossings read by eye, RMS {rms:.2f} m"}
    cfg = {k: v for k, v in s.items() if k not in ("xings", "zones", "scale", "match_shift", "match_rot", "rot", "match")}
    cfg.update(mode="chamfer_only", predicted_from=[x[:4] for x in xs], chamfer=info, pct=25,
               blocks=[{"name": n, "px4": q, "corners": []} for n, q in s["zones"].items()])
    json.dump(cfg, open(E.CONTROL / f"{key}.json", "w"), indent=1)
    apply_chamfer(key)
    report(key)


def cover_footprints():
    """the coverage of each map year also contains every traced footprint (a building drawn across the edge of a block
    zone + 12 m: its representative point decided that it was kept)."""
    import shapely
    from shapely.geometry import mapping, shape
    areas = sorted({a for a, _ in E.AREAS})
    for area in areas:
        p = E.OUT / f"{area}_coverage.geojson"
        if not p.exists():
            continue
        cov = json.load(open(p))
        for ft in cov["features"]:
            y = ft["properties"]["map_year"]
            f = E.OUT / f"{area}_{y}.geojson"
            if not f.exists():
                continue
            fps = [shape(g["geometry"]) for g in json.load(open(f))["features"]]
            g0 = shape(ft["geometry"])
            out = [q for q in fps if not g0.contains(q)]
            if not out:
                continue
            g = shapely.union_all([g0] + [q.buffer(2e-6, join_style=2) for q in out])
            g = shapely.set_precision(g, 1e-7)
            ft["geometry"] = json.loads(json.dumps(mapping(g)), parse_float=lambda v: round(float(v), 7))
            C.log(area, y, len(out), "footprints across the zone edge: coverage extended")
        json.dump(cov, open(p, "w"))


def auto(key, s):
    """two passes: predict from the crossings read by eye, refine, regroup, georef; then predict again from that
    sheet fit, refine, regroup, georef."""
    predict(key, s)
    E.refine(key, weak=s.get("weak", 0.35))
    regroup(key)
    W.georef(key)
    G = json.load(open(E.INTERIM / f"{key}.M.json"))
    M2 = chamfer(key, G["M"], shift=40, rot_span=2.0) if s.get("match", True) else np.asarray(G["M"])
    predict(key, s, M=M2)
    E.refine(key, weak=s.get("weak", 0.35))
    regroup(key)
    W.georef(key)
    store_chamfer(key, starts=[M2])
    apply_chamfer(key)
    report(key)


def report(key):
    G = json.load(open(E.INTERIM / f"{key}.M.json"))
    for b in G.get("blocks", []):
        print(f"  {key} block {b['name']:>10}: {b.get('fit', 'corners')} n={b['n']:2d} RMS {b['rms']:.2f} max {b['max']:.2f} m  "
              f"{W.describe(np.array(b['M']))}" + (f"  (corner fit {b['corner_fit']})" if "corner_fit" in b else ""))


# ----------------------------------------------------------------------------------------------- storeys
def storeys_to_attributes():
    """control/oakland_corridors/storeys.json {key: [[x, y, stories], ...]} -> {footprint id: stories}: the footprint
    containing the pixel, else the nearest within 25 px (as pipeline/sanborn_trace_peninsula.py)."""
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
                C.log(key, "storey mark not placed:", x, y, st)
    return out


def apply_storeys():
    """storeys read off the sheets replace the default rule in the assembled files; a building read at 3+ storeys that
    the rule called a dwelling is called flats."""
    st = storeys_to_attributes()
    if not st:
        return
    for (area, year) in E.AREAS:
        p = E.OUT / f"{area}_{year}.geojson"
        if not p.exists():
            continue
        fc = json.load(open(p))
        n = 0
        for ft in fc["features"]:
            pr = ft["properties"]
            if pr["id"] in st:
                pr["stories"], pr["stories_source"] = st[pr["id"]], "map (read from the sheet)"
                if pr["use_source"] == "default" and pr["use"] == "dwelling" and st[pr["id"]] >= 3:
                    pr["use"], pr["use_source"] = "flats", "default (rule: 3+ storey residential building)"
                n += 1
        json.dump(fc, open(p, "w"))
        C.log(area, year, n, "storeys read off the sheet")


# ----------------------------------------------------------------------------------------------- validation
def check(areas=None, dpi=150):
    """valid geometries, footprints inside their coverage, fits per block, and a PNG per area: the traced footprints of
    the last map year (by confidence) over today's Overture footprints (grey), today's freeways (Overture motorways,
    blue) and the coverage outline (green)."""
    import geopandas as gpd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shapely
    fp = E.modern_footprints()
    mw = C.roads()
    mw = mw[mw["class"] == "motorway"]
    names = sorted({a for a, _ in E.AREAS}) if not areas else areas
    outs = []
    for area in names:
        if not (E.OUT / f"{area}_coverage.geojson").exists():
            continue
        cov = gpd.read_file(E.OUT / f"{area}_coverage.geojson").to_crs(32610)
        years = sorted(y for a, y in E.AREAS if a == area)
        for y in years:
            g = gpd.read_file(E.OUT / f"{area}_{y}.geojson").to_crs(32610)
            cv = shapely.union_all(cov[cov.map_year == y].geometry.values)
            inside = g.geometry.within(cv.buffer(1e-3))
            C.log(area, y, f"{len(g)} footprints, valid {int(g.geometry.is_valid.sum())}, inside coverage {int(inside.sum())},",
                  "confidence", g.confidence.value_counts().to_dict(), "modern_overlap>=0.5", int((g.modern_overlap >= 0.5).sum()),
                  "georef RMS median", round(float(g.georef_rms_m.median()), 2), "max", round(float(g.georef_rms_m.max()), 2))
        y = years[-1]
        g = gpd.read_file(E.OUT / f"{area}_{y}.geojson").to_crs(32610)
        cv = shapely.union_all(cov[cov.map_year == y].geometry.values)
        x0, y0, x1, y1 = cv.bounds
        h = max(8.0, min(40.0, 14 * (y1 - y0) / max(x1 - x0, 1)))
        fig, ax = plt.subplots(figsize=(14, h))
        fp.cx[x0 - 40:x1 + 40, y0 - 40:y1 + 40].plot(ax=ax, color="#bbbbbb", edgecolor="none")
        col = {"high": "#d62728", "medium": "#ff7f0e", "low": "#9467bd"}
        for c, gg in g.groupby("confidence"):
            gg.plot(ax=ax, facecolor="none", edgecolor=col[c], linewidth=0.5)
        m = mw.cx[x0 - 40:x1 + 40, y0 - 40:y1 + 40]
        if len(m):
            m.plot(ax=ax, color="#1f77b4", linewidth=0.9)
        gpd.GeoSeries([cv], crs=32610).boundary.plot(ax=ax, color="#2ca02c", linewidth=0.8)
        ax.set_xlim(x0 - 40, x1 + 40); ax.set_ylim(y0 - 40, y1 + 40)
        ax.set_title(f"{area} {y}: {len(g)} traced (red high / orange medium / purple low) over today's footprints (grey), "
                     f"freeways (blue), coverage (green)", fontsize=9)
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        o = E.INTERIM / f"check_{area}.png"
        fig.tight_layout(); fig.savefig(o, dpi=dpi); plt.close(fig)
        outs.append(o)
        print(o)
    return outs


# ----------------------------------------------------------------------------------------------- driver
if __name__ == "__main__":
    configure()
    E.index()
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    args = sys.argv[2:]
    if stage == "grid":
        k = args[0]
        box = tuple(int(v) for v in args[1:5]) if len(args) >= 5 else None
        print(E.grid(k, box, step=int(os.environ.get("STEP", 100)), scale=float(os.environ.get("SCALE", 1.0))))
        sys.exit()
    if stage == "register":
        W.register(args[0], args[1])
        sys.exit()
    if stage in ("spec", "predict", "auto", "zones"):
        s = args[1]
        s = json.load(open(s)) if os.path.exists(s) else json.loads(s)
        if stage == "predict":
            predict(args[0], s)
        elif stage == "spec" and s.get("run"):  # hand-read block outlines: spec + refine + regroup + georef
            E.spec(args[0], {k: v for k, v in s.items() if k != "run"})
            mark_blocks(args[0], s["blocks"])
            E.refine(args[0], weak=s.get("weak", 0.35))
            regroup(args[0])
            W.georef(args[0])
            store_chamfer(args[0])
            apply_chamfer(args[0])
            report(args[0])
        elif stage == "auto":
            auto(args[0], s)
        elif stage == "zones":
            zones(args[0], s)
        else:
            E.spec(args[0], s)
        print("wrote", E.CONTROL / f"{args[0]}.json")
        sys.exit()
    if stage == "setcorner":  # setcorner <key> <block> <corner> <x> <y> [...]: hand corrections, then georef
        k = args[0]
        for i in range(1, len(args), 4):
            setcorner(k, args[i], args[i + 1], float(args[i + 2]), float(args[i + 3]))
        W.georef(k)
        apply_chamfer(k)
        report(k)
        sys.exit()
    if stage == "crops":  # crops <key> x,y x,y ...
        print(crops(args[0], [tuple(float(v) for v in a.split(",")) for a in args[1:]], half=int(os.environ.get("HALF", 70))))
        sys.exit()
    if stage == "report":
        for k in args:
            report(k)
        sys.exit()
    if stage == "respec":
        cfg = json.load(open(E.CONTROL / f"{args[0]}.json"))
        top = {k: v for k, v in cfg.items() if k not in ("blocks", "pct")}
        top.update(json.loads(args[1]) if len(args) > 1 else {})
        s = dict(top, blocks={b["name"]: dict(b["streets"], px=b["px4_est"], **{k: b[k] for k in ("w", "skip", "oc", "near", "no_refine", "with") if k in b})
                              for b in cfg["blocks"]})
        E.spec(args[0], s)
        sys.exit()
    if stage == "check":
        check(args or None)
        sys.exit()
    keys = args or E.all_keys()
    if stage in ("all", "fetch"):
        for k in keys:
            E.image(k, int(os.environ.get("PCT", 25)))
    if stage == "refine":
        for k in keys:
            E.refine(k, weak=json.load(open(E.CONTROL / f"{k}.json")).get("weak", 0.35))
            regroup(k)
    if stage in ("all", "georef"):
        for k in E.base_first(keys):
            if json.load(open(E.CONTROL / f"{k}.json")).get("mode") != "chamfer_only":
                W.georef(k)
            apply_chamfer(k)
    if stage == "mosaic":
        for k in keys:
            print(E.corner_mosaic(k))
    if stage in ("all", "extract"):
        for k in keys:
            E.extract(k)
            E.reclass(k)
            if k.split("_")[0] in E.EDITION_1950:
                E.extract_regions(k)
    if stage == "overlay":
        for k in keys:
            print(E.overlay(k, scale=float(os.environ.get("SCALE", 0.5))))
    if stage in ("all", "tracks"):
        for k in keys:
            W.tracks(k)
    if stage in ("all", "assemble"):
        E.assemble()
        C.cap_blocks()
        C.commercial_fronts()
        apply_storeys()
        cover_footprints()
