"""Cities, towns and counties for the population counter.

Outlines: US Census TIGER/Line 2024 places (incorporated cities / towns and census-
designated places) and counties inside the map's extent, simplified to ~40 m.
Populations: data/tables/population_places.csv (decennial censuses + the latest DOF
estimate per place and county; see data/research/population_places.md). The regional
total is the sum of the mapped counties (COUNTIES) for every year all of them have a row
(1850: the eight counties that existed), labelled "Bay Area (N counties)".

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
import shapely

from common import RAW, TABLES, VIEWER_DATA, log
from extent import POLY, in_extent

# the mapped counties (ten since the 2026-11 extension: + Napa, Santa Cruz, Solano, Sonoma)
COUNTIES = {"001": "Alameda", "013": "Contra Costa", "041": "Marin", "055": "Napa", "075": "San Francisco",
            "081": "San Mateo", "085": "Santa Clara", "087": "Santa Cruz", "095": "Solano", "097": "Sonoma"}
# formed after the 1850 census out of counties that are in the list (their people are counted there)
FORMED_LATER = {"Alameda": 1853, "San Mateo": 1856}


def rings_of(geom, tol=0.0004):
    g = geom.simplify(tol, preserve_topology=True)
    out = []
    for p in getattr(g, "geoms", [g]):
        if p.geom_type != "Polygon" or p.is_empty:
            continue
        out.append([[round(x, 5), round(y, 5)] for x, y in np.asarray(p.exterior.coords)[:, :2]])
    return out


def main():
    co = gpd.read_file(f"zip://{RAW / 'tiger' / 'tl_2024_us_county.zip'}")
    co = co[(co.STATEFP == "06") & co.COUNTYFP.isin(list(COUNTIES))].to_crs(4326)
    pl = gpd.read_file(f"zip://{RAW / 'tiger' / 'tl_2024_06_place.zip'}").to_crs(4326)
    # places of the mapped counties only (the extent's margin also reaches into Yolo, San
    # Joaquin, Monterey ... whose places have no series), and inside the map
    rp = pl.geometry.representative_point()
    mapped = shapely.union_all(list(co.geometry))
    shapely.prepare(mapped)
    pl = pl[shapely.contains(mapped, rp.values) & in_extent(rp, margin=0.0)]
    places = [{"name": r.NAME, "geoid": r.GEOID, "kind": "cdp" if str(r.CLASSFP).startswith("U") else "city",
               "rings": rings_of(r.geometry)} for r in pl.itertuples()]
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
                region, region_label = series, str(place)   # fallback; replaced by the county sum below
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
        # regional total = sum of the mapped counties, for the years every county has a row
        # (a county not yet formed is inside its parent, which is in the list)
        cs = {n: dict(pop.get(f"county:{n}", [])) for n in COUNTIES.values()}
        if all(cs.values()):
            summed = []
            for y in sorted(set().union(*cs.values())):
                need = [n for n in cs if FORMED_LATER.get(n, 0) <= y]
                if all(y in cs[n] for n in need):
                    summed.append((y, float(sum(cs[n][y] for n in need))))
            listed = dict(region)
            for y, v in summed:
                if y in listed and abs(listed[y] - v) > 0.5:
                    log(f"cities: region row {y:.0f} = {listed[y]:.0f} in the table, county sum {v:.0f} (sum used)")
            region, region_label = summed, f"Bay Area ({len(COUNTIES)} counties)"
        log(f"cities: populations for {len(pop)} places / counties, region {len(region)} points ({region_label})")
    else:
        log("cities: no data/tables/population_places.csv yet — outlines only")
    out = {"places": places, "counties": counties, "pop": pop, "region": region, "region_label": region_label}
    (VIEWER_DATA / "cities.json").write_text(json.dumps(out, separators=(",", ":")))
    log(f"cities: {len(places)} places, {len(counties)} counties -> cities.json "
        f"({(VIEWER_DATA / 'cities.json').stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
