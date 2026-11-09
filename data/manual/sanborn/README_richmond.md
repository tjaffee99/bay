# Sanborn tracing: Richmond (downtown Macdonald Ave) — 1916

Real building footprints of downtown Richmond — Macdonald Ave between 4th and 13th St, from Barrett Ave to Chanslor Ave —
the pre-war city that the shipyard boom, the 1960s–70s redevelopment (Richmond BART, the downtown superblocks) and the
decline of Macdonald Ave replaced, on the Sanborn Map Co. *Insurance Maps of Richmond, California*, June 1916 (Library
of Congress, public domain: "Library of Congress, Geography and Map Division, Sanborn Maps Collection"). Schema as
`README_oakland.md`; tool `pipeline/sanborn_trace_eastbay_cities.py richmond …`, control in `control/richmond/`.

**Map years.** LOC has Richmond 1903 (7 sheets, mostly Point Richmond), 1905 (15), 1909 (25) and 1916 (40) online. The
1930 (`sanborn00787_005`, `_006`) and 1950 / 1951 (`_007`, `_008`) editions are catalogued but **not digitized**. The
1909 edition has a different sheet layout (no SIFT shortcut) and is not traced; 1916 is the only map year here.

## Files

| file | content |
|---|---|
| `richmond_downtown_1916.geojson` | sheets 20, 21 (north side: Barrett – Macdonald, 5th – 13th St, drawn with north to the left), 27, 28, 29 (south side: Macdonald – Chanslor, 4th – 13th St) |
| `richmond_downtown_coverage.geojson` | `map_year` 1916: the block zones (cells between street-crossing centres, i.e. blocks + half streets) |
| `control/richmond/<key>.json` | street-crossing control (`gridspec`), `with` (sheet fit), `residential`, `notes` |
| `control/richmond/labels.json`, `areas.json` | 12 labelled buildings (10 placed); sheets per area |

Properties as `README_oakland.md`. All five sheets `residential`; default-use buildings within 50 m of Macdonald Ave are
stores (`use_source = default (rule: commercial street frontage)`).

## Counts

| file | features | high / medium / low | area (1000 m²) | modern_overlap ≥ 0.5 | materials | named |
|---|---|---|---|---|---|---|
| richmond_downtown_1916 | 708 | 235 / 473 / 0 | 58.2 | 308 | frame 645, brick 50, stone 7, concrete 6 | 10 |

Uses: dwelling 401 → most of the Macdonald frontage store (92 by the frontage rule), shed 234, church 4, hall 2,
school 1 (Lincoln School), hotel 1 (Hotel Richmond). Coverage 50 ha.

## Sources

* Sanborn Map Company, *Insurance Maps of Richmond, California*, June 1916: https://www.loc.gov/item/sanborn00787_004/ —
  sheets 20, 21, 27, 28, 29 (index / key map sheet 1); 1909 https://www.loc.gov/item/sanborn00787_003/ (key map only).
  IIIF images at 25 % (1613 × 1913 px), item JSON in `data/raw/sanborn_loc_richmond/`.
* Control: Overture transportation segments 2026-10-21.0 (`roads_region` + `roads_local`, ODbL).

## Method (differences from Oakland)

* **Street-crossing control.** The 1916 scans are pale (block lines at grey 100–125, against 15–60 on the Berkeley
  scans), so the block-side snapping finds almost nothing, and the Contra Costa parcels (CCMAP) merge into a > 1 km²
  block west of 7th St, so property corners fail there. The plates draw the streets to scale, so the control is the
  centre of each street crossing, read as the midpoint of the gap between the drawn blocks (Macdonald Ave 100 ft,
  others ~60 ft), matched to the Overture centreline crossing; one similarity per sheet (all block zones `with` each
  other; a block whose own 4-crossing fit agrees keeps it). Only crossings that exist today count: 10th St is gone
  downtown, 10th / 12th / 14th–16th St no longer cross Nevin Ave (BART / transit village and the Nevin superblocks), and
  12th St is offset at Bissell. Sheet 22 (13th – 16th St with the Southern Pacific yard, Tilden Lumber, Enterprise
  Brewing) had only extended-line crossings (RMS 9 m) and was **dropped**.
