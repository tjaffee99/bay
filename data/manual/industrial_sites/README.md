# Military and industrial sites (`data/manual/industrial_sites/`)

From about 1880 to 1960 the Bay's shores filled with refineries, powder works, smelters, shipyards,
rail yards and depots, and the war added bases, magazines and ports; quarries and landfills ate into
the hills. Today's data knows these places only as they are now: refinery tank farms and Army
warehouses carry 1980s assessor (re-assessment) or imputed years, federal posts have no roll years at
all, quarry pits are bare rock "since the beginning of time", and the sites that are gone (shipyards,
powder works, the Oakland Army Base, the SP mole) are not there. This folder is the audit and the data
to fix that, from real maps wherever possible.

## Files

| file | what |
|---|---|
| `sites.geojson` | one or more Polygon parts per site and period (ground cover + map label) |
| `building_dates.csv` | per-site rules for today's footprints inside a site |
| `known_dates_industrial.csv` | per-footprint years, same columns as `data/tables/known_building_dates_region.csv` (researched buildings first, then footprints dated by the USGS editions) |
| `traced/permanente_*.geojson` | Permanente pit outlines extracted from the 1960 / 1968 / 1979 / 1991 sheets (`tools/tint.py`) |
| `traced/audit.csv` | per site: today's footprints, the live map's years, how many the maps draw, how many are corrected and by how much |
| `traced/audit_terrain.csv` | per part: share of terrain vertices WorldCover calls bare / built (what the c.1800 cover paints as rock) |
| `tools/` | `build.py` (everything from `industrial_def.py`), `editions.py`, `date_editions.py`, `footprints.py`, `tint.py`, `montage.py`, `audit_terrain.py` |

Rebuild: `cd data/manual/industrial_sites && ../../../.venv/bin/python -I tools/build.py` (edition
presence is cached in `data/interim/industrial_sites/`; `--redate` re-reads the maps; ~30 min cold, one
process under ~1.4 GB), then `python -I tools/audit_terrain.py`.

