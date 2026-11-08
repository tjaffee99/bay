"""Stage: transit — BART and Muni rail: real track geometry, stations, and the service
lines the viewer runs its trains on.

Sources
  * Track geometry: Overture transportation `rail` segments (OpenStreetMap, ODbL) —
    each track is its own line, with is_bridge / is_tunnel flags and level_rules.
    Kept: subway / light_rail / tram / funicular / monorail / unknown classes within
    25 m of a BART or Muni service line (freight and Caltrain stay out).
  * Service lines: BART GTFS (bart.gov, shapes + stop order) and SFMTA route patterns
    (DataSF 9exe-acju) + stops (DataSF i28k-bkz6) for Muni Metro J K L M N T, the F
    Market & Wharves streetcar and the three cable car lines.
  * Dates: data/tables/transit_openings.csv (exact opening days per extension; the
    researched route lines in data/manual/routes.csv locate them) and
    data/tables/transit_stations.csv (every BART and Muni Metro subway station).
    Before 1980 the streetcar / cable car history stays in routes.csv (roads.py); from
    1980 (Muni Metro) the modern Muni lines come from here.

Outputs
  viewer/public/data/transit.bin.gz       tracks (BAYT, same columns as roads: kind,
                                          width, years, elevated: 0 ground, 2 aerial,
                                          4 tunnel)
  viewer/public/data/transit-lines.json   service lines: centreline (lon/lat offsets, z,
                                          cumulative m, opening year, tunnel flag), stop
                                          knots (distance, arrive s, depart s), vehicle
                                          and headway — trains are procedural
  viewer/public/data/transit-stations.json
"""
from __future__ import annotations

import datetime as dt
import json
import math
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Point
from shapely.ops import linemerge

from common import MANUAL, RAW, TABLES, VIEWER_DATA, download_file, log
from download_overture import RELEASE
from roads import K_BART, K_CABLE, K_LIGHTRAIL, K_STREETCAR, ORIGIN, UTM, Ground, _flag_ranges, write_paths3d

BART_GTFS = "https://www.bart.gov/dev/schedules/google_transit.zip"
MUNI_PATTERNS = "https://data.sfgov.org/resource/9exe-acju.geojson?$limit=50000"
MUNI_STOPS = "https://data.sfgov.org/resource/i28k-bkz6.geojson?$limit=50000"

# Vehicles: car [length, width, height] m, cars per train, gap between cars, cruise speed
# (m/s), acceleration (m/s^2), dwell at stops (s). Real dimensions; the running is
# procedural (constant headway, trapezoid speed profile between stops).
VEHICLES = {
    # BART A/B/C (1972-2024) and D/E "Fleet of the Future" (2018-) cars: 70-75 ft x 10.5 ft
    "bart": {"car": [21.3, 3.2, 3.3], "gap": 0.9, "vmax": 29.0, "acc": 1.2, "dwell": 35},
    # eBART Stadler FLIRT DMU: two cars with a power module between (approximate lengths)
    "ebart": {"car": [24.0, 3.0, 4.0], "gap": 0.6, "vmax": 31.0, "acc": 1.0, "dwell": 45},
    # Oakland Airport Connector: Doppelmayr Cable Liner, 3-car trains
    "cable_liner": {"car": [11.0, 2.9, 3.4], "gap": 0.6, "vmax": 14.0, "acc": 0.8, "dwell": 60},
    # Muni LRVs: Boeing (1980-2002, 71 ft), Breda (1996-2025) and Siemens S200 (2017-), 75 ft x 9 ft
    "lrv": {"car": [22.9, 2.7, 3.5], "gap": 0.8, "vmax": 14.0, "acc": 1.2, "dwell": 25},
    # F line: PCC cars (50 ft) and Milan Peter Witts
    "pcc": {"car": [15.2, 2.7, 3.2], "gap": 0.0, "vmax": 11.0, "acc": 1.1, "dwell": 20},
    # cable cars: Powell 27.5 ft, California 30 ft double-ended; the cable runs at 9.5 mph
    "cable_car": {"car": [8.4, 2.4, 3.2], "gap": 0.0, "vmax": 4.2, "acc": 0.9, "dwell": 18},
}

