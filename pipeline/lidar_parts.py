"""Stage: per-building massing (stepped parts) from airborne LiDAR.

Every footprint in sf_buildings is one prism at one height, so a 16-storey tower on a
6-storey courtyard podium reads as a flat slab. Where OSM mappers drew building:parts
we already use them (sf_buildings.apply_parts); everywhere else this stage cuts the
footprint into parts from a 1 m LiDAR surface model:

  1. DSM / DTM: USGS 3DEP point cloud as Entwine Point Tiles (EPT, public AWS bucket
     usgs-lidar-public). Nodes down to depth 8 (~0.5 m voxels, ~5 pts/m2 on roofs) are
     streamed, decoded (laspy + lazrs) and binned on a 1 m UTM 10N grid, nothing is kept
     on disk but the rasters:
        dsm   max z of all returns (noise classes 7/18 dropped)
        dsml  max z of last / single returns (tree canopy suppressed, roofs unchanged)
        dtm   max z of ground / water / ignored-ground points, gaps under buildings
              filled by inverse-distance interpolation
        veg   % of points that are non-last returns (canopy marker)
     -> data/interim/lidar/<job>/{dsm,dsml,dtm,veg}.tif   (int16 decimetres / uint8 %)
  2. Parts: inside each footprint (1 m inset for the statistics) roof pixels are joined
     into plateaus where neighbouring pixels differ by < 2 m (pitched roofs stay one
     surface, a storey step cuts), plateaus closer than 3 m in median roof elevation or
     smaller than 40 m2 are merged into their neighbour, plateaus less than 2 m above the
     local ground (courtyards, light courts open to the sky) become holes. Footprints
     with two or more plateaus (or a courtyard) are polygonised from the 1 m label raster
     (coverage-simplified ~1 m so shared edges stay shared) and clipped to the footprint.
     Heights: median roof elevation of the plateau minus the footprint's ground (mean
     DTM along its outline -- the same reference sf_export uses for the roof).
     Footprints newer than the survey, demolished before it, or OSM parts are skipped.
     -> data/interim/<job>_lidar_parts.parquet (EPSG:4326; key, part_index, height_m,
        roof_m, ground_m, area_m2, lidar_year, lidar_project, geometry)
        data/interim/<job>_lidar_heights.parquet (one row per footprint: whole-footprint
        LiDAR median height, plateau count, status)
        data/interim/reports/<job>_lidar_parts.md (+ preview PNGs)

Usage (from pipeline/):
  python lidar_parts.py sf [--bbox lon0,lat0,lon1,lat1] [--workers 3]
      San Francisco: project CA_SanFrancisco_1_B23 (NV5 for USGS, flown 2023-04-20, NPS
      0.15 m). --bbox restricts to a test area (separate job "sf_<hash>").
  python lidar_parts.py region --bbox lon0,lat0,lon1,lat1 --name oakland [--project NAME]
      any other area: picks the most recent EPT project covering the bbox (or --project);
      footprints = Overture region buildings (download_region.py) inside the bbox.
  python lidar_parts.py preview --job sf --bbox lon0,lat0,lon1,lat1 --out file.png
      top-down height map of the DSM with footprints and parts (validation).

Idempotent: EPT hierarchy pages and project metadata are cached in data/raw/lidar/,
the rasters are built once per job (resumable: finished work units are logged), the
parts are recomputed when missing. Delete data/interim/lidar/<job>/ to rebuild.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import get_context
from pathlib import Path

import numpy as np

from common import INTERIM, RAW, get_with_retry, log, session

EPT_ROOT = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public"
BOUNDARIES_URL = "https://raw.githubusercontent.com/hobuinc/usgs-lidar/master/boundaries/resources.geojson"
LIDAR_RAW = RAW / "lidar"
LIDAR_INT = INTERIM / "lidar"
REPORTS = INTERIM / "reports"
UTM = "EPSG:32610"

SF_PROJECT = "CA_SanFrancisco_1_B23"
# collection dates from the project metadata (vendor XML / ScienceBase "Start/End")
PROJECT_DATES = {
    "CA_SanFrancisco_1_B23": 2023.30,      # 2023-04-20
}

MAX_DEPTH = 8          # EPT depth: ~0.5 m voxels in SF (cube 21.1 km / 128 / 2^8 = 0.64 m mercator)
RES = 1.0              # raster cell (m, UTM)
NODATA = -32768        # int16 decimetres
NOISE_CLASSES = (7, 18)
GROUND_CLASSES = (2, 9, 20)

# segmentation parameters (metres / m2)
EDGE_STEP = 2.0        # neighbouring roof pixels further apart than this belong to different plateaus
MIN_STEP = 3.0         # plateaus closer than this (median roof elevation) are one part
MIN_PART = 40.0        # smallest part / courtyard
OPEN_HAG = 2.0         # plateau less than this above ground = open to the sky (courtyard)
VEG_FRAC = 40          # % non-last returns -> canopy pixel, ignored
INSET = 1.0            # footprint inset for the statistics
SIMPLIFY = 1.5         # coverage simplification of the 1 m staircase (VW, sqrt of area)


# ----------------------------------------------------------------------------- EPT
class Ept:
    """Entwine Point Tile dataset on the public USGS bucket (metadata cached on disk)."""

    def __init__(self, name: str):
        self.name = name
        self.url = f"{EPT_ROOT}/{name}"
        self.cache = LIDAR_RAW / name
        (self.cache / "ept-hierarchy").mkdir(parents=True, exist_ok=True)
        self.meta = self._json("ept.json")
        b = self.meta["bounds"]
        self.cube = np.array(b, float)  # minx, miny, minz, maxx, maxy, maxz (EPSG:3857)
        self.srs = self.meta["srs"].get("horizontal")
        assert self.srs == "3857", f"{name}: unexpected EPT srs {self.meta['srs']}"

    def _json(self, rel: str):
        p = self.cache / rel
        if not p.exists():
            r = get_with_retry(session(), f"{self.url}/{rel}")
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_name(p.name + f".{os.getpid()}.{id(r)}.tmp")
            tmp.write_bytes(r.content)
            os.replace(tmp, p)
        return json.loads(p.read_text())

    def node_bounds(self, key: str):
        d, x, y, z = map(int, key.split("-"))
        s = (self.cube[3] - self.cube[0]) / 2 ** d
        return (self.cube[0] + x * s, self.cube[1] + y * s, self.cube[0] + (x + 1) * s, self.cube[1] + (y + 1) * s)

    def nodes(self, max_depth: int, keep) -> dict[str, int]:
        """All nodes (key -> point count) with depth <= max_depth whose 2D bounds pass `keep`
        (hierarchy pages fetched 16 at a time and cached)."""
        out: dict[str, int] = {}
        todo = ["0-0-0-0"]
        with ThreadPoolExecutor(16) as ex:
            while todo:
                pages = list(ex.map(lambda k: self._json(f"ept-hierarchy/{k}.json"), todo))
                todo = []
                for page in pages:
                    for k, v in page.items():
                        d = int(k.split("-")[0])
                        if d > max_depth or not keep(self.node_bounds(k), d):
                            continue
                        if v == -1:
                            todo.append(k)
                        elif v > 0:
                            out[k] = v
        return out


def project_year(name: str) -> float:
    if name in PROJECT_DATES:
        return PROJECT_DATES[name]
    m = re.search(r"_B(\d\d)$", name)
    if m:
        return 2000 + int(m.group(1))
    m = re.search(r"(19|20)\d\d", name)
    return float(m.group(0)) if m else float("nan")


def pick_projects(bbox_ll) -> list[str]:
    """EPT projects for a bbox: the newest survey year whose projects together cover >= 95 % of
    it (neighbouring work units of one survey are merged), else the best-covering recent one."""
    from shapely import union_all
    from shapely.geometry import box, shape
    p = LIDAR_RAW / "resources.geojson"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(get_with_retry(session(), BOUNDARIES_URL).content)
    b = box(*bbox_ll)
    by_year: dict[float, list] = {}
    for f in json.loads(p.read_text())["features"]:
        g = shape(f["geometry"])
        if g.intersects(b):
            name = f["properties"]["name"]
            by_year.setdefault(project_year(name), []).append((g.intersection(b).area / b.area, name, g))
    if not by_year:
        raise SystemExit(f"no 3DEP EPT project covers {bbox_ll}")
    best = None
    for year in sorted(by_year, reverse=True):
        ps = sorted(by_year[year], reverse=True)
        cov = union_all([q[2] for q in ps]).intersection(b).area / b.area
        log(f"  {year:.0f}: {', '.join(q[1] for q in ps)} -> coverage {cov:.0%}")
        if cov >= 0.95:
            return [q[1] for q in ps if q[0] > 0.001]
        if best is None or cov > best[0] + 0.1:
            best = (cov, [q[1] for q in ps])
    return best[1]


# ----------------------------------------------------------------------------- grid
class Grid:
    def __init__(self, x0, y0, x1, y1, res=RES):
        self.res = res
        self.x0 = np.floor(x0 / res) * res
        self.y1 = np.ceil(y1 / res) * res
        self.w = int(np.ceil((x1 - self.x0) / res))
        self.h = int(np.ceil((self.y1 - y0) / res))

    @property
    def transform(self):
        from affine import Affine
        return Affine(self.res, 0, self.x0, 0, -self.res, self.y1)

    def to_json(self):
        return {"x0": self.x0, "y1": self.y1, "w": self.w, "h": self.h, "res": self.res}

    @classmethod
    def from_json(cls, d):
        g = cls.__new__(cls)
        g.x0, g.y1, g.w, g.h, g.res = d["x0"], d["y1"], d["w"], d["h"], d["res"]
        return g


LAYERS = {"dsm": np.int16, "dsml": np.int16, "gnd": np.int16, "cnt": np.uint16, "cmr": np.uint16}


# worker state (one per process)
_W = {}


def _worker_init(grid_json):
    import pyproj
    _W["grid"] = Grid.from_json(grid_json)
    _W["tr"] = pyproj.Transformer.from_crs("EPSG:3857", UTM, always_xy=True)
    _W["s"] = session()
    import requests
    _W["s"].mount("https://", requests.adapters.HTTPAdapter(pool_maxsize=16))
    _W["pool"] = ThreadPoolExecutor(8)


def _fetch(url):
    s = _W["s"]
    for attempt in range(6):
        try:
            r = s.get(url, timeout=120)
            if r.status_code == 200:
                return url, r.content
            if r.status_code == 404:
                return url, None
        except Exception as e:  # noqa: BLE001 - network hiccup, retry
            err = e
        time.sleep(1.5 * 2 ** attempt)
    raise RuntimeError(f"failed to fetch {url}")


def _bin_unit(unit):
    """Download + decode the nodes of one work unit, bin on the grid, reduce per cell."""
    import laspy
    uid, url, keys, bounds = unit
    g = _W["grid"]
    tr = _W["tr"]
    sel = laspy.DecompressionSelection.base()
    parts = []
    # local affine 3857 -> UTM for small units (exact to ~1 cm over 300 m), exact transform otherwise
    affine = None
    if bounds is not None and bounds[2] - bounds[0] < 1500:
        xs = np.linspace(bounds[0], bounds[2], 3)
        ys = np.linspace(bounds[1], bounds[3], 3)
        X, Y = np.meshgrid(xs, ys)
        u, v = tr.transform(X.ravel(), Y.ravel())
        A = np.c_[X.ravel(), Y.ravel(), np.ones(X.size)]
        cu, *_ = np.linalg.lstsq(A, u, rcond=None)
        cv, *_ = np.linalg.lstsq(A, v, rcond=None)
        affine = (cu, cv)
    for _, data in _W["pool"].map(_fetch, [f"{url}/ept-data/{k}.laz" for k in keys]):
        if data is None:
            continue
        las = laspy.read(io.BytesIO(data), decompression_selection=sel)
        cls = np.asarray(las.classification)
        ok = ~np.isin(cls, NOISE_CLASSES)
        try:
            ok &= ~np.asarray(las.withheld, bool)
        except Exception:  # noqa: BLE001 - no withheld flag in this point format
            pass
        x = np.asarray(las.x)[ok]
        y = np.asarray(las.y)[ok]
        z = np.asarray(las.z)[ok]
        rn = np.asarray(las.return_number)[ok].astype(np.int16)
        nr = np.asarray(las.number_of_returns)[ok].astype(np.int16)
        cls = cls[ok]
        if affine is not None:
            cu, cv = affine
            u = cu[0] * x + cu[1] * y + cu[2]
            v = cv[0] * x + cv[1] * y + cv[2]
        else:
            u, v = tr.transform(x, y)
        c = np.floor((u - g.x0) / g.res).astype(np.int64)
        r = np.floor((g.y1 - v) / g.res).astype(np.int64)
        inside = (c >= 0) & (c < g.w) & (r >= 0) & (r < g.h)
        if not inside.any():
            continue
        zz = np.clip(np.rint(z[inside] * 10), -32000, 32000).astype(np.int16)
        last = (rn >= nr)[inside]
        gnd = np.isin(cls[inside], GROUND_CLASSES)
        parts.append((r[inside] * g.w + c[inside], zz, last, gnd))
    if not parts:
        return uid, None
    idx = np.concatenate([p[0] for p in parts])
    zz = np.concatenate([p[1] for p in parts])
    last = np.concatenate([p[2] for p in parts])
    gnd = np.concatenate([p[3] for p in parts])
    o = np.argsort(idx, kind="stable")
    idx, zz, last, gnd = idx[o], zz[o], last[o], gnd[o]
    starts = np.flatnonzero(np.r_[True, idx[1:] != idx[:-1]])
    uidx = idx[starts]
    dsm = np.maximum.reduceat(zz, starts)
    dsml = np.maximum.reduceat(np.where(last, zz, NODATA).astype(np.int16), starts)
    gz = np.maximum.reduceat(np.where(gnd, zz, NODATA).astype(np.int16), starts)
    cnt = np.add.reduceat(np.ones(len(idx), np.int32), starts)
    cmr = np.add.reduceat((~last).astype(np.int32), starts)
    return uid, (uidx, dsm, dsml, gz, cnt, cmr)


def build_rasters(job: str, projects: list[str], grid: Grid, interest=None, workers: int = 3,
                  max_depth: int = MAX_DEPTH):
    """Stream the EPT nodes over the grid into 1 m rasters (data/interim/lidar/<job>/)."""
    import pyproj
    from shapely import box as sbox
    out = LIDAR_INT / job
    if (out / "dtm.tif").exists():
        log(f"lidar: rasters for {job} exist ({out})")
        return out
    out.mkdir(parents=True, exist_ok=True)
    meta = {"job": job, "project": "+".join(projects), "lidar_year": min(project_year(p) for p in projects),
            "grid": grid.to_json(), "max_depth": max_depth, "crs": UTM}
    (out / "meta.json").write_text(json.dumps(meta, indent=1))

    # grid bbox in EPSG:3857 (+ margin) for node selection
    inv = pyproj.Transformer.from_crs(UTM, "EPSG:3857", always_xy=True)
    gx = np.array([grid.x0, grid.x0 + grid.w * grid.res])
    gy = np.array([grid.y1 - grid.h * grid.res, grid.y1])
    X, Y = np.meshgrid(np.linspace(gx[0], gx[1], 9), np.linspace(gy[0], gy[1], 9))
    mx, my = inv.transform(X.ravel(), Y.ravel())
    mb = (mx.min() - 20, my.min() - 20, mx.max() + 20, my.max() + 20)

    def keep(b, d):
        if b[2] < mb[0] or b[0] > mb[2] or b[3] < mb[1] or b[1] > mb[3]:
            return False
        if interest is not None and d >= 6:
            return len(interest.query(sbox(*b))) > 0
        return True

    ulist = []
    for project in projects:
        ept = Ept(project)
        nodes = ept.nodes(max_depth, keep)
        log(f"lidar: {project}: {len(nodes)} EPT nodes (depth <= {max_depth}), {sum(nodes.values()) / 1e6:.0f} M points")
        # work units: one per depth-6 column (~260 m in SF); coarser nodes in batches
        units: dict[str, list[str]] = {}
        for k in nodes:
            d, x, y, z = map(int, k.split("-"))
            uid = f"6-{x >> (d - 6)}-{y >> (d - 6)}" if d >= 6 else f"top-{d}-{(x * 7 + y) % 8}"
            units.setdefault(uid, []).append(k)
        for uid, keys in sorted(units.items()):
            b = None
            if uid.startswith("6-"):
                _, x, y = map(int, uid.split("-"))
                s = (ept.cube[3] - ept.cube[0]) / 64
                b = (ept.cube[0] + x * s, ept.cube[1] + y * s, ept.cube[0] + (x + 1) * s, ept.cube[1] + (y + 1) * s)
            ulist.append((uid if len(projects) == 1 else f"{project}:{uid}", ept.url, keys, b))

    # accumulators (memory-mapped, resumable)
    acc = out / "acc"
    acc.mkdir(exist_ok=True)
    mm = {}
    for name, dt in LAYERS.items():
        p = acc / f"{name}.mm"
        fresh = not p.exists()
        mm[name] = np.memmap(p, dtype=dt, mode="w+" if fresh else "r+", shape=(grid.h * grid.w,))
        if fresh and name in ("dsm", "dsml", "gnd"):
            mm[name][:] = NODATA
    done_p = acc / "done.txt"
    done = set(done_p.read_text().split()) if done_p.exists() else set()
    todo = [u for u in ulist if u[0] not in done]
    log(f"lidar: {len(ulist)} work units, {len(todo)} to do ({workers} processes x 8 downloads)")
    t0 = time.time()
    pts_done = 0
    with open(done_p, "a") as df, get_context("spawn").Pool(workers, _worker_init, (grid.to_json(),)) as pool:
        for i, (uid, res) in enumerate(pool.imap_unordered(_bin_unit, todo, chunksize=1)):
            if res is not None:
                uidx, dsm, dsml, gz, cnt, cmr = res
                mm["dsm"][uidx] = np.maximum(mm["dsm"][uidx], dsm)
                mm["dsml"][uidx] = np.maximum(mm["dsml"][uidx], dsml)
                mm["gnd"][uidx] = np.maximum(mm["gnd"][uidx], gz)
                mm["cnt"][uidx] = np.minimum(mm["cnt"][uidx].astype(np.int32) + cnt, 65535)
                mm["cmr"][uidx] = np.minimum(mm["cmr"][uidx].astype(np.int32) + cmr, 65535)
                pts_done += int(cnt.sum())
            df.write(uid + "\n")
            if i % 50 == 0:
                df.flush()
                for m in mm.values():
                    m.flush()
                el = time.time() - t0
                log(f"lidar: {i + 1}/{len(todo)} units, {pts_done / 1e6:.0f} M points binned, "
                    f"{el / 60:.1f} min, eta {el / (i + 1) * (len(todo) - i - 1) / 60:.0f} min")
    for m in mm.values():
        m.flush()
    finalize_rasters(out, grid, mm)
    del mm
    import shutil
    shutil.rmtree(acc)
    return out


def finalize_rasters(out: Path, grid: Grid, mm):
    """Accumulators -> tiled GeoTIFFs; the DTM gets its gaps (under buildings) filled."""
    import rasterio
    from rasterio.fill import fillnodata
    from rasterio.windows import Window
    prof = dict(driver="GTiff", width=grid.w, height=grid.h, count=1, crs=UTM, transform=grid.transform,
                tiled=True, blockxsize=512, blockysize=512, compress="deflate", BIGTIFF="IF_SAFER")
    shape2 = (grid.h, grid.w)
    a = {k: v.reshape(shape2) for k, v in mm.items()}
    B = 2048
    with rasterio.open(out / "dsm.tif", "w", dtype="int16", nodata=NODATA, predictor=2, **prof) as f_dsm, \
            rasterio.open(out / "dsml.tif", "w", dtype="int16", nodata=NODATA, predictor=2, **prof) as f_dsml, \
            rasterio.open(out / "veg.tif", "w", dtype="uint8", nodata=255, **prof) as f_veg:
        for r0 in range(0, grid.h, B):
            h = min(B, grid.h - r0)
            win = Window(0, r0, grid.w, h)
            f_dsm.write(np.asarray(a["dsm"][r0:r0 + h]), 1, window=win)
            f_dsml.write(np.asarray(a["dsml"][r0:r0 + h]), 1, window=win)
            cnt = np.asarray(a["cnt"][r0:r0 + h]).astype(np.float32)
            cmr = np.asarray(a["cmr"][r0:r0 + h]).astype(np.float32)
            veg = np.where(cnt > 0, np.rint(100 * cmr / np.maximum(cnt, 1)), 255).astype(np.uint8)
            f_veg.write(veg, 1, window=win)
    # DTM: ground cells, gaps filled by IDW in overlapping blocks
    tmp = out / "dtm.tmp.tif"
    PAD = 384
    with rasterio.open(tmp, "w", dtype="int16", nodata=NODATA, predictor=2, **prof) as f_dtm:
        for r0 in range(0, grid.h, B):
            for c0 in range(0, grid.w, B):
                ra, rb = max(0, r0 - PAD), min(grid.h, r0 + B + PAD)
                ca, cb = max(0, c0 - PAD), min(grid.w, c0 + B + PAD)
                g = np.asarray(a["gnd"][ra:rb, ca:cb]).astype(np.float32)
                valid = g != NODATA
                if valid.sum() < 16:
                    filled = g
                else:
                    filled = fillnodata(g, mask=valid.astype(np.uint8), max_search_distance=PAD, smoothing_iterations=0)
                    filled = np.where(np.isfinite(filled), filled, NODATA)
                sub = filled[r0 - ra:r0 - ra + min(B, grid.h - r0), c0 - ca:c0 - ca + min(B, grid.w - c0)]
                f_dtm.write(np.rint(sub).astype(np.int16), 1,
                            window=Window(c0, r0, sub.shape[1], sub.shape[0]))
    os.replace(tmp, out / "dtm.tif")
    log(f"lidar: rasters written to {out}")


# ----------------------------------------------------------------------------- segmentation
def _components(z, S, step):
    """Label 4-connected pixels of S whose neighbours differ by < step (pitched roofs stay whole)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    idx = np.full(z.shape, -1, np.int64)
    n = int(S.sum())
    idx[S] = np.arange(n)
    ia, ib = [], []
    for sa, sb in (((slice(None), slice(None, -1)), (slice(None), slice(1, None))),
                   ((slice(None, -1), slice(None)), (slice(1, None), slice(None)))):
        m = S[sa] & S[sb] & (np.abs(z[sa] - z[sb]) < step)
        ia.append(idx[sa][m])
        ib.append(idx[sb][m])
    ia = np.concatenate(ia)
    ib = np.concatenate(ib)
    gph = coo_matrix((np.ones(len(ia), np.int8), (ia, ib)), shape=(n, n))
    _, lab = connected_components(gph, directed=False)
    out = np.full(z.shape, -1, np.int64)
    out[S] = lab
    return out


