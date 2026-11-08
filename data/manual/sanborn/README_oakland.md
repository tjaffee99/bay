# Sanborn tracing: Oakland (West Oakland, downtown)

Real building footprints of the parts of Oakland that were cleared for the Cypress freeway (1955–57), the Main Post
Office, Acorn and BART (1960s), I-980 (1960s–70s) and City Center / the Convention Center (1970s–80s), traced from the
Library of Congress scans of the Sanborn Map Co. *Insurance Maps of Oakland, California* (public domain: "Library of
Congress, Geography and Map Division, Sanborn Maps Collection"). Two editions of the same plates: **1911–12 vol. 1**
(start bound) and the **1912 – Nov 1951 corrected vol. 1** (end bound before the clearances).
Built by `pipeline/sanborn_trace_eastbay.py`, an extension of `pipeline/sanborn_trace_waterfront.py` (same similarity
fits per block, SIFT registration of the corrected plates, colour segmentation, output schema and confidence rules as
`README_waterfront.md` / `README_industrial.md`); the extraction pass is the one of `sanborn_trace_southbay.py`
(partition walls split rows of buildings). Control: `control/oakland/`.

## Files

| file | content |
|---|---|
| `oakland_west_1912.geojson`, `oakland_west_1951.geojson` | West Oakland: 7th St corridor (5th / 3rd St → 8th St, Willow St → Castro St), Main Post Office blocks (sheet 92), West Oakland BART block, the Cypress St corridor (Center St → Kirkham St, 7th → 18th St; 10th–14th St only Center-side control, see below), Acorn (Union St → Market St, 3rd → 10th St) |
| `oakland_downtown_1912.geojson`, `oakland_downtown_1951.geojson` | downtown west of Broadway: Jefferson St → Broadway, 6th → 14th St (Old Oakland, the Convention Center / Marriott blocks, City Center 12th–14th St), Castro St → Jefferson St, 3rd → 11th St (I-980 edge, Jefferson Square) |
| `oakland_<area>_<year>_tracks.geojson` | railway / streetcar track centrelines drawn on those sheets (SP 7th St electric line, Western Pacific 3rd St spur, spurs, streetcar lines) |
| `oakland_<area>_coverage.geojson` | one polygon per map year (`map_year` = the file year): the fitted block zones + half of the surrounding streets. Inside it an empty spot was empty on that map |
| `control/oakland/<key>.json` | per sheet: blocks (`streets` N/S/W/E, `px4_est` estimates, refined `px4`, `edge_q`, corners used with their control type), `with` (blocks fitted together), `skip`, `w` (street widths for offset corners), `confidence_cap`, `notes`; 1951 sheets: the SIFT registration (`registered_to`, `T`) |
| `control/oakland/<key>.tracks.json` | `exclude_px`: the heavy double line dividing a two-part sheet (not a track) |
| `control/oakland/labels.json` | names / uses read off the 1911–12 sheets by pixel position (25 buildings) |
| `control/oakland/areas.json` | which sheets make up each area and map year |
| `control/oakland/005_0083.json` | sheet 83 (Market → Castro, 7th → 11th St): attempted, **not used** (no consistent control) |

Keys are `<LOC item suffix>_<sheet>`: `005_0095` = sanborn00727_005 (1911–12 vol. 1) sheet 95, `015_0095` = sanborn00727_015 (1912 – Nov 1951 vol. 1) sheet 95.

### Feature properties

As in `README_waterfront.md` / `README_industrial.md` (`id`, `map_year`, `volume` = `sanborn00727_<sfx>`, `volume_label`,
`loc_url`, `sheet`, `sheet_no`, `iiif`, `stories`, `stories_source`, `material`, `use`, `use_source`, `name`,
`sanborn_colour`, `confidence`, `georef`, `georef_rms_m`, `extraction`, `area_m2`, `modern_overlap`). Differences:

| property | meaning here |
|---|---|
| `map_year` | 1912 (1911–12 vol. 1, dated 1912) or 1951 (1912 – Nov 1951 vol. 1: the 1912 plates with paste-over corrections to Nov 1951). A feature says "standing at the map date", nothing more |
| `modern_overlap` | share of the footprint covered by today's Overture footprints (`region5_building.parquet`). ≥ 0.5 marks a building that still stands (e.g. the M. W. Hanning olive factory 0.97, the Western Paper Box Co. 0.93, much of Old Oakland) or a new building on the same spot |
| `stories` | **not read** from the sheets: `stories_source = default (rule …)` everywhere: frame < 30 m² shed 1; frame ≤ 300 m² dwelling 2 on residential sheets (store 2 downtown); frame ≥ 300 m² warehouse 1; brick / stone / concrete 2 (warehouse on residential sheets, store downtown); iron shed 1 |
| `use` | the rule above, or `map (label)` for the 25 labelled buildings |
| `confidence` | high: block / group fit with ≥ 4 corners, RMS ≤ 1.5 m and max ≤ 3 m, not all control on one street; medium: ≥ 3 corners and RMS ≤ 3 m, or control along a single street (collinear), or a sheet cap; low: weaker, or the sheet cap `low` (sheet 71) |
| `georef` | `block <name>` = the fit used for that footprint (a block's own 4-corner fit, or the fit of its group of blocks) |

## Counts

| file | features | confidence high / medium / low | area (1000 m²) | modern_overlap ≥ 0.5 | materials | named |
|---|---|---|---|---|---|---|
| oakland_west_1912 | 3224 | 1952 / 994 / 278 | 254.0 | 1099 | frame 3175, brick 36, iron 8, stone 5 | 18 |
| oakland_west_1951 | 2470 | 1467 / 824 / 179 | 255.2 | 943 | frame 2236, concrete 143, brick 80, iron 11 | 0 |
| oakland_downtown_1912 | 925 | 925 / 0 / 0 | 138.3 | 544 | frame 773, brick 146, stone 5, iron 1 | 7 |
| oakland_downtown_1951 | 611 | 611 / 0 / 0 | 131.5 | 308 | frame 398, brick 147, concrete 63, iron 3 | 0 |

| track file | lines | km | confidence high / medium / low | kind (rule) | named by street label |
|---|---|---|---|---|---|
| oakland_west_1912_tracks | 206 | 7.9 | 26 / 149 / 31 | yard 116, spur 90 | SP 7th St electric line 4.8 km, Western Pacific 3rd St spur 0.9 km |
| oakland_west_1951_tracks | 213 | 8.0 | 29 / 150 / 34 | yard 121, spur 92 | SP 7th St 4.5 km, WP 3rd St 1.3 km |
| oakland_downtown_1912_tracks | 62 | 2.2 | 7 / 55 / 0 | yard 32, spur 30 | SP 7th St 2.0 km |
| oakland_downtown_1951_tracks | 53 | 2.2 | 7 / 46 / 0 | yard 39, spur 14 | SP 7th St 2.1 km |

A "feature" is one coloured fill, split along the drawn partition walls. The 1951 counts are lower partly because of
real change (parking lots, the 1942 Peralta Villa, warehouses replacing houses), partly because faded fills on
paste-over slips are missed (the region pass adds some, `extraction = region`).

## Sources

Sanborn Map Company, *Insurance Maps of Oakland, California*, Library of Congress Geography and Map Division, Sanborn
Maps Collection (public domain); IIIF images at 25 % (≈ 1660 × 1950 px, 0.20 m/px at 50 ft = 1 in):

| edition | LOC item | sheets used |
|---|---|---|
| 1911–1912 vol. 1 (1912) | https://www.loc.gov/item/sanborn00727_005/ | 52 (lower strip), 57, 71, 77, 79, 80, 81, 82, 84, 85, 86, 92, 95, 96, 97, 98, 99, 100, 102 (83 tried, not used) |
| 1912 – Nov 1951 vol. 1 | https://www.loc.gov/item/sanborn00727_015/ | the same sheet numbers (same engraved plates, corrected) |

Volume 1 covers West Oakland and downtown west of Broadway (key map sheet `0000`, "congested district" map `cbd1/cbd2`).
Other Oakland items on loc.gov (item JSON in `data/raw/sanborn_loc_oakland/`): 1889 `_001` (73 sheets); 1902 vol. 1
`_002`, 1903 vols. 2–3 `_003`, `_004`; 1911 vol. 2 `_006` (east of Broadway: Chinatown, Lake Merritt, East Oakland
waterfront — corrected to Nov 1950 as `_016`), 1911–12 vols. 3–5 `_007`–`_009` (corrected 1950 `_017`…); 1925–29 vols.
4–8 `_010`–`_014` and their 1950–51 corrections `_018`–`_021.5`; the 1952 "republished" small-format volumes `_023`–`_032`;
1917 additional sheets `_033` (no images).

Control geometry:
* **Street centrelines**: Overture Maps transportation segments, release 2026-10-21.0, all road classes in
  (-122.335, 37.780, -122.245, 37.840), queried with DuckDB from `s3://overturemaps-us-west-2/release/2026-10-21.0/theme=transportation/type=segment`
  into `data/raw/overture/2026-10-21.0/roads_oakland_sanborn.parquet` (ODbL). `roads_region.parquet` holds only
  motorway → tertiary and lacks most West Oakland streets.
* **Property lines**: Alameda County parcels (`data/raw/region_years/alameda_county_2021`, public copy, see
  `data/research/region_buildings.md`), dissolved into blocks (`data/interim/sanborn_eastbay/parcel_blocks.parquet`).

## Method

1. **Blocks by hand, edges by machine.** For each sheet the blocks were named by their four streets (read on a 42–50 %
   view with a pixel grid) and their corners estimated to ±15–25 px. `refine` moves each block side onto the strongest
   long dark line within ±16–26 px (darkness profile across the side, two halves fitted separately), and the corners
   become the crossings of the refined sides; a side without a drawn line (peak < 0.35: rounded corner buildings,
   streets drawn without a block line) drops its two corners.
2. **World corners.** `pc` = property corner: the two street centrelines (straight fits within 150 m) give the
   crossing and directions; along each street the property line is the median normal offset of today's parcel-block
   boundary facing that street (18–75 m from the crossing, so corner cut-offs don't count); the corner is the crossing
   of the two property lines. Offsets outside 2.5–24 m (superblocks, freeway land, plazas) reject the corner. Where the
   block is gone, `oc` = offset corner: the centrelines (extended across the superblock) offset by half of each street's
   width measured on today's parcels nearby (Willow / Campbell / Center / Henry 60 ft, 8th / Peralta / 5th 80 ft, 7th
   100 ft, downtown streets 80 ft, Broadway 110 ft).
3. **Fits.** Similarity (scale, rotation, shift) per block when the block has 4 good corners and agrees with its group
   (scale within 1.5 %, rotation within 0.8°, RMS < 1.5 m), else one fit for its group (`with`: the blocks of one sheet
   or one strip of a two-part sheet). A corner off by > 3 m and > 3 × the median of the others is dropped (logged);
   most dropped corners were wrong property corners at re-platted blocks.
4. **1951 plates**: registered onto the 1912 scans (SIFT + RANSAC similarity, 806–1,776 inliers, 1.4–1.8 px =
   0.20–0.37 m), inheriting the 1912 block fits.
5. **Footprints**: colour classes as in the waterfront tool (yellow frame, pink brick, blue stone / concrete, brown
   fire-proof, grey iron), split along partition walls (South Bay variant), outline test, holes < 2,500 px filled; on the
   1951 sheets dark-ochre fills are re-classed to fire-proof and regions enclosed by drawn lines are added by median
   colour. Only footprints inside a fitted block zone are kept (two-part sheets, rotated sheets).
6. **Tracks**: the waterfront tool's automatic detection (two dark rails 1.2–1.6 m apart, skeletonised), on every
   sheet and both editions independently; kind by the parallel-track rule (`yard` / `spur`); `railroad` only where the
   sheets label the street ("Southern Pacific R.R. (Electric)" on 7th St, "Western Pacific spur track" on 3rd St), the
   others (spurs, streetcar lines on 8th, 12th, 14th St, San Pablo …) are unnamed. The double line dividing two-part
   sheets is excluded by hand (`*.tracks.json`); short horizontal lines at the foot of a sheet (scale bars) are dropped.

**Findings.**
* **Two grids.** The West Oakland grid is drawn at −15.5 ± 0.5° (image x-axis vs east) on all north-up sheets; sheets
  east of Market St south of 7th (99, 100, 84) and downtown (77, 85, 86, 102: drawn with north to the right) follow the
  downtown grid at −26° / +64°. They meet at Brush St: West Oakland's 10th St, extended east from Market St, reaches Brush St within 5 m of
  today's Brush × 11th St crossing, so extended crossings there are unreliable (the reason sheet 83 failed).
* **Streets that moved.** Kirkham St north of 7th St is today a lane inside the Cypress Village / Acorn superblocks
  (corners 2–6 m off), Cypress St (60 ft in 1911 and 1951) is today's ~55 m Mandela Pkwy right of way (half widths
  25–30 m on the parcels north of 10th St: the frontage lots were taken), Brush and Castro St are I-980 frontage roads.
  West of Peralta St the 1911 5th St ran ~56 m north of today's 5th St (a jog at Peralta, now inside the Post Office
  parcel), and 3rd St at Peralta / Lewis disagrees by 3.5 m.
