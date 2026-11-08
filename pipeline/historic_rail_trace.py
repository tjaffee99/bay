"""Historic railways, interurbans and rail piers: geometry + dates (tool, not a build stage).

Writes data/manual/historic_rail.geojson (one LineString per dated segment) from the
route specifications in data/manual/historic_rail_spec.py. Each route is a sequence of
*pieces*, each with its own geometry method, best source first:

  rail   shortest path between waypoints on today's tracks and mapped grades
         (Overture rail = OpenStreetMap railway ways incl. is_abandoned / is_disused,
         plus Overpass extracts of railway=abandoned|razed|disused ways when available)
  road   shortest path on Overture/OSM road centrelines (street-running lines)
  topo   least-cost path along the black ink of a USGS historical topographic sheet
         (1:62,500, c. 1895-1919) between waypoints, inside a corridor around them; the
         sheet's own GeoPDF registration + NADCON + the local offset of the early survey
         against today's roads (topo_farmsteads.road_alignment), then smoothed
  pts    hand-placed waypoints (Chaikin-smoothed) - LOW confidence, said so in the note

Output vertices are densified to <= 20 m (curves stay round when draped).

Usage: python historic_rail_trace.py build            -> data/manual/historic_rail.geojson
       python historic_rail_trace.py view KEY W S E N  -> debug PNG (topo warped to today's
                                                          frame + overlays) for placing waypoints
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import INTERIM, MANUAL, RAW, download_file, log  # noqa: E402

OVERTURE = RAW / "overture" / "2026-10-21.0"
TOPO_DIR = RAW / "historic_rail" / "topo"
OSM_DIR = RAW / "historic_rail"
SHEET_DIR = INTERIM / "historic_rail" / "sheets"
DEBUG_DIR = INTERIM / "historic_rail" / "debug"
FARM_CACHE = INTERIM / "topo" / "maps"           # topo_farmsteads.py per-sheet results (alignment)
UTM = "EPSG:32610"
HTMC = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/"

# USGS HTMC sheets used for tracing: key -> (TNM product id, path under HTMC, edition label)
SHEETS = {
    "sf1895": (298889, "62500/CA_San%20Francisco_298889_1895_62500_geo.pdf"),
    "sf1899": (298894, "62500/CA_San%20Francisco_298894_1899_62500_geo.pdf"),
    "sf1915": (466302, "62500/CA_San%20Francisco_466302_1915_62500_geo.pdf"),
    "sm1899": (298921, "62500/CA_San%20Mateo_298921_1899_62500_geo.pdf"),
    "sm1915": (301599, "62500/CA_San%20Mateo_301599_1915_62500_geo.pdf"),
    "hmb1940": (297627, "62500/CA_Halfmoon%20Bay_297627_1940_62500_geo.pdf"),
    "mm1949": (293071, "24000/CA_Montara%20Mountain_293071_1949_24000_geo.pdf"),
    "hmb1952": (291121, "24000/CA_Half%20Moon%20Bay_291121_1952_24000_geo.pdf"),
    "sg1955": (300088, "24000/CA_San%20Gregorio_300088_1955_24000_geo.pdf"),
    "tam1897": (298988, "62500/CA_Tamalpais_298988_1897_62500_geo.pdf"),
    "pr1918": (298610, "62500/CA_Point%20Reyes_298610_1918_62500_geo.pdf"),
    "kar1898": (297860, "62500/CA_Karquines_297860_1898_62500_geo.pdf"),
    "con1897": (297157, "62500/CA_Concord_297157_1897_62500_geo.pdf"),
    "con1915": (297166, "62500/CA_Concord_297166_1915_62500_geo.pdf"),
    "hay1899": (465731, "62500/CA_Haywards_465731_1899_62500_geo.pdf"),
    "hay1915": (297660, "62500/CA_Hayward_297660_1915_62500_geo.pdf"),
    "pa1897": (298452, "62500/CA_Palo%20Alto_298452_1897_62500_geo.pdf"),
    "pa1899": (298457, "62500/CA_Palo%20Alto_298457_1899_62500_geo.pdf"),
    "sj1897": (298899, "62500/CA_San%20Jose_298899_1897_62500_geo.pdf"),
    "sj1899": (466311, "62500/CA_San%20Jose_466311_1899_62500_geo.pdf"),
    "lg1919": (298061, "62500/CA_Los%20Gatos_298061_1919_62500_geo.pdf"),
    "na1919": (298353, "62500/CA_New%20Almaden_298353_1919_62500_geo.pdf"),
    "sc1902": (299623, "125000/CA_Santa%20Cruz_299623_1902_125000_geo.pdf"),
    "md1898": (298276, "62500/CA_Mt%20Diablo_298276_1898_62500_geo.pdf"),
    "ple1906": (298577, "62500/CA_Pleasanton_298577_1906_62500_geo.pdf"),
    "pet1914": (298523, "62500/CA_Petaluma_298523_1914_62500_geo.pdf"),
}


# ============================================================== geometry helpers
_TF = {}


def tf(src, dst):
    import pyproj
    k = (src, dst)
    if k not in _TF:
        _TF[k] = pyproj.Transformer.from_crs(src, dst, always_xy=True)
    return _TF[k]


def to_utm(lon, lat):
    return tf("EPSG:4326", UTM).transform(np.asarray(lon, float), np.asarray(lat, float))


def to_ll(x, y):
    return tf(UTM, "EPSG:4326").transform(np.asarray(x, float), np.asarray(y, float))


def densify(xy: np.ndarray, step=20.0) -> np.ndarray:
    """Insert vertices so no edge is longer than step (metres, UTM coords)."""
    out = [xy[0]]
    for a, b in zip(xy[:-1], xy[1:]):
        d = float(np.hypot(*(b - a)))
        n = max(1, int(math.ceil(d / step)))
        for k in range(1, n + 1):
            out.append(a + (b - a) * k / n)
    return np.array(out)


def resample(xy: np.ndarray, step: float) -> np.ndarray:
    """Evenly spaced vertices along a polyline (keeps both ends)."""
    seg = np.hypot(*np.diff(xy, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    if s[-1] < step:
        return xy[[0, -1]]
    n = max(2, int(round(s[-1] / step)) + 1)
    t = np.linspace(0, s[-1], n)
    return np.column_stack([np.interp(t, s, xy[:, 0]), np.interp(t, s, xy[:, 1])])


def smooth(xy: np.ndarray, window_m=60.0, step=5.0, keep_ends=True) -> np.ndarray:
    """Moving-average smoothing along the line (in metres): removes pixel staircases of a
    traced path while keeping curves of railway radius (>= ~150 m) nearly unchanged."""
    if len(xy) < 3:
        return xy
    r = resample(xy, step)
    k = max(1, int(round(window_m / step / 2)))
    if len(r) < 2 * k + 2:
        k = max(1, (len(r) - 2) // 2)
    pad = np.vstack([np.repeat(r[:1], k, 0), r, np.repeat(r[-1:], k, 0)])
    ker = np.ones(2 * k + 1) / (2 * k + 1)
    sx = np.convolve(pad[:, 0], ker, "valid")
    sy = np.convolve(pad[:, 1], ker, "valid")
    out = np.column_stack([sx, sy])
    if keep_ends:
        # blend back to the exact end points over k samples
        w = np.minimum(1.0, np.arange(len(out)) / max(k, 1))
        w = np.minimum(w, w[::-1])[:, None]
        out = w * out + (1 - w) * r
    return out


def robust_smooth(xy: np.ndarray, window_m=70.0, spike_m=7.0, iters=3) -> np.ndarray:
    """Smoothing that ignores out-and-back excursions of a traced path (onto lettering, a
    crossing road): points further than spike_m from the smoothed line are dropped and the
    rest smoothed again."""
    r = resample(xy, 4.0)
    keep = np.ones(len(r), bool)
    for _ in range(iters):
        sm = smooth(r[keep], window_m)
        from scipy.spatial import cKDTree
        d, _i = cKDTree(resample(sm, 2.0)).query(r)
        new = d <= max(spike_m, np.percentile(d[keep], 80))
        new[[0, -1]] = True
        if (new == keep).all():
            break
        keep = new
    return smooth(r[keep], window_m)


def chaikin(xy: np.ndarray, n=3) -> np.ndarray:
    for _ in range(n):
        q = 0.75 * xy[:-1] + 0.25 * xy[1:]
        r = 0.25 * xy[:-1] + 0.75 * xy[1:]
        mid = np.empty((2 * len(q), 2))
        mid[0::2], mid[1::2] = q, r
        xy = np.vstack([xy[:1], mid, xy[-1:]])
    return xy


def simplify(xy: np.ndarray, tol=1.0) -> np.ndarray:
    from shapely.geometry import LineString
    return np.asarray(LineString(xy).simplify(tol, preserve_topology=False).coords)


# ============================================================== network routing (rail / road)
class Network:
    """Lines (UTM) as a graph: vertices are nodes (snapped to 0.5 m), consecutive vertices
    edges; separate lines whose ends lie within `join` m are linked (gap edges cost x3)."""

    def __init__(self, lines, join=25.0):
        from scipy.sparse import coo_matrix
        from scipy.spatial import cKDTree
        key = {}
        pts = []

        def node(p):
            k = (round(p[0] * 2), round(p[1] * 2))
            if k not in key:
                key[k] = len(pts)
                pts.append(p)
            return key[k]

        I, J, W = [], [], []
        ends = []
        for c in lines:
            c = np.asarray(c, float)
            if len(c) < 2:
                continue
            ids = [node(p) for p in c]
            for a, b, pa, pb in zip(ids[:-1], ids[1:], c[:-1], c[1:]):
                if a != b:
                    I.append(a); J.append(b); W.append(float(np.hypot(*(pb - pa))) + 1e-3)
            ends += [ids[0], ids[-1]]
        self.pts = np.array(pts)
        n = len(pts)
        if join > 0 and ends:
            e = np.unique(ends)
            t = cKDTree(self.pts[e])
            for a, b in t.query_pairs(join):
                ia, ib = e[a], e[b]
                d = float(np.hypot(*(self.pts[ia] - self.pts[ib])))
                I.append(ia); J.append(ib); W.append(3 * d + 1)
        self.G = coo_matrix((W + W, (I + J, J + I)), shape=(n, n)).tocsr()
        self.tree = cKDTree(self.pts)

    def path(self, wps, snap=150.0):
        """Shortest path through the waypoints (UTM). Returns (xy, max snap distance)."""
        from scipy.sparse.csgraph import dijkstra
        idx, dmax = [], 0.0
        for w in wps:
            d, i = self.tree.query(w)
            if d > snap:
                raise ValueError(f"waypoint {to_ll(*w)} is {d:.0f} m from the network")
            dmax = max(dmax, d)
            idx.append(int(i))
        out = []
        for a, b in zip(idx[:-1], idx[1:]):
            dist, pred = dijkstra(self.G, indices=a, return_predecessors=True, limit=np.inf)
            if not np.isfinite(dist[b]):
                log(f"   (no network path {np.round(to_ll(*self.pts[a]), 5)} -> {np.round(to_ll(*self.pts[b]), 5)}: straight link)")
                self.gaps = getattr(self, "gaps", 0) + 1
                out += [a, b] if not out else [b]
                continue
            seq = [b]
            while seq[-1] != a:
                seq.append(pred[seq[-1]])
            seq = seq[::-1]
            out += seq if not out else seq[1:]
        return self.pts[out], dmax


_RAIL = None


def rail_lines(bbox_ll, kinds=("heavy",)):
    """Overture rail (+ Overpass extracts) inside bbox, as UTM coordinate arrays with flags."""
    global _RAIL
    import geopandas as gpd
    if _RAIL is None:
        g = gpd.read_parquet(OVERTURE / "rail.parquet")
        flags = []
        for f in g.rail_flags:
            s = set()
            for x in (f if f is not None else []):
                s.update(x["values"])
            flags.append(s)
        g["flags"] = flags
        g["src"] = "overture"
        g = g.set_crs("EPSG:4326", allow_override=True)
        frames = [g[["class", "name", "flags", "src", "geometry"]]]
        osm = osm_extract()
        if osm is not None and len(osm):
            frames.append(osm)
        import pandas as pd
        _RAIL = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs="EPSG:4326")
    w, s, e, n = bbox_ll
    sub = _RAIL.cx[w:e, s:n]
    if "heavy" in kinds:
        sub = sub[~sub["class"].isin(["subway", "light_rail", "monorail", "funicular"])]
    return sub


_OSM = None


def osm_extract():
    """Overpass extracts (data/raw/historic_rail/hist_*.json, h2_*.json): abandoned / razed /
    disused railway ways, as a GeoDataFrame like the Overture rail one."""
    global _OSM
    if _OSM is not None:
        return _OSM
    import glob
    import geopandas as gpd
    from shapely.geometry import LineString
    rows, seen = [], set()
    for f in sorted(glob.glob(str(OSM_DIR / "hist_*.json")) + glob.glob(str(OSM_DIR / "h2_*.json"))):
        try:
            d = json.load(open(f))
        except Exception:  # noqa: BLE001
            continue
        for e in d.get("elements", []):
            if e.get("type") != "way" or e["id"] in seen or "geometry" not in e:
                continue
            seen.add(e["id"])
            t = e.get("tags", {})
            rw = t.get("railway") or ""
            if rw in ("platform", "station", "platform_edge"):
                continue
            c = [(p["lon"], p["lat"]) for p in e["geometry"] if p]
            if len(c) < 2:
                continue
            fl = {"is_abandoned"} if (rw in ("abandoned", "razed", "dismantled") or "abandoned:railway" in t
                                     or "razed:railway" in t) else {"is_disused"} if rw == "disused" else set()
            if t.get("bridge"):
                fl.add("is_bridge")
            if t.get("tunnel"):
                fl.add("is_tunnel")
            rows.append({"class": "osm_" + (rw or "lifecycle"), "name": t.get("name") or t.get("old_name") or t.get("operator"),
                         "flags": fl, "src": f"osm:{e['id']}", "geometry": LineString(c)})
    _OSM = gpd.GeoDataFrame(rows, crs="EPSG:4326") if rows else None
    return _OSM


_ROADS = {}


def road_lines(bbox_ll):
    import geopandas as gpd
    w, s, e, n = bbox_ll
    out = []
    for f in ("roads_region", "roads_local", "roads_oakland_sanborn", "roads_southbay_core"):
        if f not in _ROADS:
            g = gpd.read_parquet(OVERTURE / f"{f}.parquet", columns=["class", "name", "geometry"])
            g = g[~g["class"].isin(["footway", "steps", "path", "cycleway", "pedestrian", "track", "motorway"])]
            _ROADS[f] = g.set_crs("EPSG:4326", allow_override=True)
        out.append(_ROADS[f].cx[w:e, s:n])
    import pandas as pd
    return gpd.GeoDataFrame(pd.concat(out, ignore_index=True), crs="EPSG:4326")


def lines_utm(gdf):
    res = []
    for geom in gdf.geometry.values:
        for ln in getattr(geom, "geoms", [geom]):
            c = np.asarray(ln.coords)
            x, y = to_utm(c[:, 0], c[:, 1])
            res.append(np.column_stack([x, y]))
    return res


def bbox_of(wps_ll, pad=0.01):
    a = np.asarray(wps_ll)
    return (a[:, 0].min() - pad, a[:, 1].min() - pad, a[:, 0].max() + pad, a[:, 1].max() + pad)


# ============================================================== topo sheets
class Sheet:
    """A USGS HTMC GeoPDF: registration (topo_farmsteads.GeoPDF), the local road alignment
    of the survey, pixel <-> today's lon/lat, and windows of the scan."""

    def __init__(self, key):
        from topo_farmsteads import GeoPDF, crs_for
        pid, rel = SHEETS[key]
        self.key = key
        TOPO_DIR.mkdir(parents=True, exist_ok=True)
        self.pdf = TOPO_DIR / rel.split("/")[-1].replace("%20", "_")
        self.url = HTMC + rel
        download_file(self.url, self.pdf)
        self.geo = GeoPDF(self.pdf)
        g = self.geo.g
        self.crs = crs_for(g["proj"])
        a, b, c, d, e, f = g["georef"]["ctm"]
        self.ctm_inv = np.linalg.inv(np.array([[a, c], [b, d]]))
        self.ef = np.array([e, f])
        self.s, self.page_h = g["georef"]["s"], g["georef"]["page_h"]
        self.m_per_px = g["m_per_px"]
        self.res = self._meta(pid)

    def _meta(self, pid):
        """Road alignment of the sheet (cached). Reuses topo_farmsteads' result for the
        same scan; otherwise computes it from a ~8 m/px black-ink image."""
        import cv2
        SHEET_DIR.mkdir(parents=True, exist_ok=True)
        out = SHEET_DIR / f"{self.key}.json"
        if out.exists():
            return json.loads(out.read_text())
        g = self.geo.g
        step = max(1, int(round(8.0 / g["m_per_px"])))
        from topo_farmsteads import _colour_tests, road_alignment
        res = {"id": pid, "key": self.key, "m_per_px": g["m_per_px"], "ink_step": step, "georef": g["georef"],
               "proj": g["proj"], "edition": "early" if int(self.pdf.name.split("_")[-3]) < 1930 else "late",
               "source_url": self.url}
        fc = FARM_CACHE / f"{pid}.json"
        if fc.exists():
            fr = json.loads(fc.read_text())
            res["bbox"], res["align"] = fr["bbox"], fr["align"]
        else:
            sm = self.geo.read(0, self.geo.H, 0, self.geo.W, step=step)
            mx_, hue_ = _colour_tests(sm)[:2]
            ins = np.zeros(sm.shape[:2], np.uint8)
            cv2.fillPoly(ins, [np.round(g["neat_px"] / step).astype(np.int32)], 1)
            paper = float(np.percentile(sm[::4, ::4].max(2)[ins[::4, ::4] > 0], 75))
            ink = (((mx_ < 0.6 * paper) & hue_ & (ins > 0)) * 255).astype(np.uint8)
            cv2.imwrite(str(SHEET_DIR / f"{self.key}_ink.png"), ink)
            del sm, mx_, hue_
            nx, ny = g["px_to_proj"](g["neat_px"][:, 0], g["neat_px"][:, 1])
            lon, lat = tf(self.crs.to_wkt(), self.crs.geodetic_crs.to_wkt()).transform(nx, ny)
            res["bbox"] = [float(np.min(lon)), float(np.min(lat)), float(np.max(lon)), float(np.max(lat))]
            res["align"] = road_alignment(res, ink)
        out.write_text(json.dumps(res))
        log(f"sheet {self.key}: align {res['align']}")
        return res

    # ---- alignment (pixel offsets of the survey, as topo_farmsteads.apply_alignment)
    def _shift(self, cols, rows):
        al = self.res.get("align") or {}
        if not al.get("aligned") or (self.res.get("edition") != "early" and al.get("median_shift_m", 0) < 10):
            return np.zeros_like(cols), np.zeros_like(rows)
        m = self.m_per_px
        xk = (cols * m - al["xc_m"]) / 1000
        yk = (rows * m - al["yc_m"]) / 1000
        dx = al["cx"][0] + al["cx"][1] * xk + al["cx"][2] * yk
        dy = al["cy"][0] + al["cy"][1] * xk + al["cy"][2] * yk
        return dx / m, dy / m

    def px_to_ll(self, cols, rows):
        from topo_farmsteads import to_wgs84
        cols = np.asarray(cols, float); rows = np.asarray(rows, float)
        dc, dr = self._shift(cols, rows)
        c2, r2 = cols - dc, rows - dr
        x = c2 / self.s
        y = self.page_h - r2 / self.s
        a, b, c, d, e, f = self.res["georef"]["ctm"]
        X, Y = a * x + c * y + e, b * x + d * y + f
        return to_wgs84(self.crs, X, Y)

    def ll_to_px(self, lon, lat):
        from topo_farmsteads import to_wgs84
        to_wgs84(self.crs, 0.0, 0.0)      # initialise NADCON transformers
        import pyproj
        from pyproj.transformer import TransformerGroup
        if not hasattr(self, "_inv"):
            tg = TransformerGroup("EPSG:4326", self.crs.geodetic_crs, always_xy=True,
                                  area_of_interest=pyproj.aoi.AreaOfInterest(-123.5, 36.5, -121.0, 38.8))
            self._inv = (tg.transformers[0], pyproj.Transformer.from_crs(self.crs.geodetic_crs, self.crs, always_xy=True))
        t1, t2 = self._inv
        lo, la = t1.transform(np.asarray(lon, float), np.asarray(lat, float))
        X, Y = t2.transform(lo, la)
        xy = self.ctm_inv @ np.vstack([np.ravel(X) - self.ef[0], np.ravel(Y) - self.ef[1]])
        cols = xy[0] * self.s
        rows = (self.page_h - xy[1]) * self.s
        c2, r2 = cols.copy(), rows.copy()        # aligned -> published: p = a + shift(p)
        for _ in range(4):
            dc, dr = self._shift(c2, r2)
            c2, r2 = cols + dc, rows + dr
        return c2.reshape(np.shape(lon)), r2.reshape(np.shape(lat))

    def window(self, c0, r0, c1, r1, step=1):
        c0, r0 = max(0, int(c0)), max(0, int(r0))
        c1, r1 = min(self.geo.W, int(c1)), min(self.geo.H, int(r1))
        return self.geo.read(r0, r1, c0, c1, step=step), c0, r0


