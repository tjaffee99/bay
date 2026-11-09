# Sanborn tracing: downtown San Mateo (1908, 1920)

Real historical building footprints of downtown San Mateo - the B St / 3rd Av commercial core, the Southern Pacific
station plaza and freight yards, the lettered streets east of the tracks (C -> I St = Claremont -> Idaho St) and the
houses west of B St - traced from the Library of Congress scans of the Sanborn Map Co. *Insurance Maps of San Mateo,
California* (public domain: "Library of Congress, Geography and Map Division, Sanborn Maps Collection").
Built by `pipeline/sanborn_trace_peninsula.py` (`python pipeline/sanborn_trace_peninsula.py san_mateo ...`), a thin
extension of `pipeline/sanborn_trace_eastbay.py` (block specs, `refine`, property corners from today's parcels, block /
group similarity fits, colour segmentation split along partition walls, same output schema and confidence rules as
`README_oakland.md` / `README_san_jose.md`). Control: `control/san_mateo/`.

## Files

| file | content |
|---|---|
| `san_mateo_downtown_1908.geojson` | footprints on the April 1908 edition (sheets 11, 12, 14, 15, 16, 17), EPSG:4326 |
| `san_mateo_downtown_1920.geojson` | footprints on the May 1920 edition (sheets 4, 9, 10, 20, 21, 25, 26, 27) |
| `san_mateo_downtown_coverage.geojson` | one polygon per map year (`map_year` 1908 / 1920): the fitted block zones (clipped to the scan) + 12 m, i.e. the blocks and about half of the streets around them. An empty spot inside it was empty on that map |
| `control/san_mateo/<key>.json` | per sheet: blocks (`streets` N/S/W/E in the grid sense, `px4_est` estimates, refined `px4`, `edge_q`, the corners used with their control, `with` = fitted together with), `skip`, `zone_px`, `residential` / `residential_blocks` / `commercial_blocks`, `scale_prior`, `notes` |
| `control/san_mateo/aliases.json` | street names on the sheets -> today's (Overture) names |
| `control/san_mateo/labels.json` | 18 names / uses read off the sheets (pixel on the 25 % scan -> the footprint containing it) |
| `control/san_mateo/storeys.json` | 49 storey numbers read off the sheets (masonry buildings >= 120 m2 and the main commercial blocks) |
| `control/san_mateo/areas.json` | which sheets make up each map year |

Keys are `<LOC item suffix>_<sheet>`: `005_0015` = sanborn00824_005 (April 1908) sheet 15, `006_0021` =
sanborn00824_006 (May 1920) sheet 21. The two editions are different plates (1908: 18 sheets at the old sheet layout,
1920: 42 sheets incl. Hillsborough), so each sheet has its own control - no SIFT registration between them. The May
1920 - Feb 1950 corrected edition (`sanborn00824_007`) is catalogued without images (copyright period), as are the
later volumes, so 1920 is the last map year.

### Feature properties

As in `README_san_jose.md` (`id`, `map_year`, `volume`, `volume_label`, `loc_url`, `sheet`, `sheet_no`, `iiif`,
`stories`, `stories_source`, `material`, `use`, `use_source`, `name`, `sanborn_colour`, `confidence`, `georef`,
`georef_rms_m`, `extraction`, `area_m2`, `modern_overlap`). Differences:

* `material` from the 1908 / 1920 keys: yellow frame, red brick, blue stone (1908) / reinforced concrete (the 1920 blue
  fills are marked "reinf. concr."; the class name stays `stone` -> material `stone`, read the label), gray iron, brown
  adobe (1908) / fire-proof (1920) -> `adobe` / `concrete`.
