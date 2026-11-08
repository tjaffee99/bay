# Sources

Every dataset used, with licence, attribution, and what it is used for. Historical
facts that drive data (event years, demolition dates, dimensions) are cited next to
the data they drive (`data/tables/*.csv` `source_url` columns, `data/manual/*`,
`data/research/landmarks.md`).

## Licence summary of built outputs

| Output | Built from | Licence |
|---|---|---|
| `viewer/public/data/sf-buildings.bin.gz` | DataSF (PDDL) + OpenStreetMap via Overture (ODbL) | **ODbL 1.0** (derived database incl. OSM) — © OpenStreetMap contributors, Overture Maps Foundation; DataSF |
| `viewer/public/data/sf-land.json` | US Census TIGER/Line | public domain |
| `viewer/public/data/sf-trees.bin.gz` | DataSF Street Tree List | PDDL |
| `viewer/public/data/sf-ground.json` | RPD Parks (PDDL) + OSM via Overture (ODbL) + `data/tables/parks.csv` | **ODbL 1.0** |
| `viewer/public/data/sf-woods.bin.gz` | OSM wood extents via Overture (ODbL); positions procedural | **ODbL 1.0** |
| `viewer/public/data/fire-1906.json` | hand-researched boundary (`data/manual/`) + DataSF streets | see `data/manual/fire_1906_README.md` |
| `viewer/public/tiles/terrain/**`, `elevation-*.bin.gz` | USGS 3DEP (public domain), ESA WorldCover 2021 (**CC BY 4.0**), HISDAC-US (CC0), SFEI baylands / historical ecology (cite SFEI; GIS compilation GPL v3), hand-researched fill / extents / land-cover tables | **CC BY 4.0** — "contains modified ESA WorldCover 2021 data; SFEI-ASC historical ecology" |
| `viewer/public/data/roads-sf.bin.gz` | DataSF street centerlines (PDDL), dated from `data/manual/sf_extent_*.csv` and building years | PDDL |
| `viewer/public/data/roads-region.bin.gz` | OpenStreetMap via Overture transportation theme (ODbL) | **ODbL 1.0** |
| `viewer/public/data/routes.bin.gz` | `data/manual/routes.csv` (researched historic routes; geometry along DataSF centerlines) | as `data/manual/` (sources per row) |

## Datasets

### `datasf_footprints_2016` — SF Building Footprints
- URL: https://data.sfgov.org/d/ynuv-fyni (API `https://data.sf.gov/resource/ynuv-fyni`)
- Licence: Open Data Commons PDDL 1.0 (per dataset metadata), publisher City and County of San Francisco
- Fields used: `mblr` (SF + block/lot), `hgt_median_m` (2010 LiDAR median height above ground), `hgt_maxcm`, `gnd_min_m` (ground elevation), geometry
- Use: building footprints and heights for SF (172,698 footprints in SF; 4,325 San Mateo Co. footprints currently skipped)

### `sf_assessor_2025` — Assessor Historical Secured Property Tax Rolls
- URL: https://data.sfgov.org/d/wv5m-vpq2 — `closed_roll_year = 2025` (latest available 2026-11)
- Licence: PDDL 1.0
- Fields used: `parcel_number`, `year_property_built`, `number_of_stories`, `number_of_units`, `use_code`, `use_definition`, `property_class_code_definition`, `property_location`
- Use: construction year, stories, use. Known issues: placeholder spike years (1875–1900, esp. 1900), zeros, per-unit records for condos (see CLAUDE.md "Year cleaning").

### `sf_parcels` — Parcels – Active and Retired
- URL: https://data.sfgov.org/d/acdm-wktn
- Licence: PDDL 1.0
- Use: unit parcel (`blklot`) → map parcel (`mapblklot`) to group condo records; spatial fallback join.

### `sf_streets` — Streets – Active and Retired (centerlines)
- URL: https://data.sfgov.org/d/3psu-pn9h
- Licence: PDDL 1.0
- Use: geocoding street intersections for hand-researched historical boundaries (1906 fire line).

