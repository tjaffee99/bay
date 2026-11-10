"""Dated built-up extents of the region's older towns, read from USGS historical topographic maps.

  python -I extents.py sheet  TOWN SHEET [--preview]   render + align one sheet over a town, block stats (cache)
  python -I extents.py build  TOWN [YEAR ...]          classify blocks, write data/manual/region_extents/<town>_<year>.geojson
  python -I extents.py check  TOWN                     validation numbers + check PNG
  python -I extents.py all    TOWN                     sheet (every sheet of every snapshot) + build + check

Method (details and per-snapshot notes in ../README.md):

1. Sheets: USGS Historical Topographic Map Collection GeoTIFFs (public domain, TNM Access API; FGDC
   metadata for survey / aerial-photo years). The 1:62,500 15' sheets of 1885-1915 draw a closely
   built block front as a heavy black band along the street and a scattered house as a small solid
   square; the 1:24,000 7.5' sheets (and 1:62,500 editions) of 1939-1953 tint the built-up area
   red / pink and draw only landmark buildings inside it (houses outside the tint as squares).
2. Each sheet is resampled into UTM 10N (WGS84) at RES m through its own registration and the NOAA
   NADCON grid (NAD27 -> WGS84), masked to its quadrangle, and aligned to today's street centrelines
   (Overture / OpenStreetMap) by windowed cross-correlation of the black ink (the 1890s surveys are
   ~100-250 m off; the 1940s sheets a few metres), fitted as a constant or affine shift by consensus.
3. Blocks: today's street centrelines (Overture roads, motorways and service roads left out)
   polygonised and clipped to the town (TIGER 2024 places): the block is the unit of the extent.
4. Per block: heavy ink (black, lines thinner than ~0.15 mm removed by an opening), split into
   *bands* (ink runs >= ~40 m long: built frontage, large buildings) and *squares* (single houses);
   built frontage share = band length / frontage length + 15 m per square; on the tint sheets the
   share of the block under the urban tint. A block is built up when its share passes the
   threshold of its sheet style (see THRESH); holes under HOLE_HA are filled, specks under MIN_HA
   dropped, and the result is clipped to today's land.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "data" / "raw" / "region_extents"
INT = ROOT / "data" / "interim" / "region_extents"
OUT = ROOT / "data" / "manual" / "region_extents"
PROJ_DIR = ROOT / "data" / "raw" / "proj"
OVT = ROOT / "data" / "raw" / "overture" / "2026-10-21.0"
TIGER = ROOT / "data" / "raw" / "tiger" / "tl_2024_06_place.zip"
TIF = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/"
PDF = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/"
os.environ.setdefault("CURL_CA_BUNDLE", "/root/.ccr/ca-bundle.crt")
UTM = "EPSG:32610"
RES = 2.5

# --------------------------------------------------------------------------- sheets
# key -> USGS HTMC scan: file (GeoTIFF name), quad (NAD27 W, S, E, N), scale, edition (date on map),
# year (what the map shows: survey year, or aerial-photo year of the 1939-53 sheets), style.
S = {}


def sheet(key, file, quad, scale, edition, year, style, note="", tint="pink", **kw):
    """kw: open_mm = line weight (mm on paper) below which ink is a line, not a building (default 0.15)."""
    S[key] = dict(key=key, file=file, quad=quad, scale=scale, edition=edition, year=year, style=style, note=note,
                  tint=tint, **kw)


Q15 = lambda w, s: (w, s, w + 0.25, s + 0.25)      # noqa: E731
Q75 = lambda w, s: (w, s, w + 0.125, s + 0.125)    # noqa: E731
sheet("sf1895", "CA_San%20Francisco_298889_1895_62500_geo.tif", Q15(-122.5, 37.75), 62500, 1895, 1894, "early",
      "surveyed 1892-94")
sheet("sf1915", "CA_San%20Francisco_298897_1915_62500_geo.tif", Q15(-122.5, 37.75), 62500, 1915, 1914, "early",
      "1915 edition: surveyed 1892-94, culture revised in 1914 (collar note)")
sheet("concord1897", "CA_Concord_297157_1897_62500_geo.tif", Q15(-122.25, 37.75), 62500, 1897, 1894, "early",
      "surveyed 1893-94 (collar), engraved Apr 1897")
sheet("concord1915", "CA_Concord_297163_1915_62500_geo.tif", Q15(-122.25, 37.75), 62500, 1915, 1914, "early",
      "edition of June 1915: surveyed 1893-94, culture revised in part in 1913-14 (collar note)")
sheet("concord1942", "CA_Concord_465521_1942_62500_geo.tif", Q15(-122.25, 37.75), 62500, 1942, 1939, "tint",
      "aerial photographs 1939", tint="grey")
sheet("haywards1899", "CA_Haywards_297665_1899_62500_geo.tif", Q15(-122.25, 37.5), 62500, 1899, 1896, "early",
      "surveyed 1896 (1901 imprint)")
sheet("hayward1915", "CA_Hayward_297660_1915_62500_geo.tif", Q15(-122.25, 37.5), 62500, 1915, 1914, "early",
      "surveyed 1914 (1939 imprint)")
sheet("hayward1942", "CA_Hayward_465728_1942_62500_geo.tif", Q15(-122.25, 37.5), 62500, 1942, 1939, "tint",
      "aerial photographs 1939", tint="grey")
sheet("oaklandwest1949", "CA_Oakland%20West_293623_1949_24000_geo.tif", Q75(-122.375, 37.75), 24000, 1949, 1946,
      "tint", "aerial photographs 1946, field check 1947")
sheet("oaklandeast1947", "CA_Oakland%20East_293612_1947_24000_geo.tif", Q75(-122.25, 37.75), 24000, 1947, 1946,
      "tint", "aerial photographs 1946, field check 1947")
sheet("richmond1947", "CA_Richmond_294667_1947_24000_geo.tif", Q75(-122.375, 37.875), 24000, 1947, 1946, "tint",
      "aerial photographs 1946, field check 1947")
sheet("briones1947", "CA_Briones%20Valley_288606_1947_24000_geo.tif", Q75(-122.25, 37.875), 24000, 1947, 1946,
      "tint", "aerial photographs 1946, field check 1947")
sheet("sanleandro1947", "CA_San%20Leandro_300122_1947_24000_geo.tif", Q75(-122.25, 37.625), 24000, 1947, 1946,
      "tint", "1947 edition (photos c. 1946)")
sheet("hayward1947", "CA_Hayward_291242_1947_24000_geo.tif", Q75(-122.125, 37.625), 24000, 1947, 1946, "tint",
      "aerial photographs 1946, survey 1947")
sheet("sanquentin1948", "CA_San%20Quentin_300194_1948_24000_geo.tif", Q75(-122.5, 37.875), 24000, 1948, 1947,
      "tint", "aerial photographs 1947")
sheet("newark1947", "CA_Newark_293493_1947_24000_geo.tif", Q75(-122.125, 37.5), 24000, 1947, 1946, "tint",
      "aerial photographs 1946")
sheet("sanjose1889", "CA_San%20Jose_301582_1889_62500_geo.tif", Q15(-122.0, 37.25), 62500, 1889, 1885, "early",
      "surveyed 1885 (1939 reprint)")
sheet("sanjose1897", "CA_San%20Jose_298899_1897_62500_geo.tif", Q15(-122.0, 37.25), 62500, 1897, 1895, "early",
      "surveyed 1895")
sheet("sanjose1943", "CA_San%20Jose_466308_1943_62500_geo.tif", Q15(-122.0, 37.25), 62500, 1943, 1939, "tint",
      "aerial photographs 1939", tint="grey")
sheet("sanjosewest1953", "CA_San%20Jose%20West_300105_1953_24000_geo.tif", Q75(-122.0, 37.25), 24000, 1953, 1948,
      "tint", "aerial photographs 1948, survey 1953")
sheet("sanjoseeast1953", "CA_San%20Jose%20East_300099_1953_24000_geo.tif", Q75(-121.875, 37.25), 24000, 1953, 1948,
      "tint", "aerial photographs 1948, survey 1953")
sheet("milpitas1953", "CA_Milpitas_292969_1953_24000_geo.tif", Q75(-122.0, 37.375), 24000, 1953, 1948, "tint",
      "aerial photographs 1948, survey 1953")
sheet("paloalto1899", "CA_Palo%20Alto_298453_1899_62500_geo.tif", Q15(-122.25, 37.25), 62500, 1899, 1895, "early",
      "surveyed 1895")
sheet("paloalto1943", "CA_Palo%20Alto_298463_1943_62500_geo.tif", Q15(-122.25, 37.25), 62500, 1943, 1940, "tint",
      "aerial photographs 1940", tint="grey")
sheet("paloalto1953", "CA_Palo%20Alto_293907_1953_24000_geo.tif", Q75(-122.25, 37.375), 24000, 1953, 1948, "tint",
      "aerial photographs 1948, survey 1953")
sheet("mountainview1953", "CA_Mountain%20View_293234_1953_24000_geo.tif", Q75(-122.125, 37.375), 24000, 1953, 1948,
      "tint", "aerial photographs 1948, survey 1953")
sheet("woodside1953", "CA_Woodside_301429_1953_24000_geo.tif", Q75(-122.375, 37.375), 24000, 1953, 1948, "tint",
      "aerial photographs 1948, field check 1953")
sheet("redwoodpoint1948", "CA_Redwood%20Point_294610_1948_24000_geo.tif", Q75(-122.25, 37.5), 24000, 1948, 1948,
      "tint", "1948 edition")
sheet("sanmateo1896", "CA_San%20Mateo_298916_1896_62500_geo.tif", Q15(-122.5, 37.5), 62500, 1896, 1892, "early",
      "surveyed 1892")
sheet("sanmateo1915", "CA_San%20Mateo_298922_1915_62500_geo.tif", Q15(-122.5, 37.5), 62500, 1915, 1914, "early",
      "1915 edition: surveyed 1892, culture revised in part in 1914 (collar note)")
sheet("sanmateo1943", "CA_San%20Mateo_466324_1943_62500_geo.tif", Q15(-122.5, 37.5), 62500, 1943, 1939, "tint",
      "aerial photographs 1939", tint="grey")
sheet("sanmateo1947", "CA_San%20Mateo_300157_1947_24000_geo.tif", Q75(-122.375, 37.5), 24000, 1947, 1946, "tint",
      "aerial photographs 1946, field check 1947")
sheet("tamalpais1897", "CA_Tamalpais_298980_1897_62500_geo.tif", Q15(-122.75, 37.75), 62500, 1897, 1895, "early",
      "surveyed 1895")
sheet("tamalpais1941", "CA_Tamalpais_301788_1941_62500_geo.tif", Q15(-122.75, 37.75), 62500, 1941, 1939, "tint",
      "aerial photographs 1939", tint="grey")
sheet("sanrafael1954", "CA_San%20Rafael_300201_1954_24000_geo.tif", Q75(-122.625, 37.875), 24000, 1954, 1952,
      "tint", "aerial photographs 1952, field check 1954")
sheet("karquines1898", "CA_Karquines_297860_1898_62500_geo.tif", Q15(-122.25, 38.0), 62500, 1898, 1896, "early",
      "surveyed 1896")
sheet("carquinez1942", "CA_Carquinez_297034_1942_62500_geo.tif", Q15(-122.25, 38.0), 62500, 1942, 1937, "tint",
      "aerial photographs 1937", tint="grey")
sheet("carquinezstrait1940", "CA_Carquinez%20Strait_297037_1940_62500_geo.tif", Q15(-122.25, 38.0), 62500, 1940, 1940,
      "tint", "aerial photographs 1940 (1965 imprint)", tint="grey")
sheet("benicia1950", "CA_Benicia_288319_1950_24000_geo.tif", Q75(-122.25, 38.0), 24000, 1950, 1948, "tint",
      "aerial photographs 1948, field check 1950")
sheet("portchicago1951", "CA_Port%20Chicago_294325_1951_24000_geo.tif", Q75(-122.125, 38.0), 24000, 1951, 1948,
      "tint", "aerial photographs 1948, survey 1950")

# ---- the ten-county extent (2026-11): Sonoma, Napa, Solano, Santa Cruz, east Contra Costa, south Santa Clara.
# Survey / photo years from each scan's FGDC record (TNM). Q30: the 1:125,000 30' reconnaissance sheets.
Q30 = lambda w, s: (w, s, w + 0.5, s + 0.5)        # noqa: E731
# first surveys (houses drawn one by one, block fronts as bands)
sheet("napa1902", "CA_Napa_299520_1902_125000_geo.tif", Q30(-122.5, 38.0), 125000, 1902, 1899, "early",
      "1:125,000 30' sheet, surveyed 1896-99 (FGDC: survey year 1899)", open_mm=0.26)
# (the sheet runs over its south neat line to 36°56' N to hold the city of Santa Cruz and Point Santa Cruz)
sheet("santacruz1902", "CA_Santa%20Cruz_299623_1902_125000_geo.tif", (-122.5, 36.93, -122.0, 37.5), 125000, 1902, 1899,
      "early", "1:125,000 30' sheet, surveyed to 1899 (1904 imprint); read over its south edge (the city of Santa Cruz)")
sheet("santarosa1916", "CA_Santa%20Rosa_298960_1916_62500_geo.tif", Q15(-122.75, 38.25), 62500, 1916, 1914, "early",
      "surveyed 1914 (1927 imprint)")
sheet("petaluma1914", "CA_Petaluma_298524_1914_62500_geo.tif", Q15(-122.75, 38.0), 62500, 1914, 1912, "early",
      "surveyed 1912 (1924 imprint)")
sheet("mareisland1916", "CA_Mare%20Island_298114_1916_62500_geo.tif", Q15(-122.5, 38.0), 62500, 1916, 1914, "early",
      "surveyed 1914 (1927 imprint)")
sheet("capitola1914", "CA_Capitola_297018_1914_62500_geo.tif", Q15(-122.0, 36.75), 62500, 1914, 1912, "early",
      "surveyed 1912 (1922 imprint)")
sheet("sanjuanbautista1917", "CA_San%20Juan%20Bautista_466314_1917_62500_geo.tif", Q15(-121.75, 36.75), 62500, 1917,
      1915, "early", "surveyed 1915 (1925 imprint)")
sheet("morganhill1917", "CA_Morgan%20Hill_298244_1917_62500_geo.tif", Q15(-121.75, 37.0), 62500, 1917, 1915, "early",
      "surveyed 1915 (1931 imprint)")
sheet("vacaville1908", "CA_Vacaville_299006_1908_62500_geo.tif", Q15(-122.0, 38.25), 62500, 1908, 1906, "early",
      "surveyed 1906 (1922 imprint)")
sheet("antioch1908", "CA_Antioch_296718_1908_62500_geo.tif", Q15(-122.0, 38.0), 62500, 1908, 1907, "early",
      "surveyed 1907 (1914 imprint)")
sheet("riovista1910", "CA_Rio%20Vista_296463_1910_31680_geo.tif", Q75(-121.75, 38.125), 31680, 1910, 1908, "early",
      "1:31,680 sheet, surveyed 1908")
sheet("healdsburg1920", "CA_Healdsburg_465734_1920_62500_geo.tif", Q15(-123.0, 38.5), 62500, 1920, 1915, "early",
      "edition of 1920, field check 1915", open_mm=0.26)
sheet("calistoga1927", "CA_Calistoga_465409_1927_62500_geo.tif", Q15(-122.75, 38.5), 62500, 1927, 1915, "early",
      "edition of 1927, surveyed 1915", open_mm=0.26)
sheet("hopland1938", "CA_Hopland_465760_1938_62500_geo.tif", Q15(-123.25, 38.75), 62500, 1938, 1922, "early",
      "edition of 1938: surveyed 1916, field check 1922", open_mm=0.26)
# 1:62,500 editions of 1933-43 (resurveys and editions compiled from 1937-42 aerial photographs)
sheet("healdsburg1940", "CA_Healdsburg_297672_1940_62500_geo.tif", Q15(-123.0, 38.5), 62500, 1940, 1933, "tint",
      "edition of 1940, surveyed 1933", tint="grey", open_mm=0.26)
sheet("sebastopol1942", "CA_Sebastopol_301668_1942_62500_geo.tif", Q15(-123.0, 38.25), 62500, 1942, 1935, "tint",
      "edition of 1942, surveyed 1935", tint="grey", open_mm=0.26)
sheet("capitola1940", "CA_Capitola_465438_1940_62500_geo.tif", Q15(-122.0, 36.75), 62500, 1940, 1938, "tint",
      "aerial photographs 1938", tint="grey", open_mm=0.26)
sheet("sanjuanbautista1940", "CA_San%20Juan%20Bautista_466316_1940_62500_geo.tif", Q15(-121.75, 36.75), 62500, 1940,
      1939, "tint", "aerial photographs 1939", tint="grey", open_mm=0.26)
sheet("morganhill1941", "CA_Morgan%20Hill_465964_1941_62500_geo.tif", Q15(-121.75, 37.0), 62500, 1941, 1939, "tint",
      "edition of 1941: surveyed 1915, revised 1939 (aerial photographs 1939 on the 1939 edition)", tint="grey", open_mm=0.26)
sheet("sonoma1942", "CA_Sonoma_301738_1942_62500_geo.tif", Q15(-122.5, 38.25), 62500, 1942, 1939, "tint",
      "aerial photographs 1939, survey 1941", tint="grey", open_mm=0.26)
sheet("mtvaca1942", "CA_Mt%20Vaca_466013_1942_62500_geo.tif", Q15(-122.25, 38.25), 62500, 1942, 1939, "tint",
      "aerial photographs 1939", tint="grey", open_mm=0.26)
sheet("vacaville1941", "CA_Vacaville_466506_1941_62500_geo.tif", Q15(-122.0, 38.25), 62500, 1941, 1939, "tint",
      "aerial photographs 1939", tint="grey", open_mm=0.26)
sheet("byron1940", "CA_Byron_296942_1940_62500_geo.tif", Q15(-121.75, 37.75), 62500, 1940, 1940, "tint",
      "aerial photographs 1940 (1943 imprint)", tint="grey", open_mm=0.26)
sheet("santarosa1944", "CA_Santa%20Rosa_301627_1944_62500_geo.tif", Q15(-122.75, 38.25), 62500, 1944, 1942, "tint",
      "edition of 1944: surveyed 1914, revised 1942", tint="grey", open_mm=0.26)
sheet("sthelena1945", "CA_St%20Helena_466421_1945_62500_geo.tif", Q15(-122.5, 38.5), 62500, 1945, 1942, "tint",
      "edition of 1945, surveyed 1942", tint="grey", open_mm=0.26)
sheet("hopland1944", "CA_Hopland_465759_1944_62500_geo.tif", Q15(-123.25, 38.75), 62500, 1944, 1942, "tint",
      "aerial photographs 1942", tint="grey", open_mm=0.26)
sheet("calistoga1945", "CA_Calistoga_296981_1945_62500_geo.tif", Q15(-122.75, 38.5), 62500, 1945, 1943, "tint",
      "edition of 1945, surveyed 1943", tint="grey", open_mm=0.26)
# 1:24,000 sheets of 1949-60 (first imprints, before the photorevisions)
sheet("mareisland1949", "CA_Mare%20Island_292723_1949_24000_geo.tif", Q75(-122.375, 38.0), 24000, 1949, 1948, "tint",
      "aerial photographs 1948, survey 1949")
sheet("napa1951", "CA_Napa_293422_1951_24000_geo.tif", Q75(-122.375, 38.25), 24000, 1951, 1948, "tint",
      "aerial photographs 1948, survey 1951")
sheet("sonoma1951", "CA_Sonoma_300595_1951_24000_geo.tif", Q75(-122.5, 38.25), 24000, 1951, 1948, "tint",
      "aerial photographs 1948, survey 1951")
sheet("rutherford1951", "CA_Rutherford_294860_1951_24000_geo.tif", Q75(-122.5, 38.375), 24000, 1951, 1948, "tint",
      "aerial photographs 1948, survey 1951")
sheet("fairfieldsouth1949", "CA_Fairfield%20South_290434_1949_24000_geo.tif", Q75(-122.125, 38.125), 24000, 1949,
      1948, "tint", "aerial photographs 1948, survey 1949")
sheet("fairfieldnorth1951", "CA_Fairfield%20North_290424_1951_24000_geo.tif", Q75(-122.125, 38.25), 24000, 1951,
      1948, "tint", "aerial photographs 1948, survey 1951")
sheet("elmira1953", "CA_Elmira_303008_1953_24000_geo.tif", Q75(-122.0, 38.25), 24000, 1953, 1949, "tint",
      "aerial photographs 1949, field check 1953")
sheet("dixon1952", "CA_Dixon_465565_1952_24000_geo.tif", Q75(-121.875, 38.375), 24000, 1952, 1949, "tint",
      "aerial photographs 1949, survey 1952")
sheet("riovista1953", "CA_Rio%20Vista_294705_1953_24000_geo.tif", Q75(-121.75, 38.125), 24000, 1953, 1949, "tint",
      "aerial photographs 1949, survey 1953")
sheet("antiochnorth1953", "CA_Antioch%20North_288002_1953_24000_geo.tif", Q75(-121.875, 38.0), 24000, 1953, 1949,
      "tint", "aerial photographs 1949, field check 1953")
sheet("honkerbay1953", "CA_Honker%20Bay_291408_1953_24000_geo.tif", Q75(-122.0, 38.0), 24000, 1953, 1949, "tint",
      "aerial photographs 1949, field check 1953")
sheet("brentwood1954", "CA_Brentwood_288600_1954_24000_geo.tif", Q75(-121.75, 37.875), 24000, 1954, 1949, "tint",
      "aerial photographs 1949, field check 1954")
sheet("santarosa1954", "CA_Santa%20Rosa_300294_1954_24000_geo.tif", Q75(-122.75, 38.375), 24000, 1954, 1952, "tint",
      "aerial photographs 1952, survey 1954")
sheet("petaluma1953", "CA_Petaluma_294061_1953_24000_geo.tif", Q75(-122.75, 38.125), 24000, 1953, 1952, "tint",
      "aerial photographs 1952, survey 1953")
sheet("petalumacreek1954", "CA_Petaluma%20Creek_466127_1954_24000_geo.tif", Q75(-122.625, 38.125), 24000, 1954, 1952,
      "tint", "aerial photographs 1952, survey 1954 (the quadrangle later named Petaluma River)")
sheet("sebastopol1954", "CA_Sebastopol_300394_1954_24000_geo.tif", Q75(-122.875, 38.375), 24000, 1954, 1952, "tint",
      "aerial photographs 1952, survey 1954")
sheet("santacruz1954", "CA_Santa%20Cruz_300246_1954_24000_geo.tif", (-122.1833333, 36.9166667, -122.0, 37.0), 24000,
      1954, 1952, "tint", "aerial photographs 1952, survey 1954")
sheet("soquel1954", "CA_Soquel_300606_1954_24000_geo.tif", Q75(-122.0, 36.875), 24000, 1954, 1952, "tint",
      "aerial photographs 1952, survey 1954")
sheet("watsonvillewest1954", "CA_Watsonville%20West_301247_1954_24000_geo.tif", Q75(-121.875, 36.875), 24000, 1954,
      1952, "tint", "aerial photographs 1952, survey 1954")
sheet("watsonvilleeast1955", "CA_Watsonville%20East_301243_1955_24000_geo.tif", Q75(-121.75, 36.875), 24000, 1955,
      1952, "tint", "aerial photographs 1952, survey 1955")
sheet("chittenden1955", "CA_Chittenden_289219_1955_24000_geo.tif", Q75(-121.625, 36.875), 24000, 1955, 1952, "tint",
      "aerial photographs 1952, survey 1955")
sheet("gilroy1955", "CA_Gilroy_290814_1955_24000_geo.tif", Q75(-121.625, 37.0), 24000, 1955, 1953, "tint",
      "aerial photographs 1953, survey 1955")
sheet("morganhill1955", "CA_Morgan%20Hill_293124_1955_24000_geo.tif", Q75(-121.75, 37.125), 24000, 1955, 1953, "tint",
      "aerial photographs 1953, survey 1955")
sheet("mtmadonna1955", "CA_Mt%20Madonna_293330_1955_24000_geo.tif", Q75(-121.75, 37.0), 24000, 1955, 1953, "tint",
      "aerial photographs 1953, survey 1955")
sheet("healdsburg1955", "CA_Healdsburg_291252_1955_24000_geo.tif", Q75(-122.875, 38.5), 24000, 1955, 1953, "tint",
      "aerial photographs 1953, field check 1955")
sheet("guerneville1955", "CA_Guerneville_291072_1955_24000_geo.tif", Q75(-123.0, 38.5), 24000, 1955, 1953, "tint",
      "aerial photographs 1953, field check 1955")
sheet("felton1955", "CA_Felton_465668_1955_24000_geo.tif", Q75(-122.125, 37.0), 24000, 1955, 1953, "tint",
      "aerial photographs 1953, field check 1955")
sheet("castlerockridge1955", "CA_Castle%20Rock%20Ridge_289043_1955_24000_geo.tif", Q75(-122.125, 37.125), 24000, 1955,
      1953, "tint", "aerial photographs 1953, field check 1955")
sheet("bigbasin1955", "CA_Big%20Basin_288374_1955_24000_geo.tif", Q75(-122.25, 37.125), 24000, 1955, 1953, "tint",
      "aerial photographs 1953, field check 1955")
sheet("calistoga1958", "CA_Calistoga_288811_1958_24000_geo.tif", Q75(-122.625, 38.5), 24000, 1958, 1957, "tint",
      "aerial photographs 1957, field check 1958")
sheet("sthelena1960", "CA_St%20Helena_295293_1960_24000_geo.tif", Q75(-122.5, 38.5), 24000, 1960, 1957, "tint",
      "aerial photographs 1957, field check 1960")
sheet("cloverdale1960", "CA_Cloverdale_289371_1960_24000_geo.tif", Q75(-123.125, 38.75), 24000, 1960, 1957, "tint",
      "aerial photographs 1957, field check 1960")


def sheet_path(sh):
    """The sheet's GeoPDF (the full 600-700 ppi scan; the GeoTIFF is a 300 ppi resample)."""
    name = sh["file"].replace("_geo.tif", "_geo.pdf")
    p = RAW / "topo" / name.replace("%20", "_")
    if not p.exists() or p.stat().st_size < 10000:
        import subprocess
        p.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["curl", "-sS", "-L", "-m", "900", "-o", str(p), f"{PDF}{sh['scale']}/{name}"], check=True)
    return p


