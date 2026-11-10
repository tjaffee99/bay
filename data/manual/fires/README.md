# Fires that destroyed buildings (ten counties)

Built by `pipeline/fires.py` (`download` → `data/raw/fires/`, `build` → this folder). The two
building stages call it (`fires.rebuild_years` in `region_buildings.assign_years`,
`fires.add_predecessors` in `region_predecessors`); both do nothing if this folder is missing.

## Files

| file | what | made by |
|---|---|---|
| `perimeters.geojson` | 441 fire perimeters 1923–2025 touching the map: every fire ≥ 300 acres, and smaller ones with destroyed structures. `fire_id`, `name`, `year` (decimal year the fire burned; `date_estimated` = no alarm date on record, year + 0.7), `alarm_date`, `cont_date`, `acres` (FRAP GIS acres of the whole fire, also where the outline is clipped to the map), `destroyed` (DINS structures in the ten counties), `source`. Simplified to 12 / 25 / 45 m by size. | `build` |
| `severity_high.geojson` | MTBS class 4 (high severity) inside 55 perimeters of 1985–2020 (fires ≥ 1,000 acres): one MultiPolygon per fire, patches and holes ≥ 4 ha, 45 m tolerance; `high_ha`, `burnt_ha` (classes 2–4) | `build` |
| `destroyed_structures.csv` | 12,934 structures CAL FIRE inspected as "Destroyed (>50%)" in the ten counties, 2015–2025: `id` (`dins` + OBJECTID), `fire_id` (the perimeter of its year that holds it), `incident`, `date` (decimal year it burned), `lon`, `lat`, `structure_type`, `category`, `units`, `year_built` (parcel year, kept only if ≤ the fire year; 42 % have one), `apn`, `county`, `community`, `damage` | `build` |
| `rebuild_permits.csv` | 1,765 completed dwelling rebuild permits: Sonoma County (unincorporated; `year` = issue date + 1, `issued+1`, estimated — no final date is published) and Santa Cruz County (`year` = date the permit was closed, `completed`) | `build` |
| `fire_dates.csv` | hand-researched: display name and the day the structures burned where it differs from the alarm date (a lightning complex starts days before its run into the towns), one source per row | by hand |
| `clearances.csv` | older fires without structure data, in exactly the columns of `data/manual/redevelopment_areas.csv` (the lead appends them there). `fires.clearance_predecessors` reads this file directly. | by hand |

## Sources

| source | URL | licence | used for |
|---|---|---|---|
| CAL FIRE Damage Inspection (DINS), "POSTFIRE_MASTER_DATA_SHARE" | https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/arcgis/rest/services/POSTFIRE_MASTER_DATA_SHARE/FeatureServer/0 (data.ca.gov: "CAL FIRE Damage Inspection (DINS) Data") | public state data; no licence text on the service — check the data.ca.gov page before release | destroyed structures |
| CAL FIRE FRAP "California Fire Perimeters (all)" | https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/arcgis/rest/services/California_Historic_Fire_Perimeters/FeatureServer/0 | public domain (FRAP) | perimeters, the Tunnel fire ring |
| MTBS thematic burn severity mosaics (USGS / USDA Forest Service) | https://imagery.geoplatform.gov/iipp/rest/services/Fire_Aviation/USFS_EDW_MTBS_CONUS/ImageServer | public domain | high-severity patches |
| Permit Sonoma "Wildfire Rebuild Permits" (public view) | https://services1.arcgis.com/P5Mv5GY5S66M8Z1Q/arcgis/rest/services/Wildfire_Rebuild_Permits_Public_View_Layer/FeatureServer/0 | public county service, no licence text | which burned parcels were rebuilt |
| Santa Cruz County "Recovery Permit Center" (CZU) | https://sccgis.santacruzcountyca.gov/server/rest/services/czucleanup/MapServer/5 | public county service, no licence text | which CZU parcels were rebuilt, and when |

FRAP has no perimeter before 1923 inside the map and none for small urban fires. MTBS starts in 1984.

