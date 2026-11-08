# Population by place, 1850–2026 (`data/tables/population_places.csv`)

Census populations for every city, town and census-designated place (CDP) in the six counties that the map covers
(San Francisco, San Mateo, Santa Clara, Alameda, Contra Costa, Marin), the six counties, and their sum. The
counter can show the population of the city under the camera when zoomed in, and the six-county total when
zoomed out. Researched 2026-11-08.

## Layout

`place,kind,county,year,population,source_url,note,geoid`, one row per place per census year.

* `place`: the TIGER/Line 2024 place `NAME`, spelled exactly as in `tl_2024_06_place` (for example `San Jose`, `Bay Point`,
  `Lucas Valley-Marinwood`). County rows use the TIGER 2024 county `NAME` (`Alameda`, `Contra Costa`, …). The region row is
  `Bay Area (6 counties)`.
* `kind`: `city` / `town` / `cdp` is the place's type in TIGER 2024 (LSAD 25 / 43 / 57). It does not change from row to row.
  The type at the time of a census is in `note`, for example "census count of the unincorporated place; before
  incorporation (1955)". Other kinds are `county` and `region`. San Francisco has both a `county` row (geoid `06075`)
  and a `city` row (geoid `0667000`). The values are identical from 1860 on.
* `county`: the county name without "County", empty for the region.
* `geoid`: the TIGER 2024 place GEOID (7 digits). For counties it is the county GEOID (5 digits). It is empty for the region.
* `year`: the census year. Census day was 1 June for 1850–1900, 15 April for 1910, 1 January for 1920 and 1 April from
  1930 on. `2026` rows are CA DOF E-1 estimates for 1 January 2026. Rows before 1850 are pre-census estimates for the
  pueblo of San José.
