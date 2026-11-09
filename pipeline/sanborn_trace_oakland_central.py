"""Trace the vanished buildings of central Oakland east of Broadway from Library of Congress Sanborn maps.

Areas (data/manual/sanborn/README_oakland_central.md):
  oakland_lakeside     Broadway -> Lake Merritt, 10th / 11th St -> 20th St (Uptown, Lakeside, the Gold Coast)
  oakland_adams_point  north of 20th St: Broadway / Webster -> the lake's north arm, up to Santa Clara Ave / Perry Pl
                       (Valdez / Waverly / Harrison St, Grand Ave, Adams Point, Bellevue / Perkins / Van Buren Ave)
  oakland_eastlake     east of the lake (E 12th -> E 18th St, 1st Ave -> Clinton)

Volumes: Oakland vol. 2 (east of Broadway): sanborn00727_006 (1911) and sanborn00727_016 (1911 - Nov 1950, the 1911
plates with paste-over corrections), registered onto the 1911 plates by SIFT as in README_oakland.md.

This module only configures pipeline/sanborn_trace_eastbay.py (block specs, `refine`, property corners from today's
parcels, offset corners, similarity fits, SIFT registration, colour segmentation with partition walls, assembly,
confidence rules) through pipeline/sanborn_trace_eastbay_cities.py (Overture roads_region + roads_local for street
lines, `check`, `cap_blocks`, `commercial_fronts`); its own control lives in data/manual/sanborn/control/oakland_central/
(the West Oakland / downtown / freeway-corridor control in control/oakland/ belongs to sanborn_trace_eastbay.py).
Storeys read off the sheets by eye: control/oakland_central/storeys.json {key: [[x, y, stories], ...]} (pixel on the
25 % scan inside the building; the footprint containing it, else the nearest within 25 px), applied after assembly.

Usage:  python pipeline/sanborn_trace_oakland_central.py <stage> [keys]
  stages: fetch | grid <key> [x0 y0 x1 y1] | spec <key> <json> | respec <key> [json] | refine | georef | register <src> <dst>
          | mosaic | extract | large | overlay | assemble | check | all (= fetch + georef + extract + assemble)
Keys are <LOC item suffix>_<sheet>: 006_0152 = sanborn00727_006 (1911 vol. 2) sheet 152; 016_0152 = the same plate in
the 1911 - Nov 1950 corrected vol. 2.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import sanborn_trace_eastbay as E  # noqa: E402
import sanborn_trace_eastbay_cities as C  # noqa: E402
import sanborn_trace_waterfront as W  # noqa: E402

NAME = "oakland_central"
ORDINAL = {"first": "1st", "second": "2nd", "third": "3rd", "fourth": "4th", "fifth": "5th", "sixth": "6th",
           "seventh": "7th", "eighth": "8th", "ninth": "9th", "tenth": "10th", "eleventh": "11th", "twelfth": "12th",
           "thirteenth": "13th", "fourteenth": "14th", "fifteenth": "15th", "sixteenth": "16th", "seventeenth": "17th",
           "eighteenth": "18th", "nineteenth": "19th", "twentieth": "20th"}
C.CITIES[NAME] = {
    "loc": "00727",
    "volumes": {"006": (1911, "1911 Vol. 2"), "016": (1950, "1911-Nov 1950 Vol. 2 (corrected to Nov 1950)")},
    "edition_1950": ("016",),
    "parcels": ROOT / "data/raw/region_years/alameda_county_2021/alameda_county_2021.parquet",
    "parcel_cols": ["APN"],
    "bbox": (-122.285, 37.785, -122.225, 37.835),  # Broadway - Eastlake, the estuary - Piedmont Ave
    # street names on the 1911 / 1950 sheets -> today's names (Overture); more in control/oakland_central/aliases.json
    "aliases": {f"{w} street": f"{n} street" for w, n in ORDINAL.items()} | {
        "grove street": "martin luther king junior way", "grove": "martin luther king junior way",
        "w grand avenue": "grand avenue", "west grand avenue": "grand avenue", "moss avenue": "macarthur boulevard",
    },
    "commercial_streets": {"broadway": 40, "telegraph avenue": 35, "san pablo avenue": 35, "grand avenue": 30},
    "railroad_streets": [],
}


def configure():
    c = C.configure(NAME)
    # the LOC images and item index of Oakland are shared with sanborn_trace_eastbay.py (cached by key)
    E.RAW = ROOT / "data/raw/sanborn_loc_oakland"
    W.RAW = E.RAW
    al = E.CONTROL / "aliases.json"
    if al.exists():
        E.ALIASES.update(json.load(open(al)))
    return c


def storeys_to_attributes():
    """control/oakland_central/storeys.json {key: [[x, y, stories], ...]} -> {footprint id: stories}: the footprint
    containing the pixel, else the nearest within 25 px (as pipeline/sanborn_trace_peninsula.py)."""
    from shapely.geometry import Point, Polygon
    p = E.CONTROL / "storeys.json"
    out = {}
    if not p.exists():
        return out
    for key, marks in json.load(open(p)).items():
        f = E.INTERIM / f"{key}.json"
        if not f.exists():
            continue
        polys = [(r["id"], Polygon(r["px_ring"]).buffer(0)) for r in json.load(open(f))]
        for x, y, st in marks:
            pt = Point(x, y)
            hit = [rid for rid, pg in polys if pg.contains(pt)]
            if not hit:
                near = sorted((pg.distance(pt), rid) for rid, pg in polys)
                hit = [near[0][1]] if near and near[0][0] <= 25 else []
            if hit:
                out[hit[0]] = st
            else:
                C.log(key, "storey mark not placed:", x, y, st)
    return out


def apply_storeys():
    """storeys read off the sheets replace the default rule in the assembled files; a building read at 3+ storeys that
    the rule called a dwelling is called flats (apartments / flats; the sheets mark 'F' for flats)."""
    st = storeys_to_attributes()
    if not st:
        return
    for (area, year) in E.AREAS:
        p = E.OUT / f"{area}_{year}.geojson"
        if not p.exists():
            continue
        fc = json.load(open(p))
        n = 0
        for ft in fc["features"]:
            pr = ft["properties"]
            if pr["id"] in st:
                pr["stories"], pr["stories_source"] = st[pr["id"]], "map (read from the sheet)"
                if pr["use_source"] == "default" and pr["use"] == "dwelling" and st[pr["id"]] >= 3:
                    pr["use"], pr["use_source"] = "flats", "default (rule: 3+ storey residential building)"
                n += 1
        json.dump(fc, open(p, "w"))
        C.log(area, year, n, "storeys read off the sheet")


def add_labels(reads):
    """scratch aid: {footprint id: (name, use or None)} read off the sheets -> labels.json [x, y, name, use] at a point
    inside the footprint on its 25 % scan (E.assemble reads labels.json)."""
    from shapely.geometry import Polygon
    p = E.CONTROL / "labels.json"
    lab = json.load(open(p)) if p.exists() else {}
    rows = {}
    for fid, (name, use) in reads.items():
        key = fid.rsplit("_", 1)[0]
        if key not in rows:
            rows[key] = {r["id"]: r for r in json.load(open(E.INTERIM / f"{key}.json"))}
        q = Polygon(rows[key][fid]["px_ring"]).buffer(0).representative_point()
        lst = [e for e in lab.setdefault(key, []) if Polygon(rows[key][fid]["px_ring"]).buffer(0).distance(
            Polygon([(e[0] - .1, e[1] - .1), (e[0] + .1, e[1] - .1), (e[0] + .1, e[1] + .1)])) > 0.5]
        lst.append([round(q.x, 1), round(q.y, 1), name, use])
        lab[key] = lst
    json.dump(lab, open(p, "w"), indent=1)


def carry_forward():
    """a building on the earlier map whose storeys or name were read off the sheet keeps them on the later map when it
    is the same building there (IoU >= 0.5 with a footprint of the same Sanborn colour whose storeys / name were not
    read): apply_sanborn emits a building present on both maps with its later outline and attributes.
    stories_source = 'map (read from the <year> sheet: same building)'."""
    import shapely
    from shapely.geometry import shape
    from shapely.strtree import STRtree
    from pyproj import Transformer
    to_utm = Transformer.from_crs(4326, 32610, always_xy=True)
    utm = lambda g: shapely.transform(g, lambda c: np.column_stack(to_utm.transform(c[:, 0], c[:, 1])))  # noqa: E731
    for area in sorted({a for a, _ in E.AREAS}):
        years = sorted(y for a, y in E.AREAS if a == area)
        for y0, y1 in zip(years[:-1], years[1:]):
            p0, p1 = E.OUT / f"{area}_{y0}.geojson", E.OUT / f"{area}_{y1}.geojson"
            if not (p0.exists() and p1.exists()):
                continue
            A = json.load(open(p0))["features"]
            fc = json.load(open(p1))
            src = [(utm(shape(f["geometry"])), f["properties"]) for f in A
                   if f["properties"]["stories_source"].startswith("map") or f["properties"].get("name")]
            if not src:
                continue
            tree = STRtree([g for g, _ in src])
            ns = nn = 0
            for f in fc["features"]:
                pr = f["properties"]
                g = utm(shape(f["geometry"]))
                best, bi = None, 0.5
                for j in tree.query(g):
                    g0, p0r = src[j]
                    if p0r["sanborn_colour"] != pr["sanborn_colour"]:
                        continue
                    iou = g0.intersection(g).area / max(g0.union(g).area, 1e-6)
                    if iou >= bi:
                        best, bi = p0r, iou
                if best is None:
                    continue
                if best["stories_source"].startswith("map") and not pr["stories_source"].startswith("map"):
                    pr["stories"], pr["stories_source"] = best["stories"], f"map (read from the {y0} sheet: same building)"
                    ns += 1
                if best.get("name") and not pr.get("name"):
                    pr["name"] = best["name"]
                    if best["use_source"].startswith("map") and pr["use_source"] == "default":
                        pr["use"], pr["use_source"] = best["use"], f"map (label on the {y0} sheet: same building)"
                    nn += 1
            json.dump(fc, open(p1, "w"))
            C.log(area, y1, ns, "storeys and", nn, "names carried over from", y0)


def add_storeys(reads):
    """scratch aid: {footprint id: stories} -> storeys.json entries [x, y, stories] at a point inside the footprint."""
    from shapely.geometry import Polygon
    p = E.CONTROL / "storeys.json"
    st = json.load(open(p)) if p.exists() else {}
    rows = {}
    for fid, n in reads.items():
        key = fid.rsplit("_", 1)[0]
        if key not in rows:
            rows[key] = {r["id"]: r for r in json.load(open(E.INTERIM / f"{key}.json"))}
        pg = Polygon(rows[key][fid]["px_ring"]).buffer(0)
        q = pg.representative_point()
        lst = st.setdefault(key, [])
        lst[:] = [e for e in lst if not pg.buffer(0.5).contains(Polygon([(e[0] - .1, e[1] - .1), (e[0] + .1, e[1] - .1), (e[0] + .1, e[1] + .1)]))]
        lst.append([round(q.x, 1), round(q.y, 1), n])
    json.dump(st, open(p, "w"), indent=1)


def extract_large(key, min_px=2500, edge_min=0.45):
    """third pass: large, solid colour fills that E.extract rejects only for a light outline (the outline test wants
    >= 70 % dark pixels around a fill; the outlines of big fire-proof / brick buildings on the 1944-50 paste-over slips
    are thin and broken by hatching and lettering: e.g. the 1932 Post Office on 13th St). A component of a colour class
    of >= `min_px` pixels (100 m2), solidity >= 0.75, at least 10 px from edge to centre, with 45-70 % dark outline,
    not already covered (> 30 %) by a footprint, is added (ids <key>_L<n>, extraction 'colour class (light outline)')."""
    import cv2
    from shapely.geometry import Polygon
    from shapely.strtree import STRtree
    from scipy import ndimage as ndi
    G = json.load(open(E.INTERIM / f"{key}.M.json"))
    ed = key.split("_")[0]
    rgb = np.asarray(E.Image.open(G["img"]).convert("RGB"))
    hsv = cv2.cvtColor(cv2.medianBlur(rgb, 3), cv2.COLOR_RGB2HSV).astype(np.int16)
    Hh, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    del hsv
    pm = (V > np.percentile(V, 30)) & (S < np.percentile(S, 70))
    pH, pS = int(np.median(Hh[pm])), int(np.median(S[pm]))
    del pm
    if ed in E.EDITION_1950:
        fr = ((Hh >= max(pH, 22)) & (Hh <= 36) & (S >= pS + 40) & (V >= 70)) | ((Hh >= 19) & (Hh <= 36) & (S >= 125) & (V >= 70))
    else:
        fr = (Hh >= 19) & (Hh <= 38) & (S >= max(80, pS + 40)) & (V >= 80)
    classes = {"frame": fr, "brick": ((Hh >= 155) | (Hh <= 7)) & (S >= 40) & (V >= 55),
               "stone": (Hh >= 80) & (Hh <= 130) & (S >= 30) & (V >= 55), "fireproof": (Hh >= 8) & (Hh <= 18) & (S >= 100) & (V >= 50)}
    del Hh, S, V
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.int16)
    del rgb
    med = cv2.medianBlur(gray.astype(np.uint8), 7).astype(np.int16)
    line = ((gray < med - 28) & (gray < 100)) | (gray < 60)
    part = ndi.binary_opening(line, structure=np.ones((14, 1))) | ndi.binary_opening(line, structure=np.ones((1, 14)))
    part = ndi.binary_dilation(part, structure=np.ones((2, 2)))
    darkd = ndi.binary_dilation(line | (gray < 95), iterations=3)
    rows = json.load(open(E.INTERIM / f"{key}.json"))
    have = [Polygon(r["px_ring"]).buffer(0) for r in rows]
    tree = STRtree(have) if have else None
    blocks = G.get("blocks", [])
    out = []
    for cls, m in classes.items():
        m = ndi.binary_opening(m, structure=np.ones((2, 2)))
        m = (ndi.binary_closing(m, structure=np.ones((3, 3))) | m) & ~part
        holes = ndi.binary_fill_holes(m) & ~m
        hl, hn = ndi.label(holes)
        if hn:
            hs = ndi.sum(holes, hl, range(1, hn + 1))
            m = m | np.isin(hl, np.nonzero(hs < 2500)[0] + 1)
        m = m & ~part
        lab, n = ndi.label(m)
        if not n:
            continue
        sizes = ndi.sum(m, lab, range(1, n + 1))
        objs = ndi.find_objects(lab)
        for i in np.nonzero(sizes >= min_px)[0]:
            sl = objs[i]
            if sl[0].start < 12 or sl[1].start < 12 or sl[0].stop > m.shape[0] - 12 or sl[1].stop > m.shape[1] - 12:
                continue
            sub = lab[sl] == i + 1
            if ndi.distance_transform_edt(np.pad(sub, 1)).max() < 10:
                continue
            hull = cv2.convexHull(np.argwhere(sub)[:, ::-1].astype(np.int32))
            if sizes[i] / max(cv2.contourArea(hull), 1) < 0.75:
                continue
            big = np.zeros(m.shape, bool)
            big[sl] = sub
            ring = ndi.binary_dilation(big, iterations=1) & ~big
            ed_ = float(darkd[ring].mean())
            if not edge_min <= ed_ < 0.7:
                continue  # >= 0.7: E.extract kept it
            cs, _ = cv2.findContours(np.pad(sub, 2).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            c = max(cs, key=cv2.contourArea)[:, 0, :].astype(float)
            c[:, 0] += sl[1].start - 2
            c[:, 1] += sl[0].start - 2
            poly = Polygon(c).buffer(1.2, join_style=2).simplify(1.0)
            if poly.geom_type != "Polygon":
                continue
            if tree is not None and sum(have[j].intersection(poly).area for j in tree.query(poly)) > 0.3 * poly.area:
                continue
            cx, cy = poly.centroid.x, poly.centroid.y
            best, bd = None, 1e9
            for b in blocks:
                x0, y0, x1, y1 = b["rect_px"]
                d = max(x0 - cx, 0, cx - x1) + max(y0 - cy, 0, cy - y1)
                if d < bd:
                    best, bd = b, d
            if best is None or bd > 40:
                continue
            T = np.array(best["M"])
            ext = W.apply(T, np.asarray(poly.exterior.coords))
            out.append({"id": f"{key}_L{len(out) + 1}", "cls": cls, "zone": best["name"], "px_centroid": [round(cx, 1), round(cy, 1)],
                        "px_ring": np.round(np.asarray(poly.exterior.coords), 1).tolist(), "area_m2": round(float(Polygon(ext).area), 1),
                        "ring_utm": np.round(ext, 2).tolist(), "holes_utm": [], "method": "colour class (light outline)"})
            have.append(poly)
            tree = STRtree(have)
    json.dump(rows + out, open(E.INTERIM / f"{key}.json", "w"))
    C.log(key, len(out), "large light-outline footprints added")


if __name__ == "__main__":
    configure()
    E.index()
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    args = sys.argv[2:]
    if stage == "grid":
        k = args[0]
        box = tuple(int(v) for v in args[1:5]) if len(args) >= 5 else None
        print(E.grid(k, box, step=int(os.environ.get("STEP", 100)), scale=float(os.environ.get("SCALE", 1.0))))
        sys.exit()
    if stage == "register":
        W.register(args[0], args[1])
        sys.exit()
    if stage == "spec":
        s = args[1]
        E.spec(args[0], json.load(open(s)) if os.path.exists(s) else json.loads(s))
        print("wrote", E.CONTROL / f"{args[0]}.json")
        sys.exit()
    if stage == "respec":
        cfg = json.load(open(E.CONTROL / f"{args[0]}.json"))
        top = {k: v for k, v in cfg.items() if k not in ("blocks", "pct")}
        top.update(json.loads(args[1]) if len(args) > 1 else {})
        s = dict(top, blocks={b["name"]: dict(b["streets"], px=b["px4_est"], **{k: b[k] for k in ("w", "skip", "oc", "near", "no_refine", "with") if k in b})
                              for b in cfg["blocks"]})
        E.spec(args[0], s)
        sys.exit()
    if stage == "check":
        C.check(args or None)
        sys.exit()
    keys = args or E.all_keys()
    if stage in ("all", "fetch"):
        for k in keys:
            E.image(k, int(os.environ.get("PCT", 25)))
    if stage == "refine":
        for k in keys:
            E.refine(k, weak=json.load(open(E.CONTROL / f"{k}.json")).get("weak", 0.35))
    if stage in ("all", "georef"):
        for k in E.base_first(keys):
            W.georef(k)
    if stage == "mosaic":
        for k in keys:
            print(E.corner_mosaic(k))
    if stage in ("all", "extract"):
        for k in keys:
            E.extract(k)
            E.reclass(k)
            if k.split("_")[0] in E.EDITION_1950:
                E.extract_regions(k)
            extract_large(k)
            E.reclass(k)
    if stage == "large":  # only the light-outline pass (after extract)
        for k in keys:
            extract_large(k)
            E.reclass(k)
    if stage == "overlay":
        for k in keys:
            print(E.overlay(k, scale=float(os.environ.get("SCALE", 0.5))))
    if stage in ("all", "assemble"):
        E.assemble()
        C.cap_blocks()
        C.commercial_fronts()
        apply_storeys()
        carry_forward()
