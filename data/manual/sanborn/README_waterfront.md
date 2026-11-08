# Sanborn tracing: Fisherman's Wharf and Mission Bay (waterfront)

Real historical building footprints for two areas that the modern data leaves empty before the 1970s (Fisherman's Wharf)
and 2000s (Mission Bay), traced from the Library of Congress scans of the Sanborn Map Co. *Insurance Maps of San
Francisco* (public domain). Built by `pipeline/sanborn_trace_waterfront.py` from the hand-measured control data in
`control/`. The Western Addition files in this folder come from a separate tool (`pipeline/sanborn_trace.py`) and are
not covered here.

## Files

| file | content |
|---|---|
| `fishermans_wharf_1899.geojson`, `_1913.geojson`, `_1950.geojson` | footprints (EPSG:4326), one feature per building / building group / wharf deck |
| `mission_bay_1913.geojson` (1913 vol. 2 + 1914 vol. 6 sheets), `mission_bay_1950.geojson` | same for Mission Bay / China Basin |
| `fishermans_wharf_coverage.geojson`, `mission_bay_coverage.geojson` | one polygon per map year: the ground the traced sheets cover (an empty area inside it really was empty on that map) |
| `control/<item>_<sheet>.json` | measured control: pixel positions of street crossings / block corners (IIIF `pct:25` image), street-line constraints, or the registration onto an older plate |
| `control/<item>_<sheet>.wharves.json` | seed points / clip polygons for wharf decks |
| `control/attributes.json` | storeys, use and names read off the sheets for 203 large or named footprints |

### Feature properties

| property | meaning |
|---|---|
| `map_year` | 1899, 1913, 1914 (vol. 6) or 1950. The 1950 volumes are the 1913/14 plates **corrected by paste-over slips up to 1950** (vol. 1 1913–1950, vol. 2 1913–Sep 1950, vol. 6 1914–Dec 1950). A feature says the building stood at the map date; it does not give its construction or demolition year. |
| `volume`, `volume_label`, `loc_url` | LOC item id (`sanborn00813_015` …), human label, item page |
| `sheet`, `sheet_no`, `iiif` | LOC image id (`00813_01_1913-0064`), sheet number, IIIF image service |
| `stories` | storeys; 0 for wharf decks |
| `stories_source` | `map (read from the sheet)` or `default (rule: material, size, district)` |
| `material` | frame (yellow) · brick (pink) · stone (blue, 1899/1913: "stone, concrete or concrete block") · concrete (blue in 1950 = reinforced concrete; brown "fire proof construction") · iron (grey, incl. corrugated iron and the steel train sheds) · unknown (1899 brown fills, see below) |
| `use` | dwelling · store · warehouse · shed · factory · cannery · rail · wharf · other (`use_source` says whether it was read from a label) |
| `name` | the map's label where read (e.g. "California Fruit Canners Ass'n North Point Cannery …", "Southern Pacific roundhouse") |
| `sanborn_colour` | raw colour class (frame / brick / stone / fireproof / iron / wharf) |
| `confidence` | high: georeference RMS ≤ 1.5 m and max ≤ 3 m with ≥ 4 control points; medium: ≥ 3 points and RMS ≤ 3 m; low: fewer points, a 2-point fit, wharf decks traced from a clip polygon, or 1899 brown fills |
| `georef`, `georef_rms_m` | `sheet` or `block <n>` (which transform placed it) and that fit's RMS (1950: combined with the registration RMS) |
| `area_m2` | footprint area |
| `modern_overlap` | share of the footprint covered by today's DataSF building footprints (2016). High values mark buildings that still stand (Haslett Warehouse 0.95, The Cannery 0.84, Ghirardelli 0.6–0.95, many Russian Hill houses) or a new building on the same lot; use it to avoid double geometry. |

## Counts

| file | features | confidence high / medium / low | wharf decks | storeys read | named | area (1000 m²) | modern_overlap ≥ 0.5 | materials |
|---|---|---|---|---|---|---|---|---|
| fishermans_wharf_1899 | 91 | 71/11/9 | 0 | 14 | 17 | 13.3 | 58 | frame 74, unknown 9, brick 8 |
| fishermans_wharf_1913 | 219 | 192/27/0 | 3 | 44 | 49 | 68.8 | 144 | frame 193, brick 20, stone 6 |
| fishermans_wharf_1950 | 288 | 256/30/2 | 3 | 58 | 62 | 90.1 | 220 | frame 229, brick 28, concrete 26, iron 5 |
| mission_bay_1913 (incl. 1914 vol. 6) | 176 | 146/5/25 | 0 | 38 | 41 | 97.6 | 45 | frame 161, brick 12, stone 3 |
| mission_bay_1950 | 169 | 123/12/34 | 0 | 32 | 35 | 68.2 | 41 | frame 134, concrete 19, iron 8, brick 8 |

A "feature" is one coloured fill of the map. Adjacent buildings of the same colour that share a wall are often one
feature (rows of flats, the SP freight sheds, the Ghirardelli and cannery blocks); the partition lines are kept where
the map draws them as long lines.

## Sources

Sanborn Map Company, *Insurance Maps of San Francisco, California*, Library of Congress Geography and Map Division,
Sanborn Maps Collection (public domain), item pages and IIIF images:

| edition | LOC item | sheets used |
|---|---|---|
| 1899 vol. 1 | https://www.loc.gov/item/sanborn00813_008/ | 74, 88, 93, 111 |
| 1913 vol. 1 | https://www.loc.gov/item/sanborn00813_015/ | 1, 51, 64, 65, 79, 80, 81, 96 |
| 1913 vol. 2 | https://www.loc.gov/item/sanborn00813_016/ | 152, 160, 168, 176, 217, 220 |
| 1914 vol. 6 | https://www.loc.gov/item/sanborn00813_020/ | 546, 560, 561 (upper / lower half only, see `valid_px`) |
| 1913–1950 vol. 1 | https://www.loc.gov/item/sanborn00813_030/ | same sheet numbers as 1913 vol. 1 |
| 1913–Sep 1950 vol. 2 | https://www.loc.gov/item/sanborn00813_031/ | same as 1913 vol. 2 |
| 1914–Dec 1950 vol. 6 | https://www.loc.gov/item/sanborn00813_035/ | same as 1914 vol. 6 |

Other SF editions on loc.gov: 1886–93 (items 002–007), 1899–1900 vols. 1–6 (008–013), 1913–15 vols. 1–10 (015–024),
1948/49 vols. 1–2 (028–029, earlier correction states of 030/031), 1950 vols. 1–9 (030–038). The 1928 vols. 10–11
(026–027) and 1950 vols. 10–11 (039–040) have no online images. Key maps: each volume's sheet `0000`/`0000a`.

Street geometry for control: DataSF street centrelines (`data/raw/sf_streets`, via `fire_1906.intersection()` and a
local straight-line fit of each centreline); block widths from the street widths printed on the sheets (68 ft 9 in for
the northern grid, 82 ft 6 in for SoMa, 125 ft Van Ness, 100 ft Kentucky/3rd, 66 ft Mariposa / 17th, 80 ft
Tennessee / Illinois where not printed: ESTIMATES).

## Method

1. **Download.** IIIF `pct:25` (about 1650 × 1950 px per sheet, 0.20 m/px at 50 ft to the inch) for tracing and
   `pct:50` for reading labels.
2. **Georeference, 1899 / 1913 / 1914 plates.** Similarity transform (scale, rotation, shift) per sheet or per block:
   * street crossings: the centre of the street corridor between the two drawn kerb/property lines (auto-refined
     on the long-line image, then stored as fixed pixel positions in `control/`), matched to the DataSF centreline node;
   * block corners: corner pixel of a drawn block outline matched to the centreline crossing offset by half of each
     street's width toward that quadrant (`bc`); vanished streets (Jefferson west of Hyde, Beach at Van Ness, 17th St
     east of Pennsylvania) are extrapolated along the surviving grid (`sum`, `bcs`), and labelled so in the residuals;
   * street-line constraints (Mission Bay south of the channel, where few crossings survive): pixel points that lie
     on a street centreline (3rd/Kentucky, 16th, Illinois, Mariposa, Tennessee), fitted with a scale prior of
     0.2025 ± 0.002 m/px taken from the neighbouring sheets.
   * **Finding: many Sanborn sheets are not to scale across the streets.** On the 2 × 2-block sheets (1913 sheets 51,
     65, 81, 96; 1899 sheet 88; 1914 sheets 546, 561) each block is drawn at 50 ft/in but the streets between them
     are drawn 2–3 × too wide (e.g. Jones St 310 px = 63 m instead of 21 m on 1913 sheet 65). A single sheet fit has
     15–17 m residuals there; those sheets are fitted **block by block** (4 corners each, residuals 0.1–1.5 m) and
     only footprints inside a block zone are kept (`zones_only`). The to-scale sheets (64, 79, 80, 1, the Mission Bay
     sheets north of the channel, 217, 1899 sheets 74/93/111) use one sheet transform.
