# Built-up extents of the region's older towns, from USGS historical topographic maps

Where each older town of the five modelled counties was **built up** at the date of a real, dated map:
the region's counterpart of San Francisco's `sf_extent_<year>.csv` (decision 14, `../sf_extent_README.md`).
"Built up" means street blocks substantially covered with buildings, as the map draws them; a block
that was merely platted (streets laid out, a few houses) is not built up.

Every snapshot is read from one survey generation of the USGS topographic quadrangles (public domain,
`SOURCES.md` → `region_extents`); nothing is interpolated and nothing is generated. Built by
`tools/extents.py` (`python -I tools/extents.py all <town>`, then `python -I tools/extents.py report x`
for the tables below; caches in `data/interim/region_extents/`, scans in `data/raw/region_extents/`).

**Ten-county extent (2026-11).** 24 more towns in Sonoma, Napa, Solano, Santa Cruz, east Contra Costa and south
Santa Clara counties were added with the same tool (60 more sheets) and, for the years before the first usable
survey, with a second real source: the colour key maps on the index sheets of the Sanborn fire insurance volumes
of 1904-1919 (Library of Congress, public domain; `tools/sanborn_key.py`, ten towns). What differs from the twelve
core towns is in the section *Ten-county towns* below; the tables hold all 36 towns.

## Files

