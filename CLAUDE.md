# Bay Area Through Time — project brief

An interactive 3D web map of the San Francisco Bay Area where you can pan, zoom, tilt, and drag a year slider (1769 → today) to see what the region looked like in any given year: buildings, shoreline, marshes, orchards, freeways, bridges.

Visual inspiration: the "Latos Charts" YouTube channel (e.g. "BERLIN - 3D Timelapse"): extruded flat-shaded building blocks, low-poly trees, a year counter and population counter, serif era titles — but interactive in the browser.

**Owner's standing instructions (2026-11):**
- Landmarks (Golden Gate Bridge, Legion of Honor, Salesforce Tower/Park, Transamerica Pyramid, Painted Ladies, stadiums, parks, …) must be **actual reconstructions** from real dimensions and photos, not procedural stand-ins.
- Use real data and real reference imagery **as much as possible**; procedural generation **as little as possible**. When something must be generated, mark it `year_confidence = procedural` and prefer tracing a real historical map over inventing geometry.

## Core idea

Every feature is a geometry with a lifespan:

```
{ geometry, kind, height_m, start_year, end_year, year_confidence, source }
```

* `kind`: building | landmark | land | water | marsh | fill | orchard | forest | road | rail | freeway | bridge | wall …
* `end_year`: `9999` if it still exists.
* `year_confidence`: `exact` (from records) | `estimated` (imputed) | `procedural` (generated to match a historical map) | `reconstructed` (hand-modelled landmark from cited dimensions).
* `source`: short id pointing to an entry in `SOURCES.md`.

The viewer shows a feature iff `start_year <= year < end_year`.

## Repo layout

```
/viewer            web app (Vite + TS, deck.gl 9 + MapLibre 5)
/pipeline          python stages, one script per stage (see Makefile)
/data/raw          downloads (gitignored)
/data/interim      cleaned/joined intermediates + reports (gitignored)
/data/manual       hand-traced / hand-researched data (COMMITTED — precious)
/data/tables       small CSVs: population, events, eras, landmarks (committed)
/data/research     research notes (landmark dimensions, references)
/dist/tiles        future PMTiles (gitignored)
SOURCES.md         every data source: URL, license, attribution, use
CLAUDE.md          this file
```

## Running

```
make setup      # python venv + npm install
make sf         # download + build San Francisco data (~2 min after downloads)
make terrain    # elevation + land-cover tiles for the whole Bay Area (~20 min, ~80 MB, not committed)
make dev        # viewer at http://localhost:5173
make deploy     # build + publish viewer/dist (incl. terrain tiles) to gh-pages → bay.theojaffee.net
```

Pipeline stages (each idempotent, cached in data/raw or data/interim):
`download_sf` → `land` → `fire_1906` → `sf_join` → `sf_buildings` → `sf_predecessors` → `sf_export`, plus `download_overture` (buildings, parts, base land/land_use, roads), `trees` (street trees), `ground` (parks, woods, sand), `roads` (streets, region roads, historic routes), and the terrain chain `baylands_pdf` → `terrain_grid` → `terrain_tiles`.

## Landmarks (viewer/src/landmarks/)

Hand-modelled low-poly reconstructions built at runtime with a small mesh kit (`kit.ts`: prisms, lofts, domes, gables, hips, beams, parabolic cables, ribbons). Each landmark (`types.ts`) has `built: [construction start, completion]` (the model rises over that span), `end`, an anchor, cited `facts`/`sources`, and optional `replaces` polygons — the generic footprint extrusions under a *standing* landmark are hidden while landmarks are shown.
All dimensions come from `data/research/landmarks.md` (sources per item); anything estimated says so in the model's facts ("Model: …").

* `golden-gate-bridge.ts` · `downtown.ts` (Transamerica, Salesforce Tower, Transit Center + park) · `neighborhoods.ts` (Legion of Honor, Painted Ladies, 722 Steiner)
* `stadiums.ts`: Oracle Park, Chase Center, Kezar 1925/1990, Candlestick 1960/1971, Seals Stadium 1931/1946, Ewing Field (+1926 grandstand fire), Recreation Park, Cow Palace
* `city.ts`: Bay Bridge (west span; 1936 east span demolished in stages 2014–16; 2013 SAS + skyway), Ferry Building, City Hall 1915 + old City Hall (–1906), Coit Tower, Palace of Fine Arts 1915/1967, Sutro Tower, Alcatraz (cellhouse, lighthouses 1854/1909, water tower), Fort Point, Mission Dolores (adobe + basilica), Cliff House 1863/1896/1909, Sutro Baths, Embarcadero Freeway (1959–91), Golden Gate Park buildings (Conservatory, windmills, Temple of Music, de Young 1919/2005, Cal Academy 2008)

