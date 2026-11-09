"""Stage: ground detail — the small real features a satellite view shows and the terrain
grid (30 m) can't: golf fairways, greens, tees and bunkers, sports pitches, running
tracks, playgrounds, plazas, gardens and lawns (OpenStreetMap outlines via Overture
base land_use), draped on the terrain. Plus labels for every city park (one per name period
where data/tables/park_names.csv gives a name history).

Dating (outlines are real, dates estimated):
  * inside a golf course -> the course's opening year (data/tables/golf_courses.csv)
  * inside an RPD park   -> the park's year (data/tables/parks.csv)
  * otherwise            -> when the neighbourhood was built (2nd earliest building
                            within 60 m, incl. vanished ones), else 1950

Outputs: viewer/public/data/ground-detail.bin.gz (BAYT: start_indices, positions f32[3]
offsets from ORIGIN with z = ground + 0.3 m, kind u8, years f32[2]),
viewer/public/data/park-labels.json
"""
from __future__ import annotations

import glob
import json

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from scipy.spatial import cKDTree

from common import MANUAL, INTERIM, RAW, TABLES, VIEWER_DATA, log
from download_overture import RELEASE
from export_columnar import write_columnar
from roads import ORIGIN, Ground, UTM

# kinds — keep in sync with viewer/src/layers/ground-detail.ts
KINDS = {"fairway": 0, "green": 1, "tee": 2, "rough": 3, "bunker": 4, "driving_range": 5, "pitch": 6, "track": 7,
         "playground": 8, "dog_park": 9, "pedestrian": 10, "plaza": 10, "garden": 11, "flowerbed": 11, "grass": 12,
         "recreation_ground": 12, "village_green": 12, "water_hazard": 14, "lateral_water_hazard": 14}
GOLF = {"fairway", "green", "tee", "rough", "bunker", "driving_range"}
# draw order (the viewer drapes these without depth writes: later draws on top) —
# lawns and plazas under fields, fairways under tees and greens, bunkers and ponds last
DRAW_RANK = {12: 0, 11: 1, 10: 2, 3: 3, 0: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 2: 10, 1: 11, 14: 12, 4: 13, 13: 14}


def draw_order(kind_codes, areas):
    """Indices in drawing order: by DRAW_RANK, bigger pieces first within a rank."""
    rank = np.array([DRAW_RANK.get(int(k), 6) for k in kind_codes])
    return np.lexsort((-np.asarray(areas, float), rank))


def rpd_parks():
    g = gpd.GeoDataFrame(pd.concat([gpd.read_file(f) for f in glob.glob(str(RAW / "sf_rpd_parks" / "*.geojson"))]), crs=4326)
    g = g[g.geometry.notna()].copy()
    g["name"] = g.map_park_n.str.strip()
    t = pd.read_csv(TABLES / "parks.csv")
    years = dict(zip(t.name.str.strip(), pd.to_numeric(t.start_year, errors="coerce")))
    g["year"] = g.name.map(years)
    return g


