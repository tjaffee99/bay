# Western Addition from the Sanborn maps (1899 and 1913)

Real building footprints for the parts of the Western Addition that urban renewal cleared (A-1, 1956–63; A-2,
1966–73). They are traced from the Library of Congress scans of the Sanborn fire-insurance maps, two editions:

| file | edition | footprints | in A-1 / A-2 | storeys read from the map | use read |
|---|---|---|---|---|---|
| `western_addition_1913.geojson` | 1913 vols. 3–4 (survey 1912–13) | 6,430 | 2,430 / 4,000 | 3,363 (52 %) | 1,987 (+136 stables) |
| `western_addition_1899.geojson` | 1899 vol. 3 | 7,060 | 2,509 / 4,551 | 3,870 (55 %) | 1,371 (+364 stables) |
| `western_addition_coverage.geojson` | both | 159 + 158 traced sub-blocks (one polygon per sub-block, with its residuals) | | | |

* Area: every block inside the `wa_a1` / `wa_a2` rings of `data/manual/redevelopment_areas.csv` (Bush → Grove,
  Van Ness → Broderick), apart from the two gaps listed under "Coverage". A footprint is kept when its centroid is
  inside a ring; `area_id` says which.
* Coordinates: GeoJSON lon/lat (EPSG:4326 / CRS84), 6 decimals.
* Tool: `pipeline/sanborn_trace.py` (download / trace / export / preview). Sheet list and street layout:
  `sheets_western_addition.csv`. Hand-labelled storey-mark crops and digit templates: `storey_marks_train.npz`.
* Licence: the Sanborn scans are public domain. Credit line: "Library of Congress, Geography and Map Division,
  Sanborn Maps Collection."

## Sources

* Sanborn Map Company, *Insurance Maps of San Francisco, California*, 1899–1900, **vol. 3** (sheets 251–368,
  north to the right): https://www.loc.gov/item/sanborn00813_010/ (IIIF `g4364sm_g00813189903`).
* Sanborn Map Company, 1913–1915 edition, **vol. 3** (1913, sheets 225–324, Pine → Geary): https://www.loc.gov/item/sanborn00813_017/
  (IIIF `g4364sm_g00813191303`), and **vol. 4** (1913, sheets 325–426, Geary → Golden Gate Park):
  https://www.loc.gov/item/sanborn00813_018/ (IIIF `g4364sm_g00813191304`). North is to the left on these sheets.
* Images: IIIF JPEG at 50 % (`https://tile.loc.gov/image-services/iiif/service:gmd:gmd436m:g4364m:g4364sm:<resource>:<image_id>/full/pct:50/0/default.jpg`),
  about 0.100 m per pixel. The per-sheet viewer links are in the residual table below and in `sheets_western_addition.csv`.
* Reference geometry: DataSF street centrelines (`data/raw/sf_streets`) and today's assessor parcels
  (`data/raw/sf_parcels`, dissolved by block) for the property lines.
* The 1913 maps show the post-1906 Western Addition. Almost all of it lay outside the 1906 burn: A-1 is entirely
  outside the project's burn polygon (`data/interim/fire_1906.geojson`), and only a strip along Van Ness is inside it
  (7 % of the A-2 ring), shown rebuilt in 1913. Most of the houses are the 1870s–1890s Victorians that the
  redevelopment agency later cleared.

## Method

1. **Street grid frame.** The Western Addition grid is exactly orthogonal: N-S streets have bearing 350.55° and E-W
   streets 80.55°. Each street was fitted as a straight line to the DataSF centrelines, with a residual of 0.1–0.4 m.
   The frame is `u` east and `v` north in metres, with its origin at the Fillmore × Eddy centreline crossing. Each
   street's offset is the mode of its centreline positions, which also locates streets that A-2 removed or bent
   (Webster, O'Farrell, Buchanan) from their surviving stretches. Geary is placed on the straight line of downtown
   Geary St, `v` = 313.7, because Geary Blvd was rebuilt as an expressway.
   * **Property lines** = centre ± half width. The half widths were measured on today's assessor blocks (median of
     every surviving rectangular block): 10.2–10.7 m for 68.75-ft streets, Divisadero ±12.6 m (82.5 ft), and
     Van Ness 1007.5–1045.6 m, i.e. 125 ft (its modern centreline is a dual carriageway, so it was fixed from the
     parcels).
   * Spacing: blocks are 412.5 × 275 ft, with centrelines every 146.7 m (N-S) and 104.7 m (E-W). The
     Franklin–Van Ness block is 384.5 ft.