Landmarks stand on the terrain (`elevationAt(anchor)`); bridges keep z = 0 (sea level). Known model limits: LOW CONFIDENCE models (Kezar 1925, old City Hall, Recreation Park, 1936 east-span alignment, Embarcadero Freeway route) say so in their facts.

## Decisions log (deviations from the original brief, with reasons)

1. **No modern basemap.** MapLibre runs with an empty style (background = water colour). Modern streets/labels/shoreline would be anachronistic. Land is our own polygon (TIGER shoreline for now; time-varying in Phase 2). MapLibre still provides camera, controls, and later terrain.
2. **No tiles for San Francisco.** SF (~177k buildings) ships as one compact columnar binary (`BAYT` format, ~9 MB gzip) that loads once and stays on the GPU: no feature dropping at low zoom (pitfall 7 doesn't arise), and the slider never waits on tile loads. PMTiles returns at Phase 5 (9 counties, ~3M buildings) together with the low-zoom aggregate.
3. **Own `TimeExtension` instead of `DataFilterExtension`.** Same GPU technique (visibility computed in the vertex shader from a `[start,end]` attribute, slider only changes a uniform) but one attribute instead of two, and it also drives the grow-in/sink animation and the "scorched" tint for buildings ending (e.g. 1906). Works on polygons (`mode: 'polygon'`) and meshes (`'mesh-z'`, `'mesh'`, `'fade'`).
4. **Triangulation in a Web Worker.** The binary stores delta-coded integer coordinates + ring-end markers (byte-shuffled for gzip); the worker decodes and earcuts (~1–2 s) so the file stays small.
5. **Geometry precedence (real before generic):** OSM hand-modelled `building_part`s (via Overture) > DataSF 2016 footprints > Overture/OSM footprints for buildings newer than the 2016 snapshot. Hand-reconstructed landmark meshes replace all of those for named landmarks.
6. **Heights:** 2010 LiDAR median height from the DataSF footprints for buildings that existed in 2010; stories × 3.3 m + 1.5 m for newer ones; then OSM/Overture height; then 7 m.
7. **Missing SF years are imputed from neighbours** (median of nearest exact-year buildings within 150 m, respecting bounds), not ACS — ACS returns for Phase 5 (Census API now requires a key).
8. **Population counter:** San Francisco city/county until Phase 5, then 9-county total.
9. **Trees:** street trees are real (DataSF positions; planting year recorded or estimated from trunk diameter). Park woods use real OSM wood extents with procedural positions inside (no per-tree survey exists) — confidence `procedural`. Woods are dated by park year, Golden Gate Park's documented east→west reclamation, the 1886 Presidio planting, and Lands End's 1930s planting.
10. **Built data in git:** `viewer/public/data/sf-buildings.bin.gz` and friends are committed at milestones so a fresh clone runs with `npm install && npm run dev`; otherwise regenerate with `make sf`.

11. **Terrain = one mesh for land, water and land cover.** MapLibre terrain was not used: deck.gl's own `TerrainMeshLayer` (Web-Mercator tiles, 64×64 cells, region grid z13 ≈ 60 m from 3DEP overview 1, SF grid z14 ≈ 30 m) carries per-vertex *cover histories* — a natural c.1800 cover plus up to 4 dated changes (fill, diking, farms/orchards, city, 1906 burn, parks/woods). The year is a uniform, so the slider never reloads tiles; covers blend over 2.5 years (the burn is instant). Shoreline over time falls out of this: bay cells become fill/city at their researched year. Drawing: the vertex grid is 30–60 m, so covers are NOT interpolated as vertex colours (blurry squares) nor snapped to vertices (staircases); each tile keeps a small texture of its current cover colours (rebuilt on the CPU when the year moves) and the fragment shader snaps a cubic B-spline sample of it to the nearest real cover with a little noise — crisp, rounded, organic edges and coastlines. Hills are smooth-shaded from per-vertex normals.
12. **c.1800 cover, best source wins:** WorldCover-based rules < SFEI EcoAtlas poster (vectorised from the PDF, georeferenced by label control points + IoU refinement + local rubber-sheet) < SFEI historical-ecology GIS < Hidden Nature SF. SFEI c.1998 "fill" is bay by definition (Treasure Island is water until 1936).
13. **Trees and farms are procedural on real evidence:** trees stand on real WorldCover tree pixels (forest/oak/riparian/park covers, species by region and elevation); orchard rows and farmsteads are generated in dated farm/orchard cells. Trees are drawn ~2× real crown size so they read at map scale (Latos style). Confidence `procedural`.
14. **Pre-1906 city (Phase 3) is procedural massing on real lots:** SF parcel lines mostly date from the 19th-century subdivisions, so `sf_predecessors.py` stands era-typical buildings on today's lots wherever the researched extent snapshot says the block was built (massing per `sf_extent_README.md` rules: gold-rush 1–2 storey frame before 1853, replaced downtown by 2–5 storey brick in the 1850s; 3–6 storeys after 1890; 2–3 storey houses elsewhere), ending them in the fire or when today's building replaced them. Documented buildings (`notable_pre1906.csv`) take their lots. Sanborn tracing would replace this block by block.
15. **Roads are draped paths, not polygons:** DataSF centerlines (SF, dated by extent snapshot or first nearby building), Overture roads elsewhere, researched routes (cable car, streetcar, Key System, ferries, demolished freeways) with lifespans. **Freeways and ramps that still exist come from Overture's real geometry (`freeways.bin.gz`)** with heights from its level/bridge flags (approaches ≤ 5.5 %, junctions continuous, ramp ends meeting streets at grade); the researched route lines only date them. Elevated stretches get concrete deck slabs with parapets and bents sized to the real height; the Bay Bridge / Golden Gate decks belong to their landmark models. Cars and trams move on the GPU along straight legs of their roads with an era density curve (none before ~1903) — `procedural`.
16. **Labels** (`places.csv`) show the name in use that year, by zoom tier, with a collision filter; neighborhood names change with the era (e.g. Yerba Buena → San Francisco 1847, South of the Slot, Butchertown).
17. **UI:** no era title card, no layer toggles (landmarks and trees are always on); `?debug` shows the data-quality overlay and event jump; shift+drag rotates/tilts.
18. **Performance rules (2026-11 pass; keep them):** deck.gl's per-layer cost dominates frames, so
    * few layers: all landmarks are ONE merged mesh (`landmarks/merged-layer.ts`, time/grow in the shader, per-vertex picking colour); terrain decorations of all visible tiles are concatenated into one instanced `DecoLayer` per kind (`layers/deco-layer.ts`), street trees and viaduct columns use the same layer; region roads are split into an 8×8 grid and only squares near the view are drawn;
    * nothing rebuilds per animation frame: traffic moves in the vertex shader from a time uniform (`TrafficLayer`), the loop only calls `setNeedsRedraw()`; the terrain reads the year at draw time; labels are decluttered on the CPU in screen space only on moveend / zoom step / year (no GPU collision pass);
    * level of detail: trees use 4–10-triangle meshes below zoom 15 and are thinned below 14 (`treeLod`);
    * no hover picking (`pickAsync: false`), objects are picked on click; deck canvas capped at 2× device pixels, MapLibre at 1×; the high-performance GPU is requested, and a banner warns when the browser renders WebGL in software.
    * WebGPU was considered and rejected for now: deck.gl's WebGPU backend is experimental and lacks text, paths and our GLSL shader injections; the bottlenecks were CPU-side, not the graphics API.

19. **What stood before today's buildings (2026-11 pass):**
    * exempt / institutional buildings (hospitals, campuses, public housing, schools, piers) have no assessor year: `known_building_dates.csv` (1,076 researched rows); tall buildings without a usable year get height floors (≥35 m → ≥1920, ≥50 m → ≥1950; towers missing from the 2016 snapshot → ≥2014);
    * urban renewal and freeway clearances (`data/manual/redevelopment_areas.csv`, 19 areas): imputed buildings can't predate the clearance; the old fabric (Victorian rows, residential hotels, warehouses) ends there, and superblock parcels get rows of era-typical buildings along their street edges (procedural);
    * demolished post-1906 buildings (`notable_demolished.csv`: Geneva Towers, Fox Theatre, Winterland, SP depot, lost piers…), the town before the gold rush (`early_sf.csv`: Ohlone villages, the Mission compound and village, ranchos, Yerba Buena 1835–49; generated fabric starts in 1849), the 1915 and 1939 expositions and other lost landmarks (`landmarks/batch4.ts`, traced from the 1914 Sanborn map of the PPIE);
    * nothing stands before its ground: buildings, trees and roads on bay fill are moved to the year the ground appeared (terrain land-year grid); generated buildings follow era massing rules; 19th-century cemeteries (Laurel Hill, Calvary, Odd Fellows, Masonic) are open green until the graves were moved.
20. **Facade materials** (`sf_export.materials`): painted-wood Victorians, stucco Sunset/Marina (with clay-tile roofs), brick, terra cotta / granite downtown, bronze and glass towers, contemporary panels, adobe and tule for the early town; roofs (flat, tile, shingle) are drawn on the top faces only.

## Year cleaning (SF assessor roll)

* raw year = most common non-zero `year_property_built` among the assessor records of the footprint's map parcel (ties → earliest).
* **spike years** are detected automatically: a multiple of 5 before 1950 whose count is > 4× the median of nearby non-round years. On the 2025 roll this flags 1875, 1880, 1885, 1890, 1895, **1900** (14.6k buildings vs ~400/yr around it). Spike years are placeholders: imputed with an upper bound of the spike year.
* **burned**: raw year < 1906 inside the 1906 burned area (minus unburned islands) is impossible — imputed with a lower bound of 1906.5.
* **land_not_yet**: a building can't predate its land (`data/manual/land_not_before.geojson`; Phase 2 generalises this to all fill).
* imputation: median of up to 12 nearest good-year buildings within 150 m that satisfy the bounds; last resort draws from the empirical distribution (spikes) or a documented range. Imputed rows → `estimated`.
* sub-year jitter (deterministic hash) so a whole tract doesn't appear on the same frame.
* Report: `data/interim/reports/sf_years.png`, `sf_buildings_summary.json`.

## Data sources

See `SOURCES.md` (URLs, licences, attribution, use). Verify each before relying on it.

## Known pitfalls (read before building)

1. The 1906 earthquake and fire destroyed ~28,000 buildings in SF. Assessor years < 1906 inside the burned zone are wrong; outside it (much of the Mission west of the fire line, Haight, parts of the Western Addition) pre-1906 Victorians survive.
2. Assessor year values are messy: spikes at round years, zeros/nulls. Plot the histogram first; treat spikes as `estimated`.
3. Assessor data is per parcel (per unit for condos), not per building. Group by map parcel; multi-building parcels share one year.
4. Today's ground isn't yesterday's ground: Financial District over Yerba Buena Cove, the Marina (1915 Expo), Mission Bay, Treasure Island (1936–37), Foster City, SFO, Bay Farm Island, much of the East Bay waterfront. A building's `start_year` must never precede its land's.
5. Demolished things don't exist in modern data: Embarcadero Freeway (1959–1991), Central Freeway, Cypress Structure (1957–1989), Key System, Western Addition/SoMa redevelopment clearances, old Bay Bridge east span (to 2013), Playland, Sutro Baths, Candlestick Park, Seals Stadium, … — add manually with cited dates.
6. Santa Clara Valley orchards (~100,000 acres at the 1930s–40s peak) are a first-class layer.
7. Tile simplification drops features at low zoom — use an aggregated low-zoom representation when tiling (Phase 5).
8. Licenses: OSM is ODbL (attribution + share-alike on derived databases — our built building file mixes OSM parts, so it is offered under ODbL); DataSF datasets are PDDL; check each county's terms. Keep attribution visible in the viewer.

## Phased plan

Each phase ends with something runnable in the browser.

* **Phase 0 — Skeleton** ✅ viewer, time filter + grow animation, Latos-style UI.
* **Phase 1 — SF modern-data era** ✅ (first pass) pipeline + 177k buildings, confidence overlay, picking. Acceptance: 60 fps on a laptop (check on real GPU — CI/headless uses software GL), roughly matches known history.
* **Phase 2 — Time-varying land and water** ✅ (first pass): terrain + land-cover histories, SFEI c.1800 habitats, 96 dated fill/diking zones, coastline grows outward. Still to do: automatic check that no building predates its land beyond `land_not_before`.
* **Phase 3 — Pre-1906 SF and the fire** ✅ (first pass, procedural on real lots; burn + rebuild in the terrain). Next: trace street grid and built-up extent from Sanborn/Coast Survey/Rumsey maps for snapshot years; buildings from traced footprints where maps show them (Sanborn maps show individual footprints!), procedural only where unavoidable; `end_year = 1906` inside the burned zone; 1906 event.
* **Phase 4 — Landmarks, infrastructure, storytelling**: ~50 reconstructed landmarks, eras, events and population done early (owner request); routes (cable cars, streetcars, Key System, ferries, freeways) and traffic done; still to do: Transbay Terminal 1939 model, more landmark batches.
* **Phase 5 — Region** (prepared: terrain, land cover, trees, farms, roads and labels already cover Sonoma/Napa → Santa Cruz; buildings remain): San Mateo → Alameda → Santa Clara → Marin → Contra Costa → rest; Overture + county years + ACS imputation; PMTiles + low-zoom aggregate.
* **Phase 6 — Farmland and orchards** from historical topo maps and aerials.
* **Phase 7 — Polish and ship**: performance, mobile, shareable URLs (done early: `#year=…&c=lng,lat&z=…&p=…&b=…`), attribution panel, deploy.

## Working conventions

* Commit after each working step; keep the viewer runnable.
* Every pipeline stage is idempotent and cached; raw downloads are never modified in place.
* When a historical fact or date drives data, cite the source in `SOURCES.md` or next to the data.
* When unsure whether a year is real or a placeholder, mark it `estimated`.
* Prefer small, inspectable intermediates (GeoJSON/FlatGeobuf/Parquet) for QGIS.
* Screenshots: `cd viewer && node scripts/shots.cjs http://localhost:5173/ <outdir> <spec.json>` (headless Chromium; software GL is slow, ~30 s/frame with all of SF).
