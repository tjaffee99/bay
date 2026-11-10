"""Fine ground elevation around every landmark model, for the viewer's elevation lookup.

The viewer stands landmarks on the terrain with a coarse lookup (60 m in the detail area,
240 m in the rest of the region) while the terrain mesh is 30 / 60 m, so on steep ground a
landmark could sit metres below the surface (Fort Ross on its coastal terrace was buried
8 m, Lick Observatory 21 m). This stage cuts, around each landmark's anchor (its model's
reach + a margin), a patch of the grid the terrain tiles themselves are cut from; the
viewer's elevationAt() reads the patches first, so anchors and the points models measure
relative to them agree with the mesh.

    node viewer/scripts/landmark_anchors.mjs      -> data/interim/landmark_anchors.json
    python landmark_ground.py                     -> viewer/public/data/elevation-spots.bin.gz

Run it after the terrain grids change or landmarks are added / moved (make landmark-ground).
"""
import json

import numpy as np

from common import INTERIM, VIEWER_DATA, log
from export_columnar import write_columnar
from terrain_grid import grid_def

MARGIN_M = 150.0
MAX_REACH_M = 2800.0


def main():
    rows = json.loads((INTERIM / "landmark_anchors.json").read_text())
    grids = []
    for name in ("detail", "region"):
        g = grid_def(name)
        e = np.load(INTERIM / f"grid_{name}_elev.npy").astype(np.float32)
        grids.append((name, g, e))
    meta, chunks, off = [], [], 0
    worst = []
    for r in rows:
        if r["kind"] == "bridge":
            continue  # bridges are modelled from sea level
        X = np.radians(r["lon"]) * 6378137.0
        Y = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(r["lat"]) / 2))
        # mercator metres are ~1.27x ground metres here
        half = (min(max(r.get("reach_m", 0), 0), MAX_REACH_M) + MARGIN_M) / np.cos(np.radians(r["lat"]))
        for name, g, e in grids:
            c0 = int(np.floor((X - half - g["X0"]) / g["res"]))
            c1 = int(np.ceil((X + half - g["X0"]) / g["res"]))
            r0 = int(np.floor((g["Y0"] - Y - half) / g["res"]))
            r1 = int(np.ceil((g["Y0"] - Y + half) / g["res"]))
            if c0 < 0 or r0 < 0 or c1 > g["cols"] - 1 or r1 > g["rows"] - 1:
                continue
            p = e[r0:r1 + 1, c0:c1 + 1]
            if (p < -500).any():
                continue  # outside this grid's coverage: the next (coarser) grid
            meta.append([g["X0"] + c0 * g["res"], g["Y0"] - r0 * g["res"], g["res"], p.shape[0], p.shape[1], off])
            chunks.append(np.clip(np.rint(np.maximum(p, 0) * 10), 0, 32000).astype(np.int16).ravel())
            off += p.size
            # what the viewer's coarse lookup (every 2nd / 4th vertex, bilinear) returned at the anchor
            step = 2 if name == "detail" else 4
            cf, rf = (X - g["X0"]) / g["res"], (g["Y0"] - Y) / g["res"]

            def bil(a, s):
                cc, rr = cf / s, rf / s
                i, j = int(np.floor(rr)), int(np.floor(cc))
                if i + 1 >= a.shape[0] or j + 1 >= a.shape[1]:
                    return np.nan
                fy, fx = rr - i, cc - j
                return (a[i, j] * (1 - fx) + a[i, j + 1] * fx) * (1 - fy) + (a[i + 1, j] * (1 - fx) + a[i + 1, j + 1] * fx) * fy

            fine, coarse = bil(np.maximum(e, 0), 1), bil(np.maximum(e[::step, ::step], 0), step)
            worst.append((coarse - fine, r["id"]))
            break
    write_columnar(VIEWER_DATA / "elevation-spots.bin.gz",
                   {"patch": np.asarray(meta, np.float64).ravel(), "elev": np.concatenate(chunks)},
                   counts={"patches": len(meta), "cells": off},
                   meta={"units": "decimetres, EPSG:3857 vertex lattice", "patch": "X0, Y0 (first vertex), res, rows, cols, offset"})
    worst = [w for w in worst if np.isfinite(w[0])]
    off3 = [w for w in worst if abs(w[0]) > 3]
    log(f"landmark ground: {len(meta)} patches, {off} cells -> elevation-spots.bin.gz "
        f"({(VIEWER_DATA / 'elevation-spots.bin.gz').stat().st_size / 1e3:.0f} kB)")
    log(f"landmark ground: the coarse lookup was off by more than 3 m at {len(off3)} anchors; worst: "
        + ", ".join(f"{i} {d:+.1f} m" for d, i in sorted(off3, key=lambda w: -abs(w[0]))[:10]))


if __name__ == "__main__":
    main()
