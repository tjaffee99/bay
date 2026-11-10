"""Stage: per-building massing (stepped parts) from airborne LiDAR.

Every footprint in sf_buildings is one prism at one height, so a 16-storey tower on a
6-storey courtyard podium reads as a flat slab. OSM building:parts help only where they
carry heights (188 of SF's 286 OSM-parts buildings give every part the same height).
This stage cuts footprints into parts from a 1 m LiDAR surface model:

  1. DSM / DTM: USGS 3DEP point cloud as Entwine Point Tiles (EPT, public AWS bucket
     usgs-lidar-public, EPSG:3857). Nodes down to ~0.5-0.7 m voxels (SF: depth 8, ~1.65 G
     points, ~13 min with 3 processes) are streamed, decoded (laspy + lazrs) and binned on a
     1 m UTM 10N grid; only the rasters are kept:
        dsm   max z of all returns (noise classes 7/18 dropped)
        dsml  max z of last / single returns (tree canopy suppressed, roofs unchanged)
        dtm   max z of ground / water / ignored-ground points, gaps under buildings
              filled by inverse-distance interpolation
        veg   % of points that are non-last returns (canopy marker)
     -> data/interim/lidar/<job>/{dsm,dsml,dtm,veg}.tif   (int16 decimetres / uint8 %)
  2. Parts: inside each footprint (1 m inset for the statistics; canopy pixels dropped) the
     3x3-median roof surface is joined into plateaus where neighbouring pixels differ by
     < 2 m (pitched roofs stay one surface, a storey step cuts); plateaus under 40 m2 join
     the neighbour closest in height, neighbours closer than 3 m (median roof) merge,
     plateaus whose returns are mostly split are canopy (dropped), plateaus less than 2 m
     above the local ground (courtyards open to the sky) become holes. Footprints with two
     or more plateaus (or a courtyard) are polygonised from the 1 m label raster (vote-
     smoothed, coverage-simplified so shared edges stay shared), clipped to the footprint;
     touching parts closer than 3 m merge, strips narrower than 3 m (crane booms, ledges)
     join their neighbour. Heights: median roof elevation of the plateau minus the
     footprint's ground (mean DTM along the outline, the reference sf_export uses).
     Buildings drawn as OSM building:parts are segmented as one outline ("osmbld:<id>",
     `replaces` = their part keys, `prefer_lidar` where the OSM parts carry no height
     variation or disagree with the LiDAR). Footprints newer than the survey or gone
     before it are skipped.
     -> data/interim/<job>_lidar_parts.parquet (EPSG:4326; key, part_index, height_m,
        roof_m, ground_m, area_m2, replaces, prefer_lidar, lidar_year, lidar_project)
        data/interim/<job>_lidar_heights.parquet (one row per footprint / OSM part:
        status, whole-footprint LiDAR median height, plateau count)
        data/interim/reports/<job>_lidar_parts.md (+ <job>_lidar_<view>.png validation views)

Usage (from pipeline/):
  python lidar_parts.py sf [--bbox lon0,lat0,lon1,lat1] [--workers 3]
      San Francisco: project CA_SanFrancisco_1_B23 (NV5 for USGS, flown 2023-04-20, NPS
      0.15 m). --bbox restricts to a test area (separate job "sf_<hash>").
  python lidar_parts.py region --bbox lon0,lat0,lon1,lat1 --name oakland [--project A,B]
      any other area: the newest survey year whose EPT projects cover the bbox (e.g. Oakland
      CA_AlamedaCo_2_2021 + _3_2021, San Jose CA_SantaClaraCounty_2020) or --project;
      footprints = Overture region buildings (download_region.py) inside the bbox.
  python lidar_parts.py region --name santa_rosa [--redo-parts]
  python lidar_parts.py jobs [--redo-parts]
      the listed jobs of the 2026-11 expansion (REGION_JOBS: box + survey per town / campus /
      plant), one or all in order. Surveys that are not on the EPT bucket are read from their
      LAZ tiles ("tnm:" projects, Antioch / Pittsburg); a survey in feet needs PROJECT_Z_FACTOR
      (the stage stops when single-level roofs read ~3.3 x the footprints' own heights).
      Single-level footprints seen through tree canopy get status "canopy" (no height), and
      footprints with a recorded year after the survey are skipped (newer_than_survey).
  python lidar_parts.py preview --job sf --bbox lon0,lat0,lon1,lat1 --out file.png
      top-down height maps: LiDAR | one prism per footprint | with the LiDAR parts.

Idempotent: EPT metadata and hierarchy pages are cached in data/raw/lidar/<project>/, the
rasters are built once per job (resumable: finished work units are logged in acc/done.txt),
the parts are recomputed when their parquet is missing. Delete data/interim/lidar/<job>/
to rebuild the rasters.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
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
    # collection start .. end of the work unit (USGS WESM.csv, rockyweb.usgs.gov/vdelivery/Datasets/
    # Staged/Elevation/metadata/WESM.csv), mid-date
    "CA_NorthernCA_1_B22": 2022.78,        # 2022-09-13 .. 2022-11-11, QL1 (Sonoma County)
    "USGS_LPC_CA_Sonoma_A4_2013_LAS_2017": 2013.8,  # 2013-09-28 .. 2013-11-11, QL2 (Sonoma Veg Map)
    "CA_SolanoCounty_1_A23": 2023.04,      # 2022-12-26 .. 2023-02-06, QL1
    "CA_NorthCoastRanges_2_B23": 2023.83,  # 2023-09-16 .. 2023-12-15, QL1 (Napa County)
    "CA_SantaCruzCounty_2020": 2020.26,    # 2020-03-22 .. 2020-04-15, QL1
    "tnm:CA_Central_Valley_LiDAR_2016_D16/CA_Sacramento_2017": 2018.0,  # 2017-12-09 .. 2018-01-21, QL2
}
# EPT projects whose z is not metres: the bucket's EPT is EPSG:3857 horizontally but keeps the
# survey's vertical unit. The 2013 Sonoma County survey (Sonoma Veg Map) is in US survey feet
# (checked 2026-11: roofs read 3.3 x their Overture height). run() stops when a job's heights
# look like another unit.
PROJECT_Z_FACTOR = {"USGS_LPC_CA_Sonoma_A4_2013_LAS_2017": 1200 / 3937}
# A project "tnm:<project>/<work unit>" is a survey that is not on the EPT bucket: its LAZ tiles
# (rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/<project>/<work unit>/LAZ/)
# are listed by the TNM Access API for the job's box and binned like EPT nodes (east Contra Costa:
# no EPT project covers Antioch / Pittsburg; the newest public survey there is CA_Sacramento_2017).
TNM = "tnm:"
TNM_API = "https://tnmaccess.nationalmap.gov/api/v1/products"

# Region jobs of the 2026-11 expansion (Sonoma, Napa, Solano, Santa Cruz, east Contra Costa, south
# Santa Clara), in running order: name -> (lon0, lat0, lon1, lat1), EPT project(s). The project is
# the newest 3DEP survey over the box (checked against the EPT index and WESM, 2026-11): Sonoma's
# towns have the 2022 QL1 survey, so the 2013 Sonoma Veg Map survey is not used anywhere.
#   python lidar_parts.py region --name santa_rosa      (bbox / project from this list)
#   python lidar_parts.py jobs                          (every listed job not built yet, one at a time)
# The nine earlier jobs (oakland ... mountain_view) were run with --bbox before this list existed and
# before the canopy / newer-than-survey rules: `jobs` leaves them alone (their parts exist),
# `jobs --redo-parts` recomputes them too on their cached rasters with today's rules.
REGION_JOBS = {
    # the nine earlier downtowns (boxes recovered from their outputs: the same footprint sets)
    "oakland": ((-122.29, 37.79, -122.252, 37.818), "CA_AlamedaCo_2_2021,CA_AlamedaCo_3_2021"),
    "berkeley": ((-122.275, 37.86, -122.248, 37.878), "CA_AlamedaCo_3_2021,CA_AlamedaCo_2_2021"),
    "emeryville": ((-122.3, 37.828, -122.282, 37.845), "CA_AlamedaCo_2_2021,CA_AlamedaCo_3_2021"),
    "san_jose": ((-121.905, 37.32, -121.875, 37.345), "CA_SantaClaraCounty_2020"),
    "walnut_creek": ((-122.07, 37.892, -122.052, 37.908), "USGS_LPC_CA_NoCAL_Wildfires_B5b_2018"),
    "palo_alto": ((-122.168, 37.436, -122.15, 37.452), "CA_SantaClaraCounty_2020"),
    "san_mateo": ((-122.332, 37.558, -122.314, 37.572), "CA_CaliforniaGaps_3_B23"),
    "redwood_city": ((-122.238, 37.478, -122.222, 37.492), "CA_CaliforniaGaps_3_B23"),
    "mountain_view": ((-122.09, 37.388, -122.072, 37.4), "CA_SantaClaraCounty_2020"),
    # 2026-11 expansion
    "santa_rosa": ((-122.730, 38.428, -122.695, 38.460), "CA_NorthernCA_1_B22"),      # downtown, Railroad Sq, Memorial Hospital, SRJC
    "vallejo": ((-122.2645, 38.092, -122.240, 38.112), "CA_SolanoCounty_1_A23"),      # downtown + waterfront
    "napa": ((-122.300, 38.288, -122.272, 38.308), "CA_NorthCoastRanges_2_B23"),
    "santa_cruz": ((-122.040, 36.960, -122.012, 36.982), "CA_SantaCruzCounty_2020"),  # downtown, Beach Hill, Boardwalk
    "fairfield": ((-122.060, 38.240, -122.030, 38.265), "CA_SolanoCounty_1_A23"),     # Texas St, county centre, NorthBay
    "vacaville": ((-122.000, 38.348, -121.975, 38.365), "CA_SolanoCounty_1_A23"),
    "petaluma": ((-122.652, 38.224, -122.622, 38.244), "CA_NorthernCA_1_B22"),        # downtown + the river mills
    "antioch": ((-121.822, 38.006, -121.795, 38.022), "tnm:CA_Central_Valley_LiDAR_2016_D16/CA_Sacramento_2017"),
    # Pittsburg: old town, marina and the industrial waterfront east of it; the box stays inside three of
    # the survey's 1.5 km LAZ tiles (130 MB each, ~0.1 MB/s per connection from rockyweb)
    "pittsburg": ((-121.8937, 38.0242, -121.8615, 38.0450), "tnm:CA_Central_Valley_LiDAR_2016_D16/CA_Sacramento_2017"),
    "gilroy": ((-121.580, 36.998, -121.558, 37.016), "CA_SantaClaraCounty_2020"),
    "morgan_hill": ((-121.665, 37.120, -121.642, 37.138), "CA_SantaClaraCounty_2020"),
    "watsonville": ((-121.770, 36.902, -121.745, 36.920), "CA_SantaCruzCounty_2020"),
    "benicia": ((-122.170, 38.042, -122.145, 38.060), "CA_SolanoCounty_1_A23"),
    "sonoma_state": ((-122.685, 38.334, -122.665, 38.347), "CA_NorthernCA_1_B22"),    # Rohnert Park: Sonoma State University
    # Graton Resort & Casino: the 2022 survey leaves the rancheria (tribal trust land) blank, so the 2013
    # survey (US survey feet) is used; the 2016 hotel tower is newer and keeps its Overture height
    "graton": ((-122.735, 38.352, -122.718, 38.364), "USGS_LPC_CA_Sonoma_A4_2013_LAS_2017"),
    "ucsc": ((-122.072, 36.975, -122.045, 37.003), "CA_SantaCruzCounty_2020"),        # UC Santa Cruz
    "travis_afb": ((-121.970, 38.255, -121.920, 38.280), "CA_SolanoCounty_1_A23"),    # hangar line, David Grant Medical Center
    "mare_island": ((-122.290, 38.085, -122.2645, 38.110), "CA_SolanoCounty_1_A23"),  # shipyard core
    "genentech_vacaville": ((-121.965, 38.375, -121.935, 38.395), "CA_SolanoCounty_1_A23"),
    # Napa Valley: the big wineries and the towns between them
    "st_helena": ((-122.490, 38.498, -122.460, 38.519), "CA_NorthCoastRanges_2_B23"),           # Main St, Beringer, Greystone (CIA)
    "oakville_rutherford": ((-122.440, 38.436, -122.398, 38.462), "CA_NorthCoastRanges_2_B23"),  # Robert Mondavi, Opus One, Inglenook, Beaulieu
    "yountville": ((-122.375, 38.390, -122.352, 38.412), "CA_NorthCoastRanges_2_B23"),           # town, Domaine Chandon, Veterans Home
    "castello_di_amorosa": ((-122.548, 38.555, -122.538, 38.562), "CA_NorthCoastRanges_2_B23"),
}

VOXEL = 0.7            # deepest EPT level read: voxels <= 0.7 m (mercator) -> ~5 pts/m2 on roofs
                       # (SF: cube 21.1 km / span 128 / 2^8 = 0.64 m -> depth 8, 1.65 G points)
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
CANOPY_PLATEAU = 15    # plateau with median >= this % non-last returns = tree canopy, not a part
INSET = 1.0            # footprint inset for the statistics
THIN = 3.0             # parts narrower than this (crane booms, ledges) join their neighbour
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

    def depth_for(self, voxel: float = VOXEL) -> int:
        span = self.meta.get("span", 128)
        return int(np.ceil(np.log2((self.cube[3] - self.cube[0]) / span / voxel)))

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
    m = re.search(r"_[A-Z](\d\d)$", name)  # 3DEP BAA suffix: _B23, _A23 (CA_SolanoCounty_1_A23)
    if m:
        return 2000 + int(m.group(1))
    m = re.search(r"(19|20)\d\d", name)
    return float(m.group(0)) if m else float("nan")


def tnm_tiles(project: str, bbox_ll):
    """LAZ tiles of a 3DEP project / work unit over a lon/lat box, from the TNM Access API (the
    list is cached in data/raw/lidar/<project>__<work unit>/): [(tile name, url, lon/lat bounds)]."""
    tag = hashlib.md5(",".join(f"{v:.5f}" for v in bbox_ll).encode()).hexdigest()[:8]
    cache = LIDAR_RAW / project.replace("/", "__") / f"tnm_{tag}.json"
    if not cache.exists():
        r = get_with_retry(session(), TNM_API, params={"datasets": "Lidar Point Cloud (LPC)", "max": 500,
                                                       "bbox": ",".join(f"{v:.6f}" for v in bbox_ll),
                                                       "outputFormat": "JSON"})
        items = [{"url": it["downloadURL"], "bbox": it["boundingBox"], "size": it.get("sizeInBytes")}
                 for it in r.json().get("items", []) if f"/{project}/" in it["downloadURL"]]
        if not items:
            raise SystemExit(f"TNM lists no LAZ tile of {project} in {bbox_ll}")
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(items, indent=1))
    return [(Path(it["url"]).stem, it["url"], (it["bbox"]["minX"], it["bbox"]["minY"], it["bbox"]["maxX"], it["bbox"]["maxY"]))
            for it in json.loads(cache.read_text())]


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
    err = None
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
    raise RuntimeError(f"failed to fetch {url}: {err!r}")


def _bin_points(las, g, to_utm, zfac=1.0):
    """Decoded points (an EPT node / a chunk of a LAZ tile) -> (cell, z dm, last return, ground)."""
    cls = np.asarray(las.classification)
    ok = ~np.isin(cls, NOISE_CLASSES)
    try:
        ok &= ~np.asarray(las.withheld, bool)
    except Exception:  # noqa: BLE001 - no withheld flag in this point format
        pass
    x = np.asarray(las.x)[ok]
    y = np.asarray(las.y)[ok]
    z = np.asarray(las.z)[ok] * zfac
    rn = np.asarray(las.return_number)[ok].astype(np.int16)
    nr = np.asarray(las.number_of_returns)[ok].astype(np.int16)
    cls = cls[ok]
    u, v = to_utm(x, y)
    c = np.floor((u - g.x0) / g.res).astype(np.int64)
    r = np.floor((g.y1 - v) / g.res).astype(np.int64)
    inside = (c >= 0) & (c < g.w) & (r >= 0) & (r < g.h)
    if not inside.any():
        return None
    zz = np.clip(np.rint(z[inside] * 10), -32000, 32000).astype(np.int16)
    return r[inside] * g.w + c[inside], zz, (rn >= nr)[inside], np.isin(cls[inside], GROUND_CLASSES)


def _reduce(parts):
    """Binned points -> per cell (index, max z, max last-return z, max ground z, points, non-last)."""
    idx = np.concatenate([p[0] for p in parts])
    zz = np.concatenate([p[1] for p in parts])
    last = np.concatenate([p[2] for p in parts])
    gnd = np.concatenate([p[3] for p in parts])
    o = np.argsort(idx, kind="stable")
    idx, zz, last, gnd = idx[o], zz[o], last[o], gnd[o]
    starts = np.flatnonzero(np.r_[True, idx[1:] != idx[:-1]])
    return (idx[starts], np.maximum.reduceat(zz, starts),
            np.maximum.reduceat(np.where(last, zz, NODATA).astype(np.int16), starts),
            np.maximum.reduceat(np.where(gnd, zz, NODATA).astype(np.int16), starts),
            np.add.reduceat(np.ones(len(idx), np.int32), starts), np.add.reduceat((~last).astype(np.int32), starts))


def _bin_laz_tile(uid, url):
    """One LAZ tile (its own CRS, read from the header), decoded in chunks of 2 M points."""
    import laspy
    import pyproj
    path = _download(url, LIDAR_RAW / "_tiles" / url.rsplit("/", 1)[-1])
    if path is None:
        return uid, None
    try:
        return uid, _bin_laz_file(path)
    finally:
        path.unlink()  # 100-300 MB each: only the rasters are kept


def _download(url, path, tries=600):
    """A big file to disk, resumed with HTTP Range after every break: rockyweb.usgs.gov answers
    429 in bursts (a queue page) and serves ~0.1 MB/s per connection through the proxy."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():  # complete, left by an interrupted run
        return path
    part = path.with_name(path.name + ".part")
    total = None
    for attempt in range(tries):
        have = part.stat().st_size if part.exists() else 0
        if total is not None and have >= total:
            break
        try:
            with _W["s"].get(url, headers={"Range": f"bytes={have}-"} if have else {}, stream=True, timeout=120) as r:
                if r.status_code == 404:
                    return None
                if r.status_code == 416:  # nothing after `have`: complete
                    total = have
                elif r.status_code in (200, 206):
                    total = int(r.headers["Content-Range"].rsplit("/", 1)[-1]) if r.status_code == 206 \
                        else int(r.headers.get("Content-Length", 0)) or None
                    with open(part, "ab" if r.status_code == 206 else "wb") as f:
                        for chunk in r.iter_content(1 << 20):
                            f.write(chunk)
                    if total is None:
                        total = part.stat().st_size
                    continue
        except Exception:  # noqa: BLE001 - broken stream: resume
            pass
        time.sleep(min(20.0, 2.0 + attempt))
    else:
        raise RuntimeError(f"failed to download {url}")
    os.replace(part, path)
    return path


