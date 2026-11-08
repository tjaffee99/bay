# Five-county buildings: footprints, construction years, heights, historic records

Research for Phase 5 (Marin 041, Contra Costa 013, Alameda 001, San Mateo 081, Santa Clara 085).
Compiled 2026-11-08. Script: `pipeline/download_region.py`
(`overture | years | osm | heights | normalise | coverage`, each cached / idempotent).
Reports: `data/interim/reports/region5_overture.json`, `region_years_sources.json`,
`region_years_hist.json` + `region_years_hist.png`, `region_years_coverage.json`.

Goal: "accurate historic data and buildings just like SF" — real footprints, real years where
records exist, imputation only where they don't. Bottom line:

| County | Footprints | Year from a public official roll | + public copy of the roll | + FEMA/Lightbox (commercial-derived) | Fallback HISDAC FBUY cell |
|---|---:|---:|---:|---:|---:|
| Santa Clara | 603,169 | **94.8 %** | 94.8 % | 95.0 % | 96.1 % |
| Contra Costa | 388,900 | **94.1 %** | 94.1 % | 95.6 % | 95.4 % |
| Alameda | 517,755 | 37.2 % | **91.4 %** | 94.3 % | 96.9 % |
| San Mateo | 235,581 | 20.5 % | 22.4 % | **86.2 %** | 96.6 % |
| Marin | 115,638 | 0 % | 0 % | **82.1 %** | 92.4 % |
| **Total** | 1,861,043 | 63.3 % | 78.7 % | 93.0 % (93.4 % of footprints ≥ 40 m²) | 96.0 % |

("Footprint gets a year" = the footprint's point-on-surface lies in a parcel with a year, or a
building/historic point with a year lies inside the footprint. Shares are of all Overture
footprints incl. sheds/garages; the remaining 7 % are mostly outbuildings on parcels whose year
went to the main building, open-space/exempt parcels and footprints straddling parcel lines.)

---

## 1. Footprints — Overture Maps 2026-10-21.0

`s3://overturemaps-us-west-2/release/2026-10-21.0/theme=buildings/type={building,building_part}`,
bbox of the five TIGER 2024 county outlines (`data/raw/tiger/tl_2024_us_county.zip`,
STATEFP 06), then each feature is assigned to a county by `ST_PointOnSurface` in the county
polygon (TIGER outlines include each county's share of the bay, so piers and fill count).
Same anonymous-S3 DuckDB method as `download_overture.py`.

Files (`data/raw/overture/2026-10-21.0/`):
* `region5_building.parquet` — 1,861,043 buildings, 276 MB
* `region5_building_part.parquet` — 3,763 OSM 3D parts (Santa Clara 2,464, Alameda 810, San Mateo 366, Marin 76, Contra Costa 47)

Columns: `id, [building_id | has_parts, subtype, class], name, level, is_underground, height,
min_height, num_floors, num_floors_underground, min_floor, roof_shape, roof_height,
roof_direction, roof_orientation, facade_color, facade_material, roof_color, roof_material,
source_dataset, source_record, source_update_time, source_confidence (ML),
height_source (dataset of the height property, NULL = same as geometry), floors_source,
px, py (point on surface), countyfp, county, geometry`.

| County | Buildings | OSM | Microsoft ML | Esri Community Maps | with height | height: OSM tag | height: USGS LiDAR (Overture) | height: MS ML estimate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Santa Clara | 603,169 | 94.1 % | 5.2 % | 0.7 % | 94.8 % | 52.4 % | 31.9 % | 10.5 % |
| Alameda | 517,755 | 90.7 % | 9.3 % | – | 69.3 % | 0.03 % | 0.8 % | 68.5 % |
| Contra Costa | 388,900 | 41.6 % | 58.4 % | – | 81.6 % | 0.01 % | – | 81.6 % |
| San Mateo | 235,581 | 96.9 % | 3.1 % | – | 77.9 % | 2.1 % | 11.1 % | 64.7 % |
| Marin | 115,638 | 78.0 % | 2.4 % | 19.5 % | 70.4 % | 0.03 % | – | 70.4 % |

Caveats: Contra Costa is majority Microsoft ML footprints (blobby outlines, no parts).
Microsoft heights are model estimates, not LiDAR; Overture's "USGS Lidar" heights (per-feature
`height_source`) are measured. `num_floors` is rare (≤ 2.3 %). Licence ODbL
("© OpenStreetMap contributors, Overture Maps Foundation"; Microsoft ML Buildings ODbL; Esri
Community Maps per Overture attribution).

---

## 2. Construction-year sources

Raw downloads: `data/raw/region_years/<source>/<source>.parquet` (GeoParquet EPSG:4326, ArcGIS REST
paged by object id) + `<source>.source.json` (URL, query, fields, date, layer copyright/description).
**Owner names and mailing addresses were never requested** (field filter `PERSONAL` in the script);
situs (property) addresses kept for matching.

What exists, county by county (searched: county / city open-data portals, ArcGIS Online/Hub,
Socrata catalogs, county GIS servers):

