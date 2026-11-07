"""Stage: San Francisco street trees -> viewer binary.

Real positions from DataSF's Street Tree List (DPW). Year planted:
  * `planteddate` when recorded (~27 %) -> exact
  * otherwise estimated from trunk diameter: urban street trees add roughly
    0.35 in of DBH per year, so age ≈ DBH / 0.35 (capped at 120 years) — but
    never earlier than the median start year of the 5 nearest buildings
    (street trees follow development) -> estimated
Size: height and crown radius from DBH (rough allometry, clamped).
Form: palm / conifer / broadleaf from the species name.

Output: viewer/public/data/sf-trees.bin.gz
"""
from __future__ import annotations

import glob
import json
import re

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from common import CURRENT_YEAR, INTERIM, RAW, VIEWER_DATA, log
from export_columnar import write_columnar

ORIGIN = (-122.44, 37.76)
DATA_YEAR = 2026  # DBH values are current as of the dataset snapshot
PALM = re.compile(r"palm|phoenix|washingtonia|syagrus|trachycarpus|archontophoenix|butia|cordyline|dracaena|dracena", re.I)
CONIFER = re.compile(r"pinus|pine|cupressus|cypress|sequoia|redwood|cedrus|cedar|araucaria|podocarpus|juniper|abies|picea|spruce", re.I)


def main():
    rows = []
    for p in sorted(glob.glob(str(RAW / "sf_street_trees" / "page-*.json"))):
        rows.extend(json.load(open(p)))
    df = pd.DataFrame(rows)
    df["lat"] = pd.to_numeric(df.latitude, errors="coerce")
    df["lon"] = pd.to_numeric(df.longitude, errors="coerce")
    df = df[df.lat.between(37.70, 37.84) & df.lon.between(-122.53, -122.35)].copy()
    df["dbh"] = pd.to_numeric(df.mapdbh, errors="coerce").clip(0, 80)
    df["planted"] = pd.to_numeric(df.planteddate.fillna("").str[:4], errors="coerce")
    log(f"trees: {len(df)} located trees, {df.planted.notna().sum()} with planting dates")

    # nearest buildings' start year as a lower bound
    b = gpd.read_parquet(INTERIM / "sf_buildings.parquet")
    bc = b.geometry.representative_point().to_crs(32610)
    pts = gpd.GeoSeries(gpd.points_from_xy(df.lon, df.lat), crs=4326).to_crs(32610)
    tree = cKDTree(np.column_stack([bc.x, bc.y]))
    _, idx = tree.query(np.column_stack([pts.x, pts.y]), k=5)
    street_year = np.median(b.start_year.values[idx], axis=1)

    age = (df.dbh.fillna(0).values / 0.35).clip(0, 120)
    from_dbh = DATA_YEAR - age
    est = np.where(df.dbh.fillna(0).values > 0, np.maximum(from_dbh, street_year + 2), street_year + 10)
    year = np.where(df.planted.notna(), df.planted.values, est)
    year = np.minimum(year, CURRENT_YEAR)
    conf = np.where(df.planted.notna(), 0, 1).astype(np.uint8)

    dbh = df.dbh.fillna(6).values
    height = np.clip(3.0 + 0.32 * dbh, 3.0, 24.0)
    crown = np.clip(1.0 + 0.13 * dbh, 1.0, 7.0)
    sp = df.species.fillna("")
    form = np.where(sp.str.contains(PALM), 2, np.where(sp.str.contains(CONIFER), 1, 0)).astype(np.uint8)

    # deterministic jitter of the fractional year so plantings don't all pop at once
    h = (df.treeid.astype(str).map(lambda s: (hash(s) & 0xFFFF) / 65535.0)).values
    q = np.rint((np.column_stack([df.lon.values, df.lat.values]) - ORIGIN) * 1e7).astype(np.int32)
    cols = {
        "position_q|shuffle": q.ravel(),
        "start_year": (np.floor(year) + 0.9 * h).astype(np.float32),
        "height": height.astype(np.float32),
        "crown": crown.astype(np.float32),
        "form": form,
        "confidence": conf,
    }
    out = VIEWER_DATA / "sf-trees.bin.gz"
    raw, gz = write_columnar(out, cols, origin=ORIGIN, counts={"features": int(len(df))},
                             meta={"position_scale": 1e-7, "forms": ["broadleaf", "conifer", "palm"],
                                   "source": "DataSF Street Tree List (tkzw-k3nq), PDDL"})
    log(f"trees: wrote {out} ({len(df)} trees, {gz / 1e6:.1f} MB gz); forms {np.bincount(form).tolist()}")


if __name__ == "__main__":
    main()
