# Early settlements outside San Francisco, 1769 – c.1850

Research notes for `data/tables/early_region.csv`: the missions, the pueblo, the Mexican ranchos and the Native villages of Santa Clara, Alameda, Contra Costa, San Mateo and Marin counties, before the region's buildings take over.

The owner's complaint was that Mission Santa Clara, Mission San José and the pueblo of San José were labelled but empty. They were not empty. Mission Santa Clara held about 1,250 people in 1800, the largest mission population in California. It moved four times and left a trail of churches, quadrangles and rows of adobe houses for its Indian families. Mission San José peaked at 1,886 people in 1831. The pueblo of San José had about 40 houses and huts in 1835, and a map of the mid-1840s shows 51 buildings.

The table has the same columns as `early_sf.csv` plus `county`, and `sf_predecessors.table_buildings` reads it as it stands. A test run with an empty lot layer gives 972 valid footprints from 142 rows. It has 6 high, 22 medium and 114 low-confidence rows.

**Already modelled, not repeated here.** These are landmark models:

- Mission Santa Clara's 1825, 1861 and 1928 churches (`southbay.ts`).
- Mission San José's 1809 adobe church, its 1869 church, the 1985 church and the surviving padres' wing (`eastbay.ts`).
- Mission San Rafael's 1949 replica chapel (`southbay.ts`).

The surviving 1822 Adobe Lodge at Santa Clara University is in `known_building_dates_region.csv`.

---

## 1. Sources

