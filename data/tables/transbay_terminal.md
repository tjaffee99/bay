# Transbay Terminal (1939–2010/11) and its Bay Bridge loop ramps

Landmark id in `data/tables/landmarks.csv`: `transbay_terminal_1939`. Ramp and loop rows in `data/manual/routes.csv`: `transbay_terminal_loop`, segments 1–4. Rail service across the bridge itself is the route `bridge_railway`.

## Dates

| Event | Date | Source |
|---|---|---|
| Construction bids | June 1937 | [WP: San Francisco Transbay Terminal][wp] |
| Excavation begins | 1937-07-29 | [wp] |
| First steel erected | 1938-01-12 | [wp] |
| Structural concrete complete | May 1938 | [wp] |
| Ceremonial first train across the bridge | 1938-09-23 | [wp] |
| Terminal formally dedicated | 1939-01-14 | [wp] |
| Regular trains begin (Key System, SP Interurban Electric, Sacramento Northern) | 1939-01-15 | [wp]; [Key System][key] |
| Interurban Electric and Sacramento Northern end | 1941-07-26 (IER) and 1941-07-01 (SN passenger service) | [IER][ier]; [SN][sn] |
| Last Key System train | 1958-04-20 | [wp] |
| Tracks removed and terminal rebuilt for buses. All lines were using the rebuilt terminal by 1959-07-12, and Greyhound arrived 1960-02-01. | 1958–59 | [wp] |
| Muni streetcars use the loop in front of the building. The F line served it from 1995 until its last trip on 2000-03-03. | 1939–1982, 1995–2000 | [wp] |
| Damaged in the Loma Prieta earthquake | 1989-10-17 | [landmarks.md](../research/landmarks.md) |
| Last bus departs, moved to the Temporary Transbay Terminal | 2010-08-07 | [wp] |
| Demolition by wrecking ball begins | December 2010 | [wp] |
| Demolition declared complete | 2011-09-07 | [wp] |
| Successor, the Salesforce Transit Center, opens | 2018-08-12 | [wp] |

The brief says the terminal "opened 15 Jan 1939". That is the date regular train service began. The formal dedication was the day before, 14 Jan 1939.

## Location and footprint

- **Address**: 425 Mission Street. The building occupied land from Mission Street on the north to Natoma Street on the south, and it straddled both Fremont and First streets ([TJPA EIR §5.14][tjpa]). Wikipedia describes the site as "roughly in the center of the rectangle bounded north–south by Minna Street and Natoma Street, and east–west by Beale Street and 2nd Street" ([wp]). Minna Street is absent from the DataSF centrelines between First and Beale, which fits a building covering it.
- **Length**: a 1991 TRB history gives a designed length of **870 ft (265 m)**. It also says the building was split by Fremont and First streets into an east unit, a center unit and a west unit, quoting the east and west units as **164 ft** wide and the center unit as **197 ft**. This comes from search-engine OCR of [Transportation Research Record 1308, "Short History of the Transbay Transit Terminal"][trr], and the OCR is garbled. I could not open the PDF (HTTP 500), so **verify these figures**. They do not add up to 870 ft once the two street widths are included. That suggests the unit figures are measured on another axis or are misread.
- **Street geometry** (DataSF centrelines):
  - Mission & 1st to Mission & Fremont: 110 m.
  - Fremont to Beale: 109 m.
  - 2nd to 1st: 276 m.
  - Mission to Natoma, measured perpendicular: 125 m.
  - Mission Street runs at a bearing of about 45°, SW to NE.
- **Estimated footprint polygon** (LOW CONFIDENCE). The length is 870 ft, centred on the 1st–Fremont block, so the building runs from about 77 m west of First to about 77 m east of Fremont. The depth runs from the south curb of Mission to the north curb of Natoma, about 107 m. In HAER photo CA-32-71 the roof looks narrower than that, roughly 85–100 m, so treat the depth as an upper bound.
  `-122.398094 37.789193; -122.395969 37.790870; -122.395109 37.790184; -122.397234 37.788507` (closed ring). The centroid is about 37.78969, -122.39660, which matches the placeholder in `landmarks.csv` (37.7895, -122.3964).
