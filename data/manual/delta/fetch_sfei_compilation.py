"""Fetch one study of SFEI's Historical Ecology GIS data compilation (c.1800 habitats) as GeoJSON.

The compilation (https://www.sfei.org/data/historical-ecology-gis-data-compilation, GPL v3, cite
SFEI-ASC) is served by CDFW BIOS as dataset ds3201 with the same fields as the per-study files in
data/raw/sfei_historical_ecology/ (LegLabel, ClickLabel, HEProject, ...), so a fetched study is
picked up by terrain_grid.hist_raster without any new class mapping (covers.SFEI_ECOLOGY).

  python fetch_sfei_compilation.py "Sacramento-San Joaquin Delta" delta
  python fetch_sfei_compilation.py "Laguna de Santa Rosa - Central Laguna" laguna_de_santa_rosa

Only polygons that touch the bounding box of the map extent (+0.05 deg) are kept.
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

URL = "https://services2.arcgis.com/Uq9r85Potqm3MfRV/arcgis/rest/services/biosds3201_fpu/FeatureServer/0/query"
BOX = (-123.72, 36.74, -121.12, 38.95)          # pipeline/extent.py EXTENT bounds + 0.05
FIELDS = "OBJECTID,LegLabel,LegCode,ClickLabel,ClickCode,HEDivision,HEProject,ProjectURL,Sources,InterpCert,ShapeCert,LocCert,Notes,RGB"
OUT = Path(__file__).resolve().parents[2] / "raw" / "sfei_historical_ecology"


def fetch(project, name, page=250):
    feats, off = [], 0
    while True:
        q = {"where": f"HEProject = '{project}'", "outFields": FIELDS, "outSR": 4326, "f": "geojson",
             "geometry": ",".join(map(str, BOX)), "geometryType": "esriGeometryEnvelope", "inSR": 4326,
             "spatialRel": "esriSpatialRelIntersects", "geometryPrecision": 6,
             "orderByFields": "OBJECTID", "resultOffset": off, "resultRecordCount": page}
        req = urllib.request.Request(URL + "?" + urllib.parse.urlencode(q), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=180) as r:
            d = json.loads(r.read())
        if "error" in d:
            raise RuntimeError(d["error"])
        feats += d["features"]
        print(f"{project}: {len(feats)} polygons", flush=True)
        if len(d["features"]) < page:
            break
        off += page
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{name}.geojson"
    out.write_text(json.dumps({"type": "FeatureCollection", "name": name, "features": feats}))
    print(f"-> {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    fetch(sys.argv[1], sys.argv[2])