def _bin_laz_file(path):
    import laspy
    import pyproj
    reds = []
    with laspy.open(path) as rd:
        crs = rd.header.parse_crs()
        if crs is None:
            raise RuntimeError(f"{path}: no CRS in the LAS header")
        subs = crs.sub_crs_list if crs.is_compound else [crs]
        horiz = next(c for c in subs if not c.is_vertical)
        vert = next((c for c in subs if c.is_vertical), None)
        # z to metres (vertical unit; a projected CRS in feet without a vertical part has z in feet too)
        zfac = vert.axis_info[0].unit_conversion_factor if vert is not None else \
            (horiz.axis_info[0].unit_conversion_factor if horiz.is_projected else 1.0)
        # projection only, no datum shift: NAD83 is taken as WGS 84, as the EPT (EPSG:3857) nodes are
        to_ll = pyproj.Transformer.from_crs(horiz, horiz.geodetic_crs, always_xy=True)
        ll_utm = pyproj.Transformer.from_crs("EPSG:4326", UTM, always_xy=True)

        def to_utm(x, y):
            return ll_utm.transform(*to_ll.transform(x, y))

        for pts in rd.chunk_iterator(2_000_000):
            p = _bin_points(pts, _W["grid"], to_utm, zfac)
            if p is not None:
                reds.append(_reduce([p]))
    if not reds:
        return None
    if len(reds) == 1:
        return reds[0]
    idx = np.concatenate([r[0] for r in reds])
    o = np.argsort(idx, kind="stable")
    idx = idx[o]
    starts = np.flatnonzero(np.r_[True, idx[1:] != idx[:-1]])
    col = [np.concatenate([r[i] for r in reds])[o] for i in range(1, 6)]
    return (idx[starts], np.maximum.reduceat(col[0], starts), np.maximum.reduceat(col[1], starts),
            np.maximum.reduceat(col[2], starts), np.add.reduceat(col[3], starts), np.add.reduceat(col[4], starts))


