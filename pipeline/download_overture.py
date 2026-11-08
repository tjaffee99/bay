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


REGION_BBOX = (-123.2, 36.85, -121.2, 38.9)


def freeways():
    """Motorways, trunks and their ramps for the whole region, with the attributes that
    place them in 3D: subclass (link = ramp), road_flags (is_bridge / is_tunnel over a
    fraction of the segment), level_rules (stacking level) and connectors (graph)."""
    out = RAW / "overture" / RELEASE / "freeways.parquet"
    if out.exists():
        log("overture freeways: cached")
        return
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
    con.execute("CREATE OR REPLACE SECRET overture (TYPE s3, PROVIDER config, KEY_ID '', SECRET '', REGION 'us-west-2');")
    xmin, ymin, xmax, ymax = REGION_BBOX
    src = f"s3://overturemaps-us-west-2/release/{RELEASE}/theme=transportation/type=segment/*"
    con.execute(f"""
    COPY (
      SELECT id, class, subclass, names.primary AS name, road_flags, level_rules, connectors, geometry
      FROM read_parquet('{src}', hive_partitioning=1)
      WHERE bbox.xmin < {xmax} AND bbox.xmax > {xmin} AND bbox.ymin < {ymax} AND bbox.ymax > {ymin}
        AND subtype = 'road' AND class IN ('motorway', 'trunk')
    ) TO '{out}' (FORMAT parquet);""")
    n = con.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
    log(f"overture freeways: {n} segments -> {out}")


def rail():
    """Rail segments (subway = BART, light_rail = Muni Metro / VTA, tram = F line and
    cable cars, standard_gauge …) with rail_flags (is_bridge / is_tunnel) and level_rules:
    the real track geometry for transit.py."""
    out = RAW / "overture" / RELEASE / "rail.parquet"
    if out.exists():
        log("overture rail: cached")
        return
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
    con.execute("CREATE OR REPLACE SECRET overture (TYPE s3, PROVIDER config, KEY_ID '', SECRET '', REGION 'us-west-2');")
    xmin, ymin, xmax, ymax = REGION_BBOX
    src = f"s3://overturemaps-us-west-2/release/{RELEASE}/theme=transportation/type=segment/*"
    con.execute(f"""
    COPY (
      SELECT id, class, subclass, names.primary AS name, rail_flags, level_rules, connectors, geometry
      FROM read_parquet('{src}', hive_partitioning=1)
      WHERE bbox.xmin < {xmax} AND bbox.xmax > {xmin} AND bbox.ymin < {ymax} AND bbox.ymax > {ymin}
        AND subtype = 'rail'
    ) TO '{out}' (FORMAT parquet);""")
    n = con.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
    log(f"overture rail: {n} segments -> {out}")


def local_roads():
    """Residential streets, living streets, unclassified lanes and alleys for the whole
    region (the region road file only has tertiary and up): the street grid of the
    suburbs, dated in roads.py by the buildings along each street."""
    out = RAW / "overture" / RELEASE / "roads_local.parquet"
    if out.exists():
        log("overture local roads: cached")
        return
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
    con.execute("CREATE OR REPLACE SECRET overture (TYPE s3, PROVIDER config, KEY_ID '', SECRET '', REGION 'us-west-2');")
    xmin, ymin, xmax, ymax = REGION_BBOX
    src = f"s3://overturemaps-us-west-2/release/{RELEASE}/theme=transportation/type=segment/*"
    con.execute(f"""
    COPY (
      SELECT id, class, subclass, names.primary AS name, road_flags, geometry
      FROM read_parquet('{src}', hive_partitioning=1)
      WHERE bbox.xmin < {xmax} AND bbox.xmax > {xmin} AND bbox.ymin < {ymax} AND bbox.ymax > {ymin}
        AND subtype = 'road'
        AND (class IN ('residential', 'living_street', 'unclassified') OR (class = 'service' AND subclass = 'alley'))
    ) TO '{out}' (FORMAT parquet);""")
    n = con.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
    log(f"overture local roads: {n} segments -> {out}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "local_roads":
        local_roads()
        sys.exit(0)
    main()
    base_theme()
    freeways()
    rail()
    local_roads()
