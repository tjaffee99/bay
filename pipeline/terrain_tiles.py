"""Stage: time-varying terrain tiles (elevation + land-cover history + decorations).

For every lattice vertex we derive a short land-cover *history* — up to four
covers with three change years — from data wherever possible:

  natural (pre-1769)  SFEI c.1800 baylands (bay, tidal flat, marsh, ponds, riparian,
                      grassland); WorldCover 2021 for upland cover (forest, scrub,
                      grass, bare/rock, wetland); San Francisco's planted forests
                      and built-up land were dunes/scrub (landcover_history.csv when
                      present, else west-SF-dunes rule)
  diking              SFEI c.1800 marsh/flat that SFEI c.1998 shows as salt pond /
                      diked or agricultural bayland  (year: fill_zones.csv / default)
  fill                SFEI c.1800 water/flat/marsh that is land today
                      (year: fill_zones.csv, else just before urbanisation)
  agriculture         landcover_history.csv farm/orchard/vineyard eras, else
                      flat non-urban-by-1850 land outside SF -> farmland 1855,
                      Santa Clara Valley floor -> orchards 1880 (rule, `estimated`)
  urban               SF building years (rasterised), else HISDAC-US first built-up
                      year (250 m), else nearest HISDAC year
  parks / planting    data/tables/parks.csv + sf-ground woods (SF)

Decorations per tile: trees on real WorldCover tree pixels (urban/park trees
dated by their area; natural forest always present), orchard rows and
farmsteads (procedural placement inside dated farm/orchard cells).

Tile file (BAYT): tiles/{z}/{x}/{y}.bin.gz with columns
  elev i16 (decimetres), cover u8[5] per vertex, year u16[4] per vertex
  ((year-1000)*10, 0 = no change), deco_pos u16[2], deco_kind u8,
  deco_size u8 (metres), deco_years u16[2] (start, end; 0 = open)

Outputs: viewer/public/tiles/terrain/{z}/{x}/{y}.bin.gz, viewer/public/data/elevation.bin.gz
"""
from __future__ import annotations

import json
import math
import zlib

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from rasterio import features
from rasterio.transform import Affine
from scipy import ndimage

from common import INTERIM, MANUAL, RAW, TABLES, VIEWER_DATA, log
from export_columnar import write_columnar
from terrain_grid import GRIDS, VERTS, grid_def

TILES = VIEWER_DATA.parent / "tiles" / "terrain"

# ---- cover codes (shared with viewer/src/layers/terrain.ts) -------------------
from covers import (BEACH, BURNED, DEEP, DIKED, DUNES, FARM, FILL, FLAT, FOREST, GRASS, LANDCOVER_TABLE,  # noqa: E402
                    MARSH, OAK, ORCHARD, PARK, PASTURE, RESERVOIR, RIPARIAN, ROCK, SALTPOND, SCRUB, SHALLOW,
                    SUBURB, URBAN, VINEYARD, WET, WETLAND)
COVER_NAMES = ["deep_water", "shallow_water", "tidal_flat", "tidal_marsh", "beach", "dunes", "grassland",
               "scrub", "oak_woodland", "forest", "farmland", "orchard", "vineyard", "pasture", "salt_pond",
               "diked_wetland", "urban", "park", "rock", "riparian", "fill", "wetland", "reservoir", "burned",
               "suburban"]
# decoration kinds
D_BROADLEAF, D_CONIFER, D_PALM, D_ORCHARD, D_FARMHOUSE, D_SHRUB, D_FARMYARD = range(7)

SF_BOX = (-122.5155, 37.7080, -122.3550, 37.8325)
SANTA_CLARA_VALLEY = (-122.10, 37.15, -121.60, 37.50)
WINE_VALLEYS = (-122.95, 38.15, -122.20, 38.70)


def enc_year(y):
    y = np.asarray(y, dtype=float)
    out = np.where(np.isfinite(y), np.clip(np.rint((y - 1000.0) * 10), 1, 65535), 0)
    return out.astype(np.uint16)


def load_grid(name):
    g = grid_def(name)
    d = {k: np.load(INTERIM / f"grid_{name}_{k}.npy") for k in ("elev", "wc", "fbuy", "b1800", "b1998", "hist")}
    d["elev"][d["elev"] < -500] = np.nan
    return g, d


def lonlat_of(g):
    rows, cols = g["rows"], g["cols"]
    X = g["X0"] + np.arange(cols) * g["res"]
    Y = g["Y0"] - np.arange(rows) * g["res"]
    lon = X / 20037508.342789244 * 180.0
    lat = np.degrees(2 * np.arctan(np.exp(Y / 6378137.0)) - np.pi / 2)
    return np.meshgrid(lon, lat)


def rasterize_on(g, shapes, fill=np.nan, dtype="float32"):
    t = Affine(*g["transform"][:6]) if not isinstance(g["transform"], Affine) else g["transform"]
    return features.rasterize(shapes, out_shape=(g["rows"], g["cols"]), transform=t, fill=fill, dtype=dtype)


def nearest_fill(a, valid):
    """Fill invalid cells with the value of the nearest valid cell."""
    if not valid.any():
        return a
    idx = ndimage.distance_transform_edt(~valid, return_distances=False, return_indices=True)
    return a[tuple(idx)]


def exact_building_evidence(g):
    """Per cell: the earliest and the 2nd-earliest RECORDED construction year (assessor /
    researched, not estimated) among today's buildings within ~60 m (NaN without one /
    two). Evidence that the ground existed by then (used against fill years that are too
    late: two buildings against a researched fill zone, one against a fallback guess)."""
    from scipy.spatial import cKDTree
    xs, ys, yr = [], [], []
    p = INTERIM / "sf_buildings.parquet"
    if p.exists():
        b = gpd.read_parquet(p)[["start_year", "year_confidence", "year_reason", "geometry"]]
        b = b[(b.year_confidence == "exact") & b.year_reason.isin(["ok", "ok_research", "ok_permit", "ok_survey"]) & (b.start_year >= 1770)].to_crs(3857)
        c = b.geometry.representative_point()
        xs.append(c.x.values); ys.append(c.y.values); yr.append(b.start_year.values)
    # (the counties: recorded years as written by region_buildings.py before its land
    # check moved the buildings onto existing ground)
    p = INTERIM / "region_recorded_points.parquet"
    if p.exists():
        r = pd.read_parquet(p)
        r = r[r.year >= 1770]
        xs.append(np.radians(r.lon.values) * 6378137.0)
        ys.append(6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(r.lat.values) / 2)))
        yr.append(r.year.values)
    out = np.full((g["rows"], g["cols"]), np.nan, np.float32)
    out1 = out.copy()
    if not xs:
        return out1, out
    X, Y, V = np.concatenate(xs), np.concatenate(ys), np.concatenate(yr).astype(np.float32)
    rad = 60.0 / np.cos(np.radians(37.7))
    c = np.clip(np.rint((X - g["X0"]) / g["res"]).astype(int), 0, g["cols"] - 1)
    r_ = np.clip(np.rint((g["Y0"] - Y) / g["res"]).astype(int), 0, g["rows"] - 1)
    inside = (X >= g["X0"] - rad) & (X <= g["X0"] + g["cols"] * g["res"] + rad) & (Y <= g["Y0"] + rad) & (Y >= g["Y0"] - g["rows"] * g["res"] - rad)
    X, Y, V, c, r_ = X[inside], Y[inside], V[inside], c[inside], r_[inside]
    if not len(X):
        return out1, out
    # only cells near a building need the query
    near = np.zeros((g["rows"], g["cols"]), bool)
    near[r_, c] = True
    k = max(1, int(np.ceil(rad / g["res"])))
    near = ndimage.binary_dilation(near, iterations=k)
    rr, cc = np.nonzero(near)
    tree = cKDTree(np.column_stack([X, Y]))
    cx = g["X0"] + cc * g["res"]
    cy = g["Y0"] - rr * g["res"]
    d, idx = tree.query(np.column_stack([cx, cy]), k=6, distance_upper_bound=rad)
    vals = np.where(np.isfinite(d), V[np.minimum(idx, len(V) - 1)], np.inf)
    vals.sort(axis=1)
    second = vals[:, 1]
    out[rr, cc] = np.where(np.isfinite(second), second, np.nan)
    out1[rr, cc] = np.where(np.isfinite(vals[:, 0]), vals[:, 0], np.nan)
    return out1, out


def sf_building_years(g):
    """Year each cell becomes city ground: when the 2nd building within ~45 m of it stands
    (San Francisco's buildings incl. vanished ones, and the five counties' footprints from
    region_buildings.py). A neighbourhood's ground fills in with its houses instead of
    appearing as a bare street grid years ahead of them. Also returns the share of each
    cell covered by today's buildings (urban vs suburban ground)."""
    from scipy.spatial import cKDTree
    frames = [gpd.read_parquet(INTERIM / "sf_buildings.parquet")[["start_year", "end_year", "geometry"]]]
    pred = INTERIM / "sf_predecessors.parquet"
    if pred.exists():
        frames.append(gpd.read_parquet(pred)[["start_year", "end_year", "geometry"]])
    b = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), geometry="geometry", crs=4326).to_crs(3857)
    b = b[b.start_year.values >= 1770]  # tule villages (from 1700) are not city ground
    c = b.geometry.representative_point()
    px, py, yl = [c.x.values], [c.y.values], [b.start_year.values]
    today_x, today_y, today_a = [c.x.values[b.end_year.values > 2025]], [c.y.values[b.end_year.values > 2025]], \
        [b.to_crs(32610).geometry.area.values[b.end_year.values > 2025]]
    # big footprints (campuses, warehouses, stadiums) also count along their outline,
    # so the ground under and around them is city too, not only near their middle
    big = b[b.geometry.length > 150]
    for geom, y in zip(big.geometry.values, big.start_year.values):
        ring = geom.exterior if geom.geom_type == "Polygon" else max(geom.geoms, key=lambda q: q.area).exterior
        n = int(ring.length // 40)
        if n < 2:
            continue
        pts = [ring.interpolate(t, normalized=True) for t in np.linspace(0, 1, n, endpoint=False)]
        px.append(np.array([p.x for p in pts]))
        py.append(np.array([p.y for p in pts]))
        yl.append(np.full(n, y))
    rpath = INTERIM / "region_building_points.parquet"
    if rpath.exists():
        r = pd.read_parquet(rpath)
        r = r[r.start_year >= 1770]
        X = np.radians(r.lon.values) * 6378137.0
        Y = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(r.lat.values) / 2))
        px.append(X)
        py.append(Y)
        yl.append(r.start_year.values)
        now = r.end_year.values > 2025
        today_x.append(X[now])
        today_y.append(Y[now])
        today_a.append(r.area_m2.values[now])
    tree = cKDTree(np.column_stack([np.concatenate(px), np.concatenate(py)]))
    yrs = np.concatenate(yl).astype(np.float32)
    X = g["X0"] + np.arange(g["cols"]) * g["res"]
    Y = g["Y0"] - np.arange(g["rows"]) * g["res"]
    out = np.full((g["rows"], g["cols"]), np.nan, np.float32)
    # ground metres per mercator metre at the Bay's latitude ~0.79: 45 m ground ~ 57 merc
    for r0 in range(0, g["rows"], 256):
        rr = np.arange(r0, min(r0 + 256, g["rows"]))
        xx, yy = np.meshgrid(X, Y[rr])
        d, idx = tree.query(np.column_stack([xx.ravel(), yy.ravel()]), k=6, distance_upper_bound=57.0)
        ny = np.where(np.isfinite(d), yrs[np.minimum(idx, len(yrs) - 1)], np.inf)
        ny.sort(axis=1)
        second = np.where(np.isfinite(ny[:, 1]), ny[:, 1], np.nan)
        out[rr, :] = second.reshape(len(rr), -1)
    # building coverage of each cell today (footprint area binned by centre / ground area)
    tx, ty, ta = np.concatenate(today_x), np.concatenate(today_y), np.concatenate(today_a)
    col = np.floor((tx - g["X0"]) / g["res"]).astype(int)
    row = np.floor((g["Y0"] - ty) / g["res"]).astype(int)
    ok = (col >= 0) & (col < g["cols"]) & (row >= 0) & (row < g["rows"])
    cov = np.zeros((g["rows"], g["cols"]), np.float32)
    np.add.at(cov, (row[ok], col[ok]), ta[ok])
    cell_ground = (g["res"] * 0.79) ** 2
    cov = ndimage.uniform_filter(cov / cell_ground, 3)
    return out, cov


def golf_years(g):
    """Golf courses: real outlines (Overture land_use golf_course) with researched opening years."""
    out = np.full((g["rows"], g["cols"]), np.nan, np.float32)
    path = TABLES / "golf_courses.csv"
    lu = RAW / "overture" / "2026-10-21.0" / "base_land_use.parquet"
    if not path.exists() or not lu.exists():
        return out
    t = pd.read_csv(path)
    d = pd.read_parquet(lu)
    gdf = gpd.GeoDataFrame(d, geometry=gpd.GeoSeries.from_wkb(d.geometry), crs=4326)
    gdf = gdf[gdf["class"] == "golf_course"].to_crs(3857)
    years = dict(zip(t.name, t.year_open))
    shapes = [(geom, float(years[nm])) for nm, geom in zip(gdf["name"], gdf.geometry) if nm in years]
    if shapes:
        out = rasterize_on(g, shapes).astype(np.float32)
        out[out == 0] = np.nan
    log(f"golf: {len(shapes)} courses")
    return out


def researched_green_years(g5):
    """Opening year of each land-use feature (EPSG:3857 frame with name, class) outside San
    Francisco, NaN where not researched: data/tables/region_green_dates.csv (name, class,
    lon, lat, year_open …: the feature containing the point, else the nearest feature of
    that name within ~1.5 km), golf_courses.csv (by name) and the region rows of
    park_names.csv (first name period; point, else name). Also the closing year where the
    table gives one. A year_open of 9999 means planned, never built."""
    ry = np.full(len(g5), np.nan, np.float32)
    rclose = np.full(len(g5), np.nan, np.float32)
    names = g5["name"].fillna("").astype(str).str.strip().str.lower().values if "name" in g5 else np.full(len(g5), "")
    sidx = g5.sindex

    def assign(nm, lon, lat, year, close=np.nan):
        if not np.isfinite(year):
            return
        hit = []
        if np.isfinite(lon) and np.isfinite(lat):
            X = np.radians(lon) * 6378137.0
            Y = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))
            pt = shapely.Point(X, Y)
            hit = [j for j in sidx.query(pt, predicate="intersects")]
            if len(hit) > 1 and nm:
                same = [j for j in hit if names[j] == nm]
                hit = same or hit
            if not hit and nm:
                near = [j for j in sidx.query(pt.buffer(1900.0)) if names[j] == nm]
                hit = near
        elif nm:
            hit = list(np.flatnonzero(names == nm))
        for j in hit:
            ry[j] = year if not np.isfinite(ry[j]) else min(ry[j], year)
            if np.isfinite(close):
                rclose[j] = close

    p = TABLES / "region_green_dates.csv"
    if p.exists():
        t = pd.read_csv(p)
        for r in t.itertuples():
            assign(str(getattr(r, "name", "") or "").strip().lower(), pd.to_numeric(getattr(r, "lon", np.nan), errors="coerce"),
                   pd.to_numeric(getattr(r, "lat", np.nan), errors="coerce"), pd.to_numeric(getattr(r, "year_open", np.nan), errors="coerce"),
                   pd.to_numeric(getattr(r, "year_close", np.nan), errors="coerce"))
    p = TABLES / "golf_courses.csv"
    if p.exists():
        t = pd.read_csv(p)
        for nm, y in zip(t.name.astype(str), pd.to_numeric(t.year_open, errors="coerce")):
            for j in np.flatnonzero((names == nm.strip().lower()) & ~np.isfinite(ry)):
                ry[j] = y
    p = TABLES / "park_names.csv"
    if p.exists():
        t = pd.read_csv(p)
        t["from_year"] = pd.to_numeric(t.from_year, errors="coerce")
        first = t.sort_values("from_year").groupby("park", as_index=False).first()
        for r in first.itertuples():
            lon, lat = pd.to_numeric(getattr(r, "lon", np.nan), errors="coerce"), pd.to_numeric(getattr(r, "lat", np.nan), errors="coerce")
            if np.isfinite(lon) and np.isfinite(lat):
                nm = str(r.park).strip().lower()
                before = np.isfinite(ry).copy()
                assign(nm, lon, lat, float(r.from_year))
                ry[before] = ry[before]  # (assign keeps the earlier year)
    return ry, rclose


