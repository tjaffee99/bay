"""Airfields of the 2026-11 map extension (Sonoma, Napa, Solano, Santa Cruz, east Contra Costa, south Santa Clara).

  python -I newarea.py            (idempotent: replaces only its own airports / rows)

Writes
* ../../airports_extra.geojson + ../../airports_extra_outlines.geojson: the vanished airfields in FIELDS
  (runway / taxiway / apron polygons with their own start_year / end_year, and the airfield outline);
* ../../../tables/airports.csv: one row per vanished airfield (name = the outline's name) + the four airports
  that were still at the pipeline default (UNDATED);
* ../pavement_dates.csv: rows for Travis AFB, Napa County, Sonoma County (STS) and Watsonville - runway pieces by
  the first USGS edition that draws them (pipeline/airports.py `dated_pavement` matches on overture_id).
  build.py rewrites pavement_dates.csv for SFO / OAK / SJC only: run newarea.py after it.

How the geometry was read: USGS historical topographic sheets (TNM HTMC GeoTIFFs), resampled into a north-up
local metre frame around each field's centre `c` (x east, y north; ../../vanished_sites/tools/vt.py, sheet
registration + NADCON), 0.6-3.4 m per pixel, coordinates read off a 50-250 m grid (about +-5 m on the zooms,
+-12 m where the note says "coarse"). `S` names the sheets. Dates: P. Freeman, Abandoned & Little-Known
Airfields (airfields-freeman.com, quoting sectional charts, airport directories and Campbell & Campbell,
"Two Hours by Crow"), plus the map editions. Widths of unpaved strips are ESTIMATED (map symbols).
"""
from __future__ import annotations

import csv
import io
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANUAL = HERE.parents[1]
REPO = HERE.parents[3]
TABLES = REPO / "data" / "tables"
FR = "https://www.airfields-freeman.com/CA/Airfields_CA_"
TNM = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/"


def tnm(name):
    return TNM + name.replace(" ", "%20") + "_geo.tif"


def kfac(cy):
    return 111320 * math.cos(math.radians(cy))


def px(pts, res, half):
    """Pixel positions on a render (res m / px, frame half-size) -> local metres."""
    return [(-half + x * res, half - y * res) for x, y in pts]


# ---------------------------------------------------------------------------------------------- vanished fields
# piece: kind, start, end, then either a / b / w (centre line + width) or line (polyline) + w, or poly (ring)
def P(kind, start, end, note, a=None, b=None, w=None, line=None, poly=None, conf="estimated"):
    return dict(kind=kind, start=start, end=end, note=note, a=a, b=b, w=w, line=line, poly=poly, conf=conf)


