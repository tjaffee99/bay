# Landmark research — Santa Cruz County, south Santa Clara Valley, east Contra Costa (`viewer/src/landmarks/coastsouth.ts`)

Companion to `landmarks_southbay.md` / `landmarks_eastbay.md` (2026-11 ship-quality pass for the new counties). Rows for every
model are in `data/tables/landmarks_coastsouth.csv` (same columns as `landmarks_southbay.csv`, CRLF; `start_year` = completion /
opening year, `end_year` = removal or 9999). The models are exported as `COASTSOUTH: Landmark[]` (registered in `landmarks/index.ts`).

## Method
- **Outlines**: OpenStreetMap ways / relations read from the OSM API (small bounding boxes, downloaded 2026-11-10; © OpenStreetMap
  contributors, ODbL) — the same outlines Overture 2026-10-21.0 carries in `region4_building.parquet` / `region5_building.parquet`,
  plus what Overture's building theme lacks: the wharf and pier polygons, the roller-coaster track, the chairlift line, the hull of
  the SS Palo Alto. Each model is built in a frame aligned with the building (`b.frame(0, 0, 0, bearing)`).
- **Heights and placement are measured, not estimated from photographs**: USGS 3DEP lidar point clouds (public domain) —
  `CA_SantaCruzCounty_2020`, `CA_SantaClaraCounty_2020`, `CA_ContraCosta_1_2022` — read from the public Entwine tiles
  (`s3://usgs-lidar-public`, the reader of `pipeline/lidar_parts.py`). For each structure: height maps in the building frame,
  extents of each roof level (1.5–98.5 % of the returns in a height band), tower widths by height band, heights along the coaster
  track. Where the lidar and the OSM outline disagree (Holy Cross Church ≈ 6 m, Del Mar Theatre ≈ 3 m, Villa Mira Monte ≈ 3 m,
  mission replica ≈ 1.5 m, Gilroy's Old City Hall: front 4.5 m short) **the model follows the lidar and `replaces` follows the OSM
  outline** (it has to cover the centroid of the generic footprint it hides).
- **Documented dimensions** (Wikipedia, lighthouse lists, NRHP / HABS figures quoted there, local histories; URL per model) were
  checked against the lidar wherever the structure stands: Giant Dipper lift hill 70 ft = 21.3 m → lidar 21.2 m above the
  Boardwalk; Mark Abbott lighthouse 39 ft = 11.9 m → 11.6–12.0 m; Walton lighthouse 41.5 ft = 12.65 m → 12.8 m; Felton Covered
  Bridge 35 ft = 10.7 m → ridge 10.5 m above the lidar bridge deck; Seacliff pier 630 × 40 ft → 190 × 12.2 m; Capitola Wharf
  855 ft = 261 m → 264 m; Antioch Bridge main span 460 ft = 140 m → 134 m between the OSM channel-pier fenders.
- **Terrain**: landmarks stand on `elevationAt(anchor)`; wharves, piers, the cement ship and the Antioch Bridge are `kind: 'bridge'`
  (z from sea level; deck levels are NAVD88 from the lidar). Wind turbines sample `elevationAt` at each turbine.
- **Wind turbines**: U.S. Wind Turbine Database (USGS / LBNL / ACP, public domain; API `energy.usgs.gov/api/uswtdb/v1/turbines`,
  queried 2026-11-10 by county FIPS 06013 / 06001): position, hub height, rotor diameter, project year. One merged landmark per
  project; rotors static, facing WSW (245°, the prevailing Altamont wind — estimated).

## Models
| id | kind | completed–end | top (m) | triangles | basis |
|---|---|---|---|---|---|
| `giant_dipper_santa_cruz` | park | 1924.38–today | 21.2 | 2426 | measured |
| `sky_glider_santa_cruz` | park | 1967.4–today | 15.2 | 1200 | measured |
| `boardwalk_casino` | building | 1907.46–today | 18.6 | 328 | LOW |
| `boardwalk_plunge` | building | 1907.46–today | 17.2 | 67 | measured |
| `looff_carousel_santa_cruz` | park | 1911.6–today | 12.3 | 116 | measured |
| `santa_cruz_wharf` | bridge | 1914.93–today | 15.1 | 2148 | measured |
| `mission_santa_cruz_1794` | building | 1794.36–1857.03 | 10.7 | 36 | LOW |
| `holy_cross_church_santa_cruz` | building | 1889.7–today | 45.0 | 118 | measured |
| `mission_santa_cruz_replica` | building | 1931.9–today | 14.4 | 82 | measured |
| `santa_cruz_light_1869` | tower | 1869.95–1948.38 | 12.2 | 92 | LOW |
| `mark_abbott_memorial_lighthouse` | tower | 1967.9–today | 11.9 | 80 | measured |
| `walton_lighthouse` | tower | 2001.95–today | 12.6 | 168 | measured |
| `ss_palo_alto` | bridge | 1930.49–today | 8.0 | 82 | measured |
| `seacliff_pier` | bridge | 1930.45–2023.02 | 6.4 | 420 | measured |
| `capitola_wharf` | bridge | 1857.5–today | 7.0 | 624 | LOW |
| `felton_covered_bridge` | building | 1892.9–today | 14.5 | 100 | measured |
| `santa_cruz_town_clock` | monument | 1976.6–today | 19.6 | 82 | measured |
| `hotel_palomar_santa_cruz` | building | 1929.78–today | 34.1 | 56 | measured |
| `del_mar_theatre_santa_cruz` | building | 1936.6–today | 19.4 | 50 | measured |
| `venetian_court_capitola` | building | 1925.9–today | 8.4 | 253 | measured |
| `st_patricks_watsonville_1903` | building | 1903.5–1989.79 | 38.3 | 95 | LOW |
| `st_patricks_watsonville` | building | 1994.3–today | 38.3 | 95 | measured |
| `gilroy_old_city_hall` | building | 1905.9–today | 18.6 | 144 | measured |
| `villa_mira_monte` | building | 1886.6–today | 9.8 | 94 | measured |
| `antioch_bridge_1978` | bridge | 1978.95–today | 46.3 | 2330 | est. profile |
| `john_marsh_house` | building | 1856.67–today | 12.0 | 134 | measured |
| `john_marsh_house_tower` | tower | 1856.67–1868.81 | 19.8 | 90 | LOW |
| `altamont_patterson_pass_1985` | tower | 1985.95–today | 32.0 | 276 | measured |
| `altamont_diablo_winds` | tower | 2004.95–today | 83.5 | 1426 | measured |
| `vasco_buena_vista` | tower | 2006.95–today | 85.7 | 1748 | measured |
| `vasco_winds` | tower | 2011.95–today | 130.5 | 1564 | measured |
| `altamont_golden_hills` | tower | 2015.95–today | 130.0 | 2208 | measured |
| `altamont_golden_hills_north` | tower | 2017.95–today | 137.9 | 920 | measured |
| `altamont_summit_wind` | tower | 2021.95–today | 148.0 | 1058 | measured |

## Derivations worth knowing
- **Giant Dipper** — OSM maps one 387 m circuit (`roller_coaster=track`, way 123977929); the ride is 2,640 ft (805 m), a double
  out-and-back whose second circuit runs inside / under the first. Heights: highest lidar return within 1.6 m of the centreline every
  4 m, 3-point median, above the Boardwalk's ground level (6.1 m NAVD88, the 90th percentile of ground returns round the ride — the
  median is the beach). Maximum 21.2 m = the documented 70 ft. The trestle is schematic (bents every 8 m). Overture's ML
  footprints under the structure carry the coaster's height (22–25 m): they are hidden (`replaces`) and redrawn as low boxes with
  their lidar roof heights (3–7.6 m).
