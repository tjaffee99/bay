# Military and industrial sites (`data/manual/industrial_sites/`)

From about 1880 to 1960 the Bay's shores filled with refineries, powder works, smelters, shipyards,
rail yards and depots, and the war added bases, magazines and ports; quarries and landfills ate into
the hills. Today's data knows these places only as they are now: refinery tank farms and Army
warehouses carry 1980s assessor (re-assessment) or imputed years, federal posts have no roll years at
all, quarry pits are bare rock "since the beginning of time", and the sites that are gone (shipyards,
powder works, the Oakland Army Base, the SP mole) are not there. This folder is the audit and the data
to fix that, from real maps wherever possible.

## Files

| file | what |
|---|---|
| `sites.geojson` | one or more Polygon parts per site and period (ground cover + map label) |
| `building_dates.csv` | per-site rules for today's footprints inside a site |
| `known_dates_industrial.csv` | per-footprint years, same columns as `data/tables/known_building_dates_region.csv` (researched buildings first, then footprints dated by the USGS editions) |
| `traced/permanente_*.geojson` | Permanente pit outlines extracted from the 1960 / 1968 / 1979 / 1991 sheets (`tools/tint.py`) |
| `traced/audit.csv` | per site: today's footprints, the live map's years, how many the maps draw, how many are corrected and by how much |
| `traced/audit_terrain.csv` | per part: share of terrain vertices WorldCover calls bare / built (what the c.1800 cover paints as rock) |
| `tools/` | `build.py` (everything from `industrial_def.py`), `editions.py`, `date_editions.py`, `footprints.py`, `tint.py`, `montage.py`, `audit_terrain.py` |

Rebuild: `cd data/manual/industrial_sites && ../../../.venv/bin/python -I tools/build.py` (edition
presence is cached in `data/interim/industrial_sites/`; `--redate` re-reads the maps; ~30 min cold, one
process under ~1.4 GB), then `python -I tools/audit_terrain.py`.

### `sites.geojson` properties
`site_id, part_id, name, kind` (refinery | quarry | landfill | military | shipyard | rail_yard | factory |
cannery | power_plant | cement | chemical | salt_works | port_terminal | other),
`cover` — what the ground looked like over `[year_start, year_end)`:
`industrial | quarry_pit | landfill | tank_farm | military | rail_yard | water`, plus **`open_works`**
(added: a fenced works or reservation that stayed mostly open ground — powder-works buffer land,
ammunition magazines, training areas, a tank hill: keep the natural / grass cover, show the label and the
buildings, don't pave it),
`year_start, year_end` (fractional; 9999 = still there), `name_label` (short map label), `confidence`
(`exact` = outline and dates from the sources; `estimated` = traced but a date or outline approximate),
`source_url`, `note` (incl. where the geometry comes from), `county`.

Parts overlap on purpose: growth stages of a quarry are separate, ever larger features with later
`year_start` (a consumer applies each from its year; the larger later stage contains the earlier one),
and a plant part can lie inside a reservation part. Where a site ends (`year_end` < 9999) the ground is
whatever came next (the terrain's own history, or another part).

### `building_dates.csv`
`site_id, ring_type, year, applies_to, max_year, evidence, source_url`
* `ring_type = site`: the union of the site's parts.
* `applies_to = all_pre`: no footprint inside can predate `year` (the site's founding): a live year
  earlier than that is a wrong roll / imputation (Lockheed's Sunnyvale campus at 1900, a Clayton quarry
  shed at 1890) and becomes `year`.
* `applies_to = named`: the site's footprints were checked against the USGS editions; use the rows of
  `known_dates_industrial.csv` (they already apply the founding-year floor).
* `applies_to = tanks`: round footprints (circularity > 0.85, > 40 m²) inside whose live year is in
  `(year, max_year]` take `year` (re-assessed tank farms where no edition could date them).
* `max_year` (extra column): upper bound of the re-assessment window for `tanks` (blank = none).

### `known_dates_industrial.csv`
`id, name, lat, lon, start_year, end_year, source_url, note, county` — the point lies inside today's
footprint (Overture region5 id in the note). `source_url` = the sheet that first draws the footprint.

## Method

**Outlines.** Today's outline of a site = OpenStreetMap `landuse=industrial / military / quarry /
landfill / railway` (Overture base `land_use`, 2026-10-21.0) where the site survives; for vanished
sites, the outline read on the 1946–1959 1:24k sheet in a local metre frame with a labelled grid
(vanished-sites renderer `vt.render_topo`: sheet registration + NADCON; +-40 m). Military posts without
an OSM outline (Marin forts, Hamilton) use the convex hull of their buildings (+35–50 m).

**Quarry growth** (`tools/tint.py`): each edition is resampled into the site frame and the pit is
extracted by colour — the unwooded quarry ground of the 1948–1968 sheets (`open`, seeded at the
"Quarry" label), the magenta photorevision overprint of the 1968–1980 sheets (`purple`), and the
red-brown disturbed-surface tint of the 1980s–90s sheets (`tint`) — closed, hole-filled and clipped
to the sheet's NAD27 quad (so neighbouring sheets are joined, not double-counted). A stage starts at the
midpoint between the photo year of the previous edition and its own.

**Dating today's footprints by edition** (`tools/date_editions.py`): for every USGS edition covering a
site (1:62,500 from the 1890s, every reprint separately; 1:24k from the 1940s with every photorevision),
the site is resampled at 2 m (1:24k) / 4 m (1:62,500); a footprint is *drawn* when the dark ink, opened by
~6 m (drops roads, rail, lettering), covers >= 30 % (1:62,500: 20 %) of it buffered by the registration
tolerance (6 m / 15 m), or — for round tanks — when its rim band carries ink (open tank circles) or it is
filled. The footprint's start = midpoint of the last edition not drawing it and the first edition drawing
it (and staying drawn on most later ones); reprints count as drawn by their imprint year but absent only
for their culture year; drawn on the first edition after the founding -> the founding year (if within
15 years) or the midpoint. A footprint whose live year is more than 2 years later than the edition that
first draws it, or earlier than the site's founding, gets a row in `known_dates_industrial.csv`.
Absence on a topo sheet is weak evidence (urban tint areas omit buildings), so undrawn footprints keep
their live year unless it predates the site.

<!-- AUDIT -->
