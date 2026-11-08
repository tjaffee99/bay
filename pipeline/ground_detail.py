"""Stage: ground detail — the small real features a satellite view shows and the terrain
grid (30 m) can't: golf fairways, greens, tees and bunkers, sports pitches, running
tracks, playgrounds, plazas, gardens and lawns (OpenStreetMap outlines via Overture
base land_use), draped on the terrain. Plus labels for every city park.

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
         "recreation_ground": 12, "village_green": 12}
GOLF = {"fairway", "green", "tee", "rough", "bunker", "driving_range"}


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
    jp = gpd.sjoin(pts, parks[["year", "geometry"]], predicate="within", how="left")
    jp = jp[~jp.index.duplicated()]
    year = np.where(np.isnan(year) & jp.year.notna().values, jp.year.values, year)
    # otherwise when the neighbourhood around it was built
    frames = [gpd.read_parquet(INTERIM / "sf_buildings.parquet")[["start_year", "geometry"]]]
    if (INTERIM / "sf_predecessors.parquet").exists():
        frames.append(gpd.read_parquet(INTERIM / "sf_predecessors.parquet")[["start_year", "geometry"]])
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
    for i, geom in enumerate(fu.geometry.values):
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

    # labels for every city park (and the golf courses' parks), dated where known
    labels = []
    pu2 = parks.to_crs(UTM)
    for (_, r), area in zip(parks.iterrows(), pu2.geometry.area.values):
        if not np.isfinite(r.year):
            continue
        c = r.geometry.representative_point()
        labels.append({"name": r["name"], "lon": round(c.x, 6), "lat": round(c.y, 6), "start": float(r.year),
                       "ha": round(float(area) / 1e4, 2)})
    (VIEWER_DATA / "park-labels.json").write_text(json.dumps(labels))
    log(f"ground detail: {len(labels)} dated park labels ({len(parks)} parks)")


if __name__ == "__main__":
    main()
