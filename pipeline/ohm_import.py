"""Tool: bring OpenHistoricalMap (OHM, CC0) data for the core Bay Area into the project's formats.

OHM (https://www.openhistoricalmap.org/, data CC0 1.0) is a volunteer-traced, dated world map. Its Overpass
API (https://overpass-api.openhistoricalmap.org/api/interpreter) is queried here with small bbox queries and
pauses. What is useful for this project, and what this tool writes:

  goldrush   Gold-rush San Francisco: buildings traced by OHM volunteers from the U.S. Coast Survey's "City of
             San Francisco and its Vicinity" (Cutts / Rodgers, survey completed April 1852, published 1853;
             David Rumsey 3463.000), the Huntington's "Map of the Burnt District of San Francisco" (fire of
             4 May 1851) and the Sanborn 1887 vol. 1 (LoC, georeferenced on oldinsurancemaps.net). OHM's
             start / end dates on these are placeholders (1840 / 1864 "arbitrary"), so every building is re-dated
             here from evidence (map year, the 1851 fires, Yerba Buena Cove fill, the researched built-up extents,
             the 1906 fire, today's buildings) and written in the Sanborn tracing format
             (data/manual/sanborn/sf_goldrush_<map year>.geojson + sf_goldrush_coverage.geojson) that
             sf_predecessors.apply_sanborn reads.
  stanford   Stanford campus: OHM's import of the university's building outlines ("LSJUbldgs", 2,973 ways) with
             dates read off the 1934 and 1962 campus maps or cited (Stanford Daily, Wikipedia...). Matched to
             today's Overture footprints -> data/manual/ohm/known_dates_ohm.csv (format of
             data/tables/known_building_dates_region.csv) and the 1934-map evidence as bounds
             (stanford_bounds_ohm.csv); buildings gone today -> data/manual/ohm/demolished_ohm.geojson.
  extras     Other well-dated OHM features we lack (railways and horse / street railways, wharves, a WWI camp,
             SFO's vanished terminals...) -> data/manual/ohm/*.

Usage:  python pipeline/ohm_import.py download     # Overpass -> data/raw/ohm/*.json (cached)
        python pipeline/ohm_import.py goldrush
        python pipeline/ohm_import.py stanford
        python pipeline/ohm_import.py extras
        python pipeline/ohm_import.py railextract  # OHM ways of lost railways in the new counties ->
                                                    # data/raw/historic_rail/h2_ohm_newarea.json (historic_rail_trace.py)
        python pipeline/ohm_import.py newarea      # review list of dated OHM features in the new counties
        python pipeline/ohm_import.py all
"""
from __future__ import annotations

import glob
import json
import re
import sys
import time
import zlib
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import linemerge, polygonize, unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import INTERIM, MANUAL, RAW, TABLES, log, session  # noqa: E402

OHM_RAW = RAW / "ohm"
OHM_OUT = MANUAL / "ohm"
SANBORN = MANUAL / "sanborn"
OVERPASS = "https://overpass-api.openhistoricalmap.org/api/interpreter"
UTM = "EPSG:32610"
OHM_WAY = "https://www.openhistoricalmap.org/way/"
OHM_REL = "https://www.openhistoricalmap.org/relation/"

SF_BBOX = (37.70, -122.52, 37.835, -122.355)  # s, w, n, e
STANFORD_BBOX = (37.395, -122.205, 37.445, -122.145)
# the core Bay Area (pipeline/extent.py) in four boxes
REGION_BOXES = [(37.08, -123.1, 37.65, -122.3), (37.65, -123.1, 38.22, -122.3),
                (37.08, -122.3, 37.65, -121.54), (37.65, -122.3, 38.22, -121.54)]
# the ten-county extent of 2026-11 (Sonoma, Napa, Solano, Santa Cruz, east Contra Costa, south Santa Clara):
# what the core boxes leave out, downloaded 2026-11-10
NEW_AREA_BOXES = [(38.22, -123.67, 38.90, -122.3), (38.22, -122.3, 38.90, -121.17),
                  (36.79, -122.45, 37.08, -121.17), (37.08, -121.54, 38.22, -121.17)]
REGION_BOXES = REGION_BOXES + NEW_AREA_BOXES


def h01(key: str, salt: str = "") -> float:
    return (zlib.crc32(f"{salt}{key}".encode()) % 100003) / 100003.0


# ------------------------------------------------------------------ download
def overpass(query: str, path: Path, pause=6.0):
    if path.exists() and path.stat().st_size > 200:
        return path
    s = session()
    for attempt in range(4):
        r = s.post(OVERPASS, data={"data": query}, timeout=330)
        if r.status_code == 200 and '"elements"' in r.text[:2000]:
            path.write_text(r.text)
            log(f"ohm: {path.name} {len(r.text) / 1e6:.1f} MB")
            time.sleep(pause)
            return path
        log(f"ohm: HTTP {r.status_code} ({attempt + 1}), waiting")
        time.sleep(30 * (attempt + 1))
    raise RuntimeError(f"Overpass failed for {path.name}")


def bbox_str(b):
    return ",".join(str(x) for x in b)


def download():
    OHM_RAW.mkdir(parents=True, exist_ok=True)
    b = bbox_str(SF_BBOX)
    overpass(f'[out:json][timeout:240];(way["building"]({b});relation["building"]({b}););out geom;',
             OHM_RAW / "ohm_sf_buildings.json")
    for box in REGION_BOXES:
        n = bbox_str(box).replace(",", "_").replace(".", "_").replace("-", "_")
        overpass(f"[out:json][timeout:240];(way({bbox_str(box)});relation({bbox_str(box)}););out tags bb;",
                 OHM_RAW / f"tags_{n}.json")
        overpass('[out:json][timeout:280];(way[~"^(start_date|end_date)$"~"."][!boundary][!waterway][!"natural"]'
                 f'({bbox_str(box)});relation[~"^(start_date|end_date)$"~"."][!boundary][type!=chronology]'
                 f'({bbox_str(box)}););out geom;', OHM_RAW / f"geom_{n}.json")
    # SF waterfront wharves / piers (gold-rush wharves of the 1851 Burnt District map)
    overpass(f'[out:json][timeout:200];(way["man_made"~"pier|quay|wharf"]({b});way["shoreline"]({b}););out geom;',
             OHM_RAW / "ohm_sf_wharves.json")


# ------------------------------------------------------------------ OSM JSON -> geometries
def _line(geom):
    return [(p["lon"], p["lat"]) for p in geom if p]


def _rings_to_polys(outer_lines, inner_lines):
    outers = list(polygonize(unary_union([LineString(c) for c in outer_lines if len(c) >= 2]))) if outer_lines else []
    inners = list(polygonize(unary_union([LineString(c) for c in inner_lines if len(c) >= 2]))) if inner_lines else []
    if not outers:
        return None
    polys = []
    for o in outers:
        holes = [i for i in inners if o.contains(i.representative_point())]
        p = o.difference(unary_union(holes)) if holes else o
        polys.append(p)
    g = unary_union(polys)
    return shapely.make_valid(g)


AREA_KEYS = ("building", "landuse", "leisure", "amenity", "place", "aeroway", "man_made", "military", "area",
             "natural", "boundary")


def element_geometry(e, area_hint=True):
    """Shapely geometry of an Overpass `out geom` element (lon/lat)."""
    t = e.get("tags", {})
    if e["type"] == "way":
        c = _line(e.get("geometry", []))
        if len(c) < 2:
            return None
        closed = len(c) >= 4 and c[0] == c[-1]
        is_area = closed and area_hint and (any(k in t for k in AREA_KEYS) and t.get("area") != "no"
                                            and not (t.get("man_made") in ("pier", "breakwater", "groyne") and
                                                     t.get("area") != "yes" and False))
        if is_area:
            p = Polygon(c)
            return shapely.make_valid(p) if not p.is_valid else p
        return LineString(c)
    if e["type"] == "relation":
        outer, inner, lines = [], [], []
        for m in e.get("members", []):
            if m.get("type") != "way" or not m.get("geometry"):
                continue
            c = _line(m["geometry"])
            if len(c) < 2:
                continue
            role = m.get("role", "")
            if role == "inner":
                inner.append(c)
            elif role == "outer":
                outer.append(c)
            else:
                lines.append(c)
        if t.get("type") in ("multipolygon", "boundary") or outer:
            return _rings_to_polys(outer or lines, inner)
        if lines:
            u_ = unary_union([LineString(c) for c in lines])
            return linemerge(u_) if u_.geom_type == "MultiLineString" else u_
    return None


def load_elements(paths):
    els = {}
    for f in paths:
        for e in json.load(open(f))["elements"]:
            els[(e["type"], e["id"])] = e
    return els


def to_gdf(els, keep=None):
    rows = []
    for (typ, i), e in els.items():
        if e["type"] not in ("way", "relation"):
            continue
        t = e.get("tags", {})
        if keep is not None and not keep(t):
            continue
        g = element_geometry(e)
        if g is None or g.is_empty:
            continue
        rows.append({"osm_type": typ, "osm_id": i, "tags": t, "geometry": g})
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=4326)


def ohm_url(typ, i):
    return (OHM_WAY if typ == "way" else OHM_REL) + str(i)


def year_of(s):
    """First 4-digit year in an OHM date ('1851-05-04' -> 1851.34, '1840' -> 1840.0, '/1851' -> 1851.0)."""
    if s is None:
        return np.nan
    m = re.search(r"(-?\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", str(s))
    if not m:
        return np.nan
    y = float(m.group(1))
    if m.group(2):
        y += (int(m.group(2)) - 1) / 12.0 + ((int(m.group(3)) - 1) / 365.0 if m.group(3) else 0.0)
    return round(y, 3)


# ================================================================== gold-rush San Francisco
GR_AREA = "sf_goldrush"
# the maps the OHM volunteers traced (cited on every OHM way), with the date the drawing shows
GR_MAPS = {
    1851: {"date": 1851.33, "label": "Map of the Burnt District of San Francisco (fire of 4 May 1851)",
           "volume": "huntington_p9539coll1_23520", "volume_label": "1851 Burnt District map (Huntington)",
           "url": "https://hdl.huntington.org/digital/collection/p9539coll1/id/23520"},
    1852: {"date": 1852.3, "label": "U.S. Coast Survey, City of San Francisco and its Vicinity (survey completed "
                                    "April 1852, publ. 1853; Rumsey 3463.000)",
           "volume": "rumsey_3463000", "volume_label": "USCS 1853 chart (survey to April 1852)",
           "url": "https://www.davidrumsey.com/luna/servlet/detail/RUMSEY~8~1~2210~180022"},
    1887: {"date": 1887.0, "label": "Sanborn Map Company, San Francisco 1887, vol. 1 (LoC)",
           "volume": "sanborn00813_1887_v1", "volume_label": "1887 Vol. 1",
           "url": "https://www.loc.gov/resource/g4364sm.g4364sm_g00813188701/"},
}
OIM_PAGES = {"70216": "p13R", "70185": "p10R", "70189": "p15R", "70191": "p11L", "70181": "p15L", "70147": "p3L",
             "70120": "p1R"}
MAY_1851 = 1851.34    # fire of 3-4 May 1851 (began ~11 pm on 3 May)
JUNE_1851 = 1851.47   # fire of 22 June 1851
FIRE_1906 = 1906.29
GOLD_RUSH = 1849.0    # the generated fabric and the extent snapshots start with the 1849 boom
# 22 June 1851 fire: "Powell, Sansome, Clay and Broadway ... ten blocks and portions of six others"
# (SFFD Guardians of the City, https://guardiansofthecity.org/sffd/fires/great_fires/june_22_1851.html)
JUNE_1851_RING = "Powell St & Broadway; Sansome St & Broadway; Sansome St & Clay St; Powell St & Clay St"
GR_HEADER = ["id", "map_year", "volume", "volume_label", "sheet", "sheet_no", "loc_url", "iiif", "stories",
             "stories_source", "material", "use", "use_source", "name", "address", "sanborn_colour", "confidence",
             "georef", "georef_rms_m", "extraction", "area_m2", "modern_overlap"]


def gr_group(t):
    s, u = t.get("source", "") or "", t.get("source:url", "") or ""
    if "RUMSEY~8~1~2210~180022" in s or (t.get("source:1", "") or "").startswith("1853 USGS"):
        return 1852, "rumsey"
    if s == "1853 Coast Survey" and "pastmapper" in (t.get("source:1", "") or ""):
        return 1852, "pastmapper"
    if "Burnt District" in s:
        return 1851, "burnt"
    if "oldinsurancemaps.net/layer/70" in u or (t.get("start_date") == "1887" and not s):
        return 1887, "sanborn"
    return None, None


def sf_blocks():
    """Today's SF blocks (DataSF parcels dissolved by assessor block), UTM."""
    lots = gpd.read_parquet(INTERIM / "sf_parcels_active.parquet", columns=["mapblklot", "geometry"]).to_crs(UTM)
    lots["block"] = lots.mapblklot.astype(str).str[:4]
    blk = lots.dissolve("block").reset_index()[["block", "geometry"]]
    blk["geometry"] = blk.buffer(0.3)
    return blk


def fill_bands():
    """SF bay-fill zones (data/manual/fill_zones.csv) as UTM polygons with their years."""
    from geocode import ring_polygon
    t = pd.read_csv(MANUAL / "fill_zones.csv")
    t = t[t.region.astype(str).str.contains("San Francisco")]
    rows = []
    for r in t.itertuples():
        try:
            p = ring_polygon(r.ring, r.ring_type, crs=UTM)
        except Exception:  # noqa: BLE001
            p = None
        if p is not None and not p.is_empty:
            rows.append({"zone_id": r.zone_id, "kind": r.kind, "ys": float(r.year_start), "ye": float(r.year_end),
                         "geometry": p})
    return gpd.GeoDataFrame(rows, crs=UTM)


