"""Military and industrial sites of the mapped Bay Area: definitions for build.py.

Each site: site_id, name, label (short map label), kind, cover, start, end (9999 = still there),
conf, src (main source URL), note, county, and its ground as *parts*:
  osm      Overture base land_use ids (8-char prefixes, release 2026-10-21.0; OpenStreetMap
           outlines, ODbL): today's outline of the site (or of its surviving part)
  osm_box  (W, S, E, N, classes, exclude): every land_use polygon of those classes whose
           representative point lies in the box (multi-polygon sites such as refineries)
  traced   rings read on a USGS topo sheet in the local metre frame (vt.ll2loc) of `frame`
           (x east, y north), with the sheet they were read on
  files    GeoJSON outlines extracted with tools/tint.py (traced/*.geojson)
Per-part overrides: dict(cover=, start=, end=, conf=, note=).

`date`: today's footprints inside are dated by the USGS editions that first draw them
(date_editions.py) with the site's founding year `founded` as the lower bound.

Facts are cited per site; anything estimated says so in `conf` / `note`.
"""

T = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/"
W = "https://en.wikipedia.org/wiki/"

IND = ("industrial", "works", "brownfield", "railway", "military", "base", "quarry", "landfill", "construction")


def site(site_id, name, label, kind, cover, start, end, conf, src, note, county, parts, **kw):
    d = dict(site_id=site_id, name=name, label=label, kind=kind, cover=cover, start=start, end=end, conf=conf,
             src=src, note=note, county=county, parts=parts)
    d.update(kw)
    return d


def osm(*ids, **ov):
    return dict(osm=list(ids), **ov)


def box(w, s, e, n, classes=IND, exclude=(), **ov):
    return dict(osm_box=(w, s, e, n, tuple(classes), tuple(exclude)), **ov)


def traced(frame, ring, sheet, **ov):
    return dict(traced=dict(frame=frame, ring=ring, sheet=sheet), **ov)


def files(paths, **ov):
    return dict(files=list(paths), **ov)


def hull(lon, lat, radius_m, buffer_m=35, **ov):
    """Outline of a post / cantonment without an OSM outline: the convex hull of today's
    footprints within radius_m of (lon, lat), buffered by buffer_m."""
    return dict(hull=dict(center=(lon, lat), radius=radius_m, buffer=buffer_m), **ov)


# Permanente: the 1948-photo pit (white "Quarry" area of the Cupertino 1953 sheet), read on the
# render (-122.115, 37.317), 3 m pixels: crop px -> local metres
_P48 = [(140, 215), (150, 195), (175, 180), (205, 170), (230, 175), (245, 195), (250, 225), (240, 255), (225, 270),
        (195, 275), (165, 268), (145, 250)]
PERM48 = [(-1900 + 3 * (450 + a + 0.5), 1900 - 3 * (300 + b + 0.5)) for a, b in _P48]
# the early (Granite Rock / El Dorado Sugar) limestone quarry: the quarry symbol of the Palo Alto
# 1:62,500 sheets (1939 survey / 1940 photos) at about (-30, 570); extent estimated (~1.7 ha)
import math  # noqa: E402
PERM03 = [(-30 + 90 * math.cos(t / 12 * 2 * math.pi), 570 + 60 * math.sin(t / 12 * 2 * math.pi)) for t in range(12)]
# Permanente cement plant, read on the Cupertino 1953 sheet (1948 photos) in the frame (-122.104, 37.315)
PERM_PLANT = [(640, 930), (900, 960), (1180, 900), (1330, 700), (1360, 250), (1290, -180), (1060, -260), (820, -120),
              (680, 150), (610, 520)]

