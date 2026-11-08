"""Filled building symbols of a topo render -> footprints (local metres).

blobs(img, half, res, poly_xy=None, open_m=4.0, min_m2=60, thresh=100, rect=True)
 -> list of dicts {poly: [(x, y)...], area, w, l, angle}
"""
import numpy as np
import cv2


def dark_mask(img, thresh=100, gray=True):
    r, g, b = [img[:, :, i].astype(int) for i in range(3)]
    m = (r < thresh) & (g < thresh) & (b < thresh)
    if gray:
        m &= (np.abs(r - g) < 45) & (np.abs(g - b) < 45)
    return m.astype(np.uint8)


def blobs(img, half, res, poly_xy=None, open_m=4.0, min_m2=60, thresh=100, rect=True, gray=True,
          close_m=0.0, simplify_m=1.5, mask=None):
    m = dark_mask(img, thresh, gray) if mask is None else mask.astype(np.uint8)
    if poly_xy is not None:
        pm = np.zeros_like(m)
        pts = np.array([[(x + half) / res, (half - y) / res] for x, y in poly_xy], np.int32)
        cv2.fillPoly(pm, [pts], 1)
        m &= pm
    if close_m:
        k = max(1, int(round(close_m / res)))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    k = max(1, int(round(open_m / res)))
    mo = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mo, 8)
    out = []
    for i in range(1, n):
        a = stats[i, cv2.CC_STAT_AREA] * res * res
        if a < min_m2:
            continue
        comp = (lab == i).astype(np.uint8)
        cs, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(cs, key=cv2.contourArea)
        if rect:
            (cx, cy), (w, h), ang = cv2.minAreaRect(c)
            fill = a / max(w * h * res * res, 1e-6)
            if fill > 0.8:
                box = cv2.boxPoints(((cx, cy), (w, h), ang))
                pts = box
            else:
                eps = simplify_m / res
                pts = cv2.approxPolyDP(c, eps, True)[:, 0, :].astype(float)
        else:
            eps = simplify_m / res
            pts = cv2.approxPolyDP(c, eps, True)[:, 0, :].astype(float)
            (cx, cy), (w, h), ang = cv2.minAreaRect(c)
            fill = a / max(w * h * res * res, 1e-6)
        poly = [(-half + (px + 0.5) * res, half - (py + 0.5) * res) for px, py in pts]
        out.append({"poly": poly, "area": a, "w": min(w, h) * res, "l": max(w, h) * res, "fill": fill,
                    "cx": -half + (cx + 0.5) * res, "cy": half - (cy + 0.5) * res})
    return out


def outline_fill(img, half, res, poly_xy=None, thresh=110, close_m=1.0, open_m=5.0, min_m2=80):
    """Outlined (unfilled) building symbols: fill closed dark outlines, then drop thin lines."""
    m = dark_mask(img, thresh, True)
    if close_m:
        k = max(1, int(round(close_m / res)))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    filled = m.copy()
    cs, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hier is not None:
        for i, c in enumerate(cs):
            if hier[0][i][3] >= 0:          # a hole = inside of an outline
                cv2.drawContours(filled, cs, i, 1, -1)
    return blobs(img, half, res, poly_xy, open_m=open_m, min_m2=min_m2, mask=filled)
