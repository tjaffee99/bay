# Airport history: SFO, OAK, SJC (`data/manual/airports/`)

`pipeline/airports.py` dates all of an airport's pavement by one opening year (`data/tables/airports.csv`),
and the airport buildings carry roll or imputed years. This folder dates the pieces separately:
each OSM runway / taxiway / apron (Overture 2026-10-21.0 `region_airports.parquet`) by the phase that
built it, runway lengthenings as intervals along the runway, today's airport buildings with
researched or map-edition years, and the buildings and runways that are gone.

Evidence: **USGS historical topographic editions** (TNM Access / HTMC GeoTIFFs, resampled into one
north-up metre frame per airport with the sheet registration + NADCON, quads clipped at their
neatlines - `tools/render.py`), plus the documented dates below. Anything read off a map or inferred
is `estimated`; a date stated by a source is `documented`.

| airport | frame (lon, lat) | editions (aerial-photo / revision year) |
|---|---|---|
| SFO | -122.377, 37.617 | 1:24k Montara Mountain / San Mateo / San Francisco South / Hunters Point: 1946 photos (1947-50 eds.), 1956, 1968 PR, 1973 PR (Hunters Point: 1968 photos), 1979-80 PR, 1993; 1:62,500 San Mateo 1943 |
| OAK | -122.222, 37.722 | 1:24k San Leandro: 1947 (1948 ed.), 1958 photos (1959 ed.), 1968 PR, 1973 PR, 1979 PR, 1993; Hayward 1:62,500 1942 (1939 photos) |
| SJC | -121.930, 37.363 | 1:24k San Jose West + Milpitas: 1948 photos (1953 eds.), 1960 photos (1961 eds.), 1968 PR, 1973 PR, 1979 PR (no later 1:24k edition) |

## Files

### `pavement_dates.csv` (564 rows: 511 OSM features - SFO 275, OAK 159, SJC 77)
One row per feature, or several when the feature spans construction phases:

| column | meaning |
|---|---|
| `airport, feature_class, overture_id, name` | Overture id (match on this), class (runway / stopway / taxiway / taxilane / apron), OSM name / ref |
| `runway` | runway designation for runway + stopway pieces |
| `lon, lat` | a point on the feature (representative point) |
| `part` | `whole` = the whole feature; `axis_interval` = the part of a runway / stopway line between `d0_m` and `d1_m` metres from `from_end` (end points `part_lon0/lat0` -> `part_lon1/lat1`); `zone_clip` = the part of the feature inside zone `clip_zone` of `pavement_zones.geojson` (taxiways / aprons crossing a phase boundary) |
| `start_year, end_year` | when that part was built (end 9999 = still there) |
| `confidence` | `documented` (year stated by a source) or `estimated` (map edition midpoints, inferred) |
| `source_url, evidence` | source and the reading (`[zone id]` for zone-dated features) |

### `pavement_zones.geojson`
The dated zones (`kind = zone`, effective non-overlapping polygons; a later zone wins where drawn zones
overlapped) and every runway phase as a polygon (`kind = runway_phase`, the axis interval buffered to
the runway width). `zone_clip` rows refer to `zone`.

