# Brief: "New York City Through Time" — port of the Bay Area map

Hand this file to a fresh Claude Code session opened on a NEW repository. It was written at
the end of the Bay Area project (`tjaffee99/bay`, live at bay.theojaffee.net) by the session
that built it.

## The ask

The owner's words: "the same exact map through time but with New York City." An interactive
3D web map with a year slider: pan, zoom, tilt, drag the year, and see what stood then —
buildings, shoreline and landfill, streets, railways and elevated lines, bridges, parks,
landmarks — with a year counter and a population counter. Same look, same viewer, same rules.

**The owner's standing rules (they carry over unchanged):**
- Landmarks are real reconstructions from cited dimensions, not procedural stand-ins.
- Real, cited data as much as possible; procedural generation as little as possible. Anything
  generated is marked `procedural`, anything imputed `estimated`. Prefer tracing a real
  historical map over inventing geometry.
- The owner is cost-sensitive. Deploy rather than verify at length; say plainly what was not checked.

## How to start

1. New repo = a copy of `tjaffee99/bay` (not a fork you keep in sync, not a shared library —
   extract a shared engine only if a third city ever comes). Keep the viewer and the generic
   pipeline; delete the Bay data and Bay-only stages (lists below).
2. Write a NEW, short `CLAUDE.md`. Do not inherit the Bay one (50 KB of Bay decisions). Carry
   over only: the core idea (every feature is a geometry with `start_year` / `end_year` /
   `year_confidence` / `source`; shown iff `start <= year < end`), the working conventions,
   and the generic rules listed under "Lessons" here. Start a fresh decisions log.
3. Change the deploy target: `viewer/public/CNAME` and the `deploy` target of the `Makefile`
   (it force-pushes `viewer/dist` to `gh-pages`).
