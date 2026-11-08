"""Route specifications for data/manual/historic_rail.geojson (built by
pipeline/historic_rail_trace.py build). Hand-researched: every segment carries its dates,
sources and the geometry recipe (pieces, best source first: rail / road / topo / pts).

Waypoints are (lon, lat) in today's frame (WGS84). topo sheet keys: historic_rail_trace.SHEETS.
Years are decimal (1878.21 = 20 March 1878); 9999 = still in use / still standing.
"""

ROUTES = []


def route(route_id, name, mode, source_url, segments, note=None, confidence="exact"):
    ROUTES.append({"route_id": route_id, "name": name, "mode": mode, "source_url": source_url,
                   "note": note, "confidence": confidence, "segments": segments})


def seg(name, y0, y1, *pieces, elevated="ground", note=None, confidence=None, mode=None, source_url=None,
        geometry_confidence=None):
    d = {"name": name, "year_start": y0, "year_end": y1, "elevated": elevated, "pieces": list(pieces)}
    for k, v in (("note", note), ("confidence", confidence), ("mode", mode), ("source_url", source_url),
                 ("geometry_confidence", geometry_confidence)):
        if v is not None:
            d[k] = v
    return d


def rail(*wps, names=None, snap=400.0, kinds=("heavy",), join=25.0, smooth=None):
    return {"method": "rail", "wps": list(wps), "names": names, "snap": snap, "kinds": kinds, "join": join,
            "smooth": smooth}


def road(*wps, names=None, snap=60.0):
    return {"method": "road", "wps": list(wps), "names": names, "snap": snap, "join": 20.0}


def topo(sheet, *wps, corridor=110.0, smooth=70.0, step=1, via=None):
    return {"method": "topo", "sheet": sheet, "wps": list(wps), "corridor": corridor, "smooth": smooth, "step": step,
            "via": via}


def pts(*wps, chaikin=4):
    return {"method": "pts", "wps": list(wps), "chaikin": chaikin}


WIKI = "https://en.wikipedia.org/wiki/"

# =====================================================================================
# OAKLAND WATERFRONT: Long Wharf, Oakland Mole, Western Pacific Mole, Key System Mole
# =====================================================================================
route("cp_long_wharf", "Oakland Long Wharf (San Francisco & Oakland RR / Central Pacific)", "pier",
      WIKI + "Oakland_Long_Wharf", [
          seg("Long Wharf, inner part (SF&O ferry wharf 1863; filled 1879-82 into the Oakland Mole)",
              1863.67, 1882.06,
              topo("sf1899", (-122.3035, 37.8086), (-122.3150, 37.8094), (-122.3285, 37.8104)),
              elevated="pier",
              note="Gibbons' wharf (1852) used as the San Francisco & Oakland Railroad ferry landing; SF&O trains from "
                   "Sept 1863; Central Pacific acquired and extended it from 1868; reconstructed by landfill 1879-80, "
                   "Oakland Pier opened on the fill 1882-01-22. Geometry: USGS San Francisco 1899 sheet (the mole "
                   "line).", confidence="estimated"),
          seg("Long Wharf, outer trestle to deep water (freight only after 1882)", 1869.85, 1919.5,
              topo("sf1899", (-122.3285, 37.8106), (-122.3380, 37.8116), (-122.3458, 37.8125)),
              elevated="pier",
              note="Transcontinental terminus from 1869-11-08; reached deep water (11,000 ft) and fully open "
                   "1871-01-16; freight-only after 1882; abandoned 1919. Geometry: USGS San Francisco 1899 sheet."),
      ])

route("sp_oakland_mole", "Oakland Pier ('Oakland Mole', Central Pacific / Southern Pacific)", "rail",
      WIKI + "Oakland_Long_Wharf", [
          seg("Oakland Mole (fill) and train shed", 1882.06, 1958.58,
              topo("sf1899", (-122.3035, 37.8086), (-122.3150, 37.8094), (-122.3285, 37.8104)),
              note="Built on the filled Long Wharf 1879-82, opened 1882-01-22; SP main-line and East Bay local "
                   "trains (electric 1911-1939); last SP ferry 1958-07-29; demolished in the 1960s for the Port of "
                   "Oakland. Geometry: USGS San Francisco 1899 sheet."),
      ])

route("wp_mole", "Western Pacific Mole (Oakland)", "pier", WIKI + "Oakland_Long_Wharf", [
    seg("Western Pacific Mole on the north training wall of the estuary", 1910.6, 1933.5,
        topo("sf1915", (-122.3330, 37.7998), (-122.3220, 37.7975), (-122.3120, 37.7954),
             (-122.3050, 37.7942)),
        elevated="pier",
        note="Built 1906-10 along the north jetty of the Oakland Harbor entrance; WP ferry terminal opened 1910 "
             "(passenger service from Aug 1910), used until 1933, passenger terminal demolished 1940. Dates of "
             "the month ESTIMATED. Geometry: USGS San Francisco 1915 sheet.", confidence="estimated"),
])

