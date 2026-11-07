"""Stage: parks, woods and beaches (ground cover) + woodland trees.

Inputs
  * SF Rec & Park "RPD Parks" polygons (DataSF 3nje-yn2u)
  * data/tables/parks.csv — researched creation year per park (name-matched)
  * Overture base theme (OSM): `land` wood/forest + beach/sand, `land_use` parks
    (covers federal parkland — Presidio, Crissy Field, Lands End — not in RPD)

Dating
  * a park appears in its researched `start_year` (confidence from the table);
    undated parks are omitted rather than guessed
  * woods inside a dated park: park year + 3 (estimated); Golden Gate Park woods
    follow the documented east-to-west reclamation (east third 1871–80, middle
    third 1880–95, west third 1895–1910; data/research/landmarks.md "Golden Gate
    Park"), interpolated by longitude (estimated); Lands End was treeless until
    the 1930s planting (Wikipedia) -> 1935
  * beaches/sand: natural, always present

Woodland trees: real wood extents (OSM), but individual positions are a
deterministic jittered grid (confidence = procedural) — no per-tree survey
exists for SF's park forests.

Outputs: viewer/public/data/sf-ground.json, viewer/public/data/sf-woods.bin.gz
"""
from __future__ import annotations

import csv
import glob
import json

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import mapping

from common import RAW, TABLES, VIEWER_DATA, log
from download_overture import RELEASE
from export_columnar import write_columnar

UTM = "EPSG:32610"
ORIGIN = (-122.44, 37.76)
# Golden Gate Park planting front: (longitude, year) — research synthesis, medium confidence
GGP_FRONT = [(-122.4545, 1872.0), (-122.4720, 1880.0), (-122.4920, 1895.0), (-122.5105, 1908.0)]
LANDS_END = (-122.515, 37.776, -122.495, 37.792)


def load_parks_table() -> dict[str, dict]:
    p = TABLES / "parks.csv"
    if not p.exists():
        log("ground: WARNING data/tables/parks.csv missing — no parks will be dated")
        return {}
    out = {}
    for r in csv.DictReader(open(p)):
        try:
            y = float(r["start_year"])
        except (TypeError, ValueError):
            continue
        out[r["name"].strip().lower()] = {
            "start": y,
            "end": float(r.get("end_year") or 9999) if (r.get("end_year") or "").strip() else 9999.0,
            "confidence": (r.get("confidence") or "estimated").strip(),
            "source": r.get("source_url", ""),
        }
    return out


