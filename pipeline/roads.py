"""Stage: roads, rail and transit routes with lifespans, draped on the terrain.

  * San Francisco streets — DataSF centerlines. A street appears when its block
    was first built up: the first researched extent (sf_extent_YYYY) containing
    it, else just before the earliest building within 60 m (`estimated`).
  * Routes — data/manual/routes.csv (researched): freeways, highways, cable cars,
    streetcars, railroads, Key System, BART, ferries, with open/close years and
    elevated/tunnel flags. SF street routes follow the centerline between
    consecutive intersections.
  * Region roads — Overture/OSM motorway…tertiary outside SF. Motorways/trunks take
    the year of the nearest researched freeway route (≤150 m), else 1960
    (`estimated`); other roads the HISDAC first-built-up year nearby, else 1880
    (county roads, `estimated`).

Outputs (BAYT): viewer/public/data/roads-sf.bin.gz, routes.bin.gz, roads-region.bin.gz
  start_indices u32 (path vertex starts), positions f32[3] (lon/lat offsets from
  origin, z = ground + offset), kind u8, width u8 (m), years f32[2], elevated u8
"""
from __future__ import annotations

import glob
import math

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Point
from shapely.ops import linemerge, substring

from common import INTERIM, MANUAL, RAW, VIEWER_DATA, log
from download_overture import RELEASE
from export_columnar import write_columnar
from terrain_grid import grid_def

ORIGIN = (-122.44, 37.76)
UTM = "EPSG:32610"

# kinds (keep in sync with viewer/src/layers/roads.ts)
K_STREET, K_MAJOR, K_FREEWAY, K_HIGHWAY, K_CABLE, K_STREETCAR, K_RAIL, K_KEY, K_BART, K_FERRY, K_LIGHTRAIL = range(11)
MODE_KIND = {"freeway": K_FREEWAY, "highway": K_HIGHWAY, "cable_car": K_CABLE, "streetcar": K_STREETCAR,
             "horsecar": K_STREETCAR, "steam_railroad": K_RAIL, "interurban": K_RAIL, "key_system": K_KEY,
             "bart": K_BART, "ferry": K_FERRY, "light_rail": K_LIGHTRAIL}
# BART and today's Muni lines come from transit.py (transit.bin.gz) when it has run
TRANSIT_TAKES_OVER = True
# edge of the region extracts (download_overture.REGION_BBOX): freeway ends there are cuts
REGION_BBOX_ROADS = (-123.2, 36.85, -121.2, 38.9)
# routes drawn by a landmark model instead (double-deck viaduct in landmarks/city.ts)
LANDMARK_ROUTES = {"fwy_embarcadero"}
ELEV = {"ground": 0, "embankment": 1, "viaduct": 2, "bridge": 3, "tunnel": 4}
WIDTH = {K_STREET: 9, K_MAJOR: 14, K_FREEWAY: 24, K_HIGHWAY: 16, K_CABLE: 3, K_STREETCAR: 3, K_RAIL: 4,
         K_KEY: 4, K_BART: 5, K_FERRY: 6, K_LIGHTRAIL: 3}


# ---------------------------------------------------------------- elevation
class Ground:
    def __init__(self):
        self.grids = []
        for name in ("detail", "region"):
            g = grid_def(name)
            e = np.load(INTERIM / f"grid_{name}_elev.npy")
            self.grids.append((g, np.where(e < -500, 0, e)))

    def __call__(self, lon, lat):
        lon = np.asarray(lon, float)
        lat = np.asarray(lat, float)
        X = np.radians(lon) * 6378137.0
        Y = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))
        out = np.full(lon.shape, np.nan)
        for g, e in self.grids:
            c = (X - g["X0"]) / g["res"]
            r = (g["Y0"] - Y) / g["res"]
            ok = np.isnan(out) & (c >= 0) & (r >= 0) & (c < g["cols"] - 1) & (r < g["rows"] - 1)
            c0 = np.floor(c[ok]).astype(int)
            r0 = np.floor(r[ok]).astype(int)
            fx = c[ok] - c0
            fy = r[ok] - r0
            out[ok] = (e[r0, c0] * (1 - fx) + e[r0, c0 + 1] * fx) * (1 - fy) + (e[r0 + 1, c0] * (1 - fx) + e[r0 + 1, c0 + 1] * fx) * fy
        return np.maximum(np.nan_to_num(out), 0.9)


