# 1906 fire: burned-area boundary

Files in this folder:

- `fire_1906_boundary.csv`: the outer ring of the burned district. It has 106 vertices, runs clockwise, and starts on the NE waterfront at East St (now The Embarcadero) and Filbert. Columns are `seq,street_a,street_b,note,source_url`.
- `fire_1906_unburned_islands.csv`: unburned areas inside the burned district, one ring per `island`, all clockwise.

## Conventions

- Street names are present-day names as spelled in the DataSF street centerlines ("Streets – Active and Retired", `3psu-pn9h`). Examples: `The Embarcadero`, `South Van Ness Ave`, `Duboce Ave`, `Clinton Park`, `Delancey St`. Every `street_a`/`street_b` pair resolves to an existing intersection in that dataset; I checked this. Where a 1906 name differs (East St, Howard St in the Mission, 13th St, First St south of Bryant, Kearney), the `note` says so.
- Some 1906 corners fall mid-block, or at an intersection that no longer exists. Examples are former Octavia St between Fulton and Golden Gate, Juniper St at Bryant, and Fremont St south of Harrison. For these rows the street pair is the nearest existing intersection, and the `note` starts with `@lat,lon`. That coordinate is the true vertex, interpolated from the DataSF centerlines. Regex: `^@(-?\d+\.\d+),(-?\d+\.\d+)`.
- Build the polygon from the `@` coordinate where one is given, and from the intersection otherwise. If you use intersections only, some consecutive rows repeat the same intersection, so drop the duplicates. That polygon is also coarser, by up to about 150 m near Octavia/McAllister, Rincon Hill and 7th–8th St.
- The waterfront edge uses present-day Jefferson St and The Embarcadero as a stand-in for the 1906 shoreline and seawall. Some land beyond it is later fill.
- The Telegraph Hill summit and its east/south slopes are not an island. They join the saved waterfront, so they appear as a notch in the outer ring (seq 93–106). Rincon Hill (seq 7–16) is handled the same way.

## Sources

