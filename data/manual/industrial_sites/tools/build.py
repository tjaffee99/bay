"""Build data/manual/industrial_sites/{sites.geojson, building_dates.csv, known_dates_industrial.csv,
traced/audit.csv} from industrial_def.py.

  cd data/manual/industrial_sites && ../../../.venv/bin/python -I tools/build.py [site_id ...] [--redate]

* parts: OSM land_use outlines (Overture 2026-10-21.0), rings traced on USGS sheets, tint.py outlines
* sites with `date=True`: today's footprints inside (footprints.py) are checked against every USGS
  edition covering the site (date_editions.py; presence cached in data/interim/industrial_sites/);
  footprints whose live-map year disagrees with the editions get a row in known_dates_industrial.csv
* parts marked auto=True start when their footprints first appear on the maps (20th percentile of
  the footprints' estimated start years), never before the site's founding
* audit: per site, the live map's years of today's footprints inside it vs the evidence
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Polygon, mapping, shape

HERE = Path(__file__).resolve().parent
OUTD = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "vanished_sites" / "tools"))
import vt  # noqa: E402
from date_editions import presence, start_years  # noqa: E402
from editions import editions  # noqa: E402
from footprints import footprints  # noqa: E402
from industrial_def import NAMED, SITES  # noqa: E402

ROOT = HERE.parents[3]
OVT = ROOT / "data/raw/overture/2026-10-21.0"
CACHE = ROOT / "data/interim/industrial_sites"
CACHE.mkdir(parents=True, exist_ok=True)
UTM = 32610


def land_use():
    fr = [gpd.read_parquet(OVT / f) for f in ("region5_land_use.parquet", "base_land_use.parquet")]
    d = gpd.GeoDataFrame(pd.concat(fr, ignore_index=True).drop_duplicates("id"), geometry="geometry", crs=4326)
    d = d[d.geom_type.isin(["Polygon", "MultiPolygon"])].reset_index(drop=True)
    d["pfx"] = d.id.str[:8]
    return d


def ring_ll(frame, ring):
    cx, cy = frame
    x, y = np.asarray(ring, float).T
    lo, la = vt.loc2ll(x, y, cx, cy)
    return shapely.make_valid(Polygon(np.c_[lo, la]))


def part_geoms(p, lu):
    """[(geometry, ref)] of one part spec."""
    out = []
    if "osm" in p:
        for pfx in p["osm"]:
            q = lu[lu.pfx == pfx]
            if not len(q):
                print("  !! missing OSM id", pfx)
            for _, r in q.iterrows():
                out.append((r.geometry, f"osm:{r.id}" + (f" ({r['name']})" if isinstance(r["name"], str) else "")))
    if "osm_box" in p:
        w, s, e, n, classes, excl = p["osm_box"]
        q = lu.cx[w:e, s:n]
        q = q[q["class"].isin(classes) | q.subtype.isin(classes)]
        rp = q.geometry.representative_point()
        q = q[(rp.x > w) & (rp.x < e) & (rp.y > s) & (rp.y < n) & ~q.pfx.isin(excl)]
        q = q[~q["name"].fillna("").str.contains("Caltrans|Maintenance Station|School|Park", regex=True)]
        q = q[q.to_crs(UTM).area > 2000]
        for _, r in q.iterrows():
            out.append((r.geometry, f"osm:{r.id}" + (f" ({r['name']})" if isinstance(r["name"], str) else "")))
    if "traced" in p:
        t = p["traced"]
        out.append((ring_ll(t["frame"], t["ring"]), f"traced on {t['sheet'].split('/')[-1]}"))
    if "hull" in p:
        h = p["hull"]
        c = gpd.GeoSeries([shapely.Point(*h["center"])], crs=4326).to_crs(UTM)
        fp = footprints(c.buffer(h["radius"]).to_crs(4326).iloc[0])
        if len(fp):
            hu = gpd.GeoSeries([shapely.union_all(fp.to_crs(UTM).geometry.values).convex_hull], crs=UTM)
            out.append((hu.buffer(h["buffer"]).to_crs(4326).iloc[0],
                        f"convex hull of {len(fp)} footprints within {h['radius']} m, +{h['buffer']} m"))
    if "files" in p:
        gs = []
        for f in p["files"]:
            gs += [shape(ft["geometry"]) for ft in json.loads((OUTD / f).read_text())["features"]]
        out.append((shapely.make_valid(shapely.union_all(gs)), "tint.py outline " + ", ".join(p["files"])))
    return out


def dated_footprints(s, geom, redate=False):
    """Today's footprints in the site + edition evidence (cached)."""
    fps = footprints(geom)
    if not len(fps):
        return fps, None
    cp = CACHE / f"presence_{s['site_id']}.parquet"
    b = geom.bounds
    eds = editions((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, bbox=(b[0], b[1], b[2], b[3]))
    eds = [e for e in eds if e[2] and e[2] >= s["founded"] - 25 and e[0] in (24000, 31680, 62500)]
    if cp.exists() and not redate:
        pr = pd.read_parquet(cp)
        if len(pr) and pr.fid.isin(fps.fid).mean() < 0.9:
            pr = None
    else:
        pr = None
    if pr is None:
        print(f"  dating {len(fps)} footprints on {len(eds)} editions")
        pr = presence(geom, fps, eds, max_half=3500.0, log=print)
        pr["fid"] = fps.fid.values[pr.fi.values.astype(int)] if len(pr) else pd.Series(dtype=str)
        pr["url"] = pr.sheet.map({e[1]: e[5] for e in eds})
        pr.to_parquet(cp)
    if not len(pr):
        for c in ("first_drawn", "last_absent", "est_start", "evidence", "first_url", "last_drawn"):
            fps[c] = np.nan
        return fps, pr
    fid_ix = {f: i for i, f in enumerate(fps.fid.values)}
    pr = pr[pr.fid.isin(fid_ix)].copy()
    pr["fi"] = pr.fid.map(fid_ix)
    st = start_years(pr, fps, s["founded"])
    fps = fps.join(st)
    first_url = pr[pr.present].sort_values("pyear").groupby("fi").url.first()
    fps["first_url"] = first_url.reindex(fps.index).values
    return fps, pr


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    redate = "--redate" in sys.argv
    lu = land_use()
    feats, known, rules, audit = [], [], [], []
    for s in SITES:
        if args and s["site_id"] not in args:
            continue
        print(s["site_id"])
        parts = []
        for p in s["parts"]:
            for g, ref in part_geoms(p, lu):
                parts.append((g, ref, p))
        geom = shapely.union_all([g for g, _, _ in parts]) if parts else None
        # parts marked on_top (a plant inside a quarry outline) are cut out of the site's other parts
        top = [g for g, _, p in parts if p.get("on_top")]
        if top:
            tu = shapely.union_all(top)
            parts = [(g if p.get("on_top") else shapely.make_valid(g.difference(tu)), ref, p) for g, ref, p in parts]
        fps, pr = (dated_footprints(s, geom, redate) if (geom is not None and s.get("date")) else (None, None))
        # ---- footprints: evidence vs the live map
        if fps is not None and len(fps):
            f0 = s["founded"]
            drawn = fps.first_drawn.notna()
            # a real roll year later than the last edition that still draws the footprint means
            # the building was (re)built after that map: a new house on the site of base housing,
            # a rebuilt tank - trust the roll (1900 / 0 placeholders are not real years)
            real_roll = np.isfinite(fps.roll_year) & (fps.roll_year > 1900) & (fps.roll_year != 1900)
            rebuilt = real_roll & (fps.roll_year > fps.last_drawn + 2)
            late = drawn & (fps.live_year > fps.first_drawn + 2) & ~rebuilt
            # too early: only where the founding year is documented
            early = (fps.live_year < f0 - 1) & (s["conf"] == "exact")
            fix = late | early
            new = np.where(late, fps.est_start, np.nan)
            new = np.where(early & drawn, np.maximum(fps.est_start, f0), new)
            new = np.where(early & ~drawn, f0, new)
            fps["new_year"] = new
            rp = fps.geometry.representative_point()
            named_pts = shapely.points([(n["lon"], n["lat"]) for n in NAMED])
            for i in np.nonzero(fix.values)[0]:
                r = fps.iloc[i]
                if shapely.contains(r.geometry, named_pts).any():
                    continue  # a researched row (NAMED) dates this footprint
                tank = r.circ > 0.85 and r.area_m2 > 40
                kind = "tank" if tank else "building"
                ev = r.evidence if isinstance(r.evidence, str) else ""
                if early.iloc[i] and not drawn.iloc[i]:
                    ev = f"not drawn on any edition; live year {r.live_year:.0f} predates the site -> founding year"
                roll = f"roll {r.roll_year:.0f} ({r.roll_src})" if np.isfinite(r.roll_year) else "no roll year"
                known.append(dict(
                    id=f"{s['site_id']}_{str(r.fid).split(':')[-1][:8]}",
                    name=f"{s['label']}: {kind} ({r.area_m2:.0f} m2)",
                    lat=round(rp.y.iloc[i], 6), lon=round(rp.x.iloc[i], 6),
                    start_year=round(float(r.new_year), 1), end_year=9999,
                    source_url=r.first_url if isinstance(r.first_url, str) else s["src"],
                    note=f"USGS editions: {ev}; site founded {f0:g}; live map {r.live_year:.0f}, {roll}. "
                         f"Footprint {r.fid}.",
                    county=s["county"]))
            d = fps.live_year - fps.new_year
            audit.append(dict(site_id=s["site_id"], name=s["label"], founded=f0, footprints=len(fps),
                              live_median=round(float(np.nanmedian(fps.live_year)), 0),
                              live_p10=round(float(np.nanpercentile(fps.live_year.dropna(), 10)), 0) if fps.live_year.notna().any() else np.nan,
                              drawn_on_maps=int(drawn.sum()), corrected=int(fix.sum()),
                              too_late=int(late.sum()), too_early=int(early.sum()),
                              median_shift_years=round(float(np.nanmedian(d[fix])), 0) if fix.any() else 0,
                              max_shift_years=round(float(np.nanmax(np.abs(d[fix]))), 0) if fix.any() else 0))
        elif geom is not None:
            fp = footprints(geom)
            audit.append(dict(site_id=s["site_id"], name=s["label"], founded=s["start"], footprints=len(fp),
                              live_median=round(float(np.nanmedian(fp.live_year)), 0) if len(fp) else np.nan,
                              live_p10=round(float(np.nanpercentile(fp.live_year.dropna(), 10)), 0) if len(fp) and fp.live_year.notna().any() else np.nan,
                              drawn_on_maps=np.nan, corrected=0, too_late=0, too_early=0,
                              median_shift_years=0, max_shift_years=0))
        # ---- parts -> features
        for k, (g, ref, p) in enumerate(parts):
            y0 = p.get("start", s["start"])
            if p.get("auto") and fps is not None and len(fps):
                inside = fps[shapely.contains(shapely.buffer(g, 0.0002), fps.geometry.representative_point().values)]
                ests = np.sort(inside.est_start.dropna().values)
                at_founding = inside.evidence.fillna("").str.startswith("drawn on the first edition").sum()
                if at_founding >= 3:
                    y0 = s["start"]  # the part's tanks / buildings are on the first maps after the founding
                    ref += f"; {at_founding} footprints drawn on the first edition after the founding"
                elif len(ests) >= 3:
                    y0 = max(s["start"], float(ests[2]))  # when its 3rd footprint first appears
                    ref += f"; start = 3rd-earliest edition date of its {len(ests)} drawn footprints"
            pieces = [gg for gg in getattr(shapely.make_valid(g), "geoms", [g])
                      if gg.geom_type in ("Polygon", "MultiPolygon") and not gg.is_empty]
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
        # ---- site rules
        if geom is not None and s["conf"] == "exact" and s.get("floor", True):
            rules.append(dict(site_id=s["site_id"], ring_type="site", year=s.get("founded", s["start"]),
                              applies_to="all_pre", max_year="",
                              evidence=f"{s['label']} founded {s.get('founded', s['start']):g}: no footprint inside "
                                       f"can be older", source_url=s["src"]))
        if geom is not None and s.get("date"):
            rules.append(dict(site_id=s["site_id"], ring_type="site", year=s.get("founded", s["start"]),
                              applies_to="named", max_year="",
                              evidence="footprints dated by the USGS editions that first draw them: "
                                       "known_dates_industrial.csv", source_url=s["src"]))
    if args:
        print("partial run: not writing outputs")
        print(pd.DataFrame(audit).to_string())
        return
    feats.sort(key=lambda f: (f["properties"]["site_id"], f["properties"]["part_id"]))
    (OUTD / "sites.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    pd.DataFrame(NAMED + known).to_csv(OUTD / "known_dates_industrial.csv", index=False)
    pd.DataFrame(rules).to_csv(OUTD / "building_dates.csv", index=False)
    pd.DataFrame(audit).to_csv(OUTD / "traced" / "audit.csv", index=False)
    print(len(feats), "parts,", len(known), "dated footprints,", len(rules), "rules")
    print(pd.DataFrame(audit).to_string())


if __name__ == "__main__":
    main()
