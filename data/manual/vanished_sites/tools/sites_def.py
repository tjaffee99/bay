"""Site definitions (local metre frames; see trace_sites.py). Coordinates read from the
renders described in README.md; automated extractions are stored in traced/*.json."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import shapely
import shapely.ops
from shapely.geometry import Polygon, LineString, MultiPolygon

from trace_sites import Site, P, ring, path_poly
import geom

_H = Path(__file__).resolve().parent
TR = _H / "traced" if (_H / "traced").exists() else _H.parent / "traced"


def J(name):
    return json.loads((TR / name).read_text())


def smooth(poly, r=2.0):
    """Remove map-symbol jaggies (close then open)."""
    p = poly.buffer(r, join_style=1).buffer(-2 * r, join_style=1).buffer(r, join_style=1)
    if isinstance(p, MultiPolygon):
        p = max(p.geoms, key=lambda g: g.area)
    return p


# =====================================================================================
# Bay Meadows Racecourse, San Mateo (1934-2008)
# =====================================================================================
def bay_meadows():
    S = Site("bay_meadows", "Bay Meadows Racecourse", "racetrack", -122.2971, 37.5427,
             "https://en.wikipedia.org/wiki/Bay_Meadows_Racetrack")
    OPEN, CLOSE = 1934.87, 2008.77           # opened 13 Nov 1934; last race 17 Aug 2008, training to 8 Oct 2008
    WIKI = S.src
    TOPO = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/CA_San%20Mateo_295033_1993_24000_geo.tif"  # USGS San Mateo 1:24k 1993; other editions in README
    # main oval: stadium fitted to the track symbol of the 1993 sheet (centreline, rms 3 m);
    # the 1946/1956 sheets draw the track edges 10 m inside / 12 m outside it -> inner rail
    # perimeter 1,613 m = the documented 1-mile dirt oval. Turf course: 7 furlongs (1,408 m)
    # at its inner rail, same centre/straights (documented size; position estimated).
    u, v, a, L, Rc = -27.53, 31.6, -8.04, 201.75, 138.29
    Ri, Ro = Rc - 10.0, Rc + 12.0
    Ti = (1408.0 - 4 * L) / (2 * np.pi)       # 95.6 m
    To = Ti + 21.0
    st = lambda R: geom.stadium(u, v, a, L, R, step=2.0)
    chute_nw = geom.axis_rect(u, v, a, L - 5, L + 100, -Ro, -Ri)    # homestretch extension (1946/56 sheets)
    chute_se = geom.axis_rect(u, v, a, -L - 90, -L + 5, Ri, Ro)     # backstretch chute (1956/93 sheets)
    dirt = ring(st(Ro), st(Ri)).union(chute_nw).union(chute_se)
    oval_all = st(Ro).union(chute_nw).union(chute_se)
    S.part(dirt, "dirt_track", OPEN, CLOSE, "exact",
           "1-mile dirt main track (inner rail 1,613 m) with the homestretch chute (NW) and the backstretch chute (SE); "
           "fitted to the USGS 1:24k San Mateo sheets 1947 (1946 photos), 1956, 1968, 1980, 1993, 1997; chute lengths estimated",
           surface="dirt track", src=TOPO)
    S.part(ring(st(Ri), st(To)), "grass", OPEN, CLOSE, "estimated", "grass strip between the turf course and the dirt track's inner rail",
           surface="lawn", src=TOPO)
    S.part(ring(st(To), st(Ti)), "turf", OPEN, CLOSE, "estimated",
           "Longden Turf Course, 7 furlongs (documented); width 21 m and course start year estimated (an inner course line "
           "is already drawn on the 1946-photo sheet)", surface="turf course", src="https://pcad.lib.washington.edu/building/13205")
    ponds = shapely.union_all([P(p) for p in J("bay_meadows_1956_ponds.json")]).buffer(2).buffer(-2)
    inner = st(Ti)
    S.part(inner.difference(ponds), "grass", OPEN, 1962.0, "estimated", "infield (with its ponds, 1946/1956 sheets)", surface="lawn", src=TOPO)
    S.part(ponds.intersection(inner), "water", OPEN, 1962.0, "estimated",
           "infield ponds traced from the 1956 sheet (blue); absent on the 1968 photorevision -> end year estimated",
           surface="pond", src=TOPO)
    S.part(inner, "grass", 1962.0, CLOSE, "estimated", "infield (ponds filled by 1968)", surface="lawn", src=TOPO)
    # property of the main track (the 83-acre Bay Meadows II parcel): its outline is the graded
    # ground on the Oct 2010 orthophoto (Esri Wayback 2014-02-20, Microsoft UltraCam 26 Oct 2010)
    parcel = P([(0, 440), (40, 430), (115, 195), (150, -20), (175, -240), (-60, -445), (-130, -420), (-270, -200),
                (-395, 0), (-430, 130), (-245, 210), (-220, 330), (-150, 405), (-60, 435)])
    S.part(parcel.difference(oval_all), "parking", OPEN, CLOSE, "estimated",
           "racetrack grounds: parking lots, paddock, aprons and service roads around the oval (property outline = graded "
           "parcel on the Oct 2010 orthophoto, west side to the railway as on the 1956/1993 sheets; surface assumed paved)", surface="parking / paddock",
           src="https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/10/{level}/{row}/{col}")
    # Phase I land (sold off in 1997-2000: stables and the practice track) — 1993 sheet
    ph1 = P([(40, 430), (180, 400), (430, 620), (600, 430), (630, 300), (640, 110), (540, -30), (500, -20), (200, -220),
             (175, -240), (150, -20), (115, 195)])
    tu, tv, ta, tL, tR = 440.8, 329.6, -44.0, 106.2, 100.9      # practice track, fitted to the 1993 sheet (perimeter 1,059 m)
    tst = lambda R: geom.stadium(tu, tv, ta, tL, R, step=2.0)
    PH1_END = 1998.0
    S.part(ph1.difference(tst(tR + 9)), "industrial", 1951.0, PH1_END, "estimated",
           "stable area (shedrow barns, tack rooms, dormitories) east of the track, sold for Bay Meadows Phase I "
           "(Franklin Templeton campus opened 2001); barns absent on the 1946-photo sheet, present on the 1956 sheet",
           surface="stable yard", src="https://globest.com/2008/04/23/83-acre-race-track-redevelopment-gains-city-ok")
    S.part(ring(tst(tR + 9), tst(tR - 9)), "dirt_track", 1962.0, PH1_END, "estimated",
           "practice (training) track, 5/8 mile, fitted to the 1993 sheet; first drawn on the 1968 photorevision", surface="dirt track",
           src=TOPO)
    S.part(tst(tR - 9), "grass", 1962.0, PH1_END, "estimated", "practice-track infield", surface="lawn", src=TOPO)
    # ---- buildings
    gs = J("bay_meadows_grandstand.json")
    S.bldg(smooth(P(gs["g1947"]), 2.0), "Bay Meadows grandstand and clubhouse (1934)", 1934.0, 1951.0, 15.0, 3, "concrete",
           "grandstand", "estimated",
           "outline from the 1947 sheet (1946 photos); replaced/enlarged by the larger stand drawn on the 1956 sheet "
           "(year of the enlargement estimated); height estimated", src=WIKI)
    S.bldg(smooth(P(gs["g1956"]), 3.0), "Bay Meadows grandstand and clubhouse", 1951.0, 2008.9, 18.0, 4, "concrete",
           "grandstand", "estimated",
           "outline of the cross-hatched building on the 1956 sheet (same on the 1968/1980/1993 sheets); 12,000 seats "
           "(PCAD); gutted Oct 2008 and imploded late 2008 (DRF, 1 Oct 2008); height estimated",
           src="https://www.drf.com/news/piece-history-about-crumble")
    for b in J("bay_meadows_1993_buildings.json"):
        poly = P(b["coords"])
        x = b["cx"]
        in_ph1 = ph1.contains(poly.centroid)
        end = PH1_END if in_ph1 else 2008.85
        if b["role"] == "barn":
            S.bldg(poly, "Bay Meadows stable (shedrow barn)", b["start"], end, 5.0, 1, "wood frame", "other", "estimated",
                   f"barn symbol of the 1993 sheet (filled, {b['w']} x {b['l']} m); start: {b['start_note']}; "
                   + ("end: Phase I sale (estimated)" if in_ph1 else "end: track closure 2008"), src=TOPO)
        elif b["role"] == "small":
            S.bldg(poly, "Bay Meadows outbuilding", b["start"], end, 5.0, 1, "wood frame", "other", "estimated",
                   f"small building symbol of the 1993 sheet; start: {b['start_note']}", src=TOPO)
        else:
            S.bldg(poly, "Bay Meadows track building", b["start"], end, 7.0, 2, "wood frame", "other", "estimated",
                   f"building symbol of the 1993 sheet ({b['w']} x {b['l']} m; infield tote board / track office); start: {b['start_note']}",
                   src=TOPO)




# =====================================================================================
# Hewlett-Packard Cupertino site (1969-2014) and Apple Park grounds (2017-)
# =====================================================================================
def _start_from_ink(ink, eds, thr=0.15):
    """First edition with ink >= thr -> midpoint of the previous edition's photo year and it."""
    for i, (f, y) in enumerate(zip(ink, eds)):
        if f >= thr:
            if i == 0:
                return None, f"present on the {y} edition"
            return round((eds[i - 1] + y) / 2), f"absent on the {eds[i - 1]} edition, present on the {y} edition"
    return round((eds[-1] + 2010) / 2), f"absent on the {eds[-1]} edition, present on the Oct 2010 orthophoto"


