# Vanished large sites (`data/manual/vanished_sites/`)

Big sites that were built after the farms and are gone again — racetracks, an office campus, a car
plant, amusement parks, a drive-in, a wartime camp — leave no trace in today's footprints, so
without this folder the terrain shows orchard / farmland until today's buildings arrive. Each site
is traced from **real historical maps and orthophotos** (USGS historical topographic sheets
1946–1997, the October 2010 orthophoto in Esri's World Imagery Wayback archive, OpenStreetMap for
today's grounds); dates come from cited histories plus the editions on which each feature first
appears. Anything generated or estimated says so in its `confidence` / `note`.

## Files

| file | what |
|---|---|
| `sites.geojson` | Polygon parts of each site's ground over its lifetime (one feature per part and period) |
| `buildings.geojson` | Footprints of vanished buildings (predecessors) |
| `road_segments.csv` | Overture road segments (`roads_local` / `roads_region`) lying on these sites (219 rows), with a *not-before* year where the segment cannot have existed (see below) |
| `traced/*.json` | Intermediate tracings in each site's local metre frame (automatic extractions from the sheets, hand-read corners) |
| `traced/apple_park_osm.geojson` | OSM features of Apple Park (via Overture base / transportation, © OpenStreetMap contributors, ODbL) |
| `tools/` | The tracing tools (see *Method*); `python -I tools/trace_sites.py` rebuilds the two GeoJSONs from `traced/` |

### `sites.geojson` properties
`site_id, name, kind` (racetrack | office_campus | factory | amusement_park | drive_in | military | campus_grounds),
`cover` (what the ground was: `dirt_track | turf | grass | park | parking | industrial | urban | water`),
`surface` (finer label: "dirt track", "turf course", "stable yard", "footpath", "road", "theme park"…),
`year_start, year_end` (fractional years; 9999 = still there), `confidence` (`exact` = position and dates from the
sources; `estimated` = traced but a date or an outline is approximate; `procedural` = generated), `source_url`, `note`.

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
| `emeryville_racetrack` | Oakland Trotting Park / New California Jockey Club track, Emeryville | 4 Jul 1871 – last race 15 Feb 1911 (buildings burned 15 Dec 1915) | San Francisco 1:62,500 (1899 ed., 1914 imprint), shifted 220 m onto today's streets | oval ±30 m; no buildings traced |

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
grass are estimates; the grandstand / stables are not traced (no Sanborn sheet checked).

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
* The ink test can be fooled where building symbols crowd a road (stable rows); `evidence` gives the numbers.

## Not done / next
Neptune Beach (Alameda, 1917–39) and Idora Park (Oakland, 1904–29) predate the 1:24k sheets — Sanborn maps (LOC
Oakland / Alameda volumes) would give their buildings; Oakland Army Base warehouses; Kaiser Richmond shipyard grounds
(1941–46); Camp Fremont (Menlo Park 1917–19); the Libby's Sunnyvale and Del Monte San José canneries; other drive-ins
(Geneva, Burlingame, Mission, Island Auto Movie…); landmark models for the Bay Meadows / Tanforan grandstands (their
footprints are in `buildings.geojson` with estimated heights).

## Licences
USGS topographic maps: public domain. Esri World Imagery (Wayback): viewed for tracing only, no imagery
redistributed. OpenStreetMap-derived parts (`apple_park*`, `traced/apple_park_*.geojson`, road segment ids): ODbL 1.0,
© OpenStreetMap contributors (the files are derived databases: ODbL). Facts from Wikipedia (CC BY-SA), PCAD, HP
Museum, Densho, Cinema Treasures, DRF, GlobeSt: cited per feature.
