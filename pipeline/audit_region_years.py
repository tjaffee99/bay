"""Audit: likely-wrong construction years in the built five-county building tiles.

Pipeline-independent (reads only files, imports nothing from the pipeline): run after
`region_buildings.py` has written viewer/public/data/region-buildings/.

    .venv/bin/python pipeline/audit_region_years.py

Inputs
  * built tiles   viewer/public/data/region-buildings/13/x/y.bin.gz (BAYT; what the viewer shows)
  * footprints    data/raw/overture/<release>/region5_building.parquet (id -> crc32 = tile fid)
  * candidates    data/interim/region5_footprint_years.parquet (per-footprint roll / copy / vendor / survey years)
  * land use      data/raw/overture/<release>/region5_land_use.parquet (OSM campus / hospital / military /
                  religious / cemetery polygons for the five counties; falls back to base_land_use.parquet)
  * surveys       data/interim/region_years.parquet (OHP BERD + San José HRI points)
  * research      data/tables/known_building_dates_region.csv (researched years; point in footprint)

Anomaly classes (one footprint can be in several)
  institutional_imputed  on campus / hospital / military / religious / cemetery / civic land, or an
                         institutional Overture class, with NO recorded year: the year was borrowed from
                         the (usually residential) neighbours -> Stanford's Main Quad in 1983
  campus_shared_year     a campus where >= 5 buildings and >= 60 % of its dated buildings carry one
                         identical year: a parcel / vendor year applied to every building (UC Berkeley 1920)
  campus_outlier         a large building (>= 1,000 m2) whose year is >= 40 y later or earlier than the
                         median of the 8 nearest buildings on the same campus
  tall_early             height >= 35 m before 1920, >= 50 m before 1950, >= 25 m before 1900 (SF's floors)
  round_year_cluster     250 m cells with >= 12 buildings where >= 60 % share one round (x0 / x5) year
  survey_disagrees       an OHP BERD / San José HRI point (single dated building) inside or within 10 m of
                         a footprint whose built year differs by > 15 y
  roll_vs_survey         both a survey year and a roll / vendor year exist for the footprint and differ by
                         > 20 y (assign_years takes the survey; listed as evidence of roll errors)
  pre1850_recorded       recorded year before 1850 used as exact

Output: data/interim/reports/region_year_audit.md (+ region_year_audit_flags.parquet with every flag)
"""
from __future__ import annotations

import glob
import gzip
import json
import struct
import zlib
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import shapely
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "2026-10-21.0"
TILES = ROOT / "viewer/public/data/region-buildings/13"
OVR = ROOT / "data/raw/overture" / RELEASE
INTERIM = ROOT / "data/interim"
REPORTS = INTERIM / "reports"
RESEARCH = ROOT / "data/tables/known_building_dates_region.csv"
UTM = "EPSG:32610"
DT = {"f32": np.float32, "f64": np.float64, "u32": np.uint32, "i32": np.int32, "u16": np.uint16, "i16": np.int16,
      "u8": np.uint8}
CONF = ["exact", "estimated", "procedural", "reconstructed"]
INST_LU = {"education": None, "medical": None, "military": None, "religious": None, "cemetery": None}
INST_CLASS_SKIP = {"kindergarten", "schoolyard", "clinic", "doctors", "danger_area", "range", "training_area"}
INST_OVERTURE = {"university", "college", "school", "hospital", "church", "cathedral", "chapel", "mosque", "temple",
                 "synagogue", "religious", "civic", "government", "public", "military", "hangar", "terminal",
                 "fire_station", "transportation", "train_station"}


def log(*a):
    print("[audit]", *a, flush=True)


# ---------------------------------------------------------------------------- inputs
def read_bayt(path):
    b = gzip.open(path).read()
    assert b[:4] == b"BAYT"
    n = struct.unpack("<I", b[4:8])[0]
    h = json.loads(b[8:8 + n])
    base = 8 + n
    base += (-base) % 8
    out = {}
    for c in h["columns"]:
        dt = np.dtype(DT[c["dtype"]])
        raw = b[base + c["offset"]: base + c["offset"] + c["length"] * dt.itemsize]
        if c.get("shuffle"):
            arr = np.frombuffer(raw, np.uint8).reshape(dt.itemsize, -1).T.copy().view(dt).ravel()
        else:
            arr = np.frombuffer(raw, dt)
        out[c["name"]] = arr
    return h, out