def segment(z, hag, S, px_area=1.0):
    """Plateau labels (>= 0, -1 elsewhere) and {label: (median z, median hag, area px, open)}.
    z: roof elevation (nan = no data / canopy), hag: height above local ground, S: pixels to use.
    1. pixels join where 4-neighbours differ by < EDGE_STEP (a pitched roof is one surface,
       a storey step cuts); 2. plateaus under MIN_PART join the neighbour closest in height,
    smallest first; 3. neighbours closer than MIN_STEP (median roof) merge, closest first."""
    import heapq
    from scipy.ndimage import median_filter
    S = S & np.isfinite(z)
    if not S.any():
        return np.full(z.shape, -1), {}
    # 3x3 median against speckle (rooftop clutter, single noisy returns)
    zz = _fill_nearest(np.where(np.isfinite(z), z, 0.0), np.isfinite(z))
    z = np.where(S, median_filter(zz, size=3), np.nan)
    lab0 = _components(z, S, EDGE_STEP)
    n = int(lab0.max()) + 1
    flat = lab0.ravel()
    sel = np.flatnonzero(flat >= 0)
    order = sel[np.argsort(flat[sel], kind="stable")]
    pix = dict(enumerate(np.split(order, np.cumsum(np.bincount(flat[sel], minlength=n))[:-1])))
    zf, hf = z.ravel(), hag.ravel()
    med = {i: float(np.median(zf[p])) for i, p in pix.items()}
    area = {i: len(p) for i, p in pix.items()}
    nb: dict[int, set] = {i: set() for i in range(n)}
    for a, b in ((lab0[:, :-1], lab0[:, 1:]), (lab0[:-1, :], lab0[1:, :])):
        m = (a >= 0) & (b >= 0) & (a != b)
        for u, v in set(zip(a[m].tolist(), b[m].tolist())):
            nb[u].add(v)
            nb[v].add(u)

    def merge(i, j, exact=True):  # i into j
        pix[j] = np.concatenate([pix[j], pix.pop(i)])
        area[j] += area.pop(i)
        if exact:
            med[j] = float(np.median(zf[pix[j]]))
        med.pop(i)
        for k in nb.pop(i):
            if k != j:
                nb[k].discard(i)
                nb[k].add(j)
                nb[j].add(k)
        nb[j].discard(i)

    min_px = MIN_PART / px_area
    heap = [(area[i], i) for i in pix if area[i] < min_px]
    heapq.heapify(heap)
    dropped = []
    while heap:
        a_i, i = heapq.heappop(heap)
        if i not in pix or area[i] != a_i or len(pix) <= 1:
            continue
        if not nb[i]:
            dropped.append(pix.pop(i))  # isolated speck (surrounded by canopy / no data)
            area.pop(i), med.pop(i), nb.pop(i)
            continue
        j = min(nb[i], key=lambda k: abs(med[k] - med[i]))
        merge(i, j, exact=area[i] > 0.05 * area[j])
        if area[j] < min_px:
            heapq.heappush(heap, (area[j], j))
    hmed = {i: float(np.median(hf[p])) for i, p in pix.items()}
    while len(pix) > 1:
        best = None
        for a in pix:
            for b in nb[a]:
                if a < b:
                    d = abs(med[a] - med[b])
                    if (d < MIN_STEP or (hmed[a] < OPEN_HAG and hmed[b] < OPEN_HAG)) and (best is None or d < best[0]):
                        best = (d, a, b)
        if best is None:
            break
        _, a, b = best
        i, j = (a, b) if area[a] < area[b] else (b, a)
        merge(i, j)
        hmed.pop(i)
        hmed[j] = float(np.median(hf[pix[j]]))
    lab = np.full(z.size, -1, np.int64)
    info = {}
    for k, (i, p) in enumerate(pix.items()):
        lab[p] = k
        info[k] = (med[i], hmed[i], area[i], hmed[i] < OPEN_HAG)
    return lab.reshape(z.shape), info