* **Santa Clara** — county-wide public roll year. Cities add stories/units/effective year.
* **Contra Costa** — county-wide public roll year (+ stories/units/effective year from the fire district copy).
* **Alameda** — the county **sells** building characteristics (Assessor records page: property
  characteristics are developed for assessment and "may be purchased", bulk roll data sold per
  fee schedule — https://www.acgov.org/assessor/resources/records.htm); no official free download. But several public copies exist: a whole-county
  2021 copy (MNS Engineers) and current city/district copies (Union City Planning covering
  Fremont/Hayward/Union City/Newark, Zone 7 Water Agency covering the Tri-Valley, Berkeley 2017,
  Albany, Emeryville). Oakland, San Leandro, Alameda city, Castro Valley, Piedmont: only the 2021 copy.
* **San Mateo** — no county-wide public year (county layer has `OFFICEYEARBUILT` for 843 office
  parcels only). City copies: San Mateo, Belmont, San Bruno, Portola Valley, Hillsborough
  (consultant), South SF (CoreLogic). Redwood City, Daly City, Menlo Park, Burlingame, San Carlos,
  Foster City, Pacifica, Millbrae, East Palo Alto, unincorporated: nothing public.
* **Marin** — nothing public (gis.marincounty.gov refuses automated requests (Cloudflare) from the
  build environment; the open-data parcel layers on ArcGIS Online carry no characteristics; the
  Assessor offers a per-parcel tax-roll lookup only, https://apps.marincounty.gov/TaxRollSearch). Third-party: Boundary
  Solutions 2019 parcels (YEAR_BUILT) at Princeton — licensed/restricted, not used.
* **All five** — FEMA Region 9 "Property – Structures – Static – Point – Building Type (R9)":
  a building point per Microsoft/USA-Structures footprint with Lightbox SmartParcel attributes
  (YR_BLT, YR_BLT_EFFECT, STORIES_NUMBER, construction, exterior wall, roof cover). Publicly
  readable, no licence stated; attributes are from a commercial vendor (see §7).

### Source table

| id | Publisher / URL | Rows (with year) | Vintage | Year field (+ others) | Licence / terms |
|---|---|---:|---|---|---|
| `contra_costa_ccmap` | Contra Costa County DoIT, CCMAP "Assessment Parcels" — https://gis.cccounty.us/arcgis/rest/services/CCMAP/Assessment_Parcels_ArcPro/MapServer/0 | 387,976 (354,902) | 2026 (item modified 2026-04) | `YR_HS_BLT` (year house built; 340k), `YR_BUILT` (other improvements; 15k) — coalesced; `USE_CODE/Description`, `IMP_VAL`, `BLDG_SQFT` | public county service; county states the assessor parcel data is "free to download", updated monthly (https://www.contracosta.ca.gov/552/Maps-Property-Information). No explicit licence. |
| `contra_costa_cccfpd` | Contra Costa County Fire Protection District "Assessor Parcels" — https://services6.arcgis.com/CmHj285GYxHhHnTo/arcgis/rest/services/Assessor_Parcels/FeatureServer/0 | 387,859 | 2026-09-09 | `BLD_EFFYR`, `STORIES` (12k), `UNITS`, `NBR_BLDNGS` — joined to CCMAP by APN | public agency layer, no licence stated |
| `santa_clara_county` | County of Santa Clara Dept. of Planning & Development, "Parcels Public View" — https://services2.arcgis.com/tcv2cMrq63AgvbHF/arcgis/rest/services/Parcels_Public_View/FeatureServer/0 | 505,028 (474,640) | 2026-04 | `Year_Built` only | item licence: "There are no Use Constraints" (+ no-warranty disclaimer) |
| `sunnyvale` | City of Sunnyvale Property_Layer — https://services.arcgis.com/IBwZaktrBtZuqQmg/arcgis/rest/services/Property_Layer/FeatureServer/0 | 33,809 (33,389) | current | `YearBuilt`, `Stories`, `CountyUnits`, `Buildings`, `Heritage` | city layer, none stated |
| `milpitas` | City of Milpitas Parcel Owner View — https://services8.arcgis.com/OPmRdssd8jj0bT5H/arcgis/rest/services/Parcel_Owner_View/FeatureServer/0 | 20,383 (19,790) | current | `YEAR_BUILT`, `Year_Built_Eff`, `NO_OF_FLOORS`, `NO_OF_UNITS` | "© City of Milpitas 2020" |
| `saratoga` | Town of Saratoga Parcels — https://services3.arcgis.com/rExmJXzTylAKURvh/arcgis/rest/services/Parcels/FeatureServer/0 | 12,860 (12,036) | current | `YEAR_BUILT`, `EFFECTIVE_YR_BLT`, `NUMBER_OF_FLOORS`, `NUMBER_OF_UNITS`, `IsHistoricSite` | none stated |
| `los_gatos` | Town of Los Gatos Parcels — https://services3.arcgis.com/JAU7IM34hqT9y9ew/arcgis/rest/services/Parcels/FeatureServer/0 | 18,991 (17,419) | current | as Saratoga | none stated |
| `alameda_county_2021` | Copy of the Alameda County assessor roll + characteristics by MNS Engineers (AGOL "Alameda_Co_Pcls") — https://services9.arcgis.com/l0PUGx9JqRxaCPsG/arcgis/rest/services/Alameda_Co_Pcls/FeatureServer/0 | 483,381 (430,187) | 2021-04 | `YearBuilt`, `EffectiveY`, `Stories` (93 %), `Units`, `Buildings`, `UseCode` | third-party public copy, no licence stated; underlying characteristics are sold by the Alameda County Assessor |
| `alameda_south_2026` | City of Union City Planning "UC_Parcels_07_2026" (covers Fremont, Hayward, Union City, Newark, Sunol) — https://services7.arcgis.com/T3LbxamSmhpjBppB/arcgis/rest/services/UC_Parcels_07_2026_view/FeatureServer/12 | 108,353 (100,464) | 2026-07 | `YRBLT`, `YREFF`, `STORIES`, `UNITS`, `BLDGS`, `USETYPE` (ParcelQuest-style schema) | city layer, none stated |
| `alameda_trivalley_zone7` | Zone 7 Water Agency "Parcels LayFH" (Livermore, Pleasanton, Dublin, east county) — https://services6.arcgis.com/yGWezgaq4oIlwApY/arcgis/rest/services/Parcels_LayFH/FeatureServer/0 | 91,655 (73,350) | current | `YrBuilt`, `EffYr`, `Stories`, `NumUnits`, `Bldgs`, `WallHt` | layer credit "Alameda County Assessor's Office, Contra Costa County, Lynx Technologies"; none stated |
| `berkeley` | City of Berkeley "TaxParcel" — https://services1.arcgis.com/IYiCpZoSIq9lAxi8/arcgis/rest/services/TaxParcel/FeatureServer/0 | 28,870 (25,428) | 2017 | `YearBuilt`, `EffectiveY`, `Stories`, `Units`, `Buildings` | none stated |
| `albany` | City of Albany ParcelsWeb — https://services2.arcgis.com/3X7VMY0UAVT63A6d/arcgis/rest/services/ParcelsWeb/FeatureServer/0 | 6,014 (5,503) | current | `YrBuilt`, `EffYr`, `Stories`, `NumUnits` | none stated |
| `emeryville` | City of Emeryville Parcels — https://services3.arcgis.com/ljOdqLVbHpS7dOJQ/arcgis/rest/services/Parcels_Emeryville/FeatureServer/0 | 4,193 (3,254) | current | `YrBuilt`, `EffYr`, `Stories`, `NumUnits` | none stated |
| `san_mateo_county_office` | County of San Mateo ACTIVE_PARCELS_APN — https://gis.smcgov.org/maps/rest/services/Common/ACTIVE_PARCELS_APN/FeatureServer/0 (`OFFICEYEARBUILT IS NOT NULL`) | 843 (704) | current | `OFFICEYEARBUILT` (office buildings only) | county layer, none stated |
| `san_mateo_city` | City of San Mateo EnerGov TaxParcel — https://services2.arcgis.com/g26Y0m7OCdjU0ObA/arcgis/rest/services/EnerGov_Query_AGOL/FeatureServer/2 | 29,897 (27,972) | current | `YEAR_BUILT_MANUFACTURED`, `EFFECTIVE_YEAR`, `RENOVATE_YEAR`, `STORIES`, `NO_OF_UNITS`, `CONSTRUCTION_CLASS`, `WALL_HEIGHT` | none stated |
| `belmont` | City of Belmont Property Lines — https://maps.belmont.gov/arcgis/rest/services/ParcelViewer/ZoningLandUse/MapServer/4 | 8,763 (7,973) | current | `YRBLT`, `YREFF`, `STORIES`, `UNITS`, `BLDGS` | none stated |
| `san_bruno` | City of San Bruno Parcels — https://services2.arcgis.com/iLsFVn6d1pmqKEfA/arcgis/rest/services/Parcels/FeatureServer/0 | 14,623 (12,521) | current | `YearBuilt`, `RENOVATE_YEAR` | none stated |
| `portola_valley` | Town of Portola Valley Parcels — https://services8.arcgis.com/LRqASGpv7gPaTEUL/arcgis/rest/services/Parcels/FeatureServer/0 | 1,817 (1,362) | current | `YEAR_BUILT_MANUFACTURED`, `EFFECTIVE_YEAR`, `STORIES`, `NO_OF_UNITS` | none stated |
| `hillsborough` | Town of Hillsborough parcels (housing-element consultant HLA) — https://services5.arcgis.com/74bZbbuf05Ctvbzv/arcgis/rest/services/Town_of_Hillsborough_Parcels/FeatureServer/0 | 4,097 (3,736) | 2022 | `hl_yearbuilt` | third-party, none stated |
| `south_sf_corelogic` | "SSF_Corelogic_Parcels" (consultant Strategic Economics) — https://services6.arcgis.com/SAzG4Xt2MtnnJdpJ/arcgis/rest/services/SouthSFParcelAnalysis/FeatureServer/2 | 16,632 (16,539) | c.2018 | `YR_BLT`, `EFF_YR_BLT`, `STORY_NBR`, `CONSTR_TYP` | **CoreLogic (commercial)** — validation only |
| `fema_r9_res` / `_nonres` / `_mixed` | FEMA Region 9, "Property – Structures – Static – Point – Building Type (R9)" (item 712097874f5740a3a8d1865cab585f84) — https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/Property_Structures_Static_Points_Building_Type_R9/FeatureServer/{5,7,6} | 1,386,507 / 106,271 / 6,702 (1,363,640 / 57,348 / 6,157) | years ≤ 2020 (item 2024-04) | `YR_BLT`, `YR_BLT_EFFECT`, `STORIES_NUMBER` ("1+B"), `CONSTRUCTION_CODE_DESC`, `EXTERIOR_WALL_DESC`, `ROOF_COVER_DESC`, `PARCEL_APN` | access info "FEMA, Microsoft, US Census Bureau, Lightbox"; no licence; **attributes from Lightbox SmartParcels (commercial)** |
| `marin_parcels` | Marin County CDA/Assessor parcels (open data) — https://services6.arcgis.com/T8eS7sop5hLmgRRH/arcgis/rest/services/Parcels/FeatureServer/0 | 96,239 (no years) | current | `Parcel` (APN) — FEMA years attached by APN → `fema_r9_parcel` | none stated |
| `san_mateo_parcels` | County of San Mateo ACTIVE_PARCELS_APN (all) | 235,492 (no years) | current | `APN`, situs — FEMA years attached by APN → `fema_r9_parcel` | none stated |
| `san_jose_hri` | City of San José Historic Resources Inventory — https://geo.sanjoseca.gov/server/rest/services/OPN/OPN_OpenDataService/MapServer/406 | 4,849 (4,364) | 2023 | `TRUEYR` (researched), `ESTIMATEDYR` ("c1913"), `DEMOLISHED` (56), `MOVED` (86), `ARCHITECT`, `BUILDER`, `ARCHITECTURALSTYLE` | City of San José open data (free; no-warranty disclaimer) |
| `ca_ohp_berd` | California Office of Historic Preservation, Built Environment Resource Directory — https://ohp.parks.ca.gov/?page_id=30338 (`/pages/1068/files/<County>.csv`) | 30,733 resources (26,918 with a year; 18,936 located) | export 2026-02-02 | `Construction Year(s)`, `Evaluation Info` (NR/CR status codes), `Attributes` (HP codes), `Parcel Num`, address — no coordinates; located by APN (12,131) or address (6,805) | State of California public data (OHP Conditions of Use) |
| `osm_start_date` | OpenStreetMap buildings with `start_date` / `construction_date` via Overpass (0.25° tiles, cached in `data/raw/region_years/osm_start_date/tiles/`) | **not downloaded**: all Overpass instances timed out or reset during this session (one county answered once: Marin, 155 buildings) — rerun `python download_region.py osm`, then `normalise` and `coverage` (the stages already read it) | — | `start_date` | ODbL |

Searched and **not usable / not found**: Alameda County open-data parcels (no characteristics),
Oakland Parcels Public (6 fields), Hayward Area Parcels (characteristics fields are present but
null — Hayward is covered by `alameda_south_2026`), Marin "PARCEL"/"PARCEL_POINT", Marin Socrata
(permits only), San Mateo Datahub (no parcel characteristics), Redwood City / Burlingame / Foster
City / Menlo Park / Daly City / SSF open parcel layers (no year), Novato / Larkspur parcel layers
(token required), Boundary Solutions 2019 Marin (restricted, Princeton), commercial sellers
(ReportAll, Regrid, LandRecords, ATTOM — paid). Building permits (Berkeley 2010–2021 new-building
permits, Marin County building permits on Socrata, San José) exist and can date recent
construction, not downloaded.

---

## 3. Normalised table — `data/interim/region_years.parquet`

3,300,054 rows (3,300,045 with a plausible year), 176 MB, GeoParquet EPSG:4326. One row per
source record (parcel polygon, building point or historic point); **sources overlap on purpose**
— the consumer picks per footprint by `rank` (see §4 and §8).

Columns: `src, rank (0 historic record · 1 current official roll · 2 older / third-party copy ·
3 commercial-derived), licence (public | third_party_copy | commercial | odbl), kind (parcel |
building_point | historic_point), vintage, apn, year_raw (as published), year_built (Int16, cleaned),
year_flag (ok | spike | suspect_pre1850 | implausible_early | future | range), confidence (exact |
estimated), eff_year, remodel_year, stories, units, n_buildings, use, address, name, material /
construction / roof (FEMA), demolished / moved (HRI), countyfp, county, place (TIGER 2024 place /
CDP), incorporated, berd_flag / is_building / berd_status / located_by (BERD), geometry`.
Parcel polygons simplified to ~0.2 m.

Cleaning (same rules as SF, `CLAUDE.md` "Year cleaning"):
* zero / blank / missing → dropped (counted per source below);
* < 1769 → `implausible_early` (NULL); > 2026 → `future` (NULL); 1769–1849 → `suspect_pre1850`
  (kept; a few adobes are real, most are typos);
* **spike years**: a multiple of 5 before 1950 with count > 4× the median of the non-round years
  within ±10 y (and > 20) → `spike`, confidence `estimated` (treat as an upper bound, as SF's 1900).
* BERD ranges: span ≤ 10 y → completion year; wider → first year + `range` (period of significance,
  not a construction date).

| Source | Rows | zero/missing | with year | spike years flagged | median | pre-1906 | eff. year | stories |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| santa_clara_county | 505,028 | 30,388 | 474,640 | 1880,85,90,95,1900,10,20,25 (7,596 rows) | 1971 | 1.1 % | – | – |
| alameda_county_2021 | 483,381 | 53,190 | 430,187 | 1870–1900 every 5 y (5,004) | 1965 | 2.6 % | 99.7 % | 93.3 % |
| contra_costa_ccmap (+cccfpd) | 387,976 | 33,071 | 354,902 | 1880, 1890, 1900 (397) | 1977 | 0.3 % | 95.8 % | 2.9 % |
| alameda_south_2026 | 108,353 | 7,889 | 100,464 | 1900, 1925 (165) | 1978 | 0.2 % | 99.7 % | 91.3 % |
| alameda_trivalley_zone7 | 91,655 | 18,303 | 73,350 | 1890, 95, 1900, 10 (263) | 1987 | 0.4 % | 99.8 % | 94.9 % |
| sunnyvale | 33,809 | 420 | 33,389 | 1900–1930 (235) | 1963 | 0.1 % | – | 99.1 % |
| berkeley (2017) | 28,870 | 3,442 | 25,428 | 1890, 1895 (173) | 1925 | 7.4 % | 99.6 % | 95.3 % |
| san_mateo_city | 29,897 | 1,925 | 27,972 | 1900 (24) | 1954 | 0.6 % | 76 % | 99.5 % |
| milpitas | 20,383 | 593 | 19,790 | – | 1981 | 0.1 % | 100 % | 99.5 % |
| los_gatos | 18,991 | 1,572 | 17,419 | 1900–1925 (612) | 1965 | 2.2 % | 99.9 % | 98.8 % |
| south_sf_corelogic | 16,632 | 93 | 16,539 | 1900 (24) | 1956 | 0.5 % | 6 % | 71 % |
| san_bruno | 14,623 | 2,102 | 12,521 | 1910, 1925 (165) | 1958 | 0.1 % | – | – |
| saratoga | 12,860 | 824 | 12,036 | 1900, 1910 (88) | 1966 | 0.7 % | 100 % | 99.6 % |
| belmont | 8,763 | 790 | 7,973 | – | 1960 | 0.1 % | 67 % | 99.2 % |
| albany | 6,014 | 511 | 5,503 | 1910, 1925 (391) | 1936 | 0.4 % | 99.8 % | 92.1 % |
| emeryville | 4,193 | 939 | 3,254 | 1900, 1915, 1925 (110) | 1981 | 2.9 % | 99.6 % | 66 % |
| hillsborough | 4,097 | 361 | 3,736 | – | 1960 | 0.7 % | – | – |
| portola_valley | 1,817 | 455 | 1,362 | – | 1965 | 0.5 % | 66 % | 99.6 % |
| san_mateo_county_office | 843 | 139 | 704 | – | 1982 | 1.6 % | – | – |
| fema_r9_res | 1,386,507 | 22,867 | 1,363,640 | 1870–1895 every 5 y (3,431) | 1963 | 1.4 % | 35 % | 84 % |
| fema_r9_nonres | 106,271 | 48,923 | 57,348 | 1880–1930 (2,361) | 1970 | 2.1 % | 26 % | 85 % |
| fema_r9_mixed | 6,702 | 545 | 6,157 | – | 2008 | 0.0 % | 18 % | 17 % |
| fema_r9_parcel (Marin 70,234 + San Mateo 168,415 parcels by APN) | 238,649 | 10,218 | 228,431 | 1880, 1890, 1900 (692) | 1957 | 0.9 % | 22 % | 29 % |
| san_jose_hri | 4,849 | 485 | 4,364 | – | 1918 | 25.7 % | – | – |
| ca_ohp_berd (located) | 18,936 | – | 18,936 | (308 `range`) | – | – | – | – |

Round-number heaping beyond the flagged spikes (mean count at multiples of 5 ÷ other years):
1870–1905: 3–6× in every assessor source (placeholders, as in SF); **1905–1930: 1.7× Alameda
2021, 3.1× Santa Clara and Union City 2026**, 1.2–1.8× elsewhere (partial placeholders — treat
pre-1930 round years as `estimated`); after 1930 ≈ 1×. Alameda 2021 has years up to 2051 and
effective years down to 1010 (nulled). FEMA years stop at 2020; Berkeley at 2016; Alameda 2021
at 2021 — newer buildings need the current layers / Overture snapshot diff / permits.
Histogram per source: `data/interim/reports/region_years_hist.png`.

**Pre-1906 survivors**: unlike SF there was no citywide fire, so pre-1906 assessor years are
plausible (Berkeley 7.4 %, San José HRI 26 %); the risk is the opposite — placeholder spikes
(1880–1900) and parcel years that date the oldest *remaining* structure.

---

## 4. Coverage — `data/interim/reports/region_years_coverage.json`, `data/interim/region5_footprint_years.parquet`

Join: footprint point-on-surface (`px, py`) within parcel polygons (most common year when condo
parcels stack); building/historic points within footprint polygons (earliest year when several).
Classes, in priority order per footprint (BERD restricted to building resources with a
construction date, not `range`; OSM pending):
`public` (official current rolls; newest city layer first, then county roll), `third_party`
(alameda_county_2021, hillsborough), `commercial` (FEMA points, then FEMA-by-APN parcels, then
CoreLogic), `historic` (HRI, BERD, OSM). The per-footprint table has
`id, county, place, area_m2, year_<class>, src_<class>, spike_<class>, fbuy, has_height,
smc_lidar_height_m` — ready for the pipeline stage.

**Agreement** where two sources cover the same footprint: public roll vs FEMA/Lightbox — 98.5 %
same year, 98.9 % within 10 y (n = 957,608); Alameda 2021 copy vs FEMA — 99.1 % same; current
city layers vs Alameda 2021 — 99.6 % same. ⇒ FEMA/Lightbox carries the assessor's own year, so in
Marin / San Mateo it is a faithful stand-in for the roll (licence aside).

Major cities (share of Overture footprints with a year):

| County · city | Footprints | public roll | + public copy | + FEMA | ≥ 40 m², any |
|---|---:|---:|---:|---:|---:|
| Santa Clara · San José | 302,034 | 95.7 % | 95.7 % | 95.8 % | 95.9 % |
| Alameda · Oakland | 141,257 | 0 | 91.0 % (2021 copy) | 93.9 % | 93.9 % |
| Alameda · Fremont | 65,395 | 53.6 % | 92.6 % | 94.8 % | 95.4 % |
| Contra Costa · Richmond | 45,078 | 90.1 % | 90.1 % | 92.0 % | 92.6 % |
| Alameda · Hayward | 42,043 | 64.1 % | 89.0 % | 92.8 % | 93.7 % |
| Santa Clara · Sunnyvale | 41,772 | 96.6 % | 96.6 % | 96.7 % | 96.7 % |
| Santa Clara · Santa Clara | 39,715 | 94.9 % | 94.9 % | 95.1 % | 94.9 % |
| Contra Costa · Concord | 36,898 | 95.0 % | 95.0 % | 96.7 % | 97.1 % |
| Alameda · Berkeley | 36,160 | 90.6 % (2017) | 91.5 % | 96.2 % | 96.2 % |
| Alameda · San Leandro | 35,626 | 0 | 93.7 % | 95.9 % | 95.9 % |
| Alameda · Livermore | 30,968 | 92.9 % | 93.4 % | 95.0 % | 95.3 % |
| San Mateo · San Mateo | 27,771 | 92.4 % | 92.4 % | 94.3 % | 94.2 % |
| Alameda · Alameda | 27,443 | 0 | 89.8 % | 92.8 % | 93.0 % |
| Santa Clara · Palo Alto | 25,940 | 95.5 % | 95.5 % | 95.6 % | 96.2 % |
| San Mateo · Redwood City | 25,218 | 0.9 % | 0.9 % | 88.5 % | 88.4 % |
| San Mateo · Daly City | 24,480 | 0.1 % | 0.1 % | 70.3 % | 71.2 % |
| Marin · Novato | 19,517 | 0 | 0 | 87.7 % | 88.4 % |
| Marin · San Rafael | 18,808 | 0 | 0 | 85.3 % | 86.0 % |
| San Mateo · South San Francisco | 18,796 | 0.3 % | 0.3 % | 91.6 % | 91.6 % |
| Contra Costa · Walnut Creek | 18,747 | 91.3 % | 91.3 % | 93.9 % | 94.4 % |
| San Mateo · Menlo Park | 12,216 | 1.4 % | 1.4 % | 87.3 % | 87.3 % |
| San Mateo · Burlingame | 10,398 | 0.5 % | 0.5 % | 90.6 % | 90.3 % |
| Marin · Mill Valley | 6,584 | 0 | 0 | 83.2 % | 84.2 % |
| Marin · unincorporated | 13,799 | 0 | 0 | 58.1 % | 61.0 % |
| San Mateo · unincorporated | 10,462 | 0.6 % | 0.6 % | 52.5 % | 57.0 % |

(All places with ≥ 5,000 footprints: `region_years_coverage.json` → `by_place`.)

**Gaps and fallback.** Footprints with no year at all: 7 % (Marin 18 %, San Mateo 14 %, others
4–6 %); rural/unincorporated areas and Daly City are worst. HISDAC data in the repo:
`data/raw/hisdac/FBUY` only (first built-up year, 250 m, ZTRAX-derived, ≤ 2015; already used by
SF and the terrain). FBUY has a value under 96 % of all footprints and under most of the no-year
footprints (5.1 % of footprints are no-year-but-FBUY; Marin 12.6 %, San Mateo 11 %).
Not in the repo but available from the same authors: HISDAC-US **BUPR / BUPL** (built-up
property records / locations per 250 m cell every 5 years, 1810–2020; BUPR v2
https://doi.org/10.7910/DVN/45B8IU, earlier versions doi:10.7910/DVN/YSWMDR and SJ213V — verify
before use) — they give the *distribution* of years inside a cell, a better imputation prior
than FBUY's single first year.

---

## 5. Heights

* Overture (above): Santa Clara 94.8 % (52 % OSM tags, 32 % USGS LiDAR), Contra Costa 81.6 %,
  San Mateo 77.9 % (11 % USGS LiDAR), Marin 70.4 %, Alameda 69.3 % — the rest are Microsoft ML
  estimates.
* Assessor `stories` (region_years): Alameda 2021 93 % of parcels, Union City 2026 91 %, Zone 7
  95 %, Santa Clara cities 99 %, San Mateo city 99.5 %, FEMA 84 %; Santa Clara county layer and
  CCMAP have none (CC: 2.9 % via the fire district).
* **San Mateo County "Building Footprints"** (County GIS, 229,298 polygons,
  `BLDGHEIGHT` in **feet** (median 14 ft), 99.7 % populated, `BASEELEV`; Esri 3D-basemap schema,
  source not documented on the layer — check against Overture's USGS LiDAR heights) —
  https://services.arcgis.com/yq3FgOI44hYHAFVZ/arcgis/rest/services/Building_Footprints/FeatureServer/0 —
  downloaded to `data/raw/region_heights/san_mateo_county_footprints/`; matches 92 % of San Mateo's
  Overture footprints (`smc_lidar_height_m` in the footprint table). No licence stated.
* **Marin County "Building Footprints"** (113,271, `SourceDateYear` mostly 2004 = Vargis 2004
  10 cm orthophoto; base/peak elevation fields are empty) —
  https://services6.arcgis.com/T8eS7sop5hLmgRRH/arcgis/rest/services/Building_Footprints/FeatureServer/0 —
  downloaded to `data/raw/region_heights/marin_county_footprints/`. **No heights**, but useful as a
  dating constraint: a building in this layer stood in 2004 (like SF's 2016 snapshot).
* Not downloaded (city scale, attribute names in brackets): City of San José building footprints
  (BLDGHEIGHT, BLDGELEV; ~324k; seen only as SJSU student copies, e.g.
  https://services8.arcgis.com/A76GjgcBUTTcwFGS/arcgis/rest/services/Building_Footprint3/FeatureServer/0 —
  find the city original), City of Santa Clara "Building Structures 2023" (BLDGHEIGHT, EAVEHEIGHT;
  34k; https://map.santaclaraca.gov/maps/rest/services/LAYERS/BuildingStructureCache/MapServer/0),
  Mountain View BuildingFootprint (NUMSTORIES, BLDGHEIGHT; 24k;
  https://maps.mountainview.gov/arcgis/rest/services/Public/BuildingFootprint/MapServer/0),
  Cupertino (BLDG_HEIGHT, **Year_Built**; 22k; https://gis.cupertino.org/cupgis/rest/services/Public/AmazonData/MapServer/9),
  City of San Mateo Simple_Buildings (NUMSTORIES, BLDGHEIGHT; 46k;
  https://services2.arcgis.com/g26Y0m7OCdjU0ObA/arcgis/rest/services/Simple_Buildings/FeatureServer/0),
  Hayward Building Footprints (BldgHeight_* zonal stats; 77k;
  https://services3.arcgis.com/VRO5V8PH7DzSE6AU/arcgis/rest/services/Building_Footprints/FeatureServer/0),
  San Ramon Valley FPD (height; 94k;
  https://services3.arcgis.com/JpP1FSxc7q5Zn98M/arcgis/rest/services/Building_Footprints/FeatureServer/16),
  Pittsburg (Height, STORIES; 18k), UC Berkeley campus (BLDGHEIGHT; 475).
  FEMA USA Structures R9 points (HEIGHT from ORNL where LiDAR existed;
  https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/USAStructures_Region9_Point/FeatureServer/0,
  public domain) — region-wide alternative, not checked for coverage here.
* No county-wide LiDAR heights found for Alameda, Contra Costa, Marin; USGS 3DEP point clouds
  (public domain) would allow nDSM heights per footprint if ever needed.

---

## 6. Historic and vanished buildings

* **San José HRI** (above): 4,364 dated resources incl. 56 demolished and 86 moved — the only
  machine-readable lost-building list found.
* **OHP BERD**: 26,918 dated resources in the five counties (Alameda 14,062 — Oakland's survey is
  large), with NR/CR evaluation codes; 18,936 located to a parcel point (APN or address). Note
  BERD lists resources still surveyed, not demolitions; `is_building` from HP codes.
* Oakland Cultural Heritage Survey: no public GIS/download (OCHS holds permit ledgers; city lists
  landmarks with construction dates as PDFs). Berkeley, Alameda, Palo Alto inventories: PDFs.
* Contra Costa / Union City / FEMA layers do not keep demolished buildings (survivors only, as in SF).
* **Sanborn maps on loc.gov** (public domain; item ids `https://www.loc.gov/item/<id>/`;
  dates as catalogued; the 1948–52 items are probably updated re-issues of earlier volumes — check the item pages):
  * **Alameda Co.** — Oakland: 1889 `sanborn00727_001`; 1902 `_002`; 1903 `_003`, `_004`; 1911 `_006`, `_007`; 1912 `_005`, `_008`, `_009`; 1917-09 `_033`; 1925 `_011`, `_012`; 1926 `_013`; 1928 `_010`; 1929 `_014`; 1950 `_016`, `_020`, `_021.5`; 1951 `_015`, `_017`, `_018`, `_019`, `_021`, `_022`; 1952 `_023`–`_032`.
    Berkeley: 1894-05 `sanborn00419_001`; 1911 `_002`, `_003`; 1917-11 `_011`; 1929 `_004`–`_006`; 1950 `_007`–`_010`. East Berkeley 1890-04 `sanborn00517_001`.
    Alameda (city): 1897 `sanborn00374_001`; 1948 `_002`; 1950 `_003`. Bay Farm Island 1924-10 `sanborn00409_001`, `_002`.
    Hayward: 1888 `sanborn00586_001`, 1893 `_002`, 1896 `_003`, 1903 `_004`, 1907 `_005`, 1923 `_006`, 1950 `_007`.
    San Leandro: 1885 `sanborn00820_001`, 1890 `_002`, 1898 `_003`, 1907 `_004`, 1911 `_005`, 1917 `_006`, 1928 `_007`, 1950 `_008`.
    Livermore: 1884 `sanborn00640_001`, 1888 `_002`, 1893 `_003`, 1907 `_004`, 1917 `_005`, 1944 `_006`.
    Pleasanton: 1888 `sanborn00764_001`, 1893 `_002`, 1898 `_003`, 1903 `_004`, 1907 `_005`, 1943 `_006`.
    Elmhurst 1896 `sanborn00525_001`, 1905 `_002`. Fremont-area towns: Alvarado 1887–1944 `sanborn00381_001`–`_007`; Centerville 1887–1932 `sanborn00457_001`–`_006`; Irvington 1908/1926/1932 `sanborn00607_001`–`_003`; Mission San Jose 1897/1916/1932 `sanborn00690_001`–`_003`; Niles 1892–1944 `sanborn00718_001`–`_006`; Newark 1908/1925/1932 `sanborn00713_001`–`_003`; Decoto 1908/1926/1932 `sanborn00500_001`–`_003`; Sunol 1908/1929 `sanborn00875_001`, `_002`.
  * **Santa Clara Co.** — San José: 1884 `sanborn00817_001`; 1891 `_002`, `_003`; 1915 `_004`, `_005`; 1950 `_006`–`_009`. Santa Clara 1887 `sanborn00832_001`. Palo Alto 1895, 1897, 1901, 1904, 1908, 1924, 1949 `sanborn00747_001`–`_007`. Mayfield 1884–1945 `sanborn00677_001`–`_007`. Mountain View 1888–1943 `sanborn00706_001`–`_007`. Los Gatos 1884–1944 `sanborn00659_001`–`_008`. Campbell 1899–1935 `sanborn00444_001`–`_006`. Gilroy 1886, 1892, 1906, 1926, 1943 `sanborn00566_001`–`_005`. Sunnyvale 1908, 1911, 1930, 1943 `sanborn00874_001`, `_002`, `_003`, `_005`. Milpitas 1893/1908/1930 `sanborn00687_001`–`_003`. Morgan Hill 1908/1926/1941 `sanborn00703_001`–`_003`. Alviso 1908/1930 `sanborn00382_001`, `_002`. Cupertino 1920/1930 `sanborn00495_001`, `_002`. Los Altos 1926/1932 `sanborn00655_001`, `_002`. Saratoga 1918/1930 `sanborn00840_001`, `_002`.
  * **Contra Costa Co.** — Richmond 1903 `sanborn00787_001`, 1905 `_002`, 1909 `_003`, 1916 `_004`, 1930 `_005`, `_006`, 1950 `_008`, 1951 `_007`; Martinez 1884–1949 `sanborn00674_001`–`_007`; Concord 1891–1945 `sanborn00477_001`–`_008`; Walnut Creek 1891–1943 `sanborn00916_001`–`_006`; Antioch 1884–1948 `sanborn00387_001`–`_009`; Pittsburg 1911–1949 `sanborn00760_001`–`_004`; Crockett 1899–1945 `sanborn00491_001`–`_006`; also Avon, Bay Point, Black Diamond (1891–1907 `sanborn00425_001`–`_005`), Brentwood, Byron, Danville, El Cerrito 1926, New York Landing 1884, Oakley, Pinole, Port Chicago 1952, Port Costa 1889, Rodeo, Stege 1912.
  * **Marin Co.** — San Rafael 1887-05 `sanborn00828_001`, 1894-12 `_002`, 1907 `_002.5`, 1924-04 `_004`, 1950-04 `_005`; Sausalito 1887–1945 `sanborn00843_001`–`_007`; Mill Valley 1903/1908/1924/1948 `sanborn00685_001`–`_004`; Novato 1911/1924/1943 `sanborn00725_001`–`_003`; San Anselmo 1909–1950 `sanborn00804_001`–`_005`; Tiburon 1891–1928 `sanborn00886_001`–`_005`; Larkspur, Corte Madera, Fairfax, Ross, Bolinas, Point Reyes, Tomales.
  * **San Mateo Co.** — San Mateo 1888–1950 `sanborn00824_001`–`_007`; Redwood City 1884–1950 `sanborn00783_001`–`_007`; Menlo Park 1888–1944 `sanborn00680_001`–`_007`; Burlingame 1908/1913/1921/1949 `sanborn00437_001`–`_004`; Daly City 1915/1918/1927/1950 `sanborn00497_001`–`_004`; South San Francisco 1910/1925/1950 `sanborn00863_001`–`_003`; San Bruno 1913–1949 `sanborn00806_001`–`_004`; Colma, Millbrae, San Carlos, Belmont, Atherton, Half Moon Bay, Pescadero, Baden, Beresford.
  Full list with dates: 362 items (Alameda 113, Contra Costa 78, Santa Clara 68, San Mateo 59, Marin 44),
  queried from `https://www.loc.gov/collections/sanborn-maps/?fo=json&fa=location_state:california|location_county:<county>`.

---

## 7. Licences and risk

| Class | Sources | Use |
|---|---|---|
| Open / no constraints | Santa Clara County Planning ("no Use Constraints"); OHP BERD; TIGER (public domain); OSM (ODbL); Overture (ODbL) | ship |
| Public government layers, no licence stated | CCMAP + CCCFPD, city layers (Sunnyvale, Milpitas, Saratoga, Los Gatos, Union City, Zone 7, Berkeley, Albany, Emeryville, San Mateo, Belmont, San Bruno, Portola Valley), San Mateo / Marin county parcels and footprints, San José HRI | ship with attribution ("County of X Assessor via City of Y"); construction years are facts |
| Third-party public copies | alameda_county_2021 (MNS Engineers), hillsborough (HLA) | the Alameda County Assessor sells characteristics; the copy is publicly shared without terms. Medium risk; attribute; owner's decision (alternative: buy the county extract) |
| Commercial-derived | fema_r9_* / fema_r9_parcel (Lightbox SmartParcels via FEMA), south_sf_corelogic | publicly readable but vendor attributes; High risk to ship raw. Recommended: validation + imputation prior, or ship as `year_confidence = estimated`, `source = fema_lightbox`, after the owner decides |

Personal data: no owner names / mailing addresses requested or stored.

---

## 8. Recommendations for the pipeline stage

1. **Per footprint, take the year by rank**: historic record (HRI `TRUEYR`, BERD single year,
   OSM `start_date`) where it lies in the footprint → current public roll → Alameda 2021 copy →
   FEMA/Lightbox (points, then by-APN parcels) → imputation. Spike / pre-1930 round years →
   `estimated` with an upper bound (SF rule). `region5_footprint_years.parquet` already holds the
   per-class candidates.
2. **Exempt / institutional parcels need a researched table** (as SF decision 19,
   `known_building_dates.csv`): spot checks — Hotel De Anza 1931 and California Theatre 1927
   (San José roll = HRI, correct); Oakland City Hall roll **1961** (Alameda 2021 copy and FEMA)
   vs BERD 1912 (built 1911–14); Kaiser Center roll 1962 vs BERD 1960; Marin County Civic Center,
   Hoover Tower / Stanford: no year at all (exempt). Stanford, UC Berkeley, Marin Civic Center,
   government, BART, ports and military land are the main gaps.
3. **Multi-building parcels**: parcel years date the main building; outbuildings (< 40 m²) and
   extra buildings should not all get it (`n_buildings`, `units`, `stories` help; assessor data
   is per parcel as in SF pitfall 3).
4. **Imputation** for the 7 % gap: neighbour median within 150 m (SF rule 7), then HISDAC FBUY;
   consider adding HISDAC BUPR for the within-cell distribution.
5. **Newer than the source vintage**: FEMA ≤ 2020, Alameda 2021 ≤ 2021, Berkeley ≤ 2016 — use
   the 2026 city layers where they exist; otherwise Overture footprints absent from older
   snapshots (Marin 2004 footprints, SMC footprints) bound the year from below.
6. **Constraints**: land-year grid (fill: Bay Farm Island, Foster City, Redwood Shores, Alameda's
   South Shore, Richmond harbor), redevelopment clearances (West Oakland / Acorn, Cypress
   freeway, downtown San José), Marin 2004 footprints ⇒ start ≤ 2004.
7. **Heights**: SMC LiDAR footprints (feet → m) for San Mateo; stories × 3.3 m + 1.5 m from the
   rolls; Overture/OSM; Microsoft ML last.
8. **Vanished buildings**: San José HRI demolished/moved; Sanborn tracing (Oakland 1889/1902–03/1911–12,
   San José 1884/1891/1915, Berkeley 1894/1911) where the fabric was cleared (West Oakland, Acorn,
   downtown San José, Cypress structure, BART/I-980 takings).
