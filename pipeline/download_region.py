"""Stage: data foundation for the five-county expansion (Phase 5).

Counties: Marin (041), Contra Costa (013), Alameda (001), San Mateo (081), Santa Clara (085).

  overture   Overture Maps buildings + building parts clipped to the five counties
             -> data/raw/overture/<release>/region5_{building,building_part}.parquet
  years      public per-parcel / per-building year-built sources (county assessors,
             city open data) -> data/raw/region_years/<source>/ (raw, untouched)
  normalise  -> data/interim/region_years.parquet (one row per parcel/building,
             year_built int, effective year, units, stories, source, county, geometry 4326)
  coverage   join region_years to the Overture footprints -> data/interim/reports/
             region_years_coverage.json + histogram per source

Usage: python download_region.py [overture|years|normalise|coverage|all]
Research notes, licences and coverage numbers: data/research/region_buildings.md.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import shapely

from common import INTERIM, RAW, log

RELEASE = "2026-10-21.0"
STATEFP = "06"
COUNTIES = {"041": "Marin", "013": "Contra Costa", "001": "Alameda", "081": "San Mateo", "085": "Santa Clara"}
OUT_OVERTURE = RAW / "overture" / RELEASE
YEARS_RAW = RAW / "region_years"
REPORTS = INTERIM / "reports"


def county_polygons():
    """{COUNTYFP: shapely geometry} from TIGER 2024 (NAD83 ~ WGS84 within ~1 m here).
    The TIGER outlines include each county's share of the bay, so piers and fill count."""
    import geopandas as gpd
    c = gpd.read_file(f"zip://{RAW / 'tiger' / 'tl_2024_us_county.zip'}")
    c = c[(c.STATEFP == STATEFP) & c.COUNTYFP.isin(list(COUNTIES))]
    return {r.COUNTYFP: r.geometry for r in c.itertuples()}


def assign_county(x: np.ndarray, y: np.ndarray, polys: dict) -> np.ndarray:
    out = np.full(len(x), "", dtype=object)
    for fp, g in polys.items():
        shapely.prepare(g)
        inside = shapely.contains_xy(g, x, y) & (out == "")
        out[inside] = fp
    return out


def duck():
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
    # public bucket: explicit anonymous secret so DuckDB ignores unrelated AWS_* variables
    con.execute("CREATE OR REPLACE SECRET overture (TYPE s3, PROVIDER config, KEY_ID '', SECRET '', REGION 'us-west-2');")
    return con


# ---------------------------------------------------------------------------
# 1. Overture footprints
# ---------------------------------------------------------------------------

def overture():
    polys = county_polygons()
    xmin, ymin, xmax, ymax = shapely.union_all(list(polys.values())).bounds
    OUT_OVERTURE.mkdir(parents=True, exist_ok=True)
    con = duck()
    for typ in ("building", "building_part"):
        out = OUT_OVERTURE / f"region5_{typ}.parquet"
        if out.exists():
            log(f"overture region5 {typ}: cached")
            continue
        stage = OUT_OVERTURE / f"_stage_region5_{typ}.parquet"
        src = f"s3://overturemaps-us-west-2/release/{RELEASE}/theme=buildings/type={typ}/*"
        extra = "building_id," if typ == "building_part" else "has_parts, subtype, class,"
        if not stage.exists():
            log(f"overture region5 {typ}: querying {src} bbox {xmin:.3f},{ymin:.3f},{xmax:.3f},{ymax:.3f}")
            con.execute(f"""
            COPY (
              SELECT id, {extra} names.primary AS name, level, is_underground,
                     height, min_height, num_floors, num_floors_underground, min_floor,
                     roof_shape, roof_height, roof_direction, roof_orientation,
                     facade_color, facade_material, roof_color, roof_material,
                     sources[1].dataset AS source_dataset,
                     sources[1].record_id AS source_record,
                     sources[1].update_time AS source_update_time,
                     sources[1].confidence AS source_confidence,
                     list_filter(sources, lambda s: s.property LIKE '%height%')[1].dataset AS height_source,
                     list_filter(sources, lambda s: s.property LIKE '%num_floors%')[1].dataset AS floors_source,
                     ST_X(ST_PointOnSurface(geometry)) AS px, ST_Y(ST_PointOnSurface(geometry)) AS py,
                     geometry
              FROM read_parquet('{src}', hive_partitioning=1)
              WHERE bbox.xmin < {xmax} AND bbox.xmax > {xmin}
                AND bbox.ymin < {ymax} AND bbox.ymax > {ymin}
            ) TO '{stage}' (FORMAT parquet, COMPRESSION zstd);""")
        t = pq.read_table(stage)
        meta = t.schema.metadata
        cfp = assign_county(t["px"].to_numpy(), t["py"].to_numpy(), polys)
        keep = cfp != ""
        t = t.filter(pa.array(keep))
        t = t.append_column("countyfp", pa.array(cfp[keep].astype(str)))
        t = t.append_column("county", pa.array([COUNTIES[c] for c in cfp[keep]]))
        t = t.replace_schema_metadata(meta)
        pq.write_table(t, out, compression="zstd")
        stage.unlink()
        log(f"overture region5 {typ}: {t.num_rows} rows -> {out}")