def hp_apple():
    S = Site("hp_cupertino", "Hewlett-Packard Cupertino site (Wolfe Rd / Pruneridge Ave)", "office_campus", -122.0090, 37.3345,
             "https://www.hpmuseum.net/divisions.php?did=2")
    ORTHO = "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/10/{level}/{row}/{col}"   # Wayback 2014-02-20 = Microsoft UltraCam 26 Oct 2010, 0.3 m
    TOPO = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/CA_Cupertino_289701_1991_24000_geo.tif"  # USGS Cupertino 1:24k 1991 (editions in README)
    END = 2014.0          # demolition began late 2013 after the 15 Oct 2013 approval (Wikipedia, Apple Park)
    eds = [1960, 1968, 1973, 1979, 1991]
    tr = J("hp_cupertino_2010.json")
    names = {"A": "HP Cupertino Division building (1969, west half)", "B": "HP Cupertino Division building (1969, east half)"}
    for key, b in tr.items():
        poly = P(b["coords"])
        y0, why = _start_from_ink(b["ink"], eds)
        if key in ("A", "B"):
            y0, why = 1969, "HP Cupertino Division moved into its new 150,000 sq ft building at Wolfe Rd & Homestead in 1969 (HP Museum); first drawn on the 1968 photorevision (under construction)"
        south = key.startswith("S")
        end, endwhy = END, "demolished for Apple Park (late 2013-2014)"
        if key == "B":
            end, endwhy = 2009.5, "already a demolition pad (rubble around a dark basement slab) on the Oct 2010 orthophoto; year estimated"
        name = names.get(key, "office / R&D building (Pruneridge Ave campus)" if south else "HP Cupertino site building")
        S.bldg(poly, name, y0, end, 13.0 if south else 9.0, 3 if south else 2, "tilt-up", "office", "estimated",
               f"footprint from the Oct 2010 orthophoto ({'hand-read corners' if key in ('A', 'B') or south or key in ('G1', 'n248') else 'roof segmentation, orthogonalised'}); "
               f"start: {why}; end: {endwhy}; storeys/height estimated",
               src=ORTHO)
    # ---- ground: campus zones dated by their first buildings; Pruneridge Ave (removed 2014)
    curve = [(-490, -32), (-390, -32), (-290, -75), (-190, -165), (-110, -230), (-10, -275), (90, -270), (190, -258), (295, -242)]
    road = path_poly(curve, 16.0)
    ap_ll = None
    import geopandas as gpd
    osm = gpd.read_file(TR / "apple_park_osm.geojson")
    ap_ll = osm[(osm.theme == "land_use") & (osm["name"] == "Apple Park")].geometry.iloc[0]
    ap = S.loc(ap_ll).buffer(0)
    west_of_tantau = Polygon([(-480, 380), (288, 380), (288, -760), (-480, -760)])
    site = ap.intersection(west_of_tantau)
    north_poly = Polygon([(-480, 380), (300, 380)] + [(x, y + 8) for x, y in reversed(curve)][0:0] + [(300, -234)] +
                         [(x, y + 8) for x, y in reversed(curve)] + [(-480, -24)])
    north = site.intersection(north_poly).difference(road)
    south = site.difference(north_poly).difference(road)
    zones = [
        (north.intersection(Polygon([(-480, 400), (-130, 400), (-130, -400), (-480, -400)])), 1969.0,
         "HP Cupertino Division site from 1969 (first building, parking lots)"),
        (north.intersection(Polygon([(-130, 400), (60, 400), (60, -400), (-130, -400)])), 1976.0,
         "central part of the HP site: buildings first drawn on the 1979 photorevision (orchard on 1973)"),
        (north.intersection(Polygon([(60, 400), (300, 400), (300, -400), (60, -400)])), 1985.0,
         "east part of the HP site: still prune orchard on the 1979 photorevision, buildings on the 1991 sheet"),
        (south.intersection(Polygon([(-480, 0), (-100, 0), (-100, -800), (-480, -800)])), 1970.0,
         "office campus south of Pruneridge Ave, first buildings on the 1973 photorevision"),
        (south.intersection(Polygon([(-100, 0), (150, 0), (150, -800), (-100, -800)])), 1985.0,
         "office campus south of Pruneridge Ave, buildings first on the 1991 sheet"),
        (south.intersection(Polygon([(150, 0), (300, 0), (300, -800), (150, -800)])), 1970.0,
         "office campus by Tantau Ave, first buildings on the 1973 photorevision"),
    ]
    for g, y0, note in zones:
        S.part(g, "parking", y0, END, "estimated",
               note + "; parking lots, driveways and landscaped strips around the buildings (orchard before); cleared for Apple Park",
               surface="office park", src=TOPO)
    S.part(road, "parking", 1964.0, END, "estimated",
           "Pruneridge Avenue through the site (curved alignment from Wolfe Rd to Tantau Ave), traced on the Oct 2010 orthophoto; "
           "absent on the 1961 sheet (1960 photos), drawn on the 1968 edition; closed and removed for Apple Park (2014)",
           surface="road", name="Pruneridge Avenue (old alignment)", src=ORTHO)

    # ---- Apple Park grounds from OpenStreetMap (via Overture base / transportation, ODbL)
    A = Site("apple_park", "Apple Park grounds", "campus_grounds", -122.0090, 37.3345,
             "https://www.openstreetmap.org/way/38789619")
    OPEN = 2017.3     # employees moved in from April 2017 (landscaping planted 2016-17)
    WIDTH = {"footway": 3.5, "path": 3.0, "cycleway": 3.5, "pedestrian": 6.0, "steps": 3.0, "service": 6.0,
             "unclassified": 8.0, "track": 3.0}
    A.part(site, "park", OPEN, 9999, "exact",
           "Apple Park campus grounds (OSM landuse outline west of Tantau Ave): native grassland, woods, orchards; ~80 % "
           "landscaped (Wikipedia); the main building, parking structures and other buildings are today's footprints",
           surface="campus park", src="https://en.wikipedia.org/wiki/Apple_Park")
    big = shapely.union_all([A.loc(g) for g in gpd.read_file(TR / "apple_park_buildings_today.geojson").geometry]).buffer(1)
    for r in osm.itertuples():
        cls, theme = r[4], r.theme       # 'class'
        g = A.loc(r.geometry)
        if theme in ("land", "land_use", "water"):
            if theme == "land_use" and cls == "commercial":
                continue
            m = {"forest": ("park", "wood"), "wood": ("park", "wood"), "grassland": ("grass", "meadow"),
                 "grass": ("grass", "lawn"), "orchard": ("park", "orchard"), "pitch": ("turf", "sports field"),
                 "pedestrian": ("parking", "plaza"), "pond": ("water", "pond"), "basin": ("water", "pond")}.get(cls)
            if not m:
                continue
            for p in getattr(g, "geoms", [g]):
                if p.geom_type != "Polygon" or p.area < 30:
                    continue
                A.part(Polygon(p.exterior).simplify(0.4), m[0], OPEN, 9999, "exact",
                       f"OSM {cls} ({r.rec}) via Overture base", surface=m[1], src="https://www.openstreetmap.org/")
        elif theme == "segment" and cls in WIDTH:
            w = WIDTH[cls]
            g = g.intersection(site).difference(big)  # inside the campus west of Tantau Ave; not on/in the buildings
            if g.is_empty:                           # (parking-structure aisles, corridors)
                continue
            for ln in getattr(g, "geoms", [g]):
                if ln.geom_type != "LineString" or ln.length < 2:
                    continue
                # closed or long lines in pieces so no polygon encloses ground (ground detail fills outer rings)
                n = max(1, int(np.ceil(ln.length / 60.0)))
                if ln.is_closed:
                    n = max(n, 3)
                for k in range(n):
                    seg = shapely.ops.substring(ln, k / n * ln.length, (k + 1) / n * ln.length)
                    if seg.length < 1:
                        continue
                    pg = seg.simplify(0.3).buffer(w / 2, quad_segs=2, cap_style=1, join_style=1).simplify(0.2)
                    if len(pg.interiors):
                        pg = Polygon(pg.exterior)
                    A.part(pg, "parking", OPEN, 9999, "exact" if cls not in ("service", "unclassified") else "exact",
                           f"OSM {cls} centreline ({r.rec}) via Overture, buffered to {w} m (width estimated)",
                           surface="road" if cls in ("service", "unclassified") else "footpath",
                           name="Apple Park Way (campus ring road)" if (r.name == "Apple Park Way") else None,
                           src="https://www.openstreetmap.org/")


