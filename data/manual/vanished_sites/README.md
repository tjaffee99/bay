# Vanished large sites (`data/manual/vanished_sites/`)

Big sites that were built and are gone again — racetracks, an office campus, a car plant, amusement
parks and bath resorts, ball parks, drive-ins, a wartime camp, a town razed for an industrial park,
cleared redevelopment blocks — leave no trace in today's footprints, so without this folder the terrain
shows farmland or plain city ground until today's buildings arrive. Each site is traced from **real
historical maps and orthophotos** (USGS historical topographic sheets 1894–1997, Library of Congress
Sanborn fire-insurance maps 1897–1951, the October 2010 orthophoto in Esri's World Imagery Wayback
archive, OpenStreetMap for today's grounds); dates come from cited histories plus the editions on which
each feature first appears. Anything generated or estimated says so in its `confidence` / `note`.

## Files

| file | what |
|---|---|
| `sites.geojson` | Polygon parts of each site's ground over its lifetime (one feature per part and period) |
| `buildings.geojson` | Footprints of vanished buildings (predecessors) |
| `road_segments.csv` | Overture road segments (`roads_local` / `roads_region`) lying on these sites (318 rows), with a *not-before* year where the segment cannot have existed (see below) |
| `traced/*.json` | Intermediate tracings in each site's local metre frame (automatic extractions from the sheets, hand-read corners); second batch: `idora_park_1911.json`, `alameda_baths_sanborn.json`, `emeryville_sanborn_1911.json`, `oaks_park_sanborn.json` (Sanborn fits), `russell_city_topo.json`, `bay_district_track_1895.json` |
| `traced/apple_park_osm.geojson` | OSM features of Apple Park (via Overture base / transportation, © OpenStreetMap contributors, ODbL) |
| `tools/` | The tracing tools (see *Method*); `python -I tools/trace_sites.py` rebuilds the two GeoJSONs from `traced/` (first batch `sites_def.py`, second batch `sites_def2.py`); `python -I tools/roadseg2.py` (run in this folder) rewrites the second batch's rows of `road_segments.csv`; Sanborn tracers `tools/sanborn_*_trace.py` (+ `sbref.py` fits, `sbseg.py` colour segmentation) and `tools/russell_city_trace.py` write `traced/` (they expect the LOC images / topo renders in a scratch folder: see each script's header) |

### `sites.geojson` properties
`site_id, name, kind` (racetrack | office_campus | factory | amusement_park | drive_in | military | campus_grounds |
resort | ballpark | town | redevelopment_lot),
`cover` (what the ground was: `dirt_track | turf | grass | park | parking | industrial | urban | water`),
`surface` (finer label: "dirt track", "turf course", "stable yard", "footpath", "road", "theme park"…),
`year_start, year_end` (fractional years; 9999 = still there), `confidence` (`exact` = position and dates from the
sources; `estimated` = traced but a date or an outline is approximate; `procedural` = generated), `source_url`, `note`.

A part with cover `urban` / `industrial` that starts when another part of the same site ends (Russell City → industrial
park, the Trans Pacific lots → today's buildings) is there so the terrain returns to city ground instead of staying
"cleared ground" after the site's end (`terrain_tiles.py` clears a part's ground at its end unless a later part of
the same site takes it over).

Parts overlap on purpose: the larger part is the ground under the smaller ones (e.g. the racetrack grounds polygon
→ the dirt oval ring → the turf ring → the infield → the ponds). Ring parts are true polygons with holes; if a
consumer draws only exterior rings, it must draw larger parts first (as `ground_detail.py` does) — every ring
part has a filled part inside it for the same years.

### `buildings.geojson` properties
`site_id, name, start_year, end_year, height_m, storeys, material` (wood frame | brick | concrete | steel | tilt-up),
`use` (dwelling | office | factory | warehouse | grandstand | hall | other), `confidence, source_url, note`.
None of these footprints is in today's data (checked against the Overture footprints; where a building of a site
still stands — the Great Mall, the Edenvale church — it is left out).

## Method

* **Topo sheets:** USGS Historical Topographic Map Collection GeoTIFFs, read through the TNM Access API
  (`tnmaccess.nationalmap.gov`, editions and their *aerial photo / photo revision / imprint* years from each sheet's
  FGDC metadata), resampled into a north-up local metre frame with the sheet's own registration and the NOAA NADCON
  grid (NAD27 → WGS84; `data/raw/proj/us_noaa_conus.tif`). Alignment was checked against today's streets (Overture)
  on every render: 1:24,000 sheets fit within a few metres.
* **Buildings from sheets:** filled building symbols are extracted automatically (dark-ink mask → morphological
  opening → connected components → minimum-area rectangles where the symbol is rectangular; `tools/blobs.py`);
  outlined symbols (1956 Tanforan) are filled first; purple photorevision overprints are read the same way.
