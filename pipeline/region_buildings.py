"""Stage: buildings of the five counties around San Francisco — Marin, Contra Costa,
Alameda, San Mateo, Santa Clara — as map tiles the viewer loads on demand.

Like San Francisco (sf_buildings.py / sf_export.py), but for ~2 M footprints:
  * footprints: Overture buildings (OSM + ML footprints), clipped to the counties
    (data/raw/overture/<release>/region5_building.parquet, download_region.py)
  * construction year: real records first — county / city assessor and parcel data
    normalised in data/interim/region_years.parquet (one row per parcel or building
    with year_built; see data/research/region_buildings.md). Spike years (round
    placeholders) and impossible values are cleaned as for SF. Buildings without a
    record take the median year of the nearest recorded buildings (<= 200 m,
    `estimated`), else HISDAC-US first-built-up year of their 250 m cell, else 1975.
  * nothing stands before its ground (terrain land-year grid); houses finished the
    same year in the same 80 m cell are ordered along the street (as SF tract rows)
  * height: Overture height > floors x 3.3 m + 1.5 > by footprint size (estimated)
  * facade / roof material by era, use and height (Bay Area suburbs: Victorians and
    Craftsman before 1920, stucco + tile 1920-45, ranch / mid-century 1945-75)

Output: viewer/public/data/region-buildings/13/<x>/<y>.bin.gz (BAYT, same columns as
sf-buildings.bin.gz) + index.json (tiles with counts and bounds).
"""
from __future__ import annotations

import json
import math
import zlib

import geopandas as gpd
import numpy as np
from pathlib import Path
import pandas as pd
from scipy.spatial import cKDTree

from building_binary import write_buildings
from common import INTERIM, MANUAL, RAW, TABLES, VIEWER_DATA, log
from download_overture import RELEASE
from sf_buildings import CONF, USE_CATEGORIES
from sf_export import (M_BRICK, M_CIVIC, M_CONTEMP, M_EARLY, M_GLASS, M_INDUSTRIAL, M_MASONRY, M_MIDCENTURY,
                       M_STUCCO, M_TOWER70, M_VICTORIAN, R_FLAT, R_SHINGLE, R_TILE)

UTM = "EPSG:32610"
COUNTIES = {"041": "Marin", "013": "Contra Costa", "001": "Alameda", "081": "San Mateo", "085": "Santa Clara"}
TILE_Z = 13
LOW_Z = 11
OUT = VIEWER_DATA / "region-buildings"
CURRENT_YEAR = 2026.5


def h01(key: str) -> float:
    return (zlib.crc32(key.encode()) % 100003) / 100003.0


def tile_of(lon, lat, z=TILE_Z):
    n = 2 ** z
    x = np.floor((lon + 180) / 360 * n).astype(int)
    lr = np.radians(lat)
    y = np.floor((1 - np.log(np.tan(lr) + 1 / np.cos(lr)) / math.pi) / 2 * n).astype(int)
    return x, y


def tile_origin(x, y, z=TILE_Z):
    n = 2 ** z
    lon = x / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lon, lat


def load_footprints():
    """Overture footprints of the five counties (download_region.py: clipped, with county),
    joined to the per-footprint candidate years (region5_footprint_years.parquet)."""
    g = gpd.read_parquet(RAW / "overture" / RELEASE / "region5_building.parquet")
    if g.crs is None:
        g = g.set_crs(4326)
    fy = pd.read_parquet(INTERIM / "region5_footprint_years.parquet")
    fy = fy.drop(columns=[c for c in ("county",) if c in fy])
    only = __import__("os").environ.get("REGION_COUNTY")  # e.g. REGION_COUNTY=Marin for a test run
    if only:
        g = g[g.county == only]
    g = g.merge(fy, on="id", how="left")
    g = g[~g.get("is_underground", pd.Series(False, index=g.index)).fillna(False).astype(bool)]
    g = g.explode(index_parts=False)
    g = g[g.geometry.geom_type == "Polygon"].reset_index(drop=True)
    area = g.to_crs(UTM).geometry.area.values
    g = g[area > 12].reset_index(drop=True)
    log(f"region: {len(g)} footprints ({g.county.value_counts().to_dict()})")
    return g


