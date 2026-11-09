"""Dated built-up extents of the region's older towns, read from USGS historical topographic maps.

  python -I extents.py sheet  TOWN SHEET [--preview]   render + align one sheet over a town, block stats (cache)
  python -I extents.py build  TOWN [YEAR ...]          classify blocks, write data/manual/region_extents/<town>_<year>.geojson
  python -I extents.py check  TOWN                     validation numbers + check PNG
  python -I extents.py all    TOWN                     sheet (every sheet of every snapshot) + build + check

Method (details and per-snapshot notes in ../README.md):

1. Sheets: USGS Historical Topographic Map Collection GeoTIFFs (public domain, TNM Access API; FGDC
   metadata for survey / aerial-photo years). The 1:62,500 15' sheets of 1885-1915 draw a closely
   built block front as a heavy black band along the street and a scattered house as a small solid
   square; the 1:24,000 7.5' sheets (and 1:62,500 editions) of 1939-1953 tint the built-up area
   red / pink and draw only landmark buildings inside it (houses outside the tint as squares).
2. Each sheet is resampled into UTM 10N (WGS84) at RES m through its own registration and the NOAA
   NADCON grid (NAD27 -> WGS84), masked to its quadrangle, and aligned to today's street centrelines
   (Overture / OpenStreetMap) by windowed cross-correlation of the black ink (the 1890s surveys are
   ~100-250 m off; the 1940s sheets a few metres), fitted as a constant or affine shift by consensus.
3. Blocks: today's street centrelines (Overture roads, motorways and service roads left out)
   polygonised and clipped to the town (TIGER 2024 places): the block is the unit of the extent.
4. Per block: heavy ink (black, lines thinner than ~0.15 mm removed by an opening), split into
   *bands* (ink runs >= ~40 m long: built frontage, large buildings) and *squares* (single houses);
   built frontage share = band length / frontage length + 15 m per square; on the tint sheets the
   share of the block under the urban tint. A block is built up when its share passes the
   threshold of its sheet style (see THRESH); holes under HOLE_HA are filled, specks under MIN_HA
   dropped, and the result is clipped to today's land.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "data" / "raw" / "region_extents"
INT = ROOT / "data" / "interim" / "region_extents"
OUT = ROOT / "data" / "manual" / "region_extents"
PROJ_DIR = ROOT / "data" / "raw" / "proj"
OVT = ROOT / "data" / "raw" / "overture" / "2026-10-21.0"
TIGER = ROOT / "data" / "raw" / "tiger" / "tl_2024_06_place.zip"
TIF = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/"
PDF = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/"
os.environ.setdefault("CURL_CA_BUNDLE", "/root/.ccr/ca-bundle.crt")
UTM = "EPSG:32610"
RES = 2.5

# --------------------------------------------------------------------------- sheets
# key -> USGS HTMC scan: file (GeoTIFF name), quad (NAD27 W, S, E, N), scale, edition (date on map),
# year (what the map shows: survey year, or aerial-photo year of the 1939-53 sheets), style.
S = {}


def sheet(key, file, quad, scale, edition, year, style, note=""):
    S[key] = dict(key=key, file=file, quad=quad, scale=scale, edition=edition, year=year, style=style, note=note)


Q15 = lambda w, s: (w, s, w + 0.25, s + 0.25)      # noqa: E731
Q75 = lambda w, s: (w, s, w + 0.125, s + 0.125)    # noqa: E731
sheet("sf1895", "CA_San%20Francisco_298889_1895_62500_geo.tif", Q15(-122.5, 37.75), 62500, 1895, 1894, "early",
      "surveyed 1892-94")
sheet("sf1915", "CA_San%20Francisco_298897_1915_62500_geo.tif", Q15(-122.5, 37.75), 62500, 1915, 1914, "early",
      "1915 edition: surveyed 1892-94, culture revised in 1914 (collar note)")
sheet("concord1897", "CA_Concord_297157_1897_62500_geo.tif", Q15(-122.25, 37.75), 62500, 1897, 1894, "early",
      "surveyed 1893-94 (collar), engraved Apr 1897")
sheet("concord1915", "CA_Concord_297163_1915_62500_geo.tif", Q15(-122.25, 37.75), 62500, 1915, 1914, "early",
      "edition of June 1915: surveyed 1893-94, culture revised in part in 1913-14 (collar note)")
sheet("concord1942", "CA_Concord_465521_1942_62500_geo.tif", Q15(-122.25, 37.75), 62500, 1942, 1939, "tint",
      "aerial photographs 1939")
sheet("haywards1899", "CA_Haywards_297665_1899_62500_geo.tif", Q15(-122.25, 37.5), 62500, 1899, 1896, "early",
      "surveyed 1896 (1901 imprint)")
sheet("hayward1915", "CA_Hayward_297660_1915_62500_geo.tif", Q15(-122.25, 37.5), 62500, 1915, 1914, "early",
      "surveyed 1914 (1939 imprint)")
sheet("hayward1942", "CA_Hayward_465728_1942_62500_geo.tif", Q15(-122.25, 37.5), 62500, 1942, 1939, "tint",
      "aerial photographs 1939")
sheet("oaklandwest1949", "CA_Oakland%20West_293623_1949_24000_geo.tif", Q75(-122.375, 37.75), 24000, 1949, 1946,
      "tint", "aerial photographs 1946, field check 1947")
sheet("oaklandeast1947", "CA_Oakland%20East_293612_1947_24000_geo.tif", Q75(-122.25, 37.75), 24000, 1947, 1946,
      "tint", "aerial photographs 1946, field check 1947")
sheet("richmond1947", "CA_Richmond_294667_1947_24000_geo.tif", Q75(-122.375, 37.875), 24000, 1947, 1946, "tint",
      "aerial photographs 1946, field check 1947")
sheet("briones1947", "CA_Briones%20Valley_288606_1947_24000_geo.tif", Q75(-122.25, 37.875), 24000, 1947, 1946,
      "tint", "aerial photographs 1946, field check 1947")
sheet("sanleandro1947", "CA_San%20Leandro_300122_1947_24000_geo.tif", Q75(-122.25, 37.625), 24000, 1947, 1946,
      "tint", "1947 edition (photos c. 1946)")
sheet("hayward1947", "CA_Hayward_291242_1947_24000_geo.tif", Q75(-122.125, 37.625), 24000, 1947, 1946, "tint",
      "aerial photographs 1946, survey 1947")
sheet("sanquentin1948", "CA_San%20Quentin_300194_1948_24000_geo.tif", Q75(-122.5, 37.875), 24000, 1948, 1947,
      "tint", "aerial photographs 1947")
sheet("newark1947", "CA_Newark_293493_1947_24000_geo.tif", Q75(-122.125, 37.5), 24000, 1947, 1946, "tint",
      "aerial photographs 1946")
sheet("sanjose1889", "CA_San%20Jose_301582_1889_62500_geo.tif", Q15(-122.0, 37.25), 62500, 1889, 1885, "early",
      "surveyed 1885 (1939 reprint)")
sheet("sanjose1897", "CA_San%20Jose_298899_1897_62500_geo.tif", Q15(-122.0, 37.25), 62500, 1897, 1895, "early",
      "surveyed 1895")
sheet("sanjose1943", "CA_San%20Jose_466308_1943_62500_geo.tif", Q15(-122.0, 37.25), 62500, 1943, 1939, "tint",
      "aerial photographs 1939")
sheet("sanjosewest1953", "CA_San%20Jose%20West_300105_1953_24000_geo.tif", Q75(-122.0, 37.25), 24000, 1953, 1948,
      "tint", "aerial photographs 1948, survey 1953")
sheet("sanjoseeast1953", "CA_San%20Jose%20East_300099_1953_24000_geo.tif", Q75(-121.875, 37.25), 24000, 1953, 1948,
      "tint", "aerial photographs 1948, survey 1953")
sheet("milpitas1953", "CA_Milpitas_292969_1953_24000_geo.tif", Q75(-122.0, 37.375), 24000, 1953, 1948, "tint",
      "aerial photographs 1948, survey 1953")
sheet("paloalto1899", "CA_Palo%20Alto_298453_1899_62500_geo.tif", Q15(-122.25, 37.25), 62500, 1899, 1895, "early",
      "surveyed 1895")
sheet("paloalto1943", "CA_Palo%20Alto_298463_1943_62500_geo.tif", Q15(-122.25, 37.25), 62500, 1943, 1940, "tint",
      "aerial photographs 1940")
sheet("paloalto1953", "CA_Palo%20Alto_293907_1953_24000_geo.tif", Q75(-122.25, 37.375), 24000, 1953, 1948, "tint",
      "aerial photographs 1948, survey 1953")
sheet("mountainview1953", "CA_Mountain%20View_293234_1953_24000_geo.tif", Q75(-122.125, 37.375), 24000, 1953, 1948,
      "tint", "aerial photographs 1948, survey 1953")
sheet("woodside1953", "CA_Woodside_301429_1953_24000_geo.tif", Q75(-122.375, 37.375), 24000, 1953, 1948, "tint",
      "aerial photographs 1948, field check 1953")
sheet("redwoodpoint1948", "CA_Redwood%20Point_294610_1948_24000_geo.tif", Q75(-122.25, 37.5), 24000, 1948, 1948,
      "tint", "1948 edition")
sheet("sanmateo1896", "CA_San%20Mateo_298916_1896_62500_geo.tif", Q15(-122.5, 37.5), 62500, 1896, 1892, "early",
      "surveyed 1892")
sheet("sanmateo1915", "CA_San%20Mateo_298922_1915_62500_geo.tif", Q15(-122.5, 37.5), 62500, 1915, 1915, "early",
      "1915 edition of the 1892 survey")
sheet("sanmateo1943", "CA_San%20Mateo_466324_1943_62500_geo.tif", Q15(-122.5, 37.5), 62500, 1943, 1939, "tint",
      "aerial photographs 1939")
sheet("sanmateo1947", "CA_San%20Mateo_300157_1947_24000_geo.tif", Q75(-122.375, 37.5), 24000, 1947, 1946, "tint",
      "aerial photographs 1946, field check 1947")
sheet("tamalpais1897", "CA_Tamalpais_298980_1897_62500_geo.tif", Q15(-122.75, 37.75), 62500, 1897, 1895, "early",
      "surveyed 1895")
sheet("tamalpais1941", "CA_Tamalpais_301788_1941_62500_geo.tif", Q15(-122.75, 37.75), 62500, 1941, 1939, "tint",
      "aerial photographs 1939")
sheet("sanrafael1954", "CA_San%20Rafael_300201_1954_24000_geo.tif", Q75(-122.625, 37.875), 24000, 1954, 1952,
      "tint", "aerial photographs 1952, field check 1954")
sheet("karquines1898", "CA_Karquines_297860_1898_62500_geo.tif", Q15(-122.25, 38.0), 62500, 1898, 1896, "early",
      "surveyed 1896")
sheet("carquinez1942", "CA_Carquinez_297034_1942_62500_geo.tif", Q15(-122.25, 38.0), 62500, 1942, 1937, "tint",
      "aerial photographs 1937")
sheet("benicia1950", "CA_Benicia_288319_1950_24000_geo.tif", Q75(-122.25, 38.0), 24000, 1950, 1948, "tint",
      "aerial photographs 1948, field check 1950")
sheet("portchicago1951", "CA_Port%20Chicago_294325_1951_24000_geo.tif", Q75(-122.125, 38.0), 24000, 1951, 1948,
      "tint", "aerial photographs 1948, survey 1950")


def sheet_path(sh):
    """The sheet's GeoPDF (the full 600-700 ppi scan; the GeoTIFF is a 300 ppi resample)."""
    name = sh["file"].replace("_geo.tif", "_geo.pdf")
    p = RAW / "topo" / name.replace("%20", "_")
    if not p.exists() or p.stat().st_size < 10000:
        import subprocess
        p.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["curl", "-sS", "-L", "-m", "900", "-o", str(p), f"{PDF}{sh['scale']}/{name}"], check=True)
    return p