def _fill_nearest(lab, valid):
    from scipy.ndimage import distance_transform_edt
    if valid.all() or not valid.any():
        return lab
    _, (ri, ci) = distance_transform_edt(~valid, return_indices=True)
    return lab[ri, ci]


def _smooth_labels(lab, sigma=1.2):
    """Majority-like smoothing of a label raster (Gaussian-weighted vote): straightens the 1 m
    staircase and removes 1-2 m protrusions before polygonising."""
    from scipy.ndimage import gaussian_filter
    ids = np.unique(lab)
    if len(ids) < 2:
        return lab
    votes = np.stack([gaussian_filter((lab == i).astype(np.float32), sigma, mode="nearest") for i in ids])
    return ids[np.argmax(votes, axis=0)]


def split_footprint(geom, wt, z, hag, dtm, px_area=1.0):
    """-> (status, whole_roof_z, ground_ref, parts[list of (polygon, roof_z, area)])"""
    import shapely
    from rasterio.features import rasterize, shapes
    from shapely.geometry import shape as sshape

    S = rasterize([(geom, 1)], out_shape=z.shape, transform=wt, dtype=np.uint8).astype(bool)
    inner = geom.buffer(-INSET)
    Si = rasterize([(inner, 1)], out_shape=z.shape, transform=wt, dtype=np.uint8).astype(bool) if not inner.is_empty else S
    if Si.sum() < 4:
        Si = S
    # ground reference: mean DTM along the outline (sf_export puts the roof at mean outline ground + height)
    xy = shapely.get_coordinates(shapely.segmentize(geom.boundary, 1.0))
    cc, rr = (~wt) * (xy[:, 0], xy[:, 1])
    rr = np.clip(np.floor(rr).astype(int), 0, z.shape[0] - 1)
    cc = np.clip(np.floor(cc).astype(int), 0, z.shape[1] - 1)
    gvals = dtm[rr, cc]
    gvals = gvals[np.isfinite(gvals)]
    if len(gvals) == 0:
        return "no_ground", np.nan, np.nan, []
    gref = float(np.mean(gvals))
    zin = z[Si & np.isfinite(z)]
    if len(zin) < max(4, 0.25 * Si.sum()):
        return "no_data", np.nan, gref, []
    whole = float(np.median(zin))
    area = S.sum() * px_area
    hin = hag[Si & np.isfinite(z)]
    open_frac = float((hin < OPEN_HAG).mean())
    if open_frac > 0.6:
        return "mostly_open", whole, gref, []          # building gone / not built yet / mis-registered
    p1, p99 = np.percentile(zin, [1, 99])
    if area < 2 * MIN_PART or (p99 - p1 < MIN_STEP and open_frac * area < MIN_PART):
        return "single", whole, gref, []
    # plateaus on the inset (edge pixels are mixed with walls / eaves), then extended to the footprint
    lab, info = segment(np.where(Si, z, np.nan), hag, Si, px_area)
    if len(info) <= 1:
        return "single", whole, gref, []
    nparts = sum(1 for v in info.values() if not v[3])
    if nparts == 0:
        return "mostly_open", whole, gref, []
    if nparts == 1 and all(v[2] * px_area < MIN_PART for v in info.values() if v[3]):
        return "single", whole, gref, []
    full = _smooth_labels(_fill_nearest(lab, lab >= 0))
    polys = {}
    for g, v in shapes(full.astype(np.int32), transform=wt):
        polys.setdefault(int(v), []).append(sshape(g))
    keys = sorted(polys)
    cover = [shapely.union_all(polys[k]) for k in keys]
    try:
        simp = shapely.coverage_simplify(cover, SIMPLIFY, simplify_boundary=False)
    except Exception:  # noqa: BLE001 - invalid coverage (should not happen); fall back to plain DP
        simp = [c.simplify(SIMPLIFY * 0.7) for c in cover]
    parts = []
    for k, poly in zip(keys, simp):
        if k < 0 or k not in info or info[k][3]:
            continue
        p = shapely.make_valid(poly.intersection(geom))
        p = shapely.union_all([g for g in shapely.get_parts(p) if g.geom_type == "Polygon" and g.area >= 2.0])
        if p.is_empty:
            continue
        parts.append([p, info[k][0], p.area])
    # slivers left by clipping: join the neighbour sharing the longest edge
    parts.sort(key=lambda t: t[2])
    while len(parts) > 1 and parts[0][2] < MIN_PART * 0.5:
        p = parts.pop(0)
        j = max(range(len(parts)), key=lambda i: parts[i][0].buffer(0.3).intersection(p[0]).area)
        parts[j][0] = shapely.make_valid(shapely.union_all([parts[j][0], p[0]]))
        parts[j][2] = parts[j][0].area
        parts.sort(key=lambda t: t[2])
    if len(parts) == 1 and parts[0][2] > 0.9 * geom.area:
        return "single", whole, gref, []
    return "split", whole, gref, [tuple(p) for p in parts]