_SHEETS = {}


def sheet(key) -> Sheet:
    if key not in _SHEETS:
        _SHEETS.clear()          # one open at a time (memory)
        _SHEETS[key] = Sheet(key)
    return _SHEETS[key]


def trace_topo(key, wps_ll, corridor=120.0, step=1, dark=None, via=None):
    """Least-cost path along the black ink of sheet `key` through the waypoints (lon/lat in
    today's frame). corridor: metres either side of the waypoint polyline the path may use."""
    import cv2
    from skimage.graph import MCP_Geometric
    sh = sheet(key)
    wps_ll = np.asarray(wps_ll, float)
    # densify the waypoint polyline in lon/lat (for the corridor) then to pixels
    wx, wy = to_utm(wps_ll[:, 0], wps_ll[:, 1])
    dense = densify(np.column_stack([wx, wy]), 20.0)
    dl = np.column_stack(to_ll(dense[:, 0], dense[:, 1]))
    pc, pr = sh.ll_to_px(dl[:, 0], dl[:, 1])
    m = sh.m_per_px * step
    pad = corridor / sh.m_per_px + 20
    img, c0, r0 = sh.window(pc.min() - pad, pr.min() - pad, pc.max() + pad, pr.max() + pad, step=step)
    b = img.astype(np.int16)
    mx = b.max(2)
    R, G, B = b[:, :, 0], b[:, :, 1], b[:, :, 2]
    paper = float(np.percentile(mx, 90))
    blackish = ((R - G) < 45) & ((B - R) < 20) & ((G - R) < 20)
    dk = np.clip((0.78 * paper - mx) / (0.45 * paper), 0, 1) * np.where(blackish, 1.0, 0.25)
    if dark is not None:
        dk = dark(img, dk)
    dk = cv2.GaussianBlur(dk.astype(np.float32), (0, 0), max(0.6, 1.2 / step))
    cost = 1.0 + 30.0 * (1.0 - np.clip(dk / 0.6, 0, 1)) ** 2
    # corridor
    lc = np.round((pc - c0) / step).astype(np.int32)
    lr = np.round((pr - r0) / step).astype(np.int32)
    mask = np.zeros(cost.shape, np.uint8)
    cv2.polylines(mask, [np.column_stack([lc, lr]).astype(np.int32)], False, 1, max(1, int(2 * corridor / m)))
    cost[mask == 0] = 1e4
    # end points: snapped to the strongest ink within ~35 m; the path runs end to end inside
    # the corridor (intermediate waypoints only shape the corridor, so a waypoint placed on
    # a label or a few metres off the line doesn't pull the path)
    wc, wr = sh.ll_to_px(wps_ll[:, 0], wps_ll[:, 1])
    rs = max(2, int(35.0 / m))

    def snap_px(c, r):
        r_, c_ = int(np.clip(round((r - r0) / step), 0, cost.shape[0] - 1)), int(np.clip(round((c - c0) / step), 0, cost.shape[1] - 1))
        a0, a1 = max(0, r_ - rs), min(cost.shape[0], r_ + rs + 1)
        b0, b1 = max(0, c_ - rs), min(cost.shape[1], c_ + rs + 1)
        win = dk[a0:a1, b0:b1]
        yy, xx = np.mgrid[a0:a1, b0:b1]
        score = win - 0.002 * ((yy - r_) ** 2 + (xx - c_) ** 2) * m * m / 25.0
        k = np.unravel_index(np.argmax(score), score.shape)
        return (int(yy[k]), int(xx[k])) if win[k] > 0.35 else (r_, c_)
    ends = [snap_px(wc[0], wr[0])]
    for c, r in zip(wc[1:-1], wr[1:-1]):
        if "hard" in (via or ()):
            ends.append(snap_px(c, r))
    ends.append(snap_px(wc[-1], wr[-1]))
    path = []
    for a, bb in zip(ends[:-1], ends[1:]):
        mcp = MCP_Geometric(cost)
        mcp.find_costs([a], [bb])
        seg = mcp.traceback(bb)
        path += seg if not path else seg[1:]
    path = np.array(path, float)
    cols = path[:, 1] * step + c0
    rows = path[:, 0] * step + r0
    lon, lat = sh.px_to_ll(cols, rows)
    x, y = to_utm(lon, lat)
    xy = np.column_stack([x, y])
    # how much of the path ran on ink (quality)
    on = dk[path[:, 0].astype(int), path[:, 1].astype(int)] > 0.3
    return xy, float(on.mean())


