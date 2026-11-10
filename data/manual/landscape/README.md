# Landscape history: dunes, water, agriculture

These files hold researched data meant to replace the terrain's rule-based guesses. Three of those rules are being retired:

- In `terrain_tiles.py`, every flat cell outside SF becomes farmland in 1852–62, and a hard-coded Santa Clara Valley box becomes orchard in 1878–93.
- The SF dune rule stops at the county line.
- Lake Merritt, the estuary and the reservoirs carry no dated events.

The geometry here comes from real maps wherever such a map exists. Anything generalised is labelled `estimated`.

Built by `pipeline/landscape.py` (dunes), `pipeline/landscape_water.py`, `pipeline/landscape_broek.py` and `pipeline/landscape_agriculture.py`. Run all of them with `python pipeline/landscape.py all`. Each stage is idempotent. Caches are kept in `data/interim/landscape/`.

| File | What |
|---|---|
| `agriculture.geojson` | Dated agricultural land use for the five modelled counties' farm belts, plus the south Santa Clara Valley. One feature per (place, era). |
| `broek_1931_landscape_types.geojson` | A tracing of Broek's (1932) *Schematic map of landscape types of the Santa Clara Valley, 1931*. It covers all classes, including bay marshes, cities and the range-front "border landscapes". |
| `dunes.geojson` | The historic (pre-urban) sand dunes of the region. |
| `valley_floor_extra.geojson` | **Estimated** farm-ground outlines where no Quaternary map exists (Santa Cruz County: Pajaro Valley floor and bottoms, the coast terraces) or where the farm belt lies on low hills mapped as bedrock (Gold Ridge, Montezuma Hills). Derived from the terrain grid; read by `landscape_agriculture.valley_floor()`. See *Ten-county extension*. |
| `water_history.csv` | Dated water: lakes and reservoirs, the dredged estuary and harbours, the Tidal Canal, salt-pond complexes and diked baylands. |
| `south_bay_salt_phases.geojson` | The South Bay salt-pond and diked-bayland phases (San Lorenzo Creek → Ravenswood), dated from the USGS 1896–1961 sheets, the 1907 Coast Survey chart and the salt-industry histories; source of the `sb_*` rows of `water_history.csv`. See `README_south_bay_baylands.md` (decade-by-decade history, evidence, recommended code changes). |

---

## 1. `agriculture.geojson`

### Properties

| Property | Meaning |
|---|---|
| `kind` | One of `grain`, `hay`, `orchard`, `vineyard`, `pasture_dairy`, `vegetables`, `nursery`, `farm_mixed`. |
| `crop` | Free text, e.g. "wheat and barley (dry-farmed)", "hops (trellised hop yards)". |
| `year_start` | The first year the use appears in the feature. |
| `year_full` | The year the change was complete across the whole feature. For each cell, spread the change between `year_start` and `year_full`. Use a smooth, spatially coherent noise (field-sized blobs of 200–500 m), not per-cell white noise. |
| `year_end` | Empty means the use lasted until the land was urbanised; buildings date that. A value is set only where the crop itself went away, e.g. hops 1925, Alvarado beets 1967, foothill vineyards around 1900. After `year_end` the cell falls back to the previous active feature. |
| `share` | The fraction of the feature's cells in this use. Paint a hash/noise share of the cells. The rest keep the previous era, e.g. vineyards were 35 % of the gravelly foothill fans. |
| `orchard_share` | For `farm_mixed` only: the part of `share` that should be drawn as orchard trees. |
| `layer` | The evidence behind the feature (next table). |
| `district` | The farm district id (see the districts table). |
| `confidence` | `mapped_1940s`, `mapped_1931`, `mapped_today` (OpenStreetMap outline, estimated dates) or `estimated` (geometry and/or dates generalised). |
| `snapshot_year` | 1931 for Broek features. |
| `source`, `source_url`, `note` | Where the feature comes from, and why. |

### Layers, best evidence first

| Layer | Geometry | Dates |
|---|---|---|
| `topo_1940s` | **Real.** Orchard and vineyard extents (green dot / vine screen) from the USGS 1:24,000 and 1:62,500 topographic maps of 1939–56. They were extracted by the topo-farmsteads stage into `data/manual/farmsteads/topo_orchards.geojson`, read-only here. | Start comes from the district's orchard era. Where Broek's 1931 map shows small crops or pasture at the same spot, the orchard was planted after 1931: `year_start` 1932, `year_full` 1945. |
| `broek_1931` | **Traced.** Broek's 1931 landscape types for Palo Alto → Gilroy (→ Hollister): orchard formation, orchards mixed with small crops, small crops, pastures, and the northern Santa Cruz foothills. Pieces covered by a topo orchard are removed, because the topo is more precise. | `year_start`/`year_full` come from the district history. |
| `district_era` | **Estimated generalisation.** A district's era painted on its valley floor. The valley floor is the USGS Quaternary geology (Witter et al. 2006, plus Knudsen et al. 2000 outside it). It is split by soil drainage: **fan** (Holocene fans, levees, terraces: the loams of the wheat belt and later the orchards); **basin** (basin clays near the bay, "adobe": pasture, hay, dairies, truck crops); **upper_fan** (Pleistocene fans and terraces at the foothills: the gravelly belt, brush until about 1870, then vineyards). | Researched per district, with the source in `source_url` / `note`. |
| `special` | Estimated rings around documented special crops: Pleasanton hops, the Niles nursery, Redwood City flower nurseries, Bay Farm Island asparagus, Alvarado sugar beets. | As cited. |
| `osm_today` | **Real, but today's.** Vineyards and orchards as mapped in OpenStreetMap (`landuse=vineyard` / `orchard`, via Overture `region5_land_use.parquet`), merged across block roads; only in the districts of the ten-county extension. Not restricted to the valley floor (hill vineyards are real). | `year_start` / `year_full` = the district's modern planting era (`osm` in the district dict) - **estimated**; `confidence` = `mapped_today`. |