_S = {}


def _seg_init(job):
    import rasterio
    d = LIDAR_INT / job
    _S["f"] = {k: rasterio.open(d / f"{k}.tif") for k in ("dsm", "dsml", "dtm", "veg")}
    _S["meta"] = json.loads((d / "meta.json").read_text())


def _read(win):
    f = _S["f"]
    dsm = f["dsm"].read(1, window=win, boundless=True, fill_value=NODATA).astype(np.float32)
    dsml = f["dsml"].read(1, window=win, boundless=True, fill_value=NODATA).astype(np.float32)
    dtm = f["dtm"].read(1, window=win, boundless=True, fill_value=NODATA).astype(np.float32)
    veg = f["veg"].read(1, window=win, boundless=True, fill_value=255)
    z = np.where(dsml != NODATA, dsml, dsm)
    z = np.where(z == NODATA, np.nan, z / 10.0)
    dtm = np.where(dtm == NODATA, np.nan, dtm / 10.0)
    canopy = (veg != 255) & (veg >= VEG_FRAC) & (dsm - dsml > 10)  # many split returns, first > last + 1 m
    z = np.where(canopy, np.nan, z)
    return z, dtm


def _seg_chunk(chunk):
    """Process the footprints of one ~500 m tile (raster window read once)."""
    from rasterio.features import rasterize
    from rasterio.windows import Window
    from rasterio.windows import transform as wtransform
    f = _S["f"]["dsm"]
    inv = ~f.transform
    xs = np.array([it[1].bounds for it in chunk])
    c0, r1 = inv * (xs[:, 0].min() - 6, xs[:, 1].min() - 6)
    c1, r0 = inv * (xs[:, 2].max() + 6, xs[:, 3].max() + 6)
    W = Window(int(c0), int(r0), int(c1 - c0) + 2, int(r1 - r0) + 2)
    Z, DTM = _read(W)
    WT = wtransform(W, f.transform)
    hag_all = Z - DTM
    out_parts, out_rows = [], []
    for key, geom, members in chunk:
        b = geom.bounds
        cc0, rr1 = ~WT * (b[0] - 4, b[1] - 4)
        cc1, rr0 = ~WT * (b[2] + 4, b[3] + 4)
        sl = (slice(max(0, int(rr0)), int(rr1) + 2), slice(max(0, int(cc0)), int(cc1) + 2))
        z = Z[sl]
        dtm = DTM[sl]
        wt = wtransform(Window(sl[1].start, sl[0].start, z.shape[1], z.shape[0]), WT)
        try:
            status, whole, gref, parts = split_footprint(geom, wt, z, hag_all[sl], dtm)
        except Exception as e:  # noqa: BLE001 - one bad footprint must not stop the run
            status, whole, gref, parts = f"error:{type(e).__name__}", np.nan, np.nan, []
        extra = None
        if members:  # OSM parts: LiDAR roof per part vs its OSM height
            diffs, areas, hs = [], [], []
            for pkey, pg, ph in members:
                m = rasterize([(pg.buffer(-0.5) if pg.buffer(-0.5).area > 4 else pg, 1)], out_shape=z.shape,
                              transform=wt, dtype=np.uint8).astype(bool) & np.isfinite(z)
                lh = float(np.median(z[m]) - gref) if m.sum() >= 3 and np.isfinite(gref) else np.nan
                out_rows.append((pkey, "osm_part", lh + gref if np.isfinite(lh) else np.nan, gref, 0, key, None))
                if np.isfinite(lh) and np.isfinite(ph):
                    diffs.append(lh - ph)
                    areas.append(pg.area)
                hs.append(round(float(ph), 1) if np.isfinite(ph) else None)
            uniform = len(set(hs)) <= 1
            bad = float(np.sum(np.array(areas)[np.abs(diffs) > 6]) / max(1e-9, np.sum(areas))) if diffs else 1.0
            # LiDAR replaces the OSM parts where they carry no height variation (one height for
            # every part) or disagree with the LiDAR by > 6 m over more than a quarter of the outline
            extra = bool(status == "split" and (uniform or bad > 0.25))
        out_rows.append((key, status, whole, gref, len(parts), None, extra))
        repl = "|".join(m[0] for m in members) if members else key
        for i, (p, rz, a) in enumerate(sorted(parts, key=lambda t: -t[1])):
            out_parts.append((key, i, rz, gref, a, repl, extra, p.wkb))
    return out_rows, out_parts


