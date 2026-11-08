"""Stage: export SF buildings to the viewer's binary format.

Each polygon (multipolygons are split) becomes one feature: closed rings
(outer CCW + holes CW) back to back, a per-vertex ring-end marker, and
per-feature columns. Positions are integer lon/lat offsets from `origin` in
units of 1e-7 degree (~1 cm), delta-coded within each feature so gzip can
squeeze them. Triangulation happens in the browser (Web Worker + earcut).

Output: viewer/public/data/sf-buildings.bin.gz
"""
from __future__ import annotations

import zlib

import geopandas as gpd
import pandas as pd
import numpy as np
import shapely

from common import INTERIM, VIEWER_DATA, log
from export_columnar import write_columnar
from sf_buildings import CONF, USE_CATEGORIES
from terrain_grid import grid_def
from common import INTERIM as _I

_GRID = None


def ground_sampler():
    """Bilinear sampler of the 30 m detail DEM (same lattice as the terrain tiles)."""
    global _GRID
    if _GRID is None:
        g = grid_def("detail")
        e = np.load(_I / "grid_detail_elev.npy")
        e = np.where(e < -500, 0, e)
        _GRID = (g, e)
    g, e = _GRID

    def sample(lon, lat):
        X = np.radians(lon) * 6378137.0
        Y = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))
        c = np.clip((X - g["X0"]) / g["res"], 0, g["cols"] - 1.001)
        r = np.clip((g["Y0"] - Y) / g["res"], 0, g["rows"] - 1.001)
        c0 = np.floor(c).astype(int)
        r0 = np.floor(r).astype(int)
        fx = c - c0
        fy = r - r0
        v = (e[r0, c0] * (1 - fx) + e[r0, c0 + 1] * fx) * (1 - fy) + (e[r0 + 1, c0] * (1 - fx) + e[r0 + 1, c0 + 1] * fx) * fy
        return np.maximum(v, 0.9)  # land sits at least just above the sea-level water surface

    return sample

ORIGIN = (-122.44, 37.76)

# facade material classes (viewer/src/palette.ts MATERIALS has the colours)
M_GENERIC, M_EARLY, M_VICTORIAN, M_BRICK, M_MASONRY, M_STUCCO, M_MIDCENTURY, M_TOWER70, M_GLASS, M_CONTEMP, M_CIVIC, M_INDUSTRIAL, \
    M_ADOBE, M_TULE = range(14)
# roof codes: 0 flat (tar / gravel / membrane), 1 clay tile, 2 shingle / slate (pitched), 3 same as walls
R_FLAT, R_TILE, R_SHINGLE, R_WALL = range(4)


