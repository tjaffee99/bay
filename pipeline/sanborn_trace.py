"""Manual-data tool: trace building footprints from Library of Congress Sanborn sheets (Western Addition).

Not a `make` stage: it writes hand-checked data into data/manual/sanborn/ (committed).

    python pipeline/sanborn_trace.py download [KEY ...]   # LOC IIIF 50 % JPEGs -> data/raw/sanborn/
    python pipeline/sanborn_trace.py trace    [KEY ...]   # per sheet -> data/interim/sanborn/<KEY>.pkl
    python pipeline/sanborn_trace.py export               # -> data/manual/sanborn/western_addition_<year>.geojson + coverage
    python pipeline/sanborn_trace.py preview KEY [x0 y0 x1 y1]   # overlay PNG of traced outlines + storeys

KEY = row of data/manual/sanborn/sheets_western_addition.csv (e.g. 1913_0338, 1899_0289). No KEY = all rows.
Method (details and residuals in data/manual/sanborn/README_western_addition.md):
  * frame: Western Addition street grid from DataSF centrelines (each street = straight line on a common bearing,
    offset = mode of perpendicular positions); property lines = centre +- half width measured on today's assessor
    blocks (68.75 ft streets; Divisadero 82.5 ft; Van Ness 125 ft).
  * blocks on the sheet: the street network is the large connected paper region; every big non-street component is a
    (sub-)block; its 4 sides are RANSAC lines on the edge profile (moved inward by half the line width).
  * georeferencing: Sanborn blocks are drawn to scale but streets/alleys are NOT (drawn 2-3x too wide), so each
    sub-block gets its own translation while scale+rotation (similarity, or affine if clearly better) are shared per
    sheet; constraints = every sub-block side lying on a street property line; sides with residual > 1.2 m dropped.
  * footprints: pixel classes in Lab (yellow frame, pink brick, blue stone/concrete, brown fireproof, 1899 green
    'frame special'); one region per 4-connected coloured component (black lines separate buildings, dashed
    partitions and lettering do not); X-crossed buildings (diagonal shared boundaries) merged and flagged; slivers
    < 3.8 m2 merged into their largest neighbour; enclosed boxes (elevators, skylights) merged into the parent.
  * storeys: candidate marks near region corners (NCC with digit templates), classified by an SVM trained on 360
    hand-labelled crops (classes 1/2/3, 1B/2B/3B = basement, 1h = 1 1/2, n = not a mark).
Requires: opencv-python-headless, scikit-learn, scikit-image, geopandas (venv).
"""
from __future__ import annotations

import csv
import glob
import json
import math
import os
import pickle
import sys
import time
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import INTERIM, MANUAL, RAW, get_with_retry, log, session  # noqa: E402

warnings.filterwarnings("ignore")
SB = MANUAL / "sanborn"
SHEETS_CSV = SB / "sheets_western_addition.csv"
MARKS_NPZ = SB / "storey_marks_train.npz"
RAWDIR = RAW / "sanborn"
WORK = INTERIM / "sanborn"
IIIF = "https://tile.loc.gov/image-services/iiif/service:gmd:gmd436m:g4364m:g4364sm:g4364sm_{res}:{img}"
FT = 0.3048
HALF = 68.75 * FT / 2
BRG_EW = 80.548  # bearing of E-W streets (deg clockwise from north), fitted on DataSF centrelines
NS = ['VAN NESS AVE', 'FRANKLIN ST', 'GOUGH ST', 'OCTAVIA ST', 'LAGUNA ST', 'BUCHANAN ST', 'WEBSTER ST', 'FILLMORE ST',
      'STEINER ST', 'PIERCE ST', 'SCOTT ST', 'DIVISADERO ST', 'BRODERICK ST', 'BAKER ST', 'LYON ST']
EW = ['CALIFORNIA ST', 'PINE ST', 'BUSH ST', 'SUTTER ST', 'POST ST', 'GEARY ST', 'OFARRELL ST', 'ELLIS ST', 'EDDY ST',
      'TURK ST', 'GOLDEN GATE AVE', 'MCALLISTER ST', 'FULTON ST', 'GROVE ST', 'HAYES ST', 'FELL ST', 'OAK ST', 'PAGE ST', 'HAIGHT ST']
# streets whose modern centreline is not the historic one (dual carriageways, expressway): fixed from parcels
FIXED_CENTRE = {'VAN NESS AVE': (1026.55, 19.05), 'DIVISADERO ST': (-588.3, 41.25 * FT)}
WA_BBOX = (-122.4480, 37.7720, -122.4170, 37.7920)


# ----------------------------------------------------------------------------------------------- sheets / frame
def sheets():
    rows = list(csv.DictReader(open(SHEETS_CSV)))
    out = {}
    for r in rows:
        spec = dict(r)
        spec['rows'] = r['rows'].split(';'); spec['cols'] = r['cols'].split(';')
        spec['year'] = int(r['map_year']); spec['vol'] = int(r['volume'])
        spec.pop('present_cols', None)
        if r.get('present_cols'):
            spec['present_cols'] = [int(x) for x in r['present_cols'].split(';')]
        out[r['key']] = spec
    return out


class Frame:
    """u: metres along E-W streets (east), v: along N-S streets (north); origin = Fillmore x Eddy centrelines."""

    def __init__(self, d):
        self.d = d
        self.o = np.array(d['origin_utm'])
        b = math.radians(d['brg_ew'])
        self.eu = np.array([math.sin(b), math.cos(b)]); self.ev = np.array([-self.eu[1], self.eu[0]])
        from pyproj import Transformer
        self.t_fwd = Transformer.from_crs(4326, 32610, always_xy=True)
        self.t_inv = Transformer.from_crs(32610, 4326, always_xy=True)

    def utm2uv(self, x, y):
        dd = np.column_stack([np.asarray(x, float) - self.o[0], np.asarray(y, float) - self.o[1]])
        return dd @ self.eu, dd @ self.ev

    def uv2ll(self, u, v):
        p = self.o + np.outer(np.asarray(u, float), self.eu) + np.outer(np.asarray(v, float), self.ev)
        return self.t_inv.transform(p[:, 0], p[:, 1])

    def ll2uv(self, lon, lat):
        return self.utm2uv(*self.t_fwd.transform(lon, lat))

    def pl(self, street, side):
        """property-line coordinate of one side of a street (E/W -> u for N-S streets, N/S -> v for E-W streets)"""
        c = self.d['centre'][street]
        off = self.d['pl'].get(street, {}).get(side)
        if off is None or (abs(abs(off) - HALF) > 0.35 and street not in FIXED_CENTRE):
            off = HALF if side in 'EN' else -HALF
        return c + off


