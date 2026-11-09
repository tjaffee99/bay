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
<!-- /snapshots -->

### Probes and threshold sensitivity

<!-- probes -->
<!-- /probes -->

## Maps used

<!-- maps -->
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