* **Dating by edition:** each footprint's ink coverage is measured on every earlier edition (`tools/presence.py`);
  the start year is the midpoint between the last edition without it and the first with it (or a documented
  year). Photorevision editions are dated by their aerial-photo year.
* **Racetrack ovals:** a stadium curve (two semicircles joined by straights) is least-squares fitted to the track
  line pixels (`tools/oval.py`), and checked against the documented track length (Bay Meadows: inner rail 1,613 m
  = 1 mile; Tanforan: 1,610 m).
* **Orthophoto:** Esri World Imagery Wayback release 2014-02-20 (tile service
  `wayback.maptiles.arcgis.com/.../tile/10/{z}/{y}/{x}`; its metadata service gives the source: Microsoft UltraCam,
  26 Oct 2010, 0.3 m) — viewed only; roof outlines of the HP campus were segmented on it and orthogonalised, the
  rest read by hand on a 10 m grid. NAIP before 2010 and the USDA/USGS historical orthophoto services were not
  reachable from the build environment.
* **Sanborn sheets (second batch):** Library of Congress IIIF images (25 %, ~5 px per metre at 1 in = 50 ft) of the
  Oakland (sanborn00727) and Alameda (sanborn00374) atlases. A sheet is fitted to today's ground by an affine (or
  similarity) transform of four block corners read on the sheet against the same corners of today's parcel blocks
  (Alameda County parcels 2021, unioned per block; `tools/sbref.py`) or street-centreline crossings (Overture); the
  residuals (0.2–2.8 m) are given per site. Buildings are the yellow (frame) / pink (brick) / blue (concrete) fills
  (`tools/sbseg.py`: colour mask → close / open → polygons), each assigned a name and use from the sheet's lettering
  by hand (a list of label points per sheet in the tracer); rides, tracks and open-air platforms are hand-traced.
  Storey numbers give heights (≈ 4 m per storey, ESTIMATE).
* **House symbols (Russell City):** at 1:24,000 a house symbol is a fixed ~14 m square, not the house; the symbol's
  position is kept and the footprint is a 9 × 9 m house (ESTIMATE). Symbols are found by opening the dark-ink mask
  with a 7 m square (removes the 3 m road lines) and split every ~13 m along merged rows.
* **Early 15′ sheets** (1:62,500, 1890s–1910s) are not on NAD27 control; they are shifted onto today's streets by
  cross-correlation (`tools/align.py`) or, where the street grid is periodic (SF Richmond District), by an affine of
  four boundary-street corners read on the render.
* **Today's grounds (Apple Park):** OpenStreetMap features via the Overture 2026-10-21.0 release (land, land_use,
  water, transportation segments: footway / path / cycleway / steps / pedestrian / service / unclassified),
  clipped to the campus west of Tantau Ave; path centrelines buffered to a typical width (footway 3.5 m, path 3 m,
  cycleway 3.5 m, steps 3 m, pedestrian 6 m, service 6 m, unclassified 8 m — widths estimated).

## Sites

