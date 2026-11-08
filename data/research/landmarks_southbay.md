# Landmark research — Peninsula, South Bay and Marin (`viewer/src/landmarks/southbay.ts`)

Companion to `landmarks.md`, `landmarks_batch3.md`, `landmarks_batch4.md` and `landmarks_eastbay.md`.
Rows for every model below are in `data/tables/landmarks_southbay.csv` (same columns as `landmarks.csv`;
`start_year` = completion / opening year, `end_year` = removal or 9999).
The models are exported as `SOUTHBAY: Landmark[]`; registration in `landmarks/index.ts` is left to the main session.

## Method
- **Footprints and 3D parts**: OpenStreetMap outlines and `building_part`s via Overture 2026-10-21.0
  (`data/raw/overture/2026-10-21.0/region5_building*.parquet`; © OpenStreetMap contributors, ODbL). Each model is
  anchored on the OSM centroid (or a measured centre) and built in a frame aligned with the building
  (`b.frame(0, 0, 0, bearing)`: +y at `bearing`, +x at `bearing + 90°`); outlines and part heights are copied into the
  model in that frame.
- **Placement check**: every model's top view was overlaid on the OSM outlines and on an orthophoto (Esri World
  Imagery, viewed only, not stored); positions taken from the orthophoto are named in the facts (Apple Park ring centre and
  roof edges, Steve Jobs Theater paving, SAP Center roof, PayPal Park canopies, Stanford Dish, Pigeon Point tower
  base from its shadow, San José City Hall rotunda, Mission Santa Clara bell tower, Marin Civic Center dome).
- **Hipped roofs on complex plans** (Main Quad, Winchester House): the OSM outline is rasterised in the building's
  frame and covered by maximal rectangles (greedy, largest first, rectangles mostly inside earlier ones dropped);
  each rectangle gets a hipped roof of the same pitch, which reproduces the valleys and hips of wings meeting at right
  angles. The generated rectangle lists are embedded in the model (scratch tools `rects.py`, `plan.py`).
- **Heights**: Wikipedia / official figures (cited per model), else the OSM `height` tag, else estimates from
  photographs — always named in the model's `Model:` fact.
- **Terrain**: landmarks stand on `elevationAt(anchor)`. Where the ground under a long building varies (SLAC gallery,
  Marin Civic Center, Lick summit) the model samples `elevationAt` itself (`groundDz`, as in batch4): the SLAC gallery
  steps every ~96 m, the Marin wings keep a level roof 3 storeys above the highest ground and reach down to the lowest,
  Lick stands on a levelled pad at the highest ground under it (the 76–240 m terrain grid rounds the summit off
  ~28 m below the real 1,283 m). Lighthouses on cliff ledges (Point Reyes, Point Bonita) stand on the smoothed grid
  ground, not at their true ledge heights.
- **Photos**: Wikimedia Commons, 960 px thumbnails with `_meta.jsonl` (page, licence) per folder under
  `data/raw/reference_photos/` (gitignored; modelling reference only). Commons rate-limited this session; items
  without a downloaded photo are noted.

## Derivations worth knowing
- **Apple Park ring** — Wikipedia: 1,512 ft (461 m) diameter, four storeys; press (Fortune video, project description):
  57 ft at the edge, 75 ft at the centre of the roof. Orthophoto at the four cardinal points: outer roof edge
  r ≈ 236.4 m, inner roof edge r ≈ 170.3 m, a glazed skylight band at r 198.5–208.5 m on the ring's centre line, and
  nine radial glass atrium roofs at bearings 0°, 31°, 60°, 90°, 134°, 180°, 227°, 270°, 316°. The 461 m figure is taken
  as the outer glass line, i.e. a ~6 m roof overhang; the inner glass line assumes the same overhang (estimate).
- **Steve Jobs Theater** — sources disagree (165 ft vs 41 m): the engineers (IStructE award entry) and Wikipedia give a
  41 m glass cylinder ~7 m high; the roof fabricator (PCT) gives a 155 ft (47 m) carbon-fibre disc, matching OSM's
  47.6 m roof part. The 58 m light disc on the orthophoto is roof + stone paving.
- **Stanford Main Quad** — Inner Quad courtyard 177 × 73 m (OSM hole); arcade 5.2 m deep (orthophoto). One-storey Inner
  Quad (eave 7.5 m) vs two-storey Outer Quad (11.5 m) and the 27° tile roofs are photo estimates.
- **Memorial Arch (1899–1906)** — "100 ft" high; frieze 12 ft high and 232 ft long round all four sides (PCAD /
  Stanford quake history). The two 8 × 10.6 m pavilions at the entrance of Memorial Court in the OSM outline have a
  perimeter of 75 m ≈ 247 ft, consistent with the frieze length, so the arch is placed on them (span between them 11 m).
  **LOW CONFIDENCE** on arch span/springing.
- **Memorial Church** — spire 80 ft (Office for Religious Life, Stanford News; the Stanford Daily says 85 ft). The 1903
  crossing-tower height under it (34 m) is an estimate (**LOW CONFIDENCE**). 1913 rebuild: low crossing roof with a
  domed skylight (orthophoto shows a glazed pyramid at the crossing).
- **Old Stanford Stadium (1921/1925/1927)** — no plan or historic aerial was reachable; the bowl is centred on the 2006
  stadium (same site, field NW–SE), round a 440-yd track (half-width 40 m, straights ±36 m), 0.79 m per row, rim
  0.27 m per row; open south-east end in 1921 (one source), nearly closed from 1925, 80 rows from 1927. **LOW CONFIDENCE**.
- **Hangar One** — section is a catenary through 308 ft × 198 ft; ends are the section swept round a half ellipse 39 m
  deep (OSM outline: straight body ±134.5 m, ends to ±173.5 m). The skin was stripped Apr 2011 – mid-2012; the restored
  hangar (Wikipedia: reported complete Dec 2025, celebrated Mar 2026) is a second model whose construction phase
  (2010.5 → 2025.95, drawn by the shader as a frame) stands for the bare skeleton.
- **Mission Santa Clara** — the facade faces east-north-east onto the Mission Gardens; the bell tower is left of the
  door (orthophoto + photo). The 1825 adobe church and the 1861 wooden facade with two towers are on the same
  footprint (the 1928 church is a replica on the site) — **LOW CONFIDENCE** for both earlier versions.
- **Winchester House** — the OSM outline also covers visitor buildings; the model is limited to the historic house
  (frame 0°, u −32…30, v −40…20). The seven-storey tower lost in 1906 has no documented position (**LOW CONFIDENCE**).
- **San Jose Electric Light Tower** — 207 ft to the platform + 30 ft flagpole, 75 ft square base over Market &
  Santa Clara Sts (Wikipedia coordinates); legs drawn with a flared taper and hoops after the 1881 photographs.
