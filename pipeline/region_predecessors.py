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

import os

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from scipy.spatial import cKDTree

from common import INTERIM, MANUAL, TABLES, log
from sf_predecessors import apply_sanborn, footprint, h01, massing, strips_for_lot, table_buildings

UTM = "EPSG:32610"
REGION_SANBORN = ("oakland", "san_jose", "berkeley", "alameda", "richmond", "san_rafael", "palo_alto",
                  "santa_clara", "hayward", "redwood_city", "san_mateo",
                  # the new counties (pipeline/sanborn_trace_newcounties.py, README_northbay.md / README_santa_cruz.md)
                  "santa_rosa", "vallejo", "napa", "santa_cruz", "petaluma", "watsonville", "benicia")


def load_lots():
    # parcels only (the table also holds ~2 M building points), and no second name for the
    # lon/lat frame: with nine counties (2.6 M parcels) each copy of the geometry is > 1 GB
    lots = gpd.read_parquet(INTERIM / "region_years.parquet", columns=["src", "kind", "geometry"],
                            filters=[("kind", "==", "parcel")])
    lots = lots[lots.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
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


class TownGrowth:
    """When a spot of a town was first built on (owner, 2026-11: "Oakland isn't built up early enough").

    The built-up snapshots (data/manual/region_extents) only bracket it: unbuilt on the last earlier map
    that covers the spot (y0), built on the first that shows it (y1). Inside a bracket the old rule drew
    a date per block at random between 25 % and 90 % of the way, and before a town's first snapshot it
    assumed the 25 years before it - Oakland, first mapped for this in 1894, began in 1869 and held 68
    buildings in 1870, when the census counted 10,500 people. Now:
      * the bracket before the first snapshot starts when the town did (`since`: data/tables/town_since.csv,
        else 8 years before its first census count, never later than 25 years before the snapshot);
      * inside a bracket the buildings go up in step with the town's census population
        (data/tables/population_places.csv, read between the counts; a town without counts: evenly);
      * in the order of a growth front: the blocks nearest the town of the earlier snapshots first
        (distance from the block to everything already built, with ~90 m of noise so the edge is ragged).
    A snapshot of kind "buildings" (a survey that draws every house: the 1856 plane-table sheet of
    Oakland) only says what stood - its houses are added as buildings (tsheet_buildings); a lot
    without one was empty that year. Procedural dates on real evidence."""

    def __init__(self):
        import glob
        import re
        from pathlib import Path
        d = INTERIM.parent / "manual" / "region_extents"
        files = sorted(f for f in glob.glob(str(d / "*.geojson")) if re.fullmatch(r"[a-z_]+_\d{4}", Path(f).stem))
        self.snaps: dict = {}
        for f in files:
            g = gpd.read_file(f)
            if not len(g) or "year" not in g:
                continue
            town = str(g["town"].iloc[0]) if "town" in g else Path(f).stem.rsplit("_", 1)[0]
            y = float(pd.to_numeric(g["year"], errors="coerce").iloc[0])
            if not np.isfinite(y):
                continue
            exact = "kind" in g and str(g["kind"].iloc[0]) == "buildings"
            self.snaps.setdefault(town, []).append((y, shapely.union_all(g.to_crs(UTM).geometry.values), exact))
        for lst in self.snaps.values():
            lst.sort(key=lambda t: t[0])
        self.bounds = {t: shapely.union_all([p for _, p, _ in lst]).bounds for t, lst in self.snaps.items()}
        # what each snapshot's map sheets cover (a lot outside it says nothing about that year)
        self.cov: dict = {}
        cp = d / "coverage.geojson"
        if cp.exists():
            cg = gpd.read_file(cp).to_crs(UTM)
            for t_, y_, gm in zip(cg["town"].astype(str), pd.to_numeric(cg["year"], errors="coerce"), cg.geometry):
                self.cov[(t_, float(y_))] = gm
        pop = pd.read_csv(TABLES / "population_places.csv")
        pop = pop[pop.kind.isin(["city", "town", "cdp"]) & (pop.year >= 1850)]
        norm = lambda n: str(n).lower().replace("é", "e").replace(".", "").replace(" ", "_")  # noqa: E731
        series = {k: v.sort_values("year") for k, v in pop.assign(_t=pop.place.map(norm)).groupby("_t")}
        sp = TABLES / "town_since.csv"
        table = dict(zip(*[pd.read_csv(sp)[c] for c in ("town", "since")])) if sp.exists() else {}
        self.since, self.curve = {}, {}
        for town, lst in self.snaps.items():
            first = lst[0][0]
            ser = series.get(town)
            if town in table:
                since = float(table[town])
            elif ser is not None and len(ser):
                since = min(first - 25.0, max(1847.0, float(ser.year.iloc[0]) - 8.0))
            else:
                since = first - 25.0
            self.since[town] = since
            if ser is not None and len(ser):
                ys = np.r_[since, ser.year.values[ser.year.values > since]].astype(float)
                ps = np.r_[0.0, ser.population.values[ser.year.values > since]].astype(float)
                self.curve[town] = (ys, np.maximum.accumulate(ps))      # a town that shrinks builds nothing new
        self.groups: dict = {}

    def bracket(self, town, inside, covered):
        """(k1, y0, y1) of a spot from its row of the inside / covered tables; None if on no snapshot."""
        lst = self.snaps[town]
        hit = [k for k in range(len(lst)) if inside[k] and not lst[k][2]]
        if not hit:
            return None
        k1 = hit[0]
        prev = [lst[k][0] for k in range(k1) if covered[k]]
        return k1, (prev[-1] if prev else min(self.since[town], lst[k1][0] - 1.0)), lst[k1][0]

    def before(self, town, y0):
        """The town already built at y0: every earlier snapshot, else the middle of its first one."""
        lst = self.snaps[town]
        g = [p for y, p, _ in lst if y <= y0 + 0.01 and not p.is_empty]
        if g:
            return shapely.union_all(g)
        p = next(p for _, p, _ in lst if not p.is_empty)
        return max(shapely.get_parts(p), key=lambda q: q.area).representative_point().buffer(150)

    def year(self, town, y0, y1, u):
        """Year at share u of the bracket's growth (census curve; 15 % of it evenly, so no year is empty)."""
        t = np.linspace(y0, y1, 400)
        f = (t - y0) / (y1 - y0)
        if town in self.curve:
            ys, ps = self.curve[town]
            pt = np.interp(t, ys, ps)
            if pt[-1] - pt[0] > 0:
                f = 0.85 * (pt - pt[0]) / (pt[-1] - pt[0]) + 0.15 * f
        return float(np.interp(u, f, t))

    @staticmethod
    def tau(geom, x, y):
        bx, by = x // 120, y // 120
        d = shapely.distance(shapely.points(bx * 120 + 60, by * 120 + 60), geom)
        return d + 90.0 * (np.array([h01(f"b{int(i)}_{int(j)}", "grow") for i, j in zip(bx, by)]) - 0.5)

    def dev_year(self, x, y, key):
        """First-building year of any spot (for traced buildings that stand on a town's first map), or None."""
        for town, lst in self.snaps.items():
            b = self.bounds[town]
            if not (b[0] <= x <= b[2] and b[1] <= y <= b[3]):
                continue
            inside = [p.contains(shapely.Point(x, y)) for _, p, _ in lst]
            if not any(inside):
                continue
            covered = [(self.cov[(town, yk)].contains(shapely.Point(x, y)) if (town, yk) in self.cov else True) for yk, _, _ in lst]
            br = self.bracket(town, inside, covered)
            if br is None:
                continue
            _, y0, y1 = br
            g = self.groups.get((town, y1))
            if g is None:
                return y0 + (y1 - y0) * (0.25 + 0.65 * h01(key, "grow"))
            t = float(self.tau(g[1], np.array([x]), np.array([y]))[0])
            u = (np.searchsorted(g[2], t) + 0.5) / (len(g[2]) + 1)
            yr = self.year(town, min(g[0], y1 - 1.0), y1, 0.03 + 0.94 * u) + 1.5 * (h01(key, "lot") - 0.5)
            return float(np.clip(yr, y0 + 0.3, y1 - 0.3))
        return None


def extent_fill(today, pred, areas, lots=None, growth=None):
    """Built-up extent snapshots (data/manual/region_extents/<town>_<year>.geojson: where a
    town was built up at a map's date, digitised from USGS topo editions / Sanborn key maps /
    Coast Survey sheets; README there). Inside a snapshot, a parcel whose building today is
    younger than the snapshot had an older building: an era-typical predecessor (same massing
    rules as pre-1906 SF) stands from when its block was built - between the last earlier map
    that shows it unbuilt and the first that shows it built, dated by the town's growth
    (TownGrowth: census curve, nearest the older town first, whole blocks together) - until
    today's building replaced it (or a clearance). Vacant parcels inside a snapshot keep their
    predecessor until 10 years after the last snapshot showing them built. Parcels already
    carrying a predecessor (generated, documented, a house of the 1856 survey) are left alone;
    Sanborn tracings replace these inside their coverage. Procedural."""
    growth = TownGrowth() if growth is None else growth
    snaps = growth.snaps
    empty = gpd.GeoDataFrame(geometry=[], crs=UTM)
    if not snaps:
        return empty
    cov = growth.cov
    lots = load_lots() if lots is None else lots
    tu = today.to_crs(UTM)
    tp = gpd.GeoDataFrame({"start": tu.start_year.values, "h": tu.height.values, "use": tu.use.values},
                          geometry=tu.geometry.representative_point().values, crs=UTM)
    j = gpd.sjoin(tp, lots[["geometry"]], predicate="within", how="inner")
    per = j.groupby("index_right").agg(m=("start", "min"), use=("use", "max"))
    lots = lots.join(per, how="left")
    lc = lots.geometry.representative_point()
    lxy = np.column_stack([lc.x.values, lc.y.values])
    hs = tp.h.values
    ttree = cKDTree(np.column_stack([tp.geometry.x.values, tp.geometry.y.values]))
    psidx = pred.sindex if len(pred) else None
    sidx = lots.sindex
    rows = []
    n_lots = 0
    for town, lst in snaps.items():
        years = [y for y, _, _ in lst]
        inside = np.zeros((len(lst), len(lots)), bool)
        covered = np.ones((len(lst), len(lots)), bool)
        for k, (yk, poly, _exact) in enumerate(lst):
            shapely.prepare(poly)
            cand = sidx.query(poly, predicate="intersects")
            inside[k, cand] = shapely.contains_xy(poly, lxy[cand, 0], lxy[cand, 1])
            cgm = cov.get((town, yk))
            if cgm is not None:
                shapely.prepare(cgm)
                covered[k] = False
                cc = sidx.query(cgm, predicate="intersects")
                covered[k, cc] = shapely.contains_xy(cgm, lxy[cc, 0], lxy[cc, 1])
        # every lot of the town on a snapshot: its bracket, then its place in the bracket's growth front
        br = {}
        for i in np.nonzero(inside.any(axis=0))[0]:
            b = growth.bracket(town, inside[:, i], covered[:, i])
            if b is not None:
                br[int(i)] = b
        # lots first shown built on the same map form one growth front, measured from the town of the
        # last map before it that most of them were on (sheets differ in what they cover)
        share, front0 = {}, {}
        by_group: dict = {}
        for i, (_k1, y0, y1) in br.items():
            by_group.setdefault(y1, []).append(i)
        for y1, ii in by_group.items():
            ii = np.array(ii)
            y0s = np.array([br[int(i)][1] for i in ii])
            vals, cnt = np.unique(y0s, return_counts=True)
            Y0 = float(vals[np.argmax(cnt)])
            geom = growth.before(town, Y0)
            tau = growth.tau(geom, lxy[ii, 0], lxy[ii, 1])
            order = np.argsort(tau, kind="stable")
            u = np.empty(len(ii))
            u[order] = (np.arange(len(ii)) + 0.5) / len(ii)
            share.update(zip(ii.tolist(), u.tolist()))
            front0.update((int(i), Y0) for i in ii)
            growth.groups[(town, y1)] = (Y0, geom, np.sort(tau))
        for i, (k1, y0, y1) in br.items():
            m = lots.m.values[i]
            # today's building already there (or put up within ~15 years: infill of a block
            # that was mostly built, not a replacement): it is the lot's first building
            if np.isfinite(m) and m <= y1 + 15:
                continue
            lot = lots.geometry.values[i]
            if psidx is not None and len(psidx.query(lot.buffer(-1.0), predicate="intersects")):
                continue          # already has a predecessor (generated / documented / corridor)
            key = f"x{int(lxy[i, 0])}_{int(lxy[i, 1])}"
            start = growth.year(town, min(front0[i], y1 - 1.0), y1, 0.03 + 0.94 * share[i]) + 1.5 * (h01(key, "lot") - 0.5)
            start = float(np.clip(start, y0 + 0.3, y1 - 0.3))
            if np.isfinite(m):
                end = m - 0.3
            else:
                last = max(years[k] for k in range(len(lst)) if inside[k, i])
                end = min(last + 10.0, 2005.0)
            c = lc.values[i]
            for poly, cs, ce, fab, _aid in areas:
                if cs > start + 2 and c.within(poly):
                    end = min(end, cs + (ce - cs) * h01(key, "c"))
            if end <= start + 3:
                continue
            d, idx = ttree.query(lxy[i], k=20, distance_upper_bound=150)
            ok = np.isfinite(d)
            med_h = float(np.median(hs[idx[ok]])) if ok.any() else 6.0
            downtown = med_h > 11
            industrial = int(np.nan_to_num(lots.use.values[i], nan=0)) == 5
            n_lots += 1
            if lot.area > 1500:
                fab_ = "warehouses" if industrial else ("victorian_rows" if start < 1906 and not downtown else "mixed")
                rows += strips_for_lot(lot, key, fab_, lambda hh, s0=start: s0 + 3 * hh, end, sidx, "region_procedural",
                                       "predecessor_extent")
                continue
            fp = footprint(lot, downtown or industrial)
            if fp is None:
                continue
            st, sh, base = massing(start, downtown, key)
            if industrial:
                st, sh, base = 1 + int(2 * h01(key)), 4.5, 0.8
            rows.append({"geometry": fp, "start_year": start, "end_year": end, "height": st * sh + base, "stories": st,
                         "kind": "building", "source": "region_procedural", "mapblklot": key,
                         "use_sanborn": "warehouse" if industrial else "dwelling",
                         "year_confidence": "procedural", "year_reason": f"predecessor_extent:{town}_{int(y1)}"})
    out = gpd.GeoDataFrame(rows, geometry="geometry", crs=UTM) if rows else empty
    log(f"region predecessors: extents ({', '.join(f'{t} {len(v)}' for t, v in snaps.items())} snapshots): "
        f"{len(out)} buildings on {n_lots} parcels built up before today's building")
    return out


def tsheet_buildings(today, growth):
    """Houses read from a survey that draws every building (data/manual/tsheets/<town>_<year>.geojson:
    the U.S. Coast Survey plane-table sheet of Oakland, 1856; tools/tsheet_houses.py). A house stands from
    some year between the town's beginning and the survey (it is on the sheet: estimated), until the first
    building of today on its ground or a clearance, else a frame-house lifetime (ESTIMATED: gone 10-32 years
    after the survey inside the close-built town of the next snapshots, 16-46 years outside). Real outlines
    (about 10 m), one or two storeys; a house that is a footprint of today is left to the modern data."""
    from pathlib import Path
    rows = []
    tu = today
    tidx = tu.sindex
    ts = tu.start_year.values
    for f in sorted((INTERIM.parent / "manual" / "tsheets").glob("*_[12][0-9][0-9][0-9].geojson")):
        town, yr = Path(f).stem.rsplit("_", 1)
        yr = float(yr)
        g = gpd.read_file(f).to_crs(UTM)
        since = growth.since.get(town, yr - 6.0)
        later = [p for y, p, ex in growth.snaps.get(town, []) if y > yr and not ex][:1]
        n_same = 0
        for hid, geom in zip(g["id"].astype(str), g.geometry.values):
            hk = h01(hid, "t")
            start = max(since + 0.5, yr - 5.0) + (yr - 0.2 - max(since + 0.5, yr - 5.0)) * hk
            dense = bool(later) and later[0].contains(geom.representative_point())
            end = yr + (10.0 + 22.0 * h01(hid, "e") if dense else 16.0 + 30.0 * h01(hid, "e"))
            same = False
            for j in tidx.query(geom, predicate="intersects"):
                inter = geom.intersection(tu.geometry.values[j]).area
                if inter > 0.5 * geom.area and ts[j] <= yr + 1:
                    same = True
                elif inter > 0.25 * geom.area and ts[j] > yr:
                    end = min(end, ts[j] - 0.3)
            if same:
                n_same += 1
                continue
            if end <= start + 1:
                continue
            big = geom.area > 260
            st = 2 if (big or h01(hid, "s") < 0.35) else 1
            rows.append({"geometry": geom, "start_year": start, "end_year": end, "height": st * 3.4 + 1.0, "stories": st,
                         "kind": "building", "source": "sanborn_tsheet", "mapblklot": f"ts_{hid}",
                         "use_sanborn": "store" if big else "dwelling", "material": "frame",
                         "year_confidence": "estimated", "year_reason": f"tsheet:{town}_{int(yr)}"})
        log(f"region predecessors: {len(g)} buildings on the {int(yr)} survey of {town}: {n_same} stand today, "
            f"{len(rows)} drawn")
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=UTM) if rows else gpd.GeoDataFrame(geometry=[], crs=UTM)


