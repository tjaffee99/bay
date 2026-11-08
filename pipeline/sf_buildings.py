"""Stage: clean years, impute missing ones, pick heights, merge Overture/OSM
geometry -> final San Francisco building table.

Year rules (see CLAUDE.md "Year cleaning"):
  * raw year = most common non-zero assessor year on the map parcel (ties -> earliest)
  * missing        : no year, or < 1835, or > CURRENT_YEAR             -> impute
  * spike          : a round year whose count dwarfs its neighbours
                     (e.g. 1900: 14.6k vs ~400/yr nearby) = placeholder -> impute (<= raw)
  * burned         : raw < 1906 inside the 1906 burned area (outside the
                     unburned islands) — those buildings burned           -> impute (>= 1906.5)
  * land_not_yet   : raw earlier than the land under it existed           -> impute (>= land year)
  imputation = median year of the nearest good-year buildings (k<=12, <=150 m),
  respecting the bound above; deterministic hash jitter only as a last resort.
  Imputed rows get year_confidence = estimated.

Heights: 2010 LiDAR median height (DataSF footprints) for buildings that existed
in 2010; stories x 3.3 m + 1.5 m for newer ones or when LiDAR is missing; then
OSM/Overture height; then 7 m.

Geometry precedence (most real first):
  1. OSM hand-modelled building parts (via Overture building_part) — stepped towers, domes' drums, wings
  2. DataSF 2016 footprints
  3. Overture/OSM footprints for buildings missing from the 2016 snapshot (newer construction)

Outputs:
  data/interim/sf_buildings.parquet  (+ .fgb for QGIS)
  data/interim/reports/sf_years.png, sf_buildings_summary.json
"""
from __future__ import annotations

import json
import zlib
from collections import Counter

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from scipy.spatial import cKDTree
from shapely.geometry import shape

from common import CURRENT_YEAR, INTERIM, MANUAL, RAW, STILL_EXISTS, TABLES, log
from download_overture import RELEASE

UTM = "EPSG:32610"
REPORTS = INTERIM / "reports"
OUT = INTERIM / "sf_buildings.parquet"

USE_CATEGORIES = ["unknown", "single-family home", "residential", "commercial", "office",
                  "industrial", "government / civic", "other"]
USE_MAP = {"SRES": 1, "MRES": 2, "COMR": 3, "COMM": 3, "COMH": 3, "COMO": 4, "IND": 5, "GOVT": 6, "MISC": 7}
CONF = {"exact": 0, "estimated": 1, "procedural": 2, "reconstructed": 3}


def stable_hash01(key: str) -> float:
    return (zlib.crc32(key.encode()) % 100003) / 100003.0


def pick_year(years) -> int:
    ys = [int(y) for y in years]
    if not ys:
        return 0
    c = Counter(ys).most_common()
    top = c[0][1]
    return min(y for y, n in c if n == top)


def spike_years(raw: pd.Series) -> set[int]:
    h = Counter(raw[raw > 0].astype(int))
    spikes = set()
    for y, n in h.items():
        if y % 5 != 0 or y > 1950:
            continue
        neigh = [h.get(y + d, 0) for d in (-4, -3, -2, -1, 1, 2, 3, 4) if (y + d) % 5 != 0]
        base = max(np.median(neigh), 1.0)
        if n >= 25 and n > 4 * base:
            spikes.add(y)
    return spikes


