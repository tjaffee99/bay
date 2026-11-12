# Buildings read from U.S. Coast Survey plane-table sheets

`<town>_<year>.geojson`: one polygon per building symbol of a T-sheet (1:10,000 field sheets of the 1850s that draw
towns house by house). Built by `data/manual/region_extents/tools/tsheet_houses.py`; method, checks and limits in
`data/manual/region_extents/README.md` ("Oakland before 1890"). Read by `pipeline/region_predecessors.py`
(`tsheet_buildings`).

| file | sheet | buildings |
|---|---|---|
| `oakland_1856.geojson` | T-592, *San Francisco Bay, California, Plane-Table Sheet No. XXIV*, 1:10,000, 1856 (NOAA Historical Map & Chart Collection, `T00592-00-1856`; public domain) | 564 north of San Antonio Creek: Oakland, Clinton, San Antonio (Brooklyn) |

Properties: `id`, `map_year`, `area_m2`, `px` (centre of the symbol on the full-size scan). Outlines are good to
about 10 m; a rectangle where the symbol is one, else its outline.