FIELDS = [
    dict(
        name="Santa Rosa Naval Auxiliary Air Station", cls="military_airport", c=(-122.7545, 38.4125),
        opened=1943, closed=1991, src=FR + "SantaRosa_N.htm",
        S="USGS 1:24,000 Sebastopol + Santa Rosa 1954 (1952 photos): CA_Sebastopol_300394_1954_24000, CA_Santa Rosa_300294_1954_24000",
        csv_note="NAAS Santa Rosa (southwest of the city, between Wright Rd, Finley Ave and Ludwig Ave): construction from "
                 "Nov 1942, '7,000-ft hard-surface runway' in the 1944 Army / Navy directory, '2 concrete 7,000-ft runways, "
                 "north / south and east / west' in the 1945 AAF directory; Navy OLF to 1947 and again 1951-52 (Korea), "
                 "abandoned on the 1961 / 1966 charts, civil Santa Rosa Air Center (O01) from 1966-67, closed 1991 (Freeman). "
                 "Not in Overture: runways, ramp, taxiways and outline traced from the USGS Sebastopol / Santa Rosa 1:24,000 "
                 "sheets of 1954 (1952 photos, 'Naval Auxiliary Air Station (Inactive)') in data/manual/airports_extra*.geojson "
                 "(tools/newarea.py); the north half of the N-S runway, the west end of the E-W runway and the ramp still exist",
        pieces=[
            P("runway", 1943, 9999, "N-S runway, north part (still there: Esri World Imagery, viewed only): axis and ends from "
              "the 1954 sheet, checked on the orthophoto (tilt 2.8 deg, 61-70 m of concrete: the sheet draws the 125 m graded "
              "strip) - 200 ft wide", a=(-233.4, 1195), b=(-274.7, 345), w=61, conf="documented"),
            P("runway", 1943, 2006, "N-S runway, south part to the turnaround at Ludwig Ave (7,000 ft with the north part): "
              "houses on its north end by 2007 ('housing developers are gradually filling in the northern portion of that "
              "runway', Freeman 2007), the rest a strip of rubble today - end ESTIMATED", a=(-274.7, 345), b=(-335.4, -905), w=61),
            P("runway", 1943, 9999, "E-W runway, west end (still there, 66 m of concrete on the orthophoto)",
              a=(-1070, 173), b=(-633, 206.3), w=61, conf="documented"),
            P("runway", 1943, 2000, "E-W runway east of the stub: 2,350 m on the 1954 sheets (east end +-50 m under the "
              "sheet lettering); business park and houses since - 'a remaining portion ... reused as a parking lot' in "
              "2003 (Freeman); end ESTIMATED", a=(-633, 206.3), b=(1276, 352), w=61),
            P("apron", 1943, 9999, "concrete ramp north-west of the runway crossing (sheet + orthophoto, still there)",
              poly=px([(285, 560), (350, 470), (400, 500), (530, 375), (556, 395), (470, 505), (415, 610), (380, 640),
                       (275, 650), (270, 600)], 1.9, 1450)),
            P("taxiway", 1943, 9999, "taxiway parallel to the N-S runway (west side) and its link to the north turnaround "
              "(orthophoto, still there)", line=[(-355, 350), (-327, 960), (-317, 978), (-263, 1075)], w=20),
            P("taxiway", 1943, 9999, "ramp - parallel taxiway link (orthophoto)", line=[(-447, 715), (-350, 735)], w=20),
            P("taxiway", 1943, 9999, "taxiway from the ramp south-east to the runway crossing (orthophoto, still there)",
              line=[(-600, 500), (-400, 355), (-310, 335)], w=23),
        ],
        outline=px([(240, 330), (560, 300), (560, 200), (620, 125), (670, 125), (712, 180), (730, 410), (850, 410),
                    (855, 550), (1435, 515), (1440, 645), (940, 655), (940, 930), (665, 950), (690, 1280), (540, 1280),
                    (530, 860), (320, 735), (120, 725), (110, 690), (190, 640), (240, 540)], 1.9, 1450)),
    dict(
        name="Cotati Naval Outlying Landing Field", cls="military_airport", c=(-122.7222, 38.3489),
        opened=1942, closed=1946, src=FR + "SantaRosa_S.htm",
        S="USGS 1:24,000 Cotati 1954 (1952 photos): CA_Cotati_289550_1954_24000; 1968 and 1980 photorevisions",
        csv_note="NOLF Cotati (today's Rohnert Park, west of US-101 at the Expressway): built 1941-43 as an auxiliary air "
                 "station (airfield on a 1942 aerial, on the Aug 1943 chart; '3,900-ft runway' 1944, field carrier landing "
                 "practice on Runways 7/25 and 13/31), 'the field was closed in 1946' (Campbell via Freeman). The runways "
                 "were a road-racing circuit and drag strip 1957-72 (Cotati Raceway) and were built over from 1973 "
                 "(Rohnert Park Expressway 1971-73, mobile home park by 1977, shopping centres 1986). Runways traced from "
                 "the USGS Cotati 1:24,000 sheet of 1954 (1952 photos, 'Cotati Naval Auxiliary Air Station (Inactive)'; "
                 "still on the 1968 photorevision, gone on the 1980 one) with their own years (end 1973) in "
                 "data/manual/airports_extra.geojson; the airfield outline closes 1946",
        pieces=[
            P("runway", 1942, 1973, "Runway 7/25: 1,190 m (3,900 ft) on the 1954 sheet, which draws a 125 m strip with a "
              "44 m inner outline - width ESTIMATED 46 m (150 ft); race track 1957-72, end = Expressway / first buildings",
              a=(-734, 60.8), b=(454, 60.8), w=46),
            P("runway", 1942, 1973, "Runway 13/31: 1,120 m on the 1954 sheet (axis fitted through both arms, +-15 m); "
              "width ESTIMATED 46 m", a=(-497.5, 604), b=(80, -360.5), w=46),
            P("taxiway", 1942, 1973, "third leg of the triangle (east end of 7/25 to the south end of 13/31, 600 m), "
              "narrower on the sheet - taken as a taxiway, width ESTIMATED", a=(437.5, 118), b=(102, -382.5), w=30),
        ], margin=70),
    dict(
        name="Santa Cruz Sky Park", cls="airport", c=(-122.0317, 37.0513),
        opened=1947, closed=1983, src=FR + "Monterey.htm",
        S="USGS 1:24,000 Felton 1955 (1953 photos) CA_Felton_290498_1955_24000; 1980 photorevision CA_Felton_290496_1955_24000; "
          "1991 CA_Felton_290497_1991_24000 ('Landing Strip (Abandoned)')",
        csv_note="Scotts Valley: 'Sky Park Airport began operation in 1947 as a privately-owned field built by Jack & Lola "
                 "Graham' (county airport chronology via Freeman), 2,100-ft runway; city of Santa Cruz airport after "
                 "Capitola closed (1954); realigned, longer runway built c.1968 ('the 1968 USGS topo map depicted the "
                 "original runway ... along with the realigned runway which replaced it'); 'Skypark closed in January 1983'. "
                 "Traced from the USGS Felton 1:24,000 sheets (1953 photos; 1980 photorevision; 1991 'Landing Strip "
                 "(Abandoned)') in data/manual/airports_extra*.geojson",
        pieces=[
            P("runway", 1947, 1968, "original runway, 590 m on the 1955 sheet (1953 photos; coarse, +-12 m)",
              a=(-195, 172), b=(195, -275), w=15),
            P("runway", 1968, 1983, "realigned runway, 745 m on the 1980 photorevision and the 1991 sheet; start = the 1968 "
              "photorevision that shows both (ESTIMATED)", a=(-174, 214), b=(192, -433), w=18),
            P("apron", 1947, 1983, "hangar apron at the north end (1980 photorevision; 6 buildings on the north-east side "
              "in 1953)", poly=[(-149, 252), (-53, 326), (-10, 264), (-103, 196)]),
        ], margin=30),
    dict(
        name="Santa Cruz-Capitola Airport", cls="airport", c=(-121.9403, 36.98155),
        opened=1925, closed=1954, src=FR + "Monterey.htm",
        S="USGS 1:24,000 Soquel 1954 (1952 photos) CA_Soquel_300606_1954_24000 ('Airport'); 1:62,500 Capitola 1940 "
          "(1938 photos, 'Santa Cruz Airport') CA_Capitola_465438_1940_62500",
        csv_note="the bluff between Capitola and New Brighton Beach (today's Cliffwood Heights streets): flying field on a "
                 "1925 aerial (start ESTIMATED from it), Santa Cruz's civil airport from 1934, 'abandoned in September "
                 "1954' when the operators moved to Sky Park (Freeman); streets on the 1968 photorevision. Field outline "
                 "and the two turf runways traced from the USGS Soquel 1:24,000 sheet of 1954 (1952 photos) in "
                 "data/manual/airports_extra*.geojson",
        pieces=[
            P("runway", 1947, 1954, "NE-SW turf runway, 505 m on the 1954 sheet; 'an open grass area' in the 1941 directory "
              "photo, '2 distinct perpendicular unpaved runways not visible in previous photos' on a 1948 aerial -> 1947 "
              "(ESTIMATED); width ESTIMATED", a=(-269, -117), b=(111, 219), w=30),
            P("runway", 1947, 1954, "NW-SE turf runway, 470 m on the 1954 sheet (as above)", a=(-273, 146), b=(43, -201), w=30),
        ],
        outline=px([(250, 470), (560, 470), (640, 350), (930, 330), (1010, 400), (960, 740), (860, 1010), (810, 1070),
                    (700, 1100), (300, 960), (240, 900)], 0.62, 450)),
    dict(
        name="Rio Vista Airport (original)", cls="airport", c=(-121.6892, 38.1701),
        opened=1949, closed=1995, src=FR + "SacramentoSW.htm",
        S="USGS 1:24,000 Rio Vista 1953 (1949 photos, 'Landing Strip') CA_Rio Vista_294705_1953_24000; 1968 photorevision "
          "CA_Rio Vista_294707_1953_24000; 1978 (1974 photos, 'Rio Vista Airport') CA_Rio Vista_294708_1978_24000",
        csv_note="north edge of Rio Vista at St Francis Way / Airport Rd: 'in 1949 crop duster Ira Skip Seiden cut a single "
                 "runway into the dirt just to the north of Rio Vista' (Campbell via Freeman; on the Aug 1948 chart), "
                 "municipal airport 'established in 1953' (1988 county plan), 2,500-ft Runway 7/25 + 1,700-ft 14/32 in the "
                 "1960 Jeppesen manual, replaced by today's airport 2 miles north, built 1993-95 (see Rio Vista Municipal "
                 "Airport). Traced from the USGS Rio Vista 1:24,000 sheets (1949 photos; 1974 photos) in "
                 "data/manual/airports_extra*.geojson; hangars and some pavement remain (not modelled after 1995)",
        pieces=[
            P("runway", 1949, 1995, "Runway 7/25 as on the 1953 sheet (1949 photos, 'Landing Strip', 710 m; ends +-25 m); "
              "width ESTIMATED 18 m", a=(-337, 5.3), b=(322, 27.8), w=18),
            P("runway", 1968, 1995, "west extension of 7/25 (890 m on the 1978 sheet; 'lengthened primary runway' on a "
              "5/2/1968 USDA aerial, not on the 1968 photorevision) - ESTIMATED", a=(-569, -2.7), b=(-337, 5.3), w=18),
            P("runway", 1958, 1995, "Runway 14/32 (495 m on the 1978 sheet; not on the 1949-photo sheet, '1,700-ft Runway "
              "14/32' paved in the 1960 Jeppesen manual) - ESTIMATED", a=(-35, 474.5), b=(164.5, 20), w=12),
            P("apron", 1953, 1995, "ramp south of the runway with the hangar (1978 sheet; municipal airport 1953)",
              poly=[(-33.5, -11.5), (101.5, -16), (101.5, -74.5), (-29, -79)]),
            P("taxiway", 1968, 1995, "parallel taxiway west of the ramp (1978 sheet) - ESTIMATED",
              a=(-195.5, -50), b=(-33.5, -45), w=10),
        ],
        outline=px([(85, 700), (715, 80), (1270, 625), (1100, 830), (835, 830), (690, 815), (500, 815), (265, 800),
                    (195, 820)], 0.9, 650)),
    dict(
        name="Antioch Airport", cls="airport", c=(-121.80, 37.97),
        opened=1946, closed=1989, src=FR + "SacramentoSW.htm",
        S="USGS 1:24,000 Antioch South 1953 (1949 photos, 'Antioch Airport') CA_Antioch South_100045_1953_24000; unchanged on "
          "the 1968, 1973 and 1980 photorevisions",
        csv_note="Lone Tree Way east of Empire Ave (today Deer Valley High School and houses): 'Orville Prevost opened an "
                 "airport in 1946', gravel runway 2,200 ft, 'paved out to 2,480 ft' in 1949, 'the field closed in 1989' "
                 "(Campbell via Freeman; not on the Aug 1946 chart, on the Feb 1947 one). Runway and property outline "
                 "traced from the USGS Antioch South 1:24,000 sheet of 1953 (1949 photos; coarse, +-12 m) in "
                 "data/manual/airports_extra*.geojson",
        pieces=[P("runway", 1946, 1989, "runway, 690 m on the 1953 sheet (coarse); width ESTIMATED",
                  a=(-443, -213), b=(230, -356), w=15)],
        outline=[(-467, -169), (298, -169), (298, -519), (-59, -519), (-42, -325), (-467, -298)]),
    dict(
        name="Petaluma Sky Ranch Airport", cls="airport", c=(-122.6129, 38.2588),
        opened=1949, closed=1985, src=FR + "SantaRosa_S.htm",
        S="USGS 1:24,000 Petaluma River 1954 (1952 photos, 'Petaluma Skyranch Airport') CA_Petaluma River_294073_1954_24000; "
          "1980 photorevision CA_Petaluma River_101767_1954_24000",
        csv_note="East Washington St (today's Sky Ranch Drive houses, directly south-west of the municipal airport): not on "
                 "the Feb 1949 chart, on the Sep 1949 one; Justman Flying Service; 2,100-ft runway, paved later; 'the Sky "
                 "Ranch was dismantled, and Petaluma Municipal Airport opened in 1985' (Freeman) - the FAA activation "
                 "06/1949 of O69 is the Sky Ranch's. Traced from the USGS Petaluma River 1:24,000 sheets (1952 photos; "
                 "1980 photorevision) in data/manual/airports_extra*.geojson. Earlier Petaluma fields (1915 flights; "
                 "Petaluma Airport / Skyways 1946- on the north-west side; Buck / Doolittle, Justman, Oak View) not modelled",
        pieces=[
            P("runway", 1949, 1985, "runway, 610 m (2,000 ft) on both sheets; width ESTIMATED",
              a=(-228, 180), b=(282, -156), w=15),
            P("apron", 1949, 1985, "hangar row and apron on the north-east side (8 hangars on the 1980 photorevision)",
              poly=px([(560, 470), (640, 440), (900, 640), (860, 700)], 0.68, 500)),
        ],
        outline=px([(370, 470), (470, 350), (1050, 750), (1190, 940), (1120, 1030), (1040, 975), (450, 560)], 0.68, 500)),
    dict(
        name="Vallejo Sky Harbor", cls="airport", c=(-122.2569, 38.1554),
        opened=1946, closed=1953, src=FR + "Oakland_N.htm",
        S="USGS 1:24,000 Cuttings Wharf 1949 (1948 photos, 'Vallejo Sky Harbor') CA_Cuttings Wharf_289711_1949_24000",
        csv_note="north Vallejo west of Broadway (SR-29) at today's Meadows Dr: 'established Vallejo Sky Harbor Airport on "
                 "2/9/46', 2,500-ft unpaved runway (1948 chart), 'the field closed in 1953' (Freeman; off the Mar 1953 "
                 "chart; houses on its south-east part on a 1957 aerial). Four strips traced from the USGS Cuttings Wharf "
                 "1:24,000 sheet of 1949 (1948 photos) in data/manual/airports_extra*.geojson. The pre-war Vallejo (Mini) "
                 "Airport 1.5 km south (1929-c.1944, only a boundary symbol on the 1:62,500 sheet) is not modelled",
        pieces=[
            P("runway", 1946, 1953, "main NE-SW runway with its parallel strip (drawn as one 35 m band; 575 m)",
              a=(-242, -254), b=(189, 124.5), w=30),
            P("runway", 1946, 1953, "NW-SE strip, 610 m", a=(-298, 174), b=(120, -272), w=14),
            P("runway", 1946, 1953, "E-W strip, 515 m", a=(-320, -74), b=(189, 10), w=14),
        ], margin=40),
    dict(
        name="Calistoga Airpark", cls="airport", c=(-122.57304, 38.5789),
        opened=1947, closed=1998, src=FR + "SantaRosa_N.htm",
        S="USGS 1:24,000 Calistoga 1958 (1957 photos, 'Landing Strip') CA_Calistoga_288811_1958_24000; 1980 photorevision "
          "CA_Calistoga_288814_1958_24000",
        csv_note="Calistoga Airpark / Gliderport on Lincoln Ave east of the town: not on the Feb 1947 chart, on the Aug "
                 "1947 one, 2,200-ft unpaved runway (1948), paved by 1957; glider field (Calistoga Soaring Center); "
                 "'closed in December 1998 & all flying ceased' (Campbell via Freeman). Runway traced from the USGS "
                 "Calistoga 1:24,000 sheet of 1958 (1957 photos; same on the 1980 photorevision: 665 m - the '2,800-ft' "
                 "of the directories is not drawn) in data/manual/airports_extra*.geojson",
        pieces=[P("runway", 1947, 1998, "runway, 665 m on the 1958 sheet and its 1980 photorevision; width ESTIMATED",
                  a=(-331, 161.5), b=(260, -147.5), w=15)], margin=40),
    dict(
        name="Morgan Hill Airport", cls="airport", c=(-121.6509, 37.148),
        opened=1947, closed=1980, src=FR + "SanJose_E.htm",
        S="USGS 1:24,000 Morgan Hill 1955 (1953 photos, 'Landing Strip') CA_Morgan Hill_293124_1955_24000; 1968 photorevision "
          "('Morgan Hill Airport'); 1973 photorevision ('Landing Field') CA_Morgan Hill_293127_1955_24000",
        csv_note="Cochrane Rd east of US-101 (Morgan Hill Airmen Landing Strip, later Sutter Airfield, Q99): 'Valley "
                 "Airport' with unpaved 1,700-ft runways in the 1947 Haire directory (start ESTIMATED from it; first on "
                 "the Sep 1950 chart), 2,400-ft unpaved runway; abandoned on the 1981 sectional, last photo 1980 (Freeman) "
                 "- end ESTIMATED. Traced from the USGS Morgan Hill 1:24,000 sheets (1953 photos; 1973 photorevision) "
                 "in data/manual/airports_extra*.geojson",
        pieces=[
            P("runway", 1947, 1980, "landing strip of the 1955 sheet (1953 photos; 740 m from Cochrane Rd), on the axis of "
              "the 1973 'Landing Field'; width ESTIMATED", a=(-247.7, 409.7), b=(166.7, -146), w=20),
            P("runway", 1960, 1980, "south-east extension to 840 m of clear field (purple on the 1968 / 1973 "
              "photorevisions) - start ESTIMATED (1953 - 1968)", a=(166.7, -146), b=(360, -405), w=20),
            P("apron", 1960, 1980, "hangar area at Cochrane Rd (1968 / 1973 photorevisions) - start ESTIMATED",
              poly=px([(330, 320), (445, 235), (600, 420), (465, 500)], 0.9, 650)),
        ], margin=30),
    dict(
        name="Watsonville Airport (original)", cls="airport", c=(-121.7767, 36.8647),
        opened=1931, closed=1945, src=FR + "Monterey.htm",
        S="USGS 1:62,500 Capitola 1940 (1938 photos, 'Airport', three runways) CA_Capitola_465438_1940_62500; gone on the "
          "1:24,000 Moss Landing 1954 (1952 photos)",
        csv_note="San Andreas Rd / Salinas Rd junction south-west of Watsonville (Monterey County): 'Watsonville Airport "
                 "Incorporated was formed in 1930', dedicated 1931 (Governor Rolph), three runways on a 1938 aerial; "
                 "'leased by the Navy in 1942' for blimps from Moffett Field (NAAF Watsonville: the runways filled in "
                 "with one asphalt mat and mooring circles on a 1943 aerial); still on the Mar 1945 chart beside the new "
                 "airport, 'Old Airport' on a 1950 road map (Freeman) - end ESTIMATED. Runways traced from the USGS "
                 "Capitola 1:62,500 sheet of 1940 (1938 photos; +-30 m) in data/manual/airports_extra*.geojson; the "
                 "1943 blimp mat is not modelled",
        pieces=[
            P("runway", 1931, 1943, "E-W runway, 715 m on the 1:62,500 sheet (+-30 m); width ESTIMATED",
              a=(-300, -52), b=(416, -40), w=25),
            P("runway", 1931, 1943, "NE-SW runway, 480 m (as above)", a=(-260, -168), b=(-20, 248), w=25),
            P("runway", 1931, 1943, "NW-SE runway, 670 m (as above)", a=(-120, 248), b=(412, -160), w=25),
        ], margin=50),
    dict(
        name="Vaca-Dixon Airport", cls="airport", c=(-121.91, 38.40),
        opened=1947, closed=1993, src=FR + "SacramentoSW.htm",
        S="USGS 1:24,000 Allendale 1953 (1949 photos, 'Vaca Dixon Airport') CA_Allendale_287903_1953_24000; 1973 photorevision "
          "('Airport Abandoned') CA_Allendale_287906_1953_24000",
        csv_note="south-east side of I-80 at Midway Rd / Meridian Rd (next to the Vaca Valley Raceway): 'opening in 1947' "
                 "with dirt runways (Campbell via Freeman; on the Feb 1948 chart), 'Airport Abandoned' on the 1973 "
                 "photorevision but in use again for ultralights and gliders: 'when the gliders moved out on 12/1/93, the "
                 "airport certificate was pulled' ('other sources reported ... closed in 1995'). Two runways traced from "
                 "the USGS Allendale 1:24,000 sheet of 1953 (1949 photos; coarse, +-12 m) in "
                 "data/manual/airports_extra*.geojson",
        pieces=[
            P("runway", 1947, 1993, "Runway 18/36, 650 m on the 1953 sheet (coarse); width ESTIMATED",
              a=(478, 1096), b=(492, 443), w=18),
            P("runway", 1947, 1993, "Runway 3/21, 570 m on the 1953 sheet (coarse); width ESTIMATED",
              a=(553, 1181), b=(383, 637), w=18),
        ], margin=40),
    dict(
        name="Vacaville Gliderport", cls="airport", c=(-122.02, 38.33),
        opened=1957, closed=1991, src=FR + "SacramentoSW.htm",
        S="USGS 1:24,000 Fairfield North 1951, 1968 photorevision ('Vacaville Airport') CA_Fairfield North_290424_1951_24000 and "
          "1980 photorevision ('Landing Strip')",
        csv_note="Lagoon Valley, east side of I-80 at Lagoon Valley Rd (Shady Grove / Vacaville Airport, VCV; not the Nut "
                 "Tree Airport 6 km north-east): not on the 1951 sheet or the Oct 1956 chart, on the 1957 chart, 2,000-ft "
                 "Runway 2/20 paved by 1962, 'the field was closed on 9/25/91' (Campbell via Freeman). Runway traced "
                 "from the USGS Fairfield North 1:24,000 photorevisions of 1968 and 1980 (coarse, +-15 m) in "
                 "data/manual/airports_extra*.geojson",
        pieces=[P("runway", 1957, 1991, "Runway 2/20, 645 m on the 1968 / 1980 photorevisions (coarse); width ESTIMATED",
                  a=(193, -3), b=(-46, -605), w=15)], margin=40),
    dict(
        name="Knights Airport", cls="airport", c=(-122.2675, 38.1293),
        opened=1935, closed=1954, src=FR + "Oakland_N.htm",
        S="USGS 1:24,000 Cuttings Wharf 1949 (1948 photos, 'Knights Airport') CA_Cuttings Wharf_289711_1949_24000; boundary "
          "with airport symbol on the 1:62,500 Mare Island 1942 (1937 survey); gone on the 1968 photorevision",
        csv_note="Vallejo, on the Napa River flat north-west of Sears Point Rd (SR-37) at Sacramento St (Knights Airport / "
                 "Stan's Airpark): a 1935 photo is the earliest record (start ESTIMATED from it; on the May 1936 chart), "
                 "closed during the war (off the charts Aug 1943 - Feb 1946), 2,300-ft unpaved runway in 1948; 'by 1954 "
                 "the runways were deteriorating & the Napa County Airport was a better choice so this field was closed' "
                 "(Campbell via Freeman). Strips traced from the USGS Cuttings Wharf 1:24,000 sheet of 1949 (1948 "
                 "photos) in data/manual/airports_extra*.geojson; the pre-war strips are not mapped (the field is airfield "
                 "grass from 1935, the traced strips from 1946)",
        pieces=[
            P("runway", 1946, 1954, "middle NE-SW runway of the 1948-photo sheet, 470 m; widths as drawn",
              a=px([(450, 1000)], 0.55, 400)[0], b=px([(1035, 378)], 0.55, 400)[0], w=25),
            P("runway", 1946, 1954, "west NE-SW strip from the south-west turnaround, 490 m",
              a=px([(45, 1160)], 0.55, 400)[0], b=px([(605, 475)], 0.55, 400)[0], w=14),
            P("runway", 1946, 1954, "east NE-SW strip along the highway, 410 m",
              a=px([(600, 1170)], 0.55, 400)[0], b=px([(1045, 595)], 0.55, 400)[0], w=20),
            P("taxiway", 1946, 1954, "north strip from the west turnaround and the link along the heads of the runways",
              line=px([(275, 400), (745, 425), (610, 480), (980, 480), (1110, 560)], 0.55, 400)[:2], w=14),
            P("taxiway", 1946, 1954, "link along the north-east heads of the runways to the highway side",
              line=px([(610, 480), (980, 480), (1110, 560)], 0.55, 400), w=14),
            P("taxiway", 1946, 1954, "cross strip at the south-west ends", a=px([(320, 900)], 0.55, 400)[0],
              b=px([(560, 1130)], 0.55, 400)[0], w=20),
        ], margin=25),
    dict(
        name="Benicia Airport", cls="airport", c=(-122.1895, 38.0755),
        opened=1946, closed=1958, src=FR + "Oakland_N.htm",
        S="USGS 1:24,000 Benicia 1950 (1948 photos, 'Benicia Airport', two strips) CA_Benicia_288319_1950_24000; 1959 (1958 photos, still labelled); under I-780 on the 1968 photorevision",
        csv_note="west edge of Benicia between Benicia Rd and the Southampton Bay marsh (Benicia Airport / Air Harbor; "
                 "I-780 runs over it): 'in 1946, when the runway was opened' (Campbell via Freeman; not on the 1946 chart, "
                 "on the 1948 one), 2,400-ft unpaved runway; last on the Sep 1957 chart, off the Apr 1958 one -> closed "
                 "1957-58 (still labelled on the 1958-photo USGS sheet, abandoned on a 1965 aerial). Two strips traced "
                 "from the USGS Benicia 1:24,000 sheet of 1950 (1948 photos) in data/manual/airports_extra*.geojson",
        pieces=[
            P("runway", 1946, 1958, "main strip along the road, 600 m on the 1950 sheet; width as drawn (20-30 m)",
              a=px([(490, 388)], 0.55, 400)[0], b=px([(962, 1378)], 0.55, 400)[0], w=22),
            P("runway", 1946, 1958, "short cross strip into the marsh edge, 240 m",
              a=px([(417, 922)], 0.55, 400)[0], b=px([(800, 1125)], 0.55, 400)[0], w=16),
        ], margin=20),
    dict(
        name="Santa Rosa Coddingtown Airport", cls="airport", c=(-122.74097, 38.475),
        opened=1960, closed=1971, src=FR + "SantaRosa_N.htm",
        S="USGS 1:24,000 Santa Rosa 1954, 1968 photorevision (runway outline in purple) CA_Santa Rosa_300296_1954_24000; "
          "buildings over it on the 1980 photorevision",
        csv_note="north-west Santa Rosa between Piner Rd and Guerneville Rd, west of today's Coddingtown (Santa Rosa "
                 "Metropolitan / Coddingtown Airport): 'built off of Piner Road in 1960' (Sonoma County Historical "
                 "Society via Freeman), dedicated 1960, 3,050-ft paved Runway 16/34 (1967-68); sold 1971 - 'the main "
                 "portion of the field became a parking lot for the buses of the Golden Gate Transit District', 'closed "
                 "by 1972' (a heliport stayed into the 1980s). Runway traced from the 1968 photorevision of the USGS "
                 "Santa Rosa 1:24,000 sheet (920 m) in data/manual/airports_extra*.geojson. The earlier fields on the "
                 "same ground (Santa Rosa Municipal / Steiner Field 1929-, Santa Rosa Airpark c.1953) are not modelled: "
                 "the 1:62,500 sheet of 1944 shows only a boundary, the 1954 sheet nothing",
        pieces=[P("runway", 1960, 1971, "Runway 16/34, 920 m x 22 m on the 1968 photorevision", a=(-6.25, 427.75),
                  b=(-6.25, -494.75), w=22, conf="documented")], margin=25),
]