| Short name | Source | Used for |
|---|---|---|
| Skowronek & Wizorek 1997 | R. K. Skowronek and J. C. Wizorek, "Archaeology at Santa Clara de Asís: The Slow Rediscovery of a Moveable Mission", *PCAS Quarterly* 33(3): 54–92. <https://www.pcas.org/Vol33N3/333Skowr.pdf> | The five Santa Clara sites. It gives the building dimensions of the first two sites from the Informes (after Spearman 1963), the third-site layout, the fourth church (30 × 94 ft on the 1854 Black plat; demolished 1867), and the fate of the neophyte rows. |
| SCU Neatline | Santa Clara University Digital Humanities, "Sites of Mission Santa Clara" exhibit. <https://dh.scu.edu/exhibits/neatline/show/sites-of-mission-santa-clara> | **Coordinates** of sites 1–5 (Web Mercator points in the page's JSON, converted) and their dates. |
| Bancroft i–iii | H. H. Bancroft, *History of California* vols 1–3 (1884–85). <https://archive.org/details/historyofcalifor01banc> … `03banc` | Pueblo population 1791–1800 and the move before 1791 (i.716–718). Santa Clara in the 1790s (i.722–725): Vancouver's square, the 1795 lengthening of the church, the neophyte adobes of 1793–98, and Amador's 1796 list of buildings. Founding of Mission San José (i.555–556). Langsdorff at San José in 1806 (ii.139–140). The pueblo chapel of 1803 (ii.135). San Rafael's 1818 adobe of 87 × 42 × 18 ft (ii.330). Statistics and secularization of San José, Santa Clara and San Rafael (iii.715–727). |
| Hall 1871 | F. Hall, *The History of San José and Surroundings* (1871). <https://archive.org/details/historyofsanjos00hall> | The old pueblo site. The juzgado of 1798–1850 (size, rooms, position). The 1803 chapel and the 1835 church. About 40 houses in 1835. The 1846–49 American town. The Alameda of 1799. Vancouver's 1792 description of Santa Clara (pp.421–423). A Spanish writer of 1822 on neophyte huts (p.424). |
| Arbuckle 1985 | *Clyde Arbuckle's History of San José* (1985), History San José digital copy. <https://archive.org/details/casjhsj_000308> | The bounds of the old pueblo (Guadalupe, W Hedding, N First, Hobson; 400 yd from the river). The founding party of 66. Population 1777–1846. The 51 structures of the mid-1840s. The State House (40 × 60 ft, two storeys, adobe). Bayard Taylor's 1849 descriptions. |
| Milliken 2009 | R. Milliken, L. Shoup and B. Ortiz, *Ohlone/Costanoan Indians of the San Francisco Peninsula and their Neighbors* (NPS/GGNRA). <https://npshistory.com/publications/goga/ohlone-indians.pdf> | Peninsula local tribes and villages (App. B). The San Pedro y San Pablo outstation at Pruristac (1786/87–1792 chapel). Village sizes and explorers' observations (ch.3–4). The Huchiun-Aguasto village of 400. |
| CHL | California Historical Landmarks: OHP listings `https://ohp.parks.ca.gov/ListedResources/Detail/<n>`. Marker texts and **GPS** from californiahistoricallandmarks.com (`/landmarks/chl-<n>`). | Positions and dates for the following landmarks: 210 (Ynitia adobe), 207 (Reed's mill), 220, 249 (Woman's Club adobe), 250 (Santa Clara sites), 279, 285, 334, 338, 356 (Castro home), 375 (Tunitas), 391 (Sánchez adobe), 393 (San Mateo hospice), 433 (first pueblo), 455, 461 (State Capitol), 478, 509–512, 515, 524 (Briones), 866 (Peralta adobe), 898, 910 (St Joseph's) and 925 (Peralta hacienda). |
| Peralta Hacienda chronology | Peralta Hacienda Historical Park, "Peralta history chronology". <https://www.peraltahacienda.org/PeraltaHistoryChron.htm> | Every Peralta adobe, with size, date and fate: Antonio 1821 and 1840 with the walled compound and its lean-tos; Vicente 1836 and 1847–48; Domingo 1841; Ygnacio 1835 and 1842. |
| Local histories | El Cerrito Historical Society (Castro adobes); San Pablo Historical Society (Alvarado adobe); Milpitas Historical Society (Higuera adobe); Mill Valley Historical Society (Reed adobe); Sausalito Historical Society (Richardson); John Marsh House Trust; City of Hayward (Guillermo Castro); USGS OFR 2008-1121 *Resistance revised* (damage to adobes in 1856 and 1868, after Bowman). | Single rows; URLs are in each row. |
| Wikipedia | Mission San Rafael Arcángel; Sánchez Adobe Park; Coast Miwok (village list after Barrett 1908); José María Alviso Adobe; Alviso, San Jose; Rancho San Ramon (Amador); Alvarado Adobe. | Used as a pointer and a cross-check. |
| Overture / OSM | `region5_building.parquet` (ODbL) | Footprint size and orientation of the surviving adobes, measured only (no geometry copied): Peralta, Roberto, J. M. Alviso, Woman's Club, Martínez, Sánchez, S. Pacheco, Moraga, Alviso (Pleasanton). Also the Adobe Lodge and the church for the 1825 quadrangle. |
| Overture roads | `roads_local` / `roads_region` (ODbL) | Street intersections used as anchors: Market & Post, Hobson / Hedding / First, Vicente Way & 55th, Church Ln & San Pablo Ave, Dublin Blvd & San Ramon Rd, La Goma & Locke, Pine & Bonita, Mission Blvd & C St. |

The following could not be reached, mostly because of bot checks or loan-only copies:

- Hendry & Bowman, *The Spanish and Mexican Adobe and Other Buildings in the Nine San Francisco Bay Counties* (1940–45, Bancroft Library MS). It has the plans of Santa Clara, San José and Mission San José and every rancho adobe.
- Spearman, *The Five Franciscan Churches of Mission Santa Clara* (1963).
- Hylkema 1995, the Caltrans report on the third site, with its quadrangle reconstruction.
- McCarthy 1958, *History of Mission San Jose*, a loan-only copy on archive.org.
- Panich, Allen and Galvan 2018 on the Mission San José neighbourhood (eScholarship and SCU returned 403).
- Milliken 1995, *A Time of Little Choice*.
- HMDB marker pages and HABS/HALS drawings at the LOC (CA-87 for San Rafael).

Each of these would sharpen a LOW-CONFIDENCE row.

---

## 2. Places

### Mission Santa Clara de Asís (35 rows, about 190 structures)

| Phase | Dates | Position | What is in the CSV |
|---|---|---|---|
| **1st site** (Thámien, at the village So-co-is-u-ka) | 12 Jan 1777 – flood 23 Jan 1779; Murguía stayed until Nov 1779 | Neatline point 37.37638, −121.94449, near the N end of the airport by the Guadalupe–Mission Creek confluence. Never confirmed by archaeology (Cartier 1980). | A palisade quadrangle 70 varas square: church and sacristy 6 × 20 varas; kitchen 6 × 22; offices and dwellings 5 × 31; cattle corral 30 × 30; goat corral 12 × 12; 20 neophyte huts. The Tamien village sits beside it. |
| **2nd site** (sycamore grove, ¼ league from the river) | 11 Nov 1779 – May 1784 | Neatline 37.36651, −121.94150, 30 m from the CHL 250 marker at Martin Ave & De la Cruz Blvd | Church and sacristy 6 × 25 varas; habitation and storeroom with veranda 5 × 45; servants' house 5 × 10; kitchen and shop 5 × 10; 40 huts. |
| **3rd (Murguía) site**, CA-SCl-30 | Cornerstone 19 Nov 1781, dedicated 16 May 1784; damaged in 1812 and 1818; stripped c.1825 | Neatline 37.35191, −121.93791, the commemorative park at 500 El Camino Real | Church 9 × 41 varas running E–W, lengthened 24 ft in 1795. The west wing of 1784, a south range and a partial east range around Vancouver's 170 × 100 ft court ("a square, but not an entire enclosure", 1792). Two detached granaries of 1792. The 1796 buildings on higher ground: padres' house of 8 rooms × 5 yd, guard-house 8 × 5 yd, storehouse 5 yd, five soldiers' houses of 5½ yd, and a corral 36 yd square with walls 6 ft high. 80 tule huts from 1784 to 1806. |
| **Neophyte rows** | 14 houses in 1793, 9 in 1794, and "nearly all the married neophytes" housed before 1798; tile roofs by 1798 | West of the Murguía church, around the surviving Woman's Club (Peña) adobe (CHL 249) and the 2012–15 excavation under the Dowd Art building | Five rows of 1793–98 plus three western rows of the 1800s, all parallel to the surviving adobe at 66°, 6 m deep and 62–75 m long, ending 1852–62 ("gradually demolished and replaced with wood frame homes"). The surviving unit is a separate `SURVIVES` row. |
| **4th (temporary) church** | Built 1818–19; church Dec 1819 – Aug 1825; boys' dormitory; Candelaria's house and dance hall; bought 1860; **demolished 1867** | Neatline 37.34881, −121.94043 (St Ignatius Gardens) | 30 × 94 ft with a porch along the west wall (1854 Black plat). HIGH confidence. |
| **5th site** (1822–25 quadrangle) | The church is a landmark; the Adobe Lodge and a wall survive | A court between the church and the Adobe Lodge | An east range (convento, gone c.1862 under the Jesuit faculty residence) and a south range. LOW confidence. |

**Population:** 927 (1790), 1,247 (1800), 1,332 (1810), 1,395 (1823), 1,226 (1831), 1,125 (1832), about 800 (1834) and about 200 at the end of the 1830s (Bancroft; Hall).

**The Alameda** (for the roads layer): in 1799 Padre Magín Catalá had 200 Indians plant, water and guard a grove of willows "that link the Pueblo with the Mission of Santa Clara". The grove "formerly extended easterly as far as the Guadalupe river" and protected walkers from wild cattle (Hall 1871 pp.82–84). The road ran from the mission (then the third site, at today's El Camino Real / The Alameda by SCU) east to the river crossing and on to the pueblo; today's The Alameda follows it. Popular accounts describe three rows of willows over about 3 miles. Hall gives only the year, the planting crew and the eastern extent.

### Pueblo de San José de Guadalupe (16 rows, about 220 structures)

- **El Pueblo Viejo**, founded 29 Nov 1777 by Moraga with 66 people (68 in the 1778 padrón). It lay between the Guadalupe, W Hedding St, N First St and Hobson St, its eastern edge about 400 yd from the river (Arbuckle). Hall puts it 1¼ miles north of the plaza, by the first bridge on the Alviso road. The houses were palisade (palizada) with mud plaster and grass or earth roofs. The CSV has 14 founders' houses, 10 later houses, a council house and jail (named in the 1783 titles), and a granary. The point is at the centre of the bounded area; the CHL 433 marker at the old City Hall, 151 W Mission St, lies inside it.
- **The move.** The petition came in 1785 and Ugarte authorized it in 1787. Bancroft dates the move before 1791 (Fages to Romeu, Feb 1791); Hall and Arbuckle say 1797. The CSV starts the new houses in 1791 and ends the old ones in 1797, so both stand for 1791–97 (UNCERTAIN).
- **El Pueblo Nuevo** stood around the plaza on Market St between San Fernando and San Carlos (Plaza de César Chávez). The house groups are sized to the documented totals: about 40 houses and huts with a dozen good adobes in 1835 (Hall); 51 structures on the map of the mid-1840s (Arbuckle); 1849, "a collection of adobe houses, with tents and clapboard dwellings ... over a square half-mile" (Bayard Taylor). Positions within the town are procedural.
- **Documented buildings:**
  - The **juzgado** of 1798–1850: one storey, three rooms, gables facing E and W, on Market St at El Dorado (now Post) St. It was pulled down in 1850 and its adobes went into Hoppe's store.
  - The **1803 chapel**: adobe with a tule roof, cornerstone laid 12 Jul 1803; it stood until 1835.
  - The **1835 church** on the same spot: encased in brick in 1858 and damaged in 1868. Both are at the cathedral corner, Market & San Fernando (CHL 910).
  - The **Peralta adobe**, built before 1800 (it SURVIVES).
  - The **Roberto-Suñol adobe** of 1836 (it SURVIVES).
  - The **State House** of 1849–53: two storeys, 40 × 60 ft, adobe, on the east side of Market Square opposite the CHL 461 tablet.
  - The **1846–49 American stores** and the **1849 tent town**.
- **Population:** 66 (1777), 82 (1791), 208 (1796), 152 (1798), 171 (1800), about 125–175 (1800s), 240 (1820), 524 in the pueblo (1831 padrón), 935 in the 1841 padrón (including ranchos), 600–800 (Bryant, 1846), "4,000" in Jan 1850, when San José was the state capital (Michael Sanor's letter, quoted by Arbuckle; the 1850 Federal Census returns for San José were lost). Sanor gives Santa Clara 1,000 at the same date.

### Mission San José (17 rows, about 150 structures)

The site is Oroysom. The CSV has:

- The 1797 enramada and the timber buildings with grass roofs: a wooden church until 1809, plus the padres' house, guard-house and granary.
- Three adobe ranges closing a court east of the surviving padres' wing.
- Workshops: soap, tannery and mill.
- 90 conical straw huts (Langsdorff, 1806) and 30 later ones.
- Eight adobe rows of neophyte houses from 1806–17. The number and position of the rows are by analogy with Mission Dolores, west of Mission Blvd, LOW confidence.
- The village of Oroysom.

The 21 Oct 1868 earthquake destroyed everything but part of the padres' quarters (CHL 334), so the ranges end in 1868. Population: 286 (1800), 545 (1810), 1,886 (1831, the peak), 589 (1839), 580 (1840). In 1837 the orchard and vineyard had 6,000 vines and about 600 fruit trees (Bancroft iii.725). No walls are documented, so no walls are drawn.

### Mission San Rafael Arcángel (5 rows)

Founded 14 Dec 1817 at Nanaguani. The 1818 adobe was 87 × 42 × 18 ft and held the chapel, the padre's house and hospital rooms behind a corridor of tules. A church was added at one end; secondary sources say the next year. The ruins were removed in 1861–70. The CSV places the 1818 adobe at the 1949 replica chapel, which is said to stand on the hospital site. It also has outbuildings, a neophyte village and the village of Awani-wi. Population: about 230 (1817), 590 (1820), 1,140 (1828), about 500 (1834), 195 at the mission (1839).

### Mission Dolores outposts (San Mateo County)

- **San Pedro y San Pablo** stood at the Aramai village of Pruristac (Pacifica). Work began in 1786 and its chapel baptized 99 people from mid-1787 to early 1792. It had "a granary, a chapel and four other rooms surrounding three sides of a plaza", in the NE part of today's Sánchez Adobe park. It was a cattle station until 1834, and its bricks probably went into the **Sánchez Adobe** of 1842–46 (CHL 391, which SURVIVES).
- **The hospice at San Mateo** (CHL 393): an adobe on El Camino Real north of San Mateo Creek, "built around 1800" (or a granary of the 1790s). It was badly damaged in 1868 and is gone.

### Ranchos and the American years

The rows include:

- **Alameda.** Every Peralta adobe on Rancho San Antonio:
  - Antonio's 1821 and 1840 houses and his walled 2½-acre compound with 22–27 lean-tos, all destroyed in 1868 except the 1821 adobe (razed 1897).
  - Vicente's 1836 and 1847–48 adobes at Temescal.
  - Domingo's 1841 adobe on Codornices Creek.
  - Ygnacio's 1835 and 1842 adobes at San Leandro.

  Also Guillermo Castro's adobe and corral at Hayward; Amador's 1826 house and later two-storey adobe at Dublin (gone in 1868); the Estudillo house (c.1850); and the F. S. Alviso adobe at Pleasanton (1844–46, it SURVIVES).
- **Santa Clara County.** The J. M. Alviso adobe (1837) and J. Higuera adobe (c.1831) in Milpitas (both SURVIVE) and the other Tularcitos adobes; the Juana Briones house (c.1844–2011); and three adobes at the Embarcadero de Santa Clara (Alviso, c.1840).
- **Contra Costa.**
  - Francisco Castro's adobe at San Pablo (before 1829) and the Alvarado adobe (1842–1954; the replica dates from 1978).
  - The Victor Castro adobe at El Cerrito (1839–1956).
  - The Moraga (1841), Salvio Pacheco (1835), Fernando Pacheco (1843, rebuilt 1941) and Martínez (1849) adobes, all of which SURVIVE.
  - Marsh's adobe at Los Meganos (c.1838–56) and the Miwok village near it.
  - The first houses of Martínez (1849) and Elam Brown's place at Acalanes (1848).
- **Marin.** The Camilo Ynitia adobe at Olompali (from 1834; burned 1976, now a ruin); John Reed's mill (1834–36) and his 18 × 30 ft adobe in Mill Valley; Richardson's house in Sausalito (1841).
- **San Mateo.** Charles Brown's 1847 sawmill near Woodside.

### Native villages (23 rows, about 270 houses)

Only villages for which a source gives a place are included. All are LOW confidence, with the site point estimated and the house count estimated at 6–8 people per house.

- **Ohlone.**
  - So-co-is-u-ka (Tamien) at the first Santa Clara site, and Oroysom at Mission San José.
  - Pruristac and Timigtac (Aramai).
  - Siplichiquin (Urebure).
  - Two Ssalson groups on San Mateo Creek (Uturbe, Altagmu, Aleitac).
  - The Lamchin village on Laurel Creek (Font, 1776) and Cachanigtac / Las Pulgas.
  - Ssipùtca (Puichon) on San Francisquito Creek, about 250 people per Font.
  - Oljon at San Gregorio Creek and the Tunitas Creek village (both Portolá, 1769).
  - Ssatumnumo and Chagunte (Chiguan).
  - Mitenne (Quiroste) at Whitehouse Creek, about 200 people per Crespí.
  - The Huchiun-Aguasto village of about 400 between Rodeo and Pinole creeks.
- **Bay Miwok.** The Marsh Creek village.
- **Coast Miwok** (Barrett's list via Wikipedia): Olompali, Awani-wi (San Rafael), Liwanelowa (Sausalito), Echa-tamal (Nicasio), Olema-loke, Bauli-n (Bolinas), Chokeche (Novato), Puyuku (Ignacio) and Utumia (Tomales).

Tule houses follow `early_sf.csv`: a 4 m dome, 2.5 m high. Mission huts are 3.6 m across and 2.7 m high, after the Spanish writer of 1822 ("at the most ... four yards in diameter ... elevated three yards").

**Left out for lack of a located village:**

- Ohlone: Alson, Tuibun, Jalquin, Seunen and Causen.
- Bay Miwok: Saclan, Chupcan, Tatcan, Volvon and Carquin.

For the Volvon "Morgan Territory village" only advocacy sources were found. The Emeryville and West Berkeley shellmounds are pre-contact and were abandoned long before 1769. The Ohlone and Miwok tribes should be consulted before any public labelling of village sites.

---

## 3. Method and conventions

- **Columns and meaning** are as in `early_sf.md` §6:
  - `end_year` is exclusive.
  - `footprint_m` is "L×W", with L along `rotation_deg`, a compass bearing.
  - Rows with `count > 1` are scatters within `spread_m`.
  - Corrals, and walls with a height of 2.5 m or less, are fences or walls, to be drawn as outlines.
  - Palisade (jacal, palo parado) and wattle-and-daub buildings use the material key `wood frame`. Coast Miwok bark or tule kotchas use `tule`.
- **Layout frames.** Local layouts were built in metres from an anchor, using a north/east offset or a bearing frame, with helper code in the scratchpad (not committed). The anchors are:
  - Santa Clara: the Neatline points and the surviving adobe.
  - Mission San José: the landmark frame (261°; u = north, v = west).
  - San Rafael: the replica chapel centre in the landmark frame (7°).
  - Peralta Hacienda: the 1870 house.
- **`SURVIVES` rows** (11): the shape note begins with "SURVIVES" and `end_year = 9999`. These buildings are in today's footprints (Overture), most with a wrong or missing assessor year:
  - `scl_womans_club_adobe`, `sj_peralta_adobe`, `sj_roberto_sunol_adobe`, `scl_alviso_adobe_milpitas`, `scl_higuera_adobe_milpitas`
  - `sm_sanchez_adobe`, `ala_alviso_adobe_pleasanton`
  - `cc_moraga_adobe`, `cc_salvio_pacheco_adobe`, `cc_fernando_pacheco_adobe`, `cc_martinez_adobe`

  **Better: date today's footprint at that point (a `known_building_dates_region` row) and skip the box.** Otherwise a box and the real footprint overlap.
- **Replicas.** The Alvarado adobe (`cc_alvarado_adobe`, 1842–1954) has a 1978 replica in today's data, which must not predate 1978. Fernando Pacheco's adobe was rebuilt in 1941.
- **Terrain check.** Points were tested against `grid_region_b1800` and `grid_region_landyear`. Ten estimated points were moved 60–370 m onto dry c.1800 ground; each such row says so in its note. Two documented sites remain on cells the terrain treats as wet:
  - **Mission San Rafael** (`sr_mission_house_1818`, `sr_church_1819`, `sr_outbuildings`). The terrain has tidal marsh until 1915–48 at 15 m elevation at 5th & A St. The 1800 baylands polygon at San Rafael looks shifted onto the hill, so this is a terrain error, not a siting error.
  - **Alviso** (`scl_alviso_embarcadero_adobes`). Its cells are marsh with no land year, so the land check will not move it; the town stood at the marsh edge.
- **Overlap with other data.**
  - `sj_*` rows are downtown San José, where `san_jose_downtown_1915` Sanborn tracings start much later; no time overlap.
  - Mission Santa Clara rows sit under SCU buildings; the generated predecessors of the region pipeline should not add houses on campus before 1851.
  - Procedural region predecessors start after 1850 and do not collide.

## 4. Gaps and suggestions

1. **Hendry & Bowman (1940–45)** and the **1854 Black plat of Mission Santa Clara** would replace the LOW-confidence quadrangle layouts at Santa Clara (third and fifth sites) and Mission San José, and the guessed positions of the Mission San José rancheria.
2. **Panich et al. 2018** (the Mission San José Native neighbourhood) and the SCU Franklin Street reports (Hylkema, Panich, 2012–15) would fix the row orientation and extent.
3. **The 1847 Lyman survey and the mid-1840s map of San José** (Arbuckle's 51 structures) would let the procedural pueblo houses be placed one by one.
4. **The first pueblo site** is bounded but not excavated; the CSV scatters its houses over the bounded area.
5. The **San Mateo hospice**: construction year (1790s or c.1800) and size are unknown.
6. The 1847 **Dennis Martin mill** and the Rancho de las Pulgas and Buri Buri adobes are unlocated.
7. **Not included:** Benicia and Sonoma (out of scope); New York of the Pacific (1849; no buildings documented); Timothy Murphy's San Rafael house; the Garcia adobe at Olema; Briones at Bolinas; the Ygnacio Martínez hacienda in Pinole Valley; the Berryessa adobe in Santa Clara (date not verified).