# =====================================================================================
# Tanforan Racetrack, San Bruno (1899-1964) and the Tanforan Assembly Center (1942)
# =====================================================================================
def tanforan():
    S = Site("tanforan", "Tanforan Racetrack", "racetrack", -122.4192, 37.6356,
             "https://en.wikipedia.org/wiki/Tanforan_Racetrack")
    TOPO = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/CA_San%20Francisco%20South_300066_1947_24000_geo.tif"   # USGS San Francisco South 1:24k 1947 (1946 photos)
    OPEN, FIRE, GONE = 1899.84, 1964.58, 1965.0   # opened 4 Nov 1899; grandstand burned 31 Jul 1964; site cleared after
    tr = J("tanforan_topo.json")
    # 1-mile oval fitted to the 1947 sheet (1946 photos): inner line perimeter 1,610 m, outer edge 26 m outside
    u, v, a, L, Ri = 60.8, 173.6, -27.8, 195.8, 131.6
    Ro = Ri + 26.0
    st = lambda R: geom.stadium(u, v, a, L, R, step=2.0)
    S.part(ring(st(Ro), st(Ri)), "dirt_track", OPEN, 1964.2, "exact",
           "1-mile dirt oval (major axis toward Mount Hamilton), fitted to the USGS 1:24k San Francisco South sheets "
           "1947 (1946 photos) and 1956; last race 1963, closure approved Feb 1964", surface="dirt track", src=TOPO)
    lake = shapely.union_all([P(p) for p in tr["ponds"]["1956"]]).intersection(st(Ri - 5))
    ponds = shapely.union_all([P(p) for p in tr["ponds"]["1947"]]).intersection(st(Ri - 5))
    S.part(st(Ri).difference(ponds), "grass", OPEN, 1951.0, "estimated", "infield", surface="lawn", src=TOPO)
    S.part(ponds, "water", OPEN, 1951.0, "estimated",
           "two infield ponds traced from the 1947 sheet (1946 photos); their age is unknown (start = opening, ESTIMATE)",
           surface="pond", src=TOPO)
    S.part(st(Ri).difference(lake), "grass", 1951.0, 1964.2, "estimated", "infield", surface="lawn", src=TOPO)
    S.part(lake, "water", 1951.0, 1964.2, "estimated",
           "infield lake traced from the 1956 sheet (enlarged from the 1946 ponds; year estimated)", surface="pond", src=TOPO)
    prop = P([(-484, 720), (21, 720), (72, 600), (160, 400), (252, 200), (347, 0), (440, -170), (-20, -185),
              (-110, 0), (-205, 200), (-298, 400), (-400, 600)])
    S.part(prop.difference(st(Ro)), "parking", OPEN, GONE, "estimated",
           "racetrack grounds between El Camino Real and the railroad (stables, paddock, parking); 143-acre property "
           "sold Mar 1964; Tanforan Park shopping center opened 1971", surface="parking / paddock", src=S.src)
    names = {"grandstand": "Tanforan steel grandstand and clubhouse", "clubhouse": "Tanforan entrance / clubhouse building",
             "hall": "Tanforan track building", "barn": "Tanforan stable (shedrow barn)", "tote": "infield tote board"}
    for b in tr["b1947"]:
        poly = P(b["coords"])
        if b["role"] == "grandstand":
            poly = smooth(poly, 2.0)
            S.bldg(poly, "Tanforan grandstand (first, 1899)", OPEN, 1922.9, 12.0, 2, "wood frame", "grandstand", "estimated",
                   "1899 grandstand (3,000 seats); footprint ASSUMED = the later stand's site (LOW confidence)")
            S.bldg(poly, names["grandstand"], 1923.0, FIRE, 16.0, 3, "steel", "grandstand", "estimated",
                   "steel grandstand (work began Dec 1922, 5,000 seats) traced from the 1947 sheet; destroyed with the clubhouse "
                   "in the fire of 31 Jul 1964; height estimated", src=S.src)
            continue
        S.bldg(poly, names[b["role"]], 1933.0, GONE, 5.0 if b["role"] == "barn" else 7.0, 1, "wood frame",
               "other" if b["role"] == "barn" else "hall", "estimated",
               f"building symbol of the 1947 sheet (1946 photos), {b['w']} x {b['l']} m; built by 1942 (26 stables east "
               "of the infield housed detainees in 1942); start year = racing's return in 1933 (ESTIMATE); cleared 1964-65",
               src=TOPO)
    for b in tr["b1956"]:
        poly = P(b["coords"])
        S.bldg(poly, names[b["role"]], 1951.0, GONE, 5.0 if b["role"] == "barn" else 8.0, 1, "wood frame",
               "other" if b["role"] == "barn" else "hall", "estimated",
               f"outlined building of the 1956 sheet, absent on the 1946-photo sheet ({b['w']} x {b['l']} m); start year = midpoint",
               src=TOPO)
    # Tanforan Assembly Center (28 Apr - 13 Oct 1942): ~76 barracks of 20 x 100 ft in the infield (Densho);
    # their layout is not documented here -> rows along the track axis (PROCEDURAL)
    A = Site("tanforan_assembly_center", "Tanforan Assembly Center", "military", -122.4192, 37.6356,
             "https://encyclopedia.densho.org/Tanforan_(detention_facility)/")
    free = st(Ri - 12).difference(ponds.buffer(8))
    t = np.radians(a)
    ax, ay = np.sin(t), np.cos(t)
    nx, ny = ay, -ax
    cands = []
    for i in range(-8, 9):
        for j in range(-8, 9):
            s_, n_ = i * 40.0, j * 18.0
            cx_, cy_ = u + s_ * ax + n_ * nx, v + s_ * ay + n_ * ny
            g = geom.axis_rect(cx_, cy_, a, -15.25, 15.25, -3.05, 3.05)
            if free.contains(g):
                cands.append((abs(n_) + abs(s_) * 0.3, g))
    cands.sort(key=lambda c: c[0])
    for _, g in cands[:76]:
        A.bldg(g, "assembly-center barrack (20 x 100 ft)", 1942.32, 1945.9, 4.0, 1, "wood frame", "dwelling", "procedural",
               "documented count/size/location (about 76 of ~180 barracks were in the infield, 20 x 100 ft; Densho); positions "
               "GENERATED in rows; end year estimated (Army 1942-43, Navy to 1945; absent on the 1946 photos)")


