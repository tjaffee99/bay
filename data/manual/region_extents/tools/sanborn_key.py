"""Built-up extent from the colour key map on a Sanborn index sheet (Library of Congress, public domain).

  python -I sanborn_key.py santa_rosa_1904          writes <town>_<year>.geojson + its coverage (data/interim)

The index sheet of a Sanborn volume carries a small key map of the town: the street grid with every
sheet of the volume laid over it as a colour patch. Sanborn surveyed the blocks that held insurable
buildings, so the coloured area is the mapped (built) town at the survey date; it also takes in
sparsely built "special" blocks (a college, a race track, a brewery at the edge). Method:

1. the index sheet at half size (IIIF pct:50) is registered to today's streets by an affine fit on
   street intersections read on the key map (pixel positions in CFG) and looked up by street name in
   today's centrelines (Overture / OpenStreetMap); intersections off by more than 35 m are dropped;
2. colour patches = pixels that are not paper after a median filter (saturation or darkness), warped
   into the town grid of extents.py (2.5 m) and closed over the streets;
3. a block of today (extents.blocks) is *mapped* when half of it is coloured;
4. the snapshot keeps the mapped blocks that the next USGS survey (CFG["confirm"]) still reads as
   built up or partly built (>= 3-4 houses drawn): sparse special blocks drop out. So the extent is
   "inside the Sanborn survey of <year> and showing houses on the <confirm> topographic map".
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extents as E  # noqa: E402

IIIF = "https://tile.loc.gov/image-services/iiif/service:gmd:gmd436m:g4364m:{grp}:{grp}_{res}:{img}/full/pct:50/0/default.jpg"

ORD = {3: ("3rd", "Third"), 4: ("4th", "Fourth"), 5: ("5th", "Fifth"), 6: ("6th", "Sixth"), 7: ("7th", "Seventh")}
NUM = lambda n: [f"{p}{o} Street" for o in ORD[n] for p in ("", "West ", "East ")]      # noqa: E731
FIRST = ["First Street", "1st Street"]
MAIN = ["Main Street", "North Main Street", "South Main Street"]

CFG = {
    "santa_rosa_1904": dict(
        town="santa_rosa", year=1904, confirm=1914,
        item="https://www.loc.gov/item/sanborn00838_004/", res="g008381904", img="00838_1904-0001",
        title="Sanborn Fire Insurance Map from Santa Rosa, Sonoma County, California, Dec. 1904 (39 sheets), index sheet",
        # the key map on the half-size sheet (x0, y0, x1, y1); boxes inside it that are not map (legend)
        box=(80, 650, 2330, 2840), holes=[(110, 2200, 340, 2780)],
        # (streets A, streets B, x, y): intersections read on the key map (half-size pixels)
        cps=[(["Mendocino Avenue"], ["Carrillo Street"], 968, 1206),        # Healdsburg Av. on the map
             (["Mendocino Avenue"], ["College Avenue"], 968, 1297),
             (["Ripley Street"], ["Carrillo Street"], 493, 1207),
             (["Ripley Street"], ["Lincoln Street"], 493, 1378),
             (["Morgan Street"], ["College Avenue", "West College Avenue"], 637, 1298),
             (["Cleveland Avenue"], ["Carrillo Street"], 341, 1207),
             (["Santa Rosa Avenue"], ["Tupper Street"], 1400, 2108),         # S. Main on the map
             (["Santa Rosa Avenue"], ["Mill Street"], 1426, 2330),
             (["E Street", "South E Street"], ["Sonoma Avenue"], 1637, 1880),
             (["E Street"], ["4th Street"], 1480, 1600),
             (["Brown Street"], ["Tupper Street"], 1555, 2080)],
        note="after the Sanborn survey of December 1904, sixteen months before the earthquake of 18 April 1906 "
             "destroyed the business district: buildings of this snapshot inside the destroyed area ended in 1906"),
    "oakland_1889": dict(
        town="oakland", year=1889, confirm=1894, grp="g4364om",
        item="https://www.loc.gov/item/sanborn00727_001/",
        # the key map fills two facing pages; the right page repeats the last 97 px (half size) of the left one
        iiif=["service:gmd:gmd436m:g4364m:g4364om:g4364om_g007271889:00727_1889-0000L",
              "service:gmd:gmd436m:g4364m:g4364om:g4364om_g007271889:00727_1889-0000R"], overlap=97, tint="lab", paper_lab=(75.5, -2.0, 17.0), coverage="extent",
        title="Sanborn Insurance Maps of Oakland, California, Volume One, 1889 (copyright deposit 24 Oct 1889; 73 images), "
              "key map on two pages",
        box=(0, 0, 5516, 4075),
        # water stains over the uncoloured street grid north of 18th St (left page, around the patch of sheet 25J), the
        # title, the 'Corrected to' slip, the legend
        holes=[(0, 0, 2800, 255), (725, 255, 2800, 1560), (0, 690, 725, 1560), (2800, 0, 3340, 725), (3340, 0, 3620, 1100),
               (3620, 0, 5516, 1440), (4800, 2900, 5516, 3900), (5380, 0, 5516, 4075)],
        cps=[(["Market Street"], ["14th Street", "West 14th Street"], 2303, 2270),
             (["West Street"], ["14th Street", "West 14th Street"], 2435, 2270),
             (["Brush Street"], ["14th Street", "West 14th Street"], 2545, 2270),
             (["Castro Street"], ["14th Street", "West 14th Street"], 2660, 2270),
             (["Market Street"], ["7th Street", "West 7th Street"], 2412, 2850),
             (["Brush Street"], ["7th Street"], 2540, 2843),
             (["Castro Street"], ["7th Street"], 2665, 2843),
             (["Jefferson Street"], ["14th Street"], 2890, 2270),
             (["Jefferson Street"], ["7th Street"], 2890, 2843),
             (["Broadway"], ["14th Street"], 3238, 2275),
             (["Broadway"], ["7th Street"], 3240, 2843),
             (["Broadway"], ["19th Street"], 3238, 1855),
             (["Broadway"], ["Embarcadero West", "1st Street"], 3240, 3352),
             (["Webster Street"], ["14th Street"], 3475, 2275),
             (["Webster Street"], ["7th Street"], 3471, 2843),
             (["Harrison Street"], ["14th Street"], 3588, 2275),
             (["Harrison Street"], ["19th Street"], 3588, 1855),
             (["Jackson Street"], ["14th Street"], 3815, 2275),
             (["Madison Street"], ["14th Street"], 3930, 2275),
             (["Telegraph Avenue"], ["West Grand Avenue", "Grand Avenue"], 3062, 1500),          # 22nd St on the map
             (["Telegraph Avenue"], ["24th Street"], 2970, 1220),
             (["Wood Street"], ["7th Street", "West 7th Street"], 688, 3183),
             (["Pine Street"], ["7th Street", "West 7th Street"], 562, 3205),
             (["Willow Street"], ["7th Street", "West 7th Street"], 815, 3165),
             (["Chester Street"], ["7th Street", "West 7th Street"], 1260, 3085),
             (["Center Street"], ["7th Street", "West 7th Street"], 1348, 3066),
             (["Linden Street"], ["12th Street", "West 12th Street"], 2028, 2455)],
        note="Sanborn survey of 1889, Volume One (Oakland west of Lake Merritt; Volume Two, East Oakland / Brooklyn, is not in "
             "the Library of Congress scans): the coloured sheets cover the close-built town from the estuary to about 19th-24th "
             "Street and the railroad quarter at Oakland Point; the uncoloured house blocks of West Oakland between them were "
             "not surveyed, so outside the colour patches this snapshot says nothing"),
    "petaluma_1910": dict(
        town="petaluma", year=1910, confirm=1912, grp="g4364pm",
        item="https://www.loc.gov/item/sanborn00756_005/", res="g007561910", img="00756_1910-0001",
        title="Sanborn Fire Insurance Map from Petaluma, Sonoma County, California, Nov. 1910 (31 sheets), sheet 1 (key map)",
        box=(100, 50, 2450, 2575), holes=[],
        cps=[(["Liberty Street"], ["Washington Street"], 975, 1133),
             (["Kentucky Street"], ["Washington Street"], 1140, 1068),
             (["Petaluma Boulevard North"], ["Washington Street", "East Washington Street"], 1212, 1040),   # Main St
             (["Howard Street"], ["Prospect Street"], 657, 1065),
             (["Howard Street"], ["Union Street"], 735, 1150),
             (["Howard Street"], ["Oak Street"], 485, 907),
             (["Keokuk Street"], ["Prospect Street"], 812, 998),
             (["Liberty Street"], ["Prospect Street"], 898, 966),
             (["6th Street"], ["B Street"], 1232, 1583),
             (["6th Street"], ["C Street"], 1333, 1630),
             (["6th Street"], ["D Street"], 1432, 1680),
             (["6th Street"], ["F Street"], 1635, 1778),
             (["6th Street"], ["G Street"], 1760, 1840),
             (["6th Street"], ["H Street"], 1862, 1888)],
        note="Sanborn survey of November 1910 (population 5,880 on the sheet)"),
    "santa_cruz_1905": dict(
        town="santa_cruz", year=1905, confirm=1899, survivors=3, confidence="low",
        item="https://www.loc.gov/item/sanborn00833_004/", res="g008331905", img="00833_1905-0000",
        title="Sanborn Fire Insurance Map from Santa Cruz, Santa Cruz County, California, 1905 (76 sheets), key map",
        box=(50, 510, 3000, 2800), holes=[(100, 100, 570, 1270), (2560, 250, 2840, 1160)],
        cps=[(["Soquel Avenue"], ["Ocean Street"], 1768, 1812),
             (["Soquel Avenue"], ["North Branciforte Avenue", "South Branciforte Avenue", "Branciforte Avenue"], 1933, 1650),
             (["Soquel Avenue"], ["Pacific Avenue"], 1395, 1898),
             (["Laurel Street"], ["Center Street"], 1325, 2183),
             (["Laurel Street"], ["California Street"], 895, 2172),
             (["Mission Street"], ["Laurel Street"], 755, 2165),
             (["Lincoln Street"], ["Chestnut Street"], 1208, 1982),
             (["Walnut Avenue"], ["Chestnut Street"], 1148, 1922),
             (["Pacific Avenue"], ["Laurel Street"], 1420, 2168),
             (["Broadway"], ["Ocean Street"], 1795, 1895),
             (["Water Street"], ["Ocean Street"], 1619, 1447)],
        note="Sanborn survey of 1905 (population 10,000 on the sheet), eleven years after the fire of 14 April 1894 "
             "(the business district rebuilt); the next USGS survey is of 1952, so the blocks are confirmed on the "
             "1899 sheet or by buildings standing today"),
    "napa_1910": dict(
        town="napa", year=1910, confirm=1899, survivors=3,
        item="https://www.loc.gov/item/sanborn00707_004/", iiif="service:gmd:gmd436m:g4364m:g4364nm:g4364nm_g007071910:00707_1910-0001",
        title="Sanborn Fire Insurance Map from Napa, Napa County, California, Oct. 1910 (35 sheets), sheet 1 (key map)",
        box=(1258, 128, 3225, 2550), holes=[(2630, 100, 3110, 590), (1120, 90, 1300, 330)],
        cps=[(["Seminary Street"], ["Third Street", "3rd Street"], 2018, 1618),
             (["Seminary Street"], ["Clay Street"], 2003, 1385),
             (["Seminary Street"], ["Oak Street"], 2022, 1690),
             (["Jefferson Street"], ["Calistoga Avenue"], 1855, 1250),
             (["Jefferson Street"], ["Clay Street"], 1857, 1388),
             (["Jefferson Street"], ["Third Street", "3rd Street"], 1858, 1620),
             (["Madison Street"], ["Clay Street"], 1792, 1388),
             (["Madison Street"], ["Third Street", "3rd Street"], 1795, 1620),
             (["Soscol Avenue"], ["Third Street", "3rd Street"], 2622, 1268),
             (["Main Street"], ["Yount Street"], 2038, 828),
             (["Main Street"], ["Vallejo Street"], 2088, 892)],
        note="Sanborn survey of October 1910; the next USGS survey is of 1939 photographs, so the blocks are confirmed "
             "on the 1899 sheet or by buildings standing today"),
    "vallejo_1919": dict(
        town="vallejo", year=1919, confirm=1914, survivors=3,
        item="https://www.loc.gov/item/sanborn00905_004/", iiif="service:gmd:gmd436m:g4364m:g4364vm:g4364vm_g009051919:00905_1919-0001",
        title="Sanborn Fire Insurance Map from Vallejo, Solano County, California, Mar. 1919 (43 sheets), sheet 1 (key map)",
        box=(905, 600, 3100, 3600), holes=[(1400, 3260, 1730, 3560)],
        cps=[(["Sacramento Street"], ["Georgia Street"], 1905, 1962),
             (["Marin Street"], ["Georgia Street"], 1993, 1962),
             (["Sonoma Boulevard"], ["Georgia Street"], 2082, 1962),          # Sonoma St. on the map
             (["Sutter Street"], ["Georgia Street"], 2172, 1962),
             (["Napa Street"], ["Georgia Street"], 2262, 1962),
             (["Santa Clara Street"], ["Virginia Street"], 1815, 1895),
             (["Sacramento Street"], ["Florida Street"], 1905, 1687),
             (["Sonoma Boulevard"], ["Tennessee Street"], 2082, 1348),
             (["Sutter Street"], ["Kentucky Street"], 2172, 1618),
             (["Monterey Street"], ["Florida Street"], 2535, 1687),
             (["Alameda Street"], ["Capitol Street"], 2442, 1828),
             (["Marin Street"], ["Pennsylvania Street"], 1993, 2165),
             (["El Dorado Street"], ["Maine Street"], 2352, 2098)],
        note="Sanborn survey of March 1919, at the end of the wartime growth of the Mare Island Navy Yard; confirmed on "
             "the 1914 survey west of 122°15' W or by buildings standing today"),
    "watsonville_1908": dict(
        town="watsonville", year=1908, confirm=1915,
        item="https://www.loc.gov/item/sanborn00921_005/", iiif="service:gmd:gmd436m:g4364m:g4364wm:g00921005:sb000010",
        title="Sanborn Fire Insurance Map from Watsonville, Santa Cruz County, California, Jul. 1908 (25 sheets), sheet 1 (key map)",
        box=(260, 340, 3290, 3245), holes=[(170, 2330, 620, 2750)],
        cps=[(["Walker Street"], ["Ford Street"], 970, 1030),
             (["Walker Street"], ["West 5th Street", "East 5th Street", "5th Street", "West Fifth Street", "East Fifth Street", "Fifth Street"], 1012, 1295),
             (["Walker Street"], ["Kearney Street"], 1040, 1460),
             (["Walker Street"], ["West Lake Avenue", "East Lake Avenue", "Lake Avenue"], 1047, 1572),
             (["Walker Street"], ["West 2nd Street", "2nd Street", "Second Street", "East 2nd Street"], 1100, 2040),
             (["Rodriguez Street"], ["Ford Street"], 1322, 970),
             (["Rodriguez Street"], ["West 5th Street", "East 5th Street", "5th Street", "West Fifth Street", "East Fifth Street", "Fifth Street"], 1398, 1295),
             (["Rodriguez Street"], ["West Lake Avenue", "East Lake Avenue", "Lake Avenue"], 1442, 1572),
             (["Main Street"], ["Ford Street"], 1732, 1065),
             (["Main Street"], ["West 5th Street", "East 5th Street", "5th Street", "West Fifth Street", "East Fifth Street", "Fifth Street"], 1745, 1298),
             (["Main Street"], ["West Lake Avenue", "East Lake Avenue", "Lake Avenue"], 1715, 1555),
             (["Main Street"], ["Peck Street"], 1718, 1980)],
        note="Sanborn survey of July 1908"),
    "gilroy_1906": dict(
        town="gilroy", year=1906, confirm=1915,
        item="https://www.loc.gov/item/sanborn00566_003/", iiif="service:gmd:gmd436m:g4364m:g4364gm:g4364gm_g005661906:00566_1906-0001",
        title="Sanborn Fire Insurance Map from Gilroy, Santa Clara County, California, Oct. 1906 (14 sheets), sheet 1 (key map)",
        box=(190, 1160, 1935, 3700), holes=[],
        cps=[(["Church Street"], NUM(4), 790, 2432), (["Church Street"], NUM(6), 790, 2812),
             (["Rosanna Street"], NUM(3), 680, 2245), (["Rosanna Street"], NUM(5), 680, 2620),
             (["Rosanna Street"], NUM(7), 680, 3000), (["Eigleberry Street"], NUM(5), 900, 2620),
             (["Eigleberry Street"], NUM(7), 900, 3000), (["Monterey Street", "Monterey Road"], NUM(6), 1010, 2812),
             (["Monterey Street", "Monterey Road"], NUM(4), 1010, 2432), (["Hanna Street"], NUM(4), 570, 2432),
             (["Alexander Street"], ["Lewis Street"], 1240, 2472), (["Forest Street"], ["Martin Street"], 1350, 2662),
             (["Chestnut Street"], ["Lewis Street"], 1460, 2472), (["Forest Street"], NUM(7), 1350, 2990)],
        note="Sanborn survey of October 1906 (after the April 1906 earthquake)"),
    "benicia_1913": dict(
        town="benicia", year=1913, confirm=1896, survivors=3,
        item="https://www.loc.gov/item/sanborn00417_004/", iiif="service:gmd:gmd436m:g4364m:g4364bm:g4364bm_g004171913:00417_1913-0001",
        title="Sanborn Fire Insurance Map from Benicia, Solano County, California, Aug. 1913 (17 sheets), sheet 1 (key map)",
        box=(0, 2150, 3225, 3780), holes=[],
        cps=[(FIRST, ["East J Street", "West J Street"], 1667, 2642), (FIRST, ["East H Street", "West H Street"], 1667, 2815),
             (FIRST, ["East F Street", "West F Street"], 1667, 2990), (FIRST, ["East D Street", "West D Street"], 1667, 3167),
             (["East 2nd Street", "East Second Street"], ["East J Street"], 1842, 2642),
             (["East 2nd Street", "East Second Street"], ["East G Street"], 1842, 2905),
             (["East 2nd Street", "East Second Street"], ["East E Street"], 1842, 3080),
             (["East 3rd Street", "East Third Street"], ["East H Street"], 2015, 2815),
             (["East 3rd Street", "East Third Street"], ["East L Street"], 2015, 2467),
             (["East 4th Street", "East Fourth Street"], ["East J Street"], 2190, 2642),
             (["West 2nd Street", "West Second Street"], ["West J Street"], 1490, 2642),
             (["West 2nd Street", "West Second Street"], ["West H Street"], 1490, 2815),
             (["West 3rd Street", "West Third Street"], ["West K Street"], 1320, 2555),
             (["West 4th Street", "West Fourth Street"], ["West J Street"], 1148, 2642)],
        note="Sanborn survey of August 1913; the next USGS survey is of 1940 photographs, so the blocks are confirmed on "
             "the 1896 survey or by buildings standing today"),
    "st_helena_1910": dict(
        town="st_helena", year=1910, confirm=1942, survivors=3,
        item="https://www.loc.gov/item/sanborn00800_004/", iiif="service:gmd:gmd436m:g4364m:g4364sm:g4364sm_g008001910:00800_1910-0001",
        title="Sanborn Fire Insurance Map from Saint Helena, Napa County, California, Nov. 1910 (17 sheets), sheet 1 (key map)",
        box=(1610, 580, 3225, 2510), holes=[(1760, 2100, 2080, 2510), (2780, 1130, 3010, 1350)],
        cps=[(["Adams Street"], ["Stockton Street"], 2115, 1630), (["Adams Street"], ["Kearney Street"], 2252, 1622),
             (["Adams Street"], ["Oak Avenue"], 2345, 1622), (["Adams Street"], MAIN, 2445, 1622),
             (["Pine Street"], ["Oak Avenue"], 2342, 1515), (["Pine Street"], MAIN, 2425, 1513),
             (["Madrona Avenue"], ["Oak Avenue"], 2348, 1422), (["Madrona Avenue"], MAIN, 2428, 1412),
             (["Tainter Street"], ["Stockton Street"], 2130, 1717), (["Tainter Street"], ["Oak Avenue"], 2343, 1732),
             (["Spring Street"], ["Stockton Street"], 2130, 1808), (["Adams Street"], ["Allyn Avenue"], 1980, 1630),
             (["Adams Street"], ["Hudson Avenue"], 1868, 1628), (["Hunt Avenue"], ["Church Street"], 2512, 1742)],
        note="Sanborn survey of November 1910; no USGS survey of the town before 1942 north of 38°30' N, so the blocks "
             "are confirmed on the 1942 survey or by buildings standing today"),
    "sebastopol_1911": dict(
        town="sebastopol", year=1911, confirm=1935, survivors=3,
        item="https://www.loc.gov/item/sanborn00847_006/", iiif="service:gmd:gmd436m:g4364m:g4364sm:g4364sm_g008471911:00847_1911-0001",
        title="Sanborn Fire Insurance Map from Sebastopol, Sonoma County, California, Apr. 1911 (7 sheets), sheet 1 (key map)",
        box=(1500, 250, 2560, 1700), holes=[(1500, 1280, 1600, 1460)],
        cps=[(MAIN, ["Bodega Avenue"], 2077, 882), (["Bodega Avenue"], ["Florence Avenue"], 1800, 888),
             (["Bodega Avenue"], ["Morris Street"], 1955, 883), (MAIN, ["Burnett Street"], 2073, 972),
             (MAIN, ["Calder Avenue"], 2077, 1148), (["Wilton Avenue"], ["Florence Avenue"], 1772, 765),
             (["Wallace Street"], ["Bonnardel Avenue"], 2150, 610), (MAIN, ["Wallace Street"], 2075, 618),
             (["Petaluma Avenue"], ["Walker Avenue"], 2128, 1288)],
        note="Sanborn survey of April 1911; the first USGS survey of the town is of 1935, so the blocks are confirmed on "
             "it or by buildings standing today"),
}


def named_roads(bounds_ll):
    import duckdb
    import shapely
    w, s, e, n = bounds_ll
    con = duckdb.connect()
    con.execute("LOAD spatial;")
    by = {}
    for f in ("roads_local", "roads_region"):
        q = (f"select name, ST_AsWKB(geometry) g from read_parquet('{E.OVT / (f + '.parquet')}') where name is not null "
             f"and ST_XMin(geometry) < {e} and ST_XMax(geometry) > {w} and ST_YMin(geometry) < {n} and ST_YMax(geometry) > {s}")
        for nm, g in con.execute(q).fetchall():
            by.setdefault(nm, []).append(E.to_utm(shapely.from_wkb(bytes(g))))
    return by


def crossing(by, A, B):
    import shapely
    ga = shapely.union_all([g for n in A for g in by.get(n, [])])
    gb = shapely.union_all([g for n in B for g in by.get(n, [])])
    if ga.is_empty or gb.is_empty:
        return None
    x = ga.intersection(gb)
    if x.is_empty:
        if ga.distance(gb) > 30:
            return None
        from shapely.ops import nearest_points
        p, q = nearest_points(ga, gb)
        return ((p.x + q.x) / 2, (p.y + q.y) / 2)
    pts = np.array([(p.x, p.y) for p in shapely.get_parts(x) if p.geom_type == "Point"]
                   or [(x.centroid.x, x.centroid.y)])
    if np.ptp(pts[:, 0]) > 60 or np.ptp(pts[:, 1]) > 60:
        return None                      # the streets cross twice: ambiguous
    return tuple(pts.mean(0))


def run(name):
    import cv2
    import shapely
    from rasterio import features
    from shapely.geometry import mapping
    import pandas as pd
    c = CFG[name]
    town, year = c["town"], c["year"]
    raw = E.RAW / "sanborn_key"
    raw.mkdir(parents=True, exist_ok=True)
    jp = raw / f"{name}_index_50.jpg"
    url = (f"https://tile.loc.gov/image-services/iiif/{c['iiif']}/full/pct:50/0/default.jpg" if isinstance(c.get("iiif"), str)
           else "" if "iiif" in c else IIIF.format(grp=c.get("grp", "g4364sm"), res=c["res"], img=c["img"]))
    if isinstance(c.get("iiif"), list):                      # a key map on facing pages: stitch them side by side
        urls = [f"https://tile.loc.gov/image-services/iiif/{p}/full/pct:50/0/default.jpg" for p in c["iiif"]]
        url = " ".join(urls)
        if not jp.exists() or jp.stat().st_size < 10000:
            pages = []
            for k, u in enumerate(urls):
                pj = raw / f"{name}_page{k}_50.jpg"
                subprocess.run(["curl", "-sS", "-L", "--http1.1", "--retry", "3", "-m", "300", "-A", "Mozilla/5.0 (research script)",
                                "-o", str(pj), u], check=True)
                pg = cv2.imread(str(pj))
                pages.append(pg if k == 0 else pg[:, c.get("overlap", 0):])
            h = max(p.shape[0] for p in pages)
            pages = [cv2.copyMakeBorder(p, 0, h - p.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for p in pages]
            cv2.imwrite(str(jp), np.hstack(pages), [cv2.IMWRITE_JPEG_QUALITY, 92])
    elif not jp.exists() or jp.stat().st_size < 10000:
        subprocess.run(["curl", "-sS", "-L", "--http1.1", "--retry", "3", "-m", "300", "-A", "Mozilla/5.0 (research script)",
                        "-o", str(jp), url], check=True)
    im = cv2.imread(str(jp))[:, :, ::-1]
    # 1. registration
    by = named_roads(tuple(np.array(E.TOWNS[town]["bbox"]) + np.array([-.01, -.01, .01, .01])))
    P, Q, lab = [], [], []
    for A, B, x, y in c["cps"]:
        q = crossing(by, A, B)
        if q is None:
            print("no crossing today:", A, B)
            continue
        P.append((x, y)); Q.append(q); lab.append(f"{A[0]} x {B[0]}")
    P, Q = np.array(P, float), np.array(Q, float)
    use = np.ones(len(P), bool)
    for _ in range(4):
        M = np.column_stack([P[use], np.ones(use.sum())])
        ax, *_ = np.linalg.lstsq(M, Q[use, 0], rcond=None)
        ay, *_ = np.linalg.lstsq(M, Q[use, 1], rcond=None)
        res = np.hypot(np.column_stack([P, np.ones(len(P))]) @ ax - Q[:, 0], np.column_stack([P, np.ones(len(P))]) @ ay - Q[:, 1])
        new = res <= 35
        if (new == use).all() or new.sum() < 4:
            break
        use = new
    for l, r, u in zip(lab, res, use):
        print(f"  {l:<40} residual {r:6.1f} m {'' if u else '(dropped)'}")
    rms = float(np.sqrt(np.mean(res[use] ** 2)))
    scale = float(np.sqrt(abs(ax[0] * ay[1] - ax[1] * ay[0])))
    print(f"affine on {int(use.sum())} of {len(P)} intersections, RMS {rms:.1f} m, {scale:.2f} m per pixel")
    # 2. colour patches
    med = cv2.medianBlur(np.ascontiguousarray(im), 9).astype(np.int16)
    paper = np.median(med[::9, ::9].reshape(-1, 3), axis=0)              # the sheet is mostly paper (white to cream)
    col = (np.abs(med - paper[None, None, :]).max(2) >= 22).astype(np.uint8)
    if c.get("tint") == "lab":
        # tan, unevenly toned paper (Oakland 1889): a wash is a shift in hue or a clearly darker tone, read in CIELAB
        lab = cv2.cvtColor(cv2.medianBlur(np.ascontiguousarray(im[:, :, ::-1]), 9), cv2.COLOR_BGR2LAB).astype(np.float32)
        L, a, b = lab[..., 0] * 100 / 255, lab[..., 1] - 128, lab[..., 2] - 128
        pL, pa, pb = c.get("paper_lab") or (float(np.median(v[::9, ::9])) for v in (L, a, b))
        col = ((np.abs(a - pa) >= 6) | (b - pb >= 6.5) | (pb - b >= 8) | (pL - L >= 7.5)).astype(np.uint8)
        print(f"paper L*a*b* {pL:.1f} {pa:.1f} {pb:.1f}")
    x0, y0, x1, y1 = c["box"]
    keep = np.zeros(col.shape, np.uint8)
    keep[y0:y1, x0:x1] = 1
    for hx0, hy0, hx1, hy1 in c.get("holes", []):
        keep[hy0:hy1, hx0:hx1] = 0
    col &= keep
    col = cv2.morphologyEx(col, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))   # creek, lines
    grid = E.Grid(E.TOWNS[town]["bbox"])
    # town grid pixel (i, j) -> UTM -> sheet pixel: invert the affine
    A2 = np.array([[ax[0], ax[1]], [ay[0], ay[1]]]); t2 = np.array([ax[2], ay[2]])
    Ai = np.linalg.inv(A2)
    # warpAffine wants dst -> src with WARP_INVERSE_MAP: src = Ai @ (utm - t2), utm = (x0 + (i + .5) res, y1 - (j + .5) res)
    G = np.array([[grid.res, 0, grid.x0 + grid.res / 2], [0, -grid.res, grid.y1 - grid.res / 2]])
    Mi = Ai @ (G - np.column_stack([np.zeros((2, 2)), t2]))
    warped = cv2.warpAffine(col, Mi, (grid.W, grid.H), flags=cv2.INTER_NEAREST | cv2.WARP_INVERSE_MAP)
    frame = cv2.warpAffine(keep, Mi, (grid.W, grid.H), flags=cv2.INTER_NEAREST | cv2.WARP_INVERSE_MAP)
    r = int(round(12 / grid.res))
    warped = cv2.morphologyEx(warped, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1,) * 2))
    # 3. blocks
    clip = E.town_clip(town)
    bl = E.blocks(town, clip)
    labm = features.rasterize(((g, i + 1) for i, g in enumerate(bl.geometry)), out_shape=(grid.H, grid.W),
                              transform=grid.transform, dtype="int32")
    n = len(bl) + 1
    px = np.bincount(labm.ravel(), minlength=n)[1:]
    a_col = np.bincount(labm[warped > 0], minlength=n)[1:]
    a_fr = np.bincount(labm[frame > 0], minlength=n)[1:]
    share = a_col / np.maximum(px, 1)
    mapped = (share >= 0.5) & (px > 0)
    cls = pd.read_parquet(E.INT / f"class_{town}_{c['confirm']}.parquet").reindex(bl.bid.values)
    confirmed = (cls.built.fillna(False).values | cls.partial.fillna(False).values)
    how = f"the {c['confirm']} USGS survey reads the block as built up or partly built"
    if c.get("survivors"):
        # no USGS survey soon after: also a block where N buildings standing today predate the Sanborn survey
        pts = E.survivors(town, clip)
        old = pts[(pts.start_year > 1800) & (pts.start_year < year + 1)]
        hit = shapely.STRtree(list(bl.geometry.values)).query(shapely.points(old.x.values, old.y.values), predicate="within")
        cnt = np.bincount(hit[1], minlength=len(bl))
        confirmed |= cnt >= c["survivors"]
        how += f", or {c['survivors']}+ buildings standing on it today predate {year + 1} (assessor years)"
    tot = pd.DataFrame({"built": mapped & confirmed, "mapped": mapped, "cov": a_fr / np.maximum(px, 1),
                        "kind": bl.kind.values}, index=bl.bid.values)
    u = E.extent_polys(bl, tot, clip)
    um = E.extent_polys(bl, tot, clip, "mapped")
    # 4. coverage = the key map's frame on today's land
    fr_poly = shapely.union_all([shapely.geometry.shape(g) for g, v in features.shapes(frame, mask=frame > 0, transform=grid.transform)])
    cov = fr_poly.buffer(0).intersection(clip)
    if c.get("coverage") == "extent":        # a volume that left built-up house blocks unsurveyed: no negative evidence
        cov = u.buffer(8).intersection(clip)
    props = {"town": town, "year": int(year), "kind": "built_up",
             "source": f"loc_sanborn:{c['item'].rstrip('/').split('/')[-1]}:index+usgs_htmc:{'+'.join(E.TOWNS[town]['snaps'][c['confirm']])}",
             "source_url": f"{c['item']} {url}", "confidence": c.get("confidence", "medium" if rms <= 12 else "low"),      # low: key map registered worse than 12 m
             "note": f"{c['note']} | {c['title']}: blocks under the colour patches of the key map (the area Sanborn surveyed: "
                     f"{round(um.area / 1e6, 2)} km2), kept where {how} | key map registered on {int(use.sum())} street intersections (RMS {rms:.0f} m) | area read: "
                     f"{round(cov.area / 1e6, 2)} km2 (coverage.geojson); outside it this snapshot says nothing",
             "edition_years": [int(year)], "map_years": [int(year)],
             "method": "blocks >= 50 % under the Sanborn key-map patches, confirmed: " + how,
             "area_km2": round(u.area / 1e6, 3), "n_blocks": int(tot.built.sum())}
    fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": props,
                                                     "geometry": mapping(shapely.set_precision(E.to_ll(u), 1e-7))}]}
    (E.OUT / f"{town}_{year}.geojson").write_text(json.dumps(fc, separators=(",", ":")))
    # blocks Sanborn surveyed that the next USGS survey does not confirm: partly built (not part of the extent)
    tot["partial"] = tot.mapped & ~tot.built
    up = E.extent_polys(bl, tot, clip, "partial", exclude=u)
    pp = dict(props, kind="partly_built", area_km2=round(up.area / 1e6, 3), n_blocks=int(tot.partial.sum()),
              method=f"blocks under the Sanborn key-map patches that are not confirmed (special risks, large lots, "
                     f"thinly built tracts); not in {town}_{year}.geojson")
    fcp = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": pp,
                                                      "geometry": mapping(shapely.set_precision(E.to_ll(up), 1e-7))}]}
    (E.OUT / f"{town}_{year}_partial.geojson").write_text(json.dumps(fcp, separators=(",", ":")))
    cv = {"town": town, "year": int(year), "sheets": [f"sanborn:{c.get('img') or (c['iiif'] if isinstance(c['iiif'], str) else c['iiif'][0]).split(':')[-1]}"],
          "area_km2": round(cov.area / 1e6, 3)}
    (E.INT / f"coverage_{town}_{year}.json").write_text(json.dumps({"props": cv, "geom": mapping(E.to_ll(cov))}))
    tot.to_parquet(E.INT / f"class_{town}_{year}.parquet")
    E.export_coverage()
    print(f"{town} {year}: Sanborn-mapped blocks {int(mapped.sum())} ({round(um.area / 1e6, 2)} km2), kept {int(tot.built.sum())}; "
          f"extent {props['area_km2']} km2; coverage {cv['area_km2']} km2")
    # check overlay: key map patches (grey), extent outline, today's streets
    pv = np.full((grid.H, grid.W, 3), 255, np.uint8)
    pv[frame > 0] = (245, 245, 240)
    pv[warped > 0] = (200, 200, 200)
    for cls_, g in E.modern_roads(E.TOWNS[town]["bbox"], E.BLOCK_CLASSES):
        g = E.to_utm(g)
        for line in getattr(g, "geoms", [g]):
            cc = np.asarray(line.coords)
            pp = np.column_stack([(cc[:, 0] - grid.x0) / grid.res, (grid.y1 - cc[:, 1]) / grid.res])
            cv2.polylines(pv, [np.round(pp).astype(np.int32)], False, (0, 150, 0), 1)
    for poly in shapely.get_parts(u):
        cc = np.asarray(poly.exterior.coords)
        pp = np.column_stack([(cc[:, 0] - grid.x0) / grid.res, (grid.y1 - cc[:, 1]) / grid.res])
        cv2.polylines(pv, [np.round(pp).astype(np.int32)], True, (0, 0, 200), 3)
    ys, xs = np.nonzero(frame)
    pv = pv[ys.min():ys.max(), xs.min():xs.max()]
    cv2.imwrite(str(E.INT / f"pv_key_{name}.jpg"), cv2.resize(pv, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA))


if __name__ == "__main__":
    run(sys.argv[1])