- **Marin County Civic Center** — wings from the OSM outlines: Administration Building centre line from (−40, 52)
  at 26.9° (frame 164.8°), 155 m, 34.4 m wide; Hall of Justice from (−27.6, 38) at 165°, 246 m, 40.8 m wide; library
  dome r 19 m at (−29.5, 58) from the orthophoto; spire 172 ft at the OSM spire node.
- **NASA Ames NFAC** — OSM gives 54.9 m (180 ft) for the whole complex; only the 80 × 120 ft inlet is drawn that tall;
  the 40 × 80 ft circuit heights are estimates (**LOW CONFIDENCE**).

## Not modelled (and why)
- **San Quentin** — cell-block dates conflict between sources (South Block 1913; West Block 1913–25 or by 1934; East
  Block 1927; North-Seg 1934) and no heights are published; the old 1854 "Stones" has no OSM footprint.
- **Fairmont San José** (1987/2002), **Googleplex / Bay View** (2022), **Oracle HQ**, **Shoreline Amphitheatre**,
  **Cantor Arts Center**, the **Oval / Palm Drive** palms (no surveyed palm positions; the Oval lawn is ground detail),
  the **1855 Point Bonita tower** (site on the headland not located) and the **Point Bonita suspension bridge**
  (1954/2012), **San José City Hall of 1889–1958** (Market Plaza; no footprint), **Moffett Hangars 2 and 3** (1943),
  **Pigeon Point fog-signal building / keepers' houses** (left to the generic footprints).
- Bridges between the Peninsula and the East Bay (San Mateo, Dumbarton) and the Richmond–San Rafael Bridge are left
  to the East Bay batch / the freeway layer.

## Items
### Apple Park — the Ring (`apple_park_ring`)