def main():
    lu = pd.read_parquet(RAW / "overture" / RELEASE / "base_land_use.parquet")
    lu = gpd.GeoDataFrame(lu, geometry=gpd.GeoSeries.from_wkb(lu.geometry), crs=4326)
    golf_t = pd.read_csv(TABLES / "golf_courses.csv")
    golf_y = dict(zip(golf_t.name, golf_t.year_open))
    courses = lu[lu["class"] == "golf_course"].copy()
    courses["year"] = courses["name"].map(golf_y)
    feats = lu[lu["class"].isin(KINDS)].copy()
    feats = feats.explode(index_parts=False)
    feats = feats[feats.geometry.geom_type == "Polygon"].reset_index(drop=True)
    parks = rpd_parks()

    rp = feats.geometry.representative_point()
    pts = gpd.GeoDataFrame(geometry=rp, crs=4326)
    year = np.full(len(feats), np.nan)
    # golf features: their course
    j = gpd.sjoin(pts, courses[["year", "geometry"]], predicate="within", how="left")
    j = j[~j.index.duplicated()]
    is_golf = feats["class"].isin(GOLF).values
    year = np.where(is_golf & j.year.notna().values, j.year.values, year)
    # inside a city park
    # sports grounds in a park are no older than the park as a playground: the first name
    # period that calls it a playground / recreation ground / field (park_names.csv), else
    # the era floor of the kind (estimated): municipal playgrounds and athletic fields from
    # the Playground Commission (1908), dog parks from the 1990s — a reserved square of
    # 1855 had no ball fields
    sf_names, _ = park_name_periods()
    play_y = {}
    for pk, periods in sf_names.items():
        ys = [y0 for nm, y0, _y1 in periods if any(w in nm.lower() for w in ("playground", "recreation", "field", "athletic"))]
        if ys:
            play_y[pk] = min(ys)
    parks["play_year"] = parks.name.map(play_y)
    jp = gpd.sjoin(pts, parks[["year", "play_year", "geometry"]], predicate="within", how="left")
    jp = jp[~jp.index.duplicated()]
    year = np.where(np.isnan(year) & jp.year.notna().values, jp.year.values, year)
    cls = feats["class"].values
    floor = np.select([np.isin(cls, ["pitch", "track", "playground"]), cls == "dog_park"], [1909.0, 1992.0], -np.inf)
    floor = np.where(jp.play_year.notna().values & np.isin(cls, ["pitch", "track", "playground"]),
                     np.maximum(jp.play_year.values.astype(float), 1898.0), floor)
    in_park = jp.year.notna().values & ~is_golf
    year = np.where(in_park, np.maximum(year, floor), year)
    # otherwise when the neighbourhood around it was built
    frames = [gpd.read_parquet(INTERIM / "sf_buildings.parquet")[["start_year", "geometry"]]]
    if (INTERIM / "sf_predecessors.parquet").exists():
        _p = gpd.read_parquet(INTERIM / "sf_predecessors.parquet")[["start_year", "geometry"]]
        frames.append(_p[_p.start_year >= 1770])
    b = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=4326).to_crs(UTM)
    bc = b.geometry.representative_point()
    tree = cKDTree(np.column_stack([bc.x, bc.y]))
    pu = rp.to_crs(UTM)
    d, idx = tree.query(np.column_stack([pu.x, pu.y]), k=4, distance_upper_bound=60)
    ny = np.where(np.isfinite(d), b.start_year.values[np.minimum(idx, len(b) - 1)], np.inf)
    ny.sort(axis=1)
    nb = np.where(np.isfinite(ny[:, 1]), ny[:, 1], np.nan)
    year = np.where(np.isnan(year), nb, year)
    year = np.where(np.isnan(year), 1950.0, year)
    # fields and plazas of a reconstructed stadium / landmark site are no older than it
    # (Oracle Park's diamond is not there before 2000, whatever the warehouses nearby)
    lm = pd.read_csv(TABLES / "landmarks.csv")
    lm = lm[lm["kind"].isin(["stadium"]) | lm["id"].isin(["yerba_buena_gardens"])]
    lmp = gpd.GeoSeries(gpd.points_from_xy(lm.lon, lm.lat), crs=4326).to_crs(UTM)
    for (_, r), p in zip(lm.iterrows(), lmp.values):
        near = (pu.distance(p) < (120 if r["kind"] != "stadium" else 180)).values
        same_site = lm[(abs(lm.lat - r.lat) < 1e-4) & (abs(lm.lon - r.lon) < 1e-4)]
        y0 = float(same_site.start_year.min())
        year = np.where(near, np.maximum(year, y0), year)

    ground = Ground()
    starts, pos, kinds, years = [0], [], [], []
    fu = feats.to_crs(UTM)
    for i in draw_order(feats["class"].map(KINDS).values, fu.geometry.area.values):
        geom = fu.geometry.values[i]
        ring = geom.exterior
        if ring.length < 8:
            continue
        n = max(4, int(np.ceil(ring.length / 12.0)))
        p = [ring.interpolate(t, normalized=True) for t in np.linspace(0, 1, n, endpoint=False)]
        ll = gpd.GeoSeries(p, crs=UTM).to_crs(4326)
        lon, lat = np.append(ll.x.values, ll.x.values[0]), np.append(ll.y.values, ll.y.values[0])  # closed ring
        z = ground(lon, lat) + 0.3
        pos.append(np.column_stack([lon - ORIGIN[0], lat - ORIGIN[1], z]).ravel())
        starts.append(starts[-1] + n + 1)
        k = KINDS[feats["class"].iloc[i]]
        # the big ovals (Golden Gate Park's Polo Field cycling / horse track, ~1 mile) are
        # dirt and asphalt, not a red synthetic running track
        if k == KINDS["track"] and fu.geometry.values[i].area > 8000:
            k = KINDS["playground"]
        kinds.append(k)
        years.extend((float(year[i]), 9999.0))
    # vanished large sites (data/manual/vanished_sites/sites.geojson): racetrack ovals,
    # turf courses, infields, parking — drawn for their years, smaller parts on top
    sp = MANUAL / "vanished_sites" / "sites.geojson"
    if sp.exists():
        SITE_KIND = {"dirt_track": 13, "turf": 6, "grass": 12, "park": 12, "parking": 10, "water": 14}
        st = gpd.read_file(sp)
        st = st[st["cover"].isin(list(SITE_KIND))].explode(index_parts=False)
        st = st[st.geometry.geom_type == "Polygon"].reset_index(drop=True)
        su = st.to_crs(UTM)
        n_site = 0
        for rank, i in enumerate(np.argsort(-su.geometry.area.values)):
            ring = su.geometry.values[i].exterior
            if ring.length < 8:
                continue
            n = max(4, int(np.ceil(ring.length / 12.0)))
            p_ = [ring.interpolate(t, normalized=True) for t in np.linspace(0, 1, n, endpoint=False)]
            ll = gpd.GeoSeries(p_, crs=UTM).to_crs(4326)
            lon, lat = np.append(ll.x.values, ll.x.values[0]), np.append(ll.y.values, ll.y.values[0])
            z = ground(lon, lat) + 0.3 + 0.06 * min(rank, 20)
            pos.append(np.column_stack([lon - ORIGIN[0], lat - ORIGIN[1], z]).ravel())
            starts.append(starts[-1] + n + 1)
            kinds.append(SITE_KIND[st["cover"].values[i]])
            y0 = float(pd.to_numeric(st["year_start"].values[i], errors="coerce"))
            y1 = pd.to_numeric(st["year_end"].values[i], errors="coerce")
            years.extend((y0, float(y1) if np.isfinite(y1) else 9999.0))
            n_site += 1
        log(f"ground detail: {n_site} parts of vanished sites")
    write_columnar(VIEWER_DATA / "ground-detail.bin.gz", {
        "start_indices|shuffle": np.asarray(starts, np.uint32),
        "positions|shuffle": np.concatenate(pos).astype(np.float32),
        "kind": np.asarray(kinds, np.uint8),
        "years": np.asarray(years, np.float32),
    }, origin=ORIGIN, counts={"polygons": len(kinds), "vertices": starts[-1]})
    log(f"ground detail: {len(kinds)} outlines ({np.bincount(kinds, minlength=15).tolist()})")

    # labels for every city park (and the golf courses' parks), dated where known; a park
    # that was renamed gets one label per name period (data/tables/park_names.csv), never
    # before the park itself (parks.csv start_year)
    labels = []
    sf_names, _ = park_name_periods()
    pu2 = parks.to_crs(UTM)
    for (_, r), area in zip(parks.iterrows(), pu2.geometry.area.values):
        if not np.isfinite(r.year):
            continue
        c = r.geometry.representative_point()
        for nm, y0, y1 in sf_names.get(r["name"], [(r["name"], -np.inf, 9999.0)]):
            s = max(float(r.year), y0)
            if s >= y1:
                continue
            lab = {"name": nm, "lon": round(c.x, 6), "lat": round(c.y, 6), "start": s, "ha": round(float(area) / 1e4, 2)}
            if y1 < 9999:
                lab["end"] = y1
            labels.append(lab)
    n_parks = len(labels)
    # names of military / industrial sites and vanished large sites, over the years they
    # stood (label_start / label_end where the ground outlives the use)
    from extent import in_extent
    for f in (MANUAL / "industrial_sites" / "sites.geojson", MANUAL / "vanished_sites" / "sites.geojson"):
        if not f.exists():
            continue
        st = gpd.read_file(f).to_crs(4326)
        for site_id, grp in st.groupby("site_id"):
            nm = next((str(v) for v in grp.get("name_label", pd.Series(dtype=object)) if isinstance(v, str) and v.strip()), None) \
                or next((str(v) for v in grp.get("name", pd.Series(dtype=object)) if isinstance(v, str) and v.strip()), None)
            if not nm or len(nm) > 40:
                continue
            y0 = pd.to_numeric(grp.get("label_start", grp["year_start"]), errors="coerce")
            y1 = pd.to_numeric(grp.get("label_end", grp["year_end"]), errors="coerce")
            y0 = y0.min() if y0.notna().any() else pd.to_numeric(grp["year_start"], errors="coerce").min()
            y1 = y1.max() if y1.notna().any() else pd.to_numeric(grp["year_end"], errors="coerce").max()
            if not np.isfinite(y0):
                continue
            geom = grp.geometry.union_all()
            if geom is None or geom.is_empty:
                continue
            c = geom.representative_point()
            if not in_extent(gpd.GeoSeries([c], crs=4326))[0]:
                continue
            ha = float(gpd.GeoSeries([geom], crs=4326).to_crs(UTM).area.iloc[0]) / 1e4
            labels.append({"name": nm, "lon": round(c.x, 6), "lat": round(c.y, 6), "start": float(y0),
                           "end": float(y1) if np.isfinite(y1) else 9999.0, "ha": round(ha, 2), "tier": "site"})
    labels += village_labels()
    labels += region_detail(golf_y)
    (VIEWER_DATA / "park-labels.json").write_text(json.dumps(labels))
    log(f"ground detail: {n_parks} dated SF park labels ({len(parks)} parks, "
        f"{len(sf_names)} with a name history), {len(labels) - n_parks} site / region park labels")