def build_frame():
    import geopandas as gpd
    import pandas as pd
    import shapely
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / 'frame.json'
    if path.exists():
        return Frame(json.load(open(path)))
    st = gpd.read_file(RAW / 'sf_streets' / 'page-0000.geojson')
    st = st[st.intersects(shapely.box(*WA_BBOX)) & st.layer.isin(['STREETS', 'PRIVATE', 'STREETS_PEDESTRI', 'PARKS'])].to_crs(32610)
    o = st[st.streetname == 'FILLMORE ST'].geometry.union_all().intersection(st[st.streetname == 'EDDY ST'].geometry.union_all()).centroid
    d = {'origin_utm': [o.x, o.y], 'brg_ew': BRG_EW, 'centre': {}, 'pl': {}}
    F = Frame(d)
    box = gpd.GeoSeries([shapely.box(*WA_BBOX)], crs=4326).to_crs(32610).iloc[0]
    for n in NS + EW:
        pts = []
        for g in st[st.streetname == n].geometry:
            g = g.intersection(box)
            for geom in getattr(g, 'geoms', [g]):
                if geom.is_empty or geom.length < 1: continue
                c = np.asarray(geom.coords)
                for a, b in zip(c[:-1], c[1:]):
                    L = np.hypot(*(b - a))
                    if L < 3: continue
                    ua, va = F.utm2uv([a[0]], [a[1]]); ub, vb = F.utm2uv([b[0]], [b[1]])
                    du, dv = ub[0] - ua[0], vb[0] - va[0]
                    if (n in NS and abs(du) > 0.02 * abs(dv)) or (n in EW and abs(dv) > 0.02 * abs(du)): continue
                    for t in np.arange(0, 1, 2.0 / L):
                        pts.append(((ua + t * du)[0], (va + t * dv)[0]))
        if not pts: continue
        P = np.array(pts); val = P[:, 0] if n in NS else P[:, 1]
        h, e = np.histogram(val, bins=np.arange(val.min() - 1, val.max() + 1.5, 0.5))
        k = np.argmax(np.convolve(h, np.ones(5), 'same')); mode = (e[k] + e[k + 1]) / 2
        d['centre'][n] = float(np.median(val[np.abs(val - mode) < 2.0]))
    d['centre']['GEARY ST'] = d['centre'].get('GEARY ST', 313.7)  # 1913 Geary = straight line of downtown Geary St
    for n, (c, half) in FIXED_CENTRE.items():
        d['centre'][n] = c; d['pl'][n] = {'W': -half, 'E': half}
    # property lines: today's assessor blocks (dissolved active parcels), rect-like ones only
    parts = [gpd.read_file(p, bbox=WA_BBOX) for p in sorted(glob.glob(str(RAW / 'sf_parcels' / 'page-*.geojson')))]
    pc = gpd.GeoDataFrame(pd.concat(parts), crs=4326)
    pc = pc[pc.active.astype(str).str.lower() == 'true'].to_crs(32610)
    blk = pc.dissolve('block_num').reset_index()
    rec = []
    ns = {k: v for k, v in d['centre'].items() if k in NS}; ew = {k: v for k, v in d['centre'].items() if k in EW}
    for g in blk.geometry:
        g = g.buffer(0.05).buffer(-0.05)
        if g.geom_type == 'MultiPolygon': g = max(g.geoms, key=lambda p: p.area)
        x, y = np.asarray(g.exterior.coords).T
        u, v = F.utm2uv(x, y)
        if g.area / ((u.max() - u.min()) * (v.max() - v.min())) < 0.97: continue
        for side, val, dic in [('E', u.min(), ns), ('W', u.max(), ns), ('N', v.min(), ew), ('S', v.max(), ew)]:
            n = min(dic, key=lambda s: abs(dic[s] - val))
            if abs(val - dic[n]) < 25: rec.append((n, side, val - dic[n]))
    df = pd.DataFrame(rec, columns=['street', 'side', 'off'])
    for (n, s), grp in df.groupby(['street', 'side']):
        if n not in FIXED_CENTRE and len(grp) >= 3:
            d['pl'].setdefault(n, {})[s] = float(grp.off.median())
    json.dump(d, open(path, 'w'), indent=1)
    return Frame(d)


# ----------------------------------------------------------------------------------------------- pixels / blocks
CLASS_COLS = np.array([[245, 240, 225], [0, 0, 0], [240, 220, 60], [230, 120, 140], [90, 140, 220], [150, 150, 150],
                       [190, 110, 40], [80, 180, 80]], np.uint8)
MATERIAL = {2: 'frame', 3: 'brick', 4: 'stone', 5: 'iron', 6: 'concrete', 7: 'frame'}


def classify(im):
    """0 paper, 1 ink, 2 yellow (frame), 3 pink (brick), 4 blue (stone/concrete), 6 brown (fireproof), 7 green (1899 frame special)"""
    from skimage.color import rgb2lab
    lab = rgb2lab(im.astype(np.float32) / 255.0)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    c = np.zeros(L.shape, np.uint8)
    c[(b > 27) & (a < 4) & (L > 42)] = 2
    c[(a > 7) & (L > 30) & (L < 72) & (b < 22)] = 3
    c[(b < -1.5) & (a < 3) & (L > 25) & (L < 66)] = 4
    c[(a > 6) & (b > 22) & (L > 30) & (L < 65)] = 6
    c[(a < -15) & (b < 36) & (b > 3) & (L > 35) & (L < 75)] = 7
    c[L < 36] = 1
    return c


