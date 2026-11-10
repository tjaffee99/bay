# Landmark research — North Bay (`viewer/src/landmarks/northbay.ts`)

Sonoma, Napa and Solano counties (2026-11 expansion). Companion to `landmarks_eastbay.md` and `landmarks_southbay.md`.
One row per model in `data/tables/landmarks_northbay.csv` (`start_year` = completion / opening, lat/lon = model
anchor, `height_m` = model top; the dam's is its structural height, the turbines' their tip height).
54 models: 6 bridges on the Carquinez Strait, 7 at Fort Ross, 5 in Sonoma / Petaluma, 3 in Benicia and on Mare Island,
7 in the Napa Valley, Monticello Dam, 6 in Santa Rosa, Petaluma, Bodega and The Sea Ranch, and 19 wind-turbine groups
(527 turbines) in the Montezuma Hills.

## Method
- **Footprints**: OpenStreetMap outlines via Overture 2026-10-21.0 (`data/raw/overture/2026-10-21.0/region4_building.parquet`,
  `region5_building.parquet`; © OpenStreetMap contributors, ODbL), read with pyarrow filters on `px` / `py` around each
  site. Each model is built in a frame aligned with the building (`b.frame(cx, cy, 0, bearing)`: +y at `bearing`,
  +x at `bearing + 90°`); the anchor is the Overture `px, py` point of the footprint, the frame origin the centre of
  the building's own rectangle. Which way a building faces was taken from the street it stands on (nearest named
  Overture road segment) and, where the outline is ambiguous, from a photograph (below).
- **Dimensions**: National Register / National Historic Landmark nomination texts from NPGallery
  (`https://npgallery.nps.gov/NRHP/GetAsset/NRHP/<refnum>_text`, `NHLS/` for landmarks), HAER CA-297, Engineering
  News-Record 1931, Wikipedia. Heights that no source gives are scaled from a photograph whose scale is a known plan
  dimension and are named as estimates in the model's `Model:` fact.
- **Bridges**: alignments are the bridge-flagged parts of Overture's motorway / rail segments
  (`freeways.parquet`, `rail.parquet`); where the documented spans fall on them was checked against the USGS 3DEP
  surface sampled every 25 m along each line (`elevation.nationalmap.gov … 3DEPElevation/ImageServer/getSamples`).
- **Numeric check** (scratch `ship/lm_north/check.py`, `dump_nb.ts`): every mesh was dumped from the real `build()`
  with esbuild; the convex hull of its plan was compared with the hull of the Overture footprints under it (rotated
  rectangle, bearing, IoU, centroid offset), the model top with the cited height, and each standing model's `replaces`
  polygons with the footprint centroids they must cover. Table at the end. `npx tsc --noEmit` passes.
- **Photographs** (Wikimedia Commons, viewed only, not stored in the repo): `Sonoma City Hall.jpg`,
  `USA-St. Helena-Greystone Cellars-1.jpg`, `Benicia_state_capitol_exterior.JPG`, `Rhine House, Beringer Vineyards.jpg`,
  `Napa Opera House, 1018-1030 Main St., Napa, CA 9-5-2010 2-32-51 PM.JPG`,
  `Napa County Courthouse Plaza, Napa, CA 9-5-2010 3-01-28 PM.JPG`, `Church of One Tree - Circa 1918 image.jpg`,
  `Saint Teresa of Avila Church, Bodega (2023)-L1003432.jpg`, `St Peters Chapel on Mare Island in Vallejo California 2.jpg`,
  `FortRoss-chapel-reconstructed.jpg`, `SE Blockhouse.jpg`, `Kuskov House.jpg`, `Fort Ross inside.jpg`, `Rotchev House.jpg`,
  `Sea Ranch Chapel in March 2020-1378.jpg`, `Bale Mill, CA 128, St. Helena, CA 10-22-2011 11-47-42 AM.JPG`,
  `Mission San Francisco Solano. Sonoma State Historic Park.jpg`, `Photo-CA-RanchoPetaluma.jpg`,
  `Condominium 1, 110-128 Sea Walk Dr., Sea Ranch, CA 7-5-2010 7-07-18 PM.JPG`,
  `Free Public Library of Petaluma, 20 Fourth St., Petaluma, CA 5-31-2010 6-56-02 PM.JPG`, `CarquinezBridge2022.jpg`,
  `Niebaum-Coppola winery.jpg`, `Aerial view of Vista Point, Benicia–Martinez Bridge & Mt Diablo.JPG`,
  `California Zephyr crossing the Benicia-Martinez Railroad Drawbridge (1), May 2019.JPG`,
  `Monticello dam from the viewpoint.jpg`.