2. **Blocks on the sheet.** Map colours were classified in Lab: paper, ink, yellow, pink, blue, brown, and the
   1899 green "frame special". The street network is the large connected paper region. Every large non-street
   component is a sub-block, i.e. a group of lots bounded by streets or alleys.
   * Each sub-block's four sides are RANSAC lines on its edge profile, moved inward by half the line width (0.15 m).
   * Where a block is drawn joined to its neighbour, the outer straight line is preferred. This happens when a
     street was never cut through: Pierce St between Geary and O'Farrell, at the Girls' High School super-block.
3. **Georeferencing: one fit per sheet, one translation per sub-block.** Sanborn draws blocks to scale but streets
   and alleys are not to scale: Eddy is drawn 51 m wide instead of 21 m, and the 35-ft Willow alley 25 m wide. A
   single transform per sheet would therefore be wrong by tens of metres.
   * Model: `uv = S·P·p + t_k`. `P` is the sheet orientation, `S` is one similarity per sheet (or an affine, used
     only when it is constrained on both axes and lowers the RMS by more than 20 %), and `t_k` is one translation
     per sub-block.
   * **Control points**: the two corners of every sub-block side that lies on a street property line, i.e. the
     corner points of the block outlines matched to the property-line grid.
   * Alley sides are not constrained, so an alley's position comes from the to-scale lot depths drawn on each side.
   * Sides with a residual over 1.2 m are rejected greedily, trying the three worst and keeping the best drop. The
     rejected sides are listed in the table.
   * Total: **2,466 corner constraints** on 68 sheets, minimum 26 per sheet.
   * Fitted scales are 0.100–0.104 m/px, i.e. 50 ft to the inch, consistently.
4. **Footprints.** Each 4-connected coloured region is one footprint. Black lines separate buildings; dashed
   partitions and lettering do not.
   * Holes (lettering, symbols) are filled.
   * Regions are grown 1.6 px to the middle of the wall lines, so attached houses share their party wall.
   * **X-crossed** buildings are merged back into one region: these are the Sanborn stable / shed symbol, whose
     diagonals otherwise split the region into four triangles.
   * Slivers under 3.8 m² go into their longest-boundary neighbour, and boxes drawn inside a building (elevators,
     skylights) go into the parent.
   * Outlines are simplified at 0.14 m and transformed with the sub-block's own transform.
   * Uncoloured porches, stairs and open sheds are not traced.
   * One feature = one **Sanborn building section**: a building, or a part of it with its own storey mark (e.g. a
     1-storey rear wing). Adjacent sections of one house are separate features.
5. **Storeys.**
   * Candidate marks are found near region corners (≤ 4 m from two walls) with normalized cross-correlation (NCC)
     against digit templates averaged from about 1,100 glyphs. Long wall lines are stripped first.
   * The candidates are classified by an SVM (HOG + pixels) trained on 360 hand-labelled crops from 8 sheets. Its
     classes are `1 2 3`, `1B 2B 3B` (basement), `1½`, and "not a mark". The training set is in
     `storey_marks_train.npz`.
   * Cross-validated, the digit is right in **95 %** of the cases where a mark is read.
   * On a hand-checked sample (1913 sheet 338, 24 houses with a read value) 22 were right; the 2 errors were
     2B read as 1.
   * Regions without a confident read get `stories_source = estimated`: the median read storeys for the same
     material and footprint size in the same edition (2 for frame houses ≥ 30 m², 1 for small sections), and 1 for
     stables.
6. **Use.** Letters are classified by k-NN on glyph exemplars (also in the `.npz`):
   * an isolated `D` → dwelling;
   * `F` alone, or starting a word ("2 Flats") → flats;
   * an isolated `S` → store;
   * the X symbol → stable.
   Everything else is `use = other` with `use_source = not_read`; the use was simply not read, it is not known to be
   "other". Words such as "Church", "School" and "Garage" are not read.
7. **Links between editions and to today.**
   * `seen_1899` (on 1913) / `seen_1913` (on 1899): whether a footprint in the other edition overlaps with
     IoU ≥ 0.3, or `null` where that edition does not cover the spot.
   * `today_iou`: the best IoU with today's footprint in `data/interim/sf_buildings.fgb`. When it is ≥ 0.3,
     `today_bldg`, `today_start_year` and `today_year_confidence` give the modern building's id and year.