def park_layers(g):
    """Park cover years and planted-wood years from viewer/public/data/sf-ground.json."""
    path = VIEWER_DATA / "sf-ground.json"
    park = np.full((g["rows"], g["cols"]), np.nan, np.float32)
    wood = np.full_like(park, np.nan)
    if not path.exists():
        return park, wood
    gj = gpd.read_file(path).to_crs(3857)
    for kind, arr in (("park", park), ("wood", wood)):
        sub = gj[gj.kind == kind].sort_values("start_year", ascending=False)
        if len(sub):
            r = rasterize_on(g, [(geom, float(y)) for geom, y in zip(sub.geometry, sub.start_year)])
            arr[:] = r
    return park, wood


def polygon_table(path, g):
    """Rows of a researched table with their ring as an EPSG:3857 polygon (lonlat or streets rings)."""
    if not path.exists():
        return []
    from geocode import ring_polygon
    t = pd.read_csv(path)
    out = []
    for _, r in t.iterrows():
        try:
            poly = ring_polygon(r.ring, r.get("ring_type", ""))
        except Exception as e:  # noqa: BLE001
            log(f"geocode: {r.get('zone_id', r.get('area_id', '?'))}: {e}")
            continue
        if poly is not None and not poly.is_empty:
            out.append((r, poly))
    return out


def raster_mask(g, poly):
    return rasterize_on(g, [(poly, 1)], fill=0, dtype="uint8").astype(bool)


_noise_cache = {}


def organic_mask(g, poly, amp=5.0):
    """A researched polygon (often a coarse 4-8 vertex outline) with its edge displaced by
    smooth noise of +-amp cells, so painted cover doesn't end in ruler-straight lines."""
    m = raster_mask(g, poly)
    if not m.any():
        return m
    key = (g["rows"], g["cols"])
    if key not in _noise_cache:
        rng = np.random.default_rng(7)
        f = ndimage.gaussian_filter(rng.standard_normal(key).astype(np.float32), 4)
        _noise_cache[key] = f / (f.std() + 1e-6)
    noise = _noise_cache[key]
    r, c = np.nonzero(m)
    pad = int(amp * 3) + 2
    r0, r1 = max(r.min() - pad, 0), min(r.max() + pad + 1, m.shape[0])
    c0, c1 = max(c.min() - pad, 0), min(c.max() + pad + 1, m.shape[1])
    sub = m[r0:r1, c0:c1]
    signed = ndimage.distance_transform_edt(sub) - ndimage.distance_transform_edt(~sub)
    out = np.zeros_like(m)
    out[r0:r1, c0:c1] = signed + noise[r0:r1, c0:c1] * amp > 0
    return out


def sf_extent_years(g, h):
    """Year each vertex became built-up per the researched snapshot extents (NaN = not in any)."""
    import glob
    from geocode import intersection_rings
    files = sorted(glob.glob(str(MANUAL / "sf_extent_*.csv")))
    out = np.full((g["rows"], g["cols"]), np.nan, np.float32)
    prev = 1846.0
    for f in files:
        year = float(f.split("_")[-1].split(".")[0])
        rings = intersection_rings(f)
        m = np.zeros_like(out, bool)
        for poly in rings.values():
            m |= raster_mask(g, poly)
        new = m & np.isnan(out)
        out[new] = (prev + (year - prev) * h)[new]
        log(f"extent {year:.0f}: {len(rings)} rings, {new.sum()} newly built vertices")
        prev = year
    return out


def north_peninsula(lon, lat):
    """San Francisco and the peninsula south of it to about South San Francisco (west of the
    bay): one landscape before settlement — dunes, coastal scrub, grassland, hardly a tree.
    The southern limit wanders between about 37.64 and 37.67 N (smooth noise of position,
    so the region and detail grids agree)."""
    n1 = np.sin(lon * 311.0 + 0.4) * np.cos(lat * 277.0 + 1.1) + 0.5 * np.sin(lon * 733.0 - lat * 611.0)
    in_sf = (lon > SF_BOX[0]) & (lon < SF_BOX[2]) & (lat > SF_BOX[1]) & (lat < SF_BOX[3])
    return in_sf | ((lat <= SF_BOX[1]) & (lat > 37.657 + 0.011 * n1) & (lon > -122.525) & (lon < -122.37))