def land_year_detail(lon, lat):
    """Terrain land year (year the ground became dry land) from the SF detail grid; the live grid is
    being rebuilt, so the last complete one (data/interim/bak_detail_grid) is preferred."""
    for d in (INTERIM / "bak_detail_grid", INTERIM):
        p, m = d / "grid_detail_landyear.npy", d / "grid_detail_meta.json"
        if p.exists() and m.exists():
            g = json.loads(m.read_text())
            ly = np.load(p)
            if ly.shape != (g["rows"], g["cols"]):
                continue
            X = np.radians(lon) * 6378137.0
            Y = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))
            c = np.rint((X - g["X0"]) / g["res"]).astype(int)
            r = np.rint((g["Y0"] - Y) / g["res"]).astype(int)
            ok = (c >= 0) & (r >= 0) & (c < g["cols"]) & (r < g["rows"])
            out = np.full(len(lon), np.nan)
            out[ok] = ly[r[ok], c[ok]]
            return out
    return np.full(len(lon), np.nan)


def frac_covered(g, F, sidx):
    tot = 0.0
    for j in sidx.query(g, predicate="intersects"):
        tot += g.intersection(F.geometry.values[j]).area
    return tot / max(g.area, 1e-6)


def _material_1851(t):
    m = (t.get("building:material") or t.get("material") or "").lower()
    d = (t.get("description") or "").lower()
    if "brick" in m or "brick" in d or m == "mixed":
        return "brick", "OHM building:material / map key (brick, or brick and iron)"
    if m == "metal" or "iron" in d:
        return "iron", "OHM building:material / map key (iron building)"
    if m == "wood" or "wood" in d:
        return "frame", "OHM building:material / map key (wood building)"
    return "frame", "default (gold-rush frame)"


def _use_1851(t):
    d = (t.get("description") or "").lower()
    if "ship" in d:
        return "storeship", "map key (grounded ship used as a storehouse)"
    if t.get("building") == "warehouse":
        return "warehouse", "OHM building=warehouse"
    if t.get("tourism") == "hotel":
        return "hotel", "OHM tourism=hotel"
    if "store" in d:
        return "store", "map key (store building)"
    if "office" in (t.get("name") or "").lower():
        return "office", "OHM name"
    if "house" in d:
        return "dwelling", "map key (house)"
    return "", "not given"


USE_1887 = {"house": "dwelling", "apartments": "flats", "commercial": "store", "warehouse": "warehouse",
            "stable": "stable", "hotel": "hotel", "church": "church", "temple": "church", "shed": "shed",
            "industrial": "factory", "construction": ""}


def _stories_default(mapy, use, mat, area, key):
    """Storeys where the map gives none (rules from data/manual/sf_extent_README.md: gold-rush frame 1-2
    storeys; the brick and iron stores of the 1851 rebuild 2; Sanborn 1887 Chinatown / downtown 2-3)."""
    if use in ("shed", "stable", "storeship") or area < 35:
        return 1, f"default (rule: {use or 'small'} -> 1)"
    if mapy <= 1852:
        if mat == "brick":
            return 2, "default (rule: gold-rush brick -> 2)"
        if mat == "iron":
            return (1 if area < 90 else 2), "default (rule: prefabricated iron store, 1 if < 90 m2)"
        return (2 if h01(key, "st") < 0.4 else 1), "default (rule: gold-rush frame 1-2, 40 % two-storey)"
    if use in ("flats", "hotel"):
        return 3, f"default (rule: {use} -> 3)"
    if use == "dwelling":
        return 2, "default (rule: dwelling -> 2)"
    return (3 if area > 250 else 2), "default (rule: commercial 2, 3 when > 250 m2)"


def _window_pick(lo, hi, u0, u1, key, salt):
    """A year inside [lo, hi], placed by the hash in the sub-range [u0, u1] of the window."""
    u = u0 + (u1 - u0) * h01(key, salt)
    return float(lo + (hi - lo) * u)


def goldrush():
    """Re-date OHM's gold-rush San Francisco tracings and write them in the Sanborn tracing format."""
    from geocode import intersection_rings, ring_polygon
    els = load_elements([OHM_RAW / "ohm_sf_buildings.json"])
    g = to_gdf(els)
    gg = g.tags.map(gr_group)
    g["map_year"] = [a for a, _ in gg]
    g["grp"] = [b for _, b in gg]
    g = g[g.map_year.notna()].copy()
    # Mission Dolores (1791) is a reconstructed landmark (viewer/src/landmarks/city.ts): not a predecessor
    g = g[~g.tags.map(lambda t: t.get("place") == "mission" or "Mission Dolores" in (t.get("name") or ""))]
    g = g.explode(index_parts=False)
    g = g[g.geom_type == "Polygon"]
    u = g.to_crs(UTM).reset_index(drop=True)
    u["geometry"] = u.geometry.buffer(0)
    u = u[u.geometry.area > 4].reset_index(drop=True)
    u["key"] = [f"{t}{i}" for t, i in zip(u.osm_type.str[0], u.osm_id)]
    # duplicate ways (a multipolygon and its outer way): keep one
    u = u.drop_duplicates("key").reset_index(drop=True)
    log(f"goldrush: {len(u)} traced footprints: " + ", ".join(f"{int(k)} map {v}" for k, v in u.map_year.value_counts().items()))
    ll = u.to_crs(4326).geometry.representative_point()
    rp = u.geometry.representative_point()

    # ---- evidence layers
    fire = gpd.read_file(INTERIM / "fire_1906.geojson").to_crs(UTM)
    burned06 = rp.within(shapely.union_all(fire.geometry.values)).values
    rings = {int(Path(f).stem.split("_")[-1]): shapely.union_all(list(intersection_rings(f, crs=UTM).values()))
             for f in sorted(glob.glob(str(MANUAL / "sf_extent_*.csv")))}
    ext_years = sorted(rings)
    first_ring = np.full(len(u), np.nan)
    for y in reversed(ext_years):
        first_ring[rp.within(rings[y]).values] = y
    in1849 = rp.within(rings[1849]).values
    in1852 = rp.within(rings[1852]).values
    bands = fill_bands()
    ys_fill = np.full(len(u), np.nan)
    ye_fill = np.full(len(u), np.nan)
    band_id = np.array([""] * len(u), dtype=object)
    for b in bands[(bands.kind == "fill") & ~bands.zone_id.str.startswith("fb_")].itertuples():
        m = rp.within(b.geometry).values & (np.isnan(ys_fill) | (b.ys < ys_fill))
        ys_fill[m], ye_fill[m], band_id[m] = b.ys, b.ye, b.zone_id
    land = land_year_detail(ll.x.values, ll.y.values)
    tagged51 = u.tags.map(lambda t: t.get("start_date:edtf") == "1851/").values
    m51 = u[(u.map_year == 1851)]
    burnt_may = shapely.union_all(list(m51.geometry.buffer(30).values) +
                                  list(u[tagged51].geometry.buffer(30).values)).buffer(-18)
    june = ring_polygon(JUNE_1851_RING, "streets", crs=UTM)
    in_may = rp.within(burnt_may).values | tagged51
    in_june_any = rp.within(june).values
    in_june = in_june_any & ~in_may
    blocks = sf_blocks()
    bsidx = blocks.sindex
    in_blocks = np.array([frac_covered(gm, blocks, bsidx) for gm in u.geometry.values])
    today = gpd.read_parquet(INTERIM / "sf_buildings.parquet", columns=["start_year", "geometry"]).to_crs(UTM)
    tsidx = today.sindex
    t_start = today.start_year.values

    u_area0 = u.geometry.area.values.copy()
    maps = {y: u[u.map_year == y] for y in (1851, 1852, 1887)}
    msidx = {y: maps[y].sindex for y in maps}
    # ---- coverage per map
    cov = {}
    cov[1851] = burnt_may
    blk_hit = gpd.sjoin(gpd.GeoDataFrame(geometry=maps[1852].geometry.representative_point(), crs=UTM),
                        blocks, predicate="within").block.unique()
    cov[1852] = shapely.union_all(list(blocks[blocks.block.isin(blk_hit)].geometry.values) +
                                  list(maps[1852].geometry.buffer(10).values))
    j87 = gpd.sjoin(maps[1887][["geometry"]], blocks, predicate="intersects")
    share = {}
    for b_, grp_ in j87.groupby("block"):
        bg = blocks.geometry.values[blocks.index[blocks.block == b_][0]]
        share[b_] = shapely.union_all(grp_.geometry.values).intersection(bg).area / max(bg.area, 1)
    full87 = [b_ for b_, s in share.items() if s >= 0.3]
    cov[1887] = shapely.union_all(list(blocks[blocks.block.isin(full87)].geometry.values) +
                                  list(maps[1887].geometry.buffer(8).values))

    # ---- chain the maps
    # 1851 survivors: the 1852 chart draws whole block fronts as one black mass, so a survivor is "still
    # there" when the 1852 footprints cover >= 40 % of it (as apply_sanborn); it then keeps its own, more
    # detailed outline and is cut out of the 1852 masses. 1852 -> 1887 (35 years apart; the Sanborn draws
    # every outbuilding): the same structure only when one 1887 footprint has about the same shape (IoU).
    idx = {y: list(maps[y].index) for y in maps}
    nxt = {}        # row -> row on the next map that represents it
    continues = {}  # 1851 survivor row -> True when the 1852 chart still shows it
    survivor = np.array([(m == 1851) and not t.get("end_date", "").startswith("1851-05-04")
                         for m, t in zip(u.map_year.values, u.tags.values)])
    for i in idx[1851]:
        if survivor[i] and rp.values[i].within(cov[1852]):
            continues[i] = frac_covered(u.geometry.values[i], maps[1852], msidx[1852]) >= 0.4
    surv_geom = shapely.union_all([u.geometry.values[i] for i, c in continues.items() if c] or [Polygon()])
    for i in idx[1852]:
        gm = u.geometry.values[i]
        if gm.intersects(surv_geom):
            rest = gm.difference(surv_geom.buffer(0.2))
            if rest.geom_type == "MultiPolygon":
                rest = max(rest.geoms, key=lambda q: q.area)
            u.loc[i, "geometry"] = rest if (not rest.is_empty and rest.area > 15 and rest.area > 0.2 * gm.area) else Polygon()
    for i in idx[1852]:
        gm = u.geometry.values[i]
        if gm.is_empty or not rp.values[i].within(cov[1887]):
            continue
        best, biou = None, 0.0
        for j in msidx[1887].query(gm, predicate="intersects"):
            g2 = maps[1887].geometry.values[j]
            iou = gm.intersection(g2).area / max(gm.union(g2).area, 1e-6)
            if iou > biou:
                best, biou = maps[1887].index[j], iou
        if biou >= 0.45:
            nxt[i] = best
    for i, c in continues.items():  # a surviving 1851 building carried on to the 1887 Sanborn
        if c and rp.values[i].within(cov[1887]):
            gm = u.geometry.values[i]
            for j in msidx[1887].query(gm, predicate="intersects"):
                g2 = maps[1887].geometry.values[j]
                if gm.intersection(g2).area / max(gm.union(g2).area, 1e-6) >= 0.45:
                    nxt[i] = maps[1887].index[j]
    prev = {}
    for i, j in nxt.items():
        prev.setdefault(j, []).append(i)

    def root_rows(i):
        out, stack = [], [i]
        while stack:
            k = stack.pop()
            out.append(k)
            stack += prev.get(k, [])
        return out

    rows = []
    for i in range(len(u)):
        t = u.tags.values[i]
        y = int(u.map_year.values[i])
        key = u.key.values[i]
        gm = u.geometry.values[i]
        area = gm.area
        ev = []
        # --- start window from the earliest map in the chain that shows this structure
        chain = root_rows(i)
        first = min(chain, key=lambda k: u.map_year.values[k])
        fy = int(u.map_year.values[first])
        fi = first
        hi = GR_MAPS[fy]["date"]
        if fy in (1851, 1852):
            lo = GOLD_RUSH
            ev.append(f"on the {GR_MAPS[fy]['label']} -> standing by {hi:.2f}")
            if fy == 1852 and in_may[fi] and not any(u.map_year.values[k] == 1851 for k in chain):
                lo = MAY_1851
                ev.append("inside the district burned on 4 May 1851 (Burnt District map; OHM start 1851/) -> built after the fire")
            elif fy == 1852 and in_june[fi]:
                lo = JUNE_1851
                ev.append("inside the 22 June 1851 fire area (Powell-Sansome-Clay-Broadway, SFFD) -> rebuilt after it (MEDIUM: ten of its sixteen blocks burned whole)")
            if np.isfinite(ys_fill[fi]):
                if ys_fill[fi] > lo:
                    lo = min(ys_fill[fi], hi - 0.2)
                ev.append(f"on Yerba Buena Cove fill band {band_id[fi]} ({ys_fill[fi]:g}-{ye_fill[fi]:g})")
            if in1849[fi]:
                u0, u1 = 0.0, 0.45
                ev.append("inside the 1849 built-up extent (sf_extent_1849) -> early in the window")
            elif in1852[fi]:
                u0, u1 = 0.25, 0.85
                ev.append("inside the 1852 extent, outside 1849 -> mid window")
            else:
                u0, u1 = 0.45, 1.0
                ev.append("outside the 1852 built-up extent (scattered building) -> late in the window")
            if lo >= MAY_1851 - 0.01:  # rebuilt after an 1851 fire: spread over the months to the survey
                u0, u1 = 0.0, 1.0
        else:  # first seen on the 1887 Sanborn
            if rp.values[fi].within(cov[1852]):
                lo, hi = GR_MAPS[1852]["date"], 1887.0
                ev.append("on the 1887 Sanborn, not on the 1852 Coast Survey chart of the same block -> built 1852-1887")
            else:
                fr = first_ring[fi]
                hi = min(fr, 1887.0) if np.isfinite(fr) else 1887.0
                pe = [e for e in ext_years if e < hi]
                lo = float(pe[-1]) if pe else GOLD_RUSH
                ev.append(f"on the 1887 Sanborn; block first inside the {int(hi) if np.isfinite(fr) else 'none'} "
                          f"built-up extent -> built {lo:g}-{hi:g}")
            u0, u1 = 0.0, 1.0
        start = _window_pick(lo, hi, u0, u1, u.key.values[fi], "s")
        start_conf = "estimated"
        # --- end
        end_rule, end_min, end_max = "successor", np.nan, np.nan
        represented_by = u.key.values[nxt[i]] if i in nxt else None
        if gm.is_empty:
            continue  # an 1852 mass that was all the outline of an 1851 survivor
        if y == 1851 and t.get("end_date", "").startswith("1851-05-04"):
            end, end_rule, end_min, end_max = MAY_1851, "exact", MAY_1851, MAY_1851
            ev.append("destroyed in the fire of 4 May 1851 (Burnt District map)")
        elif represented_by is not None:
            end = np.nan
            ev.append(f"still on the {int(u.map_year.values[nxt[i]])} map: carried by {represented_by}")
        elif y == 1851 and i in continues and not continues[i]:
            if in_june_any[i]:
                end, end_rule, end_min, end_max = JUNE_1851, "exact", JUNE_1851, JUNE_1851
                ev.append("survived 4 May 1851, not on the 1852 chart, inside the 22 June 1851 fire area -> burned 22 June 1851")
            else:
                end_min, end_max = GR_MAPS[1851]["date"] + 0.01, GR_MAPS[1852]["date"]
                end = _window_pick(end_min, end_max, 0.15, 0.9, key, "e")
                end_rule = "between_maps"
                ev.append("survived 4 May 1851 but not on the 1852 chart of the same block -> gone 1851-52")
        elif (y == 1852 or continues.get(i)) and rp.values[i].within(cov[1887]):
            end_min, end_max = GR_MAPS[1852]["date"], 1887.0
            end = _window_pick(end_min, end_max, 0.15, 0.9, key, "e")
            end_rule = "between_maps"
            ev.append("not on the 1887 Sanborn of the same block -> gone 1852-1887")
        else:
            end = np.nan
            if burned06[i]:
                end_max = FIRE_1906
                ev.append("inside the 1906 burned area -> gone by 18 Apr 1906 at the latest")
            later = []
            for j in tsidx.query(gm, predicate="intersects"):
                inter = gm.intersection(today.geometry.values[j]).area
                if inter > 0.2 * area and t_start[j] > GR_MAPS[y]["date"] + 1:
                    later.append(t_start[j])
            if later and (not np.isfinite(end_max) or min(later) - 0.3 < end_max):
                end_max = min(later) - 0.3
                ev.append(f"today's building on the spot built {min(later):.0f} -> gone before then")
            end = end_max
            if in_blocks[i] < 0.4:
                ev.append(f"{100 * (1 - in_blocks[i]):.0f} % of it lies in today's street right-of-way (wharf / "
                          "pile building or a later street opening)")
        # --- today's building that may be this one (left to the modern data, as apply_sanborn)
        same, best_iou = False, 0.0
        for j in tsidx.query(gm, predicate="intersects"):
            tg = today.geometry.values[j]
            inter = gm.intersection(tg).area
            iou = inter / max(gm.union(tg).area, 1e-6)
            best_iou = max(best_iou, iou)
            if (iou >= 0.5 or inter >= 0.7 * area) and t_start[j] <= GR_MAPS[y]["date"] + 2:
                same = True
        # --- attributes
        name = t.get("name") or t.get("owner")
        if y == 1852 and gm.area < u_area0[i] - 1:
            ev.append("outline cut around a surviving building of the 1851 Burnt District map")
        if y == 1851:
            mat, mat_src = _material_1851(t)
            use, use_src = _use_1851(t)
        elif y == 1887:
            mat, mat_src = "", "not given in OHM (Sanborn colour not transcribed)"
            use = USE_1887.get(t.get("building", ""), "")
            if "boarding" in (t.get("description") or "").lower():
                use = "flats"
            use_src = f"OHM building={t.get('building')}" if use else "not given"
        else:
            mat, mat_src = "frame", "default (gold-rush frame; the chart does not distinguish brick)"
            use, use_src = "", "not given (the chart draws no use)"
        lv = pd.to_numeric(t.get("building:levels"), errors="coerce")
        if np.isfinite(lv) and lv > 0:
            stories, st_src = float(lv), "OHM building:levels"
        else:
            stories, st_src = _stories_default(y, use, mat, area, key)
        page = ""
        if y == 1887:
            lay = re.search(r"layer/(\d+)", t.get("source:url", "") or "")
            page = OIM_PAGES.get(lay.group(1), "") if lay else ""
        lyv = land[i]
        if np.isfinite(lyv) and lyv > GR_MAPS[fy]["date"] + 0.5 and y <= 1852:
            ev.append(f"terrain land year here {lyv:.0f} is later than the map: on piles over the cove (or the fill band is dated too late)")
        rows.append({
            "id": f"ohm_{u.osm_type.values[i]}_{u.osm_id.values[i]}", "map_year": y,
            "volume": GR_MAPS[y]["volume"], "volume_label": GR_MAPS[y]["volume_label"],
            "sheet": page or None, "sheet_no": page or None,
            "loc_url": GR_MAPS[y]["url"], "iiif": None, "stories": stories, "stories_source": st_src,
            "material": mat, "use": use, "use_source": use_src, "name": name,
            "address": " ".join(x for x in (t.get("addr:housenumber"), t.get("addr:street")) if x) or None,
            "sanborn_colour": None, "confidence": "medium" if y != 1852 else "medium-high",
            "georef": f"OpenHistoricalMap {u.osm_type.values[i]} {u.osm_id.values[i]}", "georef_rms_m": None,
            "extraction": f"OpenHistoricalMap volunteer tracing (CC0) of the {GR_MAPS[y]['label']}; OHM dates "
                          f"{t.get('start_date')} / {t.get('end_date')} ({t.get('start_date:source') or 'no date source'}) "
                          "replaced by evidence-based dates",
            "area_m2": round(area, 1), "modern_overlap": round(best_iou, 2),
            "start_year": round(start, 2) if represented_by is None else None,
            "start_min": round(lo, 2), "start_max": round(hi, 2),
            "end_year": (round(end, 2) if np.isfinite(end) else None) if represented_by is None else None,
            "end_min": round(end_min, 2) if np.isfinite(end_min) else None,
            "end_max": round(end_max, 2) if np.isfinite(end_max) else None,
            "end_rule": end_rule if represented_by is None else "represented",
            "represented_by": represented_by, "modern_same": bool(same), "year_confidence": start_conf,
            "date_evidence": "; ".join(ev), "land_year": round(float(lyv), 1) if np.isfinite(lyv) else None,
            "fill_zone": band_id[i] or None, "in_street_row": round(1 - in_blocks[i], 2),
            "burned_1906": bool(burned06[i]), "ohm_key": key, "ohm_url": ohm_url(u.osm_type.values[i], u.osm_id.values[i]),
            "ohm_start_date": t.get("start_date"), "ohm_end_date": t.get("end_date"),
            "geometry": gm})
    out = gpd.GeoDataFrame(rows, crs=UTM)
    keyrow = {k: n for n, k in enumerate(out.ohm_key)}
    # docs: pre-gold-rush / notable buildings already in the tables
    docs = []
    for tab in ("early_sf.csv", "notable_pre1906.csv"):
        d = pd.read_csv(TABLES / tab)
        d = d[pd.to_numeric(d.lat, errors="coerce").notna()]
        d = gpd.GeoDataFrame(d[["id", "name", "start_year", "end_year"]], crs=4326,
                             geometry=gpd.points_from_xy(d.lon.astype(float), d.lat.astype(float))).to_crs(UTM)
        docs.append(d)
    docs = gpd.GeoDataFrame(pd.concat(docs, ignore_index=True), crs=UTM)
    # a documented building (point) is the traced footprint nearest to it (within 12 m) on a map drawn
    # while it stood; only footprints that are emitted (not carried by a later outline) are candidates
    out["doc_match"] = None
    emitted = out[out.represented_by.isna()]
    for d in docs.itertuples():
        s0, e0 = pd.to_numeric(d.start_year, errors="coerce"), pd.to_numeric(d.end_year, errors="coerce")
        cand = emitted[(emitted.map_year >= s0 - 1) & (emitted.map_year <= e0 + 1)]
        if not len(cand):
            continue
        dist = cand.geometry.distance(d.geometry)
        k = dist.idxmin()
        if dist[k] <= 12 and out.loc[k, "doc_match"] is None:
            out.loc[k, "doc_match"] = str(d.id)
    return out, cov, {"burnt_may": burnt_may, "june": june}


