# Sanborn tracing: Alameda (West End) — 1897 and 1948

Real building footprints of Alameda's West End — 3rd St (formerly Davenport) to Webster St, Pacific Ave to the old
south shore — on two editions of the Sanborn Map Co. *Insurance Maps of Alameda, California* (Library of Congress,
public domain: "Library of Congress, Geography and Map Division, Sanborn Maps Collection"): **1897** and **1948** (the
"New Report, September 1941" corrected to 1948). Method and schema as `README_oakland.md`; tool
`pipeline/sanborn_trace_eastbay_cities.py alameda …`, control in `control/alameda/`.

**The two editions share plates.** The 1941 "new report" kept the 1897 sheet layout and engraved block outlines (with
renamed streets and paste-over changes), so every 1897 sheet registers onto its 1948 sheet by SIFT + RANSAC similarity
(91–1,057 inliers, 0.9–1.7 px ≈ 0.2–0.35 m; the waterfront tool's `register`). Only the 1948 sheets carry block
control; the 1897 sheets inherit it. The 1950 item (`sanborn00374_003`) is the same 1941 plates corrected to 1950 and
would register the same way — **not used** (two years after 1948; its paste-over slips risk false demolitions).

**Not duplicated.** The west-end bath houses, Neptune Beach / Gardens and the Terrace Baths were traced from the same
1897 / 1948 sheets (11, 12, 15) by the vanished-sites work (`data/manual/vanished_sites/`, `traced/alameda_baths_sanborn.json`):
any footprint here that lies on one of their buildings (> 30 % of its area within 3 m) is removed at assembly
(33 on 1897, 40 on 1948; `drop_vanished_sites`).

## Files

| file | content |
|---|---|
| `alameda_westend_1897.geojson` | footprints on the 1897 sheets 4, 9, 10, 11, 12, 14, 15 |
| `alameda_westend_1948.geojson` | the same sheets in the 1941 report corrected to 1948 |
| `alameda_westend_coverage.geojson` | one polygon per map year (1897, 1948): fitted block zones + half the streets |
| `control/alameda/<key>.json` | 1948 sheets: block control as for Oakland; 1897 sheets: `registered_to`, `T`, inliers, RMS |
| `control/alameda/labels.json`, `areas.json` | 2 labelled buildings (Longfellow School, St. Barnabas Church); sheets per area |

Keys: `001_0009` = `sanborn00374_001` (1897) sheet 9; `002_0009` = `sanborn00374_002` (1948) sheet 9.

Properties as `README_oakland.md`. All sheets `residential` (frame ≤ 300 m² dwelling 2 storeys); default-use buildings
within 40 m of Webster St or Park St are stores (`use_source = default (rule: commercial street frontage)`). Blue on the
1948 sheets is recorded as `stone` (the Oakland tool calls blue `concrete` only from 1950).

## Counts

| file | features | high / medium / low | area (1000 m²) | modern_overlap ≥ 0.5 | materials |
|---|---|---|---|---|---|
| alameda_westend_1897 | 693 | 302 / 391 / 0 | 36.0 | 394 | frame 690, stone 2, brick 1 |
| alameda_westend_1948 | 1624 | 732 / 891 / 1 | 115.4 | 1217 | frame 1581, brick 36, stone 7 |

Coverage 65 ha per map year. The West End filled in between the maps (sheet 9: 37 buildings in 1897, 303 in 1948), and
most of the 1948 fabric still stands (1,217 of 1,624 footprints are ≥ 50 % covered by today's buildings — `apply_sanborn`
leaves those to the modern data); what the maps add is the 1897 → 1948 build-out dates and the houses, sheds and
shore buildings that are gone.

## Sources

Sanborn Map Company, *Insurance Maps of Alameda, California*, Library of Congress (public domain), IIIF images at 25 %
(≈ 1650 × 1980 px, ≈ 0.2015 m/px at 50 ft = 1 in), item JSON in `data/raw/sanborn_loc_alameda/`:

| edition | LOC item | sheets used |
|---|---|---|
| 1897 | https://www.loc.gov/item/sanborn00374_001/ | 4, 9, 10, 11, 12, 14, 15 (key map `0000L`) |
| 1941 report corrected to 1948 | https://www.loc.gov/item/sanborn00374_002/ | 4, 9, 10, 11, 12, 14, 15 (key map `0000a`) |
| 1941 report corrected to 1950 | https://www.loc.gov/item/sanborn00374_003/ | not used |

Control: Overture transportation segments 2026-10-21.0 (`roads_region` + `roads_local`, ODbL) and Alameda County parcels
2021 (public copy) dissolved into blocks. The 1897 sheets already print "Fourth St. formerly West End Ave" / "Fifth St.
formerly Second Ave": the LOC record gives no correction date, so the 1897 date is taken as printed (the street
renaming may be a paste-over; `map_year` could be a few years late for some features).

## Georeferencing per sheet