### `sites.geojson` properties
`site_id, part_id, name, kind` (refinery | quarry | landfill | military | shipyard | rail_yard | factory |
cannery | power_plant | cement | chemical | salt_works | port_terminal | other),
`cover` — what the ground looked like over `[year_start, year_end)`:
`industrial | quarry_pit | landfill | tank_farm | military | rail_yard | water`, plus **`open_works`**
(added: a fenced works or reservation that stayed mostly open ground — powder-works buffer land,
ammunition magazines, training areas, a tank hill: keep the natural / grass cover, show the label and the
buildings, don't pave it),
`year_start, year_end` (fractional; 9999 = still there; the *ground* — e.g. a shipyard's ground stays
industrial after the yard closed), `name_label` (short map label) with `label_start, label_end` (when the
name applies: Moore Dry Dock 1909–1961 on ground that is still industrial), `confidence`
(`exact` = outline and dates from the sources; `estimated` = traced but a date or outline approximate),
`source_url`, `note` (incl. where the geometry comes from), `county`.

Parts overlap on purpose: growth stages of a quarry are separate, ever larger features with later
`year_start` (a consumer applies each from its year; the larger later stage contains the earlier one),
and a plant part can lie inside a reservation part. Where a site ends (`year_end` < 9999) the ground is
whatever came next (the terrain's own history, or another part).

### `building_dates.csv`
`site_id, ring_type, year, applies_to, max_year, evidence, source_url`
* `ring_type = site`: the union of the site's parts.
* `applies_to = all_pre`: no footprint inside can predate `year` (the site's founding): a live year
  earlier than that is a wrong roll / imputation (Lockheed's Sunnyvale campus at 1900, Shell Martinez buildings
  at 1910) and becomes `year`. Written only where the founding year is documented (`confidence = exact`).
* `applies_to = named`: the site's footprints were checked against the USGS editions; use the rows of
  `known_dates_industrial.csv` (they already apply the founding-year floor).
* `applies_to = tanks`: round footprints (circularity > 0.85, > 40 m²) inside whose live year is in
  `(year, max_year]` take `year` (re-assessed tank farms where no edition could date them). Not used
  in this pass: every refinery was dated by edition.
* `max_year` (extra column): upper bound of the re-assessment window for `tanks` (blank = none).

### `known_dates_industrial.csv`
`id, name, lat, lon, start_year, end_year, source_url, note, county` — the point lies inside today's
footprint (Overture region5 id in the note). `source_url` = the sheet that first draws the footprint.

## Method

**Outlines.** Today's outline of a site = OpenStreetMap `landuse=industrial / military / quarry /
landfill / railway` (Overture base `land_use`, 2026-10-21.0) where the site survives; for vanished
sites, the outline read on the 1946–1959 1:24k sheet in a local metre frame with a labelled grid
(vanished-sites renderer `vt.render_topo`: sheet registration + NADCON; +-40 m). Military posts without
an OSM outline (Marin forts, Hamilton) use the convex hull of their buildings (+35–50 m).

**Quarry growth** (`tools/tint.py`): each edition is resampled into the site frame and the pit is
extracted by colour — the unwooded quarry ground of the 1948–1968 sheets (`open`, seeded at the
"Quarry" label), the magenta photorevision overprint of the 1968–1980 sheets (`purple`), and the
red-brown disturbed-surface tint of the 1980s–90s sheets (`tint`) — closed, hole-filled and clipped
to the sheet's NAD27 quad (so neighbouring sheets are joined, not double-counted). A stage starts at the
midpoint between the photo year of the previous edition and its own.

**Dating today's footprints by edition** (`tools/date_editions.py`): for every USGS edition covering a
site (1:62,500 from the 1890s, every reprint separately; 1:24k from the 1940s with every photorevision),
the site is resampled at 2 m (1:24k) / 4 m (1:62,500); a footprint is *drawn* when the dark ink, opened by
~6 m (drops roads, rail, lettering), covers >= 30 % (1:62,500: 20 %) of it buffered by the registration
tolerance (6 m / 15 m), or — for round tanks — when its rim band carries ink (open tank circles) or it is
filled. The footprint's start = midpoint of the last edition not drawing it and the first edition drawing
it (and staying drawn on most later ones); reprints count as drawn by their imprint year but absent only
for their culture year; drawn on the first edition after the founding -> the founding year (if within
15 years) or the midpoint. A footprint whose live year is more than 2 years later than the edition that
first draws it, or earlier than the site's founding, gets a row in `known_dates_industrial.csv`.
Absence on a topo sheet is weak evidence (urban tint areas omit buildings), so undrawn footprints keep
their live year unless it predates the site.

## Sites and sources

Facts per site are in `tools/industrial_def.py` (each with its source URL; repeated in every feature's
`note` / `source_url`). Outline sources: `osm` = OpenStreetMap land_use outline of today, `osm_box` = all
industrial OSM outlines in a box (multi-polygon refineries), `traced` = read on the cited USGS sheet,
`files` = tint-extracted stage outlines, `hull` = convex hull of the post's buildings.

| site | label | kind | years | parts | outline | confidence |
|---|---|---|---|---|---|---|
| `chevron_richmond` | Chevron Richmond Refinery | refinery | 1902–today | 18 | osm_box | exact |
| `shell_martinez` | Shell Martinez Refinery | refinery | 1915–today | 2 | osm | exact |
| `avon_refinery` | Avon Refinery (Marathon) | refinery | 1913–today | 1 | osm | exact |
| `rodeo_refinery` | Rodeo Refinery (Oleum) | refinery | 1896–today | 4 | osm | exact |
| `selby_smelter` | Selby Smelter | factory | 1885–1971 | 1 | osm | estimated |
| `ch_crockett` | C&H Sugar | factory | 1906–today | 1 | osm | exact |
| `hercules_powder` | Hercules Powder Works | chemical | 1881–1977 | 2 | traced | estimated |
| `giant_powder` | Giant Powder Works | chemical | 1892–1960 | 3 | osm | estimated |
| `concord_nws` | Concord Naval Weapons Station | military | 1942–today | 14 | osm | exact |
| `acme_landfill` | ACME Landfill | other | 1949–today | 1 | osm | estimated |
| `keller_canyon_landfill` | Keller Canyon Landfill | other | 1992–today | 1 | osm | exact |
| `kaiser_yard3` | Kaiser Shipyard No. 3 | shipyard | 1942–today (named 1942–1946) | 1 | osm_box | exact |
| `kaiser_yards_1_2` | Kaiser Shipyards 1 & 2 | shipyard | 1941–1946 | 1 | traced | estimated |
| `ford_richmond` | Ford Assembly Plant | factory | 1931–1956 | 0 | building only | exact |
| `santa_fe_richmond` | Santa Fe Yard | rail_yard | 1900–today | 4 | osm | estimated |
| `pullman_richmond` | Pullman Shops | factory | 1910–1959 | 1 | traced | estimated |
| `point_molate` | Winehaven / Point Molate | military | 1907–1995 | 2 | traced | estimated |
| `oakland_army_base` | Oakland Army Base | military | 1942–today (named 1942–1999.8) | 1 | traced | estimated |
| `sp_oakland_mole` | Oakland Mole | rail_yard | 1882–today (named 1882–1960) | 1 | traced | estimated |
| `sp_west_oakland_yard` | West Oakland Rail Yards | rail_yard | 1879–today | 3 | osm | estimated |
| `oakland_port_terminals` | Port of Oakland | port_terminal | 1962.7–today | 13 | osm | exact |
| `moore_dry_dock` | Moore Dry Dock | shipyard | 1909–today (named 1909–1961) | 1 | traced | estimated |
| `bethlehem_alameda` | Bethlehem Shipyard | shipyard | 1916–1956 | 9 | osm | estimated |
| `alameda_coast_guard` | Coast Guard Island | military | 1942–today | 1 | osm | estimated |
| `camp_parks` | Camp Parks | military | 1942–today | 2 | osm | exact |
| `llnl` | Lawrence Livermore Lab | military | 1942–today | 1 | osm | exact |
| `sandia_livermore` | Sandia Livermore | military | 1956–today | 1 | osm | exact |
| `gm_fremont` | Tesla Factory (GM Fremont) | factory | 1962–today | 1 | osm | exact |
| `livermore_gravel` | Pleasanton Gravel Pits | quarry | 1931–today | 1 | osm | estimated |
| `sunol_quarries` | Sunol Quarries | quarry | 1950–today | 3 | osm | estimated |
| `altamont_landfill` | Altamont Landfill | other | 1980–today | 1 | osm | exact |
| `vasco_road_landfill` | Vasco Road Landfill | other | 1963–today | 1 | osm | estimated |
| `pier70_union_iron_works` | Union Iron Works (Pier 70) | shipyard | 1884–today | 3 | osm | exact |
| `potrero_power` | Potrero Power Station | power_plant | 1890–2011 | 1 | osm | estimated |
| `bayshore_yard` | Bayshore Yard | rail_yard | 1907–1982 | 2 | osm | estimated |
| `schlage_lock` | Schlage Lock | factory | 1926–1999 | 1 | osm | estimated |
| `ox_mountain_landfill` | Ox Mountain Landfill | other | 1976–today | 2 | osm | estimated |
| `guadalupe_valley_quarry` | Brisbane Quarry | quarry | 1950–today | 1 | osm | estimated |
| `permanente` | Permanente Quarry | quarry | 1903–today | 11 | files, osm, traced | exact |
| `stevens_creek_quarry` | Stevens Creek Quarry | quarry | 1950–today | 1 | osm | estimated |
| `lockheed_sunnyvale` | Lockheed Missiles & Space | factory | 1956–today | 2 | osm | exact |
| `hendy_westinghouse` | Hendy Iron Works (Westinghouse) | factory | 1906–today | 1 | osm | exact |
| `newby_island_landfill` | Newby Island Landfill | other | 1938–today | 1 | osm | estimated |
| `guadalupe_landfill` | Guadalupe Landfill | other | 1930–today | 1 | osm | estimated |
| `marinship` | Marinship | shipyard | 1942–today (named 1942–1946) | 1 | traced | exact |
| `san_rafael_quarry` | San Rafael Rock Quarry | quarry | 1929–today | 1 | osm | exact |
| `redwood_landfill` | Redwood Landfill | other | 1958–today | 1 | osm | estimated |
| `fort_baker` | Fort Baker | military | 1897–today (named 1897–2000) | 1 | hull | exact |
| `fort_barry` | Fort Barry | military | 1904–today (named 1904–1974) | 1 | hull | exact |
| `fort_cronkhite` | Fort Cronkhite | military | 1937–today (named 1937–1974) | 1 | hull | exact |
| `fort_mcdowell` | Fort McDowell | military | 1900–today (named 1900–1946) | 1 | hull | exact |
| `hamilton_field` | Hamilton Field | military | 1932–today (named 1932–1988) | 1 | hull | exact |
| `clayton_quarries` | Clayton Quarries | quarry | 1956–today | 3 | osm | estimated |

### Permanente Quarry (the owner's example)
Limestone was quarried on Permanente Creek from c.1902–03 (Granite Rock Co.; "El Dorado Sugar Co.
quarry" in 1906; RWQCB: "mined since approximately 1903"), small and intermittent until 1934; Kaiser's
Permanente Corp. built the quarry and the cement plant from June 1939 (first cement Dec 1939). Stages
(`permanente_*` parts; areas of the pit outline):

| part | from | outline | pit |
|---|---|---|---|
| early quarry | 1903 | quarry symbol of the Palo Alto 1:62,500 sheets (1939 survey, 1940 photos); extent estimated | 1.6 ha |
| cement plant | 1939.5 | Cupertino 1:24k 1953 (1948 photos), plant buildings, kilns, tanks | 73 ha (`industrial`) |
| pit 1948 | 1944 | white "Quarry" ground of the Cupertino 1953 sheet (1948 photos), read by hand | 8 ha |
| pit 1960 | 1954 | Cupertino 1961 (1960 photos), unwooded quarry ground (`tint.py open`) | 95 ha |
| pit 1968 | 1964 | 1968 photorevision (`open`) ∪ 1960 | 97 ha |
| pit 1979 | 1973.5 | 1980 photorevisions of Cupertino + Mindego Hill (magenta, `purple`) ∪ 1968 | 143 ha |
| pit 1991 | 1985 | 1991 Cupertino + Mindego Hill disturbed-surface tint (`tint`) ∪ 1979 | 197 ha |
| today | 2005 (est.) | OSM quarry outline incl. the West / East Materials Storage Areas | 330 ha |

So the hillside is oak / chaparral (WorldCover's trees around it) until 1903, a small scar until 1939,
and the pit grows through the Kaiser years; today 330 ha.

## The audit: biggest errors found in the live map's data

`traced/audit.csv` compares, for every site, the years the live map gives today's footprints inside it
(`region_building_points.parquet` / `sf_buildings.parquet` as built on 2026-11-08) with the USGS
editions. **984 rows** in `known_dates_industrial.csv` (980 footprints dated by edition + 4 researched
buildings): 930 footprints are drawn on maps decades before their live year, 50 have live years before
their site existed. Median correction: 34 years.

1. **Refineries look like 1980s plants.** Tank farms and process buildings carry re-assessment or
   neighbour-imputed years (most refinery footprints have no roll year at all): Chevron Richmond median
   1984 (tanks on the 1915 sheet → 1902; 165 footprints corrected, median +51 yr), Shell Martinez 1977
   (142), Avon / Golden Eagle 1986 (119), Rodeo / Oleum 1984 (108), C&H Crockett (8). Their ground,
   which the terrain dates by the buildings, turned to "city" only in the 1970s–80s; the parts in
   `sites.geojson` give it from the founding (and the later tank fields from the editions that first
   draw them).
2. **Federal posts have no roll years**, so their buildings took the 1970s–90s years of the
   neighbourhood: Fort Baker (the 1901–10 post at 1976–91), Fort Barry, Fort Cronkhite, Fort McDowell
   (Angel Island's 1910–11 East Garrison at ~1983), Camp Parks (97 corrected), Lawrence Livermore (89;
   NAS Livermore 1942 / Radiation Lab 1952 buildings at ~1985), Sandia, Coast Guard Island, Concord NWS,
   the Oakland Army Base warehouses that still stand (13), Hamilton Field's historic district (47
   buildings without a roll year; the 1990s houses on the old base keep their real roll years).
3. **Placeholder years before the site existed:** Lockheed Missiles & Space, Sunnyvale (1956) has 44
   buildings at **1900** (the Sunnyvale roll's 1900 placeholder), so the campus stood half a century
   before Moffett Field; Shell Martinez has 6 at 1910–11 (before the 1915 refinery).
4. **Single landmarks:** Winehaven's 1907 winery buildings at 1990 / 1993, the 1910 Bayshore Roundhouse
   at 1992, the 1931 Ford Richmond Assembly Plant at 1941 (fill zone, below), Point Molate's other
   buildings (18, median +79 yr), the SP West Oakland yard buildings (12, +74 yr).
5. **Quarries and landfills are rock from 1769.** The c.1800 cover takes WorldCover 2021's bare class as
   natural rock, so every pit and landfill is grey from the start of the timeline: 71 % of Permanente's
   terrain vertices, 86 % of the Selby slag site, about half of Stevens Creek and San Rafael, a third of
   Clayton, Sunol, the Pleasanton gravel pits and Brisbane, a fifth to a quarter of the landfills (table
   below). The quarry / landfill parts give the year the ground was dug (Permanente in 8 stages).
6. **Missing sites:** the Port of Oakland had no Army Base, SP mole, West Oakland yards, Moore Dry Dock
   or Bethlehem Alameda; Richmond no Kaiser yards, Pullman shops or Point Molate; the Carquinez shore no
   Hercules / Giant powder works or Selby smelter; Marin no Marinship — all now in `sites.geojson` with
   their years (the Naval Supply Center is in `vanished_sites/`).
7. **Fill zone too broad (Richmond):** see below — 40 buildings older than 1940 are pushed to 1941–43.

| site | founded | footprints | live p10 / median | drawn on maps | corrected (too late / too early) | median shift (yr) |
|---|---|---|---|---|---|---|
| `chevron_richmond` | 1902 | 611 | 1976 / 1984 | 340 | 165 (165 / 0) | +51 |
| `shell_martinez` | 1915 | 488 | 1960 / 1977 | 182 | 142 (136 / 6) | +28 |
| `avon_refinery` | 1913 | 327 | 1977 / 1986 | 123 | 119 (119 / 0) | +34 |
| `rodeo_refinery` | 1896 | 287 | 1976 / 1984 | 117 | 108 (108 / 0) | +33 |
| `ch_crockett` | 1898 | 37 | 1910 / 1929 | 10 | 8 (8 / 0) | +26 |
| `hercules_powder` | 1881 | 1132 | 1986 / 2004 |  | 0 (0 / 0) | +0 |
| `giant_powder` | 1892 | 6 | 1983 / 1986 |  | 0 (0 / 0) | +0 |
| `concord_nws` | 1942 | 70 | 1976 / 1984 | 9 | 8 (8 / 0) | +25 |
| `acme_landfill` | 1949 | 5 | 1984 / 1987 |  | 0 (0 / 0) | +0 |
| `keller_canyon_landfill` | 1992 | 8 | 1976 / 1980 |  | 0 (0 / 0) | +0 |
| `kaiser_yard3` | 1942 | 45 | 1963 / 1963 | 33 | 0 (0 / 0) | +0 |
| `kaiser_yards_1_2` | 1941 | 680 | 1990 / 1992 |  | 0 (0 / 0) | +0 |
| `santa_fe_richmond` | 1900 | 31 | 1967 / 1983 | 11 | 5 (5 / 0) | +54 |
| `pullman_richmond` | 1910 | 29 | 1953 / 1971 |  | 0 (0 / 0) | +0 |
| `point_molate` | 1907 | 52 | 1976 / 1984 | 38 | 18 (18 / 0) | +79 |
| `oakland_army_base` | 1942 | 84 | 1977 / 1983 | 21 | 13 (13 / 0) | +25 |
| `sp_oakland_mole` | 1882 | 21 | 1979 / 1988 |  | 0 (0 / 0) | +0 |
| `sp_west_oakland_yard` | 1879 | 66 | 1953 / 1980 | 30 | 12 (12 / 0) | +74 |
| `oakland_port_terminals` | 1962.7 | 257 | 1977 / 1990 |  | 0 (0 / 0) | +0 |
| `moore_dry_dock` | 1909 | 27 | 1982 / 1992 |  | 0 (0 / 0) | +0 |
| `bethlehem_alameda` | 1916 | 36 | 1987 / 1990 |  | 0 (0 / 0) | +0 |
| `alameda_coast_guard` | 1942 | 80 | 1977 / 1983 | 22 | 15 (15 / 0) | +39 |
| `camp_parks` | 1942 | 343 | 1978 / 1990 | 98 | 97 (97 / 0) | +49 |
| `llnl` | 1942 | 421 | 1978 / 1985 | 101 | 89 (89 / 0) | +25 |
| `sandia_livermore` | 1956 | 70 | 1977 / 1983 | 18 | 12 (12 / 0) | +27 |
| `gm_fremont` | 1962 | 118 | 1962 / 1962 | 20 | 0 (0 / 0) | +0 |
| `livermore_gravel` | 1931 | 15 | 1971 / 1971 |  | 0 (0 / 0) | +0 |
| `sunol_quarries` | 1950 | 36 | 1952 / 1980 |  | 0 (0 / 0) | +0 |
| `altamont_landfill` | 1980 | 33 | 1976 / 2014 |  | 0 (0 / 0) | +0 |
| `vasco_road_landfill` | 1963 | 4 | 1966 / 1966 |  | 0 (0 / 0) | +0 |
| `pier70_union_iron_works` | 1884 | 55 | 1896 / 1897 | 19 | 4 (4 / 0) | +27 |
| `potrero_power` | 1890 | 68 | 1923 / 1923 | 6 | 5 (5 / 0) | +33 |
| `bayshore_yard` | 1907 | 2 | 1979 / 1983 | 0 | 0 (0 / 0) | +0 |
| `schlage_lock` | 1926 | 2 | 1943 / 1944 |  | 0 (0 / 0) | +0 |
| `ox_mountain_landfill` | 1976 | 19 | 1981 / 1988 |  | 0 (0 / 0) | +0 |
| `guadalupe_valley_quarry` | 1950 | 18 | 1977 / 1988 |  | 0 (0 / 0) | +0 |
| `permanente` | 1939.5 | 48 | 1978 / 1984 | 29 | 12 (12 / 0) | +39 |
| `stevens_creek_quarry` | 1950 | 9 | 1900 / 1986 |  | 0 (0 / 0) | +0 |
| `lockheed_sunnyvale` | 1956 | 77 | 1900 / 1901 | 38 | 51 (7 / 44) | -56 |
| `hendy_westinghouse` | 1906 | 44 | 1906 / 1907 | 1 | 0 (0 / 0) | +0 |
| `newby_island_landfill` | 1938 | 7 | 1987 / 1991 |  | 0 (0 / 0) | +0 |
| `guadalupe_landfill` | 1930 | 23 | 1977 / 1986 |  | 0 (0 / 0) | +0 |
| `marinship` | 1942 | 242 | 1943 / 1956 |  | 0 (0 / 0) | +0 |
| `san_rafael_quarry` | 1929 | 17 | 1981 / 1988 |  | 0 (0 / 0) | +0 |
| `redwood_landfill` | 1958 | 24 | 1965 / 1965 |  | 0 (0 / 0) | +0 |
| `fort_baker` | 1901 | 77 | 1976 / 1984 | 31 | 14 (14 / 0) | +53 |
| `fort_barry` | 1907 | 33 | 1978 / 1985 | 14 | 9 (9 / 0) | +74 |
| `fort_cronkhite` | 1941 | 43 | 1978 / 1987 | 33 | 26 (26 / 0) | +42 |
| `fort_mcdowell` | 1909 | 16 | 1977 / 1983 | 9 | 3 (3 / 0) | +80 |
| `hamilton_field` | 1932 | 1005 | 1998 / 2000 | 258 | 47 (47 / 0) | +47 |
| `clayton_quarries` | 1956 | 16 | 1890 / 1934 | 0 | 0 (0 / 0) | +0 |

### Terrain: share of each site's terrain vertices that WorldCover calls bare (rock "since 1769")

| site | terrain vertices | WorldCover bare (rock from 1769) | built |
|---|---|---|---|
| `selby_smelter` | 73 | 86% | 7% |
| `permanente` | 2307 | 71% | 3% |
| `stevens_creek_quarry` | 145 | 56% | 4% |
| `san_rafael_quarry` | 135 | 53% | 25% |
| `clayton_quarries` | 510 | 39% | 2% |
| `sunol_quarries` | 981 | 32% | 4% |
| `livermore_gravel` | 1064 | 31% | 1% |
| `guadalupe_valley_quarry` | 381 | 31% | 5% |
| `newby_island_landfill` | 328 | 28% | 2% |
| `altamont_landfill` | 1008 | 26% | 1% |
| `oakland_army_base` | 2683 | 23% | 59% |
| `ox_mountain_landfill` | 365 | 21% | 4% |
| `keller_canyon_landfill` | 500 | 20% | 1% |
| `oakland_port_terminals` | 3846 | 19% | 79% |
| `moore_dry_dock` | 247 | 19% | 78% |
| `santa_fe_richmond` | 1048 | 19% | 79% |
| `sp_oakland_mole` | 552 | 18% | 75% |

(`traced/audit_terrain.csv` per part; at the port and yard sites the "bare" share is paved ground on
fill, which the fill history already dates.)

## Not done / could not fix here

* **Pipeline / viewer integration** (not edited here): the terrain needs to (1) take each part's `cover`
  from its `year_start` (and give quarry / landfill / tank-farm parts the *surrounding* natural cover
  before their first stage instead of WorldCover's bare = ROCK — see the terrain table), (2) draw one
  label per `site_id` (`name_label` over [min `label_start`, max `label_end`)), (3) apply
  `building_dates.csv` and merge `known_dates_industrial.csv` into the region years *after*
  `land_check`, or narrow the fill zones that move pre-fill buildings (below).
* **Fill zone too broad (Richmond):** `fill_zones.csv` row `cc_richmond_shipyards` is a lon/lat box
  (-122.39..-122.33 × 37.900..37.925) dated 1940.9–1943, so the land-year check pushes every building in
  it to 1941–43: the **Ford Assembly Plant (1931; roll 1931 → live 1941)**, the 1930–31 Ford Point
  buildings, a 1915–16 cluster at 37.924 N / -122.374 (Cutting Blvd) and others — 40 footprints whose roll
  year is before 1940.5. Ford Point was filled before the 1930–31 plant; the zone should be cut to the shipyard basins
  (`kaiser_yards_1_2`, `kaiser_yard3` outlines) and the Inner Harbor fill.
* **SF military posts** (Presidio, Fort Mason, Fort Miley, Fort Funston, Treasure Island, Hunters Point)
  are not repeated here: their buildings have researched years in `known_building_dates.csv` (Presidio
  NHL inventory etc.) and Hunters Point / NAS Alameda / Moffett are modelled in
  `data/research/landmarks_ports.md`; the Naval Supply Center Oakland is in `vanished_sites/`.
* **Hamilton Field's airfield** (runways 1935–1988) is not drawn: it needs a row in
  `data/tables/airports.csv` + runway outlines in `airports_extra.geojson` (OSM has only the wetlands /
  housing; the 1950s Novato / Petaluma Point sheets show the runways).
* **Not traced** (no outline in this pass): GM Chevrolet Oakland Assembly (1916–63, Eastmont Mall),
  Caterpillar / Best San Leandro, Western Pipe & Steel and Bethlehem South San Francisco shipyards
  (1941–45), Swift / Western Meat South San Francisco, Mococo (Mountain Copper Co., Martinez), Cowell
  Portland Cement (1908–46), Port Costa grain warehouses, Camp Fremont (Menlo Park 1917–19), Del Monte
  Plant 3 (San José), Libby's Sunnyvale cannery, FMC San José, Pacific Portland / Ideal Cement Redwood
  City (oyster-shell plant on the Port of Redwood City), Leslie Salt plants (the ponds are in
  `water_history.csv`), Nike sites (SF-88 etc.), coastal batteries, Port Chicago town (razed 1968).
* **Quarry growth** traced only at Permanente; the other quarries and landfills are today's outline with
  one start year (several estimated: Sunol, Stevens Creek, Brisbane, Clayton, ACME, Vasco Road, Redwood,
  Guadalupe, Ox Mountain) — the same `tint.py` passes on their sheets would give stages.
* **Dates that are estimates**: Selby smelter end (c.1971), Pullman shops (c.1910–59), Howard Terminal's
  first year, West Oakland yards' first year, the intermodal yards, the Navy fuel-depot tank hill outline
  at Point Molate, the Hercules buffer land outline.
* Absence on a topo sheet is weak (urban tint omits buildings; sheets sometimes skip plant buildings), so
  footprints never drawn keep their live year unless it predates the site; and edition dates are
  midpoints (±5–15 years between editions; 1915–1947 is a 32-year gap at the refineries).

## Licences
USGS topographic maps: public domain. Outlines from OpenStreetMap via Overture (`osm` / `osm_box` parts,
the hull outlines' footprints, the footprint ids and points in `known_dates_industrial.csv`): ODbL 1.0,
© OpenStreetMap contributors — `sites.geojson` and `known_dates_industrial.csv` are derived databases
(ODbL). Facts (years) from the sources cited per site / row (Wikipedia CC BY-SA, NPS, CLUI, CEC, county
and agency documents): facts only.
