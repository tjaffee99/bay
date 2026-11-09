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
            return linemerge(unary_union([LineString(c) for c in lines]))
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


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("download", "all"):
        download()
