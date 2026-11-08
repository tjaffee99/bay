# Industrial waterfront: Port of Oakland, NAS Alameda, Hunters Point, Kaiser Yard 3

Models: `viewer/src/landmarks/ports.ts` (`PORTS`), container-yard data `viewer/src/landmarks/ports-yards.ts`
(generated), table `data/tables/landmarks_ports.csv`. NAS Alameda airfield: `data/manual/airports_extra.geojson`
+ the `Naval Air Station Alameda` row of `data/tables/airports.csv`. NAS Alameda building years:
`nas_alameda_*` rows of `data/tables/known_building_dates_region.csv`.

Method (2026-11-08):

* **Positions.** Wharf faces are the OpenStreetMap coastline (API `map` call of the port, 2026-11-08; ODbL),
  straightened into one line per berth group (`W_*` in `ports.ts`; s = metres along the face, n = metres
  inland). Today's cranes were measured along those lines on the Esri World Imagery orthophoto (Vantor
  "Vivid Advanced", captured 2026-03-19/24, 0.34 m; viewed only, not stored in the repo), the crane's
  waterside rail 5 m inside the face. Earlier cranes stand on the same berths: their **counts and years** are
  documented (below), their **spacing along a berth is estimated** and said so in each model's facts.
* **Crane generations** (`T_*` types): PACECO A-frame (1959 Matson, 1960s Portainers), PACECO low-profile
  (X-421/422/423), Panamax, post-Panamax, super-post-Panamax, the 2018 raised cranes and the 2021 ZPMC cranes.
  Each is a low-poly portal (sill beams + bogies, legs, portal beams, diagonal braces), twin box girders,
  a boom lowered over the water or raised to ≈80°, A-frame with fore- and backstays, machinery house,
  trolley and cab (≈230 triangles a crane).
* **Container stacks** (`ports-yards.ts`; tools `pipeline/ports_tools/yard.py` +
  `compile_yards.py`, inputs cached in `data/raw/ports/`): the orthophoto was resampled into each terminal's wharf frame (0.4 m), pixels of
  painted container steel (saturation > 0.28, or near-white) separated from grey paving, OSM buildings masked
  out, and a lattice of 40 ft stack cells (12.8 × 2.8 m pitch, both orientations, phase fitted per 64 × 32 m
  tile) kept where ≥ 45 % of a cell is container. Each cell keeps its orientation and a colour class of its
  mean colour. **Heights are procedural**: connected blocks get 3–4 boxes (a quarter of the stacks ±1, 2–5);
  groups of ≤ 3 cells are single boxes on chassis. Container 12.19 × 2.44 × 2.59 m. The same layout is shown
  for the whole container era of each yard (dates per yard below).
* Terminal outlines for the yard masks: OSM `industrial=port` polygons (APL, SSA, Hanjin, Ben E. Nutter,
  Berths 32-34, TraPac, Transbay, Maersk Sealand ×2, Berth 23).

## Port of Oakland — container cranes

Main source: **Waterfront Ballpark District DEIR, Landmarks Preservation Advisory Board report (City of
Oakland, 2021)**, attachments C (ESA historic resource analysis) and D (Jacobs, *Historical Evaluation of
Crane X-422*, 2019), which summarise W. Minor, *Pacific Gateway* (Port of Oakland, 2000), Port Commission
minutes and newsletters:
https://www.oaklandca.gov/files/assets/city/v/1/public-meetings/landmarks-preservation-advisory-board/2021/er18-016-waterfront-ballpark-district-deir-landmarks-board-report.pdf