def clean_years(y, src):
    """Spike years (round placeholders) per source -> NaN-able flag, like SF."""
    y = np.where((y < 1800) | (y > CURRENT_YEAR), np.nan, y)
    spike = np.zeros(len(y), bool)
    for s in np.unique(src):
        m = (src == s) & np.isfinite(y)
        if m.sum() < 200:
            continue
        vals, counts = np.unique(y[m].astype(int), return_counts=True)
        cnt = dict(zip(vals, counts))
        for v in vals:
            if v % 5 or v >= 1950:
                continue
            nb = [cnt.get(v + d, 0) for d in (-3, -2, -1, 1, 2, 3)]
            if cnt[v] > 4 * max(np.median(nb), 1):
                spike |= m & (y.astype(float) == v)
    return y, spike


def assign_years(g):
    """Recorded years, best source first: historic-resource surveys (OHP directory, San
    José inventory: they also fix exempt buildings the roll misdates), the official
    assessor roll, public copies of it, then the vendor copy (FEMA / Lightbox). A
    round placeholder year (spike) is only an upper bound for the imputation."""
    year = np.full(len(g), np.nan)
    raw = np.zeros(len(g))
    raw_vendor = np.zeros(len(g), bool)  # placeholder from the vendor copy: not a bound
    conf = np.array(["estimated"] * len(g), dtype=object)
    src = np.array([""] * len(g), dtype=object)
    for col in ("historic", "public", "third_party", "commercial"):
        if f"year_{col}" not in g:
            continue
        y = pd.to_numeric(g[f"year_{col}"], errors="coerce").astype("float64").to_numpy(dtype=float, na_value=np.nan)
        sp = g[f"spike_{col}"].fillna(False).astype(bool).values
        y = np.where((y < 1769) | (y > CURRENT_YEAR), np.nan, y)
        take = np.isnan(year) & np.isfinite(y) & ~sp
        year[take] = y[take]
        conf[take] = "exact"
        src[take] = g[f"src_{col}"].astype(str).values[take]
        ph = (raw == 0) & np.isfinite(y)
        raw[ph] = y[ph]
        raw_vendor[ph] = col == "commercial"
    log(f"region: {np.isfinite(year).sum()} footprints with a recorded year "
        f"({pd.Series(src[np.isfinite(year)]).str.split(':').str[0].value_counts().head(8).to_dict()})")
    u = g.to_crs(UTM).geometry.representative_point()
    xy = np.column_stack([u.x.values, u.y.values])
    # researched dates of institutional / campus / landmark buildings (the rolls miss or
    # misdate exempt property: Stanford's Main Quad read 1983, Hoover Tower 1977)
    year, conf, src, end = known_dates(g, year, conf, src)
    # an upper bound from the placeholder year of the roll (a vendor's campus-wide
    # placeholder, e.g. UC Berkeley "1920", bounds nothing)
    upper_all = np.where((raw > 0) & ~raw_vendor, raw, np.inf)
    # campuses (universities, colleges, schools, hospitals, bases): estimated buildings
    # take the years of dated buildings of the same campus, not of the tract houses
    # across the street
    year = campus_impute(g, xy, year, conf, src, upper_all)
    # imputation from recorded neighbours (and the placeholder as an upper bound)
    have = np.isfinite(year)
    if have.any():
        tree = cKDTree(xy[have])
        hy = year[have]
        need = np.nonzero(~have)[0]
        d, idx = tree.query(xy[need], k=12, distance_upper_bound=200)
        vals = np.where(np.isfinite(d), hy[np.minimum(idx, len(hy) - 1)], np.nan)
        med = np.nanmedian(np.where(np.isfinite(vals), vals, np.nan), axis=1)
        year[need] = np.where(np.isfinite(med), np.minimum(med, upper_all[need]), np.nan)
    # HISDAC first built-up year of the 250 m cell (region grid), then a default
    miss = np.isnan(year)
    if miss.any():
        from terrain_grid import grid_def
        gR = grid_def("region")
        if "fbuy" in g:
            f = pd.to_numeric(g["fbuy"], errors="coerce").astype("float64").to_numpy(dtype=float, na_value=np.nan)
        else:
            fb = np.load(INTERIM / "grid_region_fbuy.npy").astype(float)
            rp = g.geometry.representative_point()
            X = np.radians(rp.x.values) * 6378137.0
            Y = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(rp.y.values) / 2))
            c = np.clip(((X - gR["X0"]) / gR["res"]).astype(int), 0, gR["cols"] - 1)
            r = np.clip(((gR["Y0"] - Y) / gR["res"]).astype(int), 0, gR["rows"] - 1)
            f = fb[r, c]
        ok = miss & (f >= 1810) & (f <= 2026)
        hh = np.array([h01(f"r{k}") for k in range(len(g))])
        year[ok] = f[ok] + hh[ok] * np.clip(2020 - f[ok], 0, 25)
        year[np.isnan(year)] = 1975 + 20 * hh[np.isnan(year)]
        # the placeholder still bounds these
        year[miss] = np.minimum(year[miss], upper_all[miss])
    year = site_bounds(g, year, conf, src)
    log(f"region: years exact {(conf == 'exact').sum()}, estimated {(conf != 'exact').sum()}")
    return year, raw, conf, end, src


