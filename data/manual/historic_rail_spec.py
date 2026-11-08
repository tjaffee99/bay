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
