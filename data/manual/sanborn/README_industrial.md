# Sanborn tracing: industrial San Francisco (South of Market, Produce Market, Butchertown, north waterfront)

Real historical footprints of SF's industrial districts — warehouses, factories, planing mills, slaughterhouses,
tanneries, fertilizer works, the old Commission (Produce) Market — and the railway tracks that served them, traced from
the Library of Congress scans of the Sanborn Map Co. *Insurance Maps of San Francisco* (public domain). Built by
`pipeline/sanborn_trace_industrial.py`, an extension of `pipeline/sanborn_trace_waterfront.py` (same georeferencing,
SIFT registration of the 1950 plates, colour segmentation, schema and confidence rules; see `README_waterfront.md`).
Control data: `control/industrial/`.

## Files

| file | content |
|---|---|
| `soma_industrial_1913.geojson`, `_1950.geojson` | South of Market: Folsom → Townsend / King, the Embarcadero (Steuart) → 7th St (1913 vol. 2), plus the Produce Market blocks Pacific → Clay, Battery → the Embarcadero (1913 vol. 1 sheets 10, 11, 15, 16) |
| `butchertown_1914.geojson`, `_1950.geojson` | Islais Creek south shore, Butchertown (Railroad Ave = 3rd St, Arthur → Davidson Ave, Newhall → Lane St), Bayview industrial strip west of 3rd St (Quint / Phelps / Rankin St, Davidson → Hudson Ave) |
| `north_waterfront_1913.geojson`, `_1950.geojson` | east of the Fisherman's Wharf tracing: Powell → Kearny St, Beach → Bay St (sheets 2, 3) and the Telegraph Hill waterfront, Chestnut → Greenwich, Battery → Montgomery St (sheet 19) |
| `<area>_<year>_tracks.geojson` | railway centrelines (LineString) drawn on those sheets |
| `<area>_coverage.geojson` | one polygon per map year: the ground the traced sheets cover, minus the coverage of areas traced by the other tools (`fishermans_wharf`, `mission_bay`, `western_addition`, and `potrero_point` / `dogpatch` / `potrero` if such files exist when `assemble` runs). An empty spot inside it was empty (or water / lumber yard / street) on that map |
| `control/industrial/<key>.json` | control per sheet (25 % IIIF image): block-zone corners, street crossings, street-line constraints, or the SIFT registration onto the 1913/14 plate |
| `control/industrial/<key>.tracks.json` | track centrelines in image pixels (`px`, snapped onto the drawn line; the hand trace kept as `px_hand`), or carried from the 1913/14 plate (`carried_from`) |
| `control/industrial/attributes.json` | names / uses read from the map labels for 39 footprints (positions checked on crops) |
| `control/industrial/areas.json` | which sheets make up each area and map year |

### Feature properties

As in `README_waterfront.md` (`map_year`, `volume`, `volume_label`, `loc_url`, `sheet`, `sheet_no`, `iiif`, `stories`,
`stories_source`, `material`, `use`, `use_source`, `name`, `sanborn_colour`, `confidence`, `georef`, `georef_rms_m`,
`area_m2`, `modern_overlap`), plus:

| property | meaning |
|---|---|
| `extraction` | `colour class` (the waterfront tool's colour masks) or `region` (1950 only: a region enclosed by drawn lines, classified by its median colour — catches the faded fills of paste-over slips the colour masks miss) |
| `material` | as before; additionally dark-ochre "fire proof construction" fills that the yellow mask caught (hue 18–23, saturated) are re-classed to `fireproof` → `concrete` (1913/1950) |

Track properties: `id`, `map_year`, `volume`, `sheet`, `sheet_no`, `loc_url`, `kind` (`belt` = State Belt R.R., `main`,
`spur`, `yard`), `railroad` (only where the sheet labels it: "Belt R.R.", "S.P.R.R." — otherwise null), `note`,
`confidence`, `georef_rms_m`, `line_test` (share of the centreline lying on a drawn dark line, 0–1), `outside_zones`
(share of the line outside the block zones of a block-wise sheet), `carried_from`, `length_m`.

Track confidence: never better than `medium` (hand-traced on the 25 % overview, then snapped onto the drawn line, ±1–2 m
across the track); `low` when `line_test` < 0.7 (gaps for lettering / crossings, or uncertain identification) or when
more than half of the line lies outside the block zones (in a street that the sheet draws wider than scale — e.g. King,
Townsend, Japan St, the Embarcadero; the vertex then takes the nearest block's transform, so the across-street position
is approximate). Lines with `line_test` < 0.45 are dropped. 1950 tracks are the 1913/14 centrelines moved onto the 1950
scan by the inverse registration and kept only where the line is still drawn there (`line_test` ≥ 0.7 after a ±5 px
snap); tracks added between 1913 and 1950 were **not** traced.

## Counts

| file | features | confidence high / medium / low | `region` (1950 slips) | named | area (1000 m²) | modern_overlap ≥ 0.5 | materials | track lines (high/med/low; kinds; length) |
|---|---|---|---|---|---|---|---|---|
| soma_industrial_1913 | 1198 | 929/200/69 | 0 | 34 | 511.7 | 731 | frame 1005, brick 157, stone 19, concrete 17 | 34 (0/7/27; spur 18, belt 10, yard 4, main 2; 7.46 km) |
| soma_industrial_1950 | 2036 | 1497/412/127 | 512 | 0 | 549.9 | 1499 | concrete 856, frame 854, brick 306, iron 20 | 21 (0/9/12; spur 9, belt 7, yard 3, main 2; 4.65 km) |
| butchertown_1914 | 319 | 128/166/25 | 0 | 3 | 78.1 | 91 | frame 308, brick 8, concrete 2, stone 1 | 7 (0/7/0; main 5, spur 2; 1.29 km) |
| butchertown_1950 | 399 | 148/221/30 | 18 | 0 | 91.4 | 137 | frame 340, concrete 43, brick 10, iron 6 | 7 (0/7/0; main 5, spur 2; 1.29 km) |
| north_waterfront_1913 | 46 | 15/30/1 | 0 | 0 | 42.5 | 21 | frame 34, brick 10, stone 2 | — |
| north_waterfront_1950 | 80 | 29/42/9 | 30 | 0 | 30.3 | 50 | concrete 44, brick 18, frame 16, iron 2 | — |

**Storeys were not read** on any of these sheets (`stories_source = default` everywhere; rule as in the waterfront
README: frame < 30 m² shed 1, frame ≥ 300 m² warehouse 1, brick / stone / concrete warehouse 2, iron shed 1; frame
≤ 300 m² dwelling 2 only on the residential sheets 022_0809 / 0813). `use` is the size/material rule except for the 39
labelled footprints (`use_source = map (label)`). Many SoMa warehouses were 2–5 storeys: the default 1–2 storeys is too
low for them (open item). `modern_overlap` is high in SoMa because many of the 1906–1913 warehouses still stand
(South Park, Rincon Hill, SoMa warehouse district); `sf_predecessors.apply_sanborn` leaves those to the modern data.

## Sources

Sanborn Map Company, *Insurance Maps of San Francisco, California*, Library of Congress Geography and Map Division,
Sanborn Maps Collection (public domain):

| edition | LOC item | sheets used |
|---|---|---|
| 1913 vol. 1 | https://www.loc.gov/item/sanborn00813_015/ | 2, 3, 19 (north waterfront); 10, 11, 15, 16 (Produce Market) |
| 1913 vol. 2 | https://www.loc.gov/item/sanborn00813_016/ | 115, 122, 126, 127, 128, 132–136, 140–144, 148–151, 156–159, 164–167, 172–175 |
| 1914 vol. 8 | https://www.loc.gov/item/sanborn00813_022/ | 805, 807, 808, 809, 810, 812, 813 |
| 1913–1950 vol. 1 | https://www.loc.gov/item/sanborn00813_030/ | same sheet numbers as 1913 vol. 1 |
| 1913–Sep 1950 vol. 2 | https://www.loc.gov/item/sanborn00813_031/ | same as 1913 vol. 2 |
| 1914–Feb 1950 vol. 8 | https://www.loc.gov/item/sanborn00813_037/ | same as 1914 vol. 8 |

Vol. 8 date: the title page reads "Volume Eight … 1914" (copyright 1914); the LOC catalogue's publication note says
"Sanborn Map Company, 1922 Vol. 8" and a receipt stamp is on the title page. `map_year` = 1914 (file `butchertown_1914`);
the copy may carry corrections up to c. 1922 (no paste-over slips were noticed on the traced sheets).

Key maps used to find sheets: 1913 vol. 1 `0000a/0000b`, vol. 2 and vol. 8 sheet `0000`. Vol. 8 (1914) covers
everything south of Army St (Islais Creek, Butchertown, Bayview, India Basin, Hunters Point: sheets 756–880).

## Method (differences from the waterfront tool)

1. **Block zones from street corridors.** Almost every SoMa and Produce Market sheet draws its blocks at 50 ft = 1 in
   but the streets between them too wide (a single sheet fit has 12–27 m residuals), so all of them are fitted block
   by block. A sheet is described by its street corridors on the image (left/right kerb line of each vertical street,
   top/bottom of each horizontal street, snapped to the strongest long drawn line within ±16 px); each block between
   two corridors becomes a zone whose four corners are the DataSF centreline crossings offset by half of each street's
   width (`bcx`: centrelines fitted as straight lines within 200–400 m and intersected, so streets that no longer meet
   — Japan, Ritch, Jackson / Washington east of Front, Pacific at Davis — still give a corner). Alleys inside a block
   are not used (they are drawn to scale within the block); an alley or street whose corners cannot be trusted
   (vacated, realigned, or drawn at a different place: Rincon, Madison, Harriet, South Park, Commercial, the
   Embarcadero) is marked `bad` and its zone keeps only the corners on the good streets (2-corner zones → `medium` if
   the zone's scale is within 1 % of 0.2025 m/px, else `low`). Street widths used (from the sheets' labels): SoMa
   streets 82.5 ft; alleys 35 ft (Clara, Shipley, Perry, Ritch, Zoe, Welsh, Freelon, Stanford, Morris, Gilbert,
   Harriet), 37.5 ft (Columbia Square, Sherman), 40 ft (Stillman, Essex, Boardman), 50 ft (Hawthorne, Rincon,
   Sterling, Oak Grove), 70 ft Bluxome; Produce Market: Front / Davis / Drumm / Battery 68.75 ft, Pacific / Jackson /
   Washington / Clay **49 ft** ("49' wide" on sheets 10 and 15; 68.75 ft gave 2–3 m residuals, 49 ft 0.2–1.2 m).
2. **Butchertown control.** East of 3rd St most of the 1914 street grid is gone (Lane, Mendell, Newhall north of
   Evans; Galvez / Fairfax east of Keith); straight-line extensions of the fragments disagree by tens of metres and a
   regular-grid model of the 132 surviving Bayview nodes left 40 m median residuals, so neither is used. Control per
   sheet is only what survives: node crossings (807: Rankin / Quint × Davidson / Evans; 808: Phelps × Davidson / Evans
   / Fairfax / Hudson; 809: Newhall × Hudson / Galvez / Fairfax / Evans; 813: Evans × Keith / Jennings, Fairfax ×
   Keith), the straight avenue centrelines as street-line constraints (Evans, Davidson, Burke, Custer, Galvez,
   Hudson), and the Railroad Ave (3rd St) crossings with Burke / Custer / Davidson on 805, whose diagonal corridor was
   measured with a Hough transform (kerbs 100 ft apart). 810 and 812 (the slaughterhouse and fertilizer blocks) rest
   on the Evans and Davidson lines plus one crossing each (Evans × Newhall; Evans / Davidson × Lane extended from
   Fairfax), so their scale is 3 % off the plate scale (0.193–0.197 m/px): ±2.5 m at the sheet edges; their features
   are capped at `medium`. The Hudson × Keith node (306 m from Evans × Keith instead of ~257 m: Hudson is jogged in
   India Basin) was rejected.
3. **1950 sheets**: registered onto the 1913/14 scans exactly as in the waterfront tool (SIFT + RANSAC, 51–1,672
   inliers, 1.1–2.1 px; vol. 8 sheet 810 has only 51 inliers because Islais Creek's shore was refilled and redrawn,
   but its streets line up on the overlay). After the colour pass, `extract_regions` adds regions enclosed by drawn
   lines whose median colour is a building colour (512 SoMa, 18 Butchertown, 30 north-waterfront features), and
   `reclass` moves dark-ochre fills from frame to fire-proof.
4. **Tracks.** Centrelines traced by eye on 25 % overviews (sheets with rail), then snapped onto the nearest drawn line
   (`snap_line`: vertices every 20 px, ±8 px search, profile averaged ±6 px along the track so the cross-ticks of the
   railway symbol do not count). Each track of the map's railway symbol is one line; railroads named only where the
   sheet labels them. Traced: State Belt R.R. on the Embarcadero (sheets 122, 128, 135, 136, 115), the S.P.R.R. along
   King, Townsend (approximate), Japan and 2nd St, the Santa Fe warehouse yard (115), spurs into the Oriental /
   Crane Co. / Baker & Hamilton blocks (135, 143, 151); Bayview: three tracks crossing blocks 5245 / 5250 toward Quint
   St (807) and four along Quint St (808) — not labelled on the traced crop (probably the Southern Pacific Bay Shore
   line of 1907).
5. **Labels.** Names / uses for 39 large or prominent buildings were read from the overviews and attached by position;
   each attachment was checked on a crop (one wrong hit, the Legallet-Hellwig tannery on 808, was removed).

## Georeferencing per sheet

Residuals in metres between the transformed pixel and the DataSF-derived position. Block zones: 93 zones, median RMS
0.40 m; the only zones above 1.5 m are the four of sheet 015_0019 (2.1–3.6 m: the Chestnut–Lombard block is drawn 105 m long on the map
but DataSF puts 128 m between the centrelines — probably a jog in today's Chestnut / Lombard near the Embarcadero; those
features are `medium`/`low`).

| sheet (LOC id) | method | control | residuals RMS / max | scale, rotation |
|---|---|---|---|---|
| **butchertown 1914** | | | | |
| [00813_08_1914-0805](https://www.loc.gov/item/sanborn00813_022/) | sheet similarity | 3 points + 4 street-line constraints | 1.89/2.77 m | scale 0.1968 m/px, rot -35.07 deg |
| [00813_08_1914-0807](https://www.loc.gov/item/sanborn00813_022/) | sheet similarity | 4 points + 4 street-line constraints | 0.60/0.89 m | scale 0.2006 m/px, rot -35.25 deg |
| [00813_08_1914-0808](https://www.loc.gov/item/sanborn00813_022/) | sheet similarity | 4 points + 0 street-line constraints | 0.30/0.37 m | scale 0.2005 m/px, rot -35.06 deg |
| [00813_08_1914-0809](https://www.loc.gov/item/sanborn00813_022/) | sheet similarity | 4 points + 4 street-line constraints | 0.79/1.64 m | scale 0.2024 m/px, rot 54.97 deg |
| [00813_08_1914-0810](https://www.loc.gov/item/sanborn00813_022/) | sheet similarity | 1 points + 4 street-line constraints | 0.44/0.58 m | scale 0.1932 m/px, rot 54.93 deg |
| [00813_08_1914-0812](https://www.loc.gov/item/sanborn00813_022/) | sheet similarity | 2 points + 4 street-line constraints | 1.92/3.84 m | scale 0.1971 m/px, rot 54.78 deg |
| [00813_08_1914-0813](https://www.loc.gov/item/sanborn00813_022/) | sheet similarity | 3 points + 0 street-line constraints | 1.61/1.95 m | scale 0.2020 m/px, rot -35.89 deg |
| **butchertown 1950** | | | | |
| [00813_08_1950-0805](https://www.loc.gov/item/sanborn00813_037/) | registered onto 022_0805 | SIFT+RANSAC similarity | 1.2 px = 0.23 m + base | scale 0.1961 m/px, rot -35.23 deg |
| [00813_08_1950-0807](https://www.loc.gov/item/sanborn00813_037/) | registered onto 022_0807 | SIFT+RANSAC similarity | 1.5 px = 0.31 m + base | scale 0.2014 m/px, rot -35.37 deg |
| [00813_08_1950-0808](https://www.loc.gov/item/sanborn00813_037/) | registered onto 022_0808 | SIFT+RANSAC similarity | 1.6 px = 0.31 m + base | scale 0.2009 m/px, rot -35.59 deg |
| [00813_08_1950-0809](https://www.loc.gov/item/sanborn00813_037/) | registered onto 022_0809 | SIFT+RANSAC similarity | 1.4 px = 0.27 m + base | scale 0.2024 m/px, rot 54.81 deg |
| [00813_08_1950-0810](https://www.loc.gov/item/sanborn00813_037/) | registered onto 022_0810 | SIFT+RANSAC similarity | 1.3 px = 0.25 m + base | scale 0.1935 m/px, rot 53.86 deg |
| [00813_08_1950-0812](https://www.loc.gov/item/sanborn00813_037/) | registered onto 022_0812 | SIFT+RANSAC similarity | 1.9 px = 0.37 m + base | scale 0.1982 m/px, rot 54.27 deg |
| [00813_08_1950-0813](https://www.loc.gov/item/sanborn00813_037/) | registered onto 022_0813 | SIFT+RANSAC similarity | 1.4 px = 0.29 m + base | scale 0.2024 m/px, rot -36.29 deg |
| **north_waterfront 1913** | | | | |
| [00813_01_1913-0002](https://www.loc.gov/item/sanborn00813_015/) | sheet similarity | 5 points + 0 street-line constraints | 0.20/0.29 m | scale 0.2025 m/px, rot 9.29 deg |
| [00813_01_1913-0003](https://www.loc.gov/item/sanborn00813_015/) | sheet similarity | 3 points + 0 street-line constraints | 1.31/1.66 m | scale 0.2034 m/px, rot 9.49 deg |
| [00813_01_1913-0019](https://www.loc.gov/item/sanborn00813_015/) | per-block similarity (zones_only) | 4 zones | Chestnut-Lombard/Battery-Sansome: 4 corners 3.55/4.48 m; Chestnut-Lombard/Sansome-Montgomery: 4 corners 2.52/3.44 m; Lombard-Greenwich/Battery-Sansome: 4 corners 2.34/2.57 m; Lombard-Greenwich/Sansome-Montgomery: 4 corners 2.09/2.26 m | (sheet fit meaningless) |
| **north_waterfront 1950** | | | | |
| [00813_01_1950-0002](https://www.loc.gov/item/sanborn00813_030/) | registered onto 015_0002 | SIFT+RANSAC similarity | 1.5 px = 0.31 m + base | scale 0.2066 m/px, rot 9.47 deg |
| [00813_01_1950-0003](https://www.loc.gov/item/sanborn00813_030/) | registered onto 015_0003 | SIFT+RANSAC similarity | 1.4 px = 0.29 m + base | scale 0.2070 m/px, rot 8.70 deg |
| [00813_01_1950-0019](https://www.loc.gov/item/sanborn00813_030/) | registered onto 015_0019 | SIFT+RANSAC similarity | 1.2 px = 0.22 m + base | scale 0.1841 m/px, rot -80.83 deg |
| **soma_industrial 1913** | | | | |
| [00813_02_1913-0115](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 1 zones | Harrison-Bryant/Spear-Main: 2 corners 1.00/1.00 m | (sheet fit meaningless) |
| [00813_02_1913-0122](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 3 zones | Folsom-Harrison/Embarcadero-Steuart: 2 corners 0.01/0.01 m; Folsom-Harrison/Steuart-Spear: 4 corners 0.35/0.47 m; Folsom-Harrison/Spear-Main: 4 corners 0.32/0.40 m | (sheet fit meaningless) |
| [00813_02_1913-0126](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 3 zones | Folsom-Harrison/Main-Beale: 4 corners 0.65/0.76 m; Folsom-Harrison/Beale-Fremont: 4 corners 0.27/0.29 m; Folsom-Harrison/Fremont-01St: 4 corners 0.38/0.39 m | (sheet fit meaningless) |
| [00813_02_1913-0127](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 3 zones | Harrison-Bryant/Main-Beale: 2 corners 0.62/0.62 m; Harrison-Bryant/Beale-Fremont: 4 corners 1.13/1.56 m; Harrison-Bryant/Fremont-01St: 4 corners 0.49/0.65 m | (sheet fit meaningless) |
| [00813_02_1913-0128](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 3 zones | Bryant-Brannan/Main-Beale: 2 corners 0.27/0.27 m; Bryant-Brannan/Beale-Fremont: 4 corners 1.21/1.45 m; Bryant-Brannan/Fremont-01St: 4 corners 0.50/0.64 m | (sheet fit meaningless) |
| [00813_02_1913-0132](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 2 zones | Folsom-Harrison/01St-Essex: 4 corners 0.19/0.22 m; Folsom-Harrison/Essex-02Nd: 4 corners 1.07/1.14 m | (sheet fit meaningless) |
| [00813_02_1913-0133](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 3 zones | Harrison-Bryant/01St-Rincon: 2 corners 0.12/0.12 m; Harrison-Bryant/Rincon-Sterling: 2 corners 0.26/0.26 m; Harrison-Bryant/Sterling-02Nd: 4 corners 0.35/0.58 m | (sheet fit meaningless) |
| [00813_02_1913-0134](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 2 zones | Bryant-Federal/01St-02Nd: 4 corners 0.35/0.47 m; Federal-Brannan/01St-02Nd: 4 corners 0.34/0.47 m | (sheet fit meaningless) |
| [00813_02_1913-0135](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 1 zones | Brannan-Townsend/01St-02Nd: 2 corners 0.93/0.93 m | (sheet fit meaningless) |
| [00813_02_1913-0136](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 1 zones | Townsend-Berry north of 2nd: 2 corners 0.53/0.53 m | (sheet fit meaningless) |
| [00813_02_1913-0140](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 2 zones | Folsom-Harrison/02Nd-Hawthorne: 4 corners 0.59/0.75 m; Folsom-Harrison/Hawthorne-03Rd: 4 corners 0.25/0.30 m | (sheet fit meaningless) |
| [00813_02_1913-0141](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 3 zones | Harrison-Perry/02Nd-03Rd: 4 corners 1.04/1.25 m; Perry-Stillman/02Nd-03Rd: 4 corners 0.25/0.29 m; Stillman-Bryant/02Nd-03Rd: 4 corners 0.32/0.46 m | (sheet fit meaningless) |
| [00813_02_1913-0142](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 2 zones | Bryant-South/02Nd-03Rd: 2 corners 0.04/0.04 m; South-Brannan/02Nd-03Rd: 2 corners 0.05/0.05 m | (sheet fit meaningless) |
| [00813_02_1913-0143](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 2 zones | Brannan-Townsend/02Nd-Stanford: 4 corners 0.91/1.19 m; Brannan-Townsend/Stanford-03Rd: 4 corners 1.23/1.62 m | (sheet fit meaningless) |
| [00813_02_1913-0144](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 1 zones | 03Rd-02Nd/Townsend-Mission: 2 corners 0.46/0.46 m | (sheet fit meaningless) |
| [00813_02_1913-0148](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 4 zones | Folsom-Harrison/03Rd-Ritch: 4 corners 0.13/0.17 m; 3751 Folsom-Shipley: 2 corners 0.29/0.29 m; 3751 Shipley-Clara: 2 corners 0.60/0.60 m; 3751 Clara-Harrison: 2 corners 1.00/1.00 m | (sheet fit meaningless) |
| [00813_02_1913-0149](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 3 zones | Harrison-Perry/03Rd-04Th: 4 corners 0.68/0.85 m; Perry-Stillman/03Rd-04Th: 4 corners 0.84/1.14 m; Stillman-Bryant/03Rd-04Th: 4 corners 0.76/0.91 m | (sheet fit meaningless) |
| [00813_02_1913-0150](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 5 zones | Bryant-Brannan/03Rd-Ritch: 4 corners 0.24/0.27 m; Bryant-Brannan/Ritch-Zoe: 4 corners 0.59/0.62 m; Bryant-Welsh/Zoe-04Th #2: 4 corners 0.28/0.39 m; Welsh-Freelon/Zoe-04Th #2: 4 corners 0.34/0.45 m; Freelon-Brannan/Zoe-04Th #2: 4 corners 0.13/0.13 m | (sheet fit meaningless) |
| [00813_02_1913-0151](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 2 zones | Brannan-Townsend/03Rd-Ritch: 4 corners 0.54/0.58 m; Brannan-Townsend/Ritch-04Th: 4 corners 0.85/0.90 m | (sheet fit meaningless) |
| [00813_02_1913-0156](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 3 zones | Folsom-Shipley/04Th-05Th: 4 corners 0.15/0.17 m; Shipley-Clara/04Th-05Th: 4 corners 0.07/0.09 m; Clara-Harrison/04Th-05Th: 4 corners 0.08/0.10 m | (sheet fit meaningless) |
| [00813_02_1913-0157](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 2 zones | Harrison-Perry/04Th-05Th: 4 corners 0.40/0.53 m; Perry-Bryant/04Th-05Th: 4 corners 0.24/0.35 m | (sheet fit meaningless) |
| [00813_02_1913-0158](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 1 zones | Bryant-Brannan/04Th-05Th: 4 corners 1.00/1.02 m | (sheet fit meaningless) |
| [00813_02_1913-0159](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 2 zones | Brannan-Bluxome/04Th-05Th: 4 corners 0.51/0.63 m; Bluxome-Townsend/04Th-05Th: 4 corners 0.45/0.56 m | (sheet fit meaningless) |
| [00813_02_1913-0164](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 3 zones | Folsom-Shipley/05Th-06Th: 4 corners 0.57/0.57 m; Shipley-Clara/05Th-06Th: 4 corners 0.11/0.12 m; Clara-Harrison/05Th-06Th: 4 corners 0.14/0.16 m | (sheet fit meaningless) |
| [00813_02_1913-0165](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 4 zones | Harrison-Bryant/05Th-Madison: 2 corners 0.12/0.12 m; Harrison-Bryant/Madison-Oak: 2 corners 0.13/0.13 m; Harrison-Bryant/Oak-Morris: 4 corners 0.75/0.79 m; Harrison-Bryant/Morris-06Th: 4 corners 0.40/0.51 m | (sheet fit meaningless) |
| [00813_02_1913-0166](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 1 zones | Bryant-Brannan/05Th-06Th: 4 corners 0.10/0.11 m | (sheet fit meaningless) |
| [00813_02_1913-0167](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 2 zones | Brannan-Bluxome/05Th-06Th: 4 corners 1.11/1.42 m; Bluxome-Townsend/05Th-06Th: 4 corners 1.45/1.76 m | (sheet fit meaningless) |
| [00813_02_1913-0172](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 4 zones | Folsom-Harrison/06Th-Harriet: 2 corners 0.11/0.11 m; Folsom-Harrison/Harriet-Columbia: 2 corners 0.11/0.11 m; Folsom-Harrison/Columbia-Sherman: 4 corners 0.36/0.44 m; Folsom-Harrison/Sherman-07Th: 4 corners 0.27/0.35 m | (sheet fit meaningless) |
| [00813_02_1913-0173](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 2 zones | Harrison-Bryant/06Th-Harriet: 2 corners 0.18/0.18 m; Harrison-Bryant/Harriet-07Th: 2 corners 0.19/0.19 m | (sheet fit meaningless) |
| [00813_02_1913-0174](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 4 zones | Bryant-Brannan/06Th-Harriet: 4 corners 0.40/0.53 m; Bryant-Brannan/Harriet-Boardman: 4 corners 0.26/0.31 m; Bryant-Brannan/Boardman-Gilbert: 4 corners 1.13/1.36 m; Bryant-Brannan/Gilbert-07Th: 4 corners 0.14/0.16 m | (sheet fit meaningless) |
| [00813_02_1913-0175](https://www.loc.gov/item/sanborn00813_016/) | per-block similarity (zones_only) | 1 zones | Brannan-Townsend/06Th-07Th: 4 corners 0.43/0.48 m | (sheet fit meaningless) |
| [00813_01_1913-0010](https://www.loc.gov/item/sanborn00813_015/) | per-block similarity (zones_only) | 4 zones | Pacific-Jackson/Embarcadero-Drumm: 2 corners 0.63/0.63 m; Pacific-Jackson/Drumm-Davis: 4 corners 0.75/0.89 m; Jackson-Washington/Embarcadero-Drumm: 2 corners 0.42/0.42 m; Jackson-Washington/Drumm-Davis: 4 corners 0.69/0.89 m | (sheet fit meaningless) |
| [00813_01_1913-0011](https://www.loc.gov/item/sanborn00813_015/) | per-block similarity (zones_only) | 2 zones | Washington-Clay/Drumm-Davis: 4 corners 1.08/1.58 m; Clay-Commercial/Drumm-Davis: 2 corners 0.82/0.82 m | (sheet fit meaningless) |
| [00813_01_1913-0015](https://www.loc.gov/item/sanborn00813_015/) | per-block similarity (zones_only) | 4 zones | Pacific-Jackson/Davis-Front: 4 corners 0.30/0.40 m; Jackson-Washington/Davis-Front: 4 corners 0.81/1.16 m; Pacific-Jackson/Front-Battery #2: 4 corners 0.20/0.25 m; Jackson-Washington/Front-Battery #2: 4 corners 1.08/1.17 m | (sheet fit meaningless) |
| [00813_01_1913-0016](https://www.loc.gov/item/sanborn00813_015/) | per-block similarity (zones_only) | 4 zones | Washington-Clay/Davis-Front: 4 corners 0.70/1.08 m; Clay-Commercial/Davis-Front: 2 corners 0.06/0.06 m; Washington-Clay/Front-Battery #2: 4 corners 0.22/0.31 m; Clay-Commercial/Front-Battery #2: 2 corners 0.08/0.08 m | (sheet fit meaningless) |
| **soma_industrial 1950** | | | | |
| [00813_02_1950-0115](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0115 | SIFT+RANSAC similarity | 1.4 px = 0.29 m + base | scale 0.2042 m/px, rot -45.51 deg |
| [00813_02_1950-0122](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0122 | SIFT+RANSAC similarity | 1.1 px = 0.22 m + base | scale 0.1877 m/px, rot -44.38 deg |
| [00813_02_1950-0126](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0126 | SIFT+RANSAC similarity | 1.4 px = 0.27 m + base | scale 0.1933 m/px, rot -44.59 deg |
| [00813_02_1950-0127](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0127 | SIFT+RANSAC similarity | 1.5 px = 0.29 m + base | scale 0.1945 m/px, rot -45.58 deg |
| [00813_02_1950-0128](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0128 | SIFT+RANSAC similarity | 1.8 px = 0.35 m + base | scale 0.1954 m/px, rot -45.19 deg |
| [00813_02_1950-0132](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0132 | SIFT+RANSAC similarity | 1.6 px = 0.30 m + base | scale 0.1872 m/px, rot -44.63 deg |
| [00813_02_1950-0133](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0133 | SIFT+RANSAC similarity | 1.6 px = 0.28 m + base | scale 0.1775 m/px, rot -44.91 deg |
| [00813_02_1950-0134](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0134 | SIFT+RANSAC similarity | 1.7 px = 0.33 m + base | scale 0.1931 m/px, rot -44.50 deg |
| [00813_02_1950-0135](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0135 | SIFT+RANSAC similarity | 1.6 px = 0.32 m + base | scale 0.2035 m/px, rot -45.22 deg |
| [00813_02_1950-0136](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0136 | SIFT+RANSAC similarity | 1.5 px = 0.30 m + base | scale 0.1999 m/px, rot -44.86 deg |
| [00813_02_1950-0140](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0140 | SIFT+RANSAC similarity | 1.4 px = 0.26 m + base | scale 0.1843 m/px, rot -44.81 deg |
| [00813_02_1950-0141](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0141 | SIFT+RANSAC similarity | 1.4 px = 0.27 m + base | scale 0.1953 m/px, rot -44.94 deg |
| [00813_02_1950-0142](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0142 | SIFT+RANSAC similarity | 1.5 px = 0.28 m + base | scale 0.1900 m/px, rot -45.15 deg |
| [00813_02_1950-0143](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0143 | SIFT+RANSAC similarity | 1.6 px = 0.29 m + base | scale 0.1881 m/px, rot -44.69 deg |
| [00813_02_1950-0144](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0144 | SIFT+RANSAC similarity | 2.1 px = 0.41 m + base | scale 0.2008 m/px, rot 44.62 deg |
| [00813_02_1950-0148](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0148 | SIFT+RANSAC similarity | 1.5 px = 0.27 m + base | scale 0.1778 m/px, rot -45.17 deg |
| [00813_02_1950-0149](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0149 | SIFT+RANSAC similarity | 1.2 px = 0.22 m + base | scale 0.1874 m/px, rot -44.45 deg |
| [00813_02_1950-0150](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0150 | SIFT+RANSAC similarity | 1.3 px = 0.23 m + base | scale 0.1721 m/px, rot -40.69 deg |
| [00813_02_1950-0151](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0151 | SIFT+RANSAC similarity | 1.7 px = 0.33 m + base | scale 0.1898 m/px, rot -44.78 deg |
| [00813_02_1950-0156](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0156 | SIFT+RANSAC similarity | 1.4 px = 0.27 m + base | scale 0.1921 m/px, rot -44.93 deg |
| [00813_02_1950-0157](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0157 | SIFT+RANSAC similarity | 1.5 px = 0.30 m + base | scale 0.1956 m/px, rot -44.67 deg |
| [00813_02_1950-0158](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0158 | SIFT+RANSAC similarity | 1.6 px = 0.32 m + base | scale 0.2004 m/px, rot -44.60 deg |
| [00813_02_1950-0159](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0159 | SIFT+RANSAC similarity | 1.5 px = 0.29 m + base | scale 0.1942 m/px, rot -44.78 deg |
| [00813_02_1950-0164](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0164 | SIFT+RANSAC similarity | 1.5 px = 0.29 m + base | scale 0.1892 m/px, rot -44.67 deg |
| [00813_02_1950-0165](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0165 | SIFT+RANSAC similarity | 1.6 px = 0.30 m + base | scale 0.1809 m/px, rot -44.86 deg |
| [00813_02_1950-0166](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0166 | SIFT+RANSAC similarity | 1.4 px = 0.28 m + base | scale 0.2016 m/px, rot -44.95 deg |
| [00813_02_1950-0167](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0167 | SIFT+RANSAC similarity | 1.3 px = 0.26 m + base | scale 0.1948 m/px, rot -44.92 deg |
| [00813_02_1950-0172](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0172 | SIFT+RANSAC similarity | 1.3 px = 0.25 m + base | scale 0.1846 m/px, rot -45.46 deg |
| [00813_02_1950-0173](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0173 | SIFT+RANSAC similarity | 1.9 px = 0.34 m + base | scale 0.1833 m/px, rot -44.86 deg |
| [00813_02_1950-0174](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0174 | SIFT+RANSAC similarity | 1.6 px = 0.28 m + base | scale 0.1748 m/px, rot -44.87 deg |
| [00813_02_1950-0175](https://www.loc.gov/item/sanborn00813_031/) | registered onto 016_0175 | SIFT+RANSAC similarity | 1.4 px = 0.27 m + base | scale 0.2007 m/px, rot -45.44 deg |
| [00813_01_1950-0010](https://www.loc.gov/item/sanborn00813_030/) | registered onto 015_0010 | SIFT+RANSAC similarity | 1.4 px = 0.23 m + base | scale 0.1577 m/px, rot -80.24 deg |
| [00813_01_1950-0011](https://www.loc.gov/item/sanborn00813_030/) | registered onto 015_0011 | SIFT+RANSAC similarity | 1.4 px = 0.23 m + base | scale 0.1656 m/px, rot -80.11 deg |
| [00813_01_1950-0015](https://www.loc.gov/item/sanborn00813_030/) | registered onto 015_0015 | SIFT+RANSAC similarity | 1.1 px = 0.17 m + base | scale 0.1476 m/px, rot -80.22 deg |
| [00813_01_1950-0016](https://www.loc.gov/item/sanborn00813_030/) | registered onto 015_0016 | SIFT+RANSAC similarity | 1.3 px = 0.18 m + base | scale 0.1373 m/px, rot -80.44 deg |


## Coverage

* **soma_industrial 1913 / 1950**: Folsom → Townsend between the Embarcadero / Steuart and 7th St (vol. 2 sheets
  115–175 as listed), the blocks north of King St between 2nd and 3rd (144) and Townsend / King / Berry at 2nd (136,
  only the part north of 2nd St); Mission Bay south of Townsend is left to `mission_bay_*`. Produce Market: Pacific →
  Clay between Battery and Drumm, plus the Pacific / Jackson / Washington blocks between Drumm and the Embarcadero
  (sheet 10). Coverage is the union of the block zones actually fitted (streets drawn too wide are in coverage only
  where a zone reaches into them).
* **What burned**: all of the SoMa and Produce Market coverage lay inside the 1906 burned area. The 1913 maps show the
  rebuilt city (1906–1913); nothing traced here predates the fire. The pre-fire (1899) state is **not traced** (see
  open items), so `sf_predecessors` still generates the 1850s–1906 fabric there; every 1913 footprint starts after the
  fire.
* **butchertown 1914 / 1950**: sheets 805 (Islais Creek, Kentucky / Illinois / Michigan St north of the creek,
  Railroad Ave, Arthur → Davidson Ave), 810 (Railroad Ave → Mendell, Evans → Burke: the wholesale butchers' row and
  the South San Francisco Packing & Provision Co.), 812 (Mendell → Lane: California Fertilizer Works, Hawaiian
  Fertilizer Co., Miller & Lux), 813 (Davidson → Hudson, Keith → Jennings: San Francisco Rendering Co., houses), 807 /
  808 (Rankin → 3rd St, Davidson → Hudson: Legallet-Hellwig Tanning Co., Miller & Lux buildings, the railway), 809 (Newhall → Mendell, Hudson →
  Evans). The north part of 805 (north of Islais Creek) can overlap a Potrero / Dogpatch tracing — `assemble` cuts
  out any `potrero_point` / `dogpatch` / `potrero` coverage present when it runs; the current outputs were assembled after
  `potrero_point_coverage.geojson` existed (no overlap left); rerun `assemble` whenever a neighbouring coverage changes
  (or add a new area name to `EXCLUDE`).
* **north_waterfront 1913 / 1950**: Powell → Grant, Beach → North Point (sheet 2, east of the Fisherman's Wharf
  coverage), Grant → Kearny, North Point → Bay (sheet 3: the North Point bonded warehouses), and Chestnut → Greenwich,
  Battery → Montgomery (sheet 19: North Point Dock warehouses, Merchants Ice & Cold Storage). Not the piers.

## Not done / open items

* **1899 editions** (soma_industrial, north_waterfront) were not traced: SoMa 1899 is vol. 2
  (https://www.loc.gov/item/sanborn00813_009/, sheets 125–232), the Produce Market and north waterfront 1899 vol. 1
  (`_008`, sheets 59, 60, 90, 91 for east of Taylor were downloaded by the waterfront pass). Everything there burned
  in 1906.
* **Hunters Point**: vol. 8 sheets 815 (India Basin shore, Union Iron Works Dry Dock Co.'s grounds) and 816 (Hunters
  Point dry docks No. 1 and 2, 1914) were downloaded but not georeferenced: 816 has no street at all and 815 only
  vacated India Basin streets. Control would have to come from today's dry-dock outlines (OSM / Overture) — not done.
  No `hunters_point_*` files.
* **North waterfront**: only sheets 2, 3, 19. Not done: 4 (Montgomery / Francisco, Embarcadero yard), 9 and 13
  (Broadway → Union, Front / Battery, SP Broadway freight shed, Belt R.R. yards), 20 (Greenwich → Union, Telegraph
  Hill warehouses), the pier and bulkhead sheets 5–7; no tracks traced there.
* **Produce Market**: sheet 11's blocks between Drumm and the Embarcadero (Merchant St drawn wider than scale), and
  sheet 12 (Clay → Market, Embarcadero Center site) were not traced; sheets 9 and 13 (north of Pacific) likewise.
* **Butchertown**: sheets 806 (India Basin, Albion Brewery), 811 (Hudson → Fairfax, houses), 814 (India Basin shore)
  and the rest of vol. 8 (Bayview) not traced. Buildings standing on piles over the water on 805 / 810 are found only
  where outlined in black; some were missed.
* **Storeys** (see Counts) and most names were not read; a 50 % pass over the large warehouses would improve heights.
* **Tracks**: hand-traced, not complete (only sheets with rail listed above), the Townsend St lines on 159 / 167 / 175 and the
  Bluxome line on 159 failed the line test (dropped); tracks added after 1913/14 are missing on the 1950 maps. Railroad names only
  where labelled.
* No rows were added to `data/tables/notable_demolished.csv` (dates for the Produce Market clearance and the end of
  Butchertown were not verified in this pass). Candidates: the Produce Market blocks (sheets 10, 11, 15, 16; cleared
  for the Golden Gateway project, late 1950s – early 1960s), the Butchertown slaughterhouses (810, 812), the
  Legallet-Hellwig tannery (808), Pump Station No. 1 (016_0143_s1, which still stands at 2nd / Townsend).

## Reproduce

```
python pipeline/sanborn_trace_industrial.py all            # index + fetch + georef + extract (+ regions, tracks) + assemble
python pipeline/sanborn_trace_industrial.py assemble       # outputs only (after another tool's coverage changed)
python pipeline/sanborn_trace_industrial.py register 031_0134 016_0134   # redo one SIFT registration
python pipeline/sanborn_trace_industrial.py snap 016_0135   # snap new hand-traced tracks (once; writes control)
python pipeline/sanborn_trace_industrial.py carry 016_0135 031_0135      # move 1913 tracks onto the 1950 sheet
```
The control files hold final pixel positions (`norefine`), so a rerun reproduces the outputs. New entry types in
`control/industrial/*.json` (understood by `world_of` in the industrial tool): `bcx` = block corner from two straight
centreline fits (`[street a, near a, street b, near b]`, `sa`/`sb` = side of the block along each street, `wa`/`wb`
widths in ft) and `xl` = crossing of two straight centreline fits. Extra keys: `confidence_cap` (`medium` / `low`
for sheets with weak control), `residential` (dwelling rule for small frame buildings), `valid_poly_px`.