**How features combine.** At a given year, a cell takes the active feature with the latest `year_start`. On ties, use the order `special` > `topo_1940s` > `broek_1931` > `district_era`. A feature with `share` < 1 applies only to its share of the cells; the remaining cells keep the earlier feature. So the grain era is the base layer, and orchards, vineyards and truck crops are drawn over it. The valley-floor geology is the extent of "flat farmland". All features are clipped off the SFEI c.1800 bay, flats, marsh and natural salt ponds; diked baylands are in `water_history.csv`. Hills stay natural or grazed grassland, which is what they were. Grazing does not change the look, so there are no hill features except West Marin's dairy valleys.

**Mapping to terrain covers.** `grain` and `hay` → FARM; `vegetables` and `nursery` → FARM (or a greener field colour); `pasture_dairy` → PASTURE; `orchard` → ORCHARD; `vineyard` → VINEYARD; `farm_mixed` → FARM with `orchard_share` drawn as ORCHARD.

**District boundaries** are the Voronoi cells of the district seeds. They are straight lines and **estimated**. Two neighbouring districts with different dates meet along a straight line. The `year_start`/`year_full` spread with blob noise hides it. Do not use the raw `year_start` for every cell.

### Districts and eras

All dates are `estimated` unless the row's `note` cites a dated event. Sources are in each feature's `source_url`.

