# Contact-era Native villages, c.1769–1810 (`villages.csv`)

Ohlone (Costanoan), Bay Miwok and Coast Miwok village sites around the core Bay in the
years of the Spanish entry, so that 1769 shows the people who lived here — and, since the
map grew to ten counties (2026-11), the Coast Miwok, Southern Pomo, Kashaya, Wappo, Patwin,
Delta and Awaswas / Mutsun-area villages of Sonoma, Napa, Solano, east Contra Costa, Santa
Cruz and south Santa Clara (section "The ten-county extension" below). This file is
a supplement to `data/tables/early_region.csv` and `early_sf.csv`. It has the same
columns, one row per village, with `count` tule houses scattered over `spread_m`.

- **75 rows, 932 houses** (35 rows / 422 houses around the core Bay, 40 rows / 510 houses in the extension).
  - Sonoma: 24 rows, 249 houses.
  - Contra Costa: 13 rows, 230 houses.
  - Alameda: 11 rows, 108 houses.
  - Santa Clara: 9 rows, 128 houses.
  - Napa: 6 rows, 82 houses.
  - Santa Cruz: 4 rows, 49 houses.
  - Solano: 3 rows, 42 houses.
  - Marin: 3 rows, 28 houses.
  - San Mateo: 2 rows, 16 houses.
- **Combined total.** With the Native villages in `early_region.csv` and the 5 Yelamu villages in `early_sf.csv`, `ground_detail.village_labels()` now returns 105 labels inside the ten-county extent, 104 of them standing in 1769 (it was about 60 for the core). `bmw_marsh_creek_village` and `mw_utumia`, outside the old extent, are inside the new one and were corrected (below).
- **Confidence.** Every row is `confidence = low`. Positions are place-level, and house counts are estimates.

## Are there maps of where the villages were?

There are maps, but none of them plots village points everywhere. Everything below comes from public, published sources.

| Map | What it shows | Used here |
| --- | --- | --- |
| Milliken, *A Time of Little Choice* (1995), and Milliken, Shoup & Ortiz, *Ohlone/Costanoan Indians of the SF Peninsula and their Neighbors* (NPS 2009), Fig. 12 | Territories of the ~50 **local tribes** (multi-village groups of 50–500 people) at the Spanish entry. They are reconstructed from mission baptism, marriage and death registers. | Local-tribe names, territories, populations and the years their villages emptied. The 2009 report is the main source. |
| Milliken et al., *Contact-Period Native California Community Distribution Model* (CDM; Far Western for Caltrans, 2010) | GIS polygons of the same regions with populations. The GIS download is password-protected; Table B-1 is public on the wiki. | Population per region and mean baptism year. |
| Milliken, *Ethnohistory and Ethnogeography of the Coast Miwok and their Neighbors* (NPS 2009) | Coast Miwok regional communities and the few located villages (after Barrett 1908, Kelly 1978, Collier & Thalman 1991). | Marin rows and corrections. |
| Kroeber 1925 (*Handbook*, Costanoan map) and Levy 1978 (*Handbook of North American Indians* 8, Fig. 1) | Language areas and a handful of villages. These are superseded by Milliken. | Not used. Levy is not online. |
| Crespí's 1772 map and Font's 1776 map of the Bay | Expedition routes. Bolton's notes tie each camp to a modern place. | Route positions for the villages in the diaries. |
| N. C. Nelson, *Shellmounds of the San Francisco Bay Region* (1909) | About 425 shellmounds. Most were abandoned long before 1769, for example Emeryville, West Berkeley and Ellis Landing. | **Not used.** A mound proves a site, not a 1769 village. These are archaeological sites (see Sensitivity). |

The registers name hundreds of villages: Thenau / Genau, Ocquizara, Supichom, Chichintac, Molostach and others. Most of them cannot be located. **Only villages that a published source places** are in the file.

## Method

