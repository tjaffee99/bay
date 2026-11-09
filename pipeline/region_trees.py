"""Stage: real street (and park) trees for the five counties around San Francisco.

Like San Francisco's street trees (trees.py), every tree here stands where a city's tree
inventory puts it. Sources: the public tree inventories of the cities (and two campuses)
that publish one — see SOURCES below and SOURCES.md `region_trees`. Downloads go to
data/raw/region_trees/<source>.parquet (raw, untouched; `python region_trees.py download`).

Planting year, best first:
  * a recorded planting / install date, where the inventory has one and it is
    believable (not a bulk date stamped on thousands of records at a data migration, and
    not contradicted by the trunk: a tree can't be thicker than its species grows in
    that time)                                                              -> exact
  * from the trunk diameter (DBH) at the inventory date, with the USDA Forest Service
    Urban Tree Database's species age-from-DBH equations (McPherson et al. 2016,
    RDS-2016-0005; Northern California Coast reference city Berkeley, then the
    Inland Valleys / Sacramento Valley / Southern California Coast sets for species the
    coast set lacks, or for the inland valleys first); genus median for other species
    of a covered genus; else San Francisco's rule (0.35 in of DBH a year)  -> estimated
  * no usable DBH: ten years after the street (as trees.py)                  -> estimated
Bounds (same rules as the streets, roads.date_by_buildings): a street tree isn't planted
more than 3 years before the street it stands on was built up — the 2nd-earliest
building within 45 m (today's footprints and vanished ones,
data/interim/region_building_points.parquet), else the HISDAC first built-up year of
its cell — except large native oaks / bays / sycamores (DBH >= 30 in), which are kept
as remnants of the land before the town; never before the ground under it existed
(bay fill: terrain land-year grids, airports.land_year); never after the inventory date.

Size: measured height / crown spread where the inventory has them (feet, numbers or
ranges), else the Urban Tree Database's species DBH->height / crown-diameter equations,
else trees.py's generic allometry; clamped to trees.py's ranges so both sets look alike.
Form: palm / conifer / broadleaf from the species name, with trees.py's patterns.

Output: viewer/public/data/region-trees/12/<x>/<y>.bin.gz (BAYT, the columns of
sf-trees.bin.gz) + index.json; data/interim/region_trees.parquet (one row per tree,
for QGIS / audits); data/interim/reports/region_trees.json.

Usage: python region_trees.py [download|build|all]   (default: all)
"""
from __future__ import annotations

import json
import re
import sys
import zipfile

import numpy as np
import pandas as pd

from common import CURRENT_YEAR, INTERIM, RAW, VIEWER_DATA, get_with_retry, log, session

OUT_RAW = RAW / "region_trees"
UTD = OUT_RAW / "usfs_utd"
UTD_URL = "https://www.fs.usda.gov/rds/archive/products/RDS-2016-0005/RDS-2016-0005.zip"