def _bin_unit(unit):
    """Download + decode the nodes of one work unit, bin on the grid, reduce per cell."""
    import laspy
    uid, url, keys, bounds = unit
    if keys is None:
        return _bin_laz_tile(uid, url)
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

    def to_utm(x, y):
        if affine is None:
            return tr.transform(x, y)
        cu, cv = affine
        return cu[0] * x + cu[1] * y + cu[2], cv[0] * x + cv[1] * y + cv[2]

    for _, data in _W["pool"].map(_fetch, [f"{url}/ept-data/{k}.laz" for k in keys]):
        if data is None:
            continue
        p = _bin_points(laspy.read(io.BytesIO(data), decompression_selection=sel), g, to_utm,
                        PROJECT_Z_FACTOR.get(url.rsplit("/", 1)[-1], 1.0))
        if p is not None:
            parts.append(p)
    if not parts:
        return uid, None
    return uid, _reduce(parts)


def build_rasters(job: str, projects: list[str], grid: Grid, interest=None, workers: int = 3):
    """Stream the EPT nodes over the grid into 1 m rasters (data/interim/lidar/<job>/)."""
    import pyproj
    from shapely import box as sbox
    out = LIDAR_INT / job
    if (out / "dtm.tif").exists():
        log(f"lidar: rasters for {job} exist ({out})")
        return out
    out.mkdir(parents=True, exist_ok=True)
    depths = {p: Ept(p).depth_for() for p in projects if not p.startswith(TNM)}
    meta = {"job": job, "project": "+".join(projects), "lidar_year": min(project_year(p) for p in projects),
            "grid": grid.to_json(), "max_depth": max(depths.values(), default=0), "depths": depths, "crs": UTM}
    (out / "meta.json").write_text(json.dumps(meta, indent=1))

    # grid bbox in EPSG:3857 (+ margin) for node selection
    inv = pyproj.Transformer.from_crs(UTM, "EPSG:3857", always_xy=True)
    gx = np.array([grid.x0, grid.x0 + grid.w * grid.res])
    gy = np.array([grid.y1 - grid.h * grid.res, grid.y1])
    X, Y = np.meshgrid(np.linspace(gx[0], gx[1], 9), np.linspace(gy[0], gy[1], 9))
    mx, my = inv.transform(X.ravel(), Y.ravel())
    mb = (mx.min() - 20, my.min() - 20, mx.max() + 20, my.max() + 20)

    ulist = []
    for project in projects:
        if project.startswith(TNM):  # LAZ tiles: one work unit per tile that has footprints
            fwd = pyproj.Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
            ll = fwd.transform([mb[0], mb[2]], [mb[1], mb[3]])
            n0 = len(ulist)
            for name, turl, tb in tnm_tiles(project[len(TNM):], (ll[0][0], ll[1][0], ll[0][1], ll[1][1])):
                tx, ty = fwd.transform([tb[0], tb[2]], [tb[1], tb[3]], direction="INVERSE")
                if interest is None or len(interest.query(sbox(tx[0], ty[0], tx[1], ty[1]))) > 0:
                    ulist.append((f"{project}:{name}", turl, None, None))
            log(f"lidar: {project}: {len(ulist) - n0} LAZ tiles")
            continue
        ept = Ept(project)
        max_depth = depths[project]
        ud = max_depth - 2  # work unit = one column of this depth (~260 m), its deeper nodes included

        def keep(b, d):
            if b[2] < mb[0] or b[0] > mb[2] or b[3] < mb[1] or b[1] > mb[3]:
                return False
            if interest is not None and d >= ud:
                return len(interest.query(sbox(*b))) > 0
            return True

        nodes = ept.nodes(max_depth, keep)
        log(f"lidar: {project}: {len(nodes)} EPT nodes (depth <= {max_depth}), {sum(nodes.values()) / 1e6:.0f} M points")
        # work units: one per depth-6 column (~260 m in SF); coarser nodes in batches
        units: dict[str, list[str]] = {}
        for k in nodes:
            d, x, y, z = map(int, k.split("-"))
            uid = f"{ud}-{x >> (d - ud)}-{y >> (d - ud)}" if d >= ud else f"top-{d}-{(x * 7 + y) % 8}"
            units.setdefault(uid, []).append(k)
        for uid, keys in sorted(units.items()):
            b = None
            if not uid.startswith("top"):
                _, x, y = map(int, uid.split("-"))
                s = (ept.cube[3] - ept.cube[0]) / 2 ** ud
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


