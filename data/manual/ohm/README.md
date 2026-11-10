# OpenHistoricalMap imports (`data/manual/ohm/`)

OpenHistoricalMap (OHM, https://www.openhistoricalmap.org/) is a volunteer-traced, dated world map; its data is
**CC0 1.0** (no attribution required; we credit it anyway). Everything here was pulled with
`pipeline/ohm_import.py` from the OHM Overpass API (https://overpass-api.openhistoricalmap.org/api/interpreter;
four bbox chunks over the core Bay Area, `data/raw/ohm/`, downloaded 2026-11-09), compared with what the project
already has, and kept only where it is real, dated geometry we lack. Every row links its OHM way
(`https://www.openhistoricalmap.org/way/<id>`) and the source OHM cites. Rebuild: `python pipeline/ohm_import.py all`
(`download`, `goldrush`, `stanford`, `extras` = `rail`, `demolished`, `camp`, `sf`).

Gold-rush San Francisco (USCS 1852/53 chart, 1851 Burnt District map, Sanborn 1887): see
`data/manual/sanborn/README_goldrush.md` (files `data/manual/sanborn/sf_goldrush_*.geojson`). `sf_fires_1851.geojson`
holds the two 1851 fire areas used there.

## Stanford (OHM import "LSJUbldgs", 2,973 outlines + 142 other campus outlines)

The import (source map "Campus of Leland Stanford Junior University, 1962", purl.stanford.edu/qr683hn3144) dates
almost every outline with a **binned placeholder** ("-02-29" dates, `fixme=start_date`). What each bin means was
checked against the researched Stanford rows of `data/tables/known_building_dates_region.csv` on the same
footprint: 1888-02-29 = original Quad (researched 1889-1903, 119 rows); 1920-02-29 = on the old campus maps (33
rows: all <= 1954, 30 <= 1934); 1932-02-29 "shown on 1934 map" (1934 x5); 1940-02-29 "not on 1934 map" (1961 x5);
1964-02-29 / 2000-02-28 / 2004-02-28 = built after that year (1970 x4; 2003-2020 x10; 2016 x5); **1976-02-29 =
unknown (2,110 outlines; researched 1876-2000)**; the Escondido Village "1956" is one year for the whole site (it
also sits on the 1875 Escondite Cottage) and the "approximate" Science & Engineering Quad 2008 covers buildings of
2005-2014. Only 53 outlines carry a cited or day-exact date. Matching: an outline is today's footprint (Overture
2026-10-21.0 `region5_building`) when IoU >= 0.5, or it covers >= 60 % of the smaller and its point lies inside
(2,410 of 3,115 matched; the 705 others are mostly sheds < 40 m2).

| file | format | rows | what |
|---|---|---|---|
| `known_dates_ohm.csv` | `known_building_dates_region.csv` | 10 | cited / day-exact dates on footprints the table does not date yet (Arrillaga Sports Center 2006 — pipeline now 1932; Traitel 2017 — now 1929; Wilbur Hall 1955; Knight Management Center 2011 …) + Lou Henry Hoover Building 1967-**2022** (demolished; Overture still has it) |
| `stanford_bounds_ohm.csv` | `id,name,lat,lon,start_min,start_max,evidence,current_pipeline_year,violates,known_row,source_url,county,overture_id` | 571 | the map bins as bounds: 479 "<= 1962", 9 "<= 1934", 31 ">= 1934", 5 ">= 1964", 34 ">= 2000", 13 ">= 2004"; **92 are violated by today's pipeline year** (`violates`): clamp the imputed year into [start_min, start_max] unless the year is researched (`known:`) |
| `stanford_conflicts.csv` | | 2 | OHM vs `known_building_dates_region.csv`: Harmony House (table 1920; OHM "not on the 1934 map"), Montag Hall / Bakewell Building (table 1927; OHM: Bakewell 1952-2005, Montag Hall 2006). 27 other cited OHM dates agree within 2 years. Not overwritten. |
| `demolished_ohm.geojson` | footprint + `start_year, end_year, start_evidence, end_evidence, end_confidence, storeys, height_m, source_url, today_footprint, today_footprint_year` | 19 | Stanford buildings gone today with an OHM end date: Meyer Library 1966-2015, Cummings Art 1969-2015 (PCAD), Encina / Brown Gymnasium 1915-2005, Lou Henry Hoover 1967-2022, the Ginzton / HEPL / Applied Physics lab group (to c.2006, **end "arbitrary" in OHM**), the 1888-1932 farm / early campus buildings (**arbitrary** ends) … |
| `stanford_unmatched_ohm.csv` | | 115 | outlines >= 60 m2 with no footprint today and no end date (demolished after the import? review list) |

## Railways, street railways, ferries

`rail_review_ohm.csv`: every dated OHM railway / tram / ferry way in the extent that lies < 30 % within 60 m of
`historic_rail.geojson` or `routes.csv` (207 ways), for review. Picked from it, checked one by one:

