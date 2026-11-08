"""The map's extent: the core Bay Area (Marin, San Francisco, San Mateo, Santa Clara
Valley to Coyote, Alameda incl. the Livermore Valley, Contra Costa west of Pittsburg).
Santa Cruz, south Santa Clara County (Morgan Hill, Gilroy), the Central Valley, Napa,
Sonoma, Solano and north-east Contra Costa (Pittsburg, Antioch) are left out for now.

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

# clockwise from Point Reyes; lon, lat
EXTENT = [
    (-123.06, 38.06), (-122.96, 38.19), (-122.76, 38.21), (-122.56, 38.17), (-122.45, 38.13),
    (-122.31, 38.075), (-122.2, 38.06), (-122.05, 38.045), (-121.97, 38.035), (-121.92, 37.97),
    (-121.86, 37.88), (-121.84, 37.8), (-121.56, 37.76), (-121.54, 37.62), (-121.64, 37.5),
    (-121.58, 37.38), (-121.62, 37.28), (-121.72, 37.19), (-121.85, 37.165), (-122.0, 37.12),
    (-122.15, 37.13), (-122.3, 37.08), (-122.46, 37.11), (-122.62, 37.55), (-122.66, 37.76),
    (-122.8, 37.86), (-123.1, 37.95),
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