# =====================================================================================
# Ford San Jose Assembly Plant, Milpitas (1955-1983; main building -> Great Mall 1994)
# =====================================================================================
def ford_milpitas():
    S = Site("ford_milpitas", "Ford San Jose Assembly Plant", "factory", -121.8980, 37.4158,
             "https://en.wikipedia.org/wiki/Great_Mall_of_the_Bay_Area")
    TOPO = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/CA_Milpitas_465942_1961_24000_geo.tif"   # USGS Milpitas 1:24k, 1980 photorevision (editions in README)
    tr = J("ford_milpitas_topo.json")
    site = P([(-330, 330), (40, 420), (120, 330), (330, -200), (330, -400), (60, -420), (-200, -250), (-330, -100)])
    S.part(site.difference(P(tr["plant1979"]).buffer(2)), "industrial", 1955.0, 1993.0, "estimated",
           "plant yard: employee parking, car storage lots and rail sidings between Main St and the Western Pacific line "
           "(1961-1980 sheets); plant closed 1983, converted to the Great Mall (opened 22 Sep 1994) - the main assembly "
           "building survives inside the mall (today's footprint, which should be dated 1955)", surface="factory yard", src=TOPO)
    eds = [1960, 1968, 1973, 1979]
    for b in tr["gone"]:
        ink = [b["ink"][str(y)] for y in eds]
        y0, why = _start_from_ink(ink, eds, 0.3)
        if y0 is None:
            y0, why = 1955.0, "on the 1961 sheet (1960 photos); plant built 1955"
        S.bldg(P(b["coords"]), "Ford assembly plant building (demolished)", y0, 1993.0, 9.0, 1, "steel", "factory", "estimated",
               f"plant part drawn on the 1961-1980 sheets that is not in today's footprints ({b['area']} m2); start: {why}; "
               "end: mall conversion (1993, ESTIMATE)", src=TOPO)


