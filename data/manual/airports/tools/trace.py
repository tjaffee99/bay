"""Vanished airport buildings: building symbols traced in checked windows of one reference edition,
dated by their presence on every edition (renders of render.py, same frame).

  python -I tools/trace.py SCRATCH_DIR      (expects the renders sfoB_*, oak_*, sjc_*.npy there)
  -> vanished_buildings.geojson (+ SCRATCH_DIR/trace_<ap>.png QA overlays)

Each target is a window (airport frame, local metres) on a reference edition, read by eye on the
gridded renders first. Symbols in it: dark ink + purple photorevision ink + cross-hatching
(density > 1/3 in a 7 m box), opened by 6 m; >= 150 m2; rectangle-like (area / min. rectangle
>= 0.6). Symbols lying >= 25 % under a footprint of today that is older than the target's end are
skipped (that building still stands). Presence per edition as tools/bpresence.py (ink >= 30 % of the
symbol + 4 m after the 6 m opening, or raw ink >= 35 %). start = midpoint of the last edition
without it and the first edition with it (drawn on the earliest edition: the target's `first`
year); end = midpoint of the last edition with it and the next without it, or the target's
documented end. Heights / storeys / material: ESTIMATES by use (see `USE`).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import geopandas as gpd
import numpy as np
import shapely
from shapely.geometry import Polygon, mapping

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
TOPO = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/"
EDS = {
    "SFO": [(1946, "sfoB_1946"), (1956, "sfoB_1956"), (1968, "sfoB_1968"), (1973, "sfoB_1973"), (1979, "sfoB_1979"),
            (1993, "sfoB_1993")],
    "OAK": [(1947, "oak_1947"), (1958, "oak_1958"), (1968, "oak_1968"), (1973, "oak_1973"), (1979, "oak_1979"),
            (1993, "oak_1993")],
    "SJC": [(1948, "sjc_1948"), (1960, "sjc_1960"), (1968, "sjc_1968"), (1973, "sjc_1973"), (1979, "sjc_1979")],
}
HALF = {"SFO": 2400.0, "OAK": 2600.0, "SJC": 1800.0}
RES = 2.0
SHEET = {  # reference edition -> the sheet that covers the window (for source_url)
    ("SFO", 1956): "CA_San%20Francisco%20South_363066_1956_24000_geo.tif",
    ("SFO", 1993): "CA_Montara%20Mountain_293075_1993_24000_geo.tif",
    ("OAK", 1958): "CA_San%20Leandro_300124_1959_24000_geo.tif",
    ("SJC", 1979): "CA_San%20Jose%20West_300110_1961_24000_geo.tif",
    ("SJC", 1968): "CA_San%20Jose%20West_300108_1961_24000_geo.tif",
    ("SJC", 1948): "CA_San%20Jose%20West_300105_1953_24000_geo.tif",
}
USE = {  # use -> (height_m, storeys, material): ESTIMATES
    "hangar": (12.0, 1, "steel"), "terminal": (10.0, 2, "concrete"), "barracks": (7.0, 2, "wood frame"),
    "other": (6.0, 1, "wood frame"), "t-hangar": (4.5, 1, "steel"), "concourse": (8.0, 2, "concrete"),
}

TARGETS = [
    dict(ap="SFO", ref=1956, win=[-1450, -1150, 600, 1120], first=1940, end=1961, use="hangar", min_fill=0.35,
         exclude=[[-1265, -1165, 915, 975], [-1235, -1150, 690, 755], [-1510, -1420, 915, 965]],  # lettering, quad line
         name="San Francisco Airport west-side building (old Bayshore Highway frontage)",
         conf="estimated",
         note="the pre-war / 1940s airport buildings on the west side of the field along the old Bayshore Highway "
              "(hangars, offices; the 1937 Administration and Terminal Building stood on this frontage - SFO "
              "Museum: 1937 building demolished 1966). Cleared for the 1961 west extension of 10R/28L ('Runway 28 "
              "Left was lengthened ... in 1961') and the 10L west end; none drawn on the 1968 photorevision. "
              "Individual identities not established"),
    dict(ap="SFO", ref=1956, win=[-1010, -790, 110, 270], first=1940, end=None, use="hangar", skip_today_after=1975,
         name="San Francisco Airport hangar north-west of the Central Terminal",
         conf="estimated",
         note="long building on the 1956 sheet (hangar row by the 1954 Central Terminal); gone on the 1979 "
              "photorevision - its site became the North Terminal area (North Terminal begun 1971, opened 1979)"),
    dict(ap="OAK", ref=1958, win=[250, 820, 1300, 2150], first=1943, end=None, use="barracks",
         name="Naval Air Station Oakland building (North Field)",
         conf="estimated",
         note="Navy buildings of NAS Oakland / the WWII base on North Field (Army 1942, Navy lease 1 Feb 1944; "
              "'barracks housed 253 officers and 4,658 men'); drawn from the 1947 sheet on, gone on a later "
              "edition (end = midpoint)"),
    dict(ap="OAK", ref=1958, win=[650, 1600, 600, 1150], first=1929, end=None, use="hangar",
         name="Oakland Municipal Airport North Field building (Doolittle Drive / Earhart Road frontage)",
         conf="estimated",
         note="North Field buildings along the field's east frontage that are gone today (the 1927-29 airport "
              "had 'five hangars, passenger terminal / administrative offices and a restaurant', Port of "
              "Oakland; the Navy's 1944 lease lists '8 hangars'); first-edition buildings start 1929 (estimated)"),
    dict(ap="SJC", ref=1979, win=[580, 880, -160, 130], first=1965, end=2010, use="terminal", min_fill=0.3,
         start_doc=1965,
         name="San Jose Municipal Airport Terminal C (1965)",
         conf="estimated", skip_today_after=2005,
         note="opened 1965 (groundbreaking 27 Apr 1964; south concourse 1969); north end demolished Dec 2007 - "
              "Feb 2008, closed 30 Jun 2010 when Terminal B opened and torn down, site to parking (Wikipedia, SJC "
              "timeline). Outline = the purple photorevision symbols of the 1979 PR (1979 photos)"),
    dict(ap="SJC", ref=1979, win=[950, 1420, -1380, -950], first=1955, end=2000, use="t-hangar",
         name="San Jose airport south-east T-hangar row",
         conf="estimated", skip_today_after=2005,
         note="T-hangar / shelter rows at the south-east end, removed for the 12L/30R extension (2020 Master Plan: "
              "'G-2. Remove southeast t-hangar facilities' and 'G-1. Remove south end tiedowns, shelters, and "
              "General Aviation Terminal facilities', complete; runway reopened Aug 2001) - end 2000 estimated"),
    dict(ap="SJC", ref=1948, win=[300, 900, -1450, -1000], first=1946, end=None, use="hangar",
         name="San Jose Municipal Airport early building (south-east, Airport Blvd)",
         conf="estimated",
         note="buildings of the first airport at the south-east end (Nissen's flight school 1945-46, municipal "
              "airport dedicated 1 Feb 1949, first terminal 1950); drawn on the 1953 sheets (1948 photos)"),
]


# hand-read round symbols (airport frame, local metres): the South Terminal rotundas at SFO
WIKI_SFO = "https://en.wikipedia.org/wiki/San_Francisco_International_Airport"
CIRCLES = [
    dict(ap="SFO", xy=(-986, -406), r=22, start=1974, end=2007, use="concourse", src=WIKI_SFO,
         name="SFO Rotunda A (South Terminal)",
         note="'Rotunda A was completed in 1974' and 'demolished in early 2007' (Wikipedia, Terminal 1 section); "
              "round gate building at the end of the south-west pier, position and size read on the 1993 sheet "
              "(+-10 m); identification by position (estimated)"),
    dict(ap="SFO", xy=(-766, -500), r=17, start=1963, end=2017, use="concourse", src=WIKI_SFO,
         name="SFO South Terminal Boarding Area B rotunda (west)",
         note="one of the two rotundas of the 1963 South Terminal's Boarding Area B pier, demolished for Harvey Milk "
              "Terminal 1 ('demolishing the old TWA hangar and two rotundas'; groundbreaking 29 Jun 2016). Read on "
              "the 1979 PR / 1993 sheets (+-10 m); start = South Terminal dedication 15 Sep 1963 (estimated)"),
    dict(ap="SFO", xy=(-626, -466), r=17, start=1963, end=2017, use="concourse", src=WIKI_SFO,
         name="SFO South Terminal Boarding Area B rotunda (east)",
         note="see the west rotunda"),
]


def ink(img):
    r, g, b = (img[:, :, i].astype(int) for i in range(3))
    dark = (r < 120) & (g < 120) & (b < 120) & (np.abs(r - g) < 45) & (np.abs(g - b) < 45)
    purple = ((r - g) > 38) & ((b - g) > 18) & (g < 175)
    return (dark | purple).astype(np.uint8)


def symbols(img):
    m = ink(img).astype(np.float32)
    den = cv2.blur(m, (5, 5))
    s = ((den > 0.33) | (m > 0)).astype(np.uint8)
    s = cv2.morphologyEx(s, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    return cv2.morphologyEx(s, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))


def main():
    scratch = Path(sys.argv[1])
    d = __import__("pandas").read_parquet(build.OVT)
    feats = []
    for ap in ("SFO", "OAK", "SJC"):
        H = HALF[ap]
        imgs = {y: np.load(scratch / f"{n}.npy", mmap_mode="r") for y, n in EDS[ap]}
        years = [y for y, _ in EDS[ap]]
        bl = gpd.read_file(scratch / f"{ap}_bldg.geojson")
        n = imgs[years[0]].shape[0]
        P = lambda x, y: np.c_[(np.asarray(x) + H) / RES, (H - np.asarray(y)) / RES]
        for t in [t for t in TARGETS if t["ap"] == ap]:
            # today's footprints that cover the building -> it still stands (skip)
            fm = np.zeros((n, n), np.uint8)
            for g, s0 in zip(bl.geometry.values, bl.start_now.values):
                if t.get("skip_today_after") and s0 >= t["skip_today_after"]:
                    continue
                for p in getattr(g, "geoms", [g]):
                    x, y = build.ll2loc(ap, *np.asarray(p.exterior.coords).T)
                    cv2.fillPoly(fm, [np.round(P(x, y)).astype(np.int32)], 1)
            x0, x1, y0, y1 = t["win"]
            i0, i1 = int((x0 + H) / RES), int((x1 + H) / RES)
            j0, j1 = int((H - y1) / RES), int((H - y0) / RES)
            ref = np.asarray(imgs[t["ref"]][j0:j1, i0:i1])
            s = symbols(ref)
            cnt, lab, st, _ = cv2.connectedComponentsWithStats(s, 8)
            k = 0
            for i in range(1, cnt):
                if st[i, cv2.CC_STAT_AREA] * RES * RES < 150:
                    continue
                comp = (lab == i).astype(np.uint8)
                if (comp & fm[j0:j1, i0:i1]).sum() / comp.sum() >= 0.25:
                    continue
                cs, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                c = max(cs, key=cv2.contourArea)
                rect = cv2.minAreaRect(c)
                fill = comp.sum() / max(rect[1][0] * rect[1][1], 1)
                pts = cv2.boxPoints(rect) if fill > 0.82 else cv2.approxPolyDP(c, 0.75, True)[:, 0, :].astype(float)
                if len(pts) < 3:
                    continue
                poly = Polygon([(x0 + (px + 0.5) * RES, y1 - (py + 0.5) * RES) for px, py in pts]).buffer(0)
                if poly.geom_type != "Polygon" or poly.area < 150 or poly.area > 40000:
                    continue
                if poly.area / poly.minimum_rotated_rectangle.area < t.get("min_fill", 0.6) or min(rect[1]) * RES < 6:
                    continue
                if any(shapely.box(ex[0], ex[2], ex[1], ex[3]).contains(poly.centroid) for ex in t.get("exclude", [])):
                    continue
                # presence on every edition
                ring = P(*np.asarray(poly.exterior.coords).T)
                pm = np.zeros((n, n), np.uint8)
                cv2.fillPoly(pm, [np.round(ring).astype(np.int32)], 1)
                pb = cv2.dilate(pm, np.ones((5, 5), np.uint8))
                pres = []
                for y in years:
                    im = np.asarray(imgs[y][max(j0 - 20, 0):j1 + 20, max(i0 - 20, 0):i1 + 20])
                    sub = (slice(max(j0 - 20, 0), j1 + 20), slice(max(i0 - 20, 0), i1 + 20))
                    m = ink(im)
                    mo = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
                    blank = im.astype(int).sum(2) >= 3 * 254
                    a = pm[sub] > 0
                    if blank[a].mean() > 0.5:
                        pres.append(None)
                        continue
                    solid = mo[pb[sub] > 0].mean()
                    raw = symbols(im)[a].mean()
                    pres.append(bool(solid >= 0.30 or raw >= 0.5))
                kr = years.index(t["ref"])
                pres[kr] = True
                # contiguous run of presence around the reference edition
                a_ = kr
                while a_ - 1 >= 0 and pres[a_ - 1] is not False:
                    a_ -= 1
                b_ = kr
                while b_ + 1 < len(years) and pres[b_ + 1] is not False:
                    b_ += 1
                start = (years[a_ - 1] + years[a_]) / 2 if a_ > 0 else float(t["first"])
                start = max(start, float(t["first"]))
                if t.get("start_doc") and poly.area >= 2000:
                    start = float(t["start_doc"])
                if t["end"] is not None:
                    end = float(t["end"])
                elif b_ + 1 < len(years):
                    end = (years[b_] + years[b_ + 1]) / 2
                else:
                    continue  # still drawn on the last edition: not established as vanished
                if end <= start:
                    continue
                k += 1
                h, nst, mat = USE[t["use"]]
                lon, lat = build.loc2ll(ap, *np.asarray(poly.exterior.coords).T)
                drawn = ",".join(str(y) for y, p in zip(years, pres) if p)
                feats.append({"type": "Feature", "geometry": mapping(shapely.set_precision(Polygon(np.c_[lon, lat]), 1e-7)),
                              "properties": dict(site_id=f"airport_{ap.lower()}", name=t["name"], start_year=round(start, 1),
                                                 end_year=round(end, 1), height_m=h, storeys=nst, material=mat,
                                                 use="hall" if t["use"] in ("terminal", "concourse") else
                                                 ("dwelling" if t["use"] == "barracks" else "other"),
                                                 confidence=t["conf"], source_url=TOPO + SHEET[(ap, t["ref"])],
                                                 note=f"{t['note']}. Symbol traced on the {t['ref']} edition ({round(poly.area)} m2); "
                                                      f"drawn on: {drawn}. Height / storeys / material ESTIMATED ({t['use']})")})
            print(ap, t["name"][:50], k, "buildings")
    for c in CIRCLES:
        poly = shapely.Point(c["xy"]).buffer(c["r"], 16)
        lon, lat = build.loc2ll(c["ap"], *np.asarray(poly.exterior.coords).T)
        h, nst, mat = USE[c["use"]]
        feats.append({"type": "Feature", "geometry": mapping(shapely.set_precision(Polygon(np.c_[lon, lat]), 1e-7)),
                      "properties": dict(site_id=f"airport_{c['ap'].lower()}", name=c["name"], start_year=c["start"],
                                         end_year=c["end"], height_m=h, storeys=nst, material=mat, use="hall",
                                         confidence="estimated", source_url=c["src"],
                                         note=c["note"] + "; height / storeys / material ESTIMATED")})
    (HERE / "vanished_buildings.geojson").write_text(json.dumps({"type": "FeatureCollection", "name": "vanished_buildings",
                                                                  "features": feats}, indent=0))
    print(len(feats), "vanished buildings")


if __name__ == "__main__":
    main()
