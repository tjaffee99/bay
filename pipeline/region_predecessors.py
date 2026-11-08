"""Vanished buildings of the five counties (called by region_buildings.py).

Real first: footprints traced from the LOC Sanborn maps for Oakland, San José, …
(data/manual/sanborn/<area>_<year>.geojson with a region prefix — see REGION_SANBORN),
matched between map years and dated exactly as in San Francisco (sf_predecessors.
apply_sanborn); they replace generated buildings inside the mapped blocks.

Generated where the evidence says something older stood (`year_confidence =
procedural`): on a real parcel (county / city parcel layers in region_years.parquet)
whose neighbourhood was built up before 1945 (25th percentile of the years of the
buildings within 150 m), when today's building on it is 25+ years younger than that and
most buildings around are older than it — i.e. a replacement in a built-out
neighbourhood, not the first building on a farm or an infill lot in a post-war tract.
The predecessor stands from the neighbourhood's development year until today's
building (or a redevelopment / freeway clearance in data/manual/redevelopment_areas.csv)
replaced it; massing by era as for pre-1906 SF (houses of 2-3 storeys, brick commercial
blocks where the neighbourhood is tall, warehouses in industrial areas; big lots get
rows of buildings along their street edges).
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from scipy.spatial import cKDTree

from common import INTERIM, TABLES, log
from sf_predecessors import apply_sanborn, footprint, h01, massing, strips_for_lot, table_buildings

UTM = "EPSG:32610"
REGION_SANBORN = ("oakland", "san_jose", "berkeley", "alameda", "richmond", "san_rafael", "palo_alto",
                  "santa_clara", "hayward", "redwood_city", "san_mateo")


def load_lots():
    ry = gpd.read_parquet(INTERIM / "region_years.parquet", columns=["src", "kind", "geometry"])
    lots = ry[(ry.kind == "parcel") & ry.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
    lots = lots.to_crs(UTM)
    lots = lots.explode(index_parts=False)
    lots = lots[lots.geometry.geom_type == "Polygon"]
    a = lots.geometry.area.values
    lots = lots[(a > 40) & (a < 20000)]
    c = lots.geometry.representative_point()
    key = (np.round(c.x.values, 0).astype(np.int64) * 10_000_000 + np.round(c.y.values, 0).astype(np.int64))
    lots = lots.assign(_k=key).drop_duplicates("_k").drop(columns="_k").reset_index(drop=True)
    return lots[["src", "geometry"]]


def generated(today, areas):
    """today: GeoDataFrame (EPSG:4326) of today's region buildings with start_year, height, use."""
    lots = load_lots()
    tu = today.to_crs(UTM)
    pts = gpd.GeoDataFrame({"start": today.start_year.values, "h": today.height.values, "use": today.use.values},
                           geometry=tu.geometry.representative_point().values, crs=UTM)
    j = gpd.sjoin(pts, lots[["geometry"]], predicate="within", how="inner")
    per = j.groupby("index_right").agg(m=("start", "min"), n=("start", "size"), use=("use", "max"))
    lots = lots.join(per, how="inner")
    log(f"region predecessors: {len(lots)} lots with a building today")
    # neighbourhood evidence from today's buildings within 150 m
    xy = np.column_stack([pts.geometry.x.values, pts.geometry.y.values])
    tree = cKDTree(xy)
    ys, hs = pts.start.values, pts.h.values
    lc = lots.geometry.representative_point()
    lxy = np.column_stack([lc.x.values, lc.y.values])
    d, idx = tree.query(lxy, k=40, distance_upper_bound=150)
    ok = np.isfinite(d)
    idx = np.minimum(idx, len(ys) - 1)
    ny = np.where(ok, ys[idx], np.nan)
    nh = np.where(ok, hs[idx], np.nan)
    with np.errstate(all="ignore"):
        dev = np.nanpercentile(ny, 25, axis=1)
        med_h = np.nanmedian(nh, axis=1)
        older = np.nanmean(ny < (lots.m.values[:, None] - 20), axis=1)
        nn = ok.sum(axis=1)
    cand = (nn >= 8) & (dev < 1945) & (lots.m.values - dev > 25) & (older >= 0.6)
    log(f"region predecessors: {cand.sum()} lots replaced a building from a built-out neighbourhood")
    sidx = lots.sindex
    rows = []
    for i in np.nonzero(cand)[0]:
        lot = lots.geometry.values[i]
        key = f"r{int(lxy[i, 0])}_{int(lxy[i, 1])}"
        hk = h01(key)
        start = float(dev[i]) + 6 * hk
        end = float(lots.m.values[i]) - 0.3
        c = lc.values[i]
        for poly, cs, ce, fab, _aid in areas:
            if cs > start + 2 and c.within(poly):
                end = min(end, cs + (ce - cs) * h01(key, "c"))
        if end <= start + 3:
            continue
        industrial = int(lots.use.values[i]) == 5
        downtown = med_h[i] > 11
        if lot.area > 1500:
            fab = "warehouses" if industrial else ("victorian_rows" if start < 1906 and not downtown else "mixed")
            rows += strips_for_lot(lot, key, fab, lambda h, s=start: s + 3 * h, end, sidx, "region_procedural",
                                   "predecessor_region")
            continue
        fp = footprint(lot, downtown or industrial)
        if fp is None:
            continue
        st, sh, base = massing(start, downtown, key)
        if industrial:
            st, sh, base = 1 + int(2 * hk), 4.5, 0.8
        rows.append({"geometry": fp, "start_year": start, "end_year": end, "height": st * sh + base, "stories": st,
                     "kind": "building", "source": "region_procedural", "mapblklot": key,
                     "use_sanborn": "warehouse" if industrial else "dwelling",
                     "year_confidence": "procedural", "year_reason": "predecessor_region"})
    out = gpd.GeoDataFrame(rows, geometry="geometry", crs=UTM) if rows else gpd.GeoDataFrame(geometry=[], crs=UTM)
    log(f"region predecessors: {len(out)} generated buildings")
    return out