def segment(z, hag, S, px_area=1.0, veg=None):
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
    if veg is not None and len(pix) > 1:
        # a plateau whose returns are often split (median >= CANOPY_PLATEAU %) is tree canopy over
        # the roof / courtyard: its pixels go to the neighbouring plateaus (filled by nearest later)
        vf = veg.ravel()
        for i in [i for i in pix if np.nanmedian(np.r_[vf[pix[i]], 0.0]) >= CANOPY_PLATEAU]:
            if len(pix) > 1:
                dropped.append(pix.pop(i))
                area.pop(i), med.pop(i), hmed.pop(i)
                for k in nb.pop(i):
                    nb[k].discard(i)
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


def split_footprint(geom, wt, z, hag, dtm, veg=None, px_area=1.0):
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

    def single():
        # one roof level. Seen through tree canopy (or a lattice tower / pipe rack): where most of
        # its pixels have split returns the median sits on the trees, not the roof -> no height
        # (Santa Rosa 2022: 22-71 % of such footprints read > 5 m above their Overture height,
        # 0.1-0.5 % of the others)
        if veg is not None and np.mean(veg[Si & np.isfinite(z)] >= CANOPY_PLATEAU) > 0.5:
            return "canopy", whole, gref, []
        return "single", whole, gref, []

    area = S.sum() * px_area
    hin = hag[Si & np.isfinite(z)]
    open_frac = float((hin < OPEN_HAG).mean())
    if open_frac > 0.6:
        return "mostly_open", whole, gref, []          # building gone / not built yet / mis-registered
    p1, p99 = np.percentile(zin, [1, 99])
    if area < 2 * MIN_PART or (p99 - p1 < MIN_STEP and open_frac * area < MIN_PART):
        return single()
    # plateaus on the inset (edge pixels are mixed with walls / eaves), then extended to the footprint
    lab, info = segment(np.where(Si, z, np.nan), hag, Si, px_area, veg)
    if len(info) <= 1:
        return single()
    nparts = sum(1 for v in info.values() if not v[3])
    if nparts == 0:
        return "mostly_open", whole, gref, []
    if nparts == 1 and all(v[2] * px_area < MIN_PART for v in info.values() if v[3]):
        return single()
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
    # touching parts closer than MIN_STEP (split apart by the inset at a narrow neck, or by canopy)
    merged = True
    while merged and len(parts) > 1:
        merged = False
        best = None
        for i in range(len(parts)):
            for j in range(i + 1, len(parts)):
                d = abs(parts[i][1] - parts[j][1])
                if d < MIN_STEP and (best is None or d < best[0]) and \
                        parts[i][0].buffer(0.3).intersection(parts[j][0]).area > 1.0:
                    best = (d, i, j)
        if best:
            _, i, j = best
            a, b = parts[i], parts[j]
            parts[i] = [shapely.make_valid(shapely.union_all([a[0], b[0]])), (a[1] * a[2] + b[1] * b[2]) / (a[2] + b[2]),
                        a[2] + b[2]]
            parts[i][2] = parts[i][0].area
            parts.pop(j)
            merged = True
    # slivers left by clipping and thin strips (crane booms, ledges, < ~3 m wide): join the
    # neighbour sharing the longest edge (keeping its height)
    def bad(p):
        return p[2] < MIN_PART * 0.75 or p[0].buffer(-THIN / 2).area < 0.15 * p[2]

    while len(parts) > 1:
        cand = [i for i, p in enumerate(parts) if bad(p)]
        if not cand:
            break
        p = parts.pop(min(cand, key=lambda i: parts[i][2]))
        shared = [parts[i][0].buffer(0.3).intersection(p[0]).area for i in range(len(parts))]
        j = int(np.argmax(shared))
        if shared[j] <= 0 and p[2] < 10:
            continue  # isolated speck: drop
        parts[j][0] = shapely.make_valid(shapely.union_all([parts[j][0], p[0]]))
        parts[j][2] = parts[j][0].area
    if len(parts) == 1 and parts[0][2] > 0.9 * geom.area:
        return single()
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
    return z, dtm, np.where(veg == 255, np.nan, veg.astype(np.float32))


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
    Z, DTM, VEG = _read(W)
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
            status, whole, gref, parts = split_footprint(geom, wt, z, hag_all[sl], dtm, VEG[sl])
        except Exception as e:  # noqa: BLE001 - one bad footprint must not stop the run
            status, whole, gref, parts = f"error:{type(e).__name__}", np.nan, np.nan, []
        extra = None if status != "split" else True  # plain footprint: use its LiDAR parts
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
    """Overture footprints of the counties (download_region.py) whose centroid lies in the bbox."""
    import geopandas as gpd
    import pandas as pd
    import shapely
    from download_region import OUT_OVERTURE
    from common import read_region_overture
    d = read_region_overture("building", columns=["id", "has_parts", "height", "px", "py", "geometry"],
                             filters=[("px", ">=", bbox_ll[0]), ("px", "<=", bbox_ll[2]),
                                      ("py", ">=", bbox_ll[1]), ("py", "<=", bbox_ll[3])]).to_pandas()
    g = gpd.GeoDataFrame({"key": d["id"].values, "source": np.where(d.has_parts.fillna(False), "overture_has_parts",
                                                                     "overture"),
                          "start_year": region_recorded_years(d["id"].values), "end_year": np.nan,
                          "height": d.height.astype(float).values, "members": None},
                         geometry=shapely.from_wkb(d.geometry.values), crs="EPSG:4326")
    log(f"region: {len(g)} Overture footprints in {bbox_ll} ({int(np.isfinite(g.start_year).sum())} with a recorded year)")
    return g


