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

from common import INTERIM, MANUAL, TABLES, log
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
    prev = 1846.0
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
    log(f"predecessors: {built.sum()} of {len(lots)} lots inside a pre-1906 extent")

    # today's buildings on each lot (earliest start)
    b = gpd.read_parquet(INTERIM / "sf_buildings.parquet").to_crs(UTM)
    bc = gpd.GeoDataFrame({"start": b.start_year.values}, geometry=b.geometry.representative_point(), crs=UTM)
    j = gpd.sjoin(bc, lots[["geometry"]], predicate="within", how="inner")
    modern = j.groupby("index_right").start.min()
    mod = modern.reindex(range(len(lots))).values

    fire = gpd.read_file(INTERIM / "fire_1906.geojson").to_crs(UTM)
    burned = cent.within(shapely.union_all(fire.geometry.values)).values

    rows = []
    for i in np.nonzero(built)[0]:
        key = str(lots.mapblklot.iloc[i])
        h = h01(key)
        dev = dev_lo[i] + (dev_hi[i] - dev_lo[i]) * h
        m = mod[i]
        geom = lots.geometry.iloc[i]
        c = cent.iloc[i]
        downtown = DOWNTOWN.contains(gpd.GeoSeries([c], crs=UTM).to_crs(4326).iloc[0])
        if burned[i]:
            end = 1906.29
        elif np.isfinite(m) and m > dev + 3:
            end = m - 0.3  # replaced by today's building
        else:
            continue  # today's building may be the original — nothing to add
        fp = footprint(geom, downtown)
        if fp is None:
            continue
        storeys = (3 + int(2 * h01(key, "s"))) if downtown else (2 + int(h01(key, "s") < (0.5 if dev > 1885 else 0.15)))
        storey_h = 4.5 if downtown else 3.6
        rows.append({"geometry": fp, "start_year": dev, "end_year": end, "height": storeys * storey_h + (1.5 if not downtown else 0),
                     "stories": storeys, "kind": "building", "source": "sf_extent_procedural", "mapblklot": key,
                     "year_confidence": "procedural", "year_reason": "predecessor"})
        # burned-zone rebuild that stood until today's (later) building
        if burned[i] and np.isfinite(m) and m > BURN_REBUILD[1] + 5:
            rb = BURN_REBUILD[0] + (BURN_REBUILD[1] - BURN_REBUILD[0]) * h01(key, "r")
            st = 3 + int(3 * h01(key, "t")) if downtown else 2 + int(2 * h01(key, "t"))
            rows.append({"geometry": fp, "start_year": rb, "end_year": m - 0.3, "height": st * (4.5 if downtown else 3.6),
                         "stories": st, "kind": "building", "source": "sf_rebuild_procedural", "mapblklot": key,
                         "year_confidence": "procedural", "year_reason": "post_fire_rebuild"})
    pred = gpd.GeoDataFrame(rows, crs=UTM)
    log(f"predecessors: {len(pred)} generated buildings ({(pred.source == 'sf_rebuild_procedural').sum()} post-fire rebuilds)")

    notable = notable_buildings(lots)
    if len(notable):
        # the documented building replaces any generated one on its lot for its lifetime
        pred = pred[~pred.mapblklot.isin(set(notable.mapblklot))]
        pred = pd.concat([pred, notable], ignore_index=True)
        log(f"predecessors: {len(notable)} documented pre-1906 buildings")
    pred = gpd.GeoDataFrame(pred, geometry="geometry", crs=UTM).to_crs(4326)
    pred["base"] = 0.0
    pred["use"] = 0
    pred["raw_year"] = 0
    pred["end_year"] = pred.end_year.astype(float)
    pred.to_parquet(INTERIM / "sf_predecessors.parquet")
    log(f"predecessors: wrote {len(pred)} features")


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


def notable_buildings(lots):
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