# airports still at the pipeline default (1950): name (Overture), opened, source, note
UNDATED = [
    ("Capell Valley Airport", 1960, tnm("CA_Capell Valley_288938_1951_24000"),
     "estimated: no strip at Moskowite Corner on the USGS Capell Valley 1:24,000 sheet of 1951 (1948 photos, field "
     "check 1951), 'Landing Strip' in purple on its 1968 photorevision -> midpoint 1960"),
    ("Monterey Bay Academy Airport", 1973, tnm("CA_Watsonville West_301250_1954_24000"),
     "estimated: the academy (1949) is the former Camp McQuaide (California National Guard / Army coast artillery camp, "
     "1938-48); Wikipedia calls the strip 'the former military camp's runway', but no strip is drawn on the USGS "
     "Watsonville West 1:24,000 sheet of 1954 (1952 photos; an abandoned reservoir lies on its line) nor on the 1968 "
     "photorevision; 'Landing Strip' in purple on the 1980 photorevision (1978 photos) -> midpoint 1973. Conflicting "
     "evidence: an earlier Army strip is not ruled out"),
    ("Q Area Heliport", 1980, tnm("CA_Vine Hill_102376_1959_24000"),
     "estimated lower bound: helipad of the Concord Naval Weapons Station (tidal area east of Port Chicago); nothing at "
     "the site on the USGS Port Chicago 1:24,000 sheets (1948, 1958 photos, 1968 photorevision) nor on the Vine Hill "
     "1980 photorevision (1979 photos); no later edition and no document found - after 1979"),
    ("The Sea Ranch Airport", 1968, tnm("CA_Stewarts Point_300674_1978_24000"),
     "estimated: not on the USGS Stewarts Point 1:24,000 sheet of 1943; 'Sea Ranch Airport' with the first streets on "
     "the 1978 edition (1971 photos); The Sea Ranch was laid out from 1964-65 -> midpoint 1968"),
    ("Yolo County Airport", 1942, "https://en.wikipedia.org/wiki/Yolo_County_Airport",
     "estimated: 'built by the United States Army Air Forces and the United States Army Corps of Engineers about 1942 "
     "with a 6000 by 150 foot asphalt-concrete north-south runway, and was known as Winters-Davis Flight Strip' "
     "(Wikipedia); lies in the faded band just outside the map line"),
]