| file | content |
|---|---|
| `<town>_<year>.geojson` | one Feature, a (Multi)Polygon (EPSG:4326), `kind = built_up`: the built-up area at `year` |
| `<town>_<year>_partial.geojson` | one Feature, `kind = partly_built`: blocks with some houses drawn (frontage share 0.12-0.35, about 3-4 houses or more on a block) that are **not** in the built-up file. Optional for the consumer (sparser era fabric); not part of the extent |
| `coverage.geojson` | one Feature per town and snapshot: the area that snapshot **read** (the sheets' quadrangles × the town × the processing box). Outside it a snapshot says nothing (e.g. `oakland_1939` covers only Oakland east of 122°15' W and south of 37°45' N) |
| `check/<town>.png` | the snapshots in sequence: each pixel coloured by the first snapshot whose extent holds it (dark red → light); dashed: area read; black dots: buildings standing today that predate the map |
| `tools/extents.py` | the whole method (render, alignment, blocks, classification, checks, these tables) |
| `tools/sanborn_key.py` | snapshots from Sanborn index key maps (`python -I tools/sanborn_key.py <town>_<year>`; control points and LOC items in its `CFG`) |
| `tools/tsheet_houses.py` | buildings and the snapshot of a Coast Survey plane-table sheet that draws every house (`python -I tools/tsheet_houses.py oakland_1856`) |

Properties of a snapshot feature: `town`, `year` (what the map shows: the survey year, the year of
the culture revision, or the year of the aerial photographs the map was compiled from), `kind`,
`source` (`usgs_htmc:<sheet key>` joined with `+`; sheet keys in the maps table below), `source_url`
(the GeoPDFs, space-separated), `confidence` (`high` / `medium` / `low`), `note` (town-specific
caveats; per sheet: edition, survey / revision / photo years; the area read), `edition_years`,
`map_years`, `method`, `area_km2`, `n_blocks`. Ten-county towns also carry `area_read_km2` (this map alone) and
`nested_from` (the earlier snapshot years included in the polygon, see *Nesting*); a Sanborn snapshot has
`source = loc_sanborn:<LOC item>:index+usgs_htmc:<confirming sheet>`.

Towns (`town` = today's TIGER 2024 places merged): `oakland` (Oakland, Emeryville, Piedmont),
`berkeley` (Berkeley, Albany), `alameda`, `san_jose` (San José, Santa Clara), `san_leandro`, `hayward`,
`richmond` (Richmond, El Cerrito, San Pablo), `palo_alto` (incl. Mayfield), `redwood_city`,
`san_mateo` (San Mateo, Burlingame), `san_rafael`, `martinez`. Each is processed inside a box around
its historic core and its growth to c. 1950 (`TOWNS[...]["bbox"]` in the tool), clipped to today's
land (TIGER area water removed). Ten-county towns: `santa_rosa`, `petaluma`, `napa`, `vallejo`, `santa_cruz`,
`watsonville`, `benicia`, `sonoma`, `healdsburg`, `sebastopol`, `st_helena`, `calistoga`, `fairfield` (Fairfield,
Suisun City), `vacaville`, `dixon`, `rio_vista`, `gilroy`, `morgan_hill`, `antioch`, `pittsburg`, `brentwood`,
`cloverdale`, `capitola` (Capitola, Soquel), `boulder_creek` (Boulder Creek, Felton, Ben Lomond, Brookdale).

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
   cell needs share ≥ 0.35, ≥ 20 % heavy ink (a rail line or two is not built-up) and ≥ 0.3 ha (the
   slivers of cells along a road hold nothing but its casing); units narrower than ~20 m (strips
   between a road and a parallel road or the city limit) are not read on their own. **Partly built:**
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

## Ten-county towns (2026-11): what differs

* **Nesting.** The files of these 24 towns are cumulative: each polygon is its own reading plus every earlier
  snapshot inside its area read (`python -I tools/extents.py nest <town>`, run last), so a later extent contains the
  earlier ones. A town does not un-build between two maps; the independent readings differ by threshold, alignment
  and drawing style (first surveys draw a small town house by house, see *How to use it*). No clearance falls
  between two snapshots of these towns: Santa Rosa's snapshots are 1904 (before the earthquake of 18 April 1906:
  its buildings in the destroyed business district ended then) and 1914 (the rebuilt town); Santa Cruz's first
  snapshot (1899) is after the fire of 1894 and its last (1952) before the 1989 earthquake; Vallejo's last (1948)
  is before the Marina Vista clearance of the 1960s and still holds the old lower Georgia Street district. The
  tables below (areas, pre-map buildings, "prev. snapshot kept") describe each **reading alone** (`check` is run
  before `nest`); the twelve core towns keep their independent readings.
* **Line weight.** The editions of 1915-45 (and Napa 1902) draw streets as single lines or casings of 0.15-0.2 mm,
  heavier than on the 1890s surveys: with the 0.15 mm opening every platted block read as a built front (Fairfield
  1915: 1.2 km² of orchard roads; Sonoma 1939: 2.0 km²). These sheets are read with `open_mm = 0.26` (only ink
  at least a block front thick counts); the first surveys of 1906-14 and the 1:24,000 sheets keep 0.15.
* **1:125,000 sheets** (Napa 1902 and Santa Cruz 1902, both surveyed to 1899): block fronts and houses are
  strongly generalised, alignment RMS 15-25 m: `low` confidence. Santa Cruz 1902 runs over its south neat line to
  36°56' N to hold the city and is read there. Where the reading passed nothing (Sonoma, St. Helena) or did not
  align (the San Lorenzo valley: Boulder Creek, Felton) no 1899 snapshot is given.
* **Tint.** On scans with a reddish cast (Dixon 1952, Elmira 1953: paper R - G 12-14) the pink tint must stand 8
  above the paper; the Elmira scan still reads isolated cells as tint, so parts under 12 ha are dropped at
  Vacaville 1949 (`min_ha` per snapshot; also 15 ha at Santa Rosa 1914 for the lettering SANTA ROSA).
* **Alignment.** Mountain quadrangles have too few streets for the windowed fit: 8 agreeing windows are accepted
  (Santa Cruz 1902), then one window over the town; Hopland 1938 (Cloverdale 1922) fits neither and is read as
  published (`low`).
* **Sheets looked at and not used:** Petaluma 1942 (1937 photographs) and Mare Island 1942 (1937 survey) draw the
  towns as streets without buildings (like Carquinez 1942); Mt. Vaca 1921 reads only road ink north of Fairfield;
  Byron 1916 passes no block at Brentwood; Morgan Hill 1941 passes nothing at Morgan Hill.
* **Sanborn key maps** (`tools/sanborn_key.py`). The index sheet of a Sanborn volume carries a key map of the
  town with every sheet laid over the street grid as a colour patch: the area Sanborn surveyed at 50 ft to the inch,
  i.e. the blocks holding insurable buildings (also thinly built "special" blocks: a college, a race track). The
  half-size scan is registered to today's streets by an affine fit on 8-14 street intersections read on the map and
  looked up by street name in today's centrelines; a block of today is *mapped* when half of it lies under a patch;
  the snapshot keeps the mapped blocks that a USGS survey confirms as built up or partly built (the next survey
  where it follows within ten years; otherwise the survey named below **or** three buildings standing on the block
  today that predate the Sanborn survey, by assessor year - for those towns the "pre-map buildings inside" figure
  is partly circular). Mapped blocks that are not confirmed are the `_partial` file. Registration worse than 12 m
  RMS is `low` confidence.

| town | year | LOC volume (index sheet) | intersections, RMS | mapped km² | kept km² | confirmed on |
|---|---|---|---|---|---|---|
| santa_rosa | 1904 | [Santa Rosa, Dec. 1904](https://www.loc.gov/item/sanborn00838_004/) | 9, 6 m | 4.02 | 1.92 | USGS 1914 |
| petaluma | 1910 | [Petaluma, Nov. 1910](https://www.loc.gov/item/sanborn00756_005/) | 14, 7 m | 2.93 | 2.14 | USGS 1912 |
| santa_cruz | 1905 | [Santa Cruz, 1905](https://www.loc.gov/item/sanborn00833_004/) | 7 of 11, 13 m | 7.0 | 2.97 | USGS 1899 or standing buildings |
| napa | 1910 | [Napa, Oct. 1910](https://www.loc.gov/item/sanborn00707_004/) | 9, 11 m | 3.16 | 2.82 | USGS 1899 or standing buildings |
| vallejo | 1919 | [Vallejo, Mar. 1919](https://www.loc.gov/item/sanborn00905_004/) | 12, 3 m | 4.44 | 3.13 | USGS 1914 or standing buildings |
| watsonville | 1908 | [Watsonville, Jul. 1908](https://www.loc.gov/item/sanborn00921_005/) | 11, 18 m | 2.36 | 1.83 | USGS 1915 |
| gilroy | 1906 | [Gilroy, Oct. 1906](https://www.loc.gov/item/sanborn00566_003/) | 14, 3 m | 1.39 | 0.92 | USGS 1915 |
| benicia | 1913 | [Benicia, Aug. 1913](https://www.loc.gov/item/sanborn00417_004/) | 14, 11 m | 1.64 | 1.02 | USGS 1896 or standing buildings |
| st_helena | 1910 | [Saint Helena, Nov. 1910](https://www.loc.gov/item/sanborn00800_004/) | 14, 19 m | 1.46 | 0.77 | USGS 1942 or standing buildings |
| sebastopol | 1911 | [Sebastopol, Apr. 1911](https://www.loc.gov/item/sanborn00847_006/) | 8, 14 m | 0.64 | 0.54 | USGS 1935 or standing buildings |

  Not done: Antioch 1912 (its key map names the streets Rattan, Knapp, Boobar, Galloway ...; today's are letters
  and numbers and the correspondence was not verified), Healdsburg (LOC has only the 1941 volume online), Calistoga
  1910 and Sonoma 1905 / 1911 (2-4 sheets, no usable key map), the volumes of the 1920s (Petaluma 1923, Napa 1924,
  Watsonville 1920, Antioch 1926, Gilroy 1926, Santa Cruz 1928: not looked at), and the towns without a volume
  checked (Vacaville, Dixon, Fairfield - Suisun, Rio Vista, Pittsburg, Brentwood, Morgan Hill, Cloverdale, Capitola,
  Boulder Creek).
* **Gaps that remain.** Two snapshots only: Antioch and Pittsburg (1907, 1949: no 15' edition between), Rio Vista
  (1908, 1949), Sonoma (1939, 1948), Brentwood (1940, 1949), Morgan Hill (1915, 1953); one: Boulder Creek - Felton
  (1953). Where the first snapshot is late the consumer's 25-year rule starts the town too late (Sonoma, Brentwood,
  Boulder Creek). Between a 1905-14 snapshot and the 1949-53 sheets (Petaluma, Santa Cruz, Antioch, Pittsburg,
  Vallejo west of 122°15') a block is only known to have been built "between the two"; the wartime camps and
  housing of Pittsburg (Camp Stoneman 1942) and Vallejo are inside the 1948-49 extents and need researched dates.

## Oakland before 1890 (2026-11): the 1856 Coast Survey sheet and the 1889 Sanborn key map

The first snapshot of Oakland used to be the USGS survey of 1892-94, and a town's dates before its first snapshot
were spread over the 25 years before it: Oakland began in 1869 and held 68 buildings in 1870, when the census
counted 10,500 people (owner: "Oakland isn't built up early enough I think. Look at older maps"). Two older maps
that show buildings are now read, and the dating between snapshots follows the census (below).

| file | what | source |
|---|---|---|
| `../tsheets/oakland_1856.geojson` | 564 buildings (67,100 m2 of roof), one polygon each | U.S. Coast Survey, *San Francisco Bay, California, Plane-Table Sheet No. XXIV*, Register No. 592, 1:10,000, 1856 (A. D. Bache, Superintendent). NOAA Historical Map & Chart Collection, https://historicalcharts.noaa.gov/search.php, file `T00592-00-1856` (15,656 x 9,413 px, 300 dpi = 0.85 m per pixel); public domain |
| `oakland_1856.geojson` | `kind = buildings`: those houses grown by 12 m (0.51 km2); coverage 44.5 km2 = the sheet's land inside Oakland, Emeryville and Piedmont | same |
| `oakland_1889.geojson`, `_partial` | 370 blocks, 4.49 km2 (Sanborn surveyed 728 blocks, 6.4 km2; kept where the 1894 survey reads the block as built); coverage = the extent itself | Sanborn Map & Publishing Co., *Insurance Maps of Oakland, California, Volume One*, 1889 (copyright deposit 24 Oct 1889; 73 images), key map on two pages. Library of Congress, https://www.loc.gov/item/sanborn00727_001/; public domain |

**T-592** (`tools/tsheet_houses.py oakland_1856`) draws Oakland (the Kellersberger grid from the estuary to about
14th Street, scattered houses to Oakland Point and along the San Pablo and Telegraph roads), Clinton and San Antonio
(Brooklyn) house by house: solid black blocks, dashed fence lines, clover signs for the oaks.
* *Georeference.* The sheet carries the graticule of the old "North American datum" as blue crosses and, at
  122 15' / 37 47', a pencil tick "N.A. (1927) approx. F.B.K. 1933" 47 px west of the cross. An affine through four
  crosses fits to under 2 m; shifted by the tick it gives NAD27, then WGS84 by PROJ. Check on today's street grid of
  downtown (the 1853 grid survives): the share of building ink falling on a 16 m band along today's street centrelines
  is lowest (5.5 %, against 7.8 % unshifted) with a further shift of 6 m west and 2 m south, which is applied. Outlines
  are good to about 10 m.
* *Reading.* Black ink, opened by 5 px so line work drops out; a block is a building when it is compact (short side
  >= 6 m, aspect <= 4, fill >= 0.5), black and not the brown of the sheet's foxing, and stands free of long line work
  (or is large: a shed touching the shoreline). Dropped: rows of dashes, lettering (the letters of OAKLAND and
  BROOKLYN, road and creek names - by position, listed in the tool), marks in hatched marsh, anything on tide flat,
  marsh or water of the c.1800 cover. Reviewed against the sheet tile by tile; the smallest sheds and a few houses
  fused with fence or shore lines are missed (perhaps one in ten).
* *Use* (`region_predecessors.tsheet_buildings`): a house stands from a year between 1851 and 1856 (it is on the
  sheet: `estimated`) until the first building of today on its ground or a clearance, else for a frame-house
  lifetime (ESTIMATED: gone 10-32 years after the survey inside the 1889 extent, 16-46 years outside); one or two
  storeys. A snapshot of `kind = buildings` is exact: a lot without one of its buildings was empty that year.

**Sanborn 1889** (`tools/sanborn_key.py oakland_1889`): the two pages are stitched (the right page repeats 97 px of
the left), registered on 24 street intersections (RMS 10 m), and the washes are read in CIELAB against the measured
paper colour because the atlas is tan and water-stained (stained margins are masked in the tool's `holes`). Volume
One covers Oakland west of Lake Merritt; the coloured sheets are the close-built town from the estuary to about
19th-24th Street and the railroad quarter at Oakland Point. The house blocks of West Oakland between them were not
surveyed, so the snapshot's coverage is its own extent: outside it, it says nothing. Volume Two (East Oakland) is
not among the Library of Congress scans.

**Looked at and not used** (they show no buildings later than 1856): Coast Survey chart 621 *Entrance to San
Francisco Bay*, edition of 1877 (`621-10-1877`: Oakland is still the 1856 topography, only the railroads and
wharves are new); T-1625 *Oakland and Alameda, including wharves, roads and railroads*, supplementary topography of
1881-82, and chart 5581 *San Francisco Harbor*, 1884 (the street plat only: "heavy lines indicate streets actually
surveyed"); Thompson & West, *Official and Historical Atlas Map of Alameda County*, 1878, ward maps (David Rumsey:
lots and tracts, no buildings). No map with buildings was found between 1856 and 1889.

**Dating between snapshots** (`region_predecessors.TownGrowth`, all towns): a spot is unbuilt on the last earlier
map that covers it and built on the first that shows it. Inside that bracket the buildings now go up in step with the
town's census population (`data/tables/population_places.csv`, read between the counts) and in the order of a growth
front - the blocks nearest the town of the earlier snapshots first, whole blocks together, with ~90 m of noise. The
bracket before a town's first snapshot starts when the town did (`data/tables/town_since.csv`: Oakland 1850, Palo
Alto 1889; else 8 years before its first census count, never later than 25 years before the snapshot). A Sanborn-
traced building standing on a town's first traced map starts between the year its spot was first built on and five
years before the map: a frame house mostly early (it is usually the first building), a masonry or large one anywhere
in between. All `procedural` / `estimated`; the order inside 1856-1889 is the model, not a map.

**Not done:** tracing the 73 sheets of the 1889 volume (the real footprints of the 1889 town); the Encinal
(Alameda) half of T-592; the other 1850s plane-table sheets (San Francisco, the Contra Costa shore) read the same way.

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
| oakland | 1894 | sf1895, concord1897, haywards1899 | 10.93 | 9.23 | 134.7 | medium | 81.6% (91.6%) (2362) |  |  |
| oakland | 1914 | sf1915, concord1915, hayward1915 | 27.86 | 14.03 | 134.7 | medium | 81.8% (93.2%) (23290) | 90.6% | downtown 1912: 97% of 30 / 100% of 2; west 1912: 84% of 71 / 8% of 12 |
| oakland | 1939 | concord1942, hayward1942 | 41.76 | 3.62 | 89.19 | medium | 91.5% (93.2%) (53785) | 95.2% |  |
| oakland | 1946 | oaklandwest1949, oaklandeast1947, sanleandro1947 | 71.77 | 5.61 | 134.7 | high | 95.7% (96.8%) (86788) | 93.4% | downtown 1951: 100% of 28 / 33% of 3; west 1951: 100% of 69 / 82% of 17 |
| berkeley | 1894 | sf1895, concord1897 | 4.57 | 4.65 | 41.57 | medium | 62.5% (84.7%) (275) |  |  |
| berkeley | 1914 | sf1915, concord1915 | 11.76 | 5.75 | 41.57 | medium | 87.7% (96.7%) (7619) | 83.7% | downtown 1911: 82% of 17 / 0% of 6; southside 1911: 73% of 30 / 0% of 5; west 1911: 22% of 9 / 3% of 30 |
| berkeley | 1946 | richmond1947, oaklandwest1949, briones1947, oaklandeast1947 | 25.07 | 0.89 | 41.57 | high | 99.3% (99.7%) (30117) | 98.6% |  |
| alameda | 1894 | sf1895, concord1897 | 4.01 | 1.69 | 35.67 | medium | 75.7% (89.2%) (967) |  | westend 1897: 100% of 3 / 10% of 30 |
| alameda | 1914 | sf1915, concord1915 | 5.27 | 1.42 | 35.67 | medium | 87.1% (95.4%) (5936) | 86.0% |  |
| alameda | 1946 | oaklandwest1949, oaklandeast1947 | 9.75 | 1.18 | 35.67 | high | 97.6% (98.3%) (12359) | 98.0% | westend 1948: 100% of 22 / 67% of 15 |
| san_jose | 1885 | sanjose1889 | 5.56 | 9.5 | 184.6 | medium | 55.8% (71.4%) (154) |  |  |
| san_jose | 1895 | sanjose1897 | 6.55 | 10.6 | 184.6 | medium | 54.9% (75.1%) (410) | 93.4% |  |
| san_jose | 1939 | sanjose1943 | 32.68 | 8.73 | 184.6 | medium | 92.2% (94.0%) (22224) | 88.3% |  |
| san_jose | 1948 | sanjosewest1953, sanjoseeast1953, milpitas1953 | 46.34 | 6.8 | 173.96 | high | 94.5% (96.6%) (28845) | 91.4% | jose_downtown 1950: 100% of 92 / 67% of 18 |
| san_leandro | 1896 | haywards1899 | 0.61 | 1.24 | 39.77 | low | 14.1% (42.3%) (78) |  |  |
| san_leandro | 1914 | hayward1915 | 1.17 | 2.37 | 39.77 | low | 24.3% (54.5%) (547) | 81.4% |  |
| san_leandro | 1939 | hayward1942 | 5.79 | 0.61 | 39.77 | medium | 90.1% (91.1%) (4853) | 70.4% |  |
| san_leandro | 1946 | sanleandro1947, hayward1947 | 8.58 | 1.93 | 39.77 | high | 94.4% (97.2%) (9993) | 94.0% |  |
| hayward | 1896 | haywards1899 | 0.6 | 1.7 | 77.54 | low | 6.1% (38.8%) (49) |  |  |
| hayward | 1914 | hayward1915 | 0.93 | 2.07 | 77.54 | low | 21.1% (42.4%) (399) | 98.5% |  |
| hayward | 1939 | hayward1942 | 4.26 | 1.88 | 77.54 | medium | 57.0% (62.5%) (2471) | 71.4% |  |
| hayward | 1946 | hayward1947, sanleandro1947, newark1947 | 5.02 | 3.99 | 73.86 | medium | 70.4% (85.0%) (3677) | 76.5% |  |
| richmond | 1894 | sf1895 | 0.63 | 1.81 | 99.16 | low | 0.0% (7.7%) (13) |  |  |
| richmond | 1914 | sf1915 | 3.74 | 4.67 | 99.16 | medium | 58.3% (79.0%) (2031) | 23.3% | downtown 1916: 100% of 9 / 9% of 11 |
| richmond | 1946 | richmond1947, sanquentin1948 | 27.06 | 3.24 | 99.16 | high | 95.3% (96.5%) (19638) | 88.1% |  |
| palo_alto | 1895 | paloalto1899 | 0.45 | 1.67 | 32.33 | low | 6.5% (45.2%) (31) |  | alto_downtown 1901: 75% of 4 / 0% of 7 |
| palo_alto | 1940 | paloalto1943 | 6.88 | 0.87 | 32.33 | medium | 83.4% (86.2%) (4962) | 70.3% |  |
| palo_alto | 1948 | paloalto1953, mountainview1953 | 12.91 | 1.26 | 32.33 | high | 95.7% (96.2%) (6476) | 91.9% |  |
| redwood_city | 1895 | paloalto1899 | 0.37 | 0.65 | 18.99 | low | 56.8% (73.0%) (37) |  |  |
| redwood_city | 1940 | paloalto1943 | 8.55 | 0.55 | 18.99 | medium | 93.1% (96.9%) (3470) | 97.3% |  |
| redwood_city | 1948 | paloalto1953, woodside1953, redwoodpoint1948 | 13.15 | 0.84 | 27.78 | high | 97.3% (98.3%) (6342) | 93.8% |  |
| san_mateo | 1892 | sanmateo1896 | 0.61 | 1.41 | 51.63 | low | 13.0% (26.1%) (23) |  |  |
| san_mateo | 1914 | sanmateo1915 | 0.44 | 1.82 | 51.63 | low | 3.1% (20.1%) (1574) | 11.3% | mateo_downtown 1908: 58% of 12 / 0% of 9; mateo_downtown 1920: 57% of 14 / 0% of 12 |
| san_mateo | 1939 | sanmateo1943 | 12.5 | 1.24 | 51.63 | medium | 93.3% (96.4%) (9751) | 64.2% |  |
| san_mateo | 1946 | sanmateo1947 | 16.97 | 1.02 | 48.74 | high | 98.9% (99.3%) (12730) | 97.2% |  |
| san_rafael | 1895 | tamalpais1897, sf1895 | 1.8 | 1.6 | 27.03 | medium | 58.4% (75.2%) (125) |  |  |
| san_rafael | 1939 | tamalpais1941 | 1.98 | 1.4 | 18.56 | medium | 60.0% (74.3%) (2362) | 57.5% |  |
| san_rafael | 1952 | sanrafael1954, sanquentin1948 | 5.85 | 1.63 | 27.03 | high | 88.5% (93.9%) (4540) | 94.5% |  |
| martinez | 1896 | karquines1898 | 0.19 | 0.54 | 10.31 | low | 15.7% (76.5%) (51) |  |  |
| martinez | 1940 | carquinezstrait1940 | 1.33 | 0.71 | 10.31 | medium | 75.8% (87.4%) (1677) | 69.5% |  |
| martinez | 1948 | benicia1950, briones1947, portchicago1951 | 2.62 | 0.96 | 12.32 | high | 89.1% (95.7%) (2245) | 93.4% |  |
| santa_rosa | 1904 | Sanborn key map (LOC), santa_rosa_1904 | 1.92 | 1.89 | 7.4 | medium | 54.1% (82.8%) (518) |  |  |
| santa_rosa | 1914 | santarosa1916 | 0.44 | 2.58 | 49.4 | low | 2.9% (40.7%) (1316) | 15.1% |  |
| santa_rosa | 1942 | santarosa1944 | 3.36 | 3.68 | 49.4 | medium | 52.1% (74.8%) (5252) | 65.1% |  |
| santa_rosa | 1952 | santarosa1954 | 11.73 | 3.81 | 49.4 | high | 81.7% (88.9%) (9688) | 92.5% |  |
| petaluma | 1910 | Sanborn key map (LOC), petaluma_1910 | 2.14 | 0.69 | 6.03 | medium | 78.3% (90.0%) (1551) |  |  |
| petaluma | 1912 | petaluma1914 | 1.0 | 0.73 | 21.68 | low | 30.4% (37.1%) (1686) | 38.4% |  |
| petaluma | 1952 | petaluma1953, petalumacreek1954 | 4.6 | 1.07 | 21.68 | high | 87.3% (94.0%) (4813) | 85.1% |  |
| napa | 1899 | napa1902 | 1.96 | 1.57 | 32.58 | low | 67.7% (79.0%) (718) |  |  |
| napa | 1910 | Sanborn key map (LOC), napa_1910 | 2.82 | 0.27 | 6.92 | medium | 91.8% (92.4%) (1338) | 96.0% |  |
| napa | 1939 | sonoma1942 | 3.18 | 1.78 | 32.58 | medium | 70.0% (81.0%) (3632) | 76.6% |  |
| napa | 1948 | napa1951 | 6.01 | 3.32 | 32.58 | high | 83.4% (91.1%) (6020) | 91.9% |  |
| vallejo | 1899 | napa1902 | 0.77 | 1.95 | 64.93 | low | 29.2% (69.7%) (449) |  |  |
| vallejo | 1914 | mareisland1916 | 1.78 | 0.85 | 28.56 | medium | 86.9% (97.1%) (852) | 88.4% |  |
| vallejo | 1919 | Sanborn key map (LOC), vallejo_1919 | 3.13 | 1.18 | 16.6 | medium | 93.2% (94.6%) (1892) | 88.0% |  |
| vallejo | 1940 | carquinezstrait1940 | 4.01 | 1.97 | 36.37 | medium | 88.9% (93.7%) (3174) | 97.5% |  |
| vallejo | 1948 | mareisland1949, benicia1950 | 14.93 | 0.54 | 49.16 | high | 90.0% (91.5%) (9252) | 98.1% |  |
| santa_cruz | 1899 | santacruz1902 | 0.34 | 1.34 | 34.95 | low | 13.9% (43.3%) (647) |  |  |
| santa_cruz | 1905 | Sanborn key map (LOC), santa_cruz_1905 | 2.97 | 3.76 | 15.58 | low | 78.0% (89.7%) (891) | 98.9% |  |
| santa_cruz | 1952 | santacruz1954, soquel1954 | 12.14 | 1.29 | 35.6 | high | 94.7% (96.6%) (8793) | 97.8% |  |
| watsonville | 1908 | Sanborn key map (LOC), watsonville_1908 | 1.83 | 0.37 | 4.29 | low | 88.1% (92.0%) (553) |  |  |
| watsonville | 1915 | capitola1914, sanjuanbautista1917 | 1.43 | 1.12 | 16.89 | medium | 67.1% (79.8%) (1006) | 72.8% |  |
| watsonville | 1939 | capitola1940, sanjuanbautista1940 | 2.44 | 1.1 | 16.89 | medium | 75.6% (85.9%) (3459) | 91.6% |  |
| watsonville | 1952 | watsonvillewest1954, watsonvilleeast1955 | 4.23 | 1.08 | 16.89 | high | 89.5% (95.2%) (5155) | 91.9% |  |
| benicia | 1896 | karquines1898 | 0.24 | 0.78 | 25.05 | low | 19.8% (69.8%) (106) |  |  |
| benicia | 1913 | Sanborn key map (LOC), benicia_1913 | 1.02 | 0.5 | 5.19 | medium | 90.5% (91.3%) (242) | 99.9% |  |
| benicia | 1940 | carquinezstrait1940 | 1.27 | 0.73 | 25.05 | medium | 77.8% (85.7%) (477) | 82.3% |  |
| benicia | 1948 | benicia1950 | 3.64 | 0.3 | 23.53 | high | 87.6% (88.8%) (1276) | 82.6% |  |
| sonoma | 1939 | sonoma1942 | 0.76 | 0.89 | 7.09 | medium | 51.0% (72.2%) (641) |  |  |
| sonoma | 1948 | sonoma1951 | 0.68 | 1.38 | 7.09 | medium | 44.1% (78.7%) (848) | 49.4% |  |
| healdsburg | 1915 | healdsburg1920 | 0.5 | 0.82 | 9.28 | low | 24.3% (48.2%) (552) |  |  |
| healdsburg | 1933 | healdsburg1940 | 0.91 | 0.76 | 9.28 | medium | 71.0% (81.2%) (942) | 53.3% |  |
| healdsburg | 1953 | healdsburg1955, guerneville1955 | 1.82 | 0.32 | 6.76 | high | 83.3% (87.8%) (1680) | 98.1% |  |
| sebastopol | 1911 | Sanborn key map (LOC), sebastopol_1911 | 0.54 | 0.04 | 2.03 | low | 73.9% (75.2%) (303) |  |  |
| sebastopol | 1935 | sebastopol1942 | 0.33 | 0.42 | 4.86 | low | 40.7% (73.3%) (742) | 56.6% |  |
| sebastopol | 1952 | sebastopol1954 | 1.19 | 0.7 | 4.86 | high | 70.1% (90.2%) (1283) | 92.7% |  |
| st_helena | 1910 | Sanborn key map (LOC), st_helena_1910 | 0.77 | 0.59 | 6.05 | low | 70.4% (73.2%) (328) |  |  |
| st_helena | 1942 | sonoma1942, sthelena1945 | 0.27 | 0.51 | 12.59 | low | 14.6% (36.4%) (1161) | 23.4% |  |
| st_helena | 1957 | rutherford1951, sthelena1960 | 0.99 | 0.61 | 12.59 | medium | 55.5% (60.7%) (1545) | 59.9% |  |
| calistoga | 1915 | calistoga1927 | 0.26 | 0.38 | 6.72 | low | 44.3% (53.0%) (149) |  |  |
| calistoga | 1943 | calistoga1945 | 0.26 | 0.26 | 6.72 | low | 44.9% (65.8%) (530) | 57.3% |  |
| calistoga | 1957 | calistoga1958 | 0.67 | 0.34 | 6.72 | high | 65.0% (77.2%) (882) | 100.0% |  |
| fairfield | 1896 | karquines1898 | 0.23 | 0.61 | 10.92 | low | 57.1% (96.4%) (28) |  |  |
| fairfield | 1940 | carquinezstrait1940h, mtvaca1942 | 1.1 | 1.72 | 29.3 | medium | 79.8% (86.2%) (356) | 58.3% |  |
| fairfield | 1948 | fairfieldsouth1949, fairfieldnorth1951 | 1.62 | 1.23 | 29.3 | high | 89.5% (95.3%) (571) | 69.4% |  |
| vacaville | 1906 | vacaville1908 | 0.49 | 0.55 | 21.11 | medium | 86.3% (92.2%) (51) |  |  |
| vacaville | 1939 | vacaville1941, mtvaca1942 | 0.48 | 0.51 | 27.02 | medium | 73.8% (83.1%) (195) | 72.4% |  |
| vacaville | 1949 | elmira1953, fairfieldnorth1951 | 2.0 | 1.18 | 24.47 | medium | 87.1% (91.4%) (325) | 87.4% |  |
| dixon | 1906 | vacaville1908 | 0.58 | 0.47 | 11.25 | medium | 84.9% (93.0%) (86) |  |  |
| dixon | 1939 | vacaville1941 | 0.45 | 0.37 | 11.25 | medium | 59.3% (77.0%) (322) | 52.3% |  |
| dixon | 1949 | dixon1952 | 1.19 | 0.13 | 11.25 | high | 87.4% (87.6%) (445) | 100.0% |  |
| rio_vista | 1908 | riovista1910 | 0.11 | 0.23 | 10.01 | low | 48.8% (90.2%) (82) |  |  |
| rio_vista | 1949 | riovista1953 | 0.87 | 0.15 | 10.01 | high | 91.4% (94.9%) (491) | 100.0% |  |
| gilroy | 1906 | Sanborn key map (LOC), gilroy_1906 | 0.92 | 0.4 | 4.57 | medium | 90.4% (94.3%) (335) |  |  |
| gilroy | 1915 | morganhill1917, sanjuanbautista1917 | 0.47 | 1.08 | 25.47 | low | 37.1% (79.8%) (515) | 40.5% |  |
| gilroy | 1939 | morganhill1941, sanjuanbautista1940 | 0.61 | 0.48 | 25.47 | low | 42.6% (50.5%) (1251) | 35.5% |  |
| gilroy | 1953 | gilroy1955, chittenden1955 | 2.14 | 0.63 | 25.47 | high | 80.7% (86.1%) (2025) | 69.1% |  |
| morgan_hill | 1915 | morganhill1917 | 0.08 | 0.88 | 19.1 | low | 13.9% (44.4%) (144) |  |  |
| morgan_hill | 1953 | morganhill1955, mtmadonna1955 | 0.45 | 1.14 | 18.48 | medium | 30.0% (59.1%) (783) | 47.9% |  |
| antioch | 1907 | antioch1908 | 0.33 | 0.56 | 14.5 | low | 8.3% (51.0%) (157) |  |  |
| antioch | 1949 | antiochnorth1953 | 2.99 | 0.46 | 14.5 | high | 89.0% (91.8%) (2537) | 87.5% |  |
| pittsburg | 1907 | antioch1908 | 0.3 | 0.46 | 29.47 | low | 16.7% (66.7%) (6) |  |  |
| pittsburg | 1949 | honkerbay1953, antiochnorth1953 | 5.31 | 0.86 | 29.47 | high | 93.1% (93.8%) (1589) | 100.0% |  |
| brentwood | 1940 | byron1940 | 0.17 | 0.82 | 12.2 | low | 34.6% (69.7%) (188) |  |  |
| brentwood | 1949 | brentwood1954 | 0.26 | 0.57 | 12.2 | medium | 50.8% (82.5%) (315) | 69.1% |  |
| cloverdale | 1922 | hopland1938 | 0.31 | 0.15 | 6.11 | low | 48.8% (64.7%) (252) |  |  |
| cloverdale | 1942 | hopland1944 | 0.28 | 0.32 | 6.11 | low | 39.1% (72.0%) (368) | 36.0% |  |
| cloverdale | 1957 | cloverdale1960 | 1.19 | 0.15 | 6.11 | high | 80.9% (82.8%) (1143) | 100.0% |  |
| capitola | 1912 | capitola1914 | 0.26 | 1.07 | 10.85 | low | 34.3% (71.6%) (67) |  |  |
| capitola | 1938 | capitola1940 | 0.31 | 0.92 | 10.85 | low | 18.7% (51.5%) (503) | 18.1% |  |
| capitola | 1952 | soquel1954 | 1.34 | 0.63 | 10.85 | high | 66.2% (79.8%) (1322) | 51.0% |  |
| boulder_creek | 1953 | felton1955, castlerockridge1955, bigbasin1955 | 1.92 | 3.8 | 47.07 | medium | 31.6% (75.6%) (2704) |  |  |
<!-- /snapshots -->

### Probes and threshold sensitivity

<!-- probes -->
| town | year | probe | share inside |
|---|---|---|---|
| oakland | 1894 | lakeside_uptown | 46.9% |
| oakland | 1894 | west_oakland | 82.7% |
| oakland | 1894 | temescal | 29.9% |
| oakland | 1894 | block km² at share 0.25 / 0.35 / 0.45 | 12.9 / 10.2 / 8.0 |
| oakland | 1914 | lakeside_uptown | 74.8% |
| oakland | 1914 | west_oakland | 90.9% |
| oakland | 1914 | temescal | 79.0% |
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
| santa_rosa | 1914 | block km² at share 0.25 / 0.35 / 0.45 | 1.5 / 0.9 / 0.4 |
| petaluma | 1912 | block km² at share 0.25 / 0.35 / 0.45 | 1.6 / 1.0 / 0.5 |
| napa | 1899 | block km² at share 0.25 / 0.35 / 0.45 | 2.3 / 1.8 / 1.5 |
| vallejo | 1899 | block km² at share 0.25 / 0.35 / 0.45 | 1.2 / 0.8 / 0.4 |
| vallejo | 1914 | block km² at share 0.25 / 0.35 / 0.45 | 1.9 / 1.6 / 1.3 |
| santa_cruz | 1899 | block km² at share 0.25 / 0.35 / 0.45 | 0.7 / 0.3 / 0.1 |
| watsonville | 1915 | block km² at share 0.25 / 0.35 / 0.45 | 1.6 / 1.2 / 1.1 |
| benicia | 1896 | block km² at share 0.25 / 0.35 / 0.45 | 0.3 / 0.2 / 0.1 |
| healdsburg | 1915 | block km² at share 0.25 / 0.35 / 0.45 | 0.6 / 0.4 / 0.3 |
| calistoga | 1915 | block km² at share 0.25 / 0.35 / 0.45 | 0.2 / 0.2 / 0.1 |
| fairfield | 1896 | block km² at share 0.25 / 0.35 / 0.45 | 0.4 / 0.2 / 0.1 |
| vacaville | 1906 | block km² at share 0.25 / 0.35 / 0.45 | 0.5 / 0.4 / 0.3 |
| dixon | 1906 | block km² at share 0.25 / 0.35 / 0.45 | 0.6 / 0.4 / 0.3 |
| rio_vista | 1908 | block km² at share 0.25 / 0.35 / 0.45 | 0.2 / 0.1 / 0.1 |
| gilroy | 1915 | block km² at share 0.25 / 0.35 / 0.45 | 0.8 / 0.4 / 0.3 |
| morgan_hill | 1915 | block km² at share 0.25 / 0.35 / 0.45 | 0.4 / 0.1 / 0.0 |
| antioch | 1907 | block km² at share 0.25 / 0.35 / 0.45 | 0.5 / 0.4 / 0.2 |
| pittsburg | 1907 | block km² at share 0.25 / 0.35 / 0.45 | 0.3 / 0.2 / 0.1 |
| cloverdale | 1922 | block km² at share 0.25 / 0.35 / 0.45 | 0.2 / 0.2 / 0.1 |
| capitola | 1912 | block km² at share 0.25 / 0.35 / 0.45 | 0.3 / 0.1 / 0.1 |
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
| `napa1902` | Napa | 1:125,000 | 1902 | 1899 (1:125,000 30' sheet, surveyed 1896-99 (FGDC: survey year 1899)) | bands + squares | 206 m (affine, 32/141 windows, RMS 24 m) | [299520](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/125000/CA_Napa_299520_1902_125000_geo.pdf) |
| `santacruz1902` | Santa Cruz | 1:125,000 | 1902 | 1899 (1:125,000 30' sheet, surveyed to 1899 (1904 imprint); read over its south edge (the city of Santa Cruz)) | bands + squares | 240 m (affine, 8/40 windows, RMS 15 m) | [299623](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/125000/CA_Santa%20Cruz_299623_1902_125000_geo.pdf) |
| `vacaville1908` | Vacaville | 1:62,500 | 1908 | 1906 (surveyed 1906 (1922 imprint)) | bands + squares | 48 m (affine, 91/111 windows, RMS 14 m) | [299006](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Vacaville_299006_1908_62500_geo.pdf) |
| `antioch1908` | Antioch | 1:62,500 | 1908 | 1907 (surveyed 1907 (1914 imprint)) | bands + squares | 48 m (affine, 5/8 windows, RMS 12 m) | [296718](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Antioch_296718_1908_62500_geo.pdf) |
| `riovista1910` | Rio Vista | 1:31,680 | 1910 | 1908 (1:31,680 sheet, surveyed 1908) | bands + squares | 45 m (affine, 10/13 windows, RMS 10 m) | [296463](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/31680/CA_Rio%20Vista_296463_1910_31680_geo.pdf) |
| `capitola1914` | Capitola | 1:62,500 | 1914 | 1912 (surveyed 1912 (1922 imprint)) | bands + squares | 36 m (affine, 22/26 windows, RMS 17 m) | [297018](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Capitola_297018_1914_62500_geo.pdf) |
| `petaluma1914` | Petaluma | 1:62,500 | 1914 | 1912 (surveyed 1912 (1924 imprint)) | bands + squares | 57 m (affine, 24/31 windows, RMS 19 m) | [298524](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Petaluma_298524_1914_62500_geo.pdf) |
| `concord1915` | Concord | 1:62,500 | 1915 | 1914 (edition of June 1915: surveyed 1893-94, culture revised in part in 1913-14 (collar note)) | bands + squares | 211 m (affine, 31/62 windows, RMS 16 m) | [297163](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Concord_297163_1915_62500_geo.pdf) |
| `hayward1915` | Hayward | 1:62,500 | 1915 | 1914 (surveyed 1914 (1939 imprint)) | bands + squares | 217 m (affine, 41/68 windows, RMS 18 m) | [297660](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Hayward_297660_1915_62500_geo.pdf) |
| `mareisland1916` | Mare Island | 1:62,500 | 1916 | 1914 (surveyed 1914 (1927 imprint)) | bands + squares | 56 m (affine, 13/17 windows, RMS 8 m) | [298114](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Mare%20Island_298114_1916_62500_geo.pdf) |
| `sanmateo1915` | San Mateo | 1:62,500 | 1915 | 1914 (1915 edition: surveyed 1892, culture revised in part in 1914 (collar note)) | bands + squares | 209 m (affine, 30/37 windows, RMS 8 m) | [298922](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Mateo_298922_1915_62500_geo.pdf) |
| `santarosa1916` | Santa Rosa | 1:62,500 | 1916 | 1914 (surveyed 1914 (1927 imprint)) | bands + squares | 35 m (affine, 17/25 windows, RMS 12 m) | [298960](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Santa%20Rosa_298960_1916_62500_geo.pdf) |
| `sf1915` | San Francisco | 1:62,500 | 1915 | 1914 (1915 edition: surveyed 1892-94, culture revised in 1914 (collar note)) | bands + squares | 223 m (affine, 105/128 windows, RMS 20 m) | [298897](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Francisco_298897_1915_62500_geo.pdf) |
| `calistoga1927` | Calistoga | 1:62,500 | 1927 | 1915 (edition of 1927, surveyed 1915) | bands + squares | 10 m (constant, 4/8 windows, RMS 24 m) | [465409](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Calistoga_465409_1927_62500_geo.pdf) |
| `healdsburg1920` | Healdsburg | 1:62,500 | 1920 | 1915 (edition of 1920, field check 1915) | bands + squares | 60 m (affine, 21/47 windows, RMS 23 m) | [465734](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Healdsburg_465734_1920_62500_geo.pdf) |
| `morganhill1917` | Morgan Hill | 1:62,500 | 1917 | 1915 (surveyed 1915 (1931 imprint)) | bands + squares | 35 m (affine, 90/99 windows, RMS 17 m) | [298244](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Morgan%20Hill_298244_1917_62500_geo.pdf) |
| `sanjuanbautista1917` | San Juan Bautista | 1:62,500 | 1917 | 1915 (surveyed 1915 (1925 imprint)) | bands + squares | 52 m (affine, 75/86 windows, RMS 20 m) | [466314](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Juan%20Bautista_466314_1917_62500_geo.pdf) |
| `hopland1938` | Hopland | 1:62,500 | 1938 | 1922 (edition of 1938: surveyed 1916, field check 1922) | bands + squares | as published | [465760](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Hopland_465760_1938_62500_geo.pdf) |
| `healdsburg1940` | Healdsburg | 1:62,500 | 1940 | 1933 (edition of 1940, surveyed 1933) | grey tint | as published (fit 6 m, RMS 7 m) | [297672](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Healdsburg_297672_1940_62500_geo.pdf) |
| `sebastopol1942` | Sebastopol | 1:62,500 | 1942 | 1935 (edition of 1942, surveyed 1935) | grey tint | as published (fit 6 m, RMS 7 m) | [301668](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Sebastopol_301668_1942_62500_geo.pdf) |
| `capitola1940` | Capitola | 1:62,500 | 1940 | 1938 (aerial photographs 1938) | grey tint | 36 m (affine, 32/82 windows, RMS 6 m) | [465438](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Capitola_465438_1940_62500_geo.pdf) |
| `concord1942` | Concord | 1:62,500 | 1942 | 1939 (aerial photographs 1939) | grey tint | 7 m (affine, 54/187 windows, RMS 7 m) | [465521](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Concord_465521_1942_62500_geo.pdf) |
| `hayward1942` | Hayward | 1:62,500 | 1942 | 1939 (aerial photographs 1939) | grey tint | 17 m (affine, 56/135 windows, RMS 7 m) | [465728](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Hayward_465728_1942_62500_geo.pdf) |
| `morganhill1941` | Morgan Hill | 1:62,500 | 1941 | 1939 (edition of 1941: surveyed 1915, revised 1939 (aerial photographs 1939 on the 1939 edition)) | grey tint | 31 m (affine, 33/93 windows, RMS 7 m) | [465964](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Morgan%20Hill_465964_1941_62500_geo.pdf) |
| `mtvaca1942` | Mt Vaca | 1:62,500 | 1942 | 1939 (aerial photographs 1939) | grey tint | 11 m (affine, 31/58 windows, RMS 8 m) | [466013](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Mt%20Vaca_466013_1942_62500_geo.pdf) |
| `sanjose1943` | San Jose | 1:62,500 | 1943 | 1939 (aerial photographs 1939) | grey tint | 17 m (affine, 73/210 windows, RMS 7 m) | [466308](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Jose_466308_1943_62500_geo.pdf) |
| `sanjuanbautista1940` | San Juan Bautista | 1:62,500 | 1940 | 1939 (aerial photographs 1939) | grey tint | 48 m (affine, 32/128 windows, RMS 8 m) | [466316](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Juan%20Bautista_466316_1940_62500_geo.pdf) |
| `sanmateo1943` | San Mateo | 1:62,500 | 1943 | 1939 (aerial photographs 1939) | grey tint | as published (fit 5 m, RMS 7 m) | [466324](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Mateo_466324_1943_62500_geo.pdf) |
| `sonoma1942` | Sonoma | 1:62,500 | 1942 | 1939 (aerial photographs 1939, survey 1941) | grey tint | 13 m (affine, 32/98 windows, RMS 7 m) | [301738](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Sonoma_301738_1942_62500_geo.pdf) |
| `tamalpais1941` | Tamalpais | 1:62,500 | 1941 | 1939 (aerial photographs 1939) | grey tint | 9 m (affine, 19/64 windows, RMS 8 m) | [301788](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Tamalpais_301788_1941_62500_geo.pdf) |
| `vacaville1941` | Vacaville | 1:62,500 | 1941 | 1939 (aerial photographs 1939) | grey tint | 53 m (affine, 54/134 windows, RMS 7 m) | [466506](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Vacaville_466506_1941_62500_geo.pdf) |
| `byron1940` | Byron | 1:62,500 | 1940 | 1940 (aerial photographs 1940 (1943 imprint)) | grey tint | 8 m (affine, 39/95 windows, RMS 7 m) | [296942](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Byron_296942_1940_62500_geo.pdf) |
| `carquinezstrait1940` | Carquinez Strait | 1:62,500 | 1940 | 1940 (aerial photographs 1940 (1965 imprint)) | grey tint | 8 m (affine, 21/66 windows, RMS 7 m) | [297037](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Carquinez%20Strait_297037_1940_62500_geo.pdf) |
| `carquinezstrait1940h` | Carquinez Strait | 1:62,500 | 1940 | 1940 (aerial photographs 1940 (1965 imprint); read with open_mm 0.26) | grey tint | 8 m (affine, 21/66 windows, RMS 7 m) | [297037](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Carquinez%20Strait_297037_1940_62500_geo.pdf) |
| `paloalto1943` | Palo Alto | 1:62,500 | 1943 | 1940 (aerial photographs 1940) | grey tint | as published (fit 6 m, RMS 8 m) | [298463](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Palo%20Alto_298463_1943_62500_geo.pdf) |
| `hopland1944` | Hopland | 1:62,500 | 1944 | 1942 (aerial photographs 1942) | grey tint | 45 m (constant, 3/6 windows, RMS 7 m) | [465759](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Hopland_465759_1944_62500_geo.pdf) |
| `santarosa1944` | Santa Rosa | 1:62,500 | 1944 | 1942 (edition of 1944: surveyed 1914, revised 1942) | grey tint | 43 m (affine, 49/142 windows, RMS 7 m) | [301627](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Santa%20Rosa_301627_1944_62500_geo.pdf) |
| `sthelena1945` | St Helena | 1:62,500 | 1945 | 1942 (edition of 1945, surveyed 1942) | grey tint | as published (fit 3 m, RMS 6 m) | [466421](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_St%20Helena_466421_1945_62500_geo.pdf) |
| `calistoga1945` | Calistoga | 1:62,500 | 1945 | 1943 (edition of 1945, surveyed 1943) | grey tint | 24 m (affine, 22/29 windows, RMS 6 m) | [296981](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Calistoga_296981_1945_62500_geo.pdf) |
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
| `fairfieldnorth1951` | Fairfield North | 1:24,000 | 1951 | 1948 (aerial photographs 1948, survey 1951) | pink tint | as published (fit 3 m, RMS 4 m) | [290424](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Fairfield%20North_290424_1951_24000_geo.pdf) |
| `fairfieldsouth1949` | Fairfield South | 1:24,000 | 1949 | 1948 (aerial photographs 1948, survey 1949) | pink tint | as published | [290434](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Fairfield%20South_290434_1949_24000_geo.pdf) |
| `mareisland1949` | Mare Island | 1:24,000 | 1949 | 1948 (aerial photographs 1948, survey 1949) | pink tint | as published (fit 6 m, RMS 2 m) | [292723](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Mare%20Island_292723_1949_24000_geo.pdf) |
| `milpitas1953` | Milpitas | 1:24,000 | 1953 | 1948 (aerial photographs 1948, survey 1953) | pink tint | 6 m (affine, 6/13 windows, RMS 5 m) | [292969](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Milpitas_292969_1953_24000_geo.pdf) |
| `mountainview1953` | Mountain View | 1:24,000 | 1953 | 1948 (aerial photographs 1948, survey 1953) | pink tint | as published (fit 4 m, RMS 5 m) | [293234](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Mountain%20View_293234_1953_24000_geo.pdf) |
| `napa1951` | Napa | 1:24,000 | 1951 | 1948 (aerial photographs 1948, survey 1951) | pink tint | as published (fit 3 m, RMS 5 m) | [293422](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Napa_293422_1951_24000_geo.pdf) |
| `paloalto1953` | Palo Alto | 1:24,000 | 1953 | 1948 (aerial photographs 1948, survey 1953) | pink tint | as published (fit 1 m, RMS 4 m) | [293907](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Palo%20Alto_293907_1953_24000_geo.pdf) |
| `portchicago1951` | Port Chicago | 1:24,000 | 1951 | 1948 (aerial photographs 1948, survey 1950) | pink tint | 13 m (affine, 14/22 windows, RMS 8 m) | [294325](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Port%20Chicago_294325_1951_24000_geo.pdf) |
| `redwoodpoint1948` | Redwood Point | 1:24,000 | 1948 | 1948 (1948 edition) | pink tint | as published | [294610](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Redwood%20Point_294610_1948_24000_geo.pdf) |
| `rutherford1951` | Rutherford | 1:24,000 | 1951 | 1948 (aerial photographs 1948, survey 1951) | pink tint | 6 m (affine, 8/9 windows, RMS 5 m) | [294860](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Rutherford_294860_1951_24000_geo.pdf) |
| `sanjoseeast1953` | San Jose East | 1:24,000 | 1953 | 1948 (aerial photographs 1948, survey 1953) | pink tint | as published (fit 6 m, RMS 4 m) | [300099](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_San%20Jose%20East_300099_1953_24000_geo.pdf) |
| `sanjosewest1953` | San Jose West | 1:24,000 | 1953 | 1948 (aerial photographs 1948, survey 1953) | pink tint | as published (fit 2 m, RMS 5 m) | [300105](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_San%20Jose%20West_300105_1953_24000_geo.pdf) |
| `sonoma1951` | Sonoma | 1:24,000 | 1951 | 1948 (aerial photographs 1948, survey 1951) | pink tint | as published (fit 4 m, RMS 4 m) | [300595](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Sonoma_300595_1951_24000_geo.pdf) |
| `woodside1953` | Woodside | 1:24,000 | 1953 | 1948 (aerial photographs 1948, field check 1953) | pink tint | 7 m (affine, 34/34 windows, RMS 4 m) | [301429](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Woodside_301429_1953_24000_geo.pdf) |
| `antiochnorth1953` | Antioch North | 1:24,000 | 1953 | 1949 (aerial photographs 1949, field check 1953) | pink tint | as published (fit 0 m, RMS 4 m) | [288002](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Antioch%20North_288002_1953_24000_geo.pdf) |
| `brentwood1954` | Brentwood | 1:24,000 | 1954 | 1949 (aerial photographs 1949, field check 1954) | pink tint | as published (fit 6 m, RMS 7 m) | [288600](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Brentwood_288600_1954_24000_geo.pdf) |
| `dixon1952` | Dixon | 1:24,000 | 1952 | 1949 (aerial photographs 1949, survey 1952) | pink tint | as published (fit 4 m, RMS 5 m) | [465565](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Dixon_465565_1952_24000_geo.pdf) |
| `elmira1953` | Elmira | 1:24,000 | 1953 | 1949 (aerial photographs 1949, field check 1953) | pink tint | 10 m (affine, 32/38 windows, RMS 5 m) | [303008](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Elmira_303008_1953_24000_geo.pdf) |
| `honkerbay1953` | Honker Bay | 1:24,000 | 1953 | 1949 (aerial photographs 1949, field check 1953) | pink tint | as published (fit 6 m, RMS 8 m) | [291408](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Honker%20Bay_291408_1953_24000_geo.pdf) |
| `riovista1953` | Rio Vista | 1:24,000 | 1953 | 1949 (aerial photographs 1949, survey 1953) | pink tint | as published (fit 4 m, RMS 6 m) | [294705](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Rio%20Vista_294705_1953_24000_geo.pdf) |
| `chittenden1955` | Chittenden | 1:24,000 | 1955 | 1952 (aerial photographs 1952, survey 1955) | pink tint | as published (fit 3 m, RMS 4 m) | [289219](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Chittenden_289219_1955_24000_geo.pdf) |
| `petaluma1953` | Petaluma | 1:24,000 | 1953 | 1952 (aerial photographs 1952, survey 1953) | pink tint | as published (fit 3 m, RMS 3 m) | [294061](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Petaluma_294061_1953_24000_geo.pdf) |
| `petalumacreek1954` | Petaluma Creek | 1:24,000 | 1954 | 1952 (aerial photographs 1952, survey 1954 (the quadrangle later named Petaluma River)) | pink tint | as published (fit 4 m, RMS 4 m) | [466127](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Petaluma%20Creek_466127_1954_24000_geo.pdf) |
| `sanrafael1954` | San Rafael | 1:24,000 | 1954 | 1952 (aerial photographs 1952, field check 1954) | pink tint | as published (fit 5 m, RMS 4 m) | [300201](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_San%20Rafael_300201_1954_24000_geo.pdf) |
| `santacruz1954` | Santa Cruz | 1:24,000 | 1954 | 1952 (aerial photographs 1952, survey 1954) | pink tint | as published (fit 6 m, RMS 3 m) | [300246](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Santa%20Cruz_300246_1954_24000_geo.pdf) |
| `santarosa1954` | Santa Rosa | 1:24,000 | 1954 | 1952 (aerial photographs 1952, survey 1954) | pink tint | as published (fit 5 m, RMS 4 m) | [300294](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Santa%20Rosa_300294_1954_24000_geo.pdf) |
| `sebastopol1954` | Sebastopol | 1:24,000 | 1954 | 1952 (aerial photographs 1952, survey 1954) | pink tint | as published (fit 3 m, RMS 4 m) | [300394](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Sebastopol_300394_1954_24000_geo.pdf) |
| `soquel1954` | Soquel | 1:24,000 | 1954 | 1952 (aerial photographs 1952, survey 1954) | pink tint | 22 m (constant, 3/9 windows, RMS 5 m) | [300606](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Soquel_300606_1954_24000_geo.pdf) |
| `watsonvilleeast1955` | Watsonville East | 1:24,000 | 1955 | 1952 (aerial photographs 1952, survey 1955) | pink tint | as published (fit 3 m, RMS 5 m) | [301243](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Watsonville%20East_301243_1955_24000_geo.pdf) |
| `watsonvillewest1954` | Watsonville West | 1:24,000 | 1954 | 1952 (aerial photographs 1952, survey 1954) | pink tint | as published (fit 5 m, RMS 4 m) | [301247](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Watsonville%20West_301247_1954_24000_geo.pdf) |
| `bigbasin1955` | Big Basin | 1:24,000 | 1955 | 1953 (aerial photographs 1953, field check 1955) | pink tint | as published (fit 2 m, RMS 6 m) | [288374](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Big%20Basin_288374_1955_24000_geo.pdf) |
| `castlerockridge1955` | Castle Rock Ridge | 1:24,000 | 1955 | 1953 (aerial photographs 1953, field check 1955) | pink tint | as published (fit 5 m, RMS 6 m) | [289043](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Castle%20Rock%20Ridge_289043_1955_24000_geo.pdf) |
| `felton1955` | Felton | 1:24,000 | 1955 | 1953 (aerial photographs 1953, field check 1955) | pink tint | as published (fit 6 m, RMS 6 m) | [465668](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Felton_465668_1955_24000_geo.pdf) |
| `gilroy1955` | Gilroy | 1:24,000 | 1955 | 1953 (aerial photographs 1953, survey 1955) | pink tint | as published (fit 5 m, RMS 5 m) | [290814](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Gilroy_290814_1955_24000_geo.pdf) |
| `guerneville1955` | Guerneville | 1:24,000 | 1955 | 1953 (aerial photographs 1953, field check 1955) | pink tint | as published (fit 3 m, RMS 4 m) | [291072](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Guerneville_291072_1955_24000_geo.pdf) |
| `healdsburg1955` | Healdsburg | 1:24,000 | 1955 | 1953 (aerial photographs 1953, field check 1955) | pink tint | 7 m (affine, 43/43 windows, RMS 5 m) | [291252](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Healdsburg_291252_1955_24000_geo.pdf) |
| `morganhill1955` | Morgan Hill | 1:24,000 | 1955 | 1953 (aerial photographs 1953, survey 1955) | pink tint | 34 m (affine, 9/23 windows, RMS 4 m) | [293124](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Morgan%20Hill_293124_1955_24000_geo.pdf) |
| `mtmadonna1955` | Mt Madonna | 1:24,000 | 1955 | 1953 (aerial photographs 1953, survey 1955) | pink tint | as published (fit 0 m, RMS 4 m) | [293330](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Mt%20Madonna_293330_1955_24000_geo.pdf) |
| `calistoga1958` | Calistoga | 1:24,000 | 1958 | 1957 (aerial photographs 1957, field check 1958) | pink tint | 7 m (affine, 6/6 windows, RMS 3 m) | [288811](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Calistoga_288811_1958_24000_geo.pdf) |
| `cloverdale1960` | Cloverdale | 1:24,000 | 1960 | 1957 (aerial photographs 1957, field check 1960) | pink tint | as published | [289371](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Cloverdale_289371_1960_24000_geo.pdf) |
| `sthelena1960` | St Helena | 1:24,000 | 1960 | 1957 (aerial photographs 1957, field check 1960) | pink tint | 6 m (affine, 16/16 windows, RMS 6 m) | [295293](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_St%20Helena_295293_1960_24000_geo.pdf) |
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
* **Ten-county towns** (snapshot: sheets; details in each file's `note`):
  * **Santa Rosa** (`santa_rosa`): 1904 = Sanborn key map; 1914 = santarosa1916; 1942 = santarosa1944; 1952 = santarosa1954.
  * **Petaluma** (`petaluma`): 1910 = Sanborn key map; 1912 = petaluma1914; 1952 = petaluma1953, petalumacreek1954.
  * **Napa** (`napa`): 1899 = napa1902; 1910 = Sanborn key map; 1939 = sonoma1942; 1948 = napa1951.
  * **Vallejo** (`vallejo`): 1899 = napa1902; 1914 = mareisland1916; 1919 = Sanborn key map; 1940 = carquinezstrait1940; 1948 = mareisland1949, benicia1950.
  * **Santa Cruz** (`santa_cruz`): 1899 = santacruz1902; 1905 = Sanborn key map; 1952 = santacruz1954, soquel1954.
  * **Watsonville** (`watsonville`): 1908 = Sanborn key map; 1915 = capitola1914, sanjuanbautista1917; 1939 = capitola1940, sanjuanbautista1940; 1952 = watsonvillewest1954, watsonvilleeast1955.
  * **Benicia** (`benicia`): 1896 = karquines1898; 1913 = Sanborn key map; 1940 = carquinezstrait1940; 1948 = benicia1950.
  * **Sonoma** (`sonoma`): 1939 = sonoma1942; 1948 = sonoma1951.
  * **Healdsburg** (`healdsburg`): 1915 = healdsburg1920; 1933 = healdsburg1940; 1953 = healdsburg1955, guerneville1955.
  * **Sebastopol** (`sebastopol`): 1911 = Sanborn key map; 1935 = sebastopol1942; 1952 = sebastopol1954.
  * **St. Helena** (`st_helena`): 1910 = Sanborn key map; 1942 = sonoma1942, sthelena1945; 1957 = rutherford1951, sthelena1960.
  * **Calistoga** (`calistoga`): 1915 = calistoga1927; 1943 = calistoga1945; 1957 = calistoga1958.
  * **Fairfield - Suisun City** (`fairfield`): 1896 = karquines1898; 1940 = carquinezstrait1940h, mtvaca1942; 1948 = fairfieldsouth1949, fairfieldnorth1951.
  * **Vacaville** (`vacaville`): 1906 = vacaville1908; 1939 = vacaville1941, mtvaca1942; 1949 = elmira1953, fairfieldnorth1951.
  * **Dixon** (`dixon`): 1906 = vacaville1908; 1939 = vacaville1941; 1949 = dixon1952.
  * **Rio Vista** (`rio_vista`): 1908 = riovista1910; 1949 = riovista1953.
  * **Gilroy** (`gilroy`): 1906 = Sanborn key map; 1915 = morganhill1917, sanjuanbautista1917; 1939 = morganhill1941, sanjuanbautista1940; 1953 = gilroy1955, chittenden1955.
  * **Morgan Hill** (`morgan_hill`): 1915 = morganhill1917; 1953 = morganhill1955, mtmadonna1955.
  * **Antioch** (`antioch`): 1907 = antioch1908; 1949 = antiochnorth1953.
  * **Pittsburg** (`pittsburg`): 1907 = antioch1908; 1949 = honkerbay1953, antiochnorth1953.
  * **Brentwood** (`brentwood`): 1940 = byron1940; 1949 = brentwood1954.
  * **Cloverdale** (`cloverdale`): 1922 = hopland1938; 1942 = hopland1944; 1957 = cloverdale1960.
  * **Capitola - Soquel** (`capitola`): 1912 = capitola1914; 1938 = capitola1940; 1952 = soquel1954.
  * **Boulder Creek - Felton (San Lorenzo Valley: also Ben Lomond, Brookdale)** (`boulder_creek`): 1953 = felton1955, castlerockridge1955, bigbasin1955.

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
