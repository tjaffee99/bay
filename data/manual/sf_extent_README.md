# Pre-1906 San Francisco: built-up extent by snapshot year

Files: `sf_extent_1849.csv`, `sf_extent_1852.csv`, `sf_extent_1856.csv`, `sf_extent_1863.csv`, `sf_extent_1869.csv`, `sf_extent_1876.csv`, `sf_extent_1886.csv`, `sf_extent_1899.csv`, `sf_extent_1905.csv`.

Each file holds one or more rings marking where city blocks had **substantial building** in that year. "Substantial" means roughly a third or more of the block frontage built, judged by eye at block resolution. Scattered farmhouses, dairies and roadhouses are left out.

## Format

Columns: `ring,seq,street_a,street_b,note,source_url`.

- `ring` is an id. A year can have several rings, for example `core`, `mission_dolores`, `presidio_post`, `butchertown` and `ocean_view`. Vertices run in `seq` order, and each ring closes back to seq 1.
- Street names are present-day DataSF names, using the same lookup as `pipeline/fire_1906.py`. Use `OFarrell`, not `O'Farrell`, and `The Embarcadero`.
- Every pair resolves through `fire_1906.intersection()`. I checked this. Three kinds of pair resolve by closest approach instead of a shared node:
  - `The Embarcadero & Market St`, at 64 m. Fine.
  - `Quint St & Arthur Ave`, which is a node.
  - `Rankin St & Davidson Ave`, which is a node.
- Rows whose `note` starts with `@lat,lon` are explicit vertices. Only the Presidio main-post rings use them, because they sit away from the city grid. The street pair on those rows is a dummy (`Funston Ave & Moraga Ave`).
- I built all rings as polygons in UTM 10N. Every one comes out valid; the method is described below. The areas in acres are:

| year | core | other rings |
|---|---|---|
| 1849 | 90 | Happy Valley 52, Mission Dolores 18, Presidio 5 |
| 1852 | 212 | Happy Valley/Rincon 125, Mission Dolores 35 |
| 1856 | 948 | Mission Dolores 53 |
| 1863 | 1,626 | Mission 104 |
| 1869 | 1,724 | Mission corridor 104, Mission 242, Hayes Valley 23, Potrero Point 12, South SF/Oakdale 16 |
| 1876 | 2,496 | Mission 345, Butchertown 26, Oakdale 16, Potrero Point 12 |
| 1886 | 4,102 | Noe Valley 139, Bernal/Precita 138, Butchertown 26, … |
| 1899 | 6,576 | Potrero Hill 643, inner Richmond 149, Bernal 138, Bayview 121, Ocean View 37, Presidio post 123 |
| 1905 | 6,576 | adds inner Richmond 267, inner Sunset 39, Bernal 186 |

**Waterfront edges** use present streets, mostly The Embarcadero, as in the fire file. Much of the land outside the shoreline of the year is later fill, so clip each ring with the land and fill polygons (`land_not_before`, Phase 2) before placing buildings.

**Snapshots in between.** Rings are snapshots, not lifespans. Interpolate between them, or treat each ring as valid from its year to the next snapshot. Because the city only grew, the union of earlier rings is a safe lower bound.

## Maps and sources used