* **Scale.** 0.2005–0.2037 m/px on all good fits (plate scale ≈ 0.2015 m/px at 25 %); the streets are drawn close to
  scale on most Oakland sheets (whole-sheet group fits of 0.4–1.3 m), unlike the 2 × 2-block SF sheets.

## Georeferencing per sheet

RMS / max per fit (the first fits listed; block fits and group fits), scale (m/px of the 25 % image) and rotation.
Collinear control (all corners on one street) caps a fit at `medium`.

| sheet (LOC id) | ed. | fit | control corners (property / offset) | RMS / max (m) | scale, rotation | cap / note |
|---|---|---|---|---|---|---|
| [00727_01_1912-0052](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 3 fit(s) over 3 block zones | 10 / 0 | 0.41/0.60; 0.37/0.46; 0.18/0.23 | 0.2019, -15.7 deg; 0.2016, -15.5 deg ... |  |
| [00727_01_1912-0057](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 1 fit(s) over 8 block zones | 8 / 0 | 1.05/1.98 | 0.2019, -15.6 deg |  |
| [00727_01_1912-0071](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 1 fit(s) over 5 block zones | 6 / 0 | 4.43/5.58 | 0.1994, -15.4 deg | low |
| [00727_01_1912-0079](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 1 fit(s) over 5 block zones | 5 / 0 | 0.57/0.79 | 0.2019, -15.2 deg | medium |
| [00727_01_1912-0080](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 1 fit(s) over 5 block zones | 5 / 0 | 1.39/2.32 | 0.2013, -16.1 deg |  |
| [00727_01_1912-0081](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 1 fit(s) over 6 block zones | 6 / 0 | 1.03/1.79 | 0.2013, -15.5 deg |  |
| [00727_01_1912-0082](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 2 fit(s) over 6 block zones | 15 / 0 | 2.72/4.08; 1.19/1.78 | 0.1997, -16.7 deg; 0.1928, -15.7 deg |  |
| [00727_01_1912-0092](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 1 fit(s) over 6 block zones | 3 / 3 | 1.64/2.44 | 0.2037, -15.3 deg | medium |
| [00727_01_1912-0095](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 4 fit(s) over 5 block zones | 14 / 0 | 0.73/1.70; 0.32/0.42; 0.12/0.14 ... | 0.2013, -15.4 deg; 0.2010, -15.2 deg ... |  |
| [00727_01_1912-0096](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 1 fit(s) over 6 block zones | 6 / 0 | 0.86/1.09 | 0.2024, -15.8 deg |  |
| [00727_01_1912-0097](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 1 fit(s) over 6 block zones | 10 / 0 | 1.06/1.80 | 0.2020, -15.4 deg |  |
| [00727_01_1912-0098](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 1 fit(s) over 6 block zones | 10 / 0 | 1.29/2.30 | 0.2026, -15.8 deg |  |
| [00727_01_1912-0099](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 1 fit(s) over 8 block zones | 5 / 0 | 0.36/0.53 | 0.2002, -26.1 deg |  |
| [00727_01_1912-0077](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 5 fit(s) over 6 block zones | 7 / 16 | 1.46/3.00; 0.76/1.02; 0.39/0.50 ... | 0.2011, 64.1 deg; 0.2015, 64.2 deg ... |  |
| [00727_01_1912-0084](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 4 fit(s) over 8 block zones | 21 / 0 | 0.73/2.12; 0.23/0.29; 0.21/0.27 ... | 0.2012, -25.8 deg; 0.2015, -25.7 deg ... |  |
| [00727_01_1912-0085](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 6 fit(s) over 6 block zones | 24 / 0 | 1.02/1.69; 0.19/0.25; 0.39/0.52 ... | 0.2018, 64.7 deg; 0.2011, 64.4 deg ... |  |
| [00727_01_1912-0086](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 4 fit(s) over 6 block zones | 16 / 0 | 0.30/0.38; 1.04/1.98; 0.28/0.35 ... | 0.2017, 64.6 deg; 0.2018, 64.2 deg ... |  |
| [00727_01_1912-0100](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 4 fit(s) over 8 block zones | 18 / 0 | 0.48/1.12; 0.34/0.44; 0.17/0.21 ... | 0.2015, -25.8 deg; 0.2024, -25.6 deg ... |  |
| [00727_01_1912-0102](https://www.loc.gov/item/sanborn00727_005/) | 1911-12 v.1 | 5 fit(s) over 6 block zones | 20 / 0 | 0.46/0.63; 0.33/0.43; 0.12/0.13 ... | 0.2021, 64.2 deg; 0.2007, 64.0 deg ... |  |

| 1951 sheet | registered onto | SIFT inliers | registration RMS |
|---|---|---|---|
| 015_0052 | 005_0052 | 1504 | 1.53 px = 0.32 m |
| 015_0057 | 005_0057 | 1178 | 1.71 px = 0.35 m |
| 015_0071 | 005_0071 | 806 | 1.79 px = 0.36 m |
| 015_0079 | 005_0079 | 1007 | 1.38 px = 0.28 m |
| 015_0080 | 005_0080 | 811 | 1.67 px = 0.34 m |
| 015_0081 | 005_0081 | 1295 | 1.51 px = 0.31 m |
| 015_0082 | 005_0082 | 1031 | 1.73 px = 0.34 m |
| 015_0092 | 005_0092 | 1746 | 1.42 px = 0.29 m |
| 015_0095 | 005_0095 | 1391 | 1.36 px = 0.20 m |
| 015_0096 | 005_0096 | 808 | 1.72 px = 0.35 m |
| 015_0097 | 005_0097 | 843 | 1.82 px = 0.37 m |
| 015_0098 | 005_0098 | 1327 | 1.47 px = 0.30 m |
| 015_0099 | 005_0099 | 1305 | 1.77 px = 0.36 m |
| 015_0077 | 005_0077 | 1467 | 1.65 px = 0.29 m |
| 015_0084 | 005_0084 | 1497 | 1.7 px = 0.35 m |
| 015_0085 | 005_0085 | 1776 | 1.46 px = 0.25 m |
| 015_0086 | 005_0086 | 1275 | 1.51 px = 0.26 m |
| 015_0100 | 005_0100 | 1202 | 1.66 px = 0.34 m |
| 015_0102 | 005_0102 | 1663 | 1.63 px = 0.29 m |


Notes per sheet (also in each control file's `notes`): 52 lower strip only (8th–7th St, Peralta–Center); 71 Center St
corners only, 2–6 m spread along the street (re-subdivided parcels) → **low**; 79 Center St corners only (Kirkham St
moved) → medium; 80, 81 control on both sides of Union / Adeline St only; 82 two strips fitted separately, the
8th–7th St strip 4 % off the plate scale → capped medium; 83 not used; 92 Main Post Office superblock: 7th St corners
(Willow / Campbell centrelines extended, offset 60 / 100 ft) + the Peralta–Lewis block → medium (RMS 1.6 m); 99 Brush St
corners only; 77 City Center: 13th St, Clay and Washington St between 12th and 14th St are gone, offset corners on the
extended centrelines.

## Coverage

* **oakland_west** (1912 and 1951 identical sheet sets): 7th St from Willow St (sheet 92) to Castro St (99), both sides:
  5th–7th St Willow → Castro (92, 95, 96, 97, 98, 99 with 3rd–5th St on 96–99), 7th–8th St Peralta → Market (52, 79, 80,
  81, 82), 8th–10th St Center → Market (79, 80, 81, 82); Cypress corridor 10th–14th St (71) and 14th–18th St (57),
  Center → Kirkham St.
* **oakland_downtown**: Castro → Jefferson St, 3rd → 11th St (100, 84); Jefferson St → Broadway, 6th → 14th St (102, 85,
  86, 77).
* **Not covered**: sheet 83 (Market → Castro, 7th → 11th St: the core of the Acorn housing and the I-980 / Brush St
  seam), 101 (5th–6th St Jefferson → Broadway: the Nimitz Freeway), 87–91, 93, 94 (Oakland Point, the western part of
  the Post Office site, 3rd–5th St Lewis → Cypress), 72–76, 58–62 (Oak Center, I-980 11th → 18th St), the Cypress
  corridor north of 18th St (46, 26, 27 …), and all of vol. 2 (Chinatown, Lake Merritt BART, Oakland Museum, Laney
  College).

## Clearance rows added to `data/manual/redevelopment_areas.csv`

| area_id | clear_start–end | ring | traced footprints inside (1912 / 1951) | confidence |
|---|---|---|---|---|
| `oak_peralta_villa` | 1941–1942 | Center / Cypress × 7th / 8th St crossings | 12 / 7 | dates MEDIUM, extent LOW |
| `oak_cypress_freeway` | 1954–1956 | Mandela Pkwy centreline 7th → 34th St buffered 28 m | 275 / 125 | MEDIUM |
| `oak_main_post_office` | 1962–1965 | today's USPS parcel (APN 6-1-1-6, 1675 7th St) | 180 / 160 | dates MEDIUM-LOW, extent MEDIUM |
| `oak_acorn` | 1962–1965 | Union / Brush × 10th / 3rd St | 1424 / 1180 | dates MEDIUM-HIGH, extent MEDIUM (includes industrial blocks) |
| `oak_oak_center` | 1966–1972 | Market / Brush × 18th / 10th St | 0 / 0 | LOW, mostly rehabilitation |
| `oak_bart_west_oakland` | 1966–1968 | Chester / Mandela × 7th / 5th St | 110 / 78 | dates ESTIMATED, extent HIGH |
| `oak_i980` | 1966–1974 | I-980 centrelines (Overture) buffered 45 m, I-880 → I-580 | 79 / 67 | MEDIUM-LOW |
| `oak_city_center` | 1970–1973 | Broadway / MLK Jr Way × 14th / 12th St | 63 / 60 | MEDIUM |
| `oak_convention_center` | 1978–1981 | Broadway / Clay × 11th / 10th St | 36 / 25 | LOW-MEDIUM |
| `oak_lake_merritt_bart` | 1966–1968 | Oak / Madison × 9th / 8th St | not traced | LOW-MEDIUM |

Sources per row in the CSV (Wikipedia: Cypress Street Viaduct, Interstate 980, West Oakland station, Lake Merritt
station, Oakland City Center; the Urban Renewal Atlas compilation for Acorn / the Post Office (citing Self 2003,
Schwarzer 2021, FHWA 1998); LocalWiki Oakland for Oak Center; oaklandwiki MacDermot Mansion for Peralta Villa; PCAD for
the Convention Center site). Rings run along today's street centrelines (Overture crossings) around the cleared blocks.

## Open items

* Sheet 83 and the rest of the Acorn core / I-980 corridor (72–76, 58–62), the Nimitz blocks (101), the western Post
  Office blocks (87–91, 93, 94) and the Cypress corridor north of 18th St; vol. 2 (`_006` / `_016`) for Chinatown,
  Lake Merritt BART, the Oakland Museum and Laney College.
* The 1902–03 (`_002`–`_004`) and 1889 (`_001`) editions (different plates: no SIFT shortcut; each sheet needs its own
  control). The 1925–29 volumes cover only the eastern districts (vols. 4–8).
* Storeys were not read (default rule everywhere); names only for 25 buildings on the 1912 sheets, none on 1951.
* Tracks are automatic: streetcar lines and spurs are included but unnamed; occasional double building outlines may be
  detected as tracks; tracks inside sheds are missed.
* 1951 paste-over slips: faded fills are partly missed (see Counts).
* No rows in `data/tables/notable_demolished.csv` (candidates: Golden West / Goebel brewery and the W. P. Fuller
  warehouses on the BART block, the MacDermot mansion (razed 1942), Tompkins School, St. Mary's Church).
* Clearance dates for the downtown Nimitz Freeway (5th–6th St) and the Oakland Museum / Laney College were not
  researched; Oak Center's official project boundary was not found.

## Reproduce

```
python pipeline/sanborn_trace_eastbay.py all        # fetch + georef + extract + tracks + assemble (control files are final)
python pipeline/sanborn_trace_eastbay.py assemble   # outputs only
python pipeline/sanborn_trace_eastbay.py register 015_0095 005_0095   # redo one SIFT registration
```
The control files hold the refined pixels (`norefine`), so a rerun reproduces the outputs.
