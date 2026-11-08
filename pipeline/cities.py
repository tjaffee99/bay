"""Cities, towns and counties for the population counter.

Outlines: US Census TIGER/Line 2024 places (incorporated cities / towns and census-
designated places) and counties inside the map's extent, simplified to ~40 m.
Populations: data/tables/population_places.csv (decennial censuses + the latest DOF
estimate per place, county and the 6-county region; see data/research/population_places.md).

Output: viewer/public/data/cities.json
  {"places": [{name, geoid, kind, rings}], "counties": [{name, geoid, rings}],
   "pop": {geoid_or_name: [[year, population], ...]}, "region": [[year, population], ...],
   "region_label": "..."}
"""
from __future__ import annotations

import json

import geopandas as gpd
import numpy as np
import pandas as pd

from common import RAW, TABLES, VIEWER_DATA, log
from extent import POLY, in_extent

COUNTIES = {"001": "Alameda", "013": "Contra Costa", "041": "Marin", "075": "San Francisco", "081": "San Mateo",
            "085": "Santa Clara"}


def rings_of(geom, tol=0.0004):
    g = geom.simplify(tol, preserve_topology=True)
    out = []
    for p in getattr(g, "geoms", [g]):
        if p.geom_type != "Polygon" or p.is_empty:
            continue
        out.append([[round(x, 5), round(y, 5)] for x, y in np.asarray(p.exterior.coords)[:, :2]])
    return out


def main():
    pl = gpd.read_file(f"zip://{RAW / 'tiger' / 'tl_2024_06_place.zip'}").to_crs(4326)
    pl = pl[in_extent(pl.geometry.representative_point(), margin=0.0)]
    places = [{"name": r.NAME, "geoid": r.GEOID, "kind": "cdp" if str(r.CLASSFP).startswith("U") else "city",
               "rings": rings_of(r.geometry)} for r in pl.itertuples()]
    co = gpd.read_file(f"zip://{RAW / 'tiger' / 'tl_2024_us_county.zip'}")
    co = co[(co.STATEFP == "06") & co.COUNTYFP.isin(list(COUNTIES))].to_crs(4326)
    counties = [{"name": f"{COUNTIES[r.COUNTYFP]} County" if r.COUNTYFP != "075" else "San Francisco",
                 "geoid": r.GEOID, "rings": rings_of(r.geometry.intersection(POLY.buffer(0.05)), 0.001)}
                for r in co.itertuples()]
    pop, region, region_label = {}, [], "Bay Area"
    p = TABLES / "population_places.csv"
    if p.exists():
        t = pd.read_csv(p)
        t["population"] = pd.to_numeric(t.population, errors="coerce")
        t["year"] = pd.to_numeric(t.year, errors="coerce")
        t = t.dropna(subset=["population", "year"])
        by_name = {pl_["name"]: pl_["geoid"] for pl_ in places}
        for (place, kind), grp in t.groupby(["place", "kind"]):
            series = sorted({float(y): float(v) for y, v in zip(grp.year, grp.population)}.items())
            if kind == "region":
                region, region_label = series, str(place)
            elif kind == "county":
                pop[f"county:{place}"] = series
                if place == "San Francisco":
                    pop["San Francisco"] = series
            else:
                gid = by_name.get(place)
                if "geoid" in grp and grp["geoid"].notna().any():
                    g0 = grp["geoid"].dropna().iloc[0]
                    gid = str(int(float(g0))).zfill(7) if str(g0).replace(".", "").isdigit() else str(g0)
                pop[gid or place] = series
        log(f"cities: populations for {len(pop)} places / counties, region {len(region)} points")
    else:
        log("cities: no data/tables/population_places.csv yet — outlines only")
    out = {"places": places, "counties": counties, "pop": pop, "region": region, "region_label": region_label}
    (VIEWER_DATA / "cities.json").write_text(json.dumps(out, separators=(",", ":")))
    log(f"cities: {len(places)} places, {len(counties)} counties -> cities.json "
        f"({(VIEWER_DATA / 'cities.json').stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
