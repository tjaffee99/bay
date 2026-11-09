# Built-up extents of the region's older towns, from USGS historical topographic maps

Where each older town of the five modelled counties was **built up** at the date of a real, dated map:
the region's counterpart of San Francisco's `sf_extent_<year>.csv` (decision 14, `../sf_extent_README.md`).
"Built up" means street blocks substantially covered with buildings, as the map draws them; a block
that was merely platted (streets laid out, a few houses) is not built up.

Every snapshot is read from one survey generation of the USGS topographic quadrangles (public domain,
`SOURCES.md` → `region_extents`), nothing is interpolated and nothing is generated. Built by
`tools/extents.py` (`python -I tools/extents.py all <town>`, then `report x` for the tables below).

## Files

| file | content |
|---|---|
| `<town>_<year>.geojson` | one Feature, a (Multi)Polygon (EPSG:4326): the built-up area at `year` |
| `coverage.geojson` | one Feature per town and snapshot: the area that snapshot **read** (the sheets' quadrangles × the town × the processing box). Outside it a snapshot says nothing: e.g. `oakland_1939` covers only the part of Oakland east of 122°15' W and south of 37°45' N |
| `check/<town>.png` | the snapshots in sequence (new area per snapshot in its colour over the earlier ones; dashed: area read; black dots: buildings standing today that predate the map) |
| `tools/extents.py` | the whole method (render, alignment, blocks, classification, checks, these tables) |

Properties of a snapshot feature: `town`, `year` (what the map shows: the survey year, the year of
the culture revision, or the year of the aerial photographs the map was compiled from), `kind`
(`built_up`), `source` (`usgs_htmc:<sheet key>` joined with `+`; sheet keys in the maps table below),
`source_url` (the GeoPDFs, space-separated), `confidence` (`high` / `medium` / `low`), `note` (per sheet:
edition, survey / revision / photo years; the area read), `edition_years`, `map_years`, `method`,
`area_km2`, `n_blocks`.

Towns (`town` = today's TIGER 2024 places merged): `oakland` (Oakland, Emeryville, Piedmont),
`berkeley` (Berkeley, Albany), `alameda`, `san_jose` (San José, Santa Clara), `san_leandro`, `hayward`,
`richmond` (Richmond, El Cerrito, San Pablo), `palo_alto` (incl. Mayfield), `redwood_city`,
`san_mateo` (San Mateo, Burlingame), `san_rafael`, `martinez`. Each is processed inside a box around
its historic core and its growth to c. 1950 (`TOWNS[...]["bbox"]` in the tool), clipped to today's land.

## How to use it

* A snapshot is a statement **inside its coverage polygon** only.
* Snapshots are read independently and are not forced to nest. Where a later map no longer shows an
  earlier built-up block (the share is given per snapshot as "prev. snapshot kept" below: 87-95 % in
  Oakland) the reason is mostly the reading (the threshold, alignment, a railway yard or a big
  building read differently), rarely a real clearance before 1950. As for SF, **the union of the
  earlier snapshots is a safe lower bound**: a block first contained in snapshot *k* was built up
  between snapshot *k-1* and *k*.
* The extent is on today's land: fill made after the map date is inside a polygon when the block
  around it was built up (port areas, the waterfront); clip with the land-year grid.
* The polygons follow today's street blocks (centrelines of today's streets), so a block is in or out
  as a whole; today's superblocks (freeways, campuses, the Post Office, City Center) are read in 100 m
  cells.

## Method

1. **Sheets.** The 1:62,500 15' quadrangles of 1885-1915 (first surveys and the 1915 editions with
   "culture revised in 1914"), the 1:62,500 editions of 1940-43 compiled from 1937-40 aerial
   photographs, and the 1:24,000 7.5' quadrangles of 1947-54 compiled from 1946-52 photographs (TNM
   Access API; survey / photo years from each scan's FGDC record and, for the 1915 editions, from the
   collar: San Francisco 1915 "Surveyed in 1892-94. Culture revised in 1914", Concord 1915 "Surveyed
   in 1893-94. Culture revised in part in 1913-14. Edition of June 1915"). The later imprints are
   reprints of the same plates: the 1929 reprint of San Francisco 1915 shows the 1914 culture
   unchanged (checked over Oakland), so the reprints give no c. 1930 snapshot.
2. **Scan and registration.** The GeoPDF's 600-700 ppi scan (2.35 m per pixel at 1:62,500; the
   GeoTIFF is a 300 ppi resample) is resampled into UTM 10N at 2.5 m through its own registration
   (LGIDict CTM, polyconic NAD27; `pipeline/topo_farmsteads.GeoPDF`) and the NOAA NADCON grid, masked
   to the quadrangle minus 0.5 mm along the neat line.
