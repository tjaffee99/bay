"""Pavement test on topo editions: is a line (runway / taxiway centreline) inside a drawn
pavement corridor?

On the 1:24,000 sheets an airfield's pavement is the white space between closed outlines of
the unpaved "islands" (black, purple on photorevisions). Along the centreline, every few
metres: `x` = ink at the centre (the line crosses an island outline or an end line), `~` water
tint at the centre, `#` = clear centre with ink on both sides within DMAX (inside a corridor),
`.` = clear with no ink on at least one side (open ground, outside the airfield, or an apron).

  python -I corridor.py CX CY RES TODAY.geojson NAME=IMG.npy ... [--ids a,b] [--step 25]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import shape, LineString

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vanished_sites" / "tools"))
import vt  # noqa: E402


def masks(img):
    f = img.astype(np.int16)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    dark = (r + g + b) < 3 * 150
    purple = (r - g > 50) & (b - g > 40)                     # photorevision overprint
    water = (b - r > 25) & (g - r > 5) & ~dark               # blue / cyan water tint
    return dark | purple, water


def sample(line_xy, step):
    ln = LineString(line_xy)
    d = np.arange(0, ln.length + 1e-6, step)
    pts = np.array([ln.interpolate(v).coords[0] for v in d])
    # unit normals
    tang = np.array([np.subtract(ln.interpolate(min(v + 1, ln.length)).coords[0],
                                 ln.interpolate(max(v - 1, 0)).coords[0]) for v in d])
    tang /= np.linalg.norm(tang, axis=1, keepdims=True) + 1e-9
    nrm = np.stack([-tang[:, 1], tang[:, 0]], 1)
    return d, pts, nrm


def classify(ink, water, H, res, pts, nrm, dmax=110.0, centre=3.0):
    n = ink.shape[0]

    def at(m, xy):
        c = np.clip(((xy[..., 0] + H) / res).astype(int), 0, n - 1)
        r = np.clip(((H - xy[..., 1]) / res).astype(int), 0, n - 1)
        return m[r, c]
    out = []
    offs = np.arange(-centre, centre + 0.01, res / 2)
    rays = np.arange(centre + res, dmax, res / 2)
    tg = np.stack([nrm[:, 1], -nrm[:, 0]], 1)
    for p, nv, t in zip(pts, nrm, tg):
        # centre: a small cross (along the normal and the tangent)
        cc = np.concatenate([p + offs[:, None] * nv, p + offs[:, None] * t])
        if at(ink, cc).any():
            out.append("x"); continue
        if at(water, p[None])[0]:
            out.append("~"); continue
        left = at(ink, p + rays[:, None] * nv).any()
        right = at(ink, p - rays[:, None] * nv).any()
        out.append("#" if left and right else ".")
    return "".join(out)


def main():
    a = [s for s in sys.argv[1:] if not s.startswith("--")]
    opt = {s.split("=")[0]: s.split("=", 1)[1] for s in sys.argv[1:] if s.startswith("--") and "=" in s}
    cx, cy, res = map(float, a[0:3])
    feats = json.loads(Path(a[3]).read_text())["features"]
    eds = []
    for spec in a[4:]:
        name, _, f = spec.partition("=")
        img = np.load(f)
        ink, water = masks(img)
        eds.append((name, ink, water, img.shape[0] * res / 2))
    ids = opt.get("--ids", "").split(",") if opt.get("--ids") else None
    step = float(opt.get("--step", 25))
    for f in feats:
        p = f["properties"]
        if ids and not any(p["id"].startswith(i) for i in ids):
            continue
        g = shape(f["geometry"])
        if g.geom_type != "LineString":
            continue
        x, y = vt.ll2loc(*np.asarray(g.coords).T, cx, cy)
        d, pts, nrm = sample(np.column_stack([x, y]), step)
        print(f"{p['id'][:8]} {p['class'][:7]:7s} {p.get('name') or '':10s} {round(d[-1]):5d} m")
        for name, ink, water, H in eds:
            print(f"   {name:6s} {classify(ink, water, H, res, pts, nrm)}")


if __name__ == "__main__":
    main()
