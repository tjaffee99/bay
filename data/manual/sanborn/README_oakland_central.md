# Sanborn tracing: central Oakland east of Broadway (Lakeside, Uptown, the Gold Coast, Adams Point, Eastlake)

Real building footprints of central Oakland **east of Broadway** — the Victorian houses, flats, churches, livery stables
and early apartment and store blocks between Broadway and Lake Merritt that the 1920s–60s apartments, offices, garages
and parking lots replaced (today's data shows only those, so the generated fabric left these blocks nearly empty in
1910). Traced from the Library of Congress scans of the Sanborn Map Co. *Insurance Maps of Oakland, California*,
**volume 2** (east of Broadway; public domain: "Library of Congress, Geography and Map Division, Sanborn Maps
Collection"), two editions of the same plates: **1911 vol. 2** (start bound) and the **1911 – Nov 1950 corrected vol. 2**
(end bound). Method, schema and confidence rules are those of West Oakland / downtown (`README_oakland.md`); the tool is
`pipeline/sanborn_trace_oakland_central.py`, which only configures `pipeline/sanborn_trace_eastbay.py` (through
`pipeline/sanborn_trace_eastbay_cities.py`). Control: `control/oakland_central/`.

West of Broadway (vol. 1), the freeway corridors (SR-24, I-580, I-980) and their area names `oakland_sr24`,
`oakland_i580`, `oakland_i980n` belong to `README_oakland.md` / `control/oakland/`.

## Files

| file | content |
|---|---|
| `oakland_lakeside_1911.geojson`, `oakland_lakeside_1950.geojson` | Broadway → Lake Merritt, 9th / 10th St → 20th St: Broadway – Harrison St 10th → 20th St (sheets 151–155: the Oakland Bank of Savings, the Union Savings Bank, the Macdonough Theatre, the SP depot block at 13th / Franklin, the 1st Presbyterian Church, the Liberty Theatre, City Hall Annex), Harrison – Madison St 9th → 19th St (162–166: Lincoln School and Square, Hotel Oakland, the Peralta Apartments, the Masonic Cathedral, the Gold Coast houses on Harrison / Alice / Jackson), Madison → Fallon / the lake 9th → 14th St and north of 14th (167, 168: Polytechnic College, the Oakland Public Museum in the Camron-Stanford house, the high-pressure pumping station) |
| `oakland_adams_point_1911.geojson`, `oakland_adams_point_1950.geojson` | north of 20th St: Broadway – Webster 20th → 24th St (145: the Broadway store rows, Franklin / Webster houses), Webster – Harrison / the lake 20th → 22nd St (156: the College of the Holy Names and its chapel, the Little Sisters of the Poor home, the Laguna Vista Apartments — today Kaiser Center), Webster → Harrison 22nd → 24th St with Valdez / Waverly (157: St. Paul's, the 1st Christian Church, Oakland Maternity Hospital), Webster → Valdez 24th → 28th St (137: Providence Hospital, the Piedmont livery, the Merchants Express sheds — today Broadway's auto row), Adams Point: Lee / Perkins St Vernon → Palm Ave (141), Staten → Perry Pl Palm → Van Buren Ave (135), Park View Ter → Perkins St Van Buren → Grand Ave (144), Perkins → Bellevue Ave Van Buren → the lake (142) |
| `oakland_eastlake_1911.geojson`, `oakland_eastlake_1950.geojson` | east of the lake (Clinton / Brooklyn, today Eastlake): the Lake Shore Blvd blocks and 1st → 7th Ave, E 11th / E 12th St → E 15th St (sheets 199, 200, 201: Clinton Square), 3rd → 6th Ave E 15th → E 18th St (186), 2nd → 3rd Ave E 15th → E 18th St (185: the Oakland Traction Co. car barn) |
| `oakland_<area>_coverage.geojson` | one polygon per map year (`map_year` = the file year): the fitted block zones + 12 m (half the streets). Inside it an empty spot was empty on that map |
| `control/oakland_central/<key>.json` | per sheet: blocks (`streets` N/S/W/E, `px4_est` estimates, refined `px4`, `edge_q`, corners used with their control type), `with` (blocks fitted together), `skip`, `refine_R`, `residential`, `notes`; registered 1950 sheets: the SIFT registration (`registered_to`, `T`) |
| `control/oakland_central/areas.json` | which sheets make up each area and map year |
| `control/oakland_central/storeys.json` | storeys read off the sheets by eye on the 50 % scans (the numeral at a building's corner; `2½` = 2.5; a footprint whose parts carry different marks is left to the default rule): `{key: [[x, y, stories], ...]}` (pixel on the 25 % scan inside the building) |
| `control/oakland_central/labels.json` | names / uses read off the sheets by pixel position (banks, hotels, theatres, apartment houses, churches, schools, halls, liveries) |

Keys are `<LOC item suffix>_<sheet>`: `006_0152` = sanborn00727_006 (1911 vol. 2) sheet 152, `016_0152` =
sanborn00727_016 (1911 – Nov 1950 vol. 2) sheet 152.

### Feature properties

As `README_oakland.md` (`id`, `map_year`, `volume`, `volume_label`, `loc_url`, `sheet`, `sheet_no`, `iiif`, `stories`,
`stories_source`, `material`, `use`, `use_source`, `name`, `sanborn_colour`, `confidence`, `georef`, `georef_rms_m`,
`extraction`, `area_m2`, `modern_overlap`). Differences:

| property | meaning here |
|---|---|
| `map_year` | 1911 (1911 vol. 2) or 1950 (1911 – Nov 1950 vol. 2: the 1911 plates with paste-over corrections, and re-drawn plates for sheets 152 (May 1944), 153 (May 1944) and 154 (new sheet, Jan 1925)) |
| `stories` | read off the sheet where `stories_source = map (read from the sheet)` (`storeys.json`: 1911 buildings of ≥ 300 m² frame or ≥ 150 m² masonry in Lakeside, ≥ 250 m² frame in Adams Point; 143 reads); `map (read from the 1911 sheet: same building)` on the 1950 map for a building with the same outline (IoU ≥ 0.5) and colour, names likewise (`apply_sanborn` emits such a building with its 1950 row); else the Oakland default rule (frame < 30 m² shed 1; frame ≤ 300 m² dwelling 2 on residential sheets, store 2 on the commercial sheets; frame ≥ 300 m² warehouse 1; brick / stone / concrete 2) |
| `use` | the default rule; `default (rule: commercial street frontage)` = store within 40 m of Broadway, 30 m of Grand Ave; `default (rule: 3+ storey residential building)` = flats where a dwelling was read at 3+ storeys |
| `extraction` | `colour class`, `region` (1950: regions enclosed by drawn lines, classed by median colour), or `colour class (light outline)`: a large solid fill (≥ 100 m²) whose outline is thin or broken by lettering (45–70 % dark), which `extract` rejects |
| `residential` sheets | 153–155, 162–168 and all Adams Point sheets (1911 and their registered 1950 states); commercial: 151, 152 and the re-drawn 1950 sheets 152–154 |

## Counts

| file | features | confidence high / medium / low | area (1000 m²) | modern_overlap ≥ 0.5 | materials | storeys read |
|---|---|---|---|---|---|---|
| oakland_lakeside_1911 | 1295 | 997 / 298 / 0 | 194.4 | 958 | frame 1194, brick 72, concrete 22, stone 7 | 108 |
| oakland_lakeside_1950 | 952 | 580 / 368 / 4 | 247.9 | 739 | frame 410, concrete 321, brick 207, iron 14 | 43 (carried over) |
| oakland_adams_point_1911 | 842 | 197 / 457 / 188 | 83.5 | 559 | frame 838, brick 4 | 30 |
| oakland_adams_point_1950 | 1224 | 375 / 675 / 174 | 168.0 | 846 | frame 990, concrete 129, brick 102, iron 3 | 14 (carried over) |
| oakland_eastlake_1911 | 795 | 733 / 62 / 0 | 61.2 | 477 | frame 791, brick 3, concrete 1 | 0 |
| oakland_eastlake_1950 | 998 | 905 / 93 / 0 | 101.6 | 608 | frame 890, brick 72, concrete 33, iron 3 | 0 |

A "feature" is one coloured fill, split along the drawn partition walls (porches, bay windows and rear additions drawn
with a line become their own small features: 386 / 164 "sheds" < 30 m²). `modern_overlap` ≥ 0.5 marks a building that
still stands *or* a later, larger building over the same spot (most apartment blocks here cover the whole lot of the
house they replaced); `apply_sanborn` leaves to the modern data only the footprints that match a modern building
(IoU ≥ 0.5) standing by the map year.

## Sources

Sanborn Map Company, *Insurance Maps of Oakland, California*, Library of Congress Geography and Map Division, Sanborn
Maps Collection (public domain); IIIF images at 25 % (≈ 1670 × 1950 px, 0.20 m/px at 50 ft = 1 in):

| edition | LOC item | sheets used |
|---|---|---|
| 1911 vol. 2 | https://www.loc.gov/item/sanborn00727_006/ | Lakeside 151–155, 162–168; Adams Point 135, 137, 141, 142, 144, 145, 156, 157; Eastlake 185, 186, 199, 200, 201 |
| 1911 – Nov 1950 vol. 2 | https://www.loc.gov/item/sanborn00727_016/ | the same sheet numbers |

Volume 2 covers Oakland east of Broadway (key map sheet `0000`): Chinatown, Lakeside / the Gold Coast, Adams Point,
Eastlake (Brooklyn), the East Oakland waterfront. Item JSON in `data/raw/sanborn_loc_oakland/` (shared with
`sanborn_trace_eastbay.py`).

Control geometry (as `README_oakland.md`):
* **Street centrelines**: Overture Maps transportation segments, release 2026-10-21.0, `roads_region.parquet` +
  `roads_local.parquet` read within (-122.285, 37.785, -122.225, 37.835) (ODbL).
* **Property lines**: Alameda County parcels (`data/raw/region_years/alameda_county_2021`, public copy, see
  `data/research/region_buildings.md`), dissolved into blocks.

## Method

As `README_oakland.md` (blocks named by their four streets and estimated by eye on a pixel grid, `refine` snaps each
side onto the drawn block line within ±22–26 px, property corners from today's parcel blocks, similarity fits per block
or per group of blocks, outliers > 3 m and > 3 × the median dropped; colour segmentation with partition walls). New here:

1. **Two-part sheets.** Sheets 151, 152, 162, 163 (and the re-drawn 1950 sheets 152–154) show two non-adjacent strips
   of blocks (e.g. 12th–13th St and 13th–14th St, the middle street drawn twice); each strip is one fit group (`with`).
2. **Re-drawn 1950 plates.** Sheets 152 and 153 (re-drawn May 1944) and 154 (new sheet Jan 1925) cannot be registered
   onto the 1911 plates (SIFT: 26–83 inliers, no consistent similarity); they have their own control. All other 1950
   sheets are the 1911 plates with paste-over slips, registered by SIFT + RANSAC (577–1,954 inliers, 1.4–1.8 px).
3. **Streets that changed.** In 1911 15th St and 17th St did not cross the blocks east of Franklin St (the
   Franklin – Harrison blocks ran 14th → 19th St); 15th St (80 ft) was cut through by 1944, 17th St (60 ft) by 1925.
   The 1911 sheets' "18th St" (Harrison – Alice) and "Lake St" (Jackson – Madison) are today's 17th St east of Harrison
   (220 m north of 15th St on Jackson / Madison, where 17th St bends north), and 20th St east of Broadway is today's
   Thomas L. Berkley Way; 16th / 18th St do not exist east of Broadway. Corners on streets realigned since (20th St
   at Broadway, 17th St at Harrison, the 17th St corners of block 2016) are 5–17 m off today's property lines and were
   dropped as outliers; Oak – Fallon 10th – 12th St is the Oakland Museum superblock (no corners).
4. **14th St.** On sheet 164 the blocks east of 14th St are fitted on their own (their 14th St corners are 3.3 m off a
   fit to the west side: 14th St is drawn ~3 m narrower than today's right of way).
5. **Adams Point.** The plates north of 22nd St are drawn at other rotations (157 / 156: +78°, 137: −12°, 135: +19°,
   142: −4.5°, 144: −19°, 141: +36°) and with oblique / curved streets; block corners there were read by eye on 3×
   zooms of the scan (`no_refine`). Today's names: 20th St = Thomas L. Berkley Way, W. Grand Ave (Blvd Ter.) = Grand
   Ave, Bay Pl (west of Harrison) = 26th St, Chetwood St (Adams) = Adams St, Lenox Ave (Miramar), Park View Ter (Edson).
   Sheet 137 rests on its 24th St corners only (Bay Pl / 26th St and 28th St were realigned, 4–14 m off): plate-scale
   prior, **confidence capped at `low`**; 156 (College of the Holy Names, today the Kaiser Center superblock) has 4
   corners at 2.5–4.6 m → `low`; 145's upper blocks (Franklin / Webster oblique, 20th St realigned at Franklin) 2.5 m
   RMS → `medium`.
6. **Eastlake.** The Eastlake grid is at ~45° to north (avenues run NE, E-streets NW), so the tool's "more north-south
   street" is the E-street: those control files name the block sides in the tool's frame (`N` = the avenue on the sheet's
   left, `E` = the E-street at the top; written from sheet-frame specs by a 90° relabelling, noted in each file). Today's
   names: E 14th St = International Blvd. E 11th St no longer crosses 3rd – 7th Ave (corners skipped); on 186 the E 16th
   / E 17th St corners do not match today's parcels (dropped as outliers), the fit rests on E 15th and E 18th St (8
   corners, 0.51 m); 185 rests on two E 15th St corners (exact fit, plate scale 0.1998 → `medium`). The Lake Shore Blvd
   blocks of 199 (401, 393: houses and flats facing the lake, today 1920s–60s apartments) have no corners of their own
   and are placed by the group fit 60–120 m away (block `confidence_cap` = `medium`).
7. **Light outlines.** `extract_large` adds big solid fills whose outline the tool's 70 % dark-outline test rejects
   (thin outlines broken by lettering on the 1944–50 slips).

## Georeferencing per sheet

RMS / max per fit (block fits and group fits, the largest first), scale (m/px of the 25 % image) and rotation (image
x-axis vs east: the Broadway grid is drawn north-to-the-right at +64°, sheets 167 / 168 north-up at −26°).

| sheet | ed. | fits over block zones | control corners | RMS / max (m), per fit | scale (m/px), rotation |
|---|---|---|---|---|---|
| 006_0151 | 1911 | 6 fits over 6 zones | 20 | 0.26/0.49; 0.26/0.49; 0.19/0.27; 0.22/0.27 ... | 0.2018, 64.3° |
| 006_0152 | 1911 | 6 / 6 | 22 | 0.37/0.57; 0.18/0.22; 0.35/0.38; 0.19/0.24 ... | 0.2010–0.2021, 63.9–64.2° |
| 006_0153 | 1911 | 3 / 4 | 8 | 0.32/0.62 (group) | 0.2024, 64.2° |
| 006_0154 | 1911 | 3 / 4 | 8 | 1.41/2.54 (group) | 0.2037, 64.3° |
| 006_0155 | 1911 | 3 / 3 | 6 | 0.61/1.05 (group: 19th St + Webster) | 0.2037, 64.0° |
| 006_0162 | 1911 | 6 / 6 | 24 | 0.25/0.32; 0.22/0.26; 0.31/0.42; 0.38/0.45 ... | 0.1991–0.2027, 63.9–64.2° |
| 006_0163 | 1911 | 6 / 6 | 24 | 0.48/0.66; 0.24/0.34; 0.67/0.89; 0.28/0.38 ... | 0.2010–0.2026, 64.0–64.4° |
| 006_0164 | 1911 | 4 / 6 | 18 | 0.44/0.76; 0.43/0.53; 0.39/0.50; east group 1.72/2.69 | 0.2010–0.2014, 63.9–64.2° |
| 006_0165 | 1911 | 2 / 3 | 5 | 0.44/0.55 (2001); 1.81/2.68 (group) | 0.2001, 64.6°; 0.1990, 65.2° |
| 006_0166 | 1911 | 1 / 4 | 6 | 0.31/0.44 (group: 19th St + Jackson × 17th) | 0.2009, 63.8° |
| 006_0167 | 1911 | 2 / 4 | 8 | 0.27/0.38 (903); 1.63/2.46 (group) | 0.2010, −26.5°; 0.2033, −26.4° |
| 006_0168 | 1911 | 3 / 8 | 23 | 0.16/0.20 (168); 0.24 (125); 0.14 (136); 0.53/1.02 (group) | 0.2006–0.2017, −25.6 – −26.2° |
| 016_0152 | 1950 (re-drawn) | 6 / 6 | 22 | 0.95/1.87; 0.59/0.77; 0.63/0.85; 0.45/0.50 ... | 0.2014–0.2045, 64.0–64.5° |
| 016_0153 | 1950 (re-drawn) | 4 / 6 | 18 | 0.64/0.84; 0.30/0.41; 0.40; 0.50/0.66 (right strip, 15th St only) | 0.2031–0.2055, 64.3–64.7° |
| 016_0154 | 1950 (new sheet) | 3 / 6 | 13 | 0.87/1.27 (left strip, 17th St only); 0.25/0.33; 0.99/1.77 | 0.2006–0.2020, 64.4–64.6° |
| 006_0145 | 1911 | 2 / 4 | 11 | 2.48/4.53 (upper strip, 20th – 22nd St); 1.04/1.26 (lower strip) | 0.1970, 63.9°; 0.2007, 64.1° |
| 006_0156 | 1911 | 1 / 2 | 4 | 3.29/4.60 (group) → low | 0.1993, 77.5° |
| 006_0157 | 1911 | 4 / 5 | 13 | 1.38/2.28 (group); 1.17/1.63; 0.33/0.41 | 0.2022–0.2034, 78.6–78.9° |
| 006_0137 | 1911 | 1 / 4 | 3 (24th St only) | 3.40/4.70, cap low | 0.1999, −11.9° |
| 006_0135 | 1911 | 1 / 4 | 6 | 2.07/3.41 (group) | 0.2027, 19.2° |
| 006_0142 | 1911 | 1 / 6 | 9 | 1.45/2.81 (group) | 0.2035, −4.5° |
| 006_0144 | 1911 | 1 / 3 | 6 | 1.99/2.96 (group) | 0.2044, −18.7° |
| 006_0141 | 1911 | 1 / 5 | 4 | 2.28/3.13 (group) | 0.2050, 36.2° |
| 006_0185 | 1911 | 1 / 2 | 2 (E 15th St) | exact (2 corners) → medium | 0.1998, −47.9° |
| 006_0186 | 1911 | 1 / 9 | 8 (E 15th + E 18th St) | 0.51/1.01 (group) | 0.2004, −47.6° |
| 006_0199 | 1911 | 2 / 8 | 11 | 0.35 (402); 0.65/0.95 (group; Lake Shore blocks capped medium) | 0.2006–0.2008, −47.6 – −47.8° |
| 006_0200 | 1911 | 9 / 9 | 25 | 0.12–0.45, max 0.89 | 0.1992–0.2013, −47.9 – −48.0° |
| 006_0201 | 1911 | 9 / 9 | 25 | 0.11–0.69, max 2.54 | 0.1994–0.2010, −47.7 – −47.9° |

| 1950 sheet | registered onto | SIFT inliers | registration RMS |
|---|---|---|---|
| 016_0151 | 006_0151 | 1070 | 1.66 px = 0.33 m |
| 016_0155 | 006_0155 | 577 | 1.37 px = 0.28 m |
| 016_0162 | 006_0162 | 1505 | 1.84 px = 0.37 m |
| 016_0163 | 006_0163 | 1954 | 1.68 px = 0.34 m |
| 016_0164 | 006_0164 | 1882 | 1.49 px = 0.30 m |
| 016_0165 | 006_0165 | 793 | 1.53 px = 0.31 m |
| 016_0166 | 006_0166 | 770 | 1.36 px = 0.28 m |
| 016_0167 | 006_0167 | 981 | 1.57 px = 0.32 m |
| 016_0168 | 006_0168 | 1418 | 1.50 px = 0.31 m |
| 016_0145 | 006_0145 | 732 | 1.43 px = 0.26 m |
| 016_0156 | 006_0156 | 1492 | 1.49 px = 0.30 m |
| 016_0157 | 006_0157 | 809 | 1.76 px = 0.36 m |
| 016_0137 | 006_0137 | 456 | 1.43 px = 0.29 m |
| 016_0135 | 006_0135 | 1372 | 1.70 px = 0.35 m |
| 016_0142 | 006_0142 | 762 | 1.57 px = 0.32 m |
| 016_0144 | 006_0144 | 1530 | 1.57 px = 0.32 m |
| 016_0141 | 006_0141 | 1373 | 1.68 px = 0.35 m |
| 016_0185 | 006_0185 | 1469 | 1.47 px = 0.30 m |
| 016_0186 | 006_0186 | 868 | 1.42 px = 0.29 m |
| 016_0199 | 006_0199 | 991 | 1.58 px = 0.32 m |
| 016_0200 | 006_0200 | 957 | 1.53 px = 0.31 m |
| 016_0201 | 006_0201 | 897 | 1.68 px = 0.34 m |

Collinear control (all corners on one street: the right strip of 016_0153, the left strip of 016_0154, sheet 153's
long blocks) caps a footprint at `medium`.

## Coverage

* **oakland_lakeside**: Broadway → Harrison St, 10th St → 20th St (151–155); Harrison → Madison St, 9th → 19th St
  (162–166, upper part of 166: the Harrison – Jackson blocks 17th → 19th St, the Jackson – Madison block north of
  17th St and the lake-front estate block 911 north of 19th St); Madison → Oak St 13th → north of 14th St and Oak St →
  the lake (167); Madison → Fallon St, 9th → 13th St (168).
* **oakland_adams_point**: Broadway → Webster St 20th → 24th St (145; Franklin and Webster run oblique there);
  Webster → Harrison St / the lake 20th → 22nd St (156); Webster → Harrison St 22nd → 24th St (157: west of 23rd St the
  blocks run Webster → Harrison, east of it Webster / Valdez / Waverly); Webster → Valdez St / Glen Echo Creek 24th →
  28th St (137); Adams Point: Lee St / Perkins St, Vernon St → Palm Ave (141), Staten Ave → Perry Pl, Warwick / Palm →
  Van Buren Ave (135), Park View Ter → Perkins St, Van Buren → Grand Ave (144, lower part), Perkins St → Bellevue Ave,
  Van Buren Ave → Bellevue Ave at the lake (142).
* **Not covered** (vol. 2): 146–150 and 158–161 (Chinatown south of 10th St, the waterfront, the estuary), 169–174;
  138 (28th – 29th St, Grant School: SR-24 / I-580 corridor side), 139 (Piedmont Baths / Wheelman Athletic Club,
  Harrison – Oakland Ave), 140, 143 (Vernon – Montecito – Park View Ter: 3 corners only, 8–10 m off today's lines,
  Park View Ter realigned; not used), 134, 136 (Euclid / Grand Ave north arm), 129–133, the upper part of 144 (Staten /
  Palm / Perkins / Van Buren), the inset of sheet 166 (Madison / Oak / Lake St, blocks 907, 910); in Eastlake the
  Lake Shore / Athol Plaza blocks of 185 (425, 411), E 18th – E 22nd St (175–177, 187–188), 7th Ave and east (187,
  202–204), south of E 11th St (205–207: the estuary, East 7th St) and the Brooklyn / Clinton districts beyond.
* **oakland_eastlake**: Lake Shore Blvd → 2nd Ave, E 11th → E 15th St and 2nd → 3rd Ave E 15th → E 18th St (199, 185),
  2nd → 7th Ave E 11th / E 12th → E 15th St (200, 201), 3rd → 6th Ave E 15th → E 18th St (186).

## Reproduce

```
python pipeline/sanborn_trace_oakland_central.py all        # fetch + georef + extract + assemble (control files are final)
python pipeline/sanborn_trace_oakland_central.py assemble   # outputs only
python pipeline/sanborn_trace_oakland_central.py check      # validation + data/interim/sanborn_oakland_central/check_<area>.png
python pipeline/sanborn_trace_oakland_central.py register 016_0151 006_0151   # redo one SIFT registration
```
The control files hold the refined pixels (`norefine`), so a rerun reproduces the outputs.
