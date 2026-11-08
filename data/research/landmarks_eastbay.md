# Landmark research — East Bay (`viewer/src/landmarks/eastbay.ts`)

Alameda and Contra Costa counties. Companion to `landmarks.md`, `landmarks_batch3.md`, `landmarks_batch4.md` and
`landmark_audit.md`. One row per model in `data/tables/landmarks_eastbay.csv` (`start_year` = completion / opening,
lat/lon = model anchor, `height_m` = model top).

## Method
- **Footprints**: OpenStreetMap outlines and 3D building parts via Overture 2026-10-21.0
  (`data/raw/overture/2026-10-21.0/region5_building*.parquet`; © OpenStreetMap contributors, ODbL). Each model is
  built in a frame aligned with the building (`b.frame(0, 0, 0, bearing)`: +y at `bearing`, +x at `bearing + 90°`),
  anchored on the OSM centroid; stadiums / theatres in the round are anchored on the field or orchestra centre.
  Outlines were simplified 0.3–1 m; where OSM has 3D parts (Oakland City Hall, Tribune Tower, Temple, Coliseum decks,
  Memorial Stadium press box, Christ the Light, USS Hornet island) each part keeps its own outline and height.
- **Placement check**: every model's top view (triangles dumped from the real `build()` with esbuild) was overlaid
  on the OSM outlines (scratch tooling `eb/audit/overlay.py`); `replaces` polygons were checked to cover today's
  footprint centroids. (A mistake found and fixed in the audit: `rotRect(cx, cy, …)` takes its centre in the
  north-up anchor frame — off-centre `replaces` in a rotated frame use `rotRing(rect(…), bearing)`.)
- **Heights**: Wikipedia infoboxes / articles, National Register nominations (Memorial Stadium), the Cal Performances
  tech sheet (Greek Theatre), the UC Library Handbook 1918–19 (Doe), or the OSM `height` tag, as named in each
  model's facts. Everything else (stage heights, roof pitches, colours) from the reference photos listed per item;
  estimates are named in each model's `Model:` fact.