def _write_geojson(gdf, path, name):
    gdf = gdf.to_crs(4326)
    for c in gdf.columns:
        if c != "geometry" and gdf[c].dtype == object:
            gdf[c] = gdf[c].where(gdf[c].notna(), None)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    gdf.to_file(path, driver="GeoJSON", COORDINATE_PRECISION=7)
    log(f"ohm: wrote {path.relative_to(MANUAL.parent.parent)} ({len(gdf)})")


def write_goldrush():
    out, cov, aux = goldrush()
    out = out[out.geometry.notna() & ~out.geometry.is_empty]
    extra = [c for c in out.columns if c not in GR_HEADER + ["geometry"]]
    for y in (1851, 1852, 1887):
        part = out[out.map_year == y][GR_HEADER + extra + ["geometry"]].reset_index(drop=True)
        _write_geojson(part, SANBORN / f"{GR_AREA}_{y}.geojson", f"{GR_AREA}_{y}")
    notes = {
        1851: ("district burned on 4 May 1851: the traced buildings of the Burnt District map and the 1852-chart "
               "buildings OHM tags as built after the fire (start 1851/), closed by 30 m; generated buildings that "
               "start before the map date are replaced (apply_goldrush rule 'before_map')", ["Huntington p9539coll1/23520"]),
        1852: ("today's blocks holding a traced building of the 1852 chart (DataSF parcels by assessor block) plus "
               "10 m round each traced footprint (cove / wharf buildings); OHM traced the chart building by building "
               "over North Beach, downtown, Happy Valley / Rincon and scattered houses out to Mission Dolores; "
               "rule 'before_map'", ["Rumsey 3463.000 (USCS 1853, survey to April 1852)"]),
        1887: ("blocks at least 30 % covered by OHM's 1887 Sanborn tracings (whole blocks traced) plus 8 m round each "
               "traced building; rule 'after_1852': together with the 1852 chart these blocks are described by "
               "traced buildings from 1852 to the 1906 fire", sorted(set(OIM_PAGES.values()))),
    }
    feats = []
    for y in (1851, 1852, 1887):
        n = int((out.map_year == y).sum())
        feats.append({"area": GR_AREA, "map_year": y, "sheets": json.dumps(notes[y][1]), "features": n,
                      "map_date": GR_MAPS[y]["date"], "generated_rule": "after_1852" if y == 1887 else "before_map",
                      "note": notes[y][0], "geometry": cov[y]})
    c = gpd.GeoDataFrame(feats, crs=UTM)
    _write_geojson(c, SANBORN / f"{GR_AREA}_coverage.geojson", f"{GR_AREA}_coverage")
    fires = gpd.GeoDataFrame([
        {"fire": "4 May 1851", "year": MAY_1851, "confidence": "medium",
         "note": "district burned on 3-4 May 1851 (~18 blocks, ~2,000 buildings): outline closed round the "
                 "buildings of the Huntington 'Map of the Burnt District' and the 1852-chart buildings OHM tags "
                 "as built after the fire (OHM, CC0)",
         "source_url": GR_MAPS[1851]["url"], "geometry": aux["burnt_may"]},
        {"fire": "22 June 1851", "year": JUNE_1851, "confidence": "medium-low",
         "note": "bounded by Powell, Sansome, Clay and Broadway; 'ten blocks and portions of six others' "
                 "(the whole rectangle is drawn; part of six blocks survived)",
         "source_url": "https://guardiansofthecity.org/sffd/fires/great_fires/june_22_1851.html",
         "geometry": aux["june"]}], crs=UTM)
    _write_geojson(fires, OHM_OUT / "sf_fires_1851.geojson", "sf_fires_1851")
    return out


FIRST_DEV = ("predecessor", "predecessor_rows", "predecessor_industrial")  # a lot's first generated building