# --------------------------------------------------------------------------- towns
# places: TIGER 2024 GEOIDs; bbox (lon/lat) bounds the processing (historic core + growth to c. 1950);
# snaps: year -> sheet keys (one survey generation per snapshot)
EARLY_OAK = ["sf1895", "concord1897", "haywards1899"]
REV_OAK = ["sf1915", "concord1915", "hayward1915"]
TOWNS = {
    "oakland": dict(name="Oakland (incl. Emeryville, Piedmont)", places=["0653000", "0622594", "0656938"],
                    bbox=(-122.335, 37.725, -122.155, 37.855),
                    snaps={1894: EARLY_OAK, 1914: REV_OAK, 1939: ["concord1942", "hayward1942"],
                           1946: ["oaklandwest1949", "oaklandeast1947", "richmond1947", "briones1947",
                                  "sanleandro1947"]}),
    "berkeley": dict(name="Berkeley (incl. Albany)", places=["0606000", "0600674"],
                     bbox=(-122.33, 37.845, -122.23, 37.91),
                     snaps={1894: ["sf1895", "concord1897"], 1914: ["sf1915", "concord1915"],
                            1946: ["richmond1947", "oaklandwest1949", "briones1947", "oaklandeast1947"]}),
    "alameda": dict(name="Alameda", places=["0600562"], bbox=(-122.34, 37.74, -122.22, 37.80),
                    snaps={1894: ["sf1895", "concord1897"], 1914: ["sf1915", "concord1915"],
                           1946: ["oaklandwest1949", "oaklandeast1947"]}),
    "san_jose": dict(name="San José (incl. Santa Clara)", places=["0668000", "0669084"],
                     bbox=(-122.00, 37.28, -121.83, 37.40),
                     snaps={1885: ["sanjose1889"], 1895: ["sanjose1897"], 1939: ["sanjose1943"],
                            1948: ["sanjosewest1953", "sanjoseeast1953", "milpitas1953"]}),
    "san_leandro": dict(name="San Leandro", places=["0668084"], bbox=(-122.21, 37.67, -122.10, 37.74),
                        snaps={1896: ["haywards1899"], 1914: ["hayward1915"], 1939: ["hayward1942"],
                               1946: ["sanleandro1947", "hayward1947"]}),
    "hayward": dict(name="Hayward", places=["0633000"], bbox=(-122.15, 37.61, -122.00, 37.70),
                    snaps={1896: ["haywards1899"], 1914: ["hayward1915"], 1939: ["hayward1942"],
                           1946: ["hayward1947", "sanleandro1947", "newark1947"]}),
    "richmond": dict(name="Richmond (incl. El Cerrito, San Pablo)", places=["0660620", "0621796", "0668294"],
                     bbox=(-122.42, 37.90, -122.29, 37.99),
                     snaps={1894: ["sf1895"], 1914: ["sf1915"], 1946: ["richmond1947", "sanquentin1948"]}),
    "palo_alto": dict(name="Palo Alto (incl. Mayfield)", places=["0655282"], bbox=(-122.19, 37.40, -122.10, 37.465),
                      snaps={1895: ["paloalto1899"], 1940: ["paloalto1943"],
                             1948: ["paloalto1953", "mountainview1953"]}),
    "redwood_city": dict(name="Redwood City", places=["0660102"], bbox=(-122.27, 37.45, -122.19, 37.51),
                         snaps={1895: ["paloalto1899"], 1940: ["paloalto1943"],
                                1948: ["paloalto1953", "woodside1953", "redwoodpoint1948"]}),
    "san_mateo": dict(name="San Mateo (incl. Burlingame)", places=["0668252", "0609066"],
                      bbox=(-122.39, 37.52, -122.28, 37.60),
                      snaps={1892: ["sanmateo1896"], 1915: ["sanmateo1915"], 1939: ["sanmateo1943"],
                             1946: ["sanmateo1947"]}),
    "san_rafael": dict(name="San Rafael", places=["0668364"], bbox=(-122.57, 37.95, -122.48, 38.01),
                       snaps={1895: ["tamalpais1897", "sf1895"], 1939: ["tamalpais1941"],
                              1952: ["sanrafael1954", "sanquentin1948"]}),
    "martinez": dict(name="Martinez", places=["0646114"], bbox=(-122.16, 37.99, -122.10, 38.03),
                     snaps={1896: ["karquines1898"], 1937: ["carquinez1942"],
                            1948: ["benicia1950", "briones1947", "portchicago1951"]}),
}