def densify(line: LineString, step=25.0):
    """Densify a UTM line so the ribbon follows the terrain."""
    L = line.length
    if L < 1:
        return None
    n = max(2, int(math.ceil(L / step)) + 1)
    return [line.interpolate(t, normalized=True) for t in np.linspace(0, 1, n)]


# ---------------------------------------------------------------- SF streets
def sf_streets():
    st = gpd.GeoDataFrame(pd.concat([gpd.read_file(p) for p in glob.glob(str(RAW / "sf_streets_classes" / "page-*.geojson"))]), crs=4326)
    keep = {"STREETS", "STREETS_TI", "STREETS_YBI", "STREETS_HUNTERSP", "PARKS", "PARKS_NPS_PRESIDIO", "PARKS_NPS_FTMASON", "PRIVATE"}
    st = st[st.layer.isin(keep) & st.geometry.notna()].to_crs(UTM)
    st = st.explode(index_parts=False)
    st = st[st.geometry.geom_type == "LineString"].reset_index(drop=True)
    return st


def extent_year_of(points: gpd.GeoSeries):
    from geocode import intersection_rings
    out = np.full(len(points), np.nan)
    prev = 1846.0
    for f in sorted(glob.glob(str(MANUAL / "sf_extent_*.csv"))):
        year = float(f.split("_")[-1].split(".")[0])
        for poly in intersection_rings(f, crs=UTM).values():
            inside = points.within(poly).values & np.isnan(out)
            out[inside] = prev + (year - prev) * 0.5
        prev = year
    return out


def building_years():
    b = gpd.read_parquet(INTERIM / "sf_buildings.parquet").to_crs(UTM)
    frames = [b[["start_year", "geometry"]]]
    pred = INTERIM / "sf_predecessors.parquet"
    if pred.exists():
        frames.append(gpd.read_parquet(pred).to_crs(UTM)[["start_year", "geometry"]])
    allb = pd.concat(frames, ignore_index=True)
    c = allb.geometry.representative_point()
    return cKDTree(np.column_stack([c.x, c.y])), allb.start_year.values


# ---------------------------------------------------------------- routes
def route_geometry(row, st_by_name, st_index):
    from fire_1906 import norm
    from geocode import ring_polygon  # noqa: F401  (ensures streets cache)
    from geocode import streets as all_streets
    gt = str(row.geom_type).strip()
    if gt == "lonlat":
        pts = [tuple(map(float, p.split()[:2])) for p in str(row.geom).split(";") if p.strip()]
        if len(pts) < 2:
            return None
        return gpd.GeoSeries([LineString(pts)], crs=4326).to_crs(UTM).iloc[0]
    if gt != "streets":
        return None
    from fire_1906 import intersection
    stx = all_streets()
    nodes = []
    names = []
    for entry in str(row.geom).split(";"):
        entry = entry.strip()
        if "&" not in entry:
            continue
        a, b = (s.strip() for s in entry.split("&", 1))
        p, _ = intersection(stx, a, b)
        if p is not None:
            nodes.append(p)
            names.append({norm(a)[0], norm(b)[0]})
    if len(nodes) < 2:
        return None
    coords = []
    for k in range(len(nodes) - 1):
        common = names[k] & names[k + 1]
        seg = None
        for nm in common:
            line = st_by_name.get(nm)
            if line is None:
                continue
            d0, d1 = line.project(nodes[k]), line.project(nodes[k + 1])
            if line.distance(nodes[k]) < 40 and line.distance(nodes[k + 1]) < 40 and abs(d1 - d0) > 1:
                seg = substring(line, min(d0, d1), max(d0, d1))
                if d1 < d0:
                    seg = LineString(list(seg.coords)[::-1])
                break
        part = list(seg.coords) if seg is not None and seg.geom_type == "LineString" else [nodes[k].coords[0], nodes[k + 1].coords[0]]
        coords.extend(part if not coords else part[1:])
    return LineString(coords) if len(coords) >= 2 else None


