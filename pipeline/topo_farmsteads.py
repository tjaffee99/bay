"""Farmsteads from USGS historical topographic maps (Phase 6 groundwork).

Rural houses and barns are printed on the USGS topographic quadrangles as small solid
black squares (about 0.4-0.8 mm on paper). This stage finds those symbols on the
scanned historical maps of the farming districts of the five modelled counties and
writes where farmsteads really stood:

  data/manual/farmsteads/topo_farmsteads.geojson   one point per farmstead (house +
                                                   outbuildings within ~60 m)
  data/manual/farmsteads/coverage.geojson          neat line of every processed sheet
  data/interim/topo/maps/<id>.json                 per-sheet detections (cache)
  data/interim/topo/debug/                         overlay crops for checking

Maps: USGS Historical Topographic Map Collection (HTMC, public domain), found with the
TNM API and read from the GeoPDFs (the PDFs carry the 600-700 ppi scan, the GeoTIFFs a
300 ppi resample) with their own registration (LGIDict CTM, neat line, projection).
Two editions per quadrangle where they exist: the earliest 1:62,500 15' sheet
(c. 1889-1920) and a pre-boom edition c. 1939-1955 (1:24,000 preferred).

Detection (per sheet, in paper millimetres so it works for any scan resolution):
  black ink (darkest channel below a threshold; contours are brown, water blue)
  -> morphological opening with a disc of ~0.26 mm: lines (roads, rails, boundaries,
     thin text) vanish, solid squares survive
  -> candidates by area (valley of the sheet's own blob-area histogram), compactness,
     solidity and darkness
  -> rejections: dots of dash-dot boundary lines (collinear with long dashes), pieces
     of lettering (blob is a small part of a compact letter-shaped ink component, or
     sits in a row of letter-sized components), map collar
  -> towns: symbols with > 8 others within 150 m are dropped (rural farmsteads only)
  -> farmsteads: symbols within ~60 m are one farmstead; the largest is the house.

Usage:  python topo_farmsteads.py [all|query|process|export|debug] [--area NAME] [--keep]
Raw downloads (data/raw/topo/) are deleted after a sheet is processed unless --keep;
the per-sheet JSON in data/interim/topo/maps/ keeps everything the export needs.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))   # also when run with python -I
from common import INTERIM, MANUAL, RAW, download_file, get_with_retry, log, session  # noqa: E402

TOPO_RAW = RAW / "topo"
API_CACHE = TOPO_RAW / "api"
META_CACHE = TOPO_RAW / "meta"
PROJ_DIR = RAW / "proj"
TOPO_INTERIM = INTERIM / "topo"
MAP_CACHE = TOPO_INTERIM / "maps"
INK_CACHE = TOPO_INTERIM / "ink"          # low-resolution black-ink image per sheet (for alignment)
ROADS = RAW / "overture" / "2026-10-21.0" / "roads_region.parquet"   # download_overture.py
DEBUG_DIR = TOPO_INTERIM / "debug"
OUT_DIR = MANUAL / "farmsteads"

TNM_API = "https://tnmaccess.nationalmap.gov/api/v1/products"
LINE_BAND = 0.10        # mm: a line passing this close to a blob's centre runs through it
DETECTOR_VERSION = 7
EARLY_COMPATIBLE = set()   # versions whose early-sheet results are still valid

# Farming districts of the five modelled counties (W, S, E, N in degrees). Quads are
# selected when their footprint overlaps one of these boxes.
AREAS = {
    "santa_clara_valley": (-122.15, 37.10, -121.70, 37.47),   # Palo Alto / Milpitas .. Coyote
    "south_valley": (-121.75, 36.98, -121.45, 37.20),         # Morgan Hill .. Gilroy
    "peninsula_coast": (-122.52, 37.30, -122.30, 37.55),      # Half Moon Bay, Pescadero side
    "peninsula_baylands": (-122.30, 37.40, -122.05, 37.55),   # Redwood City .. Mountain View
    "tri_valley": (-122.00, 37.55, -121.55, 37.80),           # Livermore, Pleasanton, Sunol, Dublin
    "east_bay_plain": (-122.20, 37.45, -121.90, 37.70),       # Hayward, Alvarado, Niles, Newark, Irvington
    "contra_costa": (-122.15, 37.85, -121.55, 38.05),         # Walnut Creek, Concord, Antioch, Brentwood, Byron
    "north_bay": (-122.75, 38.00, -122.45, 38.30),            # Novato, Petaluma
}
DEFAULT_AREAS = ["santa_clara_valley"]

EARLY = (1886, 1922)   # first-generation 15' sheets
LATE = (1939, 1956)    # just before the post-war suburban boom


# ----------------------------------------------------------------------------- TNM API
def query_tnm(bbox) -> list[dict]:
    """All Historical Topographic Map items intersecting bbox (cached JSON)."""
    API_CACHE.mkdir(parents=True, exist_ok=True)
    key = "_".join(f"{v:.3f}" for v in bbox)
    path = API_CACHE / f"htmc_{key}.json"
    if not path.exists():
        s = session()
        items, offset = [], 0
        while True:
            r = get_with_retry(s, TNM_API, params={
                "datasets": "Historical Topographic Maps",
                "bbox": ",".join(str(v) for v in bbox),
                "max": 200, "offset": offset, "outputFormat": "JSON"})
            d = r.json()
            items += d.get("items", [])
            offset += 200
            if offset >= d.get("total", 0) or not d.get("items"):
                break
        path.write_text(json.dumps(items))
    return json.loads(path.read_text())


TITLE_RE = re.compile(r"USGS 1:(\d+)-scale Quadrangle for (.+?), CA (\d{4})")


def parse_item(it: dict) -> dict | None:
    m = TITLE_RE.match(it.get("title", ""))
    if not m:
        return None
    scale, quad, year = int(m.group(1)), m.group(2), int(m.group(3))
    pdf = (it.get("urls") or {}).get("GeoPDF") or it.get("downloadURL")
    if not pdf or not pdf.endswith(".pdf"):
        return None
    sid = re.search(r"_(\d+)_\d{4}_\d+_geo\.pdf$", pdf)
    return {
        "id": sid.group(1) if sid else it.get("sourceId"),
        "quad": quad, "scale": scale, "edition_year": year,
        "bbox": [it["boundingBox"][k] for k in ("minX", "minY", "maxX", "maxY")],
        "pdf_url": pdf, "meta_url": it.get("vendorMetaUrl"),
        "size": it.get("sizeInBytes") or 0, "created": it.get("dateCreated", ""),
    }


def fetch_meta(m: dict) -> dict:
    """Survey year, date on map, scan quality and woodland tint from the FGDC record."""
    META_CACHE.mkdir(parents=True, exist_ok=True)
    path = META_CACHE / f"{m['id']}.xml"
    if not path.exists() and m.get("meta_url"):
        try:
            r = get_with_retry(session(), m["meta_url"], tries=3)
            path.write_bytes(r.content)
        except RuntimeError:
            return {}
    if not path.exists():
        return {}
    out = {}
    root = ET.fromstring(path.read_bytes())
    steps = root.findall(".//procstep")
    for st in steps:
        desc = (st.findtext("procdesc") or "").strip().lower()
        date = (st.findtext("procdate") or "").strip()
        if desc in ("survey year", "date on map", "edit year", "photo year", "print year", "imprint year",
                    "photo inspection year", "field check year", "aerial photo year", "photo revision year"):
            if re.fullmatch(r"\d{4}", date):
                out[desc.replace(" ", "_")] = int(date)
    sup = root.findtext(".//supplinf") or ""
    q = re.search(r"Scan Quality:\s*([^;]+)", sup)
    w = re.search(r"Woodland Tint:\s*([YN])", sup)
    out["scan_quality"] = q.group(1).strip() if q else None
    out["woodland_tint"] = (w.group(1) == "Y") if w else None
    return out


def _overlap(b1, b2):
    w = max(0.0, min(b1[2], b2[2]) - max(b1[0], b2[0]))
    h = max(0.0, min(b1[3], b2[3]) - max(b1[1], b2[1]))
    return w * h


def select_maps(area_names) -> list[dict]:
    """Sheets to process for the given farming districts:
      early: every distinct survey of the first-generation 1:62,500 / 1:48,000 sheets
             (EARLY years; reprints of the same survey are skipped);
      late:  the first edition in LATE, 1:24,000 preferred; a 15' sheet only where the
             7.5' sheets of the period do not already cover it; reprints of surveys
             before 1930 are skipped (they show the old state).
    A quadrangle is used when at least 30 % of it lies in one of the districts. Of
    duplicate scans of one edition the better scan quality / larger file wins."""
    cand = {}
    for name in area_names:
        box = AREAS[name]
        for it in query_tnm(box):
            m = parse_item(it)
            if not m or m["scale"] not in (24000, 62500, 48000, 31680):
                continue
            bb = m["bbox"]
            if _overlap(bb, box) < 0.3 * (bb[2] - bb[0]) * (bb[3] - bb[1]):
                continue
            cand[m["id"]] = m
    by_cell = {}
    for m in cand.values():
        by_cell.setdefault((m["scale"], tuple(round(v, 3) for v in m["bbox"])), []).append(m)

    def best(group):
        """The original printing: photorevised reprints (purple overprints of a later
        state) are skipped, then the earliest imprint, better scan, larger file."""
        for m in group:
            m["meta"] = fetch_meta(m)
        orig = [m for m in group if not m["meta"].get("photo_revision_year") and not m["meta"].get("edit_year")]
        group = orig or group
        bad = lambda m: (m["meta"].get("scan_quality") or "").lower().startswith("not")
        return sorted(group, key=lambda m: (m["meta"].get("imprint_year") or m["edition_year"], bad(m), -m["size"]))[0]

    chosen, late = [], []
    # early: one sheet per survey of each 15' cell (a 1:48,000 and a 1:62,500 printing of
    # the same survey are the same map; the larger scale wins)
    early_by_cell = {}
    for (scale, bbox), ms in by_cell.items():
        if scale in (62500, 48000):
            early_by_cell.setdefault(bbox, []).extend(m for m in ms if EARLY[0] <= m["edition_year"] <= EARLY[1])
    for bbox, early in sorted(early_by_cell.items()):
        for m in early:
            m["meta"] = fetch_meta(m)
        known = {m["edition_year"] for m in early if m["meta"].get("survey_year")}
        surveys = {}
        for m in early:
            sy = m["meta"].get("survey_year")
            if sy is None and m["edition_year"] in known:
                continue                          # same edition, survey year not recorded
            surveys.setdefault(sy or m["edition_year"], []).append(m)
        for sy, group in sorted(surveys.items()):
            # the regular 1:62,500 sheet over a special 1:48,000 printing of the same survey
            top = 62500 if any(m["scale"] == 62500 for m in group) else min(m["scale"] for m in group)
            mm = best([m for m in group if m["scale"] == top])
            mm["edition"] = "early"
            chosen.append(mm)
    for (scale, bbox), ms in sorted(by_cell.items()):
        lt = []
        for m in ms:
            if LATE[0] <= m["edition_year"] <= LATE[1]:
                m["meta"] = fetch_meta(m)
                sy = m["meta"].get("survey_year")
                if sy and sy < 1930:
                    continue                      # a reprint of an old survey
                if m["meta"].get("photo_revision_year") or m["meta"].get("edit_year"):
                    continue                      # photorevised later state
                lt.append(m)
        if lt:
            y0 = min(m["edition_year"] for m in lt)
            mm = best([m for m in lt if m["edition_year"] == y0])
            mm["edition"] = "late"
            late.append(mm)
    l24 = [m for m in late if m["scale"] == 24000]
    for m in late:
        if m["scale"] != 24000:
            bb = m["bbox"]
            cov = sum(_overlap(bb, q["bbox"]) for q in l24) / ((bb[2] - bb[0]) * (bb[3] - bb[1]))
            if cov >= 0.9:
                continue
            m["covered_by_24k"] = round(cov, 2)
        chosen.append(m)
    return chosen


# ----------------------------------------------------------------------------- GeoPDF
def _num_list(obj: str, key: str):
    m = re.search(r"/" + key + r"\s*\[(.*?)\]", obj, re.S)
    return [float(v) for v in re.findall(r"\(([-0-9.eE+]+)\)", m.group(1))] if m else None


class GeoPDF:
    """A scanned USGS GeoPDF: the full-resolution scan, read region by region from the
    PDF's 1024 px JPEG tiles (a 1:24,000 sheet is ~18k x 15k px, so it is never held
    whole), and its registration: pixel (col, row) -> projected metres, neat line in
    pixels, projection."""

    def __init__(self, pdf_path: Path):
        import pymupdf
        self.doc = pymupdf.open(pdf_path)
        page = self.doc[0]
        obj = self.doc.xref_object(page.xref)
        ctm = _num_list(obj, "CTM")
        neat = _num_list(obj, "Neatline")
        proj = {}
        pm = re.search(r"/Projection\s*<<(.*?)>>", obj, re.S)
        if pm:
            for k, v in re.findall(r"/(\w+)\s*\(([^)]*)\)", pm.group(1)):
                proj[k] = v
        if not ctm or not neat:
            raise ValueError(f"{pdf_path.name}: no LGIDict registration")
        info = [i for i in page.get_image_info(xrefs=True) if i["xref"] > 0]
        big = max(info, key=lambda i: i["width"])
        s = big["width"] / (big["bbox"][2] - big["bbox"][0])        # pixels per PDF point
        self.W = int(round(page.rect.width * s))
        self.H = int(round(page.rect.height * s))
        self.tiles = []
        for i in info:
            x0 = int(round(i["bbox"][0] * s)); y0 = int(round(i["bbox"][1] * s))
            self.tiles.append((x0, y0, x0 + i["width"], y0 + i["height"], i["xref"]))
        self._cache = {}
        page_h = page.rect.height
        a, b, c, d, e, f = ctm

        def px_to_proj(col, row):
            x = np.asarray(col, float) / s
            y = page_h - np.asarray(row, float) / s           # PDF user space is bottom-up
            return a * x + c * y + e, b * x + d * y + f

        nl = np.array(neat).reshape(-1, 2)
        self.g = {"px_to_proj": px_to_proj, "georef": {"ctm": list(ctm), "s": s, "page_h": page_h}, "neat_px": np.column_stack([nl[:, 0] * s, (page_h - nl[:, 1]) * s]),
                  "proj": proj, "px_per_mm": s * 72 / 25.4, "m_per_px": abs(a) / s, "W": self.W, "H": self.H}

    def _tile(self, xref):
        import pymupdf
        if xref not in self._cache:
            if len(self._cache) > 48:
                self._cache.clear()
            pix = pymupdf.Pixmap(self.doc, xref)
            if pix.n - pix.alpha < 3:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            self._cache[xref] = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].copy()
        return self._cache[xref]

    def read(self, y0, y1, x0, x1, step=1):
        """RGB region [y0:y1, x0:x1] (clipped to the page; white outside), every step-th px."""
        out = np.full(((y1 - y0 + step - 1) // step, (x1 - x0 + step - 1) // step, 3), 255, np.uint8)
        for tx0, ty0, tx1, ty1, xref in self.tiles:
            ix0, iy0, ix1, iy1 = max(x0, tx0), max(y0, ty0), min(x1, tx1), min(y1, ty1)
            if ix0 >= ix1 or iy0 >= iy1:
                continue
            # first sampled pixel at or after the intersection start
            sx = ix0 + (-(ix0 - x0)) % step
            sy = iy0 + (-(iy0 - y0)) % step
            if sx >= ix1 or sy >= iy1:
                continue
            t = self._tile(xref)
            blk = t[sy - ty0:iy1 - ty0:step, sx - tx0:ix1 - tx0:step]
            oy, ox = (sy - y0) // step, (sx - x0) // step
            out[oy:oy + blk.shape[0], ox:ox + blk.shape[1]] = blk
        return out


def read_geopdf(pdf_path: Path):
    """Whole scan in memory (debugging only) + registration."""
    r = GeoPDF(pdf_path)
    return r.read(0, r.H, 0, r.W), r.g


def crs_for(proj: dict, bbox=None):
    """pyproj CRS of a GeoPDF's projected coordinates (NAD27 maps). The LGIDict gives the
    central meridian rounded to 3 decimals, and the registration was computed with that
    rounded value (the neat line inverts exactly onto the quadrangle corners with it), so
    it is used as is; process_sheet checks the corners against the TNM footprint."""
    import pyproj
    t = proj.get("ProjectionType", "")
    datum = proj.get("Datum", "NAS-C")
    ell = "+datum=NAD27" if datum.startswith("NAS") else "+datum=NAD83" if datum.startswith("NAR") else "+datum=WGS84"
    lon0 = float(proj.get("CentralMeridian", 0) or 0)
    lat0 = float(proj.get("OriginLatitude", 0) or 0)
    fe = float(proj.get("FalseEasting", 0) or 0)
    fn = float(proj.get("FalseNorthing", 0) or 0)
    if t == "PH":       # polyconic
        return pyproj.CRS.from_proj4(f"+proj=poly +lat_0={lat0} +lon_0={lon0} +x_0={fe} +y_0={fn} {ell} +units=m +no_defs")
    if t in ("TC", "TM"):   # transverse mercator
        k = float(proj.get("ScaleFactor", 0.9996) or 0.9996)
        return pyproj.CRS.from_proj4(f"+proj=tmerc +lat_0={lat0} +lon_0={lon0} +k={k} +x_0={fe} +y_0={fn} {ell} +units=m +no_defs")
    if t == "UT":       # UTM
        zone = int(proj.get("Zone", 10))
        return pyproj.CRS.from_proj4(f"+proj=utm +zone={zone} {ell} +units=m +no_defs")
    if t == "LE":       # Lambert conformal conic (state plane)
        return pyproj.CRS.from_proj4(
            f"+proj=lcc +lat_1={proj.get('StandardParallelOne')} +lat_2={proj.get('StandardParallelTwo')} "
            f"+lat_0={lat0} +lon_0={lon0} +x_0={fe} +y_0={fn} {ell} +units=m +no_defs")
    raise ValueError(f"unsupported projection {proj}")


_TO_WGS = {}


def to_wgs84(crs, x, y):
    """Projected NAD27 metres -> WGS84 lon/lat, through the NADCON grid when available."""
    import pyproj
    key = crs.to_wkt()
    if key not in _TO_WGS:
        PROJ_DIR.mkdir(parents=True, exist_ok=True)
        grid = PROJ_DIR / "us_noaa_conus.tif"
        try:
            download_file("https://cdn.proj.org/us_noaa_conus.tif", grid)   # NADCON, open licence
        except RuntimeError:
            pass
        pyproj.datadir.append_data_dir(str(PROJ_DIR))
        geo = crs.geodetic_crs
        inv = pyproj.Transformer.from_crs(crs, geo, always_xy=True)
        from pyproj.transformer import TransformerGroup
        tg = TransformerGroup(geo, "EPSG:4326", always_xy=True,
                              area_of_interest=pyproj.aoi.AreaOfInterest(-123.5, 36.5, -121.0, 38.8))
        _TO_WGS[key] = (inv, tg.transformers[0])
    inv, dat = _TO_WGS[key]
    lon, lat = inv.transform(x, y)
    return dat.transform(lon, lat)


# ----------------------------------------------------------------------------- detection
def _valley_threshold(areas_mm2, lo=0.05, hi=0.16, default=0.09):
    """Blob-area threshold between the small-dot mode (boundary dots, junction knots)
    and the building-symbol mode, from the sheet's own histogram (log bins)."""
    a = areas_mm2[(areas_mm2 > 0.02) & (areas_mm2 < 0.6)]
    if len(a) < 200:
        return default
    bins = np.exp(np.linspace(np.log(0.02), np.log(0.6), 41))
    h, e = np.histogram(a, bins=bins)
    h = np.convolve(h, [1, 2, 1], "same") / 4
    c = np.sqrt(e[:-1] * e[1:])
    seg = (c >= lo) & (c <= hi)
    if not seg.any():
        return default
    i = np.argmin(np.where(seg, h, np.inf))
    return float(c[i])


