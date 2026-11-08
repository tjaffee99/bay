"""Today's footprints inside a site, with the year the live map gives them.

footprints(geom_ll) -> GeoDataFrame [fid, src, geometry (lon/lat), area_m2, circ, live_year,
                                     live_end, roll_year, roll_src]
  * region (5 counties): Overture `region5_building` footprints; live year = the built
    `region_building_points` row at the same representative point (nearest within 4 m);
    roll year / source = `region5_footprint_years` (public > third-party > commercial > historic)
  * San Francisco: `sf_buildings.parquet` (start_year as built; raw assessor year)
"""
from __future__ import annotations

from functools import lru_cache

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from scipy.spatial import cKDTree

ROOT = "/home/user/bay"
OVT = f"{ROOT}/data/raw/overture/2026-10-21.0"
INTERIM = f"{ROOT}/data/interim"
SF_BOX = (-122.5155, 37.7080, -122.3550, 37.8325)


@lru_cache(maxsize=1)
def _region_points():
    r = pd.read_parquet(f"{INTERIM}/region_building_points.parquet")
    X = np.radians(r.lon.values) * 6378137.0 * np.cos(np.radians(37.7))
    Y = np.radians(r.lat.values) * 6378137.0
    return r, cKDTree(np.c_[X, Y])


def _roll(ids):
    """Roll years / sources of these footprint ids only (the full table is ~1.9 M rows)."""
    cols = ["id", "year_public", "src_public", "year_third_party", "src_third_party", "year_commercial",
            "src_commercial", "year_historic", "src_historic"]
    con = duckdb.connect()
    con.register("want", pd.DataFrame({"id": list(ids)}))
    q = (f"select {', '.join('r.' + c for c in cols)} from read_parquet('{INTERIM}/region5_footprint_years.parquet') r "
         f"join want w on r.id = w.id")
    return con.execute(q).df().drop_duplicates("id").set_index("id")


@lru_cache(maxsize=1)
def _sf():
    s = gpd.read_parquet(f"{INTERIM}/sf_buildings.parquet",
                         columns=["sf16_bldgid", "raw_year", "start_year", "end_year", "year_source", "geometry"])
    return s


def _circ(g):
    a = shapely.area(g)
    p = shapely.length(g)
    return np.where(p > 0, 4 * np.pi * a / np.maximum(p, 1e-12) ** 2, 0)


def footprints(geom_ll, buffer_m=0.0):
    b = geom_ll.bounds
    pad = 0.0005
    con = duckdb.connect()
    con.execute("LOAD spatial;")
    q = (f"select id, ST_AsWKB(geometry) g from read_parquet('{OVT}/region5_building.parquet') "
         f"where ST_XMin(geometry) < {b[2] + pad} and ST_XMax(geometry) > {b[0] - pad} "
         f"and ST_YMin(geometry) < {b[3] + pad} and ST_YMax(geometry) > {b[1] - pad}")
    rows = con.execute(q).fetchall()
    frames = []
    sel = geom_ll if not buffer_m else gpd.GeoSeries([geom_ll], crs=4326).to_crs(32610).buffer(buffer_m).to_crs(4326).iloc[0]
    shapely.prepare(sel)
    if rows:
        g = gpd.GeoDataFrame({"fid": [r[0] for r in rows]},
                             geometry=gpd.GeoSeries.from_wkb([bytes(r[1]) for r in rows]), crs=4326)
        g = g[g.geom_type.isin(["Polygon", "MultiPolygon"])]
        g = g[shapely.contains(sel, g.geometry.representative_point().values)].copy()
        if len(g):
            # SF footprints come from DataSF, not Overture
            rp = g.geometry.representative_point()
            in_sf = (rp.x > SF_BOX[0]) & (rp.x < SF_BOX[2]) & (rp.y > SF_BOX[1]) & (rp.y < SF_BOX[3])
            g = g[~in_sf.values | (rp.y.values < 37.708)]
        if len(g):
            r, tree = _region_points()
            rp = g.geometry.representative_point()
            X = np.radians(rp.x.values) * 6378137.0 * np.cos(np.radians(37.7))
            Y = np.radians(rp.y.values) * 6378137.0
            d, i = tree.query(np.c_[X, Y], distance_upper_bound=4.0)
            ok = np.isfinite(d)
            ii = np.where(ok, i, 0)
            g["live_year"] = np.where(ok, r.start_year.values[ii], np.nan)
            g["live_end"] = np.where(ok, r.end_year.values[ii], np.nan)
            rr = _roll(g.fid.values).reindex(g.fid.values)
            ry, rs = [], []
            for k in ("public", "third_party", "commercial", "historic"):
                ry.append(rr[f"year_{k}"].values)
                rs.append(rr[f"src_{k}"].values)
            ry = np.array(ry, dtype=float)
            rs = np.array(rs, dtype=object)
            first = np.argmax(np.isfinite(ry) & (ry > 0), axis=0)
            g["roll_year"] = np.where(np.isfinite(ry[first, np.arange(len(g))]), ry[first, np.arange(len(g))], np.nan)
            g["roll_src"] = rs[first, np.arange(len(g))]
            g["src"] = "region"
            frames.append(g)
    sb = (SF_BOX[0] < b[2]) and (SF_BOX[2] > b[0]) and (SF_BOX[1] < b[3]) and (SF_BOX[3] > b[1])
    if sb:
        s = _sf()
        s = s.cx[b[0] - pad:b[2] + pad, b[1] - pad:b[3] + pad]
        s = s[shapely.contains(sel, s.geometry.representative_point().values)]
        if len(s):
            frames.append(gpd.GeoDataFrame({"fid": "sf:" + s.sf16_bldgid.astype(str).values,
                                            "live_year": s.start_year.values, "live_end": s.end_year.values,
                                            "roll_year": s.raw_year.values, "roll_src": s.year_source.values,
                                            "src": "sf"}, geometry=s.geometry.values, crs=4326))
    if not frames:
        return gpd.GeoDataFrame(columns=["fid", "src", "live_year", "live_end", "roll_year", "roll_src",
                                         "area_m2", "circ", "geometry"], geometry="geometry", crs=4326)
    out = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), geometry="geometry", crs=4326)
    out = out.explode(index_parts=False).reset_index(drop=True)
    out = out[out.geom_type == "Polygon"].reset_index(drop=True)
    u = out.to_crs(32610).geometry
    out["area_m2"] = u.area.values
    out["circ"] = _circ(u.values)
    return out