route("ks_mole", "Key System Mole and pier (Key Route Pier)", "pier", WIKI + "Key_System_Mole", [
    seg("Key System Mole: causeway (trestle 1903, filled 1908-16) to the ferry pier", 1903.82, 1939.83,
        topo("sf1915", (-122.2975, 37.8263), (-122.3080, 37.8243), (-122.3200, 37.8220), (-122.3330, 37.8193),
             (-122.3445, 37.8167)),
        elevated="trestle",
        note="Transbay service from 1903-10-26 on a 17,000 ft wooden trestle; approach filled 1908, causeway "
             "except the last 3,800 ft by 1916; pier fire 1933-05-06 (rebuilt slightly to the south); ferries to "
             "the Bay Bridge 1939-01-15, Exposition trains/ferries until 1939-10-29. Geometry: USGS San Francisco "
             "1915 sheet ('San Francisco-Oakland Terminal Key Route Pier')."),
])

# =====================================================================================
# ALAMEDA: San Francisco & Alameda RR (1864) and the South Pacific Coast narrow gauge (1878)
# =====================================================================================
SFA = WIKI + "San_Francisco_and_Alameda_Railroad"
route("sfa", "San Francisco & Alameda Railroad (Central Pacific / SP Lincoln Avenue line)", "rail", SFA, [
    seg("Alameda Terminal wharf at the foot of Pacific Ave", 1864.65, 1873.5,
        topo("sf1899", (-122.3068, 37.7736), (-122.2995, 37.7756), (-122.2925, 37.7772)),
        elevated="pier", mode="pier", source_url=WIKI + "Alameda_Terminal",
        note="SF&A ferry wharf (~3,750 ft) built 1864, first run 1864-08-25; transcontinental terminus "
             "1869-09-06 to 1869-11-07; abandoned for rail-ferry use 1873 (wharf later used by the Pacific Coast "
             "Oil refinery). Geometry: the wharf on the USGS San Francisco 1899 sheet.", confidence="estimated"),
    seg("Pacific Ave, private right-of-way to 5th St", 1864.65, 1873.5,
        road((-122.2925, 37.7767), (-122.2846, 37.7763), names=["Pacific Avenue"]),
        pts((-122.2846, 37.7763), (-122.2829, 37.7757), (-122.2812, 37.7753)),
        note="'Along Pacific Avenue to 4th Street, then via private right-of-way to 5th Street' (SF&A); unused "
             "after the wharf closed in 1873 (end ESTIMATED). Private right-of-way approximate.",
        confidence="estimated", geometry_confidence="medium"),
    seg("Lincoln Ave (Linnet St / Railroad Ave): 5th St - Park St - Fernside", 1864.65, 1960.0,
        road((-122.2812, 37.7753), (-122.2633, 37.7748), (-122.2454, 37.7684), (-122.2410, 37.7667),
             names=["Lincoln Avenue"]),
        note="SF&A 1864 (Alameda station at Park St); Central Pacific 1869-70, SP; electrified 1911 (Lincoln "
             "Avenue line, to the Alameda Mole from 1906); passenger service ended January 1941, freight 1960 "
             "when the rails were removed. Geometry: today's Lincoln Avenue centreline (OSM)."),
    seg("Park St - Fernside - Melrose (across the neck cut by the Tidal Canal in 1903)", 1865.0, 1960.0,
        topo("con1897", (-122.2410, 37.7667), (-122.2370, 37.7684), (-122.2335, 37.7685), (-122.2280, 37.7680),
             (-122.2215, 37.7676), (-122.2165, 37.7670), corridor=90),
        note="SF&A main line to San Leandro and Haywards (1865); after 1873 Alameda trains ran north from "
             "Fernside to Fruitvale and this link carried freight; still on the 1915 map; end ESTIMATED with the "
             "Lincoln Ave freight (1960). Geometry: USGS Concord 1897 sheet.", confidence="estimated"),
    seg("Melrose - Fitchburg - Elmhurst - San Leandro (later the CP/SP main line, now UP Niles Sub)", 1865.0, 9999,
        rail((-122.2165, 37.7675), (-122.2011, 37.7547), (-122.1781, 37.7347), (-122.1600, 37.7195),
             names=["Niles"]),
        note="SF&A route of 1865 'through Fernside, Melrose, Fitchburg and Elmhurst' to San Leandro; part of the "
             "Central Pacific main line from 1869; today's Union Pacific Niles Subdivision (geometry: OSM)."),
    seg("San Leandro - Haywards on Ward St and the county road (East 14th St / Mission Blvd)", 1865.0, 1873.5,
        pts((-122.1600, 37.7195), (-122.1575, 37.7240), (-122.1545, 37.7245)),
        road((-122.1545, 37.7245), (-122.1432, 37.7156), (-122.1270, 37.7041), (-122.1004, 37.6854),
             (-122.0843, 37.6724), (-122.0806, 37.6701), names=["East 14th", "Mission Boulevard"]),
        note="Street running 'along Ward Street in San Leandro and the county road (now East 14th Street/Mission "
             "Boulevard) to Watkins Street, Hayward' (1865); abandoned 1873. Geometry: today's East 14th St / "
             "Mission Blvd (OSM); the San Leandro end is approximate.", confidence="estimated",
        geometry_confidence="medium"),
])

