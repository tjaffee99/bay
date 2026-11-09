# Built-up extents of the region's older towns, from USGS historical topographic maps

Where each older town of the five modelled counties was **built up** at the date of a real, dated map:
the region's counterpart of San Francisco's `sf_extent_<year>.csv` (decision 14, `../sf_extent_README.md`).
"Built up" means street blocks substantially covered with buildings, as the map draws them; a block
that was merely platted (streets laid out, a few houses) is not built up.

Every snapshot is read from one survey generation of the USGS topographic quadrangles (public domain,
`SOURCES.md` → `region_extents`); nothing is interpolated and nothing is generated. Built by
`tools/extents.py` (`python -I tools/extents.py all <town>`, then `python -I tools/extents.py report x`
for the tables below; caches in `data/interim/region_extents/`, scans in `data/raw/region_extents/`).

## Files

| file | content |
|---|---|
| `<town>_<year>.geojson` | one Feature, a (Multi)Polygon (EPSG:4326), `kind = built_up`: the built-up area at `year` |
| `<town>_<year>_partial.geojson` | one Feature, `kind = partly_built`: blocks with some houses drawn (frontage share 0.12-0.35, about 3-4 houses or more on a block) that are **not** in the built-up file. Optional for the consumer (sparser era fabric); not part of the extent |
| `coverage.geojson` | one Feature per town and snapshot: the area that snapshot **read** (the sheets' quadrangles × the town × the processing box). Outside it a snapshot says nothing (e.g. `oakland_1939` covers only Oakland east of 122°15' W and south of 37°45' N) |
| `check/<town>.png` | the snapshots in sequence: each pixel coloured by the first snapshot whose extent holds it (dark red → light); dashed: area read; black dots: buildings standing today that predate the map |
| `tools/extents.py` | the whole method (render, alignment, blocks, classification, checks, these tables) |

Properties of a snapshot feature: `town`, `year` (what the map shows: the survey year, the year of
the culture revision, or the year of the aerial photographs the map was compiled from), `kind`,
`source` (`usgs_htmc:<sheet key>` joined with `+`; sheet keys in the maps table below), `source_url`
(the GeoPDFs, space-separated), `confidence` (`high` / `medium` / `low`), `note` (town-specific
caveats; per sheet: edition, survey / revision / photo years; the area read), `edition_years`,
`map_years`, `method`, `area_km2`, `n_blocks`.

Towns (`town` = today's TIGER 2024 places merged): `oakland` (Oakland, Emeryville, Piedmont),
`berkeley` (Berkeley, Albany), `alameda`, `san_jose` (San José, Santa Clara), `san_leandro`, `hayward`,
`richmond` (Richmond, El Cerrito, San Pablo), `palo_alto` (incl. Mayfield), `redwood_city`,
`san_mateo` (San Mateo, Burlingame), `san_rafael`, `martinez`. Each is processed inside a box around
its historic core and its growth to c. 1950 (`TOWNS[...]["bbox"]` in the tool), clipped to today's
land (TIGER area water removed). Vallejo is outside the map.

## How to use it

* A snapshot is a statement **inside its coverage polygon** only.
* Snapshots are read independently and are not forced to nest. Where a later map no longer shows an
  earlier built-up block ("prev. snapshot kept" below) the reason is mostly the reading (threshold,
  alignment, lettering, a yard or a big building read differently), rarely a real clearance before
  1950. As for SF, **the union of the earlier snapshots is a safe lower bound**: a block first
  contained in snapshot *k* was built up between snapshot *k-1* and *k*.
* The extent is on today's land: fill made after the map date is inside a polygon when the block
  around it was built up (port areas, the waterfront); clip with the land-year grid.
* The polygons follow today's street blocks (centrelines of today's streets), so a block is in or out
  as a whole; today's superblocks (freeways, campuses, the Post Office, City Center, cul-de-sac tracts)
  and blocks over 5 ha are read in 100 m cells.
* Small towns before c. 1915 (San Mateo, Hayward, San Leandro, Palo Alto, Redwood City, Martinez) are
  drawn house by house; only their densest core passes the built-up threshold and many of their
  surviving 1890s-1910s houses stand in the `_partial` area or outside both (see the table). Those
  snapshots are `low` confidence.

## Method

1. **Sheets.** The 1:62,500 15' quadrangles of 1885-1915 (first surveys, and the 1915 editions whose
   collars say "Culture revised in 1914": San Francisco 1915 "Surveyed in 1892-94. Culture revised in
   1914"; Concord 1915 "Surveyed in 1893-94. Culture revised in part in 1913-14. Edition of June
   1915"; San Mateo 1915 "Surveyed in 1892. Culture revised in part in 1914"), the 1:62,500 editions of
   1940-43 compiled from 1937-40 aerial photographs, and the 1:24,000 7.5' quadrangles of 1947-54
   compiled from 1946-52 photographs (TNM Access API; survey / photo years from each scan's FGDC
   record). Later imprints are reprints of the same plates (the 1929 reprint of San Francisco 1915
   shows the 1914 culture unchanged over Oakland), so they give no c. 1930 snapshot.
2. **Scan and registration.** The GeoPDF's 600-700 ppi scan (2.35 m per pixel at 1:62,500; the
   GeoTIFF is a 300 ppi resample) is resampled into UTM 10N at 2.5 m through its own registration
   (LGIDict CTM, polyconic NAD27; `pipeline/topo_farmsteads.GeoPDF`) and the NOAA NADCON grid, masked
   to the quadrangle minus 0.5 mm along the neat line.
