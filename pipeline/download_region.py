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


PERSONAL = (r"owner|mail|seller|buyer|careof|attn|^m_|^n_|^maddress|^mcity|^mzip|grantee|grantor|phone|email|sale|"
            r"^td\d|transdoc|legal|_user$")
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
    # --- historic resources with researched construction years (incl. demolished / moved)
    "san_jose_hri": {"url": "https://geo.sanjoseca.gov/server/rest/services/OPN/OPN_OpenDataService/MapServer/406",
                     "fields": "*"},
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


OVERPASS = ["https://overpass.kumi.systems/api/interpreter", "https://overpass-api.de/api/interpreter"]


def osm_start_date():
    """OSM buildings tagged start_date / construction_date (mappers' researched years:
    landmarks, NRHP buildings, campus buildings) in the five counties, via Overpass,
    one county bbox at a time. ODbL."""
    import time
    out = YEARS_RAW / "osm_start_date" / "osm_start_date.json"
    if out.exists() and out.stat().st_size > 10_000:
        log("osm_start_date: cached")
        return
    s = _session()
    polys = county_polygons()
    elements, base = {}, None
    for fp, g in polys.items():
        x0, y0, x1, y1 = g.bounds
        q = (f'[out:json][timeout:300];(way["building"]["start_date"]({y0},{x0},{y1},{x1});'
             f'relation["building"]["start_date"]({y0},{x0},{y1},{x1});'
             f'way["building"]["construction_date"]({y0},{x0},{y1},{x1}););out center tags;')
        for attempt in range(8):
            try:
                r = s.post(OVERPASS[attempt % 2], data={"data": q}, timeout=400)
                j = r.json()
                break
            except Exception as e:
                log(f"  overpass {COUNTIES[fp]} retry {attempt}: {str(e)[:120]}")
                time.sleep(20 * (attempt + 1))
        else:
            raise RuntimeError("overpass failed")
        base = j.get("osm3s", {}).get("timestamp_osm_base")
        for e in j["elements"]:
            elements[f"{e['type']}/{e['id']}"] = e
        log(f"osm_start_date {COUNTIES[fp]}: {len(j['elements'])} elements")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"timestamp_osm_base": base, "elements": list(elements.values())}))
    log(f"osm_start_date: {len(elements)} -> {out}")


# LiDAR / photogrammetry building footprints with heights (item 4 of the region research;
# Overture already carries OSM + Microsoft ML heights)
HEIGHT_SOURCES = {
    "san_mateo_county_footprints": {
        "url": "https://services.arcgis.com/yq3FgOI44hYHAFVZ/arcgis/rest/services/Building_Footprints/FeatureServer/0",
        "fields": ["BUILDINGID", "BASEELEV", "BLDGHEIGHT", "FLOORCOUNT", "EAVEHEIGHT", "ROOFFORM", "FEATURECODE", "LASTUPDATE"]},
    "marin_county_footprints": {
        "url": "https://services6.arcgis.com/T8eS7sop5hLmgRRH/arcgis/rest/services/Building_Footprints/FeatureServer/0",
        "fields": ["SourceCode", "SourceDateYear", "BuildingType", "BuildingName", "BaseElevationMinFeet", "PeakElevationMaxFeet"]},
}


def heights():
    for sid, src in HEIGHT_SOURCES.items():
        arcgis_download(src["url"], RAW / "region_heights" / sid / f"{sid}.parquet", src.get("fields", "*"), src.get("where", "1=1"))


def years():
    for sid, src in YEAR_SOURCES.items():
        arcgis_download(src["url"], YEARS_RAW / sid / f"{sid}.parquet", src.get("fields", "*"), src.get("where", "1=1"))


# ---------------------------------------------------------------------------
# 3. Normalise -> data/interim/region_years.parquet
# ---------------------------------------------------------------------------