def site_bounds(g, year, conf, src):
    """Military / industrial sites (data/manual/industrial_sites, rule all_pre in
    building_dates.csv): no footprint inside a refinery, plant, base or yard predates the
    site's documented founding (Lockheed Sunnyvale's roll placeholder 1900 -> 1956)."""
    sp, rp_ = MANUAL / "industrial_sites" / "sites.geojson", MANUAL / "industrial_sites" / "building_dates.csv"
    if not (sp.exists() and rp_.exists()):
        return year
    rules = pd.read_csv(rp_)
    rules = rules[rules.applies_to.astype(str).str.strip() == "all_pre"]
    sites = gpd.read_file(sp).to_crs(4326)
    pts = g.geometry.representative_point().set_crs(4326, allow_override=True)
    year = year.copy()
    n = 0
    for r in rules.itertuples():
        y0 = pd.to_numeric(r.year, errors="coerce")
        geom = sites[sites.site_id == r.site_id].geometry
        if not np.isfinite(y0) or not len(geom):
            continue
        poly = geom.union_all()
        idx = pts.sindex.query(poly, predicate="contains")
        bad = idx[(year[idx] < y0) & ~pd.Series(src[idx]).astype(str).str.startswith(("known:", "early:")).values]
        year[bad] = y0 + 0.5 + 2.0 * np.array([h01(f"sb{k}") for k in bad])
        conf[bad] = "estimated"
        n += len(bad)
    log(f"region: {n} footprints on military / industrial sites moved to the site's founding ({len(rules)} sites)")
    return year


def known_dates(g, year, conf, src):
    """data/tables/known_building_dates_region.csv and the military / industrial audit's
    data/manual/industrial_sites/known_dates_industrial.csv (researched, one source per row:
    refineries, plants, bases dated by the USGS topo editions that first draw them): every
    footprint containing a row's point takes its year (and end year)."""
    end = np.full(len(g), 9999.0)
    tabs = [pd.read_csv(p) for p in (TABLES / "known_building_dates_region.csv",
                                    MANUAL / "industrial_sites" / "known_dates_industrial.csv") if p.exists()]
    if not tabs:
        return year, conf, src, end
    k = pd.concat(tabs, ignore_index=True)
    k = k[k.get("county", pd.Series("", index=k.index)).fillna("").astype(str) != "San Francisco"]
    k = k[np.isfinite(pd.to_numeric(k.lat, errors="coerce")) & np.isfinite(pd.to_numeric(k.start_year, errors="coerce"))]
    pts = gpd.GeoDataFrame(k[["id", "start_year", "end_year"]].reset_index(drop=True),
                           geometry=gpd.points_from_xy(k.lon.astype(float), k.lat.astype(float)), crs=4326)
    j = gpd.sjoin(pts, g[["geometry"]].set_crs(4326, allow_override=True), predicate="within", how="inner")
    year = year.copy()
    for fi, sy, ey, kid in zip(j.index_right.values, j.start_year.values, j.end_year.values, j.id.values):
        year[fi] = float(sy)
        conf[fi] = "exact"
        src[fi] = f"known:{kid}"
        e = pd.to_numeric(ey, errors="coerce")
        if np.isfinite(e) and e < 9000:
            end[fi] = float(e)
    log(f"region: {len(j)} footprints dated from known_building_dates_region.csv ({len(k)} rows, "
        f"{len(k) - j.id.nunique()} without a footprint)")
    # adobes that still stand (early_region.csv rows marked SURVIVES): the footprint nearest
    # the documented point (within 25 m) takes the adobe's year
    ep = TABLES / "early_region.csv"
    if ep.exists():
        e = pd.read_csv(ep)
        e = e[e.shape_note.fillna("").astype(str).str.upper().str.startswith("SURVIVES")]
        if len(e):
            ep_u = gpd.GeoSeries(gpd.points_from_xy(e.lon.astype(float), e.lat.astype(float)), crs=4326).to_crs(UTM)
            gu = g.set_crs(4326, allow_override=True).to_crs(UTM)
            near = gpd.sjoin_nearest(gpd.GeoDataFrame({"y": e.start_year.astype(float).values, "id": e.id.values}, geometry=ep_u.values, crs=UTM),
                                     gu[["geometry"]], how="inner", max_distance=25)
            for fi, yy, kid in zip(near.index_right.values, near.y.values, near.id.values):
                year[fi] = yy
                conf[fi] = "exact"
                src[fi] = f"early:{kid}"
            log(f"region: {len(near)} surviving adobes dated (of {len(e)})")
    return year, conf, src, end