- **Terrain**: buildings stand on `elevationAt(anchor)`; foundations reach 1–4 m below it. The dam and the turbines
  use the lookup inside `build()` (the dam to put its crest at 139 m absolute, each turbine to stand on its own
  ground). Bridges are modelled from sea level.

## Derivations worth knowing

### Carquinez Strait
- **Carquinez Bridge, 1927 and 1958** — HAER CA-297 (Library of Congress, `ca3089data.pdf`): double cantilever
  through truss, 3,350 ft = two 500 ft anchor arms, two 1,100 ft main spans, 150 ft over the centre pier; trusses
  42 ft apart; superstructure 168 ft from the bottom chords to the peaks over piers 2, 3, 4; bottom chords 135 ft above
  mean high water at the least; roadway falling ≈1 % north to south; anchor arms of 18 panels of 27′9″, cantilever
  arms of 12; suspended spans 433′2″, 72 ft deep at mid-span, 60 ft at the hips; piers numbered from the north abutment,
  tower legs 83 ft apart on round pedestals 34 ft across, pier 5 on the south shore (legs 64 ft apart, encased in 1958).
  "The second Carquinez Bridge was constructed 200′ upstream (east) of the original … with the same span lengths, pier
  locations, and superstructure height." Dates: built 1923–27, dedicated May 21, 1927; second bridge opened Nov 25,
  1958; 1927 bridge dismantled by Sep 4, 2007 (Wikipedia).
  Placement: the 1958 bridge on Overture's eastbound segment (1,097 m bridge flag, 38.065543 → 38.055645 N); the 3DEP
  profile along it is 51 / 35 / 10 m on the north bluff, water from 75 m to ≈1,040 m, 3–4 m on the Crockett flat —
  pier 2 (152 m) in the water, pier 5 (1,021 m) at the shore, as HAER describes. The 1927 bridge 61 m west. The
  bottom chord runs from 51.0 m at the north abutment to 39.8 m at pier 5 (41.5 m = 135 ft + ≈0.4 m at pier 4), peaks
  92–101 m. Not from sources: truss depth at the abutments (12 m), 1958 truss spacing (17 m; Wikipedia gives 52 ft
  overall width). The 1927 bridge's own Crockett approach (HAER: four deck-truss and three girder spans on steel
  towers curving to the hillside) has no geometry in the sources and is **not modelled**; the 1958 model carries
  today's eastbound viaduct on its Overture line up to the 50 m hillside.
- **Alfred Zampa Memorial Bridge** — Wikipedia: spans 147 + 728 + 181 m, towers 410 ft, 84 ft wide, 148 ft clear,
  3,465 ft; opened Nov 11, 2003. The 1,056 m of spans centred on Overture's 1,078 m westbound segment put the towers
  158 m and 886 m from its south end; 3DEP water runs from ≈50 m to ≈950 m, so the south tower stands at the Crockett
  shore and the north one in the water off the bluff. Estimated: leg sections, struts, anchorage blocks, cable sag,
  deck 44.5 → 49 → 48.7 m.
- **Martinez–Benicia railroad bridge** — S. A. Roake, *Engineering News-Record*, June 4, 1931, pp. 918–922 (scan at
  historicbridges.org), table "Principal data on superstructure", distances from the south abutment: viaduct to 560 ft;
  264 ft deck Warren truss (40 ft deep, 19.5 ft c. to c.) to 826; 526 ft through Warren truss (curved top chord, 80 ft
  deep at centre, 33 ft c. to c.) to 1,356; 328 ft lift span to 1,692; six 526 ft through trusses to 4,877; 504 ft deck
  truss (60 ft deep) to 5,383; viaduct to 5,603 ft. Erected at 70 ft clearance; the lift raises 65 ft to 135 ft; formal
  opening Nov 1, 1930. The 1,708 m are centred on Overture's 1,680 m track segment (bearing 328.8°). Estimated: lift
  towers 64 m, lift-span truss depth 16.8 m, rail level 23 m, pier sizes.