def apply_goldrush(pred, today, include_years=(1851, 1852, 1887)):
    """Integration for sf_predecessors.main (call it after apply_sanborn, with the sf_goldrush area left out
    of apply_sanborn: include=lambda a: not a.startswith(REGION_SANBORN) and not a.startswith("sf_goldrush")).

    pred:  the predecessors so far (generated, documented, other Sanborn areas), EPSG:32610
    today: sf_buildings (start_year, geometry), EPSG:32610
    The traced buildings carry their own evidence-based dates (start_year / end_year, windows and evidence
    in the files). Inside the coverage of each map:
      * 'before_map' (1851, 1852 maps): a lot's first generated building (year_reason predecessor /
        predecessor_rows / predecessor_industrial, standing before 1906) that overlaps a traced building
        (>= 20 % of the smaller) is its procedural stand-in and is dropped; any other generated building there
        that starts before the map date (the map shows the lot empty, or it is the next generation such as the
        1850s brick rebuild) starts after the map instead, 1852.3-1856.5 (the next extent snapshot);
      * 'after_1852' (1887 Sanborn blocks): generated buildings standing after 1852.3 are dropped (the 1852
        chart and the 1887 Sanborn describe these blocks to the 1906 fire);
      * documented buildings (early_sf.csv, notable_pre1906.csv) whose point falls on a traced footprint drawn
        while they stood take that outline (their researched dates win, as in apply_sanborn);
      * a traced building whose end is an upper bound (end_rule 'successor': the 1906 fire, today's building)
        ends when the first later building on its spot starts (a kept generated building, another area's
        traced building, a documented one) - so the procedural brick rebuilding of the 1850s and the later
        city follow the real 1851/52 town instead of overlapping it.
    Returns pred with the traced buildings added (source 'ohm_sf_goldrush')."""
    files = [SANBORN / f"{GR_AREA}_{y}.geojson" for y in include_years]
    tr = pd.concat([gpd.read_file(f) for f in files if f.exists()], ignore_index=True)
    tr = gpd.GeoDataFrame(tr, geometry="geometry", crs=4326).to_crs(UTM)
    tr = tr[(tr.end_rule != "represented") & ~tr.modern_same.fillna(False).astype(bool)]
    tr = tr[tr.geometry.notna() & tr.geometry.is_valid & (tr.geometry.area > 6)].reset_index(drop=True)
    covf = gpd.read_file(SANBORN / f"{GR_AREA}_coverage.geojson").to_crs(UTM)
    cov = {int(r.map_year): (r.geometry, r.generated_rule, float(r.map_date)) for r in covf.itertuples()}
    pred = pred.reset_index(drop=True)
    gen = pred.source.astype(str).str.endswith("_procedural").values
    reason = pred.year_reason.astype(str).values
    pc = pred.geometry.representative_point()
    tsidx = tr.sindex
    drop = np.zeros(len(pred), bool)
    start = pred.start_year.values.astype(float).copy()
    n_shift = 0
    for y, (poly, rule, mdate) in cov.items():
        inside = pc.within(poly).values & gen
        if rule == "after_1852":
            drop |= inside & (pred.end_year.values > GR_MAPS[1852]["date"])
            continue
        for k in np.nonzero(inside & (start < FIRE_1906))[0]:
            g = pred.geometry.values[k]
            hit = False
            for j in tsidx.query(g, predicate="intersects"):
                tg = tr.geometry.values[j]
                if g.intersection(tg).area >= 0.2 * min(g.area, tg.area):
                    hit = True
                    break
            first_dev = reason[k] in FIRST_DEV or pred.source.values[k] == "sf_redevelopment_procedural"
            if hit and first_dev:
                drop[k] = True  # the lot's first building: the traced one is the real thing
            elif start[k] < mdate:
                # the map shows the lot empty (or this is a later generation, e.g. the brick rebuild): after the map
                s_new = GR_MAPS[1852]["date"] + (1856.5 - GR_MAPS[1852]["date"]) * h01(str(pred.mapblklot.values[k]), "gr")
                if s_new >= pred.end_year.values[k] - 0.5:
                    drop[k] = True
                else:
                    start[k] = max(start[k], s_new)
                    n_shift += 1
    pred = pred.assign(start_year=start)
    # documented buildings on a traced footprint
    doc_rows = pred.source.isin(["early_sf", "notable_pre1906"]).values & ~drop
    t_start = tr.start_year.astype(float).values.copy()
    t_end = tr.end_year.astype(float).values.copy()
    t_reason = np.array([f"ohm_goldrush_{int(m)}" for m in tr.map_year.values], dtype=object)
    n_doc = 0
    if "doc_match" in tr:
        docs = pred[doc_rows]
        for j, did in enumerate(tr.doc_match.values):
            if not isinstance(did, str) or not did:
                continue
            if "doc_id" in docs:
                hit = docs[docs.doc_id.astype(str) == did]
            else:  # sf_predecessors.parquet as written (doc_id dropped): the documented row nearest the footprint
                hit = docs[docs.geometry.representative_point().distance(tr.geometry.values[j].centroid) < 15]
            my = float(tr.map_year.values[j])
            hit = hit[(hit.start_year <= my + 1) & (hit.end_year >= my - 1)]
            if len(hit) != 1:
                continue  # a group of structures (early_sf count > 1), not standing then, or nothing: leave both
            if len(hit):
                r = hit.iloc[0]
                t_start[j] = min(t_start[j], float(r.start_year)) if np.isfinite(t_start[j]) else float(r.start_year)
                if np.isfinite(r.end_year) and r.end_year < 9000:
                    t_end[j] = float(r.end_year)
                t_reason[j] = f"documented:{did}"
                drop[hit.index.values] = True
                n_doc += 1
    pred = pred[~drop].reset_index(drop=True)
    # successors
    psidx = pred.sindex
    ps = pred.start_year.values
    n_succ = 0
    for j in range(len(tr)):
        if tr.end_rule.values[j] != "successor":
            continue
        g = tr.geometry.values[j]
        cands = [ps[k] for k in psidx.query(g, predicate="intersects")
                 if ps[k] > t_start[j] + 0.5 and g.intersection(pred.geometry.values[k]).area >= 0.2 * min(g.area, pred.geometry.values[k].area)]
        for k in tsidx.query(g, predicate="intersects"):  # a later traced building on the spot (1887 map)
            if k != j and t_start[k] > t_start[j] + 0.5 and g.intersection(tr.geometry.values[k]).area >= 0.2 * min(g.area, tr.geometry.values[k].area):
                cands.append(t_start[k])
        if cands and (not np.isfinite(t_end[j]) or min(cands) - 0.05 < t_end[j]):
            t_end[j] = min(cands) - 0.05
            n_succ += 1
        if not np.isfinite(t_end[j]):
            t_end[j] = max(float(tr.map_year.values[j]) + 15, 1960.0)  # as apply_sanborn
    rows = []
    for j in range(len(tr)):
        if not (np.isfinite(t_start[j]) and t_end[j] > t_start[j] + 0.3):
            continue
        r = tr.iloc[j]
        use = str(r["use"] or "")
        stories = float(r.stories) if pd.notna(r.stories) and r.stories > 0 else 1.0
        height = stories * 3.6 + (1.2 if use in ("dwelling", "flats") else 0.6)
        if use == "storeship":
            height = 4.0  # a hulk beached in the cove, used as a warehouse
        mat = str(r.material or "")
        rows.append({"geometry": r.geometry, "start_year": float(t_start[j]), "end_year": float(t_end[j]),
                     "height": height, "stories": stories, "kind": "building", "source": "ohm_sf_goldrush",
                     "mapblklot": f"{GR_AREA}:{r.id}", "material": {"frame": "", "iron": "", "concrete": ""}.get(mat, mat),
                     "use_sanborn": use, "year_confidence": "estimated", "year_reason": t_reason[j]})
    new = gpd.GeoDataFrame(rows, crs=UTM)
    log(f"predecessors: OHM gold-rush maps: {len(new)} traced buildings; {int(drop.sum())} predecessors replaced "
        f"({n_doc} documented ones take a traced outline), {n_shift} generated moved after the 1852 chart, "
        f"{n_succ} traced buildings end at a later building on their spot")
    return gpd.GeoDataFrame(pd.concat([pred, new], ignore_index=True), geometry="geometry", crs=UTM)


# ================================================================== Stanford
STANFORD_SOURCES = ("Stanford Base Map", "2003 Campus Map", "Map of the lands of Leland Stanford", "1966 Law School",
                    "Law School site aerials", "Training and Organizational", "Research Administration")
PLACEHOLDER_DAYS = ("-02-29", "-02-28")


def stanford_campus():
    """Stanford's land (Overture land_use 'university' outlines named Stanford), UTM, buffered 60 m."""
    import pyarrow.parquet as pq
    lu = pq.read_table(RAW / "overture" / "2026-10-21.0" / "region5_land_use.parquet").to_pandas()
    lu = lu[lu["class"].isin(["university", "college"]) & lu.name.fillna("").str.contains("Stanford")]
    g = gpd.GeoDataFrame(lu, geometry=gpd.GeoSeries.from_wkb(lu.geometry), crs=4326).to_crs(UTM)
    return shapely.union_all(g.geometry.values).buffer(60)


# OHM's Stanford import (user import "LSJUbldgs", source map "Campus of Leland Stanford Junior University, 1962",
# purl.stanford.edu/qr683hn3144) dates most outlines with binned "-02-29" placeholders. What each bin means was
# checked against the researched Stanford rows of data/tables/known_building_dates_region.csv on the same
# footprint (python ohm_import.py stanford prints the table): 1888-02-29 = the original Quad (researched
# 1889-1903, 119 rows); 1920-02-29 = drawn on the old campus maps (33 rows, all <= 1954, 30 <= 1934);
# 1932-02-29 "shown on 1934 map" (1934 x5); 1940-02-29 "not on 1934 map" (1961 x5); 1964-02-29 (1970 x4),
# 2000-02-28 (2003-2020, 10 rows) and 2004-02-28 (2016 x5) = built after that year; 1976-02-29 (fixme
# start_date) = unknown (1876-2000 among 29 rows); the Escondido Village "1956" is one year for the whole site
# (it also sits on the 1875 Escondite Cottage) and the "approximate" Science & Engineering Quad dates are one
# year for buildings of 2005-2014. Only cited or day-exact dates become researched rows; the bins become bounds.
BIN_BOUNDS = {"1920-02-29": (np.nan, 1962.0, "drawn on the old campus maps (OHM bin 1920-02-29; researched rows: "
                             "all <= 1954, 30 of 33 <= 1934)"),
              "1932-02-29": (np.nan, 1934.0, "shown on the 1934 campus map"),
              "1964-02-29": (1964.0, np.nan, "OHM bin 1964-02-29 = built after 1964 (researched rows: 1970 x4)"),
              "2000-02-28": (2000.0, np.nan, "OHM bin 2000-02-28 = built after 2000 (researched rows: 2003-2020)"),
              "2004-02-28": (2004.0, np.nan, "OHM bin 2004-02-28 = built after 2004 (researched rows: 2016 x5)"),
              "2004-02-29": (2004.0, np.nan, "OHM bin 2004-02-29 = built after 2004")}


def stanford_evidence(t):
    """(kind, start, note, start_min, start_max) for an OHM Stanford building; kind is 'dated' (a cited or
    day-exact date), 'bound' (a map bin: start_min / start_max) or 'placeholder' (no evidence)."""
    sd = str(t.get("start_date") or "")
    src = str(t.get("start_date:source") or "")
    fix = str(t.get("fixme") or "")
    sl, fl = src.lower(), fix.lower()
    y = year_of(sd)
    nan = np.nan
    if not np.isfinite(y):
        return "placeholder", nan, "no start_date", nan, nan
    if "not on 1934" in sl or "not shown on 1934" in sl:
        return "bound", nan, f"not on the 1934 campus map (OHM start_date {sd}: '{src}')", 1934.0, nan
    if "student_housing" in sl and sd.endswith(PLACEHOLDER_DAYS):
        return "placeholder", nan, "OHM gives the whole Escondido Village site one year (1956-02-29)", nan, nan
    if sl.startswith("approximate"):
        return "placeholder", nan, f"OHM start_date {sd} is an approximate group date ({src[:90]})", nan, nan
    if "shown on 1934 map" in sl or sl in ("on 1934 map", "arbitrary, shown on 1934 map"):
        return "bound", nan, f"shown on the 1934 campus map (OHM start_date {sd}: '{src}')", nan, 1934.0
    if sl.startswith(("http", "wikipedia", "more_info", "matched to asrc")):
        url = t.get("more_info:1") if sl.startswith("more_info") else (src if src.startswith("http") else "")
        note = f"OHM start_date {sd}, cited to {src[:110]}" + (f" ({url})" if url and url != src else "")
        return "dated", y, note, nan, nan
    if sd[:10] in BIN_BOUNDS:
        lo, hi, why = BIN_BOUNDS[sd[:10]]
        return "bound", nan, why, lo, hi
    if sd.endswith(PLACEHOLDER_DAYS) or "start_date" in fl or "start date" in fl:
        return "placeholder", nan, f"OHM start_date {sd} is a placeholder", nan, nan
    note = f"OHM start_date {sd}" + (" (no source on the feature)" if len(sd) >= 10 else " (year only, no source on the feature)")
    if "construction begins" in fl:
        note += f"; OHM fixme: {fix}"
    return "dated", y, note, nan, nan


def stanford():
    import pyarrow.parquet as pq
    els = load_elements(glob.glob(str(OHM_RAW / "geom_*.json")))
    campus = stanford_campus()
    g = to_gdf(els, keep=lambda t: "building" in t)
    g = g[g.geom_type.isin(["Polygon", "MultiPolygon"])].to_crs(UTM)
    imp = g.tags.map(lambda t: t.get("import") == "LSJUbldgs").values
    other_src = g.tags.map(lambda t: any(k in " ".join(str(v) for v in t.values()) for k in STANFORD_SOURCES)).values
    unsourced = g.tags.map(lambda t: not any(k in t for k in ("source", "source:name", "import"))).values
    on_campus = g.geometry.representative_point().within(campus).values
    g = g[imp | (on_campus & (other_src | unsourced))].reset_index(drop=True)
    g["key"] = [f"{a[0]}{b}" for a, b in zip(g.osm_type, g.osm_id)]
    log(f"stanford: {len(g)} OHM buildings ({imp.sum()} LSJUbldgs import, {len(g) - imp.sum()} others on campus)")
    ev = g.tags.map(stanford_evidence)
    g["kind"] = [e[0] for e in ev]
    g["year"] = [e[1] for e in ev]
    g["note"] = [e[2] for e in ev]
    g["smin"] = [e[3] for e in ev]
    g["smax"] = [e[4] for e in ev]
    g["name"] = g.tags.map(lambda t: t.get("name") or t.get("building:number") or "")
    g["end"] = g.tags.map(lambda t: year_of(t.get("end_date")))
    g["end_src"] = g.tags.map(lambda t: t.get("end_date:source") or t.get("source:1:name") or "")
    g["levels"] = g.tags.map(lambda t: pd.to_numeric(t.get("building:levels"), errors="coerce"))
    g["height_m"] = g.tags.map(lambda t: pd.to_numeric(t.get("height"), errors="coerce"))
    # today's footprints (Overture, five counties) around the campus
    b = g.to_crs(4326).total_bounds
    from common import read_region_overture
    t = read_region_overture("building", columns=["id", "px", "py", "name", "county", "geometry"],
                             filters=[("px", ">", b[0] - 0.01), ("px", "<", b[2] + 0.01), ("py", ">", b[1] - 0.01),
                                      ("py", "<", b[3] + 0.01)]).to_pandas()
    ov = gpd.GeoDataFrame(t, geometry=gpd.GeoSeries.from_wkb(t.geometry), crs=4326).to_crs(UTM)
    osidx = ov.sindex
    m_id, m_iou, m_cover = [], [], []
    for gm in g.geometry.values:
        best, bi, bc = None, 0.0, 0.0
        c = gm.representative_point()
        for j in osidx.query(gm, predicate="intersects"):
            og = ov.geometry.values[j]
            inter = gm.intersection(og).area
            iou = inter / max(gm.union(og).area, 1e-6)
            cover = inter / max(min(gm.area, og.area), 1e-6)
            score = iou + (0.3 if og.contains(c) else 0.0)
            if score > bi + (0.3 if best is not None and ov.geometry.values[best].contains(c) else 0.0):
                best, bi, bc = j, iou, cover
        ok = best is not None and (bi >= 0.5 or (bc >= 0.6 and ov.geometry.values[best].contains(gm.representative_point())))
        m_id.append(best if ok else None)
        m_iou.append(round(bi, 2))
        m_cover.append(round(bc, 2))
    g["ov"] = m_id
    g["iou"] = m_iou
    g["cover"] = m_cover
    log(f"stanford: {g.ov.notna().sum()} matched to today's footprints, {g.ov.isna().sum()} without one")
    # the pipeline's current year per footprint (region_building_points: one point per built footprint)
    rbp = pd.read_parquet(INTERIM / "region_building_points.parquet")
    rbp = rbp[(rbp.lon > b[0] - 0.01) & (rbp.lon < b[2] + 0.01) & (rbp.lat > b[1] - 0.01) & (rbp.lat < b[3] + 0.01)]
    rp_ = gpd.GeoDataFrame(rbp, geometry=gpd.points_from_xy(rbp.lon, rbp.lat), crs=4326).to_crs(UTM)
    jj = gpd.sjoin(rp_, ov[["geometry"]], predicate="within")
    cur = jj.groupby("index_right").start_year.min()
    # researched rows already in data/tables/known_building_dates_region.csv
    kr = pd.read_csv(TABLES / "known_building_dates_region.csv")
    kr = kr[(kr.lat.between(b[1] - 0.01, b[3] + 0.01)) & (kr.lon.between(b[0] - 0.01, b[2] + 0.01))]
    kp = gpd.GeoDataFrame(kr, geometry=gpd.points_from_xy(kr.lon, kr.lat), crs=4326).to_crs(UTM)
    kj = gpd.sjoin(kp, ov[["geometry"]], predicate="within")
    known_by_fp = {int(r.index_right): r for r in kj.itertuples()}
    return g, ov, cur, known_by_fp, kp


