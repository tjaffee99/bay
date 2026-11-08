"""water_history.csv: researched dates for water that the c.1800 / today comparison gets wrong.

The terrain derives its natural cover from SFEI c.1800 baylands and today's water from
WorldCover; three kinds of places come out wrong and are fixed by this table:

  * water today that was marsh / flat c.1800 and was *made* water (Lake Merritt 1869, the
    dredged Oakland estuary and harbours, the Tidal Canal): without a dated event it stays
    marsh for ever;
  * reservoirs and artificial lakes: WorldCover sees water, so they exist in 1769;
  * salt ponds and diked baylands, which the terrain dates with one default year.

Geometry comes from data (OpenStreetMap water via Overture 2026-10, SFEI c.1800 / c.1998
baylands), clipped by coarse hand-drawn area rings; the dates are researched (sources per row).
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Polygon

from common import INTERIM, log
from landscape import LRAW, M, OUT, explode_polys, ring_str

W = "https://en.wikipedia.org/wiki/"


def P(*xy):
    return Polygon(list(zip(xy[0::2], xy[1::2])))


# --------------------------------------------------------------------------- inputs
def overture_water():
    d = pd.read_parquet(LRAW / "overture_water.parquet")
    return gpd.GeoDataFrame(d.drop(columns="geometry"), geometry=gpd.GeoSeries.from_wkb(d.geometry), crs=4326)


def baylands(year):
    return gpd.read_file(INTERIM / f"baylands_{year}.geojson").to_crs(4326)


# --------------------------------------------------------------------------- reservoirs / lakes
# name in OSM/Overture, year the reservoir first held water (dam completed), confidence, url, note
RESERVOIRS = [
    # San Francisco (Golden Gate Park) - artificial lakes dug in the dunes
    ("Blue Heron Lake", 1893, "high", W + "Stow_Lake",
     "Stow Lake (renamed Blue Heron Lake in 2023), dug 1893 around Strawberry Hill in Golden Gate Park; the hill stays land."),
    ("Spreckels Lake", 1904, "high", W + "Spreckels_Lake", "Model-yacht lake, Golden Gate Park, 1904."),
    # San Mateo (Spring Valley Water Co. / SFPUC)
    ("Pilarcitos Lake", 1866, "high", W + "Pilarcitos_Lake", "Spring Valley Water Works dam completed 1866; first Peninsula reservoir."),
    ("San Andreas Lake", 1870, "high", W + "San_Andreas_Lake", "Dam built 1868-70 (raised 1875); the fault is named after the lake."),
    ("Upper Crystal Springs Reservoir", 1877, "medium", W + "Crystal_Springs_Reservoir",
     "First Crystal Springs dam (earth, 1877) flooded the upper valley; separated from the lower lake by the Highway 92 causeway."),
    ("Lower Crystal Springs Reservoir", 1888, "high", W + "Crystal_Springs_Dam",
     "Concrete Crystal Springs Dam 1887-90, raised 1911 (lake reached today's size then)."),
    # Alameda / Contra Costa (Contra Costa Water Co. / EBMUD / CCWD / State Water Project)
    ("Lake Temescal", 1869, "high", W + "Lake_Temescal", "Dam built 1868-69 by Anthony Chabot (Contra Costa Water Co.)."),
    ("Lake Chabot", 1875, "high", W + "Lake_Chabot_(Alameda_County,_California)", "Chabot Dam 1874-75 (raised 1892)."),
    ("San Pablo Reservoir", 1919, "high", W + "San_Pablo_Reservoir", "Dam completed 1919 (East Bay Water Co.); raised 1979."),
    ("Upper San Leandro Reservoir", 1926, "high", W + "Upper_San_Leandro_Reservoir", "EBMUD dam 1926."),
    ("Lafayette Reservoir", 1933, "high", W + "Lafayette_Reservoir", "EBMUD dam 1929-33."),
    ("Briones Reservoir", 1964, "high", W + "Briones_Reservoir", "EBMUD dam 1964."),
    ("Calaveras Reservoir", 1925, "high", W + "Calaveras_Dam", "Calaveras Dam completed 1925 (after a 1918 slide); replacement dam 2019."),
    ("San Antonio Reservoir", 1965, "high", W + "San_Antonio_Reservoir", "SFPUC James H. Turner Dam 1965."),
    ("Lake Del Valle", 1968, "high", W + "Lake_Del_Valle", "Del Valle Dam (State Water Project) 1968."),
    ("Los Vaqueros Reservoir", 1998, "high", W + "Los_Vaqueros_Reservoir", "CCWD dam 1998 (enlarged 2012)."),
    ("Clifton Court Forebay", 1969, "high", W + "Clifton_Court_Forebay", "State Water Project forebay 1969, on former Delta farmland."),
    ("Bethany Reservoir", 1967, "medium", W + "Bethany_Reservoir", "California Aqueduct reservoir, late 1960s."),
    ("Contra Loma Reservoir", 1967, "medium", W + "Contra_Loma_Regional_Park", "Bureau of Reclamation dam 1967."),
    ("Lake Elizabeth", 1969, "low", W + "Lake_Elizabeth_(Fremont)", "Fremont Central Park lake, created c.1969 (date LOW)."),
    # Santa Clara (Santa Clara Valley Water Conservation District / San Jose Water)
    ("Searsville Lake", 1892, "high", W + "Searsville_Dam", "Searsville Dam 1890-92 (Spring Valley Water Co.), now Stanford's Jasper Ridge."),
    ("Felt Lake", 1930, "medium", W + "Felt_Lake", "Stanford off-stream reservoir, c.1930."),
    ("Almaden Reservoir", 1935, "high", W + "Almaden_Reservoir", "Santa Clara Valley Water Conservation District, 1935."),
    ("Calero Reservoir", 1935, "high", W + "Calero_Reservoir", "SCVWCD, 1935."),
    ("Guadalupe Reservoir", 1935, "high", W + "Guadalupe_Reservoir", "SCVWCD, 1935."),
    ("Vasona Reservoir", 1935, "high", W + "Vasona_Lake", "SCVWCD percolation dam, 1935."),
    ("Stevens Creek Reservoir", 1935, "high", W + "Stevens_Creek_Reservoir", "SCVWCD, 1935."),
    ("Coyote Reservoir", 1936, "high", W + "Coyote_Reservoir", "SCVWCD, 1936."),
    ("Anderson Reservoir", 1950, "high", W + "Anderson_Lake_(California)", "Leroy Anderson Dam, 1950."),
    ("Lexington Reservoir", 1952, "high", W + "Lexington_Reservoir", "Lenihan Dam 1952; drowned the town of Lexington."),
    ("Lake Elsman", 1950, "medium", W + "Lake_Elsman", "San Jose Water Co. Austrian Dam, c.1950."),
    ("Chesbro Reservoir", 1955, "high", W + "Chesbro_Reservoir", "SCVWD, 1955."),
    ("Uvas Reservoir", 1957, "high", W + "Uvas_Reservoir", "SCVWD, 1957."),
    ("Shoreline Lake", 1983, "medium", W + "Shoreline_Park_(Mountain_View,_California)", "Sailing lake in Mountain View's landfill park, 1983."),
    ("Lake Cunningham", 1980, "low", W + "Lake_Cunningham_Regional_Park", "Flood-control / park lake, San Jose, c.1980 (LOW)."),
    # Marin (Marin Municipal Water District / North Marin)
    ("Lake Lagunitas", 1872, "high", W + "Lake_Lagunitas", "Marin's first reservoir, 1872."),
    ("Phoenix Lake", 1905, "high", W + "Phoenix_Lake", "Dam 1905."),
    ("Alpine Lake", 1918, "high", W + "Alpine_Lake", "Alpine Dam 1917-18, raised 1924 and 1941."),
    ("Bon Tempe Lake", 1948, "high", W + "Bon_Tempe_Lake", "Bon Tempe Dam 1948."),
    ("Kent Lake", 1953, "high", W + "Kent_Lake", "Peters Dam 1953, raised 1982."),
    ("Stafford Lake", 1951, "high", W + "Stafford_Lake", "North Marin Water District dam 1951."),
    ("Nicasio Reservoir", 1961, "high", W + "Nicasio_Reservoir", "Seeger Dam 1961."),
    ("Arroyo Sausal Reservoir", 1979, "medium", W + "Soulajule_Reservoir", "Soulajule Dam on Arroyo Sausal, 1979."),
    # lagoons of the 1960s bayfill new towns
    ("Foster City Lagoon", 1963, "medium", W + "Foster_City,_California",
     "Central lagoon dug as the drainage system of the 1960-65 Brewer Island fill; first residents 1964."),
    ("Redwood Shores Lagoon", 1970, "low", W + "Redwood_Shores,_California",
     "Lagoons of the Redwood Shores fill (late 1960s-70s; date LOW)."),
    ("Bel Marin Keys Lagoon", 1964, "low", "https://www.belmarinkeys.org/",
     "Lagoon community dredged on diked Novato baylands in the 1960s (date LOW)."),
]


def reservoirs(ow):
    rows = []
    for name, y, conf, url, note in RESERVOIRS:
        sel = ow[ow.name == name]
        if not len(sel):
            log(f"water: no OSM polygon for {name}")
            continue
        geom = shapely.union_all(list(sel.geometry))
        cover = "lake"
        rows.append(dict(area_id="lake_" + name.lower().replace(" ", "_").replace("'", ""), name=name, cover=cover,
                         year_start=y, year_end=9999, confidence=conf, geometry=geom,
                         note=note + " Before: valley floor / creek (the dam year is when water first stood here).",
                         source_url=url))
    return rows


# --------------------------------------------------------------------------- made water (dredged / dammed)
def made_water(ow, b18, ring, today=None):
    """Water today inside `ring` that was NOT open water c.1800 (marsh, flat, upland)."""
    w = today if today is not None else shapely.union_all(list(ow[ow.intersects(ring)].geometry))
    w = shapely.intersection(w, ring)
    open18 = shapely.union_all(list(b18[b18["class"].isin(["deep_bay", "shallow_bay"])].geometry))
    m = shapely.difference(w, open18)
    # drop slivers along shorelines (coarse polygons): opening by 15 m
    mm = gpd.GeoSeries([m], crs=4326).to_crs(M).buffer(-15).buffer(15).to_crs(4326).iloc[0]
    return mm


EST = W + "Oakland_Estuary"
ESTUARY = [
    dict(area_id="lake_merritt", name="Lake Merritt (dammed tidal slough)", cover="lake", year_start=1869, year_end=9999,
         confidence="high", ring=P(-122.268, 37.797, -122.243, 37.797, -122.243, 37.815, -122.268, 37.815),
         note="Arm of San Antonio Slough (tidal marsh and mudflat c.1800) closed by Samuel Merritt's dam / bridge at 12th St, "
              "1868-69, with tide gates: a tidal lake from 1869; declared the first US wildlife refuge 1870; margins filled "
              "and walled 1890s-1910s (the lake is smaller than the slough). Geometry: today's lake.",
         source_url=W + "Lake_Merritt"),
    dict(area_id="lake_merritt_channel", name="Lake Merritt Channel (12th St to the estuary)", cover="shallow_water",
         year_start=1869, year_end=9999, confidence="medium",
         ring=P(-122.268, 37.789, -122.255, 37.789, -122.255, 37.7975, -122.268, 37.7975),
         note="The slough below the 12th St dam kept as the lake's tidal inlet and straightened into a channel; marsh "
              "around it filled with the city. Date = the dam (the channel's shape is 20th-century).",
         source_url="https://oaklandgeology.com/2025/09/01/lake-merritt-channel/"),
    dict(area_id="oakland_inner_harbor_west", name="Oakland Inner Harbor (estuary mouth to Clinton Basin)",
         cover="shallow_water", year_start=1878, year_end=9999, confidence="medium",
         ring=P(-122.335, 37.783, -122.262, 37.783, -122.262, 37.802, -122.300, 37.805, -122.335, 37.800),
         note="San Antonio Creek bar and tidal flats: Congress authorised the harbor 1873; training walls from 1874; ship "
              "channel dredged to 20 ft at high tide by 1877 and deepened repeatedly (Inner Harbor quays 1900s-1930s). "
              "Flats / marsh inside today's channel read as water from c.1878.",
         source_url=EST),
    dict(area_id="oakland_brooklyn_basin_estuary", name="Brooklyn Basin and the upper estuary (to Park St)",
         cover="shallow_water", year_start=1890, year_end=9999, confidence="low",
         ring=P(-122.262, 37.770, -122.226, 37.766, -122.222, 37.785, -122.262, 37.795),
         note="Tidal basin east of the Lake Merritt channel enlarged and dredged under the 1874 harbor plan as the scour "
              "reservoir of the channel (Brooklyn Basin); marsh and flats dredged progressively 1880s-1900s (year LOW, "
              "midpoint). Coast Guard Island built from dredge spoil 1913.",
         source_url=EST),
    dict(area_id="alameda_tidal_canal", name="Tidal Canal (Alameda becomes an island)", cover="shallow_water",
         year_start=1902, year_end=9999, confidence="high",
         ring=P(-122.245, 37.752, -122.214, 37.752, -122.214, 37.772, -122.245, 37.776),
         note="1.5-mile canal through the neck of the Alameda peninsula from Brooklyn Basin to San Leandro Bay: planned "
              "1873-76, dug 1889-92 and 1901-02; opened Aug-Sept 1902 ('Alameda Now an Island'). Same dates as "
              "fill_zones.csv al_tidal_canal (kind excavated).",
         source_url="https://www.hmdb.org/m.asp?m=218625"),
    dict(area_id="richmond_inner_harbor", name="Richmond Inner Harbor and Santa Fe Channel", cover="shallow_water",
         year_start=1920, year_end=9999, confidence="low",
         ring=P(-122.375, 37.895, -122.315, 37.895, -122.315, 37.925, -122.375, 37.925),
         note="Channel and basins dredged through the tidal flats and marsh of Ellis Landing / Point Isabel: city harbor "
              "bonds and federal channel 1912-1920s, deep-water port 1929, Kaiser shipyard basins 1940-42. Year LOW "
              "(midpoint of 1912-29).",
         source_url=W + "Richmond_Inner_Harbor"),
]


# --------------------------------------------------------------------------- salt ponds / diked baylands
SALT = "https://www.southbayrestoration.org/documents/permit-related/Historic%20Salt%20AppendixE.pdf"
BCDC = "http://www.bcdc.ca.gov/wp-content/uploads/sites/354/2023/09/Salt-Ponds-PDF.pdf"
SALT_AREAS = [
    dict(area_id="salt_mt_eden_early", name="Mount Eden / San Lorenzo early salt works (natural salt pans)",
         cover="salt_pond", year_start=1856, year_end=1950, confidence="low", src=("b1800_pans",),
         ring=P(-122.185, 37.615, -122.135, 37.615, -122.135, 37.700, -122.185, 37.700),
         note="Natural salt pans (Crystal Salt Pond complex) along the San Lorenzo - Mount Eden shore were harvested before "
              "1850; John Johnson diked them in 1853-54, the first commercial solar salt works on the Bay; ~28 small works "
              "here and at Eden Landing 1850-1910 (Oliver Salt from 1872, Union Pacific Salt 1872-1927); consolidated "
              "and abandoned in the 1920s-30s (hand harvesting ended 1940). Geometry = SFEI c.1800 natural salt ponds "
              "plus 250 m of the surrounding marsh. Start = first decade (spread 1853-1868); end LOW.",
         source_url=SALT),
    dict(area_id="salt_eden_landing_inner", name="Eden Landing / Alvarado salt ponds (inner, 19th-century works)",
         cover="salt_pond", year_start=1868, year_end=9999, confidence="low", src=("b1998", ["salt_pond"], "near_upland", 2500),
         ring=P(-122.175, 37.570, -122.060, 37.570, -122.060, 37.630, -122.175, 37.630),
         note="Small family works on the marsh by Eden Landing and Alvarado (Quigley's Alvarado works 1862; 18 companies on "
              "the Bay by 1868; 17 works exporting by 1880). Today's ponds within ~2.5 km of the upland edge (ESTIMATED "
              "split - the 1950s reconstruction erased the old pond pattern).",
         source_url=SALT),
    dict(area_id="salt_eden_landing_outer", name="Eden Landing / Union City salt ponds (outer, 1924-31 and 1950s)",
         cover="salt_pond", year_start=1928, year_end=9999, confidence="medium", src=("b1998", ["salt_pond"], "far_upland", 2500),
         ring=P(-122.175, 37.570, -122.060, 37.570, -122.060, 37.630, -122.175, 37.630),
         note="Large evaporators built by Oliver / Leslie-California Salt: the Union City Alvarado ponds date from 1924-31 "
              "(Shoup & Baker 2007), flood-control levees 1955-59; current layout mostly post-1953. Several ponds "
              "restored to marsh 2006-2011 (fill_zones sb_eden_landing_restored).",
         source_url=SALT),
    dict(area_id="salt_newark_north", name="Newark salt ponds north of the Dumbarton (Alameda Creek - Coyote Hills)",
         cover="salt_pond", year_start=1905, year_end=9999, confidence="low", src=("b1998", ["salt_pond"]),
         ring=P(-122.140, 37.505, -122.040, 37.540, -122.040, 37.590, -122.140, 37.590),
         note="Pioneer Salt Works at the mouth of Alameda Creek in operation by 1885 (bought by Oliver 1927); Morton Salt "
              "refinery at Newark 1926, Leslie's Newark plant 1941. Year = ESTIMATED midpoint of 1885-1930 expansion.",
         source_url=SALT),
    dict(area_id="salt_newark_south", name="Newark / Mowry salt ponds south of the Dumbarton", cover="salt_pond",
         year_start=1935, year_end=9999, confidence="low", src=("b1998", ["salt_pond"]),
         ring=P(-122.120, 37.455, -121.950, 37.455, -121.950, 37.505, -122.040, 37.540, -122.120, 37.505),
         note="Leslie Salt expansion of the 1930s-40s (12,500 acres of ponds Bay-wide in 1936, 25,000 in 1946, 30,000 in "
              "the South Bay by 1959). Year ESTIMATED.",
         source_url=BCDC),
    dict(area_id="salt_alviso_east", name="Alviso salt ponds (Coyote Creek to Guadalupe Slough)", cover="salt_pond",
         year_start=1925, year_end=9999, confidence="medium", src=("b1998", ["salt_pond"]),
         ring=P(-122.025, 37.400, -121.920, 37.400, -121.920, 37.470, -122.025, 37.470),
         note="Attempts in the 1890s-1910s washed away; Arden Salt (Schilling, 1919) and Alviso Salt built levees and "
              "ponds in the 1920s; Arden bought Alviso Salt 1929; Leslie from 1936; Cargill 1978; state / federal 2003; "
              "Island Ponds breached 2006 (fill_zones sb_island_ponds_restored).",
         source_url=SALT),
    dict(area_id="salt_alviso_west", name="Sunnyvale / Mountain View salt ponds (A1-A4)", cover="salt_pond",
         year_start=1935, year_end=9999, confidence="low", src=("b1998", ["salt_pond"]),
         ring=P(-122.125, 37.405, -122.025, 37.405, -122.025, 37.470, -122.125, 37.470),
         note="Western end of the Alviso complex (Charleston / Mountain View / Stevens Creek sloughs), built during Leslie's "
              "1930s-40s expansion. Year ESTIMATED.",
         source_url=SALT),
    dict(area_id="salt_ravenswood", name="Ravenswood salt ponds (Menlo Park / East Palo Alto)", cover="salt_pond",
         year_start=1912, year_end=9999, confidence="medium", src=("b1998", ["salt_pond"]),
         ring=P(-122.180, 37.455, -122.100, 37.455, -122.100, 37.520, -122.180, 37.520),
         note="West-bay salt making began in the 1890s (Dumbarton Land & Improvement Co. c.1892 -> Leslie Salt Refining "
              "1904, Leslie Salt Co. 1907); Ravenswood ponds were built in the 1910s.",
         source_url=SALT),
    dict(area_id="salt_redwood_city", name="Redwood City salt ponds (Westpoint Slough / Greco Island side)",
         cover="salt_pond", year_start=1910, year_end=9999, confidence="low", src=("b1998", ["salt_pond"]),
         ring=P(-122.260, 37.470, -122.180, 37.470, -122.180, 37.535, -122.260, 37.535),
         note="Redwood City Salt Co. and West Shore Salt Co. (bayfront first diked for salt c.1901; Stauffer, then Leslie "
              "1907); today's Cargill plant ponds. Year ESTIMATED (1900s-1920s). Bair Island salt 1946-65 is in "
              "fill_zones (sm_bair_island_diked).",
         source_url=SALT),
    dict(area_id="diked_bair_island_ag", name="Bair Island diked for farming", cover="diked", year_start=1885,
         year_end=1946, confidence="medium", src=("b1998", ["diked_wetland", "agricultural_bayland", "tidal_marsh", "salt_pond"]),
         ring=P(-122.255, 37.505, -122.205, 37.505, -122.205, 37.535, -122.255, 37.535),
         note="Diked in the 1880s for grazing and hay (little success with crops in the early 1900s); Leslie Salt ponds "
              "1946-52, abandoned 1965; returned to the tides 1983-2015 (fill_zones).",
         source_url="https://baynature.org/magazine/fall2008/raising-bair-island/"),
    dict(area_id="diked_south_bay_ag", name="Diked agricultural baylands (Alviso - Newark - Union City margins)",
         cover="diked", year_start=1895, year_end=9999, confidence="low",
         src=("b1998", ["agricultural_bayland", "diked_wetland"]),
         ring=P(-122.140, 37.400, -121.900, 37.400, -121.900, 37.600, -122.140, 37.600),
         note="High marsh along the landward edge reclaimed for hay, pasture and row crops behind levees, c.1880s-1910s, "
              "before the salt companies took the outer marsh (SFEI c.1998 'agricultural bayland' / 'diked wetland'). "
              "Year ESTIMATED.",
         source_url="https://www.sfei.org/ecoatlas"),
]


def salt_rows(b18, b98):
    rows = []
    upland = shapely.union_all(list(b18[~b18["class"].isin(
        ["deep_bay", "shallow_bay", "tidal_flat", "tidal_marsh", "tidal_marsh_pan", "salt_pond", "lagoon"])].geometry))
    pans = shapely.union_all(list(b18[b18["class"] == "salt_pond"].geometry))
    wet18 = shapely.union_all(list(b18[b18["class"].isin(["tidal_marsh", "tidal_marsh_pan", "salt_pond", "tidal_flat"])].geometry))
    upl_m = gpd.GeoSeries([upland], crs=4326).to_crs(M).iloc[0]
    for a in SALT_AREAS:
        ring = a["ring"]
        src = a["src"]
        if src[0] == "b1800_pans":
            g = gpd.GeoSeries([shapely.intersection(pans, ring)], crs=4326).to_crs(M).buffer(250).to_crs(4326).iloc[0]
            geom = shapely.intersection(shapely.intersection(g, wet18), ring)
        else:
            sel = b98[b98["class"].isin(src[1])]
            geom = shapely.intersection(shapely.union_all(list(sel.geometry)), ring)
            if len(src) > 2:
                gm = gpd.GeoSeries([geom], crs=4326).to_crs(M).iloc[0]
                near = upl_m.buffer(src[3])
                gm = gm.intersection(near) if src[2] == "near_upland" else gm.difference(near)
                geom = gpd.GeoSeries([gm], crs=M).to_crs(4326).iloc[0]
        # join ponds across their levees (one polygon per complex instead of hundreds of ponds)
        geom = gpd.GeoSeries([geom], crs=4326).to_crs(M).buffer(30).buffer(-30).to_crs(4326).iloc[0]
        rows.append(dict(a, geometry=geom))
    return rows


# --------------------------------------------------------------------------- build
def water():
    ow = overture_water()
    b18 = baylands(1800)
    b98 = baylands(1998)
    rows = reservoirs(ow)
    for a in ESTUARY:
        if a["cover"] == "lake":
            geom = shapely.union_all(list(ow[(ow.name == "Lake Merritt")].geometry))
        else:
            geom = made_water(ow, b18, a["ring"])
        rows.append(dict(a, geometry=geom))
    rows += salt_rows(b18, b98)
    out = []
    for r in rows:
        parts = explode_polys(r["geometry"])
        if not parts:
            log(f"water: {r['area_id']} has no geometry")
            continue
        gs = gpd.GeoSeries(parts, crs=4326).to_crs(M)
        keep = [(p, a) for p, a in zip(gs.simplify(8), gs.area) if a >= 10000]  # >= 1 ha
        keep.sort(key=lambda t: -t[1])
        for i, (p, a) in enumerate(keep):
            p4 = gpd.GeoSeries([p], crs=M).to_crs(4326).iloc[0]
            if p4.geom_type != "Polygon":
                p4 = max(explode_polys(p4), key=lambda q: q.area)
            out.append(dict(area_id=r["area_id"] + (f"_{i + 1}" if len(keep) > 1 else ""), name=r["name"],
                            cover=r["cover"], year_start=r["year_start"], year_end=r["year_end"],
                            confidence=r["confidence"], ring_type="lonlat", ring=ring_str(p4),
                            area_ha=round(a / 1e4, 1), note=r["note"], source_url=r["source_url"]))
    df = pd.DataFrame(out)
    df.to_csv(OUT / "water_history.csv", index=False)
    log(f"water_history.csv: {len(df)} rows; areas (ha) by id:\n" +
        df.groupby(df.area_id.str.replace(r"_\d+$", "", regex=True)).area_ha.sum().round(0).to_string())


if __name__ == "__main__":
    water()
