# ports_tools — industrial-waterfront tracing (landmarks `ports.ts`)

One-off research tools behind `viewer/src/landmarks/ports-yards.ts` and `data/manual/airports_extra.geojson`
(see `data/research/landmarks_ports.md`). Inputs are cached in `data/raw/ports/` (or `$PORTS_CACHE`):
OpenStreetMap API extracts (`oak_port_w.osm` = bbox -122.345,37.795,-122.29,37.832; `alameda_point.osm` =
-122.335,37.768,-122.285,37.795), `port_polys.json` (the OSM `industrial=port` terminal polygons, way id:name
→ lon/lat ring) and Esri World Imagery tiles (viewed only, never committed).

* `yard.py <key> lonA latA lonB latB <osm way ids> <nmin> out.json` — container stacks on a terminal yard.
* `compile_yards.py out.ts key=yard.json …` — compact TS module with procedural heights.
* `airfield.py out.geojson "Naval Air Station Alameda" debug.png` — runway / taxiway / apron polygons.
* `osmparse.py` — minimal OSM XML reader.
