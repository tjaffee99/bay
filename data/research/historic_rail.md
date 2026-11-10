# Historic railways, interurbans and rail piers (2026-11)

`data/manual/historic_rail.geojson` — one LineString per dated segment (WGS84, vertices ≤ 20 m apart),
built by `pipeline/historic_rail_trace.py build` from the hand-researched route specification
`data/manual/historic_rail_spec.py` (dates, sources, notes and the geometry recipe of every segment live
there; rebuild after editing it — about 5 minutes, < 1 GB RAM).

## Properties

| field | values |
|---|---|
| `route_id` | route key (several features per route) |
| `name` | segment name; ` (tunnel)` / ` (bridge)` and ` [narrow gauge]` / ` [standard gauge]` suffixes for the automatic splits below |
| `mode` | `rail` (steam / SP / Santa Fe / WP), `narrow_gauge`, `interurban` (Key System, OA&E/SN, Peninsular, 40 San Mateo, Ocean Shore street section), `pier` (wharves and ferry piers carrying track) |
| `year_start`, `year_end` | decimal years (1878.21 = 20 March 1878); `9999` = still in use / still standing |
| `elevated` | `ground`, `trestle`, `pier`, `bridge`, `tunnel` |
| `confidence` | dates: `exact` (documented) or `estimated` (month or year estimated; the note says which) |
| `geometry_confidence` | `high` (today's mapped track or grade, or street centreline), `medium` (traced from a historical topo sheet, or mixed), `low` (hand-placed waypoints) |
| `geometry_source` | how each piece was made (rail/road routing with snap distance, topo sheet + share of the path on map ink, pts) |
| `source_url`, `note` | citation and what the note-worthy facts / uncertainties are |

Automatic splits: on mapped track, runs ≥ 60 m flagged `tunnel` and ≥ 150 m flagged `bridge` in OSM become
their own features (roads.py skips tunnels). Narrow-gauge routes are split in time at their standard-gauge
conversion (SPC Alameda 1906.5, Bay and Coast line 1907.5, San Jose / Santa Cruz 1909.2; NPC east of Manor 1904):
`narrow_gauge` before, `rail` after.

Integration hints for roads.py: `narrow_gauge`/`pier` → `K_RAIL`, `interurban` → `K_RAIL` (or `K_KEY` for
`ks_mole`); `trestle`/`pier` → viaduct-style deck (ELEV 2), `bridge` → 3, `tunnel` → skip.

## routes.csv route_ids superseded by this file (drop them)

* `rr_sfsj_valencia`, `rr_sfsj_main_sf`, `rr_sfsj_ocean_view`, `rr_sfsj_peninsula` → `sfsj`
* `rr_ocean_shore_sf`, `rr_ocean_shore_coast` → `osr`
* `rr_cp_long_wharf` → `cp_long_wharf`; `rr_sp_oakland_mole` → `sp_oakland_mole`
* `rr_alameda_mole` → `spc_alameda` (the "stranded line into the bay": the 1878 date was put on the 1884 mole
  with no landward track; now the West End wharves, Main St, Central/Encinal Ave line, the San Leandro Bay swing
  bridge and the Bay and Coast line to Newark are all there, dated)
* `rr_sf_oakland_rr` → `sfo_7th_st`
* `ks_mole`, `ks_trunk` → `ks_mole` (mole, trestle → fill, pier, and the line ashore to the 40th St yard)
* `ir_40_san_mateo` → `ir_40` (both the Mission St and the Peninsula segments)
* `sn_oakland` → `sn`

Kept in routes.csv (not covered or already from real geometry): `rr_bayshore_cutoff` (Overture geometry with
tunnels), `bridge_railway`, `transbay_terminal_loop`, `ier_7th_st` (its 7th St part now duplicates
`sfo_7th_st`, its bridge link is still needed), the Key System branch lines `ks_f_*`, `ks_c_*`, `ks_b_*`,
`ks_e_*`, `ks_h_*`, `ks_a_*`, the SF steam dummies, and the ferries. Ferry ends to move onto the new piers:
`fy_alameda_pier` → (-122.3365, 37.7972) (Alameda Mole head); `fy_oakland_pier` → (-122.3285, 37.8104)
(Oakland Mole train shed; the Long Wharf head 1869-82 is at (-122.3458, 37.8125)); `fy_key_pier` →
(-122.3445, 37.8167).

## Lines and dates

| route_id | line | dates (open → close) | geometry |
|---|---|---|---|
| `cp_long_wharf` | Oakland Long Wharf: inner part (SF&O 1863, filled 1879-82), outer trestle (CP 1869, freight only from 1882) | 1863.67 → 1882.06; 1869.85 → 1919.5 | USGS SF 1899 |
| `sp_oakland_mole` | Oakland Pier / Mole and train shed | 1882.06 → 1958.58 | USGS SF 1899 |
| `wp_mole` | Western Pacific Mole (north jetty of the estuary) | 1910.6 → 1933.5 | USGS SF 1915 |
| `ks_mole` | Key System Mole: trestle → fill (1912), Key Route Pier, line ashore to the 40th St yard | 1903.82 → 1939.83 (pier), 1958.3 (line ashore) | USGS SF 1915 |
| `sfa` | San Francisco & Alameda RR: Alameda Terminal wharf, Pacific Ave, Lincoln Ave, Park St - Fernside - Melrose, Melrose - San Leandro, San Leandro - Haywards street running | 1864.65 / 1865 → 1873.5 (wharf, Pacific Ave, Hayward), 1960 (Lincoln Ave), 9999 (Melrose - San Leandro) | SF 1899, Concord 1897, OSM, street centrelines |
| `spc_alameda` | SPC narrow gauge: Alameda Mole (1884), West End wharves (1878-84), Main St, Central/Encinal Ave, Encinal to Fernside, swing bridge and marsh trestle across San Leandro Bay | 1878.21 → 1906.3 (bridge), 1940/1941 (mole, Encinal line) | SF 1899/1915, Haywards 1899, street centrelines |
| `spc_main` | Bay and Coast RR West San Leandro - Alvarado - Newark; 1906 Elmhurst link; Newark - Alviso - Santa Clara | 1878.21 / 1906.5 / 1876.5 → 9999 | OSM (UP Coast Sub) |
| `spc_dumbarton_pt` | SPC Dumbarton Point branch | 1876.25 → 1880 | on the 1910 Dumbarton Cutoff corridor (low) |
| `spc_south` | Santa Clara - San Jose; San Jose - Campbell - Vasona; Vasona - Los Gatos; mountain line Los Gatos - Olympia (tunnels); Olympia - Felton; Felton - Santa Cruz | 1876.5 / 1878.5 / 1880.33 / 1875.8 → 9999, 1959 (Los Gatos), 1940.43 (mountains) | OSM |
| `cp_main` | CP Oakland - 1st St - Fruitvale - Melrose; San Leandro - Haywards - Decoto - Niles; Niles Canyon; Sunol - Pleasanton - Livermore; Altamont Pass | 1869.85 / 1869.68 → 9999 (UP Niles Sub, Niles Canyon Ry), 1984 (Sunol - Altamont) | OSM, Pleasanton 1906 |
| `sfo_7th_st` | San Francisco & Oakland RR / SP 7th Street line | 1863.67 / 1864.5 → 1941.57 | street centreline |
| `cp_northern` | CP Northern Railway Oakland - Richmond - Port Costa - Martinez; Martinez - Benicia bridge | 1878.1 → 9999; 1930.8 → 9999 | OSM (UP Martinez Sub) |
| `atsf_richmond` | Santa Fe Port Chicago - Franklin Canyon - Richmond; Richmond - Ferry Point tunnel and slip | 1900.4 → 9999; → 1975 | OSM; slip hand-placed |
| `wp_main` | WP Oakland waterfront (hand-placed); East Oakland - Niles - Niles Canyon - Pleasanton - Livermore - Altamont | 1909.9 → 1960 / 9999 | OSM (UP Oakland Sub) |
| `sn` | Oakland, Antioch & Eastern / Sacramento Northern: 40th & Shafter - Temescal - Montclair; Shepherd Canyon tunnel - Moraga; Moraga - Lafayette; Lafayette - Walnut Creek; Walnut Creek - Concord - Bay Point | 1913.27 / 1911.5 / 1910.5 → 1957.17, 1977 (east of Walnut Creek) | Concord 1915, OSM grade |
| `sp_san_ramon` | SP San Ramon branch Avon - Concord - Walnut Creek | 1891.5 → 1978 | OSM |
| `sfsj` | SF&SJ: Valencia St (18th-25th 1863, Market-18th 1866), Mission diagonal and Bernal Cut, 1874 Harrison St diagonal, Townsend/Division/Harrison, Ocean View Branch (Glen Park - Colma - San Bruno), San Bruno - Mayfield, Mayfield - San Jose | 1863.8 / 1866 / 1874.6 / 1864.04 → 1874.6, 1907.93, 1942, 9999 | San Mateo 1899, SF 1899, OSM (Caltrain), street centrelines |
| `ir_40` | 40 San Mateo interurban: 5th St + Mission St; private right of way Daly City - San Mateo | 1903 → 1949.1 | street centrelines; San Mateo 1915 (medium) |
| `osr` | Ocean Shore Railway: SF street section, Alemany grade, Daly City - Thornton - Mussel Rock - Salada - Rockaway (1915 sheet), Rockaway - Tobin, Pedro Point tunnel, Devil's Slide shelf, Montara, Moss Beach - Granada, Granada - Half Moon Bay, Half Moon Bay - Tunitas Glen | 1907.75 (Tobin), 1908.45 (Granada), 1908.78 (Half Moon Bay), 1908.9 (Tunitas) → 1920.58 | San Mateo 1915, OSM grade fragments, hand-placed (low) at Pedro Point / Devil's Slide / Moss Beach |
| `npc` | NPC / North Shore / NWP: Sausalito terminal, Sausalito - Mill Valley Jct, Alto tunnel (1884), Corte Madera - San Anselmo, San Anselmo - San Rafael (1874), San Anselmo - Manor, White's Hill - Tocaloma (Petaluma 1914), Tocaloma - Point Reyes Station, Tomales Bay shore - Tomales, Mill Valley branch | 1874.56 / 1875.03 / 1884.1 / 1889 → 1930.25 (Tomales Bay), 1933.5 (Manor - Point Reyes), 1941.16 (electric lines), 1971 (Sausalito - San Anselmo freight, estimated) | OSM grade, Tamalpais 1897 (1910s reprint), Petaluma 1914, Point Reyes 1918 |
| `sfnp_tiburon` | SF&NP Tiburon line: Tiburon - Reed - Greenbrae; Greenbrae - San Rafael | 1884.36 → 1967 / 9999 | OSM grade, SMART |
| `sp_mayfield_cutoff` | SP Mayfield Cutoff Mayfield - Los Altos - Monta Vista; Monta Vista - Vasona Jct | 1908.3 → 1964 / 9999 | OSM |
| `sp_dumbarton` | Dumbarton Cutoff and rail bridge (out of service since 1982, still standing) | 1910.5 → 9999 | OSM |
| `peninsular` | Peninsular Railway: San Jose - Los Gatos (Bascom Ave / Los Gatos Blvd); San Jose - Cupertino - Monta Vista (Stevens Creek Rd); Cupertino - Saratoga - Los Gatos | 1904.21 / 1907 → 1933.2 | street centrelines (low) |

## Method

1. **Today's track and mapped grades** (best): shortest path between waypoints on OpenStreetMap railway
   ways (Overture `rail.parquet` 2026-10-21, which carries OSM `is_abandoned` / `is_disused` grades, plus the
   BBBike San Francisco OSM extract and Overpass extracts of `railway=abandoned|razed|disused` and
   `abandoned:railway=*` ways in `data/raw/historic_rail/`), restricted to a corridor round the waypoints,
   with loop removal (sidings, wyes). Short gaps in the mapped grade are bridged straight and logged.
2. **Street running**: shortest path on Overture/OSM road centrelines of the named streets.
3. **Historical topographic maps**: USGS HTMC GeoPDFs (1:62,500, 1895-1919; 1:24,000 1949 for Montara)
   read with `topo_farmsteads.GeoPDF`; registration from the PDF + NADCON, plus the sheet's local offset
   against today's roads (`topo_farmsteads.road_alignment`, affine, early surveys are 50-240 m off; rms
   13-27 m). The line is a least-cost path along the black ink (railroad symbol) inside a 60-300 m corridor
   round hand-placed waypoints, end points snapped to ink; then a robust moving average (drops excursions onto
   lettering), simplified and densified. `geometry_source` reports the share of the path on ink.
   `python historic_rail_trace.py view KEY W S E N` renders a sheet warped to today's frame with today's rail,
   mapped grades and the traced lines, for placing waypoints and checking traces.