def overture_report():
    rep = {}
    for typ in ("building", "building_part"):
        f = OUT_OVERTURE / f"region5_{typ}.parquet"
        con = duckdb.connect()
        rows = con.execute(f"""
          SELECT county, count(*) n,
                 avg((height IS NOT NULL)::int) share_height,
                 avg((num_floors IS NOT NULL)::int) share_floors,
                 avg((height IS NOT NULL OR num_floors IS NOT NULL)::int) share_height_or_floors,
                 avg((source_dataset = 'OpenStreetMap')::int) share_osm,
                 avg((source_dataset = 'Microsoft ML Buildings')::int) share_ms,
                 avg((source_dataset = 'Google Open Buildings')::int) share_google,
                 avg((source_dataset LIKE 'Esri%')::int) share_esri,
                 avg((height_source = 'OpenStreetMap')::int) share_height_osm,
                 avg((height_source = 'Microsoft ML Buildings')::int) share_height_ms
          FROM '{f}' GROUP BY county ORDER BY n DESC""").fetchdf()
        rep[typ] = rows.round(4).to_dict(orient="records")
        rep[f"{typ}_datasets"] = con.execute(
            f"SELECT source_dataset, count(*) n FROM '{f}' GROUP BY 1 ORDER BY 2 DESC").fetchall()
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "region5_overture.json").write_text(json.dumps(rep, indent=1, default=str))
    log(json.dumps(rep, indent=1, default=str))


# ---------------------------------------------------------------------------
# 2. Year-built sources (ArcGIS REST layers published by counties / cities)
# ---------------------------------------------------------------------------

BROWSER_UA = "Mozilla/5.0 (X11; Linux x86_64) BayThroughTime-pipeline/0.1 (+https://github.com/tjaffee99/bay)"


def _session():
    from common import session
    s = session()
    s.headers["User-Agent"] = BROWSER_UA
    return s


