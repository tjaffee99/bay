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

TOL = {24000: 6.0, 31680: 15.0, 62500: 20.0, 125000: 40.0}
RES = {24000: 2.0, 31680: 3.0, 62500: 4.0, 125000: 8.0}
THR = {24000: 0.30, 31680: 0.25, 62500: 0.20, 125000: 0.2}


def ink(img, purple, dark=115):
    r, g, b = (img[:, :, i].astype(int) for i in range(3))
    m = (r < dark) & (g < dark) & (b < dark) & (np.abs(r - g) < 40) & (np.abs(g - b) < 40)
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
    road_r = {}
    cen = fps.geometry.representative_point()
    for sc, name, year, imp, kind, url, yrs in eds:
        if sc not in RES:
            continue
        res = max(RES[sc], half / 1200.0)  # <= 2400 px a side (memory)
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
        # old 1:62,500 scans: only the black culture ink (their brown contours / hachures scan darker)
        m = ink(img, purple=("Photo Revision" in yrs or kind == "Photo"), dark=115 if sc == 24000 else 90)
        k = max(1, int(round(6.0 / res)))
        mo = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
        # registration: the early 1:62,500 surveys are off by up to a few hundred metres (not on
        # NAD27 control); 1:24k sheets by a few metres. Shift the footprints onto the sheet by the
        # offset that best overlays today's footprints on the sheet's building ink (FFT correlation,
        # accepted only if clearly better than no shift)
        if sc == 24000:
            shift = (0, 0)  # 1:24k sheets fit today's streets within a few metres (vanished-sites checks)
        else:
            if res not in road_r:
                road_r[res] = road_raster(cx, cy, half, res, n)
            shift = align_roads(img, road_r[res], res, ALIGN_M[sc], n)
        tol = TOL[sc]
        tp = max(1, int(round(tol / res)))
        ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * tp + 1, 2 * tp + 1))
        for fi, (ring, circ, area) in enumerate(zip(rings, fps.circ.values, fps.area_m2.values)):
            px = np.c_[(ring[:, 0] + half) / res + shift[0], (half - ring[:, 1]) / res + shift[1]]
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
            if sc != 24000:
                # 1:62,500 / 1:31,680 symbols are not to scale and sit up to the tolerance off:
                # drawn when a building symbol of at least half the footprint (max ~300 m2) lies
                # within the tolerance; score = ink area / that minimum
                need = min(0.5 * area, 300.0) / (res * res)
                score = float(mo[j0:j1, i0:i1][pb > 0].sum() / max(need, 1.0)) * THR[sc]
            is_tank = circ > 0.85 and area > 40
            if is_tank:
                rim = cv2.dilate(pm, ker) - cv2.erode(pm, ker)
                rimv = m[j0:j1, i0:i1][rim > 0].mean() if rim.any() else 0
                score = float(max(filled, rimv * 0.85))
            # reprints of the older scales were often updated: a feature drawn on a reprint
            # stood by its imprint year (absence still only says something about the
            # edition's own culture year)
            pyear = imp if (sc != 24000 and imp and imp > year) else year
            rows.append((fi, year, pyear, sc, name, bool(covered), round(score, 3), score >= THR[sc],
                         round(shift[0] * res, 1), round(-shift[1] * res, 1)))
        log(f"   shift {shift[0] * res:+.0f} E {-shift[1] * res:+.0f} N m;")
        log(f"   {name} {year}: {sum(1 for r in rows if r[1] == year and r[2] == (imp if (sc != 24000 and imp and imp > year) else year) and r[4] == name and r[7])} present")
    return pd.DataFrame(rows, columns=["fi", "year", "pyear", "scale", "sheet", "covered", "score", "present",
                                       "shift_e_m", "shift_n_m"])


ALIGN_M = {24000: 30.0, 31680: 150.0, 62500: 350.0, 125000: 600.0}


def road_raster(cx, cy, half, res, n):
    """Today's streets and railways (Overture) rasterised in the site frame (blurred)."""
    import shapely.wkb
    rr = np.zeros((n, n), np.uint8)
    for rid, cls, g in vt.roads_local(cx, cy, half):
        if cls in ("motorway", "trunk", "footway", "service", "path", "cycleway", "steps"):
            continue
        ln = shapely.wkb.loads(bytes(g))
        for part in getattr(ln, "geoms", [ln]):
            x, y = vt.ll2loc(*np.asarray(part.coords).T, cx, cy)
            pts = np.c_[(x + half) / res, (half - y) / res].astype(np.int32)
            cv2.polylines(rr, [pts], False, 1, max(1, int(6 / res)))
    return cv2.GaussianBlur(rr.astype(np.float32), (0, 0), 3 / res)


def align_roads(img, rrf, res, max_m, n):
    """Pixel shift (dx, dy) of the sheet's ink against today's streets (FFT correlation, as the
    vanished-sites align.py); (0, 0) unless the correlation peak is clear."""
    r, g, b = (img[:, :, i].astype(int) for i in range(3))
    inkf = cv2.GaussianBlur(((r < 150) & (g < 150) & (b < 150)).astype(np.float32), (0, 0), 3 / res)
    if rrf.sum() < 50:
        return (0, 0)
    F = np.fft.rfft2(inkf - inkf.mean())
    G = np.fft.rfft2(rrf - rrf.mean())
    c = np.fft.fftshift(np.fft.irfft2(F * np.conj(G), s=inkf.shape))
    ms = int(max_m / res)
    ctr = n // 2
    win = c[ctr - ms:ctr + ms + 1, ctr - ms:ctr + ms + 1]
    j, i = np.unravel_index(np.argmax(win), win.shape)
    ratio = float(win.max() / (np.abs(win).mean() + 1e-9))
    if ratio < 4.0:
        return (0, 0)
    return (int(i - ms), int(j - ms))


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
    pres = pres[pres.scale.isin([24000, 31680, 62500])]  # 1:125,000 symbols are too coarse to date a footprint
    for fi, t in pres.groupby("fi"):
        t = t.sort_values(["pyear", "year"])
        per = t.groupby("pyear").present.max()
        cul = t.groupby("year").present.max()  # one vote per culture year (reprints are not independent)
        yrs = per.index.values
        pr = per.values
        first = None
        for k, y in enumerate(yrs):
            if not pr[k]:
                continue
            y_cult = t[(t.pyear == y) & t.present].year.min()
            later = cul[cul.index >= y_cult].values
            if later.mean() >= 0.6 and (len(later) >= 2 or y_cult == cul.index.max()):
                first = y
                break
        if first is None:
            out.append((fi, np.nan, np.nan, np.nan, "never drawn", np.nan))
            continue
        last = float(per[per].index.max())  # latest edition (print year) still drawing it
        absent = [y for y, p in zip(t.year.values, t.present.values) if y < first and not p and y >= founded - 1]
        la = max(absent) if absent else None
        if la is not None:
            est = max(founded, (la + first) / 2.0)
            ev = f"absent {int(la)}, drawn {int(first)}"
        else:
            est = founded if first - founded <= 15 else (founded + first) / 2.0
            ev = f"drawn on the first edition after the founding ({int(first)})"
        out.append((fi, float(first), float(la) if la is not None else np.nan, round(float(est), 1), ev, last))
    return pd.DataFrame(out, columns=["fi", "first_drawn", "last_absent", "est_start", "evidence",
                                      "last_drawn"]).set_index("fi")
