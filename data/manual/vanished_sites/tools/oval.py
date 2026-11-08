"""Fit a stadium (two semicircles joined by straights) to dark line pixels of a topo render.

python -I oval.py TIF CX CY HALF RES  x0 x1 y0 y1  [thresh]  -> prints fit (local metres)
Stadium params: centre (u, v), axis bearing a (deg, clockwise from north), half straight L, radius R.
"""
import sys
import numpy as np
from scipy.optimize import least_squares
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import vt


def stadium_dist(p, x, y):
    u, v, a, L, R = p
    t = np.radians(a)
    ax, ay = np.sin(t), np.cos(t)          # axis direction
    dx, dy = x - u, y - v
    s = dx * ax + dy * ay                   # along axis
    n = -dx * ay + dy * ax                  # across
    sc = np.clip(s, -L, L)
    return np.hypot(s - sc, n) - R


def stadium_ring(p, step=4.0, dR=0.0):
    u, v, a, L, R = p
    R = R + dR
    t = np.radians(a)
    ax, ay = np.sin(t), np.cos(t)
    nx, ny = -ay, ax
    pts = []
    # right straight (n = -R ... ) go round: start at s=-L, n=+R? build param
    nst = max(2, int(2 * L / step))
    narc = max(8, int(np.pi * R / step))
    for s in np.linspace(-L, L, nst, endpoint=False):
        pts.append((s, -R))
    for th in np.linspace(-np.pi / 2, np.pi / 2, narc, endpoint=False):
        pts.append((L + R * np.cos(th), R * np.sin(th)))
    for s in np.linspace(L, -L, nst, endpoint=False):
        pts.append((s, R))
    for th in np.linspace(np.pi / 2, 3 * np.pi / 2, narc, endpoint=False):
        pts.append((-L + R * np.cos(th), R * np.sin(th)))
    pts = np.array(pts + [pts[0]])
    x = u + pts[:, 0] * ax + pts[:, 1] * nx
    y = v + pts[:, 0] * ay + pts[:, 1] * ny
    return x, y


def dark_points(img, half, res, box, thresh=110, gray=True):
    r, g, b = [img[:, :, i].astype(int) for i in range(3)]
    m = (r < thresh) & (g < thresh) & (b < thresh)
    if gray:
        m &= (np.abs(r - g) < 40) & (np.abs(g - b) < 40)
    j, i = np.nonzero(m)
    x = -half + (i + 0.5) * res
    y = half - (j + 0.5) * res
    x0, x1, y0, y1 = box
    k = (x > x0) & (x < x1) & (y > y0) & (y < y1)
    return x[k], y[k]


def fit(x, y, p0, iters=4, keep=6.0):
    p = np.array(p0, float)
    sel = np.ones(len(x), bool)
    for _ in range(iters):
        r = least_squares(lambda q: stadium_dist(q, x[sel], y[sel]), p, loss="soft_l1", f_scale=2.0)
        p = r.x
        d = np.abs(stadium_dist(p, x, y))
        sel = d < keep
    return p, d, sel


if __name__ == "__main__":
    tif, cx, cy, half, res = sys.argv[1], *map(float, sys.argv[2:6])
    box = list(map(float, sys.argv[6:10]))
    th = float(sys.argv[10]) if len(sys.argv) > 10 else 110
    img = vt.render_topo(tif, cx, cy, half, res)
    x, y = dark_points(img, half, res, box, th)
    print(len(x), "dark px")
