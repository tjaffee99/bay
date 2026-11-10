"""Invariant: no building stands over water (owner, 2026-11).

For every exported building (San Francisco: data/interim/sf_export_final.parquet; the
counties: region_building_points.parquet) and every landmark model that is not a bridge
(landmark_anchors.json), the terrain cover under it at the moment it goes up — from the
histories the terrain stage assembled (grid_<name>_covers / _years.npy, the 30 m detail
grid where it exists, else the 60 m region grid) — must not be bay, tidal flat, salt pond
or reservoir. Run after terrain_tiles.py; prints the offenders by source.

    python audit_ground.py
"""
import json

import geopandas as gpd
import numpy as np
import pandas as pd

from common import INTERIM, log
from terrain_grid import grid_def
from terrain_tiles import COVER_NAMES, DEEP, FLAT, RESERVOIR, SALTPOND, SHALLOW

WATERISH = [DEEP, SHALLOW, FLAT, RESERVOIR, SALTPOND]


def cover_at(lon, lat, t):
    """Cover code under each point at time t (255: outside both grids)."""
    out = np.full(len(lon), 255, np.uint8)
    for name in ("detail", "region"):
        pc, py = INTERIM / f"grid_{name}_covers.npy", INTERIM / f"grid_{name}_years.npy"
        if not pc.exists():
            continue
        g = grid_def(name)
        cv, yv = np.load(pc, mmap_mode="r"), np.load(py, mmap_mode="r")
        valid = np.load(INTERIM / f"grid_{name}_elev.npy", mmap_mode="r")
        X = np.radians(lon) * 6378137.0
        Y = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))
        c = np.rint((X - g["X0"]) / g["res"]).astype(int)
        r = np.rint((g["Y0"] - Y) / g["res"]).astype(int)
        ok = (out == 255) & (c >= 0) & (r >= 0) & (c < g["cols"]) & (r < g["rows"])
        ok[ok] &= np.asarray(valid[r[ok], c[ok]]) > -500
        i = np.nonzero(ok)[0]
        if not len(i):
            continue
        C = np.stack([np.asarray(cv[k][r[i], c[i]]) for k in range(5)])
        Yr = np.stack([np.asarray(yv[k][r[i], c[i]]) for k in range(4)])
        state = (np.isfinite(Yr) & (Yr <= t[i][None, :])).sum(axis=0)
        out[i] = C[state, np.arange(len(i))]
    return out


def build_years(height):
    return np.clip(0.25 + np.nan_to_num(np.asarray(height, float), nan=7.0) / 55.0, 0.33, 3.0)


def report(name, d, lon, lat, start, by):
    # from the moment the construction frame starts to rise (build_years before start_year)
    t = np.asarray(start, float) - (build_years(d.height.values) if "height" in d.columns else 0.33) + 0.02
    cov = cover_at(np.asarray(lon, float), np.asarray(lat, float), t)
    bad = np.isin(cov, WATERISH)
    log(f"audit ground: {name}: {len(d)} checked, {int(bad.sum())} over water when they go up")
    if bad.any():
        x = d[bad].assign(cover=[COVER_NAMES[c] for c in cov[bad]])
        for col in by:
            if col in x.columns:
                print(x.groupby([x[col].astype(str).str.split(":").str[0], "cover"]).size().sort_values(ascending=False).head(12).to_string())
    return int(bad.sum())


def main():
    total = 0
    p = INTERIM / "sf_export_final.parquet"
    if p.exists():
        b = gpd.read_parquet(p)
        rp = b.geometry.representative_point()
        total += report("San Francisco", b, rp.x.values, rp.y.values, b.start_year.values, ["source", "year_confidence"])
    p = INTERIM / "region_building_points.parquet"
    if p.exists():
        r = pd.read_parquet(p)
        total += report("counties", r, r.lon.values, r.lat.values, r.start_year.values, [])
    p = INTERIM / "landmark_anchors.json"
    if p.exists():
        lm = pd.DataFrame([x for x in json.loads(p.read_text()) if x["kind"] != "bridge"])
        lm["start"] = [b[0] for b in lm.built]
        cov = cover_at(lm.lon.values, lm.lat.values, lm.start.values + 0.05)
        bad = np.isin(cov, WATERISH)
        log(f"audit ground: landmarks: {len(lm)} checked, {int(bad.sum())} anchored over water when they go up "
            "(ships, wharves and piers are meant to be): " + ", ".join(lm.id[bad].head(40)))
    log(f"audit ground: {total} buildings over water in all")


if __name__ == "__main__":
    main()
