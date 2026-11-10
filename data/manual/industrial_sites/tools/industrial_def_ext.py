"""Military and industrial sites of the counties added with the ten-county extent (2026-11):
Solano, Napa, Sonoma, Santa Cruz, east Contra Costa (Pittsburg - Antioch - Oakley) and south
Santa Clara. Definitions for build_ext.py, in the format of industrial_def.py (same helpers).

Extra part options understood by build_ext.py:
  clip=(frame, ring)   keep only the part of the outline inside this ring (local metres of `frame`);
                       used to split an OSM outline into growth stages read on the topo editions
Label periods: the consumers draw ONE label per site_id (its name_label over [label_start,
label_end)). Where the name of a place changed (Fairfield-Suisun Army Air Base -> Travis AFB,
Two Rock Ranch Station -> Coast Guard Training Center, Columbia Steel -> USS-POSCO, Basalt Rock ->
Kaiser Steel -> Napa Pipe, Benicia Arsenal -> industrial park) the other names are label-only sites
(`label_only`): the same outline with cover `open_works`, which the terrain does not paint.

Facts are cited per site; anything estimated says so in `conf` / `note`.
"""
import math

from industrial_def import T, W, box, hull, osm, site, traced  # noqa: F401

CPUC = "https://files.cpuc.ca.gov/LegacyCPUCDecisionsAndResolutions/Decisions/"


def label_only(site_id, name, label, kind, start, end, src, note, county, parts):
    """A name period of a site whose ground belongs to another site_id: label only."""
    return site(site_id, name, label, kind, "open_works", start, end, "exact", src, note, county, parts,
                label_years=(start, end), date=False, floor=False)


def circle(cx, cy, r, n=14):
    return [(cx + r * math.cos(t / n * 2 * math.pi), cy + r * math.sin(t / n * 2 * math.pi)) for t in range(n)]


BIG = 60000
# ---- frames (lon, lat) of the renders the rings were read on (tools/montage.py, grid labels)
F_MI = (-122.270, 38.094)     # Mare Island
F_BA = (-122.130, 38.062)     # Benicia (overview)
F_BA2 = (-122.133, 38.052)    # Benicia Arsenal post
F_TR = (-121.940, 38.265)     # Travis
F_SK = (-122.372, 38.188)     # Skaggs Island
F_CS = (-121.884, 38.011)     # Camp Stoneman
F_AN = (-121.765, 38.013)     # Antioch, Wilbur Avenue
F_LH = (-122.1805, 38.1152)   # Lake Herman quarry
F_NQ = (-122.256, 38.266)     # Napa quarry
F_WQ = (-121.6164, 36.9013)   # Wilson Quarry, Aromas

MI51 = T + "CA_Mare%20Island_292724_1951_24000_geo.tif"
MI16 = T + "CA_Mare%20Island_298113_1916_62500_geo.tif"
MI42 = T + "CA_Mare%20Island_465907_1942_62500_geo.tif"
# Mare Island: the yard as built up on the 1916 sheet (1914 survey) ends about y = 1450 m of F_MI;
# north of it the 1914 survey shows the river / tule, the 1942 sheet streets and shops
MI_SOUTH = (F_MI, [(-BIG, -BIG), (BIG, -BIG), (BIG, 1450), (-BIG, 1450)])
MI_NORTH = (F_MI, [(-BIG, 1450), (BIG, 1450), (BIG, BIG), (-BIG, BIG)])
MI_DEPOT = (F_MI, [(-BIG, -BIG), (BIG, -BIG), (BIG, -700), (-BIG, -700)])
# the post behind the yard (Officers' Row on Walnut Avenue, Marine barracks, hospital, quarters):
# urban tint of the Mare Island 1:24k sheet of 1951 (1948 photos) south of the 1914 yard limit
MI_POST = [(-450, 1300), (-750, 1250), (-300, 650), (-350, 400), (-300, 0), (-50, -300), (50, -550), (350, -900),
           (1050, -750), (600, -100), (150, 600), (-200, 1100)]