CAMPUS_CLASSES = ("university", "college", "school", "hospital", "military")


def campus_impute(g, xy, year, conf, src, upper):
    """Buildings on a campus (Overture land_use university / college / school / hospital /
    military outlines, smallest containing one). Exempt property has no real roll year:
    a year shared by >= 40 % of a campus's roll-dated buildings is a placeholder (the
    whole campus parcel's year), not the buildings'. Undated and placeholder-dated
    buildings take the median year of the 8 nearest dated buildings of the same campus
    (researched rows, surveys, roll years that aren't the placeholder) when it has >= 3."""
    p = RAW / "overture" / RELEASE / "region5_land_use.parquet"
    if not p.exists():
        return year
    d = pd.read_parquet(p)
    d = d[d["class"].isin(CAMPUS_CLASSES)].reset_index(drop=True)
    lu = gpd.GeoDataFrame(d[["class", "name"]], geometry=gpd.GeoSeries.from_wkb(d.geometry.values), crs=4326)
    lu = lu[lu.geom_type.isin(["Polygon", "MultiPolygon"])].to_crs(UTM)
    lu = lu.assign(area=lu.geometry.area.values)
    lu = lu[lu.area > 5000].reset_index(drop=True)
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(xy[:, 0], xy[:, 1]), crs=UTM)
    j = gpd.sjoin(pts, lu[["area", "geometry"]], predicate="within", how="inner")
    j = j.sort_values("area").loc[lambda t: ~t.index.duplicated(keep="first")]
    campus = np.full(len(g), -1)
    campus[j.index.values] = j.index_right.values
    year = year.copy()
    srcs = pd.Series(src).astype(str)
    researched = (srcs.str.startswith("known:") | srcs.str.startswith("ca_ohp") | srcs.str.startswith("san_jose_hri")).values
    have = np.isfinite(year) & (conf == "exact")
    n_done, n_ph = 0, 0
    for cid in np.unique(campus[campus >= 0]):
        members = np.nonzero(campus == cid)[0]
        roll = members[have[members] & ~researched[members]]
        # (not schools: a school is often built in one go)
        if len(roll) >= 20 and lu["class"].values[cid] != "school":
            vals, cnt = np.unique(np.floor(year[roll]), return_counts=True)
            if cnt.max() >= 0.4 * len(roll):
                ph = roll[np.floor(year[roll]) == vals[np.argmax(cnt)]]
                have[ph] = False
                conf[ph] = "estimated"
                n_ph += len(ph)
        donors = members[have[members]]
        need = members[~have[members]]
        if len(donors) < 3 or not len(need):
            continue
        t = cKDTree(xy[donors])
        k = min(8, len(donors))
        _, idx = t.query(xy[need], k=k)
        idx = idx.reshape(len(need), k)
        med = np.median(year[donors][idx], axis=1)
        year[need] = np.minimum(med, upper[need])
        n_done += len(need)
    log(f"region: {n_done} campus buildings take their campus's years ({n_ph} had a campus-wide placeholder; "
        f"{int((campus >= 0).sum())} footprints on {len(np.unique(campus[campus >= 0]))} campuses)")
    return year