| Fact | Value |
|---|---|
| First container ship | S.S. *Elizabethport*, Sea-Land, Outer Harbor Terminal, Sept 5 1962 (Port timeline; HMdb marker) |
| Oct 1961 | Washington revolving ("whirling") gantry cranes at Howard Terminal ($300,000; scrap + 20-ton containers) — first landside cranes |
| 1966 | first two PACECO A-frame container cranes, Sea-Land, Outer Harbor; terminal later 59 acres, 3 berths, 4 cranes |
| by end of 1969 | 8 container cranes, mostly PACECO (Hayward) |
| 1967–71 | Seventh Street Terminal on the SP mole + 140 acres of BART spoil fill (Kaiser Engineers, $33 M); 7 private + 4 public berths |
| 1965–74 | 7th Street + APL terminals: 221 acres, ≥ 7 berths, ≥ 7 more cranes |
| X-421 / X-422 / X-423 | PACECO low-profile cranes (NAS Alameda flight path, 132 ft limit): 1968 / Aug 4 1970 (Berth 35, 4th crane of the terminal, 9th of the port) / 1971 |
| X-422 | 96 ft high, 74 ft lift, 115.5 ft outreach, 182 ft back into the wharf, 96 ft gauge, 40 long tons; Berth 38 after the 1989 quake; 1993 rebuilt (100 ft gauge, deck + 26 + 4 ft); Howard Terminal Mar 1994 (westernmost) |
| other 1960s PACECO | 100 ft lift, > 200 ft (≈22 storeys) with the boom raised, 50 tons |
| 1977 | TransBay (Outer Harbor Container Terminal: 2 berths, 2 cranes, 29 acres) and Maersk (1 berth, 3 cranes, 36 acres) replaced the 7th St Unit, Oil Pier, 14th St Unit |
| Howard | X-415, X-416 Hitachi Panamax 1981 (terminal opened 1982); X-417 KSEC post-Panamax 1987; closed to ships early 2014; 4 cranes standing (2019–21) |
| 1999 | order for 12 post-Panamax cranes (Vision 2000) |
| 2019 | 33 cranes (3 Panamax, 15 post-Panamax, 15 super); X-402/403/404 (first-generation) slated for demolition late 2019 |

Other sources:
* Hanjin Terminal (Berths 55–56): 4 super-post-Panamax cranes (≈22 storeys, 65 t) delivered by *Zhen Hua*
  Oct 22 2000; first Vision 2000 terminal, on the former Fleet Industrial Supply Center — ARCCA Digest
  https://arccadigest.org/?p=44772
* SSA terminal (Berths 57–59) opened Nov 2002, 150 acres — FreightWaves https://freightwaves.com/?p=178161
* 2005 berth assignments (APM 20–22, 24; TransBay 25; TraPac 30; Nutter 36–39; Hanjin 55–56; SSA 57–59;
  APL 60–63; SSA Howard 67–68) — BAAQMD truck appointment list (Aug 2005)
  https://www.baaqmd.gov/~/media/Files/Compliance%20and%20Enforcement/Idling%20Trucks/port_of_oakland_mto_info_8-24-05.ashx
* APM → Ports America at Berths 20–24 (2010); two low-profile STS cranes from Oakland to Boston's Conley
  Terminal (2010) — FreightWaves https://www.freightwaves.com/news/port-of-boston-receives-new-cranes
* Outer Harbor Terminal (Berths 20–26) closed Mar 31 2016; TraPac took Berths 25–26 —
  https://ttnews.com/articles/terminal-operator-exits-port-oakland ; TraPac buildout 66 → 123 acres,
  4 → 7 STS cranes (2019) — https://www.ship-technology.com/news/trapac-completes-67m-expansion
* OICT crane raising: 4 cranes +27 ft, May 2017 – 2018, lift 115 → 142 ft —
  https://www.portofoakland.com/port-oakland-cranes-going-higher-largest-marine-terminal ,
  https://www.porttechnology.org/news/oakland_completes_crane_raising_initiative/
* OICT ZPMC cranes 2021: 174 ft lift, 225 ft outreach, $30 M, 3 older cranes removed —
  https://www.seatrade-maritime.com/terminals/largest-quay-cranes-in-us-west-coast-arrive-at-oakland-s-oict-terminal
* Today's fleet: OICT (55–60) 10 super-post-Panamax; Matson (61–63) 4 post-Panamax; Everport (35–38) 4 super;
  TraPac (25–33) 5 post + 2 super — https://www.oaklandseaport.com/facilities/seaport-facilities
