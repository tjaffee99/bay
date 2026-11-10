"""Stage: Overture Maps buildings + building parts for San Francisco.

Overture's buildings theme is largely OpenStreetMap (ODbL) plus ML-derived
footprints; `building_part` carries OSM's hand-modelled 3D parts (setbacks,
towers, domes) with height/min_height. We use it for:
  * buildings built after the 2016 DataSF footprint snapshot,
  * real stepped/tiered shapes for towers instead of one flat extrusion,
  * height fallback.

Output: data/raw/overture/<release>/{building,building_part}.parquet
"""
from __future__ import annotations

import duckdb

from common import RAW, log

RELEASE = "2026-10-21.0"
# SF city + a margin (Treasure Island, Daly City edge)
BBOX = (-122.53, 37.70, -122.35, 37.835)


def main():
    out_dir = RAW / "overture" / RELEASE
    out_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
    # The bucket is public: use an explicit anonymous secret so DuckDB doesn't
    # pick up unrelated AWS_* credentials from the environment.
    con.execute("CREATE OR REPLACE SECRET overture (TYPE s3, PROVIDER config, KEY_ID '', SECRET '', REGION 'us-west-2');")
    xmin, ymin, xmax, ymax = BBOX
    for typ in ("building", "building_part"):
        out = out_dir / f"{typ}.parquet"
        if out.exists():
            log(f"overture {typ}: cached")
            continue
        src = f"s3://overturemaps-us-west-2/release/{RELEASE}/theme=buildings/type={typ}/*"
        extra = "building_id," if typ == "building_part" else "has_parts, subtype, class,"
        q = f"""
        COPY (
          SELECT id, {extra} names.primary AS name, height, min_height, num_floors,
                 min_floor, roof_shape, roof_height, facade_color, roof_color,
                 sources[1].dataset AS source_dataset, sources[1].record_id AS source_record,
                 geometry
          FROM read_parquet('{src}', hive_partitioning=1)
          WHERE bbox.xmin < {xmax} AND bbox.xmax > {xmin}
            AND bbox.ymin < {ymax} AND bbox.ymax > {ymin}
        ) TO '{out}' (FORMAT parquet);
        """
        log(f"overture {typ}: querying {src}")
        con.execute(q)
        n = con.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
        log(f"overture {typ}: {n} rows -> {out}")


def base_theme():
    """OSM-derived natural land (wood, scrub, sand…) and land use (parks, golf…)."""
    out_dir = RAW / "overture" / RELEASE
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
    con.execute("CREATE OR REPLACE SECRET overture (TYPE s3, PROVIDER config, KEY_ID '', SECRET '', REGION 'us-west-2');")
    xmin, ymin, xmax, ymax = BBOX
    for typ in ("land", "land_use"):
        out = out_dir / f"base_{typ}.parquet"
        if out.exists():
            continue
        src = f"s3://overturemaps-us-west-2/release/{RELEASE}/theme=base/type={typ}/*"
        con.execute(f"""
        COPY (
          SELECT id, subtype, class, names.primary AS name, geometry
          FROM read_parquet('{src}', hive_partitioning=1)
          WHERE bbox.xmin < {xmax} AND bbox.xmax > {xmin} AND bbox.ymin < {ymax} AND bbox.ymax > {ymin}
            AND ST_GeometryType(geometry) IN ('POLYGON', 'MULTIPOLYGON')
        ) TO '{out}' (FORMAT parquet);""")
        n = con.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
        log(f"overture base {typ}: {n} polygons -> {out}")