def load_polygons(path) -> gpd.GeoDataFrame | None:
    if not path.exists():
        return None
    return gpd.read_file(path).to_crs(UTM)


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    df = gpd.read_parquet(INTERIM / "sf_joined.parquet").to_crs(UTM)
    df["source"] = "datasf_footprints_2016"
    df["raw_year"] = df.years.apply(pick_year)
    df["n_distinct_years"] = df.years.apply(lambda v: len(set(v)))

    # ---------------------------------------------------------------- Overture gap fill
    df = pd.concat([df, overture_extras(df)], ignore_index=True)
    df = gpd.GeoDataFrame(df, geometry="geometry", crs=UTM)

    raw = df.raw_year.fillna(0).astype(int)
    spikes = spike_years(raw)
    log(f"years: placeholder spike years detected: {sorted(spikes)}")

    reason = np.array(["ok"] * len(df), dtype=object)
    reason[(raw <= 0) | (raw < 1835) | (raw > CURRENT_YEAR)] = "missing"
    reason[raw.isin(spikes).values & (reason == "ok")] = "spike"
    lower = np.full(len(df), -np.inf)
    upper = np.full(len(df), np.inf)
    upper[reason == "spike"] = raw[reason == "spike"]

    cent = df.geometry.representative_point()

    fire = load_polygons(INTERIM / "fire_1906.geojson")
    in_fire = np.zeros(len(df), bool)
    if fire is not None:
        in_fire = cent.within(shapely.union_all(fire.geometry.values)).values
        burned = in_fire & (raw.values > 0) & (raw.values < 1906) & (reason != "missing")
        reason[burned] = "burned"
        lower[in_fire] = np.maximum(lower[in_fire], 1906.5)
        upper[burned] = np.inf
        log(f"years: {in_fire.sum()} buildings in 1906 burned area; {burned.sum()} with impossible pre-1906 years")
    else:
        log("years: WARNING no fire_1906 polygon yet; burned-area rule skipped")

    land = load_polygons(MANUAL / "land_not_before.geojson")
    if land is not None:
        for _, r in land.iterrows():
            inside = cent.within(r.geometry).values
            bad = inside & (raw.values > 0) & (raw.values < r.year) & (reason == "ok")
            reason[bad] = "land_not_yet"
            lower[inside] = np.maximum(lower[inside], r.year)
            log(f"years: {inside.sum()} buildings on {r['name']} (land from {r.year}); {bad.sum()} predate it")

    # 19th-century cemeteries (landcover_history "cem_*" rows): nothing was built there
    # until the graves were moved, so earlier years there are placeholders
    for cpoly, cend, cname in cemeteries(UTM):
        inside = cent.within(cpoly.buffer(-15)).values
        bad = inside & (raw.values > 0) & (raw.values < cend) & (reason == "ok")
        reason[bad] = "cemetery"
        lower[inside] = np.maximum(lower[inside], cend + 0.5)
        upper[inside & (reason == "spike")] = np.inf
        log(f"years: {inside.sum()} buildings on the former {cname} (cleared {cend:.0f}); {bad.sum()} predate it")

    # urban renewal / freeway clearances: a building there whose year we have to
    # impute can't predate the clearance (the old fabric was demolished first);
    # dated survivors (rehabilitated Victorians, Westside Courts, ...) keep their years
    lower_redev = np.full(len(df), -np.inf)
    for area_poly, cs, ce, _fabric, _aid in redevelopment_areas():
        inside = cent.within(area_poly).values
        lower_redev[inside] = np.where(np.isfinite(lower_redev[inside]), np.minimum(lower_redev[inside], cs + 2), cs + 2)
    # an assessor placeholder (spike) year doesn't cap a big building inside a clearance:
    # the Victorians there were small; a 1,000 m2 store is post-clearance
    big_spike = np.isfinite(lower_redev) & (reason == "spike") & (df.geometry.area.values > 600)
    upper[big_spike] = np.inf
    log(f"years: {np.isfinite(lower_redev).sum()} buildings inside urban-renewal / freeway clearances "
        f"({big_spike.sum()} large ones with placeholder years treated as post-clearance)")

    # tall buildings: imputing from (small) neighbours drops towers into the Victorian
    # era. Without a usable year, a 50 m+ building is post-war and a 35 m+ one at least
    # interwar (the pre-war towers — Russ, Shell, PT&T — have real assessor years);
    # a tall footprint missing from the 2016 DataSF snapshot is a post-2014 tower.
    hgt = np.fmax(df.hgt_median_m.astype(float).values, pd.to_numeric(df.get("overture_height"), errors="coerce").values)
    imp_tall = reason != "ok"
    lower_redev[imp_tall & (hgt >= 35)] = np.fmax(lower_redev[imp_tall & (hgt >= 35)], 1920)
    lower_redev[imp_tall & (hgt >= 50)] = np.fmax(lower_redev[imp_tall & (hgt >= 50)], 1950)
    new_tower = imp_tall & (hgt >= 30) & (df.source != "datasf_footprints_2016").values
    lower_redev[new_tower] = np.fmax(lower_redev[new_tower], 2014)
    upper[imp_tall & (hgt >= 35) & (reason == "spike")] = np.inf
    log(f"years: height floors for {int((imp_tall & (hgt >= 35)).sum())} tall buildings without usable years "
        f"({int(new_tower.sum())} post-2016-snapshot towers)")

    # ---------------------------------------------------------------- other evidence
    # LiDAR (2010) saw a building here -> it existed by 2010; every DataSF footprint existed by 2016
    lidar = df.hgt_median_m.astype(float).values
    upper[np.isfinite(lidar) & (lidar >= 3.0)] = np.minimum(upper[np.isfinite(lidar) & (lidar >= 3.0)], 2010)
    is_2016 = (df.source == "datasf_footprints_2016").values
    upper[is_2016] = np.minimum(upper[is_2016], 2016)

    year = raw.values.astype(float)
    conf = np.where(reason == "ok", "exact", "estimated").astype(object)
    src_year = np.where(reason == "ok", "assessor", "").astype(object)

    # DBI new-construction permits (completed) for parcels without a usable assessor year
    py = permit_years()
    if py is not None:
        pyr = df.mapblklot.map(py).values.astype(float)
        use = (reason != "ok") & np.isfinite(pyr) & (pyr >= lower) & (pyr <= np.maximum(upper, pyr))
        use &= pyr <= np.where(np.isfinite(upper), upper + 1, 9999)
        year[use] = pyr[use]
        reason[use] = "ok_permit"
        conf[use] = "exact"
        src_year[use] = "dbi_permit"
        log(f"years: {use.sum()} buildings dated from completed new-construction permits")

    # researched dates (federal / exempt land, public buildings) — point in footprint
    known_end = np.full(len(df), np.nan)
    kd = known_dates()
    if kd is not None:
        hit = gpd.sjoin(kd, gpd.GeoDataFrame(geometry=df.geometry, crs=UTM), predicate="within", how="inner")
        for _, r in hit.iterrows():
            i = int(r.index_right)
            year[i] = r.start_year
            reason[i] = "ok_research"
            conf[i] = "exact"
            src_year[i] = "research"
            if np.isfinite(r.end_year) and r.end_year < 9000:
                known_end[i] = r.end_year
        log(f"years: {hit.index_right.nunique()} buildings dated from data/tables/known_building_dates.csv")

    # ---------------------------------------------------------------- imputation
    good = np.isin(reason, ["ok", "ok_permit", "ok_research"])
    xy = np.column_stack([cent.x.values, cent.y.values])
    tree = cKDTree(xy[good])
    good_years = year[good].astype(float)
    need = np.where(~good)[0]
    dist, idx = tree.query(xy[need], k=12, distance_upper_bound=150)
    victorian = np.sort(good_years[good_years < 1906])
    fbuy = fbuy_years(cent)
    fallback = 0
    parcel_year: dict = {}
    for j, i in enumerate(need):
        ok = np.isfinite(dist[j])
        cands = good_years[idx[j][ok]]
        lo_i = max(lower[i], lower_redev[i])
        cands = cands[(cands >= lo_i) & (cands <= upper[i])]
        key = df.mapblklot.iloc[i]
        if isinstance(key, str) and key in parcel_year:
            # all footprints of one parcel share the parcel's imputed year
            year[i] = parcel_year[key]
        elif len(cands):
            year[i] = float(np.median(cands))
        elif np.isfinite(fbuy[i]) and lo_i <= fbuy[i] <= upper[i]:
            # HISDAC-US first built-up year of the 250 m cell
            year[i] = fbuy[i]
            src_year[i] = "hisdac_fbuy"
        else:
            fallback += 1
            h = stable_hash01(str(df.sf16_bldgid.iloc[i] or i))
            if reason[i] == "spike":
                # draw from the empirical distribution of *exact* years in the
                # 25 years up to the placeholder (e.g. 1900 -> real Victorian-era shape)
                lo = raw.values[i] - 25
                pool = victorian[(victorian >= lo) & (victorian <= raw.values[i])]
                year[i] = np.quantile(pool, h) if len(pool) > 20 else raw.values[i] - 12 * h
            elif reason[i] == "burned" or lower[i] == 1906.5:
                year[i] = 1906.5 + 7 * h                  # post-fire rebuild 1906-1913
            elif np.isfinite(lo_i):
                year[i] = lo_i + 3 * h
            else:
                year[i] = 1925 + 20 * h
        year[i] = min(max(year[i], lo_i), upper[i], CURRENT_YEAR)
        if isinstance(key, str) and key not in parcel_year:
            parcel_year[key] = year[i]
        if not src_year[i]:
            src_year[i] = "neighbours"
    log(f"years: imputed {len(need)} ({fallback} without usable neighbours or HISDAC)")

    # Sub-year timing. Houses finished the same year on the same block went up as a row
    # (tract builders worked along the street): order them along the block's long axis
    # so the row fills from one end instead of popping up at random; lone buildings get
    # a hash.
    jit = np.array([stable_hash01(f"j{k}") for k in range(len(df))])
    blk = df.mapblklot.astype(str).str[:-3].values
    yi = np.floor(year)
    cx = df.geometry.centroid.x.values
    cy = df.geometry.centroid.y.values
    grp = pd.DataFrame({"b": blk, "y": yi, "i": np.arange(len(df))})
    grp = grp[(grp.b != "") & (grp.b != "na")]
    rows_ordered = 0
    for (_, _), g in grp.groupby(["b", "y"]):
        if len(g) < 3:
            continue
        idx = g.i.values
        P = np.column_stack([cx[idx], cy[idx]])
        P = P - P.mean(axis=0)
        _, _, vt = np.linalg.svd(P, full_matrices=False)
        t = P @ vt[0]
        order = np.argsort(np.argsort(t))
        span = min(0.9, 0.12 * len(idx))
        start = 0.9 * stable_hash01(f"b{g.b.iloc[0]}{g.y.iloc[0]}") * (0.9 - span)
        jit[idx] = (start + span * order / max(len(idx) - 1, 1)) / 0.9
        rows_ordered += len(idx)
    log(f"years: {rows_ordered} buildings timed as rows along their block")
    df["start_year"] = yi + 0.9 * jit
    df.loc[df.start_year < lower, "start_year"] = lower[df.start_year < lower]
    df["end_year"] = np.where(np.isfinite(known_end), known_end, float(STILL_EXISTS))
    df["year_confidence"] = conf
    df["year_reason"] = reason
    df["year_source"] = src_year
    df["in_fire_zone"] = in_fire

    # ---------------------------------------------------------------- heights
    ovh = overture_heights(df)
    df["overture_height"] = np.where(df.get("overture_height").notna(), df.get("overture_height"), ovh) if "overture_height" in df else ovh
    df["height"] = heights(df)
    df["base"] = 0.0
    df["use"] = df.use_code.map(USE_MAP).fillna(0).astype(int)
    df["kind"] = "building"

    # ---------------------------------------------------------------- OSM 3D parts
    df = apply_parts(df)

    validate(df)
    report(df, raw, spikes)
    df = df.to_crs(4326)
    keep = ["sf16_bldgid", "mapblklot", "address", "raw_year", "start_year", "end_year", "year_confidence",
            "year_reason", "year_source", "height", "base", "stories", "units", "use", "use_definition", "kind", "source",
            "in_fire_zone", "geometry"]
    df = df[keep]
    df.to_parquet(OUT)
    df.assign(stories=df.stories.astype(float)).to_file(INTERIM / "sf_buildings.fgb", driver="FlatGeobuf")
    log(f"buildings: wrote {OUT} ({len(df)} features)")