def histories(name, g, d):
    rows, cols = g["rows"], g["cols"]
    lon, lat = lonlat_of(g)
    elev = np.nan_to_num(d["elev"], nan=0.0)
    wc, b18, b98, fb = d["wc"], d["b1800"], d["b1998"], d["fbuy"].astype(float)
    in_sf = (lon > SF_BOX[0]) & (lon < SF_BOX[2]) & (lat > SF_BOX[1]) & (lat < SF_BOX[3])
    water_now = (wc == 80) | (wc == 0)
    # WorldCover reads deep skyscraper shadows as water: "water" standing well above
    # the bay inside built-up surroundings is city, not a pond
    built_frac = ndimage.uniform_filter((wc == 50).astype(np.float32), 7)
    water_now &= ~((elev > 1.5) & (built_frac > 0.35))
    dy, dx = np.gradient(elev, g["res"] * 0.79)  # ~ground metres at this latitude
    slope = np.degrees(np.arctan(np.hypot(dx, dy)))

    # ---- natural cover
    N = np.full((rows, cols), GRASS, np.uint8)
    N[wc == 20] = SCRUB
    N[wc == 30] = GRASS
    N[wc == 40] = GRASS
    N[wc == 90] = WETLAND
    bare = wc == 60
    near_water = ndimage.binary_dilation(water_now, iterations=6)
    N[bare & (elev < 20) & near_water] = BEACH
    N[bare & ~((elev < 20) & near_water)] = ROCK
    # bare ground in the baylands (dried salt-pond crust, levee tops, mud) is not sand:
    # tidal flat, wherever SFEI maps bay / flat / marsh / pond c.1800 or baylands c.1998
    baylands = np.isin(b18, [2, 3, 4, 6]) | np.isin(b98, [3, 4, 6, 9, 10, 11])
    N[bare & baylands] = FLAT
    tree = wc == 10
    trees_near = ndimage.binary_dilation(tree, iterations=2)
    # conifer / redwood forest in the coastal fog belt and on the high ground behind it,
    # oak woodland inland and on the foothills. (Was a fixed meridian, lon > -122.30 = oak:
    # a ruler-straight edge down the Santa Cruz Mountains.) Fog belt = within ~12 km of the
    # outer coast, or above ~250 m within ~32 km of it (the bay side of the Santa Cruz
    # Mountains, Mount Tamalpais, the crest of the Oakland hills), or above 700 m anywhere;
    # both limits wander with smooth noise so the edge follows the country, not a line
    # (the outer coast as a function of latitude and the noise as a function of position,
    # so the region and detail grids agree cell for cell)
    COAST = [(36.85, -121.90), (37.00, -122.18), (37.11, -122.33), (37.20, -122.41), (37.40, -122.43), (37.50, -122.51),
             (37.70, -122.50), (37.80, -122.52), (37.83, -122.53), (37.90, -122.65), (38.00, -122.80), (38.10, -122.95),
             (38.33, -123.05), (38.50, -123.25), (38.90, -123.70)]
    coast_lon = np.interp(lat, [c[0] for c in COAST], [c[1] for c in COAST])
    coast_km = (lon - coast_lon) * 111.32 * np.cos(np.radians(lat))
    _fz = np.sin(lon * 97.0 + 1.3) * np.cos(lat * 83.0 + 0.7) + 0.6 * np.sin(lon * 211.0 + lat * 173.0) \
        + 0.4 * np.cos(lon * 431.0 - lat * 389.0)
    fog = (coast_km < 12.0 + 2.5 * _fz) | ((elev > 250.0 + 50.0 * _fz) & (coast_km < 32.0 + 3.0 * _fz)) | (elev >= 700)
    del _fz
    N[tree & ~fog] = OAK
    N[tree & fog] = FOREST
    # San Francisco had almost no native trees: planted forests and the city sit on
    # dunes (west) and grassy/scrubby hills (east)
    sf_dunes = in_sf & (lon < -122.445) & (elev < 120)
    # the dune sheet doesn't stop at the county line: it ran on south through Daly City's
    # Westlake, Lake Merced's shore and Fort Funston to the cliffs at Mussel Rock
    # (refined by data/manual/landscape/dunes.geojson when present)
    sf_dunes |= ~in_sf & (lat > 37.662) & (lat < 37.712) & (lon < -122.462 - (37.712 - lat) * 0.25) & (elev < 110)
    # The northern peninsula had almost no native trees, and not only inside today's county
    # line: the treeless country of dunes, coastal scrub and grassland ran on south over
    # Colma and San Bruno Mountain to about South San Francisco. (The rule used to be "SF =
    # scrub", a box: uniform scrub north of latitude 37.708 and grass with forest patches
    # south of it — a ruler-straight seam, owner 2026-11.) Where no c.1800 map exists the
    # cover follows the ground instead of today's land use: coastal scrub on the steeper,
    # north- and east-facing (shaded, moist) slopes and along the ocean, grassland on the
    # sunny slopes, ridges and valley floors (as on San Bruno Mountain today); planted
    # eucalyptus and cypress are not natural forest. The southern edge wanders with noise.
    north_pen = north_peninsula(lon, lat)
    gmag = np.hypot(dx, dy) + 1e-6
    shaded = (dy - 0.5 * dx) / gmag / 1.118      # +1: faces north-north-east … -1: south-south-west
    _n2 = np.sin(lon * 523.0 + 2.1) * np.cos(lat * 467.0 + 0.3) + 0.6 * np.sin(lon * 1171.0 + lat * 983.0)
    scrubby = (slope / 14.0) * (0.55 + 0.45 * shaded) + 0.35 * (coast_km < 2.5) + 0.2 * (elev > 180) + 0.16 * _n2 > 0.42
    upland = north_pen & (tree | (wc == 50) | (wc == 40) | (wc == 30) | (wc == 20))
    N[upland & scrubby] = SCRUB
    N[upland & ~scrubby] = GRASS
    del gmag, shaded, _n2, scrubby, upland
    dpath = MANUAL / "landscape" / "dunes.geojson"
    if dpath.exists():
        dn = gpd.read_file(dpath).to_crs(3857)
        mob = rasterize_on(g, [(gm, 1) for gm, k in zip(dn.geometry, dn.kind) if k == "mobile_dune" and gm is not None],
                           fill=0, dtype="uint8").astype(bool)
        stab = rasterize_on(g, [(gm, 1) for gm, k in zip(dn.geometry, dn.kind) if k == "stabilized_dune" and gm is not None],
                            fill=0, dtype="uint8").astype(bool)
        slack = rasterize_on(g, [(gm, 1) for gm, k in zip(dn.geometry, dn.kind) if k == "dune_slack" and gm is not None],
                             fill=0, dtype="uint8").astype(bool)
        peninsula = (lon < -122.37) & (lat > 37.6) & (lat < 37.82)
        N[mob & ~water_now] = DUNES
        N[stab & peninsula & ~water_now & ~mob] = SCRUB     # dune scrub on the SF / Daly City sand
        N[slack & ~water_now] = WETLAND
        log(f"terrain {name}: dunes from the mapped extent: {int(mob.sum())} mobile, {int(stab.sum())} stabilized cells")
    else:
        N[sf_dunes & ~(wc == 60) & ~water_now] = DUNES
    lc_rows = polygon_table(TABLES / "landcover_history.csv", g)
    # researched open spaces inside the city (parade grounds, plazas...) override the
    # built-up snapshot outlines: their own rows say when they were grass / paved / lawn
    # (only dated open-space rows, and natural rows sharing an outline with one — the
    # natural grassland outlines of Bernal / Potrero / Twin Peaks must not block the city)
    open_override = np.zeros((rows, cols), bool)
    open_kinds = ("grassland", "park", "lawn", "paved", "lake")
    era_rings = {str(r.ring) for r, _ in lc_rows if str(r.get("region", "")) == "San Francisco"
                 and str(r.cover).strip() in open_kinds and pd.to_numeric(r.year_start, errors="coerce") > 1769}
    for r, poly in lc_rows:
        if str(r.get("region", "")) == "San Francisco" and str(r.cover).strip() in open_kinds and str(r.ring) in era_rings:
            open_override |= raster_mask(g, poly)
    for r, poly in lc_rows:
        c = LANDCOVER_TABLE.get(str(r.cover).strip())
        if c is None or pd.notna(r.get("year_start")) and float(r.year_start) > 1769:
            continue  # only natural cover (before 1769) here; mission fields etc. are dated events below
        m = organic_mask(g, poly) & ~water_now & (d["hist"] == 0)
        if c in (FOREST, OAK):
            m &= trees_near
        N[m] = c
    # inland open water that is not bay: reservoirs / lakes
    N[water_now] = RESERVOIR
    # open ocean / bay
    N[water_now & (elev <= 2)] = DEEP
    # mapped c.1800 habitats (SFEI) override the rules wherever they exist
    hist = d["hist"]
    N = np.where(hist > 0, hist.astype(np.int16) - 1, N).astype(np.uint8)
    N[water_now & (hist == 0) & (elev <= 2)] = DEEP
    # a dated lake / shallow_water row of water_history.csv (a harbour or lagoon dug, a tract
    # flooded) wins over "water at sea level is natural" where no c.1800 map exists: before
    # its year the ground is the land around it
    dated_w = np.zeros((rows, cols), bool)
    for r_, poly_ in polygon_table(MANUAL / "landscape" / "water_history.csv", g):
        if str(r_.cover).strip() in ("lake", "shallow_water") and pd.to_numeric(r_.year_start, errors="coerce") > 1769:
            dated_w |= raster_mask(g, poly_)
    dated_low = dated_w & water_now & (hist == 0) & (elev <= 2)
    # the Delta, which the c.1998 baylands layer does not reach (data/manual/delta/delta_zone.geojson)
    dz_ = gpd.read_file(MANUAL / "delta" / "delta_zone.geojson").to_crs(3857)
    in_delta = rasterize_on(g, [(gm_, 1) for gm_ in dz_.geometry], fill=0, dtype="uint8").astype(bool)
    # mapped marsh / flat well above the tides is a registration error of the historical
    # layers (e.g. downtown San Rafael at 15 m): dry ground
    N[np.isin(N, [MARSH, FLAT]) & (elev > 6) & ~water_now] = GRASS
    # SFEI c.1998 "bay fill" is made land by definition: it was bay before (e.g. the
    # Yerba Buena Shoals under Treasure Island), whatever the coarser c.1800 layers say
    made_land = np.isin(b98, [12, 13]) & ~np.isin(N, list(WET))
    N[made_land] = SHALLOW
    # inland water today that no c.1800 map shows (SFEI / Hidden Nature ponds, lagoons and
    # lakes stay natural): reservoirs, gravel pits, park / golf lakes and stock ponds were
    # dry ground in 1769. Researched ones are dated by water_history.csv below; the rest
    # appear in the post-war decades (gravel pits, ponds)
    # (also where the c.1800 maps draw dry ground: 540 ha of gravel pits and ponds around
    # Pleasanton, Livermore, Sunol and the valley percolation ponds stayed land for good)
    mapped_dry = water_now & (hist > 0) & ((elev > 2) | in_delta) & ~np.isin(N, list(WET) + [RESERVOIR, DEEP, SHALLOW])
    later_water = (water_now & (N == RESERVOIR) & (hist == 0) & (elev > 2)) | dated_low
    if later_water.any():
        land_ok = ~water_now & ~np.isin(N, list(WET) + [RESERVOIR, DEEP, SHALLOW])
        N[later_water] = nearest_fill(N, land_ok)[later_water]
        log(f"terrain {name}: {int(later_water.sum())} cells of today's inland water were dry before their reservoir / pit / pond")
    later_water = later_water | mapped_dry
    # quarries and landfills (data/manual/industrial_sites) are WorldCover "bare", read as
    # natural rock above: before the digging / dumping the ground was the hillside around
    # them (Permanente, Selby, Stevens Creek, San Rafael rock quarry, the landfills)
    isp = MANUAL / "industrial_sites" / "sites.geojson"
    ind_sites = gpd.read_file(isp).to_crs(3857) if isp.exists() else None
    if ind_sites is not None:
        pits = ind_sites[ind_sites["cover"].isin(["quarry_pit", "landfill"])]
        if len(pits):
            pm = rasterize_on(g, [(gm, 1) for gm in pits.geometry.buffer(60) if gm is not None], fill=0,
                              dtype="uint8").astype(bool) & (N == ROCK)
            if pm.any():
                nat = nearest_fill(N, ~pm & ~np.isin(N, [ROCK, DEEP, SHALLOW, FLAT, MARSH, BEACH, RESERVOIR]))
                N[pm] = nat[pm]
                log(f"terrain {name}: {int(pm.sum())} quarry / landfill cells get the natural ground around them before the works")

    ev_cover, ev_year = [], []

    def event(mask, cover, year):
        # sparse: only the cells the change touches (dozens of dated layers as full grids
        # exhausted the memory)
        idx = np.flatnonzero(mask)
        if not len(idx):
            return
        cv = np.full(len(idx), cover, np.uint8) if np.isscalar(cover) else np.asarray(cover).ravel()[idx].astype(np.uint8)
        yv = np.full(len(idx), year, np.float32) if np.isscalar(year) else np.asarray(year, np.float32).ravel()[idx]
        ev_cover.append((idx, cv))
        ev_year.append(yv)

    def site_cleared(spans, jit):
        # a site part whose use ended is cleared ground from then on, unless a later part
        # of the same site took over the ground (sparse cell indices, not full grids)
        hv = h.ravel()
        for idx, y0, y1 in spans:
            if y1 >= 9999:
                continue
            later = [i2 for i2, z0, _ in spans if z0 >= y1 - 0.5]
            if later:
                idx = np.setdiff1d(idx, np.concatenate(later), assume_unique=False)
            if len(idx):
                ev_cover.append((idx, np.full(len(idx), FILL, np.uint8)))
                ev_year.append((y1 + jit * hv[idx]).astype(np.float32))

    # ---- urban year
    urban_y = np.full((rows, cols), np.nan, np.float32)
    sfy, bcov = sf_building_years(g)
    urban_y = np.where(np.isfinite(sfy), sfy, urban_y)
    fbv = (fb >= 1810) & (fb <= 2026)
    fb_filled = nearest_fill(np.where(fbv, fb, np.nan), fbv) if fbv.any() else np.full_like(fb, np.nan)
    built_now = (wc == 50)
    if in_sf.any():
        hh = (np.add.outer(np.arange(rows) * 7919, np.arange(cols) * 104729) % 997) / 997.0
        ext_y = sf_extent_years(g, hh)
        has_ext = np.isfinite(ext_y) & ~water_now
        # the snapshot outlines cover whole districts: squares, parade grounds and other
        # ground that is lawn or trees today (and has no building on it) became green
        # open space, not city fabric
        green_now = np.isin(wc, [10, 30]) & ~np.isfinite(sfy)
        ext_green_y = np.where(has_ext & green_now, ext_y, np.nan)
        urban_y = np.where(has_ext & ~green_now & np.isnan(urban_y), ext_y, urban_y)
    else:
        ext_green_y = np.full((rows, cols), np.nan, np.float32)
    # Outside SF, HISDAC's 250 m "first built-up year" comes from the oldest *surviving*
    # building in the cell, so a lone 1890s farmhouse paints a 250 m city block in the
    # middle of the orchards. Use the neighbourhood median instead (undeveloped cells
    # count as "not yet"): isolated houses drop out, suburbs get their typical year,
    # and edges are rounded instead of 250 m squares.
    fb_med = ndimage.median_filter(np.where(fbv, fb, 2100.0).astype(np.float32), size=7)
    dense = fb_med <= 2026
    out_sf_urban = np.where(dense, np.maximum(fb_med, np.where(fbv, fb, fb_med)), np.where(built_frac > 0.5, fb_filled, np.nan))
    # outside SF the buildings themselves (region_buildings.py) date the ground where they
    # exist; HISDAC only fills cells without footprints (e.g. counties not yet built)
    urban_y = np.where(np.isfinite(sfy) & ~in_sf & ~built_now & ~dense & (bcov < 0.04), np.nan, urban_y)
    urban_y = np.where(np.isnan(urban_y) & (built_now | dense) & ~in_sf, out_sf_urban, urban_y)
    urban_y = np.where(np.isnan(urban_y) & built_now & in_sf, np.where(fbv, fb, fb_filled), urban_y)
    urban = np.isfinite(urban_y) & ~water_now & ~open_override

    # ---- parks (SF)
    park_y, wood_y = park_layers(g)
    golf_y = golf_years(g)
    park_y = np.where(np.isfinite(golf_y) & (np.isnan(park_y) | (golf_y < park_y)), golf_y, park_y)
    park_y = np.where(np.isnan(park_y), ext_green_y, park_y)
    park_y[open_override] = np.nan
    # parks and planted woods never paint over water (Lake Merced, Stow Lake, ...)
    park_y[water_now] = np.nan
    wood_y[water_now] = np.nan
    # outside SF (whose parks come from sf-ground.json): parks, golf courses, cemeteries and
    # recreation grounds (Overture region land use) are park ground from their year —
    # golf_courses.csv / park_names.csv where researched, else the year the neighbourhood
    # around them was built (nearest city ground outside them; estimated). They also
    # claim the ground from farming (assembly below): no orchard or farmhouse comes
    # back on a park, course or cemetery
    lu5 = RAW / "overture" / "2026-10-21.0" / "region5_land_use.parquet"
    open_claim_y = np.full((rows, cols), np.nan, np.float32)
    green_close_y = np.full((rows, cols), np.nan, np.float32)
    if lu5.exists():
        TOWN = ["park", "golf_course", "cemetery", "grave_yard", "recreation_ground", "village_green"]
        # only with a researched year: reserves and state / national parks (open space —
        # the farming stops, the ground stays natural), zoos and theme parks (park ground)
        OPEN = ["nature_reserve", "state_park", "national_park", "protected_landscape_seascape", "strict_nature_reserve",
                "species_management_area", "wilderness_area", "natural_monument", "protected"]
        SPECIAL = ["zoo", "theme_park"]
        d5 = pd.read_parquet(lu5)
        d5 = d5[d5["class"].isin(TOWN + OPEN + SPECIAL)]
        g5 = gpd.GeoDataFrame(d5, geometry=gpd.GeoSeries.from_wkb(d5.geometry), crs=4326).to_crs(3857)
        g5 = g5[g5.geometry.notna() & g5.geom_type.isin(["Polygon", "MultiPolygon"])].reset_index(drop=True)
        ry, rclose = researched_green_years(g5)
        keep5 = (g5["class"].isin(TOWN).values | np.isfinite(ry)) & ~(ry >= 9000)   # 9999: planned, not built
        g5 = g5[keep5]
        ry, rclose = ry[g5.index.values], rclose[g5.index.values]
        g5 = g5.reset_index(drop=True)
        # big parks (regional open space: hills, shorelines) stay natural ground — they
        # only stop the farming; town parks, courses and cemeteries become park ground
        ha = g5.geometry.area.values * np.cos(np.radians(37.6)) ** 2 / 1e4
        big = ((ha > 40) & g5["class"].isin(["park", "recreation_ground", "village_green"]).values) | g5["class"].isin(OPEN).values
        green5 = rasterize_on(g, [(geom, 1) for geom in g5.geometry], fill=0, dtype="uint8").astype(bool) \
            & ~in_sf & ~water_now
        big5 = rasterize_on(g, [(geom, 1) for geom in g5.geometry[big]], fill=0, dtype="uint8").astype(bool) \
            & green5 if big.any() else np.zeros((rows, cols), bool)
        res5 = np.full((rows, cols), np.nan, np.float32)
        if np.isfinite(ry).any():
            sel = np.isfinite(ry)
            r_ = rasterize_on(g, [(geom, float(y)) for geom, y in zip(g5.geometry[sel], ry[sel])]).astype(np.float32)
            res5 = np.where(r_ > 0, r_, np.nan)
        around = np.isfinite(urban_y) & ~green5
        nb_y = nearest_fill(np.where(around, urban_y, np.nan).astype(np.float32), around)
        g5y = np.where(np.isfinite(res5), res5, nb_y)
        g5y = np.where(green5 & np.isfinite(g5y), g5y, np.nan)
        open_claim_y = np.where(big5, g5y, np.nan).astype(np.float32)
        g5y = np.where(big5, np.nan, g5y)
        park_y = np.where(np.isfinite(g5y) & np.isnan(park_y), g5y, park_y)
        # closed since (Skywest golf course 1964-2020): open ground again from that year
        if np.isfinite(rclose).any():
            selc = np.isfinite(rclose)
            rc_ = rasterize_on(g, [(geom, float(y)) for geom, y in zip(g5.geometry[selc], rclose[selc])]).astype(np.float32)
            green_close_y = np.where((rc_ > 0) & green5, rc_, np.nan).astype(np.float32)
        log(f"terrain {name}: {int(np.isfinite(g5y).sum())} park / golf / cemetery cells outside SF "
            f"({int(np.isfinite(res5).sum())} with a researched year)")
    is_park = np.isfinite(park_y)
    urban &= ~is_park

    # ---- diking of marsh into salt ponds / diked land
    dike_year = np.full((rows, cols), 1900.0, np.float32)
    salt = np.isin(b18, [3, 4, 6]) & np.isin(b98, [6, 11])
    diked = np.isin(b18, [3, 4, 6]) & np.isin(b98, [9, 10])
    # the Delta has no c.1998 layer: its leveed islands are the diked_marsh rows dl_* of
    # fill_zones.csv (Delta Stewardship Council outlines, Thompson's reclamation years);
    # the parts under water today (Franks Tract, Liberty Island, Clifton Court) were farm
    # land between the levee year and the flood / forebay year of their water_history row
    delta_flooded = np.zeros((rows, cols), bool)
    for r_, poly_ in polygon_table(MANUAL / "fill_zones.csv", g):
        if str(r_.zone_id).startswith("dl_") and str(r_.kind).strip() == "diked_marsh":
            m_ = raster_mask(g, poly_) & in_delta
            diked |= m_ & ~water_now & np.isin(N, [MARSH, FLAT, DEEP, SHALLOW])   # levees stand in the old channel edge
            delta_flooded |= m_ & water_now & np.isin(N, [MARSH, FLAT])
    zones_fill = np.full((rows, cols), np.nan, np.float32)
    pier_y = np.full((rows, cols), np.nan, np.float32)
    # per-cell spread of dated changes: field-sized patches of rank noise (the old hash
    # ((r*7919 + c*104729) mod 997) / 997 was a smooth ramp that swept every spread year
    # across the map in ~1 km diagonal stripes)
    from scipy.special import ndtr
    _rn = ndimage.gaussian_filter(np.random.default_rng(1769).standard_normal((rows, cols)).astype(np.float32), 4.0)
    h = ndtr(_rn / (_rn.std() + 1e-9)).astype(np.float32)
    del _rn
    restored = []
    excavated = []
    was_wet0 = np.isin(N, list(WET))
    # distance (cells) from the c.1800 shore: fill advanced outward from it
    shore_d = ndimage.distance_transform_edt(was_wet0).astype(np.float32)
    zone_rows = polygon_table(MANUAL / "fill_zones.csv", g)
    zone_rows.sort(key=lambda rp: str(rp[0].zone_id).startswith("fb_"))  # specific zones first
    covered = np.zeros((rows, cols), bool)
    researched_fill = np.zeros((rows, cols), bool)
    dike_fill_y = np.full((rows, cols), np.nan, np.float32)
    for r, poly in zone_rows:
        ys = pd.to_numeric(r.year_start, errors="coerce")
        ye = pd.to_numeric(r.year_end, errors="coerce")
        if not (np.isfinite(ys) or np.isfinite(ye)):
            continue
        ys = ys if np.isfinite(ys) else ye
        ye = ye if np.isfinite(ye) else ys
        m = raster_mask(g, poly)
        k = str(r.kind).strip()
        fallback = str(r.zone_id).startswith("fb_")
        if fallback:
            m &= ~covered
        if not m.any():
            continue
        if k == "fill" and fallback:
            # only a bracket: use the urban year if it falls inside, else the midpoint
            y = np.where(np.isfinite(urban_y) & (urban_y - 3 >= ys) & (urban_y - 3 <= ye), urban_y - 3, (ys + ye) / 2)
        else:
            dz = shore_d[m]
            span = max(float(dz.max()), 1.0)
            y = np.full((rows, cols), np.nan, np.float32)
            y[m] = ys + (ye - ys) * np.clip(dz / span, 0, 1)
        if k == "diked_marsh":
            sel = m & (salt | diked | delta_flooded)
            dike_year[sel] = y[sel]
            later = m & ~(salt | diked) & was_wet0
            dike_fill_y[later] = np.fmin(dike_fill_y[later], y[later])
        elif k == "fill":
            upd = m & (np.isnan(zones_fill) | (y < zones_fill))
            zones_fill[upd] = y[upd]
            covered |= m
            if not fallback:
                researched_fill |= m
        elif k == "pier":
            pier_y[m] = np.where(np.isnan(pier_y[m]), y[m], np.fmin(pier_y[m], y[m]))
        elif k == "excavated":
            excavated.append((m, y))
        elif k == "restored":
            restored.append((m, y))
    # researched salt-pond / diking years by complex (data/manual/landscape/water_history.csv)
    wh_rows = polygon_table(MANUAL / "landscape" / "water_history.csv", g)
    water_rows = []
    salt_end, old_works = [], []
    for r, poly in wh_rows:
        ys = pd.to_numeric(r.year_start, errors="coerce")
        if not np.isfinite(ys):
            continue
        m = raster_mask(g, poly)
        cov = str(r.cover).strip()
        if cov in ("salt_pond", "diked"):
            sel = m & (salt | diked)
            dike_year[sel] = ys + 4.0 * h[sel]
            ye = pd.to_numeric(r.get("year_end"), errors="coerce")
            ended = bool(np.isfinite(ye) and ye < 9999)
            if ended and sel.any():
                salt_end.append((sel, float(ye)))      # works closed: levees round dry / overgrown beds
            # 19th-century works that are marsh / fill today (the Hayward shore, Mt Eden)
            gone = m & ~(salt | diked) & np.isin(b18, [3, 4, 6]) & ~water_now
            if cov == "salt_pond" and gone.any():
                old_works.append((gone, float(ys), float(ye) if ended else np.nan))
        elif cov in ("lake", "shallow_water"):
            water_rows.append((m, cov, float(ys)))
    event(salt, SALTPOND, dike_year)
    event(diked, DIKED, dike_year)
    for sel, ye in salt_end:
        event(sel, DIKED, ye + 2.0 * h)
    for gone, ys, ye in old_works:
        event(gone, SALTPOND, ys + 4.0 * h)
        if np.isfinite(ye):
            event(gone, MARSH, ye + 2.0 * h)   # later fill / city events win by date

    # bridge decks / causeways read as built-up over open bay (DEM at water level):
    # still water underneath — the bridges themselves are landmarks / road paths
    deck = (wc == 50) & (elev < 0.5) & np.isin(N, [DEEP, SHALLOW]) & ~np.isin(b98, [12, 13]) \
        & ~researched_fill & np.isnan(pier_y)
    water_now = water_now | deck
    urban &= ~deck

    # ---- fill: c.1800 water/flat/marsh/lagoon that is land now (piers are decks, not fill)
    was_wet = np.isin(N, list(WET))
    is_pier = np.isfinite(pier_y) & was_wet
    # still baylands in SFEI c.1998 (flat, marsh, pond, moist grassland) are not fill:
    # levees, marsh plain and dried pond beds read as land in WorldCover, but nobody
    # filled them (they were the yellow "grass" patches along the South Bay ponds)
    still_bay = was_wet & ~water_now & ~salt & ~diked & (np.isin(b98, [3, 4, 5, 8])
                                                          | (in_delta & np.isin(N, [MARSH, FLAT]) & ~researched_fill))
    filled = was_wet & ~water_now & ~salt & ~diked & ~is_pier & ~still_bay
    fill_y = np.where(np.isfinite(zones_fill), zones_fill, np.where(urban, urban_y - 3, np.nan))
    fill_y = np.where(filled & np.isnan(fill_y), 1950.0, fill_y)
    # a building with a recorded year stands on the ground: where at least two such
    # buildings within ~60 m predate the fill year of a cell, the fill zone is too wide or
    # too late there and the ground is theirs (they stood in the bay for decades — the
    # 1889 Audiffred Building until 1915, 1880s Alameda and San Rafael streets)
    ev1, ev2 = exact_building_evidence(g)
    ev_y = np.where(researched_fill, ev2, ev1)   # a fallback fill year is a guess: one building is enough
    ev_fix = filled & np.isfinite(ev_y) & np.isfinite(fill_y) & (ev_y - 1.5 < fill_y)
    fill_y = np.where(ev_fix, ev_y - 1.5, fill_y)
    zones_fill = np.where(ev_fix & np.isfinite(zones_fill), np.fmin(zones_fill, ev_y - 1.5), zones_fill)
    log(f"terrain {name}: {int(ev_fix.sum())} made-land cells dated by the recorded buildings standing on them")
    # marsh diked long before it was filled (Brewer Island / Foster City, Redwood Shores,
    # Corte Madera: dairies, hay and salt works behind levees from c.1900, fill in the
    # 1960s): diked land between the two, not tidal marsh until the fill
    dk = filled & np.isfinite(dike_fill_y) & np.isfinite(fill_y) & (dike_fill_y < fill_y - 1.5)
    event(dk, DIKED, dike_fill_y)
    # In the city, made land was put to use within a few years (wharves, rail yards,
    # warehouses, streets) — not left bare until today's buildings went up: anything
    # standing on it today means it was city soon after filling. Open fill greens over.
    stadium = np.zeros((rows, cols), bool)
    lu = RAW / "overture" / "2026-10-21.0" / "base_land_use.parquet"
    if lu.exists() and in_sf.any():
        dl = pd.read_parquet(lu)
        gl = gpd.GeoDataFrame(dl, geometry=gpd.GeoSeries.from_wkb(dl.geometry), crs=4326)
        gl = gl[gl["class"].isin(["stadium"])].to_crs(3857)
        if len(gl):
            stadium = rasterize_on(g, [(geom, 1) for geom in gl.geometry], fill=0, dtype="uint8").astype(bool)
    city_fill = filled & in_sf & (built_now | stadium | np.isfinite(sfy) | np.isfinite(urban_y)) & ~is_park & np.isfinite(fill_y)
    urban_y = np.where(city_fill, np.fmin(urban_y, fill_y + 0.5), urban_y)
    # fill that is built on within a few years goes straight to the city (one history
    # slot saved) — from the day it was filled, not from the build date: the ground was there
    quick = filled & np.isfinite(fill_y) & np.isfinite(urban_y) & (urban_y > fill_y) & (urban_y - fill_y < 4)
    urban_y = np.where(quick, fill_y + 0.2, urban_y)
    urban |= city_fill
    open_fill = filled & ~urban & ~is_park & np.isfinite(fill_y)
    event(filled, FILL, fill_y)
    event(open_fill, GRASS, fill_y + 6.0)
    # open bay / flat that became marsh or flat by c.1998 (accretion behind the ponds)
    event(still_bay & (b98 == 4) & (N != MARSH), MARSH, 1900.0 + 40 * h)
    event(still_bay & (b98 == 3) & ~np.isin(N, [FLAT, MARSH]), FLAT, 1900.0 + 40 * h)
    event(is_pier & ~water_now, URBAN, pier_y)
    for m, y in excavated:
        event(m & water_now & ~was_wet, SHALLOW, y)
    for m, y in restored:
        event(m & water_now & (salt | diked), SHALLOW, y)
        event(m & (wc == 90) & (salt | diked), MARSH, y)
        # filled ground dug out again (Crissy Field: marsh filled for the 1915 exposition,
        # the airfield 1921-74, tidal marsh re-created 2000): water / wetland today, so the
        # fill above never touched it — land from the fill zone's year until the restoration
        # (researched fill zones only: a fallback bracket over a restored marsh made
        # channels land for decades)
        refill = m & was_wet & np.isfinite(zones_fill) & researched_fill & (water_now | (wc == 90)) & ~(salt | diked)
        if refill.any():
            event(refill, FILL, zones_fill)
            event(refill, GRASS, zones_fill + 6.0)
            event(refill & water_now, SHALLOW, y)
            event(refill & ~water_now, MARSH, y)

    # c.1800 marsh / flat that is open water today (not a salt pond or diked): narrow
    # channels are sloughs that were always water; broad water was made later — Lake
    # Merritt (dammed 1869), the Oakland estuary / tidal canal (1874-1902), dredged
    # harbours — water from c.1870-90 unless a researched row says when
    became = np.isin(N, [MARSH, FLAT]) & water_now & ~salt & ~diked
    # flats / marsh that SFEI c.1998 still maps as flats / marsh stay so (WorldCover's image
    # tide made them flicker between water and mud in the 1870s-80s)
    became &= ~np.isin(b98, [3, 4])
    broad = ndimage.binary_opening(became, iterations=2)
    N[became & ~broad & ~(dated_w & in_delta)] = SHALLOW
    researched_water = np.zeros((rows, cols), bool)
    # one event per kind (an event is a full grid: one per area would exhaust memory)
    lake_y = np.full((rows, cols), np.nan, np.float32)
    shal_y = np.full((rows, cols), np.nan, np.float32)
    for m, cov, ys in water_rows:
        mm = m & water_now
        if not mm.any():
            continue
        researched_water |= mm
        if cov == "lake":
            # dammed lakes / reservoirs: the land (or marsh) it flooded before the dam year
            dry = mm & np.isin(N, [DEEP, SHALLOW, RESERVOIR])
            N[dry & (elev > 2)] = GRASS
            lake_y[mm] = np.fmin(lake_y[mm], ys + 0.5 * h[mm])
        else:
            sel = mm & ~np.isin(N, [DEEP, SHALLOW])
            shal_y[sel] = np.fmin(shal_y[sel], ys + 2.0 * h[sel])
    event(np.isfinite(lake_y), RESERVOIR, lake_y)
    event(np.isfinite(shal_y), SHALLOW, shal_y)
    del lake_y, shal_y
    delta_flooded &= np.isin(N, [MARSH, FLAT])
    event(delta_flooded, DIKED, dike_year)
    event(delta_flooded & ~researched_water, SHALLOW, 1975.0 + 20.0 * h)
    event(later_water & ~researched_water, RESERVOIR, 1945.0 + 20.0 * h)
    event(broad & ~researched_water & ~delta_flooded, SHALLOW, 1870.0 + 20.0 * h)

    # ---- agriculture (outside SF)
    flat = slope < 6
    not_sf = ~in_sf
    farmable = not_sf & flat & (elev < 250) & ~water_now & ~np.isin(N, [DEEP, SHALLOW, FLAT, MARSH, FOREST, ROCK, BEACH])
    farm_now = (wc == 40)
    early_urban = urban & (urban_y < 1860)
    ag_candidates = farmable & (farm_now | (urban & ~early_urban))
    scv = (lon > SANTA_CLARA_VALLEY[0]) & (lon < SANTA_CLARA_VALLEY[2]) & (lat > SANTA_CLARA_VALLEY[1]) & (lat < SANTA_CLARA_VALLEY[3])
    wine = (lon > WINE_VALLEYS[0]) & (lon < WINE_VALLEYS[2]) & (lat > WINE_VALLEYS[1]) & (lat < WINE_VALLEYS[3])
    ag_path = MANUAL / "landscape" / "agriculture.geojson"
    if ag_path.exists():
        # researched farm history (data/manual/landscape/agriculture.geojson): district eras
        # (grazing -> wheat / hay / dairies / vineyards -> orchards), Broek's 1931 landscape map
        # and the 1940s-50s topo orchards; each cell keeps its first farm era, its last one
        # before the city and the one the last replaced (grain -> hops / prunes / apples ->
        # vineyards in the wine valleys; the terrain holds four changes per cell)
        from scipy.special import ndtr
        AGK = {"grain": FARM, "hay": FARM, "vegetables": FARM, "nursery": FARM, "farm_mixed": FARM,
               "orchard": ORCHARD, "vineyard": VINEYARD, "pasture_dairy": PASTURE}
        PRIO = {"district_era": 0, "broek_1931": 1, "topo_1940s": 2, "osm_today": 2, "special": 3}

        def blob(seed, sigma):
            r = np.random.default_rng(seed).standard_normal((rows, cols)).astype(np.float32)
            b = ndimage.gaussian_filter(r, sigma)
            return ndtr(b / (b.std() + 1e-9)).astype(np.float32)
        b_share, b_orch, b_year = blob(1851, 4.0), blob(1885, 3.0), blob(1869, 6.0)
        ag = gpd.read_file(ag_path).to_crs(3857)
        ag["in_city"] = False
        # farm eras inside San Francisco (truck gardens, dairies, nurseries of the southern
        # and western districts; data/manual/landscape/agriculture_sf.geojson): the farm
        # patchwork used to stop on the county line
        ag_sf_path = MANUAL / "landscape" / "agriculture_sf.geojson"
        if ag_sf_path.exists():
            ag_sf = gpd.read_file(ag_sf_path).to_crs(3857)
            ag_sf["in_city"] = True
            ag = gpd.GeoDataFrame(pd.concat([ag, ag_sf], ignore_index=True), geometry="geometry", crs=3857)
            log(f"terrain {name}: {len(ag_sf)} farm-era rows inside San Francisco")
        ag = ag[ag.geometry.notna()].copy()
        ag["prio"] = ag["layer"].map(PRIO).fillna(0)
        ag = ag.sort_values(["year_start", "prio"]).reset_index(drop=True)
        ag_ok = ~water_now & (slope < 15) & (elev < 500) & ~np.isin(N, [DEEP, SHALLOW, FLAT, MARSH, ROCK, BEACH]) & ~in_sf
        # the Delta islands were tule marsh: they are farmed once their levees stand (the
        # district eras that end before an island was reclaimed do not apply to it)
        delta_farm = in_delta & diked & ~water_now & np.isin(N, [MARSH, FLAT]) & ~in_sf
        ag_ok |= delta_farm
        ag_ok_sf = ~water_now & (slope < 15) & (elev < 500) & ~np.isin(N, [DEEP, SHALLOW, FLAT, MARSH, ROCK, BEACH, DUNES]) & in_sf
        first_c = np.full((rows, cols), 255, np.uint8)
        first_y = np.full((rows, cols), np.nan, np.float32)
        last_c = np.full((rows, cols), 255, np.uint8)
        last_y = np.full((rows, cols), np.nan, np.float32)
        last_p = np.full((rows, cols), -1, np.int8)
        mid_c = np.full((rows, cols), 255, np.uint8)        # the era the last one replaced
        mid_y = np.full((rows, cols), np.nan, np.float32)
        t = Affine(g["res"], 0, g["X0"] - g["res"] / 2, 0, -g["res"], g["Y0"] + g["res"] / 2)
        for r in ag.itertuples():
            c = AGK.get(str(r.kind))
            ys = pd.to_numeric(r.year_start, errors="coerce")
            if c is None or not np.isfinite(ys):
                continue
            yf = pd.to_numeric(r.year_full, errors="coerce")
            yf = yf if np.isfinite(yf) else ys + 5
            # rasterize only the feature's window
            x0, y0b, x1, y1b = r.geometry.bounds
            c0, c1 = max(int((x0 - g["X0"]) / g["res"]) - 1, 0), min(int((x1 - g["X0"]) / g["res"]) + 2, cols)
            r0, r1 = max(int((g["Y0"] - y1b) / g["res"]) - 1, 0), min(int((g["Y0"] - y0b) / g["res"]) + 2, rows)
            if c0 >= c1 or r0 >= r1:
                continue
            tw = Affine(g["res"], 0, g["X0"] - g["res"] / 2 + c0 * g["res"], 0, -g["res"], g["Y0"] + g["res"] / 2 - r0 * g["res"])
            mw = features.rasterize([(r.geometry, 1)], out_shape=(r1 - r0, c1 - c0), transform=tw, fill=0, dtype="uint8").astype(bool)
            sl = (slice(r0, r1), slice(c0, c1))
            share = pd.to_numeric(r.share, errors="coerce")
            share = 1.0 if not np.isfinite(share) else float(share)
            m = mw & (ag_ok_sf if bool(getattr(r, "in_city", False)) else ag_ok)[sl] & (b_share[sl] < share)
            if not m.any():
                continue
            cc = np.full(m.shape, c, np.uint8)
            osh = pd.to_numeric(getattr(r, "orchard_share", np.nan), errors="coerce")
            if str(r.kind) == "farm_mixed" and np.isfinite(osh):
                cc = np.where(b_orch[sl] < osh, ORCHARD, FARM).astype(np.uint8)
            yy = (ys + (yf - ys) * b_year[sl]).astype(np.float32)
            dfm = delta_farm[sl] & m
            if dfm.any():
                m = m & ~(dfm & (yf < dike_year[sl]))
                yy = np.where(dfm, np.fmax(yy, dike_year[sl] + 1.0 + 2.0 * b_year[sl]), yy).astype(np.float32)
                if not m.any():
                    continue
            fy, fcv = first_y[sl], first_c[sl]
            unset = m & np.isnan(fy)
            fy[unset], fcv[unset] = yy[unset], cc[unset]
            ly, lcv, lp = last_y[sl], last_c[sl], last_p[sl]
            later = m & ~unset & (np.isnan(ly) | (yy >= ly - 0.5) | (r.prio > lp))
            # a real change of crop (not a better outline of the same era) keeps the old one
            push = later & np.isfinite(ly) & (lcv != cc) & (yy > ly + 5)
            my, mcv = mid_y[sl], mid_c[sl]
            my[push], mcv[push] = ly[push], lcv[push]
            ly[later], lcv[later], lp[later] = yy[later], cc[later], r.prio
        # leveed Delta island ground outside the district outlines (those were cut to the valley
        # floor before the islands had a c.1800 layer): the same reclaimed-island farming
        # (asparagus, potatoes, beans, corn — districts sol_delta / cc_delta_islands), from
        # the island's own levee year
        rest = delta_farm & np.isnan(first_y) & (b_share < 0.9)
        first_c[rest] = FARM
        first_y[rest] = (dike_year + 1.0 + 2.0 * b_year)[rest]
        has_first = np.isfinite(first_y)
        event(has_first, first_c, first_y)
        has_last = np.isfinite(last_y) & (last_c != first_c) & (last_y > first_y)
        has_mid = has_last & np.isfinite(mid_y) & (mid_c != first_c) & (mid_c != last_c) & (mid_y > first_y) & (mid_y < last_y)
        event(has_mid, mid_c, mid_y)
        event(has_last, last_c, last_y)
        log(f"terrain {name}: farm history from researched eras: {int(has_first.sum())} cells, "
            f"{int(has_last.sum())} with a later farm era")
    else:
        event(ag_candidates, FARM, 1852.0 + 10 * h)
        event(ag_candidates & scv, ORCHARD, 1878.0 + 15 * h)
        event(ag_candidates & wine & farm_now & (h < 0.6), VINEYARD, 1870.0 + 40 * h)
    for r, poly in lc_rows:
        c = LANDCOVER_TABLE.get(str(r.cover).strip())
        ys = pd.to_numeric(r.get("year_start"), errors="coerce")
        if c is None or not np.isfinite(ys) or ys <= 1769:
            continue
        m = organic_mask(g, poly) & ~water_now & ~np.isin(N, [DEEP, SHALLOW, FLAT, MARSH])
        if c in (FOREST, OAK):
            m &= trees_near  # forests stand where trees are (today's canopy, slightly widened)
        if c in (FARM, ORCHARD, VINEYARD, PASTURE):
            m &= slope < 12
        # landscape-scale eras spread over ~6 years; city open spaces change on the date
        spread = 0.5 if c in (PARK, URBAN, RESERVOIR) else 6.0
        event(m, c, ys + spread * h)

    # natural forest rows with an end year (the Oakland hills and Woodside redwoods, logged
    # in the 1840s-60s): cut-over brush from the dozen years up to that year, second growth
    # by the 1900s (the trees stand there today) — they stayed forest through the logging
    for r, poly in lc_rows:
        c = LANDCOVER_TABLE.get(str(r.cover).strip())
        ys = pd.to_numeric(r.get("year_start"), errors="coerce")
        ye = pd.to_numeric(r.get("year_end"), errors="coerce")
        if c != FOREST or not np.isfinite(ye) or not (1769 < ye < 9000) or (np.isfinite(ys) and ys > 1769):
            continue
        m = organic_mask(g, poly) & ~water_now & (N == FOREST)
        event(m, SCRUB, ye - 12.0 * h)
        event(m, FOREST, np.maximum(ye + 40.0, 1900.0) + 25.0 * h)

    # ---- vanished large sites (data/manual/vanished_sites/sites.geojson): racetracks,
    # office / industrial campuses, amusement parks… cover the ground over their years,
    # then the site is cleared ground until whatever stands there today
    sp = MANUAL / "vanished_sites" / "sites.geojson"
    if sp.exists():
        SITE_COVER = {"urban": URBAN, "parking": URBAN, "industrial": URBAN, "park": PARK, "grass": PARK,
                      "turf": PARK, "dirt_track": PARK, "water": SHALLOW}
        st = gpd.read_file(sp).to_crs(3857)
        n_site = 0
        for site_id, grp in st.groupby("site_id"):
            spans = []
            for geom, cov, y0, y1 in zip(grp.geometry, grp["cover"], grp["year_start"], grp["year_end"]):
                c = SITE_COVER.get(str(cov))
                y0 = pd.to_numeric(y0, errors="coerce")
                y1 = pd.to_numeric(y1, errors="coerce")
                if c is None or not np.isfinite(y0) or geom is None:
                    continue
                m = rasterize_on(g, [(geom, 1)], fill=0, dtype="uint8").astype(bool) & ~water_now
                if not m.any():
                    continue
                event(m, c, float(y0) + 0.3 * h)
                spans.append((np.flatnonzero(m), float(y0), float(y1) if np.isfinite(y1) else 9999.0))
                del m
                n_site += 1
            # cleared at the end, unless another part of the site took over the ground
            site_cleared(spans, 0.3)
        log(f"terrain {name}: {n_site} parts of vanished sites")

    # ---- military and industrial sites (data/manual/industrial_sites, audited against the
    # USGS topo editions): refineries, plants, yards, bases from their founding; quarry pits
    # and landfills in their dated stages (Permanente 1903 / 1939 / 1948 / 1960 / 1968 /
    # 1979 / 1991 / today); magazines, buffer land and training ground ("open_works") keep
    # their natural ground; a use that ended leaves cleared ground unless a later part
    # takes over
    if ind_sites is not None:
        IND_COVER = {"industrial": URBAN, "tank_farm": URBAN, "rail_yard": URBAN, "military": SUBURB,
                     "quarry_pit": ROCK, "landfill": FILL}
        n_ind = 0
        for site_id, grp in ind_sites.groupby("site_id"):
            spans = []
            for geom, cov, y0, y1 in zip(grp.geometry, grp["cover"], grp["year_start"], grp["year_end"]):
                c = IND_COVER.get(str(cov))
                y0 = pd.to_numeric(y0, errors="coerce")
                y1 = pd.to_numeric(y1, errors="coerce")
                if c is None or not np.isfinite(y0) or geom is None:
                    continue
                m = rasterize_on(g, [(geom, 1)], fill=0, dtype="uint8").astype(bool) & ~water_now
                if not m.any():
                    continue
                event(m, c, float(y0) + 0.5 * h)
                spans.append((np.flatnonzero(m), float(y0), float(y1) if np.isfinite(y1) else 9999.0))
                del m
                n_ind += 1
            site_cleared(spans, 0.5)
        log(f"terrain {name}: {n_ind} parts of military / industrial sites")

    # ---- airports (airports.py): the field is airfield grass from its opening year
    # (after any fill), not city ground or orchard; runways / aprons are drawn on top
    ap_path = INTERIM / "airports.parquet"
    airport = np.zeros((rows, cols), bool)
    # ground claimed from farming: by a park / course / cemetery from its year, by an airfield
    claim_y = np.where(is_park, park_y, open_claim_y).astype(np.float32)
    # a regional park that was farmed returns to its natural cover when it became a park
    # (not ground that was bay or marsh c.1800: a shoreline park on fill, a refuge of salt
    # ponds or diked marsh keeps its made ground until a `restored` row breaches it)
    oc = np.isfinite(open_claim_y) & ~is_park & ~np.isin(N, list(WET))
    event(oc, N, open_claim_y)
    if ap_path.exists():
        ap = gpd.read_parquet(ap_path).to_crs(3857)
        ap_open = rasterize_on(g, [(geom, float(y)) for geom, y in zip(ap.geometry, ap.opened)], fill=0,
                               dtype="float32").astype(np.float32)
        airport = (ap_open > 0) & ~water_now
        # the grass follows the pavement phases (airports.py: airport_pavement.parquet, from
        # the previous run): each cell of the field from the year of the nearest pavement
        pv_path = INTERIM / "airport_pavement.parquet"
        if pv_path.exists():
            pv = gpd.read_parquet(pv_path).to_crs(3857)
            pv = pv[np.isfinite(pv.start)].sort_values("start", ascending=False)
            if len(pv):
                pav = rasterize_on(g, [(geom.buffer(60), float(y)) for geom, y in zip(pv.geometry, pv.start)]).astype(np.float32)
                pv_ok = pav > 0
                if pv_ok.any():
                    # the earliest pavement within ~400 m (a farm between a 1961 runway and
                    # a 2001 taxiway went with the runway), else the nearest pavement
                    rad = max(3, int(round(400 / (g["res"] * np.cos(np.radians(37.5))))))
                    pav_min = ndimage.minimum_filter(np.where(pv_ok, pav, 1e4).astype(np.float32), size=2 * rad + 1)
                    pav_n = nearest_fill(np.where(pv_ok, pav, np.nan).astype(np.float32), pv_ok)
                    pav_y = np.where(pav_min < 5e3, pav_min, pav_n)
                    ap_open = np.where(airport, np.maximum(ap_open, pav_y), ap_open)
        ay = np.where(np.isfinite(fill_y) & filled, np.maximum(ap_open, fill_y + 0.5), ap_open)
        urban &= ~(airport & (urban_y >= ay - 1))
        event(airport, GRASS, ay)
        claim_y = np.where(airport, ay, claim_y)
        # (park_y also tells the decorations when the farms and farmsteads went)
        park_y = np.where(airport & np.isnan(park_y), ay, park_y)

    # ---- urbanisation, parks, planted woods
    # suburban ground: houses in yards and trees (little of the ground under roofs,
    # WorldCover sees trees / grass around) reads green-grey, not as a pale city plate
    treeish = ndimage.uniform_filter(np.isin(wc, [10, 30]).astype(np.float32), 3)
    suburb = (bcov < 0.30) & (treeish > 0.12) & ~((bcov > 0.18) & in_sf)
    # open cells inside the built-up area (WorldCover grass between houses, cells the
    # building rule missed) take the city ground of their surroundings and its year, and
    # urban vs suburban is decided by the neighbourhood (5 x 5 cells), not cell by cell
    uf = ndimage.uniform_filter(urban.astype(np.float32), 5)
    uy = ndimage.uniform_filter(np.where(urban & np.isfinite(urban_y), urban_y, 0).astype(np.float32), 5)
    uc = ndimage.uniform_filter((urban & np.isfinite(urban_y)).astype(np.float32), 5)
    infill = ~urban & (uf > 0.6) & (uc > 0) & ~water_now & ~is_park & ~airport & ~np.isin(N, list(WET) + [FOREST, ROCK, BEACH])
    urban_y = np.where(infill, uy / np.maximum(uc, 1e-6) + 1.0, urban_y)
    urban = urban | infill
    sub_s = ndimage.uniform_filter((suburb & urban).astype(np.float32), 5) / np.maximum(ndimage.uniform_filter(urban.astype(np.float32), 5), 1e-6)
    suburb = sub_s > 0.5
    log(f"terrain {name}: {int(infill.sum())} open cells inside the built-up area take its ground")
    event(urban, np.where(suburb, SUBURB, URBAN).astype(np.uint8), urban_y)
    # 1906: the burned district goes dark for about a year and a half, then the city rebuilds
    fire_path = INTERIM / "fire_1906.geojson"
    if fire_path.exists():
        fg = gpd.read_file(fire_path).to_crs(3857)
        burned_area = rasterize_on(g, [(geom, 1) for geom in fg.geometry], fill=0, dtype="uint8").astype(bool) & ~water_now
        event(burned_area, BURNED, 1906.29)
        rebuilt = 1907.4 + 1.2 * h
        event(burned_area, URBAN, np.where(urban & (urban_y > rebuilt), urban_y, rebuilt))
    # wildfires burn the map only where they burned towns: open country inside a fire perimeter
    # is left as it is (the owner did not want whole mountain ranges turning brown).
    # Built-up ground (data/manual/fires: CAL FIRE damage inspections since 2013):
    # cells with two or more destroyed structures within about 60 m go dark on the fire date
    # and are city ground again when the houses around were rebuilt (mean rebuild year of the
    # structures there, region_buildings' fire_structures.parquet), else return to the natural
    # cover — as the 1906 district does
    fs_path = MANUAL / "fires" / "destroyed_structures.csv"
    if fs_path.exists():
        fs = pd.read_csv(fs_path, usecols=["id", "date", "lon", "lat"])
        rb_path = INTERIM / "fire_structures.parquet"
        if rb_path.exists():
            rb = pd.read_parquet(rb_path, columns=["sid", "rebuild_year"]).drop_duplicates("sid").set_index("sid").rebuild_year
            fs["rebuild"] = fs.id.map(rb).astype(float)
        else:
            fs["rebuild"] = np.nan
        fx = np.radians(fs.lon.values) * 6378137.0
        fyy = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(fs.lat.values) / 2))
        fc = np.rint((fx - g["X0"]) / g["res"]).astype(int)
        fr = np.rint((g["Y0"] - fyy) / g["res"]).astype(int)
        okp = (fc >= 0) & (fc < cols) & (fr >= 0) & (fr < rows)
        fr, fc, fd, frb = fr[okp], fc[okp], fs.date.values[okp].astype(np.float32), fs.rebuild.values[okp]
        win = 3 if g["z"] == 13 else 5
        cnt = np.zeros((rows, cols), np.float32)
        np.add.at(cnt, (fr, fc), 1.0)
        dmax = np.zeros((rows, cols), np.float32)
        np.maximum.at(dmax, (fr, fc), fd)
        rsum = np.zeros((rows, cols), np.float32)
        rcnt = np.zeros((rows, cols), np.float32)
        hasr = np.isfinite(frb)
        np.add.at(rsum, (fr[hasr], fc[hasr]), frb[hasr].astype(np.float32))
        np.add.at(rcnt, (fr[hasr], fc[hasr]), 1.0)
        k2 = float(win * win)
        near = ndimage.uniform_filter(cnt, win, mode="constant") * k2
        fdate = ndimage.maximum_filter(dmax, win, mode="constant")
        rs_, rc_ = ndimage.uniform_filter(rsum, win, mode="constant") * k2, ndimage.uniform_filter(rcnt, win, mode="constant") * k2
        burned_town = (near >= 1.5) & urban & (urban_y < fdate - 1.0) & ~water_now
        rebuilt_y = np.where(rc_ >= 0.5, rs_ / np.maximum(rc_, 1e-6), np.nan).astype(np.float32)
        back = burned_town & np.isfinite(rebuilt_y)
        event(burned_town, BURNED, fdate)
        event(back, np.where(suburb, SUBURB, URBAN).astype(np.uint8), np.fmax(rebuilt_y, fdate + 0.8))
        event(burned_town & ~back, N, fdate + 1.5 + 1.0 * h)
        log(f"terrain {name}: {int(burned_town.sum())} built-up cells burned in wildfires ({int(back.sum())} rebuilt)")
        del cnt, dmax, rsum, rcnt, near, fdate, rs_, rc_
    event(is_park, PARK, park_y)
    event(is_park & np.isfinite(green_close_y) & (green_close_y > park_y), GRASS, green_close_y)
    event(np.isfinite(wood_y), FOREST, wood_y)

    # ---- assemble: natural cover + first three events in time order (row chunks: memory)
    covers = np.zeros((5, rows, cols), np.uint8)
    years = np.full((4, rows, cols), np.nan, np.float32)
    covers[0] = N
    n_all = np.zeros((rows, cols), np.int8)
    # only the events that touch a chunk are expanded there (dense arrays for every event
    # of the region in every chunk ran out of memory once the site layers came in; 48 rows at a
    # time since the fire, Delta and new-county site events: the sort of a chunk is the peak)
    for r0 in range(0, rows, 48):
        r1 = min(rows, r0 + 48)
        a0, a1 = r0 * cols, r1 * cols
        act = []
        for (idx, cv), yv in zip(ev_cover, ev_year):
            lo, hi = np.searchsorted(idx, [a0, a1])
            if hi > lo:
                act.append((idx[lo:hi] - a0, cv[lo:hi], yv[lo:hi]))
        if not act:
            n_all[r0:r1] = 0
            continue
        C = np.full((len(act), r1 - r0, cols), 255, np.uint8)
        Y = np.full((len(act), r1 - r0, cols), np.nan, np.float32)
        for k, (ii, cv, yv) in enumerate(act):
            C[k].ravel()[ii] = cv
            Y[k].ravel()[ii] = yv
        del act
        Y = np.where(C == 255, np.nan, Y)
        order = np.argsort(np.where(np.isnan(Y), np.inf, Y), axis=0, kind="stable")
        C = np.take_along_axis(C, order, 0)
        Y = np.take_along_axis(Y, order, 0)
        n = np.zeros((r1 - r0, cols), np.int8)
        last = N[r0:r1].copy()
        # collect up to 8 changes per cell, then keep the first and the LAST three: the
        # farm eras of the Santa Clara Valley (grazing -> grain -> orchard …) used to fill
        # the four slots and the airport / city that came after them was dropped
        MAXC = 8
        CC = np.full((MAXC, r1 - r0, cols), 255, np.uint8)
        YY = np.full((MAXC, r1 - r0, cols), np.nan, np.float32)
        for e in range(C.shape[0]):
            ce, ye = C[e], Y[e]
            ok = np.isfinite(ye) & (ce != last) & (n < MAXC)
            # agriculture can't come after urbanisation / fill, nor once a park, golf course,
            # cemetery or airfield has the ground
            ok &= ~(np.isin(ce, [FARM, ORCHARD, VINEYARD, PASTURE]) & np.isin(last, [URBAN, SUBURB, FILL, PARK]))
            ok &= ~(np.isin(ce, [FARM, ORCHARD, VINEYARD, PASTURE]) & (ye >= claim_y[r0:r1] - 0.01))
            # natural "fill" after the place is already urban is meaningless
            ok &= ~((ce == FILL) & np.isin(last, [URBAN, SUBURB]))
            # bare fill that is built on within 4 years: go straight to the city (saves a slot)
            if (ce == FILL).any():
                nxt_urban = np.zeros_like(ok)
                for e2 in range(e + 1, C.shape[0]):
                    nxt_urban |= np.isin(C[e2], [URBAN, SUBURB]) & (Y[e2] - ye < 4)
                ok &= ~((ce == FILL) & nxt_urban)
            idx = n[ok]
            rr, cc = np.nonzero(ok)
            CC[idx, rr, cc] = ce[ok]
            YY[idx, rr, cc] = ye[ok]
            last = np.where(ok, ce, last)
            n = n + ok
        # slots: changes 0..3 when n <= 4, else change 0 and changes n-3 .. n-1
        for slot in range(4):
            src = np.where(n <= 4, slot, np.where(slot == 0, 0, n - 4 + slot)).astype(np.int64)
            take = slot < np.minimum(n, 4)
            rr, cc = np.nonzero(take)
            covers[slot + 1, rr + r0, cc] = CC[src[rr, cc], rr, cc]
            years[slot, rr + r0, cc] = YY[src[rr, cc], rr, cc]
        n = np.minimum(n, 4)
        n_all[r0:r1] = n
    n = n_all
    log(f"terrain {name}: changes per vertex " + str(np.bincount(n.ravel(), minlength=4).tolist()))
    ground_under_buildings(name, g, covers, years)
    return covers, years, elev, slope, urban_y, park_y, wood_y