- **Benicia–Martinez Bridge 1962 / 2007** — Wikipedia only: seven 528 ft deck-truss spans, 138 ft clearance, 1.2 mi;
  2007 span 1.7 mi, segmental lightweight concrete, opened Aug 25, 2007. **LOW CONFIDENCE** for everything else:
  the seven truss spans are centred on the open water of the 3DEP profile (275–1,775 m from the south end), which
  puts one of them over the railroad's lift span; deck heights run from the ground at each end (29 / 34 m; 24 / 30 m for
  the 2007 span) to ≈50 m over the channel; the 2007 span's piers stand every 160 m (not sourced). The 2007 model
  includes the I-780 connector that leaves it at the Benicia shore (ground 46 m at its west end).

### Fort Ross
- NHL nominations 66000239 (Fort Ross) and 70000150 (Commander's House): stockade "about 276 by 312 feet", walls
  12 ft; a 7-sided and an 8-sided two-storey blockhouse on opposite corners; chapel c. 1825, collapsed 1906, restored
  1916–17 and 1955–56, burned 1970 (Oct 5, Wikipedia), rebuilt 1973; "the original blockhouses and some parts of the
  stockade remained standing until the 1906 earthquake"; Rotchev House c. 1836, 36 × 48 ft, the only original building.
- OSM: blockhouses at (−6.6, 54.3) and (27.8, −77.0) m from the anchor, chapel 10.0 × 8.1 m in the east corner
  (its two outer walls lie on the stockade lines), a stockade fragment giving the west corner: walls of 93, 86, 95 and
  79 m (cited 312 × 276 ft = 95 × 84 m). The chapel's bell tower is at its west-north-west end, the cupola over the
  altar in the corner (photograph taken from inside the fort).
- **Left open**: when the State rebuilt the stockade and blockhouses (the nomination only shows them standing as
  reconstructions; dated 1955–57 with the chapel's second restoration — LOW CONFIDENCE), what became of the Kuskov
  House, Officials' Quarters and Magazin after 1841, and the years of their present reconstructions (from memory
  1983, 1981 and 2012 — unverified, the Fort Ross Conservancy site and the Internet Archive were unreachable). The
  three are therefore modelled only for the Russian period (1812–41) and today's reconstructions stay generic footprints.

### Sonoma, Petaluma
- **Mission San Francisco Solano** — one OSM footprint for chapel and convento (L-plan); its centroid lies in the
  convento, whose `replaces` rectangle hides it. Sonoma Plaza NHL nomination (75000489): convento "nearly 120 feet
  long" (OSM 37.8 m). The nomination's "16 ft. wide and 36 ft. long" for the chapel does not fit the outline
  (8.9 × 33 m) and is not used.
- **Sonoma City Hall** — plan from OSM (20.8 m square, four corner pavilions); heights scaled from the Wikipedia
  photograph by the 20.8 m front: eaves 8.8 m, pavilion roofs 10.2 m, parapet gables 11.4 m, cupola 13.9 m.
- **Petaluma Adobe** — NHL nomination 70000151: quadrangle 200 × 145 ft, walls 20 ft; OSM main wing 60.3 m (198 ft).
  Only the standing half is modelled.

### Benicia, Mare Island
- **Benicia Capitol** — front decided by West G Street (28 m to the SSW of the footprint). The National Register
  form's "40′ x 70′" (partly illegible) is smaller than the OSM outline (15.2 × 28.3 m with stairs and cornice).
- **Camel Barns** — NRHP 76000534: Building 7, 1854, 40.6 × 100 ft, two storeys of sandstone, seven arched doors on
  the north-west side; Wikipedia gives 1855 → built 1853.5–1855.

### Napa Valley
- **Greystone** — NRHP 78000725: 400 × 78 ft, entrance block 50 × 20 ft, tower 20 ft square one storey above the
  roof; OSM 123.5 × 25.4 m with the 17 × 6.2 m block centred on the north-east front (IoU 0.96).
- **Inglenook** — no dated or dimensioned source was found beyond the OSM outline: construction years (1883–87)
  are LOW CONFIDENCE.
- **Bale Grist Mill** — wheel 36 ft (Wikipedia: "the mill and its 36-foot water wheel"); the 1972 National Register
  form says 45 ft, but a 2011 photograph shows the wheel reaching the mill's eaves (≈11 m). The same photograph
  (taken from the highway side: granary false front left, wheel right) puts the wheel on the mill's north side, its
  disc facing the highway; the exact spot and the flume's line are approximate.
- **Napa County Courthouse** — NRHP 92000778: 86 × 95 ft block of 1878; tower and cupola removed in 1931 (no height
  → not modelled); the 1978 addition is a separate plain block.
- **Monticello Dam** — crest line fitted to the 3DEP surface (5 m samples: crest at 139–140 m, arc of radius
  ≈151 m centred (115, 8) m from the anchor); OSM dam way bbox 38.5122002–38.5145869 N agrees with the 312 m arc.
  Spillway: OSM building "Morning Glory Spillway Opening" (22.6 m bbox) at 38.5122583 N, 122.1049014 W.

### Santa Rosa, Bodega, The Sea Ranch
- **Church of One Tree** — the footprint has the tower projecting at the south-east corner and a plain gable toward
  Sonoma Avenue; the c. 1918 postcard (at the B Street site) shows the same arrangement. The year of the move to
  Juilliard Park (1957) is not in the sources used: LOW CONFIDENCE. The 1873–1957 site is not modelled.
- **DeTurk Round Barn** (added; it stands) — NRHP 04000334: 76 ft diameter, 32 ft high without the spire, 1891.
- **St. Teresa of Avila** — the OSM outline has a 3.5 × 1.3 m projection at the north-west end and a 6.3 × 4 m one at
  the south-east; the 2023 photograph shows an engaged tower projecting about a metre from the front, so the front
  is the north-west end, toward Bodega Highway. Built 1860, dedicated June 2, 1861 (Wikipedia).
- **Condominium One / Sea Ranch Chapel** — outlines from OSM; both roofs are simplifications (LOW CONFIDENCE massing).

### Montezuma Hills wind farms
- US Wind Turbine Database v9.1 (2026-09-28 CSV, USGS / LBNL / ACP, public domain): Solano County rows with a hub
  height (527 turbines; two rows "unknown Solano County" without attributes are left out). Grouped by project,
  project year, model and hub height → 19 models; each turbine at `xlong, ylat` (location confidence 3 for all),
  hub height / rotor diameter / tip height from `t_hh, t_rd, t_ttlh`. Built = project year ± (month unknown).
  The database lists standing turbines only: the 1980s–90s machines and the units removed for the 2024 Solano 4
  repowering are not modelled.

## Numeric check
Model plan (rotated rectangle of the mesh's hull) against the Overture footprints under it.

<!-- @@TABLE@@ -->

Bridges: mesh lengths 1,021 m (Carquinez cantilevers; 3,350 ft = 1,021 m), 1,056 m of spans on 1,078 m (Zampa), 1,708 m
(railroad; 5,603 ft), 1,881 m (1962), 2,680 m (2007); tops 101 m (cantilever peaks: 168 ft above a bottom chord at
41.5–51 m), 125 m (Zampa towers, 410 ft), 45.7 m truss tops / 64 m lift towers (railroad).

## Not modelled (and why)
- **Benicia Arsenal Clocktower Fortress** — NRHP dimensions (61 × 177.3 ft; three storeys and two lookout towers until
  the 1912 explosion) but no named OSM footprint: the best candidate (60.4 × 17.5 m at 38.044944, −122.134091) could
  not be confirmed, nor which corner the surviving tower stands on.
- **Fountaingrove Round Barn** (1899 – Oct 9, 2017) — position known (OSM "Round Barn Ruins" 38.4757922, −122.7274430;
  round-barn inventory N38 28.548 W122 43.641), 16 sides, but no diameter or height in the sources.
- **Santa Rosa courthouses** of 1885 and 1910 — no plan or dimensions found (Sanborn sheets not consulted).
- **Robert Mondavi Winery, Castello di Amorosa, Sterling Vineyards, Opus One** — OSM outlines exist, no published
  dimensions; Mondavi's layout could not be read from the outlines alone.
- **Potter School (Bodega)** — outline includes later additions, no photograph or dimensions.
- **Guerneville Bridge (1922)** — NRHP 89000945 has the spans (948 ft: seven 22 ft approach spans, three 180 ft Parker
  through trusses, eleven approach spans; roadway 17 ft; trusses ≈30 ft high) but the old bridge's line beside the
  1998 bridge was not found in the data.
- **Rio Vista Bridge** — half outside the map; **Jack London's Wolf House** — NRHP (80 × 82 ft) and OSM
  (28.9 × 20.6 m) disagree; **Mare Island Dry Dock 1 and cranes**, **Nut Tree**, **Solano County Courthouse**,
  **Sonoma Raceway** — not researched.
