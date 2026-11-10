# Delta (Sacramento–San Joaquin) — c.1800 layer, island reclamation, flooded tracts

Added in the 2026-11 ship pass for the ten-county extent. The c.1998 baylands layer (SFEI EcoAtlas poster) and the
per-study SFEI layers stopped at Antioch, so the Delta inside the map had no c.1800 cover, no diked land and no dated
water.

| file | what |
|---|---|
| `fetch_sfei_compilation.py` | downloads one study of SFEI's *Historical Ecology GIS data compilation* (served by CDFW BIOS as ds3201, same fields as the files in `data/raw/sfei_historical_ecology/`) into that folder. Run for `"Sacramento-San Joaquin Delta" delta` and `"Laguna de Santa Rosa - Central Laguna" laguna_de_santa_rosa`. |
| `delta_zone.geojson` | one polygon: the part of the Delta study area inside the map extent and east of 121.86° W, where the c.1998 layer does not reach. `terrain_tiles.py` (patch of this pass) reads it to know where diked land comes from the `dl_*` rows instead of the c.1998 layer. Derived: convex hull of the Delta study's polygons ∩ `EXTENT`. |

**c.1800 layer.** `data/raw/sfei_historical_ecology/delta.geojson` (Whipple et al. 2012, *Sacramento–San Joaquin Delta
Historical Ecology Investigation*, SFEI-ASC; 1,593 polygons, 536 touch the map). `terrain_grid.hist_raster` picks the
file up by its name: it sorts before `east_contra_costa_county.geojson`, so the East Contra Costa, Historical Baylands
and Suisun studies still win where they overlap. No new class mapping is needed — the compilation already carries the
common legend (`LegLabel`) that `covers.SFEI_ECOLOGY` maps:

| Delta study class (`ClickLabel`) | `LegLabel` | cover | ha inside the map |
|---|---|---|---|
| Tidal Freshwater Emergent Wetland | Tidal / Salt Marsh | MARSH | 66,553 |
| Wet Meadow / Seasonal Wetland, Alkali Seasonal Wetland complex | Wet / Alkali Meadow | WETLAND | 13,712 |
| vernal pool complex | Vernal Pool Complex | GRASS | 9,112 |
| Tidal Mainstem Channel | Deep Water | DEEP | 6,089 |
| Valley Foothill Riparian, Willow Thicket, Willow Riparian Scrub/Shrub | Broad Riparian Complex (densely wooded) | RIPARIAN | 3,588 |
| Oak Woodland / Savanna | Oak Woodland | OAK | 1,701 |
| stabilized interior dune vegetation | Dune | DUNES | 1,061 |
| Grassland | Grassland | GRASS | 776 |
| Tidal Low Order Channel | Shallow Water | SHALLOW | 719 |
| Non-Tidal Freshwater Emergent Wetland | Marsh | WETLAND | 362 |
| Non-tidal Intermittent Pond/Lake | Seasonal Pond/Lake | WETLAND | 212 |
| Tidal / Non-tidal Perennial Pond/Lake | Perennial Pond/Lake | RESERVOIR | 15 |

**Reclamation.** 30 `diked_marsh` rows `dl_*` in `data/manual/fill_zones.csv`: one per island or tract inside the map,
outline = the Delta Stewardship Council's island polygon (Delta Levees Investment Strategy layer) widened 60 m into
the channels, years from John Thompson, *The Settlement Geography of the Sacramento–San Joaquin Delta* (Stanford
dissertation, 1957, pp. 469–504) and his "Early Reclamation and Abandonment of the Central Sacramento–San Joaquin
Delta" (Sacramento History Journal VI, 2006). A row gives the first enclosure where farming went on (Sherman 1869,
Twitchell 1869, Jersey 1872–73 …) and the lasting reclamation where Thompson names one (Webb 1912, Holland 1910,
Bacon 1916, Mandeville 1918); abandoned spells (Sherman 1881–94, Twitchell 1875–c.1893) are in the notes, not on
the map. Hotchkiss and Quimby have no date (ESTIMATED 1897–1918, the dredge era). No row: land that was never
leveed or is marsh again (Browns Island, Lower Sherman Island, Decker Island, Dutch Slough) and tracts without a
date (Fabian, Pearson, Merritt, the Oakley / Knightsen / Rio Vista margins) — they stay tule marsh.

**Flooded tracts** are `shallow_water` rows `delta_*` in `data/manual/landscape/water_history.csv`: Big Break 1928,
Sherman Lake c.1925, Franks Tract 1938, Little Franks Tract 1982, Mildred Island 1983, Liberty Island 1997–98, and the
bays of Discovery Bay (dug from 1968). Clifton Court Forebay (1969) was already there.
