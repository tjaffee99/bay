# Bay fill, diking and restoration: when each piece happened

Files covered here:

- `data/manual/fill_zones.csv`: about 100 dated zones, one row per stage, for fill, diked marsh, excavation, restoration and piers.
- `data/tables/landcover_history.csv`: the pre-urban land cover to paint under today's city, with dates.
- New raw downloads in `data/raw/`. They are listed under "Downloaded datasets" below.

## What the zones are for

The geometry of each change comes from data: **fill = modern land (TIGER) − historical land (c.1800 baylands)**. The zones in this file supply only the dates: when each part of that difference became land, became a diked pond or pasture, or went back to the tides. That is why the zone rings are deliberately coarse. A ring only needs to **cover** its fill area and keep away from neighbours with different dates. Always intersect a zone with the data-derived difference, and never draw a zone directly as land.

### Columns

`zone_id,name,region,year_start,year_end,ring_type,ring,kind,note,source_url`

- **year_start / year_end**: when filling (or diking, or restoration) started and when it was essentially complete. Grow the land across that span. Years can be decimal, so 1912.28 is mid-April 1912. Where a span is a documented bracket, not a measured progression, the `note` says so.
- **ring_type = `streets`**: the ring is `Street A & Street B; Street C & Street D; …`, ordered, using present-day DataSF names. Every pair resolves with `pipeline/fire_1906.py:intersection()`, and I checked all of them. A few pairs ("Sansome St & Market St", "Steuart St & Folsom St", "Hawes St & Bancroft Ave") resolve by closest approach of 0–22 m. **Extension:** an element can instead be `@lat,lon`, the same convention as `fire_1906_boundary.csv` notes. I used this for vertices in the water or on the seawall line, where there is no intersection. Regex: `^@\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)$`. Bulkhead vertices along The Embarcadero and Jefferson St sit about 45 m bayward of the street centreline, which is the seawall face. Pierhead vertices sit about 420 m bayward.
- **ring_type = `lonlat`**: `lon lat; lon lat; …` (WGS84). The ring is not explicitly closed.
- **kind**:
  - `fill`: water or marsh becomes land.
  - `diked_marsh`: tidal marsh or flat is leveed off for hay, dairy, an airfield or salt ponds. It is still not open water. In San Pablo Bay, Suisun and the South Bay, render it as pasture or salt pond, not as built land.
  - `excavated`: land becomes water. Only the Alameda Tidal Canal is in this file.
  - `restored`: a levee is breached and the area goes back to tidal marsh or water.
  - **`pier`** is an extension beyond the spec. It marks pile-supported pier decks that TIGER counts as land but that are not landfill (see the pitfalls below).
- **Overlaps**: zones of the same kind were kept almost disjoint. The QA script reports overlaps of a few hectares only at shared edges. Recommended rules:
  1. For `fill` overlaps, the earliest `year_end` wins.
  2. `restored` overrides `fill` and `diked_marsh` after its own `year_start`.
  3. A later `diked_marsh` row on top of an earlier one changes the cover, not the land. Example: `nb_napa_salt_ponds` from 1950 on top of `nb_napa_marsh_diked` turns hay land into salt ponds.
  4. The `fb_*` rows are **fallbacks**. Use them only for fill pixels that no specific zone covers.
  5. Clip `excavated` and `restored` rings to the data: a restored ring is a bounding box, and only its pond or marsh interior changes.

### Method

1. **San Francisco.** The main source is Gerald R. Dow, *Bay Fill in San Francisco: A History of Change*, MA thesis, CSU San Francisco, 1973. It has 191 pages and uses the Harbor Commissioners' biennial reports, USC&GS chart comparisons (Appendix 5 lists every chart edition 1852–1973) and directories. A local copy is in `data/raw/dow_1973/`. The author permits reproduction for research. Its **Appendix 6 tabulates the start and completion dates of every seawall section**, which drive the Embarcadero zones. Map 9 shows the 1847 shoreline and marsh against the 1972 shoreline.
   - For the Marina I used USGS OFR 90-253 (`data/raw/usgs_fill/`). Its figure 6 maps fill by age class: 1851–69, 1869–95, 1895–1906 and 1906–17 (mostly 1912).
   - The NPS "Buried ships" page and the Exploratorium supplied the Yerba Buena Cove anchor points. The Port's 2006 NRHP nomination covers piers and the seawall.