* `stories`: **read off the sheet** for 49 buildings (`stories_source = map (read from the sheet)`: every masonry
  building of 120 m2 or more, read on 60 % IIIF crops; St. Matthew's Church is given 3 for its "35 ft to eaves" / "45
  ft"). Elsewhere the default rule (`default (rule: material, size, district)`): frame < 30 m2 shed 1; frame in a
  residential block < 110 m2 dwelling 1, 110-300 m2 dwelling 2, larger warehouse 1; frame in a commercial block
  < 150 m2 store 1, 150-400 m2 store 2, larger warehouse 1; brick / stone / concrete store 2 (warehouse 1 in residential
  blocks); iron shed 1. Commercial blocks: B St and the blocks along the tracks; the others are residential.
  Downtown San Mateo was a town of 1-2 storey buildings (the Hotel Wisnom block was 3, the 1908 Pacific Telephone and
  1920 reinforced-concrete stores 1-2), so the reads keep the masonry default of `sf_predecessors.apply_sanborn`
  (>= 3 storeys for unread masonry > 300 m2) from applying to them.
* `confidence`: high = the block / group fit has >= 4 corners, RMS <= 1.5 m, max <= 3 m (not all on one street);
  medium = >= 3 corners and RMS <= 3 m, or 2 corners with a scale within 1.5 % of the town's plate scale (0.2030 m/px);
  low otherwise.

## Counts

| file | features | high / medium / low | materials | uses | area (1000 m2) | modern_overlap >= 0.5 |
|---|---|---|---|---|---|---|
| san_mateo_downtown_1908 | 785 | 672 / 113 / 0 | frame 718, iron 30, brick 25, stone 12 | shed 338, dwelling 220, store 202, warehouse 19, hotel 2, library 2, church 1, bank 1 | 60.3 | 488 |
| san_mateo_downtown_1920 | 1,055 | 781 / 274 / 0 | frame 1002, brick 28, stone 22, concrete 2, iron 1 | shed 465, dwelling 318, store 237, warehouse 27, theatre 2, hall 2, other 1, church 1, garage 1, bank 1 | 85.2 | 623 |

Coverage: 52 ha (1908) and 77 ha (1920). Named: 8 (1908), 10 (1920).

## Sources

Sanborn Map Company, *Insurance Maps of San Mateo, California*, Library of Congress (public domain), IIIF images at
25 % (1613 x 1913 px, ~0.203 m/px at 50 ft = 1 in), 60 % crops for storeys:

| edition | LOC item | sheets used |
|---|---|---|
| April 1908 | https://www.loc.gov/item/sanborn00824_005/ | 11, 12, 14, 15, 16, 17 (key map 1); 13 tried, not used |
| May 1920 | https://www.loc.gov/item/sanborn00824_006/ | 4, 9, 10, 20, 21, 25, 26, 27 (key map 1) |

Other San Mateo items: 1888 `_001`, 1891 `_002`, 1897 `_003`, 1901 `_004` (11 sheets, images online, not traced),
May 1920 - Feb 1950 `_007` (no images).

Control geometry:
* **Street centrelines**: Overture Maps transportation segments, release 2026-10-21.0, `roads_local.parquet`
  (residential / unclassified / service / living street) + `roads_region.parquet` (motorway -> tertiary), clipped to the
  town box (ODbL, (c) OpenStreetMap contributors / Overture). Street directions at a crossing are fitted within 80 m
  (B St bends at 1st Av: -55 deg north of it, -49 deg south).
* **Property lines**: San Mateo County active parcels (`data/raw/region_years/san_mateo_parcels`, county GIS
  ACTIVE_PARCELS_APN, downloaded 2026-11-08), dissolved into blocks.
* **Footprints today** (`modern_overlap`): Overture buildings `region5_building.parquet` (ODbL).

## Method (differences from the East Bay / South Bay tools)

1. **Block lines on these plates are thin and light** (1-2 px at 25 %, grey 100-200 after JPEG blur) and run beside
   dashed double lines (water pipes) that are as dark on average. `refine_block` here scores an offset by the share of
   positions along the block side where a pixel 25+ grey levels darker than its 7-px median lies within +-1.5 px (solid
   line ~1.0, dashed ~0.5). A scratch aid (`lines` stage) lists the long solid axis-aligned lines of a sheet, from which
   the block outlines were read (+-5 px) before `refine`.
2. **Colour classes for the paler plates** (`extract`): yellow frame saturation >= 40 (paper ~12), the 1908 "gray" iron
   wash is grey-green (hue ~72, saturation 15-25), the 1908 blue is pale (saturation 15-30), drawn lines = 25 levels
   darker than the local median and < grey 200; the creek between its drawn banks is not a building (large, not solid).
   A footprint caught by two classes keeps the larger.
3. **Fits**: one similarity per block where its four corners agree, else with the blocks named in `with`. Corners on
   Railroad Av (100 ft wide in 1908, tracks in the street; today's N / S Railroad Ave property lines are not the old
   ones, 2-6 m residuals) are skipped and those blocks are fitted with the blocks across C St / B St. 2nd Av x F St, I St
   (north of the creek), 9th Av and the Laurel Av x 7th Av corners are not today's (re-platted) and are skipped or
   dropped as outliers. Pseudo-blocks (`no_refine`, all corners skipped) carry the parts of a sheet without a usable
   block outline (the B St lots' plaza and freight house strip, the private parks west of A St, the yards).
4. **Residential vs commercial** per block (`residential_blocks` / `commercial_blocks`) for the default uses.

## Georeferencing per sheet

| sheet (key) | map year | fits | RMS / max (m) per fit | scale (m/px), rotation | footprints |
|---|---|---|---|---|---|
| 005_0011 | 1908 | 2 fit(s), 4 block zones | 143: 2 pts 0.78/0.78; 138: 3 pts 0.81/1.13 | 0.2042, 40.6 deg | 59 |
| 005_0012 | 1908 | 6 fit(s), 7 block zones | 145: 4 pts 0.22/0.26; 146: 4 pts 0.53/0.67; 118: 6 pts 0.47/0.82; 119: 6 pts 0.96/1.67; 144: 6 pts 0.32/0.44; 139: 7 pts 0.42/0.64 | 0.2051, 41.7 deg | 193 |
| 005_0014 | 1908 | 7 fit(s), 7 block zones | 152: 4 pts 0.69/0.93; 173: 4 pts 0.61/0.69; 196: 4 pts 1.47/1.54; 208: 4 pts 0.85/0.97; 151: 6 pts 0.84/1.15; 172: 6 pts 2.14/3.38 ... | 0.2049, 41.3 deg | 129 |
| 005_0015 | 1908 | 12 fit(s), 12 block zones | 156: 4 pts 0.32/0.40; 177: 4 pts 0.46/0.57; 194: 4 pts 0.30/0.38; 155: 4 pts 0.70/0.81; 176: 4 pts 0.44/0.61; 193: 4 pts 0.59/0.83 ... | 0.2062, -49.1 deg | 293 |
| 005_0016 | 1908 | 8 fit(s), 8 block zones | 157: 11 pts 0.97/1.48; 178: 4 pts 0.72/0.82; 195: 4 pts 1.12/1.28; 158: 8 pts 0.93/1.54; 179: 4 pts 0.97/1.00; 196: 4 pts 0.54/0.60 ... | 0.2057, -48.9 deg | 82 |
| 005_0017 | 1908 | 1 fit(s), 9 block zones | 209: 14 pts 0.75/2.05 | 0.2043, 41.7 deg | 29 |
| 006_0021 | 1920 | 6 fit(s), 6 block zones | 145: 4 pts 0.36/0.46; 154: 4 pts 2.46/3.41; 144: 6 pts 0.55/0.81; 153: 5 pts 0.69/1.06; 143: 3 pts 0.39/0.48; 152: 4 pts 0.52/0.70 | 0.2021, -48.7 deg | 160 |
| 006_0026 | 1920 | 9 fit(s), 9 block zones | 174: 6 pts 0.71/1.09; 191: 6 pts 0.56/0.90; 209: 6 pts 1.30/1.92; 173: 4 pts 0.67/0.86; 190: 4 pts 0.51/0.61; 208: 4 pts 1.28/1.48 ... | 0.2000, -48.6 deg | 148 |
| 006_0009 | 1920 | 11 fit(s), 11 block zones | 157: 11 pts 0.33/0.51; 178: 4 pts 0.41/0.49; 195: 4 pts 0.89/1.02; 156: 4 pts 0.22/0.29; 177: 4 pts 0.20/0.27; 194: 4 pts 0.16/0.21 ... | 0.2026, -48.7 deg | 249 |
| 006_0020 | 1920 | 1 fit(s), 5 block zones | 118: 4 pts 1.75/2.28 | 0.2027, -48.1 deg | 151 |
| 006_0027 | 1920 | 7 fit(s), 8 block zones | 224: 6 pts 0.38/0.68; 239: 6 pts 0.35/0.60; 251: 3 pts 0.30/0.39; 223: 4 pts 0.31/0.41; 238: 4 pts 0.07/0.10; 250: 6 pts 0.22/0.33 ... | 0.2024, -48.4 deg | 69 |
| 006_0004 | 1920 | 9 fit(s), 9 block zones | 179: 4 pts 0.32/0.38; 196: 4 pts 0.15/0.20; 180: 4 pts 0.57/0.74; 197: 4 pts 0.16/0.21; 181: 9 pts 0.67/1.31; 198: 3 pts 0.40/0.49 ... | 0.2022, -48.8 deg | 182 |
| 006_0025 | 1920 | 1 fit(s), 2 block zones | 151: 2 pts 0.13/0.13 | 0.2013, -48.8 deg | 25 |
| 006_0010 | 1920 | 6 fit(s), 7 block zones | 213: 4 pts 0.41/0.51; 212: 4 pts 0.39/0.48; 211: 6 pts 0.39/0.64; 243: 6 pts 0.42/0.55; 242: 6 pts 0.49/0.62; 241: 8 pts 0.48/0.74 | 0.2015, -48.8 deg | 71 |

Rotation is the image x-axis against east (1908 sheets 11 / 12 / 14 / 17 are drawn with grid north up, the others with
grid north to the left). The 1920 sheet 21 draws one block per quarter with the streets between them not to scale;
everywhere else the streets are close to scale (group fits of 0.3-1.8 m).

### Findings (streets)

* **Lettered streets east of the tracks were renamed** after 1920 to names with the same initial: C = Claremont, D =
  Delaware, E = Eldorado, F = Fremont, G = Grant, H = Humboldt, I = Idaho (block corners fit to 0.2-1 m on today's
  parcels). In 1920 the sheets already write "South C", "North C" etc. **A St = today's (S) Ellsworth Av** south of
  2nd Av (1908 sheet 14, 0.6-1.5 m); north of the creek the 1908 sheets already say Ellsworth Av.
* **Railroad Av** was a 100 ft street with the tracks in it (1908); the B St lots, the plaza and passenger station and the
  S.P. freight house stood in the block between B St and the tracks.
* **1st -> 2nd Av west of B St**: 2nd Av does not meet B St today (crossing extended), and the block west of B St between
  1st and 2nd Av had no A St in 1908 (Hotel Wisnom block, school and library behind it).
* Sheet 13 (1908; D -> G St north of the creek, Cypress Av) was not used: its corners on today's Cypress Ave / Fremont
  St disagree by 7-28 m (the 1908 F St north of the creek is not today's Fremont St, or Cypress Av moved).

### Checks

* OpenHistoricalMap has 87 San Mateo buildings in the box; 17 are tagged as traced from the 1888 / 1901 Sanborn maps
  (Library Building, S.P. passenger station, St. Matthew's Church, Buchmann's Hotel, Fisher's Hotel, Hotel Vendome,
  Congregational Church ...). Of those inside the coverage, 12 / 15 (1908) and 9 / 14 (1920) are covered >= 50 % by
  our footprints (median 0.76 / 0.70); the rest were gone or rebuilt by 1908 / 1920. Not imported (our tracings cover
  the same buildings with the map-year outlines).
* Overlays of every sheet were checked by eye (`overlay` stage) and the check plot (`check` stage: every footprint valid
  and inside its coverage; traced footprints over today's Overture buildings) shows the blocks on today's grid.

## Not done / open items

* 1908 sheets 1-10, 13, 18 (north of the creek, Baywood, the Hillsborough / El Camino estates) and the rest of the
  1920 edition (sheets 2-3, 5-8, 11-19, 22-24, 28-42: North Central, Hillsborough, east of I St); 1901 and earlier
  editions (`_001`-`_004`, different plates).
* 1920 sheet 25: only the St. Matthew's block (2nd -> 3rd Av west of A St) is used; the school / union high school /
  hospital blocks along the creek and Griffith Av have no usable control.
* No railway tracks traced (the S.P. main line is in today's Caltrain right of way).
* Storeys read only for the masonry buildings; names for 18 buildings.

## Reproduce

```
python pipeline/sanborn_trace_peninsula.py san_mateo all        # fetch + georef + extract + assemble + check (control is frozen)
python pipeline/sanborn_trace_peninsula.py san_mateo assemble   # outputs only
python pipeline/sanborn_trace_peninsula.py san_mateo lines 005_0015      # scratch: long solid lines (block outlines)
python pipeline/sanborn_trace_peninsula.py san_mateo grid 005_0015 [x0 y0 x1 y1]   # scratch: crop with a pixel grid
python pipeline/sanborn_trace_peninsula.py san_mateo overlay 005_0015    # scratch: traced footprints on the sheet
```
Downloads go to `data/raw/sanborn_loc/peninsula/san_mateo/`, intermediates to `data/interim/sanborn_peninsula/san_mateo/`.
The control files hold the refined pixels (`norefine`), so a rerun reproduces the outputs.
