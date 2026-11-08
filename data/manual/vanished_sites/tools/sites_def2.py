"""Site definitions, second batch (2026-11): pre-war resorts and amusement parks.

Same local-metre frames and Site API as sites_def.py. Sanborn sheets (Library of Congress) are fitted
to today's parcel blocks by an affine transform of four block corners (tools: README "Method / Sanborn
sheets"); the fitted footprints are stored in traced/*.json by the tracing scripts and turned into
site parts / buildings here. Anything placed from photographs or descriptions says so (confidence
`estimated`, note "ESTIMATE")."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point

from trace_sites import Site, P, ring, path_poly
import geom

_H = Path(__file__).resolve().parent
TR = _H / "traced" if (_H / "traced").exists() else _H.parent / "traced"
LOC = "https://www.loc.gov/item/"
TOPO = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/"


def J(name):
    return json.loads((TR / name).read_text())


def poly(coords, holes=None):
    return Polygon(coords, holes or None).buffer(0)


# =====================================================================================
# Idora Park, Oakland (1903-1929)
# =====================================================================================
def idora_park():
    d = J("idora_park_1911.json")
    S = Site("idora_park", "Idora Park", "amusement_park", d["cx"], d["cy"], "https://en.wikipedia.org/wiki/Idora_Park")
    SB = LOC + "sanborn00727_007/"          # Oakland 1911-12 vol. 3 (1911), sheet 293
    SB50 = LOC + "sanborn00727_017/"        # 1911-Oct 1950 vol. 3, sheet 293 ("new sheet Oct 1931": the Idora Park tract)
    OPEN = 1903.37      # opened 16 May 1903 (Oakland LocalWiki; Wikipedia gives 1903 / "constructed in 1904")
    CLOSE = 1929.05     # closed January 1929 (Wikipedia; LocalWiki: after the 1928 season)
    RAZED = 1929.6      # torn down 1929 (both); tract houses on the Oct 1931 Sanborn sheet
    for g in d["ground"]:
        outer = Polygon(g["outer"])
        geom_ = outer.difference(Polygon(g["inner"])) if g["inner"] else outer
        surf = {"park": "amusement park", "dirt_track": "ride track", "parking": "amphitheatre platform"}[g["cover"]]
        S.part(geom_, g["cover"], OPEN, RAZED, "exact" if g["cover"] == "park" else "estimated",
               f"{g['name']}: {g['note']}; 1911 Sanborn sheet 293 fitted to today's block (affine, residuals "
               f"{max(d['fit_residual_m']):.1f} m); park opened 16 May 1903, closed Jan 1929, razed 1929",
               surface=surf, name=f"Idora Park: {g['name']}", src=SB)
    for b in d["buildings"]:
        g = poly(b["coords"], b.get("holes"))
        if g.area < 10:
            continue
        S.bldg(g, b["name"], OPEN, RAZED, b["height_m"], b["storeys"], b["material"], b["use"], "estimated",
               f"{'blue (concrete)' if b['colour'] == 'blue' else 'yellow (frame)'} building of the 1911 Sanborn sheet 293, "
               f"{b['area_m2']:.0f} m2; start = opening (the sheet shows the 1911 layout; buildings may be later), end = "
               "razing 1929; height from the storey marks, ESTIMATE"
               + ("; open-air skating floor inside (uncoloured on the sheet)" if b.get("holes") else ""), src=SB)
    for r in d["rides"]:
        g = poly(r["coords"], r.get("holes"))
        S.bldg(g, f"Idora Park {r['name']}", OPEN, RAZED, r["height_m"], 1, "wood frame", "other", "estimated",
               f"{r['note']}; start = opening (ESTIMATE: Idora had five coasters over its life)", src=SB)


# =====================================================================================
# Alameda west-end bath resorts (1878-1953) and Neptune Beach (1916-1940)
# =====================================================================================
ALA_CX, ALA_CY = -122.2800, 37.7700
AP1 = "https://alamedapost.com/history/west-end-once-served-as-magnet-for-bathers-part-1/"
AP2 = "https://alamedapost.com/history/west-end-once-served-as-magnet-for-bathers-part-2/"
AP_NB = "https://alamedapost.com/history/neptune-beach-the-coney-island-of-the-west/"
SB97 = LOC + "sanborn00374_001/"           # Alameda 1897
SB48 = LOC + "sanborn00374_002/"           # Alameda 1948 edition (new report)

# per resort: (name, start, end, conf, dating note, source)
RESORTS = {
    "sandy_beach_baths": ("Sandy Beach Baths", 1878.5, 1922.0, "estimated",
                          "opened c.1878 by Robert Cook near the Second Ave (Fifth St) station (Alameda Post); on the 1897 Sanborn, "
                          "not on the 1948 edition -> end = midpoint (ESTIMATE)", AP1),
    "alameda_baths": ("Alameda Baths", 1878.5, 1922.0, "estimated",
                      "on the 1897 Sanborn (start c.1878 with the other West End baths, ESTIMATE), not on the 1948 edition -> end = "
                      "midpoint (ESTIMATE)", SB97),
    "sunny_cove_baths": ("Sunny Cove Baths", 1878.5, 1950.5, "estimated",
                         "opened 1878 by G. W. Trover beside the Fifth Street station, operated until 1950 (site of the Marina View "
                         "apartments) (Alameda Post); 1897 buildings until the rebuilding seen on the 1948 Sanborn (midpoint 1922, "
                         "ESTIMATE)", AP1),
    "green_arbor_baths": ("Green Arbor Baths", 1878.5, 1900.0, "estimated",
                          "opened c.1878 by John T. Gilman, vanished by 1900 (Alameda Post); outlines from the 1897 Sanborn", AP1),
    "cottage_baths": ("Cottage Baths", 1895.5, 1953.0, "estimated",
                      "opened 1895 by William S. Schmidt (Alameda Post); 1897 Sanborn (tub baths) and 1948 Sanborn (swimming tank); "
                      "gone on the USGS Oakland West 1959 sheet (1958 photos) -> end = midpoint 1953 (ESTIMATE)", AP1),
    "terrace_baths": ("The Terrace Baths", 1878.5, 1916.3, "estimated",
                      "opened 1878 by Robert Haley on the SE corner of Central and Third Ave (Sixth St); managed by L. W. Shroeder in "
                      "1897-98 (Alameda Post); outlines from the 1897 Sanborn; end ESTIMATED at the building of New Surf Beach / "
                      "Neptune Beach next door (1916; the 1948 Sanborn shows Neptune Court on the site)", AP1),
    "neptune_gardens": ("Neptune Gardens (Long Branch Baths site)", 1880.4, 1916.3, "estimated",
                        "Aux Bon Vivants restaurant from May 1880 (12-room house, summer houses, windmill), Long Branch Baths; bought by "
                        "the railroad (James Fair) and reopened as Neptune Gardens 28 Jun 1885 with a $60,000 pavilion; 'formerly "
                        "Neptune Garden, pavilion not used' on the 1897 Sanborn; site rebuilt as New Surf Beach (opened 7 May 1916) "
                        "(Alameda Post)", AP2),
}


def alameda_baths():
    d = J("alameda_baths_sanborn.json")
    sites = {}
    for sid, (name, y0, y1, conf, note, src) in RESORTS.items():
        sites[sid] = Site(sid, name, "resort", d["cx"], d["cy"], src)
    sheet_src = {"1897": SB97, "1948": SB48}
    for b in d["buildings"]:
        sid = b["site_id"]
        if sid not in RESORTS:
            continue
        name, y0, y1, conf, note, src = RESORTS[sid]
        yr = int(b["sheet"][:4])
        s0, s1 = y0, y1
        if sid == "sunny_cove_baths":
            s0, s1 = (y0, 1922.0) if yr == 1897 else (1922.0, y1)
        if sid == "cottage_baths":
            s0, s1 = (y0, 1922.0) if yr == 1897 else (1922.0, y1)
        if sid == "neptune_gardens" and "pavilion" in b["name"]:
            s0, s1 = 1885.49, 1914.5
        g = poly(b["coords"], b.get("holes"))
        if g.area < 6:
            continue
        mat = "wood frame"
        sites[sid].bldg(g, b["name"], s0, s1, b["height_m"], b["storeys"], mat, b["use"], conf,
                        f"footprint from the {yr} Sanborn map of Alameda (sheet {int(b['sheet'][5:])}), fitted to today's block "
                        f"north of Central Ave (affine, residual <= 0.9 m; south of Central the fit is extrapolated, +-5 m); {note}"
                        + ("; pavilion for dancing, roller skating and theatre, built 1885, the 'Wigwam' hall demolished 1914 "
                           "(identification ESTIMATE)" if "pavilion" in b["name"] else "")
                        + ("; dates by edition: 1897 layout until 1922, 1948 layout 1922 on (ESTIMATE)" if sid in ("sunny_cove_baths", "cottage_baths") else ""),
                        src=sheet_src[b["sheet"][:4]])
    for w in d["water"]:
        sid = w["site_id"]
        name, y0, y1, conf, note, src = RESORTS[sid]
        yr = int(w["sheet"][:4])
        s0, s1 = y0, y1
        if sid in ("sunny_cove_baths", "cottage_baths") and yr == 1948:
            s0 = 1922.0
        sites[sid].part(poly(w["coords"]), "water", s0, s1, conf,
                        f"{w['name']}: hand-traced on the {yr} Sanborn map (sheet {int(w['sheet'][5:])}); {note}",
                        surface="swimming tank", name=w["name"], src=sheet_src[w["sheet"][:4]])
    # Neptune Gardens grounds: the old Long Branch Baths land between the Terrace Baths and Webster St (1897 sheet)
    NG = sites["neptune_gardens"]
    shore97 = [(140, 90), (190, 92), (240, 90), (290, 82), (335, 70), (360, 55)]   # 1897 shoreline (sheet 15), local m
    grounds = poly([(140, 150), (345, 148)] + shore97[::-1][1:] + [(140, 90)])
    NG.part(grounds, "park", 1880.4, 1916.3, "estimated",
            "Neptune Gardens / Long Branch grounds (lawns, summer houses, pavilion) between the Terrace Baths and Webster St, "
            "Central Ave to the 1897 shoreline (Sanborn 1897 sheet 15; outline approximate)", surface="pleasure garden", src=SB97)
    neptune_beach()


def neptune_beach():
    """Neptune Beach (New Surf Beach 7 May 1916, Neptune Beach 31 Mar 1917 - closed 1939, auctioned 25 Mar 1940,
    demolished by Nov 1940). No Sanborn sheet shows the park (the 1897 edition predates it; the 1948 edition shows the
    site as 'U.S. Govt. occupied'). Ground = the land on the USGS Oakland West 1:24k sheet of 1949 (1946 photos), which
    is the park's fill (the Maritime Service station took it over in 1942); features PLACED from the 1930s aerial
    photograph (Alameda Museum, via Alameda Post) and the c.1930 aerial (EBRPD Crab Cove tour): ESTIMATE, +-20 m."""
    S = Site("neptune_beach", "Neptune Beach", "amusement_park", ALA_CX, ALA_CY, "https://en.wikipedia.org/wiki/Neptune_Beach_(California)")
    T49 = TOPO + "CA_Oakland%20West_293623_1949_24000_geo.tif"
    PH = "https://alamedapost.com/history/neptune-beach-the-coney-island-of-the-west/ (1930s aerial, Alameda Museum)"
    OPEN, NB, CLOSE, GONE = 1916.35, 1917.25, 1939.75, 1940.9
    LATE = 1925.0      # second pool, stadium, 'Whoopee' coaster: after the 1922 buyout, absent on the early-1920s aerial
    land = poly([(-45, 148), (-25, 110), (0, 60), (10, 0), (10, -100), (15, -200), (20, -300), (-15, -380), (200, -170),
                 (300, -190), (365, -222), (365, 148)])
    court = poly([(46, 148), (140, 148), (140, 95), (46, 95)])          # Neptune Court bungalows + garages (Sanborn 1948)
    grounds = land.difference(court)
    S.part(grounds, "park", OPEN, GONE, "estimated",
           "Neptune Beach grounds: Central Ave to the shoreline / breakwater of the USGS Oakland West 1949 sheet (1946 photos: "
           "the fill the resort built, taken over by the U.S. Maritime Service training station in 1942), from the shore west "
           "of McKay Ave to the fence line east of Webster St; '125 acres' when sold in 1939 (incl. tidelands); outline ESTIMATE",
           surface="amusement park", src=T49)
    # features placed from the aerial photographs (ESTIMATE)
    oval = geom.stadium(62, -60, 0, 38, 40, step=3)
    S.part(ring(oval, geom.stadium(62, -60, 0, 38, 30, step=3)), "dirt_track", LATE, GONE, "estimated",
           "Neptune Beach stadium track (8,000-seat stadium with a track, Alameda Post): oval west of McKay Ave, long axis N-S, "
           "PLACED from the 1930s aerial photograph (size and position ESTIMATE)", surface="stadium track", src=PH)
    S.part(geom.stadium(62, -60, 0, 38, 30, step=3), "grass", LATE, GONE, "estimated", "stadium infield (ESTIMATE)",
           surface="infield", src=PH)
    pool = poly([(165, 12), (268, 12), (268, 52), (165, 52)])
    S.part(pool, "water", LATE, GONE, "estimated",
           "large swimming pool on fill with fountain and diving platforms (the second, 'Olympic-size' pool), east of the "
           "coaster, long axis parallel to Central Ave: PLACED from the 1930s aerial photograph, ~100 x 40 m (ESTIMATE)",
           surface="swimming pool", src=PH)
    pool1 = Point(285, 52).buffer(1).union(poly([(270, 42), (300, 42), (300, 64), (270, 64)])).buffer(4).buffer(-4)
    S.part(pool1, "water", NB, GONE, "estimated",
           "first (smaller) swimming pool at the east end of the large pool, PLACED from the 1930s aerial photograph (ESTIMATE)",
           surface="swimming pool", src=PH)
    lawn = land.intersection(poly([(140, 8), (365, 8), (365, -230), (140, -230), (60, -150)])).difference(pool)
    S.part(lawn, "grass", NB, GONE, "estimated",
           "lawns and picnic grounds (barbecue pits) with walks between the pools and the seawall / promenade, from the 1930s "
           "aerial photograph (ESTIMATE)", surface="picnic lawns", src=PH)
    # buildings / structures
    S.bldg(poly([(160, 62), (268, 62), (268, 90), (160, 90)]), "Neptune Beach bathhouse (dressing rooms)", NB, GONE, 8.0, 2,
           "wood frame", "hall", "estimated", "long two-storey bathhouse between Central Ave and the pools (1930s aerial; PLACED, "
           "ESTIMATE)", src=PH)
    S.bldg(poly([(128, 122), (165, 122), (165, 147), (128, 147)]), "Neptune Beach arcade entrance (Central Ave at McKay Ave)",
           NB, GONE, 9.0, 2, "wood frame", "hall", "estimated",
           "Moorish-arched entrance building at the foot of the coaster on Central Ave (1930s aerial; PLACED, ESTIMATE)", src=PH)
    S.bldg(poly([(255, 128), (265, 128), (265, 138), (255, 138)]), "Neptune Beach Moorish entrance tower", NB, GONE, 30.0, 1,
           "wood frame", "other", "estimated",
           "Moorish-style entrance tower on Webster St (Arcadia 'Alameda'; Alameda Post); height ~30 m read from the 1930s aerial "
           "(about four times the two-storey buildings), PLACED, ESTIMATE", src=PH)
    coaster = path_poly([(150, 140), (148, 60), (143, 0), (138, -45), (130, -80)], 22)
    S.bldg(coaster, "Neptune Beach roller coaster (the 1915 PPIE Scenic Railway, rebuilt)", OPEN, GONE, 16.0, 1, "wood frame",
           "other", "estimated",
           "the Panama-Pacific Exposition's coaster, barged over and rebuilt as a twisting helix; 'New Surf Beach' opened with it "
           "on 7 May 1916; McKay Avenue was laid on its footprint after the 1940 demolition (Alameda Post); width 22 m and height "
           "ESTIMATED from the 1930s aerial", src=AP2)
    whoopee = path_poly([(14, 70), (14, -60), (16, -180), (18, -250)], 12)
    S.bldg(whoopee, "Neptune Beach 'Whoopee' roller coaster", LATE, GONE, 22.0, 1, "wood frame", "other", "estimated",
           "big out-and-back coaster (the 'Whoopee', designed by John Miller) along the west edge of the fill beyond the stadium, "
           "PLACED from the 1930s aerial photograph; length / height ESTIMATE", src=PH)
    stand = path_poly([(109, -100), (109, -20)], 12)
    S.bldg(stand, "Neptune Beach stadium grandstand", LATE, GONE, 10.0, 1, "wood frame", "grandstand", "estimated",
           "covered grandstand along the east side of the stadium oval (1930s aerial; 8,000-seat stadium per Alameda Post); "
           "PLACED, ESTIMATE", src=PH)


# =====================================================================================
# Emeryville: New California Jockey Club track buildings (1896-1915), Shell Mound Park (1877-1924),
# Oaks Park (1913-1957)
# =====================================================================================
SB11_3 = LOC + "sanborn00727_007/"     # Oakland 1911-12 vol. 3 (1911), 'including Emeryville', sheets 323-325
SB50_3 = LOC + "sanborn00727_017/"     # Oakland 1911-Oct 1950 vol. 3, sheet 317
EHS_SMP = "https://emeryvillehistorical.org/centennial-essays/shell-mound-park/"
EHS_TRK = "https://emeryvillehistorical.org/centennial-essays/oakland-trotting-park/"


def emeryville():
    d = J("emeryville_sanborn_1911.json")
    R = Site("emeryville_racetrack", "Emeryville race track (Oakland Trotting Park / New California Jockey Club)", "racetrack",
             d["cx"], d["cy"], EHS_TRK)
    M = Site("shell_mound_park", "Shell Mound Park", "amusement_park", d["cx"], d["cy"], EHS_SMP)
    fit = (f"1911 Sanborn sheets 323-325 (sheet 325 fitted to today's Park Ave crossings, residuals <= 2.1 m; 324 joined to 325 by "
           f"the covered walk drawn on both, 323 to 324 by two hydrants: +-5 m on 324, +-15 m on 323)")
    for b in d["buildings"]:
        g = poly(b["coords"], b.get("holes"))
        if g.area < 8:
            continue
        if b["site"] == "ncjc":
            R.bldg(g, b["name"], 1896.81, 1915.96, b["height_m"], b["storeys"], "wood frame", b["use"], "estimated",
                   f"{fit}, sheet {int(b['sheet'])}; track rebuilt and reopened by the New California Jockey Club 24 Oct 1896 (start; "
                   "some stables may be older), 'closed for racing May 1911', remaining buildings burned 15 Dec 1915 (Emeryville "
                   "Historical Society); height ESTIMATED from the storey marks", src=SB11_3)
        else:
            y0 = 1901.3 if "dance pavilion (with stage)" in b["name"] else 1877.2
            M.bldg(g, b["name"], y0, 1924.5, b["height_m"], b["storeys"], "wood frame", b["use"], "estimated",
                   f"{fit}, sheet {int(b['sheet'])}; Shell Mound Park: Edward Wiard's octagonal dance pavilion on the mound (90 ft "
                   "across, 40 ft to the roof peak) opened for the 1877 picnic season; the ground-level pavilion burned 26 Feb "
                   "1901 and was rebuilt (start 1901 for it); park closed 1924, land sold for factories (EHS; Oakland Tribune 7 Aug "
                   "1949); other start years = 1877 (ESTIMATE); height ESTIMATED", src=SB11_3)
    for g in d["ground"]:
        M.part(poly(g["coords"]), "park", 1877.2, 1924.5, "estimated",
               f"{g['name']}: {fit}; outline approximate (fence lines of the sheets)", surface="pleasure ground",
               name=f"Shell Mound Park: {g['name']}", src=SB11_3)
    o = J("oaks_park_sanborn.json")
    O = Site("oaks_park", "Oaks Park (Emeryville ball park)", "ballpark", o["cx"], o["cy"],
             "https://en.wikipedia.org/wiki/List_of_baseball_parks_in_Oakland,_California")
    OPEN, LAST, GONE = 1913.3, 1955.75, 1957.5     # opened 1913 ('from plans Feb. 1913'); Oaks left after 1955; demolished 1957 (ESTIMATE)
    note = (f"Sanborn Oakland 1911-Oct 1950 vol. 3 sheet 317, 'Oakland Base Ball Association grounds, from plans Feb. 1913', "
            f"fitted to four street crossings (affine, residual {max(o['fit_residual_m']):.1f} m); home of the Oakland Oaks (PCL) "
            "1913-1955; demolished c.1957 (year ESTIMATE); site now Pixar")
    for p in o["parts"]:
        g = poly(p["coords"])
        if p["kind"] == "grounds":
            O.part(g, "grass", OPEN, GONE, "estimated", f"{p['name']}: playing field; {note}", surface="ball field", name=p["name"], src=SB50_3)
        else:
            O.bldg(g, p["name"], OPEN, GONE, p["height_m"], 1 if p["kind"] == "bleachers" else 2, "wood frame", "grandstand", "estimated",
                   f"{note}; outline hand-traced, height ESTIMATE", src=SB50_3)


# =====================================================================================
# Downtown Oakland: the Trans Pacific Centre blocks (9th - 11th St, Broadway - Webster), cleared 1978-82
# (data/manual/redevelopment_areas.csv rows oak_trans_pacific_*, oak_chinatown_franklin_webster_9th_11th)
# =====================================================================================
def oakland_trans_pacific():
    S = Site("oakland_trans_pacific_lots", "Trans Pacific Centre site (redevelopment land, 9th - 11th St)", "redevelopment_lot",
             -122.2722, 37.8015, "https://ceqanet.lci.ca.gov/1981120809")
    B9, B10, B11 = (-122.2733460, 37.8008799), (-122.2729201, 37.8015670), (-122.2724916, 37.8022601)
    F9, F10, F11 = (-122.2721278, 37.8004082), (-122.2717001, 37.8010914), (-122.2712690, 37.8017802)
    W9, W11 = (-122.2709537, 37.7999454), (-122.2700900, 37.8013174)
    blk = lambda pts: S.loc(Polygon(pts)).buffer(-8, join_style=2)      # centreline ring -> block (half street widths)
    ev = ("1950 Sanborn (vol. 2 sheets 150/151): fully built; USGS Oakland West photorevision 1980 (1979 photos): the 10th-11th St "
          "block untinted (cleared after the T & D Theatre was razed in 1978), the others still built up; Trans Pacific Center phase II "
          "Draft EIR (Feb 1982): 'three of a four-block square site'. Surface use while vacant ESTIMATED as parking (in 2000 the "
          "redevelopment agency bought back 135 public parking spaces when it sold the Franklin St lot, GlobeSt 30 Aug 2000)")
    for pts, y0, y1, label in [([B10, B11, F11, F10], 1978.9, 1981.5, "10th-11th St block (Trans Pacific Centre phase I, 1982)"),
                               ([B9, B10, F10, F9], 1982.0, 2001.0, "9th-10th St block (Courtyard by Marriott 2002, Franklin 88 2004)"),
                               ([F9, F11, W11, W9], 1982.0, 1990.0, "Franklin-Webster double block (EBMUD 1991, Pacific Renaissance Plaza 1993)")]:
        g = blk(pts)
        S.part(g, "parking", y0, y1, "estimated", f"{label}: cleared redevelopment land, vacant / surface parking; {ev}; end = start of "
               "the buildings standing there today (ESTIMATE)", surface="vacant lot / surface parking", name=f"Trans Pacific Centre site: {label}")
        S.part(g, "urban", y1, 9999, "estimated", f"{label}: city ground again from the construction of today's buildings", surface="city block",
               name=f"Trans Pacific Centre site: {label}")


def build():
    idora_park()
    alameda_baths()
    emeryville()
    oakland_trans_pacific()