- Model years: construction 2013.9 → 2017.3, end standing; anchor 37.334854, -122.009012; 7020 triangles; model top 22.9 m.
- Built: Cupertino approved the plans Oct 15, 2013 and demolition of the former HP campus followed; construction 2014–17; employees moved in from Apr 2017
- Architect: Foster + Partners (Norman Foster); engineers Arup
- Size: ring 1,512 ft (461 m) in diameter, 4,805 ft (1.46 km) round; four storeys; 2.8 million sq ft; eight sections between nine atria
- Height: about 57 ft (17.4 m) at the edge and 75 ft (22.9 m) at the centre of the roof
- Roof: ≈ 17 MW of solar panels; white glass canopies at every floor on both faces
- Model: ring and roof edges measured on the orthophoto (roof 472.8 m across, inner edge 340.6 m); glazed central skylight band and the nine radial atrium roofs from the orthophoto; inner facade radius, canopy depth (3 m) and floor levels estimated
- Previously: Hewlett-Packard Cupertino campus (1970s), demolished 2013–14
- Sources: https://en.wikipedia.org/wiki/Apple_Park, https://www.fosterandpartners.com/projects/apple-park
- Photo: `data/raw/reference_photos/apple_park_ring/Aerial_view_of_Apple_Park_dllu.jpg` — [File:Aerial_view_of_Apple_Park_dllu.jpg](https://commons.wikimedia.org/wiki/File%3AAerial_view_of_Apple_Park_dllu.jpg) — author on file page; CC-BY-SA-4.0

### Steve Jobs Theater (`steve_jobs_theater`)

- Model years: construction 2015 → 2017.7, end standing; anchor 37.330878, -122.007454; 560 triangles; model top 7.2 m.
- Opened: Sep 12, 2017 (iPhone X keynote); 1,000-seat auditorium underground
- Pavilion: glass cylinder 41 m across and ≈ 7 m high, the structural glass carrying the roof
- Roof: carbon-fibre disc 155 ft (47 m) across, 44 radial panels (Premier Composite Technologies, Dubai)
- Model: roof thickness and the paved ring around the pavilion from the orthophoto (estimated)
- Sources: https://en.wikipedia.org/wiki/Apple_Park, https://www.istructe.org/structural-awards/projects/2018/steve-jobs-theater-pavillion/, https://www.pct.ae/steve-jobs-theater
- Photo: `data/raw/reference_photos/apple_park_ring/Aerial_view_of_Apple_Park_dllu.jpg` — [File:Aerial_view_of_Apple_Park_dllu.jpg](https://commons.wikimedia.org/wiki/File%3AAerial_view_of_Apple_Park_dllu.jpg) — author on file page; CC-BY-SA-4.0

### Apple Park Visitor Center (`apple_park_visitor_center`)

- Model years: construction 2015.5 → 2017.88, end standing; anchor 37.332847, -122.005375; 398 triangles; model top 13.8 m.
- Opened: Nov 17, 2017
- Size: two storeys, 20,135 sq ft (1,871 m²): shop, café, model of the campus; roof terrace over an olive grove
- Model: roof outline from the orthophoto (28.5 × 73.5 m); glass line, stone core and terrace louvres estimated from the orthophoto
- Sources: https://en.wikipedia.org/wiki/Apple_Park
- Photo: `data/raw/reference_photos/apple_park_ring/Aerial_view_of_Apple_Park_dllu.jpg` — [File:Aerial_view_of_Apple_Park_dllu.jpg](https://commons.wikimedia.org/wiki/File%3AAerial_view_of_Apple_Park_dllu.jpg) — author on file page; CC-BY-SA-4.0

### Stanford Main Quad — Inner Quad (`stanford_inner_quad`)

- Model years: construction 1887.37 → 1891.75, end standing; anchor 37.427648, -122.170217; 1424 triangles; model top 12.8 m.
- Built: cornerstone May 14, 1887; the twelve one-storey buildings round the Inner Quad were ready for the university's opening on Oct 1, 1891
- Architects: Shepley, Rutan & Coolidge (successors of H. H. Richardson), plan by Frederick Law Olmsted
- Material: buff sandstone from the Greystone quarry (Almaden, San José), red clay tile roofs, arcades round the courtyard
- Model: plan from the OpenStreetMap outline of the Main Quad (© OSM contributors, ODbL), split into wings by maximal rectangles; courtyard 177 × 73 m (OSM); eave height (7.5 m), roof pitch (27°) and the arcade (5.2 m deep, 45 bays) estimated from photographs and the orthophoto
- Sources: https://en.wikipedia.org/wiki/Main_Quad_(Stanford_University), https://en.wikipedia.org/wiki/Stanford_University
- Photo: `data/raw/reference_photos/stanford_main_quad/Stanford_University_Main_Quad_-_7_June_2009.jpg` — [File:Stanford_University_Main_Quad_-_7_June_2009.jpg](https://commons.wikimedia.org/wiki/File%3AStanford_University_Main_Quad_-_7_June_2009.jpg) — author on file page; CC-BY-2.0

### Stanford Main Quad — Outer Quad (`stanford_outer_quad`)

- Model years: construction 1898.5 → 1903, end standing; anchor 37.427648, -122.170217; 881 triangles; model top 18.6 m.
- 1906: damaged in the earthquake of Apr 18, 1906; restored by 1909
- Built: the fourteen buildings of the Outer Quad and Memorial Court were completed about 1903 under Charles Coolidge, for Jane Stanford
- Model: plan from the OpenStreetMap outline (© OSM contributors, ODbL), wings by maximal rectangles; two-storey eave (11.5 m) and roof pitch estimated; construction start (1898) estimated
- Sources: https://en.wikipedia.org/wiki/Main_Quad_(Stanford_University)
- Photo: `data/raw/reference_photos/stanford_main_quad/Stanford_University_Main_Quad_-_7_June_2009.jpg` — [File:Stanford_University_Main_Quad_-_7_June_2009.jpg](https://commons.wikimedia.org/wiki/File%3AStanford_University_Main_Quad_-_7_June_2009.jpg) — author on file page; CC-BY-2.0

### Stanford Memorial Arch (`stanford_memorial_arch`)

- Model years: construction 1899.2 → 1902.5, end 1906.3; anchor 37.427648, -122.170217; 110 triangles; model top 31.3 m. **LOW CONFIDENCE (see Model)**
- Built: mostly in 1899; the frieze "The Progress of Civilization in America" (12 ft high, 232 ft round the four sides) finished in 1902
- Height: about 100 ft (30.5 m)
- Fate: destroyed in the earthquake of Apr 18, 1906 and never rebuilt; its two pier stubs remain as the pavilions at the entrance of Memorial Court
- Model: piers on the two 8 × 10.6 m pavilions of the OSM outline (their perimeter matches the 232 ft frieze); arch span and springing height estimated from photographs (LOW CONFIDENCE)
- Sources: https://pcad.lib.washington.edu/building/5117, https://quake06.stanford.edu/3-earthquake-impacts-prestige, https://en.wikipedia.org/wiki/Main_Quad_(Stanford_University)
- Photo: `data/raw/reference_photos/stanford_main_quad/Stanford_University_Main_Quad_-_7_June_2009.jpg` — [File:Stanford_University_Main_Quad_-_7_June_2009.jpg](https://commons.wikimedia.org/wiki/File%3AStanford_University_Main_Quad_-_7_June_2009.jpg) — author on file page; CC-BY-2.0

### Stanford Memorial Church (1903) (`stanford_memorial_church_1903`)

- Model years: construction 1900 → 1903.07, end 1906.3; anchor 37.426893, -122.170471; 470 triangles; model top 58.4 m. **LOW CONFIDENCE (see Model)**
- Built: groundbreaking May 1899, construction from Jan 1900; dedicated Jan 25, 1903 — Jane Stanford's memorial to Leland Stanford
- Design: Charles A. Coolidge and Clinton Day after H. H. Richardson; buff sandstone, red tile
- Tower: clock and bell tower over the crossing with a twelve-sided spire about 80 ft (24 m) tall
- Fate: Apr 18, 1906: the spire and clock tower fell onto the chancel roof, the facade fell into the Inner Quad; most of the church was taken down stone by stone and rebuilt
- Model: plan from the OpenStreetMap outline (© OSM contributors, ODbL); spire height documented; crossing tower height (34 m), pinnacles and wall heights estimated from photographs (LOW CONFIDENCE)
- Sources: https://en.wikipedia.org/wiki/Stanford_Memorial_Church, https://orsl.stanford.edu/memorial-church-history
- Photo: `data/raw/reference_photos/stanford_memorial_church/Stanford_Memorial_Church__2025_-L1007381.jpg` — [File:Stanford_Memorial_Church_(2025)-L1007381.jpg](https://commons.wikimedia.org/wiki/File%3AStanford_Memorial_Church_%282025%29-L1007381.jpg) — author on file page; CC-BY-SA-4.0

### Stanford Memorial Church (`stanford_memorial_church`)

- Model years: construction 1908 → 1913.5, end standing; anchor 37.426893, -122.170471; 344 triangles; model top 30.5 m.
- 1989: Loma Prieta earthquake damage; closed until the rededication of Nov 1, 1992 (30,000 new red clay tiles)
- Rebuilt: repairs from 1908; reopened 1913 without the tower (a domed skylight over the crossing); facade mosaic remade; interior mosaics finished 1917
- Size: about 190 × 150 ft (58 × 46 m); facade mosaic 84 ft wide, 30 ft high
- Model: plan from the OpenStreetMap outline (© OSM contributors, ODbL); roof shapes from the orthophoto; wall, ridge and crossing heights estimated from photographs
- Sources: https://en.wikipedia.org/wiki/Stanford_Memorial_Church, https://orsl.stanford.edu/memorial-church-history
- Photo: `data/raw/reference_photos/stanford_memorial_church/Stanford_Memorial_Church__2025_-L1007381.jpg` — [File:Stanford_Memorial_Church_(2025)-L1007381.jpg](https://commons.wikimedia.org/wiki/File%3AStanford_Memorial_Church_%282025%29-L1007381.jpg) — author on file page; CC-BY-SA-4.0

### Hoover Tower (`hoover_tower`)

- Model years: construction 1939.6 → 1941.47, end standing; anchor 37.427622, -122.166993; 302 triangles; model top 87.0 m.
- Built: groundbreaking Aug 1939; carillon first played Mar 1941; dedicated Jun 20, 1941 for the university's 50th anniversary
- Architect: Arthur Brown Jr. (after the tower of the New Cathedral of Salamanca)
- Height: 285 ft (87 m); observation deck at 250 ft (76 m); 48-bell carillon
- Model: massing from the OpenStreetMap 3D parts (© OSM contributors, ODbL: 11 / 14.3 / 65 / 75 / 81.5 / 87 m); openings and colours from photographs
- Sources: https://en.wikipedia.org/wiki/Hoover_Tower, https://www.hoover.org/research/i-ring-only-peace
- Photo: `data/raw/reference_photos/hoover_tower/Hoover_Tower_Stanford_January_2013.jpg` — [File:Hoover_Tower_Stanford_January_2013.jpg](https://commons.wikimedia.org/wiki/File%3AHoover_Tower_Stanford_January_2013.jpg) — author on file page; CC-BY-SA-3.0

### Stanford Main Library (Green Library, Bing Wing) (`stanford_green_library`)

- Model years: construction 1916.8 → 1919.5, end standing; anchor 37.426920, -122.167615; 90 triangles; model top 24.9 m.
- Built: approved 1913, completed 1919 as the university's Main Library; repaired after the 1989 Loma Prieta earthquake (gift of Peter Bing) and renamed the Bing Wing; the large East Wing (1980) is not modelled
- Architect: Arthur Brown Jr. (Bakewell & Brown)
- Model: outline from OpenStreetMap (© OSM contributors, ODbL; height 24.9 m); wings, the flat central block and the central pyramid from the orthophoto; eave height and the entrance loggia estimated
- Sources: https://en.wikipedia.org/wiki/Cecil_H._Green_Library
- Photo: `data/raw/reference_photos/stanford_green_library/Stanford_University_Green_Library_Bing_Wing.jpg` — [File:Stanford_University_Green_Library_Bing_Wing.jpg](https://commons.wikimedia.org/wiki/File%3AStanford_University_Green_Library_Bing_Wing.jpg) — author on file page; public domain

### Stanford Stadium (1921) (`stanford_stadium_1921`)

- Model years: construction 1921.42 → 1921.88, end 1925.6; anchor 37.434520, -122.161090; 152 triangles; model top 17.8 m. **LOW CONFIDENCE (see Model)**
- Built: groundbreaking Jun 1, 1921, about five months; first game Nov 19, 1921 (Big Game, Cal 42–7)
- Capacity: 60,000 in 66 rows (U-shape; second in size only to the Yale Bowl)
- Construction: earthen horseshoe with wooden bleachers on a steel frame, dug into the ground (the earth from the bowl built the embankments); cinder track
- Model: centred on today's stadium (same site); track oval, row depth (0.79 m) and rise estimated; open end at the south-east (one source) — LOW CONFIDENCE geometry, no plan or historic aerial was reachable
- Sources: https://en.wikipedia.org/wiki/Stanford_Stadium, https://stanfordmag.org/contents/a-short-history-of-stanford-stadium
- Photo: `data/raw/reference_photos/stanford_stadium_1921/Stanford_Stadium_1921_2.jpg` — [File:Stanford_Stadium_1921_2.jpg](https://commons.wikimedia.org/wiki/File%3AStanford_Stadium_1921_2.jpg) — author on file page; Public domain

### Stanford Stadium (1921) (`stanford_stadium_1925`)

- Model years: construction 1925.6 → 1925.72, end 1927.6; anchor 37.434520, -122.161090; 176 triangles; model top 17.8 m. **LOW CONFIDENCE (see Model)**
- 1925: 10,200 seats added, nearly enclosing the horseshoe (70,200)
- Construction: earthen horseshoe with wooden bleachers on a steel frame, dug into the ground (the earth from the bowl built the embankments); cinder track
- Model: centred on today's stadium (same site); track oval, row depth (0.79 m) and rise estimated; open end at the south-east (one source) — LOW CONFIDENCE geometry, no plan or historic aerial was reachable
- Sources: https://en.wikipedia.org/wiki/Stanford_Stadium, https://stanfordmag.org/contents/a-short-history-of-stanford-stadium
- Photo: `data/raw/reference_photos/stanford_stadium_1921/Stanford_Stadium_1921_2.jpg` — [File:Stanford_Stadium_1921_2.jpg](https://commons.wikimedia.org/wiki/File%3AStanford_Stadium_1921_2.jpg) — author on file page; Public domain

### Stanford Stadium (1921) (`stanford_stadium_1927`)

- Model years: construction 1927.6 → 1927.72, end 2005.9; anchor 37.434520, -122.161090; 176 triangles; model top 21.6 m. **LOW CONFIDENCE (see Model)**
- 1927: fourteen more rows (80 rows; 85,500–89,000 seats)
- End: demolished from Nov 26, 2005 and rebuilt within the old bowl
- Construction: earthen horseshoe with wooden bleachers on a steel frame, dug into the ground (the earth from the bowl built the embankments); cinder track
- Model: centred on today's stadium (same site); track oval, row depth (0.79 m) and rise estimated; open end at the south-east (one source) — LOW CONFIDENCE geometry, no plan or historic aerial was reachable
- Sources: https://en.wikipedia.org/wiki/Stanford_Stadium, https://stanfordmag.org/contents/a-short-history-of-stanford-stadium
- Photo: `data/raw/reference_photos/stanford_stadium_1921/Stanford_Stadium_1921_2.jpg` — [File:Stanford_Stadium_1921_2.jpg](https://commons.wikimedia.org/wiki/File%3AStanford_Stadium_1921_2.jpg) — author on file page; Public domain

### Stanford Stadium (`stanford_stadium_2006`)

- Model years: construction 2005.9 → 2006.71, end standing; anchor 37.434520, -122.161090; 317 triangles; model top 38.0 m.
- Built: demolition and construction began minutes after the last home game of Nov 26, 2005; opened Sep 16, 2006 (Stanford v Navy)
- Capacity: ≈ 50,400; no running track; field 29 ft (8.8 m) below the surrounding ground
- Architect: Hoover and Associates; Vance Brown Builders
- Model: stands, decks, press box and video boards from the OpenStreetMap 3D parts (© OSM contributors, ODbL) and the orthophoto; field drawn at ground level (the terrain grid does not resolve the sunken bowl)
- Sources: https://en.wikipedia.org/wiki/Stanford_Stadium
- Photo: `data/raw/reference_photos/stanford_stadium_2006/Stanford_Stadium_new.jpg` — [File:Stanford_Stadium_new.jpg](https://commons.wikimedia.org/wiki/File%3AStanford_Stadium_new.jpg) — author on file page; Public domain

### Levi's Stadium (`levis_stadium`)

- Model years: construction 2012.3 → 2014.54, end standing; anchor 37.403165, -121.969730; 408 triangles; model top 54.0 m.
- Built: groundbreaking Apr 19, 2012; opened Jul 17, 2014 (San Francisco 49ers)
- Capacity: 68,500, expandable to about 75,000; 174 suites
- Architect: HNTB
- Features: seven-storey SAP suite tower on the west side with a 27,000 sq ft green roof; solar canopies; two 200-ft video boards
- Model: outline, bowl tiers, east upper deck, suite tower and video boards from the OpenStreetMap 3D parts (© OSM contributors, ODbL) and the orthophoto; tier edges simplified to chamfered rectangles
- Sources: https://en.wikipedia.org/wiki/Levi's_Stadium
- Photo: `data/raw/reference_photos/levis_stadium/Levi_s_Stadium_in_February_2016_prior_to_Super_Bowl_50__24398261729_.jpg` — [File:Levi's_Stadium_in_February_2016_prior_to_Super_Bowl_50_(24398261729).jpg](https://commons.wikimedia.org/wiki/File%3ALevi%27s_Stadium_in_February_2016_prior_to_Super_Bowl_50_%2824398261729%29.jpg) — author on file page; Public domain

### SAP Center (San Jose Arena) (`sap_center`)

- Model years: construction 1990.49 → 1993.68, end standing; anchor 37.332798, -121.901274; 282 triangles; model top 30.1 m.
- Built: groundbreaking Jun 28, 1990; opened Sep 7, 1993 (San Jose Sharks)
- Architect: Sink Combs Dethlefs (Charles Sink); Prodis Associates
- Capacity: 17,435 (hockey) – 19,190 (concerts)
- Model: square roof (132 × 131 m), drum, diagonal skylight and corner glass atria measured on the orthophoto; height from OpenStreetMap (28.7 m, © OSM contributors, ODbL); facade bands estimated
- Sources: https://en.wikipedia.org/wiki/SAP_Center
- Photo: `data/raw/reference_photos/sap_center/SAP_Center_San_Jose.jpg` — [File:SAP_Center_San_Jose.jpg](https://commons.wikimedia.org/wiki/File%3ASAP_Center_San_Jose.jpg) — author on file page; CC-BY-SA-4.0

### PayPal Park (`paypal_park`)

- Model years: construction 2012.8 → 2015.16, end standing; anchor 37.350928, -121.924806; 240 triangles; model top 23.8 m.
- Built: groundbreaking Oct 21, 2012; opened Feb 27, 2015 (San Jose Earthquakes) as Avaya Stadium; renamed PayPal Park in 2021
- Capacity: 18,000; some of the steepest stands in Major League Soccer; field 105 × 68 m
- Architect: HOK (360 Architecture)
- Features: the largest outdoor bar in North America behind the north-east goal; canopy roofs over three sides
- Model: canopies and stands measured on the orthophoto (open north-east end); outline and height from OpenStreetMap (23.8 m, © OSM contributors, ODbL); rake estimated
- Sources: https://en.wikipedia.org/wiki/PayPal_Park
- Photo: `data/raw/reference_photos/paypal_park/PayPal_Park_pregame__Apr_1__2023_.jpg` — [File:PayPal_Park_pregame_(Apr_1,_2023).jpg](https://commons.wikimedia.org/wiki/File%3APayPal_Park_pregame_%28Apr_1%2C_2023%29.jpg) — author on file page; CC-BY-SA-3.0

### Mission Santa Clara de Asís (adobe church) (`mission_santa_clara_1825`)

- Model years: construction 1822.5 → 1825.6, end 1861; anchor 37.349245, -121.941580; 152 triangles; model top 17.0 m. **LOW CONFIDENCE (see Model)**
- Built: 1822–1825: the fifth mission church, of adobe, on today's site (the mission had moved twice since 1777 after floods and earthquakes)
- Model: nave and sanctuary on the footprint of the 1928 replica (same site and plan); adobe front after the 1928 replica of it; heights estimated (LOW CONFIDENCE)
- Sources: https://en.wikipedia.org/wiki/Mission_Santa_Clara_de_As%C3%ADs
- Photo: `data/raw/reference_photos/mission_santa_clara_1861/Santa_Clara_de_Asis_circa_1910_William_Amos_Haines.jpg` — [File:Santa_Clara_de_Asis_circa_1910_William_Amos_Haines.jpg](https://commons.wikimedia.org/wiki/File%3ASanta_Clara_de_Asis_circa_1910_William_Amos_Haines.jpg) — author on file page; Public domain

### Mission Santa Clara de Asís (1861 facade) (`mission_santa_clara_1861`)

- Model years: construction 1861 → 1861.5, end 1926.82; anchor 37.349245, -121.941580; 108 triangles; model top 29.0 m. **LOW CONFIDENCE (see Model)**
- 1861: a wooden facade with two bell towers was built over the old adobe front; in 1885 the adobe nave walls were removed to widen the church
- Fate: destroyed by fire on Oct 25, 1926
- Model: facade and tower heights estimated from photographs (LOW CONFIDENCE); nave on the 1928 footprint
- Sources: https://en.wikipedia.org/wiki/Mission_Santa_Clara_de_As%C3%ADs
- Photo: `data/raw/reference_photos/mission_santa_clara_1861/Santa_Clara_de_Asis_circa_1910_William_Amos_Haines.jpg` — [File:Santa_Clara_de_Asis_circa_1910_William_Amos_Haines.jpg](https://commons.wikimedia.org/wiki/File%3ASanta_Clara_de_Asis_circa_1910_William_Amos_Haines.jpg) — author on file page; Public domain

### Mission Santa Clara de Asís (`mission_santa_clara_1928`)

- Model years: construction 1927.3 → 1928.95, end standing; anchor 37.349245, -121.941580; 242 triangles; model top 21.8 m.
- Built: rebuilt 1927–28 after the fire of 1926 as an enlarged replica of the 1825 church; consecrated 1929; chapel of Santa Clara University
- Model: outline from OpenStreetMap (© OSM contributors, ODbL); bell tower position from the orthophoto; scalloped parapet, wall and tower heights estimated from photographs
- Sources: https://en.wikipedia.org/wiki/Mission_Santa_Clara_de_As%C3%ADs
- Photo: `data/raw/reference_photos/mission_santa_clara_1928/Mission_Santa_Clara.jpg` — [File:Mission_Santa_Clara.jpg](https://commons.wikimedia.org/wiki/File%3AMission_Santa_Clara.jpg) — author on file page; CC-BY-SA-3.0

### Winchester Mystery House (`winchester_mystery_house`)

- Model years: construction 1886.5 → 1906.25, end standing; anchor 37.318349, -121.951149; 625 triangles; model top 17.5 m.
- Built: Sarah Winchester bought the farmhouse in 1886 and kept building until the 1906 earthquake (the house was under construction for two decades); 160 rooms at her death in 1922; opened to the public in 1923
- Style: Victorian, with Gothic and Romanesque features; up to five levels in places
- Model: outline from OpenStreetMap (© OSM contributors, ODbL), limited to the historic house; turret positions from the orthophoto; wall height, roof pitch and colours estimated — the many small roofs are a simplified roofscape
- Sources: https://en.wikipedia.org/wiki/Winchester_Mystery_House
- Photo: none downloaded (Wikimedia rate-limited this session); see the Wikipedia article's infobox photo

### Winchester House seven-storey tower (`winchester_tower_1906`)

- Model years: construction 1895 → 1900, end 1906.3; anchor 37.318349, -121.951149; 14 triangles; model top 31.0 m. **LOW CONFIDENCE (see Model)**
- Fate: the seven-storey tower collapsed in the earthquake of Apr 18, 1906 and was not rebuilt
- Model: height from the seven storeys (≈ 3.4 m each); position on the house and build years ESTIMATED (LOW CONFIDENCE)
- Sources: https://en.wikipedia.org/wiki/Winchester_Mystery_House
- Photo: none downloaded (Wikimedia rate-limited this session); see the Wikipedia article's infobox photo

### Hangar One, Moffett Field (`hangar_one_1933`)

- Model years: construction 1931.8 → 1933.6, end 2011.3; anchor 37.412951, -122.053965; 370 triangles; model top 60.4 m.
- Built: built 1931–33 for the US Navy airship USS Macon (moved in Oct 15, 1933)
- Size: 1,133 × 308 ft (345 × 94 m), 198 ft (60 m) high; 8 acres of floor
- Design: Karl Arnstein with Wilbur Watson Associates: steel girders sheathed in galvanized steel, inward-curving walls forming an elongated catenary, "orange-peel" doors at both ends
- Fate: the toxic siding was stripped from Apr 2011 to mid-2012, leaving the bare frame
- Model: outline from OpenStreetMap (© OSM contributors, ODbL); section a catenary through the documented width and height; end doors as half-ellipses
- Sources: https://en.wikipedia.org/wiki/Hangar_One_(Mountain_View,_California)
- Photo: `data/raw/reference_photos/hangar_one/Hangarone.jpg` — [File:Hangarone.jpg](https://commons.wikimedia.org/wiki/File%3AHangarone.jpg) — author on file page; Public domain

### Hangar One, Moffett Field (restored) (`hangar_one`)

- Model years: construction 2010.5 → 2025.95, end standing; anchor 37.412951, -122.053965; 370 triangles; model top 60.4 m.
- Bare frame: 2011–2025 the skeleton stood without its skin (shown as a frame)
- Restored: re-skinned and restored by Planetary Ventures (Google) under a NASA lease; reported complete Dec 2025, celebrated Mar 2026
- Model: same geometry as the 1933 hangar; the frame phase stands for the stripped skeleton
- Sources: https://en.wikipedia.org/wiki/Hangar_One_(Mountain_View,_California)
- Photo: `data/raw/reference_photos/hangar_one/Hangarone.jpg` — [File:Hangarone.jpg](https://commons.wikimedia.org/wiki/File%3AHangarone.jpg) — author on file page; Public domain

### Lick Observatory (`lick_observatory`)

- Model years: construction 1880 → 1888, end standing; anchor 37.341418, -121.642845; 554 triangles; model top 23.6 m.
- Built: 1876–1887 with the $700,000 bequest of James Lick (buried under the great telescope in 1887); 36-inch refractor first light Jan 3, 1888; given to the University of California in May 1888
- Site: summit of Mount Hamilton, 4,209 ft (1,283 m)
- Domes: great dome 75 ft (22.9 m) across for the 36-inch refractor (then the largest in the world); 12-inch refractor dome at the north end
- Model: outline and dome positions from OpenStreetMap (© OSM contributors, ODbL) and the orthophoto; wall and drum heights estimated from photographs
- Sources: https://en.wikipedia.org/wiki/Lick_Observatory
- Photo: `data/raw/reference_photos/lick_observatory/Lick_Observatory_Refractor.jpg` — [File:Lick_Observatory_Refractor.jpg](https://commons.wikimedia.org/wiki/File%3ALick_Observatory_Refractor.jpg) — author on file page; CC-BY-2.0

### Lick Observatory — Shane 120-inch telescope dome (`lick_shane_dome`)

- Model years: construction 1950.5 → 1959.3, end standing; anchor 37.342971, -121.637167; 366 triangles; model top 32.2 m.
- Built: funded by the California legislature in 1950; the 120-inch (3 m) C. Donald Shane reflector was completed in 1959 — then the second-largest telescope in the world
- Model: outline and height (32.2 m) from OpenStreetMap (© OSM contributors, ODbL); drum height estimated
- Sources: https://en.wikipedia.org/wiki/Lick_Observatory
- Photo: `data/raw/reference_photos/lick_observatory/Lick_Observatory_Refractor.jpg` — [File:Lick_Observatory_Refractor.jpg](https://commons.wikimedia.org/wiki/File%3ALick_Observatory_Refractor.jpg) — author on file page; CC-BY-2.0

### San Jose Electric Light Tower (`san_jose_electric_light_tower`)

- Model years: construction 1881.61 → 1881.95, end 1915.92; anchor 37.335488, -121.892074; 654 triangles; model top 72.2 m.
- Built: groundbreaking Aug 11, 1881; dedicated Dec 13, 1881 — J. J. Owen's tower to light downtown San José
- Height: 207 ft (63 m) to the lamp platform, 237 ft (72 m) with the flagpole; base 75 ft (23 m) square over the intersection
- Fate: brought down by 56 mph winds on Dec 3, 1915 (a half-size replica stands in History Park)
- Model: hollow-iron-pipe legs and hoops after photographs; bracing stage heights estimated; aligned with the street grid
- Sources: https://en.wikipedia.org/wiki/San_Jose_Electric_Light_Tower
- Photo: `data/raw/reference_photos/san_jose_electric_light_tower/San_Jose_Electric_Light_Tower_Postcard.jpg` — [File:San_Jose_Electric_Light_Tower_Postcard.jpg](https://commons.wikimedia.org/wiki/File%3ASan_Jose_Electric_Light_Tower_Postcard.jpg) — author on file page; Public domain

### Hotel De Anza (`hotel_de_anza`)

- Model years: construction 1931.16 → 1931.9, end standing; anchor 37.334402, -121.895071; 144 triangles; model top 44.0 m.
- Built: groundbreaking Feb 27, 1931 (W. H. Weeks, architect; Carl Swenson, contractor); restored and reopened 1990
- Style: Zig Zag Moderne (Art Deco) with Mission Revival touches: a ten-storey centre between nine-storey wings
- Model: massing from the OpenStreetMap 3D parts (© OSM contributors, ODbL; 36.3 / 30.9 / 31.2 m); crown, sign and colours from a photograph (pale pink over a salmon ground storey, teal accents); crown heights estimated
- Sources: https://en.wikipedia.org/wiki/Hotel_De_Anza
- Photo: `data/raw/reference_photos/hotel_de_anza/USA-San_Jose-De_Anza_Hotel-5.jpg` — [File:USA-San_Jose-De_Anza_Hotel-5.jpg](https://commons.wikimedia.org/wiki/File%3AUSA-San_Jose-De_Anza_Hotel-5.jpg) — author on file page; CC-BY-SA-4.0,3.0,2.5,2.0,

### San José City Hall (`san_jose_city_hall`)

- Model years: construction 2002.3 → 2005.79, end standing; anchor 37.337635, -121.885877; 635 triangles; model top 86.9 m.
- Built: groundbreaking 2002; staff moved in Aug 2005; opened Oct 15, 2005
- Architect: Richard Meier & Partners with Steinberg Architects
- Height: tower 18 storeys, 285 ft (87 m), 68 × 255 ft; rotunda 100 ft (30 m) across and 110 ft (34 m) high
- Previously: City Hall stood in Market Plaza 1889–1958 and on N. First St 1958–2005
- Model: tower, wings and council chamber from the OpenStreetMap 3D parts (© OSM contributors, ODbL); rotunda position from the orthophoto, dimensions from Wikipedia; facade banding estimated
- Sources: https://en.wikipedia.org/wiki/San_Jose_City_Hall
- Photo: none downloaded (Wikimedia rate-limited this session); see the Wikipedia article's infobox photo

### The Tech Interactive (`tech_interactive`)

- Model years: construction 1996.6 → 1998.83, end standing; anchor 37.331447, -121.890197; 288 triangles; model top 22.3 m.
- Opened: Oct 31, 1998 as The Tech Museum of Innovation (132,000 sq ft)
- Architect: Ricardo Legorreta
- Model: outline and parts from OpenStreetMap (© OSM contributors, ODbL; walls 13.7 m, overall 22.3 m); dome rise and colours from photographs
- Sources: https://en.wikipedia.org/wiki/The_Tech_Interactive
- Photo: `data/raw/reference_photos/tech_interactive/The_Tech_Museum_of_Innovation_3_2016-05-14.jpg` — [File:The_Tech_Museum_of_Innovation_3_2016-05-14.jpg](https://commons.wikimedia.org/wiki/File%3AThe_Tech_Museum_of_Innovation_3_2016-05-14.jpg) — author on file page; CC-BY-SA-4.0

### Marin County Civic Center — Administration Building (`marin_civic_center_admin`)

- Model years: construction 1960.12 → 1962.78, end standing; anchor 37.997966, -122.530834; 334 triangles; model top 52.4 m.
- Built: groundbreaking Feb 15, 1960; dedicated Oct 13, 1962 — Frank Lloyd Wright's last major commission (completed by Aaron Green and William Wesley Peters)
- Size: 580 ft (177 m) long; a barrel-vaulted roof bridging between hills; dome over the library rotunda (80 ft)
- Spire: 172 ft (52 m), gold-anodised aluminium
- Colours: sand / pink stucco ("Big Pink") under a bright blue roof
- Model: wing positions and widths from the OpenStreetMap outlines (© OSM contributors, ODbL) and the orthophoto; storey heights, vault rise and arcade bands estimated; roof kept level across the valley
- Sources: https://en.wikipedia.org/wiki/Marin_County_Civic_Center
- Photo: `data/raw/reference_photos/marin_civic_center_admin/Marin_Civic_Center.jpg` — [File:Marin_Civic_Center.jpg](https://commons.wikimedia.org/wiki/File%3AMarin_Civic_Center.jpg) — author on file page; Public domain

### Marin County Civic Center — Hall of Justice (`marin_civic_center_hall_of_justice`)

- Model years: construction 1966.4 → 1969.95, end standing; anchor 37.997966, -122.530834; 133 triangles; model top 17.8 m.
- Built: cornerstone May 25, 1966; structurally complete Mar 1969; dedicated Dec 13, 1969
- Size: 880 ft (268 m) long; courts, jail and county offices; meets the Administration Building at 120°
- Model: as the Administration Building (outline from OpenStreetMap, © OSM contributors, ODbL; heights estimated)
- Sources: https://en.wikipedia.org/wiki/Marin_County_Civic_Center
- Photo: `data/raw/reference_photos/marin_civic_center_admin/Marin_Civic_Center.jpg` — [File:Marin_Civic_Center.jpg](https://commons.wikimedia.org/wiki/File%3AMarin_Civic_Center.jpg) — author on file page; Public domain

### Mission San Rafael Arcángel (replica chapel) (`mission_san_rafael`)

- Model years: construction 1948.6 → 1949.5, end standing; anchor 37.974333, -122.527917; 80 triangles; model top 9.8 m.
- Founded: Dec 14, 1817 as an asistencia (hospital) of Mission San Francisco de Asís; full mission 1822; ruins removed 1870
- Built: the replica chapel was built in 1949 on the site of the mission hospital, beside St. Raphael's Church
- Model: outline from OpenStreetMap (© OSM contributors, ODbL); wall and roof heights, star window and bell openings estimated from photographs
- Sources: https://en.wikipedia.org/wiki/Mission_San_Rafael_Arc%C3%A1ngel
- Photo: `data/raw/reference_photos/mission_san_rafael/Saint_Raphael_Church_San_Rafael_CA.jpg` — [File:Saint_Raphael_Church_San_Rafael_CA.jpg](https://commons.wikimedia.org/wiki/File%3ASaint_Raphael_Church_San_Rafael_CA.jpg) — author on file page; CC-BY-SA-3.0-migrated-wit

### Point Bonita Lighthouse (`point_bonita_lighthouse`)

- Model years: construction 1877 → 1877.5, end standing; anchor 37.815595, -122.529538; 118 triangles; model top 10.1 m.
- Built: first lit 1855 on higher ground (306 ft), often hidden by fog; moved in 1877 to its ledge at 124 ft, reached through a 118 ft tunnel hand-carved through the rock
- Tower: 33 ft (10 m), white with a black lantern; second-order Fresnel lens; focal height 124 ft
- Bridge: suspension footbridge of 1954, replaced in 2012 (not modelled)
- Model: footprint from OpenStreetMap (© OSM contributors, ODbL); octagonal tower and lantern proportions from photographs (estimated)
- Sources: https://en.wikipedia.org/wiki/Point_Bonita_Lighthouse
- Photo: `data/raw/reference_photos/point_bonita_lighthouse/USCGpointbonitaNew.JPG` — [File:USCGpointbonitaNew.JPG](https://commons.wikimedia.org/wiki/File%3AUSCGpointbonitaNew.JPG) — author on file page; public domain

### Point Reyes Lighthouse (`point_reyes_lighthouse`)

- Model years: construction 1870.3 → 1870.92, end standing; anchor 37.995618, -123.023151; 196 triangles; model top 11.3 m.
- Built: first lit Dec 1, 1870; sixteen-sided cast-iron tower 37 ft (11 m) with a first-order Fresnel lens, on a ledge some 300 steps below the headland
- Model: footprint and height from OpenStreetMap (© OSM contributors, ODbL; 10.7 m); white tower, black gallery, red lantern roof from a photograph; proportions estimated; the adjoining red-roofed equipment building is not modelled; stands on the smoothed terrain grid, not its true ledge
- Sources: https://en.wikipedia.org/wiki/Point_Reyes_Lighthouse
- Photo: `data/raw/reference_photos/point_reyes_lighthouse/Point_Reyes_Lighthouse_in_December_2019.jpg` — [File:Point_Reyes_Lighthouse_in_December_2019.jpg](https://commons.wikimedia.org/wiki/File%3APoint_Reyes_Lighthouse_in_December_2019.jpg) — author on file page; CC-BY-SA-4.0

### Filoli (`filoli`)

- Model years: construction 1915.3 → 1917.5, end standing; anchor 37.470369, -122.310847; 122 triangles; model top 15.1 m.
- Built: 1915–1917 for William Bowers Bourn II (gold-mine owner, president of the Spring Valley Water Company) and Agnes Moody Bourn; architect Willis Polk
- Size: 54,256 sq ft, 56 rooms; 16 acres of formal gardens in a 654-acre estate; National Trust since 1975
- Model: outline from OpenStreetMap (© OSM contributors, ODbL); wall height (9.5 m), roof pitch, chimneys and portico estimated from photographs
- Sources: https://en.wikipedia.org/wiki/Filoli
- Photo: `data/raw/reference_photos/filoli/Filoli_Main_House_Entrance.jpg` — [File:Filoli_Main_House_Entrance.jpg](https://commons.wikimedia.org/wiki/File%3AFiloli_Main_House_Entrance.jpg) — author on file page; CC-BY-4.0

### Pigeon Point Lighthouse (`pigeon_point_lighthouse`)

- Model years: construction 1871.3 → 1872.87, end standing; anchor 37.181692, -122.393858; 172 triangles; model top 35.1 m.
- Built: built 1871; first lit at sunset on Nov 15, 1872 — at 115 ft (35 m) one of the tallest lighthouses in the United States
- Tower: tapered brick cylinder, white with black trim; first-order Fresnel lens (1,008 prisms), focal height 148 ft
- Status: closed to visitors since Dec 2001 after the brickwork carrying the iron walkways failed; $16 million rehabilitation announced Dec 2023
- Model: base position from the tower's shadow on the orthophoto; diameters estimated from photographs
- Sources: https://en.wikipedia.org/wiki/Pigeon_Point_Lighthouse
- Photo: none downloaded (Wikimedia rate-limited this session); see the Wikipedia article's infobox photo

### Stanford Dish (`stanford_dish`)

- Model years: construction 1960.6 → 1961.8, end standing; anchor 37.408572, -122.179577; 370 triangles; model top 45.3 m.
- Built: 1961 by the Stanford Research Institute (SRI) for the US Air Force, $4.5 million; steerable 150 ft (46 m) dish
- Model: position from the orthophoto; mount, yoke height and focal ratio estimated from photographs; shown pointing at the zenith
- Sources: https://en.wikipedia.org/wiki/Stanford_Dish
- Photo: `data/raw/reference_photos/stanford_dish/Stanford_Dish.jpg` — [File:Stanford_Dish.jpg](https://commons.wikimedia.org/wiki/File%3AStanford_Dish.jpg) — author on file page; CC-BY-3.0

### SLAC — two-mile linear accelerator (klystron gallery) (`slac_klystron_gallery`)

- Model years: construction 1962.5 → 1966.4, end standing; anchor 37.414389, -122.222146; 640 triangles; model top 5.5 m.
- Built: laboratory founded 1962; the 2-mile (3.2 km) linac first ran in 1966; from 1966 to 1999 the longest building in the world
- Gallery: 3,073.7 m long; the klystrons feed the accelerator in a 10 × 11 ft tunnel under 25 ft of compacted earth
- Model: outline from OpenStreetMap (© OSM contributors, ODbL); section 17 ft × 30 ft (SLAC); drawn in ~100 m steps following the ground
- Sources: https://en.wikipedia.org/wiki/SLAC_National_Accelerator_Laboratory, https://ahro.slac.stanford.edu/resources/slac-history/history-bits
- Photo: `data/raw/reference_photos/slac_klystron_gallery/SLAC_aerial.jpg` — [File:SLAC_aerial.jpg](https://commons.wikimedia.org/wiki/File%3ASLAC_aerial.jpg) — author on file page; CC-BY-SA-4.0

### NASA Ames 40 × 80 ft wind tunnel (`nasa_ames_40x80_wind_tunnel`)

- Model years: construction 1941.6 → 1944.45, end standing; anchor 37.415067, -122.062854; 152 triangles; model top 36.0 m. **LOW CONFIDENCE (see Model)**
- Built: built 1941–44 at the NACA Ames Aeronautical Laboratory; the largest wind tunnel in the world, 40 × 80 ft test section, six 40 ft fans; upgraded 1982–87 into the National Full-Scale Aerodynamics Complex
- Model: outline from OpenStreetMap (© OSM contributors, ODbL); the circuit's heights (30–36 m; OSM gives 54.9 m for the complex) and fan housings estimated (LOW CONFIDENCE)
- Sources: https://en.wikipedia.org/wiki/Ames_Research_Center
- Photo: `data/raw/reference_photos/nasa_ames_40x80_wind_tunnel/Aerial_View_of_the_NASA_Ames_Research_Center_-_GPN-2000-001560.jpg` — [File:Aerial_View_of_the_NASA_Ames_Research_Center_-_GPN-2000-001560.jpg](https://commons.wikimedia.org/wiki/File%3AAerial_View_of_the_NASA_Ames_Research_Center_-_GPN-2000-001560.jpg) — author on file page; Public domain

### NASA Ames 80 × 120 ft wind tunnel (`nasa_ames_80x120_wind_tunnel`)

- Model years: construction 1982.5 → 1987.9, end standing; anchor 37.415067, -122.062854; 86 triangles; model top 55.2 m. **LOW CONFIDENCE (see Model)**
- Built: 1982–87: an open-circuit 80 × 120 ft test section added to the 40 × 80 ft tunnel — the largest wind tunnel in the world (National Full-Scale Aerodynamics Complex)
- Model: outline and height (54.9 m) from OpenStreetMap (© OSM contributors, ODbL); the sloping screened inlet face from the orthophoto; diffuser height estimated (LOW CONFIDENCE)
- Sources: https://en.wikipedia.org/wiki/Ames_Research_Center
- Photo: `data/raw/reference_photos/nasa_ames_40x80_wind_tunnel/Aerial_View_of_the_NASA_Ames_Research_Center_-_GPN-2000-001560.jpg` — [File:Aerial_View_of_the_NASA_Ames_Research_Center_-_GPN-2000-001560.jpg](https://commons.wikimedia.org/wiki/File%3AAerial_View_of_the_NASA_Ames_Research_Center_-_GPN-2000-001560.jpg) — author on file page; Public domain
