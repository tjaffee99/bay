# places.csv — era-accurate place-name labels

One row per **name period** of a place (462 rows). A label is shown iff
`year_start <= year < year_end` (same rule as features; `9999` = still in use).

| column | meaning |
|---|---|
| `id` | stable id, prefixed by area (`sf_`, `ala_`, `cc_`, `mar_`, `napa_`, `sol_`, `son_`, `smc_`, `scl_`, `scz_`, `reg_`) |
| `name` | label text as used in that period |
| `tier` | `region` (bays, counties, Washington Township) · `city` (incorporated cities, major historic settlements) · `town` (towns, villages, missions, unincorporated places) · `neighborhood` · `historic` (vanished/short-lived names, Ohlone villages, ranchos, expositions, shipyards) · `landscape` (hills, islands, points, creeks, straits) |
| `lat`,`lon` | WGS84 label anchor, 5 decimals |
| `year_start` | first year the name was in use for the place (founding, naming, subdivision, post office or grant — `note` says which) |
| `year_end` | first year it was no longer used (rename, annexation, demolition); `9999` = current |
| `replaced_by` | `id` of the next name for the same place. Usually `year_end` of the old row = `year_start` of the new one; deliberate gaps exist (Japantown 1942→1945 forced removal, Barbary Coast 1917→Jackson Square 1971, Laurel Hill Cemetery 1941→Laurel Heights 1946) |
| `county` | present-day county (blank for bay-wide regions) |
| `note` | what the dates mean; **"estimated"** marks any year not stated as such in the source (decade midpoints, inferred ends) — 123 rows |
| `source_url` | the page supporting the name and year (mostly Wikipedia; FoundSF, SF Planning, local history societies otherwise) |

## Conventions
* **Renames are chains**: e.g. `Yerba Buena` 1835–1847 → `San Francisco`; `San Antonio`/`Clinton` → `Brooklyn` 1856–1872 → `East Oakland`; `Ocean View` → `West Berkeley` 1878; `Union City` 1850 → `Alvarado` 1853 → `Union City` 1959; `McCarthysville` → `Bank Mills` → `Saratoga`; `Murphy's Station` → `Encinal` → `Sunnyvale` 1901; `School House Station` → `Colma` → `Lawndale` 1924 → `Colma` 1941; `Yerba Buena Island` → `Goat Island` 1895 → `Yerba Buena Island` 1931; `Loma Alta` → `Telegraph Hill` 1849.
* Towns that merged but whose name survives get two rows: `town` until the merger/annexation, then `neighborhood` (Fruitvale, Elmhurst, Temescal, Willow Glen, Alviso, Lorin). Fremont's five towns keep `town` tier to 9999.
* **Missions** end at secularization (c. 1834–36) and hand over to the town that grew around them.
* **Ranchos** (`historic`): `year_start` = grant year; `year_end` = 1852 (1853 where stated), the year the claim was filed with the US Public Land Commission under the Land Act of 1851 — a uniform cut-off for the rancho as a map label, cited in each rancho article.
* **Ohlone villages** (Yelamu and Ramaytush villages, Pruristac, Timigtac): 1769–1800, locations approximate (Milliken 1995 via Wikipedia); 1800 = last baptism of a San Francisco-peninsula native recorded at Mission Dolores (NPS Golden Gate history, ch. 4) — estimated end.
* **Natural features with no documented naming date** (Ocean Beach, Point Lobos, Candlestick Point, San Bruno Mountain, Carquinez Strait, Point Reyes, Farallones, Sweeney Ridge) use `year_start = 1769` so the landscape is labelled throughout; their notes say the first use is not established. Features with known naming dates use them (Golden Gate 1846, Tamalpais 1845, Mount Davidson 1911, Islais Creek 1834, …).
* Cities: `year_start` = founding/settlement/naming; incorporation is in `note`.

## Coordinates
Wikipedia article coordinates for cities, towns, landscape and ranchos (ranchos only to ~0.01°;
Rancho San Antonio re-anchored to central Oakland); OpenStreetMap place nodes from
`data/raw/osm_bbbike/SanFrancisco.osm.pbf` (ODbL) for most SF neighborhoods; DataSF Analysis
Neighborhoods centroid (PDDL, data.sfgov.org j2bu-swwd) for Lakeshore; hand-placed approximate
points for vanished places (Happy Valley, Tar Flat, Little Chile, Sydney Town, Harbor View,
Clinton, New Haven, Silveyville, villages) — their notes say so.

## Known gaps / caveats
* Not included for lack of a dated source: Lower Haight, Duboce Triangle, Presidio Heights, Polk Gulch, Lower Pacific Heights, India Basin; Dumbarton and Agnews; Ohlone tribelets other than the Yelamu (Huchiun, Tamien, Puichon, Lamchin…); most Oakland hill, Berkeley and San Jose neighborhoods (Rockridge, Montclair, North Berkeley, Berryessa, Evergreen, Alum Rock…).
* Conflicting sources, noted in `note`: Redwood City 1857 (county seat) vs 1867 (Britannica); Gilroy renamed 1868 vs incorporated 1870; Alvarado formed 1853 vs 1854; Yerba Buena 1834 (pueblo) vs 1835 (first dwelling, used here).
* Sub-area names (Inner/Outer Richmond) reuse the parent district's year; Inner/Outer Sunset use estimated development years.
* Research collected 2026-11 from web sources; verify before treating any single date as authoritative.