def ransac_line(t, v, tol=1.6, iters=400, seed=0, max_slope=0.03):
    rng = np.random.default_rng(seed); n = len(t)
    if n < 10: return None
    best = (-1, None)
    for _ in range(iters):
        i, j = rng.choice(n, 2, replace=False)
        if abs(t[j] - t[i]) < n * 0.2: continue
        b = (v[j] - v[i]) / (t[j] - t[i])
        if abs(b) > max_slope: continue
        inl = np.abs(v - (v[i] - b * t[i] + b * t)) < tol
        if inl.sum() > best[0]: best = (inl.sum(), inl)
    inl = best[1]
    if inl is None: return None
    for _ in range(3):
        (a, b), *_ = np.linalg.lstsq(np.column_stack([np.ones(inl.sum()), t[inl]]), v[inl], rcond=None)
        r = v - (a + b * t); inl = np.abs(r) < tol
    return float(a), float(b), float(np.sqrt(np.mean(r[inl] ** 2))), float(inl.mean())


def find_blocks(c, min_area=60000):
    import cv2
    paper = cv2.morphologyEx((c == 0).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(paper, connectivity=4)
    street = np.isin(lab, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 0.05 * c.size])
    n, blab, st, cen = cv2.connectedComponentsWithStats((~street).astype(np.uint8), connectivity=8)
    H, W_ = c.shape
    comps = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a < min_area or x <= 2 or y <= 2 or x + w >= W_ - 3 or y + h >= H - 3 or w > 0.9 * W_ or h > 0.9 * H: continue
        if min(w, h) < 220: continue  # thin strips (park fences, pipe lines) are not lot groups
        comps.append({'id': i, 'bbox': (int(x), int(y), int(w), int(h)), 'cen': cen[i].tolist()})
    return blab, comps


def side_lines(mask, bbox, trim=0.08, inset=1.5):
    x0, y0, w, h = bbox
    sub = mask[y0:y0 + h, x0:x0 + w]
    rows = np.arange(int(h * trim), int(h * (1 - trim))); cols = np.arange(int(w * trim), int(w * (1 - trim)))
    any_r = sub[rows].any(1); any_c = sub[:, cols].any(0)
    prof = {'L': np.argmax(sub[rows], 1).astype(float), 'R': w - 1 - np.argmax(sub[rows, ::-1], 1).astype(float),
            'T': np.argmax(sub[:, cols], 0).astype(float), 'B': h - 1 - np.argmax(sub[::-1, cols], 0).astype(float)}
    res = {}
    for name in 'LRTB':
        t, ok = (rows, any_r) if name in 'LR' else (cols, any_c)
        tt, vv = t[ok].astype(float), prof[name][ok]
        fit = ransac_line(tt, vv)
        if fit is not None:
            # a block drawn joined to its neighbour (street never cut through) or with a lane: prefer the OUTER
            # straight line when it has real support (the inner one is then an alley / lane edge)
            sgn = -1 if name in 'LT' else 1
            outer = sgn * (vv - (fit[0] + fit[1] * tt)) > 100  # bays form lines only 20-40 px out; a lane ~1000+ px
            if outer.sum() >= max(0.25 * len(tt), 20):
                f2 = ransac_line(tt[outer], vv[outer])
                if f2 is not None and f2[3] * outer.sum() >= max(0.12 * len(tt), 30) and abs(f2[1] - fit[1]) < 0.005:
                    fit = f2
        if fit is None:
            res[name] = (np.nan, 0.0, np.nan, 0.0); continue
        a0, b, rms, frac = fit
        a0 += inset if name in 'LT' else -inset
        a = a0 + x0 - b * y0 if name in 'LR' else a0 + y0 - b * x0
        res[name] = (float(a), float(b), rms, frac)
    return res


def corner(lr, tb):
    a1, b1 = lr[:2]; a2, b2 = tb[:2]
    x = (a1 + b1 * a2) / (1 - b1 * b2)
    return x, a2 + b2 * x


# ----------------------------------------------------------------------------------------------- georeferencing
ORIENT = {'N-left': np.array([[0., -1.], [-1., 0.]]), 'N-up': np.array([[1., 0.], [0., -1.]]),
          'N-right': np.array([[0., 1.], [1., 0.]]), 'N-down': np.array([[-1., 0.], [0., 1.]])}


def split_groups(vals, n):
    order = np.argsort(vals); v = np.asarray(vals)[order]
    if n == 1: return np.zeros(len(v), int)
    gaps = np.argsort(np.diff(v))[::-1][:n - 1]
    return np.searchsorted(sorted(v[g] + (v[g + 1] - v[g]) / 2 for g in gaps), vals)


def assign_quads(comps, spec, F=None):
    """(r0, r1, c0, c1) per component: rows/cols it spans (a block drawn across a street that was never cut through
    spans two). Cuts between rows/cols = the largest gaps between centroids of normal-sized components."""
    nr, nc = len(spec['rows']) - 1, len(spec['cols']) - 1
    pc = spec.get('present_cols', list(range(nc))); pr = list(range(nr))
    W_ = np.array([c['bbox'][2] for c in comps], float); H_ = np.array([c['bbox'][3] for c in comps], float)
    # expected size (px at ~0.1003 m/px) of a block between two consecutive row / column streets
    blk = lambda a, b: (abs(F.d['centre'][a] - F.d['centre'][b]) - 21.0) / 0.1003
    exp_h = min(blk(spec['rows'][i], spec['rows'][i + 1]) for i in range(nr))
    exp_w = min(blk(spec['cols'][i], spec['cols'][i + 1]) for i in range(nc))
    big_h = H_ > 1.5 * exp_h; big_w = W_ > 1.5 * exp_w

    def cuts(vals, n):
        v = np.sort(vals)
        if n <= 1 or len(v) < 2: return []
        g = np.argsort(np.diff(v))[::-1][:n - 1]
        return sorted(v[i] + (v[i + 1] - v[i]) / 2 for i in g)
    cy = cuts(np.array([c['cen'][1] for c, b in zip(comps, big_h) if not b]), len(pr))
    cx = cuts(np.array([c['cen'][0] for c, b in zip(comps, big_w) if not b]), len(pc))
    for c in comps:
        x, y, w, h = c['bbox']
        r0, r1 = int(np.searchsorted(cy, y + 0.15 * h)), int(np.searchsorted(cy, y + 0.85 * h))
        c0, c1 = int(np.searchsorted(cx, x + 0.15 * w)), int(np.searchsorted(cx, x + 0.85 * w))
        c['quad'] = (pr[min(r0, len(pr) - 1)], pr[min(r1, len(pr) - 1)], pc[min(c0, len(pc) - 1)], pc[min(c1, len(pc) - 1)])


