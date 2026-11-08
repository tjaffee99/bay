# Sanborn tracing: downtown San José (1915, 1950)

Real historical building footprints of downtown San José, the fabric cleared for Park Center Plaza, the plaza /
Fairmont / convention-centre blocks, SR 87 (Guadalupe Freeway) along the river and the old residential blocks west of
Market St, traced from the Library of Congress scans of the Sanborn Map Co. *Insurance Maps of San José, California*
(public domain). Built by `pipeline/sanborn_trace_southbay.py`, an extension of `pipeline/sanborn_trace_waterfront.py`
(same similarity fits per sheet / per block, SIFT registration of the 1950 plates, colour segmentation, schema and
confidence rules; see `README_waterfront.md`). What is new is the control geometry (no DataSF here) and a stricter
partition-wall split for the dense brick blocks. Control data: `control/san_jose/`.

## Files

| file | content |
|---|---|
| `san_jose_downtown_1915.geojson` | footprints on the 1915 edition (vol. 1 sheets 63-65, 79-92; vol. 2 sheets 156, 158), EPSG:4326 |
| `san_jose_downtown_1950.geojson` | the same sheets in the "1915 - Jan 1950" corrected edition (paste-over slips up to Jan 1950) |
| `san_jose_downtown_coverage.geojson` | one polygon per map year (`map_year` 1915 / 1950): the ground the traced sheets cover. For block-wise sheets the hull of the blocks incl. the streets between them; for sheet fits the sheet minus its "See Volume ..." margins (`valid_px` / `valid_poly_px`). An empty spot inside it was empty (yard, street, plaza, river) on that map. |
| `control/san_jose/<key>.json` | control per sheet (25 % IIIF image): property-corner entries, ties, priors, or the SIFT registration onto the 1915 plate; `x0`/`y0` = the first (hand) pixel, `x`/`y` = refined; `unresolved` = control that has no world position today |
| `control/san_jose/attributes_px.json` | 47 names / uses read off the sheets, keyed by a pixel on the 1915 scan (attached to the footprint containing it; `carry` = also on the 1950 scan) |
| `control/san_jose/areas.json` | which sheets make up each map year |

No `san_jose_downtown_<year>_tracks.geojson`: none of the traced sheets draws a railway on private right of way. The
only rail on them is street running (Southern Pacific main track in 4th St, labelled "S.P. Co. (main track)" at the
top edge of sheet 65, outside the traced blocks; streetcar lines are not drawn) - see *Not done*.

Keys are `<LOC item suffix>_<sheet>`: `004_0089` = sanborn00817_004 (1915 vol. 1) sheet 89; `005_` = 1915 vol. 2;
`008_` = 1915-Jan 1950 vol. 1 (LOC items `sanborn00817_006` "1915; reprinted 1950" and `_008` "1915 - Jan 1950" serve
the same scans); `007_` = 1915-Jan 1950 vol. 2 (`_007`; `_009` "1915 - Feb 1950" serves the same scans).

### Feature properties

As in `README_waterfront.md` / `README_industrial.md`: `id`, `map_year` (1915 or 1950; a feature says the building
stood at the map date, not when it was built or demolished), `volume`, `volume_label`, `loc_url`, `sheet`, `sheet_no`,
`iiif`, `stories`, `stories_source`, `material` (frame = yellow, brick = pink, stone = blue on 1915 / concrete = blue on
1950, concrete = ochre "fire proof construction", iron = grey), `use`, `use_source`, `name`, `sanborn_colour`,
`confidence`, `georef` (`sheet` or `block <name>`), `georef_rms_m`, `extraction` (`colour class`, or `region` = the
1950 second pass over regions enclosed by drawn lines), `area_m2`, `modern_overlap` (share covered by today's Overture
footprints, `data/raw/overture/2026-10-21.0/region5_building.parquet`; high values = the building still stands, or a new
building on the spot).