CURRENT_YEAR = 2026
MIN_YEAR = 1769
# licence classes (see data/research/region_buildings.md):
#   public            published openly by the county / city / state (no licence stated unless noted)
#   third_party_copy  a consultant's / district's public copy of the county roll (no licence stated)
#   commercial        attributes from a commercial parcel vendor (Lightbox via FEMA, CoreLogic)
#   odbl              OpenStreetMap
# rank: 0 researched historic record > 1 current official roll > 2 older / third-party copy
#       of the roll > 3 commercial-derived
_P = dict(kind="parcel", licence="public", rank=1)
NORM: dict[str, dict] = {
    "contra_costa_ccmap": {**_P, "countyfp": "013", "year": ["YR_HS_BLT", "YR_BUILT"], "use": "Description",
                           "addr": "full_address_display", "vintage": "2026",
                           "join": {"sid": "contra_costa_cccfpd", "on": "APN",
                                    "cols": {"BLD_EFFYR": "eff", "STORIES": "stories", "UNITS": "units",
                                             "NBR_BLDNGS": "nbldg", "full_address_display": "addr"}}},
    "santa_clara_county": {**_P, "countyfp": "085", "year": "Year_Built", "addr": "Situs_Address_Full", "vintage": "2026-04"},
    "sunnyvale": {**_P, "countyfp": "085", "year": "YearBuilt", "stories": "Stories", "units": "CountyUnits",
                  "nbldg": "Buildings", "use": "LandUse", "addr": "SiteAddress", "vintage": "current"},
    "milpitas": {**_P, "countyfp": "085", "year": "YEAR_BUILT", "eff": "Year_Built_Eff", "stories": "NO_OF_FLOORS",
                 "units": "NO_OF_UNITS", "nbldg": "Num_Bldgs", "use": "USE_CODE", "addr": "AGOL_Address_Display", "vintage": "current"},
    "saratoga": {**_P, "countyfp": "085", "year": "YEAR_BUILT", "eff": "EFFECTIVE_YR_BLT", "stories": "NUMBER_OF_FLOORS",
                 "units": "NUMBER_OF_UNITS", "nbldg": "BLDNGS_ON_PARCEL", "use": "UseCodeDescription", "addr": "SitusAddress", "vintage": "current"},
    "los_gatos": {**_P, "countyfp": "085", "year": "YEAR_BUILT", "eff": "EFFECTIVE_YR_BLT", "stories": "NUMBER_OF_FLOORS",
                  "units": "NUMBER_OF_UNITS", "nbldg": "BLDNGS_ON_PARCEL", "use": "USE_CODE", "addr": "SiteAddressFull", "vintage": "current"},
    "alameda_county_2021": {**_P, "countyfp": "001", "licence": "third_party_copy", "rank": 2, "year": "YearBuilt",
                            "eff": "EffectiveY", "stories": "Stories", "units": "Units", "nbldg": "Buildings",
                            "use": "UseCode", "addr": "SitusAddre", "vintage": "2021-04"},
    "alameda_trivalley_zone7": {**_P, "countyfp": "001", "year": "YrBuilt", "eff": "EffYr", "stories": "Stories",
                                "units": "NumUnits", "nbldg": "Bldgs", "use": "UseCodeCountyDescription",
                                "addr": "SitusAddress", "vintage": "current"},
    "alameda_south_2026": {**_P, "countyfp": "001", "year": "YRBLT", "eff": "YREFF", "stories": "STORIES", "units": "UNITS",
                           "nbldg": "BLDGS", "use": "USETYPE", "addr": "S_ADDRESS", "vintage": "2026-07"},
    "berkeley": {**_P, "countyfp": "001", "year": "YearBuilt", "eff": "EffectiveY", "stories": "Stories", "units": "Units",
                 "nbldg": "Buildings", "use": "UseCode", "addr": "SitusAddre", "vintage": "2017"},
    "albany": {**_P, "countyfp": "001", "year": "YrBuilt", "eff": "EffYr", "stories": "Stories", "units": "NumUnits",
               "nbldg": "Bldgs", "use": "UseCodeDescriptionCounty", "vintage": "current"},
    "emeryville": {**_P, "countyfp": "001", "year": "YrBuilt", "eff": "EffYr", "stories": "Stories", "units": "NumUnits",
                   "nbldg": "Bldgs", "use": "UseCodeDescriptionCounty", "vintage": "current"},
    "san_mateo_county_office": {**_P, "countyfp": "081", "year": "OFFICEYEARBUILT", "use": "PUCDESC", "addr": "SITUS_ADDR", "vintage": "current"},
    "san_mateo_city": {**_P, "countyfp": "081", "year": "YEAR_BUILT_MANUFACTURED", "eff": "EFFECTIVE_YEAR", "remodel": "RENOVATE_YEAR",
                       "stories": "STORIES", "units": "NO_OF_UNITS", "nbldg": "NUM_OF_BLDG", "use": "PROPERTY_USE_CODE", "vintage": "current"},
    "belmont": {**_P, "countyfp": "081", "year": "YRBLT", "eff": "YREFF", "stories": "STORIES", "units": "UNITS",
                "nbldg": "BLDGS", "use": "USETYPE", "addr": "Situs_Address", "vintage": "current"},
    "san_bruno": {**_P, "countyfp": "081", "year": "YearBuilt", "remodel": "RENOVATE_YEAR", "use": "LandUse", "vintage": "current"},
    "portola_valley": {**_P, "countyfp": "081", "year": "YEAR_BUILT_MANUFACTURED", "eff": "EFFECTIVE_YEAR",
                       "remodel": "RENOVATE_YEAR", "stories": "STORIES", "units": "NO_OF_UNITS", "nbldg": "NUM_OF_BLDG",
                       "use": "LandUse", "vintage": "current"},
    "hillsborough": {**_P, "countyfp": "081", "licence": "third_party_copy", "rank": 2, "year": "hl_yearbuilt",
                     "addr": "city_situsaddr", "vintage": "2022"},
    "south_sf_corelogic": {**_P, "countyfp": "081", "licence": "commercial", "rank": 3, "year": "YR_BLT", "eff": "EFF_YR_BLT",
                           "stories": "STORY_NBR", "units": "UNITS_NBR", "use": "LAND_USE", "addr": "ADDR", "vintage": "2018"},
    **{f"fema_r9_{k}": {"kind": "building_point", "licence": "commercial", "rank": 3, "year": "YR_BLT", "eff": "YR_BLT_EFFECT",
                        "stories": "STORIES_NUMBER", "use": "USE_CODE_STD_DESC_LPS", "apn": "PARCEL_APN", "addr": "SITE_ADDR",
                        "material": "EXTERIOR_WALL_DESC", "construction": "CONSTRUCTION_CODE_DESC", "roof": "ROOF_COVER_DESC",
                        "vintage": "c.2020"} for k in ("res", "mixed", "nonres")},
    "san_jose_hri": {"kind": "historic_point", "licence": "public", "rank": 0, "countyfp": "085", "year": "TRUEYR",
                     "year_est": "ESTIMATEDYR", "stories": "STORIES", "use": "ORIGUSE", "vintage": "2023",
                     "name": "RESOURCENAME"},
}