- **Sky Glider** — OSM aerialway (way 123977926, 262 m each way). Lidar: tower tops 15.2 m above the Boardwalk at x = −202, −148,
  −95 m (54 m apart), cable ≈ 13.6 m between them, stations ≈ 5.5 m. Opening year 1967 (Wikipedia ride table / Boardwalk).
- **Casino and Plunge (1907)** — the roof levels are today's (lidar 2020). The 1907 buildings by W. H. Weeks had Moorish domes and
  were altered; no dated plan of the alterations was found, so one model serves every year (earlier roofline LOW CONFIDENCE). Beach
  Street's palms (20+ m) show in the lidar beside the Plunge: they are not towers.
- **Santa Cruz Wharf** — OSM relation 7063040 (743.5 m over water; 2,745 ft includes the landward approach). Deck 7.0 m NAVD88.
  Ten OSM buildings on the deck as rectangles with lidar heights (3–8 m above the deck). The Dec 23, 2024 loss of ≈ 150 ft at the
  end is in the facts, not in the geometry.
- **Mission Santa Cruz** — church 112 × 29 × 25 ft, walls 5 ft (californiamissions.com; another account, accessgenealogy.com "History of Santa Cruz Mission", gives 30 × 112 ft and 25 ft high with a stone front);
  position: on the axis of Holy Cross Church, which Wikipedia says was built "over (in the same orientation) part of the original
  sanctuary and cemetery" — LOW CONFIDENCE (± 15 m). The 1840 collapse of the tower and the 1857 collapse are in the facts; the 1858
  wooden church next door is not modelled (no dimensions). Villa de Branciforte: nothing with dimensions found.