| District | Grain / hay on the fans | Clay lowland | Orchards (start → full) | Vineyards | Other |
|---|---|---|---|---|---|
| `scv_san_jose` (Santa Clara, San José, Willow Glen) | 1852→58 | pasture / dairy 1853 | 1872→1890 (Willows 1868; ~1,100 acres of orchard by 1863) | – | strawberries / truck from 1868 |
| `scv_campbell_los_gatos` | 1853→60 | pasture 1855 | 1878→95 (first foothill orchard 1875) | upper fans 1872–1900, 35 % | |
| `scv_west` (Mountain View, Sunnyvale, Cupertino, Los Altos, Saratoga) | 1853→62 | pasture 1855 | 1886→1905 | foothill belt 1872–1902, 35 % | |
| `scv_bayside` (Alviso, Agnew, lower Milpitas) | 1855→62 | pasture / dairy 1853 | 1900→20 (topo only) | – | small crops 1868→ |
| `scv_milpitas_berryessa` | 1854→60 | pasture 1854 | 1890→1915 | – | small crops 1880→ |
| `scv_evergreen` | 1855→62 | pasture 1855 | 1895→1915 | 1880–, 30 % | |
| `scv_coyote` (Edenvale, Coyote) | 1865→80 (cattle range before) | pasture 1850 | 1895→1915 | – | |
| `scv_morgan_hill` | 1868→85 | pasture 1850 | 1898→1920 | 1885–, 15 % | |
| `scv_gilroy` | 1860→70 | dairy 1863 | 1900→22 | 1880–, 15 % | |
| `pen_palo_alto` | 1853→60 | pasture 1853 | 1888→1905 | – | Stanford's Palo Alto Stock Farm, hay and paddocks, 1876 |
| `pen_menlo_atherton` | 1853→60 | pasture 1853 | – | – | country estates 1865 (50 %) |
| `pen_redwood_city` | 1855→62 | hay 1855 | – | – | flower nurseries 1905–65 (special) |
| `pen_san_mateo` | 1855→62 | dairy 1855 | – | – | estates 1868 (50 %) |
| `pen_millbrae_san_bruno` | 1858→65 | dairy 1858 | – | – | dairy pasture on the whole floor 1860 |
| `pen_colma` | 1858→65 | – | – | – | truck gardens 1870 (80 %) |
| `pen_coast` (Half Moon Bay) | 1855→65 | pasture 1855 | – | – | artichokes / sprouts 1920 |
| `eb_oakland_berkeley` | 1852→56 | pasture 1852 | – | – | towns soon replace it |
| `eb_san_leandro` | 1851→55 | vegetables 1880 | 1868→90, **estimated 60 % of fans** (the 1947 topos print no vegetation) | – | cherries ("Cherry City") |
| `eb_hayward` (Hayward, Mt Eden, San Lorenzo, Castro Valley) | 1852→56 | vegetables 1880 | 1870→95, **estimated 55 %** | – | apricots, cherries; row crops |
| `eb_washington` (Alvarado, Newark, Centerville, Irvington, Niles, Mission San José) | 1853→58 | vegetables / sugar beets 1879 | 1885→1910 (topo) | Mission San José / Warm Springs 1880–1920, 35 % | Niles nursery 1884–1970; Alvarado beets 1870–1967 |
| `eb_livermore` | 1865→72 | pasture 1860 | – | gravelly south side 1882–, 25 % (+ topo) | |
| `eb_pleasanton` | 1860→68 | pasture 1860 | – | – | hops 1888–1925 (special) |
| `eb_dublin_san_ramon` | 1860→68 | pasture 1860 | – | – | |
| `cc_west` (San Pablo, Pinole) | 1855→62 | dairy 1855 | – | – | |
| `cc_martinez` (Alhambra Valley) | 1855→62 | pasture 1855 | 1880→1900 | 1880–1920, 30 % | |
| `cc_walnut_creek` | 1855→60 | pasture 1855 | 1895→1925, **estimated 50 %** where the 1947 topo is blank | – | walnuts, pears, apricots |
| `cc_concord_clayton` | 1855→62 | pasture 1855 | 1900→25 | 1885–1920, 35 % | walnuts replaced vines after 1919 |
| `cc_danville` | 1858→65 | pasture 1858 | 1900→25 | – | |
| `cc_oakley_antioch` | 1870→80 | pasture 1870 | 1905→25, estimated 30 % | Oakley sands 1895–, 40 % | |
| `cc_brentwood_byron` | 1870→80 | pasture 1870 | 1916→30, estimated 40 % | – | alfalfa / dairies after irrigation, 1916 |
| `mn_novato` | 1856→62 | pasture 1856 | 1858→70, estimated 15 % (LOW) | – | |
| `mn_san_rafael` | 1855→60 | dairy 1855 | – | – | |
| `mn_west` (Point Reyes, Nicasio, Tomales) | – | dairy 1857 | – | – | Shafter–Howard dairy leases from 1857 |
| **Ten-county extension** (below: further eras as *crop start→full, share*) | | | | | |
| `son_petaluma` | 1852→58 | pasture / dairy 1855 | – | OSM 1975→2005 | chicken ranches 1885→1915 (60 %, to 1965; Byce incubator 1879); dairy pasture again 1958→75 |
| `son_sonoma_valley` | 1850→58 | hay 1860 | prunes / pears / hay mixed 1895→1920, 50 % of the fans | benches 1858→80, 50 %; fans 1860→80, 25 %; replanting 1968→95, 55 % + OSM | Buena Vista 1857; ~4,000 acres of vines by 1900 |
| `son_santa_rosa_plain` | 1853→60 | pasture / dairy 1855 | prunes, pears, apples 1890→1915, 35 % | 1972→2000, 12 % + OSM | hops 1880→95 (10 %, to 1950); pasture / rural after 1962→80 |
| `son_gold_ridge` (Sebastopol, Graton, Forestville) | 1855→65 (potatoes, grain) | pasture 1855 | **Gravenstein apples 1890→1915, 60 %** | OSM 1985→2010 | ground = estimated outline of the low hills; orchards pulled 1975→2005 |
| `son_russian_river` (Healdsburg, Windsor) | 1856→62 | pasture 1856 | prunes 1895→1925, 50 % ("Buckle of the Prune Belt") | benches 1872–, 40 %; replanting 1970→95, 60 % + OSM | hops 1880→95 (15 %, to 1952) |
| `son_dry_creek` | 1858→65 | pasture 1858 | prunes 1900→25, 60 % | benches 1870–, 35 %; 1972→95, 70 % + OSM | |
| `son_alexander_valley` (Geyserville, Cloverdale) | 1856→65 | pasture 1856 | prunes 1895→1925, 50 % | benches 1881– (Asti), 35 %; 1965→95, 65 % + OSM | hops 1885→1900 (10 %, to 1950) |
| `son_coast_dairy` (Bodega, Valley Ford, Bloomfield, Tomales) | 1853→60 (potatoes, oats) | pasture 1855 | – | – | dairy pasture on the whole floor 1865 |
| `son_coast_north` (Jenner → Gualala terraces) | – | – | – | – | sheep / cattle pasture 1860 |
| `napa_lower` (Napa, Carneros, American Canyon) | 1850→56 | hay 1856 | prunes, pears, cherries 1890→1915, 25 % | benches 1868–, 30 %; OSM 1968→95 | |
| `napa_valley_mid` (Yountville → St. Helena) | 1852→58 | pasture 1855 | prunes / walnuts 1898→1925, 20 % | **first boom 1868→85, 50 %**; OSM 1965→90 | 443 vineyards by 1880; phylloxera 1890s; Prohibition 1920 |
| `napa_calistoga` (+ Knights Valley) | 1855→62 | pasture 1855 | prunes / walnuts 1900→25, 20 % | 1875→90, 35 %; OSM 1968→95 | |
| `napa_pope_berryessa` | 1866→72 | pasture 1860 | – | OSM 1975→2000 | Berryessa Valley floor is under the lake (not drawn) |
| `sol_benicia_vallejo` | 1850→56 | pasture 1855 | – | – | |
| `sol_suisun_green_valley` | 1852→58 | pasture 1855 | cherries, pears, apricots 1880→1900, 45 % + OSM | benches 1860–1920, 20 %; OSM 1975→2005 | |
| `sol_vaca_valley` | 1851→58 | pasture 1855 | **early fruit 1875→90, 40 %** + OSM | – | pasture after 1955→80 (30 %) |
| `sol_dixon` (Dixon, Elmira, Maine Prairie) | 1855→65 (dry-farmed) | pasture 1860 | OSM orchards (walnuts, almonds) 1965→2005 | – | irrigated alfalfa, dairies, beets, tomatoes 1915→65 (60 %) |
| `sol_montezuma_hills` | dry-farmed wheat / barley with sheep 1862→75, 60 % | pasture 1860 | – | – | ground = estimated outline; years UNVERIFIED |
| `sol_delta` (Rio Vista, Ryer Island, Cache Slough) | – | swamp pasture 1862 | – | – | reclaimed: asparagus, beans, corn, grain 1872→1915 (90 %) |
| `cc_delta_islands` (Jersey → Byron tracts, Bethel Island) | – | swamp pasture 1860 | – | – | reclaimed peat: asparagus, potatoes, beans, celery 1872→1915 (90 %) |
| `scz_pajaro_valley` | 1852→58 (wheat, potatoes) | pasture 1855 | **apples 1890→1910, 50 %** + OSM | – | sugar beets 1888→92 (30 %, to 1900; Spreckels factory 1888–98); berries / lettuce 1925→65 (40 %) |
| `scz_soquel_aptos` | 1855→65 | pasture 1855 | orchards / poultry / bulbs mixed 1900→20, 50 % | – | |
| `scz_north_coast` (Santa Cruz → Waddell terraces) | – | – | – | – | dairy pasture 1860; Brussels sprouts / artichokes 1920→40 (55 %) |
| `scz_mountains` | – | – | OSM 1885→1905 | OSM 1970→95 | logging: `landcover_history.csv` `scz_*` |
| `scv_gilroy` (addition) | | | | | seed farms, garlic, row crops 1945→70 (50 %) |

