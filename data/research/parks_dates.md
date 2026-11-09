# Park creation dates (RPD parks): research notes, 2026-11

Goal: every SF Rec & Park polygon in `data/raw/sf_rpd_parks` (222 parks, field `map_park_n`)
gets a `start_year` in `data/tables/parks.csv`, so `pipeline/ground.py` shows it from that year.

Result: 149 rows appended (82 `exact`, 67 `estimated`). The 10 existing rows that had a blank
`start_year` were filled in place: their old text is kept after an "Earlier note:" marker.
Monster Park stays blank on purpose. Now 221 of the 222 RPD parks join to a dated row.

## Rule used for `start_year`

* The year the site became a public park, playground or open space in use.
  * For a developed park that opened soon after purchase: the opening or dedication year if it
    is known, otherwise the purchase year.
  * For land bought to stay natural (hilltops, Open Space lots): the purchase year.
  * For school-district land run as a playground: the year the Board of Education gave
    permission.
* `exact` means a dated record (purchase, transfer, completion, or dedication) for that year.
  `estimated` means a bounded range or a stated proxy. The proxy is written in `start_event`
  ("first appears in …", "estimated …").

## Main sources

Most of these are scans of SF Public Library documents on archive.org. Their full text was
grepped by park name, by street corner, and by Assessor block number. To match the Open
Space Program's block and lot lists, each RPD polygon was joined to the parcels in
`data/raw/sf_parcels`.

| Source | archive.org id | Used for |
|---|---|---|
| Playground Commission annual reports 1912–26 | `annualreporto19121926sanf` | deeds of 1909–1911 (Helen Wills/Spring Valley, Presidio Heights, Mission, Excelsior, Hamilton); 1926 playground directory |
| Playground Commission annual reports 1928–30 | `annualreporto19281930sanf` | "History of Playground Department" timeline 1898–1929 (Richmond 1914, Rolph 1919, Ocean View 1922, Douglass 1923, Folsom/Portola 1924, Argonne/Chinese/Bay View 1925, Potrero Hill 1926, West Portal 1927, Michelangelo 1928, Richmond No. 2 1929); Mountain Camp (Camp Mather) 1924; Hayes Valley center 1930 |
| City Planning, *Plan for the location of parks and recreation areas* (1954) | `reportonplanforl1954sanf` | 1855 Western Addition and Potrero squares (incl. Hamilton and McKinley); full 1954 inventory, used as a "first listed" bound |
| Recreation & Park Commission minutes 1947–1995 (with gaps) | `minutesrecreatio{YEAR}sanf`, `minutesrecreati1950sanf_1`, `…1954sanf_0`, `…1956sanf_0`, `…1957sanf_0`, `…1961sanf_0`, `…1962sanf_0` | 1947-bond playground dedications in 1951 (J.P. Murphy, Peixotto, Cow Hollow, Alice Chalmers, Cayuga, Merced Heights, Joseph Lee, South Sunset); the mini-park program of 1968–76 (acquisitions, RP contracts, completion dates); later dedications (Koshland 1977, Hilltop/Ridgetop 1978, Macaulay 1983, SOMA 1990) |
| General Manager's reports, Open Space Acquisition & Park Renovation Fund, 1975–89 | `generalmanagersr1975sanf` | Appendix A "Acquisition/Development Summary 1975–1984/1988": year acquired, block/lot, and status for each Prop J acquisition (Tank Hill, Kite Hill, Diamond Heights lots, Erskine, Duncan & Castro, Edgehill, Golden Gate Heights, Juri, Kelloch-Velasco, Lakeview-Ashton, Macaulay, Monterey Conservatory, Noe & Beaver, Saturn Steps, Coleridge, Washington & Hyde, 6th & Folsom …) |
| GM reports 1992–95; Open Space reports 1996, 1998–2000, draft 2000–01 | `generalmanagersr1992sanf`, `reportonsanfranc1996sanf`, `reportonsanfranc1998sanf`, `draftreportonsan2000sanf` | 1990s natural-area purchases (Rock Outcropping, Hawk Hill, 15th Ave Steps, Parcel 4 = Balboa Natural Area, Palou-Phelps hillside); Tenderloin Rec Center; Woh Hei Yuen; Turk & Hyde; 23rd & Treat; Richmond Rec Center |
| RPD annual reports 1965–67, 1967–70, 1972–77 | `annualreport196567sanf`, `annualreport196770sanf`, `annualreport197277sanf` | Allyne Park; Alice Marble courts; mini parks completed 1972–74 |
| RPD *Plan for Action* (1971) | `planforactionsan1971blyt` | maintenance schedules = list of parks that existed in 1971 |
| RPD facilities list (April 1995) | `sanfranciscorecr1995sanf` | "first listed" proxy (Chestnut & Kearny, LeConte, Presidio Library) and "absent in 1995" bound |

