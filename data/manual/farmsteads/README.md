# Farmsteads (and orchards) from USGS historical topographic maps

Where rural houses, barns and farmsteads really stood, read from the scanned USGS
topographic quadrangles of the farming districts of the modelled counties: the first
1:62,500 15' surveys (1885–1916) and the editions just before the post-war suburban boom
(1:24,000 7.5' sheets of 1947–1956, 15' sheets of 1939–1943 where no 7.5' sheet exists).
Built by `pipeline/topo_farmsteads.py` (`python pipeline/topo_farmsteads.py [list|process|export|all] [--area NAME]`);
sources: USGS Historical Topographic Map Collection (public domain, `SOURCES.md` → `usgs_htmc`).

## Files

| File | What |
|---|---|
| `topo_farmsteads.geojson` | one Point per farmstead (EPSG:4326): the dwelling, or the largest building, of a group of building symbols within 60 m |
| `coverage.geojson` | per processed sheet, the part of its neat line that the farmsteads of that sheet cover (a 15' sheet minus the 7.5' sheets of the same period); "no point here" inside it means "no rural building on that map" |
| `topo_towns.geojson` | areas excluded as towns: `kind = dense_buildings` (> 8 other symbols within 150 m: villages, town blocks, 1950s tracts) and `kind = urban_tint` (the red built-up tint of the 1940s–50s maps, inside which only landmark buildings are drawn) |
| `topo_orchards.geojson` | orchard and vineyard extents (Polygons) from the green vegetation overprint of the 1939–1956 sheets |

Farmstead properties: `map_year` (survey year from the USGS metadata, else the edition
year printed on the map), `edition_year`, `survey_year`, `photo_year` (aerial photographs
the 1940s–50s sheets were compiled from — usually 3–5 years before `map_year`), `quad`,
`scale`, `n_buildings` (symbols in the group, the farmstead's point included), `n_open`
(open squares = barns / sheds on the 1940s–50s maps), `has_dwelling` (false for a group of
open squares only — barns, packing sheds, chicken houses without a house), `score`
(detector confidence 0–1), `source_url` (the GeoPDF).

Orchard properties: `kind` (`orchard` | `vineyard`), `map_year`, `edition_year`,
`photo_year`, `quad`, `scale`, `source_url`.

## Method

1. **Sheets.** The TNM API (`tnmaccess.nationalmap.gov/api/v1/products`, dataset
   "Historical Topographic Maps") lists every scan of every edition. Per 15' cell, every
   distinct early *survey* (1886–1922) is used once (reprints and the 1:48,000 special
   printings of the same survey are skipped); per cell, the first 1939–1956 edition is used,
   1:24,000 preferred; photorevised reprints (purple overprints of a later state, "Photo
   Revision Year" in the metadata) and reprints of surveys before 1930 are skipped. Of
   duplicate scans of one printing, the earliest imprint wins. Survey / photo years come
   from the FGDC record of each scan (`vendorMetaUrl`).
2. **Scan and registration.** The GeoPDF holds the 600–700 ppi scan as 1024 px JPEG tiles
   (the published GeoTIFF is a 300 ppi resample) and its registration (`LGIDict`: CTM, neat
   line, polyconic NAD27 projection). The neat line inverts exactly onto the quadrangle
   corners (`corner_error_m` = 0 in the per-sheet cache). NAD27 → WGS84 through the NADCON
   grid (`us_noaa_conus.tif`, PROJ CDN, open licence).
3. **Building symbols** (sheet processed in 3000 px tiles, all thresholds in paper mm):
   black ink (darkest channel < 55 % of paper, not red-brown, not blue-green) → opening
   with a 0.26 mm disc (roads, rails, boundaries and thin text vanish; solid squares
   survive) → blobs above the valley of the sheet's own blob-area histogram, compact
   (elongation ≤ 2.6), solid (≥ 0.82), square-ish (min-area-rectangle fill ≥ 0.62).
   Rejected: pieces of lettering (thick strokes or other dark ink joined to the blob through
   hairline ink in a 2 mm window; letter counters; ≥ 2 letter-sized components within
   1.3 mm; next to the stems / bowls of large serif lettering; part of a curved or long
   heavy stroke), knots on rails and road crossings (a straight line through the blob with
   ink on both sides, or the blob between two parallel road casings), dots of dash-dot
   boundaries (dashes in line on both sides), triangulation stations (triangles), blobs in
   water lines, faint blobs. **Open squares** (the 1940s–50s barn / warehouse symbol):
   holes in the ink closed by a thin outline with four corners (counters of 0, 6, 8, O are
   ovals), isolated from heavy ink, then the same context tests.
4. **Towns.** Symbols with more than 8 others within 150 m (and every symbol within 150 m
   of such a symbol) are town, not farm; on the 1940s–50s maps the red urban tint (pink
   majority over ~2 mm) is town too.
5. **Farmsteads.** Dwellings (solid squares) largest first; each takes the not yet assigned
   buildings within 60 m as outbuildings. Open squares left over form farmsteads without a
   dwelling (`has_dwelling: false`). Where a 15' sheet and 7.5' sheets of the same period
   overlap, the 7.5' sheets win.
6. **Alignment to today's ground.** The early surveys are not on modern control: cross-
   correlating each sheet's black ink with today's road centrelines (OpenStreetMap via
   Overture, `roads_region.parquet`) in 2.5 km windows (± 450 m search for early sheets, ±
   150 m for late ones; ambiguous peaks dropped) and fitting the window shifts by
   consensus (the shift most windows agree with within 45 m / 15 m, then an affine model
   over those windows, bounded) shows the 1885–1899 surveys about **190–240 m** off, the
   1904–1916 surveys 35–110 m, with an inlier RMS of 12–28 m after the fit; the 1:24,000
   sheets of 1947–56 agree with today's roads to 3–15 m (corrected only when the fitted
   shift exceeds 10 m). The correction is applied to every symbol, town and orchard
   outline and to the coverage polygon of the sheet (`align` in the per-sheet cache:
   model, windows used, RMS). Sheets with too few roads (hill quadrangles) stay as
   published.
7. **Orchards / vineyards** (1939–1956 sheets, at 1/3 resolution): orchard = regular
   pattern of round green dots ~1 mm across (density of dot-shaped green components over
   3 mm); vineyard = green tint carrying a screen of white-paper lines ~0.9 mm apart
   (horizontal autocorrelation of the green-vs-white mask peaks at 0.8–1.0 mm, not at half
   that; brown contour lines and black roads count as "not white", so woodland tint cut by
   dense contours — which fooled a first version in the Marin hills — shows no screen).
   Closed / opened morphologically, ≥ 1 ha. Checked by overlay on San Jose East 1953
   (orchards across the valley floor and foothills, vineyards only in the Evergreen
   district, as on the map) and San Geronimo 1954 (woodland, no false orchards / vineyards).

## Quality

Precision was checked by eye on contact sheets of random detections (rural areas, after
the town filter) and on overlay crops (`data/interim/topo/debug/`):

* 1899 San Jose sheet (1895 survey): 96 random rural detections of the final detector —
  86 clearly buildings, 5 clearly not (a road crossing, a T-junction, two hachure strokes,
  a triangulation station corner), 5 ambiguous (blob where a road meets a building):
  **precision 0.90–0.95**. An independent earlier sample of 96, re-scored with the final
  rules: 0.97 (61 of 63 kept are buildings).
* Overlay crops of other early sheets (Petaluma 1914, Byron 1916, Pleasanton 1906, Palo
  Alto 1897, Morgan Hill 1917): ~0.9–0.98 per crop; the misses there are pieces of
  medium-size serif place names ("Byron", "Marin School") and hachures.
* 1953 San Jose East (1:24,000): solid symbols **0.98** (47 of 48 random detections are
  buildings — long sheds and schools are drawn as solid bars too; one well dot), open
  squares **~0.92** (36 of 39: the misses are the counters of O / 9 in road and place
  names; B / 8 / R counters are excluded by the two-counter test).
* Recall is lower than precision by design: on the 15' sheets roughly 70–85 % of the
  rural building symbols are found (missed: symbols touching road junctions, rows of
  touching symbols, symbols on contour-dense slopes, symbols inside or touching lettering);
  on the 1:24,000 sheets ~90 %.
* Farmstead points inherit the symbol position: on the 1:24,000 sheets ~5–10 m from the
  true position (map accuracy standard: 12 m), on the early 15' sheets ~15–30 m RMS after
  the road alignment, more where the old survey was locally distorted (symbols themselves
  are ~25 m across on the ground at 1:62,500). Unaligned sheets (`align.aligned = false`
  in the cache; marked "not aligned" in the table below) are hill sheets of 1947–56.

## Known failure modes

* **Text.** Serif wedges of large lettering and pieces of bold medium lettering can pass
  when their hairlines are too faint to connect them to the letter (most are caught by
  the stroke / big-text tests); black spot-height digits (0, 6, 8) on the late maps.
* **Road furniture.** Thickened road casings at crossings, ends of dead-end roads, rail
  tie crossings — mostly rejected; some remain where the scan is blurred.
* **Hills.** Hachures and contour-dense slopes, especially on the 1890s sheets.
* **Towns.** The 150 m density rule also removes genuine dense farm compounds (> 8
  buildings), and villages of ≤ 8 buildings remain as "farmsteads".
* **Time.** `map_year` is the survey year; the 1940s–50s sheets show the aerial photographs
  of `photo_year` with field checks up to `map_year`. The early sheets are often older than
  their edition date (e.g. San Jose 1889 shows the 1885 survey).
* **Orchards.** Orchard recall drops on steep slopes where contour lines cut the dots;
  vineyard extents are conservative (the periodic-texture test misses the edges of blocks
  and vineyards printed with another screen); only 1939–1956 sheets carry vegetation.

## Maps used

See `coverage.geojson` (one feature per sheet with quad, survey / edition / photo year,
scale, number of symbols and farmsteads, `source_url`, `metadata_url`). The list below is
regenerated by `topo_farmsteads.py export`.

<!-- maps-table -->

| Quadrangle | Scale | Edition | Survey | Photos | Period | Symbols | Farmsteads | Shift to today's roads | GeoPDF |
|---|---|---|---|---|---|---|---|---|---|
| Byron | 1:62,500 | 1916 | 1911 |  | early | 535 | 497 | 35 m (affine, RMS 19 m) | [296940](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Byron_296940_1916_62500_geo.pdf) |
| Concord | 1:62,500 | 1897 | 1894 |  | early | 743 | 701 | 98 m (affine, RMS 20 m) | [297157](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Concord_297157_1897_62500_geo.pdf) |
| Hayward | 1:62,500 | 1915 | 1914 |  | early | 794 | 753 | 211 m (affine, RMS 24 m) | [297660](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Hayward_297660_1915_62500_geo.pdf) |
| Haywards | 1:62,500 | 1899 | 1896 |  | early | 934 | 884 | 217 m (affine, RMS 22 m) | [465731](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Haywards_465731_1899_62500_geo.pdf) |
| Morgan Hill | 1:62,500 | 1917 | 1915 |  | early | 836 | 797 | 36 m (affine, RMS 16 m) | [298243](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Morgan%20Hill_298243_1917_62500_geo.pdf) |
| Mt. Diablo | 1:62,500 | 1898 | 1896 |  | early | 397 | 385 | 188 m (affine, RMS 28 m) | [298276](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Mt%20Diablo_298276_1898_62500_geo.pdf) |
| New Almaden | 1:62,500 | 1919 | 1916 |  | early | 540 | 528 | 60 m (affine, RMS 13 m) | [298353](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_New%20Almaden_298353_1919_62500_geo.pdf) |
| Palo Alto | 1:62,500 | 1897 | 1895 |  | early | 943 | 781 | 205 m (affine, RMS 23 m) | [298452](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Palo%20Alto_298452_1897_62500_geo.pdf) |
| Petaluma | 1:62,500 | 1914 | 1912 |  | early | 736 | 684 | 56 m (affine, RMS 13 m) | [298523](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Petaluma_298523_1914_62500_geo.pdf) |
| Pleasanton | 1:62,500 | 1906 | 1904 |  | early | 840 | 774 | 65 m (affine, RMS 25 m) | [298577](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Pleasanton_298577_1906_62500_geo.pdf) |
| San Jose | 1:62,500 | 1889 | 1885 |  | early | 1954 | 1507 | 238 m (affine, RMS 27 m) | [301582](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Jose_301582_1889_62500_geo.pdf) |
| San Jose | 1:62,500 | 1897 | 1895 |  | early | 3656 | 2406 | 237 m (affine, RMS 26 m) | [298899](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_San%20Jose_298899_1897_62500_geo.pdf) |
| Tesla | 1:62,500 | 1907 | 1905 |  | early | 266 | 251 | 41 m (affine, RMS 12 m) | [298992](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Tesla_298992_1907_62500_geo.pdf) |
| Altamont | 1:62,500 | 1942 |  | 1937 | late | 317 | 37 | 12 m (affine, RMS 6 m) | [296684](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Altamont_296684_1942_62500_geo.pdf) |
| Altamont | 1:24,000 | 1953 | 1953 | 1949 | late | 880 | 492 | 0 m (constant, RMS 7 m) | [287935](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Altamont_287935_1953_24000_geo.pdf) |
| Antioch South | 1:24,000 | 1953 |  | 1949 | late | 665 | 400 | 8 m (constant, RMS 8 m) | [288006](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Antioch%20South_288006_1953_24000_geo.pdf) |
| Brentwood | 1:24,000 | 1954 |  | 1949 | late | 1485 | 780 | 14 m (affine, RMS 9 m) | [302487](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Brentwood_302487_1954_24000_geo.pdf) |
| Byron Hot Springs | 1:24,000 | 1953 |  | 1949 | late | 310 | 208 | not aligned | [288716](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Byron%20Hot%20Springs_288716_1953_24000_geo.pdf) |
| Calaveras Reservoir | 1:24,000 | 1953 | 1953 | 1948 | late | 726 | 376 | 8 m (constant, RMS 7 m) | [288769](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Calaveras%20Reservoir_288769_1953_24000_geo.pdf) |
| Castle Rock Ridge | 1:24,000 | 1955 |  | 1953 | late | 821 | 390 | not aligned | [289043](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Castle%20Rock%20Ridge_289043_1955_24000_geo.pdf) |
| Cedar Mtn | 1:24,000 | 1956 |  | 1953 | late | 83 | 71 | not aligned | [289084](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Cedar%20Mtn_289084_1956_24000_geo.pdf) |
| Clayton | 1:24,000 | 1953 | 1953 | 1949 | late | 1077 | 423 | 7 m (affine, RMS 5 m) | [289332](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Clayton_289332_1953_24000_geo.pdf) |
| Concord | 1:62,500 | 1942 |  | 1939 | late | 1564 | 817 | 13 m (affine, RMS 9 m) | [465521](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Concord_465521_1942_62500_geo.pdf) |
| Cotati | 1:24,000 | 1954 | 1954 | 1952 | late | 3924 | 1048 | 4 m (affine, RMS 7 m) | [289550](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Cotati_289550_1954_24000_geo.pdf) |
| Cupertino | 1:24,000 | 1953 | 1953 | 1948 | late | 4700 | 1177 | 7 m (affine, RMS 8 m) | [289702](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Cupertino_289702_1953_24000_geo.pdf) |
| Diablo | 1:24,000 | 1953 |  | 1949 | late | 1092 | 371 | 10 m (affine, RMS 4 m) | [289931](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Diablo_289931_1953_24000_geo.pdf) |
| Dublin | 1:24,000 | 1953 | 1953 | 1949 | late | 651 | 320 | 0 m (constant, RMS 8 m) | [290057](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Dublin_290057_1953_24000_geo.pdf) |
| Gilroy | 1:24,000 | 1955 | 1955 | 1953 | late | 2019 | 1036 | 0 m (constant, RMS 0 m) | [290814](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Gilroy_290814_1955_24000_geo.pdf) |
| Gilroy Hot Springs | 1:24,000 | 1955 |  | 1953 | late | 63 | 56 | not aligned | [290822](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Gilroy%20Hot%20Springs_290822_1955_24000_geo.pdf) |
| Glen Ellen | 1:24,000 | 1954 | 1954 | 1952 | late | 952 | 438 | not aligned | [290850](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Glen%20Ellen_290850_1954_24000_geo.pdf) |
| Half Moon Bay | 1:24,000 | 1952 |  | 1948 | late | 800 | 259 | 8 m (constant, RMS 5 m) | [291121](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Half%20Moon%20Bay_291121_1952_24000_geo.pdf) |
| Hayward | 1:24,000 | 1947 | 1947 | 1946 | late | 4761 | 697 | 12 m (affine, RMS 8 m) | [291242](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Hayward_291242_1947_24000_geo.pdf) |
| Jersey Island | 1:24,000 | 1952 | 1952 | 1949 | late | 366 | 309 | not aligned | [291690](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Jersey%20Island_291690_1952_24000_geo.pdf) |
| La Costa Valley | 1:24,000 | 1953 |  | 1948 | late | 346 | 203 | not aligned | [291950](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_La%20Costa%20Valley_291950_1953_24000_geo.pdf) |
| La Honda | 1:24,000 | 1955 |  | 1953 | late | 654 | 319 | not aligned | [291977](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_La%20Honda_291977_1955_24000_geo.pdf) |
| Lick Observatory | 1:24,000 | 1955 |  | 1953 | late | 275 | 238 | not aligned | [292290](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Lick%20Observatory_292290_1955_24000_geo.pdf) |
| Livermore | 1:24,000 | 1953 |  | 1949 | late | 735 | 410 | 6 m (affine, RMS 9 m) | [292401](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Livermore_292401_1953_24000_geo.pdf) |
| Los Gatos | 1:62,500 | 1940 |  | 1937 | late | 782 | 329 | 9 m (affine, RMS 8 m) | [298059](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Los%20Gatos_298059_1940_62500_geo.pdf) |
| Los Gatos | 1:24,000 | 1953 | 1953 | 1948 | late | 2428 | 621 | 11 m (affine, RMS 7 m) | [292565](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Los%20Gatos_292565_1953_24000_geo.pdf) |
| Mendenhall Springs | 1:24,000 | 1956 |  | 1953 | late | 235 | 202 | not aligned | [292858](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Mendenhall%20Springs_292858_1956_24000_geo.pdf) |
| Milpitas | 1:24,000 | 1953 | 1953 | 1948 | late | 1473 | 705 | 15 m (affine, RMS 6 m) | [292969](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Milpitas_292969_1953_24000_geo.pdf) |
| Montara Mountain | 1:24,000 | 1949 |  | 1946 | late | 875 | 228 | 8 m (constant, RMS 8 m) | [293071](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Montara%20Mountain_293071_1949_24000_geo.pdf) |
| Morgan Hill | 1:24,000 | 1955 | 1955 | 1953 | late | 1123 | 577 | 30 m (constant, RMS 8 m) | [293124](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Morgan%20Hill_293124_1955_24000_geo.pdf) |
| Mountain View | 1:24,000 | 1953 | 1953 | 1948 | late | 3136 | 534 | 8 m (affine, RMS 7 m) | [293234](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Mountain%20View_293234_1953_24000_geo.pdf) |
| Mt. Day | 1:24,000 | 1955 |  | 1953 | late | 102 | 87 | not aligned | [293282](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Mt%20Day_293282_1955_24000_geo.pdf) |
| Mt. Madonna | 1:24,000 | 1955 | 1955 | 1953 | late | 925 | 674 | 0 m (constant, RMS 0 m) | [293330](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Mt%20Madonna_293330_1955_24000_geo.pdf) |
| Mt. Sizer | 1:24,000 | 1955 | 1955 | 1953 | late | 200 | 167 | not aligned | [466007](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Mt%20Sizer_466007_1955_24000_geo.pdf) |
| Newark | 1:24,000 | 1947 | 1947 | 1946 | late | 953 | 481 | 16 m (affine, RMS 8 m) | [293493](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Newark_293493_1947_24000_geo.pdf) |
| Niles | 1:24,000 | 1953 | 1953 | 1948 | late | 2422 | 715 | 8 m (affine, RMS 7 m) | [293546](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Niles_293546_1953_24000_geo.pdf) |
| Novato | 1:24,000 | 1954 | 1954 | 1952 | late | 2702 | 495 | not aligned | [293601](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Novato_293601_1954_24000_geo.pdf) |
| Palo Alto | 1:62,500 | 1943 |  | 1940 | late | 2478 | 176 | 8 m (affine, RMS 9 m) | [298463](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/62500/CA_Palo%20Alto_298463_1943_62500_geo.pdf) |
| Palo Alto | 1:24,000 | 1953 | 1953 | 1948 | late | 1340 | 657 | 9 m (affine, RMS 8 m) | [293907](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Palo%20Alto_293907_1953_24000_geo.pdf) |
| Petaluma | 1:24,000 | 1953 | 1953 | 1952 | late | 1642 | 323 | not aligned | [294061](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Petaluma_294061_1953_24000_geo.pdf) |
| Petaluma Creek | 1:24,000 | 1954 | 1954 | 1952 | late | 609 | 314 | 4 m (constant, RMS 4 m) | [294065](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Petaluma%20Creek_294065_1954_24000_geo.pdf) |
| Petaluma Point | 1:24,000 | 1951 | 1949 | 1948 | late | 41 | 41 | not aligned | [294067](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Petaluma%20Point_294067_1951_24000_geo.pdf) |
| Port Chicago | 1:24,000 | 1951 | 1950 | 1948 | late | 871 | 160 | not aligned | [294325](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Port%20Chicago_294325_1951_24000_geo.pdf) |
| Redwood Point | 1:24,000 | 1948 |  |  | late | 61 | 55 | not aligned | [294610](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Redwood%20Point_294610_1948_24000_geo.pdf) |
| San Geronimo | 1:24,000 | 1954 |  | 1952 | late | 694 | 252 | not aligned | [300077](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_San%20Geronimo_300077_1954_24000_geo.pdf) |
| San Gregorio | 1:24,000 | 1955 |  | 1953 | late | 153 | 76 | not aligned | [300088](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_San%20Gregorio_300088_1955_24000_geo.pdf) |
| San Jose East | 1:24,000 | 1953 | 1953 | 1948 | late | 4453 | 1210 | 3 m (affine, RMS 8 m) | [300099](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_San%20Jose%20East_300099_1953_24000_geo.pdf) |
| San Jose West | 1:24,000 | 1953 | 1953 | 1948 | late | 4663 | 997 | 4 m (affine, RMS 8 m) | [300105](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_San%20Jose%20West_300105_1953_24000_geo.pdf) |
| San Leandro | 1:24,000 | 1947 |  |  | late | 849 | 254 | 8 m (affine, RMS 9 m) | [300122](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_San%20Leandro_300122_1947_24000_geo.pdf) |
| Santa Teresa Hills | 1:24,000 | 1953 | 1953 | 1948 | late | 741 | 379 | 14 m (affine, RMS 5 m) | [300319](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Santa%20Teresa%20Hills_300319_1953_24000_geo.pdf) |
| Sears Point | 1:24,000 | 1951 | 1951 | 1948 | late | 495 | 254 | not aligned | [300386](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Sears%20Point_300386_1951_24000_geo.pdf) |
| Tassajara | 1:24,000 | 1953 |  | 1950 | late | 166 | 130 | not aligned | [300793](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Tassajara_300793_1953_24000_geo.pdf) |
| Walnut Creek | 1:24,000 | 1947 |  | 1946 | late | 4917 | 1309 | 6 m (affine, RMS 8 m) | [301185](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Walnut%20Creek_301185_1947_24000_geo.pdf) |
| Woodside | 1:24,000 | 1953 |  | 1948 | late | 1838 | 435 | 8 m (constant, RMS 7 m) | [301429](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Woodside_301429_1953_24000_geo.pdf) |
| Woodward Island | 1:24,000 | 1952 | 1952 | 1931 | late | 300 | 195 | not aligned | [301439](https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/CA_Woodward%20Island_301439_1952_24000_geo.pdf) |