def streets_by_name(st):
    from fire_1906 import norm
    out = {}
    for name, grp in st.groupby(st.street.fillna("").map(lambda n: norm(n)[0])):
        u = shapely.union_all(grp.geometry.values)
        merged = linemerge(u) if u.geom_type == "MultiLineString" else u
        if merged.geom_type == "MultiLineString":
            # keep the longest piece per name for projection; shorter islands rarely matter
            merged = max(merged.geoms, key=lambda g: g.length)
        out[name] = merged
    return out


# ---------------------------------------------------------------- writer
def write_paths(path, items, ground, z_offset_fn, step=25.0):
    """items: list of (utm LineString, kind, width, start, end, elevated).
    step: vertex spacing (m) so paths follow the terrain grid they drape on."""
    starts = [0]
    pos = []
    kinds, widths, years, elev = [], [], [], []
    for line, kind, width, y0, y1, el in items:
        pts = densify(line, step if kind not in (K_FERRY,) else 400)
        if not pts:
            continue
        xy = gpd.GeoSeries(pts, crs=UTM).to_crs(4326)
        lon, lat = xy.x.values, xy.y.values
        if kind == K_FERRY:
            z = np.full(len(lon), 1.2)
        else:
            z = ground(lon, lat) + z_offset_fn(kind, el)
        for a, b, c in zip(lon - ORIGIN[0], lat - ORIGIN[1], z):
            pos.extend((a, b, c))
        starts.append(starts[-1] + len(lon))
        kinds.append(kind)
        widths.append(width)
        years.extend((y0, y1))
        elev.append(el)
    if not kinds:
        return
    write_columnar(path, {
        "start_indices|shuffle": np.asarray(starts, np.uint32),
        "positions|shuffle": np.asarray(pos, np.float32),
        "kind": np.asarray(kinds, np.uint8),
        "width": np.clip(np.asarray(widths), 1, 255).astype(np.uint8),
        "years": np.asarray(years, np.float32),
        "elevated": np.asarray(elev, np.uint8),
    }, origin=ORIGIN, counts={"paths": len(kinds), "vertices": starts[-1]})
    log(f"roads: wrote {path.name}: {len(kinds)} paths, {starts[-1]} vertices")


def z_offset(kind, el):
    if el == ELEV["viaduct"]:
        return 14.0
    if el == ELEV["bridge"]:
        return 20.0
    if el == ELEV["embankment"]:
        return 3.0
    return {K_FREEWAY: 0.7, K_HIGHWAY: 0.6, K_MAJOR: 0.5}.get(kind, 0.45) + (0.15 if kind in (K_CABLE, K_STREETCAR, K_RAIL, K_KEY, K_BART, K_LIGHTRAIL) else 0)


# ---------------------------------------------------------------- freeways in 3D
def _flag_ranges(rules, key=None):
    """Overture road_flags / level_rules -> list of (lo, hi, value)."""
    out = []
    if rules is None:
        return out
    for r in rules:
        b = r.get("between")
        lo, hi = (0.0, 1.0) if b is None else (float(b[0]), float(b[1]))
        if key is None:
            out.append((lo, hi, float(r.get("value", 0) or 0)))
        else:
            vals = r.get("values")
            if vals is not None and key in list(vals):
                out.append((lo, hi, 1.0))
    return out


