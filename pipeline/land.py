"""Stage: modern land polygon for the viewer (Phase 0/1 ground).

TIGER/Line county polygons extend out into the bay/ocean to the county line;
subtracting TIGER "area water" polygons leaves a detailed modern shoreline
(plus holes for lakes and reservoirs). In Phase 2 this becomes one time slice of
the time-varying land/water model.

Output: viewer/public/data/sf-land.json  (GeoJSON, WGS84, simplified ~2 m)
        data/interim/land_modern.fgb     (full-detail, for QGIS)
"""
from __future__ import annotations

import json

import geopandas as gpd
import shapely
from shapely.geometry import box, mapping

from common import INTERIM, RAW, VIEWER_DATA, log
from download_sf import BAY_COUNTIES

# Area of interest for now: San Francisco plus the shores visible from it.
AOI = box(-122.66, 37.62, -122.15, 37.93)
UTM = "EPSG:32610"  # metres, for simplification and area thresholds


def main():
    out = VIEWER_DATA / "sf-land.json"
    counties = gpd.read_file(f"zip://{RAW / 'tiger' / 'tl_2024_us_county.zip'}")
    counties = counties[(counties.STATEFP + counties.COUNTYFP).isin(BAY_COUNTIES)]
    # San Mateo matters for the southern edge of SF; also include neighbouring
    # county outlines intersecting the AOI.
    counties = counties.to_crs(4326)
    counties = counties[counties.intersects(AOI)]
    land = shapely.union_all(counties.geometry.values).intersection(AOI)

    waters = []
    for fips in BAY_COUNTIES:
        w = gpd.read_file(f"zip://{RAW / 'tiger' / f'tl_2024_{fips}_areawater.zip'}").to_crs(4326)
        w = w[w.intersects(AOI)]
        waters.append(w)
    water = gpd.GeoDataFrame(pd_concat(waters), crs=4326)
    water_m = water.to_crs(UTM)
    # Ignore tiny ponds/swimming-pool-size features: they just add noise.
    water = water[water_m.area > 1500]
    log(f"land: {len(counties)} counties, {len(water)} water polygons")
    land = land.difference(shapely.union_all(water.geometry.values))

    g = gpd.GeoSeries([land], crs=4326).explode(index_parts=False).to_crs(UTM)
    g = g[g.area > 5000]  # drop slivers and rocks
    INTERIM.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame(geometry=g.to_crs(4326)).to_file(INTERIM / "land_modern.fgb", driver="FlatGeobuf")
    g = g.simplify(2.0).to_crs(4326)

    def rounded(geom):
        return shapely.set_precision(geom, 1e-6)

    features = [{"type": "Feature", "properties": {"kind": "land", "start_year": -10000,
                                                    "end_year": 9999, "source": "tiger2024"},
                 "geometry": mapping(rounded(geom))} for geom in g if not geom.is_empty]
    out.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                              separators=(",", ":")))
    log(f"land: wrote {out} ({out.stat().st_size / 1e6:.2f} MB, {len(features)} polygons)")


def pd_concat(frames):
    import pandas as pd
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    main()
