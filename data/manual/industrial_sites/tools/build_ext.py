"""Add the sites of the ten-county extent (industrial_def_ext.py) to
data/manual/industrial_sites/{sites.geojson, building_dates.csv, known_dates_industrial.csv, traced/audit.csv}.

  cd data/manual/industrial_sites && ../../../.venv/bin/python -I tools/build_ext.py [site_id ...] [--redate]

Same method as build.py (its functions are reused): OSM outlines, traced rings, hulls; sites with
`date=True` have today's footprints checked against the USGS editions (presence cached in
data/interim/industrial_sites/). The core sites' features and rows are kept byte for byte: this script only
replaces / appends the features and rows of the SITES_EXT site ids (idempotent). With site ids on the
command line nothing is written (audit only).

Extras over build.py: part option clip=(frame, ring) (see industrial_def_ext.py); researched buildings
(NAMED_EXT) are given by Overture building id prefix and their point is computed inside the footprint.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import mapping

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build as B  # noqa: E402
from industrial_def_ext import NAMED_EXT, SITES_EXT  # noqa: E402

OUTD = HERE.parent
EXT_IDS = {s["site_id"] for s in SITES_EXT}
KNOWN_COLS = ["id", "name", "lat", "lon", "start_year", "end_year", "source_url", "note", "county"]
RULE_COLS = ["site_id", "ring_type", "year", "applies_to", "max_year", "evidence", "source_url"]


def named_rows():
    """NAMED_EXT with lat / lon inside the Overture footprint whose id starts with `fid`."""
    want = sorted({n["fid"] for n in NAMED_EXT})
    con = duckdb.connect()
    con.execute("LOAD spatial;")
    geoms = {}
    for fn in ("region4_building", "region5_building"):
        q = (f"select id, ST_AsWKB(geometry) g from read_parquet('{B.OVT}/{fn}.parquet') "
             f"where substr(id, 1, 8) in ({', '.join(repr(w) for w in want)})")
        for fid, g in con.execute(q).fetchall():
            geoms.setdefault(fid[:8], (fid, shapely.from_wkb(bytes(g))))
    out = []
    for n in NAMED_EXT:
        if n["fid"] not in geoms:
            print("  !! researched building without footprint:", n["id"], n["fid"])
            continue
        fid, g = geoms[n["fid"]]
        p = g.representative_point()
        out.append(dict(id=n["id"], name=n["name"], lat=round(p.y, 6), lon=round(p.x, 6),
                        start_year=float(n["start_year"]), end_year=n["end_year"], source_url=n["source_url"],
                        note=n["note"] + f" Footprint {fid}.", county=n["county"]))
    return out


def other_researched():
    """Points of the other researched-year tables (data/tables/known_building_dates_region.csv, the OHM and
    airport tables): region_buildings.known_dates applies them before this folder's rows, so a footprint
    they date must not get an edition row here (the later row would win)."""
    pts, rows = [], []
    for p in (B.ROOT / "data/tables/known_building_dates_region.csv", B.ROOT / "data/manual/ohm/known_dates_ohm.csv",
              B.ROOT / "data/manual/airports/buildings.csv"):
        if not p.exists():
            continue
        t = pd.read_csv(p)
        t = t[np.isfinite(pd.to_numeric(t.get("lat"), errors="coerce")) & np.isfinite(pd.to_numeric(t.get("lon"), errors="coerce"))]
        pts += list(shapely.points(t.lon.astype(float).values, t.lat.astype(float).values))
        rows += [f"{p.name}:{i} ({y})" for i, y in zip(t["id"], t["start_year"])]
    return (shapely.STRtree(pts) if pts else None), rows


def merge_csv(path, cols, rows, is_ext):
    """Keep the file's other lines as they are; drop the lines `is_ext(first field)` and append `rows`."""
    text = path.read_text()
    lines = text.split("\n")
    assert lines[0].split(",") == cols, (path, lines[0])
    body = [ln for ln in lines[1:] if ln != ""]
    assert len(list(csv.reader(io.StringIO(text)))) == len(body) + 1, f"{path}: multi-line records"
    kept = [ln for ln in body if not is_ext(ln.split(",", 1)[0])]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    for r in rows:
        w.writerow([r[c] for c in cols])
    path.write_text("\n".join([lines[0]] + kept) + "\n" + buf.getvalue())
    return len(kept), len(rows)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    redate = "--redate" in sys.argv
    lu = B.land_use()
    named = named_rows()
    otree, orows = other_researched()
    n_other = 0
    if otree is not None:
        for n in named:  # the same building researched in another table: report (both rows stay)
            near = otree.query(shapely.Point(n["lon"], n["lat"]).buffer(0.00025))
            if len(near):
                print(f"  ?? {n['id']} ({n['start_year']:g}) is also dated by", [orows[k] for k in near])
    named_pts = shapely.points([(n["lon"], n["lat"]) for n in named]) if named else shapely.points([])
    feats, known, rules, audit = [], [], [], []
    for s in SITES_EXT:
        if args and s["site_id"] not in args:
            continue
        print(s["site_id"], flush=True)
        parts = []
        for p in s["parts"]:
            for g, ref in B.part_geoms(p, lu):
                g = shapely.make_valid(g)
                if "clip" in p:
                    fr, ring = p["clip"]
                    g = shapely.make_valid(shapely.intersection(g, B.ring_ll(fr, ring)))
                    ref += "; clipped to the stage read on the map"
                if g.is_empty:
                    print("  !! empty part", ref)
                    continue
                parts.append((g, ref, p))
        if not parts:
            print("  !! no geometry")
            continue
        geom = shapely.union_all([g for g, _, _ in parts])
        top = [g for g, _, p in parts if p.get("on_top")]
        if top:
            tu = shapely.union_all(top)
            parts = [(g if p.get("on_top") else shapely.make_valid(g.difference(tu)), ref, p) for g, ref, p in parts]
        fps, pr = (B.dated_footprints(s, geom, redate) if s.get("date") else (None, None))
        if fps is not None and len(fps):
            f0 = s["founded"]
            drawn = fps.first_drawn.notna()
            real_roll = np.isfinite(fps.roll_year) & (fps.roll_year > 1900)
            rebuilt = real_roll & (fps.roll_year > fps.last_drawn + 2)
            late = drawn & (fps.live_year > fps.first_drawn + 2) & ~rebuilt
            early = (fps.live_year < f0 - 1) & (s["conf"] == "exact")
            fix = late | early
            new = np.where(late, fps.est_start, np.nan)
            new = np.where(early & drawn, np.maximum(fps.est_start, f0), new)
            new = np.where(early & ~drawn, f0, new)
            fps["new_year"] = new
            rp = fps.geometry.representative_point()
            for i in np.nonzero(fix.values)[0]:
                r = fps.iloc[i]
                if len(named_pts) and shapely.contains(r.geometry, named_pts).any():
                    continue  # a researched row dates this footprint
                if otree is not None and len(otree.query(r.geometry, predicate="contains")):
                    n_other += 1
                    continue  # researched in another table (it would be overridden by this row)
                tank = r.circ > 0.85 and r.area_m2 > 40
                ev = r.evidence if isinstance(r.evidence, str) else ""
                if early.iloc[i] and not drawn.iloc[i]:
                    ev = f"not drawn on any edition; live year {r.live_year:.0f} predates the site -> founding year"
                roll = f"roll {r.roll_year:.0f} ({r.roll_src})" if np.isfinite(r.roll_year) else "no roll year"
                known.append(dict(
                    id=f"{s['site_id']}_{str(r.fid).split(':')[-1][:8]}",
                    name=f"{s['label']}: {'tank' if tank else 'building'} ({r.area_m2:.0f} m2)",
                    lat=round(rp.y.iloc[i], 6), lon=round(rp.x.iloc[i], 6),
                    start_year=round(float(r.new_year), 1), end_year=9999,
                    source_url=r.first_url if isinstance(r.first_url, str) else s["src"],
                    note=f"USGS editions: {ev}; site founded {f0:g}; live map {r.live_year:.0f}, {roll}. "
                         f"Footprint {r.fid}.", county=s["county"]))
            d = fps.live_year - fps.new_year
            audit.append(dict(site_id=s["site_id"], name=s["label"], founded=f0, footprints=len(fps),
                              live_median=round(float(np.nanmedian(fps.live_year)), 0),
                              live_p10=round(float(np.nanpercentile(fps.live_year.dropna(), 10)), 0)
                              if fps.live_year.notna().any() else np.nan,
                              drawn_on_maps=int(drawn.sum()), corrected=int(fix.sum()), too_late=int(late.sum()),
                              too_early=int(early.sum()),
                              median_shift_years=round(float(np.nanmedian(d[fix])), 0) if fix.any() else 0,
                              max_shift_years=round(float(np.nanmax(np.abs(d[fix]))), 0) if fix.any() else 0))
        else:
            fp = B.footprints(geom)
            ok = len(fp) and fp.live_year.notna().any()
            f0 = s.get("founded", s["start"])
            audit.append(dict(site_id=s["site_id"], name=s["label"], founded=f0, footprints=len(fp),
                              live_median=round(float(np.nanmedian(fp.live_year)), 0) if ok else np.nan,
                              live_p10=round(float(np.nanpercentile(fp.live_year.dropna(), 10)), 0) if ok else np.nan,
                              drawn_on_maps=np.nan, corrected=0, too_late=0,
                              too_early=int((fp.live_year < f0 - 1).sum()) if ok else 0,
                              median_shift_years=0, max_shift_years=0))
        for k, (g, ref, p) in enumerate(parts):
            y0 = p.get("start", s["start"])
            pieces = [gg for gg in getattr(shapely.make_valid(g), "geoms", [g])
                      if gg.geom_type in ("Polygon", "MultiPolygon") and not gg.is_empty]
            pieces = [q for gg in pieces for q in getattr(gg, "geoms", [gg])]
            if len(pieces) > 1:  # slivers left by cutting one part out of another
                ar = gpd.GeoSeries(pieces, crs=4326).to_crs(B.UTM).area.values
                pieces = [q for q, a in zip(pieces, ar) if a > 3000]
            for m_, gg in enumerate(pieces):
                pid = f"{s['site_id']}_{k + 1}" + (chr(97 + m_) if len(pieces) > 1 else "")
                feats.append({"type": "Feature", "properties": {
                    "site_id": s["site_id"], "part_id": pid, "name": s["name"],
                    "kind": s["kind"], "cover": p.get("cover", s["cover"]),
                    "year_start": round(float(y0), 2), "year_end": p.get("end", s["end"]),
                    "name_label": s["label"],
                    "label_start": round(float(p.get("label_years", s.get("label_years", (y0, 0)))[0]), 2),
                    "label_end": p.get("label_years", s.get("label_years", (0, p.get("end", s["end"]))))[1],
                    "confidence": p.get("conf", s["conf"]),
                    "source_url": p.get("src", s["src"]),
                    "note": (p.get("note", "") + ("; " if p.get("note") else "") + f"geometry: {ref}").strip(),
                    "county": s["county"]},
                    "geometry": mapping(shapely.set_precision(gg, 1e-7))})
        if s["conf"] == "exact" and s.get("floor", True):
            f0 = s.get("founded", s["start"])
            rules.append(dict(site_id=s["site_id"], ring_type="site", year=repr(float(f0)), applies_to="all_pre",
                              max_year="", evidence=f"{s['label']} founded {f0:g}: no footprint inside can be older",
                              source_url=s["src"]))
        if s.get("date"):
            rules.append(dict(site_id=s["site_id"], ring_type="site", year=repr(float(s.get("founded", s["start"]))),
                              applies_to="named", max_year="",
                              evidence="footprints dated by the USGS editions that first draw them: "
                                       "known_dates_industrial.csv", source_url=s["src"]))
    print(f"{n_other} footprints left to the other researched tables")
    aud = pd.DataFrame(audit)
    print(aud.to_string())
    lab = pd.DataFrame([f["properties"] for f in feats])
    if len(lab):
        g = lab.groupby("site_id").agg(label=("name_label", "first"), y0=("label_start", "min"),
                                       y1=("label_end", "max"), parts=("part_id", "count"),
                                       covers=("cover", lambda v: "/".join(sorted(set(v)))))
        g["len"] = g.label.str.len()
        print(g.to_string())
    if args:
        print("partial run: not writing outputs")
        return
    # ---- sites.geojson: the other sites' features unchanged, ours replaced / appended
    sp = OUTD / "sites.geojson"
    src = sp.read_text()
    fc = json.loads(src)
    keep = [f for f in fc["features"] if f["properties"]["site_id"] not in EXT_IDS]
    assert not EXT_IDS & {f["properties"]["site_id"] for f in keep}
    feats.sort(key=lambda f: (f["properties"]["site_id"], f["properties"]["part_id"]))
    sp.write_text(json.dumps({"type": "FeatureCollection", "features": keep + feats}))
    # ---- known_dates_industrial.csv
    rows = named + known
    seen = {}
    for r in rows:
        r["id"] = r["id"].replace(".0", "")
        n = seen.get(r["id"], 0)
        seen[r["id"]] = n + 1
        if n:
            r["id"] = f"{r['id']}_{n}"  # parts of one building
        r["lat"], r["lon"] = repr(float(r["lat"])), repr(float(r["lon"]))
        r["start_year"] = repr(float(r["start_year"]))
    ext_pfx = tuple(sorted(s + "_" for s in EXT_IDS)) + ("indx_",)
    k0, k1 = merge_csv(OUTD / "known_dates_industrial.csv", KNOWN_COLS, rows, lambda v: v.startswith(ext_pfx))
    r0, r1 = merge_csv(OUTD / "building_dates.csv", RULE_COLS, rules, lambda v: v in EXT_IDS)
    ap = OUTD / "traced" / "audit.csv"
    old = pd.read_csv(ap)
    cols = list(old.columns)
    a0, a1 = merge_csv(ap, cols, [{c: ("" if pd.isna(v) else v) for c, v in r.items()} for r in
                                  aud[cols].to_dict("records")], lambda v: v in EXT_IDS)
    aud.to_csv(B.CACHE / "audit_ext.csv", index=False)
    print(f"sites.geojson: {len(keep)} kept + {len(feats)} new parts; known dates: {k0} kept + {k1} "
          f"({len(named)} researched); rules: {r0} kept + {r1}; audit rows {a0} + {a1}")


if __name__ == "__main__":
    main()