# BART lines (GTFS route -> the shape most trips use, one direction); colours = GTFS.
BART_LINES = [
    # id, name, route_id, cars, headway min
    ("yellow", "Yellow (Antioch - SFO/Millbrae)", "1", 10, 15),
    ("orange", "Orange (Richmond - Berryessa)", "4", 8, 15),
    ("green", "Green (Berryessa - Daly City)", "5", 8, 15),
    ("red", "Red (Richmond - SFO/Millbrae)", "7", 8, 15),
    ("blue", "Blue (Dublin/Pleasanton - Daly City)", "11", 8, 15),
    ("grey", "Oakland Airport Connector", "20", 3, 5),
]
# Muni (DataSF pattern route_name): vehicle, cars, headway min, base opening year in this layer
MUNI_LINES = [
    ("J", "J Church", "lrv", 1, 12, 1980.0),
    ("K", "K Ingleside", "lrv", 1, 12, 1980.0),
    ("L", "L Taraval", "lrv", 2, 10, 1980.0),
    ("M", "M Ocean View", "lrv", 2, 12, 1980.0),
    ("N", "N Judah", "lrv", 2, 8, 1980.0),
    ("T", "T Third Street", "lrv", 2, 10, 2007.27),
    ("F", "F Market & Wharves", "pcc", 1, 8, 1995.67),
    ("PM", "Powell-Mason cable car", "cable_car", 1, 8, 1980.0),
    ("PH", "Powell-Hyde cable car", "cable_car", 1, 8, 1980.0),
    ("C", "California St cable car", "cable_car", 1, 10, 1980.0),
]
MUNI_COLOR = {"J": "D3A13C", "K": "5E9FC4", "L": "92278F", "M": "2E8B57", "N": "1F4E9C", "T": "D2232A",
              "F": "F1A340", "PM": "8B3A2F", "PH": "8B3A2F", "C": "8B3A2F"}
# the whole cable car system closed for the 1982-84 rebuild
CABLE_GAP = [1982.72, 1984.47]

TRACK_KIND = {"bart": K_BART, "ebart": K_BART, "cable_liner": K_BART, "lrv": K_LIGHTRAIL, "pcc": K_STREETCAR,
              "cable_car": K_CABLE}
TRACK_WIDTH = {"bart": 3.0, "ebart": 3.0, "cable_liner": 2.8, "lrv": 2.6, "pcc": 2.6, "cable_car": 2.2}
GROUND_H = 0.45


def decyear(s: str) -> float:
    d = dt.date.fromisoformat(str(s).strip())
    return round(d.year + (d.timetuple().tm_yday - 1) / 365.25, 3)


# ---------------------------------------------------------------- downloads
def downloads():
    bart = RAW / "gtfs" / "bart"
    if not (bart / "shapes.txt").exists():
        bart.mkdir(parents=True, exist_ok=True)
        z = download_file(BART_GTFS, bart / "bart.zip")
        zipfile.ZipFile(z).extractall(bart)
    muni = RAW / "gtfs" / "muni"
    muni.mkdir(parents=True, exist_ok=True)
    for url, name in ((MUNI_PATTERNS, "patterns.geojson"), (MUNI_STOPS, "stops.geojson")):
        if not (muni / name).exists():
            download_file(url, muni / name)
    return bart, muni


# ---------------------------------------------------------------- lines
def to_utm(lon, lat):
    s = gpd.GeoSeries(gpd.points_from_xy(lon, lat), crs=4326).to_crs(UTM)
    return np.column_stack([s.x.values, s.y.values])


def to_ll(xy):
    s = gpd.GeoSeries(gpd.points_from_xy(xy[:, 0], xy[:, 1]), crs=UTM).to_crs(4326)
    return s.x.values, s.y.values


def densify_xy(xy, step=20.0):
    out = [xy[0]]
    for a, b in zip(xy[:-1], xy[1:]):
        d = float(np.hypot(*(b - a)))
        if d < 0.5:
            continue
        n = int(math.ceil(d / step))
        for k in range(1, n + 1):
            out.append(a + (b - a) * (k / n))
    return np.array(out)