1. **Official boundary description**, transcribed by the SF Fire Department Museum: <https://www.guardiansofthecity.org/sffd/fires/great_fires/1906/fire_boundry.html>. This is a turn-by-turn perimeter ("South to Beach, West to Taylor…"), plus a separate description of the saved Russian Hill district. It is the **primary source** for both CSVs. The same page reprints the *Los Angeles Herald* of 24 Apr 1906, whose reporter drove the perimeter (26 miles on the odometer) and named the unburned Jackson/Washington/Montgomery/Battery block.
2. **L. J. Kennedy, "The Progress of the Fire in San Francisco, April 18th–21st, 1906"** (UC master's thesis, 1908): <https://sfmuseum.org/1906/kennedy.html>. It gives a narrative of where and why each line held (Van Ness, Franklin, Octavia, Dolores, 20th St, Capp St, Clinton Park) and is used for the notes.
3. **R. J. Waters & Co. 1906 map**, "San Francisco, California, showing the areas destroyed by fire, April 18–21, 1906" (Harvard Map Collection, about 1:21,000). DataSF digitized it as "Areas Damaged by Fire Following 1906 Earthquake": <https://data.sfgov.org/d/yk2r-b4e8>, GeoJSON at `https://data.sf.gov/resource/ff3a-iqhv.geojson`. I used it as an **independent cross-check**. My ring overlaps it with IoU 0.956, and its outer area is 2,552 acres against 2,569 for my ring. The largest gap is about 140 m, at Kearny/Chestnut. Its four holes match the Russian Hill, Jackson Square, Mint and Post Office islands. Its two tiny Mission holes are included as low-confidence islands.
4. Also consulted at catalog level only (not traced): the State Earthquake Investigation Commission atlas map "Map of the city of San Francisco showing the streets and the burnt area, 1906" (Britton & Rey, 1908), <https://davidrumsey.com/maps1151064-31133.html>, and the California Promotion Committee map of 1908, <https://www.loc.gov/item/2006626079/>.

## Headline figures (sources disagree)

| Measure | Value | Source |
|---|---|---|
| Area | 4.7 sq mi (quoting NOAA) | USGS, <https://earthquake.usgs.gov/earthquakes/events/1906calif/18april/casualties.php> |
| Area | 2,560 acres (= 4.0 sq mi); 497 blocks | Rep. Julius Kahn, 1906 speech, <https://guardiansofthecity.org/sffd/fires/great_fires/1906/kahn_speech.html> |
| Area | 2,831 acres; "more than 490 blocks" | Exploratorium, <https://annex.exploratorium.edu/fault-line/great/1906/1906_13.html> |
| Blocks / buildings | 490 blocks; about 25,000 buildings | Wikipedia, <https://en.wikipedia.org/wiki/1906_San_Francisco_earthquake> |
| Buildings destroyed | 28,188 (24,671 wood, 3,168 brick, "by one count"); headline 28,000 | USGS (link above) |
| Homeless | 225,000 of about 400,000 | USGS (link above) |
| **Measured from these CSVs** | outer ring 2,569 acres, minus 21.5 acres of islands = **about 2,548 acres (3.98 sq mi)** | computed (equirectangular projection) |
| Measured from DataSF/Waters | 2,544 acres net (`shape_area` 110,827,955 sq ft) | DataSF |

Both polygon measurements agree with Kahn's 2,560 acres. The widely quoted 4.7 sq mi (about 3,000 acres) is roughly 18% larger than any traced polygon, and its derivation is undocumented.

## Confidence by section

| Section (seq) | Confidence | Notes |
|---|---|---|
| Van Ness firebreak, Golden Gate to Filbert, and the Franklin lobe between Sutter and Clay (63–68) | High | Official text, Kennedy, LA Herald and Waters agree. Kennedy's summary says "Sutter to Sacramento" once, but his narrative says Clay. |
| North edge: Polk/Greenwich/Hyde/Chestnut/Jones/Bay/Taylor (69–86) | High for main lines, medium for the ¼–⅙-block stair-steps | The LA Herald's variant (Larkin to Lombard) was rejected because the official text and Waters agree on Greenwich to Hyde. |
| North waterfront (86–92) | Medium | The 1906 shoreline is approximated by present streets. |
| Telegraph Hill notch (93–106) | Medium | The official text is garbled between Filbert and Union, so Waters was followed there. Waters puts the Lombard/Chestnut corner at Montgomery, not Kearny. |
| East waterfront and Rincon Hill (1–16) | Medium | A small East/Pacific/Drumm notch is omitted. Fremont and First St south of Harrison now lie under the Bay Bridge approach. |
| SoMa south edge: Townsend, 8th, Bryant, Harrison (17–28) | Medium-high | Sources differ by about ½ block at 7th–8th St and around Juniper St. |
| Mission: 14th–15th, South Van Ness, Capp, 20th, Dolores (29–46) | High for main lines | Waters places the Capp-to-Mission mid-block line about ½ block further west (San Carlos St). Only one lobe crossed 20th St: the Harney building at Valencia. |
| Hayes Valley: Gough, Octavia, Ash/Fulton lobe, Locust jog (47–62) | Medium | The text places the lobe west of Octavia north of Fulton, at the former Ash Ave. Waters shows it south of Fulton. Octavia St itself is gone between Fulton and Golden Gate. |

## Islands

| `island` | Confidence | Source and notes |
|---|---|---|
| `russian_hill` | High (traced) | Detailed official description. The houses are named in the LA Herald. |
| `jackson_square` | Medium | LA Herald rectangle (Montgomery, Battery, Jackson, Washington), which takes in the Appraisers' Building and the Hotaling warehouses. I added a bump for the Montgomery Block on the SE corner of Montgomery & Washington. Waters extends it south to Merchant St between Sansome and Battery; I did not adopt that. |
| `us_mint` | High location, approximate footprint | Old Mint, 5th & Mission. |
| `post_office_7th_mission` | High location, approximate footprint | 1905 Post Office/Courthouse, NE side of 7th St at Mission. |
| `waters_spot_15th_guerrero`, `waters_spot_14th_guerrero` | Low | Unidentified spots of about 0.3–0.4 acre that appear only on the Waters digitization. Fine to drop. |

## Not captured

Individual surviving buildings that were gutted, such as the Fairmont and the Call Building, are not islands. The fire perimeter at intermediate times (April 18–20) is also not in these files. Kennedy's narrative supports time steps if needed.
