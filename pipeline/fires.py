"""Wildfires (and other disasters) that destroyed buildings — the ten counties.

The map shows a building iff start_year <= year < end_year. Houses rebuilt after the 2017
and 2020 wildfires carry the rebuild year in the county rolls, so Coffey Park, Fountaingrove,
Boulder Creek … were empty before 2018 / 2021 and nothing burned. This module brings in

  * CAL FIRE Damage Inspection (DINS) structure points (every structure inspected since 2013),
  * CAL FIRE FRAP fire perimeters (all years),
  * MTBS burn severity (high-severity patches, 1984 →),

and gives the two building stages what they need:

  python fires.py download    data/raw/fires/ (cached, idempotent)
  python fires.py build       data/manual/fires/ (committed: perimeters.geojson,
                              severity_high.geojson, destroyed_structures.csv, fires.csv)
  python fires.py test NAME   run the building logic on a small box (see TEST_BOXES)

Hooks (both are no-ops when data/manual/fires/ is missing):

  rebuild_years(g, xy, year, conf, end)   region_buildings.assign_years: a footprint standing
        today where DINS recorded a destroyed structure is the REBUILD. If its year is not
        after the fire it starts after the fire (fire date + the rebuild lag measured per fire
        from the parcels whose roll year is after the fire; `estimated`).
  fire_predecessors(today, pred)          region_predecessors: what stood until the fire —
        on the rebuild's outline where a footprint stands today, else a plain outline typical
        of the DINS structure type; and, for older fires without structure data
        (clearances.csv), on the outline of each building recorded as built in the years
        after the fire. All end EXACTLY at the fire date (decimal year) so a neighbourhood
        goes at once; `year_confidence = procedural`, ids `fire:<…>`.

The viewer tints every building that ends ("scorched" endTint in layers/buildings.ts), so no
extra flag is needed for the burn.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from common import INTERIM, MANUAL, RAW, log

RAW_FIRES = RAW / "fires"
OUT = MANUAL / "fires"
UTM = "EPSG:32610"

CALFIRE = "https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/arcgis/rest/services"
DINS_URL = f"{CALFIRE}/POSTFIRE_MASTER_DATA_SHARE/FeatureServer/0/query"
FRAP_URL = f"{CALFIRE}/California_Historic_Fire_Perimeters/FeatureServer/0/query"   # "California Fire Perimeters (all)"
MTBS_URL = "https://imagery.geoplatform.gov/iipp/rest/services/Fire_Aviation/USFS_EDW_MTBS_CONUS/ImageServer"

MIN_ACRES = 300.0
MATCH_M = 10.0          # a DINS point within this distance of a footprint is that building


def _session():
    """Plain client (no project name in the User-Agent: these are third-party services)."""
    import os
    import requests
    s = requests.Session()
    s.headers["User-Agent"] = "python-requests (fire-data download)"
    ca = "/root/.ccr/ca-bundle.crt"
    if os.path.exists(ca) and not os.environ.get("REQUESTS_CA_BUNDLE"):
        s.verify = ca
    return s


def _get(s, url, params, tries=5, **kw):
    delay = 2.0
    for k in range(tries):
        try:
            r = s.get(url, params=params, timeout=300, **kw)
            if r.status_code == 200:
                return r
            log(f"fires: HTTP {r.status_code} {url} (try {k + 1})")
        except Exception as e:  # noqa: BLE001
            log(f"fires: {e!r} {url} (try {k + 1})")
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"failed to fetch {url}")


def decimal_year(ms) -> float:
    """Epoch milliseconds (ArcGIS date) -> decimal year (UTC)."""
    d = dt.datetime(1970, 1, 1) + dt.timedelta(milliseconds=float(ms))
    y0 = dt.datetime(d.year, 1, 1)
    return d.year + (d - y0).total_seconds() / ((dt.datetime(d.year + 1, 1, 1) - y0).total_seconds())


def date_year(y, m, d) -> float:
    d0 = dt.date(int(y), 1, 1)
    return int(y) + (dt.date(int(y), int(m), int(d)) - d0).days / ((dt.date(int(y) + 1, 1, 1) - d0).days)


def _bbox():
    from extent import POLY, MARGIN_DEG
    b = POLY.buffer(MARGIN_DEG).bounds
    return ",".join(f"{v:.4f}" for v in b)


# ----------------------------------------------------------------------------- download

def download_dins(s):
    """CAL FIRE DINS: every inspected structure inside the map's bounding box."""
    path = RAW_FIRES / "dins.jsonl"
    if path.exists():
        return path
    rows, off = [], 0
    while True:
        r = _get(s, DINS_URL, {"where": "1=1", "geometry": _bbox(), "geometryType": "esriGeometryEnvelope",
                               "inSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "*",
                               "returnGeometry": "true", "outSR": 4326, "orderByFields": "OBJECTID",
                               "resultOffset": off, "resultRecordCount": 2000, "f": "json"}).json()
        fs = r.get("features", [])
        for f in fs:
            a = f["attributes"]
            g = f.get("geometry") or {}
            a["lon"], a["lat"] = g.get("x"), g.get("y")
            rows.append(a)
        log(f"fires: DINS {len(rows)} structures")
        if not r.get("exceededTransferLimit") and len(fs) < 2000:
            break
        off += len(fs)
    RAW_FIRES.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text("\n".join(json.dumps(a, separators=(",", ":")) for a in rows))
    tmp.rename(path)
    return path


def download_frap(s):
    """FRAP "California Fire Perimeters (all)": every perimeter touching the bounding box."""
    path = RAW_FIRES / "frap_perimeters.geojson"
    if path.exists():
        return path
    feats, off = [], 0
    while True:
        r = _get(s, FRAP_URL, {"where": "1=1", "geometry": _bbox(), "geometryType": "esriGeometryEnvelope",
                               "inSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "*",
                               "returnGeometry": "true", "outSR": 4326, "geometryPrecision": 5,
                               "orderByFields": "OBJECTID", "resultOffset": off, "resultRecordCount": 250,
                               "f": "geojson"}).json()
        fs = r.get("features", [])
        feats += fs
        log(f"fires: FRAP {len(feats)} perimeters")
        if len(fs) < 250 and not (r.get("properties") or {}).get("exceededTransferLimit"):
            break
        off += len(fs)
    RAW_FIRES.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")))
    tmp.rename(path)
    return path