## Properties

| property | meaning |
|---|---|
| `id` | `sb<year>_<n>` (stable for this export only) |
| `map_year` | 1899 or 1913 (edition; the 1913 survey is 1912–13) |
| `volume`, `sheet`, `loc_item` | Sanborn volume, LOC image id (e.g. `00813_04_1913-0338`), LOC item (`sanborn00813_018`) |
| `stories` | int (1–3 read; 4+ storey marks are not in the classifier, see problems) |
| `stories_source` | `read` (from the mark) / `estimated` (median of read values for the same material and size) |
| `basement`, `half_storey`, `stories_p` | "B" after the storey digit (raised basement); "1½"; classifier probability (null when estimated) |
| `material` | `frame` (yellow; 1899 green "frame special" too, `frame_special = true`), `brick` (pink), `stone` (blue: "stone, concrete or concrete block" on the 1913 key), `concrete` (brown: "fire proof construction"), `iron` (grey; none found) |
| `use`, `use_source` | dwelling / flats / store / stable / other; `read`, `x_symbol` or `not_read` |
| `confidence` | `high`: storeys read and the sub-block had ≥ 3 street sides on a sheet with RMS ≤ 0.6 m; `medium`: same geometry with storeys estimated, or 2 street sides; `low`: weaker geometry |
| `area_m2`, `area_id` | footprint area; `wa_a1` / `wa_a2` |
| `row_overlap_m2` | area lying inside a street right-of-way strip (QA; bays and stairs are drawn over the line) |
| `seen_1899` / `seen_1913` (+`_iou`) | presence in the other edition (see 7.) |
| `today_iou`, `today_bldg`, `today_start_year`, `today_year_confidence` | match with today's building (see 7.) |

### Suggested lifespans for the viewer (not applied here; the viewer and pipeline code are untouched)

* **Start.**
  * A 1913 footprint with `seen_1899 = true` stood by 1899. Use the assessor year when `today_iou ≥ 0.5`;
    otherwise ≤ 1899, the Western Addition being built mostly 1870s–1890s.
  * `seen_1899 = false` → built 1899–1913. Mostly the post-quake boom of 1906–1912, especially the Fillmore stores
    and flats.
  * A 1899 footprint with `seen_1913 = false` ended 1899–1913.
* **End.**
  * The clearance window of its area: A-1 1956–63, A-2 1966–73. `redevelopment_areas.csv` already carries these.
  * Unless `today_iou ≥ 0.5`: then it is probably still standing. That is 481 of the 1913 footprints ≥ 40 m² (13 %),
    including the rehabilitated rows inside the A-2 boundary.
  * Some A-2 Victorians were moved rather than demolished; they will show up as a 1913 footprint that ends plus a
    "new" modern building elsewhere.
* Height: storeys × 3.3 m + 1.5 m as in decision 6; + about 1.2 m when `basement` (raised basement).
* These footprints should replace the procedural `victorian_rows` fabric for the blocks in the coverage file.
  * 1913 → year of clearance.
  * 1899-only buildings → 1899 to 1913.
* `year_confidence = exact`/`estimated` as above, `source = sanborn_1913` / `sanborn_1899`.

## Quality checks

* **Residuals.**
  * Per-sheet RMS 0.10–0.49 m (median 0.19 m), worst single constraint 1.18 m. Table below.
  * Sides rejected as outliers are almost all alley or lane sides wrongly taken for street sides (residual 10–76 m),
    plus a few 1.2–1.7 m sides on irregular frontages.
* **Footprints on today's streets (visual).** All 68 sheets were drawn in the grid frame over the DataSF centrelines
  and the property lines, as an overview of both editions plus zooms at Fillmore × Eddy, Laguna/Octavia × Geary/Post,
  Steiner–Scott × Geary–Ellis and Laguna–Webster × McAllister–Grove.
  * Blocks sit between their property lines.
  * Alleys come out at their real widths without being constrained: Willow and Larch (35 ft = 10.67 m) measure
    10.4 m and 11.0 m on sheet 1913/338.
  * The two editions overlay house for house: 73 % of the 1913 footprints ≥ 40 m² match an 1899 footprint at
    IoU ≥ 0.3, and 78 % the other way.