SITES = [
    # ------------------------------------------------------------------ Contra Costa: refineries & chemicals
    site("chevron_richmond", "Standard Oil (Chevron) Richmond Refinery", "Chevron Richmond Refinery", "refinery",
         "tank_farm", 1902, 9999, "exact", W + "Chevron_Richmond_Refinery",
         "Pacific Coast Oil Co. / Standard Oil of California built the refinery on the Potrero hills and the "
         "marsh behind Point Richmond from 1901; first oil 1902. Tanks on the hills on the 1915 San Francisco "
         "1:62,500 sheet (and its 1904-1914 reprints); the plant spread over the flats south and the Castro Creek "
         "marsh north (first on the 1947-1993 sheets). Parts are dated by the editions that first draw tanks on them.",
         "Contra Costa",
         [box(-122.4105, 37.9285, -122.3855, 37.9560, exclude=("78f49fab", "26c5b557", "4959cec7", "fe6b4bc3"),
              auto=True)],
         date=True, founded=1902),
    site("shell_martinez", "Shell Martinez Refinery (Martinez Refining Co., PBF, since 2020)", "Shell Martinez Refinery",
         "refinery", "tank_farm", 1915, 9999, "exact", "https://clui.org/ludb/site/martinez-refinery",
         "Shell's first U.S. refinery, built 1915 (Water Board fact sheet: operating 1916); sold to PBF 2020. "
         "Edition dates of the tank farms: Carquinez Strait 1:62,500 (1937/1940 photos), Port Chicago / Vine Hill / "
         "Benicia 1:24k (1948-1979).", "Contra Costa",
         [osm("56067500", "bdd6a9de", auto=True)], date=True, founded=1915),
    site("avon_refinery", "Associated Oil Avon Refinery (Tidewater, Tosco 1976, Golden Eagle, Tesoro; Marathon "
         "Martinez Renewable Fuels)", "Avon Refinery (Marathon)", "refinery", "tank_farm", 1913, 9999, "exact",
         W + "Marathon_Martinez_Renewable_Fuels",
         "Associated Oil Co. topping plant at Avon 1913 (CEC refinery history: Associated 1913-37, Tidewater Associated, "
         "Phillips, Tosco 1976-2000, UDS, Tesoro/Andeavor, Marathon 2018); idled 2020, renewable diesel from 2023. "
         "The 1958 Port Chicago sheet labels it 'Avon (Associated)'.", "Contra Costa",
         [osm("b4e0a5e2", auto=True)], date=True, founded=1913),
    site("rodeo_refinery", "Union Oil Oleum (Rodeo) Refinery (Phillips 66 Rodeo Renewed)", "Rodeo Refinery (Oleum)",
         "refinery", "tank_farm", 1896, 9999, "exact", "https://archive.cocohistory.org/bulletin-oleum.html",
         "Union Oil's Oleum refinery, built 1896 - the first major refinery on the Bay (CLUI; Contra Costa County "
         "Historical Society 'Oleum stands for petroleum'); Unocal -> Tosco 1997 -> ConocoPhillips -> Phillips 66; "
         "renewable fuels since 2024. 'Oleum' with tanks on the 1948 Mare Island sheet.", "Contra Costa",
         [osm("db11ded9", "9d4d57a9", "c6e3a184", auto=True)], date=True, founded=1896),
    site("selby_smelter", "Selby Smelting and Lead Co. works (ASARCO Selby smelter)", "Selby Smelter", "factory",
         "industrial", 1885, 1971, "estimated", "https://oac.cdlib.org/findaid/ark:/13030/tf7h4nb206/entire_text/",
         "Prentiss Selby's company moved its smelting and refining from San Francisco to the Carquinez shore "
         "(decided 1884; works running 1885); American Smelting & Refining Co. from 1905; the 605 ft stack was a "
         "landmark; closed c.1970-71 and razed with the company town of Tormey (end year estimated). Site today: "
         "the capped slag area west of Crockett (OSM industrial outline).", "Contra Costa",
         [osm("64f36f00")], date=True, founded=1885),
    site("ch_crockett", "C&H Sugar refinery, Crockett", "C&H Sugar", "factory", "industrial", 1906, 9999, "exact",
         W + "C%26H_Sugar",
         "California and Hawaiian Sugar Refining Co. took over the 1897-98 California Beet Sugar Co. refinery "
         "(itself on Starr's 1884 flour mill site) and has refined cane sugar there since 1906.", "Contra Costa",
         [osm("08dd0b41")], date=True, founded=1898),
    site("hercules_powder", "California Powder Works / Hercules Powder Co. works", "Hercules Powder Works",
         "chemical", "industrial", 1881, 1977, "estimated", W + "Hercules,_California",
         "California Powder Works bought the Pinole shore site 1879; dynamite made from 1881 (du Pont 1903, "
         "Hercules Powder Co. 1913); TNT in both World Wars; explosives ended 1964, the post-war ammonia / fertiliser "
         "plant closed 1976. Plant area (wharf, nitroglycerine and packing houses, the 1960s 'Chemical Plant') read "
         "on the Mare Island 1:24k sheets 1948 / 1968 PR; the 3,000-acre buffer land of magazines is open_works. "
         "The company town of Hercules (houses) is not part of the site.", "Contra Costa",
         [traced((-122.275, 38.018), [(-1700, 420), (-1450, 520), (-900, 560), (-500, 620), (-250, 560), (-250, 250),
                                      (-500, 150), (-800, 0), (-1000, -150), (-1250, -200), (-1450, -100),
                                      (-1600, 150), (-1750, 300)], T + "CA_Mare%20Island_292724_1951_24000_geo.tif"),
          traced((-122.275, 38.018), [(-250, 560), (300, 700), (900, 500), (1300, 100), (1000, -350), (300, -450),
                                      (-250, -300), (-500, 150), (-250, 250)],
                 T + "CA_Mare%20Island_292724_1951_24000_geo.tif", cover="open_works", conf="estimated",
                 note="magazine / buffer land east of the plant (scattered small buildings on the 1948 sheet); "
                      "outline estimated; housing from 1974")],
         date=False),
    site("giant_powder", "Giant Powder Co. / Atlas Powder works, Point Pinole", "Giant Powder Works", "chemical",
         "open_works", 1892, 1960, "estimated", W + "Point_Pinole_Regional_Shoreline",
         "Giant Powder moved its dynamite works to Point Pinole in 1892 after explosions at its earlier plants; "
         "Atlas Powder later; production ended 1960; Bethlehem Steel bought the land 1960 (unbuilt steel mill), "
         "regional shoreline since 1973. The works' buildings were scattered over the point ('Nitro' on the 1948 "
         "Mare Island sheet): the ground stays open, the outline is today's park.", "Contra Costa",
         [osm("f613b0f0")], date=False),
    site("concord_nws", "Naval Magazine Port Chicago / Naval Weapons Station Concord (MOTCO)",
         "Concord Naval Weapons Station", "military", "open_works", 1942, 9999, "exact",
         W + "Concord_Naval_Weapons_Station",
         "Naval Magazine Port Chicago commissioned Dec 1942 (explosion 17 Jul 1944); inland magazine area added 1944; "
         "NWS Concord 1957; the tidal area is Military Ocean Terminal Concord (Army) since 2008; the inland area "
         "closed 2008 (BRAC 2005). The town of Port Chicago inside the buffer was bought out and razed 1968-69. "
         "Mostly open ground with igloo magazines and rail yards: open_works.", "Contra Costa",
         [osm("4126be4d")], date=True, founded=1942),
    site("acme_landfill", "ACME Landfill, Martinez", "ACME Landfill", "other", "landfill", 1949, 9999, "estimated",
         "https://www.calrecycle.ca.gov/",
         "Bayside landfill on the Pacheco Creek marsh north of the Avon refinery; opening year estimated (late 1940s; "
         "the dump is drawn on the 1958 Port Chicago sheet).", "Contra Costa", [osm("baa3122f")], date=False),
    site("keller_canyon_landfill", "Keller Canyon Landfill", "Keller Canyon Landfill", "other", "landfill", 1992, 9999,
         "exact", "https://www.contracosta.ca.gov/", "Opened 1992 (county-permitted canyon landfill near Bay Point).",
         "Contra Costa", [osm("5e6f81ab")], date=False),
    site("kaiser_yard3", "Kaiser Richmond Shipyard No. 3 (and No. 4), Point Potrero", "Kaiser Shipyard No. 3",
         "shipyard", "industrial", 1942, 9999, "exact",
         "https://www.nps.gov/rori/learn/historyculture/historic-richmond-shipyards.htm",
         "Permanent yard with five graving basins built 1942 by Permanente Metals; Yard 4 (small craft) beside it; "
         "the yards closed 1945-46. Point Potrero then Port of Richmond terminals and the Navy's Richmond "
         "(reserve-fleet) annex - industrial ground continues (end = the shipyard). Outline: today's OSM industrial "
         "polygons on Point Potrero.", "Contra Costa",
         [box(-122.3740, 37.9010, -122.3600, 37.9150, exclude=("4959cec7",))], label_years=(1942, 1946), date=True, founded=1942),
    site("kaiser_yards_1_2", "Kaiser Richmond Shipyards No. 1 and 2", "Kaiser Shipyards 1 & 2", "shipyard",
         "industrial", 1941, 1946, "estimated", W + "Richmond_Shipyards",
         "Yard 1 (Todd-California, from Jan 1941) and Yard 2 (1941) on the Inner Harbor basin; 747 ships in the four "
         "yards; closed 1945-46; the ground became Marina Bay (housing from the 1980s). Outline read on the Richmond "
         "1:24k sheet (1946 photos) - approximate (+-50 m).", "Contra Costa",
         [traced((-122.355, 37.912), [(-150, -650), (-150, 50), (600, 100), (1300, 150), (1900, 50), (1900, -650),
                                      (1200, -700), (600, -700)], T + "CA_Richmond_294667_1947_24000_geo.tif")],
         date=False),
    site("ford_richmond", "Ford Richmond Assembly Plant (Ford Point / Craneway)", "Ford Assembly Plant", "factory",
         "industrial", 1931, 1956, "exact", W + "Ford_Assembly_Building_(Richmond,_California)",
         "Albert Kahn plant opened 1931, tank depot in WWII, closed 1956 (moved to Milpitas); the building stands "
         "(Rosie the Riveter NHP, Craneway Pavilion). Only the building's date is given (known_dates_industrial.csv).",
         "Contra Costa", [], date=False),
    site("santa_fe_richmond", "Santa Fe Railway Richmond yard and terminal", "Santa Fe Yard", "rail_yard", "rail_yard",
         1900, 9999, "estimated", W + "Richmond,_California",
         "The Santa Fe reached Point Richmond and its Ferry Point terminal in 1900 (yards east of the Potrero hills, "
         "drawn on the 1915 sheet); today BNSF's Richmond yard.", "Contra Costa",
         [osm("78f49fab", "26c5b557")], date=True, founded=1900),
    site("pullman_richmond", "Pullman Company shops, Richmond", "Pullman Shops", "factory", "industrial", 1910, 1959,
         "estimated", "https://www.richmondmuseumofhistory.org/",
         "Pullman car repair shops on the Santa Fe line ('Pullman Shops' on the 1946-photo Richmond sheet); "
         "opened c.1910, closed late 1950s (years estimated). Outline read on the 1946 sheet.", "Contra Costa",
         [traced((-122.355, 37.912), [(1250, 1650), (1600, 1650), (1600, 2050), (1250, 2050)],
                 T + "CA_Richmond_294667_1947_24000_geo.tif")], date=False),
    site("point_molate", "Winehaven (California Wine Association) / Naval Fuel Depot Point Molate",
         "Winehaven / Point Molate", "military", "industrial", 1907, 1995, "estimated", W + "Winehaven,_California",
         "California Wine Association's Winehaven winery and company town, built 1907-08, the world's largest winery "
         "until Prohibition closed it (1919); Navy fuel depot (tank farm on the hill) 1942-1995; the brick winery "
         "buildings stand (NRHP district). Outlines read on the San Quentin 1:24k sheet (1947 photos).", "Contra Costa",
         [traced((-122.418, 37.947), [(-160, 120), (-100, 880), (130, 900), (300, 700), (260, 300), (100, 120)],
                 T + "CA_San%20Quentin_466329_1948_24000_geo.tif", end=9999,
                 note="winery buildings and wharf (1907); industrial / depot ground until today's vacant site"),
          traced((-122.418, 37.947), [(130, 900), (600, 950), (1000, 850), (1000, 250), (500, 0), (100, 120),
                                      (260, 300), (300, 700)], T + "CA_San%20Quentin_466329_1948_24000_geo.tif",
                 start=1942, end=1995, cover="open_works", conf="estimated",
                 note="Navy fuel depot tank hill (outline estimated; tanks removed after 1995)")],
         date=True, founded=1907),
    # ------------------------------------------------------------------ Alameda: Port of Oakland & military
    site("oakland_army_base", "Oakland Army Base (Oakland Sub-Port / Army Supply Base / Army Terminal)",
         "Oakland Army Base", "military", "military", 1941.95, 9999, "estimated", W + "Oakland_Army_Base",
         "Construction from Dec 1941 as the Oakland Sub-Port of the SF Port of Embarkation; Oakland Army Base 1944, "
         "Army Terminal 1955; Port of Embarkation HQ from Fort Mason 1964; decommissioned 30 Sep 1999 (BRAC 1995). "
         "Warehouses demolished in waves (Port of Oakland / Oakland Global logistics centre 2010s; Gateway Park "
         "2020). Outline: the 'Army Reservation' of the Oakland West 1:24k sheet (1946 photos), read +-40 m.",
         "Alameda",
         [traced((-122.302, 37.805), [(-1950, 550), (-1450, 1250), (-1150, 1750), (-850, 1900), (-500, 2060),
                                      (300, 2150), (650, 2000), (150, 1300), (-300, 650), (-600, 520), (-1300, 470)],
                 T + "CA_Oakland%20West_293623_1949_24000_geo.tif")], label_years=(1941.95, 1999.75), date=True, founded=1941.95),
    site("sp_oakland_mole", "Southern Pacific Oakland Mole (Oakland Pier)", "Oakland Mole", "rail_yard", "rail_yard",
         1882, 9999, "estimated", W + "Oakland_Long_Wharf",
         "Central Pacific's Oakland Long Wharf (1871) rebuilt 1882 as the rock-fill mole with the Oakland Pier train "
         "and ferry terminal; ferries ended 1958, the mole became the base of the Port's Seventh Street Terminal "
         "(fill 1967-71). Outline: the mole and yards of the 1946-photo Oakland West sheet; the end year marks the "
         "railway use (the ground stays port).", "Alameda",
         [traced((-122.338, 37.812), [(450, -520), (450, -160), (1150, -130), (1700, -120), (1700, -520)],
                 T + "CA_Oakland%20West_293623_1949_24000_geo.tif")], label_years=(1882, 1960), date=False),
    site("sp_west_oakland_yard", "Southern Pacific West Oakland yards and shops (Desert Yard)",
         "West Oakland Rail Yards", "rail_yard", "rail_yard", 1879, 9999, "estimated",
         "https://www.oaklandlocalwiki.org/",
         "Central / Southern Pacific yards and car shops between 7th St and the mole (on the 1899/1915 sheets); "
         "Union Pacific's Oakland intermodal yard today. Founding year estimated (Oakland mole works 1879-82).",
         "Alameda", [osm("63eb46c6", "b6ebadb0", "ea323d45")], date=True, founded=1879),
    site("oakland_port_terminals", "Port of Oakland marine terminals", "Port of Oakland", "port_terminal",
         "industrial", 1962.7, 9999, "exact", "https://www.oaklandca.gov/files/assets/city/v/1/public-meetings/"
         "landmarks-preservation-advisory-board/2021/er18-016-waterfront-ballpark-district-deir-landmarks-board-report.pdf",
         "Container terminals dated as in data/research/landmarks_ports.md (container yard years): Outer Harbor / "
         "Sea-Land Sep 1962, Berths 23-26 1977, Seventh St Terminal 1968-69 (on 1967-71 BART-spoil fill), APL 1972, "
         "Hanjin 2001 and SSA Nov 2002 (both on the Naval Supply Center: see vanished_sites/oakland_nsc), Howard "
         "Terminal (Howard Co. coal / break-bulk terminal from the 1920s, container terminal 1982).", "Alameda",
         [osm("fad21de1", "b18f3703", start=1962.7, note="Outer Harbor (Sea-Land) container terminal Sep 1962"),
          osm("0dd679c9", "19119654", start=1977, note="Berths 23-26 (Maersk / TransBay terminals) 1977"),
          osm("6d1ea5cf", "db0a0a8b", start=1968.5, note="Seventh Street Terminal north berths (30-34)"),
          osm("99aef70c", start=1969.5, note="Seventh Street Terminal tip (Ben E. Nutter, Berths 35-38)"),
          osm("94f268a4", start=1972.5, conf="estimated", note="APL terminal, Berths 60-63 (year estimated)"),
          osm("8fdc0b8a", start=2001.3, note="Hanjin terminal on the former Naval Supply Center"),
          osm("65294082", start=2002.9, note="SSA terminal on the former Naval Supply Center"),
          osm("d189fbdf", start=1925, conf="estimated",
              note="Howard Terminal: waterfront terminal from the 1920s (year estimated), containers 1982-2014"),
          osm("6772f314", "8d6d5508", start=2002, conf="estimated",
              note="intermodal / truck yards on former Army Base and SP ground (year estimated)")],
         date=False),
    site("moore_dry_dock", "Moore Dry Dock Co. (Moore & Scott Iron Works), Oakland", "Moore Dry Dock", "shipyard",
         "industrial", 1909, 9999, "estimated", W + "Moore_Dry_Dock_Company",
         "Moore & Scott bought W. A. Boole & Son's yard at the foot of Adeline St in 1909; Moore Shipbuilding 1917, "
         "Moore Dry Dock 1922; over 100 ships in WWII; closed 1961; site now Schnitzer Steel / Radius Recycling and "
         "the Howard Terminal edge. Outline: the yard's piers and shops on the 1946-photo Oakland West sheet "
         "(read +-40 m); the ground stays industrial after 1961.", "Alameda",
         [traced((-122.302, 37.805), [(500, -1030), (500, -800), (950, -760), (1150, -800), (1350, -900),
                                      (1350, -1050), (900, -1080)], T + "CA_Oakland%20West_293623_1949_24000_geo.tif")],
         label_years=(1909, 1961), date=False),
    site("bethlehem_alameda", "Bethlehem Steel Alameda Works shipyard (Union Iron Works Alameda)",
         "Bethlehem Shipyard", "shipyard", "industrial", 1916, 1956, "estimated", W + "Alameda_Works_Shipyard",
         "United Engineering Works yard bought 1916 by Union Iron Works (Bethlehem): the Alameda Works; Bethlehem "
         "Alameda Shipyard in WWII; closed 1956. The site became Marina Village (offices / research park, 1980s); "
         "only the Union Iron Works Powerhouse (NRHP 1980) remains. Outline: today's Marina Village office / research "
         "park polygons (approximate).", "Alameda", [osm("69060cf7", "20580f0a")], date=False),
    site("alameda_coast_guard", "Coast Guard Island (Government Island), Alameda", "Coast Guard Island", "military",
         "military", 1942, 9999, "estimated", W + "Coast_Guard_Island",
         "Government Island, made from estuary dredge spoil 1913, became the Coast Guard training station in 1942; "
         "Coast Guard Island since 1982.", "Alameda", [osm("4d12d3b4")], date=True, founded=1942),
    site("camp_parks", "Camp Parks / Camp Shoemaker / Shoemaker Naval Hospital / Parks AFB (Parks RFTA)",
         "Camp Parks", "military", "military", 1942, 9999, "exact", W + "Camp_Parks",
         "Navy Seabee base Camp Parks, Camp Shoemaker and Shoemaker Naval Hospital built 1942-43; Parks Air Force "
         "Base 1951-59; Army reserve training area since 1959 (most WWII buildings demolished; the cantonment's "
         "western half became Dublin housing). Training ground east of the cantonment is open_works.", "Alameda",
         [osm("0e39ee81"), osm("fcd7495d", cover="open_works", note="training area (open ground)")],
         date=True, founded=1942),
    site("llnl", "Naval Air Station Livermore / Lawrence Livermore National Laboratory", "Lawrence Livermore Lab",
         "military", "industrial", 1942, 9999, "exact", W + "Lawrence_Livermore_National_Laboratory",
         "Naval Air Station Livermore 1942-46 (training field); the University of California Radiation Laboratory's "
         "Livermore branch opened on the old air station in Sep 1952 (LLNL).", "Alameda",
         [osm("46577255")], date=True, founded=1942),
    site("sandia_livermore", "Sandia National Laboratories, Livermore", "Sandia Livermore", "military", "industrial",
         1956, 9999, "exact", W + "Sandia_National_Laboratories",
         "Sandia's Livermore site opened 1956 beside the Radiation Laboratory.", "Alameda",
         [osm("affab8d3")], date=True, founded=1956),
    site("gm_fremont", "GM Fremont Assembly / NUMMI / Tesla Fremont Factory", "Tesla Factory (GM Fremont)",
         "factory", "industrial", 1962, 9999, "exact", W + "Tesla_Fremont_Factory",
         "General Motors Fremont Assembly opened 1962 (closed 1982), NUMMI 1984-2010, Tesla from 2010.", "Alameda",
         [osm("86bd3c14")], date=True, founded=1962),
    site("livermore_gravel", "Livermore-Amador Valley sand and gravel pits (Kaiser Radum, Pleasanton)",
         "Pleasanton Gravel Pits", "quarry", "quarry_pit", 1931, 9999, "estimated",
         "https://nps.acgov.org/nps-assets/docs/LAVQAR%20Specific%20Plan%20Draft%20EIR%20(1979).pdf",
         "Henry J. Kaiser's original Radum aggregate plant (1931) on the Arroyo del Valle / Arroyo Mocho gravels; "
         "the 3,820-acre mining area between Livermore and Pleasanton was worked by three operators by 1979 "
         "(LAVQAR plan). Today's pit outline (OSM); growth not traced.", "Alameda",
         [osm("89167eb4")], date=False),
    site("sunol_quarries", "Sunol Valley quarries (Mission Valley Rock, Hanson / CEMEX)", "Sunol Quarries", "quarry",
         "quarry_pit", 1950, 9999, "estimated", "https://www.sfpuc.org/",
         "Sand and gravel pits on SFPUC land in the Sunol Valley along Alameda Creek; start year estimated (1950s).",
         "Alameda", [osm("d85c396e", "9d0cd5ce", "5f9d8e88")], date=False),
    site("altamont_landfill", "Altamont Landfill", "Altamont Landfill", "other", "landfill", 1980, 9999, "exact",
         "https://www.calrecycle.ca.gov/", "Opened 1980 in the Altamont hills.", "Alameda",
         [osm("c083068a")], date=False),
    site("vasco_road_landfill", "Vasco Road Landfill", "Vasco Road Landfill", "other", "landfill", 1963, 9999,
         "estimated", "https://www.calrecycle.ca.gov/", "Livermore canyon landfill; opening year estimated (1960s).",
         "Alameda", [osm("9b88769d")], date=False),
    # ------------------------------------------------------------------ San Francisco
    site("pier70_union_iron_works", "Union Iron Works / Bethlehem Steel San Francisco Yard (Pier 70)",
         "Union Iron Works (Pier 70)", "shipyard", "industrial", 1884, 9999, "exact", W + "Pier_70",
         "Union Iron Works moved to Potrero Point in 1884; Bethlehem Shipbuilding from 1905; ship repair (Todd, BAE) "
         "to 2017; Pier 70 mixed-use redevelopment since 2018 (industrial ground continues).", "San Francisco",
         [osm("e99a6779", "e3364983", "b3d797ec")], date=True, founded=1884),
    site("potrero_power", "Potrero Gas Works and Power Station (PG&E)", "Potrero Power Station", "power_plant",
         "industrial", 1901, 2011, "estimated", W + "Potrero_Generating_Station",
         "SF Gas & Electric's Potrero works (Station A, 1901; gas works on the point earlier); PG&E's Unit 3 1965; "
         "closed 2011, demolished; Power Station development from 2020. Years of the earliest works estimated.",
         "San Francisco", [osm("0a18c9f9")], date=True, founded=1901),
    site("bayshore_yard", "Southern Pacific Bayshore Yard and roundhouse", "Bayshore Yard", "rail_yard", "rail_yard",
         1907, 1982, "estimated", W + "Bayshore_Roundhouse",
         "Yard, shops and roundhouse of the 1907 Bayshore Cutoff (roundhouse 1910 still stands); the yard closed in "
         "the early 1980s (end estimated); Brisbane Baylands brownfield since.", "San Mateo",
         [osm("0d7285fd", "d1c1adc7")], date=True, founded=1907),
    site("schlage_lock", "Schlage Lock factory, Visitacion Valley", "Schlage Lock", "factory", "industrial", 1926,
         1999, "estimated", W + "Visitacion_Valley,_San_Francisco",
         "Schlage Lock Co. factory on Bayshore Blvd 1926-1999 (demolished 2000s; Visitacion Valley redevelopment); "
         "outline: today's construction site.", "San Francisco", [osm("dd25fe3d")], date=False),
    # ------------------------------------------------------------------ San Mateo
    site("ox_mountain_landfill", "Ox Mountain (Corinda Los Trancos) Landfill", "Ox Mountain Landfill", "other",
         "landfill", 1976, 9999, "estimated", "https://www.calrecycle.ca.gov/",
         "Canyon landfill above Half Moon Bay, opened 1976 (estimated).", "San Mateo",
         [osm("55769e62", "2ffe4a65")], date=False),
    site("guadalupe_valley_quarry", "Guadalupe Valley Quarry, Brisbane", "Brisbane Quarry", "quarry", "quarry_pit",
         1950, 9999, "estimated", W + "Brisbane,_California",
         "Rock quarry in the Guadalupe Valley on San Bruno Mountain's south flank; start year estimated (mid-20th c.).",
         "San Mateo", [osm("460249a2")], date=False),
    # ------------------------------------------------------------------ Santa Clara
    site("permanente", "Permanente Quarry and cement plant (Kaiser Permanente Cement; Hanson; Lehigh)",
         "Permanente Quarry", "quarry", "quarry_pit", 1903, 9999, "exact", W + "Permanente_Quarry",
         "Limestone quarried on Permanente Creek from c.1902-03 (Granite Rock Co.; the 'El Dorado Sugar Co. quarry' "
         "of 1906), intermittently to 1934; Henry J. Kaiser's Permanente Corp. built the quarry and the cement plant "
         "from June 1939 (first cement Dec 1939, for Shasta Dam); Kaiser Cement 1964, Hanson 1986, Lehigh; kiln "
         "closed 2020, quarry closure agreed 2023. The pit is traced from the USGS editions (see parts).",
         "Santa Clara",
         [traced((-122.115, 37.317), PERM03, T + "CA_Palo%20Alto_298463_1943_62500_geo.tif", start=1903,
                 conf="estimated", note="early limestone quarry at the quarry symbol of the 1939/1940 1:62,500 "
                                       "sheets; extent estimated"),
          traced((-122.104, 37.315), PERM_PLANT, T + "CA_Cupertino_289702_1953_24000_geo.tif", start=1939.5,
                 cover="industrial", conf="exact", note="Permanente cement plant (1939), Cupertino 1953 sheet"),
          traced((-122.115, 37.317), PERM48, T + "CA_Cupertino_289702_1953_24000_geo.tif", start=1944,
                 note="pit on the 1948 photos (start = midpoint 1939.5-1948)"),
          files(["traced/permanente_1960.geojson"], start=1954,
                note="pit on the 1960 photos (Cupertino 1961; unwooded quarry ground, tools/tint.py open); "
                     "start = midpoint 1948-1960"),
          files(["traced/permanente_1968.geojson"], start=1964,
                note="pit on the 1968 photorevision; start = midpoint 1960-1968"),
          files(["traced/permanente_1979.geojson"], start=1973.5,
                note="pit on the 1979 photorevision (magenta overprint, Cupertino + Mindego Hill); "
                     "start = midpoint 1968-1979"),
          files(["traced/permanente_1991.geojson"], start=1985,
                note="disturbed-ground tint of the 1991 Cupertino + Mindego Hill sheets; start = midpoint 1979-1991"),
          osm("d606bcce", start=2005, conf="estimated",
              note="today's quarry outline (OSM; incl. the West Materials Storage Area of the 1985 reclamation "
                   "plan and the 2012 East storage area); start = midpoint 1991-2020, estimated")],
         date=True, founded=1939.5),
    site("stevens_creek_quarry", "Stevens Creek Quarry", "Stevens Creek Quarry", "quarry", "quarry_pit", 1950,
         9999, "estimated", "https://www.stevenscreekquarry.com/",
         "Rock quarry south of Permanente on Stevens Creek; start year estimated (mid-20th c.).", "Santa Clara",
         [osm("0626534a")], date=False),
    site("lockheed_sunnyvale", "Lockheed Missiles & Space Co., Sunnyvale (Lockheed Martin Space)",
         "Lockheed Missiles & Space", "factory", "industrial", 1956, 9999, "exact",
         W + "Lockheed_Martin_Space",
         "Lockheed Missiles and Space Division moved to its new Sunnyvale plant beside NAS Moffett in 1956 "
         "(Polaris, Agena, satellites); the Navy's NIROP / Strategic Systems Programs plant alongside.",
         "Santa Clara", [osm("012ea709"), osm("ac3cf992", note="Navy plant (NIROP / SSP) beside Lockheed")],
         date=True, founded=1956),
    site("hendy_westinghouse", "Joshua Hendy Iron Works / Westinghouse Marine Division, Sunnyvale",
         "Hendy Iron Works (Westinghouse)", "factory", "industrial", 1906, 9999, "exact",
         W + "Joshua_Hendy_Iron_Works",
         "Hendy Iron Works moved to Sunnyvale after the 1906 earthquake; Liberty ship engines in WWII; Westinghouse "
         "from 1947; Northrop Grumman Marine Systems since 1996.", "Santa Clara",
         [osm("315d7b64")], date=True, founded=1906),
    site("newby_island_landfill", "Newby Island Landfill", "Newby Island Landfill", "other", "landfill", 1938, 9999,
         "estimated", "https://www.republicservices.com/municipality/newby-island",
         "Open burn dump from 1938 (operator; other sources 1932), sanitary landfill from 1956, on the Coyote Creek "
         "marsh island.", "Santa Clara", [osm("953d142a")], date=False),
    site("guadalupe_landfill", "Guadalupe Landfill, San José", "Guadalupe Landfill", "other", "landfill", 1930,
         9999, "estimated", "https://www.calrecycle.ca.gov/",
         "Canyon landfill in the Almaden foothills; opening year estimated.", "Santa Clara",
         [osm("33cd62d9")], date=False),
    # ------------------------------------------------------------------ Marin
    site("marinship", "Marinship (Marin Shipbuilding Co.), Sausalito", "Marinship", "shipyard", "industrial", 1942,
         9999, "exact", W + "Marinship",
         "Bechtel's Marinship built 93 Liberty ships and tankers, Mar 1942 - Sep 1945 (yard closed 1946); the Army "
         "Corps of Engineers' Bay Model is in its warehouse; the ground stays industrial (boatyards). Outline read on "
         "the San Francisco North 1:24k sheet (1946 photos): ways, outfitting docks, plate shop; NW end estimated "
         "(off the sheet).", "Marin",
         [traced((-122.497, 37.866), [(-700, 700), (-360, 560), (-60, 420), (40, 340), (430, 120), (520, -100),
                                      (330, -260), (100, -190), (-360, 80), (-700, 250)],
                 T + "CA_San%20Francisco%20North_300059_1947_24000_geo.tif")], label_years=(1942, 1946), date=False),
    site("san_rafael_quarry", "San Rafael Rock Quarry (McNear brickyard), Point San Pedro", "San Rafael Rock Quarry",
         "quarry", "quarry_pit", 1929, 9999, "exact", "https://sprcoalition.org/?p=1834",
         "McNear brickyard on Point San Pedro from the late 19th century (1870s-1900, sources differ); hard-rock "
         "quarrying from 1929.", "Marin", [osm("1f3cfce5")], date=False),
    site("redwood_landfill", "Redwood Landfill, Novato", "Redwood Landfill", "other", "landfill", 1958, 9999,
         "estimated", "https://www.calrecycle.ca.gov/", "Bayside landfill on the Petaluma River marsh; opened "
         "late 1950s (estimated).", "Marin", [osm("249fd95a")], date=False),
    site("fort_baker", "Fort Baker (Lime Point Military Reservation)", "Fort Baker", "military", "military", 1897,
         9999, "exact", W + "Fort_Baker",
         "Lime Point reservation from 1866; named Fort Baker 1897; the post's barracks, officers' row and parade "
         "ground were built 1901-1910 (Colonial Revival); Army post until 2000 (to the NPS 2002; Cavallo Point "
         "lodge 2008). Outline: hull of the post's buildings.", "Marin",
         [hull(-122.4775, 37.8355, 380)], label_years=(1897, 2000), date=True, founded=1901),
    site("fort_barry", "Fort Barry", "Fort Barry", "military", "military", 1904, 9999, "exact",
         W + "Fort_Barry",
         "Named 1904 for the Marin Headlands batteries; the cantonment (barracks, officers' quarters, hospital) was "
         "built 1908-1912; Nike site SF-88 1954-74; to the NPS (GGNRA) 1972-74. Outline: hull of the post's "
         "buildings.", "Marin", [hull(-122.5245, 37.8295, 420)], label_years=(1904, 1974), date=True, founded=1907),
    site("fort_cronkhite", "Fort Cronkhite", "Fort Cronkhite", "military", "military", 1937, 9999, "exact",
         W + "Fort_Cronkhite",
         "Established 1937; the WWII wooden cantonment (barracks, mess halls) was built 1941; GGNRA since 1974. "
         "Outline: hull of the post's buildings.", "Marin", [hull(-122.5375, 37.8325, 330)], label_years=(1937, 1974), date=True,
         founded=1941),
    site("fort_mcdowell", "Fort McDowell, Angel Island (East Garrison)", "Fort McDowell", "military", "military",
         1900, 9999, "exact", W + "Angel_Island_(California)",
         "Camp Reynolds (West Garrison) 1863; Fort McDowell 1900; the East Garrison's concrete barracks, hospital and "
         "mess hall were built 1910-11 (recruit depot / Discharge Depot); closed 1946; state park since 1954-63. "
         "Outline: hull of the East Garrison buildings.", "Marin", [hull(-122.4225, 37.8650, 300)], label_years=(1900, 1946), date=True,
         founded=1909),
    site("hamilton_field", "Hamilton Field / Hamilton Air Force Base, Novato", "Hamilton Field", "military",
         "military", 1932, 9999, "exact", W + "Hamilton_Army_Airfield",
         "Construction from 1932 (dedicated May 1935) with Spanish-revival barracks, officers' housing and hangars "
         "(historic district); Hamilton AFB 1947-1974, Army airfield to 1988; housing (Hamilton, Novato) from the "
         "1990s. Outline: hull of the base's buildings (the airfield itself is not drawn here).", "Marin",
         [hull(-122.5130, 38.0580, 1000, buffer_m=50)], label_years=(1932, 1988), date=True, founded=1932),
    # ------------------------------------------------------------------ Contra Costa quarries
    site("clayton_quarries", "Mitchell Canyon / Clayton quarries (Clayton Quarry, Hanson)", "Clayton Quarries",
         "quarry", "quarry_pit", 1956, 9999, "estimated", W + "Clayton,_California",
         "Diabase rock quarries at the foot of Mount Diablo east of Clayton; start year estimated (1950s).",
         "Contra Costa", [osm("a44fd439", "d4fc409a", "7f68502b")], date=True, founded=1956),
]


