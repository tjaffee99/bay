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
make dev        # viewer at http://localhost:5173
```

Pipeline stages (each idempotent, cached in data/raw or data/interim):
`download_sf` → `land` → `fire_1906` → `sf_join` → `sf_buildings` → `sf_export`, plus `download_overture`, `trees`.

## Decisions log (deviations from the original brief, with reasons)

1. **No modern basemap.** MapLibre runs with an empty style (background = water colour). Modern streets/labels/shoreline would be anachronistic. Land is our own polygon (TIGER shoreline for now; time-varying in Phase 2). MapLibre still provides camera, controls, and later terrain.
2. **No tiles for San Francisco.** SF (~177k buildings) ships as one compact columnar binary (`BAYT` format, ~9 MB gzip) that loads once and stays on the GPU: no feature dropping at low zoom (pitfall 7 doesn't arise), and the slider never waits on tile loads. PMTiles returns at Phase 5 (9 counties, ~3M buildings) together with the low-zoom aggregate.
3. **Own `TimeExtension` instead of `DataFilterExtension`.** Same GPU technique (visibility computed in the vertex shader from a `[start,end]` attribute, slider only changes a uniform) but one attribute instead of two, and it also drives the grow-in/sink animation and the "scorched" tint for buildings ending (e.g. 1906). Works on polygons (`mode: 'polygon'`) and meshes (`'mesh-z'`, `'mesh'`, `'fade'`).
4. **Triangulation in a Web Worker.** The binary stores delta-coded integer coordinates + ring-end markers (byte-shuffled for gzip); the worker decodes and earcuts (~1–2 s) so the file stays small.
5. **Geometry precedence (real before generic):** OSM hand-modelled `building_part`s (via Overture) > DataSF 2016 footprints > Overture/OSM footprints for buildings newer than the 2016 snapshot. Hand-reconstructed landmark meshes replace all of those for named landmarks.
6. **Heights:** 2010 LiDAR median height from the DataSF footprints for buildings that existed in 2010; stories × 3.3 m + 1.5 m for newer ones; then OSM/Overture height; then 7 m.
7. **Missing SF years are imputed from neighbours** (median of nearest exact-year buildings within 150 m, respecting bounds), not ACS — ACS returns for Phase 5 (Census API now requires a key).
8. **Population counter:** San Francisco city/county until Phase 5, then 9-county total.
9. **Built data in git:** `viewer/public/data/sf-buildings.bin.gz` and friends are committed at milestones so a fresh clone runs with `npm install && npm run dev`; otherwise regenerate with `make sf`.

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
* **Phase 2 — Time-varying land and water**: historical bay + marsh (SFEI), fill polygons with emplacement years (USGS), coastline grows outward; validation that no building predates its land.
* **Phase 3 — Pre-1906 SF and the fire**: trace street grid and built-up extent from Sanborn/Coast Survey/Rumsey maps for snapshot years; buildings from traced footprints where maps show them (Sanborn maps show individual footprints!), procedural only where unavoidable; `end_year = 1906` inside the burned zone; 1906 event.
* **Phase 4 — Landmarks, infrastructure, storytelling**: reconstructed landmarks (in progress early per owner request), freeways/rail with lifespans, eras, events, population.
* **Phase 5 — Region**: San Mateo → Alameda → Santa Clara → Marin → Contra Costa → rest; Overture + county years + ACS imputation; PMTiles + low-zoom aggregate.
* **Phase 6 — Farmland and orchards** from historical topo maps and aerials.
* **Phase 7 — Polish and ship**: performance, mobile, shareable URLs (done early: `#year=…&c=lng,lat&z=…&p=…&b=…`), attribution panel, deploy.

## Working conventions

* Commit after each working step; keep the viewer runnable.
* Every pipeline stage is idempotent and cached; raw downloads are never modified in place.
* When a historical fact or date drives data, cite the source in `SOURCES.md` or next to the data.
* When unsure whether a year is real or a placeholder, mark it `estimated`.
* Prefer small, inspectable intermediates (GeoJSON/FlatGeobuf/Parquet) for QGIS.
* Screenshots: `cd viewer && node scripts/shots.cjs http://localhost:5173/ <outdir> <spec.json>` (headless Chromium; software GL is slow, ~30 s/frame with all of SF).
