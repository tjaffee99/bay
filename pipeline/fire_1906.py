"""Stage: 1906 burned-area polygon from the hand-researched boundary.

Input (committed, hand-researched):
  data/manual/fire_1906_boundary.csv          ordered ring of street intersections
  data/manual/fire_1906_unburned_islands.csv  rings of unburned islands (optional)
Lookup: DataSF street centerlines (active + retired) — an intersection is the
node shared by segments of both streets; if the streets never meet (e.g. the
waterfront), the midpoint of their closest approach is used.

Outputs:
  data/interim/fire_1906.geojson    polygon (burned minus islands), for QGIS/pipeline
  viewer/public/data/fire-1906.json same, simplified, for the viewer overlay
  data/interim/fire_1906_vertices.csv  resolved vertex coordinates + method (for review)
"""
from __future__ import annotations

import csv
import glob
import json
import re

import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry import Point, Polygon, mapping
from shapely.ops import nearest_points

from common import INTERIM, MANUAL, RAW, VIEWER_DATA, log

SUFFIX = {
    "STREET": "ST", "AVENUE": "AVE", "BOULEVARD": "BLVD", "PLACE": "PL", "ROAD": "RD",
    "TERRACE": "TER", "COURT": "CT", "DRIVE": "DR", "LANE": "LN", "ALLEY": "ALY",
    "WAY": "WAY", "HIGHWAY": "HWY", "PLAZA": "PLZ", "SQUARE": "SQ",
}
UTM = "EPSG:32610"


ORDINALS = {"FIRST": 1, "SECOND": 2, "THIRD": 3, "FOURTH": 4, "FIFTH": 5, "SIXTH": 6, "SEVENTH": 7,
            "EIGHTH": 8, "NINTH": 9, "TENTH": 10, "ELEVENTH": 11, "TWELFTH": 12, "THIRTEENTH": 13,
            "FOURTEENTH": 14, "FIFTEENTH": 15, "SIXTEENTH": 16, "SEVENTEENTH": 17, "EIGHTEENTH": 18,
            "NINETEENTH": 19, "TWENTIETH": 20}


def norm(name: str) -> tuple[str, str]:
    """('VAN NESS', 'AVE') from 'Van Ness Avenue' / 'VAN NESS AVE'; '3rd St' -> ('03TH', 'ST')."""
    s = re.sub(r"[^A-Z0-9 ]", " ", name.upper())
    s = re.sub(r"^THE ", "", s.strip())
    s = re.sub(r"\b(\d+)(ST|ND|RD|TH)\b", lambda m: f"{int(m.group(1)):02d}TH", s)
    s = re.sub(r"\b(" + "|".join(ORDINALS) + r")\b", lambda m: f"{ORDINALS[m.group(1)]:02d}TH", s)
    parts = s.split()
    if len(parts) > 1 and (parts[-1] in SUFFIX or parts[-1] in SUFFIX.values()):
        return " ".join(parts[:-1]), SUFFIX.get(parts[-1], parts[-1])
    return " ".join(parts), ""


def load_streets() -> gpd.GeoDataFrame:
    st = gpd.GeoDataFrame(pd.concat([gpd.read_file(p) for p in sorted(glob.glob(str(RAW / "sf_streets" / "page-*.geojson")))]), crs=4326)
    # normalise exactly like the hand-written names ("03RD" -> "03TH", "THE EMBARCADERO" -> "EMBARCADERO")
    st["base"] = st.street.fillna("").map(lambda n: norm(n)[0])
    st["type"] = st.st_type.fillna("").str.upper().str.strip()
    return st.to_crs(UTM)


def street_rows(st, name):
    base, typ = norm(name)
    rows = st[st.base == base]
    if rows.empty and " " in base:  # e.g. "Clinton Park" stored as street CLINTON, type PARK
        rows = st[st.base == base.rsplit(" ", 1)[0]]
    if typ and (rows.type == typ).any():
        rows = rows[rows.type == typ]
    return rows


