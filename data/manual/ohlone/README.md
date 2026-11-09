# Contact-era Native villages, c.1769–1810 (`villages.csv`)

Ohlone (Costanoan), Bay Miwok and Coast Miwok village sites around the core Bay in the
years of the Spanish entry, so that 1769 shows the people who lived here. This file is
a supplement to `data/tables/early_region.csv` and `early_sf.csv`. It has the same
columns, one row per village, with `count` tule houses scattered over `spread_m`.

- **35 rows, 422 houses.**
  - Contra Costa: 12 rows, 190 houses.
  - Alameda: 11 rows, 108 houses.
  - Santa Clara: 7 rows, 80 houses.
  - San Mateo: 2 rows, 16 houses.
  - Marin: 3 rows, 28 houses.
- **Combined total.** With the 26 Native villages already in `early_region.csv` and the 5 Yelamu villages in `early_sf.csv`, the map would show about 60 villages in 1769. That count drops the superseded Aguasto row; `bmw_marsh_creek_village` and `mw_utumia` lie outside the map extent.
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
- `bmw_marsh_creek_village`: it lies **outside the map extent** (Brentwood). Milliken's Volvons left in 1805 – March 1806, so the 1838–45 Marsh-era rancheria is a later community.

**Nearby but distinct:**
- `ohl_huchiun_san_pablo_creek` is 4.5 km from the old Aguasto row.
- `ohl_fremont_*` are 2–3 km from `ohl_oroysom`, which is counted as one of Crespí's five Fremont-plain villages.
- `ohl_tamien_guadalupe_agnews` is 2.4 km from `tam_socoisuka`, which is probably one of Anza's three villages at the Guadalupe camp.
- `mw_ewu_gallinas` is 4.3 km from `mw_awaniwi`. `mw_shotomoko_cha` is 4.1 km from `mw_puyuku`.

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

  The map's existing label style (local-tribe names such as `sf_yelamu` in `places.csv`) is preferable to labelling individual sites.

## Sources

- R. Milliken, L. H. Shoup and B. R. Ortiz, *Ohlone/Costanoan Indians of the San Francisco Peninsula and their Neighbors, Yesterday and Today* (Far Western for NPS / GGNRA, 2009), ch. 3–5 and App. B: <https://npshistory.com/publications/goga/ohlone-indians.pdf>
- R. Milliken, *Ethnohistory and Ethnogeography of the Coast Miwok and their Neighbors, 1783–1840* (NPS / GGNRA, 2009): <https://www.nps.gov/goga/learn/historyculture/upload/2009-Final-Coast-Miwok-Report.pdf>
- R. Milliken et al., *Contact-Period Native California Community Distribution Model*, vol. 1, App. B, Table B-1 (Far Western, 2010): <https://wiki.farwestern.com/index.php/Volume_1_Appendix_B>
- M. V. Arellano, A. Leventhal et al., "Ethnohistory, Historic Ties, and Tribal Stewardship of Sunol/Pleasanton, Santa Clara Valley, and Adjacent Areas", ch. 3 of *Protohistoric Village Organization … Síi Túupentak (CA-ALA-565/H)*, CARD Publication 20 (2014). It quotes Milliken 1991, 1995, 2008, Fages 1770 and 1772, Crespí's Seville manuscript, and King 1994 / Hylkema 1995 on the Santa Clara districts: <https://muwekma.org/pdf/muwekma-ethnohistory-sfpuc-ala-565.pdf>
- Fr. Juan Crespí, diary of the Fages expedition, 20 Mar – 5 Apr 1772, in F. Palóu, *Historical Memoirs of New California*, ed. H. E. Bolton, vol. ii (1926), ch. 32–33, with Bolton's route notes: <https://archive.org/details/historicalmemoir0000fray>
- J. B. de Anza, diary (vol. iii) and P. Font, complete diary (vol. iv), 29 Mar – 3 Apr 1776, in H. E. Bolton, *Anza's California Expeditions* (1930), with Bolton's route notes: <https://archive.org/details/anzascaliforniae03bolt>, <https://archive.org/details/anzascaliforniae04bolt>
- Background, not used for points: R. Milliken, *A Time of Little Choice* (Ballena Press, 1995); A. L. Kroeber, *Handbook of the Indians of California* (1925); R. Levy, "Costanoan", *Handbook of North American Indians* 8 (1978); N. C. Nelson, *Shellmounds of the San Francisco Bay Region* (UCPAAE 7(4), 1909); S. A. Barrett, *Ethno-geography of the Pomo and Neighboring Indians* (1908).