* **Right-of-way intrusion.**
  * 0.72 % (1913) and 1.50 % (1899) of the footprint area lies inside a street right-of-way strip.
  * 237 / 360 footprints intrude by > 5 m². These are mainly bay windows, stairs and porches drawn over the line,
    and the buildings on the line of Pierce St between Geary and O'Farrell, which was not a street then.
  * The 1899 figure is higher because its frontages are drawn with more projecting bays and porches.
* **Storeys.** See Method 5. Basement marks are read where the "B" is clear: 38–44 % of the read buildings
  ≥ 40 m² have one.
* Previews: `python pipeline/sanborn_trace.py preview 1913_0338 300 300 1400 1100` draws the outlines and read
  storeys over a sheet crop.

## Coverage

`13+99` = traced in both editions, `13` = 1913 only, `park` = no buildings (Jefferson Square, Hamilton Square, Alamo
Square). Rows = blocks between N-S streets (east → west), columns = between E-W streets (north → south).
`western_addition_coverage.geojson` has the exact traced sub-block outlines with their residuals.

| N-S \ E-W | Bush–Sutter | Sutter–Post | Post–Geary | Geary–O'Farrell | O'Farrell–Ellis | Ellis–Eddy | Eddy–Turk | Turk–G. Gate | G. Gate–McAllister | McAllister–Fulton | Fulton–Grove |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Van Ness–Franklin | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 |
| Franklin–Gough | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 |
| Gough–Octavia | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | park | park | 13+99 | 13+99 | 13+99 |
| Octavia–Laguna | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | park | park | 13+99 | 13+99 | 13+99 |
| Laguna–Buchanan | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 |
| Buchanan–Webster | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 |
| Webster–Fillmore | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 |
| Fillmore–Steiner | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 |
| Steiner–Pierce | 13+99 | 13 | park | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | park |
| Pierce–Scott | 13+99 | 13 | park | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | park |
| Scott–Divisadero | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 |
| Divisadero–Broderick | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 | 13+99 |

Gaps:
* **Post–Geary × Steiner–Scott** (both editions): Hamilton Square, plus block 704. In 1913 block 704 is drawn only
  as an inset on vol. 3 sheet 244, which was not traced.
* **Sutter–Post × Steiner–Scott, 1899**: sheet 335 shares its page with a Marina inset, which the automatic block
  detection cannot separate; it needs a crop. The 1913 sheet 277 covers it.
* Blocks outside the A-1/A-2 rings on the processed sheets (Pine–Bush, Grove–Fell) were traced but dropped at
  export.

## Sheets, control points and residuals

Control points = the corners of every sub-block side that lies on a street property line (two per side). They are
matched to the property-line grid of step 1 and listed in `data/interim/sanborn/<key>.pkl` (`georef.obs`) after a
`trace` run. "model" = shared transform (`similarity` or `affine`), plus one translation per sub-block. Residuals
are point-to-property-line distances in metres.