# ============================================================== building
def piece_geometry(p):
    """p: dict(method=rail|road|topo|pts, wps=[(lon,lat),...], sheet=, corridor=, smooth=)
    -> (UTM xy array, info str)"""
    meth = p["method"]
    wps = np.asarray(p["wps"], float)
    wx, wy = to_utm(wps[:, 0], wps[:, 1])
    W = np.column_stack([wx, wy])
    if meth in ("rail", "road"):
        bb = bbox_of(wps, pad=p.get("pad", 0.015))
        gdf = rail_lines(bb, kinds=p.get("kinds", ("heavy",))) if meth == "rail" else road_lines(bb)
        if p.get("names"):
            gdf = gdf[gdf["name"].fillna("").str.contains("|".join(p["names"]))]
        net = Network(lines_utm(gdf), join=p.get("join", 25.0 if meth == "rail" else 8.0))
        xy, dmax = net.path(W, snap=p.get("snap", 150.0))
        xy = simplify(xy, 0.3)
        if p.get("smooth"):
            xy = smooth(xy, p["smooth"])
        return xy, f"{meth} (snap {dmax:.0f} m)"
    if meth == "topo":
        xy, on = trace_topo(p["sheet"], wps, corridor=p.get("corridor", 120.0), step=p.get("step", 1),
                            via=p.get("via"))
        xy = robust_smooth(xy, p.get("smooth", 70.0))
        return xy, f"topo {p['sheet']} ({on:.0%} on ink)"
    if meth == "pts":
        xy = chaikin(W, p.get("chaikin", 4)) if len(W) > 2 else W
        return xy, "pts"
    raise ValueError(meth)


