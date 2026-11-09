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

# Freeway corridors: SR-24, I-580, I-980 north of 11th St

The rights-of-way of the 1960s freeways through North Oakland, traced from the same LOC Sanborn editions so that the
cut blocks look like the neighbourhood they were (they replace the procedural corridor houses of
`region_predecessors.corridor_fill` inside their coverage). Whole blocks the freeway cut are traced, not only the part
under the road, so they join the surviving fabric; footprints that are today's buildings are left to the modern data
by `apply_sanborn` (`modern_overlap`). Tool: `pipeline/sanborn_trace_oakland_corridors.py` (configures
`sanborn_trace_eastbay.py` through `sanborn_trace_eastbay_cities.py`, like `sanborn_trace_oakland_central.py`);
control: `control/oakland_corridors/` (`areas.json`, `aliases.json`, one file per sheet; the 1950/51 sheets hold their
SIFT registration). Images and the LOC index are shared with `data/raw/sanborn_loc_oakland/`.

Volumes: 1911-12 **vol. 1** (`sanborn00727_005`, West Oakland / downtown up to 38th St - Moss Ave) and **vol. 3**
(`_007`, North Oakland and Emeryville: Moss Ave / 36th St to the Berkeley line), 1911 **vol. 2** (`_006`, east of
Broadway), and their corrected states 1912 - Nov 1951 vol. 1 (`_015`), 1911 - Nov 1950 vol. 2 (`_016`) and
1911 - Oct 1950 vol. 3 (`_017`): the same plates with paste-overs, registered onto the 1911-12 scans by SIFT. Sheet
293 of vol. 3 was re-drawn for the Idora Park tract ("New sheet Oct 1931") and is georeferenced on its own. File years
are 1912 / 1951 for all three areas (vol. 2 / 3 sheets are dated 1911 / 1950 in `map_year` / `volume_label`).