# --------------------------------------------------------------------------- towns
# places: TIGER 2024 GEOIDs; bbox (lon/lat) bounds the processing (historic core + growth to c. 1950);
# snaps: year -> sheet keys (one survey generation per snapshot)
EARLY_OAK = ["sf1895", "concord1897", "haywards1899"]
REV_OAK = ["sf1915", "concord1915", "hayward1915"]
TOWNS = {
    "oakland": dict(name="Oakland (incl. Emeryville, Piedmont)", places=["0653000", "0622594", "0656938"],
                    bbox=(-122.335, 37.725, -122.155, 37.855),
                    snaps={1894: EARLY_OAK, 1914: REV_OAK, 1939: ["concord1942", "hayward1942"],
                           1946: ["oaklandwest1949", "oaklandeast1947", "sanleandro1947"]}),
    "berkeley": dict(name="Berkeley (incl. Albany)", places=["0606000", "0600674"],
                     bbox=(-122.33, 37.845, -122.23, 37.91),
                     snaps={1894: ["sf1895", "concord1897"], 1914: ["sf1915", "concord1915"],
                            1946: ["richmond1947", "oaklandwest1949", "briones1947", "oaklandeast1947"]}),
    "alameda": dict(name="Alameda", places=["0600562"], bbox=(-122.34, 37.74, -122.22, 37.80),
                    snaps={1894: ["sf1895", "concord1897"], 1914: ["sf1915", "concord1915"],
                           1946: ["oaklandwest1949", "oaklandeast1947"]}),
    "san_jose": dict(name="San José (incl. Santa Clara)", places=["0668000", "0669084"],
                     bbox=(-122.00, 37.28, -121.83, 37.40),
                     snaps={1885: ["sanjose1889"], 1895: ["sanjose1897"], 1939: ["sanjose1943"],
                            1948: ["sanjosewest1953", "sanjoseeast1953", "milpitas1953"]}),
    "san_leandro": dict(name="San Leandro", places=["0668084"], bbox=(-122.21, 37.67, -122.10, 37.74),
                        snaps={1896: ["haywards1899"], 1914: ["hayward1915"], 1939: ["hayward1942"],
                               1946: ["sanleandro1947", "hayward1947"]}),
    "hayward": dict(name="Hayward", places=["0633000"], bbox=(-122.15, 37.61, -122.00, 37.70),
                    snaps={1896: ["haywards1899"], 1914: ["hayward1915"], 1939: ["hayward1942"],
                           1946: ["hayward1947", "sanleandro1947", "newark1947"]}),
    "richmond": dict(name="Richmond (incl. El Cerrito, San Pablo)", places=["0660620", "0621796", "0668294"],
                     bbox=(-122.42, 37.90, -122.29, 37.99),
                     snaps={1894: ["sf1895"], 1914: ["sf1915"], 1946: ["richmond1947", "sanquentin1948"]}),
    "palo_alto": dict(name="Palo Alto (incl. Mayfield)", places=["0655282"], bbox=(-122.19, 37.40, -122.10, 37.465),
                      snaps={1895: ["paloalto1899"], 1940: ["paloalto1943"],
                             1948: ["paloalto1953", "mountainview1953"]}),
    "redwood_city": dict(name="Redwood City", places=["0660102"], bbox=(-122.27, 37.45, -122.19, 37.51),
                         snaps={1895: ["paloalto1899"], 1940: ["paloalto1943"],
                                1948: ["paloalto1953", "woodside1953", "redwoodpoint1948"]}),
    "san_mateo": dict(name="San Mateo (incl. Burlingame)", places=["0668252", "0609066"],
                      bbox=(-122.39, 37.52, -122.28, 37.60),
                      snaps={1892: ["sanmateo1896"], 1914: ["sanmateo1915"], 1939: ["sanmateo1943"],
                             1946: ["sanmateo1947"]}),
    "san_rafael": dict(name="San Rafael", places=["0668364"], bbox=(-122.57, 37.95, -122.48, 38.01),
                       snaps={1895: ["tamalpais1897", "sf1895"], 1939: ["tamalpais1941"],
                              1952: ["sanrafael1954", "sanquentin1948"]}),
    "martinez": dict(name="Martinez", places=["0646114"], bbox=(-122.16, 37.99, -122.10, 38.03),
                     snaps={1896: ["karquines1898"], 1940: ["carquinezstrait1940"],
                            1948: ["benicia1950", "briones1947", "portchicago1951"]}),
}


