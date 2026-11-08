"""Stage (Phase 3): buildings that no longer exist — the pre-1906 city and the
generation of houses that today's buildings replaced.

Modern data only records survivors, so 1880 downtown would be empty. We stand
buildings on SF's *real* lots (parcel lines mostly date from the 19th-century
subdivisions) wherever the researched built-up extents say the block was built:

  * build year: lot inside the first snapshot extent (data/manual/sf_extent_YYYY.csv)
    that contains it -> uniform between the previous snapshot and that year;
  * end year:   inside the 1906 burned area (minus unburned islands) -> 18 Apr 1906;
                elsewhere -> when today's building on the lot was built (it replaced it);
  * after 1906 in the burned area, a rebuilt building stands from 1906–1913 until
    today's building if that is much later;
  * footprint:  the lot, set back/inset per the researched era fabric (row houses
    full width, residential depth ~60 %, downtown ~95 %);
  * height:     storeys per district and era (sf_extent_README.md suggested rules).
All of this is `year_confidence = procedural` (real lots and extents, generated
massing). Documented buildings in data/tables/notable_pre1906.csv are placed on
their lots with researched heights/dates (`estimated`).

Output: data/interim/sf_predecessors.parquet (same columns as sf_buildings)
"""
from __future__ import annotations

import glob
import zlib

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import box

from shapely.geometry import Point

from common import INTERIM, MANUAL, RAW, TABLES, log
from geocode import intersection_rings

UTM = "EPSG:32610"
DOWNTOWN = box(-122.4110, 37.7860, -122.3950, 37.7990)  # fire limits core (approx.)
BURN_REBUILD = (1906.6, 1913.0)


def h01(key: str, salt: str = "") -> float:
    return (zlib.crc32(f"{salt}{key}".encode()) % 100003) / 100003.0