4. **Hand-placed waypoints** (Chaikin-smoothed) only where nothing else exists — marked `low`.

Sheets used (TNM product id): San Francisco 1899 (298894) and 1915 (466302), San Mateo 1899 (298921) and
1915 (301599), Concord 1897 (297157) and 1915 (297166), Haywards 1899 (465731), Tamalpais 1897 (298988,
1910s reprint), Petaluma 1914 (298523), Point Reyes 1918 (298610), Pleasanton 1906 (298577); Montara Mountain
1949 and Halfmoon Bay 1940 were viewed for the coast.

## Sources (dates)

Wikipedia: Oakland Long Wharf, Alameda Mole, Key System Mole, San Francisco and Alameda Railroad, Alameda
Terminal, South Pacific Coast Railroad, Ocean Shore Railroad, North Pacific Coast Railroad, Northwestern
Pacific Railroad, Sacramento Northern Railway, East Bay Electric Lines, Ocean View Branch, Peninsular Railway
(California), Dumbarton Rail Bridge, Niles Canyon Railway, Western Pacific Railroad. Alameda Post, "South
Pacific Coast Narrow-Gauge Railroad Once Traversed Alameda" (route along Main St, Central and Encinal Ave,
West End wharves, swing bridge, dates). NPS Point Reyes "Then & Now: Tomales Bay Communities" (NPC built
1873 - 1875-01-11). San Anselmo Historical Museum "Trains? In San Anselmo?" (San Anselmo - San Rafael spur
1874-07-25). Marin railroad timeline (sfgenealogy.org; via search summary: Corte Madera tunnel Feb 1884, old
route abandoned April 1884, last narrow-gauge train to Point Reyes 1930-03-30). Saratoga Historical
Foundation "The Peninsular Interurban". Earlier routes.csv research (SF street sections from DataSF).