SPC = WIKI + "South_Pacific_Coast_Railroad"
ALAPOST = "https://alamedapost.com/history/south-pacific-coast-narrow-gauge-railroad-once-traversed-alameda/"
route("spc_alameda", "South Pacific Coast Railroad (narrow gauge): Alameda Mole and Alameda line", "narrow_gauge",
      SPC, [
          seg("Alameda Mole: stone mole and ferry pier (2.5 mi to deep water)", 1884.2, 1940.0,
              topo("sf1915", (-122.3365, 37.7972), (-122.3250, 37.7950), (-122.3120, 37.7928), (-122.3020, 37.7907),
                   (-122.2965, 37.7898)),
              elevated="embankment", mode="pier", source_url=WIKI + "Alameda_Mole",
              note="SPC extended its West End wharf ~2.5 miles NW on a stone mole, terminal opened 1884-03-15 "
                   "(Alameda Post); dual gauge 1898, standard gauge after 1906; terminal burned 1902-11-20 and was "
                   "rebuilt larger and farther out; SP electric trains 1911-1939; ferries ended 1939-01-15; the "
                   "Navy demolished the terminal in 1940 for NAS Alameda. Geometry: USGS San Francisco 1915 sheet "
                   "('Southern Pacific' on the south jetty)."),
          seg("West End wharves (first SPC ferry terminal)", 1878.21, 1884.2,
              topo("sf1899", (-122.2960, 37.7905), (-122.2930, 37.7915)),
              pts((-122.2930, 37.7915), (-122.2950, 37.7928), (-122.2985, 37.7935)),
              elevated="pier", mode="pier", source_url=ALAPOST,
              note="A pair of 1,000 ft wharves at the old shoreline where Main Street bends west; ferries Bay City "
                   "and Garden City to San Francisco; replaced by the mole (1884). Wikipedia dates the Alameda ferry "
                   "terminal to 1878-03-20, the Alameda Post the wharves to summer 1879. Wharf outline APPROXIMATE.",
              confidence="estimated", geometry_confidence="low"),
          seg("Main Street across the marsh (West End)", 1878.21, 1941.05,
              topo("sf1899", (-122.2930, 37.7912), (-122.2915, 37.7880), (-122.2915, 37.7830), (-122.2915, 37.7790)),
              road((-122.2913, 37.7787), (-122.2911, 37.7766), names=["Main Street"]),
              elevated="trestle", source_url=ALAPOST,
              note="'Along Main [Street] over the marshland to the wharves'; electric (Encinal Avenue line) 1911; "
                   "last train January 1941. Geometry: USGS San Francisco 1899 sheet + today's Main Street."),
          seg("Central Ave (trestle along the shore from Main St to 4th St) and Encinal Ave to High St", 1878.21, 1941.05,
              road((-122.2911, 37.7765), (-122.2889, 37.7729), (-122.2769, 37.7714), (-122.2636, 37.7710),
                   names=["Central Avenue"]),
              road((-122.2636, 37.7710), (-122.2564, 37.7678), (-122.2470, 37.7637), (-122.2384, 37.7592),
                   (-122.2342, 37.7562), names=["Encinal Avenue"]),
              source_url=ALAPOST,
              note="Test train on Encinal Ave 1877-12-02; service Park St - Los Gatos 1878-03-20; trestle on Central "
                   "Ave over the water 4th St - Main St; 33 trains a day by 1888; standard gauge from 1906; SP "
                   "electric Encinal Avenue line from 1911-06-01; last service 1941-01-18. Geometry: today's Central "
                   "and Encinal Avenue centrelines (OSM)."),
          seg("Encinal Ave east of High St to Fernside (bridge abutment)", 1878.21, 1906.3,
              road((-122.2342, 37.7562), (-122.2306, 37.7537), names=["Encinal Avenue"]),
              source_url=ALAPOST, note="Approach to the San Leandro Bay swing bridge; unused after the bridge was "
                                       "abandoned (1906)."),
          seg("Swing bridge across San Leandro Bay", 1878.21, 1906.3,
              pts((-122.2306, 37.7537), (-122.2292, 37.7517)),
              topo("hay1899", (-122.2292, 37.7517), (-122.2268, 37.7478)),
              elevated="bridge",
              note="Bay and Coast Railroad (SPC) swing bridge from Fernside/Encinal across San Leandro Bay; damaged "
                   "in the 1906 earthquake and abandoned (Alameda track isolated). Geometry: USGS Haywards 1899 "
                   "sheet; the west abutment at today's Encinal Ave / Fernside Blvd (Alameda Post)."),
          seg("Trestle across the San Leandro Bay marsh to West San Leandro", 1878.21, 1906.3,
              topo("hay1899", (-122.2268, 37.7478), (-122.2185, 37.7355), (-122.2075, 37.7300),
                   (-122.2000, 37.7255), (-122.1925, 37.7210), (-122.1840, 37.7155)),
              elevated="trestle",
              note="Trestles and fill of the Bay and Coast Railroad (1878) across the marsh; abandoned with the "
                   "bridge after the 1906 earthquake. Geometry: USGS Haywards 1899 sheet ('Southern [Pacific]')."),
      ])

