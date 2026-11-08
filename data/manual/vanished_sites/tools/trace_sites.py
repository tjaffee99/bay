"""Vanished large sites: traced ground parts (sites.geojson) and buildings (buildings.geojson).

Every site is worked in a local metre frame around (cx, cy) (x east, y north,
equirectangular: x = (lon - cx) * 111320 cos(cy), y = (lat - cy) * 110574 — the frame of
the landmark kit). Sources per site in README.md; the tools in this folder render the
USGS historical topographic GeoTIFFs (NADCON NAD27 -> WGS84) and the Esri Wayback
orthophotos into these frames (`vt.py`), find building symbols (`blobs.py`), fit racetrack
ovals (`oval.py`) and date footprints by their presence on successive map editions
(`presence.py`).

python -I trace_sites.py            -> ../sites.geojson, ../buildings.geojson
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Polygon, MultiPolygon, LineString, mapping, shape
from shapely import affinity

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import geom  # noqa: E402

OUT = HERE.parent
TOPO = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/"
CACHE = Path("/home/user/bay/data/raw/vanished_sites")

SITES: list[dict] = []
BLDGS: list[dict] = []


class Site:
    def __init__(self, site_id, name, kind, cx, cy, source_url):
        self.id, self.name, self.kind, self.cx, self.cy, self.src = site_id, name, kind, cx, cy, source_url
        self.k = 111320 * math.cos(math.radians(cy))

    # local metres -> lon/lat
    def ll(self, g):
        return shapely.transform(g, lambda xy: np.column_stack([self.cx + xy[:, 0] / self.k, self.cy + xy[:, 1] / 110574]))

    def loc(self, g):
        return shapely.transform(g, lambda xy: np.column_stack([(xy[:, 0] - self.cx) * self.k, (xy[:, 1] - self.cy) * 110574]))

    def part(self, g, cover, y0, y1, conf, note, surface=None, name=None, src=None):
        g = shapely.make_valid(g)
        if g.is_empty or g.area < 1:
            return
        SITES.append({"geometry": self.ll(g), "site_id": self.id, "name": name or self.name, "kind": self.kind,
                      "cover": cover, "surface": surface or cover, "year_start": y0, "year_end": y1,
                      "confidence": conf, "source_url": src or self.src, "note": note})

    def bldg(self, g, name, y0, y1, h, storeys, material, use, conf, note, src=None):
        g = shapely.make_valid(g)
        if g.is_empty or g.area < 4:
            return
        BLDGS.append({"geometry": self.ll(g), "site_id": self.id, "name": name, "start_year": y0, "end_year": y1,
                      "height_m": h, "storeys": storeys, "material": material, "use": use,
                      "confidence": conf, "source_url": src or self.src, "note": note})


def P(coords):
    return Polygon(coords).buffer(0)


def ring(outer, inner):
    return outer.difference(inner)


def path_poly(coords, width):
    return LineString(coords).buffer(width / 2, cap_style=2, join_style=1)


# =====================================================================================
def write():
    def fc(rows):
        feats = []
        for r in rows:
            g = r.pop("geometry")
            g = shapely.set_precision(g, 1e-7)
            feats.append({"type": "Feature", "properties": r, "geometry": mapping(g)})
        return {"type": "FeatureCollection", "features": feats}
    (OUT / "sites.geojson").write_text(json.dumps(fc(SITES), separators=(",", ":")))
    (OUT / "buildings.geojson").write_text(json.dumps(fc(BLDGS), separators=(",", ":")))
    print(f"sites.geojson: {len(SITES)} parts; buildings.geojson: {len(BLDGS)} footprints")


if __name__ == "__main__":
    import trace_sites as ts  # the module instance sites_def appends to
    import sites_def  # noqa: E402
    if len(sys.argv) > 1:
        ts.OUT = Path(sys.argv[1])
    sites_def.build()
    ts.write()
