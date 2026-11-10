"""Stage: master terrain grids (elevation + raw land-cover inputs) on the Web-Mercator
tile-vertex lattice, cached as .npy for terrain_tiles.py.

Two grids share the same lattice definition (vertex = 1/64 of a tile):
  * region grid at z13/64 (~60 m)  — the whole Bay Area (Sonoma/Napa to Santa Cruz)
  * detail grid at z14/64 (~30 m)  — San Francisco and its shores

Inputs (windowed reads of cloud-optimised GeoTIFFs; nothing bulky is stored):
  * USGS 3DEP 1/3 arc-second DEM (public domain) — prd-tnm S3
  * ESA WorldCover 2021 10 m land cover (CC BY 4.0) — esa-worldcover S3
  * HISDAC-US first built-up year (CC0), data/raw/hisdac
  * SFEI baylands c.1800 / c.1998 (data/interim, from baylands_pdf.py)

Outputs: data/interim/grid_<name>_{elev,wc,fbuy,b1800,b1998}.npy + _meta.json
"""
from __future__ import annotations

import json
import math

import geopandas as gpd
import numpy as np
import rasterio
from rasterio import features
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.warp import reproject

from common import INTERIM, RAW, log

R = 6378137.0
ORIGIN_SHIFT = math.pi * R  # 20037508.34

GRIDS = {
    # name: (zoom of the lattice tiles, lon_min, lat_min, lon_max, lat_max)
    # ten counties: Sonoma (to the Gualala River) and Napa to Santa Cruz / Gilroy, Solano and the Delta edge
    "region": (13, -123.68, 36.78, -121.16, 38.91),
    # 30 m: San Francisco and the urban bay plain (Richmond / San Rafael to San José,
    # the Peninsula, the East Bay down to Fremont, Walnut Creek and the Tri-Valley)
    "detail": (14, -122.62, 37.22, -121.75, 37.98),
}
VERTS = 64  # grid cells per tile edge

B1800 = {"deep_bay": 1, "shallow_bay": 2, "tidal_flat": 3, "tidal_marsh": 4, "tidal_marsh_pan": 4,
         "perennial_pond": 5, "lagoon": 5, "salt_pond": 6, "riparian_forest": 7,
         "moist_grassland": 8, "grassland_vernal_pool": 8}
B1998 = {"deep_bay": 1, "shallow_bay": 2, "tidal_flat": 3, "tidal_marsh": 4, "tidal_marsh_pan": 4,
         "perennial_pond": 5, "lagoon": 5, "salt_pond": 6, "riparian_forest": 7, "moist_grassland": 8,
         "grassland_vernal_pool": 8, "agricultural_bayland": 9, "diked_wetland": 10, "storage_pond": 11,
         "undeveloped_fill": 12, "developed_fill": 13}


def tile_x(lon, z):
    return (lon + 180.0) / 360.0 * 2 ** z


def tile_y(lat, z):
    s = math.radians(lat)
    return (1 - math.log(math.tan(s) + 1 / math.cos(s)) / math.pi) / 2 * 2 ** z


def grid_def(name):
    z, lon0, lat0, lon1, lat1 = GRIDS[name]
    tx0, tx1 = math.floor(tile_x(lon0, z)), math.ceil(tile_x(lon1, z))
    ty0, ty1 = math.floor(tile_y(lat1, z)), math.ceil(tile_y(lat0, z))
    res = 2 * ORIGIN_SHIFT / (2 ** z * VERTS)  # mercator metres per cell
    cols = (tx1 - tx0) * VERTS + 1
    rows = (ty1 - ty0) * VERTS + 1
    # vertex (r, c) sits at mercator (X0 + c*res, Y0 - r*res); pixel centres on vertices
    X0 = -ORIGIN_SHIFT + tx0 * VERTS * res
    Y0 = ORIGIN_SHIFT - ty0 * VERTS * res
    transform = Affine(res, 0, X0 - res / 2, 0, -res, Y0 + res / 2)
    return {"name": name, "z": z, "tx0": tx0, "ty0": ty0, "tx1": tx1, "ty1": ty1, "rows": rows, "cols": cols,
            "res": res, "X0": X0, "Y0": Y0, "transform": transform}


def dem_tiles(lon0, lat0, lon1, lat1):
    out = []
    for lat in range(math.floor(lat0) + 1, math.ceil(lat1) + 1):
        for lon in range(math.floor(lon0), math.ceil(lon1)):
            out.append(f"/vsicurl/https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/current/n{lat:02d}w{-lon:03d}/USGS_13_n{lat:02d}w{-lon:03d}.tif")
    return out


def wc_tiles(lon0, lat0, lon1, lat1):
    out = []
    for lat in range(math.floor(lat0 / 3) * 3, math.ceil(lat1 / 3) * 3, 3):
        for lon in range(math.floor(lon0 / 3) * 3, math.ceil(lon1 / 3) * 3, 3):
            out.append(f"/vsicurl/https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
                       f"ESA_WorldCover_10m_2021_v200_N{lat:02d}W{-lon:03d}_Map.tif")
    return out