route("spc_main", "South Pacific Coast Railroad (narrow gauge): West San Leandro - Newark - San Jose", "narrow_gauge",
      SPC, [
          seg("West San Leandro - West San Lorenzo - Mt Eden - Alvarado - Newark (Bay and Coast RR)", 1878.21, 9999,
              rail((-122.1840, 37.7155), (-122.1538, 37.6741), (-122.1186, 37.6363), (-122.0793, 37.6011),
                   (-122.0572, 37.5591), (-122.0420, 37.5320), names=["Coast"]),
              note="Bay and Coast Railroad trestles and fill from Newark to Alameda (1878); standard gauge 1906-09; "
                   "SP Coast line, now the Union Pacific Coast Subdivision (geometry: OSM). The 1906 link north to "
                   "the SP main at Elmhurst is a separate segment."),
          seg("Elmhurst connection to the SP main line (after the 1906 earthquake)", 1906.5, 9999,
              rail((-122.1840, 37.7155), (-122.1832, 37.7250), (-122.1804, 37.7367), names=["Coast"]),
              note="Built when the San Leandro Bay bridge was abandoned (date ESTIMATED); today's UP Coast "
                   "Subdivision junction (geometry: OSM).", confidence="estimated"),
          seg("Newark - Alviso (Drawbridge) - Agnew - Santa Clara", 1876.5, 9999,
              rail((-122.0420, 37.5320), (-122.0266, 37.5223), (-122.0030, 37.5086), (-121.9741, 37.4684),
                   (-121.9767, 37.4201), (-121.9475, 37.3776), (-121.9398, 37.3550), names=["Coast"]),
              note="Santa Clara Valley RR / SPC narrow gauge from Dumbarton Point and Newark to San Jose, completed "
                   "1876 (month ESTIMATED); standard gauge 1906-09; now UP Coast Subdivision (geometry: OSM).",
              confidence="estimated"),
      ])

route("spc_dumbarton_pt", "South Pacific Coast Railroad: Dumbarton Point branch and ferry landing", "narrow_gauge",
      SPC, [
          seg("Newark - Dumbarton Point", 1876.25, 1880.0,
              pts((-122.0420, 37.5320), (-122.0490, 37.5262), (-122.0556, 37.5223)),
              rail((-122.0556, 37.5223), (-122.0814, 37.5137), (-122.0966, 37.5064), (-122.1093, 37.4979),
                   names=["Dumbarton"]),
              note="The SPC's first ferry terminal at Dumbarton Point (1876), used until the line to Alameda opened "
                   "(1878); end ESTIMATED. The 1910 Dumbarton Cutoff runs on the same corridor; geometry follows it "
                   "(LOW CONFIDENCE).", confidence="estimated", geometry_confidence="low"),
      ])