def urban_tint(sm, inside_sm, ppm):
    """Red urban-area tint of the 1940s-50s maps (a pink background with red dots; only
    landmark buildings are drawn inside it). Contours are orange-brown and thin, red
    highways narrow, so a pink majority over ~2 mm marks the tint. Works on the sheet at
    1/4 resolution -> (mask at 1/4 resolution, outer rings in full-res pixels) or None."""
    import cv2
    sm = sm.astype(np.int16)
    R, G, B = sm[:, :, 0], sm[:, :, 1], sm[:, :, 2]
    pink = ((R - G > 22) & (G - B < 18) & (R > 190) & (inside_sm > 0)).astype(np.float32)
    del sm, R, G, B
    k = max(3, int(round(2.0 * ppm / 4)) | 1)
    m = (cv2.blur(pink, (k, k)) > 0.35).astype(np.uint8)
    kk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    m = cv2.morphologyEx(cv2.morphologyEx(m, cv2.MORPH_OPEN, kk), cv2.MORPH_CLOSE, kk)
    if m.sum() < (3 * ppm / 4) ** 2:
        return None
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rings = [(c[:, 0, :] * 4 + 2).tolist() for c in cnts if cv2.contourArea(c) >= (4 * ppm / 4) ** 2]
    return m.astype(bool), rings


