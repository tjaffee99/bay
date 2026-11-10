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
| `viewer/public/data/region-trees/**` | city / county / campus tree inventories (`region_trees`, below) + USFS Urban Tree Database growth equations | mixed: San José CC BY 4.0; the others published without a licence (public records) — attribute every source (list in `region-trees/index.json`) |
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

### `region_trees` — street and park tree inventories of the five counties (2026-11)
Built by `pipeline/region_trees.py` (raw layers: `data/raw/region_trees/<id>.parquet` + `<id>.source.json`, downloaded 2026-11-09). Positions, species, DBH and, where present, height, crown spread, planting and inventory dates; every record as published by the city. Licence: only San José states one; the others are public city / county / campus GIS services published without a licence or with a no-warranty disclaimer — used as public records with attribution.

| id | publisher / attribution | layer | records → trees used | licence / terms |
|---|---|---|---|---|
| `san_jose` | City of San José, Dept. of Transportation (Davey 2014 inventory + updates) | https://geo.sanjoseca.gov/server/rest/services/OPN/OPN_OpenDataService/MapServer/510 (portal: https://data.sanjoseca.gov/dataset/street-tree) | 344,875 → 267,094 | **CC BY 4.0** |
| `oakland` | City of Oakland, 2019–20 public tree inventory | https://services.arcgis.com/9tC74aDHuml0x5Yz/arcgis/rest/services/Oakland_Public_Tree_Inventory_/FeatureServer/0 (map: https://www.oaklandca.gov/resources/oakland-public-tree-map) | 70,420 → 68,297 | none stated |
| `berkeley` | City of Berkeley Parks Division / Arborwell, 2013 urban forest inventory (archived by the UC Berkeley Library, rights "Public") | https://geodata.lib.berkeley.edu/catalog/berkeley-s7gq2s | 46,037 → 34,889 | public |
| `palo_alto` | City of Palo Alto Public Works | https://gis.cityofpaloalto.org/server/rest/services/Parcel/ParcelReport/MapServer/2 | 39,629 → 33,348 | none stated |
| `mountain_view` | City of Mountain View | https://maps.mountainview.gov/arcgis/rest/services/Public/Trees/FeatureServer/0 | 35,192 → 35,180 | none stated (no-warranty disclaimer) |
| `hayward` | City of Hayward / Davey Resource Group (2010 inventory) | https://maps.hayward-ca.gov/arcgis/rest/services/MaintenanceServices/TreeInventory/MapServer/0 | 37,970 → 29,803 | none stated |
| `alameda` | City of Alameda / West Coast Arborists | https://services9.arcgis.com/ucDLsG1EwPnOGY4c/arcgis/rest/services/City_Tree_view/FeatureServer/0 | 34,640 → 25,160 | none stated |
| `pleasanton` | City of Pleasanton / West Coast Arborists | https://services2.arcgis.com/yrktbS5Xw87hJQvs/arcgis/rest/services/TreeInvPleasanton_Public/FeatureServer/0 | 28,744 → 23,960 | none stated |
| `san_ramon` | City of San Ramon / West Coast Arborists (Feb 2017) | https://gis.sanramon.ca.gov/server/rest/services/Fieldwork/Trees/FeatureServer/0 | 50,975 → 44,515 | none stated |
| `cupertino` | City of Cupertino Public Works / GIS | https://gis.cupertino.org/cupgis/rest/services/Public/AmazonData/MapServer/29 | 24,609 → 24,213 | none stated |
| `san_mateo` | City of San Mateo Public Works / Davey (2009–12) | https://services2.arcgis.com/g26Y0m7OCdjU0ObA/arcgis/rest/services/Street_Trees/FeatureServer/0 | 24,045 → 23,360 | none stated |
| `menlo_park` | City of Menlo Park / West Coast Arborists (2026) | https://gisweb.menlopark.gov/server/rest/services/GISWeb/Trees2026/FeatureServer/3 | 19,185 → 18,950 | none stated |
| `milpitas` | City of Milpitas / West Coast Arborists (© City of Milpitas 2022) | https://services8.arcgis.com/OPmRdssd8jj0bT5H/arcgis/rest/services/Trees%20West%20Coast%20Arborist/FeatureServer/0 | 18,198 → 17,149 | none stated |
| `santa_clara` | City of Santa Clara Public Works (Lucity) | https://map.santaclaraca.gov/maps/rest/services/Lucity/StreetTrees/MapServer/0 | 13,208 → 10,494 | none stated |
| `emeryville` | City of Emeryville / West Coast Arborists (2004 survey) | https://services3.arcgis.com/ljOdqLVbHpS7dOJQ/arcgis/rest/services/Trees_Authoritative_view/FeatureServer/0 | 3,807 → 3,549 | none stated |
| `los_gatos`, `sunnyvale`, `scc_county` | Town of Los Gatos, City of Sunnyvale (a 10,000-record part of the city's ~37,000 street trees), County of Santa Clara parks — compiled by the County of Santa Clara | https://services.arcgis.com/NkcnS0qk4w2wasOJ/arcgis/rest/services/Tree_Inventories_in_Santa_Clara_County_WFL1/FeatureServer (layers 3, 1, 0) | 13,207 → 12,139; 10,000 → 8,232; 19,103 → 15,515 (in the map extent) | none stated |
| `stanford` | Stanford University campus tree database | https://services.arcgis.com/7CRlmWNEbeCqEJ6a/arcgis/rest/services/Stanford_Trees_Basic_WFL1/FeatureServer/1 | 13,364 → 13,344 | none stated |
| `santa_clara_university` | Santa Clara University sustainability office tree survey (2025–26) | https://services9.arcgis.com/4mGCdwoq2Vacd9uM/arcgis/rest/services/Tree_Data_(Updated_11_21_2025)/FeatureServer/0 | 760 → 759 | none stated |
- Checked, nothing public found (2026-11): Fremont (77k-tree 2020 inventory, report only), Sunnyvale's full TreeKeeper inventory, Redwood City, Walnut Creek, San Rafael, Richmond, Concord, Livermore (pruning-zone polygons only), Daly City, South San Francisco, Burlingame, San Leandro, Saratoga (empty layer). The USFS "Raw urban street tree inventory data for 49 California cities" (RDS-2017-0010) has addresses, not positions.
- Growth: USDA Forest Service **Urban Tree Database** (McPherson, van Doorn & Peper 2016, RDS-2016-0005, https://doi.org/10.2737/RDS-2016-0005; public domain US government work): `TS6_Growth_coefficients.csv` age-from-DBH, height-from-DBH and crown-diameter-from-DBH equations for the Northern California Coast (reference city Berkeley), Inland Valleys (Modesto), Sacramento Valley, Southern California Coast and Inland Empire regions.
- Use: real positions of ~710,000 street / park trees outside San Francisco; planting year from a recorded date (exact) or the DBH at the inventory date (estimated), bounded by the street and the ground (see the stage's docstring).

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

### `usgs_3dep_lpc_sf2023` — USGS 3DEP lidar point cloud, CA_SanFrancisco_1_B23 (flown 2023-04-20)
- Project CA_SanFrancisco_B23, work unit 300449, acquired by NV5 Geospatial for USGS on 2023-04-20 (vendor metadata `begdate/enddate`), nominal pulse spacing 0.15 m (~44 pts/m²), USGS Lidar Base Specification 2023 rev. A; NAD83(2011) San Francisco CS13 / NAVD88 (Geoid18). Classes: 1 unclassified, 2 ground, 7/18 noise, 9 water, 17 bridge deck, 20 ignored ground — **no building class**, so buildings are found inside the footprints.
- Access: Entwine Point Tiles (re-projected to EPSG:3857) on the public AWS bucket, `https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CA_SanFrancisco_1_B23/ept.json` (project index: `https://github.com/hobuinc/usgs-lidar`, `boundaries/resources.geojson`). Original 1 km LAZ tiles + reports: `https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/CA_SanFrancisco_B23/`, `https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/Elevation/metadata/CA_SanFrancisco_B23/`.
- Licence: public domain (USGS); credit "U.S. Geological Survey, 3D Elevation Program".
- Use: `pipeline/lidar_parts.py sf` streams EPT nodes to depth 8 (~0.64 m voxels, 1.65 G points near footprints, ~13 min) into a 1 m DSM / last-return DSM / DTM over SF (`data/interim/lidar/sf/`, 266 MB) and cuts footprints into roof plateaus → stepped building parts (`data/interim/sf_lidar_parts.parquet`: 3,663 footprints → 8,668 parts, incl. 152 OSM building:part outlines whose parts carry one height for all or disagree with the LiDAR) and whole-footprint 2023 heights (`sf_lidar_heights.parquet`; vs the DataSF 2010 heights: median difference −0.01 m). Buildings finished after April 2023 keep their flat footprint.
- Other SF collections checked: ARRA-CA_GoldenGate_2010 (the 2010 survey behind DataSF `hgt_median_m`), ARRA-CA_SanFranCoast_2010, CA_SanFranBayFEMA_2004, USGS_LPC_CA_NoCAL_Wildfires_B5b_2018 (covers about half of SF). For `lidar_parts.py region`: CA_AlamedaCo_2_2021 / CA_AlamedaCo_3_2021 (Oakland), CA_SantaClaraCounty_2020 (San José); the newest project year covering the bbox is chosen.

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
- `data/tables/known_building_dates.csv` `sfusd_*` rows (225 footprints, 71 SFUSD school sites whose assessor year is the exempt-parcel placeholder 1900 or missing): San Francisco public schools annual reports 1904-17 and 1924-29 (buildings completed / dedicated per year, https://archive.org/details/annualreporto19041917sanf, https://archive.org/details/annualreporto19241929sanf), *A Review of Accomplishments … 1936-37* (https://archive.org/details/reviewofaccompli1936anf), SFUSD School Accountability Report Cards (facility section), PCAD; otherwise SF Planning "Historic Resources" dataset `yearbuilt` per parcel (DataSF njrt-gtwr, https://data.sfgov.org/d/njrt-gtwr, PDDL; survey years, not independently verified — said so per row).
- `data/tables/park_names.csv`: name histories of renamed parks (SF and region), source per row — SF Recreation & Park Commission minutes 1941-95 (SFPL scans, https://archive.org/details/minutesrecreatio1978sanf etc.), Playground Commission annual reports 1912-26 / 1928-30 (https://archive.org/details/annualreporto19121926sanf, https://archive.org/details/annualreporto19281930sanf), the 1954 Planning Department recreation plan (https://archive.org/details/reportonplanforl1954sanf), Board of Supervisors resolutions, Rec & Park / city pages, Wikipedia, local news.
- `data/tables/notable_demolished.csv`: demolished post-1906 buildings with footprints and heights (source per row).
- `data/manual/redevelopment_areas.csv`: urban-renewal project areas and freeway takings with clearance years (SF Redevelopment Agency histories, Wikipedia, FoundSF; confidence per row).
- `data/tables/early_sf.csv` + `data/research/early_sf.md`: 160 structures 1700–1849 (Bancroft's lot notes, the *Annals of San Francisco*, Milliken / NPS for Mission Dolores, SF Planning Early Settlement context statement).
- `data/tables/early_region.csv` + `data/research/early_region.md`: 142 rows (≈970 structures) 1700–c.1850 in Santa Clara, Alameda, Contra Costa, San Mateo and Marin: Mission Santa Clara's five sites, the pueblo of San José, Mission San José, Mission San Rafael, the Mission Dolores outposts, rancho adobes and Ohlone / Bay Miwok / Coast Miwok villages. Sources (facts only, per row in `source_url`): Skowronek & Wizorek, "Archaeology at Santa Clara de Asís" (*PCAS Quarterly* 33(3), 1997, https://www.pcas.org/Vol33N3/333Skowr.pdf); Santa Clara University Digital Humanities "Sites of Mission Santa Clara" (site coordinates, https://dh.scu.edu/exhibits/neatline/show/sites-of-mission-santa-clara); Bancroft, *History of California* i–iii (https://archive.org/details/historyofcalifor01banc …); F. Hall, *History of San José* (1871, https://archive.org/details/historyofsanjos00hall); *Clyde Arbuckle's History of San José* (1985, https://archive.org/details/casjhsj_000308); Milliken, Shoup & Ortiz, *Ohlone/Costanoan Indians of the San Francisco Peninsula* (NPS 2009, https://npshistory.com/publications/goga/ohlone-indians.pdf); California Historical Landmark listings (https://ohp.parks.ca.gov/ListedResources/Detail/<no.>, marker GPS from https://www.californiahistoricallandmarks.com/landmarks/chl-<no.>); Peralta Hacienda chronology (https://www.peraltahacienda.org/PeraltaHistoryChron.htm); El Cerrito, San Pablo, Milpitas, Mill Valley and Sausalito historical societies, John Marsh House Trust, City of Hayward, USGS OFR 2008-1121; Wikipedia (Coast Miwok village list after Barrett 1908, Sánchez Adobe Park, Alviso, Mission San Rafael). Sizes and orientations of surviving adobes measured on `overture_region5` footprints (ODbL; no geometry copied); street-intersection anchors from `overture_transportation` (ODbL).
- `data/research/landmarks_batch4.md`: 1915 PPIE traced from the Library of Congress Sanborn map of the Exposition (https://www.loc.gov/item/sanborn00813_025/, Nov 1914, public domain); GGIE 1939 from the Official Guide plan; Presidio, Castillo, Mission compound, Playland, Woodward's Gardens, Mechanics' Pavilion, Sutro Heights.
- `data/manual/sanborn/western_addition_1899.geojson`, `western_addition_1913.geojson` (+ `README_western_addition.md`, `sheets_western_addition.csv`): building footprints, storeys and construction traced from the Library of Congress Sanborn Fire Insurance Maps of San Francisco — 1899 vol. 3 (https://www.loc.gov/item/sanborn00813_010/) and 1913 vols. 3–4 (https://www.loc.gov/item/sanborn00813_017/, https://www.loc.gov/item/sanborn00813_018/); public domain ("Library of Congress, Geography and Map Division, Sanborn Maps Collection"). Use: pre-redevelopment Western Addition (A-1/A-2 areas) instead of procedural rows; tool `pipeline/sanborn_trace.py`.
- `data/manual/sanborn/fishermans_wharf_{1899,1913,1950}.geojson`, `mission_bay_{1913,1950}.geojson`, `potrero_point_{1914,1950}.geojson`, the railway centrelines `mission_bay_{1913,1950}_tracks.geojson` / `potrero_point_{1914,1950}_tracks.geojson` + `README_waterfront.md`: building footprints, wharf decks, rail-yard tracks, storeys and uses traced from the Library of Congress Sanborn Fire Insurance Maps of San Francisco (public domain): 1899 vol. 1 https://www.loc.gov/item/sanborn00813_008/, 1913 vols. 1–2 https://www.loc.gov/item/sanborn00813_015/ and _016/, 1914 vol. 6 _020/, 1913–1950 corrected vols. 1, 2, 6 _030/, _031/, _035/; georeferenced on DataSF street centrelines (`pipeline/sanborn_trace_waterfront.py`, control in `data/manual/sanborn/control/`).
- `data/manual/sanborn/soma_industrial_{1913,1950}.geojson`, `butchertown_{1914,1950}.geojson`, `north_waterfront_{1913,1950}.geojson`, their `*_tracks.geojson` railway centrelines and `*_coverage.geojson` + `README_industrial.md`: industrial / warehouse footprints and rail tracks traced from the Library of Congress Sanborn Fire Insurance Maps of San Francisco (public domain, "Library of Congress, Geography and Map Division, Sanborn Maps Collection"): 1913 vol. 1 https://www.loc.gov/item/sanborn00813_015/ (Produce Market, north waterfront), 1913 vol. 2 https://www.loc.gov/item/sanborn00813_016/ (South of Market), 1914 vol. 8 https://www.loc.gov/item/sanborn00813_022/ (Butchertown / Islais Creek / Bayview; title page 1914, LOC catalogue note "1922"), and the corrected 1950 states 1913–1950 vol. 1 https://www.loc.gov/item/sanborn00813_030/, 1913–Sep 1950 vol. 2 https://www.loc.gov/item/sanborn00813_031/, 1914–Feb 1950 vol. 8 https://www.loc.gov/item/sanborn00813_037/. Georeferenced on DataSF street centrelines (`pipeline/sanborn_trace_industrial.py`, control in `data/manual/sanborn/control/industrial/`). Use: real factories, warehouses, slaughterhouses and rail spurs instead of procedural fabric.
- `data/manual/sanborn/san_jose_downtown_{1915,1950}.geojson`, `san_jose_downtown_coverage.geojson` + `README_san_jose.md`: downtown San José building footprints (Park Center Plaza, plaza / Fairmont / convention-centre blocks, First / Market St core, St James Park, SR 87 corridor) traced from the Library of Congress Sanborn Fire Insurance Maps of San José, California (public domain, "Library of Congress, Geography and Map Division, Sanborn Maps Collection"): 1915 vol. 1 https://www.loc.gov/item/sanborn00817_004/ (sheets 63-65, 79-92), 1915 vol. 2 https://www.loc.gov/item/sanborn00817_005/ (156, 158), 1915-Jan 1950 vol. 1 https://www.loc.gov/item/sanborn00817_008/ (same scans as _006) and vol. 2 https://www.loc.gov/item/sanborn00817_007/ (same scans as _009). Georeferenced on County of Santa Clara parcel property lines (Parcels Public View, April 2026) and Overture road centrelines (`pipeline/sanborn_trace_southbay.py`, control in `data/manual/sanborn/control/san_jose/`).
- `data/raw/overture/2026-10-21.0/roads_southbay_core.parquet`: Overture Maps transportation segments, release 2026-10-21.0, all road classes for downtown San José, old Santa Clara and Palo Alto University Ave (ODbL; (c) OpenStreetMap contributors, Overture Maps Foundation) - street crossings / lines for the San José Sanborn control.
- San José clearance dates in `data/manual/redevelopment_areas.csv` (`sj_*` rows): Park Center Project Building Survey finding aid, History San José (blight 1960, plan 1961, groundbreaking 1968), https://oac.cdlib.org/findaid/ark:/13030/c84m9bw5/; Route 87 history, https://www.cahighways.org/ROUTE087.html; I-280 opening (mid-1972), https://www.interstate-guide.com/i-280-ca/ and SJSU Mineta Transportation Institute "Beneath I-280" (2024), https://transweb.sjsu.edu/research/2304-Freeways-Neighborhoods-Redevelopment; Heinlenville, https://en.wikipedia.org/wiki/Heinlenville; Market Street Chinatowns, https://en.wikipedia.org/wiki/Chinatowns_in_San_Jose,_California; convention centre, https://en.wikipedia.org/wiki/San_Jose_Convention_Center.
- `data/manual/sanborn/oakland_west_{1912,1951}.geojson`, `oakland_downtown_{1912,1951}.geojson`, their `*_tracks.geojson` and `*_coverage.geojson` + `README_oakland.md`: West Oakland and downtown Oakland building footprints and track centrelines (7th St corridor, Main Post Office / West Oakland BART blocks, Cypress St corridor, Acorn, City Center, Convention Center, I-980 edge) traced from the Library of Congress Sanborn Fire Insurance Maps of Oakland, California (public domain, "Library of Congress, Geography and Map Division, Sanborn Maps Collection"): 1911-1912 vol. 1 https://www.loc.gov/item/sanborn00727_005/ (sheets 52, 57, 71, 77, 79-82, 84-86, 92, 95-100, 102) and its corrected state 1912-Nov 1951 vol. 1 https://www.loc.gov/item/sanborn00727_015/ (same sheets). Georeferenced on Alameda County parcel property lines (`alameda_county_2021`) and Overture road centrelines (`pipeline/sanborn_trace_eastbay.py`, control in `data/manual/sanborn/control/oakland/`); `modern_overlap` against `overture_region5` (ODbL).
- `data/manual/sanborn/oakland_sr24_{1912,1951}.geojson`, `oakland_i980n_{1912,1951}.geojson`, `oakland_i580_{1912,1951}.geojson` (+ `_coverage`) and `README_oakland.md` (section "Freeway corridors"): buildings in the rights-of-way of SR-24 (Grove-Shafter), I-980 north of 11th St and I-580 (MacArthur) east of the Maze, traced from the Library of Congress Sanborn Fire Insurance Maps of Oakland, California (public domain, "Library of Congress, Geography and Map Division, Sanborn Maps Collection"): 1911-1912 vol. 1 https://www.loc.gov/item/sanborn00727_005/ (sheets 12, 16-20, 31, 32, 40-42, 50, 62, 75, 76), 1911 vol. 2 https://www.loc.gov/item/sanborn00727_006/ (126, 127, 133), 1911-1912 vol. 3 https://www.loc.gov/item/sanborn00727_007/ (281-283, 293-296, 303-306, 310, 333, 334, 345, 346, 359) and the corrected states 1912-Nov 1951 vol. 1 https://www.loc.gov/item/sanborn00727_015/, 1911-Nov 1950 vol. 2 https://www.loc.gov/item/sanborn00727_016/ and 1911-Oct 1950 vol. 3 https://www.loc.gov/item/sanborn00727_017/ (same sheets; 293 re-drawn Oct 1931). Georeferenced on Alameda County parcel property lines (`alameda_county_2021`) and Overture road centrelines (roads_region + roads_local, release 2026-10-21.0, ODbL) with `pipeline/sanborn_trace_oakland_corridors.py` (control in `data/manual/sanborn/control/oakland_corridors/`); `modern_overlap` against `overture_region5` (ODbL); freeway lines in the check images: Overture motorway segments (ODbL).
- `data/manual/sanborn/oakland_lakeside_{1911,1950}.geojson`, `oakland_adams_point_{1911,1950}.geojson`, `oakland_eastlake_{1911,1950}.geojson` (+ `_coverage`) and `README_oakland_central.md`: central Oakland east of Broadway (Lakeside / Uptown / the Gold Coast, Broadway - Lake Merritt, 9th - 20th St; Adams Point and Broadway - Harrison 20th - 28th St; Eastlake, Lake Shore Blvd - 7th Ave, E 11th - E 18th St) building footprints traced from the Library of Congress Sanborn Fire Insurance Maps of Oakland, California (public domain, "Library of Congress, Geography and Map Division, Sanborn Maps Collection"): 1911 vol. 2 https://www.loc.gov/item/sanborn00727_006/ (sheets 151-155, 162-168; 135, 137, 141, 142, 144, 145, 156, 157; Eastlake 185, 186, 199-201) and 1911-Nov 1950 vol. 2 https://www.loc.gov/item/sanborn00727_016/ (same sheets; 152-154 re-drawn 1925 / 1944). Georeferenced on Alameda County parcel property lines (`alameda_county_2021`) and Overture road centrelines (roads_region + roads_local, ODbL) with `pipeline/sanborn_trace_oakland_central.py` (control in `data/manual/sanborn/control/oakland_central/`); `modern_overlap` against `overture_region5` (ODbL).
- `data/raw/overture/2026-10-21.0/roads_oakland_sanborn.parquet`: Overture Maps transportation segments, release 2026-10-21.0, `subtype = road`, all classes in (-122.335, 37.780, -122.245, 37.840) (ODbL; (c) OpenStreetMap contributors, Overture Maps Foundation) - street crossings / lines for the Oakland Sanborn control and the `oak_*` clearance rings.
- `data/manual/sanborn/berkeley_{downtown,southside,west}_1911.geojson`, their `*_coverage.geojson` + `README_berkeley.md`: building footprints of downtown Berkeley, the Southside blocks cleared by the University (Sproul Plaza, Student Union, Edwards Stadium, residence halls, People's Park) and the West Berkeley industrial waterfront, traced from the Library of Congress Sanborn Fire Insurance Maps of Berkeley, California, 1911 vol. 1 https://www.loc.gov/item/sanborn00419_002/ (sheets 47, 48, 61-63, 72, 73, 75, 83-90, 93-98; public domain, "Library of Congress, Geography and Map Division, Sanborn Maps Collection"). The 1917, 1929 and 1950 Berkeley editions (`sanborn00419_004`-`_011`) are catalogued but not digitized. Georeferenced on Alameda County parcel property lines (`alameda_county_2021`) and Overture road centrelines (`roads_region` + `roads_local`, ODbL) with `pipeline/sanborn_trace_eastbay_cities.py` (control in `data/manual/sanborn/control/berkeley/`).
- `data/manual/sanborn/berkeley_northside_1911.geojson` (+ coverage): 169 Northside houses of the 1911 Berkeley Sanborn destroyed in the 1923 fire, traced by OpenHistoricalMap contributors (CC0; ways tagged `source=1911 Sanborn Map`, `wikidata=Q4561337`; https://www.openhistoricalmap.org, Overpass https://overpass-api.openhistoricalmap.org/api/interpreter), re-written in the Sanborn schema. `data/manual/redevelopment_areas.csv` row `berk_fire_1923`: the 1923 Berkeley fire zone (17 Sep 1923) from OHM relation 2743804 (CC0), itself from the East Bay Water Company "Map of Berkeley Fire Zone, 17 Sept 1923" (in *The Story of the Berkeley Fire*, Berkeley Public Library).
- `data/manual/sanborn/alameda_westend_{1897,1948}.geojson`, `alameda_westend_coverage.geojson` + `README_alameda.md`: Alameda West End (3rd St - Webster St, Pacific Ave - the old south shore) from the Library of Congress Sanborn Fire Insurance Maps of Alameda, California (public domain): 1897 https://www.loc.gov/item/sanborn00374_001/ and the 1941 report corrected to 1948 https://www.loc.gov/item/sanborn00374_002/ (sheets 4, 9-12, 14, 15 of both; the 1897 sheets SIFT-registered onto the 1948 plates). Bath houses / Neptune Beach already in `data/manual/vanished_sites/` are not repeated. Control: Alameda County parcels 2021 and Overture road centrelines (ODbL); `pipeline/sanborn_trace_eastbay_cities.py`, `data/manual/sanborn/control/alameda/`.
- `data/manual/sanborn/richmond_downtown_1916.geojson`, `richmond_downtown_coverage.geojson` + `README_richmond.md`: downtown Richmond (Macdonald Ave, Barrett - Chanslor Ave, 4th - 13th St) from the Library of Congress Sanborn Fire Insurance Maps of Richmond, California, June 1916 https://www.loc.gov/item/sanborn00787_004/ (sheets 20, 21, 27, 28, 29; public domain). The 1930 and 1950/51 Richmond editions are not digitized. Control: Overture road-centreline crossings (ODbL); `pipeline/sanborn_trace_eastbay_cities.py`, `data/manual/sanborn/control/richmond/`.
- `data/manual/sanborn/san_mateo_downtown_{1908,1920}.geojson`, `san_mateo_downtown_coverage.geojson` + `README_san_mateo.md`: downtown San Mateo (B St / 3rd Av core, the S.P. station plaza and yards, C -> I St east of the tracks, A St -> B St, 1st -> 9th Av) from the Library of Congress Sanborn Fire Insurance Maps of San Mateo, California (public domain, "Library of Congress, Geography and Map Division, Sanborn Maps Collection"): April 1908 https://www.loc.gov/item/sanborn00824_005/ (sheets 11, 12, 14-17) and May 1920 https://www.loc.gov/item/sanborn00824_006/ (sheets 4, 9, 10, 20, 21, 25-27). The May 1920 - Feb 1950 edition (`sanborn00824_007`) has no images. Control: San Mateo County active parcels (https://gis.smcgov.org/maps/rest/services/Common/ACTIVE_PARCELS_APN/FeatureServer/0, 2026-11-08) and Overture road centrelines (`roads_local` + `roads_region`, ODbL); `pipeline/sanborn_trace_peninsula.py`, `data/manual/sanborn/control/san_mateo/`.
- `data/manual/sanborn/palo_alto_downtown_{1901,1904,1908}.geojson`, `palo_alto_mayfield_{1904,1908}.geojson`, their `*_coverage.geojson` + `README_palo_alto.md`: downtown Palo Alto (Alma -> Cowper St, Palo Alto Av -> Channing Av) and old Mayfield (Lincoln Av = California Av, El Camino Real -> the tracks) from the Library of Congress Sanborn Fire Insurance Maps (public domain): Palo Alto May 1908 https://www.loc.gov/item/sanborn00747_005/ (sheets 11, 12, 16-19), June 1904 https://www.loc.gov/item/sanborn00747_004/ (7, 8, 12-15) and August 1901 https://www.loc.gov/item/sanborn00747_003/ (5, 6, 11, 12), the earlier editions SIFT-registered onto the later plates; Mayfield May 1908 https://www.loc.gov/item/sanborn00677_005/ (3-5) and June 1904 https://www.loc.gov/item/sanborn00677_004/ (2-4). The 1924 / 1949 Palo Alto and 1925 / 1945 Mayfield volumes have no images. Control: Santa Clara County parcels (Parcels Public View, April 2026) and Overture road centrelines (ODbL); `pipeline/sanborn_trace_peninsula.py`, `data/manual/sanborn/control/palo_alto/`, `control/mayfield/`. OpenHistoricalMap (CC0) was checked: its Sanborn-traced buildings in the area are in Menlo Park, not Palo Alto (`data/raw/ohm/ohm_peninsula_buildings.json`).
- Oakland clearance dates in `data/manual/redevelopment_areas.csv` (`oak_*` rows): Cypress Street Viaduct https://en.wikipedia.org/wiki/Cypress_Street_Viaduct; Acorn (demolition Apr 1962 - May 1965) and the Main Post Office (c. 1962-65, ~12 blocks) from the Urban Renewal Atlas compilation https://urban-renewal-atlas.vercel.app/cities/oakland/west-oakland-cypress (citing R. Self, *American Babylon* 2003; M. Schwarzer, *Hella Town* 2021; FHWA *Public Roads* 1998) and East Bay Yesterday https://eastbayyesterday.com/portraits-of-progress-and-pain/ (Acorn groundbreaking 10 Nov 1967, City Center demolition ceremony 12 Nov 1970); Oak Center https://localwiki.org/oakland/Oak_Center; Peralta Villa https://oaklandwiki.org/MacDermot_Mansion; West Oakland station https://en.wikipedia.org/wiki/West_Oakland_station; Interstate 980 https://en.wikipedia.org/wiki/Interstate_980; Oakland City Center https://en.wikipedia.org/wiki/Oakland_City_Center; Oakland Convention Center / Hyatt Regency site (1981 bid notice) https://pcad.lib.washington.edu/building/24314; Lake Merritt station https://en.wikipedia.org/wiki/Lake_Merritt_station. Rings from Overture centreline crossings, the Mandela Pkwy / I-980 centrelines, and the USPS parcel (Alameda County parcels).
- `data/tables/notable_demolished_region.csv`: demolished buildings outside SF (column `county`): San José City Hall in the plaza (Metro Silicon Valley 1997, https://www.metrosiliconvalley.com/papers/metro/07.03.97/cover/gone2-9727.html), Hotel Montgomery's first site (https://en.wikipedia.org/wiki/Hotel_Montgomery), Donner-Houghton House fire 2007 (https://www.firehouse.com/photo-story/article/10566066/fouralarm-fire-destroys-historic-san-jose-house), San José HRI demolished records (DPR forms, https://gis.sanjoseca.gov/apps/archiveddocs/dpr.html?file=<id>.pdf); confidence per row in `shape_note`.
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

### `overture_airports` — Overture base / infrastructure (airports, runways, taxiways, aprons) — OSM
Airport outlines and runway / taxiway / apron features (OSM centrelines buffered to typical widths) from Overture release 2026-10-21.0 (`region_airports.parquet`), ODbL. Opening years per airport in `data/tables/airports.csv` (source URL per row: Wikipedia articles, county / city airport history pages, militarymuseum.org; rows without a URL are estimates and say so); undated small fields default to 1950 (`estimated`). Airports OSM maps only as a point (San Rafael Airport, Meadowlark Field) get an outline from their own runways / taxiways / aprons. Crissy Field (Presidio, 1921–74; not in Overture): outline and paved-runway pieces traced on the USGS 1:24,000 San Francisco North sheets (1946 photos, 1956, 1968 photorevision; public domain) in `data/manual/airports_extra*.geojson`, dates from P. Freeman, *Abandoned & Little-Known Airfields: San Francisco area* (https://www.airfields-freeman.com/CA/Airfields_CA_SanFran.htm — aerials, charts and directories cited there; facts only) and Wikipedia. San Rafael Airport: Marin History Museum, "The Many Lives of San Rafael's Airport" (https://marinhistory.org/?p=2308) + USGS Novato 1954 / 1968 PR / 1980 PR; Meadowlark Field: USGS Altamont 1953 / 1968 PR. SFO fill phases (`data/manual/fill_zones.csv` `sm_sfo_*`): USGS San Mateo 1:62,500 1899 (1892 survey) and 1943 (1939 photos), 1:24,000 San Francisco South / Montara Mountain / San Mateo / Hunters Point 1946–73; FoundSF *San Francisco Airport* (https://www.foundsf.org/San_Francisco_Airport), SFO Museum *Why "Mills Field"?* (https://millsfield.sfomuseum.org/blog/2018/08/08/why/), Living New Deal (https://livingnewdeal.org/sites/san-francisco-airport-san-francisco-ca/), militarymuseum.org (USACE 1991) — facts only.

### `land_not_before` (manual)
- File: `data/manual/land_not_before.geojson`
- Treasure Island: built 1936–37 on the Yerba Buena Shoals for the 1939 Golden Gate International Exposition — https://en.wikipedia.org/wiki/Treasure_Island,_San_Francisco . Outline from TIGER.

### `fire_1906` (manual research)
- Files: `data/manual/fire_1906_boundary.csv`, `fire_1906_unburned_islands.csv`, `fire_1906_README.md` (sources per vertex)

### Tables
- `data/tables/population.csv`, `eras.csv`, `events.csv`, `landmarks.csv` — every row carries its `source_url`.

### Population by place (`data/tables/population_places.csv`, 2026-11)
Census populations 1850–2020 plus the 1 Jan 2026 estimate for every TIGER 2024 place (80 cities/towns, 82 CDPs) in San Francisco, San Mateo, Santa Clara, Alameda, Contra Costa and Marin, the six counties and their sum. Every row carries its `source_url`. Method, precedence, corrections and caveats are in `data/research/population_places.md`.
- `dof_hist_census` — CA Department of Finance, *Historical Census Populations of Counties and Incorporated Cities in California, 1850–2020* (rev. 2021-08-13), https://dof.ca.gov/media/docs/reports/demographic-reports/2020-1850_STCO_IncCities.xlsx — State of California public data. Primary source for counties and cities. Its Gilroy 1980/1990 cells repeat Los Altos and are corrected from CPH-2.
- `dof_township_place` — Campbell Gibson for CA DOF, *Population Totals by Township and Place for California Counties: 1860 to 1950* (2007), https://dof.ca.gov/media/docs/reports/demographic-reports/Populations-Township_and_Place_1850-1950.zip — counts before incorporation and unincorporated places (1860–1950), transcribed by hand.
- `census_cph2_1990` — U.S. Census Bureau, 1990 CPH-2-6 *Population and Housing Unit Counts: California*, https://www2.census.gov/library/publications/decennial/1990/cph-2/cph-2-06.pdf — public domain. Table 9 (1970/1980/1990 for places incl. CDPs), plus the User Notes (CDP renames, 1980 population of areas incorporated 1980–90).
- `census_gazetteer_2000_2010` — Census 2000 and 2010 gazetteer place files, https://www2.census.gov/geo/docs/maps-data/data/gazetteer/places2k.zip , https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2010_place_list_06.txt — public domain. CDP counts for 2000 and 2010; the 1990 file `places.zip` was used only as a check.
- `dof_census2020_c1` — CA DOF, 2020 Census Table C1 (P.L. 94-171 summary for counties, cities and CDPs), https://dof.ca.gov/media/docs/forecasting/Demographics/2020-census-data/2020Census_C1_Summary_RedistrictingFile.xlsx — 2020 CDP counts.
- `dof_e1_2026` — CA DOF Report E-1, 1 Jan 2025 and 2026 (released 2026-05-01), https://dof.ca.gov/media/docs/forecasting/Demographics/estimates-e1/E-1_2026_InternetVersion.xlsx — latest estimates for cities and counties.
- `census_forstall_1996` — R. L. Forstall, *Population of States and Counties of the United States: 1790 to 1990* (Census Bureau 1996), https://www2.census.gov/library/publications/decennial/1990/population-of-states-and-counties-us-1790-1990/population-of-states-and-counties-of-the-united-states-1790-1990.pdf — public domain. 1852 state-census substitutes for the lost or burned 1850 returns.
- `census_1970_vol1_ca` — 1970 Census of Population Vol. I Part 6 (California), *Number of Inhabitants*, https://www2.census.gov/library/publications/decennial/1970/population-volume-1/1970a_ca1-01.pdf — public domain. 12 1960/1970 values for unincorporated places (Tables 6 and 10), read by hand from the OCR text.
- Pre-census San José: Arbuckle (1985) https://archive.org/details/casjhsj_000308 and Bancroft, *History of California* i, https://archive.org/details/historyofcalifor01banc (as in `data/research/early_region.md`).
- Wikipedia `{{US Census population}}` tables (CC BY-SA; facts only), fallback for 4 values from 1960 (Danville, Alamo, Lafayette, Pleasant Hill), URL per row.

### Landmark reconstructions
- `data/research/landmarks.md`: per landmark dimensions, dates, colours, and Wikimedia Commons reference photos (file page, author, licence). Photos are used as modelling references only and are not redistributed (`data/raw/reference_photos/` is gitignored).
- `data/research/landmarks_southbay.md` (`viewer/src/landmarks/southbay.ts`, `data/tables/landmarks_southbay.csv`): Peninsula, South Bay and Marin models (Apple Park, Stanford, Levi's / SAP Center / PayPal Park, missions, Hangar One, Lick, downtown San José, Marin Civic Center, lighthouses, SLAC, NASA Ames wind tunnels, Shoreline Amphitheatre, Googleplex / Bay View / Charleston East, Valley Fair, Santana Row, Stanford Shopping Center anchors …). Construction years of the Google buildings and malls also from the Santa Clara County roll as joined in `region5_footprint_years` (see `data/research/region_buildings.md`); Bay View facts from Dezeen (2022-05-18). Great America coaster centrelines from the OpenStreetMap API (https://api.openstreetmap.org/api/0.6/map, bbox of the park, 2026-11-08; ODbL), heights from Wikipedia / RCDB / park pages; Mill Valley: enjoymillvalley.com (Mount Carmel), Calisphere / PCAD / Mill Valley Historical Society (library); Pacifica Taco Bell: KQED (2026-04-23), ABC7 (2019) — facts only. Footprints and 3D parts from `overture_region5` (ODbL, © OpenStreetMap contributors); placement checked on Esri World Imagery (viewed only, not stored or redistributed); dates and dimensions from the Wikipedia article per row, plus Stanford Office for Religious Life (Memorial Church history), PCAD / Stanford "quake06" pages (Memorial Arch), IStructE Structural Awards 2018 and Premier Composite Technologies (Steve Jobs Theater), SLAC history pages (klystron gallery) — facts only. Reference photos: Wikimedia Commons (licence per file in the research note), modelling reference only.
- `data/research/landmarks_eastbay.md` (`viewer/src/landmarks/eastbay.ts`, `data/tables/landmarks_eastbay.csv`): East Bay models. Footprints and 3D parts from `overture_region5` (ODbL); Lake Merritt shoreline from `tiger2024` AREAWATER (Alameda County); dimensions from Wikipedia articles (per row), the California Memorial Stadium National Register nomination (2006, https://npgallery.nps.gov/GetAsset/ffa8730b-60f5-430b-9898-bedc4539cfb5 — public domain, US government), the University of California Library Handbook 1918–19 (Project Gutenberg #51874, public domain; Doe Library), the Cal Performances Hearst Greek Theatre technical sheet (https://calperformances.org/wp-content/uploads/venues/tech-specs/Hearst-Greek-Theatre-2324-updated.pdf; facts only). Reference photos: Wikimedia Commons (licence per file in the research note), modelling reference only.
- `data/research/landmarks_ports.md` (`viewer/src/landmarks/ports.ts` + generated `ports-yards.ts`, `data/tables/landmarks_ports.csv`; tools `pipeline/ports_tools/`): industrial waterfront — Port of Oakland container cranes by terminal and generation, container stacks, Matson's 1959 crane at Encinal Terminals, NAS Alameda hangars / control tower / seaplane ramps / carriers, Hunters Point drydocks 2–4 and gantry crane, Kaiser Richmond Yard 3 whirley cranes. Crane history: City of Oakland, Waterfront Ballpark District DEIR — Landmarks Preservation Advisory Board report (2021) with the ESA analysis and the Jacobs *Historical Evaluation of Crane X-422* (2019) https://www.oaklandca.gov/files/assets/city/v/1/public-meetings/landmarks-preservation-advisory-board/2021/er18-016-waterfront-ballpark-district-deir-landmarks-board-report.pdf (facts only); ASME landmark #85 PACECO container crane https://www.asme.org/about-asme/engineering-history/landmarks/85-paceco-container-crane ; Port of Oakland press releases (crane raising 2017–18), Seatrade Maritime (2021 ZPMC cranes), ARCCA Digest (Hanjin terminal), FreightWaves / TT News / Ship Technology (terminal operators), BAAQMD 2005 terminal list, oaklandseaport.com facilities page — facts only. NAS Alameda: National Register nomination, NAS Alameda Historic District (NRIS 12001191, 2013; https://npgallery.nps.gov/AssetDetail/NRIS/12001191 — public domain, US government) and Wikipedia; carriers' home-port years from Wikipedia (USS Enterprise CVN-65, USS Carl Vinson, USS Hancock, USS Oriskany). Hunters Point: NRHP Drydock 4 (12000424) and Commercial Drydock Historic District (12000425) via NARA catalog 123861089 / 123861175; Wikipedia *Hunter's Point crane*; KQED. Richmond: NPS Rosie the Riveter pages (historic shipyards, the whirley crane). Geometry: OpenStreetMap API extracts of the port, Alameda Point, Hunters Point and Point Potrero (https://api.openstreetmap.org/api/0.6/map, 2026-11-08; ODbL, © OpenStreetMap contributors) — wharf faces (coastline), terminal outlines, hangar / tower / drydock / pier / crane outlines, abandoned runways and taxiways; crane positions, container-stack footprints and colours, and the NAS Alameda taxiway / apron pavement traced on Esri World Imagery (Vantor, March 2026; viewed only, tiles not stored in the repo or redistributed). The NAS Alameda airfield polygons (`data/manual/airports_extra.geojson`) are therefore an ODbL derivative. Container heights, earlier cranes' spacing along their berths and carrier berths are estimates (named in each model's facts).
- `known_building_dates_region` rows `nas_alameda_*`: construction years of the NAS Alameda Historic District buildings (NRHP inventory, carried as `start_date` / `old_name:YYYY-1997` on the OSM footprints; Buildings 2, 4, 5 from the nomination's table).

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
- `sonoma_county` — County of Sonoma, Clerk-Recorder-Assessor "Parcels Public" (2026 roll: `BuildingPrimaryYearBuilt`, effective year, stories, units), https://socogis.sonomacounty.ca.gov/map/rest/services/CRAPublic/ParcelsPublic/FeatureServer/0 — public; attribution "County of Sonoma" required when distributing. Construction years of Sonoma County footprints (2026-11 expansion).
- `solano_county` — Solano County "Parcels Public Aumentum" (assessor roll 2026: `yrbuilt`, stories, use), https://services2.arcgis.com/SCn6czzcqKAFwdGU/arcgis/rest/services/Parcels_Public_Aumentum/FeatureServer/0 — public county layer, no licence stated. Construction years of Solano County footprints.
- `napa_county` — Napa County "Public Parcels" (Assessor's Mapping Section / ITS-GIS: `YearBuilt` to 2014, floors, units), https://services1.arcgis.com/Ko5rxt00spOfjMqj/arcgis/rest/services/Napa_County_Public_Parcels/FeatureServer/1 — public county layer, no licence stated. Construction years of Napa County footprints.
- `scotts_valley`, `santa_cruz_parcels` — City of Scotts Valley public parcel viewer (`BldgYearBuilt`; https://services6.arcgis.com/B40wkQx76bHpW2GH/arcgis/rest/services/PUBLIC_Scotts_Valley_Parcel_Viewer_V26_06_15_WFL1/FeatureServer/3) and County of Santa Cruz Assessor parcels (APN / situs / use, no years; https://services1.arcgis.com/jJfZghspGKh8J9Jm/arcgis/rest/services/Assessor_Parcels/FeatureServer/10) — no licence stated. Santa Cruz County publishes no year built: the parcels are the base FEMA / Lightbox years are attached to by APN (`fema_r9_parcel`).
- `fema_r9b_*` — the `fema_r9_lightbox` layers for Sonoma, Napa, Solano and Santa Cruz counties (503,409 building points, same terms and caveats). `ca_ohp_berd` likewise extended with the Sonoma, Napa, Solano and Santa Cruz county CSVs (export 2026-02-02).
- `san_jose_hri` — City of San José Historic Resources Inventory (`TRUEYR`, `ESTIMATEDYR`, demolished / moved flags, architect), https://geo.sanjoseca.gov/server/rest/services/OPN/OPN_OpenDataService/MapServer/406 — City of San José open data (no-warranty disclaimer).
- `ca_ohp_berd` — California Office of Historic Preservation, Built Environment Resource Directory, county CSVs (export 2026-02-02; construction years, NR/CR status codes), https://ohp.parks.ca.gov/?page_id=30338 — State of California (OHP Conditions of Use); located by APN / address.
- `osm_start_date` — OpenStreetMap buildings tagged `start_date` / `construction_date` (Overpass API; download pending — Overpass unreachable 2026-11-08) — ODbL.
- `tiger2024_place` — US Census TIGER/Line 2024 places, California (https://www2.census.gov/geo/tiger/TIGER2024/PLACE/tl_2024_06_place.zip) — public domain; city / CDP names for the coverage report, and the `place` names and `geoid`s of `data/tables/population_places.csv` (places assigned to counties by interior point in `tl_2024_us_county`).
- `san_mateo_county_footprints` — County of San Mateo "Building Footprints" (229,298; `BLDGHEIGHT` feet, `BASEELEV`), https://services.arcgis.com/yq3FgOI44hYHAFVZ/arcgis/rest/services/Building_Footprints/FeatureServer/0 — no licence stated; height source for San Mateo.
- `marin_county_footprints` — Marin County "Building Footprints" (113,271; outlines from the 2004 Vargis orthophoto, `SourceDateYear`; height fields empty), https://services6.arcgis.com/T8eS7sop5hLmgRRH/arcgis/rest/services/Building_Footprints/FeatureServer/0 — no licence stated; "stood by 2004" constraint.
- `loc_sanborn_region` — Library of Congress Sanborn Fire Insurance Maps for the five counties (362 items, ids per city in the research note; public domain, "Library of Congress, Geography and Map Division, Sanborn Maps Collection") — listed only, not traced.

### `known_building_dates_region` — researched construction years of institutional / landmark buildings (2026-11 audit)
`data/tables/known_building_dates_region.csv` (371 rows, a source URL per row): Stanford University 2018 General Use Permit application, historic-resources inventory (`SU_2018GUP_App_Vol4_pt2.pdf`) and Stanford news / Stanford Daily / Wikipedia for post-1975 buildings; UC Berkeley Disability Access & Compliance building list (year built per building); Santa Clara University facilities "Building Information" pages (year constructed); Wikipedia (list of tallest buildings in Oakland, individual building articles); city / county / airport history pages. Facts only (years), used to override assessor / vendor years per footprint. Overture `land_use` (university, college, school, hospital, military outlines; ODbL) delimits campuses for `region_buildings.campus_impute`.

### `usgs_htmc` — USGS Historical Topographic Map Collection (farmsteads, orchards, vineyards)
- URL: https://www.usgs.gov/programs/national-geospatial-program/historical-topographic-maps-preserving-past ; discovery through the TNM Access API https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Historical%20Topographic%20Maps ; GeoPDFs from https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/ (FGDC metadata per scan: survey / photo / imprint years).
- Licence: public domain (U.S. Geological Survey; "Acknowledgment of the U.S. Geological Survey is expected for products derived from these data").
- Use: building symbols of the first 1:62,500 surveys (1885–1916) and of the 1939–1956 sheets → `data/manual/farmsteads/topo_farmsteads.geojson` (farmstead positions), `topo_towns.geojson`, `coverage.geojson`; green orchard / vineyard overprint of the 1939–1956 sheets → `topo_orchards.geojson`. Sheets used (quad, years, URL) are listed in `data/manual/farmsteads/README.md` / `coverage.geojson`. Built by `pipeline/topo_farmsteads.py`; raw PDFs in `data/raw/topo/` are deleted after extraction.
- Also used there: NOAA NADCON grid `us_noaa_conus.tif` (PROJ CDN https://cdn.proj.org/, open licence) for NAD27 → WGS84, and Overture/OSM road centrelines (`overture_transportation`, ODbL) only to measure the local offset of the early surveys; no OSM geometry is copied, but the early-sheet positions carry that correction (an affine shift per sheet), so treat the outputs as OSM-influenced (ODbL attribution) if in doubt.

### Landscape history (`data/manual/landscape/`, 2026-11): dunes, water, agriculture
Built by `pipeline/landscape.py`, `landscape_water.py`, `landscape_broek.py`, `landscape_agriculture.py`; raw inputs in `data/raw/landscape/`. See `data/manual/landscape/README.md`.

#### `broek_1932` — J.O.M. Broek, *The Santa Clara Valley, California: a study in landscape changes* (Utrecht: Oosthoek, 1932)
- Utrecht University Repository, open access: https://dspace.library.uu.nl/handle/1874/302720 (PDF https://objects.library.uu.nl/download/1874-302720/pdf). Published 1932 (Netherlands); facts and a traced generalisation of its map are used, the scan is not redistributed.
- Use: Plate II Map III "Schematic map of landscape types of the Santa Clara Valley 1931" traced (hatch-texture classification, affine georeference on 15 towns, RMS ~0.7 km) → `broek_1931_landscape_types.geojson` and the `broek_1931` layer of `agriculture.geojson`; text (wheat / orchard / vineyard / dairy history, county grain production 1859–1929, orchard acreage 1890 / 1930) → district eras and the README findings.

#### `usgs_of98_354` — Bonilla, M.G., 1998, *Preliminary geologic map of the San Francisco South 7.5′ quadrangle and part of the Hunters Point 7.5′ quadrangle*, USGS Open-File Report 98-354
- https://pubs.usgs.gov/of/1998/of98-354/ (`sfs_data.tar.gz`, ARC export; compressed E00 decompressed with `e00conv` from the Debian `e00compr` package). Public domain (USGS).
- Use: unit Qd (dune sand) and Qc (Colma Formation) → dunes of southern San Francisco, Lake Merced, Fort Funston and Daly City (`dunes.geojson`).

#### `usgs_of2006_1037` — Witter, R.C., Knudsen, K.L., Sowers, J.M., Wentworth, C.M., Koehler, R.D., Randolph, C.E., 2006, *Maps of Quaternary deposits and liquefaction susceptibility in the central San Francisco Bay region*, USGS Open-File Report 2006-1037
- https://pubs.usgs.gov/of/2006/1037/ (`of06-1037_4b.shp.zip`, NAD27 geographic → WGS84 via NADCON). Public domain (USGS).
- Use: dune sand (Qds/Qhds; Merritt Sand of Alameda / Oakland / Bay Farm Island, coast dunes) → `dunes.geojson`; Holocene fan / levee / terrace, basin and Pleistocene fan units → the valley-floor soil classes ("fan", "basin", "upper_fan") on which `agriculture.geojson` paints the district eras.

#### `usgs_of00_444` — Knudsen, K.L., Sowers, J.M., Witter, R.C., Wentworth, C.M., Helley, E.J., 2000, *Preliminary maps of Quaternary deposits and liquefaction susceptibility, nine-county San Francisco Bay region*, USGS Open-File Report 00-444
- https://pubs.usgs.gov/of/2000/of00-444/ (`of00-444_4c.tar.gz`, shapefiles, NAD27). Public domain (USGS).
- Use: same as OFR 2006-1037 where that map does not reach (Delta / Antioch–Oakley–Brentwood sand sheet, Livermore east, south Santa Clara Valley, West Marin).

#### `overture_water` — Overture Maps base theme, water (OpenStreetMap)
- `s3://overturemaps-us-west-2/release/2026-10-21.0/theme=base/type=water` (region bbox, polygons) — ODbL 1.0, © OpenStreetMap contributors, Overture Maps Foundation.
- Use: lake / reservoir outlines (named) and today's water for the dredged-estuary rows of `water_history.csv` (so that file is OSM-derived: ODbL attribution).

#### `sbsprp_salt_history`, `bcdc_salt_ponds_2005` — salt-pond histories
- USFWS / South Bay Salt Pond Restoration Project, *Appendix E: Identification and Evaluation of the South San Francisco Bay Solar Salt Ponds* (https://www.southbayrestoration.org/documents/permit-related/Historic%20Salt%20AppendixE.pdf), citing Ver Planck (1958) *Salt in California* (CDMG Bulletin 175), Sandoval (1988), Shoup & Baker (2007).
- BCDC, *Staff Report: Salt Ponds*, October 2005 (http://www.bcdc.ca.gov/wp-content/uploads/sites/354/2023/09/Salt-Ponds-PDF.pdf).
- Use: dates of the salt-pond complexes in `water_history.csv` (facts only).

#### `sbsprp_salt_context_2005`, `sbsprp_phase2_cultural_2016`, `usgs_htmc` South Bay sheets — South Bay salt-pond phases (2026-11)
- EDAW (L. Watt), 2005, *South Bay Salt Pond Restoration Project Historic Context Report* (Appendix D; scanned text OCR'd), https://www.southbayrestoration.org/documents/permit-related/Historic%20Salt%20AppendixD.pdf — chronology after Ver Planck 1958 (*Salt in California*, CDMG Bulletin 175), Sandoval 1988 and the Leslie Salt / Dumbarton Land & Improvement Co. archive; reproduces the USC&GS 1907 chart of San Francisco Bay, Thompson & West 1878 atlas plates, Claire Lopez's 1971 maps (reclamation districts, DL&I Co. levees 1907–08, Eden Landing works 1860–1910) and Ver Planck's 1958 maps.
- SBSPRP Phase 2 Final EIS/R (2016), §3.7 Cultural Resources, https://www.southbayrestoration.org/planning/phase2/documents/AR-FEISR/3.7_Cultural%20Resources_w%20Figs.pdf (Alviso, Drawbridge, Ravenswood histories; pond S5 pumphouse 1943–48).
- USGS Historical Topographic Map Collection (`usgs_htmc`, public domain): Haywards 1899 (survey 1896), Hayward 1915, 1942 (1939 photos); Palo Alto 1897 / 1899 (survey 1895), 1941 (survey 1939), 1943 (1940 photos); San Jose 1897 / 1899 (survey 1895), 1943 (1939 photos); Pleasanton 1906; 1:24,000 Newark 1947 / 1959, Redwood Point 1948 / 1959, Mountain View, Milpitas, Palo Alto, Niles 1953 (1948 photos), Milpitas, Mountain View, Palo Alto 1961, Hayward 1959 — read on screen with a lon/lat grid (scratch renders, not stored).
- Licences: the reports are public agency documents used for facts; maps public domain.
- Use: `data/manual/landscape/south_bay_salt_phases.geojson` → `sb_*` rows of `water_history.csv` (zone rings drawn on the sheets, clipped to the SFEI c.1998 pond / diked extent); `README_south_bay_baylands.md`.

#### Other dated facts (per row / feature in the files)
- Lake Merritt, Oakland estuary, Tidal Canal: Wikipedia "Lake Merritt", "Oakland Estuary"; oaklandgeology.com (tidal canal history); HMdb Tidal Canal marker; Alameda Post. Reservoir / lake dam years: Wikipedia articles per reservoir (URL per row). Farm-district eras: Broek 1932; Hayward Area Historical Society (agricultural history); Contra Costa County Historical Society; East Contra Costa Historical Society (Brentwood); NPS Point Reyes ranching history; Pleasanton Weekly (hops); Wikipedia articles cited per feature.

### `historic_rail` — historic railways, interurbans and rail piers (2026-11)
- File: `data/manual/historic_rail.geojson` (built by `pipeline/historic_rail_trace.py` from `data/manual/historic_rail_spec.py`; method, superseded `routes.csv` ids and gaps in `data/research/historic_rail.md`).
- Geometry: OpenStreetMap railway ways incl. abandoned / disused grades (Overture `rail.parquet` 2026-10-21.0; BBBike San Francisco extract `data/raw/osm_bbbike/`; Overpass API extracts via https://maps.mail.ru/osm/tools/overpass/api/interpreter, `data/raw/historic_rail/`) — ODbL 1.0, © OpenStreetMap contributors (the output is a derived database: ODbL); Overture/OSM road centrelines for street running; USGS Historical Topographic Map Collection GeoPDFs (`usgs_htmc`, public domain): San Francisco 1899/1915, San Mateo 1899/1915, Concord 1897/1915, Haywards 1899, Tamalpais 1897, Petaluma 1914, Point Reyes 1918, Pleasanton 1906 (traced line work, registered with NADCON and the local road alignment of `topo_farmsteads.py`).
- Dates: Wikipedia articles cited per segment (Oakland Long Wharf, Alameda Mole, Key System Mole, San Francisco and Alameda Railroad, Alameda Terminal, South Pacific Coast Railroad, Ocean Shore Railroad, North Pacific Coast Railroad, Northwestern Pacific Railroad, Sacramento Northern Railway, East Bay Electric Lines, Ocean View Branch, Peninsular Railway (California), Dumbarton Rail Bridge, Niles Canyon Railway, Western Pacific Railroad); Alameda Post, "South Pacific Coast Narrow-Gauge Railroad Once Traversed Alameda" (https://alamedapost.com/history/south-pacific-coast-narrow-gauge-railroad-once-traversed-alameda/); NPS Point Reyes "Then & Now: Tomales Bay Communities" (https://www.nps.gov/pore/learn/photosmultimedia/photogallery_thenandnow_tomalesbay.htm); San Anselmo Historical Museum (https://sananselmohistory.org/articles/trains-in-san-anselmo/); Saratoga Historical Foundation (https://saratogahistory.com/History/PIrailroad.htm); Marin railroad timeline (https://legacy.sfgenealogy.org/marin/history/rrtimeline.htm, via search summary — the page is behind a bot check). Facts only.

### `vanished_sites` — vanished large sites: racetracks, campuses, plants, amusement parks (2026-11)
- Files: `data/manual/vanished_sites/sites.geojson` (ground parts per period), `buildings.geojson` (vanished footprints), `road_segments.csv` (Overture road segments on those sites with not-before years); method, per-site sources and confidence in `data/manual/vanished_sites/README.md`; tools in `data/manual/vanished_sites/tools/`.
- Maps: USGS Historical Topographic Map Collection 1:24,000 GeoTIFFs (public domain; TNM Access API, https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/): San Mateo 1947, 1956 (+1968, 1973, 1980 photorevisions), 1993, 1997; Cupertino 1961 (+1968, 1973, 1979 PR), 1991; San Francisco South 1947, 1956; Milpitas 1961 (+1968, 1973, 1980 PR); San Jose East 1961 (1973 PR); Oakland West 1949, 1959, 1993; 1:62,500 San Francisco (1899 edition, 1914 imprint). NAD27 → WGS84 with the NOAA NADCON grid.
- Orthophoto: Esri World Imagery Wayback, release 2014-02-20 (https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/10/{level}/{row}/{col}; source per its metadata service: Microsoft UltraCam, 26 Oct 2010) — viewed for tracing only (HP Cupertino roofs, Bay Meadows parcel), no imagery redistributed.
- Today's grounds of Apple Park: OpenStreetMap via Overture 2026-10-21.0 (base land / land_use / water, transportation segments) — ODbL 1.0, © OpenStreetMap contributors.
- Facts (dates, sizes): Wikipedia "Bay Meadows Racetrack", "Bay Meadows (neighborhood)", "Apple Park", "Tanforan Racetrack", "Great Mall of the Bay Area", "Marine World/Africa USA", "Frontier Village"; PCAD (https://pcad.lib.washington.edu/building/13205); Daily Racing Form, 1 Oct 2008 (https://www.drf.com/news/piece-history-about-crumble); GlobeSt, 23 Apr 2008 (https://globest.com/2008/04/23/83-acre-race-track-redevelopment-gains-city-ok); HP Computer Museum (https://www.hpmuseum.net/divisions.php?did=2); Densho Encyclopedia "Tanforan (detention facility)"; Cinema Treasures "Frontier Auto Movie" (https://www.cinematreasures.org/theaters/70447); Wikipedia "Fleet and Industrial Supply Center, Oakland"; Emeryville Historical Society, "Horse Racing in Emeryville" (https://emeryvillehistorical.org/centennial-essays/oakland-trotting-park/).
- Second batch (2026-11: pre-war resorts, amusement parks, ball parks, race tracks, Russell City, a drive-in):
  - Sanborn Fire Insurance Maps, Library of Congress (public domain; IIIF images at 25 %, item JSON `https://www.loc.gov/item/<id>/?fo=json`): Oakland 1911-12 vol. 3 (`sanborn00727_007`: sheet 293 Idora Park; 317, 321, 323-325 Emeryville race track and Shell Mound Park), Oakland 1911-Oct 1950 vol. 3 (`sanborn00727_017`: 293, 317 Oaks Park), Oakland 1911-Nov 1950 vol. 2 (`sanborn00727_016`: 150, 151 downtown 9th-11th St), Alameda 1897 (`sanborn00374_001`: 11, 12, 15) and 1948 (`sanborn00374_002`: 11, 12, 15). Each sheet fitted to today's parcel blocks (Alameda County parcels 2021) or street crossings (Overture) by an affine / similarity transform.
  - USGS HTMC (as above): San Leandro 1:24k 1947, 1959 (+1968 PR); Hayward 1:62,500 1915 (1914 survey), 1942 (1939 photos); Oakland West 1:24k 1959 (1973, 1980 PR); San Francisco South 1:24k 1956, 1993; San Francisco 1:62,500 1895 (1894 survey), 1915 (1932 imprint); San Mateo 1:62,500 1899 (1905 imprint).
  - Facts: Wikipedia "Idora Park", "Neptune Beach (California)", "List of baseball parks in Oakland, California", "Russell City, California", "Ingleside Terraces, San Francisco", "Chinatown, Oakland, California"; Oakland LocalWiki "Idora Park", "Pacific Renaissance Plaza", "East Bay Municipal Utility District"; Alameda Post, "West End once served as magnet for bathers" parts 1-2 and "Neptune Beach: the Coney Island of the West" (https://alamedapost.com/history/); EBRPD Crab Cove digital tour (c.1930 aerial); Emeryville Historical Society "Shell Mound Park" (https://emeryvillehistorical.org/centennial-essays/shell-mound-park/); Oakland Tribune 7 Aug 1949 (via blog repost); OpenSFHistory / Richmond SF Blog (Bay District track); Cinema Treasures "Geneva 4 Drive-In" (https://cinematreasures.org/theaters/4986), "T & D Theatre" (3548); PCAD 14588 (T & D Theatre) and 24314 (Oakland Marriott, citing SF Examiner 22 Nov 1981); CEQAnet SCH 1981120809 (Trans Pacific Center phase II Draft EIR, 1982); GlobeSt 30 Aug 2000 (Franklin 88 land sale, via search snippet).
  - Photographs viewed for placement only (not redistributed): 1930s aerial of Neptune Beach (Alameda Museum, via Alameda Post), c.1930 aerial (Alameda Historical Society, via EBRPD).

### `ohm` — OpenHistoricalMap (2026-11)
- Data: OpenHistoricalMap contributors, **CC0 1.0** (https://www.openhistoricalmap.org/copyright); read through the OHM Overpass API (https://overpass-api.openhistoricalmap.org/api/interpreter; bbox queries in four chunks over the core Bay Area, 2026-11-09; raw answers in `data/raw/ohm/`, gitignored). Tool: `pipeline/ohm_import.py`. Every exported feature links its OHM way and the source OHM cites; OHM's placeholder dates are replaced by evidence (see the READMEs).
- Files: `data/manual/sanborn/sf_goldrush_{1851,1852,1887}.geojson` + `sf_goldrush_coverage.geojson` (`README_goldrush.md`), and `data/manual/ohm/` (`README.md`): Stanford known dates / bounds / demolished buildings, railways (`historic_rail_ohm.geojson`, `routes_ohm.csv`), demolished buildings of the region (`region_demolished_ohm.geojson`, `notable_demolished_ohm.csv`), Camp Fremont (`vanished_sites_ohm.geojson`, `vanished_buildings_ohm.geojson`, `camp_fremont_lines_ohm.geojson`), SF (`known_dates_ohm_sf.csv`, `notable_sf_ohm.csv`, `sf_wharves_1851_ohm.geojson`, `sf_fires_1851.geojson`).
- Source maps the OHM volunteers traced (cited on the ways): U.S. Coast Survey, *City of San Francisco and its Vicinity* (Cutts / Rodgers, survey to April 1852, publ. 1853), David Rumsey Map Collection 3463.000 (https://www.davidrumsey.com/luna/servlet/detail/RUMSEY~8~1~2210~180022), also via Pastmapper's 1853 layer (http://www.pastmapper.com/map/1853/); *Map of the Burnt District of San Francisco* (fire of 4 May 1851), The Huntington Library (https://hdl.huntington.org/digital/collection/p9539coll1/id/23520); Sanborn Map Co., San Francisco 1887 vol. 1, Library of Congress (https://www.loc.gov/resource/g4364sm.g4364sm_g00813188701/), georeferenced on oldinsurancemaps.net (layers 70120, 70147, 70181, 70185, 70189, 70191, 70216); *Campus of Leland Stanford Junior University, 1962* (Stanford, http://purl.stanford.edu/qr683hn3144) with the 1934 campus map; 1917 Camp Fremont map (Stanford archive, https://purl.stanford.edu/fb297sh0179); USGS historical topographic sheets (Tamalpais 1897, Palo Alto 1897 / 1940s, San Francisco 1895, Concord 1897, Karquines 1898, San Jose West 1980) and Esri World Imagery Wayback for track removals; city and newspaper sources per feature (San Jose Mercury News / Herald, City of San José historic resources inventory and context statements, NPS, NPGallery, SFPL branch histories, Stanford Daily, PCAD, pacificng.com, santacruztrains.com, chicagorailfan.com).
- Facts used to date the gold-rush tracings: the fire of 22 June 1851 bounded by Powell, Sansome, Clay and Broadway (SFFD Guardians of the City, https://guardiansofthecity.org/sffd/fires/great_fires/june_22_1851.html); fire of 3-4 May 1851 (Wikipedia "San Francisco Fire of 1851"); Vogdes p. 253 via the Rumsey record (survey completed April 1852).

## Sources checked but not yet usable from the build environment
- SFEI EcoAtlas web services (https://www.sfei.org/) — behind a bot check; the poster PDF was supplied by hand and the GIS compilation downloads directly.
- OpenHistoricalMap (https://www.openhistoricalmap.org/) — the website / main API are behind a bot check; the Overpass API works (see `ohm` above).
- Geofabrik / Overpass OSM extracts — network timeouts; Overture covers the OSM data needed so far.
- Census API (ACS B25034) — now requires a (free) key; needed for Phase 5 imputation.
- Alameda County Assessor property characteristics (sold, not on the open-data portal), Marin County Assessor roll (per-parcel lookup only; GIS server behind Cloudflare), San Mateo County roll characteristics (not published) — public copies / FEMA-Lightbox used instead (see `data/research/region_buildings.md`).

### `industrial_sites` — military and industrial sites audit (2026-11)
- Files: `data/manual/industrial_sites/sites.geojson` (ground parts per period: refineries, quarries and their growth stages, landfills, shipyards, ports, rail yards, bases), `building_dates.csv` (per-site rules for today's footprints), `known_dates_industrial.csv` (per-footprint years in the `known_building_dates_region.csv` format: researched buildings + footprints dated by the USGS editions that first draw them), `traced/` (tint-extracted pit outlines, audit tables); method, per-site sources / confidence and the list of errors found in `data/manual/industrial_sites/README.md`; tools in `data/manual/industrial_sites/tools/` (built on the vanished-sites renderer).
- Maps: USGS Historical Topographic Map Collection GeoTIFFs (`usgs_htmc`; public domain; TNM Access API; FGDC metadata for photo / photorevision / imprint years; NAD27 → WGS84 with the NOAA NADCON grid). 1:24,000: San Quentin 1948/1959 (+1973, 1980 PR)/1993/1995, Richmond 1947/1959 (+PR)/1993, Mare Island 1951/1959 (+PR), Benicia 1950/1959 (+PR), Port Chicago 1951/1959/1968, Vine Hill 1959 (1980 PR), Oakland West 1949/1959 (+PR)/1993, San Francisco North 1947/1956, Cupertino 1953/1961 (+1968, 1973, 1980 PR)/1991, Mindego Hill 1961 (+PR)/1991, Livermore, Dublin, Mountain View, Milpitas, Niles, La Costa Valley and others per site (the sheet that first draws each footprint is cited per row of `known_dates_industrial.csv`); 1:62,500: San Francisco 1895/1899 (reprints 1900–1914)/1915 (reprints 1929–1947), Karquines 1898/1901, Carquinez Strait 1896/1940, Mare Island 1916, Palo Alto 1897/1899 (reprints)/1941/1943/1948/1961, Concord, Haywards, Pleasanton, San Mateo, Tamalpais as covering.
- Outlines: OpenStreetMap land_use (industrial / works / military / quarry / landfill / railway / park) via Overture base theme 2026-10-21.0 — ODbL 1.0, © OpenStreetMap contributors (the GeoJSON is a derived database: ODbL); today's building footprints (`overture`, region5) and the built live-map years (`region_building_points`, `region5_footprint_years`, `sf_buildings`) for the audit.
- Facts (dates; cited per site in the README and per feature): Wikipedia articles (Chevron Richmond Refinery, Marathon Martinez Renewable Fuels, Associated Oil Company, Rodeo San Francisco Refinery, C&H Sugar, Hercules California, Point Pinole Regional Shoreline, Concord Naval Weapons Station, Richmond Shipyards, Ford Assembly Building (Richmond), Winehaven, Oakland Army Base, Oakland Long Wharf, Moore Dry Dock Company, Alameda Works Shipyard, Coast Guard Island, Camp Parks, Lawrence Livermore National Laboratory, Sandia National Laboratories, Tesla Fremont Factory, Pier 70, Potrero Generating Station, Bayshore Roundhouse, Permanente Quarry, Lockheed Martin Space, Joshua Hendy Iron Works, Marinship); CLUI Land Use Database (Martinez, Rodeo, Golden Eagle refineries); California Energy Commission, California oil refinery history; Contra Costa County Historical Society, "Oleum stands for petroleum"; OAC, Guide to the Selby Smelting & Lead Company Records; NPS Rosie the Riveter NHP, historic Richmond shipyards; City of Oakland, Waterfront Ballpark District DEIR LPAB report (Port of Oakland terminal history); Regional Water Board, Lehigh Permanente WDR 2018 (limestone mined since c.1903); Alameda County LAVQAR Specific Plan Draft EIR 1979 and SME 1970 (Kaiser Radum plant 1931); Marin Magazine / SPRC (San Rafael Rock Quarry, hard-rock quarrying from 1929); Republic Services (Newby Island 1938 / 1956). Facts only.

### `region_extents` — dated built-up extents of the region's older towns (2026-11)
- Files: `data/manual/region_extents/<town>_<year>.geojson` (built-up area per snapshot), `<town>_<year>_partial.geojson` (partly built blocks), `coverage.geojson` (area each snapshot read), `check/<town>.png`; method, maps, per-snapshot validation and limits in `data/manual/region_extents/README.md`; tool `data/manual/region_extents/tools/extents.py`.
- Maps: USGS Historical Topographic Map Collection GeoPDFs (`usgs_htmc`; public domain; TNM Access API https://tnmaccess.nationalmap.gov/api/v1/products, scans from https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/; FGDC metadata for survey / photo years; culture-revision years read off the collars of the 1915 editions; NAD27 → WGS84 with the NOAA NADCON grid `us_noaa_conus.tif`, PROJ CDN, open licence). 1:62,500: San Francisco 1895 (survey 1892-94), 1915 (culture revised 1914); Concord 1897 (survey 1893-94), 1915 (culture revised in part 1913-14), 1942 (1939 photos); Haywards 1899 (survey 1896); Hayward 1915 (survey 1914), 1942 (1939 photos); San Jose 1889 (survey 1885; 1939 reprint), 1897 (survey 1895), 1943 (1939 photos); Palo Alto 1899 (survey 1895), 1943 (1940 photos); San Mateo 1896 (survey 1892), 1915 (culture revised in part 1914), 1943 (1939 photos); Tamalpais 1897 (survey 1895), 1941 (1939 photos); Karquines 1898 (survey 1896); Carquinez Strait 1940 (1940 photos; Carquinez 1942, 1937 photos, checked and not used: streets only). 1:24,000: Oakland West 1949, Oakland East 1947, Richmond 1947, Briones Valley 1947, San Leandro 1947, Hayward 1947, Newark 1947, San Mateo 1947 (1946 photos); San Quentin 1948 (1947); San Jose West / East, Milpitas, Palo Alto, Mountain View, Woodside 1953 (1948 photos); Redwood Point 1948; Benicia 1950, Port Chicago 1951 (1948 photos); San Rafael 1954 (1952 photos). Each sheet's GeoPDF link is in the README maps table and in the snapshot's `source_url`.
- Blocks and alignment: Overture transportation segments 2026-10-21.0 (street centrelines; OpenStreetMap, ODbL 1.0, © OpenStreetMap contributors) polygonised into today's blocks and used to measure each sheet's offset (an affine shift per sheet); Overture rail and `data/manual/historic_rail.geojson` to ignore railway ink. The extents follow today's OSM-derived blocks, so treat them as OSM-influenced (ODbL attribution) if in doubt. Clipped to TIGER 2024 places and `data/interim/land_modern.fgb`.
- Checks only: `data/interim/region_building_points.parquet` (today's buildings with years), the Sanborn tracings in `data/manual/sanborn/`.
- Checked, not usable for a built-up extent: Thompson & West, *Official and historical atlas map of Alameda County* (1878), map 16 (David Rumsey Map Collection, https://www.davidrumsey.com/luna/servlet/detail/RUMSEY~8~1~21416~630030) — subdivisions and owners, no houses.

### `ohlone_villages` — contact-era Ohlone, Bay Miwok and Coast Miwok villages (2026-11)
- Files: `data/manual/ohlone/villages.csv` (35 village rows in the `early_region.csv` format, c.1769–1810; position precision, local tribe, quotations and end-year basis in each `shape_note`) + `data/manual/ohlone/README.md` (method, duplicates / corrections of `early_region` rows, sensitivity note, gaps).
- Ethnohistory (facts: local-tribe territories, populations, years villages emptied): Milliken, Shoup & Ortiz, *Ohlone/Costanoan Indians of the San Francisco Peninsula and their Neighbors* (NPS GGNRA 2009), https://npshistory.com/publications/goga/ohlone-indians.pdf; Milliken, *Ethnohistory and Ethnogeography of the Coast Miwok and their Neighbors, 1783–1840* (NPS GGNRA 2009), https://www.nps.gov/goga/learn/historyculture/upload/2009-Final-Coast-Miwok-Report.pdf; Milliken et al., *Contact-Period Native California Community Distribution Model* (Far Western 2010) Table B-1, https://wiki.farwestern.com/index.php/Volume_1_Appendix_B; Arellano, Leventhal et al., ch. 3 of CARD Publication 20 (2014; quotes Milliken 1991/1995/2008, Fages 1770/1772, King 1994 / Hylkema 1995), https://muwekma.org/pdf/muwekma-ethnohistory-sfpuc-ala-565.pdf.
- Explorers' diaries with H. E. Bolton's route identifications (public domain scans, Internet Archive): Crespí's 1772 diary in Palóu, *Historical Memoirs of New California* ii (1926), https://archive.org/details/historicalmemoir0000fray; Anza's and Font's 1776 diaries in *Anza's California Expeditions* iii–iv (1930), https://archive.org/details/anzascaliforniae03bolt, https://archive.org/details/anzascaliforniae04bolt.
- Positions are place-level only (creek / camp / town named by the sources, ~1–4 km); no archaeological site records (CHRIS / NWIC) were used; Nelson's 1909 shellmound map was not used for points. Consult the Ohlone, Bay Miwok and Coast Miwok tribes before public site labels.

### Audit of 2026-11 — sources added
- **`fhwa_nbi`** — FHWA National Bridge Inventory 2024 (public domain, https://www.fhwa.dot.gov/bridge/nbi/ascii.cfm): year built of grade separations, used to place Caltrans postmile limits and to bracket the opening year of freeway stretches in `data/manual/routes.csv` (rows that rest on it alone say ESTIMATED).
- **`cahighways`**, **`kurumi`** — California Highways (https://www.cahighways.org/) route pages and Kurumi's 3-digit Interstates (https://www.kurumi.com/roads/3di/): opening dates of freeway stretches (facts only, URL per row).
- **`usgs_htmc`** — USGS Historical Topographic Map Collection GeoTIFFs (public domain, https://www.usgs.gov/programs/national-geospatial-program/historical-topographic-maps-preserving-past): every 1:24,000 edition of 16 bay quadrangles (photo years 1946–97) classed land / wet per terrain cell, and the 1:62,500 sheets surveyed 1894–97, date the `tp_*` and `ot_*` rows of `data/manual/fill_zones.csv` (edition per row).
- **`ca_ohp_berd` for San Francisco** — the San Francisco county export of the OHP Built Environment Resource Directory (2026-02-02, see `ca_ohp_berd` above) reduced to `data/tables/ohp_sf_years.csv` (3,670 parcels whose surveyed rows agree on one construction year); used only where the assessor year is a placeholder, missing or impossible.
- **`noehill`** — NoeHill in San Francisco, San Francisco Landmarks (https://noehill.com/sf/landmarks/): "Built" years of designated landmarks (facts only; URL per row in `known_building_dates.csv`).
- **`golflink`**, **`wikidata`** — GolfLink course directory ("Year Opened", https://www.golflink.com/golf-courses/) and Wikidata inception dates (CC0): opening years in `data/tables/region_green_dates.csv` (URL and confidence per row).
- **US Census / California DOF** — DOF "Historical Census Populations of Counties and Incorporated Cities, 1850–2020" and E-1 estimates: every figure of `population_places.csv` re-checked against them.


### Ten-county extent (2026-11) — sources added
- **`usace_nid`** — National Inventory of Dams, US Army Corps of Engineers (public domain, https://nid.sec.usace.army.mil/): year each dam was completed, joined by distance to today's lakes and reservoirs; dates the water bodies of `data/manual/landscape/water_history.csv` (Lake Berryessa 1957, Lake Sonoma 1983, …). Record id per row.
- **`cpad`** — California Protected Areas Database 2024a, GreenInfo Network (https://www.calands.org/cpad/; free to use with attribution): "year established" of park and reserve units, used in `data/tables/region_green_dates.csv` only where no agency page or article states the year, and then marked `estimated` (CPAD often records the land purchase; placeholder years were not used).
- **`faa_nasr`** — FAA National Airspace System Resources airport data (public domain, https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/): activation dates of small airfields in `data/tables/airports.csv`, marked estimated (the date the field entered the federal records, not necessarily its first use).
- **County rolls of the new counties** — see `sonoma_county`, `solano_county`, `napa_county`, `scotts_valley`, `santa_cruz_parcels` and `fema_r9b_*` above and `data/research/region_buildings.md`.
- **Place names, census series, farm districts** — sources per row in `data/tables/places.csv`, `population_places.csv` (DOF historical census table, Census CPH-2 / gazetteer, Gibson's early counts; `data/research/population_places.md`) and per feature in `data/manual/landscape/agriculture.geojson` (README there); OSM vineyard / orchard outlines (ODbL) via Overture `land_use`.
- **Freeways, bridges and railways of the new counties** — `fhwa_nbi` (year built of each section's own structures, 2024 and 2008 files), Wikipedia route / railroad articles and Gribblenation, URL per row in `data/manual/routes.csv`; geometry is the Overture line of each road / track.

## Ship-quality pass for the new counties (2026-11) — sources added

<!-- villages -->
### Contact-era Native villages and first colonial places of the ten-county extension (2026-11)

`data/manual/ohlone/villages.csv` (40 new rows; README there), `data/tables/early_region.csv` (16 new rows, 2 corrected; `data/research/early_region.md`).

| Source | URL | Licence | Use |
|---|---|---|---|
| S. A. Barrett, *The Ethno-geography of the Pomo and Neighboring Indians*, UC Publications in American Archaeology and Ethnology 6(1), 1908 | https://archive.org/details/ethnogeographyp00barrgoog | public domain | Village places (bearing and distance from the towns of 1903-06) of the Coast Miwok of Sonoma County, Southern Pomo, Kashaya, Wappo and southern Patwin; house types (pp. 25, 124). Facts only, re-stated; a village is entered only where Milliken ties it to a community of the contact years. |
| R. Milliken, *Ethnohistory and Ethnogeography of the Coast Miwok and their Neighbors, 1783-1840* (NPS / GGNRA 2009), ch. 10-12 | https://www.nps.gov/goga/learn/historyculture/upload/2009-Final-Coast-Miwok-Report.pdf | US government report | Which Barrett villages are the communities of the mission registers; baptism years (= end years) for the Petaluma, Sonoma, Bodega Bay, Bloomfield / Cotati, Pomo and Wappo communities. Already listed for the core. |
| R. Milliken, L. Shoup, B. Ortiz, *Ohlone/Costanoan Indians of the San Francisco Peninsula and their Neighbors* (NPS / GGNRA 2009), ch. 5-7 | https://npshistory.com/publications/goga/ohlone-indians.pdf | US government report | Patwin (Suisun, Napa), Wappo, Delta, Awaswas and Mutsun-area migrations to the missions (end years). Already listed for the core. |
| Fr. J. Crespi (1769, 1772) and Fr. F. Palou (1774) in Palou, *Historical Memoirs of New California*, ed. H. E. Bolton, vols ii-iii (1926) | https://archive.org/details/historicalmemoir0000fray , https://archive.org/details/historicalmemoir0003herb | public domain | Villages on the Pajaro River, San Lorenzo River, Soquel-Aptos, Scott Creek, at Gilroy and San Felipe Lake; Bolton's route notes for the positions. Vol. iii is new. |
| J. B. de Anza and P. Font (1776) in H. E. Bolton, *Anza's California Expeditions* iii-iv (1930) | https://archive.org/details/anzascaliforniae03bolt , https://archive.org/details/anzascaliforniae04bolt | public domain (already listed) | The village of about 400 at Antioch; the village near Gilroy. |
| A. L. Kroeber, *The Patwin and their Neighbors*, UCPAAE 29(4), 1932 | https://digitalassets.lib.berkeley.edu/anthpubs/ucb/text/ucp029-005.pdf | UC Berkeley digital assets | Southern Patwin towns (Suskol, Tuluka, Chimenukme at Napa). |
| H. E. Driver, *Wappo Ethnography*, UCPAAE 36(3), 1936 | https://digitalassets.lib.berkeley.edu/anthpubs/ucb/text/ucp036-004.pdf | UC Berkeley digital assets | Wappo house type. |
| O. C. Stewart, *Notes on Pomo Ethnogeography*, UCPAAE 40(2), 1943 | https://digitalassets.lib.berkeley.edu/anthpubs/ucb/text/ucp040-003.pdf | UC Berkeley digital assets | Pomo community names (as cited by Milliken). |
| Fort Ross Conservancy, "Ranch era" | https://www.fortross.org/ranch-era | (c) Fort Ross Conservancy; one fact | The Kashaya sent away from Metini after the 1867 sale (read as a search summary; the site was unreachable). |
| California Office of Historic Preservation, California Historical Landmarks nos. 17, 501, 667, 835 (Sonoma), 564, 682 (Napa), 534 (Solano), 342, 469, 998 (Santa Cruz) | https://ohp.parks.ca.gov/ListedResources/Detail/<n> | State of California | Official landmark texts: dates of the Blue Wing Inn, Salvador Vallejo and Nash adobes, Cooper's sawmill, Yount's blockhouse / adobe / mills, York's cabin, the Pena Adobe, the Castro Adobe; Mission Santa Cruz and the Villa de Branciforte. |
| Wikipedia: "Sonoma State Historic Park", "Blue Wing Inn", "Branciforte Adobe", "Pena Adobe", "Rancho Los Putos", and the lists "California Historical Landmarks in ... County" | https://en.wikipedia.org/wiki/Sonoma_State_Historic_Park | CC BY-SA 4.0 (facts only) | La Casa Grande (1836-40, tower about 1843, fire of 12 Feb 1867, surviving servants' wing); landmark coordinates; cross-checks. |
| Visit Santa Cruz County, "The Historic Adobes of Santa Cruz County" | https://www.santacruz.org/blog/the-historic-adobes-of-santa-cruz-county/ | (c) Visit Santa Cruz County; facts only | Mission Adobe (built 1822-24, 7 of 17 rooms), Branciforte Adobe ("Spanish period (1797-1821)"), Castro Adobe ("1848 or 1849"). |
| Overture Maps buildings, `region4_building.parquet` | (already listed) | ODbL / CDLA | Size and bearing of the eight surviving adobes, measured only. |


<!-- sites -->
### Military and industrial sites of the ten-county extent (`data/manual/industrial_sites/`, README section "Ten-county extent")

Added 2026-11 for Solano, Napa, Sonoma, Santa Cruz, east Contra Costa and south Santa Clara (definitions and
sources per site in `tools/industrial_def_ext.py`; every feature / row carries its `source_url`).

* **Outlines:** OpenStreetMap land-use outlines via Overture `base/land_use` 2026-10-21.0 (ODbL, © OpenStreetMap
  contributors); outlines of vanished sites and growth stages read on USGS historical topographic maps
  (public domain; https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/): Mare Island
  1:62,500 1916 / 1942 and 1:24k 1951 / 1959; Benicia 1950 / 1959 (PR 1968, 1979); Vacaville 1:62,500 1953 and
  Elmira 1:24k 1953 (PR 1968–78); Sears Point 1951; Honker Bay and Antioch North 1953 / 1978; Davenport 1955 /
  1991; Felton 1955; Chittenden 1955 (PR 1980); Watsonville West 1954 (PR 1978); Napa 1951 (PR 1978); Cuttings
  Wharf 1949; Morgan Hill 1955 (PR 1978); Two Rock 1954. Footprints: Overture buildings (OSM / ML, ODbL / CDLA).
* **Facts (years; facts only):**
  * Wikipedia (CC BY-SA): Mare Island Naval Shipyard; Benicia Arsenal; Benicia, California; Benicia Refinery;
    Travis Air Force Base; Skaggs Island Naval Communication Station; Training Center Petaluma; Camp Stoneman;
    Columbia Steel Company; Gaylord Container Corporation; Davenport, California; California Powder Works;
    Graniterock; Basalt Rock Company; California Medical Facility; California State Prison, Solano; Fairfield,
    California (https://en.wikipedia.org/wiki/…).
  * National Park Service, Mare Island Naval Shipyard: https://www.nps.gov/places/mare-island-naval-shipyard.htm ;
    National Historic Landmark listing summary (areas A–D, building years):
    https://noehill.com/solano/nat1975002103.aspx
  * Center for Land Use Interpretation: https://clui.org/ludb/site/dow-chemical-pittsburg ,
    https://clui.org/ludb/site/pittsburg-power-plant
  * Contra Costa Health, Corteva / Dow Pittsburg risk-management page (Dow bought the plant in 1939):
    https://www.cchealth.org/health-and-safety-information/hazmat-programs/refinery-and-industry-safety-reports/rmp-corteva-agriscience
  * California Public Utilities Commission decisions 50035 (1954, Pittsburg Steam Plant units 1–4) and 63489
    (1962, Contra Costa Power Plant units of 1951 / 1953): https://files.cpuc.ca.gov/LegacyCPUCDecisionsAndResolutions/Decisions/
  * DTSC fact sheet, DuPont Oakley (plant 1956–1997):
    https://dtsc.ca.gov/wp-content/uploads/sites/31/2018/01/DuPont_FS_CorAction_0206.pdf
  * San Francisco Bay Regional Water Quality Control Board: Potrero Hills Landfill (opened August 1986)
    https://www.waterboards.ca.gov/sanfranciscobay/board_decisions/tentative_orders/Potrero_Hills/Potrero_Hills.pdf ;
    Kirby Canyon (landfilling since 1986)
    https://www.waterboards.ca.gov/sanfranciscobay/board_info/agendas/2018/March/KirbyCanyon/2018_Kirby_TO.pdf
  * Santa Cruz LocalWiki, Lockheed Martin (test base established 1957): https://localwiki.org/santacruz/Lockheed_Martin
  * Morgan Hill Times, "UTC shutting down its Coyote Valley plant" (after about 45 years of rocket testing):
    https://morganhilltimes.com/utc-shutting-down-its-coyote-valley-plant/
  * CEQAnet, Syar Lake Herman Quarry expansion (SCH 2000072074): https://ceqanet.lci.ca.gov/2000072074
* **Use:** ground cover per site part and period, `site` map labels, founding-year floors for footprints inside a
  site (`building_dates.csv`), footprint years from the map editions and researched buildings
  (`known_dates_industrial.csv`). Licence of the derived files: ODbL (OSM outlines / footprints); USGS maps public
  domain.


<!-- fires -->
### Wildfires and other disasters (`pipeline/fires.py`, `data/manual/fires/`, README there)

* **CAL FIRE Damage Inspection (DINS) structure points** — ArcGIS service `POSTFIRE_MASTER_DATA_SHARE`
  (https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/arcgis/rest/services/POSTFIRE_MASTER_DATA_SHARE/FeatureServer/0;
  data.ca.gov "CAL FIRE Damage Inspection (DINS) Data"). Public state data (no licence text on the service —
  check the data.ca.gov page). Attribution: CAL FIRE. Use: the 12,934 structures inspected as destroyed in the
  ten counties since 2015 (`destroyed_structures.csv`): today's footprint there is the rebuild or ends at the fire,
  and a predecessor stands until the fire date.
* **CAL FIRE FRAP fire perimeters, "California Fire Perimeters (all)"** —
  https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/arcgis/rest/services/California_Historic_Fire_Perimeters/FeatureServer/0
  (https://www.fire.ca.gov/what-we-do/fire-resource-assessment-program/fire-perimeters). Public domain.
  Attribution: CAL FIRE FRAP. Use: 441 perimeters 1923–2025 (`perimeters.geojson`), the ring of the 1991 Tunnel fire.
* **MTBS (Monitoring Trends in Burn Severity), thematic burn severity mosaics** — USGS / USDA Forest Service,
  https://www.mtbs.gov, image service
  https://imagery.geoplatform.gov/iipp/rest/services/Fire_Aviation/USFS_EDW_MTBS_CONUS/ImageServer. Public domain.
  Use: high-severity (class 4) patches of 55 fires 1985–2020 (`severity_high.geojson`) for the terrain.
* **Permit Sonoma, "Wildfire Rebuild Permits" (public view layer)** —
  https://services1.arcgis.com/P5Mv5GY5S66M8Z1Q/arcgis/rest/services/Wildfire_Rebuild_Permits_Public_View_Layer/FeatureServer/0.
  Public county service (no licence text). Use: completed rebuild permits per parcel in unincorporated Sonoma County
  (`rebuild_permits.csv`; year = issue date + 1, estimated).
* **Santa Cruz County GIS, "Recovery Permit Center" (CZU fire)** —
  https://sccgis.santacruzcountyca.gov/server/rest/services/czucleanup/MapServer/5. Public county service (no
  licence text). Use: closed dwelling rebuild permits per parcel with the closing date (`rebuild_permits.csv`).
* Researched dates and names (`fire_dates.csv`), the Tunnel fire clearance (`clearances.csv`) and the fire events in
  `data/tables/events.csv`: Wikipedia articles cited per row (Tubbs, Atlas, Kincade, Glass, LNU / CZU / SCU Lightning
  Complex fires, October 2017 Northern California wildfires, Oakland firestorm of 1991, 1923 Berkeley fire, Mount
  Vision Fire).


<!-- land -->
### `sfei_delta_historical_ecology` — SFEI Sacramento–San Joaquin Delta Historical Ecology (2012) and Laguna de Santa Rosa
- Whipple, Grossinger, Rankin, Stanford, Askevold 2012, *Sacramento–San Joaquin Delta Historical Ecology Investigation: Exploring Pattern and Process*, SFEI-ASC; and the Central Laguna de Santa Rosa study. Taken from SFEI's Historical Ecology GIS data compilation (https://www.sfei.org/data/historical-ecology-gis-data-compilation, GPL v3, cite SFEI-ASC) as served by CDFW BIOS, dataset ds3201: https://services2.arcgis.com/Uq9r85Potqm3MfRV/arcgis/rest/services/biosds3201_fpu/FeatureServer/0 — fetched by `data/manual/delta/fetch_sfei_compilation.py` into `data/raw/sfei_historical_ecology/delta.geojson` and `laguna_de_santa_rosa.geojson`.
- Use: c.1800 habitat of the Delta inside the map (tidal freshwater marsh, channels, riparian forest, wet meadow, dunes) and of the Laguna near Sebastopol; same class mapping as the other SFEI studies.

### `dsc_delta_islands` — Delta Stewardship Council, Delta Levees Investment Strategy islands and tracts
- https://services5.arcgis.com/netd7RBEFAa05HUC/arcgis/rest/services/DLIS_Island_Priority/FeatureServer/0 (170 polygons of Delta and Suisun Marsh islands and tracts; "DLIS Team and Delta Stewardship Council, 2017", public agency data).
- Use: outlines of the 30 island rows `dl_*` in `data/manual/fill_zones.csv` and of three flooded tracts in `water_history.csv`; `data/manual/delta/delta_zone.geojson`.

### `thompson_delta` — John Thompson on the reclamation of the Delta
- *The Settlement Geography of the Sacramento–San Joaquin Delta, California*, Ph.D. dissertation, Stanford University, 1957 (scan filed as a State Water Board exhibit: https://www.waterboards.ca.gov/waterrights/water_issues/programs/hearings/pak_young/exhibits/pakyoung_3j.pdf), pp. 469–504; "Early Reclamation and Abandonment of the Central Sacramento–San Joaquin Delta", Sacramento History Journal VI (2006) (https://www.waterboards.ca.gov/waterrights/water_issues/programs/bay_delta/california_waterfix/exhibits/docs/SHR/SHR-201.pdf).
- Use: year each island or tract was leveed, abandoned, reclaimed for good or flooded (`dl_*` rows, Sherman Lake, Franks Tract).

### `nid` — National Inventory of Dams (US Army Corps of Engineers)
- https://nid.sec.usace.army.mil/api/nation/csv (California rows; public domain). Use: completion year of the dam of every reservoir of 7.5 ha and more in the new counties (`data/manual/landscape/water_history.csv`), joined to the Overture / OSM lake polygon by distance.

### Other sources of this pass (one per row in the tables)
- USGS historical topographic maps, 1:24,000 editions 1948–1997 of the Mare Island, Benicia, Port Chicago / Vine Hill, Honker Bay, Antioch North, Fairfield South and Cuttings Wharf quadrangles and the 1940 1:62,500 Carquinez Strait sheet (TNM, public domain): `tp_*` rows on the region grid.
- State Coastal Conservancy, Napa River Salt Marsh Restoration Project (Pond 3, 2006); NOAA (Cullinan Ranch breach, 6 Jan 2015); East Contra Costa Historical Society (Discovery Bay, first bay dug from 1968); Trust for Public Land (Liberty Island, 1997–98); J. Lund, California WaterBlog 2011 (Mildred Island, 1983); Wikipedia (Franks Tract 1938, Little Franks Tract 1982, Big Break 1928).


<!-- airfields -->
### Airfields of the new counties (2026-11) — `data/manual/airports/tools/newarea.py`

* **USGS Historical Topographic Map Collection** (TNM Access, GeoTIFFs under
  `https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/`; public domain). Sheets used to trace
  vanished airfields and to date pavement (aerial-photo / photorevision year in brackets): Sebastopol and Santa Rosa
  1:24,000 1954 (1952; PR 1968, 1980), Cotati 1954 (1952; PR 1968, 1980), Felton 1955 (1953; PR 1968, 1980) and 1991,
  Soquel 1954 (1952; PR 1968), Capitola 1:62,500 1940 (1938), Rio Vista 1953 (1949; PR 1968) and 1978 (1974), Antioch
  South 1953 (1949; PR to 1980), Petaluma River / Glen Ellen / Cotati / Petaluma 1954 (1952; PR 1968, 1980), Cuttings Wharf
  1949 (1948; PR 1968, 1981), Benicia 1950 (1948), 1959 (1958; PR 1968), Calistoga 1958 (1957; PR 1980), Morgan Hill 1955
  (1953; PR 1968, 1973, 1980), Allendale 1953 (1949; PR 1968, 1973), Fairfield North / South 1951 / 1949 (1948; PR 1968,
  1973, 1980), Elmira and Denverton 1953 (1949; PR 1968, 1973, 1980), Healdsburg 1955 (1953; PR 1980) and 1993, Watsonville
  West 1954 (1952; PR 1968, 1980, 1994), Capell Valley 1951 (1948; PR 1968), Port Chicago 1951 / 1959 / 1968 and Vine Hill
  1959 (PR 1980), Stewarts Point 1943 and 1978 (1971), Mare Island 1949-1980, Sears Point 1951 (PR 1968).
  Use: outlines and runways of 16 vanished airfields (`data/manual/airports_extra*.geojson`), runway phases of Travis AFB,
  Napa County, Sonoma County and Watsonville (`data/manual/airports/pavement_dates.csv`), opening years of five small
  airports (`data/tables/airports.csv`).
* **Paul Freeman, Abandoned & Little-Known Airfields** — California pages `Airfields_CA_SantaRosa_N.htm`,
  `_SantaRosa_S.htm`, `_Monterey.htm`, `_Oakland_N.htm`, `_SacramentoSW.htm`, `_SanJose_E.htm` under
  `https://www.airfields-freeman.com/CA/` (© Paul Freeman; facts and dates only, no text or images copied). Use: opening /
  closing years and runway lengths of the vanished airfields (it quotes sectional charts, airport directories, and
  H. & J. Campbell, *Two Hours by Crow*); each row of `data/tables/airports.csv` names the statement used.
* **Wikipedia** (CC BY-SA; facts only): Charles M. Schulz–Sonoma County Airport (1939 county purchase, Army field June
  1942, 2013–14 extension of runway 14/32), Travis Air Force Base (construction 1942; C-17s from 2006), Naval Auxiliary
  Landing Field Santa Rosa (two 7,000-ft concrete runways, commissioned 1943), Yolo County Airport (Winters-Davis Flight
  Strip, c.1942), Monterey Bay Academy (Camp McQuaide).
* **Esri World Imagery** (viewed only, nothing copied): check of the surviving pavement of NAAS Santa Rosa (north half of
  the N-S runway, west end of the E-W runway, ramp and taxiways) — which pieces end 9999.
* **OpenStreetMap** (via Overture 2026-10-21.0 `region_airports.parquet`; © OpenStreetMap contributors, ODbL): today's
  runway / taxiway lines of Travis AFB, Napa County, Sonoma County and Watsonville (dated per piece in
  `pavement_dates.csv`); the lines of two surviving taxiways of NAAS Santa Rosa in `airports_extra.geojson`; the OSM lines
  of the surviving NAAS Santa Rosa pavement were used to check the tracing (agreement within a few metres).


<!-- rail -->
### Lost railways of the new counties (2026-11; `data/manual/historic_rail.geojson`, `historic_rail_spec.py`, `routes.csv`)

* **Geometry** — OpenStreetMap abandoned / disused railway grades via Overture `rail.parquet` 2026-10-21.0 (ODbL) and the
  2026-11 Overpass extracts in `data/raw/historic_rail/`; OpenHistoricalMap ways (CC0 1.0, https://www.openhistoricalmap.org/,
  OHM Overpass API https://overpass-api.openhistoricalmap.org/api/interpreter, downloaded 2026-11-10; way ids in each
  segment's note); USGS Historical Topographic Map Collection (public domain, GeoPDFs from
  https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/): Vacaville 1908 1:62,500 (TNM 299005; Elmira -
  Vacaville "Clear Lake Branch"), Mt Diablo 1898 (298276) and Antioch 1908 (296717) (Pittsburg R.R., Empire R.R.); today's
  street centrelines (Overture roads) for the Port Watsonville line and Guerneville - Northwood.
* **Dates** — Wikipedia: Northwestern Pacific Railroad; San Francisco and North Pacific Railroad; North Pacific Coast
  Railroad; Petaluma and Santa Rosa Railroad; Santa Rosa and Carquinez Railroad; Vaca Valley and Clear Lake Railroad;
  Sacramento Northern Railway; Ocean Shore Railroad; Watsonville Traction Company; San Francisco, Napa and Calistoga Railway
  (checked, not drawn). santacruztrains.com (Derek R. Whaley): Boulder Creek stations
  (https://www.santacruztrains.com/2019/03/stations-boulder-creek.html), Dougherty Extension Railroad, Loma Prieta Branch,
  Pajaro Valley Consolidated Railroad, Scott Creek Railway / San Vicente Lumber Company, Swanton (site search pages cited
  in the rows). abandonedrails.com: Glen Ellen Branch (https://www.abandonedrails.com/glen-ellen-branch), Calistoga Branch
  (https://www.abandonedrails.com/calistoga-branch; ICC docket 25306 of 18 Sept 1968). wx4.org "Mount Diablo coal mine
  railroads" (https://wx4.org/to/foam/shortlines/coal/mines.html) for the Pittsburg and Empire railroads. Thos. H. Thompson,
  Map of the City of Santa Rosa, 1876 (Historical Atlas of Sonoma County, 1877; David Rumsey
  https://www.davidrumsey.com/maps2368.html) for the Santa Rosa horse railway.


<!-- dates -->
### Researched construction years, new counties (2026-11 ship pass) — `data/tables/known_building_dates_region.csv` (+181 rows), `data/tables/notable_demolished_region.csv` (+15 rows)

Construction / opening years of exempt, institutional and other notable buildings of Sonoma, Napa, Solano, Santa Cruz,
east Contra Costa and south Santa Clara counties that the assessor rolls do not date (one row per Overture footprint;
source URL and wording in each row). Sources, by use:

* **Wikipedia** (CC BY-SA 4.0; articles and infoboxes, incl. the NRHP county lists and "List of Carnegie libraries in
  California") and **Wikidata** (CC0; inception / opening dates, coordinates) — schools, colleges, hospitals, wineries,
  theatres, NRHP buildings, lost hotels. https://en.wikipedia.org/ · https://www.wikidata.org/
* **National Register of Historic Places** records (NPS NPGallery, public domain): Veterans Home chapel (79000510), Santa
  Cruz Veterans Memorial Building (92000423), Santa Cruz post office (85000139). https://npgallery.nps.gov/
* **Institutions' own histories** (facts only): Sonoma State University timeline (sonoma.edu/history,
  music.sonoma.edu/about/history); Santa Rosa Junior College building pages (maps.santarosa.edu); UC Santa Cruz "UCSC at 60"
  (magazine.ucsc.edu) and timeline (ucsc.edu/60-years/timeline); City of Morgan Hill public facilities; Sonoma County
  (Petaluma Veterans Memorial Building; Sheriff's facilities); Solano County Library; Santa Clara County Library District;
  Superior Court of Santa Clara County; Judicial Council of California (Arnason Justice Center); Dignity Health (Dominican
  Hospital); NorthBay Health; Tannery Arts Center; Vacaville Performing Arts Theatre.
* **Local history and press** (facts only): Santa Cruz LocalWiki (CC BY 4.0; downtown buildings, Cooper House, St. George
  Hotel, Neptune Casino, Calvary Church); Santa Cruz Public Libraries local history (Carnegie library 1904-1966, Sea Beach
  Hotel fire 1912); PCAD — Pacific Coast Architecture Database (Sonoma County courthouses of 1884 and 1909); Living New
  Deal (Sonoma County Hospital 1937); Historical Marker Database; NoeHill (Sonoma Carnegie library); Solano history columns
  (solanoarticles.com: Fairfield civic center 1971); Western City (Solano County Government Center 2005); Napa Wine
  Project, Napa County Landmarks, The Clio (Sterling, Clos Pegase, Inglenook); Pajaronian, Gilroy Dispatch, Morgan Hill
  Life, Tradeline, Healthcare Design, Tricycle (single opening dates).

Rows whose year is the opening of a whole campus (high schools, Solano Community College, Cabrillo College — the Laney
College pattern) say "Campus-wide date" in the note; rows with an approximate year say ESTIMATE. Demolished rows give
`footprint_m` as WxD estimates (no county parcel layer is needed) and say how certain the position is.


<!-- lm_north -->
## North Bay landmark reconstructions (`viewer/src/landmarks/northbay.ts`, `data/research/landmarks_northbay.md`, `data/tables/landmarks_northbay.csv`)

* **National Register of Historic Places / National Historic Landmark nomination forms** (National Park Service,
  NPGallery; US government works, public domain) — `https://npgallery.nps.gov/NRHP/GetAsset/NRHP/<refnum>_text`
  (`NHLS/` for landmarks). Used for dimensions and histories: Fort Ross 66000239, Fort Ross Commander's House
  70000150, Sonoma Plaza 75000489, Petaluma Adobe 70000151, Benicia Capitol 71000204, Benicia Arsenal 76000534,
  Mare Island Naval Shipyard 75002103, Greystone Cellars 78000725, Rhine House 72000242, Bale Mill 72000240, Napa
  County Courthouse Plaza 92000778, Napa Opera House 73000414, De Turk Round Barn 04000334, Free Public Library of
  Petaluma 88000925, Condominium 1 05000731 (Guerneville Bridge 89000945 and Jack London Ranch 66000240 were read but
  not modelled).
* **HAER CA-297, Carquinez Bridge** (Historic American Engineering Record, Library of Congress; public domain) —
  https://www.loc.gov/pictures/item/ca3089/ (data pages `ca3089data.pdf`). Span lengths, truss depths, pier
  arrangement and clearances of the 1927 cantilever; relation of the 1958 bridge to it.
* **S. A. Roake, "Design and erection of the Martinez-Benicia bridge superstructure", Engineering News-Record,
  June 4, 1931, pp. 918–922** (and C. R. Harding, ENR Jan 30, 1930), scans at
  https://historicbridges.org/california/martinezrr/benicia.pdf — span table of the 1930 railroad bridge. Facts only.
* **US Wind Turbine Database v9.1** (USGS, Lawrence Berkeley National Laboratory, American Clean Power Association;
  public domain; Hoen et al., doi:10.5066/F7TX3DN0) — https://eerscmap.usgs.gov/uswtdb/ (CSV of 2026-09-28 from
  https://energy.usgs.gov/uswtdb/assets/data/uswtdbCSV.zip). Position, project year, model, hub height, rotor
  diameter and tip height of the 527 Solano County turbines drawn as landmarks (their offsets are embedded in
  `northbay.ts`).
* **USGS 3DEP elevation** (public domain) — https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer
  (`getSamples`): shore positions along the bridge alignments, ground heights at the bridge approaches, the crest line
  and crest elevation of Monticello Dam.
* **OpenStreetMap** (© OpenStreetMap contributors, ODbL) via Overture 2026-10-21.0 for building outlines and bridge
  alignments; via Nominatim (https://nominatim.openstreetmap.org) for the outline of the Monticello Dam spillway
  ("Morning Glory Spillway Opening", way 138525103) and the dam line (way 604427590).
* **California State Parks, Fort Ross State Historic Park** — https://www.parks.ca.gov/?page_id=449 and the park
  brochure (`/pages/449/files/FortRossSHPFinalWebLayout113018.pdf`): founding party of 1812. Facts only.
* **Wikipedia** (CC BY-SA 4.0; facts only) — Carquinez Bridge, Benicia–Martinez Bridge, Fort Ross, Rotchev House,
  Mission San Francisco Solano, Sonoma Barracks, Sonoma City Hall, Rancho Petaluma Adobe, Benicia Capitol State
  Historic Park, Benicia Arsenal, St. Peter's Chapel (Mare Island), The Culinary Institute of America at Greystone,
  Inglenook (winery), Beringer Vineyards, Bale Grist Mill State Historic Park, Napa County Courthouse Plaza, Napa
  Valley Opera House, Monticello Dam, Church of One Tree, Free Public Library of Petaluma, St. Teresa of Avila Church
  (Bodega), Condominium 1, Sea Ranch, Shiloh wind power plant. Reference photographs from Wikimedia Commons were
  viewed for proportions only (file names in `landmarks_northbay.md`); none is redistributed.


<!-- lm_south -->
### Landmarks — Santa Cruz County, south Santa Clara Valley, east Contra Costa (`viewer/src/landmarks/coastsouth.ts`)

- `data/research/landmarks_coastsouth.md` (`viewer/src/landmarks/coastsouth.ts`, `data/tables/landmarks_coastsouth.csv`): 34 models —
  Santa Cruz Beach Boardwalk (Giant Dipper, Sky Glider, Casino / Cocoanut Grove, the Plunge, Looff Carousel), Santa Cruz Wharf,
  Mission Santa Cruz (1794 church, Holy Cross 1889, 1931 replica), Santa Cruz lighthouses (1869, Mark Abbott 1967, Walton 2001),
  SS Palo Alto and its pier, Capitola Wharf and Venetian Court, Felton Covered Bridge, Town Clock, Hotel Palomar, Del Mar Theatre,
  St. Patrick's Watsonville (1903 / 1994), Gilroy Old City Hall, Villa Mira Monte, Antioch Bridge (1978), John Marsh Stone House
  and its tower, seven Altamont / Vasco wind-turbine groups. Sources per model in the table's `year_source_url` / notes.
- **OpenStreetMap** outlines via the OSM API (downloaded 2026-11-10) and Overture 2026-10-21.0 — © OpenStreetMap contributors,
  **ODbL** (attribution; the landmark file is offered under ODbL like the other landmark files).
- `usgs_3dep_lpc_santacruz2020`, `usgs_3dep_lpc_santaclara2020`, `usgs_3dep_lpc_contracosta2022` — **USGS 3DEP lidar point clouds**
  `CA_SantaCruzCounty_2020`, `CA_SantaClaraCounty_2020`, `CA_ContraCosta_1_2022`, read as Entwine Point Tiles from the public bucket
  `https://s3-us-west-2.amazonaws.com/usgs-lidar-public/<project>/` (small windows round each landmark). **Public domain**
  (U.S. Geological Survey, 3D Elevation Program). Use: roof, tower, spire and deck heights, plan placement, track heights.
- `uswtdb` — **U.S. Wind Turbine Database** (Hoen, B.D., Diffendorfer, J.E., Rand, J.T., Kramer, L.A., Garrity, C.P., Hunt, H.E.:
  United States Wind Turbine Database, U.S. Geological Survey, American Clean Power Association and Lawrence Berkeley National
  Laboratory data release, https://doi.org/10.5066/F7TX3DN0; viewer https://energy.usgs.gov/uswtdb/ ; API
  `https://energy.usgs.gov/api/uswtdb/v1/turbines`, queried 2026-11-10 for FIPS 06013 and 06001). **Public domain** (cite as above).
  Use: turbine positions, hub heights, rotor diameters, project years.
- Text sources (facts only, no data copied): Wikipedia (CC BY-SA; articles named per model), lighthousefriends.com (Santa Cruz
  light history), ibiblio.org Lighthouse Directory (tower heights), californiamissions.com (mission church dimensions), Pacific Coast
  Architecture Database (St. Patrick's, Hotel Palomar, Felton bridge), Santa Cruz Public Libraries local history (Town Clock, SS Palo
  Alto), semperaltius.com Palo Alto history (pier 630 × 40 ft, 1930 dates), LocalWiki Santa Cruz (Palomar, Del Mar plaque text),
  City of Capitola "Capitola Wharf Past", pierfishing.com, MTC bridge page (Antioch Bridge), johnmarshhouse.com.


<!-- extents -->
### region_extents — ten-county towns (2026-11) (add to the existing `region_extents` entry)

* **USGS Historical Topographic Map Collection** (public domain; U.S. Geological Survey, The National Map — TNM Access
  API `https://tnmaccess.nationalmap.gov/api/v1/products`, scans at
  `https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/<scale>/…_geo.pdf`): 60 more sheets
  for 24 towns of Sonoma, Napa, Solano, Santa Cruz, east Contra Costa and south Santa Clara counties — the
  1:125,000 Napa and Santa Cruz sheets of 1902 (surveyed to 1899), the 1:62,500 first surveys of 1906-22, the
  1:31,680 Rio Vista sheet of 1910, the 1:62,500 editions of 1933-45 and the 1:24,000 sheets of 1949-60. Survey /
  photo years from each scan's FGDC record. Every sheet with its GeoPDF link: `data/manual/region_extents/README.md`
  → *Maps used*. Use: built-up extent snapshots `data/manual/region_extents/<town>_<year>.geojson`
  (`tools/extents.py`).
* **Library of Congress, Geography and Map Division, Sanborn Maps Collection** (public domain: "The content of the
  Library of Congress online Sanborn Maps Collection is in the public domain and is free to use and reuse"; credit
  line: Library of Congress, Geography and Map Division, Sanborn Maps Collection): the colour key maps on the index
  sheets of ten volumes — Santa Rosa Dec. 1904 (https://www.loc.gov/item/sanborn00838_004/), Santa Cruz 1905
  (https://www.loc.gov/item/sanborn00833_004/), Gilroy Oct. 1906 (https://www.loc.gov/item/sanborn00566_003/),
  Watsonville Jul. 1908 (https://www.loc.gov/item/sanborn00921_005/), Petaluma Nov. 1910
  (https://www.loc.gov/item/sanborn00756_005/), Napa Oct. 1910 (https://www.loc.gov/item/sanborn00707_004/),
  Saint Helena Nov. 1910 (https://www.loc.gov/item/sanborn00800_004/), Sebastopol Apr. 1911
  (https://www.loc.gov/item/sanborn00847_006/), Benicia Aug. 1913 (https://www.loc.gov/item/sanborn00417_004/),
  Vallejo Mar. 1919 (https://www.loc.gov/item/sanborn00905_004/). Use: the area Sanborn surveyed (blocks under the
  key-map patches), kept where a USGS survey or buildings standing today confirm the block
  (`data/manual/region_extents/tools/sanborn_key.py`; snapshots `<town>_<year>.geojson` with
  `source = loc_sanborn:…`).
* **US Census Bureau TIGER/Line 2024** area water of Santa Cruz County (`tl_2024_06087_areawater.zip`, public
  domain; https://www2.census.gov/geo/tiger/TIGER2024/AREAWATER/): today's land for the extent polygons (the other
  counties' files were already listed).
* Street names and centrelines for the registration: Overture Maps roads (OpenStreetMap, ODbL) — already listed.


<!-- sanborn -->
### Sanborn maps of the new counties (Santa Rosa, Vallejo, Napa, Petaluma, Santa Cruz, Watsonville)

* **Sanborn Map Company, Insurance Maps** — Library of Congress, Geography and Map Division, Sanborn Maps Collection
  (public domain; IIIF images via `https://www.loc.gov/item/<id>/?fo=json`). Volumes traced by
  `pipeline/sanborn_trace_newcounties.py` (details, sheets and fits: `data/manual/sanborn/README_northbay.md`,
  `README_santa_cruz.md`):
  Santa Rosa `sanborn00838_004` (Dec 1904), `_005` (1908), `_006` (1908 corrected to 1950);
  Vallejo `sanborn00905_003` (Jul 1901), `_004` (Mar 1919), `_005` (1919 corrected to Mar 1950);
  Napa `sanborn00707_003` (Jun 1901), `_004` (Oct 1910);
  Petaluma `sanborn00756_005` (Nov 1910);
  Santa Cruz `sanborn00833_003` (Jul 1892), `_004` (1905);
  Watsonville `sanborn00921_006` (Dec 1920), `_007` (1920 corrected to Dec 1962).
  Use: footprints of vanished buildings (`data/manual/sanborn/<town>_downtown_<year>.geojson`, `_coverage.geojson`),
  merged by `sf_predecessors.apply_sanborn` through `region_predecessors.REGION_SANBORN`.
  Attribution: "Library of Congress, Geography and Map Division, Sanborn Maps Collection".
* Control geometry for the tracing: Overture Maps transportation segments and buildings, release 2026-10-21.0 (ODbL,
  (c) OpenStreetMap contributors / Overture); county parcel layers already listed (Sonoma, Solano, Napa, Santa Cruz).
* **Clearances** (`data/manual/redevelopment_areas.csv`, rows `val_marina_vista`, `sr_urban_renewal_phase1`,
  `sr_urban_renewal_mall`, `sr_us101_viaduct`, `napa_town_center`, `sc_san_lorenzo_park_plaza`; source URLs in each row):
  * ESA, *Vallejo Ferry Terminal Reconfiguration Project: Cultural Resources Survey Report*, April 2024 (CEQAnet
    attachment, pp. 20-23: Marina Vista Redevelopment Project, adopted 1960, 600 structures, 125 acres, 24 blocks, seawall
    1966; fig. 9 = the 1967 site plan with the project boundary, fig. 10 = aerial view of May 1965) — https://files.ceqanet.lci.ca.gov/300424-1/attachment/YJM2lmLy00GH6JH8-0EBw6umsZQ6PpfDGFUFPJ5NM55hIiF-cR3zSk1laG2VGONDEva753A2MCL8c34M0 ;
    *Historical Articles of Solano County*, "Georgia St. has pioneers" (15 Mar 1964) — https://www.solanoarticles.com/history/index.php/weblog4/more/georgia_st_has_pioneers/
  * Jeff Elliott, *Santa Rosa History* (comstockhousehistory.blogspot.com / santarosahistory.com): "It will be a resplendent
    city" (2019: Urban Renewal Agency 1958, Phase I = 40 acres, Third St - Sonoma Av, Santa Rosa Av - E St), "Road to the
    mall" series (2022: ordinance 1439 of 10 Mar 1970, wrecking from 1972); Wikipedia, "Santa Rosa Plaza" (opened 1983,
    Macy's 1981); Cinema Treasures no. 28446 (California Theatre closed 1977).
  * US 101 in Santa Rosa: AARoads, "U.S. 101 North - Sonoma County" (downtown viaduct built 1968) —
    https://www.aaroads.com/california/us-101nl_ca.html ; Gribblenation, "The California State Route 12 freeway" (Santa Rosa
    Freeway opening 20 May 1949).
  * Napa: California Planning & Development Report, "Napa uncorks new downtown ..." (33-block redevelopment area, 1969) —
    https://www.cp-dr.com/post/napa-uncorks-new-downtown-to-tap-tourist-wine-industries ; Napa County Landmarks, "Dwight
    Murray Plaza and Kohl's" (Migliavacca Building razed 1973); Napa County Historical Society, "Napa Redevelopment, 1974".
  * Santa Cruz: Santa Cruz Public Library local history clippings (Santa Cruz Sentinel 18 Mar 1956 "Santa Cruz
    Redevelopment Gets Under Way: Flood-Hit Area is Initial Target", Sep 1956 plans approved, Dec 1959 call for proposals,
    22 Oct 1970 "SC Redevelopment Agency ... Closes") — https://history.santacruzpl.org/omeka/items/show/92142 , /103434 ,
    /92523 , /92571 ; Coastal Watershed Council, "Abating flooding along an urban river" (levees 1957-59).
    Only the catalogue records (title, date) of the clippings were read, not the article texts: the row's years are
    ESTIMATED from those dates.