def clearance_fill(areas, today_utm, pred_utm):
    """Freeway corridors and renewal areas whose parcels are gone (I-980, the Cypress
    viaduct, SR-87, I-280, Acorn, …) have no lots to stand predecessors on, and the
    Sanborn tracing covers only part of them. Where neither today's buildings nor traced /
    generated predecessors cover the ground, stand rows of houses on a block grid aligned
    with the surrounding streets (lots 8 m wide, two 30 m rows back to back, 20 m
    streets), from the neighbourhood's development year until the clearance. Procedural."""
    from download_overture import RELEASE
    from common import RAW
    region_areas = [a for a in areas if a[4].startswith(("oak_", "sj_")) and a[3] not in ("vacant", "rail_yards")]
    if not region_areas:
        return gpd.GeoDataFrame(geometry=[], crs=UTM)
    bb = shapely.union_all([a[0] for a in region_areas]).buffer(600)
    roads = []
    for f in ("roads_local.parquet", "roads_region.parquet"):
        p = RAW / "overture" / RELEASE / f
        if p.exists():
            r = gpd.read_parquet(p, columns=["geometry"])
            r = (r if r.crs else r.set_crs(4326)).to_crs(UTM)
            roads.append(r[r.intersects(bb)])
    roads = pd.concat(roads, ignore_index=True) if roads else gpd.GeoDataFrame(geometry=[], crs=UTM)
    tg = today_utm.geometry.values
    tsidx = today_utm.sindex
    psidx = pred_utm.sindex if len(pred_utm) else None
    ty = today_utm.start_year.values.astype(float)
    tc = np.column_stack([today_utm.geometry.representative_point().x.values, today_utm.geometry.representative_point().y.values])
    ttree = cKDTree(tc)
    rows = []
    for poly, cs, ce, fab, aid in region_areas:
        # dominant street direction around the area (bearings mod 90 deg, length-weighted)
        near = roads[roads.intersects(poly.buffer(400))]
        ang, wts = [], []
        for g in near.geometry.values:
            c = np.asarray(g.coords)
            d = np.diff(c, axis=0)
            ang += list(np.degrees(np.arctan2(d[:, 1], d[:, 0])) % 90)
            wts += list(np.hypot(d[:, 0], d[:, 1]))
        if not ang:
            continue
        hist, edges = np.histogram(ang, bins=90, range=(0, 90), weights=wts)
        theta = np.radians(edges[np.argmax(hist)] + 0.5)
        # development year: early quartile of the buildings around that predate the clearance
        ctr = poly.representative_point()
        idx = ttree.query_ball_point([ctr.x, ctr.y], 500)
        yrs = ty[idx] if len(idx) else np.array([])
        yrs = yrs[yrs < cs]
        dev = float(np.percentile(yrs, 25)) if len(yrs) >= 10 else 1890.0
        cu, su = np.cos(theta), np.sin(theta)
        x0, y0, x1, y1 = poly.bounds
        R = np.hypot(x1 - x0, y1 - y0) / 2 + 100
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for vb in np.arange(-R, R, 80.0):                 # block bands across (v)
            for front, sgn in ((vb + 10.0, 1), (vb + 70.0, -1)):
                for ub in np.arange(-R, R, 140.0):        # blocks along (u), 20 m cross streets
                    for k in range(15):
                        u = ub + 4.0 + 8.0 * k
                        v = front + sgn * 7.0
                        px, py = cx + u * cu - v * su, cy + u * su + v * cu
                        pt = shapely.Point(px, py)
                        if not poly.contains(pt):
                            continue
                        rect = shapely.affinity.rotate(shapely.box(px - 3.5, py - 7.0, px + 3.5, py + 7.0),
                                                       np.degrees(theta) - 90.0, origin=(px, py))
                        if len(tsidx.query(rect.buffer(4.0), predicate="intersects")):
                            continue
                        if psidx is not None and len(psidx.query(rect.buffer(3.0), predicate="intersects")):
                            continue
                        key = f"cf_{aid}_{int(px)}_{int(py)}"
                        h = h01(key)
                        start = dev + 10.0 * h
                        end = cs + (ce - cs) * h01(key, "c")
                        if end <= start + 3:
                            continue
                        st = 1 + int(h01(key, "s") < 0.7)
                        rows.append({"geometry": rect, "start_year": start, "end_year": end, "height": st * 3.4 + 2.2,
                                     "stories": st, "kind": "building", "source": "region_procedural", "mapblklot": key,
                                     "use_sanborn": "dwelling", "year_confidence": "procedural",
                                     "year_reason": f"cleared_{aid}"})
    out = gpd.GeoDataFrame(rows, geometry="geometry", crs=UTM) if rows else gpd.GeoDataFrame(geometry=[], crs=UTM)
    log(f"region predecessors: {len(out)} houses stood where clearances left no parcels")
    return out