MAX_STORIES = 65  # SF's tallest building has 61 floors; assessor values like 752 are typos


def heights(df: gpd.GeoDataFrame) -> np.ndarray:
    """LiDAR (if the building existed in 2010) > OSM/Overture height > sane storey count > 7 m."""
    lidar = df.hgt_median_m.astype(float).values
    stories = df.stories.astype(float).values
    ov = df.overture_height.astype(float).values if "overture_height" in df else np.full(len(df), np.nan)
    start = df.start_year.values
    h = np.full(len(df), np.nan)
    use_lidar = np.isfinite(lidar) & (lidar >= 2.5) & (start < 2010)
    h[use_lidar] = lidar[use_lidar]
    from_ov = ~np.isfinite(h) & np.isfinite(ov) & (ov > 2)
    h[from_ov] = ov[from_ov]
    sane = np.isfinite(stories) & (stories > 0) & (stories <= MAX_STORIES)
    from_st = ~np.isfinite(h) & sane
    h[from_st] = stories[from_st] * 3.3 + 1.5
    h[~np.isfinite(h)] = 7.0
    bad = np.isfinite(stories) & (stories > MAX_STORIES)
    if bad.any():
        log(f"heights: ignored {bad.sum()} implausible storey counts (> {MAX_STORIES})")
    return np.clip(h, 2.5, 340.0)