# ---------------------------------------------------------------------------------------------- geometry
def local_geom(f):
    import shapely
    from shapely.geometry import LineString, Polygon
    out = []
    for p in f["pieces"]:
        if p["poly"]:
            g = Polygon(p["poly"]).buffer(0)
        elif p["line"]:
            g = LineString(p["line"]).buffer(p["w"] / 2, cap_style="flat", join_style="mitre")
        else:
            g = LineString([p["a"], p["b"]]).buffer(p["w"] / 2, cap_style="flat")
        out.append(g)
    if f.get("outline"):
        o = Polygon(f["outline"]).buffer(0)
        o = shapely.union_all([o] + [g.buffer(8) for g in out]).buffer(0)
    else:
        o = shapely.union_all(out).convex_hull.buffer(f.get("margin", 40), join_style="mitre")
    return out, o


def to_ll(g, c):
    import numpy as np
    import shapely
    k = kfac(c[1])
    return shapely.set_precision(shapely.transform(g, lambda xy: np.c_[c[0] + xy[:, 0] / k, c[1] + xy[:, 1] / 110574]), 1e-7)


def overture():
    import geopandas as gpd
    import pandas as pd
    sys.path.insert(0, str(REPO / "pipeline"))
    from common import RAW
    from download_overture import RELEASE
    d = pd.read_parquet(RAW / "overture" / RELEASE / "region_airports.parquet")
    return gpd.GeoDataFrame(d, geometry=gpd.GeoSeries.from_wkb(d.geometry), crs=4326)