* `historic_rail_ohm.geojson` (format of `historic_rail.geojson`, 10 segments): Mount Tamalpais & Muir Woods
  Railway 1896-1930 (NPS); SP 4th Street line through downtown San Jose 1869-1935 (moved to the Cahill St line;
  San Jose Mercury Herald 29 Dec 1935) and its later industrial remnants / SP San Jose - Gilroy track sections
  removed 1975-2019 (OHM from USGS quads and Esri Wayback; ends ESTIMATED inside the windows); Camp Fremont spur
  1917-1920; a spur from the SP line toward the Stanford campus on the 1897 USGS Palo Alto sheet only; California &
  Nevada Railroad (3 ft gauge) north of Blake St, Berkeley, abandoned c.1902.
* `routes_ohm.csv` (format of `routes.csv`, `geom_type = lonlat`): San Jose & Santa Clara Horse Railroad (The
  Alameda) 1868-1901, electric Santa Clara line 1901-1938; North Side Horse Railroad 1875-1901; Port Costa -
  Benicia train ferry (Solano) 1879-1930 (until the Martinez-Benicia bridge). Modes `horsecar`, `streetcar`,
  `ferry` as in routes.csv.

Seen and **not** exported (already ours, or undated / unsourced / outside the extent): Muni A-H lines and the
Geary lines (routes.csv), the San Mateo interurban (ir_40), Ocean Shore, SN, Los Altos branch (ours:
sp_mayfield_cutoff 1908.3-1964; OHM 1907-11-05 - 1964-01-27), the Santa Cruz-mountain SPC lines, Lincoln Highway
ferry (= our SF - Oakland Pier ferry), SF rail yards (Sanborn tracks), many unsourced 1900-1980 spurs.

## Demolished buildings elsewhere in the region

`region_demolished_ohm.geojson`: 532 OHM buildings with an end date outside San Francisco and Stanford and not from
a Sanborn tracing (Palo Alto / San Mateo / Berkeley Sanborn work is being done by other agents). Versions of one
structure (same outline, renamed / re-dated) are chained. Columns: `name, start_year, end_year, versions, storeys,
height_m, material, building, ohm_start_date, ohm_end_date, end_cause, description, sources, cited, ohm_url,
today_iou` (a footprint of the same shape still in Overture -> not demolished / stale), `county, traced_in` (already a
traced Sanborn / vanished-site building), `on_site` (Camp Fremont, HP Cupertino …), `other_agent_area`.

`notable_demolished_ohm.csv` (format of `data/tables/notable_demolished_region.csv` + `other_agent_area`): the
226 clean rows — cited, dated, no footprint today, not traced already (Sanborn areas, vanished sites), not on a
vanished site, not already in that table: San Jose and Santa Clara County (newspaper-, survey- and city-cited:
San Jose City Hall 1855-1906, City Hall Fire Station 1908-1951, Dawson Building 1894-1960, Carnegie Library
1903-1960, Santa Clara County Administration Building 1959-1976, Saint Joseph's College 1924-1990 …), Alviso,
Hayward's Carnegie library 1905-1949, and 115 in Menlo Park / Atherton dated by the USGS Palo Alto 1897 / 1940s sheets (Linden Towers 1878-1936
…; `other_agent_area = palo_alto_menlo_park`: coordinate with the Palo Alto / San Mateo Sanborn work). The footprint
for each row is the OHM outline in the geojson (same `id`).

## Camp Fremont (Menlo Park, July 1917 - Oct 1919)

`vanished_sites/README.md` found no map of the camp; OHM has a tracing of the **1917 Camp Fremont map (Stanford
archive, purl.stanford.edu/fb297sh0179)**: `vanished_sites_ohm.geojson` (format of `vanished_sites/sites.geojson`:
camp outline 205 ha `cover = grass`, 32 regiment / camp plots `cover = industrial`), `vanished_buildings_ohm.geojson`
(format of `vanished_sites/buildings.geojson`: 46 buildings incl. YMCA, Knights of Columbus, lettered barracks A-J;
one storey, height ESTIMATED), `camp_fremont_lines_ohm.geojson` (37 camp roads, the spur, fences, sewers;
1917.5-1919.75).

## San Francisco, beyond the gold rush

* `known_dates_ohm_sf.csv` (format of `data/tables/known_building_dates.csv`): 30 cited construction years of
  standing buildings not in that table — 23 SFPL branch libraries (city-owned, so no assessor year; dates from
  sfpl.org branch histories), St. Monica's (1918), Marina Theatre (1928), Holy Virgin Cathedral (1965) … Each note
  gives the pipeline's year now. Eureka Valley was dropped (1902 is the branch's founding; its building is of 1961);
  check West Portal (1936 = first branch opening) before merging.
* `notable_sf_ohm.csv` (format of `notable_pre1906.csv`): St. Ignatius Church and College on Market St, 1855-1862
  (3 parts) and 1862-1880 (the 1880-1906 Hayes St building is already `st_ignatius_1880`).
* `sf_wharves_1851_ohm.geojson`: the 12 wharf centrelines of the Burnt District map (California, Commercial = Long
  Wharf, Clay, Sacramento, Washington, Jackson, Pacific, Battery St …) with the fill band that later buried each.