def region_recorded_years(ids):
    """Recorded construction year per Overture footprint id (download_region.py candidates:
    historic survey > official roll > public copy > commercial; placeholder spikes dropped; NaN =
    none). run_parts skips footprints recorded after the survey (status newer_than_survey): the
    survey saw the site before today's building, so it keeps its flat footprint and Overture
    height instead of parts / a height cut from whatever stood there (region_buildings applies
    the same rule to the single-level heights with its final start year)."""
    import pandas as pd
    p = INTERIM / "region5_footprint_years.parquet"
    out = np.full(len(ids), np.nan)
    if not p.exists() or not len(ids):
        return out
    kinds = ("historic", "public", "third_party", "commercial")
    fy = pd.read_parquet(p, columns=["id"] + [f"{a}_{k}" for k in kinds for a in ("year", "spike")],
                         filters=[("id", "in", list(ids))]).drop_duplicates("id").set_index("id")
    fy = fy.reindex(ids)
    for k in kinds:
        y = pd.to_numeric(fy[f"year_{k}"], errors="coerce").to_numpy(dtype=float, na_value=np.nan)
        ok = np.isfinite(y) & (y > 1700) & ~fy[f"spike_{k}"].fillna(False).astype(bool).values
        out = np.where(np.isfinite(out), out, np.where(ok, y, np.nan))
    return out


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
    st["n_parts"] = st.n_parts.fillna(0).astype(int)
    st["lidar_year"] = year
    st["lidar_project"] = meta["project"]
    pdf = pd.DataFrame(parts, columns=["key", "part_index", "roof_m", "ground_m", "area_m2", "replaces", "prefer_lidar",
                                       "wkb"])
    pg = gpd.GeoDataFrame(pdf.drop(columns="wkb"), geometry=shapely.from_wkb(pdf.wkb.values), crs=UTM)
    pg["height_m"] = (pg.roof_m - pg.ground_m).clip(lower=1.0).round(2)
    pg["roof_m"] = pg.roof_m.round(2)
    pg["ground_m"] = pg.ground_m.round(2)
    pg["area_m2"] = pg.area_m2.round(1)
    pg["prefer_lidar"] = pg.prefer_lidar.astype(bool)
    st["prefer_lidar"] = st.prefer_lidar.astype("boolean")
    pg["lidar_year"] = year
    pg["lidar_project"] = meta["project"]
    pg = pg[["key", "part_index", "height_m", "roof_m", "ground_m", "area_m2", "replaces", "prefer_lidar", "lidar_year",
             "lidar_project", "geometry"]]
    return st, pg.to_crs("EPSG:4326")