AIRPORT_CLASSES = ["airport", "international_airport", "military_airport", "municipal_airport", "private_airport"]


def write_fields(g):
    import shapely
    from shapely.geometry import mapping
    names = {f["name"] for f in FIELDS}
    ef, eo = MANUAL / "airports_extra.geojson", MANUAL / "airports_extra_outlines.geojson"
    d = json.loads(ef.read_text())
    o = json.loads(eo.read_text())
    d["features"] = [x for x in d["features"] if x["properties"].get("airport") not in names]
    o["features"] = [x for x in o["features"] if x["properties"].get("name") not in names]
    today = g[g["class"].isin(AIRPORT_CLASSES) & (g.geom_type == "Polygon")]
    qa = []
    for f in FIELDS:
        geoms, outline = local_geom(f)
        ol = to_ll(outline, f["c"])
        # never overlap a standing airport's outline of another name (Petaluma Sky Ranch / Petaluma Municipal)
        k = kfac(f["c"][1]) * 110574
        full = ol.area
        for nm, tg in zip(today.name, today.geometry):
            if tg.intersects(ol):
                a0 = ol.intersection(tg).area * k / 1e4
                ol = ol.difference(tg.buffer(0.0001))
                if ol.geom_type == "MultiPolygon":
                    ol = max(ol.geoms, key=lambda q: q.area)
                print(f"  {f['name']}: outline clipped by {nm} ({a0:.1f} ha overlap)")
        # a field that lies inside today's airport of another name (Petaluma Sky Ranch inside the municipal
        # airport's boundary) gets no outline of its own: its pieces keep their years, the ground is today's airport's
        has_outline = (not ol.is_empty) and ol.area > 0.3 * full
        for p, gm in zip(f["pieces"], geoms):
            props = {"airport": f["name"], "kind": p["kind"], "start_year": p["start"], "end_year": p["end"],
                     "width_m": p["w"], "confidence": p["conf"], "source_url": f["src"],
                     "note": p["note"] + ". " + f["S"]}
            ft = {"type": "Feature", "properties": props, "geometry": mapping(to_ll(gm, f["c"]))}
            d["features"].append(ft); qa.append(ft)
        op = {"name": f["name"], "class": f["cls"]}
        if has_outline:
            o["features"].append({"type": "Feature", "properties": op, "geometry": mapping(shapely.set_precision(ol, 1e-7))})
            qa.append({"type": "Feature", "properties": op, "geometry": mapping(ol)})
        print(f"  {f['name']}: {len(geoms)} pieces, outline " + (f"{ol.area * k / 1e4:.1f} ha" if has_outline else "none (inside a standing airport)")
              + f", {f['opened']}-{f['closed']}")
    tag = "Vanished airfields of the 2026-11 map extension"
    if tag not in d.get("description", ""):
        d["description"] = d.get("description", "") + (
            f" {tag} (NAAS Santa Rosa, NOLF Cotati, Santa Cruz Sky Park, Capitola, old Rio Vista, Antioch, Petaluma Sky "
            "Ranch, Vallejo Sky Harbor, Calistoga, Morgan Hill, old Watsonville, Vaca-Dixon, Vacaville Gliderport, Knights, "
            "Benicia, Coddingtown): "
            "runway / taxiway / apron polygons traced on USGS historical topographic sheets (sheet per feature in `note`), "
            "each with its own start_year / end_year (data/manual/airports/tools/newarea.py).")
    if tag not in o.get("description", ""):
        o["description"] = o.get("description", "") + (
            f" {tag}: field boundary as drawn on the sheet, else the hull of the runways + 30-80 m "
            "(data/manual/airports/tools/newarea.py).")
    ef.write_text(json.dumps(d))
    eo.write_text(json.dumps(o))
    return qa