# --------------------------------------------------------------------------- frames
_T = {}


def tf(a, b):
    import pyproj
    if (a, b) not in _T:
        _T[(a, b)] = pyproj.Transformer.from_crs(a, b, always_xy=True)
    return _T[(a, b)]


def nad27_tfs(crs_wkt):
    """WGS84 -> NAD27 geographic (NADCON) and NAD27 geographic -> the sheet's projection."""
    import pyproj
    from pyproj.transformer import TransformerGroup
    key = ("nad27", crs_wkt)
    if key not in _T:
        pyproj.datadir.append_data_dir(str(PROJ_DIR))
        crs = pyproj.CRS.from_wkt(crs_wkt)
        geo = crs.geodetic_crs
        tg = TransformerGroup("EPSG:4326", geo, always_xy=True,
                              area_of_interest=pyproj.aoi.AreaOfInterest(-123.5, 36.5, -121.0, 38.8))
        _T[key] = (tg.transformers[0], pyproj.Transformer.from_crs(geo, crs, always_xy=True))
    return _T[key]


class Grid:
    def __init__(self, bbox_ll, res=RES):
        t = tf("EPSG:4326", UTM)
        w, s, e, n = bbox_ll
        xs, ys = t.transform([w, e, w, e], [s, s, n, n])
        self.res = res
        self.x0 = math.floor(min(xs) / res) * res
        self.y1 = math.ceil(max(ys) / res) * res
        self.W = int(math.ceil((max(xs) - self.x0) / res))
        self.H = int(math.ceil((self.y1 - min(ys)) / res))

    def xy(self, i, j):
        return self.x0 + (np.asarray(i) + 0.5) * self.res, self.y1 - (np.asarray(j) + 0.5) * self.res

    @property
    def transform(self):
        from rasterio.transform import Affine
        return Affine(self.res, 0, self.x0, 0, -self.res, self.y1)