def load_sf_footprints(bbox_ll=None):
    """sf_buildings footprints (key = sf16_bldgid). Buildings drawn as OSM building:parts are
    grouped back into one outline (key "osmbld:<Overture building id>", members = the part rows
    as (key, UTM polygon, roof height above ground)):
    most of them carry no height per part (one height for every part = a flat slab), so their
    outline is segmented too and each OSM part gets its LiDAR height for comparison."""
    import geopandas as gpd
    import pandas as pd
    import shapely
    from download_overture import RELEASE
    df = gpd.read_parquet(INTERIM / "sf_buildings.parquet",
                          columns=["sf16_bldgid", "source", "start_year", "end_year", "height", "base", "geometry"])
    if bbox_ll is not None:
        df = df.cx[bbox_ll[0]:bbox_ll[2], bbox_ll[1]:bbox_ll[3]]
    df = df[~df.source.str.contains("lidar")].rename(columns={"sf16_bldgid": "key"})
    isp = df.source.str.contains("parts")
    plain = df[~isp].copy()
    plain["members"] = None
    prt = df[isp].copy()
    if len(prt):
        bp = pd.read_parquet(RAW / "overture" / RELEASE / "building_part.parquet", columns=["id", "building_id"])
        prt["bid"] = prt.key.str.replace("part:", "", regex=False).map(bp.set_index("id").building_id)
        prt["bid"] = prt.bid.fillna(prt.key)
        u = prt.to_crs(UTM)
        rows = []
        for bid, g in u.groupby("bid"):
            outline = shapely.make_valid(shapely.union_all(g.geometry.buffer(0.05).values).buffer(-0.05))
            rows.append({"key": f"osmbld:{bid}", "source": "osm_parts_outline", "start_year": g.start_year.min(),
                         "end_year": g.end_year.max(), "height": g.height.max(), "base": 0.0,
                         "members": list(zip(g.key, g.geometry, g.height + g.base)), "geometry": outline})
        grp = gpd.GeoDataFrame(rows, geometry="geometry", crs=UTM).to_crs(df.crs)
        plain = pd.concat([plain, grp], ignore_index=True)
    return gpd.GeoDataFrame(plain, geometry="geometry", crs=df.crs)


