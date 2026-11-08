"""Encode building footprints into the viewer's BAYT building format (as sf_export.py
does for San Francisco): delta-coded 1e-7° int32 rings with ring-end markers, plus
per-feature columns. Shared by the region tiles (region_buildings.py)."""
from __future__ import annotations

import zlib

import numpy as np
import shapely

from export_columnar import write_columnar


def encode(geoms, origin):
    """geoms: shapely Polygons (EPSG:4326). Returns (positions int32 flat, starts u32, valid u8, n_vertices)."""
    pos_chunks, valid_chunks = [], []
    starts = np.zeros(len(geoms) + 1, np.uint32)
    vcount = 0
    ox, oy = origin
    for i, geom in enumerate(geoms):
        g = shapely.geometry.polygon.orient(geom, 1.0)  # CCW outer, CW holes
        rings = [np.asarray(g.exterior.coords)[:, :2]] + [np.asarray(r.coords)[:, :2] for r in g.interiors]
        closed = np.concatenate(rings)
        valid = np.ones(len(closed), np.uint8)
        e = 0
        for r in rings:
            e += len(r)
            valid[e - 1] = 0
        q = np.rint((closed - (ox, oy)) * 1e7).astype(np.int64)
        d = np.diff(q, axis=0, prepend=np.zeros((1, 2), np.int64))  # first vertex relative to the origin
        pos_chunks.append(d.astype(np.int32))
        valid_chunks.append(valid)
        vcount += len(closed)
        starts[i + 1] = vcount
    if not pos_chunks:
        return np.zeros(0, np.int32), starts, np.zeros(0, np.uint8), 0
    return np.concatenate(pos_chunks).ravel(), starts, np.concatenate(valid_chunks), vcount


def write_buildings(path, df, origin, conf_codes, use_categories, extra_meta=None):
    """df: GeoDataFrame (EPSG:4326, Polygons) with start_year, end_year, height, base,
    year_confidence, use, raw_year, stories, mat, roof, fid_key."""
    positions, starts, valid, vcount = encode(df.geometry.values, origin)
    fid = np.array([zlib.crc32(str(k).encode()) for k in df.fid_key.astype(str)], dtype=np.uint32)
    stories = np.nan_to_num(df.stories.astype(float).values, nan=0).clip(0, 255).astype(np.uint8)
    cols = {
        "positions_delta|shuffle": positions,
        "start_indices|shuffle": starts,
        "vertex_valid": valid,
        "start_year": df.start_year.astype(np.float32).values,
        "end_year": df.end_year.astype(np.float32).values,
        "height": df.height.astype(np.float32).values,
        "base": df.base.astype(np.float32).values,
        "confidence": df.year_confidence.map(conf_codes).fillna(1).astype(np.uint8).values,
        "use": df.use.astype(np.uint8).values,
        "raw_year": df.raw_year.fillna(0).astype(np.int16).values,
        "stories": stories,
        "mat": df.mat.astype(np.uint8).values,
        "roof": df.roof.astype(np.uint8).values,
        "fid|shuffle": fid,
    }
    meta = {"position_scale": 1e-7, "use_categories": use_categories, "confidence": list(conf_codes)}
    meta.update(extra_meta or {})
    return write_columnar(path, cols, origin=origin, counts={"features": len(df), "vertices": int(vcount)}, meta=meta)
