"""Markdown tables for README.md from industrial_def.py, sites.geojson and traced/audit*.csv.

  python -I tools/readme_tables.py > /tmp/tables.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from industrial_def import SITES  # noqa: E402

OUT = HERE.parent


def yr(v):
    v = float(v)
    return "today" if v >= 9999 else (f"{v:.0f}" if abs(v - round(v)) < 0.05 else f"{v:.1f}")


def main():
    feats = json.loads((OUT / "sites.geojson").read_text())["features"]
    parts = pd.DataFrame([f["properties"] for f in feats])
    au = pd.read_csv(OUT / "traced" / "audit.csv").set_index("site_id")
    at = OUT / "traced" / "audit_terrain.csv"
    te = pd.read_csv(at) if at.exists() else None
    print("| site | label | kind | years | parts | outline | confidence |")
    print("|---|---|---|---|---|---|---|")
    for s in SITES:
        p = parts[parts.site_id == s["site_id"]]
        src = set()
        for pp in s["parts"]:
            src |= {k for k in ("osm", "osm_box", "traced", "files", "hull") if k in pp}
        lab = s.get("label_years")
        years = f"{yr(s['start'])}–{yr(s['end'])}" + (f" (named {yr(lab[0])}–{yr(lab[1])})" if lab else "")
        print(f"| `{s['site_id']}` | {s['label']} | {s['kind']} | {years} | {len(p)} | "
              f"{', '.join(sorted(src)) or 'building only'} | {s['conf']} |")
    print()
    print("| site | founded | footprints | live p10 / median | drawn on maps | corrected (too late / too early) | median shift (yr) |")
    print("|---|---|---|---|---|---|---|")
    for sid, r in au.iterrows():
        if r.footprints == 0:
            continue
        print(f"| `{sid}` | {yr(r.founded)} | {int(r.footprints)} | {yr(r.live_p10) if pd.notna(r.live_p10) else ''} / "
              f"{yr(r.live_median) if pd.notna(r.live_median) else ''} | "
              f"{'' if pd.isna(r.drawn_on_maps) else int(r.drawn_on_maps)} | {int(r.corrected)} ({int(r.too_late)} / "
              f"{int(r.too_early)}) | {r.median_shift_years:+.0f} |")
    if te is not None:
        print()
        g = te.groupby("site_id").apply(lambda t: pd.Series({
            "cells": int(t.cells.sum()),
            "bare": (t.bare_share * t.cells).sum() / t.cells.sum(),
            "built": (t.built_share * t.cells).sum() / t.cells.sum()}))
        g = g[g.bare > 0.15].sort_values("bare", ascending=False)
        print("| site | terrain vertices | WorldCover bare (rock from 1769) | built |")
        print("|---|---|---|---|")
        for sid, r in g.iterrows():
            print(f"| `{sid}` | {int(r.cells)} | {r.bare:.0%} | {r.built:.0%} |")


if __name__ == "__main__":
    main()