SMALL = ("small town drawn house by house on this sheet: only its densest core passes the built-up threshold; "
         "most houses of the time stand in the _partial area or outside both")
NOTES = {
    ("oakland", 1939): dict(note="east of 122°15' W and south of 37°45' N only (no 1940s edition of the San Francisco "
                                 "15' quadrangle)"),
    ("berkeley", 1894): dict(note="a college town of scattered houses: West Berkeley (Ocean View) and the blocks south "
                                  "and west of the campus"),
    ("richmond", 1894): dict(confidence="low", note="before Richmond (founded 1905): a few houses at Stege and along "
                                                    "San Pablo Avenue, partly road ink"),
    ("san_leandro", 1896): dict(confidence="low", note=SMALL), ("san_leandro", 1914): dict(confidence="low", note=SMALL),
    ("hayward", 1896): dict(confidence="low", note=SMALL), ("hayward", 1914): dict(confidence="low", note=SMALL),
    ("hayward", 1939): dict(note="no tint over Hayward on Hayward 1942: read house by house"),
    ("san_leandro", 1939): dict(note="no tint over San Leandro on Hayward 1942: read house by house"),
    ("hayward", 1946): dict(confidence="medium", note="Hayward 1947 tints only part of the town; the rest is read "
                                                      "house by house"),
    ("palo_alto", 1895): dict(confidence="low", note=SMALL), ("redwood_city", 1895): dict(confidence="low", note=SMALL),
    ("san_mateo", 1892): dict(confidence="low", note=SMALL + "; the lettering SAN MATEO adds a few blocks"),
    ("san_mateo", 1914): dict(confidence="low", note=SMALL + "; culture revised only in part in 1914"),
    ("martinez", 1896): dict(confidence="low", note=SMALL),
    ("san_rafael", 1939): dict(note="Tamalpais 1941 covers west of 122°30' only; houses drawn, no tint"),
    ("martinez", 1940): dict(note="houses drawn, no tint (Carquinez Strait 1940)"),
}
# ---- the older towns of the ten-county extent (2026-11)
TOWNS.update({
    "santa_rosa": dict(name="Santa Rosa", places=["0670098"], bbox=(-122.75, 38.405, -122.665, 38.475),
                       snaps={1914: ["santarosa1916"], 1942: ["santarosa1944"], 1952: ["santarosa1954"]}),
    "petaluma": dict(name="Petaluma", places=["0656784"], bbox=(-122.68, 38.205, -122.59, 38.275),
                     snaps={1912: ["petaluma1914"], 1952: ["petaluma1953", "petalumacreek1954"]}),
    "napa": dict(name="Napa", places=["0650258"], bbox=(-122.33, 38.27, -122.25, 38.34),
                 snaps={1899: ["napa1902"], 1939: ["sonoma1942"], 1948: ["napa1951"]}),
    "vallejo": dict(name="Vallejo", places=["0681666"], bbox=(-122.30, 38.07, -122.20, 38.15),
                    snaps={1899: ["napa1902"], 1914: ["mareisland1916"],
                           1940: ["carquinezstrait1940"], 1948: ["mareisland1949", "benicia1950"]}),
    "santa_cruz": dict(name="Santa Cruz", places=["0669112"], bbox=(-122.07, 36.945, -121.98, 37.005),
                       snaps={1899: ["santacruz1902"], 1952: ["santacruz1954", "soquel1954"]}),
    "watsonville": dict(name="Watsonville", places=["0683668"], bbox=(-121.80, 36.89, -121.73, 36.94),
                        snaps={1915: ["capitola1914", "sanjuanbautista1917"],
                               1939: ["capitola1940", "sanjuanbautista1940"],
                               1952: ["watsonvillewest1954", "watsonvilleeast1955"]}),
    "benicia": dict(name="Benicia", places=["0605290"], bbox=(-122.19, 38.04, -122.12, 38.085),
                    snaps={1896: ["karquines1898"], 1940: ["carquinezstrait1940"], 1948: ["benicia1950"]}),
    "sonoma": dict(name="Sonoma", places=["0672646"], bbox=(-122.49, 38.27, -122.43, 38.315),
                   snaps={1939: ["sonoma1942"], 1948: ["sonoma1951"]}),
    "healdsburg": dict(name="Healdsburg", places=["0633056"], bbox=(-122.90, 38.59, -122.84, 38.64),
                       snaps={1915: ["healdsburg1920"], 1933: ["healdsburg1940"],
                              1953: ["healdsburg1955", "guerneville1955"]}),
    "sebastopol": dict(name="Sebastopol", places=["0670770"], bbox=(-122.85, 38.385, -122.80, 38.42),
                       snaps={1935: ["sebastopol1942"], 1952: ["sebastopol1954"]}),
    "st_helena": dict(name="St. Helena", places=["0664140"], bbox=(-122.50, 38.485, -122.44, 38.53),
                      snaps={1942: ["sonoma1942", "sthelena1945"],
                             1957: ["rutherford1951", "sthelena1960"]}),
    "calistoga": dict(name="Calistoga", places=["0609892"], bbox=(-122.61, 38.56, -122.55, 38.60),
                      snaps={1915: ["calistoga1927"], 1943: ["calistoga1945"], 1957: ["calistoga1958"]}),
    "fairfield": dict(name="Fairfield - Suisun City", places=["0623182", "0675630"],
                      bbox=(-122.08, 38.225, -122.00, 38.275),
                      snaps={1896: ["karquines1898"], 1940: ["carquinezstrait1940", "mtvaca1942"],
                             1948: ["fairfieldsouth1949", "fairfieldnorth1951"]}),
    "vacaville": dict(name="Vacaville", places=["0681554"], bbox=(-122.02, 38.335, -121.95, 38.38),
                      snaps={1906: ["vacaville1908"], 1939: ["vacaville1941", "mtvaca1942"],
                             1949: ["elmira1953", "fairfieldnorth1951"]}),
    "dixon": dict(name="Dixon", places=["0619402"], bbox=(-121.85, 38.43, -121.80, 38.465),
                  snaps={1906: ["vacaville1908"], 1939: ["vacaville1941"], 1949: ["dixon1952"]}),
    "rio_vista": dict(name="Rio Vista", places=["0660984"], bbox=(-121.72, 38.14, -121.67, 38.18),
                      snaps={1908: ["riovista1910"], 1949: ["riovista1953"]}),
    "gilroy": dict(name="Gilroy", places=["0629504"], bbox=(-121.61, 36.985, -121.54, 37.03),
                   snaps={1915: ["morganhill1917", "sanjuanbautista1917"],
                          1939: ["morganhill1941", "sanjuanbautista1940"], 1953: ["gilroy1955", "chittenden1955"]}),
    "morgan_hill": dict(name="Morgan Hill", places=["0649278"], bbox=(-121.68, 37.105, -121.62, 37.155),
                        snaps={1915: ["morganhill1917"], 1939: ["morganhill1941"],
                               1953: ["morganhill1955", "mtmadonna1955"]}),
    "antioch": dict(name="Antioch", places=["0602252"], bbox=(-121.85, 37.985, -121.77, 38.03),
                    snaps={1907: ["antioch1908"], 1949: ["antiochnorth1953"]}),
    "pittsburg": dict(name="Pittsburg", places=["0657456"], bbox=(-121.92, 38.0, -121.85, 38.045),
                      snaps={1907: ["antioch1908"], 1949: ["honkerbay1953", "antiochnorth1953"]}),
    "brentwood": dict(name="Brentwood", places=["0608142"], bbox=(-121.72, 37.915, -121.67, 37.95),
                      snaps={1940: ["byron1940"], 1949: ["brentwood1954"]}),
    "cloverdale": dict(name="Cloverdale", places=["0614190"], bbox=(-123.04, 38.785, -122.99, 38.825),
                       snaps={1922: ["hopland1938"], 1942: ["hopland1944"], 1957: ["cloverdale1960"]}),
    "capitola": dict(name="Capitola - Soquel", places=["0611040", "0672688"], bbox=(-121.98, 36.965, -121.93, 37.005),
                     snaps={1912: ["capitola1914"], 1938: ["capitola1940"], 1952: ["soquel1954"]}),
    "boulder_creek": dict(name="Boulder Creek - Felton (San Lorenzo Valley: also Ben Lomond, Brookdale)",
                          places=["0607652", "0623826", "0605332", "0608478"], bbox=(-122.14, 37.03, -122.05, 37.14),
                          snaps={1899: ["santacruz1902"], 1953: ["felton1955", "castlerockridge1955", "bigbasin1955"]}),
})