def main():
    lots = gpd.read_parquet(INTERIM / "sf_parcels_active.parquet").to_crs(UTM)
    # condo unit parcels repeat their map parcel's geometry: one lot per map parcel
    lots = lots.drop_duplicates("mapblklot")
    lots = lots[lots.geometry.area.between(40, 20000)].reset_index(drop=True)
    lots = lots[~lots.geometry.centroid.duplicated()].reset_index(drop=True)
    cent = lots.geometry.representative_point()

    # first snapshot containing each lot
    files = sorted(glob.glob(str(MANUAL / "sf_extent_*.csv")))
    dev_hi = np.full(len(lots), np.nan)
    dev_lo = np.full(len(lots), np.nan)
    # documented structures (data/tables/early_sf.csv) cover the town before the gold
    # rush; generated fabric starts with the 1849 boom
    prev = 1849.0
    for f in files:
        year = float(f.split("_")[-1].split(".")[0])
        rings = intersection_rings(f, crs=UTM)
        inside = np.zeros(len(lots), bool)
        for poly in rings.values():
            inside |= cent.within(poly).values
        new = inside & np.isnan(dev_hi)
        dev_hi[new] = year
        dev_lo[new] = prev
        prev = year
    built = np.isfinite(dev_hi)
    # Within a snapshot period, development spread outward from the previous built-up
    # edge and went up a block at a time: lot year = growth front (distance from the
    # earlier extent) blended with a per-block year, plus a little per-lot spread.
    front = np.full(len(lots), 0.5)
    prev_union = None
    for f in files:
        year = float(f.split("_")[-1].split(".")[0])
        rings = intersection_rings(f, crs=UTM)
        cur = shapely.union_all(list(rings.values())) if rings else None
        sel = np.isfinite(dev_hi) & (dev_hi == year)
        if prev_union is not None and sel.any():
            dist = np.array([prev_union.distance(p) for p in cent.values[sel]])
            front[sel] = dist / max(np.percentile(dist, 95), 1.0)
        if cur is not None:
            prev_union = cur if prev_union is None else shapely.union_all([prev_union, cur])
    block = lots.mapblklot.astype(str).str[:4].values
    blk_h = np.array([h01(b_, "blk") for b_ in block])
    lot_t = np.clip(0.6 * np.clip(front, 0, 1) + 0.4 * blk_h, 0, 1)
    log(f"predecessors: {built.sum()} of {len(lots)} lots inside a pre-1906 extent")

    # today's buildings on each lot (earliest start)
    b = gpd.read_parquet(INTERIM / "sf_buildings.parquet").to_crs(UTM)
    bc = gpd.GeoDataFrame({"start": b.start_year.values}, geometry=b.geometry.representative_point(), crs=UTM)
    j = gpd.sjoin(bc, lots[["geometry"]], predicate="within", how="inner")
    modern = j.groupby("index_right").start.min()
    mod = modern.reindex(range(len(lots))).values

    fire = gpd.read_file(INTERIM / "fire_1906.geojson").to_crs(UTM)
    burned = cent.within(shapely.union_all(fire.geometry.values)).values

    # urban-renewal / freeway clearances: the old fabric ends at the clearance, and
    # lots that became plazas or parks get it too
    from sf_buildings import redevelopment_areas
    areas = redevelopment_areas()
    clear = np.full(len(lots), np.nan)
    fabric = np.array([""] * len(lots), dtype=object)
    for poly, cs, ce, fab, _aid in reversed(areas):  # smallest last -> wins
        inside = cent.within(poly).values
        hh = np.array([h01(str(k), "c") for k in lots.mapblklot.values])
        clear[inside] = cs + (ce - cs) * hh[inside]
        fabric[inside] = fab
    log(f"predecessors: {np.isfinite(clear).sum()} lots inside clearance areas")
    # 19th-century cemeteries (landcover_history rows "cem_*"): nothing built until the graves were moved
    no_build_until = np.full(len(lots), -np.inf)
    lc = pd.read_csv(TABLES / "landcover_history.csv")
    from geocode import ring_polygon
    for _, r in lc[lc.area_id.astype(str).str.startswith("cem_") & ~lc.area_id.astype(str).str.endswith("_cleared")].iterrows():
        try:
            poly = ring_polygon(r.ring, r.ring_type, crs=UTM)
        except Exception as e:  # noqa: BLE001
            log(f"predecessors: cemetery {r.area_id}: {e}")
            continue
        no_build_until[cent.within(poly).values] = float(r.year_end)

    lots_sidx = lots.sindex
    rows = []
    for i in np.nonzero(built)[0]:
        key = str(lots.mapblklot.iloc[i])
        h = h01(key)
        dev = dev_lo[i] + (dev_hi[i] - dev_lo[i]) * lot_t[i] + 1.5 * (h - 0.5)
        dev = float(np.clip(dev, dev_lo[i], dev_hi[i]))
        if dev < no_build_until[i]:
            continue  # a cemetery until then; today's buildings came after
        m = mod[i]
        geom = lots.geometry.iloc[i]
        c = cent.iloc[i]
        downtown = DOWNTOWN.contains(gpd.GeoSeries([c], crs=UTM).to_crs(4326).iloc[0])
        cl = clear[i]
        if burned[i]:
            end = 1906.29
        elif np.isfinite(cl) and (np.isnan(m) or m > dev + 3) and fabric[i] != "vacant" and fabric[i] != "rail_yards":
            end = min(cl, m - 0.3) if np.isfinite(m) else cl  # cleared for redevelopment
        elif np.isfinite(m) and m > dev + 3:
            end = m - 0.3  # replaced by today's building
        else:
            continue  # today's building may be the original — nothing to add
        # a big parcel (merged later, or a superblock) held rows of ordinary buildings,
        # not one giant box: put era-typical rows along its street edges instead
        if geom.area > 3500 and not downtown:
            fab = fabric[i] if fabric[i] in STRIP_STYLE else "victorian_rows"
            rows += strips_for_lot(geom, key, fab, lambda hk, dev=dev: dev + 3 * hk, end, lots_sidx,
                                   "sf_extent_procedural", "predecessor_rows")
            if burned[i]:
                rb_end_big = min(m - 0.3, cl) if np.isfinite(cl) and np.isfinite(m) else (cl if np.isfinite(cl) else m - 0.3)
                if np.isfinite(rb_end_big) and rb_end_big > BURN_REBUILD[1] + 5:
                    fab2 = fab if fab in ("residential_hotels", "warehouses") else "mixed"
                    rows += strips_for_lot(geom, key + "r", fab2, lambda hk: BURN_REBUILD[0] + (BURN_REBUILD[1] - BURN_REBUILD[0]) * hk,
                                           rb_end_big, lots_sidx, "sf_rebuild_procedural", "post_fire_rebuild")
            continue
        early = dev < 1853  # gold rush: tents and 1-2 storey wood frame, not built out to the lot lines
        fp = footprint(geom, downtown and not early)
        if fp is None:
            continue
        storeys, storey_h, base = massing(dev, downtown, key)
        # downtown's gold-rush frame buildings burned in the 1849-51 fires and the core
        # rebuilt in brick (fire limits): a second, built-out building from then on
        brick_from = 1851.4 + 7.0 * h01(key, "b") if (early and downtown) else None
        first_end = min(end, brick_from) if brick_from else end
        rows.append({"geometry": fp, "start_year": dev, "end_year": first_end, "height": storeys * storey_h + base,
                     "stories": storeys, "kind": "building", "source": "sf_extent_procedural", "mapblklot": key,
                     "year_confidence": "procedural", "year_reason": "predecessor"})
        if brick_from and brick_from < end - 1:
            fp2 = footprint(geom, True)
            if fp2 is not None:
                st2, sh2, b2 = massing(brick_from, True, key)
                rows.append({"geometry": fp2, "start_year": brick_from, "end_year": end, "height": st2 * sh2 + b2,
                             "stories": st2, "kind": "building", "source": "sf_extent_procedural", "mapblklot": key,
                             "year_confidence": "procedural", "year_reason": "predecessor_brick"})
        # burned-zone rebuild that stood until today's (later) building
        rb_end = min(m - 0.3, cl) if np.isfinite(cl) and np.isfinite(m) else (cl if np.isfinite(cl) else m - 0.3)
        if burned[i] and np.isfinite(rb_end) and rb_end > BURN_REBUILD[1] + 5:
            rb = BURN_REBUILD[0] + (BURN_REBUILD[1] - BURN_REBUILD[0]) * h01(key, "r")
            st = 3 + int(3 * h01(key, "t")) if downtown else 2 + int(2 * h01(key, "t"))
            rows.append({"geometry": fp, "start_year": rb, "end_year": rb_end, "height": st * (4.5 if downtown else 3.6),
                         "stories": st, "kind": "building", "source": "sf_rebuild_procedural", "mapblklot": key,
                         "year_confidence": "procedural", "year_reason": "post_fire_rebuild"})
    rows += superblock_rows(areas, files)
    pred = gpd.GeoDataFrame(rows, crs=UTM)
    log(f"predecessors: {len(pred)} generated buildings ({(pred.source == 'sf_rebuild_procedural').sum()} post-fire rebuilds)")

    notable = notable_buildings(lots)
    if len(notable):
        # the documented building replaces any generated one on its lot for its lifetime
        # a documented building on a lot holds it for its lifetime: generated buildings
        # there start only after it is gone (and none overlap it)
        on_lot = notable[~notable.mapblklot.str.startswith("n:")]
        span = on_lot.groupby("mapblklot").agg(s0=("start_year", "min"), s1=("end_year", "max"))
        pred = pred.join(span, on="mapblklot")
        hit = pred.s0.notna() & (pred.end_year > pred.s0)
        pred.loc[hit, "start_year"] = np.maximum(pred.loc[hit, "start_year"], pred.loc[hit, "s1"])
        pred = pred[~(hit & (pred.start_year >= pred.end_year - 0.5))].drop(columns=["s0", "s1"])
        pred = pd.concat([pred, notable], ignore_index=True)
        log(f"predecessors: {len(notable)} documented buildings (pre-1906, early SF, demolished)")
    pred = gpd.GeoDataFrame(pred, geometry="geometry", crs=UTM)
    pred = apply_sanborn(pred, b, fire, areas)
    pred = pred.to_crs(4326)
    pred["base"] = 0.0
    pred["use"] = pred["use_sanborn"].map(SANBORN_USE).fillna(0).astype(int) if "use_sanborn" in pred else 0
    pred = pred.drop(columns=["use_sanborn"], errors="ignore")
    pred["raw_year"] = 0
    pred["end_year"] = pred.end_year.astype(float)
    pred.to_parquet(INTERIM / "sf_predecessors.parquet")
    log(f"predecessors: wrote {len(pred)} features")


