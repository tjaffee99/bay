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


def rail(*wps, names=None, snap=150.0, kinds=("heavy",), join=25.0, smooth=None):
    return {"method": "rail", "wps": list(wps), "names": names, "snap": snap, "kinds": kinds, "join": join,
            "smooth": smooth}


def road(*wps, snap=60.0):
    return {"method": "road", "wps": list(wps), "snap": snap, "join": 8.0}


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
