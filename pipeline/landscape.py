"""Stage: researched landscape history -> data/manual/landscape/ (dunes, water, agriculture).

Builds the geometry of three hand-researched layers from real maps, so the terrain can
stop using rules (bounding boxes, "every flat cell is a farm in 1852"):

  dunes        historic (pre-urban) sand dunes: SFEI Hidden Nature SF (2021) for northern
               San Francisco, USGS geologic maps (Bonilla 1998 OF 98-354; Witter et al. 2006
               OF 2006-1037; Knudsen et al. 2000 OF 00-444) for the rest of the region
  water        water_history.csv: lakes, dredged channels, salt ponds, diked baylands with
               researched dates (rings from OpenStreetMap water via Overture, SFEI baylands)
  agriculture  agriculture.geojson: Broek (1932) "Landscape types of the Santa Clara Valley
               1931" (traced), USGS 1939-56 topo orchards / vineyards
               (data/manual/farmsteads, read-only), and dated farm-district eras on the
               valley-floor geology (estimated)

Usage: python pipeline/landscape.py [dunes|water|agriculture|all]
Raw inputs live in data/raw/landscape/ (see data/manual/landscape/README.md for the
download list); every step is idempotent.
"""
from __future__ import annotations

import json
import sys
import tarfile

import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj
import shapely
from shapely.geometry import Polygon, box, mapping

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from common import INTERIM, MANUAL, RAW, log  # noqa: E402

LRAW = RAW / "landscape"
LINT = INTERIM / "landscape"
OUT = MANUAL / "landscape"
for d in (LRAW, LINT, OUT):
    d.mkdir(parents=True, exist_ok=True)

M = 3310  # California Albers (metres) for areas / buffers

# --------------------------------------------------------------------------- datum helpers
pyproj.datadir.append_data_dir(str(RAW / "proj"))
_NADCON = pyproj.Transformer.from_pipeline(
    "+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad "
    "+step +proj=hgridshift +grids=us_noaa_conus.tif +step +proj=unitconvert +xy_in=rad +xy_out=deg")


def nad27_to_wgs84(gs: gpd.GeoSeries) -> gpd.GeoSeries:
    """NAD27 (any CRS on the NAD27 datum, or naive lon/lat) -> EPSG:4326 through NADCON."""
    if gs.crs is None:
        gs = gs.set_crs(4267)
    if not gs.crs.equals(pyproj.CRS(4267)):
        gs = gs.to_crs(4267)

    def f(xy):
        x, y = _NADCON.transform(xy[:, 0], xy[:, 1])
        return np.column_stack([x, y])
    return gpd.GeoSeries(shapely.transform(gs.values, f), index=gs.index, crs=4326)


def read_tar_shp(tar_path, stem, workdir):
    workdir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path) as t:
        for ext in ("shp", "shx", "dbf"):
            name = f"{stem}.{ext}"
            if not (workdir / name).exists():
                t.extract(name, workdir, filter="data")
    return gpd.read_file(workdir / f"{stem}.shp")


def witter2006():
    """USGS OF 2006-1037 (Witter et al.) Quaternary polygons, EPSG:4326."""
    cache = LINT / "witter2006.parquet"
    if cache.exists():
        return gpd.read_parquet(cache)
    import zipfile
    z = RAW / "usgs_ofr2006_1037" / "of06-1037_4b.shp.zip"
    wd = LINT / "witter2006_shp"
    wd.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(z) as zz:
        for ext in ("shp", "shx", "dbf"):
            if not (wd / f"sfq2py.{ext}").exists():
                zz.extract(f"sfq2py.{ext}", wd)
    g = gpd.read_file(wd / "sfq2py.shp")[["PTYPE", "PTYPE2", "geometry"]]
    g["geometry"] = nad27_to_wgs84(g.geometry.set_crs(4267, allow_override=True))
    g = g.set_crs(4326, allow_override=True)
    g.to_parquet(cache)
    return g


def knudsen2000():
    """USGS OF 00-444 (Knudsen et al.) nine-county Quaternary polygons, EPSG:4326."""
    cache = LINT / "knudsen2000.parquet"
    if cache.exists():
        return gpd.read_parquet(cache)
    g = read_tar_shp(LRAW / "of00-444_4c.tar.gz", "sf-qpys", LINT / "knudsen2000_shp")[["PTYPE", "geometry"]]
    g["geometry"] = nad27_to_wgs84(g.geometry.set_crs(4267, allow_override=True))
    g = g.set_crs(4326, allow_override=True)
    g.to_parquet(cache)
    return g


