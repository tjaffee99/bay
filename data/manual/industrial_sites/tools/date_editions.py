"""Date today's footprints of a site by the USGS topo editions that first draw them.

presence(site_ll, fps, eds, res24=2.0) -> DataFrame (one row per footprint x edition):
    fid, year, scale, sheet, covered, score, present

For every edition (editions.editions) the site is resampled into its local metre frame
(vt.render_topo: sheet registration + NADCON). Ink = dark grey ink (+ the magenta of
photorevisions). A footprint is *covered* when the sheet's map face is under it, and
*present* when
  * buildings: the ink, opened by ~6 m (drops roads, rail, lettering), covers >= 30 %
    (1:24k; 20 % on 1:62,500, whose symbols are not to scale) of the footprint buffered by
    the registration tolerance (6 m / 15 m), or
  * tanks (round footprints): a filled circle (>= 35 %) or an open circle: ink on >= 35 %
    of the rim band (radius +- tolerance).
First edition drawing it, last earlier covered edition not drawing it -> start year
(midpoint), see `start_years`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vanished_sites" / "tools"))
import vt  # noqa: E402

TOL = {24000: 6.0, 31680: 10.0, 62500: 15.0, 125000: 30.0}
RES = {24000: 2.0, 31680: 3.0, 62500: 4.0, 125000: 8.0}
THR = {24000: 0.30, 31680: 0.25, 62500: 0.20, 125000: 0.2}


def ink(img, purple):
    r, g, b = (img[:, :, i].astype(int) for i in range(3))
    m = (r < 115) & (g < 115) & (b < 115) & (np.abs(r - g) < 40) & (np.abs(g - b) < 40)
    if purple:
        m |= ((r - g) > 38) & ((b - g) > 18) & (g < 175)
    return m.astype(np.uint8)


def presence(site_ll, fps, eds, max_half=4000.0, log=print):
    c = site_ll.centroid
    cx, cy = c.x, c.y
    x0, y0 = vt.ll2loc(site_ll.bounds[0], site_ll.bounds[1], cx, cy)
    x1, y1 = vt.ll2loc(site_ll.bounds[2], site_ll.bounds[3], cx, cy)
    half = float(min(max_half, max(abs(x0), abs(x1), abs(y0), abs(y1)) + 120))
    # footprint rings in the local frame
    rings = []
    for gm in fps.geometry.values:
        x, y = vt.ll2loc(*np.asarray(gm.exterior.coords).T, cx, cy)
        rings.append(np.c_[x, y])
    rows = []
    cen = fps.geometry.representative_point()
    for sc, name, year, imp, kind, url, yrs in eds:
        if sc not in RES:
            continue
        res = max(RES[sc], half / 1400.0)  # <= 2800 px a side (memory)
        try:
            on_face = sheet_quad(url, sc)(cen.x.values, cen.y.values)
        except Exception as e:  # noqa: BLE001
            log(f"   skip {name} {year}: {e}")
            continue
        if not on_face.any():
            continue
        try:
            img = vt.render_topo(url, cx, cy, half, res)
        except Exception as e:  # noqa: BLE001
            log(f"   skip {name} {year}: {e}")
            continue
        n = img.shape[0]
        m = ink(img, purple=("Photo Revision" in yrs or kind == "Photo"))
        k = max(1, int(round(6.0 / res)))
        mo = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
        tol = TOL[sc]
        tp = max(1, int(round(tol / res)))
        ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * tp + 1, 2 * tp + 1))
        for fi, (ring, circ, area) in enumerate(zip(rings, fps.circ.values, fps.area_m2.values)):
            px = np.c_[(ring[:, 0] + half) / res, (half - ring[:, 1]) / res]
            if px[:, 0].max() < 0 or px[:, 1].max() < 0 or px[:, 0].min() >= n or px[:, 1].min() >= n:
                continue
            i0, j0 = int(max(0, px[:, 0].min() - 3 * tp)), int(max(0, px[:, 1].min() - 3 * tp))
            i1, j1 = int(min(n, px[:, 0].max() + 3 * tp + 1)), int(min(n, px[:, 1].max() + 3 * tp + 1))
            if i1 <= i0 or j1 <= j0:
                continue
            pm = np.zeros((j1 - j0, i1 - i0), np.uint8)
            cv2.fillPoly(pm, [np.round(px - [i0, j0]).astype(np.int32)], 1)
            if pm.sum() == 0:
                cv2.circle(pm, (int(px[:, 0].mean() - i0), int(px[:, 1].mean() - j0)), 1, 1, -1)
            if not on_face[fi]:
                continue
            pb = cv2.dilate(pm, ker)
            covered = True
            filled = mo[j0:j1, i0:i1][pb > 0].mean()
            score = float(filled)
            is_tank = circ > 0.85 and area > 40
            if is_tank:
                rim = cv2.dilate(pm, ker) - cv2.erode(pm, ker)
                rimv = m[j0:j1, i0:i1][rim > 0].mean() if rim.any() else 0
                score = float(max(filled, rimv * 0.85))
            # reprints of the older scales were often updated: a feature drawn on a reprint
            # stood by its imprint year (absence still only says something about the
            # edition's own culture year)
            pyear = imp if (sc != 24000 and imp and imp > year) else year
            rows.append((fi, year, pyear, sc, name, bool(covered), round(score, 3), score >= THR[sc]))
        log(f"   {name} {year}: {sum(1 for r in rows if r[1] == year and r[2] == (imp if (sc != 24000 and imp and imp > year) else year) and r[4] == name and r[7])} present")
    return pd.DataFrame(rows, columns=["fi", "year", "pyear", "scale", "sheet", "covered", "score", "present"])


QUAD = {24000: 0.125, 31680: 0.125, 62500: 0.25, 125000: 0.5}


def sheet_quad(url, sc):
    """The sheet's map face: its NAD27 quadrangle (7.5' / 15' / 30' cells), found by snapping
    the centre of the GeoTIFF to the quad grid; returns (inside(lon, lat) -> bool array)."""
    import rasterio
    from pyproj.enums import TransformDirection
    src = url if url.startswith("/") else "/vsicurl/" + url
    with rasterio.open(src) as r:
        t_ll, t_pr = vt.nad27_tfs(r.crs.to_wkt())
        b = r.bounds
    lo, la = t_pr.transform((b.left + b.right) / 2, (b.top + b.bottom) / 2, direction=TransformDirection.INVERSE)
    q = QUAD[sc]
    w, s = np.floor(lo / q) * q, np.floor(la / q) * q

    def inside(lon, lat):
        a, c = t_ll.transform(np.asarray(lon), np.asarray(lat))
        a, c = np.asarray(a), np.asarray(c)
        return (a >= w) & (a <= w + q) & (c >= s) & (c <= s + q)
    return inside


def start_years(pres, fps, founded, last_year=2024):
    """Per footprint: first edition drawing it (and staying drawn on most later editions),
    the last earlier edition not drawing it, and an estimated start year:
      * midpoint(last absent, first present), bounded below by the site's founding year;
      * drawn on the first edition after the founding: the founding year if that edition
        is within 15 years of it, else the midpoint of founding and that edition."""
    out = []
    for fi, t in pres.groupby("fi"):
        t = t.assign(ky=np.where(t.present, t.pyear, t.year)).sort_values(["pyear", "year"])
        per = t.groupby("pyear").present.max()
        yrs = per.index.values
        pr = per.values
        first = None
        for k, y in enumerate(yrs):
            if not pr[k]:
                continue
            later = pr[k:]
            if later.mean() >= 0.6:
                first = y
                break
        if first is None:
            out.append((fi, np.nan, np.nan, np.nan, "never drawn"))
            continue
        absent = [y for y, p in zip(t.year.values, t.present.values) if y < first and not p and y >= founded - 1]
        la = max(absent) if absent else None
        if la is not None:
            est = max(founded, (la + first) / 2.0)
            ev = f"absent {int(la)}, drawn {int(first)}"
        else:
            est = founded if first - founded <= 15 else (founded + first) / 2.0
            ev = f"drawn on the first edition after the founding ({int(first)})"
        out.append((fi, float(first), float(la) if la is not None else np.nan, round(float(est), 1), ev))
    return pd.DataFrame(out, columns=["fi", "first_drawn", "last_absent", "est_start", "evidence"]).set_index("fi")