# =====================================================================================
# Marine World / Africa USA, Redwood Shores (1968-1986; site -> Oracle HQ)
# =====================================================================================
def marine_world():
    S = Site("marine_world", "Marine World / Africa USA (Redwood Shores)", "amusement_park", -122.2640, 37.5300,
             "https://en.wikipedia.org/wiki/Marine_World/Africa_USA")
    TOPO = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/CA_San%20Mateo_300164_1956_24000_geo.tif"   # USGS San Mateo 1:24k, 1980 photorevision (1978 photos)
    tr = J("marine_world_topo.json")
    park = shapely.union_all([P(p) for p in tr["park1978"]]).difference(P([(-213, -140), (80, -140), (80, 55), (-213, 55)]))
    park = smooth(park, 3.0)
    OPEN, CLOSE = 1968.5, 1986.0
    S.part(park, "park", OPEN, CLOSE, "estimated",
           "built-up park area (show stadiums, pools, animal areas, lawns) = the magenta built-up tint labelled MARINE WORLD "
           "on the 1980 photorevision (1978 photos); opened July 1968, moved to Vallejo 1986; Oracle HQ from 1989",
           surface="theme park", src=TOPO)
    S.bldg(shapely.Point(-25, 205).buffer(17, 24), "Marine World round show building", OPEN, CLOSE, 9.0, 1, "steel", "hall",
           "estimated", "ring symbol (r = 17 m) of the 1980 photorevision, hand-placed; height estimated", src=TOPO)
    lot = P([(-213, -140), (80, -140), (80, 60), (-213, 60)]).difference(park)
    S.part(lot, "parking", OPEN, CLOSE, "estimated", "parking lot = dashed outline on the 1980 photorevision", surface="parking",
           src=TOPO)
    for c in tr["bldg1978"]:
        g = P(c)
        if g.area / g.convex_hull.area < 0.75:      # ragged blobs = dot pattern / tree symbols, not buildings
            continue
        S.bldg(g.convex_hull if g.area > 700 else g, "Marine World show building / stadium", OPEN, CLOSE, 8.0, 1, "steel",
               "hall", "estimated",
               "purple building symbol of the 1980 photorevision (1978 photos), outline approximate (symbol blob); start = "
               "opening year (buildings may be later additions); height estimated", src=TOPO)


