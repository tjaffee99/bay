# Landmark orientation / placement audit (2026-11)

Method
- Real footprints: Overture 2026-10-21.0 `building` + `building_part` (OSM-derived, ODbL), cross-checked with the
  DataSF 2016 footprints in `data/interim/sf_buildings.parquet` and an orthophoto (Esri World Imagery, viewed only, not stored in the repo).
- For each landmark: minimum rotated rectangle (long-axis bearing, L × W) and centroid of the matching footprint(s),
  in local metres from the model anchor (x east, y north); the model's top view (triangles dumped from the real
  `build()` functions with esbuild) was overlaid on the footprints and the orthophoto
  (scripts: scratchpad `audit/fp.py`, `shape.py`, `overlay.py`, `aerial.py`, `dump.ts`).
- `frame(x, y, z, bearing)`: local +y points at `bearing`, local +x at `bearing + 90°`.
- Bearings are compass degrees; an axis of 171° is the same line as 351°.
- Thresholds: < 6 m / < 5° = OK.

## Summary of changes

| Landmark | Measured (OSM / orthophoto) | Model before | Change |
|---|---|---|---|
| **City Hall (1915)** | 126.6 m N–S × 87 m (98 m incl. Polk/Van Ness pavilions), long axis **351°/171°**, two light courts N and S of a 28 m E–W rotunda wing, dome centred, rotunda centre 6.5 m SE of the old anchor | 119 m **E–W** × 83 m N–S, axis 90°, pavilions on the short sides, courts E and W of the dome | **Rotated 90° and re-modelled**: frame −9°, 87 × 126.6 m block, Polk/Van Ness pavilions on the long fronts, giant order along the long fronts, end pavilions, N/S courts with glazed roofs, verdigris roofs (orthophoto), rotunda wing, dome stages from the OSM 3D parts (drum r 17 m, dome r 14.6 m from 60 m, 93.7 m total); anchor = rotunda centre |
| **Ferry Building** | 201 × 47 m main block + 9 × 43 m entrance pavilion on the **Embarcadero (SW)** side; tower 11.4 m square at (−22, 2.9) in a 324° frame, i.e. on the city side | frame 144° put the tower 6 m toward the **bay** and two 8 m "sheds" in the Embarcadero roadway (mirrored) | Frame 324° (+x = bay); tower moved to the front; entrance pavilion added; arcade on the Embarcadero front; tower stages from OSM parts (43.5 / 50.5 / 54.2 / 60.5 m); sheds removed |
| **Oracle Park** | home plate at (−5.5, −31), CF bearing ≈ 90° (orthophoto: plate, mound and 2nd base); Coke bottle (OSM) at (121, 41); clock tower (OSM) at (−90, −30) | home plate at (−100, −6) — **97 m off**, stands across King St; bottle and glove with x/y swapped (in foul territory) | Home plate moved; bottle/glove moved to the LF corner; clock tower placed on the OSM tower (12 m square) |
| **Palace of Fine Arts (1915 & 1967)** | hall ≈ 270 m arc, 45 m deep, r ≈ 61–138 m; colonnade arms run N then NE (to y ≈ 110) and S then SE (to y ≈ −104); 8 rotunda piers on r = 24.5 m at 13.5° + 45°k; dome r 16.3 m | hall r 60–88 m over 140°; colonnades an arc centred 75 m east (curving the wrong way); piers on r = 17 m; lagoon a 70 × 140 m rounded box | **Re-modelled from OSM geometry**: hall outline + clerestory band, colonnade centrelines with paired columns and planter boxes, rotunda dimensions, TIGER lagoon polygon |
| **Legion of Honor** | axis 49° ✓, 3 m SE of the anchor; solid gallery block Y −34…+5, wings to Y 54, court 30 × 41 m (Y 8–49), portico Y 9–15, rotunda at Y −32.5; El Cid statue on the NW lawn | wings Y −47…41 (13 m too far SW, extending past the building), court Y 0–41, El Cid on the axis 87 m out (in the car park) | Layout rebuilt from the OSM 3D parts; El Cid moved to its surveyed position |
| **Transamerica Pyramid** | footprint 54.5 m square, faces 81°/171° ✓; centroid **12 m west** of the anchor | frame −9° ✓ | Anchor → OSM centroid |
| **Salesforce Transit Center** | 436.6 × 55 m, axis 45.3° ✓; footprint midpoint 16 m NE along the axis | centred on the old anchor | Anchor moved 15.8 m along the axis; First/Fremont St underpasses re-measured from DataSF street centrelines (7.8 m, 117.4 m) |
| **Chase Center** | 155 × 154 m, centroid (10.9, −4.5) | centred on anchor | Anchor → OSM centroid |
| **Kezar Stadium (1925 & 1990)** | 1990 bleachers 139 × 15 m at y +41…56 / −69…−54 (OSM), field centre (6.7, −6.4); track ≈ 152 × 82 m | bleachers 108 m long at ±52…72; track 176 × 92 m | Anchor → field centre; bleachers, track, colonnade and arch positions re-measured (1925 bowl keeps its estimated massing, re-centred) |
| **Seals Stadium (both)** | (demolished) RF corner at 16th & Bryant, field SE, RF bleachers on 16th St (Wikipedia); Bryant/16th centrelines from DataSF; grid −4.3° | home at (−88, 58): stands 25 m across Bryant St, RF pole 80 m from 16th St | Home (−56, 5), CF 130.7° (estimated from the street block; flagged) |
| **Ewing Field (both)** | home near Masonic & Anza facing SW; grid −9.5° | home 55 m east, stands across Masonic Ave | Home (0, 63), CF 215.5° |
| **Recreation Park** | home at 15th & Valencia facing NW; grid −4.3° | stands across Valencia/15th St | Home (56, −23), CF 310.5° |
| **Spreckels Temple of Music** | T-shaped footprint 54 × 20 m, long axis 138°; shell block at the **SW** back, opening NE toward the Music Concourse | frame 228°: shell opening faced **SW, away from the concourse** | Frame 48°, plan from OSM (shell block 18 m, wings to ±27 m) |
| **de Young (2005)** | Hamon Tower centroid (24.8, 53.4) = NW side of the NE end; floor plates ≈ 30 × 9 m, long axis 137.6° at 18 m → 150.8° at 28 m | tower at the SE side (local x +26 instead of −23), 16 × 26 m plates, 18° twist | Tower moved; 30 × 10 m plates twisting clockwise ~42° (extrapolated) |
| **Sutro Tower** | OSM truss-level triangles point **west**, legs W / SE / NE | legs N / SW / SE (rotated 90°) | Leg angles + 90° |
| **Mission Dolores (adobe)** | 46 × 11.5 m, axis 82°, centroid 6.5 m W of anchor | 46 × 17 m, axis 90°, 6 m too far east | Anchor → OSM centroid, frame 82°, width 11.5 m, heights from photo |
| **Mission Dolores Basilica** | cruciform: nave 20.7 m, transept 27.7 m, front 25 m with twin towers; south edge touches the adobe | 33 × 59 m box overlapping the adobe by ~5 m | Re-modelled: nave, transept, sanctuary + apse, crossing dome, twin towers ≈ 28 m (photo estimate) |
| **Alcatraz cellhouse** | cellhouse 65 × 49 m at 136° (8 m off); dining hall NW (6.6 m off); **administration block at the SE end**, long axis 46° | admin block at the NW end, axis 136° | Positions → OSM centroids; admin block moved and rotated; dining hall added to `replaces` |
| **Fort Point** | OSM outline (irregular, 92 × 60 m, 68°) with the parade-ground ring; long straight wall = landward (SSE) gorge | pentagon; embrasures on the **landward** face | OSM outline + inner ring; embrasures on the NNW / ENE / WSW water faces |
| **Conservatory of Flowers** | 74 m long, axis −6°; end pavilions are N–S wings 11.4 × 24.3 m projecting south; entrance vestibule south of the dome | axis 0°, pavilions 8 × 14 m boxes, no vestibule | Re-modelled to the OSM plan |
| **Dutch Windmill** | OSM centroid **32 m south** of the anchor (orthophoto confirms) | at anchor | Anchor → OSM centroid |
| **Cliff House (1909)** | OSM 71 × 32 m includes the 2004 Sutro wing; the 1909 block is the south 22 × 27 m | 32 × 71 m box reaching over the cliff edge | 1909 block only (12 m, photo); the 2004 wing added as its own landmark in `batch3.ts` |
| **Sutro Baths** | ruins: seawall on the anchor, pools and hall to the east, axis ≈ N–S (−2°) | hall centred on the seawall at 160°, half over the rocks | Hall re-centred 38 m east on a −2° axis; entrance pavilion placed on Point Lobos Ave (estimated) |
| **Coit Tower** | base footprint 22 m, axes 75.6°/165.6° | base axis-aligned | Base rotated −14.5° |
| **Cow Palace** | 185 × 154 m, axis 19.5° ✓, centroid 8 m E | — | Anchor → OSM centroid |

