"""Terrain audit: which site parts the c.1800 ground already paints as bare rock.

  python -I tools/audit_terrain.py  ->  traced/audit_terrain.csv

terrain_tiles.py takes the natural (pre-1769) upland cover from ESA WorldCover 2021: class 60
(bare / sparse vegetation) becomes ROCK unless it is low ground by the water. Quarry pits,
landfills, tank farms and graded plant sites are bare *today*, so they are grey rock from the
start of the timeline (the Permanente pit "goes back to the beginning of time"). This counts,
for every part of sites.geojson, the share of terrain-grid vertices (region z13 ~60 m, SF
detail z14 ~30 m) that WorldCover calls bare (60) or built-up (50), i.e. what the natural
cover would have to be replaced with before the part's year_start.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from rasterio import features
from rasterio.transform import Affine
from shapely.geometry import shape
from shapely.ops import transform as stransform

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1]


def merc(x, y, z=None):
    x = np.asarray(x)
    y = np.asarray(y)
    return x * 20037508.342789244 / 180.0, np.log(np.tan(np.pi / 4 + np.radians(y) / 2)) * 6378137.0


def main():
    grids = {}
    for name in ("region", "detail"):
        meta = json.loads((ROOT / f"data/interim/grid_{name}_meta.json").read_text())
        wc = np.load(ROOT / f"data/interim/grid_{name}_wc.npy")
        grids[name] = (meta, wc)
    feats = json.loads((OUT / "sites.geojson").read_text())["features"]
    rows = []
    for f in feats:
        p = f["properties"]
        g = stransform(merc, shape(f["geometry"]))
        best = None
        for name in ("detail", "region"):
            meta, wc = grids[name]
            t = Affine(*meta["transform"][:6])
            m = features.rasterize([(g, 1)], out_shape=wc.shape, transform=t, fill=0, dtype="uint8").astype(bool)
            if m.sum() >= 4:
                best = (name, m, wc)
                break
        if best is None:
            continue
        name, m, wc = best
        v = wc[m]
        rows.append(dict(site_id=p["site_id"], part_id=p["part_id"], cover=p["cover"], year_start=p["year_start"],
                         grid=name, cells=int(m.sum()), bare_share=round(float((v == 60).mean()), 2),
                         built_share=round(float((v == 50).mean()), 2),
                         tree_grass_share=round(float(np.isin(v, [10, 20, 30]).mean()), 2)))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "traced" / "audit_terrain.csv", index=False)
    s = df.groupby("site_id").apply(lambda t: pd.Series({"cells": t.cells.sum(),
                                                          "bare_share": np.average(t.bare_share, weights=t.cells)}))
    print(s.sort_values("bare_share", ascending=False).round(2).head(30).to_string())


if __name__ == "__main__":
    main()