## Method (buildings)

The map shows a building iff `start_year <= year < end_year`. The rolls carry the rebuild year,
so burned neighbourhoods were empty before the fire and nothing burned.

1. **Match.** Each destroyed structure takes the footprint standing there today: the one its
   point lies in, else the nearest within 10 m. A house (not an outbuilding) still unmatched takes
   the nearest unclaimed footprint within 40 m whose recorded year is after the fire (inspectors
   often stood on the driveway). One structure speaks for a footprint (house before shed).
2. **Is the footprint a rebuild?** Best evidence first:
   * `rebuilt` — its recorded year is after the fire: unchanged.
   * `rebuilt_permit` — a completed rebuild permit on the parcel (APN): starts at the permit's year.
   * `rebuilt_est` — the outline comes from a source that post-dates the fire: starts at the fire
     date + a lag drawn from that fire's measured distribution (below), `estimated`.
   * `gone` — none of these: the outline is the building that burned and nothing shows it was
     rebuilt. The footprint **ends at the fire date** and keeps its own year.
   * (`dup`: a second structure on an already matched footprint; `none`: no footprint today.)
3. **What stood before** (`year_confidence = procedural`, id `fire:<dins id>`, source `fire_dins`,
   end = the fire date exactly): on the rebuild's own outline; with no footprint today, a plain
   rectangle of the DINS structure type (table `PLAIN` in `fires.py`; in a house lot ≤ 2,500 m² it
   sits across the middle of the lot, else at the point, turned like the nearest building; never
   on a building that stood through the fire). Vehicles ("Motor Home") and "Infrastructure" are not
   drawn. Start year: DINS parcel year > the roll's pre-fire year > the vendor copy's pre-fire year
   > median of the 12 nearest recorded pre-fire years within 300 m > HISDAC first built-up year >
   the fire's median DINS year. Storeys from the DINS type (single / multi story).
   A completed permit with no outline in today's data returns on the same plain rectangle from the
   permit's year (`fire:<id>:rebuild`).
4. **Older fires** (`clearances.csv`): inside the outline, a building dated in the 15 years after
   the fire replaced one that burned; a predecessor stands on its outline from the median recorded
   pre-fire year of the 12 nearest survivors (± 3 years) until the fire (`fire_procedural`).

### Is it a rebuild? — why the roll year alone is not enough

Measured on the matched footprints (simplified year assignment, 2026-11):

* Sonoma and Solano rolls record the rebuild year. Napa's keeps the old year (7 of 1,370 matched
  footprints dated after their fire); Santa Cruz has only a c. 2020 vendor copy (0 of 755).
* **County-contributed outlines (Esri Community Maps, Napa) post-date the 2020 fires**: around the
  Glass Fire in Napa they cover 587 undamaged inspected structures but 21 destroyed ones; the
  destroyed ones are Microsoft ML outlines instead (444). So an Esri outline on a destroyed point
  is a rebuild, a Microsoft one there is the burned building.
* **OpenStreetMap outlines edited after a fire are not evidence**: around the Kincade Fire 93 % of
  destroyed houses have an OSM outline, 17 % of undamaged ones — mappers drew the burned buildings.
* So OSM / Microsoft outlines count as rebuilds only for a fire where at least half of them
  (n ≥ 20) are recorded rebuilds: Tubbs (OSM 92 %, Microsoft 93 %), Nuns (53 %, 73 %). Not for
  Atlas, Kincade, Glass, LNU, CZU, SCU (0–29 %).

`FIRE_UNCONFIRMED=rebuild` in the environment turns every `gone` into `rebuilt_est` (the simpler
rule: any footprint on a destroyed point is a rebuild).

### Counts per fire (all structures; simplified year assignment — the stage will differ slightly)