def _colour_tests(blk):
    """(darkest-channel max, black-ink hue ok, blue water, min channel) of an RGB block."""
    b = blk.astype(np.int16)
    R, G, B = b[:, :, 0], b[:, :, 1], b[:, :, 2]
    mx = b.max(2)
    hue = (R - G < 40) & (B - R < 15) & (G - R < 15)       # not red-brown, not blue-green
    water = (B - R > 20) & (B > G - 10)
    return mx, hue, water, b.min(2)


def _inside_tile(neat_px, y0, y1, x0, x1, ppm):
    """Inside the neat line minus 1 mm (the neat line itself and its ticks), for a tile."""
    import cv2
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillPoly(m, [np.round(neat_px - [x0, y0]).astype(np.int32)], 1)
    return cv2.erode(m, cv2.getStructuringElement(cv2.MORPH_RECT, (int(ppm * 2) | 1,) * 2))


def _ink_core(img, inside, ink_t, ppm):
    import cv2
    mx_, hue_ = _colour_tests(img)[:2]
    ink = ((mx_ < ink_t) & hue_ & (inside > 0)).astype(np.uint8)
    d_open = max(3, int(round(0.26 * ppm)) | 1)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d_open, d_open))
    return ink, cv2.morphologyEx(ink, cv2.MORPH_OPEN, k), k