def bart_lines(bart):
    shapes = pd.read_csv(bart / "shapes.txt")
    trips = pd.read_csv(bart / "trips.txt")
    st = pd.read_csv(bart / "stop_times.txt")
    stops = pd.read_csv(bart / "stops.txt")
    routes = pd.read_csv(bart / "routes.txt", dtype=str)
    parent = dict(zip(stops.stop_id, stops.parent_station.fillna("")))
    out = []
    for lid, name, rid, cars, headway in BART_LINES:
        t = trips[trips.route_id.astype(str) == rid]
        shape_id = t.shape_id.value_counts().index[0]
        trip = t[t.shape_id == shape_id].trip_id.iloc[0]
        seq = st[st.trip_id == trip].sort_values("stop_sequence").stop_id.map(lambda s: parent.get(s) or s).tolist()
        sh = shapes[shapes.shape_id == shape_id].sort_values("shape_pt_sequence")
        xy = to_utm(sh.shape_pt_lon.values, sh.shape_pt_lat.values)
        color = routes[routes.route_id == rid].route_color.iloc[0]
        veh = "cable_liner" if lid == "grey" else "bart"
        out.append({"id": lid, "name": name, "system": "bart", "veh": veh, "cars": cars, "headway": headway * 60,
                    "color": color, "xy": xy, "stops": seq})
    # eBART (Pittsburg/Bay Point - Antioch) is a separate DMU shuttle on the Yellow line's east end
    y = out[0]
    if y["stops"][0] == "ANTC" and "PITT" in y["stops"]:
        k = y["stops"].index("PITT")
        st_xy = station_xy(bart)
        cut = int(np.argmin(np.hypot(*(y["xy"] - st_xy["PITT"]).T)))
        out.append({"id": "ebart", "name": "eBART (Pittsburg/Bay Point - Antioch)", "system": "bart", "veh": "ebart",
                    "cars": 2, "headway": 30 * 60, "color": y["color"], "xy": y["xy"][: cut + 1], "stops": y["stops"][: k + 1]})
        y["xy"] = y["xy"][cut:]
        y["stops"] = y["stops"][k:]
    return out


def station_xy(bart):
    stops = pd.read_csv(bart / "stops.txt")
    s = stops[stops.location_type == 1]
    xy = to_utm(s.stop_lon.values, s.stop_lat.values)
    return dict(zip(s.stop_id, xy))


def muni_lines(muni):
    pat = gpd.read_file(muni / "patterns.geojson")
    pat["route_name"] = pat.route_name.str.strip()
    pat = pat.to_crs(UTM)
    out = []
    for rn, name, veh, cars, headway, y0 in MUNI_LINES:
        p = pat[(pat.route_name == rn) & (pat.direction == "O") & (pat.pattern_type == "F")]
        if not len(p):
            p = pat[(pat.route_name == rn) & (pat.direction == "O")]
        if not len(p):
            log(f"transit: no pattern for {rn}")
            continue
        g = p.geometry.iloc[int(np.argmax(p.geometry.length.values))]
        m = linemerge(g) if g.geom_type == "MultiLineString" else g
        if m.geom_type == "MultiLineString":  # join the parts in order
            pts = [c for part in m.geoms for c in part.coords]
        else:
            pts = list(m.coords)
        xy = np.array(pts)[:, :2]
        out.append({"id": rn, "name": name, "system": "muni", "veh": veh, "cars": cars, "headway": headway * 60,
                    "color": MUNI_COLOR[rn], "xy": xy, "base": y0})
    return out


# ---------------------------------------------------------------- tracks (Overture)
def compatible(veh, cls, tunnel):
    """Can a vehicle run on an Overture rail class (BART is OSM railway=subway)?"""
    if veh == "bart":
        return cls in ("subway", "unknown")
    if veh == "cable_liner":
        return cls in ("monorail", "funicular", "unknown", "subway", "light_rail")
    if veh == "ebart":
        return cls in ("standard_gauge", "light_rail", "unknown", "subway")
    if veh == "lrv":  # OSM: Muni Metro is railway=light_rail, the F/E and cable cars railway=tram
        return cls in ("light_rail", "unknown")
    # F line streetcars and cable cars run in the street, never in the Muni Metro subway
    return cls in ("tram", "light_rail", "funicular", "unknown") and not tunnel


