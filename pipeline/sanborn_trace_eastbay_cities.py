"""Trace vanished buildings of Berkeley, Alameda and Richmond from Library of Congress Sanborn maps.

Same method, schema and outputs as pipeline/sanborn_trace_eastbay.py (Oakland; README_oakland.md), which this module
configures per city (the Oakland module reads its paths, LOC ids and street aliases from module globals, which are set
here before any stage runs):

  berkeley   sanborn00419: 1894 (one volume, 14 sheets) and 1911 (vols. 1-2). The 1917 additional sheets and the 1929
             / 1950 editions are listed on loc.gov but not digitized.
  alameda    sanborn00374: 1897, 1948, 1950 (the 1950 volume is the 1948 plates with paste-over corrections).
  richmond   sanborn00787: 1903, 1905, 1909, 1916. The 1930 and 1950 / 1951 editions are not digitized.

Control geometry, as for Oakland: Overture road segments (here roads_region.parquet = motorway -> tertiary plus
roads_local.parquet = residential / unclassified / service / living street, both release 2026-10-21.0, read within the
city box) for street crossings and lines; today's parcel polygons (Alameda County 2021 public copy for Berkeley and
Alameda, Contra Costa County CCMAP Assessment Parcels for Richmond) for property lines.

Outputs (data/manual/sanborn/): <city>_<area>_<year>.geojson, <city>_<area>_coverage.geojson,
<city>_<area>_<year>_tracks.geojson; control in data/manual/sanborn/control/<city>/; README_<city>.md.

Usage:  python pipeline/sanborn_trace_eastbay_cities.py <city> all             # fetch + georef + extract + tracks + assemble
        python pipeline/sanborn_trace_eastbay_cities.py <city> georef 002_0012 # one stage, some sheets
        python pipeline/sanborn_trace_eastbay_cities.py <city> fetch 002_0012
        python pipeline/sanborn_trace_eastbay_cities.py <city> grid 002_0012 [x0 y0 x1 y1]
        python pipeline/sanborn_trace_eastbay_cities.py <city> refine 002_0012
        python pipeline/sanborn_trace_eastbay_cities.py <city> register 003_0012 002_0012
        python pipeline/sanborn_trace_eastbay_cities.py <city> mosaic|overlay 002_0012
        python pipeline/sanborn_trace_eastbay_cities.py <city> keymap <vol> <sheet id> [pct]   # index / key map image
Keys are <LOC item suffix>_<sheet>, e.g. 002_0012 = sanborn00419_002 (Berkeley 1911 vol. 1) sheet 12.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import sanborn_trace_eastbay as E  # noqa: E402
import sanborn_trace_waterfront as W  # noqa: E402

OVERTURE = ROOT / "data/raw/overture/2026-10-21.0"
CITIES = {
    "berkeley": {
        "loc": "00419",
        "volumes": {"001": (1894, "1894"), "002": (1911, "1911 Vol. 1"), "003": (1911, "1911 Vol. 2")},
        "edition_1950": (),
        "parcels": ROOT / "data/raw/region_years/alameda_county_2021/alameda_county_2021.parquet",
        "parcel_cols": ["APN"],
        "bbox": (-122.325, 37.845, -122.235, 37.895),
        "aliases": {
            "first street": "1st street", "second street": "2nd street", "third street": "3rd street",
            "fourth street": "4th street", "fifth street": "5th street", "sixth street": "6th street",
            "seventh street": "7th street", "eighth street": "8th street", "ninth street": "9th street",
            "tenth street": "10th street",
            "shattuck": "shattuck avenue", "university": "university avenue", "san pablo": "san pablo avenue",
            "telegraph": "telegraph avenue", "college": "college avenue", "grove street": "martin luther king junior way",
            "grove": "martin luther king junior way", "dwight way": "dwight way", "dwight": "dwight way",
            "bancroft": "bancroft way", "bancroft way": "bancroft way", "allston": "allston way", "addison": "addison street",
            "center": "center street", "kittredge": "kittredge street", "durant": "durant avenue", "channing": "channing way",
            "haste": "haste street", "allston way": "allston way", "milvia": "milvia street", "oxford": "oxford street",
            "berkeley way": "berkeley way", "hearst": "hearst avenue", "delaware": "delaware street", "virginia": "virginia street",
            "university ave": "university avenue", "ellsworth": "ellsworth street", "fulton": "fulton street",
            "dana": "dana street", "bowditch": "bowditch street", "union": "union street",
            "bristol": "hearst avenue",  # West Berkeley's Bristol St is today's Hearst Ave
        },
        "wide_streets": {"shattuck avenue": 32},
        "railroad_streets": [],
    },
    "alameda": {
        "loc": "00374",
        "volumes": {"001": (1897, "1897"), "002": (1948, "1948"), "003": (1950, "1948-1950 (corrected to 1950)")},
        "edition_1950": ("002", "003"),
        "parcels": ROOT / "data/raw/region_years/alameda_county_2021/alameda_county_2021.parquet",
        "parcel_cols": ["APN"],
        "bbox": (-122.345, 37.745, -122.220, 37.800),
        "aliases": {
            "first street": "1st street", "second street": "2nd street", "third street": "3rd street",
            "fourth street": "4th street", "fifth street": "5th street", "sixth street": "6th street",
            "seventh street": "7th street", "eighth street": "8th street", "ninth street": "9th street",
            "park": "park street", "webster": "webster street", "santa clara": "santa clara avenue",
            "central": "central avenue", "lincoln": "lincoln avenue", "encinal": "encinal avenue",
            "pacific": "pacific avenue", "buena vista": "buena vista avenue", "atlantic": "atlantic avenue",
            "oak": "oak street", "walnut": "walnut street", "chestnut": "chestnut street", "willow": "willow street",
            "everett": "everett street", "broadway": "broadway", "grand": "grand street", "paru": "paru street",
            "st charles": "saint charles street", "schiller": "schiller street", "morton": "morton street",
            "taylor": "taylor avenue", "railroad avenue": "lincoln avenue",
        },
        "railroad_streets": [],
    },
    "richmond": {
        "loc": "00787",
        "volumes": {"001": (1903, "1903"), "002": (1905, "1905"), "003": (1909, "1909"), "004": (1916, "1916")},
        "edition_1950": (),
        "parcels": ROOT / "data/raw/region_years/contra_costa_ccmap/contra_costa_ccmap.parquet",
        "parcel_cols": ["APN"],
        "bbox": (-122.405, 37.900, -122.315, 37.960),
        "aliases": {
            "first street": "1st street", "second street": "2nd street", "third street": "3rd street",
            "fourth street": "4th street", "fifth street": "5th street", "sixth street": "6th street",
            "seventh street": "7th street", "eighth street": "8th street", "ninth street": "9th street",
            "tenth street": "10th street", "eleventh street": "11th street", "twelfth street": "12th street",
            "macdonald": "macdonald avenue", "macdonald avenue": "macdonald avenue", "nevin": "nevin avenue",
            "barrett": "barrett avenue", "bissell": "bissell avenue", "ohio": "ohio avenue", "cutting": "cutting boulevard",
            "washington": "washington avenue", "park place": "park place", "richmond": "west richmond avenue",
        },
        "railroad_streets": [],
    },
}

CITY_NAME = None


def configure(city):
    """point the Oakland module (and through it the SF waterfront module) at one city."""
    global CITY_NAME
    c = CITIES[city]
    CITY_NAME = city
    E.RAW = ROOT / f"data/raw/sanborn_loc_{city}"
    E.INTERIM = ROOT / f"data/interim/sanborn_{city}"
    E.CONTROL = ROOT / f"data/manual/sanborn/control/{city}"
    E.SCRATCH = Path(os.environ.get("SANBORN_SCRATCH", str(E.INTERIM / "scratch")))
    W.RAW, W.INTERIM, W.CONTROL = E.RAW, E.INTERIM, E.CONTROL
    E.CITY = c["loc"]
    E.VOLUMES = c["volumes"]
    E.EDITION_1950 = c["edition_1950"]
    W.EDITION_1950 = c["edition_1950"]
    E.PARCELS = c["parcels"]
    E.BBOX = c["bbox"]
    E.ALIASES = c["aliases"]
    E.AREAS.clear()
    E._roads = None
    E._blocks = None
    W._index = None
    E.INTERIM.mkdir(parents=True, exist_ok=True)
    E.CONTROL.mkdir(parents=True, exist_ok=True)
    E.load_areas()
    return c


def log(*a):
    print(f"sanborn_{CITY_NAME}:", *a, flush=True)


def roads():
    """Overture road segments in the city box (roads_region: motorway -> tertiary, roads_local: residential / service
    / unclassified / living street), EPSG:32610, with a normalised name; cached per city."""
    import geopandas as gpd
    import pandas as pd
    if E._roads is None:
        cache = E.INTERIM / "roads.parquet"
        if cache.exists():
            g = gpd.read_parquet(cache)
        else:
            parts = [E._read_bbox(OVERTURE / f, ["id", "class", "name"]) for f in ("roads_region.parquet", "roads_local.parquet")]
            g = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), geometry="geometry", crs=4326)
            g = g[g.geometry.geom_type.isin(["LineString", "MultiLineString"])].copy()
            g = g.to_crs(32610)
            g.to_parquet(cache)
        g = g[~g["class"].isin(["footway", "cycleway", "path", "steps", "pedestrian", "track"])].copy()
        g["key"] = g["name"].map(E.norm_name)
        E._roads = g
    return E._roads


E.roads = roads

_property_corner = E.property_corner


def property_corner(a, b, q, near=None, reach=(18, 75), R=150):
    """E.property_corner, but a street listed in CITIES[city]['wide_streets'] may have its property line up to that
    many metres from the centreline (Berkeley's Shattuck Ave is ~150 ft wide south of Center St; the Oakland tool
    rejects offsets > 24 m as superblocks / plazas)."""
    wide = CITIES[CITY_NAME].get("wide_streets", {})
    lim = max([wide.get(E.norm_name(s), 24) for s in (a, b)])
    if lim <= 24:
        return _property_corner(a, b, q, near, reach, R)
    from shapely.geometry import Point
    X = E.xing(a, b, near)[0]
    eN, eE, _ = E.grid_axes(a, b, X, R)
    sN = 1 if "N" in q else -1
    sE = 1 if "E" in q else -1
    geoms, tree = E.parcel_blocks()
    blk = None
    for d in (30, 40):  # past a wide street the block starts further out
        probe = X + sN * d * eN + sE * d * eE
        cand = [geoms[i] for i in tree.query(Point(*probe).buffer(25))]
        blk = min(cand, key=lambda g: g.distance(Point(*probe))) if cand else None
        if blk is not None and blk.distance(Point(*probe)) <= 15:
            break
        blk = None
    if blk is None:
        raise ValueError(f"no parcel block in quadrant {q} of {a} x {b}")
    ring = np.asarray(blk.exterior.coords)[:, :2]
    pts = []
    for p0, p1 in zip(ring[:-1], ring[1:]):
        n = max(2, int(np.hypot(*(p1 - p0)) / 0.5))
        pts += [p0 + t * (p1 - p0) for t in np.linspace(0, 1, n, endpoint=False)]
    rel = np.array(pts) - X
    nN = np.array([eN[1], -eN[0]]); nN = nN if nN @ eE > 0 else -nN
    nE = np.array([-eE[1], eE[0]]); nE = nE if nE @ eN > 0 else -nE
    offs = []
    lo = (reach[0] + 10, reach[1] + 10)
    for e_al, n_ac, s_al, s_ac, name in ((eN, nN, sN, sE, None), (eE, nE, sE, sN, None)):
        al, ac = rel @ e_al * s_al, rel @ n_ac * s_ac
        sel = (al > lo[0]) & (al < lo[1]) & (ac > 0)
        if sel.sum() < 5:
            raise ValueError(f"property line not found at {a} x {b} {q}")
        acs = ac[sel]
        offs.append(float(np.median(acs[acs <= acs.min() + 2.0])))
    if not all(2.5 <= o <= lim for o in offs):
        raise ValueError(f"implausible property-line offsets {np.round(offs, 1)} at {a} x {b} {q}")
    p = X + np.linalg.solve(np.array([nN, nE]), np.array([sE * offs[0], sN * offs[1]]))
    return p, f"property corner {q} of {a} x {b}", offs


E.property_corner = property_corner


def keymap(vol, sid, pct=12):
    """download an index / key-map page (sheet ids like 'ind1', '0000L', '0000a') for finding sheets."""
    E.index()
    rec = [s for s in E.index()[vol] if s["id"].split("-")[-1] == sid][0]
    out = E.RAW / f"{vol}_{sid}_{pct}.jpg"
    W.curl(rec["info"].replace("/info.json", f"/full/pct:{pct}/0/default.jpg"), out, 10000)
    return out


# ----------------------------------------------------------------------------------------------- tracks
def assemble_tracks():
    """the Oakland track assembly, with this city's railroad street labels (CITIES[city]['railroad_streets'])."""
    import shapely
    from pyproj import Transformer
    from shapely.geometry import LineString, Point, Polygon, mapping
    from shapely.ops import unary_union
    from shapely.strtree import STRtree
    to_ll = Transformer.from_crs(32610, 4326, always_xy=True)
    rank = {"high": 0, "medium": 1, "low": 2}
    down = {"high": "medium", "medium": "low", "low": "low"}
    rnd = lambda gj: json.loads(json.dumps(gj), parse_float=lambda s: round(float(s), 7))  # noqa: E731
    for (area, year), keys in E.AREAS.items():
        if not all((E.INTERIM / f"{k}.tracks.json").exists() for k in keys):
            continue
        info = []
        for key in keys:
            G = json.load(open(E.INTERIM / f"{key}.M.json"))
            kcfg = json.load(open(E.CONTROL / f"{key}.json"))
            base = json.load(open(E.CONTROL / f"{kcfg['registered_to']}.json")) if "registered_to" in kcfg else kcfg
            if G.get("zones_only"):
                q = dict(n=min(b["n"] for b in G["blocks"]), rms=max(b["rms"] for b in G["blocks"]), max=max(b["max"] for b in G["blocks"]))
                polys = [p for _, p in E.block_polys(G)]
                cover = unary_union(polys).buffer(12, join_style=2)
            else:
                q = dict(n=G.get("n", 0), rms=G.get("rms", 9), max=G.get("max", 9))
                W_, H_ = Image.open(G["img"]).size
                x0, y0, x1, y1 = G.get("valid_px") or [30, 30, W_ - 30, H_ - 30]
                rect = Polygon([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
                if G.get("valid_poly_px"):
                    rect = rect.intersection(Polygon(G["valid_poly_px"]))
                cover = Polygon(W.apply(np.array(G["M"]), np.asarray(rect.exterior.coords)))
            if "registered_to" in G:
                q["rms"] = math.hypot(q["rms"], G.get("reg_rms_m", 0.3))
            conf = "high" if q["n"] >= 4 and q["rms"] <= 1.5 and q["max"] <= 3 else "medium" if q["n"] >= 3 and q["rms"] <= 3 else "low"
            if base.get("confidence_cap") and rank[conf] < rank[base["confidence_cap"]]:
                conf = base["confidence_cap"]
            info.append((rank[conf], q["rms"], key, conf, q, cover, G))
        info.sort(key=lambda t: (t[0], t[1]))
        claimed, feats = None, []
        for _, _, key, conf, q, cover, G in info:
            vol, sheet = key.split("_")
            rec = W.sheet_rec(key)
            tcfg = W.track_cfg(key)
            H_img = Image.open(G["img"]).size[1]
            for t in json.load(open(E.INTERIM / f"{key}.tracks.json")):
                ln = LineString(t["utm"])
                px = np.asarray(t["px"])
                d = px[-1] - px[0]
                if px[:, 1].min() > 0.88 * H_img and abs(d[1]) < 0.03 * abs(d[0]) + 2 and ln.length < 120:
                    continue  # the "Scale of Feet" bar at the foot of the sheet
                if not cover.buffer(5).contains(ln.centroid):
                    continue
                if claimed is not None:
                    ln = ln.difference(claimed.buffer(-1.0))
                for part in getattr(ln, "geoms", [ln]):
                    if part.is_empty or part.geom_type != "LineString" or part.length < 8:
                        continue
                    mid = px[len(px) // 2]
                    rr, rsrc = tcfg.get("railroad"), "map label" if tcfg.get("railroad") else None
                    for r in tcfg.get("railroads", []):
                        if Polygon(r["poly_px"]).contains(Point(*mid)):
                            rr, rsrc = r["name"], "map label"
                    is_main = any(Polygon(m).contains(Point(*mid)) for m in tcfg.get("main_px", []))
                    c = conf if t.get("share_in_blocks", 1) >= 0.6 else down[conf]
                    feats.append([part, {"id": f"{t['id']}" + (f"_{len(feats)}" if part.length < ln.length - 0.5 else ""),
                                         "map_year": E.VOLUMES[vol][0], "volume": f"sanborn{E.CITY}_{vol}",
                                         "volume_label": E.VOLUMES[vol][1], "sheet": rec["id"],
                                         "sheet_no": int(sheet[:4].lstrip("0") or 0), "loc_url": f"https://www.loc.gov/item/sanborn{E.CITY}_{vol}/",
                                         "iiif": rec["info"].replace("/info.json", ""), "railroad": rr, "railroad_source": rsrc,
                                         "kind": "main" if is_main else None, "kind_source": "map label" if is_main else None,
                                         "confidence": c, "georef": "blocks" if G.get("zones_only") else "sheet",
                                         "georef_rms_m": round(float(q["rms"]), 2), "length_m": round(part.length, 1)}])
            claimed = cover if claimed is None else claimed.union(cover)
        geoms = [f[0] for f in feats]
        tree = STRtree(geoms) if geoms else None
        for i, (g, p) in enumerate(feats):
            if p["kind"]:
                continue
            hits = 0
            samples = [g.interpolate(d) for d in np.arange(2.5, g.length, 5.0)] or [g.interpolate(0.5, normalized=True)]
            for pt in samples:
                d0 = g.project(pt)
                a, b = g.interpolate(max(0, d0 - 2)), g.interpolate(min(g.length, d0 + 2))
                tv = np.array([b.x - a.x, b.y - a.y]); tv = tv / (np.hypot(*tv) or 1)
                par = 0
                for j in tree.query(pt.buffer(15)):
                    if j == i:
                        continue
                    o = geoms[j]
                    if not 3 <= o.distance(pt) <= 15:
                        continue
                    dj = o.project(pt)
                    a2, b2 = o.interpolate(max(0, dj - 2)), o.interpolate(min(o.length, dj + 2))
                    tv2 = np.array([b2.x - a2.x, b2.y - a2.y]); tv2 = tv2 / (np.hypot(*tv2) or 1)
                    par += abs(float(tv @ tv2)) > 0.98
                hits += par >= 2
            p["kind"] = "yard" if hits >= 0.5 * len(samples) else "spur"
            p["kind_source"] = "rule: parallel tracks" if p["kind"] == "yard" else "rule: default"
        for g, p in feats:  # railroad named on the sheets along these streets
            for street, name in CITIES[CITY_NAME]["railroad_streets"]:
                try:
                    L = E.street_line(street, np.array([g.centroid.x, g.centroid.y]), 250)
                except (ValueError, KeyError):
                    continue
                nrm = np.array([-L[1][1], L[1][0]])
                cs = np.asarray(g.coords)
                if np.mean(np.abs((cs - L[0]) @ nrm) < 20) > 0.8 and p["railroad"] is None:
                    p["railroad"], p["railroad_source"] = name, f"map label along {street}"
        fc = {"type": "FeatureCollection", "name": f"{area}_{year}_tracks",
              "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
              "features": [{"type": "Feature", "properties": p,
                            "geometry": rnd(mapping(shapely.transform(g, lambda c: np.column_stack(to_ll.transform(c[:, 0], c[:, 1])))))}
                           for g, p in sorted(feats, key=lambda f: f[1]["id"])]}
        if feats:
            json.dump(fc, open(E.OUT / f"{area}_{year}_tracks.geojson", "w"))
        log(area, year, len(feats), "track lines", round(sum(f[0].length for f in feats)), "m")


def cap_blocks():
    """per-block confidence caps: a block whose own corners are gone (campus, superblock) and that is placed by the fit
    of its neighbours ("with") carries `confidence_cap` in its control entry; lower the confidence of its footprints in
    the assembled files (E.assemble applies only per-sheet caps)."""
    rank = {"high": 0, "medium": 1, "low": 2}
    caps = {}
    for f in E.CONTROL.glob("[0-9][0-9][0-9]_[0-9][0-9][0-9][0-9]*.json"):
        if f.name.endswith(".tracks.json"):
            continue
        cfg = json.load(open(f))
        if "registered_to" in cfg:
            cfg = json.load(open(E.CONTROL / f"{cfg['registered_to']}.json"))
            base = f.stem
        else:
            base = f.stem
        for b in cfg.get("blocks", []):
            if b.get("confidence_cap"):
                caps[(base, b["name"])] = b["confidence_cap"]
    if not caps:
        return
    for (area, year) in E.AREAS:
        p = E.OUT / f"{area}_{year}.geojson"
        if not p.exists():
            continue
        fc = json.load(open(p))
        n = 0
        for ft in fc["features"]:
            pr = ft["properties"]
            key = f"{pr['volume'].split('_')[1]}_{pr['sheet_no']:04d}"
            cap = caps.get((key, pr["georef"].replace("block ", "", 1)))
            if cap and rank[pr["confidence"]] < rank[cap]:
                pr["confidence"] = cap
                n += 1
        json.dump(fc, open(p, "w"))
        if n:
            log(area, year, n, "footprints capped by their block's confidence_cap")


def check(areas=None, out=None, dpi=160):
    """validation: geometries valid, footprints inside their coverage, and a PNG per area of the traced footprints
    (by confidence) over today's Overture footprints (grey) and the coverage outline."""
    import geopandas as gpd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shapely
    fp = E.modern_footprints()
    names = sorted({a for a, _ in E.AREAS}) if not areas else areas
    outs = []
    for area in names:
        cov = gpd.read_file(E.OUT / f"{area}_coverage.geojson").to_crs(32610)
        years = sorted(y for a, y in E.AREAS if a == area)
        fig, axs = plt.subplots(1, len(years), figsize=(9 * len(years), 10), squeeze=False)
        for ax, y in zip(axs[0], years):
            g = gpd.read_file(E.OUT / f"{area}_{y}.geojson").to_crs(32610)
            cv = shapely.union_all(cov[cov.map_year == y].geometry.values)
            inside = g.geometry.representative_point().within(cv)
            valid = g.geometry.is_valid
            log(area, y, f"{len(g)} footprints, valid {int(valid.sum())}, inside coverage {int(inside.sum())},",
                "confidence", g.confidence.value_counts().to_dict(), "modern_overlap>=0.5", int((g.modern_overlap >= 0.5).sum()))
            x0, y0, x1, y1 = cv.bounds
            m = fp.cx[x0 - 30:x1 + 30, y0 - 30:y1 + 30]
            m.plot(ax=ax, color="#bbbbbb", edgecolor="none")
            col = {"high": "#d62728", "medium": "#ff7f0e", "low": "#9467bd"}
            for c, gg in g.groupby("confidence"):
                gg.plot(ax=ax, facecolor="none", edgecolor=col[c], linewidth=0.6)
            gpd.GeoSeries([cv], crs=32610).boundary.plot(ax=ax, color="#2ca02c", linewidth=0.8)
            ax.set_title(f"{area} {y}: {len(g)} traced (red high / orange medium / purple low) over today's footprints (grey)")
            ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        o = out or E.INTERIM / f"check_{area}.png"
        fig.tight_layout(); fig.savefig(o, dpi=dpi); plt.close(fig)
        outs.append(o)
        print(o)
    return outs


# ----------------------------------------------------------------------------------------------- driver
if __name__ == "__main__":
    city = sys.argv[1]
    configure(city)
    E.index()
    stage = sys.argv[2] if len(sys.argv) > 2 else "all"
    args = sys.argv[3:]
    if stage == "keymap":
        print(keymap(args[0], args[1], int(args[2]) if len(args) > 2 else 12))
        sys.exit()
    if stage == "grid":
        k = args[0]
        box = tuple(int(v) for v in args[1:5]) if len(args) >= 5 else None
        print(E.grid(k, box, step=int(os.environ.get("STEP", 100)), scale=float(os.environ.get("SCALE", 1.0))))
        sys.exit()
    if stage == "register":
        W.register(args[0], args[1])
        sys.exit()
    if stage == "spec":  # spec <key> <json file or inline json>: write a control file from a block spec (E.spec)
        s = args[1]
        s = json.load(open(s)) if os.path.exists(s) else json.loads(s)
        E.spec(args[0], s)
        print("wrote", E.CONTROL / f"{args[0]}.json")
        sys.exit()
    if stage == "respec":  # respec <key> [json of top-level keys to set]: rebuild a control file from its own block
        # estimates (px4_est, streets, w, skip, oc, with, no_refine), e.g. after changing a threshold
        cfg = json.load(open(E.CONTROL / f"{args[0]}.json"))
        top = {k: v for k, v in cfg.items() if k not in ("blocks", "pct")}
        top.update(json.loads(args[1]) if len(args) > 1 else {})
        s = dict(top, blocks={b["name"]: dict(b["streets"], px=b["px4_est"], **{k: b[k] for k in ("w", "skip", "oc", "near", "no_refine", "with") if k in b})
                              for b in cfg["blocks"]})
        E.spec(args[0], s)
        sys.exit()
    if stage == "check":
        check(args or None)
        sys.exit()
    keys = args or E.all_keys()
    if stage in ("all", "fetch"):
        for k in keys:
            E.image(k, int(os.environ.get("PCT", 25)))
    if stage in ("all", "georef"):
        for k in E.base_first(keys):
            W.georef(k)
    if stage == "mosaic":
        for k in keys:
            print(E.corner_mosaic(k))
    if stage == "refine":  # the 1911 Berkeley block lines are thin: a control file may lower the weak-side threshold
        for k in keys:
            E.refine(k, weak=json.load(open(E.CONTROL / f"{k}.json")).get("weak", 0.35))
    if stage == "freeze":
        for k in keys:
            E.freeze(k)
    if stage in ("all", "extract"):
        for k in keys:
            E.extract(k)
            E.reclass(k)
            if k.split("_")[0] in E.EDITION_1950:
                E.extract_regions(k)
    if stage == "overlay":
        for k in keys:
            print(E.overlay(k, scale=float(os.environ.get("SCALE", 0.5))))
    if stage in ("all", "tracks"):
        for k in keys:
            W.tracks(k)
    if stage in ("all", "assemble"):
        E.assemble()
        cap_blocks()
        assemble_tracks()