def _detect_tile(img, inside, ppm, paper, ink_t, a_min, core_box):
    """Candidates (solid blobs and open squares) of one tile with all their features.
    Only candidates whose centre lies in core_box (y0, y1, x0, x1 in tile pixels) are
    returned; the margin around it gives every window its full context."""
    import cv2
    from scipy.spatial import cKDTree
    H, W, _ = img.shape
    ink, core, k = _ink_core(img, inside, ink_t, ppm)
    n, lab, st, cen = cv2.connectedComponentsWithStats(core, connectivity=8)
    area_mm2 = st[:, 4] / ppm ** 2
    a_max = 0.80
    # --- per core blob: shape
    recs, dashes = [], []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if area_mm2[i] < 0.6 * a_min:
            continue
        sub = (lab[y:y + h, x:x + w] == i).astype(np.uint8)
        mom = cv2.moments(sub, binaryImage=True)
        mu20, mu02, mu11 = mom["mu20"] / a, mom["mu02"] / a, mom["mu11"] / a
        tr, det = mu20 + mu02, mu20 * mu02 - mu11 ** 2
        disc = math.sqrt(max(tr * tr / 4 - det, 0))
        l1, l2 = tr / 2 + disc, max(tr / 2 - disc, 1e-6)
        elong = math.sqrt(l1 / l2)
        theta = 0.5 * math.atan2(2 * mu11, mu20 - mu02)
        cx, cy = x + mom["m10"] / a, y + mom["m01"] / a
        length = 4 * math.sqrt(l1)
        if elong > 3.5 and length > 1.0 * ppm:
            dashes.append((cx, cy, math.cos(theta), math.sin(theta), length / 2))
            continue
        if area_mm2[i] > a_max:
            continue
        cnts, _ = cv2.findContours(sub, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cnts, key=cv2.contourArea)
        hull = np.zeros((h + 2, w + 2), np.uint8)
        cv2.fillConvexPoly(hull, cv2.convexHull(c) + 1, 1)
        solidity = a / max(hull.sum(), 1)
        (rw, rh) = cv2.minAreaRect(c)[1]
        rect_fill = a / max((rw + 1) * (rh + 1), 1)
        tri_area, _ = cv2.minEnclosingTriangle(c.astype(np.float32))
        tri_fill = cv2.contourArea(c) / max(tri_area, 1)
        dark = float(np.median(img[y:y + h, x:x + w].min(2)[sub > 0]))
        recs.append({"i": i, "x": cx, "y": cy, "area_mm2": float(area_mm2[i]), "elong": elong,
                     "solidity": float(solidity), "rect_fill": float(rect_fill), "tri_fill": float(tri_fill), "dark": dark,
                     "w": int(w), "h": int(h), "theta": theta})
    sym_ok = np.zeros(n, bool)
    for r in recs:
        r["shape_ok"] = (r["area_mm2"] >= a_min and r["elong"] <= 2.6 and r["solidity"] >= 0.82
                         and r["rect_fill"] >= 0.62)
        sym_ok[r["i"]] = r["shape_ok"]
    # --- open squares (barns, sheds, warehouses on the 1940s-50s maps; dwellings are
    # solid): small holes in the ink enclosed by a closed, thin square outline
    inkc = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))   # bridge 1 px breaks
    inv = ((inkc == 0) & (inside > 0)).astype(np.uint8)
    no, olab, ost, ocen = cv2.connectedComponentsWithStats(inv, connectivity=4)
    del inv
    ring_t = max(2, int(round(0.16 * ppm)))
    k_ring = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * ring_t + 1,) * 2)
    k_in = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    k_out = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * int(round(0.45 * ppm)) + 1,) * 2)
    sqfill = np.zeros((H, W), np.uint8)       # accepted open squares, filled
    opens = []
    # all small holes: a letter like B, 8, g has two counters side by side
    hsel = np.nonzero((ost[:, 4] >= 0.015 * ppm ** 2) & (ost[:, 4] <= 2.0 * ppm ** 2))[0]
    hsel = hsel[hsel > 0]
    htree = cKDTree(ocen[hsel]) if len(hsel) else None
    for i in range(1, no):
        x, y, w, h, a = ost[i]
        if not (0.07 * ppm ** 2 <= a <= 2.0 * ppm ** 2) or max(w, h) > 2.2 * ppm or min(w, h) < 0.25 * ppm:
            continue
        if htree is not None and len(htree.query_ball_point(ocen[i], 0.55 * ppm)) > 1:
            continue                          # a second counter next to it: 8, a letter
        pad = int(0.5 * ppm) + 2
        y0, y1, x0, x1 = max(y - pad, 0), min(y + h + pad, H), max(x - pad, 0), min(x + w + pad, W)
        hole = (olab[y0:y1, x0:x1] == i).astype(np.uint8)
        cnts, _ = cv2.findContours(hole, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cnts, key=cv2.contourArea)
        (rw, rh) = cv2.minAreaRect(c)[1]
        rect_fill = a / max((rw + 1) * (rh + 1), 1)
        elong = max(rw, rh) / max(min(rw, rh), 1)
        if rect_fill < 0.72 or elong > 3.5:
            continue
        inkw = inkc[y0:y1, x0:x1]
        d0 = cv2.dilate(hole, k_in)
        ringm = (d0 > 0) & (hole == 0)
        ring_ink = float(inkw[ringm].mean())
        if ring_ink < 0.85:
            continue                          # not closed by an outline
        d1 = cv2.dilate(hole, k_ring)
        d2 = cv2.dilate(hole, k_out)
        outer = (d2 > 0) & (d1 == 0)
        out_ink = float(inkw[outer].mean())
        if out_ink > 0.2:
            continue                          # outline is part of a heavy mass / a word
        filled = (d1 > 0) & ((inkw > 0) | (hole > 0))
        # a square has 4 corners; the counters of 0, 6, 8, O are ovals (5+ vertices)
        fc, _ = cv2.findContours(filled.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        fc = max(fc, key=cv2.contourArea)
        if len(cv2.approxPolyDP(fc, 0.06 * cv2.arcLength(fc, True), True)) != 4:
            continue
        # the outline's own ink: a barn outline holds one hole; a letter (B, R, P, 8, 9 …)
        # or digit with this counter holds more than one
        pad2 = int(1.5 * ppm)
        z0, z1, w0_, w1_ = max(y - pad2, 0), min(y + h + pad2, H), max(x - pad2, 0), min(x + w + pad2, W)
        zi = inkc[z0:z1, w0_:w1_]
        _, zl = cv2.connectedComponents(zi, connectivity=8)
        ring_lab = np.bincount(zl[(cv2.dilate((olab[z0:z1, w0_:w1_] == i).astype(np.uint8), k_in) > 0) & (zi > 0)]).argmax() \
            if ((olab[z0:z1, w0_:w1_] == i).any()) else 0
        if ring_lab > 0:
            cm = (zl == ring_lab).astype(np.uint8)
            hc, hh_ = cv2.findContours(cm, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
            nh = 0
            if hh_ is not None:
                for q_, hq in enumerate(hh_[0]):
                    if hq[3] < 0:
                        continue
                    ha_ = cv2.contourArea(hc[q_])
                    bx_, by_, bw_, bh_ = cv2.boundingRect(hc[q_])
                    if ha_ >= 0.015 * ppm ** 2 and max(bw_, bh_) < 3 * max(min(bw_, bh_), 1) and \
                            math.hypot(bx_ + bw_ / 2 + w0_ - ocen[i][0], by_ + bh_ / 2 + z0 - ocen[i][1]) < 1.5 * ppm:
                        nh += 1
            if nh >= 2:
                continue
        sqfill[y0:y1, x0:x1] |= filled.astype(np.uint8)
        fa = int(filled.sum())
        opens.append({"oi": i, "x": float(ocen[i][0]), "y": float(ocen[i][1]), "area_mm2": fa / ppm ** 2,
                      "hole_mm2": a / ppm ** 2, "elong": elong, "solidity": 1.0, "rect_fill": rect_fill,
                      "tri_fill": 0.5, "dark": float(np.median(img[y0:y1, x0:x1].min(2)[ringm & (inkw > 0)])),
                      "w": int(w + 2 * ring_t), "h": int(h + 2 * ring_t), "theta": 0.0, "shape_ok": True,
                      "ring_ink": ring_ink, "out_ink": out_ink, "open": True})
    del olab, inkc
    for r in recs:
        r["open"] = False

    cy0, cy1, cx0, cx1 = core_box
    in_core = lambda r: cy0 <= r["y"] < cy1 and cx0 <= r["x"] < cx1
    recs_c = [r for r in recs if in_core(r)]
    opens = [r for r in opens if in_core(r)]

    # --- context in a window around each candidate. Light ink (hairlines of lettering,
    # soft edges) connects a blob to the rest of its glyph; components are only followed
    # inside the window, so roads and rails leaving it are "lines", not glyphs.
    R = int(round(2.0 * ppm))
    small_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    min_letter = 0.2 * ppm
    ann_in, ann_out = 0.45 * ppm, 1.2 * ppm
    thick_t = max(2.5, 0.13 * ppm)
    thetas = np.deg2rad(np.arange(0, 180, 3))
    line_band = LINE_BAND * ppm
    corridor = 0.32 * ppm
    side_min = int(0.35 * ppm * 2)          # ~0.35 mm of a 2 px line on each side
    # big lettering: thick (>= 0.34 mm) ink masses that are not symbols (stems, bowls of
    # large serif capitals); their hairlines are often too faint to connect the serifs
    er = int(round(0.17 * ppm))
    eroded = cv2.erode(core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * er + 1,) * 2))
    deep = np.zeros(n, bool)
    deep[np.unique(lab[eroded > 0])] = True
    del eroded
    glyph_mass = np.zeros(n, bool)
    shp = {r["i"]: r for r in recs}
    for i in range(1, n):
        if area_mm2[i] < 0.2 or not deep[i]:
            continue
        r = shp.get(i)
        if r is not None and r["shape_ok"]:
            continue
        if r is not None and r["solidity"] >= 0.7 and max(r["w"], r["h"]) < 1.2 * ppm:
            continue                          # merged pair of symbols, a long barn
        if st[i, 2] > 6 * ppm or st[i, 3] > 6 * ppm:
            continue                          # town blocks, long heavy lines
        glyph_mass[i] = True
    gm_pts = []
    for i in np.nonzero(glyph_mass)[0]:
        x, y, w, h, _ = st[i]
        ys_, xs_ = np.nonzero(lab[y:y + h, x:x + w] == i)
        sel = slice(None, None, 4)
        gm_pts.append(np.column_stack([xs_[sel] + x, ys_[sel] + y]))
    gm_tree = cKDTree(np.concatenate(gm_pts)) if gm_pts else None
    for r in recs_c + opens:
        cx, cy = int(round(r["x"])), int(round(r["y"]))
        y0, y1, x0, x1 = max(cy - R, 0), min(cy + R + 1, H), max(cx - R, 0), min(cx + R + 1, W)
        ccx, ccy = r["x"] - x0, r["y"] - y0
        mxw, huew, waterw, _ = _colour_tests(img[y0:y1, x0:x1])
        huew &= inside[y0:y1, x0:x1] > 0
        lp = max(float(np.percentile(mxw, 80)), 0.8 * paper)
        inkw = ink[y0:y1, x0:x1]
        lightw = ((mxw < 0.80 * lp) & huew).astype(np.uint8) | inkw
        labw = lab[y0:y1, x0:x1]
        sqw = sqfill[y0:y1, x0:x1]
        if r["open"]:
            _, sl = cv2.connectedComponents(sqw, connectivity=8)
            own = sl == sl[min(int(ccy), sl.shape[0] - 1), min(int(ccx), sl.shape[1] - 1)]
            if not sqw[min(int(ccy), sl.shape[0] - 1), min(int(ccx), sl.shape[1] - 1)]:
                own = np.zeros_like(own)
                own[min(int(ccy), sl.shape[0] - 1), min(int(ccx), sl.shape[1] - 1)] = True
            lightw = lightw | own.astype(np.uint8)
        else:
            own = labw == r["i"]
        symw = (cv2.dilate((sym_ok[labw] | own).astype(np.uint8), small_k) > 0) | \
               (cv2.dilate(sqw, small_k) > 0)
        hh_, ww_ = own.shape
        # light components
        ncl, cl, cst, _ = cv2.connectedComponentsWithStats(lightw, connectivity=8)
        c = int(np.bincount(cl[own]).argmax())
        comp = cl == c

        def touching(st_):
            return st_[0] == 0 or st_[1] == 0 or st_[0] + st_[2] >= ww_ or st_[1] + st_[3] >= hh_
        touches = touching(cst[c])
        # dark sub-components: lines leaving the window vs bounded glyph parts
        nd, dl, dst, _ = cv2.connectedComponentsWithStats(inkw, connectivity=8)
        leaving = np.zeros(nd, bool)
        for q in range(1, nd):
            leaving[q] = touching(dst[q])
        resid_dark = int((comp & (inkw > 0) & ~symw & ~leaving[dl]).sum())
        # thick strokes (letter stems, >= ~0.26 mm) joined to the blob through light ink
        dtw = cv2.distanceTransform(inkw, cv2.DIST_L2, 3)
        resid_thick = int((comp & (dtw >= thick_t) & ~symw).sum())
        # the thick part of the blob's own dark component: a house is a compact square (with
        # thin roads touching it); a letter stroke cut into several "squares" by the
        # opening is curved (low solidity) or a long bar
        od = int(np.bincount(dl[own]).argmax()) if own.any() else 0
        t_area, t_sol, t_elong, t_len = 0, 1.0, 1.0, 0.0
        if od > 0:
            T_ = ((dl == od) & (dtw >= 0.6 * thick_t)).astype(np.uint8)
            t_area = int(T_.sum())
            if t_area > 8:
                tc, _ = cv2.findContours(T_, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                pts = np.concatenate(tc)
                hull = np.zeros_like(T_)
                cv2.fillConvexPoly(hull, cv2.convexHull(pts), 1)
                t_sol = t_area / max(int(hull.sum()), 1)
                (tw, th_), = [cv2.minAreaRect(pts)[1]]
                t_elong = max(tw, th_) / max(min(tw, th_), 1)
                t_len = max(tw, th_) / ppm
        # on a line: a straight dark line (rail, road casing at a crossing) runs through
        # the blob, with ink on both sides of it. A house beside a road has the casing at
        # >= half its width from its centre; a lane ending at a house has ink on one side.
        on_line = False
        if touches:
            ys_, xs_ = np.nonzero((inkw > 0) & ~symw)
            dx, dy = xs_ - ccx, ys_ - ccy
            rr = np.hypot(dx, dy)
            sel = (rr > ann_in) & (rr < ann_out)
            if sel.sum() > 2 * side_min:
                dx, dy = dx[sel], dy[sel]
                for th in thetas:
                    ux, uy = math.cos(th), math.sin(th)
                    dd = -dx * uy + dy * ux
                    al = dx * ux + dy * uy
                    near = np.abs(dd) < corridor
                    if near.sum() < 2 * side_min:
                        continue
                    # lines at offset d (1 px bins) with ink on both sides along them
                    bins = np.round(dd[near]).astype(int)
                    alp = al[near] > 0
                    off = int(corridor) + 1
                    pos = np.bincount(bins[alp] + off, minlength=2 * off + 1)
                    neg = np.bincount(bins[~alp] + off, minlength=2 * off + 1)
                    # 3 px wide bands
                    pos3 = np.convolve(pos, [1, 1, 1], "same")
                    neg3 = np.convolve(neg, [1, 1, 1], "same")
                    both = (pos3 >= side_min) & (neg3 >= side_min)
                    if not both.any():
                        continue
                    offs = np.nonzero(both)[0] - off
                    through = np.abs(offs) < line_band
                    if (offs < -line_band).any() and (offs > line_band).any():
                        on_line = True          # between two parallel lines: inside a road
                        break
                    if through.any() and not (np.abs(offs) >= 0.15 * ppm).any():
                        on_line = True          # on a single line (rail, boundary): no
                        break                   # partner casing, so not a house on a road
        # holes (letter counters) near the blob, for glyphs not attached to lines
        holes = 0
        if not touches and not r["open"]:
            cnts, hier = cv2.findContours(comp.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
            if hier is not None:
                for q, hh in enumerate(hier[0]):
                    if hh[3] >= 0:
                        ha = cv2.contourArea(cnts[q])
                        if 3 <= ha <= 0.25 * ppm ** 2:
                            hx, hy, hw2, hh2 = cv2.boundingRect(cnts[q])
                            if max(hw2, hh2) < 0.8 * ppm and math.hypot(hx + hw2 / 2 - ccx, hy + hh2 / 2 - ccy) < 0.9 * ppm:
                                holes += 1
        # other compact non-symbol components (letters) within 1.3 mm
        letters = 0
        for q in range(1, ncl):
            if q == c:
                continue
            qx, qy, qw, qh, qa = cst[q]
            if touching(cst[q]) or max(qw, qh) < min_letter or qa < 0.02 * ppm ** 2:
                continue
            if math.hypot(qx + qw / 2 - ccx, qy + qh / 2 - ccy) > 1.3 * ppm:
                continue
            if max(qw, qh) >= 4.5 * max(min(qw, qh), 1):
                continue                      # a dash, not a letter
            qm = cl[qy:qy + qh, qx:qx + qw] == q
            if (qm & symw[qy:qy + qh, qx:qx + qw]).sum() > 0.5 * qa:
                continue                      # another building symbol
            qc, _ = cv2.findContours(qm.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            rw_, rh_ = cv2.minAreaRect(np.concatenate(qc))[1]
            if min(rw_, rh_) < 0.28 * ppm or max(rw_, rh_) > 4 * min(rw_, rh_):
                continue                      # dashes of dashed roads / trails (also in pairs)
            letters += 1
        wr = int(round(0.6 * ppm))
        wwin = waterw[max(cy - y0 - wr, 0):cy - y0 + wr + 1, max(cx - x0 - wr, 0):cx - x0 + wr + 1]
        big_text = False
        if gm_tree is not None:
            dgm, _ = gm_tree.query([r["x"], r["y"]], distance_upper_bound=1.5 * ppm)
            big_text = bool(np.isfinite(dgm))
        r.update({"touches": bool(touches), "resid_dark_mm2": resid_dark / ppm ** 2,
                  "resid_thick_mm2": resid_thick / ppm ** 2, "big_text": big_text,
                  "t_ratio": t_area / max(int(own.sum()), 1), "t_sol": float(t_sol), "t_elong": float(t_elong),
                  "t_len": float(t_len),
                  "on_line": on_line, "holes": holes, "letters_near": letters,
                  "water": float(wwin.mean()), "own_px": int(own.sum())})
    # --- dash-dot boundaries: a candidate on the extension of a long dash. Thin dashes
    # (vanished in the opening) come from the ink components: straight, 0.8-6 mm long.
    n0, lab0, st0, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    dim0 = np.maximum(st0[:, 2], st0[:, 3])
    cand0 = np.nonzero((dim0 >= 0.45 * ppm) & (dim0 <= 6 * ppm))[0]
    cand0 = cand0[cand0 > 0]
    if len(cand0):
        ys_, xs_ = np.nonzero(ink)
        ll = lab0[ys_, xs_]
        cnt = np.bincount(ll, minlength=n0).astype(float) + 1e-9
        mx_ = np.bincount(ll, xs_, n0) / cnt; my_ = np.bincount(ll, ys_, n0) / cnt
        sxx = np.bincount(ll, xs_.astype(float) ** 2, n0) / cnt - mx_ ** 2
        syy = np.bincount(ll, ys_.astype(float) ** 2, n0) / cnt - my_ ** 2
        sxy = np.bincount(ll, xs_.astype(float) * ys_, n0) / cnt - mx_ * my_
        del ys_, xs_, ll
        for q in cand0:
            tr, det = sxx[q] + syy[q], sxx[q] * syy[q] - sxy[q] ** 2
            dd = math.sqrt(max(tr * tr / 4 - det, 0))
            l1, l2 = tr / 2 + dd, max(tr / 2 - dd, 1e-6)
            if l1 / l2 < 20 or 4 * math.sqrt(l1) < 0.6 * ppm:
                continue                          # not a straight dash (power-line dashes ~0.9 mm)
            th = 0.5 * math.atan2(2 * sxy[q], sxx[q] - syy[q])
            dashes.append((mx_[q], my_[q], math.cos(th), math.sin(th), 2 * math.sqrt(l1)))
    del lab0
    D = np.array(dashes) if dashes else None
    dtree = cKDTree(D[:, :2]) if dashes else None
    out = recs_c + opens
    for r in out:
        # a dot of a dash-dot line has dashes in line with it on both sides
        sides = set()
        if dtree is not None:
            for q in dtree.query_ball_point([r["x"], r["y"]], 6 * ppm):
                qx, qy, ux, uy, half = D[q]
                vx, vy = r["x"] - qx, r["y"] - qy
                along = vx * ux + vy * uy
                across = abs(-vx * uy + vy * ux)
                if half < abs(along) < half + 3.5 * ppm and across < 0.15 * ppm:
                    # side along the line's own axis, oriented canonically (dash axes
                    # come out of atan2 as either direction)
                    flip = -1 if (ux < 0 or (ux == 0 and uy < 0)) else 1
                    sides.add(1 if along * flip < 0 else -1)
                    if len(sides) == 2:
                        break
        r["on_dash"] = len(sides) == 2
    return out


def detect_symbols(pdf: "GeoPDF", debug=None, tile=3000):
    """Building symbols on one sheet -> (kept symbols, stats). Each symbol: pixel centroid,
    area (mm² on paper), shape / context features, rejection reasons, score 0..1.
    Tiled (tile x tile px plus an 8 mm margin) so memory stays ~0.5 GB per sheet."""
    import cv2
    g = pdf.g
    ppm = g["px_per_mm"]
    H, W = pdf.H, pdf.W
    # low resolution: paper level and the urban tint
    small = pdf.read(0, H, 0, W, step=4)
    ins_small = np.zeros(small.shape[:2], np.uint8)
    cv2.fillPoly(ins_small, [np.round(g["neat_px"] / 4).astype(np.int32)], 1)
    paper = float(np.percentile(small[::4, ::4].max(2)[ins_small[::4, ::4] > 0], 75))
    urban_px = urban_tint(small, ins_small, ppm)
    del small, ins_small
    ink_t = 0.55 * paper
    margin = int(round(8 * ppm))
    boxes = [(y, min(y + tile, H), x, min(x + tile, W)) for y in range(0, H, tile) for x in range(0, W, tile)]
    # neat line bbox: skip tiles of the collar
    nx0, ny0 = g["neat_px"].min(0); nx1, ny1 = g["neat_px"].max(0)
    boxes = [b for b in boxes if b[1] > ny0 and b[0] < ny1 and b[3] > nx0 and b[2] < nx1]

    def tile_arrays(b):
        y0, y1, x0, x1 = max(b[0] - margin, 0), min(b[1] + margin, H), max(b[2] - margin, 0), min(b[3] + margin, W)
        return (y0, y1, x0, x1), pdf.read(y0, y1, x0, x1), _inside_tile(g["neat_px"], y0, y1, x0, x1, ppm)
    # pass 1: blob areas of the whole sheet -> threshold between dots and symbols
    areas = []
    for b in boxes:
        (y0, y1, x0, x1), im, ins = tile_arrays(b)
        _, core, k = _ink_core(im, ins, ink_t, ppm)
        n, lab, st, cen = cv2.connectedComponentsWithStats(core, connectivity=8)
        sel = (cen[1:, 1] + y0 >= b[0]) & (cen[1:, 1] + y0 < b[1]) & (cen[1:, 0] + x0 >= b[2]) & (cen[1:, 0] + x0 < b[3])
        areas.append(st[1:, 4][sel] / ppm ** 2)
        del core, lab, im, ins
    disc_mm2 = k.sum() / ppm ** 2
    a_min = _valley_threshold(np.concatenate(areas), lo=max(0.05, 1.35 * disc_mm2), hi=max(0.13, 2.6 * disc_mm2))
    # pass 2: candidates with context
    allr = []
    for b in boxes:
        (y0, y1, x0, x1), im, ins = tile_arrays(b)
        out = _detect_tile(im, ins, ppm, paper, ink_t, a_min, (b[0] - y0, b[1] - y0, b[2] - x0, b[3] - x0))
        for r in out:
            r["x"] += x0; r["y"] += y0
        allr += out
        del im, ins
    a_typ = float(np.median([r["area_mm2"] for r in allr if r["shape_ok"] and not r["open"]] or [0.15]))
    a_typ_open = float(np.median([r["area_mm2"] for r in allr if r["open"]] or [a_typ]))
    keep = []
    for r in allr:
        reasons = []
        if r["area_mm2"] < a_min and not r["open"]:
            reasons.append("small")
        if r["elong"] > 2.6:
            reasons.append("elongated")
        if r["solidity"] < 0.82 or r["rect_fill"] < 0.62:
            reasons.append("shape")
        if r["resid_thick_mm2"] > 0.02:
            reasons.append("glyph")           # letter stems hang on it: part of a word
        if r["big_text"]:
            reasons.append("bigtext")         # next to the strokes of large lettering
        if r["t_ratio"] > 1.6 and (r["t_sol"] < 0.55 or (r["t_elong"] > 3 and r["t_len"] > 0.9)):
            reasons.append("stroke")          # piece of a curved / long heavy stroke
        if r["on_line"]:
            reasons.append("online")          # knot on a rail / road crossing
        if r["tri_fill"] > 0.72 and r["area_mm2"] >= 0.22:
            reasons.append("triangle")        # triangulation station, letter wedge
        if not r["touches"] and r["resid_dark_mm2"] > 0.04:
            reasons.append("glyph2")          # isolated glyph: other dark strokes around it
        if r["holes"] >= 1:
            reasons.append("counter")         # a letter with a counter (a, e, o, R …)
        if r["letters_near"] >= 2 or (r["open"] and r["letters_near"] >= 1 and r["elong"] > 1.2):
            reasons.append("text")
        if r["water"] > 0.06:
            reasons.append("water")
        if r["on_dash"]:
            reasons.append("dashline")
        if r["dark"] > 0.45 * paper:
            reasons.append("faint")
        if urban_px is not None and urban_px[0][min(int(r["y"]) // 4, urban_px[0].shape[0] - 1),
                                                min(int(r["x"]) // 4, urban_px[0].shape[1] - 1)]:
            reasons.append("urban")           # red urban tint: only landmark buildings shown
        r["reject"] = reasons
        r["s_tmp"] = None
        s_area = math.exp(-abs(math.log(r["area_mm2"] / (a_typ_open if r["open"] else a_typ))) / 0.8)
        s_shape = max(0.0, min(1.0, (2.6 - r["elong"]) / 1.2)) * max(0.0, min(1.0, (r["solidity"] - 0.78) / 0.12)) \
            * max(0.0, min(1.0, (r["rect_fill"] - 0.58) / 0.15))
        s_dark = min(1.0, max(0.0, (0.45 * paper - r["dark"]) / (0.25 * paper)))
        s_ctx = 1.0 - 0.25 * min(r["letters_near"], 1)
        r["score"] = float(max(0.0, min(1.0, 0.3 * s_area + 0.4 * s_shape + 0.2 * s_dark + 0.1)) * s_ctx)
    # lettering leaves a trail of rejected letter pieces: a kept blob with two or more of
    # them within 1.5 mm is part of a word too (road knots / hachures don't count)
    from scipy.spatial import cKDTree
    LETTERY = {"glyph", "glyph2", "counter", "text", "bigtext"}
    lp_ = [r for r in allr if LETTERY & set(r["reject"])]
    ltree = cKDTree([[r["x"], r["y"]] for r in lp_]) if lp_ else None
    for r in allr:
        r.pop("s_tmp", None)
        if not r["reject"] and ltree is not None:
            if len(ltree.query_ball_point([r["x"], r["y"]], 1.5 * ppm)) >= 2:
                r["reject"].append("nearletters")
        if not r["reject"]:
            keep.append(r)
    stats = {"paper": paper, "ink_t": ink_t, "a_min_mm2": a_min, "a_typ_mm2": a_typ,
             "n_candidates": len(allr), "n_open_candidates": sum(1 for r in allr if r["open"]),
             "n_kept": len(keep), "n_kept_open": sum(1 for r in keep if r["open"]),
             "urban_rings_px": urban_px[1] if urban_px is not None else []}
    if debug is not None:
        debug["all"] = allr
    return keep, stats


# ----------------------------------------------------------------------------- orchards
ORCHARD_VERSION = 3


def extract_orchards(sheet: "GeoPDF", step=3):
    """Orchard and vineyard extents on a 1940s-50s sheet (green vegetation overprint):
      orchard  = regular pattern of round green dots ~1 mm across on white;
      vineyard = green tint carrying a screen of white lines ~0.9 mm apart (a periodic
                 texture; solid woodland tint and woodland cut by contours have none).
    -> list of {"kind", "rings": [outer, holes...] in full-res pixels, "area_mm2"}."""
    import cv2
    g = sheet.g
    sm = sheet.read(0, sheet.H, 0, sheet.W, step=step)
    sheet._cache.clear()
    ppm = g["px_per_mm"] / step
    green = np.zeros(sm.shape[:2], np.uint8)
    paperish = np.zeros(sm.shape[:2], np.uint8)     # white paper (the vineyard screen lines)
    for r in range(0, sm.shape[0], 1024):
        b = sm[r:r + 1024].astype(np.int16)
        green[r:r + 1024] = (b[:, :, 1] - b[:, :, 2] > 45) & (b[:, :, 1] > 150) & (b[:, :, 1] >= b[:, :, 0] - 10)
        paperish[r:r + 1024] = (b.min(2) > 175) & (b[:, :, 1] - b[:, :, 2] < 40)
    del sm
    ins = np.zeros(green.shape, np.uint8)
    cv2.fillPoly(ins, [np.round(g["neat_px"] / step).astype(np.int32)], 1)
    ins = cv2.erode(ins, np.ones((int(ppm) | 1,) * 2, np.uint8))
    green &= ins
    if green.mean() < 0.002:
        return []
    n, lab, st, _ = cv2.connectedComponentsWithStats(green, connectivity=8)
    w, h = st[:, 2], st[:, 3]
    fill = st[:, 4] / np.maximum(w * h, 1)
    dot = (np.maximum(w, h) > 0.7 * ppm) & (np.maximum(w, h) < 1.6 * ppm) & (fill > 0.66) & (fill < 0.88) \
        & (np.maximum(w, h) < 1.35 * np.minimum(w, h))
    dot[0] = False
    dens = cv2.blur(dot[lab].astype(np.float32), (int(3 * ppm) | 1,) * 2)
    del lab
    orchard = (dens > 0.15).astype(np.uint8)
    del dens
    kw = int(2.0 * ppm) | 1
    vine = np.zeros(green.shape, np.uint8)
    band, mg = 1200, 3 * kw
    # the screen lines of the vineyard symbol are white paper; contour lines (brown) or
    # roads crossing a woodland tint every ~1 mm are not, so only green-vs-white counts
    for r0 in range(0, green.shape[0], band):                  # in bands: bounded memory
        a0, a1 = max(r0 - mg, 0), min(r0 + band + mg, green.shape[0])
        gfl = (1 - paperish[a0:a1]).astype(np.float32)
        gf = cv2.blur(gfl, (int(1.2 * ppm) | 1,) * 2)
        A = gfl - cv2.blur(gfl, (kw, kw))
        del gfl
        den = cv2.blur(A * A, (kw, kw)) + 1e-3

        def corr(l):
            B = np.zeros_like(A)
            B[:, l:] = A[:, :-l]
            B *= A
            return cv2.blur(B, (kw, kw)) / den
        best = None
        for lmm in (0.8, 0.85, 0.9, 0.95, 1.0):
            l = max(2, int(round(lmm * ppm)))
            c = corr(l) - np.maximum(corr(max(1, l // 2)), 0)
            best = c if best is None else np.maximum(best, c)
        gg = cv2.blur(green[a0:a1].astype(np.float32), (int(1.2 * ppm) | 1,) * 2)
        v = (gf > 0.40) & (gf < 0.92) & (gg > 0.35) & (cv2.blur(best, (kw, kw)) > 0.22)
        vine[r0:min(r0 + band, green.shape[0])] = v[r0 - a0:r0 - a0 + min(band, green.shape[0] - r0)]
        del A, den, best, gf, v

    def clean(m, close_mm, open_mm):
        kc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(close_mm * ppm) | 1,) * 2)
        ko = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(open_mm * ppm) | 1,) * 2)
        return cv2.morphologyEx(cv2.morphologyEx(m, cv2.MORPH_CLOSE, kc), cv2.MORPH_OPEN, ko)
    orchard = clean(orchard, 2.0, 2.0) & ins
    vine = clean(vine, 1.5, 2.5) & ins & (1 - orchard)
    min_mm2 = max(4.0, 10000 / (g["m_per_px"] * g["px_per_mm"]) ** 2)     # >= 1 ha and >= 4 mm²
    out = []
    for kind, m in (("orchard", orchard), ("vineyard", vine)):
        cnts, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        if hier is None:
            continue
        for i, hh in enumerate(hier[0]):
            if hh[3] >= 0:
                continue
            a = cv2.contourArea(cnts[i]) / ppm ** 2
            if a < min_mm2:
                continue
            rings = [cv2.approxPolyDP(cnts[i], 0.25 * ppm, True)]
            j = hh[2]
            while j >= 0:
                if cv2.contourArea(cnts[j]) / ppm ** 2 >= min_mm2 / 2:
                    rings.append(cv2.approxPolyDP(cnts[j], 0.25 * ppm, True))
                j = hier[0][j][0]
            out.append({"kind": kind, "area_mm2": round(a, 1),
                        "rings": [(r_[:, 0, :] * step + step / 2).round(1).tolist() for r_ in rings if len(r_) >= 3]})
    return out


# ----------------------------------------------------------------------------- alignment
def px_to_proj_fn(georef):
    a, b, c, d, e, f = georef["ctm"]
    s, page_h = georef["s"], georef["page_h"]

    def px_to_proj(col, row):
        x = np.asarray(col, float) / s
        y = page_h - np.asarray(row, float) / s
        return a * x + c * y + e, b * x + d * y + f
    return px_to_proj


_ROADS = None


def modern_roads(bbox):
    """Overture road centrelines (OpenStreetMap) inside bbox, or None if not downloaded."""
    global _ROADS
    if _ROADS is None:
        if not ROADS.exists():
            return None
        import geopandas as gpd
        r = gpd.read_parquet(ROADS, columns=["class", "geometry"])
        _ROADS = r[r["class"].isin(["primary", "secondary", "tertiary", "residential", "unclassified", "trunk"])]
    m = 0.02
    return _ROADS.cx[bbox[0] - m:bbox[2] + m, bbox[1] - m:bbox[3] + m]


def road_alignment(res, ink_small):
    """Local offset of the map against today's roads (OpenStreetMap via Overture).

    Many of the valley's county roads are where they were in the 1890s, so the black ink
    of the map (roads, buildings) is cross-correlated with the rasterised modern road
    centrelines in 2.5 km windows; the window shifts are fitted with a robust affine model
    (outlier windows: changed roads, the repeating road grid). The early 15' surveys are
    off by 100-250 m this way (not on NAD27 control), the 1940s-50s maps by ~5 m.
    -> dict with the model in metres (shift = map - modern, image axes x east / y south)."""
    import cv2
    import pyproj
    from pyproj.transformer import TransformerGroup
    step = res["ink_step"]
    px_to_proj = px_to_proj_fn(res["georef"])
    mpp = res["m_per_px"] * step
    roads = modern_roads(res["bbox"])
    if roads is None or not len(roads):
        return {"aligned": False, "reason": "no modern roads"}
    crs = crs_for(res["proj"])
    pyproj.datadir.append_data_dir(str(PROJ_DIR))
    tg = TransformerGroup("EPSG:4326", crs.geodetic_crs, always_xy=True,
                          area_of_interest=pyproj.aoi.AreaOfInterest(-123.5, 36.5, -121.0, 38.8))
    t1 = tg.transformers[0]
    t2 = pyproj.Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True)
    X0, Y0 = px_to_proj(0, 0)
    X1, Y1 = px_to_proj(1, 0)
    X2, Y2 = px_to_proj(0, 1)
    Ai = np.linalg.inv(np.array([[X1 - X0, X2 - X0], [Y1 - Y0, Y2 - Y0]]))
    rr = np.zeros(ink_small.shape, np.uint8)
    for geom in roads.geometry:
        for line in getattr(geom, "geoms", [geom]):
            c = np.asarray(line.coords)
            lo, la = t1.transform(c[:, 0], c[:, 1])
            x, y = t2.transform(lo, la)
            px = Ai @ np.vstack([np.asarray(x) - X0, np.asarray(y) - Y0])
            cv2.polylines(rr, [np.round(px.T / step).astype(np.int32)], False, 1, 1)
    Rb = cv2.GaussianBlur(rr.astype(np.float32), (0, 0), 1.5)
    Ib = cv2.GaussianBlur((ink_small > 0).astype(np.float32), (0, 0), 1.5)
    win = int(2500 / mpp)
    S = int((450 if res.get("edition") == "early" else 150) / mpp)
    sup = max(2, int(60 / mpp))
    rows = []
    for y in range(S, Ib.shape[0] - win - S, win // 2):
        for x in range(S, Ib.shape[1] - win - S, win // 2):
            tpl = Rb[y:y + win, x:x + win]
            if tpl.sum() < 3 * win or Ib[y:y + win, x:x + win].sum() < 3 * win:
                continue
            cc = cv2.matchTemplate(Ib[y - S:y + win + S, x - S:x + win + S], tpl, cv2.TM_CCOEFF_NORMED)
            _, r1, _, (lx, ly) = cv2.minMaxLoc(cc)
            cc2 = cc.copy()
            cc2[max(ly - sup, 0):ly + sup + 1, max(lx - sup, 0):lx + sup + 1] = -1
            r2 = cc2.max()
            if r1 >= 0.15 and r1 - r2 >= 0.02:
                rows.append(((x + win / 2) * mpp, (y + win / 2) * mpp, (lx - S) * mpp, (ly - S) * mpp, r1))
    if len(rows) < 3:
        return {"aligned": False, "reason": f"{len(rows)} usable windows", "n_windows": len(rows)}
    A = np.array(rows)
    xc, yc = A[:, 0].mean(), A[:, 1].mean()
    X = np.column_stack([np.ones(len(A)), (A[:, 0] - xc) / 1000, (A[:, 1] - yc) / 1000])
    # consensus: the shift most windows agree with (within tol), weighted by correlation;
    # windows locked onto the wrong road of the grid or onto changed roads drop out
    tol = 45.0 if res.get("edition") == "early" else 15.0
    best_w, best_use = -1, None
    for k in range(len(A)):
        inl = np.hypot(A[:, 2] - A[k, 2], A[:, 3] - A[k, 3]) <= 2 * tol
        w = A[inl, 4].sum()
        if w > best_w:
            best_w, best_use = w, inl
    use = best_use
    if use.sum() < 4 or use.sum() < 0.35 * len(A):
        return {"aligned": False, "reason": f"no consensus ({int(use.sum())} of {len(A)} windows)", "n_windows": len(A)}
    affine = False
    cx_ = np.array([np.median(A[use, 2]), 0, 0]); cy_ = np.array([np.median(A[use, 3]), 0, 0])
    for _ in range(5):
        if use.sum() >= 8 and np.ptp(A[use, 0]) > 4000 and np.ptp(A[use, 1]) > 4000:
            cxa, *_ = np.linalg.lstsq(X[use], A[use, 2], rcond=None)
            cya, *_ = np.linalg.lstsq(X[use], A[use, 3], rcond=None)
            # an affine model must not move any part of the sheet by much more than the windows did
            corners = np.array([[1, -6, -7], [1, 6, -7], [1, -6, 7], [1, 6, 7]])
            if np.abs(corners @ cxa).max() < 400 and np.abs(corners @ cya).max() < 400:
                cx_, cy_, affine = cxa, cya, True
        resid = np.hypot(A[:, 2] - X @ cx_, A[:, 3] - X @ cy_)
        new = resid <= tol
        if (new == use).all() or new.sum() < 4:
            break
        use = new
    resid = np.hypot(A[:, 2] - X @ cx_, A[:, 3] - X @ cy_)
    rms = float(np.sqrt(np.mean(resid[use] ** 2)))
    shift = np.hypot(X[use] @ cx_, X[use] @ cy_)
    return {"aligned": True, "model": "affine" if affine else "constant", "xc_m": float(xc), "yc_m": float(yc),
            "cx": [float(v) for v in cx_], "cy": [float(v) for v in cy_], "n_windows": len(rows),
            "n_used": int(use.sum()), "rms_m": round(rms, 1), "median_shift_m": round(float(np.median(shift)), 1)}


def apply_alignment(res, cols, rows):
    """Pixel coordinates of the map -> pixel coordinates in today's frame."""
    al = res.get("align") or {}
    cols = np.asarray(cols, float); rows = np.asarray(rows, float)
    if not al.get("aligned"):
        return cols, rows
    late = res.get("edition") != "early"
    if late and al["median_shift_m"] < 10:
        return cols, rows                    # accurate 1:24,000 sheets: leave as published
    m = res["m_per_px"]
    xk = (cols * m - al["xc_m"]) / 1000
    yk = (rows * m - al["yc_m"]) / 1000
    dx = al["cx"][0] + al["cx"][1] * xk + al["cx"][2] * yk
    dy = al["cy"][0] + al["cy"][1] * xk + al["cy"][2] * yk
    return cols - dx / m, rows - dy / m


def georeference(res):
    """(Re)compute lon/lat of a processed sheet's symbols, urban outlines and neat line
    from its pixel coordinates, the GeoPDF registration and the road alignment."""
    import cv2
    crs = crs_for(res["proj"])
    p2p = px_to_proj_fn(res["georef"])
    ink_png = INK_CACHE / f"{res['id']}.png"
    if ink_png.exists() and ROADS.exists():
        res["align"] = road_alignment(res, cv2.imread(str(ink_png), cv2.IMREAD_GRAYSCALE))
    if res["symbols"]:
        c, r = apply_alignment(res, [s_["px"][0] for s_ in res["symbols"]], [s_["px"][1] for s_ in res["symbols"]])
        lon, lat = to_wgs84(crs, *p2p(c, r))
        for s_, a, b in zip(res["symbols"], lon, lat):
            s_["lon"], s_["lat"] = round(float(a), 7), round(float(b), 7)
    res["urban_tint"] = []
    for ring in res.get("urban_px", []):
        ring = np.asarray(ring, float)
        c, r = apply_alignment(res, ring[:, 0], ring[:, 1])
        lon, lat = to_wgs84(crs, *p2p(c, r))
        res["urban_tint"].append([[round(float(a), 6), round(float(b), 6)] for a, b in zip(lon, lat)])
    res["orchards"] = []
    for o in res.get("orchard_px", []):
        rings = []
        for ring in o["rings"]:
            ring = np.asarray(ring, float)
            c, r = apply_alignment(res, ring[:, 0], ring[:, 1])
            lon, lat = to_wgs84(crs, *p2p(c, r))
            rings.append([[round(float(a), 6), round(float(b), 6)] for a, b in zip(lon, lat)])
        res["orchards"].append({"kind": o["kind"], "rings": rings})
    # the neat line stays where the sheet was registered (coverage); shift it with the map
    nl = np.asarray(res["neat_px"], float)
    c, r = apply_alignment(res, nl[:, 0], nl[:, 1])
    lon, lat = to_wgs84(crs, *p2p(c, r))
    res["neatline"] = [[round(float(a), 7), round(float(b), 7)] for a, b in zip(lon, lat)]
    return res


# ----------------------------------------------------------------------------- per sheet
def sheet_path(m) -> Path:
    return MAP_CACHE / f"{m['id']}.json"


def process_sheet(m: dict, keep_raw=False, debug_crops=0) -> dict:
    """Download, detect, align and georeference one sheet; cache the result as JSON
    (pixel coordinates + registration, so it can be re-georeferenced without the PDF)
    and a low-resolution ink image for the road alignment."""
    import cv2
    import pyproj
    out = sheet_path(m)
    want_orchards = m.get("edition") == "late"
    TOPO_RAW.mkdir(parents=True, exist_ok=True)
    pdf = TOPO_RAW / Path(m["pdf_url"].replace("%20", "_")).name
    if out.exists():
        res = json.loads(out.read_text())
        if res.get("detector_version") == DETECTOR_VERSION or (
                m.get("edition") == "early" and res.get("detector_version") in EARLY_COMPATIBLE):
            if want_orchards and res.get("orchard_version") != ORCHARD_VERSION:
                download_file(m["pdf_url"], pdf)
                res["orchard_px"] = extract_orchards(GeoPDF(pdf))
                res["orchard_version"] = ORCHARD_VERSION
                georeference(res)
                out.write_text(json.dumps(res))
                if not keep_raw:
                    pdf.unlink(missing_ok=True)
            return res
    download_file(m["pdf_url"], pdf)
    sheet = GeoPDF(pdf)
    g = sheet.g
    log(f"{m['quad']} {m['edition_year']} 1:{m['scale']}: {sheet.W}x{sheet.H} px, "
        f"{g['px_per_mm'] * 25.4:.0f} ppi, {g['m_per_px']:.2f} m/px")
    keep, stats = detect_symbols(sheet)
    # low-resolution black ink (~8 m/px) for the alignment against today's roads
    step = max(1, int(round(8.0 / g["m_per_px"])))
    sm = sheet.read(0, sheet.H, 0, sheet.W, step=step)
    mx_, hue_ = _colour_tests(sm)[:2]
    ins = np.zeros(sm.shape[:2], np.uint8)
    cv2.fillPoly(ins, [np.round(g["neat_px"] / step).astype(np.int32)], 1)
    INK_CACHE.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(INK_CACHE / f"{m['id']}.png"), (((mx_ < 0.6 * stats["paper"]) & hue_ & (ins > 0)) * 255).astype(np.uint8))
    del sm, mx_, hue_, ins
    # registration check: neat line corners (NAD27) against the quadrangle footprint
    crs = crs_for(g["proj"])
    nx, ny = g["px_to_proj"](g["neat_px"][:, 0], g["neat_px"][:, 1])
    glon, glat = pyproj.Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True).transform(nx, ny)
    bb = m["bbox"]
    err = max(min(abs(glon[i] - bb[0]) * 88000, abs(glon[i] - bb[2]) * 88000,
                  abs(glat[i] - bb[1]) * 111000, abs(glat[i] - bb[3]) * 111000) for i in range(len(glon)))
    syms = [{"px": [round(r["x"], 1), round(r["y"], 1)], "area_mm2": round(r["area_mm2"], 4),
             "score": round(r["score"], 3), "open": bool(r["open"])} for r in keep]
    meta = m.get("meta") or fetch_meta(m)
    res = {"detector_version": DETECTOR_VERSION, "id": m["id"], "quad": m["quad"], "scale": m["scale"],
           "bbox": m["bbox"], "edition_year": m["edition_year"], "survey_year": meta.get("survey_year"),
           "date_on_map": meta.get("date_on_map"), "edit_year": meta.get("edit_year"),
           "imprint_year": meta.get("imprint_year"),
           "photo_year": meta.get("aerial_photo_year") or meta.get("photo_year"),
           "field_check_year": meta.get("field_check_year"),
           "scan_quality": meta.get("scan_quality"), "woodland_tint": meta.get("woodland_tint"),
           "edition": m.get("edition"), "source_url": m["pdf_url"], "metadata_url": m.get("meta_url"),
           "m_per_px": g["m_per_px"], "m_per_mm": g["m_per_px"] * g["px_per_mm"], "ink_step": step,
           "georef": g["georef"], "proj": g["proj"],
           "neat_px": np.round(g["neat_px"], 2).tolist(), "urban_px": stats.pop("urban_rings_px", []),
           "stats": stats, "corner_error_m": round(float(err), 1), "symbols": syms}
    if want_orchards:
        res["orchard_px"] = extract_orchards(sheet)
        res["orchard_version"] = ORCHARD_VERSION
    georeference(res)
    MAP_CACHE.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res))
    if debug_crops:
        write_debug(sheet, keep, m, debug_crops)
    del sheet
    if not keep_raw:
        pdf.unlink(missing_ok=True)
    return res


def write_debug(sheet, keep, m, n_crops):
    """A few overlay crops (kept symbols circled) for eyeballing."""
    import cv2
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(int(m["id"]) % 1000)
    for k in range(n_crops):
        if not keep:
            break
        r = keep[rng.integers(len(keep))]
        y0, x0 = int(max(r["y"] - 450, 0)), int(max(r["x"] - 600, 0))
        a = sheet.read(y0, y0 + 900, x0, x0 + 1200)
        for q in keep:
            x, y = q["x"] - x0, q["y"] - y0
            if 0 <= x < a.shape[1] and 0 <= y < a.shape[0]:
                cv2.circle(a, (int(x), int(y)), 12, (0, 120, 255) if q.get("open") else (0, 200, 0), 2)
        cv2.imwrite(str(DEBUG_DIR / f"{m['id']}_{m['quad'].replace(' ', '_')}_{m['edition_year']}_{k}.jpg"),
                    a[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 85])


# ----------------------------------------------------------------------------- farmsteads
TOWN_RADIUS_M = 150
TOWN_MAX = 8            # more than this many other symbols within TOWN_RADIUS_M: a town
FARMSTEAD_M = 60
# farmsteads below this detector score are left out: on 160 hand-checked points (4 sheets)
# it removes ~2/3 of the false positives (letter counters, hachures, power-line towers)
# and ~6 % of the true farmsteads
MIN_SCORE = 0.7


def local_xy(lon, lat, lat0):
    k = 111320.0
    return np.column_stack([np.asarray(lon) * k * math.cos(math.radians(lat0)), np.asarray(lat) * k])


def farmsteads_of_sheet(res: dict, drop=None):
    """Town filter + grouping of one sheet's symbols -> (farmstead features, town features).
    drop: optional shapely geometry (lon/lat) where a better sheet of the same period
    supersedes this one."""
    from scipy.spatial import cKDTree
    from shapely.geometry import Point, Polygon
    from shapely.ops import unary_union
    syms = res["symbols"]
    props0 = {"map_year": map_year(res), "photo_year": res.get("photo_year"), "quad": res["quad"], "scale": res["scale"]}
    towns = []
    for ring in res.get("urban_tint", []):
        if len(ring) >= 4:
            towns.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring + [ring[0]]]},
                          "properties": {**props0, "kind": "urban_tint"}})
    if not syms:
        return [], towns
    lon = np.array([s_["lon"] for s_ in syms]); lat = np.array([s_["lat"] for s_ in syms])
    area = np.array([s_["area_mm2"] for s_ in syms]); score = np.array([s_["score"] for s_ in syms])
    is_open = np.array([s_.get("open", False) for s_ in syms])
    lat0 = float(lat.mean())
    kx = 111320.0 * math.cos(math.radians(lat0))
    P = local_xy(lon, lat, lat0)
    t = cKDTree(P)
    cnt = np.array([len(v) - 1 for v in t.query_ball_point(P, TOWN_RADIUS_M)])
    core = cnt > TOWN_MAX
    # town = town cores and every symbol within TOWN_RADIUS_M of one
    town = core.copy()
    if core.any():
        d, _ = cKDTree(P[core]).query(P, distance_upper_bound=TOWN_RADIUS_M)
        town |= np.isfinite(d)
        u = unary_union([Point(x, y).buffer(TOWN_RADIUS_M, 8) for x, y in P[town]])
        for gm in getattr(u, "geoms", [u]):
            n_in = int(sum(1 for x, y in P[town] if gm.contains(Point(x, y))))
            if n_in < TOWN_MAX + 1:
                continue
            ring = [[round(x / kx, 6), round(y / 111320.0, 6)] for x, y in gm.simplify(20).exterior.coords]
            towns.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]},
                          "properties": {**props0, "kind": "dense_buildings", "n_symbols": n_in}})
    # farmsteads: dwellings (solid symbols) largest first, each taking the unassigned
    # buildings within FARMSTEAD_M; then barns / sheds (open squares) without a dwelling
    assigned = town.copy()
    feats = []
    for want_open in (False, True):
        idx = np.nonzero(~town & (is_open == want_open))[0]
        for i in idx[np.argsort(-area[idx])]:
            if assigned[i]:
                continue
            members = sorted({j for j in t.query_ball_point(P[i], FARMSTEAD_M) if not assigned[j]} | {i})
            assigned[members] = True
            if drop is not None and drop.contains(Point(lon[i], lat[i])):
                continue
            n_open = int(is_open[members].sum())
            sc = float(np.clip(0.7 * score[i] + 0.3 * score[members].mean() + 0.05 * min(len(members) - 1, 2), 0, 1))
            if want_open:
                sc *= 0.8
            feats.append({"type": "Feature",
                          "geometry": {"type": "Point", "coordinates": [round(float(lon[i]), 6), round(float(lat[i]), 6)]},
                          "properties": {**props0, "n_buildings": len(members), "n_open": n_open,
                                         "has_dwelling": not want_open, "score": round(sc, 3),
                                         "source_url": res["source_url"]}})
    return feats, towns


