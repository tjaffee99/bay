"""Stage: airports — runways, taxiways and aprons (Overture base/infrastructure, OSM) as
dated ground features, and airport outlines for the terrain (airfield grass instead of
city ground or orchard, from the opening year).

Dates: data/tables/airports.csv (researched opening / closing years per airport, source
per row; SFO / OAK / SJC piece by piece from data/manual/airports; researched pieces of
vanished airfields may carry their own start_year / end_year). Airports OSM maps only as a
point get an outline from their own pavement. Nothing is laid before its ground exists (bay
fill: SFO, OAK, NAS Alameda) — each feature waits for the terrain's land year (median over
the piece). Runways are mostly OSM
centrelines: buffered to the usual width (45 m at the international / military fields,
23 m elsewhere; taxiways 23 / 15 m, taxilanes 10 m).

Outputs: viewer/public/data/airports.bin.gz (BAYT: start_indices, positions f32[3] offsets
from ORIGIN with z = ground + 0.35, kind u8 (0 runway, 1 taxiway, 2 apron), years f32[2]),
data/interim/airports.parquet (airport outlines with opened / closed for terrain_tiles).
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from common import INTERIM, MANUAL, RAW, TABLES, VIEWER_DATA, log
from download_overture import RELEASE
from export_columnar import write_columnar
from extent import in_extent
from roads import ORIGIN, UTM, Ground

AIRPORT_CLASSES = ["airport", "international_airport", "military_airport", "municipal_airport", "private_airport"]
BIG = {"international_airport", "military_airport"}
KIND = {"runway": 0, "stopway": 0, "taxiway": 1, "taxilane": 1, "apron": 2}


def point_airport_outlines(g, reach=1500.0, margin=40.0):
    """Outlines for airports OSM maps only as a point (San Rafael Airport, Meadowlark Field):
    the convex hull of the runways / taxiways / aprons around the point that belong to it
    (nearer to it than to any other airport, within `reach` m), plus a margin. Points
    within 300 m of a polygon outline are duplicates of it and skipped; a point with no
    pavement around it gets no outline (nothing to draw)."""
    import shapely
    none = gpd.GeoDataFrame(columns=["name", "class", "geometry"], geometry="geometry", crs=4326)
    ports = g[g["class"].isin(AIRPORT_CLASSES)].to_crs(UTM)
    poly = ports[ports.geom_type.isin(["Polygon", "MultiPolygon"])]
    pts = ports[ports.geom_type == "Point"]
    if not poly.empty:
        pts = pts[pts.geometry.distance(shapely.union_all(poly.geometry.values)) > 300]
    feats = g[g["class"].isin(list(KIND))].to_crs(UTM)
    if pts.empty or feats.empty:
        return none
    # distance of every feature to every airport (polygon outlines first, then the points)
    anchors = list(poly.geometry.values) + list(pts.geometry.values)
    d = np.stack([feats.geometry.distance(a).values for a in anchors])
    nearest = d.argmin(0)
    out = []
    for i, (_, p) in enumerate(pts.iterrows(), start=len(poly)):
        mine = (nearest == i) & (d[i] <= reach)
        if not mine.any():
            continue
        parts = [geom.buffer(12) for geom in feats.geometry.values[mine]] + [p.geometry.buffer(30)]
        hull = shapely.union_all(parts).convex_hull.buffer(margin)
        out.append({"name": p["name"], "class": p["class"], "geometry": hull})
        log(f"airports: outline for point-only {p['name']} from {int(mine.sum())} runway / taxiway / apron features "
            f"({hull.area / 1e4:.1f} ha)")
    return gpd.GeoDataFrame(out, geometry="geometry", crs=UTM).to_crs(4326) if out else none


def land_year(lon, lat):
    """Year the ground at each point became dry land (terrain land-year grids), NaN if always land."""
    from terrain_grid import grid_def
    out = np.full(len(lon), np.nan)
    for name in ("detail", "region"):
        p = INTERIM / f"grid_{name}_landyear.npy"
        if not p.exists():
            continue
        g = grid_def(name)
        ly = np.load(p)
        X = np.radians(lon) * 6378137.0
        Y = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))
        c = np.rint((X - g["X0"]) / g["res"]).astype(int)
        r = np.rint((g["Y0"] - Y) / g["res"]).astype(int)
        ok = np.isnan(out) & (c >= 0) & (r >= 0) & (c < g["cols"]) & (r < g["rows"])
        out[ok] = ly[r[ok], c[ok]]
    return out


def dated_pavement(f):
    """SFO / OAK / SJC pavement dated feature by feature (data/manual/airports: USGS topo
    editions + airport histories; README there): a whole feature takes its own years, a
    runway is cut into its construction phases (metres along its axis), taxiways / aprons
    crossing a phase boundary are clipped by the dated zones; the removed runways (Mills
    Field's north-south strip 1927-62, OAK's Navy diagonal 1944-86) are added."""
    import shapely
    base = MANUAL / "airports"
    pp, zp, vp = base / "pavement_dates.csv", base / "pavement_zones.geojson", base / "vanished_pavement.geojson"
    if not pp.exists():
        return f
    pav = pd.read_csv(pp)
    zones = {}
    if zp.exists():
        z = gpd.read_file(zp).to_crs(UTM)
        zones = dict(zip(z["zone"].astype(str), z.geometry.values))
    to_utm = lambda lon, lat: gpd.GeoSeries(gpd.points_from_xy([lon], [lat]), crs=4326).to_crs(UTM).iloc[0]  # noqa: E731

    def band(r, half=250.0):
        a, b = to_utm(r.part_lon0, r.part_lat0), to_utm(r.part_lon1, r.part_lat1)
        d = np.array([b.x - a.x, b.y - a.y]); L = np.hypot(*d)
        if L < 1:
            return None
        u = d / L; n = np.array([-u[1], u[0]]) * half
        P0, P1 = np.array([a.x, a.y]), np.array([b.x, b.y])
        return shapely.Polygon([P0 + n, P1 + n, P1 - n, P0 - n])

    by_id = {k: g_ for k, g_ in pav.groupby("overture_id")}
    out = []
    n_dated = 0
    # (records, not itertuples: "class" is a keyword and would be renamed)
    for d in f.to_dict("records"):
        rows = by_id.get(d.get("id"))
        if rows is None:
            out.append(d)
            continue
        n_dated += 1
        geom = d["geometry"]
        used = []
        for q in rows.itertuples():
            if q.part == "whole":
                piece = geom
            elif q.part == "axis_interval":
                bd = band(q)
                piece = geom.intersection(bd) if bd is not None else None
            else:
                zg = zones.get(str(q.clip_zone))
                piece = geom.intersection(zg) if zg is not None else None
            if piece is None or piece.is_empty or piece.area < 20:
                continue
            for u_ in used:
                piece = piece.difference(u_)
            if piece.is_empty or piece.area < 20:
                continue
            used.append(piece)
            out.append(dict(d, geometry=piece, opened=float(q.start_year),
                            closed=float(q.end_year) if pd.notna(q.end_year) else 9999.0))
        rest = geom.difference(shapely.union_all(used)) if used else geom
        if not rest.is_empty and rest.area > 200:
            first = float(rows.start_year.min())
            out.append(dict(d, geometry=rest, opened=first))
    f2 = gpd.GeoDataFrame(out, geometry="geometry", crs=UTM)
    if vp.exists():
        v = gpd.read_file(vp).to_crs(UTM)
        vg = [gm.buffer(float(w) / 2, cap_style="flat") if gm.geom_type == "LineString" else gm
              for gm, w in zip(v.geometry, pd.to_numeric(v.get("width_m", 45), errors="coerce").fillna(45))]
        extra = gpd.GeoDataFrame({"class": v["kind"].astype(str).replace({"": "runway"}), "name": v["name"],
                                  "opened": pd.to_numeric(v.start_year, errors="coerce"),
                                  "closed": pd.to_numeric(v.end_year, errors="coerce").fillna(9999.0),
                                  "aclass": "aerodrome"}, geometry=vg, crs=UTM)
        f2 = gpd.GeoDataFrame(pd.concat([f2, extra], ignore_index=True), geometry="geometry", crs=UTM)
    log(f"airports: {n_dated} SFO / OAK / SJC pavement features dated by construction phase, "
        f"+ {len(f2) - len(f)} pieces / removed runways")
    return f2


def main():
    d = pd.read_parquet(RAW / "overture" / RELEASE / "region_airports.parquet")
    g = gpd.GeoDataFrame(d, geometry=gpd.GeoSeries.from_wkb(d.geometry), crs=4326)
    g = g[in_extent(g.geometry.representative_point())]
    # airports OSM has only as a point (no aerodrome outline): outline from their pavement
    po = point_airport_outlines(g)
    if len(po):
        g = gpd.GeoDataFrame(pd.concat([g, po], ignore_index=True), geometry="geometry", crs=4326)
    # airfields gone from today's map (NAS Alameda 1940-97, Crissy Field 1921-74): researched
    # pavement polygons (data/manual/airports_extra.geojson, already at their real width; a
    # piece with its own start_year / end_year keeps them) + airfield outline
    extra_f = MANUAL / "airports_extra.geojson"
    extra_o = MANUAL / "airports_extra_outlines.geojson"
    if extra_f.exists() and extra_o.exists():
        ef = gpd.read_file(extra_f).to_crs(4326).rename(columns={"airport": "name"})
        ef["class"] = ef["kind"]
        for c in ("start_year", "end_year"):
            ef["piece_" + c] = pd.to_numeric(ef[c], errors="coerce") if c in ef else np.nan
        eo = gpd.read_file(extra_o).to_crs(4326)
        g = gpd.GeoDataFrame(pd.concat([g, ef[["name", "class", "piece_start_year", "piece_end_year", "geometry"]],
                                        eo[["name", "class", "geometry"]]],
                                       ignore_index=True), geometry="geometry", crs=4326)
        log(f"airports: + {len(ef)} researched pavement polygons, {len(eo)} outlines of vanished airfields")
    ports = g[g["class"].isin(AIRPORT_CLASSES) & (g.geom_type == "Polygon")].copy()
    t = pd.read_csv(TABLES / "airports.csv")
    ports = ports.merge(t[["name", "opened", "closed"]], on="name", how="left")
    ports["opened"] = pd.to_numeric(ports.opened, errors="coerce")
    ports["closed"] = pd.to_numeric(ports.closed, errors="coerce").fillna(9999.0)
    log(f"airports: {len(ports)} airport outlines, {ports.opened.notna().sum()} dated "
        f"(undated: {sorted(ports[ports.opened.isna()].name.dropna().tolist())[:12]}…)")
    ports["opened"] = ports.opened.fillna(1950.0)  # undated small fields: estimated
    pu = ports.to_crs(UTM)
    pu[["name", "class", "opened", "closed", "geometry"]].to_crs(4326).to_parquet(INTERIM / "airports.parquet")

    f = g[g["class"].isin(list(KIND))].copy().to_crs(UTM)
    # features belong to the airport they touch, else the nearest one within 1.5 km (SFO's
    # maintenance base, aprons just outside a drawn boundary); farm strips far from any
    # mapped airport are left out
    j = gpd.sjoin_nearest(f, pu[["class", "opened", "closed", "geometry"]].rename(columns={"class": "aclass"}),
                          how="left", max_distance=1500)
    j = j[~j.index.duplicated()]
    # align by row label (sjoin_nearest returns its rows in its own order: assigning .values
    # positionally gave features other airports' opening years)
    f["aclass"] = j.aclass.reindex(f.index).values
    f["opened"] = j.opened.reindex(f.index).values
    f["closed"] = j.closed.reindex(f.index).values
    if "piece_start_year" in f:
        # researched pieces of vanished airfields carry their own years (Crissy Field's paved
        # runway 1947-99 inside an airfield of 1921-74)
        f["opened"] = f.piece_start_year.where(f.piece_start_year.notna() & f.opened.notna(), f.opened)
        f["closed"] = f.piece_end_year.where(f.piece_end_year.notna() & f.opened.notna(), f.closed)
    f = f[f.opened.notna()]
    big = f.aclass.isin(list(BIG)).values
    width = np.select([f["class"].isin(["runway", "stopway"]).values, f["class"].eq("taxiway").values,
                       f["class"].eq("taxilane").values], [np.where(big, 45, 23), np.where(big, 23, 15), 10], 0)
    geoms = []
    for geom, w in zip(f.geometry.values, width):
        if geom.geom_type == "LineString":
            geoms.append(geom.buffer(w / 2, cap_style="flat", join_style="round"))
        else:
            geoms.append(geom)
    f = f.set_geometry(gpd.GeoSeries(geoms, index=f.index, crs=UTM))  # same row labels as f
    f = dated_pavement(f)
    # vertices every 25 m so the flat polygons follow the terrain (earcut joins the long
    # edges of a runway across its width, so the inside follows too); segmentize can turn
    # a clipped piece with a pinched ring into a MultiPolygon, so explode afterwards
    f = f.set_geometry(f.geometry.make_valid().segmentize(25))
    f = f.explode(index_parts=False).reset_index(drop=True)
    f = f[(f.geometry.geom_type == "Polygon") & (f.geometry.area > 20)].reset_index(drop=True)
    ll = f.to_crs(4326)
    # ground year of a piece = median over its representative point and up to 24 of its
    # vertices ("always land" counts as earliest): one cell of a ditch or pond that only
    # became land with a later building no longer holds back a whole taxiway
    smp = []
    for geom in ll.geometry.values:
        xy = np.asarray(geom.exterior.coords)[:-1, :2]
        xy = xy[np.linspace(0, len(xy) - 1, min(len(xy), 24)).astype(int)]
        rp = geom.representative_point()
        smp.append(np.vstack([[rp.x, rp.y], xy]))
    n_s = np.array([len(s) for s in smp])
    allp = np.vstack(smp)
    lys = land_year(allp[:, 0], allp[:, 1])
    lys = np.where(np.isfinite(lys), lys, -1e4)
    ly = np.array([np.median(v) for v in np.split(lys, np.cumsum(n_s)[:-1])])
    ly = np.where(ly < 0, np.nan, ly)
    start = np.where(np.isfinite(ly), np.maximum(f.opened.values, ly + 0.5), f.opened.values)
    # dated pavement for the terrain: the airfield's grass follows its pavement phases
    # (terrain_tiles.py), not the whole of today's outline from the opening year
    gpd.GeoDataFrame({"start": start, "end": f.closed.values, "kind": f["class"].map(KIND).values},
                     geometry=f.geometry.values, crs=UTM).to_crs(4326).to_parquet(INTERIM / "airport_pavement.parquet")
    ground = Ground()
    starts, pos, kinds, years = [0], [], [], []
    # drawn in this order without depth writes (viewer DrapeExtension): aprons, then
    # taxiways, then runways on top; big pieces before small ones
    kind_arr = f["class"].map(KIND).values
    order = np.lexsort((-f.geometry.area.values, -kind_arr))
    for i in order:
        geom, k, y0, y1 = ll.geometry.values[i], kind_arr[i], start[i], f.closed.values[i]
        ring = np.asarray(geom.exterior.coords)[:, :2]
        z = ground(ring[:, 0], ring[:, 1]) + 0.35
        pos.append(np.column_stack([ring[:, 0] - ORIGIN[0], ring[:, 1] - ORIGIN[1], z]).ravel())
        starts.append(starts[-1] + len(ring))
        kinds.append(k)
        years.extend((float(y0), float(y1)))
    # centre lines of runways and taxiways (long axis of each piece): drawn with a
    # minimum pixel width so the airfields still read when zoomed far out
    lstarts, lpos, lkind, lwidth, lyears = [0], [], [], [], []
    fu = f.geometry.values
    for geom, k, y0, y1 in zip(fu, kind_arr, start, f.closed.values):
        # runways only (taxiway pieces are curved / L-shaped: their bounding rectangle
        # drew wide grey bands across the field when zoomed out), and only pieces that
        # are close to a rectangle; width = area / length (the true mean width)
        if k != 0:
            continue
        mrr = geom.minimum_rotated_rectangle
        if geom.area < 0.8 * mrr.area:
            continue
        rect = np.asarray(mrr.exterior.coords)[:4]
        e1, e2 = rect[1] - rect[0], rect[2] - rect[1]
        if np.hypot(*e1) >= np.hypot(*e2):
            a, b = (rect[0] + rect[3]) / 2, (rect[1] + rect[2]) / 2
        else:
            a, b = (rect[0] + rect[1]) / 2, (rect[2] + rect[3]) / 2
        L = np.hypot(*(b - a))
        w = geom.area / max(L, 1.0)
        if L < 3 * w:
            continue
        ll = gpd.GeoSeries(gpd.points_from_xy([a[0], b[0]], [a[1], b[1]]), crs=UTM).to_crs(4326)
        lon, lat = ll.x.values, ll.y.values
        z = ground(lon, lat) + 0.45
        lpos.append(np.column_stack([lon - ORIGIN[0], lat - ORIGIN[1], z]).ravel())
        lstarts.append(lstarts[-1] + 2)
        lkind.append(k)
        lwidth.append(min(255, max(1, round(w))))
        lyears.extend((float(y0), float(y1)))
    write_columnar(VIEWER_DATA / "airport-lines.bin.gz", {
        "start_indices|shuffle": np.asarray(lstarts, np.uint32),
        "positions|shuffle": np.concatenate(lpos).astype(np.float32),
        "kind": np.asarray(lkind, np.uint8),
        "width": np.asarray(lwidth, np.uint8),
        "years": np.asarray(lyears, np.float32),
    }, origin=ORIGIN, counts={"paths": len(lkind), "vertices": lstarts[-1]})
    write_columnar(VIEWER_DATA / "airports.bin.gz", {
        "start_indices|shuffle": np.asarray(starts, np.uint32),
        "positions|shuffle": np.concatenate(pos).astype(np.float32),
        "kind": np.asarray(kinds, np.uint8),
        "years": np.asarray(years, np.float32),
    }, origin=ORIGIN, counts={"polygons": len(kinds), "vertices": starts[-1]})
    log(f"airports: {len(kinds)} runway / taxiway / apron polygons ({np.bincount(kinds, minlength=3).tolist()})")


if __name__ == "__main__":
    main()