1. **Explorers' villages: the core of the file.** The diaries record villages with dates, sizes and creek crossings:
   - Crespí's diary of the Fages expedition (March–April 1772; in Palóu's *Historical Memoirs* ii).
   - Fages 1772 (in Brown 1994, quoted by Milliken 2008 and Arellano et al. 2014).
   - Palóu 1774.
   - Font's and Anza's diaries (March–April 1776; in Bolton, *Anza's California Expeditions* iii–iv).

   Each position comes from **Bolton's identification of the camp or creek**: Tormey, San Pablo Creek, Wildcat Creek, Stevens Creek, the Guadalupe at Agnews, Scott Creek, Grayson Creek / Pacheco, San Ramon, Pleasanton, the Sunol Valley. Where a diary gives only a stretch, the village is put on a creek mouth along that stretch and marked **ESTIMATED**. Examples are "five villages in three leagues" on the Fremont plain and "five large villages" on Carquinez Strait.
2. **Register and ethnohistory villages.** Some villages are placed by Milliken (or by King and Hylkema for Santa Clara) from the mission registers:
   - The main Chupcan town in Concord.
   - Huchiun-Aguasto at Crockett.
   - Carquin in the Martinez vicinity.
   - "Our Patron San Francisco" at the Guadalupe / Los Gatos Creek junction.
   - Sorontac at the head of San Francisquito Creek.
   - The Lamchin valley of West Union Creek.
   - The Coast Miwok villages located by Barrett and Kelly: Ewu, Shotomoko-cha and Etcakólum.
3. **Local-tribe placements.** Four rows have no published village site, only the tribe's area. Each one is marked "site ESTIMATED" with a precision of 3–4 km:
   - Saclan (Lafayette).
   - Jalquin (San Leandro Creek).
   - Santa Ysabel (east of Coyote Creek).
   - Tuibun (mouth of Alameda Creek).

   Their tribes held 250–400 people each, so leaving them out would empty a populated valley.
4. **House counts.** Counts use diary figures where there are any; otherwise they are CDM populations spread over the tribe's usual 3–5 villages:
   - Diary figures: "some four hundred" and "five hundred souls" at Tormey; "about a hundred" at Stevens Creek and at the Guadalupe; "perhaps over two hundred" near Pleasanton; "close to six houses of spherical shape" on the Fremont plain.
   - Conversion: about 6–8 people per house, as in `early_region`.
   - House shape: a 4 m domed tule house, 2.5 m high. Coast Miwok houses are 2.8 m.
5. **Years.**
   - `start_year = 1700`, before the map starts, as in `early_region`.
   - `end_year` (exclusive) is when the last residents were baptised or moved to a mission, per Milliken. Examples:
     - Huchiun villages empty by summer 1806.
     - Jalquin / Irgin: last baptisms June 1803.
     - Chupcan main town raided September 1804; its people fled across Suisun Bay.
     - Saclan defeated July 1797.
     - Carquin and Huchiun-Aguasto: last groups June 1809 – February 1810.
     - Tamien villages near Santa Clara: about 1795.
   - Villages were seasonal. Some were empty when the Spaniards passed, such as Wildcat Creek and Hayward in 1776, but they are drawn for the whole period.
6. **Dry-land check.**
   - Every scatter disk was tested against the terrain's c.1800 cover: `grid_region_b1800` codes 1–6 are wet, and so are WorldCover water and elevation ≤ 0.5 m.
   - Every row is inside the map extent (`pipeline/extent.py`).
   - Three rows were moved onto dry ground; each note says so: `ohl_causen_sunol` (61 m), `ohl_alson_coyote_creek` (1.1 km) and `mw_etcakolum` (0.7 km).

Each row's `shape_note` gives its local tribe, language, quotations, position precision, end-year basis and the cited pages. `source_url` points to the main source.

## Rows that duplicate or should correct existing ones

**Superseded by this file:**
- **`early_region.hch_aguasto_village`.** It was 40 houses placed by guess near Pinole Creek, ending in 1800. Drop it when merging.
  - The large village is `ohl_aguasto_tormey`. Bolton identifies the "400" or "500" village of 2 Apr 1776 at Tormey; it ends in 1809.5.
  - `ohl_huchiun_pinole_creek` is the "fair-sized village" at that spot.

**Suggested corrections to existing rows, from Milliken's Coast Miwok report (2009) and the NPS Ohlone report:**
- `mw_liwanelowa` (Liuaneglua, Sausalito): end 1817.95 → **1803.9**. 90 % of the Huimens were baptised by the end of 1803.
- `mw_awaniwi`: end 1818 → **1803.9**. "By the end of 1803 the Huimen, Guaulen, and Tamal Aguasto villages south of Miller Creek were empty." Awani-wi never appears as a home village in the registers; the mission site was called Nanaguani.
- `mw_bauli_n` (Guaulen, Bolinas): end 1820 → **1803.1**. Most Guaulens were baptised 15–29 Jan 1803.
- `mw_chokeche` (Omiomi, Novato): end 1820 → **1811.4**. The main group was baptised Dec 1810 – May 1811.
- `mw_puyuku`: Kelly puts Puyuku on Miller Creek; it is the "Piguucu" of 1798. End 1820 → **1808.6**, the last significant Miller Creek group.
- `mw_echatamal` (Nicasio): most Nicasio Tamals were baptised in 1808. The 1835 ex-neophyte rancho is a different, post-mission community. Consider ending at 1808.6 and adding a separate 1835– row.
- `tam_socoisuka`: King (1994, via Hylkema 1995) puts Socoistac ("Our Mother Santa Clara", 25 converts 1777–93) at the **second** mission site (Los Laureles), not the first. Consider moving it about 1.2 km SSE and ending it at about 1793.
- `bmw_marsh_creek_village` (Brentwood; inside the ten-county extent): **done 2026-11.** Milliken's Volvons left in 1804–06, so the row now ends in 1806.2 as "Volvon Bay Miwok village", and the Marsh-era rancheria is its own row, `cc_marsh_rancheria` (1838–56.5), in `early_region.csv`.
- `mw_utumia` (Tomales; inside the ten-county extent): **done 2026-11.** End 1820 → 1821.6 ("By the end of 1821 only 15 North Tomales Bay region people remained to be converted").

**Nearby but distinct:**
- `ohl_huchiun_san_pablo_creek` is 4.5 km from the old Aguasto row.
- `ohl_fremont_*` are 2–3 km from `ohl_oroysom`, which is counted as one of Crespí's five Fremont-plain villages.
- `ohl_tamien_guadalupe_agnews` is 2.4 km from `tam_socoisuka`, which is probably one of Anza's three villages at the Guadalupe camp.
- `mw_ewu_gallinas` is 4.3 km from `mw_awaniwi`. `mw_shotomoko_cha` is 4.1 km from `mw_puyuku`.

## The ten-county extension (2026-11): 40 villages by language area

Same standard as the core rows: a village is entered only where a published source gives a
**place** (a town site, a creek crossing, a bearing and distance, an expedition camp), never
from a tribe's territory alone and never from an archaeological site record. Every row's
`shape_note` quotes the source, states the position precision and gives the basis of the end
year. All rows are `confidence = low`.

**Where the places come from.** North of the Bay the Spanish diaries stop, and the places come
from S. A. Barrett's *Ethno-geography of the Pomo and Neighboring Indians* (1908), a
village-by-village list with bearings and distances from the towns of 1903–06, taken from
elderly informants. Barrett lists several hundred "old village sites"; most were never tied to
a period. A Barrett village is entered **only where Milliken's mission-register work (2009)
ties it to a community that was living there at contact** — which also gives the end year.
South of the Bay and in the Delta the places are the villages the expeditions walked into
(Crespí 1769 and 1772, Palóu 1774, Font and Anza 1776), located by Bolton's route notes.

**End years** follow the core rule: the year the community's last large group was baptised
(Mission Dolores, San José, San Rafael 1817–, San Francisco Solano 1823–, Santa Cruz 1791–,
San Juan Bautista 1797–), per Milliken. Three rows cannot use it and say so: Hukabetawi at
Santa Rosa (baptisms end in 1831 but Thompson has the rancheria standing in 1838 → 1839.0),
Metini (the Kashaya were never missionised; they left Fort Ross after the ranch was sold in
1867 → 1870.0) and the Volvon / Los Meganos pair on Marsh Creek. In the Napa Valley George
Yount found the tribes living at their old places again in 1831 and 1843 (Menefee 1873, quoted
by Barrett): those rancho-era rancherias are later communities and are **not drawn** (their
end is not recorded).

| Language area | Rows | Houses | Villages (end year) | Position from | Precision |
| --- | --- | --- | --- | --- | --- |
| **Coast Miwok** of the Petaluma and Sonoma valleys and Bodega Bay | 13 | 119 | Petaluma, Etem, Wotoki (1821.6), Tuchayelin (1821.95), Kotati (1822.5), Huchi, Temblek, Wugiliwa (1816.05), Cholequebit (1817.5), Chocoayco (1818.55), Tokau / Tiutuye (1832.3), Yoletamal, Kennekono (1831.35) | Barrett 1908:303–314; Cholequebit and Chocoayco from Milliken's reading of the registers ("may have been at Sears Point" / "at Lakeville") | 1–2 km; Cholequebit, Chocoayco ~3 km |
| **Southern Pomo** of the Santa Rosa plain and the Russian River, and the Pomo of Duncans Point (dialect unsettled in Barrett) | 8 | 98 | Hukabetawi (1839.0), Batikletcawi (1831.9), Cakakmo (1831.0), Tohmakau (1826.9), Tsolikawi (1831.9), Kale, Wotokkaton (1839.9), Kabemali (1827.9) | Barrett 1908:214–223, 232 | 0.5–1.5 km |
| **Kashaya** (Southwestern Pomo) | 2 | 22 | Metini at Fort Ross (1870.0), Tsubatcemali above the mouth of the Russian River (1839.9) | Barrett 1908:230–232 | 1–1.5 km |
| **Wappo** | 4 | 50 | Kaimus, Annakotanoma (1821.5), Maiyakma, Wilikos (1825.9) | Barrett 1908:268–270 | 1–2 km |
| **Patwin** of the Napa River and Suisun | 4 | 62 | Suskol, Tuluka, Tcimenukme (1815.9), Hesaia (1814.9) | Barrett 1908:293–294; Kroeber 1932 | 1–2 km |
| **Ohlone of the north shore of Carquinez Strait** (Huchiun-Aguasto, Karkin) | 2 | 22 | Mare Island, Benicia (1809.9) | town / island named by Milliken; "many villages" on that shore, Crespí 1772 | ~3 km, site ESTIMATED |
| **Bay Miwok of the Delta edge** | 1 | 40 | the village of "about four hundred persons" at Antioch (1811.5) | Anza and Font, 3 Apr 1776; Bolton | ~1.5 km |
| **Awaswas and Calendaruc** (Santa Cruz County) | 4 | 49 | Uypi on the San Lorenzo (1793.0), Aptos (1796.5), Cotoni on Scott Creek (1795.0), Calendaruc on the Pajaro (1801.9) | Crespí 1769, Palóu 1774; Bolton | 1.5–3 km |
| **Unijaima / Ausaima** (south Santa Clara County) | 2 | 48 | the village of 300 near Gilroy (1799.0), the fishing villages of San Felipe Lake (1800.9) | Crespí 1772, Palóu 1774, Font and Anza 1776; Bolton | 3–4 km |

Notes on single rows:

- **Tribe names in the registers and in Barrett.** The missionaries used the Coast Miwok names of
  the Pomo communities; the rows give both: Gualomi = Bitakomtara (Santa Rosa), Livantolomi =
  Konhomtara (Sebastopol), Livancacayomi (Cakakmo), Jauyomi (Tohmakau), Potiyomi = Kataictemi
  (Healdsburg), Lupuyomi = Kabemali (Duncans Point), Guasamolu (Tsubatcemali).
- **Weakest links, flagged in the rows.** Tsolikawi–Chaqualoyomi (Milliken: "by inference alone"),
  Tsubatcemali–Guasamolu and Tohmakau–Jauyomi ("tentatively"), Yoletamal = Barrett's helapattai
  (a guess), Kennekono = Lupualic ("tentatively"). In each the *place* is Barrett's; only the
  end year hangs on the link.
- **The Gilroy village** is one row for four diary entries (thirty grass houses, Crespí 1772;
  "no fewer than three hundred souls", Palóu 1774; "about twenty tule huts", Font 1776;
  "seventeen huts", Anza 1776). That they are one village is an inference from the routes.
- **Antioch.** The diaries name no tribe; Julpun or Ompin. Font describes larger houses of tule
  mats ("like those of the Channel"), so the row uses a 5 m footprint.
- **House types.** Barrett 1908:25, 124 (valley: pole frame and grass thatch; coast: cones of
  redwood-bark slabs), Driver 1936:189 (Wappo: grass-thatched dome on an elliptical plan). All
  use the material key `tule` so that they are drawn as domes and labelled.
- **Dry-land check** as for the core, on the ten-county grids (`grid_region_hist`, `_b1800`,
  WorldCover, elevation), over each scatter disk. Five points were moved and say so: Wotoki
  (0.7 km, to the marsh edge), Chocoayco (0.27 km), Kabemali (0.17 km, the grid's shoreline),
  Hesaia (0.36 km: Suisun City was a marsh island; the point is "a very short distance north",
  as Barrett's second informant had it) and San Felipe Lake (0.14 km). Four more were sited
  clear of the water from the start, within their stated precision: Etem, Tokau, Cholequebit
  and Antioch (Font: the huts were "not a dozen steps" from the water; they are drawn ~150 m
  back so that none stands in the river).
- **Labels.** `ground_detail.village_labels()` reads the names as they stand: "Name, … village"
  gives the name; "Tribe Ohlone village …" gives "Tribe village". Checked for all 40 rows.

**Left out of the extension, and why:**

- **Barrett's other old village sites** (dozens along the Russian River, Dry Creek, the Laguna
  and the Kashaya coast: Makahmo at Cloverdale, Danaga at Stewarts Point, the Dry Creek and
  Alexander Valley villages, Mutistul in Knights Valley, Pipoholma and Unutsawaholma near
  Geyserville, Susuli, Tulme, Himetagala …): the place is published but nothing ties the village
  to the contact years or gives an end year (these peoples were not taken to the missions).
  Entering them needs a dated basis — e.g. the 1837–39 smallpox epidemic, the 1857 removals,
  Driver's c.1870 census of Unutsawaholma — per village.
- **Conflicting places.** Oyeyomi (Barrett: Freestone; Tom Smith: Valley Ford); Yulyul of the
  Suisuns (Barrett: "about two miles south of Suisun City", tidal marsh in the c.1800 cover;
  other writers: Rockville).
- **"Indefinitely located" by Barrett.** Uliyomi, Payinetca, Tuli, Lumentakala; Guolea and
  Lupualic are placed only tentatively by Milliken.
- **Territory only, no village place** (the brief's rule: enter nothing): the Patwin Ululato
  (Vacaville), Tolenas (hills north of Fairfield), Malaca (plain east of Fairfield) and
  Libayto / Liwai (Putah Creek; Barrett's Liwai is on the Yolo bank at Winters, outside the map);
  the Awaswas Sayanta, Chaloctaca and Achistaca; Somontac, Chitac and the Ausaima of the
  Pacheco Creek hills; the Julpun and Ompin villages other than Antioch.
- **Chitactac** (Uvas Creek): the name is in the Santa Cruz registers and a county park carries
  it, but the park is an archaeological site and no register-based location was found.
- **Taylor's 1860 list for Mission Santa Cruz** (Aulintac "the rancheria proper to the Mission",
  Chalumü a mile northwest, Hottrochtac two miles northwest): a single newspaper list, not
  checked against the registers.
- **Vague diary mentions:** the village "in the hills" west of Soquel Creek and the "large
  village" behind a hill near the Corralitos lagoons (Palóu, Dec 1774); the new village being
  built south of the Pajaro in Nov 1769 (Monterey County, outside the map).

## Integration warnings (found while checking; not fixed here)

Village houses are "buildings" with `start_year` 1700, and the pipeline's neighbour-based dating picks them up:
- **Region buildings.** 51 of today's buildings around Ssipùtca in Palo Alto (37.448, −122.162) were imputed `start_year` ≈ 1699–1701 from the tule houses. They stand in 1769.
- **Sanborn tracings.** 3 Mission Bay warehouses near Sitlintac in SF got start years of about 1700.
- **Roads.** 57 region roads, 5 SF roads and 58 suburban-street segments are dated 1699, "a year before the 2nd-earliest building".
- **Ground.** About 100 urban or suburban terrain vertices near villages are city in 1769.
- **Downtown San José.** 37 downtown buildings were dated 1776–1800 from the pueblo rows.

Adding these 35 villages in towns (Concord, Hayward, Fremont, Mountain View, San José, Pleasanton…) would multiply this. **Exclude `material == tule` and the `early_*` / `ohlone` rows from building-year imputation, street dating and city-ground dating.**

## Gaps (no published village location found)

- **Oakland–Berkeley Huchiun villages** (CDM "Berkeley" region, about 360 people). Thenau, Ocquizara and Juncháque are named in the registers but not located, and the 1772 and 1776 parties saw no village between San Leandro Creek and Albany.
- **Livermore Valley and hills.** The Souyen, the Ssaoan (Brushy Peak), the Taunan and Asirin (upper Alameda Creek), and the Paleños (Hall's Valley).
- **Santa Clara districts.** South San José ("San Carlos" district) and the Huimen villages Naique and Anamás.
- **Guaulen Itaes.**
- **Cotegen.** Their villages Ssalaime and Torose are unlocated. The existing `ohl_tunitas` row is probably Cotegen.
- **Ohlone villages at Mission Santa Clara 1777–1780s.** Peña reported "more than forty villages within a radius of five leagues" of the mission in 1777, but most are unlocated.

## Sensitivity

- Village sites are culturally sensitive, and many are also burial places.
- Positions here are **only as precise as the published sources** (about 1–4 km, stated per row): the creek, the camp, or the town named in a diary or in Milliken.
- No CHRIS / Northwest Information Center records and no unpublished site locations were used.
- Points were kept off named, published archaeological sites (the Coyote Hills mounds and Síi Túupentak at Sunol).
- Nelson's shellmound map was deliberately not used for points.
- Before labelling sites publicly, consult the tribes of the area:
  - The Muwekma Ohlone Tribe and other Ohlone groups for the East Bay and South Bay.
  - The Ramaytush Ohlone for the Peninsula.
  - The Federated Indians of Graton Rancheria for the Coast Miwok.
  - For the ten-county extension: the Federated Indians of Graton Rancheria (Coast Miwok and Southern Pomo of Sonoma County); the Kashia Band of Pomo Indians of the Stewarts Point Rancheria (Metini and the coast); the Dry Creek Rancheria and Lytton bands (Southern Pomo of Healdsburg and Dry Creek); the Mishewal Wappo; the Yocha Dehe Wintun Nation (Patwin); the Amah Mutsun Tribal Band (Awaswas and Mutsun of Santa Cruz and the Gilroy–Pajaro country).

  The map's existing label style (local-tribe names such as `sf_yelamu` in `places.csv`) is preferable to labelling individual sites.

## Sources

- R. Milliken, L. H. Shoup and B. R. Ortiz, *Ohlone/Costanoan Indians of the San Francisco Peninsula and their Neighbors, Yesterday and Today* (Far Western for NPS / GGNRA, 2009), ch. 3–5 and App. B: <https://npshistory.com/publications/goga/ohlone-indians.pdf>
- R. Milliken, *Ethnohistory and Ethnogeography of the Coast Miwok and their Neighbors, 1783–1840* (NPS / GGNRA, 2009): <https://www.nps.gov/goga/learn/historyculture/upload/2009-Final-Coast-Miwok-Report.pdf>
- R. Milliken et al., *Contact-Period Native California Community Distribution Model*, vol. 1, App. B, Table B-1 (Far Western, 2010): <https://wiki.farwestern.com/index.php/Volume_1_Appendix_B>
- M. V. Arellano, A. Leventhal et al., "Ethnohistory, Historic Ties, and Tribal Stewardship of Sunol/Pleasanton, Santa Clara Valley, and Adjacent Areas", ch. 3 of *Protohistoric Village Organization … Síi Túupentak (CA-ALA-565/H)*, CARD Publication 20 (2014). It quotes Milliken 1991, 1995, 2008, Fages 1770 and 1772, Crespí's Seville manuscript, and King 1994 / Hylkema 1995 on the Santa Clara districts: <https://muwekma.org/pdf/muwekma-ethnohistory-sfpuc-ala-565.pdf>
- Fr. Juan Crespí, diary of the Fages expedition, 20 Mar – 5 Apr 1772, in F. Palóu, *Historical Memoirs of New California*, ed. H. E. Bolton, vol. ii (1926), ch. 32–33, with Bolton's route notes: <https://archive.org/details/historicalmemoir0000fray>
- J. B. de Anza, diary (vol. iii) and P. Font, complete diary (vol. iv), 29 Mar – 3 Apr 1776, in H. E. Bolton, *Anza's California Expeditions* (1930), with Bolton's route notes: <https://archive.org/details/anzascaliforniae03bolt>, <https://archive.org/details/anzascaliforniae04bolt>
- For the ten-county extension:
  - S. A. Barrett, *The Ethno-geography of the Pomo and Neighboring Indians*, UCPAAE 6(1), 1908 (public domain): village lists with bearings and distances for the Pomo (pp. 214–233), Wappo (268–274), southerly Wintun / Patwin (290–294) and Coast Miwok (303–314); house types (pp. 25, 124). <https://archive.org/details/ethnogeographyp00barrgoog>
  - Milliken's Coast Miwok report (above), ch. 10–12: the Bodega Bay, Sonoma, Petaluma and Bloomfield / Cotati regions, and the Pomo and Wappo communities at Mission San Rafael, with baptism years.
  - Milliken, Shoup & Ortiz (above), ch. 5–7: the Patwin, Wappo ("Canicaymo") and Delta migrations to Missions Dolores and San José; Missions Santa Cruz and San Juan Bautista.
  - Fr. Juan Crespí, diary of the Portolá expedition, Oct–Nov 1769, in Palóu, *Historical Memoirs* ii (above), with Bolton's notes (Pajaro River, Soquel, San Lorenzo, Scott Creek).
  - Fr. Francisco Palóu, diary of the Rivera expedition, Nov–Dec 1774, in *Historical Memoirs* iii (1926), with Bolton's notes (Gilroy valley; Scott Creek, San Lorenzo River, Soquel–Aptos): <https://archive.org/details/historicalmemoir0003herb>
  - Anza and Font, 24 Mar and 3 Apr 1776 (Gilroy; Antioch), in Bolton's *Anza's California Expeditions* iii–iv (above).
  - A. L. Kroeber, *The Patwin and their Neighbors*, UCPAAE 29(4), 1932 ("South of Cache creek, data fail"; Suskol, Tuluka, Chimenukme): <https://digitalassets.lib.berkeley.edu/anthpubs/ucb/text/ucp029-005.pdf>
  - H. E. Driver, *Wappo Ethnography*, UCPAAE 36(3), 1936 (houses; Unutsawaholma c.1870): <https://digitalassets.lib.berkeley.edu/anthpubs/ucb/text/ucp036-004.pdf>
  - O. C. Stewart, *Notes on Pomo Ethnogeography*, UCPAAE 40(2), 1943 (community names Bitakomtara, Konhomtara, Kataictemi, Tsoliikawi, as cited by Milliken): <https://digitalassets.lib.berkeley.edu/anthpubs/ucb/text/ucp040-003.pdf>
  - Fort Ross Conservancy, "Ranch era" (the Kashaya sent away after the 1867 sale): <https://www.fortross.org/ranch-era> — the site refused connections from here; quoted from a search summary, so the Metini end year is marked ESTIMATED.
  - Not reached: Milliken 1995 (*A Time of Little Choice*, the tribe-by-tribe appendix); Collier & Thalman 1991 (Kelly's Coast Miwok notes); Kroeber 1925; the Santa Cruz and San Juan Bautista register studies (Milliken 1993, 2002).
- Background, not used for points: R. Milliken, *A Time of Little Choice* (Ballena Press, 1995); A. L. Kroeber, *Handbook of the Indians of California* (1925); R. Levy, "Costanoan", *Handbook of North American Indians* 8 (1978); N. C. Nelson, *Shellmounds of the San Francisco Bay Region* (UCPAAE 7(4), 1909).