## Checked and unchanged

| Landmark | Measured | Model | Note |
|---|---|---|---|
| Golden Gate Bridge | axis 173.6° from OSM tower piers | same | towers/anchorages/pylons were already from OSM |
| Salesforce Tower | 54 m rounded square on the 45° grid (the MRR's 140° is a rounding artefact; sides at 45°/135°), 3 m off | frame 45° | OK |
| Painted Ladies + 722 Steiner | houses 16 × 6.9 m, axis 81°, per-house centroids within 1 m | frame 261° | OK |
| California Academy of Sciences | 161 × 102.5 m, axis 48.2°, 4 m off | frame 48° | OK |
| de Young main building | 154 × 76 m, axis 48.3° | frame 48° | OK (tower fixed above) |
| Murphy Windmill | OSM centroid 1.3 m; sails on the west face (orthophoto) | | OK |
| Alcatraz lighthouse (1909), water tower | within 1 m of OSM | | OK |
| Bay Bridge west span | tower/anchorage points from OSM; matches orthophoto | | OK |
| Bay Bridge east spans, Embarcadero Freeway, old City Hall, Candlestick, Kezar 1925 bowl | no modern trace (demolished / site regraded) | | already flagged LOW CONFIDENCE / estimated in their facts |
| Cliff House 1863 / 1896 | no trace | | estimated, unchanged |

Remaining uncertainties: Seals / Ewing / Recreation Park home-plate positions are derived from street blocks and
documented corner/orientation statements (no historic aerial was reachable from this session; the 1938
Harrison Ryker mosaic would settle them); the Hamon Tower's total twist is extrapolated from the OSM floor plates up to 28 m.