* Matson / Encinal Terminals, Alameda: world's first high-speed container crane, PACECO, in service
  **Jan 7 1959**; modified 1963–64, 1974–75; a new-generation PACECO Portainer added 1977; both dismantled
  1987 and sold to the Port of Nanjing; terminal closed to shipping 1993 — ASME landmark #85
  https://www.asme.org/about-asme/engineering-history/landmarks/85-paceco-container-crane (brochure PDF),
  Alameda Post https://alamedapost.com/history/canner-ships-railroad-shaped-alamedas-north-shore/ .
  Site: 1521 Buena Vista Ave (Nominatim); crane on the Encinal pier's basin face — position estimated.

### Model table (crane chainages in metres along each wharf; † = orthophoto 2026)

| Model id | Wharf | Cranes at s | Type | Years | Estimated |
|---|---|---|---|---|---|
| encinal_matson_crane_1959 | Encinal pier | 120 | PACECO 1959 | 1958.7–1959.02 → 1987.5 | dims, position |
| encinal_paceco_1977 | Encinal pier | 230 | Panamax | 1977 → 1987.5 | position |
| howard_whirley_cranes_1961 | Howard | 180, 330 | whirley | 1961.6 → 1977.5 | count, positions, end |
| howard_cranes_1981 | Howard | 60, 96 † | Panamax (booms up) | 1981 → | which is which |
| howard_crane_x417 | Howard | 132 † | post-Panamax | 1987 → | — |
| howard_crane_x422 | Howard | 24 † | low-profile raised | Mar 1994 → | — |
| oak_sealand_cranes_1966 / _1968 | Outer Harbor | 110, 180 / 330, 400 | PACECO | 1966 / 1968 → 1999.5 | positions, 3rd/4th year, end |
| oak_maersk_cranes_1977 | Outer Harbor | 560, 640, 720 | Panamax | 1977 → 2010.1 | positions, end |
| oak_transbay_cranes_1977 | Outer Harbor | 1000, 1080 | Panamax | 1977 → 2016.25 | positions, end |
| oak_outer_harbor_cranes | Outer Harbor | 41, 95, 158, 188 † | post-Panamax | 2000 → (idle since 2016) | start |
| oak_trapac_cranes_25_26 | Outer Harbor | 1062, 1092, 1122 † | super | 2017 → | start |
| oak_7th_street_cranes_1968 / _1972 | 7th St north | 250, 340 / 580, 700 | PACECO | 1968 / 1972 → 2001 | positions, years |
| oak_crane_x421 / x422_berth35 / x423 | 7th St tip | 330 / 200 / 460 | low-profile | 1968 / 1970.59 / 1971 → 1989.8 | positions, X-421/423 end |
| oak_crane_x422_berth38 | 7th St tip | 880 | low-profile | 1990.3 → 1993.5 | position |
| oak_nutter_cranes_1991 | 7th St tip | 360, 612, 775 | post-Panamax | 1991 → 2002 | count, years |
| oak_everport_cranes | 7th St tip | 360, 612, 718, 775 † | super (green) | 2002 → | start |
| oak_trapac_cranes_30_33 | 7th St north | 134, 305, 626, 839 † | super | 2001 → | start |
| oak_hanjin_cranes_2000 | Middle Harbor | 53, 101, 353, 461 † | super | Oct 2000 → | — |
| oak_ssa_cranes_2002 (+b) | Middle Harbor | 551, 821, 1482 (+1329, 1359, 1614, 1659) † | super | Nov 2002 → 2020.9 (2017.4) | which ones replaced / raised |
| oak_oict_raised_cranes | Middle Harbor | 1329, 1359, 1614, 1659 † | super +27 ft | 2017.4–2018.6 → | which four |
| oak_oict_zpmc_cranes_2021 | Middle Harbor | 551, 821, 1482 † | ZPMC | 2021 → | which three |
| oak_apl_cranes_1972 | Berths 60–63 | 419, 608, 806 | PACECO | 1972 → 2002 | count, years |
| oak_matson_cranes | Berths 60–63 | 419, 608, 638, 806 † | post-Panamax | 2002 → | start |