## Gaps / not yet done

* Key System branch lines (B, C, E, F, H, A) and the 1939 bridge approach: still the approximate routes.csv
  lines; SP East Bay electric lines other than 7th St and Alameda (Shattuck, California St, Ellsworth,
  9th St/West Berkeley, East Oakland - Fruitvale continuation of 7th St), and the 1876 Berkeley branch.
* NPC: the pre-1884 Strawberry Point / Alto Hill route; the San Rafael & San Quentin RR (1870); the Mt
  Tamalpais & Muir Woods Railway (1896-1930); NWP north of San Rafael (still in use, SMART).
* Ocean Shore: Pedro Point tunnel, Devil's Slide shelf and Moss Beach - Granada hand-placed (no early survey
  of the coast west of 122.5 W; OSM has the grade only in Montara and near Half Moon Bay); the 1916
  relocation round Devil's Slide is not modelled; the WP-operated SE San Francisco remnant (to the 1980s) is
  not identified.
* WP Oakland waterfront line hand-placed; SN Bay Point - Pittsburg, the Chipps Island ferry, the Danville /
  Diablo branch (1914-24); SP San Ramon branch south of Walnut Creek (Iron Horse Trail) and to Radum (1909).
* Santa Fe east of Port Chicago; Santa Fe's Oakland extension via Berkeley (1904); CP 7th St line east of
  Lake Merritt; Port Costa train-ferry slips.
