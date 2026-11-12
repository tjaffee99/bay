"""Houses of 1856 from a U.S. Coast Survey plane-table sheet (T-sheet), and the built-up snapshot they make.

  python -I tsheet_houses.py oakland_1856        (run from data/manual/region_extents; needs the terrain grids)

T-592, "San Francisco Bay, California, Plane-Table Sheet No. XXIV", 1:10,000, 1856 (A. D. Bache, Superintendent;
NOAA Historical Map & Chart Collection, public domain) draws Oakland, Clinton / San Antonio (Brooklyn) and the
Encinal house by house: every building is a solid black block, lots are dashed fence lines, oaks are clover signs.

1. Georeference: the sheet carries the graticule of the old "North American datum" as blue crosses and, at
   122 15' / 37 47', a 1933 pencil tick "N.A. (1927) approx." 47 px west of it. An affine through four crosses
   (residual < 2 m, 0.85 m per pixel), shifted by that tick, gives NAD27 positions; NAD27 -> WGS84 by PROJ. Checked on
   today's street grid: the houses of 1856 avoid today's streets best with a further shift of (-6 m, -2 m), applied.
2. Houses: black ink (red channel < 150, not the blue pencil), opened by 5 px so line work drops out; a block is kept
   when it is compact (short side >= 7 px = 6 m, aspect <= 4, fill >= 0.5), black rather than brown (the sheet is
   foxed: median R <= 108, R - B <= 43), and either stands free or is large (a waterfront shed touching the shoreline).
   Dropped: rows of dashes, lettering (the letters of OAKLAND and BROOKLYN, road and creek names, by position), marks
   in hatched marsh, anything on tide flat, marsh or water of the c.1800 cover, the title and the table of areas.
3. Output: data/manual/tsheets/<town>_<year>.geojson (one polygon per house; a rectangle when the block is one, else
   its outline) and the snapshot <town>_<year>.geojson = the houses grown by 12 m; coverage = the sheet's land inside
   the town (a lot outside the snapshot had no building in 1856).
Position accuracy about 10 m; the smallest sheds and a few houses fused with fence or shore lines are missed.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extents as E  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
OUT_HOUSES = ROOT / "data" / "manual" / "tsheets"

CFG = {
    "oakland_1856": dict(
        town="oakland", year=1856, sheet="T00592-00-1856",
        title="U.S. Coast Survey, San Francisco Bay, California, Plane-Table Sheet No. XXIV (Register No. 592), 1:10,000, 1856",
        page="https://historicalcharts.noaa.gov/search.php",
        url="https://historicalcharts.noaa.gov/includes/downloadsingle.php?filename=T00592-00-1856&fileExt=.jpg",
        # blue crosses of the North American datum graticule: pixel -> (lon, lat)
        crosses=[((10468, 4609), (-122 - 15 / 60, 37 + 47 / 60)), ((9235.3, 5821.2), (-122 - 16 / 60, 37 + 47 / 60)),
                 ((7708.8, 4266.3), (-122 - 16 / 60, 37 + 48 / 60)), ((6474.4, 5468.2), (-122 - 17 / 60, 37 + 48 / 60))],
        nad27_tick=(-47.0, -2.0),          # the 1933 "N.A. (1927) approx." tick relative to the blue cross (px)
        shift=(-6.0, -2.0),                # metres, from the fit on today's street grid
        neat=(585, 665, 15125, 8925),      # neat line (px); boxes that are not map: title, table of areas
        furniture=[(0, 0, 4700, 3700), (12800, 0, 15656, 3500)],
        letters=[(5468, 5395), (5645, 5152), (5855, 4952), (6086, 4793), (6348, 4670), (6650, 4645), (6730, 4665), (6957, 4630),   # O A K L A N D
                 (9241, 3800), (9473, 3618), (9688, 3479), (9943, 3368), (10241, 3279), (10514, 3241), (10764, 3232), (11057, 3264),  # B R O O K L Y N
                 (10548, 3568)],           # a station mark
        labels=[((10518, 3014), (10920, 2639)), ((11560, 3560), (12100, 3440)), ((5662, 2050), (5900, 2412)),
                ((6037, 2275), (6312, 2019)), ((5350, 3162), (5787, 3425))],   # San Antonio Crk., San Jose Road, Peralta Road, South Base, San Pablo Road
        note="every building the plane-table survey of 1856 drew north of San Antonio Creek (Oakland, Clinton, San Antonio); "
             "the town of 1,543 people of the 1860 census"),
}


def georef(c):
    from pyproj import Transformer
    P = np.array([p for p, _ in c["crosses"]], float) + np.array(c["nad27_tick"])
    LL = np.array([q for _, q in c["crosses"]], float)
    A = np.column_stack([P, np.ones(len(P))])
    cx, *_ = np.linalg.lstsq(A, LL[:, 0], rcond=None)
    cy, *_ = np.linalg.lstsq(A, LL[:, 1], rcond=None)
    t1 = Transformer.from_crs(4267, 4326, always_xy=True)
    t2 = Transformer.from_crs(4326, 32610, always_xy=True)

    def px2utm(x, y):
        x = np.asarray(x, float); y = np.asarray(y, float)
        lo, la = t1.transform(cx[0] * x + cx[1] * y + cx[2], cy[0] * x + cy[1] * y + cy[2])
        e, n = t2.transform(lo, la)
        return np.asarray(e) + c["shift"][0], np.asarray(n) + c["shift"][1]
    return px2utm


def run(name):
    import geopandas as gpd
    import rasterio.features as RF
    import shapely
    from PIL import Image
    from scipy import ndimage as ndi
    from scipy.spatial import cKDTree
    from pyproj import Transformer
    c = CFG[name]
    town, year = c["town"], c["year"]
    raw = E.RAW / "tsheets"
    raw.mkdir(parents=True, exist_ok=True)
    jp = raw / f"{c['sheet']}.jpg"
    if not jp.exists() or jp.stat().st_size < 1e6:
        subprocess.run(["curl", "-sS", "-L", "--retry", "3", "-m", "600", "-A", "Mozilla/5.0 (research script)", "-o", str(jp), c["url"]],
                       check=True)
    Image.MAX_IMAGE_PIXELS = None
    rgb = np.asarray(Image.open(jp).convert("RGB")).astype(np.int16)
    R, B = rgb[..., 0], rgb[..., 2]
    ink = (R < 150) & (B - R < 12)
    rl, _ = ndi.label(ink, structure=np.ones((3, 3), bool))
    rdim = np.array([0] + [max(s[0].stop - s[0].start, s[1].stop - s[1].start) for s in ndi.find_objects(rl)])
    opened = ndi.binary_opening(ink, np.ones((5, 5), bool))
    dens = ndi.uniform_filter((ink & ~opened).astype(np.float32), size=121)       # hatched marsh = dense thin strokes
    solid = ndi.binary_fill_holes(ndi.binary_dilation(opened, np.ones((3, 3), bool)) & ink)
    lab, n = ndi.label(solid)
    area = ndi.sum(solid, lab, np.arange(1, n + 1))
    x0, y0, x1, y1 = c["neat"]
    cand = []
    for i, s in enumerate(ndi.find_objects(lab)):
        a = area[i]
        if a < 50 or a > 7000 or max(s[0].stop - s[0].start, s[1].stop - s[1].start) > 230:
            continue
        mm = lab[s] == i + 1
        ys, xs = np.nonzero(mm & ink[s])
        if not len(ys):
            continue
        m = np.pad(mm, 1)
        p = max((shapely.geometry.shape(g) for g, v in RF.shapes(m.astype(np.uint8), mask=m) if v == 1), key=lambda q: q.area)
        p = shapely.affinity.translate(p, s[1].start - 1, s[0].start - 1)
        rect = p.minimum_rotated_rectangle
        cc = np.asarray(rect.exterior.coords)[:4]
        e1, e2 = np.hypot(*(cc[1] - cc[0])), np.hypot(*(cc[2] - cc[1]))
        fill, short, long_ = p.area / max(e1 * e2, 1), min(e1, e2), max(e1, e2)
        ctr = np.asarray(p.centroid.coords[0])
        px = rgb[s][mm]
        free = rdim[rl[s][ys[0], xs[0]]] <= 420
        ok = (short >= 7 and long_ / max(short, 1) <= 4 and fill >= 0.5 and (free or (a >= 140 and fill >= 0.6 and short >= 9))
              and np.median(px[:, 0]) <= 108 and np.median(px[:, 0] - px[:, 2]) <= 43
              and x0 < ctr[0] < x1 and y0 < ctr[1] < y1
              and not any(bx0 < ctr[0] < bx1 and by0 < ctr[1] < by1 for bx0, by0, bx1, by1 in c["furniture"])
              and dens[int(ctr[1]), int(ctr[0])] < 0.16)
        if ok:
            cand.append((p if fill < 0.8 else rect, ctr, a, short, long_))
    C = np.array([k[1] for k in cand])

    def axis(g):
        cc = np.asarray(g.minimum_rotated_rectangle.exterior.coords)[:4]
        v = max(cc[1] - cc[0], cc[2] - cc[1], key=lambda w: np.hypot(*w))
        return v / max(np.hypot(*v), 1e-6)
    small = np.array([i for i, k in enumerate(cand) if k[2] <= 260])
    T = cKDTree(C[small])
    TA = cKDTree(C)
    drop = set()
    for i in small:                                     # dashes of a road casing / fence: 3+ marks along their own axis
        g, _, a, short, long_ = cand[i]
        if long_ / max(short, 1) < 1.5:
            continue
        v = axis(g)
        k = 0
        for j in T.query_ball_point(C[i], 4.5 * long_):
            jj = small[j]
            d = C[jj] - C[i]
            if jj != i and abs(d[0] * v[1] - d[1] * v[0]) < 0.35 * short + 2 and abs(d @ v) > 0.8 * long_ and abs(axis(cand[jj][0]) @ v) > 0.94:
                k += 1
        if k >= 2:
            drop.add(i)
    for i in small:                                     # a line of lettering: 4+ small marks on a line, nothing else around
        nb = [small[j] for j in T.query_ball_point(C[i], 170) if small[j] != i]
        for j in nb:
            v = C[j] - C[i]
            L = np.hypot(*v)
            if L < 12:
                continue
            v = v / L
            on = [i] + [m for m in nb if abs((C[m] - C[i])[0] * v[1] - (C[m] - C[i])[1] * v[0]) <= 4.5]
            if len(on) < 4 or np.diff(np.sort([(C[m] - C[i]) @ v for m in on])).max() > 75:
                continue
            around = set()
            for m in on:
                around.update(TA.query_ball_point(C[m], 110))
            if len(around - set(on)) <= 0.35 * len(on):
                drop.update(on)

    def lettering(ctr):
        if any(np.hypot(ctr[0] - lx, ctr[1] - ly) < 58 for lx, ly in c["letters"]):
            return True
        for a, b in c["labels"]:
            a = np.array(a, float); b = np.array(b, float)
            v = b - a
            L = np.hypot(*v)
            v /= L
            t = (ctr - a) @ v
            if -40 <= t <= L + 40 and abs((ctr - a)[0] * v[1] - (ctr - a)[1] * v[0]) <= 42:
                return True
        return False
    px2utm = georef(c)
    # c.1800 cover of the terrain (detail grid): nothing on tide flat, marsh or water
    sys.path.insert(0, str(ROOT / "pipeline"))
    from terrain_grid import grid_def
    import terrain_tiles as TT
    g = grid_def("detail")
    cov = np.load(ROOT / "data" / "interim" / "grid_detail_covers.npy", mmap_mode="r")[0]
    wet = np.isin(np.asarray(cov), list(TT.WET))
    tm = Transformer.from_crs(32610, 3857, always_xy=True)
    clip = E.town_clip(town)
    rows = []
    for i, (geom, ctr, a, short, long_) in enumerate(cand):
        if i in drop or lettering(ctr):
            continue
        xy = np.asarray(geom.exterior.coords)
        e, n_ = px2utm(xy[:, 0], xy[:, 1])
        poly = shapely.Polygon(np.c_[e, n_]).buffer(0)
        if poly.is_empty or not poly.centroid.within(clip):
            continue
        X, Y = tm.transform(poly.centroid.x, poly.centroid.y)
        cc, rr = int(round((X - g["X0"]) / g["res"])), int(round((g["Y0"] - Y) / g["res"]))
        if wet[rr - 1:rr + 2, cc - 1:cc + 2].sum() >= 7:
            continue
        rows.append({"geometry": poly, "px": [round(float(ctr[0])), round(float(ctr[1]))]})
    gdf = gpd.GeoDataFrame(rows, crs=32610)
    gdf["id"] = [f"t592:{i:04d}" for i in range(len(gdf))]
    gdf["map_year"] = year
    gdf["area_m2"] = gdf.area.round(1)
    OUT_HOUSES.mkdir(parents=True, exist_ok=True)
    ll = gdf.to_crs(4326)
    feats = [{"type": "Feature", "properties": {"id": i, "map_year": int(year), "area_m2": float(a), "px": list(px)},
              "geometry": shapely.geometry.mapping(shapely.set_precision(gm, 1e-7))}
             for i, a, px, gm in zip(ll.id, ll.area_m2, ll.px, ll.geometry)]
    (OUT_HOUSES / f"{town}_{year}.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "name": f"{town}_{year}", "source": "uscs_tsheet_t592", "sheet": c["title"],
         "source_url": c["url"], "licence": "public domain (U.S. Coast Survey; NOAA Historical Map & Chart Collection)",
         "note": "px = centre of the building symbol on the full-size scan; outlines are good to about 10 m",
         "features": feats}, separators=(",", ":")))
    # the snapshot: houses grown by 12 m; coverage: the sheet's land inside the town
    u = shapely.union_all(gdf.geometry.buffer(12, quad_segs=3).values).intersection(clip).simplify(1.0)
    nx = [x0, x1, x1, x0]
    ny = [y0, y0, y1, y1]
    e, n_ = px2utm(nx, ny)
    sheet = shapely.Polygon(np.c_[e, n_])
    for bx0, by0, bx1, by1 in c["furniture"]:
        e, n_ = px2utm([bx0, bx1, bx1, bx0], [by0, by0, by1, by1])
        sheet = sheet.difference(shapely.Polygon(np.c_[e, n_]))
    covg = sheet.intersection(clip)
    props = {"town": town, "year": int(year), "kind": "buildings", "source": f"noaa_hmcc:{c['sheet']}", "source_url": f"{c['page']} {c['url']}",
             "confidence": "high",
             "note": f"{c['note']} | {c['title']}: {len(gdf)} buildings read from the sheet (data/manual/tsheets/{town}_{year}.geojson), "
                     f"each grown by 12 m | area read: {round(covg.area / 1e6, 2)} km2 (coverage.geojson); inside it a spot outside "
                     f"this snapshot had no building in {year}",
             "edition_years": [int(year)], "map_years": [int(year)], "method": "building symbols of the plane-table sheet, buffered 12 m",
             "area_km2": round(u.area / 1e6, 3), "n_buildings": int(len(gdf))}
    fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": props,
                                                     "geometry": shapely.geometry.mapping(shapely.set_precision(E.to_ll(u), 1e-7))}]}
    (E.OUT / f"{town}_{year}.geojson").write_text(json.dumps(fc, separators=(",", ":")))
    cv = {"town": town, "year": int(year), "sheets": [f"noaa:{c['sheet']}"], "area_km2": round(covg.area / 1e6, 3)}
    (E.INT / f"coverage_{town}_{year}.json").write_text(json.dumps({"props": cv, "geom": shapely.geometry.mapping(E.to_ll(covg))}))
    E.export_coverage()
    print(f"{town} {year}: {len(gdf)} houses, {round(float(gdf.area.sum()))} m2 of roof; snapshot {props['area_km2']} km2; coverage {cv['area_km2']} km2")


if __name__ == "__main__":
    run(sys.argv[1])