def tile_features():
    rows = []
    for f in sorted(glob.glob(str(TILES / "*" / "*.bin.gz"))):
        h, o = read_bayt(f)
        n = h["counts"]["features"]
        ox, oy = h["origin"]
        pos = o["positions_delta"].reshape(-1, 2).astype(np.int64)
        st = o["start_indices"].astype(np.int64)
        valid = o["vertex_valid"]
        cx, cy = np.zeros(n), np.zeros(n)
        for i in range(n):
            a, b = st[i], st[i + 1]
            q = np.cumsum(pos[a:b], axis=0)
            e = np.nonzero(valid[a:b] == 0)[0]
            r = q[: (e[0] + 1 if len(e) else b - a)]
            cx[i] = ox + r[:, 0].mean() * 1e-7
            cy[i] = oy + r[:, 1].mean() * 1e-7
        rows.append(pd.DataFrame({"fid": o["fid"], "lon": cx, "lat": cy, "year": o["start_year"].astype(float),
                                  "end": o["end_year"].astype(float), "height": o["height"].astype(float),
                                  "conf": o["confidence"], "raw": o["raw_year"].astype(int)}))
    df = pd.concat(rows, ignore_index=True)
    df["conf"] = np.array(CONF)[np.minimum(df.conf.values, 3)]
    log(f"tiles: {len(df)} features")
    return df


def footprints(t):
    cols = ["id", "class", "subtype", "name", "height", "px", "py", "county", "geometry"]
    tb = pq.read_table(OVR / "region5_building.parquet", columns=cols)
    b = tb.drop(["geometry"]).to_pandas()
    b["wkb"] = tb.column("geometry").to_numpy(zero_copy_only=False)
    b["fid"] = np.array([zlib.crc32(s.encode()) for s in b.id.values], dtype=np.uint32)
    m = t.reset_index().merge(b, on="fid", how="inner")
    # crc32 collisions: keep the footprint whose point lies closest to the tile outline's centroid
    m["d"] = np.hypot(m.px - m.lon, m.py - m.lat)
    m = m.sort_values("d").drop_duplicates("index").drop_duplicates("id").sort_values("index")
    fy = pd.read_parquet(INTERIM / "region5_footprint_years.parquet").drop(columns=["county"])
    m = m.merge(fy, on="id", how="left")
    m["geometry"] = shapely.from_wkb(m.pop("wkb").values)
    g = gpd.GeoDataFrame(m.drop(columns=["d"]), geometry="geometry", crs=4326)
    g["area_m2"] = g.area_m2.fillna(pd.Series(g.to_crs(UTM).area.values, index=g.index))
    g["recorded"] = g[[c for c in ("year_public", "year_third_party", "year_commercial", "year_historic")
                       if c in g]].notna().any(axis=1)
    log(f"footprints: {len(g)} of {len(t)} tile features matched to Overture ({(~g.recorded).sum()} with no record)")
    return g


def campuses():
    p = OVR / "region5_land_use.parquet"
    lu = gpd.read_parquet(p if p.exists() else OVR / "base_land_use.parquet")
    lu = lu.set_crs(4326, allow_override=True)
    keep = lu.subtype.isin(list(INST_LU)) | (lu["class"] == "institutional")
    lu = lu[keep & ~lu["class"].isin(INST_CLASS_SKIP)].copy()
    lu["lu_area"] = lu.to_crs(UTM).area.values
    lu = lu.rename(columns={"name": "campus", "class": "campus_class", "subtype": "campus_type"})
    lu["campus_id"] = np.arange(len(lu))
    log(f"land use: {len(lu)} institutional polygons ({lu.campus_type.value_counts().to_dict()})")
    return lu[["campus_id", "campus", "campus_class", "campus_type", "lu_area", "geometry"]]


def research_points():
    if not RESEARCH.exists():
        return None
    k = pd.read_csv(RESEARCH)
    k = k[pd.to_numeric(k.start_year, errors="coerce").notna()]
    return gpd.GeoDataFrame(k, geometry=gpd.points_from_xy(k.lon, k.lat), crs=4326)


def survey_points():
    t = pq.read_table(INTERIM / "region_years.parquet",
                      columns=["src", "year_built", "year_flag", "is_building", "demolished", "moved", "address",
                               "name", "geometry"],
                      filters=[("src", "in", ["ca_ohp_berd", "san_jose_hri"])]).to_pandas()
    t["geometry"] = shapely.from_wkb(t.geometry.values)
    t = gpd.GeoDataFrame(t, geometry="geometry", crs=4326)
    ok = (t.year_flag == "ok") & t.year_built.notna() & (t.is_building.fillna(True).astype(bool))
    ok &= ~t.demolished.fillna(False).astype(bool) & ~t.moved.fillna(False).astype(bool)
    return t[ok].reset_index(drop=True)