def download_mtbs(s, years):
    """MTBS thematic burn severity (30 m; 1 unburned-low, 2 low, 3 moderate, 4 HIGH,
    5 increased greenness, 6 mask), one GeoTIFF per fire year over the map (UTM 10N)."""
    import pyproj
    from extent import POLY
    out = RAW_FIRES / "mtbs"
    out.mkdir(parents=True, exist_ok=True)
    tr = pyproj.Transformer.from_crs(4326, UTM, always_xy=True)
    xs, ys = tr.transform(*np.array(POLY.exterior.coords).T)
    x0, x1 = math.floor(min(xs) / 30) * 30, math.ceil(max(xs) / 30) * 30
    y0, y1 = math.floor(min(ys) / 30) * 30, math.ceil(max(ys) / 30) * 30
    done = []
    for y in years:
        p = out / f"mtbs_{y}.tif"
        if not p.exists():
            t0 = int(dt.datetime(y, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
            t1 = int(dt.datetime(y, 12, 31, tzinfo=dt.timezone.utc).timestamp() * 1000)
            try:
                r = _get(s, f"{MTBS_URL}/exportImage",
                         {"bbox": f"{x0},{y0},{x1},{y1}", "bboxSR": 32610, "imageSR": 32610,
                          "size": f"{(x1 - x0) // 30},{(y1 - y0) // 30}", "format": "tiff", "pixelType": "U8",
                          "noData": 0, "interpolation": "RSP_NearestNeighbor", "time": f"{t0},{t1}",
                          "renderingRule": json.dumps({"rasterFunction": "None"}), "f": "image"}, tries=3)
            except RuntimeError as e:
                log(f"fires: MTBS {y}: {e}")
                continue
            if not r.content[:4] in (b"II*\x00", b"MM\x00*"):
                log(f"fires: MTBS {y}: not a TIFF ({r.content[:120]!r})")
                continue
            p.write_bytes(r.content)
            log(f"fires: MTBS {y} {len(r.content) // 1024} kB")
        done.append(p)
    return done


SONOMA_PERMITS = ("https://services1.arcgis.com/P5Mv5GY5S66M8Z1Q/arcgis/rest/services/"
                  "Wildfire_Rebuild_Permits_Public_View_Layer/FeatureServer/0/query")
SANTA_CRUZ_PERMITS = "https://sccgis.santacruzcountyca.gov/server/rest/services/czucleanup/MapServer/5/query"


def download_permits(s):
    """Rebuild permits: Permit Sonoma "Wildfire Rebuild Permits" (unincorporated Sonoma County:
    2017 complex, Kincade, Glass, LNU) and Santa Cruz County "Recovery Permit Center" (CZU)."""
    for name, url in (("sonoma_rebuild_permits.json", SONOMA_PERMITS), ("santa_cruz_recovery_permits.json", SANTA_CRUZ_PERMITS)):
        path = RAW_FIRES / name
        if path.exists():
            continue
        rows, off = [], 0
        try:
            while True:
                r = _get(s, url, {"where": "1=1", "outFields": "*", "returnGeometry": "false", "orderByFields": "OBJECTID",
                                  "resultOffset": off, "resultRecordCount": 1000, "f": "json"}, tries=3).json()
                fs = [f["attributes"] for f in r.get("features", [])]
                rows += fs
                if len(fs) < 1000:
                    break
                off += len(fs)
        except RuntimeError as e:
            log(f"fires: {name}: {e} — skipped")
            continue
        RAW_FIRES.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, separators=(",", ":")))
        log(f"fires: {len(rows)} permits -> {name}")


def download():
    s = _session()
    download_dins(s)
    download_frap(s)
    download_permits(s)
    fr = json.loads((RAW_FIRES / "frap_perimeters.geojson").read_text())
    years = sorted({int(f["properties"]["YEAR_"]) for f in fr["features"]
                    if f["properties"].get("YEAR_") and (f["properties"].get("GIS_ACRES") or 0) >= 1000
                    and int(f["properties"]["YEAR_"]) >= 1984})
    download_mtbs(s, years)


# ----------------------------------------------------------------------------- build

COUNTIES = {"Sonoma", "Napa", "Solano", "Marin", "Contra Costa", "Alameda", "San Francisco", "San Mateo",
            "Santa Clara", "Santa Cruz"}


def _slug(name, year):
    import re
    s = re.sub(r"[^a-z0-9]+", "_", str(name or "unnamed").lower()).strip("_") or "unnamed"
    s = s.replace("lightning_complex", "").replace("lightning_cmplx", "").strip("_") or s
    return f"{s}_{int(year)}"


def _iso(ms):
    if ms is None or not np.isfinite(ms):
        return None
    return (dt.datetime(1970, 1, 1) + dt.timedelta(milliseconds=float(ms))).strftime("%Y-%m-%d")


def _overrides():
    """data/manual/fires/fire_dates.csv: researched display names and the date the structures
    burned (a complex's alarm date can be days before its run into the towns)."""
    p = OUT / "fire_dates.csv"
    if not p.exists():
        return {}
    t = pd.read_csv(p)
    return {r.fire_id: r for r in t.itertuples()}


def build():
    import geopandas as gpd
    import shapely
    from extent import POLY, MARGIN_DEG
    OUT.mkdir(parents=True, exist_ok=True)
    ext = POLY.buffer(MARGIN_DEG)
    ov = _overrides()
    # --- structures
    d = pd.DataFrame([json.loads(l) for l in (RAW_FIRES / "dins.jsonl").read_text().splitlines()])
    d = d[d.DAMAGE.astype(str).str.startswith("Destroyed") & d.lon.notna()]
    inx = shapely.contains(ext, shapely.points(d.lon.values, d.lat.values))
    d = d[(d.COUNTY.isin(COUNTIES) | (d.COUNTY.isna() & inx)) & inx].reset_index(drop=True)
    d["alarm"] = d.INCIDENTSTARTDATE.map(decimal_year)
    # --- perimeters
    fr = gpd.read_file(RAW_FIRES / "frap_perimeters.geojson")
    fr = fr[fr.geometry.notna() & fr.YEAR_.notna()].copy()
    fr["geometry"] = shapely.make_valid(fr.geometry.values)
    fr = fr[fr.intersects(ext)].reset_index(drop=True)
    fu = fr.to_crs(UTM)
    du = gpd.GeoDataFrame(d[["OBJECTID"]], geometry=gpd.points_from_xy(d.lon, d.lat), crs=4326).to_crs(UTM)
    # each destroyed structure -> the perimeter of its year that holds it (else the nearest within 1 km)
    fid = np.array([""] * len(d), dtype=object)
    names = fr.FIRE_NAME.fillna("unnamed").astype(str).values
    ids, seen = [], {}
    for n, y in zip(names, fr.YEAR_.values):
        k = _slug(n, y)
        seen[k] = seen.get(k, 0) + 1
        ids.append(k if seen[k] == 1 else f"{k}_{seen[k]}")
    fr["fire_id"] = ids
    dy = np.floor(d.alarm.values).astype(int)
    for y in np.unique(dy):
        sel = np.nonzero(dy == y)[0]
        cand = np.nonzero(fr.YEAR_.values.astype(int) == y)[0]
        if not len(cand):
            continue
        tree = shapely.STRtree(fu.geometry.values[cand])
        a, b = tree.query_nearest(du.geometry.values[sel], max_distance=1000, all_matches=False)
        fid[sel[a]] = fr.fire_id.values[cand[b]]
    miss = fid == ""
    fid[miss] = [_slug(n, y) for n, y in zip(d.INCIDENTNAME.values[miss], dy[miss])]
    d["fire_id"] = fid
    n_destroyed = d.groupby("fire_id").size()
    keep = (fr.GIS_ACRES.fillna(0).values >= MIN_ACRES) | fr.fire_id.isin(n_destroyed.index).values
    fr, fu = fr[keep].reset_index(drop=True), fu[keep].reset_index(drop=True)
    extu = gpd.GeoSeries([ext], crs=4326).to_crs(UTM).values[0]
    feats, fyear = [], {}
    for i, r in enumerate(fr.itertuples()):
        acres = float(r.GIS_ACRES or 0)
        tol = 12 if acres < 2000 else (25 if acres < 20000 else 45)
        geom = shapely.intersection(fu.geometry.values[i], extu)
        geom = shapely.make_valid(shapely.simplify(geom, tol, preserve_topology=True))
        polys = [p for p in shapely.get_parts(geom) if p.geom_type == "Polygon" and p.area > 2000]
        if not polys:
            continue
        geom = gpd.GeoSeries([shapely.MultiPolygon(polys) if len(polys) > 1 else polys[0]], crs=UTM).to_crs(4326).values[0]
        alarm = float(r.ALARM_DATE) if r.ALARM_DATE is not None and np.isfinite(r.ALARM_DATE) else None
        o = ov.get(r.fire_id)
        if o is not None and isinstance(o.date, str):
            year, est = date_year(*o.date.split("-")), False
        elif alarm is not None and int(decimal_year(alarm)) == int(r.YEAR_):
            year, est = decimal_year(alarm), False
        else:
            year, est = int(r.YEAR_) + 0.7, True     # no alarm date on record: the fire season (September)
        fyear[r.fire_id] = year
        name = o.name if o is not None and isinstance(o.name, str) else str(r.FIRE_NAME or "unnamed").strip().title()
        feats.append({"type": "Feature", "properties": {
            "fire_id": r.fire_id, "name": name, "year": round(year, 3), "date_estimated": est,
            "alarm_date": _iso(alarm), "cont_date": _iso(r.CONT_DATE), "acres": round(acres, 1),
            "destroyed": int(n_destroyed.get(r.fire_id, 0)),
            "source": f"CAL FIRE FRAP fire perimeters (all), OBJECTID {int(r.OBJECTID)}"},
            "geometry": json.loads(shapely.to_geojson(shapely.set_precision(geom, 1e-5)))})
    feats.sort(key=lambda f: f["properties"]["year"])
    (OUT / "perimeters.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")))
    log(f"fires: {len(feats)} perimeters -> perimeters.geojson ({(OUT / 'perimeters.geojson').stat().st_size // 1024} kB)")
    # --- destroyed structures: the date the structure burned (researched run date, else alarm date)
    date = np.array([fyear.get(f, np.nan) for f in d.fire_id.values])
    for f, o in ov.items():
        if isinstance(o.date, str):
            date[d.fire_id.values == f] = date_year(*o.date.split("-"))
    date = np.where(np.isfinite(date) & (np.floor(date) == np.floor(d.alarm.values)), date, d.alarm.values)
    yb = pd.to_numeric(d.YEARBUILT, errors="coerce")
    out = pd.DataFrame({
        "id": ["dins" + str(int(v)) for v in d.OBJECTID.values], "fire_id": d.fire_id.values,
        "incident": d.INCIDENTNAME.values, "date": np.round(date, 3),
        "lon": np.round(d.lon.values, 6), "lat": np.round(d.lat.values, 6),
        "structure_type": d.STRUCTURETYPE.values, "category": d.STRUCTURECATEGORY.values,
        "units": pd.to_numeric(d.NUMBEROFUNITPERSTRUCTURE, errors="coerce").astype("Int64").values,
        "year_built": yb.where((yb >= 1800) & (yb <= np.floor(date))).astype("Int64").values,
        "apn": d.APN.values, "county": d.COUNTY.values, "community": d.COMMUNITY.values, "damage": d.DAMAGE.values})
    out = out.sort_values(["date", "fire_id", "id"]).reset_index(drop=True)
    out.to_csv(OUT / "destroyed_structures.csv", index=False)
    log(f"fires: {len(out)} destroyed structures -> destroyed_structures.csv "
        f"({out.groupby('fire_id').size().sort_values(ascending=False).head(12).to_dict()})")
    build_permits()
    build_severity(feats)