def _num(v) -> np.ndarray:
    import pandas as pd
    if v.dtype == object:
        v = v.astype(str).str.extract(r"(\d+(?:\.\d+)?)", expand=False)
    return pd.to_numeric(v, errors="coerce").to_numpy(dtype=float)


def apn_key(countyfp: str, s) -> str | None:
    """Canonical book-page-parcel(-sub) key so APNs written differently by different
    publishers (dashes, spaces, zero padding, 8/9-digit runs) compare equal."""
    if not isinstance(s, str) or not s.strip():
        return None
    toks = [t for t in re.split(r"[^0-9A-Za-z]+", s.strip().upper()) if t]
    widths = {"013": (3, 3, 3), "081": (3, 3, 3), "085": (3, 2, 3), "041": (3, 3, 2)}
    if len(toks) == 1 and toks[0].isdigit() and countyfp in widths:
        d, w = toks[0], widths[countyfp]
        if len(d) not in (sum(w), sum(w) + 1):
            return None
        toks = [d[:w[0]], d[w[0]:w[0] + w[1]], d[w[0] + w[1]:]]
    elif countyfp == "001" and len(toks) == 2 and len(toks[1]) == 9 and toks[1].isdigit():
        toks = [toks[0], toks[1][:4], toks[1][4:7], toks[1][7:]]          # '501 045610700'
    if len(toks) < 3:
        return None
    norm = [str(int(t)) if t.isdigit() else t.lstrip("0") for t in toks[:4]]
    if countyfp == "001":
        sub = norm[3] if len(norm) > 3 else "0"
        return "-".join(norm[:3] + [sub])
    return "-".join(norm[:3])


