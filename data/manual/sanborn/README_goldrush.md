# Gold-rush San Francisco from OpenHistoricalMap (`sf_goldrush_*`)

2,696 building outlines that OpenHistoricalMap (OHM, https://www.openhistoricalmap.org/, data **CC0 1.0**)
volunteers traced from three historical maps of San Francisco, re-dated here from evidence and written in the
Sanborn tracing format. Tool: `pipeline/ohm_import.py` (`download`, then `goldrush`); raw Overpass answers in
`data/raw/ohm/` (gitignored). Integration: `ohm_import.apply_goldrush` (below).

| file | map (what OHM cites on every way) | date shown | outlines |
|---|---|---|---|
| `sf_goldrush_1851.geojson` | *Map of the Burnt District of San Francisco*, fire of 3-4 May 1851 (Huntington Library, https://hdl.huntington.org/digital/collection/p9539coll1/id/23520): buildings destroyed and the lettered ones that survived, with owners, material (wood / iron / brick) and the beached storeships | 4 May 1851 | 112 |
| `sf_goldrush_1852.geojson` | U.S. Coast Survey, *City of San Francisco and its Vicinity* (R. D. Cutts, topography A. F. Rodgers; "survey completed April 1852", Vogdes p. 253; published 1853; David Rumsey 3463.000, https://www.davidrumsey.com/luna/servlet/detail/RUMSEY~8~1~2210~180022) — the same chart (another issue) our `sf_extent_1852.csv` was read from. 145 of the outlines (western scattered houses, Mission road) were traced from Pastmapper's georeferenced copy of the chart | April 1852 | 2,356 |
| `sf_goldrush_1887.geojson` | Sanborn Map Co., San Francisco 1887 vol. 1 (LoC `g4364sm_g00813188701`, https://www.loc.gov/resource/g4364sm.g4364sm_g00813188701/), sheets p1R, p3L, p10R, p11L, p13R, p15L, p15R as georeferenced on oldinsurancemaps.net: Chinatown / Dupont St blocks, Stockton-Powell, Market & Mason, the north waterfront | 1887 | 228 |
| `sf_goldrush_coverage.geojson` | one feature per map: 1851 = the burned district (closed round the map's buildings and the 1852 buildings OHM tags `start_date:edtf=1851/`); 1852 = today's blocks holding a traced building + 10 m round each outline (399 ha: North Beach, Telegraph Hill, downtown, Happy Valley / Rincon, scattered houses to Mission Dolores); 1887 = blocks >= 30 % covered by the traced buildings | | 3 |

`data/manual/ohm/sf_fires_1851.geojson`: the 4 May 1851 district (as above) and the 22 June 1851 fire
(Powell-Sansome-Clay-Broadway, "ten blocks and portions of six others", SFFD Guardians of the City; the whole
rectangle is drawn).

OHM's own dates on these ways are placeholders: 1840 / 1864 "arbitrary, proximate to date of geometry source"
(2,018 ways), 1848 / 1876 (Pastmapper set), /1851 for the Burnt District map. They are ignored.

## Columns

The Sanborn columns (`id` = `ohm_way_<id>`, `map_year`, `volume`, `volume_label`, `sheet` (1887 page),
`loc_url`, `stories`, `stories_source`, `material`, `use`, `use_source`, `name` (owner on the 1851 map),
`confidence`, `georef` (OHM way), `extraction`, `area_m2`, `modern_overlap`) plus:

* `start_year`, `end_year` — the evidence-based dates (estimated inside the window; empty on an outline whose
  structure is carried by a later map's outline, `end_rule = represented`);
* `start_min` / `start_max`, `end_min` / `end_max` — the evidence window; `date_evidence` — every rule that applied;
* `end_rule`: `exact` (burned 4 May 1851 / 22 June 1851), `between_maps` (gone by the next map of the same block),
  `successor` (`end_year` is an upper bound — the 1906 fire or today's building — and the building ends earlier
  when a later building starts on its spot), `represented`;
* `represented_by`, `modern_same` (today's building, left to the modern data), `doc_match` (an `early_sf.csv` /
  `notable_pre1906.csv` row on this outline), `land_year` (terrain), `fill_zone`, `in_street_row` (share in today's
  street right-of-way), `burned_1906`, `ohm_url`, `ohm_start_date` / `ohm_end_date`.

## Dating rules

Start (window `[lo, hi]`, `hi` = the map date; position in the window by the extent snapshot, deterministic hash):
* 1849.0 (the boom; generated fabric and the snapshot series start there) is the floor; pre-1849 Yerba Buena
  structures are `early_sf.csv` rows (34 outlines match one; `apply_goldrush` gives them the outline).
* On the 1852 chart inside the district burned on 4 May 1851 (and not a survivor of the 1851 map): built after the
  fire, 1851.34-1852.3 (320 outlines). Inside the 22 June 1851 fire rectangle: after 1851.47 (300).
* On Yerba Buena Cove fill (`fill_zones.csv` `sf_ybc_*`, Telegraph Hill east, SoMa marsh, …; 627 outlines): not
  before the band's `year_start`.
* Inside the 1849 extent ring: early in the window; inside the 1852 ring only: middle; outside the 1852 ring
  (scattered building, 1,159 outlines): late.
* 1887 outlines not on the 1852 chart of a covered block: 1852.3-1887; elsewhere between the snapshots whose rings
  first contain them.

End:
* 1851 map: 88 destroyed on 4 May 1851 (exact); survivors: still on the 1852 chart (its masses cover >= 40 % of
  them) -> they keep their own outline and are cut out of the 1852 mass (12 masses cut); not on it and inside the
  22 June fire -> burned 22 June 1851 (2: El Dorado, Dewitt & Harrison); otherwise gone 1851-52.
* 1852 chart in a block of the 1887 Sanborn: same structure only if one 1887 outline has about the same shape
  (IoU >= 0.45; 3 cases), else gone 1852-1887 (55).
* Otherwise: the 1906 fire (2,553 of 2,696 are in the burned area) or today's building on the spot (422) is the
  upper bound, `end_rule = successor`.

Storeys are not on the 1851/1852 maps: defaults by material / size from `sf_extent_README.md` (gold-rush frame
1-2, 40 % two-storey; iron stores 1 if < 90 m2; brick 2), marked `default (rule: …)`. 1887: OHM
`building:levels` where tagged (11), else by OHM building type (house 2, apartments / hotel 3, commercial 2-3).

## Integration (`ohm_import.apply_goldrush`)

`apply_sanborn` cannot use these files as they are: it would (a) drop *every* generated building inside the
coverage that ends after 1851 — i.e. the whole 1852-1906 history of these 400 ha — and (b) end an 1852 building
that has no later map at today's building (1907+) instead of the 1906 fire. So leave the area out of
`apply_sanborn` and call the tool's function after it, in `sf_predecessors.main`:

```python
from region_predecessors import REGION_SANBORN
pred = apply_sanborn(pred, b, fire, areas,
                     include=lambda a: not a.startswith(REGION_SANBORN) and not a.startswith("sf_goldrush"))
from ohm_import import apply_goldrush
pred = apply_goldrush(pred, b)  # b = today's sf_buildings in UTM, as main() already has it
```

It adds the traced buildings (source `ohm_sf_goldrush`, `year_confidence = estimated`) and, inside the coverage:
drops a lot's first generated building where a traced one stands; moves other generated buildings that started
before the 1852 survey to 1852.3-1856.5 (the chart shows the lot empty); drops all generated buildings after 1852
in the 1887 blocks; gives documented `early_sf` / `notable_pre1906` buildings the traced outline (their dates
win); ends a `successor` building when the next building on its spot starts (mostly the procedural 1850s brick
rebuild downtown). Dry run on the current `data/interim/sf_predecessors.parquet`: 2,689 traced buildings added,
1,905 predecessors replaced (15 documented ones take a traced outline), 801 generated buildings moved after the
chart, 1,086 traced buildings end at a later building; standing traced buildings 1850: 412, 1852: 1,779,
1853: 2,228, 1860: 1,412, 1880: 1,438, 1906 (before the fire): 1,391.

Also: `sf_export.py`'s land check moves non-`exact` buildings that predate the terrain's land year. 97 buildings
of the 1852 chart stand where the terrain is still water then (fill bands `sf_ybc_3` 28, `sf_ybc_4` 23,
`sf_ybc_5` 17, SoMa marsh 7, …) — pile-supported buildings over the cove, or bands dated too late. Add
`"ohm_sf_goldrush"` to the `documented` exemption there (as for wharves and storeships), and consider moving the
`sf_ybc_3` / `sf_ybc_4` band starts earlier (the chart shows buildings to Front / Davis St in April 1852).

## Overlap with other SF areas

288 outlines of the 1852 chart lie in `soma_industrial`'s coverage, 16 in `north_waterfront`'s, 12 in
`mission_bay`'s, and 10 of the 1887 Sanborn in `north_waterfront`'s. No duplication: those areas' maps are of
1913-1950 and every gold-rush / 1887 outline there ends by the 1906 fire (or at the later building). Finding while
checking: `apply_sanborn` starts a building first seen on a 1913 map inside the 1906 burned area at the median of
the generated buildings around it (often 1860s-1890s), i.e. before the fire; such starts could be clamped to
>= 1906.3.

## Limits

* The 1852 chart draws contiguous fronts as one black mass (several buildings, one outline: up to ~6,500 m2);
  storeys are defaults. OHM's tracing is by eye over a georeferenced scan: a few metres of offset; the 1851 map's
  outlines are offset up to ~10-30 m from the 1852 ones in places.
* The June 1851 rectangle overstates the burned area (six of its blocks only partly burned).
* Fires of 24 Dec 1849, 4 May 1850, 14 June 1850 and 17 Sept 1850 are not used (no outlines here).
* The 1887 tracing covers whole blocks of Chinatown / downtown only; its start years are spread uniformly over
  1852-1887 where the 1852 chart shows the lot empty.
