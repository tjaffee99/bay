"""Turn researched rings into polygons.

Ring formats used in data/manual and data/tables:
  * ring_type = lonlat   "lon lat; lon lat; …"
  * ring_type = streets  "Street A & Street B; Street C & Street D; @lat,lon; …"
    (present-day SF street names; '@lat,lon' entries are explicit vertices for
    offshore / vanished corners)
  * ordered intersection CSVs (fire_1906_boundary.csv, sf_extent_YYYY.csv):
    rows of street_a, street_b with an optional '@lat,lon' at the start of `note`
All results are shapely polygons in EPSG:3857 unless asked otherwise.
"""
from __future__ import annotations

import csv
import re
from functools import lru_cache

import geopandas as gpd
import shapely
from shapely.geometry import Point, Polygon

from fire_1906 import UTM, explicit_point, intersection, load_streets

AT = re.compile(r"@\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)")


@lru_cache(maxsize=1)
def streets():
    return load_streets()


def _to(geom, crs_from, crs_to):
    return gpd.GeoSeries([geom], crs=crs_from).to_crs(crs_to).iloc[0]


def ring_polygon(ring: str, ring_type: str, crs="EPSG:3857"):
    ring_type = (ring_type or "").strip()
    pts = []
    if ring_type == "lonlat":
        for p in str(ring).split(";"):
            p = p.strip()
            if p:
                x, y = map(float, p.split()[:2])
                pts.append((x, y))
        if len(pts) < 3:
            return None
        return _to(shapely.make_valid(Polygon(pts)), 4326, crs)
    if ring_type == "streets":
        st = streets()
        for entry in str(ring).split(";"):
            entry = entry.strip()
            if not entry:
                continue
            m = AT.search(entry)
            if m:
                lat, lon = float(m.group(1)), float(m.group(2))
                p = _to(Point(lon, lat), 4326, UTM)
            elif "&" in entry:
                a, b = (s.strip() for s in entry.split("&", 1))
                p, _ = intersection(st, a, b)
            else:
                p = None
            if p is not None:
                pts.append((p.x, p.y))
        if len(pts) < 3:
            return None
        return _to(shapely.make_valid(Polygon(pts)), UTM, crs)
    return None


def intersection_rings(path, crs="EPSG:3857"):
    """{ring_id: polygon} from an ordered intersection CSV (ring,seq,street_a,street_b,note)."""
    rows = list(csv.DictReader(open(path)))
    out = {}
    st = streets()
    for rid in dict.fromkeys(r.get("ring", "main") for r in rows):
        ring = sorted([r for r in rows if r.get("ring", "main") == rid], key=lambda r: float(r.get("seq") or 0))
        pts = []
        for r in ring:
            p = explicit_point(r.get("note", ""))
            if p is None:
                p, _ = intersection(st, r["street_a"], r["street_b"])
            if p is not None:
                pts.append((p.x, p.y))
        if len(pts) >= 3:
            out[rid] = _to(shapely.make_valid(Polygon(pts)), UTM, crs)
    return out
