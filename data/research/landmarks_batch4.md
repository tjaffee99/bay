# Landmark research — batch 4: destroyed structures (`viewer/src/landmarks/batch4.ts`)

Companion to `landmarks.md`, `landmarks_batch3.md` and `landmark_audit.md`. One row per model below was appended
to `data/tables/landmarks.csv` (68 rows). The Tower of Jewels (`batch3.ts`) was re-placed from the Sanborn map
(see below); its older row in `landmarks.csv` still carries the estimated position.

## Confidence at a glance

| Group | Footprints | Heights | Confidence |
|---|---|---|---|
| PPIE 1915: 8 palaces of the walled city, Machinery, Horticulture, Festival Hall, Tower of Jewels | traced from the 1914–15 Sanborn map (±3 m) | Sanborn height figures + Official Guide / Todd | **high** (plan), medium (roof forms) |
| PPIE courts: arches, 6 towers 121 ft, 4 towers 206 ft, Tower of the Ages, Column of Progress, fountains | Sanborn positions | Sanborn | high (position/height), estimated stage proportions |
| PPIE Zone (75 concession buildings), state and foreign pavilions, Inside Inn, Aeroscope | Sanborn | estimated from footprint size (except Oregon 60 ft, California 40/45/106 ft, Denmark tower 80 ft, Aeroscope after Todd) | high (plan), **low** (most heights) |
| GGIE 1939: 7 exhibit halls, Tower of the Sun, Seven Seas / Pacifica, Elephant Towers | traced from the plan in the 1939 Official Guide Book (±9 m) | walls 70 ft (Guide), Tower 400 ft (Guide / James & Weller) | medium; end years estimated |
| El Presidio (1776 palisade, 1792 adobe square, c.1815 ranges with staggered ends) | sizes from early_sf.md (Sal, Vancouver); placement on the Officers' Club / Main Post axis estimated | Vancouver (walls 14 ft) / estimated | low–medium (1792), **low** (1815 square) |
| Castillo de San Joaquín + the 90-ft white cliff | horseshoe 125 × 105 ft, 14 embrasures (Eldredge) at Fort Point | cliff height documented, parapet estimated | medium (castillo), **low** (cliff outline) |
| Mission Dolores convento, quadrangle ranges, guard houses, 8 rancheria rows | positions/sizes from early_sf.csv (reasoned reconstruction) | early_sf.csv | **low** |
| Playland (Big Dipper, Shoot-the-Chutes, Fun House, carousel, midway) | blocks from DataSF; positions within them estimated | estimated | **low** |
| Woodward's Gardens, Mechanics' Pavilion, Sutro Heights | site from DataSF / park; buildings schematic | estimated | **low** |

## 1. Panama-Pacific International Exposition (1915)

### Source plan
- **Sanborn Map Co., "Panama-Pacific-International Exposition 1915, San Francisco, Cal."**, scale 100 ft to one inch,
  4 sheets (81 × 269 cm), "survey and inspection completed November 18, 1914", copyright 1914. Library of Congress,
  Geography and Map Division, https://www.loc.gov/item/sanborn00813_025/ (IIIF images `00813_1915-0001` … `-0004`,
  downloaded at 50 %, ≈ 0.205 m/px). Public domain. It shows every Exposition building as a footprint, coloured by
  construction (yellow wood, blue concrete — the Palace of Fine Arts is the only blue palace), with height figures
  in feet, floor areas, domes, towers, pools and the streets just outside the fence.
- Sheet 1 = the Zone and Fort Mason (Van Ness → Buchanan); sheet 2 = Webster → Scott (Machinery, the eastern palaces,
  Court of the Universe, Festival Hall); sheet 3 = Divisadero → the Presidio (western palaces, Palace of Fine Arts,
  Horticulture, state and foreign pavilions, Inside Inn); sheet 4 = livestock area, race track and the western
  states (not used — no street control; only minor pavilions).