def write_stanford():
    g, ov, cur, known_by_fp, kp = stanford()
    OHM_OUT.mkdir(parents=True, exist_ok=True)
    rows, bounds, conflicts, agree = [], [], [], []
    ovll = ov.to_crs(4326)
    for r in g.itertuples():
        if pd.isna(r.ov) or (np.isfinite(r.end) and r.end < 2026):
            continue
        j = int(r.ov)
        fp = ov.geometry.values[j]
        pt = r.geometry.representative_point()
        if not fp.contains(pt):
            pt = fp.representative_point()
        ll = gpd.GeoSeries([pt], crs=UTM).to_crs(4326).iloc[0]
        cy = cur.get(j, np.nan)
        county = ov.county.values[j] or "Santa Clara"
        url = ohm_url(r.osm_type, r.osm_id)
        if r.kind == "dated":
            yr = int(np.floor(r.year))
            k = known_by_fp.get(j)
            if k is not None:
                d = abs(float(k.start_year) - yr)
                (agree if d <= 2 else conflicts).append({
                    "footprint": ov.id.values[j], "known_id": k.id, "known_name": k.name, "known_start": k.start_year,
                    "ohm_id": url, "ohm_name": r.name, "ohm_start": yr, "ohm_note": r.note, "diff": d,
                    "current_pipeline_year": cy, "known_source": k.source_url})
                continue
            rows.append({"id": f"ohm_stanford_{r.key}", "name": r.name or f"Stanford building (OHM {r.key})",
                         "lat": round(ll.y, 6), "lon": round(ll.x, 6), "start_year": yr, "end_year": 9999,
                         "source_url": url, "note": r.note + f". Matched to Overture {ov.id.values[j][:8]} "
                         f"(IoU {r.iou}); pipeline year now {cy:.0f}." if np.isfinite(cy) else
                         r.note + f". Matched to Overture {ov.id.values[j][:8]} (IoU {r.iou}).",
                         "county": county})
        elif r.kind == "bound":
            k = known_by_fp.get(j)
            lo, hi = r.smin, r.smax
            viol = np.isfinite(cy) and ((np.isfinite(hi) and cy > hi + 0.5) or (np.isfinite(lo) and cy < lo))
            if k is not None:
                ks = float(k.start_year)
                if (np.isfinite(hi) and ks > hi + 0.5) or (np.isfinite(lo) and ks < lo):
                    conflicts.append({"footprint": ov.id.values[j], "known_id": k.id, "known_name": k.name,
                                      "known_start": ks, "ohm_id": url, "ohm_name": r.name,
                                      "ohm_start": f"<= {hi:g}" if np.isfinite(hi) else f">= {lo:g}", "ohm_note": r.note,
                                      "diff": np.nan, "current_pipeline_year": cy, "known_source": k.source_url})
            bounds.append({"id": f"ohm_stanford_{r.key}", "name": r.name, "lat": round(ll.y, 6), "lon": round(ll.x, 6),
                           "start_min": lo, "start_max": hi, "evidence": r.note,
                           "current_pipeline_year": round(cy, 1) if np.isfinite(cy) else np.nan,
                           "violates": bool(viol), "known_row": k.id if k is not None else "",
                           "source_url": url, "county": county, "overture_id": ov.id.values[j]})
    kd = pd.DataFrame(rows)
    kd = kd.drop_duplicates("lat").sort_values("id")
    kd.to_csv(OHM_OUT / "known_dates_ohm.csv", index=False)
    pd.DataFrame(bounds).sort_values("id").to_csv(OHM_OUT / "stanford_bounds_ohm.csv", index=False)
    pd.DataFrame(conflicts + [dict(a, diff=a["diff"]) for a in []]).to_csv(OHM_OUT / "stanford_conflicts.csv", index=False)
    log(f"stanford: {len(kd)} known-date rows, {len(bounds)} map-bin bounds "
        f"({sum(x['violates'] for x in bounds)} violated by today's pipeline year), {len(conflicts)} conflicts and "
        f"{len(agree)} agreements with known_building_dates_region.csv")
    # demolished: gone from today's footprints, with an OHM end date
    dem = g[g.end.notna() & (g.end < 2026)].copy()
    out = []
    for r in dem.itertuples():
        kind, y, note = r.kind, r.year, r.note
        esrc = str(r.tags.get("end_date:source") or "")
        ssrc = str(r.tags.get("start_date:source") or "")
        arbitrary = "arbitrary" in esrc.lower()
        jov = None if pd.isna(r.ov) else int(r.ov)
        out.append({"id": f"ohm_stanford_{r.key}", "name": r.name or None,
                    "start_year": float(np.floor(y)) if kind == "dated" else None,
                    "start_evidence": note + (" [OHM: arbitrary]" if "arbitrary" in ssrc.lower() else ""),
                    "end_year": float(r.end),
                    "end_evidence": f"OHM end_date {r.tags.get('end_date')}" + (f" ({r.end_src})" if r.end_src else ""),
                    "end_confidence": "arbitrary (OHM)" if arbitrary else ("cited" if esrc.startswith("http") else "OHM date"),
                    "storeys": r.levels if np.isfinite(r.levels) else None,
                    "height_m": r.height_m if np.isfinite(r.height_m) else None,
                    "confidence": "estimated", "source_url": ohm_url(r.osm_type, r.osm_id),
                    "best_overture_iou": r.iou,
                    "today_footprint": ov.id.values[jov] if jov is not None else None,
                    "today_footprint_year": round(float(cur.get(jov, np.nan)), 1) if jov is not None else None,
                    "geometry": r.geometry})
    dg = gpd.GeoDataFrame(out, crs=UTM)
    # gone, but today's footprint data (Overture 2026-10) still has the same building: a researched row that ends it
    stale = dg[dg.today_footprint.notna() & (dg.best_overture_iou >= 0.8) & dg.start_year.notna() &
               ((dg.today_footprint_year - dg.start_year).abs() <= 3) & (dg.end_confidence != "arbitrary (OHM)")]
    if len(stale):
        add = []
        for r in stale.itertuples():
            pt = gpd.GeoSeries([r.geometry.representative_point()], crs=UTM).to_crs(4326).iloc[0]
            add.append({"id": r.id, "name": r.name, "lat": round(pt.y, 6), "lon": round(pt.x, 6),
                        "start_year": int(r.start_year), "end_year": int(np.floor(r.end_year)),
                        "source_url": r.source_url, "note": f"{r.start_evidence}; {r.end_evidence}. Demolished, but "
                        f"the Overture 2026-10 footprint {r.today_footprint[:8]} is still this building.",
                        "county": "Santa Clara"})
        kd = pd.concat([kd, pd.DataFrame(add)], ignore_index=True).sort_values("id")
        kd.to_csv(OHM_OUT / "known_dates_ohm.csv", index=False)
        log(f"stanford: + {len(add)} rows ending a demolished building that today's footprints still show")
    _write_geojson(dg, OHM_OUT / "demolished_ohm.geojson", "demolished_ohm")
    # LSJU outlines with no footprint today and no end date: for review (demolished after the import?)
    un = g[g.ov.isna() & g.end.isna() & (g.geometry.area >= 60)]
    pd.DataFrame({"ohm": [ohm_url(a, b_) for a, b_ in zip(un.osm_type, un.osm_id)], "name": un.name.values,
                  "kind": un.kind.values, "note": un.note.values, "best_iou": un.iou.values,
                  "area_m2": un.geometry.area.round(0).values,
                  "lat": un.to_crs(4326).geometry.representative_point().y.round(6).values,
                  "lon": un.to_crs(4326).geometry.representative_point().x.round(6).values}
                 ).to_csv(OHM_OUT / "stanford_unmatched_ohm.csv", index=False)
    log(f"stanford: {len(dg)} demolished buildings with OHM end dates ({dg.today_footprint.notna().sum()} on a spot "
        f"rebuilt since); {len(un)} outlines >= 60 m2 without a footprint today or an end date (stanford_unmatched_ohm.csv)")
    print(g.kind.value_counts())


# ================================================================== extras: railways, ferries
def existing_routes():
    """Our historic railways and routes (historic_rail.geojson + routes.csv) as one UTM geometry."""
    from fire_1906 import intersection
    from geocode import streets
    geoms = list(gpd.read_file(MANUAL / "historic_rail.geojson").to_crs(UTM).geometry.values)
    rt = pd.read_csv(MANUAL / "routes.csv")
    st = None
    for r in rt.itertuples():
        try:
            if str(r.geom_type).strip() == "lonlat":
                pts = [tuple(map(float, q.split()[:2])) for q in str(r.geom).split(";") if q.strip()]
                if len(pts) >= 2:
                    geoms.append(gpd.GeoSeries([LineString(pts)], crs=4326).to_crs(UTM).iloc[0])
            elif str(r.geom_type).strip() == "streets":
                st = st if st is not None else streets()
                nodes = []
                for e in str(r.geom).split(";"):
                    if "&" in e:
                        a, b = (x.strip() for x in e.split("&", 1))
                        q, _ = intersection(st, a, b)
                        if q is not None:
                            nodes.append((q.x, q.y))
                if len(nodes) >= 2:
                    geoms.append(LineString(nodes))
        except Exception:  # noqa: BLE001
            continue
    return shapely.union_all(geoms)


def rail_candidates():
    from extent import POLY
    els = load_elements(glob.glob(str(OHM_RAW / "geom_*.json")))
    keep = lambda t: (t.get("railway") in ("rail", "light_rail", "tram", "narrow_gauge", "disused", "abandoned")  # noqa: E731
                      or t.get("route") == "ferry")
    g = to_gdf({k: e for k, e in els.items() if k[0] == "way"}, keep=keep)
    g = g[g.geom_type.isin(["LineString", "MultiLineString"])]
    g = g[g.geometry.representative_point().within(POLY.buffer(0.02))].to_crs(UTM).reset_index(drop=True)
    # route relations the ways belong to (names, operators, mode periods)
    rel = {}
    for (typ, i), e in els.items():
        if typ != "relation":
            continue
        t = e.get("tags", {})
        if t.get("type") != "route" and t.get("route") is None:
            continue
        for m in e.get("members", []):
            if m.get("type") == "way":
                rel.setdefault(m["ref"], []).append(t)
    g["rels"] = [rel.get(i, []) for i in g.osm_id]
    return g


def write_rail():
    g = rail_candidates()
    ours = existing_routes().buffer(60)
    g["overlap"] = [round(gm.intersection(ours).length / max(gm.length, 1), 2) for gm in g.geometry.values]
    g["km"] = (g.length / 1000).round(2)
    t = g.tags
    g["name"] = [d.get("name") or next((r.get("name") for r in rr if r.get("name")), "") for d, rr in zip(t, g.rels)]
    g["src"] = t.map(lambda d: d.get("source") or d.get("start_date:source") or d.get("source:name") or "")
    g["sd"] = t.map(lambda d: d.get("start_date"))
    g["ed"] = t.map(lambda d: d.get("end_date"))
    review = g[(g.overlap < 0.3) & g.sd.notna()].copy()
    review["ohm"] = [ohm_url("way", i) for i in review.osm_id]
    review["kind"] = t[review.index].map(lambda d: d.get("railway") or d.get("route"))
    review["operator"] = t[review.index].map(lambda d: d.get("operator", ""))
    OHM_OUT.mkdir(parents=True, exist_ok=True)
    review[["ohm", "kind", "name", "operator", "sd", "ed", "km", "overlap", "src"]].sort_values(["name", "sd"]).to_csv(
        OHM_OUT / "rail_review_ohm.csv", index=False)
    log(f"rail: {len(g)} OHM railway / tram / ferry ways in the extent, {len(review)} dated ones not in our data "
        "(< 30 % within 60 m of historic_rail / routes) -> rail_review_ohm.csv")
    return g