def map_year(res: dict) -> int:
    """The year the map shows: the survey year from the USGS metadata, else the edition
    year printed on it (aerial photo year, where recorded, is kept as its own property)."""
    if res.get("survey_year"):
        return int(res["survey_year"])
    return int(res["edition_year"])


# ----------------------------------------------------------------------------- export
def export():
    """All processed sheets -> data/manual/farmsteads/*.geojson."""
    from shapely.geometry import Polygon, mapping
    from shapely.ops import unary_union
    sheets = [json.loads(p.read_text()) for p in sorted(MAP_CACHE.glob("*.json"))]
    sheets = [r for r in sheets if r.get("detector_version") == DETECTOR_VERSION
              or (r.get("edition") == "early" and r.get("detector_version") in EARLY_COMPATIBLE)]
    polys = {r["id"]: Polygon(r["neatline"]) for r in sheets}
    feats, towns, cov = [], [], []
    for r in sheets:
        # a 15' sheet of the same period is superseded where 7.5' sheets cover it
        better = [polys[q["id"]] for q in sheets if q["id"] != r["id"] and q.get("edition") == r.get("edition")
                  and q["scale"] < r["scale"] and polys[q["id"]].intersects(polys[r["id"]])]
        drop = unary_union(better) if better else None
        f, tw = farmsteads_of_sheet(r, drop)
        f = [x for x in f if x["properties"]["score"] >= MIN_SCORE]
        feats += f
        towns += tw
        shown = polys[r["id"]].difference(drop) if drop is not None else polys[r["id"]]
        # towns (dense symbols, red urban tint) say nothing about single farmhouses: the
        # sheet doesn't "see" farmsteads there, so they are not part of its coverage
        tpolys = [Polygon(t["geometry"]["coordinates"][0]).buffer(0) for t in tw]
        if tpolys:
            shown = shown.difference(unary_union(tpolys))
        if shown.is_empty:
            continue
        cov.append({"type": "Feature", "geometry": mapping(shown.simplify(1e-6)),
                    "properties": {"quad": r["quad"], "map_year": map_year(r), "edition_year": r["edition_year"],
                                   "survey_year": r.get("survey_year"), "photo_year": r.get("photo_year"),
                                   "scale": r["scale"], "period": r.get("edition"),
                                   "n_symbols": len(r["symbols"]), "n_farmsteads": len(f),
                                   "corner_error_m": r.get("corner_error_m"), "source_url": r["source_url"],
                                   "metadata_url": r.get("metadata_url")}})
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    feats.sort(key=lambda f: (f["properties"]["map_year"], f["properties"]["quad"], f["geometry"]["coordinates"]))

    def dump(name, fs):
        (OUT_DIR / name).write_text(json.dumps({"type": "FeatureCollection", "features": fs}, separators=(",", ":")) + "\n")
    dump("topo_farmsteads.geojson", feats)
    dump("coverage.geojson", cov)
    dump("topo_towns.geojson", towns)
    orch = []
    for r in sheets:
        better = [polys[q["id"]] for q in sheets if q["id"] != r["id"] and q.get("edition") == r.get("edition")
                  and q["scale"] < r["scale"] and polys[q["id"]].intersects(polys[r["id"]])]
        drop = unary_union(better) if better else None
        for o in r.get("orchards", []):
            if len(o["rings"][0]) < 4:
                continue
            pg = Polygon(o["rings"][0], [h for h in o["rings"][1:] if len(h) >= 4]).buffer(0)
            if drop is not None:
                pg = pg.difference(drop)
            if pg.is_empty or pg.area < 1e-6:
                continue
            orch.append({"type": "Feature", "geometry": mapping(pg),
                         "properties": {"kind": o["kind"], "map_year": map_year(r), "edition_year": r["edition_year"],
                                        "photo_year": r.get("photo_year"), "quad": r["quad"], "scale": r["scale"],
                                        "source_url": r["source_url"]}})
    dump("topo_orchards.geojson", orch)
    # the list of sheets in the README
    readme = OUT_DIR / "README.md"
    if readme.exists():
        txt = readme.read_text()
        mark = "<!-- maps-table -->"
        if mark in txt:
            nf = {}
            for f in feats:
                nf[f["properties"]["source_url"]] = nf.get(f["properties"]["source_url"], 0) + 1
            rows = ["| Quadrangle | Scale | Edition | Survey | Photos | Period | Symbols | Farmsteads | Shift to today's roads | GeoPDF |",
                    "|---|---|---|---|---|---|---|---|---|---|"]
            for r in sorted(sheets, key=lambda r: (r.get("edition") or "", r["quad"], r["edition_year"])):
                al = r.get("align") or {}
                sh = (f"{al['median_shift_m']:.0f} m ({al['model']}, RMS {al['rms_m']:.0f} m)" if al.get("aligned")
                      else "not aligned")
                rows.append(f"| {r['quad']} | 1:{r['scale']:,} | {r['edition_year']} | {r.get('survey_year') or ''} | "
                            f"{r.get('photo_year') or ''} | {r.get('edition')} | {len(r['symbols'])} | "
                            f"{nf.get(r['source_url'], 0)} | {sh} | [{r['id']}]({r['source_url']}) |")
            readme.write_text(txt[:txt.index(mark) + len(mark)] + "\n\n" + "\n".join(rows) + "\n")
    log(f"export: {len(feats)} farmsteads from {len(sheets)} sheets, {len(towns)} town areas, "
        f"{len(orch)} orchard / vineyard polygons -> {OUT_DIR}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", nargs="?", default="all", choices=["all", "list", "process", "realign", "export"])
    ap.add_argument("--area", action="append", help=f"farming district(s): {', '.join(AREAS)} (default: all)")
    ap.add_argument("--keep", action="store_true", help="keep the downloaded PDFs")
    ap.add_argument("--debug", type=int, default=0, help="overlay crops per sheet in data/interim/topo/debug")
    ap.add_argument("--only", help="comma-separated sheet ids")
    ap.add_argument("--shard", help="i/n: process every n-th sheet starting at i (parallel runs)")
    a = ap.parse_args()
    areas = a.area or list(AREAS)
    if a.cmd in ("all", "list", "process"):
        maps = select_maps(areas)
        if a.only:
            maps = [m for m in maps if m["id"] in a.only.split(",")]
        if a.shard:
            i, n = map(int, a.shard.split("/"))
            maps = maps[i::n]
        for m in maps:
            done = sheet_path(m).exists()
            log(f"{m['id']} {m['edition']:5s} {m['quad']} 1:{m['scale']} {m['edition_year']} "
                f"(survey {m['meta'].get('survey_year')}){' [done]' if done else ''}")
        if a.cmd == "list":
            return
        for k, m in enumerate(maps):
            try:
                res = process_sheet(m, keep_raw=a.keep, debug_crops=a.debug)
                log(f"[{k + 1}/{len(maps)}] {m['quad']} {m['edition_year']}: {len(res['symbols'])} symbols "
                    f"(corner error {res.get('corner_error_m')} m)")
            except Exception as e:          # one bad scan must not stop the batch
                log(f"[{k + 1}/{len(maps)}] {m['quad']} {m['edition_year']} FAILED: {e!r}")
    if a.cmd == "realign":
        # recompute the road alignment and every coordinate from the cached pixel positions
        for pth in sorted(MAP_CACHE.glob("*.json")):
            res = json.loads(pth.read_text())
            georeference(res)
            pth.write_text(json.dumps(res))
            al = res.get("align") or {}
            log(f"{res['quad']} {res['edition_year']}: shift {al.get('median_shift_m')} m, RMS {al.get('rms_m')} m "
                f"({al.get('n_used')}/{al.get('n_windows')} windows){'' if al.get('aligned') else ' not aligned'}")
    if a.cmd in ("all", "export", "realign"):
        export()


if __name__ == "__main__":
    main()
