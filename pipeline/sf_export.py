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
import numpy as np
import shapely

from common import INTERIM, VIEWER_DATA, log
from export_columnar import write_columnar
from sf_buildings import CONF, USE_CATEGORIES

ORIGIN = (-122.44, 37.76)


def main():
    df = gpd.read_parquet(INTERIM / "sf_buildings.parquet")
    df = df.explode(index_parts=False).reset_index(drop=True)
    df = df[df.geometry.geom_type == "Polygon"]
    # simplify by 25 cm in metres: drops survey jitter / collinear vertices, invisible at map scale
    df["geometry"] = df.geometry.to_crs(32610).simplify(0.25, preserve_topology=True).to_crs(4326)
    df = df[~df.geometry.is_empty & df.geometry.is_valid & (df.geometry.geom_type == "Polygon")]
    df = df.reset_index(drop=True)
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
