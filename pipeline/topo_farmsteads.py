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

from common import INTERIM, MANUAL, RAW, download_file, get_with_retry, log, session

TOPO_RAW = RAW / "topo"
API_CACHE = TOPO_RAW / "api"
META_CACHE = TOPO_RAW / "meta"
PROJ_DIR = RAW / "proj"
TOPO_INTERIM = INTERIM / "topo"
MAP_CACHE = TOPO_INTERIM / "maps"
DEBUG_DIR = TOPO_INTERIM / "debug"
OUT_DIR = MANUAL / "farmsteads"

TNM_API = "https://tnmaccess.nationalmap.gov/api/v1/products"
DETECTOR_VERSION = 1

# Farming districts of the five modelled counties (W, S, E, N in degrees). Quads are
# selected when their footprint overlaps one of these boxes.
AREAS = {
    "santa_clara_valley": (-122.10, 36.95, -121.55, 37.50),   # Palo Alto / Milpitas .. Morgan Hill
    "south_valley": (-121.75, 36.90, -121.45, 37.15),         # Morgan Hill .. Gilroy
    "peninsula_coast": (-122.52, 37.30, -122.30, 37.55),      # Half Moon Bay, Pescadero side
    "peninsula_baylands": (-122.30, 37.40, -122.05, 37.55),   # Redwood City .. Mountain View
    "tri_valley": (-122.00, 37.55, -121.55, 37.80),           # Livermore, Pleasanton, Sunol, Dublin
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
        if desc in ("survey year", "date on map", "edit year", "photo year", "print year",
                    "photo inspection year", "field check year", "aerial photo year"):
            if re.fullmatch(r"\d{4}", date):
                out[desc.replace(" ", "_")] = int(date)
    sup = root.findtext(".//supplinf") or ""
    q = re.search(r"Scan Quality:\s*([^;]+)", sup)
    w = re.search(r"Woodland Tint:\s*([YN])", sup)
    out["scan_quality"] = q.group(1).strip() if q else None
    out["woodland_tint"] = (w.group(1) == "Y") if w else None
    return out


def select_maps(area_names) -> list[dict]:
    """Per quadrangle: the earliest 15' edition in EARLY and one edition in LATE
    (1:24,000 preferred, else 1:62,500). Of duplicate scans of the same edition the one
    with the better scan quality / larger file wins."""
    cand = {}
    for name in area_names:
        for it in query_tnm(AREAS[name]):
            m = parse_item(it)
            if m and m["scale"] in (24000, 62500, 31680, 48000):
                cand[m["id"]] = m
    by_quad = {}
    for m in cand.values():
        by_quad.setdefault((m["quad"], tuple(round(v, 3) for v in m["bbox"])), []).append(m)
    chosen = []
    for (quad, _), ms in sorted(by_quad.items()):
        early = [m for m in ms if m["scale"] in (62500, 48000) and EARLY[0] <= m["edition_year"] <= EARLY[1]]
        late = [m for m in ms if LATE[0] <= m["edition_year"] <= LATE[1]]
        for group, kind in ((early, "early"), (late, "late")):
            if not group:
                continue
            if kind == "early":
                y0 = min(m["edition_year"] for m in group)
                group = [m for m in group if m["edition_year"] == y0]
            else:
                s24 = [m for m in group if m["scale"] == 24000]
                group = s24 or group
                y0 = min(m["edition_year"] for m in group)
                group = [m for m in group if m["edition_year"] == y0]
            for m in group:
                m["meta"] = fetch_meta(m)
            good = lambda m: (m["meta"].get("scan_quality") or "").lower().startswith("optimal")
            best = sorted(group, key=lambda m: (not good(m), -m["size"]))[0]
            best["edition"] = kind
            chosen.append(best)
    return chosen


# ----------------------------------------------------------------------------- GeoPDF
def _num_list(obj: str, key: str):
    m = re.search(r"/" + key + r"\s*\[(.*?)\]", obj, re.S)
    return [float(v) for v in re.findall(r"\(([-0-9.eE+]+)\)", m.group(1))] if m else None


def read_geopdf(pdf_path: Path):
    """Full-resolution scan (H, W, 3 uint8) assembled from the PDF's image tiles, and its
    registration: pixel (col, row) -> projected metres, neat line in pixels, projection."""
    import pymupdf
    doc = pymupdf.open(pdf_path)
    page = doc[0]
    obj = doc.xref_object(page.xref)
    ctm = _num_list(obj, "CTM")
    neat = _num_list(obj, "Neatline")
    proj = {}
    pm = re.search(r"/Projection\s*<<(.*?)>>", obj, re.S)
    if pm:
        for k, v in re.findall(r"/(\w+)\s*\(([^)]*)\)", pm.group(1)):
            proj[k] = v
        t = re.search(r"/ProjectionType\s*\(([^)]*)\)", pm.group(1))
        proj["ProjectionType"] = t.group(1) if t else proj.get("ProjectionType")
    if not ctm or not neat:
        raise ValueError(f"{pdf_path.name}: no LGIDict registration")
    info = page.get_image_info(xrefs=True)
    big = max(info, key=lambda i: i["width"])
    s = big["width"] / (big["bbox"][2] - big["bbox"][0])        # pixels per PDF point
    W = int(round(page.rect.width * s))
    H = int(round(page.rect.height * s))
    img = np.full((H, W, 3), 255, np.uint8)
    for i in info:
        if i["xref"] <= 0:
            continue
        pix = pymupdf.Pixmap(doc, i["xref"])
        if pix.n - pix.alpha < 3:
            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
        a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3]
        x0 = int(round(i["bbox"][0] * s))
        y0 = int(round(i["bbox"][1] * s))
        h = min(a.shape[0], H - y0)
        w = min(a.shape[1], W - x0)
        if h > 0 and w > 0:
            img[y0:y0 + h, x0:x0 + w] = a[:h, :w]
    page_h = page.rect.height
    a, b, c, d, e, f = ctm

    def px_to_proj(col, row):
        x = np.asarray(col, float) / s
        y = page_h - np.asarray(row, float) / s           # PDF user space is bottom-up
        return a * x + c * y + e, b * x + d * y + f

    nl = np.array(neat).reshape(-1, 2)
    neat_px = np.column_stack([nl[:, 0] * s, (page_h - nl[:, 1]) * s])
    px_per_mm = s * 72 / 25.4
    return img, {"px_to_proj": px_to_proj, "neat_px": neat_px, "proj": proj,
                 "px_per_mm": px_per_mm, "m_per_px": abs(a) / s}


