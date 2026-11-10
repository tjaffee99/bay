"""The map's extent: ten counties — the nine Bay Area counties and Santa Cruz (Sonoma, Napa,
Solano, Marin, Contra Costa, Alameda, San Francisco, San Mateo, Santa Clara, Santa Cruz).
The outline is the union of the TIGER 2024 county polygons (which include each county's
share of the bay and the ocean to the three-mile line), grown by 0.035 degrees and
simplified to 0.012 degrees, so the faded band lies mostly outside the county lines.
(Until 2026-11 the map was the core Bay Area only: EXTENT_CORE.)

Pipeline stages drop features outside it (with a margin: the viewer fades the map out
over the last few km inside the line, like the edge of an old game map); the viewer
reads viewer/public/data/map-extent.json (written by `python extent.py`).
"""
from __future__ import annotations

import json

import numpy as np
import shapely
from shapely.geometry import Polygon

from common import VIEWER_DATA

# the core Bay Area outline used before the ten-county extent; clockwise from Point Reyes; lon, lat
EXTENT_CORE = [
    (-123.06, 38.06), (-122.96, 38.19), (-122.76, 38.21), (-122.56, 38.17), (-122.45, 38.13),
    (-122.31, 38.075), (-122.2, 38.06), (-122.05, 38.045), (-121.97, 38.035), (-121.92, 37.97),
    (-121.86, 37.88), (-121.84, 37.8), (-121.56, 37.76), (-121.54, 37.62), (-121.64, 37.5),
    (-121.58, 37.38), (-121.62, 37.28), (-121.72, 37.19), (-121.85, 37.165), (-122.0, 37.12),
    (-122.15, 37.13), (-122.3, 37.08), (-122.46, 37.11), (-122.62, 37.55), (-122.66, 37.76),
    (-122.8, 37.86), (-123.1, 37.95),
]
# ten counties (see the docstring); lon, lat
EXTENT = [
    (-123.533, 38.653), (-123.666, 38.748), (-123.643, 38.792), (-123.403, 38.812), (-123.372, 38.841),
    (-123.171, 38.844), (-123.147, 38.873), (-123.026, 38.888), (-122.805, 38.883), (-122.724, 38.829),
    (-122.669, 38.743), (-122.632, 38.738), (-122.607, 38.711), (-122.484, 38.738), (-122.425, 38.828),
    (-122.435, 38.872), (-122.394, 38.899), (-122.260, 38.862), (-122.189, 38.726), (-122.104, 38.621),
    (-122.081, 38.550), (-122.016, 38.529), (-121.954, 38.566), (-121.888, 38.574), (-121.708, 38.573),
    (-121.674, 38.555), (-121.660, 38.530), (-121.659, 38.348), (-121.582, 38.346), (-121.559, 38.319),
    (-121.581, 38.184), (-121.657, 38.130), (-121.557, 38.121), (-121.524, 38.026), (-121.532, 37.891),
    (-121.499, 37.851), (-121.522, 37.803), (-121.522, 37.562), (-121.483, 37.555), (-121.444, 37.513),
    (-121.428, 37.430), (-121.379, 37.401), (-121.372, 37.301), (-121.419, 37.261), (-121.382, 37.213),
    (-121.269, 37.217), (-121.213, 37.183), (-121.186, 37.139), (-121.173, 37.060), (-121.199, 37.016),
    (-121.188, 36.939), (-121.419, 36.926), (-121.477, 36.943), (-121.567, 36.859), (-121.725, 36.875),
    (-121.805, 36.816), (-122.072, 36.791), (-122.106, 36.881), (-122.269, 36.956), (-122.328, 37.019),
    (-122.396, 37.037), (-122.495, 37.161), (-122.519, 37.248), (-122.502, 37.341), (-122.609, 37.493),
    (-122.619, 37.771), (-122.684, 37.811), (-122.776, 37.830), (-122.891, 37.933), (-122.976, 37.905),
    (-123.093, 37.934), (-123.120, 38.015), (-123.055, 38.142), (-123.079, 38.193), (-123.165, 38.278),
    (-123.194, 38.365), (-123.241, 38.412), (-123.384, 38.484),
]
POLY = Polygon(EXTENT)
MARGIN_DEG = 0.02  # keep features ~2 km beyond the line: they sit in the faded band


def in_extent(points, margin=MARGIN_DEG):
    """Boolean mask: (Geo)Series / array of shapely points (EPSG:4326) inside the extent."""
    poly = POLY.buffer(margin)
    shapely.prepare(poly)
    return shapely.contains(poly, np.asarray(getattr(points, "values", points)))


def write_viewer_extent():
    VIEWER_DATA.mkdir(parents=True, exist_ok=True)
    (VIEWER_DATA / "map-extent.json").write_text(json.dumps({"ring": [list(p) for p in EXTENT], "fade_km": 4.0}))


if __name__ == "__main__":
    write_viewer_extent()
    print("map-extent.json written", POLY.bounds)