def render(sh, grid, model=None, step=16, pdf_step=1):
    """Sheet resampled into the grid (RGB uint8, white outside) + inside-quad mask. model: shift
    (dX, dY) in m added to a modern position to find it on the map. Reads the GeoPDF scan through
    its own registration (topo_farmsteads.GeoPDF: LGIDict CTM, polyconic NAD27)."""
    import cv2
    sys.path.insert(0, str(ROOT / "pipeline"))
    import topo_farmsteads as TF
    path = sheet_path(sh)
    pdf = TF.GeoPDF(path)
    crs = TF.crs_for(pdf.g["proj"])
    a_, b_, c_, d_, e_, f_ = pdf.g["georef"]["ctm"]
    s_, page_h = pdf.g["georef"]["s"], pdf.g["georef"]["page_h"]
    Ainv = np.linalg.inv(np.array([[a_, c_], [b_, d_]]))
    ci = np.arange(0, grid.W + step, step)
    cj = np.arange(0, grid.H + step, step)
    X, Y = np.meshgrid(*grid.xy(ci, cj))
    if model is not None:
        dX, dY = shift_xy(model, X, Y)
        X, Y = X + dX, Y + dY
    lon, lat = tf(UTM, "EPSG:4326").transform(X, Y)
    t_ll, t_pr = nad27_tfs(crs.to_wkt())
    lo27, la27 = t_ll.transform(lon, lat)
    lo27 = np.asarray(lo27); la27 = np.asarray(la27)
    w, s, e, n = sh["quad"]
    inq = ((lo27 >= w) & (lo27 <= e) & (la27 >= s) & (la27 <= n)).astype(np.float32)
    px, py = t_pr.transform(lo27, la27)
    uv = Ainv @ np.vstack([np.asarray(px).ravel() - e_, np.asarray(py).ravel() - f_])
    col = (uv[0] * s_).reshape(X.shape).astype(np.float32)
    row = ((page_h - uv[1]) * s_).reshape(X.shape).astype(np.float32)
    ok = inq > 0
    if not ok.any():
        return None, None
    c0 = int(max(0, np.floor(col[ok].min()) - 4)); c1 = int(min(pdf.W, np.ceil(col[ok].max()) + 4))
    r0 = int(max(0, np.floor(row[ok].min()) - 4)); r1 = int(min(pdf.H, np.ceil(row[ok].max()) + 4))
    arr = np.ascontiguousarray(pdf.read(r0, r1, c0, c1, step=pdf_step))
    pdf._cache.clear()
    pdf.doc.close()
    del pdf
    col = (col - c0) / pdf_step; row = (row - r0) / pdf_step
    img = np.full((grid.H, grid.W, 3), 255, np.uint8)
    valid = np.zeros((grid.H, grid.W), bool)
    ii = (np.arange(grid.W, dtype=np.float32) / step)
    for j0 in range(0, grid.H, 1024):
        j1 = min(grid.H, j0 + 1024)
        jj = (np.arange(j0, j1, dtype=np.float32) / step)
        mx = np.ascontiguousarray(np.broadcast_to(ii[None, :], (j1 - j0, grid.W)))
        my = np.ascontiguousarray(np.broadcast_to(jj[:, None], (j1 - j0, grid.W)))
        cf = cv2.remap(col, mx, my, cv2.INTER_LINEAR)
        rf = cv2.remap(row, mx, my, cv2.INTER_LINEAR)
        img[j0:j1] = cv2.remap(arr, cf, rf, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                               borderValue=(255, 255, 255))
        valid[j0:j1] = cv2.remap(inq, mx, my, cv2.INTER_LINEAR) > 0.5
    img[~valid] = 255
    return img, valid


def shift_xy(m, X, Y):
    if not m or not m.get("aligned"):
        return np.zeros_like(X), np.zeros_like(Y)
    xk = (X - m["xc"]) / 1000.0
    yk = (Y - m["yc"]) / 1000.0
    return (m["cx"][0] + m["cx"][1] * xk + m["cx"][2] * yk,
            m["cy"][0] + m["cy"][1] * xk + m["cy"][2] * yk)


# --------------------------------------------------------------------------- ink / tint
def _strips(img, fn):
    out = np.zeros(img.shape[:2], bool)
    for j0 in range(0, img.shape[0], 1024):
        out[j0:j0 + 1024] = fn(img[j0:j0 + 1024].astype(np.int16))
    return out


def ink_mask(img, style):
    """Black ink: dark in every channel and neutral (contours are brown, water blue, tint pink)."""
    mx = img[::7, ::7].max(2)
    paper = np.percentile(mx[mx > 150], 60) if (mx > 150).any() else 235

    def f(b):
        R, G, B = b[:, :, 0], b[:, :, 1], b[:, :, 2]
        return (b.max(2) < 0.55 * paper) & (np.abs(R - G) < 45) & (B - R < 25) & (G - R < 25)
    return _strips(img, f)


def tint_mask(img):
    """Red / pink urban-area tint of the 1939-53 sheets (as topo_farmsteads.urban_tint)."""
    def f(b):
        R, G, B = b[:, :, 0], b[:, :, 1], b[:, :, 2]
        return (R - G > 22) & (G - B < 18) & (R > 190)
    return _strips(img, f)


def line_kernels(length_px, n=12):
    import cv2
    ks = []
    L = int(length_px) | 1
    for k in range(n):
        a = math.pi * k / n
        m = np.zeros((L, L), np.uint8)
        c = L // 2
        dx, dy = math.cos(a) * c, math.sin(a) * c
        cv2.line(m, (int(round(c - dx)), int(round(c - dy))), (int(round(c + dx)), int(round(c + dy))), 1, 1)
        ks.append(m)
    return ks


def heavy_and_bands(ink, res, sh):
    """Heavy ink (thin lines removed) and its elongated part (bands: built frontage)."""
    import cv2
    mm = sh["scale"] / 1000.0                 # metres per paper mm
    r_open = max(1, int(round(0.15 * mm / res / 2)))      # remove lines thinner than ~0.15 mm
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r_open + 1,) * 2)
    heavy = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_OPEN, k)
    L = 40.0 / res if sh["scale"] >= 62500 else 30.0 / res
    bands = np.zeros_like(heavy)
    for kk in line_kernels(L):
        bands |= cv2.morphologyEx(heavy, cv2.MORPH_OPEN, kk)
    return heavy.astype(bool), bands.astype(bool)


# --------------------------------------------------------------------------- vectors
def town_clip(town):
    import geopandas as gpd
    import shapely
    pl = gpd.read_file(f"zip://{TIGER}")
    pl = pl[pl.GEOID.isin(TOWNS[town]["places"])].to_crs(UTM)
    g = shapely.union_all(list(pl.geometry)).buffer(0)
    w, s, e, n = TOWNS[town]["bbox"]
    box = shapely.box(*tf("EPSG:4326", UTM).transform(w, s), *tf("EPSG:4326", UTM).transform(e, n))
    return g.intersection(box)


def land_poly(bounds):
    """Today's land (data/interim/land_modern.fgb) within bounds (UTM)."""
    import geopandas as gpd
    import shapely
    p = ROOT / "data" / "interim" / "land_modern.fgb"
    g = gpd.read_file(p).to_crs(UTM)
    return shapely.union_all(list(g.geometry)).buffer(0).intersection(shapely.box(*bounds))