3. **Georeference, 1950 sheets.** The 1950 volumes are the same engraved plates with paste-over corrections, so each
   1950 scan is registered onto its 1913/14 scan (SIFT features + RANSAC similarity, 480–2,300 inliers, 1.2–1.9 px =
   0.22–0.38 m RMS) and inherits the older sheet's control. Independent check: the 1913 street crossings re-measured
   on the 1950 scans land 1.2 m RMS from the DataSF crossings on sheet 64, 1.6 m on 168, 0.6 m (two-sided crossings)
   on 160; one-sided crossings (Townsend St, Jefferson St) re-measure worse (2–10 m) because paste-over slips hide
   one kerb, so they are a check on the measurement, not on the registration.
4. **Footprints.** Colour classes in HSV (thresholds relative to the paper colour of each scan): yellow frame, pink
   brick, blue stone/concrete, brown fire-proof, grey iron. Each class mask is closed over lettering and split along
   the long drawn lines (partition walls), holes < 2,500 px (lettering, light wells) are filled. Kept only if the
   outline is drawn: ≥ 78 % of the region's boundary within 3 px of a dark line, solidity ≥ 0.55 (or a clean
   outline), minimum width 9 px (1.8 m), area ≥ 120 px (≈ 5 m²). This rejects the water stains of the 1899 volume and
   the yellowed paste-over slips of the 1950 volumes. Vectorised with OpenCV contours, simplified 1 px (0.2 m),
   transformed to UTM 10N then WGS84. Overlaps between adjacent sheets are de-duplicated (> 50 % of the smaller
   polygon), keeping the better-georeferenced copy.
