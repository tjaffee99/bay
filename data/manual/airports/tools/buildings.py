"""Build data/manual/airports/buildings.csv: researched / edition-dated years for today's footprints at
SFO, OAK and SJC (same columns as data/tables/known_building_dates_region.csv + overture_id, confidence).

  python -I tools/buildings.py      (run from data/manual/airports; reads data/raw/overture region5_building,
                                     data/interim region5_footprint_years + region_building_points)

Rows:
  * DOC: documented buildings (terminals, towers, hangars, maintenance bases) matched to their footprint
    by Overture id (name / position checked on the renders);
  * edition rows: footprints with NO roll / assessor year (exempt airport property, so the pipeline's year
    is imputed from neighbours) that the USGS topo editions draw earlier than that imputed year (evidence:
    tools/evidence/footprint_editions_<AP>.csv, made by tools/bpresence.py). start = midpoint of the last
    edition without it and the first with it (a footprint must stay drawn on the later editions: one miss
    allowed); drawn on the first edition after the opening -> FIRST_ED rule below.
lat / lon = a point inside the footprint (representative point), so the point-in-footprint join of
region_buildings.known_dates() picks it up.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow.dataset as ds

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bdate import first_drawn  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[2]
OVT = ROOT / "data/raw/overture/2026-10-21.0"
BBOX = {"SFO": (-122.405, 37.595, -122.35, 37.64), "OAK": (-122.26, 37.69, -122.19, 37.75),
        "SJC": (-121.955, 37.345, -121.905, 37.385)}
EDS = {"SFO": ["1946", "1956", "1968", "1973", "1979", "1993"],
       "OAK": ["1947", "1958", "1968", "1973", "1979", "1993"],
       "SJC": ["1948", "1960", "1968", "1973", "1979"]}
COUNTY = {"SFO": "San Mateo", "OAK": "Alameda", "SJC": "Santa Clara"}
TOPO = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/"
ED_URL = {
    ("SFO", "1946"): TOPO + "CA_Montara%20Mountain_293071_1949_24000_geo.tif",
    ("SFO", "1956"): TOPO + "CA_San%20Francisco%20South_363066_1956_24000_geo.tif",
    ("SFO", "1968"): TOPO + "CA_San%20Francisco%20South_300070_1956_24000_geo.tif",
    ("SFO", "1973"): TOPO + "CA_San%20Francisco%20South_300071_1956_24000_geo.tif",
    ("SFO", "1979"): TOPO + "CA_San%20Francisco%20South_300072_1956_24000_geo.tif",
    ("SFO", "1993"): TOPO + "CA_San%20Francisco%20South_295007_1993_24000_geo.tif",
    ("OAK", "1947"): TOPO + "CA_San%20Leandro_300123_1948_24000_geo.tif",
    ("OAK", "1958"): TOPO + "CA_San%20Leandro_300124_1959_24000_geo.tif",
    ("OAK", "1968"): TOPO + "CA_San%20Leandro_300125_1959_24000_geo.tif",
    ("OAK", "1973"): TOPO + "CA_San%20Leandro_300126_1959_24000_geo.tif",
    ("OAK", "1979"): TOPO + "CA_San%20Leandro_300127_1959_24000_geo.tif",
    ("OAK", "1993"): TOPO + "CA_San%20Leandro_295024_1993_24000_geo.tif",
    ("SJC", "1948"): TOPO + "CA_San%20Jose%20West_300105_1953_24000_geo.tif",
    ("SJC", "1960"): TOPO + "CA_San%20Jose%20West_300106_1961_24000_geo.tif",
    ("SJC", "1968"): TOPO + "CA_San%20Jose%20West_300108_1961_24000_geo.tif",
    ("SJC", "1973"): TOPO + "CA_San%20Jose%20West_300109_1961_24000_geo.tif",
    ("SJC", "1979"): TOPO + "CA_San%20Jose%20West_300110_1961_24000_geo.tif",
}
W_SFO = "https://en.wikipedia.org/wiki/San_Francisco_International_Airport"
W_OAK = "https://en.wikipedia.org/wiki/Oakland_San_Francisco_Bay_Airport"
P_OAK = "https://www.iflyoak.com/business/news-media/media-kit/oak-backgrounder/"
W_SJC = "https://en.wikipedia.org/wiki/San_Jose_Mineta_International_Airport"
T_SJC = "https://www.flysanjose.com/sjc_timeline"
CGAS = "https://www.militarymuseum.org/cgassf.html"
OAKMUS = "https://en.wikipedia.org/wiki/Oakland_Aviation_Museum"

# id prefix -> (key, name, start, end, source, confidence, note)
DOC = {
    "SFO": {
        "1c12ed61": ("sfo_terminal_2", "SFO Terminal 2 (1954 Central Terminal)", 1954, 9999, W_SFO, "documented",
                     "Central Terminal dedicated 27 Aug 1954; rebuilt inside, reopened 14 Apr 2011"),
        "748deda8": ("sfo_terminal_3", "SFO Terminal 3 (North Terminal)", 1979, 9999, W_SFO, "documented",
                     "groundbreaking 22 Apr 1971, opened 1979 (Boarding Area F 1979, E 1981)"),
        "0b96caa2": ("sfo_international", "SFO International Terminal (main hall)", 2000, 9999, W_SFO, "documented",
                     "opened December 2000"),
        "a76f2fb3": ("sfo_intl_boarding_g", "SFO International Terminal Boarding Area G", 2000, 9999, W_SFO,
                     "documented", "opened December 2000"),
        "33a5db7a": ("sfo_intl_boarding_a", "SFO International Terminal Boarding Area A", 2000, 9999, W_SFO,
                     "documented", "opened December 2000"),
        "377b5d4a": ("sfo_bart_station", "SFO BART station", 2003, 9999, W_SFO, "estimated",
                     "BART service to SFO opened 22 Jun 2003 (structure inside the International Terminal "
                     "complex; identification by position)"),
        "ff3cd931": ("sfo_harvey_milk_t1", "SFO Harvey Milk Terminal 1", 2019, 9999, W_SFO, "documented",
                     "rebuilt 2016-24 on the 1963 South Terminal's site: first 9 gates 23 Jul 2019, complete 2024 "
                     "(the old rotundas are in vanished_buildings.geojson)"),
        "3661380e": ("sfo_superbay", "SFO Superbay hangar", 1971, 9999,
                     "https://collection.sfomuseum.org/objects/1511948883", "estimated",
                     "747 maintenance hangar (TWA / American, later United + American): SFO Museum construction "
                     "negatives 1970; not on the 1968-photo sheet, drawn on the 1979 PR"),
        "3d7db9d8": ("sfo_grand_hyatt", "Grand Hyatt at SFO", 2019, 9999,
                     "https://www.hotelmanagement.net/openings/237m-grand-hyatt-opens-at-san-francisco-airport",
                     "documented", "opened 7 Oct 2019 (the 1968-79 editions draw an older building on this site)"),
        "41d47f97": ("sfo_rental_car_center", "SFO Rental Car Center", 2003, 9999, W_SFO, "estimated",
                     "served by the AirTrain, opened 24 Feb 2003; not on the 1993 sheet"),
        "22d75158": ("sfo_cgas_hangar", "Coast Guard Air Station San Francisco hangar", 1941, 9999, CGAS, "documented",
                     "air station commissioned 15 Nov 1940, dedicated 15 Feb 1941 ('one hangar, one nose hangar, "
                     "barracks, an administration building ...'); drawn on the 1943 1:62,500 and 1946-photo sheets"),
        "3c0b5c73": ("sfo_cgas_admin", "Coast Guard Air Station San Francisco administration building", 1941, 9999,
                     CGAS, "documented", "see the hangar; drawn on the 1946-photo sheet"),
        "c7466ba4": ("sfo_cgas_barracks", "Coast Guard Air Station San Francisco barracks (Stonerock Barracks)", 1941,
                     9999, CGAS, "documented", "see the hangar; drawn on the 1946-photo sheet"),
        "6c73fbc9": ("sfo_cgas_garage", "Coast Guard Air Station building (Port Security Unit 312)", 1941, 9999, CGAS,
                     "estimated", "in the air station compound, drawn on the 1946-photo sheet"),
        "4d706cd7": ("sfo_cgas_bldg", "Coast Guard Air Station building", 1941, 9999, CGAS, "estimated",
                     "in the air station compound, drawn on the 1946-photo sheet"),
    },
    "OAK": {
        "88e8e6cc": ("oak_terminal_1", "Oakland Airport Terminal 1", 1962, 9999, P_OAK, "documented",
                     "South Field terminal opened 1962 (John Carl Warnecke)"),
        "44ab4c69": ("oak_terminal_2", "Oakland Airport Terminal 2", 1985, 9999, P_OAK, "documented",
                     "Terminal Two dedicated 1985 (7 gates); the footprint includes the 7-gate concourse extension "
                     "opened Nov 2006 - spring 2007"),
        "1981f954": ("oak_world_air_center", "World Air Center jet maintenance hangar (Oakland)", 1973, 9999, P_OAK,
                     "estimated", "jet maintenance facility for World Airways, federal grant 1966, dedicated 1973 "
                     "('four Boeing 747 or six DC-10'); identification by size / position (largest South Field "
                     "hangar); not on the 1958-photo sheet"),
        "6ab07b34": ("oak_fedex_metroplex", "FedEx Metroplex sort facility (Oakland)", 1988, 9999, P_OAK, "estimated",
                     "'FedEx opens a 13-acre Metroplex regional sort facility west of the passenger terminals' (1988); "
                     "identification by position; drawn on the 1993 sheet, not on the 1979 PR"),
        "161752e1": ("oak_control_tower_2013", "Oakland International Airport control tower", 2013, 9999,
                     "https://simpleflying.com/oakland-international-airport-history/", "documented",
                     "236-ft tower, construction from Oct 2010, opened 22 Nov 2013, replacing the two older towers"),
        "a3cebd2f": ("oak_boeing_school_hangar", "Boeing School of Aeronautics hangar (Building 621, Oakland "
                     "Aviation Museum)", 1940, 9999, OAKMUS, "estimated",
                     "Boeing School hangar built 1939-40 (sources give 1939 and 1940); drawn on the 1947 sheet, not on "
                     "the 1939-photo 1:62,500 sheet"),
    },
    "SJC": {
        "a27f729d": ("sjc_terminal_a", "San Jose Airport Terminal A", 1990, 9999, T_SJC, "documented",
                     "construction from 1987, opened 1990; expanded / remodelled 2009-10"),
        "8047987e": ("sjc_terminal_b", "San Jose Airport Terminal B", 2010, 9999, T_SJC, "documented",
                     "opened 30 Jun 2010 with the North Concourse"),
        "f536a8c1": ("sjc_rental_car_garage", "San Jose Airport consolidated rental car garage", 2010, 9999, T_SJC,
                     "documented", "consolidated rental car center opened 2010 (Terminal Area Improvement Program, "
                     "completed June 2010)"),
        "2abfc99d": ("sjc_arff_station_20", "San Jose Airport ARFF station (Fire Station 20)", 2022, 9999, T_SJC,
                     "estimated", "'2022: Fire Station 20, an Aircraft Rescue and Fire Fighting station, opens on "
                     "Coleman Avenue'; identification by name / position"),
    },
}
# North Field (OAK): footprints drawn on the Hayward 1:62,500 (1939 photos) are the 1927-29 airport
NORTH_FIELD_1939 = (1928, "the 1927-29 airport ('five hangars, an administration building, and a hotel, built "
                          "between 1927 and 1929', Oakland Heritage Alliance; 'by Summer 1929 ... five hangars, "
                          "passenger terminal/administrative offices', Port of Oakland): drawn on the Hayward "
                          "1:62,500 (1939 photos)",
                    "https://www.oaklandheritage.org/events/walking-tour-amelias-airport-oaklands-historic-north-field")
# areas rebuilt after the last edition (edition presence there is an older building): no edition rows
REBUILT = {"SJC": [(-121.929, -121.920, 37.348, 37.3545)]}  # SE GA / SJSU area: 2020 Master Plan G-1, G-5, G-6
FIRST_ED = {  # footprint drawn on the earliest edition: start year used (the edition only bounds it above)
    "SFO": (1944, "drawn on the 1946-photo sheet: built 1927-46 (most of the field dates from the wartime "
                  "expansion 1942-46) - 1944 estimated"),
    "OAK": (1943, "drawn on the 1947 sheet, not on the 1939-photo 1:62,500: built 1939-47 (Army 1942 / NAS "
                  "Oakland 1944-46) - 1943 estimated"),
    "SJC": (1947, "drawn on the 1953 sheets (1948 photos): 1945-48 airport (Nissen's flight school 1945, first "
                  "permanent runway 1948) - 1947 estimated"),
}


def footprints(ap):
    x0, y0, x1, y1 = BBOX[ap]
    d = ds.dataset(str(OVT / "region5_building.parquet"))
    t = d.to_table(columns=["id", "name", "px", "py", "geometry"],
                   filter=(ds.field("px") > x0) & (ds.field("px") < x1) & (ds.field("py") > y0) & (ds.field("py") < y1)
                   ).to_pandas()
    return gpd.GeoDataFrame(t, geometry=gpd.GeoSeries.from_wkb(t.geometry), crs=4326)


def main():
    yrs = pd.read_parquet(ROOT / "data/interim/region5_footprint_years.parquet",
                          columns=["id", "year_public", "year_third_party", "year_commercial", "year_historic"])
    pts = pd.read_parquet(ROOT / "data/interim/region_building_points.parquet")
    from scipy.spatial import cKDTree
    rows = []
    for ap in ("SFO", "OAK", "SJC"):
        fp = footprints(ap).merge(yrs, on="id", how="left").set_index("id", drop=False)
        x0, y0, x1, y1 = BBOX[ap]
        p = pts[(pts.lon > x0) & (pts.lon < x1) & (pts.lat > y0) & (pts.lat < y1)]
        rp = fp.geometry.representative_point()
        dd, ii = cKDTree(p[["lon", "lat"]].values).query(np.c_[rp.x, rp.y])
        fp["start_now"] = np.where(dd < 2e-5, p.start_year.values[ii], np.nan)
        fp["lon"], fp["lat"] = rp.x.round(6), rp.y.round(6)
        has_roll = fp[["year_public", "year_third_party", "year_commercial", "year_historic"]].notna().any(axis=1)
        ev = pd.read_csv(HERE / f"tools/evidence/footprint_editions_{ap}.csv", dtype=str, keep_default_na=False).set_index("id")
        ev39 = (pd.read_csv(HERE / "tools/evidence/footprint_editions_OAK_1939.csv", dtype=str, keep_default_na=False)
                .set_index("id") if ap == "OAK" else None)
        done = set()
        for pre, (key, name, s, e, url, conf, note) in DOC[ap].items():
            m = fp[fp.id.str.startswith(pre)]
            if len(m) != 1:
                print("!! no unique footprint for", ap, pre, len(m)); continue
            r = m.iloc[0]
            done.add(r.id)
            rows.append(dict(id=key, name=name, lat=r.lat, lon=r.lon, start_year=s, end_year=e, source_url=url,
                             note=f"{note}. Pipeline year before: {r.start_now:.0f}" if np.isfinite(r.start_now) else note,
                             county=COUNTY[ap], overture_id=r.id, confidence=conf))
        n_ed = 0
        for fid, r in fp.iterrows():
            if fid in done or fid not in ev.index or has_roll[fid] or not np.isfinite(r.start_now):
                continue
            area = float(ev.loc[fid, "area_m2"])
            if area < 150:
                continue
            f, prev, last = first_drawn(ev.loc[fid], EDS[ap])
            if f is None:
                continue
            if any(a <= r.lon <= b and c <= r.lat <= d for a, b, c, d in REBUILT.get(ap, [])):
                continue  # area redeveloped after the last edition: an older building stood there
            nm = r["name"] if isinstance(r["name"], str) else "airport building"
            if prev is None:
                if ap == "OAK" and ev39 is not None and fid in ev39.index and ev39.loc[fid, "1939"].startswith("P") \
                        and -122.2125 < r.lon < -122.2045 and 37.726 < r.lat < 37.7315:
                    s, why, url = NORTH_FIELD_1939
                    conf = "estimated"
                else:
                    s, why = FIRST_ED[ap]
                    if ap == "OAK" and -122.2125 < r.lon < -122.2045 and 37.726 < r.lat < 37.7315:
                        why += ("; stands in the 1927-29 North Field building row but its symbol is not resolved on "
                                "the 1:62,500 sheet - may be one of the 1927-29 buildings")
                    url = ED_URL[(ap, f)]
                    conf = "estimated"
                if r.start_now <= int(f) + 2:
                    continue  # the imputed year already fits the edition
            else:
                s = (int(prev) + int(f)) / 2
                if r.start_now <= int(f) + 2:
                    continue  # only positive evidence (drawn earlier than the imputed year) overrides
                why = f"absent on the {prev} edition, drawn from the {f} edition on (midpoint)"
                url = ED_URL[(ap, f)]
                conf = "estimated"
            n_ed += 1
            rows.append(dict(id=f"{ap.lower()}_ed_{fid[:8]}", name=f"{nm} ({ap})", lat=r.lat, lon=r.lon,
                             start_year=round(float(s), 1), end_year=9999, source_url=url,
                             note=f"USGS topo editions: {why}; no roll year (exempt airport property), pipeline's "
                                  f"imputed year was {r.start_now:.0f}. Footprint {area:.0f} m2",
                             county=COUNTY[ap], overture_id=fid, confidence=conf))
        print(ap, len(done), "documented,", n_ed, "edition-dated")
    cols = ["id", "name", "lat", "lon", "start_year", "end_year", "source_url", "note", "county", "overture_id", "confidence"]
    with open(HERE / "buildings.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "rows")


if __name__ == "__main__":
    main()