def park_name_periods():
    """Name histories (data/tables/park_names.csv): one row per name a park went by.
    `park` is the park's key — the RPD / parks.csv name in San Francisco, the OSM / Overture
    name in the region (rows with lon / lat, matched within ~1 km); `name` is the label for
    [from_year, to_year). A park listed here is labelled only for its listed periods (a gap
    = no known name, no label). Returns ({sf park: [(name, y0, y1)]}, [region rows])."""
    p = TABLES / "park_names.csv"
    if not p.exists():
        return {}, []
    t = pd.read_csv(p)
    t["from_year"] = pd.to_numeric(t.from_year, errors="coerce")
    t["to_year"] = pd.to_numeric(t.to_year, errors="coerce").fillna(9999.0)
    t = t[t.from_year.notna() & t.name.notna()]
    lon = pd.to_numeric(t.get("lon"), errors="coerce")
    lat = pd.to_numeric(t.get("lat"), errors="coerce")
    sf, region = {}, []
    for r, x, y in zip(t.itertuples(), lon, lat):
        if np.isfinite(x) and np.isfinite(y):
            region.append((str(r.park).strip(), float(x), float(y), str(r.name), float(r.from_year), float(r.to_year)))
        else:
            sf.setdefault(str(r.park).strip(), []).append((str(r.name), float(r.from_year), float(r.to_year)))
    for v in sf.values():
        v.sort(key=lambda a: a[1])
    return sf, region


