"""Trace historical building footprints for the San Francisco waterfront from Library of Congress Sanborn maps.

Areas: Fisherman's Wharf / northern waterfront (1899, 1913, 1950) and Mission Bay / China Basin (1913-14, 1950).
Inputs (committed, hand-measured):  data/manual/sanborn/control/<vol>_<sheet>.json  (control points, block corners,
                                    street-line constraints, registration transforms), *.wharves.json (deck seeds),
                                    attributes.json (storeys / use / names read from the sheets)
Downloads (cached, gitignored):     data/raw/sanborn_loc/   (LOC item JSON, IIIF images at 25 % and 50 %)
Intermediates:                      data/interim/sanborn_waterfront/<key>.M.json (fits), <key>.json (footprints)
Outputs:                            data/manual/sanborn/<area>_<year>.geojson, <area>_coverage.geojson
See data/manual/sanborn/README_waterfront.md for the method, sheets and residuals.

Usage:  python pipeline/sanborn_trace_waterfront.py all            # fetch + georef + extract + wharves + assemble
        python pipeline/sanborn_trace_waterfront.py georef 015_0064 # one stage, some sheets
        python pipeline/sanborn_trace_waterfront.py register 030_0064 015_0064   # recompute a SIFT registration
Keys are <LOC item suffix>_<sheet file suffix>, e.g. 015_0064 = sanborn00813_015 (1913 vol. 1), sheet 64.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
RAW = ROOT / "data/raw/sanborn_loc"
INTERIM = ROOT / "data/interim/sanborn_waterfront"
CONTROL = ROOT / "data/manual/sanborn/control"
OUT = ROOT / "data/manual/sanborn"
FT = 0.3048
PXM = 0.1935  # nominal metres per pixel at 25 % (50 ft = 1 in)

VOLUMES = {  # LOC item suffix -> (map year, label)
    "008": (1899, "1899 Vol. 1"), "015": (1913, "1913 Vol. 1"), "016": (1913, "1913 Vol. 2"), "020": (1914, "1914 Vol. 6"),
    "030": (1950, "1913-1950 Vol. 1 (corrected to 1950)"), "031": (1950, "1913-Sep 1950 Vol. 2 (corrected)"),
    "035": (1950, "1914-Dec 1950 Vol. 6 (corrected)")}
AREAS = {
    ("fishermans_wharf", 1899): ["008_0074", "008_0088", "008_0093", "008_0111"],
    ("fishermans_wharf", 1913): ["015_0064", "015_0065", "015_0079", "015_0080", "015_0081", "015_0096"],
    ("fishermans_wharf", 1950): ["030_0064", "030_0065", "030_0079", "030_0080", "030_0081", "030_0096"],
    ("mission_bay", 1913): ["016_0152", "016_0160", "016_0168", "016_0176", "016_0217", "016_0220", "020_0546", "020_0560", "020_0561"],
    ("mission_bay", 1950): ["031_0152", "031_0160", "031_0168", "031_0176", "031_0217", "031_0220", "035_0546", "035_0560", "035_0561"],
}
RESIDENTIAL_SHEETS = {"0065", "0081", "0096", "0088", "0546", "0561"}
EDITION_1950 = ("028", "029", "030", "031", "032", "033", "034", "035", "036", "037", "038")


def log(*a):
    print("sanborn_waterfront:", *a, flush=True)


# ----------------------------------------------------------------------------------------------- LOC downloads
def curl(url, out: Path, min_bytes=1000, tries=6):
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_size >= min_bytes:
        return out
    for k in range(tries):
        r = subprocess.run(["curl", "-sS", "-L", "--http1.1", "--retry", "3", "--max-time", "300", "-A",
                            "BayAreaThroughTime/0.1 (research)", url, "-o", str(out)])
        if r.returncode == 0 and out.exists() and out.stat().st_size >= min_bytes:
            return out
        time.sleep(3 + 5 * k)
    raise RuntimeError(f"download failed: {url}")


_index = None


def index():
    """{vol: [{id, info, w, h}]} for the volumes used, from the LOC item JSON."""
    global _index
    if _index is not None:
        return _index
    p = RAW / "index.json"
    if p.exists():
        _index = json.load(open(p))
        return _index
    idx = {}
    for vol in VOLUMES:
        f = curl(f"https://www.loc.gov/item/sanborn00813_{vol}/?fo=json", RAW / f"item_{vol}.json", 20000)
        d = json.load(open(f))
        ids = []
        for fl in d["resources"][0]["files"]:
            jp = [x for x in fl if x.get("mimetype") == "image/jp2"]
            if jp:
                ids.append({"id": jp[0]["url"].rsplit("/", 1)[1][:-4], "info": jp[0]["info"], "w": jp[0]["width"], "h": jp[0]["height"]})
        idx[vol] = ids
    json.dump(idx, open(p, "w"))
    _index = idx
    return idx


def sheet_rec(key):
    vol, sheet = key.split("_")
    return [s for s in index()[vol] if s["id"].split("-")[-1] == sheet][0]


def image(key, pct=25) -> Path:
    s = sheet_rec(key)
    return curl(s["info"].replace("/info.json", f"/full/pct:{pct}/0/default.jpg"), RAW / f"{key}_{pct}.jpg", 10000)


# ----------------------------------------------------------------------------------------------- street geometry
_st = None


def streets():
    global _st
    if _st is None:
        from fire_1906 import load_streets
        _st = load_streets()  # EPSG:32610
    return _st


def xing(a, b):
    from fire_1906 import intersection
    p, how = intersection(streets(), a, b)
    return np.array([p.x, p.y]), how


def street_line(name, near, R=350):
    """least-squares straight line (point, unit dir) through the centreline of `name` within R m of `near`."""
    from fire_1906 import street_rows
    pts = []
    for geom in street_rows(streets(), name).geometry:
        for gg in ([geom] if geom.geom_type == "LineString" else list(geom.geoms)):
            c = np.asarray(gg.coords)
            for a, b in zip(c[:-1], c[1:]):
                for t in np.linspace(0, 1, max(2, int(np.hypot(*(b - a)) / 5))):
                    p = a + t * (b - a)
                    if np.hypot(*(p - near)) < R:
                        pts.append(p)
    pts = np.asarray(pts)
    m = pts.mean(axis=0)
    return m, np.linalg.svd(pts - m)[2][0]


def grid_dirs(a, b):
    """unit vectors at the a x b crossing: (northward along the N-S street, eastward along the E-W street)."""
    X = xing(a, b)[0]
    ds = []
    for n in (a, b):
        d = street_line(n, X, 250)[1]
        if abs(d[1]) > abs(d[0]):
            ds.append(("NS", d if d[1] > 0 else -d))
        else:
            ds.append(("EW", d if d[0] > 0 else -d))
    eN = [d for k, d in ds if k == "NS"][0]
    eE = [d for k, d in ds if k == "EW"][0]
    kinds = [k for k, _ in ds]
    return X, eN, eE, kinds


def block_corner(a, b, q, wa=68.75, wb=68.75, X=None):
    """world corner of the block in quadrant q (NE/NW/SE/SW) of the a x b crossing, offset by half street widths."""
    X0, eN, eE, kinds = grid_dirs(a, b)
    X = X0 if X is None else X
    w = {"a": wa, "b": wb}
    wNS = (wa if kinds[0] == "NS" else wb) * FT
    wEW = (wb if kinds[1] == "EW" else wa) * FT
    sN = 1 if "N" in q else -1
    sE = 1 if "E" in q else -1
    return X + sN * (wEW / 2) * eN + sE * (wNS / 2) * eE


def world_of(c):
    """world position (EPSG:32610) of one control entry."""
    if "bcs" in c:  # block corner at a vanished crossing (grid vector sum of existing crossings)
        X = sum((1 if sg == "+" else -1) * xing(a, b)[0] for sg, a, b in c["bcs"])
        _, eN, eE, _ = grid_dirs(c["ns"], c["ew"])
        sN = 1 if "N" in c["q"] else -1
        sE = 1 if "E" in c["q"] else -1
        return X + sN * (c.get("wew", 68.75) * FT / 2) * eN + sE * (c.get("wns", 68.75) * FT / 2) * eE, c.get("label", "grid corner")
    if "bc" in c:
        return block_corner(c["bc"][0], c["bc"][1], c["q"], c.get("wa", 68.75), c.get("wb", 68.75)), f"corner {c['q']} of {c['bc'][0]} x {c['bc'][1]}"
    if "a" in c:
        p, how = xing(c["a"], c["b"])
        return p, f"{c['a']} x {c['b']} [{how}]"
    if "sum" in c:
        return sum((1 if sg == "+" else -1) * xing(a, b)[0] for sg, a, b in c["sum"]), c.get("label", "grid point")
    if "la" in c:
        L1 = street_line(c["la"][0], xing(*c["la"])[0])
        L2 = street_line(c["lb"][0], xing(*c["lb"])[0])
        A = np.array([L1[1], -L2[1]]).T
        t = np.linalg.solve(A, L2[0] - L1[0])
        return L1[0] + t[0] * L1[1], f"line {c['la'][0]} x {c['lb'][0]} (extended)"
    raise ValueError(c)


# ----------------------------------------------------------------------------------------------- fitting
def apply(M, p):
    p = np.asarray(p, float)
    return (M[:, :2] @ p.T).T + M[:, 2]


def M_of(v):
    s, th, tx, ty = v
    a, b = s * math.cos(th), s * math.sin(th)
    return np.array([[a, b, tx], [b, -a, ty]])  # image (x right, y down) -> world


def fit(px, w, lines=(), prior=None):
    """similarity image px -> world by least squares on points, point-on-line constraints and a scale prior."""
    from scipy.optimize import least_squares
    px, w = np.asarray(px, float).reshape(-1, 2), np.asarray(w, float).reshape(-1, 2)

    def resid(v):
        M = M_of(v)
        r = list((apply(M, px) - w).ravel()) if len(px) else []
        r += [float(n @ (apply(M, [q])[0] - p0)) for q, p0, n in lines]
        if prior:
            r.append((v[0] - prior[0]) / prior[1])
        return r
    s0 = prior[0] if prior else 0.2
    c0 = w.mean(axis=0) if len(w) else lines[0][1]
    pc = px.mean(axis=0) if len(px) else np.mean([q for q, _, _ in lines], axis=0)
    best = None
    for th in np.radians(np.arange(-180, 180, 15)):
        t = c0 - apply(M_of([s0, th, 0, 0]), [pc])[0]
        sol = least_squares(resid, [s0, th, t[0], t[1]])
        if best is None or sol.cost < best.cost:
            best = sol
    M = M_of(best.x)
    res = [float(np.hypot(*(apply(M, [p])[0] - q))) for p, q in zip(px, w)]
    res += [abs(float(n @ (apply(M, [q])[0] - p0))) for q, p0, n in lines]
    return M, np.array(res)


def describe(M):
    a, b = M[0, 0], M[1, 0]
    return f"scale {math.hypot(a, b):.4f} m/px, rot {math.degrees(math.atan2(b, a)):.2f} deg"


def georef(key):
    cfg = json.load(open(CONTROL / f"{key}.json"))
    INTERIM.mkdir(parents=True, exist_ok=True)
    img = image(key)
    if "registered_to" in cfg:  # 1950 sheet registered onto its 1913/14 base plate
        D = json.load(open(INTERIM / f"{cfg['registered_to']}.M.json"))
        T = np.array(cfg["T"])
        Ti = np.linalg.inv(np.vstack([T, [0, 0, 1]]))[:2]

        def comp(M):
            M = np.array(M)
            return np.column_stack([M[:, :2] @ T[:, :2], M[:, :2] @ T[:, 2] + M[:, 2]]).tolist()

        def back(r):
            x0, y0, x1, y1 = r
            q = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], float) @ Ti[:, :2].T + Ti[:, 2]
            return [float(q[:, 0].min()), float(q[:, 1].min()), float(q[:, 0].max()), float(q[:, 1].max())]
        out = dict(D, M=comp(D["M"]), img=str(img), registered_to=cfg["registered_to"], reg_rms_px=cfg["reg_rms_px"])
        out["scale"] = describe(np.array(out["M"]))
        out["reg_rms_m"] = cfg["reg_rms_px"] * math.hypot(out["M"][0][0], out["M"][1][0])
        out["blocks"] = [dict(b, M=comp(b["M"]), rect_px=back(b["rect_px"])) for b in D.get("blocks", [])]
        if D.get("valid_px"):
            out["valid_px"] = back(D["valid_px"])
        json.dump(out, open(INTERIM / f"{key}.M.json", "w"), indent=1)
        log(key, "registered to", cfg["registered_to"], out["scale"], f"reg {cfg['reg_rms_px']:.2f} px")
        return
    allpx, allw, alllab = [], [], []
    for c in cfg.get("points", []):
        w, lab = world_of(c)
        allpx.append((c["x"], c["y"])); allw.append(w); alllab.append(lab)
    lines = []
    for ln in cfg.get("lines", []):
        p0, d = street_line(ln["street"], xing(*ln["near"])[0], ln.get("R", 300))
        lines += [(np.array(q, float), p0, np.array([-d[1], d[0]])) for q in ln["px"]]
    blocks = []
    for b in cfg.get("blocks", []):
        bpx, bw, bl = [], [], []
        for c in b["corners"]:
            w, lab = world_of(c)
            bpx.append((c["x"], c["y"])); bw.append(w); bl.append(lab)
        Mb, d = fit(bpx, bw, prior=cfg.get("scale_prior"))
        pa = np.array(bpx)
        rect = b.get("zone_px") or [float(pa[:, 0].min()), float(pa[:, 1].min()), float(pa[:, 0].max()), float(pa[:, 1].max())]
        blocks.append({"name": b["name"], "M": Mb.tolist(), "rect_px": rect, "rms": float(np.sqrt((d ** 2).mean())), "max": float(d.max()),
                       "n": len(bpx), "points": [{"label": l, "px": list(map(float, p)), "res_m": round(float(r), 2)} for l, p, r in zip(bl, bpx, d)]})
        allpx += bpx; allw += bw; alllab += [b["name"] + " " + l for l in bl]
        log(key, f"block {b['name']}", describe(Mb), f"RMS {np.sqrt((d ** 2).mean()):.2f} m")
    M, d = fit(allpx, allw, lines, cfg.get("scale_prior"))
    labs = alllab + ["on street line"] * len(lines)
    pxs = allpx + [tuple(q) for q, _, _ in lines]
    json.dump({"M": M.tolist(), "pct": 25, "img": str(img), "rms": float(np.sqrt((d ** 2).mean())), "max": float(d.max()), "n": len(d),
               "scale": describe(M), "blocks": blocks, "zones_only": cfg.get("zones_only", False), "valid_px": cfg.get("valid_px"),
               "points": [{"label": l, "px": list(map(float, p)), "res_m": round(float(r), 2)} for l, p, r in zip(labs, pxs, d)]},
              open(INTERIM / f"{key}.M.json", "w"), indent=1)
    log(key, "sheet", describe(M), f"n={len(d)} RMS {np.sqrt((d ** 2).mean()):.2f} max {d.max():.2f} m")


def register(src, dst):
    """SIFT + RANSAC similarity from sheet image src onto dst (same base plate, later edition); updates the control file."""
    import cv2
    A = cv2.GaussianBlur(np.asarray(Image.open(image(src)).convert("L")), (3, 3), 0)
    B = cv2.GaussianBlur(np.asarray(Image.open(image(dst)).convert("L")), (3, 3), 0)
    det = cv2.SIFT_create(nfeatures=20000)
    ka, da = det.detectAndCompute(A, None)
    kb, db = det.detectAndCompute(B, None)
    good = [m[0] for m in cv2.BFMatcher(cv2.NORM_L2).knnMatch(da, db, k=2) if len(m) == 2 and m[0].distance < 0.8 * m[1].distance]
    pa = np.float32([ka[g.queryIdx].pt for g in good]); pb = np.float32([kb[g.trainIdx].pt for g in good])
    T, inl = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=3.0, maxIters=20000, confidence=0.999)
    inl = inl.ravel().astype(bool)
    r = (pa[inl] @ T[:, :2].T + T[:, 2]) - pb[inl]
    rms = float(np.sqrt((r ** 2).sum(axis=1).mean()))
    json.dump({"registered_to": dst, "T": T.tolist(), "reg_inliers": int(inl.sum()), "reg_rms_px": round(rms, 2)},
              open(CONTROL / f"{src}.json", "w"), indent=1)
    log(src, "->", dst, f"inliers {int(inl.sum())} rms {rms:.2f} px")


# ----------------------------------------------------------------------------------------------- footprints
def extract(key):
    """colour-segment Sanborn building fills (yellow frame, pink brick, blue stone/concrete, brown fireproof, grey iron)."""
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
    pH, pS = int(np.median(Hh[pm])), int(np.median(S[pm]))
    if ed in EDITION_1950:  # yellowed paper and paste-over slips: hue + saturation relative to the paper
        fr = ((Hh >= max(pH, 23)) & (Hh <= 36) & (S >= pS + 42) & (V >= 70)) | ((Hh >= 19) & (Hh <= 36) & (S >= 125) & (V >= 70))
    else:
        fr = (Hh >= 18) & (Hh <= 38) & (S >= max(85, pS + 45)) & (V >= 80)
    split = ed in ("031", "035")
    classes = {
        "frame": fr,
        "brick": ((Hh >= 158) | (Hh <= 6)) & (S >= 45) & (V >= 60),
        "stone": (Hh >= 80) & (Hh <= 130) & (S >= 35) & (V >= 60),
        "fireproof": (Hh >= 5) & (Hh <= (18 if split else 15)) & (S >= (90 if split else 115)) & (V >= 50),
        "iron": ((Hh >= 17) & (Hh <= 28) & (S <= 31) & (V >= 115) & (V <= 146) & (dV <= -4))
                | ((ed in EDITION_1950) & (Hh >= 31) & (Hh <= 42) & (S >= 28) & (S <= pS - 6) & (V >= 112) & (V <= 152)),
    }
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    dark = gray < 110
    part = ndi.binary_dilation(ndi.binary_opening(dark, structure=np.ones((18, 1))) | ndi.binary_opening(dark, structure=np.ones((1, 18))),
                               structure=np.ones((2, 2)))
    darkd = ndi.binary_dilation(gray < 120, iterations=3)
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
        if split and cls != "brick":
            m = (ndi.binary_closing(m, structure=np.ones((3, 3))) | m) & ~part
        else:
            m = ndi.binary_closing(m, structure=np.ones((5, 5))) & ~part | m
        holes = ndi.binary_fill_holes(m) & ~m
        hl, hn = ndi.label(holes)
        if hn:
            hs = ndi.sum(holes, hl, range(1, hn + 1))
            m = m | np.isin(hl, np.nonzero(hs < 2500)[0] + 1)
        lab, n = ndi.label(m)
        if not n:
            continue
        sizes = ndi.sum(m, lab, range(1, n + 1)); objs = ndi.find_objects(lab)
        for i in range(n):
            sl = objs[i]
            if sizes[i] < 120 or sl[0].start < 12 or sl[1].start < 12 or sl[0].stop > m.shape[0] - 12 or sl[1].stop > m.shape[1] - 12:
                continue
            if min(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) < 8:
                continue
            sub = lab[sl] == i + 1
            dist = ndi.distance_transform_edt(np.pad(sub, 1))
            if dist.max() < 4.5:
                continue
            hullA = cv2.contourArea(cv2.convexHull(np.argwhere(sub)[:, ::-1].astype(np.int32)))
            solid = sizes[i] / hullA if hullA > 0 else 0
            if cls == "iron" and (sizes[i] < 400 or dist.max() < 6 or solid < 0.75):
                continue
            # outline test: buildings are outlined in black, stains and paste-over slips are not
            ring_out = ndi.binary_dilation(np.pad(sub, 4), iterations=1) & ~np.pad(sub, 4)
            y0_, x0_ = max(0, sl[0].start - 4), max(0, sl[1].start - 4)
            dd = darkd[y0_:sl[0].stop + 4, x0_:sl[1].stop + 4]
            oy, ox = 4 - (sl[0].start - y0_), 4 - (sl[1].start - x0_)
            dd = np.pad(dd, ((oy, max(0, ring_out.shape[0] - dd.shape[0] - oy)), (ox, max(0, ring_out.shape[1] - dd.shape[1] - ox))))
            dd = dd[:ring_out.shape[0], :ring_out.shape[1]]
            edge_dark = float(dd[ring_out].mean()) if ring_out.any() else 0
            (_, (rw, rh), _) = cv2.minAreaRect(np.argwhere(sub)[:, ::-1].astype(np.float32))
            if sizes[i] / max(rw * rh, 1) < 0.45 and edge_dark < 0.9:
                edge_dark = min(edge_dark, 0.5)
            if edge_dark < (0.7 if cls == "iron" else 0.78) or (solid < 0.55 and edge_dark < 0.85):
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
            outer = Polygon(rings[0]).buffer(0.8, join_style=2).simplify(1.0)
            if outer.geom_type != "Polygon":
                outer = max(outer.geoms, key=lambda p: p.area)
            hol = [Polygon(r).buffer(-0.8, join_style=2).simplify(1.0) for r in rings[1:] if Polygon(r).area > 400]
            hol = [h for h in hol if h.geom_type == "Polygon" and outer.contains(h)]
            poly = Polygon(outer.exterior.coords, [h.exterior.coords for h in hol])
            cx, cy = poly.centroid.x, poly.centroid.y
            vp = G.get("valid_px")
            if vp and not (vp[0] <= cx <= vp[2] and vp[1] <= cy <= vp[3]):
                continue
            T, zone = transform_for(cx, cy)
            if T is None:
                continue
            ext = apply(T, np.asarray(poly.exterior.coords))
            hw = [apply(T, np.asarray(h.coords)) for h in poly.interiors]
            feats.append({"id": f"{key}_{cls[0]}{i + 1}", "cls": cls, "zone": zone, "px_centroid": [round(cx, 1), round(cy, 1)],
                          "px_ring": np.round(np.asarray(poly.exterior.coords), 1).tolist(), "area_m2": round(float(Polygon(ext, hw).area), 1),
                          "ring_utm": np.round(ext, 2).tolist(), "holes_utm": [np.round(h, 2).tolist() for h in hw]})
    json.dump(feats, open(INTERIM / f"{key}.json", "w"))
    log(key, len(feats), "footprints")


def wharves(key):
    """wharf / pier decks: flood fill between the drawn outlines from hand-placed seeds (control/<key>.wharves.json)."""
    import cv2
    from shapely.geometry import Polygon
    f = CONTROL / f"{key}.wharves.json"
    if not f.exists():
        return
    G = json.load(open(INTERIM / f"{key}.M.json"))
    gray = cv2.cvtColor(np.asarray(Image.open(G["img"]).convert("RGB")), cv2.COLOR_RGB2GRAY)
    barrier = ndi.binary_dilation(gray < 120, iterations=1)
    M = np.array(G["M"])
    out = []
    for k, w in enumerate(json.load(open(f))):
        allowed = ~barrier
        cm = None
        if w.get("clip"):
            cm = np.zeros(gray.shape, np.uint8)
            cv2.fillPoly(cm, [np.array(w["clip"], np.int32)], 1)
            cm = cm.astype(bool)
            allowed &= cm
        lab, _ = ndi.label(allowed)
        seeds = list(w.get("seeds", []))
        if w.get("seed_grid") and cm is not None:
            ys, xs = np.nonzero(cm & ~barrier)
            seeds += [(int(x), int(y)) for x, y in zip(xs[::997], ys[::997])]
        reg = np.isin(lab, [lab[y, x] for x, y in seeds if lab[y, x] > 0])
        reg = ndi.binary_fill_holes(ndi.binary_closing(reg, structure=np.ones((5, 5)), iterations=2))
        if cm is not None:
            reg &= cm
        reg = ndi.binary_opening(reg, structure=np.ones((3, 3)))
        cs, _ = cv2.findContours(reg.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not cs:
            continue
        poly = Polygon(max(cs, key=cv2.contourArea)[:, 0, :].astype(float)).buffer(1.2, join_style=2).simplify(1.5)
        if poly.geom_type != "Polygon":
            poly = max(poly.geoms, key=lambda p: p.area)
        ext = apply(M, np.asarray(poly.exterior.coords))
        out.append({"id": f"{key}_w{k + 1}", "cls": "wharf", "zone": "sheet", "name": w["name"], "confidence": w.get("confidence", "medium"),
                    "px_centroid": [round(poly.centroid.x, 1), round(poly.centroid.y, 1)], "px_ring": np.asarray(poly.exterior.coords).round(1).tolist(),
                    "area_m2": round(float(Polygon(ext).area), 1), "ring_utm": np.round(ext, 2).tolist(), "holes_utm": []})
    json.dump(out, open(INTERIM / f"{key}.manual.json", "w"))
    log(key, len(out), "wharf decks")


# ----------------------------------------------------------------------------------------------- outputs
def assemble():
    import glob
    import geopandas as gpd
    import pandas as pd
    import shapely
    from pyproj import Transformer
    from shapely import make_valid
    from shapely.geometry import Polygon, mapping
    from shapely.ops import unary_union
    from shapely.strtree import STRtree
    to_ll = Transformer.from_crs(32610, 4326, always_xy=True)

    def lonlat(g):
        return shapely.transform(g, lambda c: np.column_stack(to_ll.transform(c[:, 0], c[:, 1])))
    attrs = json.load(open(CONTROL / "attributes.json"))
    fp = gpd.GeoDataFrame(pd.concat([gpd.read_file(p) for p in sorted(glob.glob(str(ROOT / "data/raw/sf_footprints/page-*.geojson")))]), crs=4326).to_crs(32610)
    fpg = list(fp.geometry.values); tree = STRtree(fpg)

    def overlap(g):
        parts = [fpg[i].intersection(g) for i in tree.query(g) if fpg[i].intersects(g)]
        return round(float(unary_union(parts).area / g.area), 2) if parts and g.area > 0 else 0.0

    def conf_of(f):
        if f.get("n", 0) >= 4 and f.get("rms", 9) <= 1.5 and f.get("max", 9) <= 3:
            return "high"
        return "medium" if f.get("n", 0) >= 3 and f.get("rms", 9) <= 3 else "low"
    covers = {}
    for (area, year), keys in AREAS.items():
        feats, cover = [], []
        for key in keys:
            vol, sheet = key.split("_")
            G = json.load(open(INTERIM / f"{key}.M.json"))
            map_year, vlabel = VOLUMES[vol]
            rec = sheet_rec(key)
            rows = json.load(open(INTERIM / f"{key}.json"))
            if (INTERIM / f"{key}.manual.json").exists():
                rows += json.load(open(INTERIM / f"{key}.manual.json"))
            blocks = {b["name"]: b for b in G.get("blocks", [])}
            W_, H_ = Image.open(G["img"]).size
            if G.get("zones_only"):
                for b in G["blocks"]:
                    x0, y0, x1, y1 = b["rect_px"]
                    cover.append(Polygon(apply(np.array(b["M"]), [[x0, y0], [x1, y0], [x1, y1], [x0, y1]])))
            else:
                x0, y0, x1, y1 = G.get("valid_px") or [30, 30, W_ - 30, H_ - 30]
                x0, y0, x1, y1 = max(x0, 30), max(y0, 30), min(x1, W_ - 30), min(y1, H_ - 30)
                cover.append(Polygon(apply(np.array(G["M"]), [[x0, y0], [x1, y0], [x1, y1], [x0, y1]])))
            for r in rows:
                g = make_valid(Polygon(r["ring_utm"], r.get("holes_utm") or []))
                if g.geom_type != "Polygon":
                    polys = [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]
                    if not polys:
                        continue
                    g = max(polys, key=lambda p: p.area)
                if g.area < 6:
                    continue
                zone = r.get("zone", "sheet")
                fitq = dict(blocks[zone] if zone in blocks else {"rms": G.get("rms", 9), "n": G.get("n", 0), "max": G.get("max", 9)})
                if "registered_to" in G:
                    fitq["rms"] = math.hypot(fitq.get("rms", 0), G.get("reg_rms_m", 0.3))
                cls, a = r["cls"], r["area_m2"]
                att = attrs.get(r["id"], {})
                if cls == "wharf":
                    material, use, stories, ssrc, usrc = "frame", "wharf", 0, "deck (no storeys)", "map"
                else:
                    material = {"frame": "frame", "brick": "brick", "stone": "concrete" if map_year >= 1950 else "stone",
                                "fireproof": "unknown" if map_year < 1900 else "concrete", "iron": "iron"}[cls]
                    if cls == "frame":
                        st, us = ((1, "shed") if a < 30 else (2, "dwelling") if sheet in RESIDENTIAL_SHEETS and a <= 300
                                  else (1, "warehouse") if a >= 300 else (1, "shed"))
                    else:
                        st, us = (1, "shed") if cls == "iron" else (2, "warehouse")
                    rule = "default (rule: material, size, district)"
                    if att and att.get("src") != "default":
                        stories, use, ssrc, usrc = att.get("stories", st), att.get("use", us), "map (read from the sheet)", "map (label)"
                    elif att:
                        stories, use, ssrc, usrc = att.get("stories", st), att.get("use", us), rule, "map (label)" if att.get("name") else "default"
                    else:
                        stories, use, ssrc, usrc = st, us, rule, "default"
                conf = conf_of(fitq)
                if r.get("confidence") == "low" or (G.get("zones_only") and zone == "sheet") or (map_year < 1900 and cls == "fireproof"):
                    conf = "low"
                feats.append((g, {"id": r["id"], "map_year": map_year, "volume": f"sanborn00813_{vol}", "volume_label": vlabel,
                                  "sheet": rec["id"], "sheet_no": int(sheet.lstrip("0") or 0), "loc_url": f"https://www.loc.gov/item/sanborn00813_{vol}/",
                                  "iiif": rec["info"].replace("/info.json", ""), "stories": stories, "stories_source": ssrc, "material": material,
                                  "use": use, "use_source": usrc, "name": att.get("name") or r.get("name") or None, "sanborn_colour": cls,
                                  "confidence": conf, "georef": f"block {zone}" if zone in blocks else "sheet",
                                  "georef_rms_m": round(float(fitq.get("rms", 0)), 2), "area_m2": round(float(g.area), 1), "modern_overlap": overlap(g)}))
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
        covers.setdefault(area, []).append({"type": "Feature", "properties": {"area": area, "map_year": year, "sheets": keys, "features": len(kept)},
                                            "geometry": rnd(mapping(lonlat(unary_union(cover).buffer(35, join_style=2).buffer(-35, join_style=2))))})
        log(area, year, len(kept), "features")
    for area, fs in covers.items():
        json.dump({"type": "FeatureCollection", "name": f"{area}_coverage", "features": fs}, open(OUT / f"{area}_coverage.geojson", "w"))


def all_keys():
    return [k for ks in AREAS.values() for k in ks]


def base_first(keys):
    """georeference base plates before the sheets registered onto them."""
    reg = [k for k in keys if "registered_to" in json.load(open(CONTROL / f"{k}.json"))]
    return [k for k in keys if k not in reg] + reg


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    keys = sys.argv[2:] or all_keys()
    if stage == "register":
        register(sys.argv[2], sys.argv[3])
        sys.exit()
    if stage in ("all", "fetch"):
        for k in keys:
            image(k, 25)
    if stage in ("all", "georef"):
        for k in base_first(keys):
            georef(k)
    if stage in ("all", "extract"):
        for k in keys:
            extract(k); wharves(k)
    if stage in ("all", "assemble"):
        assemble()