# ----------------------------------------------------------------------------- preview / report
def preview(job, bbox_ll, out_png, fp=None, parts=None, title=None):
    """Top-down height maps, same colour scale: LiDAR (DSM - DTM) with the footprints | the model
    today (one prism per footprint, OSM parts as drawn) | the model with the LiDAR parts."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pyproj
    import rasterio
    from rasterio.features import rasterize
    from rasterio.windows import from_bounds
    from rasterio.windows import transform as wtransform
    tr = pyproj.Transformer.from_crs("EPSG:4326", UTM, always_xy=True)
    x0, y0 = tr.transform(bbox_ll[0], bbox_ll[1])
    x1, y1 = tr.transform(bbox_ll[2], bbox_ll[3])
    d = LIDAR_INT / job
    with rasterio.open(d / "dsm.tif") as f, rasterio.open(d / "dtm.tif") as g:
        w = from_bounds(x0, y0, x1, y1, f.transform).round_offsets().round_lengths()
        dsm = f.read(1, window=w, boundless=True, fill_value=NODATA).astype(float)
        dtm = g.read(1, window=w, boundless=True, fill_value=NODATA).astype(float)
        wt = wtransform(w, f.transform)
    ndsm = np.where((dsm == NODATA) | (dtm == NODATA), np.nan, (dsm - dtm) / 10)
    b = rasterio.windows.bounds(w, f.transform)
    ext = (b[0], b[2], b[1], b[3])
    vmax = float(np.nanpercentile(ndsm, 99.7)) if np.isfinite(ndsm).any() else 50.0
    fpu = fp.to_crs(UTM) if fp is not None and len(fp) else None
    pp = parts.to_crs(UTM) if parts is not None and len(parts) else None
    used = set()
    if pp is not None:
        ok = pp.prefer_lidar.fillna(True).astype(bool) if "prefer_lidar" in pp else np.ones(len(pp), bool)
        pp = pp[np.asarray(ok, bool)]
        used = set(pp.key)

    def model(with_parts):
        shp = []
        if fpu is not None:
            for r in fpu.itertuples():
                if with_parts and r.key in used:
                    continue
                if getattr(r, "members", None):
                    shp += [(mg, mh) for _, mg, mh in r.members if np.isfinite(mh)]
                elif np.isfinite(r.height):
                    shp.append((r.geometry, r.height))
        if with_parts and pp is not None:
            shp += list(zip(pp.geometry, pp.height_m))
        shp.sort(key=lambda t: t[1])
        if not shp:
            return np.full(ndsm.shape, np.nan)
        m = rasterize([(g_, float(h)) for g_, h in shp], out_shape=ndsm.shape, transform=wt, fill=np.nan,
                      dtype="float32")
        return m

    asp = (ext[3] - ext[2]) / max(1.0, ext[1] - ext[0])
    fig, axs = plt.subplots(1, 3, figsize=(22, 22 / 3 * asp + 1.2), layout="constrained")
    from matplotlib.colors import PowerNorm
    norm = PowerNorm(0.5, vmin=0, vmax=vmax)  # towers and houses both readable
    year = json.loads((d / "meta.json").read_text())["lidar_year"]
    panels = [(ndsm, f"LiDAR {int(year)}: height above ground (DSM - DTM), footprints"), (model(False), "model now: one prism per footprint"),
              (model(True), "model with LiDAR parts")]
    for ax, (img, ttl) in zip(axs, panels):
        ax.set_facecolor("#202020")
        ax.imshow(img, extent=ext, cmap="magma", norm=norm, interpolation="nearest")
        ax.set_title(ttl)
        ax.set_xlim(ext[0], ext[1])
        ax.set_ylim(ext[2], ext[3])
        ax.set_xticks([])
        ax.set_yticks([])
    if fpu is not None:
        fpu.boundary.plot(ax=axs[0], color="cyan", linewidth=0.5)
        fpu.boundary.plot(ax=axs[1], color="#66ccff", linewidth=0.3)
    if pp is not None:
        pp.boundary.plot(ax=axs[2], color="white", linewidth=0.5)
        for r in pp.itertuples():
            if r.geometry.area > 200:
                c = r.geometry.representative_point()
                axs[2].annotate(f"{r.height_m:.0f}", (c.x, c.y), color="cyan", fontsize=6, ha="center", va="center")
    sm = plt.cm.ScalarMappable(cmap="magma", norm=norm)
    fig.colorbar(sm, ax=axs, fraction=0.012, pad=0.01, label="m above ground")
    if title:
        fig.suptitle(title)
    fig.savefig(out_png, dpi=100, bbox_inches="tight")
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


STATUS_TEXT = {
    "split": "cut into LiDAR parts",
    "single": "one roof plateau (no step >= 3 m over >= 40 m2): stays one prism",
    "canopy": "one roof level, but most of its pixels have split returns (tree canopy over the roof, lattice "
              "tower): no measured height, keeps its Overture height",
    "mostly_open": "> 60 % of the footprint is at ground level in the survey (building gone / footprint over open ground)",
    "no_data": "too few LiDAR returns inside (glass / water / outside the survey)",
    "no_ground": "no ground around it in the DTM",
    "newer_than_survey": "start_year after the survey: keeps its flat footprint",
    "gone_before_survey": "end_year before the survey",
    "osm_part": "an OSM building:part (member of an osmbld: outline), LiDAR height for comparison",
}


def report(job, st, pg, fp, extra_lines=()):
    REPORTS.mkdir(parents=True, exist_ok=True)
    meta = json.loads((LIDAR_INT / job / "meta.json").read_text())
    split = st[st.status == "split"]
    outs = [INTERIM / f"{job}_lidar_parts.parquet", INTERIM / f"{job}_lidar_heights.parquet"]
    lines = [f"# LiDAR building parts ({job})", "",
             f"* LiDAR: USGS 3DEP `{meta['project']}` (" + ("LAZ tiles listed by the TNM API" if TNM in meta["project"]
                                                             else f"Entwine Point Tiles, depth <= {meta['max_depth']}") + "), "
             f"survey {meta['lidar_year']}; built by `pipeline/lidar_parts.py`",
             f"* rasters: {meta['grid']['w']} x {meta['grid']['h']} cells at {meta['grid']['res']} m ({UTM}), "
             f"`data/interim/lidar/{job}/{{dsm,dsml,dtm,veg}}.tif`",
             "* outputs: " + ", ".join(f"`{o.relative_to(INTERIM.parent.parent)}` ({o.stat().st_size / 1e6:.1f} MB)"
                                       for o in outs if o.exists()),
             f"* parameters: plateau edge step {EDGE_STEP} m, min step between parts {MIN_STEP} m, min part / courtyard "
             f"{MIN_PART} m2, open to the sky below {OPEN_HAG} m above ground, canopy >= {VEG_FRAC} % split returns, "
             f"inset {INSET} m, simplify {SIMPLIFY}",
             "", "## Coverage", "", "| status | footprints | meaning |", "|---|---:|---|"]
    for k, v in st.status.value_counts().items():
        lines.append(f"| {k} | {v} | {STATUS_TEXT.get(k, '')} |")
    lines += ["", f"* **{len(split)} footprints split into {len(pg)} parts** (median {split.n_parts.median() if len(split) else 0:.0f}, "
              f"max {split.n_parts.max() if len(split) else 0:.0f} per footprint); split footprints cover "
              f"{fp[fp.key.isin(split.key)].to_crs(UTM).area.sum() / 1e6:.2f} km2, their parts "
              f"{pg.to_crs(UTM).area.sum() / 1e6:.2f} km2 (the difference = courtyards / ground-level areas)"]
    osm = st[st.key.astype(str).str.startswith("osmbld:")]
    if len(osm):
        n_unif = int(osm.prefer_lidar.fillna(False).astype(bool).sum())
        lines += [f"* OSM building:part outlines (`osmbld:` keys, `replaces` = their part keys): {len(osm)}, "
                  f"{int((osm.status == 'split').sum())} split by LiDAR, **prefer_lidar** for {n_unif} (their OSM parts "
                  f"all share one height, or differ from the LiDAR by > 6 m over > 25 % of the outline)"]
        mem = st[st.status == "osm_part"].merge(fp.explode("members")[["members"]].dropna().assign(
            key=lambda d: d.members.map(lambda m: m[0]), osm_h=lambda d: d.members.map(lambda m: m[2]))[["key", "osm_h"]],
            on="key", how="left")
        mem = mem[np.isfinite(mem.lidar_height_m) & np.isfinite(mem.osm_h)]
        if len(mem):
            dd = mem.lidar_height_m - mem.osm_h
            lines.append(f"* OSM part heights vs LiDAR: median |diff| {dd.abs().median():.1f} m, > 6 m for "
                         f"{(dd.abs() > 6).mean():.0%} of {len(mem)} parts")
    if "height" in fp and len(st):
        m = st.merge(fp[["key", "height", "source"]], on="key")
        m = m[np.isfinite(m.lidar_height_m.astype(float)) & np.isfinite(m.height.astype(float)) & (m.status != "osm_part")]
        if len(m):
            lines += ["", "## Whole-footprint LiDAR height vs the current height", "",
                      "| source | footprints | median diff (m) | abs diff > 5 m |", "|---|---:|---:|---:|"]
            for src, g in m.groupby("source"):
                dh = g.lidar_height_m - g.height
                lines.append(f"| {src} | {len(g)} | {dh.median():+.2f} | {(dh.abs() > 5).mean():.1%} |")
            lines.append("")
            lines.append("`lidar_height_m` (survey median roof minus the mean ground along the outline) is in "
                         f"`{job}_lidar_heights.parquet` for every footprint, also the unsplit ones.")
    lines += [""] + list(extra_lines)
    if len(split):
        big = split.copy()
        big["area"] = big.key.map(fp.set_index("key").to_crs(UTM).area)
        big = big.sort_values("area", ascending=False).head(15)
        hs = pg.groupby("key").height_m.agg(["min", "max"])
        lines += ["## Largest split footprints", "", "| key | parts | part heights (m) | footprint m2 |", "|---|---:|---|---:|"]
        lines += [f"| {r.key} | {r.n_parts} | {hs.loc[r.key, 'min']:.0f}-{hs.loc[r.key, 'max']:.0f} | {r.area:.0f} |"
                  for r in big.itertuples() if r.key in hs.index]
    lines += ["", "## Using the parts", "",
              "* `replaces`: the sf_buildings keys a footprint's parts stand in for (`|`-separated; the footprint "
              "itself, or all OSM parts of an `osmbld:` outline). `prefer_lidar` is True for every plain footprint; "
              "for an `osmbld:` outline only where its OSM parts carry no height variation or disagree with the LiDAR "
              "(else keep the OSM parts).",
              "* `height_m` = part roof (median, NAVD88 `roof_m`) minus the footprint's ground (`ground_m`, mean DTM "
              "along the outline, the reference sf_export uses for the roof). On a slope the parts of one footprint "
              "share that ground, so keep the roof consistent by adding (footprint ground - part ground) when each "
              "part gets its own terrain sample.",
              "* parts tile the footprint (minus courtyards open to the sky); every part is extruded from the ground.",
              "* buildings newer than the survey (and footprints with status mostly_open) keep their flat footprint."]
    (REPORTS / f"{job}_lidar_parts.md").write_text("\n".join(lines) + "\n")
    log(f"report: {REPORTS / f'{job}_lidar_parts.md'}")


def job_grid(fp_ll, margin=60.0):
    b = fp_ll.to_crs(UTM).total_bounds
    return Grid(b[0] - margin, b[1] - margin, b[2] + margin, b[3] + margin)


def interest_tree(fp_ll):
    import shapely
    g = fp_ll.to_crs("EPSG:3857").geometry.envelope.buffer(40).values
    return shapely.STRtree(g)


def run(job, projects, fp, workers, bbox_ll=None, examples=None, redo_parts=False):
    import pandas as pd
    grid = job_grid(fp)
    log(f"job {job}: {len(fp)} footprints, grid {grid.w} x {grid.h} m, LiDAR {', '.join(projects)}")
    build_rasters(job, projects, grid, interest=interest_tree(fp), workers=workers)
    out_parts = INTERIM / f"{job}_lidar_parts.parquet"
    out_st = INTERIM / f"{job}_lidar_heights.parquet"
    if out_parts.exists() and out_st.exists() and not redo_parts:
        log(f"parts: {out_parts} exists (--redo-parts to recompute)")
        import geopandas as gpd
        st, pg = pd.read_parquet(out_st), gpd.read_parquet(out_parts)
    else:
        st, pg = run_parts(job, fp, workers)
        # unit check: single-level roofs against the footprints' own heights (Overture / DataSF)
        both = st[st.status == "single"].merge(fp[["key", "height"]], on="key")
        both = both[(both.height > 2) & (both.lidar_height_m.astype(float) > 2)]
        ratio = float((both.lidar_height_m.astype(float) / both.height).median()) if len(both) >= 30 else 1.0
        if not 0.6 < ratio < 1.6:
            raise SystemExit(f"{job}: LiDAR / footprint height ratio {ratio:.2f} over {len(both)} footprints: wrong "
                             f"vertical unit? (feet -> add the project to PROJECT_Z_FACTOR); nothing written")
        for frame, out in ((pg, out_parts), (st, out_st)):  # replaced whole: region_buildings may be reading
            tmp = out.with_name(out.name + ".tmp")
            frame.to_parquet(tmp)
            os.replace(tmp, out)
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
    a.add_argument("--bbox", type=parse_bbox, help="default: the box of --name in REGION_JOBS")
    a.add_argument("--name", required=True)
    a.add_argument("--project", help="EPT project name(s), comma-separated (default: REGION_JOBS, else the "
                                     "newest covering the bbox)")
    a.add_argument("--workers", type=int, default=3)
    a.add_argument("--redo-parts", action="store_true", help="recompute the parts on the existing rasters")
    a = sub.add_parser("jobs", help="every REGION_JOBS job whose parts are not built yet, in order")
    a.add_argument("--workers", type=int, default=3)
    a.add_argument("--redo-parts", action="store_true", help="every listed job: recompute the parts")
    a = sub.add_parser("preview")
    a.add_argument("--job", default="sf")
    a.add_argument("--bbox", type=parse_bbox, required=True)
    a.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.cmd == "sf":
        fp = load_sf_footprints(args.bbox)
        job = "sf" if args.bbox is None else "sf_" + hashlib.md5(str(args.bbox).encode()).hexdigest()[:6]
        run(job, [SF_PROJECT], fp, args.workers, args.bbox, EXAMPLES)
    elif args.cmd in ("region", "jobs"):
        if args.cmd == "jobs":
            todo = [(n, bb, pr) for n, (bb, pr) in REGION_JOBS.items()
                    if args.redo_parts or not (INTERIM / f"{n}_lidar_parts.parquet").exists()]
        else:
            listed = REGION_JOBS.get(args.name)
            if args.bbox is None and listed is None:
                raise SystemExit(f"--bbox is required: {args.name} is not in REGION_JOBS")
            todo = [(args.name, args.bbox or listed[0], args.project or (listed[1] if listed and not args.bbox else None))]
        for name, b, project in todo:
            projects = project.split(",") if project else pick_projects(b)
            fp = load_region_footprints(b)
            cx, cy, hw, hh = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2, min(0.004, (b[2] - b[0]) / 2), min(0.003, (b[3] - b[1]) / 2)
            run(name, projects, fp, args.workers, b, {"centre": (cx - hw, cy - hh, cx + hw, cy + hh)}, args.redo_parts)
    elif args.cmd == "preview":
        import geopandas as gpd
        fp = load_sf_footprints(args.bbox) if args.job.startswith("sf") else load_region_footprints(args.bbox)
        p = INTERIM / f"{args.job}_lidar_parts.parquet"
        parts = gpd.read_parquet(p).cx[args.bbox[0]:args.bbox[2], args.bbox[1]:args.bbox[3]] if p.exists() else None
        preview(args.job, args.bbox, args.out, fp, parts, title=args.job)


if __name__ == "__main__":
    main()