def to_utm(g):
    import shapely
    t = tf("EPSG:4326", UTM)
    return shapely.transform(g, lambda c: np.column_stack(t.transform(c[:, 0], c[:, 1])))


def modern_roads(bounds_ll, classes=None):
    import duckdb
    import shapely
    w, s, e, n = bounds_ll
    out = []
    con = duckdb.connect()
    con.execute("LOAD spatial;")
    for f in ("roads_local", "roads_region"):
        q = (f"select class, ST_AsWKB(geometry) g from read_parquet('{OVT / (f + '.parquet')}') "
             f"where ST_XMin(geometry) < {e} and ST_XMax(geometry) > {w} and ST_YMin(geometry) < {n} "
             f"and ST_YMax(geometry) > {s}")
        for cls, g in con.execute(q).fetchall():
            if classes and cls not in classes:
                continue
            out.append((cls, shapely.from_wkb(bytes(g))))
    return out


BLOCK_CLASSES = {"trunk", "primary", "secondary", "tertiary", "residential", "unclassified", "living_street"}


def blocks(town, clip):
    """Today's street blocks (UTM polygons) inside the town clip."""
    import geopandas as gpd
    import shapely
    cache = INT / f"blocks_{town}.parquet"
    if cache.exists():
        return gpd.read_parquet(cache)
    w, s, e, n = TOWNS[town]["bbox"]
    lines = [to_utm(g) for c, g in modern_roads((w - .01, s - .01, e + .01, n + .01), BLOCK_CLASSES)]
    lines.append(clip.boundary)
    net = shapely.union_all(lines)
    polys = list(shapely.get_parts(shapely.polygonize(shapely.get_parts(net))))
    polys = [p for p in polys if p.area > 200 and clip.contains(p.representative_point())]
    polys = [p.intersection(clip) for p in polys]
    polys = [p for p in polys if not p.is_empty and p.area > 200]
    g = gpd.GeoDataFrame({"bid": np.arange(len(polys))}, geometry=polys, crs=UTM)
    g.to_parquet(cache)
    return g


# --------------------------------------------------------------------------- alignment
def align_sheet(key):
    """Shift of a whole sheet against today's street centrelines (model: modern position + shift =
    map position), by cross-correlation of its black ink with rasterised centrelines in 2.5 km
    windows over the quadrangle (5 m pixels). Cached per sheet."""
    INT.mkdir(parents=True, exist_ok=True)
    p = INT / f"align_{key}.json"
    if p.exists():
        return json.loads(p.read_text())
    sh = S[key]
    w, s, e, n = sh["quad"]
    grid = Grid((w - 0.003, s - 0.003, e + 0.003, n + 0.003), 5.0)
    img, valid = render(sh, grid, None, pdf_step=2)
    ink = ink_mask(img, sh["style"]).astype(np.float32)
    del img
    m = align(sh, grid, ink, valid, (w, s, e, n))
    p.write_text(json.dumps(m, indent=1))
    return m


