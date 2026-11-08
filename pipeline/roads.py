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


def freeway_items(ground, fw_tree):
    """Motorways, trunks and ramps (Overture) with a height profile per vertex.

    Height above ground: level 1 viaducts ~12.5 m, level 2 ~22 m, other bridges 6.5 m,
    at grade 0.7 m. Approaches climb at most ~5.5 % (the profile is dilated with that
    slope cone), junctions share one height (connectors), and ramp ends that meet a
    surface street (a connector no other freeway segment uses) come down to the ground
    at ~8 %. Tunnel portions are dropped. Dates: nearest researched freeway route
    (<= 150 m), else 1960."""
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
        segs.append({"i": i, "g": g, "f": f, "s": f * L, "h": h, "tn": tn, "conns": conns, "cls": row["class"], "sub": row.subclass})

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
    # ramp ends meeting surface streets come down to the ground
    for seg in segs:
        h, s_ = seg["h"], seg["s"]
        for cid, at in seg["conns"]:
            if conn_count.get(cid, 0) > 1 or at not in (0.0, 1.0) or seg["sub"] != "link":
                continue
            d = np.abs(s_ - s_[idx_at(seg, at)])
            h[:] = np.minimum(h, 0.7 + DOWN * d)

    items = []
    for seg in segs:
        g = seg["g"]
        pts = [g.interpolate(x, normalized=True) for x in seg["f"]]
        xy = gpd.GeoSeries(pts, crs=UTM).to_crs(4326)
        lon, lat = xy.x.values, xy.y.values
        z = ground(lon, lat) + seg["h"]
        y0 = 1960.0
        if fw_tree is not None:
            mid = g.interpolate(0.5, normalized=True)
            dd, ii = fw_tree[0].query((mid.x, mid.y))
            if dd < 150:
                y0 = float(fw_tree[1][ii])
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
    d, idx = tree.query(np.column_stack([mids.x, mids.y]), k=6, distance_upper_bound=60)
    near = np.where(np.isfinite(d), byears[np.minimum(idx, len(byears) - 1)], np.nan)
    first_b = np.nanmin(np.where(np.isfinite(near), near, np.inf), axis=1)
    first_b[~np.isfinite(first_b)] = np.nan
    y0 = np.where(np.isfinite(ext), ext, np.where(np.isfinite(first_b), first_b - 1, 1950.0))
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
        ritems.append((geom, k, WIDTH[k], float(y0r) if np.isfinite(y0r) else 1900.0, float(y1r) if np.isfinite(y1r) else 9999.0, el))
        rids.append(str(r.route_id))
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
    write_paths3d(VIEWER_DATA / "freeways.bin.gz", freeway_items(ground, fw_tree))


if __name__ == "__main__":
    main()
