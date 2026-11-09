# South Bay baylands and plains, 1769 → today

Mount Eden – Alvarado – Newark – Alviso – Mountain View – Palo Alto / Mayfield – Ravenswood, and the plains behind them
(Alameda Creek plain: Decoto, Centerville, Irvington; San Francisquito fan: Mayfield, Palo Alto, Mountain View).

Why this file exists: in the 1800s the map showed salt ponds, diked land and long blue-grey bands across Newark, Centerville,
Decoto, Palo Alto and Alviso. This note sets out what those places looked like decade by decade, from real maps and records,
and what was changed in the data (2026-11).

Files: `south_bay_salt_phases.geojson` (the researched phase zones, one feature per phase, with dates and evidence) →
the `sb_*` rows of `water_history.csv` (each zone clipped to SFEI's c.1998 pond / diked extent, ponds joined across their
levees, like the other salt rows); `check_south_bay_salt_by_decade.png` (what the rows give at 1850 … 1970).

## 1. What was wrong

| Symptom on the map | Cause | Fix |
|---|---|---|
| Blue-grey diagonal bands across Newark, Centerville, Decoto, Irvington, Ardenwood, Palo Alto, Sunnyvale and Alviso **upland** from 1853, crossed with field patterns | `data/tables/landcover_history.csv` row `salt_ponds_south_bay`: a six-point hexagon (Hayward → Mountain View) with cover `salt_pond`, `year_start` 1853. `terrain_tiles.py` paints *every* non-water, non-marsh cell inside a landcover_history polygon (its note "clip to historical marsh/flat" was never applied) at `1853 + 6·h`, and `h` is a linear hash, so the change sweeps across in ~1 km diagonal stripes. Where the farm era came first, the plain became a salt pond after it and stayed one until the city (Decoto: farm 1856 → salt pond 1857 → town 1920). | Row removed. Salt ponds come only from `water_history.csv`, which the terrain applies only to SFEI c.1800 marsh / flat / pan that is still salt pond or diked in SFEI c.1998. |
| Orchard / wheat blocks with straight edges and diagonal stripes in the Santa Clara Valley and Eden Township | Same mechanism: `scv_wheat` (1850), `scv_orchards` (1885) and `eb_eden_township_orchards` (1870) boxes in `landcover_history.csv`, painted after and over the researched `agriculture.geojson` districts. | Rows removed; `agriculture.geojson` (districts, Broek 1931, 1940s topo orchards) covers these areas. |
| Salt ponds at Newark (1905), Mowry (1935), Alviso (1925), Mountain View (1935), Ravenswood (1912) and diked hay land along the whole South Bay margin from 1895 | Old `water_history.csv` rows: complex-wide dates, mostly ESTIMATED midpoints; the Eden Landing "inner 1868 / outer 1928" split was a 2.5 km distance rule. | 66 old rows replaced by 26 researched phase zones (24 salt / diked zones and 2 sewage-pond complexes; section 3). |
| Stivers Lagoon at Irvington shown as dry grass until 1969 | `lake_lake_elizabeth_1` (Lake Elizabeth, 1969) makes the c.1800 cover of a lake's cells grass before its dam year. But Lake Elizabeth was dug in a natural sag pond on the Hayward Fault: "The Lagoon" (USGS 1906), "Stivers Pond" (1953); SFEI maps it as a perennial pond (Higley 1857, Allardt 1874, Thompson & West 1878, USGS 1906). `lake_lake_elizabeth_2` was a different "Lake Elizabeth" (37.14 N, −122.33) matched by name. | Both rows removed: the SFEI pond stays water throughout. |

Not data but code (section 5): the linear hash `h` makes diagonal stripes wherever it spreads a year (salt ponds `+4·h`,
c.1800 flats that read as water today `1870 + 20·h`, flats / marsh accreting behind the ponds `1900 + 40·h`, every
landcover_history era `+6·h`). In the 1880s the open flats off Palo Alto and Newark showed stripes of water and mud for that reason.

## 2. What the places looked like