### Broek 1931 tracing (`broek_1931_landscape_types.geojson`)

**Source.** J.O.M. Broek, *The Santa Clara Valley, California: a study in landscape changes* (Utrecht, 1932). The dissertation is open access at the Utrecht University Repository (<https://dspace.library.uu.nl/handle/1874/302720>). The tracing uses Plate II, Map III, at 1:420,000; the scan is `data/raw/landscape/broek1932_plate2.jpg`.

**Classification.** Each pixel is classified from the texture of its 1.6 km neighbourhood:

| Pattern on the map | Class |
|---|---|
| Long horizontal lines | orchard formation |
| Dashed lines | orchards mixed with small crops |
| Sparse dots | small crops |
| Dense dot grid | bay marshes |
| Blank | pastures |
| Crosshatch | cities |
| Half-tone with `\\\` hatching | Diablo range front, grass-covered |
| Half-tone with `///` hatching | southern Santa Cruz / Gabilan range front, wooded |
| Half-tone with `///` and horizontal hatching | northern Santa Cruz foothills, with residential and agricultural settlement |

The class raster then gets two majority filters. Town blobs smaller than 0.4 km² are reassigned to their surroundings.

**Georeference.** An affine fit to 15 town symbols. The RMS is about 0.7 km and the maximum 1.1 km; the map itself is schematic. A check overlay against the 1948–55 topo orchards shows the topo orchards falling inside Broek's orchard formation.

**Area check.** Orchard formation is 556 km² and orchards mixed with small crops 311 km², both including San Benito County. Broek gives 103,000 acres (417 km²) of orchards in Santa Clara County in 1930.

**Limits.**
- Units are generalised. The orchard formation includes farmsteads, roads and villages.
- The bottom of the map (Bolsa de San Felipe, Hollister) is San Benito County and lies outside the model.
- Broek's Map II (simplified soils, after Cosby) was **not** traced. Its belts are the same as the geology split used here.

### Ten-county extension (2026-11)

Districts were added for Sonoma, Napa, Solano and Santa Cruz counties, the Delta tracts of Contra Costa and the Montezuma Hills (24 districts, table above), in the same form as the first 33. What is different:

- **Farm region** (`farm_region()`): the hand outline of the first five counties plus the whole of Sonoma, Napa, Solano and Santa Cruz and the rest of Marin, Contra Costa and Santa Clara (TIGER county outlines) - without the Diablo Range valleys of Henry Coe State Park. New seeds change the Voronoi cells of four old districts on purpose: `mn_novato` no longer paints Petaluma and the Sonoma Valley baylands, `mn_west` ends near the county line (Tomales goes with the Bodega dairy belt), `cc_oakley_antioch` / `cc_brentwood_byron` give the Delta tracts to `cc_delta_islands`.
- **Valley floor**: USGS OF 00-444 (Knudsen 2000) covers Sonoma, Napa, Solano, east Contra Costa and south Santa Clara with the same classes. Santa Cruz County is "not mapped" there, and two farm belts lie on low hills the map shows as bedrock. For these `valley_floor_extra.geojson` holds **estimated** outlines (83 polygons), made from the terrain grid (USGS 3DEP, 76 m cells: `data/interim/grid_region_elev.npy`) and ESA WorldCover 2021 inside hand-drawn rings, used only where the geology gives no valley floor:

  | `area` | class | rule inside the ring | km² |
  |---|---|---|---|
  | `pajaro_valley_floor` | fan | 8–70 m, slope < 2.5°, no tree cover, Santa Cruz County side of the river | 56 |
  | `pajaro_valley_bottom` | basin | 1.5–8 m, slope < 2° (Watsonville / Harkins / Struve sloughs) | 13 |
  | `santa_cruz_north_coast_terraces` | upper_fan | 10–150 m, slope < 5°, no tree cover (Wilder Ranch → Waddell Creek) | 15 |
  | `santa_cruz_mid_county_terraces` | upper_fan | 6–130 m, slope < 4°, no tree cover (Live Oak, Soquel, Aptos, La Selva) | 20 |
  | `gold_ridge` | upper_fan | 25–280 m, slope < 8° (Wilson Grove Formation sandy loam west of the Laguna de Santa Rosa) | 130 |
  | `montezuma_hills` | upper_fan | 6–100 m, slope < 9°, WorldCover grass / cropland | 231 |

  The real maps to replace them: Brabb (1997), *Geologic map of Santa Cruz County* (USGS OF 97-489, digital) for the alluvium and marine terraces; the USDA soil surveys (Goldridge series, Sonoma County 1972; Solano County 1977).
- **`eras`**: a district can list further eras (hops, prunes, apples, poultry, row crops, replanting …), each on named soil classes with a share. The shares are nested (the terrain uses one blob field), so a later era with a larger share replaces an earlier one with a smaller share on the same soil - prunes over the phylloxera / Prohibition vineyards, vineyards over the prunes after 1965. Hops are drawn as `vineyard` (trellis rows), like Pleasanton's.
- **`osm_today`**: today's vineyards and orchards are real OpenStreetMap outlines (Napa 191 km² of vineyards - about the county's bearing acreage; Sonoma 107 km², roughly half of it; Solano orchards 136 km²), dated by the district's modern planting era. Where OSM is thin (Sonoma) a district-level replanting era fills in by share.
- **Checked against acreage** (district eras × share): Napa first-boom vineyards 73 km² (≈ 18,000 acres c.1890), Napa prunes / walnuts 53 km², Sonoma prunes and other tree fruit ≈ 120 km², Sonoma hops ≈ 20 km², Gold Ridge apples 77 km², Pajaro apples 28 km² (Santa Cruz County side), Petaluma chicken ranches 54 km².
- **Related rows elsewhere**: redwood logging and second growth in `data/tables/landcover_history.csv` (`scz_san_lorenzo_redwoods` –1905, `scz_aptos_soquel_redwoods` –1923, `scz_north_coast_redwoods` –1915, `son_russian_river_redwoods` –1900, `son_coast_redwoods` –1910; only the Nisene Marks dates are documented, the others estimated); Suisun Marsh diking in `water_history_extra.csv` (`suisun_marsh_diked`, 1890, LOW).

