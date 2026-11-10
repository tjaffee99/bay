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

from common import INTERIM, MANUAL, RAW, TABLES, VIEWER_DATA, log
from download_overture import RELEASE
from export_columnar import write_columnar
from terrain_grid import grid_def
from extent import in_extent

ORIGIN = (-122.44, 37.76)
UTM = "EPSG:32610"

# kinds (keep in sync with viewer/src/layers/roads.ts)
K_STREET, K_MAJOR, K_FREEWAY, K_HIGHWAY, K_CABLE, K_STREETCAR, K_RAIL, K_KEY, K_BART, K_FERRY, K_LIGHTRAIL = range(11)
MODE_KIND = {"freeway": K_FREEWAY, "highway": K_HIGHWAY, "cable_car": K_CABLE, "streetcar": K_STREETCAR,
             "horsecar": K_STREETCAR, "steam_railroad": K_RAIL, "interurban": K_RAIL, "key_system": K_KEY,
             "bart": K_BART, "ferry": K_FERRY, "light_rail": K_LIGHTRAIL,
             # road bridges (San Mateo, Dumbarton, Carquinez, Richmond-San Rafael, Benicia…): the
             # standing ones date Overture's geometry like any highway, the replaced ones are drawn
             "bridge": K_HIGHWAY}
# BART and today's Muni lines come from transit.py (transit.bin.gz) when it has run
TRANSIT_TAKES_OVER = True
# edge of the region extracts (download_overture.REGION_BBOX): freeway ends there are cuts
REGION_BBOX_ROADS = (-123.68, 36.78, -121.16, 38.91)
# routes drawn by a landmark model instead (double-deck viaduct in landmarks/city.ts)
LANDMARK_ROUTES = {"fwy_embarcadero", "br_carquinez_1927"}
# bridge decks drawn by a landmark model (lon0, lat0, lon1, lat1): the generic deck slabs and
# bents of the freeway layer are left out inside the box
LANDMARK_BRIDGE_BOXES = [
    (-121.7560, 38.0167, -121.7470, 38.0427),   # Antioch Bridge 1978 (landmarks/coastsouth.ts)
    (-122.1302, 38.0486, -122.1262, 38.0514),   # I-780 connector of the 2007 Benicia span (landmarks/northbay.ts)
]
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
    allb = allb[allb.start_year.values >= 1770]  # Ohlone villages (from 1700) don't date streets
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
# routes.csv lines replaced by the traced historic railways (data/manual/historic_rail.geojson)
RAIL_SUPERSEDED = {"rr_sfsj_valencia", "rr_sfsj_main_sf", "rr_sfsj_ocean_view", "rr_sfsj_peninsula", "rr_ocean_shore_sf",
                   "rr_ocean_shore_coast", "rr_cp_long_wharf", "rr_sp_oakland_mole", "rr_alameda_mole", "rr_sf_oakland_rr",
                   "ks_mole", "ks_trunk", "ir_40_san_mateo", "sn_oakland"}


def historic_rail():
    """Historic railways, interurbans and rail piers of the region, traced from today's
    track, mapped abandoned grades, 1895-1919 USGS topo sheets and Sanborn maps, dated per
    segment (data/manual/historic_rail.geojson, data/research/historic_rail.md)."""
    p = MANUAL / "historic_rail.geojson"
    if not p.exists():
        return []
    h = gpd.read_file(p).to_crs(UTM)
    KIND = {"rail": K_RAIL, "narrow_gauge": K_RAIL, "interurban": K_RAIL, "streetcar": K_STREETCAR, "pier": K_RAIL}
    # rail bridges, piers and trestles sit a few metres over the creek / water, not at
    # road-bridge height
    EL = {"ground": 0, "bridge": ELEV["embankment"], "tunnel": ELEV["tunnel"], "pier": ELEV["embankment"],
          "trestle": ELEV["embankment"]}
    items = []
    for g, mode, y0, y1, el in zip(h.geometry, h["mode"], h["year_start"], h["year_end"], h["elevated"]):
        y0 = pd.to_numeric(y0, errors="coerce")
        y1 = pd.to_numeric(y1, errors="coerce")
        if g is None or not np.isfinite(y0):
            continue
        k = KIND.get(str(mode), K_RAIL)
        for part in getattr(g, "geoms", [g]):
            if part.geom_type == "LineString" and part.length > 5:
                items.append((part, k, WIDTH[k], float(y0), float(y1) if np.isfinite(y1) else 9999.0, EL.get(str(el), 0)))
    log(f"roads: {len(items)} historic railway segments")
    return items