# curated: OHM railways we lack, checked one by one (rail_review_ohm.csv lists every candidate)
RAIL_PICK = [
    # (way ids, route_id, name, mode, start, end, confidence, note)
    ([200221495], "mt_tamalpais_muir_woods", "Mount Tamalpais and Muir Woods Railway (Mill Valley - summit)", "rail",
     1896.6, 1930.5, "exact",
     "'Crookedest railroad in the world': Mill Valley to the summit opened Aug 1896, Muir Woods branch 1907, "
     "abandoned 1930 after the 1929 fire (NPS, 'The Crookedest Railroad - Early Travel to Muir Woods'). Geometry: "
     "OHM, traced from the USGS Tamalpais 1897 sheet. Month of opening / closure ESTIMATED from the years."),
    ([200655254], "sp_sj_4th_street", "SP 4th Street line through downtown San Jose", "rail", 1869.2, 1936.0, "exact",
     "Southern Pacific (San Jose & Gilroy line, opened 13 Mar 1869) along 4th St; trains moved to the new Cahill "
     "St (Diridon) line at the end of 1935 (San Jose Mercury Herald, 29 Dec 1935). Geometry: OHM."),
    ([201228649], "sp_sj_4th_street", "SP 4th Street line, north part (industrial lead after 1935)", "rail", 1869.2,
     1977.5, "estimated", "Same line; this part stayed as an industrial track, gone on the 1980 USGS San Jose West "
     "quad (OHM: removed 1975-1980). Geometry: OHM."),
    ([201228655], "sp_sj_4th_street", "SP 4th Street line, south part (industrial lead after 1935)", "rail", 1869.2,
     1995.0, "estimated", "Same line; removed between 1980 and 2010 (OHM, Esri World Imagery Wayback). End year "
     "ESTIMATED inside that window."),
    ([201228651], "sp_sj_gilroy", "SP San Jose - Gilroy line, section south of downtown (removed)", "rail", 1869.2, 1995.0,
     "estimated", "1869 track south of downtown San Jose, removed 1980-2010 (OHM, Esri Wayback); end ESTIMATED."),
    ([201228652], "sp_sj_gilroy", "SP San Jose - Gilroy line, short section (removed)", "rail", 1869.2, 2013.0,
     "estimated", "Removed 2010-2016 (OHM, Esri Wayback); end ESTIMATED."),
    ([201228654], "sp_sj_gilroy", "SP San Jose - Gilroy line, short section (removed)", "rail", 1869.2, 2018.0,
     "estimated", "Removed 2017-2019 (OHM, Esri Wayback); end ESTIMATED."),
    ([199612534, 199612536, 199612537], "camp_fremont_spur", "Camp Fremont spur (US Army camp, Menlo Park)", "rail",
     1917.5, 1920.0, "exact", "Spur from the SP main line into Camp Fremont, the WWI training camp (opened July 1917, "
     "closed 1919-20); drawn on the 1917 Camp Fremont map (Stanford archive) traced in OHM."),
    ([199600583, 199600584, 199867367, 199890065], "stanford_spur_1890s", "Spur from the SP main line at Palo Alto "
     "toward the Stanford campus", "rail", 1891.0, 1897.5, "estimated",
     "Drawn on the 1897 USGS Palo Alto sheet only (OHM: by 1894 - 1897; 'probably used' for campus construction). "
     "Start ESTIMATED (campus opened 1891), end = the sheet year."),
    ([200250635, 200250636], "california_nevada_rr", "California and Nevada Railroad (Emeryville - Berkeley - "
     "Orinda), north of Blake St", "narrow_gauge", 1885.0, 1902.0, "estimated",
     "3 ft gauge line (1884-1900s); track north of Blake St abandoned about 1902 (Pacific Narrow Gauge, "
     "https://www.pacificng.com/template.php?page=roads/ca/cnr/index.htm). Geometry: OHM from the USGS San Francisco "
     "1895 and Concord 1897 sheets. Start ESTIMATED (line built 1884-91)."),
]
ROUTE_PICK = [
    ([199825842, 199825847, 199825848], "sj_santa_clara_horse", "San Jose & Santa Clara Horse Railroad (The Alameda)",
     "horsecar", 1868.0, 1901.0,
     "Horse railroad along The Alameda between San Jose and Santa Clara, 1868-1901 (History San Jose; "
     "chicagorailfan.com San Jose streetcar dates); electrified 1901. Geometry: OHM.",
     "https://web.archive.org/web/20160204195910/http://www.chicagorailfan.com/sjcdate.html"),
    ([199825842, 199825847, 199825848], "sj_santa_clara_horse", "Santa Clara streetcar line (The Alameda)",
     "streetcar", 1901.0, 1938.27, "Electric from 1901 (San Jose & Santa Clara County RR, San Jose Railroads from "
     "1912); last car 10 Apr 1938. Geometry: OHM.",
     "https://web.archive.org/web/20160204195910/http://www.chicagorailfan.com/sjcdate.html"),
    ([199812812], "sj_north_side_horse", "North Side Horse Railroad (San Jose)", "horsecar", 1875.0, 1901.0,
     "Horse railroad 1875-1901 (OHM; start cited to the NRHP nomination on NPGallery). Geometry: OHM.",
     "https://npgallery.nps.gov/GetAsset/f0a732a6-9b37-4887-98b7-a355da88df8"),
    # Santa Rosa (new counties, 2026-11): OHM's dates on these ways are placeholders ("1854"), ours are below
    ([198305780, 198305783], "sr_street_railway", "Santa Rosa Street Railway (horse cars): Fourth Street and McDonald "
     "Avenue", "horsecar", 1877.0, 1905.17,
     "Horse-car line along Fourth Street from the railroad depot and out McDonald Avenue, drawn on Thos. H. "
     "Thompson's Map of the City of Santa Rosa of 1876 (Historical Atlas of Sonoma County, 1877): in service by "
     "1877 (start ESTIMATED from the map). The Santa Rosa horse lines were consolidated into the Petaluma & Santa "
     "Rosa Railway on 20 June 1903 and replaced by its electric cars, downtown from 1 March 1905 (Wikipedia, "
     "Petaluma and Santa Rosa Railroad). Geometry: OHM, from the 1876 map.",
     "https://www.davidrumsey.com/maps2368.html"),
    ([198305780], "sr_psr_fourth_st", "Petaluma & Santa Rosa electric cars on Fourth Street (Santa Rosa)", "streetcar",
     1905.17, 1931.5,
     "The interurban reached downtown Santa Rosa when its crossing of the steam railroad was installed on 1 March "
     "1905; 'the Santa Rosa line was dismantled from McDonald Avenue to Olive Street in 1931' (Wikipedia; month "
     "ESTIMATED). Fourth Street between the depot and McDonald Avenue is drawn; the approach from Sebastopol Avenue "
     "is not. Geometry: OHM (the horse-car line of the 1876 map).",
     "https://en.wikipedia.org/wiki/Petaluma_and_Santa_Rosa_Railroad"),
]


def _line_of(ways, g):
    parts = [g.geometry.values[k] for k in np.nonzero(g.osm_id.isin(ways).values)[0]]
    if not parts:
        return None
    u_ = unary_union(parts)
    return linemerge(u_) if u_.geom_type == "MultiLineString" else u_


def write_rail_picks(g):
    rows = []
    for ways, rid, name, mode, y0, y1, conf, note in RAIL_PICK:
        geom = _line_of(ways, g)
        if geom is None:
            continue
        rows.append({"route_id": rid, "name": name, "mode": mode, "year_start": y0, "year_end": y1,
                     "elevated": "ground", "confidence": conf,
                     "source_url": " ".join(ohm_url("way", w) for w in ways), "note": note,
                     "geometry_confidence": "medium", "geometry_source": "OpenHistoricalMap (CC0)", "geometry": geom})
    rg = gpd.GeoDataFrame(rows, crs=UTM)
    _write_geojson(rg, OHM_OUT / "historic_rail_ohm.geojson", "historic_rail_ohm")
    out = []
    seq = {}     # (route_id, segment_seq) stays unique when one route has several periods
    for ways, rid, name, mode, y0, y1, note, url in ROUTE_PICK:
        geom = _line_of(ways, g)
        if geom is None:
            continue
        geom = gpd.GeoSeries([geom], crs=UTM).to_crs(4326).iloc[0].simplify(0.00002)
        lines = list(geom.geoms) if geom.geom_type == "MultiLineString" else [geom]
        for ln in lines:
            k = seq[rid] = seq.get(rid, 0) + 1
            out.append({"route_id": rid, "name": name, "mode": mode, "year_start": y0, "year_end": y1,
                        "elevated": "ground", "segment_seq": k, "geom_type": "lonlat",
                        "geom": "; ".join(f"{x:.6f} {y:.6f}" for x, y in ln.coords),
                        "note": note + " " + " ".join(ohm_url("way", w) for w in ways), "source_url": url})
    # Port Costa - Benicia train ferry (Central Pacific's Solano / Contra Costa), until the 1930 bridge
    fe = g[g.tags.map(lambda t: t.get("route") == "ferry" and t.get("start_date") == "1879")]
    for r in fe.itertuples():
        ln = gpd.GeoSeries([r.geometry], crs=UTM).to_crs(4326).iloc[0]
        out.append({"route_id": "fy_port_costa_benicia", "name": "Train ferry: Port Costa - Benicia (Solano, Contra Costa)",
                    "mode": "ferry", "year_start": 1879.95, "year_end": 1930.79, "elevated": "ground", "segment_seq": 1,
                    "geom_type": "lonlat", "geom": "; ".join(f"{x:.6f} {y:.6f}" for x, y in ln.coords),
                    "note": "Central Pacific train ferry Solano (from Dec 1879; Contra Costa from 1914) across the "
                            "Carquinez Strait until the Martinez-Benicia rail bridge opened 15 Oct 1930. Geometry: OHM "
                            f"(USGS Karquines 1898 sheet) {ohm_url('way', r.osm_id)}",
                    "source_url": "https://en.wikipedia.org/wiki/Solano_(ferry)"})
    rt = pd.DataFrame(out, columns=["route_id", "name", "mode", "year_start", "year_end", "elevated", "segment_seq",
                                    "geom_type", "geom", "note", "source_url"])
    rt.to_csv(OHM_OUT / "routes_ohm.csv", index=False)
    log(f"rail: {len(rg)} railway segments -> historic_rail_ohm.geojson, {len(rt)} route rows -> routes_ohm.csv")


# ================================================================== extras: lost railways of the new counties
# OHM ways of railways whose track is gone (Sonoma, Santa Cruz, Solano), handed to historic_rail_trace.py: its
# `rail` method routes on data/raw/historic_rail/h2_*.json next to the Overture / OSM grades, so the routes of
# data/manual/historic_rail_spec.py (dates, sources and sections live there - never OHM's dates) can follow them.
# (name, (w, s, e, n) box the ways are clipped to, keep(tags) or None)
NEW_AREA_RAIL_BOXES = [
    # NPC narrow gauge Valley Ford - Occidental - Monte Rio - Duncans Mills (ways 202387713 / 202387715, from USGS
    # topo sheets and 3DEP lidar), the Guerneville branch (202387871, 3DEP) and its 1909 extension, the SF&NP
    # Sebastopol branch (202387872) and SP's Santa Rosa branch through the Valley of the Moon (200461230)
    # (not the Santa Rosa street railway ways, nor the St. Helena - Calistoga line: OSM has that grade)
    ("sonoma", (-123.20, 38.315, -122.45, 38.56),
     lambda t: t.get("name") not in ("Fourth Street", "McDonald Avenue")
     and "1945 topographic" not in str(t.get("source", ""))),
    # Boulder Creek branch (Felton - Boulder Creek; santacruztrains.com), not the SPC main line beside it
    ("boulder_creek", (-122.14, 37.045, -122.065, 37.155),
     lambda t: str(t.get("end_date", "")).startswith("1934")),
    # Sacramento Northern: Creed - Vacaville Junction link of 1930 (cut by the air base)
    ("sn_vacaville", (-121.97, 38.24, -121.85, 38.30), lambda t: str(t.get("end_date", "")) in ("1950", "1960")),
]


def write_rail_extract():
    """data/raw/historic_rail/h2_ohm_newarea.json: Overpass-style JSON of the OHM railway ways above that are not
    today's track (end-dated, or < 50 % within 40 m of an Overture track in use), clipped to their box. Way ids
    are written negative (OHM ids, not OSM ids)."""
    import pyarrow.parquet as pq  # noqa: F401
    els = load_elements(glob.glob(str(OHM_RAW / "geom_*.json")))
    g = to_gdf({k: e for k, e in els.items() if k[0] == "way"}, keep=lambda t: "railway" in t)
    g = g[g.geom_type.isin(["LineString", "MultiLineString"])].reset_index(drop=True)
    ov = gpd.read_parquet(RAW / "overture" / "2026-10-21.0" / "rail.parquet").set_crs(4326, allow_override=True)
    gone = np.array([any(v in ("is_abandoned", "is_disused") for x in (f if f is not None else []) for v in x["values"])
                     for f in ov.rail_flags])
    out = []
    for name, (w, s_, e, n), keep in NEW_AREA_RAIL_BOXES:
        box = shapely.geometry.box(w, s_, e, n)
        sub = g[g.intersects(box)]
        act = shapely.union_all(ov[~gone].cx[w - 0.01:e + 0.01, s_ - 0.01:n + 0.01].to_crs(UTM).geometry.values).buffer(40)
        su = sub.to_crs(UTM)
        for r, gu in zip(sub.itertuples(), su.geometry.values):
            t = r.tags
            if keep is not None and not keep(t):
                continue
            on = gu.intersection(act).length / max(gu.length, 1.0)
            if not t.get("end_date") and on >= 0.5:
                continue
            part = r.geometry.intersection(box)
            for k, ln in enumerate(getattr(part, "geoms", [part])):
                if ln.geom_type != "LineString" or len(ln.coords) < 2:
                    continue
                out.append({"type": "way", "id": -int(r.osm_id) * 10 - k,
                            "tags": {"railway": "abandoned", "name": f"OHM way {r.osm_id} {t.get('name', '')}".strip(),
                                     "source": ohm_url("way", r.osm_id)},
                            "geometry": [{"lon": round(x, 7), "lat": round(y, 7)} for x, y in ln.coords]})
    p = RAW / "historic_rail" / "h2_ohm_newarea.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"generator": "pipeline/ohm_import.py write_rail_extract (OpenHistoricalMap, CC0)",
                             "elements": out}))
    log(f"rail extract: {len(out)} OHM way pieces -> {p}")