2. **The rest of the Bay** is coarser. Each zone uses one or two secondary sources (Wikipedia, local historical societies, agency pages), cited per row.
3. **Checks.** Every street ring was geocoded against DataSF centrelines. Every zone was plotted over TIGER modern land and the SFEI c.1800 baylands GIS (QA plots were made in a scratch area and are not committed).

### Yerba Buena Cove bands (important caveat)

No source I found gives the shoreline street by street year by year. The bands follow the cove shore (Montgomery St → Sansome → Battery → Front → Davis → East St / The Embarcadero). They are **interpolated between documented anchors**:

- 1847 beach on Montgomery St.
- Laguna Salada filled 1849.
- *Niantic* beached at Clay & Sansome in 1849.
- Storeships at Battery St buried after the fire of 4 May 1851.
- City grades of 1853, set because the shore had moved about 1000 ft east.
- Steam paddy dumping along Battery St in 1853–54.
- Water-lot filling "until 1859".
- First seawall along East St, 1867–69.

The 1853 USC&GS city chart and T-687 (1857) would pin the bands down. The georeferenced rasters are at <https://nsde.ngs.noaa.gov/>. SFEI's copy of T-687 is on a bot-walled WMS (`mapserver.sfei.org … hiddennature.map`).

## Known pitfalls for the land model