def materials(df, h01):
    """Rough facade material + roof per building, from era, use, height and district.
    Rules of thumb (SF Planning context statements, sf_extent_README.md): pre-1906
    houses are painted wood (Victorian / Edwardian), the pre-1906 commercial core and
    warehouses brick; 1906-1930 downtown is terra cotta / granite / buff brick; SoMa and
    the industrial bayside are red brick, later concrete; 1920s-50s Sunset / Richmond /
    Marina houses are stucco (Marina with clay tile roofs); post-war mid-rises are
    painted concrete / stucco; 1960s-80s towers bronze glass and concrete, later ones
    blue / silver glass; recent mid-rises grey, white and charcoal panels."""
    c = df.geometry.representative_point()
    lon, lat = c.x.values, c.y.values
    y = df.start_year.values
    H = df.height.values
    use = df.use.fillna(0).values.astype(int)
    src = df.source.fillna("").values
    reason = df.year_reason.fillna("").values if "year_reason" in df else np.array([""] * len(df))
    downtown = (lon > -122.4115) & (lon < -122.392) & (lat > 37.7855) & (lat < 37.7995)
    soma = (lon > -122.425) & (lon < -122.385) & (lat > 37.765) & (lat < 37.7855) & ~downtown
    bayside_ind = (lon > -122.405) & (lat < 37.765)
    west = lon < -122.455
    marina = (lat > 37.7985) & (lon > -122.448) & (lon < -122.427)
    # the Presidio (boundary approx.: Lyon St, W Pacific Ave / Lake St, the shore)
    from shapely import contains_xy
    from shapely.geometry import Polygon
    presidio_poly = Polygon([(-122.4467, 37.8065), (-122.4467, 37.7882), (-122.4590, 37.7873), (-122.4720, 37.7861),
                             (-122.4852, 37.7866), (-122.4885, 37.7905), (-122.4800, 37.8115), (-122.4500, 37.8095)])
    presidio = contains_xy(presidio_poly, lon, lat)
    resid = np.isin(use, [1, 2]) | ((use == 0) & (H < 14))
    commercial = np.isin(use, [3, 4])
    industrial = (use == 5) | ((soma | bayside_ind) & ~resid & (y < 1960))
    hash_ = np.array([h01(str(k)) for k in df.sf16_bldgid.fillna("").astype(str) + df.index.astype(str)])
    mat = np.full(len(df), M_GENERIC, np.uint8)
    roof = np.full(len(df), R_FLAT, np.uint8)

    def put(mask, m, r=None):
        sel = mask & (mat == M_GENERIC)
        mat[sel] = m
        if r is not None:
            roof[sel] = r

    # documented materials first (early_sf / notable tables)
    dm = df["material"].fillna("").values if "material" in df else np.array([""] * len(df))
    put(dm == "adobe", M_ADOBE, R_TILE)
    put(dm == "tule", M_TULE, R_WALL)
    put(dm == "canvas tent", M_EARLY, R_WALL)
    put(dm == "brick", M_BRICK, R_FLAT)
    put(dm == "stone", M_CIVIC, R_FLAT)
    put(dm == "wharf", M_EARLY, R_WALL)  # weathered timber wharf decks
    # Presidio: the 1890s Montgomery St barracks are red brick; the Army's 1909-1940s
    # Mission / Spanish Colonial Revival buildings (Fort Scott, Main Post, Letterman,
    # housing) are white stucco under red clay tile, like Fort Mason's
    put(presidio & (y >= 1890) & (y < 1906) & (H > 7), M_BRICK, R_FLAT)
    put(presidio & (y >= 1908) & (y < 1946), M_STUCCO, R_TILE)
    put(y < 1853, M_EARLY, R_SHINGLE)
    put((reason == "predecessor_brick") | ((y < 1906) & (commercial | industrial | (downtown & (H > 9)))), M_BRICK, R_FLAT)
    put(y < 1906, M_VICTORIAN, R_SHINGLE)
    put((use == 6) & (y < 1960) & (H > 12), M_CIVIC, R_FLAT)
    # SoMa / bayside warehouses: brick and (painted) reinforced concrete in about equal shares
    put((y < 1946) & industrial & (hash_ < 0.55), M_BRICK, R_FLAT)
    put((y < 1946) & industrial, M_INDUSTRIAL, R_FLAT)
    put((y < 1935) & (downtown | (commercial & (H > 20))), M_MASONRY, R_FLAT)
    put((y < 1920) & resid & ~west & ~marina, M_VICTORIAN, R_SHINGLE)  # Edwardian wood flats
    put((y < 1960) & resid & marina, M_STUCCO, R_TILE)
    put((y < 1960) & resid, M_STUCCO, R_FLAT)
    put((y < 1946) & commercial, M_MASONRY, R_FLAT)
    put((y >= 1955) & (y < 1986) & (H >= 40), M_TOWER70, R_FLAT)
    put((y >= 1986) & (H >= 40), M_GLASS, R_FLAT)
    put((y < 1990) & industrial, M_INDUSTRIAL, R_FLAT)
    put(y < 1995, M_MIDCENTURY, R_FLAT)
    put(np.ones(len(df), bool), M_CONTEMP, R_FLAT)
    # roofs: about half the Marina's Mediterranean houses have clay tile, ~15% elsewhere;
    # most Italianate / Edwardian flats are flat-roofed behind cornices, Queen Annes pitched
    roof[(mat == M_STUCCO) & marina] = np.where(hash_[(mat == M_STUCCO) & marina] < 0.5, R_TILE, R_FLAT)
    roof[(mat == M_STUCCO) & ~marina] = np.where(hash_[(mat == M_STUCCO) & ~marina] < 0.15, R_TILE, R_FLAT)
    roof[mat == M_VICTORIAN] = np.where(hash_[mat == M_VICTORIAN] < 0.4, R_SHINGLE, R_FLAT)
    return mat, roof


