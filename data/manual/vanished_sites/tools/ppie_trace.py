"""PPIE 1915 west end (the Presidio part of the Exposition: race track, polo / athletic / aviation field, livestock
exhibit, western state pavilions) from sheet 4 of the 1914 Sanborn map of the Panama-Pacific International Exposition.

  python -I ppie_trace.py SCRATCH          -> ../traced/ppie_sheet4_1914.json
  python -I ppie_trace.py SCRATCH --apply  -> also replaces site 'ppie_west_end' in ../sites.geojson / ../buildings.geojson

SCRATCH must hold the Library of Congress IIIF images of sheets 3 and 4 at 50 % (s0003.jpg, s0004.jpg):
  https://tile.loc.gov/image-services/iiif/service:gmd:gmd436m:g4364m:g4364sm:g4364sm_g008131915:00813_1915-000{3,4}/full/pct:50/0/default.jpg
(item https://www.loc.gov/item/sanborn00813_025/, "survey and inspection completed November 18, 1914", public domain).

Georeferencing (no street control on sheet 4, as noted in data/research/landmarks_batch4.md):
* sheet 3 -> the Exposition grid of viewer/src/landmarks/batch4.ts (origin = Palace of Fine Arts rotunda
  -122.448402, 37.802919; u along Chestnut St, bearing 80.89 deg): similarity fitted on the yellow footprints of six
  pavilions batch4 traced from the same sheet (Canada, Oregon, Pennsylvania, Netherlands, Argentina, Italy;
  residuals 0.7-5.3 m) -> 0.2050 m/px, 0.16 deg; the rotunda falls 2 m from its traced centre;
* sheet 4 abuts sheet 3 (the Avenue of the States kerb lines continue across the seam 8 px lower on sheet 4; the
  Canada pavilion straddles it): x3 = x4 - 3964, y3 = y4 - 8 (+-2 m).
Race track: two concentric arcs (inner / outer track lines) of the east turn fitted by RANSAC circles on the sheet's
line pixels: centre (235.6, 844.7) px, r = 97.7 m / 116.5 m (track 18.8 m wide), spanning +-96 deg - a semicircle and
the start of the straights. The west turn is beyond the sheet (in the Presidio): the oval is completed as a
stadium with the documented length - "the mile track" with "an athletic field and polo grounds in its infield"
(Daily Racing Form, 4 Dec 1915) - one mile at the inner line -> straights 497.7 m, its long axis at bearing 97 deg
as the oval is drawn on the USGS 1:62,500 San Francisco sheet, 1915 edition (whose oval spans the same 740 m of the
shore; that sheet is not on NAD27 control, so only its length / tilt are used). With the Exposition-grid bearing
(81 deg) the west turn would climb 20 m up the Presidio bluff; at 97 deg the whole oval stays on the Crissy flat.
ESTIMATED shape of the west half.
Buildings: yellow (frame) fills of sheet 4 (sbseg colour mask, close 15 px / open 5 px), names from the sheet's
lettering (label points below); the livestock stadium ring and the Dairy Building's open arena are read by hand.
Heights / storeys: ESTIMATES by use (the sheet's height figures were not read).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "traced" / "ppie_sheet4_1914.json"
SANBORN = "https://www.loc.gov/item/sanborn00813_025/"
O = (-122.448402, 37.802919)          # Palace of Fine Arts rotunda (batch4.ts PPIE_O)
BRG_U = 80.89                         # u axis bearing (Chestnut St)
A3 = complex(0.20501552, 0.00058241)   # sheet-3 similarity: (u + i v) = A3 * (x - i y) + B3   (x, y = 50 % pixels)
B3 = complex(-355.67669, 439.43939)
SEAM = (-3964.0, -8.0)                 # sheet 4 pixel -> sheet 3 pixel
TRACK_C = (235.6, 844.8)               # east-turn centre (sheet-4 px)
R_IN, R_OUT = 97.7, 116.5              # metres
MILE = 1609.34
AXIS_BRG = 97.0                        # long axis of the oval on the USGS 1:62,500 San Francisco 1915 sheet (+-2 deg)
LABELS = {  # sheet-4 px of the lettering -> name, use
    (3570, 385): ("Montana Building", "state"), (3570, 550): ("Maryland Building", "state"),
    (3900, 385): ("Idaho Building", "state"), (2400, 400): ("West Virginia Building", "state"),
    (2400, 550): ("Kansas Building", "state"), (2125, 470): ("Arkansas Building", "state"),
    (2865, 500): ("North Dakota Building", "state"), (2765, 780): ("Iowa Building", "state"),
    (3440, 785): ("Washington State Building", "state"), (3085, 1030): ("Massachusetts Building", "state"),
    (3800, 865): ("Utah Building", "state"), (3812, 1210): ("Indiana Building", "state"),
    (3437, 1420): ("Philippine Islands Building", "nation"), (3700, 1680): ("Sweden Pavilion", "nation"),
    (380, 1560): ("Poultry Exhibit", "poultry"), (720, 1800): ("stables for work teams", "stable"),
    (1259, 434): ("feed storage and warehouses (stock supply yard)", "shed"),
    (1955, 470): ("Livestock Congress auditorium and office building", "hall1"), (950, 590): ("stock supply yard buildings", "shed"),
}
USE = {"state": (10.0, 2, "hall"), "nation": (10.0, 2, "hall"), "barn": (7.0, 1, "hall"), "poultry": (6.0, 1, "hall"),
       "stable": (5.0, 1, "other"), "hall1": (5.0, 1, "hall"), "shed": (6.0, 1, "other"), "dairy": (9.0, 1, "hall"), "stadium": (8.0, 1, "grandstand")}
# hand-read (sheet-4 px): the livestock stadium (stalls ring round the show ring) and the Dairy Building's open arena
STADIUM_OUT = [(1040, 950), (1100, 890), (1665, 890), (1725, 950), (1725, 1125), (1665, 1185), (1100, 1185), (1040, 1125)]
STADIUM_IN = [(1090, 985), (1130, 945), (1635, 945), (1675, 985), (1675, 1090), (1635, 1130), (1130, 1130), (1090, 1090)]
DAIRY_IN = [(690, 1500), (1410, 1500), (1410, 1625), (690, 1625)]
BUILT, OPEN, CLOSE, GONE = 1914.3, 1915.13, 1915.92, 1916.3   # construction 1914; 20 Feb - 4 Dec 1915; razed 1916 (batch4)


def uv_of_px4(x, y):
    z = A3 * ((np.asarray(x) + SEAM[0]) - 1j * (np.asarray(y) + SEAM[1])) + B3
    return z.real, z.imag


def ll_of_uv(u, v):
    su, cu = math.sin(math.radians(BRG_U)), math.cos(math.radians(BRG_U))
    east, north = u * su - v * cu, u * cu + v * su
    k = 111320 * math.cos(math.radians(O[1]))
    return O[0] + east / k, O[1] + north / 110574


def ll_of_px4(pts):
    p = np.asarray(pts, float)
    u, v = uv_of_px4(p[:, 0], p[:, 1])
    lon, lat = ll_of_uv(u, v)
    return np.c_[lon, lat].tolist()


def stadium_ll(r_m, step_deg=4):
    """Stadium (two semicircles of radius r_m joined by straights) in lon/lat: east-turn centre traced on the Sanborn
    sheet (TRACK_C), axis bearing AXIS_BRG, straights of one mile at the inner line."""
    E = np.array(ll_of_px4([TRACK_C])[0])
    k = 111320 * math.cos(math.radians(E[1]))
    L = (MILE - 2 * math.pi * R_IN) / 2
    d = np.array([math.sin(math.radians(AXIS_BRG)), math.cos(math.radians(AXIS_BRG))])   # east, north of the axis
    n = np.array([-d[1], d[0]])
    pts = [d * r_m * math.cos(math.radians(a)) + n * r_m * math.sin(math.radians(a)) for a in np.arange(-90, 90.1, step_deg)]
    pts += [-d * L + d * r_m * math.cos(math.radians(a)) + n * r_m * math.sin(math.radians(a)) for a in np.arange(90, 270.1, step_deg)]
    pts = np.array(pts)
    return np.c_[E[0] + pts[:, 0] / k, E[1] + pts[:, 1] / 110574].tolist()


def trace(scratch: Path):
    sys.path.insert(0, str(HERE))
    from sbseg import comps
    from shapely.geometry import Polygon
    cs = comps(str(scratch / "s0004.jpg"), min_area=1500, close_k=15, open_k=5, kinds=("yellow", "pink"))
    st_out = Polygon(STADIUM_OUT)
    out = {"source": SANBORN, "buildings": [], "parts": []}
    for c in cs:
        xs = [p[0] for p in c["coords"]]
        if c["cy"] > 2000 or max(xs) > 3960 or len(c["coords"]) < 3:
            continue                                     # below the map / cut by the seam (on sheet 3)
        poly = Polygon(c["coords"]).buffer(0)
        if st_out.buffer(10).contains(poly.representative_point()):
            continue                                     # the stadium ring is read by hand
        cxy = np.array([c["cx"], c["cy"]])
        name, kind = "livestock barn (Stock Exhibit)", "barn"
        if c["area_px"] > 60000:
            name, kind = "Dairy Building", "dairy"
            poly = poly.difference(Polygon(DAIRY_IN))
        else:
            d = {k: math.hypot(*(cxy - np.array(k))) for k in LABELS}
            k = min(d, key=d.get)
            if d[k] < 260 or not (850 < c["cx"] < 1900 and 650 < c["cy"] < 1420):
                name, kind = LABELS[k] if d[k] < 400 else ("Exposition pavilion (name not read)", "state")
        poly = poly.simplify(1.5)
        for p in getattr(poly, "geoms", [poly]):
            if p.area < 1500:
                continue
            out["buildings"].append({"name": name, "kind": kind, "ll": ll_of_px4(p.exterior.coords),
                                     "holes": [ll_of_px4(h.coords) for h in p.interiors]})
    ring = Polygon(STADIUM_OUT).difference(Polygon(STADIUM_IN))
    out["buildings"].append({"name": "Livestock stadium (enclosed stalls and seats round the show ring)", "kind": "stadium",
                             "ll": ll_of_px4(ring.exterior.coords), "holes": [ll_of_px4(h.coords) for h in ring.interiors]})
    out["parts"] = {
        "track_outer": stadium_ll(R_OUT), "track_inner": stadium_ll(R_IN),
        "show_ring": ll_of_px4(STADIUM_IN), "dairy_arena": ll_of_px4(DAIRY_IN)}
    OUT.write_text(json.dumps(out))
    print(f"{OUT}: {len(out['buildings'])} buildings")
    return out


def apply(d):
    import shapely
    from shapely.geometry import Polygon, mapping
    SID = "ppie_west_end"
    NAME = "Exposition race track and livestock exhibit (PPIE 1915)"
    DRF = "https://drf.uky.edu/catalog/1910s/drf1915120401/drf1915120401_2_5"
    P = lambda ring, holes=(): Polygon(ring, list(holes)).buffer(0)
    tout, tin = P(d["parts"]["track_outer"]), P(d["parts"]["track_inner"])
    TRACK_END = 1919.5   # Army air coast-defence station built 1919-21 "on the old racetrack" (airports.csv Crissy Field)
    parts = [
        (tout.difference(tin), "dirt_track", "dirt track", OPEN - 0.1, TRACK_END, "estimated",
         "the Exposition's one-mile track on the Presidio (Vanderbilt Cup and Grand Prix 22 Feb / 6 Mar 1915, horse races, the "
         "October horse show; NPS): east turn traced from sheet 4 of the 1914 Sanborn map of the PPIE (two track lines, 18.8 m "
         "apart), west turn beyond the sheet - completed as a stadium of one mile at the inner line (ESTIMATED shape). The track "
         "builder wanted to keep it after the fair (Daily Racing Form, 4 Dec 1915); it lay idle until the Army built Crissy "
         "airfield on it 1919-21 (end ESTIMATED)", DRF),
        (tin, "turf", "polo field / athletic field / aviation field", OPEN - 0.1, TRACK_END, "estimated",
         "infield: 'an athletic field and polo grounds in its infield' (Daily Racing Form, 4 Dec 1915) - POLO FIELD on the 1914 "
         "Sanborn sheet; the Exposition Athletic Field was dedicated 9 Apr 1915 (NPS); Lincoln Beachey's and Art Smith's flights "
         "used the Marina field. Turf ESTIMATED", "https://www.nps.gov/goga/learn/historyculture/ppie-sportsandathletics.htm"),
        (P(d["parts"]["show_ring"]), "dirt_track", "livestock show ring", OPEN - 0.1, GONE, "estimated",
         "the open show ring ('STADIUM') inside the stalls of the Stock Exhibit, 1914 Sanborn map of the PPIE sheet 4", SANBORN),
        (P(d["parts"]["dairy_arena"]), "dirt_track", "open arena", OPEN - 0.1, GONE, "estimated",
         "open arena inside the Dairy Building ('open arena', hand-read on the 1914 Sanborn sheet 4)", SANBORN),
    ]
    site_feats = []
    for g, cover, surface, y0, y1, conf, note, src in parts:
        g = shapely.set_precision(shapely.make_valid(g), 1e-7)
        site_feats.append({"type": "Feature", "properties": {
            "site_id": SID, "name": NAME, "kind": "racetrack", "cover": cover, "surface": surface, "year_start": y0,
            "year_end": y1, "confidence": conf, "source_url": src, "note": note}, "geometry": mapping(g)})
    bl_feats = []
    for b in d["buildings"]:
        h, storeys, use = USE[b["kind"]]
        g = shapely.set_precision(shapely.make_valid(P(b["ll"], b.get("holes", []))), 1e-7)
        mat = "wood frame"
        bl_feats.append({"type": "Feature", "properties": {
            "site_id": SID, "name": b["name"] + " (PPIE 1915)", "start_year": OPEN, "end_year": GONE, "height_m": h,
            "storeys": storeys, "material": mat, "use": use, "confidence": "estimated", "source_url": SANBORN,
            "note": "footprint: yellow (frame) fill of the 1914 Sanborn map of the PPIE, sheet 4 (chained to sheet 3, +-5 m); built "
                    "1914, Exposition 20 Feb - 4 Dec 1915, razed 1916 (end as the batch4 PPIE models, 1916.3); height / storeys "
                    "ESTIMATED by use"}, "geometry": mapping(g)})
    for fname, feats in (("sites.geojson", site_feats), ("buildings.geojson", bl_feats)):
        # the files are GDAL-style GeoJSON (one feature per line): keep that layout, replace this site's lines
        p = HERE.parent / fname
        lines = p.read_text().split("\n")
        i0 = next(i for i, ln in enumerate(lines) if ln.startswith('"features": ['))
        i1 = max(i for i, ln in enumerate(lines) if ln.strip() == "]")
        body = [ln.rstrip(",") for ln in lines[i0 + 1:i1] if ln.strip() and f'"site_id": "{SID}"' not in ln]
        body += [json.dumps(f, ensure_ascii=False) for f in feats]
        lines = lines[:i0 + 1] + [ln + "," for ln in body[:-1]] + body[-1:] + lines[i1:]
        p.write_text("\n".join(lines))
        print(f"{fname}: + {len(feats)} '{SID}' features ({len(body)} total)")


if __name__ == "__main__":
    scratch = Path(sys.argv[1])
    d = trace(scratch)
    if "--apply" in sys.argv:
        apply(d)