- The old building sat on the north-eastern part of today's Salesforce Transit Center block. The new centre is about 1,400 ft long and runs from 2nd to Beale.

## Massing, structure and appearance

- **Architects**: Timothy L. Pflueger, Arthur Brown Jr. and John J. Donovan, in the Art Moderne style ([wp]; [tjpa]). Its official name was the "San Francisco–Oakland Bay Bridge Electric Railway Terminal Building".
- **Levels**:
  - Street level, with the Mission St concourse and the Muni streetcar loop in front of the building.
  - A mezzanine. A ramp or "hump" brought Muni streetcars up to the front mezzanine level ([trr] OCR).
  - A **third-floor track level that extends over the entire structure**, with enclosed ramps and stairs to every platform ([trr] OCR).
  - There were six tracks on that level ([wp]). After 1959 the track level was paved as a bus deck.
- **Height** (ESTIMATE, from photos): track or bus deck about 12–15 m above the street, high enough to clear First and Fremont streets. Long platform canopies rise about 6–8 m above the deck, so the overall height is about 20–23 m. From the street the building reads as a 3–4 storey block.
- **Roof**: HAER photo CA-32-130 shows the view at ramp level. Long, low gabled or monitor-roofed platform sheds run east–west over the deck. They are clad in corrugated sheet with light skylight bands and stand on concrete or steel columns. Concrete parapets and pipe railings line the ramp edges, and a concrete portal frame spans the ramp entrance. In the aerials (CA-32-70 and -71) the roof reads as one long, light, flat-topped slab.
- **Structure**: reinforced concrete. Where ramps cross city streets the spans are steel girders on concrete or steel bents ([HAER CA-32 data pages][haer], p. 15).
- **Colours**: all the reference photos found are black and white. The exterior reads as light grey or buff concrete. This is not verified in colour, so check the Commons colour photos listed below.
  - Key System "bridge units" were orange and silver until 1946, then National City Lines yellow and green ([Key System][key]).
  - SP Interurban Electric cars were the "red trains".

## Train/bus loop ramps (alignment)

Facts from the [HAER CA-32 data pages][haer] (pp. 14–15 and 31) and the photo captions:

- Trains came off the Bay Bridge lower deck between First and Second streets, looped through the terminal and went back onto the bridge.
- The loop is a **3,439 ft elevated structure of riveted steel girders on concrete and steel bents**, about two-thirds of a mile including its approaches.
- In the late 1950s the ramps were widened for buses.
- The TJPA EIR calls the loop ramp "two of the six approach spans that remain from the original SFOBB project". It was demolished in 2010–11.
- The HAER photo captions place the loop:
  - over Natoma Street and over Howard Street, both between First and Second;
  - over Fremont Street;
  - over Beale Street between Folsom and Howard;
  - over Howard Street north-east of Beale;
  - "near Folsom Street", and at a "split" near Second Street, where the ramp joins the lower-deck on-ramp.

Reconstructed loop, traced from those captions and from HAER aerials CA-32-70 and -71 (LOW CONFIDENCE, ±30 m):

1. The terminal's west end is just west of First, between Minna and Natoma.
2. The loop runs south over Natoma and Howard between First and Second.
3. It turns east between Howard and Folsom, crossing First and Fremont.
4. It curves north over Beale (between Howard and Folsom) and over Howard north-east of Beale.
5. It enters the terminal's east end, between Fremont and Beale.
6. A connector leaves the loop's south-west corner near Second and Folsom and drops to the bridge lower deck between First and Second, near Harrison.

The vertices are computed from DataSF intersections in `routes.csv`:

| Rows | Content | Era |
|---|---|---|
| `transbay_terminal_loop` segments 1–2 | loop and connector | `key_system`, 1939–1958 |
| `transbay_terminal_loop` segments 3–4 | the same structure | `highway` (buses), 1959–2010 |

