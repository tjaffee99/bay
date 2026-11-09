# Sanborn tracing: Berkeley (downtown, Southside, West Berkeley, Northside) — 1911

Real building footprints of Berkeley as the 1911 Sanborn maps show them, where the city changed most since: downtown
(Shattuck Ave, the Berkeley High / Civic Center blocks), the Southside blocks the University cleared for Sproul Plaza,
the Student Union, Edwards Stadium, the residence halls and People's Park, and the West Berkeley (Ocean View)
industrial waterfront at University Ave that I-80, the 1920s–50s factories and today's 4th St replaced. Traced from the
Library of Congress scans of the Sanborn Map Co. *Insurance Maps of Berkeley, California*, 1911 (public domain:
"Library of Congress, Geography and Map Division, Sanborn Maps Collection"), with the Oakland method and schema
(`README_oakland.md`): tool `pipeline/sanborn_trace_eastbay_cities.py berkeley …` (it configures
`pipeline/sanborn_trace_eastbay.py` for this city), control in `control/berkeley/`.

**Map years.** LOC has Berkeley 1894 (one volume, 14 sheets) and 1911 (vols. 1–2) online. The 1917 additional sheets
(`sanborn00419_011`) and the 1929 (`_004`–`_006`) and 1950 (`_007`–`_010`) editions are catalogued but **not digitized**
(`digitized: false`, no images). So Berkeley has one map year here (1911); `apply_sanborn` dates a building on a single
map from its neighbourhood (start) and ends it at today's building on the spot or a clearance (end). The 1894 edition is
not traced (different plates, small coverage).

## Files

| file | content |
|---|---|
| `berkeley_downtown_1911.geojson` | Milvia – Oxford / Fulton, Berkeley Way – Dwight Way along Shattuck Ave (sheets 72, 73, 84, 85, 93) and Grove St (MLK Jr Way) – Milvia, Center – Bancroft (83: the 1911 Berkeley High School buildings) |
| `berkeley_southside_1911.geojson` | Fulton – College Ave, Allston Way – Dwight Way (sheets 86–90, 94–98): the blocks north of Bancroft that became Edwards Stadium (5215/5216), Sproul Hall / Sproul Plaza (5219/5220), the Student Union (5221), California Field (1904–22 football grandstands, 5223/5224); south of Bancroft the residence-hall blocks and People's Park (5351) |
| `berkeley_west_1911.geojson` | West Berkeley shore – 8th St, Virginia St – Bancroft Way (sheets 47, 48, 61, 62, 63, 75): Monarch Oil, Everding starch works, El Dorado Oil Works, West Berkeley Lumber, the municipal wharf, Ramona Candy, Standard Soap / Western Refining, Van Emon Elevator, Tillman & Bendel, the SP depot, Ocean View houses |
| `berkeley_northside_1911.geojson` | 169 houses north of the campus (Le Roy Ave, Buena Vista Way, La Loma Ave, Cedar St …) **traced from the same 1911 sheets by OpenHistoricalMap volunteers** (CC0), all destroyed in the 1923 Berkeley fire; re-written in this schema (see below) |
| `berkeley_<area>_coverage.geojson` | one polygon per area and map year (`map_year` 1911): the fitted block zones + 12 m (half the streets). Inside it an empty spot was empty on the map. Northside: only 8 m around each OHM building (the OHM tracing is partial) |
| `control/berkeley/<key>.json` | per sheet: blocks (`streets`, `px4_est` hand estimates, refined `px4`, `edge_q`, corners with control type), `with` (blocks fitted together), `skip`, `scale_prior`, `confidence_cap` (sheet or block), `residential`, `notes` |
| `control/berkeley/labels.json` | 58 names / uses read off the sheets by pixel position (25 % image) |
| `control/berkeley/areas.json` | sheets per area |

Keys are `<LOC item suffix>_<sheet>`: `002_0072` = `sanborn00419_002` (1911 vol. 1) sheet 72.