def join_pieces(parts):
    """Concatenate piece polylines; consecutive pieces are joined end to start (a short
    blend where they don't meet exactly)."""
    out = None
    for xy in parts:
        if out is None:
            out = xy
            continue
        if np.hypot(*(out[-1] - xy[0])) > 1.0:
            out = np.vstack([out, xy])
        else:
            out = np.vstack([out, xy[1:]])
    return out


def build(spec_mod, only=None):
    feats = []
    report = []
    for r in spec_mod.ROUTES:
        if only and not any(r["route_id"].startswith(o) for o in only):
            continue
        for seg in r["segments"]:
            parts, info = [], []
            for p in seg["pieces"]:
                try:
                    xy, inf = piece_geometry(p)
                except Exception as ex:  # noqa: BLE001
                    log(f"!! {r['route_id']} / {seg.get('name', '')}: {p['method']} failed: {ex}")
                    raise
                parts.append(xy)
                info.append(inf)
            xy = join_pieces(parts)
            xy = densify(simplify(xy, 0.5), 20.0)
            lon, lat = to_ll(xy[:, 0], xy[:, 1])
            props = {k: seg.get(k, r.get(k)) for k in
                     ("route_id", "name", "mode", "year_start", "year_end", "elevated", "confidence", "source_url", "note")}
            props["route_id"] = r["route_id"]
            props["geometry_source"] = "; ".join(info)
            feats.append({"type": "Feature", "properties": props,
                          "geometry": {"type": "LineString",
                                       "coordinates": [[round(float(a), 6), round(float(b), 6)] for a, b in zip(lon, lat)]}})
            length = float(np.sum(np.hypot(*np.diff(xy, axis=0).T)))
            report.append(f"{r['route_id']:28s} {seg.get('year_start')}-{seg.get('year_end')} {length/1000:6.2f} km  {props['geometry_source']}")
            log(report[-1])
    return feats, report