def spike_years(years: np.ndarray, min_count: int = 20) -> set[int]:
    """Round-number placeholder years, SF rule: a multiple of 5 before 1950 whose count is
    more than 4x the median of the non-round years within +-10 years."""
    from collections import Counter
    c = Counter(int(y) for y in years if np.isfinite(y))
    out = set()
    for y in range(1800, 1950, 5):
        nb = [c.get(k, 0) for k in range(y - 10, y + 11) if k % 5]
        if c.get(y, 0) > max(4 * float(np.median(nb)), min_count):
            out.add(y)
    return out


def _clean_years(raw: np.ndarray):
    """-> (year_built float, flag str array). Zero / missing rows are dropped earlier."""
    year = np.array(raw, dtype=float, copy=True)
    flag = np.full(len(raw), "ok", dtype=object)
    flag[raw < MIN_YEAR] = "implausible_early"
    flag[raw > CURRENT_YEAR] = "future"
    year[(raw < MIN_YEAR) | (raw > CURRENT_YEAR)] = np.nan
    flag[(year >= MIN_YEAR) & (year < 1850)] = "suspect_pre1850"   # a few adobes exist; most are typos
    return year, flag


def _std_frame(sid: str, spec: dict, g):
    """Source GeoDataFrame -> standard columns."""
    import geopandas as gpd
    import pandas as pd
    col = lambda k: g[spec[k]] if spec.get(k) and spec[k] in g else None
    ycols = spec["year"] if isinstance(spec["year"], list) else [spec["year"]]
    raw = np.full(len(g), np.nan)
    for c in ycols:
        v = _num(g[c])
        raw = np.where(np.isfinite(raw) & (raw > 0), raw, v)
    conf = np.full(len(g), "exact", dtype=object)
    if spec.get("year_est"):
        est = _num(g[spec["year_est"]])
        use_est = ~(np.isfinite(raw) & (raw > 0)) & np.isfinite(est) & (est > 0)
        raw = np.where(use_est, est, raw)
        conf[use_est] = "estimated"
    out = pd.DataFrame({
        "src": sid, "rank": spec["rank"], "licence": spec["licence"], "kind": spec["kind"],
        "vintage": spec.get("vintage"),
        "apn": col("apn").astype(str) if col("apn") is not None else (g["APN"].astype(str) if "APN" in g else None),
        "year_raw": raw,
        "eff_year": _num(col("eff")) if col("eff") is not None else np.nan,
        "remodel_year": _num(col("remodel")) if col("remodel") is not None else np.nan,
        "stories": _num(col("stories")) if col("stories") is not None else np.nan,
        "units": _num(col("units")) if col("units") is not None else np.nan,
        "n_buildings": _num(col("nbldg")) if col("nbldg") is not None else np.nan,
        "use": col("use").astype(str) if col("use") is not None else None,
        "address": col("addr").astype(str) if col("addr") is not None else None,
        "name": col("name").astype(str) if col("name") is not None else None,
        "material": col("material") if col("material") is not None else None,
        "construction": col("construction") if col("construction") is not None else None,
        "roof": col("roof") if col("roof") is not None else None,
        "confidence": conf,
    })
    if sid == "san_jose_hri":
        out["demolished"] = g["DEMOLISHED"].fillna(0).astype(float).to_numpy() > 0
        out["moved"] = g["MOVED"].fillna(0).astype(float).to_numpy() > 0
    return gpd.GeoDataFrame(out, geometry=g.geometry.values, crs=4326)


