"""NAS Alameda pavement phases -> data/manual/airports_extra.geojson (the 'Naval Air Station Alameda' pieces).

  cd data/manual/airports && ../../../.venv/bin/python -I tools/nas.py

The runway / taxiway / apron polygons of NAS Alameda (OSM abandoned runways + orthophoto pavement, i.e. the pavement
that is still there at Alameda Point) are cut along the shore of the 1946-photo USGS Oakland West sheet
(FIELD_1946, local metres, traced from the topo water tint; the same ground as the fill_zones rows
al_alameda_airport_point / al_alameda_benton_field_navy_fill / al_alameda_nas_inner_bay):
  * inside  -> start 1941 (the station's field: commissioned 1 Nov 1940, camouflaged runways on a 1943 photo,
               5 paved runways on the USGS aerial of 29 Jul 1946) - ESTIMATED;
  * outside -> start 1957 (the west / south additions for the jet runways: water on the 1946 sheet, land and
               runway on the 1958-photo sheet and the USGS aerial of 12 Aug 1958; 13/31 8,000 ft on the April 1959
               chart) - ESTIMATED;
  * every piece end_year 9999: the airfield closed 25 Apr 1997 (BRAC) but its pavement was never removed - "a 4/2/18
    aerial view looking north shows the NAS Alameda airfield remained almost completely intact, with an extensive
    network of runways, taxiways, large ramp areas" (airfields-freeman.com); the airport outline itself still closes in
    1997 (data/tables/airports.csv).
airports.py keeps a piece's own start_year / end_year and waits for its ground (land year + 0.5).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

MANUAL = Path(__file__).resolve().parents[2]
NAME = "Naval Air Station Alameda"
CX, CY = -122.305, 37.790
SRC = "https://www.airfields-freeman.com/CA/Airfields_CA_Oakland.htm"
FIELD_1946 = [
    (-2229, -166), (-2229, 24), (-2196, 124), (-2229, 303), (-2224, 702), (-1863, 671), (-1680, 583), (-1555, 581),
    (-1533, 554), (-1374, 521), (-1350, 493), (-1161, 461), (-1017, 373), (-832, 365), (-744, 313), (-529, 281),
    (-507, 254), (-345, 221), (-321, 193), (-213, 191), (-111, 133), (106, 101), (134, 72), (226, 71), (344, 12),
    (747, 12), (777, 41), (871, 42), (980, 86), (1050, 42), (1160, 123), (1263, 66), (1313, 71), (1364, 14),
    (1466, 11), (1469, -1424), (1250, -1428), (1222, -1457), (1103, -1458), (1073, -1487), (1008, -1488),
    (987, -1518), (1016, -1552), (1027, -1691), (1097, -1726), (1164, -1728), (1209, -1782), (1314, -1818),
    (1468, -1939), (1469, -2082), (1388, -2076), (1373, -2167), (1233, -2308), (1225, -2356), (1202, -2357),
    (1181, -2241), (1110, -2237), (933, -2149), (837, -2147), (756, -2090), (687, -2082), (603, -2029), (537, -2027),
    (513, -1999), (228, -2016), (197, -1998), (21, -1994), (18, -1941), (67, -1908), (128, -1908), (195, -1948),
    (264, -1937), (286, -1908), (345, -1938), (375, -1925), (379, -1838), (345, -1806), (116, -1781), (111, -1762),
    (305, -1757), (366, -1725), (437, -1652), (442, -1594), (588, -1475), (593, -1150), (555, -1105), (146, -1097),
    (61, -1072), (20, -1085), (-282, -1047), (-311, -1075), (-319, -1229), (-399, -1197), (-529, -1217),
    (-752, -1182), (-924, -1194), (-1098, -1158), (-1410, -1157), (-1470, -1138), (-1577, -1157), (-1716, -1041),
    (-1879, -986), (-1877, -746), (-1856, -708), (-1879, -643), (-1879, -455), (-1860, -421), (-1885, -202)]
INSIDE = dict(start_year=1941, note="NAS Alameda field of the 1946-photo USGS sheet (commissioned 1 Nov 1940; 5 paved "
              "runways on the 29 Jul 1946 USGS aerial) - start ESTIMATED; pavement still at Alameda Point (end 9999)")
OUTSIDE = dict(start_year=1957, note="west / south additions for the jet runways: bay on the 1946-photo sheet, runway "
               "and ramp on the 1958-photo sheet and the 12 Aug 1958 USGS aerial (8,000-ft 13/31 on the April 1959 chart) - "
               "start ESTIMATED; pavement still at Alameda Point (end 9999)")


def main():
    import shapely
    from shapely.geometry import Polygon, mapping, shape
    k = 111320 * math.cos(math.radians(CY))
    field = Polygon([(CX + x / k, CY + y / 110574) for x, y in FIELD_1946])
    ef = MANUAL / "airports_extra.geojson"
    d = json.loads(ef.read_text())
    keep = [f for f in d["features"] if f["properties"].get("airport") != NAME]
    nas = [f for f in d["features"] if f["properties"].get("airport") == NAME]
    out = []
    for f in nas:
        g = shape(f["geometry"])
        for part, meta in ((g.intersection(field), INSIDE), (g.difference(field), OUTSIDE)):
            for p in getattr(part, "geoms", [part]):
                if p.geom_type != "Polygon" or p.area * k * 110574 < 150:     # < 150 m2: slivers along the cut
                    continue
                out.append({"type": "Feature", "properties": {
                    "airport": NAME, "kind": f["properties"]["kind"], "start_year": meta["start_year"], "end_year": 9999,
                    "width_m": None, "confidence": "estimated", "source_url": SRC, "note": meta["note"]},
                    "geometry": mapping(shapely.set_precision(p, 1e-7))})
    d["features"] = out + keep
    add = (" NAS Alameda pieces cut at the 1946-photo shore (data/manual/airports/tools/nas.py): 1941 inside, 1957 "
           "outside (jet-runway additions), all still standing (end 9999).")
    if "tools/nas.py" not in d.get("description", ""):
        d["description"] = d.get("description", "") + add
    ef.write_text(json.dumps(d))
    n_in = sum(1 for f in out if f["properties"]["start_year"] == 1941)
    print(f"{NAME}: {len(nas)} pieces -> {len(out)} ({n_in} from 1941, {len(out) - n_in} from 1957), all to 9999")


if __name__ == "__main__":
    main()