# ---------------------------------------------------------------- Sanborn maps
SANBORN_USE = {"dwelling": 1, "flats": 2, "store": 3, "office": 4, "warehouse": 5, "factory": 5, "shed": 5,
               "rail": 5, "stable": 0, "church": 6, "school": 6, "hall": 6, "hotel": 3}
SANBORN_SKIP = {"wharf", "pier"}


def apply_sanborn(pred, today, fire, areas):
    """Traced Sanborn footprints (data/manual/sanborn/<area>_<map year>.geojson) replace
    the generated fabric in the blocks the sheets cover. The same building on
    consecutive maps (IoU >= 0.5) is one building; it starts at the block's development
    year if it is on the first map (else between the two maps), and ends between maps
    when it is gone from the next one (in the 1906 fire inside the burned area), else
    when today's building on the spot (or a clearance) replaced it. A footprint that is
    today's building (IoU >= 0.5 with one built by then) is left to the modern data."""
    files = sorted(glob.glob(str(MANUAL / "sanborn" / "*_[12][0-9][0-9][0-9].geojson")))
    if not files:
        return pred
    frames = []
    for f in files:
        stem = f.split("/")[-1][:-8]
        area, yr = stem.rsplit("_", 1)
        g = gpd.read_file(f)
        if not len(g):
            continue
        g = g.to_crs(UTM)
        g["area"] = area
        g["map_year"] = float(yr)
        frames.append(g[["area", "map_year", "stories", "material", "use", "geometry"] +
                        [c for c in ("basement", "half_storey", "confidence") if c in g]])
    sb = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=UTM)
    sb = sb[sb.geometry.notna() & sb.geometry.is_valid & (sb.geometry.area > 6)]
    sb = sb[~sb["use"].fillna("").isin(SANBORN_SKIP)].reset_index(drop=True)
    burned_zone = shapely.union_all(fire.geometry.values)
    today_sidx = today.sindex
    t_start = today.start_year.values
    pred_sidx = pred.sindex
    rows, covered = [], []
    for area, A in sb.groupby("area"):
        years = sorted(A.map_year.unique())
        cov_file = MANUAL / "sanborn" / f"{area}_coverage.geojson"
        if cov_file.exists():
            cov = gpd.read_file(cov_file).to_crs(UTM)
            covered.append((shapely.union_all(cov.geometry.values), years[0]))
        else:
            covered.append((shapely.union_all(A.geometry.buffer(15).values), years[0]))
        # chain the same building across consecutive maps
        A = A.reset_index(drop=True)
        nxt = {}
        for y0, y1 in zip(years[:-1], years[1:]):
            a = A[A.map_year == y0]
            b_ = A[A.map_year == y1]
            sidx = b_.sindex
            for i, g in zip(a.index, a.geometry.values):
                best, bi = 0.0, None
                for j in sidx.query(g, predicate="intersects"):
                    h = b_.geometry.values[j]
                    iou = g.intersection(h).area / max(g.union(h).area, 1e-6)
                    if iou > best:
                        best, bi = iou, b_.index[j]
                if best >= 0.5:
                    nxt[i] = bi
        has_prev = set(nxt.values())
        for i in A.index:
            if i in has_prev:
                continue  # part of a chain started on an earlier map
            chain = [i]
            while chain[-1] in nxt:
                chain.append(nxt[chain[-1]])
            first, last = A.loc[chain[0]], A.loc[chain[-1]]
            g = first.geometry
            key = f"{area}:{chain[0]}"
            hk = h01(key)
            fy, ly = first.map_year, last.map_year
            # today's building on the spot
            cand = today_sidx.query(g, predicate="intersects")
            same, later = None, []
            for j in cand:
                tg = today.geometry.values[j]
                inter = g.intersection(tg).area
                iou = inter / max(g.union(tg).area, 1e-6)
                if iou >= 0.5 and t_start[j] <= ly + 2:
                    same = j
                elif inter > 0.2 * g.area and t_start[j] > fy:
                    later.append(t_start[j])
            if same is not None:
                continue  # the building still stands: the modern data has it
            # start
            if fy == years[0]:
                near = pred_sidx.query(g.buffer(25), predicate="intersects")
                st = [pred.start_year.values[j] for j in near if pred.start_year.values[j] < fy]
                start = float(np.median(st)) + 2 * (hk - 0.5) if st else fy - 6 - 6 * hk
                start = min(start, fy - 0.5)
            else:
                prev_y = years[years.index(fy) - 1]
                start = prev_y + (fy - prev_y) * (0.2 + 0.7 * hk)
            # end
            if ly != years[-1]:
                ny = years[years.index(ly) + 1]
                if ly < 1906.29 < ny and g.centroid.within(burned_zone):
                    end = 1906.29
                else:
                    end = ly + (ny - ly) * (0.25 + 0.6 * h01(key, "e"))
            else:
                ends = [x - 0.3 for x in later if x > ly]
                c = g.centroid
                for poly, cs, ce, _fab, _aid in areas:
                    if c.within(poly) and cs > ly:
                        ends.append(cs + (ce - cs) * h01(key, "c"))
                end = min(ends) if ends else max(ly + 15, 1960.0)
            if end <= start + 0.5:
                continue
            stories = float(first.stories) if pd.notna(first.stories) and first.stories > 0 else 2.0
            use = str(first.use or "")
            storey_h = 4.5 if use in ("warehouse", "factory", "rail") else 3.6
            height = stories * storey_h + (1.6 if bool(first.get("half_storey", False)) else 0) + (1.2 if use in ("dwelling", "flats") else 0.6)
            mat = str(first.material or "")
            rows.append({"geometry": g, "start_year": float(start), "end_year": float(end), "height": height,
                         "stories": stories, "kind": "building", "source": f"sanborn_{area}",
                         "mapblklot": key, "material": {"frame": "", "iron": "", "concrete": ""}.get(mat, mat),
                         "use_sanborn": use, "year_confidence": "estimated",
                         "year_reason": f"sanborn_{int(fy)}_{int(ly)}"})
    new = gpd.GeoDataFrame(rows, crs=UTM)
    # the generated fabric gives way inside the mapped blocks (what vanished before the first map stays)
    c = pred.geometry.representative_point()
    drop = np.zeros(len(pred), bool)
    for poly, y_first in covered:
        inside = c.within(poly).values
        gen = pred.source.astype(str).str.endswith("_procedural").values
        drop |= inside & gen & (pred.end_year.values > y_first)
    log(f"predecessors: Sanborn maps: {len(new)} traced buildings from {len(files)} map files; "
        f"{int(drop.sum())} generated buildings replaced")
    out = pd.concat([pred[~drop], new], ignore_index=True)
    return gpd.GeoDataFrame(out, geometry="geometry", crs=UTM)