| site_id | name | years | traced from | confidence |
|---|---|---|---|---|
| `bay_meadows` | Bay Meadows Racecourse, San Mateo | 13 Nov 1934 – Aug 2008 (training to 8 Oct 2008; grandstand gutted Oct 2008, imploded late 2008) | San Mateo 1:24k sheets 1947 (1946 photos), 1956, 1968 PR, 1973 PR, 1980 PR (1978 photos), 1993, 1997; Oct 2010 orthophoto for the parcel edge | oval exact (fit rms 3 m); turf width, chute lengths, infield pond end estimated |
| `hp_cupertino` | Hewlett-Packard Cupertino site (Wolfe Rd / Pruneridge Ave) | 1969 – 2014 | Oct 2010 orthophoto (footprints), Cupertino 1:24k 1961 (1960), 1968 PR, 1973 PR, 1979 PR, 1991 (dating) | footprints good (±2 m); start years by edition (±4 yr) |
| `apple_park` | Apple Park grounds | Apr 2017 – | OSM (Overture) | exact geometry; path widths estimated |
| `tanforan` | Tanforan Racetrack, San Bruno | 4 Nov 1899 – 1964 (grandstand fire 31 Jul 1964) | San Francisco South 1:24k 1947 (1946 photos), 1956 | oval / buildings exact; the 1899 grandstand outline assumed = the 1923 stand's |
| `tanforan_assembly_center` | Tanforan Assembly Center | 28 Apr – 13 Oct 1942 (barracks to c.1945) | Densho (count / size / location in the infield) | **procedural** positions |
| `ford_milpitas` | Ford San Jose Assembly Plant, Milpitas | 1955 – 1983 (mall 1994) | Milpitas 1:24k 1961 (1960), 1968 PR, 1973 PR, 1980 PR (1979) | yard estimated; demolished parts exact outline |
| `marine_world` | Marine World / Africa USA, Redwood Shores | Jul 1968 – 1986 | San Mateo 1:24k 1980 PR (1978 photos) | built-up area exact; buildings are symbol blobs (approximate) |
| `frontier_village` | Frontier Village, San José | 21 Oct 1961 – 28 Sep 1980 | San Jose East 1:24k 1973 PR | grounds / lake traced; buildings exact symbols |
| `frontier_drive_in` | Frontier drive-in (Frontier Auto Movie) | Apr 1962 – c.1980 | San Jose East 1:24k 1973 PR ("Drive-in Theater" + dashed outline) | outline approximate, end year estimated |
| `oakland_nsc` | Naval Supply Center Oakland (Naval Supply Depot / FISC) | 15 Dec 1941 – 1998 (cleared c.1999–2001) | Oakland West 1:24k 1949 (1946 photos), 1959 (1958 photos), 1993 | warehouses traced automatically (±5 m, a few merged pairs); start 1942.5 / 1952 by edition; end 2000 estimated |
| `emeryville_racetrack` | Oakland Trotting Park / New California Jockey Club track, Emeryville | 4 Jul 1871 – last race 15 Feb 1911 (buildings burned 15 Dec 1915) | San Francisco 1:62,500 (1899 ed., 1914 imprint), shifted 220 m onto today's streets, then 22 m onto the 1911 Sanborn; 39 buildings from the 1911 Sanborn (sheets 321–325) | oval ±15 m; buildings ±5 m (sheet 324/325), ±15 m (323) |
| `idora_park` | Idora Park, Oakland (56th–58th St, Telegraph–Shattuck) | 16 May 1903 – Jan 1929 (razed 1929) | Sanborn Oakland 1911 vol. 3 sheet 293 (affine to today's block, residuals ≤ 1.5 m) | outline / buildings ±2 m; heights estimated |
| `neptune_beach` | Neptune Beach, Alameda (Central Ave, Webster St – McKay Ave) | New Surf Beach 7 May 1916, Neptune Beach 31 Mar 1917 – closed 1939, auctioned 25 Mar 1940, demolished by Nov 1940 | ground = the fill on USGS Oakland West 1949 (1946 photos); pools, coasters, stadium, bathhouse **placed** from 1930s aerial photographs | **estimated** (features ±20 m) |
| `neptune_gardens` | Neptune Gardens (Long Branch Baths site, later Croll's), Alameda | May 1880 – 1916 (pavilion 1885–1914) | Sanborn Alameda 1897 sheet 15 | estimated |
| `terrace_baths` | The Terrace Baths, Alameda (Central Ave at Sixth St) | 1878 – 1916 (end estimated) | Sanborn Alameda 1897 sheet 15 | estimated |
| `cottage_baths`, `sunny_cove_baths`, `green_arbor_baths`, `sandy_beach_baths`, `alameda_baths` | Alameda west-end bath houses (Fifth – Sixth St, south of Central Ave) | 1878/1895 – 1900…1953 | Sanborn Alameda 1897 and 1948, sheets 11, 12 | estimated (layout of each edition, dates by edition) |
| `shell_mound_park` | Shell Mound Park, Emeryville | 1877 – 1924 | Sanborn Oakland 1911 vol. 3 sheets 323, 324 | estimated |
| `oaks_park` | Oaks Park (Oakland Oaks ball park), Emeryville | 1913 – 1955 (demolished c.1957) | Sanborn Oakland 1911–Oct 1950 vol. 3 sheet 317 | stands ±3 m; demolition year estimated |
| `bay_district_track` | Bay District race track, SF (First Ave – Fifth Ave, Fulton St – Point Lobos Ave) | Sep 1874 – 27 May 1896 (streets cut by 1898) | San Francisco 1:62,500 1895 (1894 survey) | oval ±20 m |
| `ingleside_racetrack` | Ingleside race track, SF | 28 Nov 1895 – 1906 (sold 1910) | Urbano Drive (laid on the track 1912) | oval ±10 m; width estimated |
| `russell_city` | Russell City, Hayward | laid out 1907 – evicted 1964, cleared 1966 | San Leandro 1:24k 1947 (houses), 1959 (town tint), 1968 PR; Hayward 1:62,500 1942 (1939 photos) for dating | positions ±5 m; footprints and start years **estimated** |
| `geneva_drive_in` | Geneva Drive-In (Geneva 4), Daly City | 1950 – 1999 (demolished Mar 2002) | San Francisco South 1:24k 1956 | outline ±10 m |
| `oakland_trans_pacific_lots` | Trans Pacific Centre blocks, downtown Oakland (9th–11th St, Broadway–Webster) | cleared 1978 / c.1980–82, vacant or parking until 1982 / 1990 / 2001 | Sanborn 1950 vol. 2 sheets 150–151; USGS Oakland West 1980 PR (1979 photos); 1982 EIR | estimated (see `../redevelopment_areas.csv`) |

### Bay Meadows (1934–2008)
* Main track: 1-mile dirt oval, axis bearing −8°, fitted to the track line of the 1993 sheet (the 1946/1956 sheets
  draw its two edges 10 m inside / 12 m outside that line → inner rail 1,613 m). Homestretch chute (NW) and backstretch
  chute (SE) from the 1946/1956/1993 sheets (lengths estimated).
* Longden Turf Course: 7 furlongs (PCAD) at its inner rail, same centre and straights → radius 95.6 m, width 21 m
  (estimated). The 1946-photo sheet already shows an inner course line; its turf start year is not documented, so
  the turf ring spans the track's whole life (estimated).
* Infield: grass with two ponds (1956 sheet, blue), gone on the 1968 photorevision (end 1962, estimated).
* Grandstand: the 1934 stand from the 1947 sheet (1946 photos), replaced by the larger cross-hatched stand of the 1956
  sheet (enlargement year 1951 estimated; 12,000 seats per PCAD). Heights estimated (15 / 18 m).
* Stables: 35 shedrow barns + outbuildings from the 1993 sheet, dated by edition (most first on the 1956 sheet →
  start 1951; two in 1962 / 1970; four first on 1993 → 1985). The stable area and the 5/8-mile practice track (first
  drawn on the 1968 photorevision; fitted on the 1993 sheet, perimeter 1,059 m) were sold for **Bay Meadows Phase I**
  (end 1998, estimated: specific plan approved 1997, Franklin Templeton campus opened 2001).
* Racetrack grounds polygon (parking, paddock): the graded 83-acre parcel on the Oct 2010 orthophoto, west side to
  the railway as on the 1956/1993 sheets.
* **Neighbourhood construction (for streets):** Phase I (the stable area / practice track, ~75 acres): built late
  1990s – mid-2000s (Franklin Templeton HQ opened 2001; completed with the Kaiser medical offices). Phase II (the main
  track, 83 acres): demolition from Sep/Oct 2008; the northern streets are already paved on the Oct 2010 orthophoto;
  first residential groundbreaking Oct 2012 (Landsdowne, Amelia); Nueva School opened Aug 2014; SurveyMonkey lease
  2015; Station 2 offices from May 2017; 11 of 18 blocks developed by 2019; 25th Ave grade separation 2017–21 moved
  Hillsdale station to 28th Ave (Wikipedia "Bay Meadows (neighborhood)"; GlobeSt 2008; SM Daily Journal).

### HP Cupertino site and Apple Park
* HP Cupertino Division moved into a new 150,000 sq ft building at Wolfe Rd & Homestead in **1969** (HP Museum): the
  two big buildings at the NW corner. On the Oct 2010 orthophoto the east half of that building is already a
  demolition pad (end 2009.5, estimated).
* The other 20 footprints were segmented / read on the Oct 2010 orthophoto and dated by the first Cupertino edition
  showing them: central / south-west buildings 1973–79 photorevisions, the rest first on the 1991 sheet (start
  1985 = midpoint). Ends: demolition for Apple Park from late 2013 (approval 15 Oct 2013) → 2014.0. Heights /
  storeys estimated (2 storeys north, 3 south).
* Ground: the campus west of Tantau Ave is office park (`parking` cover) from its zone's first building (1969 / 1970 /
  1976 / 1985); before that orchard (the 1960 sheet shows prune orchard everywhere except the fruit-plant / farm
  cluster at the SW). **Old Pruneridge Avenue** (curved alignment through the site, 16 m, on the 1968–2010 maps and
  imagery, removed 2014) is a `road` part.
* Apple Park (2017.3 –): the whole campus outline is `park`; on top: OSM woods / orchards (`park`), native grassland and
  lawns (`grass`), the sports fields (`turf`), plazas (`parking`), the courtyard pond (`water`), and every footway,
  path, cycleway, steps, service road and **Apple Park Way** (the ring road) as a buffered polygon (`parking`,
  `surface` footpath / road). The main building, parking structures, fitness centre, visitor centre and Steve Jobs
  Theater are today's footprints and are not repeated here. Parts under today's buildings are clipped away.

### Tanforan (1899–1964)
* Oval fitted to the 1947 sheet (inner line 1,610 m = 1 mile; outer edge +26 m). Infield: two ponds on the 1946-photo
  sheet, one large lake on the 1956 sheet (switch year 1951, estimated).
* Grandstand: steel stand begun Dec 1922 (5,000 seats) traced from the 1947 sheet, burned with the clubhouse on
  31 Jul 1964. The first (1899) stand is given the same outline — LOW confidence. Stables / track buildings from the
  1947 sheet (start 1933, the return of racing, estimated) and the outlined buildings added on the 1956 sheet (1951).
  Site sold Mar 1964, shopping centre 1971.
* Assembly Center: ~76 of its ~180 barracks (20 × 100 ft) stood in the infield (Densho); their positions are not
  documented here, so 76 barracks are **generated** in rows along the track axis (`procedural`). The stables east of
  the infield, which housed about half the detainees, are the traced stable footprints.

### Ford Milpitas (1955–1983)
The main assembly building is **today's Great Mall footprint** (the mall opened 22 Sep 1994 inside the plant's main
structure). The region data gives it 1994 (`region5_footprint_years`: Milpitas roll and FEMA both 1994); it should be
dated **1955** — Overture id `2716f0ef-a8ca-41e4-b308-26ca19416db4` (please add to `known_building_dates_region.csv`;
I did not edit that table). This folder adds the plant yard (`industrial`, 1955–1993) and the plant parts drawn on the
1961–1980 sheets that are not in today's footprints (additions dated by edition).

