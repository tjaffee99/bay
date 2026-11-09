"""Land year under the SFO pavement from the fill-zone rings alone (no terrain run needed).

  cd pipeline && ../.venv/bin/python ../data/manual/airports/tools/fillcheck.py [FILL_ZONES_CSV]

Re-does terrain_tiles.py's zone step on the detail grid: c.1800 wet cells (SFEI layers in
grid_detail_hist + c.1998 "bay fill" = made land, as in terrain_tiles), distance from the
c.1800 shore in cells, and per zone year = start + (end - start) * distance / max distance
(earliest year per cell; fb_* fallbacks only where no specific zone is, at their midpoint).
Then prints the land year at the Mills Field points, the removed runways and every SFO row of
pavement_dates.csv against its researched start year (a piece waits for its ground: start =
max(start, land + 0.5) in airports.py). Default CSV: data/manual/fill_zones.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "pipeline"))
from common import INTERIM, MANUAL  # noqa: E402
from covers import WET, MARSH, FLAT, GRASS, SHALLOW  # noqa: E402
from terrain_grid import grid_def  # noqa: E402

BOX = (-122.43, 37.585, -122.33, 37.66)


def zone_years(csv_path, g, r0, r1, c0, c1):
    import rasterio.features
    from rasterio.transform import Affine
    from geocode import ring_polygon
    hist = np.load(INTERIM / "grid_detail_hist.npy")[r0:r1, c0:c1]
    b98 = np.load(INTERIM / "grid_detail_b1998.npy")[r0:r1, c0:c1]
    elev = np.load(INTERIM / "grid_detail_elev.npy")[r0:r1, c0:c1]
    wc = np.load(INTERIM / "grid_detail_wc.npy")[r0:r1, c0:c1]
    water_now = (wc == 80) | (wc == 0)
    N = np.where(hist > 0, hist.astype(np.int16) - 1, np.where(water_now, SHALLOW, GRASS)).astype(np.uint8)
    N[np.isin(N, [MARSH, FLAT]) & (elev > 6) & ~water_now] = GRASS
    N[np.isin(b98, [12, 13]) & ~np.isin(N, list(WET))] = SHALLOW
    wet = np.isin(N, list(WET))
    shore_d = ndimage.distance_transform_edt(wet)
    T = Affine(*g["transform"][:6]) * Affine.translation(c0, r0)
    t = pd.read_csv(csv_path)
    t = t.iloc[sorted(range(len(t)), key=lambda i: str(t.zone_id.iloc[i]).startswith("fb_"))]
    out = np.full(wet.shape, np.nan, np.float32)
    covered = np.zeros(wet.shape, bool)
    for _, r in t.iterrows():
        if str(r.kind).strip() != "fill":
            continue
        try:
            poly = ring_polygon(r.ring, r.get("ring_type", ""))
        except Exception:  # noqa: BLE001
            continue
        if poly is None or poly.is_empty:
            continue
        m = rasterio.features.rasterize([(poly, 1)], out_shape=wet.shape, transform=T, fill=0, dtype="uint8").astype(bool)
        fb = str(r.zone_id).startswith("fb_")
        if fb:
            m &= ~covered
        if not m.any():
            continue
        ys, ye = float(r.year_start), float(r.year_end)
        y = np.full(wet.shape, np.nan, np.float32)
        if fb:
            y[m] = (ys + ye) / 2
        else:
            span = max(float(shore_d[m].max()), 1.0)
            y[m] = ys + (ye - ys) * np.clip(shore_d[m] / span, 0, 1)
            covered |= m
        upd = m & (np.isnan(out) | (y < out))
        out[upd] = y[upd]
    return np.where(wet, out, np.nan)


def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else MANUAL / "fill_zones.csv"
    g = grid_def("detail")

    def rc(lon, lat):
        X = np.radians(lon) * 6378137.0
        Y = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))
        return np.rint((g["Y0"] - Y) / g["res"]).astype(int), np.rint((X - g["X0"]) / g["res"]).astype(int)
    (ra, rb), (ca, cb) = rc(np.array([BOX[0], BOX[2]]), np.array([BOX[3], BOX[1]]))
    r0, r1, c0, c1 = min(ra, rb), max(ra, rb) + 1, min(ca, cb), max(ca, cb) + 1
    ly = zone_years(csv_path, g, r0, r1, c0, c1)

    def at(lon, lat):
        r, c = rc(np.atleast_1d(lon), np.atleast_1d(lat))
        return ly[r - r0, c - c0]

    print(f"zones: {csv_path}")
    pts = {
        "Mills Field 1927 field, centre (1939 dike, marsh part)": (-122.3870, 37.6245),
        "Mills Field hangar row on the old Bayshore Highway": (-122.3917, 37.6245),
        "Mills Field, NW corner by the 1939 north levee": (-122.3880, 37.6290),
        "tidelands reclaimed early 1930s (1939 field, east)": (-122.3770, 37.6230),
        "Coast Guard Air Station (1940-41)": (-122.3893, 37.6327),
        "wartime field, centre (1946 sheet)": (-122.3740, 37.6150),
        "28L extension fill (1961)": (-122.3643, 37.6142),
        "28R extension fill (1968)": (-122.3598, 37.6159),
    }
    for k, (lon, lat) in pts.items():
        v = at(lon, lat)[0]
        print(f"  {k:55s} land {'always' if np.isnan(v) else f'{v:7.1f}'}")
    import geopandas as gpd
    vp = gpd.read_file(MANUAL / "airports" / "vanished_pavement.geojson")
    for _, f in vp[vp.airport == "SFO"].iterrows():
        xy = np.asarray(f.geometry.exterior.coords)
        v = at(xy[:, 0], xy[:, 1])
        c = f.geometry.representative_point()
        print(f"  removed runway '{f['name']}': start {f.start_year}, land at its corners "
              f"{np.round(v, 1).tolist()}, centre {at(c.x, c.y)[0]:.1f}")
    pav = pd.read_csv(MANUAL / "airports" / "pavement_dates.csv")
    pav = pav[pav.airport == "SFO"]
    v = at(pav.lon.values, pav.lat.values)
    late = np.isfinite(v) & (v + 0.5 > pav.start_year.values)
    print(f"  SFO pavement_dates rows: {len(pav)}; on land after their researched start: {int(late.sum())}")
    for (_, p), y in zip(pav[late].iterrows(), v[late]):
        print(f"    {p.feature_class:9s} {str(p['name'])[:24]:24s} start {p.start_year} -> land {y:.1f} ({p.lon:.5f}, {p.lat:.5f})")
    s = pd.Series(np.floor(np.where(np.isfinite(v), np.maximum(pav.start_year.values, v + 0.5), pav.start_year.values)))
    print("  effective start years (rows):", s.value_counts().sort_index().to_dict())


if __name__ == "__main__":
    main()
