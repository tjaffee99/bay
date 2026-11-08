"""Geometry helpers for tracing (local metre frames)."""
import numpy as np
import shapely
from shapely.geometry import Polygon, MultiPolygon, LineString, Point
from shapely import affinity


def orthogonalize(poly, angle_deg=0.0, min_edge=1.0):
    """Snap a roughly rectilinear polygon to edges parallel/perpendicular to angle_deg
    (degrees, counter-clockwise from the x axis)."""
    if poly.is_empty:
        return poly
    p = affinity.rotate(poly, -angle_deg, origin=(0, 0))
    xy = np.asarray(p.exterior.coords)[:-1]
    n = len(xy)
    if n < 4:
        return poly
    # classify edges
    edges = []
    for i in range(n):
        a, b = xy[i], xy[(i + 1) % n]
        d = b - a
        L = np.hypot(*d)
        if L < 1e-9:
            continue
        o = "H" if abs(d[0]) >= abs(d[1]) else "V"
        edges.append([o, a, b, L])
    # merge consecutive same-orientation edges (weighted)
    merged = []
    for e in edges:
        if merged and merged[-1][0] == e[0]:
            m = merged[-1]
            m[2] = e[2]
            m[3] += e[3]
            m.append(e)
        else:
            merged.append(list(e))
    if len(merged) > 1 and merged[0][0] == merged[-1][0]:
        last = merged.pop()
        merged[0][1] = last[1]
        merged[0][3] += last[3]
    if len(merged) < 4 or len(merged) % 2:
        return poly
    # level per edge: weighted mean coordinate
    lv = []
    for o, a, b, L, *rest in merged:
        if o == "H":
            lv.append(("H", (a[1] + b[1]) / 2))
        else:
            lv.append(("V", (a[0] + b[0]) / 2))
    pts = []
    m = len(lv)
    for i in range(m):
        o1, v1 = lv[i]
        o2, v2 = lv[(i + 1) % m]
        if o1 == o2:
            continue
        pts.append((v2, v1) if o1 == "H" else (v1, v2))
    if len(pts) < 4:
        return poly
    q = Polygon(pts)
    if not q.is_valid:
        q = q.buffer(0)
    q = affinity.rotate(q, angle_deg, origin=(0, 0))
    if isinstance(q, MultiPolygon):
        q = max(q.geoms, key=lambda g: g.area)
    return q


def clean_rect(poly, angle_deg=0.0, tol=1.5, close=2.0):
    """Close small notches, simplify, orthogonalize."""
    p = poly.buffer(close, join_style=2).buffer(-close, join_style=2)
    p = p.buffer(-close / 2, join_style=2).buffer(close / 2, join_style=2)
    if isinstance(p, MultiPolygon):
        p = max(p.geoms, key=lambda g: g.area)
    p = p.simplify(tol)
    return orthogonalize(p, angle_deg)


def stadium(u, v, a_deg, L, R, step=3.0):
    """Stadium polygon: centre (u, v), axis bearing a (deg clockwise from north), half straight L, radius R."""
    t = np.radians(a_deg)
    ax, ay = np.sin(t), np.cos(t)
    nx, ny = ay, -ax       # to the right of the axis
    pts = []
    nst = max(2, int(2 * L / step))
    narc = max(12, int(np.pi * R / step))
    for s in np.linspace(-L, L, nst, endpoint=False):
        pts.append((s, R))
    for th in np.linspace(np.pi / 2, -np.pi / 2, narc, endpoint=False):
        pts.append((L + R * np.cos(th), R * np.sin(th)))
    for s in np.linspace(L, -L, nst, endpoint=False):
        pts.append((s, -R))
    for th in np.linspace(-np.pi / 2, -3 * np.pi / 2, narc, endpoint=False):
        pts.append((-L + R * np.cos(th), R * np.sin(th)))
    pts = np.array(pts)
    x = u + pts[:, 0] * ax + pts[:, 1] * nx
    y = v + pts[:, 0] * ay + pts[:, 1] * ny
    return Polygon(np.column_stack([x, y])).buffer(0)


def axis_rect(u, v, a_deg, s0, s1, n0, n1):
    """Rectangle in a stadium/axis frame: s along the axis (bearing a), n to the right."""
    t = np.radians(a_deg)
    ax, ay = np.sin(t), np.cos(t)
    nx, ny = ay, -ax
    c = [(s0, n0), (s1, n0), (s1, n1), (s0, n1)]
    return Polygon([(u + s * ax + n * nx, v + s * ay + n * ny) for s, n in c])