CP = WIKI + "Oakland_Long_Wharf"
route("cp_main", "Central Pacific (Western Pacific of 1869) Oakland - San Leandro - Niles", "rail", CP, [
    seg("Oakland Point - 1st St (Embarcadero) - Brooklyn - Fruitvale - Melrose", 1869.85, 9999,
        rail((-122.3011, 37.8027), (-122.2849, 37.7984), (-122.2695, 37.7926), (-122.2530, 37.7893),
             (-122.2384, 37.7825), (-122.2255, 37.7736), (-122.2165, 37.7675), snap=120),
        note="Transcontinental trains to the Oakland Long Wharf from 1869-11-08 (via the SF&O 7th St line); the "
             "First Street line was completed 1870 (SF&A article). SP main, now UP Niles Subdivision (geometry: "
             "OSM).", confidence="estimated", source_url=WIKI + "San_Francisco_and_Alameda_Railroad"),
    seg("San Leandro - Haywards - Decoto - Niles", 1869.68, 9999,
        rail((-122.1600, 37.7195), (-122.1314, 37.6939), (-122.0965, 37.6633), (-122.0615, 37.6327),
             (-122.0266, 37.6021), (-121.9848, 37.5788), (-121.9720, 37.5728), names=["Niles"]),
        note="Western Pacific (1862) / Central Pacific line from Niles to San Leandro; first through train reached "
             "the Alameda wharf 1869-09-06 over a temporary connection to the SF&A at San Leandro. Today's UP "
             "Niles Subdivision (geometry: OSM).", source_url=WIKI + "Alameda_Terminal"),
])

