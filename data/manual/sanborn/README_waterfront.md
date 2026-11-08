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

* (DONE, see *Extension 2026-11* at the end; the Counts table above is superseded for Mission Bay there.) **Mission Bay south of the channel between 4th and 7th St** (1913 vol. 2 sheets 215, 216, 219) and the Santa Fe /
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

## Extension 2026-11: Mission Bay south of the channel, Potrero Point, rail-yard tracks

New area `potrero_point` (Potrero Point, Central Basin, Dogpatch), the rest of `mission_bay`, and railway track
centrelines for both. Same tool, same schema; everything traced before is kept (exceptions below).

### Files

| file | features | confidence high / medium / low | storeys read | named | area (1000 m²) | modern_overlap ≥ 0.5 | materials |
|---|---|---|---|---|---|---|---|
| mission_bay_1913 (1913 vol. 2 + 1914 vol. 6) | 363 | 314/24/25 | 38 | 50 | 158.4 | 129 | frame 327, brick 21, iron 10, stone 5 |
| mission_bay_1950 | 427 | 330/64/33 | 28 | 33 | 133.3 | 144 | frame 354, concrete 40, brick 18, iron 15 |
| potrero_point_1914 (1914 vol. 6) | 635 | 351/284/0 | 1 | 49 | 204.2 | 333 | frame 533, iron 50, brick 44, stone 8 |
| potrero_point_1950 (1914-Dec 1950 vol. 6) | 660 | 359/301/0 | 1 | 32 | 160.8 | 373 | frame 526, brick 68, concrete 49, iron 17 |

| track file | lines | km | km by confidence high / medium / low | km yard / spur / main | km by railroad (map label) |
|---|---|---|---|---|---|
| mission_bay_1913_tracks | 1256 | 57.9 | 42.4 / 10.5 / 5.0 | 43.7 / 14.1 / 0 | SP 24.1, AT&SF 3.3, not labelled 30.4 |
| mission_bay_1950_tracks | 1468 | 62.4 | 48.0 / 10.6 / 3.8 | 47.8 / 14.7 / 0 | SP 21.8, AT&SF 3.4, not labelled 37.3 |
| potrero_point_1914_tracks | 378 | 13.3 | 8.6 / 2.7 / 1.9 | 4.2 / 9.1 / 0 | not labelled 13.3 |
| potrero_point_1950_tracks | 404 | 12.7 | 8.1 / 2.7 / 1.9 | 4.1 / 8.5 / 0 | not labelled 12.7 |

`<area>_coverage.geojson` has one polygon per map year (mission_bay 1913 / 1950: 21 sheet parts each; potrero_point
1914 / 1950: 16). For these two areas the coverage of a block-wise sheet is the hull of its blocks **including the
streets between them** (also empty of buildings on the map; the tracks laid in those streets are traced). Inside the
coverage an empty area is empty on that map, for buildings and for tracks.

Track properties: `id`, `map_year`, `volume`, `volume_label`, `sheet`, `sheet_no`, `loc_url`, `iiif`, `railroad`
(only where the sheet names it: "Southern Pacific R.R. Freight Tracks / Freight Yard / Car Repairing Tracks" on
sheets 216, 217, 219, 220, the SP roundhouse sheet 560, "Atchison, Topeka & Santa Fe Railway Yards" on 221 / 222;
`null` elsewhere), `railroad_source`, `kind` (`yard` = at least two parallel tracks 3-15 m to either side along most
of the line, else `spur`; `main` only from a hand polygon `main_px` in `control/<key>.tracks.json`, none drawn yet),
`kind_source`, `confidence` (the sheet / block fit, one level lower on a block-wise sheet when > 40 % of the line runs
in the streets between the fitted blocks), `georef` (`sheet` or `blocks (rubber sheet)`), `georef_rms_m`, `length_m`.

### Sheets (Library of Congress, public domain)

| edition | LOC item | sheets added |
|---|---|---|
| 1913 vol. 2 | https://www.loc.gov/item/sanborn00813_016/ | 215, 216, 217 (rotated part, key `016_0217r`), 219, 221, 222, 223 |
| 1914 vol. 6 | https://www.loc.gov/item/sanborn00813_020/ | 545 (upper `020_0545`, lower `020_0545b`), 546 upper (`020_0546u`), 547, 559 (mission_bay); 560 lower (`020_0560b`), 561 lower (`020_0561b`), 562, 574, 575, 589, 590, 591, 592, 593, 594, 607, 608, 609, 610, 626 (potrero_point) |
| 1913-Sep 1950 vol. 2 | https://www.loc.gov/item/sanborn00813_031/ | same sheets as 1913 vol. 2 |
| 1914-Dec 1950 vol. 6 | https://www.loc.gov/item/sanborn00813_035/ | same sheets as 1914 vol. 6 |

A key with a letter after the sheet number (`020_0545b`) is another part of the same scan with its own fit
(`valid_px` / `valid_poly_px` say which part). 1899: Potrero Point was not looked for in the 1899-1900 volumes
(items 009-013) - open.