**Sources (summary):** SFEI historical ecology GIS (Alameda Creek, Coyote Creek, western Santa Clara Valley and the
South Bay T-sheet baylands, already the terrain's c.1800 cover), USGS 15′ sheets Haywards 1899 (survey 1896), Palo Alto and
San Jose 1897/1899 (1895), Hayward 1915 (reprint of the 1899 base with the 1910 Dumbarton rail bridge), the War Department
15′ sheets Hayward 1942, Palo Alto 1941/1943, San Jose 1943, Pleasanton 1941 (aerial photos 1939–40), the 7.5′ sheets Newark
1947 (1946 photos), Redwood Point 1948, Mountain View / Milpitas / Palo Alto / Niles 1953 (1948 photos), Newark, Redwood Point,
Hayward 1959 and Milpitas / Mountain View / Palo Alto 1961; the USC&GS 1907 chart and the Thompson & West 1878 atlas plates,
Claire Lopez's 1971 maps for Leslie Salt and Ver Planck's 1958 maps (all reproduced in EDAW 2005); the salt histories of
USFWS (2009), EDAW (2005, after Ver Planck 1958, Sandoval 1988, Lopez 1971 and the Leslie / DL&IC archive) and the SBSPRP
Phase 2 EIS/R (2016). Full list in section 6.

### The bay margin

* **Before 1850.** A tidal-marsh fringe 1–3 km wide (pickleweed and cordgrass cut by branching sloughs) from San Lorenzo
  Creek round the south end of the bay to Ravenswood, with wide mudflats beyond. Between San Lorenzo and Mount Eden the marsh
  held **natural salt pans** (salinas: the SFEI T-sheet layer maps ~500 ha of "salt flat / salina" and marsh pannes at
  37.62–37.67 °N, the USFWS "natural salt ponds c.1850" panel the same strip). The Ohlone scraped salt from them; Mission San
  José (1797) collected enough to export some; none of this altered the marsh.
* **1853–1870s.** **John Johnson** leveed 14 acres of the saline marsh at Mount Eden in **1853** (just north of today's SR-92;
  first harvest 25 t) — the first solar salt works on the Bay. Small family works (Danish and German immigrants, holdings of
  20–40 acres) spread along the marsh from San Lorenzo Creek to Alvarado: **Quigley** at Barron's Landing, Alvarado, **1862**;
  **Plummer Brothers** (Turk Island) **1869**; **Andrew Oliver** (120 acres at Mount Eden) and the **Union Pacific Salt Co.**
  **1872**. Bay salt output was 17,000 t in 1868. Everywhere south of the Coyote Hills the marsh was untouched. Reclamation
  Districts 82 (17,000 acres, east bay) and 95 (10,000 acres, south bay) were formed in **1869**; their levees were not
  maintained after 1873 and washed away (Lopez 1971).
* **1880s–1890s.** About **28 works** from Hayward Landing to Coyote Hill Slough: concentrating ponds of 100–300 acres
  behind mud dikes, wood-floored crystallizers of 1–8 acres, windmill-driven Archimedes screws, white salt piles and
  "tent-piles" (Union Pacific alone held 1,200 acres in 1882; production close to 100,000 t a year by 1900). The USGS 1896
  survey writes "SALT WORKS" over the whole marsh strip from San Lorenzo to Alameda Creek and marks "Union City Salt Works"
  at Alvarado. South of the Coyote Hills there was one small works, the **Crystal Salt Works** (Plummer Bros.) at Plummer
  Landing below Newark. The 1895–99 Palo Alto and San Jose sheets show the **whole margin from Ravenswood to Mowry, Alviso and
  Warm Springs as untouched tidal marsh**, with the hay and grain landings (Cooley's / Ravenswood, Mountain View, Guth and
  Jagel landings, Alviso, Mowry, Plummer, Jarvis) at the slough heads.
* **1900s–1910s.** Consolidation (California Salt 1901, Continental 1900, Leslie 1907; Oliver absorbed its neighbours by
  1915; the small works peaked in the 1910s). The Dumbarton Land & Improvement Co. leveed the marsh for farming in 1905–08
  ("over 4,000 acres in Santa Clara County under levee, only 500 rented", early 1908) — the venture failed and the levees
  washed out; in 1907–08 it leveed ~2,000 acres north of Dumbarton Point for salt, next to California Salt's works. The
  USC&GS 1907 chart shows ponds from Russell (Hayward) Landing to **Coyote Hill Slough** and marsh south of it.
* **1920s.** Industrial salt: **Arden Salt** (Schilling, 1919) on the Dumbarton Point marsh, Newark and Mowry; Morton refinery
  at Newark 1926; **Continental / Alviso Salt** bought the marsh west of Alviso to Mayfield Slough (contract 1921, purchase
  1924) and built ponds there and a plant at Alviso (used one year, 1929); the **Union City Alvarado** ponds were rebuilt
  1924–31. Drawbridge at its peak (90 cabins 1926).
* **1930s–40s.** Leslie-California (1924) absorbed Turk Island (1927) and Oliver (1931); **Leslie Salt** (1936) merged with
  Arden. 12,000 acres of ponds in 1936, 25,000 in 1946. The 1939–40 photos (1941–43 sheets) still show **marsh** at Mowry south
  of the slough (inside a levee), between Guadalupe and Alviso sloughs, between Alviso Slough and Coyote Creek, round
  Drawbridge, and at **Ravenswood**; the Mountain View ponds of Alviso Salt lie **dry** inside their levees. By the 1948 photos
  (1953 sheets) all of that is salt evaporators except the marsh east of the Alviso railroad and round Drawbridge.
* **1950s.** Leslie's last expansion: ponds A12–A18, the Island ponds (A19–A21) and A22/A23 (evaporators on the 1961
  Milpitas sheet), the Redwood City plant (first salt 1951) and Bair Island; sewage-plant ponds at Alviso and Sunnyvale
  (1956). 1972 wildlife refuge, 1978 Cargill, 2003 public purchase, tidal restoration from 2006 (`fill_zones.csv`).