**What the terrain does with it - needs a change in `terrain_tiles.py`.** The terrain keeps, per cell, only the *first* and the *last* farm era of this file. The new valleys have three or four (grain → vineyards / hops → prunes or apples → vineyards or pasture), so the middle eras - the prune and apple decades of 1900–1965 - are dropped wherever a later era or an OSM vineyard covers the cell. The terrain has four change slots per cell; keeping the era before the last one as well (first, previous, last) shows the full sequence. Once that is in, the four ring rows `napa_vineyards_first_boom`, `napa_orchards_prohibition`, `napa_vineyards_modern` and `sonoma_valley_vineyards` of `landcover_history.csv` should go: they paint every cell of their rings, hills included, and override the shares and the real vineyard outlines.

**Not drawn / needs real mapping later**

- **The Delta's natural state and per-island reclamation years.** The c.1800 layers stop at Suisun Bay; the tule marsh of the Delta tracts has no natural cover here, and each tract has its own levee history (Bethel Island 1859–70, Franks Tract 1902–06 and flooded 1938, Big Break flooded 1928). Source to trace: the Delta Atlas (DWR 1995) or Thompson (1957), *The settlement geography of the Sacramento–San Joaquin Delta*; SFEI's Delta historical ecology GIS (2012) for the c.1800 habitats.
- **East Contra Costa orchards and the Oakley vineyards** stay on the first pass (share of the fans); the 1950s–70s USGS sheets (Brentwood, Woodward Island, Antioch South) carry the orchard tint.
- **Orchard, hop-yard and vineyard extents before 1960 in the four new counties** are shares, not mapped extents. The 1:62,500 and 1:24,000 topo editions of 1942–58 (Sebastopol, Healdsburg, Santa Rosa, Rutherford, St. Helena, Fairfield, Vacaville, Watsonville West / East …) print the green orchard / vineyard pattern and can go through `topo_farmsteads.py` like the first 68 sheets; for the 1870s–90s the Thompson (1877) and Reynolds & Proctor (1897) atlases of Sonoma County and the 1895 Napa County map.
- **Berryessa Valley** (wheat farms 1866–1957) lies under the lake; the 1940s Capell Valley / Lake Berryessa sheets would give the valley floor.
- **Fort Ross**: the Russian fields and orchard (1812–41, a few hundred acres) on the terrace around the fort.
- **Petaluma's chicken ranches** stood mostly on the low hills west and north of the town (Two Rock, Penngrove, Cotati), which are bedrock on the geology map and not painted; the 1942–54 topo sheets show the long hen houses.
- **Santa Cruz Mountains ridge-top vineyards and orchards** of 1860–1920 (Vine Hill, Ben Lomond Mountain, Skyline, Corralitos) - only today's mapped ones are drawn.
- **Coast dairies on the hills** (Marin–Sonoma, Santa Cruz north coast above the terraces) and the **sheep range of the Montezuma Hills and Carneros** look like grassland and have no feature, as in West Marin.
- **Natural cover of the new valleys** (valley-oak savanna of the Santa Rosa Plain and Napa Valley, the Laguna de Santa Rosa wetlands, the Pajaro sloughs) is left to the terrain's general rules; only Napa has a `landcover_history.csv` oak row.
- **Dates marked UNVERIFIED** in the notes: Montezuma Hills grain, Dixon irrigation, the Sonoma coast and Santa Cruz north-coast redwood end years.

### Known limits of the agriculture layer

- **The 1947 East Bay sheets carry no vegetation overprint.** These are Hayward, San Leandro and Walnut Creek, so the orchards of Eden Township and Walnut Creek are an **estimated share of the fans**. The fix is the 1:62,500 15′ editions of about 1940–43, if they carry the green tint, or the 1939 USDA aerial photos (UCSB FrameFinder).
- **Some topo sheets under-detect orchards.** Mountain View 1953 yields only 35 ha. The topo-farmsteads README describes the detector's recall limits. In the Santa Clara Valley, Broek's orchard formation fills the gaps.
- **Brentwood 1954 and Redwood Point 1948 had no orchards when built.** The topo stage was still running. Re-run `python pipeline/landscape.py agriculture` after `topo_farmsteads.py export`; nothing here needs editing.
- **c.1870–1900 vineyards in the vanished foothill belts are a share of the upper fans, not mapped vineyards.** The belts are Cupertino, Saratoga, Los Gatos, Mission San José, Concord and Martinez. Mapped extents would need the Thompson & West 1876 atlas or the 1880s viticultural-commission reports.
- **Rancho-era grazing (1797–1850s) is not a feature.** It looks like the natural grassland. Mission fields were a few hundred acres at most (Mission Santa Clara: about 100 acres of grain in 1790 and 250–330 acres in 1824–26, per Broek pp. 47–48).

---

## 2. `dunes.geojson`

### Properties

| Property | Meaning |
|---|---|
| `kind` | `mobile_dune` (open sand), `stabilized_dune` (sand with dune scrub, grass or oaks) or `dune_slack` (wet hollows). |
| `name`, `region`, `unit` | The geologic unit or SFEI habitat class. |
| `confidence` | `mapped` or `estimated`. |
| `source`, `source_url`, `note` | Where the polygon comes from. |
| `year_start` / `year_end` | Empty. Buildings, parks and golf courses already date the end of the dunes in the terrain. Notes say what replaced them. |