def bonilla1998():
    """USGS OF 98-354 (Bonilla) San Francisco South quadrangle geology, EPSG:4326.
    sfs_geol.parquet = the PAL layer of sfs-geol.e00 (decompressed with e00conv from the
    Debian e00compr package, read with GDAL/AVCE00), California zone III metres, NAD27."""
    cache = LINT / "bonilla1998.parquet"
    if cache.exists():
        return gpd.read_parquet(cache)
    g = gpd.read_parquet(LRAW / "sfs_geol.parquet")
    lcc = pyproj.CRS.from_proj4("+proj=lcc +lat_1=38.43333333333333 +lat_2=37.06666666666667 +lat_0=36.5 "
                                "+lon_0=-120.5 +x_0=609601.2192024384 +y_0=0 +datum=NAD27 +units=m +no_defs")
    g = g.set_crs(lcc, allow_override=True)
    g["geometry"] = nad27_to_wgs84(g.geometry.to_crs(4267))
    g = g.set_crs(4326, allow_override=True)[["PTYPE", "geometry"]]
    g.to_parquet(cache)
    return g


def ring_str(poly, nd=5):
    """Exterior ring of a polygon as 'lon lat; lon lat; ...' (not closed)."""
    xs, ys = poly.exterior.coords.xy
    pts = list(zip(xs, ys))[:-1]
    return "; ".join(f"{x:.{nd}f} {y:.{nd}f}" for x, y in pts)


def explode_polys(geom):
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if hasattr(geom, "geoms"):
        out = []
        for g in geom.geoms:
            out += explode_polys(g)
        return out
    return []


def write_geojson(gdf: gpd.GeoDataFrame, path, precision=6):
    gdf = gdf.to_crs(4326)
    feats = []
    for _, r in gdf.iterrows():
        props = {k: (None if (isinstance(v, float) and not np.isfinite(v)) else
                     (int(v) if isinstance(v, (np.integer,)) else (float(v) if isinstance(v, np.floating) else v)))
                 for k, v in r.items() if k != "geometry"}
        geom = shapely.set_precision(r.geometry, 10 ** -precision)
        if geom.is_empty:
            continue
        feats.append({"type": "Feature", "properties": props, "geometry": mapping(geom)})
    path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")))
    log(f"{path.name}: {len(feats)} features")


# =========================================================================== dunes
SFEI_DUNES = {"Mobile dunes": "mobile_dune", "Stabilized dune/dune scrub/grassland": "stabilized_dune",
              "Dune slack": "dune_slack"}
URL_SFEI_HN = "https://www.sfei.org/projects/hidden-nature-sf"
URL_BONILLA = "https://pubs.usgs.gov/of/1998/of98-354/"
URL_WITTER = "https://pubs.usgs.gov/of/2006/1037/"
URL_KNUDSEN = "https://pubs.usgs.gov/of/2000/of00-444/"