| Snapshot | Primary source (viewed) | How used |
|---|---|---|
| 1849 | Eddy, *Official map of San Francisco* 1849 (LoC, <https://www.loc.gov/item/77692722/>), street grid only. Narrative: SF Chronicle, "Seeking gold, the 49ers found a sad, sodden S.F." (<https://preview-prod.w.sfchronicle.com/bayarea/article/Seeking-gold-the-49ers-found-a-sad-sodden-S-F-5969393.php>): the commercial district ran from the bay edge at Montgomery St up to Portsmouth Square, and Happy Valley (near the later Palace Hotel) held about 2,000 people. "A Room at Clark's Point" (<https://www.sanfranciscostory.com/a-room-at-clarks-point/>): Broadway & Battery was the landing place. | Reconstructed. **LOW.** |
| 1852 | US Coast Survey, *City of San Francisco and its vicinity* (Cutts/Rodgers, survey completed July 1853, publ. 1853), Rumsey 11890.000, <https://www.davidrumsey.com/luna/servlet/detail/RUMSEY~8~1~321600~90090766>. Buildings are drawn as black blocks. | Traced by eye from full-resolution crops through the IIIF server (`…/iiif/RUMSEY~8~1~321600~90090766/x,y,w,h/1900,/0/default.jpg`). **MEDIUM-HIGH.** Error about ±1 block. |
| 1856 | US Coast Survey, *City of San Francisco and its vicinity*, 1857 (A. F. Rodgers plane-table survey), Rumsey 6811.000, <https://www.davidrumsey.com/luna/servlet/detail/RUMSEY~8~1~239938~5512085>. Reissued 1859 with the same topography (Rumsey 1030.000, <https://www.davidrumsey.com/luna/servlet/detail/RUMSEY~8~1~2212~180003>); that sheet is oriented with north to the right. | Traced. It represents 1856–57. **MEDIUM-HIGH** for the core, MEDIUM for the Mission and Hayes edges. |
| 1863 | No dated survey used. Interpolated between 1857/59 and 1869. | **LOW-MEDIUM.** A better source would be the 1861 *City and County of San Francisco* (Rumsey 3867.000) or the 1864 Rumsey 11809.000 map; I did not view either. |
| 1869 | US Coast Survey, *San Francisco Peninsula* 1869 (1:40,000), Rumsey 2648.000, <https://www.davidrumsey.com/luna/servlet/detail/RUMSEY~8~1~2214~190053>. Built frontages are drawn as heavy black block outlines. Hayes Valley follows the Market & Octavia context statement (<https://default.sfplanning.org/DPRforms/MO_Context_Final_202007.pdf>), which reads the 1869 map the same way: development along Hayes St, Grove to Fell. Bayview follows the BVHP context statement (<https://timkelleyconsulting.com/BVHP_Context.pdf>): in 1869 the densest point was Railroad Ave (3rd St) & 15th (Oakdale) Ave; Butchertown opened in 1868. | Traced. **MEDIUM.** The small scale limits resolution. |
| 1876 | Interpolated between 1869 and the 1886–87 Sanborn, checked against Britton, Rey & Co.'s 1875 bird's-eye *Graphic chart of the city and county* (<https://www.loc.gov/item/75693102/>; LoC also has 1868 and 1876 views, items 75693101 and 75693103). | **LOW-MEDIUM.** The Western Addition edge at Laguna is a judgement call based on the 1870s cable and horse-car boom described in the M&O context statement. |
| 1886 | Sanborn 1886–87 edition (LoC). Vol. 3 (1887) key map: <https://www.loc.gov/item/sanborn00813_004/> covers SoMa west of 8th and the Mission from Market to about 26th, Dolores to Potrero Ave. Vol. 5 (1886) key: <https://www.loc.gov/item/sanborn00813_007/> covers Eureka and Noe Valley in part (sheets 124–137), upper Mission/Precita (138–142), Potrero Point (144, 155), and Butchertown/"South San Francisco" (145–152). The Western Addition edge comes from the Japantown context (<https://archives.sfplanning.org/documents/1696-Japantown_Context_Statement_REVISED_5-11.pdf>: Fillmore commercial strip by the late 1880s). | Sanborn **coverage**, which is a proxy for built-up area: Sanborn mapped insurable built blocks, though coverage also takes in some half-empty blocks. **MEDIUM.** |
| 1899 | Sanborn 1899–1900 edition, vol. 1 index (<https://www.loc.gov/item/sanborn00813_008/>), whose inset shows the coverage of vols. 1–6. Ocean View is from the Sanborn 1897 *Ocean View* sheet (<https://www.loc.gov/item/sanborn00730_001/>), not viewed in detail. | **MEDIUM** for the core, **LOW-MEDIUM** for the outer rings. |
| 1905 | The 1899 coverage plus growth. The 1904 Sanborn *Block Line Map* (<https://www.loc.gov/item/sanborn00813_014/>) covers downtown and SoMa only and marks brick and fireproof buildings. Richmond and Sunset rings are judgement calls. | **MEDIUM** for the core, **LOW** for the periphery. |

The images are reachable for anyone who wants to redo this more carefully. Rumsey serves full resolution through IIIF (`https://www.davidrumsey.com/luna/servlet/iiif/<ID>/info.json`). LoC serves `https://tile.loc.gov/image-services/iiif/service:gmd:…/full/pct:25/0/default.jpg`; the image ids are in each item's `?fo=json`.

The Coast Survey sheets of 1853, 1857, 1859 and 1869 are the best candidates for **georeferencing and real tracing in QGIS**. A georeferenced trace would replace these block-level rings, and it could also yield individual building footprints for 1853 and 1857: the maps draw every building.

## How I built the rings

1. I opened each map at overview, then at about 0.3–0.5 m per pixel over downtown, SoMa, the Mission and the Western Addition. On the 1853/57/59 Coast Survey sheets every building is drawn. The 1869 sheet draws built frontage as heavy outline.
2. I drew the boundary along streets around the contiguous built blocks, one block outward where a block was about half built. Isolated clusters became separate rings.
3. The Presidio post ring is the 1776–1840s adobe quadrangle area around today's Officers' Club, Bldg 50. From 1899 it is enlarged to cover the Montgomery St barracks (1895–97) and the post hospital. Dates come from the 1993 NHL inventory (see `data/tables/known_building_dates.csv`).
4. Things deliberately left out:
   - Cliff House, Sutro Baths and Fort Point, which are separate landmarks.
   - Black Point/Fort Mason houses.
   - Lone Mountain cemeteries, the Ocean House roadhouse, racetracks, and scattered dairies in Cow Hollow, Noe and Bernal. These are not "built-up blocks".

## Confidence summary

| Year | Confidence | Main doubt |
|---|---|---|
| 1849 | LOW | No building-level map. Limits of the tent city are unknown. |
| 1852 | MEDIUM-HIGH | Waterfront on piles: pier-buildings beyond Davis/Front are omitted. |
| 1856 | MEDIUM-HIGH | Western edge (Taylor/Mason) and the Mission plank-road ribbon, which is left out. |
| 1863 | LOW-MEDIUM | Interpolated. |
| 1869 | MEDIUM | 1:40,000 sheet. Western Addition beyond Larkin is sparse and outside the ring except Hayes Valley. |
| 1876 | LOW-MEDIUM | Interpolated. The Western Addition edge (Laguna) is uncertain by ±2 blocks. |
| 1886 | MEDIUM | Coverage proxy. The Noe and Bernal rings over-state density. |
| 1899 | MEDIUM | Coverage proxy. The west edge (Arguello/Stanyan) over-states density in Presidio Heights and the inner Richmond. |
| 1905 | MEDIUM / LOW | Periphery rings are judgement calls. |

## What the built fabric looked like (for procedural stand-ins on real parcels)

Use these as parameter ranges and mark the results `procedural`. Lots are the real parcel lines. Today's parcels mostly preserve the 19th-century subdivision.

**Lot sizes.**
- North of Market, a 50-vara lot (137.5 ft square) was usually split into five lots of 27.5 × 137.5 ft (8.4 × 41.9 m). Other common sizes were 25 × 120, 25 × 100 and 20 × 80 ft. Source: M&O context (lot-size footnote, citing Moudon, *Built for Change*).
- South of Market, O'Farrell's 1847 survey used 100-vara blocks, four times the area of the northern blocks, from 1st St to 5th St (Transit Center District context, <https://archives.sfplanning.org/CDG/docs/transit_center/Context_Statement_FINAL.pdf>). These were later cut by alleys (Natoma, Minna, Tehama, Clementina, Jessie, …) into smaller lots of about 25 × 75–80 ft, which held working-class housing (alley-lot size is my ESTIMATE from the Sanborn sheets, not a sourced figure).
- Bayview tracts (1860s–70s) used 25 × 100 ft "New York style" lots (BVHP context).

**1848–1852, Gold Rush.**
- Tents, canvas and simple 1–2 storey wood-frame buildings, many with false fronts, some prefabricated and shipped in. Hotels and boarding houses dominated (SF Planning, *Early Settlement Era Styles 1848–1906*, <https://sfplanning.org/sites/default/files/documents/preserv/SFsurvey/hcs_Early_Settlement_Era_Styles-Draft.pdf>).
- After the 1849–51 fires, the core around Portsmouth Square and Montgomery St rebuilt largely in brick at about 2–3 storeys with iron shutters. This is general history, not checked against a source here; the storey range is an ESTIMATE. The Montgomery Block (1853) was 4 storeys, about 15 m, and the tallest building in the city (<https://en.wikipedia.org/wiki/List_of_tallest_buildings_in_San_Francisco>).
- Coverage downtown was high: buildings were built lot-line to lot-line, so the 1853 map shows solid black blocks between Kearny and Front.
- Beyond Stockton, detached 1–2 storey frame houses on large lots.

**1853–1869, Comstock boom.**
- Downtown, north of California and east of Kearny: 2–4 storey brick commercial blocks, built out to the lot lines, flat roofs with parapets and cornices. Old St. Mary's tower reached 27 m.
- SoMa: brick rowhouses appear, such as the 1861–62 Ladd row on Folsom between 1st and 2nd (Transit Center context, "Comstock Lode Boom"). Rincon Hill and South Park had large wooden Italianate villas on big lots (Early Settlement HCS).
- Elsewhere: wood frame, 1–2 storeys, Gothic Revival, Greek Revival and Italianate. Larger setbacks, because many houses predate the street grading (Early Settlement HCS).
- Hayes Valley and the Mission were villa and cottage suburbs along horse-car lines.

**1870–1889, Victorian boom.**
- Row-built wood-frame Italianates, flat-front then bay-windowed, and later Stick/Eastlake. Typically 2 storeys over a raised basement, about 7–10 m to the cornice (height is an ESTIMATE).
- Built by speculative builders such as The Real Estate Associates (1,000+ nearly identical houses from 1870). On 25-ft lots most "directly abutted their neighbors", with light wells and a front setback of about 1.5–3 m for stairs and bay (setback figure is an ESTIMATE). Source: M&O context (Western Addition section).
- Front setbacks are "more generous, even for narrow row lots within the Mission and Western Addition". A house flush with the street usually indicates post-1906 work (Early Settlement HCS).
- Rear yards were deep: build about 50–65 % of the lot depth (ESTIMATE). Two-flat buildings were common in working-class Potrero, Dogpatch and SoMa (Early Settlement HCS).
- Nob Hill mansions were wood (Hopkins, Stanford, Crocker) on granite-walled sites. The Flood mansion (1886) was the first brownstone.
- Downtown: 3–5 storey brick and stone commercial blocks with cast-iron fronts. The Palace Hotel (1875) was 7 storeys and 37 m, covering a whole block (`data/tables/notable_pre1906.csv`).
- Material shares: of the 28,188 buildings destroyed in 1906, 24,671 were wood and 3,168 brick (USGS via `fire_1906_README.md`). That is about 88 % wood even inside the burned district.

**1890–1906, steel frame and Queen Anne.**
- Downtown gained the first steel-frame towers:
  - Chronicle, 1890, 10 storeys, 66 m with its clock tower.
  - Mills, 1892, 10 storeys, 47 m.
  - Crocker, 1891, 11 storeys.
  - Call, 1898, 15 storeys, 96 m.
  - Mutual Savings, 1902, 12 storeys.
  - St. Francis, 1904, 12 storeys.
  - Merchants Exchange and Flood, both 1904 and 12 storeys.
- The ordinary downtown fabric stayed at 3–6 storeys.
- Fire limits: after the 1850s fires, wood frame was banned downtown and along the first blocks of 2nd, New Montgomery, 3rd, 4th and 5th south to Howard. Inside the limits, pre-quake commercial buildings were masonry; outside them, SoMa mixed frame cottages, tenements and industry (Transit Center context, "Fire Limits").
- The 1904 Sanborn block-line map shows brick concentrated in the financial district and along Market. Many downtown and most SoMa blocks are still frame.
- Residential areas: 2–3 storey Queen Anne houses and flats. Corner lots carried 3-storey flats or apartment hotels over shops.
- Western Addition, Haight and Mission: 25-ft lots, 2–3 storeys at 8–11 m, short front setbacks with steps, bay windows, and 40–50 % rear yards.

**Suggested generation rules.** These are my suggested defaults, not sourced figures.

| Area and era | Material | Storeys | Lot coverage |
|---|---|---|---|
| Downtown inside the fire limits, 1853–1889 | brick | 2–5 (mostly 3) | 90–100 % |
| Downtown inside the fire limits, 1890–1905 | brick, a few steel landmarks | as before; tall towers come from `notable_pre1906.csv` | as before |
| SoMa alleys and Chinatown | wood frame | 2–3 | 70–90 % |
| Residential districts | wood frame | 2 (to 1885), 2–3 (after) | depth 55–65 % of lot, width 100 % on row lots, 70–80 % on detached lots |

- Typical heights:

| Building type | Height |
|---|---|
| Residential storey | ~3.6 m |
| Commercial storey | ~4.5 m |
| 2-storey Italianate rowhouse | ~9 m including the raised basement |

- Set residential houses back 2 m from the front lot line, except corner commercial buildings and anything inside the fire limits.

## Other files

- `data/tables/notable_pre1906.csv`: 43 significant pre-1906 buildings with dates, location, height, storeys and footprint where known. Every row cites a URL. Estimates are flagged `ESTIMATE` in `shape_note`.
- `data/tables/known_building_dates.csv`: dated buildings on federal and exempt land, covering the Presidio inventory and civic, port, religious and educational buildings.
- Raw downloads (gitignored), all in `data/raw/`:
  - `presidio/`: the 1993 NHL nomination with full inventory, the Presidio Trust building footprints, and the HABS and SHS reports.
  - `sf_context/`: SF Planning context statements.
  - `osm_bbbike/`: OSM extract used for coordinates and `start_date`.