def land_check(g, year):
    p = INTERIM / "grid_region_landyear.npy"
    if not p.exists():
        return year
    from terrain_grid import grid_def
    gR = grid_def("region")
    ly = np.load(p)
    rp = g.geometry.representative_point()
    X = np.radians(rp.x.values) * 6378137.0
    Y = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(rp.y.values) / 2))
    c = np.clip(np.rint((X - gR["X0"]) / gR["res"]).astype(int), 0, gR["cols"] - 1)
    r = np.clip(np.rint((gR["Y0"] - Y) / gR["res"]).astype(int), 0, gR["rows"] - 1)
    land = ly[r, c]
    early = np.isfinite(land) & (year < land - 0.5)
    year = np.where(early, land + 0.5, year)
    log(f"region: land check moved {early.sum()} buildings onto ground that existed")
    return year


def row_timing(g, year):
    """Sub-year timing: same-year buildings in an 80 m cell go up in order along their
    principal axis (tract builders worked down the street); others get a hash."""
    u = g.to_crs(UTM).geometry.representative_point()
    x, y = u.x.values, u.y.values
    yi = np.floor(year)
    jit = np.array([h01(f"j{k}") for k in range(len(g))])
    cell = (np.floor(x / 80).astype(np.int64) * 100003 + np.floor(y / 80).astype(np.int64))
    df = pd.DataFrame({"c": cell, "y": yi, "i": np.arange(len(g))})
    for (_, _), grp in df.groupby(["c", "y"]):
        if len(grp) < 3:
            continue
        idx = grp.i.values
        P = np.column_stack([x[idx], y[idx]])
        P = P - P.mean(axis=0)
        _, _, vt = np.linalg.svd(P, full_matrices=False)
        order = np.argsort(np.argsort(P @ vt[0]))
        span = min(0.9, 0.12 * len(idx))
        jit[idx] = (0.5 * (0.9 - span) + span * order / max(len(idx) - 1, 1)) / 0.9
    return yi + 0.9 * jit


def lidar_parts_region(g, start=None):
    """Replace footprints by their LiDAR parts (data/interim/<job>_lidar_parts.parquet of
    the region jobs: Oakland, Berkeley, San José, … downtowns; 2020-21 USGS 3DEP surveys).
    Returns the new frame, the source row of each new row (None if nothing changed), the
    part heights (NaN elsewhere) and each row's part group ("" elsewhere)."""
    import glob
    files = [f for f in sorted(glob.glob(str(INTERIM / "*_lidar_parts.parquet")))
             if not Path(f).name.startswith("sf")]
    hfiles = [f for f in sorted(glob.glob(str(INTERIM / "*_lidar_heights.parquet")))
              if not Path(f).name.startswith("sf")]
    # single-level footprints: the measured whole-footprint height (roof median minus the
    # footprint's ground) where the building stood at the survey (Overture often has none)
    single_h = np.full(len(g), np.nan)
    if hfiles and "id" in g:
        hh = pd.concat([pd.read_parquet(f, columns=["key", "status", "lidar_height_m", "lidar_year"]) for f in hfiles])
        hh = hh[(hh.status == "single") & (pd.to_numeric(hh.lidar_height_m, errors="coerce") > 2.0)]
        hmap = dict(zip(hh.key.astype(str), hh.lidar_height_m.astype(float)))
        ymap = dict(zip(hh.key.astype(str), hh.lidar_year.astype(float)))
        ids = g["id"].astype(str).values
        single_h = np.array([hmap.get(k, np.nan) for k in ids])
        if start is not None:
            sy = np.array([ymap.get(k, np.nan) for k in ids])
            single_h = np.where(np.asarray(start, float) <= sy + 0.5, single_h, np.nan)
        log(f"region: {int(np.isfinite(single_h).sum())} footprints take their measured LiDAR height")
    none = (g, None, single_h, np.full(len(g), "", dtype=object))
    if not files or "id" not in g:
        return none
    lp = pd.concat([gpd.read_parquet(f).to_crs(4326) for f in files], ignore_index=True)
    lp = lp[lp.prefer_lidar.astype(bool) & (lp.height_m > 0.5)]
    if not len(lp):
        return none
    pos: dict = {}
    for i, k in enumerate(g["id"].astype(str).values):
        pos.setdefault(k, []).append(i)
    drop, src_rows, geoms, hs, grp = set(), [], [], [], []
    for key, parts in lp.groupby("key"):
        idx = [i for k in str(parts.replaces.iloc[0]).split("|") for i in pos.get(k, [])]
        if not idx:
            continue
        donor = max(idx, key=lambda i: g.geometry.values[i].area)
        for r in parts.itertuples():
            if r.geometry is None or r.geometry.is_empty:
                continue
            for part in getattr(r.geometry, "geoms", [r.geometry]):
                if part.geom_type == "Polygon" and part.area > 0:
                    src_rows.append(donor); geoms.append(part); hs.append(float(r.height_m)); grp.append(str(key))
        drop.update(idx)
    if not src_rows:
        return none
    keep = np.array([i for i in range(len(g)) if i not in drop], dtype=np.int64)
    src_rows = np.asarray(src_rows, dtype=np.int64)
    rows = np.concatenate([keep, src_rows])
    new = g.iloc[rows].copy()
    new["geometry"] = list(g.geometry.values[keep]) + geoms
    new = gpd.GeoDataFrame(new.reset_index(drop=True), geometry="geometry", crs=g.crs)
    lidar_h = np.concatenate([single_h[keep], np.asarray(hs)])
    lgroup = np.concatenate([np.full(len(keep), "", dtype=object), np.asarray(grp, dtype=object)])
    log(f"region: LiDAR stepped massing: {len(drop)} footprints -> {len(src_rows)} parts ({len(files)} areas)")
    return new, rows, lidar_h, lgroup