- **Terrain**: hillside sites were checked against the terrain grids (`data/interim/grid_{detail,region}_elev.npy`
  sampled with the viewer's own lookup rules). Findings that drove the models:
  - *Memorial Stadium*: the 30 m mesh puts the field at ≈124 m (Wikipedia: 125 m) and the east rim near Stadium Rim
    Way at ≈140–143 m (NRHP: "about 470 feet"), so the bowl rises 19 m from field to rim; the west facade stands
    on ground ≈4–8 m lower (foundations reach −8 m).
  - *Greek Theatre*: the bowl rises ≈10 m from the orchestra to the grassy rim; seat rows sit ≈0.5–1 m above the
    (smoothed) mesh so they are not swallowed.
  - *Oakland Coliseum*: the field is 21 ft below sea level, but the terrain shader never draws land below +0.9 m
    (`coverZ`), so the field and the lower bowl are raised onto the mesh; upper decks keep their height above the
    outside concourse (≈ +6.5 m).
  - *Mount Diablo*: the 60 m region mesh rounds the 1,173 m summit to ≈1,152 m and the viewer's 240 m height lookup
    gives ≈1,127 m at the summit building, so the model is lifted by `1152.4 − elevationAt(anchor)`
    (constant `DIABLO_MESH_TOP`; re-check after rebuilding the region terrain).
  - *USS Hornet*: the waterline is pinned to sea level (`0.5 − elevationAt(anchor)`), the lookup gives +1.5 m at the pier.
  - *Claremont Hotel*: the site falls ≈12 m across the building's width; walls start 10 m below the anchor's ground.
- **Photos**: Wikimedia Commons, 960 px thumbnails with `_meta.jsonl` (page, licence) per folder under
  `data/raw/reference_photos/<folder>/` (not committed). The API was rate-limited (HTTP 429) all session, so file
  names came from the article / category HTML pages; authors were not captured — see each file page.

## Derivations worth knowing
- **California Memorial Stadium** — NRHP nomination (2006, John S. English for BAHA; NPGallery asset
  ffa8730b-60f5-430b-9898-bedc4539cfb5): "Elliptical in shape … about 760 feet by 570", major axis NW–SE; facade
  "well over 1,000 feet long … at maximum … about 67 feet" above grade; stands "a horizontal depth of some 150
  feet"; 28 vomitories half-way up; Memorial Arch at the NW end with a concrete scoreboard tablet ~50 ft wide rising
  30+ ft above the rim, a matching south scoreboard; 15 pairs of flagpoles; the west/north-west/south upper rows on
  a concrete frame (three 24-ft bays), the east and north-east seating on an earth bank with no facade. Matches the
  OSM outline (235 × 179 m, field opening 80 × 139 m, axis 136.6°). 1968 press box (demolished 2002) and the
  temporary 2002–10 press box are NOT modelled (no dimensions found). 2012: gold seats, navy end zones, press box
  from the OSM part (123 × 25 m), its height from the photos.
- **Oakland Coliseum** — the OSM parts "Field Level", "Plaza Level", "Upper Deck" (crescents), "Mount Davis" and the
  outfield "Bleachers" give the plan; home plate ≈ 60 ft (backstop) in front of the field-level front row, CF fence
  400 ft out at the Mount Davis front — both consistent with the OSM geometry. No published deck heights were found;
  a 1995 planning requirement (quoted on newballpark.org) that Mount Davis "not exceed [the existing stadium] in
  overall height" sets its top to the upper deck. **LOW CONFIDENCE: deck heights.**
- **Oakland Arena** — the 1996–97 rebuild kept "the original walls, roof and foundation" (Wikipedia), so one model
  covers 1966–today (interior change only). OSM: a circle Ø 130 m. The OSM height (14.5 m) is not used; the X-brace
  count (16) and the ≈29 m height are photo estimates.
- **Sather Tower** — 307 ft, deck 200 ft (Wikipedia); the 10.4 m square shaft and the 6.9 m octagonal spire are
  OSM parts. Stage heights between 61 m and 94 m from the 2008 photo.
- **Doe Library** — UC Library Handbook 1918–19 (Project Gutenberg #51874): "outside dimensions of 262 feet by 224
  feet … California granite with roof of red mission tile … steel frame"; reading room 210 × 53 ft; "In 1911 a
  little more than half the building was completed … completion in 1917". North front heights scaled from the 2018
  photograph using the 69 m facade width. The 1949–50 Doe Annex (Bancroft Library) is not modelled (generic
  extrusion stays); the underground Gardner Stacks (1994) footprint is replaced (nothing drawn).
- **Hearst Greek Theatre** — Cal Performances tech sheet: stage 127 × 28 ft, upstage 170 ft; colonnade 35 ft above
  the stage; stage 6′5″ above the pit. NRHP: 19 rows of concrete benches, 28 carved stone chairs.
- **Fox Oakland** — no published dimensions; all heights from the 2005 and 2018 photographs (street wing ≈16 m,
  dome ≈39 m). **LOW CONFIDENCE: heights.**
- **Mission San José** — which OSM outline is the church: the E–W building (50.4 × 18.5 m) whose west gable faces
  Mission Blvd, with the bell tower at its north-west corner (left of the facade in the 2011 photo); the N–S
  building 23 m south along the street is the surviving padres' wing (museum), as in the c. 1900 photograph.
  The 1869 wooden Gothic church (moved away 1982) is sized from that photograph only — **LOW CONFIDENCE**.
- **Necklace of Lights** — 126 lampposts, 3,400 bulbs; lit 1925, removed 1941, relit 1987 (Wikipedia). Posts are
  spaced evenly (≈39 m) along the TIGER 2024 Lake Merritt shoreline offset 4.5 m onto the shore path — positions are
  generated, not surveyed. Strings are drawn 0.28 m thick so they read at map scale.
- **Golden Gate Fields** — the one-mile oval is built from standard geometry (two 402 m straights, 128 m turns,
  i.e. 2·402 + 2π·128 ≈ 1,609 m) placed along the grandstand front; the infield tote board in OSM falls inside the
  modelled infield. **LOW CONFIDENCE: oval position (±20 m) and grandstand section.** Racing ended Jun 9, 2024; the
  structures are kept standing (no demolition date known).

## Not done (and why)
- **Port of Oakland container cranes** (1960s →): crane positions and per-crane dates were not available offline
  (cranes are not building footprints); a dated crane inventory (Port of Oakland / OSM `man_made=crane`) is needed.
- **Oakland Mole / Oakland Pier terminal** (1882–1958, demolished 1960s): position known (37.810, −122.326,
  Wikipedia) but no dimensions of the train shed / ferry house were found this session.
- **Alameda NAS hangars, Kaiser Richmond shipyard whirley crane, Hearst Mining Building, South Hall, Rotunda
  Building, Oakland Museum, Kaiser Center**: footprints exist in OSM but there was no time for photos / dates; the
  generic extrusions stay.
- **Memorial Stadium 1968 press box** (to 2002): no dimensions.

## Items
### Sather Tower (the Campanile) (`sather_tower`)

- Model years: construction 1913 → 1915, end standing; anchor 37.872060, -122.257832; 376 triangles; top ≈ 93.6 m.
- Construction: built 1914, completed 1915, opened to the public 1916 (construction start estimated)
- Height: 307 ft (94 m); belfry / observation deck at 200 ft (61 m)
- Architect: John Galen Howard (after St Mark’s Campanile, Venice)
- Carillon: 61 bells (12-bell chime 1917; 48 in 1979; 61 in 1983)
- Model: shaft 10.4 m square from OSM; stage heights between the deck (61 m) and the top (94 m) estimated from photos
- Sources: https://en.wikipedia.org/wiki/Sather_Tower, https://npgallery.nps.gov/AssetDetail/NRIS/64000062
- Photo: `data/raw/reference_photos/sather_tower/Campanile_Hi-Res_-_reduced_file_size.jpg` — [File:Campanile_Hi-Res_-_reduced_file_size.jpg](https://commons.wikimedia.org/wiki/File:Campanile_Hi-Res_-_reduced_file_size.jpg) — public domain

### Sather Gate (`sather_gate`)

- Model years: construction 1909.6 → 1910.4, end standing; anchor 37.870218, -122.259481; 344 triangles; top ≈ 8.7 m.
- Completed: 1910 (John Galen Howard; built by Giovanni Meneghetti)
- Panels: eight bas-reliefs by Earl Cummings (four men, four women; removed 1910, reinstalled 1977–79)
- Restored: Oct 2008 – Apr 2009 (bronze and steel work)
- Model: proportions scaled from the LoC photograph (pylon width assumed 1.8 m); construction months estimated
- Sources: https://en.wikipedia.org/wiki/Sather_Gate, https://npgallery.nps.gov/AssetDetail/NRIS/64000062
- Photo: `data/raw/reference_photos/sather_gate/Sather_Gate_at_University_of_California__Berkeley__California_LCCN2013633500__edited_.jpg` — [File:Sather_Gate_at_University_of_California,_Berkeley,_California_LCCN2013633500_(edited).jpg](https://commons.wikimedia.org/wiki/File:Sather_Gate_at_University_of_California,_Berkeley,_California_LCCN2013633500_(edited).jpg) — Public domain

### Hearst Greek Theatre (`hearst_greek_theatre`)

- Model years: construction 1903.05 → 1903.73, end standing; anchor 37.873650, -122.254326; 649 triangles; top ≈ 13.1 m.
- Opened: Sep 24, 1903 (first used for Theodore Roosevelt’s commencement address, May 16, 1903)
- Capacity: 8,500
- Design: John Galen Howard (with Julia Morgan), after the theatre at Epidaurus; William Randolph Hearst paid for it
- Stage: 127 × 28 ft; colonnade 35 ft above the stage; 19 rows of concrete benches; backstage added 1957 (Ernest Born)
- Model: bowl and stage outline from OSM; row heights follow the terrain; backstage height estimated
- Sources: https://en.wikipedia.org/wiki/Hearst_Greek_Theatre, https://calperformances.org/wp-content/uploads/venues/tech-specs/Hearst-Greek-Theatre-2324-updated.pdf, https://npgallery.nps.gov/AssetDetail/NRIS/64000062
- Photo: `data/raw/reference_photos/hearst_greek_theatre/Hearst_Greek_Theatre__Berkeley__CA_.JPG` — [File:Hearst_Greek_Theatre_(Berkeley,_CA).JPG](https://commons.wikimedia.org/wiki/File:Hearst_Greek_Theatre_(Berkeley,_CA).JPG) — CC-BY-SA-3.0,2.5,2.0,1.0
- Photo: `data/raw/reference_photos/hearst_greek_theatre/MooreGreekTheaterUCBerkeley.JPG` — [File:MooreGreekTheaterUCBerkeley.JPG](https://commons.wikimedia.org/wiki/File:MooreGreekTheaterUCBerkeley.JPG) — Public domain

### California Memorial Stadium (1923) (`memorial_stadium_berkeley_1923`)

- Model years: construction 1922.9 → 1923.9, end 2010.95; anchor 37.870995, -122.250743; 1761 triangles; top ≈ 28.5 m.
- Construction: site clearing Dec 1922, groundbreaking Jan 1923; opened Nov 24, 1923 (Big Game)
- Capacity: ≈75,000 (temporary bleachers to ≈85,000; record 83,000 in 1947)
- Design: John Galen Howard; Roman-coliseum west half on a concrete frame, east half on an earthen bank, built across the Hayward Fault in two halves
- Press box: a lofty press box (1968) stood on the west rim until 2002 (not modelled)
- Model: outline from OSM (235 × 179 m); rim ≈ +19 m above the field (Stadium Rim Way ≈470 ft, field ≈410 ft); row profile and arch rhythm estimated
- Sources: https://en.wikipedia.org/wiki/California_Memorial_Stadium, https://npgallery.nps.gov/GetAsset/ffa8730b-60f5-430b-9898-bedc4539cfb5
- Photo: `data/raw/reference_photos/memorial_stadium_berkeley/California_Memorial_Stadium_aerial_view.jpg` — [File:California_Memorial_Stadium_aerial_view.jpg](https://commons.wikimedia.org/wiki/File:California_Memorial_Stadium_aerial_view.jpg) — CC-BY-4.0
- Photo: `data/raw/reference_photos/memorial_stadium_berkeley/Cal__Stanford_football_game__Memorial_Stadium__1930.jpg` — [File:Cal,_Stanford_football_game,_Memorial_Stadium,_1930.jpg](https://commons.wikimedia.org/wiki/File:Cal,_Stanford_football_game,_Memorial_Stadium,_1930.jpg) — Public domain
- Photo: `data/raw/reference_photos/memorial_stadium_berkeley/CaliforniaMemorialStadium.JPG` — [File:CaliforniaMemorialStadium.JPG](https://commons.wikimedia.org/wiki/File:CaliforniaMemorialStadium.JPG) — CC-BY-SA-3.0

### California Memorial Stadium (`memorial_stadium_berkeley`)

- Model years: construction 2010.95 → 2012.67, end standing; anchor 37.870995, -122.250743; 1918 triangles; top ≈ 28.5 m.
- Renovation: June 2010 – Sep 1, 2012: west side demolished and rebuilt behind the 1923 outer wall (HNTB / STUDIOS), new press box and club levels, field lowered 4 ft, fault-rupture blocks in the end zones
- Opened: Nov 24, 1923; reopened Sep 1, 2012
- Capacity: ≈63,000
- Model: press box outline from OSM; its height (≈8 m above the rim, cantilevered over the upper rows) estimated from photos; gold seats and navy end zones as photographed in 2024
- Sources: https://en.wikipedia.org/wiki/California_Memorial_Stadium, https://npgallery.nps.gov/GetAsset/ffa8730b-60f5-430b-9898-bedc4539cfb5
- Photo: `data/raw/reference_photos/memorial_stadium_berkeley/California_Memorial_Stadium_aerial_view.jpg` — [File:California_Memorial_Stadium_aerial_view.jpg](https://commons.wikimedia.org/wiki/File:California_Memorial_Stadium_aerial_view.jpg) — CC-BY-4.0
- Photo: `data/raw/reference_photos/memorial_stadium_berkeley/Cal__Stanford_football_game__Memorial_Stadium__1930.jpg` — [File:Cal,_Stanford_football_game,_Memorial_Stadium,_1930.jpg](https://commons.wikimedia.org/wiki/File:Cal,_Stanford_football_game,_Memorial_Stadium,_1930.jpg) — Public domain
- Photo: `data/raw/reference_photos/memorial_stadium_berkeley/CaliforniaMemorialStadium.JPG` — [File:CaliforniaMemorialStadium.JPG](https://commons.wikimedia.org/wiki/File:CaliforniaMemorialStadium.JPG) — CC-BY-SA-3.0

### Doe Memorial Library (north half) (`doe_library_1911`)

- Model years: construction 1907.5 → 1911.45, end standing; anchor 37.872190, -122.259497; 318 triangles; top ≈ 21.3 m.
- Construction: 1907 – 1911 (north half; opened Jun 26, 1911); completed 1914 – 1917
- Size: 262 × 224 ft; reading room 210 × 53 ft for 500 readers
- Design: John Galen Howard, after Émile Bénard’s 1899 competition plan; California granite, red mission-tile roof, steel frame
- Model: plan from OSM; north-front heights scaled from the 2018 photograph (16 columns, roof ≈20.6 m); split line between the 1911 and 1917 halves estimated
- Sources: https://en.wikipedia.org/wiki/Doe_Memorial_Library, https://gutenberg.org/ebooks/51874, https://npgallery.nps.gov/AssetDetail/NRIS/64000062
- Photo: `data/raw/reference_photos/doe_library/Doe_Library__main_facade__July_2018.jpg` — [File:Doe_Library,_main_facade,_July_2018.jpg](https://commons.wikimedia.org/wiki/File:Doe_Library,_main_facade,_July_2018.jpg) — CC-BY-SA-4.0

### Doe Memorial Library (south half) (`doe_library_1917`)

- Model years: construction 1914.5 → 1917.6, end standing; anchor 37.872190, -122.259497; 80 triangles; top ≈ 20.5 m.
- Completion: 1914 – 1917, funded by a state bond issue
- Model: courts and roof layout estimated (the south half is hidden from most viewpoints)
- Sources: https://en.wikipedia.org/wiki/Doe_Memorial_Library, https://gutenberg.org/ebooks/51874
- Photo: `data/raw/reference_photos/doe_library/Doe_Library__main_facade__July_2018.jpg` — [File:Doe_Library,_main_facade,_July_2018.jpg](https://commons.wikimedia.org/wiki/File:Doe_Library,_main_facade,_July_2018.jpg) — CC-BY-SA-4.0

### Oakland City Hall (`oakland_city_hall`)

- Model years: construction 1910.6 → 1914.5, end standing; anchor 37.805309, -122.272552; 687 triangles; top ≈ 98 m.
- Construction: 1910 – 1914 (Palmer & Hornbostel, competition of 1910)
- Height: 320 ft (98 m) — the first high-rise city hall in the United States
- Tiers: 3-storey base, 10-storey office tower, 2-storey podium with the clock tower; white granite and terra cotta
- After 1989: closed by the Loma Prieta earthquake; base-isolated on rubber bearings and reopened 1995
- Model: plan and tier heights from the OSM 3D parts (13/16, 82, 90, 98 m); cornice, podium and cupola heights from the photo
- Sources: https://en.wikipedia.org/wiki/Oakland_City_Hall
- Photo: `data/raw/reference_photos/oakland_city_hall/Oakland_City_Hall.jpg` — [File:Oakland_City_Hall.jpg](https://commons.wikimedia.org/wiki/File:Oakland_City_Hall.jpg) — CC-BY-2.0
- Photo: `data/raw/reference_photos/oakland_city_hall/Oakland_City_Hall_1917.jpg` — [File:Oakland_City_Hall_1917.jpg](https://commons.wikimedia.org/wiki/File:Oakland_City_Hall_1917.jpg) — Public domain

### Fox Oakland Theatre (`fox_oakland_theatre`) — **LOW CONFIDENCE** (see Model)

- Model years: construction 1926.9 → 1928.82, end standing; anchor 37.808068, -122.270541; 556 triangles; top ≈ 39.5 m.
- Opened: Oct 27, 1928 as “The Oakland” (West Coast Theatres; Fox from Mar 1929); about two years in construction
- Seats: 3,200 originally; 2,800 today
- Design: Weeks and Day for Maury L. Diggs; Moorish / Indian-temple styled terra cotta with a tiled dome
- History: closed Sep 14, 1965; bought by the city 1996; restored ($75 M) and reopened Feb 5, 2009
- Model: footprint from OpenStreetMap (© OSM contributors, ODbL); wing, pavilion, dome and sign heights estimated from photos (no published dimensions); construction start estimated
- Sources: https://en.wikipedia.org/wiki/Fox_Oakland_Theatre
- Photo: `data/raw/reference_photos/fox_oakland_theatre/Fox_Oakland_Theatre.jpg` — [File:Fox_Oakland_Theatre.jpg](https://commons.wikimedia.org/wiki/File%3AFox_Oakland_Theatre.jpg) — Public domain
- Photo: `data/raw/reference_photos/fox_oakland_theatre/Fox_Theater_of_Oakland__Wide.jpg` — [File:Fox_Theater_of_Oakland,_Wide.jpg](https://commons.wikimedia.org/wiki/File%3AFox_Theater_of_Oakland%2C_Wide.jpg) — CC-BY-SA-4.0

### Paramount Theatre (`paramount_theatre_oakland`)

- Model years: construction 1930.4 → 1931.96, end standing; anchor 37.809855, -122.268596; 157 triangles; top ≈ 37.5 m.
- Opened: Dec 16, 1931 (premiere of The False Madonna); closed Jun 1932 – 1933
- Design: Timothy Pflueger, Art Deco; facade mosaic by Gerald Fitzgerald; 3,476 seats (3,040 today)
- Restored: bought by the Oakland Symphony 1972, restored and reopened 1973; National Historic Landmark 1977
- Height: ≈33 m (OSM)
- Model: footprint from OpenStreetMap (© OSM contributors, ODbL); pylon, sign and marquee proportions from photos; auditorium height and construction start estimated
- Sources: https://en.wikipedia.org/wiki/Paramount_Theatre_(Oakland,_California)
- Photo: `data/raw/reference_photos/paramount_theatre_oakland/Oakland_Paramount_Theatre_exterior__1975.jpg` — [File:Oakland_Paramount_Theatre_exterior,_1975.jpg](https://commons.wikimedia.org/wiki/File:Oakland_Paramount_Theatre_exterior,_1975.jpg) — public domain
- Photo: `data/raw/reference_photos/paramount_theatre_oakland/Paramount.jpg` — [File:Paramount.jpg](https://commons.wikimedia.org/wiki/File:Paramount.jpg) — CC-BY-2.0

### Tribune Tower base (Breuner Building, 1906) (`tribune_building_1906`)

- Model years: construction 1905.3 → 1906.3, end standing; anchor 37.803054, -122.270827; 57 triangles; top ≈ 24 m.
- Completed: 1906 (D. Franklin Oliver) as the Breuner furniture store; the Oakland Tribune moved here in 1918
- Height: six storeys
- Model: footprint from OpenStreetMap (© OSM contributors, ODbL); storey height estimated
- Sources: https://en.wikipedia.org/wiki/Tribune_Tower_(Oakland)
- Photo: `data/raw/reference_photos/tribune_tower_oakland/Oakland_tribune_tower_detail.jpg` — [File:Oakland_tribune_tower_detail.jpg](https://commons.wikimedia.org/wiki/File:Oakland_tribune_tower_detail.jpg) — CC-BY-SA-3.0

### Tribune Tower (`tribune_tower_oakland`)

- Model years: construction 1922.4 → 1923.99, end standing; anchor 37.803054, -122.270827; 156 triangles; top ≈ 93.0 m.
- Tower: 1923 (Edward T. Foulkes), added to the 1906 base; opened by Joseph R. Knowland Jan 1, 1924
- Height: 305 ft (93 m), 22 storeys; 86 ft flagpole; clock faces and TRIBUNE neon on all four sides
- Later: damaged 1989, empty until 1995, renovated; the Tribune returned 1999–2007
- Model: tower and annex outlines from the OSM 3D parts; gallery, clock and mansard heights scaled from the photo; construction start estimated
- Sources: https://en.wikipedia.org/wiki/Tribune_Tower_(Oakland)
- Photo: `data/raw/reference_photos/tribune_tower_oakland/Oakland_tribune_tower_detail.jpg` — [File:Oakland_tribune_tower_detail.jpg](https://commons.wikimedia.org/wiki/File:Oakland_tribune_tower_detail.jpg) — CC-BY-SA-3.0

### Oakland Arena (`oakland_arena`)

- Model years: construction 1964.29 → 1966.86, end standing; anchor 37.750279, -122.202932; 796 triangles; top ≈ 29.5 m.
- Opened: Nov 9, 1966 (Oakland–Alameda County Coliseum Arena); Golden State Warriors 1971–2019
- Renovated: 1996–97 (HNTB, $121 M): interior gutted and a new bowl built inside the original walls, roof and foundation; ≈19,600 seats; the Warriors played 1996–97 in San José
- Design: Skidmore, Owings & Merrill (Myron Goldsmith) — glass drum under a concrete roof ring, X-braced
- Model: outline from OSM (Ø 130 m); bay count and heights (≈29 m) estimated from photos
- Sources: https://en.wikipedia.org/wiki/Oakland_Arena, https://pcad.lib.washington.edu/building/7178
- Photo: `data/raw/reference_photos/oakland_arena/Oracle_Arena_exterior_1.JPG` — [File:Oracle_Arena_exterior_1.JPG](https://commons.wikimedia.org/wiki/File%3AOracle_Arena_exterior_1.JPG) — CC-BY-SA-3.0
- Photo: `data/raw/reference_photos/oakland_arena/Oracle_coliseum_and_stadium_and_parking_lot_from_building_12th_floor_across_the_street.jpg` — [File:Oracle_coliseum_and_stadium_and_parking_lot_from_building_12th_floor_across_the_street.jpg](https://commons.wikimedia.org/wiki/File%3AOracle_coliseum_and_stadium_and_parking_lot_from_building_12th_floor_across_the_street.jpg) — CC-BY-SA-3.0
- Photo: `data/raw/reference_photos/oakland_arena/Oakland_Alameda_County_Coliseum_and_Arena_model.jpg` — [File:Oakland–Alameda_County_Coliseum_and_Arena_model.jpg](https://commons.wikimedia.org/wiki/File:Oakland%E2%80%93Alameda_County_Coliseum_and_Arena_model.jpg) — Public domain

### Necklace of Lights, Lake Merritt (1925) (`lake_merritt_necklace_1925`) — **LOW CONFIDENCE** (see Model)

- Model years: construction 1925 → 1925.5, end 1941.95; anchor 37.804073, -122.256979; 5292 triangles; top ≈ 6.8 m.
- Lit: 1925 — 126 lampposts and 3,400 "pearly bulbs" strung round the lake
- Dark: removed in 1941 for the World War II blackout
- Model: posts spaced evenly on the TIGER shoreline (positions estimated); strings drawn thicker than real so they read at map scale; months estimated
- Sources: https://en.wikipedia.org/wiki/Lake_Merritt
- Photo: `data/raw/reference_photos/lake_merritt_necklace/Lakemerritlights02192006.JPG` — [File:Lakemerritlights02192006.JPG](https://commons.wikimedia.org/wiki/File:Lakemerritlights02192006.JPG) — CC-BY-SA-3.0-migrated

### Necklace of Lights, Lake Merritt (`lake_merritt_necklace`) — **LOW CONFIDENCE** (see Model)

- Model years: construction 1986.8 → 1987.3, end standing; anchor 37.804073, -122.256979; 5292 triangles; top ≈ 6.8 m.
- Relit: 1987, after a decade-long campaign by the Lake Merritt Breakfast Club (first lit 1925, dark 1941–87)
- Model: posts spaced evenly on the TIGER shoreline (positions estimated); strings drawn thicker than real
- Sources: https://en.wikipedia.org/wiki/Lake_Merritt
- Photo: `data/raw/reference_photos/lake_merritt_necklace/Lakemerritlights02192006.JPG` — [File:Lakemerritlights02192006.JPG](https://commons.wikimedia.org/wiki/File:Lakemerritlights02192006.JPG) — CC-BY-SA-3.0-migrated

### Oakland–Alameda County Coliseum (1966) (`oakland_coliseum_1966`) — **LOW CONFIDENCE** (see Model)

- Model years: construction 1964.29 → 1966.71, end 1995.85; anchor 37.751665, -122.200474; 1280 triangles; top ≈ 33.8 m.
- Construction: groundbreaking Apr 15, 1964; opened Sep 18, 1966 (Raiders 1966–81, A’s from 1968)
- Design: Skidmore, Owings & Merrill (Myron Goldsmith); field 21 ft below sea level inside an earth berm
- Outfield: open to the Oakland hills, with bleachers and scoreboards
- Model: deck outlines from the OSM 3D parts; deck heights estimated; field raised to the terrain surface (see eastbay.ts)
- Sources: https://en.wikipedia.org/wiki/Oakland_Coliseum, https://pcad.lib.washington.edu/building/7178
- Photo: `data/raw/reference_photos/oakland_coliseum/Oakland_Coliseum_from_above_2024.jpg` — [File:Oakland_Coliseum_from_above_2024.png](https://commons.wikimedia.org/wiki/File:Oakland_Coliseum_from_above_2024.png) — CC-BY-4.0
- Photo: `data/raw/reference_photos/oakland_coliseum/Oakland_Coliseum_Exterior_2017.jpg` — [File:Oakland_Coliseum_Exterior_2017.jpg](https://commons.wikimedia.org/wiki/File:Oakland_Coliseum_Exterior_2017.jpg) — CC-BY-SA-4.0
- Photo: `data/raw/reference_photos/oakland_arena/Oracle_Arena_exterior_1.JPG` — [File:Oracle_Arena_exterior_1.JPG](https://commons.wikimedia.org/wiki/File%3AOracle_Arena_exterior_1.JPG) — CC-BY-SA-3.0
- Photo: `data/raw/reference_photos/oakland_arena/Oracle_coliseum_and_stadium_and_parking_lot_from_building_12th_floor_across_the_street.jpg` — [File:Oracle_coliseum_and_stadium_and_parking_lot_from_building_12th_floor_across_the_street.jpg](https://commons.wikimedia.org/wiki/File%3AOracle_coliseum_and_stadium_and_parking_lot_from_building_12th_floor_across_the_street.jpg) — CC-BY-SA-3.0
- Photo: `data/raw/reference_photos/oakland_arena/Oakland_Alameda_County_Coliseum_and_Arena_model.jpg` — [File:Oakland–Alameda_County_Coliseum_and_Arena_model.jpg](https://commons.wikimedia.org/wiki/File:Oakland%E2%80%93Alameda_County_Coliseum_and_Arena_model.jpg) — Public domain

### Oakland Coliseum (`oakland_coliseum`) — **LOW CONFIDENCE** (see Model)

- Model years: construction 1995.85 → 1996.62, end standing; anchor 37.751665, -122.200474; 1370 triangles; top ≈ 34.3 m.
- Renovation: Nov 1995 – Aug 1996 (HNTB) for the Raiders’ return: “Mount Davis”, a 10,000+-seat, 90-suite outfield grandstand, closes the bowl
- Tenants: A’s until 2024, Raiders until 2019; cricket and soccer since 2025
- Fences: LF 330 ft · LC 388 · CF 400 · RC 388 · RF 330
- Model: Mount Davis outline from OSM; its height set to the existing upper deck (as specified in 1995); deck heights estimated
- Sources: https://en.wikipedia.org/wiki/Oakland_Coliseum, https://en.wikipedia.org/wiki/Mount_Davis_(Oakland)
- Photo: `data/raw/reference_photos/oakland_coliseum/Oakland_Coliseum_from_above_2024.jpg` — [File:Oakland_Coliseum_from_above_2024.png](https://commons.wikimedia.org/wiki/File:Oakland_Coliseum_from_above_2024.png) — CC-BY-4.0
- Photo: `data/raw/reference_photos/oakland_coliseum/Oakland_Coliseum_Exterior_2017.jpg` — [File:Oakland_Coliseum_Exterior_2017.jpg](https://commons.wikimedia.org/wiki/File:Oakland_Coliseum_Exterior_2017.jpg) — CC-BY-SA-4.0

### Oakland California Temple (`oakland_california_temple`)

- Model years: construction 1962.4 → 1964.88, end standing; anchor 37.807818, -122.199100; 296 triangles; top ≈ 52.2 m.
- Construction: groundbreaking May 26, 1962 (David O. McKay); dedicated Nov 17, 1964
- Height: 170 ft (52 m) central spire; five spires; Sierra white granite over reinforced concrete
- Design: Harold W. Burton — Mid-century Modern, Asian and Art Deco; terrace garden and reflecting pool
- Model: plan and spire footprint from OSM; stage and corner-spire heights estimated from photos
- Sources: https://en.wikipedia.org/wiki/Oakland_California_Temple
- Photo: `data/raw/reference_photos/oakland_temple/Oakland_Mormon_Temple.jpg` — [File:Oakland_Mormon_Temple.jpg](https://commons.wikimedia.org/wiki/File:Oakland_Mormon_Temple.jpg) — Public domain

### 16th Street Station (Southern Pacific) (`sp_16th_street_station`)

- Model years: construction 1910.6 → 1912.59, end standing; anchor 37.815470, -122.297166; 152 triangles; top ≈ 23.2 m.
- Opened: Aug 3, 1912 (Jarvis Hunt), replacing an 1870s wooden depot on the then shoreline
- Served: Southern Pacific mainline trains and the SP Red Trains’ interurban platforms; Amtrak until Aug 21, 1994
- Since: damaged in 1989, closed 1994; restored as an event venue
- Model: footprint from OpenStreetMap (© OSM contributors, ODbL); heights scaled from the 2007 photo; signal tower date assumed with the station
- Sources: https://en.wikipedia.org/wiki/Oakland_16th_Street_station
- Photo: `data/raw/reference_photos/sp_16th_street_station/Oaklandstation2007.JPG` — [File:Oaklandstation2007.JPG](https://commons.wikimedia.org/wiki/File:Oaklandstation2007.JPG) — CC-BY-SA-3.0-migrated
- Photo: `data/raw/reference_photos/sp_16th_street_station/Sixteenth_Street_station_1918_postcard.JPG` — [File:Sixteenth_Street_station_1918_postcard.JPG](https://commons.wikimedia.org/wiki/File:Sixteenth_Street_station_1918_postcard.JPG) — public domain

### El Embarcadero Pergola, Lake Merritt (`lake_merritt_pergola`) — **LOW CONFIDENCE** (see Model)

- Model years: construction 1912.6 → 1913.5, end standing; anchor 37.808460, -122.249804; 1176 triangles; top ≈ 8.2 m.
- Built: 1913, City Beautiful improvements of Lake Merritt (Lakeside Park); restored 2007 (Measure DD)
- Style: Mission Revival: a semicircle of columns carrying a timber trellis, with tiled pavilions
- Model: outline from OSM; column spacing, heights and roof colours estimated (no photo or drawing downloaded); construction months estimated
- Sources: https://en.wikipedia.org/wiki/Lake_Merritt
- Photo: none downloaded (Wikimedia rate limits)

### Mills Hall, Mills College (`mills_hall`)

- Model years: construction 1870 → 1871.6, end standing; anchor 37.779656, -122.182039; 194 triangles; top ≈ 23 m.
- Built: 1871 (S. C. Bugbee & Son) — Mills Seminary moved here from Benicia in 1871; Mills College from 1885
- Style: Second Empire, painted wood, mansard roofs; National Register of Historic Places
- Model: footprint from OpenStreetMap (© OSM contributors, ODbL); storey and mansard heights estimated from the photo; construction start estimated
- Sources: https://en.wikipedia.org/wiki/Mills_College
- Photo: `data/raw/reference_photos/mills_hall/Mills-Hall-Mills-College-Oakland.jpg` — [File:Mills-Hall-Mills-College-Oakland.jpg](https://commons.wikimedia.org/wiki/File:Mills-Hall-Mills-College-Oakland.jpg) — CC-BY-SA-4.0

### Mission San José — adobe church (1809) (`mission_san_jose_1809`)

- Model years: construction 1806.5 → 1809.31, end 1868.81; anchor 37.533894, -121.919663; 185 triangles; top ≈ 16.2 m.
- Mission: founded Jun 11, 1797 (Fermín Lasuén), the 14th California mission
- Church: first permanent adobe church dedicated Apr 22, 1809
- Destroyed: Oct 21, 1868 Hayward Fault earthquake shattered the walls and roof
- Model: same massing as the 1985 reconstruction (a near-perfect replica on the original site); construction start estimated
- Sources: https://en.wikipedia.org/wiki/Mission_San_Jos%C3%A9_(California)
- Photo: `data/raw/reference_photos/mission_san_jose/Mission_San_Jose_April_2011_001.jpg` — [File:Mission_San_Jose_April_2011_001.jpg](https://commons.wikimedia.org/wiki/File:Mission_San_Jose_April_2011_001.jpg) — CC-BY-SA-3.0
- Photo: `data/raw/reference_photos/mission_san_jose/San_Jose_de_Guadalupe_circa_1900_Keystone-Mast.jpg` — [File:San_Jose_de_Guadalupe_circa_1900_Keystone-Mast.jpg](https://commons.wikimedia.org/wiki/File:San_Jose_de_Guadalupe_circa_1900_Keystone-Mast.jpg) — Public domain

### St. Joseph’s Church, Mission San José (1869) (`mission_san_jose_1869`) — **LOW CONFIDENCE** (see Model)

- Model years: construction 1868.9 → 1869.8, end 1982.3; anchor 37.533894, -121.919663; 44 triangles; top ≈ 31 m.
- Built: after the 1868 earthquake: a wood-framed Gothic church over the original red-tiled floor
- Moved: 1982, to make way for the reconstruction of the adobe church
- Model: LOW CONFIDENCE — size and steeple height estimated from a c. 1900 stereo photograph; built and removal dates approximate
- Sources: https://en.wikipedia.org/wiki/Mission_San_Jos%C3%A9_(California)
- Photo: `data/raw/reference_photos/mission_san_jose/Mission_San_Jose_April_2011_001.jpg` — [File:Mission_San_Jose_April_2011_001.jpg](https://commons.wikimedia.org/wiki/File:Mission_San_Jose_April_2011_001.jpg) — CC-BY-SA-3.0
- Photo: `data/raw/reference_photos/mission_san_jose/San_Jose_de_Guadalupe_circa_1900_Keystone-Mast.jpg` — [File:San_Jose_de_Guadalupe_circa_1900_Keystone-Mast.jpg](https://commons.wikimedia.org/wiki/File:San_Jose_de_Guadalupe_circa_1900_Keystone-Mast.jpg) — Public domain

### Mission San José — reconstructed church (`mission_san_jose`)

- Model years: construction 1982.4 → 1985.5, end standing; anchor 37.533894, -121.919663; 185 triangles; top ≈ 16.2 m.
- Reconstruction: completed 1985 by the Committee for the Restoration of Mission San Jose and the Diocese of Oakland — a near-perfect replica with a concealed steel frame
- Interior: reredos, chandeliers and side altars after the 1830s inventories
- Model: footprint from OpenStreetMap (© OSM contributors, ODbL); wall, ridge and tower heights scaled from the 2011 photo
- Sources: https://en.wikipedia.org/wiki/Mission_San_Jos%C3%A9_(California)
- Photo: `data/raw/reference_photos/mission_san_jose/Mission_San_Jose_April_2011_001.jpg` — [File:Mission_San_Jose_April_2011_001.jpg](https://commons.wikimedia.org/wiki/File:Mission_San_Jose_April_2011_001.jpg) — CC-BY-SA-3.0
- Photo: `data/raw/reference_photos/mission_san_jose/San_Jose_de_Guadalupe_circa_1900_Keystone-Mast.jpg` — [File:San_Jose_de_Guadalupe_circa_1900_Keystone-Mast.jpg](https://commons.wikimedia.org/wiki/File:San_Jose_de_Guadalupe_circa_1900_Keystone-Mast.jpg) — Public domain

### Mission San José — padres’ quarters (museum) (`mission_san_jose_padres_wing`) — **LOW CONFIDENCE** (see Model)

- Model years: construction 1808.5 → 1810, end standing; anchor 37.533894, -121.919663; 166 triangles; top ≈ 7.1 m.
- Built: part of the mission quadrangle (c. 1810, LOW CONFIDENCE date); the only surviving original adobe, saved by the Native Sons of the Golden West (1915, 1950) as the museum
- Model: footprint from OpenStreetMap (© OSM contributors, ODbL); roof, corridor and heights estimated
- Sources: https://en.wikipedia.org/wiki/Mission_San_Jos%C3%A9_(California)
- Photo: `data/raw/reference_photos/mission_san_jose/Mission_San_Jose_April_2011_001.jpg` — [File:Mission_San_Jose_April_2011_001.jpg](https://commons.wikimedia.org/wiki/File:Mission_San_Jose_April_2011_001.jpg) — CC-BY-SA-3.0
- Photo: `data/raw/reference_photos/mission_san_jose/San_Jose_de_Guadalupe_circa_1900_Keystone-Mast.jpg` — [File:San_Jose_de_Guadalupe_circa_1900_Keystone-Mast.jpg](https://commons.wikimedia.org/wiki/File:San_Jose_de_Guadalupe_circa_1900_Keystone-Mast.jpg) — Public domain

### USS Hornet (CV-12) museum ship (`uss_hornet_museum`)

- Model years: construction 1998.77 → 1998.79, end standing; anchor 37.772720, -122.302920; 311 triangles; top ≈ 47.5 m.
- Ship: Essex-class carrier, laid down Aug 3, 1942, commissioned Nov 29, 1943; recovered the Apollo 11 and 12 crews (1969); decommissioned 1970
- Museum: opened Oct 17, 1998 on the southernmost pier of the former Naval Air Station Alameda (closed 1997)
- Size: 872 ft (266 m) overall, beam 93 ft at the waterline; angled flight deck since the SCB-27A/125 refits
- Model: flight deck and island outline from OSM; deck heights and mast estimated from the photo; shown from the museum opening
- Sources: https://en.wikipedia.org/wiki/USS_Hornet_(CV-12), https://en.wikipedia.org/wiki/USS_Hornet_Museum
- Photo: `data/raw/reference_photos/uss_hornet_alameda/USS_Hornet__Alameda__CA_.JPG` — [File:USS_Hornet_(Alameda,_CA).JPG](https://commons.wikimedia.org/wiki/File:USS_Hornet_(Alameda,_CA).JPG) — CC-BY-SA-3.0,2.5,2.0,1.0

### Mount Diablo Summit Building and beacon (`mount_diablo_summit_building`) — **LOW CONFIDENCE** (see Model)

- Model years: construction 1939.3 → 1942, end standing; anchor 37.881754, -121.914189; 152 triangles; top ≈ 13.8 m.
- Built: 1939 – 1942 by the Civilian Conservation Corps, of sandstone quarried on the mountain; museum and visitor centre
- Beacon: the "Eye of Diablo" (Standard Oil aviation beacon, 1928) on the tower; relit every Pearl Harbor Day since 1964
- Summit: 3,849 ft (1,173 m)
- Model: footprint from OpenStreetMap (© OSM contributors, ODbL); heights estimated (no measured drawing); placed on the terrain mesh’s rounded summit (≈1,152 m)
- Sources: https://en.wikipedia.org/wiki/Mount_Diablo
- Photo: `data/raw/reference_photos/mount_diablo_summit/Mount_Diablo_Summit.JPG` — [File:Mount_Diablo_Summit.JPG](https://commons.wikimedia.org/wiki/File:Mount_Diablo_Summit.JPG) — CC-BY-SA-3.0

### Golden Gate Fields (`golden_gate_fields`) — **LOW CONFIDENCE** (see Model)

- Model years: construction 1940 → 1941.08, end standing; anchor 37.884133, -122.313132; 886 triangles; top ≈ 19.5 m.
- Opened: Feb 1, 1941 (grandstand against Fleming Point, track on filled marsh); turf course Feb 22, 1972
- Facilities: one-mile main track, 9/10-mile turf course, grandstand ≈8,000 and clubhouse ≈5,200 seats
- Closed: final race card Jun 9, 2024, after 83 years
- Model: grandstand outline from OSM; seating section, roof and clubhouse heights, and the oval geometry (one mile: 402 m straights, 128 m turns) estimated
- Sources: https://en.wikipedia.org/wiki/Golden_Gate_Fields
- Photo: `data/raw/reference_photos/golden_gate_fields/Golden_Gate_Fields_infield.jpg` — [File:Golden_Gate_Fields_infield.jpg](https://commons.wikimedia.org/wiki/File:Golden_Gate_Fields_infield.jpg) — CC-BY-SA-3.0

### Claremont Hotel (`claremont_hotel`) — **LOW CONFIDENCE** (see Model)

- Model years: construction 1906 → 1915.3, end standing; anchor 37.859410, -122.242066; 296 triangles; top ≈ 54 m.
- Construction: begun 1906 after the Claremont Hotel Company bought the site (Nov 1905); halted by the 1906 earthquake, resumed 1910; opened 1915
- Design: Charles W. Dickey and Walter D. Reed; wood frame — the 160 ft (49 m) tower is among the tallest wooden structures
- Notes: the Key System "E" line ran to its doors until 1958; spared by the 1991 Oakland firestorm
- Model: outline from OSM; wings simplified to gabled blocks; eave (≈19 m) and roof heights estimated from photos
- Sources: https://en.wikipedia.org/wiki/Claremont_Hotel_%26_Spa
- Photo: `data/raw/reference_photos/claremont_hotel/Claremonthotel03192006.JPG` — [File:Claremonthotel03192006.JPG](https://commons.wikimedia.org/wiki/File:Claremonthotel03192006.JPG) — CC-BY-SA-3.0-migrated
- Photo: `data/raw/reference_photos/claremont_hotel/1915_Claremont_Hotel_I0025726A__cropped_.jpg` — [File:1915_Claremont_Hotel_I0025726A_(cropped).jpg](https://commons.wikimedia.org/wiki/File:1915_Claremont_Hotel_I0025726A_(cropped).jpg) — Public domain

### Cathedral of Christ the Light (`cathedral_christ_the_light`)

- Model years: construction 2005.39 → 2008.73, end standing; anchor 37.810532, -122.263122; 381 triangles; top ≈ 41.5 m.
- Construction: groundbreaking May 21, 2005; consecrated and dedicated Sep 25, 2008
- Design: Craig W. Hartman, Skidmore Owings & Merrill — a vesica piscis of glass and Douglas-fir louvres; Omega window with the image of Christ (from Chartres)
- Height: 41 m (OSM)
- Model: top lens and podium from OSM; the base lens size and the fin crown height estimated from the photo
- Sources: https://en.wikipedia.org/wiki/Cathedral_of_Christ_the_Light_(Oakland,_California)
- Photo: `data/raw/reference_photos/cathedral_christ_the_light/Oak_Cathdrl_1.jpg` — [File:Oak_Cathdrl_1.jpg](https://commons.wikimedia.org/wiki/File:Oak_Cathdrl_1.jpg) — CC-BY-SA-3.0

### Cathedral Building (`cathedral_building_oakland`)

- Model years: construction 1913.2 → 1914.6, end standing; anchor 37.806232, -122.270244; 98 triangles; top ≈ 42 m.
- Built: 1914 (Benjamin Geer McDougall), the Federal Realty Building — "the Wedding Cake"
- Height: 42 m, 12 floors (OSM)
- Model: footprint from OpenStreetMap (© OSM contributors, ODbL); crown, pinnacle and mansard proportions from the photo; construction start estimated
- Sources: https://en.wikipedia.org/wiki/Cathedral_Building
- Photo: `data/raw/reference_photos/cathedral_building_oakland/Federal_Realty_Building__Oakland__CA__2.JPG` — [File:Federal_Realty_Building_(Oakland,_CA)_2.JPG](https://commons.wikimedia.org/wiki/File:Federal_Realty_Building_(Oakland,_CA)_2.JPG) — CC-BY-SA-3.0,2.5,2.0,1.0

### Ford Assembly Building (Craneway) (`ford_richmond_assembly_plant`)

- Model years: construction 1930.2 → 1931.2, end standing; anchor 37.910580, -122.358387; 272 triangles; top ≈ 19.3 m.
- Built: 1930 – 31 (Albert Kahn) on Richmond’s inner harbour; ≈500,000 sq ft
- History: Ford assembly 1931–56 (Jeeps and tanks in WWII); Loma Prieta damage 1989; rehabilitated 2008; part of Rosie the Riveter/WWII Home Front NHP
- Model: footprint from OpenStreetMap (© OSM contributors, ODbL); wall, monitor and Craneway heights estimated from the photo (OSM height 17.3 m); construction months estimated
- Sources: https://en.wikipedia.org/wiki/Ford_Assembly_Building
- Photo: `data/raw/reference_photos/ford_richmond_plant/Ford_Motor_Company_Assembly_Plant__Richmond__CA_.JPG` — [File:Ford_Motor_Company_Assembly_Plant_(Richmond,_CA).JPG](https://commons.wikimedia.org/wiki/File:Ford_Motor_Company_Assembly_Plant_(Richmond,_CA).JPG) — CC-BY-SA-3.0,2.5,2.0,1.0