# ---------------------------------------------------------------------------- checks
def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    t = tile_features()
    g = footprints(t)
    pts = gpd.GeoDataFrame(g[["id"]], geometry=gpd.points_from_xy(g.px, g.py), crs=4326)
    lu = campuses().sort_values("lu_area")  # the smallest enclosing polygon wins (school inside a city campus)
    j = gpd.sjoin(pts, lu, predicate="within", how="left")
    j = j[~j.index.duplicated(keep="first")]
    for c in ("campus_id", "campus", "campus_class", "campus_type"):
        g[c] = j[c].reindex(g.index).values
    cls = g["class"].fillna("").str.lower()
    g["institutional"] = g.campus_id.notna() | cls.isin(INST_OVERTURE)
    g["inst_kind"] = np.where(g.campus_id.notna(), g.campus_class.fillna(""), cls)

    # researched rows: the footprint containing each point takes the researched year
    rp = research_points()
    g["research_year"] = np.nan
    if rp is not None:
        hit = gpd.sjoin(rp, g[["geometry"]], predicate="within", how="inner")
        ry = hit.groupby("index_right").start_year.first()
        g.loc[ry.index, "research_year"] = ry.values
        missed = len(rp) - hit.drop_duplicates("id").shape[0] if "id" in hit else len(rp) - len(hit)
        log(f"research: {len(rp)} rows, {g.research_year.notna().sum()} footprints hit, {missed} rows hit nothing")
    g["fixed"] = g.research_year.notna()
    yr = g.year.values
    flags = []

    def flag(mask, cls_, why):
        idx = np.nonzero(np.asarray(mask))[0]
        flags.append(pd.DataFrame({"i": idx, "flag": cls_, "why": why if isinstance(why, str) else np.asarray(why)[idx]}))

    # 1 institutional land / class without any recorded year
    inst_imp = g.institutional & ~g.recorded & (g.area_m2 >= 40)
    why = np.where(g.campus_id.notna(), "no recorded year on " + g.inst_kind.fillna("").astype(str) + " land",
                   "no recorded year (Overture class " + cls + ")")
    flag(inst_imp, "institutional_imputed", why)

    # 2 campus-wide shared year (parcel or vendor year on every building)
    rec = g[g.recorded & g.campus_id.notna()]
    shared = []
    for cid, grp in rec.groupby("campus_id"):
        if len(grp) < 5:
            continue
        vc = grp.year.round().value_counts()
        y0, n0 = vc.index[0], vc.iloc[0]
        if n0 >= 5 and n0 / len(grp) >= 0.6:
            shared.append((cid, y0, n0, len(grp), grp.campus.iloc[0], grp.campus_class.iloc[0], grp.county.iloc[0]))
            m = (g.campus_id == cid) & g.recorded & (g.year.round() == y0)
            flag(m, "campus_shared_year", f"{int(n0)}/{len(grp)} dated buildings on the campus read {int(y0)}")
    shared = pd.DataFrame(shared, columns=["campus_id", "year", "n_same", "n_dated", "campus", "kind", "county"])

    # 3 campus outliers (vs the 8 nearest buildings on the same campus)
    u = gpd.GeoSeries(gpd.points_from_xy(g.px, g.py), crs=4326).to_crs(UTM)
    xy = np.column_stack([u.x.values, u.y.values])
    out_mask = np.zeros(len(g), bool)
    out_why = np.array([""] * len(g), dtype=object)
    for cid, idx in g[g.campus_id.notna()].groupby("campus_id").groups.items():
        idx = np.asarray(idx)
        if len(idx) < 6:
            continue
        tree = cKDTree(xy[idx])
        k = min(9, len(idx))
        _, nn = tree.query(xy[idx], k=k)
        med = np.median(yr[idx][nn[:, 1:]], axis=1)
        dev = yr[idx] - med
        big = g.area_m2.values[idx] >= 1000
        m = big & (np.abs(dev) >= 40)
        out_mask[idx[m]] = True
        out_why[idx[m]] = [f"{yr[i]:.0f} vs campus neighbours {mm:.0f}" for i, mm in zip(idx[m], med[m])]
    flag(out_mask, "campus_outlier", out_why)

    # 4 tall buildings with implausibly early years
    h = g.height_x.values if "height_x" in g else g.height.values
    tall = ((h >= 35) & (yr < 1920)) | ((h >= 50) & (yr < 1950)) | ((h >= 25) & (yr < 1900))
    flag(tall, "tall_early", [f"{hh:.0f} m tall in {y:.0f}" for hh, y in zip(h, yr)])

    # 5 round-year clusters (250 m cells)
    cell = (np.floor(xy[:, 0] / 250).astype(np.int64) * 1000003 + np.floor(xy[:, 1] / 250).astype(np.int64))
    cdf = pd.DataFrame({"c": cell, "y": np.floor(yr)})
    cnt = cdf.groupby("c").size()
    top = cdf.groupby("c").y.agg(lambda s: s.value_counts().index[0])
    topn = cdf.groupby("c").y.agg(lambda s: s.value_counts().iloc[0])
    # placeholders are pre-war round years (1900, 1910, 1920, 1925 ...); a post-war tract often really was
    # finished in one (round or not) year, so those cells are only counted for context
    rnd = ((top % 10 == 0) & (top <= 1950)) | ((top % 5 == 0) & (top <= 1930))
    sus = (cnt >= 12) & (topn / cnt >= 0.6) & rnd
    late_round = int(((cnt >= 12) & (topn / cnt >= 0.6) & (top % 5 == 0) & ~rnd).sum())
    sus_cells = set(sus[sus].index)
    m = np.isin(cell, list(sus_cells)) & (cdf.y.values == top.reindex(cell).values)
    flag(m, "round_year_cluster", [f"cell shares {y:.0f}" for y in np.floor(yr)])
    round_cells = pd.DataFrame({"cell": list(sus_cells)})
    round_cells.attrs["late"] = late_round

    # 6 survey points vs built year
    sv = survey_points()
    sv_in = gpd.sjoin(sv, g[["geometry"]], predicate="within", how="inner")
    sv_out = sv[~sv.index.isin(sv_in.index)]
    sv_near = gpd.sjoin_nearest(sv_out.to_crs(UTM), g[["geometry"]].to_crs(UTM), max_distance=10, how="inner")
    both = pd.concat([pd.DataFrame(sv_in.drop(columns="geometry")).assign(where="inside"),
                      pd.DataFrame(sv_near.drop(columns="geometry")).assign(where="within 10 m")])
    both = both[~both.index.duplicated(keep="first")]
    both["built"] = yr[both.index_right.values]
    both["diff"] = both.built - both.year_built
    dis = both[both["diff"].abs() > 15]
    sm = np.zeros(len(g), bool)
    sm[dis.index_right.values] = True
    swhy = np.array([""] * len(g), dtype=object)
    swhy[dis.index_right.values] = [f"{s} {y:.0f} ({w}) vs built {b:.0f}" for s, y, w, b in
                                     zip(dis.src, dis.year_built, dis["where"], dis.built)]
    flag(sm, "survey_disagrees", swhy)

    # 7 roll / vendor year vs survey year inside the same footprint
    roll = g.year_public.fillna(g.year_third_party).fillna(g.year_commercial).astype(float)
    hist = g.year_historic.astype(float)
    rvs = hist.notna() & roll.notna() & ((roll - hist).abs() > 20)
    flag(rvs, "roll_vs_survey", [f"survey {a:.0f} vs roll {b:.0f}" if np.isfinite(a) and np.isfinite(b) else ""
                                 for a, b in zip(hist, roll)])

    # 8 recorded pre-1850
    flag((yr < 1850) & (g.conf == "exact").values, "pre1850_recorded", [f"{y:.0f}" for y in yr])

    F = pd.concat(flags, ignore_index=True)
    F = F.merge(g[["id", "name", "county", "campus", "campus_class", "inst_kind", "area_m2", "year", "raw", "conf", "px", "py",
                   "research_year", "fixed"]].assign(height=h), left_on="i", right_index=True)
    F.drop(columns=["i"]).to_parquet(REPORTS / "region_year_audit_flags.parquet")
    write_report(g, F, shared, round_cells, both, dis, rp, h)