def intersection(st, a: str, b: str):
    ra, rb = street_rows(st, a), street_rows(st, b)
    if ra.empty or rb.empty:
        return None, f"unknown street: {a if ra.empty else b}"
    nodes_a = set(ra.f_node_cnn.dropna()) | set(ra.t_node_cnn.dropna())
    nodes_b = set(rb.f_node_cnn.dropna()) | set(rb.t_node_cnn.dropna())
    common = nodes_a & nodes_b
    if common:
        pts = []
        for _, r in pd.concat([ra, rb]).iterrows():
            coords = list(r.geometry.coords) if r.geometry.geom_type == "LineString" else list(r.geometry.geoms[0].coords)
            if r.f_node_cnn in common:
                pts.append(coords[0])
            if r.t_node_cnn in common:
                pts.append(coords[-1])
        x = sum(p[0] for p in pts) / len(pts)
        y = sum(p[1] for p in pts) / len(pts)
        return Point(x, y), "node"
    ga, gb = shapely.union_all(ra.geometry.values), shapely.union_all(rb.geometry.values)
    pa, pb = nearest_points(ga, gb)
    d = pa.distance(pb)
    return Point((pa.x + pb.x) / 2, (pa.y + pb.y) / 2), f"closest-approach {d:.0f}m"


EXPLICIT = re.compile(r"@\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)")
TO_UTM = None


def explicit_point(note: str):
    """Researchers mark mid-block vertices with '@lat,lon' in the note."""
    m = EXPLICIT.search(note or "")
    if not m:
        return None
    lat, lon = float(m.group(1)), float(m.group(2))
    return gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(UTM).iloc[0]


def ring_from(rows, st, log_rows, label):
    pts = []
    for r in rows:
        p = explicit_point(r.get("note", ""))
        how = "explicit"
        if p is None:
            p, how = intersection(st, r["street_a"], r["street_b"])
        log_rows.append({"ring": label, "seq": r.get("seq"), "street_a": r["street_a"], "street_b": r["street_b"],
                         "method": how, "x": p.x if p else "", "y": p.y if p else ""})
        if p is not None:
            pts.append(p)
        else:
            log(f"fire: WARNING {label} seq {r.get('seq')}: {how}")
    return pts


def main():
    src = MANUAL / "fire_1906_boundary.csv"
    if not src.exists():
        log("fire: no data/manual/fire_1906_boundary.csv yet; skipping")
        return
    st = load_streets()
    log_rows = []
    rows = list(csv.DictReader(open(src)))
    rows.sort(key=lambda r: float(r.get("seq") or 0))
    outer = ring_from(rows, st, log_rows, "burned")
    poly = shapely.make_valid(Polygon([(p.x, p.y) for p in outer]))

    isl_src = MANUAL / "fire_1906_unburned_islands.csv"
    islands = []
    if isl_src.exists():
        isl_rows = list(csv.DictReader(open(isl_src)))
        for name in dict.fromkeys(r["island"] for r in isl_rows):
            ring = [r for r in isl_rows if r["island"] == name]
            ring.sort(key=lambda r: float(r.get("seq") or 0))
            pts = ring_from(ring, st, log_rows, f"island:{name}")
            if len(pts) >= 3:
                islands.append(shapely.make_valid(Polygon([(p.x, p.y) for p in pts])))
            elif len(pts) >= 1:
                # a single building/point island: buffer ~ half a block
                islands.append(shapely.union_all([p.buffer(45) for p in pts]))
    burned = poly.difference(shapely.union_all(islands)) if islands else poly

    g = gpd.GeoSeries([burned], crs=UTM)
    area_acres = g.area.iloc[0] / 4046.86
    log(f"fire: burned polygon {area_acres:.0f} acres ({len(outer)} vertices, {len(islands)} islands)")
    out = g.to_crs(4326)
    feat = {"type": "Feature", "properties": {"kind": "burned_area", "start_year": 1906.3, "end_year": 1906.3,
                                              "source": "fire_1906", "acres": round(area_acres)},
            "geometry": mapping(out.iloc[0])}
    (INTERIM / "fire_1906.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [feat]}))
    simp = gpd.GeoSeries([burned], crs=UTM).simplify(3).to_crs(4326)
    feat["geometry"] = mapping(shapely.set_precision(simp.iloc[0], 1e-6))
    (VIEWER_DATA / "fire-1906.json").write_text(json.dumps({"type": "FeatureCollection", "features": [feat]}))
    with open(INTERIM / "fire_1906_vertices.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(log_rows[0].keys()))
        w.writeheader()
        w.writerows(log_rows)


if __name__ == "__main__":
    main()