def write_new_area_review():
    """data/manual/ohm/new_area_review_ohm.csv: every dated OHM feature that is not a railway or a road in the
    counties added in 2026-11 (inside EXTENT, outside EXTENT_CORE) - buildings, bridges, sites, town outlines -
    for review. Nothing is imported from it: OHM's dates there are mostly map years (the 1876 Thompson map of
    Santa Rosa) or unsourced, and are evidence to check, not dates to copy (decision 39)."""
    from extent import EXTENT_CORE, POLY
    core = Polygon(EXTENT_CORE)
    els = load_elements(glob.glob(str(OHM_RAW / "geom_*.json")))
    g = to_gdf(els, keep=lambda t: "railway" not in t and t.get("route") != "ferry" and "highway" not in t)
    rp = g.geometry.representative_point()
    g = g[rp.within(POLY) & ~rp.within(core)].reset_index(drop=True)

    def kind(t):
        for k in ("building", "man_made", "amenity", "landuse", "leisure", "boundary", "historic", "military",
                  "aeroway", "place", "route", "natural", "waterway", "tourism"):
            if k in t:
                return f"{k}={t[k]}"
        return "other"
    t = g.tags
    c = g.geometry.representative_point()
    out = pd.DataFrame({
        "ohm": [ohm_url(a, b) for a, b in zip(g.osm_type, g.osm_id)], "kind": t.map(kind),
        "name": t.map(lambda d: d.get("name", "")), "start_date": t.map(lambda d: d.get("start_date", "")),
        "end_date": t.map(lambda d: d.get("end_date", "")),
        "source": t.map(lambda d: d.get("source") or d.get("start_date:source") or d.get("source:name") or ""),
        "lon": c.x.round(5), "lat": c.y.round(5)})
    out = out.sort_values(["kind", "lat", "lon"])
    OHM_OUT.mkdir(parents=True, exist_ok=True)
    out.to_csv(OHM_OUT / "new_area_review_ohm.csv", index=False)
    log(f"new area: {len(out)} dated OHM features that are not railways or roads -> new_area_review_ohm.csv")


# ================================================================== extras: demolished buildings in the region
# cities whose Sanborn maps other agents are tracing now (they may reuse OHM there): flagged, not dropped
OTHER_AGENT_AREAS = {"palo_alto_menlo_park": (-122.22, 37.40, -122.10, 37.48), "san_mateo": (-122.36, 37.54, -122.28, 37.60),
                     "berkeley": (-122.32, 37.845, -122.23, 37.90), "alameda": (-122.33, 37.75, -122.22, 37.79),
                     "richmond": (-122.40, 37.90, -122.31, 37.96)}
CAMP_FREMONT_BOX = gpd.GeoSeries([shapely.geometry.box(-122.205, 37.425, -122.170, 37.460)], crs=4326).to_crs(UTM).iloc[0]
SKIP_BUILDING_SRC = ("Sanborn", "LSJUbldgs", "Campus of Leland Stanford", "Stanford Base Map", "SFO Museum")


def _src_text(t):
    return " ".join(str(v) for k, v in t.items() if k.startswith(("source", "import", "start_date:source",
                                                                     "end_date:source", "note")))


def write_region_demolished():
    """OHM buildings with an end date (demolished, burned or moved) outside San Francisco and Stanford, and not
    from a Sanborn tracing (Palo Alto, San Mateo, Berkeley are being traced by other agents)."""
    import pyarrow.parquet as pq
    from extent import EXTENT_CORE
    # the core Bay Area only (today's footprints are checked against the five-county file); OHM's few dated
    # buildings in the counties added in 2026-11 are listed by write_new_area_review()
    POLY = Polygon(EXTENT_CORE)
    els = load_elements(glob.glob(str(OHM_RAW / "geom_*.json")))
    g = to_gdf(els, keep=lambda t: "building" in t)
    g = g[g.geom_type.isin(["Polygon", "MultiPolygon"])]
    rp = g.geometry.representative_point()
    s_, w_, n_, e_ = SF_BBOX
    in_sf = (rp.y > s_) & (rp.y < n_) & (rp.x > w_) & (rp.x < e_)
    g = g[rp.within(POLY.buffer(0.02)) & ~in_sf]
    src = g.tags.map(_src_text)
    g = g[~src.map(lambda x: any(k in x for k in SKIP_BUILDING_SRC))]
    st = stanford_campus()
    gu = g.to_crs(UTM)
    gu = gu[~gu.geometry.representative_point().within(st)].reset_index(drop=True)
    gu["sd"] = gu.tags.map(lambda t: year_of(t.get("start_date")))
    gu["ed"] = gu.tags.map(lambda t: year_of(t.get("end_date")))
    gu["name"] = gu.tags.map(lambda t: t.get("name") or "")
    gu["key"] = [f"{a[0]}{b}" for a, b in zip(gu.osm_type, gu.osm_id)]
    # versions of one structure (renamed, re-dated): same outline, one starting when the other ends
    sidx = gu.sindex
    nxt = {}
    for i_, gm in enumerate(gu.geometry.values):
        if not np.isfinite(gu.ed.values[i_]):
            continue
        for j in sidx.query(gm, predicate="intersects"):
            if j == i_:
                continue
            g2 = gu.geometry.values[j]
            iou = gm.intersection(g2).area / max(gm.union(g2).area, 1e-6)
            if iou >= 0.8 and abs(gu.sd.values[j] - gu.ed.values[i_]) <= 1.0:
                nxt[i_] = j
    has_prev = set(nxt.values())
    rows = []
    for i_ in range(len(gu)):
        if i_ in has_prev:
            continue  # reported with the first version
        chain = [i_]
        while chain[-1] in nxt and nxt[chain[-1]] not in chain:
            chain.append(nxt[chain[-1]])
        last = chain[-1]
        end = gu.ed.values[last]
        if not (np.isfinite(end) and end < 2026):
            continue
        t0, tl = gu.tags.values[i_], gu.tags.values[last]
        names = [gu.name.values[k] for k in chain if gu.name.values[k]]
        srcs = []
        for k in chain:
            tk = gu.tags.values[k]
            for kk in ("source", "start_date:source", "end_date:source", "source:start_date", "source:end_date",
                       "end_date:source:url", "start_date:source:url"):
                if tk.get(kk) and tk[kk] not in srcs:
                    srcs.append(tk[kk])
        lv = pd.to_numeric(tl.get("building:levels"), errors="coerce")
        rows.append({"id": f"ohm_{gu.key.values[i_]}", "name": " / ".join(dict.fromkeys(names)) or None,
                     "start_year": gu.sd.values[i_], "end_year": end,
                     "versions": len(chain), "storeys": float(lv) if np.isfinite(lv) else None,
                     "height_m": pd.to_numeric(tl.get("height"), errors="coerce"),
                     "material": tl.get("building:material") or None, "building": tl.get("building"),
                     "ohm_start_date": t0.get("start_date"), "ohm_end_date": tl.get("end_date"),
                     "end_cause": tl.get("end_date:cause") or tl.get("end_date:note") or None,
                     "description": (t0.get("description") or tl.get("description") or "")[:300] or None,
                     "sources": " | ".join(srcs)[:600] or None,
                     "cited": any("arbitrary" not in str(x).lower() and "derived" not in str(x).lower() for x in srcs),
                     "ohm_url": ohm_url(gu.osm_type.values[i_], gu.osm_id.values[i_]),
                     "geometry": gu.geometry.values[last]})
    d = gpd.GeoDataFrame(rows, crs=UTM)
    # today's footprints (Overture): a footprint of the same shape means it still stands (or moved back) / is stale
    b = d.to_crs(4326).total_bounds
    from common import read_region_overture
    t = read_region_overture("building", columns=["id", "county", "geometry"],
                             filters=[("px", ">", b[0] - 0.01), ("px", "<", b[2] + 0.01), ("py", ">", b[1] - 0.01),
                                      ("py", "<", b[3] + 0.01)]).to_pandas()
    ov = gpd.GeoDataFrame(t, geometry=gpd.GeoSeries.from_wkb(t.geometry), crs=4326).to_crs(UTM)
    osidx = ov.sindex
    best, county = [], []
    for gm in d.geometry.values:
        bi, cty = 0.0, None
        for j in osidx.query(gm, predicate="intersects"):
            og = ov.geometry.values[j]
            iou = gm.intersection(og).area / max(gm.union(og).area, 1e-6)
            if iou > bi:
                bi, cty = iou, ov.county.values[j]
        best.append(round(bi, 2))
        county.append(cty)
    d["today_iou"] = best
    d["county"] = county
    # already traced elsewhere in the project (Sanborn areas, vanished sites)
    traced = []
    for f in glob.glob(str(SANBORN / "*_[12][0-9][0-9][0-9].geojson")) + [str(MANUAL / "vanished_sites" / "buildings.geojson")]:
        try:
            x = gpd.read_file(f).to_crs(UTM)
            x["file"] = Path(f).stem
            traced.append(x[["file", "geometry"]])
        except Exception:  # noqa: BLE001
            pass
    tr = gpd.GeoDataFrame(pd.concat(traced, ignore_index=True), crs=UTM)
    tsidx = tr.sindex
    dup = []
    for gm in d.geometry.values:
        hit = None
        for j in tsidx.query(gm, predicate="intersects"):
            tg = tr.geometry.values[j]
            if gm.intersection(tg).area / max(gm.union(tg).area, 1e-6) >= 0.4:
                hit = tr.file.values[j]
                break
        dup.append(hit)
    d["traced_in"] = dup
    # county where no footprint overlaps: the nearest of today's footprints
    miss = d.county.isna()
    if miss.any():
        near = gpd.sjoin_nearest(d[miss][["geometry"]], ov[["county", "geometry"]], how="left", max_distance=3000)
        near = near[~near.index.duplicated()]
        d.loc[miss, "county"] = near.county.reindex(d[miss].index).values
    d["county"] = d.county.fillna("")
    # on a vanished / industrial site already in data/manual (HP Cupertino, Bay Meadows...) or Camp Fremont
    sites = []
    for f in (MANUAL / "vanished_sites" / "sites.geojson", MANUAL / "industrial_sites" / "sites.geojson"):
        if f.exists():
            x = gpd.read_file(f).to_crs(UTM)
            sites.append(x[["site_id", "geometry"]])
    sites = gpd.GeoDataFrame(pd.concat(sites, ignore_index=True), crs=UTM)
    js = gpd.sjoin(gpd.GeoDataFrame(geometry=d.geometry.representative_point(), crs=UTM), sites, predicate="within")
    d["on_site"] = js.groupby(level=0).site_id.first().reindex(d.index).values
    camp = d.geometry.representative_point().within(CAMP_FREMONT_BOX) & (d.start_year >= 1916) & (d.end_year <= 1921)
    d.loc[camp.values, "on_site"] = "camp_fremont"
    llp = d.to_crs(4326).geometry.representative_point()
    d["other_agent_area"] = None
    for nm, (x0, y0, x1, y1) in OTHER_AGENT_AREAS.items():
        d.loc[((llp.x > x0) & (llp.x < x1) & (llp.y > y0) & (llp.y < y1)).values, "other_agent_area"] = nm
    _write_geojson(d, OHM_OUT / "region_demolished_ohm.geojson", "region_demolished_ohm")
    # the clean subset in the notable_demolished_region.csv format
    ok = d[d.cited & np.isfinite(d.start_year) & (d.end_year > d.start_year) & (d.today_iou < 0.5) & d.traced_in.isna()
           & d.on_site.isna() & (d.geometry.area >= 25)]
    ll = ok.to_crs(4326).geometry.representative_point()
    nd = pd.DataFrame({
        "id": ok.id.values, "name": ok.name.fillna("").values,
        "start_year": np.floor(ok.start_year.values).astype(int), "end_year": ok.end_year.round(2).values,
        "lat": ll.y.round(6).values, "lon": ll.x.round(6).values,
        "height_m": ok.height_m.values, "footprint_m": "", "storeys": ok.storeys.values, "material": ok.material.values,
        "shape_note": [f"Footprint: OpenHistoricalMap {u} (CC0; region_demolished_ohm.geojson). OHM dates "
                       f"{a} / {b_}" + (f"; end: {c}" if c else "") + (f"; {dsc}" if dsc else "")
                       for u, a, b_, c, dsc in zip(ok.ohm_url, ok.ohm_start_date, ok.ohm_end_date, ok.end_cause,
                                                    ok.description.fillna(""))],
        "source_url": [s_.split(" | ")[0] if s_.split(" | ")[0].startswith("http") else
                       next((x for x in s_.split(" | ") if x.startswith("http")), u)
                       for s_, u in zip(ok.sources, ok.ohm_url)],
        "county": ok.county.values, "other_agent_area": ok.other_agent_area.values})
    # already documented (data/tables/notable_demolished_region.csv): within 30 m, overlapping lifespans
    ex = pd.read_csv(TABLES / "notable_demolished_region.csv")
    exp = gpd.GeoSeries(gpd.points_from_xy(ex.lon, ex.lat), crs=4326).to_crs(UTM)
    ndp = gpd.GeoSeries(gpd.points_from_xy(nd.lon, nd.lat), crs=4326).to_crs(UTM)
    dupe = np.zeros(len(nd), bool)
    for k_, q in enumerate(ndp.values):
        dist = exp.distance(q).values
        ov_ = (ex.start_year.values < nd.end_year.values[k_]) & (ex.end_year.values > nd.start_year.values[k_])
        dupe[k_] = bool(((dist < 30) & ov_).any())
    if dupe.any():
        log(f"region: {int(dupe.sum())} rows already in notable_demolished_region.csv dropped: "
            + ", ".join(nd.name.values[dupe].astype(str)))
    nd = nd[~dupe]
    nd.to_csv(OHM_OUT / "notable_demolished_ohm.csv", index=False)
    log(f"region: {len(d)} OHM buildings with an end date (outside SF / Stanford / Sanborn tracings): "
        f"{(d.today_iou >= 0.5).sum()} match a footprint standing today, {d.traced_in.notna().sum()} already traced; "
        f"{len(nd)} cited, clean rows -> notable_demolished_ohm.csv")
    return d