# ============================================================== debug view
def view(key, w, s_, e, n, px=1400, out=None, overlay=True):
    """PNG of the lon/lat box: the topo sheet `key` warped to today's frame ('-' = none),
    today's rail (grey), mapped abandoned/disused grades (red/orange), roads (light),
    features of historic_rail.geojson (blue) and a labelled graticule."""
    import cv2
    w, s_, e, n = map(float, (w, s_, e, n))
    lat0 = (s_ + n) / 2
    W = int(px)
    H = int(round(px * (n - s_) / ((e - w) * math.cos(math.radians(lat0)))))
    lon = w + (np.arange(W) + 0.5) / W * (e - w)
    lat = n - (np.arange(H) + 0.5) / H * (n - s_)
    LON, LAT = np.meshgrid(lon, lat)
    canvas = np.full((H, W, 3), 255, np.uint8)
    mpp = (e - w) * 111320 * math.cos(math.radians(lat0)) / W
    if key and key != "-":
        sh = sheet(key)
        pc, pr = sh.ll_to_px(LON.ravel(), LAT.ravel())
        pc = pc.reshape(H, W); pr = pr.reshape(H, W)
        step = max(1, int(mpp / sh.m_per_px * 0.8))
        img, c0, r0 = sh.window(pc.min() - 5, pr.min() - 5, pc.max() + 5, pr.max() + 5, step=step)
        canvas = cv2.remap(img, ((pc - c0) / step).astype(np.float32), ((pr - r0) / step).astype(np.float32),
                           cv2.INTER_LINEAR, borderValue=(255, 255, 255))
        canvas = (0.75 * canvas + 0.25 * 255).astype(np.uint8)

    def draw(geoms, color, thick):
        for gm in geoms:
            for ln in getattr(gm, "geoms", [gm]):
                c = np.asarray(ln.coords)
                xs = (c[:, 0] - w) / (e - w) * W
                ys = (n - c[:, 1]) / (n - s_) * H
                cv2.polylines(canvas, [np.column_stack([xs, ys]).round().astype(np.int32)], False, color, thick, cv2.LINE_AA)
    if overlay:
        bb = (w, s_, e, n)
        try:
            rd = road_lines(bb)
            draw(rd.geometry.values, (235, 205, 205), 1)
        except Exception:  # noqa: BLE001
            pass
        rl = rail_lines(bb, kinds=("all",))
        ab = rl[[("is_abandoned" in f) for f in rl["flags"]]]
        du = rl[[("is_disused" in f) and ("is_abandoned" not in f) for f in rl["flags"]]]
        act = rl[[not (f & {"is_abandoned", "is_disused"}) for f in rl["flags"]]]
        draw(act.geometry.values, (90, 90, 90), 1)
        draw(du.geometry.values, (255, 140, 0), 2)
        draw(ab.geometry.values, (230, 0, 0), 2)
        gj = MANUAL / "historic_rail.geojson"
        if gj.exists():
            from shapely.geometry import shape
            fs = json.loads(gj.read_text())["features"]
            draw([shape(f["geometry"]) for f in fs], (0, 90, 255), 2)
    # graticule every ~0.005 / 0.01 deg
    span = e - w
    st = 0.002 if span < 0.03 else 0.005 if span < 0.08 else 0.01 if span < 0.2 else 0.05
    for v in np.arange(math.ceil(w / st) * st, e, st):
        x = int((v - w) / (e - w) * W)
        cv2.line(canvas, (x, 0), (x, H), (160, 220, 160), 1)
        cv2.putText(canvas, f"{v:.3f}", (x + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 120, 0), 1, cv2.LINE_AA)
    for v in np.arange(math.ceil(s_ / st) * st, n, st):
        y = int((n - v) / (n - s_) * H)
        cv2.line(canvas, (0, y), (W, y), (160, 220, 160), 1)
        cv2.putText(canvas, f"{v:.3f}", (2, y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 120, 0), 1, cv2.LINE_AA)
    cv2.putText(canvas, f"{key}  {mpp:.1f} m/px", (W - 230, H - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    out = out or DEBUG_DIR / f"view_{key}_{w:.3f}_{s_:.3f}.png"
    cv2.imwrite(str(out), canvas[:, :, ::-1])
    return out


def main():
    import importlib.util
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        spec = importlib.util.spec_from_file_location("hr_spec", MANUAL / "historic_rail_spec.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        only = sys.argv[2:] or None
        feats, report = build(mod, only)
        out = MANUAL / "historic_rail.geojson"
        if only and out.exists():
            old = json.loads(out.read_text())["features"]
            keep = [f for f in old if not any(f["properties"]["route_id"].startswith(o) for o in only)]
            feats = keep + feats
            order = {r["route_id"]: i for i, r in enumerate(mod.ROUTES)}
            feats.sort(key=lambda f: order.get(f["properties"]["route_id"], 1e9))
        fc = {"type": "FeatureCollection",
              "name": "historic_rail",
              "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
              "features": feats}
        out.write_text("{\n" + ",\n".join(
            [f'"type": "FeatureCollection"', f'"name": "historic_rail"',
             f'"crs": {json.dumps(fc["crs"])}',
             '"features": [\n' + ",\n".join(json.dumps(f, ensure_ascii=False) for f in feats) + "\n]"]) + "\n}\n")
        log(f"wrote {out} ({len(feats)} features)")
    elif cmd == "view":
        args = sys.argv[2:]
        print(view(args[0], *args[1:5], px=int(args[5]) if len(args) > 5 else 1400))


if __name__ == "__main__":
    main()