* **Contrast stretch before extraction** (`enhance`: value (V − 90) × 255 / 155, saturation × 1.8 − 25), so the
  Oakland colour classes apply; the frame yellow is hue 21–22 on these plates, so the brown "fire-proof" re-class is
  off (`no_reclass`).

## Georeferencing per sheet

Residuals in metres between the transformed crossing pixel and the Overture crossing.

| sheet | ed. | block zones / fits | control crossings | RMS (m) per fit | scale (m/px), rotation |
|---|---|---|---|---|---|
| [004_0020](https://www.loc.gov/item/sanborn00787_004/) | 1916 | 8 zones, 1 fit(s) | 10 | 8 blocks: 1.9 | 0.1998, -89.56 deg |
| [004_0021](https://www.loc.gov/item/sanborn00787_004/) | 1916 | 4 zones, 1 fit(s) | 5 | 4 blocks: 2.88 | 0.1992, -90.08 deg |
| [004_0027](https://www.loc.gov/item/sanborn00787_004/) | 1916 | 6 zones, 3 fit(s) | 12 | 4th-5th/Macdonald-Bissell: 1.01; 4 blocks: 2.11; 5th-6th/Bissell-Chanslor: 1.25 | 0.2013, 0.43 deg; 0.204, 0.45 deg; 0.2064, 0.33 deg |
| [004_0028](https://www.loc.gov/item/sanborn00787_004/) | 1916 | 6 zones, 4 fit(s) | 8 | 7th-8th/Macdonald-Bissell+9th-10th/Macdonald-Bissell+9th-10th/Bissell-Chanslor: 0.61; 7th-8th/Bissell-Chanslor: 0.49; 8th-9th/Macdonald-Bissell: 0.24; 8th-9th/Bissell-Chanslor: 0.29 | 0.1997, 0.4 deg; 0.2007, 0.4 deg; 0.2007, 0.57 deg; 0.2014, 0.69 deg |
| [004_0029](https://www.loc.gov/item/sanborn00787_004/) | 1916 | 4 zones, 2 fit(s) | 6 | 11th-13th/Macdonald-Bissell+10th-11th/Macdonald-Bissell+10th-11th/Bissell-Chanslor: 1.92; 11th-13th/Bissell-Chanslor: 0.7 | 0.2046, 0.54 deg; 0.2064, 0.66 deg |

## Open items

* Not traced: Point Richmond (1916 sheets 2–8: the old town under the Standard Oil refinery hill, Washington Ave),
  sheets 19 / 26 (1st – 5th St), 22–24, 30–32 (east end, Santa Fe yard), 33–35 (the residential Iron Triangle south of
  Chanslor), 9–18 (north of Barrett), and the 1909 edition (different layout; each sheet needs its own control).
* One map year only (1930 / 1950 not online): ends come from today's buildings; the downtown redevelopment and BART
  clearances are **not** in `redevelopment_areas.csv` yet (candidates: Richmond Redevelopment Agency downtown projects
  of the 1960s–70s, BART 1969–73).
* Storeys not read; tracks not traced (the SP and Santa Fe lines are outside the traced blocks; the Macdonald Ave
  streetcar is street running).

## Reproduce

```
python pipeline/sanborn_trace_eastbay_cities.py richmond all
python pipeline/sanborn_trace_eastbay_cities.py richmond gridspec 004_0028 '{"cols": [[x, "7th"], ...], "rows": [[y, "Macdonald"], ...]}'
python pipeline/sanborn_trace_eastbay_cities.py richmond check
```
(after `gridspec`, sheets 21 / 29 add zones without own control by hand: see their control files).