SITES_EXT = [
    # ------------------------------------------------------------------ Solano: Navy, Army, Air Force
    site("mare_island", "Mare Island Navy Yard / Mare Island Naval Shipyard", "Mare Island Naval Shipyard", "shipyard",
         "industrial", 1854, 9999, "exact", W + "Mare_Island_Naval_Shipyard",
         "First U.S. Navy base on the Pacific: shipbuilding and repair began 16 Sep 1854 (Cdr. Farragut); Dry Dock 1 "
         "1872-91, Dry Dock 2 1899-1910; causeway to Vallejo 1919; wartime expansion from 1938 (usable area about 635 "
         "acres before, about 1,500 acres by 1945, much of it reclaimed land at the North End); closed 31 Mar 1996. "
         "Yard = OpenStreetMap 'Mare Island Navy Yard (historical)' outline, split where the Mare Island 1:62,500 "
         "sheet of 1916 (1914 survey) ends the built-up yard; the 1942 sheet draws streets and shops north of it.",
         "Solano",
         [osm("df4179de", clip=MI_SOUTH, on_top=True,
              note="the yard along Mare Island Strait as built up on the 1916 sheet (1914 survey): shops of 1854-58, "
                   "dry docks 1 and 2, coal sheds"),
          osm("df4179de", clip=MI_NORTH, on_top=True, start=1928, conf="estimated", src=MI42,
              note="north yard (causeway of 1919, building ways): river / tule on the 1914 survey, built up on the "
                   "1942 sheet; start = midpoint of the two editions (estimated)"),
          osm("32dd6cc3", "5f145e6e", "02383327", "67e8ec36", "721396ea", on_top=True, start=1940, conf="estimated",
              src=MI42, note="North End: land reclaimed in the 1938-45 expansion (Wikipedia), streets on the 1942 "
                             "sheet, shops and building ways 4-8; start estimated"),
          traced(F_MI, MI_POST, MI51, cover="military", conf="estimated",
                 note="the post behind the yard (Officers' Row, Marine barracks, hospital, quarters): urban tint of "
                      "the 1951 sheet (1948 photos) where the 1916 sheet already draws buildings; outline +-60 m"),
          osm("e7fc672c", clip=MI_DEPOT, cover="open_works", start=1857, conf="estimated",
              src="https://noehill.com/solano/nat1975002103.aspx",
              note="south end: Naval Ammunition Depot (stone magazines A-1, A-4, A-20 of 1857-64, brick magazines "
                   "of the 1890s; NHL Area B), cemetery 1856, golf course on the hill - open ground with magazines; "
                   "outline = the south part of the OSM Navy investigation area")],
         label_years=(1854, 1996.25), date=True, founded=1854),

    site("benicia_arsenal", "Benicia Barracks (1849) and Benicia Arsenal", "Benicia Arsenal", "military", "military",
         1851, 9999, "estimated", W + "Benicia_Arsenal",
         "Military reserve of 1847 east of Benicia; Benicia Barracks from 9 Apr 1849; the first Ordnance supply depot "
         "of the West 1851 (designated Benicia Arsenal 1852); Camel Barns 1855; deactivated 1963, closed 1964; the "
         "city made the industrial park of it. Outline = the built post (storehouses and shops on the shore, "
         "quarters and barracks around Pine Lake) between the reservation line on the west and the railroad along "
         "the strait, read on the Benicia 1:24k sheet of 1959 with its 1968 photorevision, +-50 m - about the "
         "252-acre reserve of 1847; the hill land added later (magazines) is not outlined.", "Solano",
         [traced(F_BA2, [(-750, -870), (-750, -300), (-620, -60), (-520, 250), (-420, 600), (-150, 680), (250, 600),
                         (330, 300), (380, 0), (430, -300), (420, -600), (330, -820), (0, -860)],
                 T + "CA_Benicia_288324_1959_24000_geo.tif")],
         label_years=(1851, 1964), date=True, founded=1851, floor=False),
    label_only("benicia_industrial_park", "Benicia Industrial Park and Port of Benicia (on the Arsenal lands)",
               "Benicia Industrial Park", "other", 1965, 9999, W + "Benicia,_California",
               "The Arsenal closed 1960-64 and the city created an industrial park on its land (Wikipedia: Benicia); "
               "label from 1965 (estimated: the year after the closure). Open_works on purpose: the warehouses went "
               "up over decades and date their own ground. Outline = OSM 'Benicia Industrial Park' and 'Port of "
               "Benicia'.", "Solano", [osm("83256cc5", "5e2ebe8e", "f760ac05", "e8147f94", conf="estimated")]),
    site("benicia_refinery", "Humble Oil Benicia Refinery (Exxon 1972, Valero 2000)", "Benicia Refinery", "refinery",
         "tank_farm", 1969, 9999, "exact", W + "Benicia_Refinery",
         "Built 1968 for Humble Oil on the Arsenal's hill land, completed 1969; Exxon from 1972; Valero from 2000 "
         "(closure announced for 2026). 'Oil Refinery' in the photorevision magenta of the Benicia sheet (1968).",
         "Solano", [osm("bc1632f8")], date=True, founded=1969),

    site("travis_afb", "Fairfield-Suisun Army Air Base (1942) / Travis Air Force Base (1951)", "Travis AFB",
         "military", "military", 1943, 9999, "exact", W + "Travis_Air_Force_Base",
         "Construction of Fairfield-Suisun Army Air Base began 1942 (Air Transport Command from Oct 1942); "
         "Fairfield-Suisun AFB 1947; renamed Travis AFB 1951. Cantonment = urban tint of the Vacaville 1:62,500 "
         "sheet of 1953 (1949 photos); the whole base = OSM outline (open_works: the airfield and its runways are "
         "the airports layer's).", "Solano",
         [traced(F_TR, [(-950, 70), (-950, 1190), (-700, 1640), (600, 1640), (600, 70)],
                 T + "CA_Vacaville_301915_1953_62500_geo.tif", conf="estimated",
                 note="cantonment (barracks, shops, hospital) as tinted on the 1953 sheet (1949 photos), +-80 m; "
                      "built 1942-43"),
          osm("4820365c", cover="open_works", start=1942, note="base boundary of today")],
         label_years=(1951, 9999), date=True, founded=1942),
    label_only("fairfield_suisun_aab", "Fairfield-Suisun Army Air Base (Air Force Base 1947-51)",
               "Fairfield-Suisun Army Air Base", "military", 1942, 1951, W + "Travis_Air_Force_Base",
               "Name of Travis AFB before 1951 (Fairfield-Suisun Air Force Base from 1947).", "Solano",
               [osm("4820365c")]),

    site("skaggs_island", "Naval Radio Station / Naval Security Group Activity, Skaggs Island",
         "Skaggs Island Naval Station", "military", "military", 1942, 2012, "estimated",
         W + "Skaggs_Island_Naval_Communication_Station",
         "The Navy bought 3,310 acres of the diked island in 1941; communications station 1942-1993; antennas and "
         "all remaining buildings removed by 2013 (end of the ground estimated 2012); San Pablo Bay NWR since 2011. "
         "Outline = the station's buildings and housing on the Sears Point 1:24k sheet of 1951 (1948 photos), "
         "+-40 m; the antenna fields (hay land) are not outlined.", "Sonoma",
         [traced(F_SK, [(-1620, 1260), (-1450, 1340), (-1280, 1290), (-1300, 1000), (-1294, 775), (-1334, 645),
                        (-1494, 645), (-1554, 765), (-1600, 820), (-1650, 1050)],
                 T + "CA_Sears%20Point_300386_1951_24000_geo.tif")],
         label_years=(1942, 1993), date=False),

    site("tracen_petaluma", "Two Rock Ranch Station (Army, 1942-71) / Coast Guard Training Center Petaluma",
         "Coast Guard Training Center Petaluma", "military", "military", 1942.6, 9999, "exact",
         W + "Training_Center_Petaluma",
         "Army signal-intercept station established 7 Aug 1942 on 876 acres of ranch land (camouflaged as a dairy "
         "farm); closed 30 June 1971; Coast Guard training center from 1 July 1971. Built area = hull of the "
         "station's buildings; the reservation (antenna fields) = OSM outline, open_works.", "Sonoma",
         [hull(-122.7945, 38.2505, 650, buffer_m=40), osm("542bf9c7", cover="open_works")],
         label_years=(1971.5, 9999), date=True, founded=1942.6),
    label_only("two_rock_ranch_station", "Two Rock Ranch Station (Army Security Agency)", "Two Rock Ranch Station",
               "military", 1942.6, 1971.5, W + "Training_Center_Petaluma",
               "The Army's name of the station, 7 Aug 1942 - 30 June 1971.", "Sonoma", [osm("542bf9c7")]),

    # ------------------------------------------------------------------ east Contra Costa
    site("camp_stoneman", "Camp Stoneman (San Francisco Port of Embarkation staging area)", "Camp Stoneman",
         "military", "military", 1942.4, 9999, "estimated", W + "Camp_Stoneman",
         "Army staging camp opened 28 May 1942, decommissioned 1954; the land went back to the town (schools, "
         "housing, shops), so the ground stays built-up after 1954 (no cleared stage: today's houses date it). "
         "Outline = the camp's street grid (tint) and warehouse tracks south of the railroad / "
         "today's SR-4 on the Honker Bay and Antioch North 1:24k sheets of 1953 (1949 photos), +-100 m.",
         "Contra Costa",
         [traced(F_CS, [(-900, 220), (-470, 300), (-450, 500), (650, 440), (1100, 300), (1550, 190), (1950, 100),
                        (1950, -150), (1620, -200), (1620, -1000), (700, -1000), (650, -780), (250, -620),
                        (-100, -420), (-600, -330), (-950, -150)], T + "CA_Honker%20Bay_291408_1953_24000_geo.tif")],
         label_years=(1942.4, 1954), date=False),
    site("columbia_steel", "Columbia Steel Co. (U.S. Steel 1930; USS-POSCO Industries 1986-2023), Pittsburg",
         "Columbia Steel", "factory", "industrial", 1910, 9999, "exact", W + "Columbia_Steel_Company",
         "Columbia Steel opened its Pittsburg plant in 1910 (first heat 22 Nov 1910); U.S. Steel subsidiary 1930; "
         "USS-POSCO Industries joint venture 1986; shutdown announced 2022 for 2023. 'Steel Mill' on the Antioch "
         "North 1:24k sheets of 1953 (1949 photos) and 1978 over the whole OSM outline.", "Contra Costa",
         [osm("43797ad4")], label_years=(1910, 1986), date=True, founded=1910),
    label_only("uss_posco", "USS-POSCO Industries (UPI), Pittsburg", "USS-POSCO Industries", "factory", 1986, 2023.9,
               W + "Columbia_Steel_Company",
               "Joint venture of U.S. Steel and Pohang Iron and Steel 1986; U.S. Steel alone from 2020; the mill shut "
               "down in 2023.", "Contra Costa", [osm("43797ad4")]),
    site("dow_pittsburg", "Dow Chemical Co., Pittsburg (Great Western Electro-Chemical Co. plant until 1939)",
         "Dow Chemical", "chemical", "industrial", 1939, 9999, "estimated",
         "https://clui.org/ludb/site/dow-chemical-pittsburg",
         "Dow bought the chlorine / caustic plant of the Great Western Electro-Chemical Co. in 1939 - its first "
         "site outside Michigan (CLUI: 'built in 1939'; Contra Costa Health, https://www.cchealth.org/"
         "health-and-safety-information/hazmat-programs/refinery-and-industry-safety-reports/"
         "rmp-corteva-agriscience). The older plant's founding year was not verified, so "
         "the ground is dated from 1939 only and footprints are not floored. Plant drawn on the Antioch North sheet "
         "of 1953 (1949 photos). Outline = OSM industrial outline east of Loveridge Road.", "Contra Costa",
         [osm("a2e16840")], date=False, floor=False),
    site("pittsburg_power_plant", "PG&E Pittsburg Steam Plant / Pittsburg Power Plant (Mirant, NRG)",
         "Pittsburg Power Plant", "power_plant", "industrial", 1954, 9999, "exact",
         "https://clui.org/ludb/site/pittsburg-power-plant",
         "PG&E's Pittsburg Steam Plant: units 1-4 scheduled for June - December 1954 (CPUC Decision 50035, 11 May "
         "1954: " + CPUC + "Decisions_D40600_to_D57800/D50035_19540511_A33182.pdf); units 5-7 1960-72.",
         "Contra Costa", [osm("df815ee4", "fc7e4705")], date=False),
    site("contra_costa_power_plant", "PG&E Contra Costa Power Plant, Antioch (Marsh Landing Generating Station 2013)",
         "Contra Costa Power Plant", "power_plant", "industrial", 1951, 9999, "exact",
         CPUC + "Decisions_D57801_to_D73750/D63489_19620327_A43983.pdf",
         "First three units in commercial operation 1951, two more 1953 (CPUC Decision 63489, 1962); units 1-5 "
         "retired 1995. Power house and oil tanks on the Antioch North sheet of 1953 (1949 photos, field check "
         "1953). Outline = OSM 'Contra Costa Power Plant' and 'Marsh Landing Generating Station'.", "Contra Costa",
         [osm("16a9e9d3", "87143170")], date=False),
    site("antioch_paper_mills", "Fibreboard San Joaquin kraft mill (1949) and Crown Zellerbach Antioch mill (1957; "
         "Gaylord Container 1986-2002), Wilbur Avenue", "Antioch Paper Mills", "factory", "industrial", 1949, 9999,
         "exact", W + "Gaylord_Container_Corporation",
         "Fibreboard's kraft pulp and board mill of 1949 (Louisiana-Pacific; Gaylord's 'east mill' 1988, shut "
         "Feb 1991) and next to it Crown Zellerbach's mill and converting complex of 1957 (Gaylord Container 1986; "
         "closed after Temple-Inland bought Gaylord in 2002); both demolished. Outline = OSM industrial outline of "
         "the two mill sites (today an auto terminal), split between the two building groups of the Antioch North "
         "sheet of 1978; the 1953 sheet (1949 photos) draws only the east mill.", "Contra Costa",
         [osm("5e8c8a12", clip=(F_AN, [(-700, -BIG), (BIG, -BIG), (BIG, BIG), (-700, BIG)]),
              note="east mill: Fibreboard San Joaquin mill, 1949"),
          osm("5e8c8a12", clip=(F_AN, [(-BIG, -BIG), (-700, -BIG), (-700, BIG), (-BIG, BIG)]), start=1957,
              note="west mill: Crown Zellerbach, opened 1957")],
         label_years=(1949, 2002), date=False),
    site("dupont_oakley", "E. I. du Pont de Nemours Oakley plant (tetraethyl lead, Freon, titanium dioxide)",
         "DuPont Oakley Plant", "chemical", "industrial", 1956, 1999, "estimated",
         "https://dtsc.ca.gov/wp-content/uploads/sites/31/2018/01/DuPont_FS_CorAction_0206.pdf",
         "Manufacturing plant 1956-1997 (DTSC fact sheet; State Lands Commission: to 1998), built to make the "
         "anti-knock agent tetraethyl lead; buildings demolished 1998-99. Outline = OSM outline of the logistics "
         "centre built on the plant site in the 2020s (estimated extent of the plant).", "Contra Costa",
         [osm("4a7a3d6c")], label_years=(1956, 1998), date=False),

    # ------------------------------------------------------------------ Santa Cruz County / Pajaro
    site("davenport_cement", "Santa Cruz Portland Cement Co. plant, Davenport (Pacific Cement & Aggregates 1956, "
         "Lone Star 1965, RMC 1998, Cemex 2005)", "Davenport Cement Plant", "cement", "industrial", 1906, 9999,
         "exact", W + "Davenport,_California",
         "Cement plant built 1906; shipping pier 1934; Cemex ceased operations and decommissioned the plant in "
         "2010 (it still stands).", "Santa Cruz", [osm("87fe73f1", "f5cc8212")],
         label_years=(1906, 2010), date=True, founded=1906),
    site("davenport_quarries", "Quarries of the Davenport cement plant (San Vicente limestone quarry; Bonny Doon "
         "limestone and shale quarries)", "Bonny Doon Quarries", "quarry", "quarry_pit", 1906, 9999, "estimated",
         W + "Davenport,_California",
         "The Santa Cruz Lime Co.'s quarry on San Vicente Creek was bought in 1905 and fed the 1906 cement plant "
         "('Quarry' on the Davenport 1:24k sheet of 1955, 1953 photos); the Bonny Doon limestone and shale quarries "
         "are not on that sheet and are bare ground on the 1991 sheet. Quarrying ended with the plant in 2010. "
         "Outlines = today's OSM quarry outlines (growth not traced).", "Santa Cruz",
         [osm("27e561ac", note="San Vicente limestone quarry, labelled 'Quarry' on the 1955 sheet"),
          osm("df9cdff7", "ee8cdc0f", start=1972, src=T + "CA_Davenport_289765_1991_24000_geo.tif",
              note="Bonny Doon limestone quarry and the shale quarry: absent on the 1955 sheet (1953 photos), bare "
                   "on the 1991 sheet; start = midpoint (estimated)")],
         label_years=(1906, 2010), date=False),
    site("california_powder_works", "California Powder Works, San Lorenzo River", "California Powder Works",
         "chemical", "industrial", 1864, 1914, "estimated", W + "California_Powder_Works",
         "First powder mill of the West: incorporated 1861, gunpowder from May 1864 on the river flat three miles "
         "above Santa Cruz (covered bridge 1872); closed 1914; the flat is the Masonic community of Paradise Park. "
         "Outline = hull of today's Paradise Park houses on the works' flat (estimated).", "Santa Cruz",
         [hull(-122.0449, 37.0098, 480, buffer_m=35)], date=False),
    site("lockheed_santa_cruz", "Lockheed Missiles & Space Santa Cruz Test Base (Lockheed Martin Santa Cruz "
         "Facility), Empire Grade", "Lockheed Santa Cruz Facility", "factory", "open_works", 1957, 9999, "exact",
         "https://localwiki.org/santacruz/Lockheed_Martin",
         "Missile and rocket-motor test base established 1957 off Empire Grade: test stands and bunkers in the "
         "forest (open_works). Outline = OSM industrial outline.", "Santa Cruz", [osm("d0f30959")], date=False),
    site("wilson_quarry", "Granite Rock Co. A. R. Wilson Quarry (Logan), Aromas", "Wilson Quarry (Graniterock)",
         "quarry", "quarry_pit", 1900, 9999, "estimated", W + "Graniterock",
         "Granite quarry on Judge Logan's ranch (Southern Pacific spur 'Logan'), Granite Rock Co. founded 14 Feb "
         "1900. Stages: the early pit (flooded 'Quarry Lake' of the Chittenden 1:24k sheet of 1955, 1952 photos); "
         "the pit in the photorevision magenta of the 1980 sheet (1978 photos); today's OSM outline.", "San Benito",
         [traced(F_WQ, circle(-800, 200, 170), T + "CA_Chittenden_289219_1955_24000_geo.tif",
                 note="early pit around 'Quarry Lake' (1955 sheet); extent estimated"),
          traced(F_WQ, [(-900, 900), (-500, 950), (-200, 700), (0, 300), (-50, 0), (-400, -100), (-800, 50),
                        (-1000, 400)], T + "CA_Chittenden_302703_1955_24000_geo.tif", start=1965,
                 note="pit of the 1980 photorevision (1978 photos); start = midpoint of the 1952 and 1978 photos"),
          osm("5bf7f82a", start=2000, note="today's outline; start = midpoint of the 1978 photos and today "
                                           "(estimated)")],
         date=False),
    site("buena_vista_landfill", "Buena Vista Landfill (Santa Cruz County) and Watsonville city landfill",
         "Buena Vista Landfill", "other", "landfill", 1965, 9999, "estimated",
         T + "CA_Watsonville%20West_301250_1954_24000_geo.tif",
         "No landfill on the Watsonville West 1:24k sheet of 1954 (1952 photos); disturbed ground along Gallighan "
         "Slough in the photorevision magenta of 1978: start = midpoint (estimated; opening year not researched). "
         "Outlines = OSM landfill outlines.", "Santa Cruz", [osm("9b40c4a1", "0235d057")], date=False),

    # ------------------------------------------------------------------ Napa
    site("kaiser_steel_napa", "Basalt Rock Co. shipyard and steel-pipe plant (1941) / Kaiser Steel Napa (1955) / "
         "Napa Pipe (1988-2004)", "Kaiser Steel Napa", "factory", "industrial", 1941, 9999, "exact",
         W + "Basalt_Rock_Company",
         "Basalt Rock Co. began building ships for the Navy at its Napa River plant in 1941 and made pipe after "
         "the war; Kaiser Steel bought the steel plant in 1955; Oregon Steel Mills ran it as Napa Pipe 1988-2004. "
         "'Rocktram', 'Steel-pipe Factory' and 'Dry Dock' on the Napa 1:24k sheet of 1951 (1948 photos). Outline = "
         "OSM industrial / brownfield outlines of the plant.", "Napa", [osm("d983a02a", "b7a0d1f9")],
         label_years=(1955, 1988), date=False),
    label_only("basalt_rock_napa", "Basalt Rock Co. shipyard and steel plant, Napa", "Basalt Rock Co.", "shipyard",
               1941, 1955, W + "Basalt_Rock_Company", "The plant's name until Kaiser Steel bought it in 1955.",
               "Napa", [osm("d983a02a", "b7a0d1f9")]),
    label_only("napa_pipe", "Napa Pipe (Oregon Steel Mills)", "Napa Pipe", "factory", 1988, 2004,
               W + "Basalt_Rock_Company", "Oregon Steel Mills, 1988-2004.", "Napa", [osm("d983a02a", "b7a0d1f9")]),
    site("napa_quarry", "Basalt Rock Co. quarry (Dillingham 1970s; Syar Napa Quarry 1986)",
         "Napa Quarry (Basalt Rock, Syar)", "quarry", "quarry_pit", 1920, 9999, "estimated",
         W + "Basalt_Rock_Company",
         "Basalt Rock Co. was founded in 1920 as a rock-quarrying operation south of Napa near Rocktram; Dillingham "
         "in the early 1970s, Syar Industries since 1986. 'Quarry' and 'Rock Quarry' symbols on the Napa 1:24k "
         "sheet of 1951 (1948 photos); large pits in the photorevision magenta of 1978. Stages: the two early "
         "quarries (extent estimated), then today's OSM quarry outlines from the midpoint of the 1948 and 1978 "
         "photos.", "Napa",
         [traced(F_NQ, circle(-250, -350, 110), T + "CA_Napa_293422_1951_24000_geo.tif",
                 note="'Rock Quarry' of the 1951 sheet; extent estimated"),
          traced(F_NQ, circle(-700, 100, 90), T + "CA_Napa_293422_1951_24000_geo.tif",
                 note="'Quarry' of the 1951 sheet; extent estimated"),
          osm("3f27ff1b", "50f91abd", "d5758dc9", "8c0c5da3", "aff60eb8", start=1963,
              src=T + "CA_Napa_293426_1951_24000_geo.tif",
              note="today's pits; drawn (smaller) in the 1978 photorevision; start = midpoint 1948 / 1978 photos")],
         date=False),

    # ------------------------------------------------------------------ Solano: plants, prisons, quarry, landfill
    site("cmf_vacaville", "California Medical Facility, Vacaville", "California Medical Facility", "other",
         "military", 1955, 9999, "exact", W + "California_Medical_Facility",
         "State prison medical facility, opened 1955. Outline = hull of its buildings (institutional ground, drawn "
         "like a post).", "Solano", [hull(-121.9772, 38.3289, 330, buffer_m=40)], date=False),
    site("csp_solano", "California State Prison, Solano", "California State Prison, Solano", "other", "military",
         1984, 9999, "exact", W + "California_State_Prison,_Solano",
         "Opened August 1984 next to the California Medical Facility. Outline = OSM.", "Solano",
         [osm("e3c87d46")], founded=1984.6, date=False),
    site("anheuser_busch_fairfield", "Anheuser-Busch Fairfield brewery", "Anheuser-Busch Brewery", "factory",
         "industrial", 1976, 9999, "exact", W + "Fairfield,_California",
         "Regional Budweiser brewery, operated 1976-2026. Outline = OSM industrial outline on Busch Drive.",
         "Solano", [osm("d401d069")], label_years=(1976, 2026), date=False),
    site("potrero_hills_landfill", "Potrero Hills Landfill", "Potrero Hills Landfill", "other", "landfill", 1986.6,
         9999, "exact",
         "https://www.waterboards.ca.gov/sanfranciscobay/board_decisions/tentative_orders/Potrero_Hills/Potrero_Hills.pdf",
         "Opened and began receiving waste in August 1986 (Regional Water Board). Outline = OSM (today's permitted "
         "area; growth not traced).", "Solano", [osm("d087d51e")], date=False),
    site("lake_herman_quarry", "Lake Herman Quarry, Sulphur Springs Mountain (Syar Industries; Vulcan Materials)",
         "Lake Herman Quarry", "quarry", "quarry_pit", 1948, 9999, "estimated",
         T + "CA_Benicia_288319_1950_24000_geo.tif",
         "'Quarry' symbol on the Benicia 1:24k sheet of 1950 (1948 photos) and its 1968 photorevision (opening year "
         "not researched: start = the first edition showing it). Today's 138 ha pit (expansion project SCH "
         "2000072074) from the midpoint of the 1968 photorevision and today (estimated).", "Solano",
         [traced(F_LH, circle(-250, 150, 120), T + "CA_Benicia_288319_1950_24000_geo.tif",
                 note="quarry symbol of the 1950 / 1968 sheets; extent estimated"),
          osm("2ba87bdd", start=1995, src="https://ceqanet.lci.ca.gov/2000072074",
              note="today's outline; start = midpoint of the 1968 photorevision and today (estimated)")],
         date=False),

    # ------------------------------------------------------------------ south Santa Clara
    site("utc_coyote", "United Technology Center / UTC Chemical Systems Division (Pratt & Whitney Space "
         "Propulsion), Coyote", "UTC Rocket Test Site", "factory", "industrial", 1959, 9999, "estimated",
         "https://morganhilltimes.com/utc-shutting-down-its-coyote-valley-plant/",
         "Solid-rocket motor plant and test site on Metcalf Road: closure announced after about 45 years of rocket "
         "testing (Morgan Hill Times), i.e. c.1959-2004 (both years estimated). Not on the Morgan Hill 1:24k sheet "
         "of 1955 (1953 photos); buildings in the photorevision magenta of 1968-78. Outline = OSM industrial "
         "outlines of the plant areas (the 5,000-acre buffer land is not outlined).", "Santa Clara",
         [osm("2665802a", "de952d29")], label_years=(1959, 2004), date=False),
    site("kirby_canyon_landfill", "Kirby Canyon Recycling and Disposal Facility", "Kirby Canyon Landfill", "other",
         "landfill", 1986, 9999, "exact",
         "https://www.waterboards.ca.gov/sanfranciscobay/board_info/agendas/2018/March/KirbyCanyon/2018_Kirby_TO.pdf",
         "Landfilling began in 1986 (Regional Water Board order, 2018). Outline = OSM (today's fill area).",
         "Santa Clara", [osm("8e1e389b")], date=False),
]

