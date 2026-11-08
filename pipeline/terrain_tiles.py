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
                    URBAN, VINEYARD, WET, WETLAND)
COVER_NAMES = ["deep_water", "shallow_water", "tidal_flat", "tidal_marsh", "beach", "dunes", "grassland",
               "scrub", "oak_woodland", "forest", "farmland", "orchard", "vineyard", "pasture", "salt_pond",
               "diked_wetland", "urban", "park", "rock", "riparian", "fill", "wetland", "reservoir", "burned"]
# decoration kinds
D_BROADLEAF, D_CONIFER, D_PALM, D_ORCHARD, D_FARMHOUSE, D_SHRUB = range(6)

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
    b = gpd.read_parquet(INTERIM / "sf_buildings.parquet").to_crs(3857)
    b = b.sort_values("start_year", ascending=False)  # earliest painted last -> wins
    shapes = [(geom, float(y)) for geom, y in zip(b.geometry, b.start_year)]
    yr = rasterize_on(g, shapes)
    # spread to the street/yard cells around buildings (urban fabric), earliest neighbour
    filled = np.isfinite(yr)
    tmp = np.where(filled, yr, 9999.0)
    tmp = ndimage.minimum_filter(tmp, size=3)
    out = np.where(filled, yr, np.where(tmp < 9999, tmp, np.nan))
    return out


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
    tree = wc == 10
    trees_near = ndimage.binary_dilation(tree, iterations=2)
    inland = lon > -122.30
    N[tree & inland & (elev < 700)] = OAK
    N[tree & ~(inland & (elev < 700))] = FOREST
    # San Francisco had almost no native trees: planted forests and the city sit on
    # dunes (west) and grassy/scrubby hills (east)
    sf_dunes = in_sf & (lon < -122.445) & (elev < 120)
    N[in_sf & (tree | (wc == 50) | (wc == 40))] = SCRUB
    N[sf_dunes & ~(wc == 60)] = DUNES
    lc_rows = polygon_table(TABLES / "landcover_history.csv", g)
    # researched open spaces inside the city (parade grounds, plazas...) override the
    # built-up snapshot outlines: their own rows say when they were grass / paved / lawn
    open_override = np.zeros((rows, cols), bool)
    for r, poly in lc_rows:
        if str(r.get("region", "")) == "San Francisco" and str(r.cover).strip() in ("grassland", "park", "lawn", "paved", "lake"):
            open_override |= raster_mask(g, poly)
    for r, poly in lc_rows:
        c = LANDCOVER_TABLE.get(str(r.cover).strip())
        if c is None or pd.notna(r.get("year_start")) and float(r.year_start) > 1800:
            continue  # only natural (pre-1800) cover here; eras handled below
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
    # SFEI c.1998 "bay fill" is made land by definition: it was bay before (e.g. the
    # Yerba Buena Shoals under Treasure Island), whatever the coarser c.1800 layers say
    made_land = np.isin(b98, [12, 13]) & ~np.isin(N, list(WET))
    N[made_land] = SHALLOW

    ev_cover, ev_year = [], []

    def event(mask, cover, year):
        c = np.full((rows, cols), 255, np.uint8)
        y = np.full((rows, cols), np.nan, np.float32)
        c[mask] = cover if np.isscalar(cover) else cover[mask]
        y[mask] = year if np.isscalar(year) else year[mask]
        ev_cover.append(c)
        ev_year.append(y)

    # ---- urban year
    urban_y = np.full((rows, cols), np.nan, np.float32)
    if in_sf.any():
        sfy = sf_building_years(g)
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
        urban_y = np.where(has_ext & ~green_now & (np.isnan(urban_y) | (ext_y < urban_y)), ext_y, urban_y)
    else:
        ext_green_y = np.full((rows, cols), np.nan, np.float32)
        sfy = np.full((rows, cols), np.nan, np.float32)
    # Outside SF, HISDAC's 250 m "first built-up year" comes from the oldest *surviving*
    # building in the cell, so a lone 1890s farmhouse paints a 250 m city block in the
    # middle of the orchards. Use the neighbourhood median instead (undeveloped cells
    # count as "not yet"): isolated houses drop out, suburbs get their typical year,
    # and edges are rounded instead of 250 m squares.
    fb_med = ndimage.median_filter(np.where(fbv, fb, 2100.0).astype(np.float32), size=7)
    dense = fb_med <= 2026
    out_sf_urban = np.where(dense, np.maximum(fb_med, np.where(fbv, fb, fb_med)), np.where(built_frac > 0.5, fb_filled, np.nan))
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
    filled = was_wet & ~water_now & ~salt & ~diked & ~is_pier
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
    event(is_pier & ~water_now, URBAN, pier_y)
    for m, y in excavated:
        event(m & water_now & ~was_wet, SHALLOW, y)
    for m, y in restored:
        event(m & water_now & (salt | diked), SHALLOW, y)
        event(m & (wc == 90) & (salt | diked), MARSH, y)

    # ---- agriculture (outside SF)
    flat = slope < 6
    not_sf = ~in_sf
    farmable = not_sf & flat & (elev < 250) & ~water_now & ~np.isin(N, [DEEP, SHALLOW, FLAT, MARSH, FOREST, ROCK, BEACH])
    farm_now = (wc == 40)
    early_urban = urban & (urban_y < 1860)
    ag_candidates = farmable & (farm_now | (urban & ~early_urban))
    scv = (lon > SANTA_CLARA_VALLEY[0]) & (lon < SANTA_CLARA_VALLEY[2]) & (lat > SANTA_CLARA_VALLEY[1]) & (lat < SANTA_CLARA_VALLEY[3])
    wine = (lon > WINE_VALLEYS[0]) & (lon < WINE_VALLEYS[2]) & (lat > WINE_VALLEYS[1]) & (lat < WINE_VALLEYS[3])
    event(ag_candidates, FARM, 1852.0 + 10 * h)
    event(ag_candidates & scv, ORCHARD, 1878.0 + 15 * h)
    event(ag_candidates & wine & farm_now & (h < 0.6), VINEYARD, 1870.0 + 40 * h)
    for r, poly in lc_rows:
        c = LANDCOVER_TABLE.get(str(r.cover).strip())
        ys = pd.to_numeric(r.get("year_start"), errors="coerce")
        if c is None or not np.isfinite(ys) or ys <= 1800:
            continue
        m = organic_mask(g, poly) & ~water_now & ~np.isin(N, [DEEP, SHALLOW, FLAT, MARSH])
        if c in (FOREST, OAK):
            m &= trees_near  # forests stand where trees are (today's canopy, slightly widened)
        if c in (FARM, ORCHARD, VINEYARD, PASTURE):
            m &= slope < 12
        # landscape-scale eras spread over ~6 years; city open spaces change on the date
        spread = 0.5 if c in (PARK, URBAN, RESERVOIR) else 6.0
        event(m, c, ys + spread * h)

    # ---- urbanisation, parks, planted woods
    event(urban, URBAN, urban_y)
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
    for r0 in range(0, rows, 384):
        r1 = min(rows, r0 + 384)
        C = np.stack([c[r0:r1] for c in ev_cover])
        Y = np.stack([y[r0:r1] for y in ev_year])
        Y = np.where(C == 255, np.nan, Y)
        order = np.argsort(np.where(np.isnan(Y), np.inf, Y), axis=0, kind="stable")
        C = np.take_along_axis(C, order, 0)
        Y = np.take_along_axis(Y, order, 0)
        n = np.zeros((r1 - r0, cols), np.int8)
        last = N[r0:r1].copy()
        for e in range(C.shape[0]):
            ce, ye = C[e], Y[e]
            ok = np.isfinite(ye) & (ce != last) & (n < 4)
            # agriculture can't come after urbanisation / fill
            ok &= ~(np.isin(ce, [FARM, ORCHARD, VINEYARD, PASTURE]) & np.isin(last, [URBAN, FILL, PARK]))
            # natural "fill" after the place is already urban is meaningless
            ok &= ~((ce == FILL) & (last == URBAN))
            # bare fill that is built on within 4 years: go straight to the city (saves a slot)
            if (ce == FILL).any():
                nxt_urban = np.zeros_like(ok)
                for e2 in range(e + 1, C.shape[0]):
                    nxt_urban |= (C[e2] == URBAN) & (Y[e2] - ye < 4)
                ok &= ~((ce == FILL) & nxt_urban)
            idx = n[ok]
            rr, cc = np.nonzero(ok)
            covers[idx + 1, rr + r0, cc] = ce[ok]
            years[idx, rr + r0, cc] = ye[ok]
            last = np.where(ok, ce, last)
            n = n + ok
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
            planted_sf = np.isnan(start) & np.isin(nat, [DUNES, SCRUB]) & (name == "detail")
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
                    # rows of trees: a 3x3 block per lattice cell (≈20 m spacing in the region grid)
                    oy, ox = np.meshgrid(np.linspace(-0.33, 0.33, 3), np.linspace(-0.33, 0.33, 3))
                    fy = ((vy[:, None] + oy.ravel()[None]) + max(r0 // sub, 0)) * sub
                    fx = ((vx[:, None] + ox.ravel()[None]) + max(c0 // sub, 0)) * sub
                    kinds.append(np.full(fy.size, D_ORCHARD)); ys.append(fy.ravel()); xs.append(fx.ravel())
                    sizes.append(rng.uniform(4, 6, fy.size)); starts.append(np.repeat(y_start, 9) + rng.uniform(0, 3, fy.size))
                    ends.append(np.repeat(y_end, 9))
                else:
                    # one farmstead per ~25 lattice cells, on a hash
                    pick = ((vy * 31 + vx * 17 + tx * 7 + ty * 13) % 25) == 0
                    if not pick.any():
                        continue
                    fy = (vy[pick] + max(r0 // sub, 0)) * sub + rng.uniform(-1, 1, pick.sum())
                    fx = (vx[pick] + max(c0 // sub, 0)) * sub + rng.uniform(-1, 1, pick.sum())
                    kinds.append(np.full(pick.sum(), D_FARMHOUSE)); ys.append(fy); xs.append(fx)
                    sizes.append(rng.uniform(7, 10, pick.sum())); starts.append(y_start[pick] + rng.uniform(0, 8, pick.sum()))
                    ends.append(y_end[pick])
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


def write_elevation_lookup(name, g, elev, step):
    """Coarse elevation grid for the viewer (placing landmarks, labels, cars)."""
    e = elev[::step, ::step]
    out = VIEWER_DATA / f"elevation-{name}.bin.gz"
    write_columnar(out, {"elev": np.clip(np.rint(e * 10), -32000, 32000).astype(np.int16).ravel()},
                   counts={"rows": e.shape[0], "cols": e.shape[1]},
                   meta={"X0": g["X0"], "Y0": g["Y0"], "res": g["res"] * step, "units": "decimetres, EPSG:3857 vertex lattice"})
    log(f"terrain {name}: elevation lookup {e.shape} -> {out}")


def main():
    meta = {}
    for name, zooms, step in (("region", [8, 9, 10, 11, 12, 13], 4), ("detail", [14], 2)):
        g, d = load_grid(name)
        covers, years, elev, slope, urban_y, park_y, wood_y = histories(name, g, d)
        deco = decorations(name, g, covers, years, elev, urban_y, park_y, wood_y)
        write_tiles(name, g, covers, years, elev, deco, zooms)
        write_elevation_lookup(name, g, elev, step)
        np.save(INTERIM / f"grid_{name}_landyear.npy", land_year_of(covers, years))
        meta[name] = {"z": g["z"], "tx0": g["tx0"], "ty0": g["ty0"], "tx1": g["tx1"], "ty1": g["ty1"], "zooms": zooms}
    (VIEWER_DATA / "terrain.json").write_text(json.dumps({"grids": meta, "covers": COVER_NAMES,
                                                          "deco": ["broadleaf", "conifer", "palm", "orchard", "farmhouse", "shrub"]}, indent=1))


if __name__ == "__main__":
    main()