def sanborn_tracks():
    """Railway tracks traced from the Sanborn maps (data/manual/sanborn/<area>_<year>_tracks.geojson:
    rail yards, spurs, the State Belt). A track drawn on consecutive maps (>= 60 % of it
    within 4 m of the next map's tracks) is one track; it is laid between the previous map
    and its first map (well before, if that is the area's first map), and taken up between
    its last map and the next one that covers the area — or, if still on the last map, at
    the clearance of a redevelopment area it lies in (Mission Bay 1998-2008), else 15 years on."""
    files = sorted(glob.glob(str(MANUAL / "sanborn" / "*_[12][0-9][0-9][0-9]_tracks.geojson")))
    if not files:
        return []
    from sf_buildings import redevelopment_areas
    areas = redevelopment_areas()
    frames = []
    for f in files:
        stem = f.split("/")[-1][: -len("_tracks.geojson")]
        area, yr = stem.rsplit("_", 1)
        t = gpd.read_file(f)
        if not len(t):
            continue
        t = t.to_crs(UTM)
        t["area"], t["map_year"] = area, float(yr)
        frames.append(t[["area", "map_year", "geometry"]])
    T = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=UTM)
    T = T[T.geometry.notna() & T.geometry.geom_type.isin(["LineString", "MultiLineString"])].explode(index_parts=False)
    T = T[T.geometry.length > 10].reset_index(drop=True)
    items = []
    for area, A in T.groupby("area"):
        years = sorted(A.map_year.unique())
        cov = {}
        cf = MANUAL / "sanborn" / f"{area}_coverage.geojson"
        if cf.exists():
            c = gpd.read_file(cf).to_crs(UTM)
            if "map_year" in c:
                cov = {float(y): shapely.union_all(g.geometry.values) for y, g in c.groupby("map_year")}
        maps = {y: shapely.union_all(A[A.map_year == y].geometry.values).buffer(4.0) for y in years}
        for k, y in enumerate(years):
            for g in A[A.map_year == y].geometry.values:
                if k + 1 < len(years) and g.intersection(maps[years[k + 1]]).length >= 0.6 * g.length:
                    continue  # still there on the next map
                first = y
                for kk in range(k - 1, -1, -1):
                    if g.intersection(maps[years[kk]]).length >= 0.6 * g.length:
                        first = years[kk]
                    else:
                        break
                kf = years.index(first)
                start = (years[kf - 1] + first) / 2 if kf > 0 else first - 10
                mid = g.interpolate(0.5, normalized=True)
                if k + 1 < len(years) and (not cov or mid.within(cov.get(years[k + 1], mid.buffer(1)))):
                    end = (y + years[k + 1]) / 2
                else:
                    ends = [cs + (ce - cs) * 0.5 for poly, cs, ce, _f, _a in areas if mid.within(poly) and cs > y]
                    end = min(ends) if ends else y + 15
                if end > start + 1:
                    items.append((g, K_RAIL, 3, float(start), float(end), 0))
    log(f"roads: {len(items)} railway tracks traced from Sanborn maps")
    return items


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


