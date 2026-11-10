# Sanborn tracing: Santa Cruz and Watsonville

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

## Santa Cruz (`santa_cruz_downtown`: Jul 1892, 1905; `santa_cruz_beach`: 1905)

Pacific Avenue from Mission / Water St to Laurel St with the blocks west to Center St and east to Front St and the river: the later Pacific Garden Mall blocks (hit on 17 Oct 1989), the courthouse block and the Front St Chinatown that burned on 14 April 1894 (1892 edition). `santa_cruz_beach` is the beach flat on the 1905 sheet 28: Tent City, the cottages between Cliff St and Riverside Av, and the Neptune Casino, baths and pleasure wharf of 1904 (burned 22 June 1906; today's Casino and Plunge of 1907 stand on the site).

| edition | LOC item | sheets used |
|---|---|---|
| Jul 1892 (30 sheets) | https://www.loc.gov/item/sanborn00833_003/ | 4, 6 (key on sheet 1) |
| 1905 (73 sheets + key) | https://www.loc.gov/item/sanborn00833_004/ | 9, 14, 15, 16, 20 (downtown), 28 (beach; key map `0000`) |

The 1928, 1950 and 1971 volumes (`_005`-`_010`) have no images, so 1905 is the last map year.

| file | features | high / medium / low | materials | uses | area (1000 m2) | modern_overlap >= 0.5 |
|---|---|---|---|---|---|---|
| santa_cruz_beach_1905 | 66 | 0 / 57 / 9 | frame 66 | dwelling 34, shed 24, store 5, warehouse 3 | 8.0 | 19 |
| santa_cruz_downtown_1892 | 476 | 81 / 122 / 273 | frame 428, brick 24, iron 24 | shed 238, store 226, warehouse 12 | 42.3 | 324 |
| santa_cruz_downtown_1905 | 841 | 511 / 330 / 0 | frame 764, iron 33, brick 27, unknown 9, adobe 6, stone 2 | shed 395, store 322, dwelling 91, warehouse 24, other 9 | 80.5 | 502 |

Coverage: 1892: 15 ha, 1905: 34 ha.

**Georeferencing.** 1905 (north up, Pacific Av vertical): parcel corners; sheets 14 and 20 fit to 0.4-1.1 m (Cedar St was a 20 ft lane north of Elm St - 'Vine St' north of Locust St - and is not used there), sheet 15 (Cooper St - Soquel Av, Pacific Av - Front St and the flat east of Front St) as one group 2.0 m, sheet 9's two pieces each on two corners + the plate scale (the flatiron between Pacific Av and Front St on its Cooper St corners, block 6 on its Locust St corners - Pacific Av is not to scale between them), sheet 16 (Cathcart - Laurel St) on the Cathcart St corners + scale (`medium`). 1892 is another drawing: sheet 6 (Pacific Av horizontal) on parcel corners (0.7-0.9 m west of Pacific Av; the courthouse block 13 has 3.5 m RMS on four corners, its Soquel Av corners 4.6 m off - `low`), sheet 4 like the 1905 sheet 9, with the Front St Chinatown carried across Front St by the flatiron's fit (`low`). 72 % of the 1892 footprints are found again on the 1905 map. The beach sheet 28 (sheet-left = north): blocks 227 / 229 west of Cliff St on five parcel corners (1.4 m), the Tent City block on its two 2nd St corners + the plate scale, the casino strip beyond the Southern Pacific track by the fit of the blocks across it (`low`); today's Beach St frontage is 4-5 m off the 1905 Esplanade line and is not used.

| sheet (key) | map year | fits | RMS / max (m) per fit | scale (m/px), rotation | footprints |
|---|---|---|---|---|---|
| 004_0028 | 1905 | 3 fit(s), 4 block zones | 231: 2 pts 0.02/0.02; 229: 5 pts 1.37/2.44; 232: 5 pts 1.65/2.91 | 0.2031, -68.7 deg | 66 |
| 003_0004 | 1892 | 2 fit(s), 3 block zones | 6: 2 pts 0.38/0.38; 4: 2 pts 0.03/0.03 | 0.2052, 14.2 deg | 134 |
| 003_0006 | 1892 | 4 fit(s), 4 block zones | 13: 4 pts 3.54/4.71; 7: 2 pts 0.74/0.74; 12: 2 pts 0.80/0.80; 16: 4 pts 0.92/1.14 | 0.2081, -76.4 deg | 342 |
| 004_0009 | 1905 | 4 fit(s), 4 block zones | 6: 2 pts 1.02/1.02; 4: 2 pts 0.55/0.55; 196: 4 pts 1.24/1.60; 197: 4 pts 0.54/0.89 | 0.2038, 13.1 deg | 179 |
| 004_0014 | 1905 | 2 fit(s), 3 block zones | 7: 8 pts 1.14/2.16; 16: 4 pts 0.66/0.92 | 0.2057, 14.6 deg | 252 |
| 004_0015 | 1905 | 1 fit(s), 5 block zones | 13: 6 pts 2.03/3.17 | 0.2037, 14.5 deg | 165 |
| 004_0016 | 1905 | 1 fit(s), 3 block zones | 19: 4 pts 2.45/3.31 | 0.2071, 13.4 deg | 71 |
| 004_0020 | 1905 | 3 fit(s), 4 block zones | 192: 4 pts 0.40/0.64; 193: 4 pts 0.74/1.02; 194: 4 pts 0.99/1.34 | 0.2033, 12.3 deg | 174 |

**apply_sanborn test.** 1892: 476 footprints (23 awning strips dropped), 341 matched on 1905; 1905: 841; 976 vanished buildings emitted (135 only on the 1892 map); 18 of the 38 inside `sc_san_lorenzo_park_plaza` end in its years, 264 end at the default 1960. 'Standing' could not be measured in the test: the Santa Cruz parcel layer carries no year, so every footprint of today was dated 1950 (the real stage has the years); `modern_overlap >= 0.5` in the tables is the proxy. Beach: 66 footprints, 66 emitted (the casino complex ends when the real stage finds today's 1907 building on its ground, else at the default 1960 - a dated row for the fire of 22 June 1906 is a lead / fires item).

**Limits / not done.** The 1894 fire: a building on the 1892 map that is gone in 1905 ends at a hashed year between the maps (1895-1903); the fire hook would need the burned blocks (Pacific Av / Cooper St / Front St) at 1894.29 - not entered here. No map after 1905: the 1989 losses are buildings of today's data or of the lead's disaster rows, not of these files. Not traced: the rest of the beach flat (1905 sheets 22-27: almost empty lots in 1905), Mission Hill, the east side, the 1892 sheets 5, 7, 8, the 1886 / 1888 editions.

## Watsonville (`watsonville_downtown`: Dec 1920, Dec 1962)

Main St from Lake Av to 1st St with the plaza, Rodriguez St to Union / Alexander St.

| edition | LOC item | sheets used |
|---|---|---|
| Dec 1920 (32 sheets) | https://www.loc.gov/item/sanborn00921_006/ | 18, 24 (key on sheet 1) |
| 1920 corrected to Dec 1962 (35 sheets) | https://www.loc.gov/item/sanborn00921_007/ | 18, 24 |

1902 and 1908 (`_004`, `_005`) have images and are not traced. The 1902-1920 volumes use LOC's older file names (`sb000010` = sheet 1): the tool renames them, keys stay `<volume>_<sheet>`; their 25 % scans are larger (0.155 m/px).

| file | features | high / medium / low | materials | uses | area (1000 m2) | modern_overlap >= 0.5 |
|---|---|---|---|---|---|---|
| watsonville_downtown_1920 | 575 | 201 / 187 / 187 | frame 507, brick 40, stone 23, iron 4, concrete 1 | store 290, shed 266, dwelling 12, warehouse 7 | 50.1 | 245 |
| watsonville_downtown_1962 | 162 | 66 / 33 / 63 | frame 79, concrete 49, brick 21, iron 13 | store 118, shed 40, warehouse 3, dwelling 1 | 45.9 | 74 |

Coverage: 1920: 16 ha, 1962: 16 ha.

**Georeferencing.** East of Main St the property lines survive: blocks 97 (Peck - Maple), 100 and 103 on parcel corners (0.6-1.0 m), block 92 (Lake - 3rd St) on its Main St corners + block 97. West of Main St, Rodriguez St is realigned (and '3rd St' is today's Beach St): blocks 72, 73 and 74 each on their two Main St corners + the plate scale (0.4-2.0 m at those corners; `medium` / `low`). The 1962 sheets are the 1920 plates corrected (204 / 369 inliers, 1.5 px of the 1920 scan).

| sheet (key) | map year | fits | RMS / max (m) per fit | scale (m/px), rotation | footprints |
|---|---|---|---|---|---|
| 006_0018 | 1920 | 4 fit(s), 5 block zones | 72: 2 pts 0.42/0.42; 73: 2 pts 2.03/2.03; 92: 6 pts 0.70/0.99; 97: 4 pts 0.59/0.89 | 0.1552, 42.1 deg | 365 |
| 006_0024 | 1920 | 3 fit(s), 3 block zones | 74: 2 pts 1.46/1.46; 100: 4 pts 1.03/1.40; 103: 6 pts 0.95/1.37 | 0.1536, 42.8 deg | 210 |
| 007_0018 | 1962 | registered onto 006_0018 (SIFT, 1.54 px) | (base fits) | | 92 |
| 007_0024 | 1962 | registered onto 006_0024 (SIFT, 1.56 px) | (base fits) | | 70 |

**apply_sanborn test.** 1920: 575 footprints, 271 matched on 1962; 1962: 162 (large concrete and brick blocks, parking lots), 58 standing; 407 vanished buildings emitted. (The test dates today's buildings 1950 where the parcel layer has no year, so no 1920 footprint can be recognised as standing.)

**Limits / not done.** Only two sheets. No clearance row: no dated source for a Watsonville renewal project was found; the 1989 earthquake losses belong to the lead's disaster rows (a 1962 footprint with nothing on its ground today ends at the default 1977). Not traced: 1902 / 1908, the packing-house district along Walker St, Pajaro.

## Clearance added (`data/manual/redevelopment_areas.csv`)

| area_id | years | what |
|---|---|---|
| `sc_san_lorenzo_park_plaza` | 1957-1962 | San Lorenzo Park redevelopment project (Project Area No. 1 after the flood of Dec 1955; plans approved Sep 1956, developers called Dec 1959, agency closed Oct 1970) - ring = the west-bank part on the 1905 sheet 15 (Front St to the river, Cooper St - Soquel Av); dates ESTIMATED |

The 1989 earthquake is NOT entered here (the lead's disaster rows).