There were also upper-deck auto ramps nearby, which were not part of the terminal ([HAER][haer] p. 14):

- an on-ramp from First St between Howard and Folsom;
- an off-ramp to Fremont St at Harrison;
- truck access to the lower deck from Harrison between First and Second.

## Reference photos

Downloaded to `data/raw/reference_photos/transbay_terminal_1939/`, with author, licence and caption in `_meta.jsonl`. All are public-domain HAER photos from the Library of Congress, and I looked at each one.

- `HAER_CA-32-71.jpg`, Frank Deras Jr., June 1998. Aerial looking NW: the long flat-roofed terminal straddling First St, the elevated bus loop in the foreground running between Howard and Folsom, and both curved ends rising into the terminal. **This is the best massing reference.**
- `HAER_CA-32-70.jpg`, Frank Deras Jr., July 1998. High aerial looking NE: terminal, loop and Bay Bridge, which shows how the ramps relate to the bridge approach.
- `HAER_CA-32-130.jpg`, Dennis Hill, April 1998. Ramp-level view into the terminal looking west: platform sheds, parapets, portal frame.
- `HAER_CA-32-66_sf_approach_aerial.jpg`, Frank Deras Jr., July 1998. Context for the SF approach viaduct, anchorage and ramps.

Colour photos on Wikimedia Commons could not be downloaded because Commons returned HTTP 429 (rate limited). Author and licence come from the Wikipedia API:

- [File:Transbayterminalbusdeck.png](https://commons.wikimedia.org/wiki/File:Transbayterminalbusdeck.png). John Nagle, CC BY-SA 3.0, 2010-08-01. Shows the bus deck a week before closing.
- [File:Transbay Terminal Demolition - with wrecking ball (5235388469).jpg](https://commons.wikimedia.org/wiki/File:Transbay_Terminal_Demolition_-_with_wrecking_ball_(5235388469).jpg). David Brossard, CC BY-SA 2.0, 2010-12-04.
- [File:Ex-Kobe streetcar 578 turning into SF Transbay Terminal in 1987.jpg](https://commons.wikimedia.org/wiki/File:Ex-Kobe_streetcar_578_turning_into_SF_Transbay_Terminal_in_1987.jpg). Steve Morgan, CC BY-SA 4.0, 1987-09-28. Shows the Mission St front and the streetcar loop.
- 1939 views: the Dorothea Lange photo of a Key System train on the terminal ramp, 1939 (FSA, Library of Congress, linked from [Key System][key]); and keyrailpix "Key System Train Inside Transbay Terminal 1/15/39" (linked from [wp]). Neither is downloaded, and the keyrailpix licence is unknown.

## Open questions and next steps

- Get exact plan dimensions from HAER CA-32 drawing sheet 2 ("Key Plans") or Detail 1 ("San Francisco Approach"), at <https://www.loc.gov/item/ca1352/>, which has 20 measured drawings. Another option is the TJPA 2004 EIR/EIS Section 4.16 (historic resources), which may hold HABS-level documentation of the terminal itself; its demolition required HABS/HAER recording, per the FRA Record of Decision of 2010.
- Check the TRB 1991 figures (870 ft; 164/197/164 ft) against the PDF once it is reachable.
- Get colours from the Commons colour photos above.

[wp]: https://en.wikipedia.org/wiki/San_Francisco_Transbay_Terminal
[key]: https://en.wikipedia.org/wiki/Key_System
[ier]: https://en.wikipedia.org/wiki/East_Bay_Electric_Lines
[sn]: https://en.wikipedia.org/wiki/Sacramento_Northern_Railway
[tjpa]: https://www.tjpa.org/media/30677/download
[trr]: https://onlinepubs.trb.org/Onlinepubs/trr/1991/1308/1308-015.pdf
[haer]: https://tile.loc.gov/storage-services/master/pnp/habshaer/ca/ca1300/ca1352/data/ca1352data.pdf