def fit_sheet(F, comps, blab, spec, kind='similarity', ext_tol=25, min_frac=0.2):
    P = ORIENT[spec['orient']]
    assign_quads(comps, spec, F)
    quads = [c['quad'] for c in comps]
    for c in comps:
        c['sides'] = s = side_lines(blab == c['id'], c['bbox'])
        c['corners'] = {'TL': corner(s['L'], s['T']), 'TR': corner(s['R'], s['T']), 'BL': corner(s['L'], s['B']), 'BR': corner(s['R'], s['B'])}

    def side_world(q, side):
        nrm = {'T': np.array([0, -1]), 'B': np.array([0, 1]), 'L': np.array([-1, 0]), 'R': np.array([1, 0])}[side]
        w = P @ nrm
        street = {'T': spec['rows'][q[0]], 'B': spec['rows'][q[1] + 1], 'L': spec['cols'][q[2]], 'R': spec['cols'][q[3] + 1]}[side]
        if abs(w[0]) > 0.5:
            ss = 'W' if w[0] > 0 else 'E'; return 'u', F.pl(street, ss), f'{street}/{ss}'
        ss = 'S' if w[1] > 0 else 'N'; return 'v', F.pl(street, ss), f'{street}/{ss}'

    obs = []
    for q in set(quads):
        idx = [i for i, qq in enumerate(quads) if qq == q]
        mid = lambda i, sd: comps[i]['sides'][sd][0] + comps[i]['sides'][sd][1] * (comps[i]['cen'][1] if sd in 'LR' else comps[i]['cen'][0])
        ext = {}
        for sd, fn in (('T', min), ('B', max), ('L', min), ('R', max)):
            vals = [mid(i, sd) for i in idx if comps[i]['sides'][sd][3] > min_frac]
            ext[sd] = fn(vals) if vals else np.nan
        for i in idx:
            comps[i]['street_sides'] = []
            for sd in 'TBLR':
                if comps[i]['sides'][sd][3] > min_frac and abs(mid(i, sd) - ext[sd]) <= ext_tol:
                    ax, val, lab = side_world(q, sd)
                    comps[i]['street_sides'].append(sd)
                    for cn in {'T': ['TL', 'TR'], 'B': ['BL', 'BR'], 'L': ['TL', 'BL'], 'R': ['TR', 'BR']}[sd]:
                        obs.append((i, comps[i]['corners'][cn], ax, val, lab, sd))
    K = len(comps)

    def solve(obs):
        npar = (2 if kind == 'similarity' else 4) + 2 * K
        A, y = [], []
        for i, p, ax, val, _, _s in obs:
            q = P @ np.asarray(p, float); row = np.zeros(npar)
            if kind == 'similarity':
                if ax == 'u': row[0], row[1] = q[0], -q[1]; row[2 + 2 * i] = 1
                else: row[0], row[1] = q[1], q[0]; row[3 + 2 * i] = 1
            else:
                if ax == 'u': row[0], row[1] = q[0], q[1]; row[4 + 2 * i] = 1
                else: row[2], row[3] = q[0], q[1]; row[5 + 2 * i] = 1
            A.append(row); y.append(val)
        A = np.array(A); y = np.array(y)
        used = (np.abs(A) > 0).any(0)
        x, *_ = np.linalg.lstsq(A[:, used], y, rcond=None)
        full = np.full(npar, np.nan); full[used] = x
        return full, A[:, used] @ x - y

    sol, res = solve(obs)
    dropped = []
    for _ in range(6):
        worst = {}
        for k, o in enumerate(obs):
            worst[(o[0], o[5])] = max(worst.get((o[0], o[5]), 0), abs(res[k]))
        if max(worst.values()) <= 1.2: break
        best = None
        for key, w in sorted(worst.items(), key=lambda kv: -kv[1])[:3]:  # try the 3 worst sides, keep the best drop
            axis = [o[2] for o in obs if (o[0], o[5]) == key][0]
            if not any(o[0] == key[0] and o[2] == axis and o[5] != key[1] for o in obs): continue
            ob2 = [o for o in obs if (o[0], o[5]) != key]
            s2, r2 = solve(ob2)
            if best is None or np.abs(r2).max() < best[0]: best = (np.abs(r2).max(), key, w, ob2, s2, r2)
        if best is None: break
        _, key, w, obs, sol, res = best
        dropped.append((key, round(float(w), 2)))
        comps[key[0]]['street_sides'] = [s for s in comps[key[0]]['street_sides'] if s != key[1]]
    if kind == 'similarity':
        S = np.array([[sol[0], -sol[1]], [sol[1], sol[0]]]); T = sol[2:].reshape(K, 2)
    else:
        S = sol[:4].reshape(2, 2); T = sol[4:].reshape(K, 2)
    return {'M': (S @ P).tolist(), 'T': T.tolist(), 'res': res.tolist(), 'dropped': dropped,
            'obs': [(int(i), list(map(float, p)), ax, float(v), lab, s) for (i, p, ax, v, lab, s) in obs]}


def georeference(F, c, spec):
    blab, comps = find_blocks(c)
    gs = fit_sheet(F, comps, blab, spec, 'similarity')
    ga = fit_sheet(F, comps, blab, spec, 'affine')
    rs, ra = np.sqrt(np.mean(np.square(gs['res']))), np.sqrt(np.mean(np.square(ga['res'])))
    Ms, Ma = np.array(gs['M']), np.array(ga['M'])
    ss = np.hypot(*Ms[:, 0])
    # affine only where both axes are constrained (some sub-block spans two streets on each axis): scales within 3 %
    ok = np.all(np.abs(np.hypot(Ma[0], Ma[1]) / ss - 1) < 0.03) and not np.isnan(np.array(ga['T'])).any()
    g = ga if (ok and ra < 0.8 * rs) else gs
    g['kind'] = 'affine' if g is ga else 'similarity'; g['rms_sim'], g['rms_aff'] = float(rs), float(ra)
    return blab, comps, g