def dunes():
    rows = []
    # 1. northern San Francisco: SFEI Hidden Nature SF habitats (pre-colonial)
    h = gpd.read_file(RAW / "sfei_hidden_nature_sf" / "sf_historical_habitats_2021.geojson").to_crs(4326)
    hd = h[h.HabitatCla.isin(SFEI_DUNES)]
    for _, r in hd.iterrows():
        for p in explode_polys(r.geometry):
            rows.append(dict(kind=SFEI_DUNES[r.HabitatCla], name="San Francisco dune sheet", region="San Francisco",
                             unit=r.HabitatCla, year_start=None, year_end=None, confidence="mapped",
                             source="sfei_hidden_nature_sf",
                             source_url=URL_SFEI_HN,
                             note="SFEI Hidden Nature SF (2021) pre-colonial habitat map; mobile-dune inland edge also "
                                  "surveyed 1852 and 1873 (US Coast Survey). Levelled / built over by district: "
                                  "buildings, parks (Golden Gate Park 1871-1900s) and golf courses date it.",
                             geometry=p))
    sfei_cover = shapely.union_all(list(hd.to_crs(M).geometry.buffer(30)))
    sfei_extent = box(*h.total_bounds)
    # 2. southern San Francisco / Daly City: Bonilla 1998 (SF South quadrangle)
    b = bonilla1998()
    bq = b[b.PTYPE == "Qd"]
    for p in explode_polys(shapely.union_all(list(bq.geometry))):
        pm = gpd.GeoSeries([p], crs=4326).to_crs(M).iloc[0].difference(sfei_cover)
        for q in explode_polys(gpd.GeoSeries([pm], crs=M).to_crs(4326).iloc[0]):
            if gpd.GeoSeries([q], crs=4326).to_crs(M).area.iloc[0] < 2000:
                continue
            c = q.representative_point()
            name = ("Lake Merced / Fort Funston dunes" if c.y > 37.69 else "Daly City / Mussel Rock coastal dunes")
            rows.append(dict(kind="mobile_dune", name=name, region="San Francisco / San Mateo", unit="Qd",
                             year_start=None, year_end=None, confidence="mapped", source="usgs_of98_354",
                             source_url=URL_BONILLA,
                             note="Bonilla (1998) unit Qd, dune sand (Holocene). Lake Merced dunes partly became golf "
                                  "courses 1915-1925 and Parkmerced / Stonestown 1940s-50s; Fort Funston still sand.",
                             geometry=q))
    # 2b. sand on the Colma Formation west of the Colma valley (Lake Merced east, Ingleside,
    #     Westlake): 'sand hills' before the tract builders levelled them (ESTIMATED extent)
    qc = b[b.PTYPE == "Qc"]
    # west of the Colma valley (roughly the Junipero Serra / I-280 corridor), south of the SFEI map
    westbox = Polygon([(-122.515, 37.650), (-122.490, 37.650), (-122.478, 37.668), (-122.468, 37.690),
                       (-122.458, 37.708), (-122.452, 37.725), (-122.455, 37.750), (-122.515, 37.750)])
    est = shapely.intersection(shapely.union_all(list(qc.geometry)), westbox)
    for p in explode_polys(est):
        pm = gpd.GeoSeries([p], crs=4326).to_crs(M)
        if pm.area.iloc[0] < 20000:
            continue
        rows.append(dict(kind="stabilized_dune", name="Lake Merced east / Ingleside / Westlake sand hills",
                         region="San Francisco / San Mateo", unit="Qc (Colma Formation) west of the Colma valley",
                         year_start=None, year_end=None, confidence="estimated", source="usgs_of98_354",
                         source_url=URL_BONILLA,
                         note="ESTIMATED: the Colma Formation (Pleistocene beach / dune sand) west of the Colma valley "
                              "carried wind-blown sand hills with dune scrub before the tract builders (Parkside, "
                              "Ingleside Terraces 1910s, Stonestown / Parkmerced 1940s-50s, Doelger's Westlake 1949-) "
                              "levelled them; the extent is the geologic unit clipped to the west side of the Colma valley (Junipero Serra / I-280 corridor) between Daly City (37.65) and the Sunset.",
                         geometry=p))
    bon_cover = shapely.union_all([r["geometry"] for r in rows])
    # 3. Witter 2006 (central Bay region): Merritt Sand (Alameda / Oakland / Bay Farm), coast
    w = witter2006()
    wd = w[w.PTYPE.isin(["Qds", "Qhds"]) | (w.PTYPE.str.startswith("a") & w.PTYPE2.astype(str).str.contains("ds"))]
    for _, r in wd.iterrows():
        for p in explode_polys(r.geometry):
            if p.intersects(sfei_extent) and p.representative_point().within(sfei_extent):
                continue  # SFEI is better in northern SF
            if p.representative_point().within(bon_cover.buffer(0.002)):
                continue
            c = p.representative_point()
            kind, name, region, note = dune_label(c.x, c.y, r.PTYPE, r.PTYPE2)
            rows.append(dict(kind=kind, name=name, region=region, unit=f"{r.PTYPE}" + (f" over {r.PTYPE2}" if r.PTYPE != r.PTYPE2 else ""),
                             year_start=None, year_end=None, confidence="mapped", source="usgs_of2006_1037",
                             source_url=URL_WITTER, note=note, geometry=p))
    # 4. Knudsen 2000 (nine counties) where Witter 2006 doesn't map: Delta, Point Reyes, Ano Nuevo
    k = knudsen2000()
    kd = k[k.PTYPE.isin(["Qds", "Qhds", "ads"])]
    wfoot = w[w.PTYPE != "nm"]
    kd = kd.copy()
    kd["rp"] = kd.geometry.representative_point()
    inside = gpd.sjoin(gpd.GeoDataFrame(geometry=kd.rp, crs=4326), wfoot[["geometry"]], predicate="within", how="inner")
    kd = kd[~kd.index.isin(inside.index)]
    for _, r in kd.iterrows():
        for p in explode_polys(r.geometry):
            c = p.representative_point()
            if c.within(sfei_extent):
                continue
            kind, name, region, note = dune_label(c.x, c.y, r.PTYPE, r.PTYPE)
            rows.append(dict(kind=kind, name=name, region=region, unit=r.PTYPE, year_start=None, year_end=None,
                             confidence="mapped", source="usgs_of00_444", source_url=URL_KNUDSEN, note=note, geometry=p))
    g = gpd.GeoDataFrame(rows, crs=4326)
    # 5. Antioch Dunes: the tall active dunes on the San Joaquin river front (ESTIMATED strip)
    strip = Polygon([(-121.822, 38.0105), (-121.765, 38.0135), (-121.765, 38.0215), (-121.822, 38.0195)])
    ad = shapely.intersection(shapely.union_all(list(g[g.region == "Contra Costa (Delta)"].geometry)), strip)
    for p in explode_polys(ad):
        g = pd.concat([g, gpd.GeoDataFrame([dict(
            kind="mobile_dune", name="Antioch Dunes (river-front dunes)", region="Contra Costa (Delta)", unit="Qds (river-front strip)",
            year_start=None, year_end=None, confidence="estimated", source="usgs_of00_444",
            source_url="https://www.fws.gov/refuge/antioch-dunes",
            note="ESTIMATED strip of the Qds sand sheet along the river: dunes up to ~120 ft high, quarried for sand from the "
                 "late 1800s (bricks for San Francisco after 1906) and built over by industry; ~55 acres remain in the "
                 "Antioch Dunes NWR (1980). Mobile sand only on this river front; the sand sheet inland was farmed.",
            geometry=p)], crs=4326)], ignore_index=True)
    g["area_ha"] = (g.to_crs(M).area / 1e4).round(2)
    g = g[g.area_ha >= 0.2].reset_index(drop=True)
    write_geojson(g, OUT / "dunes.geojson")
    log("dunes by kind/region:\n" + g.groupby(["region", "kind"]).area_ha.sum().round(0).to_string())