# Box around the ten-county map (pipeline/extent.py; 2026-11 expansion: Sonoma, Napa, Solano,
# Santa Cruz and the whole of Contra Costa / Santa Clara). roads.py REGION_BBOX_ROADS must match.
REGION_BBOX = (-123.68, 36.78, -121.16, 38.91)
_BOX = "bbox.xmin < {2} AND bbox.xmax > {0} AND bbox.ymin < {3} AND bbox.ymax > {1}"
# region extracts cut by REGION_BBOX: file -> (theme/type, columns, extra condition)
REGION_EXTRACTS = {
    # motorways, trunks and their ramps with the attributes that place them in 3D: subclass
    # (link = ramp), road_flags (is_bridge / is_tunnel over a fraction of the segment),
    # level_rules (stacking level) and connectors (graph)
    "freeways": ("transportation/type=segment",
                 "id, class, subclass, names.primary AS name, road_flags, level_rules, connectors, geometry",
                 "subtype = 'road' AND class IN ('motorway', 'trunk')"),
    # rail segments (subway = BART, light_rail = Muni Metro / VTA, tram = F line and cable
    # cars, standard_gauge ...) with rail_flags and level_rules: the real tracks for transit.py
    "rail": ("transportation/type=segment",
             "id, class, subclass, names.primary AS name, rail_flags, level_rules, connectors, geometry",
             "subtype = 'rail'"),
    # residential streets, living streets, unclassified lanes and alleys: the street grid of
    # the suburbs, dated in roads.py by the buildings along each street
    "roads_local": ("transportation/type=segment",
                    "id, class, subclass, names.primary AS name, road_flags, geometry",
                    "subtype = 'road' AND (class IN ('residential', 'living_street', 'unclassified') "
                    "OR (class = 'service' AND subclass = 'alley'))"),
    # main roads (tertiary and up) of the region: roads.py region roads, farmstead / Sanborn control
    "roads_region": ("transportation/type=segment",
                     "id, class, subtype, names.primary AS name, road_flags, geometry",
                     "subtype = 'road' AND class IN ('motorway', 'trunk', 'primary', 'secondary', 'tertiary')"),
    # OSM aerodromes, runways, taxiways, aprons (points, lines, polygons): airports.py
    "region_airports": ("base/type=infrastructure",
                        "id, subtype, class, names.primary AS name, geometry", "subtype = 'airport'"),
    # OSM land use polygons (parks, golf, campuses, cemeteries, farmland ...) of the region; the
    # name is from the five-county pass: ground_detail.py, terrain_tiles.py, region_buildings.py
    "region5_land_use": ("base/type=land_use",
                         "id, subtype, class, names.primary AS name, geometry",
                         "ST_GeometryType(geometry) IN ('POLYGON', 'MULTIPOLYGON')"),
}


def region_extract(name: str, refetch: bool = False):
    """One region extract. A re-fetch (the box grew) writes beside the cached file and
    replaces it only when the new file holds at least the old rows, so a build running
    meanwhile never sees a missing or partial file."""
    import os
    out = RAW / "overture" / RELEASE / f"{name}.parquet"
    if out.exists() and not refetch:
        log(f"overture {name}: cached")
        return
    theme, cols, cond = REGION_EXTRACTS[name]
    stage = out.with_name(f"_stage_{name}.parquet")
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
    con.execute("CREATE OR REPLACE SECRET overture (TYPE s3, PROVIDER config, KEY_ID '', SECRET '', REGION 'us-west-2');")
    src = f"s3://overturemaps-us-west-2/release/{RELEASE}/theme={theme}/*"
    con.execute(f"""
    COPY (
      SELECT {cols}
      FROM read_parquet('{src}', hive_partitioning=1)
      WHERE {_BOX.format(*REGION_BBOX)} AND {cond}
    ) TO '{stage}' (FORMAT parquet);""")
    n = con.execute(f"SELECT count(*) FROM '{stage}'").fetchone()[0]
    if out.exists():
        old, lost = con.execute(f"""SELECT count(*), count(*) FILTER (WHERE id NOT IN (SELECT id FROM '{stage}'))
                                    FROM '{out}'""").fetchone()
        if lost > 0.001 * old:
            raise RuntimeError(f"overture {name}: new extract lacks {lost} of the {old} cached rows; kept {out}, see {stage}")
        log(f"overture {name}: {old} cached rows, {lost} not in the new extract")
    os.replace(stage, out)
    log(f"overture {name}: {n} rows -> {out}")


def freeways():
    region_extract("freeways")


def rail():
    region_extract("rail")


def local_roads():
    region_extract("roads_local")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "local_roads":
        local_roads()
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] in ("region", "refetch"):   # refetch: REGION_BBOX changed
        for name in (sys.argv[2:] or REGION_EXTRACTS):
            region_extract(name, refetch=sys.argv[1] == "refetch")
        sys.exit(0)
    main()
    base_theme()
    for name in REGION_EXTRACTS:
        region_extract(name)