Wharf lines (A → B, lon/lat): Outer Harbor −122.313306, 37.819247 → −122.322696, 37.810320;
7th St north −122.323276, 37.810097 → −122.333068, 37.811030; 7th St tip −122.333187, 37.810626 →
−122.342630, 37.805782; Middle Harbor −122.325312, 37.798801 → −122.305558, 37.793725; Berths 60–63
−122.305558, 37.793725 → −122.296073, 37.793392; Howard −122.287947, 37.794963 → −122.281163, 37.794660;
Encinal −122.259466, 37.781213 → −122.259864, 37.777966.

### Container yards (dates)

| Yard | OSM polygon | Stacks | From |
|---|---|---|---|
| Berths 20–22 | Maersk Sealand (north) | 248 | Sep 1962 (Sea-Land) |
| Berth 23, Berth 24 | Berth 23, Maersk Sealand (south) | 317, 431 | 1977 |
| Berths 25–26 | Transbay Container Terminal | 537 | 1977 |
| Berths 30–34 | TraPac, Berths 32-34 | 1,327 | 1968.5 |
| Berths 35–38 | Ben E. Nutter | 833 | 1969.5 |
| Berths 55–56 | Hanjin | 1,142 | 2001.3 |
| Berths 57–59 | SSA | 1,597 | Nov 2002 |
| Berths 60–63 | APL | 339 | 1972.5 (estimated) |

Berths 20–24 have been chassis / container parking since the Outer Harbor Terminal closed (2016); the
orthophoto shows that use, and it is kept for today. Not modelled: the Naval Supply Center / Fleet Industrial
Supply Center piers and warehouses (1941–98) under today's OICT, the Oakland Army Base warehouses
(1941–99; mostly demolished 2010s), the 1882 Oakland Long Wharf / Mole train shed (the mole is under the
7th Street Terminal) — no dimensioned plans found in this pass.

## NAS Alameda (1940–1997)

Source: **National Register nomination, NAS Alameda Historic District** (NRIS 12001191, listed 2013-01-23),
https://npgallery.nps.gov/AssetDetail/NRIS/12001191 (PDF https://npgallery.nps.gov/GetAsset/686693c1-b856-4b8f-a9bf-2d17a3164724),
and Wikipedia https://en.wikipedia.org/wiki/Naval_Air_Station_Alameda . OSM footprints carry the district's
inventory years (`start_date`, `old_name:YYYY-1997`, source_ref NARA catalog 123858288).

| Item | Facts | Model |
|---|---|---|
| Station | commissioned Nov 1 1940; closed Apr 25 1997 (BRAC); runways 13/31 8,000 × 200 ft, 07/25 7,200 × 200 ft | runways in `airports_extra.geojson` |
| Landplane hangars 20–23 | 1941; 254 × 213 ft, 65,547–67,344 sq ft; low-pitched gable roof, two monitors, set-back 3rd storey on E/W, glazed sliding doors N and S between pylon-like door pockets | OSM 78 × 65 m; eaves ≈16 m, wings 2 storeys (estimated) |
| Seaplane hangars 39 / 40 / 41 | 1944 / 1941 / 1945; 110,139 / 118,190 / 118,041 sq ft; very low gable roofs, doors E and W, three storeys of shops at the N and S ends | OSM 117 × 80 m; eaves ≈19 m (estimated; ML heights 15–25 m) |
| Buildings 11, 12 | 1941 aircraft maintenance shops (non-contributing) | same massing as the seaplane hangars (assumed) |
| Control tower, Building 19 | 1941 (+1945 wings); L-shaped, 23,706 sq ft; 2-storey N–S wing, 1-storey E–W wing; 4-storey concrete tower at SW corner with octagonal glass control room | OSM building + tower part (10 m square); ≈21 m to cab roof (estimated) |
| Seaplane ramps 1–4 | 1940, 1940, 1941, 1941 (OSM, NRHP district) | slabs ≈15 × 43–54 m into the lagoon; slope estimated |
| Piers 1–3 | Pier 2 387 × 38 m, Pier 3 416 × 65 m (OSM); 1940 appropriation included "an aircraft carrier berthing pier" | — |
| Carriers | home port of Coral Sea, Hancock, Oriskany, Enterprise, Ranger, Carl Vinson, Abraham Lincoln; Hornet (CV-8) loaded the Doolittle B-25s here Apr 1942; Hancock and Oriskany decommissioned 1976; Enterprise (CVN-65) home-ported Nov 1965 – 1990; Carl Vinson (CVN-70) Oct 28 1983 – Jan 1997 (last carrier) | generic class massing: Essex (266 m, 45 m deck) on the north side of Pier 3, 1946–76; Enterprise (342 × 78 m) north of Pier 2, 1965.85–1990.7; Nimitz class (333 × 77 m) south of Pier 2, 1983.82–1997.05 — berths and continuous presence are simplifications |