### `vanished_pavement.geojson`
Runways gone from today's map: Mills Field's 1927 dirt strip, Runway B (1927.35-1944, see *Mills Field 1927-41* below), the north end of Mills Field's north-south runway (1931-1962, marked '4'
on the 1946 sheet; on the tidelands reclaimed in the early 1930s, so not the 1927 strip - see *Ground under
SFO* below), OAK's NAS diagonal runway (1944-1986). Polygons at runway width, `start_year / end_year / width_m / confidence /
source_url / note`.

### `buildings.csv` (97 rows) - columns of `data/tables/known_building_dates_region.csv` + `overture_id, confidence`
`lat / lon` is a point inside today's footprint (Overture `region5_building`), so the point-in-footprint
join of `region_buildings.known_dates()` matches it. SFO rows are San Mateo County (region footprints).
* 25 documented / identified buildings (terminals, towers, hangars, maintenance bases, Coast Guard air station);
* 72 edition-dated footprints: **no roll year** (exempt airport property: the pipeline year was imputed from
  neighbours) and drawn on a topo edition **earlier** than that imputed year; start = midpoint of the
  last edition without it and the first with it (it must stay drawn on later editions). Only positive
  evidence overrides (a footprint *missing* from an edition is not used: hatched terminal symbols are
  missed by the detector). SJC's south-east GA area, rebuilt in the 2010s, is excluded.
  Evidence per footprint and edition: `tools/evidence/footprint_editions_<AP>.csv` (`P`/`-` +
  solid / raw ink shares).

### `vanished_buildings.geojson` (64) - same properties as `data/manual/vanished_sites/buildings.geojson`
`site_id` = `airport_sfo / airport_oak / airport_sjc`. Traced on a reference edition inside windows
checked by eye (`tools/trace.py`), dated by presence on every edition: SFO's west-side buildings along
the old Bayshore Highway (to 1961), a hangar NW of the Central Terminal, South Terminal rotundas
(Rotunda A 1974-2007, Boarding Area B rotundas 1963-2017); OAK's NAS Oakland / North Field buildings that
are gone; SJC Terminal C (1965-2010, outline from the 1979 PR), the south-east T-hangar rows (to 2000)
and an early (1946-) building. Heights / storeys / material are estimates by use.

## Key dates (sources in the rows)

**SFO** - Mills Field dedicated 7 May 1927 (one dirt strip), runway C 1,900 -> 3,000 ft 1935, paved runways
by 1937, three runways "forming a triangle" by 1936; Coast Guard Air Station 15 Nov 1940 / 15 Feb 1941;
Army lease 5 Feb 1942, wartime hydraulic fill and "three hard-surfaced runways, the longest 8,000 ft"
(USACE 1991 via militarymuseum.org) - the four-runway layout is on the 1946-photo sheets (core dated
1944, estimated); Aug 1952 chart 1L 7,000 / 1R 7,750 / 28L 6,500 / 28R 8,870 ft; south ends of 1L/1R after
1952 (1956 sheet); 28L lengthened 1961 (both ends, onto new fill); 28R extended 1968 (east, paved on the
1973 PR -> 1969) and the west ends over the old highway / hangar row (1962); 1R north extension onto the
NE fill (1962). Central Terminal 27 Aug 1954; South Terminal 15 Sep 1963; Superbay c.1970-71; North Terminal
1979 / Boarding Area E 1981; International Terminal Dec 2000; BART 2003; Harvey Milk T1 2019-24.

**OAK** - North Field: 7,020-ft runway built June 1927 (today's 10L/28R alignment, 1927), dedicated
17 Sep 1927; five hangars, terminal and inn 1927-30; Boeing School 1929 (its hangar, Building 621, 1939-40);
Navy (NAS Oakland) 1943-46: runway 15/33 and the diagonal, repaved taxiways (1944, estimated); 6,200-ft
parallel runway 10R/28L 1945. South Field on the 1960-62 dike fill: 10,000-ft runway (now 12/30) and
Terminal 1, 1962; World Air Center hangar 1973; FedEx Metroplex 1988; Terminal 2 1985 (concourse 2006);
tower 2013.

**SJC** - dirt runway 1945 (Nissen), first permanent runway 1948 (4,500 ft), dedicated 1 Feb 1949;
1961: west runway +2,500 ft and a new 4,400-ft east runway (12L/30R); 12R 6,312 ft 1964, 7,787 ft 1965,
8,900 ft late 1960s, 10,200 ft by 1996; 12L/30R extended to 11,000 ft Aug 2001, 12R/30L Oct 2004;
GA runway 11/29 1970s (now Taxiway V, still drawn as taxiway in OSM: dated 1970); Terminal C 1965 (south
concourse 1969) - 2010; Terminal A 1990; Terminal B + rental car garage 2010.

## Integration (suggested)

1. **Pavement** (`pipeline/airports.py`): after building `f` (and before the land-year check), join
   `pavement_dates.csv` on `overture_id`:
   * `part == whole`: the feature's `start/end` = the row's (instead of the airport's `opened`);
   * `part == axis_interval` (runways / stopways): cut the buffered runway polygon into pieces with a
     rectangle from (`part_lon0, part_lat0`) to (`part_lon1, part_lat1`) (wider than the runway), one
     piece per row with its year; or clip with the matching `runway_phase` polygon of
     `pavement_zones.geojson` (same interval);
   * `part == zone_clip`: intersect the (buffered) feature with the `zone` polygon named `clip_zone`;
   * keep `max(start, land_year + 0.5)`; centre lines (`airport-lines.bin.gz`) per piece the same way.
   Add `vanished_pavement.geojson` like `airports_extra.geojson` (polygons with their own start / end).
2. **Buildings**: add `data/manual/airports/buildings.csv` to the `tabs` list of
   `region_buildings.known_dates()` (same columns; extra columns are ignored).
3. **Vanished buildings**: read `vanished_buildings.geojson` like `vanished_sites/buildings.geojson` in
   `region_predecessors.py` (same properties; `use` hall / dwelling / other).
4. `data/tables/airports.csv` is consistent with these files (SFO 1927, OAK 1927; SJC 1945 = the dirt
   strip, paved runway 1948) - no change needed. `airports_extra*.geojson` (NAS Alameda, Crissy Field) is unrelated.

## Mills Field 1927-41 (2026-11)
The field had lettered runways from the start; none is drawn on a topo sheet (the 1939-photo 1:62,500 sheet omits the
airfield), so their places are read from documents and the 1946 sheet:
* **Runway B**, the runway dedicated on 7 May 1927: '5,770-foot-long, dirt-surfaced' (SFO Museum; negative of 5 Jan 1928
  inscribed 'RUNWAY B 5,770 FT LONG'; the first graded strip was 4,950 ft). Placed on the 150-acre pasture east of the
  Bayshore Highway, parallel to the highway ~250 m east of it, 1,759 m NNW from the south end of the 1939 dike - the
  'original dirt-paved North-South runway' / 'diagonal runway Northwest to Southeast' of the 1930-37 aerial films.
  `vanished_pavement.geojson`, 1927.35-1944, 60 m wide; position, width and end ESTIMATED.
* **Runway C** ran with 'the prevailing west-northwest winds' and was extended 'from 1,900 to 3,000 feet' in 1935 (New Deal;
  SFO Museum) - onto the tidelands reclaimed in the early 1930s. The WNW runway of the 1946 sheet lies on the axis of
  today's 10L/28R (+-80 m), so 10L/28R d 350-929 m is dated 1928 (estimated: lettered runways by Jan 1928) and d 929-1264 m
  1935 (documented); the rest stays the 1944 wartime core. Land check (fillcheck intervals): pasture ~1912, extension <= 1934.
* The north end of the N-S runway '4' (1931-62) is unchanged.

## Ground under OAK and NAS Alameda (2026-11) - `data/manual/fill_zones.csv` `al_*`
The 1927 box under OAK (every c.1800 marsh / flat cell of -122.23..-122.195 x 37.715..37.735 that is land today became land
in 1927, i.e. also the 1958-62 South Field and the Hegenberger marsh) and the Bay Farm / South Field / NAS / NSC boxes are
replaced by phases read off the editions (`../fill_README.md`, *Alameda Point … Oakland Airport*). All 159 OAK rows of
`pavement_dates.csv` keep their researched start years with the new zones (1927 North Field pieces wait for their ground
until 1927.5-1927.8 at most; 1945 10R/28L on the 1941.5-44.5 Navy strip; 1962 South Field on the 1958.5-61.5 dike fill).

## NAS Alameda pavement (`../airports_extra.geojson`, `tools/nas.py`)
The NAS runway / taxiway / apron polygons (today's pavement at Alameda Point) are cut at the shore of the 1946-photo sheet:
inside 1941 (the station's field, 5 paved runways on the 29 Jul 1946 aerial), outside 1957 (west / south additions for the
lengthened jet runways, on the 1958-photo sheet); every piece ends 9999 - the airfield closed 25 Apr 1997 but its runways,
taxiways and ramps are still there ('a 4/2/18 aerial view ... shows the NAS Alameda airfield remained almost completely
intact', airfields-freeman.com). The airport outline (`data/tables/airports.csv`) still closes in 1997. Not modelled: the
Alameda Airport (1929-39; 3 shell / graded runways, the longest 3,250 ft E-W) and Benton Field runways.

## Ground under SFO (2026-11) - `data/manual/fill_zones.csv` `sm_sfo_*`

Pavement waits for its ground (terrain land-year grid), and the two old SFO fill boxes (1927.2-1945 west of
-122.386, 1941-1965 east of it, years spread across each) put the ground under the 1930s field in the
1950s. They are replaced by one zone per phase, read off the editions in the SFO frame (water-tint masks of
the 1946 / 1956 / 1968 PR / 1973 PR sheets, the 1939 dike traced by hand on the 1:62,500 1943 edition, the
c.1800 marsh from the SFEI poster):
* **Mills estate marsh pasture** (tidal marsh to the railroad on the 1892 survey, drained pasture on the
  1939 sheet), 1905-15 ESTIMATED: the part inside the 1939 dike is 152 acres, i.e. the 150-acre "cow
  pasture" leased in March 1927 - Mills Field of 1927 is on land from the start;
* **tidelands reclaimed in the early 1930s** (the rest of the 1939 dike, 230 acres; "350 acres of
  tidelands reclaimed" by 1935), 1930.5-35 - the N-S runway '4' lies here (land c.1934);
* WPA seaplane harbour / Coast Guard Air Station 1936-40.5; 1939 extension + wartime hydraulic fill
  1939.5-43.5 (field of the 1946 sheets); NE fill 1946.5-50.5; small 1946->56 shore pieces 1947-52.5;
  28L extension 1957-60.5; 1R north extension 1957-61.5 (Hunters Point 1968 PR, read by hand: its purple
  revision ink defeats the water mask); 28R extension 1968-68.5.
Each zone ends half a year before the researched pavement on it. Check without a terrain run:
`cd pipeline && ../.venv/bin/python ../data/manual/airports/tools/fillcheck.py` (land year at the Mills
Field points and under every SFO row of `pavement_dates.csv`). With the new zones 296 of the 301 SFO rows
keep their researched start (before: 215); the rest wait for their ground as the maps show: 3 taxiways
dated 1944 by the coarse SFO-1946 zone lie beyond the 1946 shoreline (bay until the 28L fill, c.1960), a
NE stopway (1944; Hunters Point quad not mapped in 1946) on the NE fill (c.1950), a 1961 taxiway on the
1968 mud (1968.5).

## Point-only airports and Crissy Field (`pipeline/airports.py`, `../airports_extra*.geojson`)

* An airport that OSM maps only as a point (no aerodrome outline: San Rafael Airport, Meadowlark Field
  in Livermore) gets an outline from the runways / taxiways / aprons nearer to it than to any other
  airport within 1.5 km (convex hull + 40 m), so its pavement is kept and the terrain shows airfield
  grass. Opening years: San Rafael 1972 (early 1970s per the Marin History Museum; not on the Novato
  1968 PR, "LANDING STRIP" on the 1980 PR), Meadowlark 1958 (between the Altamont 1953 / 1949-photo
  edition and its 1968 PR) - both ESTIMATED.
* **Crissy Field** (Presidio, Army airfield 1921-74, not in Overture): `tools/crissy.py` writes the
  outline (the open field on the 1946-photo San Francisco North sheet + the runway) and the paved runway
  6/24 in two pieces with their own years (`start_year / end_year` in `airports_extra.geojson`, honoured
  by `airports.py`): east part 1947.5-1999 (7/1946 aerial unpaved, 8/1948 paved; the 1956 sheet's strip),
  west 180 m 1958-1999 (not on the 1956 sheet; 2,900 ft paved on the 1959 chart; the 1968 PR outline,
  ~790 x 28 m). The grass field of 1921-c.1947 is the outline's airfield grass (terrain). The 1915 PPIE race track /
  polo, athletic and aviation field is the vanished site `ppie_west_end` (`../vanished_sites/`). Not modelled: the WWII
  temporary buildings 901-919 at the field's ends (no footprints), and the field over today's Crissy Marsh
  (terrain: the marsh is water today, so the 1912-15 fill zone never makes it land - needs a terrain change).

## Limits

* Runway interval ends are read to about +-75 m; the SJC 1953 sheets (1948 photos) are registered
  to +-30 m. The 1927 Mills Field strip and the 1930s SFO field are not on any 1:24k edition: only the
  north end of the N-S runway is drawn (vanished); the rest of the 1930s pavement is assumed under today's NW field
  (dated with the 1946 field, 1944), except Runway B (1927 strip, vanished) and Runway C (west end of 10L/28R, 1928 / 1935):
  see *Mills Field 1927-41*.
* Topo editions draw buildings as symbols (solid, hatched, purple); footprints under 150 m2 are not dated.
  Photorevisions seldom delete demolished buildings, so some ends are late. Identities of vanished
  buildings are generic unless named.
* OAK North Field taxiways are dated to the Navy era (1944, estimated) as a block; the 1927-40 North
  Field taxiways under them are not separated.

## Tools (`tools/`, scratch-level; renders go to a scratch folder)
`render.py` (topo mosaic in a local frame, `--npy`), `gridview.py`, `crops.py`, `rwyticks.py`, `strip.py`,
`montage_px.py`, `overlay.py` (reading aids), `presence.py` + `corridor.py` (pavement on each edition ->
`evidence/pavement_editions_<AP>.csv`), `bpresence.py` + `bdate.py` (footprints on each edition ->
`evidence/footprint_editions_<AP>.csv`), `zcheck.py`, `qa_build.py`, `qa_trace.py` (QA maps),
**`build.py`** (runway phases, zones, feature overrides -> `pavement_dates.csv`, `pavement_zones.geojson`,
`vanished_pavement.geojson`), **`buildings.py`** (-> `buildings.csv`), **`trace.py SCRATCH`** (->
`vanished_buildings.geojson`; needs the `.npy` renders and `<AP>_bldg.geojson` in SCRATCH, see its header),
**`fillcheck.py`** (SFO land years from the fill-zone rings, no terrain run), **`crissy.py`** (Crissy Field ->
`../airports_extra*.geojson`), **`nas.py`** (NAS Alameda pavement phases in `../airports_extra.geojson`).