def region_green_dates():
    """Researched opening / closing years of golf courses, cemeteries, parks, zoos outside San
    Francisco (data/tables/region_green_dates.csv: `name` = the Overture / OSM name of the
    feature, lon / lat = a point inside it because names repeat between cities).
    Returns [(name, lon, lat, class, year_open, year_close)]; year_open 9999 = planned, not built."""
    p = TABLES / "region_green_dates.csv"
    if not p.exists():
        return []
    t = pd.read_csv(p)
    y0 = pd.to_numeric(t.year_open, errors="coerce")
    y1 = pd.to_numeric(t.year_close, errors="coerce").fillna(9999.0)
    return [(str(n).strip(), float(x), float(y), str(c), float(a), float(b))
            for n, x, y, c, a, b in zip(t.name, t.lon, t.lat, t["class"], y0, y1) if np.isfinite(a)]


def green_lookup(rows, names, lons, lats):
    """(year_open, year_close) arrays for features matched to region_green_dates.csv rows by
    name and position (within ~2 km of the row's point); NaN / 9999 where unmatched."""
    by_name = {}
    for r in rows:
        by_name.setdefault(r[0], []).append(r)
    y0 = np.full(len(names), np.nan)
    y1 = np.full(len(names), 9999.0)
    for i, (n, x, y) in enumerate(zip(names, lons, lats)):
        best, bd = None, 0.025
        for r in by_name.get(str(n).strip(), ()):
            d = max(abs(r[1] - x), abs(r[2] - y))
            if d < bd:
                best, bd = r, d
        if best is not None:
            y0[i], y1[i] = best[4], best[5]
    return y0, y1