def massing(year, downtown, key):
    """Storeys, storey height and base for a generated building, per the era rules in
    data/manual/sf_extent_README.md ("Suggested rules"):
      before 1853: tents / 1-2 storey wood frame;
      downtown in the fire limits: brick 2-5 storeys (mostly 3) to 1889, 3-6 after;
      residential: 2 storeys (to 1885), 2-3 after, ~3.6 m storeys over a raised basement."""
    hs = h01(key, "s")
    if year < 1853:
        return (1 if hs < 0.6 else 2), 3.6, 0.6
    if downtown:
        choices = [2, 3, 3, 3, 4, 5] if year < 1890 else [3, 3, 4, 4, 5, 6]
        return choices[int(hs * len(choices))], 4.5, 0.0
    return (2 + int(hs < (0.5 if year > 1885 else 0.15))), 3.6, 1.5


def footprint(lot, downtown):
    """Building on a lot: nearly full coverage downtown, ~60 % depth for houses."""
    g = lot.buffer(-0.4 if downtown else -0.8)
    if g.is_empty:
        return None
    if not downtown:
        # keep the front ~60 %: approximate with a scaled copy anchored on the lot's
        # longer-axis end nearest the street is unknown -> centred shrink along the long axis
        mrr = g.minimum_rotated_rectangle
        coords = np.asarray(mrr.exterior.coords)[:4]
        e1 = coords[1] - coords[0]
        e2 = coords[2] - coords[1]
        long_axis = e1 if np.hypot(*e1) > np.hypot(*e2) else e2
        L = np.hypot(*long_axis)
        if L > 14:
            u = long_axis / L
            cx, cy = np.asarray(g.centroid.coords[0])
            # cut a slab of 60 % of the length, centred slightly toward one end (hash)
            keep = 0.6 * L
            offset = 0.15 * L
            p0 = np.array([cx, cy]) + u * (offset - keep / 2)
            w = 1000
            n = np.array([-u[1], u[0]])
            slab = shapely.geometry.Polygon([p0 - n * w, p0 + n * w, p0 + n * w + u * keep, p0 - n * w + u * keep])
            g = g.intersection(slab)
    if g.is_empty or g.area < 20:
        return None
    if g.geom_type != "Polygon":
        g = max(getattr(g, "geoms", [g]), key=lambda x: x.area)
    return g