Web sources are cited per row: Wikipedia, Living New Deal, SF RPD facility pages,
SF Planning, FoundSF, Richmond Review/Sunset Beacon, Mission Local, TPL, and the Dogpatch
Neighborhood Association. Many RPD facility pages (`sfrecpark.org/Facilities/Facility/Details/x-<id>`)
were scraped for history paragraphs: Seward ("built 1973"), Fay Park (2006), Argonne
("established 1926"), Dorothy Erskine (1977), and Joe DiMaggio (renamed 2000).

## Doubtful cases (estimated, weakest first)

The following are proxies with no direct date. Each one would be worth replacing with a dated record:

* **No date found. The year is a SLUG-era proxy (1993):** Page Street Community Garden, Park St. Garden,
  Wolfe Lane Community Garden. The city funded gardens from 1974, and SLUG ran from 1983 to 2003.
  These gardens are not in the 1995 RPD list, because SLUG gardens were not listed there.
* **"Not in April 1995 RPD list" proxy (2000):** Portola Open Space, Roosevelt & Henry Stairs.
* **"First listed" proxy:** Chesnut & Kearny Open Space (1995 list), LeConte Mini Park (1995 list as
  "Le Conte Ave. Mini, LeConte/Meade". The 1988 LeConte Ave subdivision park was never built, so
  the polygon's origin is unclear), Coso & Precita (1954 "Coso Park"), DuPont Tennis Courts (1954,
  as "Clement Tennis Courts"), Noe Valley Courts (1954), States Street Playground (1954, "not in
  use"), Fairmont Plaza (1947 minutes, undeveloped), Visitation Valley Playground (1950),
  Bernal Heights Rec Center (1950), Arkansas and Connecticut Friendship Gardens (1982).
  The real dates may be decades earlier.
* **1930s WPA playgrounds dated to the middle of the era:** Cabrillo, Fulton, and Rochambeau
  (1937), and J.P. Murphy (1938, from a WPA progress report). All are school-district land. None is
  in the 1930 Playground Commission list, and the 1954 report says they were developed in the 1930s.
* **Community gardens dated to the 1973–77 garden boom:** Clipper Terrace (KQED: "one of the
  oldest"), White Crane Springs (RPD: "since the 1970s"), Hooker Alley (existed by 1980), and
  Dearborn (planted on a loaned Pepsi lot after the plant closed in the 1970s).
* **Conflicting or thin evidence:**
  * Cottage Row Mini Park (1942): Wikipedia/NRHP says "developed into a park around 1942". The
    Japantown context statement is consistent with that, but it may have become a city park only
    in the 1970s Western Addition A-2 work.
  * St. Mary's Square (1910): the 1950 minutes say it was held under a grant; one secondary source
    says the Catholic diocese donated it in 1910.
  * Presidio Library Mini Park (1911): the Board of Education deeded the block for a playground in
    1911, and the library was built there in 1921.
  * Richmond Recreation Center (1929): "Richmond No. 2" playground from 1929, idle by 1954; a
    99-year lease in 1989 and the new building c.2000. Use 2000 if only the current center counts.
  * Turk & Hyde (2000): RPD reports give a 1997 purchase and construction from spring 2000. A
    2026 Mission Local piece says the park "sprung up around 1968", which the RPD reports do not
    support.
  * Ogden Terrace Community Garden (2025): not built as of Oct 2024.
  * Esprit Park (1982): a private park open to the public; the city has owned it since 2001.
* **Western Addition A-2 mini parks (1975):** Beideman & O'Farrell, Fillmore & Turk, Golden Gate &
  Steiner. The source is "five permanent mini-parks" by the Redevelopment Agency, reported in
  Dec 1975. Which five sites they were is inferred; Bush & Broderick is separately dated 1971.
* **Brotherhood Way mini parks:** Head & Brotherhood (1977, Contract RP 730 on DPW land at
  Brotherhood Way/Bright) and Brotherhood & Chester (1982, Contract RP-941). Matching each
  contract to its polygon is inferred.
* **Others with a dated range:** Hayes Valley Playground (1930, indoor center first), Russian Hill
  Open Space (1958, Halprin plans; owned before 1950), McKinley Square (1855, "laid out at the
  same time" as the 1855 squares), Mt. Olympus (1887 statue), Ina Coolbrith (1911 naming), Joe
  DiMaggio (1904 purchase, 1903 bond), Rowing Club/Dolphin Club (1938 move to Aquatic Park),
  Kidpower Park (2005), and Parque Niños Unidos (2003, from a blog; site bought Dec 1998).

## Renamed parks (former names found)

* North Beach Playground → Joe DiMaggio Playground (2000)
* Spring Valley Playground → Helen Wills Playground (by 1929)
* Folsom Playground (21st & Folsom) → Jose Coronado Playground (1992)
* Portola / University Mound Playground → Palega Playground (1996)
* Longfellow Playground → Alice Chalmers Playground (1950)
* Miley playlot → Cow Hollow Playground (1951)
* Beaver Playground → Sidney Peixotto Playground (1950)
* Byxbee Playground → Merced Heights Playground (1950)
* Burnett playground → Joseph Lee Recreation Center (1950)
* Chinese Playground → Willie "Woo Woo" Wong Playground
* Chinese Recreation Center → Betty Ann Ong Recreation Center
* Bernal Park → Precita Park (1973)
* Lobos Square → Funston Playground → Moscone Recreation Center
* Visitacion Valley Playground → Yik Oi Huang Peace & Friendship Park (2022). The RPD polygon
  still spells it "Visitation Valley Playground".
* Bay View Playground → Bayview K.C. Jones Playground (2003)
* Sunset Heights Park → Golden Gate Heights Park (1982)
* Central City Park → Father Alfred E. Boeddeker Park (1984)
* Arguello Park → Muriel Leff Mini Park
* Martha Hill → Dorothy Erskine Park
* Knudsen-Bloom → Potrero del Sol
* Sixth & Folsom Park → Gene Friend (SOMA) Rec Center
* Hayes Green → Patricia's Green (2006)
* Chester Street Mini Park → Brotherhood & Chester
* Monterey Conservatory → Sunnyside Conservatory
* Palou-Jennings Park → Adam Rogers Park
* Ridgepoint Plaza → Ridgetop Plaza
* "Ridgetop (Hilltop) Park" → Hilltop Park

## Parks that no longer exist, or were absorbed

These are not in RPD today and were not added to `parks.csv`:

* **Southside Playground / Father Crowley Playground** (7th & Harrison/Bryant, 4–6.7 ac). The
  Board of Education leased it in 1901, it was bought with the 1903–04 bond, and it was renamed
  Father Crowley in 1928. The OCR of the 1950 minutes ("sale P.C. P/G … to State of
  California") appears to record its sale to the State (freeway and Hall of Justice area);
  this needs checking. In 1950 the Commission approved renaming Franklin Square "Father Crowley
  Playground".
* **Columbia Square** (SoMa). In 1947, business owners asked to use it for parking. It may be the
  forerunner of the 7th & Harrison / Victoria Manalo Draves area; not verified.
* **Levi Strauss Playlot** (Valencia at Brosnan/14th St). It was supervised by the Playground
  Commission from 1927 and was on private land in 1954.
* **James Lick Playground** (25th & Noe), 1924. Now school grounds.
* **Richmond Tennis Courts / Richmond No. 2** (18th & California), 1929. Idle in 1954; now the site of
  Richmond Rec Center.
* **Bay View playground at 3rd & Jerrold** (Feb 1920, built by volunteers), replaced by the
  3rd/Armstrong site in 1925.
* **1969 mini-park acquisitions** not in today's RPD list: Fitzgerald & Jennings,
  Kirkham & Funston, Balboa & 21st Ave, and Revere & Keith. Also the "Sumner Mini" (1971 list,
  SoMa), the Peru Avenue Walkway (1980–81), the Kearny Street Steps mini park (DPW, 1978–86), the
  Esmeralda Corridor (1978), Campbell-Rutland Mini Park (1971/1977, now inside the Visitacion
  Valley Greenway polygon), and Francisco Reservoir park (Water Department, 1954; now Francisco
  Park, 2022, not in this RPD file).

## Discrepancies noticed in existing rows (not changed)

* **Potrero del Sol** (table: 1981, estimated). The Open Space report says Knudsen-Bloom was
  bought in 1976, and a $2.4 M park was "recently completed … dedicated May 3" in the 1984 GM
  report, so the year is probably 1984.
* **Franklin Square** cites `sanfranciscoparksalliance.org`. That domain now redirects to an
  unrelated site, so the URL should be replaced (e.g. the 1954 report or the Showplace Square
  context statement).
* **Dorothy Erskine Park:** RPD says acquired 1977; the Open Space summary says 1978 (dedicated
  1979). Used 1977.

## 2026-11 audit: greens outside San Francisco, and non-RPD parks in the city

New table `data/tables/region_green_dates.csv` (215 rows): researched opening (and closing)
years for the golf courses, cemeteries, big parks, zoos and regional / state parks of the
five counties. `name` is the Overture / OSM name of the land-use feature and `lon, lat` a
point inside it (names repeat between cities). `pipeline/ground_detail.py` reads it for the
fairways / greens of each course (with the closing year of courses that shut but are still
mapped) and for the park labels; `terrain_tiles.py` should read it for the ground (lead).

* **Golf courses (94 rows, 100 of the 110 mapped features dated with `golf_courses.csv`):**
  GolfLink's city listings give a "Year Opened" per course
  (`https://www.golflink.com/golf-courses/ca/<city>`). They were used where the year is
  plausible and not contradicted; the directory often gives the year of a *remodel* instead
  (Diablo CC 2020, Contra Costa CC 2015, Menlo CC 2022, California GC 2008, Indian Valley 2004,
  Marin CC 2008, Tony Lema 2001, Redwood Canyon 2023, Baylands 2018, Corica 2018 / 2021,
  Castlewood Hill 1923 — before the Hearst estate was sold), so those were researched one by
  one (club histories, Wikipedia, NCGA, golf.com, a 1984 superintendents' newsletter).
  `estimated` = single directory source, or sources 1–2 years apart.
* **Closed or replaced courses still on the map:** Skywest (Hayward, 1964 – Sept 2020), San
  Geronimo (1960s – 2018, now the park features San Geronimo Park / Meadow / Commons),
  Springtown (Livermore, 1966 – Oct 2015, now Springtown Open Space), Lew F. Galbraith
  (Oakland, 1966 – c.1994, rebuilt as Metropolitan Golf Links 2003), Palo Alto Municipal
  (1956, rebuilt as Baylands 2018), Willow Park (1966, renamed Redwood Canyon 2015).
* **Cemeteries (36 rows):** Colma's from the Wikipedia article on the town and the articles
  of each cemetery; the rest from Wikipedia / Wikidata inception dates and the cemeteries'
  own histories. `Planned Heritage Oaks Memorial Park` (111 ha, Coyote Valley) is a proposal
  that has not been built: `year_open = 9999`.
* **Parks (46) and other classes (34: regional, state and national parks that Overture maps
  as nature_reserve / protected_landscape / state_park …, Great America, Fairyland, People's
  Park):** Wikipedia text or Wikidata inception / opening dates; the Overture class is in the
  note of the `other` rows. Fairgrounds have no named Overture outline (2 rows, by name).

Not found / left to the neighbourhood estimate (would be worth a dated source): golf —
Sharon Heights (c.1962), Mariners Point, Montclair, Spartan Golf Complex, the Riverside course
under Coyote Creek's Valley Course, the Thunderbird course under Rancho del Pueblo;
cemeteries — Santa Clara Mission Cemetery, Saint Joseph (San Pablo), Chinese Cemetery (Daly
City), Mission City Memorial Park, Valley Memorial Park (Novato), Memorial Gardens (Concord),
Mount Olivet (San Rafael), Cedar Lawn (Fremont) and the small pioneer / parish graveyards;
parks — Vasona Lake, Hellyer, Lake Cunningham, Sycamore Grove, Miller/Knox, Crown Beach
(state-beach year), Bedwell Bayfront, Byxbee, Mussel Rock, Rinconada, Mitchell, Cuesta,
Rengstorff, Washington Park (Burlingame / Alameda / Sunnyvale), Nicholl, Alvarado, DeFremery,
San Antonio (Oakland), Dimond, Codornices, and the other city parks below ~40 ha; among the
`other` classes Mount Tamalpais SP, Mount Diablo SP (Wikidata's dates are wrong), Angel Island,
Redwood, Las Trampas, Mission Peak, Wildcat Canyon, San Bruno Mountain, Huddart, Edgewood.

San Francisco (`parks.csv`, `golf_courses.csv`):

* Non-RPD parks are matched by their Overture name (`ground.py`): added Candlestick Point
  State Recreation Area (1977), Heron's Head Park (1998), Aquatic Park Historic District
  (1939, estimated), Crane Cove Park (2020), Francisco Park (2022), Presidio Tunnel Tops
  (2022), Sunset Dunes (2025). The Presidio itself is deliberately not a row (its forest is
  dated by `Presidio forest`; a 1994 park row would re-date the woods).
* `Sutro Heights` never matched its outline (Overture: `Sutro Heights Park`): renamed, and
  dated 1883 (gardens opened to the public) instead of 1938 (gift to the city).
* `ground.py` now ignores same-named Overture parks outside the city: Daly City's own
  "Lincoln Park" was drawn from 1909.
* Lincoln Park Golf Course 1902 → 1909: the 1902 layout was three holes on a corner of the
  City Cemetery; the land went to the Park Commission in 1909 (18 holes by 1917).
* Checked and kept: Golden Gate Park 1870, Panhandle, Mountain Lake (1868 reservation;
  Wikipedia "c.1875" design), Lincoln Park 1909, McLaren 1927 (Wikidata 1926 = vote), Glen
  Canyon 1922, Bay View 1915, Precita 1894, Mission Dolores 1905 (Wikidata 1906), South Park
  1852, Washington Square 1847, Pioneer Park 1876, Yerba Buena Gardens 1993, Embarcadero Plaza
  1972, Boeddeker 1985, zoo 1929, Marina Green 1915 (airfield 1920–44 already noted), Harding
  1925, Presidio GC 1895, Golden Gate Park GC 1951, Gleneagles 1962, Sharp Park 1917 / golf 1932.