### Feature properties

As `README_oakland.md` (`id`, `map_year`, `volume`, `volume_label`, `loc_url`, `sheet`, `sheet_no`, `iiif`, `stories`,
`stories_source`, `material`, `use`, `use_source`, `name`, `sanborn_colour`, `confidence`, `georef`, `georef_rms_m`,
`extraction`, `area_m2`, `modern_overlap`). Storeys are **not read** (default rule of the Oakland tool: frame < 30 m²
shed 1; frame ≤ 300 m² dwelling 2 on residential sheets, store 2 on the commercial downtown sheets 72, 73, 84, 85;
frame ≥ 300 m² warehouse 1; brick / stone / concrete 2). New here: `use_source = default (rule: commercial street
frontage)` — a default-use building whose centroid lies within 50 m of Shattuck Ave, 45 m of University / San Pablo Ave
or 40 m of Telegraph Ave is a store. Per-block `confidence_cap` = `medium` for blocks with no control of their own
(campus and superblock blocks placed by a neighbour's fit). The Northside file has `address` (OHM `Address` +
`StreetName`), `georef = OpenHistoricalMap way <id>`, `sheet` / `iiif` null, `confidence = medium`, `extraction` naming
OHM; storeys from OHM `building:levels` (8 houses) else the default rule; `use = flats` where OHM's comment (from the
sheet) says so.

## Counts

| file | features | high / medium / low | area (1000 m²) | modern_overlap ≥ 0.5 | materials | named |
|---|---|---|---|---|---|---|
| berkeley_downtown_1911 | 603 | 224 / 286 / 93 | 77.8 | 450 | frame 522, brick 67, stone 8, concrete 6 | 15 |
| berkeley_southside_1911 | 1019 | 586 / 433 / 0 | 108.1 | 621 | frame 1004, brick 14, stone 1 | 16 |
| berkeley_west_1911 | 791 | 569 / 222 / 0 | 57.4 | 397 | frame 779, brick 12 | 18 |
| berkeley_northside_1911 (OHM) | 169 | 0 / 169 / 0 | 16.6 | 100 | frame 169 | 0 |

Coverage: downtown 33.9 ha, Southside 61.6 ha, West Berkeley 57.8 ha, Northside 8.4 ha (8 m around the houses).
`modern_overlap` ≥ 0.5 marks a building still standing *or* a newer one on the same spot; `apply_sanborn` keeps only
those that today's building (built by 1913) matches out of the predecessor set.

## Sources