def warp_into(srcs, g, dtype, resampling, nodata, overview_level=None):
    dst = np.full((g["rows"], g["cols"]), nodata, dtype=dtype)
    for url in srcs:
        try:
            opts = {} if overview_level is None else {"overview_level": overview_level}
            with rasterio.open(url, **opts) as src:
                tmp = np.full_like(dst, nodata)
                reproject(rasterio.band(src, 1), tmp, src_nodata=src.nodata, dst_transform=g["transform"],
                          dst_crs="EPSG:3857", dst_nodata=nodata, resampling=resampling, num_threads=4)
                m = tmp != nodata
                dst[m] = tmp[m]
                log(f"grid {g['name']}: {url.split('/')[-1]} -> {m.sum()} cells")
        except rasterio.errors.RasterioIOError as e:
            log(f"grid {g['name']}: skip {url.split('/')[-1]} ({e.__class__.__name__})")
    return dst


def rasterize_classes(path, mapping, g):
    gdf = gpd.read_file(path).to_crs(3857)
    shapes = [(geom, mapping[c]) for c, geom in zip(gdf["class"], gdf.geometry) if c in mapping and geom is not None]
    # paint big classes first so detail (marsh, ponds) wins
    shapes.sort(key=lambda s: s[0].area, reverse=True)
    return features.rasterize(shapes, out_shape=(g["rows"], g["cols"]), transform=g["transform"], fill=0, dtype="uint8")


def hist_raster(g):
    """Pre-colonial (c.1800) habitat as cover code + 1 (0 = unknown), best source wins:
    SFEI EcoAtlas poster < SFEI historical ecology GIS < SFEI Hidden Nature SF."""
    import glob as _glob
    from covers import SFEI_ECOLOGY, SFEI_HIDDEN_NATURE, SFEI_POSTER_1800
    sources = [(INTERIM / "baylands_1800.geojson", "class", SFEI_POSTER_1800)]
    sources += [(f, "LegLabel", SFEI_ECOLOGY) for f in sorted(_glob.glob(str(RAW / "sfei_historical_ecology" / "*.geojson")))]
    sources += [(RAW / "sfei_hidden_nature_sf" / "sf_historical_habitats_2021.geojson", "HabitatCla", SFEI_HIDDEN_NATURE)]
    out = np.zeros((g["rows"], g["cols"]), np.uint8)
    for path, field, mapping in sources:
        try:
            gdf = gpd.read_file(path).to_crs(3857)
        except Exception as e:
            log(f"hist: skip {path} ({e.__class__.__name__})")
            continue
        shapes = [(geom, mapping[c] + 1) for c, geom in zip(gdf[field], gdf.geometry) if c in mapping and geom is not None and not geom.is_empty]
        if not shapes:
            continue
        shapes.sort(key=lambda s: s[0].area, reverse=True)
        tmp = features.rasterize(shapes, out_shape=(g["rows"], g["cols"]), transform=g["transform"], fill=0, dtype="uint8")
        out = np.where(tmp > 0, tmp, out)
        log(f"hist {g['name']}: {str(path).split('/')[-1]} -> {int((tmp > 0).sum())} cells")
    return out


def build(name):
    g = grid_def(name)
    log(f"grid {name}: z{g['z']} tiles x {g['tx0']}..{g['tx1']} y {g['ty0']}..{g['ty1']}, {g['rows']}x{g['cols']} vertices, {g['res']:.1f} m")
    _, lon0, lat0, lon1, lat1 = GRIDS[name]
    out = INTERIM / f"grid_{name}"
    ov = 1 if name == "region" else 0  # 3DEP overviews: 0 -> 20 m, 1 -> 40 m
    if not (out.parent / f"grid_{name}_elev.npy").exists():
        elev = warp_into(dem_tiles(lon0 - 0.2, lat0 - 0.2, lon1 + 0.2, lat1 + 0.2), g, np.float32, Resampling.bilinear, -9999.0, ov)
        np.save(f"{out}_elev.npy", elev)
    if not (out.parent / f"grid_{name}_wc.npy").exists():
        wc = warp_into(wc_tiles(lon0, lat0, lon1, lat1), g, np.uint8, Resampling.mode, 0, 1 if name == "region" else 0)
        np.save(f"{out}_wc.npy", wc)
    if not (out.parent / f"grid_{name}_fbuy.npy").exists():
        fb = warp_into([str(RAW / "hisdac" / "FBUY" / "data" / "FBUY.tif")], g, np.int16, Resampling.nearest, -32768)
        np.save(f"{out}_fbuy.npy", fb)
    np.save(f"{out}_b1800.npy", rasterize_classes(INTERIM / "baylands_1800.geojson", B1800, g))
    np.save(f"{out}_b1998.npy", rasterize_classes(INTERIM / "baylands_1998.geojson", B1998, g))
    np.save(f"{out}_hist.npy", hist_raster(g))
    meta = {k: (v if not isinstance(v, Affine) else list(v)[:6]) for k, v in g.items()}
    (INTERIM / f"grid_{name}_meta.json").write_text(json.dumps(meta, indent=1))
    log(f"grid {name}: done")


def main():
    for name in GRIDS:
        build(name)


if __name__ == "__main__":
    main()