def region_predecessors(today):
    """All vanished buildings for the region (EPSG:4326): generated + traced (Sanborn)."""
    from sf_buildings import redevelopment_areas
    areas = redevelopment_areas()
    pred = generated(today, areas)
    # documented demolished buildings (data/tables/notable_demolished_region.csv): on their
    # parcel, or their traced Sanborn outline when the row points at one (apply_sanborn)
    lots = load_lots()
    lots["mapblklot"] = [f"rl{i}" for i in range(len(lots))]
    doc = table_buildings(TABLES / "notable_demolished_region.csv", lots, "notable_demolished_region")
    if doc:
        d = gpd.GeoDataFrame(doc, geometry="geometry", crs=UTM)
        d["use_sanborn"] = "dwelling"
        pred = gpd.GeoDataFrame(pd.concat([pred, d], ignore_index=True), geometry="geometry", crs=UTM)
        log(f"region predecessors: {len(d)} documented demolished buildings")
    tu = today.to_crs(UTM).reset_index(drop=True)
    no_fire = gpd.GeoDataFrame(geometry=[], crs=UTM)
    pred = apply_sanborn(pred, tu, no_fire, areas, include=lambda area: area.startswith(REGION_SANBORN))
    # buildings of vanished large sites (data/manual/vanished_sites/buildings.geojson:
    # traced from aerials / topo maps — racetrack grandstands, office campuses, factories)
    vb = INTERIM.parent / "manual" / "vanished_sites" / "buildings.geojson"
    if vb.exists():
        v = gpd.read_file(vb).to_crs(UTM)
        v = v[v.geometry.notna() & v.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].explode(index_parts=False)
        USE = {"dwelling": "dwelling", "office": "office", "factory": "factory", "warehouse": "warehouse",
               "grandstand": "hall", "hall": "hall", "other": "shed"}
        rows = []
        for k, r in enumerate(v.itertuples()):
            y0 = pd.to_numeric(getattr(r, "start_year", np.nan), errors="coerce")
            y1 = pd.to_numeric(getattr(r, "end_year", np.nan), errors="coerce")
            if not np.isfinite(y0):
                continue
            hgt = pd.to_numeric(getattr(r, "height_m", np.nan), errors="coerce")
            sto = pd.to_numeric(getattr(r, "storeys", np.nan), errors="coerce")
            if not np.isfinite(hgt):
                hgt = (sto if np.isfinite(sto) else 1) * 4.0 + 1.0
            mat = str(getattr(r, "material", "") or "").lower()
            rows.append({"geometry": r.geometry, "start_year": float(y0), "end_year": float(y1) if np.isfinite(y1) else 9999.0,
                         "height": float(hgt), "stories": float(sto) if np.isfinite(sto) else np.nan, "kind": "building",
                         "source": "vanished_site", "mapblklot": f"vs_{getattr(r, 'site_id', 'x')}_{k}",
                         "material": "brick" if "brick" in mat else "",
                         "use_sanborn": USE.get(str(getattr(r, "use", "other")), "shed"),
                         "year_confidence": "estimated", "year_reason": f"vanished_site:{getattr(r, 'site_id', '')}"})
        if rows:
            pred = gpd.GeoDataFrame(pd.concat([pred, gpd.GeoDataFrame(rows, geometry="geometry", crs=UTM)], ignore_index=True),
                                    geometry="geometry", crs=UTM)
            log(f"region predecessors: {len(rows)} buildings of vanished large sites")
    cf = clearance_fill(areas, tu, pred)
    if len(cf):
        pred = gpd.GeoDataFrame(pd.concat([pred, cf], ignore_index=True), geometry="geometry", crs=UTM)
    pred = pred.to_crs(4326)
    use_map = {"dwelling": 1, "flats": 2, "store": 3, "office": 4, "warehouse": 5, "factory": 5, "shed": 5,
               "rail": 5, "stable": 0, "church": 6, "school": 6, "hall": 6, "hotel": 3}
    pred["use"] = pred.get("use_sanborn", pd.Series(index=pred.index, dtype=object)).map(use_map).fillna(0).astype(int) \
        if len(pred) else 0
    return pred