* `stories`: **not read** from the sheets (`stories_source = default` everywhere). Rule: frame < 30 m2 shed 1;
  residential sheets (79, 80, 86-92, 156, 158) frame <= 300 m2 dwelling 1 (San José's cottages), larger frame 2
  (`other`); commercial sheets (63-65, 81-85) frame store 1, >= 400 m2 warehouse 1; brick / stone / concrete store 2;
  iron shed 1. Many commercial brick blocks on First St were 2-4 storeys (Montgomery Hotel 4, Garden City Bank and
  First National Bank taller): the default is low there.
* `use`: the rule above unless a label was read (`use_source = map (label)`, 45 named footprints in 1915, 11 carried to
  1950).
* `confidence`: high = the fit (block or sheet) has >= 4 control points, RMS <= 1.5 m and max <= 3 m; medium = >= 3
  points and RMS <= 3 m, or a 2-corner block whose scale is within 1.5 % of the plate scale (0.2010 m/px); low
  otherwise. Then: one level lower for a footprint more than 600 px (~120 m) outside the control points of a sheet fit;
  1950: the registration RMS is added; tied sheets: the RMS of the block / sheet they are tied to is added; per-sheet
  caps (`confidence_cap`: 79, 87, 88, 156 medium; 158 low).

## Counts

| file | features | high / medium / low | materials | uses | area (1000 m2) | modern_overlap >= 0.5 | named |
|---|---|---|---|---|---|---|---|
| san_jose_downtown_1915 | 3,287 | 918 / 1,195 / 1,174 | frame 2,934, brick 301, stone 35, concrete 16, iron 1 | shed 1,303, dwelling 1,286, store 620, other 40, warehouse 10, church 6, hotel 6, school 5, factory 5, theatre 4 | 383.1 | 1,433 | 45 |
| san_jose_downtown_1950 | 2,538 | 662 / 862 / 1,014 | frame 1,910, brick 345, concrete 267, iron 16 | dwelling 1,001, shed 782, store 698, other 51 | 368.6 | 1,081 | 11 |

Coverage: 139 ha per map year. Per sheet (1915 / 1950 features; confidence):

| sheet | area | 1915 | 1950 | confidence (1915) |
|---|---|---|---|---|
| 63 | 1st-3rd, St John-Santa Clara (Trinity Church, Bank of San Jose) | 106 | 72 | all high |
| 64 | 1st-3rd, Santa Clara-San Fernando (Fountain Alley, Letitia Bldg, Theatre Jose) | 97 | 74 | all high |
| 65 | 1st-4th, San Fernando-San Antonio (O. A. Hale & Co., First Baptist) | 147 | 99 | 93 medium, 54 low |
| 79 | Santa Teresa St to the Guadalupe, Julian-San Augustine (SR 87) | 155 | 171 | 93 medium, 62 low |
| 80 | Santa Teresa-San Pedro, Julian-San Augustine (Longfellow School) | 260 | 216 | 59 high, 152 medium, 49 low |
| 81 | 1st-San Pedro, Julian-St James | 118 | 48 | all high |
| 82 | 1st-San Pedro, St James-St John (Courthouse, Hall of Records, Hotel St. James) | 87 | 62 | all medium |
| 83 | 1st-San Pedro, St John / San Augustine-Santa Clara (Victory Theatre) | 132 | 63 | all medium |
| 84 | 1st-San Pedro, Santa Clara-San Fernando (First National Bank, St Joseph's) | 107 | 89 | 92 high, 15 medium |
| 85 | Convent of Notre Dame block, San Pedro-Santa Teresa | 102 | 70 | 96 medium, 6 low |
| 86 | San Pedro-Locust, Santa Clara-San Fernando (foundry, planing mill) | 237 | 123 | all high |
| 87 | Santa Teresa-River St, San Augustine-Santa Clara (SR 87) | 265 | 228 | all low |
| 88 | Locust-Delmas, Santa Clara-San Fernando, the river (San Jose Water Co., Hubbard & Carmichael) | 218 | 154 | 214 medium, 4 low |
| 89 | 1st-Orchard, San Fernando-San Antonio / Park (Market St Chinatown block, Post Office, Olympic Theatre) | 138 | 73 | 74 medium, 64 low |
| 90 | 1st-Orchard, San Antonio / Park-San Carlos (City Hall, Hotel Montgomery, Auditorium rink) | 139 | 95 | 13 medium, 126 low |
| 91 | 1st-Orchard, San Carlos-Viola (Eagle Brewery, Columbia Hospital, Lincoln School) | 172 | 106 | 78 medium, 94 low |
| 92 | 1st-Orchard, San Salvador-Pierce (Viola, Balbach, William) | 209 | 219 | all high |
| 156 (vol. 2) | Orchard-River St, San Fernando-San Carlos (St Joseph's schools; Park Center / Performing Arts site) | 351 | 290 | 148 medium, 203 low |
| 158 (vol. 2) | Orchard-Guadalupe and across the river, San Carlos-Balbach | 247 | 286 | all low |

A "feature" is one coloured fill between drawn walls. Unlike the SF tools every class is split along the drawn
partition walls (long straight lines >= 14 px = 2.8 m, darker than their 7-px neighbourhood by 28+ grey levels), so a
row of brick stores on First St is one feature per building as drawn; frame back buildings and sheds come out
separately (hence many small `shed` features).

## Sources

Sanborn Map Company, *Insurance Maps of San José, California*, Library of Congress Geography and Map Division,
Sanborn Maps Collection (public domain), item pages and IIIF images (25 % for tracing, 50 % of sheet 89 for labels):

| edition | LOC item | sheets used |
|---|---|---|
| 1915 vol. 1 | https://www.loc.gov/item/sanborn00817_004/ | 63, 64, 65, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92; key map `0000`, "map of congested district" `cbd` (200 ft = 1 in, used to find sheets) |
| 1915 vol. 2 | https://www.loc.gov/item/sanborn00817_005/ | 156, 158; key map `0000` |
| 1915 - Jan 1950 vol. 1 | https://www.loc.gov/item/sanborn00817_008/ (same scans as `_006`, "1915; reprinted 1950") | same sheet numbers as 1915 vol. 1 |
| 1915 - Jan 1950 vol. 2 | https://www.loc.gov/item/sanborn00817_007/ (same scans as `_009`, "1915 - Feb 1950") | 156, 158 |

Control geometry:
* **Overture Maps transportation segments**, release 2026-10-21.0, all road classes in three small boxes (downtown
  San José, old Santa Clara, Palo Alto University Ave): `data/raw/overture/2026-10-21.0/roads_southbay_core.parquet`
  (23,654 segments; ODbL, (c) OpenStreetMap contributors / Overture). `roads_region.parquet` holds only the primary-
  tertiary classes and lacks most downtown streets (Post, Lightston, Devine, Terraine...).
* **County of Santa Clara parcels** ("Parcels Public View", April 2026, `data/raw/region_years/santa_clara_county`):
  dissolved into blocks (`data/interim/sanborn_southbay/parcel_blocks.parquet`) as today's property lines.

## Method (differences from the SF tools)

1. **Property corners from parcels (`pc`).** A Sanborn sheet draws the block outline, i.e. the property lines. For a
   control corner the block of today's parcels in the given quadrant of a street crossing is taken; along each of the
   two streets its frontage is the median normal offset of the block-boundary points 18-75 m from the crossing (so a
   rounded or cut corner does not count), and the two frontage lines are intersected. This is independent of where
   the Overture centreline lies in the street (it is often off-centre: First St's centreline is ~3.4 m east of the
   right-of-way centre because of the light-rail mall; San Fernando St's ~3.8 m north). Pixel corners were read by
   eye on half-size overviews / 3x crops and snapped to the nearest drawn block lines (`refine_corner`), then frozen.
   Diagnostics: the four quadrant offsets at each crossing must add up to plausible street widths (Santa Clara and
   Market St 100 ft, First St 80 ft, Post St 50 ft, St John 60 ft ...).
2. **Where today's property line is not the 1915 one**: `wa`/`wb` = the street's Overture centreline + half the width
   printed on the sheet (60 ft San Antonio, San Carlos, St John, William St); `ma`/`mb` = the property line across the
   street + the mapped width (San Fernando St west of Market, 80 ft ESTIMATE); `shift` = a known corner moved across
   a street by its width (Orchard / Vine / Locust corners south of San Fernando); `tie` = a corner drawn on an already
   georeferenced neighbour sheet (the adjacent-sheet rectangles at the sheet edges are drawn to scale: 18.2 m drawn
   vs 60 ft printed for San Antonio St on sheets 89 / 90, 91 px = 60 ft for Santa Teresa St on sheet 87).
3. **Priors.** The well-controlled block fits share a scale of 0.200-0.203 m/px (25 % scans) and a rotation of
   -58.2 to -59.0 deg (31.2-31.7 deg on the north-up sheets 79, 80, 156, 158), so sheet fits with few or clustered
   control points use a scale prior 0.2010-0.2015 +- 0.0006-0.0015 and a rotation prior +- 0.4-0.6 deg (`scale_prior`
   = [scale, sigma, rotation, sigma]).
4. **Block-wise sheets.** As in SF, the quadrant sheets 63, 64, 81-84, 86 draw their blocks to scale but the streets
   between them (Market St, Post St, 2nd St) far wider: a single sheet fit has 14-30 m residuals, so they are fitted
   block by block (`zones_only`). Sheet 80 is fitted per block for the three blocks with surviving property lines and
   by a sheet fit for the rest.
5. **1950 sheets** are the 1915 plates with paste-over corrections: each 1950 scan is registered onto its 1915 scan
   (SIFT + RANSAC similarity, 754-2,176 inliers, 1.3-1.9 px = 0.25-0.38 m) and inherits its control.
6. **Footprints**: the waterfront tool's colour classes with thresholds for these plates (the San José pink wash is
   darker, grey ~108, than SF's; the absolute "dark < 110" line test of the SF tool marked half the pink as lines),
   drawn lines found relative to a 7-px median; every class split along partition walls; dark-ochre fire-proof fills
   that fall into the yellow mask re-classed by their median hue (<= 23.5); 1950: paler blue (concrete) on paste-over
   slips accepted, and a second pass over regions enclosed by drawn lines classified by median colour (56 features).

## Georeferencing per sheet (1915; the 1950 scans are registered onto these)

Residuals in metres between the transformed pixel and the parcel-derived position.

| sheet (LOC id) | method | control | RMS / max (m) | scale (m/px), rotation | cap |
|---|---|---|---|---|---|
| [00817_01_1915-0063](https://www.loc.gov/item/sanborn00817_004/) | per-block similarity (zones only; streets drawn wider than scale) | 8 parcel corner | 8: 4 pts 0.52/0.74; 9: 4 pts 0.35/0.44 | (block fits) |  |
| [00817_01_1915-0064](https://www.loc.gov/item/sanborn00817_004/) | per-block similarity (zones only; streets drawn wider than scale) | 8 parcel corner | 17: 4 pts 0.98/1.34; 19: 4 pts 0.28/0.33 | (block fits) |  |
| [00817_01_1915-0065](https://www.loc.gov/item/sanborn00817_004/) | sheet similarity + scale/rotation priors | 6 parcel corner | 1.61/2.78 | scale 0.2031 m/px, rot -58.76 deg |  |
| [00817_01_1915-0079](https://www.loc.gov/item/sanborn00817_004/) | sheet similarity + scale/rotation priors | 6 tie | 0.52/0.75 | scale 0.2016 m/px, rot 31.46 deg | medium |
| [00817_01_1915-0080](https://www.loc.gov/item/sanborn00817_004/) | per-block similarity + sheet fit for the rest | 12 parcel corner | 75: 4 pts 0.80/0.95; 76: 4 pts 0.53/0.75; 77: 4 pts 2.23/2.81; sheet 2.10/4.07 | scale 0.2021 m/px, rot 31.70 deg |  |
| [00817_01_1915-0081](https://www.loc.gov/item/sanborn00817_004/) | per-block similarity (zones only; streets drawn wider than scale) | 12 parcel corner | 73+72: 8 pts 0.97/1.65; 74: 4 pts 0.39/0.52 | (block fits) |  |
| [00817_01_1915-0082](https://www.loc.gov/item/sanborn00817_004/) | per-block similarity (zones only; streets drawn wider than scale) | 5 parcel corner, 1 parcel corner (+width) | 3: 3 pts 0.79/1.00; 11: 3 pts 0.42/0.54 | (block fits) |  |
| [00817_01_1915-0083](https://www.loc.gov/item/sanborn00817_004/) | per-block similarity (zones only; streets drawn wider than scale) | 5 parcel corner | 5: 3 pts 0.17/0.21; SanAugustine-SantaClara/Market-SanPedro: 2 pts 0.00/0.00 | (block fits) |  |
| [00817_01_1915-0084](https://www.loc.gov/item/sanborn00817_004/) | per-block similarity (zones only; streets drawn wider than scale) | 20 parcel corner | 20: 4 pts 0.45/0.61; 21: 4 pts 0.50/0.61; 22: 4 pts 0.83/1.02; 23: 4 pts 1.69/1.86; 24: 4 pts 1.15/1.31 | (block fits) |  |
| [00817_01_1915-0085](https://www.loc.gov/item/sanborn00817_004/) | sheet similarity + scale/rotation priors | 2 parcel corner, 1 parcel corner (+width) | 1.54/1.88 | scale 0.2008 m/px, rot -58.66 deg |  |
| [00817_01_1915-0086](https://www.loc.gov/item/sanborn00817_004/) | per-block similarity (zones only; streets drawn wider than scale) | 12 parcel corner | SantaClara-Post: 6 pts 0.63/0.91; Post-SanFernando: 6 pts 1.16/2.18 | (block fits) |  |
| [00817_01_1915-0087](https://www.loc.gov/item/sanborn00817_004/) | sheet similarity + scale/rotation priors | 2 tie | 0.23/0.23 | scale 0.2015 m/px, rot -58.82 deg | medium |
| [00817_01_1915-0088](https://www.loc.gov/item/sanborn00817_004/) | sheet similarity + scale/rotation priors | 2 tie, 1 parcel corner | 1.95/2.23 | scale 0.2044 m/px, rot -58.25 deg | medium |
| [00817_01_1915-0089](https://www.loc.gov/item/sanborn00817_004/) | sheet similarity + scale/rotation priors | 3 parcel corner, 1 parcel corner (+width) | 1.88/2.74 | scale 0.2010 m/px, rot -58.19 deg |  |
| [00817_01_1915-0090](https://www.loc.gov/item/sanborn00817_004/) | sheet similarity + scale/rotation priors | 1 parcel corner (+width), 2 tie | 1.34/1.84 | scale 0.2015 m/px, rot -58.72 deg |  |
| [00817_01_1915-0091](https://www.loc.gov/item/sanborn00817_004/) | sheet similarity + scale/rotation priors | 1 parcel corner (+width), 2 parcel corner | 2.02/2.76 | scale 0.1959 m/px, rot -58.62 deg |  |
| [00817_01_1915-0092](https://www.loc.gov/item/sanborn00817_004/) | sheet similarity + scale/rotation priors | 4 parcel corner, 2 parcel corner (+width) | 1.28/2.42 | scale 0.2000 m/px, rot -58.58 deg |  |
| [00817_02_1915-0156](https://www.loc.gov/item/sanborn00817_005/) | sheet similarity + scale/rotation priors | 3 tie, 1 parcel corner moved across street | 2.53/4.31 | scale 0.2018 m/px, rot 31.16 deg | medium |
| [00817_02_1915-0158](https://www.loc.gov/item/sanborn00817_005/) | sheet similarity + scale/rotation priors | 2 tie, 1 parcel corner | 2.81/3.61 | scale 0.1996 m/px, rot 32.88 deg | low |

### Findings (control)

* **Orchard St = today's Almaden Avenue** north of San Fernando (sheet 86: 6 corners per half, 0.6 / 1.2 m RMS) and
  south of Viola Ave (S Almaden Ave; sheet 92's Orchard x Balbach corners fit to 0.7-0.8 m). Between San Fernando and
  Viola it is gone (Park Center Plaza, convention centre). Vine and Locust St (west of Orchard) and River St are gone.
* **San Augustine St = today's W St John St west of Market**: St John St jogs at Market St (1915: St John east of
  Market, San Augustine west of it; corners on the jog give 6-20 m residuals and were dropped). Santa Teresa x
  San Augustine survives; Santa Teresa no longer reaches Santa Clara St.
* **San Carlos St was 60 ft in 1915** (adjacent-sheet rectangle on sheet 90) and is ~91-93 ft today: its parcel
  corners are not the 1915 ones. With the plate scale fixed, sheet 90 puts the 1915 north line ~12 m south of today's
  north property line, i.e. the widening was mostly on the north (plaza / Fairmont) side - an inference, not checked.
* **Paseo de San Antonio does not keep San Antonio St's line east of First St**: its centreline is 181 m from San
  Fernando St at First St but 256 m at 4th St, so sheet 65 uses only its San Fernando corners. At First St the paseo
  + 30 ft and sheet 65's fit (controlled on the east side of First) disagree by ~12 m along First St; today's San
  Fernando St south property line also differs by 7.8 m between the west (Fairmont) and east (Pavilion) sides of
  First St. Sheets 89 / 90 (west side) and 65 (east side) may therefore be offset against each other by up to ~10 m
  along First St; 65 and the far parts of 89 / 90 are `medium` / `low` accordingly.
* The blocks west of Terraine St (sheet 80) and west of Santa Teresa St (79, 87) have no property lines left (SR 87 /
  Guadalupe River Park); 79 and 87 are tied to 80 and 85.

### Checks

* Buildings that still stand fall on today's footprints: Trinity Episcopal Church (1863) 0.96, Bank of San Jose
  (1892) 1.00, Letitia Building 0.96 (1950), Theatre Jose (1904) 0.91, St. Joseph's 1.00, the 1892 Post Office (Museum
  of Art) 1.00 / 0.94, County Courthouse 1.00; demolished ones do not: City Hall in the plaza (1887-1958) 0.00.
* San José HRI record 3318 (Peterson Residence, 160 Balbach St, c1909, demolished) lies inside a traced 1915 and 1950
  frame house on sheet 92 (0 m).
* Overlays of every sheet's footprints were checked by eye (scratch, `python pipeline/sanborn_trace_southbay.py
  overlay <key>`): houses on the residential sheets and the brick rows on the commercial sheets are found; faint
  paste-over fills on the 1950 sheets are still partly missed (1950 feature counts are lower than 1915 on 81 / 83 /
  86 also because of real consolidation and "auto parking" lots).

## Not done / open items

* **1891 and 1884 editions** (`sanborn00817_001`-`_003`): not traced (the 1915 plates were the priority).
* **Railway tracks**: none traced (no private-right-of-way rail on these sheets; the SP 4th St street track and the
  Southern Pacific / interurban lines along the Guadalupe / Stockton Ave lie on sheets not traced).
* **Not traced in downtown**: vol. 1 sheets 47-53 (3rd-5th St, Washington Square), 61, 62, 66, 67, 68 (east side of
  1st-3rd St north of St John and south of San Antonio), the area east of 5th St (2005 City Hall blocks, Heinlenville
  and Japantown, sheets ~30-46). Old Santa Clara (1887 `sanborn00832_001`) and Palo Alto University Ave
  (`sanborn00747_*`) were not started (their Overture streets are downloaded in `roads_southbay_core.parquet`).
* **Storeys** were not read; names only for 47 labelled buildings (45 attached on the 1915 map, 11 carried to 1950;
  five more labels were dropped: three did not fall on a footprint, two landed on small sheds).
* **1950 paste-over slips**: faded fills partly missed.
* **Coverage** includes the streets between blocks and plaza / river areas (empty on the map); the scan margins with
  "See Volume ..." notes are cut off by `valid_px` / `valid_poly_px` on 79, 87-92, 156, 158.

## Rows added elsewhere

* `data/manual/redevelopment_areas.csv`: `sj_park_center` (1962-1968, plan 1961, groundbreaking 1968),
  `sj_sr87_guadalupe_downtown` (1970-1976, temporary freeway I-280 - Julian 1976), `sj_i280_downtown` (1965-1971,
  opened mid-1972), `sj_heinlenville` (1931), `sj_market_street_chinatown` (fire 4 May 1887), `sj_convention_center`
  (1984-1987, approved 1983, opened 1989). Rings from today's street crossings (Overture), freeway corridors as the
  centre line + 50 m, the Chinatown block from the sheet 89 fit; confidence words in each note.
* `data/tables/notable_demolished_region.csv` (new; columns of `notable_demolished.csv` + `county`): City Hall in the
  plaza 1887-1958 and the Hotel Montgomery at its first site 1911-2000 (traced footprint ids in `shape_note`), the
  Donner-Houghton House (c1881-2007, fire of 19 Jul 2007), and six San José HRI demolished resources whose `TRUEYR`
  is later than their construction estimate (`end_year` = that year as an UPPER BOUND, LOW confidence: for the
  Donner-Houghton House the HRI year is 2017, ten years after the verified demolition).
* San José HRI: 56 demolished / 86 moved records. The layer has no demolition or move date field; `NOTES` is empty
  for all but one; `FORMERADDRESS` (47 moved records) is text, not geocoded. Usable for a dated row: 1 (verified by
  a news source) + 6 (upper bound only); 20 have only a construction estimate and 29 neither year - not written.

## Reproduce

```
python pipeline/sanborn_trace_southbay.py all                 # fetch + georef + extract + assemble (control is frozen)
python pipeline/sanborn_trace_southbay.py assemble            # outputs only
python pipeline/sanborn_trace_southbay.py register 008_0089 004_0089   # redo one SIFT registration
python pipeline/sanborn_trace_southbay.py grid 004_0089 300 700 700 1000  # scratch crop with a pixel grid
python pipeline/sanborn_trace_southbay.py overlay 004_0089    # scratch overlay of the traced footprints
```
Downloads go to `data/raw/sanborn_loc/san_jose/` (separate from the SF and Oakland folders); intermediates to
`data/interim/sanborn_southbay/`. A new sheet: write corners as `{"pc": [street a, street b], "q": "NE", "x": .., "y": ..}`
(approximate pixels within ~10 px; `refine_corner` snaps them), run `georef`, check the residuals and the quadrant
offsets, then freeze the refined pixels (`freeze()` in the module) so reruns reproduce the fit.