def overture_heights(df: gpd.GeoDataFrame) -> np.ndarray:
    """OSM/Overture height of the Overture building overlapping each footprint most."""
    ov = read_overture("building").to_crs(UTM)
    ov = ov[ov.height.notna()][["height", "geometry"]].reset_index(drop=True)
    hits = gpd.sjoin(gpd.GeoDataFrame(geometry=df.geometry, crs=UTM), ov, predicate="intersects", how="inner")
    out = np.full(len(df), np.nan)
    best = np.zeros(len(df))
    for i, j in zip(hits.index.values, hits.index_right.values):
        a = df.geometry.iloc[i].intersection(ov.geometry.iloc[j]).area
        if a > best[i] and a > 0.5 * df.geometry.iloc[i].area:
            best[i] = a
            out[i] = ov.height.iloc[j]
    return out


def permit_years():
    import glob
    import json as _json
    files = sorted(glob.glob(str(RAW / "sf_permits_newdemo" / "page-*.json")))
    if not files:
        return None
    rows = []
    for f in files:
        rows.extend(_json.load(open(f)))
    p = pd.DataFrame(rows)
    p = p[p.permit_type.isin(["1", "2"]) & p.status.fillna("").str.lower().isin(["complete", "completed"])]
    p["year"] = pd.to_datetime(p.completed_date, errors="coerce").dt.year
    p = p[p.year.between(1900, CURRENT_YEAR)]
    p["blklot"] = p.block.str.strip() + p.lot.str.strip()
    # permits are filed on unit or map parcels; map them to map parcels via the parcels table
    pm = parcel_map()
    p["mapblklot"] = p.blklot.map(pm).fillna(p.blklot)
    return p.groupby("mapblklot").year.max()