def freeway_items(ground, fw_routes):
    """Motorways, trunks and ramps (Overture) with a height profile per vertex.

    Height above ground: level 1 viaducts ~12.5 m, level 2 ~22 m, other bridges 6.5 m,
    at grade 0.7 m. Approaches climb at most ~5.5 % (the profile is dilated with that
    slope cone), junctions share one height (connectors), and ramp ends that meet a
    surface street (a connector no other freeway segment uses), mainline ends and tunnel
    portals come down to grade through the network (see below). Tunnel portions are
    dropped. Dates: the parallel researched freeway route; ramps open with the latest
    mainline they connect."""
    fwy = gpd.read_parquet(RAW / "overture" / RELEASE / "freeways.parquet")
    if fwy.crs is None:
        fwy = fwy.set_crs(4326)
    fwy = fwy[fwy.geometry.geom_type == "LineString"].reset_index(drop=True)
    fwu = fwy.to_crs(UTM)
    SLOPE, DOWN = 0.055, 0.08
    segs = []
    conn_count = {}
    for i, row in fwy.iterrows():
        g = fwu.geometry.iloc[i]
        L = g.length
        if L < 1:
            continue
        sf = row.geometry.bounds[0] > -122.53 and row.geometry.bounds[2] < -122.35 and row.geometry.bounds[1] > 37.70
        step = 20.0 if sf else 40.0
        n = max(2, int(math.ceil(L / step)) + 1)
        f = np.linspace(0, 1, n)
        lev = np.zeros(n)
        for lo, hi, v in _flag_ranges(row.level_rules):
            lev[(f >= lo) & (f <= hi)] = v
        br = np.zeros(n, bool)
        for lo, hi, _ in _flag_ranges(row.road_flags, "is_bridge"):
            br[(f >= lo) & (f <= hi)] = True
        tn = np.zeros(n, bool)
        for lo, hi, _ in _flag_ranges(row.road_flags, "is_tunnel"):
            tn[(f >= lo) & (f <= hi)] = True
        h = np.where(lev >= 1, 3.0 + 9.5 * lev, np.where(br, 6.5, 0.7))
        tn_real = tn.copy()
        # the Bay Bridge and Golden Gate Bridge decks belong to their landmark models
        nm = str(row["name"] or "")
        if br.any():
            ll = [row.geometry.interpolate(x, normalized=True) for x in f]
            lo_ = np.array([p.x for p in ll])
            la_ = np.array([p.y for p in ll])
            over_water = ground(lo_, la_) < 2.0
            bay_bridge = (lo_ > -122.392) & (lo_ < -122.298) & (la_ > 37.783) & (la_ < 37.832)
            if "Golden Gate Bridge" in nm:
                tn = tn | br
            tn = tn | (br & bay_bridge & over_water)
        conns = [(c["connector_id"], float(c["at"])) for c in (row.connectors if row.connectors is not None else [])]
        for cid, _ in conns:
            conn_count[cid] = conn_count.get(cid, 0) + 1
        segs.append({"i": i, "g": g, "f": f, "s": f * L, "h": h, "tn": tn, "tn_real": tn_real, "conns": conns,
                     "cls": row["class"], "sub": row.subclass, "bounds": row.geometry.bounds})

    def dilate(seg):
        h, s_ = seg["h"], seg["s"]
        for k in range(1, len(h)):
            h[k] = max(h[k], h[k - 1] - SLOPE * (s_[k] - s_[k - 1]))
        for k in range(len(h) - 2, -1, -1):
            h[k] = max(h[k], h[k + 1] - SLOPE * (s_[k + 1] - s_[k]))

    def idx_at(seg, at):
        return int(np.argmin(np.abs(seg["f"] - at)))

    for seg in segs:
        dilate(seg)
    for _ in range(2):  # junction heights: highest wins, then re-dilate
        node_h = {}
        for seg in segs:
            for cid, at in seg["conns"]:
                node_h[cid] = max(node_h.get(cid, 0.0), seg["h"][idx_at(seg, at)])
        for seg in segs:
            for cid, at in seg["conns"]:
                k = idx_at(seg, at)
                seg["h"][k] = max(seg["h"][k], node_h[cid])
            dilate(seg)
    # Where a freeway meets the ground: ends that no other freeway segment uses (ramp or
    # mainline meeting a surface street) and tunnel portals are pinned at grade, and the
    # road comes down to them through the network (graph distance across connectors):
    #   * ramps (links) blend from the mainline height at their junction to the street
    #     (at most 8 % where they are long enough, steeper on short ramps so they never
    #     detach from the mainline);
    #   * mainline ends descend at 5 % (e.g. I-280 at King St);
    #   * tunnel approaches descend at 5.5 % to meet the hillside at the portal.
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra
    x0, y0_, x1, y1_ = REGION_BBOX_ROADS
    offs = np.cumsum([0] + [len(sg["f"]) for sg in segs])
    N = int(offs[-1])
    is_link = np.zeros(N, bool)
    real_tn = np.zeros(N, bool)
    rows, cols, wts = [], [], []
    for q, sg in enumerate(segs):
        o = int(offs[q])
        is_link[o:o + len(sg["f"])] = sg["sub"] == "link"
        real_tn[o:o + len(sg["f"])] = sg["tn_real"]
        ds = np.maximum(np.diff(sg["s"]), 1e-3)
        a = np.arange(o, o + len(ds))
        rows.append(a)
        cols.append(a + 1)
        wts.append(ds)
    members = {}
    for q, sg in enumerate(segs):
        for cid, at in sg["conns"]:
            members.setdefault(cid, []).append((int(offs[q]) + idx_at(sg, at), q))
    jr, jc = [], []
    for mem in members.values():
        for (a, _), (b, _) in zip(mem[:-1], mem[1:]):
            jr.append(a)
            jc.append(b)
    rows = np.concatenate(rows + [np.array(jr, int)])
    cols = np.concatenate(cols + [np.array(jc, int)])
    wts = np.concatenate(wts + [np.full(len(jr), 1e-3)])
    G = csr_matrix((wts, (rows, cols)), shape=(N, N))
    H = np.concatenate([sg["h"] for sg in segs])
    street_link, street_main = [], []
    for q, sg in enumerate(segs):
        for cid, at in sg["conns"]:
            if conn_count.get(cid, 0) > 1 or at not in (0.0, 1.0):
                continue
            pt = sg["g"].interpolate(at, normalized=True)
            ll = gpd.GeoSeries([pt], crs=UTM).to_crs(4326).iloc[0]
            if not (x0 + 0.02 < ll.x < x1 - 0.02 and y0_ + 0.02 < ll.y < y1_ - 0.02):
                continue  # cut by the region edge, not a real end
            v = int(offs[q]) + idx_at(sg, at)
            (street_link if sg["sub"] == "link" else street_main).append(v)
    cap = np.full(N, np.inf)
    if real_tn.any():
        d = dijkstra(G, directed=False, indices=np.nonzero(real_tn)[0], min_only=True)
        cap = np.minimum(cap, 0.7 + SLOPE * d)
    if street_main:
        d = dijkstra(G, directed=False, indices=street_main, min_only=True)
        cap = np.minimum(cap, 0.7 + 0.05 * d)
    if street_link:
        # ramps only: distances inside the link network
        lk = np.nonzero(is_link)[0]
        pos_in = -np.ones(N, int)
        pos_in[lk] = np.arange(len(lk))
        sub = G[lk][:, lk]
        d_pin = dijkstra(sub, directed=False, indices=pos_in[street_link], min_only=True)
        # link vertices at a junction with a mainline segment
        jn = sorted({a for mem in members.values() if any(not is_link[a2] for a2, _ in mem) for a, _ in mem if is_link[a]})
        if jn:
            d_main, _, src = dijkstra(sub, directed=False, indices=pos_in[jn], min_only=True, return_predecessors=True)
            Hsrc = np.where(src >= 0, H[lk[np.maximum(src, 0)]], 0.7)
            t = np.where(np.isfinite(d_main) & np.isfinite(d_pin), d_pin / np.maximum(d_pin + d_main, 1e-3), 1.0)
            interp = 0.7 + (Hsrc - 0.7) * t
        else:
            interp = np.full(len(lk), 0.7)
        c = np.where(np.isfinite(d_pin), np.maximum(0.7 + DOWN * d_pin, interp), np.inf)
        cap[lk] = np.minimum(cap[lk], c)
    H = np.minimum(H, cap)
    # keep junctions continuous after lowering: the lowest member wins, and a road may
    # climb away from a lowered junction at no more than 8 %
    for _ in range(4):
        for mem in members.values():
            idx = [a for a, _ in mem]
            H[idx] = H[idx].min()
        for q, sg in enumerate(segs):
            o, n_ = int(offs[q]), len(sg["f"])
            hs, s_ = H[o:o + n_], sg["s"]
            for k in range(1, n_):
                hs[k] = min(hs[k], hs[k - 1] + DOWN * (s_[k] - s_[k - 1]))
            for k in range(n_ - 2, -1, -1):
                hs[k] = min(hs[k], hs[k + 1] + DOWN * (s_[k + 1] - s_[k]))
    for q, sg in enumerate(segs):
        sg["h"] = H[int(offs[q]):int(offs[q + 1])]
    log(f"roads: freeway grade pins: {len(street_main)} mainline ends, {len(street_link)} ramp ends, "
        f"{int(real_tn.sum())} tunnel vertices")

    # Dates: a mainline segment takes the year of the researched route running along it
    # (parallel, <= 150 m; a crossing freeway at an interchange doesn't count); ramps open
    # with the latest of the mainlines they connect.
    def vote(seg):
        if fw_routes is None:
            return None
        P, T, Y = fw_routes
        ys = []
        for fr in (0.1, 0.3, 0.5, 0.7, 0.9):
            g = seg["g"]
            a = g.interpolate(max(fr - 0.02, 0), normalized=True)
            b = g.interpolate(min(fr + 0.02, 1), normalized=True)
            tv = np.array([b.x - a.x, b.y - a.y])
            tv /= max(np.linalg.norm(tv), 1e-6)
            m = g.interpolate(fr, normalized=True)
            dd, ii = fw_routes_tree.query((m.x, m.y), k=12, distance_upper_bound=150)
            for d_, j in zip(np.atleast_1d(dd), np.atleast_1d(ii)):
                if np.isfinite(d_) and abs(float(T[j] @ tv)) > 0.8:
                    ys.append(Y[j])
                    break
        return float(np.median(ys)) if ys else None
    fw_routes_tree = cKDTree(fw_routes[0]) if fw_routes is not None else None
    for sg in segs:
        sg["year"] = vote(sg) if sg["sub"] != "link" else None
    # mainlines without a parallel route: nearest route within 60 m, else 1960
    for sg in segs:
        if sg["sub"] != "link" and sg["year"] is None:
            sg["year"] = 1960.0
            if fw_routes_tree is not None:
                m = sg["g"].interpolate(0.5, normalized=True)
                dd, ii = fw_routes_tree.query((m.x, m.y))
                if dd < 60:
                    sg["year"] = float(fw_routes[2][ii])
    # ramps: connected components of link segments
    parent = list(range(len(segs)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for mem in members.values():
        lq = [q for _, q in mem if segs[q]["sub"] == "link"]
        for a, b in zip(lq[:-1], lq[1:]):
            parent[find(a)] = find(b)
    comp_year = {}
    for mem in members.values():
        mains = [segs[q]["year"] for _, q in mem if segs[q]["sub"] != "link"]
        links = [q for _, q in mem if segs[q]["sub"] == "link"]
        if mains and links:
            for q in links:
                r = find(q)
                comp_year[r] = max(comp_year.get(r, -1e9), max(mains))
    for q, sg in enumerate(segs):
        if sg["sub"] == "link":
            sg["year"] = comp_year.get(find(q))
            if sg["year"] is None:
                sg["year"] = vote(sg) or 1960.0

    items = []
    for seg in segs:
        g = seg["g"]
        pts = [g.interpolate(x, normalized=True) for x in seg["f"]]
        xy = gpd.GeoSeries(pts, crs=UTM).to_crs(4326)
        lon, lat = xy.x.values, xy.y.values
        z = ground(lon, lat) + seg["h"]
        y0 = float(seg["year"])
        link = seg["sub"] == "link"
        k = K_FREEWAY if seg["cls"] == "motorway" else K_HIGHWAY
        width = 6.5 if link else (13.0 if seg["cls"] == "motorway" else 11.0)
        # split at tunnels
        keep = ~seg["tn"]
        start = None
        for j in range(len(keep) + 1):
            if j < len(keep) and keep[j]:
                start = j if start is None else start
            elif start is not None:
                if j - start >= 2:
                    sl = slice(start, j)
                    hmax = float(seg["h"][sl].max())
                    items.append((lon[sl], lat[sl], z[sl], k, width, y0, 9999.0, 2 if hmax > 4 else 0))
                start = None
    log(f"roads: {len(items)} freeway / ramp paths in 3D")
    return items


def write_paths3d(path, items):
    """items: (lon array, lat array, z array, kind, width, start, end, elevated)."""
    starts = [0]
    pos = []
    kinds, widths, years, elev = [], [], [], []
    for lon, lat, z, kind, width, y0, y1, el in items:
        pos.append(np.column_stack([lon - ORIGIN[0], lat - ORIGIN[1], z]).ravel())
        starts.append(starts[-1] + len(lon))
        kinds.append(kind)
        widths.append(width)
        years.extend((y0, y1))
        elev.append(el)
    write_columnar(path, {
        "start_indices|shuffle": np.asarray(starts, np.uint32),
        "positions|shuffle": np.concatenate(pos).astype(np.float32),
        "kind": np.asarray(kinds, np.uint8),
        "width": np.clip(np.rint(widths), 1, 255).astype(np.uint8),
        "years": np.asarray(years, np.float32),
        "elevated": np.asarray(elev, np.uint8),
    }, origin=ORIGIN, counts={"paths": len(kinds), "vertices": starts[-1]})
    log(f"roads: wrote {path.name}: {len(kinds)} paths, {starts[-1]} vertices")


def main():
    ground = Ground()

    # ---- SF streets
    st = sf_streets()
    mids = st.geometry.interpolate(0.5, normalized=True)
    ext = extent_year_of(gpd.GeoSeries(mids.values, crs=UTM))
    tree, byears = building_years()
    # a street is cut / graded just before the first buildings along it go up (2nd earliest
    # within 45 m of its middle, counting vanished buildings); the extent outlines only
    # date streets with no buildings near them
    d, idx = tree.query(np.column_stack([mids.x, mids.y]), k=8, distance_upper_bound=45)
    near = np.where(np.isfinite(d), byears[np.minimum(idx, len(byears) - 1)], np.inf)
    near.sort(axis=1)
    first_b = np.where(np.isfinite(near[:, 1]), near[:, 1], near[:, 0])
    first_b[~np.isfinite(first_b)] = np.nan
    y0 = np.where(np.isfinite(first_b), first_b - 1.0, np.where(np.isfinite(ext), ext, 1950.0))
    # streets across the 19th-century cemeteries were cut through after the graves were moved
    from sf_buildings import cemeteries
    for cpoly, cend, _ in cemeteries(UTM):
        inside = gpd.GeoSeries(mids.values, crs=UTM).within(cpoly.buffer(-10)).values
        y0 = np.where(inside, np.maximum(y0, cend + 1), y0)
    cls = pd.to_numeric(st.classcode, errors="coerce").fillna(5).values
    kind = np.where(cls <= 3, K_MAJOR, K_STREET)
    items = [(g, int(k), WIDTH[int(k)], float(a), 9999.0, 0) for g, k, a in zip(st.geometry.values, kind, y0)]
    write_paths(VIEWER_DATA / "roads-sf.bin.gz", items, ground, z_offset)

    # ---- researched routes (whole region)
    routes = pd.read_csv(MANUAL / "routes.csv")
    st_names = streets_by_name(st)
    ritems, rids = [], []
    for _, r in routes.iterrows():
        k = MODE_KIND.get(str(r["mode"]).strip())
        if k is None:
            continue
        if k == K_BART and TRANSIT_TAKES_OVER:
            continue  # BART: real tracks, stations and trains from transit.py
        el = ELEV.get(str(r.elevated).strip(), 0)
        if el == ELEV["tunnel"]:
            continue  # underground: nothing to see
        try:
            geom = route_geometry(r, st_names, None)
        except Exception as e:  # noqa: BLE001
            log(f"roads: route {r.route_id} failed: {e}")
            continue
        if geom is None:
            continue
        y0r = pd.to_numeric(r.year_start, errors="coerce")
        y1r = pd.to_numeric(r.year_end, errors="coerce")
        y0f = float(y0r) if np.isfinite(y0r) else 1900.0
        y1f = float(y1r) if np.isfinite(y1r) else 9999.0
        rid = str(r.route_id)
        # (the E Embarcadero has no SFMTA pattern: it keeps its researched line and trams)
        if k in (K_CABLE, K_STREETCAR, K_LIGHTRAIL) and y1f >= 9999 and TRANSIT_TAKES_OVER and rid != "sc_e_embarcadero":
            # still running today: from 1980 (Muni Metro) these lines are drawn and run by
            # transit.py with their real track geometry
            y1f = 1980.0
            if y1f <= y0f:
                continue
        ritems.append((geom, k, WIDTH[k], y0f, y1f, el))
        rids.append(rid)
    # freeways / highways still standing are drawn from Overture's real geometry
    # (freeways.bin.gz); the researched lines only date them. Demolished ones stay here.
    draw_routes = [it for it, rid in zip(ritems, rids) if not (it[1] in (K_FREEWAY, K_HIGHWAY) and it[4] >= 9999)
                   and rid not in LANDMARK_ROUTES]
    write_paths(VIEWER_DATA / "routes.bin.gz", draw_routes, ground, z_offset)

    # ---- region roads (outside SF)
    rr = gpd.read_parquet(RAW / "overture" / RELEASE / "roads_region.parquet")
    if rr.crs is None:
        rr = rr.set_crs(4326)
    counties = gpd.read_file(f"zip://{RAW / 'tiger' / 'tl_2024_us_county.zip'}")
    sf_poly = counties[(counties.STATEFP == "06") & (counties.COUNTYFP == "075")].geometry.iloc[0]
    rr = rr[~rr.geometry.representative_point().within(sf_poly)]
    rr = rr.to_crs(UTM)
    rr = rr[rr.geometry.geom_type == "LineString"]
    rr = rr[~rr["class"].isin(["motorway", "trunk"])]  # drawn in 3D from freeways.bin.gz
    fw = [it for it in ritems if it[1] in (K_FREEWAY, K_HIGHWAY)]
    fw_tree = None
    if fw:
        pts, yrs = [], []
        for g, _, _, a, _, _ in fw:
            for p in densify(g, 200) or []:
                pts.append((p.x, p.y))
                yrs.append(a)
        fw_tree = (cKDTree(np.array(pts)), np.array(yrs))
    from terrain_grid import grid_def as _gd  # noqa
    fb = np.load(INTERIM / "grid_region_fbuy.npy").astype(float)
    gR = grid_def("region")
    mid = rr.geometry.interpolate(0.5, normalized=True)
    mid_ll = gpd.GeoSeries(mid.values, crs=UTM).to_crs(4326)
    X = np.radians(mid_ll.x.values) * 6378137.0
    Y = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(mid_ll.y.values) / 2))
    c = np.clip(((X - gR["X0"]) / gR["res"]).astype(int), 0, gR["cols"] - 1)
    r_ = np.clip(((gR["Y0"] - Y) / gR["res"]).astype(int), 0, gR["rows"] - 1)
    fby = fb[r_, c]
    fby[(fby < 1810) | (fby > 2026)] = np.nan
    items = []
    for i, (g, klass) in enumerate(zip(rr.geometry.values, rr["class"].values)):
        if klass in ("motorway", "trunk"):
            k = K_FREEWAY if klass == "motorway" else K_HIGHWAY
            y = 1960.0
            if fw_tree is not None:
                dd, ii = fw_tree[0].query((mid.iloc[i].x, mid.iloc[i].y))
                if dd < 150:
                    y = float(fw_tree[1][ii])
        else:
            k = K_MAJOR if klass in ("primary", "secondary") else K_STREET
            y = float(fby[i]) if np.isfinite(fby[i]) and klass == "tertiary" else 1880.0
        items.append((g, k, WIDTH[k], y, 9999.0, 0))
    write_paths(VIEWER_DATA / "roads-region.bin.gz", items, ground, z_offset, step=60.0)
    # researched freeway lines with their direction, to date Overture's real geometry
    fw_routes = None
    if fw:
        P, T, Y = [], [], []
        for g, _, _, a, _, _ in fw:
            pts = densify(g, 40) or []
            xy = np.array([(p.x, p.y) for p in pts])
            if len(xy) < 2:
                continue
            tg = np.gradient(xy, axis=0)
            tg /= np.maximum(np.linalg.norm(tg, axis=1, keepdims=True), 1e-6)
            P.append(xy)
            T.append(tg)
            Y += [a] * len(xy)
        fw_routes = (np.concatenate(P), np.concatenate(T), np.array(Y))
    write_paths3d(VIEWER_DATA / "freeways.bin.gz", freeway_items(ground, fw_routes))


if __name__ == "__main__":
    main()
