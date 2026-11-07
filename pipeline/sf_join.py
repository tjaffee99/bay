"""Stage: join SF building footprints -> parcels -> assessor roll.

Footprints (DataSF ynuv-fyni, 2016 snapshot with 2010 LiDAR heights) carry
`mblr` = "SF" + block/lot of the parcel they sit on. The assessor roll is per
*unit* parcel (condos have one record per unit), so records are grouped by
their *map* parcel (`mapblklot` from the parcels dataset) before joining.

Footprints whose key finds no assessor record fall back to a spatial join
(footprint centroid within an active parcel).

Output: data/interim/sf_joined.parquet (GeoParquet, EPSG:4326), one row per
footprint with aggregated assessor fields:
  years        list of non-zero year_property_built values on the map parcel
  stories      max number_of_stories, units  sum of number_of_units
  use_code     most common use code, n_records  number of assessor records
  match        'key' | 'spatial' | 'none'
"""
from __future__ import annotations

import glob
import json
from collections import Counter

import geopandas as gpd
import numpy as np
import pandas as pd

from common import INTERIM, RAW, log
from download_sf import ROLL_YEAR

OUT = INTERIM / "sf_joined.parquet"


def read_pages(pattern: str) -> gpd.GeoDataFrame:
    frames = [gpd.read_file(p) for p in sorted(glob.glob(pattern))]
    return gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=4326)


def read_assessor() -> pd.DataFrame:
    rows = []
    for p in sorted(glob.glob(str(RAW / f"sf_assessor_{ROLL_YEAR}" / "page-*.json"))):
        rows.extend(json.load(open(p)))
    df = pd.DataFrame(rows)
    for c in ("year_property_built", "number_of_stories", "number_of_units", "property_area"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _mode(df: pd.DataFrame, col: str) -> pd.Series:
    """Most common non-null value of `col` per mapblklot (ties -> alphabetical)."""
    c = df.dropna(subset=[col]).groupby(["mapblklot", col]).size().reset_index(name="n")
    c = c.sort_values(["mapblklot", "n", col], ascending=[True, False, True])
    return c.drop_duplicates("mapblklot").set_index("mapblklot")[col]


def aggregate(asr: pd.DataFrame) -> pd.DataFrame:
    g = asr.groupby("mapblklot")
    out = pd.DataFrame({"n_records": g.size()})
    out["years"] = asr.dropna(subset=["year"]).groupby("mapblklot").year.apply(lambda v: [int(x) for x in v])
    out["years"] = out["years"].apply(lambda v: v if isinstance(v, list) else [])
    out["stories"] = g.number_of_stories.max()
    out["units"] = g.number_of_units.sum()
    for col, name in (("use_code", "use_code"), ("use_definition", "use_definition"),
                      ("property_class_code_definition", "class_definition"),
                      ("property_location", "address")):
        out[name] = _mode(asr, col)
    return out


def main():
    log("join: reading footprints")
    fp = read_pages(str(RAW / "sf_footprints" / "page-*.geojson"))
    n_all = len(fp)
    fp = fp[fp.mblr.fillna("").str.startswith("SF")].copy()
    log(f"join: {n_all} footprints, {len(fp)} in San Francisco (others are San Mateo Co.)")
    fp["blklot"] = fp.mblr.str[2:]
    for c in ("hgt_median_m", "peak_1st_m", "gnd_min_m"):
        fp[c] = pd.to_numeric(fp[c], errors="coerce")
    fp["hgt_max_m"] = pd.to_numeric(fp["hgt_maxcm"], errors="coerce") / 100.0
    fp = fp.drop(columns=["hgt_maxcm"])

    log("join: reading parcels")
    parcels = read_pages(str(RAW / "sf_parcels" / "page-*.geojson"))
    to_map = dict(zip(parcels.blklot, parcels.mapblklot))

    log("join: reading assessor roll")
    asr = read_assessor()
    asr["mapblklot"] = asr.parcel_number.map(to_map).fillna(asr.parcel_number)
    asr["year"] = asr.year_property_built.where(asr.year_property_built > 0)

    log("join: aggregating assessor records per map parcel")
    by_map = aggregate(asr)
    by_map.to_parquet(INTERIM / "sf_assessor_by_map.parquet")
    log(f"join: {len(asr)} assessor records -> {len(by_map)} map parcels")

    fp["mapblklot"] = fp.blklot.map(to_map).fillna(fp.blklot)
    fp["match"] = np.where(fp.mapblklot.isin(by_map.index), "key", "none")

    # Spatial fallback: centroid within an *active* parcel that has records.
    miss = fp.match == "none"
    log(f"join: {miss.sum()} footprints without key match; trying spatial")
    active = parcels[(parcels.active.astype(str).str.lower() == "true") & parcels.mapblklot.isin(by_map.index)]
    active = active[["mapblklot", "geometry"]].drop_duplicates("mapblklot")
    pts = gpd.GeoDataFrame({"idx": fp.index[miss]}, geometry=fp.loc[miss].geometry.representative_point(), crs=4326)
    hit = gpd.sjoin(pts, active, predicate="within", how="inner").drop_duplicates("idx")
    fp.loc[hit.idx.values, "mapblklot"] = hit.mapblklot.values
    fp.loc[hit.idx.values, "match"] = "spatial"

    fp = fp.join(by_map, on="mapblklot")
    fp["years"] = fp["years"].apply(lambda v: v if isinstance(v, list) else [])
    counts = fp.match.value_counts().to_dict()
    log(f"join: match counts {counts}")
    fp = fp.reset_index(drop=True)
    fp.to_parquet(OUT)
    log(f"join: wrote {OUT} ({len(fp)} rows)")


if __name__ == "__main__":
    main()