STRIP_STYLE = {"victorian_rows": (7.6, 17.0), "residential_hotels": (12.0, 22.0), "warehouses": (18.0, 30.0), "mixed": (9.0, 20.0)}


def strips_for_lot(lot, key, fab, start_fn, end, sidx, source, reason):
    """Rows of era-typical buildings along the street-facing edges of a large lot."""
    width, depth = STRIP_STYLE[fab]
    lot = lot if lot.geom_type == "Polygon" else max(lot.geoms, key=lambda g: g.area)
    ring = lot.exterior
    L = ring.length
    placed, out = [], []
    for k in range(int(L // width)):
        d = (k + 0.5) * width
        p = ring.interpolate(d)
        a = np.array(ring.interpolate(max(d - 1.0, 0)).coords[0])
        b = np.array(ring.interpolate(min(d + 1.0, L)).coords[0])
        t = (b - a) / (np.linalg.norm(b - a) or 1)
        nrm = np.array([-t[1], t[0]])
        pt = np.array(p.coords[0])
        if not lot.contains(Point(*(pt + nrm * 2.0))):
            nrm = -nrm
        # faces a street: just outside this edge there is no other parcel
        if len(sidx.query(Point(*(pt - nrm * 4.0)), predicate="intersects")):
            continue
        c0 = pt + nrm * 0.8
        hw = t * width * 0.46
        rect = shapely.geometry.Polygon([c0 - hw, c0 + hw, c0 + hw + nrm * depth, c0 - hw + nrm * depth])
        if not rect.within(lot.buffer(0.5)) or any(rect.intersection(q).area > 3 for q in placed[-4:]):
            continue
        placed.append(rect)
        hk = h01(key, f"s{k}")
        y0 = start_fn(hk)
        if fab == "victorian_rows":
            st, sh, base = 2 + int(hk < 0.35), 3.6, 1.5
        elif fab == "residential_hotels":
            st, sh, base = 3 + int(2 * hk), 3.6, 0.0
        elif fab == "warehouses":
            st, sh, base = 2 + int(2 * hk), 4.5, 0.0
        else:
            st, sh, base = 2 + int(2 * hk), 3.6, 1.0
        e = end(k) if callable(end) else end
        if e <= y0 + 2:
            continue
        out.append({"geometry": rect, "start_year": y0, "end_year": e, "height": st * sh + base,
                    "stories": st, "kind": "building", "source": source, "mapblklot": f"{key}:{k}",
                    "year_confidence": "procedural", "year_reason": reason})
    return out


def superblock_rows(areas, extent_files):
    """Urban renewal merged whole blocks into superblock parcels, so today's lots don't
    show the old 25-ft lots. Along every street-facing edge of a large parcel inside a
    clearance area, stand a row of era-typical buildings (Victorian rows, residential
    hotels, warehouses) from the block's built-up snapshot until the clearance. Procedural."""
    allp = gpd.read_parquet(INTERIM / "sf_parcels_active.parquet").to_crs(UTM).drop_duplicates("mapblklot")
    allp = allp[allp.geometry.notna()].reset_index(drop=True)
    sidx = allp.sindex
    out = []
    cent = allp.geometry.representative_point()
    for poly, cs, ce, fab, aid in areas:
        if fab not in ("victorian_rows", "residential_hotels", "warehouses", "mixed"):
            continue
        big = allp[(allp.geometry.area > 20000) & cent.within(poly).values]  # smaller ones: main loop
        for j, lot in zip(big.index, big.geometry.values):
            key = str(allp.mapblklot.iloc[j])
            dev = 1880.0 + 20.0 * h01(key, "d")
            start_fn = {"victorian_rows": lambda hk, dev=dev: dev + 6 * hk - 3, "residential_hotels": lambda hk: 1907.0 + 5 * hk,
                        "warehouses": lambda hk: 1907.0 + 20 * hk}.get(fab, lambda hk, dev=dev: dev + 6 * hk)
            out += strips_for_lot(lot, key, fab, start_fn, lambda k, key=key: cs + (ce - cs) * h01(key, f"c{k}"), sidx,
                                  "sf_redevelopment_procedural", f"cleared_{aid}")
    log(f"predecessors: {len(out)} buildings on superblocks of cleared areas")
    return out


def _rect(cx, cy, a, b, ang_deg):
    r = box(cx - a / 2, cy - b / 2, cx + a / 2, cy + b / 2)
    return shapely.affinity.rotate(r, ang_deg, origin=(cx, cy))


# early_sf.csv rows modelled as landmarks (viewer/src/landmarks/batch4.ts: Mission Dolores compound)
EARLY_AS_LANDMARKS = {"mis_convento", "mis_quadrangle_north", "mis_quadrangle_west", "mis_guardhouse",
                      *(f"mis_rancheria_row_{i}" for i in range(1, 9))}

EARLY_DEFAULT_FP = {"tule": (4.0, 4.0), "canvas tent": (4.0, 5.5), "adobe": (12.0, 6.0), "wood frame": (8.0, 6.0),
                    "brick": (12.0, 10.0), "stone": (10.0, 8.0)}


def table_buildings(path, lots, source, embarcadero=None):
    """Documented buildings from a researched table (notable_pre1906 / notable_demolished /
    early_sf columns). Rows with count > 1 are groups scattered over spread_m."""
    if not path.exists():
        return []
    t = pd.read_csv(path)
    t = t[pd.to_numeric(t.start_year, errors="coerce").notna() & t.lat.notna() & t.lon.notna()].reset_index(drop=True)
    if source == "early_sf":
        t = t[~t.id.isin(EARLY_AS_LANDMARKS)].reset_index(drop=True)
    pts = gpd.GeoSeries(gpd.points_from_xy(t.lon, t.lat), crs=4326).to_crs(UTM)
    hits = gpd.sjoin(gpd.GeoDataFrame(geometry=pts), lots[["mapblklot", "geometry"]], predicate="within", how="left")
    hits = hits[~hits.index.duplicated()]
    rows = []
    for i, r in t.iterrows():
        p = pts.iloc[i]
        mat = str(r.get("material", "") or "").strip().lower()
        mat_key = next((k for k in EARLY_DEFAULT_FP if k in mat), "wood frame")
        n = int(pd.to_numeric(r.get("count", 1), errors="coerce") or 1) if "count" in t else 1
        spread = float(pd.to_numeric(r.get("spread_m", 0), errors="coerce") or 0) if "spread_m" in t else 0.0
        fpm = str(r.get("footprint_m", "") or "")
        dims = None
        if "x" in fpm.lower():
            try:
                dims = tuple(float(v) for v in fpm.lower().split("x")[:2])
            except ValueError:
                dims = None
        rot = pd.to_numeric(r.get("rotation_deg", np.nan), errors="coerce")
        lot_i = hits.index_right.iloc[i] if "index_right" in hits else np.nan
        lot = lots.geometry.iloc[int(lot_i)] if pd.notna(lot_i) else None
        if not np.isfinite(rot):
            if "pier" in str(r.id) and embarcadero is not None:
                q = embarcadero.interpolate(embarcadero.project(p))
                rot = 90.0 - np.degrees(np.arctan2(p.y - q.y, p.x - q.x))  # long axis away from the seawall
            elif lot is not None:
                mrr = np.asarray(lot.minimum_rotated_rectangle.exterior.coords)[:4]
                e = mrr[1] - mrr[0]
                rot = 90.0 - np.degrees(np.arctan2(e[1], e[0]))
            else:
                rot = 0.0
        storeys = pd.to_numeric(r.get("storeys"), errors="coerce")
        height = pd.to_numeric(r.get("height_m"), errors="coerce")
        if not np.isfinite(height):
            height = (storeys * (4.5 if mat_key in ("brick", "stone") else 3.6) + 0.6) if np.isfinite(storeys) else (
                {"tule": 2.5, "canvas tent": 2.8, "adobe": 4.5}.get(mat_key, 7.0))
        end = float(r.end_year) if pd.notna(r.end_year) else 9999.0
        rng = np.random.default_rng(zlib.crc32(str(r.id).encode()))
        for k in range(min(n, 1500)):
            if n > 1:
                ang = rng.uniform(0, 2 * np.pi)
                rad = spread * np.sqrt(rng.uniform(0, 1))
                cx, cy = p.x + rad * np.cos(ang), p.y + rad * np.sin(ang)
                a_ = rot + rng.uniform(-12, 12)
            else:
                cx, cy, a_ = p.x, p.y, rot
            if dims is None and lot is not None and n == 1 and source != "early_sf":
                fp = lot.buffer(-0.3)
            else:
                a, b = dims or EARLY_DEFAULT_FP[mat_key]
                # shapely rotates counter-clockwise; our bearing is clockwise from north for the long side
                fp = _rect(cx, cy, b, a, -a_) if mat_key != "tule" else Point(cx, cy).buffer(a / 2, 4)
            if fp is None or fp.is_empty:
                continue
            rows.append({"geometry": fp, "start_year": float(r.start_year) + (rng.uniform(0, 0.8) if n > 1 else 0.0), "end_year": end,
                         "height": float(height), "stories": float(storeys) if np.isfinite(storeys) else np.nan, "kind": "building",
                         "source": source, "material": mat_key,
                         "mapblklot": str(lots.mapblklot.iloc[int(lot_i)]) if (pd.notna(lot_i) and n == 1) else f"n:{r.id}:{k}",
                         "year_confidence": "procedural" if n > 1 else "estimated", "year_reason": "documented"})
    return rows


def notable_buildings(lots):
    """Documented buildings: pre-1906 notables, demolished post-1906 buildings, and the
    structures of the town before the gold rush (data/tables/early_sf.csv)."""
    emb = None
    try:
        st = gpd.GeoDataFrame(pd.concat([gpd.read_file(f) for f in glob.glob(str(RAW / "sf_streets_classes" / "page-*.geojson"))]), crs=4326)
        e = st[st.street.fillna("").str.upper().str.contains("EMBARCADERO")].to_crs(UTM)
        emb = shapely.ops.linemerge(shapely.union_all(e.geometry.values))
    except Exception as ex:  # noqa: BLE001
        log(f"predecessors: no Embarcadero line ({ex})")
    rows = []
    rows += table_buildings(TABLES / "notable_pre1906.csv", lots, "notable_pre1906", emb)
    rows += table_buildings(TABLES / "notable_demolished.csv", lots, "notable_demolished", emb)
    rows += table_buildings(TABLES / "early_sf.csv", lots, "early_sf", emb)
    return gpd.GeoDataFrame(rows, crs=UTM) if rows else gpd.GeoDataFrame()


def _old_notable_buildings(lots):
    path = TABLES / "notable_pre1906.csv"
    if not path.exists():
        return gpd.GeoDataFrame()
    t = pd.read_csv(path)
    t = t[pd.to_numeric(t.start_year, errors="coerce").notna() & t.lat.notna() & t.lon.notna()]
    pts = gpd.GeoDataFrame(t, geometry=gpd.points_from_xy(t.lon, t.lat), crs=4326).to_crs(UTM)
    j = gpd.sjoin(pts, lots[["mapblklot", "geometry"]], predicate="within", how="left")
    rows = []
    for _, r in j.iterrows():
        lot = lots.geometry.iloc[int(r.index_right)] if pd.notna(r.index_right) else r.geometry.buffer(15, cap_style=3)
        fp = lot.buffer(-0.3)
        if pd.notna(r.get("footprint_m")) and "x" in str(r.footprint_m):
            try:
                a, b = (float(v) for v in str(r.footprint_m).lower().split("x")[:2])
                rect = shapely.affinity.scale(lot.minimum_rotated_rectangle, 1, 1)
                # keep the lot orientation, size to the documented footprint when smaller than the lot
                if a * b < lot.area * 1.3:
                    c = lot.centroid
                    mrr = np.asarray(lot.minimum_rotated_rectangle.exterior.coords)[:4]
                    ang = np.degrees(np.arctan2(*(mrr[1] - mrr[0])[::-1]))
                    fp = shapely.affinity.rotate(box(c.x - a / 2, c.y - b / 2, c.x + a / 2, c.y + b / 2), ang, origin=c)
                del rect
            except ValueError:
                pass
        height = float(r.height_m) if pd.notna(r.get("height_m")) else (float(r.storeys) * 4.5 if pd.notna(r.get("storeys")) else 15.0)
        end = float(r.end_year) if pd.notna(r.end_year) else 9999.0
        rows.append({"geometry": fp, "start_year": float(r.start_year), "end_year": end, "height": height,
                     "stories": float(r.storeys) if pd.notna(r.get("storeys")) else np.nan, "kind": "building",
                     "source": "notable_pre1906", "mapblklot": str(r.mapblklot) if pd.notna(r.get("mapblklot")) else f"n:{r.id}",
                     "year_confidence": "estimated", "year_reason": "documented"})
    return gpd.GeoDataFrame(rows, crs=UTM)


if __name__ == "__main__":
    main()