_PARCEL_MAP = None


def parcel_map():
    global _PARCEL_MAP
    if _PARCEL_MAP is None:
        import glob
        frames = [gpd.read_file(f, columns=["blklot", "mapblklot"], ignore_geometry=True) for f in sorted(glob.glob(str(RAW / "sf_parcels" / "page-*.geojson")))]
        t = pd.concat(frames)
        _PARCEL_MAP = dict(zip(t.blklot, t.mapblklot))
    return _PARCEL_MAP


def cemeteries(crs):
    """[(polygon, cleared year, name)] from data/tables/landcover_history.csv cem_* rows."""
    from geocode import ring_polygon
    lc = pd.read_csv(TABLES / "landcover_history.csv")
    out = []
    for _, r in lc[lc.area_id.astype(str).str.startswith("cem_") & ~lc.area_id.astype(str).str.endswith("_cleared")].iterrows():
        try:
            out.append((ring_polygon(r.ring, r.ring_type, crs=crs), float(r.year_end), str(r["name"])))
        except Exception as e:  # noqa: BLE001
            log(f"cemetery {r.area_id}: {e}")
    return out


def redevelopment_areas():
    """data/manual/redevelopment_areas.csv -> [(polygon UTM, clear_start, clear_end, prior_fabric, id)],
    smallest areas first (A-1 inside A-2 must win)."""
    path = MANUAL / "redevelopment_areas.csv"
    if not path.exists():
        return []
    from geocode import ring_polygon
    t = pd.read_csv(path)
    out = []
    for _, r in t.iterrows():
        try:
            poly = ring_polygon(r.ring, r.ring_type, crs=UTM)
        except Exception as e:  # noqa: BLE001
            log(f"redevelopment: {r.area_id}: {e}")
            continue
        if poly is None or poly.is_empty:
            continue
        out.append((poly, float(r.clear_start), float(r.clear_end), str(r.prior_fabric), str(r.area_id)))
    out.sort(key=lambda a: a[0].area)
    return out