def arcgis_download(url: str, out: Path, fields: list[str] | str = "*", where: str = "1=1", threads: int = 4):
    """Download every feature of an ArcGIS REST layer (MapServer / FeatureServer) as
    GeoParquet in EPSG:4326, paging by object id. Attributes are kept as published;
    only the listed fields are requested (owner names / mailing addresses are left out)."""
    import concurrent.futures as cf
    import time

    import geopandas as gpd
    import pandas as pd

    if out.exists():
        log(f"{out.name}: cached")
        return
    s = _session()
    meta = s.get(url, params={"f": "json"}, timeout=120).json()
    oid = meta.get("objectIdField") or next(f["name"] for f in meta["fields"] if f["type"] == "esriFieldTypeOID")
    page = min(int(meta.get("maxRecordCount") or 1000), 2000)
    if isinstance(fields, str) and fields.startswith("re:"):
        # every published field matching the pattern, minus personal data (owner, mailing)
        keep, drop = re.compile(fields[3:], re.I), re.compile(PERSONAL, re.I)
        fields = [f["name"] for f in meta["fields"] if keep.search(f["name"]) and not drop.search(f["name"])]
    count = s.get(f"{url}/query", params={"where": where, "returnCountOnly": "true", "f": "json"}, timeout=300).json()["count"]
    # returnIdsOnly is capped on some servers (400k on hosted layers): ask per object-id window
    st = s.get(f"{url}/query", params={"where": where, "f": "json", "outStatistics": json.dumps([
        {"statisticType": "min", "onStatisticField": oid, "outStatisticFieldName": "lo"},
        {"statisticType": "max", "onStatisticField": oid, "outStatisticFieldName": "hi"}])}, timeout=300).json()
    lo, hi = (st["features"][0]["attributes"][k] for k in ("lo", "hi"))
    ids: list[int] = []
    for a in range(lo, hi + 1, 200_000):
        w = f"({where}) AND {oid} >= {a} AND {oid} < {a + 200_000}"
        ids.extend(s.get(f"{url}/query", params={"where": w, "returnIdsOnly": "true", "f": "json"},
                         timeout=300).json()["objectIds"] or [])
    ids = sorted(set(ids))
    log(f"{out.name}: {len(ids)} of {count} features from {url}")
    outf = fields if isinstance(fields, str) else ",".join(dict.fromkeys([oid, *fields]))

    def fetch(chunk):
        for attempt in range(6):
            try:
                r = s.post(f"{url}/query", data={
                    "objectIds": ",".join(map(str, chunk)), "outFields": outf, "outSR": 4326,
                    "returnGeometry": "true", "geometryPrecision": 7, "f": "geojson"}, timeout=300)
                j = r.json()
                if "features" in j:
                    return j["features"]
                log(f"  retry {attempt}: {str(j)[:200]}")
            except Exception as e:  # network hiccup / bad JSON
                log(f"  retry {attempt}: {e!r}")
            time.sleep(2 ** attempt)
        raise RuntimeError(f"failed chunk starting {chunk[0]} of {url}")

    chunks = [ids[i:i + page] for i in range(0, len(ids), page)]
    feats = []
    with cf.ThreadPoolExecutor(threads) as ex:
        for i, f in enumerate(ex.map(fetch, chunks)):
            feats.extend(f)
            if i % 50 == 0:
                log(f"  {out.name}: {len(feats)}/{len(ids)}")
    rows = [ft.get("properties") or {} for ft in feats]
    geoms = [shapely.geometry.shape(ft["geometry"]) if ft.get("geometry") else None for ft in feats]
    g = gpd.GeoDataFrame(pd.DataFrame(rows), geometry=geoms, crs=4326)
    out.parent.mkdir(parents=True, exist_ok=True)
    g.to_parquet(out, compression="zstd")
    (out.parent / f"{out.stem}.source.json").write_text(json.dumps({
        "url": url, "where": where, "fields": outf, "count": len(g),
        "downloaded": time.strftime("%Y-%m-%d"), "layer_name": meta.get("name"),
        "copyright": meta.get("copyrightText"), "description": (meta.get("description") or "")[:2000],
    }, indent=1))
    log(f"{out.name}: {len(g)} rows -> {out}")


PERSONAL = r"owner|mail|seller|buyer|careof|attn|^m_|^n_|grantee|grantor|phone|email|sale|^td\d|transdoc|legal"
# assessor fields worth keeping (year, effective year, stories, units, use, area, address)
ASSESSOR_RE = (r"^apn|parcel|year|yr|blt|built|eff|stor|floor|unit|use|class|situs|address|addr|city|zip|"
               r"bldg|build|area|sq|const|height|wall|bldgs|lot|acre|tra$|value|imp|land")