### Marine World / Africa USA (1968–1986) and Frontier Village (1961–1980)
Both traced from photorevised 1:24k sheets: the built-up tint outlines the park, building symbols give the
buildings (Marine World's are purple overprint blobs — approximate; its round show building is hand-placed),
Frontier Village's lake / canoe canal is the unshaded area with blue shore lines inside the park tint. Marine World's
site became Oracle's headquarters (from 1989); Frontier Village's became Edenvale Garden Park and Bren housing; the
cross-plan church on the same sheet still stands and is not included.

### Naval Supply Center Oakland (1941–1998)
* Ground: the depot inside its perimeter road (1993 sheet) is `industrial` 1941.95–2000; the part over today's Middle
  Harbor water stays water in the terrain (the depot's finger piers and their warehouses are in `buildings.geojson`).
* Warehouses: the cross-hatched buildings of the 1959 sheet, found as areas where *both* diagonal hatch directions are
  present (`tools/fisc3.py`: short ±45° line openings minus long straight lines → density → opening), then split along
  the depot's street grid (grid angle 74.7°, from the clean detections) by row / column projections (`tools/fisc6.py`).
  108 footprints, 0.7 km²; map lettering filtered by size / aspect. Present on the 1946-photo sheet → built 1941–45
  (start 1942.5, estimated); else 1952 (midpoint). Heights 9 m, one storey, concrete — estimated.
* Not done: the Oakland Army Base north of the rail yards (its warehouses were demolished in several waves 1999–2016;
  some stand in today's data).

### Emeryville race track (1871–1915)
Edward Wiard's Oakland Trotting Park opened 4 Jul 1871; rebuilt and reopened 24 Oct 1896 as the New California Jockey
Club track (pagoda-style stand for ~3,000); the last race was run 15 Feb 1911 (Walker-Young anti-gambling law); the Mee
estate subdivided it for factories in 1915 and the remaining buildings burned on 15 Dec 1915 (Emeryville Historical
Society). The oval is fitted to the 1:62,500 sheet after aligning the sheet's ink to today's streets by
cross-correlation (`tools/align.py`: shift +100 m E, +194 m N; the early 15′ surveys were not on NAD27 control). Size
from the fit: 629 × 243 m between inner-line centres (documented 2,000 × 900 ft). Track width 18 m and the infield
grass are estimates.

**2026-11 (second batch): buildings from the 1911 Sanborn** (Oakland 1911-12 vol. 3, "including Emeryville",
sheets 321, 323–325; the track was "closed for racing May 1911"). Sheet 325 is fitted to today's Park Ave crossings
(Holden, Horton, Hubbard, Halleck; similarity, residuals ≤ 2.1 m), sheet 324 joined to it by the covered walk to the
grandstand drawn on both, sheet 323 to 324 by two hydrants drawn on both. 39 buildings: the grandstand with betting
ring and paddock (15 m, estimated), the covered walk, club house, the stall quadrangle (Holden – Horton), the
Burns & Waterhouse and another private racing barn, 16 stable barns (A–K), stable hands' rooms, the SP race-track
station platforms, restaurant, warehouse; all 24 Oct 1896 – 15 Dec 1915 (some stables may be older). The east curve of
the main track on sheet 321 (circle fit r = 166 m) put the oval 14 m back along its axis and 16.5 m SW of the 1914-sheet
fit, which is now applied (oval ±15 m). Shell Mound Park, next door, is its own site (below).

### Idora Park, Oakland (1903–1929)
Amusement park of the Realty Syndicate (Key System owners) on the block bounded by 56th St, 58th St, Telegraph Ave and
Shattuck Ave (17.5 acres documented; today's block 16.8 acres), opened 16 May 1903, closed Jan 1929 and razed that year;
the Idora Park tract (57th St, Aileen St, Carberry Ave cut through it) is on the Oct 1931 "new sheet" 293 of the 1950
volume. From the 1911 Sanborn sheet 293 (Oakland vol. 3), fitted by an affine of the four block corners to today's
parcel block (residuals 0.9–1.5 m): 36 buildings by colour (frame = yellow, concrete = blue) — the 2-storey theatre /
opera house with stage and balcony (the Wigwam / Idora Park Opera Company; 13 m, estimated), the roller-skating rink
(open-air floor inside), the Scenic Railway station, the restaurant, the "Shooting the Rapids" / "Tickler" building, the
merry-go-round, the Telegraph Ave and Shattuck Ave entrances, the moving-picture theatre, the band stand, monkey house,
concessions, the ice-cream factory and shops — plus the figure-eight coaster (hand-traced centreline, 4 m track) and the
Scenic Railway trestle loop as structures, and as ground parts the park block, the electric-car "Auto Race Course"
(with its inside) and the open-air amphitheatre platform. All dated opening – razing (the 1911 layout; rides changed
often: ESTIMATE). The 1904–06 ball park (Oakland Oaks) inside the park is not traced.

### Neptune Beach and the Alameda west-end baths (1878–1953)
* **The bath houses** of the 1880s–1950s between Fifth St, Webster St and the bay, from the Sanborn maps of Alameda
  1897 (sheets 11, 12, 15) and 1948 (same sheets), each sheet fitted by an affine to the parcel block north of Central
  Ave (residuals ≤ 0.9 m; the bath houses south of Central lie outside the fitted block: ±5 m). Sandy Beach Baths,
  Alameda Baths and Green Arbor Baths (dressing-room rows on piers, Green Arbor's open swimming tank) from 1897;
  Sunny Cove Baths (1878 – 1950, Alameda Post) and the Cottage Baths (1895 – c.1953) in their 1897 layout (tub baths,
  dressing rooms) and their 1948 layout (concrete swimming tanks, lunch room, canoe house, club house); the 1897 →
  1948 switch is set to 1922 (midpoint, ESTIMATE); the Cottage Baths are gone on the 1959 sheet (1958 photos → end
  1953, ESTIMATE). The Terrace Baths (Robert Haley 1878; glass-roofed swimming tank, laundry, 300 dressing rooms per
  the Alameda Post; a planked "enclosed swimming tank" of bay water) end at Neptune Beach's opening (1916, ESTIMATE).
* **Neptune Gardens** (Aux Bon Vivants restaurant May 1880, the Long Branch Baths, reopened by the railroad / James Fair
  28 Jun 1885 with a $60,000 pavilion for dancing, roller skating and theatre — "formerly Neptune Garden, pavilion not
  used" on the 1897 sheet): house, summer houses, sheds, windmill and the pavilion (1885–1914, identification and end
  ESTIMATED from the Alameda Post's "Wigwam demolished 1914"), and the grounds between the Terrace Baths and Webster St.
  "Croll's Gardens" was the same resort's later name (John Croll's hotel / bar across Central Ave is not traced).
* **Neptune Beach** (Robert Strehlow, August Freese, Pete Peterson: "New Surf Beach" with the 1915 PPIE Scenic Railway,
  barged over and rebuilt, opened 7 May 1916; Neptune Beach from 31 Mar 1917; Alameda Park Co. 1922; foreclosed 7 Apr
  1939, sold 30 Sep 1939, auctioned 25 Mar 1940, demolished by Nov 1940; McKay Ave laid on the coaster's footprint;
  the U.S. Maritime Service training station took the site in 1942). **No Sanborn sheet shows the park** (the 1897
  edition predates it; the 1948 edition shows the site as government land). Its ground is the fill on the USGS
  Oakland West 1949 sheet (1946 photos) between Central Ave, the shore west of McKay Ave and the fence line east of
  Webster St (Neptune Court's bungalows from the 1948 Sanborn are left out). The features are **placed** from two
  aerial photographs (1930s, Alameda Museum via the Alameda Post; c.1930, EBRPD Crab Cove tour) — the big pool
  (~100 × 40 m) and the first pool east of the coaster, the bathhouse along Central Ave, the arcade entrance at McKay
  Ave, the Moorish tower on Webster St, the PPIE coaster along McKay Ave, the "Whoopee" coaster along the west edge, the
  8,000-seat stadium (oval and grandstand) and the picnic lawns — all `estimated`, ±20 m; the second pool, stadium and
  Whoopee from 1925 (after the 1922 buy-out, ESTIMATE). Not traced: Kiddieland, dance hall, carousel, Ferris wheel,
  the cottages.

### Shell Mound Park, Emeryville (1877–1924)
Edward Wiard's picnic and amusement park on and around the Emeryville shellmound, next to his race track: the octagonal
dance pavilion on top of the mound (90 ft across, 1877; with its bar) and the ground-level dance pavilion with stage
(rebuilt after the fire of 26 Feb 1901), the dining room / bars / bowling alley along the railway, the grandstand round
its athletic track, merry-go-round, band stands, shooting gallery, photo gallery; closed 1924, land sold for factories
(Emeryville Historical Society; Oakland Tribune 7 Aug 1949). Buildings and the mound's "bottom line" from the 1911
Sanborn sheets 323 / 324 (fit as for the race track: ±5–15 m); grounds outline approximate (sheet fence lines).
Today's Bay Street centre stands on it.

### Oaks Park, Emeryville (1913–1957)
"Oakland Base Ball Association grounds, from plans Feb. 1913" on the Sanborn Oakland 1911–Oct 1950 vol. 3 sheet 317
(Park Ave, San Pablo Ave, 45th St, Watts St extended), fitted by an affine of four water-main / street crossings
(residuals 1.3 m): the roofed wood grandstand (L-shaped, behind home plate at San Pablo Ave / 45th St), the bleachers
along San Pablo Ave, left field, Watts St and the Park Ave corner (hand-traced), and the field. Home of the Oakland Oaks
(PCL) 1913–1955; demolition year c.1957 ESTIMATED; site now Pixar's campus.

### San Francisco race tracks
* **Bay District** (Sep 1874 – last race 27 May 1896; streets cut across the infield by 1898; OpenSFHistory, Richmond SF
  Blog): the oval drawn on the USGS San Francisco 1:62,500 sheet of 1895 (1894 survey) — narrow at the north end, wide at
  the south — read on a NADCON render and placed by an affine of the four boundary-street corners on the sheet (First
  Ave / Fifth Ave × Fulton St / Point Lobos Ave) onto today's centreline crossings (Arguello, 5th Ave, Fulton, Geary;
  the periodic Richmond grid defeats cross-correlation). Outer perimeter 1.65 km (a mile track), width 14 m estimated,
  infield and grounds as grass. No buildings (stands / stables not on the sheet).
* **Ingleside** (28 Nov 1895 – 1906; refugee camp after the earthquake, never reopened; bought 1910 for Ingleside
  Terraces): Urbano Drive "was paved along the loop of the old track" (1912) — a stadium fitted to its centreline (rms
  0.25 m, perimeter 1.48 km) is the track's centre line, track 22 m wide (ESTIMATE), infield grass. No buildings traced.
* Neither SF site has buildings here; `region_predecessors.py` reads `buildings.geojson` for the five counties.

### Russell City, Hayward (1907–1966)
Unincorporated Black and Latino community west of Hayward (named 1853; laid out 1907, 700 lots sold by 1908; ~1,400
residents when Hayward declared it blighted in the 1950s; annexed 1964, residents evicted by eminent domain 1964,
last buildings cleared 1966; industrial park, Russell City Energy Center 2013 — Wikipedia). Town = the urban tint of
the San Leandro 1:24k sheet of 1959 (1958 photos; 0.53 km²), `urban` 1908–1965.5, then `industrial` from 1968 (the 1968
photorevision shows the old street grid without buildings or tint). 395 houses at the building symbols of the 1947
sheet (footprint 9 × 9 m ESTIMATE, see Method); start 1925 where the Hayward 1:62,500 sheet of 1942 (1939 photos,
aligned by cross-correlation) has ink within 12 m, else 1943; ends spread over 1964.5–1966.5. The old street grid is
not drawn (it differs from today's industrial streets; the roads layer has no historic streets here). Not traced: the
church, school and the Country Club / hotel (burned 1964 / 1966).

### Geneva Drive-In, Daly City (1950–2002)
The dashed outline labelled "Drive-in Theater" south of the Cow Palace on the San Francisco South 1:24k sheet of 1956,
read by hand (±10 m), minus the Cow Palace annex inside it; opened 1950 (Syufy, 771 cars, on a former greyhound track),
closed 1999, demolished Mar 2002 (Cinema Treasures).

### Downtown Oakland: the Trans Pacific Centre blocks (1978–2004)
Asked: were the blocks 9th–11th St, Broadway–Franklin empty from the 1970s to the 1990s–2000s? Findings: in 1950 both
blocks (and the Franklin–Webster double block east of them) were fully built (Sanborn vol. 2 corrected to Nov 1950,
sheets 150/151: garages, stores, hotels, a church hall, the 1916 T & D Theatre). The T & D closed 1977 and was razed in
1978 (PCAD, Cinema Treasures); on the USGS Oakland West photorevision of 1980 (1979 photos) the 10th–11th St block is the
only block east of Broadway without the built-up tint. The Trans Pacific Centre was planned (SF Examiner 22 Nov 1981)
as "a four-block square office and retail complex" across Broadway from the Hyatt / convention-centre site; phase I,
1000 Broadway (6 storeys), was finished in 1982; phase II (a 68-storey tower and two 30-storey residential towers on
"3 of 4-block square site", Draft EIR Feb 1982) was never built. 10th St between Broadway and Franklin was closed (it
is not in today's street data). The rest stayed redevelopment-agency land until the EBMUD building (dedicated 1991) and
Pacific Renaissance Plaza (1993) east of Franklin and the Courtyard by Marriott (2002) and Franklin 88 (2004; the agency
sold the land in 2000 and bought back 135 public parking spaces) west of it. Surface use while vacant: parking
(ESTIMATE). Rows `oak_trans_pacific_10th_11th` (cleared 1977.5–1978.9), `oak_trans_pacific_9th_10th` and
`oak_chinatown_franklin_webster_9th_11th` (1979.5–1982.0, ESTIMATE) in `data/manual/redevelopment_areas.csv`; the
vacant / parking parts here (`oakland_trans_pacific_lots`, then `urban` from the new buildings' start).

## Road segments (`road_segments.csv`)
For every Overture road segment on a site part that ended (and every non-arterial segment inside Apple Park):
`segment_id, file, cls, name, site_id, inside_m` (metres of it on the site), `on_last_sheet` (share of 5 m samples
with road ink within 4 m on the site's last topo sheet before demolition), `action` (`keep` = drawn on that sheet,
it existed; `date` = it cannot predate `not_before`), `not_before`, `evidence`.

* Bay Meadows: 136 segments to date — the Phase I streets (Franklin Parkway, Park Place, Yates Way, Wayne Way, …)
  not before **1999**, the Bay Meadows II streets (Derby Ave, Landing Ave, Kyne St, Delaware St extension, …) not
  before **2010**; Saratoga Drive and East 28th Avenue were drawn on the 1993 sheet (keep). The roads dated by
  "buildings along them" would otherwise pick up the 1951 stable barns.
* HP / Apple Park: the ~10 `unclassified` **Apple Park Way** segments (and `Wolfe Road` stub inside the outline) are
  the campus ring/perimeter road — real, but **not before 2017**; N Tantau Ave and the Pruneridge stubs existed.
  Apple Park's footways / paths / service aisles are not in `roads_local` and are drawn as `sites.geojson` parts.
* Tanforan (not before 1965), Ford Milpitas (not before 1983: Great Mall Parkway etc.), Marine World (Oracle Parkway,
  not before 1986), Frontier Village (Saddle Brook Drive, not before 1981), Naval Supply Center (today's port roads,
  not before 2000), Emeryville track (the 1915 industrial streets across the oval, not before 1916).
* Second batch (`tools/roadseg2.py`; no ink test — boundary streets drawn on the Sanborn / topo sheets are `keep`, the
  rest `date`): Idora Park (57th St, Aileen St, Carberry Ave through the park: not before 1930), Neptune Beach (McKay
  Ave on the coaster's footprint, Crolls Garden Court, Garden Way, Webster St south of Central: 1941), Shell Mound Park
  (Bay St, Ohlone Way, Shellmound St: 1925), Bay District (2nd–4th Ave, Cabrillo, Balboa, Anza across the track: 1898;
  the four boundary streets keep), Ingleside (the Ingleside Terraces streets: 1911), Russell City (the industrial-park
  streets: 1966).
* The ink test can be fooled where building symbols crowd a road (stable rows); `evidence` gives the numbers.

## Not done / next
* Neptune Beach's real layout (no Sanborn or topo sheet shows the park: a georeferenced 1930s aerial would replace
  the placed features); the 1942–c.1956 U.S. Maritime Service training station on its site (buildings on the 1949 /
  1959 sheets).
* Camp Fremont (Menlo Park 1917–19, ~1,125 temporary buildings on 7,200 acres): no map of the camp was found from the
  build environment (Wikipedia gives no boundaries); the Alameda municipal airport / Pan Am China Clipper base (1927–39)
  under NAS Alameda: not on any available sheet (the 1:62,500 1932 / 1947 imprints are unrevised 1915 content).
* Other drive-ins (Burlingame, Island Auto Movie, Mission, Capitol…), Agnews State Hospital's demolished wards, the
  Libby's / Del Monte canneries, Russell City's old street grid and public buildings, Idora's 1904–06 ball park,
  Freeman's Park (Emeryville ball park 1899–1912).
* Industrial and military sites (Kaiser yards, Oakland Army Base, Hamilton Field, …) are in `../industrial_sites/`.
* Landmark models for the Bay Meadows / Tanforan grandstands, Idora's theatre, Neptune Beach's tower and coasters.

## Licences
USGS topographic maps: public domain. Esri World Imagery (Wayback): viewed for tracing only, no imagery
redistributed. OpenStreetMap-derived parts (`apple_park*`, `traced/apple_park_*.geojson`, road segment ids): ODbL 1.0,
© OpenStreetMap contributors (the files are derived databases: ODbL). Facts from Wikipedia (CC BY-SA), PCAD, HP
Museum, Densho, Cinema Treasures, DRF, GlobeSt: cited per feature. Sanborn maps (Library of Congress): public
domain. Photographs of Neptune Beach (Alameda Museum / Alameda Historical Society): viewed for placement only, not
redistributed.