def known_dates():
    path = TABLES / "known_building_dates.csv"
    if not path.exists():
        return None
    k = pd.read_csv(path)
    k = k[pd.to_numeric(k.start_year, errors="coerce").notna() & k.lat.notna() & k.lon.notna()]
    k["start_year"] = k.start_year.astype(float)
    # modern footprints are standing buildings: a documented building that was demolished
    # before the 2016 snapshot (e.g. the 1939 Transbay Terminal) can't date its successor
    end = pd.to_numeric(k.get("end_year"), errors="coerce")
    k = k[end.isna() | (end >= 2016)]
    k = k.assign(end_year=pd.to_numeric(k.get("end_year"), errors="coerce").fillna(9999.0))
    return gpd.GeoDataFrame(k[["name", "start_year", "end_year"]], geometry=gpd.points_from_xy(k.lon, k.lat), crs=4326).to_crs(UTM)


def fbuy_years(points: gpd.GeoSeries) -> np.ndarray:
    """HISDAC-US first built-up year (250 m) at each point; NaN where unknown."""
    path = RAW / "hisdac" / "FBUY" / "data" / "FBUY.tif"
    out = np.full(len(points), np.nan)
    if not path.exists():
        return out
    import rasterio
    with rasterio.open(path) as src:
        pts = points.to_crs(src.crs)
        vals = np.array([v[0] for v in src.sample(zip(pts.x, pts.y))], dtype=float)
    vals[(vals < 1810) | (vals > CURRENT_YEAR)] = np.nan  # 0/1/nodata: no record or year unknown
    return vals


def read_overture(typ: str) -> gpd.GeoDataFrame:
    path = RAW / "overture" / RELEASE / f"{typ}.parquet"
    try:
        g = gpd.read_parquet(path)
    except ValueError:  # no geo metadata: geometry stored as WKB
        d = pd.read_parquet(path)
        g = gpd.GeoDataFrame(d, geometry=gpd.GeoSeries.from_wkb(d.geometry))
    if g.crs is None:
        g = g.set_crs(4326)
    return g


