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
   150 m for late ones), with a robust affine fit over the window shifts, shows the
   1885–1895 surveys about **150–230 m** off (residual RMS 35–50 m after the fit) and the
   1915 surveys ~35 m; the 1:24,000 sheets of 1947–56 agree with today's roads to ~5 m
   (not corrected unless the fitted shift exceeds 10 m). The fitted correction is applied
   to every symbol, town and orchard outline and to the coverage polygon of the sheet
   (`align` in the per-sheet cache: model, windows used, RMS).
7. **Orchards / vineyards** (1939–1956 sheets, at 1/3 resolution): orchard = regular
   pattern of round green dots ~1 mm across (density of dot-shaped green components over
   3 mm); vineyard = green tint carrying a screen of white lines ~0.9 mm apart (horizontal
   autocorrelation peak at 0.8–1.0 mm, none at half that); solid woodland tint and woodland
   cut by contour lines show neither. Closed / opened morphologically, ≥ 1 ha.

## Quality

Precision was checked by eye on contact sheets of random detections (rural areas, after
the town filter) and on overlay crops (`data/interim/topo/debug/`):

* 1899 San Jose sheet (1895 survey), 96 random detections of an earlier detector version,
  re-scored with the final rules: **precision 0.97** (2 false of 63 kept; remaining false
  positives: a hachure stroke, a short heavy line), recall relative to the earlier version
  0.90 (houses touching a road at a junction and touching rows of houses are given up).
* 1953 San Jose East (1:24,000): solid symbols **~0.99** (96 sampled: all buildings; three
  were long sheds / a school drawn as solid bars), open squares **~0.98** after the
  four-corner test (the five false of 48 sampled before it were digit / letter counters).
* Recall is lower than precision by design: on the 15' sheets roughly 70–85 % of the
  rural building symbols are found (missed: symbols touching road junctions, rows of
  touching symbols, symbols on contour-dense slopes, symbols inside or touching lettering);
  on the 1:24,000 sheets ~90 %.
* Farmstead points inherit the symbol position: on the 1:24,000 sheets ~5–10 m from the
  true position (map accuracy standard: 12 m), on the early 15' sheets ~35–50 m RMS after
  the road alignment (symbols themselves are ~25 m across on the ground at 1:62,500).

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
