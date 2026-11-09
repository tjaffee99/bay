"""Build the dated airport history files for SFO, OAK and SJC (data/manual/airports/).

  python -I tools/build.py            (run from data/manual/airports; ~10 s, < 300 MB)

Inputs: Overture 2026-10-21.0 airport features (data/raw/overture/2026-10-21.0/region_airports.parquet,
OSM runways / taxiways / aprons) and the definitions below, which were read off the USGS topo
editions rendered with tools/render.py (see README.md: method, editions, sources).
Outputs:
  pavement_dates.csv      one row per OSM runway / stopway / taxiway / taxilane / apron (runway pieces
                          that span several construction phases: one row per phase, as an interval
                          along the runway axis with its end points)
  pavement_zones.geojson  the dated zones (polygons) and runway phases (axis intervals buffered to
                          the runway width) behind those rows - for QGIS checks or polygon clipping
  vanished_pavement.geojson  runways that existed and are gone from today's map
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import LineString, Polygon, mapping, Point

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[2]
OVT = ROOT / "data/raw/overture/2026-10-21.0/region_airports.parquet"

# ----------------------------------------------------------------------------------------- sources
SRC = {
    "sfo_wiki": "https://en.wikipedia.org/wiki/San_Francisco_International_Airport",
    "sfo_museum": "https://www.sfomuseum.org/exhibitions/mills-field-and-san-francisco-airport",
    "sfo_simpleflying": "https://simpleflying.com/san-francisco-airport-runways-terminals-opening-dates/",
    "sfo_cgas": "https://www.militarymuseum.org/cgassf.html",
    "oak_backgrounder": "https://www.iflyoak.com/business/news-media/media-kit/oak-backgrounder/",
    "oak_wiki": "https://en.wikipedia.org/wiki/Oakland_San_Francisco_Bay_Airport",
    "oak_nas": "https://www.militarymuseum.org/NASOakland.html",
    "sjc_wiki": "https://en.wikipedia.org/wiki/San_Jose_Mineta_International_Airport",
    "sjc_timeline": "https://www.flysanjose.com/sjc_timeline",
    "sjc_mp2020": "https://www.flysanjose.com/sites/default/files/rsheelen/MP-ExecSum2020.pdf",
    "usgs_topo": "https://www.usgs.gov/programs/national-geospatial-program/historical-topographic-maps-preserving-past",
}
TOPO = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/"
ED = {  # the editions the readings come from (first sheet named = the one covering most of the field)
    "SFO": "USGS 1:24k San Mateo / Montara Mountain / San Francisco South / Hunters Point: 1946 photos "
           "(1947-50 eds.), 1956, 1968 PR, 1973 PR, 1979-80 PR, 1993",
    "OAK": "USGS 1:24k San Leandro: 1947 (1948 ed.), 1958 photos (1959 ed.), 1968 PR, 1973 PR, 1979 PR, 1993; "
           "Hayward 1:62,500 1942 (1939 photos)",
    "SJC": "USGS 1:24k San Jose West + Milpitas: 1948 photos (1953 eds.), 1960 photos (1961 eds.), 1968 PR, "
           "1973 PR, 1979 PR",
}

# ----------------------------------------------------------------------------------------- frames
FRAME = {"SFO": (-122.377, 37.617), "OAK": (-122.222, 37.722), "SJC": (-121.930, 37.363)}
NAME = {"SFO": "San Francisco International Airport", "OAK": "Oakland International Airport",
        "SJC": "San José Mineta International Airport"}


def kfac(cy):
    return 111320 * math.cos(math.radians(cy))


def loc2ll(ap, x, y):
    cx, cy = FRAME[ap]
    return cx + np.asarray(x) / kfac(cy), cy + np.asarray(y) / 110574


def ll2loc(ap, lon, lat):
    cx, cy = FRAME[ap]
    return (np.asarray(lon) - cx) * kfac(cy), (np.asarray(lat) - cy) * 110574


# ----------------------------------------------------------------------------------------- runways
# Each runway: its Overture pieces (runway + stopway lines), the axis end the distances count from
# ("a", the W / S / SE end of the full paved length incl. stopways / blast pads), width (m), and the
# construction phases as intervals [d0, d1] along the axis (m from end a).
# Interval ends were read on the topo editions with tools/rwyticks.py (distance ticks every 100 m
# along today's axis; precision about +-75 m) and checked against the documented lengths.
RUNWAYS = {
    "SFO": {
        "10L/28R": dict(ids=["c161b8e8-f8f6-3719-b220-20227ff1c202", "c43be67d-3fe1-3ff5-9969-f311063d3c6d",
                             "1cf96308-5113-32ed-be4b-bcd8731cf6c8", "081cb7ea-b670-33fb-b2b8-0096d7a09cab"],
                        end_a="10L (west)", width=61, parts=[
            (350, 3050, 1944, "estimated", "sfo_cgas",
             "core: drawn on the 1946-photo sheets from just east of the old Bayshore Highway to the 1946 seawall; "
             "built on wartime hydraulic fill (Army lease 5 Feb 1942: 'three hard-surfaced runways built, the "
             "longest 8,000 ft', USACE 1991 via militarymuseum.org); Aug 1952 chart 28R 8,870 ft. Year = middle of "
             "1942-46. May incorporate the 1930s Runway C (1,900 ft -> 3,000 ft in 1935) at its west end"),
            (0, 350, 1962, "estimated", "usgs_topo",
             "west end / blast pad over the former Bayshore Highway (crossed this axis at d~50 until the freeway "
             "bypass); not on the 1956 sheet, purple on the 1968 photorevision -> midpoint 1962"),
            (3050, 3974, 1969, "estimated", "sfo_simpleflying",
             "east extension onto new fill: 'Runway 28 Right was extended in 1968'; still mud with the approach-"
             "light pier on the 1968 photos, paved on the 1973 photorevision -> 1969"),
        ]),
        "10R/28L": dict(ids=["b7e52bc0-8aac-3cf1-b15f-abb942331005", "11362bb7-d24c-355b-9d38-17988ea747ca",
                             "2d93cd5f-a16b-3430-9805-b5f3e6100651", "cc861d8d-c8ae-32bd-b98c-978e6e4e8087"],
                        end_a="10R (west)", width=61, parts=[
            (900, 2950, 1944, "estimated", "sfo_cgas",
             "core on the 1946-photo sheets (west end ~d 780-900 behind the 1940s hangar row, east end at the 1946 "
             "seawall); Aug 1952 chart 28L 6,500 ft; wartime fill, year = middle of 1942-46"),
            (0, 900, 1961, "documented", "sfo_simpleflying",
             "'Runway 28 Left was lengthened ... in 1961'; west part across the old hangar row (buildings on the axis "
             "on the 1956 sheet, pavement on the 1968 photorevision)"),
            (2950, 3786, 1961, "documented", "sfo_simpleflying",
             "1961 lengthening of 28L: east part on new fill (bay on the 1956 sheet, paved on the 1968 photorevision)"),
        ]),
        "1L/19R": dict(ids=["eae9fcf7-8da2-3775-961f-4f8e5e8650d7", "90877d9f-34cc-394b-99fd-291e79a010ab",
                            "b47d4d17-2783-322d-a078-f43f7aac7723", "f5f9c9cd-42f4-3bc5-92e2-582632e6db8f"],
                       end_a="1L (south)", width=61, parts=[
            (420, 2602, 1944, "estimated", "sfo_wiki",
             "core: south end east of the old Bayshore Highway on the 1946-photo sheet (north end beyond that sheet, "
             "at d~2600 on the 1956 sheet); Aug 1952 chart 1L 7,000 ft; wartime fill, year = middle of 1942-46"),
            (200, 420, 1953, "estimated", "usgs_topo",
             "south extension after the Aug 1952 chart, across the old highway alignment (south end at d~200 on "
             "the 1956 sheet)"),
            (0, 200, 1962, "estimated", "usgs_topo", "south end / blast pad: 1956 -> 1968 editions, midpoint"),
        ]),
        "1R/19L": dict(ids=["99601710-f1bc-3430-b1c1-b5a4c180c847", "7ad1780b-1348-37c1-93b8-c10d6c54dbb5",
                            "74777df0-f0f5-3cfb-81bb-4216c987deac", "f34d9575-4881-3dbe-8ee7-6ce38ee105e8"],
                       end_a="1R (south)", width=61, parts=[
            (330, 2480, 1944, "estimated", "sfo_wiki",
             "core (south end east of the old highway on the 1946 sheet, north end d~2480 on the 1956 sheet); "
             "Aug 1952 chart 1R 7,750 ft; wartime fill, year = middle of 1942-46"),
            (200, 330, 1953, "estimated", "usgs_topo", "south extension, after the 1952 chart, on the 1956 sheet"),
            (0, 200, 1962, "estimated", "usgs_topo", "south end / blast pad: 1956 -> 1968 editions, midpoint"),
            (2480, 2887, 1962, "estimated", "usgs_topo",
             "north extension onto the NE fill with its approach-light pier: absent 1956, purple on the 1968 PR"),
        ]),
    },
    "OAK": {
        "10L/28R (North Field)": dict(ids=["15236529-9d07-3a9c-ad9c-ffd6bc24e2ec", "ff6e10f7-e960-3a0e-a16f-01043a6f79f9",
                                           "4ad21548-2301-3dd6-a05d-8cfa5d0d7da6"],
                                      end_a="10L (west)", width=45, parts=[
            (0, 1864, 1927, "estimated", "oak_backgrounder",
             "the original runway: built June 1927 in 21-23 days ('a 7,020-foot runway, the longest in the world'), "
             "dedicated 17 Sep 1927. Identified as today's 10L/28R because the 1945 6,200-ft runway 'parallels the "
             "original runway' (Port of Oakland); today 5,458 ft (the 1927 strip was longer). On every edition from "
             "the 1947 sheet on"),
        ]),
        "10R/28L (North Field)": dict(ids=["79b41b83-dcab-3c01-ab12-7853cbce4820", "c2cb9b93-950e-38dd-b05f-7e54025912d7",
                                           "ebf0c731-37ff-33ab-a921-e10bc14719c7"],
                                      end_a="10R (west)", width=45, parts=[
            (0, 2252, 1945, "documented", "oak_backgrounder",
             "'1945: A new 6,200-foot east-west runway paralleling the original runway is constructed' (6,213 ft today); "
             "on the 1947 sheet"),
        ]),
        "15/33 (North Field)": dict(ids=["61c0d432-7949-32cb-987a-7ad7b138dc75"], end_a="15 (north)", width=30, parts=[
            (0, 1026, 1944, "estimated", "oak_nas",
             "wartime runway of NAS Oakland (Navy lease 1 Feb 1944, 'repair and repavement of runways and taxiways', "
             "expansion from April 1944; 'four asphalt runways, the longest 6,500 ft'); on the 1947 sheet"),
        ]),
        "12/30 (South Field)": dict(ids=["ef92d67a-61e4-3d31-975b-b85d9a290430", "62fd95eb-3ab1-390e-8917-aaf2bd775ebe",
                                         "a3ab0de3-cfe6-3f88-a58a-b81e8661c99a"],
                                    end_a="12 (northwest)", width=45, parts=[
            (0, 3441, 1962, "documented", "oak_backgrounder",
             "South Field jet runway 'behind a 4.5-mile dike', begun 1960, opened with the new terminal 1962 "
             "(10,000 ft, then 11/29; renumbered 12/30 in 2013; 10,520 ft today - the later lengthening is not "
             "dated here). Bay water on the 1958-photo sheet, runway on the 1968 PR"),
        ]),
    },
    "SJC": {
        "12R/30L": dict(ids=["c3ea3cce-fb36-312a-9886-3eeb625106c2", "d3e07cab-cb14-3178-98ef-fdad0db94d76",
                             "6c86f082-0b88-34e3-8f36-75cc2bb17a5a", "eb1aa941-4f60-3ce4-920a-ce6f050a96dd"],
                        end_a="12R (southeast)", width=45, parts=[
            (350, 1550, 1948, "documented", "sjc_timeline",
             "'1948: the first permanent runway was built with a federal airport grant' (a dirt strip from 1945, "
             "Nissen's flight school); 4,500 ft until ~1962 (Wikipedia); drawn on the 1948-photo sheet from d~350 "
             "to d~1550 (registration of that sheet +-30 m)"),
            (200, 350, 1961, "documented", "sjc_timeline",
             "'1961: the west runway was extended by 2,500 feet' - drawn on the 1960-photo sheet (SE end d~200)"),
            (1550, 2350, 1961, "documented", "sjc_timeline", "1961 extension, NW part (to d~2350 on the 1960-photo sheet)"),
            (130, 200, 1966, "estimated", "sjc_wiki",
             "lengthened to 7,787 ft (1965) and 8,900 ft (late 1960s, Wikipedia); SE end at d~130 on the 1968 PR"),
            (2350, 2840, 1966, "estimated", "sjc_wiki",
             "1964-68 lengthenings (6,312 ft 1964, 7,787 ft 1965, 8,900 ft late 1960s); NW end at d~2840 on the "
             "1968-1979 photorevisions"),
            (2840, 3240, 1993, "estimated", "sjc_mp2020",
             "8,900 ft until ~1991 (Wikipedia), 10,200 ft in 1996 (2020 Master Plan table) -> lengthened NW toward "
             "Kifer Rd c.1991-96"),
            (0, 130, 2004, "documented", "sjc_mp2020", "'Runway 12R-30L reconstructed and extended [to 11,000 ft]: October 2004'"),
            (3240, 3412, 2004, "documented", "sjc_mp2020", "October 2004 extension to 11,000 ft (NW end)"),
        ]),
        "12L/30R": dict(ids=["610674ef-d18b-3494-8abc-e2ad1ded1de0", "42854837-1d2b-3a9c-9089-ec7d6c8228ac",
                             "5241aaf9-a63f-305c-95c2-d924321d87e1", "bdb635dd-099e-3895-8a33-ea95d9a073d1",
                             "68f5d205-4bbc-3733-b145-45975ac05e29"],
                        end_a="12L (southeast)", width=45, parts=[
            (450, 1790, 1961, "documented", "sjc_timeline",
             "'1961: ... a new 4,400-foot east runway was added' (4,400 ft still in 1996, 2020 Master Plan); on the "
             "1968-1979 PRs its SE end is clear of the T-hangar rows that stood on today's axis d 0-300"),
            (0, 450, 2001, "documented", "sjc_mp2020",
             "'Runway 12L-30R reconstructed and extended [to 11,000 ft]: August 2001' (over the removed SE T-hangars "
             "and south-end GA area)"),
            (1790, 3435, 2001, "documented", "sjc_mp2020", "August 2001 extension to 11,000 ft (NW part)"),
        ]),
    },
}

# ----------------------------------------------------------------------------------------- zones
# Areas of taxiway / apron construction, polygons in the airport frame (local metres, x east, y north),
# read off the editions (tools/gridview.py, tools/zcheck.py). A feature takes the LAST zone in the list
# holding >= 50 % of it (later zones are re-builds / additions inside older ones).
def band(ap, rw, d0, d1, t0, t1):
    """Polygon of axis distances d0..d1 (from end a) and lateral offsets t0..t1 (+ = right of a->b)."""
    a, b = RW_AXIS[ap][rw]
    u = (b - a) / np.linalg.norm(b - a)
    n = np.array([u[1], -u[0]])
    pts = [a + d * u + t * n for d, t in ((d0, t0), (d1, t0), (d1, t1), (d0, t1))]
    return [tuple(map(float, p)) for p in pts]


def zones():
    return {
        "SFO": [
            dict(id="SFO-1946", start=1944, conf="estimated", src="sfo_cgas",
                 xy=[[-1500, 1420], [-1500, 1750], [-900, 1750], [-600, 1560], [-300, 1300], [330, 1150], [700, 1100],
                     [1000, 880], [1160, 620], [1160, -20], [900, -180], [500, -470], [150, -760], [0, -960],
                     [-250, -1080], [-470, -860], [-700, -560], [-950, -200], [-1150, 250], [-1330, 800]],
                 ev="airfield on the 1946-photo sheets (taxiway grid between the four runways, 1930s field in the NW); "
                    "wartime hydraulic fill and runways 1942-46"),
            dict(id="SFO-westfield", start=1962, conf="estimated", src="usgs_topo",
                 xy=[[-2300, 1250], [-1500, 1420], [-1330, 800], [-1150, 250], [-950, -200], [-1250, -800], [-2300, -800]],
                 ev="West Field (cargo, airline and service area west of the 1946 field, along the freeway): "
                    "developed between the 1956 and 1968 editions (low confidence for individual taxilanes)"),
            dict(id="SFO-south-ends", start=1962, conf="estimated", src="usgs_topo",
                 xy=[[-950, -650], [-470, -860], [-560, -1120], [-300, -1300], [-60, -1180], [100, -1450],
                     [-450, -1550], [-1000, -1200]],
                 ev="south end blast pads / taxiways of the 1/19 runways: 1956 -> 1968 editions"),
            dict(id="SFO-CGAS", start=1941, conf="documented", src="sfo_cgas",
                 xy=[[-1750, 1650], [-850, 1650], [-850, 2050], [-1750, 2050]],
                 ev="Coast Guard Air Station San Francisco (commissioned 15 Nov 1940, dedicated 15 Feb 1941), on the "
                    "1946-photo sheet"),
            dict(id="SFO-NE-fill", start=1951, conf="estimated", src="usgs_topo",
                 xy=[[330, 1150], [300, 1520], [1150, 1520], [1200, 1250], [1000, 880], [700, 1100]],
                 ev="NE fill north of the 1946 airfield, paved on the 1956 sheet (Hunters Point quad not mapped "
                    "1946) -> midpoint 1951"),
            dict(id="SFO-south", start=1953, conf="estimated", src="usgs_topo",
                 xy=[[-470, -860], [-250, -1080], [0, -960], [-60, -1180], [-300, -1300], [-560, -1120]],
                 ev="south ends of the 1/19 runways beyond the old Bayshore Highway: after the Aug 1952 chart, on "
                    "the 1956 sheet"),
            dict(id="SFO-NW-ends", start=1962, conf="estimated", src="usgs_topo",
                 xy=[[-1500, 1420], [-1330, 800], [-1520, 800], [-1800, 1150], [-1750, 1500]],
                 ev="west ends of 10L/10R across the old hangar row / highway: 1956 -> 1968 editions"),
            dict(id="SFO-28L-ext", start=1961, conf="documented", src="sfo_simpleflying",
                 xy=[[900, -180], [1160, -60], [1980, -520], [1950, -700], [1500, -900], [1000, -700], [500, -470]],
                 ev="fill and taxiways south of the 28L extension: bay on the 1956 sheet, paved on the 1968 PR; "
                    "28L lengthened 1961"),
            dict(id="SFO-28R-ext", start=1969, conf="estimated", src="sfo_simpleflying",
                 xy=[[1160, 640], [1160, -60], [1980, -520], [2150, -470], [2100, -330], [1250, 640]],
                 ev="fill and taxiways north of 28R east of the 1956 seawall: mud on the 1968 photos, paved on the "
                    "1973 PR; 28R extended 1968"),
        ],
        "OAK": [
            dict(id="OAK-NorthField", start=1944, conf="estimated", src="oak_nas",
                 xy=[[-900, 900], [-650, 2300], [700, 2300], [1900, 600], [1700, -50], [-700, 450]],
                 ev="North Field taxiways on the 1947 sheet: the wartime Navy field (lease 1 Feb 1944, 'repair and "
                    "repavement of runways and taxiways', expansion from April 1944)"),
            dict(id="OAK-SouthField", start=1962, conf="documented", src="oak_backgrounder",
                 xy=[[-2100, -100], [-1500, 300], [600, 250], [1700, -50], [1500, -900], [1100, -1900],
                     [900, -2500], [-300, -2500]],
                 ev="South Field (runway, terminal, cargo apron, jet hangar) on the 1960-62 dike fill, opened 1962; "
                    "bay on the 1958-photo sheet, airfield on the 1968 PR"),
        ],
        "SJC": [
            dict(id="SJC-1961", start=1961, conf="documented", src="sjc_timeline",
                 xy=band("SJC", "12R/30L", 150, 2400, -160, 460),
                 ev="taxiways of the 1961 runway program (12R extension + new east runway): on the 1960-photo sheet "
                    "or the 1968 PR within the 1961 runway lengths"),
            dict(id="SJC-westside", start=1965, conf="estimated", src="usgs_topo",
                 xy=band("SJC", "12R/30L", 150, 2900, -760, -160),
                 ev="west-side GA taxiways and aprons: the west-side hangars carry 1965-66 roll years; on the 1968 PR"),
            dict(id="SJC-1966", start=1966, conf="estimated", src="sjc_wiki",
                 xy=band("SJC", "12R/30L", 2400, 2900, -160, 460),
                 ev="NW taxiways of the 1964-68 lengthenings (8,900 ft)"),
            dict(id="SJC-1993", start=1993, conf="estimated", src="sjc_mp2020",
                 xy=band("SJC", "12R/30L", 2900, 3260, -220, 140),
                 ev="NW end with the 10,200-ft 12R (c.1991-96)"),
            dict(id="SJC-NW-GA", start=2013, conf="estimated", src="sjc_timeline",
                 xy=[[-380, 850], [-100, 850], [-100, 1250], [-380, 1250]],
                 ev="north-west general-aviation area (Signature FBO; 2020 Master Plan G-8): open land on the 1979 PR; "
                    "'2011: the west-side long-term lot closed to prepare for general aviation redevelopment'"),
            dict(id="SJC-2001-SE", start=2001, conf="documented", src="sjc_mp2020",
                 xy=band("SJC", "12R/30L", -150, 450, 120, 520),
                 ev="12L extension and new cross Taxiway A at the south end (Aug 2001), over removed T-hangars"),
            dict(id="SJC-2001-NW", start=2001, conf="documented", src="sjc_mp2020",
                 xy=band("SJC", "12R/30L", 1800, 3550, 150, 420),
                 ev="12L extension NW part, extended parallel Taxiway Y and new cross Taxiway N (Aug 2001)"),
            dict(id="SJC-2004-NW", start=2004, conf="documented", src="sjc_mp2020",
                 xy=band("SJC", "12R/30L", 3260, 3550, -220, 150),
                 ev="12R extension to 11,000 ft (Oct 2004), NW end"),
        ],
    }


# per-feature overrides (aprons by id; former runway 11/29 at SJC)
FEAT = {
    "SFO": {
        "75ac0d86-c904-3bfb-b75d-e602031809ad": (1954, None, "documented", "sfo_wiki",
                                                 "Boarding Area D: apron of the Central Terminal (opened 27 Aug 1954)"),
        "88a4c581-5bdc-343c-9985-e5b88e640e88": (1963, None, "documented", "sfo_wiki",
                                                 "Boarding Area C: South Terminal, dedicated 15 Sep 1963"),
        "1e90289c-4ecf-33b4-8b3b-f58046a248c1": (1963, None, "documented", "sfo_wiki",
                                                 "Boarding Area B: South Terminal 1963 (pier rebuilt 2016-21 for "
                                                 "Harvey Milk Terminal 1; apron continuous)"),
        "16cb23d8-95be-3307-9081-8eba643d9346": (1979, None, "documented", "sfo_wiki", "Boarding Area F: North Terminal 1979"),
        "e7627687-c6db-392c-a705-a9923933f732": (1979, None, "documented", "sfo_wiki", "Boarding Area F: North Terminal 1979"),
        "08754c62-e969-3822-ba0a-67e8a245858e": (1981, None, "documented", "sfo_wiki", "Boarding Area E: opened 1981"),
        "a0fa2e7e-7183-3c90-aab6-b19cca9fee71": (2000, None, "documented", "sfo_wiki",
                                                 "International Terminal Boarding Area A, opened Dec 2000"),
        "e9042fbe-8db5-349b-a885-1920abf96851": (2000, None, "documented", "sfo_wiki",
                                                 "International Terminal Boarding Area G, opened Dec 2000"),
        "111c18bd-ceca-3907-944f-fbcdba9c73f6": (2000, None, "estimated", "usgs_topo",
                                                 "remote apron south of Boarding Area A: buildings on its site on the 1993 "
                                                 "sheet; with the International Terminal"),
        "2dc8a733-e430-3ce4-87be-5e113cb76d33": (1962, None, "estimated", "usgs_topo",
                                                 "West Field cargo apron: area developed between the 1956 and 1968 editions "
                                                 "(low confidence)"),
        "84f45dc1-f9f2-31c4-9557-e8779bf5f9ef": (1962, None, "estimated", "usgs_topo", "West Field apron (low confidence)"),
        "287a6e75-c91e-312a-8ff8-a600ecc47466": (1962, None, "estimated", "usgs_topo", "West Field apron (low confidence)"),
        "51c87361-e6e3-326d-afc8-5eaee8d9c821": (1962, None, "estimated", "usgs_topo",
                                                 "NW apron by the United maintenance base (1956 -> 1968 editions)"),
        "d1e11a3b-e85b-3307-b463-1eb0989d9014": (1962, None, "estimated", "usgs_topo",
                                                 "north aprons (Plot 40 / 41 area) between the 1956 and 1968 editions"),
        "9edc8e5e-7820-3661-8854-b375d26ac704": (1962, None, "estimated", "usgs_topo", "north apron (1956 -> 1968 editions)"),
        "3cdd0f57-7bb6-3ea9-9f01-268277d907ac": (1962, None, "estimated", "usgs_topo", "north apron (1956 -> 1968 editions)"),
        "88052d7f-b416-306e-b7f3-97c1378822aa": (1970, None, "estimated", "sfo_museum",
                                                 "Superbay hangar apron: hangar built 1969-72 (SFO Museum construction "
                                                 "photo 1970), on the 1979 PR"),
        "2c99bc85-9049-333e-89f7-152620ceed81": (1941, None, "documented", "sfo_cgas",
                                                 "Coast Guard Air Station San Francisco, commissioned 15 Nov 1940, "
                                                 "dedicated 15 Feb 1941"),
    },
    "OAK": {
        "e9bffe98-0347-3841-9ace-c0c6cb54f8fe": (1929, None, "estimated", "oak_backgrounder",
                                                 "North Field apron in front of the 1927-29 hangar row (five hangars, "
                                                 "terminal finished summer 1929); later enlarged"),
        "b865bf5b-55a2-34aa-a6e4-f99272e7b7b6": (1944, None, "estimated", "oak_nas", "NW North Field apron (Navy era)"),
        "49afd1a4-4db5-3af9-9585-5775bc2d4030": (1944, None, "estimated", "oak_nas", "NW North Field apron (Navy era)"),
        "c614501f-d8c4-3768-855a-57bc18165510": (1962, None, "documented", "oak_backgrounder",
                                                 "Terminal 1 / 2 apron: South Field terminal 1962 (Terminal 2 gates 1985, "
                                                 "T2 concourse 2006 on its east end)"),
        "17dd1f5e-f8af-3cac-9f84-4d9f497da2a1": (1988, None, "estimated", "oak_backgrounder",
                                                 "FedEx 'Metroplex regional sort facility west of the passenger terminals' "
                                                 "opened 1988 (identification by position)"),
        "620bc19f-2821-3a09-8aaf-a130e7c9c096": (1973, None, "documented", "oak_backgrounder",
                                                 "jet maintenance base (World Airways / World Air Center, 4 x 747) "
                                                 "dedicated 1973"),
        "458c4adc-1248-3abe-86a9-2735be81806c": (1962, None, "estimated", "oak_backgrounder", "cargo apron of the 1962 complex"),
        "9339145a-6f71-3b64-ba27-e3f75984c6df": (1962, None, "estimated", "oak_backgrounder", "cargo apron of the 1962 complex"),
        "4c6fbcda-8362-3289-b327-f191fd747275": (1962, None, "estimated", "oak_backgrounder", "apron west of Terminal 1"),
        "0e874849-1c01-38f0-88ff-191ddd3ead82": (1962, None, "estimated", "oak_backgrounder", "small South Field apron"),
    },
    "SJC": {
        "7f9a57ad-cb32-3b99-8565-dbfcbbff6b29": (1965, None, "documented", "sjc_timeline",
                                                 "east-side terminal apron: Terminal C opened 1965 (south concourse 1969, "
                                                 "Terminal A 1990, Terminal B 2010 on the same apron)"),
        "8d85165e-d6bf-3918-99cc-2ac27912d4f8": (1965, None, "estimated", "usgs_topo",
                                                 "west-side GA apron: hangars on it carry 1965-66 roll years"),
        "c0a97516-830d-3d4e-a8ab-259dda447eb5": (1965, None, "estimated", "usgs_topo", "west-side GA apron"),
        "58578fba-d937-3ffc-81f8-7084c1cb1e4e": (2002, None, "estimated", "sjc_mp2020",
                                                 "SE apron: rebuilt after the south-end GA terminal, tiedowns and T-hangars "
                                                 "were removed for the 2001 12L extension"),
        "1188c74e": (1970, None, "estimated", "sjc_timeline",
                     "former Runway 11/29 (4,600 ft GA runway, 'a third runway opened on the west side for general "
                     "aviation in the 1970s'; between the 1968 and 1973 PRs); closed c.2010-14 and used as Taxiway V"),
        "17be5be6": (1970, None, "estimated", "sjc_timeline", "former Runway 11/29 (NW half), now Taxiway V"),
    },
}
# taxiways / taxilanes in the SFO terminal area take the date of the nearest apron (within 80 m)
# when that is later than their zone's (they serve that pier)
TERMINAL_AREA = {"SFO": [[-1650, -850], [-450, -850], [-250, -300], [-250, 250], [-500, 600], [-1300, 650], [-1650, 300]]}

# airports.csv opening year: features no zone covers (none expected) fall back to it
OPENED = {"SFO": 1927, "OAK": 1927, "SJC": 1948}

# ----------------------------------------------------------------------------------------- vanished pavement
VANISHED = [
    dict(airport="SFO", name="Mills Field north-south runway (early 1930s, on the reclaimed tidelands)", kind="runway",
         axis=[[-338, 1400], [-372, 1000]], width=45, start=1931, end=1962, conf="estimated", src="sfo_museum",
         note="the north end of the N-S runway marked '4' on the 1946-photo sheet, outside today's pavement (a 1930-37 "
              "aerial film of Mills Field shows the 'original dirt-paved North-South runway'; paved and widened by "
              "1937). It lies ~300 m bayward of the c.1800 marsh edge, inside the dike of the 1939-photo sheet on the "
              "tidelands reclaimed in the early 1930s (fill_zones sm_sfo_tidelands_1930s), so it is not the 1927 strip "
              "(which ran on the marsh pasture by the Bayshore Highway): start = the reclamation (1931, ESTIMATED; "
              "airports.py waits for the ground). Only the part north of today's taxiway grid is given (its south part "
              "lies under later pavement). Still drawn 1956, gone with the 1960s north-side works (end = 1956 -> 1968 "
              "midpoint). Axis read on the 1946 sheet (+-20 m)"),
    dict(airport="OAK", name="NAS Oakland / North Field NW-SE diagonal runway", kind="runway",
         axis=[[-133, 1501], [595, 979]], width=45, start=1944, end=1986, conf="estimated", src="oak_nas",
         note="wartime runway ('four asphalt runways, the longest 6,500 ft'), on the 1947-1979 editions, gone on the "
              "1993 sheet (end = midpoint); axis read on the 1958-photo sheet (+-40 m)"),
]


# ========================================================================================== build
def runway_axes(feats):
    """Full axis (end a -> end b) of each runway from its Overture pieces (local metres)."""
    out = {}
    for ap, rws in RUNWAYS.items():
        out[ap] = {}
        for rw, d in rws.items():
            pts = []
            for i in d["ids"]:
                g = feats.loc[i].geometry
                x, y = ll2loc(ap, *np.asarray(g.coords).T)
                pts.append(np.c_[x, y])
            p = np.vstack(pts)
            c = p.mean(0)
            u = np.linalg.svd(p - c)[2][0]
            t = (p - c) @ u
            a, b = p[t.argmin()], p[t.argmax()]
            key = d["end_a"].split("(")[1].rstrip(")")
            score = {"west": lambda q: -q[0], "south": lambda q: -q[1], "southeast": lambda q: -q[1],
                     "north": lambda q: q[1], "northwest": lambda q: -q[0]}[key]
            if score(b) > score(a):
                a, b = b, a
            out[ap][rw] = (a, b)
    return out


RW_AXIS = {}


def main():
    d = pd.read_parquet(OVT)
    feats = gpd.GeoDataFrame(d, geometry=gpd.GeoSeries.from_wkb(d.geometry), crs=4326).set_index("id", drop=False)
    RW_AXIS.update(runway_axes(feats))
    Z = zones()
    rows, zfeat = [], []
    bbox = {"SFO": (-122.42, 37.59, -122.34, 37.645), "OAK": (-122.26, 37.69, -122.19, 37.75),
            "SJC": (-121.955, 37.345, -121.905, 37.385)}
    for ap in ("SFO", "OAK", "SJC"):
        x0, y0, x1, y1 = bbox[ap]
        f = feats.cx[x0:x1, y0:y1]
        f = f[f["class"].isin(["runway", "stopway", "taxiway", "taxilane", "apron"])]
        loc = {i: shapely.transform(g, lambda xy: np.c_[ll2loc(ap, xy[:, 0], xy[:, 1])])
               for i, g in zip(f.id, f.geometry)}
        # --- runways
        done = set()
        for rw, rd in RUNWAYS[ap].items():
            a, b = RW_AXIS[ap][rw]
            L = float(np.linalg.norm(b - a)); u = (b - a) / L
            for d0, d1, y, conf, src, ev in rd["parts"]:
                ln = LineString([a + d0 * u, a + min(d1, L) * u])
                poly = shapely.buffer(ln, rd["width"] / 2, cap_style="flat")
                zfeat.append(dict(airport=ap, zone=f"{ap} {rw} d{d0}-{d1}", kind="runway_phase", start_year=y,
                                  end_year=9999, confidence=conf, source_url=SRC[src], evidence=ev, xy=poly))
            for i in rd["ids"]:
                done.add(i)
                g = loc[i]
                c = np.asarray(g.coords)
                pr = (c - a) @ u
                p0, p1 = float(pr.min()), float(pr.max())
                ll = feats.loc[i].geometry.representative_point()
                for d0, d1, y, conf, src, ev in rd["parts"]:
                    q0, q1 = max(p0, d0), min(p1, d1)
                    if q1 - q0 < 5:
                        continue
                    whole = (q0 - p0) < 5 and (p1 - q1) < 5
                    e0 = loc2ll(ap, *(a + q0 * u)); e1 = loc2ll(ap, *(a + q1 * u))
                    rows.append(dict(airport=ap, feature_class=feats.loc[i, "class"], overture_id=i, runway=rw, clip_zone="",
                                     name=feats.loc[i, "name"] if isinstance(feats.loc[i, "name"], str) else "",
                                     lon=round(ll.x, 6), lat=round(ll.y, 6),
                                     part="whole" if whole else "axis_interval",
                                     from_end=rd["end_a"], d0_m=round(q0), d1_m=round(q1),
                                     part_lon0=round(float(e0[0]), 6), part_lat0=round(float(e0[1]), 6),
                                     part_lon1=round(float(e1[0]), 6), part_lat1=round(float(e1[1]), 6),
                                     start_year=y, end_year=9999, confidence=conf, source_url=SRC[src], evidence=ev))
        # --- zones
        zp = []
        for z in Z[ap]:
            p = Polygon(z["xy"]).buffer(0)
            zp.append((z, p))
        # effective (non-overlapping) zones: a later zone wins where zones overlap
        eff = []
        for k, (z, p) in enumerate(zp):
            later = shapely.union_all([q for _, q in zp[k + 1:]]) if k + 1 < len(zp) else None
            e = p.difference(later) if later is not None else p
            eff.append((z, shapely.make_valid(e)))
        for z, e in eff:
            zfeat.append(dict(airport=ap, zone=z["id"], kind="zone", start_year=z["start"], end_year=9999,
                              confidence=z["conf"], source_url=SRC[z["src"]], evidence=z["ev"], xy=e))
        aprons = {i: loc[i] for i in f.id if feats.loc[i, "class"] == "apron"}
        term = Polygon(TERMINAL_AREA[ap]) if ap in TERMINAL_AREA else None

        def base(i, g, y, ye, conf, src, ev, zone, part="whole", clip=""):
            ll = feats.loc[i].geometry.representative_point()
            return dict(airport=ap, feature_class=feats.loc[i, "class"], overture_id=i, runway="",
                        name=feats.loc[i, "name"] if isinstance(feats.loc[i, "name"], str) else "",
                        lon=round(ll.x, 6), lat=round(ll.y, 6), part=part, clip_zone=clip, from_end="", d0_m="",
                        d1_m="", part_lon0="", part_lat0="", part_lon1="", part_lat1="",
                        start_year=y, end_year=ye or 9999, confidence=conf, source_url=SRC[src],
                        evidence=f"[{zone}] {ev}")
        for i in f.id:
            if i in done:
                continue
            g = loc[i]
            cls = feats.loc[i, "class"]
            poly = g.geom_type == "Polygon"
            tot = g.area if poly else g.length
            ov = FEAT[ap].get(i) or FEAT[ap].get(i[:8])
            if ov:
                y, ye, conf, src, ev = ov
                rows.append(base(i, g, y, ye, conf, src, ev, "feature"))
                continue
            pieces = []
            for z, e in eff:
                v = g.intersection(e)
                m = v.area if poly else v.length
                if m > 0:
                    pieces.append((m / tot if tot else 0, m, z))
            pieces.sort(key=lambda t: -t[0])
            cover = sum(t[0] for t in pieces)
            if term is not None and cls in ("taxiway", "taxilane") and term.contains(g.centroid):
                near = sorted(((g.distance(ag), ai) for ai, ag in aprons.items()))
                z0 = pieces[0][2] if pieces else None
                if near and near[0][0] < 80:
                    ao = FEAT[ap].get(near[0][1])
                    if ao and (z0 is None or ao[0] > z0["start"]):
                        rows.append(base(i, g, ao[0], None, ao[2], ao[3],
                                         f"terminal-area taxiway serving apron {near[0][1][:8]}: {ao[4]}",
                                         "terminal-apron"))
                        continue
            big = [t for t in pieces if t[0] >= 0.12 and t[1] >= (2000 if poly else 40)]
            if not pieces or cover < 0.5:
                rows.append(base(i, g, OPENED[ap], None, "estimated", "usgs_topo",
                                 "outside the dated zones: airport opening year", "none"))
            elif len(big) <= 1 or pieces[0][0] >= 0.88:
                z = pieces[0][2]
                rows.append(base(i, g, z["start"], None, z["conf"], z["src"], z["ev"], z["id"]))
            else:
                for share, m, z in big:
                    rows.append(base(i, g, z["start"], None, z["conf"], z["src"],
                                     f"{round(100 * share)} % of the feature: {z['ev']}", z["id"],
                                     part="zone_clip", clip=z["id"]))
    cols = ["airport", "feature_class", "overture_id", "runway", "name", "lon", "lat", "part", "clip_zone", "from_end", "d0_m", "d1_m",
            "part_lon0", "part_lat0", "part_lon1", "part_lat1", "start_year", "end_year", "confidence", "source_url",
            "evidence"]
    with open(HERE / "pavement_dates.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    # zones + runway phases as lon/lat polygons
    feats_out = []
    for z in zfeat:
        p = shapely.transform(z.pop("xy"), lambda xy: np.c_[loc2ll(z["airport"], xy[:, 0], xy[:, 1])])
        feats_out.append({"type": "Feature", "properties": z, "geometry": mapping(shapely.set_precision(p, 1e-7))})
    (HERE / "pavement_zones.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats_out}, indent=0))
    # vanished pavement
    vf = []
    for v in VANISHED:
        ln = LineString(v["axis"])
        p = shapely.buffer(ln, v["width"] / 2, cap_style="flat")
        p = shapely.transform(p, lambda xy: np.c_[loc2ll(v["airport"], xy[:, 0], xy[:, 1])])
        props = {k: v[k] for k in ("airport", "name", "kind", "start", "end", "conf", "note")}
        props = dict(airport=v["airport"], name=v["name"], kind=v["kind"], start_year=v["start"], end_year=v["end"],
                     width_m=v["width"], confidence=v["conf"], source_url=SRC[v["src"]], note=v["note"])
        vf.append({"type": "Feature", "properties": props, "geometry": mapping(shapely.set_precision(p, 1e-7))})
    (HERE / "vanished_pavement.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": vf}, indent=0))
    df = pd.DataFrame(rows)
    print(df.groupby(["airport", "feature_class"]).size().to_string())
    print(df.groupby(["airport", "start_year"]).size().to_string())


if __name__ == "__main__":
    main()