for (t_, y_), v_ in NOTES.items():
    TOWNS[t_].setdefault("notes", {})[y_] = v_


# --------------------------------------------------------------------------- frames
_T = {}


def tf(a, b):
    import pyproj
    if (a, b) not in _T:
        _T[(a, b)] = pyproj.Transformer.from_crs(a, b, always_xy=True)
    return _T[(a, b)]


def nad27_tfs(crs_wkt):
    """WGS84 -> NAD27 geographic (NADCON) and NAD27 geographic -> the sheet's projection."""
    import pyproj
    from pyproj.transformer import TransformerGroup
    key = ("nad27", crs_wkt)
    if key not in _T:
        pyproj.datadir.append_data_dir(str(PROJ_DIR))
        crs = pyproj.CRS.from_wkt(crs_wkt)
        geo = crs.geodetic_crs
        tg = TransformerGroup("EPSG:4326", geo, always_xy=True,
                              area_of_interest=pyproj.aoi.AreaOfInterest(-123.7, 36.5, -121.0, 39.1))
        _T[key] = (tg.transformers[0], pyproj.Transformer.from_crs(geo, crs, always_xy=True))
    return _T[key]


class Grid:
    def __init__(self, bbox_ll, res=RES):
        t = tf("EPSG:4326", UTM)
        w, s, e, n = bbox_ll
        xs, ys = t.transform([w, e, w, e], [s, s, n, n])
        self.res = res
        self.x0 = math.floor(min(xs) / res) * res
        self.y1 = math.ceil(max(ys) / res) * res
        self.W = int(math.ceil((max(xs) - self.x0) / res))
        self.H = int(math.ceil((self.y1 - min(ys)) / res))

    def xy(self, i, j):
        return self.x0 + (np.asarray(i) + 0.5) * self.res, self.y1 - (np.asarray(j) + 0.5) * self.res

    @property
    def transform(self):
        from rasterio.transform import Affine
        return Affine(self.res, 0, self.x0, 0, -self.res, self.y1)


def render(sh, grid, model=None, step=16, pdf_step=1):
    """Sheet resampled into the grid (RGB uint8, white outside) + inside-quad mask. model: shift
    (dX, dY) in m added to a modern position to find it on the map. Reads the GeoPDF scan through
    its own registration (topo_farmsteads.GeoPDF: LGIDict CTM, polyconic NAD27)."""
    import cv2
    sys.path.insert(0, str(ROOT / "pipeline"))
    import topo_farmsteads as TF
    path = sheet_path(sh)
    pdf = TF.GeoPDF(path)
    crs = TF.crs_for(pdf.g["proj"])
    a_, b_, c_, d_, e_, f_ = pdf.g["georef"]["ctm"]
    s_, page_h = pdf.g["georef"]["s"], pdf.g["georef"]["page_h"]
    Ainv = np.linalg.inv(np.array([[a_, c_], [b_, d_]]))
    ci = np.arange(0, grid.W + step, step)
    cj = np.arange(0, grid.H + step, step)
    X, Y = np.meshgrid(*grid.xy(ci, cj))
    if model is not None:
        dX, dY = shift_xy(model, X, Y)
        X, Y = X + dX, Y + dY
    lon, lat = tf(UTM, "EPSG:4326").transform(X, Y)
    t_ll, t_pr = nad27_tfs(crs.to_wkt())
    lo27, la27 = t_ll.transform(lon, lat)
    lo27 = np.asarray(lo27); la27 = np.asarray(la27)
    w, s, e, n = sh["quad"]
    inq = ((lo27 >= w) & (lo27 <= e) & (la27 >= s) & (la27 <= n)).astype(np.float32)
    px, py = t_pr.transform(lo27, la27)
    uv = Ainv @ np.vstack([np.asarray(px).ravel() - e_, np.asarray(py).ravel() - f_])
    col = (uv[0] * s_).reshape(X.shape).astype(np.float32)
    row = ((page_h - uv[1]) * s_).reshape(X.shape).astype(np.float32)
    ok = inq > 0
    if not ok.any():
        return None, None
    c0 = int(max(0, np.floor(col[ok].min()) - 4)); c1 = int(min(pdf.W, np.ceil(col[ok].max()) + 4))
    r0 = int(max(0, np.floor(row[ok].min()) - 4)); r1 = int(min(pdf.H, np.ceil(row[ok].max()) + 4))
    arr = np.ascontiguousarray(pdf.read(r0, r1, c0, c1, step=pdf_step))
    pdf._cache.clear()
    pdf.doc.close()
    del pdf
    col = (col - c0) / pdf_step; row = (row - r0) / pdf_step
    img = np.full((grid.H, grid.W, 3), 255, np.uint8)
    valid = np.zeros((grid.H, grid.W), bool)
    ii = (np.arange(grid.W, dtype=np.float32) / step)
    for j0 in range(0, grid.H, 1024):
        j1 = min(grid.H, j0 + 1024)
        jj = (np.arange(j0, j1, dtype=np.float32) / step)
        mx = np.ascontiguousarray(np.broadcast_to(ii[None, :], (j1 - j0, grid.W)))
        my = np.ascontiguousarray(np.broadcast_to(jj[:, None], (j1 - j0, grid.W)))
        cf = cv2.remap(col, mx, my, cv2.INTER_LINEAR)
        rf = cv2.remap(row, mx, my, cv2.INTER_LINEAR)
        img[j0:j1] = cv2.remap(arr, cf, rf, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                               borderValue=(255, 255, 255))
        valid[j0:j1] = cv2.remap(inq, mx, my, cv2.INTER_LINEAR) > 0.5
    img[~valid] = 255
    return img, valid


def shift_xy(m, X, Y):
    if not m or not m.get("aligned"):
        return np.zeros_like(X), np.zeros_like(Y)
    xk = (X - m["xc"]) / 1000.0
    yk = (Y - m["yc"]) / 1000.0
    return (m["cx"][0] + m["cx"][1] * xk + m["cx"][2] * yk,
            m["cy"][0] + m["cy"][1] * xk + m["cy"][2] * yk)


# --------------------------------------------------------------------------- ink / tint
def _strips(img, fn):
    out = np.zeros(img.shape[:2], bool)
    for j0 in range(0, img.shape[0], 1024):
        out[j0:j0 + 1024] = fn(img[j0:j0 + 1024].astype(np.int16))
    return out


def ink_mask(img, style):
    """Black ink: dark in every channel and neutral (contours are brown, water blue, tint pink)."""
    mx = img[::7, ::7].max(2)
    paper = np.percentile(mx[mx > 150], 60) if (mx > 150).any() else 235

    def f(b):
        R, G, B = b[:, :, 0], b[:, :, 1], b[:, :, 2]
        return (b.max(2) < 0.55 * paper) & (np.abs(R - G) < 45) & (B - R < 25) & (G - R < 25)
    return _strips(img, f)


def tint_mask(img, kind, res, scale):
    """Urban-area tint of the 1939-53 sheets: 'pink' (red / pink screen of the 1:24,000 sheets, as
    topo_farmsteads.urban_tint) or 'grey' (the grey-tan built-up tint of the 1939-43 1:62,500
    editions). A majority over ~0.8 mm on paper drops the anti-aliased edges of lines."""
    import cv2
    mx = img[::7, ::7].astype(np.int16).sum(2)
    paper = np.percentile(mx[mx > 450], 95) if (mx > 450).any() else 700

    # light pink / salmon ground + red dot screen; the paper is white to yellowish (R - G 0-6 on every
    # 1:24,000 sheet used, from the sheets' R - G histograms), woodland green, contours thin orange
    # a scan with a reddish cast (Dixon 1952, Elmira 1953: paper R - G ~ 12-20) is not tinted: on those the
    # tint must stand 8 above the paper (20th percentile of R - G over the bright, non-green pixels)
    sub = img[::7, ::7].astype(np.int16)
    br = sub.sum(2)
    pp = sub[(br > 0.85 * paper) & (br < 765) & (sub[:, :, 0] - sub[:, :, 1] >= -3)]     # 765: outside the sheet
    rg0 = float(np.percentile(pp[:, 0] - pp[:, 1], 20)) if len(pp) > 100 else 0.0
    rg_min = 10.0 if rg0 <= 6 else rg0 + 8.0

    def pink(b):
        R, G, B = b[:, :, 0], b[:, :, 1], b[:, :, 2]
        return (R - G > rg_min) & (R > 195) & (B > 100) & (G - B < 50)

    def grey(b):
        R, G, B = b[:, :, 0], b[:, :, 1], b[:, :, 2]
        return ((R > 150) & (R < 235) & (R - G >= -3) & (R - G < 27) & (G - B > 3) & (G - B < 42)
                & (R + G + B < paper - 55))
    m = _strips(img, pink if kind == "pink" else grey).astype(np.float32)
    k = max(3, int(round(0.8 * scale / 1000.0 / res)) | 1)
    m = (cv2.blur(m, (k, k)) > (0.35 if kind == "pink" else 0.45)).astype(np.uint8)
    r = max(1, int(round(0.3 * scale / 1000.0 / res)))      # drop strips along road lines (< 0.6 mm wide)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1,) * 2))
    return m.astype(bool)


def line_kernels(length_px, n=12):
    import cv2
    ks = []
    L = int(length_px) | 1
    for k in range(n):
        a = math.pi * k / n
        m = np.zeros((L, L), np.uint8)
        c = L // 2
        dx, dy = math.cos(a) * c, math.sin(a) * c
        cv2.line(m, (int(round(c - dx)), int(round(c - dy))), (int(round(c + dx)), int(round(c + dy))), 1, 1)
        ks.append(m)
    return ks