def _osm_frame():
    import geopandas as gpd
    import pandas as pd
    f = YEARS_RAW / "osm_start_date" / "osm_start_date.json"
    if not f.exists():
        return None
    rows = []
    for e in json.loads(f.read_text())["elements"]:
        tg, c = e.get("tags", {}), e.get("center")
        if not c:
            continue
        sd = tg.get("start_date") or tg.get("construction_date") or ""
        m = re.search(r"(1[6-9]\d\d|20[0-2]\d)", sd)
        if not m:
            continue
        approx = bool(re.match(r"^\s*(~|c\.|ca|before|after|early|mid|late)", sd, re.I)) or len(sd.strip()) > 10
        rows.append({"src": "osm_start_date", "rank": 1, "licence": "odbl", "kind": "building_point",
                     "vintage": "2026-05", "apn": None, "year_raw": float(m.group(1)), "start_date_tag": sd,
                     "name": tg.get("name"), "use": tg.get("building"), "address": " ".join(
                         x for x in (tg.get("addr:housenumber"), tg.get("addr:street")) if x) or None,
                     "stories": pd.to_numeric(tg.get("building:levels"), errors="coerce"),
                     "osm_id": f"{e['type']}/{e['id']}", "confidence": "estimated" if approx else "exact",
                     "x": c["lon"], "y": c["lat"]})
    if not rows:
        return None
    d = pd.DataFrame(rows)
    return gpd.GeoDataFrame(d.drop(columns=["x", "y"]), geometry=gpd.points_from_xy(d.x, d.y), crs=4326)


HP_BUILDING = {f"HP{n:02d}" for n in (2, 3, 4, 5, 6, 7, 8, 9, 10, 13, 14, 15, 16, 17, 24, 34, 41, 42, 44, 45)}


def _berd_frame(located):
    """OHP Built Environment Resource Directory rows -> points, located by APN (FEMA building
    points and the parcel layers) and then by address. Construction ranges <= 10 years
    take the completion year; wider ranges are periods of significance (flag 'range')."""
    import geopandas as gpd
    import pandas as pd
    files = sorted((YEARS_RAW / "ca_ohp_berd").glob("*.csv"))
    if not files:
        return None, {}
    name2fp = {v.upper(): k for k, v in COUNTIES.items()}
    rows, stats = [], {}
    # lookup tables: (countyfp, apn_key) -> point ; (countyfp, address key) -> point
    by_apn, by_addr = {}, {}
    for r in located.itertuples():
        if r.apn_key is not None:
            by_apn.setdefault((r.countyfp, r.apn_key), r.pt)
        if r.addr_key is not None:
            by_addr.setdefault((r.countyfp, r.addr_key), r.pt)
    for f in files:
        d = pd.read_csv(f, dtype=str, encoding="latin-1").dropna(how="all")
        d = d[d["OTIS ID"].notna()]
        fp = name2fp.get(f.stem.replace("_", " ").upper())
        st = {"rows": len(d), "with_year": 0, "by_apn": 0, "by_address": 0}
        for rec in d.to_dict("records"):
            ys = [int(y) for y in re.findall(r"\b(1[6-9]\d\d|20[0-2]\d)\b", str(rec.get("Construction Year(s)") or ""))]
            if not ys:
                continue
            st["with_year"] += 1
            span = max(ys) - min(ys)
            year, flag = (float(max(ys)), "ok") if span <= 10 else (float(min(ys)), "range")
            pt, how = None, None
            for a in re.split(r"\s*\|\s*", str(rec.get("Parcel Num") or "")):
                k = apn_key(fp, a)
                if k and (fp, k) in by_apn:
                    pt, how = by_apn[(fp, k)], "apn"
                    break
            num, street = rec.get("St Number"), rec.get("St Name")
            if pt is None and isinstance(num, str) and isinstance(street, str):
                k = _addr_key(f"{num} {street}")
                if k and (fp, k) in by_addr:
                    pt, how = by_addr[(fp, k)], "address"
            if pt is None:
                continue
            st["by_apn" if how == "apn" else "by_address"] += 1
            attrs = str(rec.get("Attributes") or "")
            rows.append({"src": "ca_ohp_berd", "rank": 0, "licence": "public", "kind": "historic_point",
                         "vintage": "2026-02", "apn": rec.get("Parcel Num"), "year_raw": year, "berd_flag": flag,
                         "name": rec.get("Name"), "use": attrs,
                         "is_building": bool(set(re.findall(r"HP\d\d", attrs)) & HP_BUILDING),
                         "address": f"{num} {street}, {rec.get('City')}",
                         "berd_status": rec.get("Evaluation Info"), "located_by": how,
                         "confidence": "exact" if flag == "ok" else "estimated", "geometry": pt})
        stats[f.stem] = st
    if not rows:
        return None, stats
    return gpd.GeoDataFrame(pd.DataFrame(rows), geometry="geometry", crs=4326), stats