### Georeferencing (new control types in `pipeline/sanborn_trace_waterfront.py`)

* **Retired DataSF centrelines** (`active = false`) are used: the 1860s Mission Bay grid survives only there (old
  diagonal 4th St cnn 272000-274000, 6th St 345000-348000, Illinois / Merrimac / Alameda / El Dorado east of 3rd St).
  `cnn` in a line constraint restricts the fit to given segments (old diagonal 4th St, not today's 4th St beside it).
* **Line crossings** (`la` / `lb`): crossing of two fitted centrelines, each extended across vanished blocks
  (Hooper / Irwin / Hubbell St survive only south-west of 7th St; their 1913 crossings with 6th St are their lines
  extended), with an optional kerb offset (`off: [[ft, side], [ft, side]]`) for block corners on the straight grid.
* **Kerb lines**: `off: [ft, side]` on a street-line constraint (points on a drawn kerb, not the centre).
* **Sheet ties** (`tie`): a drawn feature shared with an already fitted neighbour sheet (hydrant corner, pier-head
  corner, building corner, match-line); SIFT matches between neighbouring sheets were used only after checking them
  by eye (identical lettering, compass roses, scale bars and the scan rulers match falsely and were rejected).
  The neighbour's RMS is added to the sheet's (`tie_rms`).
* **Finding: sheet 217 is drawn in two orientations.** North-west of the heavy line (Kentucky St east kerb) the sheet
  is rotated 45 deg with its own compass rose. The earlier pass fitted the whole sheet north-up, so the Mission Bay
  warehouses No. 1 / No. 2 and three small features (`016_0217_f68/f79/f87/f153/f164` and `031_0217_*` north-west of
  the line) were misplaced; they now come from `016_0217r` / `031_0217r` (`016_0217r_f68`, `_f153`; attributes copied).
* **Finding: the street on the left of sheets 215 / 219 is 6th St** (labelled), not 7th St.
* Iron (grey) fills of the 1914 vol. 6 sheets: paper hue and saturation, 14+ darker than the paper
  (`iron_rule: dark_grey`); paler blue on 1950 paste-over slips: `stone_low_sat`. Both opt-in per control file.
* Missed rectangles (grey U.S. Steel Products warehouses with truss lines drawn inside, 1914 sheet 594; the 1950
  shipyard buildings on paste-over slips, sheet 592): `trace: rect` in `<key>.wharves.json`, a hand rectangle whose
  corners are snapped to the drawn outline; confidence at most `medium`.

| key | method | control | RMS / max (m) | scale, rotation |
|---|---|---|---|---|
| 016_0215 | sheet | 6th St x Hooper / Irwin / Hubbell (extended), 6th St NE kerb | 0.21 / 0.33 | 0.2032, 45.07 |
| 016_0216 | sheet, **capped medium** | old 4th St centreline, Kentucky St kerbs (scale from the prior) | 0.23 / 0.47 | 0.2025, 45.27 |
| 016_0217r | sheet | 4th St NE kerb, Kentucky St E kerb, tie 216 | 0.33 / 0.60 (+0.23 tie) | 0.2025, 45.09 |
| 016_0219 | sheet | 6th St kerbs, 2 ties 215 (a 3rd at 7.7 m dropped) | 0.20 / 0.38 (+0.21) | 0.2031, 44.85 |
| 016_0221 | sheet | Kentucky St centreline, 3 ties 217 | 0.41 / 0.51 (+0.30) | 0.2024, 4.94 |
| 016_0222 | sheet, **capped medium** | 2 hydrant-corner ties 223, Merrimac kerbs, 4th St label | 1.30 / 2.94 (+0.23) | 0.2037, 19.54 |
| 016_0223 | sheet | Merrimac / Alameda x Illinois, Illinois, El Dorado N kerb | 0.23 / 0.43 | 0.2019, -85.17 |
| 020_0545 | 2 blocks | corners on the straight 16th / 17th / Texas / Mississippi / Pennsylvania lines | 0.48, 0.67 / 0.86 | |
| 020_0545b | sheet | 4 Pennsylvania Ave corners | 0.22 / 0.31 | 0.2060, 4.47 |
| 020_0546u | sheet | 3 ties 560 (17th St), 16th St S kerb | 1.03 / 1.32 | 0.2058, 4.67 |
| 020_0547 | sheet | Illinois x 16th, Illinois x 17th (grid), 16th St | 0.14 / 0.22 | 0.2048, 4.54 |
| 020_0559 | 6 blocks | straight-grid corners | 0.19-0.67 / 0.78 | |
| 020_0560b, 020_0561b | 3 + 2 blocks | corners | 0.09-0.80 / 1.16 | |
| 020_0562 | sheet | Illinois x Mariposa / 18th, 3 ties 591 | 0.69 / 1.20 (+0.45) | 0.2051, 3.89 |
| 020_0574, 020_0575 | 6 + 6 blocks | corners (streets drawn wide) | 0.59-2.80 / 3.38 | |
| 020_0589, 020_0590 | 3 + 4 blocks | corners | 0.60-2.13 / 3.12 | |
| 020_0591 | sheet | Illinois x 18th / 19th / 20th, Michigan x 20th | 0.45 / 0.72 | 0.2062, 4.38 |
| 020_0592 | sheet | 4 SIFT ties 591 / 594 (checked) | 0.97 / 1.44 (+0.45) | 0.2047, 4.09 |
| 020_0593 | sheet | Michigan x 20th / 22nd, 22nd St | 0.14 / 0.19 | 0.1988, 4.65 |
| 020_0594 | sheet | tie 593 (Louisiana x 22nd), 20th / 22nd St | 0.07 / 0.10 (+0.14) | 0.2048, 4.58 |
| 020_0607 | sheet | 12 block corners (3 blocks, to scale) | 1.16 / 2.22 | 0.2044, 4.14 |
| 020_0608 | 3 blocks | corners (Michigan x 23rd extended) | 1.37-2.57 / 2.69 | |
| 020_0609 | sheet | Michigan x 22nd, tie 593, 23rd St, Michigan St | 1.67 / 2.78 (+0.14) | 0.2039, 4.83 |
| 020_0610 | sheet | 3 SIFT ties 609 | 0.30 / 0.36 (+1.67) | 0.2020, 4.58 |
| 020_0626 | sheet | 16 block corners (4 blocks, to scale) | 1.41 / 1.69 | 0.2052, 4.53 |

The 1950 scans are registered onto these (SIFT + RANSAC, 418-3,321 inliers, 1.1-2.0 px). Note: on sheets 593 / 594 the drawn
20th St kerb does not follow DataSF's 20th St east of Illinois (which bends ~3 deg), so 20th St was not used on 593
and the Louisiana x 22nd corner of 593 is carried to 594 / 609 as a tie rather than taken from DataSF.

### Tracks (`tracks()`, `assemble_tracks()`)

A track is drawn as two rails 6-8 px apart on the 25 % scans (1.2-1.6 m; standard gauge 1.435 m). Dark pixels on
straight 15-px line segments (24 orientations; drops lettering and the dashed pipe / fence lines) are paired across the
gap, the paper pixels between the rails are skeletonised and vectorised; pieces inside building fills, in the scan
margins, shorter than 8 m, in small isolated groups, or the "Scale of Feet" bar are dropped. Block-wise sheets use a
rubber sheet (each block's fit inside the block, inverse-distance blend in the streets) so a track crossing a
too-wide street stays continuous. Overlaps between sheets are kept once (best fit first, the rest clipped to what the
better sheets do not cover). `control/<key>.tracks.json`: `railroad`, `railroads` (polygons), `main_px`, `exclude_px`.
Checked on overlays of sheets 591, 216, 217, 219-222: the yard fans, the Illinois St lead, the Union Iron Works loop,
the Santa Fe yard and the roundhouse turntable are found. Known false or doubtful lines: double lines along the edges
of shipbuilding slips and wharf bulkheads (crane rails or ways, not railway tracks), occasional pairs of parallel
building outlines 1.2-1.6 m apart; tracks inside train sheds and iron-clad buildings are missed.

### Rows added to `data/tables/notable_demolished.csv`

`tubbs_cordage_mill`, `tubbs_cordage_rope_walk` (traced ids `020_0607_b3/b4/b5/b9/f56`, 1950 `035_0607_*`; start and
end ESTIMATE: works 1856/57, closed 1961-63, demolished in the 1970s, last buildings 1978). Most of the Union Iron Works
/ Bethlehem buildings traced here still stand at Pier 70 (`modern_overlap`), so no rows.

### Open items

* **1950 shipyard (sheet 592)**: a paste-over slip says the Bethlehem Ship Building Corp. / Union Iron Works plant was
  "not surveyed since 1919 on account of government work": the 1950 sheet shows c. 1919, not 1950. Its slip
  buildings are only partly traced (3 hand rectangles).
* 1950 paste-over slips in general: grey / pale buildings on slips are often missed (1950 building area is 16 % (Mission Bay) and
  21 % (Potrero Point) lower than 1914, partly real demolition, partly this).
* `main` track kind: not drawn (SP Bayshore Cutoff main line through 545 / 559 / 574 not identified by label);
  railroad names only where the sheet labels the yard. Potrero Point spurs: no railroad label read.
* Sheet 220 (earlier pass) still has only two block corners (`low`); 222 / 216 are capped at `medium`.
* Storeys were read only for a few buildings; most of the 1914 vol. 6 features use the size / material rule.
* Not traced: 1914 vol. 6 sheets 576, 588, 606, 625 (south and west edges), the 1899-1900 editions of the area, 1950
  sheets beyond these.
* Probable ruler artefacts on the old sheets 152-176 / 220 (thin fills in the scan margin) are now dropped by a margin
  filter in the two rail-yard areas (`mission_bay`, `potrero_point`); the Fisherman's Wharf files are unchanged.