def ground_under_buildings(name, g, covers, years):
    """No building stands over water (owner, 2026-11). The building stages make generated
    and imputed buildings wait for their ground (sf_export / region_buildings land checks);
    what still stands over bay, flat, pond or reservoir when it goes up has a researched,
    recorded or documented date — the ground yields to it here, on the assembled histories:

      * a cell that becomes land later (fill, city) becomes land half a year before the
        first building on it instead (under any part of a footprint);
      * a cell that is water for good gets a deck (city ground) under a sizeable building's
        middle from then on — pier sheds, wharf warehouses; small boathouses are left;
      * before American settlement (villages, missions): the natural cover there is grass.

    Landmark models (viewer anchors, not bridges) only pull an existing fill date forward."""
    rows, cols = g["rows"], g["cols"]
    need = np.full(rows * cols, np.inf, np.float32)     # first building start per cell (any part of a footprint)
    core = np.full(rows * cols, np.inf, np.float32)     # ... of a sizeable building whose middle is on the cell
    until = np.full(rows * cols, -np.inf, np.float32)   # last end of those buildings

    def cells(lon, lat):
        X = np.radians(np.asarray(lon, float)) * 6378137.0
        Y = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(np.asarray(lat, float)) / 2))
        c = np.rint((X - g["X0"]) / g["res"]).astype(np.int64)
        r = np.rint((g["Y0"] - Y) / g["res"]).astype(np.int64)
        ok = (c >= 0) & (r >= 0) & (c < cols) & (r < rows)
        return r * cols + c, ok

    def put(arr, lon, lat, y0, y1=None, sel=None):
        k, ok = cells(lon, lat)
        ok &= np.isfinite(y0)
        if sel is not None:
            ok &= sel
        np.minimum.at(arr, k[ok], np.asarray(y0, np.float32)[ok])
        if y1 is not None:
            np.maximum.at(until, k[ok], np.asarray(y1, np.float32)[ok])

    cell_m = g["res"] * 0.79
    min_area = 150.0 if name == "detail" else 2000.0
    p = INTERIM / "sf_export_final.parquet"
    if p.exists():
        b = gpd.read_parquet(p)
        y0, y1 = b.start_year.values.astype(float), b.end_year.values.astype(float)
        ext = [np.asarray(gm.exterior.coords)[:, :2] for gm in b.geometry.values]
        owner = np.repeat(np.arange(len(ext)), [len(e) for e in ext])
        allv = np.concatenate(ext)
        put(need, allv[:, 0], allv[:, 1], y0[owner], y1[owner])
        rp = b.geometry.representative_point()
        put(need, rp.x.values, rp.y.values, y0, y1)
        put(core, rp.x.values, rp.y.values, y0, sel=b.to_crs(32610).geometry.area.values >= min_area)
        del b, ext, owner, allv
    p = INTERIM / "region_building_points.parquet"
    if p.exists():
        r = pd.read_parquet(p)
        y0, y1 = r.start_year.values.astype(float), r.end_year.values.astype(float)
        put(need, r.lon.values, r.lat.values, y0, y1)
        put(core, r.lon.values, r.lat.values, y0, sel=r.area_m2.values >= min_area)
        # big footprints reach the cells around their middle
        half = np.sqrt(r.area_m2.values) / 2.0
        big = half > 0.6 * cell_m
        if big.any():
            rb = r[big]
            hb = np.minimum(half[big], 3 * cell_m)
            for fx, fy in ((-1, -1), (1, -1), (-1, 1), (1, 1), (0, -1), (0, 1), (-1, 0), (1, 0)):
                dlon = fx * 0.7 * hb / (111320.0 * np.cos(np.radians(rb.lat.values)))
                dlat = fy * 0.7 * hb / 110574.0
                put(need, rb.lon.values + dlon, rb.lat.values + dlat, y0[big], y1[big])
        del r
    lm = np.full(rows * cols, np.inf, np.float32)
    p = INTERIM / "landmark_anchors.json"
    if p.exists():
        import json as _json
        rows_ = [x for x in _json.loads(p.read_text()) if x["kind"] != "bridge"]
        put(lm, [x["lon"] for x in rows_], [x["lat"] for x in rows_], np.array([x["built"][0] for x in rows_], float))
    WATERISH = (DEEP, SHALLOW, FLAT, RESERVOIR, SALTPOND)
    cand = np.flatnonzero(np.isfinite(need) | np.isfinite(lm))
    cv = covers.reshape(5, -1)
    yv = years.reshape(4, -1)
    moved = decks = natural = 0
    for k in cand:
        t_any = min(need[k], lm[k]) - 0.6
        seq = [(float(yv[j, k]), int(cv[j + 1, k])) for j in range(4) if np.isfinite(yv[j, k])]
        nat = int(cv[0, k])
        state = nat
        for y, c in seq:
            if y <= t_any:
                state = c
        if state not in WATERISH:
            continue
        earlier = [e for e in seq if e[0] <= t_any]
        later = [e for e in seq if e[0] > t_any]
        j = next((i for i, e in enumerate(later) if e[1] not in WATERISH), None)
        if t_any <= 1800.0:
            # a village, a mission building: the spot was dry ground
            if np.isfinite(need[k]) and (j is not None or np.isfinite(core[k])):
                nat = GRASS
                new = [e for e in seq if not (e[1] in WATERISH and e[0] < until[k])]
                natural += 1
            else:
                continue
        elif j is not None:
            new = earlier + [(t_any, later[j][1])] + later[j + 1:]
            moved += 1
        elif np.isfinite(core[k]):
            tc = float(core[k]) - 0.6
            new = [e for e in seq if e[0] <= tc] + [(tc, URBAN if tc >= 1849.0 else GRASS)] \
                + [e for e in seq if e[0] > tc and not (e[1] in WATERISH and e[0] < until[k])]
            decks += 1
        else:
            continue
        # drop repeats, keep at most four changes (the first and the last three)
        out, last = [], nat
        for y, c in new:
            if c != last:
                out.append((y, c))
                last = c
        if len(out) > 4:
            out = out[:1] + out[-3:]
        cv[0, k] = nat
        for s_ in range(4):
            if s_ < len(out):
                yv[s_, k], cv[s_ + 1, k] = out[s_]
            else:
                yv[s_, k], cv[s_ + 1, k] = np.nan, 0
    log(f"terrain {name}: ground under buildings: {moved} cells become land earlier (a building stood on them before "
        f"their fill date), {decks} water cells get a deck under a building, {natural} cells of pre-1800 sites are dry ground")


