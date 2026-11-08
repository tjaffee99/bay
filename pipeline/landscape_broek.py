"""Trace Broek (1932) Plate II, Map III: 'Schematic map of landscape types of the Santa Clara
Valley 1931' (1:420,000), from the Utrecht University scan of J.O.M. Broek, *The Santa Clara
Valley, California: a study in landscape changes* (Utrecht: Oosthoek, 1932; open access,
https://dspace.library.uu.nl/handle/1874/302720).

The map's area symbols are hatch patterns; each pixel is classified from the texture around it
(31 px ~ 1.6 km window: long horizontal lines = orchard formation, dashed horizontal lines =
orchards mixed with small crops, sparse dots = small crops, dense dot grid = bay marshes,
blank = pastures, crosshatch = cities, halftone-screened diagonal hatching = the range-front
"border landscapes"), smoothed with a majority filter, polygonised and georeferenced by an
affine fit to 15 towns shown on the map (RMS ~0.7 km: the map is schematic).

Output: data/manual/landscape/broek_1931_landscape_types.geojson (+ cached class raster).
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pyproj
import shapely
from PIL import Image
from rasterio import features
from rasterio.transform import Affine
from scipy import ndimage

from common import log
from landscape import LINT, LRAW, M, OUT

CROP = (1596, 491, 3058, 3044)        # Map III panel inside Plate II (pixels of the 200 ppi scan)
FRAME = [(13, 38), (707, 38), (707, 297), (632, 302), (632, 2228), (91, 2228), (91, 743), (13, 743)]
CLS = ["nodata", "orchard", "orchard_mixed", "small_crops", "pasture", "marsh", "city",
       "diablo_front", "sc_wooded", "nsc_foothills", "outside"]
LEGEND = {
    "orchard": "Orchard formation",
    "orchard_mixed": "Orchards mixed with small crops",
    "small_crops": "Small crops",
    "pasture": "Pastures",
    "marsh": "Bay marshes",
    "city": "Cities and towns",
    "diablo_front": "Diablo Rangefront, grass-covered, uninhabited",
    "sc_wooded": "Southern Santa Cruz and Gabilan range front, wooded, uninhabited",
    "nsc_foothills": "Northern Santa Cruz foothills, with residential and agricultural settlements",
}
# town symbols on Map III (pixel in the panel crop) -> lon / lat of the town centre (1920s)
CONTROL = {
    "mission_sj": ((630, 116), (-121.9200, 37.5330)), "warm_springs": ((537, 207), (-121.9290, 37.4890)),
    "alviso": ((390, 259), (-121.9745, 37.4265)), "milpitas": ((498, 338), (-121.9070, 37.4325)),
    "agnew": ((345, 345), (-121.9510, 37.3960)), "los_altos": ((68, 183), (-122.1150, 37.3794)),
    "los_gatos": ((60, 669), (-121.9817, 37.2265)), "evergreen": ((502, 725), (-121.7840, 37.3200)),
    "new_almaden": ((228, 932), (-121.8180, 37.1750)), "coyote": ((428, 965), (-121.7390, 37.2140)),
    "morgan_hill": ((416, 1245), (-121.6545, 37.1305)), "san_martin": ((422, 1379), (-121.6105, 37.0850)),
    "gilroy": ((353, 1566), (-121.5680, 37.0055)), "san_juan_bautista": ((160, 1924), (-121.5380, 36.8455)),
    "hollister": ((361, 2086), (-121.4010, 36.8525)),
}


def classify(a: np.ndarray) -> np.ndarray:
    ink = a < 125
    win = 31

    def frac(m, w=win):
        return ndimage.uniform_filter(m.astype(np.float32), w)
    hlong = ndimage.binary_opening(ink, structure=np.ones((1, 27), bool))
    hshort = ndimage.binary_opening(ink, structure=np.ones((1, 9), bool)) & \
        ~ndimage.binary_dilation(hlong, structure=np.ones((1, 5), bool))
    vert = ndimage.binary_opening(ink, structure=np.ones((9, 1), bool))
    d1 = ndimage.binary_opening(ink, structure=np.eye(13, dtype=bool))
    d2 = ndimage.binary_opening(ink, structure=np.fliplr(np.eye(13, dtype=bool)))
    lines = hlong | hshort | vert | d1 | d2
    rest = ink & ~ndimage.binary_dilation(lines, iterations=2)
    lab, n = ndimage.label(rest)
    sizes = ndimage.sum(rest, lab, range(1, n + 1))
    dots = np.zeros_like(ink)
    for sl, s in zip(ndimage.find_objects(lab), sizes):
        h = sl[0].stop - sl[0].start
        w = sl[1].stop - sl[1].start
        if 4 <= s <= 70 and h <= 10 and w <= 10:
            dots[(sl[0].start + sl[0].stop) // 2, (sl[1].start + sl[1].stop) // 2] = True
    hf = np.abs(a - ndimage.gaussian_filter(a, 1.2))
    paper = ~ndimage.binary_dilation(ink, iterations=2)
    screen = ndimage.uniform_filter(np.where(paper, hf, 0), 21) / \
        np.maximum(ndimage.uniform_filter(paper.astype(np.float32), 21), 0.05)
    hl, hs, vt = frac(hlong), frac(hshort), frac(vert)
    dt = frac(dots, 41) * 41 * 41
    inkf = frac(ink)
    scr = screen > 12
    c = np.zeros(a.shape, np.uint8)
    cream = ~scr
    c[cream] = 4
    c[cream & (dt > 1.5)] = 3
    c[cream & (dt > 10)] = 5
    c[cream & (hs > 0.03)] = 2
    c[cream & (hl > 0.05)] = 1
    c[scr] = 10
    c[scr & (frac(d2) > 0.012)] = 8
    c[scr & (frac(d2) > 0.012) & ((hl + hs) > 0.04)] = 9
    c[scr & (frac(d1) > 0.012)] = 7
    c[(inkf > 0.33) & (vt > 0.05)] = 6

    def mode(c, size):
        best = np.zeros(c.shape, np.float32)
        out = c.copy()
        for k in range(1, len(CLS)):
            f = ndimage.uniform_filter((c == k).astype(np.float32), size)
            m = f > best
            best[m] = f[m]
            out[m] = k
        return out
    c = mode(mode(c, 21), 21)
    # cities: keep only real towns (>= 0.4 km2 blocks); town dots / road knots go to their surroundings
    lab, n = ndimage.label(c == 6)
    sizes = ndimage.sum(c == 6, lab, range(1, n + 1))
    small = np.isin(lab, np.nonzero(sizes < 150)[0] + 1)
    if small.any():
        c2 = c.copy()
        c2[small] = 0
        idx = ndimage.distance_transform_edt(c2 == 0, return_distances=False, return_indices=True)
        c[small] = c2[idx[0][small], idx[1][small]]
    # outside the T-shaped frame = nodata
    fr = np.zeros(a.shape, np.uint8)
    features.rasterize([(shapely.Polygon(FRAME).buffer(-12, join_style=2), 1)], out=fr)  # off the frame line
    c[fr == 0] = 0
    return c


def affine_fit():
    T = pyproj.Transformer.from_crs(4326, M, always_xy=True)
    px = np.array([p for p, _ in CONTROL.values()], float)
    ll = np.array([l for _, l in CONTROL.values()], float)
    X, Y = T.transform(ll[:, 0], ll[:, 1])
    A = np.column_stack([px, np.ones(len(px))])
    cx, *_ = np.linalg.lstsq(A, X, rcond=None)
    cy, *_ = np.linalg.lstsq(A, Y, rcond=None)
    r = np.hypot(A @ cx - X, A @ cy - Y)
    log(f"broek map III georeference: affine on {len(px)} towns, RMS {np.sqrt((r ** 2).mean()):.0f} m, max {r.max():.0f} m")
    return Affine(cx[0], cx[1], cx[2], cy[0], cy[1], cy[2]), float(np.sqrt((r ** 2).mean()))


def broek_1931() -> gpd.GeoDataFrame:
    out = OUT / "broek_1931_landscape_types.geojson"
    if out.exists():
        return gpd.read_file(out)
    cache = LINT / "broek_map3_classes.npy"
    if cache.exists():
        c = np.load(cache)
    else:
        im = Image.open(LRAW / "broek1932_plate2.jpg").crop(CROP).convert("L")
        c = classify(np.asarray(im).astype(np.float32))
        np.save(cache, c)
    tf, rms = affine_fit()
    rows = []
    for geom, v in features.shapes(c, mask=c > 0, transform=tf, connectivity=4):
        cls = CLS[int(v)]
        poly = shapely.geometry.shape(geom)
        if poly.area < 2e5:     # < 20 ha: speck
            continue
        rows.append(dict(cls=cls, legend=LEGEND.get(cls, "outside the study area"), geometry=poly.simplify(60)))
    g = gpd.GeoDataFrame(rows, crs=M)
    g = g.dissolve("cls", as_index=False, aggfunc="first").explode(index_parts=False).reset_index(drop=True)
    g = g[g.cls != "outside"].copy()
    g["snapshot_year"] = 1931
    g["georef_rms_m"] = round(rms)
    g["source"] = "broek_1932"
    g["source_url"] = "https://dspace.library.uu.nl/handle/1874/302720"
    g = g.to_crs(4326)
    from landscape import write_geojson
    write_geojson(g, out, precision=5)
    log("broek 1931 classes (km2):\n" + (g.to_crs(M).assign(a=lambda d: d.area / 1e6).groupby("cls").a.sum().round(1).to_string()))
    return g
