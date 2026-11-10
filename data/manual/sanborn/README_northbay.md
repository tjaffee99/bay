# Sanborn tracing: Santa Rosa, Vallejo, Napa, Petaluma (the north bay downtowns)

Real historical building footprints traced from the Library of Congress scans of the Sanborn Map Co. fire-insurance
maps (public domain: "Library of Congress, Geography and Map Division, Sanborn Maps Collection"). Built by
`pipeline/sanborn_trace_newcounties.py <town> all`, a thin extension of `sanborn_trace_peninsula.py` (-> `_eastbay.py` ->
`_waterfront.py`): block specs (four streets + estimated pixel corners), `refine` (block sides snapped onto the drawn block
lines), similarity fits per block / group, colour segmentation with partition-wall splitting, SIFT registration of an
edition onto another state of the same plate, and the same output schema and confidence rules (`README_san_mateo.md`,
`README_palo_alto.md`, `README_san_jose.md`). The area prefixes are registered in `region_predecessors.REGION_SANBORN`.

What this tool adds (see its docstrings):
* **scan normalisation**: the LOC scans of these volumes are dark (paper ~ RGB 132/130/112 on Santa Rosa 1908); a
  per-channel gain brings the paper to the cream the colour thresholds were tuned on (`normalise`);
* **control where today's property lines are not the map's**: `oc` offset corners (street centrelines of Overture,
  release 2026-10-21.0, + half the street width printed on the sheet) beside the `pc` parcel corners; `tie` corners on a
  georeferenced neighbour sheet; a single corner + the scale / rotation of a neighbouring fit (`scale_prior`);
* **plate matching with a displacement vote** (`match`, `partner`, `register`): RANSAC alone found degenerate transforms
  between editions whose buildings all changed; also finds the partner of a renumbered sheet;