4. Scope: **Manhattan first**, then the other boroughs, then (maybe) Hudson County / the
   harbor. Pick the start year deliberately (1609 or 1624 instead of the Bay's 1769).
5. First milestone: Manhattan's present-day buildings with construction years and measured
   heights on a terrain with today's shoreline, slider working, deployed. Then shoreline /
   landfill over time, then "what stood before", then landmarks, then the boroughs.

## What carries over (keep)

**Viewer** (`viewer/`, Vite + TypeScript, deck.gl 9 + MapLibre 5 with an empty style):
- `src/main.ts` — map, slider, URL hash (`#year=…&c=lng,lat&z=…&p=…&b=…`), population counter.
- `src/layers/buildings.ts`, `region-buildings.ts` — time-aware building layer (own
  `TimeExtension`: visibility, construction frame and demolition computed in the vertex
  shader from a `[start,end]` attribute; the slider only changes a uniform) and the z13 tile loader.
- `src/layers/terrain.ts` — one mesh for land, water and land cover; each vertex carries a
  natural cover plus up to four dated changes, so shoreline, fill, farms and city ground
  change with the year without reloading tiles.
- `src/layers/deco-layer.ts`, `decoration-meshes.ts` — instanced trees and small buildings.
- `src/layers/roads.ts`, `transit.ts`, `labels.ts`, `ground-detail.ts`, `drape-extension.ts`,
  `extent.ts`, `elevation.ts`.
- `src/landmarks/` — `kit.ts` (prisms, lofts, domes, gables, cables …), `types.ts`,
  `merged-layer.ts`, `index.ts`. Delete the Bay model files; keep one or two as examples
  (a bridge from `city.ts` or `northbay.ts`, a church, a tower).

**Pipeline** (`pipeline/`, Python; one script per stage, each idempotent and cached):
- Formats and helpers: `common.py`, `export_columnar.py`, `building_binary.py` (the `BAYT`
  columnar binary), `audit_region_years.py` (`read_bayt`), `extent.py`.
- `download_overture.py` (buildings, parts, land use, roads, rail by bounding box).
- `terrain_grid.py`, `terrain_tiles.py`, `covers.py` — elevation (USGS 3DEP), land cover
  (ESA WorldCover), cover histories, tiles.
- `lidar_parts.py` — measured heights and stepped massing from USGS 3DEP point clouds.
- `region_buildings.py`, `region_predecessors.py`, and from `sf_predecessors.py` the generic
  parts: `apply_sanborn`, `resolve_overlaps`, `consistency`.
- `sanborn_trace*.py` (fire-insurance map tracing), `data/manual/region_extents/tools/`
  (built-up extents from old topographic sheets), `roads.py`, `transit.py`, `cities.py`,
  `ground_detail.py`, `airports.py`, `ohm_import.py` (OpenHistoricalMap).

## What does not carry over (delete or rewrite)

- All of `data/manual/`, `data/tables/`, `data/research/`, `SOURCES.md` content, built files
  under `viewer/public/data` and `viewer/public/tiles`.
- Bay-only stages: `download_sf.py`, `land.py`, `fire_1906.py`, `sf_join.py`,
  `sf_buildings.py`, `sf_export.py`, `trees.py`, `ground.py`, `baylands_pdf.py`,
  `download_region.py` (county assessor sources), `fires.py`, `landscape*.py`,
  `topo_farmsteads.py`, `region_trees.py`.
- Hard-coded Bay geography inside the kept files: bounding boxes and county lists
  (`terrain_grid.GRIDS`, `download_overture.REGION_BBOX`, `roads.REGION_BBOX_ROADS`,
  `region_buildings.COUNTIES`, `cities.COUNTIES`, the viewer's `REGION` box and tile extents),
  the fog-belt forest rule and the dune / SF rules in `terrain_tiles.py`, the 1906 date in
  `apply_sanborn`, landmark-bridge names in `roads.py`.

## New York sources to check first

These are from memory — **verify each (URL, licence, fields) before relying on it.**
- **Buildings:** the city's Building Footprints dataset (construction year, roof height,
  ground elevation per footprint) and MapPLUTO (year built, floors, use per tax lot). Expect
  the same placeholder years as the Bay rolls (round years, 1900 / 1910 / 1920 heaps).
- **Heights:** the city's 2017 LiDAR and USGS 3DEP.
- **Before today's buildings:** the New York Public Library's Map Warper (thousands of
  georeferenced fire-insurance and real-estate atlases: Perris, Bromley, Robinson, Sanborn);
  the city's 1924 and 1951 aerial mosaics; OpenHistoricalMap; Department of Buildings
  demolition records; the Landmarks Preservation Commission's designation data.
- **Natural landscape and shoreline:** the Welikia / Mannahatta project (the 1609 ecology of
  the city — check what is downloadable), historical shoreline and landfill maps (Lower
  Manhattan, Battery Park City, the East River and Brooklyn waterfronts), USGS historical topo.
- **Streets and transit:** the city's street centreline data, the 1811 grid's opening dates
  where documented, MTA GTFS plus station opening dates, the demolished elevated lines,
  streetcars, ferries, bridges and tunnels with their dates.
- **Population:** decennial census by borough / county back to 1790, wards before 1898.

## Lessons that cost the most here

**Data**
- Assessor years are messy: detect placeholder ("spike") years, treat them as bounds, impute
  from neighbours, spread heaps instead of stacking them, mark the result `estimated`.
- Evidence order for a year: researched row > historic-resource survey > assessor > permit >
  neighbours. Tall or large buildings must never be dated from small neighbours.
- Nothing stands before its ground: date made land first, then check every building, tree
  and road against it.
- Demolished things are not in modern data. Manhattan has been rebuilt several times, so plan
  the "what stood before" work early and base it on the georeferenced atlases, not on generation.
- No two buildings on one spot at once (documented > traced > generated); no feature with
  start >= end; no year carrying thousands of buildings more than its neighbours. Check these
  on the built files after every rebuild.

**Viewer performance**
- Few layers (per-layer cost dominates): all landmarks are one merged mesh; decorations are
  one instanced layer per kind. Nothing is rebuilt per animation frame; time lives in shaders.
- Keep tiled layers alive across zoom (hide, don't remove) or everything blinks.

**Hosting and machine limits**
- GitHub Pages cancels a deployment whose file sync runs over ten minutes: a 483 MB site
  failed three times, 365 MB went through. Keep the site well under ~400 MB, or host the
  tiles elsewhere from the start. After `make deploy`, confirm the live site by comparing a
  file's checksum — a pushed deploy is not a published one.
- Tree records were four fifths of the terrain tiles. Ship a tree-cover mask and generate
  forest trees in the browser instead of storing every tree (not done in the Bay repo).
- The build machine has 16 GB. The terrain stage peaks near 10.6 GB and the buildings stage
  near 9 GB: run heavy stages one at a time, and process big arrays in chunks.
- Headless screenshots do not work there (software rendering times out). Verify with
  numeric checks and a headless console-error check, and tell the owner what to eyeball.

**Working with parallel agents**
- Give each agent one bounded part, a tool-call budget, and exclusive ownership of named
  files; only the lead runs heavy stages and edits shared pipeline code; agents hand back
  exact specs or patches for anything outside their files.
- Agents' code that was tested on subsets broke in the full run once (a coordinate-system
  mismatch). Smoke-test each stage with the new data before the long rebuild.
- Landmarks: take anchor, orientation and plan from the real footprint, heights from cited
  sources, and check the model numerically against the footprint and LiDAR.