* Sanborn Map Company, *Insurance Maps of Berkeley, California*, 1911, vol. 1:
  https://www.loc.gov/item/sanborn00419_002/ — sheets 47, 48, 61, 62, 63, 72, 73, 75, 83, 84, 85, 86, 87, 88, 89, 90,
  93, 94, 95, 96, 97, 98 (IIIF images at 25 %, ≈ 1640 × 1950 px, 0.2015 m/px at 50 ft = 1 in); key map sheet `0000`
  of vols. 1 and 2 (https://www.loc.gov/item/sanborn00419_003/) used to find sheets. Item JSON and images cached in
  `data/raw/sanborn_loc_berkeley/`.
* OpenHistoricalMap (CC0): 169 ways tagged `source = 1911 Sanborn Map`, `end_date = 1923-09-17`, `wikidata = Q4561337`
  (1923 Berkeley Fire), queried via https://overpass-api.openhistoricalmap.org/api/interpreter (bbox 37.84, −122.33,
  37.90, −122.23); relation 2743804 "1923 Berkeley Fire Boundary" (source: East Bay Water Company, "Map of Berkeley
  Fire Zone, 17 Sept 1923", in *The Story of the Berkeley Fire*, Berkeley Public Library).
* Control: Overture Maps transportation segments, release 2026-10-21.0 (`roads_region.parquet` + `roads_local.parquet`
  within (−122.325, 37.845, −122.235, 37.895); ODbL), and Alameda County parcels (`alameda_county_2021`, public copy, see
  `data/research/region_buildings.md`) dissolved into blocks for property lines. `modern_overlap` against
  `region5_building.parquet` (Overture, ODbL).

## Method

As Oakland (`README_oakland.md`): block outlines estimated by eye on a half-size grid view, sides snapped onto the drawn
block lines (`refine`; Berkeley's 1911 block lines are thin, so a side counts as found from a darkness peak of 0.12),
property corners from today's parcel blocks (`pc`), a similarity fit per block (or per group of blocks, `with`),
outlier corners dropped (> 3 m and > 3× the median), colour classes split along partition walls. Additions in the city
tool: a street may have its property line up to 32 m from the centreline (`wide_streets`: Shattuck Ave is ~150 ft wide
south of Center St); `respec` / `freeze`-free control files (the refined pixels are stored, reruns reproduce the fits);
per-block confidence caps; the commercial-frontage use rule.

**Findings (control).**
* The plate scale holds everywhere: good block fits are 0.1996–0.2048 m/px. The Southside and West Berkeley sheets
  fit to 0.1–1.1 m per block; downtown 1.1–3.5 m.
* Downtown east of Shattuck between University and Center, the roadway today called **Kala Bagai Way** (renamed 2023)
  is the 1911 east side of Shattuck Ave; the SP depot in Shattuck's median (blocks 5178/5179) is outside the traced
  zones.
* **Milvia St jogged at University Ave in 1911** (block 3159 north of University is drawn ~15 m east of the line of the
  blocks south of it; today Milvia is straight): 3159's 4-corner fit has RMS 3.5 m (low).
* **Fulton St between Bancroft and Durant** has today's property lines 3–5 m off its line elsewhere (block 176 m wide
  today, 184 m drawn): block 5214 (sheet 86) is controlled by its Ellsworth corners with the plate-scale prior; the
  Edwards Stadium blocks 5215/5216 north of Bancroft take that fit. Ellsworth St carried a double streetcar track drawn
  beside the block line (refine radius 12 px there).
* Campus blocks north of Bancroft (5217–5224) have no surviving property corners (the campus parcel); each is placed by
  the fit of the block across Bancroft (RMS 0.2–1.1 m; capped `medium`).
* **West Berkeley**: Bristol St is today's Hearst Ave; 3rd St (the Southern Pacific right of way) has no road today, so
  the blocks beside it are fitted per row across it (the plate is to scale: sheet 48 fits all six blocks with one
  similarity to 0.99 m over 8 corners). Today's 7th St runs diagonally from Allston Way to 8th St at Bancroft and
  Bancroft is closed between 6th and 8th St: blocks 2559/2560 take the row fit of 2558. Sheet 47 (the shore at
  University Ave, filled ground, today I-80 and the University Ave overpass) has control only along 2nd St (two corners
  + plate-scale prior; sheet capped `medium`); its inset (Pacific Guano & Fertilizer Co.) has one corner and is not
  traced.

## Georeferencing per sheet

Residuals in metres between the transformed pixel and the parcel-derived corner; "N blocks: x" = one group fit for N
block zones. Scale / rotation column lists the distinct fits of the sheet.

| sheet (LOC item) | ed. | block zones / fits | control corners | RMS (m) per fit | scale (m/px), rotation |
|---|---|---|---|---|---|
| [002_0047](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 3 zones, 1 fit(s) | 2 | 2593+2574+2594: 0.75 | 0.2012, 14.25 deg |
| [002_0048](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 6 zones, 1 fit(s) | 8 | 6 blocks: 0.99 | 0.2011, 14.79 deg |
| [002_0061](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 6 zones, 4 fit(s) | 16 | 2592+2591: 1.62; 2590: 1.09; 2575+2576: 1.83; 2577: 1.25 | 0.1957, 14.78 deg; 0.1958, 14.78 deg; 0.1991, 14.82 deg; 0.2005, 14.19 deg |
| [002_0062](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 6 zones, 4 fit(s) | 12 | 2572+2571: 0.62; 2555+2556: 0.66; 2570: 0.32; 2557: 0.38 | 0.2008, 14.35 deg; 0.2012, 14.67 deg; 0.2014, 14.31 deg; 0.2015, 14.65 deg |
| [002_0063](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 6 zones, 6 fit(s) | 24 | 2589: 0.29; 2588: 0.34; 2587: 0.43; 2578: 0.36; 2579: 0.31; 2580: 0.38 | 0.1997, 14.71 deg; 0.1998, 14.8 deg; 0.2004, 15.01 deg; 0.2011, 15.05 deg; 0.2021, 14.78 deg; 0.2022, 14.85 deg |
| [002_0072](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 3 zones, 3 fit(s) | 11 | 3159: 3.47; 3158: 1.91; 3127: 1.28 | 0.2016, 8.52 deg; 0.2036, 9.33 deg; 0.2059, 8.67 deg |
| [002_0073](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 3 zones, 3 fit(s) | 11 | 5180: 2.96; 5177: 1.13; 5176: 3.03 | 0.1967, 6.69 deg; 0.2024, 6.52 deg; 0.2041, 5.61 deg |
| [002_0075](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 6 zones, 5 fit(s) | 17 | 2569: 0.16; 2568: 0.31; 2567: 0.33; 2558: 0.25; 2559+2560: 0.33 | 0.2003, 14.94 deg; 0.2007, 14.69 deg; 0.2007, 14.76 deg; 0.2015, 15.0 deg; 0.2019, 14.92 deg |
| [002_0083](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 3 zones, 2 fit(s) | 6 | 3125: 1.94; 3124+3121: 1.69 | 0.2004, 9.41 deg; 0.2009, 9.45 deg |
| [002_0084](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 3 zones, 3 fit(s) | 12 | 3126: 2.0; 3123: 2.94; 3122: 2.81 | 0.1998, 8.81 deg; 0.2009, 9.34 deg; 0.201, 9.72 deg |
| [002_0085](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 3 zones, 3 fit(s) | 10 | 5175: 1.26; 5174: 0.38; 5173: 1.61 | 0.1948, 9.86 deg; 0.1995, 9.85 deg; 0.1999, 10.35 deg |
| [002_0086](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 3 zones, 1 fit(s) | 2 | 5214+5215+5216: 0.55 | 0.2016, 10.45 deg |
| [002_0087](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 3 zones, 1 fit(s) | 4 | 5244+5217+5218: 0.25 | 0.2012, 9.53 deg |
| [002_0088](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 3 zones, 1 fit(s) | 4 | 5253+5219+5220: 0.22 | 0.2028, 9.17 deg |
| [002_0089](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 2 zones, 1 fit(s) | 4 | 5328+5221: 1.08 | 0.2028, 9.52 deg |
| [002_0090](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 2 zones, 1 fit(s) | 4 | 5354+5223_5224: 0.82 | 0.203, 9.62 deg |
| [002_0093](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 3 zones, 3 fit(s) | 12 | 5172: 0.79; 5171: 0.79; 5170: 0.51 | 0.2023, 10.13 deg; 0.2028, 10.17 deg; 0.2028, 10.22 deg |
| [002_0094](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 4 zones, 4 fit(s) | 16 | 5213: 0.57; 5211: 0.5; 5212: 0.42; 5210: 0.35 | 0.2006, 9.47 deg; 0.2016, 9.21 deg; 0.2016, 9.57 deg; 0.202, 9.43 deg |
| [002_0095](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 3 zones, 3 fit(s) | 12 | 5243: 0.21; 5242: 0.3; 5241: 0.35 | 0.2005, 9.99 deg; 0.2011, 9.98 deg; 0.2028, 9.89 deg |
| [002_0096](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 3 zones, 3 fit(s) | 11 | 5252: 0.32; 5251: 0.81; 5250: 0.58 | 0.2009, 9.36 deg; 0.2034, 9.39 deg; 0.2048, 9.42 deg |
| [002_0097](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 3 zones, 3 fit(s) | 11 | 5327: 0.29; 5326: 0.98; 5325: 0.1 | 0.1996, 9.74 deg; 0.2009, 9.53 deg; 0.202, 9.46 deg |
| [002_0098](https://www.loc.gov/item/sanborn00419_002/) | 1911 v.1 | 3 zones, 3 fit(s) | 12 | 5353: 0.48; 5352: 0.71; 5351: 0.66 | 0.2002, 9.38 deg; 0.2007, 9.4 deg; 0.201, 9.45 deg |

## The 1923 fire (`data/manual/redevelopment_areas.csv`, row `berk_fire_1923`)

The fire of 17 Sep 1923 is entered as a dated clearance (like San José's 1887 Chinatown fire, `sj_market_street_chinatown`):
`clear_start = clear_end = 1923.71`, ring = the OHM fire-zone boundary (56 ha), `prior_fabric = mixed`, id prefix
`berk_` (so `region_predecessors.corridor_fill`, which looks only at `oak_` / `sj_` areas, ignores it). Effects through
the existing code: the OHM Northside houses (and any procedural predecessors) inside it end in the fire; imputed years
of today's buildings there cannot predate the clearance (+2 years); survivors with recorded years keep them.

## Coverage

Downtown: Milvia – Oxford, Berkeley Way – Center (72, 73); Grove – Shattuck, Center – Bancroft (83, 84); Shattuck –
Fulton, Allston – Dwight (85, 93). Southside: Fulton – College, Allston – Dwight (86–90, 94–98). West Berkeley: the
shore – 5th St, Virginia – Bancroft, and 5th – 8th St, Bristol – Bancroft (47, 48, 61, 62, 63, 75). Northside: the
houses OHM traced.

## Open items

* Not traced: downtown sheets 70, 71, 82 (west of Milvia), the Shattuck median depot blocks; West Berkeley north of
  Virginia St (sheets 11–16, 32, 49, 50, 60) and south of Bancroft (vol. 2: 121–125, 131–133: the Dwight Way / Potter St
  industrial waterfront, Heinz, Durkee); the Northside fire zone beyond the 169 OHM houses (vol. 1 sheets 20–33, 42–46);
  south Berkeley / Lorin and Emeryville (vol. 2); the 1894 edition (`sanborn00419_001`).
* One map year only (no later Berkeley Sanborn is online): end years come from today's buildings and clearances.
* Storeys not read; names for 58 labelled buildings (49 placed; e.g. Stiles Hall and the Eldorado coconut storage
  missed their footprints).
* Tracks not traced (the SP Shattuck Ave line and the Ellsworth / Telegraph streetcar lines are street running; the SP
  main line along 3rd St is in `historic_rail`).

## Reproduce

```
python pipeline/sanborn_trace_eastbay_cities.py berkeley all        # fetch + georef + extract + tracks + assemble
python pipeline/sanborn_trace_eastbay_cities.py berkeley assemble   # outputs only (control files are final)
python pipeline/sanborn_trace_eastbay_cities.py berkeley check      # validation + PNG per area (data/interim/sanborn_berkeley/)
```
`python pipeline/sanborn_trace_eastbay_cities.py berkeley ohm` re-queries OpenHistoricalMap (cached in
`data/raw/ohm_berkeley/`) and rewrites `berkeley_northside_1911.geojson` / `_coverage.geojson`; the fire ring of
`berk_fire_1923` was copied from OHM relation 2743804 (simplified to 1e-5°).