# named buildings (known_dates_industrial.csv): point inside today's footprint
NAMED = [
    dict(id="ind_ford_richmond_assembly", name="Ford Richmond Assembly Plant (Craneway, Ford Point)",
         lat=37.910835, lon=-122.358419, start_year=1931, end_year=9999,
         source_url=W + "Ford_Assembly_Building_(Richmond,_California)",
         note="Albert Kahn plant opened 1931 (roll 1931); live map 1941 - moved by the land-year check: the fill "
              "zone under Ford Point is dated too late. Two identical Overture footprints (f881c874, 2f25de54).",
         county="Contra Costa"),
    dict(id="ind_winehaven_winery_n", name="Winehaven winery building (north)", lat=37.951636, lon=-122.417554,
         start_year=1907, end_year=9999, source_url=W + "Winehaven,_California",
         note="California Wine Association winery built 1907-08 (NRHP Winehaven Historic District); drawn on the "
              "1915 1:62,500 and 1947 1:24k sheets; live map 1993 (no roll year: imputed).", county="Contra Costa"),
    dict(id="ind_winehaven_winery_s", name="Winehaven winery building (south)", lat=37.949512, lon=-122.417635,
         start_year=1907, end_year=9999, source_url=W + "Winehaven,_California",
         note="As the north building; live map 1990 (imputed).", county="Contra Costa"),
    dict(id="ind_bayshore_roundhouse", name="Bayshore Roundhouse (Southern Pacific), Brisbane", lat=37.707393,
         lon=-122.400660, start_year=1910, end_year=9999, source_url=W + "Bayshore_Roundhouse",
         note="Built 1910 for the Bayshore Cutoff yard (NRHP); live map 1992 (no roll year: imputed).",
         county="San Mateo"),
]