def _norm_apn(a) -> str:
    return "".join(ch for ch in str(a) if ch.isdigit()).lstrip("0")


def build_permits():
    """rebuild_permits.csv: one row per dwelling rebuild permit that was completed — county,
    apn (digits), year (decimal), year_kind: `completed` (Santa Cruz: date the permit was
    closed) or `issued+1` (Sonoma publishes no final date: issue date + one year, estimated)."""
    rows = []
    p = RAW_FIRES / "sonoma_rebuild_permits.json"
    if p.exists():
        for a in json.loads(p.read_text()):
            if a.get("Status") != "Construction Complete" or a.get("Category") == "Bridge" or not a.get("Issue_Date"):
                continue
            rows.append({"county": "Sonoma", "apn": _norm_apn(a.get("APN")), "event": a.get("Event_Title"),
                         "category": a.get("Category"), "year": round(decimal_year(a["Issue_Date"]) + 1.0, 2),
                         "year_kind": "issued+1", "permit": a.get("Record_ID"),
                         "source": "Permit Sonoma Wildfire Rebuild Permits (public view)"})
    p = RAW_FIRES / "santa_cruz_recovery_permits.json"
    if p.exists():
        for a in json.loads(p.read_text()):
            if a.get("PERMITSTATUS") != "Closed" or a.get("WORKTYPE") != "DWELLING" or not a.get("STATUSDATE") or a.get("VOIDDATE"):
                continue
            rows.append({"county": "Santa Cruz", "apn": _norm_apn(a.get("PARCELNO")), "event": "2020 CZU Lightning Complex",
                         "category": a.get("PERMITTYPE"), "year": round(decimal_year(a["STATUSDATE"]), 2),
                         "year_kind": "completed", "permit": a.get("PERMITNO"),
                         "source": "Santa Cruz County Recovery Permit Center (czucleanup/MapServer/5)"})
    if not rows:
        return
    t = pd.DataFrame(rows)
    t = t[t.apn != ""].sort_values(["county", "apn", "year"]).reset_index(drop=True)
    t.to_csv(OUT / "rebuild_permits.csv", index=False)
    log(f"fires: {len(t)} completed rebuild permits -> rebuild_permits.csv ({t.groupby('county').size().to_dict()})")


def build_severity(feats=None):
    """MTBS class 4 (high severity) inside each kept perimeter of the year -> simplified
    polygons (patches and holes >= 4 ha, 45 m tolerance), one MultiPolygon per fire."""
    import geopandas as gpd
    import shapely
    files = sorted((RAW_FIRES / "mtbs").glob("mtbs_*.tif")) if (RAW_FIRES / "mtbs").exists() else []
    if not files:
        log("fires: no MTBS rasters (python fires.py download) — severity_high.geojson not written")
        return
    import rasterio
    from rasterio import features, windows
    if feats is None:
        feats = json.loads((OUT / "perimeters.geojson").read_text())["features"]
    per = gpd.GeoDataFrame.from_features(feats, crs=4326).to_crs(UTM)
    out = []
    for f in files:
        y = int(f.stem.split("_")[1])
        sel = per[np.floor(per.year.values).astype(int) == y]
        if not len(sel):
            continue
        with rasterio.open(f) as ds:
            for r in sel.itertuples():
                if r.acres < 1000:
                    continue
                b = r.geometry.bounds
                w = windows.from_bounds(*b, transform=ds.transform).round_offsets().round_lengths()
                w = w.intersection(windows.Window(0, 0, ds.width, ds.height))
                a = ds.read(1, window=w)
                tr = ds.window_transform(w)
                inside = features.rasterize([(r.geometry, 1)], out_shape=a.shape, transform=tr, fill=0, dtype="uint8")
                burnt = ((a >= 2) & (a <= 4) & (inside == 1)).sum()
                m = ((a == 4) & (inside == 1)).astype("uint8")
                if not m.any():
                    continue
                polys = [shapely.geometry.shape(g) for g, v in features.shapes(m, mask=m == 1, transform=tr)]
                g = shapely.union_all(polys).buffer(25).buffer(-25)          # close 1-pixel gaps
                g = shapely.make_valid(shapely.simplify(g, 45, preserve_topology=True))
                parts = [shapely.Polygon(p.exterior, [h for h in p.interiors if shapely.Polygon(h).area >= 40000])
                         for p in shapely.get_parts(g) if p.geom_type == "Polygon" and p.area >= 40000]
                if not parts:
                    continue
                g = shapely.MultiPolygon(parts)
                ll = gpd.GeoSeries([g], crs=UTM).to_crs(4326).values[0]
                out.append({"type": "Feature", "properties": {
                    "fire_id": r.fire_id, "name": r.name, "year": r.year,
                    "high_ha": round(float(m.sum()) * 0.09, 1), "burnt_ha": round(float(burnt) * 0.09, 1),
                    "source": f"MTBS thematic burn severity {y}, class 4 (high), 30 m"},
                    "geometry": json.loads(shapely.to_geojson(shapely.make_valid(shapely.set_precision(ll, 1e-4))))})
    (OUT / "severity_high.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": out}, separators=(",", ":")))
    log(f"fires: high severity for {len(out)} fires -> severity_high.geojson ({(OUT / 'severity_high.geojson').stat().st_size // 1024} kB)")