def load_region_footprints(bbox_ll):
    import geopandas as gpd
    from download_region import OUT_OVERTURE
    g = gpd.read_parquet(OUT_OVERTURE / "region5_building.parquet", bbox=tuple(bbox_ll))
    g = g.cx[bbox_ll[0]:bbox_ll[2], bbox_ll[1]:bbox_ll[3]]
    return gpd.GeoDataFrame({"key": g["id"].values, "source": "overture", "start_year": np.nan,
                             "end_year": np.nan, "height": np.nan}, geometry=g.geometry.values, crs=g.crs)


def run_parts(job: str, fp, workers: int = 3):
    """Segment every footprint of `fp` (GeoDataFrame, key column) on the job's rasters."""
    import geopandas as gpd
    import pandas as pd
    import shapely
    meta = json.loads((LIDAR_INT / job / "meta.json").read_text())
    year = meta["lidar_year"]
    fp = fp.to_crs(UTM)
    skip = (fp.start_year > year) | (fp.end_year <= year)
    log(f"parts: {len(fp)} footprints, {int(skip.sum())} skipped (built after / gone before the {year:.1f} survey)")
    todo = fp[~skip]
    geoms = [shapely.make_valid(g) for g in todo.geometry.values]
    cx = np.array([g.centroid.x for g in geoms])
    cy = np.array([g.centroid.y for g in geoms])
    tile = (np.floor(cx / 500).astype(np.int64) * 100000 + np.floor(cy / 500).astype(np.int64))
    chunks = []
    keys = todo.key.values
    mem = todo.members.values if "members" in todo else [None] * len(todo)
    items = [(keys[i], geoms[i], [(k, shapely.make_valid(g), h) for k, g, h in mem[i]] if mem[i] else None)
             for i in range(len(todo))]
    for t in np.unique(tile):
        ii = np.flatnonzero(tile == t)
        size = [max(geoms[i].bounds[2] - geoms[i].bounds[0], geoms[i].bounds[3] - geoms[i].bounds[1]) for i in ii]
        rest = [items[i] for i, sz in zip(ii, size) if sz <= 400]
        if rest:
            chunks.append(rest)
        chunks += [[items[i]] for i, sz in zip(ii, size) if sz > 400]
    log(f"parts: {len(todo)} footprints in {len(chunks)} chunks")
    rows, parts = [], []
    t0 = time.time()
    with get_context("spawn").Pool(workers, _seg_init, (job,)) as pool:
        for i, (r, p) in enumerate(pool.imap_unordered(_seg_chunk, chunks)):
            rows += r
            parts += p
            if i % 100 == 0:
                log(f"parts: {i + 1}/{len(chunks)} chunks, {len(rows)} footprints, {len(parts)} parts, "
                    f"{(time.time() - t0) / 60:.1f} min")
    st = pd.DataFrame(rows, columns=["key", "status", "roof_m", "ground_m", "n_parts", "group", "prefer_lidar"])
    st["lidar_height_m"] = (st.roof_m - st.ground_m).round(2)
    sk = pd.DataFrame({"key": fp[skip].key.values, "status": np.where(fp[skip].start_year > year, "newer_than_survey",
                                                                    "gone_before_survey")})
    st = pd.concat([st, sk], ignore_index=True)
    st["lidar_year"] = year
    st["lidar_project"] = meta["project"]
    pdf = pd.DataFrame(parts, columns=["key", "part_index", "roof_m", "ground_m", "area_m2", "replaces", "prefer_lidar",
                                       "wkb"])
    pg = gpd.GeoDataFrame(pdf.drop(columns="wkb"), geometry=shapely.from_wkb(pdf.wkb.values), crs=UTM)
    pg["height_m"] = (pg.roof_m - pg.ground_m).clip(lower=1.0).round(2)
    pg["roof_m"] = pg.roof_m.round(2)
    pg["ground_m"] = pg.ground_m.round(2)
    pg["area_m2"] = pg.area_m2.round(1)
    pg["lidar_year"] = year
    pg["lidar_project"] = meta["project"]
    pg = pg[["key", "part_index", "height_m", "roof_m", "ground_m", "area_m2", "replaces", "prefer_lidar", "lidar_year",
             "lidar_project", "geometry"]]
    return st, pg.to_crs("EPSG:4326")


