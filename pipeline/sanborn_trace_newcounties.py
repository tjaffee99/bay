"""Trace demolished buildings of the downtowns of the new counties (Sonoma, Solano, Napa, Santa Cruz) from Library of
Congress Sanborn maps.

Areas (data/manual/sanborn/README_northbay.md, README_santa_cruz.md):
  santa_rosa_downtown   the courthouse-square blocks, 4th St from the railroad to E St (Dec 1904 = before the earthquake
                        of 18 Apr 1906, 1908 = the rebuilt town)
  vallejo_downtown      Georgia / Virginia / Marin St down to Mare Island Strait: the old downtown and waterfront, most
                        of it razed for the Marina Vista redevelopment
  napa_downtown         Main / First / Second / Third St and the river front
  santa_cruz_downtown   Pacific Avenue and the blocks around it
  petaluma_downtown, watsonville_downtown, benicia_downtown   (configured; traced only as far as the README says)

This is a thin extension of pipeline/sanborn_trace_peninsula.py (-> sanborn_trace_eastbay.py -> sanborn_trace_waterfront.py):
the same block specs (four streets + estimated pixel corners), `refine`, property corners from today's parcels (`pc`),
offset corners from centrelines + printed street widths (`oc`), similarity fits per block / group, colour segmentation
with partition-wall splitting, SIFT registration of an edition onto a later state of the same plate, and the same output
schema and confidence rules. What changes is the per-town configuration:
  * street centrelines: Overture transportation segments, release 2026-10-21.0 (roads_local.parquet + roads_region.parquet),
    clipped to the town box;
  * property lines: the county parcel layers in data/raw/region_years/{sonoma_county, solano_county, napa_county,
    santa_cruz_parcels} (their parcel-id column differs per county: `pid`);
  * today's footprints for modern_overlap: Overture buildings of the four new counties (region4_building.parquet);
  * `partner`: finds the sheet of another edition that shows the same ground (SIFT inliers), for towns whose sheets were
    renumbered between editions.

Usage:  python pipeline/sanborn_trace_newcounties.py <town> all            # fetch + georef + extract + assemble + check
        python pipeline/sanborn_trace_newcounties.py <town> sheets          # sheets of each volume
        python pipeline/sanborn_trace_newcounties.py <town> grid 005_0003 [x0 y0 x1 y1]
        python pipeline/sanborn_trace_newcounties.py <town> refine|georef|extract|overlay 005_0003
        python pipeline/sanborn_trace_newcounties.py <town> partner 004_0003 005   # which sheet of volume 005 matches
        python pipeline/sanborn_trace_newcounties.py <town> register 004_0003 005_0004
        python pipeline/sanborn_trace_newcounties.py <town> assemble|check|tables
<town> = santa_rosa | vallejo | napa | santa_cruz | petaluma | watsonville | benicia. Keys are <LOC item suffix>_<sheet>,
e.g. 005_0003 = sanborn00838_005 (Santa Rosa, 1908) sheet 3. Downloads go to data/raw/sanborn_loc/newcounties/<town>/
(scans can be deleted after tracing: the control files hold the refined pixels), intermediates to
data/interim/sanborn_newcounties/<town>/, control to data/manual/sanborn/control/<town>/.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import sanborn_trace_peninsula as P  # noqa: E402

E, W = P.E, P.W
RY = ROOT / "data/raw/region_years"
CITIES = {
    "santa_rosa": {
        "loc": "00838", "area": "santa_rosa_downtown",
        "volumes": {"004": (1904, "Dec 1904"), "005": (1908, "1908"), "006": (1950, "1908 - 1950 (corrected to 1950)")},
        "parcels": RY / "sonoma_county/sonoma_county.parquet", "pid": "APN",
        "bbox": (-122.730, 38.430, -122.700, 38.450),
        "awnings": ("004",),  # the Dec 1904 sheets draw the wooden sidewalk awnings (yellow strips in the street)
        "fireproof_years": (1908, 1950),
    },
    "vallejo": {
        "loc": "00905", "area": "vallejo_downtown",
        "volumes": {"003": (1901, "Jul 1901"), "004": (1919, "Mar 1919"), "005": (1950, "1919 - Mar 1950 (corrected to Mar 1950)")},
        "parcels": RY / "solano_county/solano_county.parquet", "pid": "parcelid",
        "bbox": (-122.275, 38.090, -122.240, 38.115),
    },
    "napa": {
        "loc": "00707", "area": "napa_downtown",
        "volumes": {"003": (1901, "Jun 1901"), "004": (1910, "Oct 1910")},
        "parcels": RY / "napa_county/napa_county.parquet", "pid": "ASMT",
        "bbox": (-122.300, 38.285, -122.270, 38.310),
    },
    "santa_cruz": {
        "loc": "00833", "area": "santa_cruz_downtown",
        "volumes": {"003": (1892, "Jul 1892"), "004": (1905, "1905")},
        "parcels": RY / "santa_cruz_parcels/santa_cruz_parcels.parquet", "pid": "APN",
        "bbox": (-122.040, 36.955, -122.010, 36.985),
    },
    "petaluma": {
        "loc": "00756", "area": "petaluma_downtown",
        "volumes": {"004": (1906, "Nov 1906"), "005": (1910, "Nov 1910")},
        "parcels": RY / "sonoma_county/sonoma_county.parquet", "pid": "APN",
        "bbox": (-122.655, 38.225, -122.625, 38.245),
    },
    "watsonville": {
        "loc": "00921", "area": "watsonville_downtown",
        "volumes": {"004": (1902, "Dec 1902"), "005": (1908, "Jul 1908"), "006": (1920, "Dec 1920"), "007": (1962, "1920 - Dec 1962")},
        "parcels": RY / "santa_cruz_parcels/santa_cruz_parcels.parquet", "pid": "APN",
        "bbox": (-121.775, 36.900, -121.745, 36.920),
    },
    "benicia": {
        "loc": "00417", "area": "benicia_downtown",
        "volumes": {"003": (1899, "Jun 1899"), "004": (1913, "Aug 1913")},
        "parcels": RY / "solano_county/solano_county.parquet", "pid": "parcelid",
        "bbox": (-122.175, 38.040, -122.145, 38.060),
    },
}
P.CITIES.update(CITIES)


def setup(city):
    """point the eastbay / waterfront / peninsula module globals at this town (as P.setup, with this tool's folders)."""
    c = CITIES[city]
    P.CITY_NAME = city
    E.RAW = ROOT / "data/raw/sanborn_loc/newcounties" / city
    E.INTERIM = ROOT / "data/interim/sanborn_newcounties" / city
    E.CONTROL = ROOT / "data/manual/sanborn/control" / city
    E.SCRATCH = Path(os.environ.get("SANBORN_SCRATCH", str(E.INTERIM / "scratch")))
    E.CITY = c["loc"]
    E.VOLUMES = c["volumes"]
    E.EDITION_1950 = ()
    E.PARCELS = c["parcels"]
    E.BUILDINGS = P.OV / "region4_building.parquet"
    E.BBOX = c["bbox"]
    E.ALIASES = dict(c.get("aliases", {}))
    E.AREAS.clear()
    E._roads = E._blocks = None
    W.RAW, W.INTERIM, W.CONTROL = E.RAW, E.INTERIM, E.CONTROL
    W.EDITION_1950 = ()
    W._index = None
    E.INTERIM.mkdir(parents=True, exist_ok=True)
    E.CONTROL.mkdir(parents=True, exist_ok=True)
    E.RAW.mkdir(parents=True, exist_ok=True)
    E.load_areas()
    al = E.CONTROL / "aliases.json"  # street names on the sheets -> today's names (Overture)
    if al.exists():
        E.ALIASES.update(json.load(open(al)))
    return c


def parcel_blocks():
    """blocks = connected unions of today's parcels in the town box (EPSG:32610); the parcel-id column is the county's."""
    if E._blocks is None:
        import geopandas as gpd
        import shapely
        from shapely.strtree import STRtree
        cache = E.INTERIM / "parcel_blocks.parquet"
        if cache.exists():
            b = gpd.read_parquet(cache)
        else:
            g = E._read_bbox(E.PARCELS, [CITIES[P.CITY_NAME]["pid"]], 20000).to_crs(32610)
            g = g[g.geometry.notna() & (g.geometry.area > 1)]
            u = shapely.buffer(shapely.union_all(shapely.buffer(shapely.make_valid(g.geometry.values), 0.4, join_style="mitre")), -0.4, join_style="mitre")
            b = gpd.GeoDataFrame(geometry=[p for p in getattr(u, "geoms", [u]) if p.area > 50], crs=32610)
            b.to_parquet(cache)
        E._blocks = (list(b.geometry.values), STRtree(list(b.geometry.values)))
    return E._blocks


E.parcel_blocks = parcel_blocks


def normalise(raw, out, target=(238, 234, 214)):
    """the LOC scans of these volumes are dark (paper ~ (132, 130, 112) on Santa Rosa 1908): a per-channel gain brings
    the paper to the cream of the plates the colour thresholds were tuned on."""
    from PIL import Image
    a = np.asarray(Image.open(raw).convert("RGB")).astype(np.float32)
    g = a.mean(axis=2)
    core = a[g.shape[0] // 6: -g.shape[0] // 6, g.shape[1] // 6: -g.shape[1] // 6].reshape(-1, 3)
    gc = core.mean(axis=1)
    paper = core[(gc > np.percentile(gc, 55)) & (gc < np.percentile(gc, 97))]
    med = np.median(paper if len(paper) else core, axis=0)
    gain = np.asarray(target, np.float32) / np.maximum(med, 1)
    if np.all(np.abs(gain - 1) < 0.04):
        gain[:] = 1
    Image.fromarray(np.clip(a * gain, 0, 255).astype(np.uint8)).save(out, quality=93)
    return gain


_W_image = W.image


def image(key, pct=25):
    """the IIIF image of a sheet (downloaded once), brightness / white-balance normalised (INTERIM/<key>_<pct>n.jpg)."""
    import time
    key = key[:8]
    out = E.INTERIM / f"{key}_{pct}n.jpg"
    if out.exists() and out.stat().st_size > 10000:
        return out
    from PIL import Image
    raw = E.RAW / f"{key}_{pct}.jpg"
    for k in range(4):
        if not (raw.exists() and raw.stat().st_size > 10000):
            E.index()
            raw = _W_image(key, pct)
            time.sleep(1.5)  # be polite to tile.loc.gov
        try:
            Image.open(raw).load()  # a transfer cut short leaves a truncated JPEG
            break
        except Exception:
            raw.unlink(missing_ok=True)
            time.sleep(4 + 4 * k)
    normalise(raw, out)
    return out


E.image = image
W.image = image


def sift(key, mask_box=None):
    import cv2
    from PIL import Image
    A = cv2.GaussianBlur(np.asarray(Image.open(E.image(key[:8])).convert("L")), (3, 3), 0)
    m = None
    if mask_box:
        m = np.zeros(A.shape, np.uint8)
        m[mask_box[1]:mask_box[3], mask_box[0]:mask_box[2]] = 255
    return cv2.SIFT_create(nfeatures=12000).detectAndCompute(A, m)


def match(fa, fb, bin_px=24, scale0=1.0):
    """SIFT matches between two states of one plate: the pairs whose displacement falls in the fullest 3 x 3 cells of
    a displacement histogram (a corrected plate is shifted by tens of pixels, hardly scaled or rotated; without this
    vote RANSAC finds degenerate transforms on sheets whose buildings all changed), then a RANSAC similarity.
    -> (inliers, T, rms_px) or (0, None, 0)."""
    import cv2
    (ka, da), (kb, db) = fa, fb
    good = [m[0] for m in cv2.BFMatcher(cv2.NORM_L2).knnMatch(da, db, k=2) if len(m) == 2 and m[0].distance < 0.8 * m[1].distance]
    if len(good) < 12:
        return 0, None, 0
    pa = np.float32([ka[g.queryIdx].pt for g in good]); pb = np.float32([kb[g.trainIdx].pt for g in good])
    d = np.floor((pb - pa * scale0) / bin_px).astype(int)  # scale0: the two scans differ in resolution
    cells, cnt = np.unique(d, axis=0, return_counts=True)
    c = cells[int(np.argmax(cnt))]
    sel = (np.abs(d - c) <= 1).all(axis=1)
    if sel.sum() < 12:
        return int(sel.sum()), None, 0
    T, inl = cv2.estimateAffinePartial2D(pa[sel], pb[sel], method=cv2.RANSAC, ransacReprojThreshold=3.0, maxIters=5000, confidence=0.999)
    if T is None:
        return 0, None, 0
    inl = inl.ravel().astype(bool)
    r = (pa[sel][inl] @ T[:, :2].T + T[:, 2]) - pb[sel][inl]
    return int(inl.sum()), T, float(np.sqrt((r ** 2).sum(axis=1).mean()))


def partner(src, vol, sheets=None, feats=None):
    """the sheets of volume `vol` that show the same plate as `src` (another edition), best first ->
    [(inliers, key, scale, rotation_deg, rms_px)]."""
    import math
    fa = sift(src)
    out = []
    for rec in E.index()[vol]:
        sh = rec["id"].split("-")[-1]
        if not sh.isdigit() or (sheets and int(sh) not in sheets):
            continue
        dst = f"{vol}_{sh}"
        fb = feats[dst] if feats and dst in feats else sift(dst)
        if fb[1] is None or len(fb[1]) < 50:
            continue
        n, T, rms = match(fa, fb)
        if T is not None:
            out.append((n, dst, round(math.hypot(T[0, 0], T[1, 0]), 4), round(math.degrees(math.atan2(T[1, 0], T[0, 0])), 2), round(rms, 2)))
    return sorted(out, reverse=True)


def register(src, dst, scale0=1.0):
    """W.register with the displacement vote of `match`: writes the control file of `src` (registered_to dst)."""
    n, T, rms = match(sift(src), sift(dst), scale0=scale0)
    if T is None:
        raise ValueError(f"{src} does not match {dst}")
    json.dump({"registered_to": dst, "T": T.tolist(), "reg_inliers": n, "reg_rms_px": round(rms, 2)}, open(E.CONTROL / f"{src}.json", "w"), indent=1)
    E.log(src, "->", dst, f"inliers {n} rms {rms:.2f} px")
    return n, rms


def property_lines_x(pa, pb, reach=22):
    """crossing of two of today's property lines, each given by a UTM point on (near) it: the boundary of the nearest
    parcel block within `reach` m of the point's foot on it is fitted by a straight line (a frontage that survives
    where the street it faced has no name in Overture any more, or the other frontage of the block is gone)."""
    from shapely.geometry import Point
    geoms, tree = parcel_blocks()
    lines = []
    for p in (pa, pb):
        pt = Point(*p)
        cand = [geoms[i] for i in tree.query(pt.buffer(15))]
        if not cand:
            raise ValueError(f"no parcel block within 15 m of {p}")
        ring = min(cand, key=lambda g: g.exterior.distance(pt)).exterior
        s0 = ring.project(pt)
        ss = np.arange(s0 - reach, s0 + reach + 0.01, 0.5) % ring.length
        q = np.array([ring.interpolate(s).coords[0][:2] for s in ss])
        m = q.mean(axis=0)
        d = np.linalg.svd(q - m)[2][0]
        off = np.abs((q - m) @ np.array([-d[1], d[0]]))
        if off.max() > 1.5:  # the stretch turns a corner: keep the part in line with the foot point
            keep = off <= max(0.6, np.median(off) * 2)
            m = q[keep].mean(axis=0)
            d = np.linalg.svd(q[keep] - m)[2][0]
        lines.append((m, d))
    if abs(lines[0][1] @ lines[1][1]) > 0.9:
        raise ValueError("property lines are parallel")
    return E.line_x(lines[0], lines[1])


_P_world_of = E.world_of


def world_of(c):
    """adds `pl`: [[E, N], [E, N]] - the crossing of the two property lines of today's parcel blocks nearest to the two
    UTM points (see property_lines_x)."""
    if "pl" in c:
        return property_lines_x(c["pl"][0], c["pl"][1], c.get("reach", 22)), c.get("label", "property lines " + c.get("corner", ""))
    return _P_world_of(c)


E.world_of = world_of
W.world_of = world_of


def spec(key, s):
    """E.spec with per-corner control overrides: a block may carry "ctl": {"NE": {control entry}} - e.g. {"tie": key of
    a georeferenced neighbour sheet, "px_other": [x, y], "tie_block": name}, {"pl": [[E, N], [E, N]]}, {"la": .., "lb":
    .., "off": ..} - replacing the property-corner (`pc`) rule for that corner (which may be listed under "skip")."""
    ctl = {n: b.pop("ctl") for n, b in s["blocks"].items() if "ctl" in b}
    for n, b in s["blocks"].items():  # an overridden corner is built like the others, then rewritten
        b["skip"] = [c for c in b.get("skip", []) if c not in ctl.get(n, {})]
    cfg = E.spec(key, s)
    for b in cfg["blocks"]:
        for c in b["corners"]:
            o = ctl.get(b["name"], {}).get(c["corner"])
            if o:
                for k in ("pc", "oc", "w"):
                    c.pop(k, None)
                c.update(o)
    json.dump(cfg, open(E.CONTROL / f"{key}.json", "w"), indent=1)
    return cfg


def run(key, s=None, stages=("refine", "georef", "extract", "overlay")):
    """one new sheet from its block spec (see spec) to footprints + a scratch overlay."""
    if s is not None:
        spec(key, s)
    if "refine" in stages:
        E.refine(key)
    if "georef" in stages:
        P._georef(key)
    if "extract" in stages:
        P.extract(key)
    if "overlay" in stages:
        return E.overlay(key, scale=float(os.environ.get("SCALE", 0.6)))


def assemble():
    """P.assemble, then this tool's per-block rules:
      * `block_cap` {block: "medium" | "low"} of a sheet's control file (inherited by the editions registered onto it):
        blocks placed by a neighbour's fit (no control of their own today: the mall, the freeway) are capped;
      * volumes listed under the town's `awnings` draw the wooden sidewalk awnings as yellow strips outside the block
        line: footprints are clipped to their block and strips lying in the street are dropped."""
    import shapely
    from pyproj import Transformer
    from shapely.geometry import Polygon, mapping, shape
    P.assemble()
    c = CITIES[P.CITY_NAME]
    rank = {"high": 0, "medium": 1, "low": 2}
    to_ll = Transformer.from_crs(32610, 4326, always_xy=True)
    for (area, year), keys in sorted(E.AREAS.items()):
        f = E.OUT / f"{area}_{year}.geojson"
        fc = json.load(open(f))
        caps, clip = {}, {}
        for key in keys:
            cfg = json.load(open(E.CONTROL / f"{key}.json"))
            while "registered_to" in cfg:
                cfg = json.load(open(E.CONTROL / f"{cfg['registered_to']}.json"))
            caps[key] = cfg.get("block_cap", {})
            if key.split("_")[0] in c.get("awnings", ()):
                G = json.load(open(E.INTERIM / f"{key}.M.json"))
                for b in G.get("blocks", []):
                    x0, y0, x1, y1 = b["rect_px"]
                    q = W.apply(np.array(b["M"]), [[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
                    clip[(key, b["name"])] = Polygon(np.column_stack(to_ll.transform(q[:, 0], q[:, 1]))).buffer(4e-6)
        out, n_cap, n_drop = [], 0, 0
        for ft in fc["features"]:
            pr = ft["properties"]
            key = pr["id"].rsplit("_", 1)[0]
            blk = pr["georef"][6:] if pr["georef"].startswith("block ") else None
            cap = caps.get(key, {}).get(blk)
            if cap and rank[pr["confidence"]] < rank[cap]:
                pr["confidence"] = cap
                n_cap += 1
            if pr["sanborn_colour"] == "fireproof" and year in c.get("fireproof_years", ()):
                pr["material"] = "concrete"  # brown = "fire proof construction" on this edition's key (not adobe)
            if (key, blk) in clip:
                g = shape(ft["geometry"])
                gi = g.intersection(clip[(key, blk)])
                if gi.geom_type != "Polygon":
                    polys = [q for q in getattr(gi, "geoms", []) if q.geom_type == "Polygon"]
                    gi = max(polys, key=lambda q: q.area) if polys else None
                if gi is None or gi.area < 0.5 * g.area or gi.area < 6e-10:
                    n_drop += 1
                    continue
                if gi.area < 0.995 * g.area:
                    pr["area_m2"] = round(pr["area_m2"] * gi.area / g.area, 1)
                    ft["geometry"] = json.loads(json.dumps(mapping(shapely.set_precision(gi, 1e-7))), parse_float=lambda v: round(float(v), 7))
            out.append(ft)
        fc["features"] = out
        json.dump(fc, open(f, "w"))
        cf = E.OUT / f"{area}_coverage.geojson"
        cov = json.load(open(cf))
        for ft in cov["features"]:
            if ft["properties"]["map_year"] == year:
                ft["properties"]["features"] = len(out)
        json.dump(cov, open(cf, "w"))
        E.log(area, year, len(out), "features after block rules:", n_cap, "capped,", n_drop, "awning strips dropped")


def set_areas(d):
    """control/<town>/areas.json: {"<area>_<year>": [keys]}"""
    p = E.CONTROL / "areas.json"
    cur = json.load(open(p)) if p.exists() else {}
    cur.update(d)
    json.dump(cur, open(p, "w"), indent=1)
    E.AREAS.clear()
    E.load_areas()


def main():
    city = sys.argv[1]
    setup(city)
    E.index()
    stage = sys.argv[2] if len(sys.argv) > 2 else "all"
    if stage == "grid":
        k = sys.argv[3]
        box = tuple(int(v) for v in sys.argv[4:8]) if len(sys.argv) >= 8 else None
        print(E.grid(k, box, step=int(os.environ.get("STEP", 100)), scale=float(os.environ.get("SCALE", 1.0))))
        return
    if stage == "lines":
        for ln in P.solid_lines(sys.argv[3], int(os.environ.get("MINLEN", 120))):
            print(*ln)
        return
    if stage == "tables":
        print(P.tables())
        return
    if stage == "sheets":
        for vol, recs in E.index().items():
            print(vol, E.VOLUMES.get(vol), [r["id"].split("-")[-1] for r in recs])
        return
    if stage == "partner":
        for r in partner(sys.argv[3], sys.argv[4], [int(v) for v in sys.argv[5:]] or None)[:4]:
            print(*r)
        return
    if stage == "register":
        register(sys.argv[3], sys.argv[4], float(sys.argv[5]) if len(sys.argv) > 5 else 1.0)
        return
    keys = sys.argv[3:] or E.all_keys()
    if stage in ("all", "fetch"):
        for k in keys:
            print(E.image(k, int(os.environ.get("PCT", 25))))
    if stage == "refine":
        for k in keys:
            E.refine(k)
    if stage in ("all", "georef"):
        for k in E.base_first(keys):
            P._georef(k)
    if stage in ("all", "extract"):
        for k in keys:
            P.extract(k)
    if stage == "overlay":
        for k in keys:
            print(E.overlay(k, scale=float(os.environ.get("SCALE", 0.5))))
    if stage in ("all", "assemble"):
        assemble()
    if stage in ("all", "check"):
        print(P.check())


if __name__ == "__main__":
    main()