### The plains behind the marsh

* **Alameda Creek plain (Decoto, Centerville, Irvington, Newark, Alvarado).** c.1800 (SFEI Alameda Creek study, in the
  terrain): **grassland** on the Alameda Creek fan (8,900 ha in the box Decoto–Irvington–Newark–Alvarado), an **alkali
  vernal-pool complex** (2,100 ha) and **alkali / wet meadows** (1,500 ha) on the clay flats between the fan and the marsh
  (Alvarado, Union City, the Coyote Hills, west Newark), **willow thickets** and freshwater marsh along the creek and at the
  fan toe, and two natural ponds on the Hayward Fault at Irvington — **Tule Pond** and **"The Lagoon"** (Stivers Lagoon, now
  Lake Elizabeth). There are no long bands in any of these sources: the bands were the salt-pond artefact. Land use: Mission
  San José's cattle range (1797), then Ranchos Arroyo de la Alameda (1842) and Potrero de los Cerritos (1844) — open grazed
  grassland that looks natural. **Farms from the 1850s** (Washington Township: wheat and barley on the fan; G.W. Patterson's
  Ardenwood ranch from 1856), the beet-sugar factory at **Alvarado 1870** (first successful one in the US), Newark laid out
  1876–78 on the South Pacific Coast Railroad, orchards, vineyards (Mission San José, Warm Springs) and nurseries (Niles 1884)
  from the 1880s. `agriculture.geojson` (`eb_washington`: grain 1853→58, truck crops / beets on the clay lowland from 1879,
  orchards 1885→1910, vineyards 1880–1920) matches this record — **farmland on these plains from the 1850s is real**.
* **San Francisquito fan and the Mayfield / Mountain View flats.** c.1800 (SFEI western Santa Clara Valley): **oak woodland
  and oak savanna** (the Llano de los Robles) on the fan round today's downtown Palo Alto and Stanford, **wet meadow**
  (2,650 ha) in a belt between the oaks and the marsh — Mayfield, Mountain View north of El Camino, Moffett — with willow
  groves and alkali meadow at its bay edge. Ranchos Rincón de San Francisquito (1841) and Pastoria de las Borregas (1842):
  grazing. **Mayfield Farm 1853**, Uncle Jim's Cabin stage stop 1855, railroad to Mayfield October 1863, Mayfield Brewery
  1868; wheat, barley, hay; Stanford's Palo Alto Stock Farm 1876, the university 1891, Palo Alto (University Park) 1894;
  Mayfield annexed 1925. `pen_palo_alto` (grain 1853→60, pasture on the clay lowland 1853, stock farm / estates 1876→91,
  orchards 1888→1905) and `scv_west` match this.

## 3. Data changes