### Sources, in priority order

1. **Northern San Francisco (north of 37.733°N).** SFEI *Hidden Nature SF* (2021) pre-colonial habitats: "Mobile dunes", "Stabilized dune/dune scrub/grassland" and "Dune slack" (`data/raw/sfei_hidden_nature_sf/`). This is the same layer the terrain already uses; it is here so the dune extent is in one file.
2. **Southern San Francisco and Daly City, 37.625–37.75°N.** Bonilla (1998), *Preliminary geologic map of the San Francisco South 7.5′ quadrangle*, USGS Open-File Report 98-354, unit **Qd** (dune sand). Two parts:
   - The dunes west of Lake Merced, Fort Funston and the coastal strip to Mussel Rock are `mapped`.
   - The sand hills on the Colma Formation (**Qc**) west of the Colma valley are `estimated`. They lie east of Lake Merced, in Parkside, Ingleside and Daly City's Westlake. The extent is the geologic unit clipped to the Junipero Serra / I-280 corridor. They were levelled by the 1910s–50s tract builders, including Doelger's Westlake from 1949.
   - **This is the dune continuation past the county line.** The Colma valley itself was truck gardens and then cemeteries; see `pen_colma`.
3. **Central Bay region.** Witter et al. (2006), USGS OFR 2006-1037, units **Qds**, **Qhds** and fill over dune sand. This covers:
   - The **Merritt Sand** ridges of Alameda (the "Encinal"), downtown Oakland around Lake Merritt, and Bay Farm Island. These are **stabilized**: oak groves and grass on sand, not open dunes.
   - The Pacifica / Half Moon Bay coast dunes.
4. **Where Witter does not map.** Knudsen et al. (2000), USGS OFR 00-444 (nine counties), **Qds/Qhds/ads**. This covers:
   - The **Antioch–Oakley–Brentwood sand sheet**: `stabilized`, farmed for vineyards and almonds.
   - The Point Reyes / Dillon Beach coastal dunes.
   - Año Nuevo.
5. **Antioch Dunes.** The tall active river-front dunes, quarried from the late 1800s. This is an `estimated` strip of the Qds sheet along the San Joaquin. The Antioch Dunes NWR was established in 1980.

**Datum.** All geologic maps are NAD27. They are shifted to WGS84 with the NADCON grid (`data/raw/proj/us_noaa_conus.tif`).

### Recommended terrain rule

Replace `sf_dunes = in_sf & (lon < -122.445) & (elev < 120)` with these polygons as natural cover:

- `mobile_dune` → DUNES.
- `stabilized_dune` → DUNES only in SF, Daly City and on the coast. In Alameda and Oakland keep oak / grass, perhaps with a sandy tint. On the Delta sand sheet use grass.
- `dune_slack` → WETLAND.

---

## 3. `water_history.csv`

### Columns

`area_id, name, cover, year_start, year_end, confidence, ring_type, ring, area_ha, note, source_url`

- **`cover`** is `lake`, `shallow_water`, `salt_pond` or `diked`. It applies from `year_start` until `year_end`; `9999` means still today.
- **`ring_type`** is `lonlat`; `ring` is `lon lat; lon lat; …` (not closed).
- **Multi-part areas** have one row per part (`_1`, `_2`, …).
- **`confidence`** is the confidence in the date: `high`, `medium` or `low`.

### Where the geometry comes from