def village_labels():
    """Names of the contact-era Native villages (data/manual/ohlone/villages.csv,
    early_region.csv, early_sf.csv tule rows; mission neophyte huts and sweat houses are not
    labelled): the village's own name where the sources give one (Pruristac, Petlenuc,
    Olompali), else its local tribe's ('Huchiun village'), from 1769 until it emptied."""
    import re
    from extent import in_extent

    def short(name, vid):
        n = str(name)
        if vid == "ohl_seunen_san_ramon":
            return "Seunen village"
        if re.search(r"neophyte|temescal|sweat house|\bhuts\b|^Second", n, re.I):
            return ""
        if ", " in n:
            head = re.sub(r"\s*\([^)]*\)", "", n.split(", ")[0]).split(" / ")[0].strip()
            if len(head.split()) <= 2 and "village" not in head.lower():
                return head
        m = re.match(r"^([A-Z][\w'-]+(?: [A-Z][\w'-]+)?)(?: \([^)]*\))? (?:(?:Ohlone|Bay Miwok|Coast Miwok) )?"
                     r"(?:village|villages|rancheria|main town)", n)
        if not m:
            return ""
        w = re.sub(r" (Ohlone|Bay|Coast)$", "", m.group(1))
        return "Ohlone village" if w == "Ohlone" else f"{w} village"

    out = []
    for f in (MANUAL / "ohlone" / "villages.csv", TABLES / "early_region.csv", TABLES / "early_sf.csv"):
        if not f.exists():
            continue
        t = pd.read_csv(f)
        t = t[t.material.astype(str).str.contains("tule") & pd.to_numeric(t.lat, errors="coerce").notna()]
        for r in t.itertuples():
            nm = short(r.name, r.id)
            y1 = pd.to_numeric(r.end_year, errors="coerce")
            if not nm or not np.isfinite(y1) or y1 <= 1769:
                continue
            c = gpd.GeoSeries(gpd.points_from_xy([float(r.lon)], [float(r.lat)]), crs=4326)
            if not in_extent(c)[0]:
                continue
            out.append({"name": nm, "lon": round(float(r.lon), 6), "lat": round(float(r.lat), 6),
                        "start": max(1769.0, float(r.start_year)), "end": float(y1), "ha": 0.0, "tier": "village"})
    log(f"ground detail: {len(out)} Native village labels")
    return out


