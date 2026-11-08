"""Route specifications for data/manual/historic_rail.geojson (built by
pipeline/historic_rail_trace.py build). Hand-researched: every segment carries its dates,
sources and the geometry recipe (pieces, best source first: rail / road / topo / pts).

Waypoints are (lon, lat) in today's frame (WGS84). topo sheet keys: historic_rail_trace.SHEETS.
Years are decimal (1878.21 = 20 March 1878); 9999 = still in use / still standing.
"""

ROUTES = []


def route(route_id, name, mode, source_url, segments, note=None, confidence="exact", standard_gauge=None):
    """standard_gauge: year a narrow-gauge route was converted (its segments are split there into a
    narrow_gauge and a rail time slice)."""
    ROUTES.append({"route_id": route_id, "name": name, "mode": mode, "source_url": source_url,
                   "note": note, "confidence": confidence, "segments": segments, "standard_gauge": standard_gauge})


def seg(name, y0, y1, *pieces, elevated="ground", note=None, confidence=None, mode=None, source_url=None,
        geometry_confidence=None, standard_gauge=None):
    d = {"name": name, "year_start": y0, "year_end": y1, "elevated": elevated, "pieces": list(pieces)}
    for k, v in (("note", note), ("confidence", confidence), ("mode", mode), ("source_url", source_url),
                 ("geometry_confidence", geometry_confidence), ("standard_gauge", standard_gauge)):
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
    seg("Key System Mole: wooden trestle (before the fill)", 1903.82, 1912.0,
        topo("sf1915", (-122.2975, 37.8263), (-122.3080, 37.8243), (-122.3200, 37.8220), (-122.3330, 37.8193)),
        elevated="trestle",
        note="Transbay service from 1903-10-26 on a 17,000 ft wooden trestle; approach filled 1908, causeway "
                 "except the last 3,800 ft by 1916; pier fire 1933-05-06 (rebuilt slightly to the south); ferries "
                 "to the Bay Bridge 1939-01-15, Exposition trains/ferries until 1939-10-29. Geometry: USGS San "
                 "Francisco 1915 sheet ('San Francisco-Oakland Terminal Key Route Pier')." + " Trestle-to-fill change dated 1912 (filled 1908-16, ESTIMATED).", confidence="estimated"),
    seg("Key System Mole: causeway (fill)", 1912.0, 1939.83,
        topo("sf1915", (-122.2975, 37.8263), (-122.3080, 37.8243), (-122.3200, 37.8220), (-122.3330, 37.8193)),
        elevated="ground", mode="interurban",
        note="Transbay service from 1903-10-26 on a 17,000 ft wooden trestle; approach filled 1908, causeway "
                 "except the last 3,800 ft by 1916; pier fire 1933-05-06 (rebuilt slightly to the south); ferries "
                 "to the Bay Bridge 1939-01-15, Exposition trains/ferries until 1939-10-29. Geometry: USGS San "
                 "Francisco 1915 sheet ('San Francisco-Oakland Terminal Key Route Pier')." + " Trestle-to-fill change dated 1912 (filled 1908-16, ESTIMATED).", confidence="estimated"),
    seg("Key Route Pier: last 3,800 ft of trestle and the ferry terminal", 1903.82, 1939.83,
        topo("sf1915", (-122.3330, 37.8193), (-122.3445, 37.8167)),
        elevated="pier", note="Transbay service from 1903-10-26 on a 17,000 ft wooden trestle; approach filled 1908, causeway "
                 "except the last 3,800 ft by 1916; pier fire 1933-05-06 (rebuilt slightly to the south); ferries "
                 "to the Bay Bridge 1939-01-15, Exposition trains/ferries until 1939-10-29. Geometry: USGS San "
                 "Francisco 1915 sheet ('San Francisco-Oakland Terminal Key Route Pier')."),
    seg("Key System main line ashore: mole root - Emeryville (40th St) yard", 1903.82, 1958.3,
        pts((-122.2975, 37.8263), (-122.2955, 37.8267)),
        topo("sf1915", (-122.2955, 37.8267), (-122.2925, 37.8278), (-122.2890, 37.8287), (-122.2850, 37.8292),
             (-122.2810, 37.8298), corridor=60),
        mode="interurban", geometry_confidence="medium",
        note="Double track from the mole across the SP main line to the Key System yard and shops near 40th St / "
             "San Pablo Ave, where the Berkeley, Piedmont, Claremont and 22nd St lines branched; Key trains used "
             "the Bay Bridge from 1939-01-15; last Key train 1958-04-20. Geometry: USGS San Francisco 1915 sheet "
             "(the junction east of the yard is not traced)."),
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
      SPC, standard_gauge=1906.5, segments=[
          seg("Alameda Mole: stone mole and ferry pier (2.5 mi to deep water)", 1884.2, 1940.0,
              topo("sf1915", (-122.3365, 37.7972), (-122.3250, 37.7950), (-122.3120, 37.7928), (-122.3020, 37.7907),
                   (-122.2965, 37.7898)),
              elevated="ground", source_url=WIKI + "Alameda_Mole",
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
      SPC, standard_gauge=1907.5, segments=[
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
    seg("Niles Canyon: Niles - Brightside - Sunol", 1869.68, 9999,
        rail((-121.9715, 37.5786), (-121.9496, 37.5972), (-121.9268, 37.5988), (-121.8952, 37.5941),
             (-121.8805, 37.5994), names=["Niles Canyon"], snap=200),
        note="Western Pacific of 1862-69 (Central Pacific): the first transcontinental trains came down Niles Canyon "
             "in September 1869; SP main line until it was abandoned in 1984 (ESTIMATED); since 1987 the Niles "
             "Canyon Railway heritage line, so still standing (geometry: OSM).", source_url=WIKI + "Niles_Canyon_Railway",
        confidence="estimated"),
    seg("Sunol - Verona - Pleasanton - Remillard - Livermore", 1869.68, 1984.0,
        rail((-121.8805, 37.5994), (-121.8762, 37.6112), (-121.8814, 37.6242), (-121.8860, 37.6371),
             names=["Niles Canyon"], snap=200),
        topo("ple1906", (-121.8860, 37.6371), (-121.8845, 37.6500), (-121.8780, 37.6600), (-121.8700, 37.6670),
             (-121.8600, 37.6700), corridor=150),
        rail((-121.8600, 37.6700), (-121.8350, 37.6740), (-121.7700, 37.6850), snap=250,
             join=200),
        note="Central Pacific 1869 ('Niles and Sacramento Line' on the 1906 Pleasanton sheet); SP main line "
             "until 1984 (end ESTIMATED; the WP line alongside is still in use). Geometry: OSM grade (Niles Canyon "
             "Railway to Verona, Pleasanton - Livermore) and the USGS Pleasanton 1906 sheet.", confidence="estimated"),
    seg("Livermore - Altamont Pass - county line", 1869.68, 1984.0,
        rail((-121.7700, 37.6850), (-121.7417, 37.6923), (-121.6988, 37.7111), (-121.6769, 37.7233),
             (-121.6674, 37.7415), (-121.6454, 37.7435), (-121.5940, 37.7243), (-121.5573, 37.7144), snap=250,
             join=300),
        note="Central Pacific over Altamont Pass (1869); SP abandoned the pass in 1984 (ESTIMATED; the west end "
             "survives as a spur). Geometry: OSM ('Altamont', incl. the summit tunnel).", confidence="estimated"),
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

# =====================================================================================
# MARIN: North Pacific Coast (narrow gauge, 1874-75) / North Shore (1902) / Northwestern Pacific (1907)
# and the San Francisco & North Pacific Tiburon line (1884)
# =====================================================================================
NPC = WIKI + "North_Pacific_Coast_Railroad"
NPS_TB = "https://www.nps.gov/pore/learn/photosmultimedia/photogallery_thenandnow_tomalesbay.htm"
SANS = "https://sananselmohistory.org/articles/trains-in-san-anselmo/"
route("npc", "North Pacific Coast Railroad / North Shore Railroad / Northwestern Pacific (Marin)", "narrow_gauge", NPC,
      standard_gauge=1904.0, segments=[
    seg("Sausalito ferry terminal and waterfront yard", 1875.03, 1941.16,
        topo("sf1899", (-122.4783, 37.8562), (-122.4830, 37.8585), (-122.4885, 37.8605), (-122.4945, 37.8635),
             (-122.5007, 37.8669), corridor=120),
        note="NPC ferry and train terminal at Sausalito (line built from Sausalito from March 1873, open to Tomales "
             "1875-01-11); electric suburban trains from 1903; Sausalito ferries and electric service ended "
             "1941-02-28 (freight continued; end of the Sausalito track not modelled). Geometry: USGS San "
             "Francisco 1899 sheet.", source_url=NPS_TB),
    seg("Sausalito - Waldo Point - Manzanita - Mill Valley Junction (Almonte)", 1875.03, 1971.0,
        rail((-122.5007, 37.8669), (-122.5106, 37.8763), (-122.5177, 37.8818), (-122.5243, 37.8871), snap=200),
        note="Along the Richardson Bay shore (today's Mill Valley - Sausalito Path, OSM); electrified 1903 "
             "(third rail); passenger service ended 1941-02-28; freight end ESTIMATED (1971).",
        confidence="estimated"),
    seg("Mill Valley Junction - Alto", 1884.1, 1971.0,
        rail((-122.5243, 37.8871), (-122.5259, 37.8950), (-122.5270, 37.9018), (-122.5249, 37.9105), snap=200),
        note="Built with the Corte Madera (Alto) tunnel; first train through the tunnel February 1884, the old "
             "Strawberry Point / Alto Hill route abandoned April 1884 (not modelled). End ESTIMATED.",
        confidence="estimated", source_url="https://legacy.sfgenealogy.org/marin/history/rrtimeline.htm"),
    seg("Alto (Corte Madera) tunnel", 1884.1, 1971.0,
        rail((-122.5249, 37.9105), (-122.5262, 37.9180), snap=200),
        elevated="tunnel", confidence="estimated",
        note="First train February 1884; later closed and sealed (end ESTIMATED). Geometry: OSM."),
    seg("Corte Madera - Larkspur - Kentfield (Tamalpais) - Ross - San Anselmo", 1875.03, 1971.0,
        rail((-122.5262, 37.9180), (-122.5285, 37.9229), (-122.5302, 37.9273), snap=100),
        topo("tam1897", (-122.5302, 37.9273), (-122.5330, 37.9350), (-122.5400, 37.9400), (-122.5480, 37.9480),
             (-122.5530, 37.9530), (-122.5570, 37.9620), (-122.5600, 37.9700), (-122.5615, 37.9755), corridor=200),
        confidence="estimated",
        note="NPC main line (1875; standard gauge and electric 1903-04, 'Northwestern Pacific' on the 1910s "
             "Tamalpais sheet); passenger service ended 1941-02-28, freight end ESTIMATED. Geometry: OSM grade "
             "(Larkspur Path) and USGS Tamalpais sheet."),
    seg("San Anselmo (Junction) - San Rafael", 1874.56, 1941.16,
        topo("tam1897", (-122.5615, 37.9755), (-122.5530, 37.9770), (-122.5440, 37.9760), (-122.5350, 37.9745),
             (-122.5290, 37.9730), corridor=130),
        source_url=SANS,
        note="San Anselmo - San Rafael spur opened 1874-07-25 (San Anselmo Historical Museum); electric to San "
             "Rafael 1903-10-17; electric service ended 1941-02-28. Geometry: USGS Tamalpais sheet."),
    seg("San Anselmo - Fairfax - Manor", 1875.03, 1941.16,
        topo("tam1897", (-122.5615, 37.9755), (-122.5690, 37.9790), (-122.5770, 37.9830), (-122.5880, 37.9870),
             (-122.5960, 37.9930), (-122.6005, 37.9980), corridor=130),
        note="NPC narrow gauge (1875); electric suburban trains to Manor from the 1900s; electric service ended "
             "1941-02-28. Geometry: USGS Tamalpais sheet."),
    seg("Manor - White's Hill - San Geronimo - Lagunitas - Shafter - Camp Taylor - Tocaloma", 1875.03, 1933.5,
        topo("pet1914", (-122.6005, 37.9980), (-122.6120, 38.0020), (-122.6250, 38.0045), (-122.6450, 38.0085),
             (-122.6600, 38.0125), (-122.6750, 38.0135), (-122.6900, 38.0125), (-122.7000, 38.0105),
             (-122.7050, 38.0040), (-122.7120, 38.0030), (-122.7180, 38.0100), (-122.7250, 38.0170),
             (-122.7350, 38.0250), (-122.7400, 38.0300), (-122.7450, 38.0400), (-122.7500, 38.0450), corridor=150),
        note="'San Francisco and Cazadero Line' over White's Hill (tunnel) and down Paper Mill (Lagunitas) Creek; "
             "narrow gauge to the end; abandoned 1933 (ESTIMATED; last narrow-gauge trains to Point Reyes 1930). "
             "Geometry: USGS Petaluma 1914 sheet.", confidence="estimated"),
    seg("Tocaloma - Point Reyes Station", 1875.03, 1933.5,
        topo("pr1918", (-122.7500, 38.0450), (-122.7600, 38.0520), (-122.7700, 38.0600), (-122.7790, 38.0680),
             (-122.7860, 38.0680), (-122.7945, 38.0665), (-122.8076, 38.0695), corridor=200),
        note="Last scheduled narrow-gauge train to Point Reyes Station 1930-03-30; abandoned 1933 (ESTIMATED). "
             "Geometry: USGS Point Reyes 1918 sheet (no local alignment; checked against OSM grade fragments).",
        confidence="estimated"),
    seg("Point Reyes Station - Marshall - Tomales Bay shore - Tomales - Sonoma County line", 1875.03, 1930.25,
        rail((-122.8076, 38.0695), (-122.8144, 38.0713), (-122.8364, 38.1008), (-122.8632, 38.1215),
             (-122.8885, 38.1523), (-122.9003, 38.1667), (-122.9176, 38.1914), (-122.9253, 38.2150),
             (-122.9137, 38.2484), (-122.8993, 38.2634), (-122.9084, 38.3056), snap=150, join=150),
        source_url=NPS_TB,
        note="Built 1873-75 along the east shore of Tomales Bay; tracks Point Reyes - Monte Rio abandoned after the "
             "last narrow-gauge train of 1930-03-30. Geometry: OSM (abandoned grade)."),
    seg("Mill Valley branch: Mill Valley Junction - Millwood - Mill Valley", 1889.0, 1941.16,
        topo("tam1897", (-122.5243, 37.8871), (-122.5280, 37.8920), (-122.5340, 37.8960), (-122.5400, 37.9010),
             (-122.5460, 37.9060), corridor=140),
        note="Branch to Mill Valley (opening year ESTIMATED with the 1889-90 founding of the town); electric from "
             "1903-08-20; electric service ended 1941-02-28. Geometry: USGS Tamalpais sheet.",
        confidence="estimated"),
])

route("sfnp_tiburon", "San Francisco & North Pacific Railroad (Tiburon line) / Northwestern Pacific", "rail",
      WIKI + "Northwestern_Pacific_Railroad", [
          seg("Tiburon terminal - Reed - Corte Madera (San Clemente) - Greenbrae", 1884.36, 1967.0,
              rail((-122.4560, 37.8734), (-122.4725, 37.8843), (-122.4889, 37.8997), (-122.5048, 37.9117),
                   (-122.5123, 37.9353), (-122.5133, 37.9466), snap=150, join=60),
              note="SF&NP terminal and ferry slips at Tiburon and the line across the marshes of Richardson Bay and "
                   "Corte Madera to San Rafael (1884); NWP passenger ferries until 1941, car floats and freight until "
                   "the line south of Greenbrae closed (1967, ESTIMATED; Tiburon Linear Park / Old Rail Trail). "
                   "Geometry: OSM grade.", confidence="estimated"),
          seg("Greenbrae - San Rafael", 1884.36, 9999,
              rail((-122.5133, 37.9466), (-122.5180, 37.9580), (-122.5222, 37.9692), snap=300, join=80),
              note="Still in use (SMART Larkspur extension). Geometry: OSM."),
      ])

# =====================================================================================
# SOUTH BAY: SPC San Jose - Los Gatos - Santa Cruz, SP Mayfield Cutoff, Dumbarton, Peninsular Ry
# =====================================================================================
route("spc_south", "South Pacific Coast Railroad (narrow gauge): Santa Clara - San Jose - Los Gatos - Santa Cruz",
      "narrow_gauge", SPC, standard_gauge=1909.2, segments=[
          seg("Santa Clara - San Jose", 1876.5, 9999,
              rail((-121.9398, 37.3550), (-121.9139, 37.3421), (-121.9035, 37.3300), snap=200),
              note="SPC narrow gauge to San Jose (1876; month ESTIMATED); today's UP/Caltrain tracks (geometry: OSM; "
                   "the 1876 SPC depot and street running in San Jose are not modelled).", confidence="estimated"),
          seg("San Jose - Campbell - Vasona Junction", 1878.5, 9999,
              rail((-121.9035, 37.3300), (-121.9028, 37.3256), (-121.9246, 37.3045), (-121.9456, 37.2825),
                   (-121.9637, 37.2589), names=["Vasona", "Caltrain", "Coast"], snap=200),
              note="Extended from San Jose to Los Gatos in 1878 (month ESTIMATED); SP from 1887; still the Vasona "
                   "Industrial Lead (geometry: OSM).", confidence="estimated"),
          seg("Vasona Junction - Los Gatos", 1878.5, 1959.0,
              rail((-121.9637, 37.2589), (-121.9663, 37.2544), (-121.9785, 37.2319), (-121.9800, 37.2287), snap=200),
              note="Last San Jose - Los Gatos commuter train 1955; track to Los Gatos removed later (end ESTIMATED "
                   "1959). Geometry: OSM grade (Los Gatos Creek Trail).", confidence="estimated"),
          seg("Los Gatos - Alma - Wrights - Summit tunnel - Laurel - Glenwood - Zayante - Olympia", 1880.33, 1940.43,
              rail((-121.9800, 37.2287), (-121.9881, 37.2167), (-121.9899, 37.2027), (-121.9846, 37.1758),
                   (-121.9758, 37.1623), (-121.9563, 37.1462), (-121.9642, 37.1217), (-121.9918, 37.0980),
                   (-122.0171, 37.1036), (-122.0352, 37.0984), (-122.0507, 37.0787), snap=200, join=2500),
              note="Mountain line over the Santa Cruz Mountains (eight tunnels) completed 1880 after two years of "
                   "construction; standard gauge 1909 (Summit tunnel damaged in 1906); last train 1940-02-26, "
                   "abandoned 1940-06-04; tunnels dynamited 1942. The grade under Lexington Reservoir (1952) is "
                   "interpolated. Geometry: OSM (abandoned grade and tunnels)."),
          seg("Olympia - Felton", 1880.33, 9999,
              rail((-122.0507, 37.0787), (-122.0557, 37.0639), (-122.0643, 37.0476), snap=200),
              note="SPC main line; today the Santa Cruz, Big Trees & Pacific to Olympia (geometry: OSM)."),
          seg("Felton - Santa Cruz (Felton & Santa Cruz RR)", 1875.8, 9999,
              rail((-122.0643, 37.0476), (-122.0602, 37.0234), (-122.0396, 37.0011), (-122.0324, 36.9870),
                   (-122.0254, 36.9631), snap=200),
              note="Santa Cruz & Felton narrow gauge (1875, absorbed by the SPC by 1879); SP; today the Santa Cruz, "
                   "Big Trees & Pacific (geometry: OSM). Opening month ESTIMATED.", confidence="estimated"),
      ])

route("sp_mayfield_cutoff", "Southern Pacific Mayfield Cutoff (Los Altos line)", "rail", WIKI + "Los_Altos,_California", [
    seg("Mayfield - Los Altos - Monta Vista", 1908.3, 1964.0,
        pts((-122.1428, 37.4292), (-122.1418, 37.4235), (-122.1415, 37.4175)),
        rail((-122.1415, 37.4175), (-122.1343, 37.3996), (-122.1155, 37.3743), (-122.0739, 37.3424),
             (-122.0601, 37.3317), snap=200, join=300),
        note="SP cutoff from Mayfield (Palo Alto) through Los Altos to Los Gatos (opened 1908, month ESTIMATED); "
             "electrified for the Peninsular Railway interurbans (to 1933); abandoned 1964 for the Foothill "
             "Expressway. Geometry: OSM abandoned grade.", confidence="estimated"),
    seg("Monta Vista - Vasona Junction", 1908.3, 9999,
        rail((-122.0601, 37.3317), (-122.0560, 37.3284), (-122.0364, 37.2903), (-122.0070, 37.2757),
             (-121.9765, 37.2627), (-121.9637, 37.2589), names=["Vasona"], snap=200),
        note="Still in use as the Vasona Industrial Lead to the Permanente quarry (geometry: OSM).",
        confidence="estimated"),
])

route("sp_dumbarton", "Southern Pacific Dumbarton Cutoff and rail bridge", "rail", WIKI + "Dumbarton_Rail_Bridge", [
    seg("Newark - Dumbarton rail bridge - Redwood City", 1910.5, 9999,
        rail((-122.0556, 37.5223), (-122.0814, 37.5137), (-122.0966, 37.5064), (-122.1093, 37.4979),
             (-122.1205, 37.4904), (-122.1372, 37.4822), (-122.1640, 37.4796), (-122.2000, 37.4790), snap=250, join=400),
        note="SP cutoff across the bay with a swing-span bridge (opened 1910, month ESTIMATED); out of service "
             "since 1982 and the west trestle damaged by fire in 1998, but the bridge and tracks still stand "
             "(year_end 9999 = still standing). Geometry: OSM.", confidence="estimated"),
])

PEN = WIKI + "Peninsular_Railway_(California)"
route("peninsular", "Peninsular Railway (San Jose & Los Gatos Interurban)", "interurban", PEN, [
    seg("San Jose - Los Gatos via San Jose-Los Gatos Road (Bascom Ave / Los Gatos Blvd)", 1904.21, 1933.2,
        road((-121.8871, 37.3314), (-121.9043, 37.3239), (-121.9320, 37.3233), (-121.9317, 37.3027),
             (-121.9317, 37.2810), (-121.9421, 37.2650), (-121.9539, 37.2514), (-121.9646, 37.2323),
             (-121.9740, 37.2211), snap=150),
        note="San Jose-Los Gatos Interurban, first trip 1904-03-19; Peninsular Railway (SP) from 1909; interurban "
             "service ended 1933 (the company's last car ran 1934-09-30). Route 'via county roads and the San Jose-"
             "Los Gatos Road (now Bascom Avenue and Los Gatos Boulevard)'; geometry follows today's streets "
             "(OSM) - LOW CONFIDENCE in the downtown approach.", confidence="estimated", geometry_confidence="low"),
    seg("San Jose - Cupertino - Monta Vista via Stevens Creek Road", 1907.0, 1933.2,
        road((-121.9320, 37.3233), (-121.9600, 37.3235), (-121.9950, 37.3230), (-122.0322, 37.3225),
             (-122.0600, 37.3240), names=["Stevens Creek"], snap=250),
        note="'Cupertino to San Jose along Stevens Creek Road' (Monta Vista branch). Opening year ESTIMATED. "
             "Geometry: today's Stevens Creek Boulevard (OSM).", confidence="estimated", geometry_confidence="low"),
    seg("Cupertino - Saratoga - Los Gatos along the Saratoga roads (Highway 9)", 1904.21, 1933.2,
        road((-122.0322, 37.3225), (-122.0322, 37.2906), (-122.0320, 37.2593), (-122.0313, 37.2582),
             (-122.0156, 37.2470), (-121.9968, 37.2398), (-121.9850, 37.2290), snap=150),
        note="Saratoga loop of the Peninsular Railway ('Cupertino to Los Gatos along Highway 9'); dates per the "
             "San Jose-Saratoga-Los Gatos timetable (1904-03-19 to 1933-03-12). Geometry: today's roads (OSM) - "
             "LOW CONFIDENCE.", source_url="https://saratogahistory.com/History/PIrailroad.htm",
        confidence="estimated", geometry_confidence="low"),
])

# =====================================================================================
# EAST BAY / CONTRA COSTA: Central Pacific Northern Railway (1878), Santa Fe (1900), Western Pacific (1909-10),
# Oakland, Antioch & Eastern / Sacramento Northern (1910-13), SP San Ramon branch (1891)
# =====================================================================================
route("cp_northern", "Central Pacific 'Northern Railway': Oakland - Berkeley - Richmond - Port Costa - Martinez", "rail",
      WIKI + "Martinez_Subdivision", [
          seg("Oakland - Emeryville - Berkeley - Albany - Richmond - San Pablo - Pinole - Hercules - Rodeo - Crockett -"
              " Port Costa - Martinez", 1878.1, 9999,
              rail((-122.3021, 37.8140), (-122.2927, 37.8416), (-122.3023, 37.8715), (-122.3139, 37.9005),
                   (-122.3378, 37.9246), (-122.3599, 37.9489), (-122.3577, 37.9807), (-122.3430, 38.0020),
                   (-122.3131, 38.0108), (-122.2849, 38.0213), (-122.2636, 38.0407), (-122.2418, 38.0577),
                   (-122.2078, 38.0550), (-122.1781, 38.0431), (-122.1560, 38.0238), (-122.1468, 38.0202),
                   names=["Martinez"], snap=250),
              note="Central Pacific's Northern Railway along the shore of San Francisco and San Pablo bays (opened "
                   "1878, month ESTIMATED; train ferry Solano from Port Costa to Benicia from December 1879 until the "
                   "1930 bridge); today the UP Martinez Subdivision (geometry: OSM).", confidence="estimated"),
          seg("Martinez - Benicia bridge approach (1930)", 1930.8, 9999,
              rail((-122.1468, 38.0202), (-122.1184, 38.0355), (-122.1237, 38.0655), (-122.1037, 38.0939),
                   names=["Martinez"], snap=250),
              note="SP Martinez-Benicia bridge opened 1930 (replacing the Port Costa train ferry); geometry: OSM.",
              confidence="estimated", source_url=WIKI + "Benicia%E2%80%93Martinez_Bridge"),
      ])

SANTAFE = WIKI + "Point_Richmond,_California"
route("atsf_richmond", "Atchison, Topeka & Santa Fe (San Francisco & San Joaquin Valley Ry) to Point Richmond", "rail",
      SANTAFE, [
          seg("Port Chicago - Martinez (Muir trestle) - Franklin Canyon - Hercules - Pinole - Richmond", 1900.4, 9999,
              rail((-121.9310, 38.0310), (-121.9982, 38.0454), (-122.0579, 38.0250), (-122.0824, 38.0053),
                   (-122.1152, 37.9997), (-122.1444, 37.9885), (-122.1728, 37.9975), (-122.2056, 38.0010),
                   (-122.2316, 38.0158), (-122.2565, 38.0117), (-122.2897, 38.0080), (-122.3224, 38.0023),
                   (-122.3534, 37.9915), (-122.3573, 37.9640), (-122.3711, 37.9395), names=["BNSF"], snap=250),
              note="Santa Fe's Valley Road from Stockton reached Point Richmond in 1900 (first train May 1900, month "
                   "ESTIMATED); today the BNSF Stockton Subdivision (geometry: OSM). The line east of Port Chicago "
                   "(Pittsburg - Antioch - Stockton) is outside this file.", confidence="estimated"),
          seg("Richmond yard - Ferry Point tunnel - Ferry Point slip", 1900.4, 1975.0,
              rail((-122.3711, 37.9395), (-122.3755, 37.9318), snap=250),
              pts((-122.3755, 37.9318), (-122.3815, 37.9290), (-122.3870, 37.9215), (-122.3905, 37.9150),
                  (-122.3935, 37.9115)),
              note="Santa Fe terminal and ferry slip at Ferry Point, reached through a tunnel under the Potrero hills; "
                   "passenger ferries to San Francisco from 1900 (moved to the Oakland Pier in 1933), car floats "
                   "until c.1975 (ESTIMATED). Tunnel and slip positions APPROXIMATE.", confidence="estimated",
              geometry_confidence="low"),
      ])

WPRR = WIKI + "Western_Pacific_Railroad"
route("wp_main", "Western Pacific Railroad (Feather River Route) in Alameda County", "rail", WPRR, [
    seg("Oakland Mole - 3rd St - East Oakland (Fruitvale)", 1909.9, 1960.0,
        pts((-122.3050, 37.7942), (-122.2990, 37.7955), (-122.2900, 37.7985), (-122.2760, 37.7965),
            (-122.2600, 37.7910), (-122.2450, 37.7845), (-122.2330, 37.7775), (-122.2197, 37.7697)),
        note="WP's own line from its mole along the Oakland waterfront (3rd Street) to East Oakland; freight from "
             "December 1909, passenger trains from 1910-08-22; later merged with the SP/UP lines (end ESTIMATED). "
             "Geometry hand-placed along the waterfront - LOW CONFIDENCE.", confidence="estimated",
        geometry_confidence="low"),
    seg("East Oakland - San Leandro - Hayward - Niles - Niles Canyon - Sunol - Pleasanton - Livermore - Altamont",
        1909.9, 9999,
        rail((-122.2197, 37.7697), (-122.1674, 37.7292), (-122.1147, 37.6886), (-122.0660, 37.6453),
             (-122.0246, 37.5972), (-121.9681, 37.5745), (-121.9170, 37.5938), (-121.8793, 37.6187),
             (-121.8741, 37.6664), (-121.8066, 37.6765), (-121.7411, 37.6925), (-121.6755, 37.7286),
             (-121.6551, 37.7462), (-121.6002, 37.7239), (-121.5560, 37.7040), names=["UP Oakland"], snap=250),
        note="Golden spike 1909-11-01, freight service December 1909, passenger 1910-08-22; today the UP Oakland "
             "Subdivision (geometry: OSM).", confidence="estimated"),
])

SN = WIKI + "Sacramento_Northern_Railway"
route("sn", "Oakland, Antioch & Eastern / Sacramento Northern Railway", "interurban", SN, [
    seg("Oakland: 40th & Shafter - Shafter Ave - Rockridge - Temescal - Thornhill (Montclair)", 1913.27, 1957.17,
        road((-122.25978, 37.82846), (-122.2575, 37.8360), names=["Shafter"], snap=120),
        pts((-122.2575, 37.8360), (-122.2545, 37.8410), (-122.2500, 37.8435)),
        topo("con1915", (-122.2500, 37.8435), (-122.2420, 37.8445), (-122.2330, 37.8405), (-122.2250, 37.8365),
             (-122.2160, 37.8318), corridor=150),
        note="Terminal yard at 40th St & Shafter Ave; north up Shafter Ave, across College Ave, then the private "
             "right of way past Temescal to Montclair; through service Oakland - Bay Point 1913-04-07 (Key System "
             "Mole from 1913, Bay Bridge 1939); passenger service ended 1941-07-01; freight Oakland - Lafayette "
             "ended 1957-03-01. Geometry: today's Shafter Ave, USGS Concord 1915 sheet ('O.A. and E.').",
        geometry_confidence="medium"),
    seg("Shepherd Canyon - Redwood Peak tunnel - Pinehurst - Canyon - Moraga", 1913.27, 1957.17,
        rail((-122.2150, 37.8316), (-122.2004, 37.8298), (-122.1727, 37.8358), (-122.1455, 37.8193), snap=250),
        note="Up Shepherd Canyon and under the hills near Havens / Eastport (tunnel of ~3,500 ft, sealed after "
             "1957). Geometry: OSM grade."),
    seg("Moraga - Lafayette", 1913.27, 1957.17,
        rail((-122.1455, 37.8193), (-122.1345, 37.8273), (-122.1074, 37.8521), (-122.1128, 37.8875), snap=250),
        note="Today the Lafayette-Moraga Regional Trail (geometry: OSM)."),
    seg("Lafayette - Saranap - Walnut Creek", 1911.5, 1957.17,
        rail((-122.1128, 37.8875), (-122.0962, 37.8858), (-122.0930, 37.8860), snap=250),
        topo("con1915", (-122.0930, 37.8860), (-122.0800, 37.8930), (-122.0700, 37.8990), (-122.0645, 37.9025),
             corridor=250),
        note="Oakland & Antioch Railway extended Walnut Creek - Lafayette 1911 (month ESTIMATED); end of freight "
             "ESTIMATED with the Oakland - Lafayette abandonment. Geometry: OSM grade + USGS Concord 1915 sheet.",
        confidence="estimated"),
    seg("Walnut Creek - Concord - Clyde - Bay Point (Oakland & Antioch Ry, 1910-11)", 1910.5, 1977.0,
        topo("con1915", (-122.0645, 37.9025), (-122.0550, 37.9150), (-122.0450, 37.9270), (-122.0350, 37.9390),
             (-122.0310, 37.9580), (-122.0300, 37.9780), (-122.0250, 37.9990), corridor=300),
        pts((-122.0250, 37.9990), (-121.9950, 38.0150), (-121.9600, 38.0260), (-121.9500, 38.0300)),
        note="Oakland and Antioch Railway opened Bay Point - Walnut Creek 1910; SN freight continued for decades "
             "after passenger service ended in 1941 (end ESTIMATED). Geometry: USGS Concord 1915 sheet south of "
             "38 N, hand-placed to Bay Point - LOW CONFIDENCE east of Concord.", confidence="estimated",
        geometry_confidence="low"),
])

route("sp_san_ramon", "Southern Pacific San Ramon branch (Avon - Concord - Walnut Creek)", "rail",
      WIKI + "Iron_Horse_Regional_Trail", [
          seg("Avon - Pacheco - Concord - Walnut Creek", 1891.5, 1978.0,
              rail((-122.0324, 38.0283), (-122.0388, 37.9985), (-122.0481, 37.9693), (-122.0512, 37.9469),
                   (-122.0563, 37.9169), names=["San Ramon"], snap=250),
              note="SP branch from Avon to Walnut Creek, Danville and San Ramon (1891, month ESTIMATED; extended to "
                   "Radum 1909); abandoned 1978, now the Iron Horse Trail. Only the Avon - Walnut Creek part "
                   "(OSM 'San Ramon Line') is traced here.", confidence="estimated"),
      ])

# =====================================================================================
# OAKLAND: San Francisco & Oakland Railroad (1863) on 7th Street
# =====================================================================================
route("sfo_7th_st", "San Francisco & Oakland Railroad / SP 7th Street line (Oakland)", "rail",
      WIKI + "East_Bay_Electric_Lines", [
          seg("Oakland Point - 7th St - Broadway", 1863.67, 1941.57,
              road((-122.3062, 37.8081), (-122.2960, 37.8056), (-122.2828, 37.8027), (-122.2766, 37.8005),
                   names=["7th Street"], snap=120),
              note="San Francisco & Oakland Railroad ferry-train line from the Oakland Point wharf along 7th Street "
                   "(opened September 1863); Central Pacific 1868-69; SP steam commute trains, electrified 1911-12 "
                   "(East Bay Electric Lines / Interurban Electric Ry); last train 1941-07-26. Geometry: today's 7th "
                   "Street (OSM).", confidence="estimated"),
          seg("7th St east of Broadway to the Lake Merritt outlet (toward Brooklyn / East Oakland)", 1864.5, 1941.57,
              road((-122.2766, 37.8005), (-122.2705, 37.7980), (-122.2643, 37.7956), (-122.2586, 37.7928),
                   names=["7th Street"], snap=120),
              note="SF&O extension east toward Brooklyn (year ESTIMATED); the 7th Street line of the SP electric "
                   "trains (1911-41). Its continuation through East Oakland to Fruitvale is not traced here.",
              confidence="estimated"),
      ])