- **Holy Cross Church (1889)** — lidar: nave ridge 21.5 m, eaves 12.9 m, sanctuary roof 24 m, tower 7.6 m square to 22 m, 5.9 m to
  28.2 m, a 3.7 m stage from 28 to 37 m, spire apex 45.0 m. No published spire height was found; the lidar figure stands.
- **Lighthouses** — first light (1869–1948): lighthousefriends.com (Ediz Hook plans; lit Jan 1, 1870; moved ≈ 300 ft north in 1879;
  1941 framework tower 200 ft seaward; dismantled from May 20, 1948). No dimensions and no mapped position were found: house and
  tower sizes are photo estimates and the anchor is 300 ft north of the tip of the point — LOW CONFIDENCE. Mark Abbott (1967): 39 ft
  (ibiblio lighthouse directory) = lidar. Walton (current light 2001, Wikipedia; year only): 41.5 ft = lidar 12.8 m.
- **SS Palo Alto / Seacliff pier** — sources disagree on 1929 vs 1930 for the grounding (Wikipedia lead: 1929; Santa Cruz Public
  Library and the Seacliff history: towed Jan 21–22, sunk Jan 25, 1930 — used) and on the pier's length (500 / 600 / 630 ft; the
  lidar gives 190 m = 623 ft, 12.2 m wide). The pier ends in 2023.02 (storm of Jan 5, 2023). The hull is drawn whole for every
  year; its break-up (1963 split, 2017 stern) is in the facts.
- **Capitola Wharf** — today's outline for every year since 1857 (450 ft in 1857, 1,200 ft a few years later, 855 ft today; city
  history page). LOW CONFIDENCE before the 20th century. OSM maps the wharf in two pieces (the January 2023 breach): the model joins
  them. The buildings at the head (removed 2024) are left out; nothing in Overture stands there.
- **Felton Covered Bridge** — lidar: bridge-deck class at 80.0 m NAVD88, ridge 90.5 m, eaves 88.0 m, river bed 76 m; roof 54 × 10 m.
  Span: 80 ft (Wikipedia) vs 140 ft (PCAD) — not resolved, the piers are schematic.
- **Town Clock** — no published height; lidar 19.6 m, stepped silhouette 6.4 / 5.6 / 4.7 m.
- **Hotel Palomar** — LocalWiki (established 1928; first building over three storeys), PCAD (dealership opened in the hotel Oct 12,
  1929). Lidar: slab 16 × 38 m at 25 m, penthouse floor 29 m, mast 34.1 m.
- **St. Patrick's, Watsonville** — PCAD: first church 1865–1903; brick church 1903 (W. H. Weeks, City of Watsonville survey);
  rebuilt after Loma Prieta to the 1903 design, dedicated 1994. One mesh for both (lidar of the 1994 church): spire 38.3 m.
- **Old City Hall, Gilroy** — the OSM outline stops ≈ 4.5 m short of the Monterey Street front; the tower (4.5 m square, 18.6 m)
  stands inside that front (lidar).
- **Antioch Bridge (1978)** — Wikipedia / MTC: 9,504 ft, main span 460 ft, clearance 135 ft, 38.1 ft wide, steel plate girder.
  No 3DEP point cloud covers the bridge: the deck profile (crest = clearance + 4.4 m girder, 3.3 % grades, 7.5 m viaduct over
  Sherman Island) is ESTIMATED, and so are the approach piers (every 76 m).
- **John Marsh Stone House** — Wikipedia (Marsh Creek State Park): begun 1853, completed 1856, Thomas Boyd; tower 65 ft; HABS
  CA-1500 floor areas (2,100 sq ft per floor, tower 144 sq ft); tower down in the 1868 Hayward earthquake, wooden replacement down
  after 1906. Lidar 2022: walls 13 × 19 m (= the OSM outline), ridge 12 m, the tower stub (4.3 m square, 14 m) on the west front —
  the 1856 tower is drawn there as its own landmark (1856–1868). The house is drawn complete; today it is a shell under repair.
- **Venetian Court** — Wikipedia: begun 1924, NRHP "built 1925", Henry J. Roth and Wolfe & Higgins. Lidar: roofs 3.1 / 5.2 / 8.0 m
  above the beach in three tiers. One pastel per row (schematic).