def crs_for(proj: dict):
    """pyproj CRS of a GeoPDF's projected coordinates (NAD27 maps)."""
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


def detect_symbols(img, g, debug=None):
    """Building symbols on one sheet -> (kept symbols, stats). Each symbol: pixel centroid,
    area (mm² on paper), shape / context features, rejection reasons, score 0..1."""
    import cv2
    from scipy.spatial import cKDTree
    ppm = g["px_per_mm"]
    H, W, _ = img.shape
    # inside the neat line (minus 1 mm: the neat line itself and its ticks)
    inside = np.zeros((H, W), np.uint8)
    cv2.fillPoly(inside, [np.round(g["neat_px"]).astype(np.int32)], 1)
    inside = cv2.erode(inside, cv2.getStructuringElement(cv2.MORPH_RECT, (int(ppm * 2) | 1,) * 2))
    mx = np.empty((H, W), np.uint8)
    mn = np.empty((H, W), np.uint8)
    hue_ok = np.empty((H, W), bool)          # black / grey ink: not red-brown, not blue-green
    water = np.empty((H, W), bool)           # blue water lines / tint
    for r in range(0, H, 2048):
        blk = img[r:r + 2048].astype(np.int16)
        mx[r:r + 2048] = blk.max(2)
        mn[r:r + 2048] = blk.min(2)
        R, G, B = blk[:, :, 0], blk[:, :, 1], blk[:, :, 2]
        hue_ok[r:r + 2048] = (R - G < 40) & (B - R < 15) & (G - R < 15)
        water[r:r + 2048] = (B - R > 20) & (B > G - 10)
    hue_ok &= inside > 0
    paper = float(np.percentile(mx[inside > 0][::97], 75))
    ink_t = 0.55 * paper
    ink = ((mx < ink_t) & hue_ok).astype(np.uint8)
    d_open = max(3, int(round(0.26 * ppm)) | 1)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d_open, d_open))
    core = cv2.morphologyEx(ink, cv2.MORPH_OPEN, k)
    n, lab, st, cen = cv2.connectedComponentsWithStats(core, connectivity=8)
    area_mm2 = st[:, 4] / ppm ** 2
    disc_mm2 = k.sum() / ppm ** 2
    a_min = _valley_threshold(area_mm2[1:], lo=max(0.05, 1.35 * disc_mm2), hi=max(0.13, 2.6 * disc_mm2))
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
        dark = float(np.median(mn[y:y + h, x:x + w][sub > 0]))
        recs.append({"i": i, "x": cx, "y": cy, "area_mm2": float(area_mm2[i]), "elong": elong,
                     "solidity": float(solidity), "rect_fill": float(rect_fill), "dark": dark,
                     "w": int(w), "h": int(h), "theta": theta})
    sym_ok = np.zeros(n, bool)
    for r in recs:
        r["shape_ok"] = (r["area_mm2"] >= a_min and r["elong"] <= 2.6 and r["solidity"] >= 0.82
                         and r["rect_fill"] >= 0.62)
        sym_ok[r["i"]] = r["shape_ok"]
    # --- context in a window around each candidate. Light ink (hairlines of lettering,
    # soft edges) connects a blob to the rest of its glyph; components are only followed
    # inside the window, so roads and rails leaving it are "lines", not glyphs.
    R = int(round(2.0 * ppm))
    small_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    min_letter = 0.2 * ppm
    ann_in, ann_out = 0.45 * ppm, 1.2 * ppm
    thick_t = max(2.5, 0.13 * ppm)
    # big lettering: thick (>= 0.34 mm) ink masses that are not symbols (stems, bowls of
    # large serif capitals); their hairlines are often too faint to connect the serifs
    dtc = cv2.distanceTransform(core, cv2.DIST_L2, 3)
    from scipy import ndimage
    dmax = ndimage.maximum(dtc, lab, np.arange(n))
    del dtc
    glyph_mass = np.zeros(n, bool)
    shp = {r["i"]: r for r in recs}
    for i in range(1, n):
        if area_mm2[i] < 0.2 or dmax[i] < 0.17 * ppm:
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
    for r in recs:
        cx, cy = int(round(r["x"])), int(round(r["y"]))
        y0, y1, x0, x1 = max(cy - R, 0), min(cy + R + 1, H), max(cx - R, 0), min(cx + R + 1, W)
        ccx, ccy = r["x"] - x0, r["y"] - y0
        mxw = mx[y0:y1, x0:x1]
        lp = max(float(np.percentile(mxw, 80)), 0.8 * paper)
        inkw = ink[y0:y1, x0:x1]
        lightw = ((mxw < 0.80 * lp) & hue_ok[y0:y1, x0:x1]).astype(np.uint8) | inkw
        labw = lab[y0:y1, x0:x1]
        own = labw == r["i"]
        symw = cv2.dilate((sym_ok[labw] | own).astype(np.uint8), small_k) > 0
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
        # on a line: the blob's own dark component runs straight through its centre (rails)
        on_line = False
        od = int(np.bincount(dl[own]).argmax())
        if od > 0 and leaving[od]:
            ys_, xs_ = np.nonzero((dl == od) & ~symw)
            if len(xs_) > 20:
                dx, dy = xs_ - ccx, ys_ - ccy
                rr = np.hypot(dx, dy)
                sel = (rr > ann_in) & (rr < ann_out)
                if sel.sum() > 20:
                    P = np.column_stack([dx[sel], dy[sel]])
                    cov = P.T @ P / len(P)
                    wv, vv = np.linalg.eigh(cov)
                    u = vv[:, 1]
                    along = P @ u
                    perp = np.abs(P @ np.array([-u[1], u[0]]))
                    if (np.median(perp) < 0.12 * ppm and (along > 0).mean() > 0.25 and (along < 0).mean() > 0.25):
                        on_line = True
        # holes (letter counters) near the blob, for glyphs not attached to lines
        holes = 0
        if not touches:
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
            letters += 1
        wr = int(round(0.6 * ppm))
        wwin = water[max(cy - wr, 0):cy + wr + 1, max(cx - wr, 0):cx + wr + 1]
        big_text = False
        if gm_tree is not None:
            dgm, _ = gm_tree.query([r["x"], r["y"]], distance_upper_bound=1.5 * ppm)
            big_text = bool(np.isfinite(dgm))
        r.update({"touches": bool(touches), "resid_dark_mm2": resid_dark / ppm ** 2,
                  "resid_thick_mm2": resid_thick / ppm ** 2, "big_text": big_text,
                  "on_line": on_line, "holes": holes, "letters_near": letters,
                  "water": float(wwin.mean()), "own_px": int(own.sum())})
    # --- dash-dot boundaries: a candidate on the extension of a long dash
    D = np.array(dashes) if dashes else None
    dtree = cKDTree(D[:, :2]) if dashes else None
    a_typ = float(np.median([r["area_mm2"] for r in recs if r["shape_ok"]] or [0.15]))
    keep = []
    for r in recs:
        reasons = []
        if r["area_mm2"] < a_min:
            reasons.append("small")
        if r["elong"] > 2.6:
            reasons.append("elongated")
        if r["solidity"] < 0.82 or r["rect_fill"] < 0.62:
            reasons.append("shape")
        if r["resid_thick_mm2"] > 0.02:
            reasons.append("glyph")           # letter stems hang on it: part of a word
        if r["big_text"]:
            reasons.append("bigtext")         # next to the strokes of large lettering
        if r["on_line"]:
            reasons.append("online")          # knot on a rail / heavy line
        if r["holes"] >= 1:
            reasons.append("counter")         # a letter with a counter (a, e, o, R …)
        if r["letters_near"] >= 2:
            reasons.append("text")
        if r["water"] > 0.06:
            reasons.append("water")
        on_dash = False
        if dtree is not None:
            for q in dtree.query_ball_point([r["x"], r["y"]], 4.5 * ppm):
                qx, qy, ux, uy, half = D[q]
                vx, vy = r["x"] - qx, r["y"] - qy
                along = vx * ux + vy * uy
                across = abs(-vx * uy + vy * ux)
                if half < abs(along) < half + 3.5 * ppm and across < 0.18 * ppm:
                    on_dash = True
                    break
        if on_dash:
            reasons.append("dashline")
        if r["dark"] > 0.45 * paper:
            reasons.append("faint")
        r["reject"] = reasons
        s_area = math.exp(-abs(math.log(r["area_mm2"] / a_typ)) / 0.8)
        s_shape = max(0.0, min(1.0, (2.6 - r["elong"]) / 1.2)) * max(0.0, min(1.0, (r["solidity"] - 0.78) / 0.12)) \
            * max(0.0, min(1.0, (r["rect_fill"] - 0.58) / 0.15))
        s_dark = min(1.0, max(0.0, (0.45 * paper - r["dark"]) / (0.25 * paper)))
        s_ctx = 1.0 - 0.25 * min(r["letters_near"], 1)
        r["score"] = float(max(0.0, min(1.0, 0.3 * s_area + 0.4 * s_shape + 0.2 * s_dark + 0.1)) * s_ctx)
        if not reasons:
            keep.append(r)
    stats = {"paper": paper, "ink_t": ink_t, "a_min_mm2": a_min, "a_typ_mm2": a_typ,
             "n_cores": int(n - 1), "n_candidates": len(recs), "n_kept": len(keep), "n_dashes": len(dashes)}
    if debug is not None:
        debug["all"] = recs
    return keep, stats