# Each source: id -> (url, fields, where). Field lists keep what the year table needs
# (+ address / use for checks) and skip owner names and mailing addresses.
YEAR_SOURCES: dict[str, dict] = {
    # Contra Costa County DoIT/GIS, CCMAP "Assessment Parcels" (assessor roll joined to parcels)
    "contra_costa_ccmap": {
        "url": "https://gis.cccounty.us/arcgis/rest/services/CCMAP/Assessment_Parcels_ArcPro/MapServer/0",
        "fields": ["APN", "TRA", "S_STR_NBR", "S_STR_NM", "S_STR_SUF", "S_APT_NBR", "S_CTY_ABBR", "s_city", "S_ZIP",
                   "USE_CODE", "Description", "LAND_VALUE", "IMP_VAL", "TLA", "GR_LND_AR", "YR_BUILT", "YR_HS_BLT",
                   "BLDG_SQFT", "C_DED_DT", "ACREAGE"],
    },
    # Contra Costa County Fire Protection District copy of the assessor characteristics
    # (stories, units, effective year, buildings per parcel) — joins to CCMAP by APN
    "contra_costa_cccfpd": {
        "url": "https://services6.arcgis.com/CmHj285GYxHhHnTo/arcgis/rest/services/Assessor_Parcels/FeatureServer/0",
        "fields": ["APN", "TYPE_1", "NBR_BLDNGS", "USE_DESC", "STORIES", "UNITS", "BLD_EFFYR", "ADDITION", "full_address_display"],
    },
    # County of Santa Clara Planning Office "Parcels Public View" (April 2026)
    "santa_clara_county": {
        "url": "https://services2.arcgis.com/tcv2cMrq63AgvbHF/arcgis/rest/services/Parcels_Public_View/FeatureServer/0",
        "fields": ["APN", "TRA", "Year_Built", "Situs_Address_Full", "Acres_Rec", "Sq_Ft_Rec"],
    },
    # --- Santa Clara County cities (same county roll, + stories / units / effective year)
    "sunnyvale": {"url": "https://services.arcgis.com/IBwZaktrBtZuqQmg/arcgis/rest/services/Property_Layer/FeatureServer/0",
                  "fields": "re:" + ASSESSOR_RE + "|heritage"},
    "milpitas": {"url": "https://services8.arcgis.com/OPmRdssd8jj0bT5H/arcgis/rest/services/Parcel_Owner_View/FeatureServer/0",
                 "fields": "re:" + ASSESSOR_RE},
    "saratoga": {"url": "https://services3.arcgis.com/rExmJXzTylAKURvh/arcgis/rest/services/Parcels/FeatureServer/0",
                 "fields": "re:" + ASSESSOR_RE + "|historic"},
    "los_gatos": {"url": "https://services3.arcgis.com/JAU7IM34hqT9y9ew/arcgis/rest/services/Parcels/FeatureServer/0",
                  "fields": "re:" + ASSESSOR_RE + "|historic"},
    # --- Alameda County: whole-county 2021 copy of the assessor roll + characteristics,
    # current city / district copies of the same county data
    "alameda_county_2021": {"url": "https://services9.arcgis.com/l0PUGx9JqRxaCPsG/arcgis/rest/services/Alameda_Co_Pcls/FeatureServer/0",
                            "fields": "re:" + ASSESSOR_RE + "|^situs|^centroid"},
    "alameda_trivalley_zone7": {"url": "https://services6.arcgis.com/yGWezgaq4oIlwApY/arcgis/rest/services/Parcels_LayFH/FeatureServer/0",
                                "fields": "re:" + ASSESSOR_RE + "|community"},
    "alameda_south_2026": {"url": "https://services7.arcgis.com/T3LbxamSmhpjBppB/arcgis/rest/services/UC_Parcels_07_2026_view/FeatureServer/12",
                           "fields": "re:" + ASSESSOR_RE + "|fips|countyuse|usetype|quality"},
    "hayward": {"url": "https://services3.arcgis.com/VRO5V8PH7DzSE6AU/arcgis/rest/services/Hayward_Area_Parcels/FeatureServer/0",
                "fields": "re:" + ASSESSOR_RE + "|remodel|condition|propertycharacter"},
    "berkeley": {"url": "https://services1.arcgis.com/IYiCpZoSIq9lAxi8/arcgis/rest/services/TaxParcel/FeatureServer/0",
                 "fields": "re:" + ASSESSOR_RE + "|date_updat|additions"},
    "albany": {"url": "https://services2.arcgis.com/3X7VMY0UAVT63A6d/arcgis/rest/services/ParcelsWeb/FeatureServer/0",
               "fields": "re:" + ASSESSOR_RE},
    "emeryville": {"url": "https://services3.arcgis.com/ljOdqLVbHpS7dOJQ/arcgis/rest/services/Parcels_Emeryville/FeatureServer/0",
                   "fields": "re:" + ASSESSOR_RE + "|historic"},
    # --- San Mateo County (no county-wide public characteristics; city copies)
    "san_mateo_county_office": {"url": "https://gis.smcgov.org/maps/rest/services/Common/ACTIVE_PARCELS_APN/FeatureServer/0",
                                "fields": ["APN", "SITUS_ADDR", "SITUS_CITY", "PUCDESC", "OFFICEYEARBUILT", "OFFICEGRSBLDAREA"],
                                "where": "OFFICEYEARBUILT IS NOT NULL"},
    "san_mateo_city": {"url": "https://services2.arcgis.com/g26Y0m7OCdjU0ObA/arcgis/rest/services/EnerGov_Query_AGOL/FeatureServer/2",
                       "fields": "re:" + ASSESSOR_RE},
    "belmont": {"url": "https://maps.belmont.gov/arcgis/rest/services/ParcelViewer/ZoningLandUse/MapServer/4",
                "fields": "re:" + ASSESSOR_RE},
    "san_bruno": {"url": "https://services2.arcgis.com/iLsFVn6d1pmqKEfA/arcgis/rest/services/Parcels/FeatureServer/0",
                  "fields": "re:" + ASSESSOR_RE + "|renovate"},
    "portola_valley": {"url": "https://services8.arcgis.com/LRqASGpv7gPaTEUL/arcgis/rest/services/Parcels/FeatureServer/0",
                       "fields": "re:" + ASSESSOR_RE + "|renovate"},
    "hillsborough": {"url": "https://services5.arcgis.com/74bZbbuf05Ctvbzv/arcgis/rest/services/Town_of_Hillsborough_Parcels/FeatureServer/0",
                     "fields": "re:" + ASSESSOR_RE + "|^hl_"},
    "south_sf_corelogic": {"url": "https://services6.arcgis.com/SAzG4Xt2MtnnJdpJ/arcgis/rest/services/SouthSFParcelAnalysis/FeatureServer/2",
                           "fields": "re:" + ASSESSOR_RE},
    # --- FEMA Region 9 building points (Microsoft / USA Structures footprint centroids
    # enriched with Lightbox SmartParcels assessor attributes) — all five counties, incl. Marin
    **{f"fema_r9_{k}": {
        "url": f"https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/Property_Structures_Static_Points_Building_Type_R9/FeatureServer/{lid}",
        "fields": ["BUILD_GEO_ID", "COUNTYFP", "PLACE_NAME", "PARCEL_APN", "USE_CODE_MUNI_DESC", "USE_CODE_STD_DESC_LPS",
                   "USE_CODE_STD_CTGR_DESC_LPS", "STORIES_NUMBER", "YR_BLT", "YR_BLT_EFFECT", "STYLE_DESC",
                   "CONSTRUCTION_CODE_DESC", "EXTERIOR_WALL_DESC", "ROOF_COVER_DESC", "SITE_ADDR"],
        "where": "STATEFP = '06' AND COUNTYFP IN ('001','013','041','081','085')"}
       for k, lid in (("res", 5), ("mixed", 6), ("nonres", 7))},
}


def years():
    for sid, src in YEAR_SOURCES.items():
        arcgis_download(src["url"], YEARS_RAW / sid / f"{sid}.parquet", src.get("fields", "*"), src.get("where", "1=1"))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("overture", "all"):
        overture()
        overture_report()
    if what in ("years", "all"):
        years()
