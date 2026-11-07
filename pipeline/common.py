"""Shared helpers for pipeline stages.

Every stage is idempotent: it checks whether its outputs exist (and are newer
than its inputs where that matters) and skips work otherwise. Raw downloads in
data/raw are never modified in place.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
MANUAL = ROOT / "data" / "manual"
TABLES = ROOT / "data" / "tables"
VIEWER_DATA = ROOT / "viewer" / "public" / "data"

USER_AGENT = "BayThroughTime-pipeline/0.1 (+https://github.com/tjaffee99/bay)"

# Feature lifespans: end_year of a feature that still exists.
STILL_EXISTS = 9999
# The "present" for the slider.
CURRENT_YEAR = 2026

for d in (RAW, INTERIM, VIEWER_DATA):
    d.mkdir(parents=True, exist_ok=True)


def log(*args):
    print(f"[{time.strftime('%H:%M:%S')}]", *args, file=sys.stderr, flush=True)


def session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    ca = "/root/.ccr/ca-bundle.crt"
    if os.path.exists(ca) and not os.environ.get("REQUESTS_CA_BUNDLE"):
        s.verify = ca
    return s


def get_with_retry(s: requests.Session, url: str, params=None, tries: int = 5, **kw):
    delay = 2.0
    for attempt in range(tries):
        try:
            r = s.get(url, params=params, timeout=300, **kw)
            if r.status_code == 200:
                return r
            log(f"HTTP {r.status_code} for {url} (attempt {attempt + 1})")
        except requests.RequestException as e:  # network hiccup
            log(f"error {e!r} for {url} (attempt {attempt + 1})")
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"failed to fetch {url}")


def socrata_pages(dataset: str, out_dir: Path, select: str | None = None,
                  where: str | None = None, order: str = ":id",
                  page_size: int = 50000, fmt: str = "json") -> list[Path]:
    """Download a Socrata dataset page by page into out_dir/page-XXXX.<fmt>.

    Pages already on disk are skipped, so an interrupted download resumes.
    A `_complete` marker is written when the last (short) page has arrived.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    marker = out_dir / "_complete"
    if marker.exists():
        return sorted(out_dir.glob(f"page-*.{fmt}"))
    s = session()
    base = f"https://data.sf.gov/resource/{dataset}.{fmt}"
    page = 0
    while True:
        path = out_dir / f"page-{page:04d}.{fmt}"
        if path.exists():
            n = _count(path, fmt)
        else:
            params = {"$limit": page_size, "$offset": page * page_size, "$order": order}
            if select:
                params["$select"] = select
            if where:
                params["$where"] = where
            r = get_with_retry(s, base, params=params)
            tmp = path.with_suffix(".part")
            tmp.write_bytes(r.content)
            n = _count(tmp, fmt)
            tmp.rename(path)
            log(f"{dataset}: page {page} -> {n} rows")
        if n < page_size:
            break
        page += 1
    marker.write_text(time.strftime("%Y-%m-%dT%H:%M:%S"))
    return sorted(out_dir.glob(f"page-*.{fmt}"))


def _count(path: Path, fmt: str) -> int:
    data = json.loads(path.read_bytes())
    if fmt == "geojson":
        return len(data["features"])
    return len(data)


def download_file(url: str, path: Path) -> Path:
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    s = session()
    log(f"downloading {url}")
    r = get_with_retry(s, url, stream=False)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(r.content)
    tmp.rename(path)
    return path
