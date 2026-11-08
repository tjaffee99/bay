"""Road segments on the second batch of vanished sites -> rows of ../road_segments.csv (rows of these
site_ids are replaced, all other rows kept). Run from the vanished_sites folder:

    python -I tools/roadseg2.py

Rule per site: Overture segments (roads_local + roads_region) with >= 15 m on a site part that ended
are either `keep` (a street the site's maps already show: boundary streets, named in KEEP) or `date`
(not before the researched year in NOT_BEFORE, with the evidence)."""
import csv
import json
import sys
from pathlib import Path

import shapely
from shapely.geometry import shape

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from roads_in import roads_in  # noqa: E402

OUT = HERE.parent
SITES = {  # site_id: (not_before, evidence for dated segments, keep-names, evidence for kept segments, part filter)
    "idora_park": (1930, "street cut through Idora Park for the Idora Park tract after the park was razed in 1929 (57th St, "
                         "Aileen St, Carberry Ave: not on the 1911 Sanborn sheet 293; the Oct 1931 'new sheet' 293 shows them built up)",
                   ("56th Street", "58th Street", "Telegraph Avenue", "Shattuck Avenue"),
                   "boundary street of the park, drawn on the 1911 Sanborn sheet 293", None),
    "neptune_beach": (1941, "lies on Neptune Beach (1916-1940): McKay Ave was laid on the roller coaster's footprint after the "
                            "1940 demolition (Alameda Post); it and the station roads are on the USGS 1949 sheet (1946 photos)",
                      ("Central Avenue",), "Central Ave, the resort's frontage (1897 / 1948 Sanborn)", None),
    "neptune_gardens": (1941, "lies on the Neptune Gardens / Neptune Beach grounds (1880-1940); Webster St ended at Central Ave on "
                              "the 1897 Sanborn", ("Central Avenue",), "Central Ave (1897 Sanborn)", None),
    "terrace_baths": (1941, "lies on the Terrace Baths site (1878-1916) and then Neptune Beach / Neptune Court", ("Central Avenue",),
                      "Central Ave (1897 Sanborn)", None),
}


def main():
    fc = json.load(open(OUT / "sites.geojson"))["features"]
    rows = []
    for sid, (nb, ev, keep, kev, filt) in SITES.items():
        gs = [shape(f["geometry"]) for f in fc if f["properties"]["site_id"] == sid and f["properties"]["year_end"] < 9999
              and (filt is None or filt(f["properties"]))]
        if not gs:
            continue
        poly = shapely.union_all(gs).buffer(0)
        r = roads_in(poly)
        if r is None:
            continue
        r = r[r.inside_m >= 15]
        for x in r.itertuples():
            name = x.name if isinstance(x.name, str) else ""
            cls = x._2
            if cls in ("motorway", "trunk", "motorway_link", "trunk_link"):
                continue
            if name in keep:
                rows.append(dict(segment_id=x.id, file=x.file, cls=cls, name=name, site_id=sid, inside_m=int(x.inside_m),
                                 on_last_sheet="", action="keep", not_before="", evidence=kev))
            else:
                rows.append(dict(segment_id=x.id, file=x.file, cls=cls, name=name, site_id=sid, inside_m=int(x.inside_m),
                                 on_last_sheet="", action="date", not_before=nb, evidence=ev))
    # a segment on two sites: keep the latest not-before
    best = {}
    for row in rows:
        k = row["segment_id"]
        if k not in best or (row["action"] == "date" and (best[k]["action"] == "keep" or row["not_before"] > best[k]["not_before"])):
            best[k] = row
    rows = list(best.values())
    p = OUT / "road_segments.csv"
    old = list(csv.DictReader(open(p)))
    fields = list(old[0].keys())
    seen = {r["segment_id"] for r in old if r["site_id"] not in SITES}
    old = [r for r in old if r["site_id"] not in SITES]
    new = [r for r in rows if r["segment_id"] not in seen]
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(old)
        w.writerows(new)
    import collections
    print(len(old), "kept rows +", len(new), "new:", collections.Counter((r["site_id"], r["action"]) for r in new))


if __name__ == "__main__":
    main()
