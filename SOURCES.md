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
| `viewer/public/data/roads-region.bin.gz`, `freeways.bin.gz` | OpenStreetMap via Overture transportation theme (ODbL) | **ODbL 1.0** |
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

### Researched tables (2026-11 pass)
- `data/tables/known_building_dates.csv` (now 1,076 rows): adds institutional / exempt buildings — UCSF Parnassus (2003 historic-resources survey), VA Fort Miley (2009 National Register nomination), Port of SF piers (2006 Embarcadero Historic District nomination), USF, City College, SFUSD high schools, SFHA housing (Sunnydale…), towers (Wikipedia list of tallest buildings). Source URL per row.
- `data/tables/notable_demolished.csv`: demolished post-1906 buildings with footprints and heights (source per row).
- `data/manual/redevelopment_areas.csv`: urban-renewal project areas and freeway takings with clearance years (SF Redevelopment Agency histories, Wikipedia, FoundSF; confidence per row).
- `data/tables/early_sf.csv` + `data/research/early_sf.md`: 160 structures 1700–1849 (Bancroft's lot notes, the *Annals of San Francisco*, Milliken / NPS for Mission Dolores, SF Planning Early Settlement context statement).
- `data/research/landmarks_batch4.md`: 1915 PPIE traced from the Library of Congress Sanborn map of the Exposition (https://www.loc.gov/item/sanborn00813_025/, Nov 1914, public domain); GGIE 1939 from the Official Guide plan; Presidio, Castillo, Mission compound, Playland, Woodward's Gardens, Mechanics' Pavilion, Sutro Heights.
- `data/manual/sanborn/western_addition_1899.geojson`, `western_addition_1913.geojson` (+ `README_western_addition.md`, `sheets_western_addition.csv`): building footprints, storeys and construction traced from the Library of Congress Sanborn Fire Insurance Maps of San Francisco — 1899 vol. 3 (https://www.loc.gov/item/sanborn00813_010/) and 1913 vols. 3–4 (https://www.loc.gov/item/sanborn00813_017/, https://www.loc.gov/item/sanborn00813_018/); public domain ("Library of Congress, Geography and Map Division, Sanborn Maps Collection"). Use: pre-redevelopment Western Addition (A-1/A-2 areas) instead of procedural rows; tool `pipeline/sanborn_trace.py`.
- `data/manual/sanborn/fishermans_wharf_{1899,1913,1950}.geojson`, `mission_bay_{1913,1950}.geojson` + `README_waterfront.md`: building footprints, wharf decks, storeys and uses traced from the Library of Congress Sanborn Fire Insurance Maps of San Francisco (public domain): 1899 vol. 1 https://www.loc.gov/item/sanborn00813_008/, 1913 vols. 1–2 https://www.loc.gov/item/sanborn00813_015/ and _016/, 1914 vol. 6 _020/, 1913–1950 corrected vols. 1, 2, 6 _030/, _031/, _035/; georeferenced on DataSF street centrelines (`pipeline/sanborn_trace_waterfront.py`, control in `data/manual/sanborn/control/`).
- `data/tables/golf_courses.csv` (opening years) with Overture `land_use` golf-course outlines; cemeteries and the Presidio Main Parade in `landcover_history.csv` (Presidio Trust; FoundSF / Wikipedia "Lone Mountain Cemetery").

### `overture_freeways` — Overture transportation segments (motorway, trunk, links)
- `theme=transportation/type=segment`, class motorway/trunk incl. `subclass = link`, with `road_flags` (is_bridge / is_tunnel), `level_rules` and `connectors` — ODbL 1.0, © OpenStreetMap contributors, Overture Maps Foundation. Use: freeway and ramp geometry and heights (`freeways.bin.gz`).

### `overture_rail` — Overture transportation segments (rail)
- `theme=transportation/type=segment`, `subtype = rail` (subway = BART, light_rail = Muni Metro, tram = F line / cable cars …) with `rail_flags` (is_bridge / is_tunnel / is_abandoned …) and `level_rules` — ODbL 1.0, © OpenStreetMap contributors, Overture Maps Foundation. Use: per-track BART and Muni geometry, aerial structures and tunnels (`transit.bin.gz`), and the track spacing trains follow.

### `bart_gtfs` — BART GTFS feed
- https://www.bart.gov/dev/schedules/google_transit.zip (BART developer licence; schedule data free to use with attribution). Use: line shapes, station positions and stop order (`transit-lines.json`, `transit-stations.json`). Trains are procedural (headway, speed profile), not the timetable.

### `sfmta_patterns`, `sfmta_stops` — SFMTA route patterns and stops (DataSF)
- https://data.sfgov.org/resource/9exe-acju (Muni route patterns), https://data.sfgov.org/resource/i28k-bkz6 (Muni stops) — PDDL. Use: Muni Metro J/K/L/M/N/T, F line and cable car centrelines and stops (`transit-lines.json`).

### Transit dates
- `data/tables/transit_stations.csv` (every BART and Muni Metro subway station with opening day) and `data/tables/transit_openings.csv` (opening day of each BART extension and Muni Metro segment) — Wikipedia "List of Bay Area Rapid Transit stations", station articles, "Muni Metro", "T Third Street", "Central Subway", "Oakland Airport Connector", "eBART"; source URL per row. Before 1980 Muni's streetcar and cable car history stays in `data/manual/routes.csv`.
- Vehicle dimensions (BART 70–75 ft × 10.5 ft cars; Muni LRVs 75 ft × 9 ft; PCC 50 ft; Powell cable cars 27.5 ft) from the vehicles' Wikipedia articles. Liveries are approximate (`procedural`).

### `overture_land_use` detail — golf, sport and park outlines
- `theme=base/type=land_use`, classes fairway, green, tee, rough, bunker, driving_range, pitch, track, playground, dog_park, plaza, garden, grass — ODbL 1.0 (OpenStreetMap). Use: `ground-detail.bin.gz` (dated by golf course / RPD park / first buildings nearby) and park labels (DataSF RPD parks, `parks.csv`).

### `land_not_before` (manual)
- File: `data/manual/land_not_before.geojson`
- Treasure Island: built 1936–37 on the Yerba Buena Shoals for the 1939 Golden Gate International Exposition — https://en.wikipedia.org/wiki/Treasure_Island,_San_Francisco . Outline from TIGER.

### `fire_1906` (manual research)
- Files: `data/manual/fire_1906_boundary.csv`, `fire_1906_unburned_islands.csv`, `fire_1906_README.md` (sources per vertex)

### Tables
- `data/tables/population.csv`, `eras.csv`, `events.csv`, `landmarks.csv` — every row carries its `source_url`.

### Landmark reconstructions
- `data/research/landmarks.md`: per landmark dimensions, dates, colours, and Wikimedia Commons reference photos (file page, author, licence). Photos are used as modelling references only and are not redistributed (`data/raw/reference_photos/` is gitignored).

### Region (Phase 5) — footprints, construction years, heights (2026-11 research)
Details, field names, coverage and licence notes: `data/research/region_buildings.md`; downloader `pipeline/download_region.py`. Raw files in `data/raw/region_years/`, `data/raw/region_heights/` (gitignored); owner names / mailing addresses never requested.
- `overture_region5` — Overture buildings + building parts 2026-10-21.0 clipped to Marin, Contra Costa, Alameda, San Mateo, Santa Clara (`data/raw/overture/2026-10-21.0/region5_{building,building_part}.parquet`; 1,861,043 + 3,763) — ODbL, © OpenStreetMap contributors, Overture Maps Foundation (+ Microsoft ML Buildings, Esri Community Maps, USGS LiDAR heights per `height_source`).
- `contra_costa_ccmap` — Contra Costa County CCMAP "Assessment Parcels" (`YR_HS_BLT`, `YR_BUILT`, use, values), https://gis.cccounty.us/arcgis/rest/services/CCMAP/Assessment_Parcels_ArcPro/MapServer/0 — public county service, "free to download" (https://www.contracosta.ca.gov/552/Maps-Property-Information); no explicit licence.
- `contra_costa_cccfpd` — Contra Costa County Fire Protection District "Assessor Parcels" (`BLD_EFFYR`, `STORIES`, `UNITS`, `NBR_BLDNGS`), https://services6.arcgis.com/CmHj285GYxHhHnTo/arcgis/rest/services/Assessor_Parcels/FeatureServer/0 — public agency layer, no licence stated.
- `santa_clara_county` — County of Santa Clara Planning "Parcels Public View" (`Year_Built`, April 2026), https://services2.arcgis.com/tcv2cMrq63AgvbHF/arcgis/rest/services/Parcels_Public_View/FeatureServer/0 — "There are no Use Constraints".
- `sunnyvale`, `milpitas`, `saratoga`, `los_gatos` — city/town parcel layers with the Santa Clara County roll year + stories/units/effective year (URLs in the research note) — city publications, no licence stated (Milpitas "© City of Milpitas 2020").
- `alameda_county_2021` — whole-county copy of the Alameda County assessor roll + characteristics (`YearBuilt`, `EffectiveY`, `Stories`, `Units`; April 2021) shared on ArcGIS Online by MNS Engineers, https://services9.arcgis.com/l0PUGx9JqRxaCPsG/arcgis/rest/services/Alameda_Co_Pcls/FeatureServer/0 — no licence stated; the Assessor sells characteristics (third-party copy, use with care).
- `alameda_south_2026` — City of Union City Planning parcels July 2026 (Fremont, Hayward, Union City, Newark; `YRBLT`, `YREFF`, `STORIES`, `UNITS`), https://services7.arcgis.com/T3LbxamSmhpjBppB/arcgis/rest/services/UC_Parcels_07_2026_view/FeatureServer/12 — no licence stated.
- `alameda_trivalley_zone7` — Zone 7 Water Agency parcels with Alameda County Assessor data (Livermore, Pleasanton, Dublin, east county), https://services6.arcgis.com/yGWezgaq4oIlwApY/arcgis/rest/services/Parcels_LayFH/FeatureServer/0 — no licence stated.
- `berkeley`, `albany`, `emeryville` — City of Berkeley TaxParcel (2017), City of Albany ParcelsWeb, City of Emeryville Parcels (Alameda County roll year, effective year, stories, units; URLs in the research note) — no licence stated.
- `san_mateo_city`, `belmont`, `san_bruno`, `portola_valley`, `san_mateo_county_office` — City of San Mateo EnerGov TaxParcel, City of Belmont Property Lines, City of San Bruno and Town of Portola Valley Parcels, County of San Mateo ACTIVE_PARCELS_APN (`OFFICEYEARBUILT`, 843 office parcels) — no licence stated.
- `hillsborough` — Town of Hillsborough parcels from the housing-element consultant HLA (`hl_yearbuilt`, 2022) — third-party, no licence stated.
- `south_sf_corelogic` — "SSF_Corelogic_Parcels" (consultant layer, CoreLogic attributes) — commercial origin; validation only.
- `fema_r9_lightbox` — FEMA Region 9 "Property – Structures – Static – Point – Building Type (R9)" (item 712097874f5740a3a8d1865cab585f84; building points from Microsoft Buildings / USA Structures with Lightbox SmartParcels `YR_BLT`, `YR_BLT_EFFECT`, `STORIES_NUMBER`, construction / wall / roof), https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/Property_Structures_Static_Points_Building_Type_R9/FeatureServer — publicly readable, no licence stated, **attributes from a commercial vendor**: owner decision before shipping (98.5 % same year as the public rolls where both exist). Also attached to the Marin and San Mateo county parcels by APN.
- `marin_parcels`, `san_mateo_parcels` — Marin County CDA / Assessor parcels (open data, https://services6.arcgis.com/T8eS7sop5hLmgRRH/arcgis/rest/services/Parcels/FeatureServer/0) and County of San Mateo ACTIVE_PARCELS_APN (https://gis.smcgov.org/maps/rest/services/Common/ACTIVE_PARCELS_APN/FeatureServer/0) — parcel bases (APN), no licence stated.
- `san_jose_hri` — City of San José Historic Resources Inventory (`TRUEYR`, `ESTIMATEDYR`, demolished / moved flags, architect), https://geo.sanjoseca.gov/server/rest/services/OPN/OPN_OpenDataService/MapServer/406 — City of San José open data (no-warranty disclaimer).
- `ca_ohp_berd` — California Office of Historic Preservation, Built Environment Resource Directory, county CSVs (export 2026-02-02; construction years, NR/CR status codes), https://ohp.parks.ca.gov/?page_id=30338 — State of California (OHP Conditions of Use); located by APN / address.
- `osm_start_date` — OpenStreetMap buildings tagged `start_date` / `construction_date` (Overpass API; download pending — Overpass unreachable 2026-11-08) — ODbL.
- `tiger2024_place` — US Census TIGER/Line 2024 places, California (https://www2.census.gov/geo/tiger/TIGER2024/PLACE/tl_2024_06_place.zip) — public domain; city / CDP names for the coverage report.
- `san_mateo_county_footprints` — County of San Mateo "Building Footprints" (229,298; `BLDGHEIGHT` feet, `BASEELEV`), https://services.arcgis.com/yq3FgOI44hYHAFVZ/arcgis/rest/services/Building_Footprints/FeatureServer/0 — no licence stated; height source for San Mateo.
- `marin_county_footprints` — Marin County "Building Footprints" (113,271; outlines from the 2004 Vargis orthophoto, `SourceDateYear`; height fields empty), https://services6.arcgis.com/T8eS7sop5hLmgRRH/arcgis/rest/services/Building_Footprints/FeatureServer/0 — no licence stated; "stood by 2004" constraint.
- `loc_sanborn_region` — Library of Congress Sanborn Fire Insurance Maps for the five counties (362 items, ids per city in the research note; public domain, "Library of Congress, Geography and Map Division, Sanborn Maps Collection") — listed only, not traced.

## Sources checked but not yet usable from the build environment
- SFEI EcoAtlas web services (https://www.sfei.org/) — behind a bot check; the poster PDF was supplied by hand and the GIS compilation downloads directly.
- OpenHistoricalMap (https://www.openhistoricalmap.org/) — API behind a bot check.
- Geofabrik / Overpass OSM extracts — network timeouts; Overture covers the OSM data needed so far.
- Census API (ACS B25034) — now requires a (free) key; needed for Phase 5 imputation.
- Alameda County Assessor property characteristics (sold, not on the open-data portal), Marin County Assessor roll (per-parcel lookup only; GIS server behind Cloudflare), San Mateo County roll characteristics (not published) — public copies / FEMA-Lightbox used instead (see `data/research/region_buildings.md`).