# ---------------------------------------------------------------------------- report
def fmt_row(r):
    nm = r["name"] if isinstance(r["name"], str) else "(unnamed)"
    camp = r["campus"] if isinstance(r.get("campus"), str) else ""
    fx = f" → **{r.research_year:.0f}** (research)" if r.fixed else ""
    camp = camp or (f"({r.inst_kind})" if isinstance(r.get("inst_kind"), str) and r.inst_kind else "")
    return (f"| {nm[:44]} | {camp[:34]} | {r.county} | {r.area_m2:,.0f} | {r.height:.0f} | {r.year:.0f}{fx} | "
            f"{r.why} | {r.py:.5f}, {r.px:.5f} |")


def table(F, n=25, sort="area_m2"):
    hdr = "| building | campus / land use | county | m² | h m | year shown | why | lat, lon |\n|---|---|---|--:|--:|---|---|---|"
    rows = [fmt_row(r) for _, r in F.sort_values(sort, ascending=False).head(n).iterrows()]
    return hdr + "\n" + "\n".join(rows)


def write_report(g, F, shared, round_cells, both, dis, rp, h):
    L = ["# Region building-year audit (five counties)", "",
         "Generated by `pipeline/audit_region_years.py` from the built tiles "
         "(`viewer/public/data/region-buildings/13/`), Overture footprints, the per-footprint candidate years, "
         "OSM land use and the OHP BERD / San José HRI survey points. "
         f"Researched rows: `data/tables/known_building_dates_region.csv` "
         f"({0 if rp is None else len(rp)} rows). "
         "A footprint is *fixed* when a researched point lies in it (the pipeline should then take that year "
         "as `exact`); *year shown* is what the current tiles show.", ""]
    n = len(g)
    L += [f"Footprints audited: **{n:,}** ({(~g.recorded).sum():,} without any recorded year; "
          f"{g.institutional.sum():,} on institutional land or with an institutional class).", ""]
    # summary
    L += ["## Summary", "", "| class | footprints | of which ≥ 1,000 m² | fixed by research | still open (≥ 1,000 m²) |",
          "|---|--:|--:|--:|--:|"]
    order = ["institutional_imputed", "campus_shared_year", "campus_outlier", "tall_early", "round_year_cluster",
             "survey_disagrees", "roll_vs_survey", "pre1850_recorded"]
    for c in order:
        s = F[F.flag == c]
        big = s.area_m2 >= 1000
        L.append(f"| `{c}` | {len(s):,} | {big.sum():,} | {s.fixed.sum():,} | {(big & ~s.fixed).sum():,} |")
    L += ["", "By county (footprints flagged at least once, ≥ 100 m²):", "",
          "| county | flagged | institutional_imputed | campus_shared_year | survey_disagrees | tall_early |",
          "|---|--:|--:|--:|--:|--:|"]
    F100 = F[F.area_m2 >= 100]
    for cty, s in F100.groupby("county"):
        L.append(f"| {cty} | {s.id.nunique():,} | {(s.flag == 'institutional_imputed').sum():,} | "
                 f"{(s.flag == 'campus_shared_year').sum():,} | {(s.flag == 'survey_disagrees').sum():,} | "
                 f"{(s.flag == 'tall_early').sum():,} |")
    # research effect
    if rp is not None:
        fx = g[g.fixed]
        d = (fx.research_year - fx.year).abs()
        L += ["", "## Effect of the researched table", "",
              f"{len(fx):,} footprints carry a researched year; the tiles currently show a year more than 5 years "
              f"off for **{(d > 5).sum():,}** of them (more than 20 years off: {(d > 20).sum():,}; median error "
              f"{d.median():.0f} y). Biggest corrections:", "",
              "| building | county | m² | shown | researched |", "|---|---|--:|--:|--:|"]
        for _, r in fx.assign(d=d).sort_values("d", ascending=False).head(30).iterrows():
            nm = r["name"] if isinstance(r["name"], str) else "(unnamed)"
            L.append(f"| {nm[:50]} | {r.county} | {r.area_m2:,.0f} | {r.year:.0f} | {r.research_year:.0f} |")
    # per class detail
    L += ["", "## institutional_imputed — no recorded year on institutional land", "",
          "Exempt parcels (universities, schools, hospitals, churches, government, military, airports) have no "
          "roll year; the pipeline borrows the median of nearby recorded buildings (often a 1950s–80s tract or a "
          "placeholder), so historic campuses appear decades late. Campuses by floor area without a recorded year "
          "(*fixed* = footprints that now have a researched row):", "",
          "| campus / land use | kind | county | buildings | m² | fixed |", "|---|---|---|--:|--:|--:|"]
    s = F[(F.flag == "institutional_imputed")]
    s = s.assign(campus=s.campus.fillna("(no land-use polygon; Overture class)"),
                 campus_class=s.campus_class.fillna(s.inst_kind.fillna("")))
    agg = s.groupby(["campus", "campus_class", "county"], dropna=False).agg(
        n=("id", "size"), m2=("area_m2", "sum"), fixed=("fixed", "sum"))
    for (c, k, cty), r in agg.sort_values("m2", ascending=False).head(40).iterrows():
        L.append(f"| {c} | {k} | {cty} | {int(r.n)} | {r.m2:,.0f} | {int(r.fixed)} |")
    L += ["", "Largest open examples:", "", table(s[~s.fixed], 30)]
    L += ["", "## campus_shared_year — one year on a whole campus", "",
          "A parcel / vendor year copied onto every building of a campus (pitfall 3); 1920 at UC Berkeley is "
          "FEMA/Lightbox's placeholder, which `assign_years` treats as a spike (upper bound) and then imputes.", "",
          "| campus | kind | county | year | same / dated |", "|---|---|---|--:|--:|"]
    for _, r in shared.sort_values("n_same", ascending=False).head(40).iterrows():
        L.append(f"| {r.campus if isinstance(r.campus, str) else '(unnamed)'} | {r.kind} | {r.county} | {r.year:.0f} | "
                 f"{r.n_same} / {r.n_dated} |")
    L += [f"", f"{len(shared)} campuses in total."]
    for c, title, txt in [
        ("campus_outlier", "campus_outlier — ≥ 40 years off the campus neighbours",
         "Large buildings (≥ 1,000 m²) whose year is ≥ 40 years later or earlier than the median of their "
         "8 nearest campus neighbours."),
        ("tall_early", "tall_early — tall buildings with early years",
         "SF's height floors applied to the region: ≥ 35 m before 1920, ≥ 50 m before 1950, ≥ 25 m before 1900. "
         "Most are real (Oakland City Hall, Tribune Tower, Cathedral Building) or a newer tower on an old parcel."),
        ("round_year_cluster", "round_year_cluster — placeholder years",
         f"{len(round_cells)} 250 m cells where ≥ 12 buildings and ≥ 60 % share one pre-war round year "
         "(x0 up to 1950, x5 up to 1930): parcel or vendor placeholders not caught by the per-source spike test. "
         f"(Another {round_cells.attrs.get('late', 0)} cells share a post-war round year; those are mostly real "
         "one-year tracts and are not flagged.)"),
        ("survey_disagrees", "survey_disagrees — historic survey year vs built year",
         f"OHP BERD / San José HRI single-building points ({len(both):,} matched to a footprint, inside or "
         f"≤ 10 m) whose year differs from the built year by > 15 y ({len(dis):,}). 'within 10 m' cases are "
         "survey points placed on the parcel point next to the building, which `assign_years` never sees."),
        ("roll_vs_survey", "roll_vs_survey — roll / vendor year vs survey year in the same footprint",
         "Evidence of roll errors: the survey year wins in `assign_years`, so these are already fixed in the "
         "tiles unless the survey year was a range or spike."),
        ("pre1850_recorded", "pre1850_recorded", "Recorded years before 1850 used as exact (adobes are real; most are typos)."),
    ]:
        s = F[F.flag == c]
        L += ["", f"## {title}", "", txt, "", f"{len(s):,} footprints ({(s.area_m2 >= 1000).sum():,} ≥ 1,000 m², "
              f"{s.fixed.sum():,} fixed by research).", "", table(s[~s.fixed], 25, "height" if c == "tall_early" else "area_m2")]
    L += ["", "## What remains", "",
          "* Unnamed campus buildings (UC Berkeley, Stanford, SJSU, LBNL, hospitals) without a researched row keep "
          "an imputed year; a campus-level rule (buildings on a dated campus can't predate its founding; a big "
          "historic campus core shouldn't take tract-house years) would cover the rest.",
          "* Public schools (the largest group by count) mostly date from the 1950s–60s school boom and their "
          "imputed years are usually close; individual campuses need district records.",
          "* Survey points just outside their footprint (`within 10 m`) could be snapped in `assign_years`.", ""]
    out = REPORTS / "region_year_audit.md"
    out.write_text("\n".join(L))
    log(f"wrote {out} ({len(F):,} flags on {F.id.nunique():,} footprints)")


if __name__ == "__main__":
    main()
