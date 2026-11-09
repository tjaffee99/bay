# Sanborn tracing: Palo Alto (downtown 1901 / 1904 / 1908) and Mayfield (1904 / 1908)

Real historical building footprints of downtown Palo Alto (University Av from Alma St to Cowper St, Palo Alto Av ->
Channing Av) and of the old town of Mayfield (Lincoln Av = today's California Av, from El Camino Real to the tracks;
annexed by Palo Alto in 1925), traced from the Library of Congress scans of the Sanborn Map Co. *Insurance Maps of Palo
Alto* and *of Mayfield, Santa Clara Co., California* (public domain: "Library of Congress, Geography and Map Division,
Sanborn Maps Collection"). Built by `pipeline/sanborn_trace_peninsula.py` (`... palo_alto ...` / `... mayfield ...`);
method, schema and confidence rules as in `README_san_mateo.md` (and `README_oakland.md` / `README_san_jose.md`).
Control: `control/palo_alto/`, `control/mayfield/`.

## Files

| file | content |
|---|---|
| `palo_alto_downtown_1901.geojson` | August 1901 edition, sheets 5, 6, 11, 12 (registered onto the 1904 plates) |
| `palo_alto_downtown_1904.geojson` | June 1904 edition, sheets 7, 8, 12, 13, 14, 15 (registered onto the 1908 plates) |
| `palo_alto_downtown_1908.geojson` | May 1908 edition, sheets 11, 12, 16, 17, 18, 19 (fitted to today's parcels) |
| `palo_alto_downtown_coverage.geojson` | one polygon per map year: the block zones of the traced sheets (clipped to each scan) + 12 m |
| `palo_alto_mayfield_1904.geojson` | Mayfield, June 1904, sheets 2, 3, 4 (sheet 4's two strips registered separately) |
| `palo_alto_mayfield_1908.geojson` | Mayfield, May 1908, sheets 3, 4, 5 |
| `palo_alto_mayfield_coverage.geojson` | one polygon per Mayfield map year |
| `control/palo_alto/`, `control/mayfield/` | control per sheet (block specs / fits, or the SIFT registration onto the later plate: `registered_to`, `T`, `reg_rms_px`; Mayfield `004_0004a` / `004_0004b` = the two strips of 1904 sheet 4 with their `src_box` / `dst_box` / `valid_px`), `aliases.json`, `labels.json` (14 + 5 names), `storeys.json` (31 + 7 storeys read), `areas.json` |

The area prefix `palo_alto` (both areas) is in `region_predecessors.REGION_SANBORN`. The 1924 and 1924-Dec 1949 Palo
Alto volumes (`sanborn00747_006`, `_007`) and the 1925 / 1925-Apr 1945 Mayfield volumes (`sanborn00677_006`, `_007`) are
catalogued without images (copyright period), so 1908 is the last map year for both.

Feature properties as in `README_san_mateo.md`; storeys read for every masonry building >= 120 m2 (Palo Alto: 1-2
storeys - the Mariposa Lodgings, the D.G. / clothing and drugs / hall blocks on University Av were 2, the banks, City
Hall, library, Times Publishing Co. and the concrete garages 1), defaults elsewhere (frame dwellings 1 storey under
110 m2, 2 up to 300 m2). Plate scale for 2-corner fits: Palo Alto 0.2045 m/px, Mayfield 0.2030.

## Counts

| file | features | high / medium / low | materials | uses | area (1000 m2) | modern_overlap >= 0.5 |
|---|---|---|---|---|---|---|
| palo_alto_downtown_1901 | 533 | 533 / 0 / 0 | frame 508, stone 15, brick 8, iron 2 | shed 237, dwelling 175, store 112, warehouse 7, hotel 1, bank 1 | 35.7 | 352 |
| palo_alto_downtown_1904 | 888 | 887 / 1 / 0 | frame 852, iron 19, brick 17 | shed 390, dwelling 355, store 126, warehouse 13, church 1, library 1, hotel 1, bank 1 | 64.5 | 557 |
| palo_alto_downtown_1908 | 1,102 | 1102 / 0 / 0 | frame 1043, iron 31, brick 18, stone 10 | shed 480, dwelling 435, store 157, warehouse 22, factory 2, bank 2, church 1, other 1, library 1, hotel 1 | 82.2 | 692 |

| file | features | high / medium / low | materials | uses | area (1000 m2) | modern_overlap >= 0.5 |
|---|---|---|---|---|---|---|
| palo_alto_mayfield_1904 | 486 | 129 / 251 / 106 | frame 469, brick 6, iron 6, stone 5 | shed 269, dwelling 135, store 73, warehouse 8, factory 1 | 24.7 | 226 |
| palo_alto_mayfield_1908 | 461 | 116 / 238 / 107 | frame 443, stone 8, brick 6, iron 4 | shed 247, dwelling 129, store 73, warehouse 10, bank 1, factory 1 | 23.8 | 232 |

Coverage: Palo Alto 39 ha (1901), 60 ha (1904, 1908); Mayfield 27 ha (1904, 1908).

## Sources

| edition | LOC item | sheets used |
|---|---|---|
| Palo Alto, May 1908 (23 sheets) | https://www.loc.gov/item/sanborn00747_005/ | 11, 12, 16, 17, 18, 19 (key map 1) |
| Palo Alto, June 1904 (17 sheets) | https://www.loc.gov/item/sanborn00747_004/ | 7, 8, 12, 13, 14, 15 (key map 0000) |
| Palo Alto, August 1901 (14 sheets) | https://www.loc.gov/item/sanborn00747_003/ | 5, 6, 11, 12 |
| Mayfield, May 1908 (5 sheets) | https://www.loc.gov/item/sanborn00677_005/ | 3, 4, 5 (key map 1) |
| Mayfield, June 1904 (4 sheets) | https://www.loc.gov/item/sanborn00677_004/ | 2, 3, 4 |

Control: Overture road centrelines (release 2026-10-21.0, `roads_local` + `roads_region`, ODbL), Santa Clara County
parcels ("Parcels Public View", April 2026, `data/raw/region_years/santa_clara_county`) as property lines, Overture
buildings for `modern_overlap`.

**OpenHistoricalMap** (CC0, Overpass `https://overpass-api.openhistoricalmap.org/api/interpreter`, queried 2026-11-09,
`data/raw/ohm/ohm_peninsula_buildings.json`): the box 37.40-37.47 N, 122.20-122.10 W holds 4,633 OHM buildings, but
2,969 are the Stanford campus import (`import=LSJUbldgs`) and the ~650 ways tagged as traced from the 1888-1908
Sanborn maps are in **Menlo Park** (Santa Cruz Av / El Camino / Middlefield, north of San Francisquito Creek), not Palo
Alto; inside downtown Palo Alto OHM has 24 buildings (USGS 1890 map, a few dated landmarks) and none in Mayfield. So
nothing was reused here; the Menlo Park tracings could be imported separately (there is no `menlo_park` prefix in
`REGION_SANBORN`).

## Method

* **1908 = the georeferenced base.** All six Palo Alto 1908 sheets draw two columns x four rows of blocks with the
  streets close to scale; every block has four property corners on today's parcels (Alma, High, Emerson, Ramona,
  Bryant, Waverley, Kipling, Cowper St x Palo Alto Av -> Channing Av) and fits to 0.1-1.3 m. The grid's north (along
  University Av toward Middlefield Rd, NE) is up on the sheets.
* **1904 and 1901 = the same engraved plates.** Sanborn corrected the plates between editions: each 1904 sheet was
  matched to the 1908 sheets by SIFT (the right partner has 260-450 RANSAC inliers, transform scale 0.995-1.004,
  rotation < 0.35 deg, shift < 25 px) and registered onto it (1.30-1.45 px = 0.27-0.30 m); the 1901 sheets likewise onto
  the 1904 ones (1.18-1.44 px). They inherit the 1908 block fits. 1904 sheets 12 and 15 have no 1901 counterpart
  (that ground was not mapped in 1901). Of the 1904 buildings > 40 m2, 96 % are found on the 1908 map (>= 40 % of their
  area covered), i.e. the registration and extraction agree between editions.
* **Mayfield 1908**: Lincoln Av is drawn horizontally (grid north = right). The El Camino and Lincoln / California Av
  property lines moved since (both widened): block fits 1-2.6 m, the block north of Lincoln (44, College Av -> California
  Av) 4 m by its group fit - `medium`. Sheet 4 (Birch St -> the tracks) is tied to sheet 3, which draws Birch St's east
  side: four tie corners on sheet 3's fits of blocks 56 / 69 (1.7 m); sheet 5's lower strip (Birch -> 3rd St, Grant ->
  Sheridan Av) has a single Birch St corner + the plate scale and rotation priors (`low`). Mayfield 1904 is the 1908
  plates' earlier state (SIFT 1.35-1.9 px); its sheet 4 holds the two strips of 1908 sheet 5 in the opposite order, so
  each strip was registered separately (`register_region`). 93 % of the 1904 buildings > 40 m2 are on the 1908 map.

## Georeferencing per sheet

| sheet (key) | map year | fits | RMS / max (m) per fit | scale (m/px), rotation | footprints |
|---|---|---|---|---|---|
| 003_0005 | 1901 | registered onto 004_0007 (SIFT, 1.38 px) | (base fits) | | 139 |
| 003_0006 | 1901 | registered onto 004_0008 (SIFT, 1.23 px) | (base fits) | | 92 |
| 003_0011 | 1901 | registered onto 004_0013 (SIFT, 1.18 px) | (base fits) | | 136 |
| 003_0012 | 1901 | registered onto 004_0014 (SIFT, 1.44 px) | (base fits) | | 166 |
| 004_0007 | 1904 | registered onto 005_0011 (SIFT, 1.36 px) | (base fits) | | 189 |
| 004_0008 | 1904 | registered onto 005_0012 (SIFT, 1.44 px) | (base fits) | | 135 |
| 004_0012 | 1904 | registered onto 005_0016 (SIFT, 1.34 px) | (base fits) | | 90 |
| 004_0013 | 1904 | registered onto 005_0017 (SIFT, 1.3 px) | (base fits) | | 169 |
| 004_0014 | 1904 | registered onto 005_0018 (SIFT, 1.45 px) | (base fits) | | 191 |
| 004_0015 | 1904 | registered onto 005_0019 (SIFT, 1.4 px) | (base fits) | | 114 |
| 005_0011 | 1908 | 7 fit(s), 7 block zones | 33: 4 pts 0.48/0.60; 34: 4 pts 1.19/1.41; 31: 4 pts 0.81/0.98; 30: 4 pts 0.47/0.62; 19: 4 pts 0.34/0.43; 35: 4 pts 0.58/0.68 ... | 0.2042, -37.6 deg | 209 |
| 005_0012 | 1908 | 5 fit(s), 5 block zones | 29: 4 pts 0.80/1.11; 28: 4 pts 0.21/0.25; 21: 4 pts 1.31/1.73; 36: 4 pts 0.65/0.89; 22: 4 pts 0.90/0.98 | 0.2029, -37.5 deg | 166 |
| 005_0016 | 1908 | 6 fit(s), 6 block zones | 45: 4 pts 1.21/1.26; 15: 4 pts 0.47/0.58; 147: 4 pts 0.11/0.14; 2: 4 pts 0.66/0.86; 16: 10 pts 1.15/1.51; 1: 10 pts 0.80/1.29 | 0.2068, -37.7 deg | 136 |
| 005_0017 | 1908 | 8 fit(s), 8 block zones | 46: 4 pts 0.24/0.28; 47: 4 pts 0.68/0.90; 14: 4 pts 0.66/0.80; 13: 4 pts 0.79/0.89; 48: 4 pts 0.79/0.97; 49: 4 pts 0.54/0.66 ... | 0.2042, -38.0 deg | 195 |
| 005_0018 | 1908 | 8 fit(s), 8 block zones | 51: 4 pts 0.60/0.73; 52: 4 pts 0.85/1.17; 12: 4 pts 0.45/0.61; 11: 4 pts 0.23/0.30; 53: 4 pts 0.34/0.42; 60: 4 pts 0.28/0.37 ... | 0.2048, -37.9 deg | 237 |
| 005_0019 | 1908 | 8 fit(s), 8 block zones | 66: 4 pts 1.00/1.12; 67: 4 pts 0.57/0.68; 10: 4 pts 0.29/0.36; 9: 4 pts 0.11/0.14; 7: 4 pts 0.25/0.30; 68: 4 pts 0.21/0.24 ... | 0.2068, -37.9 deg | 159 |

| sheet (key) | map year | fits | RMS / max (m) per fit | scale (m/px), rotation | footprints |
|---|---|---|---|---|---|
| 004_0002 | 1904 | registered onto 005_0003 (SIFT, 1.9 px) | (base fits) | | 268 |
| 004_0003 | 1904 | registered onto 005_0004 (SIFT, 1.35 px) | (base fits) | | 99 |
| 004_0004a | 1904 | registered onto 005_0005 (SIFT, 1.66 px) | (base fits) | | 105 |
| 004_0004b | 1904 | registered onto 005_0005 (SIFT, 1.91 px) | (base fits) | | 14 |
| 005_0003 | 1908 | 5 fit(s), 5 block zones | 55: 4 pts 2.56/2.80; 56: 4 pts 2.51/3.28; 68: 4 pts 1.99/2.15; 69: 4 pts 0.98/1.05; 44: 10 pts 3.97/5.61 | 0.1994, 57.1 deg | 262 |
| 005_0004 | 1908 | 1 fit(s), 5 block zones | 57: 4 pts 1.72/2.89 | 0.2020, 57.1 deg | 90 |
| 005_0005 | 1908 | 5 fit(s), 6 block zones | 81: 4 pts 0.66/1.07; 82: 4 pts 1.48/1.70; 94: 6 pts 1.26/2.06; 95: 6 pts 1.37/1.67; 83: 1 pts 0.00/0.00 | 0.2030, 57.2 deg | 109 |

### Findings (streets)

* Palo Alto 1901-08: "Margarita (Kipling)" = Kipling St, "Gilman (Florence)" = Gilman St, "Waverly" = Waverley St; the
  grid and the property lines of 1908 survive almost everywhere (most block fits < 1 m).
* Mayfield: **Lincoln Av = California Av**, **Palo Alto Av = College Av** (182-196 m north of California Av at El
  Camino), **County Road / Main St = El Camino Real**, the unnamed street at ~195 m = **Ash St**, then **Birch St**.
  Mayfield's **3rd St** (east of Birch St) is not today's Park Blvd (70 m apart) and **Washington Av** (south of
  Sheridan) does not meet Ash / Birch St today (Page Mill Rd / Oregon Expressway) - neither is used as control.
  At Birch St x Grant Av the parcels are re-platted (one large parcel): those corners are dropped.

## Not done / open items

* Palo Alto 1908 sheets 2-10, 13-15, 20-23 (Professorville south of Channing, Crescent Park, University Park east of
  Cowper, College Terrace, the Stanford sheets) and the matching 1901 / 1904 sheets; the 1895 / 1897 editions
  (`sanborn00747_001`, `_002`).
* Mayfield: sheet 2 of 1908 (College Terrace / Stanford side of El Camino, 1904 sheet 1) and the depot / lumber yard
  strip along the tracks; the 1884-1894 Mayfield editions (`sanborn00677_001`-`_003`).
* No buildings after 1908: everything built 1908-1925 and gone before today is missing (no later images).
* No tracks traced (the S.P. main line is today's Caltrain right of way).
* Storeys read only for masonry buildings; names for 19 buildings.

## Reproduce

```
python pipeline/sanborn_trace_peninsula.py palo_alto all     # fetch + georef (1908, then the registered 1904 / 1901) + extract + assemble + check
python pipeline/sanborn_trace_peninsula.py mayfield all
python pipeline/sanborn_trace_peninsula.py palo_alto tables  # the README tables
```