Airfield geometry (`data/manual/airports_extra.geojson`, tool `pipeline/ports_tools/airfield.py`):
runways = OSM `abandoned:aeroway=runway` centrelines (ways 488956336, 742280167) extended to the documented
7,200 / 8,000 ft and buffered to 200 ft; taxiways = orthophoto pavement within 35 m of the OSM
`abandoned:aeroway=taxiway` lines (incl. the wide WWII diagonal strips); aprons = the rest of the orthophoto
pavement on the field west of Monarch Street and along the Seaplane Lagoon (pieces > 4,000 m², slivers
dropped). Non-overlapping polygons. The 1927 Alameda city airport and Pan Am's 1935–39 China Clipper base on
part of the site are not included.

## Hunters Point Naval Shipyard (San Francisco)

* Drydock 4: 1942–43, built in ten months on the leveled hill; largest on the West Coast (NRHP 12000424;
  NARA https://catalog.archives.gov/id/123861089); OSM outline 335 × 53 m.
* Drydocks 2 (1903) and 3 (1918): Hunters Point Commercial Drydock Historic District (NRHP 12000425;
  https://catalog.archives.gov/id/123861175); OSM 229 × 36 m (8.8 m deep) and 317 × 47 m (12.1 m).
  Drawn flooded, gate at the bay end (estimated).
* Gantry crane: 1947, American Bridge Co., on the Gun Mole Pier; 450 ft (137 m) tall, 730 ft (222 m) long;
  450 or 630 long-ton lifts (sources differ) — https://en.wikipedia.org/wiki/Hunter%27s_Point_crane , KQED
  https://www.kqed.org/news/12005257/the-hunters-point-cranes-legacy-is-both-majestic-and-troubling ;
  OSM relation 9433187 (outline 222 × 52 m, height 137.16). Leg spacing, truss panels, house estimated.

## Kaiser Richmond Shipyard No. 3 (1942–45)

* Built 1942 (Permanente Metals) as a permanent yard with five graving basins; 27 ways in the four yards;
  747 ships — NPS https://www.nps.gov/rori/learn/historyculture/historic-richmond-shipyards.htm ,
  https://en.wikipedia.org/wiki/Richmond_Shipyards ; basins 1–5 and the four piers between them from OSM.
* Whirley crane: Clyde Iron Works 1935 (Grand Coulee), to Richmond 1941; 110 ft boom, 166,000 lb lift,
  229,000 lb; beside the SS *Red Oak Victory* at Basin 5 —
  https://www.nps.gov/rori/learn/historyculture/the-whirley-crane.htm .
* Model: eight whirleys, two per pier (count and positions estimated), 1942–46; the preserved crane from 1942
  (its move from Yard 1 is undated). Yards 1, 2 and 4 (slipways, now Marina Bay) are not modelled — no
  dimensioned layout found in this pass.