# ----------------------------------------------------------------------------- buildings

# plain outlines by DINS structure type where no footprint stands today:
# (width m, depth m, storeys, storey height m, use for the building palette); None = not a building
PLAIN = {
    "Single Family Residence Single Story": (15.0, 11.0, 1, 3.2, "dwelling"),
    "Single Family Residence Multi Story": (12.0, 10.0, 2, 3.0, "dwelling"),
    "Multi Family Residence Single Story": (26.0, 11.0, 1, 3.2, "flats"),
    "Multi Family Residence Multi Story": (26.0, 12.0, 2, 3.0, "flats"),
    "Mobile Home Single Wide": (18.0, 4.3, 1, 2.8, "dwelling"),
    "Mobile Home Double Wide": (18.0, 7.3, 1, 2.8, "dwelling"),
    "Mobile Home Triple Wide": (18.0, 11.0, 1, 2.8, "dwelling"),
    "Commercial Building Single Story": (24.0, 15.0, 1, 4.5, "store"),
    "Commercial Building Multi Story": (24.0, 15.0, 2, 4.0, "store"),
    "Mixed Commercial/Residential": (18.0, 12.0, 2, 3.6, "store"),
    "School": (30.0, 12.0, 1, 4.0, "school"),
    "Church": (22.0, 12.0, 1, 6.0, "church"),
    "Hospital": (30.0, 18.0, 2, 4.0, "hall"),
    "Utility Misc Structure": (7.0, 5.0, 1, 2.8, "shed"),
    "Utility or Miscellaneous Structure > 120 sqft": (7.0, 5.0, 1, 2.8, "shed"),
    "Motor Home": None,          # a vehicle
    "Infrastructure": None,      # tanks, bridges, pump houses: not building massing
}
MAIN_TYPES = ("Single Family", "Multi Family", "Mobile Home", "Commercial", "Mixed", "School", "Church", "Hospital")


def structures():
    """data/manual/fires/destroyed_structures.csv with UTM coordinates (x, y); None if missing."""
    p = OUT / "destroyed_structures.csv"
    if not p.exists():
        return None
    import pyproj
    t = pd.read_csv(p)
    t["x"], t["y"] = pyproj.Transformer.from_crs(4326, UTM, always_xy=True).transform(t.lon.values, t.lat.values)
    t["main"] = t.structure_type.astype(str).str.startswith(MAIN_TYPES)
    if globals().get("ONLY_BOX"):
        b = ONLY_BOX
        t = t[(t.lon >= b[0]) & (t.lon <= b[2]) & (t.lat >= b[1]) & (t.lat <= b[3])].reset_index(drop=True)
    return t


def match(st, geoms, xy):
    """Destroyed structures -> the footprint standing there today.
    st: structures(); geoms: footprint polygons (UTM, shapely array); xy: their representative
    points. Returns (fp, dist): per structure the footprint index (-1: none) and its distance —
    the footprint the point lies in, else the nearest within MATCH_M."""
    import shapely
    from scipy.spatial import cKDTree
    fp = np.full(len(st), -1, np.int64)
    dist = np.full(len(st), np.inf)
    if not len(st) or not len(geoms):
        return fp, dist
    # only footprints near a structure (a 2.5 M-polygon index is slow to build)
    d, _ = cKDTree(st[["x", "y"]].values).query(xy, k=1, distance_upper_bound=250.0)
    cand = np.nonzero(np.isfinite(d))[0]
    if not len(cand):
        return fp, dist
    tree = shapely.STRtree(np.asarray(geoms)[cand])
    pts = shapely.points(st.x.values, st.y.values)
    a, b = tree.query_nearest(pts, max_distance=MATCH_M, all_matches=False)
    fp[a] = cand[b]
    dist[a] = shapely.distance(pts[a], np.asarray(geoms)[cand[b]])
    return fp, dist


def footprints_near(st, radius=250.0, columns=("id", "source_dataset", "source_update_time", "county")):
    """Test helper: today's Overture footprints within `radius` of the given structures
    (GeoDataFrame, UTM), with their candidate years from region5_footprint_years.parquet."""
    import geopandas as gpd
    import pyarrow.parquet as pq
    import pyproj
    import shapely
    from scipy.spatial import cKDTree
    from common import region_overture_files
    tree = cKDTree(st[["x", "y"]].values)
    tr = pyproj.Transformer.from_crs(4326, UTM, always_xy=True)
    parts = []
    for f in region_overture_files("building"):
        for b in pq.ParquetFile(f).iter_batches(batch_size=200_000, columns=list(columns) + ["px", "py", "geometry"]):
            t = b.to_pandas()
            x, y = tr.transform(t.px.values, t.py.values)
            d, _ = tree.query(np.column_stack([x, y]), k=1, distance_upper_bound=radius)
            t = t[np.isfinite(d)]
            if len(t):
                parts.append(t)
    t = pd.concat(parts, ignore_index=True)
    g = gpd.GeoDataFrame(t.drop(columns="geometry"), geometry=shapely.from_wkb(t.geometry.values), crs=4326)
    g = g.explode(index_parts=False)
    g = g[g.geometry.geom_type == "Polygon"].to_crs(UTM).reset_index(drop=True)
    g = g[g.geometry.area.values > 12].reset_index(drop=True)
    fy = pd.read_parquet(INTERIM / "region5_footprint_years.parquet", filters=[("id", "in", list(set(g.id)))])
    return g.merge(fy.drop(columns=[c for c in ("county",) if c in fy]), on="id", how="left")


# ----------------------------------------------------------------------------- hooks

FALLBACK_M = 40.0        # a house whose DINS point is off its outline: nearest recorded rebuild within this
REBUILD_SPAN = 15.0      # older fires (clearances.csv): a building dated within this many years after the fire is a rebuild
STATE: dict = {}         # rebuild_years -> add_predecessors (same process); also INTERIM/fire_structures.parquet
CURRENT = ("Esri Community Maps",)   # county-contributed outlines that post-date the fires (README, "Is it a rebuild?")
ONLY_BOX = None          # test runs: (lon0, lat0, lon1, lat1)
REBUILT = ("rebuilt", "rebuilt_permit", "rebuilt_est")


def _h(key) -> float:
    import zlib
    return (zlib.crc32(str(key).encode()) % 100003) / 100003.0


def _permits():
    p = OUT / "rebuild_permits.csv"
    if not p.exists():
        return {}
    t = pd.read_csv(p, dtype={"apn": str}).sort_values("year", ascending=False)
    return {(c, a): (float(y), k) for c, a, y, k in zip(t.county, t.apn, t.year, t.year_kind)}   # earliest wins


def _datasets(ids):
    """Overture source dataset per footprint id ('' when the raw files are not there)."""
    try:
        from common import read_region_overture
        t = read_region_overture("building", ["id", "source_dataset"], filters=[("id", "in", list(set(ids)))]).to_pandas()
        m = dict(zip(t.id.astype(str), t.source_dataset.astype(str)))
    except Exception as e:  # noqa: BLE001
        log(f"fires: no Overture source datasets ({e})")
        m = {}
    return np.array([m.get(i, "") for i in ids], dtype=object)