# =====================================================================================
# Frontier Village amusement park + Frontier drive-in, San Jose (1961-1980)
# =====================================================================================
def frontier_village():
    S = Site("frontier_village", "Frontier Village", "amusement_park", -121.8240, 37.2650,
             "https://en.wikipedia.org/wiki/Frontier_Village")
    TOPO = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/CA_San%20Jose%20East_300103_1961_24000_geo.tif"   # USGS San Jose East 1:24k, 1973 photorevision
    tr = J("frontier_village_topo.json")
    OPEN, CLOSE = 1961.8, 1980.75          # 21 Oct 1961 - 28 Sep 1980; rides/buildings auctioned Oct 1980
    lake = P(tr["lake1973"]["outer"])
    island = shapely.union_all([P(h) for h in tr["lake1973"]["islands"]]) if tr["lake1973"]["islands"] else Polygon()
    grounds = P(tr["park1973"]).intersection(P([(60, 260), (460, 260), (460, -232), (240, -232), (100, -125), (60, -125)]))
    S.part(grounds.difference(lake), "park", OPEN, CLOSE, "estimated",
           "amusement-park grounds (green park tint labelled AMUSEMENT PARK, 1973 photorevision): Main Street, rides, "
           "narrow-gauge railroad round the perimeter; part became Edenvale Garden Park, the west part housing (Bren)",
           surface="theme park", src=TOPO)
    S.part(lake.difference(island), "water", OPEN, CLOSE, "estimated",
           "Rainbow Falls trout pond and the canoe canal round Indian Island (Fort Far West): the unshaded area with blue "
           "shore lines inside the park tint of the 1973 photorevision (outline includes narrow banks)", surface="pond", src=TOPO)
    for b in tr["bldg1973"]:
        if b["cy"] < -200:      # cross-plan church: still standing today (today's footprint)
            continue
        S.bldg(P(b["coords"]), "Frontier Village building", OPEN, CLOSE, 6.0, 1, "wood frame", "hall", "estimated",
               "building symbol of the 1973 photorevision; start = opening; all buildings removed after the Oct 1980 auction",
               src=TOPO)
    D = Site("frontier_drive_in", "Frontier Village drive-in (Frontier Auto Movie)", "drive_in", -121.8240, 37.2650,
             "https://www.cinematreasures.org/theaters/70447")
    D.part(P([(25, -180), (120, -180), (170, -220), (240, -230), (240, -380), (85, -385), (85, -410), (25, -410)]),
           "parking", 1962.3, 1980.75, "estimated",
           "drive-in ramps ('Drive-in Theater' label and dashed outline on the 1973 photorevision; outline approximate); "
           "opened Apr 1962 (San Jose News ad cited by Cinema Treasures), closed with the park c. 1980 (ESTIMATE)",
           surface="drive-in", src=TOPO)


def build():
    bay_meadows()
    hp_apple()
    tanforan()
    ford_milpitas()
    marine_world()
    frontier_village()
