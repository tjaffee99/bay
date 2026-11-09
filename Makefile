# Bay Area Through Time — build targets. Each pipeline stage is idempotent and
# caches its outputs (data/raw, data/interim); delete an output to force a rebuild.

PY := .venv/bin/python
P  := cd pipeline &&

.PHONY: setup sf download land fire overture join buildings predecessors export trees ground terrain baylands grid tiles roads transit ground-detail region-download region region-trees airports dev build deploy shots clean-interim

setup:
	python3 -m venv .venv
	$(PY) -m pip install -q -r pipeline/requirements.txt
	cd viewer && npm install

# ---- San Francisco ---------------------------------------------------------
sf: download land fire overture join buildings predecessors export trees ground transit roads ground-detail

download:
	$(P) ../$(PY) download_sf.py

overture:
	$(P) ../$(PY) download_overture.py

land: download
	$(P) ../$(PY) land.py

fire: download
	$(P) ../$(PY) fire_1906.py

join: download
	$(P) ../$(PY) sf_join.py

buildings: join overture fire
	$(P) ../$(PY) sf_buildings.py

# Phase 3: the pre-1906 city and the houses today's buildings replaced (procedural
# massing on real lots inside researched built-up extents)
predecessors: buildings
	$(P) ../$(PY) sf_predecessors.py

export: buildings predecessors grid
	$(P) ../$(PY) sf_export.py

trees: buildings
	$(P) ../$(PY) trees.py

ground: download overture
	$(P) ../$(PY) ground.py

# BART + Muni: tracks (Overture rail), stations, service lines for the trains
# (BART GTFS, SFMTA patterns/stops from DataSF); roads.py hands those lines over to it
transit: overture grid
	$(P) ../$(PY) transit.py

# streets (DataSF centerlines dated by the extent snapshots / first buildings),
# region roads (Overture), historic routes (data/manual/routes.csv)
roads: download overture grid transit
	$(P) ../$(PY) roads.py

# golf fairways / greens / bunkers, pitches, tracks, playgrounds, gardens (Overture
# land_use outlines draped on the terrain) + park labels
ground-detail: export
	$(P) ../$(PY) ground_detail.py

# runways / taxiways / aprons (Overture base/infrastructure) from each airport's researched
# opening year (data/tables/airports.csv); airport outlines turn the terrain to airfield grass
airports: grid
	$(P) ../$(PY) airports.py

# ---- five counties around SF (Phase 5): Overture footprints + assessor / survey years
# (data/research/region_buildings.md), z13 building tiles (not committed, shipped by deploy)
region-download:
	$(P) ../$(PY) download_region.py all

region: grid
	$(P) ../$(PY) region_buildings.py

# street / park tree inventories of the cities (SOURCES.md `region_trees`), dated by DBH and
# the buildings along the street -> z12 tiles viewer/public/data/region-trees/ (not committed)
region-trees: grid
	$(P) ../$(PY) region_trees.py all

# ---- terrain: elevation + time-varying land cover tiles (whole Bay Area) -----
terrain: baylands grid tiles

baylands:
	$(P) ../$(PY) baylands_pdf.py

grid: baylands
	$(P) ../$(PY) terrain_grid.py

tiles: grid fire airports
	$(P) ../$(PY) terrain_tiles.py

# ---- viewer ----------------------------------------------------------------
dev:
	cd viewer && npm run dev

build:
	cd viewer && npm run build

# Publish viewer/dist to the gh-pages branch, served at https://bay.theojaffee.net
# (viewer/public/CNAME). The branch holds one generated commit, replaced on each
# deploy, so built data doesn't pile up in history. The git metadata lives in a
# fresh temp dir; nothing in the repo is touched.
DEPLOY_URL = $(shell git remote get-url origin)
DEPLOY_SHA = $(shell git rev-parse --short HEAD)

deploy: build
	cd viewer/dist && export GIT_DIR=$$(mktemp -d) GIT_WORK_TREE=. && \
	  git init -q -b gh-pages && git add -A && \
	  git commit -q -m "Deploy $(DEPLOY_SHA)" && \
	  git push -f $(DEPLOY_URL) gh-pages

clean-interim:
	rm -rf data/interim/*
