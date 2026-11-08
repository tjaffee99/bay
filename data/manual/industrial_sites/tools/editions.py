"""USGS historical topo editions covering a point, with the year each one shows.

  python -I editions.py LON LAT [--scales 24000,62500,31680]

The "map year" of an edition is its aerial-photo year (photorevisions: the revision's photo
year), else its survey / field-check year, else the imprint (TNM Access API + the sheet's
FGDC metadata, via the vanished-sites vt.py cache). Reprints of the same survey are merged.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vanished_sites" / "tools"))
import vt  # noqa: E402


def map_year(title, yrs):
    import re
    m = re.search(r"(\d{4})$", title)
    ty = int(m.group(1)) if m else None
    # a re-issue whose title year is later than its survey (e.g. San Francisco 1:62,500
    # "1915", surveyed 1892-94) carries the culture of the title year
    if ty and "Survey" in yrs and ty > yrs["Survey"] + 2 and not any(
            k in yrs for k in ("Aerial Photo", "Photo Revision", "Field Check")):
        return ty, "title"
    for k in ("Photo Revision", "Aerial Photo", "Survey", "Field Check", "Edit", "Imprint"):
        if k in yrs:
            if k == "Photo Revision" and "Aerial Photo" in yrs:
                return yrs["Aerial Photo"], k
            return yrs[k], k
    return (ty, "title") if ty else (None, "")


def editions(lon, lat, scales=("24000", "62500", "31680", "125000")):
    d = 0.002
    items = vt.topo_list(round(lon - d, 3), round(lat - d, 3), round(lon + d, 3), round(lat + d, 3))
    out = {}
    for it in items:
        sc = next((s for s in scales if f"1:{s}-scale" in it["title"]), None)
        if not sc or not it["urls"].get("GeoTIFF"):
            continue
        yrs = vt.topo_years(it)
        y, kind = map_year(it["title"], yrs)
        name = it["title"].split("Quadrangle for ")[-1]
        # older scales: every reprint (imprint) separately - reprints were often updated
        key = (sc, name.rsplit(" ", 1)[0], y, yrs.get("Photo Revision"), yrs.get("Photo Inspection"),
               yrs.get("Imprint") if sc != "24000" else None)
        url = it["urls"]["GeoTIFF"]
        if key not in out or "Imprint" in yrs and out[key][3] and yrs.get("Imprint", 9999) < out[key][3]:
            out[key] = (int(sc), name, y, yrs.get("Imprint"), kind, url, yrs)
    return sorted(out.values(), key=lambda t: (t[2] or 0, t[0]))


if __name__ == "__main__":
    lon, lat = float(sys.argv[1]), float(sys.argv[2])
    sc = sys.argv[sys.argv.index("--scales") + 1].split(",") if "--scales" in sys.argv else ("24000", "62500", "31680")
    for s, name, y, imp, kind, url, yrs in editions(lon, lat, sc):
        print(f"{y} {kind[:6]:6s} 1:{s:<6d} {name:32s} imp {imp}  {url.split('/')[-1]}")