def freeway_items(ground, fw_routes, buildings=None, streets=None):
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
            if "Golden Gate Bridge" in nm or "Carquinez Bridge" in nm or "Benicia-Martinez Bridge" in nm:
                tn = tn | br
            tn = tn | (br & bay_bridge & over_water)
            # other bridges with a landmark model: the whole modelled structure (approach
            # spans included), by the box of its deck
            for x0_, y0_, x1_, y1_ in LANDMARK_BRIDGE_BOXES:
                tn = tn | (br & (lo_ > x0_) & (lo_ < x1_) & (la_ > y0_) & (la_ < y1_))
        conns = [(c["connector_id"], float(c["at"])) for c in (row.connectors if row.connectors is not None else [])]
        for cid, _ in conns:
            conn_count[cid] = conn_count.get(cid, 0) + 1
        segs.append({"i": i, "g": g, "f": f, "s": f * L, "h": h, "tn": tn, "tn_real": tn_real, "conns": conns,
                     "cls": row["class"], "sub": row.subclass, "bounds": row.geometry.bounds,
                     "name": row["name"] if isinstance(row["name"], str) else ""})
    # the extract is wider than the map (decision 32): heights and junctions are worked out on
    # the whole network, but only roads inside the map's extent (+ margin) are written
    inside = in_extent(shapely.points([(sg["bounds"][0] + sg["bounds"][2]) / 2 for sg in segs],
                                      [(sg["bounds"][1] + sg["bounds"][3]) / 2 for sg in segs]))
    for sg, ok in zip(segs, inside):
        sg["in"] = bool(ok)

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
    # mainlines without a parallel route: nearest route within 60 m, else 1960 (motorways;
    # `estimated`) — trunk roads without a researched route are mostly old highways and
    # arterials (Woodside Rd, Vallecitos Rd, Kirker Pass Rd, 19th Ave, Van Ness Ave…), dated
    # like the other main roads: a year before the buildings along them (date_by_buildings)
    undated, n_def = [], 0
    for q, sg in enumerate(segs):
        if sg["sub"] != "link" and sg["year"] is None:
            sg["year"] = 1960.0
            if fw_routes_tree is not None:
                m = sg["g"].interpolate(0.5, normalized=True)
                dd, ii = fw_routes_tree.query((m.x, m.y))
                if dd < 60:
                    sg["year"] = float(fw_routes[2][ii])
                    continue
            if sg["cls"] == "trunk":
                undated.append(q)
            elif sg["in"]:
                n_def += 1
    if undated:
        mids = gpd.GeoSeries([segs[q]["g"].interpolate(0.5, normalized=True) for q in undated], crs=UTM).to_crs(4326)
        yrs, n_b = date_by_buildings([segs[q]["g"] for q in undated], mids, 1870.0)
        # one road, one year: a through road does not open house by house — every stretch of a
        # named road takes the early quartile of its stretches (as neighbourhoods are dated)
        by_name = {}
        for q, y in zip(undated, yrs):
            if segs[q]["in"]:
                by_name.setdefault(segs[q]["name"], []).append(float(y))
        for q, y in zip(undated, yrs):
            ys = by_name.get(segs[q]["name"]) if segs[q]["name"] else None
            segs[q]["year"] = float(np.quantile(ys, 0.25)) if ys and len(ys) >= 4 else float(y)
        log(f"roads: {len(undated)} trunk road segments without a researched route dated like main roads "
            f"({n_b} by the buildings along them)")
    log(f"roads: {n_def} motorway segments inside the map left at the 1960 default (no researched route)")
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

    # Nothing drives through a building: a group of ramps (or a mainline stretch whose
    # date is clearly off) opens only after the buildings standing where it runs are gone
    # (e.g. the Transit Center bus ramps of 2018 inherited I-80's 1936 date and crossed
    # 1910s warehouses). Buildings = today's + vanished ones, if taller than the road there.
    if buildings is not None:
        from shapely import STRtree
        bg, bstart, bend, bh = buildings
        btree = STRtree(bg)
        bump = np.full(len(segs), -np.inf)
        for q, sg in enumerate(segs):
            b0 = sg["bounds"]
            if not (-122.53 < b0[0] and b0[2] < -122.35 and b0[1] > 37.70):
                continue  # buildings exist for San Francisco only (so far)
            for x, hq in zip(sg["f"], sg["h"]):
                pt = sg["g"].interpolate(x, normalized=True)
                for j in btree.query(pt, predicate="within"):
                    if bh[j] > hq - 1.0 and bstart[j] < sg["year"] + 0.5 < bend[j] < 9000:
                        bump[q] = max(bump[q], bend[j] + 0.3)
        comp_bump = {}
        for q, sg in enumerate(segs):
            if sg["sub"] == "link" and np.isfinite(bump[q]):
                r = find(q)
                comp_bump[r] = max(comp_bump.get(r, -np.inf), bump[q])
        nb = 0
        for q, sg in enumerate(segs):
            if sg["sub"] == "link":
                nb_ = comp_bump.get(find(q), -np.inf)
                if nb_ > sg["year"]:
                    sg["year"] = float(nb_)
                    nb += 1
            elif np.isfinite(bump[q]) and bump[q] - sg["year"] > 8:
                sg["year"] = float(bump[q])
                nb += 1
        log(f"roads: {nb} freeway / ramp segments wait for the buildings in their way to go")

    # sample positions once
    for sg in segs:
        g = sg["g"]
        pts = [g.interpolate(x, normalized=True) for x in sg["f"]]
        sg["xy"] = np.array([(p.x, p.y) for p in pts])

    # ramp / mainline ends meeting a street: one more vertex on the street centreline,
    # so the ramp visibly joins it instead of stopping beside it
    if streets is not None:
        from shapely import STRtree
        from shapely.geometry import Point as _P
        stree = STRtree(streets)
        n_snap = 0
        for sg in segs:
            for cid, at in sg["conns"]:
                if conn_count.get(cid, 0) > 1 or at not in (0.0, 1.0) or sg["tn"][0 if at == 0.0 else -1]:
                    continue
                e = sg["xy"][0] if at == 0.0 else sg["xy"][-1]
                cand = stree.query(_P(e).buffer(30))
                if not len(cand):
                    continue
                best = min(cand, key=lambda j: streets[j].distance(_P(e)))
                line = streets[best]
                d = line.distance(_P(e))
                if d < 2 or d > 30:
                    continue
                q = line.interpolate(line.project(_P(e)))
                extra = np.array([[q.x, q.y]])
                hh = np.array([0.7])
                if at == 0.0:
                    sg["xy"] = np.vstack([extra, sg["xy"]])
                    sg["h"] = np.concatenate([hh, sg["h"]])
                    sg["tn"] = np.concatenate([[False], sg["tn"]])
                    sg["f"] = np.concatenate([[0.0], sg["f"]])
                else:
                    sg["xy"] = np.vstack([sg["xy"], extra])
                    sg["h"] = np.concatenate([sg["h"], hh])
                    sg["tn"] = np.concatenate([sg["tn"], [False]])
                    sg["f"] = np.concatenate([sg["f"], [1.0]])
                n_snap += 1
        log(f"roads: {n_snap} freeway / ramp ends extended onto their street")

    # Draw continuous roads: chain segments end to end through connectors joining exactly
    # two segments of the same road kind and date (Overture splits a road at every
    # connector; drawn one by one they read as loose straight pieces with gaps).
    end_nodes = {}
    for q, sg in enumerate(segs):
        for cid, at in sg["conns"]:
            if at in (0.0, 1.0):
                end_nodes.setdefault(cid, []).append((q, at))

    def key_of(sg):
        return (sg["cls"], sg["sub"] == "link", float(sg["year"]))

    def next_seg(q, at):
        """the segment continuing segment q beyond its end `at` (0 or 1), or None"""
        sg = segs[q]
        cid = next((c for c, a in sg["conns"] if a == at), None)
        if cid is None or conn_count.get(cid, 0) != 2:
            return None
        mem = end_nodes.get(cid, [])
        others = [(q2, a2) for q2, a2 in mem if q2 != q]
        if len(others) != 1:
            return None
        q2, a2 = others[0]
        if key_of(segs[q2]) != key_of(sg):
            return None
        return q2, a2

    used = np.zeros(len(segs), bool)
    chains = []
    for q in range(len(segs)):
        if used[q]:
            continue
        # walk back to the start of the chain
        cur, cur_at = q, 0.0
        seen = {q}
        while True:
            nx = next_seg(cur, cur_at)
            if nx is None or nx[0] in seen or used[nx[0]]:
                break
            cur, cur_at = nx[0], 1.0 - nx[1]
            seen.add(cur)
        # now walk forward from cur, entering at cur_at
        chain = []
        c, enter = cur, cur_at
        while c is not None and not used[c]:
            used[c] = True
            chain.append((c, enter == 1.0))  # reversed if we enter at its end
            nx = next_seg(c, 1.0 - enter)
            if nx is None:
                break
            c, enter = nx
        chains.append(chain)

    items = []
    for chain in chains:
        if not any(segs[q]["in"] for q, _ in chain):
            continue  # outside the map
        XY, Hh, TN = [], [], []
        for k_, (q, rev) in enumerate(chain):
            sg = segs[q]
            xy, hq, tq = sg["xy"], sg["h"], sg["tn"]
            if rev:
                xy, hq, tq = xy[::-1], hq[::-1], tq[::-1]
            if k_ > 0:
                xy, hq, tq = xy[1:], hq[1:], tq[1:]
            XY.append(xy)
            Hh.append(hq)
            TN.append(tq)
        XY = np.vstack(XY)
        Hh = np.concatenate(Hh)
        TN = np.concatenate(TN)
        sg0 = segs[chain[0][0]]
        ll = gpd.GeoSeries(gpd.points_from_xy(XY[:, 0], XY[:, 1]), crs=UTM).to_crs(4326)
        lon, lat = ll.x.values, ll.y.values
        z = ground(lon, lat) + Hh
        y0 = float(sg0["year"])
        link = sg0["sub"] == "link"
        k = K_FREEWAY if sg0["cls"] == "motorway" else K_HIGHWAY
        width = 6.5 if link else (13.0 if sg0["cls"] == "motorway" else 11.0)
        # split at tunnels (and at the Bay Bridge / Golden Gate spans the landmarks draw)
        keep = ~TN
        start = None
        for j in range(len(keep) + 1):
            if j < len(keep) and keep[j]:
                start = j if start is None else start
            elif start is not None:
                if j - start >= 2:
                    sl = slice(start, j)
                    hmax = float(Hh[sl].max())
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
    # streets cut through existing blocks later (data/tables/street_dates.csv, researched:
    # Columbus Ave was Montgomery Avenue, cut diagonally through North Beach in 1873-74)
    sd = TABLES / "street_dates.csv"
    if sd.exists():
        t = pd.read_csv(sd)
        names = (st.street.fillna("").str.upper().str.strip() + " " + st.st_type.fillna("").str.upper().str.strip()).str.strip().values
        for r in t.itertuples():
            m = names == str(r.street).upper().strip()
            # rule (optional column): blank = not before that year (a street cut through older
            # blocks, a tunnel); `set` = the researched opening year replaces the estimate (a
            # boulevard without buildings along it, which the building rule leaves at 1950)
            if str(getattr(r, "rule", "")).strip().lower() == "set":
                y0 = np.where(m, float(r.year_start), y0)
            else:
                y0 = np.where(m, np.maximum(y0, float(r.year_start)), y0)
            log(f"roads: {int(m.sum())} segments of {r.street} from {r.year_start}")
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
        # (and VTA light rail in the Santa Clara Valley, which transit.py does not cover)
        if (k in (K_CABLE, K_STREETCAR, K_LIGHTRAIL) and y1f >= 9999 and TRANSIT_TAKES_OVER and rid != "sc_e_embarcadero"
                and not rid.startswith("vta_")):
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
                   and rid not in LANDMARK_ROUTES and rid not in RAIL_SUPERSEDED]
    draw_routes += sanborn_tracks()
    draw_routes += historic_rail()
    write_paths(VIEWER_DATA / "routes.bin.gz", draw_routes, ground, z_offset)

    # ---- region roads (outside SF)
    rr = gpd.read_parquet(RAW / "overture" / RELEASE / "roads_region.parquet")
    if rr.crs is None:
        rr = rr.set_crs(4326)
    counties = gpd.read_file(f"zip://{RAW / 'tiger' / 'tl_2024_us_county.zip'}")
    sf_poly = counties[(counties.STATEFP == "06") & (counties.COUNTYFP == "075")].geometry.iloc[0]
    rr = rr[~rr.geometry.representative_point().within(sf_poly)]
    rr = rr[in_extent(rr.geometry.representative_point())]
    rr = rr.to_crs(UTM)
    rr = rr[rr.geometry.geom_type == "LineString"]
    rr = rr[~rr["class"].isin(["motorway", "trunk"])]  # drawn in 3D from freeways.bin.gz
    # only roads that still stand date today's geometry: a replaced road (Bayshore Highway
    # 1929-47, Eastshore Highway, Doyle Drive, the 1929 San Mateo bridge, the Cypress viaduct)
    # is drawn from its own line and must not hand its year to the freeway built over it
    fw = [it for it in ritems if it[1] in (K_FREEWAY, K_HIGHWAY) and it[4] >= 9999]
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
    # main roads: like the streets, a year before the buildings along them went up (the
    # old county roads — primary / secondary — no later than their towns' first
    # buildings, and before 1880 in open country, when no buildings date them)
    by_bld, n_bld = date_by_buildings(rr.geometry.values, mid_ll, np.where(rr["class"].isin(["primary", "secondary"]).values, 1870.0, 1900.0))
    dated, dropped = segment_overrides()
    rids_ = rr["id"].astype(str).values
    by_bld = np.array([max(y, dated[i]) if i in dated else y for y, i in zip(by_bld, rids_)])
    by_bld = np.where(np.isin(rids_, list(dropped)), np.nan, by_bld)
    log(f"region roads: {len(rr)} segments, {n_bld} dated by the buildings along them")
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
            y = float(by_bld[i])
            if not np.isfinite(y):
                continue  # researched: not a road
        items.append((g, k, WIDTH[k], y, 9999.0, 0))
    # the old streets of cleared corridors (region_predecessors.clearance_fill): I-980,
    # Cypress, SR-87, I-280, Acorn… stood until the clearance
    cpath = INTERIM / "clearance_streets.parquet"
    if cpath.exists():
        cst = gpd.read_parquet(cpath).to_crs(UTM)
        for g, y0, y1 in zip(cst.geometry, cst.start_year, cst.end_year):
            if g is not None and g.geom_type == "LineString":
                items.append((g, K_STREET, WIDTH[K_STREET], float(y0), float(y1), 0))
        log(f"region roads: + {len(cst)} old streets of cleared corridors")
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
    # buildings in the way (today's + vanished) and the streets ramps join
    bl = [gpd.read_parquet(INTERIM / "sf_buildings.parquet")[["start_year", "end_year", "height", "geometry"]]]
    if (INTERIM / "sf_predecessors.parquet").exists():
        _p = gpd.read_parquet(INTERIM / "sf_predecessors.parquet")[["start_year", "end_year", "height", "geometry"]]
        bl.append(_p[_p.start_year >= 1770])
    bdf = gpd.GeoDataFrame(pd.concat(bl, ignore_index=True), crs=4326).to_crs(UTM)
    bdf = bdf[bdf.geometry.notna() & bdf.geometry.is_valid]
    buildings = (bdf.geometry.values, bdf.start_year.values.astype(float), bdf.end_year.values.astype(float),
                 bdf.height.fillna(7).values.astype(float))
    street_lines = list(st.geometry.values) + list(rr.geometry.values)
    write_paths3d(VIEWER_DATA / "freeways.bin.gz", freeway_items(ground, fw_routes, buildings, street_lines))


