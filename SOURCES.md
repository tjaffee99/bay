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
- `data/tables/early_region.csv` + `data/research/early_region.md`: 142 rows (≈970 structures) 1700–c.1850 in Santa Clara, Alameda, Contra Costa, San Mateo and Marin: Mission Santa Clara's five sites, the pueblo of San José, Mission San José, Mission San Rafael, the Mission Dolores outposts, rancho adobes and Ohlone / Bay Miwok / Coast Miwok villages. Sources (facts only, per row in `source_url`): Skowronek & Wizorek, "Archaeology at Santa Clara de Asís" (*PCAS Quarterly* 33(3), 1997, https://www.pcas.org/Vol33N3/333Skowr.pdf); Santa Clara University Digital Humanities "Sites of Mission Santa Clara" (site coordinates, https://dh.scu.edu/exhibits/neatline/show/sites-of-mission-santa-clara); Bancroft, *History of California* i–iii (https://archive.org/details/historyofcalifor01banc …); F. Hall, *History of San José* (1871, https://archive.org/details/historyofsanjos00hall); *Clyde Arbuckle's History of San José* (1985, https://archive.org/details/casjhsj_000308); Milliken, Shoup & Ortiz, *Ohlone/Costanoan Indians of the San Francisco Peninsula* (NPS 2009, https://npshistory.com/publications/goga/ohlone-indians.pdf); California Historical Landmark listings (https://ohp.parks.ca.gov/ListedResources/Detail/<no.>, marker GPS from https://www.californiahistoricallandmarks.com/landmarks/chl-<no.>); Peralta Hacienda chronology (https://www.peraltahacienda.org/PeraltaHistoryChron.htm); El Cerrito, San Pablo, Milpitas, Mill Valley and Sausalito historical societies, John Marsh House Trust, City of Hayward, USGS OFR 2008-1121; Wikipedia (Coast Miwok village list after Barrett 1908, Sánchez Adobe Park, Alviso, Mission San Rafael). Sizes and orientations of surviving adobes measured on `overture_region5` footprints (ODbL; no geometry copied); street-intersection anchors from `overture_transportation` (ODbL).
- `data/research/landmarks_batch4.md`: 1915 PPIE traced from the Library of Congress Sanborn map of the Exposition (https://www.loc.gov/item/sanborn00813_025/, Nov 1914, public domain); GGIE 1939 from the Official Guide plan; Presidio, Castillo, Mission compound, Playland, Woodward's Gardens, Mechanics' Pavilion, Sutro Heights.
- `data/manual/sanborn/western_addition_1899.geojson`, `western_addition_1913.geojson` (+ `README_western_addition.md`, `sheets_western_addition.csv`): building footprints, storeys and construction traced from the Library of Congress Sanborn Fire Insurance Maps of San Francisco — 1899 vol. 3 (https://www.loc.gov/item/sanborn00813_010/) and 1913 vols. 3–4 (https://www.loc.gov/item/sanborn00813_017/, https://www.loc.gov/item/sanborn00813_018/); public domain ("Library of Congress, Geography and Map Division, Sanborn Maps Collection"). Use: pre-redevelopment Western Addition (A-1/A-2 areas) instead of procedural rows; tool `pipeline/sanborn_trace.py`.
- `data/manual/sanborn/fishermans_wharf_{1899,1913,1950}.geojson`, `mission_bay_{1913,1950}.geojson`, `potrero_point_{1914,1950}.geojson`, the railway centrelines `mission_bay_{1913,1950}_tracks.geojson` / `potrero_point_{1914,1950}_tracks.geojson` + `README_waterfront.md`: building footprints, wharf decks, rail-yard tracks, storeys and uses traced from the Library of Congress Sanborn Fire Insurance Maps of San Francisco (public domain): 1899 vol. 1 https://www.loc.gov/item/sanborn00813_008/, 1913 vols. 1–2 https://www.loc.gov/item/sanborn00813_015/ and _016/, 1914 vol. 6 _020/, 1913–1950 corrected vols. 1, 2, 6 _030/, _031/, _035/; georeferenced on DataSF street centrelines (`pipeline/sanborn_trace_waterfront.py`, control in `data/manual/sanborn/control/`).
- `data/manual/sanborn/soma_industrial_{1913,1950}.geojson`, `butchertown_{1914,1950}.geojson`, `north_waterfront_{1913,1950}.geojson`, their `*_tracks.geojson` railway centrelines and `*_coverage.geojson` + `README_industrial.md`: industrial / warehouse footprints and rail tracks traced from the Library of Congress Sanborn Fire Insurance Maps of San Francisco (public domain, "Library of Congress, Geography and Map Division, Sanborn Maps Collection"): 1913 vol. 1 https://www.loc.gov/item/sanborn00813_015/ (Produce Market, north waterfront), 1913 vol. 2 https://www.loc.gov/item/sanborn00813_016/ (South of Market), 1914 vol. 8 https://www.loc.gov/item/sanborn00813_022/ (Butchertown / Islais Creek / Bayview; title page 1914, LOC catalogue note "1922"), and the corrected 1950 states 1913–1950 vol. 1 https://www.loc.gov/item/sanborn00813_030/, 1913–Sep 1950 vol. 2 https://www.loc.gov/item/sanborn00813_031/, 1914–Feb 1950 vol. 8 https://www.loc.gov/item/sanborn00813_037/. Georeferenced on DataSF street centrelines (`pipeline/sanborn_trace_industrial.py`, control in `data/manual/sanborn/control/industrial/`). Use: real factories, warehouses, slaughterhouses and rail spurs instead of procedural fabric.
- `data/manual/sanborn/san_jose_downtown_{1915,1950}.geojson`, `san_jose_downtown_coverage.geojson` + `README_san_jose.md`: downtown San José building footprints (Park Center Plaza, plaza / Fairmont / convention-centre blocks, First / Market St core, St James Park, SR 87 corridor) traced from the Library of Congress Sanborn Fire Insurance Maps of San José, California (public domain, "Library of Congress, Geography and Map Division, Sanborn Maps Collection"): 1915 vol. 1 https://www.loc.gov/item/sanborn00817_004/ (sheets 63-65, 79-92), 1915 vol. 2 https://www.loc.gov/item/sanborn00817_005/ (156, 158), 1915-Jan 1950 vol. 1 https://www.loc.gov/item/sanborn00817_008/ (same scans as _006) and vol. 2 https://www.loc.gov/item/sanborn00817_007/ (same scans as _009). Georeferenced on County of Santa Clara parcel property lines (Parcels Public View, April 2026) and Overture road centrelines (`pipeline/sanborn_trace_southbay.py`, control in `data/manual/sanborn/control/san_jose/`).
- `data/raw/overture/2026-10-21.0/roads_southbay_core.parquet`: Overture Maps transportation segments, release 2026-10-21.0, all road classes for downtown San José, old Santa Clara and Palo Alto University Ave (ODbL; (c) OpenStreetMap contributors, Overture Maps Foundation) - street crossings / lines for the San José Sanborn control.
- San José clearance dates in `data/manual/redevelopment_areas.csv` (`sj_*` rows): Park Center Project Building Survey finding aid, History San José (blight 1960, plan 1961, groundbreaking 1968), https://oac.cdlib.org/findaid/ark:/13030/c84m9bw5/; Route 87 history, https://www.cahighways.org/ROUTE087.html; I-280 opening (mid-1972), https://www.interstate-guide.com/i-280-ca/ and SJSU Mineta Transportation Institute "Beneath I-280" (2024), https://transweb.sjsu.edu/research/2304-Freeways-Neighborhoods-Redevelopment; Heinlenville, https://en.wikipedia.org/wiki/Heinlenville; Market Street Chinatowns, https://en.wikipedia.org/wiki/Chinatowns_in_San_Jose,_California; convention centre, https://en.wikipedia.org/wiki/San_Jose_Convention_Center.
- `data/manual/sanborn/oakland_west_{1912,1951}.geojson`, `oakland_downtown_{1912,1951}.geojson`, their `*_tracks.geojson` and `*_coverage.geojson` + `README_oakland.md`: West Oakland and downtown Oakland building footprints and track centrelines (7th St corridor, Main Post Office / West Oakland BART blocks, Cypress St corridor, Acorn, City Center, Convention Center, I-980 edge) traced from the Library of Congress Sanborn Fire Insurance Maps of Oakland, California (public domain, "Library of Congress, Geography and Map Division, Sanborn Maps Collection"): 1911-1912 vol. 1 https://www.loc.gov/item/sanborn00727_005/ (sheets 52, 57, 71, 77, 79-82, 84-86, 92, 95-100, 102) and its corrected state 1912-Nov 1951 vol. 1 https://www.loc.gov/item/sanborn00727_015/ (same sheets). Georeferenced on Alameda County parcel property lines (`alameda_county_2021`) and Overture road centrelines (`pipeline/sanborn_trace_eastbay.py`, control in `data/manual/sanborn/control/oakland/`); `modern_overlap` against `overture_region5` (ODbL).
- `data/raw/overture/2026-10-21.0/roads_oakland_sanborn.parquet`: Overture Maps transportation segments, release 2026-10-21.0, `subtype = road`, all classes in (-122.335, 37.780, -122.245, 37.840) (ODbL; (c) OpenStreetMap contributors, Overture Maps Foundation) - street crossings / lines for the Oakland Sanborn control and the `oak_*` clearance rings.
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
Airport outlines and runway / taxiway / apron features (OSM centrelines buffered to typical widths) from Overture release 2026-10-21.0 (`region_airports.parquet`), ODbL. Opening years per airport in `data/tables/airports.csv` (source URL per row: Wikipedia articles, county / city airport history pages, militarymuseum.org; rows without a URL are estimates and say so); undated small fields default to 1950 (`estimated`).

### `land_not_before` (manual)
- File: `data/manual/land_not_before.geojson`
- Treasure Island: built 1936–37 on the Yerba Buena Shoals for the 1939 Golden Gate International Exposition — https://en.wikipedia.org/wiki/Treasure_Island,_San_Francisco . Outline from TIGER.

### `fire_1906` (manual research)
- Files: `data/manual/fire_1906_boundary.csv`, `fire_1906_unburned_islands.csv`, `fire_1906_README.md` (sources per vertex)

### Tables
- `data/tables/population.csv`, `eras.csv`, `events.csv`, `landmarks.csv` — every row carries its `source_url`.

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
- `san_jose_hri` — City of San José Historic Resources Inventory (`TRUEYR`, `ESTIMATEDYR`, demolished / moved flags, architect), https://geo.sanjoseca.gov/server/rest/services/OPN/OPN_OpenDataService/MapServer/406 — City of San José open data (no-warranty disclaimer).
- `ca_ohp_berd` — California Office of Historic Preservation, Built Environment Resource Directory, county CSVs (export 2026-02-02; construction years, NR/CR status codes), https://ohp.parks.ca.gov/?page_id=30338 — State of California (OHP Conditions of Use); located by APN / address.
- `osm_start_date` — OpenStreetMap buildings tagged `start_date` / `construction_date` (Overpass API; download pending — Overpass unreachable 2026-11-08) — ODbL.
- `tiger2024_place` — US Census TIGER/Line 2024 places, California (https://www2.census.gov/geo/tiger/TIGER2024/PLACE/tl_2024_06_place.zip) — public domain; city / CDP names for the coverage report.
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

#### Other dated facts (per row / feature in the files)
- Lake Merritt, Oakland estuary, Tidal Canal: Wikipedia "Lake Merritt", "Oakland Estuary"; oaklandgeology.com (tidal canal history); HMdb Tidal Canal marker; Alameda Post. Reservoir / lake dam years: Wikipedia articles per reservoir (URL per row). Farm-district eras: Broek 1932; Hayward Area Historical Society (agricultural history); Contra Costa County Historical Society; East Contra Costa Historical Society (Brentwood); NPS Point Reyes ranching history; Pleasanton Weekly (hops); Wikipedia articles cited per feature.

## Sources checked but not yet usable from the build environment
- SFEI EcoAtlas web services (https://www.sfei.org/) — behind a bot check; the poster PDF was supplied by hand and the GIS compilation downloads directly.
- OpenHistoricalMap (https://www.openhistoricalmap.org/) — API behind a bot check.
- Geofabrik / Overpass OSM extracts — network timeouts; Overture covers the OSM data needed so far.
- Census API (ACS B25034) — now requires a (free) key; needed for Phase 5 imputation.
- Alameda County Assessor property characteristics (sold, not on the open-data portal), Marin County Assessor roll (per-parcel lookup only; GIS server behind Cloudflare), San Mateo County roll characteristics (not published) — public copies / FEMA-Lightbox used instead (see `data/research/region_buildings.md`).