Seen and not exported: the 1915 PPIE buildings (batch4.ts has the PPIE from the 1914 Sanborn), SF piers 1848-1965
(no sources on the ways), renamed buildings (Bechtel / Blue Shield / 50 Beale, Marshall Square / Orpheum, Wells
Fargo / Pacific Telephone, Western Merchandise Mart floors), business founding years (City Lights, Green Apple),
OHM street "opening" years 1847 / 1857 (the O'Farrell / Eddy plans, not openings), SFO Museum's terminal floor-plan
snapshots 1927-2021 (by period, not by building).

## The counties added in 2026-11 (Sonoma, Napa, Solano, Santa Cruz, east Contra Costa, south Santa Clara)

Same endpoint (the OHM Overpass API above; the main OSM Overpass is blocked by the proxy), four more bbox chunks
(`NEW_AREA_BOXES` in `ohm_import.py`, downloaded 2026-11-10). What OHM holds inside the ten-county extent but
outside the core: 14,400 undated waterways, 285 dated railway ways (752 km) and 85 other dated features - nothing
like the gold-rush or Stanford imports. **Nothing was imported wholesale; no OHM date was used.**

| file | what |
|---|---|
| `rail_review_ohm.csv` | regenerated for the ten counties: 221 dated OHM railway / tram / ferry ways not in `historic_rail.geojson` / `routes.csv` (the lines below are now ours and dropped out of it) |
| `new_area_review_ohm.csv` | the 85 dated features that are not railways or roads (`python pipeline/ohm_import.py newarea`): 16 outlines from Thompson's 1876 map of Santa Rosa (colleges, schools, hotels, the plaza - "1876" is the map year), 5 downtown Santa Cruz buildings (Hall of Records 1882, Leonard Building 1894, two banks 1910; no sources on the ways), Gilroy / Morgan Hill (Wheeler Hospital 1929, Dixon House 1887-1906, Saint Louise hospital 1987-89; newspaper-cited), Duncans Mills (1877 buildings, Scotta School 1877-2020), the Calistoga depot 1868, Mission San Francisco Solano 1823, the SS Palo Alto 1929 and its pier 1930, Monticello cemetery 1870-1953 and the Putah Creek stone bridge 1896-1956 (under Lake Berryessa), 18 Pacheco Pass highway bridges (Caltrans log), 14 `landuse=residential` town outlines, 10 `route=road`. For the building-date and landmark tables to check - not merged anywhere. |
| `routes_ohm.csv` | + Santa Rosa: the horse-car line on Fourth Street and McDonald Avenue of the 1876 Thompson map (`sr_street_railway`, 1877-1905, start ESTIMATED from the map; OHM's "1854" is a placeholder) and the Petaluma & Santa Rosa electric cars on Fourth Street (`sr_psr_fourth_st`, 1905-1931). Both rows are in `routes.csv`. `(route_id, segment_seq)` is now unique (the electric period of `sj_santa_clara_horse` is segment 2). |
| `data/raw/historic_rail/h2_ohm_newarea.json` (raw, not committed) | `python pipeline/ohm_import.py railextract`: 61 OHM way pieces of railways whose track is gone, clipped to three boxes, in the Overpass JSON that `historic_rail_trace.py`'s `rail` method reads next to the OSM grades. The routes that follow them are in `data/manual/historic_rail_spec.py` with our own dates and sections. |

OHM geometry used through that extract (each cited in the segment's `source_url` / note): North Pacific Coast narrow
gauge Valley Ford - Occidental - Monte Rio - Duncans Mills (ways 202387713 / 202387715; "USGS topographic maps; USGS
3DEP"), the Guerneville branch (202387871, "USGS 3DEP") and its approximate Monte Rio ways (2003720xx, tagged "routes
are approximate" - LOW confidence), the SF&NP Sebastopol branch and the P&SR Forestville line (202387872), Southern
Pacific's Santa Rosa branch through the Valley of the Moon (200461230, from the USGS Santa Rosa 1916 sheet), the
Boulder Creek branch and the Dougherty Extension (200444390, 200446467-92, cited to santacruztrains.com). OHM dates
that were wrong or placeholders and were replaced: Guerneville branch end "1940 (approximate)" -> rails removed 1935;
Boulder Creek branch start "1880-05" (the main line's date) -> 1885; Dougherty Extension end "1934" -> scrapped late
1917; Sebastopol branch end "1980 (arbitrary)" -> 1984-89; SP Santa Rosa branch "1935" -> 1935 north of Glen Ellen,
1942 south of it; Santa Rosa street railway "1854" -> by 1877.

Seen and not exported: the Sacramento Northern ways (OSM has the same grades; OHM's 1950 / 1960 / 1980 / 1990 ends
are decade bins), the SP Walnut Grove branch (outside the extent), the Alameda & San Joaquin coal line to Tesla
(outside), spurs at Bohemian Grove (approximate, unsourced), SP / NWP / Santa Fe main lines still in place (dated in
`routes.csv`).