def align(sh, grid, small, vs, bounds_ll):
    import cv2
    res = grid.res
    rr = np.zeros(small.shape, np.uint8)
    w, s, e, n = bounds_ll
    for cls, g in modern_roads((w - .01, s - .01, e + .01, n + .01),
                               {"primary", "secondary", "tertiary", "residential", "unclassified", "trunk"}):
        g = to_utm(g)
        for line in getattr(g, "geoms", [g]):
            c = np.asarray(line.coords)
            px = np.column_stack([(c[:, 0] - grid.x0) / res, (grid.y1 - c[:, 1]) / res])
            cv2.polylines(rr, [np.round(px).astype(np.int32)], False, 1, 1)
    Rb = cv2.GaussianBlur(rr.astype(np.float32), (0, 0), 1.5)
    Ib = cv2.GaussianBlur(small, (0, 0), 1.5)
    early = sh["style"] == "early"
    win = int(2500 / res)
    S_ = int((420 if early else 120) / res)
    sup = max(2, int(50 / res))
    rows = []
    for y in range(S_, Ib.shape[0] - win - S_, win // 2):
        for x in range(S_, Ib.shape[1] - win - S_, win // 2):
            if vs[y:y + win, x:x + win].mean() < 0.9:
                continue
            tpl = Rb[y:y + win, x:x + win]
            if tpl.sum() < 3 * win or Ib[y:y + win, x:x + win].sum() < 3 * win:
                continue
            cc = cv2.matchTemplate(Ib[y - S_:y + win + S_, x - S_:x + win + S_], tpl, cv2.TM_CCOEFF_NORMED)
            _, r1, _, (lx, ly) = cv2.minMaxLoc(cc)
            cc2 = cc.copy()
            cc2[max(ly - sup, 0):ly + sup + 1, max(lx - sup, 0):lx + sup + 1] = -1
            r2 = cc2.max()
            if r1 >= 0.12 and r1 - r2 >= 0.015:
                X, Y = grid.x0 + (x + win / 2) * res, grid.y1 - (y + win / 2) * res
                rows.append((X, Y, (lx - S_) * res, -(ly - S_) * res, r1, r1 - r2))
    out = {"n_windows": len(rows), "windows": [[round(float(v), 2) for v in r] for r in rows]}
    if len(rows) < 2:
        out.update(aligned=False, reason="too few windows")
        return out
    A = np.array(rows)
    tol = 40.0 if early else 12.0
    best_w, use = -1, None
    for k in range(len(A)):
        inl = np.hypot(A[:, 2] - A[k, 2], A[:, 3] - A[k, 3]) <= 2 * tol
        wsum = A[inl, 4].sum()
        if wsum > best_w:
            best_w, use = wsum, inl
    if use.sum() < 2 or use.sum() < 0.35 * len(A):
        out.update(aligned=False, reason=f"no consensus ({int(use.sum())} of {len(A)})")
        return out
    xc, yc = A[use, 0].mean(), A[use, 1].mean()
    Xm = np.column_stack([np.ones(len(A)), (A[:, 0] - xc) / 1000, (A[:, 1] - yc) / 1000])
    cx = np.array([np.median(A[use, 2]), 0, 0]); cy = np.array([np.median(A[use, 3]), 0, 0])
    model = "constant"
    for _ in range(6):
        if use.sum() >= 6 and np.ptp(A[use, 0]) > 3000 and np.ptp(A[use, 1]) > 3000:
            ax, *_ = np.linalg.lstsq(Xm[use], A[use, 2], rcond=None)
            ay, *_ = np.linalg.lstsq(Xm[use], A[use, 3], rcond=None)
            if np.abs(ax[1:]).max() < 25 and np.abs(ay[1:]).max() < 25:     # < 25 m per km
                cx, cy, model = ax, ay, "affine"
        resid = np.hypot(A[:, 2] - Xm @ cx, A[:, 3] - Xm @ cy)
        new = resid <= tol
        if (new == use).all() or new.sum() < 2:
            break
        use = new
    resid = np.hypot(A[:, 2] - Xm @ cx, A[:, 3] - Xm @ cy)
    out.update(aligned=True, model=model, xc=float(xc), yc=float(yc), cx=[float(v) for v in cx],
               cy=[float(v) for v in cy], n_used=int(use.sum()),
               rms_m=round(float(np.sqrt(np.mean(resid[use] ** 2))), 1),
               shift_m=round(float(np.hypot(cx[0], cy[0])), 1))
    return out


# --------------------------------------------------------------------------- per sheet
def block_stats(town, key, preview=False):
    """Render + align one sheet over a town, measure every block. Cached in data/interim."""
    import cv2
    import pandas as pd
    from rasterio import features
    sh = S[key]
    INT.mkdir(parents=True, exist_ok=True)
    cache = INT / f"stats_{town}_{key}.parquet"
    if cache.exists() and not preview:
        return pd.read_parquet(cache)
    grid = Grid(TOWNS[town]["bbox"])
    clip = town_clip(town)
    bl = blocks(town, clip)
    model = align_sheet(key)
    print(key, "align", {k: model.get(k) for k in ("aligned", "model", "n_windows", "n_used", "rms_m", "shift_m", "reason")})
    if sh["style"] == "tint" and model.get("aligned") and model.get("shift_m", 0) < 6:
        model = None                        # accurate 1:24,000 sheets: as published
    img, valid = render(sh, grid, model)
    ink = ink_mask(img, sh["style"])
    heavy, bands = heavy_and_bands(ink, grid.res, sh)
    tint = tint_mask(img) if sh["style"] == "tint" else np.zeros_like(ink)
    if sh["style"] == "tint":               # the tint is drawn under streets / lettering: close small gaps
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        tint = cv2.morphologyEx(tint.astype(np.uint8), cv2.MORPH_CLOSE, k).astype(bool)
    lab = features.rasterize(((g, i + 1) for i, g in enumerate(bl.geometry)), out_shape=(grid.H, grid.W),
                             transform=grid.transform, dtype="int32")
    n = len(bl) + 1
    cnt = lambda m: np.bincount(lab[m], minlength=n)      # noqa: E731
    px_all = np.bincount(lab.ravel(), minlength=n)
    px_valid = cnt(valid)
    a_band = cnt(bands & valid)
    a_heavy = cnt(heavy & valid)
    a_tint = cnt(tint & valid)
    # squares: compact heavy-ink components not part of a band
    sq = heavy & ~cv2.dilate(bands.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    nl, cl, st, cen = cv2.connectedComponentsWithStats(sq.astype(np.uint8), 8)
    mm = sh["scale"] / 1000.0
    amin = (0.25 * mm) ** 2 / grid.res ** 2           # >= 0.25 x 0.25 mm on paper
    ok = (st[1:, cv2.CC_STAT_AREA] >= amin)
    ci = np.clip(np.round(cen[1:, 0]).astype(int), 0, grid.W - 1)
    cj = np.clip(np.round(cen[1:, 1]).astype(int), 0, grid.H - 1)
    n_sq = np.bincount(lab[cj[ok], ci[ok]], minlength=n)
    # band thickness -> band length per block
    from skimage.morphology import skeletonize
    sk = skeletonize(bands)
    a_skel = cnt(sk & valid)
    df = pd.DataFrame({"bid": bl.bid.values, "px": px_all[1:], "px_valid": px_valid[1:], "a_band": a_band[1:],
                       "a_heavy": a_heavy[1:], "a_tint": a_tint[1:], "n_sq": n_sq[1:], "skel": a_skel[1:]})
    df["res"] = grid.res
    df.to_parquet(cache)
    if preview:
        pv = img.copy()
        pv[heavy & ~bands] = (0, 160, 255)
        pv[bands] = (255, 0, 0)
        if sh["style"] == "tint":
            pv[tint & ~heavy] = (255, 190, 120)
        cv2.imwrite(str(INT / f"pv_{town}_{key}.jpg"), pv[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 80])
    return df


# --------------------------------------------------------------------------- classify / build
THRESH = {"early": 0.35, "tint": 0.35}   # built frontage share (early) / share under the urban tint
TINT_SHARE = 0.30
SQ_FRONT_M = 15.0                         # frontage credited to one house square
HOLE_HA = 0.6                             # fill holes in the extent smaller than this
MIN_HA = 0.8                              # drop isolated built specks smaller than this


def snapshot_stats(town, year):
    """Per block: summed sheet stats of one snapshot + shares."""
    import pandas as pd
    import shapely
    keys = TOWNS[town]["snaps"][year]
    clip = town_clip(town)
    bl = blocks(town, clip)
    tot = None
    for k in keys:
        df = block_stats(town, k)
        if df is None:
            continue
        df = df.set_index("bid")[["px", "px_valid", "a_band", "a_heavy", "a_tint", "n_sq", "skel"]]
        if tot is None:
            tot = df.copy()
        else:
            tot[["px_valid", "a_band", "a_heavy", "a_tint", "n_sq", "skel"]] += df[["px_valid", "a_band", "a_heavy", "a_tint", "n_sq", "skel"]]
    res = RES
    tot = tot.reindex(bl.bid.values)
    g = bl.set_index("bid").geometry
    inner = shapely.buffer(g.values, -15.0)
    P = np.where(shapely.is_empty(inner), 0.5 * shapely.length(g.values), shapely.length(inner))
    tot["front_m"] = P
    tot["cov"] = tot.px_valid / tot.px.clip(lower=1)
    t_band = tot.a_band.sum() * res * res / max(1.0, tot.skel.sum() * res)
    tot["band_m"] = tot.a_band * res * res / t_band
    fr = (tot.front_m * tot["cov"]).clip(lower=1)
    tot["share"] = ((tot.band_m + SQ_FRONT_M * tot.n_sq) / fr).clip(upper=1.5)
    tot["tint_share"] = tot.a_tint / tot.px_valid.clip(lower=1)
    style = S[keys[0]]["style"]
    built = (tot["cov"] >= 0.5) & (tot.share >= THRESH[style])
    if style == "tint":
        built |= (tot["cov"] >= 0.5) & (tot.tint_share >= TINT_SHARE)
    tot["built"] = built
    tot.attrs["t_band"] = t_band
    return bl, tot


def extent_polys(bl, tot, clip):
    import shapely
    g = bl.set_index("bid").geometry
    u = shapely.union_all(list(g[tot.built.values].values)).buffer(0.5).buffer(-0.5)
    parts = []
    for p in shapely.get_parts(u):
        holes = [h for h in p.interiors if shapely.Polygon(h).area < HOLE_HA * 1e4]
        keep = [h for h in p.interiors if shapely.Polygon(h).area >= HOLE_HA * 1e4]
        p = shapely.Polygon(p.exterior, keep)
        if p.area >= MIN_HA * 1e4:
            parts.append(p)
    u = shapely.union_all(parts) if parts else shapely.Polygon()
    land = land_poly(clip.bounds)
    u = u.intersection(land.buffer(30)).intersection(clip)
    u = shapely.simplify(u, 1.0)
    return shapely.make_valid(u)


def coverage_poly(town, year, clip):
    import shapely
    t = tf("EPSG:4326", UTM)
    out = []
    for k in TOWNS[town]["snaps"][year]:
        w, s, e, n = S[k]["quad"]
        xs = np.r_[np.linspace(w, e, 20), np.full(20, e), np.linspace(e, w, 20), np.full(20, w)]
        ys = np.r_[np.full(20, s), np.linspace(s, n, 20), np.full(20, n), np.linspace(n, s, 20)]
        x, y = t.transform(xs, ys)
        out.append(shapely.Polygon(np.column_stack([x, y])))
    return shapely.union_all(out).intersection(clip)


def to_ll(g):
    import shapely
    t = tf(UTM, "EPSG:4326")
    return shapely.transform(g, lambda c: np.column_stack(t.transform(c[:, 0], c[:, 1])))


def build(town, years=None, meta=None):
    import shapely
    from shapely.geometry import mapping
    clip = town_clip(town)
    OUT.mkdir(parents=True, exist_ok=True)
    meta = meta or {}
    for year in (years or TOWNS[town]["snaps"]):
        bl, tot = snapshot_stats(town, year)
        u = extent_polys(bl, tot, clip)
        cov = coverage_poly(town, year, clip)
        keys = TOWNS[town]["snaps"][year]
        info = TOWNS[town].get("notes", {}).get(year, {})
        props = {"town": town, "year": int(year),
                 "source": "+".join(f"usgs_htmc:{k}" for k in keys),
                 "source_url": " ".join(f"{PDF}{S[k]['scale']}/{S[k]['file'].replace('_geo.tif', '_geo.pdf')}" for k in keys),
                 "confidence": info.get("confidence", "medium"),
                 "note": info.get("note", "; ".join(f"{k}: {S[k]['note']}" for k in keys)),
                 "edition_years": sorted({S[k]["edition"] for k in keys}),
                 "map_years": sorted({S[k]["year"] for k in keys}),
                 "method": f"blocks with built frontage share >= {THRESH[S[keys[0]]['style']]}"
                           + (f" or urban tint share >= {TINT_SHARE}" if S[keys[0]]["style"] == "tint" else ""),
                 "area_km2": round(u.area / 1e6, 3), "n_blocks": int(tot.built.sum())}
        fc = {"type": "FeatureCollection",
              "features": [{"type": "Feature", "properties": props, "geometry": mapping(to_ll(u))}]}
        p = OUT / f"{town}_{year}.geojson"
        p.write_text(json.dumps(fc, separators=(",", ":")))
        # per-block table (interim, for checks)
        t = tot.copy()
        t.to_parquet(INT / f"class_{town}_{year}.parquet")
        cv = {"town": town, "year": int(year), "sheets": keys, "area_km2": round(cov.area / 1e6, 3)}
        (INT / f"coverage_{town}_{year}.json").write_text(json.dumps({"props": cv, "geom": mapping(to_ll(cov))}))
        print(town, year, "built blocks", int(tot.built.sum()), "of", int((tot["cov"] >= 0.5).sum()),
              "read; extent", props["area_km2"], "km2; t_band", round(tot.attrs["t_band"], 1), "m")


# --------------------------------------------------------------------------- checks
SANBORN = {"oakland": ["oakland_west", "oakland_downtown"],
           "berkeley": ["berkeley_downtown", "berkeley_northside", "berkeley_southside", "berkeley_west"],
           "alameda": ["alameda_westend"], "san_jose": ["san_jose_downtown"],
           "palo_alto": ["palo_alto_downtown", "palo_alto_mayfield"], "san_mateo": ["san_mateo_downtown"],
           "richmond": ["richmond_downtown"]}
SAN_BUILT, SAN_EMPTY = 0.15, 0.05     # Sanborn footprint share of a block: built / empty


def load_extent(town, year):
    import shapely
    from shapely.geometry import shape
    p = OUT / f"{town}_{year}.geojson"
    fc = json.loads(p.read_text())
    return to_utm(shapely.union_all([shape(f["geometry"]) for f in fc["features"]]))


def load_coverage(town, year):
    from shapely.geometry import shape
    return to_utm(shape(json.loads((INT / f"coverage_{town}_{year}.json").read_text())["geom"]))


def survivors(town, clip):
    import pandas as pd
    import shapely
    w, s, e, n = TOWNS[town]["bbox"]
    d = pd.read_parquet(ROOT / "data" / "interim" / "region_building_points.parquet")
    d = d[(d.lon > w) & (d.lon < e) & (d.lat > s) & (d.lat < n) & (d.end_year > 9000) & (d.area_m2 >= 30)]
    x, y = tf("EPSG:4326", UTM).transform(d.lon.values, d.lat.values)
    pts = shapely.points(x, y)
    inside = shapely.contains(clip, pts) if hasattr(shapely, "contains") else np.array([clip.contains(p) for p in pts])
    d = d[inside].copy()
    d["x"], d["y"] = np.asarray(x)[inside], np.asarray(y)[inside]
    return d


def sanborn_blocks(town, bl):
    """Per Sanborn area and map year: blocks fully inside the traced coverage with their footprint share."""
    import geopandas as gpd
    import shapely
    out = []
    for area in SANBORN.get(town, []):
        cp = ROOT / "data" / "manual" / "sanborn" / f"{area}_coverage.geojson"
        if not cp.exists():
            continue
        cov = gpd.read_file(cp).to_crs(UTM)
        for _, c in cov.iterrows():
            yr = int(c.map_year)
            fp = ROOT / "data" / "manual" / "sanborn" / f"{area}_{yr}.geojson"
            if not fp.exists():
                continue
            f = gpd.read_file(fp).to_crs(UTM)
            fu = shapely.union_all(list(f.geometry.buffer(0)))
            for bid, g in zip(bl.bid, bl.geometry):
                if not g.intersects(c.geometry):
                    continue
                if g.intersection(c.geometry).area < 0.9 * g.area or g.area > 6e4:
                    continue
                share = g.intersection(fu).area / g.area
                out.append((area, yr, bid, share))
    import pandas as pd
    return pd.DataFrame(out, columns=["area", "year", "bid", "share"])


def check(town):
    import shapely
    clip = town_clip(town)
    bl = blocks(town, clip)
    pts = survivors(town, clip)
    P = shapely.points(pts.x.values, pts.y.values)
    sb = sanborn_blocks(town, bl)
    gb = bl.set_index("bid").geometry
    rep = {"town": town, "snapshots": []}
    years = sorted(TOWNS[town]["snaps"])
    for year in years:
        ext = load_extent(town, year)
        cov = load_coverage(town, year)
        r = {"year": year, "area_km2": round(ext.area / 1e6, 2), "coverage_km2": round(cov.area / 1e6, 2)}
        inc = shapely.contains(cov, P)
        ine = shapely.contains(ext.buffer(20), P)
        for lab, lo, hi in (("pre", 1800, year - 1), ("decade_before", year - 10, year - 1)):
            m = inc & (pts.start_year.values >= lo) & (pts.start_year.values < hi)
            r[f"survivors_{lab}"] = int(m.sum())
            r[f"survivors_{lab}_inside_pct"] = round(100 * float((m & ine).sum()) / max(1, m.sum()), 1)
        # precision proxy: extent blocks (read) holding a building standing today that predates the map
        cls = __import__("pandas").read_parquet(INT / f"class_{town}_{year}.parquet")
        built_b = cls.index[cls.built.values]
        old = pts[(pts.start_year < year) & (pts.start_year > 1800)]
        bt = shapely.STRtree(list(gb.loc[built_b].values))
        hit = np.zeros(len(built_b), bool)
        if len(old):
            idx = bt.query(shapely.points(old.x.values, old.y.values), predicate="within")
            hit[np.unique(idx[1])] = True
        r["extent_blocks"] = int(len(built_b))
        r["extent_blocks_with_survivor_pct"] = round(100 * float(hit.mean()) if len(hit) else 0, 1)
        # Sanborn
        sr = []
        for (area, yr), grp in sb.groupby(["area", "year"]):
            if abs(yr - year) > 6:
                continue
            ok = grp.bid.isin(cls.index[cls["cov"] >= 0.5])
            grp = grp[ok]
            b = grp[grp.share >= SAN_BUILT]
            e = grp[grp.share < SAN_EMPTY]
            sr.append({"area": area, "sanborn_year": int(yr), "blocks": int(len(grp)),
                       "built_blocks": int(len(b)), "built_in_extent_pct": round(100 * float(cls.loc[b.bid, "built"].mean()) if len(b) else float("nan"), 1),
                       "empty_blocks": int(len(e)), "empty_in_extent_pct": round(100 * float(cls.loc[e.bid, "built"].mean()) if len(e) else float("nan"), 1)})
        r["sanborn"] = sr
        rep["snapshots"].append(r)
        print(json.dumps(r))
    (INT / f"check_{town}.json").write_text(json.dumps(rep, indent=1))
    plot(town, bl, pts, years)
    return rep


def plot(town, bl, pts, years):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PatchCollection
    import shapely
    clip = town_clip(town)
    n = len(years)
    fig, axs = plt.subplots(1, n, figsize=(5.2 * n, 5.6), dpi=110)
    axs = np.atleast_1d(axs)
    xmin, ymin, xmax, ymax = clip.bounds
    cols = ["#7a1f1f", "#b4472a", "#d98a3d", "#e8bf5a", "#9cb86b", "#5f9ea0"]

    def draw(ax, g, **kw):
        for p in shapely.get_parts(g):
            if p.is_empty:
                continue
            x, y = p.exterior.xy
            ax.fill(x, y, **kw)
            for h in p.interiors:
                hx, hy = h.xy
                ax.fill(hx, hy, color="white", lw=0)
    prev = []
    for k, (ax, year) in enumerate(zip(axs, years)):
        bnd = shapely.union_all(list(bl.geometry.values))
        for p in shapely.get_parts(clip):
            x, y = p.exterior.xy
            ax.plot(x, y, color="#888", lw=0.5)
        for pe, (py_, pc) in enumerate(prev):
            draw(ax, py_, color=pc, lw=0, alpha=0.9)
        ext = load_extent(town, year)
        cov = load_coverage(town, year)
        new = ext.difference(shapely.union_all([p for p, _ in prev])) if prev else ext
        draw(ax, new, color=cols[k % len(cols)], lw=0, alpha=0.9)
        for p in shapely.get_parts(cov):
            x, y = p.exterior.xy
            ax.plot(x, y, color="#2b6cb0", lw=1.0, ls="--")
        old = pts[(pts.start_year < year) & (pts.start_year > 1800)]
        ax.scatter(old.x, old.y, s=0.4, c="k", lw=0)
        prev.append((ext, cols[k % len(cols)]))
        ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_aspect("equal")
        ax.set_xticks([]); ax.set_yticks([])
        keys = TOWNS[town]["snaps"][year]
        ax.set_title(f"{year}  ({ext.area / 1e6:.1f} km²)\n" + ", ".join(k for k in keys), fontsize=8)
    fig.suptitle(f"{TOWNS[town]['name']}: built-up extent by USGS topo snapshot (new area in colour, "
                 f"earlier snapshots underneath; dashed = area read; dots = buildings standing today built before the map)",
                 fontsize=8)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "check" / f"{town}.png" if (OUT / "check").exists() else INT / f"check_{town}.png")
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("town")
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--preview", action="store_true")
    o = ap.parse_args()
    if o.cmd == "sheet":
        print(block_stats(o.town, o.rest[0], o.preview).describe().T)
    elif o.cmd == "build":
        build(o.town, [int(y) for y in o.rest] or None)
    elif o.cmd == "check":
        check(o.town)
    elif o.cmd == "all":
        for y, keys in TOWNS[o.town]["snaps"].items():
            for k in keys:
                block_stats(o.town, k)
        build(o.town)
        check(o.town)