| sheet | ed. | block zones / fits | control corners | RMS (m) per fit | scale (m/px), rotation |
|---|---|---|---|---|---|
| 001_0004 | 1897 | registered onto 002_0004 (SIFT, 506 inliers) | — | 1.39 px = 0.27 m | scale 0.1965 m/px, rot 88.38 deg |
| 001_0009 | 1897 | registered onto 002_0009 (SIFT, 776 inliers) | — | 1.47 px = 0.29 m | scale 0.1966 m/px, rot -1.25 deg |
| 001_0010 | 1897 | registered onto 002_0010 (SIFT, 723 inliers) | — | 1.49 px = 0.29 m | scale 0.1979 m/px, rot -1.38 deg |
| 001_0011 | 1897 | registered onto 002_0011 (SIFT, 706 inliers) | — | 1.21 px = 0.24 m | scale 0.1974 m/px, rot -0.71 deg |
| 001_0012 | 1897 | registered onto 002_0012 (SIFT, 1057 inliers) | — | 1.48 px = 0.29 m | scale 0.1974 m/px, rot -1.05 deg |
| 001_0014 | 1897 | registered onto 002_0014 (SIFT, 677 inliers) | — | 1.27 px = 0.25 m | scale 0.1970 m/px, rot -1.25 deg |
| 001_0015 | 1897 | registered onto 002_0015 (SIFT, 799 inliers) | — | 1.69 px = 0.33 m | scale 0.1982 m/px, rot -1.67 deg |
| [002_0004](https://www.loc.gov/item/sanborn00374_002/) | 1948 | 4 zones, 1 fit(s) | 3 | 4 blocks: 2.13 | 0.2011, 88.26 deg |
| [002_0009](https://www.loc.gov/item/sanborn00374_002/) | 1948 | 3 zones, 3 fit(s) | 9 | 459: 0.73; 461: 0.75; 460_384: 1.22 | 0.2008, -1.03 deg; 0.2008, -1.08 deg; 0.2017, -1.24 deg |
| [002_0010](https://www.loc.gov/item/sanborn00374_002/) | 1948 | 3 zones, 3 fit(s) | 10 | 381: 0.42; 383_382: 0.4; 380_378: 0.32 | 0.202, -1.37 deg; 0.2022, -1.37 deg; 0.2032, -1.48 deg |
| [002_0011](https://www.loc.gov/item/sanborn00374_002/) | 1948 | 3 zones, 2 fit(s) | 7 | 425: 1.16; 426+427: 2.21 | 0.2022, -1.15 deg; 0.2025, -0.7 deg |
| [002_0012](https://www.loc.gov/item/sanborn00374_002/) | 1948 | 3 zones, 2 fit(s) | 6 | 464_465: 2.98; 462_463_429+428: 2.99 | 0.2017, -1.04 deg; 0.2036, -0.94 deg |
| [002_0014](https://www.loc.gov/item/sanborn00374_002/) | 1948 | 3 zones, 3 fit(s) | 12 | 374: 0.9; 373: 0.44; 466: 0.85 | 0.2012, -1.4 deg; 0.2014, -1.63 deg; 0.2032, -1.44 deg |
| [002_0015](https://www.loc.gov/item/sanborn00374_002/) | 1948 | 3 zones, 2 fit(s) | 7 | 430: 0.28; 431+neptune_court: 1.62 | 0.2029, -1.95 deg; 0.2045, -1.57 deg |

**Findings.** Today's **4th St west property line lies ~4.5 m west of the line the sheets draw** (12.3 m from the
centreline vs 7.9 m on the east side, where sheet 9 fits to 0.8 m): sheet 4 (3rd – 4th St, drawn with north to the
right) is fitted on its 3rd St corners only, with the plate-scale prior (RMS 2.1 m, collinear → medium); the curving
Lincoln / Santa Clara Ave blocks west of 3rd St (393–396, 410) take that fit. Pacific Ave's south line has moved at
4th – 5th St (block 459, crossed by the railroad: Pacific corners 7–8 m off; fitted on its Lincoln corners with 461).
Taylor Ave's parcels reach its centreline in places (implausible offsets) and the land south of Central Ave is the
1950s South Shore fill (no property corners): the shore blocks 427 / 428 / Neptune Court take the fit of the block
north of Central.

## Open items

* Not traced: sheets 1–3, 5–8, 13 (west of 3rd St and north of Pacific: J. H. Baxter & Co. pole yard, N. Clark & Sons
  terra-cotta works, the Atlantic trailer park federal housing, the estuary shipyards on 93 / 8 / 35), downtown Park St
  (sheets ~33, 38, 40) and the east end.
* The 1950 corrected state (registration is ready: `register 003_xxxx 002_xxxx`).
* Storeys not read; tracks not traced (the SP Lincoln Ave / Pacific Ave lines are street running).

## Reproduce

```
python pipeline/sanborn_trace_eastbay_cities.py alameda all
python pipeline/sanborn_trace_eastbay_cities.py alameda register 001_0009 002_0009   # redo one SIFT registration
python pipeline/sanborn_trace_eastbay_cities.py alameda check
```