def write_tiles(name, g, covers, years, elev, deco_fn=None, zooms=None):
    z_native = g["z"]
    zooms = zooms or [z_native]
    count = 0
    for z in zooms:
        k = 2 ** (z_native - z)
        tx0 = g["tx0"] // k
        tx1 = -(-g["tx1"] // k)
        ty0 = g["ty0"] // k
        ty1 = -(-g["ty1"] // k)
        for tx in range(tx0, tx1):
            for ty in range(ty0, ty1):
                # native-lattice vertex indices for this tile
                gx = (tx * k - g["tx0"]) * VERTS + np.arange(VERTS + 1) * k
                gy = (ty * k - g["ty0"]) * VERTS + np.arange(VERTS + 1) * k
                inside_x = (gx >= 0) & (gx < g["cols"])
                inside_y = (gy >= 0) & (gy < g["rows"])
                if not inside_x.any() or not inside_y.any():
                    continue
                gxc = np.clip(gx, 0, g["cols"] - 1)
                gyc = np.clip(gy, 0, g["rows"] - 1)
                sel = np.ix_(gyc, gxc)
                cv = covers[:, sel[0], sel[1]].copy()
                yr = years[:, sel[0], sel[1]].copy()
                el = elev[sel].copy()
                outside = ~np.outer(inside_y, inside_x)
                cv[:, outside] = DEEP
                yr[:, outside] = np.nan
                el[outside] = -10
                if (cv[0] == DEEP).all() and np.isnan(yr).all():
                    continue  # open water: the water plane covers it
                cols = {
                    "elev": np.clip(np.rint(el * 10), -32000, 32000).astype(np.int16).ravel(),
                    "cover": np.moveaxis(cv, 0, -1).reshape(-1).astype(np.uint8),
                    "year": enc_year(np.moveaxis(yr, 0, -1).reshape(-1)),
                }
                if deco_fn is not None and z == z_native:
                    cols.update(deco_fn(tx, ty))
                out = TILES / str(z) / str(tx) / f"{ty}.bin.gz"
                write_columnar(out, cols, counts={"n": VERTS + 1, "z": z, "x": tx, "y": ty,
                                                  "deco": int(len(cols.get("deco_kind", [])))})
                count += 1
    log(f"terrain {name}: wrote {count} tiles for zooms {zooms}")


def land_year_of(covers, years):
    """Year each vertex became dry land (NaN: always land, or still water)."""
    wet0 = np.isin(covers[0], list(WET))
    out = np.full(covers.shape[1:], np.nan, np.float32)
    for e in range(4):
        became = wet0 & np.isnan(out) & ~np.isin(covers[e + 1], list(WET)) & np.isfinite(years[e])
        out[became] = years[e][became]
    return out


def decorations(name, g, covers, years, elev, urban_y, park_y, wood_y):
    """Return a function (tx, ty) -> decoration columns for that native tile."""
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import reproject
    from terrain_grid import wc_tiles

    _, lon0, lat0, lon1, lat1 = GRIDS[name]
    # fine tree mask: sub-cells per lattice cell edge (≈7.5 m detail, ≈30 m region)
    sub = 4 if name == "detail" else 2
    res = g["res"] / sub
    t = Affine(res, 0, g["X0"] - g["res"] / 2, 0, -res, g["Y0"] + g["res"] / 2)
    shape = ((g["rows"]) * sub, (g["cols"]) * sub)
    fine = np.zeros(shape, np.uint8)
    for url in wc_tiles(lon0, lat0, lon1, lat1):
        try:
            opts = {"overview_level": 0} if name == "region" else {}
            with rasterio.open(url, **opts) as src:
                tmp = np.zeros(shape, np.uint8)
                reproject(rasterio.band(src, 1), tmp, src_nodata=0, dst_transform=t, dst_crs="EPSG:3857", dst_nodata=0,
                          resampling=Resampling.mode, num_threads=4)
                fine = np.where(tmp > 0, tmp, fine)
        except Exception as e:
            log(f"deco {name}: skip {url.split('/')[-1]} {e}")
    tree_fine = fine == 10
    shrub_fine = fine == 20
    land_year = land_year_of(covers, years)
    # no trees on sports fields, in stadiums (Oracle Park's grass reads as canopy) or
    # inside building footprints
    blockers = []
    lu = RAW / "overture" / "2026-10-21.0" / "base_land_use.parquet"
    if lu.exists():
        d = pd.read_parquet(lu)
        gl = gpd.GeoDataFrame(d, geometry=gpd.GeoSeries.from_wkb(d.geometry), crs=4326)
        gl = gl[gl["class"].isin(["stadium", "pitch", "track", "fairway", "green", "tee", "bunker", "driving_range"])].to_crs(3857)
        blockers += [(geom, 1) for geom in gl.geometry if geom is not None]
    bpath = INTERIM / "sf_buildings.parquet"
    if name == "detail" and bpath.exists():
        bg = gpd.read_parquet(bpath).to_crs(3857)
        blockers += [(geom, 1) for geom in bg.geometry if geom is not None]
    if blockers:
        block = features.rasterize(blockers, out_shape=shape, transform=t, fill=0, dtype="uint8").astype(bool)
        log(f"deco {name}: {int((tree_fine & block).sum())} canopy sub-cells removed (fields, stadiums, buildings)")
        tree_fine &= ~block
        shrub_fine &= ~block
    log(f"deco {name}: tree sub-cells {tree_fine.sum()}, shrub {shrub_fine.sum()}")
    rng_seed = 1906

    def at_vertex(arr, fy, fx):
        return arr[np.clip(np.rint(fy / sub).astype(int), 0, g["rows"] - 1), np.clip(np.rint(fx / sub).astype(int), 0, g["cols"] - 1)]

    lon_all, lat_all = None, None
    mapped = real_farmsteads(g, covers, years, park_y)
    # San Francisco's planted forests (Sutro, Presidio, Golden Gate Park on dunes / scrub)
    lon_g, lat_g = lonlat_of(g)
    # (the treeless northern peninsula: today's trees there were planted)
    in_sf_g = north_peninsula(lon_g, lat_g)
    del lon_g, lat_g
    mapped_mask = mapped[1] if mapped is not None else np.zeros((g["rows"], g["cols"]), bool)
    # generated farmsteads only where no real building is known: within ~300 m of any real
    # footprint (standing today or vanished, region_building_points) the real buildings are the
    # farm, and an invented red farmhouse beside them is wrong (owner, 2026-11)
    real_near = np.zeros((g["rows"], g["cols"]), np.uint8)
    bpp = INTERIM / "region_building_points.parquet"
    if bpp.exists():
        bb = pd.read_parquet(bpp, columns=["lon", "lat"])
        bj = np.rint((np.radians(bb.lon.values) * 6378137.0 - g["X0"]) / g["res"]).astype(int)
        bi = np.rint((g["Y0"] - 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(bb.lat.values) / 2))) / g["res"]).astype(int)
        okb = (bi >= 0) & (bi < g["rows"]) & (bj >= 0) & (bj < g["cols"])
        real_near[bi[okb], bj[okb]] = 1
        rr_ = int(np.ceil(300.0 / (g["res"] * 0.79)))   # ground metres per lattice cell ~ res * cos(lat)
        real_near = ndimage.maximum_filter(real_near, size=2 * rr_ + 1)
        del bb, bj, bi
    real_near = real_near.astype(bool)

    def fn(tx, ty):
        r0 = (ty - g["ty0"]) * VERTS * sub
        c0 = (tx - g["tx0"]) * VERTS * sub
        rs = slice(max(r0, 0), min(r0 + VERTS * sub, shape[0]))
        cs = slice(max(c0, 0), min(c0 + VERTS * sub, shape[1]))
        rng = np.random.default_rng(rng_seed + tx * 100003 + ty)
        kinds, ys, xs, sizes, starts, ends = [], [], [], [], [], []
        # --- trees on real canopy pixels
        tr, tc = np.nonzero(tree_fine[rs, cs])
        keep = rng.random(len(tr)) < (0.55 if name == "detail" else 0.35)
        tr, tc = tr[keep] + rs.start, tc[keep] + cs.start
        if len(tr):
            fy = tr + rng.uniform(-0.45, 0.45, len(tr))
            fx = tc + rng.uniform(-0.45, 0.45, len(tr))
            uy = at_vertex(urban_y, fy, fx)
            py = at_vertex(park_y, fy, fx)
            wy = at_vertex(wood_y, fy, fx)
            nat = at_vertex(covers[0], fy, fx)
            start = np.full(len(fy), np.nan)
            start = np.where(np.isfinite(wy), wy + rng.uniform(0, 4, len(fy)), start)
            start = np.where(np.isnan(start) & np.isfinite(py), py + rng.uniform(2, 12, len(fy)), start)
            start = np.where(np.isnan(start) & np.isfinite(uy), uy + rng.uniform(5, 25, len(fy)), start)
            planted_sf = np.isnan(start) & np.isin(nat, [DUNES, SCRUB, GRASS]) & at_vertex(in_sf_g, fy, fx)
            start = np.where(planted_sf, 1890 + rng.uniform(0, 40, len(fy)), start)
            # trees on made land (bay, flats, marsh until filled) can't predate the land
            ly = at_vertex(land_year, fy, fx)
            start = np.where(np.isfinite(ly), np.fmax(start, ly + rng.uniform(4, 15, len(fy))), start)
            # natural forest: always there (no start)
            conifer_p = np.where(at_vertex(elev, fy, fx) > 150, 0.65, 0.45)
            kind = np.where(rng.random(len(fy)) < conifer_p, D_CONIFER, D_BROADLEAF)
            kind = np.where(np.isfinite(uy) & (rng.random(len(fy)) < 0.06), D_PALM, kind)
            size = np.where(kind == D_CONIFER, rng.uniform(12, 26, len(fy)), rng.uniform(8, 18, len(fy)))
            size = np.where(np.isfinite(uy) & np.isnan(wy), size * 0.75, size)
            kinds.append(kind); ys.append(fy); xs.append(fx); sizes.append(size); starts.append(start); ends.append(np.full(len(fy), np.nan))
        # --- orchards and farmsteads: dated farm cells (procedural placement)
        cv = covers[:, max(r0 // sub, 0):min((r0 // sub) + VERTS + 1, g["rows"]), max(c0 // sub, 0):min((c0 // sub) + VERTS + 1, g["cols"])]
        yv = years[:, max(r0 // sub, 0):min((r0 // sub) + VERTS + 1, g["rows"]), max(c0 // sub, 0):min((c0 // sub) + VERTS + 1, g["cols"])]
        for kind_code, deco in ((ORCHARD, D_ORCHARD), (FARM, D_FARMHOUSE), (VINEYARD, D_FARMHOUSE), (PASTURE, D_FARMHOUSE)):
            for e in range(1, 5):
                m = cv[e] == kind_code
                if not m.any():
                    continue
                vy, vx = np.nonzero(m)
                y_start = yv[e - 1][m]
                y_end = yv[e][m] if e < 4 else np.full(m.sum(), np.nan)
                if deco == D_ORCHARD:
                    # rows of trees: a 3x3 block per lattice cell (≈25 m spacing), on every
                    # third crown of the viewer's orchard ground pattern (8.5 m grid at
                    # (k + 0.5) / 9 cells) — clear of the lanes along the 4-cell block edges
                    # (always on the z13 lattice the shader draws on: in the z14 detail grid
                    # one z13 cell is 2 x 2 lattice cells)
                    lat = 2.0 if g["z"] == 14 else 1.0
                    if lat > 1:
                        ev = (((vy + max(r0 // sub, 0) + g["ty0"] * VERTS) % 2) == 0) & \
                             (((vx + max(c0 // sub, 0) + g["tx0"] * VERTS) % 2) == 0)
                        vy, vx, y_start, y_end = vy[ev], vx[ev], y_start[ev], y_end[ev]
                        if not len(vy):
                            continue
                    oy, ox = np.meshgrid(np.array([-1, 1, 3]) / 6.0 * lat, np.array([-1, 1, 3]) / 6.0 * lat)
                    ly_ = (vy[:, None] + oy.ravel()[None]) + max(r0 // sub, 0)
                    lx_ = (vx[:, None] + ox.ravel()[None]) + max(c0 // sub, 0)
                    # not on the blocks the shader draws as other fields (block_hash)
                    keep = block_hash(np.floor((lx_ + g["tx0"] * VERTS) / (4 * lat)),
                                      np.floor((ly_ + g["ty0"] * VERTS) / (4 * lat))) >= 0.2
                    fy, fx = ly_[keep] * sub, lx_[keep] * sub
                    t_start = np.repeat(y_start, 9)[keep.ravel()]
                    t_end = np.repeat(y_end, 9)[keep.ravel()]
                    # a tree goes when the ground under it (its own nearest lattice vertex, not
                    # the vertex the block was dated from) stops being farm: in the 30 m grid a
                    # block of trees spans four vertices, and trees stood on in streets and yards
                    gi = np.clip(np.rint(ly_[keep]).astype(int), 0, g["rows"] - 1)
                    gj = np.clip(np.rint(lx_[keep]).astype(int), 0, g["cols"] - 1)
                    built = np.zeros(len(gi), bool)   # ground already city / park when the block starts
                    for k in range(4):
                        yk = years[k][gi, gj]
                        ck = covers[k + 1][gi, gj]
                        gone = np.isfinite(yk) & ~np.isin(ck, FARM_COVERS)
                        later = gone & (yk > t_start)
                        t_end = np.where(later, np.fmin(t_end, yk), t_end)
                        chg = np.isfinite(yk) & (yk <= t_start)
                        built = np.where(chg, np.isin(ck, (URBAN, SUBURB, PARK)), built)
                    ok_t = ~built
                    fy, fx, t_start, t_end = fy[ok_t], fx[ok_t], t_start[ok_t], t_end[ok_t]
                    kinds.append(np.full(fy.size, D_ORCHARD)); ys.append(fy); xs.append(fx)
                    sizes.append(rng.uniform(4, 6, fy.size))
                    starts.append(t_start + rng.uniform(0, 3, fy.size))
                    ends.append(t_end)
                else:
                    # one farmstead per ~25 lattice cells, on a hash — except where a
                    # historical map shows where the farmsteads really were
                    pick = ((vy * 31 + vx * 17 + tx * 7 + ty * 13) % (100 if g["z"] == 14 else 25)) == 0
                    pick &= ~mapped_mask[vy + max(r0 // sub, 0), vx + max(c0 // sub, 0)]
                    pick &= ~real_near[vy + max(r0 // sub, 0), vx + max(c0 // sub, 0)]
                    if not pick.any():
                        continue
                    fy = (vy[pick] + max(r0 // sub, 0)) * sub + rng.uniform(-1, 1, pick.sum())
                    fx = (vx[pick] + max(c0 // sub, 0)) * sub + rng.uniform(-1, 1, pick.sum())
                    kinds.append(np.full(pick.sum(), D_FARMHOUSE)); ys.append(fy); xs.append(fx)
                    # (never before American settlement: the mission fields of 1776-1849 had
                    # no farmsteads of this kind)
                    fs = np.maximum(y_start[pick], 1849.0) + rng.uniform(0, 8, pick.sum())
                    sizes.append(rng.uniform(11, 14, pick.sum())); starts.append(fs)
                    ends.append(y_end[pick])
                    wy, wx, ws, wst, wen = windbreaks(fy, fx, fs, y_end[pick], g["res"] / sub, rng)
                    kinds.append(np.full(len(wy), D_BROADLEAF)); ys.append(wy); xs.append(wx)
                    sizes.append(ws); starts.append(wst); ends.append(wen)
        # --- farmsteads at their mapped positions (USGS historical topographic maps)
        if mapped is not None:
            fm = mapped[0]
            lr0, lc0 = (ty - g["ty0"]) * VERTS, (tx - g["tx0"]) * VERTS
            sel = (fm.li.values >= lr0) & (fm.li.values < lr0 + VERTS) & (fm.lj.values >= lc0) & (fm.lj.values < lc0 + VERTS)
            if sel.any():
                f = fm[sel]
                fy, fx = f.li.values * sub, f.lj.values * sub
                st = f.start.values
                en = f.end.values
                kinds.append(f.kind.values.astype(int)); ys.append(fy); xs.append(fx)
                sizes.append(rng.uniform(11, 14, len(f))); starts.append(st); ends.append(en)
                wy, wx, ws, wst, wen = windbreaks(fy, fx, st, en, g["res"] / sub, rng)
                kinds.append(np.full(len(wy), D_BROADLEAF)); ys.append(wy); xs.append(wx)
                sizes.append(ws); starts.append(wst); ends.append(wen)
        if not kinds:
            return {}
        kinds = np.concatenate(kinds); ys = np.concatenate(ys); xs = np.concatenate(xs)
        sizes = np.concatenate(sizes); starts = np.concatenate(starts); ends = np.concatenate(ends)
        # tile-local coordinates 0..65535 across the tile (vertex 0 .. vertex 64)
        ly = np.clip((ys / sub - (ty - g["ty0"]) * VERTS) / VERTS * 65535, 0, 65535)
        lx = np.clip((xs / sub - (tx - g["tx0"]) * VERTS) / VERTS * 65535, 0, 65535)
        pos = np.column_stack([lx, ly]).astype(np.uint16).ravel()
        return {
            "deco_pos": pos,
            "deco_kind": kinds.astype(np.uint8),
            "deco_size": np.clip(np.rint(sizes), 1, 255).astype(np.uint8),
            "deco_years": np.column_stack([enc_year(starts), enc_year(ends)]).ravel(),
        }

    return fn


FARM_COVERS = (FARM, ORCHARD, VINEYARD, PASTURE)


def block_hash(bx, by):
    """Integer hash of a 4x4-cell block of the z13 lattice in [0, 1] — the same as
    blockHash() in the viewer's terrain shader (uint32 arithmetic): orchard blocks with
    a hash < 0.2 are drawn as other fields there, so no orchard trees stand on them."""
    v_x = np.asarray(bx, np.int64).astype(np.uint32)
    v_y = np.asarray(by, np.int64).astype(np.uint32)
    with np.errstate(over="ignore"):
        h = v_x * np.uint32(1664525) + v_y * np.uint32(1013904223)
        h ^= h >> np.uint32(16)
        h *= np.uint32(2246822519)
        h ^= h >> np.uint32(13)
        h *= np.uint32(3266489917)
        h ^= h >> np.uint32(16)
    return (h & np.uint32(65535)).astype(np.float64) / 65535.0


def real_farmsteads(g, covers, years, park_y=None):
    """Farmsteads mapped on USGS historical topographic maps (topo_farmsteads.py ->
    data/manual/farmsteads/). A farmstead seen on one edition and missing from a later
    edition covering the same ground ended between the two; one first seen on a later
    edition was built after the earlier one; otherwise it stands from the farm era of its
    cell (cover history) until the cell becomes city. Where a farmhouse of the map's
    date still stands today (a region footprint at most a few years younger than the map
    within 30 m), only its barn and tank house are drawn (the house is the real footprint).
    Returns (frame with li, lj in lattice units, start, end, kind; bool lattice mask of
    the ground covered by the processed map sheets), or None without the data."""
    from scipy.spatial import cKDTree
    base = MANUAL / "farmsteads"
    p = base / "topo_farmsteads.geojson"
    if not p.exists():
        return None
    pts = gpd.read_file(p).to_crs(3857)
    pts = pts[pts.geometry.notna()].reset_index(drop=True)
    cov = gpd.read_file(base / "coverage.geojson").to_crs(3857) if (base / "coverage.geojson").exists() else None
    rows, cols = g["rows"], g["cols"]
    x, y = pts.geometry.x.values, pts.geometry.y.values
    lj, li = (x - g["X0"]) / g["res"], (g["Y0"] - y) / g["res"]
    ok = (lj >= 0) & (li >= 0) & (lj < cols - 1) & (li < rows - 1)
    pts, x, y, lj, li = pts[ok].reset_index(drop=True), x[ok], y[ok], lj[ok], li[ok]
    if not len(pts):
        return None
    my = pd.to_numeric(pts["map_year"], errors="coerce").fillna(1900).values.astype(float)
    # one farmstead across editions: points within ~60 m on the ground (~75 m Mercator)
    xy = np.column_stack([x, y])
    parent = np.arange(len(pts))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for a, b in cKDTree(xy).query_pairs(75.0):
        ra, rb = find(a), find(b)
        if ra != rb and my[a] != my[b]:
            parent[ra] = rb
    grp = np.array([find(a) for a in range(len(pts))])
    dwell = pts["has_dwelling"].fillna(True).astype(bool).values if "has_dwelling" in pts else np.ones(len(pts), bool)
    gdf = pd.DataFrame({"g": grp, "x": x, "y": y, "y_map": my, "dw": dwell}).groupby("g").agg(
        x=("x", "mean"), y=("y", "mean"), first=("y_map", "min"), last=("y_map", "max"), dw=("dw", "max"))
    # map editions covering each farmstead
    editions = [[] for _ in range(len(gdf))]
    if cov is not None and len(cov):
        gp = gpd.GeoDataFrame(geometry=gpd.points_from_xy(gdf.x, gdf.y), crs=3857)
        j = gpd.sjoin(gp, cov[["map_year", "geometry"]], predicate="within", how="inner")
        for i, yr in zip(j.index.values, pd.to_numeric(j.map_year, errors="coerce").values):
            if np.isfinite(yr):
                editions[i].append(float(yr))
    gi = np.clip(np.rint((g["Y0"] - gdf.y.values) / g["res"]).astype(int), 0, rows - 1)
    gj = np.clip(np.rint((gdf.x.values - g["X0"]) / g["res"]).astype(int), 0, cols - 1)
    cv = covers[:, gi, gj]
    yv = years[:, gi, gj]
    rng = np.random.default_rng(1899)
    starts, ends, cities = [], [], []
    for k in range(len(gdf)):
        first, last = gdf["first"].values[k], gdf["last"].values[k]
        farm_y, city_y = np.nan, np.nan
        for e in range(1, 5):
            if not np.isfinite(yv[e - 1, k]) or yv[e - 1, k] <= 0:
                continue
            if cv[e, k] in FARM_COVERS and not np.isfinite(farm_y):
                farm_y = yv[e - 1, k]
            elif cv[e, k] not in FARM_COVERS and np.isfinite(farm_y) and not np.isfinite(city_y):
                city_y = yv[e - 1, k]
        # the year the cell became city / park ground, whether or not a farm era is
        # recorded there first (3,400 mapped farmsteads on cells that went from natural
        # cover straight to city stood on among the houses to this day)
        if not np.isfinite(city_y):
            for e in range(1, 5):
                if np.isfinite(yv[e - 1, k]) and yv[e - 1, k] > 0 and cv[e, k] in (URBAN, SUBURB, PARK, FILL):
                    city_y = yv[e - 1, k]
                    break
        before = [m for m in editions[k] if m < first - 0.5]
        after = [m for m in editions[k] if m > last + 0.5]
        if before:
            b = max(before)
            st = b + (first - b) * rng.uniform(0.2, 0.9)
        elif np.isfinite(farm_y) and farm_y < first:
            st = min(farm_y + rng.uniform(0, 8), first - 0.5)
        else:
            st = first - rng.uniform(4, 15)
        # no farmsteads before American settlement (the mission / rancho range was
        # unfenced; the earliest maps are from 1885)
        st = max(st, 1849 + rng.uniform(0, 8))
        if after:
            a = min(after)
            en = last + (a - last) * rng.uniform(0.2, 0.9)
        else:
            # (a cell already city ground on the last map that shows the farmstead: it
            # went within a few years of that map)
            en = city_y if np.isfinite(city_y) and city_y > last else (last + rng.uniform(2, 10) if np.isfinite(city_y) else np.nan)
        # a park, golf course or cemetery took the ground: the farm went with it
        if park_y is not None and np.isfinite(park_y[gi[k], gj[k]]):
            py_ = float(park_y[gi[k], gj[k]])
            en = py_ if not np.isfinite(en) else min(en, py_)
        starts.append(st)
        ends.append(en)
        cities.append(city_y)
    out = pd.DataFrame({"li": (g["Y0"] - gdf.y.values) / g["res"], "lj": (gdf.x.values - g["X0"]) / g["res"],
                        "start": starts, "end": ends, "kind": D_FARMHOUSE})
    # mapped with barns / sheds only (open squares on the 1950s sheets): no house
    out.loc[~gdf["dw"].values, "kind"] = D_FARMYARD
    # surviving farmhouses: a footprint standing today, about as old as the map
    bp = INTERIM / "region_building_points.parquet"
    if bp.exists():
        b = pd.read_parquet(bp, columns=["lon", "lat", "start_year", "end_year"])
        b = b[(b.end_year > 9000) & (b.start_year < 1950)]
        bx = np.radians(b.lon.values) * 6378137.0
        by = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(b.lat.values) / 2))
        d, idx = cKDTree(np.column_stack([bx, by])).query(np.column_stack([gdf.x.values, gdf.y.values]),
                                                          distance_upper_bound=38.0)
        hit = np.isfinite(d)
        old = np.zeros(len(gdf), bool)
        old[hit] = b.start_year.values[idx[hit]] <= gdf["first"].values[hit] + 5
        out.loc[old, "kind"] = D_FARMYARD
        # the house still stands (a missing later edition is a detector miss); the barns
        # go when the cell becomes city
        cy_ = np.asarray(cities, float)
        out.loc[old, "end"] = np.where(np.isfinite(cy_) & (cy_ <= gdf["last"].values), gdf["last"].values + 6.0, cy_)[old]
        # real buildings tell the story once they are there (owner, 2026-11: no red farm
        # buildings where real houses are known): a mapped farmstead - house or barns - ends
        # when the first building standing today within ~60 m of it was built, and is not
        # drawn at all where such a building is as old as the farmstead (the map's symbol and
        # the footprint are the same farm)
        ball = pd.read_parquet(bp, columns=["lon", "lat", "start_year", "end_year"])
        ball = ball[ball.end_year > 9000]
        ax = np.radians(ball.lon.values) * 6378137.0
        ay = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(ball.lat.values) / 2))
        dd, ii = cKDTree(np.column_stack([ax, ay])).query(np.column_stack([gdf.x.values, gdf.y.values]), k=8,
                                                          distance_upper_bound=76.0)
        ys_ = np.where(np.isfinite(dd), ball.start_year.values[np.minimum(ii, len(ball) - 1)], np.inf)
        real_first = ys_.min(axis=1)
        has_real = np.isfinite(real_first)
        st_ = out["start"].values.astype(float)
        en_ = out["end"].values.astype(float)
        out["end"] = np.where(has_real, np.fmin(en_, np.maximum(real_first, st_)), en_)
        gone = has_real & (out["end"].values <= st_ + 0.5)
        n_cut = int((has_real & ~gone).sum())
        out = out[~gone].reset_index(drop=True)
        log(f"farmsteads: {int(gone.sum())} mapped farmsteads are today's real buildings (not drawn), "
            f"{n_cut} more end when a real building takes the site")
    mask = np.zeros((rows, cols), bool)
    if cov is not None and len(cov):
        t = Affine(g["res"], 0, g["X0"] - g["res"] / 2, 0, -g["res"], g["Y0"] + g["res"] / 2)
        mask = features.rasterize([(geom, 1) for geom in cov.geometry if geom is not None], out_shape=(rows, cols),
                                  transform=t, fill=0, dtype="uint8").astype(bool)
    log(f"farmsteads: {len(out)} mapped ({int((out.kind == D_FARMYARD).sum())} farmhouses still standing), "
        f"{int(mask.sum())} lattice cells covered by the maps")
    return out, mask


def windbreaks(fy, fx, start, end, cell_m, rng):
    """A row of 4-6 tall trees (the eucalyptus / cypress windbreak of a California
    farmstead) ~25 m upwind (north-west) of each farmstead, planted a few years after it.
    fy, fx in fine-grid units of cell_m metres."""
    out = ([], [], [], [], [])
    for y, x, s0, e0 in zip(fy, fx, start, end):
        n = int(rng.integers(4, 7))
        along = rng.uniform(0, 1) < 0.5  # row runs east-west north of the house, or north-south west of it
        t = (np.arange(n) - (n - 1) / 2) * 8.0 / cell_m
        if along:
            yy, xx = np.full(n, y - 26.0 / cell_m), x + t
        else:
            yy, xx = y + t, np.full(n, x - 26.0 / cell_m)
        out[0].append(yy + rng.uniform(-0.6, 0.6, n) / cell_m)
        out[1].append(xx + rng.uniform(-0.6, 0.6, n) / cell_m)
        out[2].append(rng.uniform(14, 20, n))
        out[3].append(np.full(n, s0 + rng.uniform(3, 8)))
        out[4].append(np.full(n, e0))
    if not out[0]:
        return (np.zeros(0),) * 5
    return tuple(np.concatenate(a) for a in out)


def write_elevation_lookup(name, g, elev, step):
    """Coarse elevation grid for the viewer (placing landmarks, labels, cars)."""
    e = elev[::step, ::step]
    out = VIEWER_DATA / f"elevation-{name}.bin.gz"
    write_columnar(out, {"elev": np.clip(np.rint(e * 10), -32000, 32000).astype(np.int16).ravel()},
                   counts={"rows": e.shape[0], "cols": e.shape[1]},
                   meta={"X0": g["X0"], "Y0": g["Y0"], "res": g["res"] * step, "units": "decimetres, EPSG:3857 vertex lattice"})
    log(f"terrain {name}: elevation lookup {e.shape} -> {out}")


def region_under_detail(g, elev):
    """Where the 30 m detail grid exists (San Francisco), the coarse region tiles shown
    from further out never rise above it: each region cell takes the lowest detail
    elevation around it. Roads, rails and buildings are draped on the detail grid, so a
    freeway in a cut (US-101 below Potrero Hill) is no longer buried under the averaged
    hillside until the detail tiles load."""
    from terrain_grid import grid_def
    gd = grid_def("detail")
    ed = np.load(INTERIM / "grid_detail_elev.npy").astype(np.float32)
    ed = np.where(ed < -500, np.nan, ed)
    mn = ndimage.minimum_filter(np.nan_to_num(ed, nan=1e4), size=3)
    rows, cols = elev.shape
    X = g["X0"] + (np.arange(cols) + 0.5) * g["res"]
    Y = g["Y0"] - (np.arange(rows) + 0.5) * g["res"]
    c = np.floor((X - gd["X0"]) / gd["res"]).astype(int)
    r = np.floor((gd["Y0"] - Y) / gd["res"]).astype(int)
    okc = (c >= 0) & (c < gd["cols"])
    okr = (r >= 0) & (r < gd["rows"])
    out = elev.copy()
    sub = mn[np.ix_(r[okr], c[okc])]
    reg = out[np.ix_(np.nonzero(okr)[0], np.nonzero(okc)[0])]
    valid = sub < 5e3
    reg[valid] = np.minimum(reg[valid], sub[valid])
    out[np.ix_(np.nonzero(okr)[0], np.nonzero(okc)[0])] = reg
    log(f"terrain region: {int(valid.sum())} cells capped by the detail grid")
    return out


def merge_detail_deco():
    """The z13 region tiles over the detail grid carry the detail grid's decorations (the
    trees, orchards and farmsteads of their z14 children) instead of their own: the viewer
    shows z13 tiles from zoom 11.5 and z14 tiles from 12.5, and two independently placed
    sets would swap every tree in the urban bay plain at that zoom."""
    from audit_region_years import read_bayt
    kids = {}
    for f in (TILES / "14").glob("*/*.bin.gz"):
        x, y = int(f.parent.name), int(f.name.split(".")[0])
        kids.setdefault((x >> 1, y >> 1), []).append((x, y, f))
    n_par = n_add = 0
    for (px, py), ch in kids.items():
        pf = TILES / "13" / str(px) / f"{py}.bin.gz"
        if not pf.exists():
            continue
        h, c = read_bayt(pf)
        pos = c.get("deco_pos", np.zeros(0, np.uint16)).reshape(-1, 2)
        kind = c.get("deco_kind", np.zeros(0, np.uint8))
        size = c.get("deco_size", np.zeros(0, np.uint8))
        yrs = c.get("deco_years", np.zeros(0, np.uint16)).reshape(-1, 2)
        qx = (pos[:, 0] >= 32768).astype(int)
        qy = (pos[:, 1] >= 32768).astype(int)
        keep = np.ones(len(kind), bool)
        P, K, S, Yr = [], [], [], []
        for x, y, f in ch:
            ox, oy = x - 2 * px, y - 2 * py
            keep &= ~((qx == ox) & (qy == oy))
            _, cc = read_bayt(f)
            if "deco_kind" not in cc or not len(cc["deco_kind"]):
                continue
            cp = cc["deco_pos"].reshape(-1, 2).astype(np.float64)
            P.append(np.column_stack([(ox * 65535 + cp[:, 0]) / 2, (oy * 65535 + cp[:, 1]) / 2]))
            K.append(cc["deco_kind"]); S.append(cc["deco_size"]); Yr.append(cc["deco_years"].reshape(-1, 2))
        P = np.concatenate([pos[keep].astype(np.float64)] + P) if P else pos[keep].astype(np.float64)
        K = np.concatenate([kind[keep]] + K) if K else kind[keep]
        S = np.concatenate([size[keep]] + S) if S else size[keep]
        Yr = np.concatenate([yrs[keep]] + Yr) if Yr else yrs[keep]
        cols = {k: c[k] for k in ("elev", "cover", "year")}
        if len(K):
            cols.update({"deco_pos": np.clip(np.rint(P), 0, 65535).astype(np.uint16).ravel(),
                         "deco_kind": K.astype(np.uint8), "deco_size": S.astype(np.uint8),
                         "deco_years": Yr.astype(np.uint16).ravel()})
        counts = dict(h.get("counts", {}), deco=int(len(K)))
        write_columnar(pf, cols, counts=counts)
        n_par += 1
        n_add += int(len(K)) - int(keep.sum())
    log(f"terrain: {n_par} z13 tiles over the detail grid take its decorations ({n_add:+d} instances)")


def rank_byte(lon, lat):
    """rankByte() of viewer/src/layers/deco-layer.ts (32-bit integer hash of the position)."""
    M = np.uint64(0xFFFFFFFF)
    a = np.floor(np.asarray(lon, np.float64) * 3.3e4 + 0.5).astype(np.int64).astype(np.uint64) & M
    b = np.floor(np.asarray(lat, np.float64) * 3.3e4 + 0.5).astype(np.int64).astype(np.uint64) & M
    h = ((a * np.uint64(73856093)) & M) ^ ((b * np.uint64(19349663)) & M)
    h = ((h ^ (h >> np.uint64(13))) * np.uint64(0x5BD1E995)) & M
    h ^= h >> np.uint64(15)
    return (h % np.uint64(256)).astype(np.int64)


def prune_unseen_deco():
    """Drop the decorations the viewer never draws (2026-11: the published site had grown to
    half a gigabyte, four fifths of the terrain tiles being tree records). The tile loader
    (decodeTile in viewer/src/layers/terrain.ts) skips, by the tree's position rank,
      * broadleaf / conifer trees of rank > 0.4 in a dense tile (> 6,000 instances per z13
        tile area) at every zoom, and
      * every tree, shrub and orchard tree of rank > 0.4 in a z13 tile drawn as such — the
        only way a z13 tile under four z14 detail tiles is ever drawn.
    The same test here, with the same hash on the same coordinates, so nothing visible
    changes; the viewer keeps its own test."""
    from audit_region_years import read_bayt
    n_tiles = n_drop = n_all = 0
    for z in (13, 14):
        for f in (TILES / str(z)).glob("*/*.bin.gz"):
            x, y = int(f.parent.name), int(f.name.split(".")[0])
            h, c = read_bayt(f)
            if "deco_kind" not in c or not len(c["deco_kind"]):
                continue
            kind = c["deco_kind"]
            pos = c["deco_pos"].reshape(-1, 2)
            gx = pos[:, 0].astype(np.float64) / 65535 * 64
            gy = pos[:, 1].astype(np.float64) / 65535 * 64
            west, east = x / 2 ** z * 360 - 180, (x + 1) / 2 ** z * 360 - 180
            lon = west + ((east - west) * gx) / 64
            nn = math.pi - (2 * math.pi * (y + gy / 64)) / 2 ** z
            lat = (180 / math.pi) * np.arctan(np.sinh(nn))
            high = rank_byte(lon, lat) / 255 > 0.4
            dense = len(kind) * (4 if z == 14 else 1) > 6000
            drop = high & (kind <= 1) & dense
            if z == 13 and all((TILES / "14" / str(2 * x + i) / f"{2 * y + j}.bin.gz").exists() for i in (0, 1) for j in (0, 1)):
                drop |= high & (kind != D_FARMHOUSE) & (kind != D_FARMYARD)
            n_all += len(kind)
            if not drop.any():
                continue
            keep = ~drop
            cols = {k: c[k] for k in ("elev", "cover", "year")}
            cols.update({"deco_pos": pos[keep].ravel(), "deco_kind": kind[keep], "deco_size": c["deco_size"][keep],
                         "deco_years": c["deco_years"].reshape(-1, 2)[keep].ravel()})
            write_columnar(f, cols, counts=dict(h.get("counts", {}), deco=int(keep.sum())))
            n_tiles += 1
            n_drop += int(drop.sum())
    log(f"terrain: {n_drop} of {n_all} decorations the viewer never draws removed from {n_tiles} tiles")


def main():
    meta = {}
    for name, zooms, step in (("region", [8, 9, 10, 11, 12, 13], 4), ("detail", [14], 2)):
        g, d = load_grid(name)
        covers, years, elev, slope, urban_y, park_y, wood_y = histories(name, g, d)
        if name == "region":
            elev = region_under_detail(g, elev)
        deco = decorations(name, g, covers, years, elev, urban_y, park_y, wood_y)
        write_tiles(name, g, covers, years, elev, deco, zooms)
        write_elevation_lookup(name, g, elev, step)
        np.save(INTERIM / f"grid_{name}_landyear.npy", land_year_of(covers, years))
        # the assembled histories, for the audits (audit_ground.py: no building over water)
        np.save(INTERIM / f"grid_{name}_covers.npy", covers)
        np.save(INTERIM / f"grid_{name}_years.npy", years)
        meta[name] = {"z": g["z"], "tx0": g["tx0"], "ty0": g["ty0"], "tx1": g["tx1"], "ty1": g["ty1"], "zooms": zooms}
    merge_detail_deco()
    prune_unseen_deco()
    (VIEWER_DATA / "terrain.json").write_text(json.dumps({"grids": meta, "covers": COVER_NAMES,
                                                          "deco": ["broadleaf", "conifer", "palm", "orchard", "farmhouse", "shrub", "farmyard"]}, indent=1))


if __name__ == "__main__":
    main()