* `note` starts with `decennial census`, `census count of …` (Gibson's township and place tables), `estimate (CA DOF E-1 …`,
  `estimate (pre-census): …` or `estimate: …` (the 1850 substitutes). Every row that is not a plain census count of the
  incorporated city says so in `note`.

The places were assigned to counties by a spatial join of each TIGER 2024 place's interior point (`INTPTLAT/INTPTLON`)
with the TIGER 2024 county polygons (`data/raw/tiger/tl_2024_06_place.zip`, `tl_2024_us_county.zip`).

## Coverage

* **1,422 rows**: 19 region rows (1850–2020 plus 2026), 112 county rows, and 1,291 place rows.
* **162 places**, every TIGER 2024 place in the six counties:
  * 80 incorporated places (66 cities, 14 towns): Alameda 14, Contra Costa 19, Marin 11, San Francisco 1, San Mateo 20,
    Santa Clara 15. Each has every census from its incorporation (except the `n/a` cells listed under *Gaps*), and earlier census counts where they exist (57 rows
    before incorporation). Each also has a 2026 estimate. The note on each place's first DOF row gives its
    incorporation year.
  * 82 CDPs: Alameda 6, Contra Costa 34, Marin 20, San Mateo 13, Santa Clara 9. All have 2020 counts. Older CDPs
    have counts from 1970, 1980 or 1990, and a few have 1880–1960 counts as unincorporated places. CDPs have no
    2026 estimate, because DOF E-1 covers only cities and counties, so their latest row is the 2020 count.
* **6 counties**: every census from formation. Marin, Contra Costa, Santa Clara and San Francisco start in 1850, and
  Alameda (formed 1853) and San Mateo (formed 1856) start in 1860. Each county also has a 2026 estimate.
* **Region**: the sum of the six counties for each census year 1850–2020 and the 2026 estimate. In 1850 the region row
  is Marin's 1850 count plus the 1852 state census for the other three counties (see below).

Rows by source: DOF historical table 937, 1990 CPH-2 91, E-1 2026 87, 2020 DOF C1 82, 2010 gazetteer 80, 2000 gazetteer 60,
Gibson township and place tables 55, 1970 census report 12, Arbuckle and Bancroft (San José pueblo) 9, Forstall (1850
substitutes) 5, Wikipedia 4.

## Sources and precedence

Each place and year takes its value from the first source in this list that has it, except for the corrections listed under *Corrections and lineage decisions*.

1. **CA Department of Finance, *Historical Census Populations of Counties and Incorporated Cities in California,
   1850–2020*** (revised 13 Aug 2021),
   <https://dof.ca.gov/media/docs/reports/demographic-reports/2020-1850_STCO_IncCities.xlsx>, from
   <https://dof.ca.gov/reports/demographic-reports/>. This is the primary source for counties and incorporated cities.
   It lists a city only from incorporation, under its current name (Pittsburg was "Black Diamond" in 1910, Colma was
   "Lawndale", and Sausalito appears as "Saucelito" in 1880). The 2010 values include Count Question Resolution
   corrections. As an exception, DOF also lists Danville 1980 (26,446) and Dublin 1980 (13,496), both of which
   incorporated in 1982. Cells marked `n/a`, which have no row: San Jose 1850 and 1860, Martinez 1880, San Leandro 1890
   ("not reported separately"), and San Francisco 1850.
2. **Campbell Gibson for CA DOF, *Population Totals by Township and Place for California Counties: 1860 to 1950*** (2007),
   <https://dof.ca.gov/media/docs/reports/demographic-reports/Populations-Township_and_Place_1850-1950.zip>.
   55 counts were transcribed by hand from the six county tables and checked against DOF where both exist. They are
   counts from before incorporation (Hayward 1870, San Leandro 1870, Martinez 1870, San Rafael 1870, San Pablo 1870 …)
   and counts of unincorporated places. Unincorporated places were published only in 1880, 1940 and 1950 (in 1950 only
   outside urbanized areas), and the 1890 census gave places as "town"/"village" without legal status. Examples are
   Castro Valley 1940, Newark 1880/1940/1950, Novato 1940/1950, Cupertino 1950, Saratoga 1880/1940/1950, Pleasant Hill
   1950 (reported as "Pleasant Hills") and Half Moon Bay 1880 (reported as "Spanishtown").
3. **U.S. Census Bureau, 1990 CPH-2-6, *Population and Housing Unit Counts: California*** (1992),
   <https://www2.census.gov/library/publications/decennial/1990/cph-2/cph-2-06.pdf>. Table 9 gives 1970, 1980 and 1990 for
   every 1990 place, and was parsed from the text layer: 124 places in the six counties, 79 incorporated and 45 CDPs.
   It supplies the 1970–1990 counts of the CDPs and of Oakley as a CDP. "r" marks 1980 counts revised after publication,
   which the notes say. The 1970 column can differ from the 1970 report (for example San Martin 1,429 here, 1,392 in
   1970), apparently because it was re-tabulated to 1980 boundaries. For cities the DOF values, which match the 1970
   report, are kept. The User Notes give the name changes of 1980–90 and the 1 April 1980 population of the areas that
   incorporated in 1980–90. The table uses three of these: Orinda 17,030, San Ramon 20,511 and East Palo Alto 18,106.
4. **Census 2000 and 2010 gazetteer files** (CDPs only):
   <https://www2.census.gov/geo/docs/maps-data/data/gazetteer/places2k.zip> (`POP2000`) and
   <https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2010_place_list_06.txt> (`POP10`). Places are matched
   by GEOID, then by name. Contra Costa Centre was "Waldon CDP" in 2000 (same code, 0683215).
5. **CA DOF, 2020 Census Table C1 (P.L. 94-171)**,
   <https://dof.ca.gov/media/docs/forecasting/Demographics/2020-census-data/2020Census_C1_Summary_RedistrictingFile.xlsx>.
   This gives the 2020 counts for CDPs, matched by county and place code. Its counts for cities match source 1.
6. **CA DOF, Report E-1, *Population Estimates for Cities, Counties, and the State, January 1, 2025 and 2026*** (released
   1 May 2026), <https://dof.ca.gov/media/docs/forecasting/Demographics/estimates-e1/E-1_2026_InternetVersion.xlsx>.
   The 1 Jan 2026 value is the row, and the note gives the 1 Jan 2025 value. San Francisco's 845,658 matches
   `population.csv`. The region estimate is the sum of the six counties.
7. **Forstall, R. L., *Population of States and Counties of the United States: 1790 to 1990*** (Census Bureau, 1996),
   <https://www2.census.gov/library/publications/decennial/1990/population-of-states-and-counties-us-1790-1990/population-of-states-and-counties-of-the-united-states-1790-1990.pdf>,
   California notes. The 1850 federal returns for Contra Costa and Santa Clara were lost, and those for San Francisco
   burned. The 1852 state census gave 2,786 (Contra Costa), 36,154 (San Francisco County, which then included San
   Mateo) and 6,764 (Santa Clara), and these stand in for 1850 marked `estimate`. San Francisco city 1850 = 34,776,
   the 1852 city figure already used in `population.csv`.
8. **1970 Census of Population, Vol. I, Part 6 (California), *Number of Inhabitants***,
   <https://www2.census.gov/library/publications/decennial/1970/population-volume-1/1970a_ca1-01.pdf>.
   12 values were read from Tables 6 and 10 of the OCR text. Each was accepted only when both tables agree or the
   published 1960–70 percent change reproduces it. They are the 1960 counts of Castro Valley, San Lorenzo, Orinda
   Village, West Pittsburg (now Bay Point), Alum Rock (now East Foothills, see below) and San Martin, and the 1970
   counts of unincorporated Dublin, Moraga, San Ramon Village, Foster City, East Palo Alto and Orinda Village.
9. **Pre-census estimates for San José** (`data/research/early_region.md`): Arbuckle, *Clyde Arbuckle's History of San
   José* (1985), <https://archive.org/details/casjhsj_000308>, and Bancroft, *History of California* i.716–718,
   <https://archive.org/details/historyofcalifor01banc>. The rows are 1777 (founding party, 66), 1791, 1800, 1820,
   1831 (padrón), 1841 (padrón including ranchos), 1846 (Bryant's 600–800, shown as 700) and January 1850 ("4,000",
   Sanor). Santa Clara January 1850 is about 1,000 (Sanor). All are marked `estimate (pre-census)`. San Francisco's
   pre-1850 estimates (Yelamu, Presidio, Mission Dolores, Yerba Buena) stay in `population.csv`. The populations of
   the missions (Santa Clara 1,247 in 1800, San José 1,886 in 1831) are in `early_region.md`. They are not place rows,
   because a mission's Indian population is not the population of a town.
10. **Wikipedia `{{US Census population}}` tables** (fallback only), fetched with `action=raw` on 2026-11-08 for 115 CDP
    and post-1950 city articles. They were used only for 1940–1980 years that no primary source above has, which gave
    4 rows: Danville 1960 (3,585), Alamo 1960 (1,791), Lafayette 1960 (7,114) and Pleasant Hill 1960 (23,844). Where
    they overlap the primary sources, 497 values agree and 11 differ. The differences are revised versus published
    1980 counts, the 1980 population of an incorporated area versus the CDP (Orinda, San Ramon, East Palo Alto), East
    Palo Alto 1970 (17,837 in both tables of the 1970 report, 18,727 on Wikipedia) and Stanford 2000 (13,315 versus
    13,314). Wikipedia's Danville 1970 value (14,059) is the combined Alamo-Danville place and was not used.

## Corrections and lineage decisions

* **Error in the DOF table, Gilroy 1980/1990.** The DOF 1850–2020 table repeats the Los Altos values (25,769 and 26,303)
  for Gilroy. The correct values are 21,641 (1980) and 31,487 (1990), from CPH-2 Table 9, the 1990 gazetteer and DOF's
  own 1990–2000 table. They are used and noted.
* **Renamed CDPs** (1990 CPH-2 User Notes): East Foothills was **Alum Rock** CDP in 1970 and 1980 and Alum Rock
  unincorporated place in 1960. Today's Alum Rock CDP first appears in 2000 (a different area), so its rows start in 2000.
  Lexington Hills was Chemeketa Park-Redwood Estates. Tara Hills 1980 was Tara Hills-Montalvin Manor and Vine Hill 1980
  was Vine Hill-Pacheco, both larger areas. Bay Point was West Pittsburg until Census 2000, and Contra Costa Centre was
  Waldon in 2000. Each such row names the old CDP in `note`.
* **Combined CDPs that were not used**: Alamo-Danville (1970), Bayview-Montalvin (1990, split in 2010), Blackhawk-Camino
  Tassajara (2000, split in 2010) and Highlands-Baywood Park (2000/2010, split in 2020). Rancho Rinconada CDP (1990,
  annexed by Cupertino in 1999) has no TIGER 2024 place.
* **Colma and Daly City 2000/2010**: the gazetteers have the counts as first published (Colma 1,191 and 1,792; Daly City
  103,621 and 101,123), while DOF carries the post-census corrections (Colma 1,187 and 1,454; Daly City 103,625 and
  101,072). DOF is kept.

## Caveats

* **Boundaries change.** A city's series mixes growth and annexation. Examples: Oakland absorbed Brooklyn (1872), Palo
  Alto annexed Mayfield (1925), San José annexed Willow Glen (1936) and Alviso (1968) and grew from about 17 to 136 sq mi
  in 1950–70, Fremont was formed in 1956 from five towns, and Union City was formed in 1959 from Alvarado and Decoto.
  County lines also moved before 1856. Contra Costa and Santa Clara included parts of later Alameda County until 1853,
  and San Francisco County included San Mateo until 1856. The county rows follow each county as it was at the time.
* **CDPs are redrawn every census**, so jumps can be boundary artefacts (Stanford 18,097 in 1990, 13,315 in 2000,
  21,150 in 2020; East Foothills 14,898 in 1990, 8,133 in 2000). The "unincorporated place" counts of 1880, 1940 and
  1950 had no fixed boundaries ("only approximate", Gibson). A count before incorporation (for example Brentwood
  1940, 2,569, larger than the 1950 city's 1,729) covers a different area from the later city.
* **1900–1930 list incorporated places only**, so unincorporated places have no counts in those decades. 1950 omitted
  unincorporated places inside urbanized areas, so most suburban CDPs start in 1960, 1970 or later.
* **1850**: the federal returns for San Francisco, Contra Costa and Santa Clara do not exist, so the 1852 state-census
  substitutes are an estimate. The 1852 values are higher than mid-1850 would have been, because the gold-rush towns
  were still growing fast.
* **Sum of places ≠ county**: the unincorporated balance (148,265 in Alameda in 2026, for example) lives outside the
  places, and CDPs cover only part of it. Use the county or region rows for totals.
* **The six-county region is not the nine-county Bay Area** in `population.csv` (`bay_area_9county`, which also counts
  Napa, Solano and Sonoma). The 2020 figures are 6,685,267 for six counties and 7,765,640 for nine.
* The E-1 estimates are DOF's figures for 1 January (provisional for 2026). The Census Bureau's Vintage 2025 estimates
  for 1 July differ (for San Francisco, 826,079 in July 2025).

## Gaps

* No count exists for San José 1860, Martinez 1880 or San Leandro 1890 (`n/a` in DOF). San José 1850 has only Sanor's
  "4,000" estimate.
* Unincorporated predecessors that are **not TIGER 2024 places** are left out of the CSV, because `place` must match
  TIGER. For reference, Gibson gives these (Alameda County, Washington township ≈ today's Fremont + Newark + Union City):
  township 2,011 (1860), 3,019 (1870), 4,592 (1880), 5,596 (1890), 6,914 (1900), 7,874 (1910), 8,494 (1920), 12,711
  (1930), 13,051 (1940), 16,895 (1950). The towns are Alvarado 315 (1870), 364 (1880), 776 (1940); Centerville 203
  (1880), 1,846 (1940), 1,401 (1950); Decoto 1,762 (1940), 2,830 (1950); Irvington 894 (1940); Mission San Jose 246
  (1880), 849 (1940); Niles 136 (1880), 2,104 (1940), 1,519 (1950). Other examples: Brooklyn 1,603 (1870, now
  Oakland), Mayfield 1,041 (1910, now Palo Alto), Willow Glen 4,167 (1930, now San José), Alviso 652 (1950, now San
  José) and Port Chicago 1,032 (1940).
* 1960 counts exist for only 10 unincorporated places (6 from the 1970 report, 4 from Wikipedia).
  The 1970 report's OCR text is too noisy to parse automatically, and the
  1980 report (*Number of Inhabitants*, `1980a_caab-*.pdf`) is a scan with no text layer. More values could be read
  from those pages by hand.
* Napa, Solano and Sonoma counties are not covered (the buildings layer doesn't cover them yet either).

## Using it in the viewer (suggestion)

Zoomed in: find the TIGER 2024 place polygon under the view centre, select rows by `geoid`, and interpolate between
the bracketing years. Log-linear interpolation suits growth best. Hide the counter before the first row, or fall back
to the county. Zoomed out: use the `region` row, or the sum of the `county` rows in view. For years before a county
existed, its population is inside its parent county (Alameda in Contra Costa and Santa Clara before 1853, San Mateo in
San Francisco before 1856).