- **Lakes and reservoirs.** OpenStreetMap water polygons via Overture 2026-10 (`data/raw/landscape/overture_water.parquet`).
- **Dredged water.** Today's water inside a coarse area ring, minus the SFEI c.1800 open bay. That leaves exactly the marsh and flat that became water.
- **Salt ponds and diked land.** SFEI c.1998 baylands (`data/interim/baylands_1998.geojson`) clipped by complex rings. Ponds are joined across their levees, giving one polygon per complex.
- **Hand rows (`water_history_extra.csv`, 2026-11 audit, 25 rows).** Same columns; `landscape_water.py` appends them as they are. Outlines are the terrain grid's own water cells (WorldCover), one row per water body. They cover what the two rules of the terrain get wrong when no row exists:
  - *water today that no c.1800 layer covers* is taken for a post-war pond (default 1945–65). That is wrong for natural lakes — **Lake Merced** (3 parts, 107 ha), **Rodeo Lagoon**, **Abbotts Lagoon** get `year_start` 1700 = "always" — and too late or early for **Lake Anza 1938**, **Cull Canyon 1963**, **Don Castro 1964** and an arm of Upper San Leandro Reservoir (1926) that the OSM ring misses;
  - *water today on ground a c.1800 layer maps as dry or wet meadow* never becomes water at all: **Shadow Cliffs Lake 1971** (Kaiser gravel pit, park opening), the **Quarry Lakes / Niles gravel pits 1976** (ESTIMATED: the year the gravel company's pumping was stopped), **Lake Elizabeth 1969** — only its cells on the SFEI wet meadow; the cells SFEI maps as the perennial pond of Stivers Lagoon are left out, so the lagoon stays water before 1969 (the earlier `lake_lake_elizabeth` rows, which dried the lagoon, stay dropped).
  - Not dated yet (no row, so still default or never water): the Pleasanton–Livermore gravel-pit lakes (Lake I, Cope Lake, Lake H … about 370 ha), the Sunol pits, Almaden Lake and the Santa Clara Valley percolation ponds, Mallard Reservoir, Bear Gulch, Cherry Flat, Lake Ranch, Grant Lake, Sandy Wool Lake, Boronda Lake, Lake Lucerne.

### Rows

| Group | Rows |
|---|---|
| **Oakland / Alameda** | Lake Merritt, lake from **1869** (12th St dam 1868–69; marsh / slough before). Lake Merritt Channel, 1869. Inner Harbor from the estuary mouth to Clinton Basin, **1878** (harbor authorised 1873; training walls 1874; channel 20 ft by 1877). Brooklyn Basin and the upper estuary, 1890 (LOW). Tidal Canal, **1902** (Alameda becomes an island). |
| **Richmond** | Inner Harbor and Santa Fe Channel, 1920 (LOW: 1912–29). |
| **Reservoirs and lakes (48, incl. Lake Merritt)** | Dam years are listed in `pipeline/landscape_water.py` `RESERVOIRS`. Examples: Pilarcitos 1866, San Andreas 1870, Lake Temescal 1869, Lake Chabot 1875, Crystal Springs 1877/1888, Lake Lagunitas 1872, Searsville 1892, Stow (Blue Heron) Lake 1893, Calaveras 1925, the SCVWCD dams of 1935–36, Anderson 1950, Lexington 1952, Briones 1964, Del Valle 1968, Los Vaqueros 1998, and the 1960s lagoons of Foster City, Redwood Shores and Bel Marin Keys. **Before the dam year the cell is valley floor, not water.** |
| **Salt ponds, South Bay** | `sb_*` rows from `south_bay_salt_phases.geojson` (2026-11, replacing the complex-wide estimates): Mount Eden / Johnson Landing **1854** (Johnson 1853), Mount Eden works **1862**, Union Pacific **1872**, Alvarado / Turk Island **1864**, Barton / Carmen Island **1880**, Hayward shore 1865–1930, Crystal works at Plummer Landing 1875, south of Coyote Hill Slough **1908**, Arden at Dumbarton Point **1920**, Newark–Mowry north and M4–M6 **1925**, Union City Alvarado ponds **1925**, Alviso Salt A1–A4 **1925** and A8 **1927**, M1–M3 / A5–A11 / Ravenswood **1944–45** (marsh on the 1939–40 photos, ponds on the 1948 photos), A12–A23 **1955** (marsh in 1948, ponds by 1961), sewage ponds 1956. Details in `README_south_bay_baylands.md`. Redwood City: 1910 (LOW; bayfront first diked c.1901). |
| **Diked baylands** | Bair Island diked for farming, 1885–1946. South Bay diked land is dated per phase (`sb_coyote_hills_east` 1939, `sb_alviso_east_diked` 1920, `sb_palo_alto_baylands` 1930; all LOW): nothing was diked south of the Coyote Hills on the 1895–99 surveys. |

### Relation to `data/manual/fill_zones.csv`

The coarse zones `sb_salt_ponds_east_early` (1853–1930) and `sb_salt_ponds_south` (1920–57) are superseded inside these rings: use a row's `year_start` as the dike year. Keep all fill, restored and excavated zones; the dates agree with them (Tidal Canal, Bair Island salt 1948–52, Redwood Shores, Foster City).

### Recommended terrain rule

For rows with cover `lake` or `shallow_water`, apply only to cells that are water today:

- **Natural cover before `year_start`.** Use the c.1800 cover: SFEI marsh / flat, or for reservoirs the surrounding upland cover (grass, riparian, oak). Do **not** use RESERVOIR.
- **At `year_start`.** Switch to SHALLOW or RESERVOIR.

**Salt ponds and diked land.** For `salt_pond` and `diked` rows, the row's `year_start` becomes the dike year of the SFEI c.1998 salt-pond / diked cells inside the ring. `year_end` ends the salt use (Mount Eden early works; Bair Island farming before salt). After that, keep what SFEI c.1998 shows.

---

## 4. Findings: what the South Bay looked like, c.1769–1950

These come chiefly from Broek (1932). His sources are the State Agricultural Society *Transactions* (1850s–70s), the US censuses, Thompson & West (1876) and fieldwork in 1929–31. His figures are for Santa Clara County.

### 1777–1850: Mission and ranchos

- **The valley floor was oak savanna and grassland (the *Llano de los Robles*), grazed by mission and then rancho cattle.**
- **Cultivation was tiny.** Mission Santa Clara grew wheat on the adobe north of the mission: about 100 acres in 1790, and 250–330 acres in 1824–26. It also kept an orchard of apples, pears, apricots, peaches, figs and olives, but no prunes.
- **The Pueblo de San José fields lay along the Guadalupe** (1780: 700 bushels of grain).
- **Ranchos were open range until about 1850.** There were no fences or barns, only corrals.

### 1850–65: Cattle, wheat and experiment

- **The first significant wheat and barley crop on the east bay shore was harvested in 1851** (Alameda County).
- **The wheat belt was the Yolo loams of the middle valley floor.** These are today's Holocene fans.
  - The black adobe by the marshes stayed **pasture, and the first dairies** (1850s).
  - The gravelly upper fans along the Santa Cruz foothills were **brush and chaparral**. They were cleared from about 1870, partly by Chinese contractors.
- **Wheat output in Santa Clara County** was about 180,000 bu in 1856 and 549,195 bu in 1859.
- **Some rancho grants stayed undivided cattle range until about 1900.** These lay in the Central Section (Coyote–Morgan Hill), on the bay border, and at the Sunnyvale site (Murphy).

### 1865–75: Wheat dominant

- **Wheat peaked at 1,188,137 bu in 1869.** A heavy spring-sown, summer-fallow regime followed, with white sacks piled in the stubble in August and September.
- **Orchards were patches.**
  - There were about 1,100 acres around San José and Santa Clara by 1863.
  - The Willows, south of San José, went to strawberries in 1863 and to fruit trees in 1868. Strawberries moved to Agnew's artesian wells.
- **Vines.**
  - Plantings went from 150,000 vines in 1856 to 500,000 in 1857.
  - The "foothill" grape belt on the Stevens and Permanente creek fans was known as such by 1872.
  - The first foothill orchard was planted near Los Gatos in 1875.

### 1875–1900: Horticulture supersedes wheat

- **Wheat collapsed:** 648,055 bu in 1879, 282,536 in 1889, 175,230 in 1899 and 10,198 in 1909.
- **Barley rose to 1.39 M bu in 1899, then fell.** Hay kept growing for the Bay cities' horses.
- **In 1890 orchards equalled wheat, at about 19,000 acres each.** Orchards were then 10 % of improved land; apricots covered 3,507 acres.
- **The dried prune succeeded in New York in 1886, and prunes were planted massively in the 1890s.**
- **Vineyards peaked around 1900.** Phylloxera and the 1897–1900 droughts then turned the wine belt into "the dense fruit tree forest of today".

### 1900–30: The Valley of Heart's Delight

- **Orchard expansion paused from 1902 to 1918, then resumed.**
- **About 79,000 acres were in orchard at the end of WWI** (SJSU).
- **By 1930 there were 103,000 acres of orchard, 65 % of cropland.**
  - Prunes: 5.3 M bearing trees. 83 % of the 4,971 fruit farms grew prunes.
  - Apricots: 18,244 acres.
  - Pears and cherries were expanding.
- **Dairies held at about 12,000 cows** (1910–30).
- **Truck crops and seed farms grew on the bay lowlands.** These are Broek's "small crops" belt around Alviso and Milpitas.
- **The peak of about 100,000+ acres came in the 1930s–40s.** The topos of 1948–55 show it.

### Elsewhere

- **North and west of Mountain View the land was not grassland.** Palo Alto and Mayfield were grain and hay farms from the 1850s. Then came Stanford's Palo Alto Stock Farm (1876), and orchards in Mayfield and Barron Park in the 1890s. Further north:
  - Menlo Park and Atherton were country estates from the 1860s.
  - Redwood City had hay, dairies and tanneries, then flower nurseries.
  - San Mateo, Burlingame and Hillsborough had estates and dairies.
  - Millbrae and San Bruno were dairy land.
  - Colma was truck gardens from the 1870s, with cemeteries from 1887.
- **Newark and the Mayfield shore had no salt ponds from 1850.** Solar salt began in **1853–54 at Mount Eden / Eden Landing (Hayward)**. By the 1880s–1900s small works covered the marsh there and at Alvarado. Ponds then followed:
  - Newark north: 1885–1920s.
  - Ravenswood: 1910s.
  - Alviso: 1920s.
  - Mountain View, Sunnyvale and Newark south: 1930s–40s, in Leslie's expansion (12,500 acres Bay-wide in 1936, 25,000 in 1946, 30,000 in the South Bay by 1959).
  - Before that, the shore was tidal marsh. Its landward edge was diked for hay in places (1880s–1910s).
- **East Bay.**
  - Eden Township (San Leandro, Hayward, San Lorenzo) went from grain (1851) to cherries, apricots and row crops from about 1870–76.
  - Washington Township had grain, then sugar beets (Alvarado mill 1870/1879) and vineyards at Mission San José (1880s), then orchards and the Niles nursery (1884).
  - Livermore stayed grain and hay with vineyards on the south side from 1882; Pleasanton grew hops (1880s–WWI).
- **Contra Costa.** Wheat was the leading crop until the 1880s–90s. Walnuts, pears, apricots and grapes followed; walnuts replaced the Concord vines after 1919 and peaked in 1946. In the east, Brentwood was dry-farmed until irrigation in 1914–16, then grew alfalfa, dairies and orchards (1922).
- **Marin.** Dairies from 1857, with grain and potatoes in the 1860s around Novato.

### Recommended eras for the terrain

1. **Before 1850.** Natural cover everywhere. Grazing does not show. Optionally draw the small mission fields near Mission Santa Clara, Mission San José and the Pueblo.
2. **1851–62.** `grain` appears on the valley-floor fans district by district. The Santa Clara / San José core and Eden Township come first (1851–58). The Central Section follows in the 1860s and Morgan Hill in the 1870s–80s. The clay lowland by the bay is pasture / hay. The foothill gravelly fans stay grass / brush until the 1870s.
3. **1868–1925.** Orchards spread from San José / Santa Clara outward: the core 1872–90, the west 1886–1905, the east side and the south 1895–1922. The foothill vineyards (1872–1900) turn to orchards around 1900.
4. **1931 and 1948 snapshots** come from Broek and the topos. Urbanisation from the buildings ends them.

---

## Sources

See `SOURCES.md`:

- `broek_1932`
- `usgs_of98_354`, `usgs_of2006_1037`, `usgs_of00_444`
- `sfei_hidden_nature_sf`
- `overture_water`
- `sbsprp_salt_history`, `bcdc_salt_ponds_2005`
- `usgs_htmc` (via the topo-farmsteads stage)

Per-row and per-feature URLs are in the data.

Raw inputs are in `data/raw/landscape/`, which is gitignored:

| File | Contents |
|---|---|
| `broek1932_plate1.jpg`, `broek1932_plate2.jpg` | Plates I and II, extracted from the 352 MB Utrecht PDF |
| `broek1932_map10_sample_north.jpg` | Map X, the 1875 / 1931 sample strip |
| `broek1932.txt` | OCR text |
| `of00-444_4c.tar.gz` | OFR 00-444 shapefiles |
| `sfs_data.tar.gz`, `sfs_geol.parquet` | OF 98-354 ARC export. The PAL layer of `sfs-geol.e00` was decompressed with `e00conv` (Debian package `e00compr`) and read with GDAL. |
| `overture_water.parquet` | Overture 2026-10-21 `theme=base/type=water`, region bbox |
| `sbsprp_salt_appendixE.txt`, `bcdc_salt_ponds_2005.txt` | Text of the salt-pond histories |

OFR 2006-1037 is in `data/raw/usgs_ofr2006_1037/`.