* Several opening months and most freight abandonments are `estimated` (see notes).
## Addendum for data/research/historic_rail.md (new counties, 2026-11) — lead to merge

Modes now also used in routes.csv for the new area: `horsecar`, `streetcar` (Santa Rosa). New tracer sheets are
registered from the spec (`EXTRA_SHEETS`: vac1908 = Vacaville 1908, TNM 299005; ant1908 = Antioch 1908, TNM 296717);
OHM ways reach the `rail` method through `data/raw/historic_rail/h2_ohm_newarea.json`
(`python pipeline/ohm_import.py railextract`, after `download`).

| route_id | line | dates (open -> close) | geometry |
|---|---|---|---|
| `npc_north` | NPC narrow gauge Valley Ford - Freestone - Occidental - Monte Rio; Monte Rio - Duncans Mills (dual gauge 1909) | 1876.5 -> 1930.25; 1876.9 -> 1935.5 | OHM 202387713 / 202387715 (topo + 3DEP), OSM grade |
| `nwp_guerneville` | Fulton - Guerneville; Guerneville - Monte Rio (1909 line) | 1877 -> 1935.5; 1909 -> 1935.5 | OHM 202387871 (3DEP); highway + OHM approximate ways (low) |
| `nwp_sebastopol` | Santa Rosa - Sebastopol: SF&NP branch, then P&SR beside it | 1890 -> 1904.92 (rail); 1904.92 -> 1984 (interurban) | OHM 202387872 |
| `psr_forestville` | P&SR Sebastopol - Forestville | 1905.54 -> 1961 / 1969 / 1984 | OSM grade + OHM 202387872 |
| `psr_two_rock` | P&SR Liberty - Two Rock | 1913.57 -> 1952.5 | OSM grade; 1.4 km straight link at Liberty |
| `sp_santa_rosa` | SP Santa Rosa branch (Santa Rosa & Carquinez): Santa Rosa - Glen Ellen; Glen Ellen - Schellville | 1888 -> 1935; 1888 -> 1942.71 | OHM 200461230 (Santa Rosa 1916 sheet), OSM grade |
| `nwp_sonoma` | Sonoma Valley RR Schellville - Sonoma (3 ft until 1890) | 1879.5 -> 1975 | OSM grade |
| `sp_calistoga` | Napa Valley RR St. Helena - Krug (in place); Krug - Calistoga | 1868.58 -> 9999; -> 1969 | OSM |
| `sfnp_donahue` | SF&NP Petaluma - Lakeville - Donahue Landing | 1870 -> 1884.36 | OSM grade |
| `vaca_valley`, `vaca_valley_elmira` | Vacaville - Winters; Elmira - Vacaville | 1875.65 -> 1975; 1869.47 -> 1987 | OSM grade; Vacaville 1908 sheet |
| `sn_dozier_north` | Sacramento Northern Dozier - county line | 1913 -> 1954 | OSM grade |
| `coal_pittsburg` | Pittsburg RR Somersville - Pittsburg Landing | 1866.5 -> 1916 | Mt Diablo 1898 + Antioch 1908 sheets |
| `coal_empire` | Empire RR: stem toward Antioch (to 38 N), West Hartley, Stewartville branch | 1878.5 / 1882 -> 1898.5 | Mt Diablo 1898 sheet |
| `spc_boulder_creek` | Felton - Boulder Creek (3 ft until c.1909); Dougherty Extension (first 3 km) | 1885.4 -> 1934.07; 1888.4 -> 1917.9 | OSM grade + OHM |
| `sp_loma_prieta` | Aptos - Loma Prieta; Loma Prieta - Monte Vista | 1883.8 -> 1928.13; 1884.2 -> 1902.5 | OSM grade |
| `pvc` | Pajaro Valley Consolidated: Watsonville - Pajaro River | 1890 -> 1929.5 | OSM grade |
| `osr_south` | Ocean Shore: Davenport - Scott Creek; Scott Creek Railway Folger - Swanton | 1906.9 / 1908.9 -> 1923.9 | OSM grade |
| `wtc` | Watsonville Transportation Co. to Port Watsonville | 1904.4 -> 1913.8 | West Beach St / Beach Road |

routes.csv: `rr_nwp_schellville` (Ignacio - Sears Point 1888; Sears Point - Schellville 1879.5; in place),
`sr_street_railway` (horsecar 1877-1905.17), `sr_psr_fourth_st` (streetcar 1905.17-1931.5); `ir_psr` segments 2-4
(partial Forestville stretches) removed in favour of `psr_forestville`.

Gaps (not done, with what is needed): see the agent's final report.