def track_samples(lines, ground):
    """Overture rail near the service lines, sampled with a height profile."""
    r = gpd.read_parquet(RAW / "overture" / RELEASE / "rail.parquet")
    if r.crs is None or str(r.crs) != "EPSG:4326":
        r = r.set_crs(4326, allow_override=True)
    r = r[r.geometry.geom_type == "LineString"]
    r = r[r["class"].isin(["subway", "light_rail", "tram", "funicular", "monorail", "unknown", "standard_gauge"])]

    def has_flag(f, key):
        return f is not None and any(key in list(e.get("values", [])) for e in f)

    bad = r.rail_flags.map(lambda f: has_flag(f, "is_abandoned") or has_flag(f, "is_disused") or has_flag(f, "is_under_construction"))
    r = r[~bad.values].reset_index(drop=True)
    ru = r.to_crs(UTM)
    # which service line each segment belongs to (all its samples within 25 m of the line)
    pts, owner = [], []
    for i, ln in enumerate(lines):
        d = densify_xy(ln["xy"], 10.0)
        pts.append(d)
        owner.append(np.full(len(d), i))
    tree = cKDTree(np.concatenate(pts))
    owner = np.concatenate(owner)
    segs = []
    for i, row in r.iterrows():
        g = ru.geometry.iloc[i]
        L = g.length
        if L < 2:
            continue
        n = max(2, int(math.ceil(L / 15.0)) + 1)
        f = np.linspace(0, 1, n)
        xy = np.array([g.interpolate(x, normalized=True).coords[0][:2] for x in f])
        dd, ii = tree.query(xy, distance_upper_bound=25.0)
        near = np.isfinite(dd)
        if near.mean() < 0.6:
            continue
        cls = row["class"]
        tunnel_any = has_flag(row.rail_flags, "is_tunnel")
        cnt = np.bincount(owner[ii[near]], minlength=len(lines))
        compat = [li for li in np.nonzero(cnt)[0] if compatible(lines[li]["veh"], cls, tunnel_any)]
        if not compat:
            continue
        li = max(compat, key=lambda k: cnt[k])
        ln = lines[li]
        lev = np.zeros(n)
        for lo, hi, v in _flag_ranges(row.level_rules):
            lev[(f >= lo) & (f <= hi)] = v
        br = np.zeros(n, bool)
        for lo, hi, _ in _flag_ranges(row.rail_flags, "is_bridge"):
            br[(f >= lo) & (f <= hi)] = True
        tn = np.zeros(n, bool)
        for lo, hi, _ in _flag_ranges(row.rail_flags, "is_tunnel"):
            tn[(f >= lo) & (f <= hi)] = True
        tn |= lev <= -1
        h = np.where(br | (lev >= 1), 8.5 + 4.5 * np.maximum(lev - 1, 0), GROUND_H)
        if ln["system"] == "muni":  # Muni bridges (Islais Creek, over I-280) carry the street level
            h[:] = GROUND_H
        s_ = f * L
        slope = 0.04 if ln["system"] == "bart" else 0.06
        for k in range(1, n):
            h[k] = max(h[k], h[k - 1] - slope * (s_[k] - s_[k - 1]))
        for k in range(n - 2, -1, -1):
            h[k] = max(h[k], h[k + 1] - slope * (s_[k + 1] - s_[k]))
        h[tn] = GROUND_H
        segs.append({"xy": xy, "h": h, "tn": tn, "line": li, "compat": compat, "veh": ln["veh"]})
    log(f"transit: {len(segs)} track segments (of {len(r)} rail segments in the region)")
    return segs


# ---------------------------------------------------------------- dating
def route_points(prefixes, step=40.0):
    """Researched route lines (lon/lat rows of routes.csv) -> (utm points, route ids)."""
    routes = pd.read_csv(MANUAL / "routes.csv")
    pts, ids = [], []
    for _, r in routes.iterrows():
        if not str(r.route_id).startswith(prefixes) or str(r.geom_type).strip() != "lonlat":
            continue
        ll = np.array([tuple(map(float, p.split()[:2])) for p in str(r.geom).split(";") if p.strip()])
        if len(ll) < 2:
            continue
        d = densify_xy(to_utm(ll[:, 0], ll[:, 1]), step)
        pts.append(d)
        ids += [str(r.route_id)] * len(d)
    return np.concatenate(pts), np.array(ids)