def heights(g):
    area = g.to_crs(UTM).geometry.area.values
    def num(col):
        if col not in g:
            return np.full(len(g), np.nan)
        return pd.to_numeric(g[col], errors="coerce").astype("float64").to_numpy(dtype=float, na_value=np.nan)
    h = num("height")
    fl = num("num_floors")
    lidar = num("smc_lidar_height_m")
    h = np.where(np.isfinite(lidar) & (lidar > 2), lidar, h)
    out = np.where(np.isfinite(h) & (h > 2), h, np.where(np.isfinite(fl) & (fl > 0), fl * 3.3 + 1.5, np.nan))
    default = np.where(area < 60, 3.2, np.where(area < 300, 5.5, np.where(area < 1500, 7.0, 9.0)))
    stories = np.where(np.isfinite(fl), fl, np.round(np.where(np.isfinite(out), out, default) / 3.3))
    return np.where(np.isfinite(out), out, default), stories, area


def materials(year, H, area, use):
    mat = np.full(len(year), M_CONTEMP, np.uint8)
    roof = np.full(len(year), R_FLAT, np.uint8)
    resid = (use <= 2) & (area < 600)
    big = area > 2500
    def put(m, a, r):
        mat[m] = a
        roof[m] = r
    put(year >= 1995, M_CONTEMP, R_FLAT)
    put((year >= 1945) & (year < 1995), M_MIDCENTURY, R_SHINGLE)
    put((year >= 1920) & (year < 1945), M_STUCCO, R_TILE)
    put(year < 1920, M_VICTORIAN, R_SHINGLE)
    put((year < 1930) & ~resid & ~big & (H > 8), M_BRICK, R_FLAT)
    put(big & (year < 1990), M_INDUSTRIAL, R_FLAT)
    put((year < 1940) & (H > 20), M_MASONRY, R_FLAT)
    put((year >= 1955) & (year < 1986) & (H >= 40), M_TOWER70, R_FLAT)
    put((year >= 1986) & (H >= 40), M_GLASS, R_FLAT)
    put((use == 6) & (H > 10) & (year < 1960), M_CIVIC, R_FLAT)
    roof[(mat == M_MIDCENTURY) & (area > 400)] = R_FLAT
    return mat, roof