| area | files | sheets (1911-12 key -> corrected) | extent |
|---|---|---|---|
| `oakland_sr24` | `oakland_sr24_1912.geojson`, `_1951.geojson`, `_coverage.geojson` | vol. 1: 31, 32, 17, 18, 12, 16; vol. 3: 359, 345, 346, 333, 334, 310, 304, 303, 293, 305, 294, 295, 296, 306, 281, 282, 283 | Grove St (MLK Jr Way) - Telegraph Ave Merrimac (27th) - 38th St and the MacArthur Maze (West - Grove St, 33rd - 38th St); West St - Telegraph 40th - 44th St, Grove - Shattuck 44th - 52nd St (Children's Hospital / Temescal Creek blocks); Dover - Shattuck - Telegraph 52nd - 55th St; Shattuck - Telegraph 55th - 58th (the Idora Park tract on the 1931 plate); Telegraph - Claremont Ave (Vicente / Ayala / Miranda St); Claremont - Shafter Ave, Forest - Clifton St (Hudson St); Claremont - College Ave (Oakgrove Ave); College Ave - McMillan Ave / Broadway (Shafter Ave - Bayview Ave) |
| `oakland_i980n` | `oakland_i980n_1912.geojson`, `_1951.geojson`, `_coverage.geojson` | vol. 1: 75, 76, 62, 50, 40, 41, 42 | Brush - Castro St 11th - 19th St (and Castro - Grove 15th - 19th), Brush St - Grove St 19th - 22nd St (San Pablo Ave), San Pablo Ave - Grove 22nd - Sycamore St, Grove - Telegraph 22nd - Merrimac St. South of 11th St: `oakland_downtown` / `oakland_west` |
| `oakland_i580` | `oakland_i580_1912.geojson`, `_1951.geojson`, `_coverage.geojson` | vol. 1: 19, 20; vol. 2: 126, 133, 127 | Telegraph Ave - Broadway 34th - 37th St (Edwards St, south of Mosswood Park); Richmond Ave / Kempton Ave - Fairmount Ave - Walsworth Ave, Moss Ave - Pearl St; Walsworth Ave - Vernon St, Perry St - Perkins St; Perry St - Santa Clara Ave - Moss Ave (MacArthur Blvd) to Vernon St |

## Method (additions to the West Oakland method)

* **`predict` / `auto`**: two to four street crossings read by eye on the 25 % scan give a first similarity; it is
  refined by a **chamfer match** (below); every block corner of the spec (today's property corner, else the
  centreline crossing offset by the printed widths) is projected onto the sheet as the estimate that `refine` snaps
  onto the drawn block outline; a second pass repeats this from the first fit. Blocks cut by the sheet edge keep the
  part on the sheet (their off-sheet corners are not control) and are fitted with the blocks of their row / column.
* **Own fit kept** (`regroup`): a block with four good corners of its own (RMS <= 1 m, scale within 2.5 % of the plate
  scale 0.2015 m/px) keeps its own fit even where it disagrees with its group (blocks are to scale, streets not
  always).
* **Chamfer match**: a similarity (scale within 1.5 % of the plate scale) minimising the distance from today's
  property lines (boundaries of the Alameda County parcel blocks, sampled every 1 m) to the dark lines drawn on the
  sheet (`chamfer` in each control file: M, mean distance, share of property-line points within 6 px = inliers,
  their RMS). Along the freeways the corners of the cut blocks are mostly gone or re-platted (parcels running into the
  old streets: "implausible property-line offsets"), so a block **without a good corner fit** (fewer than 3 corners,
  RMS > 1.5 m or max > 3 m, or a scale > 2.5 % off the plate) takes the chamfer match when at least 45 % of the
  property lines fall on drawn lines (`fit: chamfer`, `georef_rms_m` = max(inlier RMS, 1 m), confidence at most
  medium); below 45 % it keeps a fair corner fit (n >= 3, RMS <= 3 m) or takes the match as **low** (RMS 3.5 m). The
  chamfer match agrees with good 4-corner block fits to 0.1-1.4 m (sheets 345, 333).
* **Zones by hand** (`zones`, `mode: chamfer_only`): where the 1911 streets are gone (Oakgrove Ave, the 1911 Shafter /
  Keith Ave in Rockridge, Miranda St, Edwards St, 56th St east of Telegraph) the block zones are polygons drawn on the
  scan and the sheet is placed by the chamfer match alone (281: by three street crossings, the match failing there).
* **Control-only blocks**: blocks beside the corridor that were not cut (still standing) are fitted for their
  neighbours' sake but emit no footprints and no coverage (`control_only`).
* Zones are the block outlines (refined px4 or the drawn polygon), not their bounding boxes; the coverage of each map
  year is extended to every footprint kept (a building drawn across a zone edge); a footprint on sheets of two corridor
  areas (zones meeting across a street) is kept once, in the first of sr24 / i980n / i580 (8 + 9 at Merrimac St).
* Street names: `aliases.json` (Forest = Forest St, the 1911/12 38th St and Moss Ave = today's (West) MacArthur Blvd
  are written as `MacArthur Boulevard` in the specs).
* Validation (`check`): all geometries valid, every footprint inside its coverage, a PNG per area with the traced 1951
  footprints over today's Overture footprints and freeways (`data/interim/sanborn_oakland_corridors/check_<area>.png`),
  and zoomed overlays: houses that still stand fall on today's footprints on 345, 333, 304, 296, 306, 293 (1931), 76,
  62, 40, 126, 133, 127.

## Counts

| file | features | confidence high / medium / low | area (1000 m²) | modern_overlap ≥ 0.5 | materials |
|---|---|---|---|---|---|
| oakland_i580_1912 | 717 | 0 / 657 / 60 | 60.2 | 284 | frame 715, stone 1, brick 1 |
| oakland_i580_1951 | 944 | 0 / 869 / 75 | 87.0 | 396 | frame 898, concrete 28, brick 17, iron 1 |
| oakland_i980n_1912 | 1022 | 369 / 653 / 0 | 99.4 | 280 | frame 1010, iron 6, brick 5, concrete 1 |
| oakland_i980n_1951 | 986 | 336 / 650 / 0 | 117.7 | 252 | frame 827, brick 99, concrete 55, iron 5 |
| oakland_sr24_1912 | 3147 | 878 / 2222 / 47 | 239.9 | 1306 | frame 3136, brick 10, stone 1 |
| oakland_sr24_1951 | 5435 | 1570 / 3748 / 117 | 450.9 | 2405 | frame 5214, brick 127, concrete 82, iron 12 |


Storeys are **not read** on these sheets (the default rule: frame dwelling <= 300 m2 = 2 storeys, < 30 m2 shed 1,
masonry 2; `stories_source = default`); most corridor houses are 1-2 storey frame cottages, so the 2-storey default
overstates the 1-storey ones. `use` = store within 35 m of Telegraph, 40 m of Broadway, 30 m of College Ave.

## Georeferencing per sheet

Fits per block zone (corners n, RMS / max in m) or `chamfer` (with the rejected corner fit in brackets), the sheet's
chamfer match and its scale / rotation (image x-axis vs east).

| sheet | area | blocks / zones | fit per block: corners n, RMS / max (m) | chamfer match (inliers, inlier RMS) | scale, rotation |
|---|---|---|---|---|---|
| 005_0019 | oakland_i580 | 1 zones by hand | 1120-1129: chamfer | 60%, 0.54 m | 0.1991, -11.7° |
| 005_0020 | oakland_i580 | 2 zones by hand | 1120-1127e: chamfer; 1124-1126: chamfer | 38%, 0.54 m | 0.2045, -11.5° |
| 006_0126 | oakland_i580 | 1 zones by hand | 982-1033: chamfer | 76%, 0.40 m | 0.2012, -42.6° |
| 006_0133 | oakland_i580 | 1 zones by hand | 960-987: chamfer | 79%, 0.44 m | 0.2008, -47.1° |
| 006_0127 | oakland_i580 | 1 zones by hand | 1006-1036: chamfer | 69%, 0.42 m | 0.2006, 42.5° |
| 005_0075 | oakland_i980n | 4, control only: 258 184 181 152 | 257: chamfer (corners 3, 1.4); 185: chamfer (corners 3, 3.7); 180: chamfer (corners 4, 1.6); 153: 3, 0.53 / 0.71 | 68%, 0.42 m | 0.2018, -25.9° |
| 005_0076 | oakland_i980n | 4, control only: 256 186 179 154 | 257: 11, 0.91 / 1.95; 185: 9, 1.02 / 1.75; 180: 9, 0.92 / 1.51; 153: 11, 0.84 / 1.51 | 94%, 0.31 m | 0.2005, -26.0° |
| 005_0062 | oakland_i980n | 8 | 287: chamfer (corners 9, 3.1); 280: chamfer (corners 8, 1.7); 273: 7, 0.80 / 1.08; 264: 9, 0.73 / 1.26; 286: 9, 0.77 / 1.50; 281: 12, 1.07 / 2.28; 272: 11, 0.98 / 1.93; 265: 4, 0.09 / 0.13 | 89%, 0.30 m | 0.2011, -25.9° |
| 005_0050 | oakland_i980n | 5, control only: 299 293 | 294: chamfer (corners 5, 3.0); 295: chamfer (corners 5, 3.0); 297-298: 3, 0.72 / 0.88; 1508: chamfer; 1516: chamfer (corners 4, 2.5) | 63%, 0.36 m | 0.2031, -25.5° |
| 005_0040 | oakland_i980n | 4 | 1510: 7, 0.46 / 0.71; 1519: 4, 0.34 / 0.42; 1518: 7, 0.46 / 0.71; 1517: 7, 0.46 / 0.71 | 65%, 0.38 m | 0.2017, -10.8° |
| 005_0041 | oakland_i980n | 3 | 1206: chamfer (corners 5, 9.7); 1514: chamfer (corners 5, 9.7); 1515: chamfer (corners 5, 9.7) | 66%, 0.48 m | 0.2029, 78.7° |
| 005_0042 | oakland_i980n | 3 | 1520: chamfer (corners 11, 10.0); 1521: chamfer (corners 11, 10.0); 1522: chamfer (corners 11, 10.0) | 69%, 0.43 m | 0.2020, 79.4° |
| 005_0031 | oakland_sr24 | 3 | 1205: chamfer (corners 6, 7.9); 1524: chamfer (corners 6, 7.9); 1525: chamfer (corners 6, 7.9) | 47%, 0.51 m | 0.2045, 79.4° |
| 005_0032 | oakland_sr24 | 3 | 1145: chamfer (corners 6, 3.8); 1146: chamfer (corners 6, 3.8); 1147: chamfer (corners 6, 3.8) | 77%, 0.37 m | 0.2018, 79.2° |
| 005_0017 | oakland_sr24 | 3 | 1148: chamfer (corners 6, 4.5); 1149: chamfer (corners 6, 4.5); 1150: chamfer (corners 6, 4.5) | 81%, 0.43 m | 0.2019, 79.1° |
| 005_0018 | oakland_sr24 | 2 | 1151-1152: chamfer (corners 5, 3.1); 1153: chamfer (corners 5, 3.1) | 76%, 0.40 m | 0.2018, 79.3° |
| 005_0012 | oakland_sr24 | 3 | 1160: 4, 0.08 / 0.11; 1161-1162: 4, 0.08 / 0.11; 1163: 4, 0.08 / 0.11 | 87%, 0.29 m | 0.2007, -10.3° |
| 005_0016 | oakland_sr24 | 2, control only: 1166 1167 | 1164: chamfer (corners 16, 4.2); 1165: chamfer (corners 16, 4.2) | 95%, 0.29 m | 0.2012, -16.4° |
| 007_0359 | oakland_sr24 | 3 | 1154: chamfer (corners 9, 2.1); 1155: chamfer (corners 9, 2.1); 1156: 4, 0.46 / 0.65 | 66%, 0.40 m | 0.2003, 79.2° |
| 007_0345 | oakland_sr24 | 8 | 5053: 4, 0.22 / 0.30; 5052: 4, 0.22 / 0.26; 5051: 14, 0.88 / 2.00; 5050: 14, 0.89 / 2.04; 5085: 11, 0.42 / 0.72; 5084: 11, 0.40 / 0.87; 5083: 9, 0.33 / 0.62; 5082: 9, 0.72 / 1.02 | 93%, 0.35 m | 0.2003, -11.1° |
| 007_0346 | oakland_sr24 | 4 | 5085: chamfer (corners 6, 1.9); 5084: chamfer (corners 6, 1.9); 5083: chamfer (corners 6, 1.9); 5082: chamfer (corners 6, 1.9) | 87%, 0.43 m | 0.2009, -11.0° |
| 007_0333 | oakland_sr24 | 6 | 5056: 10, 0.77 / 1.46; 5055: 4, 0.51 / 0.65; 5054: 10, 0.68 / 1.39; 5088: 6, 0.97 / 1.75; 5087: 7, 0.85 / 1.33; 5086: 3, 0.24 / 0.31 | 80%, 0.32 m | 0.1994, -10.7° |
| 007_0334 | oakland_sr24 | 4 | 5089: chamfer (corners 4, 2.4); 5088: chamfer (corners 4, 2.4); 5087: chamfer (corners 4, 2.4); 5086: chamfer (corners 6, 2.9) | 81%, 0.46 m | 0.2011, -10.5° |
| 007_0310 | oakland_sr24 | 3, control only: 5058 | 5061: chamfer (corners 3, 1.1); 5057: 4, 0.59 / 0.94; 5060: 3, 0.88 / 1.20 | 28%, 0.46 m | 0.1977, -79.7° |
| 007_0304 | oakland_sr24 | 6 | 5095: 8, 1.37 / 2.45; 5094: 8, 1.47 / 2.84; 5093: 7, 1.26 / 2.11; 5064: chamfer (corners 8, 2.0); 5063: chamfer (corners 8, 1.9); 5062: chamfer (corners 8, 2.2) | 76%, 0.40 m | 0.2025, -79.6° |
| 007_0303 | oakland_sr24 | 5 | 5095: chamfer; 5094: chamfer; 5093: chamfer (corners 5, 3.5); 5138: chamfer (corners 5, 3.2); 5137: chamfer (corners 6, 3.9) | 49%, 0.49 m | 0.2025, -80.7° |
| 007_0293 | oakland_sr24 | 1 | 5140: chamfer | 26%, 0.45 m | 0.1907, 6.5° |
| 007_0305 | oakland_sr24 | 4 | 5256: chamfer (corners 4, 4.0); 5255: chamfer (corners 4, 4.0); 5265: chamfer (corners 4, 4.0); 5264: chamfer (corners 4, 4.0) | 47%, 0.42 m | 0.2014, -6.3° |
| 007_0294 | oakland_sr24 | 4 | 5257: 3, 1.74 / 2.14; 5269: 3, 1.74 / 2.14; 5268: 3, 1.74 / 2.14; 5265: 3, 1.74 / 2.14 | 32%, 0.43 m | 0.2057, -6.0° |
| 007_0295 | oakland_sr24 | 5 | 5267: chamfer; 5568: chamfer; 5567: chamfer; 5266: 3, 0.33 / 0.40; 5566: chamfer | 68%, 0.55 m | 0.2010, -32.1° |
| 007_0296 | oakland_sr24 | 8 | 5569: 14, 1.18 / 2.47; 5590: 14, 1.08 / 2.42; 5570: 4, 0.88 / 1.22; 5591: 14, 1.13 / 2.52; 5565: 10, 0.80 / 1.32; 5564: 11, 0.74 / 1.92; 5563: 12, 1.01 / 2.25; 5562: 11, 0.75 / 1.57 | 86%, 0.38 m | 0.2011, -32.1° |
| 007_0306 | oakland_sr24 | 3, control only: 5553 5554 5555 | 5566: 8, 1.06 / 1.95; 5565: 10, 0.63 / 1.39; 5564: 10, 0.62 / 1.26 | 92%, 0.33 m | 0.2001, -32.1° |
| 007_0282 | oakland_sr24 | 1 zones by hand | 5621-5625: chamfer | 63%, 0.50 m | 0.1985, 26.4° |
| 007_0283 | oakland_sr24 | 1 zones by hand | 5622-5627: chamfer | 63%, 0.42 m | 0.2015, 26.4° |
| 007_0281 | oakland_sr24 | 1 zones by hand | 5573-5575: chamfer | 3 street crossings read by eye, RMS 2.42 m | 0.2009, -30.5° |

| corrected sheet | registered onto | SIFT inliers | RMS |
|---|---|---|---|
| 015_0019 | 005_0019 | 742 | 1.54 px = 0.31 m |
| 015_0020 | 005_0020 | 866 | 1.51 px = 0.31 m |
| 016_0126 | 006_0126 | 1185 | 1.58 px = 0.32 m |
| 016_0133 | 006_0133 | 1760 | 1.41 px = 0.29 m |
| 016_0127 | 006_0127 | 1111 | 1.73 px = 0.35 m |
| 015_0075 | 005_0075 | 1683 | 1.34 px = 0.27 m |
| 015_0076 | 005_0076 | 1668 | 1.6 px = 0.32 m |
| 015_0062 | 005_0062 | 1679 | 1.32 px = 0.27 m |
| 015_0050 | 005_0050 | 1270 | 1.45 px = 0.30 m |
| 015_0040 | 005_0040 | 1169 | 1.55 px = 0.32 m |
| 015_0041 | 005_0041 | 841 | 1.83 px = 0.38 m |
| 015_0042 | 005_0042 | 782 | 1.71 px = 0.35 m |
| 015_0031 | 005_0031 | 925 | 1.84 px = 0.38 m |
| 015_0032 | 005_0032 | 1095 | 1.45 px = 0.30 m |
| 015_0017 | 005_0017 | 969 | 1.45 px = 0.29 m |
| 015_0018 | 005_0018 | 1023 | 1.35 px = 0.28 m |
| 015_0012 | 005_0012 | 1443 | 1.78 px = 0.36 m |
| 015_0016 | 005_0016 | 1286 | 1.39 px = 0.28 m |
| 017_0359 | 007_0359 | 1107 | 1.57 px = 0.32 m |
| 017_0345 | 007_0345 | 710 | 1.19 px = 0.24 m |
| 017_0346 | 007_0346 | 765 | 1.58 px = 0.32 m |
| 017_0333 | 007_0333 | 602 | 1.75 px = 0.36 m |
| 017_0334 | 007_0334 | 644 | 1.64 px = 0.33 m |
| 017_0310 | 007_0310 | 867 | 1.6 px = 0.32 m |
| 017_0304 | 007_0304 | 770 | 1.59 px = 0.33 m |
| 017_0303 | 007_0303 | 1048 | 1.77 px = 0.36 m |
| 017_0293 | own control (new plate) | – | – |
| 017_0305 | 007_0305 | 1351 | 1.59 px = 0.32 m |
| 017_0294 | 007_0294 | 1276 | 1.44 px = 0.30 m |
| 017_0295 | 007_0295 | 823 | 1.8 px = 0.37 m |
| 017_0296 | 007_0296 | 505 | 1.53 px = 0.31 m |
| 017_0306 | 007_0306 | 432 | 1.77 px = 0.36 m |
| 017_0282 | 007_0282 | 402 | 1.5 px = 0.30 m |
| 017_0283 | 007_0283 | 335 | 1.66 px = 0.34 m |
| 017_0281 | 007_0281 | 670 | 1.69 px = 0.34 m |

## Limits and open items

* **I-580 is partial**: traced from Telegraph Ave to Broadway (34th - 37th St) and from Kempton / Fairmount Ave over
  Santa Clara Ave to Vernon St. Not traced: vol. 2 sheet 131 (Broadway - Richmond Ave, Piedmont / Randwick / Croxton
  Ave: tried, the fit left the houses ~15 deg off today's Brook St houses, not used), 132 (Glen Echo Creek / block 963,
  weak match), 125 and the stretch south of Vernon St to Lakeshore Ave / Grand Ave (vol. 2 sheets 128-130, 134, next
  to `oakland_adams_point` sheets 135 / 141 - check its coverage before tracing), and everything east of Grand Ave
  (vol. 4: the 1911-12 plates `_008` and the 1928 re-survey `_010` corrected to 1950 `_018` are different plates, so
  no SIFT shortcut).
* SR-24: the Rockridge zones (281-283) are coarse polygons (all of the sheet between the old Shafter Ave and Bayview /
  Forest St), 281 is placed by three crossings (RMS 2.4 m), 293 (1911, block 5140) and 310 (5061) are low confidence;
  Idora Park itself (1911) is left to `data/manual/vanished_sites` (site `idora_park`); sheets 302 and 22 (west of
  Grove St, not cut) are not traced.
* Corner residuals near the freeways are large (re-platted parcels, MacArthur Blvd widened, 28th St / Merrimac St and
  36th St re-aligned): the chamfer match carries most cut blocks (`fit: chamfer`, medium confidence).
* **No clearance rows** for SR-24 / I-580 in `data/manual/redevelopment_areas.csv` (I-980 has `oak_i980`, 1966-74):
  without one, a 1951-map building that nothing replaced ends at max(1951 + 15, 1960) = 1966 in `apply_sanborn`.
  SR-24 (Grove-Shafter) opened in stages c.1968-70 and I-580 (MacArthur Freeway) c.1963-66, so rows with researched
  clearance years would date the corridor houses better (not added here).
* Storeys not read; names / labels not read; tracks not extracted on these sheets.

## Reproduce

```
python pipeline/sanborn_trace_oakland_corridors.py georef            # all sheets in areas.json (control files are final)
python pipeline/sanborn_trace_oakland_corridors.py extract
python pipeline/sanborn_trace_oakland_corridors.py assemble
python pipeline/sanborn_trace_oakland_corridors.py check [area]
python pipeline/sanborn_trace_oakland_corridors.py auto 007_0296 <spec.json>    # new sheet: crossings + blocks -> control
python pipeline/sanborn_trace_oakland_corridors.py zones 007_0283 <spec.json>   # new sheet: hand-drawn zones, chamfer only
python pipeline/sanborn_trace_oakland_corridors.py register 017_0296 007_0296   # corrected plate onto the 1911-12 scan
```
`georef` re-fits the base sheets from their control files and re-applies the chamfer / control-only / zone-outline
rules from the stored `chamfer` results, so a rerun reproduces the outputs.