3. **Alignment.** Black ink of the whole quadrangle (5 m pixels) is cross-correlated with today's
   street centrelines (Overture / OpenStreetMap) in 2.5 km windows, ±420 m search on the early sheets,
   ±120 m on the 1940s ones; window shifts are fitted by consensus (constant, then affine when the
   windows span > 3 km). The 1890s-1915 surveys are **~210-225 m** off (Concord 1897 113 m), RMS
   15-21 m after the fit; the 1940s sheets 2-17 m (the 1:24,000 sheets are used as published when the
   fit is under 6 m). Same approach and magnitudes as `../farmsteads/README.md`.
4. **Blocks.** Today's street centrelines (Overture: trunk, primary, secondary, tertiary,
   residential, unclassified, living street; not motorways or service roads) polygonised and clipped
   to the town and to today's land (`data/interim/land_modern.fgb`, which leaves out the bay and Lake
   Merritt). Blocks over 5 ha (hills, parks, cemeteries, yards, superblocks) are cut into 100 m cells.
5. **Reading the early sheets (1885-1915).** These sheets draw a closely built block front as a heavy
   black band along the street (~0.25-0.33 mm, measured band thickness 16-21 m on the ground) and a
   scattered house as a solid square. Black ink (dark and neutral: contours are brown, water blue) →
   opening with a 0.15 mm disc (street casings, contours, thin lettering vanish) → *bands* = what
   survives an opening with a 40 m line at 12 orientations; *squares* = the remaining compact blobs
   ≥ 0.25 × 0.25 mm. Ink further than 60 m from a street of today (big lettering in the hills,
   triangulation marks) or within 12 m of a railway (Overture rail + `../historic_rail.geojson`) is not
   counted. **Built frontage share** of a block = (band length + 15 m per square) / frontage (the
   perimeter 15 m inside the street centrelines). A block is built up at share ≥ **0.35** (SF used
   "about a third of the frontage"); a 100 m cell needs share ≥ 0.35 and ≥ 20 % heavy ink (a rail
   line or two is not built-up).
6. **Reading the 1939-53 sheets.** These tint the built-up area (1:24,000: pink ground with a red dot
   screen; 1:62,500 1940-43 editions: a grey-tan screen) and draw only landmark buildings inside it.
   Tint pixels → majority over 0.8 mm → opening 0.6 mm (drops the anti-aliased edges of road lines) →
   a block is built up when ≥ 50 % of it is tinted, or by the frontage rule above (houses drawn
   individually outside the tint, e.g. San Leandro on Hayward 1942, where the tint stops at the
   Oakland line).
7. **Polygons.** Built blocks merged, closed by 12 m (street gaps), holes under 0.6 ha or thinner
   than 10 m filled, parts under 0.8 ha dropped, clipped to the town and today's land, simplified 1 m.

## Validation

* **Buildings standing today that predate the map** (`data/interim/region_building_points.parquet`,
  `end_year = 9999`, ≥ 30 m², start year before the map year; inside the area read): share inside the
  extent (+20 m). A built-up area should contain most of them; the rest are farmhouses, scattered
  houses on half-built blocks, or wrong roll years. Also the share of extent blocks holding at least
  one such building (a low number for 1890s downtowns: most of their fabric is gone).
* **Sanborn tracings** (`../sanborn/<area>_<year>.geojson`, within ±6 years of the snapshot): blocks of
  today fully inside the traced coverage with ≥ 15 % of their area under traced footprints ("built")
  and < 5 % ("empty"); share of each inside the extent.
* **Probes:** districts known to be built up by the map date (boxes in `PROBES`), share of their land
  inside the extent; and the block area at frontage-share thresholds 0.25 / 0.35 / 0.45 (sensitivity).