| fire | destroyed | rebuilt (recorded / permit / estimated) | footprint ends at the fire | no footprint today (plain outline) | second point on a footprint |
|---|---|---|---|---|---|
| Tubbs 2017 | 5,656 | 2,875 / 20 / 263 | 0 | 2,134 | 364 |
| Glass 2020 | 1,528 | 126 / 13 / 40 | 760 | 398 | 191 |
| CZU 2020 | 1,490 | 0 / 114 / 0 | 593 | 724 | 59 |
| Nuns 2017 | 1,324 | 214 / 5 / 149 | 0 | 903 | 53 |
| LNU Hennessey 2020 | 1,157 | 59 / 0 / 26 | 686 | 310 | 76 |
| Atlas 2017 | 787 | 8 / 0 / 164 | 100 | 480 | 35 |
| Kincade 2019 | 372 | 82 / 12 / 0 | 229 | 35 | 14 |
| LNU Walbridge 2020 | 293 | 37 / 2 / 0 | 151 | 79 | 24 |
| SCU 2020 | 177 | 3 / 0 / 0 | 96 | 73 | 5 |
| 19 smaller fires | 150 | 11 / 0 / 3 | 38 | 94 | 4 |
| **all** | **12,934** | **3,415 / 166 / 645** | **2,653** | **5,230** | **825** |

Another 462 houses with a completed permit but no outline today return on their plain outline.
Predecessors drawn: 4,226 on the rebuild's outline + 5,004 plain outlines (125 skipped as
overlapping, 101 vehicles / infrastructure).

### Rebuild lag (recorded rebuilds: roll year + 0.5 − fire date; years)

| fire | n | 10 % | 25 % | median | 75 % | 90 % |
|---|---|---|---|---|---|---|
| Tubbs 2017 | 2,875 | 0.7 | 1.7 | 1.7 | 2.7 | 2.7 |
| Nuns 2017 | 214 | 1.7 | 2.7 | 2.7 | 3.7 | 3.7 |
| Kincade 2019 | 82 | 0.7 | 0.9 | 2.7 | 3.7 | 4.7 |
| Glass 2020 | 126 | 1.8 | 2.8 | 2.8 | 3.8 | 4.8 |
| LNU Hennessey 2020 | 59 | 1.9 | 1.9 | 1.9 | 2.9 | 3.9 |
| LNU Walbridge 2020 | 37 | 1.9 | 2.9 | 2.9 | 3.9 | 4.9 |

Fires with fewer than 30 recorded rebuilds use the pooled distribution. Santa Cruz permits close
2022–2026 (median 2024.3: 3.7 years after the fire).

## Tests (no stage needed)

`python fires.py test coffey|fountaingrove|boulder|bonnydoon|oakland|all [out_dir]`

| box | destroyed | standing just before → just after the fire | today |
|---|---|---|---|
| Coffey Park (Tubbs, 2017.77) | 1,430 | 2,745 → 1,409 | 2,770 |
| Boulder Creek (CZU, 2020.63) | 666 | 1,781 → 1,158 | 1,210 |
| Oakland hills (Tunnel, 1991.80) | 2,409 rebuilds inside the perimeter, 2,348 predecessors | 23,499 → 21,151 | 24,501 |

## Known limits

* DINS starts in 2013; its points are where the inspector stood, not always on the building.
* A house rebuilt in Napa County or after the CZU fire without a county-contributed outline or a
  closed permit is shown as not rebuilt (`gone`); a burned outbuilding that was put up again too.
* Plain outlines are not surveyed shapes. Pre-fire outlines exist (Microsoft 2018 footprints, 2016
  NAIP) and would replace them; not done.
* The Sonoma permit year is the issue date + 1 (no final date published).
* Tunnel fire: the 61 rebuilds without three dated survivors within 400 m get no predecessor; a
  house built 1992–2006 on a lot that was empty in 1991 gets one it should not have.
* Not entered, for lack of a citable outline or of agreeing sources: Santa Rosa 1906 (the Sanborn
  1904 / 1908 pair carries it), Santa Cruz and Watsonville 1989 (counts of demolished buildings
  differ between sources), Santa Cruz 1894, Hanly 1964 / Lexington 1985 / Mount Vision 1995
  (perimeters are here; their burned houses are scattered and not mapped).