### Georeferencing
- Control points: DataSF street-centreline intersections (`data/raw/sf_streets`) measured on the sheets as the
  midpoint of the kerb lines (refined on the darkest pixel column/row):
  - sheet 1: Chestnut × Buchanan, Laguna, Octavia, Gough, Franklin, Van Ness; North Point × Laguna
    (Bay × Laguna rejected: the modern Bay St bends there);
  - sheet 2: Chestnut and Lombard × Scott, Pierce, Steiner, Fillmore, Webster (Chestnut's centreline = south block
    line − ½ × 68.75 ft: the Exposition widened Chestnut to 125 ft);
  - sheet 3: Lombard × Baker (straight extension), Broderick, Divisadero; the Palace of Fine Arts rotunda (= the
    origin of the frame, the existing model's anchor).
- Similarity transforms per sheet: 0.2049 / 0.2056 / 0.2050 m/px, rotation 9.23° / 9.10° / 9.77°; residuals
  ≤ 2.9 m (sheet 1), ≤ 4.6 m (sheet 2), ≤ 1.7 m (sheet 3).
- Checks: (a) the traced 1915 Palace of Fine Arts hall and colonnades fall within 2–3 m of today's OSM outlines of
  the 1967 replica; (b) the sheets join without a step (Agriculture and Liberal Arts cross the 2/3 seam);
  (c) the traced Palace of Mines measures 23,480 m² against the 252,000 sq ft = 23,411 m² printed on the map
  (+0.3 %), Machinery 35,400 m² against 369,600 sq ft = 34,337 m² (+3 %, outline includes the vestibules);
  (d) Machinery measures 110 × 295 m against the documented 968 × 368 ft (295 × 112 m).
- The Exposition was laid out on the Marina street grid (Chestnut St at 80.89°), so all models are built in that
  frame (`u` along Chestnut, `v` across, origin = Fine Arts rotunda) — `PPIE_BRG = 350.89` in the code.

### Footprints
- Building masks = yellow/blue map colour (closing over the lines and lettering, small holes filled, courts kept),
  warped into the grid frame at 0.5 m/px, the sheet seams bridged; each palace cut out by a rectangle at the avenue
  / court axes (Court of the Universe axis u = 581, Court of Abundance axis u = 837, the E–W avenue v ≈ 6–8) and
  polygonised (Douglas–Peucker 1 m). The court colonnades and avenue arcades drawn as part of the palaces stay in
  the palace outlines.
- Zone / states / nations: every map building as its own polygon (0.7 m tolerance); hatched open areas (Grand
  Canyon, Yellowstone scenery, Toyland lawn) dropped by a solidity test; names assigned by hand from the map labels.
  The Zone climbs ~19 m from Fillmore St to Van Ness Ave, so each small building stands on its own ground
  (`groundDz`: `elevationAt` at the building minus at the group anchor, walls sunk 1.5 m); the Presidio ranges
  do the same.

### Heights and forms (sources)
- Palaces: "seventy feet to cornices, 113 feet to gables, and 160 feet to the top of central domes" (Official
  Guide 1915, Varied Industries); Liberal Arts "585 feet long, 470 feet wide, and 65 feet high" (Condensed Facts
  1915); Sanborn: walls 50 ft, gables 80 ft, wood domes 160 ft. Model: walls 65 ft (19.8 m), nave eaves 80 ft,
  gables 113 ft, domes 160 ft, dome radius from the Sanborn circles (≈ 31 m diameter). Dome positions read from the
  dome circles (Transportation and Manufactures measured exactly, the others read on the mosaic and symmetrised
  about the court axis, ±5 m). Floor areas and dimensions per palace from the Official Guide / Condensed Facts.
- Colours: Jules Guerin's palette (Todd 1921 vol. 1, the colour-scheme chapter; Official Guide 1915): "travertine" walls,
  "dome green" palace domes, burnt orange on domes about the Court of the Universe; roof planes estimated.
- Court of the Universe: 650 ft arch to arch, 1,200 ft Tower of Jewels → Column of Progress (Barry 1915); Sanborn:
  arches 156 ft, towers 121 ft (six), electric-fountain columns 88 ft, Column of Progress 185 ft "steel frame
  plastered outside". Barry gives 203 ft for the arches — taken as the top of the sculpture groups.
- Four "Italian" towers 206 ft (Sanborn) at the Courts of Palms and Flowers; the Court of Abundance "organ tower"
  (Tower of the Ages) 160 ft.
- Machinery: 968 × 368 ft; three naves 972 ft long and 110 ft high, three transverse naves 372 ft (Official Guide;
  Condensed Facts) — transverse nave positions estimated at the thirds.
- Horticulture: 672 × 320 ft, glass dome 152 ft diameter and 186 ft high (Official Guide; Sanborn "185'"), nave
  80 ft, aisles 50 ft (Condensed Facts), four corner glass domes 52 ft (Sanborn).
- Festival Hall: walls 46 ft, wood dome 156 ft, 220 ft to the top of the lantern, corner towers 112 ft (Sanborn);
  57,400 sq ft.
- Tower of Jewels: re-placed — base 39 m square centred at u 581.6, v −152 (37.802394, −122.441599), i.e. 38 m north
  and 3 m west of the batch-3 estimate; frame turned to the grid (−9.11°); its flanking walls replaced by the
  Sanborn's double colonnades (60 ft) to the palace walls.
- Oregon Building: "Parthenon with the bark on" — 48 Douglas-fir logs 5–6½ ft through and 42 ft high, 150 × 250 ft
  over all (Todd 1921 vol. 3, p. 331); Sanborn 60 ft. California Building: walls 40 ft, ballroom 45 ft, tower 106 ft
  (Sanborn). Danish pavilion tower 80 ft (Sanborn).
- Strauss Aeroscope: arm 200 ft beyond the trunnions and 38½ ft behind them, 380-ton counterweight, cabin for 120,
  top height 265 ft, trunnion tower 48 ft on a 60-ft circular track (Todd 1921 vol. 2, pp. 151–152); placed on the
  Sanborn's "Steel Aeroscope" circle (the 60-ft track is drawn ≈ 22 m across).
- Dates: open Feb 20 – Dec 4, 1915 and demolished 1916 (only the Palace of Fine Arts kept; already modelled).
  Construction spans in the models (palaces 1913.4 → 1915.13, Machinery 1912.9 → 1914.3, Zone/pavilions
  1914.3 → 1915.13) are ESTIMATES for the grow-in animation.

### Not modelled (PPIE)
- Sheet 4 (livestock exhibit, stadium, dairy building, Philippine Islands, Sweden, Massachusetts, Washington, Iowa,
  Kansas, Utah, Indiana, Idaho, Maryland, Montana, North Dakota, West Virginia, Arkansas): no street control on that
  sheet; it can be chained to sheet 3 along the seam (Canada straddles it) when needed.
- The palaces' portals, half-domes and corner minarets; the courts' colonnade figures; the South Gardens' pools;
  the Yacht Harbor and Marina seawall (they belong to the terrain).

## 2. Golden Gate International Exposition (1939–40)

### Source plan
- **Official Guide Book, Golden Gate International Exposition on San Francisco Bay (1939)**, Internet Archive
  `offboo00gold`, page n23 (the island plan with buildings in black/hatched, page 20 of the guide); legend letters
  per the "Cartograph of Treasure Island" (HABS CA-2785 data pages, fig. 1): B Mines, Metals & Machinery,
  C Electricity & Communications, D Hall of Science, F Ford Building, G Vacationland, H Foods & Beverages,
  J Agriculture Hall, K International Hall, L Homes & Gardens, M Hall of Air Transportation (Building 2),
  N Palace of Fine & Decorative Arts (Building 3), A Administration (Building 1), R Court of Honor and Tower of the
  Sun, U Court of the Seven Seas, V Court of Pacifica, O Portals of the Pacific, Q Northwest Passage.
- Georeferencing: A, M and N matched to the OSM centroids of the three surviving buildings, with the rotation fixed
  so that the Court of Honor → Court of Pacifica axis runs along the island grid (332°) — a free fit drifted 1.5°
  because the three controls lie on one line. Scale 0.545 m/px; residuals 2.7 / 5.7 / 8.5 m. The plan's island
  edge runs parallel to the TIGER shoreline. Halls cut out by rectangles and polygonised (1.5 m).
- Heights: "great 70-foot-high walls of stucco" (Guide); Tower of the Sun 400 ft, steel frame clothed in timber,
  22-ft golden phoenix, 44-bell carillon; sixteen 60-ft pylons with galleon prows in the Court of the Seven Seas;
  Pacifica 80 ft before a ~100 × 48 ft "prayer curtain" (James & Weller, *Treasure Island, "the Magic City"*, 1941).
- Fate: Navy from 1941; many palaces reused (Foods & Beverages as a mess hall); a 1947 fire destroyed three palaces
  and most of the rest were then demolished (HABS CA-2785, https://www.loc.gov/item/ca3486/). End years: halls 1947.6
  (estimated), Tower of the Sun 1942 (estimated, LOW), court sculpture 1941.5 (estimated).
- Not modelled: California State Building group, Federal Building (Colonnade of States, 104 ft), Hall of Western
  States, Cavalcade of the Golden West arena, the Gayway, foreign pavilions of the Pacific basin, Temple Compound —
  all traceable from the same plan.

## 3. El Presidio, Castillo de San Joaquín
- Dimensions and dates from `data/research/early_sf.md` §4.1–4.2 (written in parallel by the early-SF agent from
  Bancroft, Eldredge, Vancouver and the NPS / Presidio Trust archaeology), plus `data/raw/presidio/nhl_66000232_text.pdf`
  (NHL district nomination: three walled sides and a palisade or hedge on the east, chapel on the south side, the
  castillo's later "horseshoe" with the sallyport on the south) and `shs.txt` (1852: "rows of one-story adobe
  buildings on two sides of a square").
- Placement: frame 30° (Main Post axis; Officers' Club OSM outline at 27.9°/117.9°), origin = the Officers' Club
  centroid. 1776: Moraga's square of 92 varas (77 m), rush-thatched wooden buildings. 1792: Sal's "square of 120
  yards" (110 m), three sides adobe and stone with walls ~14 ft high and 5 ft thick (Vancouver), a palisade on the
  fourth, thatched; comandancia 37 × 6 varas on the west side near the NW corner and chapel 19 × 8 varas (Sal's key).
  c.1815–18: rebuilt around a larger square with tile roofs and two gates — the side (150 m) and its offset east of
  the Officers' Club (Pershing Square lies in the west part of the c.1815 quadrangle) are ESTIMATES.
- Decline: north and east ranges end Feb 1844 (ruins, tiles and timber taken); west range 1857 and south range 1862
  (US Army reuse; "two sides of a square" in 1852) — estimated. The 1815 adobe core of the Officers' Club is left to
  the city buildings layer.
- Castillo: begun Aug 1793, blessed Dec 8, 1794; horseshoe ≈ 125 × 105 ft (Eldredge; Bancroft 100 × 120 ft), parapet
  10 ft thick, 14 brick-lined embrasures, barrack in the middle, 8 guns in 1794. It stands on a separate cliff
  landmark (`punta_del_cantil_blanco`): the 90-ft white cliff (Wikipedia; "about 100 ft", Eldredge) that the Army cut
  down to 15 ft in 1853–54 — 22.8 m above today's ground, running inland (SSE) until today's terrain reaches the old
  cliff-top level (~25 m, 150–180 m inland); outline ESTIMATED; it ends 1853.5 when Fort Point begins.

## 4. Mission Dolores compound
- Built from the rows of `data/tables/early_sf.csv` that describe the compound — `mis_convento`,
  `mis_quadrangle_north`, `mis_quadrangle_west`, `mis_guardhouse`, `mis_rancheria_row_1` … `_8` — with their
  positions, sizes, bearings and years (convento 40 × 10 m on the north side of the church fronting Dolores St, with
  its corridor; the 1794 storehouse (150 ft) and 1795 building (180 ft) closing a ~40 m court; eight 72 × 6 m adobe
  row-house ranges across Dolores St on the Notre Dame Plaza site, with staggered decay). These are reasoned
  reconstructions (LOW CONFIDENCE) by the early-SF agent; **when early_sf.csv is rendered, skip those twelve ids**
  (the workshops, mills, outbuildings, dairy and first-site rows are not modelled here).

## 5. Playland, Woodward's Gardens, Mechanics' Pavilion, Sutro Heights
- Playland: Great Highway between Balboa and Fulton (Wikipedia), blocks from DataSF centrelines; Big Dipper 1922–55,
  Shoot-the-Chutes 1921–50, Looff carousel house c. 1913–72, Fun House (opening year estimated) – 1972, torn down
  from Sep 4, 1972. Positions within the blocks are estimates (the 1938 Harrison Ryker mosaic would fix them).
- Woodward's Gardens (1866–1891): the two blocks between Mission, Valencia, Duboce/13th and 15th (Wikipedia; DataSF
  for the streets); museum, art gallery, conservatory, pavilion, lake, animal houses placed schematically.
- Mechanics' Pavilion (1882–1906): the whole block of Larkin/Polk/Grove/Hayes (DataSF), ≈ 125 × 82 m; wall and roof
  heights and the Larkin St towers estimated.
- Sutro Heights: mansion (1880s–1939, WPA demolition) and parapet; positions on the plateau estimated.

## Overlap with the generic pre-1906 layer (action for the main session)
`data/tables/notable_pre1906.csv` already places generic extrusions for `mechanics_pavilion_1882` (1882–1906, 4.5 m),
`woodwards_gardens_1866` (1866–1891, 15 m over the whole lot) and `sutro_mansion_1881` (1881–1939, 9 m). With the
batch-4 landmarks these are double geometry; drop those three rows (or skip them in `sf_predecessors.py`) and
re-run the predecessors/export stages.

## Not modelled this session
- **Crystal Palace Baths** — location/dates could not be verified (Wikipedia/Wikimedia rate-limited, FoundSF 404).
- PPIE sheet 4 pavilions; GGIE secondary buildings (see above); the US-era Presidio Main Post buildings.

## Tooling (scratchpad, not committed)
`b4/py/`: `refine.py` (kerb-line refinement), `fit_all.py` + `georef.py` (per-sheet similarity fits), `mosaic.py`
(warp sheets into the grid frame with a 10 m grid), `gridmask.py`, `items.py`, `smalls.py`, `gen_ppie.py`,
`gen_small.py` (Sanborn → TypeScript tables), `ggie_grid.py`, `gen_ggie.py` (GGIE plan), `check_ppie.py`, `site.py`
(model top views over the source plans / OSM / DataSF). Checks: every PPIE and GGIE model was drawn back over its
source plan (`chk_center.png`, `chk_west.png`, `chk_zone.png`, `chk_ggie.png`).

## Items
### Palace of Food Products (PPIE 1915) (`ppie_food_products`)

- Model years: construction 1913.4 → 1915.13, end 1916.3; anchor 37.804226, -122.446072; top 51.5 m; 405 triangles.
- Exposition: Panama-Pacific International Exposition, Feb 20 – Dec 4, 1915; palaces demolished 1916
- Size: 236,690 sq ft (Sanborn / Condensed Facts)
- Architects: Bliss & Faville (walled-city facades); one of the eight palaces of the "walled city"
- Heights: walls 65 ft (Condensed Facts; Sanborn 50 ft to the eaves, Official Guide 70 ft to the cornices), gables 113 ft, central dome 160 ft (Sanborn, Official Guide)
- Model: footprint traced from the 1915 Sanborn map (incl. the court colonnades and arcades); nave widths, crossing tower and dome radius (Sanborn circle ≈ 31 m) from the plan; roof colours estimated
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Palace of Agriculture (PPIE 1915) (`ppie_agriculture`)

- Model years: construction 1913.4 → 1915.13, end 1916.3; anchor 37.804569, -122.443722; top 51.5 m; 458 triangles.
- Exposition: Panama-Pacific International Exposition, Feb 20 – Dec 4, 1915; palaces demolished 1916
- Size: 328,633 sq ft
- Architects: Bliss & Faville; one of the eight palaces of the "walled city"
- Heights: walls 65 ft (Condensed Facts; Sanborn 50 ft to the eaves, Official Guide 70 ft to the cornices), gables 113 ft, central dome 160 ft (Sanborn, Official Guide)
- Model: footprint traced from the 1915 Sanborn map (incl. the court colonnades and arcades); nave widths, crossing tower and dome radius (Sanborn circle ≈ 31 m) from the plan; roof colours estimated
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Palace of Education and Social Economy (PPIE 1915) (`ppie_education`)

- Model years: construction 1913.4 → 1915.13, end 1916.3; anchor 37.802395, -122.445709; top 51.5 m; 372 triangles.
- Exposition: Panama-Pacific International Exposition, Feb 20 – Dec 4, 1915; palaces demolished 1916
- Size: 394 × 526 ft, 205,100 sq ft; Half Dome of Philosophy entrance (113 ft)
- Architects: Bliss & Faville; one of the eight palaces of the "walled city"
- Heights: walls 65 ft (Condensed Facts; Sanborn 50 ft to the eaves, Official Guide 70 ft to the cornices), gables 113 ft, central dome 160 ft (Sanborn, Official Guide)
- Model: footprint traced from the 1915 Sanborn map (incl. the court colonnades and arcades); nave widths, crossing tower and dome radius (Sanborn circle ≈ 31 m) from the plan; roof colours estimated
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Palace of Liberal Arts (PPIE 1915) (`ppie_liberal_arts`)

- Model years: construction 1913.4 → 1915.13, end 1916.3; anchor 37.802728, -122.443422; top 51.5 m; 525 triangles.
- Exposition: Panama-Pacific International Exposition, Feb 20 – Dec 4, 1915; palaces demolished 1916
- Size: 475 × 585 ft, 251,300 sq ft
- Architects: Bliss & Faville; one of the eight palaces of the "walled city"
- Heights: walls 65 ft (Condensed Facts; Sanborn 50 ft to the eaves, Official Guide 70 ft to the cornices), gables 113 ft, central dome 160 ft (Sanborn, Official Guide)
- Model: footprint traced from the 1915 Sanborn map (incl. the court colonnades and arcades); nave widths, crossing tower and dome radius (Sanborn circle ≈ 31 m) from the plan; roof colours estimated
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Palace of Transportation (PPIE 1915) (`ppie_transportation`)

- Model years: construction 1913.4 → 1915.13, end 1916.3; anchor 37.804994, -122.440526; top 51.5 m; 433 triangles.
- Exposition: Panama-Pacific International Exposition, Feb 20 – Dec 4, 1915; palaces demolished 1916
- Size: 314,000 sq ft
- Architects: Bliss & Faville; one of the eight palaces of the "walled city"
- Heights: walls 65 ft (Condensed Facts; Sanborn 50 ft to the eaves, Official Guide 70 ft to the cornices), gables 113 ft, central dome 160 ft (Sanborn, Official Guide)
- Model: footprint traced from the 1915 Sanborn map (incl. the court colonnades and arcades); nave widths, crossing tower and dome radius (Sanborn circle ≈ 31 m) from the plan; roof colours estimated
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Palace of Manufactures (PPIE 1915) (`ppie_manufactures`)

- Model years: construction 1913.4 → 1915.13, end 1916.3; anchor 37.803148, -122.440110; top 51.5 m; 527 triangles.
- Exposition: Panama-Pacific International Exposition, Feb 20 – Dec 4, 1915; palaces demolished 1916
- Size: 475 × 552 ft, 234,000 sq ft
- Architects: Bliss & Faville; one of the eight palaces of the "walled city"
- Heights: walls 65 ft (Condensed Facts; Sanborn 50 ft to the eaves, Official Guide 70 ft to the cornices), gables 113 ft, central dome 160 ft (Sanborn, Official Guide)
- Model: footprint traced from the 1915 Sanborn map (incl. the court colonnades and arcades); nave widths, crossing tower and dome radius (Sanborn circle ≈ 31 m) from the plan; roof colours estimated
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Palace of Mines and Metallurgy (PPIE 1915) (`ppie_mines`)

- Model years: construction 1913.4 → 1915.13, end 1916.3; anchor 37.805257, -122.438161; top 51.5 m; 405 triangles.
- Exposition: Panama-Pacific International Exposition, Feb 20 – Dec 4, 1915; palaces demolished 1916
- Size: 252,000 sq ft
- Architects: Bliss & Faville; one of the eight palaces of the "walled city"
- Heights: walls 65 ft (Condensed Facts; Sanborn 50 ft to the eaves, Official Guide 70 ft to the cornices), gables 113 ft, central dome 160 ft (Sanborn, Official Guide)
- Model: footprint traced from the 1915 Sanborn map (incl. the court colonnades and arcades); nave widths, crossing tower and dome radius (Sanborn circle ≈ 31 m) from the plan; roof colours estimated
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Palace of Varied Industries (PPIE 1915) (`ppie_varied_industries`)

- Model years: construction 1913.4 → 1915.13, end 1916.3; anchor 37.803401, -122.437776; top 51.5 m; 407 triangles.
- Exposition: Panama-Pacific International Exposition, Feb 20 – Dec 4, 1915; palaces demolished 1916
- Size: 414 × 541 ft, 219,000 sq ft; south portal after the Hospital of Santa Cruz, Toledo
- Architects: Bliss & Faville; one of the eight palaces of the "walled city"
- Heights: walls 65 ft (Condensed Facts; Sanborn 50 ft to the eaves, Official Guide 70 ft to the cornices), gables 113 ft, central dome 160 ft (Sanborn, Official Guide)
- Model: footprint traced from the 1915 Sanborn map (incl. the court colonnades and arcades); nave widths, crossing tower and dome radius (Sanborn circle ≈ 31 m) from the plan; roof colours estimated
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Court of the Universe (PPIE 1915) (`ppie_court_of_the_universe`)

- Model years: construction 1913.4 → 1915.13, end 1916.3; anchor 37.803787, -122.441887; top 61.9 m; 808 triangles.
- Court: largest court of the Exposition (McKim, Mead & White): 650 ft from arch to arch, 1,200 ft from the Tower of Jewels to the Column of Progress (Barry 1915)
- Arches: Arches of the Rising Sun (east) and Setting Sun (west): 156 ft on the Sanborn map; 203 ft to the top of the sculpture groups (Barry)
- Towers: six towers 121 ft; two electric fountain columns 88 ft; Column of Progress 185 ft (Sanborn)
- Model: positions and footprints from the Sanborn map; arch opening and pier proportions, tower stages and the sculpture blocks estimated from period photographs
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://www.gutenberg.org/ebooks/3151, https://archive.org/details/officialguidepa00pana

### Italian towers and Tower of the Ages (PPIE 1915) (`ppie_court_towers`)

- Model years: construction 1913.4 → 1915.13, end 1916.3; anchor 37.803207, -122.441839; top 62.8 m; 290 triangles.
- Italian towers: four towers 206 ft flanking the Courts of Palms and Flowers on the Avenue of Palms (Sanborn); "the four Italian Renaissance towers" (Barry)
- Tower of the Ages: Court of Abundance (Court of Ages), 160 ft (Sanborn "organ tower 160' high")
- Model: positions and heights from the Sanborn map; stage proportions estimated
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://www.gutenberg.org/ebooks/3151

### Palace of Machinery (PPIE 1915) (`ppie_palace_of_machinery`)

- Model years: construction 1912.9 → 1914.3, end 1916.3; anchor 37.804546, -122.435980; top 33.5 m; 239 triangles.
- Built: first exhibit palace of the Exposition (Ward & Blohme), 1913–14; the largest wooden building of its time
- Size: 968 × 368 ft, 369,600 sq ft (Condensed Facts; Sanborn area 369,600 sq ft); three naves 972 ft long and 110 ft high, three transverse naves 372 ft (Official Guide)
- Fate: demolished 1916
- Model: footprint traced from the Sanborn map; positions of the transverse naves and wall height estimated
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/condensedfactsco00panarich, https://archive.org/details/storyofexpositio01todd

### Palace of Horticulture (PPIE 1915) (`ppie_palace_of_horticulture`)

- Model years: construction 1913.4 → 1915.13, end 1916.3; anchor 37.800657, -122.444879; top 56.4 m; 758 triangles.
- Architects: Bakewell & Brown; modelled on the Mosque of Ahmed I (Official Guide)
- Size: 672 × 320 ft, 201,000 sq ft; glass dome 152 ft in diameter, 186 ft high; nave 80 ft, side aisles 50 ft (Condensed Facts, Official Guide)
- Fate: demolished 1916
- Model: outline, dome and corner-dome positions from the Sanborn map; wing nave and drum heights estimated
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/condensedfactsco00panarich

### Festival Hall (PPIE 1915) (`ppie_festival_hall`)

- Model years: construction 1913.4 → 1915.13, end 1916.3; anchor 37.801485, -122.438447; top 67 m; 660 triangles.
- Architect: Robert Farquhar; seated 3,000 for the Exposition's concerts and congresses
- Heights: walls 46 ft, wood dome 156 ft, 220 ft to the top of the lantern, four corner towers 112 ft (Sanborn)
- Size: 57,400 sq ft (Condensed Facts)
- Model: footprint and heights from the Sanborn map; drum and lantern proportions estimated
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/condensedfactsco00panarich, https://archive.org/details/officialguidepa00pana

### Strauss Aeroscope (PPIE 1915) (`ppie_aeroscope`)

- Model years: construction 1914.6 → 1915.13, end 1916.3; anchor 37.802541, -122.427364; top 55.4 m; 116 triangles.
- Designer: Joseph B. Strauss (later chief engineer of the Golden Gate Bridge)
- Ride: a steel arm lifted a two-storey cabin for 120 passengers to 265 ft; arm 200 ft beyond the trunnions, 38½ ft behind them to a 380-ton counterweight; trunnion tower 48 ft on a 60-ft circular track (Todd 1921)
- Model: position and track from the Sanborn map ("Steel Aeroscope"); shown with the arm raised at 40° (the ride swung it from ground level to 265 ft)
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/storyofexpositio02todd

### Oregon Building (PPIE 1915) (`ppie_oregon_building`)

- Model years: construction 1914.3 → 1914.84, end 1921.0 (LOW CONFIDENCE; audit 2026-11); anchor 37.805905, -122.449409; top 18.3 m; 612 triangles.
- Built: a "Parthenon with the bark on" (Foulkes & Hogue), dedicated Halloween 1914
- Colonnade: 48 Douglas-fir logs (one per state), 5 to 6½ ft through and 42 ft high, about 20 tons each; 150 × 250 ft over all (Todd 1921, vol. 3); 60 ft on the Sanborn map
- Fate: not demolished in 1916: it stood on Presidio ground and the Army kept it as a military clubhouse (NPS, https://www.nps.gov/goga/learn/historyculture/ppie-legacy.htm); torn down about 1921 (one photo caption; unverified)
- Model: platform outline from the Sanborn map; column spacing (18 × 8) estimated
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/storyofexpositio03todd

### California Building (PPIE 1915) (`ppie_california_building`)

- Model years: construction 1914.3 → 1915.13, end 1916.3; anchor 37.805876, -122.447731; top 32.3 m; 135 triangles.
- Building: the largest state building, Mission revival, housing the exhibits of the California counties ("California Counties Building" on the Sanborn map); ballroom 45 ft, tower 106 ft (Sanborn)
- Model: footprint from the Sanborn map (walls 40 ft); tower stages estimated
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### The Zone (PPIE 1915 amusement street) (`ppie_the_zone`)

- Model years: construction 1914.3 → 1915.13, end 1916.3; anchor 37.803413, -122.430242; top 14 m; 3081 triangles.
- Zone: 65-acre amusement street ("the Joy Zone") from Van Ness Ave to Fillmore St: Toyland, the Panama Canal working model, Creation, the Submarines, Evolution of the Dreadnaught, the 101 Ranch, Yellowstone and the Grand Canyon (Santa Fe), Battle of Gettysburg, Chinese Village, Samoan villages, Racing Coaster
- Model: every concession building traced from the 1914 Sanborn map (open/hatched show grounds left out); heights estimated from the footprint size
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Canada Pavilion (PPIE 1915) (`ppie_canada_pavilion`)

- Model years: construction 1914.3 → 1915.13, end 1916.3; anchor 37.803831, -122.452204; top 12 m; 142 triangles.
- Exposition: Panama-Pacific International Exposition, 1915 — largest foreign pavilion, on the Avenue of the Nations
- Model: footprint from the 1914 Sanborn map; heights estimated from the footprint size (Sanborn storey figures not transcribed)
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### New York State Building (PPIE 1915) (`ppie_new_york_building`)

- Model years: construction 1914.3 → 1915.13, end 1916.3; anchor 37.805290, -122.449274; top 11 m; 85 triangles.
- Exposition: Panama-Pacific International Exposition, 1915 — Avenue of the States
- Model: footprint from the 1914 Sanborn map; heights estimated from the footprint size (Sanborn storey figures not transcribed)
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Pennsylvania Building (PPIE 1915) (`ppie_pennsylvania_building`)

- Model years: construction 1914.3 → 1915.13, end 1916.3; anchor 37.805105, -122.450322; top 8 m; 100 triangles.
- Exposition: Panama-Pacific International Exposition, 1915 — colonial style, suggested by Independence Hall (Official Guide)
- Model: footprint from the 1914 Sanborn map; heights estimated from the footprint size (Sanborn storey figures not transcribed)
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Italian Pavilion (PPIE 1915) (`ppie_italy_pavilion`)

- Model years: construction 1914.3 → 1915.13, end 1916.3; anchor 37.801899, -122.449705; top 12 m; 97 triangles.
- Exposition: Panama-Pacific International Exposition, 1915 — villa group on the Avenue of the Nations south of the Fine Arts lagoon
- Model: footprint from the 1914 Sanborn map; heights estimated from the footprint size (Sanborn storey figures not transcribed)
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Japanese Pavilion and garden (PPIE 1915) (`ppie_japan_pavilion`)

- Model years: construction 1914.3 → 1915.13, end 1916.3; anchor 37.800430, -122.448027; top 8 m; 93 triangles.
- Exposition: Panama-Pacific International Exposition, 1915 — pavilions in a Japanese garden
- Model: footprint from the 1914 Sanborn map; heights estimated from the footprint size (Sanborn storey figures not transcribed)
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Chinese Pavilion (PPIE 1915) (`ppie_china_pavilion`)

- Model years: construction 1914.3 → 1915.13, end 1916.3; anchor 37.803868, -122.451316; top 8 m; 139 triangles.
- Exposition: Panama-Pacific International Exposition, 1915 — group of pavilions in a walled garden
- Model: footprint from the 1914 Sanborn map; heights estimated from the footprint size (Sanborn storey figures not transcribed)
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Netherlands Pavilion (PPIE 1915) (`ppie_netherlands_pavilion`)

- Model years: construction 1914.3 → 1915.13, end 1916.3; anchor 37.804483, -122.449028; top 11 m; 127 triangles.
- Exposition: Panama-Pacific International Exposition, 1915 — Avenue of the Nations, by the Fine Arts lagoon
- Model: footprint from the 1914 Sanborn map; heights estimated from the footprint size (Sanborn storey figures not transcribed)
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Argentine Republic Pavilion (PPIE 1915) (`ppie_argentina_pavilion`)

- Model years: construction 1914.3 → 1915.13, end 1916.3; anchor 37.804242, -122.449864; top 11 m; 94 triangles.
- Exposition: Panama-Pacific International Exposition, 1915 — Avenue of the Nations
- Model: footprint from the 1914 Sanborn map; heights estimated from the footprint size (Sanborn storey figures not transcribed)
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Australian Pavilion (PPIE 1915) (`ppie_australia_pavilion`)

- Model years: construction 1914.3 → 1915.13, end 1916.3; anchor 37.799636, -122.450478; top 11 m; 106 triangles.
- Exposition: Panama-Pacific International Exposition, 1915 — Avenue of the Nations
- Model: footprint from the 1914 Sanborn map; heights estimated from the footprint size (Sanborn storey figures not transcribed)
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Turkish Pavilion (PPIE 1915) (`ppie_turkey_pavilion`)

- Model years: construction 1914.3 → 1915.13, end 1916.3; anchor 37.803000, -122.450148; top 11 m; 73 triangles.
- Exposition: Panama-Pacific International Exposition, 1915 — Avenue of the Nations
- Model: footprint from the 1914 Sanborn map; heights estimated from the footprint size (Sanborn storey figures not transcribed)
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Danish Pavilion (PPIE 1915) (`ppie_denmark_pavilion`)

- Model years: construction 1914.3 → 1915.13, end 1916.3; anchor 37.801429, -122.448534; top 24.4 m; 63 triangles.
- Exposition: Panama-Pacific International Exposition, 1915 — Avenue of the Nations
- Note: tower 80 ft (Sanborn)
- Model: footprint from the 1914 Sanborn map; heights estimated from the footprint size (Sanborn storey figures not transcribed)
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Inside Inn (PPIE 1915) (`ppie_inside_inn`)

- Model years: construction 1914.3 → 1915.13, end 1916.3; anchor 37.799100, -122.446676; top 12 m; 130 triangles.
- Exposition: Panama-Pacific International Exposition, 1915 — the Exposition hotel inside the grounds by the Baker St entrance (from plans, Nov 1914)
- Model: footprint from the 1914 Sanborn map; heights estimated from the footprint size (Sanborn storey figures not transcribed)
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### State buildings on the Avenue of the States (PPIE 1915) (`ppie_state_buildings`)

- Model years: construction 1914.3 → 1915.13, end 1916.3; anchor 37.805138, -122.450179; top 11 m; 450 triangles.
- Exposition: Panama-Pacific International Exposition, 1915 — Virginia (Mount Vernon), Missouri, Nevada, Wisconsin, New Jersey, Ohio, Illinois and the Territory of Hawaii
- Model: footprint from the 1914 Sanborn map; heights estimated from the footprint size (Sanborn storey figures not transcribed)
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Other foreign pavilions (PPIE 1915) (`ppie_foreign_pavilions`)

- Model years: construction 1914.3 → 1915.13, end 1916.3; anchor 37.801467, -122.449410; top 11 m; 492 triangles.
- Exposition: Panama-Pacific International Exposition, 1915 — Portugal, Cuba, New Zealand, Honduras, Kali Syndicate and smaller pavilions; fire station No. 3; lagoon restaurant
- Model: footprint from the 1914 Sanborn map; heights estimated from the footprint size (Sanborn storey figures not transcribed)
- Sources: https://www.loc.gov/item/sanborn00813_025/, https://archive.org/details/officialguidepa00pana, https://archive.org/details/storyofexpositio01todd, https://en.wikipedia.org/wiki/Panama%E2%80%93Pacific_International_Exposition

### Mines, Metals and Machinery Building (GGIE 1939) (`ggie_mines`)

- Model years: construction 1937.6 → 1939.13, end 1947.6; anchor 37.819066, -122.371571; top 21.3 m; 298 triangles.
- Exposition: Golden Gate International Exposition, Feb 18 – Oct 29, 1939 and May 25 – Sep 29, 1940; B on the 1939 plan
- Walls: "great 70-foot-high walls of stucco, flecked with iridescent vermiculite" — windowless palaces in the "Pacifica" style (Official Guide 1939)
- Fate: taken over by the Navy in 1941; many palaces reused, a 1947 fire destroyed three and most of the rest were demolished afterwards (HABS CA-2785)
- Model: footprint traced from the plan in the 1939 Official Guide Book (georeferenced on Buildings 1–3, ±9 m); END YEAR ESTIMATED (1947) for each hall; pylons and setbacks not modelled
- Sources: https://archive.org/details/offboo00gold, https://archive.org/details/treasureislandma00jamerich, https://www.loc.gov/item/ca3486/, https://en.wikipedia.org/wiki/Golden_Gate_International_Exposition

### Homes and Gardens Building (GGIE 1939) (`ggie_homes`)

- Model years: construction 1937.6 → 1939.13, end 1947.6; anchor 37.819476, -122.370156; top 21.3 m; 143 triangles.
- Exposition: Golden Gate International Exposition, Feb 18 – Oct 29, 1939 and May 25 – Sep 29, 1940; L on the 1939 plan
- Walls: "great 70-foot-high walls of stucco, flecked with iridescent vermiculite" — windowless palaces in the "Pacifica" style (Official Guide 1939)
- Fate: taken over by the Navy in 1941; many palaces reused, a 1947 fire destroyed three and most of the rest were demolished afterwards (HABS CA-2785)
- Model: footprint traced from the plan in the 1939 Official Guide Book (georeferenced on Buildings 1–3, ±9 m); END YEAR ESTIMATED (1947) for each hall; pylons and setbacks not modelled
- Sources: https://archive.org/details/offboo00gold, https://archive.org/details/treasureislandma00jamerich, https://www.loc.gov/item/ca3486/, https://en.wikipedia.org/wiki/Golden_Gate_International_Exposition

### International Hall and Agriculture Hall (GGIE 1939) (`ggie_intl`)

- Model years: construction 1937.6 → 1939.13, end 1947.6; anchor 37.820757, -122.369385; top 21.3 m; 203 triangles.
- Exposition: Golden Gate International Exposition, Feb 18 – Oct 29, 1939 and May 25 – Sep 29, 1940; K and J on the 1939 plan (one continuous block)
- Walls: "great 70-foot-high walls of stucco, flecked with iridescent vermiculite" — windowless palaces in the "Pacifica" style (Official Guide 1939)
- Fate: taken over by the Navy in 1941; many palaces reused, a 1947 fire destroyed three and most of the rest were demolished afterwards (HABS CA-2785)
- Model: footprint traced from the plan in the 1939 Official Guide Book (georeferenced on Buildings 1–3, ±9 m); END YEAR ESTIMATED (1947) for each hall; pylons and setbacks not modelled
- Sources: https://archive.org/details/offboo00gold, https://archive.org/details/treasureislandma00jamerich, https://www.loc.gov/item/ca3486/, https://en.wikipedia.org/wiki/Golden_Gate_International_Exposition

### Foods and Beverages Building (GGIE 1939) (`ggie_foods`)

- Model years: construction 1937.6 → 1939.13, end 1947.6; anchor 37.821579, -122.370005; top 21.3 m; 238 triangles.
- Exposition: Golden Gate International Exposition, Feb 18 – Oct 29, 1939 and May 25 – Sep 29, 1940; H on the 1939 plan; used by the Navy as a mess hall
- Walls: "great 70-foot-high walls of stucco, flecked with iridescent vermiculite" — windowless palaces in the "Pacifica" style (Official Guide 1939)
- Fate: taken over by the Navy in 1941; many palaces reused, a 1947 fire destroyed three and most of the rest were demolished afterwards (HABS CA-2785)
- Model: footprint traced from the plan in the 1939 Official Guide Book (georeferenced on Buildings 1–3, ±9 m); END YEAR ESTIMATED (1947) for each hall; pylons and setbacks not modelled
- Sources: https://archive.org/details/offboo00gold, https://archive.org/details/treasureislandma00jamerich, https://www.loc.gov/item/ca3486/, https://en.wikipedia.org/wiki/Golden_Gate_International_Exposition

### Vacationland (GGIE 1939) (`ggie_vacation`)

- Model years: construction 1937.6 → 1939.13, end 1947.6; anchor 37.822527, -122.372225; top 21.3 m; 248 triangles.
- Exposition: Golden Gate International Exposition, Feb 18 – Oct 29, 1939 and May 25 – Sep 29, 1940; G on the 1939 plan, east side of the Court of the Seven Seas
- Walls: "great 70-foot-high walls of stucco, flecked with iridescent vermiculite" — windowless palaces in the "Pacifica" style (Official Guide 1939)
- Fate: taken over by the Navy in 1941; many palaces reused, a 1947 fire destroyed three and most of the rest were demolished afterwards (HABS CA-2785)
- Model: footprint traced from the plan in the 1939 Official Guide Book (georeferenced on Buildings 1–3, ±9 m); END YEAR ESTIMATED (1947) for each hall; pylons and setbacks not modelled
- Sources: https://archive.org/details/offboo00gold, https://archive.org/details/treasureislandma00jamerich, https://www.loc.gov/item/ca3486/, https://en.wikipedia.org/wiki/Golden_Gate_International_Exposition

### Hall of Science and Electricity and Communications Building (GGIE 1939) (`ggie_science`)

- Model years: construction 1937.6 → 1939.13, end 1947.6; anchor 37.821960, -122.373380; top 21.3 m; 163 triangles.
- Exposition: Golden Gate International Exposition, Feb 18 – Oct 29, 1939 and May 25 – Sep 29, 1940; D and C on the 1939 plan, west side of the Court of the Seven Seas
- Walls: "great 70-foot-high walls of stucco, flecked with iridescent vermiculite" — windowless palaces in the "Pacifica" style (Official Guide 1939)
- Fate: taken over by the Navy in 1941; many palaces reused, a 1947 fire destroyed three and most of the rest were demolished afterwards (HABS CA-2785)
- Model: footprint traced from the plan in the 1939 Official Guide Book (georeferenced on Buildings 1–3, ±9 m); END YEAR ESTIMATED (1947) for each hall; pylons and setbacks not modelled
- Sources: https://archive.org/details/offboo00gold, https://archive.org/details/treasureislandma00jamerich, https://www.loc.gov/item/ca3486/, https://en.wikipedia.org/wiki/Golden_Gate_International_Exposition

### Ford Building (GGIE 1939) (`ggie_ford`)

- Model years: construction 1937.6 → 1939.13, end 1947.6; anchor 37.824452, -122.373545; top 21.3 m; 93 triangles.
- Exposition: Golden Gate International Exposition, Feb 18 – Oct 29, 1939 and May 25 – Sep 29, 1940; F on the 1939 plan, beside the Court of Pacifica
- Walls: "great 70-foot-high walls of stucco, flecked with iridescent vermiculite" — windowless palaces in the "Pacifica" style (Official Guide 1939)
- Fate: taken over by the Navy in 1941; many palaces reused, a 1947 fire destroyed three and most of the rest were demolished afterwards (HABS CA-2785)
- Model: footprint traced from the plan in the 1939 Official Guide Book (georeferenced on Buildings 1–3, ±9 m); END YEAR ESTIMATED (1947) for each hall; pylons and setbacks not modelled
- Sources: https://archive.org/details/offboo00gold, https://archive.org/details/treasureislandma00jamerich, https://www.loc.gov/item/ca3486/, https://en.wikipedia.org/wiki/Golden_Gate_International_Exposition

### Tower of the Sun (GGIE 1939) (`ggie_tower_of_the_sun`)

- Model years: construction 1937.9 → 1939.13, end 1942; anchor 37.820374, -122.371490; top 122.1 m; 294 triangles.
- Architect: Arthur Brown Jr.; centrepiece of the Court of Honor
- Height: 400 ft (122 m), steel frame clothed in timber; topped by a 22-ft wrought-iron golden phoenix; 44-bell carillon (James & Weller 1941)
- Model: position from the 1939 plan (centre of the Court of Honor); octagonal stage heights estimated from photographs; DEMOLITION YEAR ESTIMATED (Navy era, early 1940s)
- Sources: https://archive.org/details/offboo00gold, https://archive.org/details/treasureislandma00jamerich, https://www.loc.gov/item/ca3486/, https://en.wikipedia.org/wiki/Golden_Gate_International_Exposition

### Court of the Seven Seas and Court of Pacifica (GGIE 1939) (`ggie_court_of_the_seven_seas`)

- Model years: construction 1937.6 → 1939.13, end 1941.5; anchor 37.822014, -122.372695; top 30.5 m; 448 triangles.
- Seven Seas: main north–south court, sixteen 60-ft pylons with galleon prows and the "Spirit of Adventure" figures (P. O. Tognelli)
- Pacifica: Ralph Stackpole's 80-ft statue of Pacifica before a fluttering metal "prayer curtain" about 100 ft high and 48 ft wide; Brutons' 144 × 57 ft "Peacemakers" mural (James & Weller 1941)
- Model: court axis and Pacifica position from the 1939 plan; pylon spacing and statue form estimated; removal year estimated
- Sources: https://archive.org/details/treasureislandma00jamerich, https://archive.org/details/offboo00gold

### Portals of the Pacific — Elephant Towers (GGIE 1939) (`ggie_elephant_towers`)

- Model years: construction 1937.6 → 1939.13, end 1947.6; anchor 37.819785, -122.372879; top 45 m; 108 triangles.
- Portals: west entrance to the Court of Honor (Ernest E. Weihe): "heavy masses of Malayan pyramids which contract sharply into towers supported by formalized elephants and climaxed by elephant heads and howdahs" (Official Guide 1939)
- Model: rampart footprints from the 1939 plan; tower heights ESTIMATED (LOW CONFIDENCE); elephant sculpture not modelled
- Sources: https://archive.org/details/offboo00gold

### El Presidio de San Francisco — palisade quadrangle (1776) (`el_presidio_1776`)

- Model years: construction 1776.55 → 1776.72, end 1781; anchor 37.797448, -122.459097; top 5.2 m; 248 triangles.
- History: founded Sep 17, 1776 (Moraga): wooden, rush-thatched chapel, storehouse and quarters; adobe from 1776–77 on; in 1792 three sides of adobe and stone and a palisade on the fourth, all thatched (Sal, Vancouver); rebuilt around a larger square with tile roofs and two gates in 1815–18 (Argüello); the company left for Sonoma in 1835, a few families and a small garrison stayed, and by Feb 1844 it was in ruins, its tiles and timber taken for the custom house (Bancroft; early_sf.md §4.1)
- Model: square of 92 varas (77 m) after Moraga's plan; hut sizes and positions SCHEMATIC (LOW CONFIDENCE)
- Sources: https://archive.org/details/historyofcalifor01banc, https://archive.org/details/beginningsofsanf02eldr, https://npshistory.com/publications/goga/brochures/presidio-arch-tour-2001.pdf, https://npgallery.nps.gov/AssetDetail/NRIS/66000232

### El Presidio de San Francisco — adobe quadrangle (1792) (`el_presidio_1792`)

- Model years: construction 1781 → 1792.5, end 1815.5; anchor 37.797448, -122.459097; top 6.6 m; 136 triangles.
- History: founded Sep 17, 1776 (Moraga): wooden, rush-thatched chapel, storehouse and quarters; adobe from 1776–77 on; in 1792 three sides of adobe and stone and a palisade on the fourth, all thatched (Sal, Vancouver); rebuilt around a larger square with tile roofs and two gates in 1815–18 (Argüello); the company left for Sonoma in 1835, a few families and a small garrison stayed, and by Feb 1844 it was in ruins, its tiles and timber taken for the custom house (Bancroft; early_sf.md §4.1)
- Model: square of 120 yards (Sal 1792), comandancia 37 × 6 varas and chapel 19 × 8 varas (Sal's key), wall height and thickness (Vancouver) per early_sf.md §4.1; positions of the ranges and the alignment of the square on the Main Post axis ESTIMATED
- Sources: https://archive.org/details/historyofcalifor01banc, https://archive.org/details/beginningsofsanf02eldr, https://npshistory.com/publications/goga/brochures/presidio-arch-tour-2001.pdf, https://npgallery.nps.gov/AssetDetail/NRIS/66000232

### El Presidio — south range with the chapel and Comandancia (c.1815) (`el_presidio_south_range`)

- Model years: construction 1815 → 1818.3, end 1862; anchor 37.797448, -122.459097; top 8.2 m; 58 triangles.
- History: founded Sep 17, 1776 (Moraga): wooden, rush-thatched chapel, storehouse and quarters; adobe from 1776–77 on; in 1792 three sides of adobe and stone and a palisade on the fourth, all thatched (Sal, Vancouver); rebuilt around a larger square with tile roofs and two gates in 1815–18 (Argüello); the company left for Sonoma in 1835, a few families and a small garrison stayed, and by Feb 1844 it was in ruins, its tiles and timber taken for the custom house (Bancroft; early_sf.md §4.1)
- Model: c.1815 enlarged square, side ~150 m ESTIMATED (sources: "rebuilt around a larger square", "some say doubled"); the south range stays to the 1860s as the US Army reused the adobes — its core survives in the Officers' Club (rendered by the city buildings)
- Sources: https://archive.org/details/historyofcalifor01banc, https://archive.org/details/beginningsofsanf02eldr, https://npshistory.com/publications/goga/brochures/presidio-arch-tour-2001.pdf, https://npgallery.nps.gov/AssetDetail/NRIS/66000232

### El Presidio — west range (c.1815) (`el_presidio_west_range`)

- Model years: construction 1815 → 1818.3, end 1857; anchor 37.797448, -122.459097; top 5.8 m; 16 triangles.
- History: founded Sep 17, 1776 (Moraga): wooden, rush-thatched chapel, storehouse and quarters; adobe from 1776–77 on; in 1792 three sides of adobe and stone and a palisade on the fourth, all thatched (Sal, Vancouver); rebuilt around a larger square with tile roofs and two gates in 1815–18 (Argüello); the company left for Sonoma in 1835, a few families and a small garrison stayed, and by Feb 1844 it was in ruins, its tiles and timber taken for the custom house (Bancroft; early_sf.md §4.1)
- Model: side ~150 m ESTIMATED; one of the "rows of one-story adobe buildings on two sides of a square" seen in 1852 (Townsend); end year ESTIMATED
- Sources: https://archive.org/details/historyofcalifor01banc, https://archive.org/details/beginningsofsanf02eldr, https://npshistory.com/publications/goga/brochures/presidio-arch-tour-2001.pdf, https://npgallery.nps.gov/AssetDetail/NRIS/66000232

### El Presidio — north and east ranges (c.1815) (`el_presidio_north_east_ranges`)

- Model years: construction 1815 → 1818.3, end 1844.15; anchor 37.797448, -122.459097; top 5.8 m; 42 triangles.
- History: founded Sep 17, 1776 (Moraga): wooden, rush-thatched chapel, storehouse and quarters; adobe from 1776–77 on; in 1792 three sides of adobe and stone and a palisade on the fourth, all thatched (Sal, Vancouver); rebuilt around a larger square with tile roofs and two gates in 1815–18 (Argüello); the company left for Sonoma in 1835, a few families and a small garrison stayed, and by Feb 1844 it was in ruins, its tiles and timber taken for the custom house (Bancroft; early_sf.md §4.1)
- Model: side ~150 m ESTIMATED; in ruins by Feb 1844, tiles and timber taken for the custom house (Bancroft iv.666–669)
- Sources: https://archive.org/details/historyofcalifor01banc, https://archive.org/details/beginningsofsanf02eldr, https://npshistory.com/publications/goga/brochures/presidio-arch-tour-2001.pdf, https://npgallery.nps.gov/AssetDetail/NRIS/66000232

### Punta del Cantil Blanco (cliff, cut down 1853–54) (`punta_del_cantil_blanco`)

- Model years: construction 1700 → 1700.01, end 1853.5; anchor 37.810600, -122.477092; top 22.8 m; 22 triangles.
- Cliff: "Punta del Cantil Blanco", a serpentine promontory with a high white cliff at the narrowest part of the Golden Gate (about 100 ft, Eldredge); workers blasted the 90-ft cliff down to 15 ft above sea level for Fort Point (1853–54, Wikipedia)
- Model: height documented (90 ft); outline of the promontory ESTIMATED (Fort Point site, running inland until today's ground reaches the old cliff-top level)
- Sources: https://en.wikipedia.org/wiki/Fort_Point_National_Historic_Site

### Castillo de San Joaquín (`castillo_de_san_joaquin`)

- Model years: construction 1793.6 → 1794.94, end 1853.5; anchor 37.810600, -122.477092; top 28.1 m; 296 triangles.
- Built: begun Aug 1793 by a gunner's mate, a master carpenter and about 60 Indian labourers; completed and blessed Dec 8, 1794; adobe with brick-lined embrasures, a barrack for the artillerymen in the middle, 8 guns mounted in 1794 (Bancroft i.700, Eldredge ii.720 via early_sf.md)
- Plan: horseshoe-shaped, about 100 × 120 ft (Bancroft) or 125 × 105 ft with a parapet ten feet thick and 14 embrasures (Eldredge); sallyport on the landward (south) side (NHL nomination)
- Fate: abandoned 1835, walls crumbling; guns spiked by Frémont's party in 1846; the cliff was cut away for Fort Point in 1853–54
- Model: plan size and parapet from the sources; parapet height and the barrack ESTIMATED
- Sources: https://en.wikipedia.org/wiki/Fort_Point_National_Historic_Site, https://archive.org/details/historyofcalifor01banc, https://archive.org/details/beginningsofsanf02eldr

### Mission Dolores — convento (padres' house), later the Mansion House (`mission_dolores_convento`)

- Model years: construction 1789.5 → 1791.5, end 1876.5; anchor 37.764371, -122.426598; top 6.1 m; 126 triangles.
- Building: one-storey adobe range with a front corridor attached to the north side of the church, fronting the road ("the church … joins the house of the missionaries", Choris 1816); tiled by 1795; after 1834 the Mansion House tavern and a wooden rectory; razed by 1876 for the brick church
- Model: position, size, bearing and years from data/tables/early_sf.csv (a reasoned reconstruction from Bancroft, Langsdorff, Roquefeuil and the SF Planning Mission Dolores context statement; LOW CONFIDENCE — Hendry & Bowman's survey not reached); render these rows of early_sf.csv only once
- Sources: https://archive.org/details/historyofcalifor01banc, https://sfplanning.org/sites/default/files/documents/preserv/mdna_hcs/mdna_hcs_draft.pdf

### Mission Dolores — quadrangle north range (1795, 180 ft) (`mission_dolores_quadrangle_north`)

- Model years: construction 1793.5 → 1795.5, end 1856.5; anchor 37.764589, -122.426846; top 6.1 m; 16 triangles.
- Building: "In 1795 another adobe building 180 feet long was erected" (Bancroft i.714) — the weaving and workshop court behind the padres' house (Langsdorff 1806)
- Model: position, size, bearing and years from data/tables/early_sf.csv (a reasoned reconstruction from Bancroft, Langsdorff, Roquefeuil and the SF Planning Mission Dolores context statement; LOW CONFIDENCE — Hendry & Bowman's survey not reached); render these rows of early_sf.csv only once
- Sources: https://archive.org/details/historyofcalifor01banc, https://sfplanning.org/sites/default/files/documents/preserv/mdna_hcs/mdna_hcs_draft.pdf

### Mission Dolores — quadrangle west range (1794 storehouse, 150 ft) (`mission_dolores_quadrangle_west`)

- Model years: construction 1792.5 → 1794.5, end 1856.5; anchor 37.764401, -122.427166; top 6.1 m; 16 triangles.
- Building: "In 1794 a new storehouse 150 feet long was built and roofed with tiles" (Bancroft i.714)
- Model: position, size, bearing and years from data/tables/early_sf.csv (a reasoned reconstruction from Bancroft, Langsdorff, Roquefeuil and the SF Planning Mission Dolores context statement; LOW CONFIDENCE — Hendry & Bowman's survey not reached); render these rows of early_sf.csv only once
- Sources: https://archive.org/details/historyofcalifor01banc, https://sfplanning.org/sites/default/files/documents/preserv/mdna_hcs/mdna_hcs_draft.pdf

### Mission Dolores — escolta (guard) houses (`mission_dolores_guardhouse`)

- Model years: construction 1795.5 → 1797.5, end 1846.5; anchor 37.764655, -122.426596; top 5.1 m; 16 triangles.
- Building: houses for the guard detachment in the line of church, padres' house and storehouses (Roquefeuil 1817)
- Model: position, size, bearing and years from data/tables/early_sf.csv (a reasoned reconstruction from Bancroft, Langsdorff, Roquefeuil and the SF Planning Mission Dolores context statement; LOW CONFIDENCE — Hendry & Bowman's survey not reached); render these rows of early_sf.csv only once
- Sources: https://archive.org/details/historyofcalifor01banc, https://sfplanning.org/sites/default/files/documents/preserv/mdna_hcs/mdna_hcs_draft.pdf

### Mission Dolores rancheria — adobe row 1 of 8 (`mission_dolores_rancheria_1`)

- Model years: construction 1791.5 → 1793.5, end 1858.5; anchor 37.763855, -122.426032; top 5.1 m; 16 triangles.
- Building: attached one-room adobe family houses with tile roofs in long parallel ranges: 19 houses in 1793, 20 more in 1794, "eight long rows" by 1806 (Langsdorff); across Dolores St from the church (Notre Dame Plaza archaeological site); the population fell after 1823 and empty rows decayed
- Model: position, size, bearing and years from data/tables/early_sf.csv (a reasoned reconstruction from Bancroft, Langsdorff, Roquefeuil and the SF Planning Mission Dolores context statement; LOW CONFIDENCE — Hendry & Bowman's survey not reached); render these rows of early_sf.csv only once
- Sources: https://archive.org/details/historyofcalifor01banc, https://sfplanning.org/sites/default/files/documents/preserv/mdna_hcs/mdna_hcs_draft.pdf

### Mission Dolores rancheria — adobe row 2 of 8 (`mission_dolores_rancheria_2`)

- Model years: construction 1792.5 → 1794.5, end 1858.5; anchor 37.763869, -122.425793; top 5.1 m; 16 triangles.
- Building: attached one-room adobe family houses with tile roofs in long parallel ranges: 19 houses in 1793, 20 more in 1794, "eight long rows" by 1806 (Langsdorff); across Dolores St from the church (Notre Dame Plaza archaeological site); the population fell after 1823 and empty rows decayed
- Model: position, size, bearing and years from data/tables/early_sf.csv (a reasoned reconstruction from Bancroft, Langsdorff, Roquefeuil and the SF Planning Mission Dolores context statement; LOW CONFIDENCE — Hendry & Bowman's survey not reached); render these rows of early_sf.csv only once
- Sources: https://archive.org/details/historyofcalifor01banc, https://sfplanning.org/sites/default/files/documents/preserv/mdna_hcs/mdna_hcs_draft.pdf

### Mission Dolores rancheria — adobe row 3 of 8 (`mission_dolores_rancheria_3`)

- Model years: construction 1794.5 → 1796.5, end 1835.5; anchor 37.763884, -122.425555; top 5.1 m; 16 triangles.
- Building: attached one-room adobe family houses with tile roofs in long parallel ranges: 19 houses in 1793, 20 more in 1794, "eight long rows" by 1806 (Langsdorff); across Dolores St from the church (Notre Dame Plaza archaeological site); the population fell after 1823 and empty rows decayed
- Model: position, size, bearing and years from data/tables/early_sf.csv (a reasoned reconstruction from Bancroft, Langsdorff, Roquefeuil and the SF Planning Mission Dolores context statement; LOW CONFIDENCE — Hendry & Bowman's survey not reached); render these rows of early_sf.csv only once
- Sources: https://archive.org/details/historyofcalifor01banc, https://sfplanning.org/sites/default/files/documents/preserv/mdna_hcs/mdna_hcs_draft.pdf

### Mission Dolores rancheria — adobe row 4 of 8 (`mission_dolores_rancheria_4`)

- Model years: construction 1796.5 → 1798.5, end 1835.5; anchor 37.763898, -122.425316; top 5.1 m; 16 triangles.
- Building: attached one-room adobe family houses with tile roofs in long parallel ranges: 19 houses in 1793, 20 more in 1794, "eight long rows" by 1806 (Langsdorff); across Dolores St from the church (Notre Dame Plaza archaeological site); the population fell after 1823 and empty rows decayed
- Model: position, size, bearing and years from data/tables/early_sf.csv (a reasoned reconstruction from Bancroft, Langsdorff, Roquefeuil and the SF Planning Mission Dolores context statement; LOW CONFIDENCE — Hendry & Bowman's survey not reached); render these rows of early_sf.csv only once
- Sources: https://archive.org/details/historyofcalifor01banc, https://sfplanning.org/sites/default/files/documents/preserv/mdna_hcs/mdna_hcs_draft.pdf

### Mission Dolores rancheria — adobe row 5 of 8 (`mission_dolores_rancheria_5`)

- Model years: construction 1798.5 → 1800.5, end 1826.5; anchor 37.763912, -122.425077; top 5.1 m; 16 triangles.
- Building: attached one-room adobe family houses with tile roofs in long parallel ranges: 19 houses in 1793, 20 more in 1794, "eight long rows" by 1806 (Langsdorff); across Dolores St from the church (Notre Dame Plaza archaeological site); the population fell after 1823 and empty rows decayed
- Model: position, size, bearing and years from data/tables/early_sf.csv (a reasoned reconstruction from Bancroft, Langsdorff, Roquefeuil and the SF Planning Mission Dolores context statement; LOW CONFIDENCE — Hendry & Bowman's survey not reached); render these rows of early_sf.csv only once
- Sources: https://archive.org/details/historyofcalifor01banc, https://sfplanning.org/sites/default/files/documents/preserv/mdna_hcs/mdna_hcs_draft.pdf

### Mission Dolores rancheria — adobe row 6 of 8 (`mission_dolores_rancheria_6`)

- Model years: construction 1800.5 → 1802.5, end 1826.5; anchor 37.763927, -122.424838; top 5.1 m; 16 triangles.
- Building: attached one-room adobe family houses with tile roofs in long parallel ranges: 19 houses in 1793, 20 more in 1794, "eight long rows" by 1806 (Langsdorff); across Dolores St from the church (Notre Dame Plaza archaeological site); the population fell after 1823 and empty rows decayed
- Model: position, size, bearing and years from data/tables/early_sf.csv (a reasoned reconstruction from Bancroft, Langsdorff, Roquefeuil and the SF Planning Mission Dolores context statement; LOW CONFIDENCE — Hendry & Bowman's survey not reached); render these rows of early_sf.csv only once
- Sources: https://archive.org/details/historyofcalifor01banc, https://sfplanning.org/sites/default/files/documents/preserv/mdna_hcs/mdna_hcs_draft.pdf

### Mission Dolores rancheria — adobe row 7 of 8 (`mission_dolores_rancheria_7`)

- Model years: construction 1802.5 → 1804.5, end 1826.5; anchor 37.763941, -122.424599; top 5.1 m; 16 triangles.
- Building: attached one-room adobe family houses with tile roofs in long parallel ranges: 19 houses in 1793, 20 more in 1794, "eight long rows" by 1806 (Langsdorff); across Dolores St from the church (Notre Dame Plaza archaeological site); the population fell after 1823 and empty rows decayed
- Model: position, size, bearing and years from data/tables/early_sf.csv (a reasoned reconstruction from Bancroft, Langsdorff, Roquefeuil and the SF Planning Mission Dolores context statement; LOW CONFIDENCE — Hendry & Bowman's survey not reached); render these rows of early_sf.csv only once
- Sources: https://archive.org/details/historyofcalifor01banc, https://sfplanning.org/sites/default/files/documents/preserv/mdna_hcs/mdna_hcs_draft.pdf

### Mission Dolores rancheria — adobe row 8 of 8 (`mission_dolores_rancheria_8`)

- Model years: construction 1804.5 → 1806.5, end 1826.5; anchor 37.763956, -122.424361; top 5.1 m; 16 triangles.
- Building: attached one-room adobe family houses with tile roofs in long parallel ranges: 19 houses in 1793, 20 more in 1794, "eight long rows" by 1806 (Langsdorff); across Dolores St from the church (Notre Dame Plaza archaeological site); the population fell after 1823 and empty rows decayed
- Model: position, size, bearing and years from data/tables/early_sf.csv (a reasoned reconstruction from Bancroft, Langsdorff, Roquefeuil and the SF Planning Mission Dolores context statement; LOW CONFIDENCE — Hendry & Bowman's survey not reached); render these rows of early_sf.csv only once
- Sources: https://archive.org/details/historyofcalifor01banc, https://sfplanning.org/sites/default/files/documents/preserv/mdna_hcs/mdna_hcs_draft.pdf

### Big Dipper roller coaster (Playland) (`playland_big_dipper`)

- Model years: construction 1921.6 → 1922.4, end 1955.5; anchor 37.774050, -122.510720; top 23.8 m; 530 triangles.
- Ride: wooden coaster designed by Arthur Looff (1922); torn down 1955 (Wikipedia)
- Model: position along La Playa and circuit size ESTIMATED (LOW CONFIDENCE — no historic aerial reached; the 1938 Ryker mosaic would settle it)
- Sources: https://en.wikipedia.org/wiki/Playland_(San_Francisco)

### Shoot-the-Chutes (Playland) (`playland_shoot_the_chutes`)

- Model years: construction 1921 → 1921.6, end 1950.5; anchor 37.774050, -122.510720; top 22 m; 32 triangles.
- Ride: boat slide that gave the amusement area its first name, "Chutes at the Beach" (1921); torn down 1950 (Wikipedia)
- Model: position and dimensions ESTIMATED (LOW CONFIDENCE)
- Sources: https://en.wikipedia.org/wiki/Playland_(San_Francisco)

### Fun House (Playland) (`playland_fun_house`)

- Model years: construction 1923.5 → 1924.5, end 1972.68; anchor 37.774050, -122.510720; top 16 m; 26 triangles.
- Attraction: Fun House with the "Laffing Sal" automaton at the entrance; Playland closed Labor Day 1972 and was torn down from Sep 4, 1972 (Wikipedia)
- Model: position near Balboa St and the Great Highway, size and opening year ESTIMATED (LOW CONFIDENCE)
- Sources: https://en.wikipedia.org/wiki/Playland_(San_Francisco)

### Looff carousel building (Playland) (`playland_carousel`)

- Model years: construction 1913.6 → 1914.4, end 1972.68; anchor 37.774050, -122.510720; top 15 m; 80 triangles.
- Carousel: Arthur Looff leased land around 1913 for a carousel and its house, the Looff Hippodrome; the Whitneys bought the merry-go-round in 1942 (Wikipedia)
- Model: position and size ESTIMATED (LOW CONFIDENCE)
- Sources: https://en.wikipedia.org/wiki/Playland_(San_Francisco)

### Playland midway concessions (`playland_midway`)

- Model years: construction 1921 → 1923, end 1972.68; anchor 37.774050, -122.510720; top 7.0 m; 60 triangles.
- Midway: in 1934 the midway had 14 rides, 25 concessions and four restaurants along the Great Highway (Wikipedia)
- Model: a schematic row of concession sheds (PROCEDURAL — positions not documented)
- Sources: https://en.wikipedia.org/wiki/Playland_(San_Francisco)

### Woodward's Gardens (`woodwards_gardens`)

- Model years: construction 1865.5 → 1866.33, end 1891.5; anchor 37.768292, -122.421096; top 17 m; 178 triangles.
- Gardens: amusement park, museum, art gallery, zoo, aquarium, conservatories and lakes of Robert B. Woodward on the two blocks between Mission, Valencia, Duboce (13th) and 15th Sts; opened May 1, 1866, closed 1891 (Wikipedia)
- Model: site from DataSF street centrelines; building types from the contemporary descriptions; ALL POSITIONS AND SIZES ESTIMATED (LOW CONFIDENCE)
- Sources: https://en.wikipedia.org/wiki/Woodward%27s_Gardens

### Mechanics' Pavilion (`mechanics_pavilion_1882`)

- Model years: construction 1881.6 → 1882.6, end 1906.3; anchor 37.778096, -122.417312; top 30 m; 90 triangles.
- Built: 1882, a vast wooden exhibition hall of the Mechanics' Institute filling the block of Larkin, Polk, Grove and Hayes Sts — San Francisco's first great indoor arena (~11,000 seats)
- Fate: emergency hospital and morgue on the morning of Apr 18, 1906; evacuated about noon and burned that afternoon (sfmuseum.org timeline, FoundSF); the Exposition Auditorium (Civic Auditorium) took the site in 1915
- Model: block from DataSF centrelines (≈125 × 82 m); wall height, arched roof and towers ESTIMATED (LOW CONFIDENCE)
- Sources: https://www.nesssoftware.com/www/sf/buildings.php?id=MechPav, https://en.wikipedia.org/wiki/1906_San_Francisco_earthquake

### Sutro Heights — mansion and parapet (`sutro_heights_mansion`)

- Model years: construction 1883 → 1885, end 1939.5; anchor 37.778600, -122.511700; top 19 m; 124 triangles.
- Estate: Adolph Sutro bought 22 acres above the Cliff House in 1881 and built a turreted mansion, carriage house, conservatory and gardens with statuary; gardens opened to the public by 1883; given to the city 1938; the WPA demolished the mansion in 1939 (Wikipedia)
- Model: mansion and parapet positions on the park plateau ESTIMATED (LOW CONFIDENCE); massing from period photographs (estimated)
- Sources: https://en.wikipedia.org/wiki/Sutro_Heights_Park