`water_history.csv`, salt / diked rows of the South Bay (San Lorenzo Creek → Ravenswood). Each phase is one feature of
`south_bay_salt_phases.geojson` and one or more `sb_<phase>[_n]` rows (the zone clipped to SFEI c.1998 salt pond, storage
pond, diked wetland and agricultural bayland). Phases marked `_abandoned` are 19th-century works on ground that is marsh or
fill today (zone ∩ SFEI c.1800 marsh, minus today's ponds); they need the `year_end` rule of section 5 to show.

| Phase id (`sb_…`) | Place | Cover | From | To | Conf. | ha | Evidence (short) |
|---|---|---|---|---|---|---|---|
| `hayward_shore_south` | Mount Eden / Johnson Landing salt works (SR-92 to Hayward Landing) | salt_pond | 1854 | – | medium | 176 | Johnson 1853 (EDAW 2005); 1857 T-sheet salinas; ponds on 1942 sheet (1939 photos) |
| `hayward_shore_south_abandoned` | Mount Eden / Johnson Landing salt works (SR-92 to Hayward Landing) — works on ground that is marsh / fill today | salt_pond | 1854 | 1955 | medium | 175 | Johnson 1853 (EDAW 2005); 1857 T-sheet salinas; ponds on 1942 sheet (1939 photos) |
| `hayward_shore_north` | Hayward shore salt works (Hayward Landing to San Lorenzo Creek) | salt_pond | 1865 | 1930 | low | 134 | Ver Planck 1958 works map; USC&GS 1907 levees; only ditches / dry diked land in 1939 |
| `hayward_shore_north_abandoned` | Hayward shore salt works (Hayward Landing to San Lorenzo Creek) — works on ground that is marsh / fill today | salt_pond | 1865 | 1930 | low | 547 | Ver Planck 1958 works map; USC&GS 1907 levees; only ditches / dry diked land in 1939 |
| `eden_mteden` | Mount Eden salt works between SR-92 and Mt Eden Creek (Nielsen, Michelson, Peterman, Whisby, Oliver, Ohlsen) | salt_pond | 1862 | – | low | 346 | Lopez 1971 works A-G; Oliver 1872; USFWS c.1870 panel |
| `eden_unionpacific` | Union Pacific Salt Co. works (Mt Eden Creek to Old Alameda Creek) | salt_pond | 1872 | – | medium | 632 | Union Pacific Salt 1872-1927, 1,200 acres in 1882 (Ver Planck) |
| `eden_barton_carmen` | Barton's Solar (Pioneer) and Carmen Island salt works (bay side, Old Alameda Creek to Coyote Hill Slough) | salt_pond | 1880 | – | low | 385 | Lopez I/J; Barton's works by 1885; 1896 survey 'SALT WORKS'; 1907 chart |
| `eden_alvarado_turk` | Alvarado, Union City and Turk Island salt works (landward, Old Alameda Creek to Coyote Hill Slough) | salt_pond | 1864 | – | low | 888 | Quigley 1862, Plummer Bros 1869, Putnam's Union City (1896 survey), Continental 1900 |
| `eden_unioncity_1920s` | Union City Alvarado salt ponds (upland edge, levees 1924-31) | salt_pond | 1925 | – | medium | 271 | levees 1924-31 (Shoup & Baker 2007) |
| `coyote_hills_east` | Diked marsh at the north end of the Coyote Hills (Patterson Ranch) | diked | 1939 | – | low | 270 | levees around marsh on the 1942 sheet (1939 photos) |
| `newark_coyote_hill_slough` | Salt ponds south of Coyote Hill Slough (DL&IC / Whitney 1907-08) | salt_pond | 1908 | – | low | 439 | marsh on the 1907 chart; DL&IC 2,000 acres for salt 1907-08; ponded by 1939 |
| `newark_dumbarton_pt` | Arden Salt Co. ponds, Coyote Hills to Dumbarton Point | salt_pond | 1920 | – | medium | 1020 | marsh 1896 / 1907; Arden Salt 1919; evaporators 1939 |
| `newark_crystal_works` | Crystal Salt Works (Plummer Bros.) at Plummer Landing, Newark | salt_pond | 1875 | – | low | 144 | 'Crystal Salt Works' at Plummer Landing, 1896 survey; Plummer Bros 1869 |
| `newark_plummer_mowry_north` | Arden / Leslie Newark ponds, Dumbarton Point to Mowry Slough | salt_pond | 1925 | – | medium | 1314 | marsh 1896-99; Arden 1920s, Morton refinery 1926; evaporators 1939-40 |
| `newark_mowry_south_west` | Mowry ponds M1-M3 (Mowry Slough to Coyote Creek, west) | salt_pond | 1944 | – | medium | 654 | marsh inside levee 1939-40; evaporators 1948 (1953 sheet) |
| `newark_mowry_south_east` | Mowry ponds M4-M6 (along Coyote Creek, west of the railroad) | salt_pond | 1925 | – | medium | 842 | 'Salt Beds' 1939 (1943 San Jose sheet) |
| `alviso_mountain_view` | Alviso Salt Co. ponds, Charleston Slough to Guadalupe Slough (A1-A4) | salt_pond | 1925 | – | medium | 1121 | marsh 1899; Continental / Alviso Salt 1921-29 (Bancroft maps); dry 1939-40; evaporators 1948 |
| `alviso_a5_a7` | Ponds A5 / A7 (Guadalupe Slough to Alviso Slough) | salt_pond | 1944 | – | medium | 570 | marsh 1939-40; evaporators 1948 |
| `alviso_a8` | Alviso Salt Co. plant ponds west of Alviso (A8) | salt_pond | 1927 | – | medium | 924 | 'Salt Beds' + crystallizers 1939; Alviso Salt plant 1929 |
| `alviso_a9_a11` | Ponds A9-A11 (Alviso Slough to Coyote Creek, west of the railroad) | salt_pond | 1944 | – | medium | 423 | DL&IC levees 1907-08 washed out; marsh 1939; evaporators 1948 |
| `alviso_a12_a18` | Ponds A12-A18 (railroad to Artesian Slough / Coyote Creek) | salt_pond | 1955 | – | low | 1260 | marsh 1939 and 1948; evaporators by 1961 |
| `alviso_east_diked` | Diked marsh east of Coyote Creek (Milpitas / North San Jose margin) | diked | 1920 | – | low | 170 | marsh 1899; leveed farm ground 1939 |
| `alviso_island_ponds` | Island ponds A19-A21 (Coyote Creek to Mud Slough, Drawbridge) | salt_pond | 1955 | – | low | 395 | marsh 1939 and 1948; evaporators by 1961 |
| `alviso_a22_a23` | Ponds A22 / A23 (north of Mud Slough, Warm Springs) | salt_pond | 1955 | – | low | 145 | DL&I 1907-08; leveed dry land 1948; evaporators by 1961 |
| `ravenswood` | Ravenswood ponds (R1-R5, S5; Menlo Park / East Palo Alto) | salt_pond | 1945 | – | medium | 824 | marsh 1940 photos; ponds 1948; Leslie 1940s (EDAW 2005) |
| `palo_alto_baylands` | Palo Alto baylands diked (yacht harbor, airport) | diked | 1930 | – | low | 70 | marsh 1899; levees / dry diked land 1939-40 |
| `sj_wpcp_ponds` | San Jose / Santa Clara sewage plant ponds (Alviso) | salt_pond | 1956 | – | low | 248 | SFEI c.1998 storage ponds; plant opened 1956 |
| `sunnyvale_wpcp_ponds` | Sunnyvale sewage plant oxidation ponds | salt_pond | 1956 | – | low | 212 | SFEI c.1998 storage ponds; plant 1956 |

**Removed rows** (all superseded):

| Old row | Old dating | Why it was wrong |
|---|---|---|
| `salt_mt_eden_early_*` | 1856–1950 on the c.1800 pans + 250 m | Right place, but the works started 1853 and spread far beyond the pans (Lopez A–G, H); now `hayward_shore_*` and `eden_mteden`. |
| `salt_eden_landing_inner_*` | 1868, within 2.5 km of the upland | ESTIMATED split; by 1896–1907 the ponds already reached the bay edge. Now dated per group of works (1862–1880). |
| `salt_eden_landing_outer_*` | 1928 beyond 2.5 km | Most of it was 19th-century works (Barton, Carmen Island, Union Pacific); only the Union City Alvarado ponds date 1924–31 (`eden_unioncity_1920s`). |
| `salt_newark_north_*` | 1905 (midpoint 1885–1930) | Marsh on the 1896 survey and the 1907 chart; 1908 (Coyote Hill Slough strip), 1920 (Arden, to Dumbarton Point), 1925 (Newark–Mowry). The only older works there is Crystal (Plummer Landing). |
| `salt_newark_south_*` | 1935 | M4–M6 were salt beds by 1939 (1920s); M1–M3 were still marsh in 1939–40 (1940s). |
| `salt_alviso_east_*` | 1925 for all of Alviso | Only A8 (and A1–A4 west of it) by 1939; A9–A11 1940s; A12–A18, Island ponds and A22/A23 1950s. |
| `salt_alviso_west_*` | 1935 | Alviso Salt built A1–A4 in the 1920s (1921–29); dry in 1939–40, evaporators again by 1948. |
| `salt_ravenswood_*` | 1912 ("built in the 1910s", USFWS 2009) | The 1943 sheet (1940 photos) shows tidal marsh; ponds on the 1948 sheet; EDAW 2005 dates the unit to Leslie's 1940s works. |
| `diked_south_bay_ag_*` | 1895 everywhere on the margin | Nothing was diked south of the Coyote Hills on the 1895–99 sheets; the 1869–73 and 1905–08 levees washed out. Diked land now dated per zone (1920 / 1930 / 1939, LOW). |
| `lake_lake_elizabeth_1/_2` | lake from 1969, grass before | Natural Stivers Lagoon (see section 1). |

Kept: `salt_redwood_city` (1910, LOW), `diked_bair_island_ag_*` (1885–1946) — outside this study.

`data/tables/landcover_history.csv`: removed `salt_ponds_south_bay`, `scv_wheat`, `scv_orchards`, `eb_eden_township_orchards`
(section 1). The other non-SF era rows there (`cc_wheat_era`, `cc_walnut_orchards`, `eb_livermore_vineyards`, the Napa /
Sonoma vineyard and orchard boxes, `salt_ponds_napa`, `baylands_hay_dairy_north`) are the same kind of crude box with the
same stripes; they are outside this study and left for review.

`agriculture.geojson`: checked at Decoto, Centerville, Irvington, Newark, Ardenwood, Mayfield, Palo Alto and Mountain View
against the dates above — no change needed.

## 4. Confidence and limits

* The phase **boundaries** follow sloughs and levees read off the 1896–1961 sheets with a lon/lat grid (±100 m); inside a
  zone only SFEI c.1998 pond / diked cells are touched, so a boundary error only moves a date between neighbouring ponds.
* The **1939–40 / 1948 / 1961** brackets are hard (map evidence). Years inside the brackets (1944, 1955) are ESTIMATED from
  Leslie's acreage (12,000 acres 1936 → 25,000 1946 → 30,000 in the South Bay by 1959).
* The **19th-century works** are dated by company (Ver Planck, Sandoval, Lopez); each zone holds several works of different
  years, so the zone year is the earliest well-documented one (LOW / medium). The 1896 survey and 1907 chart are hard upper
  bounds for all of them. Lopez's 1971 map of works A–P (EDAW 2005 fig. 13) was used to group the works by zone; it was not
  georeferenced polygon by polygon.
* Short episodes the terrain cannot hold (one change per cell here): the 1869–73 and 1905–08 levees that washed out; the
  Mountain View ponds lying dry 1931–c.1945; the Hayward shore works' abandoned levees after c.1930.
* Not mapped here: duck clubs and hunters' cabins (Drawbridge from 1876–1880; 90 cabins in 1926), the Palo Alto Flood Basin
  (1956), Shoreline / Mountain View landfill (1960s–80s) — they come from fill / site layers.

## 5. Code changes recommended (not made here)

**A. Diagonal stripes: replace the linear hash `h` in `terrain_tiles.histories()`.**
`h = ((r·7919 + c·104729) mod 997) / 997` changes by −0.057 per row and +0.044 per column, i.e. it is a smooth ramp that wraps
every ~20 cells: `year + span·h` sweeps across the map in ~1 km diagonal bands. Use field-sized rank noise instead (the
agriculture block already has `blob()` for this):

```python
from scipy.special import ndtr
_rn = ndimage.gaussian_filter(np.random.default_rng(1769).standard_normal((rows, cols)).astype(np.float32), 4.0)
h = ndtr(_rn / (_rn.std() + 1e-9)).astype(np.float32)      # was: (np.add.outer(...) % 997) / 997.0
```

It feeds the salt-pond years (`ys + 4·h`), the flats / marsh behind the ponds (`1900 + 40·h`), the "broad" water
(`1870 + 20·h`), every landcover_history era (`ys + 6·h`), site parts and the 1906 rebuild.

**B. Open flats striped water / mud in the 1870s–80s.** `became = isin(N, [MARSH, FLAT]) & water_now & ~salt & ~diked`
turns c.1800 flats that WorldCover sees as water (its image tide) into water at 1870–90. SFEI c.1998 still maps most of them
as tidal flat. Suggest `became &= ~np.isin(b98, [3, 4])` (flats and marsh that are still flats / marsh stay so); the dredged
harbours keep their researched `shallow_water` rows.

**C. Salt rows: honour `year_end`, and draw 19th-century works that are no pond today.** Today only cells that are salt pond /
diked in SFEI c.1998 take a salt row, and only its start year. In the `water_history` loop:

```python
        if cov in ("salt_pond", "diked"):
            sel = m & (salt | diked)
            dike_year[sel] = ys + 4.0 * h[sel]
            ye = pd.to_numeric(r.year_end, errors="coerce")
            ended = bool(np.isfinite(ye) and ye < 9999)
            if ended and sel.any():
                salt_end.append((sel, float(ye)))            # works closed: levees round dry / overgrown beds
            gone = m & ~(salt | diked) & np.isin(b18, [3, 4, 6]) & ~water_now
            if cov == "salt_pond" and gone.any():
                old_works.append((gone, float(ys), float(ye) if ended else np.nan))
```

and after `event(diked, DIKED, dike_year)`:

```python
    for sel, ye in salt_end:
        event(sel, DIKED, ye + 2.0 * h)
    for gone, ys, ye in old_works:
        event(gone, SALTPOND, ys + 4.0 * h)
        if np.isfinite(ye):
            event(gone, MARSH, ye + 2.0 * h)     # fill / city events that come later win by date as now
```

(`salt_end = []; old_works = []` before the loop.) This draws the Hayward-shore and Mount Eden works of 1853–1930s
(`sb_hayward_shore_*_abandoned`, 720 ha) that are marsh or industrial fill today.

**D. `pipeline/landscape_water.py` regenerates `water_history.csv`.** Re-running `landscape.py water` would bring back the old
South Bay rows. Replace the South Bay entries of `SALT_AREAS` (`salt_mt_eden_early` … `salt_ravenswood`,
`diked_south_bay_ag`) by rows built from `south_bay_salt_phases.geojson` (same clipping as the committed rows), and drop
`("Lake Elizabeth", 1969, …)` from `RESERVOIRS`:

```python
def south_bay_rows(b18, b98):
    ph = gpd.read_file(OUT / "south_bay_salt_phases.geojson")
    U = lambda cls, b: shapely.union_all(list(b[b["class"].isin(cls)].geometry))
    ponds = U(["salt_pond", "storage_pond", "diked_wetland", "agricultural_bayland"], b98)
    storage = U(["storage_pond"], b98)
    marsh18 = U(["tidal_marsh", "tidal_marsh_pan", "salt_pond"], b18)
    bay98 = U(["deep_bay", "shallow_bay", "tidal_flat", "lagoon"], b98)
    sew = {"sb_sj_wpcp_ponds", "sb_sunnyvale_wpcp_ponds"}
    sew_all = shapely.union_all([shapely.intersection(g, storage) for g, p in zip(ph.geometry, ph.phase_id) if p in sew])
    rows = []
    for f in ph.itertuples():
        base = dict(name=f.name, cover=f.cover, year_start=int(f.year_start), confidence=f.confidence,
                    note=f.note, source_url=f.source_url)
        today = (shapely.intersection(f.geometry, storage) if f.phase_id in sew
                 else shapely.difference(shapely.intersection(f.geometry, ponds), sew_all))
        rows.append(dict(base, area_id=f.phase_id, year_end=int(f.year_end), geometry=today))
        if pd.notna(getattr(f, "abandoned_end", np.nan)):
            gone = shapely.difference(shapely.difference(shapely.intersection(f.geometry, marsh18), ponds), bay98)
            rows.append(dict(base, area_id=f.phase_id + "_abandoned", year_end=int(f.abandoned_end), geometry=gone))
    return rows
```

`water()` then does `rows += south_bay_rows(b18, b98)` (the existing ponds-join / simplify / ≥ 1 ha / numbering loop is the one
that produced the committed rows; the `_abandoned` rows' note also carries "needs the year_end rule …").

**E. Missing today: the Niles-cone quarry lakes** (Horseshoe Lake, Rainbow Lake, Lago Los Osos, Shinn and Kaiser ponds
between Niles and Decoto). WorldCover maps them as water but the SFEI grassland overrides it and no row adds them, so they
never appear. They need dated `lake` rows (gravel pits of the 20th century, Alameda County Water District recharge ponds,
Quarry Lakes park 2001; not researched here).

## 6. Sources

**Maps** (USGS Historical Topographic Map Collection, public domain; GeoPDFs from
`https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/`, survey / photo years from the FGDC metadata;
registered with the GeoPDF's own georeference, NAD27 → WGS84 by NADCON, the early sheets also with the road alignment cached
by `topo_farmsteads.py`):

| Sheet | Scale | Date (survey / photos) | File | Used for |
|---|---|---|---|---|
| Haywards | 1:62,500 | 1899 (survey 1896) | `62500/CA_Haywards_465731_1899_62500_geo.pdf` | "SALT WORKS" strip San Lorenzo → Alameda Creek; Union City and Crystal works; Newark marsh untouched |
| Hayward | 1:62,500 | 1915 (1899 base) | `62500/CA_Hayward_297660_1915_62500_geo.pdf` | no pond revision (adds 1910 Dumbarton rail bridge) |
| Palo Alto | 1:62,500 | 1897 / 1899 (survey 1895) | `62500/CA_Palo%20Alto_298452_1897…`, `…_298457_1899…` | 1897 "incomplete" in the baylands; 1899: whole margin tidal marsh |
| San Jose | 1:62,500 | 1897 / 1899 (survey 1895) | `62500/CA_San%20Jose_298899_1897…`, `…_466311_1899…` | Alviso / Mowry / Warm Springs marsh |
| Pleasanton | 1:62,500 | 1906 (survey 1904) | `62500/CA_Pleasanton_298577_1906_62500_geo.pdf` | "The Lagoon" and Tule Pond at Irvington |
| Hayward (War Dept.) | 1:62,500 | 1942 (photos 1939) | `62500/CA_Hayward_465728_1942_62500_geo.pdf` | evaporators Mt Eden → Dumbarton; Hayward shore abandoned |
| Palo Alto (War Dept.) | 1:62,500 | 1941 (survey 1939) / 1943 (photos 1940) | `62500/CA_Palo%20Alto_466099_1941…`, `…_298463_1943…` | Mowry north ponds; M1–M3, A5/A7, Ravenswood still marsh; Mountain View ponds dry |
| San Jose (War Dept.) | 1:62,500 | 1943 (photos 1939) | `62500/CA_San%20Jose_466308_1943_62500_geo.pdf` | "Salt Beds" M4–M6 and A8; A9–A18 and Drawbridge marsh |
| Newark | 1:24,000 | 1947 (photos 1946) / 1959 | `24000/CA_Newark_293493_1947…`, `…_293496_1959…` | evaporators (blank inside levees on 1947) |
| Redwood Point | 1:24,000 | 1948 / 1959 | `24000/CA_Redwood%20Point_294610_1948…`, `…_294613_1959…` | Ravenswood ponds by 1948; Eden Landing 1959 |
| Mountain View, Milpitas, Palo Alto, Niles | 1:24,000 | 1953 (photos 1948) | `24000/CA_Mountain%20View_293234_1953…`, `CA_Milpitas_292969_1953…`, `CA_Palo%20Alto_293907_1953…`, `CA_Niles_293546_1953…` | evaporators everywhere except A12–A23; Stivers Pond |
| Milpitas, Mountain View, Palo Alto, Hayward | 1:24,000 | 1959–61 | `24000/CA_Milpitas_465942_1961…`, `CA_Mountain%20View_293239_1961…`, `CA_Palo%20Alto_293909_1961…`, `CA_Hayward_291250_1959…` | A12–A23 evaporators |

Reproduced in EDAW (2005): U.S. Coast & Geodetic Survey chart of San Francisco Bay, 1907 (pond levees Russell Landing →
Coyote Hill Slough); Thompson & West, *Official Historical Atlas Map of Alameda County* (1878), Johnson's Landing and Alvarado
salt works; C. Lopez (1971) report to Leslie Salt — reclamation districts 82 / 95, DL&I Co. levees 1907–08, Solar Salt
Development Eden Landing 1860–1910 (works A–P); W.E. Ver Planck (1958) map of the salt works and the consolidation chart;
Leslie Salt Co. 1953 map of the crude salt plants. USFWS (2009) "Salt Pond Eras" map (natural c.1850, commercial c.1870 /
1900 / 1940 / 1950 / 2000).

**Texts**

* L.A. Speulda-Drews and N. Valentine (USFWS), 2009, *Appendix E: Identification and Evaluation of the South San Francisco Bay
  Solar Salt Industry Landscape* — https://www.southbayrestoration.org/documents/permit-related/Historic%20Salt%20AppendixE.pdf
* EDAW (L. Watt), 2005, *South Bay Salt Pond Restoration Project Historic Context Report* (Appendix D; scanned, OCR'd for this
  note) — https://www.southbayrestoration.org/documents/permit-related/Historic%20Salt%20AppendixD.pdf
* SBSPRP Phase 2 Final EIS/R (2016), §3.7 Cultural Resources —
  https://www.southbayrestoration.org/planning/phase2/documents/AR-FEISR/3.7_Cultural%20Resources_w%20Figs.pdf
* W.E. Ver Planck, 1958, *Salt in California*, California Division of Mines Bulletin 175 (via the three reports above);
  J. Sandoval, 1988, *Mt. Eden: Cradle of the Salt Industry in California*; Shoup and Baker, 2007 (P-01-010834).
* SFEI-ASC historical ecology GIS (`data/raw/sfei_historical_ecology/`): Alameda Creek (Stanford et al. 2013,
  https://www.sfei.org/projects/AlamedaCreekHE), western Santa Clara Valley, Coyote Creek, South San Francisco Baylands
  T-sheets (Kerr 1857, Westdahl 1896, Morse & Westdahl 1896).
* Towns: Wikipedia "Newark, California" (Pacific Land Investment Co. subdivision 1878), "Mayfield, California" (Mayfield Farm
  1853, Uncle Jim's Cabin 1855, railroad 1863, brewery 1868, annexed 1925); `data/manual/landscape/README.md` for the farm
  districts.