def main():
    table = load_parks_table()
    rpd = gpd.GeoDataFrame(pd.concat([gpd.read_file(p) for p in glob.glob(str(RAW / "sf_rpd_parks" / "page-*.geojson"))]), crs=4326)
    rpd["key"] = rpd.map_park_n.str.strip().str.lower()
    rpd = rpd.join(pd.DataFrame.from_dict(table, orient="index"), on="key")
    dated = rpd[rpd.start.notna()].copy()
    log(f"ground: {len(rpd)} RPD parks, {len(dated)} dated from parks.csv")

    land = gpd.read_parquet(RAW / "overture" / RELEASE / "base_land.parquet")
    land_use = gpd.read_parquet(RAW / "overture" / RELEASE / "base_land_use.parquet")
    for g in (land, land_use):
        if g.crs is None:
            g.set_crs(4326, inplace=True)

    feats = []

    def add(geom, props):
        geom = shapely.set_precision(geom, 1e-6)
        if not geom.is_empty:
            feats.append({"type": "Feature", "properties": props, "geometry": mapping(geom)})

    for _, r in dated.iterrows():
        add(r.geometry, {"kind": "park", "name": r.map_park_n, "start_year": r.start, "end_year": r.end,
                         "year_confidence": r.confidence, "source": "rpd_parks+parks.csv"})

    # federal parkland (not in RPD) dated in parks.csv by name
    named = land_use[(land_use.subtype == "park") & land_use.name.notna()].copy()
    named["key"] = named.name.str.strip().str.lower()
    for _, r in named.iterrows():
        t = table.get(r.key)
        if t is None or r.key in set(dated.key):
            continue
        add(r.geometry, {"kind": "park", "name": r["name"], "start_year": t["start"], "end_year": t["end"],
                         "year_confidence": t["confidence"], "source": "osm_via_overture+parks.csv"})

    # beaches / sand: natural ground, always present
    for _, r in land[land["class"].isin(["beach", "sand"])].iterrows():
        add(r.geometry, {"kind": "sand", "start_year": -10000, "end_year": 9999, "year_confidence": "exact", "source": "osm_via_overture"})

    # woods
    woods = land[land["class"].isin(["wood", "forest"])].to_crs(UTM).copy()
    parks_utm = gpd.GeoDataFrame(
        [{"start": f["properties"]["start_year"], "name": f["properties"].get("name"), "geometry": shapely.geometry.shape(f["geometry"])}
         for f in feats if f["properties"]["kind"] == "park"], crs=4326).to_crs(UTM) if feats else None
    presidio_year = table.get("presidio forest", {}).get("start")
    wood_years = []
    for _, w in woods.iterrows():
        c = w.geometry.representative_point()
        lon, lat = gpd.GeoSeries([c], crs=UTM).to_crs(4326).iloc[0].coords[0]
        year = None
        if parks_utm is not None:
            hit = parks_utm[parks_utm.contains(c)]
            if len(hit):
                name = (hit.iloc[0]["name"] or "").lower()
                if "golden gate park" in name:
                    xs_, ys_ = zip(*GGP_FRONT)
                    year = float(np.interp(-lon, [-x for x in xs_], ys_))
                else:
                    year = float(hit.start.min()) + 3
        if LANDS_END[0] < lon < LANDS_END[2] and LANDS_END[1] < lat < LANDS_END[3] and (year is None or year > 1935):
            year = 1935.0
        if year is None and presidio_year and -122.485 < lon < -122.445 and 37.785 < lat < 37.812:
            year = presidio_year + 2
        wood_years.append(year)
    woods["year"] = wood_years
    woods = woods[woods.year.notna()]
    for _, w in woods.iterrows():
        add(gpd.GeoSeries([w.geometry], crs=UTM).to_crs(4326).iloc[0],
            {"kind": "wood", "start_year": float(w.year), "end_year": 9999, "year_confidence": "estimated", "source": "osm_via_overture"})
    log(f"ground: {sum(f['properties']['kind'] == 'park' for f in feats)} parks, {len(woods)} dated woods, "
        f"{sum(f['properties']['kind'] == 'sand' for f in feats)} sand polygons")
    out = VIEWER_DATA / "sf-ground.json"
    out.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")))
    log(f"ground: wrote {out} ({out.stat().st_size / 1e6:.2f} MB)")

    # ---- woodland trees: jittered grid inside real wood extents
    rng = np.random.default_rng(1906)
    xs, ys, yrs = [], [], []
    spacing = 7.5
    for _, w in woods.iterrows():
        g = w.geometry
        minx, miny, maxx, maxy = g.bounds
        gx, gy = np.meshgrid(np.arange(minx, maxx, spacing), np.arange(miny, maxy, spacing))
        px = gx.ravel() + rng.uniform(-2.8, 2.8, gx.size)
        py = gy.ravel() + rng.uniform(-2.8, 2.8, gy.size)
        inside = shapely.contains_xy(g, px, py)
        xs.append(px[inside])
        ys.append(py[inside])
        yrs.append(np.full(inside.sum(), w.year) + rng.uniform(0, 4, inside.sum()))
    xs, ys, yrs = np.concatenate(xs), np.concatenate(ys), np.concatenate(yrs)
    ll = gpd.GeoSeries(gpd.points_from_xy(xs, ys), crs=UTM).to_crs(4326)
    n = len(ll)
    q = np.rint((np.column_stack([ll.x.values, ll.y.values]) - ORIGIN) * 1e7).astype(np.int32)
    # SF park forests: Monterey cypress / pine (conifer) and blue gum eucalyptus (broadleaf, tall)
    form = (rng.uniform(size=n) < 0.55).astype(np.uint8)  # 1 = conifer
    height = np.where(form == 1, rng.uniform(12, 24, n), rng.uniform(18, 32, n)).astype(np.float32)
    crown = np.where(form == 1, rng.uniform(3.5, 5.5, n), rng.uniform(3.0, 4.5, n)).astype(np.float32)
    cols = {
        "position_q|shuffle": q.ravel(),
        "start_year": yrs.astype(np.float32),
        "height": height,
        "crown": crown,
        "form": form,
        "confidence": np.full(n, 2, np.uint8),
    }
    out = VIEWER_DATA / "sf-woods.bin.gz"
    _, gz = write_columnar(out, cols, origin=ORIGIN, counts={"features": n},
                           meta={"position_scale": 1e-7, "forms": ["broadleaf", "conifer", "palm"],
                                 "source": "OSM wood extents via Overture; positions procedural"})
    log(f"ground: wrote {out} ({n} woodland trees, {gz / 1e6:.1f} MB gz)")


if __name__ == "__main__":
    main()