# ----------------------------------------------------------------------------------------------- footprints
def adjacency(lab):
    pairs = {}
    for dy, dx in [(0, 1), (1, 0)]:
        A = lab[:lab.shape[0] - dy, :lab.shape[1] - dx]; B = lab[dy:, dx:]
        m = (A != B) & (A > 0) & (B > 0)
        ys, xs = np.nonzero(m)
        if len(ys) == 0: continue
        key = np.minimum(A[m], B[m]).astype(np.int64) * 10_000_000 + np.maximum(A[m], B[m])
        o = np.argsort(key); key, ys, xs = key[o], ys[o], xs[o]
        cuts = np.nonzero(np.diff(key))[0] + 1
        for ks, yy, xx in zip(np.split(key, cuts), np.split(ys, cuts), np.split(xs, cuts)):
            k = (int(ks[0] // 10_000_000), int(ks[0] % 10_000_000))
            pts = np.column_stack([yy, xx]); pairs[k] = np.vstack([pairs[k], pts]) if k in pairs else pts
    return pairs


def merge_regions(lab, small_px=380):
    import cv2
    from scipy import ndimage as ndi
    n = int(lab.max()) + 1
    parent = list(range(n))

    def f(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    xcount = np.zeros(n, int)
    for (a, b), pts in adjacency(lab).items():  # X-crossed buildings: straight diagonal shared boundaries
        if len(pts) < 8: continue
        p = pts[:, ::-1].astype(float); p -= p.mean(0)
        _, S, Vt = np.linalg.svd(p, full_matrices=False)
        ang = np.degrees(np.arctan2(Vt[0][1], Vt[0][0])) % 90
        length = 2 * np.sqrt(3) * S[0] / np.sqrt(len(p))
        if 18 < ang < 72 and length > 18 and S[1] / max(S[0], 1e-6) < 0.25:
            ra, rb = f(a), f(b)
            if ra != rb: parent[max(ra, rb)] = min(ra, rb)
            xcount[a] += 1; xcount[b] += 1
    root = np.array([f(i) for i in range(n)]); lab2 = root[lab]
    enc = np.arange(n)  # enclosed boxes -> parent
    for r, sl in enumerate(ndi.find_objects(lab2)):
        if sl is None or r == 0: continue
        sl2 = (slice(max(sl[0].start - 3, 0), sl[0].stop + 3), slice(max(sl[1].start - 3, 0), sl[1].stop + 3))
        m = lab2[sl2] == r
        if m.sum() > 6000: continue
        ring = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~m
        u = np.unique(lab2[sl2][ring])
        if len(u) == 1 and u[0] not in (0, r): enc[r] = u[0]
    for _ in range(3): enc = enc[enc]
    lab2 = enc[lab2]; root = enc[root]
    areas = np.bincount(lab2.ravel(), minlength=n)
    best = {}
    for (a, b), pts in adjacency(lab2).items():  # slivers -> neighbour with the longest shared boundary
        for s, o in [(a, b), (b, a)]:
            if 0 < areas[s] < small_px and areas[o] > areas[s] and (s not in best or len(pts) > best[s][1]):
                best[s] = (o, len(pts))
    r2 = np.arange(n)
    for s, (o, _) in best.items(): r2[s] = o
    for _ in range(3): r2 = r2[r2]
    xc = np.zeros(n, int); np.add.at(xc, root, xcount)
    xc2 = np.zeros(n, int); np.add.at(xc2, r2, xc)
    return r2[lab2], xc2


def segment(c):
    import cv2
    from skimage.segmentation import expand_labels
    n, lab = cv2.connectedComponents((c >= 2).astype(np.uint8), connectivity=4)
    areas = np.bincount(lab.ravel(), minlength=n)
    keep = np.where(areas >= 120)[0]; keep = keep[keep > 0]
    lab = np.where(np.isin(lab, keep), lab, 0)
    nb, hl, st, _ = cv2.connectedComponentsWithStats((lab == 0).astype(np.uint8), connectivity=4)
    holes = np.zeros_like(lab)
    for j in range(1, nb):  # lettering / small holes enclosed by one region
        x, y, w, h, a = st[j]
        if a > 6000: continue
        sl = (slice(max(y - 1, 0), y + h + 1), slice(max(x - 1, 0), x + w + 1))
        m = hl[sl] == j
        ring = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~m
        u = np.unique(lab[sl][ring])
        if len(u) == 1 and u[0] != 0: holes[sl][m] = u[0]
    lab = np.where(holes > 0, holes, lab)
    lab = expand_labels(lab, distance=1.6)  # to the middle of the drawn wall lines
    return merge_regions(lab)


# ----------------------------------------------------------------------------------------------- storey marks
_MARKS = None
CW_, CH_ = 46, 28


def marks_model():
    """SVM on the hand-labelled corner crops + digit templates (data/manual/sanborn/storey_marks_train.npz)."""
    global _MARKS
    if _MARKS is None:
        from sklearn.svm import SVC
        z = np.load(MARKS_NPZ)
        X, y = [], []
        for crop, lab in zip(z['crops'], z['labels']):
            for dx, dy in [(0, 0), (-2, 0), (2, 0), (0, -2), (0, 2)]:
                X.append(crop_feats(np.roll(np.roll(crop, dy, 0), dx, 1))); y.append(str(lab))
        clf = SVC(C=8, gamma='scale', probability=True, class_weight='balanced', random_state=0).fit(np.array(X), np.array(y))
        _MARKS = (clf, {k: z['tmpl_' + k] for k in ('1', '2', '3', '2B')})
    return _MARKS


def crop_feats(crop):
    import cv2
    from skimage.feature import hog
    f = crop.astype(np.float32)
    return np.concatenate([hog(f, orientations=9, pixels_per_cell=(7, 7), cells_per_block=(2, 2), feature_vector=True),
                           cv2.resize(f, (23, 14), interpolation=cv2.INTER_AREA).ravel()])


def strip_walls(ink):
    import cv2
    u = ink.astype(np.uint8)
    walls = cv2.morphologyEx(u, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))) | \
        cv2.morphologyEx(u, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25)))
    return ink & ~cv2.dilate(walls, np.ones((3, 3), np.uint8)).astype(bool)