LOCAL_Z = 12  # tiles of the suburban street grid (~9.8 km), loaded from zoom 12.5
LOCAL_LOW_Z = 10  # simplified street grid for city scale (zoom 9-12.5)


def segment_overrides():
    """Overture road segments researched on vanished large sites
    (data/manual/vanished_sites/road_segments.csv): `date` = not before `not_before`
    (Bay Meadows II streets didn't exist while the racetrack did), `drop` = not a road."""
    p = MANUAL / "vanished_sites" / "road_segments.csv"
    if not p.exists():
        return {}, set()
    t = pd.read_csv(p)
    nb = pd.to_numeric(t.not_before, errors="coerce")
    dated = {str(i): float(y) for i, a, y in zip(t.segment_id, t.action, nb) if str(a) == "date" and np.isfinite(y)}
    dropped = {str(i) for i, a in zip(t.segment_id, t.action) if str(a) == "drop"}
    return dated, dropped


def date_by_buildings(lines_utm, mid_ll, default):
    """A street is cut a year before the 2nd-earliest building within 45 m of it goes up
    (today's footprints and vanished ones: region_building_points.parquet), as in SF;
    with one building, a year before it; without, the HISDAC first built-up year of its
    cell; else `default` (scalar or array). Never before the ground under it (fill).
    Returns (years, number dated by buildings)."""
    from airports import land_year
    seg, px, py = [], [], []
    for i, g in enumerate(lines_utm):
        n = max(2, int(g.length // 20) + 1)
        pts = shapely.line_interpolate_point(g, np.linspace(0, g.length, n))
        seg.append(np.full(n, i))
        px.append(shapely.get_x(pts))
        py.append(shapely.get_y(pts))
    seg, px, py = np.concatenate(seg), np.concatenate(px), np.concatenate(py)
    b = pd.read_parquet(INTERIM / "region_building_points.parquet", columns=["lon", "lat", "start_year"])
    b = b[b.start_year >= 1770]  # Ohlone villages (from 1700) don't date streets
    bu = gpd.GeoSeries(gpd.points_from_xy(b.lon, b.lat), crs=4326).to_crs(UTM)
    tree = cKDTree(np.column_stack([bu.x.values, bu.y.values]))
    by = b.start_year.values.astype(float)
    d, idx = tree.query(np.column_stack([px, py]), k=4, distance_upper_bound=45)
    yrs = np.where(np.isfinite(d), by[np.minimum(idx, len(by) - 1)], np.nan)
    flat = pd.DataFrame({"s": np.repeat(seg, 4), "y": yrs.ravel()}).dropna().sort_values(["s", "y"])
    flat["r"] = flat.groupby("s").cumcount()
    n = len(lines_utm)
    year = np.full(n, np.nan)
    first = flat[flat.r == 0].set_index("s").y
    second = flat[flat.r == 1].set_index("s").y
    year[first.index.values] = first.values
    year[second.index.values] = second.values
    year -= 1.0
    n_bld = int(np.isfinite(year).sum())
    gR = grid_def("region")
    fb = np.load(INTERIM / "grid_region_fbuy.npy").astype(float)
    X = np.radians(mid_ll.x.values) * 6378137.0
    Y = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(mid_ll.y.values) / 2))
    c = np.clip(((X - gR["X0"]) / gR["res"]).astype(int), 0, gR["cols"] - 1)
    r_ = np.clip(((gR["Y0"] - Y) / gR["res"]).astype(int), 0, gR["rows"] - 1)
    fby = fb[r_, c]
    fby[(fby < 1810) | (fby > 2026)] = np.nan
    year = np.where(np.isfinite(year), year, fby - 1.0)
    year = np.where(np.isfinite(year), year, default)
    ly = land_year(mid_ll.x.values, mid_ll.y.values)
    year = np.where(np.isfinite(ly), np.maximum(year, ly + 0.5), year)
    return year, n_bld