* **per-block rules at assembly**: `block_cap` (blocks placed by a neighbour's fit are capped at medium / low),
  `awnings` (editions that draw the wooden sidewalk awnings as yellow strips in the street: footprints are clipped to
  their block, strips dropped), `drop_classes` (the blue water tint of a waterfront sheet), brown = fire-proof concrete
  on the 1908+ Santa Rosa keys, blue = concrete on the editions corrected to 1950 / 1962.

Files per area: `<area>_<year>.geojson` (EPSG:4326, properties as in `README_san_mateo.md`), `<area>_coverage.geojson`
(one polygon per map year: the block zones of the traced sheets + 12 m; an empty spot inside was empty on that map),
`control/<town>/<key>.json` (block specs with refined pixels, or the registration `T`), `aliases.json` (street names on
the sheets -> today's), `areas.json`. Keys are `<LOC item suffix>_<sheet>`. No `_tracks.geojson`: no tracks were traced.
Storeys were **not read** (`stories_source = default`, the small-town rule of the peninsula tool); no names were read.
Parcel layers used as property lines: `data/raw/region_years/{sonoma_county, solano_county, napa_county,
santa_cruz_parcels}`; today's footprints for `modern_overlap`: Overture `region4_building.parquet`.

`apply_sanborn` was run on each area alone (scratch script: today's Overture footprints dated by the county parcel
under them, no generated fabric, the committed clearances): "matched" = footprints of a map year that the next map
year covers by >= 40 % (the same building), "standing" = footprints recognised as a building of today and left to the
modern data. A traced building of the last map year with no later building on its ground and no clearance around it
ends at apply_sanborn's default (`max(map year + 15, 1960)`): where a town's last map is 1905-1910 that is a heap of
buildings vanishing in 1960 - every dated clearance row removes part of it (see each town's limits).

## Santa Rosa (`santa_rosa_downtown`: Dec 1904, 1908, 1950)

The courthouse-square blocks and 4th St from Wilson St (Railroad Square) to E St, 5th St to 1st St: the brick downtown that the earthquake of 18 April 1906 destroyed (Dec 1904 edition), the town rebuilt in stone and brick (1908), and the same plates corrected to 1950 - the fabric the urban renewal of the 1960s-70s and US 101 removed.

| edition | LOC item | sheets used |
|---|---|---|
| Dec 1904 (39 sheets) | https://www.loc.gov/item/sanborn00838_004/ | 24 (two strips: `004_0024` / `004_0024b`), 25, 28, 29 |
| 1908 (58 sheets + key) | https://www.loc.gov/item/sanborn00838_005/ | 25, 34, 35, 36, 43, 44 (key map `0000`) |
| 1908 corrected to 1950 (65 sheets) | https://www.loc.gov/item/sanborn00838_006/ | 25, 34, 35, 36, 43, 44 |

The 1969 volume (`_007`) has no images.

| file | features | high / medium / low | materials | uses | area (1000 m2) | modern_overlap >= 0.5 |
|---|---|---|---|---|---|---|
| santa_rosa_downtown_1904 | 876 | 47 / 765 / 64 | frame 727, brick 113, iron 34, adobe 2 | shed 409, store 273, dwelling 176, warehouse 18 | 81.7 | 515 |
| santa_rosa_downtown_1908 | 832 | 67 / 689 / 76 | frame 694, brick 73, stone 43, unknown 22 | shed 337, store 252, dwelling 205, other 22, warehouse 16 | 79.0 | 505 |
| santa_rosa_downtown_1950 | 510 | 71 / 411 / 28 | frame 310, concrete 105, brick 86, iron 9 | store 191, shed 159, dwelling 99, warehouse 61 | 91.0 | 319 |

Coverage: 1904: 29 ha, 1908: 29 ha, 1950: 29 ha.

**Georeferencing.** 1908 is the base: grid north (along B St / Mendocino Av) is left on the sheets. Railroad Square (sheets 43 / 44: Wilson - Davis - Washington St) keeps its property lines (0.4-1.6 m); the courthouse blocks do not: Exchange and Hinton Av are gone (the square was reunited), 3rd St and B St south of 4th were widened (today's corners at B x 4th / B x 3rd give a block 3-4 m short both ways), A and Washington St lie under the mall, and 1st St was re-platted by the Phase I renewal. So sheet 34 is fitted on block 12 (B - Mendocino, 5th - 4th: four parcel corners, 1.2 m), sheet 35 is tied to sheet 34's 4th St corners with the plate scale measured on sheet 44, sheets 36 and 25 use the 3rd / 2nd St corners that survive and carry the rest of each sheet by group fits (capped `medium`; the strip south of 1st St `low`). The 1950 sheets are the 1908 plates with paste-over slips (SIFT, 598-1,167 inliers, 1.3-1.8 px). The Dec 1904 plates: sheets 24, 28, 29 are earlier states of the 1908 plates 43 / 44, 36, 25 (72-181 inliers, 1.0-1.6 px); sheet 25 (the 4th St business blocks) was redrawn after the earthquake and is fitted on its four block outlines tied to the same corners on the 1908 sheets 34 / 35 (0.3-1.2 m).

| sheet (key) | map year | fits | RMS / max (m) per fit | scale (m/px), rotation | footprints |
|---|---|---|---|---|---|
| 004_0024 | 1904 | registered onto 005_0043 (SIFT, 1.01 px) | (base fits) | | 97 |
| 004_0024b | 1904 | registered onto 005_0044 (SIFT, 1.23 px) | (base fits) | | 131 |
| 004_0025 | 1904 | 4 fit(s), 4 block zones | 12: 4 pts 0.45/0.60; 15: 4 pts 1.21/1.28; 13: 4 pts 0.39/0.49; 16: 4 pts 0.32/0.44 | 0.2051, -59.7 deg | 191 |
| 004_0028 | 1904 | registered onto 005_0036 (SIFT, 1.25 px) | (base fits) | | 179 |
| 004_0029 | 1904 | registered onto 005_0025 (SIFT, 1.64 px) | (base fits) | | 278 |
| 005_0025 | 1908 | 6 fit(s), 8 block zones | 301: 4 pts 2.22/2.37; 302: 4 pts 1.10/1.25; 303: 6 pts 0.99/1.48; 10: 10 pts 2.92/4.02; 1: 4 pts 2.05/2.85; 2: 10 pts 3.33/5.76 | 0.2000, -60.0 deg | 293 |
| 005_0034 | 1908 | 1 fit(s), 2 block zones | 12: 4 pts 1.19/1.62 | 0.2032, -59.5 deg | 57 |
| 005_0035 | 1908 | 1 fit(s), 2 block zones | 13: 2 pts 0.86/0.86 | 0.2051, -60.4 deg | 60 |
| 005_0036 | 1908 | 2 fit(s), 5 block zones | 3: 4 pts 1.76/2.29; 4: 6 pts 2.68/4.07 | 0.2042, -59.7 deg | 210 |
| 005_0043 | 1908 | 2 fit(s), 3 block zones | 26: 6 pts 0.74/0.80; 21: 4 pts 0.43/0.57 | 0.2020, -60.1 deg | 116 |
| 005_0044 | 1908 | 2 fit(s), 3 block zones | 27: 6 pts 1.60/2.30; 22: 4 pts 1.14/1.33 | 0.2057, -59.7 deg | 96 |
| 006_0025 | 1950 | registered onto 005_0025 (SIFT, 1.61 px) | (base fits) | | 187 |
| 006_0034 | 1950 | registered onto 005_0034 (SIFT, 1.46 px) | (base fits) | | 37 |
| 006_0035 | 1950 | registered onto 005_0035 (SIFT, 1.6 px) | (base fits) | | 53 |
| 006_0036 | 1950 | registered onto 005_0036 (SIFT, 1.77 px) | (base fits) | | 122 |
| 006_0043 | 1950 | registered onto 005_0043 (SIFT, 1.33 px) | (base fits) | | 56 |
| 006_0044 | 1950 | registered onto 005_0044 (SIFT, 1.6 px) | (base fits) | | 55 |

**apply_sanborn test.** 1904: 876 footprints, 671 matched on 1908, 15 standing; 1908: 832, 488 matched on 1950, 40 standing; 1950: 510, 77 standing; 977 vanished buildings emitted. With the coverage passed as a disaster polygon at 1906.29 (what the fire hook will do with the lead's earthquake outline), 530 buildings end in the earthquake, 326 of them rebuilt on the same lot (`sanborn_1904_burned_1906`), and 55 first mapped in 1908 start after it. With the clearances below, 122 of the 260 emitted inside `sr_urban_renewal_phase1` end in its years, 134 of 253 inside `sr_urban_renewal_mall` and 13 of 68 inside `sr_us101_viaduct` (the others inside those rings were already gone on an earlier map); 71 have nothing on their ground today and no clearance (default end).

**Limits / not done.** The 1904 map is before, the 1908 map after the earthquake - but apply_sanborn's `burned_core` rule treats every building mapped on both as rebuilt, which is right for the brick blocks around the square and wrong for frame houses that survived (most of sheets 28 / 29, 43 / 44): the lead's disaster polygon should cover the destroyed business district only. 1950 paste-over slips: pale fills partly missed (a missed building ends between 1908 and 1950 instead of at its clearance). Not traced: 5th - 7th St, the blocks east of E St and south of 1st St, Railroad Square west of Wilson St, the 1885-1893 editions.

## Vallejo (`vallejo_downtown`: Jul 1901, Mar 1919, Mar 1950)

Lower Georgia St and the old waterfront: Branciforte / Santa Clara / Sacramento / Marin St to Sonoma St, Florida St to Maine / Pennsylvania St, and the ferry slips on Mare Island Strait - most of it razed for the Marina Vista redevelopment.

| edition | LOC item | sheets used |
|---|---|---|
| Jul 1901 (35 sheets) | https://www.loc.gov/item/sanborn00905_003/ | 14 (= the 1919 plate 20) |
| Mar 1919 (43 sheets) | https://www.loc.gov/item/sanborn00905_004/ | 20, 21, 25, 26, 27, 28 (key on sheet 1) |
| 1919 corrected to Mar 1950 (53 sheets) | https://www.loc.gov/item/sanborn00905_005/ | 20, 21, 25, 26, 27, 28 |

The 1970 volume (`_006`) has no images.

| file | features | high / medium / low | materials | uses | area (1000 m2) | modern_overlap >= 0.5 |
|---|---|---|---|---|---|---|
| vallejo_downtown_1901 | 272 | 145 / 127 / 0 | frame 268, brick 2, iron 2 | dwelling 148, shed 120, warehouse 4 | 14.7 | 83 |
| vallejo_downtown_1919 | 1,288 | 785 / 503 / 0 | frame 1220, brick 60, stone 7, iron 1 | shed 507, dwelling 436, store 318, warehouse 27 | 104.3 | 488 |
| vallejo_downtown_1950 | 915 | 528 / 387 / 0 | frame 761, brick 81, concrete 50, iron 23 | dwelling 367, shed 284, store 205, warehouse 59 | 111.4 | 336 |

Coverage: 1901: 10 ha, 1919: 50 ha, 1950: 50 ha.

**Georeferencing - on the streets, not on parcels.** West of Sacramento St nothing of the 1919 lot pattern is left (superblocks, Mare Island Way, Virginia and York St vacated, Branciforte St gone), and elsewhere today's frontages are set back unevenly (7-12 m from the centreline at one crossing). The town grid itself survives: centrelines 146.3 m apart east-west and 109.7 m north-south (480 x 360 ft = blocks of 400 x 280 ft + the 80 ft streets printed on every sheet). So every block corner is an offset corner (`oc`: centreline crossing, extended where the street is gone, +- 40 ft): fits 0.3-1.3 m, sheets 20 / 21 as one group of six blocks each (0.9 m), sheets 26 / 27 per pair of blocks. Sheet 25 (the waterfront west of Branciforte St) is tied to the west corners of blocks 280 / 261 drawn at its east edge (0.7 m; the Ohio / Trinity / Kentucky St inset is not traced, the blue water tint is dropped); sheet 28 (York - Pennsylvania St) has the two York St corners of block 245 + the plate scale, because Maine St west of Sacramento St is realigned (capped `medium`). 1950 = the 1919 plates corrected (202-718 inliers, 1.4-1.9 px; the 1919 scan of sheet 26 has another resolution). Of the 1901 volume only sheet 14 is an earlier state of a 1919 plate (110 inliers); the other 1901 sheets were redrawn and are not traced. This is the "streets the Sanborn itself shows" method, not decision 34's corridor fill: inside the coverage no generated houses are needed.

| sheet (key) | map year | fits | RMS / max (m) per fit | scale (m/px), rotation | footprints |
|---|---|---|---|---|---|
| 003_0014 | 1901 | registered onto 004_0020 (SIFT, 1.54 px) | (base fits) | | 272 |
| 004_0020 | 1919 | 4 fit(s), 6 block zones | 346: 4 pts 0.76/0.90; 345: 18 pts 0.92/1.69; 323: 4 pts 0.57/0.79; 301: 4 pts 0.41/0.43 | 0.2052, -0.6 deg | 360 |
| 004_0021 | 1919 | 6 fit(s), 6 block zones | 347: 4 pts 0.34/0.46; 348: 4 pts 0.42/0.53; 324: 4 pts 0.58/0.66; 325: 4 pts 1.26/1.62; 302: 4 pts 0.84/1.16; 303: 4 pts 1.18/1.35 | 0.2061, -0.3 deg | 280 |
| 004_0025 | 1919 | 1 fit(s), 1 block zones | waterfront: 3 pts 0.66/0.89 | 0.1970, 0.2 deg | 20 |
| 004_0026 | 1919 | 4 fit(s), 4 block zones | 281: 4 pts 0.44/0.56; 280: 6 pts 0.41/0.61; 262: 4 pts 0.92/1.10; 261: 6 pts 1.03/1.22 | 0.1518, -0.9 deg | 217 |
| 004_0027 | 1919 | 4 fit(s), 4 block zones | 282: 4 pts 0.93/1.25; 283: 4 pts 0.36/0.50; 263: 4 pts 0.68/0.96; 264: 4 pts 1.00/1.19 | 0.2027, -0.8 deg | 221 |
| 004_0028 | 1919 | 1 fit(s), 5 block zones | 245: 2 pts 0.45/0.45 | 0.2052, -0.9 deg | 190 |
| 005_0020 | 1950 | registered onto 004_0020 (SIFT, 1.75 px) | (base fits) | | 310 |
| 005_0021 | 1950 | registered onto 004_0021 (SIFT, 1.33 px) | (base fits) | | 200 |
| 005_0025 | 1950 | registered onto 004_0025 (SIFT, 1.46 px) | (base fits) | | 11 |
| 005_0026 | 1950 | registered onto 004_0026 (SIFT, 1.41 px) | (base fits) | | 134 |
| 005_0027 | 1950 | registered onto 004_0027 (SIFT, 1.64 px) | (base fits) | | 107 |
| 005_0028 | 1950 | registered onto 004_0028 (SIFT, 1.89 px) | (base fits) | | 153 |

**apply_sanborn test.** 1901: 272 footprints, 218 matched on 1919, 8 standing; 1919: 1,288, 864 matched on 1950, 134 standing; 1950: 915, 231 standing; 1,147 vanished buildings emitted; 552 lie inside `val_marina_vista`, 331 of them ending in its years (1962-65.3) and 221 already gone on an earlier map; 315 outside it have nothing on their ground today and end at the default (1960 / 1965).

**Limits / not done.** 1950 slips: pale fills partly missed. Not traced: the 1901 downtown sheets (redrawn plates: they need their own control), Georgia St east of Sonoma St, South Vallejo, the 1886 / 1889 editions. The I-80 and Sonoma Blvd widenings have no dated source and no row.

## Napa (`napa_downtown`: Jun 1901, Oct 1910)

Main St and the river front from Clinton St to 5th St, and the blocks west to Franklin St (Pearl - Division St): the downtown that the 1970s redevelopment (Dwight Murray Plaza, the department-store superblock) and the flood project thinned out.

| edition | LOC item | sheets used |
|---|---|---|
| Jun 1901 (27 sheets) | https://www.loc.gov/item/sanborn00707_003/ | 10, 17 (Main St; key on sheet 1) |
| Oct 1910 (35 sheets) | https://www.loc.gov/item/sanborn00707_004/ | 13, 14, 20, 21 (key on sheet 1) |

The 1924, 1949 and 1970 volumes (`_005`-`_007`) have no images, so 1910 is the last map year.

| file | features | high / medium / low | materials | uses | area (1000 m2) | modern_overlap >= 0.5 |
|---|---|---|---|---|---|---|
| napa_downtown_1901 | 244 | 0 / 112 / 132 | frame 190, brick 36, iron 14, unknown 3, stone 1 | store 137, shed 99, warehouse 5, other 3 | 26.3 | 93 |
| napa_downtown_1910 | 696 | 0 / 668 / 28 | frame 641, brick 43, iron 11, stone 1 | shed 310, store 209, dwelling 150, warehouse 27 | 67.9 | 328 |

Coverage: 1901: 9 ha, 1910: 30 ha.

**Georeferencing.** 1910 (sheet-up = north-west along Main St): the grid west of Main St is fitted per sheet as one group on offset corners (60 ft streets, as printed), because parcel corners gave worse fits (the property lines moved with the redevelopment): 2.3 m (sheet 13) and 2.9 m (sheet 20) RMS, up to 5.7 m at single corners - `medium`. Main St (sheets 14 / 21): the west side on its Brown / Main St corners (0.7-2.0 m), the river side on its Main St corners (0.5-1.4 m; the block lines end at Napa Creek), the east bank (Palace Hotel, Enterprise mill, glove factory) carried across the river by the Main St fit (`low`). 1901 is another drawing (Main St horizontal) and has its own control: the west-side blocks on four corners (1.0-2.6 m), the river side on two Main St corners; its scan resolution differs (0.200-0.213 m/px), so the 2-corner blocks are `low`. 68 % of the 1901 footprints are found again on the 1910 map.

| sheet (key) | map year | fits | RMS / max (m) per fit | scale (m/px), rotation | footprints |
|---|---|---|---|---|---|
| 003_0010 | 1901 | 4 fit(s), 4 block zones | 39: 3 pts 0.54/0.66; 24: 2 pts 0.60/0.60; 40: 2 pts 0.36/0.36; 23: 2 pts 1.91/1.91 | 0.2101, -56.7 deg | 140 |
| 003_0017 | 1901 | 6 fit(s), 6 block zones | 70: 4 pts 1.08/1.29; 81: 4 pts 1.01/1.68; 99: 4 pts 2.62/3.52; 71: 2 pts 0.22/0.22; 80: 2 pts 1.15/1.15; 100: 2 pts 1.69/1.69 | 0.2091, -57.6 deg | 104 |
| 004_0013 | 1910 | 2 fit(s), 9 block zones | 207: 34 pts 2.31/4.57; 250: 4 pts 1.08/1.48 | 0.2052, 33.6 deg | 211 |
| 004_0014 | 1910 | 2 fit(s), 6 block zones | 210: 7 pts 1.66/2.87; 211: 5 pts 0.47/0.76 | 0.2026, 32.8 deg | 165 |
| 004_0020 | 1910 | 1 fit(s), 10 block zones | 283: 36 pts 2.85/5.72 | 0.2044, 32.9 deg | 204 |
| 004_0021 | 1910 | 3 fit(s), 7 block zones | 286: 4 pts 0.69/1.09; 320: 11 pts 2.02/4.01; 287: 5 pts 1.36/1.70 | 0.2037, 32.0 deg | 116 |

**apply_sanborn test.** 1901: 244 footprints (39 awning strips dropped), 167 matched on 1910, 17 standing; 1910: 696, 13 standing; 755 vanished buildings emitted; 38 of the 43 inside `napa_town_center` end in its years; 310 have nothing on their ground today and end at the default 1960.

**Limits / not done.** No map after 1910: what was built 1910-1970 and is gone is missing, and a 1910 building with nothing on its ground today ends at the default 1960. 1901: only the two Main St sheets (sheets 9 / 16 = the 1910 sheets 13 / 20 are not traced). Not traced: Spanish Town east of West St, the tannery, East Napa. The flood-project removals along the river (2000s) have no dated source and no row.

## Petaluma (`petaluma_downtown`: Nov 1910)

The iron-front blocks (Main St = Petaluma Blvd N, Kentucky St, Western Av), McNear's warehouses on the river, and the blocks west to Liberty / Keokuk St.

| edition | LOC item | sheets used |
|---|---|---|
| Nov 1910 (31 sheets) | https://www.loc.gov/item/sanborn00756_005/ | 6, 7, 9 (key on sheet 1) |

Nov 1906 (`_004`) is an earlier state of the same plates with other sheet numbers (1910 sheet 6 = 1906 sheet 10, 251 inliers); it is not traced. 1923 / 1949 (`_006`, `_007`) have no images.

| file | features | high / medium / low | materials | uses | area (1000 m2) | modern_overlap >= 0.5 |
|---|---|---|---|---|---|---|
| petaluma_downtown_1910 | 462 | 246 / 149 / 67 | frame 397, brick 61, iron 4 | shed 197, store 149, dwelling 105, warehouse 11 | 55.9 | 244 |

Coverage: 1910: 21 ha.

**Georeferencing.** Petaluma's property lines survive: each block on its own four parcel corners (0.4-1.3 m; Kentucky, Keller and Liberty St are not parallel to Main St, and the streets between the blocks are not to scale). The river side of Main St: north of Washington St by block 27's fit across the street, south of it (block 18, McNear's) by the Main x Washington corner + the scale and rotation of block 28 (`medium`).

| sheet (key) | map year | fits | RMS / max (m) per fit | scale (m/px), rotation | footprints |
|---|---|---|---|---|---|
| 005_0006 | 1910 | 4 fit(s), 5 block zones | 27: 4 pts 0.60/0.70; 36: 4 pts 1.27/1.39; 46: 4 pts 1.04/1.15; 26: 4 pts 1.21/1.58 | 0.2044, -68.3 deg | 142 |
| 005_0007 | 1910 | 2 fit(s), 2 block zones | 28: 3 pts 1.09/1.35; 18: 1 pts 0.00/0.00 | 0.2065, -67.2 deg | 114 |
| 005_0009 | 1910 | 3 fit(s), 6 block zones | 37: 4 pts 0.42/0.53; 47: 4 pts 0.39/0.50; 57: 6 pts 0.35/0.65 | 0.2042, -67.2 deg | 206 |

**apply_sanborn test.** 1910: 462 footprints, 63 standing (the iron fronts), 399 vanished buildings emitted.

**Limits / not done.** One map year. Not traced: sheet 10 (south of Western Av: Masonic hall block, City Hall, library - blocks at an angle), the east bank (Golden Eagle mill, the railway), the 1906 edition, the hill west of Liberty St.

## Clearances added (`data/manual/redevelopment_areas.csv`)

| area_id | years | what |
|---|---|---|
| `val_marina_vista` | 1962-1965.3 | Marina Vista redevelopment (adopted 1960; 600 structures, 125 acres, 24 blocks; all cleared on the aerial view of May 1965) - ring = the project boundary of the 1967 site plan (ESA 2024 report, figs. 9 / 10) on the street grid: Florida - Butte - Carolina - Branciforte - Capitol - Sacramento - York - Marin - Maryland St - the strait |
| `sr_urban_renewal_phase1` | 1961.5-1965 | Santa Rosa urban renewal Phase I: 3rd St - Sonoma Av, Santa Rosa Av - E St (40 acres); dates LOW |
| `sr_urban_renewal_mall` | 1972-1978 | west of B St to US 101, 1st - 6th St (ordinance 1439 of 10 Mar 1970; wrecking from 1972; Santa Rosa Plaza opened 1983) |
| `sr_us101_viaduct` | 1966-1968 | the elevated US 101 of 1968 (surface highway opened 20 May 1949); ring = today's freeway footprint |
| `napa_town_center` | 1970-1973.5 | Coombs - Brown St, Pearl - First St (33-block redevelopment area of 1969; Migliavacca Building razed 1973; plaza dedicated 1974) |

The 1906 Santa Rosa earthquake is NOT entered here (the lead's fire / disaster rows).
