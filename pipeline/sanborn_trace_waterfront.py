"""Trace historical building footprints for the San Francisco waterfront from Library of Congress Sanborn maps.

Areas: Fisherman's Wharf / northern waterfront (1899, 1913, 1950), Mission Bay / China Basin (1913-14, 1950) and
Potrero Point / Central Basin / Dogpatch (1914, 1950). Rail-yard tracks: see `tracks()`.
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
        python pipeline/sanborn_trace_waterfront.py tracks 020_0591  # railway track centrelines of some sheets
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
    ("fishermans_wharf", 1913): ["015_0001", "015_0051", "015_0064", "015_0065", "015_0079", "015_0080", "015_0081", "015_0096"],
    ("fishermans_wharf", 1950): ["030_0001", "030_0051", "030_0064", "030_0065", "030_0079", "030_0080", "030_0081", "030_0096"],
    ("mission_bay", 1913): ["016_0152", "016_0160", "016_0168", "016_0176", "016_0217", "016_0220", "020_0546", "020_0560", "020_0561",
                            "016_0215", "016_0216", "016_0217r", "016_0219", "016_0221", "016_0222", "016_0223",
                            "020_0545", "020_0545b", "020_0546u", "020_0547", "020_0559"],
    ("mission_bay", 1950): ["031_0152", "031_0160", "031_0168", "031_0176", "031_0217", "031_0220", "035_0546", "035_0560", "035_0561",
                            "031_0215", "031_0216", "031_0217r", "031_0219", "031_0221", "031_0222", "031_0223",
                            "035_0545", "035_0545b", "035_0546u", "035_0547", "035_0559"],
    ("potrero_point", 1914): ["020_0560b", "020_0561b", "020_0562", "020_0574", "020_0575", "020_0589", "020_0590", "020_0591", "020_0592",
                              "020_0593", "020_0594", "020_0607", "020_0608", "020_0609", "020_0610", "020_0626"],
    ("potrero_point", 1950): ["035_0560b", "035_0561b", "035_0562", "035_0574", "035_0575", "035_0589", "035_0590", "035_0591", "035_0592",
                              "035_0593", "035_0594", "035_0607", "035_0608", "035_0609", "035_0610", "035_0626"],
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
    return [s for s in index()[vol] if s["id"].split("-")[-1] == sheet[:4]][0]


def image(key, pct=25) -> Path:
    """IIIF image of a sheet; a key with a letter after the sheet number (020_0546u) is a second, separately
    georeferenced part of the same sheet and shares its image."""
    key = key[:8]
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


def near_xy(near):
    """a `near` hint: a crossing [street a, street b] or a UTM 10N position [x, y] (a hint only: the fitted line is DataSF)."""
    if len(near) == 2 and all(isinstance(v, (int, float)) for v in near):
        return np.array(near, float)
    return xing(*near)[0]


def street_line(name, near, R=350, cnn=None):
    """least-squares straight line (point, unit dir) through the centreline of `name` within R m of `near`.
    DataSF's retired segments (active = false) are included: the old Mission Bay grid (6th St and 4th St south of the
    channel, Channel St, Illinois / Merrimac / Alameda / El Dorado east of 3rd) survives only there."""
    from fire_1906 import street_rows
    pts = []
    rows = street_rows(streets(), name)
    if cnn:  # only these DataSF segments (e.g. the retired diagonal 4th St, not today's N-S 4th St beside it)
        rows = rows[rows.cnn.astype(float).astype(int).isin([int(c) for c in cnn])]
    for geom in rows.geometry:
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
    if "tie" in c:  # a feature drawn on an adjacent, already georeferenced sheet (street corner, wharf corner, match line end)
        G = json.load(open(INTERIM / f"{c['tie']}.M.json"))
        Mo = np.array(G["M"])
        for b in G.get("blocks", []):
            if b["name"] == c.get("tie_block"):
                Mo = np.array(b["M"])
        return apply(Mo, [c["px_other"]])[0], c.get("label", f"tie to {c['tie']} {c['px_other']}")
    if "la" in c:  # crossing of two fitted centrelines, extended where the street no longer reaches (optional offsets in ft)
        def L(spec):  # [street, other street] (near their crossing) or [street, [x, y]] (near a UTM position)
            return street_line(spec[0], near_xy(spec if isinstance(spec[1], str) else spec[1]), c.get("R", 350),
                               spec[2] if len(spec) > 2 else None)
        L1, L2 = L(c["la"]), L(c["lb"])
        p1, p2 = L1[0], L2[0]
        if "off" in c:  # block corner: shift each line sideways by [ft, compass direction], e.g. [[41.25, "SE"], [41.25, "NE"]]
            comp = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0), "NE": (1, 1), "NW": (-1, 1), "SE": (1, -1), "SW": (-1, -1)}

            def shift(p, d, o):
                n = np.array([-d[1], d[0]])
                n = n if n @ np.array(comp[o[1]], float) > 0 else -n
                return p + o[0] * FT * n
            p1, p2 = shift(p1, L1[1], c["off"][0]), shift(p2, L2[1], c["off"][1])
        A = np.array([L1[1], -L2[1]]).T
        t = np.linalg.solve(A, p2 - p1)
        return p1 + t[0] * L1[1], c.get("label", f"line {c['la'][0]} x {c['lb'][0]} (extended)")
    raise ValueError(c)


# ----------------------------------------------------------------------------------------------- pixel refinement
def line_masks(g, L=35):
    """long vertical / horizontal dark lines (block and kerb lines) of a grey image."""
    dark = g < min(150, float(np.median(g)) - 40)
    return ndi.binary_opening(dark, structure=np.ones((L, 1))), ndi.binary_opening(dark, structure=np.ones((1, L)))


def _pick(prof, lo, centre, w, side=None, tol=0.22):
    xs = np.arange(len(prof)) + lo
    pk = [i for i in range(1, len(prof) - 1) if prof[i] >= prof[i - 1] and prof[i] >= prof[i + 1] and prof[i] > 0.1 * prof.max() and prof[i] > 5]
    L = [i for i in pk if xs[i] < centre - 0.2 * w]
    R = [i for i in pk if xs[i] > centre + 0.2 * w]
    best = None
    if side is None:
        for i in L:
            for j in R:
                if abs(xs[j] - xs[i] - w) <= tol * w:
                    sc = prof[i] + prof[j] - 0.5 * abs((xs[i] + xs[j]) / 2 - centre)
                    if best is None or sc > best[0]:
                        best = (sc, (xs[i] + xs[j]) / 2)
    if best is None and side in (None, "L") and L:
        i = max(L, key=lambda i: prof[i] - 2 * abs(xs[i] - (centre - w / 2)))
        best = (0, xs[i] + w / 2)
    if best is None and side in (None, "R") and R:
        j = max(R, key=lambda j: prof[j] - 2 * abs(xs[j] - (centre + w / 2)))
        best = (0, xs[j] - w / 2)
    return best


def refine_crossing(masks, x0, y0, wv=68.75, wh=68.75, scale=PXM, reach=320, sides=(None, None), only=None):
    """centre of a street crossing from the two kerb lines of each street (approximate pixel in, refined pixel out)."""
    v, h = masks
    H, Wd = v.shape
    wvp, whp = wv * FT / scale, wh * FT / scale
    x, y = x0, y0
    if only != "y":
        rows = [r for r in range(int(y0 - reach), int(y0 + reach)) if abs(r - y0) > whp * 0.8 and 0 <= r < H]
        lo, hi = int(max(0, x0 - wvp * 1.1)), int(min(Wd, x0 + wvp * 1.1))
        b = _pick(v[rows, lo:hi].sum(axis=0).astype(float), lo, x0, wvp, sides[0])
        x = b[1] if b else x0
    if only != "x":
        cols = [c for c in range(int(x0 - reach), int(x0 + reach)) if abs(c - x0) > wvp * 0.8 and 0 <= c < Wd]
        lo, hi = int(max(0, y0 - whp * 1.1)), int(min(H, y0 + whp * 1.1))
        b = _pick(h[lo:hi, cols].sum(axis=1).astype(float), lo, y0, whp, sides[1])
        y = b[1] if b else y0
    return float(x), float(y)


def refine_corner(masks, x, y, win=14, span=70):
    """snap a block-corner pixel to the strongest vertical and horizontal block line nearby."""
    v, h = masks
    H, Wd = v.shape
    pv = v[int(max(0, y - span)):int(min(H, y + span)), int(max(0, x - win)):int(min(Wd, x + win))].sum(axis=0)
    ph = h[int(max(0, y - win)):int(min(H, y + win)), int(max(0, x - span)):int(min(Wd, x + span))].sum(axis=1)
    nx = int(max(0, x - win)) + int(np.argmax(pv)) if pv.max() > 10 else x
    ny = int(max(0, y - win)) + int(np.argmax(ph)) if ph.max() > 10 else y
    return float(nx), float(ny)


def measured(c, masks):
    """pixel of a control entry: as stored if `norefine`, else refined on the image (new sheets)."""
    if c.get("norefine") or masks is None:
        return c["x"], c["y"]
    if "bc" in c or "bcs" in c:
        return refine_corner(masks, c["x"], c["y"])
    return refine_crossing(masks, c["x"], c["y"], c.get("wv", 68.75), c.get("wh", 68.75), sides=tuple(c.get("sides", [None, None])), only=c.get("only"))


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
        if D.get("valid_poly_px"):
            q = np.array(D["valid_poly_px"], float)
            out["valid_poly_px"] = (q @ Ti[:, :2].T + Ti[:, 2]).tolist()
        json.dump(out, open(INTERIM / f"{key}.M.json", "w"), indent=1)
        log(key, "registered to", cfg["registered_to"], out["scale"], f"reg {cfg['reg_rms_px']:.2f} px")
        return
    needs = [c for c in cfg.get("points", []) + [c for b in cfg.get("blocks", []) for c in b["corners"]] if not c.get("norefine")]
    masks = line_masks(np.asarray(Image.open(img).convert("L"), dtype=np.float32)) if needs else None
    allpx, allw, alllab = [], [], []
    for c in cfg.get("points", []):
        w, lab = world_of(c)
        allpx.append(measured(c, masks)); allw.append(w); alllab.append(lab)
    lines = []
    for ln in cfg.get("lines", []):
        p0, d = street_line(ln["street"], near_xy(ln["near"]), ln.get("R", 300), ln.get("cnn"))
        if "off" in ln:  # points on a kerb / building line parallel to the centreline: [ft, compass side]
            n = np.array([-d[1], d[0]])
            comp = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0), "NE": (1, 1), "NW": (-1, 1), "SE": (1, -1), "SW": (-1, -1)}
            p0 = p0 + ln["off"][0] * FT * (n if n @ np.array(comp[ln["off"][1]], float) > 0 else -n)
        lines += [(np.array(q, float), p0, np.array([-d[1], d[0]])) for q in ln["px"]]
    blocks = []
    for b in cfg.get("blocks", []):
        bpx, bw, bl = [], [], []
        for c in b["corners"]:
            w, lab = world_of(c)
            bpx.append(measured(c, masks)); bw.append(w); bl.append(lab)
        Mb, d = fit(bpx, bw, prior=cfg.get("scale_prior"))
        pa = np.array(bpx)
        rect = b.get("zone_px") or [float(pa[:, 0].min()), float(pa[:, 1].min()), float(pa[:, 0].max()), float(pa[:, 1].max())]
        blocks.append({"name": b["name"], "M": Mb.tolist(), "rect_px": rect, "rms": float(np.sqrt((d ** 2).mean())), "max": float(d.max()),
                       "n": len(bpx), "points": [{"label": l, "px": list(map(float, p)), "res_m": round(float(r), 2)} for l, p, r in zip(bl, bpx, d)]})
        allpx += bpx; allw += bw; alllab += [b["name"] + " " + l for l in bl]
        log(key, f"block {b['name']}", describe(Mb), f"RMS {np.sqrt((d ** 2).mean()):.2f} m")
    M, d = fit(allpx, allw, lines, cfg.get("scale_prior"))
    tied = {c["tie"] for c in cfg.get("points", []) + [x for b in cfg.get("blocks", []) for x in b["corners"]] if "tie" in c}
    tie_rms = max([json.load(open(INTERIM / f"{t}.M.json")).get("rms", 0) for t in tied], default=0.0)
    labs = alllab + ["on street line"] * len(lines)
    pxs = allpx + [tuple(q) for q, _, _ in lines]
    json.dump({"M": M.tolist(), "pct": 25, "img": str(img), "rms": float(np.sqrt((d ** 2).mean())), "max": float(d.max()), "n": len(d),
               "scale": describe(M), "blocks": blocks, "zones_only": cfg.get("zones_only", False), "valid_px": cfg.get("valid_px"),
               "valid_poly_px": cfg.get("valid_poly_px"),
               "tied_to": sorted(tied), "tie_rms": tie_rms,
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
    pH, pS, pV = int(np.median(Hh[pm])), int(np.median(S[pm])), int(np.median(V[pm]))
    if ed in EDITION_1950:  # yellowed paper and paste-over slips: hue + saturation relative to the paper
        fr = ((Hh >= max(pH, 23)) & (Hh <= 36) & (S >= pS + 42) & (V >= 70)) | ((Hh >= 19) & (Hh <= 36) & (S >= 125) & (V >= 70))
    else:
        fr = (Hh >= 18) & (Hh <= 38) & (S >= max(85, pS + 45)) & (V >= 80)
    split = ed in ("031", "035")
    cfg = json.load(open(CONTROL / f"{key}.json"))

    classes = {
        "frame": fr,
        "brick": ((Hh >= 158) | (Hh <= 6)) & (S >= 45) & (V >= 60),
        "stone": (Hh >= 80) & (Hh <= 130) & (S >= 35) & (V >= 60),
        "fireproof": (Hh >= 5) & (Hh <= (18 if split else 15)) & (S >= (90 if split else 115)) & (V >= 50),
        "iron": ((Hh >= 17) & (Hh <= 28) & (S <= 31) & (V >= 115) & (V <= 146) & (dV <= -4))
                | ((ed in EDITION_1950) & (Hh >= 31) & (Hh <= 42) & (S >= 28) & (S <= pS - 6) & (V >= 112) & (V <= 152)),
    }
    if cfg.get("stone_low_sat"):  # 1950 paste-over slips: the blue (concrete) wash is paler (saturation 25-35)
        classes["stone"] = classes["stone"] | ((Hh >= 85) & (Hh <= 125) & (S >= 22) & (V >= 60) & (V <= pV - 20))
    if cfg.get("iron_rule") == "dark_grey":  # 1914 vol. 6 iron buildings: paper hue and saturation, 14+ darker than paper
        classes["iron"] = (Hh >= 14) & (Hh <= 32) & (S <= pS + 4) & (V <= pV - 14) & (V >= 80)
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
            if G.get("valid_poly_px") and not Polygon(G["valid_poly_px"]).contains(poly.centroid):
                continue  # part of the sheet drawn in another orientation (another key covers it)
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


# ----------------------------------------------------------------------------------------------- railway tracks
def warp_px(G, pts):
    """pixel -> UTM for a sheet: its sheet transform, or for block-wise sheets (streets drawn wider than scale) a
    rubber sheet: each block's transform inside its rectangle, inverse-distance blend of the block transforms in the
    streets between them (so a track crossing a too-wide street stays continuous)."""
    pts = np.asarray(pts, float)
    if not G.get("zones_only"):
        return apply(np.array(G["M"]), pts)
    acc, wsum = np.zeros((len(pts), 2)), np.zeros(len(pts))
    for b in G["blocks"]:
        x0, y0, x1, y1 = b["rect_px"]
        d = np.hypot(np.maximum(0, np.maximum(x0 - pts[:, 0], pts[:, 0] - x1)), np.maximum(0, np.maximum(y0 - pts[:, 1], pts[:, 1] - y1)))
        w = 1.0 / (d + 0.5) ** 4
        acc += w[:, None] * apply(np.array(b["M"]), pts)
        wsum += w
    return acc / wsum[:, None]


def in_blocks(G, pts, margin=0):
    pts = np.asarray(pts, float)
    ok = np.zeros(len(pts), bool)
    for b in G.get("blocks", []):
        x0, y0, x1, y1 = b["rect_px"]
        ok |= (pts[:, 0] >= x0 - margin) & (pts[:, 0] <= x1 + margin) & (pts[:, 1] >= y0 - margin) & (pts[:, 1] <= y1 + margin)
    return ok


def skeleton_paths(sk):
    """pixel paths between end / junction pixels of a 1-px skeleton (8-connected)."""
    H, W = sk.shape
    ys, xs = np.nonzero(sk)
    on = set(zip(ys.tolist(), xs.tolist()))
    nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    def nbrs(p):
        return [(p[0] + a, p[1] + b) for a, b in nb if (p[0] + a, p[1] + b) in on]
    deg = {p: len(nbrs(p)) for p in on}
    nodes = {p for p, d in deg.items() if d != 2}
    seen, paths = set(), []
    for n0 in nodes:
        for q in nbrs(n0):
            if (n0, q) in seen:
                continue
            path, prev, cur = [n0], n0, q
            while True:
                seen.add((prev, cur)); seen.add((cur, prev))
                path.append(cur)
                if cur in nodes:
                    break
                nx_ = [r for r in nbrs(cur) if r != prev and (cur, r) not in seen]
                if not nx_:
                    break
                prev, cur = cur, nx_[0]
            paths.append(path)
    left = on - {p for path in paths for p in path}  # loops without end or junction pixels
    while left:
        p0 = next(iter(left)); path, prev, cur = [p0], None, p0
        while True:
            nx_ = [r for r in nbrs(cur) if r != prev and r in left and r not in path]
            if not nx_:
                break
            prev, cur = cur, nx_[0]; path.append(cur)
        left -= set(path)
        paths.append(path)
    return [np.array([(x, y) for y, x in path], float) for path in paths if len(path) >= 2]


def tracks(key):
    """railway track centrelines: a track is two parallel rail lines 5.5-8.5 px (1.1-1.7 m; standard gauge 1.435 m)
    apart. Dark straight-line pixels (opening with a 15-px line in 16 orientations; drops lettering and the dashed
    water-pipe and fence lines) are paired across the gap, the paper pixels between a pair are skeletonised and
    vectorised; building fills, sheet margins and short pieces are dropped."""
    import cv2
    from shapely.geometry import LineString, MultiLineString, Polygon
    from shapely.ops import linemerge, unary_union
    from skimage.morphology import skeletonize
    G = json.load(open(INTERIM / f"{key}.M.json"))
    tcfg_path = CONTROL / f"{key}.tracks.json"
    tcfg = json.load(open(tcfg_path)) if tcfg_path.exists() else {}
    rgb = np.asarray(Image.open(G["img"]).convert("RGB"))
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    small = cv2.resize(g, None, fx=1 / 8, fy=1 / 8, interpolation=cv2.INTER_AREA)
    bg = cv2.resize(cv2.medianBlur(small.astype(np.uint8), 31), (g.shape[1], g.shape[0])).astype(np.float32)
    dark = (g < bg - 38).astype(np.uint8)
    hsv = cv2.cvtColor(cv2.medianBlur(rgb, 3), cv2.COLOR_RGB2HSV).astype(int)
    Hh, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    pm = (V > np.percentile(V, 30)) & (S < np.percentile(S, 70))
    pS = int(np.median(S[pm]))
    fill = (S > pS + 42) | (((Hh >= 80) & (Hh <= 130)) & (S >= 30)) | (((Hh >= 158) | (Hh <= 6)) & (S >= 45))
    fill = ndi.binary_dilation(ndi.binary_opening(fill, structure=np.ones((5, 5))), iterations=5)
    C = np.zeros(g.shape, bool)
    dark3 = cv2.dilate(dark, np.ones((3, 3), np.uint8))  # 1-px rails survive a slightly misaligned line opening
    for th in np.radians(np.arange(0, 180, 7.5)):
        k = np.zeros((17, 17), np.uint8)
        dx, dy = 7 * math.cos(th), 7 * math.sin(th)
        cv2.line(k, (int(round(8 - dx)), int(round(8 - dy))), (int(round(8 + dx)), int(round(8 + dy))), 1, 1)
        Lt = cv2.morphologyEx(dark3, cv2.MORPH_OPEN, k).astype(bool)
        nx_, ny_ = -math.sin(th), math.cos(th)
        for r in (3.0, 3.5, 4.0):
            ox, oy = int(round(r * nx_)), int(round(r * ny_))
            A = np.roll(np.roll(Lt, oy, axis=0), ox, axis=1)
            B = np.roll(np.roll(Lt, -oy, axis=0), -ox, axis=1)
            C |= A & B
    C &= ~dark.astype(bool) & ~fill
    m = 14
    C[:m], C[-m:], C[:, :m], C[:, -m:] = False, False, False, False
    C = ndi.binary_closing(C, structure=np.ones((3, 3)))
    lab, n = ndi.label(C)
    if n:
        sizes = ndi.sum(C, lab, range(1, n + 1))
        C = np.isin(lab, np.nonzero(sizes >= 40)[0] + 1)
    sk = skeletonize(C)
    paths = skeleton_paths(sk)
    lines = [LineString(p) for p in paths if len(p) >= 2]
    # drop skeleton barbs (short dead-end twigs), then merge through the remaining degree-2 joints
    for _ in range(2):
        ends = {}
        for ln in lines:
            for c in (ln.coords[0], ln.coords[-1]):
                ends[c] = ends.get(c, 0) + 1
        lines = [ln for ln in lines if not (ln.length < 14 and (ends[ln.coords[0]] == 1 or ends[ln.coords[-1]] == 1))]
        merged = linemerge(MultiLineString(lines)) if lines else None
        lines = list(getattr(merged, "geoms", [merged])) if merged is not None and not merged.is_empty else []
    vp = G.get("valid_px")
    clip = Polygon([[vp[0], vp[1]], [vp[2], vp[1]], [vp[2], vp[3]], [vp[0], vp[3]]]) if vp else None
    if G.get("valid_poly_px"):
        clip = Polygon(G["valid_poly_px"]) if clip is None else clip.intersection(Polygon(G["valid_poly_px"]))
    for ex in tcfg.get("exclude_px", []):  # hand-marked non-track double lines (e.g. a viaduct parapet), see the .tracks.json
        clip = (clip if clip is not None else Polygon([[0, 0], [1e5, 0], [1e5, 1e5], [0, 1e5]])).difference(Polygon(ex))
    out = []
    comp_len = {}
    if lines:
        U = unary_union(lines)
        groups = list(getattr(U.buffer(2.5), "geoms", [U.buffer(2.5)]))
        for gi, gp in enumerate(groups):
            comp_len[gi] = sum(ln.length for ln in lines if ln.intersects(gp))
    for ln in lines:
        ln = ln.simplify(0.8)
        if clip is not None:
            ln = ln.intersection(clip)
        for part in getattr(ln, "geoms", [ln]):
            if part.is_empty or part.geom_type != "LineString" or part.length < 40:
                continue
            gi = next((i for i, gp in enumerate(groups) if gp.intersects(part)), None)
            if gi is not None and comp_len[gi] < 150:  # isolated short pieces (lettering, symbols)
                continue
            (ax, ay), (bx, by) = part.coords[0], part.coords[-1]
            if (gi is not None and comp_len[gi] < 400 and min(ay, by) > 0.82 * g.shape[0]
                    and abs(math.degrees(math.atan2(by - ay, bx - ax))) % 180 in [a for a in range(0, 2)] + [179, 180]):
                continue  # the "Scale of Feet" bar (two parallel lines like a track) at the foot of the sheet
            px = np.asarray(part.coords)
            if G.get("zones_only"):
                dens = np.linspace(0, part.length, max(2, int(part.length / 4)))
                px = np.array([part.interpolate(t).coords[0] for t in dens])
                share_in = float(in_blocks(G, px, 10).mean())
            else:
                share_in = 1.0
            utm = warp_px(G, px)
            out.append({"id": f"{key}_t{len(out) + 1}", "px": np.round(px, 1).tolist(), "utm": np.round(utm, 2).tolist(),
                        "share_in_blocks": round(share_in, 2)})
    json.dump(out, open(INTERIM / f"{key}.tracks.json", "w"))
    log(key, len(out), "track lines", round(sum(LineString(t["utm"]).length for t in out)), "m")


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
    rank_c = {"high": 0, "medium": 1, "low": 2}
    for (area, year), keys in AREAS.items():
        feats, cover = [], []
        for key in keys:
            vol, sheet = key.split("_")
            sheet = sheet[:4]
            G = json.load(open(INTERIM / f"{key}.M.json"))
            kcfg = json.load(open(CONTROL / f"{key}.json"))
            if "registered_to" in kcfg:
                kcfg = json.load(open(CONTROL / f"{kcfg['registered_to']}.json"))
            residential = kcfg.get("residential", sheet in RESIDENTIAL_SHEETS)
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
                rect = Polygon([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
                if G.get("valid_poly_px"):
                    rect = rect.intersection(Polygon(G["valid_poly_px"]))
                cover.append(Polygon(apply(np.array(G["M"]), np.asarray(rect.exterior.coords))))
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
                if G.get("tie_rms"):  # tied to a neighbouring sheet: its fit error adds
                    fitq["rms"] = math.hypot(fitq.get("rms", 0), G["tie_rms"])
                cls, a = r["cls"], r["area_m2"]
                att = attrs.get(r["id"], {})
                if cls == "wharf":
                    material, use, stories, ssrc, usrc = "frame", "wharf", 0, "deck (no storeys)", "map"
                else:
                    material = {"frame": "frame", "brick": "brick", "stone": "concrete" if map_year >= 1950 else "stone",
                                "fireproof": "unknown" if map_year < 1900 else "concrete", "iron": "iron"}[cls]
                    if cls == "frame":
                        st, us = ((1, "shed") if a < 30 else (2, "dwelling") if residential and a <= 300
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
                if kcfg.get("confidence_cap") and rank_c[conf] < rank_c[kcfg["confidence_cap"]]:
                    conf = kcfg["confidence_cap"]  # e.g. scale only from the prior, or control from street labels
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


def track_cfg(key):
    """control/<key>.tracks.json: railroad named on the sheet (default + polygons), main-line polygons, exclusions;
    a 1950 sheet without its own file uses its base plate's."""
    p = CONTROL / f"{key}.tracks.json"
    if p.exists():
        return json.load(open(p))
    c = json.load(open(CONTROL / f"{key}.json"))
    if "registered_to" in c and (CONTROL / f"{c['registered_to']}.tracks.json").exists():
        t = json.load(open(CONTROL / f"{c['registered_to']}.tracks.json"))
        T = np.array(c["T"])  # base-plate polygons -> this scan's pixels
        Ti = np.linalg.inv(np.vstack([T, [0, 0, 1]]))[:2]
        mp = lambda poly: (np.asarray(poly, float) @ Ti[:, :2].T + Ti[:, 2]).tolist()
        t = dict(t)
        t["railroads"] = [dict(r, poly_px=mp(r["poly_px"])) for r in t.get("railroads", [])]
        t["main_px"] = [mp(q) for q in t.get("main_px", [])]
        t["exclude_px"] = [mp(q) for q in t.get("exclude_px", [])]
        return t
    return {}