def vertex_years(ln, xy, openings, bart_pts, muni_pts):
    if ln["system"] == "bart":
        if ln["veh"] == "ebart":
            return np.full(len(xy), openings["bart_ebart"])
        if ln["veh"] == "cable_liner":
            return np.full(len(xy), openings["bart_oak_connector"])
        P, ids = bart_pts
        d, i = cKDTree(P).query(xy)
        return np.array([openings.get(ids[k], 1972.69) if dd < 250 else 1972.69 for dd, k in zip(d, i)])
    y = np.full(len(xy), ln["base"])
    P, ids = muni_pts
    d, i = cKDTree(P).query(xy)
    rid = ids[i]
    near = d < 30
    lid = ln["id"]
    if lid in ("N", "T", "K", "J", "L", "M"):
        mmx = near & (rid == "muni_metro_extension")
        y[mmx] = np.maximum(y[mmx], 1998.64 if lid == "N" else openings["muni_metro_extension"])
    if lid == "T":
        cs = near & (rid == "muni_central_subway")
        y[cs] = openings["muni_central_subway"]
    if lid == "J":
        ext = near & (rid == "sc_j_church")
        y[ext] = openings["sc_j_church"]
    if lid == "F":
        lon, lat = to_ll(xy)
        y[lat > 37.7950] = 2000.17  # F extended along The Embarcadero to Fisherman's Wharf 2000-03-04
    return y


# ---------------------------------------------------------------- schedule
def run_time(D, vmax, acc):
    d_acc = vmax * vmax / (2 * acc)
    if D < 2 * d_acc:
        return 2 * math.sqrt(D / acc)
    return 2 * vmax / acc + (D - 2 * d_acc) / vmax


def knots_for(stops_s, total, veh):
    v = VEHICLES[veh]
    s = sorted(set([0.0] + [float(x) for x in stops_s] + [total]))
    # merge stops closer than a train length
    merged = [s[0]]
    for x in s[1:]:
        if x - merged[-1] > 60 or x == total:
            merged.append(x)
    t = 0.0
    out = []
    for k, x in enumerate(merged):
        if k:
            t += run_time(x - merged[k - 1], v["vmax"], v["acc"])
        dwell = 0.0 if k in (0, len(merged) - 1) else v["dwell"]
        out.append([round(x, 1), round(t, 1), round(t + dwell, 1)])
        t += dwell
    return out