3. **Alignment.** Black ink of the whole quadrangle (5 m pixels) is cross-correlated with today's
   street centrelines (Overture / OpenStreetMap) in 2.5 km windows (±420 m search on the early sheets,
   ±120 m on the 1940s ones); window shifts are fitted by consensus (constant, then affine when the
   windows span > 3 km). The 1885-1915 surveys are **~210-250 m** off (Concord 1897 113 m), RMS 15-23 m
   after the fit; the 1940s sheets 2-17 m (the 1:24,000 sheets are used as published when the fit is
   under 6 m). Same approach and magnitudes as `../farmsteads/README.md`.
4. **Blocks.** Today's street centrelines (Overture: trunk, primary, secondary, tertiary,
   residential, unclassified, living street; not motorways or service roads) polygonised and clipped
   to the town and to today's land. Blocks over 5 ha are cut into 100 m cells.
5. **Reading the 1885-1915 sheets.** They draw a closely built block front as a heavy black band along
   the street (~0.25-0.33 mm; measured band thickness 15-21 m on the ground) and a scattered house as
   a small solid square. Black ink (dark and neutral: contours are brown, water blue) → opening with
   a 0.15 mm disc (street casings, contours, thin lettering vanish) → *bands* = what survives an
   opening with a 40 m line at 12 orientations; *squares* = the remaining compact blobs ≥ 0.25 × 0.25
   mm. Not counted: ink further than 60 m from a street of today (lettering and symbols in the hills),
   within 12 m of a railway (Overture rail + `../historic_rail.geojson`), and on sheets from 1925 on
   within 25 m of a freeway of today (the heavy highway symbol of the Bayshore). **Built frontage
   share** of a block = (band length + 15 m per square) / frontage (the perimeter 15 m inside the street
   centrelines). A block is **built up at share ≥ 0.35** (SF: "about a third of the frontage"); a 100 m
   cell needs share ≥ 0.35 and ≥ 20 % heavy ink (a rail line or two is not built-up). **Partly built:**
   share ≥ 0.12.
6. **Reading the 1939-53 sheets.** The 1:24,000 sheets tint the built-up area pink with a red dot
   screen and draw only landmark buildings inside it; the 1:62,500 editions of 1940-43 tint it
   grey-tan (Concord 1942, Hayward 1942, San Jose 1943, Palo Alto 1943, San Mateo 1943) or draw the
   town house by house without a tint (Tamalpais 1941, Carquinez Strait 1940). Tint pixels (pink:
   R − G > 10 on paper that is white to yellowish, R − G 0-6 on every sheet; grey: 55 below the sheet's
   paper brightness, neutral hue) → majority over 0.8 mm → opening 0.6 mm, and at block level 0.9 mm
   (road fills and casings) → a block is built up when ≥ 50 % of it is tinted, **or** by the frontage
   rule above (houses drawn outside the tint, e.g. San Leandro and Hayward on Hayward 1942, where the
   tint stops at the Oakland line).
7. **Polygons.** Built blocks merged, closed by 12 m (street gaps), holes under 0.6 ha or thinner than
   10 m filled, parts under 2 ha dropped (a farm group, a single cell), clipped to the town and today's
   land, simplified 1 m. The partly-built polygons are made the same way, minus the built-up area.

## Validation

* **Buildings standing today that predate the map** (`data/interim/region_building_points.parquet`,
  `end_year = 9999`, ≥ 30 m², start year before the map year, inside the area read): share inside the
  extent (+20 m), and inside built-up + partly built. A built-up area should contain most of them;
  the rest are farmhouses, houses on half-built blocks, or wrong roll years (spike / imputed years).
* **Sanborn tracings** (`../sanborn/<area>_<year>.geojson`, within ±6 years of the snapshot): blocks of
  today fully inside the traced coverage with ≥ 15 % of their area under traced footprints ("built")
  and < 5 % ("empty"); share of each inside the extent.