# ----------------------------------------------------------------------------- preview / report
def preview(job, bbox_ll, out_png, fp=None, parts=None, title=None):
    """Top-down height map (DSM minus DTM) with footprints (white) and LiDAR parts (coloured by height)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pyproj
    import rasterio
    from rasterio.windows import from_bounds
    tr = pyproj.Transformer.from_crs("EPSG:4326", UTM, always_xy=True)
    x0, y0 = tr.transform(bbox_ll[0], bbox_ll[1])
    x1, y1 = tr.transform(bbox_ll[2], bbox_ll[3])
    d = LIDAR_INT / job
    with rasterio.open(d / "dsm.tif") as f, rasterio.open(d / "dtm.tif") as g:
        w = from_bounds(x0, y0, x1, y1, f.transform)
        dsm = f.read(1, window=w, boundless=True, fill_value=NODATA).astype(float)
        dtm = g.read(1, window=w, boundless=True, fill_value=NODATA).astype(float)
    ndsm = np.where((dsm == NODATA) | (dtm == NODATA), np.nan, (dsm - dtm) / 10)
    fig, axs = plt.subplots(1, 2, figsize=(16, 8.4))
    ext = (x0, x1, y0, y1)
    vmax = np.nanpercentile(ndsm, 99.5) if np.isfinite(ndsm).any() else 50
    for ax in axs:
        ax.imshow(ndsm, extent=ext, cmap="magma", vmin=0, vmax=vmax, interpolation="nearest")
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_xticks([])
        ax.set_yticks([])
    axs[0].set_title("LiDAR height above ground (DSM - DTM), footprints")
    if fp is not None and len(fp):
        fp.to_crs(UTM).boundary.plot(ax=axs[0], color="cyan", linewidth=0.6)
    axs[1].set_title("LiDAR parts (colour = part height)")
    if parts is not None and len(parts):
        pp = parts.to_crs(UTM)
        pp.plot(ax=axs[1], column="height_m", cmap="viridis", vmin=0, vmax=vmax, edgecolor="white", linewidth=0.7,
                alpha=0.85)
        for _, r in pp.iterrows():
            if r.geometry.area > 150:
                c = r.geometry.representative_point()
                axs[1].annotate(f"{r.height_m:.0f}", (c.x, c.y), color="white", fontsize=6, ha="center", va="center")
    if fp is not None and len(fp):
        fp.to_crs(UTM).boundary.plot(ax=axs[1], color="cyan", linewidth=0.4)
    sm = plt.cm.ScalarMappable(cmap="magma", norm=plt.Normalize(0, vmax))
    fig.colorbar(sm, ax=axs, fraction=0.02, label="m above ground")
    if title:
        fig.suptitle(title)
    fig.savefig(out_png, dpi=110, bbox_inches="tight")
    plt.close(fig)


EXAMPLES = {  # validation views (lon0, lat0, lon1, lat1)
    "mission_bay_3rd": (-122.3925, 37.7695, -122.3870, 37.7730),      # One Mission Bay / 420 Mission Bay Blvd N
    "transbay_salesforce": (-122.3990, 37.7880, -122.3925, 37.7920),  # Salesforce Tower, Transit Center, 181 Fremont
    "rincon_hill": (-122.3945, 37.7845, -122.3880, 37.7885),
    "financial_district": (-122.4040, 37.7905, -122.3975, 37.7945),
    "painted_ladies": (-122.4345, 37.7752, -122.4315, 37.7770),       # Victorian rows at Alamo Square
    "outer_sunset_row": (-122.4985, 37.7590, -122.4955, 37.7608),     # stucco tract houses
    "russian_hill_slope": (-122.4200, 37.7995, -122.4160, 37.8020),   # hillside buildings
}


def report(job, st, pg, fp, extra_lines=()):
    REPORTS.mkdir(parents=True, exist_ok=True)
    meta = json.loads((LIDAR_INT / job / "meta.json").read_text())
    split = st[st.status == "split"]
    lines = [f"# LiDAR building parts ({job})", "",
             f"* LiDAR: USGS 3DEP `{meta['project']}` (EPT, depth <= {meta['max_depth']}), survey year {meta['lidar_year']}",
             f"* raster grid: {meta['grid']['w']} x {meta['grid']['h']} cells at {meta['grid']['res']} m ({UTM})",
             f"* footprints: {len(st)}; status counts: " +
             ", ".join(f"{k} {v}" for k, v in st.status.value_counts().items()),
             f"* footprints split into parts: **{len(split)}** -> {len(pg)} parts "
             f"(median {split.n_parts.median() if len(split) else 0:.0f}, max {split.n_parts.max() if len(split) else 0:.0f} per footprint)",
             f"* parts area: {pg.to_crs(UTM).area.sum() / 1e6:.2f} km2; split footprints cover "
             f"{fp[fp.key.isin(split.key)].to_crs(UTM).area.sum() / 1e6:.2f} km2", ""]
    if "height" in fp and len(st):
        m = st.merge(fp[["key", "height"]], on="key")
        m = m[np.isfinite(m.lidar_height_m) & np.isfinite(m.height)]
        if len(m):
            dh = m.lidar_height_m - m.height
            lines += [f"* whole-footprint LiDAR median height vs sf_buildings height: median diff {dh.median():.2f} m, "
                      f"|diff| > 5 m for {(dh.abs() > 5).mean():.1%} ({len(m)} footprints)", ""]
    lines += list(extra_lines)
    big = split.copy()
    if len(big):
        big["area"] = big.key.map(fp.set_index("key").to_crs(UTM).area)
        big = big.sort_values("area", ascending=False).head(15)
        lines += ["## Largest split footprints", "", "| key | parts | whole-footprint height (m) |", "|---|---|---|"]
        lines += [f"| {r.key} | {r.n_parts} | {r.lidar_height_m:.1f} |" for r in big.itertuples()]
    (REPORTS / f"{job}_lidar_parts.md").write_text("\n".join(lines) + "\n")
    log(f"report: {REPORTS / f'{job}_lidar_parts.md'}")


def job_grid(fp_ll, margin=60.0):
    b = fp_ll.to_crs(UTM).total_bounds
    return Grid(b[0] - margin, b[1] - margin, b[2] + margin, b[3] + margin)


def interest_tree(fp_ll):
    import shapely
    g = fp_ll.to_crs("EPSG:3857").geometry.envelope.buffer(40).values
    return shapely.STRtree(g)


def run(job, projects, fp, workers, bbox_ll=None, examples=None):
    import pandas as pd
    grid = job_grid(fp)
    log(f"job {job}: {len(fp)} footprints, grid {grid.w} x {grid.h} m, LiDAR {', '.join(projects)}")
    build_rasters(job, projects, grid, interest=interest_tree(fp), workers=workers)
    out_parts = INTERIM / f"{job}_lidar_parts.parquet"
    out_st = INTERIM / f"{job}_lidar_heights.parquet"
    if out_parts.exists() and out_st.exists():
        log(f"parts: {out_parts} exists (delete to recompute)")
        import geopandas as gpd
        st, pg = pd.read_parquet(out_st), gpd.read_parquet(out_parts)
    else:
        st, pg = run_parts(job, fp, workers)
        pg.to_parquet(out_parts)
        st.to_parquet(out_st)
        log(f"parts: wrote {out_parts} ({out_parts.stat().st_size / 1e6:.1f} MB, {len(pg)} parts of "
            f"{(st.status == 'split').sum()} footprints)")
    extra = []
    for name, bb in (examples or {}).items():
        if bbox_ll is not None and not (bb[0] < bbox_ll[2] and bb[2] > bbox_ll[0] and bb[1] < bbox_ll[3] and bb[3] > bbox_ll[1]):
            continue
        png = REPORTS / f"{job}_lidar_{name}.png"
        sub_fp = fp.cx[bb[0]:bb[2], bb[1]:bb[3]]
        sub_p = pg.cx[bb[0]:bb[2], bb[1]:bb[3]]
        preview(job, bb, png, sub_fp, sub_p, title=f"{name} ({job})")
        sp = st[st.key.isin(sub_fp.key)]
        extra.append(f"* `{png.name}`: {len(sub_fp)} footprints, {int((sp.status == 'split').sum())} split, "
                     f"{len(sub_p)} parts")
    if extra:
        extra = ["## Validation views", ""] + extra + [""]
    report(job, st, pg, fp, extra)


def parse_bbox(s):
    return tuple(float(v) for v in s.split(","))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("sf")
    a.add_argument("--bbox", type=parse_bbox)
    a.add_argument("--workers", type=int, default=3)
    a = sub.add_parser("region")
    a.add_argument("--bbox", type=parse_bbox, required=True)
    a.add_argument("--name", required=True)
    a.add_argument("--project", help="EPT project name(s), comma-separated (default: newest covering the bbox)")
    a.add_argument("--workers", type=int, default=3)
    a = sub.add_parser("preview")
    a.add_argument("--job", default="sf")
    a.add_argument("--bbox", type=parse_bbox, required=True)
    a.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.cmd == "sf":
        fp = load_sf_footprints(args.bbox)
        job = "sf" if args.bbox is None else "sf_" + hashlib.md5(str(args.bbox).encode()).hexdigest()[:6]
        run(job, [SF_PROJECT], fp, args.workers, args.bbox, EXAMPLES)
    elif args.cmd == "region":
        projects = args.project.split(",") if args.project else pick_projects(args.bbox)
        fp = load_region_footprints(args.bbox)
        run(args.name, projects, fp, args.workers, args.bbox, {})
    elif args.cmd == "preview":
        import geopandas as gpd
        fp = load_sf_footprints(args.bbox) if args.job.startswith("sf") else None
        p = INTERIM / f"{args.job}_lidar_parts.parquet"
        parts = gpd.read_parquet(p).cx[args.bbox[0]:args.bbox[2], args.bbox[1]:args.bbox[3]] if p.exists() else None
        preview(args.job, args.bbox, args.out, fp, parts, title=args.job)


if __name__ == "__main__":
    main()
