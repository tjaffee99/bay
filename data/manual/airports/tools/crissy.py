"""Crissy Field (Presidio of San Francisco, Army airfield 1921-74) -> data/manual/airports_extra.geojson
(paved runway pieces with their own years) + airports_extra_outlines.geojson (airfield outline).

  python -I crissy.py          (idempotent: replaces the features of airport / name "Crissy Field")

Traced on the USGS 1:24,000 San Francisco North sheets (TNM historical topo GeoTIFFs, rendered into
a north-up metre frame around (-122.4600, 37.8040) with ../tools/render.py, 1 m per pixel):
* 1950 edition, 1946 photos: the open field between the shore road and the road / Belt Railroad spur
  south of it, from the WWII buildings at the west end to the barracks at the east end
  (~775 x 100 m; "5,000 x 400 ft" field in the 1937 Airports Directory) -> the outline;
* 1956 edition (1956 photos): a 25-30 m strip from x = -197 to the east end (~590 m) - the paved
  runway (7/1946 aerial: unpaved runway with some pavement; 8/1948 aerial: paved runway);
* 1956 sheet, 1968 photorevision: the runway outline in purple from (-377, -37) to (395, 123),
  ~790 m x 28 m (Runway 6/24, 2,610 ft in the 1960 Jeppesen manual; 2,900 ft paved on the
  Apr 1959 chart) - the west 180 m added between the 1956 sheet and the 1959 chart.
Runway gone in the 1999-2001 restoration (1998 topo still shows it, 2000 aerial: removed).
Dates: Freeman, Abandoned & Little-Known Airfields (aerials 1946/1948, charts 1959/1960/1967),
NPS (Haller 1994, "The Last Word in Airfields"), Wikipedia.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANUAL = HERE.parents[1]
CX, CY = -122.4600, 37.8040
NAME = "Crissy Field"
SRC = "https://www.airfields-freeman.com/CA/Airfields_CA_SanFran.htm"


def ll(x, y):
    k = 111320 * math.cos(math.radians(CY))
    return [round(CX + x / k, 7), round(CY + y / 110574, 7)]


def strip(a, b, w):
    (x0, y0), (x1, y1) = a, b
    L = math.hypot(x1 - x0, y1 - y0)
    nx, ny = -(y1 - y0) / L * w / 2, (x1 - x0) / L * w / 2
    ring = [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny), (x0 + nx, y0 + ny)]
    return [[ll(x, y) for x, y in ring]]


W, MID, E = (-377.0, -37.0), (-197.0, 0.3), (395.0, 123.0)
PIECES = [
    dict(kind="runway", start_year=1947.5, end_year=1999, a=MID, b=E, width_m=28,
         note="paved Runway 6/24, east part: the strip on the 1956 sheet (1956 photos); unpaved runway with a "
              "paved surface on its south side in a 7/1946 aerial, paved in an 8/1948 aerial -> 1947.5 (ESTIMATED); "
              "removed for the Crissy Field restoration (on the 1998 topo, gone in a 2000 aerial) -> 1999 (ESTIMATED)"),
    dict(kind="runway", start_year=1958, end_year=1999, a=W, b=MID, width_m=28,
         note="west extension of Runway 6/24: not on the 1956 sheet, on the 1968 photorevision; 2,900 ft paved on the "
              "Apr 1959 chart, 2,610 ft in the 1960 Jeppesen manual -> 1958 (ESTIMATED); removed 1999 (ESTIMATED)"),
]
# 1946-photo sheet: the field between the shore road and the road / rail spur (local metres)
FIELD_1946 = [(-325, 30), (-300, 48), (-200, 55), (0, 82), (200, 112), (450, 150), (450, 57), (200, 22), (0, -12),
              (-175, -40), (-325, 30)]


def main():
    import shapely
    from shapely.geometry import Polygon, mapping, shape
    ef = MANUAL / "airports_extra.geojson"
    eo = MANUAL / "airports_extra_outlines.geojson"
    d = json.loads(ef.read_text())
    d["features"] = [f for f in d["features"] if f["properties"].get("airport") != NAME]
    for p in PIECES:
        d["features"].append({"type": "Feature", "properties": {
            "airport": NAME, "kind": p["kind"], "start_year": p["start_year"], "end_year": p["end_year"],
            "width_m": p["width_m"], "confidence": "estimated", "source_url": SRC, "note": p["note"]},
            "geometry": {"type": "Polygon", "coordinates": strip(p["a"], p["b"], p["width_m"])}})
    add = (" Crissy Field (Presidio, Army airfield 1921-74): paved runway pieces traced on the USGS 1:24,000 "
           "San Francisco North sheets (1956; 1968 photorevision), each with its own start_year / end_year "
           "(data/manual/airports/tools/crissy.py).")
    if "Crissy" not in d.get("description", ""):
        d["description"] = d.get("description", "") + add
    ef.write_text(json.dumps(d))
    o = json.loads(eo.read_text())
    o["features"] = [f for f in o["features"] if f["properties"].get("name") != NAME]
    field = Polygon([ll(x, y) for x, y in FIELD_1946])
    rw = shapely.union_all([shape({"type": "Polygon", "coordinates": strip(p["a"], p["b"], p["width_m"] + 30)})
                            for p in PIECES])
    outline = shapely.union_all([field, rw]).buffer(0)
    o["features"].append({"type": "Feature", "properties": {"name": NAME, "class": "military_airport"},
                          "geometry": mapping(shapely.set_precision(outline, 1e-7))})
    if "Crissy" not in o.get("description", ""):
        o["description"] = o.get("description", "") + (
            " Crissy Field: the open field on the 1946-photo USGS San Francisco North sheet (between the shore road "
            "and the Belt Railroad spur) + the 1968 runway, 15 m margin (data/manual/airports/tools/crissy.py).")
    eo.write_text(json.dumps(o))
    k = 111320 * math.cos(math.radians(CY)) * 110574
    print(f"{NAME}: {len(PIECES)} runway pieces, outline {outline.area * k / 1e4:.1f} ha")


if __name__ == "__main__":
    main()