def _addr_key(s) -> str | None:
    """'1445 LAKESIDE DR' -> '1445 LAKESIDE' (house number + first street-name word)."""
    if not isinstance(s, str):
        return None
    m = re.match(r"\s*(\d+)[A-Z]?\s+(?:[NSEW]\.?\s+)?([A-Z0-9']+)", s.upper())
    return f"{m.group(1)} {m.group(2)}" if m else None


def place_polygons():
    import geopandas as gpd
    p = gpd.read_file(f"zip://{RAW / 'tiger' / 'tl_2024_06_place.zip'}")[["NAME", "LSAD", "geometry"]].to_crs(4326)
    p["incorporated"] = p.LSAD.isin(["25", "43"])    # 25 city, 43 town; 57 = CDP
    return p


def normalise():
    import geopandas as gpd
    import pandas as pd

    out_path = INTERIM / "region_years.parquet"
    polys = county_polygons()
    frames, report = [], {"sources": {}}
    for sid, spec in NORM.items():
        f = YEARS_RAW / sid / f"{sid}.parquet"
        if not f.exists():
            log(f"normalise: {sid} missing, skipped")
            continue
        g = gpd.read_parquet(f)
        if "join" in spec:
            j = spec["join"]
            jt = gpd.read_parquet(YEARS_RAW / j["sid"] / f"{j['sid']}.parquet").drop(columns="geometry")
            jt = jt[[j["on"], *j["cols"]]].drop_duplicates(j["on"]).rename(columns={k: f"_j_{k}" for k in j["cols"]})
            g = g.merge(jt, on=j["on"], how="left")
            for k, role in j["cols"].items():
                if role in spec and spec[role] in g:
                    continue
                spec = {**spec, role: f"_j_{k}"}
        d = _std_frame(sid, spec, g)
        frames.append(d)
    osm = _osm_frame()
    if osm is not None:
        frames.append(osm)
    d = pd.concat(frames, ignore_index=True)
    d = gpd.GeoDataFrame(d, geometry="geometry", crs=4326)
    d = d[d.geometry.notna() & ~d.geometry.is_empty]

    # county from the representative point; city / CDP from TIGER places
    rp = d.geometry.representative_point()
    x, y = rp.x.to_numpy(), rp.y.to_numpy()
    d["countyfp"] = assign_county(x, y, polys)
    d = d[d.countyfp != ""].copy()
    rp = d.geometry.representative_point()
    d["county"] = d.countyfp.map(COUNTIES)
    places = place_polygons()
    pts = gpd.GeoDataFrame(geometry=rp.values, crs=4326, index=d.index)
    hit = gpd.sjoin(pts, places, how="left", predicate="within")
    hit = hit[~hit.index.duplicated(keep="first")]
    d["place"] = hit["NAME"].reindex(d.index)
    d["incorporated"] = hit["incorporated"].reindex(d.index).fillna(False).astype(bool)

    # zero / missing raw year: dropped (counted); then plausibility and spikes per source
    stats = {}
    for sid, grp in d.groupby("src"):
        r = grp.year_raw.to_numpy()
        stats[sid] = {"rows": int(len(grp)), "zero_or_missing": int((~np.isfinite(r) | (r <= 0)).sum())}
    d = d[np.isfinite(d.year_raw) & (d.year_raw > 0)].copy()
    year, flag = _clean_years(d.year_raw.to_numpy())
    d["year_built"], d["year_flag"] = year, flag
    if "berd_flag" in d:
        d.loc[d.berd_flag == "range", "year_flag"] = "range"
    for col in ("eff_year", "remodel_year"):
        v = d[col].to_numpy(dtype=float).copy()
        v[(v < MIN_YEAR) | (v > CURRENT_YEAR) | (v <= 0)] = np.nan
        d[col] = v
    d.loc[d.stories <= 0, "stories"] = np.nan
    d.loc[d.units <= 0, "units"] = np.nan
    d.loc[d.n_buildings <= 0, "n_buildings"] = np.nan
    hist = {}
    for sid, grp in d.groupby("src"):
        yb = grp.year_built.to_numpy()
        sp = spike_years(yb) if sid not in ("san_jose_hri", "ca_ohp_berd", "osm_start_date") else set()
        is_sp = np.isin(yb, list(sp))
        d.loc[grp.index[is_sp], "year_flag"] = "spike"
        d.loc[grp.index[is_sp], "confidence"] = "estimated"
        fl = d.loc[grp.index, "year_flag"].value_counts().to_dict()
        ok = yb[np.isfinite(yb)]
        stats[sid].update({
            "with_year": int(np.isfinite(yb).sum()),
            "flags": {k: int(v) for k, v in fl.items()},
            "spike_years": sorted(sp),
            "median_year": float(np.median(ok)) if len(ok) else None,
            "share_pre1906": round(float((ok < 1906).mean()), 4) if len(ok) else None,
            "max_year": int(ok.max()) if len(ok) else None,
            "share_eff_year": round(float(np.isfinite(grp.eff_year).mean()), 4),
            "share_stories": round(float(np.isfinite(grp.stories).mean()), 4),
            "county": grp.county.value_counts().to_dict(),
        })
        hist[sid] = {int(k): int(v) for k, v in pd.Series(ok.astype(int)).value_counts().sort_index().items()}

    # OHP BERD located through APN / address of the rows above
    loc = d[d.src.str.startswith("fema_r9") | (d.kind == "parcel")]
    lrp = loc.geometry.representative_point()
    located = pd.DataFrame({
        "countyfp": loc.countyfp.to_numpy(),
        "apn_key": [apn_key(c, a) for c, a in zip(loc.countyfp, loc.apn)],
        "addr_key": [_addr_key(a) for a in loc.address],
        "pt": lrp.values})
    berd, berd_stats = _berd_frame(located)
    if berd is not None:
        brp = berd.geometry
        berd["countyfp"] = assign_county(brp.x.to_numpy(), brp.y.to_numpy(), polys)
        berd = berd[berd.countyfp != ""].copy()
        berd["county"] = berd.countyfp.map(COUNTIES)
        hit = gpd.sjoin(berd[["geometry"]], places, how="left", predicate="within")
        hit = hit[~hit.index.duplicated(keep="first")]
        berd["place"] = hit["NAME"]
        berd["incorporated"] = hit["incorporated"].fillna(False).astype(bool)
        yb, fl = _clean_years(berd.year_raw.to_numpy())
        berd["year_built"] = yb
        berd["year_flag"] = np.where(berd.berd_flag == "range", "range", fl)
        stats["ca_ohp_berd"] = {"rows": int(sum(s["rows"] for s in berd_stats.values())),
                                "with_year": int(np.isfinite(yb).sum()), "located": berd_stats,
                                "flags": berd.year_flag.value_counts().to_dict(),
                                "county": berd.county.value_counts().to_dict()}
        ok = yb[np.isfinite(yb)]
        hist["ca_ohp_berd"] = {int(k): int(v) for k, v in pd.Series(ok.astype(int)).value_counts().sort_index().items()}
        d = pd.concat([d, berd], ignore_index=True)

    # compact geometry: parcels simplified to ~0.2 m, coordinates to 1e-7 deg
    is_poly = d.geom_type.isin(["Polygon", "MultiPolygon"]).to_numpy()
    geoms = np.asarray(d.geometry.to_numpy(), dtype=object)
    geoms[is_poly] = shapely.simplify(geoms[is_poly], 2e-6, preserve_topology=True)
    d = gpd.GeoDataFrame(d.drop(columns="geometry"), geometry=shapely.set_precision(geoms, 1e-7, mode="pointwise"), crs=4326)
    for c in ("year_built", "eff_year", "remodel_year"):
        d[c] = d[c].round().astype("Int16")
    d["year_raw"] = d.year_raw.round().astype("Int32")
    d["units"] = d.units.round().astype("Int32")
    d["n_buildings"] = d.n_buildings.round().astype("Int16")
    for c in ("apn", "use", "address", "name", "material", "construction", "roof", "start_date_tag", "osm_id",
              "berd_status", "located_by", "berd_flag", "vintage", "place"):
        if c in d:
            d[c] = d[c].astype("string").replace({"None": pd.NA, "nan": pd.NA, "": pd.NA})
    d = d.reset_index(drop=True)
    d.to_parquet(out_path, compression="zstd")
    log(f"region_years: {len(d)} rows -> {out_path}")

    REPORTS.mkdir(parents=True, exist_ok=True)
    report["sources"] = stats
    (REPORTS / "region_years_sources.json").write_text(json.dumps(report, indent=1, default=str))
    (REPORTS / "region_years_hist.json").write_text(json.dumps(hist))
    plot_histograms(hist, stats)