def main():
    df = gpd.read_parquet(INTERIM / "sf_buildings.parquet")
    pred_path = INTERIM / "sf_predecessors.parquet"
    df["material"] = None
    if pred_path.exists():
        pred = gpd.read_parquet(pred_path)
        pred["sf16_bldgid"] = "pred:" + pred.mapblklot.astype(str) + ":" + pred.start_year.round(1).astype(str)
        df = gpd.GeoDataFrame(pd.concat([df, pred[[c for c in pred.columns if c in df.columns]]], ignore_index=True), crs=4326)
        log(f"export: + {len(pred)} vanished buildings (pre-1906 city, replaced houses)")
    df = df.explode(index_parts=False).reset_index(drop=True)
    df = df[df.geometry.geom_type == "Polygon"]
    # simplify by 25 cm in metres: drops survey jitter / collinear vertices, invisible at map scale
    df["geometry"] = df.geometry.to_crs(32610).simplify(0.25, preserve_topology=True).to_crs(4326)
    df = df[~df.geometry.is_empty & df.geometry.is_valid & (df.geometry.geom_type == "Polygon")]
    df = df.reset_index(drop=True)
    # nothing stands before its ground exists (bay fill): push generated / imputed
    # buildings onto dry land; report documented ones that conflict
    ly_path = _I / "grid_detail_landyear.npy"
    if ly_path.exists():
        g = grid_def("detail")
        ly = np.load(ly_path)
        rp = df.geometry.representative_point()
        X = np.radians(rp.x.values) * 6378137.0
        Y = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(rp.y.values) / 2))
        c = np.clip(np.rint((X - g["X0"]) / g["res"]).astype(int), 0, g["cols"] - 1)
        r = np.clip(np.rint((g["Y0"] - Y) / g["res"]).astype(int), 0, g["rows"] - 1)
        land = ly[r, c]
        early = np.isfinite(land) & (df.start_year.values < land - 0.5)
        soft = early & (df.year_confidence.values != "exact")
        documented = df.source.fillna("").isin(["early_sf", "notable_pre1906"]).values  # wharves, piers, beached ships
        fix = soft & ~documented
        df.loc[fix, "start_year"] = land[fix] + 0.5 + (df.index.values[fix] % 7) * 0.3
        drop = fix & (df.start_year.values >= df.end_year.values - 0.5)
        log(f"export: land check: {early.sum()} buildings predate their ground; moved {fix.sum()} generated/imputed "
            f"(dropped {drop.sum()} that no longer fit), kept {(early & ~fix).sum()} exact/documented (piers, wharves)")
        df = df[~drop].reset_index(drop=True)

    n = len(df)
    log(f"export: {n} polygons")

    pos_chunks, valid_chunks = [], []
    starts = np.zeros(n + 1, np.uint32)
    vcount = 0
    ox, oy = ORIGIN
    for i, geom in enumerate(df.geometry.values):
        g = shapely.geometry.polygon.orient(geom, 1.0)  # CCW outer, CW holes
        rings = [np.asarray(g.exterior.coords)[:, :2]] + [np.asarray(r.coords)[:, :2] for r in g.interiors]
        closed = np.concatenate(rings)
        valid = np.ones(len(closed), np.uint8)
        e = 0
        for r in rings:
            e += len(r)
            valid[e - 1] = 0
        q = np.rint((closed - (ox, oy)) * 1e7).astype(np.int64)
        d = np.diff(q, axis=0, prepend=np.zeros((1, 2), np.int64))  # first vertex absolute
        pos_chunks.append(d.astype(np.int32))
        valid_chunks.append(valid)
        vcount += len(closed)
        starts[i + 1] = vcount
    positions = np.concatenate(pos_chunks).ravel()
    vertex_valid = np.concatenate(valid_chunks)

    # ---- ground under each footprint (terrain): foundation at the lowest corner,
    # roof at mean ground + building height
    sample = ground_sampler()
    lonlat = np.concatenate([np.asarray(shapely.geometry.polygon.orient(gm, 1.0).exterior.coords)[:, :2] for gm in df.geometry.values])
    counts = np.array([len(gm.exterior.coords) for gm in df.geometry.values])
    gz = sample(lonlat[:, 0], lonlat[:, 1])
    splits = np.cumsum(counts)[:-1]
    gmin = np.array([a.min() for a in np.split(gz, splits)])
    gmean = np.array([a.mean() for a in np.split(gz, splits)])
    ground = gmin - 1.0
    df["height"] = df.height + (gmean - gmin) + 1.0 * (df.base.values == 0)
    df["base"] = np.where(df.base.values > 0, gmean + df.base.values, ground)
    log(f"export: ground elevation {np.percentile(gmean, [1, 50, 99]).round(1)} m (p1/median/p99)")

    import zlib as _z
    mat, roof = materials(df, lambda k: (_z.crc32(k.encode()) % 100003) / 100003.0)
    log(f"export: materials {np.bincount(mat, minlength=14).tolist()}")
    fid = np.array([zlib.crc32(str(k).encode()) for k in df.sf16_bldgid.fillna("").astype(str) + df.index.astype(str)],
                   dtype=np.uint32)
    stories = np.nan_to_num(df.stories.astype(float).values, nan=0).clip(0, 255).astype(np.uint8)
    cols = {
        "positions_delta|shuffle": positions,
        "start_indices|shuffle": starts,
        "vertex_valid": vertex_valid,
        "start_year": df.start_year.astype(np.float32).values,
        "end_year": df.end_year.astype(np.float32).values,
        "height": df.height.astype(np.float32).values,
        "base": df.base.astype(np.float32).values,
        "confidence": df.year_confidence.map(CONF).astype(np.uint8).values,
        "use": df.use.astype(np.uint8).values,
        "raw_year": df.raw_year.fillna(0).astype(np.int16).values,
        "stories": stories,
        "mat": mat,
        "roof": roof,
        "fid|shuffle": fid,
    }
    out = VIEWER_DATA / "sf-buildings.bin.gz"
    raw, gz = write_columnar(out, cols, origin=ORIGIN,
                             counts={"features": n, "vertices": int(vcount)},
                             meta={"position_scale": 1e-7, "use_categories": USE_CATEGORIES,
                                   "confidence": list(CONF),
                                   "sources": sorted(df.source.unique().tolist())})
    log(f"export: {n} features, {vcount} vertices; {raw / 1e6:.1f} MB raw, {gz / 1e6:.1f} MB gz -> {out}")


if __name__ == "__main__":
    main()