def _outlines(fu, ground, kind_of, years_of, z_extra=0.0):
    starts, pos, kinds, years = [0], [], [], []
    for i in draw_order([kind_of(j) for j in range(len(fu))], fu.geometry.area.values):
        geom = fu.geometry.values[i]
        ring = geom.exterior
        if ring.length < 8:
            continue
        n = max(4, int(np.ceil(ring.length / 12.0)))
        p = [ring.interpolate(t, normalized=True) for t in np.linspace(0, 1, n, endpoint=False)]
        ll = gpd.GeoSeries(p, crs=UTM).to_crs(4326)
        lon, lat = np.append(ll.x.values, ll.x.values[0]), np.append(ll.y.values, ll.y.values[0])
        z = ground(lon, lat) + 0.3 + z_extra
        pos.append(np.column_stack([lon - ORIGIN[0], lat - ORIGIN[1], z]).ravel())
        starts.append(starts[-1] + n + 1)
        kinds.append(kind_of(i))
        years.extend(years_of(i))
    return starts, pos, kinds, years


def region_detail(golf_y):
    """The five counties' golf courses, pitches, tracks, playgrounds, gardens and lawns
    (OSM outlines via Overture region5_land_use) -> region-ground-detail.bin.gz, loaded by
    the viewer when zoomed in. Dated like SF's: golf features by their course (golf_courses.csv
    and region_green_dates.csv — researched opening year, and closing year for courses that
    shut but are still mapped — else the course's neighbourhood: early tenth of the buildings
    within 500 m, not before 1895), the rest by when the neighbourhood was built (2nd earliest building within 60 m,
    incl. vanished ones: region_building_points.parquet), else 1950. Also labels for the named
    parks of 1 ha or more."""
    from extent import in_extent
    p = RAW / "overture" / RELEASE / "region5_land_use.parquet"
    bp = INTERIM / "region_building_points.parquet"
    if not (p.exists() and bp.exists()):
        log("ground detail: no region land use / building points yet")
        return []
    lu = pd.read_parquet(p)
    lu = gpd.GeoDataFrame(lu, geometry=gpd.GeoSeries.from_wkb(lu.geometry), crs=4326)
    lu = lu[in_extent(lu.geometry.representative_point())]
    courses = lu[lu["class"] == "golf_course"].copy()
    feats = lu[lu["class"].isin(KINDS)].explode(index_parts=False)
    feats = feats[feats.geometry.geom_type == "Polygon"].reset_index(drop=True)
    b = pd.read_parquet(bp, columns=["lon", "lat", "start_year"])
    b = b[b.start_year >= 1770]
    bu = gpd.GeoSeries(gpd.points_from_xy(b.lon, b.lat), crs=4326).to_crs(UTM)
    tree = cKDTree(np.column_stack([bu.x.values, bu.y.values]))
    by = b.start_year.values.astype(float)

    def nth_year(xy, k, r, q=None):
        d, idx = tree.query(xy, k=k, distance_upper_bound=r)
        ny = np.where(np.isfinite(d), by[np.minimum(idx, len(by) - 1)], np.inf)
        ny.sort(axis=1)
        if q is None:
            return np.where(np.isfinite(ny[:, 1]), ny[:, 1], np.nan)
        ok = np.isfinite(ny)
        out = np.full(len(xy), np.nan)
        for i in range(len(xy)):
            v = ny[i][ok[i]]
            if len(v) >= 5:
                out[i] = np.percentile(v, q)
        return out

    cu = courses.to_crs(UTM)
    cc = cu.geometry.representative_point()
    cy = courses["name"].map(golf_y).astype(float).values
    green = region_green_dates()
    ccl = cc.to_crs(4326)
    gy0, gy1 = green_lookup([r for r in green if r[3] == "golf_course"], courses["name"].values, ccl.x.values, ccl.y.values)
    cy = np.where(np.isfinite(gy0), gy0, cy)
    est = nth_year(np.column_stack([cc.x.values, cc.y.values]), 200, 500.0, q=10)
    courses["year"] = np.where(np.isfinite(cy), cy, np.maximum(np.nan_to_num(est, nan=1960.0), 1895.0))
    courses["end"] = gy1
    fu = feats.to_crs(UTM)
    rp = fu.geometry.representative_point()
    year = nth_year(np.column_stack([rp.x.values, rp.y.values]), 4, 60.0)
    j = gpd.sjoin(gpd.GeoDataFrame(geometry=rp.values, crs=UTM),
                  cu[["geometry"]].assign(cyear=courses.year.values, cend=courses.end.values),
                  predicate="within", how="left")
    j = j[~j.index.duplicated()]
    golf = feats["class"].isin(GOLF | {"water_hazard", "lateral_water_hazard"}).values & j.cyear.notna().values
    year = np.where(golf, j.cyear.values, year)
    year = np.where(np.isnan(year), 1950.0, year)
    end = np.where(golf, j.cend.fillna(9999.0).values, 9999.0)   # closed courses still mapped
    kinds_ = feats["class"].map(KINDS).values
    area = fu.geometry.area.values
    starts, pos, kinds, years = _outlines(
        fu, Ground(),
        lambda i: KINDS["playground"] if (kinds_[i] == KINDS["track"] and area[i] > 8000) else int(kinds_[i]),
        lambda i: (float(year[i]), float(end[i])))
    write_columnar(VIEWER_DATA / "region-ground-detail.bin.gz", {
        "start_indices|shuffle": np.asarray(starts, np.uint32),
        "positions|shuffle": np.concatenate(pos).astype(np.float32),
        "kind": np.asarray(kinds, np.uint8),
        "years": np.asarray(years, np.float32),
    }, origin=ORIGIN, counts={"polygons": len(kinds), "vertices": starts[-1]})
    log(f"ground detail: region {len(kinds)} outlines ({np.bincount(kinds, minlength=15).tolist()}), "
        f"{len(courses)} golf courses ({int(np.isfinite(cy).sum())} with a researched year)")
    # labels: named parks of 1 ha or more, from their researched opening year
    # (region_green_dates.csv), else from when their neighbourhood was built
    pk = lu[(lu["class"].isin(["park", "golf_course", "recreation_ground"])) & lu["name"].notna()]
    pk = pk[pk["name"].astype(str).str.len().between(3, 40)]
    pku = pk.to_crs(UTM)
    ha = pku.geometry.area.values / 1e4
    keep = ha >= 1.0
    pk, pku, ha = pk[keep], pku[keep], ha[keep]
    pr = pku.geometry.representative_point()
    py = nth_year(np.column_stack([pr.x.values, pr.y.values]), 4, 150.0)
    gyear = pk["name"].map(dict(zip(courses["name"], courses["year"]))).astype(float).values
    py = np.where(np.isfinite(gyear), gyear, py)
    prl0 = pr.to_crs(4326)
    ty0, ty1 = green_lookup(green, pk["name"].astype(str).values, prl0.x.values, prl0.y.values)
    py = np.where(np.isfinite(ty0), ty0, py)
    # researched name histories (park_names.csv rows with lon / lat) replace the
    # neighbourhood date: their periods start when the park opened under that name
    _, hist = park_name_periods()
    out, seen, n_hist = [], set(), 0
    prl = pr.to_crs(4326)
    for nm, c, y, h, y1 in zip(pk["name"].astype(str), prl.values, py, ha, ty1):
        key = (nm, round(c.x, 2), round(c.y, 2))
        if key in seen:
            continue
        rows = [r for r in hist if r[0] == nm.strip() and abs(r[1] - c.x) < 0.012 and abs(r[2] - c.y) < 0.01]
        if rows:
            seen.add(key)
            n_hist += 1
            for _, _, _, label, y0, y1 in sorted(rows, key=lambda a: a[4]):
                lab = {"name": label, "lon": round(c.x, 6), "lat": round(c.y, 6), "start": y0, "ha": round(float(h), 2)}
                if y1 < 9999:
                    lab["end"] = y1
                out.append(lab)
            continue
        if not np.isfinite(y):   # no neighbourhood to date it by: no label
            continue
        seen.add(key)
        if y >= 9999:            # planned, not built
            continue
        lab = {"name": nm, "lon": round(c.x, 6), "lat": round(c.y, 6), "start": float(y), "ha": round(float(h), 2)}
        if y1 < 9999:
            lab["end"] = float(y1)
        out.append(lab)
    log(f"ground detail: {len(out)} region park labels ({n_hist} parks with a researched name history)")
    return out


if __name__ == "__main__":
    main()