# ================================================================== extras: Camp Fremont (vanished site)
CAMP_SRC = ("Camp Fremont", "fb297sh0179")


def write_camp_fremont(d=None):
    """Camp Fremont, the WWI Army training camp in Menlo Park (July 1917 - Oct 1919), from OHM's tracing of the
    1917 camp map (Stanford archive, purl.stanford.edu/fb297sh0179): outline, regiment plots, buildings, camp
    roads and the rail spur. vanished_sites/README.md had no map of the camp."""
    els = load_elements(glob.glob(str(OHM_RAW / "geom_*.json")))
    g = to_gdf(els)
    g = g.to_crs(UTM)
    inbox = g.geometry.representative_point().within(CAMP_FREMONT_BOX.buffer(800))
    txt = g.tags.map(lambda t: " ".join(str(v) for v in t.values()))
    sel = g[inbox & txt.map(lambda x: any(k in x for k in CAMP_SRC) or "Camp_Fremont" in x)].copy()
    sel["sd"] = sel.tags.map(lambda t: year_of(t.get("start_date")))
    sel["ed"] = sel.tags.map(lambda t: year_of(t.get("end_date")))
    sel = sel[(sel.sd >= 1916) & (sel.ed <= 1921) | sel.tags.map(lambda t: t.get("landuse") == "military")]
    src_of = lambda t: next((t[k] for k in ("source", "source:url") if str(t.get(k, "")).startswith("http")),  # noqa: E731
                            "https://purl.stanford.edu/fb297sh0179") if t else ""
    note_of = lambda t, i: (f"OpenHistoricalMap {ohm_url(*i)} (CC0), traced from the 1917 Camp Fremont map "  # noqa: E731
                            f"(Stanford archive); OHM dates {t.get('start_date')} / {t.get('end_date')}"
                            + (f"; {t.get('description')[:200]}" if t.get("description") else ""))
    parts, blds, lines = [], [], []
    for r in sel.itertuples():
        t = r.tags
        y0 = r.sd if np.isfinite(r.sd) else 1917.5
        y1 = r.ed if np.isfinite(r.ed) else 1919.75
        if r.geometry.geom_type in ("Polygon", "MultiPolygon") and "building" not in t:
            kind = "outline" if t.get("landuse") == "military" else "plot"
            parts.append({"site_id": "camp_fremont", "name": t.get("name") or ("Camp Fremont" if kind == "outline" else "camp plot"),
                          "kind": "military", "cover": "grass" if kind == "outline" else "industrial",
                          "surface": "army camp grounds" if kind == "outline" else f"regiment / camp area ({t.get('name') or 'unnamed'})",
                          "year_start": y0, "year_end": y1, "confidence": "estimated", "source_url": src_of(t),
                          "note": note_of(t, (r.osm_type, r.osm_id)), "geometry": r.geometry})
        elif "building" in t and r.geometry.geom_type in ("Polygon", "MultiPolygon"):
            nm = t.get("name") or ""
            blds.append({"site_id": "camp_fremont", "name": nm or "Camp Fremont building", "start_year": y0, "end_year": y1,
                         "height_m": 4.5, "storeys": 1, "material": "wood frame",
                         "use": "hall" if nm in ("YMCA", "Knights of Columbus") or "Hall" in nm else "other",
                         "confidence": "estimated", "source_url": src_of(t),
                         "note": note_of(t, (r.osm_type, r.osm_id)) + "; height ESTIMATED (one-storey wartime frame building)",
                         "geometry": r.geometry})
        elif r.geometry.geom_type in ("LineString", "MultiLineString"):
            lines.append({"site_id": "camp_fremont", "kind": t.get("highway") and "road" or t.get("railway") or
                          t.get("barrier") or t.get("man_made") or "line", "name": t.get("name"),
                          "year_start": y0, "year_end": y1, "source_url": src_of(t),
                          "note": note_of(t, (r.osm_type, r.osm_id)), "geometry": r.geometry})
    _write_geojson(gpd.GeoDataFrame(parts, crs=UTM), OHM_OUT / "vanished_sites_ohm.geojson", "vanished_sites_ohm")
    _write_geojson(gpd.GeoDataFrame(blds, crs=UTM), OHM_OUT / "vanished_buildings_ohm.geojson", "vanished_buildings_ohm")
    _write_geojson(gpd.GeoDataFrame(lines, crs=UTM), OHM_OUT / "camp_fremont_lines_ohm.geojson", "camp_fremont_lines_ohm")
    log(f"camp fremont: {len(parts)} ground parts, {len(blds)} buildings, {len(lines)} roads / rail / fences / sewers")


# ================================================================== extras: San Francisco (beyond the gold rush)
def write_sf_extras():
    """SF OHM buildings outside the gold-rush maps: cited construction years of standing buildings (SFPL branch
    libraries, churches, schools...) in the format of data/tables/known_building_dates.csv; documented demolished
    buildings in the notable_pre1906.csv format; the 1851 wharves of the Burnt District map."""
    els = load_elements([OHM_RAW / "ohm_sf_buildings.json"])
    g = to_gdf(els)
    g = g[g.tags.map(lambda t: gr_group(t)[0] is None)]
    g = g[g.geom_type.isin(["Polygon", "MultiPolygon"])].to_crs(UTM).reset_index(drop=True)
    t = g.tags
    cite = t.map(lambda d: next((d[k] for k in ("start_date:source", "source:start_date", "source", "source:url")
                                 if str(d.get(k, "")).startswith("http")), ""))
    skip = t.map(lambda d: "High Points on Four Great High Ways" in str(d.get("source", "")) or
                 "oldinsurancemaps" in str(d.get("source:url", "")))
    today = gpd.read_parquet(INTERIM / "sf_buildings.parquet", columns=["start_year", "year_reason", "geometry"]).to_crs(UTM)
    tsidx = today.sindex
    kb = pd.read_csv(TABLES / "known_building_dates.csv")
    kbp = gpd.GeoDataFrame(kb, geometry=gpd.points_from_xy(kb.lon, kb.lat), crs=4326).to_crs(UTM)
    rows, dem = [], []
    for k in range(len(g)):
        d = t.values[k]
        if skip.values[k] or d.get("shop") or str(d.get("start_date:edtf", "")).endswith("/..") or \
                (np.isfinite(year_of(d.get("end_date"))) and year_of(d.get("end_date")) < 2026 and
                 any(abs(year_of(d.get("end_date")) - year_of(t2.get("start_date"))) < 0.5 and t2 is not d
                     for t2 in t.values if (t2.get("addr:housenumber"), t2.get("addr:street")) ==
                     (d.get("addr:housenumber"), d.get("addr:street")) and d.get("addr:street"))):
            continue  # a business's founding year, or one version of a renamed / altered building
        gm = g.geometry.values[k]
        sd, ed = year_of(d.get("start_date")), year_of(d.get("end_date"))
        name = d.get("name") or d.get("amenity") or "building"
        if not np.isfinite(sd):
            continue
        if not np.isfinite(ed) and cite.values[k]:
            best, bi = None, 0.0
            for j in tsidx.query(gm, predicate="intersects"):
                tg = today.geometry.values[j]
                iou = gm.intersection(tg).area / max(gm.union(tg).area, 1e-6)
                if iou > bi:
                    best, bi = j, iou
            if best is None or bi < 0.4:
                continue
            fp = today.geometry.values[best]
            if kbp.within(fp).any():
                continue  # already researched
            if "eureka-valley" in cite.values[k]:
                continue  # 1902 is the branch's founding; its present building is of 1961 (SFPL)
            pt = gm.representative_point() if fp.contains(gm.representative_point()) else fp.representative_point()
            ll = gpd.GeoSeries([pt], crs=UTM).to_crs(4326).iloc[0]
            cy = float(today.start_year.values[best])
            rows.append({"id": f"ohm_{g.osm_type.values[k][0]}{g.osm_id.values[k]}", "name": name,
                         "lat": round(ll.y, 6), "lon": round(ll.x, 6), "start_year": int(np.floor(sd)), "end_year": 9999,
                         "source_url": cite.values[k],
                         "note": f"OpenHistoricalMap {ohm_url(g.osm_type.values[k], g.osm_id.values[k])} start_date "
                                 f"{d.get('start_date')} cited to the source; footprint IoU {bi:.2f}; the pipeline's "
                                 f"year now {cy:.0f} ({today.year_reason.values[best]}). CHECK: a branch's opening "
                                 "year can predate its present building."})
        elif np.isfinite(ed) and ed < 1990 and (cite.values[k] or d.get("name")) and d.get("name") != "City Hall":
            ll = gpd.GeoSeries([gm.representative_point()], crs=UTM).to_crs(4326).iloc[0]
            lv = pd.to_numeric(d.get("building:levels"), errors="coerce")
            dem.append({"id": f"ohm_{g.osm_type.values[k][0]}{g.osm_id.values[k]}", "name": name,
                        "start_year": int(np.floor(sd)), "end_year": round(ed, 2), "lat": round(ll.y, 6),
                        "lon": round(ll.x, 6), "height_m": pd.to_numeric(d.get("height"), errors="coerce"),
                        "footprint_m": "", "storeys": lv if np.isfinite(lv) else None,
                        "material": d.get("building:material") or "",
                        "shape_note": f"Footprint: OpenHistoricalMap {ohm_url(g.osm_type.values[k], g.osm_id.values[k])} "
                                      f"(CC0), {gm.area:.0f} m2; OHM dates {d.get('start_date')} / {d.get('end_date')}",
                        "source_url": cite.values[k] or ohm_url(g.osm_type.values[k], g.osm_id.values[k])})
    ge = to_gdf(load_elements(glob.glob(str(OHM_RAW / "geom_*.json"))),
                keep=lambda d: re.search(r"Ign?atius|Ingatius", str(d.get("name", ""))) is not None and d.get("amenity") == "school")
    for r in ge.to_crs(UTM).itertuples():
        d = r.tags
        sd, ed = year_of(d.get("start_date")), year_of(d.get("end_date"))
        if not (np.isfinite(sd) and np.isfinite(ed) and ed < 1880.5):
            continue  # the 1880-1906 Hayes St church + college is notable_pre1906.csv st_ignatius_1880
        ll = gpd.GeoSeries([r.geometry.representative_point()], crs=UTM).to_crs(4326).iloc[0]
        dem.append({"id": f"ohm_w{r.osm_id}", "name": f"St. Ignatius Church and College (Market St, {int(sd)}-{int(ed)})",
                    "start_year": int(sd), "end_year": float(ed), "lat": round(ll.y, 6), "lon": round(ll.x, 6),
                    "height_m": None, "footprint_m": "", "storeys": None, "material": "",
                    "shape_note": f"Footprint: OpenHistoricalMap {ohm_url('way', r.osm_id)} (CC0), {r.geometry.area:.0f} m2. "
                                  "The Jesuits' first church and college on Market St between 4th and 5th (1855; a larger "
                                  "building 1862) before the move to Hayes St / Van Ness in 1880. Dates from OHM (photo "
                                  "source); heights not known.",
                    "source_url": d.get("source") or ohm_url("way", r.osm_id)})
    pd.DataFrame(rows).sort_values("id").to_csv(OHM_OUT / "known_dates_ohm_sf.csv", index=False)
    pd.DataFrame(dem).sort_values("start_year").to_csv(OHM_OUT / "notable_sf_ohm.csv", index=False)
    # the wharves of the 1851 Burnt District map (lines: wharf centrelines)
    w = to_gdf(load_elements([OHM_RAW / "ohm_sf_wharves.json"]))
    w = w[w.tags.map(lambda d: "Burnt District" in str(d.get("source", "")))].to_crs(UTM)
    bands = fill_bands()
    out = []
    for r in w.itertuples():
        d = r.tags
        mid = r.geometry.interpolate(0.5, normalized=True)
        band = bands[bands.contains(mid) & ~bands.zone_id.str.startswith("fb_")]
        out.append({"name": d.get("name") or "wharf", "year_start": 1849.5, "year_end_fire": MAY_1851,
                    "burned_1851": str(d.get("end_date", "")).startswith("1851-05-04"),
                    "fill_zone": band.zone_id.iloc[0] if len(band) else None,
                    "filled_by": float(band.ye.iloc[0]) if len(band) else None,
                    "note": "Wharf centreline on the Burnt District map of the 4 May 1851 fire (OHM, CC0): burned "
                            "where the map shows it; most were rebuilt at once and became streets as Yerba Buena Cove was "
                            "filled (fill_zone / filled_by from data/manual/fill_zones.csv). Start ESTIMATED (the "
                            "wharves were built 1848-50).",
                    "source_url": GR_MAPS[1851]["url"], "ohm_url": ohm_url("way", r.osm_id), "geometry": r.geometry})
    _write_geojson(gpd.GeoDataFrame(out, crs=UTM), OHM_OUT / "sf_wharves_1851_ohm.geojson", "sf_wharves_1851_ohm")
    log(f"sf extras: {len(rows)} cited construction years (known_dates_ohm_sf.csv), {len(dem)} demolished "
        f"(notable_sf_ohm.csv), {len(out)} 1851 wharves")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("download", "all"):
        download()
    if cmd in ("goldrush", "all"):
        write_goldrush()
    if cmd in ("stanford", "all"):
        write_stanford()
    if cmd in ("rail", "extras", "all"):
        write_rail_picks(write_rail())
    if cmd in ("railextract", "extras", "all"):
        write_rail_extract()
    if cmd in ("newarea", "extras", "all"):
        write_new_area_review()
    if cmd in ("demolished", "extras", "all"):
        write_region_demolished()
    if cmd in ("camp", "extras", "all"):
        write_camp_fremont()
    if cmd in ("sf", "extras", "all"):
        write_sf_extras()