def _num(g, col, idx):
    if col not in g:
        return np.full(len(idx), np.nan)
    return pd.to_numeric(g[col], errors="coerce").astype("float64").to_numpy(dtype=float, na_value=np.nan)[idx].copy()


def rebuild_years(g, xy, year, conf, end, src=None):
    """region_buildings.assign_years hook (after every other rule). g: today's footprints
    (EPSG:4326, with `id`, the candidate-year columns and `fbuy`), xy: their UTM points.

    Every destroyed DINS structure is matched to the footprint standing there today (point
    inside, or within MATCH_M; a house whose point is off its outline takes the nearest
    recorded rebuild within FALLBACK_M). What the footprint is, best evidence first:
      rebuilt         its recorded year is after the fire                      -> unchanged
      rebuilt_permit  a completed rebuild permit on the parcel (rebuild_permits.csv)
                                                                               -> the permit's year
      rebuilt_est     its outline comes from a source that post-dates the fire (county
                      footprints; OSM / Microsoft outlines only for fires where most of
                      them are recorded rebuilds) -> fire + the fire's measured rebuild lag
      gone            none of these: the outline is the building that burned   -> ends at the fire
    (FIRE_UNCONFIRMED=rebuild in the environment turns `gone` into `rebuilt_est`.)
    Researched buildings (known: / early: sources) are never touched.
    Returns (year, conf, end); the per-structure table is kept for add_predecessors."""
    st = structures()
    STATE.clear()
    if st is None or not len(st):
        STATE["structures"] = pd.DataFrame({"status": []})
        return year, conf, end
    import os
    import geopandas as gpd
    import shapely
    from scipy.spatial import cKDTree
    year = np.asarray(year, float).copy()
    end = np.asarray(end, float).copy()
    conf = np.asarray(conf, dtype=object).copy()
    n = len(st)
    d, _ = cKDTree(st[["x", "y"]].values).query(xy, k=1, distance_upper_bound=250.0)
    cand = np.nonzero(np.isfinite(d))[0]
    date = st.date.values.astype(float)
    main = st.main.values.astype(bool)
    fire = st.fire_id.values
    fp = np.full(n, -1, np.int64)
    if len(cand):
        geoms = np.asarray(gpd.GeoSeries(np.asarray(g.geometry.values[cand], dtype=object), crs=4326).to_crs(UTM).values)
        ids = g["id"].iloc[cand].astype(str).values if "id" in g else np.array([f"fp{k}" for k in cand], dtype=object)
        cxy = xy[cand]
        cy = year[cand]
        cexact = (conf[cand] == "exact") & np.isfinite(cy)
        locked = np.zeros(len(cand), bool)
        if src is not None:
            locked = pd.Series(np.asarray(src, dtype=object)[cand]).astype(str).str.startswith(("known:", "early:")).values
        vend, fbuy = _num(g, "year_commercial", cand), _num(g, "fbuy", cand)
        area = shapely.area(geoms)
        tree = shapely.STRtree(geoms)
        pts = shapely.points(st.x.values, st.y.values)
        a, b = tree.query_nearest(pts, max_distance=MATCH_M, all_matches=False)
        fp[a] = b
        # a house whose point sits on the driveway / street front: the nearest recorded rebuild
        claimed = set(fp[fp >= 0].tolist())
        need = np.nonzero((fp < 0) & main)[0]
        n_fb = 0
        if len(need):
            ia, ib = tree.query(pts[need], predicate="dwithin", distance=FALLBACK_M)
            dn = date[need[ia]]
            ok = cexact[ib] & (cy[ib] > dn) & (cy[ib] <= dn + 12) & (area[ib] >= 50) & ~locked[ib]
            ia, ib = ia[ok], ib[ok]
            dd = shapely.distance(pts[need[ia]], geoms[ib])
            for k in np.argsort(dd, kind="stable"):
                i, j = need[ia[k]], int(ib[k])
                if fp[i] < 0 and j not in claimed:
                    fp[i] = j
                    claimed.add(j)
                    n_fb += 1
    else:
        ids, cy, cexact = np.array([], dtype=object), np.array([]), np.array([], bool)
    has = fp >= 0
    j = np.maximum(fp, 0)
    # one structure speaks for a footprint: the house before the shed, the later fire before the earlier
    prim = np.zeros(n, bool)
    seen = set()
    for i in np.lexsort((-date, ~main)):
        if has[i] and fp[i] not in seen:
            seen.add(fp[i])
            prim[i] = True
    status = np.array(["none"] * n, dtype=object)
    old = pd.to_numeric(st.year_built, errors="coerce").astype("float64").to_numpy(dtype=float, na_value=np.nan).copy()
    old_src = np.where(np.isfinite(old), "dins", "").astype(object)
    reb = np.full(n, np.nan)
    cal = {}
    perm = _permits()
    got = [perm.get((c, a_), (np.nan, "")) for c, a_ in zip(st.county.values, st.apn.map(_norm_apn).values)]
    py = np.array([v[0] for v in got], float)
    pk = np.array([v[1] for v in got], dtype=object)
    py = np.where(main & (py > date), np.maximum(py, np.floor(date) + 1.0), np.nan)   # a completed dwelling permit on the parcel
    if has.any():
        after = has & cexact[j] & (cy[j] > date)
        permit = has & ~after & np.isfinite(py)
        ds = np.array([""] * n, dtype=object)
        ds[has] = _datasets(ids[np.unique(fp[has])])[np.searchsorted(np.unique(fp[has]), fp[has])]
        confirmed = after | permit
        current = has & np.isin(ds, CURRENT)
        for f in np.unique(fire[has]):
            for s_ in ("OpenStreetMap", "Microsoft ML Buildings"):
                m = has & (fire == f) & (ds == s_)
                mp = m & prim
                share = float(confirmed[mp].mean()) if mp.sum() >= 20 else 0.0
                cal[f"{f}|{s_}"] = (int(mp.sum()), round(share, 2))
                if share >= 0.5:
                    current |= m
        if os.environ.get("FIRE_UNCONFIRMED") == "rebuild":
            current |= has
        status[has] = np.where(after, "rebuilt", np.where(permit, "rebuilt_permit", np.where(current, "rebuilt_est", "gone")))[has]
        status[has & ~prim] = "dup"
        status[has & locked[j]] = "locked"
        # --- what stood before: DINS parcel year > the roll's pre-fire year > the vendor copy > neighbours
        m = np.isnan(old) & has & cexact[j] & (cy[j] < np.floor(date))
        old[m], old_src[m] = cy[j][m], "roll"
        m = np.isnan(old) & has & (vend[j] > 1800) & (vend[j] < np.floor(date))
        old[m], old_src[m] = vend[j][m], "vendor"
    if len(cand):
        for f in np.unique(fire[np.isnan(old)]):
            sel = np.nonzero(np.isnan(old) & (fire == f))[0]
            pool = np.nonzero(cexact & (cy < np.floor(date[sel].min()) - 0.5))[0]
            if len(pool) < 3:
                continue
            dd, ii = cKDTree(cxy[pool]).query(st[["x", "y"]].values[sel], k=min(12, len(pool)), distance_upper_bound=300.0)
            vals = np.where(np.isfinite(dd), cy[pool][np.minimum(ii, len(pool) - 1)], np.nan)
            cnt = np.isfinite(vals).sum(axis=1)
            with np.errstate(all="ignore"):
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    med = np.nanmedian(vals, axis=1)
            ok = cnt >= 3
            old[sel[ok]], old_src[sel[ok]] = med[ok], "neighbours"
        m = np.nonzero(np.isnan(old))[0]
        if len(m):   # HISDAC first built-up year of the 250 m cell (the nearest footprint carries it)
            dd, ii = cKDTree(cxy).query(st[["x", "y"]].values[m], k=1, distance_upper_bound=300.0)
            fb = np.where(np.isfinite(dd), fbuy[np.minimum(ii, len(cand) - 1)], np.nan)
            ok = (fb >= 1810) & (fb < np.floor(date[m]) - 1)
            old[m[ok]], old_src[m[ok]] = fb[ok] + 10.0 * np.array([_h(f"fb{k}") for k in m[ok]]), "hisdac"
    for f in np.unique(fire[np.isnan(old)]):
        m = np.isnan(old) & (fire == f)
        known = pd.to_numeric(st.year_built[fire == f], errors="coerce").dropna()
        old[m] = float(known.median()) if len(known) >= 10 else date[m] - 30.0
        old_src[m] = "fire_median" if len(known) >= 10 else "default"
    old = np.minimum(old, np.floor(date) - 1.0)
    # --- the rebuild lag, measured per fire on the recorded rebuilds (roll year, mid-year)
    lag_all = np.sort((cy[j] + 0.5 - date)[status == "rebuilt"]) if has.any() else np.array([])
    lags = {}
    for f in np.unique(fire):
        l = np.sort((cy[j] + 0.5 - date)[(status == "rebuilt") & (fire == f)]) if has.any() else np.array([])
        lags[f] = l if len(l) >= 30 else (lag_all if len(lag_all) >= 30 else np.array([2.5]))
    # --- today's footprints
    n_set = {"rebuilt_permit": 0, "rebuilt_est": 0, "gone": 0}
    for i in np.nonzero(np.isin(status, ("rebuilt_permit", "rebuilt_est", "gone")))[0]:
        fi = cand[fp[i]]
        if status[i] == "rebuilt_permit":
            year[fi] = py[i]
            conf[fi] = "exact" if pk[i] == "completed" else "estimated"
        elif status[i] == "rebuilt_est":
            l = lags[fire[i]]
            year[fi] = max(date[i] + float(l[min(int(_h(f"lag{st.id.values[i]}") * len(l)), len(l) - 1)]), np.floor(date[i]) + 1.0)
            conf[fi] = "estimated"
        else:
            end[fi] = date[i]
            if not year[fi] < np.floor(date[i]):     # undated, imputed from the rebuilt houses around
                year[fi] = old[i]
                conf[fi] = "estimated"
        reb[i] = year[fi] if status[i] != "gone" else np.nan
        n_set[status[i]] += 1
    m = status == "rebuilt"
    if m.any():
        reb[m] = cy[j][m]
    tab = pd.DataFrame({"sid": st.id.values, "fire_id": fire, "date": date, "status": status,
                        "fid": np.where(has, ids[j] if len(ids) else "", ""), "old_year": old, "old_src": old_src,
                        "rebuild_year": reb, "permit_year": py, "structure_type": st.structure_type.values, "main": main,
                        "county": st.county.values, "x": st.x.values, "y": st.y.values})
    STATE["structures"], STATE["calibration"] = tab, cal
    STATE["lag"] = {f: [round(float(q), 2) for q in np.quantile(l, [0.1, 0.25, 0.5, 0.75, 0.9])] + [int(((status == "rebuilt") & (fire == f)).sum())]
                    for f, l in lags.items() if ((status == "rebuilt") & (fire == f)).sum() >= 30}
    try:
        tab.to_parquet(INTERIM / "fire_structures.parquet")
    except Exception as e:  # noqa: BLE001
        log(f"fires: fire_structures.parquet not written ({e})")
    log(f"fires: {n} destroyed structures: {pd.Series(status).value_counts().to_dict()}; footprints changed: {n_set}; "
        f"rebuild lag (median years) {({f: v[2] for f, v in STATE['lag'].items()})}")
    return year, conf, end