def heavy_and_bands(ink, res, sh):
    """Heavy ink (thin lines removed) and its elongated part (bands: built frontage)."""
    import cv2
    mm = sh["scale"] / 1000.0                 # metres per paper mm
    # remove lines thinner than ~0.15 mm; open_mm 0.26 on the editions of 1915-45 and the 1:125,000 sheets, whose
    # street lines / casings are heavier (0.15-0.2 mm: every platted block would read as a built front)
    r_open = max(1, int(round(sh.get("open_mm", 0.15) * mm / res / 2)))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r_open + 1,) * 2)
    heavy = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_OPEN, k)
    L = 40.0 / res if sh["scale"] >= 62500 else 30.0 / res
    bands = np.zeros_like(heavy)
    for kk in line_kernels(L):
        bands |= cv2.morphologyEx(heavy, cv2.MORPH_OPEN, kk)
    return heavy.astype(bool), bands.astype(bool)


# --------------------------------------------------------------------------- vectors
def town_clip(town):
    import geopandas as gpd
    import shapely
    pl = gpd.read_file(f"zip://{TIGER}")
    pl = pl[pl.GEOID.isin(TOWNS[town]["places"])].to_crs(UTM)
    g = shapely.union_all(list(pl.geometry)).buffer(0)
    w, s, e, n = TOWNS[town]["bbox"]
    box = shapely.box(*tf("EPSG:4326", UTM).transform(w, s), *tf("EPSG:4326", UTM).transform(e, n))
    return g.intersection(box)


def land_poly(bounds):
    """Today's land within bounds (UTM): the box minus TIGER 2024 area water (bay, lakes, reservoirs,
    salt ponds) of the five counties."""
    import geopandas as gpd
    import shapely
    box = shapely.box(*bounds)
    ll = to_ll(box).bounds
    ws = []
    for c in ("06001", "06013", "06041", "06081", "06085", "06055", "06095", "06097", "06087"):
        zp = ROOT / "data" / "raw" / "tiger" / f"tl_2024_{c}_areawater.zip"
        if not zp.exists():
            import subprocess
            subprocess.run(["curl", "-sS", "-L", "-m", "300", "-o", str(zp),
                            f"https://www2.census.gov/geo/tiger/TIGER2024/AREAWATER/{zp.name}"], check=True)
        w = gpd.read_file(f"zip://{zp}", bbox=tuple(ll))
        if len(w):
            ws += list(w.to_crs(UTM).geometry)
    water = shapely.union_all(ws).buffer(0) if ws else shapely.Polygon()
    return box.difference(water)


def to_utm(g):
    import shapely
    t = tf("EPSG:4326", UTM)
    return shapely.transform(g, lambda c: np.column_stack(t.transform(c[:, 0], c[:, 1])))


def modern_roads(bounds_ll, classes=None):
    import duckdb
    import shapely
    w, s, e, n = bounds_ll
    out = []
    con = duckdb.connect()
    con.execute("LOAD spatial;")
    for f in ("roads_local", "roads_region"):
        q = (f"select class, ST_AsWKB(geometry) g from read_parquet('{OVT / (f + '.parquet')}') "
             f"where ST_XMin(geometry) < {e} and ST_XMax(geometry) > {w} and ST_YMin(geometry) < {n} "
             f"and ST_YMax(geometry) > {s}")
        for cls, g in con.execute(q).fetchall():
            if classes and cls not in classes:
                continue
            out.append((cls, shapely.from_wkb(bytes(g))))
    return out


BLOCK_CLASSES = {"trunk", "primary", "secondary", "tertiary", "residential", "unclassified", "living_street"}


BIG_HA = 5.0       # blocks larger than this (hills, parks, yards, waterfront) are read in CELL_M cells
CELL_M = 100.0


def blocks(town, clip):
    """Today's street blocks (UTM polygons) inside the town clip, on today's land; blocks over
    BIG_HA split into CELL_M squares (kind = 'cell')."""
    import geopandas as gpd
    import shapely
    cache = INT / f"blocks_{town}.parquet"
    if cache.exists():
        return gpd.read_parquet(cache)
    w, s, e, n = TOWNS[town]["bbox"]
    lines = [to_utm(g) for c, g in modern_roads((w - .01, s - .01, e + .01, n + .01), BLOCK_CLASSES)]
    lines.append(clip.boundary)
    net = shapely.union_all(lines)
    polys = list(shapely.get_parts(shapely.polygonize(shapely.get_parts(net))))
    polys = [p for p in polys if p.area > 200 and clip.contains(p.representative_point())]
    land = land_poly(clip.bounds)
    out, kind = [], []
    for p in polys:
        p = p.intersection(clip).intersection(land)
        for q in shapely.get_parts(p):
            if q.geom_type != "Polygon" or q.area <= 200:
                continue
            if q.area <= BIG_HA * 1e4:
                out.append(q); kind.append("block")
                continue
            x0, y0, x1, y1 = q.bounds
            for gx in np.arange(math.floor(x0 / CELL_M) * CELL_M, x1, CELL_M):
                for gy in np.arange(math.floor(y0 / CELL_M) * CELL_M, y1, CELL_M):
                    c = q.intersection(shapely.box(gx, gy, gx + CELL_M, gy + CELL_M))
                    for cc in shapely.get_parts(c):
                        if cc.geom_type == "Polygon" and cc.area > 200:
                            out.append(cc); kind.append("cell")
    g = gpd.GeoDataFrame({"bid": np.arange(len(out)), "kind": kind}, geometry=out, crs=UTM)
    g.to_parquet(cache)
    return g


# --------------------------------------------------------------------------- alignment
def align_sheet(key):
    """Shift of a whole sheet against today's street centrelines (model: modern position + shift =
    map position), by cross-correlation of its black ink with rasterised centrelines in 2.5 km
    windows over the quadrangle (5 m pixels). Cached per sheet."""
    INT.mkdir(parents=True, exist_ok=True)
    p = INT / f"align_{key}.json"
    if p.exists():
        return json.loads(p.read_text())
    sh = S[key]
    w, s, e, n = sh["quad"]
    grid = Grid((w - 0.003, s - 0.003, e + 0.003, n + 0.003), 5.0)
    img, valid = render(sh, grid, None, pdf_step=2)
    ink = ink_mask(img, sh["style"]).astype(np.float32)
    del img
    m = align(sh, grid, ink, valid, (w, s, e, n))
    p.write_text(json.dumps(m, indent=1))
    return m