def write_table():
    p = TABLES / "airports.csv"
    mine = {f["name"] for f in FIELDS} | {u[0] for u in UNDATED}
    lines = p.read_text().split("\n")
    keep = [ln for ln in lines if ln and next(csv.reader([ln]))[0] not in mine]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    for f in FIELDS:
        w.writerow([f["name"], f["opened"], f["closed"], f["src"], f["csv_note"]])
    for nm, yr, src, note in UNDATED:
        w.writerow([nm, yr, "", src, note])
    # same quoting as the rest of the table: only the notes column is quoted
    new = []
    for row in csv.reader(io.StringIO(buf.getvalue())):
        new.append(",".join(row[:4]) + ',"' + row[4].replace('"', "'") + '"')
    p.write_text("\n".join(keep + new) + "\n")
    print(f"  airports.csv: {len(keep) - 1} kept + {len(new)} rows")


# ---------------------------------------------------------------------------------------------- phased airports
# (airport code, Overture id prefix, runway, [(from_end label, d0, d1, year, confidence, evidence)] or year)
S_TRAVIS = "USGS 1:24,000 Elmira + Denverton 1953 (1949 photos, field check 1953), 1968 and 1980 photorevisions"
S_NAPA = "USGS 1:24,000 Cuttings Wharf 1949 (1948 photos), 1968 photorevision, 1981 photorevision (1978 photos)"
S_STS = "USGS 1:24,000 Healdsburg 1955 (1953 photos) + Sebastopol 1954 (1952 photos), 1980 photorevisions, Healdsburg 1993"
S_WVI = "USGS 1:24,000 Watsonville West 1954 (1952 photos), 1968 / 1980 photorevisions, 1994"
U_TRAVIS = tnm("CA_Elmira_290319_1953_24000")
U_NAPA = tnm("CA_Cuttings Wharf_289711_1949_24000")
U_STS = "https://en.wikipedia.org/wiki/Charles_M._Schulz%E2%80%93Sonoma_County_Airport"
U_WVI = tnm("CA_Watsonville West_301247_1954_24000")
RUNWAYS = [
    ("TRAVIS", "47d9d0c9", "03L/21R", U_TRAVIS, [
        ("21R (north-east)", 0, 2900, 1943, "estimated", "on the first edition that maps the base (" + S_TRAVIS + "): "
         "pavement corridor along today's centre line from the north-east end to 2,900 m; dated with the opening of "
         "Fairfield-Suisun Army Air Base (built some time 1942-49)"),
        ("21R (north-east)", 2900, 3350, 1960, "estimated", "south-west 450 m: open ground on the 1949-photo sheet, "
         "runway extension in purple on the 1968 photorevision -> c.1960 (" + S_TRAVIS + ")")]),
    ("TRAVIS", "d32da621", "03L/21R", U_TRAVIS, 1960),
    ("TRAVIS", "3252ad81", "03L/21R", U_TRAVIS, 1943),
    ("TRAVIS", "a4201b40", "03R/21L", U_TRAVIS, [
        ("21L (north-east)", 0, 900, 1960, "estimated", "north-east 900 m: fields and a road on the 1949-photo sheet, "
         "runway extension in purple on the 1968 photorevision -> c.1960 (" + S_TRAVIS + ")"),
        ("21L (north-east)", 900, 3352, 1943, "estimated", "on the first edition that maps the base (1949 photos): "
         "pavement corridor from 900 m to the south-west end; dated with the opening of the base (built some time 1942-49)")]),
    ("TRAVIS", "48a0d5b9", "03R/21L", U_TRAVIS, 1960),
    ("TRAVIS", "15ce0402", "03R/21L", U_TRAVIS, 1943),
    ("TRAVIS", "b264d934", "assault strip", U_TRAVIS, 2008),
    ("NAPA", "b9e53d7d", "01L/19R", U_NAPA, [
        ("19R (north)", 0, 200, 1973, "estimated", "north 200 m beyond the apex of the 1942 triangle: not on the "
         "1948-photo sheet nor the 1968 photorevision, purple on the 1978-photo revision -> 1973 (" + S_NAPA + ")"),
        ("19R (north)", 200, 1807, 1942, "documented", "west leg of the Army Air Forces triangle of 1942 "
         "(napacounty.gov Airport History), complete on the 1948-photo sheet")]),
    ("NAPA", "a6263038", "06/24", U_NAPA, 1942),
    ("NAPA", "11a27e3b", "01R/19L", U_NAPA, 1973),
    ("STS", "2f8cd876", "14/32", U_STS, [
        ("14 (north-west)", 0, 270, 2014, "documented", "'In August 2013 the airport began a project to separate the ends "
         "of its two runways and lengthen runway 14/32 by 885 feet to 6,000 feet' (Wikipedia); open ground on every "
         "edition to 1993 (" + S_STS + ")"),
        ("14 (north-west)", 270, 1819, 1942, "documented", "Santa Rosa Army Air Field, opened June 1942; complete on "
         "the 1953-photo sheet")]),
    ("STS", "1ec54533", "02/20", U_STS, 1942),
    ("WVI", "902e906b", "02/20", U_WVI, 1943),
    ("WVI", "446ee894", "09/27", U_WVI, 1943),
    ("WVI", "f1541fc1", "02/20", U_WVI, 1943),
]
WHOLE_NOTE = {
    ("TRAVIS", 1943): ("estimated", "on the first edition that maps the base (" + S_TRAVIS + "); dated with its opening"),
    ("TRAVIS", 1960): ("estimated", "beside a runway extension that is purple on the 1968 photorevision, open ground "
                       "on the 1949-photo sheet -> c.1960 (" + S_TRAVIS + ")"),
    ("TRAVIS", 2008): ("estimated", "assault landing strip beside 03R/21L: not on any edition to the 1980 "
                       "photorevision; built for the C-17 crews based at Travis from 2006 - year ESTIMATED, no source found"),
    ("NAPA", 1942): ("documented", "base of the 1942 Army Air Forces triangle, complete on the 1948-photo sheet (" + S_NAPA + ")"),
    ("NAPA", 1973): ("estimated", "inside the triangle: not on the 1948-photo sheet nor the 1968 photorevision, purple "
                     "on the 1978-photo revision -> 1973 (" + S_NAPA + ")"),
    ("STS", 1942): ("documented", "Santa Rosa Army Air Field, opened June 1942; complete on the 1953-photo sheet (" + S_STS
                    + "); the 200 ft added in 2013-14 is not separated (end not identified)"),
    ("STS", 2014): ("documented", "taxiway of the 2013-14 runway-end separation, beside the 885-ft extension of 14/32; "
                    "open ground on every edition to 1993"),
    ("WVI", 1943): ("documented", "NAAS Watsonville, commissioned 23 Oct 1943; runway complete on the 1952-photo sheet and "
                    "unchanged on the 1968 / 1980 photorevisions and the 1994 sheet (" + S_WVI + ")"),
}
# taxiways / taxilanes / aprons that came with a dated extension: (airport, runway id prefix, d0, d1, reach m, year)
NEAR = [("TRAVIS", "47d9d0c9", 2900, 3660, 300, 1960), ("TRAVIS", "a4201b40", -310, 900, 300, 1960),
        ("NAPA", "b9e53d7d", -60, 200, 150, 1973), ("NAPA", "11a27e3b", 0, 764, 60, 1973),
        ("STS", "2f8cd876", -60, 270, 160, 2014)]