def _rect(cx, cy, w, dpt, ang):
    import shapely
    c, s = math.cos(ang), math.sin(ang)
    pts = [(cx + c * dx - s * dy, cy + s * dx + c * dy) for dx, dy in ((-w / 2, -dpt / 2), (w / 2, -dpt / 2), (w / 2, dpt / 2), (-w / 2, dpt / 2))]
    return shapely.Polygon(pts)


def _long_axis(poly) -> float:
    c = np.asarray(poly.minimum_rotated_rectangle.exterior.coords)[:4]
    e1, e2 = c[1] - c[0], c[2] - c[1]
    e = e1 if np.hypot(*e1) >= np.hypot(*e2) else e2
    return math.atan2(e[1], e[0])


def _row(geom, key, fire_id, date, old, n, sh, use, source="fire_dins"):
    return {"geometry": geom, "start_year": float(min(old + 0.9 * _h("s" + key), date - 0.5)), "end_year": float(date),
            "height": n * sh + 0.6, "stories": float(n), "kind": "building", "source": source,
            "mapblklot": f"fire:{key}", "use_sanborn": use, "year_confidence": "procedural",
            "year_reason": f"fire:{fire_id}"}


def dins_predecessors(tu, lots=None):
    """What stood until the fire, per destroyed DINS structure (rows for region_predecessors)."""
    import shapely
    t = STATE.get("structures")
    if t is None:
        # rebuild_years did not run in this process: the table of the last region_buildings run,
        # unless the structures changed since
        p, c = INTERIM / "fire_structures.parquet", OUT / "destroyed_structures.csv"
        if not p.exists() or not c.exists() or p.stat().st_mtime < c.stat().st_mtime:
            log("fires: no current structure table (rebuild_years has not run) — no DINS predecessors")
            return []
        t = pd.read_parquet(p)
    if not len(t):
        return []
    geom = np.asarray(tu.geometry.values)
    ts = tu.start_year.values.astype(float)
    te = tu.end_year.values.astype(float)
    sto = pd.to_numeric(tu.get("stories", pd.Series(1.0, index=tu.index)), errors="coerce").fillna(1).values
    area = shapely.area(geom)
    reb = t[t.status.isin(REBUILT)]
    hit = np.nonzero(tu.fid_key.isin(set(reb.fid)).values)[0]
    df = pd.DataFrame({"k": tu.fid_key.iloc[hit].astype(str).values, "a": area[hit], "i": hit})
    big = df.sort_values("a").groupby("k").i.last().to_dict()
    rows, n_same = [], 0
    for r in reb.itertuples():
        i = big.get(r.fid)
        if i is None or not ts[i] > r.date:
            continue          # the footprint does not start after the fire (researched / changed downstream)
        spec = PLAIN.get(r.structure_type) if r.main else None
        if spec:
            ns, sh, use = spec[2], spec[3], spec[4]
        else:
            ns, sh, use = int(np.clip(sto[i], 1, 3)), 3.2, ("dwelling" if area[i] > 60 else "shed")
        rows.append(_row(geom[i], r.sid, r.fire_id, r.date, r.old_year, ns, sh, use))
        n_same += 1
    # no footprint today: a plain outline of the DINS structure type
    none = t[t.status == "none"].sort_values("main", ascending=False)
    sidx = tu.sindex
    lot_of = {}
    if lots is not None and len(lots) and len(none):
        ia, ib = lots.sindex.query(shapely.points(none.x.values, none.y.values), predicate="within")
        lot_of = dict(zip(none.sid.values[ia], ib))
    placed, cells, n_plain, n_skip, n_not, n_back = [], {}, 0, 0, 0, 0
    for r in none.itertuples():
        spec = PLAIN.get(r.structure_type, PLAIN["Utility Misc Structure"])
        if spec is None:
            n_not += 1
            continue
        w, dpt, ns, sh, use = spec
        cx, cy, ang, clip = r.x, r.y, None, None
        li = lot_of.get(r.sid)
        if li is not None and r.main:
            lot = lots.geometry.values[li]
            if lot.area <= 2500:           # a house lot: the house sits across it, in the middle
                c = lot.representative_point() if not lot.centroid.within(lot) else lot.centroid
                cx, cy, ang, clip = c.x, c.y, _long_axis(lot) + math.pi / 2, lot.buffer(-1.5)
        if ang is None:
            nb = sidx.nearest(shapely.Point(cx, cy), max_distance=150.0, return_all=False)
            ang = _long_axis(geom[nb[1][0]]) if nb.shape[1] else 0.0
        rect = _rect(cx, cy, w, dpt, ang)
        if clip is not None and not clip.is_empty:
            cl = rect.intersection(clip)
            if cl.geom_type == "Polygon" and cl.area >= 0.5 * rect.area:
                rect = cl
        # never on a building that stood through the fire, nor on another burned building
        hit = sidx.query(rect, predicate="intersects")
        bad = any((ts[h] <= r.date <= te[h]) and rect.intersection(geom[h]).area > 0.3 * rect.area for h in hit)
        key = (int(cx // 60), int(cy // 60))
        if not bad:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for k in cells.get((key[0] + dx, key[1] + dy), ()):
                        if rect.intersects(placed[k]) and rect.intersection(placed[k]).area > 0.3 * min(rect.area, placed[k].area):
                            bad = True
        if bad:
            n_skip += 1
            continue
        cells.setdefault(key, []).append(len(placed))
        placed.append(rect)
        rows.append(_row(rect, r.sid, r.fire_id, r.date, r.old_year, ns, sh, use))
        n_plain += 1
        py = getattr(r, "permit_year", np.nan)
        if r.main and np.isfinite(py):
            # a completed rebuild permit, but no outline in today's data: the house returns on the
            # same plain outline (the date is the permit's, the outline is not surveyed)
            nr = _row(rect, f"{r.sid}:rebuild", r.fire_id, 9999.0, py, ns, sh, use)
            nr["start_year"], nr["year_reason"] = float(py), f"fire_rebuild:{r.fire_id}"
            rows.append(nr)
            n_back += 1
    log(f"fires: predecessors: {n_same} on the rebuild's outline, {n_plain} plain outlines "
        f"({n_skip} skipped: on a standing or another burned building; {n_not} vehicles / infrastructure), "
        f"{n_back} permitted rebuilds without an outline today return on the plain outline")
    return rows


def clearance_predecessors(tu, pred, taken=()):
    """Older fires without structure data (data/manual/fires/clearances.csv, the columns of
    redevelopment_areas.csv): inside the outline, a building dated in the REBUILD_SPAN years
    after the fire replaced one that burned — a predecessor on its outline from the
    neighbourhood's development year (median of the recorded pre-fire years around) until the
    fire. Existing generated predecessors standing through the fire end at the fire instead."""
    import shapely
    from scipy.spatial import cKDTree
    p = OUT / "clearances.csv"
    if not p.exists():
        return [], pred
    from geocode import ring_polygon
    t = pd.read_csv(p)
    geom = np.asarray(tu.geometry.values)
    ts = tu.start_year.values.astype(float)
    te = tu.end_year.values.astype(float)
    conf = tu.year_confidence.values if "year_confidence" in tu else None
    sidx = tu.sindex
    has_pred = pred is not None and len(pred) and "start_year" in pred
    if has_pred:
        pred = pred.reset_index(drop=True)
        ps, pe = pred.start_year.values.astype(float).copy(), pred.end_year.values.astype(float).copy()
        pgeom = np.asarray(pred.geometry.values)
        ptree = shapely.STRtree(pgeom)
    tk = shapely.STRtree([r["geometry"] for r in taken]) if len(taken) else None
    rows = []
    for r in t.itertuples():
        try:
            poly = ring_polygon(r.ring, r.ring_type, crs=UTM)
        except Exception as e:  # noqa: BLE001
            log(f"fires: clearance {r.area_id}: {e}")
            continue
        date = float(r.clear_start)
        near = sidx.query(poly.buffer(450.0), predicate="intersects")      # the outline and its surroundings
        rp = shapely.point_on_surface(geom[near])
        xy = dict(zip(near, np.column_stack([shapely.get_x(rp), shapely.get_y(rp)])))
        area = dict(zip(near, shapely.area(geom[near])))
        exact = np.ones(len(near), bool) if conf is None else (pd.Series(conf[near]).astype(str).values == "exact")
        ins = near[shapely.contains(poly, rp)]
        reb = ins[(ts[ins] > date) & (ts[ins] <= date + REBUILD_SPAN) & (te[ins] > 9000)]
        pool = near[exact & (ts[near] < np.floor(date) - 0.5) & (te[near] > date)]
        if not len(reb) or len(pool) < 3:
            log(f"fires: clearance {r.area_id}: {len(reb)} rebuilds, {len(pool)} dated survivors — nothing generated")
            continue
        dd, ii = cKDTree(np.array([xy[k] for k in pool])).query(np.array([xy[k] for k in reb]), k=min(12, len(pool)),
                                                                 distance_upper_bound=400.0)
        vals = np.where(np.isfinite(dd), ts[pool][np.minimum(ii, len(pool) - 1)], np.nan)
        cnt = np.isfinite(vals).sum(axis=1)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            med = np.nanmedian(vals, axis=1)
        n_new = n_cut = n_no = 0
        for k, i in enumerate(reb):
            g_ = geom[i]
            if has_pred:      # an era-typical predecessor is already on the lot: it burns
                hit = [h for h in ptree.query(g_, predicate="intersects")
                       if ps[h] < date < pe[h] + 1e-9 and g_.intersection(pgeom[h]).area > 0.3 * min(area[i], pgeom[h].area)]
                if hit:
                    pe[hit] = date
                    n_cut += 1
                    continue
            if tk is not None and len(tk.query(g_, predicate="intersects")):
                continue
            if cnt[k] < 3:
                n_no += 1
                continue
            key = f"{r.area_id}:{int(xy[i][0])}_{int(xy[i][1])}"
            ns = 2 if area[i] < 350 else 3
            rows.append(_row(g_, key, r.area_id, date, float(med[k]) + 6.0 * (_h("o" + key) - 0.5), ns, 3.2,
                             "dwelling" if area[i] < 350 else "flats", source="fire_procedural"))
            n_new += 1
        log(f"fires: clearance {r.area_id} ({date:.2f}): {len(reb)} rebuilds inside -> {n_new} predecessors on their outlines, "
            f"{n_cut} existing predecessors end in the fire, {n_no} without dated neighbours")
    if has_pred:
        pred = pred.assign(end_year=pe)
    return rows, pred


def add_predecessors(tu, pred, lots=None):
    """region_predecessors hook. tu: today's buildings (UTM; start_year, end_year, stories,
    year_confidence, fid_key); pred: the vanished buildings so far. Returns pred + the
    buildings the fires destroyed; generated predecessors on the same spot make way."""
    if not OUT.exists():
        return pred
    import geopandas as gpd
    import shapely
    rows = dins_predecessors(tu, lots)
    more, pred = clearance_predecessors(tu, pred, rows)
    rows += more
    if not rows:
        return pred
    new = gpd.GeoDataFrame(rows, geometry="geometry", crs=UTM)
    if pred is not None and len(pred) and "source" in pred:
        pred = pred.reset_index(drop=True)
        gen = pred.source.astype(str).str.endswith("procedural").values
        ps, pe = pred.start_year.values.astype(float).copy(), pred.end_year.values.astype(float).copy()
        ng = np.asarray(new.geometry.values)
        na = shapely.area(ng)
        ia, ib = pred.sindex.query(ng, predicate="intersects")
        drop = np.zeros(len(pred), bool)
        for a, b in zip(ia, ib):
            if not gen[b] or drop[b] or new.source.values[a] != "fire_dins":
                continue
            pg = pred.geometry.values[b]
            if ng[a].intersection(pg).area <= 0.3 * min(na[a], pg.area):
                continue
            s0, e0 = new.start_year.values[a], new.end_year.values[a]
            if pe[b] <= s0 or ps[b] >= e0:
                continue
            if ps[b] < s0 - 3:
                pe[b] = s0 - 0.1          # the older house the burned one had replaced
            else:
                drop[b] = True
        pred = pred.assign(start_year=ps, end_year=pe)[~drop]
        log(f"fires: {int(drop.sum())} generated predecessors replaced by burned buildings")
    return gpd.GeoDataFrame(pd.concat([pred, new], ignore_index=True), geometry="geometry", crs=UTM)


# ----------------------------------------------------------------------------- tests

TEST_BOXES = {
    "coffey": (-122.765, 38.468, -122.735, 38.492),       # Coffey Park, Santa Rosa (Tubbs, 9 Oct 2017)
    "fountaingrove": (-122.735, 38.468, -122.69, 38.50),  # Fountaingrove / Hidden Valley
    "boulder": (-122.215, 37.115, -122.105, 37.215),      # Boulder Creek, Big Basin Hwy, Riverside Grove (CZU, Aug 2020)
    "bonnydoon": (-122.20, 37.02, -122.10, 37.10),        # Bonny Doon (CZU)
    "oakland": (-122.265, 37.835, -122.195, 37.878),      # Oakland / Berkeley hills (Tunnel fire, 20 Oct 1991)
    "all": None,
}


def simple_years(g):
    """The recorded-year part of region_buildings.assign_years for a test: best source first,
    undated footprints from the median of their recorded neighbours within 200 m."""
    from scipy.spatial import cKDTree
    year = np.full(len(g), np.nan)
    for col in ("historic", "public", "third_party", "commercial"):
        if f"year_{col}" not in g:
            continue
        y = _num(g, f"year_{col}", np.arange(len(g)))
        sp = g[f"spike_{col}"].fillna(False).astype(bool).values
        take = np.isnan(year) & (y >= 1769) & (y <= 2026) & ~sp
        year[take] = y[take]
    conf = np.where(np.isfinite(year), "exact", "estimated").astype(object)
    rp = g.geometry.to_crs(UTM).representative_point()
    xy = np.column_stack([rp.x.values, rp.y.values])
    have = np.isfinite(year)
    need = np.nonzero(~have)[0]
    if have.sum() >= 3 and len(need):
        d, idx = cKDTree(xy[have]).query(xy[need], k=min(12, int(have.sum())), distance_upper_bound=200)
        vals = np.where(np.isfinite(d), year[have][np.minimum(idx, have.sum() - 1)], np.nan)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            year[need] = np.nanmedian(vals, axis=1)
    f = _num(g, "fbuy", np.arange(len(g)))
    m = np.isnan(year) & (f >= 1810)
    year[m] = f[m] + 5
    year[np.isnan(year)] = 1975.0
    return year, conf, xy


def test(name, out_dir=None):
    """Run both hooks on a box without the stages; prints counts, writes GeoJSON for a look."""
    global ONLY_BOX
    import geopandas as gpd
    from sf_predecessors import resolve_overlaps
    ONLY_BOX = TEST_BOXES[name]
    st = structures()
    cp = OUT / "clearances.csv"
    if name == "oakland" and cp.exists():
        import pyproj
        b = ONLY_BOX
        gx, gy = np.meshgrid(np.linspace(b[0], b[2], 40), np.linspace(b[1], b[3], 40))
        x, y = pyproj.Transformer.from_crs(4326, UTM, always_xy=True).transform(gx.ravel(), gy.ravel())
        near = pd.DataFrame({"x": x, "y": y})
    else:
        near = st
    g = footprints_near(near, radius=300.0)
    g = g.to_crs(4326)
    year, conf, xy = simple_years(g)
    end = np.full(len(g), 9999.0)
    y0 = year.copy()
    year, conf, end = rebuild_years(g, xy, year, conf, end)
    tu = gpd.GeoDataFrame({"start_year": np.floor(year) + 0.45, "end_year": end, "stories": 1.0, "year_confidence": conf,
                           "fid_key": g["id"].astype(str).values}, geometry=g.geometry.to_crs(UTM).values, crs=UTM)
    pred = add_predecessors(tu, gpd.GeoDataFrame(geometry=[], crs=UTM))
    if pred is not None and len(pred):
        pred = resolve_overlaps(gpd.GeoDataFrame(pred, geometry="geometry", crs=UTM), tu)
    t = STATE.get("structures")
    print(f"== {name}: {len(st)} destroyed structures, {len(g)} footprints today within 300 m")
    if t is not None and len(t):
        print(t.groupby(["fire_id", "status"]).size().unstack(fill_value=0).assign(total=lambda d: d.sum(axis=1)).sort_values("total", ascending=False).head(14).to_string())
        print("main structures (houses, shops …):")
        print(t[t.main].groupby(["fire_id", "status"]).size().unstack(fill_value=0).assign(total=lambda d: d.sum(axis=1)).sort_values("total", ascending=False).head(14).to_string())
        print("pre-fire year from:", t.old_src.value_counts().to_dict())
        print("rebuild lag quantiles 10/25/50/75/90 % (years after the fire), n:", STATE.get("lag"))
        print("outline calibration (n matched, share recorded as rebuilt):", {k: v for k, v in STATE.get("calibration", {}).items() if v[0] >= 20})
    print("today's footprints: year moved after a fire", int((np.floor(year) != np.floor(y0)).sum()), "| ended by a fire", int((end < 9000).sum()))
    if pred is not None and len(pred):
        print("predecessors:", len(pred), pred.source.value_counts().to_dict(), "| end years", pred.end_year.round(2).value_counts().head(5).to_dict())
        ey = pred.end_year.values
        for d in sorted(set(np.round(ey, 3)))[-6:]:
            s = ((tu.start_year.values <= d - 0.05) & (tu.end_year.values > d - 0.05)).sum() + ((pred.start_year.values <= d - 0.05) & (pred.end_year.values > d - 0.05)).sum()
            a = ((tu.start_year.values <= d + 0.05) & (tu.end_year.values > d + 0.05)).sum() + ((pred.start_year.values <= d + 0.05) & (pred.end_year.values > d + 0.05)).sum()
            print(f"   {d:.3f}: buildings standing just before {s}, just after {a}, today {(tu.end_year.values > 9000).sum()}")
        bad = (pred.start_year.values >= pred.end_year.values).sum()
        print("   start >= end:", int(bad), "| ids unique:", pred.mapblklot.is_unique)
    if out_dir:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        tu.to_crs(4326).to_file(Path(out_dir) / f"{name}_today.geojson", driver="GeoJSON")
        if pred is not None and len(pred):
            pred.to_crs(4326).to_file(Path(out_dir) / f"{name}_pred.geojson", driver="GeoJSON")
    ONLY_BOX = None
    (INTERIM / "fire_structures.parquet").unlink(missing_ok=True)    # a test box must not pass for a stage run
    return tu, pred


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "download":
        download()
    elif cmd == "build":
        build()
    elif cmd == "test":
        test(sys.argv[2] if len(sys.argv) > 2 else "coffey", sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        print(__doc__)