# ---------------------------------------------------------------- sources
# kind "arcgis": every feature of an ArcGIS REST layer (download_region.arcgis_download);
# kind "zip": a zipped shapefile. `inland` cities use the inland-valley growth sets first.
SOURCES = {
    "san_jose": dict(
        city="San José", county="Santa Clara", kind="arcgis",
        url="https://geo.sanjoseca.gov/server/rest/services/OPN/OPN_OpenDataService/MapServer/510",
        info="https://data.sanjoseca.gov/dataset/street-tree",
        licence="CC BY 4.0 (San José Open Data portal)", attribution="City of San José, Department of Transportation"),
    "oakland": dict(
        city="Oakland", county="Alameda", kind="arcgis",
        url="https://services.arcgis.com/9tC74aDHuml0x5Yz/arcgis/rest/services/Oakland_Public_Tree_Inventory_/FeatureServer/0",
        info="https://www.oaklandca.gov/resources/oakland-public-tree-map",
        licence="public city data, no licence stated", attribution="City of Oakland, 2019-20 public tree inventory"),
    "berkeley": dict(
        city="Berkeley", county="Alameda", kind="zip",
        url="https://spatial.lib.berkeley.edu/maps/berkeley-ark28722-s7gq2s/data/original/data.zip",
        info="https://geodata.lib.berkeley.edu/catalog/berkeley-s7gq2s",
        licence="public (City of Berkeley open data, archived by the UC Berkeley Library; rights: Public)",
        attribution="City of Berkeley Parks Division / Arborwell, 2013 urban forest inventory"),
    "palo_alto": dict(
        city="Palo Alto", county="Santa Clara", kind="arcgis",
        url="https://gis.cityofpaloalto.org/server/rest/services/Parcel/ParcelReport/MapServer/2",
        info="https://data.paloalto.gov/datasets/62370/city-of-palo-alto-trees/",
        licence="public city data, no licence stated", attribution="City of Palo Alto Public Works, tree inventory"),
    "mountain_view": dict(
        city="Mountain View", county="Santa Clara", kind="arcgis",
        url="https://maps.mountainview.gov/arcgis/rest/services/Public/Trees/FeatureServer/0",
        info="https://maps.mountainview.gov/arcgis/rest/services/Public/Trees/FeatureServer",
        licence="public city data, no licence stated (City disclaimer: no warranty)",
        attribution="City of Mountain View"),
    "hayward": dict(
        city="Hayward", county="Alameda", kind="arcgis",
        url="https://maps.hayward-ca.gov/arcgis/rest/services/MaintenanceServices/TreeInventory/MapServer/0",
        info="https://maps.hayward-ca.gov/arcgis/rest/services/MaintenanceServices/TreeInventory/MapServer",
        licence="public city data, no licence stated", attribution="City of Hayward / Davey Resource Group tree inventory"),
    "alameda": dict(
        city="Alameda", county="Alameda", kind="arcgis",
        url="https://services9.arcgis.com/ucDLsG1EwPnOGY4c/arcgis/rest/services/City_Tree_view/FeatureServer/0",
        info="https://services9.arcgis.com/ucDLsG1EwPnOGY4c/arcgis/rest/services/City_Tree_view/FeatureServer",
        licence="public city data, no licence stated", attribution="City of Alameda / West Coast Arborists tree inventory"),
    "pleasanton": dict(
        city="Pleasanton", county="Alameda", kind="arcgis", inland=True,
        url="https://services2.arcgis.com/yrktbS5Xw87hJQvs/arcgis/rest/services/TreeInvPleasanton_Public/FeatureServer/0",
        info="https://services2.arcgis.com/yrktbS5Xw87hJQvs/arcgis/rest/services/TreeInvPleasanton_Public/FeatureServer",
        licence="public (published by West Coast Arborists for the City), no licence stated",
        attribution="City of Pleasanton / West Coast Arborists tree inventory"),
    "san_ramon": dict(
        city="San Ramon", county="Contra Costa", kind="arcgis", inland=True,
        url="https://gis.sanramon.ca.gov/server/rest/services/Fieldwork/Trees/FeatureServer/0",
        info="https://gis.sanramon.ca.gov/server/rest/services/Fieldwork/Trees/FeatureServer",
        licence="public city data, no licence stated", attribution="City of San Ramon / West Coast Arborists (Feb 2017)"),
    "cupertino": dict(
        city="Cupertino", county="Santa Clara", kind="arcgis",
        url="https://gis.cupertino.org/cupgis/rest/services/Public/AmazonData/MapServer/29",
        info="https://gis.cupertino.org/cupgis/rest/services/Public/Fleet_Tables/MapServer/14",
        licence="public city data, no licence stated", attribution="City of Cupertino Public Works / GIS"),
    "san_mateo": dict(
        city="San Mateo", county="San Mateo", kind="arcgis",
        url="https://services2.arcgis.com/g26Y0m7OCdjU0ObA/arcgis/rest/services/Street_Trees/FeatureServer/0",
        info="https://services2.arcgis.com/g26Y0m7OCdjU0ObA/arcgis/rest/services/Street_Trees/FeatureServer",
        licence="public city data, no licence stated", attribution="City of San Mateo Public Works / Davey Resource Group"),
    "menlo_park": dict(
        city="Menlo Park", county="San Mateo", kind="arcgis",
        url="https://gisweb.menlopark.gov/server/rest/services/GISWeb/Trees2026/FeatureServer/3",
        info="https://gisweb.menlopark.gov/server/rest/services/GISWeb/Trees2026/FeatureServer",
        licence="public city data, no licence stated", attribution="City of Menlo Park / West Coast Arborists (2026)"),
    "milpitas": dict(
        city="Milpitas", county="Santa Clara", kind="arcgis",
        url="https://services8.arcgis.com/OPmRdssd8jj0bT5H/arcgis/rest/services/Trees West Coast Arborist/FeatureServer/0",
        info="https://services8.arcgis.com/OPmRdssd8jj0bT5H/arcgis/rest/services/Trees%20West%20Coast%20Arborist/FeatureServer",
        licence="public city data, © City of Milpitas 2022, no licence stated",
        attribution="City of Milpitas / West Coast Arborists"),
    "santa_clara": dict(
        city="Santa Clara", county="Santa Clara", kind="arcgis",
        url="https://map.santaclaraca.gov/maps/rest/services/Lucity/StreetTrees/MapServer/0",
        info="https://map.santaclaraca.gov/maps/rest/services/Lucity/StreetTrees/MapServer",
        licence="public city data, no licence stated", attribution="City of Santa Clara Public Works"),
    "emeryville": dict(
        city="Emeryville", county="Alameda", kind="arcgis",
        url="https://services3.arcgis.com/ljOdqLVbHpS7dOJQ/arcgis/rest/services/Trees_Authoritative_view/FeatureServer/0",
        info="https://services3.arcgis.com/ljOdqLVbHpS7dOJQ/arcgis/rest/services/Trees_Authoritative_view/FeatureServer",
        licence="public city data, no licence stated", attribution="City of Emeryville / West Coast Arborists"),
    # Santa Clara County's compilation (Office of Sustainability): Los Gatos, Sunnyvale
    # (a 10,000-tree part of the city's ~37,000), county parks; Palo Alto / San José come
    # from the cities themselves
    "los_gatos": dict(
        city="Los Gatos", county="Santa Clara", kind="arcgis",
        url="https://services.arcgis.com/NkcnS0qk4w2wasOJ/arcgis/rest/services/Tree_Inventories_in_Santa_Clara_County_WFL1/FeatureServer/3",
        info="https://services.arcgis.com/NkcnS0qk4w2wasOJ/arcgis/rest/services/Tree_Inventories_in_Santa_Clara_County_WFL1/FeatureServer",
        licence="public (County of Santa Clara compilation of city inventories), no licence stated",
        attribution="Town of Los Gatos, via County of Santa Clara"),
    "sunnyvale": dict(
        city="Sunnyvale", county="Santa Clara", kind="arcgis",
        url="https://services.arcgis.com/NkcnS0qk4w2wasOJ/arcgis/rest/services/Tree_Inventories_in_Santa_Clara_County_WFL1/FeatureServer/1",
        info="https://services.arcgis.com/NkcnS0qk4w2wasOJ/arcgis/rest/services/Tree_Inventories_in_Santa_Clara_County_WFL1/FeatureServer",
        licence="public (County of Santa Clara compilation of city inventories), no licence stated",
        attribution="City of Sunnyvale, via County of Santa Clara"),
    "scc_county": dict(
        city="Santa Clara County parks", county="Santa Clara", kind="arcgis",
        url="https://services.arcgis.com/NkcnS0qk4w2wasOJ/arcgis/rest/services/Tree_Inventories_in_Santa_Clara_County_WFL1/FeatureServer/0",
        info="https://services.arcgis.com/NkcnS0qk4w2wasOJ/arcgis/rest/services/Tree_Inventories_in_Santa_Clara_County_WFL1/FeatureServer",
        licence="public (County of Santa Clara), no licence stated", attribution="County of Santa Clara"),
    "stanford": dict(
        city="Stanford University", county="Santa Clara", kind="arcgis",
        url="https://services.arcgis.com/7CRlmWNEbeCqEJ6a/arcgis/rest/services/Stanford_Trees_Basic_WFL1/FeatureServer/1",
        info="https://services.arcgis.com/7CRlmWNEbeCqEJ6a/arcgis/rest/services/Stanford_Trees_Basic_WFL1/FeatureServer",
        licence="public (Stanford University ArcGIS Online), no licence stated", attribution="Stanford University campus tree database"),
    "santa_clara_university": dict(
        city="Santa Clara University", county="Santa Clara", kind="arcgis",
        url="https://services9.arcgis.com/4mGCdwoq2Vacd9uM/arcgis/rest/services/Tree_Data_(Updated_11_21_2025)/FeatureServer/0",
        info="https://services9.arcgis.com/4mGCdwoq2Vacd9uM/arcgis/rest/services/Tree_Data_(Updated_11_21_2025)/FeatureServer",
        licence="public (Santa Clara University sustainability office), no licence stated",
        attribution="Santa Clara University campus tree survey (2025-26)"),
}