1. **TIGER counts piers as land.** Along the Embarcadero, the pile-supported piers are land polygons in TIGER. For that reason the waterfront fill zones stop at the seawall or bulkhead line. The band beyond it, out to the pierhead line, is the `sf_embarcadero_piers` zone (`kind=pier`). Everything there is deck on piles except Pier 45, which has a fill core. Elsewhere (Mission Bay southward) the zones run offshore, because Piers 50, 80, 94 and 96 really are on fill.
2. **TIGER counts salt ponds and diked marsh as land.** That covers the South Bay, Napa and Redwood City ponds (checked in the QA plot), so `modern − historical` will call them "fill". Treat everything inside the `diked_marsh` zones as **pond or pasture**, not urban land, until a later `fill` zone says otherwise. Examples are Foster City (1961), Redwood Shores (1963) and Alameda South Shore.
3. **The c.1800 baseline near downtown SF is itself a reconstruction.** The earliest accurate Coast Survey sheets (1851–53) already show Yerba Buena Cove partly filled. SFEI's EcoAtlas c.1800 shoreline draws the cove at Montgomery St, which agrees with Dow's 1847 map. Expect about ±50 m of uncertainty at the cove, North Beach and Mission Bay heads.
4. **Some sources disagree, and the notes record it.** Marina fill is dated "1851–1912 piecemeal + 1912" in one source and "filled for 1915" in another. The Crissy marsh has been dated to the 1870s and to 1911–14. NAS Alameda fill is given as 1936–40 and as "1945". Treasure Island start and finish dates differ by a few days between sources.
5. **Lake Merced is not fill.** It was a coastal lagoon that sometimes opened to the ocean: the 1869 USC&GS map shows an outlet, and a breach was reported in 1852. Spring Valley Water Co. dammed it from the sea in **1895** (SFPUC, via Wikipedia: <https://en.wikipedia.org/wiki/Lake_Merced>). Later causeways and road fills split it into North, South, East and Impound lakes. I found no dates for those, so they are not zoned. Use TIGER water.
6. **Ocean Beach.** The O'Shaughnessy seawall and Esplanade went up 1915/16–1928/29 and the Great Highway was paved in 1929. This is not bay fill, and the zone matters only if the c.1800 ocean shore lies east of today's.

## Downloaded datasets (all in `data/raw/`, gitignored)

| Folder | What | Licence / terms |
|---|---|---|
| `sfei_historical_ecology/` | **SFEI Historical Ecology compilation v2.3 (Feb 2026)**, from CDFW BIOS ds3201, FeatureServer <https://services2.arcgis.com/Uq9r85Potqm3MfRV/arcgis/rest/services/biosds3201_fpu/FeatureServer/0>, one GeoJSON per project (WGS84). Projects: **`historical_baylands.geojson`** (EcoAtlas c.1800 baylands from T-sheets, 783 polygons; classes Tidal/Salt Marsh, Tidal Flat, Shallow/Deep Water, Beach, Lagoon, Marsh Panne/Salt Flat, plus islands as "Grassland/Savanna"; covers lon −122.58…−121.83, lat **37.585**…38.247); `south_san_francisco_baylands_tsheets.geojson` (236 MB, 26,699 polygons: South Bay from 1857 and 1896 T-sheets, south of about 37.70); `petaluma_river`, `novato_creek_baylands`, `napa_valley`, `suisun_landscapes`, `alameda_creek`, `coyote_creek`, `santa_clara_valley_{west,south}`, `lower_walnut_creek`, `east_contra_costa_county` (which also include inland habitats: oak woodland, grassland, chaparral, wet meadow, riparian). Fields include `LegLabel`, `ClickLabel`, `Sources`, `InterpCert/ShapeCert/LocCert`. **This can replace extracting polygons from `pastpres2.pdf`.** | SFEI's data centre lists the compilation as free data under GPL v3 (<https://www.sfei.org/data/historical-ecology-gis-data-compilation>). The BIOS metadata asks users to cite SFEI and credit the originators (<https://filelib.wildlife.ca.gov/Public/BDB/GIS/BIOS/metadata/DS3201.html>). Add to SOURCES.md. |
| `sfei_hidden_nature_sf/` | **SFEI "Hidden Nature SF" (2021) pre-colonial habitats of northern San Francisco**, 450 polygons in 31 classes (mobile dunes, stabilised dune/scrub, coast live oak woodland, coastal prairie and scrub, serpentine chaparral, tidal marsh and flat, dune-dammed lakes, willow groves, …). Covers lat 37.733–37.817. Source: <https://services1.arcgis.com/8V9ShUQ1DGYVLtOg/arcgis/rest/services/Historical_habitats_dissolved_v3/FeatureServer/1>. Also **mobile-dune-sheet inland boundaries for 1852 and 1873** (`mobile_dune_sheet_boundary_featurecollection.json`, Web Mercator polylines). Project page: <https://www.sfei.org/projects/hidden-nature-sf>. **This is the best source for the SF landcover layer.** | No licence stated on the ArcGIS item. Treat as "cite SFEI, ask before redistributing" until clarified. |
| `usgs_ofr2006_1037/` | **USGS OFR 2006-1037 (Witter et al.), Quaternary deposits, central Bay Area, 1:24k.** File `of06-1037_4b.shp.zip`, layer `sfq2py`, **geographic NAD27 (EPSG:4267)**. Units: `af` (artificial fill, 2,089 polygons), **`afem` (fill over estuarine mud = bay fill, 501)**, `alf` (levee fill, 703), `ac`/`acf` (artificial channel or channel fill), `adf` (dam fill). `PTYPE2` gives the natural unit under the fill (for example `Qhbm` = bay mud). This is an independent check that a TIGER-vs-SFEI difference is real fill. It has no dates. | USGS, public domain. <https://pubs.usgs.gov/of/2006/1037/> |
| `usgs_fill/usgs_ofr90-253_marina.pdf` | USGS OFR 90-253, Marina District geology and history. Fig. 6 shows fill by age class, and the text dates the 1912 hydraulic fill to 13 Apr – Sep 1912. | Public domain. |
| `dow_1973/` | Dow 1973 thesis, PDF with a text layer. EPA SEMS doc 1137835. | The author permits reproduction for education and research. |
| `sf_historical_shoreline/` | SFPUC Flood Resilience layers: `sfpuc_historical_shoreline_ecoatlas.geojson` (EcoAtlas 1.5 shoreline as polylines, possibly shifted slightly in transfer) and `sfpuc_historical_waterbodies.geojson` (106 untyped polygons: historic lakes, lagoons and marshes of SF). <https://services.arcgis.com/Zs2aNLFN00jrS4gG/ArcGIS/rest/services/FloodMap/FeatureServer> | City and County of SF ArcGIS. No licence stated. |
| `bcdc/diked_historic_baylands_1982.pdf` | BCDC 1982 maps of diked historic baylands (1968–73 USGS quad base). No dates. | Public agency report. |

**Not obtained:**

- **USGS NEHRP report 07HQGR0078**, Hitchcock et al. 2008, *Detailed Mapping of Artificial Fills, SF Bay Area*. It explicitly "maps the progression of shorelines into the Bay". The USGS URL now returns 404, and the Wayback Machine and web.archive.org are blocked from this machine. **It is worth retrieving manually:** it is the only bay-wide source of dated fill progression I know of.
- NOAA georeferenced T-sheets (NSDE) for SF 1851–1869.
- SFEI's EcoAtlas "Historical Baylands (SFEI 2024)" app layer.

## Confidence per zone (dates; rings are approximate unless street-defined)

| zone_id | years | kind | confidence (dates) |
|---|---|---|---|
| `sf_ybc_1_montgomery_sansome` | 1849–1851.7 | fill | medium |
| `sf_ybc_2_sansome_battery` | 1850–1853 | fill | medium |
| `sf_ybc_3_battery_front` | 1852–1856 | fill | medium |
| `sf_ybc_4_front_davis` | 1853–1859 | fill | low |
| `sf_ybc_5_davis_eastst` | 1855–1869 | fill | low |
| `sf_seawall_broadway_mission` | 1884–1892.9 | fill | high |
| `sf_seawall_mission_harrison` | 1909.9–1915.4 | fill | high |
| `sf_rincon_east` | 1855–1890 | fill | low |
| `sf_seawall_harrison_king` | 1907.4–1914.9 | fill | high |
| `sf_south_beach_1864_1885` | 1864–1885 | fill | medium |
| `sf_china_basin_north_1903` | 1903.9–1905.4 | fill | high |
| `sf_pier46_block_1922` | 1922.1–1924.1 | fill | high |
| `sf_telegraph_hill_east` | 1853–1900 | fill | medium |
| `sf_north_beach_tidelands` | 1881–1915 | fill | medium |
| `sf_fishermans_wharf` | 1900.4–1917 | fill | medium |
| `sf_pier45` | 1928–1929.2 | fill | high |
| `sf_aquatic_park` | 1914–1939.1 | fill | high |
| `sf_fort_mason_lower` | 1909.1–1910.6 | fill | high |
| `sf_marina_east` | 1863–1906 | fill | medium |
| `sf_marina_cove_1912` | 1912.28–1912.7 | fill | high |
| `sf_marina_west_ppie` | 1911–1914 | fill | medium |
| `sf_marina_green` | 1912–1917 | fill | medium |
| `sf_crissy_field` | 1911–1915 | fill | medium |
| `sf_crissy_marsh_restored` | 1999–2000.9 | restored | high |
| `sf_soma_marsh` | 1852–1875 | fill | medium |
| `sf_mission_bay_north` | 1869–1890 | fill | medium |
| `sf_mission_bay_south` | 1884–1910 | fill | medium |
| `sf_mission_bay_16th_mariposa` | 1906.3–1912 | fill | low |
| `sf_mission_creek_marsh` | 1865–1900 | fill | low |
| `sf_china_basin_santa_fe` | 1901.4–1904 | fill | medium |
| `sf_mission_bay_east_point_san_quentin` | 1895–1930 | fill | low |
| `sf_mission_rock_pier50` | 1947–1950.7 | fill | high |
| `sf_potrero_point` | 1866–1900 | fill | medium |
| `sf_potrero_south_western_pacific` | 1906–1931 | fill | low |
| `sf_islais_reclamation_district` | 1925.3–1936 | fill | high |
| `sf_pier80_army_street_terminal` | 1963.7–1967 | fill | high |
| `sf_india_basin_boblitt_piers94_96` | 1962–1971 | fill | high |
| `sf_herons_head_pier98` | 1970–1978 | fill | low |
| `sf_herons_head_restored` | 1998–1999.9 | restored | high |
| `sf_station_p_india_basin` | 1929–1929.9 | fill | medium |
| `sf_india_basin_1965` | 1965–1966 | fill | medium |
| `sf_hunters_point_navy_wwii` | 1942–1945 | fill | high |
| `sf_hunters_point_parcel_e_south_basin` | 1945–1975 | fill | low |
| `sf_bayview_racetrack` | 1864–1874 | fill | medium |
| `sf_double_rock_war_housing` | 1943–1947 | fill | medium |
| `sf_gilman_griffith_cove` | 1930–1934 | fill | low |
| `sf_candlestick_cove_wwii` | 1942–1944 | fill | medium |
| `sf_candlestick_park` | 1956–1960.3 | fill | high |
| `sf_south_basin_post1965` | 1965–1975 | fill | low |
| `sf_treasure_island` | 1936.1–1937.65 | fill | high |
| `sf_ocean_beach_esplanade` | 1915.9–1929 | fill | low |
| `sf_embarcadero_piers` | 1880–1938 | pier | medium |
| `sm_bayshore_cutoff_yard` | 1904.8–1921 | fill | medium |
| `sm_brisbane_landfill` | 1932–1967 | fill | high |
| `sm_sierra_point` | 1965–1972 | fill | medium |
| `sm_oyster_point` | 1956–1970 | fill | high |
| `sm_sfo_mills_pasture_field` / `_west` (Mills estate marsh pasture: the 1927 Mills Field and the strip west of the Bayshore Highway) | 1905–1915 | fill | low (date between the 1892 survey and the 1927 lease) |
| `sm_sfo_tidelands_1930s` (diked airfield of the 1939 sheet, bayward of the c.1800 marsh) | 1930.5–1935 | fill | medium |
| `sm_sfo_seaplane_harbor_a/b/c` (WPA seaplane harbour shores, Coast Guard Air Station) | 1936–1940.5 | fill | medium |
| `sm_sfo_wartime_fill_a/b/c` (1939 extension + Army hydraulic fill, field of the 1946 sheets) | 1939.5–1943.5 | fill | medium |
| `sm_sfo_ne_fill` | 1946.5–1950.5 | fill | medium |
| `sm_sfo_1950s_shore_a/b/c` | 1947–1952.5 | fill | low |
| `sm_sfo_28L_extension_fill` | 1957–1960.5 | fill | medium |
| `sm_sfo_1R_north_fill` | 1957–1961.5 | fill | medium |
| `sm_sfo_28R_extension_fill_a/b/c` | 1968–1968.5 | fill | medium |
| `sm_foster_city_diked` | 1897–1901 | diked_marsh | medium |
| `sm_foster_city_fill` | 1961–1971 | fill | high |
| `sm_redwood_shores_salt` | 1902–1930 | diked_marsh | low |
| `sm_redwood_shores_fill` | 1963–1975 | fill | medium |
| `sm_bair_island_diked` | 1948–1952 | diked_marsh | high |
| `sm_bair_island_restored` | 1983–2015.95 | restored | medium |
| `al_oakland_long_wharf_mole` | 1868–1882 | fill | high |
| `al_key_route_mole_toll_plaza` | 1903–1936.9 | fill | low |
| `al_oakland_outer_harbor_army_base` | 1910–1942 | fill | medium |
| `al_naval_supply_center_middle_harbor_a…d` (depot ground of the 1946 sheet, north of the Inner Harbor entrance) | 1940–1941.95 | fill | medium |
| `al_middle_harbor_shoreline_park_a…i` (depot ground of the 1946–93 sheets that is water today) | 2000.5–2004 | restored | low |
| `al_middle_harbor_vision2000_a/b` (water to 1993, land today) | 2000–2004 | fill | low |
| `al_tidal_canal` | 1889–1902.7 | excavated | high |
| `al_alameda_airport_point` (training-wall strip, sand hook, Alameda Airport) | 1927–1929.2 | fill | low (extent from a 1939 aerial) |
| `al_alameda_benton_field_navy_fill` (Bay Airdrome marsh, Benton Field, Navy fill to Aug 1939) | 1930–1939.5 | fill | medium |
| `al_alameda_nas_inner_bay` (inner bay filled for the airfield) | 1939.6–1941 | fill | medium |
| `al_alameda_nas_1950s_extension_a/b/c` (jet-runway additions, 1946 → 1958 sheets) | 1947–1956.5 | fill | medium |
| `al_alameda_south_shore` | 1955.85–1960 | fill | medium |
| `al_bay_farm_reclaimed_marsh` (marsh round Bay Farm Island inside the 1939 levee, Alameda side) | 1900–1924 | fill | low |
| `al_oakland_airport_north_field` (North Field marsh, Oakland side) | 1926.8–1927.3 | fill | medium |
| `al_oakland_airport_navy_strip` (south of Maitland Drive, 1939 → 1946 sheets) | 1941.5–1944.5 | fill | medium |
| `al_oakland_airport_south_field_a/b` (South Field dike fill) | 1958.5–1961.5 | fill | medium |
| `al_oakland_hegenberger_marsh` (east of the Airport Channel, inside the old box) | 1950–1965 | fill | low |
| `al_bay_farm_nw_fill` | 1956.5–1959.5 | fill | medium |
| `al_bay_farm_harbor_bay_fill_a…d` (land on the 1968-photo sheets) | 1960–1967.5 | fill | medium |
| `al_bay_farm_harbor_bay_fill_1970s_a/b` (land on the 1973 / 1980 PRs) | 1968–1973 | fill | medium |
| `al_berkeley_waterfront_landfill` | 1923–1983 | fill | medium |
| `al_albany_bulb` | 1963–1987 | fill | medium |
| `cc_richmond_shipyards` | 1940.9–1943 | fill | medium |
| `mn_marinship` | 1942.2–1942.5 | fill | high |
| `mn_corte_madera_larkspur` | 1947–1970 | fill | low |
| `mn_hamilton_diked` | 1880–1932 | diked_marsh | low |
| `mn_hamilton_restored` | 2014.3–2014.4 | restored | high |
| `nb_petaluma_sonoma_baylands_diked` | 1860–1920 | diked_marsh | low |
| `nb_sears_point_restored` | 2015.8–2015.85 | restored | high |
| `nb_napa_marsh_diked` | 1860–1920 | diked_marsh | low |
| `nb_napa_salt_ponds` | 1950–1960 | diked_marsh | medium |
| `nb_napa_ponds_restored` | 2006–2015 | restored | medium |
| `nb_suisun_marsh_diked` | 1870–1930 | diked_marsh | low |
| `sb_salt_ponds_east_early` | 1853–1930 | diked_marsh | medium |
| `sb_salt_ponds_south` | 1920–1957 | diked_marsh | medium |
| `sb_island_ponds_restored` | 2006.2–2006.3 | restored | medium |
| `sb_eden_landing_restored` | 2011.7–2011.75 | restored | high |
| `fb_sf_county` | 1850–1965 | fill | low |
| `fb_peninsula_bayfront` | 1900–1970 | fill | low |
| `fb_east_bay` | 1870–1970 | fill | low |
| `fb_north_bay` | 1860–1970 | fill | low |

The SFO rows (2026-11) replace one box per period: each is the land added between two USGS editions
(1892 survey, 1939 photos at 1:62,500; 1946 / 1956 / 1968 PR / 1973 PR at 1:24,000), from a water-tint
mask of each sheet with the 1939 dike hand-traced, split from the c.1800 marsh (SFEI poster) and
buffered 30 m (earliest year per cell, so no gaps); years from the airport history (sources in the
rows), ending half a year before the researched pavement on them (`data/manual/airports`).
`data/manual/airports/tools/fillcheck.py` recomputes the zone years at the Mills Field points and under
every SFO pavement row without a terrain run.

Confidence levels:

- **high**: dated construction records (contracts, seawall tables, openings).
- **medium**: a documented bracket, or one secondary source.
- **low**: an inferred or interpolated bracket, conflicting sources, or a fallback.

## Alameda Point, Middle Harbor, Bay Farm Island and Oakland Airport (2026-11)

The boxes `al_alameda_nas`, `al_naval_supply_center_middle_harbor` (+ the restored `al_middle_harbor_shoreline_park` box),
`al_bay_farm_island_harbor_bay`, `al_oakland_airport_north` and `al_oakland_airport_south` are replaced by phases traced on
the USGS editions like the SFO zones (renders in a local metre frame with `airports/tools/render.py`, water-tint masks per
edition, ring = c.1800 wet ground that is land today, cut into the phases; hand lines where a sheet has no water tint):
* **The strait into Oakland was closed 1941–2003.** The terrain's restored-ground rule (fill under a `restored` ring that is
  water today is land from its fill year until the restoration) turned every water cell of the Middle Harbor box that a
  fill zone also covered into land — the NSC box reached across the Inner Harbor entrance channel, so the channel was
  land from 1941 to 2003. The NSC ring now stops at the channel, and the restored ring is the depot ground of the
  1946–93 sheets that is water in WorldCover 2021 (the berths, the widened channel edge) — and lies inside the NSC
  ring (a restored cell outside any specific fill ring would take the `fb_east_bay` fallback year: land from 1920).