_DEBUG: dict = {}


def _not_sf(x, y):
    """UTM points outside San Francisco (its corridors have their own parcel predecessors)."""
    import pyproj
    lon, lat = pyproj.Transformer.from_crs(UTM, 4326, always_xy=True).transform(np.asarray(x), np.asarray(y))
    return ~((lat > 37.7085) & (lon < -122.355) & (lon > -122.53))


def corridor_fill(today_utm, pred_utm, areas):
    """Ground cleared for freeways and renewal (I-980, the Cypress viaduct, SR-24 Grove-Shafter,
    I-580 MacArthur, I-880 Nimitz, SR-87 / I-280 in San José, Acorn, City Center, …) has no
    parcels and no streets on today's map, so it would be bare decades before the clearance.
    The 1940s-50s USGS topo sheets and the Sanborn maps show the street grid running on
    across, and today's streets still dead-end in pairs on both sides. Evidence used: a
    street end (a dead end, or a T at a frontage street) pointing into a cleared zone,
    matched with a collinear street end pointing back from the far side — or, failing one,
    run on to the first street beyond the zone — is a street the clearance cut; it is
    redrawn from the neighbourhood's development year until the clearance, never through a
    building standing today. Rows of buildings (10 m lots: houses where the prior fabric was
    Victorian rows, 2-3 storey row buildings where it was mixed) stand along the redrawn
    streets and on the zone side of the streets beside it, from the development year (early
    quartile of today's buildings within 150-300 m that predate the clearance) until the
    clearance (researched dates in redevelopment_areas.csv; 1-3 years before a freeway
    opened). Only where the neighbourhood predates the clearance by 12+ years, the ground
    was dry land, and nothing real (today's buildings, traced / documented predecessors)
    covers it. Freeways planned ahead of the tracts around them (SR-85, I-280 in Cupertino…)
    have no cut streets and stay empty. Procedural."""
    from audit_region_years import read_bayt
    from download_overture import RELEASE
    from common import RAW, VIEWER_DATA
    from airports import land_year
    from shapely.strtree import STRtree
    import pyproj
    empty = gpd.GeoDataFrame(geometry=[], crs=UTM)
    to_utm = pyproj.Transformer.from_crs(4326, UTM, always_xy=True)
    to_ll = pyproj.Transformer.from_crs(UTM, 4326, always_xy=True)
    # researched clearance areas (region ones: oak_, sj_)
    zareas = [a for a in areas if a[4].startswith(("oak_", "sj_")) and a[3] not in ("vacant", "rail_yards")]
    # freeway rights-of-way: every carriageway / ramp opened after 1940, buffered
    bufs, byear = [], []
    fp = VIEWER_DATA / "freeways.bin.gz"
    if fp.exists():
        h, c = read_bayt(fp)
        si = c["start_indices"].astype(np.int64)
        pos = c["positions"].reshape(-1, 3).astype(np.float64)
        fy = c["years"].reshape(-1, 2)[:, 0]
        fw = c["width"].astype(float)
        o = h["origin"]
        for i in range(len(c["kind"])):
            if not (1940 < fy[i] < 2030):
                continue
            p = pos[si[i]:si[i + 1]]
            if len(p) < 2:
                continue
            x, y = to_utm.transform(p[:, 0] + o[0], p[:, 1] + o[1])
            half = fw[i] / 2 + (16.0 if fw[i] >= 11 else 10.0)   # carriageway, shoulders, embankment
            bufs.append(shapely.LineString(np.column_stack([x, y])).buffer(half, cap_style="flat"))
            byear.append(float(fy[i]))
    if not bufs and not zareas:
        return empty, []
    byear = np.array(byear)
    btree = STRtree(bufs) if bufs else None
    aidx = STRtree([a[0] for a in zareas]) if zareas else None
    zone = shapely.union_all(bufs + [a[0] for a in zareas])
    shapely.prepare(zone)

    def dev_limit(cl):
        # the neighbourhood must predate the clearance; for freeways also 1955: tracts laid
        # out after the state's freeway plans (1950s) were built around the reserved route
        # (SR-85, I-280 in Cupertino), so their rights-of-way were never built on
        return min(cl[0] - 12, 1955.0) if cl[3] else cl[0] - 12

    def clear_at(geom):
        """(clearance start, end, prior fabric) of the zone under geom: a researched area
        (the smallest one) wins over a freeway right-of-way."""
        if aidx is not None:
            hit = aidx.query(geom, predicate="intersects")
            if len(hit):
                a = min((zareas[k] for k in hit), key=lambda a: a[0].area)
                return a[1], a[2], a[3], False
        if btree is not None:
            # the right-of-way reaches past the carriageways (widen_right_of_way)
            hit = btree.query(geom, predicate="dwithin", distance=130.0)
            if len(hit):
                f = float(byear[hit].min())
                return f - 3.0, f - 1.0, "victorian_rows", True
        return None

    # today's streets (not freeways, ramps or service roads) around the zones
    roads = []
    for f, keep in (("roads_local.parquet", ("residential", "living_street", "unclassified")),
                    ("roads_region.parquet", ("tertiary", "secondary", "primary"))):
        p = RAW / "overture" / RELEASE / f
        if p.exists():
            r = gpd.read_parquet(p, columns=["class", "geometry"])
            r = r[r["class"].isin(keep)]
            r = (r if r.crs else r.set_crs(4326)).to_crs(UTM)
            roads.append(r)
    roads = pd.concat(roads, ignore_index=True)
    roads = roads[roads.geometry.geom_type == "LineString"]
    zparts = bufs + [a[0] for a in zareas]
    near = np.unique(STRtree(zparts).query(roads.geometry.values, predicate="dwithin", distance=400)[0])
    lines = list(roads.geometry.values[near])
    ltree = STRtree(lines)
    log(f"corridors: {len(bufs)} freeway paths after 1940 + {len(zareas)} clearance areas, {len(lines)} streets around")
    tsidx = today_utm.sindex
    tgeo = today_utm.geometry.values
    tyear = today_utm.start_year.values.astype(float)
    if bufs:
        zone = widen_right_of_way(bufs, byear, btree, zone, lines, ltree, tsidx, tgeo, tyear)
        shapely.prepare(zone)

    # street ends pointing into a zone: dead ends, or T / L ends (no street carries on
    # straight from them)
    def end_dir(ln, at_end):
        L = ln.length
        if L < 12:
            return None
        a = ln.interpolate(max(0.0, L - 15.0)) if at_end else ln.interpolate(min(L, 15.0))
        b = ln.coords[-1] if at_end else ln.coords[0]
        d = np.array([b[0] - a.x, b[1] - a.y])
        nd = np.hypot(*d)
        return (np.array(b[:2]), d / nd) if nd > 1e-6 else None

    ends = {}
    for li, ln in enumerate(lines):
        for at_end in (False, True):
            e = end_dir(ln, at_end)
            if e is not None:
                ends.setdefault((int(round(e[0][0])), int(round(e[0][1]))), []).append((li, e[0], e[1]))
    stubs = []
    for lst in ends.values():
        touch = ltree.query(shapely.Point(lst[0][1]).buffer(1.5), predicate="intersects")
        for li, p, d in lst:
            straight = False
            for lj in touch:
                if lj == li:
                    continue
                q = lines[lj]
                t = q.project(shapely.Point(p))
                for a in (q.interpolate(max(0.0, t - 15.0)), q.interpolate(min(q.length, t + 15.0))):
                    v = np.array([a.x - p[0], a.y - p[1]])
                    nv = np.hypot(*v)
                    if nv > 3 and np.dot(v / nv, d) > 0.85:
                        straight = True
            if not straight and zone.intersects(shapely.LineString([p, p + d * 60.0])):
                stubs.append((li, p, d))
    log(f"corridors: {len(stubs)} street ends pointing into a cleared zone")
    # bearings of the straight street pieces around (to keep redrawn streets on the grid)
    gm, ga = [], []
    for ln in lines:
        cc = np.asarray(ln.coords)[:, :2]
        dv = np.diff(cc, axis=0)
        ll_ = np.hypot(dv[:, 0], dv[:, 1])
        k = ll_ >= 25
        gm.append((cc[:-1][k] + cc[1:][k]) / 2)
        ga.append(np.degrees(np.arctan2(dv[k, 1], dv[k, 0])) % 180)
    gm, ga = np.concatenate(gm), np.concatenate(ga)
    gtree = cKDTree(gm)

    def on_grid(seg, tol=8.0):
        m = seg.interpolate(0.5, normalized=True)
        u = _unit(seg)
        a = np.degrees(np.arctan2(u[1], u[0])) % 180
        idx = gtree.query_ball_point([m.x, m.y], 200)
        if not idx:
            return False
        d = np.abs((ga[idx] - a + 90) % 180 - 90)
        return int((d < tol).sum()) >= 2
    _DEBUG["stubs"] = stubs
    _DEBUG["zone"] = zone
    if len(stubs) < 2:
        return empty, []
    def blocked(seg):
        # a street can't have run through a building that stood before the clearance
        # (apartments put up on the leftover strips after the freeway don't count)
        cl = clear_at(seg)
        if cl is None:
            return True
        rest = seg.difference(zone)
        if rest.is_empty:
            return False
        hit = tsidx.query(rest, predicate="intersects")
        return any(tyear[k] < cl[0] - 1 and tgeo[k].buffer(-0.8).intersects(rest) for k in hit)

    P = np.array([s[1] for s in stubs])
    D = np.array([s[2] for s in stubs])
    stree = cKDTree(P)
    cand = []
    for i in range(len(stubs)):
        for j in stree.query_ball_point(P[i], 900):
            if j <= i or stubs[j][0] == stubs[i][0]:
                continue
            v = P[j] - P[i]
            L = np.hypot(*v)
            if L < 20:
                continue
            lat = abs(v[0] * D[i][1] - v[1] * D[i][0])
            if np.dot(v, D[i]) <= 0 or lat > max(10.0, min(0.08 * L, 25.0)) or np.dot(D[i], D[j]) > -0.93:
                continue
            seg = shapely.LineString([P[i], P[j]])
            inside = seg.intersection(zone).length
            if inside < max(15.0, 0.5 * L if L > 450 else 0.3 * L):
                continue
            cand.append((L + 4 * lat, i, j, seg))
    cand.sort(key=lambda t: t[0])
    used, links = set(), []

    lgrid: dict = {}

    def cells(seg):
        x0, y0, x1, y1 = seg.bounds
        return [(a, b) for a in range(int(x0 // 100), int(x1 // 100) + 1) for b in range(int(y0 // 100), int(y1 // 100) + 1)]

    def crosses(seg):
        # redrawn streets don't cross each other at a slant mid-block (one grid)
        near_ = {k for c_ in cells(seg) for k in lgrid.get(c_, ())}
        for k in near_:
            o = links[k]
            if not seg.crosses(o):
                continue
            x = seg.intersection(o)
            if x.distance(shapely.Point(seg.coords[0])) > 12 and x.distance(shapely.Point(seg.coords[-1])) > 12 \
                    and abs(np.dot(_unit(seg), _unit(o))) > 0.5:
                return True
        return False

    def add_link(seg):
        for c_ in cells(seg):
            lgrid.setdefault(c_, []).append(len(links))
        links.append(seg)

    for _, i, j, seg in cand:
        if i in used or j in used or blocked(seg) or crosses(seg):
            continue
        used.update((i, j))
        add_link(seg)
    n_pair = len(links)
    # ends without a partner: the street ran on across the zone to the first street beyond
    for i in range(len(stubs)):
        if i in used:
            continue
        li, p, d = stubs[i]
        ray = shapely.LineString([p, p + d * 500.0])
        hits = []
        for k in ltree.query(ray, predicate="intersects"):
            if k == li or lines[k].distance(shapely.Point(p)) < 2.0:
                continue
            x = lines[k].intersection(ray)
            for q in getattr(x, "geoms", [x]):
                if q.geom_type == "Point":
                    t = float(np.dot([q.x - p[0], q.y - p[1]], d))
                    if t > 8:
                        hits.append(t)
        seg = None
        for t in sorted(hits):   # frontage streets inside the right-of-way are passed over
            sg = shapely.LineString([p, p + d * t])
            if sg.intersection(zone).length >= max(15.0, 0.3 * t):
                seg = sg
                break
        if seg is None or not on_grid(seg) or blocked(seg) or crosses(seg):
            continue
        used.add(i)
        add_link(seg)
    log(f"corridors: {len(links)} cut streets redrawn ({n_pair} end to end, {len(links) - n_pair} to the street beyond)")

    # neighbourhood ages from today's buildings
    tc = today_utm.geometry.representative_point()
    txy = np.column_stack([tc.x.values, tc.y.values])
    ty = today_utm.start_year.values.astype(float)
    ttree = cKDTree(txy)

    def dev_year(x, y, cs):
        for r, need in ((150.0, 10), (300.0, 20)):
            idx = ttree.query_ball_point([x, y], r)
            yrs = ty[idx] if len(idx) else np.array([])
            yrs = yrs[yrs < cs - 2]
            if len(yrs) >= need:
                return float(np.percentile(yrs, 25))
        return np.nan

    streets, keep_links = [], []
    for seg in links:
        m = seg.interpolate(0.5, normalized=True)
        cl = clear_at(seg)
        if cl is None or not _not_sf([m.x], [m.y])[0]:
            continue
        dv = dev_year(m.x, m.y, cl[0])
        if not np.isfinite(dv) or dv > dev_limit(cl):
            continue
        lon, lat = to_ll.transform(m.x, m.y)
        ly = land_year(np.array([lon]), np.array([lat]))[0]
        if np.isfinite(ly) and ly > dv:
            continue
        streets.append({"geometry": seg, "start_year": dv - 1.0, "end_year": cl[1], "area": "corridor"})
        keep_links.append(seg)
    log(f"corridors: {len(keep_links)} redrawn streets in neighbourhoods older than their clearance")
    if not keep_links:
        return empty, streets

    # buildings: along the redrawn streets, and on the zone side of the streets beside the
    # zone (within 150 m of a redrawn street)
    near_links = shapely.union_all(keep_links).buffer(150)
    side = [ln for ln in lines if ln.intersects(near_links) and ln.distance(zone) < 45
            and ln.difference(zone).length > 0.5 * ln.length]
    atree = STRtree(lines + keep_links)
    # where they may stand: the zone, and the cleared ground along the redrawn streets
    # between the zone and the streets beyond (landscaped right-of-way today)
    place = shapely.union_all([zone.intersection(near_links)] + [ln.buffer(50) for ln in keep_links])
    shapely.prepare(place)
    psidx = pred_utm.sindex if len(pred_utm) else None
    placed, rows = {}, []
    for ln in keep_links + side:
        L = ln.length
        if L < 20:
            continue
        for s_ in np.arange(8.0, L - 8.0, 10.0):
            a, b = ln.interpolate(max(0.0, s_ - 2.0)), ln.interpolate(min(L, s_ + 2.0))
            t = np.array([b.x - a.x, b.y - a.y])
            nt = np.hypot(*t)
            if nt < 1e-6:
                continue
            t /= nt
            nrm = np.array([-t[1], t[0]])
            pm = ln.interpolate(s_)
            for sgn in (1, -1):
                key = f"cf_{int(pm.x)}_{int(pm.y)}_{sgn}"
                cl0 = clear_at(shapely.Point(pm.x + sgn * nrm[0] * 15, pm.y + sgn * nrm[1] * 15))
                rowb = cl0 is not None and cl0[2] == "mixed" and h01(key, "m") < 0.6
                if rowb:   # brick / frame row buildings to the sidewalk
                    depth, width, setback = 15.0 + 8.0 * h01(key, "d"), 9.4, 0.6
                else:      # houses with side yards
                    depth, width, setback = 11.0 + 5.0 * h01(key, "d"), 6.0 + 1.6 * h01(key, "w"), 2.5 + 3.0 * h01(key, "b")
                cx, cy = np.array([pm.x, pm.y]) + sgn * nrm * (5.0 + setback + depth / 2)
                pt = shapely.Point(cx, cy)
                if not place.contains(pt):
                    continue
                gk = (int(cx // 20), int(cy // 20))
                rect = shapely.Polygon([(cx + t[0] * dx - nrm[0] * dy * sgn, cy + t[1] * dx - nrm[1] * dy * sgn)
                                        for dx, dy in ((-width / 2, -depth / 2), (width / 2, -depth / 2),
                                                       (width / 2, depth / 2), (-width / 2, depth / 2))])
                cl_h = clear_at(pt)
                if cl_h is None:
                    continue
                # only buildings that stood together with this house get in its way
                if any(tyear[k] < cl_h[1] + 1 for k in tsidx.query(rect.buffer(3.5), predicate="intersects")):
                    continue
                if psidx is not None and len(psidx.query(rect.buffer(2.5), predicate="intersects")):
                    continue
                if len(atree.query(rect.buffer(4.5), predicate="intersects")):
                    continue
                if any(rect.intersects(q.buffer(0.8)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                       for q in placed.get((gk[0] + dx, gk[1] + dy), [])):
                    continue
                cl = clear_at(pt)
                if cl is None:
                    continue
                dv = dev_year(cx, cy, cl[0])
                if not np.isfinite(dv) or dv > dev_limit(cl):
                    continue
                start = dv + 10.0 * h01(key)
                end = cl[0] + (cl[1] - cl[0]) * h01(key, "c")
                if end <= start + 3:
                    continue
                placed.setdefault(gk, []).append(rect)
                if rowb:
                    st = 2 + int(h01(key, "s") < 0.4)
                    use, hgt = "store", st * 3.8 + 1.0
                else:
                    st = 1 + int(h01(key, "s") < 0.7)
                    use, hgt = "dwelling", st * 3.4 + 2.2
                rows.append({"geometry": rect, "start_year": start, "end_year": end, "height": hgt,
                             "stories": st, "kind": "building", "source": "region_procedural", "mapblklot": key,
                             "use_sanborn": use, "year_confidence": "procedural", "year_reason": "cleared_corridor"})
    out = gpd.GeoDataFrame(rows, geometry="geometry", crs=UTM) if rows else empty
    if len(out):
        # nothing before its ground (bay fill under the Nimitz, the Eastshore…), nothing in SF
        c_ = out.geometry.representative_point()
        lon, lat = to_ll.transform(c_.x.values, c_.y.values)
        ly = land_year(np.asarray(lon), np.asarray(lat))
        ok = _not_sf(c_.x.values, c_.y.values) & ~(np.isfinite(ly) & (out.start_year.values < ly + 1))
        out = out[ok].reset_index(drop=True)
    log(f"corridors: {len(out)} buildings stood on ground later cleared for freeways and renewal")
    return out, streets


def widen_right_of_way(bufs, byear, btree, zone, lines, ltree, tsidx, tgeo, tyear, step=3000.0, reach=110.0):
    """The cleared right-of-way is wider than the carriageways: embankments, frontage
    strips and the half-blocks between the freeway and the next street went too (SR-24 in
    North Oakland took ~150 m on each side of the roadway). Beside each freeway, within
    `reach` of its carriageways, the land counts as cleared where no building that predates
    the freeway stands today (later infill doesn't count), that isn't a park, school,
    cemetery, campus or sports ground (OSM land use), up to the nearest street — the
    pieces touching the carriageways are added to the zone."""
    from shapely.strtree import STRtree
    from download_overture import RELEASE
    from common import RAW
    lu = []
    for f in ("region5_land_use.parquet", "base_land_use.parquet"):
        p = RAW / "overture" / RELEASE / f
        if p.exists():
            d = pd.read_parquet(p, columns=["class", "geometry"])
            d = d[d["class"].isin(["park", "school", "cemetery", "golf_course", "recreation_ground", "pitch",
                                   "playground", "college", "university", "hospital", "kindergarten", "schoolyard",
                                   "religious", "grass", "village_green", "nature_reserve", "allotments"])]
            lu.append(gpd.GeoSeries(gpd.GeoSeries.from_wkb(d.geometry.values), crs=4326).to_crs(UTM))
    lu_geoms = list(pd.concat(lu, ignore_index=True).values) if lu else []
    lu_tree = STRtree(lu_geoms) if lu_geoms else None
    x0, y0, x1, y1 = shapely.union_all([b.envelope for b in bufs]).bounds
    ext = []
    for tx in np.arange(x0 - reach, x1 + reach, step):
        for ty in np.arange(y0 - reach, y1 + reach, step):
            tile = shapely.box(tx, ty, tx + step, ty + step)
            bi = btree.query(tile.buffer(reach + 20), predicate="intersects")
            if not len(bi):
                continue
            core = shapely.union_all([bufs[k] for k in bi])
            wide = core.buffer(reach).intersection(tile)
            if wide.is_empty:
                continue
            blockers = []
            ti = tsidx.query(wide, predicate="intersects")
            if len(ti):
                pairs = btree.query(tgeo[ti], predicate="dwithin", distance=reach + 30)
                fmin = np.full(len(ti), np.inf)
                np.minimum.at(fmin, pairs[0], byear[pairs[1]])
                old = ti[tyear[ti] < fmin - 1]
                blockers += [tgeo[k].buffer(6.0) for k in old]
            li = ltree.query(wide, predicate="intersects")
            blockers += [lines[k].buffer(7.0) for k in li]
            if lu_tree is not None:
                blockers += [lu_geoms[k] for k in lu_tree.query(wide, predicate="intersects")]
            free = wide.difference(shapely.union_all(blockers)) if blockers else wide
            for part in getattr(free, "geoms", [free]):
                if part.area > 300 and part.intersects(core):
                    ext.append(part)
    if not ext:
        return zone
    out = shapely.union_all([zone] + ext)
    log(f"corridors: right-of-way widened by {shapely.union_all(ext).difference(zone).area / 1e6:.2f} km2 of cleared land beside the carriageways")
    return out


def _unit(ln):
    c = np.asarray(ln.coords)
    v = c[-1, :2] - c[0, :2]
    return v / max(np.hypot(*v), 1e-9)



def region_predecessors(today):
    """All vanished buildings for the region (EPSG:4326): generated + traced (Sanborn)."""
    from sf_buildings import redevelopment_areas
    areas = redevelopment_areas()
    pred = generated(today, areas)
    growth = TownGrowth()
    tsb = tsheet_buildings(today.to_crs(UTM).reset_index(drop=True), growth)
    if len(tsb):
        pred = gpd.GeoDataFrame(pd.concat([pred, tsb], ignore_index=True), geometry="geometry", crs=UTM)
    ex = extent_fill(today, pred, areas, growth=growth)
    if len(ex):
        pred = gpd.GeoDataFrame(pd.concat([pred, ex], ignore_index=True), geometry="geometry", crs=UTM)
    # documented demolished buildings (data/tables/notable_demolished_region.csv): on their
    # parcel, or their traced Sanborn outline when the row points at one (apply_sanborn)
    lots = load_lots()
    lots["mapblklot"] = [f"rl{i}" for i in range(len(lots))]
    doc = table_buildings(TABLES / "notable_demolished_region.csv", lots, "notable_demolished_region")
    # OpenHistoricalMap's demolished civic buildings and estates (data/manual/ohm, CC0, cited)
    ohm_p = INTERIM.parent / "manual" / "ohm" / "notable_demolished_ohm.csv"
    if ohm_p.exists():
        ohm_doc = table_buildings(ohm_p, lots, "notable_demolished_ohm")
        if ohm_doc:
            doc = list(doc) + ohm_doc
            log(f"region predecessors: {len(ohm_doc)} demolished buildings from OpenHistoricalMap")
    # the region before the gold rush (data/tables/early_region.csv): missions, the San José
    # pueblo, rancho adobes, Ohlone / Miwok villages — adobes that still stand are today's
    # footprints (dated in region_buildings), not drawn twice
    ep = TABLES / "early_region.csv"
    if ep.exists():
        e = pd.read_csv(ep)
        # contact-era Ohlone / Bay Miwok / Coast Miwok villages from the expedition diaries
        # and Milliken's ethnohistory (data/manual/ohlone/villages.csv, README there)
        vp = INTERIM.parent / "manual" / "ohlone" / "villages.csv"
        if vp.exists():
            v = pd.read_csv(vp)
            v = v[~v["id"].isin(set(e["id"]))]
            e = pd.concat([e, v[[c for c in e.columns if c in v.columns]]], ignore_index=True)
            log(f"region predecessors: + {len(v)} contact-era villages (data/manual/ohlone)")
        keep = ~e.shape_note.fillna("").astype(str).str.upper().str.startswith("SURVIVES")
        tmp = INTERIM / "early_region_drawn.csv"
        e[keep].to_csv(tmp, index=False)
        early = table_buildings(tmp, lots, "early_region")
        if early:
            doc = list(doc) + early
            log(f"region predecessors: {len(early)} structures before 1850 ({int((~keep).sum())} surviving adobes left to their footprints)")
    if doc:
        d = gpd.GeoDataFrame(doc, geometry="geometry", crs=UTM)
        d["use_sanborn"] = "dwelling"
        pred = gpd.GeoDataFrame(pd.concat([pred, d], ignore_index=True), geometry="geometry", crs=UTM)
        log(f"region predecessors: {len(d)} documented demolished buildings")
    tu = today.to_crs(UTM).reset_index(drop=True)
    # the earthquake of 18 April 1906 outside San Francisco: where a district was destroyed
    # (data/manual/fires/quake_1906_*.geojson - Santa Rosa's business blocks), the traced
    # buildings mapped before it end that day and those mapped after it are the rebuilt town,
    # exactly as inside San Francisco's burned district
    qfiles = sorted((MANUAL / "fires").glob("quake_1906_*.geojson"))
    if qfiles:
        quake = gpd.GeoDataFrame(pd.concat([gpd.read_file(f) for f in qfiles], ignore_index=True), crs=4326).to_crs(UTM)[["geometry"]]
        # the outlines run along street centrelines; apply_sanborn only splits a building mapped
        # before and after the disaster when it lies 40 m inside the zone (San Francisco's fire
        # line is ragged) - grown by that much, the district's own street fronts count
        quake["geometry"] = quake.geometry.buffer(40.0)
    else:
        quake = gpd.GeoDataFrame(geometry=[], crs=UTM)
    pred = apply_sanborn(pred, tu, quake, areas, include=lambda area: area.startswith(REGION_SANBORN), dev_year=growth.dev_year)
    # buildings of vanished large sites (data/manual/vanished_sites/buildings.geojson:
    # traced from aerials / topo maps — racetrack grandstands, office campuses, factories)
    vb = INTERIM.parent / "manual" / "vanished_sites" / "buildings.geojson"
    if vb.exists():
        v = gpd.read_file(vb).to_crs(UTM)
        # + the airports' vanished terminals, rotundas, hangars and Navy buildings (SFO / OAK / SJC)
        ab = INTERIM.parent / "manual" / "airports" / "vanished_buildings.geojson"
        if ab.exists():
            v = gpd.GeoDataFrame(pd.concat([v, gpd.read_file(ab).to_crs(UTM)], ignore_index=True), geometry="geometry", crs=UTM)
        # + the shops, warehouses and barracks of shipyards, works and camps that are gone
        # (Kaiser's Richmond yards, Marinship, Moore Dry Dock, Oakland Army Base, Camp Parks ...):
        # building symbols traced from the USGS 1:24,000 sheets, dated by the editions
        # (data/manual/industrial_sites/tools/trace_vanished.py)
        ib = INTERIM.parent / "manual" / "industrial_sites" / "vanished_buildings.geojson"
        if ib.exists():
            v = gpd.GeoDataFrame(pd.concat([v, gpd.read_file(ib).to_crs(UTM)], ignore_index=True), geometry="geometry", crs=UTM)
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
    # buildings destroyed by wildfires (pipeline/fires.py, data/manual/fires; unchanged
    # without that folder): they stand until the day of the fire
    import fires
    pred = fires.add_predecessors(tu, pred, lots)
    # freeway rights-of-way and renewal clearances: the streets they cut and the rows
    # along them (corridor_fill), until the clearance
    # (REUSE_CORRIDORS=1 reuses the last run's result: ~20 min, and it only changes with
    # freeways, clearance areas, today's buildings or the predecessors near them)
    cp, sp = INTERIM / "corridor_houses.parquet", INTERIM / "clearance_streets.parquet"
    if os.environ.get("REUSE_CORRIDORS") and cp.exists() and sp.exists():
        cf, st = gpd.read_parquet(cp).to_crs(UTM), gpd.read_parquet(sp).to_crs(UTM)
        log(f"corridors: reused {len(cf)} buildings and {len(st)} streets from the last run")
    else:
        cf, streets = corridor_fill(tu, pred, areas)
        cf.to_parquet(cp)  # for QA plots
        st = gpd.GeoDataFrame(streets, geometry="geometry", crs=UTM) if streets else \
            gpd.GeoDataFrame({"start_year": [], "end_year": []}, geometry=[], crs=UTM)
        st.to_parquet(sp)
    if len(cf):
        pred = gpd.GeoDataFrame(pd.concat([pred, cf], ignore_index=True), geometry="geometry", crs=UTM)
    # two buildings never stand on one spot at the same time (sf_predecessors.resolve_overlaps)
    from sf_predecessors import resolve_overlaps
    pred = resolve_overlaps(gpd.GeoDataFrame(pred, geometry="geometry", crs=UTM), tu)
    pred = pred.to_crs(4326)
    use_map = {"dwelling": 1, "flats": 2, "store": 3, "office": 4, "warehouse": 5, "factory": 5, "shed": 5,
               "rail": 5, "stable": 0, "church": 6, "school": 6, "hall": 6, "hotel": 3}
    pred["use"] = pred.get("use_sanborn", pd.Series(index=pred.index, dtype=object)).map(use_map).fillna(0).astype(int) \
        if len(pred) else 0
    return pred
