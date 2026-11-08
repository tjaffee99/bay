# Bay Area Through Time — build targets. Each pipeline stage is idempotent and
# caches its outputs (data/raw, data/interim); delete an output to force a rebuild.

PY := .venv/bin/python
P  := cd pipeline &&

.PHONY: setup sf download land fire overture join buildings predecessors export trees ground terrain baylands grid tiles roads dev build deploy shots clean-interim

setup:
	python3 -m venv .venv
	$(PY) -m pip install -q -r pipeline/requirements.txt
	cd viewer && npm install

# ---- San Francisco ---------------------------------------------------------
sf: download land fire overture join buildings predecessors export trees ground roads

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

# streets (DataSF centerlines dated by the extent snapshots / first buildings),
# region roads (Overture), historic routes (data/manual/routes.csv)
roads: download overture grid
	$(P) ../$(PY) roads.py

# ---- terrain: elevation + time-varying land cover tiles (whole Bay Area) -----
terrain: baylands grid tiles

baylands:
	$(P) ../$(PY) baylands_pdf.py

grid: baylands
	$(P) ../$(PY) terrain_grid.py

tiles: grid fire
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
