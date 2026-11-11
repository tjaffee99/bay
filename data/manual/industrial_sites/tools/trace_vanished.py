"""Vanished buildings of the industrial / military sites, traced from the USGS sheets.

    python -I trace_vanished.py [site_id ...]      (run in this folder; needs the network: TNM sheets)

The sites of this folder (sites.geojson) carry their ground and a label, and their footprints
standing today are dated by the map editions (date_editions.py) — but what stood on them and
is gone was missing: the four Kaiser shipyards at Richmond were bare fill through the war,
the Selby smelter, the powder works, Camp Stoneman or the Oakland Army Base empty ground
(owner, 2026-11: "fix the missing Kaiser shipyards and anything similar").

For each site in TARGETS the building symbols of the first 1:24,000 edition after its founding
(and of a later one for long-lived sites) are extracted inside the site outline:

  * filled symbols: dark ink, opened by 5 m (drops roads, rails, lettering), connected
    components of at least MIN_M2 whose narrow side is at least 9 m;
  * hatched symbols (large buildings): the hatch density mask of the vanished-sites tools;
  * not counted: round symbols (tanks), symbols on the sheet's water tint or on its red
    built-up tint (city blocks are not drawn building by building there).

A symbol that overlaps a footprint standing today is that building (left to the footprint
table; listed in traced/<site>_standing.csv with the edition year, for the dating audit).
The rest are vanished buildings: start = the site's founding (the first edition after it
draws them) or the midpoint between the last edition without and the first with the symbol;
end = the midpoint between the last edition that draws it and the next that does not (the
site's closing year where documented and no edition says otherwise). Heights are not on the
maps: one tall storey by footprint size (ESTIMATED, said in each note).

Output: ../vanished_buildings.geojson (same columns as vanished_sites/buildings.geojson; read
by pipeline/region_predecessors.py) and traced/<site>_<year>.json (local-metre tracings).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Polygon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "vanished_sites" / "tools"))
import vt  # noqa: E402
import editions as ed  # noqa: E402
import date_editions as de  # noqa: E402
import footprints as fpm  # noqa: E402

OUT = HERE.parent / "vanished_buildings.geojson"
TRACED = HERE.parent / "traced"
MIN_M2 = 180.0
G = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/"


def _known_years():
    """fid (first 8 characters) -> the edition-dated year of known_dates_industrial.csv."""
    p = HERE.parent / "known_dates_industrial.csv"
    if not p.exists():
        return {}
    k = pd.read_csv(p)
    return {str(i).rsplit("_", 1)[-1]: float(y) for i, y in zip(k["id"], k["start_year"]) if len(str(i).rsplit("_", 1)[-1]) == 8}


KNOWN_Y = _known_years()


def tint_masks(img):
    """(water, built-up) tints of a 1:24,000 sheet, pixel by pixel (float 0/1; the caller
    averages them over a ring round each symbol, which also evens out the dot screens)."""
    r, g, b = (img[:, :, i].astype(np.float32) for i in range(3))
    light = (r + g + b) > 420          # not ink
    water = light & (b > r + 6) & (g > r + 6)
    built = light & (r > g + 18) & (r > b + 18)
    return water.astype(np.float32), built.astype(np.float32)


def symbols(img, half, res, zone_xy):
    """Building symbols inside zone_xy (local metres) -> list of dicts (poly, area, kind)."""
    n = img.shape[0]
    r, g, b = (img[:, :, i].astype(int) for i in range(3))
    dark = ((r < 105) & (g < 105) & (b < 105) & (np.abs(r - g) < 45) & (np.abs(g - b) < 45)).astype(np.uint8)
    k = max(1, int(round(5.0 / res)))
    solid = cv2.morphologyEx(dark, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    # hatched symbols (large buildings) are printed as a screen of separate dots on a ~11 m
    # pitch: where small detached specks of ink stand that densely (one per ~60 m2), over
    # at least 25 m in every direction, is a hatched building. Rails, road casings and
    # lettering are long connected strokes and never count. (The vanished-sites hatch
    # mask, tuned for 2 m pixels, chained the rail lines of a yard into one blob at 1 m.)
    mx = np.maximum(np.maximum(r, g), b)
    ink = ((mx < 125) & (np.abs(r - g) < 55) & (np.abs(g - b) < 55)).astype(np.uint8)
    w31 = max(5, int(round(31 / res)) | 1)
    dd = np.zeros((n, n), np.float32)
    # three ways to count a screen: its dots, its dots thinned (where they touch), and the
    # white gaps between dots that have run together into a mesh
    for src in (ink, cv2.erode(ink, np.ones((2, 2), np.uint8)), 1 - ink):
        nk, _, st, cen = cv2.connectedComponentsWithStats(src, 4)  # the dots of a screen touch at their corners
        a2 = st[:, cv2.CC_STAT_AREA] * res * res
        speck = (a2 >= 2) & (a2 <= 90) & (st[:, cv2.CC_STAT_WIDTH] * res <= 13) & (st[:, cv2.CC_STAT_HEIGHT] * res <= 13)
        speck[0] = False
        dots = np.zeros((n, n), np.float32)
        cc = np.round(cen[speck]).astype(int)
        dots[np.clip(cc[:, 1], 0, n - 1), np.clip(cc[:, 0], 0, n - 1)] = 1.0
        dd = np.maximum(dd, cv2.blur(dots, (w31, w31)) / (res * res))
    hat = (dd > 0.0055).astype(np.uint8)
    hat = hat & (1 - cv2.dilate(cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((max(3, int(round(11 / res))),) * 2, np.uint8)), np.ones((5, 5), np.uint8)))
    k25 = max(3, int(round(25 / res)) | 1)
    hat = cv2.morphologyEx(hat, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k25, k25)))
    zm = np.zeros((n, n), np.uint8)
    for ring in zone_xy:
        cv2.fillPoly(zm, [np.array([[(x + half) / res, (half - y) / res] for x, y in ring], np.int32)], 1)
    water_raw, built_raw = tint_masks(img)
    out = []
    for kind, m in (("hatched", hat), ("filled", solid)):
        m = m & zm
        num, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
        for i in range(1, num):
            a = stats[i, cv2.CC_STAT_AREA] * res * res
            if a < MIN_M2:
                continue
            x0, y0, w, h = stats[i, :4]
            comp = (lab[y0:y0 + h, x0:x0 + w] == i).astype(np.uint8)
            # the tint around the symbol (under it the ink hides it): lettering on the water
            # and symbols inside the red built-up tint are not buildings to trace
            pad = int(round(14 / res))
            Y0, Y1, X0, X1 = max(0, y0 - pad), min(n, y0 + h + pad), max(0, x0 - pad), min(n, x0 + w + pad)
            big = (lab[Y0:Y1, X0:X1] == i).astype(np.uint8)
            ring = cv2.dilate(big, np.ones((2 * pad + 1, 2 * pad + 1), np.uint8)) - cv2.dilate(big, np.ones((5, 5), np.uint8))
            wfrac = water_raw[Y0:Y1, X0:X1][ring > 0].mean() if ring.any() else 0.0
            if wfrac > 0.45 or (wfrac > 0.25 and a < 500) or (ring.any() and built_raw[Y0:Y1, X0:X1][ring > 0].mean() > 0.6):
                continue  # (a letter of a channel's name is small and stands in the water)
            cs, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            c = max(cs, key=cv2.contourArea)
            (cx, cy), (rw, rh), ang = cv2.minAreaRect(c)
            if min(rw, rh) * res < 11.0 or max(rw, rh) > 9.0 * min(rw, rh):
                continue  # a road casing, a railway, a pier line
            hull = cv2.contourArea(cv2.convexHull(c)) * res * res
            fill = a / max(rw * rh * res * res, 1e-6)
            if kind == "filled" and (a < (0.72 if a < 1500 else 0.55) * max(hull, 1e-6) or (a < 900 and fill < 0.7)):
                continue  # lettering, lines that cross, a figure
            per = cv2.arcLength(c, True) * res
            circ = 4 * np.pi * a / max(per * per, 1e-6)
            if circ > 0.84 and fill < 0.86 and a < 4000:
                continue  # a tank
            if fill < 0.45:
                continue  # lettering, a crossing of lines
            if fill > 0.8:
                pts = cv2.boxPoints(((cx, cy), (rw, rh), ang))
            else:
                pts = cv2.approxPolyDP(c, 2.0 / res, True)[:, 0, :].astype(float)
            if len(pts) < 3:
                continue
            poly = [(-half + (px + x0 + 0.5) * res, half - (py + y0 + 0.5) * res) for px, py in pts]
            out.append({"poly": poly, "area": float(a), "kind": kind, "w": float(min(rw, rh) * res), "l": float(max(rw, rh) * res)})
    return out


def height_for(area, kind):
    # single tall storey: sheds, shops, warehouses (not on the maps)
    return (6.0, 1) if area < 500 else (9.0, 1) if area < 3000 else (13.0, 1)


def trace_site(t, sites, log=print):
    sid = t["site_id"]
    if t.get("zone_ll"):
        geom = shapely.union_all([Polygon(r) for r in t["zone_ll"]])
    else:
        geom = sites[sites.site_id == sid].geometry.union_all()
    name = t.get("name") or t.get("label") or sites[sites.site_id == sid].name.iloc[0]
    founded = float(t.get("founded") or sites[sites.site_id == sid].year_start.min())
    closed = t.get("closed")
    if closed is None and len(sites[sites.site_id == sid]):
        ye = float(sites[sites.site_id == sid].year_end.max())
        closed = ye if ye < 9000 else None
    c = geom.centroid
    cx, cy = c.x, c.y
    eds = [e for e in ed.editions(cx, cy, scales=("24000",), bbox=geom.bounds) if e[2]]
    if not eds:
        log(f"{sid}: no 1:24,000 edition")
        return []
    after = [e for e in eds if e[2] >= founded - 1]
    if not after:
        log(f"{sid}: no edition after {founded}")
        return []
    first = after[0]
    tr_eds = [first]
    if closed is None or closed - first[2] > 18:
        later = [e for e in after if e[2] >= first[2] + 10 and (closed is None or e[2] <= closed + 1) and "Photo Revision" not in e[6]]
        if later:
            tr_eds.append(later[0])
    x0, y0 = vt.ll2loc(geom.bounds[0], geom.bounds[1], cx, cy)
    x1, y1 = vt.ll2loc(geom.bounds[2], geom.bounds[3], cx, cy)
    half = float(max(abs(x0), abs(x1), abs(y0), abs(y1)) + 60)
    res = max(1.0, half / 1500.0)
    zone = []
    for poly in (geom.geoms if geom.geom_type == "MultiPolygon" else [geom]):
        x, y = vt.ll2loc(*np.asarray(poly.buffer(0.00012).exterior.coords).T, cx, cy)
        zone.append(list(zip(x, y)))
    traced = []
    for sc, sheet, year, imp, kind, url, yrs in tr_eds:
        try:
            img = vt.render_topo(url, cx, cy, half, res)
        except Exception as e:  # noqa: BLE001
            log(f"{sid}: {sheet} {year}: {e}")
            continue
        syms = symbols(img, half, res, zone)
        (TRACED / f"{sid}_{year}.json").write_text(json.dumps({"site_id": sid, "sheet": sheet, "map_year": year, "url": url,
                                                             "frame": {"lon": cx, "lat": cy}, "res_m": res,
                                                             "symbols": [{"poly": [[round(a, 1), round(b, 1)] for a, b in s["poly"]],
                                                                          "area": round(s["area"]), "kind": s["kind"]} for s in syms]}))
        for s in syms:
            lon, lat = vt.loc2ll(*np.asarray(s["poly"]).T, cx, cy)
            g = Polygon(zip(lon, lat))
            if g.is_valid and not g.is_empty:
                traced.append({"geometry": g, "area_m2": s["area"], "sym": s["kind"], "sheet": sheet, "map_year": year, "url": url})
        log(f"{sid}: {sheet} {year}: {len(syms)} building symbols ({res:.1f} m/px, {2 * half / 1000:.1f} km frame)")
    if not traced:
        return []
    tg = gpd.GeoDataFrame(traced, geometry="geometry", crs=4326)
    # the same structure on both traced editions: keep the first tracing
    keep = np.ones(len(tg), bool)
    tu = tg.to_crs(32610)
    for i in range(len(tg)):
        if not keep[i]:
            continue
        for j in range(i + 1, len(tg)):
            if keep[j] and tg.map_year.values[j] != tg.map_year.values[i]:
                inter = tu.geometry.values[i].intersection(tu.geometry.values[j]).area
                if inter > 0.4 * min(tu.geometry.values[i].area, tu.geometry.values[j].area):
                    keep[j] = False
    tg, tu = tg[keep].reset_index(drop=True), tu[keep].reset_index(drop=True)
    # standing today?
    today = fpm.footprints(geom.buffer(0.0006))
    repl = np.full(len(tg), np.nan)
    standing = np.zeros(len(tg), bool)
    hit_fid = [""] * len(tg)
    if len(today):
        tdu = today.to_crs(32610)
        tree = shapely.STRtree(tdu.geometry.values)
        for i, gm in enumerate(tu.geometry.values):
            # the same building: the symbol and a footprint of today cover each other (a new
            # building on the ground of an old one usually does not: the plate shops of Yard 2
            # lie under the warehouses of the 1980s)
            idx = tree.query(gm.buffer(6.0))
            best, bj = 0.0, -1
            for j in idx:
                fj = tdu.geometry.values[j]
                inter = gm.buffer(6.0).intersection(fj).area
                m = min(inter / max(gm.area, 1.0), inter / max(fj.area, 1.0))
                if m > best:
                    best, bj = m, j
            # (or several footprints of today that together are the symbol: a block of sheds)
            cover = sum(gm.intersection(tdu.geometry.values[j]).area for j in idx if tdu.geometry.values[j].area < 1.3 * gm.area) / max(gm.area, 1.0)
            if best > 0.5 or cover > 0.7:
                # ... unless today's building there is younger than the map: then the symbol is
                # what stood before it (it ends when today's building went up). Years: the live
                # map's, or the edition-dated year of known_dates_industrial.csv for that footprint
                js = [bj] if best > 0.5 else [j for j in idx if gm.intersection(tdu.geometry.values[j]).area > 0.15 * gm.area]
                ys = [KNOWN_Y.get(str(today.fid.values[j]).split(":")[-1][:8], float(today.live_year.values[j])) for j in js]
                ys = [y for y in ys if np.isfinite(y)]
                if ys and min(ys) > float(tg.map_year.values[i]) + 3:
                    repl[i] = min(ys)
                    continue
                standing[i] = True
                hit_fid[i] = str(today.fid.values[bj]) if bj >= 0 else ""
    st = tg[standing].assign(fid=[f for f, s in zip(hit_fid, standing) if s])
    if len(st):
        live = today.set_index(today.fid.astype(str)).live_year
        pd.DataFrame({"site_id": sid, "fid": st.fid.values, "drawn_on": st.sheet.values, "map_year": st.map_year.values,
                      "live_year": [round(float(live.get(f, np.nan)), 1) for f in st.fid.values]}
                     ).drop_duplicates("fid").to_csv(TRACED / f"{sid}_standing.csv", index=False)
    tg["repl"] = repl
    van = tg[~standing].reset_index(drop=True)
    if not len(van):
        log(f"{sid}: every symbol stands today")
        return []
    van["circ"] = fpm._circ(van.to_crs(32610).geometry.values)
    pres = de.presence(geom, van, eds, log=lambda *_: None)
    rows = []
    for fi, r in van.iterrows():
        # the editions (by the year of their culture) that draw this symbol: it stands on the
        # traced edition; forward to the first that does not, back to the last that does not
        cul = pres[pres.fi == fi].groupby("year").present.max()
        yt = int(r.map_year)
        yrs = sorted(set(cul.index) | {yt})
        drawn = {y: (True if y == yt else bool(cul.get(y, False))) for y in yrs}
        last_drawn, gone = yt, None
        for y in [y for y in yrs if y > yt]:
            if drawn[y]:
                last_drawn = y
            else:
                gone = y
                break
        first_drawn, absent = yt, None
        for y in [y for y in reversed(yrs) if y < yt and y >= founded - 1]:
            if drawn[y]:
                first_drawn = y
            else:
                absent = y
                break
        if absent is not None:
            start, sev = max(founded, (absent + first_drawn) / 2.0), f"absent on the {absent} edition, drawn {first_drawn}"
        elif first_drawn - founded <= 15:
            start, sev = founded, f"drawn on the {first_drawn} sheet, the first after the site's founding"
        else:
            start, sev = (founded + first_drawn) / 2.0, f"first drawn {first_drawn}, no earlier 1:24,000 edition"
        if "start" in t:
            start = float(t["start"])
        if gone is not None:
            end, eev = (last_drawn + gone) / 2.0, f"last drawn {last_drawn}, gone on the {gone} edition"
            if closed and last_drawn <= closed <= gone:
                end = float(closed) + 0.5 + 3.0 * ((fi * 0.6180339) % 1.0)
                eev += f"; the site closed {closed:g}"
        else:
            end, eev = (last_drawn + 2012.0) / 2.0, f"drawn to the last edition ({last_drawn}), not in today's footprints"
        if np.isfinite(r.repl) and r.repl - 1.0 < end:
            end, eev = float(r.repl) - 1.0, eev + f"; today's building on its ground dates from {r.repl:.0f}"
        if end <= start + 0.5:
            continue
        h, sto = height_for(r.area_m2, r.sym)
        use = "warehouse" if r.sym == "hatched" or r.area_m2 > 2500 else "factory"
        rows.append({"site_id": sid, "name": f"{t.get('label') or name}: building on the {r.sheet.rsplit(' ', 1)[0]} sheet of {int(r.map_year)}",
                     "start_year": round(start, 2), "end_year": round(end, 2), "height_m": h, "storeys": sto,
                     "material": "steel", "use": use, "confidence": "estimated", "source_url": r.url,
                     "note": f"{r.sym} symbol, {r.area_m2:.0f} m2; start: {sev}; end: {eev}; height estimated (one tall storey)",
                     "geometry": r.geometry})
    log(f"{sid}: {len(rows)} vanished buildings ({int(standing.sum())} symbols stand today)")
    return rows


def main():
    from targets import TARGETS
    sites = gpd.read_file(HERE.parent / "sites.geojson")
    want = set(sys.argv[1:])
    old = gpd.read_file(OUT) if OUT.exists() else None
    rows = []
    done = set()
    for t in TARGETS:
        if want and t["site_id"] not in want:
            continue
        try:
            rows += trace_site(t, sites)
            done.add(t["site_id"])
        except Exception as e:  # noqa: BLE001
            print(f"{t['site_id']}: FAILED {type(e).__name__}: {str(e)[:200]}")
    # zones of neighbouring targets may overlap: a symbol is kept once (the first target's)
    keep, tree_geoms = [], []
    for r in rows:
        g = r["geometry"]
        if any(g.intersects(h) and g.intersection(h).area > 0.4 * min(g.area, h.area) for h in tree_geoms):
            continue
        keep.append(r)
        tree_geoms.append(g)
    if len(keep) < len(rows):
        print(f"{len(rows) - len(keep)} symbols traced twice (overlapping zones) dropped")
    rows = keep
    new = gpd.GeoDataFrame(rows, geometry="geometry", crs=4326) if rows else None
    parts = [d for d in (old[~old.site_id.isin(done)] if old is not None else None, new) if d is not None and len(d)]
    if parts:
        out = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), geometry="geometry", crs=4326)
        out["geometry"] = shapely.set_precision(out.geometry.values, 1e-6)
        out.to_file(OUT, driver="GeoJSON")
        print(f"{len(out)} vanished buildings of {out.site_id.nunique()} sites -> {OUT.name}")


if __name__ == "__main__":
    main()
