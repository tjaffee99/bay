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
- SFEI EcoAtlas / Historical Baylands (https://www.sfei.org/) — behind a bot check; needed for Phase 2, download manually.
- OpenHistoricalMap (https://www.openhistoricalmap.org/) — API behind a bot check.
- Geofabrik / Overpass OSM extracts — network timeouts; Overture covers the OSM data needed so far.
- Census API (ACS B25034) — now requires a (free) key; needed for Phase 5 imputation.