# =====================================================================================
# OCEAN SHORE RAILWAY (1905-1920): San Francisco - Daly City - Pacifica - Half Moon Bay - Tunitas
# =====================================================================================
OSR = WIKI + "Ocean_Shore_Railroad"
OSR_END = 1920.58          # mainline service ended 1920-07-31
route("osr", "Ocean Shore Railway", "rail", OSR, [
    seg("San Francisco: 12th & Mission - 12th St - Division (trestle over the SP) - Florida - Mariposa - "
        "Potrero Ave - Army St - Old San Bruno Rd (electric street section)", 1907.75, OSR_END,
        pts((-122.418618, 37.773053), (-122.416900, 37.771724), (-122.413283, 37.770229), (-122.411759, 37.768693),
            (-122.411207, 37.762973), (-122.407305, 37.763188), (-122.406201, 37.751521), (-122.405261, 37.749353),
            (-122.403593, 37.749472), (-122.403243, 37.743794), (-122.406888, 37.736762), chaikin=1),
        mode="interurban",
        note="Depot at the SE corner of 12th & Mission; electrified 600 V (city franchise) to the Army St shops; "
             "street sections from DataSF intersections (route per the earlier routes.csv research). North-end "
             "service from 1907-10-02; mainline service ended 1920-07-31 (a southeast-SF piece later carried "
             "Western Pacific freight into the 1980s - which piece is not documented here).",
        geometry_confidence="medium"),
    seg("San Francisco: Islais Creek / Alemany grade to Daly City", 1907.75, OSR_END,
        road((-122.4069, 37.7368), (-122.4289, 37.7312), (-122.4386, 37.7216), (-122.4550, 37.7106),
             (-122.4689, 37.7108), (-122.4722, 37.7047), names=["Alemany"], snap=120),
        note="'then steam via Barneveld/Loomis and the Alemany Blvd (Islais Creek) grade'; the OSR's Mission (5.4 "
             "mi) and Daly City (7.6 mi) stations fit this alignment; geometry follows today's Alemany Boulevard "
             "(built on the grade; OSM).", confidence="estimated", geometry_confidence="medium"),
    seg("Daly City - Crosby - Thornton - Mussel Rock - Edgemar - Salada - Brighton - Vallemar - Rockaway",
        1907.75, OSR_END,
        pts((-122.4722, 37.7047), (-122.4718, 37.7030)),
        topo("sm1915", (-122.4718, 37.7030), (-122.4718, 37.6990), (-122.4728, 37.6963), (-122.4845, 37.6963),
             (-122.4885, 37.6995), (-122.4930, 37.6998), (-122.4965, 37.6978), (-122.4972, 37.6900),
             (-122.4958, 37.6800), (-122.4955, 37.6700), (-122.4945, 37.6630), (-122.4920, 37.6600),
             (-122.4898, 37.6531), (-122.4908, 37.6474), (-122.4904, 37.6420), (-122.4900, 37.6330),
             (-122.4897, 37.6270), (-122.4891, 37.6255), (-122.4857, 37.6210), (-122.4857, 37.6162),
             (-122.4887, 37.6147), (-122.4925, 37.6126), (-122.4959, 37.6108), (-122.4982, 37.6090),
             corridor=60),
        note="Along the face of the sea cliffs from Thornton to Mussel Rock (the San Andreas rift crossing), then "
             "the beach terraces of Salada (Sharp Park) and Rockaway. Geometry: USGS San Mateo 1915 sheet "
             "('Ocean Shore')."),
    seg("Rockaway - Pedro Valley (Tobin)", 1907.75, OSR_END,
        pts((-122.4982, 37.6090), (-122.5010, 37.6040), (-122.5050, 37.5985), (-122.5095, 37.5966)),
        note="Tobin station at San Pedro Point (Danmann Ave / Shelter Cove Rd), reached 1907-10-02. Geometry "
             "hand-placed along the valley floor (LOW CONFIDENCE).", geometry_confidence="low"),
    seg("Tobin - Shelter Cove (San Pedro Point)", 1908.45, OSR_END,
        pts((-122.5095, 37.5966), (-122.5130, 37.5975), (-122.5150, 37.5972)),
        note="Along today's Shelter Cove road (on the grade); extension south opened to Granada June 1908.",
        geometry_confidence="medium"),
    seg("Pedro Point tunnel", 1908.45, OSR_END,
        pts((-122.5150, 37.5972), (-122.5168, 37.5950), (-122.5186, 37.5926), chaikin=2),
        elevated="tunnel",
        note="Tunnel through San Pedro Point (built during construction, 1905-08). Position APPROXIMATE.",
        geometry_confidence="low"),
    seg("Cliff shelf round Devil's Slide to Montara", 1908.45, OSR_END,
        pts((-122.5186, 37.5926), (-122.5195, 37.5895), (-122.5190, 37.5855), (-122.5182, 37.5812),
            (-122.5180, 37.5775), (-122.5172, 37.5745), (-122.5162, 37.5712), (-122.5150, 37.5680),
            (-122.5137, 37.5650), (-122.5130, 37.5615), (-122.5133, 37.5585), (-122.5130, 37.5555),
            (-122.5140, 37.5515), (-122.5138, 37.5470)),
        note="Shelf cut into the sea cliffs of Montara Mountain round Devil's Slide; washed out January 1916 and "
             "the track relocated round the slide. Hand-placed along the cliff and the 1937 highway "
             "(USGS Montara Mountain 1949 sheet) - LOW CONFIDENCE.", geometry_confidence="low",
        source_url=WIKI + "Devil%27s_Slide_(California)"),
    seg("Montara - Farallone - Moss Beach", 1908.45, OSR_END,
        rail((-122.5136, 37.5462), (-122.5169, 37.5395), snap=60),
        pts((-122.5169, 37.5395), (-122.5162, 37.5340), (-122.5145, 37.5300), (-122.5130, 37.5270)),
        note="Montara station (222 Second St) and Farallone City (Seventh St); the grade is under today's Cabrillo "
             "Highway in Montara (OSM abandoned:railway, old operator Ocean Shore Railway); Moss Beach "
             "approximate.", geometry_confidence="medium"),
    seg("Moss Beach - Princeton - North Granada - Granada", 1908.45, OSR_END,
        pts((-122.5130, 37.5270), (-122.5085, 37.5205), (-122.5010, 37.5135), (-122.4945, 37.5070),
            (-122.4890, 37.5035), (-122.4820, 37.5025), (-122.4735, 37.5012), (-122.4685, 37.4985),
            (-122.4617, 37.4966)),
        note="Granada reached June 1908; North Granada depot (1900 building) at 10151 Cabrillo Hwy. Geometry "
             "hand-placed along the shore of Half Moon Bay (LOW CONFIDENCE).", geometry_confidence="low"),
    seg("Granada - Miramar - Half Moon Bay", 1908.78, OSR_END,
        rail((-122.4617, 37.4966), (-122.4565, 37.4904), snap=80),
        pts((-122.4565, 37.4904), (-122.4510, 37.4820), (-122.4465, 37.4735), (-122.4442, 37.4668)),
        rail((-122.4442, 37.4668), (-122.4437, 37.4644), snap=80),
        note="'Ocean Shore' station reached October 1908 (Half Moon Bay; Arleta Park depot at 920 Railroad Ave). "
             "Geometry: OSM grade fragments (Miramar, Half Moon Bay), hand-placed between.",
        geometry_confidence="medium"),
    seg("Half Moon Bay - Arleta - Purisima - Lobitos - Tunitas Glen", 1908.9, OSR_END,
        pts((-122.4437, 37.4644), (-122.4425, 37.4600), (-122.4409, 37.4559)),
        rail((-122.4409, 37.4559), (-122.4393, 37.4508), (-122.4381, 37.4466), snap=60),
        pts((-122.4381, 37.4466), (-122.4360, 37.4390), (-122.4330, 37.4300), (-122.4306, 37.4254)),
        rail((-122.4306, 37.4254), (-122.4185, 37.3924), (-122.4127, 37.3847), (-122.4089, 37.3795),
             (-122.4063, 37.3753), (-122.4057, 37.3680), (-122.4050, 37.3628), snap=60, join=60),
        pts((-122.4050, 37.3628), (-122.4035, 37.3600), (-122.4010, 37.3570)),
        note="End of track at Tunitas Glen (1908, month ESTIMATED); a Stanley Steamer auto stage bridged the "
             "26-mile gap to Swanton. Geometry: OSM grade fragments south of Half Moon Bay and at Purisima, "
             "hand-placed between (south of Purisima LOW CONFIDENCE).", confidence="estimated",
        geometry_confidence="medium"),
])