COLS = ["airport", "feature_class", "overture_id", "runway", "name", "lon", "lat", "part", "clip_zone", "from_end",
        "d0_m", "d1_m", "part_lon0", "part_lat0", "part_lon1", "part_lat1", "start_year", "end_year", "confidence",
        "source_url", "evidence"]
CODES = ("TRAVIS", "NAPA", "STS", "WVI")
AP_NAME = {"TRAVIS": "Travis Air Force Base", "NAPA": "Napa County Airport", "STS": "Sonoma County Airport",
           "WVI": "Watsonville Municipal Airport"}


def write_pavement(g):
    import geopandas as gpd
    from shapely.geometry import LineString
    from shapely.ops import substring
    UTM = 32610
    gu = g.to_crs(UTM)
    feats = gu[gu["class"].isin(["runway", "stopway", "taxiway", "taxilane", "apron"])]
    by = {i: (c, n, gm) for i, c, n, gm in zip(feats.id, feats["class"], feats.name, feats.geometry)}

    def find(pref):
        k = [i for i in by if i.startswith(pref)]
        assert len(k) == 1, (pref, k)
        return k[0]

    def ll(pt):
        q = gpd.GeoSeries([pt], crs=UTM).to_crs(4326).iloc[0]
        return round(q.x, 6), round(q.y, 6)

    rows, used = [], set()
    for ap, pref, rw, url, spec in RUNWAYS:
        i = find(pref); cls, nm, gm = by[i]; used.add(i)
        lon, lat = ll(gm.representative_point())
        base = dict(airport=ap, feature_class=cls, overture_id=i, runway=rw, name=nm if isinstance(nm, str) else "",
                    lon=lon, lat=lat, clip_zone="", end_year=9999, source_url=url)
        if isinstance(spec, int):
            conf, ev = WHOLE_NOTE[(ap, spec)]
            a, b = ll(gm.interpolate(0)), ll(gm.interpolate(gm.length))
            rows.append(dict(base, part="whole", from_end="", d0_m=0, d1_m=round(gm.length), part_lon0=a[0], part_lat0=a[1],
                             part_lon1=b[0], part_lat1=b[1], start_year=spec, confidence=conf, evidence=ev))
        else:
            for end, d0, d1, yr, conf, ev in spec:
                d1 = min(d1, gm.length)
                a, b = ll(gm.interpolate(d0)), ll(gm.interpolate(d1))
                rows.append(dict(base, part="axis_interval", from_end=end, d0_m=round(d0), d1_m=round(d1), part_lon0=a[0],
                                 part_lat0=a[1], part_lon1=b[0], part_lat1=b[1], start_year=yr, confidence=conf, evidence=ev))
    # pavement beside a dated extension
    ports = gu[gu["class"].isin(AIRPORT_CLASSES) & (gu.geom_type == "Polygon")]
    for ap, pref, d0, d1, reach, yr in NEAR:
        rid = find(pref); line = by[rid][2]
        c = list(line.coords)
        # extend the line beyond its ends when d0 < 0 or d1 > length (stopways / overruns)
        ux, uy = (c[1][0] - c[0][0]), (c[1][1] - c[0][1]); L0 = math.hypot(ux, uy)
        vx, vy = (c[-1][0] - c[-2][0]), (c[-1][1] - c[-2][1]); L1 = math.hypot(vx, vy)
        ext = LineString([(c[0][0] - ux / L0 * 400, c[0][1] - uy / L0 * 400)] + c + [(c[-1][0] + vx / L1 * 400, c[-1][1] + vy / L1 * 400)])
        seg = substring(ext, 400 + d0, 400 + d1)
        # the older part of the same runway: a feature nearer to it than to the extension keeps the opening year
        rest = []
        if d0 > 0:
            rest.append(substring(line, 0, d0))
        if d1 < line.length:
            rest.append(substring(line, d1, line.length))
        apg = ports[ports.name == AP_NAME[ap]].geometry.iloc[0]
        for i, (cls, nm, gm) in by.items():
            if i in used or cls in ("runway", "stopway") or gm.distance(apg) > 1500:
                continue
            p = gm.representative_point() if gm.geom_type != "LineString" else gm.interpolate(0.5, normalized=True)
            ds = p.distance(seg)
            if ds > reach or any(p.distance(r) <= ds for r in rest):
                continue
            used.add(i)
            lon, lat = ll(p)
            conf, ev = WHOLE_NOTE[(ap, yr)]
            if ap == "NAPA":
                ev = "beside the " + ("north extension of 01L/19R" if pref == "b9e53d7d" else "parallel runway 01R/19L") + ": " + ev
            rows.append(dict(airport=ap, feature_class=cls, overture_id=i, runway="", name=nm if isinstance(nm, str) else "",
                             lon=lon, lat=lat, part="whole", clip_zone="", from_end="", d0_m="", d1_m="", part_lon0="",
                             part_lat0="", part_lon1="", part_lat1="", start_year=yr, end_year=9999, confidence=conf,
                             source_url=dict(TRAVIS=U_TRAVIS, NAPA=U_NAPA, STS=U_STS, WVI=U_WVI)[ap], evidence=ev))
    p = HERE.parent / "pavement_dates.csv"
    raw = p.read_bytes().decode()
    nl = "\r\n" if "\r\n" in raw else "\n"
    keep = [ln for ln in raw.split(nl) if ln and not ln.startswith(tuple(c + "," for c in CODES))]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, lineterminator=nl)
    for r in rows:
        w.writerow(r)
    p.write_bytes((nl.join(keep) + nl + buf.getvalue()).encode())
    import collections
    cnt = collections.Counter((r["airport"], r["feature_class"], r["start_year"]) for r in rows)
    print("  pavement_dates.csv:", len(keep) - 1, "kept +", len(rows), "rows:", dict(sorted(cnt.items())))
    return rows


def main():
    g = overture()
    print("vanished airfields:")
    qa = write_fields(g)
    write_table()
    write_pavement(g)
    if len(sys.argv) > 1:           # QA copy of the traced features
        Path(sys.argv[1]).write_text(json.dumps({"type": "FeatureCollection", "features": qa}))


if __name__ == "__main__":
    main()