| key | LOC image | streets (rows × cols) | model | sub-blocks | corner constraints | RMS m | max m | sides dropped | footprints |
|---|---|---|---|---|---|---|---|---|---|
| 1899_0253 | [00813_03_1899-0253](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=8) | Gough/Franklin/Van Ness × Grove/Fulton/Mcallister | affine | 5 | 34 | 0.14 | 0.33 | 1 | 273 |
| 1899_0254 | [00813_03_1899-0254](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=9) | Gough/Franklin/Van Ness × Mcallister/Golden Gate/Turk | affine | 7 | 44 | 0.12 | 0.32 | 0 | 204 |
| 1899_0255 | [00813_03_1899-0255](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=10) | Gough/Franklin/Van Ness × Turk/Eddy/Ellis | affine | 7 | 44 | 0.14 | 0.31 | 0 | 163 |
| 1899_0256 | [00813_03_1899-0256](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=11) | Gough/Franklin/Van Ness × Ellis/Ofarrell/Geary | similarity | 7 | 44 | 0.15 | 0.31 | 0 | 169 |
| 1899_0257 | [00813_03_1899-0257](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=12) | Gough/Franklin/Van Ness × Geary/Post/Sutter | affine | 4 | 32 | 0.20 | 0.35 | 0 | 138 |
| 1899_0258 | [00813_03_1899-0258](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=13) | Gough/Franklin/Van Ness × Sutter/Bush/Pine | similarity | 8 | 48 | 0.14 | 0.31 | 0 | 204 |
| 1899_0271 | [00813_03_1899-0271](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=26) | Laguna/Octavia/Gough × Grove/Fulton/Mcallister | affine | 6 | 40 | 0.27 | 0.81 | 0 | 350 |
| 1899_0272 | [00813_03_1899-0272](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=27) | Laguna/Octavia/Gough × Mcallister/Golden Gate/Eddy/Ellis | similarity | 6 | 40 | 0.25 | 0.58 | 0 | 192 |
| 1899_0273 | [00813_03_1899-0273](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=28) | Laguna/Octavia/Gough × Ellis/Ofarrell/Geary | affine | 6 | 40 | 0.13 | 0.27 | 0 | 160 |
| 1899_0274 | [00813_03_1899-0274](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=29) | Laguna/Octavia/Gough × Geary/Post/Sutter | similarity | 6 | 40 | 0.34 | 0.77 | 0 | 265 |
| 1899_0275 | [00813_03_1899-0275](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=30) | Laguna/Octavia/Gough × Sutter/Bush/Pine | affine | 5 | 36 | 0.19 | 0.31 | 0 | 191 |
| 1899_0287 | [00813_03_1899-0287](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=42) | Webster/Buchanan/Laguna × Grove/Fulton/Mcallister | affine | 6 | 40 | 0.23 | 0.79 | 0 | 329 |
| 1899_0288 | [00813_03_1899-0288](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=43) | Webster/Buchanan/Laguna × Mcallister/Golden Gate/Turk | affine | 4 | 32 | 0.13 | 0.28 | 0 | 275 |
| 1899_0289 | [00813_03_1899-0289](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=44) | Webster/Buchanan/Laguna × Turk/Eddy/Ellis | affine | 6 | 38 | 0.13 | 0.28 | 1 | 336 |
| 1899_0290 | [00813_03_1899-0290](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=45) | Webster/Buchanan/Laguna × Ellis/Ofarrell/Geary | affine | 6 | 40 | 0.10 | 0.27 | 0 | 284 |
| 1899_0291 | [00813_03_1899-0291](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=46) | Webster/Buchanan/Laguna × Geary/Post/Sutter | similarity | 4 | 32 | 0.25 | 0.53 | 0 | 253 |
| 1899_0292 | [00813_03_1899-0292](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=47) | Webster/Buchanan/Laguna × Sutter/Bush/Pine | affine | 4 | 32 | 0.18 | 0.35 | 0 | 211 |
| 1899_0309 | [00813_03_1899-0309](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=64) | Steiner/Fillmore/Webster × Grove/Fulton/Mcallister | affine | 4 | 32 | 0.21 | 0.36 | 0 | 206 |
| 1899_0310 | [00813_03_1899-0310](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=65) | Steiner/Fillmore/Webster × Mcallister/Golden Gate/Turk | similarity | 4 | 32 | 0.24 | 0.61 | 0 | 177 |
| 1899_0311 | [00813_03_1899-0311](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=66) | Steiner/Fillmore/Webster × Turk/Eddy/Ellis | affine | 5 | 36 | 0.14 | 0.39 | 0 | 289 |
| 1899_0312 | [00813_03_1899-0312](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=67) | Steiner/Fillmore/Webster × Ellis/Ofarrell/Geary | similarity | 5 | 34 | 0.41 | 0.73 | 1 | 144 |
| 1899_0313 | [00813_03_1899-0313](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=68) | Steiner/Fillmore/Webster × Geary/Post/Sutter | affine | 5 | 36 | 0.23 | 0.45 | 0 | 179 |
| 1899_0314 | [00813_03_1899-0314](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=69) | Steiner/Fillmore/Webster × Sutter/Bush/Pine | similarity | 7 | 42 | 0.28 | 0.82 | 1 | 311 |
| 1899_0331 | [00813_03_1899-0331](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=86) | Scott/Pierce/Steiner × Fell/Hayes/Fulton/Mcallister | similarity | 4 | 32 | 0.49 | 1.18 | 0 | 119 |
| 1899_0332 | [00813_03_1899-0332](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=87) | Scott/Pierce/Steiner × Mcallister/Golden Gate/Turk | affine | 5 | 36 | 0.21 | 0.56 | 0 | 235 |
| 1899_0333 | [00813_03_1899-0333](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=88) | Scott/Pierce/Steiner × Turk/Eddy/Ellis | affine | 6 | 40 | 0.23 | 0.75 | 0 | 335 |
| 1899_0334 | [00813_03_1899-0334](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=89) | Scott/Pierce/Steiner × Ellis/Ofarrell/Geary | affine | 4 | 26 | 0.14 | 0.35 | 3 | 284 |
| 1899_0336 | [00813_03_1899-0336](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=91) | Scott/Pierce/Steiner × Sutter/Bush/Pine | similarity | 4 | 32 | 0.27 | 0.69 | 0 | 172 |
| 1899_0351 | [00813_03_1899-0351](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=106) | Broderick/Divisadero/Scott × Grove/Fulton/Mcallister | similarity | 4 | 32 | 0.33 | 0.67 | 0 | 188 |
| 1899_0352 | [00813_03_1899-0352](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=107) | Broderick/Divisadero/Scott × Mcallister/Golden Gate/Turk | affine | 5 | 36 | 0.22 | 0.45 | 0 | 162 |
| 1899_0353 | [00813_03_1899-0353](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=108) | Broderick/Divisadero/Scott × Turk/Eddy/Ellis | similarity | 4 | 32 | 0.31 | 0.55 | 0 | 252 |
| 1899_0354 | [00813_03_1899-0354](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=109) | Broderick/Divisadero/Scott × Ellis/Ofarrell/Geary | affine | 5 | 34 | 0.24 | 0.44 | 1 | 308 |
| 1899_0355 | [00813_03_1899-0355](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=110) | Broderick/Divisadero/Scott × Geary/Post/Sutter | similarity | 5 | 34 | 0.40 | 0.79 | 1 | 249 |
| 1899_0356 | [00813_03_1899-0356](https://www.loc.gov/resource/g4364sm.g4364sm_g00813189903/?sp=111) | Broderick/Divisadero/Scott × Sutter/Bush/Pine | affine | 4 | 30 | 0.29 | 0.67 | 1 | 291 |
| 1913_0233 | [00813_03_1913-0233](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191303/?sp=13) | Van Ness/Franklin/Gough × Pine/Bush/Sutter | similarity | 8 | 44 | 0.18 | 0.58 | 1 | 154 |
| 1913_0234 | [00813_03_1913-0234](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191303/?sp=14) | Van Ness/Franklin/Gough × Sutter/Post/Geary | similarity | 4 | 32 | 0.31 | 0.64 | 0 | 96 |
| 1913_0242 | [00813_03_1913-0242](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191303/?sp=22) | Gough/Octavia/Laguna × Pine/Bush/Sutter | similarity | 5 | 36 | 0.19 | 0.49 | 0 | 166 |
| 1913_0243 | [00813_03_1913-0243](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191303/?sp=23) | Gough/Octavia/Laguna × Sutter/Post/Geary | similarity | 6 | 40 | 0.20 | 0.58 | 0 | 209 |
| 1913_0253 | [00813_03_1913-0253](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191303/?sp=33) | Laguna/Buchanan/Webster × Pine/Bush/Sutter | similarity | 4 | 32 | 0.13 | 0.32 | 0 | 262 |
| 1913_0254 | [00813_03_1913-0254](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191303/?sp=34) | Laguna/Buchanan/Webster × Sutter/Post/Geary | similarity | 4 | 32 | 0.30 | 0.65 | 0 | 227 |
| 1913_0265 | [00813_03_1913-0265](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191303/?sp=45) | Webster/Fillmore/Steiner × Pine/Bush/Sutter | similarity | 6 | 40 | 0.35 | 0.77 | 0 | 312 |
| 1913_0266 | [00813_03_1913-0266](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191303/?sp=46) | Webster/Fillmore/Steiner × Sutter/Post/Geary | similarity | 6 | 40 | 0.35 | 1.03 | 0 | 179 |
| 1913_0277 | [00813_03_1913-0277](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191303/?sp=57) | Steiner/Pierce/Scott × Bush/Sutter/Post | similarity | 4 | 32 | 0.30 | 0.63 | 0 | 165 |
| 1913_0289 | [00813_03_1913-0289](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191303/?sp=69) | Scott/Divisadero/Broderick × Pine/Bush/Sutter | similarity | 4 | 32 | 0.15 | 0.35 | 0 | 247 |
| 1913_0290 | [00813_03_1913-0290](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191303/?sp=70) | Scott/Divisadero/Broderick × Sutter/Post/Geary | similarity | 5 | 36 | 0.42 | 1.06 | 0 | 190 |
| 1913_0325 | [00813_04_1913-0325](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=5) | Van Ness/Franklin/Gough × Geary/Ofarrell/Ellis | similarity | 7 | 44 | 0.22 | 0.70 | 0 | 182 |
| 1913_0326 | [00813_04_1913-0326](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=6) | Van Ness/Franklin/Gough × Ellis/Eddy/Turk | similarity | 7 | 44 | 0.13 | 0.39 | 0 | 156 |
| 1913_0327 | [00813_04_1913-0327](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=7) | Van Ness/Franklin/Gough × Turk/Golden Gate/Mcallister | similarity | 7 | 44 | 0.20 | 0.62 | 0 | 142 |
| 1913_0328 | [00813_04_1913-0328](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=8) | Van Ness/Franklin/Gough × Mcallister/Fulton/Grove | similarity | 5 | 36 | 0.20 | 0.52 | 0 | 98 |
| 1913_0331 | [00813_04_1913-0331](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=11) | Gough/Octavia/Laguna × Geary/Ofarrell/Ellis | similarity | 6 | 40 | 0.15 | 0.35 | 0 | 192 |
| 1913_0332 | [00813_04_1913-0332](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=12) | Gough/Octavia/Laguna × Ellis/Eddy/Golden Gate/Mcallister | similarity | 6 | 40 | 0.12 | 0.30 | 0 | 204 |
| 1913_0333 | [00813_04_1913-0333](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=13) | Gough/Octavia/Laguna × Mcallister/Fulton/Grove | similarity | 6 | 36 | 0.19 | 0.45 | 1 | 216 |
| 1913_0337 | [00813_04_1913-0337](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=17) | Laguna/Buchanan/Webster × Geary/Ofarrell/Ellis | similarity | 6 | 40 | 0.18 | 0.47 | 0 | 276 |
| 1913_0338 | [00813_04_1913-0338](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=18) | Laguna/Buchanan/Webster × Ellis/Eddy/Turk | similarity | 6 | 40 | 0.15 | 0.43 | 0 | 279 |
| 1913_0339 | [00813_04_1913-0339](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=19) | Laguna/Buchanan/Webster × Turk/Golden Gate/Mcallister | similarity | 4 | 30 | 0.19 | 0.51 | 1 | 223 |
| 1913_0340 | [00813_04_1913-0340](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=20) | Laguna/Buchanan/Webster × Mcallister/Fulton/Grove | similarity | 6 | 40 | 0.38 | 0.87 | 0 | 283 |
| 1913_0345 | [00813_04_1913-0345](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=25) | Webster/Fillmore/Steiner × Geary/Ofarrell/Ellis | similarity | 5 | 36 | 0.15 | 0.48 | 0 | 168 |
| 1913_0346 | [00813_04_1913-0346](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=26) | Webster/Fillmore/Steiner × Ellis/Eddy/Turk | affine | 4 | 32 | 0.23 | 0.55 | 0 | 199 |
| 1913_0347 | [00813_04_1913-0347](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=27) | Webster/Fillmore/Steiner × Turk/Golden Gate/Mcallister | similarity | 4 | 32 | 0.25 | 0.68 | 0 | 180 |
| 1913_0348 | [00813_04_1913-0348](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=28) | Webster/Fillmore/Steiner × Mcallister/Fulton/Grove | affine | 4 | 32 | 0.09 | 0.20 | 0 | 238 |
| 1913_0355 | [00813_04_1913-0355](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=35) | Steiner/Pierce/Scott × Geary/Ofarrell/Ellis | similarity | 4 | 28 | 0.18 | 0.48 | 2 | 284 |
| 1913_0356 | [00813_04_1913-0356](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=36) | Steiner/Pierce/Scott × Ellis/Eddy/Turk | similarity | 6 | 40 | 0.14 | 0.35 | 0 | 264 |
| 1913_0357 | [00813_04_1913-0357](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=37) | Steiner/Pierce/Scott × Turk/Golden Gate/Mcallister | similarity | 5 | 36 | 0.15 | 0.37 | 0 | 235 |
| 1913_0358 | [00813_04_1913-0358](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=38) | Steiner/Pierce/Scott × Mcallister/Fulton/Hayes/Fell | similarity | 4 | 32 | 0.17 | 0.41 | 0 | 124 |
| 1913_0367 | [00813_04_1913-0367](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=47) | Scott/Divisadero/Broderick × Geary/Ofarrell/Ellis | affine | 5 | 36 | 0.16 | 0.46 | 0 | 315 |
| 1913_0368 | [00813_04_1913-0368](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=48) | Scott/Divisadero/Broderick × Ellis/Eddy/Turk | affine | 4 | 32 | 0.09 | 0.18 | 0 | 234 |
| 1913_0369 | [00813_04_1913-0369](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=49) | Scott/Divisadero/Broderick × Turk/Golden Gate/Mcallister | similarity | 5 | 36 | 0.16 | 0.37 | 0 | 177 |
| 1913_0370 | [00813_04_1913-0370](https://www.loc.gov/resource/g4364sm.g4364sm_g00813191304/?sp=50) | Scott/Divisadero/Broderick × Mcallister/Fulton/Grove | affine | 4 | 32 | 0.17 | 0.41 | 0 | 221 |

## Known problems

* **Storey reading is partial**: 52–55 % of the sections are read.
  * The classifier knows only 1, 2, 3 (± B, 1½). Marks of 4 storeys and more, and "2½B" / "3½B", are not in its
    training set: they are either missed (→ estimated, usually 2) or misread as 2 or 3. This matters for
    the 4–6 storey apartment buildings and warehouses on Fillmore, Geary and Divisadero.
  * The commonest error is a lone slanted stroke (a letter of a word, a "/") read as "1". About 740 read sections
    ≥ 40 m² in 1913 are 1-storey; most are stores, stables and garages, but some are misreads.
  * Estimates are medians, so every unread frame house gets 2 storeys.
* **Use** is read only from D / F ("Flats") / S letters and the X symbol: about 30 % of the sections. "other" means
  "not read".
* **Sections, not whole buildings**: a house with a 1-storey rear wing gives two features. Adjacent sections can be
  dissolved by touching boundary and lot if whole buildings are needed (the lot lines are not traced).
* Porches, stairs, light wells and uncoloured open sheds are not traced. Bay windows are part of the footprint and
  project up to about 1 m over the property line, as on the map.
* **Material**: blue covers "stone, concrete or concrete block" on the 1913 key (exported as `stone`); brown
  "fire proof" is exported as `concrete`. The 1899 green "frame special" is exported as `frame` with
  `frame_special = true`. No grey "iron" buildings were found.
* **Geary**: the 1913 Geary St is placed on the straight line of downtown Geary St, v = 313.7. The residuals on
  Geary sides are as small as elsewhere, which supports this.
* **Alley widths** are not used as constraints: each alley's position follows from the to-scale lot depths on both
  sides. Checked on Willow and Larch (35 ft): within 0.35 m.
* The super-block Geary–O'Farrell × Steiner–Scott (Girls' High School and Hamilton Grammar School, blocks 705/706)
  is drawn without Pierce St in both editions and is fitted as one block (RMS 0.15 m in 1913).
* `seen_*` and `today_iou` use a plain IoU threshold. Rebuilt houses on the same lot can match, and a section split
  differently in the two editions can fail to match. Use them as evidence, not truth.
* The `.pkl` intermediates in `data/interim/sanborn/` (gitignored) hold the pixel outlines and every corner
  constraint for re-checking.

## Re-running and extending

```
.venv/bin/pip install opencv-python-headless scikit-learn      # once
python pipeline/sanborn_trace.py download            # LOC IIIF 50 % JPEGs -> data/raw/sanborn/ (~1 MB/sheet, ~5 s each)
python pipeline/sanborn_trace.py trace [KEY ...]     # 6-15 s per sheet single-threaded; 4 processes in parallel ~2.5 min for all 68
python pipeline/sanborn_trace.py export              # ~15 s
```

To add a sheet:
1. Add a row to `sheets_western_addition.csv`:
   * the LOC image id and resource, from the item's `?fo=json` (`resources[0].files`);
   * the orientation;
   * the N-S streets from the top of the sheet to the bottom (`rows`) and the E-W streets from left to right
     (`cols`);
   * `present_cols` when a column holds a park.
2. Run `trace`, look at the residual line and at a `preview`, then `export`.

Agent time is about 3–5 minutes per sheet (spec row and checking) plus about 15 s of compute. Streets outside the
Western Addition grid would need their lines added to `NS` / `EW`.

Next sources worth tracing:
* The **1913–1950 corrected volumes** (`sanborn00813_032` … `_035`; vol. 4 = `sanborn00813_033`, "1913 – Oct
  1950"). They show the area just before clearance, which would give end years and the 1910s–40s infill.
* The rest of 1899 vol. 3 / 1900 vol. 5–6, for the parts of the Western Addition outside A-1/A-2.