* **Probes:** districts known to be built up by the map date (`PROBES`), share of their land inside
  the extent; block area at frontage-share thresholds 0.25 / 0.35 / 0.45 (sensitivity). A square
  credit of 15 / 20 / 25 m and thresholds 0.30 / 0.35 were also compared (Oakland 1914: 29.0 / 30.7 /
  32.2 km² of blocks at 0.35 and 31.0-34.4 km² at 0.30; survivors inside 79-86 %; the Sanborn recall
  did not change), so 15 m (one lot) and 0.35 were kept.
* Every check PNG was looked at; overlays of the extent on the aligned sheet were checked by eye in
  Oakland (Lakeside / Uptown, West Oakland, Fruitvale, the 37°45' sheet edge), San Mateo, Hayward,
  Martinez and San Rafael.

### Snapshots

<!-- snapshots -->
| town | year | sheets | built-up km² | partly built km² | area read km² | confidence | pre-map buildings standing today inside built-up (+ partly built) (n) | prev. snapshot kept | Sanborn built blocks inside / empty blocks inside |
|---|---|---|---|---|---|---|---|---|---|
| oakland | 1894 | sf1895, concord1897, haywards1899 | 11.06 | 9.8 | 134.7 | medium | 81.6% (91.7%) (2362) |  |  |
| oakland | 1914 | sf1915, concord1915, hayward1915 | 28.35 | 14.63 | 134.7 | medium | 82.3% (93.8%) (23290) | 90.7% | downtown 1912: 97% of 30 / 100% of 2; west 1912: 89% of 71 / 33% of 12 |
| oakland | 1939 | concord1942, hayward1942 | 41.91 | 4.05 | 89.19 | medium | 91.6% (93.5%) (53785) | 95.0% |  |
| oakland | 1946 | oaklandwest1949, oaklandeast1947, sanleandro1947 | 71.91 | 6.23 | 134.7 | high | 95.7% (96.8%) (86788) | 93.4% | downtown 1951: 100% of 28 / 33% of 3; west 1951: 100% of 69 / 82% of 17 |
| berkeley | 1894 | sf1895, concord1897 | 4.7 | 4.81 | 41.57 | medium | 62.5% (85.1%) (275) |  |  |
| berkeley | 1914 | sf1915, concord1915 | 11.89 | 5.87 | 41.57 | medium | 88.0% (97.0%) (7619) | 82.8% | downtown 1911: 88% of 17 / 33% of 6; southside 1911: 77% of 30 / 0% of 5; west 1911: 22% of 9 / 13% of 30 |
| berkeley | 1946 | richmond1947, oaklandwest1949, briones1947, oaklandeast1947 | 25.1 | 0.95 | 41.57 | high | 99.3% (99.7%) (30117) | 98.5% |  |
| alameda | 1894 | sf1895, concord1897 | 4.04 | 1.76 | 35.67 | medium | 76.8% (90.3%) (967) |  | westend 1897: 100% of 3 / 10% of 30 |
| alameda | 1914 | sf1915, concord1915 | 5.32 | 1.51 | 35.67 | medium | 87.5% (95.8%) (5936) | 85.8% |  |
| alameda | 1946 | oaklandwest1949, oaklandeast1947 | 9.76 | 1.28 | 35.67 | high | 97.7% (98.3%) (12359) | 97.7% | westend 1948: 100% of 22 / 67% of 15 |
| san_jose | 1885 | sanjose1889 | 5.73 | 10.2 | 184.6 | medium | 56.5% (72.1%) (154) |  |  |
| san_jose | 1895 | sanjose1897 | 6.86 | 11.28 | 184.6 | medium | 55.1% (76.1%) (410) | 92.7% |  |
| san_jose | 1939 | sanjose1943 | 33.73 | 10.83 | 184.6 | medium | 92.3% (94.3%) (22224) | 86.2% |  |
| san_jose | 1948 | sanjosewest1953, sanjoseeast1953, milpitas1953 | 46.4 | 7.45 | 173.96 | high | 94.5% (96.8%) (28845) | 89.0% | jose_downtown 1950: 100% of 92 / 67% of 18 |
| san_leandro | 1896 | haywards1899 | 0.66 | 1.39 | 39.77 | low | 16.7% (46.2%) (78) |  |  |
| san_leandro | 1914 | hayward1915 | 1.24 | 2.53 | 39.77 | low | 24.3% (54.8%) (547) | 79.6% |  |
| san_leandro | 1939 | hayward1942 | 5.88 | 0.68 | 39.77 | medium | 90.2% (91.4%) (4853) | 71.4% |  |
| san_leandro | 1946 | sanleandro1947, hayward1947 | 8.66 | 2.1 | 39.77 | high | 94.4% (97.2%) (9993) | 93.6% |  |
| hayward | 1896 | haywards1899 | 0.62 | 1.91 | 77.54 | low | 6.1% (38.8%) (49) |  |  |
| hayward | 1914 | hayward1915 | 0.98 | 2.38 | 77.54 | low | 22.1% (44.6%) (399) | 98.4% |  |
| hayward | 1939 | hayward1942 | 5.24 | 1.93 | 77.54 | medium | 58.3% (63.5%) (2471) | 68.6% |  |
| hayward | 1946 | hayward1947, sanleandro1947, newark1947 | 5.02 | 4.67 | 73.86 | medium | 70.4% (86.2%) (3677) | 62.8% |  |
| richmond | 1894 | sf1895 | 0.72 | 2.0 | 99.16 | low | 0.0% (7.7%) (13) |  |  |
| richmond | 1914 | sf1915 | 3.9 | 5.02 | 99.16 | medium | 58.6% (79.4%) (2031) | 22.6% | downtown 1916: 100% of 9 / 27% of 11 |
| richmond | 1946 | richmond1947, sanquentin1948 | 27.18 | 4.05 | 99.16 | high | 95.3% (96.7%) (19638) | 87.5% |  |
| palo_alto | 1895 | paloalto1899 | 0.5 | 1.74 | 32.33 | low | 9.7% (45.2%) (31) |  | alto_downtown 1901: 75% of 4 / 0% of 7 |
| palo_alto | 1940 | paloalto1943 | 7.1 | 1.07 | 32.33 | medium | 83.6% (86.4%) (4962) | 66.4% |  |
| palo_alto | 1948 | paloalto1953, mountainview1953 | 12.92 | 1.45 | 32.33 | high | 95.7% (96.3%) (6476) | 89.8% |  |
| redwood_city | 1895 | paloalto1899 | 0.37 | 0.66 | 18.99 | low | 56.8% (73.0%) (37) |  |  |
| redwood_city | 1940 | paloalto1943 | 8.68 | 0.55 | 18.99 | medium | 93.1% (96.7%) (3470) | 97.3% |  |
| redwood_city | 1948 | paloalto1953, woodside1953, redwoodpoint1948 | 13.15 | 0.88 | 27.78 | high | 97.3% (98.3%) (6342) | 93.0% |  |
| san_mateo | 1892 | sanmateo1896 | 0.62 | 1.46 | 51.63 | low | 13.0% (26.1%) (23) |  |  |
| san_mateo | 1914 | sanmateo1915 | 0.46 | 1.87 | 51.63 | low | 3.1% (20.0%) (1574) | 11.3% | mateo_downtown 1908: 58% of 12 / 0% of 9; mateo_downtown 1920: 57% of 14 / 0% of 12 |
| san_mateo | 1939 | sanmateo1943 | 12.87 | 1.28 | 51.63 | medium | 93.4% (96.4%) (9751) | 63.1% |  |
| san_mateo | 1946 | sanmateo1947 | 17.0 | 1.18 | 48.74 | high | 99.0% (99.4%) (12730) | 95.4% |  |
| san_rafael | 1895 | tamalpais1897, sf1895 | 1.89 | 1.65 | 27.03 | medium | 62.4% (76.8%) (125) |  |  |
| san_rafael | 1939 | tamalpais1941 | 2.04 | 1.54 | 18.56 | medium | 61.9% (76.0%) (2362) | 56.2% |  |
| san_rafael | 1952 | sanrafael1954, sanquentin1948 | 5.87 | 1.71 | 27.03 | high | 88.6% (94.1%) (4540) | 94.3% |  |
| martinez | 1896 | karquines1898 | 0.19 | 0.56 | 10.31 | low | 15.7% (76.5%) (51) |  |  |
| martinez | 1940 | carquinezstrait1940 | 1.4 | 0.79 | 10.31 | medium | 80.7% (91.5%) (1677) | 68.2% |  |
| martinez | 1948 | benicia1950, briones1947, portchicago1951 | 2.63 | 1.06 | 12.32 | high | 89.1% (96.3%) (2245) | 92.9% |  |
<!-- /snapshots -->

### Probes and threshold sensitivity

<!-- probes -->
| town | year | probe | share inside |
|---|---|---|---|
| oakland | 1894 | lakeside_uptown | 46.9% |
| oakland | 1894 | west_oakland | 83.3% |
| oakland | 1894 | temescal | 30.4% |
| oakland | 1894 | block km² at share 0.25 / 0.35 / 0.45 | 12.9 / 10.2 / 8.0 |
| oakland | 1914 | lakeside_uptown | 74.8% |
| oakland | 1914 | west_oakland | 91.8% |
| oakland | 1914 | temescal | 79.3% |
| oakland | 1914 | block km² at share 0.25 / 0.35 / 0.45 | 29.5 / 25.1 / 20.9 |
| oakland | 1946 | lakeside_uptown | 78.2% |
| oakland | 1946 | west_oakland | 94.1% |
| oakland | 1946 | temescal | 98.6% |
| berkeley | 1894 | block km² at share 0.25 / 0.35 / 0.45 | 5.8 / 4.3 / 3.3 |
| berkeley | 1914 | block km² at share 0.25 / 0.35 / 0.45 | 12.7 / 10.8 / 8.9 |
| alameda | 1894 | block km² at share 0.25 / 0.35 / 0.45 | 4.3 / 3.7 / 3.1 |
| alameda | 1914 | block km² at share 0.25 / 0.35 / 0.45 | 5.5 / 5.0 / 4.4 |
| san_jose | 1885 | block km² at share 0.25 / 0.35 / 0.45 | 7.1 / 5.0 / 3.6 |
| san_jose | 1895 | block km² at share 0.25 / 0.35 / 0.45 | 7.8 / 5.7 / 4.3 |
| san_leandro | 1896 | block km² at share 0.25 / 0.35 / 0.45 | 0.8 / 0.5 / 0.3 |
| san_leandro | 1914 | block km² at share 0.25 / 0.35 / 0.45 | 1.4 / 1.0 / 0.7 |
| hayward | 1896 | block km² at share 0.25 / 0.35 / 0.45 | 1.0 / 0.6 / 0.5 |
| hayward | 1914 | block km² at share 0.25 / 0.35 / 0.45 | 1.4 / 0.9 / 0.6 |
| richmond | 1894 | block km² at share 0.25 / 0.35 / 0.45 | 1.2 / 0.6 / 0.4 |
| richmond | 1914 | block km² at share 0.25 / 0.35 / 0.45 | 4.6 / 3.2 / 2.5 |
| palo_alto | 1895 | block km² at share 0.25 / 0.35 / 0.45 | 0.8 / 0.4 / 0.2 |
| redwood_city | 1895 | block km² at share 0.25 / 0.35 / 0.45 | 0.5 / 0.3 / 0.2 |
| san_mateo | 1892 | block km² at share 0.25 / 0.35 / 0.45 | 1.2 / 0.7 / 0.3 |
| san_mateo | 1914 | block km² at share 0.25 / 0.35 / 0.45 | 0.8 / 0.4 / 0.2 |
| san_rafael | 1895 | block km² at share 0.25 / 0.35 / 0.45 | 2.0 / 1.4 / 1.0 |
| martinez | 1896 | block km² at share 0.25 / 0.35 / 0.45 | 0.3 / 0.2 / 0.1 |
<!-- /probes -->

## Maps used

<!-- maps -->
| sheet | quadrangle | scale | edition | shows | reading | alignment to today's streets | GeoPDF |
|---|---|---|---|---|---|---|---|
| `sanjose1889` | San Jose | 1:62,500 | 1889 | 1885 (surveyed 1885 (1939 reprint)) | bands + squares | 239 m (affine, 43/63 windows, RMS 22 m) | [301582](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Jose_301582_1889_62500_geo.pdf) |
| `sanmateo1896` | San Mateo | 1:62,500 | 1896 | 1892 (surveyed 1892) | bands + squares | 208 m (affine, 9/17 windows, RMS 16 m) | [298916](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Mateo_298916_1896_62500_geo.pdf) |
| `concord1897` | Concord | 1:62,500 | 1897 | 1894 (surveyed 1893-94 (collar), engraved Apr 1897) | bands + squares | 113 m (affine, 10/15 windows, RMS 19 m) | [297157](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Concord_297157_1897_62500_geo.pdf) |
| `sf1895` | San Francisco | 1:62,500 | 1895 | 1894 (surveyed 1892-94) | bands + squares | 221 m (affine, 43/67 windows, RMS 21 m) | [298889](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Francisco_298889_1895_62500_geo.pdf) |
| `paloalto1899` | Palo Alto | 1:62,500 | 1899 | 1895 (surveyed 1895) | bands + squares | 193 m (affine, 28/42 windows, RMS 19 m) | [298453](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Palo%20Alto_298453_1899_62500_geo.pdf) |
| `sanjose1897` | San Jose | 1:62,500 | 1897 | 1895 (surveyed 1895) | bands + squares | 250 m (affine, 53/84 windows, RMS 23 m) | [298899](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Jose_298899_1897_62500_geo.pdf) |
| `tamalpais1897` | Tamalpais | 1:62,500 | 1897 | 1895 (surveyed 1895) | bands + squares | 204 m (affine, 23/27 windows, RMS 21 m) | [298980](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Tamalpais_298980_1897_62500_geo.pdf) |
| `haywards1899` | Haywards | 1:62,500 | 1899 | 1896 (surveyed 1896 (1901 imprint)) | bands + squares | 215 m (affine, 35/57 windows, RMS 20 m) | [297665](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Haywards_297665_1899_62500_geo.pdf) |
| `karquines1898` | Karquines | 1:62,500 | 1898 | 1896 (surveyed 1896) | bands + squares | 194 m (affine, 7/15 windows, RMS 23 m) | [297860](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Karquines_297860_1898_62500_geo.pdf) |
| `concord1915` | Concord | 1:62,500 | 1915 | 1914 (edition of June 1915: surveyed 1893-94, culture revised in part in 1913-14 (collar note)) | bands + squares | 211 m (affine, 31/62 windows, RMS 16 m) | [297163](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Concord_297163_1915_62500_geo.pdf) |
| `hayward1915` | Hayward | 1:62,500 | 1915 | 1914 (surveyed 1914 (1939 imprint)) | bands + squares | 217 m (affine, 41/68 windows, RMS 18 m) | [297660](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Hayward_297660_1915_62500_geo.pdf) |
| `sanmateo1915` | San Mateo | 1:62,500 | 1915 | 1914 (1915 edition: surveyed 1892, culture revised in part in 1914 (collar note)) | bands + squares | 209 m (affine, 30/37 windows, RMS 8 m) | [298922](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Mateo_298922_1915_62500_geo.pdf) |
| `sf1915` | San Francisco | 1:62,500 | 1915 | 1914 (1915 edition: surveyed 1892-94, culture revised in 1914 (collar note)) | bands + squares | 223 m (affine, 105/128 windows, RMS 20 m) | [298897](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Francisco_298897_1915_62500_geo.pdf) |
| `concord1942` | Concord | 1:62,500 | 1942 | 1939 (aerial photographs 1939) | grey tint | 7 m (affine, 54/187 windows, RMS 7 m) | [465521](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Concord_465521_1942_62500_geo.pdf) |
| `hayward1942` | Hayward | 1:62,500 | 1942 | 1939 (aerial photographs 1939) | grey tint | 17 m (affine, 56/135 windows, RMS 7 m) | [465728](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Hayward_465728_1942_62500_geo.pdf) |
| `sanjose1943` | San Jose | 1:62,500 | 1943 | 1939 (aerial photographs 1939) | grey tint | 17 m (affine, 73/210 windows, RMS 7 m) | [466308](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Jose_466308_1943_62500_geo.pdf) |
| `sanmateo1943` | San Mateo | 1:62,500 | 1943 | 1939 (aerial photographs 1939) | grey tint | as published (fit 5 m, RMS 7 m) | [466324](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Mateo_466324_1943_62500_geo.pdf) |
| `tamalpais1941` | Tamalpais | 1:62,500 | 1941 | 1939 (aerial photographs 1939) | grey tint | 9 m (affine, 19/64 windows, RMS 8 m) | [301788](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Tamalpais_301788_1941_62500_geo.pdf) |
| `carquinezstrait1940` | Carquinez Strait | 1:62,500 | 1940 | 1940 (aerial photographs 1940 (1965 imprint)) | grey tint | 8 m (affine, 21/66 windows, RMS 7 m) | [297037](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Carquinez%20Strait_297037_1940_62500_geo.pdf) |
| `paloalto1943` | Palo Alto | 1:62,500 | 1943 | 1940 (aerial photographs 1940) | grey tint | as published (fit 6 m, RMS 8 m) | [298463](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Palo%20Alto_298463_1943_62500_geo.pdf) |
| `briones1947` | Briones Valley | 1:24,000 | 1947 | 1946 (aerial photographs 1946, field check 1947) | pink tint | as published (fit 4 m, RMS 5 m) | [288606](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Briones%20Valley_288606_1947_24000_geo.pdf) |
| `hayward1947` | Hayward | 1:24,000 | 1947 | 1946 (aerial photographs 1946, survey 1947) | pink tint | 8 m (affine, 22/26 windows, RMS 4 m) | [291242](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Hayward_291242_1947_24000_geo.pdf) |
| `newark1947` | Newark | 1:24,000 | 1947 | 1946 (aerial photographs 1946) | pink tint | as published (fit 2 m, RMS 8 m) | [293493](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Newark_293493_1947_24000_geo.pdf) |
| `oaklandeast1947` | Oakland East | 1:24,000 | 1947 | 1946 (aerial photographs 1946, field check 1947) | pink tint | 6 m (affine, 43/43 windows, RMS 4 m) | [293612](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Oakland%20East_293612_1947_24000_geo.pdf) |
| `oaklandwest1949` | Oakland West | 1:24,000 | 1949 | 1946 (aerial photographs 1946, field check 1947) | pink tint | as published (fit 3 m, RMS 5 m) | [293623](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Oakland%20West_293623_1949_24000_geo.pdf) |
| `richmond1947` | Richmond | 1:24,000 | 1947 | 1946 (aerial photographs 1946, field check 1947) | pink tint | as published (fit 4 m, RMS 4 m) | [294667](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Richmond_294667_1947_24000_geo.pdf) |
| `sanleandro1947` | San Leandro | 1:24,000 | 1947 | 1946 (1947 edition (photos c. 1946)) | pink tint | as published (fit 2 m, RMS 5 m) | [300122](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_San%20Leandro_300122_1947_24000_geo.pdf) |
| `sanmateo1947` | San Mateo | 1:24,000 | 1947 | 1946 (aerial photographs 1946, field check 1947) | pink tint | as published (fit 3 m, RMS 4 m) | [300157](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_San%20Mateo_300157_1947_24000_geo.pdf) |
| `sanquentin1948` | San Quentin | 1:24,000 | 1948 | 1947 (aerial photographs 1947) | pink tint | as published (fit 1 m, RMS 4 m) | [300194](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_San%20Quentin_300194_1948_24000_geo.pdf) |
| `benicia1950` | Benicia | 1:24,000 | 1950 | 1948 (aerial photographs 1948, field check 1950) | pink tint | as published (fit 4 m, RMS 6 m) | [288319](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Benicia_288319_1950_24000_geo.pdf) |
| `milpitas1953` | Milpitas | 1:24,000 | 1953 | 1948 (aerial photographs 1948, survey 1953) | pink tint | 6 m (affine, 6/13 windows, RMS 5 m) | [292969](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Milpitas_292969_1953_24000_geo.pdf) |
| `mountainview1953` | Mountain View | 1:24,000 | 1953 | 1948 (aerial photographs 1948, survey 1953) | pink tint | as published (fit 4 m, RMS 5 m) | [293234](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Mountain%20View_293234_1953_24000_geo.pdf) |
| `paloalto1953` | Palo Alto | 1:24,000 | 1953 | 1948 (aerial photographs 1948, survey 1953) | pink tint | as published (fit 1 m, RMS 4 m) | [293907](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Palo%20Alto_293907_1953_24000_geo.pdf) |
| `portchicago1951` | Port Chicago | 1:24,000 | 1951 | 1948 (aerial photographs 1948, survey 1950) | pink tint | 13 m (affine, 14/22 windows, RMS 8 m) | [294325](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Port%20Chicago_294325_1951_24000_geo.pdf) |
| `redwoodpoint1948` | Redwood Point | 1:24,000 | 1948 | 1948 (1948 edition) | pink tint | as published | [294610](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Redwood%20Point_294610_1948_24000_geo.pdf) |
| `sanjoseeast1953` | San Jose East | 1:24,000 | 1953 | 1948 (aerial photographs 1948, survey 1953) | pink tint | as published (fit 6 m, RMS 4 m) | [300099](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_San%20Jose%20East_300099_1953_24000_geo.pdf) |
| `sanjosewest1953` | San Jose West | 1:24,000 | 1953 | 1948 (aerial photographs 1948, survey 1953) | pink tint | as published (fit 2 m, RMS 5 m) | [300105](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_San%20Jose%20West_300105_1953_24000_geo.pdf) |
| `woodside1953` | Woodside | 1:24,000 | 1953 | 1948 (aerial photographs 1948, field check 1953) | pink tint | 7 m (affine, 34/34 windows, RMS 4 m) | [301429](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Woodside_301429_1953_24000_geo.pdf) |
| `sanrafael1954` | San Rafael | 1:24,000 | 1954 | 1952 (aerial photographs 1952, field check 1954) | pink tint | as published (fit 5 m, RMS 4 m) | [300201](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_San%20Rafael_300201_1954_24000_geo.pdf) |
<!-- /maps -->

## Per-town notes

* **Oakland** (incl. Emeryville, Piedmont). 1894 = San Francisco 1895 (west of 122°15') + Concord
  1897 (east of it; both surveyed 1893-94) + Haywards 1899 (south of 37°45', surveyed 1896). 1914 = the
  1915 editions (culture revised 1913-14) + Hayward 1915 (surveyed 1914). 1939 = Concord 1942 +
  Hayward 1942 (1939 photographs): **east and south parts only** (no 1940s edition of the San
  Francisco 15' quadrangle). 1946 = Oakland West 1949, Oakland East 1947, San Leandro 1947 (1946
  photographs). Lakeside / Uptown (Broadway to the lake, 14th St to Grand Ave), which the live map
  showed half empty in 1910, is about three quarters built up on the 1914 map (half in 1894; the rest
  is the lakeshore park strip and a few blocks around Grand Ave).
* **Berkeley** (incl. Albany). 1894, 1914 as Oakland; 1946 = Richmond 1947 (north of 37°52'30"),
  Oakland West 1949, Briones Valley 1947, Oakland East 1947. No 1939 snapshot (only the hills are on
  Concord 1942). The 1911 Sanborn blocks of West Berkeley are mostly industrial lots in today's large
  blocks and read low.
* **Alameda.** 1894, 1914 as Oakland; 1946 = Oakland West / East. No 1939 snapshot (Concord 1942
  covers only the east end).
* **San José** (incl. Santa Clara). 1885 = San Jose 1889 edition (survey 1885; the scan is a 1939
  reprint of the unchanged plate); 1895 = San Jose 1897 (survey 1895; USGS scan quality "not
  optimal"); 1939 = San Jose 1943 (1939 photographs, grey tint; darker paper); 1948 = San Jose West /
  East, Milpitas 1953 (1948 photographs). No topographic survey between 1895 and 1939 (the downtown
  1915 Sanborn tracing covers that gap locally).
* **San Leandro, Hayward.** 1896 = Haywards 1899; 1914 = Hayward 1915 (resurveyed 1914); 1939 =
  Hayward 1942 (1939 photographs: the grey tint covers only Oakland; both towns are drawn house by
  house and read with the frontage rule); 1946 = San Leandro, Hayward, Newark 1947.
* **Richmond** (incl. El Cerrito, San Pablo). 1894 = San Francisco 1895 (before Richmond: Stege and the
  San Pablo Avenue strip); 1914 = San Francisco 1915; 1946 = Richmond 1947 + San Quentin 1948 (Point
  Richmond, 1947 photographs).
* **Palo Alto** (incl. Mayfield), **Redwood City.** 1895 = Palo Alto 1899 edition (survey 1895); 1940 =
  Palo Alto 1943 (1940 photographs, grey tint); 1948 = Palo Alto, Mountain View, Woodside 1953 and
  Redwood Point 1948. No c. 1914 survey.
* **San Mateo** (incl. Burlingame). 1892 = San Mateo 1896 edition (survey 1892); 1914 = 1915 edition
  ("culture revised in part in 1914": the town is drawn house by house and the revision evidently did
  not redraw every new tract; see `_partial`); 1939 = San Mateo 1943 (1939 photographs); 1946 = San
  Mateo 1947. The large lettering "SAN MATEO" over the town adds a few blocks in 1892 / 1914.
* **San Rafael.** 1895 = Tamalpais 1897 (survey 1895) + San Francisco 1895 (east of 122°30'); 1939 =
  Tamalpais 1941 (1939 photographs; houses drawn, no tint; west of 122°30' only); 1952 = San Rafael
  1954 (1952 photographs) + San Quentin 1948 (east margin, 1947 photographs).
* **Martinez.** 1896 = Karquines 1898; 1940 = Carquinez Strait 1940 (1940 photographs, 1965 imprint;
  houses drawn). The Carquinez 1942 edition (1937 photographs) draws the town as streets only and was
  not used. 1948 = Benicia 1950, Briones Valley 1947, Port Chicago 1951.

## Limits

* **Generalisation.** At 1:62,500 a house square is ~25 m across and rows are drawn as bands, so the
  share is a reading of the cartographer's generalisation, not a count of lots. Blocks near the
  threshold flip with ±0.1 of it (see sensitivity).
* **Lettering and symbols near streets** (town names in large capitals over the town, e.g. "SAN MATEO",
  "OAKLAND") still count as ink; railway yards and industrial plants read as built up (they are built,
  not with houses); on the 1940s sheets ink under today's freeways is dropped with the highway symbol.
* **Alignment** RMS 15-25 m on the early sheets; a block's band can fall in its neighbour where the
  survey is locally distorted (the 1890s East Oakland hills).
* **Missing dates.** No c. 1878-80 snapshot: no georeferenceable map of that time draws buildings (the
  Thompson & West 1878 Alameda County atlas draws subdivisions and owners, not houses — checked on its
  map 16, Berkeley / North Oakland, David Rumsey Map Collection; the 1857 Coast Survey chart of
  Oakland is too early). No c. 1929-31 snapshot: the 1920s-30s imprints are reprints of the 1914-15
  plates, the next survey generation is the 1937-40 aerial photographs. Sanborn key maps (LOC: Oakland
  1925-29 vols. 4-8) could give a coverage proxy for parts of Oakland; not done.
* **Survey vs. edition.** The `year` of a 1:24,000 sheet is its photo year; the field check is 1-5
  years later. The 1885-1915 sheets show the survey (or revision) year; "culture revised in part"
  editions may miss tracts.