# =====================================================================================
# SAN FRANCISCO & SAN JOSE RAILROAD (1863-64) / SP PENINSULA LINE
# =====================================================================================
SFSJ = WIKI + "San_Francisco_and_San_Jose_Railroad"
OVB = WIKI + "Ocean_View_Branch"
route("sfsj", "San Francisco & San Jose Railroad / Southern Pacific (Peninsula line)", "rail", SFSJ, [
    seg("Valencia St street running, 18th St - 25th St (first SF terminal at 18th & Valencia)", 1863.8, 1874.6,
        road((-122.42160, 37.76170), (-122.42051, 37.75051), names=["Valencia"]),
        source_url=OVB,
        note="SF&SJ trains reached the city at 18th & Valencia (October 1863; passengers changed to horsecars), "
             "then ran up Valencia St to a Market St depot 'by around 1866', until SP moved the line to Harrison, "
             "Division and Townsend streets (4th & Townsend depot 1874-08-17). Geometry: today's Valencia St.",
        confidence="estimated"),
    seg("Valencia St street running, Market St - 18th St", 1866.0, 1874.6,
        road((-122.42265, 37.77250), (-122.42160, 37.76170), names=["Valencia"]),
        source_url=OVB, note="Extension to a Market St depot c.1866 (year ESTIMATED).", confidence="estimated"),
    seg("Mission diagonal (Valencia near 25th - Juri Commons - Dolores St viaduct) and the Bernal Cut to Glen Park",
        1863.8, 1942.0,
        topo("sm1899", (-122.4205, 37.7508), (-122.4220, 37.7496), (-122.4246, 37.7462), (-122.4236, 37.7430),
             (-122.4238, 37.7405), (-122.4260, 37.7378), (-122.4304, 37.7339), (-122.4339, 37.7330), corridor=80),
        source_url=OVB,
        note="Private right of way across the Mission (Juri Commons; steel viaduct over Dolores St) into the "
             "Bernal Cut (dug 1862-63, 43 ft deep; now San Jose Ave); main line until the Bayshore Cutoff "
             "(1907-12-08), then the Ocean View Branch; abandoned 1942. Geometry: USGS San Francisco 1899 and San "
             "Mateo 1899 sheets."),
    seg("Mission diagonal east of Valencia: Harrison St at 22nd - Folsom - Mission St (1874 line)", 1874.6, 1942.0,
        topo("sf1899", (-122.41223, 37.75584), (-122.4137, 37.7541), (-122.4184, 37.7518), (-122.4205, 37.7508),
             corridor=60),
        source_url=OVB,
        note="Diagonal leaving Harrison at 22nd, crossing Treat/Folsom near 23rd and Mission just south of 24th; "
             "built when the line moved off Valencia St (1874). Geometry: USGS San Francisco 1899 sheet."),
    seg("4th & Townsend - Townsend St - Division St - Harrison St to 22nd (1874 main line)", 1874.6, 1907.93,
        pts((-122.394981, 37.777089), (-122.401657, 37.771817), (-122.404391, 37.769750), (-122.406213, 37.769463),
            (-122.410872, 37.769232), (-122.413243, 37.766898), (-122.41223, 37.75584), chaikin=2),
        source_url=OVB,
        note="SP moved the line onto Townsend, Division and Harrison streets with the 4th & Townsend depot "
             "(1874-08-17); main line until the Bayshore Cutoff opened 1907-12-08, then Ocean View Branch "
             "freight (Harrison St freight tracks to Treat Ave survived until c.1990). Street geometry from DataSF "
             "intersections; the Division/Harrison link approximate.", geometry_confidence="medium"),
    seg("Ocean View Branch: Glen Park - Ocean View - Daly City - Colma - Baden - San Bruno (original main line)",
        1863.8, 1942.0,
        topo("sm1899", (-122.4339, 37.7331), (-122.4378, 37.7306), (-122.4433, 37.7281), (-122.4455, 37.7263),
             (-122.4471, 37.7236), (-122.4488, 37.7163), (-122.4503, 37.7145), (-122.4533, 37.7119),
             (-122.4551, 37.7107), (-122.4570, 37.7102), (-122.4640, 37.7101), (-122.4654, 37.7098),
             (-122.4665, 37.7090), (-122.4706, 37.7043), (-122.4712, 37.7030), (-122.4711, 37.6983),
             (-122.4700, 37.6948), (-122.4698, 37.6895), (-122.4680, 37.6857), (-122.4621, 37.6817),
             (-122.4575, 37.6769), (-122.4532, 37.6739), (-122.4479, 37.6669), (-122.4400, 37.6616),
             (-122.4350, 37.6564), (-122.4283, 37.6526), (-122.4261, 37.6509), (-122.4228, 37.6471),
             (-122.4194, 37.6433), (-122.4164, 37.6381), (-122.4120, 37.6305), corridor=110),
        source_url=OVB,
        note="SF&SJ opened San Francisco - Mayfield October 1863 over this route (through the Bernal Cut, Ocean "
             "View and Colma); bypassed by the Bayshore Cutoff 1907; Ocean View Branch, abandoned 1942. Geometry: "
             "USGS San Mateo 1899 sheet."),
    seg("San Bruno - Millbrae - San Mateo - Redwood City - Mayfield (Palo Alto)", 1863.8, 9999,
        rail((-122.4112, 37.6298), (-122.4031, 37.6174), (-122.3889, 37.6020), (-122.3713, 37.5912),
             (-122.3426, 37.5791), (-122.3234, 37.5676), (-122.3072, 37.5490), (-122.2911, 37.5322),
             (-122.2678, 37.5147), (-122.2429, 37.4931), (-122.2172, 37.4768), (-122.1830, 37.4551),
             (-122.1573, 37.4389), (-122.1428, 37.4292), names=["Caltrain"]),
        note="SF&SJ opened to Mayfield 1863-10-18 (to San Jose 1864-01-16); Southern Pacific 1870; Caltrain "
             "today (geometry: OSM). Later grade separations and the 1907 Bayshore Cutoff junction at San Bruno "
             "are not modelled separately."),
    seg("Mayfield - Mountain View - Santa Clara - San Jose", 1864.04, 9999,
        rail((-122.1428, 37.4292), (-122.1231, 37.4174), (-122.1029, 37.4051), (-122.0729, 37.3932),
             (-122.0446, 37.3832), (-122.0172, 37.3743), (-121.9859, 37.3705), (-121.9639, 37.3654),
             (-121.9376, 37.3539), (-121.9132, 37.3415), (-121.9029, 37.3304), names=["Caltrain"]),
        note="Opened to San Jose 1864-01-16; Caltrain today (geometry: OSM; the San Jose end follows the 1935 "
             "line to Diridon station, the 1864 depot stood further east)."),
])