NHL = "https://noehill.com/solano/nat1975002103.aspx"
NPS = "https://www.nps.gov/places/mare-island-naval-shipyard.htm"
_COAL = ["6808b1fd", "b0257f96", "fb75daab", "6c9b82dd", "0954014c", "fbcf7e94", "0ef4f673", "b30ceb6d", "50b94972"]
# researched buildings: `fid` = Overture building id prefix (the row's point is computed inside it)
NAMED_EXT = [
    dict(id="indx_mare_island_bldg46", name="Mare Island Building 46 (Smithery; Mare Island Museum)", fid="69d3a21b",
         start_year=1855, end_year=9999, source_url=NPS,
         note="Oldest shipyard building: cornerstone 23 Feb 1855 (NPS: 1855; NHL listing: 1854).", county="Solano"),
    dict(id="indx_mare_island_bldg47", name="Mare Island Building 47 (Administration Building)", fid="b7216453",
         start_year=1855, end_year=9999, source_url=NHL,
         note="NHL Area A: Administration Building (Building 47), 1855.", county="Solano"),
    dict(id="indx_mare_island_bldg69", name="Mare Island Building 69 (Supply Warehouse)", fid="6baf8043",
         start_year=1869, end_year=9999, source_url=NHL, note="NHL Area A: Supply Warehouse (Building 69), 1869.",
         county="Solano"),
    dict(id="indx_mare_island_quarters_a", name="Mare Island Quarters A (Officers' Row, Walnut Avenue)",
         fid="252e538f", start_year=1900, end_year=9999, source_url=NHL,
         note="NHL Area A: Officers' Quarters A-L on Walnut Avenue, 1900 (NPS: ranking officers' mansions c.1900).",
         county="Solano"),
    dict(id="indx_mare_island_magazine_a1", name="Mare Island Stone Magazine A-1 (Naval Ammunition Depot)",
         fid="4982e927", start_year=1857, end_year=9999, source_url=NHL,
         note="NHL Area B: stone magazines A-1, A-4, A-20 built 1857-64; A-1 is the first (1857).", county="Solano"),
] + [
    dict(id=f"indx_mare_island_coal_shed_{k + 1}", name="Mare Island coal shed (Buildings 141-163)", fid=f,
         start_year=1900, end_year=9999, source_url=NHL,
         note="NHL Area A: nine coal sheds (Buildings 141, 143, 145, 147, 149, 151, 153, 155, 163), 1900.",
         county="Solano") for k, f in enumerate(_COAL)
] + [
    dict(id="indx_benicia_camel_barn", name="Benicia Arsenal Camel Barns (Museum of History Benicia)",
         fid="3909bce7", start_year=1855, end_year=9999, source_url=W + "Benicia_Arsenal",
         note="Sandstone storehouses of 1855, known as the Camel Barns (the Army's Camel Corps was stabled here).",
         county="Solano"),
    dict(id="indx_cmf_vacaville_main", name="California Medical Facility, main building", fid="7555ab34",
         start_year=1955, end_year=9999, source_url=W + "California_Medical_Facility",
         note="CMF opened in 1955; the main building had no roll year (live map 1977, imputed).", county="Solano"),
]