* **NAS Alameda:** 1:24k Oakland West 1949 (1946 photos), 1959, 1968 PR … 1993 + the USGS aerial of 4 Aug 1939
  (UCSB via airfields-freeman.com, registered by hand on the 1946 sheet, ±150 m): the Alameda Airport's training-wall
  strip and sand hook (1927–29), the Bay Airdrome marsh / Benton Field / Navy fill east of the inner bay (land in Aug 1939),
  the inner bay filled for the airfield (1939–41), and the west / south additions of the 1958 sheet (jet runways).
* **Bay Farm Island / OAK:** marsh round the island on the 1896 survey, farmland and golf course (Alameda side) and the
  North Field (Oakland side, bought Feb–Apr 1927) inside the levee of the 1939-photo sheet; a Navy-era strip south of
  Maitland Drive (1946 sheet); the South Field dike fill (under construction on the 1959 sheet, airfield on the 1968 PR);
  the Utah Construction / Harbor Bay fills by edition (NW lobe diked on the 1956 photos; land on the 1968 / 1973 / 1980
  sheets). Check without a terrain run: OAK `pavement_dates.csv` rows keep their researched starts (the 1927 runway waits
  to 1927.5–1927.8 at most).

## Land cover table (`data/tables/landcover_history.csv`)

Columns: `area_id,name,region,cover,year_start,year_end,ring_type,ring,note,source_url`. `year_start = -10000` means "since before 1769".