def assemble_tracks():
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
                polys = [Polygon(apply(np.array(b["M"]), [[b["rect_px"][0], b["rect_px"][1]], [b["rect_px"][2], b["rect_px"][1]],
                                                          [b["rect_px"][2], b["rect_px"][3]], [b["rect_px"][0], b["rect_px"][3]]])) for b in G["blocks"]]
                cover = unary_union(polys).convex_hull.buffer(12)
            else:
                q = dict(n=G.get("n", 0), rms=G.get("rms", 9), max=G.get("max", 9))
                W_, H_ = Image.open(G["img"]).size
                x0, y0, x1, y1 = G.get("valid_px") or [30, 30, W_ - 30, H_ - 30]
                rect = Polygon([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
                if G.get("valid_poly_px"):
                    rect = rect.intersection(Polygon(G["valid_poly_px"]))
                cover = Polygon(apply(np.array(G["M"]), np.asarray(rect.exterior.coords)))
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
            rec = sheet_rec(key)
            tcfg = track_cfg(key)
            for t in json.load(open(INTERIM / f"{key}.tracks.json")):
                ln = LineString(t["utm"])
                px = np.asarray(t["px"])
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
                                         "volume": f"sanborn00813_{vol}", "volume_label": VOLUMES[vol][1], "sheet": rec["id"],
                                         "sheet_no": int(sheet[:4].lstrip("0") or 0), "loc_url": f"https://www.loc.gov/item/sanborn00813_{vol}/",
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
        fc = {"type": "FeatureCollection", "name": f"{area}_{year}_tracks",
              "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
              "features": [{"type": "Feature", "properties": p,
                            "geometry": rnd(mapping(shapely.transform(g, lambda c: np.column_stack(to_ll.transform(c[:, 0], c[:, 1])))))}
                           for g, p in sorted(feats, key=lambda f: f[1]["id"])]}
        json.dump(fc, open(OUT / f"{area}_{year}_tracks.geojson", "w"))
        log(area, year, len(feats), "track lines", round(sum(f[0].length for f in feats)), "m")


def all_keys():
    return [k for ks in AREAS.values() for k in ks]


def base_first(keys):
    """georeference street-controlled sheets first, then sheets tied to them, then the 1950 sheets registered onto
    their base plates."""
    cfg = {k: json.load(open(CONTROL / f"{k}.json")) for k in keys}
    reg = [k for k in keys if "registered_to" in cfg[k]]

    def ties(k):
        c = cfg[k]
        return {e["tie"] for e in c.get("points", []) + [x for b in c.get("blocks", []) for x in b["corners"]] if "tie" in e}
    order, left = [], [k for k in keys if k not in reg]
    while left:
        ready = [k for k in left if not (ties(k) & set(left))]
        if not ready:
            raise ValueError(f"circular sheet ties: {left}")
        order += ready
        left = [k for k in left if k not in ready]
    return order + reg


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
    if stage in ("all", "tracks"):
        for k in keys:
            if k.split("_")[0] not in ("008", "015", "030"):  # rail-yard areas only (Mission Bay, Potrero Point)
                tracks(k)
    if stage in ("all", "assemble"):
        assemble()
        assemble_tracks()