### `sf_street_trees` — Street Tree List
- URL: https://data.sfgov.org/d/tkzw-k3nq
- Licence: PDDL 1.0
- Use: real positions (and planting dates where recorded) of SF street trees.

### `overture` / `osm_via_overture` / `osm_parts_via_overture` — Overture Maps buildings
- URL: `s3://overturemaps-us-west-2/release/2026-10-21.0/theme=buildings/type={building,building_part}`
- Licence: ODbL 1.0 (buildings theme). Attribution: "© OpenStreetMap contributors, Overture Maps Foundation" (https://docs.overturemaps.org/attribution/). A few features come from Microsoft ML Buildings / Esri Community Maps (see `source_dataset`).
- Use: hand-modelled OSM 3D building parts (1,209 parts replacing 445 footprints: City Hall, Ferry Building, Transamerica, Salesforce Tower, 333 Bush, …); footprints for ~3,200 buildings missing from the 2016 DataSF snapshot; height fallback.

### `rpd_parks` — SF Recreation & Parks "RPD Parks"
- URL: https://data.sfgov.org/d/3nje-yn2u — Licence: PDDL 1.0
- Use: park polygons; creation years from `data/tables/parks.csv` (researched, one source URL per row; undated parks are not shown).

### `overture_base` — Overture base theme (land, land_use) — OSM
- `s3://overturemaps-us-west-2/release/2026-10-21.0/theme=base/type={land,land_use}` — ODbL 1.0, © OpenStreetMap contributors, Overture Maps Foundation
- Use: wood/forest extents (woodland trees), beaches/sand, federal parkland polygons (Presidio, Crissy Field, Lands End).

### `tiger2024` — US Census TIGER/Line 2024
- URLs: https://www2.census.gov/geo/tiger/TIGER2024/COUNTY/ , https://www2.census.gov/geo/tiger/TIGER2024/AREAWATER/
- Licence: public domain (US federal government work)
- Use: modern land polygon = Bay Area county outlines minus area-water polygons.

### `usgs_3dep` — USGS 3D Elevation Program, 1/3 arc-second DEM
- URL: `https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/current/` (cloud-optimised GeoTIFFs, windowed reads; overview 1 ≈ 40 m for the region grid, full ≈ 10 m resampled to the 30 m SF grid)
- Licence: public domain (USGS). Use: terrain elevation for the whole region; ground level under buildings, trees, roads and landmarks.

### `esa_worldcover_2021` — ESA WorldCover 10 m v200
- URL: `https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/` — Licence: **CC BY 4.0**, © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium.
- Use: present-day land cover (trees, shrub, grass, crops, built-up, bare, water, wetland) → the natural-cover rules and today's state; real tree positions for the procedural tree placement. Known artefacts handled in `terrain_tiles.py`: skyscraper shadows read as water, bridge decks read as built-up.

### `hisdac_fbuy` — HISDAC-US first built-up year (1810–2015)
- Leyk, S.; Uhl, J. H. (2018) "Historical settlement composite layer for the U.S. 1810–2015", https://doi.org/10.7910/DVN/PKJ90M (Harvard Dataverse); Scientific Data 5:180175. Licence: CC0.
- Use: year a 250 m cell first had a (surviving) building, from Zillow ZTRAX — urbanisation year outside SF and fallback inside SF. Like the assessor roll it only sees survivors.

### `sfei_baylands_poster` — SFEI EcoAtlas "Bay Area EcoAtlas: Baylands, past and present" poster
- File: `data/raw/sfei/pastpres2.pdf` (supplied by the project owner; https://www.sfei.org/sites/default/files/users/jamiek/pastpres2.pdf), © 2001 San Francisco Estuary Institute.
- Use: c.1800 and c.1998 bayland habitats (bay, flats, tidal marsh, ponds, salt ponds, diked baylands, fill) vectorised from the PDF and georeferenced (`pipeline/baylands_pdf.py`); lowest-priority historical-habitat source and the c.1998 "fill" mask.

### `sfei_historical_ecology` — SFEI Historical Ecology GIS data compilation
- https://www.sfei.org/data/historical-ecology-gis-data-compilation — per-study layers (historical baylands, Alameda Creek, Coyote Creek, Napa Valley, East Contra Costa, Lower Walnut Creek, …). Distributed under GPL v3 per the compilation; cite SFEI-ASC.
- Use: c.1800 habitat (overrides the poster where present).

### `sfei_hidden_nature_sf` — SFEI "Hidden Nature SF" historical habitats (2021)
- https://www.sfei.org/projects/hidden-nature-sf — SF's pre-development habitats (dunes, grassland, scrub, marsh, creeks). Cite SFEI-ASC / SF Public Utilities Commission.
- Use: highest-priority c.1800 cover inside San Francisco.

### `sf_permits` — DBI Building Permits
- https://data.sfgov.org/d/i98e-djp9 — PDDL 1.0. Use: completed new-construction / demolition permits → construction years for buildings the assessor roll dates wrongly.

### `overture_transportation` — Overture transportation theme (segments) — OSM
- `s3://overturemaps-us-west-2/release/2026-10-21.0/theme=transportation/type=segment` (motorway → tertiary, region bbox) — ODbL 1.0, © OpenStreetMap contributors, Overture Maps Foundation.
- Use: roads outside SF. Freeways take the opening year of the nearest researched route in `routes.csv`; other roads are dated from HISDAC.

### Researched tables (Phases 2–4)
- `data/manual/fill_zones.csv` + `fill_README.md`: dated bay fill, diking, piers, excavation, restoration (96 zones; Dow 1973, USGS OFR 90-253 / 2006-1037, BCDC 1982, NPS, SF Port histories — one source per row).
- `data/manual/sf_extent_YYYY.csv` + `sf_extent_README.md`: built-up extent of SF at nine snapshots 1849–1905 (Coast Survey, Sanborn, Langley directories, context statements — sources per file).
- `data/manual/routes.csv`: cable car, streetcar, Key System, rail, ferry, freeway and BART routes with opening/closing dates (source per row).
- `data/tables/places.csv` + `places_README.md`: era-accurate place names with years in use (source per row).
- `data/tables/landcover_history.csv`: dated land-cover eras (orchards, vineyards, ranches, parks, dunes reclaimed) — source per row.
- `data/tables/known_building_dates.csv`, `notable_pre1906.csv`: documented construction / demolition years and pre-1906 buildings (source per row).
- `data/tables/transbay_terminal.md`: Transbay Terminal 1939 research (HAER CA-2296 drawings and photos).

### `land_not_before` (manual)
- File: `data/manual/land_not_before.geojson`
- Treasure Island: built 1936–37 on the Yerba Buena Shoals for the 1939 Golden Gate International Exposition — https://en.wikipedia.org/wiki/Treasure_Island,_San_Francisco . Outline from TIGER.

### `fire_1906` (manual research)
- Files: `data/manual/fire_1906_boundary.csv`, `fire_1906_unburned_islands.csv`, `fire_1906_README.md` (sources per vertex)

### Tables
- `data/tables/population.csv`, `eras.csv`, `events.csv`, `landmarks.csv` — every row carries its `source_url`.

### Landmark reconstructions
- `data/research/landmarks.md`: per landmark dimensions, dates, colours, and Wikimedia Commons reference photos (file page, author, licence). Photos are used as modelling references only and are not redistributed (`data/raw/reference_photos/` is gitignored).

## Sources checked but not yet usable from the build environment
- SFEI EcoAtlas web services (https://www.sfei.org/) — behind a bot check; the poster PDF was supplied by hand and the GIS compilation downloads directly.
- OpenHistoricalMap (https://www.openhistoricalmap.org/) — API behind a bot check.
- Geofabrik / Overpass OSM extracts — network timeouts; Overture covers the OSM data needed so far.
- Census API (ACS B25034) — now requires a (free) key; needed for Phase 5 imputation.