def dune_label(x, y, ptype, ptype2):
    """Name / kind / region for a geologic dune-sand polygon by location."""
    under_fill = str(ptype).startswith("a")
    fill_note = " Under artificial fill today." if under_fill else ""
    if -122.33 < x < -122.20 and 37.72 < y < 37.83:
        if y < 37.745:
            return ("stabilized_dune", "Bay Farm Island sand ridges", "Alameda",
                    "Merritt Sand (late Pleistocene dune / beach sand). Bay Farm Island: low sand ridges and dunes between "
                    "marsh, farmed for asparagus and vegetables from the 1880s until the 1950s fills." + fill_note)
        if y < 37.79 and x > -122.3:
            return ("stabilized_dune", "Alameda peninsula ('Encinal') sand ridge", "Alameda",
                    "Merritt Sand ridge of the Alameda peninsula: oak groves on sand ('Encinal de San Antonio', coast live "
                    "oak), not open dunes; town of Alameda from 1853, Tidal Canal made it an island 1902." + fill_note)
        return ("stabilized_dune", "Oakland Merritt Sand (downtown / Lake Merritt)", "Alameda",
                "Merritt Sand under downtown Oakland and around Lake Merritt: grass and coast live oak ('Oakland') on "
                "sand, not open dunes; town laid out 1852-53." + fill_note)
    if x > -121.9:
        return ("stabilized_dune", "Antioch - Oakley - Brentwood sand sheet", "Contra Costa (Delta)",
                "Latest Pleistocene - Holocene wind-blown sand of the Delta edge (Oakley / Knightsen / Antioch): vegetated "
                "sand plain, farmed for vineyards, almonds and melons from the 1890s; only the river-front Antioch Dunes "
                "were tall open dunes." + fill_note)
    if x < -122.85:
        return ("mobile_dune", "Point Reyes / Tomales coastal dunes", "Marin",
                "Coastal dunes (Point Reyes Beach, Abbotts Lagoon, Limantour, Dillon Beach); partly stabilized by planted "
                "European beachgrass and ice plant in the 20th century." + fill_note)
    if y < 37.3:
        return ("mobile_dune", "Ano Nuevo / south San Mateo coast dunes", "San Mateo",
                "Active coastal dune field (Ano Nuevo); still sand." + fill_note)
    if x < -122.44:
        return ("mobile_dune", "San Mateo / Marin coast dunes", "San Mateo / Marin",
                "Coastal dunes behind the beaches (Sharp Park / Salada / Linda Mar in Pacifica, Half Moon Bay, Stinson "
                "Beach spit); built over or planted from the 1900s." + fill_note)
    return ("stabilized_dune", "Bay-side dune sand", "Bay Area", "Dune sand mapped by the USGS." + fill_note)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("dunes", "all"):
        dunes()
    if what in ("water", "all"):
        from landscape_water import water
        water()
    if what in ("agriculture", "all"):
        from landscape_agriculture import agriculture
        agriculture()