def overture_extras(df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """OSM/Overture buildings with no counterpart in the 2016 DataSF snapshot."""
    ov = read_overture("building").to_crs(UTM)
    ov = ov[ov.geometry.area > 15]
    counties = gpd.read_file(f"zip://{RAW / 'tiger' / 'tl_2024_us_county.zip'}")
    sf = counties[(counties.STATEFP == "06") & (counties.COUNTYFP == "075")].to_crs(UTM).geometry.iloc[0]
    ov = ov[ov.representative_point().within(sf)]
    # not buildings you can see: subway stations under Market St (Powell, Civic Center,
    # Montgomery, Embarcadero… mapped as building=train_station over the street — a
    # station on its own parcel, like 4th & King, stays), roofs / canopies, and the
    # Visitor Information Center down in sunken Hallidie Plaza
    pa = gpd.read_parquet(INTERIM / "sf_parcels_active.parquet").to_crs(UTM) if (INTERIM / "sf_parcels_active.parquet").exists() else None
    station = ov["class"].eq("train_station").values
    if pa is not None and station.any():
        pu = shapely.union_all(pa.geometry[pa.intersects(shapely.union_all(ov.geometry.values[station]).buffer(5))].values)
        on_parcel = np.array([g.intersection(pu).area / max(g.area, 1) for g in ov.geometry.values[station]])
        under = np.zeros(len(ov), bool)
        under[np.nonzero(station)[0][on_parcel < 0.5]] = True
    else:
        under = station
    sunken = ov["name"].fillna("").str.contains("Visitor Information Center").values
    canopy = ov["class"].eq("roof").values
    log(f"overture: dropping {int(under.sum())} subway stations under the street, {int(canopy.sum())} roofs/canopies, "
        f"{int(sunken.sum())} sunken-plaza buildings")
    ov = ov[~(under | canopy | sunken)]
    # area of each Overture building covered by DataSF footprints
    hits = gpd.sjoin(ov[["geometry"]], df[["geometry"]], predicate="intersects", how="left")
    covered = np.zeros(len(ov))
    pos = {k: i for i, k in enumerate(ov.index)}
    fp_geom = df.geometry
    for oi, fi in zip(hits.index, hits.index_right):
        if pd.isna(fi):
            continue
        covered[pos[oi]] += ov.geometry.loc[oi].intersection(fp_geom.iloc[int(fi)]).area
    frac = covered / ov.geometry.area.values
    extra = ov[frac < 0.3].copy()
    log(f"overture: {len(ov)} buildings in SF, {len(extra)} not in the 2016 DataSF footprints")
    # year: parcel under the centroid -> assessor
    by_map = pd.read_parquet(INTERIM / "sf_assessor_by_map.parquet")
    parcels = gpd.read_parquet(INTERIM / "sf_parcels_active.parquet") if (INTERIM / "sf_parcels_active.parquet").exists() else None
    if parcels is None:
        import glob
        parcels = gpd.GeoDataFrame(pd.concat([gpd.read_file(p) for p in sorted(glob.glob(str(RAW / "sf_parcels" / "page-*.geojson")))]), crs=4326)
        parcels = parcels[parcels.active.astype(str).str.lower() == "true"][["mapblklot", "geometry"]]
        parcels.to_parquet(INTERIM / "sf_parcels_active.parquet")
    parcels = parcels.to_crs(UTM)
    pts = gpd.GeoDataFrame({"oid": extra.index}, geometry=extra.representative_point(), crs=UTM)
    j = gpd.sjoin(pts, parcels, predicate="within", how="left").drop_duplicates("oid").set_index("oid")
    extra["mapblklot"] = j.mapblklot.reindex(extra.index).values
    extra = extra.join(by_map, on="mapblklot")
    extra["years"] = extra["years"].apply(lambda v: list(v) if isinstance(v, (list, np.ndarray)) else [])
    extra["raw_year"] = extra.years.apply(pick_year)
    extra["overture_height"] = extra.height
    extra["hgt_median_m"] = np.nan
    extra["sf16_bldgid"] = "ov:" + extra.id.astype(str)
    extra["source"] = np.where(extra.source_dataset == "OpenStreetMap", "osm_via_overture", "overture")
    extra["stories"] = extra.stories.fillna(extra.num_floors)
    extra["start_year"] = extra.raw_year
    cols = ["sf16_bldgid", "mapblklot", "years", "raw_year", "stories", "units", "use_code", "use_definition",
            "address", "hgt_median_m", "overture_height", "source", "geometry"]
    return extra[cols].reset_index(drop=True)


def apply_parts(df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Replace flat footprint extrusions with OSM building parts where mapped."""
    parts = read_overture("building_part").to_crs(UTM)
    bld = read_overture("building").to_crs(UTM)
    bld = bld[bld.id.isin(parts.building_id)].set_index("id")
    drop, add = set(), []
    for bid, ps in parts.groupby("building_id"):
        if bid not in bld.index:
            continue
        outline = bld.loc[bid]
        ph = ps.height.astype(float)
        if ph.isna().all() and pd.isna(outline.height):
            continue
        cands = df.sindex.query(outline.geometry, predicate="intersects")
        cands = [c for c in cands if df.geometry.iloc[c].intersection(outline.geometry).area > 0.5 * df.geometry.iloc[c].area]
        if not cands:
            continue
        donor = max(cands, key=lambda c: df.geometry.iloc[c].area)
        row = df.iloc[donor]
        for _, p in ps.iterrows():
            h = p.height if pd.notna(p.height) else (outline.height if pd.notna(outline.height) else row.height)
            base = p.min_height if pd.notna(p.min_height) else 0.0
            if h - base < 0.5 or p.geometry.area < 2:
                continue
            r = row.copy()
            r["geometry"] = p.geometry
            r["height"] = float(h - base)
            r["base"] = float(base)
            r["source"] = "osm_parts_via_overture"
            r["sf16_bldgid"] = f"part:{p.id}"
            add.append(r)
        drop.update(cands)
    log(f"parts: replaced {len(drop)} footprints with {len(add)} OSM building parts")
    df = df.drop(df.index[list(drop)])
    if add:
        df = pd.concat([df, gpd.GeoDataFrame(add, crs=UTM)], ignore_index=True)
    return gpd.GeoDataFrame(df, geometry="geometry", crs=UTM)


def validate(df: gpd.GeoDataFrame):
    problems = []
    if (df.start_year > CURRENT_YEAR + 1).any():
        problems.append(f"{(df.start_year > CURRENT_YEAR + 1).sum()} start_year in the future")
    if (df.start_year >= df.end_year).any():
        problems.append("start_year >= end_year")
    if df.in_fire_zone.any():
        bad = df.in_fire_zone & (df.start_year < 1906.3)
        if bad.any():
            problems.append(f"{bad.sum()} buildings in the 1906 burned area predate the fire")
    if (df.height <= 0).any():
        problems.append("non-positive heights")
    if problems:
        raise SystemExit("VALIDATION FAILED: " + "; ".join(problems))
    log("validate: ok")


def report(df, raw, spikes):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True)
    bins = np.arange(1840, CURRENT_YEAR + 2)
    axes[0].hist(raw[raw > 0], bins=bins, color="#b5543a")
    axes[0].set_title("Assessor year_property_built (raw, per footprint)")
    axes[0].set_yscale("log")
    for y in sorted(spikes):
        axes[0].axvline(y + 0.5, color="#333", lw=0.6, ls=":")
    exact = df.year_confidence == "exact"
    axes[1].hist([df.start_year[exact], df.start_year[~exact]], bins=bins, stacked=True,
                 color=["#4096a0", "#e8923c"], label=["exact", "estimated"])
    axes[1].set_title("Cleaned start_year")
    axes[1].set_yscale("log")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(REPORTS / "sf_years.png", dpi=110)
    summary = {
        "features": int(len(df)),
        "by_source": df.source.value_counts().to_dict(),
        "by_confidence": df.year_confidence.value_counts().to_dict(),
        "by_reason": df.year_reason.value_counts().to_dict(),
        "spike_years": sorted(int(s) for s in spikes),
        "height_median": float(df.height.median()),
    }
    (REPORTS / "sf_buildings_summary.json").write_text(json.dumps(summary, indent=2))
    log(f"report: {summary}")


if __name__ == "__main__":
    main()