route("ir_40", "San Francisco & San Mateo Electric Railway / United Railroads 40 San Mateo interurban", "interurban",
      WIKI + "List_of_defunct_San_Francisco_Municipal_Railway_lines", [
          seg("San Francisco: 5th St and Mission St to Onondaga Ave", 1903.0, 1949.1,
              road((-122.40807, 37.78401), (-122.40649, 37.78274), names=["5th Street"]),
              road((-122.40649, 37.78274), (-122.41984, 37.76668), (-122.4186, 37.7537), (-122.4249, 37.7352),
                   (-122.4348, 37.7247), (-122.4391, 37.7191), (-122.4436, 37.7136), names=["Mission Street"]),
              note="Northern terminus 5th & Market by 1906; along Mission St (street running) to San Jose Ave and the "
                   "private right of way; service from 1902-12-31, through to San Mateo 1903; discontinued 1949 "
                   "(track and cars worn out). Geometry: today's street centrelines (OSM)."),
          seg("Daly City - Colma - Baden - San Bruno - Millbrae - Burlingame - San Mateo (private right of way)",
              1903.0, 1949.1,
              topo("sm1915", (-122.4436, 37.7136), (-122.4500, 37.7100), (-122.4560, 37.7080), (-122.4600, 37.6990),
                   (-122.4615, 37.6860), (-122.4570, 37.6770), (-122.4520, 37.6700), (-122.4400, 37.6620),
                   (-122.4290, 37.6560), (-122.4220, 37.6460), (-122.4140, 37.6330), (-122.4040, 37.6200),
                   (-122.3940, 37.6080), (-122.3820, 37.5960), (-122.3700, 37.5860), (-122.3580, 37.5790),
                   (-122.3470, 37.5730), (-122.3360, 37.5690), (-122.3260, 37.5650), corridor=220),
              note="Private right of way parallel to Mission Rd / El Camino Real (Centennial Way trail in South San "
                   "Francisco and San Bruno reuses it). Geometry: least-cost trace on the USGS San Mateo 1915 sheet "
                   "along the documented corridor - MEDIUM CONFIDENCE (the sheet also shows the SP and the county "
                   "road nearby).", geometry_confidence="medium"),
      ])