def local_streets():
    """Residential streets, lanes and alleys outside San Francisco (Overture,
    download_overture.local_roads) in z12 tiles: viewer/public/data/region-streets/.
    A street is cut a year before the 2nd-earliest building within 45 m of it goes up
    (today's footprints and vanished ones: region_building_points.parquet), as in SF;
    without buildings along it, the HISDAC first built-up year of its cell, else 1925
    (country lanes). Never before the ground under it (bay fill)."""
    import json
    import shutil
    rr = gpd.read_parquet(RAW / "overture" / RELEASE / "roads_local.parquet")
    if rr.crs is None:
        rr = rr.set_crs(4326)
    counties = gpd.read_file(f"zip://{RAW / 'tiger' / 'tl_2024_us_county.zip'}")
    sf_poly = counties[(counties.STATEFP == "06") & (counties.COUNTYFP == "075")].geometry.iloc[0]
    rr = rr[rr.geometry.geom_type == "LineString"]
    rr = rr[~rr.geometry.representative_point().within(sf_poly)].reset_index(drop=True)
    rr = rr[in_extent(rr.geometry.representative_point())].reset_index(drop=True)
    ru = rr.to_crs(UTM)
    mid = rr.geometry.interpolate(0.5, normalized=True)
    year, n_bld = date_by_buildings(ru.geometry.values, mid, 1925.0)
    dated, dropped = segment_overrides()
    ids = rr["id"].astype(str).values
    year = np.array([max(y, dated[i]) if i in dated else y for y, i in zip(year, ids)])
    keep = ~np.isin(ids, list(dropped))
    rr, ru, mid, year = rr[keep].reset_index(drop=True), ru[keep].reset_index(drop=True), mid[keep].reset_index(drop=True), year[keep]
    log(f"local streets: {len(rr)} segments, {n_bld} dated by the buildings along them, "
        f"{int(np.isin(ids, list(dated)).sum())} researched dates, {int((~keep).sum())} dropped")
    # tiles
    n = 2 ** LOCAL_Z
    tx = np.floor((mid.x.values + 180) / 360 * n).astype(int)
    lat = np.radians(mid.y.values)
    ty = np.floor((1 - np.log(np.tan(lat) + 1 / np.cos(lat)) / np.pi) / 2 * n).astype(int)
    out = VIEWER_DATA / "region-streets"
    if out.exists():
        shutil.rmtree(out)
    ground = Ground()
    index = []
    df = pd.DataFrame({"tx": tx, "ty": ty, "i": np.arange(len(rr))})
    for (x, y), grp in df.groupby(["tx", "ty"]):
        items = [(ru.geometry.values[i], K_STREET, WIDTH[K_STREET] - (2 if rr["class"].values[i] == "service" else 0),
                  float(year[i]), 9999.0, 0) for i in grp.i.values]
        p = out / str(LOCAL_Z) / str(x) / f"{y}.bin.gz"
        p.parent.mkdir(parents=True, exist_ok=True)
        write_paths(p, items, ground, z_offset, step=30.0)
        index.append({"x": int(x), "y": int(y), "n": len(items)})
    # city scale: the same streets, simplified to 8 m and not draped vertex by vertex
    nL = 2 ** LOCAL_LOW_Z
    tx = np.floor((mid.x.values + 180) / 360 * nL).astype(int)
    ty = np.floor((1 - np.log(np.tan(lat) + 1 / np.cos(lat)) / np.pi) / 2 * nL).astype(int)
    simp = ru.geometry.simplify(8.0).values
    low = []
    df = pd.DataFrame({"tx": tx, "ty": ty, "i": np.arange(len(rr))})
    for (x, y), grp in df.groupby(["tx", "ty"]):
        items = [(simp[i], K_STREET, WIDTH[K_STREET], float(year[i]), 9999.0, 0) for i in grp.i.values]
        p = out / str(LOCAL_LOW_Z) / str(x) / f"{y}.bin.gz"
        p.parent.mkdir(parents=True, exist_ok=True)
        write_paths(p, items, ground, z_offset, step=400.0)
        low.append({"x": int(x), "y": int(y), "n": len(items)})
    (out / "index.json").write_text(json.dumps({"z": LOCAL_Z, "tiles": index, "low": {"z": LOCAL_LOW_Z, "tiles": low}}))
    log(f"local streets: {len(index)} z{LOCAL_Z} tiles + {len(low)} z{LOCAL_LOW_Z} tiles -> {out}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "local":
        local_streets()
        sys.exit(0)
    main()
    local_streets()