- **Overlapping rows of the same area are a sequence.** For example, the Santa Clara Valley goes oak savanna → mission and rancho grazing (1777) → wheat (1850) → orchards (1885–1965). Napa goes vineyard 1860 → phylloxera and Prohibition orchards 1895 → vineyard 1965.
- **`year_end` is when the cover stops being natural or agricultural.** Usually that is urbanisation, and building years should take over from there. For dune districts it is a **midpoint estimate** of a building-out span, with the span given in `note`. Inner Richmond is c.1890–1915, Outer Richmond c.1906–45, Inner Sunset c.1900–30 and Outer Sunset c.1925–55. In practice, let building `start_year`s reveal the dunes block by block, and use `year_end` only where no buildings exist.
- **Rings are coarse.** For SF prefer `sfei_hidden_nature_sf`. For Napa, Santa Clara, Alameda Creek, Suisun and East Contra Costa prefer the SFEI project layers. They map oak woodland, grassland, chaparral and wetlands at c.1800 in detail.
- **Confidence:**
  - High: Golden Gate Park reclamation, Presidio forest, Oakland redwoods logging (1845–60), Point Reyes dairies from 1857, Mission Santa Clara 1777, the Santa Clara orchard peak, the Napa phylloxera and Prohibition dates.
  - Medium: Contra Costa wheat and walnuts, Livermore vineyards, Woodside logging.
  - Low: Eden Township orchards, Sonoma dates, Western Addition dunes, the regrowth start years.
- **Gaps:**
  - Alameda Washington Township (Fremont) farms.
  - San Mateo bayside and coastside farms and dairies.
  - Cow Hollow dairies (1860s–1890s, unsourced).
  - Eucalyptus plantations, which are not a `cover` value. Sutro's from 1886 and the East Bay's 1880s–1910s plantings are mentioned in notes.