- **Del Mar Theatre** — plaque text via LocalWiki (Golden State Theatres, 1936, 1,500 seats). Lidar: auditorium 13.8 m, stage house
  19.4 m, blade sign 18.2 m; Pacific Avenue's street trees (11–14 m) stand in front of the facade in the lidar.
- **Wind turbines** — USWTDB groups: Patterson Pass / Patterson Wind 1985 (6 survivors of 313: Nordtank NTK65, Bonus 65 kW; hub
  24–24.6 m, rotor 16 m), Diablo Winds 2004 (31 × Vestas V47), Buena Vista 2006 (38 × Mitsubishi MWT62/1.0), Vasco Winds 2011
  (34 × Siemens SWT-2.3-101; one in Alameda County), Golden Hills 2015 (48 × GE 1.7-100), Golden Hills North 2017 (20 × GE 2.3-116),
  Summit Wind 2021 (23 × GE 2.7-116). The database has only the year a project went online: turbines appear at the end of that year.
  19 turbines of an unnamed 2026 Alameda County project have no attributes in the database: not drawn. The thousands of small 1980s
  turbines removed since are not in the database: not drawn (said in every group's facts).

## Numeric check (scratch `ship/lm_south/`: `dump_cs.ts`, `compare.py`, `check2.py`, `rastercmp.py`)
- `npx tsc --noEmit`: no error in `coastsouth.ts`. Every model builds in node (finite vertices; 20.7k triangles in all).
- Extent / bearing / top of every model against its OSM outline and the cited dimension (`compare.py`): tops within 0.6 m of the
  lidar or documented figure for all standing models; the adobe church is 10.7 m to its ridge over 25 ft (7.6 m) walls by design.
- Model surface vs lidar surface, cell by cell (`rastercmp.py`; model rasterised from above on a 1–2 m grid, lidar = highest return
  per cell; cells where the model stands): median difference / share of cells within 2 m —
  Casino 0.0 m / 79 %, Plunge +0.3 / 69 %, Looff Carousel −0.2 / 82 %, Giant Dipper (track above 9 m) +0.8 / 64 %, Holy Cross
  +0.5 / 73 %, mission replica 0.0 / 81 %, Mark Abbott +0.2 / 88 %, Walton −0.2 / 76 %, Town Clock +0.9 / 62 %, Palomar +0.3 / 69 %,
  St. Patrick's +1.1 / 68 %, Gilroy City Hall +0.6 / 77 %, Villa Mira Monte +0.5 / 86 %, Marsh house +0.4 / 56 % (a shell under a
  protective roof today), Felton bridge +0.2 / 94 %, Capitola Wharf +0.1 / 81 %, Seacliff pier −0.1 / 95 %, Santa Cruz Wharf
  0.0 / 87 %, Del Mar −0.1 / 89 %, Venetian Court 0.0 / 90 %.
- `replaces`: each polygon hides exactly the Overture footprint(s) of its landmark (list in `compare.py` output); the wharf polygon
  hides the ten buildings redrawn on the deck; the Giant Dipper hides five footprints with bogus ML heights.

## Looked at and left out (no model)
- **Old Antioch Bridge (Jan 1, 1926 – 1978)**: only "two spans each 270 ft", "70 ft clearance raised" and the alignment (the
  fishing pier of the Antioch / Oakley Regional Shoreline stands on its piers: OSM pier way from −121.750709, 38.019539 north to
  38.021023) are documented; no span layout, tower height or length found. Needs a HAER / Caltrans drawing or the 1953 topo.
- **Davenport cement plant**: the plant (1906, closed 2010) still stands; lidar 2020: preheater tower 80.6 m, silos 41–43 m — but
  no source dates the standing structures (the tall tower belongs to a later modernisation). Not modelled.
- **Quicksilver Express (Gilroy Gardens, June 15, 2001)**: OSM track (639 m) is there, but sources give 38, 40 and 60 ft and the
  lidar under the trees is ambiguous (19.9 m maximum over the track, not separable from rockwork). Left out.
- **Pleasure Pier (1904–)**: 400 ft or 450 ft, removal year not confirmed. **Cooper House** (1894 – 1989): no dimensions.
  **El Campanil Theatre, Antioch** (opened Nov 1, 1928): no lidar here and no tower height. **Pittsburg / Antioch power-plant
  stacks**: no dated heights found. **UCSC** (McHenry Library, Quarry Amphitheater, lime kilns), **Watsonville plaza bandstand**,
  **Gilroy Hot Springs**, **Mount Madonna**, **Wilder Ranch**, **Brookdale Lodge**, **depots**: not reached.