def arcgis_points(url: str, out, page: int = 1000):
    """Every point of an ArcGIS REST layer -> GeoParquet (EPSG:4326), streamed: object ids
    first, then one chunk at a time appended to the file (memory stays small). Attributes as
    published. A .source.json next to it records url, date, count and the layer's notes."""
    import time

    import pyarrow as pa
    import pyarrow.parquet as pq
    import shapely

    if out.exists():
        log(f"{out.name}: cached")
        return
    s = session()
    s.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) BayThroughTime-pipeline"

    def get(path, **params):
        for attempt in range(6):
            try:
                r = s.post(f"{url}{path}", data={"f": "json", **params}, timeout=300)
                j = r.json()
                if "error" not in j:
                    return j
                log(f"  retry {attempt}: {str(j)[:200]}")
            except Exception as e:  # network hiccup / bad JSON
                log(f"  retry {attempt}: {e!r}")
            time.sleep(2 ** attempt)
        raise RuntimeError(f"failed {url}{path} {str(params)[:100]}")

    meta = get("")
    page = min(page, int(meta.get("maxRecordCount") or 1000))
    ids = sorted(get("/query", where="1=1", returnIdsOnly="true").get("objectIds") or [])
    log(f"{out.name}: {len(ids)} features from {url}")
    tmp = out.with_suffix(".part")
    writer, schema, n = None, None, 0
    for i in range(0, len(ids), page):
        j = get("/query", objectIds=",".join(map(str, ids[i:i + page])), outFields="*", outSR=4326,
                returnGeometry="true")
        feats = j.get("features", [])
        rows = [f.get("attributes") or {} for f in feats]
        geo = [f.get("geometry") or {} for f in feats]
        x = np.array([g.get("x", np.nan) if g.get("x") is not None else np.nan for g in geo], float)
        y = np.array([g.get("y", np.nan) if g.get("y") is not None else np.nan for g in geo], float)
        df = pd.DataFrame(rows)
        if schema is None:
            # types from the layer's field list (numbers and dates -> float64, dates as epoch ms)
            numeric = {"esriFieldTypeDouble", "esriFieldTypeSingle", "esriFieldTypeInteger", "esriFieldTypeOID",
                       "esriFieldTypeSmallInteger", "esriFieldTypeDate", "esriFieldTypeBigInteger"}
            ftype = {f["name"]: f["type"] for f in meta.get("fields", [])}
            names = [c for c in df.columns if c != "geometry"]
            schema = pa.schema([pa.field(c, pa.float64() if ftype.get(c) in numeric else pa.string()) for c in names]
                               + [pa.field("geometry", pa.binary())])
            schema = schema.with_metadata({b"geo": json.dumps({"version": "1.0.0", "primary_column": "geometry",
                                           "columns": {"geometry": {"encoding": "WKB",
                                                                    "geometry_types": ["Point"]}}}).encode()})
            writer = pq.ParquetWriter(tmp, schema, compression="zstd")
        cols = {}
        for f in schema:
            if f.name == "geometry":
                cols[f.name] = pa.array(shapely.to_wkb(shapely.points(x, y)), pa.binary())
            elif pa.types.is_float64(f.type):
                cols[f.name] = pa.array(pd.to_numeric(df.get(f.name, pd.Series([None] * len(df))),
                                                      errors="coerce").to_numpy(float), pa.float64())
            else:
                v = df.get(f.name, pd.Series([None] * len(df)))
                cols[f.name] = pa.array([None if (e is None or (isinstance(e, float) and np.isnan(e))) else str(e)
                                         for e in v], pa.string())
        writer.write_table(pa.table(cols, schema=schema))
        n += len(df)
        if (i // page) % 25 == 0:
            log(f"  {out.name}: {n}/{len(ids)}")
    if writer:
        writer.close()
        tmp.rename(out)
    (out.parent / f"{out.stem}.source.json").write_text(json.dumps({
        "url": url, "count": n, "downloaded": time.strftime("%Y-%m-%d"), "layer_name": meta.get("name"),
        "copyright": meta.get("copyrightText"), "description": (meta.get("description") or "")[:2000]}, indent=1))
    log(f"{out.name}: {n} rows -> {out}")


def download(only: list[str] | None = None):
    """Each source's raw layer to data/raw/region_trees/<id>.parquet (cached), one at a
    time, and the Urban Tree Database (growth equations)."""
    arcgis_download = lambda url, out, *a: arcgis_points(url, out)  # noqa: E731
    OUT_RAW.mkdir(parents=True, exist_ok=True)
    if not (UTD / "Data" / "TS6_Growth_coefficients.csv").exists():
        UTD.mkdir(parents=True, exist_ok=True)
        z = UTD / "RDS-2016-0005.zip"
        z.write_bytes(get_with_retry(session(), UTD_URL).content)
        zipfile.ZipFile(z).extractall(UTD)
    for sid, src in SOURCES.items():
        if only and sid not in only:
            continue
        out = OUT_RAW / f"{sid}.parquet"
        try:
            if src["kind"] == "arcgis":
                arcgis_download(src["url"], out, src.get("fields", "*"), src.get("where", "1=1"))
            elif not out.exists():
                import geopandas as gpd
                d = OUT_RAW / sid
                d.mkdir(exist_ok=True)
                z = d / "data.zip"
                if not z.exists():
                    z.write_bytes(get_with_retry(session(), src["url"]).content)
                g = gpd.read_file(f"zip://{z}").to_crs(4326)
                g.to_parquet(out, compression="zstd")
                log(f"{sid}: {len(g)} rows -> {out}")
        except Exception as e:  # one failing server doesn't stop the others
            log(f"{sid}: download failed: {e!r}")


# ---------------------------------------------------------------- species and growth
# trees.py's form patterns (0 broadleaf, 1 conifer, 2 palm)
from trees import CONIFER, PALM  # noqa: E402

COAST = ["NoCalC", "InlVal", "SacVal", "SoCalC", "InlEmp"]
INLAND = ["InlVal", "SacVal", "NoCalC", "InlEmp", "SoCalC"]
SYNONYM = {"platanus hispanica": "platanus acerifolia", "platanus x": "platanus acerifolia",
           "pinus thunbergii": "pinus thunbergiana", "fraxinus oxycarpa": "fraxinus angustifolia",
           "ficus microcarpa": "ficus thonningii", "ficus retusa": "ficus thonningii",
           "tristania conferta": "lophostemon confertus", "tristaniopsis conferta": "lophostemon confertus",
           "melaleuca linariifolia": "melaleuca quinquenervia", "prunus blireiana": "prunus cerasifera",
           "pyrus kawakami": "pyrus kawakamii", "eucalyptus spp": "eucalyptus globulus"}
SP_WORDS = re.compile(r"[a-z]+")
NATIVE_REMNANT = re.compile(r"^(quercus (lobata|agrifolia|douglasii|kelloggii|wislizeni|wislizenii)|"
                            r"umbellularia californica|platanus racemosa|aesculus californica)$")


def sci_key(name: str) -> str:
    """'Platanus x acerifolia 'Bloodgood'' / 'MAGNOLIA SOUTHERN (Magnolia grandiflora)' ->
    'platanus acerifolia' / 'magnolia grandiflora' (genus + epithet, lower case)."""
    s = str(name or "").strip()
    m = re.search(r"\(([A-Z][a-z]+ [a-z]+[^)]*)\)", s)
    if m:
        s = m.group(1)
    s = re.sub(r"'[^']*'|\"[^\"]*\"|\bcvs?\.?|\bvar\.|\bssp\.|\bspp?\.?$|\bspp?\.?\s|×|\s[xX]\s", " ", s).lower()
    w = SP_WORDS.findall(s)
    w = [x for x in w if x not in ("x", "cv", "cvs", "var", "spp", "sp", "species", "hybrid", "and")]
    key = " ".join(w[:2])
    return SYNONYM.get(key, SYNONYM.get(" ".join(w[:1]) + " x", key))


def load_utd():
    """{(region, species key, predicts): (eq, a, b, c, d, e, sigma, x_lo, x_hi, y_lo, y_hi)} for the
    California regions, from the Urban Tree Database (TS6). dbh in cm, height / crown in m."""
    t = pd.read_csv(UTD / "Data" / "TS6_Growth_coefficients.csv")
    t.columns = [c.strip() for c in t.columns]
    t = t[t.Region.isin(set(COAST))].copy()
    t["key"] = t["Scientific Name"].map(sci_key)
    # the dbh range an equation applies to comes from the species' age -> dbh fit
    rng = t[(t["Independent variable"] == "age") & (t["Predicts component"] == "dbh")]
    rng = {(r.Region, r.key): (float(r["Apps min"]), float(r["Apps max"])) for _, r in rng.iterrows()}
    out = {}
    for _, r in t[t["Independent variable"] == "dbh"].iterrows():
        pred = {"age": "age", "tree ht": "height", "crown dia": "crown"}.get(r["Predicts component"])
        if not pred or (r.Region, r.key) not in rng:
            continue
        f = lambda c: float(r[c]) if pd.notna(r[c]) else 0.0
        out[(r.Region, r.key, pred)] = (r.EqName, f("a"), f("b"), f("c"), f("d"), f("e"), f("Sigma"),
                                        *rng[(r.Region, r.key)], f("Apps min"), f("Apps max"))
    return out


DBH_GRID = np.arange(0.0, 251.0, 0.5)  # cm


def utd_curve(eq) -> np.ndarray:
    """An equation evaluated on DBH_GRID, made usable everywhere: monotonic non-decreasing,
    clamped to the published application range; beyond the fitted DBH range an age keeps
    growing at the mean rate of the upper half of the range (a size stays at its maximum)."""
    name, a, b, c, d, e, sigma, x_lo, x_hi, y_lo, y_hi = eq
    x = np.clip(DBH_GRID, x_lo, x_hi)
    mse = sigma ** 2
    if name.startswith("loglog"):
        w = {"1": 1.0, "2": np.sqrt(x), "3": x, "4": x ** 2}[name[-1]]
        y = np.exp(a + b * np.log(np.log(x + 1)) + w * mse / 2)
    elif name.startswith("expow"):
        w = {"1": 1.0, "2": np.sqrt(x), "3": x, "4": x ** 2}[name[-1]]
        y = np.exp(a + b * x + w * mse / 2)
    else:
        y = a + b * x + c * x ** 2 + d * x ** 3 + e * x ** 4
    y = np.maximum.accumulate(np.clip(y, max(y_lo, 0.0), y_hi))
    return y, x_hi


def growth_tables(utd):
    """Per species key (and per genus, the median of its species), per region order:
    age / height / crown curves over DBH_GRID."""
    curves = {}
    for (region, key, pred), eq in utd.items():
        y, x_hi = utd_curve(eq)
        if pred == "age":
            beyond = DBH_GRID > x_hi
            if beyond.any():
                i_hi = np.searchsorted(DBH_GRID, x_hi)
                i_mid = np.searchsorted(DBH_GRID, x_hi / 2)
                slope = (y[i_hi] - y[i_mid]) / max(DBH_GRID[i_hi] - DBH_GRID[i_mid], 1.0)
                y = np.where(beyond, y[i_hi] + max(slope, 0.2) * (DBH_GRID - DBH_GRID[i_hi]), y)
        curves[(region, key, pred)] = y
    genus = {}
    for (region, key, pred), y in curves.items():
        genus.setdefault((region, key.split()[0], pred), []).append(y)
    gcurves = {k: np.median(np.stack(v), axis=0) for k, v in genus.items()}
    return curves, gcurves


def pick_curve(curves, gcurves, key: str, pred: str, order) -> tuple[np.ndarray | None, str]:
    for region in order:
        if (region, key, pred) in curves:
            return curves[(region, key, pred)], f"species:{region}"
    g = key.split()[0] if key else ""
    for region in order:
        if (region, g, pred) in gcurves:
            return gcurves[(region, g, pred)], f"genus:{region}"
    return None, "generic"


# ---------------------------------------------------------------- field helpers
_NUM = re.compile(r"\d+(?:\.\d+)?")


def num_range(v) -> tuple[np.ndarray, np.ndarray]:
    """Numbers and range classes as published ("12 to 18", '13"-18"', "30-45", "51 +",
    "0-6") -> (low, high); a plain number -> (v, v); "51 +" (open top class) -> (51, 61);
    "---" / blank / NA -> NaN."""
    s = pd.Series(v)
    if pd.api.types.is_numeric_dtype(s):
        x = pd.to_numeric(s, errors="coerce").to_numpy(float)
        return x, x.copy()
    lo, hi = np.full(len(s), np.nan), np.full(len(s), np.nan)
    for i, t in enumerate(s.fillna("").astype(str).values):
        nums = _NUM.findall(t)
        if len(nums) >= 2:
            lo[i], hi[i] = float(nums[0]), float(nums[1])
        elif len(nums) == 1:
            lo[i] = float(nums[0])
            hi[i] = lo[i] * (1.2 if "+" in t else 1.0)
    return lo, hi


def num_or_range(v) -> np.ndarray:
    """num_range's midpoint."""
    lo, hi = num_range(v)
    return (lo + hi) / 2


def year_of(v) -> np.ndarray:
    """Dates as published (epoch milliseconds, ISO / m/d/Y strings) -> decimal year (NaN if none)."""
    s = pd.Series(v)
    if pd.api.types.is_numeric_dtype(s):
        d = pd.to_datetime(pd.to_numeric(s, errors="coerce"), unit="ms", errors="coerce")
    else:
        d = pd.to_datetime(s.astype(str).where(s.notna()), errors="coerce", format="mixed")
    y = d.dt.year + (d.dt.dayofyear - 1) / 365.25
    return y.to_numpy(float)


def col(df, *names, default=np.nan):
    for n in names:
        if n in df.columns:
            return df[n]
    return pd.Series(default, index=df.index)


NOT_TREE = re.compile(r"vacant|stump|asphalt|planting site|plant site|no tree|removed|empty|future|proposed|"
                      r"^\s*(?:n/?a|none|#n/a)\s*$", re.I)


def std(df, sp, common, dbh, height=None, crown=None, planted=None, asof=None, park=None, alive=None):
    """One normalised table per source."""
    n = len(df)
    dbh_lo, dbh_hi = (dbh if isinstance(dbh, tuple) else (dbh, dbh))
    full = lambda v, d=np.nan: (np.full(n, d) if v is None else (np.full(n, v) if np.isscalar(v) else np.asarray(v)))
    out = pd.DataFrame({
        "lon": df.geometry.x.values, "lat": df.geometry.y.values,
        "species": pd.Series(sp, index=df.index).fillna("").astype(str).str.strip().values,
        "common": pd.Series(common, index=df.index).fillna("").astype(str).str.strip().values,
        "dbh_lo": full(dbh_lo).astype(float), "dbh_hi": full(dbh_hi).astype(float), "height_ft": full(height).astype(float),
        "crown_ft": full(crown).astype(float), "planted": full(planted).astype(float),
        "measured": full(asof).astype(float), "park": full(park, False).astype(bool),
        "alive": full(alive, True).astype(bool),
    })
    out["alive"] &= ~(out.species.str.contains(NOT_TREE) | out.common.str.contains(NOT_TREE))
    bad = ~(out.dbh_hi > 0)
    out.loc[bad, ["dbh_lo", "dbh_hi"]] = np.nan
    out["dbh_lo"] = np.fmax(out.dbh_lo, 0.5)
    out["dbh_in"] = (out.dbh_lo + out.dbh_hi) / 2
    return out


def park_of(v) -> np.ndarray:
    return pd.Series(v).fillna("").astype(str).str.contains(r"\bpark\b|open space|golf|campus|school|civic|facility",
                                                             case=False, regex=True).values


def _sj(d):
    # DIAMETER is the crown spread (ft) and TRUNKDIAM the DBH (in); dates: Davey 2014 inventory, updates since
    return std(d, d.NAMESCIENTIFIC, "", num_range(d.TRUNKDIAM), d.HEIGHT, d.DIAMETER, year_of(d.INSTALLDATE),
               np.fmax(year_of(d.INVENTORYUPDATE), year_of(d.ORIGINALINVENTORYDATE)),
               park=park_of(d.MAINTBY), alive=d.VACANTSITE.astype(str).str.lower().ne("yes").values)


def _oakland(d):
    return std(d, d.Species___botanical, d.Species___common, num_range(d.DBH), asof=2020.0,
               park=park_of(d.SubArea), alive=d.Public_Tree.astype(str).ne("No").values)


def _berkeley(d):
    return std(d, d.SPECIES, d.Common_Nam, num_range(d.DBH_IN), num_or_range(d.HEIGHT_FT),
               num_or_range(d.SPREAD_FT), asof=year_of(d.GPS_Date),
               park=park_of(d.GROWSPACE), alive=d.ICON_TYPE.astype(str).eq("T").values)


def _palo_alto(d):
    return std(d, d.SPECIES, "", num_range(d.DIAMETERBREASTHEIGHT), num_or_range(d.HEIGHTCODE),
               num_or_range(d.CANOPYWIDTH), year_of(d.INSTALLDATE), year_of(d.INVENTORYDATE),
               park=park_of(d.GROWSPACE), alive=pd.to_numeric(d.ACTIVE, errors="coerce").fillna(1).ne(0).values)


def _mountain_view(d):
    # DIAMETER is the DBH in inches (Circumference / pi); HEIGHT mostly empty
    return std(d, d.SPECIES, d.NAME, num_range(d.DIAMETER), num_or_range(d.HEIGHT),
               planted=year_of(d.INSTALLDATE), park=park_of(d.SPACETYPE))


def _hayward(d):
    return std(d, d.SPP, "", num_range(d.DBH), num_or_range(d.HEIGHT), num_or_range(d.WIDTH),
               asof=np.fmax(year_of(d.Inv_Date), year_of(d.INSPECT_DT)), park=park_of(d.LANDUSE),
               alive=pd.to_numeric(d.Active, errors="coerce").fillna(1).ne(0).values)


def _wca(d, sp, common, dbh, actual, height, asof=None, park=None):
    """West Coast Arborists exports: DBH class ('0-6', '13-18', '---') and, newer, the measured DBH."""
    a = num_or_range(actual) if actual is not None else np.full(len(d), np.nan)
    lo, hi = num_range(dbh)
    lo, hi = np.where(a > 0, a, lo), np.where(a > 0, a, hi)
    return std(d, sp, common, (lo, hi), num_or_range(height), asof=asof, park=park)


def _alameda(d):
    return _wca(d, "", d.CommonName, d.DBH, d.ActualDBH, d.Height, park=park_of(d.ParkwayType))


def _pleasanton(d):
    return _wca(d, d.BotanicalName, d.CommonName, d.DBH, None, d.Height, park=park_of(d.Street))


def _san_ramon(d):
    out = _wca(d, d.BotanicalName, d.CommonName, d.DBH, None, d.Height, park=park_of(d.Street))
    ah = num_or_range(d.ActualHeight)
    out["height_ft"] = np.where(ah > 0, ah, out.height_ft)
    out["crown_ft"] = num_or_range(d.ActualCrown)
    return out


def _menlo_park(d):
    return _wca(d, d.BOTANICALN, d.COMMONNAME, d.DBH, d.ACTUALDBH, d.HEIGHT, asof=year_of(d.DATEMODIFI),
                park=park_of(d.SIDE))


def _milpitas(d):
    return _wca(d, d.BotanicalName, d.NameCommon, d.DBH, None, d.HeightRange, asof=year_of(d.TS),
                park=park_of(d.TypePark))


def _cupertino(d):
    st = d.Status.fillna("").astype(str)
    return std(d, d.Species, d.SpeciesCommonName, num_range(d.DiameterBreastHieght), num_or_range(d.Height),
               num_or_range(d.CanopyDiameter), year_of(d.PlantDate), year_of(d.LastInspectedDate),
               park=park_of(d.LocationType), alive=~st.str.contains("remov|dead|inactive|retired", case=False).values)


def _san_mateo(d):
    return std(d, d.SPP, "", num_range(d.DBH), num_or_range(d.HEIGHT), num_or_range(d.WIDTH),
               asof=np.fmax(year_of(d.INV_DATE), year_of(d.INSPECT_DT)), park=park_of(d.LANDUSE),
               alive=pd.to_numeric(d.ACTIVE, errors="coerce").fillna(1).ne(0).values)


def _santa_clara(d):
    gone = d.SpeciesType.fillna("").astype(str).str.contains("remov", case=False) | \
        pd.to_numeric(d.StatusCode, errors="coerce").eq(999)
    return std(d, "", d.SpeciesName, num_range(d.DBH), num_or_range(d.Height), num_or_range(d.Canopy),
               asof=year_of(d.AssessmentDate), alive=~gone.values)  # LastModDate: a 2026 bulk edit


def _emeryville(d):
    return std(d, d.BOTANICAL, d.COMMON, num_range(d.DBH_RANGE), num_or_range(d.HEIGHT_RAN),
               asof=year_of(d.DATE), park=park_of(d.PKWY_TYPE))


def _los_gatos(d):
    return std(d, d.Botanical, d.Common, num_range(d.DBH), num_or_range(d.Height), asof=year_of(d.Date))


def _sunnyvale(d):
    return std(d, d.Species, "", num_range(d.DBH), num_or_range(d.Height))


def _scc_county(d):
    return std(d, d.Scientific, d.CommonName, num_range(d.DBH), num_or_range(d.TreeHeight),
               num_or_range(d.CrownSprea), park=park_of(d.TreeType))


def _stanford(d):
    return std(d, d.BOTANICAL_, "", num_range(d.DBH_NUM), park=True)


def _scu(d):
    return std(d, "", d.Tree_Species, num_range(d.Tree_Diameter_at_Breast_Height__in__),
               num_or_range(d.Tree_Height__ft__), asof=year_of(d.Timestamp), park=True)


NORMALISE = {"san_jose": _sj, "oakland": _oakland, "berkeley": _berkeley, "palo_alto": _palo_alto,
             "mountain_view": _mountain_view, "hayward": _hayward, "alameda": _alameda, "pleasanton": _pleasanton,
             "san_ramon": _san_ramon, "cupertino": _cupertino, "san_mateo": _san_mateo, "menlo_park": _menlo_park,
             "milpitas": _milpitas, "santa_clara": _santa_clara, "emeryville": _emeryville,
             "los_gatos": _los_gatos, "sunnyvale": _sunnyvale, "scc_county": _scc_county, "stanford": _stanford,
             "santa_clara_university": _scu}
# the survey year of a source whose records carry no inventory date (DBH measured then)
ASOF = {"san_jose": 2014, "oakland": 2020, "berkeley": 2013, "palo_alto": 2012, "mountain_view": 2022,
        "hayward": 2010, "alameda": 2023, "pleasanton": 2023, "san_ramon": 2017, "cupertino": 2018,
        "san_mateo": 2010, "menlo_park": 2024, "milpitas": 2022, "santa_clara": 2022, "emeryville": 2004,
        "los_gatos": 2018, "sunnyvale": 2019, "scc_county": 2019, "stanford": 2010, "santa_clara_university": 2026}
for _k, _v in ASOF.items():
    SOURCES[_k]["asof"] = float(_v)


# ---------------------------------------------------------------- build
DECO_ORIGIN = (-122.2, 37.85)   # viewer/src/layers/deco-layer.ts: tiles share it, so they merge without re-offsetting
TILE_Z = 12                     # like region-streets/: ~10 x 8 km squares, drawn from zoom ~12.5
SF_RATE_IN = 0.35               # trees.py: inches of DBH a year
DEDUPE_M = 2.0                  # the same tree in two inventories (compilation vs city)
STREET_LEAD = 3.0               # a street tree may be planted this many years before the 2nd building
UTM = 32610


def load_sources() -> pd.DataFrame:
    import geopandas as gpd
    parts = []
    for prio, (sid, src) in enumerate(SOURCES.items()):
        p = OUT_RAW / f"{sid}.parquet"
        if not p.exists() or sid not in NORMALISE:
            log(f"{sid}: {'no download' if not p.exists() else 'no normaliser'} — skipped")
            continue
        g = gpd.read_parquet(p)
        g = g[g.geometry.notna() & ~g.geometry.is_empty]
        g = g[g.geometry.geom_type == "Point"]
        d = NORMALISE[sid](g.reset_index(drop=True))
        d["source"], d["prio"], d["inland"] = sid, prio, bool(src.get("inland", False))
        n0 = len(d)
        d = d[d.alive & d.lon.between(-123.2, -121.2) & d.lat.between(36.8, 38.9)]
        if sid != "scc_county":
            # stray records far outside the city (bad coordinates): keep the city's own box + ~3 km
            lo, hi = d[["lon", "lat"]].quantile(0.002), d[["lon", "lat"]].quantile(0.998)
            d = d[d.lon.between(lo.lon - 0.03, hi.lon + 0.03) & d.lat.between(lo.lat - 0.03, hi.lat + 0.03)]
        d = d.drop_duplicates(["lon", "lat", "species"])
        log(f"{sid}: {n0} records, {len(d)} trees")
        parts.append(d)
    return pd.concat(parts, ignore_index=True)


def fill_species(d: pd.DataFrame):
    """Scientific names for records that only have a common name (Alameda's WCA export,
    Santa Clara University), learnt from the sources that publish both."""
    both = d[(d.species.str.len() > 3) & (d.common.str.len() > 2)]
    lut = (both.assign(c=both.common.str.upper().str.strip(), k=both.species.map(sci_key))
           .groupby("c").k.agg(lambda s: s.value_counts().index[0]))
    key = d.species.map(sci_key)
    need = (key.str.len() < 4) | ~key.str.contains(" ")
    from_common = d.common.str.upper().str.strip().map(lut)
    key = key.where(~need | from_common.isna(), from_common)
    # a bare genus as the common name ("Magnolia", "Liquidambar"): the genus
    genera = {k.split()[0] for k in lut.values if k}
    first = d.common.str.lower().str.extract(r"^\s*([a-z]+)\b", expand=False)
    gen = need & key.isna() | need & (key.str.len() < 4)
    key = key.where(~(gen & first.isin(genera)), first)
    return key.fillna(""), int((need & from_common.notna()).sum())


def build():
    import geopandas as gpd
    from scipy.spatial import cKDTree

    from airports import land_year
    from export_columnar import write_columnar
    from extent import in_extent
    from terrain_grid import grid_def

    d = load_sources()
    log(f"region trees: {len(d)} inventory trees from {d.source.nunique()} sources")

    # San Francisco has its own street trees (trees.py); the map extent
    counties = gpd.read_file(f"zip://{RAW / 'tiger' / 'tl_2024_us_county.zip'}")
    sf = counties[(counties.STATEFP == "06") & (counties.COUNTYFP == "075")].geometry.iloc[0]
    pts = gpd.GeoSeries(gpd.points_from_xy(d.lon, d.lat), crs=4326)
    keep = in_extent(pts) & ~pts.within(sf).values
    d, pts = d[keep].reset_index(drop=True), pts[keep].reset_index(drop=True)
    pu = pts.to_crs(UTM)
    d["x"], d["y"] = pu.x.values, pu.y.values

    # the same tree in two inventories: the higher-priority source (city before compilation) wins
    order = np.argsort(d.prio.values, kind="stable")
    tree = cKDTree(np.column_stack([d.x.values, d.y.values]))
    drop = np.zeros(len(d), bool)
    for i, j in tree.query_pairs(DEDUPE_M, output_type="ndarray"):
        if d.source.values[i] != d.source.values[j]:
            drop[j if d.prio.values[j] > d.prio.values[i] else i] = True
    log(f"region trees: {drop.sum()} duplicates across sources dropped")
    d = d[~drop].reset_index(drop=True)

    # species -> form, growth curves
    d["key"], n_common = fill_species(d)
    names = d.species + " " + d.common + " " + d.key
    d["form"] = np.where(names.str.contains(PALM), 2, np.where(names.str.contains(CONIFER), 1, 0)).astype(np.uint8)
    curves, gcurves = growth_tables(load_utd())

    # a DBH class ('13-18') is a range: each tree a stable point inside it, so a city's
    # trees of one species and class aren't all planted in the same year
    u = (pd.util.hash_pandas_object(d[["source", "lon", "lat"]], index=False).to_numpy() >> 16 & 0xFFFF) / 65535.0
    dbh = (d.dbh_lo + (d.dbh_hi - d.dbh_lo) * u).to_numpy(float)
    dbh = np.where((dbh > 0) & (dbh < 120), dbh, np.nan)
    d["dbh_in"] = dbh
    dbh_cm = dbh * 2.54
    age = np.full(len(d), np.nan)
    hgt = np.full(len(d), np.nan)
    crn = np.full(len(d), np.nan)
    how = np.full(len(d), "generic", dtype=object)
    for (key, inland), idx in d.groupby(["key", "inland"]).indices.items():
        order_ = INLAND if inland else COAST
        x = dbh_cm[idx]
        ok = np.isfinite(x)
        ca, how_a = pick_curve(curves, gcurves, key, "age", order_)
        if ca is not None:
            age[idx[ok]] = np.interp(x[ok], DBH_GRID, ca)
            how[idx[ok]] = how_a
        ch, _ = pick_curve(curves, gcurves, key, "height", order_)
        if ch is not None:
            hgt[idx[ok]] = np.interp(x[ok], DBH_GRID, ch)
        cc, _ = pick_curve(curves, gcurves, key, "crown", order_)
        if cc is not None:
            crn[idx[ok]] = np.interp(x[ok], DBH_GRID, cc) / 2
    # palms: a trunk hardly thickens with age, so DBH says little — trees.py's rule
    generic = np.isfinite(dbh) & (np.isnan(age) | (d.form.values == 2))
    age[generic] = dbh[generic] / SF_RATE_IN
    how[generic] = "generic"
    remnant = d.key.str.match(NATIVE_REMNANT).values & (dbh >= 30)
    age = np.minimum(age, np.where(remnant, 250.0, 150.0))

    # when the DBH was measured: the record's inventory date, else the source's survey year
    asof = d.measured.to_numpy(float)
    asof = np.where(np.isfinite(asof) & (asof > 1990) & (asof <= CURRENT_YEAR + 1), asof, np.nan)
    src_default = d.source.map({k: v.get("asof", 2022.0) for k, v in SOURCES.items()}).to_numpy(float)
    asof = np.where(np.isfinite(asof), asof, src_default)
    from_dbh = asof - age

    # recorded planting dates: believable ones only (not a bulk date, not contradicted by the trunk)
    planted = d.planted.to_numpy(float)
    planted = np.where((planted > 1850) & (planted <= asof + 0.5), planted, np.nan)
    day = pd.Series(np.round(planted, 3)).where(np.isfinite(planted))
    bulk_n = day.map(day.value_counts()).fillna(0).to_numpy()
    src_n = d.source.map(d.source.value_counts()).to_numpy()
    bulk = (bulk_n >= np.maximum(200, 0.02 * src_n))
    # survey years: a year with far more "plantings" than the years around it is when the
    # records were entered (Mountain View: 17k dates in 1993, 7k on 31 Dec 2006)
    py = np.floor(planted)
    for sid in d.source.unique():
        m = (d.source.values == sid) & np.isfinite(py)
        if not m.any():
            continue
        cnt = pd.Series(py[m]).value_counts()
        for yv, cn in cnt.items():
            around = [cnt.get(yv + k, 0) for k in range(-5, 6) if k]
            if cn >= 100 and cn > 5 * max(np.median(around), 1):
                bulk |= m & (py == yv)
    # a tree planted in year P can't have a trunk much thicker than its species reaches by asof
    too_thick = np.isfinite(from_dbh) & (from_dbh < planted - np.maximum(8.0, 0.5 * (asof - planted)))
    rec_ok = np.isfinite(planted) & ~bulk & ~too_thick
    log(f"region trees: {np.isfinite(planted).sum()} recorded planting dates, {(np.isfinite(planted) & bulk).sum()} "
        f"bulk-stamped, {(np.isfinite(planted) & ~bulk & too_thick).sum()} contradicted by DBH, {rec_ok.sum()} used")

    # the street: 2nd-earliest building within 45 m (today's and vanished), else HISDAC first built-up year
    b = pd.read_parquet(INTERIM / "region_building_points.parquet", columns=["lon", "lat", "start_year"])
    bu = gpd.GeoSeries(gpd.points_from_xy(b.lon, b.lat), crs=4326).to_crs(UTM)
    bt = cKDTree(np.column_stack([bu.x.values, bu.y.values]))
    by = b.start_year.to_numpy(float)
    dist, idx = bt.query(np.column_stack([d.x.values, d.y.values]), k=6, distance_upper_bound=45)
    yrs = np.where(np.isfinite(dist), by[np.minimum(idx, len(by) - 1)], np.nan)
    yrs.sort(axis=1)
    street = np.where(np.isfinite(yrs[:, 1]), yrs[:, 1], yrs[:, 0])
    n_bld = int(np.isfinite(street).sum())
    del b, bu, bt, by
    gR = grid_def("region")
    fb = np.load(INTERIM / "grid_region_fbuy.npy").astype(float)
    X = np.radians(d.lon.values) * 6378137.0
    Y = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(d.lat.values) / 2))
    c = np.clip(np.rint((X - gR["X0"]) / gR["res"]).astype(int), 0, gR["cols"] - 1)
    r = np.clip(np.rint((gR["Y0"] - Y) / gR["res"]).astype(int), 0, gR["rows"] - 1)
    fby = fb[r, c]
    del fb
    fby[(fby < 1810) | (fby > CURRENT_YEAR)] = np.nan
    street = np.where(np.isfinite(street), street, fby)

    # planting year
    est = np.where(np.isfinite(from_dbh), from_dbh, street + 10.0)
    year = np.where(rec_ok, planted, est)
    bound = street - STREET_LEAD
    bounded = np.isfinite(bound) & (year < bound) & ~(remnant & ~rec_ok)
    year = np.where(bounded, bound, year)
    ly = land_year(d.lon.values, d.lat.values)
    on_fill = np.isfinite(ly) & (year < ly + 1.0)
    year = np.where(on_fill, ly + 1.0, year)
    # no date and no street / built-up year at all: an undated tree in the country, from 1950
    nodate = ~np.isfinite(year)
    year = np.where(nodate, 1950.0, year)
    year = np.minimum(year, np.minimum(asof, CURRENT_YEAR))
    conf = np.where(rec_ok & ~bounded & ~on_fill, 0, 1).astype(np.uint8)

    # size: measured > Urban Tree Database species allometry > trees.py's generic rule
    dbh_f = np.where(np.isfinite(dbh), dbh, 6.0)
    h_meas = d.height_ft.to_numpy(float) * 0.3048
    c_meas = d.crown_ft.to_numpy(float) * 0.3048 / 2
    height = np.where(h_meas > 1.0, h_meas, np.where(np.isfinite(hgt), hgt, 3.0 + 0.32 * dbh_f))
    crown = np.where(c_meas > 0.4, c_meas, np.where(np.isfinite(crn), crn, 1.0 + 0.13 * dbh_f))
    height = np.clip(height, 3.0, 24.0)
    crown = np.clip(crown, 1.0, 7.0)

    d["year"], d["confidence"], d["height_m"], d["crown_m"] = year, conf, height, crown
    d["street_year"], d["land_year"], d["age_from"] = street, ly, np.where(rec_ok, "recorded", how)
    d["age_from"] = np.where(~rec_ok & ~np.isfinite(dbh), "street+10", d.age_from)
    d["bounded_by"] = np.select([on_fill, bounded], ["fill", "street"], "")
    d.drop(columns=["x", "y", "alive", "prio"]).to_parquet(INTERIM / "region_trees.parquet", compression="zstd")
    write_tiles(d)
    report(d, n_bld, n_common, rec_ok)