# ---------------------------------------------------------------- main
def main():
    bart, muni = downloads()
    ground = Ground()
    ot = pd.read_csv(TABLES / "transit_openings.csv")
    openings = {r.route_id: decyear(r.opened) for r in ot.itertuples()}
    lines = bart_lines(bart) + muni_lines(muni)
    segs = track_samples(lines, ground)

    # centre each service line between its tracks (GTFS shapes / patterns run on one
    # track or the street centreline)
    tr_xy = np.concatenate([s["xy"] for s in segs])
    tr_h = np.concatenate([s["h"] for s in segs])
    tr_tn = np.concatenate([s["tn"] for s in segs])
    tr_line = np.concatenate([np.full(len(s["xy"]), s["line"]) for s in segs])
    tr_seg = np.concatenate([np.full(len(s["xy"]), q) for q, s in enumerate(segs)])
    tree = cKDTree(tr_xy)
    bart_pts = route_points(("bart_",))
    muni_pts = route_points(("muni_", "sc_j_church"))
    st_xy = station_xy(bart)
    stations_tab = pd.read_csv(TABLES / "transit_stations.csv")
    mstops = gpd.read_file(muni / "stops.geojson").to_crs(UTM)
    mst_xy = np.column_stack([mstops.geometry.x.values, mstops.geometry.y.values])

    out_lines = []
    for li, ln in enumerate(lines):
        xy = densify_xy(ln["xy"], 20.0)
        # tangent / normal
        tang = np.gradient(xy, axis=0)
        tang /= np.maximum(np.linalg.norm(tang, axis=1, keepdims=True), 1e-6)
        nrm = np.column_stack([-tang[:, 1], tang[:, 0]])
        nb = tree.query_ball_point(xy, 7.0)
        shift = np.zeros(len(xy))
        half = np.full(len(xy), np.nan)
        for k, idx in enumerate(nb):
            idx = [j for j in idx if li in segs[tr_seg[j]]["compat"]]
            if not idx:
                continue
            off = (tr_xy[idx] - xy[k]) @ nrm[k]
            pos, neg = off[off > 0.6], off[off < -0.6]
            if len(pos) and len(neg):
                shift[k] = (pos.max() + neg.min()) / 2
                half[k] = (pos.max() - neg.min()) / 2
        shift = pd.Series(shift).rolling(5, center=True, min_periods=1).median().values
        xy = xy + nrm * shift[:, None]
        # half the distance between the two tracks (trains follow it: tracks spread
        # around island platforms); default where only one track was found
        default_half = {"bart": 2.15, "ebart": 2.3, "cable_liner": 2.2}.get(ln["veh"], 1.75)
        half = pd.Series(half).rolling(7, center=True, min_periods=1).median().fillna(default_half).values
        half = np.clip(half, 1.4, 9.0)
        # height / tunnel from the nearest track this line can run on
        mine = np.array([li in segs[q]["compat"] for q in tr_seg])
        h = np.full(len(xy), GROUND_H)
        tn = np.zeros(len(xy), bool)
        if mine.any():
            d, i = cKDTree(tr_xy[mine]).query(xy, distance_upper_bound=30.0)
            ok = np.isfinite(d)
            h[ok] = tr_h[mine][i[ok]]
            tn[ok] = tr_tn[mine][i[ok]]
        lon, lat = to_ll(xy)
        # wheels on the drawn rails: ground tracks are lifted 0.9 m in the viewer (terrain bulge)
        z = ground(lon, lat) + np.where(tn, GROUND_H, np.where(h > 4, h, GROUND_H + 0.9))
        seg = np.hypot(*np.diff(xy, axis=0).T)
        cum = np.concatenate([[0.0], np.cumsum(seg)])
        years = vertex_years(ln, xy, openings, bart_pts, muni_pts)
        # stops: distance along the line
        line = LineString(xy)
        if ln["system"] == "bart":
            stop_s = [line.project(Point(st_xy[s])) for s in ln["stops"] if s in st_xy]
        else:
            # stops beside this direction's track; under ground only the subway stations
            dd, kk = cKDTree(xy).query(mst_xy, distance_upper_bound=8.0)
            ok = np.isfinite(dd)
            kk = np.minimum(kk, len(xy) - 1)
            ok &= ~tn[kk] | mstops.stopname.str.contains("Station").values
            stop_s = sorted(line.project(Point(p)) for p in mst_xy[ok])
        knots = knots_for(stop_s, float(cum[-1]), ln["veh"])
        out_lines.append({
            "id": ln["id"], "name": ln["name"], "system": ln["system"], "veh": ln["veh"], "cars": ln["cars"],
            "headway": ln["headway"], "color": ln["color"],
            "gap": CABLE_GAP if ln["veh"] == "cable_car" else None,
            "lon": np.round(lon - ORIGIN[0], 6).tolist(), "lat": np.round(lat - ORIGIN[1], 6).tolist(),
            "z": np.round(z, 1).tolist(), "cum": np.round(cum, 1).tolist(), "year": np.round(years, 2).tolist(),
            "tunnel": tn.astype(int).tolist(), "half": np.round(half, 1).tolist(), "knots": knots,
        })
        log(f"transit: line {ln['id']}: {cum[-1] / 1000:.1f} km, {len(knots)} stops, "
            f"{tn.mean() * 100:.0f}% tunnel, {(h > 4).mean() * 100:.0f}% aerial, opens {years.min():.2f}-{years.max():.2f}")
    meta = {"origin": list(ORIGIN), "vehicles": VEHICLES, "lines": out_lines}
    (VIEWER_DATA / "transit-lines.json").write_text(json.dumps(meta, separators=(",", ":")))

    # ---- tracks for drawing: years from the nearest line vertex of the same line
    lv_xy = {li: None for li in range(len(lines))}
    lv_y = {}
    for li, ol in enumerate(out_lines):
        lv_xy[li] = to_utm(np.array(ol["lon"]) + ORIGIN[0], np.array(ol["lat"]) + ORIGIN[1])
        lv_y[li] = np.array(ol["year"])
    trees = {li: cKDTree(v) for li, v in lv_xy.items()}
    items = []
    for sg in segs:
        li = sg["line"]
        # shared track (e.g. King St: N from 1998, T from 2007) opens with its first line
        y0 = 9999.0
        for lj in sg["compat"]:
            dd, ii = trees[lj].query(sg["xy"])
            if np.median(dd) < 30:
                y0 = min(y0, float(np.median(lv_y[lj][ii])))
        if y0 >= 9999:
            _, ii = trees[li].query(sg["xy"])
            y0 = float(np.median(lv_y[li][ii]))
        lon, lat = to_ll(sg["xy"])
        z = ground(lon, lat) + sg["h"]
        kind = TRACK_KIND[sg["veh"]]
        width = TRACK_WIDTH[sg["veh"]]
        # split into runs: tunnel (4) / aerial (2) / ground (0)
        cls = np.where(sg["tn"], 4, np.where(sg["h"] > 4, 2, 0))
        a = 0
        for k in range(1, len(cls) + 1):
            if k == len(cls) or cls[k] != cls[a]:
                b = min(k + 1, len(cls))
                if b - a >= 2:
                    items.append((lon[a:b], lat[a:b], z[a:b], kind, width, y0, 9999.0, int(cls[a])))
                a = k
    write_paths3d(VIEWER_DATA / "transit.bin.gz", items)

    # ---- stations
    stations = []
    all_xy = np.concatenate([lv_xy[li] for li in range(len(out_lines))])
    all_li = np.concatenate([np.full(len(lv_xy[li]), li) for li in range(len(out_lines))])
    all_k = np.concatenate([np.arange(len(lv_xy[li])) for li in range(len(out_lines))])
    lt = cKDTree(all_xy)
    mnames = mstops.stopname.str.replace(r"\s+(Inbound|Outbound|OB|IB)$", "", regex=True).str.strip()
    for r in stations_tab.itertuples():
        if r.system == "bart":
            if r.code not in st_xy:
                log(f"transit: station {r.code} not in GTFS")
                continue
            p = st_xy[r.code]
        else:
            key = {"EMB": "Embarcadero Station", "MON": "Montgomery Station", "POW": "Powell Station",
                   "CIV": "Civic Center Station", "VNS": "Van Ness Station", "CHU": "Church St Station",
                   "CAS": "Castro Station", "FHL": "Forest Hill Station", "WPT": "West Portal Station",
                   "YBM": "Yerba Buena/Moscone Station", "USQ": "Union Square/Market St Station",
                   "CHI": "Chinatown - Rose Pak Station"}[r.code]
            m = mnames.str.startswith(key).values
            if not m.any():
                log(f"transit: Muni station {key} not found")
                continue
            p = mst_xy[m].mean(axis=0)
        d, j = lt.query(p)
        li, k = int(all_li[j]), int(all_k[j])
        ol = out_lines[li]
        k0, k1 = max(0, k - 2), min(len(ol["lon"]) - 1, k + 2)
        a, b = lv_xy[li][k0], lv_xy[li][k1]
        heading = math.degrees(math.atan2(b[0] - a[0], b[1] - a[1]))  # bearing, degrees from north
        lon, lat = to_ll(np.array([lv_xy[li][k] if d < 40 else p]))
        tunnel = bool(ol["tunnel"][k]) if d < 40 else True
        gz = float(ground(lon, lat)[0])
        zt = float(ol["z"][k]) if d < 40 else gz
        kind = "underground" if tunnel else ("elevated" if zt - gz > 4 else "surface")
        if r.system == "muni":
            kind = "underground" if r.code not in ("WPT",) else "surface"
        stations.append({"code": r.code, "name": r.name, "system": r.system, "lon": round(float(lon[0]), 6),
                         "lat": round(float(lat[0]), 6), "z": round(zt, 1), "ground": round(gz, 1),
                         "heading": round(heading, 1), "kind": kind, "start": decyear(r.opened),
                         "end": decyear(r.closed) if isinstance(r.closed, str) and r.closed.strip() else 9999.0,
                         "line": ol["id"], "veh": ol["veh"]})
    (VIEWER_DATA / "transit-stations.json").write_text(json.dumps(stations, separators=(",", ":")))
    kinds = pd.Series([s["kind"] for s in stations]).value_counts().to_dict()
    log(f"transit: {len(stations)} stations {kinds}")


if __name__ == "__main__":
    main()
