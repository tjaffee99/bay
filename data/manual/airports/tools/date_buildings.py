"""Date today's airport footprints by the USGS topo editions that first draw them.

  python -I date_buildings.py SFO|OAK|SJC BLDG.geojson OUT.csv

Uses the industrial-sites edition tools (../../industrial_sites/tools/date_editions.py):
every 1:24,000 / 1:62,500 edition covering the airport is resampled into a local metre
frame; a footprint is drawn when building ink covers >= 30 % of it (+6 m tolerance).
Output per footprint: first edition drawing it, last earlier edition not drawing it,
latest edition still drawing it, estimated start (midpoint), evidence string.
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

T = Path(__file__).resolve().parents[2] / "industrial_sites" / "tools"
sys.path.insert(0, str(T))
from date_editions import presence, start_years  # noqa: E402
from editions import editions  # noqa: E402

FOUNDED = {"SFO": 1927, "OAK": 1927, "SJC": 1945}


def main():
    ap, src, out = sys.argv[1:4]
    fps = gpd.read_file(src)
    fps = fps[fps.geometry.geom_type == "Polygon"].reset_index(drop=True)
    u = fps.to_crs(32610)
    fps["area_m2"] = u.area.values
    fps["circ"] = (4 * np.pi * u.area / u.length ** 2).values
    site = shapely.union_all(fps.geometry.values).envelope
    b = site.bounds
    eds = editions((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, bbox=b)
    eds = [e for e in eds if e[2] and e[2] >= FOUNDED[ap] - 20 and e[0] in (24000, 62500)]
    for e in eds:
        print(e[2], e[0], e[1], e[3], e[5].split("/")[-1])
    pr = presence(site, fps, eds, max_half=3500.0, log=print)
    pr["url"] = pr.sheet.map({e[1]: e[5] for e in eds})
    pr.to_csv(out.replace(".csv", "_presence.csv"), index=False)
    st = start_years(pr, fps, FOUNDED[ap])
    r = fps.drop(columns="geometry").join(st)
    first_url = pr[pr.present].sort_values("pyear").groupby("fi").url.first()
    r["first_url"] = first_url.reindex(r.index).values
    r.to_csv(out, index=False)
    print(out, len(r), r.first_drawn.notna().sum(), "drawn")


if __name__ == "__main__":
    main()