def mark_candidates(ink, m, tmpl, th=0.38, zone=40):
    import cv2
    from scipy import ndimage as ndi
    inkc = strip_walls(ink) & m; inkf = inkc.astype(np.float32)
    best = None
    for t in tmpl.values():
        if inkf.shape[0] < t.shape[0] or inkf.shape[1] < t.shape[1]: continue
        r = cv2.matchTemplate(inkf, t.astype(np.float32), cv2.TM_CCOEFF_NORMED)
        full = np.full(inkf.shape, -1, np.float32)
        full[t.shape[0] // 2:t.shape[0] // 2 + r.shape[0], t.shape[1] // 2:t.shape[1] // 2 + r.shape[1]] = r
        best = full if best is None else np.maximum(best, full)
    if best is None: return []
    mx = ndi.maximum_filter(best, size=17)
    H, Wd = m.shape
    out = []
    for y, x in zip(*np.nonzero((best == mx) & (best >= th))):
        if not m[y, x]: continue
        row, col = m[y], m[:, x]
        l = x - np.where(~row[:x])[0].max() if (~row[:x]).any() else x
        r_ = np.where(~row[x:])[0].min() if (~row[x:]).any() else Wd - x
        t = y - np.where(~col[:y])[0].max() if (~col[:y]).any() else y
        b_ = np.where(~col[y:])[0].min() if (~col[y:]).any() else H - y
        dx, dy = min(l, r_), min(t, b_)
        if dx > zone or dy > zone: continue
        pad = np.zeros((H + 2 * CH_, Wd + 2 * CW_), bool); pad[CH_:CH_ + H, CW_:CW_ + Wd] = inkc
        out.append({'x': int(x), 'y': int(y), 'dx': int(dx), 'dy': int(dy), 'crop': pad[CH_ + y - 14:CH_ + y + 14, CW_ + x - 15:CW_ + x + 31].copy()})
    return out


DIG = {'1': (1, False, False), '2': (2, False, False), '3': (3, False, False), 'q': (1, True, False), 'w': (2, True, False),
       'e': (3, True, False), 'h': (1, False, True)}


def read_storeys(ink, m, pmin=0.55):
    clf, tmpl = marks_model()
    cs = mark_candidates(ink, m, tmpl)
    out = {'stories': None, 'basement': False, 'half': False, 'p': 0.0}
    if not cs: return out
    P = clf.predict_proba(np.array([crop_feats(c['crop']) for c in cs]))
    best = None
    for c, p in zip(cs, P):
        k = int(np.argmax(p)); lab = clf.classes_[k]
        if lab == 'n' or p[k] < pmin: continue
        score = p[k] - 0.004 * (c['dx'] + c['dy'])
        if best is None or score > best[0]: best = (score, lab, float(p[k]))
    if best:
        n, b, h = DIG[best[1]]; out.update(stories=n, basement=b, half=h, p=round(best[2], 3))
    return out


# ----------------------------------------------------------------------------------------------- use letters
_GLYPH = None


def glyph_model():
    global _GLYPH
    if _GLYPH is None:
        from sklearn.neighbors import KNeighborsClassifier
        z = np.load(MARKS_NPZ)
        X = np.array([glyph_feat(im.astype(np.float32) / 255, h, w) for im, (h, w) in zip(z['glyph_img'], z['glyph_hw'])])
        _GLYPH = KNeighborsClassifier(5).fit(X, z['glyph_cls'].astype(str))
    return _GLYPH


def glyph_feat(img, h, w):
    return np.concatenate([img.ravel(), [h / 12, w / 12, h / max(w, 1) / 3]])


def read_use(ink, m):
    """isolated 'D' -> dwelling, 'S' -> store, 'F' alone or starting a word ('Flats') -> flats; None if not read"""
    import cv2
    n, cl, st, _ = cv2.connectedComponentsWithStats((ink & m).astype(np.uint8), connectivity=8)
    gl = []
    for j in range(1, n):
        x, y, w, h, a = st[j]
        comp = cl[y:y + h, x:x + w] == j
        if not m[y:y + h, x:x + w][comp].all() or not (7 <= h <= 34 and 2 <= w <= 34 and a >= 10): continue
        sz = max(h, w); pad = np.zeros((sz, sz), np.uint8)
        pad[(sz - h) // 2:(sz - h) // 2 + h, (sz - w) // 2:(sz - w) // 2 + w] = comp
        img = cv2.resize(pad * 255, (20, 20), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        gl.append({'x': x, 'y': y, 'w': w, 'h': h, 'f': glyph_feat(img, h, w)})
    if not gl: return None
    clf = glyph_model()
    P = clf.predict_proba(np.array([g['f'] for g in gl]))
    for g, p in zip(gl, P):
        k = int(np.argmax(p)); g['cls'] = clf.classes_[k]; g['p'] = float(p[k])

    def neigh(g):
        out = []
        for h in gl:
            if h is g: continue
            if min(g['y'] + g['h'], h['y'] + h['h']) - max(g['y'], h['y']) < 0.3 * min(g['h'], h['h']): continue
            if -2 <= h['x'] - (g['x'] + g['w']) <= 9 or -2 <= g['x'] - (h['x'] + h['w']) <= 9: out.append(h)
        return out
    use = None
    for g in gl:
        if g['cls'] not in ('D', 'S', 'F') or g['p'] < 0.6 or not (13 <= g['h'] <= 28): continue
        word = [h for h in neigh(g) if h['cls'] != 'x' and h['h'] > 8]
        if g['cls'] == 'F' and word: use = use or 'flats'
        elif not word: use = use or {'D': 'dwelling', 'S': 'store', 'F': 'flats'}[g['cls']]
    return use


# ----------------------------------------------------------------------------------------------- per sheet
def image_path(spec):
    return RAWDIR / spec['loc_item'] / f"{spec['image_id']}.jpg"


def download(keys):
    s = session()
    S = sheets()
    for k in keys:
        spec = S[k]; p = image_path(spec)
        if p.exists() and p.stat().st_size > 100_000: continue
        p.parent.mkdir(parents=True, exist_ok=True)
        url = IIIF.format(res=spec['resource'], img=spec['image_id']) + '/full/pct:50/0/default.jpg'
        r = get_with_retry(s, url)
        p.write_bytes(r.content); log(k, len(r.content) // 1024, 'KB')


def trace(key, F=None):
    import cv2
    from PIL import Image
    from scipy import ndimage as ndi
    F = F or build_frame()
    spec = sheets()[key]
    t0 = time.time()
    im = np.asarray(Image.open(image_path(spec)).convert('RGB'))
    c = classify(im)
    blab, comps, g = georeference(F, c, spec)
    lab, xcount = segment(c)
    M = np.array(g['M']); T = np.array(g['T'])
    ids = {cp['id']: k for k, cp in enumerate(comps)}
    feats = []
    for rid, sl in enumerate(ndi.find_objects(lab), start=1):
        if sl is None: continue
        m = lab[sl] == rid
        if m.sum() < 150: continue
        bl = blab[sl][m]; bl = bl[np.isin(bl, list(ids))]
        if len(bl) >= 0.5 * m.sum():
            ci = ids[int(np.bincount(bl).argmax())]
        else:  # outside every detected block (gap in an outline): nearest block within 150 px
            cy, cx = ndi.center_of_mass(m); cy += sl[0].start; cx += sl[1].start
            d = [(max(b[0] - cx, 0, cx - b[0] - b[2]) + max(b[1] - cy, 0, cy - b[1] - b[3]), k) for k, b in ((k, cp['bbox']) for k, cp in enumerate(comps))]
            d = [x for x in d if x[0] < 150]
            if not d: continue
            ci = min(d)[1]
        if np.isnan(T[ci]).any(): continue
        cnt = np.bincount(c[sl][m], minlength=8)
        mat = int(np.argmax(cnt[2:8]) + 2)
        cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        ap = np.asarray(cv2.approxPolyDP(max(cs, key=cv2.contourArea), 1.4, True)).reshape(-1, 2).astype(float)
        if len(ap) < 3: continue
        ap[:, 0] += sl[1].start; ap[:, 1] += sl[0].start
        uv = ap @ M.T + T[ci]
        lon, lat = F.uv2ll(uv[:, 0], uv[:, 1])
        y0, x0 = max(sl[0].start - 2, 0), max(sl[1].start - 2, 0)
        ssl = (slice(y0, sl[0].stop + 2), slice(x0, sl[1].stop + 2))
        st = read_storeys(c[ssl] == 1, lab[ssl] == rid)
        st['use'] = read_use(c[ssl] == 1, lab[ssl] == rid)
        feats.append({'rid': rid, 'comp': ci, 'px': ap.tolist(), 'uv': uv.tolist(), 'll': list(zip(lon, lat)),
                      'material': MATERIAL[mat], 'special': mat == 7, 'xdiag': int(xcount[rid]), 'read': st})
    out = {'key': key, 'spec': spec, 'feats': feats, 'georef': g, 'secs': time.time() - t0,
           'comps': [{k: v for k, v in cp.items() if k in ('id', 'bbox', 'quad', 'street_sides', 'corners')} for cp in comps]}
    WORK.mkdir(parents=True, exist_ok=True)
    pickle.dump(out, open(WORK / f'{key}.pkl', 'wb'))
    res = np.abs(g['res'])
    log(f"{key}: {len(comps)} sub-blocks, {g['kind']} rms {np.sqrt(np.mean(res ** 2)):.2f} m max {res.max():.2f} m; "
        f"{len(feats)} footprints, {sum(1 for f in feats if f['read']['stories'])} storeys read; {out['secs']:.0f} s")
    return out


# ----------------------------------------------------------------------------------------------- export
def export():
    import shapely
    import shapely.ops
    from shapely.geometry import Polygon, mapping, shape
    from shapely.strtree import STRtree
    F = build_frame()
    rings = {}
    for r in csv.DictReader(open(MANUAL / 'redevelopment_areas.csv')):
        if r['area_id'] in ('wa_a1', 'wa_a2'):
            rings[r['area_id']] = Polygon([tuple(map(float, p.split())) for p in r['ring'].split(';') if p.strip()])
    inside = lambda pt: 'wa_a1' if rings['wa_a1'].contains(pt) else ('wa_a2' if rings['wa_a2'].contains(pt) else None)
    rows = []  # right-of-way strips in the grid frame
    for n in F.d['centre']:
        sides = F.d['pl'].get(n, {})
        if not sides: continue
        if n in NS: rows.append(shapely.box(F.pl(n, 'W'), -3000, F.pl(n, 'E'), 3000))
        else: rows.append(shapely.box(-3000, F.pl(n, 'S'), 3000, F.pl(n, 'N')))
    S = sheets()
    data = {}
    for year in sorted({s['year'] for s in S.values()}):
        outs = [pickle.load(open(p, 'rb')) for p in sorted(glob.glob(str(WORK / f'{year}_*.pkl')))]
        bins = [0, 12, 30, 60, 120, 250, 1e9]
        dd = {}
        for o in outs:
            for f in o['feats']:
                if f['read']['stories']:
                    dd.setdefault((f['material'], int(np.digitize(Polygon(f['uv']).area, bins))), []).append(f['read']['stories'])
        est = {k: int(round(np.median(v))) for k, v in dd.items() if len(v) >= 8}
        feats, cover = [], []
        for o in outs:
            spec, g = o['spec'], o['georef']
            M, T, res, obs = np.array(g['M']), np.array(g['T']), np.array(g['res']), g['obs']
            rms = g['rms_aff'] if g['kind'] == 'affine' else g['rms_sim']
            for ci, cp in enumerate(o['comps']):
                if np.isnan(T[ci]).any(): continue
                uv = np.array([cp['corners'][k] for k in ('TL', 'TR', 'BR', 'BL')]) @ M.T + T[ci]
                poly = Polygon(list(zip(*F.uv2ll(uv[:, 0], uv[:, 1]))))
                if inside(poly.centroid) is None: continue
                r_ci = [abs(res[k]) for k, ob in enumerate(obs) if ob[0] == ci]
                q, rr, cc = cp['quad'], spec['rows'], spec['cols']  # (r0, r1, c0, c1)
                cover.append({'type': 'Feature', 'geometry': mapping(poly), 'properties': {
                    'map_year': year, 'volume': spec['vol'], 'sheet': spec['image_id'], 'loc_item': spec['loc_item'],
                    'block': f"{rr[q[0]].title()}-{rr[q[1] + 1].title()} x {cc[q[2]].title()}-{cc[q[3] + 1].title()}",
                    'area_id': inside(poly.centroid), 'street_sides': ''.join(cp.get('street_sides', [])), 'georef': g['kind'],
                    'res_rms_m': round(float(np.sqrt(np.mean(np.square(r_ci)))), 2) if r_ci else None,
                    'res_max_m': round(float(max(r_ci)), 2) if r_ci else None}})
            for f in o['feats']:
                P = shapely.make_valid(Polygon(f['ll']))
                if P.geom_type != 'Polygon':
                    P = max((p for p in getattr(P, 'geoms', [P]) if p.geom_type == 'Polygon'), key=lambda p: p.area, default=None)
                    if P is None: continue
                area_id = inside(P.centroid)
                if area_id is None: continue
                Puv = shapely.make_valid(Polygon(f['uv'])); a = Puv.area
                if a < 1.0: continue
                r = f['read']; stable = f['xdiag'] >= 4
                if r['stories']:
                    st, src = int(r['stories']), 'read'
                else:
                    st = 1 if stable else est.get((f['material'], int(np.digitize(a, bins))), 1 if a < 30 else 2)
                    src = 'estimated'
                nside = len(o['comps'][f['comp']].get('street_sides', []))
                gconf = 'high' if (nside >= 3 and rms <= 0.6) else ('medium' if nside >= 2 else 'low')
                P = shapely.set_precision(P, 1e-6)
                if P.geom_type != 'Polygon':
                    P = max((p for p in getattr(P, 'geoms', [P]) if p.geom_type == 'Polygon'), key=lambda p: p.area, default=None)
                    if P is None: continue
                feats.append({'type': 'Feature', 'geometry': mapping(P), 'properties': {
                    'map_year': year, 'volume': spec['vol'], 'sheet': spec['image_id'], 'loc_item': spec['loc_item'],
                    'stories': st, 'material': f['material'], 'use': 'stable' if stable else (r.get('use') or 'other'),
                    'use_source': 'x_symbol' if stable else ('read' if r.get('use') else 'not_read'), 'stories_source': src,
                    'confidence': gconf if src == 'read' else ('medium' if gconf == 'high' else gconf),
                    'basement': bool(r['basement']) if src == 'read' else None, 'half_storey': bool(r['half']) if src == 'read' else None,
                    'stories_p': r['p'] if src == 'read' else None, 'frame_special': bool(f['special']) if year < 1900 else None,
                    'area_m2': round(a, 1), 'area_id': area_id,
                    'row_overlap_m2': round(sum(Puv.intersection(rp).area for rp in rows), 2)}})
        data[year] = (feats, cover)
        log(year, len(feats), 'footprints,', len(cover), 'sub-blocks')
    years = sorted(data)
    for a in years:  # presence in the other edition(s), where those cover the spot
        for b in years:
            if a == b: continue
            gb = [shape(f['geometry']) for f in data[b][0]]; tree = STRtree(gb)
            covb = shapely.union_all([shape(c['geometry']) for c in data[b][1]]).buffer(1e-5)
            for f in data[a][0]:
                g = shape(f['geometry'])
                if not covb.contains(g.centroid):
                    f['properties'][f'seen_{b}'] = None; continue
                best = max([g.intersection(gb[j]).area / g.union(gb[j]).area for j in tree.query(g)] or [0.0])
                f['properties'][f'seen_{b}'] = bool(best >= 0.3); f['properties'][f'seen_{b}_iou'] = round(best, 2)
    try:  # still standing today? best IoU with today's footprint (data/interim/sf_buildings.fgb, `make sf`)
        import geopandas as gpd
        mod = gpd.read_file(INTERIM / 'sf_buildings.fgb', bbox=WA_BBOX)
        mod = mod[mod.geometry.notna()].to_crs(32610).reset_index(drop=True)
        mt = STRtree(list(mod.geometry.values))
        tf = F.t_fwd.transform
        for y in years:
            for f in data[y][0]:
                g = shapely.ops.transform(tf, shape(f['geometry']))
                best, bj = 0.0, None
                for j in mt.query(g):
                    h = mod.geometry.values[j]; iou = g.intersection(h).area / g.union(h).area
                    if iou > best: best, bj = iou, j
                f['properties']['today_iou'] = round(best, 2)
                if bj is not None and best >= 0.3:
                    f['properties']['today_bldg'] = str(mod.sf16_bldgid.values[bj])
                    f['properties']['today_start_year'] = round(float(mod.start_year.values[bj]), 1)
                    f['properties']['today_year_confidence'] = str(mod.year_confidence.values[bj])
    except Exception as e:  # noqa: BLE001
        log('today match skipped:', e)
    SB.mkdir(parents=True, exist_ok=True)
    for y in years:
        feats = data[y][0]
        for i, f in enumerate(feats):
            f['properties'] = {'id': f'sb{y}_{i:05d}', **f['properties']}
        json.dump({'type': 'FeatureCollection', 'name': f'western_addition_{y}', 'features': feats},
                  open(SB / f'western_addition_{y}.geojson', 'w'), separators=(',', ':'))
    json.dump({'type': 'FeatureCollection', 'name': 'western_addition_coverage', 'features': [c for y in years for c in data[y][1]]},
              open(SB / 'western_addition_coverage.geojson', 'w'), separators=(',', ':'))


def preview(key, crop=None):
    from PIL import Image, ImageDraw
    o = pickle.load(open(WORK / f'{key}.pkl', 'rb'))
    im = Image.open(image_path(o['spec'])).convert('RGB'); d = ImageDraw.Draw(im)
    for f in o['feats']:
        d.line([tuple(p) for p in f['px']] + [tuple(f['px'][0])], fill=(255, 0, 0), width=2)
        r = f['read']; s = (str(r['stories']) + ('B' if r['basement'] else '')) if r['stories'] else '?'
        cx, cy = np.mean(np.array(f['px']), 0)
        d.text((cx - 6, cy - 6), s + ('X' if f['xdiag'] >= 4 else ''), fill=(0, 0, 255) if r['stories'] else (255, 0, 255))
    if crop: im = im.crop(crop)
    p = WORK / f'preview_{key}.png'; im.save(p); log('wrote', p)


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    keys = [a for a in args if not a.lstrip('-').isdigit()] or list(sheets())
    if cmd == 'download': download(keys)
    elif cmd == 'trace':
        F = build_frame()
        for k in keys: trace(k, F)
    elif cmd == 'export': export()
    elif cmd == 'preview': preview(args[0], tuple(map(int, args[1:5])) if len(args) >= 5 else None)
    else: raise SystemExit(__doc__)