* Every check PNG was looked at; overlays of the extent on the aligned sheet were checked by eye in
  Oakland (Lakeside / Uptown, West Oakland, Fruitvale, the 37°45' sheet edge).

### Snapshots

<!-- snapshots -->
| town | year | sheets | built-up km² | area read km² | confidence | pre-map buildings standing today inside (n) | prev. snapshot kept | Sanborn built blocks inside / empty blocks inside |
|---|---|---|---|---|---|---|---|---|
| oakland | 1894 | sf1895, concord1897, haywards1899 | 11.8 | 134.7 | medium | 81.8% (2362) |  |  |
| oakland | 1914 | sf1915, concord1915, hayward1915 | 29.09 | 134.7 | medium | 83.1% (23290) | 87.3% | downtown 1912: 97% of 30 / 100% of 2; west 1912: 89% of 71 / 33% of 12 |
| oakland | 1939 | concord1942, hayward1942 | 44.6 | 89.19 | medium | 92.7% (53785) | 95.2% |  |
| oakland | 1946 | oaklandwest1949, oaklandeast1947, sanleandro1947 | 73.24 | 134.7 | high | 96.5% (86788) | 91.4% | downtown 1951: 100% of 28 / 33% of 3; west 1951: 100% of 69 / 82% of 17 |
<!-- /snapshots -->

### Probes and threshold sensitivity

<!-- probes -->
| town | year | probe | share inside |
|---|---|---|---|
| oakland | 1894 | lakeside_uptown | 49.0% |
| oakland | 1894 | west_oakland | 83.3% |
| oakland | 1894 | temescal | 30.5% |
| oakland | 1894 | block km² at share 0.25 / 0.35 / 0.45 | 12.9 / 10.2 / 8.0 |
| oakland | 1914 | lakeside_uptown | 74.8% |
| oakland | 1914 | west_oakland | 91.8% |
| oakland | 1914 | temescal | 79.3% |
| oakland | 1914 | block km² at share 0.25 / 0.35 / 0.45 | 29.5 / 25.1 / 20.9 |
| oakland | 1946 | lakeside_uptown | 78.3% |
| oakland | 1946 | west_oakland | 95.3% |
| oakland | 1946 | temescal | 98.7% |
<!-- /probes -->

## Maps used

<!-- maps -->
| sheet | quadrangle | scale | edition | shows | reading | alignment to today's streets | GeoPDF |
|---|---|---|---|---|---|---|---|
| `sanjose1889` | San Jose | 1:62,500 | 1889 | 1885 (surveyed 1885 (1939 reprint)) | bands + squares | 239 m (affine, 43/63 windows, RMS 22 m) | [301582](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Jose_301582_1889_62500_geo.pdf) |
| `concord1897` | Concord | 1:62,500 | 1897 | 1894 (surveyed 1893-94 (collar), engraved Apr 1897) | bands + squares | 113 m (affine, 10/15 windows, RMS 19 m) | [297157](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Concord_297157_1897_62500_geo.pdf) |
| `sf1895` | San Francisco | 1:62,500 | 1895 | 1894 (surveyed 1892-94) | bands + squares | 221 m (affine, 43/67 windows, RMS 21 m) | [298889](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Francisco_298889_1895_62500_geo.pdf) |
| `sanjose1897` | San Jose | 1:62,500 | 1897 | 1895 (surveyed 1895) | bands + squares | 250 m (affine, 53/84 windows, RMS 23 m) | [298899](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Jose_298899_1897_62500_geo.pdf) |
| `haywards1899` | Haywards | 1:62,500 | 1899 | 1896 (surveyed 1896 (1901 imprint)) | bands + squares | 215 m (affine, 35/57 windows, RMS 20 m) | [297665](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Haywards_297665_1899_62500_geo.pdf) |
| `concord1915` | Concord | 1:62,500 | 1915 | 1914 (edition of June 1915: surveyed 1893-94, culture revised in part in 1913-14 (collar note)) | bands + squares | 211 m (affine, 31/62 windows, RMS 16 m) | [297163](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Concord_297163_1915_62500_geo.pdf) |
| `hayward1915` | Hayward | 1:62,500 | 1915 | 1914 (surveyed 1914 (1939 imprint)) | bands + squares | 217 m (affine, 41/68 windows, RMS 18 m) | [297660](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Hayward_297660_1915_62500_geo.pdf) |
| `sf1915` | San Francisco | 1:62,500 | 1915 | 1914 (1915 edition: surveyed 1892-94, culture revised in 1914 (collar note)) | bands + squares | 223 m (affine, 105/128 windows, RMS 20 m) | [298897](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Francisco_298897_1915_62500_geo.pdf) |
| `concord1942` | Concord | 1:62,500 | 1942 | 1939 (aerial photographs 1939) | grey tint | 7 m (affine, 54/187 windows, RMS 7 m) | [465521](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Concord_465521_1942_62500_geo.pdf) |
| `hayward1942` | Hayward | 1:62,500 | 1942 | 1939 (aerial photographs 1939) | grey tint | 17 m (affine, 56/135 windows, RMS 7 m) | [465728](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Hayward_465728_1942_62500_geo.pdf) |
| `sanjose1943` | San Jose | 1:62,500 | 1943 | 1939 (aerial photographs 1939) | grey tint | 17 m (affine, 73/210 windows, RMS 7 m) | [466308](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Jose_466308_1943_62500_geo.pdf) |
| `briones1947` | Briones Valley | 1:24,000 | 1947 | 1946 (aerial photographs 1946, field check 1947) | pink tint | as published (fit 4 m, RMS 5 m) | [288606](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Briones%20Valley_288606_1947_24000_geo.pdf) |
| `oaklandeast1947` | Oakland East | 1:24,000 | 1947 | 1946 (aerial photographs 1946, field check 1947) | pink tint | 6 m (affine, 43/43 windows, RMS 4 m) | [293612](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Oakland%20East_293612_1947_24000_geo.pdf) |
| `oaklandwest1949` | Oakland West | 1:24,000 | 1949 | 1946 (aerial photographs 1946, field check 1947) | pink tint | as published (fit 3 m, RMS 5 m) | [293623](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Oakland%20West_293623_1949_24000_geo.pdf) |
| `richmond1947` | Richmond | 1:24,000 | 1947 | 1946 (aerial photographs 1946, field check 1947) | pink tint | as published (fit 4 m, RMS 4 m) | [294667](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Richmond_294667_1947_24000_geo.pdf) |
| `sanleandro1947` | San Leandro | 1:24,000 | 1947 | 1946 (1947 edition (photos c. 1946)) | pink tint | as published (fit 2 m, RMS 5 m) | [300122](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_San%20Leandro_300122_1947_24000_geo.pdf) |
| `milpitas1953` | Milpitas | 1:24,000 | 1953 | 1948 (aerial photographs 1948, survey 1953) | pink tint | 6 m (affine, 6/13 windows, RMS 5 m) | [292969](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Milpitas_292969_1953_24000_geo.pdf) |
| `sanjoseeast1953` | San Jose East | 1:24,000 | 1953 | 1948 (aerial photographs 1948, survey 1953) | pink tint | as published (fit 6 m, RMS 4 m) | [300099](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_San%20Jose%20East_300099_1953_24000_geo.pdf) |
| `sanjosewest1953` | San Jose West | 1:24,000 | 1953 | 1948 (aerial photographs 1948, survey 1953) | pink tint | as published (fit 2 m, RMS 5 m) | [300105](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_San%20Jose%20West_300105_1953_24000_geo.pdf) |
<!-- /maps -->

## Per-town notes

**Oakland.** 1894 = San Francisco 1895 (west of 122°15') + Concord 1897 (east of it; both surveyed
1893-94) + Haywards 1899 (south of 37°45', surveyed 1896). 1914 = the 1915 editions (culture revised
1913-14) + Hayward 1915 (surveyed 1914). 1939 = Concord 1942 + Hayward 1942 (1939 photographs): **east
and south parts only** (no 1940s 1:62,500 edition of the San Francisco quadrangle exists). 1946 =
Oakland West 1949, Oakland East 1947, San Leandro 1947 (1946 photographs). Lakeside / Uptown
(Broadway to the lake, 14th St to Grand Ave), which the live map showed half empty in 1910, is
75 % built up on the 1914 map (49 % in 1894; the rest is the lakeshore park strip and a few blocks
around Grand Ave); the 1912 Sanborn blocks of West Oakland and downtown are 89-97 % inside.

## Limits

* **Generalisation.** At 1:62,500 a house square is ~30 m across and rows are drawn as bands, so the
  share is a reading of the cartographer's generalisation, not a count of lots. Partly built blocks
  near the threshold flip with ±0.1 of the threshold (see sensitivity).
* **Lettering and symbols near streets** (big place names, the city name across downtown) still count
  as ink; railway yards and industrial plants read as built up (they are built, but not with houses).
* **Alignment** RMS 15-25 m on the early sheets; a block's band can fall in its neighbour where the
  survey is locally distorted (the 1890s East Oakland hills).
* **Missing dates.** No c. 1878-80 snapshot: no georeferenceable map of that time draws buildings (the
  Thompson & West 1878 Alameda County atlas draws subdivisions and owners, not houses — checked on its
  map 16, Berkeley / North Oakland, David Rumsey Map Collection); the 1857 Coast Survey chart of
  Oakland is too early. No c. 1929-31 snapshot: the 1920s-30s imprints of the topographic sheets are
  reprints of the 1914-15 plates (the 1929 San Francisco reprint checked), the next survey generation
  is the 1937-40 aerial photographs. Sanborn key maps (LOC: Oakland 1925-29 vols. 4-8) could give a
  coverage proxy for parts of Oakland; not done.
* **Survey vs. edition.** San José's earliest sheet is the 1939 reprint of the 1889 edition (survey
  1885; reprints of an unchanged plate). The `year` of a 1:24,000 sheet is its photo year; the field
  check is 1-5 years later.