def use_codes(g, area):
    cls = g.get("class").astype(str).str.lower().values if "class" in g else np.array([""] * len(g))
    sub = g.get("subtype").astype(str).str.lower().values if "subtype" in g else np.array([""] * len(g))
    use = np.zeros(len(g), np.uint8)
    use[np.isin(cls, ["house", "detached", "semidetached_house", "bungalow", "residential"]) | (sub == "residential")] = 1
    use[np.isin(cls, ["apartments", "dormitory", "terrace"])] = 2
    use[np.isin(cls, ["commercial", "retail", "supermarket", "kiosk"]) | (sub == "commercial")] = 3
    use[np.isin(cls, ["office"])] = 4
    use[np.isin(cls, ["industrial", "warehouse", "factory", "manufacture"]) | (sub == "industrial")] = 5
    use[np.isin(cls, ["school", "university", "hospital", "church", "civic", "government", "public"]) | np.isin(sub, ["civic", "education", "medical", "religious"])] = 6
    use[(use == 0) & (area < 400)] = 1
    return use


def main():
    from roads import Ground
    g = load_footprints()
    year, raw, conf, end, src = assign_years(g)
    # researched dates stand even where the fill under them is dated later (the fill
    # zones are coarse: the Richmond shipyard box pushed the 1931 Ford plant to 1941)
    known = pd.Series(src).astype(str).str.startswith(("known:", "early:")).values
    year = np.where(known, year, land_check(g, year))
    start = row_timing(g, year)
    # stepped massing from airborne LiDAR in the downtowns (lidar_parts.py region jobs):
    # footprints with several roof levels become parts that keep their building's years
    g, rows, lidar_h, lgroup = lidar_parts_region(g, start)
    if rows is not None:
        year, raw, conf, end, start, src = (np.asarray(a)[rows] for a in (year, raw, conf, end, start, src))
    H, stories, area = heights(g)
    H = np.where(np.isfinite(lidar_h), lidar_h, H)
    stories = np.where(np.isfinite(lidar_h), np.maximum(1, np.round(lidar_h / 3.6)), stories)
    use = use_codes(g, area)
    mat, roof = materials(start, H, area, use)
    if rows is not None:
        # one building, one material and use: its largest part's
        has = lgroup != ""
        if has.any():
            df = pd.DataFrame({"g": lgroup[has], "a": area[has], "i": np.nonzero(has)[0]})
            big = df.sort_values("a").groupby("g").i.last()
            pick = big.reindex(lgroup[has]).values
            for arr in (mat, roof, use):
                arr[has] = arr[pick]
    # foundation at the lowest corner, roof at mean ground + height
    ground = Ground()
    ext = [np.asarray(gm.exterior.coords)[:, :2] for gm in g.geometry.values]
    counts = np.array([len(e) for e in ext])
    allc = np.concatenate(ext)
    gz = ground(allc[:, 0], allc[:, 1])
    splits = np.cumsum(counts)[:-1]
    gmin = np.array([a.min() for a in np.split(gz, splits)])
    gmean = np.array([a.mean() for a in np.split(gz, splits)])
    # LiDAR part heights are above their footprint's ground: all parts of one footprint
    # stand on the group's (area-weighted) mean ground so the roofs stay where measured
    if (lgroup != "").any():
        has = lgroup != ""
        t = pd.DataFrame({"g": lgroup[has], "m": gmean[has] * area[has], "a": area[has]}).groupby("g").sum()
        gmean = gmean.copy()
        gmean[has] = (t.m / t.a).reindex(lgroup[has]).values
    g = g.assign(start_year=start, end_year=end, height=H + (gmean - gmin) + 1.0, base=gmin - 1.0,
                 year_confidence=conf, use=use, raw_year=raw, stories=stories, mat=mat, roof=roof)
    g["fid_key"] = g["id"].astype(str) if "id" in g else g.index.astype(str)
    cols = ["start_year", "end_year", "height", "base", "year_confidence", "use", "raw_year", "stories", "mat",
            "roof", "fid_key", "geometry"]
    g = g[cols]
    # vanished buildings: traced (Sanborn) + generated where the neighbourhood says so
    from region_predecessors import region_predecessors
    pred = region_predecessors(g)
    if len(pred):
        pred = pred.explode(index_parts=False)
        pred = pred[pred.geometry.geom_type == "Polygon"].reset_index(drop=True)
        parea = pred.to_crs(UTM).geometry.area.values
        pmat, proof = materials(pred.start_year.values.astype(float), pred.height.values.astype(float), parea,
                                pred.use.values.astype(int))
        dm = pred.get("material", pd.Series("", index=pred.index)).fillna("").astype(str).values
        pmat = np.where(dm == "brick", M_BRICK, np.where(dm == "stone", M_CIVIC, np.where(dm == "wharf", M_EARLY, pmat)))
        # adobe, tule and canvas of the early settlements: the early-town palette
        pmat = np.where(np.isin(dm, ["adobe", "tule", "canvas tent"]), M_EARLY, pmat)
        pext = [np.asarray(gm.exterior.coords)[:, :2] for gm in pred.geometry.values]
        pc = np.array([len(e) for e in pext])
        pz = ground(*np.concatenate(pext).T)
        psplit = np.cumsum(pc)[:-1]
        pmin = np.array([a.min() for a in np.split(pz, psplit)])
        pmean = np.array([a.mean() for a in np.split(pz, psplit)])
        pred = pred.assign(height=pred.height.values + (pmean - pmin) + 1.0, base=pmin - 1.0, raw_year=0,
                           mat=pmat.astype(np.uint8), roof=proof, fid_key=pred.mapblklot.astype(str),
                           stories=pred.stories.fillna(2).values)
        pc_ = pred[cols].set_crs(4326, allow_override=True)
        g = gpd.GeoDataFrame(pd.concat([g.set_crs(4326, allow_override=True), pc_], ignore_index=True), geometry="geometry", crs=4326)
        log(f"region: + {len(pred)} vanished buildings ({pred.year_confidence.value_counts().to_dict()})")
    g["geometry"] = g.geometry.to_crs(UTM).simplify(0.3, preserve_topology=True).to_crs(4326)
    g = g[~g.geometry.is_empty & g.geometry.is_valid & (g.geometry.geom_type == "Polygon")]
    rp = g.geometry.representative_point()
    tx, ty = tile_of(rp.x.values, rp.y.values)
    g = g.assign(tx=tx, ty=ty)
    # building points for the terrain stage (city ground follows the buildings; suburban
    # vs urban ground from how much of it buildings cover)
    pd.DataFrame({"lon": rp.x.values, "lat": rp.y.values, "start_year": g.start_year.values,
                  "end_year": g.end_year.values,
                  "area_m2": g.to_crs(UTM).geometry.area.values}).to_parquet(INTERIM / "region_building_points.parquet")
    OUT.mkdir(parents=True, exist_ok=True)
    index = []
    for (x, y), t in g.groupby(["tx", "ty"]):
        origin = tile_origin(x, y)
        path = OUT / str(TILE_Z) / str(x) / f"{y}.bin.gz"
        path.parent.mkdir(parents=True, exist_ok=True)
        b = t.total_bounds
        write_buildings(path, t, origin, CONF, USE_CATEGORIES)
        index.append({"x": int(x), "y": int(y), "n": int(len(t)), "bbox": [round(float(v), 5) for v in b]})
    # zoomed out (city scale): only buildings big enough to see there — footprint over
    # 600 m² or taller than 12 m — in z11 tiles, outlines simplified to 1.5 m
    au = g.to_crs(UTM)
    big = (au.geometry.area.values > 600) | (g.height.values - 1.0 > 12)
    low = g[big].copy()
    low["geometry"] = au.geometry[big].simplify(1.5, preserve_topology=True).to_crs(4326).values
    low = low[~low.geometry.is_empty & low.geometry.is_valid & (low.geometry.geom_type == "Polygon")]
    lp = low.geometry.representative_point()
    lx, ly = tile_of(lp.x.values, lp.y.values, LOW_Z)
    low = low.assign(tx=lx, ty=ly)
    low_index = []
    for (x, y), t in low.groupby(["tx", "ty"]):
        path = OUT / str(LOW_Z) / str(x) / f"{y}.bin.gz"
        path.parent.mkdir(parents=True, exist_ok=True)
        write_buildings(path, t, tile_origin(x, y, LOW_Z), CONF, USE_CATEGORIES)
        low_index.append({"x": int(x), "y": int(y), "n": int(len(t))})
    log(f"region: wrote {len(low_index)} low-zoom tiles with {len(low)} large buildings")
    (OUT / "index.json").write_text(json.dumps({"z": TILE_Z, "tiles": index, "low": {"z": LOW_Z, "tiles": low_index}},
                                               separators=(",", ":")))
    log(f"region: wrote {len(index)} tiles, {len(g)} buildings -> {OUT}")


if __name__ == "__main__":
    main()