5. **Wharves.** Decks are uncoloured on the maps; they are flood-filled between the drawn outlines from seed points
   (1913 Fishermen's Wharf of 1900: north arm with its east leg, south arm along lot 5, the Taylor St wharf; 1950:
   the Wharf J7/J8 deck west of the lagoon, the Fishermen's Wharf J2/J4 "Fish Alley" deck and the diagonal wharf on
   the south side of the lagoon). Where railway tracks cross a deck (1950 J2/J4), the deck is the hand-drawn clip
   polygon itself (`confidence = low`).
6. **Storeys and use.** Read by eye from 50 % crops for every footprint ≥ 250–400 m² and for named buildings (203
   entries in `control/attributes.json`: the number in the building corner, the use label: "Ware Ho.", "Cannery",
   "Fish Packing", "Freight Shed", "2 Flats", "S" = store, "D" = dwelling …). Tesseract OCR was tried and gave
   nothing usable on these scans. Everything else gets a rule: frame < 30 m² shed (1); frame ≤ 300 m² on the
   residential sheets (65, 81, 96, 88, 546, 561) dwelling (2); frame ≥ 300 m² warehouse (1); brick / stone /
   concrete warehouse (2); iron shed (1) — `stories_source = default`.
7. **Checks.** Overlays of every footprint on its sheet (scratch), plots over DataSF centrelines and 2016 footprints:
   the surviving buildings traced from the maps (Haslett Warehouse, The Cannery, Ghirardelli's Mustard / Chocolate /
   Cocoa buildings, and on the 1950 sheet 152 the long Pacific Terminal building along Mission Creek, probably today's China Basin Building of 1922) fall on today's footprints
   (`modern_overlap` 0.84–0.98).

## Georeferencing per sheet

Control and residuals in metres (horizontal distance between the transformed pixel and the DataSF-derived position).
| sheet (LOC id) | ed. | method | control | residuals RMS / max | scale, rotation |
|---|---|---|---|---|---|
| **fishermans_wharf 1899** | | | | | |
| [00813_01_1899-0074](https://www.loc.gov/item/sanborn00813_008/) | 1899 v.1 | sheet similarity | 6 points (block corners) | 0.34/0.53 m | scale 0.2008 m/px, rot 99.47 deg |
| [00813_01_1899-0088](https://www.loc.gov/item/sanborn00813_008/) | 1899 v.1 | per-block similarity (streets drawn wider than true scale) | block 799: 4 corners; block 798: 4 corners; block 789: 4 corners; block 790: 3 corners | 799: 0.45/0.49 m; 798: 0.84/0.90 m; 789: 0.24/0.32 m; 790: 0.38/0.47 m | scale 0.1684 m/px, rot 99.54 deg |
| [00813_01_1899-0093](https://www.loc.gov/item/sanborn00813_008/) | 1899 v.1 | sheet similarity | 7 points (block corners) | 0.64/0.97 m | scale 0.2008 m/px, rot 99.52 deg |
| [00813_01_1899-0111](https://www.loc.gov/item/sanborn00813_008/) | 1899 v.1 | sheet + per-block similarity | block 810: 3 corners; block 809: 4 corners | 810: 0.60/0.73 m; 809: 0.91/1.01 m; whole sheet 0.90/1.31 m | scale 0.2019 m/px, rot 99.64 deg |
| **fishermans_wharf 1913** | | | | | |
| [00813_01_1913-0001](https://www.loc.gov/item/sanborn00813_015/) | 1913 v.1 | sheet similarity | 9 points (street crossings) | 0.40/0.56 m | scale 0.2024 m/px, rot 9.40 deg |
| [00813_01_1913-0051](https://www.loc.gov/item/sanborn00813_015/) | 1913 v.1 | per-block similarity (streets drawn wider than true scale) | block 31: 4 corners; block 30: 4 corners | 31: 0.23/0.30 m; 30: 0.40/0.56 m | scale 0.1756 m/px, rot -80.65 deg |
| [00813_01_1913-0064](https://www.loc.gov/item/sanborn00813_015/) | 1913 v.1 | sheet similarity | 6 points (street crossings) | 0.85/1.25 m | scale 0.2023 m/px, rot 9.04 deg |
| [00813_01_1913-0065](https://www.loc.gov/item/sanborn00813_015/) | 1913 v.1 | per-block similarity (streets drawn wider than true scale) | block 22: 4 corners; block 29: 4 corners; block 23: 4 corners; block 28: 3 corners | 22: 0.29/0.38 m; 29: 0.90/1.20 m; 23: 1.03/1.44 m; 28: 0.91/1.11 m | scale 0.1677 m/px, rot -80.74 deg |
| [00813_01_1913-0079](https://www.loc.gov/item/sanborn00813_015/) | 1913 v.1 | sheet similarity | 5 points (grid-extrapolated crossings, street crossings) | 0.80/1.19 m | scale 0.2024 m/px, rot 9.36 deg |
| [00813_01_1913-0080](https://www.loc.gov/item/sanborn00813_015/) | 1913 v.1 | sheet similarity | 5 points (street crossings) | 1.25/1.48 m | scale 0.2030 m/px, rot 9.45 deg |
| [00813_01_1913-0081](https://www.loc.gov/item/sanborn00813_015/) | 1913 v.1 | per-block similarity (streets drawn wider than true scale) | block 24: 3 corners; block 27: 4 corners; block 25: 4 corners; block 26: 4 corners | 24: 0.14/0.18 m; 27: 0.75/1.05 m; 25: 1.33/1.67 m; 26: 0.75/1.01 m | scale 0.1673 m/px, rot -80.04 deg |
| [00813_01_1913-0096](https://www.loc.gov/item/sanborn00813_015/) | 1913 v.1 | per-block similarity (streets drawn wider than true scale) | block 452: 4 corners; block 453: 4 corners; block 451: 3 corners; block 454: 4 corners | 452: 0.80/0.91 m; 453: 0.19/0.25 m; 451: 0.59/0.72 m; 454: 0.23/0.32 m | scale 0.1655 m/px, rot -80.57 deg |
| **fishermans_wharf 1950** | | | | | |
| [00813_01_1950-0001](https://www.loc.gov/item/sanborn00813_030/) | 1950 v.1 | registered onto 015_0001 | SIFT+RANSAC similarity on the shared base plate | registration 1.6 px = 0.32 m, plus the base sheet's | scale 0.2067 m/px, rot 8.66 deg |
| [00813_01_1950-0051](https://www.loc.gov/item/sanborn00813_030/) | 1950 v.1 | registered onto 015_0051 | SIFT+RANSAC similarity on the shared base plate | registration 1.4 px = 0.24 m, plus the base sheet's | scale 0.1765 m/px, rot -80.84 deg |
| [00813_01_1950-0064](https://www.loc.gov/item/sanborn00813_030/) | 1950 v.1 | registered onto 015_0064 | SIFT+RANSAC similarity on the shared base plate | registration 1.4 px = 0.29 m, plus the base sheet's | scale 0.2054 m/px, rot 9.50 deg |
| [00813_01_1950-0065](https://www.loc.gov/item/sanborn00813_030/) | 1950 v.1 | registered onto 015_0065 | SIFT+RANSAC similarity on the shared base plate | registration 1.3 px = 0.22 m, plus the base sheet's | scale 0.1689 m/px, rot -80.92 deg |
| [00813_01_1950-0079](https://www.loc.gov/item/sanborn00813_030/) | 1950 v.1 | registered onto 015_0079 | SIFT+RANSAC similarity on the shared base plate | registration 1.3 px = 0.26 m, plus the base sheet's | scale 0.2034 m/px, rot 9.25 deg |
| [00813_01_1950-0080](https://www.loc.gov/item/sanborn00813_030/) | 1950 v.1 | registered onto 015_0080 | SIFT+RANSAC similarity on the shared base plate | registration 1.3 px = 0.27 m, plus the base sheet's | scale 0.2037 m/px, rot 9.47 deg |
| [00813_01_1950-0081](https://www.loc.gov/item/sanborn00813_030/) | 1950 v.1 | registered onto 015_0081 | SIFT+RANSAC similarity on the shared base plate | registration 1.4 px = 0.23 m, plus the base sheet's | scale 0.1691 m/px, rot -80.40 deg |
| [00813_01_1950-0096](https://www.loc.gov/item/sanborn00813_030/) | 1950 v.1 | registered onto 015_0096 | SIFT+RANSAC similarity on the shared base plate | registration 1.6 px = 0.27 m, plus the base sheet's | scale 0.1679 m/px, rot -80.51 deg |
| **mission_bay 1913** | | | | | |
| [00813_02_1913-0152](https://www.loc.gov/item/sanborn00813_016/) | 1913 v.2 | sheet similarity | 4 points (street crossings) | 0.47/0.59 m | scale 0.2025 m/px, rot -44.80 deg |
| [00813_02_1913-0160](https://www.loc.gov/item/sanborn00813_016/) | 1913 v.2 | sheet similarity | 4 points (street crossings) | 0.65/0.90 m | scale 0.2017 m/px, rot -45.12 deg |
| [00813_02_1913-0168](https://www.loc.gov/item/sanborn00813_016/) | 1913 v.2 | sheet similarity | 4 points (street crossings) | 1.20/1.68 m | scale 0.2010 m/px, rot -44.74 deg |
| [00813_02_1913-0176](https://www.loc.gov/item/sanborn00813_016/) | 1913 v.2 | sheet similarity | 4 points (street crossings) | 0.75/1.04 m | scale 0.2021 m/px, rot -44.71 deg |
| [00813_02_1913-0217](https://www.loc.gov/item/sanborn00813_016/) | 1913 v.2 | sheet similarity + street-line constraints + scale prior | 0 points () + 6 points on 3 street centrelines + scale prior | 0.30/0.47 m | scale 0.2034 m/px, rot 4.88 deg |
| [00813_02_1913-0220](https://www.loc.gov/item/sanborn00813_016/) | 1913 v.2 | sheet similarity | 2 points (block corners) + scale prior | 1.14/1.14 m | scale 0.2049 m/px, rot 45.89 deg |
| [00813_06_1914-0546](https://www.loc.gov/item/sanborn00813_020/) | 1914 v.6 | per-block similarity (streets drawn wider than true scale) | block 3942: 4 corners; block 3943: 2 corners | 3942: 2.22/2.26 m; 3943: 0.00/0.00 m | scale 0.1841 m/px, rot 4.48 deg |
| [00813_06_1914-0560](https://www.loc.gov/item/sanborn00813_020/) | 1914 v.6 | sheet similarity + street-line constraints + scale prior | 1 points (block corners) + 4 points on 2 street centrelines + scale prior | 0.07/0.10 m | scale 0.2025 m/px, rot 4.78 deg |
| [00813_06_1914-0561](https://www.loc.gov/item/sanborn00813_020/) | 1914 v.6 | per-block similarity (streets drawn wider than true scale) | block 3992: 2 corners; block 3993: 3 corners | 3992: 0.00/0.00 m; 3993: 2.36/2.89 m | scale 0.1704 m/px, rot 1.60 deg |
| **mission_bay 1950** | | | | | |
| [00813_02_1950-0152](https://www.loc.gov/item/sanborn00813_031/) | 1950 v.2 | registered onto 016_0152 | SIFT+RANSAC similarity on the shared base plate | registration 1.5 px = 0.31 m, plus the base sheet's | scale 0.2013 m/px, rot -44.78 deg |
| [00813_02_1950-0160](https://www.loc.gov/item/sanborn00813_031/) | 1950 v.2 | registered onto 016_0160 | SIFT+RANSAC similarity on the shared base plate | registration 1.3 px = 0.26 m, plus the base sheet's | scale 0.2000 m/px, rot -45.00 deg |
| [00813_02_1950-0168](https://www.loc.gov/item/sanborn00813_031/) | 1950 v.2 | registered onto 016_0168 | SIFT+RANSAC similarity on the shared base plate | registration 1.9 px = 0.38 m, plus the base sheet's | scale 0.2003 m/px, rot -44.49 deg |
| [00813_02_1950-0176](https://www.loc.gov/item/sanborn00813_031/) | 1950 v.2 | registered onto 016_0176 | SIFT+RANSAC similarity on the shared base plate | registration 1.2 px = 0.24 m, plus the base sheet's | scale 0.2018 m/px, rot -44.95 deg |
| [00813_02_1950-0217](https://www.loc.gov/item/sanborn00813_031/) | 1950 v.2 | registered onto 016_0217 | SIFT+RANSAC similarity on the shared base plate | registration 1.8 px = 0.37 m, plus the base sheet's | scale 0.2025 m/px, rot 5.27 deg |
| [00813_02_1950-0220](https://www.loc.gov/item/sanborn00813_031/) | 1950 v.2 | registered onto 016_0220 | SIFT+RANSAC similarity on the shared base plate | registration 1.6 px = 0.33 m, plus the base sheet's | scale 0.2041 m/px, rot 45.60 deg |
| [00813_06_1950-0546](https://www.loc.gov/item/sanborn00813_035/) | 1950 v.6 | registered onto 020_0546 | SIFT+RANSAC similarity on the shared base plate | registration 1.4 px = 0.26 m, plus the base sheet's | scale 0.1795 m/px, rot 4.88 deg |
| [00813_06_1950-0560](https://www.loc.gov/item/sanborn00813_035/) | 1950 v.6 | registered onto 020_0560 | SIFT+RANSAC similarity on the shared base plate | registration 1.4 px = 0.28 m, plus the base sheet's | scale 0.1979 m/px, rot 5.32 deg |
| [00813_06_1950-0561](https://www.loc.gov/item/sanborn00813_035/) | 1950 v.6 | registered onto 020_0561 | SIFT+RANSAC similarity on the shared base plate | registration 1.5 px = 0.25 m, plus the base sheet's | scale 0.1680 m/px, rot 1.25 deg |

Scale = metres per pixel of the 25 % image; rotation = angle of the image x-axis (counter-clockwise from east). For the
block-wise sheets the "scale" of the whole-sheet fit is meaningless (streets drawn wide) and only the block fits are
used. 2-corner blocks (1914 sheet 546 block 3943, sheet 561 block 3992) have no redundancy: their footprints are
`confidence = low`. 1913 sheet 220 has only two block corners (block 3840, on the DataSF paper-street stubs of
Merrimac and Alameda St) plus the scale prior: `low`.

## Coverage

* **Fisherman's Wharf**: Van Ness Ave to Powell St, Bay St to the water (1913, 1950: sheets 79, 96, 80, 81, 64, 65, 1,
  51 — sheet 51 only for the two blocks north of Bay St); 1899: Van Ness to Taylor, Bay St to the water (sheets 111,
  88, 93, 74; north of Beach St west of Taylor the 1899 sheets are mostly open water). The 1913 maps show the
  lagoon, the 1900 Fishermen's Wharf, lumber yards, the PG&E North Beach gas works, the CFCA North Point cannery and
  warehouses, Ghirardelli, the Musto marble works, rowing clubs and the Russian Hill flats; the 1950 maps add Fish
  Alley, the fish-packing and boat-building sheds, the Standard Oil distributing plant, Galileo High School's gym, etc.
* **Mission Bay**: Townsend St to the Mission Creek channel, 3rd to 7th St (sheets 152, 160, 168, 176: SP depot and
  train sheds, SP freight sheds, lumber yards, hay warehouses, planing mills); south of the channel only Kentucky
  (3rd) St to Illinois St between the channel and 16th (sheet 217, 220) and 16th St to Mariposa around 3rd St
  (1914 vol. 6 sheets 546 lower half, 560 upper half with the SP roundhouse and shops, 561 upper half).

## Not done / next steps

* **Mission Bay south of the channel between 4th and 7th St** (1913 vol. 2 sheets 215, 216, 219) and the Santa Fe /
  China Basin terminal east of 3rd (221, 222, 223): too few surviving streets for control (only the channel, the
  diagonal 4th St extension and Kentucky St). They can be done with street-line constraints (4th St between Berry
  and Channel St continues the 1913 line) and ties to sheets 217/220, or from the 1938 Harrison Ryker aerial mosaic.
  1914 vol. 6 sheets 545, 559 (Pennsylvania – Mississippi) and the upper half of 546 were not traced either.
* **1899 Mission Bay** (1899 vol. 2 / 1900 vol. 5 sheets) and **1899 Fisherman's Wharf east of Taylor** (sheets 59,
  60, 90, 91) not traced.
* **Produce Market** (Golden Gateway) and **Yerba Buena Center** blocks: not started (1913 vol. 1 / vol. 2 sheets;
  the method and the registration of the 1950 plates apply unchanged).
* **Wharves and piers** other than the Fishermen's Wharf decks (Pier 45 is standing; Hyde St and Municipal Pier
  stand) and the Pier 47 / Wharf fingers on the 1950 sheet 64 were not traced; the 1950 sheet 112 (Pier 45) was not
  georeferenced.
* **Colour classes**: the 1899 scan's water stains and the 1950 paste-over slips are rejected by the outline test,
  which also drops some real buildings with faint outlines; grey (iron) buildings on 1950 sheets are found only when
  solid and well outlined. The dark ochre 1899 fills (Ghirardelli / Pioneer Woolen Mill complex on sheet 111) come
  out as `material = unknown`. Partition walls drawn as short lines are not split, so rows of houses are often one
  feature with the row's dominant storeys.
* **Storeys** are read only for the large / named buildings; the other ~740 features use the rule above.
* Feature-level years: a feature only says "standing in `map_year`". Combine the editions (1899 → 1913 → 1950 →
  today via `modern_overlap`) to bound start and end years; the documented ones are in `data/tables/notable_demolished.csv`.

## Rows added to `data/tables/notable_demolished.csv`

`sp_third_townsend_station_1889`, `sp_freight_sheds_king_4th_5th`, `sp_freight_sheds_king_5th_6th`,
`sp_mission_bay_roundhouse`, `spring_valley_black_point_pumping_station`, `equitable_gaslight_hyde_st_works` — each
points to the traced footprint ids in these files; prefer the traced geometry over a box. Most start / end years are
ESTIMATES (said so per row); the 1975–76 depot demolition and the CFCA cannery (standing) were already known.

## Reproduce

```
python pipeline/sanborn_trace_waterfront.py all          # downloads to data/raw/sanborn_loc, fits to data/interim/sanborn_waterfront
python pipeline/sanborn_trace_waterfront.py register 030_0064 015_0064   # redo one SIFT registration (writes control/)
```
The control files hold the final pixel positions (`norefine`), so a rerun reproduces these outputs exactly. For a new
sheet, write approximate pixels (±20 px on the 25 % image) without `norefine`: crossings are then refined to the
centre between the two kerb lines (`refine_crossing`, optional `wv`/`wh` street widths in ft, `sides` for one-sided
streets) and block corners to the nearest block lines (`refine_corner`). Check the residuals it logs: a 15 m sheet
residual with sub-metre block residuals means the sheet draws its streets wider than scale (use `blocks` +
`zones_only`).