def align(sh, grid, small, vs, bounds_ll):
    import cv2
    res = grid.res
    rr = np.zeros(small.shape, np.uint8)
    w, s, e, n = bounds_ll
    for cls, g in modern_roads((w - .01, s - .01, e + .01, n + .01),
                               {"primary", "secondary", "tertiary", "residential", "unclassified", "trunk"}):
        g = to_utm(g)
        for line in getattr(g, "geoms", [g]):
            c = np.asarray(line.coords)
            px = np.column_stack([(c[:, 0] - grid.x0) / res, (grid.y1 - c[:, 1]) / res])
            cv2.polylines(rr, [np.round(px).astype(np.int32)], False, 1, 1)
    Rb = cv2.GaussianBlur(rr.astype(np.float32), (0, 0), 1.5)
    Ib = cv2.GaussianBlur(small, (0, 0), 1.5)
    early = sh["style"] == "early"
    win = int(2500 / res)
    S_ = int((420 if early else 120) / res)
    sup = max(2, int(50 / res))
    rows = []
    for y in range(S_, Ib.shape[0] - win - S_, win // 2):
        for x in range(S_, Ib.shape[1] - win - S_, win // 2):
            if vs[y:y + win, x:x + win].mean() < 0.9:
                continue
            tpl = Rb[y:y + win, x:x + win]
            if tpl.sum() < 3 * win or Ib[y:y + win, x:x + win].sum() < 3 * win:
                continue
            cc = cv2.matchTemplate(Ib[y - S_:y + win + S_, x - S_:x + win + S_], tpl, cv2.TM_CCOEFF_NORMED)
            _, r1, _, (lx, ly) = cv2.minMaxLoc(cc)
            cc2 = cc.copy()
            cc2[max(ly - sup, 0):ly + sup + 1, max(lx - sup, 0):lx + sup + 1] = -1
            r2 = cc2.max()
            if r1 >= 0.12 and r1 - r2 >= 0.015:
                X, Y = grid.x0 + (x + win / 2) * res, grid.y1 - (y + win / 2) * res
                rows.append((X, Y, (lx - S_) * res, -(ly - S_) * res, r1, r1 - r2))
    out = {"n_windows": len(rows), "windows": [[round(float(v), 2) for v in r] for r in rows]}
    if len(rows) < 2:
        out.update(aligned=False, reason="too few windows")
        return out
    A = np.array(rows)
    tol = 40.0 if early else 12.0
    best_w, use = -1, None
    for k in range(len(A)):
        inl = np.hypot(A[:, 2] - A[k, 2], A[:, 3] - A[k, 3]) <= 2 * tol
        wsum = A[inl, 4].sum()
        if wsum > best_w:
            best_w, use = wsum, inl
    # (mountain sheets: most windows match contours, not streets; 8+ windows agreeing within 2 tol out of a
    # +-420 m search cannot be chance)
    if use.sum() < 2 or (use.sum() < 0.35 * len(A) and use.sum() < 8):
        out.update(aligned=False, reason=f"no consensus ({int(use.sum())} of {len(A)})")
        return out
    xc, yc = A[use, 0].mean(), A[use, 1].mean()
    Xm = np.column_stack([np.ones(len(A)), (A[:, 0] - xc) / 1000, (A[:, 1] - yc) / 1000])
    cx = np.array([np.median(A[use, 2]), 0, 0]); cy = np.array([np.median(A[use, 3]), 0, 0])
    model = "constant"
    for _ in range(6):
        if use.sum() >= 6 and np.ptp(A[use, 0]) > 3000 and np.ptp(A[use, 1]) > 3000:
            ax, *_ = np.linalg.lstsq(Xm[use], A[use, 2], rcond=None)
            ay, *_ = np.linalg.lstsq(Xm[use], A[use, 3], rcond=None)
            if np.abs(ax[1:]).max() < 25 and np.abs(ay[1:]).max() < 25:     # < 25 m per km
                cx, cy, model = ax, ay, "affine"
        resid = np.hypot(A[:, 2] - Xm @ cx, A[:, 3] - Xm @ cy)
        new = resid <= tol
        if (new == use).all() or new.sum() < 2:
            break
        use = new
    resid = np.hypot(A[:, 2] - Xm @ cx, A[:, 3] - Xm @ cy)
    out.update(aligned=True, model=model, xc=float(xc), yc=float(yc), cx=[float(v) for v in cx],
               cy=[float(v) for v in cy], n_used=int(use.sum()),
               rms_m=round(float(np.sqrt(np.mean(resid[use] ** 2))), 1),
               shift_m=round(float(np.hypot(cx[0], cy[0])), 1))
    return out


def align_local(town, key):
    """Fallback for sheets whose quadrangle has too few streets for the windowed fit (mountain sheets:
    Hopland 1938): one constant shift from the town itself (its box + 600 m, 5 m pixels), accepted
    when the correlation peak is distinct. Cached per sheet and town."""
    import cv2
    p = INT / f"align_{key}_{town}.json"
    if p.exists():
        return json.loads(p.read_text())
    sh = S[key]
    w, s, e, n = TOWNS[town]["bbox"]
    bb = (w - 0.007, s - 0.0055, e + 0.007, n + 0.0055)
    grid = Grid(bb, 5.0)
    out = {"aligned": False, "reason": "local: no distinct peak", "n_windows": 1}
    img, valid = render(sh, grid, None, pdf_step=2)
    if img is not None:
        ink = ink_mask(img, sh["style"]).astype(np.float32)
        rr = np.zeros(ink.shape, np.uint8)
        for cls, g in modern_roads(bb, {"primary", "secondary", "tertiary", "residential", "unclassified", "trunk"}):
            g = to_utm(g)
            for line in getattr(g, "geoms", [g]):
                c = np.asarray(line.coords)
                px = np.column_stack([(c[:, 0] - grid.x0) / grid.res, (grid.y1 - c[:, 1]) / grid.res])
                cv2.polylines(rr, [np.round(px).astype(np.int32)], False, 1, 1)
        Rb = cv2.GaussianBlur(rr.astype(np.float32), (0, 0), 1.5)
        Ib = cv2.GaussianBlur(ink, (0, 0), 1.5)
        S_ = int((420 if sh["style"] == "early" else 120) / grid.res)
        if min(Rb.shape) > 2 * S_ + 40:
            tpl = Rb[S_:-S_, S_:-S_]
            cc = cv2.matchTemplate(Ib, tpl, cv2.TM_CCOEFF_NORMED)
            _, r1, _, (lx, ly) = cv2.minMaxLoc(cc)
            sup = max(2, int(50 / grid.res))
            cc2 = cc.copy()
            cc2[max(ly - sup, 0):ly + sup + 1, max(lx - sup, 0):lx + sup + 1] = -1
            r2 = float(cc2.max())
            dX, dY = (lx - S_) * grid.res, -(ly - S_) * grid.res
            out.update(peak=round(float(r1), 3), second=round(r2, 3))
            if r1 >= 0.10 and r1 - r2 >= 0.015:
                out = {"aligned": True, "model": "constant (town window)", "xc": float(grid.x0 + grid.W * grid.res / 2),
                       "yc": float(grid.y1 - grid.H * grid.res / 2), "cx": [float(dX), 0.0, 0.0],
                       "cy": [float(dY), 0.0, 0.0], "n_windows": 1, "n_used": 1, "rms_m": None,
                       "shift_m": round(float(np.hypot(dX, dY)), 1), "peak": round(float(r1), 3), "second": round(r2, 3)}
    p.write_text(json.dumps(out, indent=1))
    return out


# --------------------------------------------------------------------------- per sheet
TINT_OPEN_MM = 0.9
NEAT_MM = 0.5      # ink this close to the quadrangle edge (neat line, ticks) is not read

# mask codes (one uint8 PNG per town and sheet in data/interim): which pixels are what
M_VALID, M_HEAVY, M_BAND, M_TINT, M_SQ, M_SKEL = 1, 2, 4, 8, 16, 32


def masks(town, key, preview=False):
    """Render + align one sheet over a town -> code image (cached PNG) with valid / heavy ink / band /
    tint / house-square centre / band skeleton bits."""
    import cv2
    INT.mkdir(parents=True, exist_ok=True)
    cache = INT / f"mask_{town}_{key}.png"
    if cache.exists() and not preview:
        return cv2.imread(str(cache), cv2.IMREAD_UNCHANGED)
    sh = S[key]
    grid = Grid(TOWNS[town]["bbox"])
    model = align_sheet(key)
    if not model.get("aligned"):
        model = align_local(town, key)
    print(key, "align", {k: model.get(k) for k in ("aligned", "model", "n_windows", "n_used", "rms_m", "shift_m", "reason")})
    if sh["style"] == "tint" and model.get("aligned") and model.get("shift_m", 0) < 6:
        model = None                        # accurate 1:24,000 sheets: as published
    img, valid = render(sh, grid, model)
    if img is None:
        code = np.zeros((grid.H, grid.W), np.uint8)
        cv2.imwrite(str(cache), code)
        return code
    ink = ink_mask(img, sh["style"])
    heavy, bands = heavy_and_bands(ink, grid.res, sh)
    del ink
    tint = (tint_mask(img, sh.get("tint", "pink"), grid.res, sh["scale"]) if sh["style"] == "tint"
            else np.zeros_like(heavy))
    print(key, "tinted share of the area read", round(float(tint[valid].mean()), 3) if valid.any() else 0)
    if preview:
        pv = img.copy()
        pv[heavy & ~bands] = (0, 160, 255)
        pv[bands] = (255, 0, 0)
        if sh["style"] == "tint":
            pv[tint & ~heavy] = (255, 190, 120)
        cv2.imwrite(str(INT / f"pv_{town}_{key}.jpg"), pv[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 80])
        del pv
    del img
    code = (valid * M_VALID | heavy * M_HEAVY | bands * M_BAND | tint * M_TINT).astype(np.uint8)
    # squares: compact heavy-ink components not part of a band -> one centre pixel each
    sq = heavy & ~cv2.dilate(bands.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    nl, cl, st, cen = cv2.connectedComponentsWithStats(sq.astype(np.uint8), 8)
    del cl, sq
    mm = sh["scale"] / 1000.0
    amin = (0.25 * mm) ** 2 / grid.res ** 2           # >= 0.25 x 0.25 mm on paper
    ok = (st[1:, cv2.CC_STAT_AREA] >= amin)
    ci = np.clip(np.round(cen[1:, 0]).astype(int), 0, grid.W - 1)[ok]
    cj = np.clip(np.round(cen[1:, 1]).astype(int), 0, grid.H - 1)[ok]
    code[cj, ci] |= M_SQ
    from skimage.morphology import skeletonize
    code[skeletonize(bands)] |= M_SKEL
    cv2.imwrite(str(cache), code)
    return code


NEAR_M = 60.0      # band / square ink further than this from today's streets is not counted


_NEAR = {}


def street_near(town, grid):
    """Pixels within NEAR_M of a street centreline of today (the block-forming classes)."""
    import cv2
    if town in _NEAR:
        return _NEAR[town]
    w, s, e, n = TOWNS[town]["bbox"]
    rr = np.full((grid.H, grid.W), 255, np.uint8)
    for cls, g in modern_roads((w - .01, s - .01, e + .01, n + .01), BLOCK_CLASSES | {"service"}):
        g = to_utm(g)
        for line in getattr(g, "geoms", [g]):
            c = np.asarray(line.coords)
            px = np.column_stack([(c[:, 0] - grid.x0) / grid.res, (grid.y1 - c[:, 1]) / grid.res])
            cv2.polylines(rr, [np.round(px).astype(np.int32)], False, 0, 1)
    d = cv2.distanceTransform(rr, cv2.DIST_L2, 5)
    near = d <= NEAR_M / grid.res
    del d, rr
    # railways (today's, Overture; and vanished ones, data/manual/historic_rail.geojson) are drawn as
    # heavy lines on the early sheets: ink within RAIL_M of a railway is not counted
    rl = np.zeros((grid.H, grid.W), np.uint8)
    th = max(1, int(round(2 * RAIL_M / grid.res)))
    for g in railways((w - .01, s - .01, e + .01, n + .01)):
        g = to_utm(g)
        for line in getattr(g, "geoms", [g]):
            c = np.asarray(line.coords)
            px = np.column_stack([(c[:, 0] - grid.x0) / grid.res, (grid.y1 - c[:, 1]) / grid.res])
            cv2.polylines(rl, [np.round(px).astype(np.int32)], False, 1, th)
    near &= rl == 0
    del rl
    rm = np.zeros((grid.H, grid.W), np.uint8)
    # freeways: the heavy highway symbol of the 1930s-50s sheets (Bayshore, Eastshore) is not frontage;
    # on the earlier sheets the ground under today's freeways was ordinary blocks, so they keep it
    thm = max(1, int(round(2 * MOTORWAY_M / grid.res)))
    for cls, g in modern_roads((w - .01, s - .01, e + .01, n + .01), {"motorway"}):
        g = to_utm(g)
        for line in getattr(g, "geoms", [g]):
            c = np.asarray(line.coords)
            px = np.column_stack([(c[:, 0] - grid.x0) / grid.res, (grid.y1 - c[:, 1]) / grid.res])
            cv2.polylines(rm, [np.round(px).astype(np.int32)], False, 1, thm)
    _NEAR[town] = (near, near & (rm == 0))
    return _NEAR[town]


RAIL_M = 12.0
MOTORWAY_M = 25.0


def railways(bounds_ll):
    import duckdb
    import geopandas as gpd
    import shapely
    w, s, e, n = bounds_ll
    con = duckdb.connect()
    con.execute("LOAD spatial;")
    q = (f"select ST_AsWKB(geometry) g from read_parquet('{OVT / 'rail.parquet'}') where class in "
         f"('standard_gauge', 'narrow_gauge', 'unknown') and ST_XMin(geometry) < {e} and ST_XMax(geometry) > {w} "
         f"and ST_YMin(geometry) < {n} and ST_YMax(geometry) > {s}")
    out = [shapely.from_wkb(bytes(g)) for (g,) in con.execute(q).fetchall()]
    h = gpd.read_file(ROOT / "data" / "manual" / "historic_rail.geojson")
    h = h[h["mode"].isin(["rail", "narrow_gauge", "interurban"])].cx[w:e, s:n]
    return out + list(h.geometry)


def block_stats(town, key, preview=False):
    """Per block pixel counts of one sheet (cached; recomputed from the mask PNG when blocks change)."""
    import pandas as pd
    from rasterio import features
    cache = INT / f"stats_{town}_{key}.parquet"
    bl = blocks(town, town_clip(town))
    if cache.exists() and not preview:
        df = pd.read_parquet(cache)
        if len(df) == len(bl):
            return df
    code = masks(town, key, preview)
    grid = Grid(TOWNS[town]["bbox"])
    lab = features.rasterize(((g, i + 1) for i, g in enumerate(bl.geometry)), out_shape=(grid.H, grid.W),
                             transform=grid.transform, dtype="int32")
    n = len(bl) + 1
    import cv2
    r = max(1, int(round(NEAT_MM * S[key]["scale"] / 1000.0 / grid.res)))   # off the neat line and its ticks
    valid = cv2.erode(((code & M_VALID) > 0).astype(np.uint8),
                      cv2.getStructuringElement(cv2.MORPH_RECT, (2 * r + 1,) * 2)) > 0
    near = street_near(town, grid)[1 if S[key]["year"] >= 1925 else 0]   # ink near a street of today only
    tint = (code & M_TINT) > 0
    if S[key]["style"] == "tint":        # tint narrower than ~0.9 mm is road casing / fill, not a tinted block
        rt = max(1, int(round(TINT_OPEN_MM / 2 * S[key]["scale"] / 1000.0 / grid.res)))
        tint = cv2.morphologyEx(tint.astype(np.uint8), cv2.MORPH_OPEN,
                                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rt + 1,) * 2)) > 0
    cnt = lambda m: np.bincount(lab[m & valid], minlength=n)      # noqa: E731
    df = pd.DataFrame({"bid": bl.bid.values, "px": np.bincount(lab.ravel(), minlength=n)[1:],
                       "px_valid": cnt(np.ones_like(valid))[1:], "a_band": cnt(((code & M_BAND) > 0) & near)[1:],
                       "a_heavy": cnt(((code & M_HEAVY) > 0) & near)[1:], "a_tint": cnt(tint)[1:],
                       "n_sq": cnt(((code & M_SQ) > 0) & near)[1:], "skel": cnt(((code & M_SKEL) > 0) & near)[1:]})
    df["res"] = grid.res
    df.to_parquet(cache)
    return df


# --------------------------------------------------------------------------- classify / build
THRESH = {"early": 0.35, "tint": 0.35}   # built frontage share (early) / share under the urban tint
TINT_SHARE = 0.50
CELL_SHARE, CELL_HEAVY = 0.35, 0.20       # cells of big blocks
CELL_MIN_M2 = 3000.0
MIN_WIDTH_M = 20.0                        # narrower units (area / perimeter < 10 m) are not read on their own
MIN_COV = 0.3                             # a block is read when this share of it lies on the sheet(s)
SQ_FRONT_M = 15.0                         # frontage credited to one house square
HOLE_HA = 0.6                             # fill holes in the extent smaller than this
PARTIAL_SHARE = 0.12                      # partly built blocks (separate files)
MIN_HA = 2.0                              # drop isolated built specks smaller than this (a farm group, one cell)


def snapshot_stats(town, year):
    """Per block: summed sheet stats of one snapshot + shares."""
    import pandas as pd
    import shapely
    keys = TOWNS[town]["snaps"][year]
    clip = town_clip(town)
    bl = blocks(town, clip)
    tot = None
    for k in keys:
        df = block_stats(town, k)
        if df is None:
            continue
        df = df.set_index("bid")[["px", "px_valid", "a_band", "a_heavy", "a_tint", "n_sq", "skel"]]
        if tot is None:
            tot = df.copy()
        else:
            tot[["px_valid", "a_band", "a_heavy", "a_tint", "n_sq", "skel"]] += df[["px_valid", "a_band", "a_heavy", "a_tint", "n_sq", "skel"]]
    res = RES
    tot = tot.reindex(bl.bid.values)
    g = bl.set_index("bid").geometry
    inner = shapely.buffer(g.values, -15.0)
    P = np.where(shapely.is_empty(inner), 0.5 * shapely.length(g.values), shapely.length(inner))
    tot["front_m"] = P
    tot["cov"] = tot.px_valid / tot.px.clip(lower=1)
    t_band = tot.a_band.sum() * res * res / max(1.0, tot.skel.sum() * res)
    tot["band_m"] = tot.a_band * res * res / t_band
    fr = (tot.front_m * tot["cov"]).clip(lower=1)
    tot["share"] = ((tot.band_m + SQ_FRONT_M * tot.n_sq) / fr).clip(upper=1.5)
    tot["tint_share"] = tot.a_tint / tot.px_valid.clip(lower=1)
    style = S[keys[0]]["style"]
    tot["kind"] = bl.set_index("bid").kind.reindex(tot.index).values
    tot["heavy_frac"] = tot.a_heavy / tot.px_valid.clip(lower=1)
    # street blocks: built frontage share; cells of big blocks (yards, wharves, hills): a rail line or
    # two is not built-up, so also a minimum share of heavy ink
    # (a cell must be at least CELL_MIN_M2: the slivers of cells along a road are all road casing)
    cell_ok = (tot.kind == "cell") & (tot.px * res * res >= CELL_MIN_M2)
    # strips (between a road and a parallel road or the city limit) hold road casing, not frontage
    gg = bl.set_index("bid").geometry.reindex(tot.index)
    wide = (shapely.area(gg.values) / np.maximum(shapely.length(gg.values), 1.0)) >= MIN_WIDTH_M / 2
    built = (tot["cov"] >= MIN_COV) & wide & (((tot.kind == "block") & (tot.share >= THRESH[style]))
                                          | (cell_ok & (tot.share >= CELL_SHARE) & (tot.heavy_frac >= CELL_HEAVY)))
    if style == "tint":
        built |= (tot["cov"] >= MIN_COV) & (tot.tint_share >= TINT_SHARE)
    tot["built"] = built
    # partly built: at least ~3-4 houses drawn on the block (or a short built frontage), not built up
    tot["partial"] = ((tot["cov"] >= MIN_COV) & wide & ~built & (tot.share >= PARTIAL_SHARE)
                      & ((tot.kind == "block") | cell_ok))
    tot.attrs["t_band"] = t_band
    return bl, tot


def extent_polys(bl, tot, clip, col="built", exclude=None):
    import shapely
    g = bl.set_index("bid").geometry
    sel = list(g[tot[col].values].values)
    if not sel:
        return shapely.MultiPolygon()
    u = shapely.union_all(sel).buffer(12, join_style="mitre").buffer(-12, join_style="mitre")
    if exclude is not None:
        d = shapely.difference(shapely.make_valid(u).buffer(0), shapely.make_valid(exclude).buffer(0))
        u = shapely.union_all([q for q in shapely.get_parts(d) if q.geom_type == "Polygon"] or [shapely.Polygon()])
    parts = []
    for p in shapely.get_parts(u):
        if p.geom_type != "Polygon":
            continue

        def small(h):
            hp = shapely.Polygon(h)
            return hp.area < HOLE_HA * 1e4 or hp.area / max(hp.length, 1) < 10     # specks, street strips
        keep = [h for h in p.interiors if not small(h)]
        p = shapely.Polygon(p.exterior, keep)
        if p.area >= MIN_HA * 1e4:
            parts.append(p)
    u = shapely.union_all(parts) if parts else shapely.Polygon()
    land = land_poly(clip.bounds)
    u = u.intersection(land.buffer(30)).intersection(clip)
    u = shapely.make_valid(shapely.simplify(u, 1.0))
    polys = [p for p in shapely.get_parts(u) if p.geom_type == "Polygon" and p.area > 1]
    if not polys:
        polys += [q for p in shapely.get_parts(u) if p.geom_type in ("MultiPolygon", "GeometryCollection")
                  for q in shapely.get_parts(p) if q.geom_type == "Polygon"]
    return shapely.MultiPolygon(polys) if polys else shapely.MultiPolygon()


def coverage_poly(town, year, clip):
    import shapely
    t = tf("EPSG:4326", UTM)
    out = []
    for k in TOWNS[town]["snaps"][year]:
        w, s, e, n = S[k]["quad"]
        xs = np.r_[np.linspace(w, e, 20), np.full(20, e), np.linspace(e, w, 20), np.full(20, w)]
        ys = np.r_[np.full(20, s), np.linspace(s, n, 20), np.full(20, n), np.linspace(n, s, 20)]
        x, y = t.transform(xs, ys)
        out.append(shapely.Polygon(np.column_stack([x, y])))
    return shapely.union_all(out).intersection(clip)


def to_ll(g):
    import shapely
    t = tf(UTM, "EPSG:4326")
    return shapely.transform(g, lambda c: np.column_stack(t.transform(c[:, 0], c[:, 1])))


def default_confidence(keys):
    """high: 1:24,000 urban tint from aerial photographs; medium: the 1:62,500 sheets (band / square
    reading of the 1885-1915 surveys, ~15-25 m alignment RMS; grey tint of the 1939-43 editions)."""
    return "high" if all(S[k]["style"] == "tint" and S[k]["scale"] == 24000 for k in keys) else "medium"


def export_coverage():
    """data/manual/region_extents/coverage.geojson: per town and snapshot, the area that was read."""
    feats = []
    for p in sorted(INT.glob("coverage_*.json")):
        d = json.loads(p.read_text())
        t, y = d["props"]["town"], d["props"]["year"]
        if t not in TOWNS or y not in TOWNS[t]["snaps"] or not (OUT / f"{t}_{y}.geojson").exists():
            continue
        feats.append({"type": "Feature", "properties": d["props"], "geometry": d["geom"]})
    (OUT / "coverage.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                                     separators=(",", ":")))


def build(town, years=None, meta=None):
    import shapely
    from shapely.geometry import mapping
    clip = town_clip(town)
    OUT.mkdir(parents=True, exist_ok=True)
    meta = meta or {}
    for year in (years or TOWNS[town]["snaps"]):
        bl, tot = snapshot_stats(town, year)
        u = extent_polys(bl, tot, clip)
        cov = coverage_poly(town, year, clip)
        keys = TOWNS[town]["snaps"][year]
        info = TOWNS[town].get("notes", {}).get(year, {})
        sheets_note = "; ".join(f"{k} (1:{S[k]['scale']:,} {S[k]['edition']}): {S[k]['note']}" for k in keys)
        props = {"town": town, "year": int(year), "kind": "built_up",
                 "source": "+".join(f"usgs_htmc:{k}" for k in keys),
                 "source_url": " ".join(f"{PDF}{S[k]['scale']}/{S[k]['file'].replace('_geo.tif', '_geo.pdf')}" for k in keys),
                 "confidence": info.get("confidence", default_confidence(keys)),
                 "note": (info["note"] + " | " if "note" in info else "") + sheets_note
                         + f" | area read: {round(cov.area / 1e6, 2)} km2 (coverage.geojson); outside it this snapshot says nothing",
                 "edition_years": sorted({S[k]["edition"] for k in keys}),
                 "map_years": sorted({S[k]["year"] for k in keys}),
                 "method": f"blocks with built frontage share >= {THRESH[S[keys[0]]['style']]}"
                           + (f" or urban tint share >= {TINT_SHARE}" if S[keys[0]]["style"] == "tint" else ""),
                 "area_km2": round(u.area / 1e6, 3), "n_blocks": int(tot.built.sum())}
        fc = {"type": "FeatureCollection",
              "features": [{"type": "Feature", "properties": props,
                            "geometry": mapping(shapely.set_precision(to_ll(u), 1e-7))}]}
        p = OUT / f"{town}_{year}.geojson"
        p.write_text(json.dumps(fc, separators=(",", ":")))
        # partly built blocks (not part of the built-up extent)
        up = extent_polys(bl, tot, clip, "partial", exclude=u)
        pp = dict(props, kind="partly_built", area_km2=round(up.area / 1e6, 3), n_blocks=int(tot.partial.sum()),
                  method=f"blocks with built frontage share >= {PARTIAL_SHARE} (about 3-4 houses drawn on a block) "
                         f"but below the built-up threshold; not in {town}_{year}.geojson")
        fcp = {"type": "FeatureCollection",
               "features": [{"type": "Feature", "properties": pp,
                             "geometry": mapping(shapely.set_precision(to_ll(up), 1e-7))}]}
        (OUT / f"{town}_{year}_partial.geojson").write_text(json.dumps(fcp, separators=(",", ":")))
        # per-block table (interim, for checks)
        t = tot.copy()
        t.to_parquet(INT / f"class_{town}_{year}.parquet")
        cv = {"town": town, "year": int(year), "sheets": keys, "area_km2": round(cov.area / 1e6, 3)}
        (INT / f"coverage_{town}_{year}.json").write_text(json.dumps({"props": cv, "geom": mapping(to_ll(cov))}))
        print(town, year, "built blocks", int(tot.built.sum()), "of", int((tot["cov"] >= MIN_COV).sum()),
              "read; extent", props["area_km2"], "km2; t_band", round(tot.attrs["t_band"], 1), "m")
    export_coverage()


# --------------------------------------------------------------------------- checks
SANBORN = {"oakland": ["oakland_west", "oakland_downtown"],
           "berkeley": ["berkeley_downtown", "berkeley_northside", "berkeley_southside", "berkeley_west"],
           "alameda": ["alameda_westend"], "san_jose": ["san_jose_downtown"],
           "palo_alto": ["palo_alto_downtown", "palo_alto_mayfield"], "san_mateo": ["san_mateo_downtown"],
           "richmond": ["richmond_downtown"]}
SAN_BUILT, SAN_EMPTY = 0.15, 0.05     # Sanborn footprint share of a block: built / empty
# districts known to be built up by a date (lon/lat boxes), reported per snapshot
PROBES = {"oakland": {"lakeside_uptown": (1905, (-122.2705, 37.8030, -122.2590, 37.8120)),
                      "west_oakland": (1890, (-122.2990, 37.8020, -122.2830, 37.8130)),
                      "temescal": (1910, (-122.2660, 37.8300, -122.2560, 37.8380))}}


def load_extent(town, year, suffix=""):
    import shapely
    from shapely.geometry import shape
    p = OUT / f"{town}_{year}{suffix}.geojson"
    fc = json.loads(p.read_text())
    return to_utm(shapely.union_all([shape(f["geometry"]) for f in fc["features"]]))


def load_coverage(town, year):
    from shapely.geometry import shape
    return to_utm(shape(json.loads((INT / f"coverage_{town}_{year}.json").read_text())["geom"]))


def survivors(town, clip):
    import pandas as pd
    import shapely
    w, s, e, n = TOWNS[town]["bbox"]
    d = pd.read_parquet(ROOT / "data" / "interim" / "region_building_points.parquet")
    d = d[(d.lon > w) & (d.lon < e) & (d.lat > s) & (d.lat < n) & (d.end_year > 9000) & (d.area_m2 >= 30)]
    x, y = tf("EPSG:4326", UTM).transform(d.lon.values, d.lat.values)
    pts = shapely.points(x, y)
    inside = shapely.contains(clip, pts) if hasattr(shapely, "contains") else np.array([clip.contains(p) for p in pts])
    d = d[inside].copy()
    d["x"], d["y"] = np.asarray(x)[inside], np.asarray(y)[inside]
    return d


def sanborn_blocks(town, bl):
    """Per Sanborn area and map year: blocks fully inside the traced coverage with their footprint share."""
    import geopandas as gpd
    import shapely
    out = []
    for area in SANBORN.get(town, []):
        cp = ROOT / "data" / "manual" / "sanborn" / f"{area}_coverage.geojson"
        if not cp.exists():
            continue
        cov = gpd.read_file(cp).to_crs(UTM)
        for _, c in cov.iterrows():
            yr = int(c.map_year)
            fp = ROOT / "data" / "manual" / "sanborn" / f"{area}_{yr}.geojson"
            if not fp.exists():
                continue
            f = gpd.read_file(fp).to_crs(UTM)
            fu = shapely.union_all(list(f.geometry.buffer(0)))
            for bid, g in zip(bl.bid, bl.geometry):
                if not g.intersects(c.geometry):
                    continue
                if g.intersection(c.geometry).area < 0.9 * g.area or g.area > 6e4:
                    continue
                share = g.intersection(fu).area / g.area
                out.append((area, yr, bid, share))
    import pandas as pd
    return pd.DataFrame(out, columns=["area", "year", "bid", "share"])


def check(town):
    import shapely
    clip = town_clip(town)
    bl = blocks(town, clip)
    pts = survivors(town, clip)
    P = shapely.points(pts.x.values, pts.y.values)
    sb = sanborn_blocks(town, bl)
    gb = bl.set_index("bid").geometry
    rep = {"town": town, "snapshots": []}
    years = sorted(TOWNS[town]["snaps"])
    for year in years:
        ext = load_extent(town, year)
        cov = load_coverage(town, year)
        r = {"year": year, "area_km2": round(ext.area / 1e6, 2), "coverage_km2": round(cov.area / 1e6, 2)}
        inc = shapely.contains(cov, P)
        ine = shapely.contains(ext.buffer(20), P)
        part = load_extent(town, year, "_partial")
        r["partial_km2"] = round(part.area / 1e6, 2)
        inp = shapely.contains(part.buffer(20), P) | ine
        mm = inc & (pts.start_year.values > 1800) & (pts.start_year.values < year - 1)
        r["survivors_pre_inside_built_or_partial_pct"] = round(100 * float((mm & inp).sum()) / max(1, mm.sum()), 1)
        for lab, lo, hi in (("pre", 1800, year - 1), ("decade_before", year - 10, year - 1)):
            m = inc & (pts.start_year.values >= lo) & (pts.start_year.values < hi)
            r[f"survivors_{lab}"] = int(m.sum())
            r[f"survivors_{lab}_inside_pct"] = round(100 * float((m & ine).sum()) / max(1, m.sum()), 1)
        # precision proxy: extent blocks (read) holding a building standing today that predates the map
        cls = __import__("pandas").read_parquet(INT / f"class_{town}_{year}.parquet")
        built_b = cls.index[cls.built.values]
        old = pts[(pts.start_year < year) & (pts.start_year > 1800)]
        bt = shapely.STRtree(list(gb.loc[built_b].values))
        hit = np.zeros(len(built_b), bool)
        if len(old):
            idx = bt.query(shapely.points(old.x.values, old.y.values), predicate="within")
            hit[np.unique(idx[1])] = True
        r["extent_blocks"] = int(len(built_b))
        r["extent_blocks_with_survivor_pct"] = round(100 * float(hit.mean()) if len(hit) else 0, 1)
        # Sanborn
        sr = []
        for (area, yr), grp in sb.groupby(["area", "year"]):
            if abs(yr - year) > 6:
                continue
            ok = grp.bid.isin(cls.index[cls["cov"] >= MIN_COV])
            grp = grp[ok]
            b = grp[grp.share >= SAN_BUILT]
            e = grp[grp.share < SAN_EMPTY]
            sr.append({"area": area, "sanborn_year": int(yr), "blocks": int(len(grp)),
                       "built_blocks": int(len(b)), "built_in_extent_pct": round(100 * float(cls.loc[b.bid, "built"].mean()) if len(b) else float("nan"), 1),
                       "empty_blocks": int(len(e)), "empty_in_extent_pct": round(100 * float(cls.loc[e.bid, "built"].mean()) if len(e) else float("nan"), 1)})
        r["sanborn"] = sr
        # consistency: share of the previous snapshot (inside this one's coverage) that this one keeps
        prev = [y for y in years if y < year]
        if prev:
            pe = load_extent(town, prev[-1]).intersection(cov)
            r["prev_kept_pct"] = round(100 * pe.intersection(ext).area / max(1.0, pe.area), 1)
        # probe areas: known built-up districts (share of their land inside the extent)
        land = land_poly(clip.bounds)
        for name, (yr_built, bb) in PROBES.get(town, {}).items():
            pb = shapely.box(*tf("EPSG:4326", UTM).transform(bb[0], bb[1]),
                             *tf("EPSG:4326", UTM).transform(bb[2], bb[3])).intersection(land).intersection(cov)
            if pb.area > 0:
                r[f"probe_{name}_pct"] = round(100 * pb.intersection(ext).area / pb.area, 1)
        # threshold sensitivity (block area, early sheets)
        if S[TOWNS[town]["snaps"][year][0]]["style"] == "early":
            ar = gb.area.reindex(cls.index).values
            rd = (cls["cov"] >= MIN_COV).values & (cls["kind"] == "block").values
            r["block_km2_at_share"] = {str(t): round(float(ar[rd & (cls.share.values >= t)].sum()) / 1e6, 1)
                                       for t in (0.25, 0.35, 0.45)}
        rep["snapshots"].append(r)
        print(json.dumps(r))
    (INT / f"check_{town}.json").write_text(json.dumps(rep, indent=1))
    plot(town, bl, pts, years)
    return rep


def plot(town, bl, pts, years):
    """check/<town>.png: one panel per snapshot; each pixel (10 m) coloured by the earliest snapshot
    (up to the panel's) whose extent contains it; dashed: area read; dots: buildings standing today
    that predate the map."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shapely
    from rasterio import features
    from rasterio.transform import Affine
    clip = town_clip(town)
    xmin, ymin, xmax, ymax = clip.bounds
    r = 10.0
    W, H = int((xmax - xmin) / r) + 1, int((ymax - ymin) / r) + 1
    tr = Affine(r, 0, xmin, 0, -r, ymax)
    cols = np.array([[122, 31, 31], [180, 71, 42], [217, 138, 61], [232, 191, 90], [156, 184, 107], [95, 158, 160]])
    first = np.full((H, W), -1, np.int16)
    town_m = features.rasterize([(clip, 1)], out_shape=(H, W), transform=tr, dtype="uint8")
    n = len(years)
    fig, axs = plt.subplots(1, n, figsize=(5.2 * n, 5.6), dpi=110)
    axs = np.atleast_1d(axs)
    for k, (ax, year) in enumerate(zip(axs, years)):
        ext = load_extent(town, year)
        cov = load_coverage(town, year)
        m = features.rasterize([(g, 1) for g in shapely.get_parts(ext) if not g.is_empty] or [(shapely.box(0, 0, 1, 1), 0)],
                               out_shape=(H, W), transform=tr, dtype="uint8")
        first[(m > 0) & (first < 0)] = k
        img = np.full((H, W, 3), 255, np.uint8)
        img[town_m > 0] = (246, 246, 242)
        for j in range(k + 1):
            img[first == j] = cols[j % len(cols)]
        ax.imshow(img, extent=(xmin, xmin + W * r, ymax - H * r, ymax), interpolation="nearest")
        for p in shapely.get_parts(cov):
            if p.geom_type != "Polygon":
                continue
            x, y = p.exterior.xy
            ax.plot(x, y, color="#2b6cb0", lw=0.9, ls="--")
        old = pts[(pts.start_year < year) & (pts.start_year > 1800)]
        ax.scatter(old.x, old.y, s=0.3, c="k", lw=0)
        ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_aspect("equal")
        ax.set_xticks([]); ax.set_yticks([])
        keys = TOWNS[town]["snaps"][year]
        ax.set_title(f"{year}  ({ext.area / 1e6:.1f} km²)\n" + ", ".join(k_ for k_ in keys), fontsize=8)
    fig.suptitle(f"{TOWNS[town]['name']}: built-up extent per USGS topo snapshot (colour = first snapshot showing it; "
                 f"dashed = area read; dots = buildings standing today built before the map)", fontsize=8)
    fig.tight_layout()
    (OUT / "check").mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "check" / f"{town}.png")
    plt.close(fig)


# --------------------------------------------------------------------------- README tables
def report():
    """Markdown tables (maps used, snapshots + validation) between the markers of ../README.md."""
    used = sorted({k for t in TOWNS.values() for ks in t["snaps"].values() for k in ks},
                  key=lambda k: (S[k]["year"], S[k]["key"]))
    L = ["| sheet | quadrangle | scale | edition | shows | reading | alignment to today's streets | GeoPDF |",
         "|---|---|---|---|---|---|---|---|"]
    for k in used:
        sh = S[k]
        ap = INT / f"align_{k}.json"
        if not ap.exists():
            continue
        al = json.loads(ap.read_text())
        a = (f"{al['shift_m']:.0f} m ({al['model']}, {al['n_used']}/{al['n_windows']} windows, RMS {al['rms_m']:.0f} m)"
             if al.get("aligned") else "as published")
        if sh["style"] == "tint" and al.get("aligned") and al.get("shift_m", 0) < 6:
            a = f"as published (fit {al['shift_m']:.0f} m, RMS {al['rms_m']:.0f} m)"
        quad = sh["file"].split("_")[1].replace("%20", " ")
        url = f"{PDF}{sh['scale']}/{sh['file'].replace('_geo.tif', '_geo.pdf')}"
        rd = "bands + squares" if sh["style"] == "early" else f"{sh['tint']} tint"
        L.append(f"| `{k}` | {quad} | 1:{sh['scale']:,} | {sh['edition']} | {sh['year']} ({sh['note']}) | {rd} | {a} | "
                 f"[{url.split('_')[-4]}]({url}) |")
    T = ["| town | year | sheets | built-up km² | partly built km² | area read km² | confidence | pre-map buildings standing "
         "today inside built-up (+ partly built) (n) | prev. snapshot kept | Sanborn built blocks inside / empty blocks inside |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for town in TOWNS:
        cp = INT / f"check_{town}.json"
        if not cp.exists():
            continue
        rep = json.loads(cp.read_text())
        for r in rep["snapshots"]:
            y = r["year"]
            gj = OUT / f"{town}_{y}.geojson"
            if not gj.exists():
                continue
            pr = json.loads(gj.read_text())["features"][0]["properties"]
            sb = "; ".join(f"{x['area'].split('_', 1)[-1]} {x['sanborn_year']}: {x['built_in_extent_pct']:.0f}% of "
                           f"{x['built_blocks']} / {x['empty_in_extent_pct']:.0f}% of {x['empty_blocks']}"
                           for x in r.get("sanborn", []) if x["blocks"])
            T.append(f"| {town} | {y} | {', '.join(TOWNS[town]['snaps'][y])} | {r['area_km2']} | {r.get('partial_km2', '')} | "
                     f"{r['coverage_km2']} | {pr['confidence']} | {r['survivors_pre_inside_pct']}% "
                     f"({r.get('survivors_pre_inside_built_or_partial_pct', '')}%) ({r['survivors_pre']}) | "
                     f"{str(r.get('prev_kept_pct', '')) + '%' if 'prev_kept_pct' in r else ''} | {sb} |")
    P = ["| town | year | probe | share inside |", "|---|---|---|---|"]
    for town in TOWNS:
        cp = INT / f"check_{town}.json"
        if not cp.exists():
            continue
        for r in json.loads(cp.read_text())["snapshots"]:
            for k, v in r.items():
                if k.startswith("probe_"):
                    P.append(f"| {town} | {r['year']} | {k[6:-4]} | {v}% |")
            if "block_km2_at_share" in r:
                d = r["block_km2_at_share"]
                P.append(f"| {town} | {r['year']} | block km² at share 0.25 / 0.35 / 0.45 | "
                         f"{d['0.25']} / {d['0.35']} / {d['0.45']} |")
    rp = OUT / "README.md"
    txt = rp.read_text()
    for tag, body in (("maps", L), ("snapshots", T), ("probes", P)):
        a0, a1 = f"<!-- {tag} -->", f"<!-- /{tag} -->"
        if a0 in txt and a1 in txt:
            i, j = txt.index(a0) + len(a0), txt.index(a1)
            txt = txt[:i] + "\n" + "\n".join(body) + "\n" + txt[j:]
    rp.write_text(txt)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("town")
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--preview", action="store_true")
    o = ap.parse_args()
    if o.cmd == "sheet":
        print(block_stats(o.town, o.rest[0], o.preview).describe().T)
    elif o.cmd == "build":
        build(o.town, [int(y) for y in o.rest] or None)
    elif o.cmd == "check":
        check(o.town)
    elif o.cmd == "report":
        report()
    elif o.cmd == "all":
        for y, keys in TOWNS[o.town]["snaps"].items():
            for k in keys:
                block_stats(o.town, k)
        build(o.town)
        check(o.town)
