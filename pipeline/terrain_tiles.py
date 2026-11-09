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
    inland = lon > -122.30
    N[tree & inland & (elev < 700)] = OAK
    N[tree & ~(inland & (elev < 700))] = FOREST
    # San Francisco had almost no native trees: planted forests and the city sit on
    # dunes (west) and grassy/scrubby hills (east)
    sf_dunes = in_sf & (lon < -122.445) & (elev < 120)
    # the dune sheet doesn't stop at the county line: it ran on south through Daly City's
    # Westlake, Lake Merced's shore and Fort Funston to the cliffs at Mussel Rock
    # (refined by data/manual/landscape/dunes.geojson when present)
    sf_dunes |= ~in_sf & (lat > 37.662) & (lat < 37.712) & (lon < -122.462 - (37.712 - lat) * 0.25) & (elev < 110)
    N[in_sf & (tree | (wc == 50) | (wc == 40))] = SCRUB
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
    # mapped marsh / flat well above the tides is a registration error of the historical
    # layers (e.g. downtown San Rafael at 15 m): dry ground
    N[np.isin(N, [MARSH, FLAT]) & (elev > 6) & ~water_now] = GRASS
    # SFEI c.1998 "bay fill" is made land by definition: it was bay before (e.g. the
    # Yerba Buena Shoals under Treasure Island), whatever the coarser c.1800 layers say
    made_land = np.isin(b98, [12, 13]) & ~np.isin(N, list(WET))
    N[made_land] = SHALLOW
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
    is_park = np.isfinite(park_y)
    urban &= ~is_park

    # ---- diking of marsh into salt ponds / diked land
    dike_year = np.full((rows, cols), 1900.0, np.float32)
    salt = np.isin(b18, [3, 4, 6]) & np.isin(b98, [6, 11])
    diked = np.isin(b18, [3, 4, 6]) & np.isin(b98, [9, 10])
    zones_fill = np.full((rows, cols), np.nan, np.float32)
    pier_y = np.full((rows, cols), np.nan, np.float32)
    h = (np.add.outer(np.arange(rows) * 7919, np.arange(cols) * 104729) % 997) / 997.0
    restored = []
    excavated = []
    was_wet0 = np.isin(N, list(WET))
    # distance (cells) from the c.1800 shore: fill advanced outward from it
    shore_d = ndimage.distance_transform_edt(was_wet0).astype(np.float32)
    zone_rows = polygon_table(MANUAL / "fill_zones.csv", g)
    zone_rows.sort(key=lambda rp: str(rp[0].zone_id).startswith("fb_"))  # specific zones first
    covered = np.zeros((rows, cols), bool)
    researched_fill = np.zeros((rows, cols), bool)
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
            sel = m & (salt | diked)
            dike_year[sel] = y[sel]
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
    for r, poly in wh_rows:
        ys = pd.to_numeric(r.year_start, errors="coerce")
        if not np.isfinite(ys):
            continue
        m = raster_mask(g, poly)
        cov = str(r.cover).strip()
        if cov in ("salt_pond", "diked"):
            sel = m & (salt | diked)
            dike_year[sel] = ys + 4.0 * h[sel]
        elif cov in ("lake", "shallow_water"):
            water_rows.append((m, cov, float(ys)))
    event(salt, SALTPOND, dike_year)
    event(diked, DIKED, dike_year)

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
    still_bay = was_wet & ~water_now & ~salt & ~diked & np.isin(b98, [3, 4, 5, 8])
    filled = was_wet & ~water_now & ~salt & ~diked & ~is_pier & ~still_bay
    fill_y = np.where(np.isfinite(zones_fill), zones_fill, np.where(urban, urban_y - 3, np.nan))
    fill_y = np.where(filled & np.isnan(fill_y), 1950.0, fill_y)
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

    # c.1800 marsh / flat that is open water today (not a salt pond or diked): narrow
    # channels are sloughs that were always water; broad water was made later — Lake
    # Merritt (dammed 1869), the Oakland estuary / tidal canal (1874-1902), dredged
    # harbours — water from c.1870-90 unless a researched row says when
    became = np.isin(N, [MARSH, FLAT]) & water_now & ~salt & ~diked
    broad = ndimage.binary_opening(became, iterations=2)
    N[became & ~broad] = SHALLOW
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
    event(broad & ~researched_water, SHALLOW, 1870.0 + 20.0 * h)

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
        # and the 1940s-50s topo orchards; each cell keeps its first farm era and its last one
        # before the city (the terrain holds four changes per cell)
        from scipy.special import ndtr
        AGK = {"grain": FARM, "hay": FARM, "vegetables": FARM, "nursery": FARM, "farm_mixed": FARM,
               "orchard": ORCHARD, "vineyard": VINEYARD, "pasture_dairy": PASTURE}
        PRIO = {"district_era": 0, "broek_1931": 1, "topo_1940s": 2, "special": 3}

        def blob(seed, sigma):
            r = np.random.default_rng(seed).standard_normal((rows, cols)).astype(np.float32)
            b = ndimage.gaussian_filter(r, sigma)
            return ndtr(b / (b.std() + 1e-9)).astype(np.float32)
        b_share, b_orch, b_year = blob(1851, 4.0), blob(1885, 3.0), blob(1869, 6.0)
        ag = gpd.read_file(ag_path).to_crs(3857)
        ag = ag[ag.geometry.notna()].copy()
        ag["prio"] = ag["layer"].map(PRIO).fillna(0)
        ag = ag.sort_values(["year_start", "prio"]).reset_index(drop=True)
        ag_ok = ~water_now & (slope < 15) & (elev < 500) & ~np.isin(N, [DEEP, SHALLOW, FLAT, MARSH, ROCK, BEACH]) & ~in_sf
        first_c = np.full((rows, cols), 255, np.uint8)
        first_y = np.full((rows, cols), np.nan, np.float32)
        last_c = np.full((rows, cols), 255, np.uint8)
        last_y = np.full((rows, cols), np.nan, np.float32)
        last_p = np.full((rows, cols), -1, np.int8)
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
            m = mw & ag_ok[sl] & (b_share[sl] < share)
            if not m.any():
                continue
            cc = np.full(m.shape, c, np.uint8)
            osh = pd.to_numeric(getattr(r, "orchard_share", np.nan), errors="coerce")
            if str(r.kind) == "farm_mixed" and np.isfinite(osh):
                cc = np.where(b_orch[sl] < osh, ORCHARD, FARM).astype(np.uint8)
            yy = (ys + (yf - ys) * b_year[sl]).astype(np.float32)
            fy, fcv = first_y[sl], first_c[sl]
            unset = m & np.isnan(fy)
            fy[unset], fcv[unset] = yy[unset], cc[unset]
            ly, lcv, lp = last_y[sl], last_c[sl], last_p[sl]
            later = m & ~unset & (np.isnan(ly) | (yy >= ly - 0.5) | (r.prio > lp))
            ly[later], lcv[later], lp[later] = yy[later], cc[later], r.prio
        has_first = np.isfinite(first_y)
        event(has_first, first_c, first_y)
        has_last = np.isfinite(last_y) & (last_c != first_c) & (last_y > first_y)
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
    if ap_path.exists():
        ap = gpd.read_parquet(ap_path).to_crs(3857)
        ap_open = rasterize_on(g, [(geom, float(y)) for geom, y in zip(ap.geometry, ap.opened)], fill=0,
                               dtype="float32").astype(np.float32)
        airport = (ap_open > 0) & ~water_now
        ay = np.where(np.isfinite(fill_y) & filled, np.maximum(ap_open, fill_y + 0.5), ap_open)
        urban &= ~(airport & (urban_y >= ay - 1))
        event(airport, GRASS, ay)

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
    event(is_park, PARK, park_y)
    event(np.isfinite(wood_y), FOREST, wood_y)

    # ---- assemble: natural cover + first three events in time order (row chunks: memory)
    covers = np.zeros((5, rows, cols), np.uint8)
    years = np.full((4, rows, cols), np.nan, np.float32)
    covers[0] = N
    n_all = np.zeros((rows, cols), np.int8)
    # only the events that touch a chunk are expanded there (dense arrays for every event
    # of the region in every chunk ran out of memory once the site layers came in)
    for r0 in range(0, rows, 192):
        r1 = min(rows, r0 + 192)
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
            # agriculture can't come after urbanisation / fill
            ok &= ~(np.isin(ce, [FARM, ORCHARD, VINEYARD, PASTURE]) & np.isin(last, [URBAN, SUBURB, FILL, PARK]))
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
    return covers, years, elev, slope, urban_y, park_y, wood_y


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
    mapped = real_farmsteads(g, covers, years)
    # San Francisco's planted forests (Sutro, Presidio, Golden Gate Park on dunes / scrub)
    lon_g, lat_g = lonlat_of(g)
    in_sf_g = (lon_g > SF_BOX[0]) & (lon_g < SF_BOX[2]) & (lat_g > SF_BOX[1]) & (lat_g < SF_BOX[3])
    del lon_g, lat_g
    mapped_mask = mapped[1] if mapped is not None else np.zeros((g["rows"], g["cols"]), bool)

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
            planted_sf = np.isnan(start) & np.isin(nat, [DUNES, SCRUB]) & at_vertex(in_sf_g, fy, fx)
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
                    kinds.append(np.full(fy.size, D_ORCHARD)); ys.append(fy); xs.append(fx)
                    sizes.append(rng.uniform(4, 6, fy.size))
                    starts.append(np.repeat(y_start, 9)[keep.ravel()] + rng.uniform(0, 3, fy.size))
                    ends.append(np.repeat(y_end, 9)[keep.ravel()])
                else:
                    # one farmstead per ~25 lattice cells, on a hash — except where a
                    # historical map shows where the farmsteads really were
                    pick = ((vy * 31 + vx * 17 + tx * 7 + ty * 13) % (100 if g["z"] == 14 else 25)) == 0
                    pick &= ~mapped_mask[vy + max(r0 // sub, 0), vx + max(c0 // sub, 0)]
                    if not pick.any():
                        continue
                    fy = (vy[pick] + max(r0 // sub, 0)) * sub + rng.uniform(-1, 1, pick.sum())
                    fx = (vx[pick] + max(c0 // sub, 0)) * sub + rng.uniform(-1, 1, pick.sum())
                    kinds.append(np.full(pick.sum(), D_FARMHOUSE)); ys.append(fy); xs.append(fx)
                    fs = y_start[pick] + rng.uniform(0, 8, pick.sum())
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


def real_farmsteads(g, covers, years):
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
        before = [m for m in editions[k] if m < first - 0.5]
        after = [m for m in editions[k] if m > last + 0.5]
        if before:
            b = max(before)
            st = b + (first - b) * rng.uniform(0.2, 0.9)
        elif np.isfinite(farm_y) and farm_y < first:
            st = min(farm_y + rng.uniform(0, 8), first - 0.5)
        else:
            st = first - rng.uniform(4, 15)
        if after:
            a = min(after)
            en = last + (a - last) * rng.uniform(0.2, 0.9)
        else:
            en = city_y if np.isfinite(city_y) and city_y > last else np.nan
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
        out.loc[old, "end"] = np.asarray(cities)[old]
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
        meta[name] = {"z": g["z"], "tx0": g["tx0"], "ty0": g["ty0"], "tx1": g["tx1"], "ty1": g["ty1"], "zooms": zooms}
    (VIEWER_DATA / "terrain.json").write_text(json.dumps({"grids": meta, "covers": COVER_NAMES,
                                                          "deco": ["broadleaf", "conifer", "palm", "orchard", "farmhouse", "shrub", "farmyard"]}, indent=1))


if __name__ == "__main__":
    main()
