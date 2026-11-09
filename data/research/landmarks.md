# Landmark reconstruction research — Bay Area Through Time

Research notes for faithful low-poly reconstructions of San Francisco landmarks.
Companion table: `data/tables/landmarks.csv`. Reference photos: `data/raw/reference_photos/<id>/`
(each folder also has a `_meta.jsonl` with Commons page URL, author, licence, thumbnail URL).

Conventions
- Units are metres unless stated; original imperial figures are kept in brackets where they are the documented value.
- "Bearing" = compass bearing of a main axis, degrees clockwise from true north (an axis bearing of 174° is the same line as 354°).
- Footprints measured from OpenStreetMap ("OSM") geometry fetched from `api.openstreetmap.org` / Nominatim in Nov 2026: centroid, minimum-area oriented bounding box (L × W) and long-axis bearing. OSM is © OpenStreetMap contributors (ODbL). OSM `height` values are contributor estimates unless matched by a cited source.
- "Estimated from photo X" = I measured proportions in the named reference photo against a known documented dimension. Treat as ±10–20 %.
- Commons thumbnails: the API now only serves standard widths, so files are 960 px (some 1280 px) wide.

Coverage summary and biggest uncertainties (read this first)
- Fully researched with OSM-measured footprints, documented heights and photo checks: Golden Gate Bridge (incl. OSM 3D tier data for the towers), Legion of Honor, Salesforce Tower, Salesforce Transit Center/Park, Transamerica Pyramid, Painted Ladies (per-house positions and colours), Oracle Park, Chase Center, Cow Palace, current Kezar, Golden Gate Park structures, P2 buildings.
- Weakest data (placeholders flagged in their sections): original 1925 Kezar bowl geometry; Candlestick (no plan dimensions; heights estimated); Seals Stadium / Ewing Field / Recreation Park (dimensions only from field distances and street boundaries); old Transbay Terminal (1939–2010); old City Hall (1899–1906) position; 1894/1919 de Young and 1916 Cal Academy buildings; Embarcadero Freeway route coordinates; original Bay Bridge east-span pier coordinates; Salesforce Tower taper profile (photo-derived); Legion of Honor court width (photo-derived).
- Dates that sources disagree on are noted inline (e.g. GGB vehicle opening 28 vs 29 May 1937; Kezar demolition timing; Sutro Baths operating years; Union Square garage year unverified).
- No free photos were downloaded for: old City Hall, 1863/1896 Cliff House, 1894/1919 de Young, 1916 Cal Academy, 1915 Palace of Fine Arts, Transbay Terminal, Sutro Baths, Embarcadero Freeway, Crissy Field airfield era (Wikimedia rate-limited this session's IP for 10-minute periods).

---

## Golden Gate Bridge (`golden_gate_bridge`)

**Dates**
- Construction began 5 Jan 1933 — https://www.goldengate.org/exhibits/facts-and-figures-about-the-bridge/
- Suspended deck complete 19 Apr 1937 — https://www.goldengate.org/exhibits/hanging-the-roadway-deck/
- Opened: Pedestrian Day 27 May 1937; vehicles from 28 May 1937 (Wikipedia, citing contemporary press). The Bridge District exhibit page says "open to vehicular traffic on May 29, 1937" — sources disagree by a day; use 1937 either way. https://en.wikipedia.org/wiki/Golden_Gate_Bridge
- Alterations: lower lateral (bottom) deck bracing added 1953–54 after the 1 Dec 1951 wind closure (https://www.goldengate.org/exhibits/resisting-the-twisting/); concrete deck replaced with steel orthotropic deck in 747 sections 1982–86 (Wikipedia); seismic retrofit Phase 1 (Marin viaduct) 1997–2001, Phase 2 (SF approach viaduct, south anchorage housing, Fort Point arch, pylons S1/S2) Jun 2001–Jul 2008, Phase 3 (towers / suspension spans) ongoing (https://www.goldengate.org/bridge/bridge-projects/seismic-retrofit/phase-ii/); railings between walkways and traffic 2003; movable median barrier 2015; suicide-deterrent net (stainless net ~6 m below sidewalk) built 2018–2024 (Wikipedia). None of these change the massing at the scale of the model.

**Location** (from OSM geometry of tower legs/piers, see method note above)
- South (San Francisco) tower centre: 37.814013, -122.477892 (legs at -122.477736 and -122.478047)
- North (Marin) tower centre: 37.825500, -122.479234
- Tower-to-tower distance computed from these points: 1,275 m (official 1,280 m) — good agreement.
- Mid-span: 37.819757, -122.478563
- Bridge axis bearing 173–174° / 353–354° (runs ~6–7° west of due north going toward Marin).
- South anchorage housing centre: 37.809601, -122.477426 (OSM footprint ~101 × 40 m)
- Pylon S2 (south end of Fort Point arch): 37.80994, -122.47741; Pylon S1 (north end of arch / start of south side span): 37.81096, -122.47752
- Pylon N1: 37.82859, -122.47960; Pylon N2 / North anchorage housing centre: 37.829063, -122.479678 (OSM footprint ~109 × 48 m)
- South abutment (end of SF approach viaduct at toll plaza): ≈ 37.80800, -122.47665. Toll plaza booths ≈ 37.80720, -122.47560.
- North abutment (end of Marin approach viaduct): ≈ 37.83230, -122.48070. The Marin approach curves: its axis bearing is ~163° vs 174° for the main bridge.
- South tower foundation fender ("bathtub"): oval concrete wall centred on the tower, ~90 m (across the bridge axis) × ~45 m (along the axis), wall ~5 m thick, ~4 m above water (OSM `man_made=breakwater` geometry); clearly visible as an oval ring elongated across the bridge in `Aerial_view_of_Golden_Gate_Bridge_from_the_south_dllu.jpg` (author: Daniel L. Lu (user:dllu); licence: CC BY-SA 4.0).

**Dimensions** (official = Golden Gate Bridge Highway & Transportation District, https://www.goldengate.org/bridge/history-research/statistics-data/design-construction-stats/)
- Total length abutment to abutment 2,737 m (8,981 ft); to toll plaza 2,788 m (9,150 ft).
- Suspension span (main + 2 side spans) 1,966 m (6,450 ft); main span 1,280 m (4,200 ft); each side span 343 m (1,125 ft).
- Fort Point arch: steel arch spanning 97 m (318 ft) over the fort (https://www.goldengate.org/exhibits/fort-point-arch/; ENR rounds to 320 ft).
- Approaches (not officially itemised; derived = 2,737 − 1,966 − 97 ≈ 674 m for both approach viaducts plus the two anchorage/pylon housings). OSM: SF approach viaduct ≈ 223 m (curving), Marin approach ≈ 320 m (curving).
- Width 27 m (90 ft) overall; roadway between curbs 19 m (62 ft); each sidewalk 3 m (10 ft). Main cables are on the bridge centrelines 27.4 m (90 ft) apart (OSM leg centres 27.4 m apart).
- Tower height 227 m (746 ft) above water; 152 m (500 ft) above roadway → roadway at the towers ≈ 75 m above water (OSM 3D model has deck at 73–75 m).
- Clearance above mean higher high water at mid-span 67 m (220 ft).
- Tower leg base 10 × 16 m (33 × 54 ft) each leg; long side along the bridge axis. Legs are cellular (riveted steel cells).
- Stiffening trusses on each side of the deck: 7.6 m (25 ft) deep, Warren with verticals, panel points every 15.2 m (50 ft) at the suspenders (https://www.goldengate.org/exhibits/hanging-the-roadway-deck/).
- Main cables: 2, each 0.92 m (36⅜ in) diameter incl. wrapping, 2,332 m long, 27,572 wires; cable sag at mid main span 143 m (470 ft) (US Naval Institute Proceedings, Apr 1935, https://www.usni.org/magazines/proceedings/1935/april/golden-gate-and-san-francisco-bay-bridges). Cable profile ≈ parabola: saddle at tower top (≈ 225 m) down to ≈ 82–84 m above water at mid-span, i.e. a few metres above the roadway.
- Suspenders: 250 pairs, 15.2 m (50 ft) apart, 68 mm (2-11/16 in) ropes; cable bands every 50 ft.
- South tower foundation 34 m below mean low water.

Tower tiers (OSM 3D building:part mapping of both towers — contributor-measured, consistent with the official 227 m / 10 × 16 m figures; heights above water):
| Element | z from–to (m) | Plan size per leg (along axis × across) |
|---|---|---|
| Concrete pier (both legs) | 0–13 | 42 × 20.3 (across × along) |
| Leg base | 13–21 | 15.6 × 9.6 |
| Leg tier 1 | 21–74 | 13.8 × 7.5 |
| Leg tier 2 | 74–123 | 11.7 × 7.5 |
| Leg tier 3 | 123–162 | 9.8 × 7.5 |
| Leg tier 4 | 162–195 | 9.8 × 5.4 |
| Leg tier 5 (top) | 195–225 | 7.4 × 3.3 |
| Struts between legs (along-axis thickness ≈ 3.7–3.8 m) | 24–26, 50–52 (below deck), 111–121, 151–161, 185–193, 215–223 | span 20–24 m between legs |

**Massing description for low-poly modelling** (verified against the photos listed below)
1. Two towers, each = 2 legs on a shared concrete pier. Legs are boxes that step inward at each tier (table above). Above the deck the legs are joined by 4 horizontal portal struts (the openings get shorter going up: the portal shapes "decrease on ascent" — goldengate.org Art Deco page), the top strut sits just below the tower top; struts have vertical ribbing on their faces (seen in the HAER photo). Tower top: small stepped cap with the aircraft beacon.
2. Below the deck each tower has a large X-brace between the legs plus horizontal struts (clearly visible under the deck of the south tower in the HAER photo and under the north tower in the aerial).
3. South tower stands in the water on its pier inside the oval fender ring (~90 × 45 m, wall ~4 m above water). North tower stands on a pier at the Marin shoreline (Lime Point), no fender ring.
4. Deck: a 27 m wide box/U section, 7.6 m deep (the stiffening trusses), roadway on top at ≈ 75 m above water at the towers, crowning slightly to mid-span (clearance 67 m to the truss underside). Paint the truss sides with a triangulated (Warren) texture or leave as a solid orange box.
5. Main cables: two parabolic catenaries per span. Main span: from tower tops (≈ 225 m) to ≈ 83 m at mid-span. Side spans: from tower tops down to the cable housings at pylons S1 / N1 (~343 m away), then on into the anchorage housings.
6. Suspenders: vertical lines every 15.2 m from cable to deck edge on both sides (250 pairs total over the suspension spans); for low poly, draw as thin lines or a semi-transparent "harp" plane.
7. Fort Point arch (south end): a two-rib steel arch spanning 97 m, its springings low beside the fort (~15–20 m above water, estimated from HAER photo), crown just under the deck, with vertical spandrel posts and diagonal bracing between arch and deck truss. It sits between two concrete pylons: S2 (south) is the tallest, rising ~10 m above deck level with a stepped Art Deco top; S1 (north) rises a few metres above the deck (estimated from `HAER_CAL_38-SANFRA_140-3_fort_point_arch.jpg` (author: Lowe, Jet Related names: Strauss, Joseph B Pacific Bridge Company John Roebling'; licence: Public domain)). Pylons are ~10 × 4.5 m per side (OSM), unpainted concrete.
8. Anchorage housings: large stepped concrete blocks (~101 × 40 m south, ~109 × 48 m north per OSM) at deck level that enclose the cable anchorages; pylons S2 / N2 rise from them.
9. Approach viaducts: steel deck-truss viaducts on steel bents (orange), ~223 m (SF, curving east toward the toll plaza) and ~320 m (Marin, curving to bearing ~163°), descending to grade at the abutments.
10. Toll plaza at the SF end (~37.8072, -122.4756): row of small booths under a canopy; 1937 Art Deco toll plaza building.

**Colors**
- Official "International Orange" formula published by the District: CMYK C0 M69 Y100 K6; closest off-the-shelf paint Sherwin-Williams "Fireweed" SW 6328; nearest Pantone PMS 173/174/180 (https://www.goldengate.org/bridge/history-research/bridge-features/color-art-deco-styling/).
- Naive CMYK→sRGB of the formula: **#F04A00** (very saturated; print conversion).
- Wikipedia's "International orange (Golden Gate Bridge)" swatch: **#C0362C** (https://en.wikipedia.org/wiki/International_orange) — closer to how the bridge reads in photos; OSM's 3D model uses `#bf4e3b`. Recommendation for flat shading: #C0362C for lit faces.
- Concrete pylons / anchorages / tower piers / fender: light warm grey ~#BDB8AE (estimated from photos). Roadway asphalt dark grey ~#4A4A4A.
- Historical: originally red-lead primer + lead topcoat (1937); repainted with zinc silicate primer + vinyl topcoat from the mid-1960s (Wikipedia) — same orange colour.

**Reference photos**
- `data/raw/reference_photos/golden_gate_bridge/Golden_Gate_Bridge_aerial_photo_2010-09-21_1_.jpg` — [File:Golden Gate Bridge aerial photo 2010-09-21 (1).jpg](https://commons.wikimedia.org/wiki/File:Golden_Gate_Bridge_aerial_photo_2010-09-21_(1).jpg) — author: Reedy — CC BY-SA 3.0. Full side elevation from the west: both towers, cable sag, SF anchorage housing + Fort Point arch at right, south-tower fender ring.
- `data/raw/reference_photos/golden_gate_bridge/Aerial_view_of_Golden_Gate_Bridge_from_the_south_dllu.jpg` — [File:Aerial view of Golden Gate Bridge from the south dllu.jpg](https://commons.wikimedia.org/wiki/File:Aerial_view_of_Golden_Gate_Bridge_from_the_south_dllu.jpg) — author: Daniel L. Lu (user:dllu) — CC BY-SA 4.0. Plan-like oblique along the axis: portal struts, oval fender, deck width, Marin approach curve.
- `data/raw/reference_photos/golden_gate_bridge/HAER_CAL_38-SANFRA_140-3_fort_point_arch.jpg` (author: Lowe, Jet Related names: Strauss, Joseph B Pacific Bridge Company John Roebling'; licence: Public domain) — [HAER CA-31-3, "General view looking north with approach span deck arch on left"](https://commons.wikimedia.org/wiki/File:GENERAL_VIEW,_LOOKING_NORTH,_WITH_APPROACH_SPAN_DECK_ARCH_ON_LEFT_-_Golden_Gate_Bridge,_Spanning_mouth_of_San_Francisco_Bay,_San_Francisco,_San_Francisco_County,_CA_HAER_CAL,38-SANFRA,140-3.tif) — Jet Lowe, Historic American Engineering Record — public domain. Fort Point arch, pylons S1/S2, below-deck X-bracing, portal struts, fender.

**Sources**
- https://www.goldengate.org/bridge/history-research/statistics-data/design-construction-stats/
- https://www.goldengate.org/exhibits/ (fort-point-arch, hanging-the-roadway-deck, resisting-the-twisting, a-bathtub-for-the-south-tower, facts-and-figures-about-the-bridge)
- https://www.goldengate.org/bridge/history-research/bridge-features/color-art-deco-styling/
- https://www.usni.org/magazines/proceedings/1935/april/golden-gate-and-san-francisco-bay-bridges (cable sag)
- https://en.wikipedia.org/wiki/Golden_Gate_Bridge
- OSM ways 1330586852 (SF tower), 1330832666 (Marin tower), 1560010167 (South Anchorage), 1560010149 (North Anchor), 1560010166 (Fort Point Arch), 432712872/1330739248 (fender)

---

## California Palace of the Legion of Honor (`legion_of_honor`)

**Dates**
- Site: city Golden Gate Cemetery 1870–1909 (Wikipedia). Building is a full-scale replica of the French Pavilion at the 1915 PPIE, itself a ¾-scale version of the Hôtel de Salm (Palais de la Légion d'Honneur), Paris (Wikipedia).
- Groundbreaking 1921 (delayed by WWI) — https://en.wikipedia.org/wiki/Legion_of_Honor_(museum)
- Opened Armistice Day, 11 Nov 1924 — https://famsf.org/legion/history
- Mar 1992 – Nov 1995: seismic strengthening, restoration and 35,000 sq ft underground expansion by Edward Larrabee Barnes & Mark Cavagnero; small glass pyramid skylight inserted in the Court of Honor (Wikipedia). Exterior massing unchanged apart from the pyramid.
- 1984 Holocaust Memorial (George Segal) off the NW corner of the grounds; 2000 di Suvero sculpture in the front plaza (Wikipedia).

**Location**
- Centre of footprint 37.784510, -122.500846 (OSM relation 21115818), Lincoln Park, ground elevation ~113 m (OSM `ele`).
- Main axis bearing 49° / 229°: the entrance gate and forecourt face NE (bearing ~49°) toward the circular drive with the *El Cid* equestrian statue (37.78521, -122.50040); the domed rotunda is on the axis at the SW (rear) end (dome centre 37.784297, -122.501101).
- Glass pyramid skylight (1995) in the Court of Honor: 37.784637, -122.500624.

**Dimensions** (no published building dimensions found; values from OSM 3D building:part mapping and photo estimates — treat as ±10 %)
- Overall footprint ≈ 94 m (along the NE–SW axis) × 60 m (OSM relation 21115818, area ≈ 5,300 m²).
- Two long gallery wings along the axis, each ≈ 88 × 24 m, height 17 m including a ≈ 2 m low hipped roof (OSM ways 1540337302 / 1540337304). Connecting rear block ≈ 39 × 13 m, 17 m (OSM 1540337303).
- Court of Honor colonnades: two ≈ 48 × 12.5 m colonnade ranges, 11 m high (OSM 1540327029/-030). The court itself reads ≈ 25 m wide × ≈ 45 m long in the 1932 aerial (estimated from photo `California_-_San_Francisco_-_NARA_-_23935697.jpg` (author: Unknown authorUnknown author or not provided; licence: Public domain); OSM part geometry here looks schematic).
- Entrance gate/arch pavilion at the NE end: ≈ 16 m high (OSM 1540333313/-314), ≈ 5 × 5 m piers.
- Rotunda + dome at the rear: drum Ø ≈ 13.6 m to 16 m height, dome rising ≈ 5 m to ≈ 21 m (OSM way 1410202318: height 21, roof:height 5, roof:shape dome).
- Main-entrance portico inside the court: 4 tall Corinthian columns carrying an attic inscribed "HONNEUR ET PATRIE", ≈ 14 m tall; the court colonnades are single-storey Ionic columns (≈ 7–8 m, estimated from `…LCCN2011630619…jpg` against the 11 m colonnade height), ≈ 3 m spacing, with a balustrade above.
- Glass pyramid ≈ 5.2 × 5.2 m, ~1–2 m tall.

**Massing description for low-poly modelling**
1. Base: rectangle 94 × 60 m rotated so its long axis is 49°/229°.
2. Two side gallery wings: boxes 88 × 24 × 15 m with 2 m low hipped roofs, along the NW and SE long sides.
3. Rear (SW) block between the wings: box ≈ 39 × 13 × 15 m + hipped roof.
4. Rotunda on the rear facade centreline: cylinder Ø 13.6 m, 16 m high, ringed by engaged Corinthian columns, topped by a shallow dome (5 m rise) with statues on the drum (seen in `500px_photo_55877656_.jpeg` (author: Hugh Nelson; licence: CC BY 3.0)). In the 1932 aerial the dome sits at the far (SW) end, partly projecting from the rear block.
5. Court of Honor: open paved rectangle ≈ 25 × 45 m between the wings, lined on both long sides by Ionic colonnades (11 m tall boxes with a balustrade — model as a slab roof on a row of thin cylinders or a single box with a dark recessed face).
6. Main entrance portico at the SW end of the court: projecting box ≈ 20 m wide × 6 m deep × 14 m with 4 columns and an attic.
7. Front (NE) side: triumphal-arch gateway in the centre (16 m tall, arched opening) with low Ionic colonnade screens linking it to the ends of the two wings (visible in the 1932 aerial).
8. Forecourt to the NE: circular drive / lawn with El Cid statue; balustraded terraces wrap the SE side (aerial).
9. 1995+: tiny glass pyramid in the court (optional).

**Colors**
- Walls/columns: cream limestone-look cast stone, ≈ #E3DCCB (estimated from `…LCCN2011630619…jpg`, `500px_photo_55877656_.jpeg` (author: Hugh Nelson; licence: CC BY 3.0)).
- Dome: pale verdigris / yellow-green, ≈ #B9C07F (estimated from `500px_photo_55877656_.jpeg` (author: Hugh Nelson; licence: CC BY 3.0)); statues same cream as walls.
- Gallery roofs: grey hipped roofs with long skylight strips, ≈ #7A7E84 (estimated from 1932 aerial; B/W so tone only).

**Reference photos**
- `data/raw/reference_photos/legion_of_honor/California_-_San_Francisco_-_NARA_-_23935697.jpg` (author: Unknown authorUnknown author or not provided; licence: Public domain) — [File:California - San Francisco - NARA - 23935697.jpg](https://commons.wikimedia.org/wiki/File:California_-_San_Francisco_-_NARA_-_23935697.jpg) — US Army Air Corps aerial, 1932 (NARA) — public domain. Best overall massing view (whole building from the SE, dome at the rear).
- `data/raw/reference_photos/legion_of_honor/California_Palace_of_the_Legion_of_Honor_San_Francisco_California_LCCN2011630619.tif.jpg` — [File:…LCCN2011630619.tif](https://commons.wikimedia.org/wiki/File:California_Palace_of_the_Legion_of_Honor,_San_Francisco,_California_LCCN2011630619.tif) — Carol M. Highsmith — public domain. Court of Honor with the Thinker, colonnades and entrance portico.
- `data/raw/reference_photos/legion_of_honor/500px_photo_55877656_.jpeg` — [File:500px photo (55877656).jpeg](https://commons.wikimedia.org/wiki/File:500px_photo_(55877656).jpeg) — Hugh Nelson — CC BY 3.0. Rotunda drum and dome colour.

**Sources**
- https://en.wikipedia.org/wiki/Legion_of_Honor_(museum)
- https://famsf.org/legion/history
- OSM relation 21115818 and building:part ways 1540337302/-303/-304, 1540327029/-030, 1410202318, 1540333313

---

## Salesforce Tower (`salesforce_tower`)

**Dates**
- Developer/architect competition won 2007 (Hines / Pelli Clarke Pelli); ceremonial groundbreaking 27 Mar 2013, below-grade work from late 2013 — https://en.wikipedia.org/wiki/Salesforce_Tower
- Topped out (final beam) 6 Apr 2017 — https://www.cnbc.com/2017/04/06/salesforce-tower-san-franciscos-tallest-building-views.html
- First tenants moved in 8 Jan 2018 (opening) — Wikipedia. Crown LED artwork *Day for Night* (Jim Campbell, 11,000 LEDs) activated 21 May 2018 — Wikipedia.
- Site was previously the ground-level entrance/ramps of the 1939 Transbay Terminal (demolished 2010–11).

**Location**
- Centre of footprint 37.789780, -122.396959 (OSM way 431972186), 415 Mission St at First & Fremont, SE side of Mission St. Faces are parallel to the SoMa street grid: axes at bearings 45° and 135° (OSM bearing 140° for the rounded square — treat as 45°/135°).
- Directly NW of (and linked by a bridge to) the Salesforce Transit Center roof park.

**Dimensions**
- Architectural top 326 m (1,070 ft); roof 296 m (970 ft); 61 floors; 34 elevators — Wikipedia infobox / CNBC. Some reports at topping out said 1,072 or 1,077 ft; use 1,070 ft.
- Footprint at grade: rounded square ≈ 54.4 × 54.2 m (OSM way 431972186, 83 vertices; area consistent with ~29,000 sq ft floor plates). Lot 50,514 sq ft (Wikipedia).
- Crown: hollow, open-topped extension of the facade above the 61st floor, clad in perforated white aluminium panels; reported as 130 ft (most sources) or 150 ft tall. The *Day for Night* LED screen occupies the upper ~6–9 floors of the facade/crown (sources vary).
- Facade: glass curtain wall in a lattice of white aluminium vertical fins + horizontal perforated sunshades projecting up to 0.6 m (2 ft) — Wikipedia.
- Taper (no published profile found; estimated from `Salesforce_Tower_from_Ina_Coolbrith_Park-01445.jpg` (author: Frank Schulenburg; licence: CC BY-SA 4.0), where the crown top is ≈ 0.50 × the width measured at ~45 % of the height): treat as base width 54 m held nearly constant (very slight inward slope) for the lower ~55 % of the height, then curving inward with increasing rate to ≈ 26–28 m at the top (326 m). Plan stays a rounded square all the way up; corner radius ≈ 15 % of the side at the base growing to ≈ 25–30 % at the crown (the roof aerial shows a "squircle").

**Massing description for low-poly modelling**
1. A single lofted "obelisk/bullet": stack ~8–12 rounded-square rings (8 segments per corner is enough) with side length s(z): z=0 → 54 m; z=100 → 53 m; z=180 → 51 m; z=230 → 47 m; z=270 → 41 m; z=300 → 34 m; z=326 → 27 m (profile estimated from photo, see above).
2. The top ~40–45 m (≈ z 285–326) is the open crown: same outer skin but hollow with an open top; from above you see a ring-shaped roof terrace/equipment deck inside (visible in `Salesforce_Tower_Roof.jpg` (author: InvadingInvader; licence: CC BY-SA 4.0)). For low poly, a capped solid is fine; optionally inset the top cap 3 m down to suggest the hollow.
3. Faces: a central vertical seam/rib runs down the middle of each face from the crown (visible as a white vertical line in the Ina Coolbrith photo) — optional.
4. Ground: lobby podium flush with the tower; a pedestrian bridge connects the tower at roughly park level (≈ 21 m) to Salesforce Park to the SE.

**Colors**
- Overall reads pale silver-blue glass with white fins: body ≈ #B9C9D6 (lit) / #8FA7BC (shade); crown ≈ #E4E8EC (white perforated aluminium). Estimated from `Salesforce_Tower_from_Ina_Coolbrith_Park-01445.jpg` (author: Frank Schulenburg; licence: CC BY-SA 4.0).
- Night: crown LED artwork (white/various).

**Reference photos**
- `data/raw/reference_photos/salesforce_tower/Salesforce_Tower_from_Ina_Coolbrith_Park-01445.jpg` — [File:Salesforce Tower from Ina Coolbrith Park-01445.jpg](https://commons.wikimedia.org/wiki/File:Salesforce_Tower_from_Ina_Coolbrith_Park-01445.jpg) — author: Frank Schulenburg — licence: CC BY-SA 4.0. Long-lens near-elevation: full taper silhouette and crown.
- `data/raw/reference_photos/salesforce_tower/Salesforce_Tower_Roof.jpg` — [File:Salesforce Tower Roof.jpg](https://commons.wikimedia.org/wiki/File:Salesforce_Tower_Roof.jpg) — author: InvadingInvader — licence: CC BY-SA 4.0. Drone view straight down onto the open crown: rounded-square plan, fins, interior deck; Salesforce Park visible at lower left.
- `data/raw/reference_photos/salesforce_tower/Salesforce_Tower_Completed_2018.jpg` — [File:Salesforce Tower Completed 2018.jpg](https://commons.wikimedia.org/wiki/File:Salesforce_Tower_Completed_2018.jpg) — author: Leijurv — licence: CC BY-SA 4.0. Corner view from the street: rounded corners and fin grid.

**Sources**
- https://en.wikipedia.org/wiki/Salesforce_Tower ; https://www.cnbc.com/2017/04/06/salesforce-tower-san-franciscos-tallest-building-views.html ; https://www.aisc.org/modernsteel/news/2017/april/steel-shots-san-frans-tallest-tower-tops-out/
- OSM way 431972186

---

## Salesforce Transit Center + Salesforce Park (`salesforce_transit_center`; predecessor `transbay_terminal_1939`)

**Dates**
- Predecessor: Transbay Terminal opened 1939 (Key System / interurban trains over the Bay Bridge; bus-only from 1958); damaged in 1989 Loma Prieta quake; services moved to a temporary terminal 7 Aug 2010; demolition of terminal and ramps completed Sep 2011 — https://en.wikipedia.org/wiki/Salesforce_Transit_Center
- New centre: Prop H funding 1999; construction began 2010; limited Muni service 26 Dec 2017; full opening incl. rooftop park 12 Aug 2018; closed 25 Sep 2018 after cracked steel beams were found over Fremont St; park reopened 1 Jul 2019, buses 13 Jul 2019, full facility 11 Aug 2019 — Wikipedia.
- Future phase 2 ("The Portal" rail extension) underground only — no change to massing.

**Location**
- Centre of footprint 37.789010, -122.397009 (OSM way 542375290). Long axis bearing 45°/225° (parallel to Mission St), between Minna and Natoma streets, from Beale St (NE end ≈ 37.7906, -122.3954) to 140 ft east of 2nd St (SW end ≈ 37.7874, -122.3986). It bridges over First St and Fremont St (streets run beneath at grade).
- Bus ramp / cable-stayed bus bridge leaves the SE side toward the Bay Bridge (visible in `Salesforce_Park_and_bus_bridge__seen_from_Salesforce_Tower.jpg` (author: Fullmetal2887; licence: CC BY-SA 4.0): single white pylon with a fan of stays).

**Dimensions**
- Length ≈ 436 m (1,430 ft), width ≈ 50 m (165 ft) — Wikipedia; OSM outline 436.4 × 55.9 m (incl. facade bulges).
- Floor area 1,500,000 sq ft; 4 levels above ground (street/Grand Hall, 2nd-floor concourse, 3rd-floor bus deck, roof park) + 2 below-grade rail levels (shell) — https://pcparch.com/work/salesforce-transit-center ; Wikipedia.
- Salesforce Park: 5.4 acres (≈ 2.2 ha) on the roof, about 21 m (70 ft) above the street; 0.5-mile walking loop; 600 trees, 16,000 plants; amphitheater lawn (1,000 people) at the W end; Ned Kahn "Bus Fountain" > 1,200 ft long with 247 jets; two domed skylights + a central oculus/"light column" over the Grand Hall; aerial gondola from Mission & Fremont — https://www.tjpa.org/salesforce-transit-center/salesforce-park ; https://pcparch.com/work/salesforce-transit-center
- Facade: "gently curving, undulating" pearlescent-white perforated aluminium panels, perforation pattern based on Penrose tiling — pcparch.com, Wikipedia.
- Heights not officially published: park deck ≈ 21 m; facade band from its undulating lower edge at ≈ 8–12 m up to the park parapet at ≈ 22–24 m; trees on the roof add 5–12 m (estimated from `Salesforce_Transit_Center__San_Francisco__1__2023-07-18.jpg` (author: The wub; licence: CC BY-SA 4.0) using people ≈ 1.7 m and the 70 ft park height).

**Massing description for low-poly modelling**
1. Main body: long box 436 × 50 m along 45°, from z = 8 m (underside of bus deck/facade band) to z ≈ 22 m (park level), raised on a ground storey: glass box set back ~3–5 m behind the facade line, with white tree-like / V-shaped steel columns (pairs leaning outward) carrying the upper levels.
2. Facade "lattice": wrap the upper box in a white skin whose plan outline is wavy — bulging outward by up to ~3 m in long, smooth waves (wavelength ~60–100 m) and whose bottom edge also waves up/down by ~2–3 m. One curved, slightly convex surface per bay is enough; texture with a perforated pattern or use semi-transparent white.
3. Gaps where First St and Fremont St pass under: the box continues as a bridge over each street (no ground storey there).
4. Roof: flat park surface at ≈ 21 m covered in lawns, paths and tree clusters; amphitheater lawn at the SW end; two small glass domes + an oculus near the Fremont–First middle section (the Grand Hall "light column" sits by Mission & Fremont).
5. Main entrance on Mission St at Fremont: the facade sweeps up in a concave curve over a tall glazed Grand Hall entrance (see `Salesforce_Transit_Center_main_entrance.jpg` (author: Fullmetal2887; licence: CC BY-SA 4.0)).
6. Bus ramp: elevated roadway leaving the bus deck (z ≈ 15 m) eastward over Howard/Main streets toward the Bay Bridge, with a cable-stayed span (one white pylon ~30 m tall, estimated from photo).

**Colors**
- Facade panels: white / pearlescent ≈ #ECEDEC; columns white ≈ #E6E6E3; glazing ≈ #9DB4BE; park lawn ≈ #6FA83A, trees ≈ #3E6B2C (estimated from photos).

**Old Transbay Terminal (1939–2010)** — for the pre-2010 timeline: a long low (~3-storey) concrete terminal building on the same block facing Mission St at First/Fremont, plus elevated train/bus ramps looping to the Bay Bridge. Detailed massing not researched (time); use a ~200 × 50 m, ~15 m high block at the NE half of the present footprint and elevated ramps toward the bridge as a placeholder (low confidence).

**Reference photos**
- `data/raw/reference_photos/salesforce_transit_center/Salesforce_Park_and_bus_bridge__seen_from_Salesforce_Tower.jpg` — [File:Salesforce Park and bus bridge, seen from Salesforce Tower.jpg](https://commons.wikimedia.org/wiki/File:Salesforce_Park_and_bus_bridge,_seen_from_Salesforce_Tower.jpg) — author: Fullmetal2887 — licence: CC BY-SA 4.0. Roof park from above, wavy facade edge, cable-stayed bus bridge.
- `data/raw/reference_photos/salesforce_transit_center/Salesforce_Transit_Center__San_Francisco__1__2023-07-18.jpg` — [File:Salesforce Transit Center, San Francisco (1) 2023-07-18.jpg](https://commons.wikimedia.org/wiki/File:Salesforce_Transit_Center,_San_Francisco_(1)_2023-07-18.jpg) — author: The wub — licence: CC BY-SA 4.0. Side elevation: undulating perforated skin, V columns, trees on roof.
- `data/raw/reference_photos/salesforce_transit_center/Salesforce_Transit_Center_main_entrance.jpg` — [File:Salesforce Transit Center main entrance.jpg](https://commons.wikimedia.org/wiki/File:Salesforce_Transit_Center_main_entrance.jpg) — author: Fullmetal2887 — licence: CC BY-SA 4.0. Main entrance (Mission & Fremont), Penrose perforation pattern.

**Sources**
- https://en.wikipedia.org/wiki/Salesforce_Transit_Center ; https://pcparch.com/work/salesforce-transit-center ; https://www.tjpa.org/salesforce-transit-center/salesforce-park
- OSM way 542375290

---

## Transamerica Pyramid (`transamerica_pyramid`)

**Dates**
- Site of the Montgomery Block (1853–1959). Construction began Dec 1969; completed 1972 — https://en.wikipedia.org/wiki/Transamerica_Pyramid
- Tallest building in SF 1972–2017 (passed by Salesforce Tower during construction) — Wikipedia. 2020s renovation (Foster + Partners) affected the base/lobby only.

**Location**
- Centre of footprint 37.795187, -122.402651 (OSM way 24222973), 600 Montgomery St between Clay and Washington; ground elevation ~5 m.
- Footprint square rotated with the downtown street grid: faces at bearings 81° and 171° (i.e. ~9° clockwise from true N/E). "East" face (elevator wing) faces bearing 81° toward Montgomery St; "west" face (stair/smoke-tower wing) faces 261°.

**Dimensions**
- Height 260 m (853 ft) to the spire tip; top occupied floor at 212 m (695 ft); 48 floors (some sources 49) — Wikipedia infobox; https://vibrationdata.com/earthquakes/Pyramid.htm gives 845 ft apex-to-ground.
- Base width 53.3 m (175 ft) per side — vibrationdata.com; OSM footprint 54.5 × 54.3 m ✓.
- Spire: the top 65 m (212 ft) is the hollow spire (aluminium clad) — Wikipedia. In photo `SF_Transamerica_full_CA.jpg` (author: Daniel Schwen; licence: CC BY-SA 2.5) the narrow spire is visible from ≈ 205 m up.
- Wings: two vertical "wings" (elevator shaft on the east, stairs + smoke tower on the west) start at the 29th floor — Wikipedia, vibrationdata. OSM maps their tops as a 27.2 (E–W) × 6.5 m (N–S) bar with a gabled top at 215 m.
- Base: ground-level arcade of inclined precast concrete columns forming triangular openings (a truss above the first floor — vibrationdata), ≈ 12–15 m tall (estimated from `SF_Transamerica_full_CA.jpg` (author: Daniel Schwen; licence: CC BY-SA 2.5); Wikipedia: "four-story base").
- Facade: precast panels faced with crushed quartz, punched windows (each window has a deep splayed reveal — see `South_face_of_the_Transamerica_Pyramid__2017.jpg` (author: Dllu; licence: CC BY-SA 4.0)).

**Massing description for low-poly modelling**
1. Main body: square pyramid frustum, base 53.3 × 53.3 m at z = 0 tapering linearly toward an apex at 260 m (half-width h(z) = 26.65 × (1 − z/260)); faces rotated 9° (bearings 81°/171°). Measured photo ratio (width incl. wings at the wing tops ÷ base width ≈ 0.47) is consistent with this linear taper plus wings.
2. Spire: from z ≈ 200 m to 260 m continue the same pyramid but render as a separate, slightly greyer/metallic piece (it reads as a narrower needle because the wings frame its base).
3. Wings (×2, on the E and W faces): vertical-sided slabs 6.5 m thick (N–S), whose outer faces sit 13.6 m from the centre line (total E–W span 27.2 m). They emerge from the sloping face where the pyramid half-width drops below 13.6 m (z ≈ 127 m by the linear profile; documented start "29th floor") and run up to z ≈ 205–215 m, ending in a top sloping inward toward the spire. Below the emergence point they disappear into the pyramid.
4. Base arcade: ring of A-shaped (inverted-V) concrete legs around the bottom ≈ 12–15 m on all four sides (5 arches per side visible in the photo); for low poly, a dark recessed band at the bottom with triangular pilasters.
5. Redwood Park (½ acre) on the east side with tall redwoods — optional trees.

**Colors**
- Walls: white quartz-aggregate precast ≈ #E6E3DB; window recesses dark ≈ #3C4048; spire aluminium ≈ #C8CCCF (estimated from `SF_Transamerica_full_CA.jpg` (author: Daniel Schwen; licence: CC BY-SA 2.5)).

**Reference photos**
- `data/raw/reference_photos/transamerica_pyramid/SF_Transamerica_full_CA.jpg` — [File:SF Transamerica full CA.jpg](https://commons.wikimedia.org/wiki/File:SF_Transamerica_full_CA.jpg) — author: Daniel Schwen — licence: CC BY-SA 2.5. Near-elevation of the north face from Coit Tower: taper, both wings, spire, base arcade. Best single reference.
- `data/raw/reference_photos/transamerica_pyramid/Transamerica_Pyramid_from_Coit_Tower_____-_panoramio.jpg` — [File:Transamerica Pyramid from Coit Tower コイトタワー (サンフランシスコ) - panoramio.jpg](https://commons.wikimedia.org/wiki/File:Transamerica_Pyramid_from_Coit_Tower_%E3%82%B3%E3%82%A4%E3%83%88%E3%82%BF%E3%83%AF%E3%83%BC_(%E3%82%B5%E3%83%B3%E3%83%95%E3%83%A9%E3%83%B3%E3%82%B7%E3%82%B9%E3%82%B3)_-_panoramio.jpg) — author: Yoshio Kohara — licence: CC BY 3.0. Same view in context with the skyline.
- `data/raw/reference_photos/transamerica_pyramid/South_face_of_the_Transamerica_Pyramid__2017.jpg` — [File:South face of the Transamerica Pyramid, 2017.jpg](https://commons.wikimedia.org/wiki/File:South_face_of_the_Transamerica_Pyramid,_2017.jpg) — author: Dllu — licence: CC BY-SA 4.0. Facade texture/colour.

**Sources**
- https://en.wikipedia.org/wiki/Transamerica_Pyramid ; https://vibrationdata.com/earthquakes/Pyramid.htm
- OSM way 24222973, building:parts 136615987 (wings), 451336902

---

## Painted Ladies / "Postcard Row", 710–722 Steiner St (`painted_ladies`)

**Dates**
- Built 1892–1896 by developer Matthew Kavanaugh, who lived next door in the 1892 house at 722 Steiner — https://en.wikipedia.org/wiki/Painted_ladies. Per-house construction years are not documented in the sources found; use 1892 for 722 and 1894 (midpoint) ± 2 years for 710–720.
- Group is called "Postcard Row" / "Seven Sisters". Sources differ on whether 722 is part of the group: Wikipedia says "710–720 Steiner" (six matching houses) but "Seven Sisters" counts 722 as the seventh. Model all seven.
- Colour history: like most SF Victorians they were painted grey/drab for decades (WWI/WWII "battleship grey" story is unverified per Wikipedia); multi-colour "colorist" repaints started in the 1960s–70s. Present colours are owner choices and change every 10–20 years.
- Within the Alamo Square Historic District (designated 1984).

**Location** (OSM building footprints; east side of Steiner St between Hayes (south) and Grove (north), facing west onto Alamo Square)
| House | Centroid lat, lon | Footprint (depth × width) | OSM height / roof |
|---|---|---|---|
| 710 (south end, next to 700 Steiner apartment block) | 37.776062, -122.432725 | 15.9 × 6.9 m | 12 m, gabled |
| 712 | 37.776125, -122.432739 | 16.1 × 6.9 m | 12 m, gabled |
| 714 | 37.776193, -122.432739 | 16.1 × 6.9 m | 12 m, gabled |
| 716 | 37.776252, -122.432742 | 15.9 × 6.9 m | 12 m, gabled |
| 718 | 37.776319, -122.432750 | 15.9 × 7.1 m | 12 m, gabled |
| 720 | 37.776374, -122.432764 | 16.1 × 6.9 m | 12 m, gabled |
| 722 (north end, Kavanaugh house) | 37.776463, -122.432781 | 18.8 × 9.1 m | 13 m, hipped |
- Long axis of each lot (front-to-back) bearing 81°/261°; the facades face 261° (WSW) across Steiner St to the park. Row length ≈ 50 m.
- Immediately south: 700 Steiner, a ~24 m tall apartment building (OSM) that appears at the right edge of the classic view.

**Dimensions**
- Six matching narrow Queen Anne row houses (710–720), each ≈ 6.9 m wide (≈ 25 ft lots) × 16 m deep; 722 is larger (≈ 9 × 19 m) with a hipped roof (OSM ways 261412896/-895/-900/-894/-879/-899/-887).
- Height: OSM gives 12 m (710–720, 3 m gable) and 13 m (722, 4 m hipped roof). From `San_Francisco__CA__USA__Painted_Ladies_--_2022_--_3059.jpg` (author: Dietmar Rabich; licence: CC BY-SA 4.0) (height:width ≈ 2.1 for 716 incl. raised basement and stoop) the gable peak is ≈ 13–14.5 m above the sidewalk; eaves ≈ 9.5–10 m. Use 13.5 m to the ridge from sidewalk level, ~1.5 m of which is the raised basement/garage plinth.
- Storeys: garage/basement at sidewalk level (garage doors and front stoops visible), two main floors, attic in the front gable.

**Massing description for low-poly modelling** (each of 710–720; from the 2022 photos)
1. Box 6.9 m wide × 16 m deep × 10 m to the eaves, facade facing 261°.
2. Front-gabled roof: ridge running front-to-back (perpendicular to the street), 3–3.5 m tall triangular gable facing the street with a strong projecting eave (decorated gable field).
3. Two-storey angled bay window on one side of the facade (left side as seen from the park in most houses), projecting ~0.8 m, from first floor up to the eave; the other half has the entry porch and a small balcony/porch roof at second-floor level.
4. Front stoop: steps rising ~2 m from the sidewalk to the entry; a garage door in the plinth (several houses).
5. 722: wider box 9 × 19 m, hipped roof (steeper, ~4 m) with a front dormer/turret, wrap-around corner porch; reads darker (navy) in current paint.
6. The houses step slightly with the slope of Steiner St; the tall eucalyptus/ficus street trees partly hide the lower floors (optional).

**Colours** (current as of the 2022 photos; body / trim / accent; hex values estimated by eye and spot-sampling from `…2022_--_3059.jpg` — lighting and shade shift them, treat as ±1 shade)
| House | Body | Trim | Accents | Roof |
|---|---|---|---|---|
| 722 | slate navy #36404D | white #F2F0EA | light blue-grey | brown-grey shingle #9C8C7C (hipped) |
| 720 | olive khaki #9C9165 | cream #E8DDB5 | ochre #C9A54F | dark grey #4A4A4A |
| 718 | sage grey-green #8F9479 | off-white #EAE6D6 | darker sage #6E7357 | dark grey #4A4A4A |
| 716 | golden tan / mustard #D4B77A | white #F1ECDD | brick red #8E2F25 (gable triangles) | brown #8F7D67 |
| 714 | cream #E4D6BE | burgundy-brown #7A3B2E | gold #C9A26A | red-brown #8C543D |
| 712 | powder blue #A8C2D0 | white #F4F4F0 | mid blue #5F7F9A | dark grey #434142 |
| 710 | beige / khaki #CFC3A6 | cream #F0EADB | brown #6B5A47 | dark grey #515151 |
(OSM `building:colour` tags exist but are older — e.g. OSM has 722 as olive #96a55b; the 2022 photos show navy. Prefer the photo values above.)

**Reference photos**
- `data/raw/reference_photos/painted_ladies/San_Francisco__CA__USA__Painted_Ladies_--_2022_--_3059.jpg` — [File:San Francisco (CA, USA), Painted Ladies -- 2022 -- 3059.jpg](https://commons.wikimedia.org/wiki/File:San_Francisco_(CA,_USA),_Painted_Ladies_--_2022_--_3059.jpg) — author: Dietmar Rabich — licence: CC BY-SA 4.0. Frontal elevation of all seven houses (left = 722 north end, right = 710 south end) with 700 Steiner at far right.
- `data/raw/reference_photos/painted_ladies/San_Francisco__CA__USA__Painted_Ladies_--_2022_--_3063.jpg` — [File:San Francisco (CA, USA), Painted Ladies -- 2022 -- 3063.jpg](https://commons.wikimedia.org/wiki/File:San_Francisco_(CA,_USA),_Painted_Ladies_--_2022_--_3063.jpg) — author: Dietmar Rabich — licence: CC BY-SA 4.0. Same, slightly different angle (good for roof pitch and colours).

**Sources**
- https://en.wikipedia.org/wiki/Painted_ladies ; https://en.wikipedia.org/wiki/Alamo_Square,_San_Francisco
- OSM ways 261412896, 261412895, 261412900, 261412894, 261412879, 261412899, 261412887

---

## Stadiums and arenas

General note: San Francisco's professional baseball/football venues in chronological order — Recreation Grounds (25th & Folsom, 1868–1884) → Central Park / "Recreation Park" (8th & Market, 1884–1906) → Recreation Park (14th & Valencia, 1907–1930s) → Ewing Field (1914 only for the Seals) → Seals Stadium (1931–1959) → Candlestick Park (1960–2014) → Oracle Park (2000–). Football: Kezar (1925–1989; 49ers 1946–1970) → Candlestick (49ers 1971–2013). Source for the list: https://en.wikipedia.org/wiki/Recreation_Park_(San_Francisco)

### Oracle Park (`oracle_park`)

**Dates** — groundbreaking 11 Dec 1997; opened 31 Mar 2000 as Pacific Bell Park (SBC Park 2004–05, AT&T Park 2006–18, Oracle Park 2019–); centre-field renovation (bullpens moved) Oct 2019–Jun 2020 — https://en.wikipedia.org/wiki/Oracle_Park

**Location** — stadium polygon centroid 37.778661, -122.389847 (OSM relation 7325085, 212 × 191 m, sides parallel to the SoMa grid, bearings 45°/135°). Block bounded by King St (NW side), 2nd St (NE), McCovey Cove / China Basin (SE) and 3rd St (SW). Home plate is in the west corner (near Willie Mays Plaza, 3rd & King); centre field points roughly east (bearing ≈ 90°, estimated from the aerial and the RF-along-the-cove layout); right field runs along McCovey Cove (SE side), left field along King St, with the Coca-Cola bottle and giant glove behind the left-field bleachers at the 2nd & King corner.

**Dimensions**
- Field: LF line 339 ft (103 m), LF 354, LC 399, CF 391, RC 415 ("Triples Alley"), RF 365, RF line 309 ft (94 m); RF wall 24 ft (7.3 m) high, brick; LF wall 8 ft — Wikipedia (post-2020 values).
- Capacity ≈ 41,900 (OSM tag 42,300); record 44,046 — Wikipedia.
- Coca-Cola bottle 80 ft (24 m) long, lying at an angle behind LF; giant 1927-style glove ~26 ft (not verified).
- Heights not published: grandstand rim ≈ 30 m, light standards on the rim to ≈ 45 m (OSM `height=45` on the stadium relation), Willie Mays Plaza clock tower ≈ 30–35 m — all estimated from `Aerial_photograph_of_AT_T_Park__home_of_the_San_Francisco_Giants.jpg` (author: The original uploader was Grant.gibson at English Wikipedia .; licence: CC BY 2.5).

**Massing** (from the aerial photo)
1. Horseshoe-shaped double-deck grandstand (lower bowl + upper deck with suites level between) wrapping from the RF foul pole around home plate to the LF foul pole; upper deck seats dark green; exterior wall red-brown brick with arched openings.
2. Right field: low (~8 m) brick-faced arcade wall along the cove (a long row of arched portholes) with the promenade behind it; no stands above it — this is the signature open side toward the water.
3. Centre field: big scoreboard (≈ 30 × 10 m board on posts, estimate) and the ferry pier behind.
4. Left field: bleachers + Coke bottle and glove in the corner.
5. Thin light standards along the upper-deck rim; flat green-painted steel canopy over the top rows on the home-plate side.
6. Clock tower over the main gate at 3rd & King (brick, square, with a pyramidal cap).

**Colours** — brick #8E4B3A, concrete/stone trim #D8D2C6, seats dark green #2F5E46, steel green #3C6E5A, grass #4E8B3A (estimated from the aerial).

**Reference photos** — `data/raw/reference_photos/oracle_park/Aerial_photograph_of_AT_T_Park__home_of_the_San_Francisco_Giants.jpg` — [Commons](https://commons.wikimedia.org/wiki/File:Aerial_photograph_of_AT%26T_Park,_home_of_the_San_Francisco_Giants.jpg) — author: The original uploader was Grant.gibson at English Wikipedia . — licence: CC BY 2.5 (oblique aerial from the cove side).

### Chase Center (`chase_center`)

**Dates** — plan announced 22 May 2012 (Piers 30–32, abandoned); Mission Bay site bought 19 Apr 2014; groundbreaking 17 Jan 2017; opened 6 Sep 2019 — https://en.wikipedia.org/wiki/Chase_Center

**Location** — arena centroid 37.767915, -122.387520 (OSM way 579646390), 1 Warriors Way at 3rd St & 16th St, Mission Bay. Twin glass office buildings (Uber HQ, 2020) stand on the same 11-acre site to the N/NW; Thrive City plaza around the arena.

**Dimensions** — 900,000 sq ft; capacity 18,064 basketball / 19,500 concerts — Wikipedia. Footprint a rounded oval/"squircle" ≈ 155 × 154 m (OSM, area 19,466 m²); height 38.1 m (OSM tag; not verified against an official figure).

**Massing** (from `Chase_Center_-_Warriors.jpg` (author: Christopher Michel; licence: CC BY 2.0), `Chase_Center_San_Francisco.jpg` (author: Dale Cruse from San Francisco, CA, USA; licence: CC BY 2.0))
1. A single drum with a rounded-rectangle plan ≈ 155 m across, 38 m tall; walls slightly convex (bulging), clad in smooth white/silver horizontal metal panels.
2. Bottom ~10–12 m: recessed glass base / lobby band (the skin lifts above a glazed ground floor at the entrances).
3. Roof: nearly flat, very slightly domed, white, with a narrow raised rim; "CHASE CENTER" lettered on it.
4. One side (toward 3rd St/16th St plaza) has a large LED screen and a sweeping white canopy over the main entrance ("Gatehouse").

**Colours** — facade #E8EAEC, roof #DADDE0, glass base #6E8796.

**Reference photos** — `data/raw/reference_photos/chase_center/Chase_Center_-_Warriors.jpg` (author: Christopher Michel; licence: CC BY 2.0) ([Commons](https://commons.wikimedia.org/wiki/File:Chase_Center_-_Warriors.jpg); 2020 drone aerial) and `…/Chase_Center_San_Francisco.jpg` (author: Dale Cruse from San Francisco, CA, USA; licence: CC BY 2.0) ([Commons](https://commons.wikimedia.org/wiki/File:Chase_Center_San_Francisco.jpg); street view with entrance canopy) — credits in the photo index appendix.

### Kezar Stadium — original 1925 bowl (`kezar_stadium_1925`) and 1990 rebuild (`kezar_stadium_1990`)

**Dates**
- Funded by Mary Kezar estate ($100k of ~$300k); built 1924–25 to a design by Willis Polk; dedicated/opened 2 May 1925 — https://en.wikipedia.org/wiki/Kezar_Stadium ; https://pcad.lib.washington.edu/building/3893
- 49ers home 1946–1970; Raiders 1960. Original stadium demolished June 1989 (before the 17 Oct 1989 Loma Prieta quake per PCAD; some accounts wrongly attribute it to quake damage) — PCAD.
- Rebuilt 1989–1990 as a ~10,000-seat stadium (Prop D 1987 park bond); later added 1,000 seats from Candlestick — Wikipedia; https://broughttolight.ucsf.edu/2016/02/03/kezar/
- The 1925 Roman triumphal-arch entrance gate survives at the east end (see photo).

**Location** — site centroid 37.766924, -122.456077 (OSM way 30675203, 246 × 144 m, long axis E–W, ground ele ~82 m), SE corner of Golden Gate Park at Frederick & Stanyan streets; Kezar Pavilion (1924, indoor arena) immediately east at 37.767458, -122.453903.

**Dimensions**
- 1925: capacity 59,942. No published plan dimensions found. Massing (medium-low confidence): a fully enclosed concrete bowl — the 49ers' own history calls it "the original bowl-shaped structure" with bench seating (https://www.49ers.com/news/on-this-day-in-the-bay-goodbye-old-kezar-stadium) — filling most of the 246 × 144 m site (≈ 230 × 130 m outside, long axis E–W) around a running track + football field. Photos `OldKezarEastScoreboard.jpg` (author: uploader Tom SF; licence: Public domain) and `OldKezarArch.jpg` (taken before the 1989 demolition) show: wooden bench seats on stepped concrete terraces continuing around the east end, a big concrete scoreboard wall with a segmental-arched parapet standing on top of the east-end stands, and a plain rusticated concrete perimeter wall into which the "KEZAR STADIUM" arched entrance was built (the arch was later replicated/kept for the 1990 stadium). Rim height ≈ 15 m above the field on the long sides (estimate); the bowl was partly dug into the slope.
- 1990: capacity 10,000. From `Wfm_kezar_stadium.jpg` (author: uploader Finlay McWalter; licence: Public domain) (overhead): 400 m track oval with football field inside; one long uncovered concrete bleacher on each long side (north side has the press-box building), each ≈ 100–110 m long × 20 m deep, ≈ 8–10 m tall at the back (estimated from photos); light towers (~6, ≈ 30 m); the east-end colonnade of salmon-coloured columns and the 1925 arch (≈ 12 m tall, ≈ 10 m wide, single arched opening, inscribed "KEZAR STADIUM").

**Colours** — 1990 bleachers and arch: pinkish-tan concrete #CDB79E with terracotta/salmon trim #C9795E (arch cornice, columns); track red-brown #A65A4A; field green.

**Reference photos** — 1925 bowl: `data/raw/reference_photos/kezar_stadium_1925/OldKezarEastScoreboard.jpg` (author: uploader Tom SF; licence: Public domain) ([Commons](https://commons.wikimedia.org/wiki/File:OldKezarEastScoreboard.jpg)) and `…/kezar_stadium_1925/OldKezarArch.jpg` (author: uploader Tom SF; licence: CC BY-SA 3.0) ([Commons](https://commons.wikimedia.org/wiki/File:OldKezarArch.jpg)). 1990: `data/raw/reference_photos/kezar_stadium_1990/Wfm_kezar_stadium.jpg` (author: uploader Finlay McWalter; licence: Public domain) ([Commons](https://commons.wikimedia.org/wiki/File:Wfm_kezar_stadium.jpg), overhead), `…/Kezar_Stadium__2341900471_.jpg` (author: Ashleigh Nushawg; licence: CC BY 2.0) ([Commons](https://commons.wikimedia.org/wiki/File:Kezar_Stadium_(2341900471).jpg), 1925 arch), `…/_49ers__28791895142_.jpg` (author: Topher.; licence: CC BY 2.0) ([Commons](https://commons.wikimedia.org/wiki/File:%2749ers_(28791895142).jpg), stands from the field).

### Candlestick Park — open 1960 form (`candlestick_park_1960`) and enclosed 1971 form (`candlestick_park_1971`)

**Dates** — land at Candlestick Point bought from contractor Charles Harney; groundbreaking 12 Aug 1958; opened 12 Apr 1960 (first all-reinforced-concrete MLB stadium); enclosed with outfield grandstands after the 1970 season, ready for the 49ers' move in 1971 (upper-deck expansion was under way during the 1971 baseball season); AstroTurf 1970–78; Giants left after 30 Sep 1999; last 49ers game 2013; last event Paul McCartney concert 14 Aug 2014; demolition 4 Feb – 24 Sep 2015 — https://en.wikipedia.org/wiki/Candlestick_Park

**Location** — 37.71361, -122.38611 (Wikipedia coordinates; centre of the stadium), Candlestick Point on the Bay shore below Bayview Hill; huge parking lots to the S and E.

**Dimensions** — capacity 43,765 (1960), 63,000 baseball / 69,732 football after enclosure. Field 1960: LF/RF 330 ft, CF 420 ft. No published plan dimensions found; from the 1990s aerials the enclosed bowl is a slightly squared oval ≈ 240 × 210 m outside, rim ≈ 30 m above grade with light towers on the rim to ≈ 45 m (estimated from `Aerial_view_of_Candlestick_Park…LCCN2011633072.tif.jpg`).

**Massing**
- 1960–1970: a horseshoe/"C" of double-deck concrete grandstand wrapping home plate from foul pole to foul pole (open toward the outfield and the Bay to the east), with low uncovered outfield bleachers and a scoreboard (see `data/raw/reference_photos/candlestick_park_1960/Candlestick_Postcard_-_01.JPG` (author: Mike Roberts; licence: Public domain) — aerial postcard of the original layout: horseshoe of double-deck stands around the infield, low single-level stands/bleachers in the outfield, parking all round).
- 1971–2015: fully enclosed oval bowl: the double-deck stand continued around the outfield; distinctive exterior of ribbed white concrete with continuous external ramps; red/orange upper-deck seats; 3–4 tall light standards; scoreboards at the ends.

**Colours** — concrete #D9D5CC; seats orange-red #B5452F (upper) and dark red; field green.

**Reference photos** — `data/raw/reference_photos/candlestick_park_1960/Candlestick_Postcard_-_01.JPG` (author: Mike Roberts; licence: Public domain) ([Commons](https://commons.wikimedia.org/wiki/File:Candlestick_Postcard_-_01.JPG); 1960s postcard, open configuration); `data/raw/reference_photos/candlestick_park_1971/Aerial_view_of_Candlestick_Park__home_stadium_of_the_San_Francisco_49ers_Nationa_1d6b7a.tif.jpg` ([Commons](https://commons.wikimedia.org/wiki/File:Aerial_view_of_Candlestick_Park,_home_stadium_of_the_San_Francisco_49ers_National_Football_League_professional_team,_with_downtown_San_Francisco,_California,_in_the_distance_LCCN2011633072.tif), Carol M. Highsmith, public domain) and `data/raw/reference_photos/candlestick_park_1971/Candlestick_Park_aerial.jpg` ([Commons](https://commons.wikimedia.org/wiki/File:Candlestick_Park_aerial.jpg)) — both show the enclosed form; plus `data/raw/reference_photos/candlestick_park_1971/Candlestick_Park_destruction_1971_-_2013__18439354058_.jpg` (author: rulenumberone2 from San Francisco, CA, USA; licence: CC BY 2.0) ([Commons](https://commons.wikimedia.org/wiki/File:Candlestick_Park_destruction_1971_-_2013_(18439354058).jpg)) — 2015 demolition exposing the stand cross-section: steeply raked upper deck on concrete frames topped by a curved, out-turned windscreen/roof lip (useful for the rim profile).

### Seals Stadium (`seals_stadium`)

**Dates** — opened 7 Apr 1931 (cost $1.25 M); right-field bleachers added 1946; LF "Paul's Porch" 1951 only; Giants' temporary home 1958–59; last game 20 Sep 1959; demolished Nov 1959. Site now the Potrero Center shopping centre — https://en.wikipedia.org/wiki/Seals_Stadium

**Location** — block bounded by Alameda St (N), Potrero Ave (E), 16th St (S) and Bryant St (W); block centroid 37.766756, -122.409239 (Potrero Center outline, OSM way 219072799, 234 × 173 m, long axis E–W). Home plate in the NW corner (Bryant & Alameda); field oriented SE from home to second base; right-field corner at 16th & Bryant, RF bleachers along 16th St — Wikipedia.

**Dimensions** — capacity 18,600 at opening (16,000 per infobox), 22,900 in 1958. LF 365 ft (1931) / 361 ft (1958), CF 400–410 ft, RF line ~348 ft after 1946. Concrete and steel ("The Queen of Concrete"); single-deck grandstand with **no roof**, running foul pole to foul pole; six light towers. Heights not documented: grandstand back ≈ 12–15 m, light towers ≈ 30 m (estimates).

**Massing** — an L/V-shaped uncovered single-deck concrete grandstand wrapping the NW corner of the block along Bryant St and Alameda St, uncovered bleachers along 16th St (from 1946) and in LF (1958–59), outfield fence along Potrero Ave; 6 lattice light towers on the stands. Painted green overall after WWII (Wikipedia: owner Paul Fagan "had the entire stadium painted green").

**Colours** — 1931–45 bare concrete #CFCABF; 1946–59 green #4F7A55 (shade not documented).

**Reference photos** — `data/raw/reference_photos/seals_stadium/Seals_Stadium_Army-Navy_War_Show.jpg` (author: Official U. S. Signal Corps Photo; licence: Public domain) ([Commons](https://commons.wikimedia.org/wiki/File:Seals_Stadium_Army-Navy_War_Show.jpg); WWII-era night view showing light towers and the field — the Wikipedia infobox aerial `Seals Stadium aerial.JPG` is not on Commons) and `data/raw/reference_photos/seals_stadium/Corbett___Fields__1933.jpg` (author: Unknown author Unknown author; licence: Public domain) ([Commons](https://commons.wikimedia.org/wiki/File:Corbett_%26_Fields,_1933.jpg); 1933 boxing card in the stadium: packed, uncovered single-deck grandstand and a lattice light tower).

### Ewing Field (`ewing_field`)

**Dates** — opened 16 May 1914; Seals' home for the 1914 season only (cold, fog); afterwards amateur football/soccer/boxing; wooden grandstand burned 5 Jun 1926 (fire spread to ~100 houses); bleachers used for football incl. SF State 1931–35; demolished 1938 for the Ewing Terrace housing tract — https://en.wikipedia.org/wiki/Ewing_Field

**Location** — Richmond District / Lone Mountain: bounded by Masonic Ave (E, third-base side), Anza St (then St. Rose's Ave, N, first-base side), the Presentation Convent and Turk Blvd (S, left field) and Lone Mountain (W, right field). Site centre ≈ 37.7801, -122.4480 (the Ewing Terrace loop street, OSM ways 399590025/8919914). Home plate therefore near the Masonic/Anza (NE) corner with the field facing SW (inferred from the base-line descriptions).

**Dimensions** — LF 340 ft, CF 400 ft, RF 356 ft (SF Chronicle 22 Mar 1914 via Wikipedia); capacity ≈ 17,500 at the opener (LoC photo title). From `Ewing_Field_1914_05_17.jpg` (author: anonymous staff photographer for the Examiner; licence: Public domain): a single-deck, roofed wooden grandstand behind home plate extending along both baselines (an "L"), uncovered bleachers continuing down the lines, plain board outfield fence; grandstand roof ≈ 12 m high (estimate).

**Reference photos** — `data/raw/reference_photos/ewing_field/Ewing_Field_1914_05_17.jpg` (author: anonymous staff photographer for the Examiner; licence: Public domain) ([Commons](https://commons.wikimedia.org/wiki/File:Ewing_Field_1914_05_17.jpg), newspaper aerial-perspective view, 1914, public domain) and `…/Ewing_Field_San_Francisco_under_construction_1914_03_22.jpg` ([Commons](https://commons.wikimedia.org/wiki/File:Ewing_Field_San_Francisco_under_construction_1914_03_22.jpg), 1914 newspaper photo).

### Recreation Park, 14th & Valencia (`recreation_park_valencia`)

**Dates** — Seals' home 1907–1913 and 1915–1930 (the park dates from 1907, after the 1906 fire destroyed Central Park at 8th & Market); Oakland Oaks also played most games here 1907–1913; expanded before the 1917 season (buildings on 15th St demolished, grandstand rebuilt/expanded); remained in local use after Seals Stadium opened (1931); acquired by San Francisco State 1936 and renamed Roberts Field; sold to the SF Housing Authority 1940; site cleared for the Valencia Gardens public housing — https://en.wikipedia.org/wiki/Recreation_Park_(San_Francisco). End year for the model: 1940 (exact demolition date not found; Valencia Gardens opened 1943).

**Location** — block bounded by 14th St (N, right field), Valencia St (E, first base), 15th St (S, third base) and Guerrero St (W, left field); Wikipedia coordinate 37.76750, -122.42306; Valencia Gardens block centroid 37.767160, -122.423198 (OSM, 176 × 120 m). Home plate therefore in the SE corner (15th & Valencia) facing NW.

**Dimensions** — LF line 315 ft, CF 340 ft, RF line 284 ft (SF Examiner 1 Feb 1931 via Wikipedia). Wooden stands of unusual design: a small lower deck with a large upper deck directly above it (initially largely unroofed). Photo: `data/raw/reference_photos/recreation_park_valencia/Opening_of_Base_Ball_Season_1912__Recreation_Park__San_Francisco__Cal._April_2_1_9e8851.jpg` (author: California Historical Society Digital Collection; licence: No restrictions) ([Commons](https://commons.wikimedia.org/wiki/File:Opening_of_Base_Ball_Season_1912,_Recreation_Park,_San_Francisco,_Cal._April_2_1912,_Seals_vs_Oaks_(17125734669).jpg), 1912 panorama): a long, packed two-level wooden grandstand with a roofed upper level behind the teams. Massing: two-level wooden grandstand ≈ 12–15 m tall wrapping the SE corner along Valencia and 15th, board fence along 14th/Guerrero (estimate).

### Cow Palace, Daly City (`cow_palace`)

**Dates** — opened 20 Apr 1941 as the California State Livestock Pavilion (renamed Cow Palace 1944; WWII military use 1942–45) — https://en.wikipedia.org/wiki/Cow_Palace

**Location** — building centroid 37.706764, -122.418864 (OSM way 29397734; 2600 Geneva Ave, Daly City, just south of the SF line which crosses its upper parking lot). Building long axis bearing ≈ 19°/199° (OSM).

**Dimensions** — footprint ≈ 185 × 155 m including low annexes (OSM); main arena hall ≈ 120 × 90 m (estimate); seats ~11,000–15,000. Height not documented; barrel-vault roof ≈ 30 m at the crown (estimated from `Cow_Palace_front_1.JPG` (author: BrokenSphere; licence: CC BY-SA 3.0)).

**Massing** — a long rectangular hall covered by a single segmental barrel vault (steel arched trusses — visible in the interior photo `Cow_Palace__2563656722_.jpg` (author: gosheshe; licence: CC BY 2.0)), gable ends are big segmental-arched walls with vertical pilaster strips, "COW PALACE" in large red letters over the main (end) entrance; lower flat-roofed annexes/ramps along the sides.

**Colours** — walls light grey #C9CACB with darker grey pilaster strips #8F9396, red lettering/trim #D2405A (estimated from photo).

**Reference photos** — `data/raw/reference_photos/cow_palace/Cow_Palace_front_1.JPG` (author: BrokenSphere; licence: CC BY-SA 3.0) ([Commons](https://commons.wikimedia.org/wiki/File:Cow_Palace_front_1.JPG)) and `…/Cow_Palace__2563656722_.jpg` (author: gosheshe; licence: CC BY 2.0) ([Commons](https://commons.wikimedia.org/wiki/File:Cow_Palace_(2563656722).jpg), interior roof trusses).

---

## Parks (dates, development history, notable structures)

### Golden Gate Park (`golden_gate_park`)

**Dates and development**
- 1866 Outside Lands Act extends the city to the Pacific; 1870 park land approved — official founding year; William Hammond Hall surveys/maps the site in 1870 and is superintendent 1871–1876 — https://en.wikipedia.org/wiki/Golden_Gate_Park ; https://www.kqed.org/news/11915008
- Before: about three-quarters of the 1,017 acres was bare shifting sand dunes ("Great Sand Bank" on 1853 maps); a few natural ponds in the west (origin of the Chain of Lakes) and some scrub in the east — KQED, Wikipedia.
- Reclamation method and sequence: Hall reclaimed the east (lee) end first, starting with the Panhandle and the eastern third; dunes were stabilised with quick-growing grasses (barley in folklore; McLaren later used bent grass) and native lupine, fertilised with street-sweeper manure, then planted with tree windbreaks; west of that he extended planting progressively toward the ocean using the remaining dunes as windbreaks; the ocean end needed sand-trapping fences first — KQED; Wikipedia.
- Planting counts: ~60,000 trees (mostly Eucalyptus globulus, Monterey pine, Monterey cypress) by 1875; ~155,000 trees by 1879 — Wikipedia. By c. 1890 the eastern end "looked fairly mature" — KQED.
- John McLaren superintendent 1890 (hired 1887 per some sources) – death 1943; McLaren Lodge 1896; he built the ocean-front esplanade by stacking brush over ~20 years — Wikipedia, KQED.
- Suggested model staging (my synthesis, medium confidence): 1870 all dunes except the Panhandle strip and the eastern ~500 m; 1871–1880 Panhandle + east third (to about the Conservatory / Stow Lake area) wooded; 1880–1895 middle third planted, Stow Lake dug 1893, Music Concourse excavated 1893 for the 1894 fair; 1895–1910 west third planted out to the beach, windmills 1903/1908, Spreckels Lake ~1904; 1910s–1929 Great Highway / O'Shaughnessy seawall and esplanade along Ocean Beach (photos captioned "Esplanade 1929"). The exact year each zone became forest is not documented in the sources found.
- 1894 California Midwinter International Exposition, 27 Jan – 5 Jul 1894, 200 acres centred on today's Music Concourse; 120 temporary structures including the 266 ft (81 m) Bonet electric tower in the centre of the Grand Court — https://en.wikipedia.org/wiki/California_Midwinter_International_Exposition_of_1894
- 1906: refugee camps / earthquake shacks in the park — Wikipedia. 2004 National Historic Landmark.

**Location / extent** — park polygon centroid 37.768547, -122.480750 (OSM way 158602261, start_date 1870); ≈ 5.03 km E–W (Stanyan St to the Great Highway) × 0.94 km N–S (Fulton St to Lincoln Way), area ≈ 4.05 km² excluding the Panhandle. The Panhandle runs east from Stanyan to Baker St between Fell and Oak (≈ 1.3 km × 0.17 km).

**Reference photos (Golden Gate Park and its structures)** — credits in the photo index appendix:
- `data/raw/reference_photos/golden_gate_park/Golden_gate_park_aerial.jpg` (author: uploader Aomarks; licence: CC BY-SA 3.0) — whole park from the air (E–W strip between the Richmond and Sunset, Ocean Beach at right).
- `data/raw/reference_photos/conservatory_of_flowers/Conservatory_of_Flowers_-_panoramio.jpg` (author: harley photo; licence: CC BY-SA 3.0) — south front: central domed pavilion with cupola, two long barrel-roofed wings, small domed end pavilions; all white.
- `data/raw/reference_photos/de_young_museum_2005/M._H._de_Young_Memorial_Museum.jpg` (author: Mark Miller; licence: Public domain) and `…/Hamon_Tower.jpg` (author: Amadscientist; licence: Public domain) — low copper-clad block and the twisting Hamon tower: the tower's plan rotates so its elevation reads as an inverted trapezoid, topped by a recessed glazed band and an overhanging flat roof slab.
- `data/raw/reference_photos/california_academy_of_sciences_2008/California-06239_-_California_Academy_of_Sciences__20449900470_.jpg` (author: Dennis G. Jarvis; licence: CC BY-SA 2.0) — seen from the Music Concourse: glazed box under a thin white overhanging canopy, green roof hills and the glass rainforest dome.
- `data/raw/reference_photos/japanese_tea_garden/Japanese_tea_garden_Golden_Gate_Park.JPG` (author: Asamudra ( talk ); licence: CC BY 3.0) — the red-lacquered Temple Gate (from the 1915 PPIE).
- `data/raw/reference_photos/dutch_windmill/GGParkNorthWindmill2.jpg` (author: Sam at English Wikipedia; licence: CC BY-SA 3.0), `data/raw/reference_photos/murphy_windmill/Murphy_windmill.jpg` (author: Allie_Caulfield; licence: CC BY 2.0) — both mills (proportions used for the height estimates).
- `data/raw/reference_photos/spreckels_temple_of_music/Golden_Gate_Park_-_Spreckels_Temple_of_Music_02.jpg` (author: Joe Mabel; licence: CC BY-SA 3.0) — arched shell with flanking Ionic colonnades and balustrade.
- `data/raw/reference_photos/midwinter_fair_1894/CMIE_a.jpg` (author: The original uploader was Mdiamante at English Wikipedia .; licence: Public domain) — 1894 Grand Court with the Bonet electric tower (lattice, Eiffel-like) at its centre.

**Notable structures (each also in the CSV)**
| id | Structure | Dates | Ref. point / footprint | Height | Notes |
|---|---|---|---|---|---|
| `conservatory_of_flowers` | Conservatory of Flowers | built 1878, opened Apr 1879; dome burned Jan 1883 (rebuilt ~6 ft taller, domical instead of saucer-shaped); fire 1918; closed after winter storms 1995–96; restored and reopened 2003 | 37.772590, -122.460184; 75 × 35 m (OSM); overall length 240 ft (73 m) | central dome ≈ 60 ft (18 m) | white-painted wooden Victorian glasshouse, central domed pavilion + two long arched (barrel-vault) wings ending in small pavilions, facing south over a flower bed. Source: https://en.wikipedia.org/wiki/Conservatory_of_Flowers |
| `japanese_tea_garden` | Japanese Tea Garden | 1894 (Japanese Village at the Midwinter Fair, George T. Marsh); city-owned after the fair; Hagiwara family 1895–1942; pagoda + Temple Gate added after 1915 (from PPIE); Zen garden 1953 | 37.770122, -122.470231 (Wikipedia); ~5 acres | pagoda (5 tiers) ≈ 15 m (estimate) | Source: https://en.wikipedia.org/wiki/Japanese_Tea_Garden_(San_Francisco) |
| `spreckels_temple_of_music` | Spreckels Temple of Music (bandshell) | construction began 1899; dedicated 9 Sep 1900; damaged 1906 and 1989, repaired | 37.769872, -122.468600; 54 × 20 m (OSM), faces NE across the Music Concourse | shell 70 ft (21 m) | Italian Renaissance; Colusa sandstone; coffered half-dome shell flanked by colonnaded wings. Earlier bandstands 1882, 1888. Source: https://en.wikipedia.org/wiki/Spreckels_Temple_of_Music |
| `music_concourse` | Music Concourse | excavated 1893 for the 1894 fair; completed 1900; rebuilt 2000s with 800-car garage underneath (2005) | 37.770790, -122.467338; sunken oval ≈ 278 × 134 m, long axis 48° (OSM) | sunken ~3–4 m below surroundings (estimate) | London plane trees in a grid, fountains. Source: https://en.wikipedia.org/wiki/Music_Concourse |
| `dutch_windmill` | Dutch (North) Windmill | authorised 1902, completed 1903; electric pumps replaced it 1913; ruin by 1950s; restored 1981 | 37.770732, -122.509403 (Wikipedia) | not documented; ≈ 22 m to the top of the cap, ≈ 30 m to the upper sail tip (estimated from `GGParkNorthWindmill2.jpg` (author: Sam at English Wikipedia; licence: CC BY-SA 3.0) with people for scale) | concrete/brick drum base (≈ 7 m) with a wooden reefing gallery around it, tapering octagonal tower clad in brown-grey shingles, bulbous (onion-like) shingled cap with a fantail/wind-rose at the back, 4 lattice sails ≈ 30 m span; Queen Wilhelmina Tulip Garden beside it. Source: https://en.wikipedia.org/wiki/Dutch_Windmill_(Golden_Gate_Park) |
| `murphy_windmill` | Murphy (South) Windmill | completed 1908; restoration 2002–2012 (reopened 2012) | 37.765002, -122.508711 (OSM; 21 m base footprint incl. gallery) | OSM 10 m (tower body) is too low; from `Murphy_windmill.jpg` (author: Allie_Caulfield; licence: CC BY 2.0) ≈ 22 m to the cap, ≈ 30 m to the upper sail tip (estimate) | same type as the Dutch mill: grey shingled octagonal tower on a brick base with a red-brown wooden gallery; small brick millwright's cottage beside it | Source: https://en.wikipedia.org/wiki/Murphy_Windmill |
| `de_young_museum_1895` | de Young — Midwinter Fair Fine Arts Building (Egyptian Revival) | built for the 1894 fair; museum opened 1895; damaged 1906, reopened Nov 1907; declared unsafe and demolished 1929 (Google Arts & Culture timeline gives 1929–31) — https://artsandculture.google.com/exhibit/125-years-of-the-de-young/TwLSfQB4ajfOLw ; it stood next to the new Mullgardt wings 1919–1929 | Music Concourse N side (≈ 37.7713, -122.4685) | brick, ≈ 50 ft (15 m) | "pseudo-Egyptian Revival", Hathor heads. Source: Midwinter Exposition article |
| `de_young_museum_1919` | de Young — Mullgardt Spanish-Plateresque building | first wing completed 1919; central section + signature tower 1921 (more wings through the 1920s); severely damaged 1989; kept its configuration until 2000, then closed and demolished (exact demolition year not found; use 2001) | N side of the Music Concourse (same site as 2005 building) | tower ≈ 30 m (estimate, not documented) | cast-stone, buff colour. Source: https://en.wikipedia.org/wiki/De_Young_Museum |
| `de_young_museum_2005` | de Young — Herzog & de Meuron | competition won Jan 1999; opened 15 Oct 2005 | 37.771550, -122.468612; ≈ 154 × 76 m (OSM relation 1652482), long axis 48° | main block ≈ 13 m (OSM); Hamon Observation Tower 144 ft (43.9 m) | see massing below |
| `california_academy_of_sciences_1916` | Cal Academy old complex | North American Hall 1916; Steinhart Aquarium 1923; Simson African Hall 1934; Cowell Hall 1969; galleries 1976; damaged 1989; demolished from 2005 (African Hall/North American Hall/aquarium elements kept) | S side of the Music Concourse (≈ 37.7699, -122.4661) | ≈ 15–20 m (estimate) | cluster of classical-revival halls around a court, facing the Concourse. Source: https://en.wikipedia.org/wiki/California_Academy_of_Sciences |
| `california_academy_of_sciences_2008` | Cal Academy — Renzo Piano | construction began 12 Sep 2005; opened 27 Sep 2008 | 37.769853, -122.466126; ≈ 161 × 103 m (OSM), long axis 48° | roof edge ≈ 11 m (OSM); domes rise higher | 2.5-acre living roof with ~1.7 M plants; 400,000 sq ft |

**de Young 2005 massing** (photos pending in `reference_photos/de_young_museum_2005/`): a long, low, 2-storey copper-clad building ≈ 154 × 76 m formed of three long parallel bars slightly skewed to each other with landscaped courts cut into it, under one large flat roof that cantilevers deeply at the entrance; at the NE corner the Hamon tower rises 43.9 m and twists — its footprint is aligned with the museum below and rotates so the top floor aligns with the city street grid (Herzog & de Meuron's description; amount of rotation not quantified in sources found). Cladding 163,118 sq ft of perforated and dimpled copper, now weathered to a dark brown with greenish tints (Wikipedia). Colour ≈ #6E4B33 (weathered copper, estimate).

**Cal Academy 2008 massing**: rectangular glass-walled box ≈ 161 × 103 m, ≈ 11 m high to a thin flat canopy edge; the green roof undulates over seven rounded hills, the two largest covering the planetarium dome (W) and the rainforest dome (E) and rising ≈ 10–11 m above the roof plane (estimate, roof "domes" ~ 90 ft diameter per common descriptions — not verified); central glass-covered piazza with a round skylight. Colours: roof green #7FA35A, glass #A9C1C9, white steel frame.

---

### Other parks

| id | Park | Key dates (sources) | Location / extent | Notable structures and changes |
|---|---|---|---|---|
| `mission_dolores_park` | Mission Dolores Park | Site = two Jewish cemeteries (Congregations Sherith Israel and Emanu-El), inactive from 1894; bodies moved to Colma; city bought the land 1905 and made it a park (Wikipedia infobox "established 1906"); 1906–08 refugee camp for >1,600 families; 1917 J Church streetcar right-of-way laid through the SW corner; 2012–2016 major renovation (new playground, restrooms, regrading). https://en.wikipedia.org/wiki/Mission_Dolores_Park | 37.7596522, -122.4260821 (Wikipedia); two city blocks between Dolores & Church, 18th & 20th St (~16 acres); slopes up steeply to the SW | Mexican Liberty Bell replica 1966; Muni J line crosses the park on a private ROW. |
| `alamo_square` | Alamo Square | Land set aside by Mayor James Van Ness in 1856 and officially established as a park in 1857 (https://alamosquare.org/park-history/); named for a lone cottonwood ("alamo") marking a watering hole on the Mission–Presidio trail; surrounding Victorians 1870s–1920s; Alamo Square Historic District 1984 (Wikipedia). Park renovation 2016–17 (SF Rec & Park; not verified). https://en.wikipedia.org/wiki/Alamo_Square,_San_Francisco | 37.776384, -122.434709 (Wikipedia); 13.6 acres, four blocks bounded by Hayes (S), Steiner (E), Fulton (N), Scott (W); hilltop | Painted Ladies on Steiner (see own section); Westerfeld House (1889) on Fulton/Scott. |
| `union_square` | Union Square | Set aside as a public square 1850 (dedicated by Mayor John Geary); originally a sand dune; named for pro-Union rallies c. 1860–61; Dewey Monument (85 ft / 26 m column + 9 ft / 2.7 m Nike statue) dedicated 1903; underground garage beneath the square 1942 (first underground garage — commonly cited; not verified here); redesign by April Philips/Michael Fotheringham, reopened 25 Jul 2002 (Wikipedia). https://en.wikipedia.org/wiki/Union_Square,_San_Francisco | 37.788056, -122.4075 (Wikipedia); one block (2.6 acres) bounded by Geary, Powell, Post, Stockton | Dewey Monument at the centre: total ≈ 29 m (column 26 m + statue 2.7 m). Since 2002 a raised granite plaza with terraces and palm trees. |
| `yerba_buena_gardens` | Yerba Buena Gardens | Redevelopment of the South of Market Yerba Buena area from the 1960s (clearance); Moscone Center below (1981); Esplanade gardens opened 1993 with the MLK Jr. memorial fountain "Revelations"; YBCA 1993; south block (Children's Creativity Museum, ice rink, bowling, 1906 LeRoy King carousel) 1998 (Wikipedia; 1998 not verified). https://en.wikipedia.org/wiki/Yerba_Buena_Gardens | 37.7848, -122.4027 (Wikipedia); two blocks between 3rd & 4th, Mission & Folsom (roof gardens over Moscone) | MLK waterfall (~15 m wide × 6 m high, estimate); SFMOMA (1995) faces the gardens across 3rd St. |
| `presidio_forest` | Presidio forest planting | Maj. William A. Jones' Army beautification/forestation plan 1883; planting began Arbor Day 1886; ~100,000 trees over ~14 years (NPS figure; other sources 300,000–400,000), mainly Monterey cypress, Monterey pine, blue gum eucalyptus, blackwood acacia; today ~306 acres with ~75,000 trees; reforestation program since the 1990s/2000s — https://foundsf.org/The_Presidio_Forest ; https://presidio.gov/about/sustainability/creating-a-sustainable-forest ; https://baynature.org/article/presidios-forest-resists-the-sands-of-time/ | Presidio centroid 37.798056, -122.465833 (Wikipedia); forest mostly on the ridges in the centre/south of the Presidio | Before 1886 the Presidio was almost treeless grass/scrub and dunes (model: bare until ~1886, young trees 1886–1900, mature forest after ~1910). Army post 1846/1847–1994; Spanish presidio founded 1776. |
| `crissy_field_airfield` (1921–1974) / `crissy_field_restored` (2001–) | Crissy Field | Tidal salt marsh (~130 acres) until filled for the 1915 PPIE (racetrack/aviation field); Army air coast-defense station authorised 1918; airfield built from 1919 on the old racetrack and completed by 1921 (named for Maj. Dana Crissy, killed Oct 1919); NPS: centre of West Coast military aviation 1921–1936, the field's first-line role ending in 1936 as the Golden Gate Bridge neared completion (https://www.nps.gov/articles/crissy-airfield-presidio-of-san-francisco.htm ; https://www.nps.gov/goga/learn/photosmultimedia/now-and-then-crissy-field.htm); closed to fixed-wing aircraft 1974, helicopters later (https://www.parksconservancy.org/node/4769); grass field with hangars at the W end; Air Corps operations moved to Hamilton Field (Marin) 1936; paved runway after WWII; closed as an airfield after 1974; NPS took over 1994; restoration project 1996–2001 (construction 1998–2000: 28-acre grass airfield, tidal marsh, dunes), completed and reopened 2001 with the Crissy Field Center — https://en.wikipedia.org/wiki/Crissy_Field ; https://baynature.org/article/presidios-forest-resists-the-sands-of-time/ | 37.8042, -122.4597 (Wikipedia); 1.6 km strip along the bay shore of the Presidio between the Marina and Fort Point | Model states: 1915 PPIE grounds; 1921–1974 airfield (kidney-shaped landing field, hangars and 1921 Mediterranean-revival buildings along Mason St); 2001+ restored grass airfield + tidal marsh lagoon (~18 acres) + beach. |
| `lands_end` | Lands End | Coastal headland; Sutro Baths (1896–1966) and Cliff House below (see Priority 2); part of Golden Gate National Recreation Area since 1972; until the 1930s the headlands were treeless except willows, then planted with pine, eucalyptus, cypress (Wikipedia); Lands End Lookout visitor centre 2012 (not verified). https://en.wikipedia.org/wiki/Lands_End_(San_Francisco) | 37.784925, -122.50553 (Wikipedia) | USS San Francisco memorial; Coastal Trail; Mile Rock lighthouse offshore (1906; tower cut down 1966). |
| `sutro_heights` | Sutro Heights Park | Adolph Sutro bought 22 acres in 1881, built his mansion and gardens; gardens opened to the public by 1883 (Wikipedia; other sources say 1885); estate donated to the city 1938; WPA demolished the mansion 1939; now part of GGNRA — https://en.wikipedia.org/wiki/Sutro_Heights_Park | 37.7782632, -122.5110838 (Wikipedia); promontory above the Cliff House | Mansion (1880s–1939), parapet/lookout, lion statues at the gate, Diana statue; Sutro also built the Sutro Baths (1894–1964 per this article; 1896–1966 per the Sutro Baths article) and the 1896 Cliff House. |

**Reference photos (other parks)** — shared-photo notes: Crissy Field appears in the Presidio aerial; the Music Concourse in the Cal Academy photo; the Alcatraz lighthouse/water tower in `Alcatraz_2021.jpg`; the old Bay Bridge east span in the New-and-Old photo; the Mission Dolores Basilica in the Mission photo. — credits in the photo index appendix: `mission_dolores_park/Dolores_Park_May_2025.jpg` (author: Alexwennerberg; licence: CC0) (view NE across the lawns to downtown), `alamo_square/Alamo_Square_with_Painted_Ladies__SF__CA__jjron_26.03.2012.jpg`, `union_square/San_Francisco_Union_Square.jpg` (author: Lordsamp; licence: CC BY-SA 4.0) (granite plaza with the Dewey column), `yerba_buena_gardens/2017_Yerba_Buena_Gardens.jpg` (author: Beyond My Ken; licence: CC BY-SA 4.0), `presidio_forest/Aerial_view_-_Presidio-whole.jpg` (author: Robert Campbell; licence: CC BY-SA 3.0) (forest distribution, Crissy Field along the bay), `lands_end/Coastal_Trail_and_Golden_Gate_Bridge__April_2019.JPG` (author: Pi.1415926535; licence: CC BY-SA 3.0), `sutro_heights/SutroHeightsPark.jpg` (author: uploader Nz1845; licence: CC BY-SA 3.0) (all under `data/raw/reference_photos/`). No Crissy Field-specific photo was downloaded (the Presidio aerial covers it).

---

## Priority 2

### San Francisco–Oakland Bay Bridge — west span (`bay_bridge_west_span`), original east span (`bay_bridge_east_span_1936`), new east span (`bay_bridge_east_span_2013`)

**Dates** (https://en.wikipedia.org/wiki/San_Francisco%E2%80%93Oakland_Bay_Bridge ; https://en.wikipedia.org/wiki/Eastern_span_replacement_of_the_San_Francisco%E2%80%93Oakland_Bay_Bridge)
- Construction began 9 Jul 1933; opened 12 Nov 1936 (both original spans). Key System / interurban rail on the lower deck until 1958; decks converted to one-way (upper westbound, lower eastbound) by 1963 (not verified here).
- 17 Oct 1989 Loma Prieta: a 50 ft section of the east span upper deck collapsed onto the lower deck; reopened after ~1 month.
- Replacement east span: construction began 29 Jan 2002 (skyway ~75 % done by 2005; SAS tower and deck 2009–2013); old east span closed 28 Aug 2013; new span opened 2 Sep 2013. A temporary S-curve detour connecting the old cantilever to the YBI tunnel was used Sep 2007 – 2013.
- Demolition of the old east span: began Sep 2013 (reverse of construction); cantilever cut at its centre by 2014 (800 ft gap), cantilever removed 2014–2015 (complete 12 Jun 2015, Wikipedia); the five 504 ft truss spans lowered onto barges 4 Feb – Aug 2016 and the fourteen 288 ft causeway trusses by 13 Mar 2017 (ABC7 / KTVU; audit 2026-11 — was "truss spans and causeway 2015–2016"); the 13 (sources say 11–13) marine foundations removed by controlled implosions 2015–2017; complete in Nov 2017 (≈ 2 years ahead of the 2018 schedule) — https://www.cbsnews.com/sanfrancisco/news/demolition-of-old-bay-bridge-to-take-years ; https://ktvu.com/news/caltrans-finalizes-plans-for-bay-bridge-old-eastern-span-demolition . Model: 2013 old span complete but closed; 2014 cantilever gapped; 2015 truss spans present, cantilever gone; 2016 some piers; 2018+ nothing.
- West span: seismic retrofit 1999–2004 (no massing change). "Bay Lights" LED art on the west-span suspenders 2013–2023 (relit 2025).

**Location** (OSM `bridge:support` ways; bearing of the west-span axis ≈ 40°/220°)
- W1 concrete pier near SF shore: 37.788310, -122.388471; SF cable anchorage on Rincon Hill (land), ~37.7867, -122.3905 (approximate).
- Tower W2: 37.790764, -122.385856 · Tower W3: 37.795600, -122.380677 · Centre anchorage W4 ("Moran's Island", 69 × 40 m, OSM height 67 m): 37.798119, -122.377877 · Tower W5: 37.800800, -122.375112 · Tower W6: 37.805635, -122.369929 · Pier W7 / YBI anchorage area: 37.808179, -122.367179.
- Computed W2–W3 = 702 m (documented main span 2,310 ft = 704 m ✓).
- Yerba Buena Island: 540 ft (165 m) double-deck tunnel through the island, plus a 321 ft concrete viaduct west of it.
- New SAS tower (T1): 37.815265, -122.358479 (OSM, height 160 m). SAS deck ≈ 37.8143, -122.3602 (W2, YBI side) → 37.8176, -122.3543 (E2); skyway viaducts then run ENE (bearing ≈ 70–73°) to the Oakland touchdown ≈ 37.8222, -122.3277.
- Original east span: ran roughly parallel to and just north of today's alignment from the YBI tunnel east portal to the Oakland mole (exact pier coordinates not researched; ~50–150 m north of the new skyway, see the "New and Old bridges" photo).

**Dimensions**
- West span: two suspension bridges in series sharing the centre anchorage; each main span 2,310 ft (704 m); side spans ≈ 1,160 ft (354 m, commonly cited — not verified here); towers 526 ft (160 m) above water (infobox; OSM 160); total west crossing 10,304 ft (3.14 km); double deck, 5 lanes per deck (57.5 ft roadway); three short truss spans connect the SF anchorage to the Rincon Hill touchdown. Towers: steel, two legs with X-bracing (not portal struts like the GGB) — check `bay_bridge_west_span` photo. Colour: silver-grey "aluminum" paint.
- Original east span (1936–2013): 10,176 ft (3.10 km) = double balanced cantilever (main span 1,400 ft / 427 m, the longest in the US at the time), five 509 ft through-truss spans (509 ft per common sources; Wikipedia says only "five long-span through-trusses"), then a deck-truss causeway (~14 spans of ~291 ft — from memory, not verified) descending to the Oakland mole; double deck; grey steel. Cantilever top ≈ 60–70 m above water (estimate).
- New east span (2013–): single-tower asymmetric self-anchored suspension span — tower 525 ft (160 m) of four steel legs joined by shear links, main span 1,263 ft (385 m), total SAS length 624 m; side-by-side twin decks (eastbound/westbound) with a bike/pedestrian path on the south side; total width 258 ft (78.7 m) incl. gap; then twin concrete "Skyway" viaducts (~2 km) and the curved Oakland touchdown. Colour: white tower and cables, grey concrete.

**Massing (low poly)**
- West span: per span — 2 towers (tall narrow portal frames ~ 25 m wide), parabolic cables from the anchorages over the towers to the centre anchorage, double-deck truss box ~ 20 m wide × 10 m deep at ~ 60 m above water (deck height estimate), suspenders. Centre anchorage: a massive concrete block (69 × 40 m) rising to 67 m with a steel tower-like top carrying both spans' cables.
- Old east span: from YBI, double-deck truss approach → big cantilever truss (deep at the main piers ~ 60 m, shallow at mid-span) → 5 boxy through-trusses (~30 m tall trusses) → long low deck-truss causeway descending to grade.
- New east span: single tower (4 tapered legs, ~ 160 m) carrying one continuous cable that loops around the east end of the deck; twin flat orthotropic box decks; long low twin concrete viaducts.

- Photos: `data/raw/reference_photos/bay_bridge_west_span/Bay_Bridge_2022.jpg` (author: InvadingInvader; licence: CC BY-SA 4.0) (west span from above SF: two suspension spans, slender X-braced steel towers, concrete centre anchorage, light silver-grey paint ≈ #B8BDC0); `data/raw/reference_photos/bay_bridge_east_span_2013/San_Francisco_Oakland_Bay_Bridge-_New_and_Old_bridges.jpg` (author: Frank Schulenburg; licence: CC BY-SA 3.0) (night: white single-tower SAS beside the dark-grey old cantilever, ≈ #4E5459, still standing in 2013). Credits in the photo index appendix.
### Ferry Building (`ferry_building`)
- Dates: wooden predecessor 1875; current building (A. Page Brown) built 1896–1898, opened 13 Jul 1898; survived 1906; ferry traffic collapsed after the bridges (1936–39); Embarcadero Freeway in front 1959–1991; restoration/renovation 2002–2003 (Great Nave restored) — https://en.wikipedia.org/wiki/San_Francisco_Ferry_Building
- Location: centroid 37.795538, -122.393383 (OSM way 558731934), foot of Market St; long axis bearing ≈ 144°/324° (parallel to the Embarcadero); clock tower on the Market St axis at the building's centre.
- Dimensions: building ≈ 201 × 57 m footprint (OSM); 660 ft (201 m) long Great Nave; two-storey main block ≈ 15 m (OSM height; plus roof); clock tower 245 ft (75 m) with four 22 ft (6.7 m) clock dials — Wikipedia.
- Massing: long 2–3 storey arcaded block (ground floor arcade of round arches facing the Embarcadero) with a pitched/clerestory roof over the nave; central square tower modelled on Seville's Giralda: square shaft (~ 12 m side, estimate) to the clock stage, then stepped belvedere stages and a small domed cupola. Piers/sheds behind on the bay side.
- Colours: light grey/cream Colusa sandstone-look #D8D2C4; roof grey; clock faces white.

- Photo: `data/raw/reference_photos/ferry_building/Ferry_Building_San_Francisco_from_Hyatt_Regency_with_R-Evolution_and_Bay_Bridge__c0ceed.jpg` (author: Daniel Lu ( User:dllu ); licence: CC BY-SA 4.0) — from the west: long 2-storey arcaded block with a grey pitched roof, central clock tower with stepped upper stages, Bay Bridge behind.
### San Francisco City Hall — current (`city_hall_1915`) and old (`city_hall_1899`)
- Current: construction began 5 Apr 1913; occupied/opened Dec 1915 (in time for PPIE); completed 28 Jul 1916 — infobox; 1989 quake damage → seismic base-isolation retrofit 1995–1999 (Wikipedia; not verified here). Location: centroid 37.779322, -122.419284 (OSM relation 7261820), Civic Center, between Van Ness (W) and Polk (E), Grove (S) and McAllister (N). Dimensions: 390 ft (119 m) between Van Ness and Polk × 273 ft (83 m) between Grove and McAllister; main block ≈ 30 m (OSM height; 5 floors incl. ground); dome rises 307.5 ft (93.7 m) (Wikipedia/infobox; SAH Archipedia: 307 ft to the springing … lantern to ≈ 350 ft — sources disagree whether 307.5 ft is to the lantern top). Massing: rectangular Beaux-Arts block with two inner light courts, Doric colonnaded centre pavilions on the Polk (E, main) and Van Ness facades; central rotunda with a tall drum (colonnaded) → ribbed dome → lantern. Colours: granite walls #DDD9CF, dome copper patina/dark lead-grey #6C7377 with gilded ribs and lantern details #C9A43A (gilding restored 1999).
- Old City Hall: construction 1870/71–1897 (27 years, 7 architects; building finished 1899), destroyed by the 1906 earthquake and fire; ruins stood until ~1909 (unverified; a 1912 Rolph editorial still refers to the ruins) — https://en.wikipedia.org/wiki/San_Francisco_City_Hall ; https://calisphere.org/item/ark:/13030/hb096nb16b/ . Location: triangular former cemetery block bounded by Larkin, McAllister and City Hall Ave (now built over) — today the Main Library / UN Plaza / Civic Center area; reference ≈ 37.7795, -122.4150 (estimate between Main Library 37.779173,-122.415884 and UN Plaza). Main dome 335 ft (102 m) (Calisphere 1906 caption). Massing: long multi-wing classical building with a tall domed tower (steel-framed dome on a drum) at the Larkin/McAllister side; after 1906 the dome's steel skeleton stood bare over the ruins.

- Photo: `data/raw/reference_photos/city_hall_1915/San_Francisco_City_Hall_2.JPG` (author: Sanfranman59; licence: CC BY-SA 3.0) — Polk St (east) front: long colonnaded block, central pedimented pavilion, drum + dark dome with gilded ribs and lantern.
### Coit Tower (`coit_tower`)
- Dates: Lillie Hitchcock Coit bequest (d. 1929); built 1932–33; dedicated 8 Oct 1933; WPA/PWAP murals 1934 — https://en.wikipedia.org/wiki/Coit_Tower
- Location: 37.802373, -122.405842 (OSM way 28824850), summit of Telegraph Hill (ground elevation ≈ 89 m), Pioneer Park.
- Dimensions: 210 ft (64 m) tall (OSM height 64); the fluted shaft is described as 180 ft (55 m) supporting the viewing platform, observation deck ~32 ft below the top, shaft 18 in narrower at the top than the bottom (Wikipedia mirror text); base footprint ≈ 22 × 22 m including the lobby rotunda (OSM). Shaft diameter not documented — ≈ 11 m (estimate).
- Massing: a square-ish one-storey base building (≈ 22 m) wrapping the bottom, a fluted cylindrical concrete shaft (slight taper) to ≈ 55 m, then an arcaded crown (row of tall arched openings) and a slightly recessed flat top. Colour: unpainted light concrete #E2DED3.

- Photo: `data/raw/reference_photos/coit_tower/Coit_Tower_1.jpg` (author: Ryan Schwark; licence: CC0) — fluted cylindrical shaft, crown with a ring of tall arched openings and a stepped/recessed top; uniform light concrete.
### Palace of Fine Arts (`palace_of_fine_arts_1915`, `palace_of_fine_arts_1967`)
- Dates: built 1914–15 for the PPIE (20 Feb – 4 Dec 1915) by Bernard Maybeck, of wood frame + staff (plaster and burlap); the only PPIE structure kept on site (Palace Preservation League); decayed; demolished 1964 and rebuilt in steel and concrete 1964–1967 (plaque) / works to 1974 (Wikipedia); Exploratorium in the hall 1969–2013; lagoon and seismic renovation completed early 2009 — https://en.wikipedia.org/wiki/Palace_of_Fine_Arts
- Location: rotunda ≈ 37.802919, -122.448402 (OSM way 288371295, height 48 m), Marina District; the exhibition hall curves around the W/NW of the rotunda; lagoon to the E.
- Dimensions: open rotunda 162 ft (49 m) high (Wikipedia); rotunda + peristyle footprint ≈ 68 × 58 m (OSM); exhibition hall a long curved (≈ 300 m arc, estimate) windowless shed ≈ 20 m high.
- Massing: octagonal open rotunda (8 arched openings, Corinthian columns, dome of ochre/red-brown), flanked on both sides by curving open colonnades (peristyle) with tall square planter "boxes" topped by weeping-women figures; behind them the long curved hall; the lagoon in front.
- Colours: 1915 plaster ochre/salmon (staff tinted); 1967 rebuild concrete ochre-beige #D7B98E, dome reddish ochre #B07A52 (estimate).

- Photo: `data/raw/reference_photos/palace_of_fine_arts_1967/Palace_of_Fine_Arts__16794p_.jpg` (author: Rhododendrites; licence: CC BY-SA 4.0) — rotunda across the lagoon with the two curving colonnades; ochre/salmon colour.
### Sutro Tower (`sutro_tower`)
- Dates: construction 1971; completed 4 Jul 1973; tallest structure in SF until 2018 — https://en.wikipedia.org/wiki/Sutro_Tower
- Location: 37.755242, -122.452857 (OSM relation 3829019), hill between Twin Peaks and Mount Sutro; base elevation 834 ft (254 m); top of antennas 1,811 ft (552 m) above sea level — https://www.sutrotower.com/faq
- Dimensions: 977 ft (297.8 m) to the top of the antennas; three legs at the corners of an equilateral triangle whose side varies linearly from 150 ft (45.7 m) at the base to 60 ft (18.3 m) at the "waist" to 100 ft (30.5 m) at the antenna base level; horizontal trusses between the legs at 180, 375, 550, 650 and 770 ft above the base; observatory level 6 at 751 ft; steel tower proper ≈ 770 ft (235 m) with three antenna masts on top — sutrotower.com / NZSEE engineering paper via search.
- Massing: three tubular lattice legs (model as thin tapering cylinders) converging from a 45.7 m triangle to an 18.3 m triangle at the waist (~ 550 ft / 168 m — waist height inferred from the truss levels; check photo) then diverging to a 30.5 m triangle at ~770 ft (235 m), joined by triangular horizontal truss frames at the listed heights; the top crossarm platform carries three vertical antenna masts to 297.8 m.
- Colours: red-orange and white bands (aviation marking) — OSM `colour=#bf4e3b`; white #F2F2F2.

- Photo: `data/raw/reference_photos/sutro_tower/Sutro_Tower_from_Grandview.jpg` (author: Justin Beck; licence: CC BY 2.0) — three legs narrowing to a waist at ≈ 0.58 of the total height (≈ 173 m, measured in this photo; consistent with the 550 ft truss level), then flaring to the crossarm platform, three antenna masts above; red-orange and white bands.
### Alcatraz Island (`alcatraz_cellhouse`, `alcatraz_lighthouse_1854`, `alcatraz_lighthouse_1909`, `alcatraz_water_tower`)
- Dates: fortification from 1850s (citadel 1859); first lighthouse lit 1 Jun 1854 (first on the US West Coast), damaged 1906 and demolished after the 1909 tower; new reinforced concrete lighthouse 1909 (tower 84 ft / 26 m, focal height 214 ft / 65 m — Wikipedia infobox), automated 1963; Army cellhouse built 1909/1910–1912 incorporating parts of the 1859 citadel; federal penitentiary 1934 – 21 Mar 1963; Native American occupation Nov 1969 – Jun 1971 (fires 1970 destroyed the warden's house, social hall and lighthouse keeper's house); NPS/GGNRA from 1972, open to visitors 1973 — https://en.wikipedia.org/wiki/Alcatraz_Island ; https://en.wikipedia.org/wiki/Alcatraz_Island_Lighthouse ; https://en.wikipedia.org/wiki/Alcatraz_Federal_Penitentiary . Water tower built 1940–41 (commonly cited; not verified here).
- Island: centroid 37.826810, -122.423250 (OSM, ≈ 540 × 205 m, long axis 123°), 1,675 × 590 ft, 135 ft high (Wikipedia).
- Structures (OSM centroids, footprints): Main cellhouse 37.826659, -122.423015, 65 × 49 m, axis 136° (3 storeys, ≈ 15 m, estimate); Administration block 37.826399, -122.422581 (35 × 15 m); Dining Hall 37.827030, -122.423454 (52 × 20 m); Building 64 (1905 barracks by the dock) 37.826707, -122.421705 (85 × 30 m); New Industries Building 37.827573, -122.424737 (93 × 21 m, 9 m); Model Industries Building 37.827975, -122.425380 (42 × 28 m); Powerhouse 37.828197, -122.424592 (44 × 25 m, with a tall chimney); Water Tower 37.827573, -122.423935 (13 m footprint; OSM; tank on steel legs, ≈ 30 m — it is taller than the lighthouse per Wikipedia); Lighthouse (1909) 37.826254, -122.422296, OSM height 26 m (a tapering white concrete tower attached to the keeper's house); Warden's House ruin 37.826316, -122.421914 (burned 1970).
- Colours: cellhouse and most buildings weathered concrete/stucco #CFC8B8 / light buff; lighthouse white; water tower white/rust with red graffiti lettering since 1970.

- Photo: `data/raw/reference_photos/alcatraz_cellhouse/Alcatraz_2021.jpg` (author: Chris6d; licence: CC BY-SA 4.0) — island from the water: long cellhouse on the summit, lighthouse at its SE end, water tower on legs at the NW, Building 64 by the dock.
### Fort Point (`fort_point`)
- Dates: Spanish Castillo de San Joaquín (adobe, 9–13 cannon) 1794, abandoned 1835; US Army Corps of Engineers began the masonry fort 1853, completed 1861 (OSM start_date 1861); Fort Point lighthouse (third) 1864 on the roof, deactivated 1934; GGB arch built over it 1933–37; National Historic Site 1970 — https://en.wikipedia.org/wiki/Fort_Point,_San_Francisco
- Location: centroid 37.810600, -122.477092 (OSM relation 5504536, building=fort), directly under the GGB Fort Point arch; long axis bearing ≈ 68° (OSM).
- Dimensions: ≈ 92 × 60 m irregular quadrilateral (OSM), height ≈ 15 m (OSM; 3 casemate tiers + barbette tier); walls brick with granite.
- Massing: a 4-sided brick fort (the bay-facing NW and NE sides are long casemated walls with rows of gun embrasures; the landward S side is a lower barracks/gorge wall), open central parade ground; small iron lighthouse tower on the roof at the NW corner (37.810542, -122.477293).
- Colours: red-brown brick #8C4A36, granite trim #9A968C.

- Photo: `data/raw/reference_photos/fort_point/Golden_Gate_Bridge_tower_views_07.jpg` (author: Ɱ; licence: CC BY-SA 4.0) — looking down from the south tower: brick fort with its open parade ground, roof-top barbette, GGB arch and deck above it.
### Mission San Francisco de Asís / Mission Dolores (`mission_dolores`, `mission_dolores_basilica`)
- Dates: mission founded 1776 at a nearby site (temporary structures); present adobe church built 1782–1791, dedicated 1791 (oldest intact building in SF); next to it a Gothic brick parish church of 1876 was destroyed in 1906; the present church (Basilica since 1952) had its cornerstone laid 1913 and was dedicated Christmas 1918, remodelled with Churrigueresque ornament in 1926 — https://en.wikipedia.org/wiki/Mission_San_Francisco_de_As%C3%ADs ; https://test.opensfhistory.org/news/2021/03/28/streetwise-mission-dolores-san-francisco-landmark-1/ (via search summary).
- Location: adobe church 37.764151, -122.426736 (OSM way 256442765), 320 Dolores St at 16th St, facade facing east onto Dolores St; Basilica 37.764340, -122.427016 (OSM way 256442760), immediately N at the 16th St corner.
- Dimensions: adobe church ≈ 46 × 17 m (OSM; documented interior ≈ 114 × 22 ft — not verified); height ≈ 12 m to the gable (estimate); Basilica ≈ 59 × 33 m, OSM height 14 m (towers higher, ≈ 25 m, estimate).
- Massing: adobe: a long, simple gabled rectangle with a low-pitched red tile roof and a plain white facade with 6 engaged columns in two tiers and a balcony with 3 bells; cemetery garden to the north/west. Basilica: Churrigueresque/Spanish Colonial revival church with twin bell towers on the Dolores St front.
- Colours: whitewash #F1EEE6, red clay tile roof #A0523A; basilica cream #E8DCC6.

- Photo: `data/raw/reference_photos/mission_dolores/Mission_Dolores__1165072805_.jpg` (author: David Ohmer from Cincinnati, USA; licence: CC BY 2.0) — whitewashed adobe facade (engaged columns, bell balcony, red tile roof) with the Basilica's two ornate towers (cream, green-tiled domes) to its right.
### Sutro Baths (`sutro_baths`)
- Dates: built 1894 (construction from ~1894); opened 14 Mar 1896 as the world's largest indoor swimming establishment; later partly converted to an ice rink (1937 Whitney); 1964 sold for apartments; burned June 1966; ruins in GGNRA — https://en.wikipedia.org/wiki/Sutro_Baths (the Sutro Heights article gives 1894–1964 as the operating span; use 1896 opening and 1966 fire).
- Location: ruins centroid 37.780156, -122.514124 (OSM way 32776564), cove N of the Cliff House at Point Lobos; site ≈ 169 × 125 m (OSM area incl. ruins/pond).
- Massing: a huge glass-roofed shed (≈ 150 × 75 m, estimate) on a concrete base at the cove floor: a long series of parallel gabled glass roofs (wood/iron trusses) over 6 salt-water pools + 1 freshwater pool, stepped seating galleries; a classical (Greek-temple) entrance pavilion at the top of the slope on Point Lobos Ave with a long descending stair/gallery. Colours: white frame, glass roofs reading light grey-blue.

- Photo: none downloaded (Wikimedia rate limits). Suggested Commons search: `Category:Sutro Baths` (historic exterior views c. 1896–1910 are public domain).
### Cliff House versions (`cliff_house_1863`, `cliff_house_1896`, `cliff_house_1909`)
- 1858? (anecdotal first building by Sam Brannan); 1863 Cliff House (Senator John Buckley / Charles Butler) — a modest 1-2 storey wooden restaurant; damaged 16 Jan 1887 by the schooner *Parallel* explosion, repaired; destroyed by fire 25 Dec 1894 — https://en.wikipedia.org/wiki/Cliff_House,_San_Francisco
- 1896 Sutro "Gingerbread Palace": seven-storey Victorian château with turrets and a tall central spire/observation tower, perched on the cliff edge; survived 1906; burned 7 Sep 1907.
- 1909 (Reid & Reid, for Emma Merritt): neoclassical 2–3 storey concrete building; remodelled as a roadhouse 1937 (Whitney) with additions 1949–50; restored toward its 1909 look 2003–2004 (Whitney additions removed, new wing); restaurant closed Dec 2020; NPS new 20-year lease 2023 (Sutro Lands End Partners). Current OSM footprint 71 × 32 m, axis 155°, height 7 m above the road (more on the cliff side) — centroid 37.778557, -122.514044. Camera Obscura (1946) on the terrace.
- Massing (1909/2004): simple flat-roofed, white, neoclassical block ~ 3 storeys on the seaward side, 1–2 storeys on Point Lobos Ave; 1896: large timber château, ~ 60 m wide (estimate) with a central octagonal tower to ~ 40 m.

- Photo: `data/raw/reference_photos/cliff_house_1909/Cliff_House_from_Ocean_Beach_crop.jpg` (author: Brocken Inaglory; licence: CC BY-SA 3.0) — the 1909 building as restored in 2004 (plain white blocks) on the rock bluff above the beach. No free photo of the 1896 château was downloaded.
### Embarcadero Freeway (`embarcadero_freeway`)
- Dates: construction from 1955/1957 (sources vary); first section from the Bay Bridge approach near First St north to Broadway opened 5 Feb 1959; Clay and Washington St ramps 1965; closed after the 17 Oct 1989 Loma Prieta earthquake; demolished 1991 (demolition under way early 1991, complete that year) — https://en.wikipedia.org/wiki/California_State_Route_480 ; https://www.aaroads.com/guides/i-480-ca
- Route (approximate; double-deck viaduct ≈ 1.2 mi / 2 km): from the I-80 Bay Bridge approach near First & Fremont streets (≈ 37.7885, -122.3935) NE between Main and Beale toward the waterfront, curving north onto The Embarcadero near Howard/Mission St (≈ 37.7920, -122.3915), then along The Embarcadero in front of the Ferry Building (≈ 37.7955, -122.3940, it passed directly between the Ferry Building and Market St) to Broadway (≈ 37.7990, -122.3988), where it ended with ramps to Broadway / Battery / Sansome. Ramps: First & Fremont, Mission & Main (NB off), Mission & Beale (SB on), Washington & Clay (1965), Broadway. (Ramp list from aaroads/interstate-guide via search; coordinates are my estimates along the current Embarcadero — verify against a historic aerial before final placement.)
- Massing: two stacked decks of a reinforced-concrete viaduct on single-column/portal bents, upper deck ≈ 18–20 m above street, lower ≈ 9–10 m, width ≈ 20 m (estimates); grey concrete #B9B7B0.

- Photo: none downloaded (Wikimedia rate limits). Suggested Commons search: `Category:Embarcadero Freeway`.
### Twin Peaks Tunnel (`twin_peaks_tunnel`)
- Dates: contract awarded 2 Nov 1914; holed through 1917; opened 3 Feb 1918 — https://en.wikipedia.org/wiki/Twin_Peaks_Tunnel
- Location: east portal 37.76194, -122.43694 (Market & Castro, now inside the Market St subway / Castro station since 1980 — no visible portal today); west portal 37.74139, -122.46556 (West Portal Ave & Ulloa St); length 11,675 ft (3.56 km).
- Massing: underground; only the West Portal entrance is visible: a short concrete portal arch at street level (≈ 10 m wide × 7 m high, estimate) at the head of West Portal Ave. Suggest representing only as a small portal marker (or omit — "none").

- Photo: `data/raw/reference_photos/twin_peaks_tunnel/Twin_Peaks_Tunnel.jpg` (author: Jef Poskanzer from Berkeley, CA, USA; licence: CC BY 2.0) — tunnel interior (no portal photo found); only useful to confirm it is not a surface feature.
---

---

---
## Appendix: reference photo index

All downloaded reference photos (960 px thumbnails from upload.wikimedia.org; originals on Commons). Author and licence from the Commons file-page metadata (`extmetadata`).

| Landmark folder | Local file | Commons page | Author | Licence |
|---|---|---|---|---|
| `alamo_square` | `Alamo_Square_with_Painted_Ladies__SF__CA__jjron_26.03.2012.jpg` | [File:Alamo Square with Painted Ladies, SF, CA, jjron 26.03.2012.jpg](https://commons.wikimedia.org/wiki/File:Alamo_Square_with_Painted_Ladies%2C_SF%2C_CA%2C_jjron_26.03.2012.jpg) | jjron | GFDL 1.2 |
| `alcatraz_cellhouse` | `Alcatraz_2021.jpg` | [File:Alcatraz 2021.jpg](https://commons.wikimedia.org/wiki/File:Alcatraz_2021.jpg) | Chris6d | CC BY-SA 4.0 |
| `bay_bridge_east_span_2013` | `San_Francisco_Oakland_Bay_Bridge-_New_and_Old_bridges.jpg` | [File:San Francisco–Oakland Bay Bridge- New and Old bridges.jpg](https://commons.wikimedia.org/wiki/File:San_Francisco%E2%80%93Oakland_Bay_Bridge-_New_and_Old_bridges.jpg) | Frank Schulenburg | CC BY-SA 3.0 |
| `bay_bridge_west_span` | `Bay_Bridge_2022.jpg` | [File:Bay Bridge 2022.jpg](https://commons.wikimedia.org/wiki/File:Bay_Bridge_2022.jpg) | InvadingInvader | CC BY-SA 4.0 |
| `california_academy_of_sciences_2008` | `California-06239_-_California_Academy_of_Sciences__20449900470_.jpg` | [File:California-06239 - California Academy of Sciences (20449900470).j](https://commons.wikimedia.org/wiki/File:California-06239_-_California_Academy_of_Sciences_%2820449900470%29.jpg) | Dennis G. Jarvis | CC BY-SA 2.0 |
| `candlestick_park_1960` | `Candlestick_Postcard_-_01.JPG` | [File:Candlestick Postcard - 01.JPG](https://commons.wikimedia.org/wiki/File:Candlestick_Postcard_-_01.JPG) | Mike Roberts | Public domain |
| `candlestick_park_1971` | `Aerial_view_of_Candlestick_Park__home_stadium_of_the_San_Francisco_49ers_Nationa_1d6b7a.tif.jpg` | [File:Aerial view of Candlestick Park, home stadium of the San Francisc](https://commons.wikimedia.org/wiki/File:Aerial_view_of_Candlestick_Park%2C_home_stadium_of_the_San_Francisco_49ers_National_Football_League_professional_team%2C_with_downtown_San_Francisco%2C_California%2C_in_the_distance_LCCN2011633072.tif) | Carol M. Highsmith | Public domain |
| `candlestick_park_1971` | `Candlestick_Park_aerial.jpg` | [File:Candlestick Park aerial.jpg](https://commons.wikimedia.org/wiki/File:Candlestick_Park_aerial.jpg) | Carol M. Highsmith | Public domain |
| `candlestick_park_1971` | `Candlestick_Park_destruction_1971_-_2013__18439354058_.jpg` | [File:Candlestick Park destruction 1971 - 2013 (18439354058).jpg](https://commons.wikimedia.org/wiki/File:Candlestick_Park_destruction_1971_-_2013_%2818439354058%29.jpg) | rulenumberone2 from San Francisco, CA, USA | CC BY 2.0 |
| `chase_center` | `Chase_Center_-_Warriors.jpg` | [File:Chase Center - Warriors.jpg](https://commons.wikimedia.org/wiki/File:Chase_Center_-_Warriors.jpg) | Christopher Michel | CC BY 2.0 |
| `chase_center` | `Chase_Center_San_Francisco.jpg` | [File:Chase Center San Francisco.jpg](https://commons.wikimedia.org/wiki/File:Chase_Center_San_Francisco.jpg) | Dale Cruse from San Francisco, CA, USA | CC BY 2.0 |
| `city_hall_1915` | `San_Francisco_City_Hall_2.JPG` | [File:San Francisco City Hall 2.JPG](https://commons.wikimedia.org/wiki/File:San_Francisco_City_Hall_2.JPG) | Sanfranman59 | CC BY-SA 3.0 |
| `cliff_house_1909` | `Cliff_House_from_Ocean_Beach_crop.jpg` | [File:Cliff House from Ocean Beach crop.jpg](https://commons.wikimedia.org/wiki/File:Cliff_House_from_Ocean_Beach_crop.jpg) | Brocken Inaglory | CC BY-SA 3.0 |
| `coit_tower` | `Coit_Tower_1.jpg` | [File:Coit Tower 1.jpg](https://commons.wikimedia.org/wiki/File:Coit_Tower_1.jpg) | Ryan Schwark | CC0 |
| `conservatory_of_flowers` | `Conservatory_of_Flowers_-_panoramio.jpg` | [File:Conservatory of Flowers - panoramio.jpg](https://commons.wikimedia.org/wiki/File:Conservatory_of_Flowers_-_panoramio.jpg) | harley photo | CC BY-SA 3.0 |
| `cow_palace` | `Cow_Palace__2563656722_.jpg` | [File:Cow Palace (2563656722).jpg](https://commons.wikimedia.org/wiki/File:Cow_Palace_%282563656722%29.jpg) | gosheshe | CC BY 2.0 |
| `cow_palace` | `Cow_Palace_front_1.JPG` | [File:Cow Palace front 1.JPG](https://commons.wikimedia.org/wiki/File:Cow_Palace_front_1.JPG) | BrokenSphere | CC BY-SA 3.0 |
| `de_young_museum_2005` | `M._H._de_Young_Memorial_Museum.jpg` | [File:M. H. de Young Memorial Museum.jpg](https://commons.wikimedia.org/wiki/File:M._H._de_Young_Memorial_Museum.jpg) | Mark Miller | Public domain |
| `de_young_museum_2005` | `Hamon_Tower.jpg` | [File:Hamon Tower.jpg](https://commons.wikimedia.org/wiki/File:Hamon_Tower.jpg) | Amadscientist | Public domain |
| `dutch_windmill` | `GGParkNorthWindmill2.jpg` | [File:GGParkNorthWindmill2.jpg](https://commons.wikimedia.org/wiki/File:GGParkNorthWindmill2.jpg) | Sam at English Wikipedia | CC BY-SA 3.0 |
| `ewing_field` | `Ewing_Field_1914_05_17.jpg` | [File:Ewing Field 1914 05 17.jpg](https://commons.wikimedia.org/wiki/File:Ewing_Field_1914_05_17.jpg) | anonymous staff photographer for the Examiner | Public domain |
| `ewing_field` | `Ewing_Field_San_Francisco_under_construction_1914_03_22.jpg` | [File:Ewing Field San Francisco under construction 1914 03 22.jpg](https://commons.wikimedia.org/wiki/File:Ewing_Field_San_Francisco_under_construction_1914_03_22.jpg) | anonymous staff photographer for the Examiner | Public domain |
| `ferry_building` | `Ferry_Building_San_Francisco_from_Hyatt_Regency_with_R-Evolution_and_Bay_Bridge__c0ceed.jpg` | [File:Ferry Building San Francisco from Hyatt Regency with R-Evolution ](https://commons.wikimedia.org/wiki/File:Ferry_Building_San_Francisco_from_Hyatt_Regency_with_R-Evolution_and_Bay_Bridge_2026_dllu.jpg) | Daniel Lu ( User:dllu ) | CC BY-SA 4.0 |
| `fort_point` | `Golden_Gate_Bridge_tower_views_07.jpg` | [File:Golden Gate Bridge tower views 07.jpg](https://commons.wikimedia.org/wiki/File:Golden_Gate_Bridge_tower_views_07.jpg) | Ɱ | CC BY-SA 4.0 |
| `golden_gate_bridge` | `Golden_Gate_Bridge_aerial_photo_2010-09-21_1_.jpg` | [File:Golden Gate Bridge aerial photo 2010-09-21 (1).jpg](https://commons.wikimedia.org/wiki/File:Golden_Gate_Bridge_aerial_photo_2010-09-21_(1).jpg) | Reedy | CC BY-SA 3.0 |
| `golden_gate_bridge` | `Aerial_view_of_Golden_Gate_Bridge_from_the_south_dllu.jpg` | [File:Aerial view of Golden Gate Bridge from the south dllu.jpg](https://commons.wikimedia.org/wiki/File:Aerial_view_of_Golden_Gate_Bridge_from_the_south_dllu.jpg) | Daniel L. Lu (user:dllu) | CC BY-SA 4.0 |
| `golden_gate_bridge` | `HAER_CAL_38-SANFRA_140-3_fort_point_arch.jpg` | [File:GENERAL VIEW, LOOKING NORTH, WITH APPROACH SPAN DECK ARCH ON LEFT](https://commons.wikimedia.org/wiki/File:GENERAL_VIEW,_LOOKING_NORTH,_WITH_APPROACH_SPAN_DECK_ARCH_ON_LEFT_-_Golden_Gate_Bridge,_Spanning_mouth_of_San_Francisco_Bay,_San_Francisco,_San_Francisco_County,_CA_HAER_CAL,38-SANFRA,140-3.tif) | Lowe, Jet
Related names:

Strauss, Joseph B
Pacific Bridge Company
John Roebling's Sons Co | Public domain |
| `golden_gate_park` | `Golden_gate_park_aerial.jpg` | [File:Golden gate park aerial.jpg](https://commons.wikimedia.org/wiki/File:Golden_gate_park_aerial.jpg) | uploader Aomarks | CC BY-SA 3.0 |
| `japanese_tea_garden` | `Japanese_tea_garden_Golden_Gate_Park.JPG` | [File:Japanese tea garden Golden Gate Park.JPG](https://commons.wikimedia.org/wiki/File:Japanese_tea_garden_Golden_Gate_Park.JPG) | Asamudra ( talk ) | CC BY 3.0 |
| `kezar_stadium_1925` | `OldKezarEastScoreboard.jpg` | [File:OldKezarEastScoreboard.jpg](https://commons.wikimedia.org/wiki/File:OldKezarEastScoreboard.jpg) | uploader Tom SF | Public domain |
| `kezar_stadium_1925` | `OldKezarArch.jpg` | [File:OldKezarArch.jpg](https://commons.wikimedia.org/wiki/File:OldKezarArch.jpg) | uploader Tom SF | CC BY-SA 3.0 |
| `kezar_stadium_1990` | `Kezar_Stadium__2341900471_.jpg` | [File:Kezar Stadium (2341900471).jpg](https://commons.wikimedia.org/wiki/File:Kezar_Stadium_%282341900471%29.jpg) | Ashleigh Nushawg | CC BY 2.0 |
| `kezar_stadium_1990` | `_49ers__28791895142_.jpg` | [File:'49ers (28791895142).jpg](https://commons.wikimedia.org/wiki/File:%2749ers_%2828791895142%29.jpg) | Topher. | CC BY 2.0 |
| `kezar_stadium_1990` | `Wfm_kezar_stadium.jpg` | [File:Wfm kezar stadium.jpg](https://commons.wikimedia.org/wiki/File:Wfm_kezar_stadium.jpg) | uploader Finlay McWalter | Public domain |
| `lands_end` | `Coastal_Trail_and_Golden_Gate_Bridge__April_2019.JPG` | [File:Coastal Trail and Golden Gate Bridge, April 2019.JPG](https://commons.wikimedia.org/wiki/File:Coastal_Trail_and_Golden_Gate_Bridge%2C_April_2019.JPG) | Pi.1415926535 | CC BY-SA 3.0 |
| `legion_of_honor` | `California_Palace_of_the_Legion_of_Honor_San_Francisco_California_LCCN2011630619.tif.jpg` | [File:California Palace of the Legion of Honor, San Francisco, Californ](https://commons.wikimedia.org/wiki/File:California_Palace_of_the_Legion_of_Honor,_San_Francisco,_California_LCCN2011630619.tif) | Carol M. Highsmith | Public domain |
| `legion_of_honor` | `500px_photo_55877656_.jpeg` | [File:500px photo (55877656).jpeg](https://commons.wikimedia.org/wiki/File:500px_photo_(55877656).jpeg) | Hugh Nelson | CC BY 3.0 |
| `legion_of_honor` | `California_-_San_Francisco_-_NARA_-_23935697.jpg` | [File:California - San Francisco - NARA - 23935697.jpg](https://commons.wikimedia.org/wiki/File:California_-_San_Francisco_-_NARA_-_23935697.jpg) | Unknown authorUnknown author or not provided | Public domain |
| `midwinter_fair_1894` | `CMIE_a.jpg` | [File:CMIE a.jpg](https://commons.wikimedia.org/wiki/File:CMIE_a.jpg) | The original uploader was Mdiamante at English Wikipedia . | Public domain |
| `mission_dolores` | `Mission_Dolores__1165072805_.jpg` | [File:Mission Dolores (1165072805).jpg](https://commons.wikimedia.org/wiki/File:Mission_Dolores_%281165072805%29.jpg) | David Ohmer from Cincinnati, USA | CC BY 2.0 |
| `mission_dolores_park` | `Dolores_Park_May_2025.jpg` | [File:Dolores Park May 2025.jpg](https://commons.wikimedia.org/wiki/File:Dolores_Park_May_2025.jpg) | Alexwennerberg | CC0 |
| `murphy_windmill` | `Murphy_windmill.jpg` | [File:Murphy windmill.jpg](https://commons.wikimedia.org/wiki/File:Murphy_windmill.jpg) | Allie_Caulfield | CC BY 2.0 |
| `oracle_park` | `Aerial_photograph_of_AT_T_Park__home_of_the_San_Francisco_Giants.jpg` | [File:Aerial photograph of AT&T Park, home of the San Francisco Giants.](https://commons.wikimedia.org/wiki/File:Aerial_photograph_of_AT%26T_Park%2C_home_of_the_San_Francisco_Giants.jpg) | The original uploader was Grant.gibson at English Wikipedia . | CC BY 2.5 |
| `painted_ladies` | `San_Francisco__CA__USA__Painted_Ladies_--_2022_--_3059.jpg` | [File:San Francisco (CA, USA), Painted Ladies -- 2022 -- 3059.jpg](https://commons.wikimedia.org/wiki/File:San_Francisco_%28CA%2C_USA%29%2C_Painted_Ladies_--_2022_--_3059.jpg) | Dietmar Rabich | CC BY-SA 4.0 |
| `painted_ladies` | `San_Francisco__CA__USA__Painted_Ladies_--_2022_--_3063.jpg` | [File:San Francisco (CA, USA), Painted Ladies -- 2022 -- 3063.jpg](https://commons.wikimedia.org/wiki/File:San_Francisco_%28CA%2C_USA%29%2C_Painted_Ladies_--_2022_--_3063.jpg) | Dietmar Rabich | CC BY-SA 4.0 |
| `palace_of_fine_arts_1967` | `Palace_of_Fine_Arts__16794p_.jpg` | [File:Palace of Fine Arts (16794p).jpg](https://commons.wikimedia.org/wiki/File:Palace_of_Fine_Arts_%2816794p%29.jpg) | Rhododendrites | CC BY-SA 4.0 |
| `presidio_forest` | `Aerial_view_-_Presidio-whole.jpg` | [File:Aerial view - Presidio-whole.jpg](https://commons.wikimedia.org/wiki/File:Aerial_view_-_Presidio-whole.jpg) | Robert Campbell | CC BY-SA 3.0 |
| `recreation_park_valencia` | `Opening_of_Base_Ball_Season_1912__Recreation_Park__San_Francisco__Cal._April_2_1_9e8851.jpg` | [File:Opening of Base Ball Season 1912, Recreation Park, San Francisco,](https://commons.wikimedia.org/wiki/File:Opening_of_Base_Ball_Season_1912%2C_Recreation_Park%2C_San_Francisco%2C_Cal._April_2_1912%2C_Seals_vs_Oaks_%2817125734669%29.jpg) | California Historical Society Digital Collection | No restrictions |
| `salesforce_tower` | `Salesforce_Tower_Completed_2018.jpg` | [File:Salesforce Tower Completed 2018.jpg](https://commons.wikimedia.org/wiki/File:Salesforce_Tower_Completed_2018.jpg) | Leijurv | CC BY-SA 4.0 |
| `salesforce_tower` | `Salesforce_Tower_Roof.jpg` | [File:Salesforce Tower Roof.jpg](https://commons.wikimedia.org/wiki/File:Salesforce_Tower_Roof.jpg) | InvadingInvader | CC BY-SA 4.0 |
| `salesforce_tower` | `Salesforce_Tower_from_Ina_Coolbrith_Park-01445.jpg` | [File:Salesforce Tower from Ina Coolbrith Park-01445.jpg](https://commons.wikimedia.org/wiki/File:Salesforce_Tower_from_Ina_Coolbrith_Park-01445.jpg) | Frank Schulenburg | CC BY-SA 4.0 |
| `salesforce_transit_center` | `Salesforce_Park_and_bus_bridge__seen_from_Salesforce_Tower.jpg` | [File:Salesforce Park and bus bridge, seen from Salesforce Tower.jpg](https://commons.wikimedia.org/wiki/File:Salesforce_Park_and_bus_bridge%2C_seen_from_Salesforce_Tower.jpg) | Fullmetal2887 | CC BY-SA 4.0 |
| `salesforce_transit_center` | `Salesforce_Transit_Center_main_entrance.jpg` | [File:Salesforce Transit Center main entrance.jpg](https://commons.wikimedia.org/wiki/File:Salesforce_Transit_Center_main_entrance.jpg) | Fullmetal2887 | CC BY-SA 4.0 |
| `salesforce_transit_center` | `Salesforce_Transit_Center__San_Francisco__1__2023-07-18.jpg` | [File:Salesforce Transit Center, San Francisco (1) 2023-07-18.jpg](https://commons.wikimedia.org/wiki/File:Salesforce_Transit_Center%2C_San_Francisco_%281%29_2023-07-18.jpg) | The wub | CC BY-SA 4.0 |
| `seals_stadium` | `Seals_Stadium_Army-Navy_War_Show.jpg` | [File:Seals Stadium Army-Navy War Show.jpg](https://commons.wikimedia.org/wiki/File:Seals_Stadium_Army-Navy_War_Show.jpg) | Official U. S. Signal Corps Photo | Public domain |
| `seals_stadium` | `Corbett___Fields__1933.jpg` | [File:Corbett & Fields, 1933.jpg](https://commons.wikimedia.org/wiki/File:Corbett_%26_Fields%2C_1933.jpg) | Unknown author Unknown author | Public domain |
| `spreckels_temple_of_music` | `Golden_Gate_Park_-_Spreckels_Temple_of_Music_02.jpg` | [File:Golden Gate Park - Spreckels Temple of Music 02.jpg](https://commons.wikimedia.org/wiki/File:Golden_Gate_Park_-_Spreckels_Temple_of_Music_02.jpg) | Joe Mabel | CC BY-SA 3.0 |
| `sutro_heights` | `SutroHeightsPark.jpg` | [File:SutroHeightsPark.jpg](https://commons.wikimedia.org/wiki/File:SutroHeightsPark.jpg) | uploader Nz1845 | CC BY-SA 3.0 |
| `sutro_tower` | `Sutro_Tower_from_Grandview.jpg` | [File:Sutro Tower from Grandview.jpg](https://commons.wikimedia.org/wiki/File:Sutro_Tower_from_Grandview.jpg) | Justin Beck | CC BY 2.0 |
| `transamerica_pyramid` | `SF_Transamerica_full_CA.jpg` | [File:SF Transamerica full CA.jpg](https://commons.wikimedia.org/wiki/File:SF_Transamerica_full_CA.jpg) | Daniel Schwen | CC BY-SA 2.5 |
| `transamerica_pyramid` | `South_face_of_the_Transamerica_Pyramid__2017.jpg` | [File:South face of the Transamerica Pyramid, 2017.jpg](https://commons.wikimedia.org/wiki/File:South_face_of_the_Transamerica_Pyramid%2C_2017.jpg) | Dllu | CC BY-SA 4.0 |
| `transamerica_pyramid` | `Transamerica_Pyramid_from_Coit_Tower_____-_panoramio.jpg` | [File:Transamerica Pyramid from Coit Tower コイトタワー (サンフランシスコ) - panorami](https://commons.wikimedia.org/wiki/File:Transamerica_Pyramid_from_Coit_Tower_%E3%82%B3%E3%82%A4%E3%83%88%E3%82%BF%E3%83%AF%E3%83%BC_%28%E3%82%B5%E3%83%B3%E3%83%95%E3%83%A9%E3%83%B3%E3%82%B7%E3%82%B9%E3%82%B3%29_-_panoramio.jpg) | Yoshio Kohara | CC BY 3.0 |
| `twin_peaks_tunnel` | `Twin_Peaks_Tunnel.jpg` | [File:Twin Peaks Tunnel.jpg](https://commons.wikimedia.org/wiki/File:Twin_Peaks_Tunnel.jpg) | Jef Poskanzer from Berkeley, CA, USA | CC BY 2.0 |
| `union_square` | `San_Francisco_Union_Square.jpg` | [File:San Francisco Union Square.jpg](https://commons.wikimedia.org/wiki/File:San_Francisco_Union_Square.jpg) | Lordsamp | CC BY-SA 4.0 |
| `yerba_buena_gardens` | `2017_Yerba_Buena_Gardens.jpg` | [File:2017 Yerba Buena Gardens.jpg](https://commons.wikimedia.org/wiki/File:2017_Yerba_Buena_Gardens.jpg) | Beyond My Ken | CC BY-SA 4.0 |