def plot_histograms(hist: dict, stats: dict):
    """Small multiples, one panel per source: construction years 1840-2026, spike years marked."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    surface, ink, ink2, grid = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
    base, spike = "#2a78d6", "#eb6834"
    srcs = sorted(hist, key=lambda s: -sum(hist[s].values()))
    n = len(srcs)
    cols = 4
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(4.2 * cols, 2.2 * rows), facecolor=surface, squeeze=False)
    for ax, sid in zip(axes.flat, srcs):
        h = hist[sid]
        yrs = np.array([y for y in h if 1840 <= y <= CURRENT_YEAR])
        cnt = np.array([h[y] for y in yrs])
        sp = set(stats.get(sid, {}).get("spike_years", []))
        colors = [spike if y in sp else base for y in yrs]
        ax.bar(yrs, cnt, width=1.0, color=colors, linewidth=0)
        ax.set_facecolor(surface)
        ax.set_xlim(1840, CURRENT_YEAR + 1)
        for x in (1906, 1950, 2000):
            ax.axvline(x, color=grid, linewidth=0.8, zorder=0)
        ax.set_title(f"{sid}  (n={sum(h.values()):,})", fontsize=8.5, color=ink, loc="left")
        ax.tick_params(labelsize=7, colors=ink2, length=2)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(grid)
        if sp:
            ax.text(0.01, 0.92, "spikes: " + ", ".join(map(str, sorted(sp))), transform=ax.transAxes,
                    fontsize=6.5, color=ink2, va="top")
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=base, label="year built (count per year)"),
                        Patch(color=spike, label="placeholder spike year (flagged)")],
               loc="upper right", fontsize=8, frameon=False, labelcolor=ink)
    fig.suptitle("Construction years per source, five-county region (grey lines: 1906, 1950, 2000)",
                 fontsize=10, color=ink, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(REPORTS / "region_years_hist.png", dpi=110, facecolor=surface)
    plt.close(fig)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("overture", "all"):
        overture()
        overture_report()
    if what in ("years", "all"):
        years()
    if what in ("osm", "years", "all"):
        osm_start_date()
    if what in ("normalise", "all"):
        normalise()
    if what in ("heights", "all"):
        heights()
