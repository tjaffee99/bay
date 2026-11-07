# Bay Area Through Time — build targets. Each pipeline stage is idempotent and
# caches its outputs (data/raw, data/interim); delete an output to force a rebuild.

PY := .venv/bin/python
P  := cd pipeline &&

.PHONY: setup sf download land fire overture join buildings export trees dev build shots clean-interim

setup:
	python3 -m venv .venv
	$(PY) -m pip install -q -r pipeline/requirements.txt
	cd viewer && npm install

# ---- San Francisco ---------------------------------------------------------
sf: download land fire overture join buildings export trees

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

export: buildings
	$(P) ../$(PY) sf_export.py

trees: download
	$(P) ../$(PY) trees.py

# ---- viewer ----------------------------------------------------------------
dev:
	cd viewer && npm run dev

build:
	cd viewer && npm run build

clean-interim:
	rm -rf data/interim/*