def write_tiles(d: pd.DataFrame):
    import shutil
    from export_columnar import write_columnar
    out = VIEWER_DATA / "region-trees"
    if out.exists():
        shutil.rmtree(out)
    n = 2 ** TILE_Z
    tx = np.floor((d.lon.values + 180) / 360 * n).astype(int)
    lat = np.radians(d.lat.values)
    ty = np.floor((1 - np.log(np.tan(lat) + 1 / np.cos(lat)) / np.pi) / 2 * n).astype(int)
    # deterministic jitter of the fractional year (trees.py) so a planting doesn't pop on one frame
    h = (pd.util.hash_pandas_object(d[["source", "lon", "lat"]], index=False).to_numpy() & 0xFFFF) / 65535.0
    sources = list(SOURCES)
    index, total = [], 0
    for (x, y), idx in pd.DataFrame({"x": tx, "y": ty}).groupby(["x", "y"]).indices.items():
        t = d.iloc[idx]
        q = np.rint((np.column_stack([t.lon.values, t.lat.values]) - DECO_ORIGIN) * 1e7).astype(np.int32)
        cols = {
            "position_q|shuffle": q.ravel(),
            "start_year": (np.floor(t.year.values) + 0.9 * h[idx]).astype(np.float32),
            "height": t.height_m.values.astype(np.float32),
            "crown": t.crown_m.values.astype(np.float32),
            "form": t.form.values.astype(np.uint8),
            "confidence": t.confidence.values.astype(np.uint8),
            "source": t.source.map(sources.index).values.astype(np.uint8),
        }
        p = out / str(TILE_Z) / str(x) / f"{y}.bin.gz"
        _, gz = write_columnar(p, cols, origin=DECO_ORIGIN, counts={"features": int(len(t))},
                               meta={"position_scale": 1e-7, "forms": ["broadleaf", "conifer", "palm"]})
        index.append({"x": int(x), "y": int(y), "n": int(len(t)), "bytes": int(gz)})
        total += gz
    (out / "index.json").write_text(json.dumps({
        "z": TILE_Z, "origin": list(DECO_ORIGIN), "position_scale": 1e-7,
        "forms": ["broadleaf", "conifer", "palm"], "sources": sources,
        "attribution": {k: v["attribution"] for k, v in SOURCES.items()},
        "tiles": index}, separators=(",", ":")))
    log(f"region trees: {len(d)} trees in {len(index)} z{TILE_Z} tiles, {total / 1e6:.1f} MB gz "
        f"(largest {max(i['n'] for i in index)} trees, {max(i['bytes'] for i in index) / 1e3:.0f} kB)")


def report(d, n_bld, n_common, rec_ok):
    rep = {"trees": int(len(d)), "dated_by_buildings_nearby": n_bld, "species_from_common_name": n_common,
           "forms": np.bincount(d.form, minlength=3).tolist(), "sources": {}}
    for sid, t in d.groupby("source"):
        rep["sources"][sid] = {
            "city": SOURCES[sid]["city"], "trees": int(len(t)),
            "with_dbh": int((t.dbh_in > 0).sum()), "with_height": int((t.height_ft > 0).sum()),
            "with_crown": int((t.crown_ft > 0).sum()),
            "age_from": t.age_from.value_counts().to_dict(),
            "bounded_by": t.bounded_by.value_counts().to_dict(),
            "exact": int((t.confidence == 0).sum()),
            "year_quartiles": [round(float(v), 1) for v in np.percentile(t.year, [5, 25, 50, 75, 95])],
            "measured_median": round(float(np.nanmedian(t.measured)), 1) if t.measured.notna().any() else None,
        }
    p = INTERIM / "reports" / "region_trees.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rep, indent=1))
    log(f"region trees: report -> {p}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("download", "all"):
        download(sys.argv[2:] or None)
    if cmd in ("build", "all"):
        build()


if __name__ == "__main__":
    main()
