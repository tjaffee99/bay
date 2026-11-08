"""Land-cover codes shared by the terrain stages and the viewer
(viewer/src/layers/terrain.ts PALETTE — keep in sync)."""

DEEP, SHALLOW, FLAT, MARSH, BEACH, DUNES, GRASS, SCRUB, OAK, FOREST, FARM, ORCHARD, VINEYARD, PASTURE, \
    SALTPOND, DIKED, URBAN, PARK, ROCK, RIPARIAN, FILL, WETLAND, RESERVOIR, BURNED, SUBURB = range(25)

NAMES = ["deep_water", "shallow_water", "tidal_flat", "tidal_marsh", "beach", "dunes", "grassland", "scrub",
         "oak_woodland", "forest", "farmland", "orchard", "vineyard", "pasture", "salt_pond", "diked_wetland",
         "urban", "park", "rock", "riparian", "fill", "wetland", "reservoir", "burned", "suburban"]

WET = {DEEP, SHALLOW, FLAT, MARSH, RESERVOIR}

# SFEI historical ecology (regional projects, c.1800), field LegLabel
SFEI_ECOLOGY = {
    "Marsh Panne / Salt Flat": MARSH, "Tidal / Salt Marsh": MARSH, "Wet / Alkali Meadow": WETLAND,
    "Tidal Flat": FLAT, "Grassland / Savanna": GRASS, "Grassland": GRASS, "Oak Woodland": OAK,
    "Shallow Water": SHALLOW, "Vernal Pool Complex": GRASS, "Broad Riparian Complex (densely wooded)": RIPARIAN,
    "Broad Riparian Complex (sparsely vegetated)": RIPARIAN, "Marsh": WETLAND, "Chaparral": SCRUB,
    "Beach": BEACH, "Perennial Pond/Lake": RESERVOIR, "Seasonal Pond/Lake": WETLAND, "Rock Outcrops": ROCK,
    "Dune": DUNES, "Deep Water": DEEP, "Lagoon": SHALLOW, "Riverine Open Water": SHALLOW,
}

# SFEI "Hidden Nature SF" (2021), field HabitatCla — pre-colonial northern San Francisco
SFEI_HIDDEN_NATURE = {
    "Coast live oak woodland": OAK, "Dune slack": WETLAND, "Willow grove": RIPARIAN,
    "Stabilized dune/dune scrub/grassland": DUNES, "Wet meadow": WETLAND, "Serpentine maritime chaparral": SCRUB,
    "Serpentine grassland": GRASS, "Coastal scrub": SCRUB, "Coastal prairie": GRASS,
    "Dune-dammed pond or lake": RESERVOIR, "Beach": BEACH, "Maritime chaparral": SCRUB,
    "Sandy/Rocky Intertidal": BEACH, "Tidal marsh": MARSH, "Mobile dunes": DUNES, "Foothill grassland": GRASS,
    "Shallow ocean/bay": SHALLOW, "Tidal flat": FLAT, "Riparian woodland": RIPARIAN, "Coastal bluff scrub": SCRUB,
    "Fen": WETLAND, "Tidal slough": SHALLOW, "Barrier beach-impounded freshwater lagoon": RESERVOIR,
    "California Bay Woodland": OAK, "Coastal prairie/scrub": SCRUB,
    "Serpentine slope wetland/serpentine maritime chaparral complex": SCRUB, "Tidal coastal lagoon": SHALLOW,
    "Deep ocean/bay": DEEP, "Dune-dammed headwater lake": RESERVOIR, "Island": ROCK, "Other pond or lake": RESERVOIR,
}

# SFEI EcoAtlas poster (PDF extraction, data/interim/baylands_1800.geojson), field class
SFEI_POSTER_1800 = {
    "deep_bay": DEEP, "shallow_bay": SHALLOW, "tidal_flat": FLAT, "tidal_marsh": MARSH, "tidal_marsh_pan": MARSH,
    "perennial_pond": RESERVOIR, "lagoon": SHALLOW, "salt_pond": FLAT, "riparian_forest": RIPARIAN,
    "moist_grassland": GRASS, "grassland_vernal_pool": GRASS,
}

LANDCOVER_TABLE = {"dunes": DUNES, "beach": BEACH, "coastal_scrub": SCRUB, "grassland": GRASS,
                   "oak_woodland": OAK, "redwood_forest": FOREST, "chaparral": SCRUB, "marsh": MARSH,
                   "farmland": FARM, "orchard": ORCHARD, "vineyard": VINEYARD, "dairy_pasture": PASTURE,
                   "salt_pond": SALTPOND,
                   # open spaces inside the city (e.g. parade grounds paved / restored)
                   "park": PARK, "lawn": PARK, "paved": URBAN, "lake": RESERVOIR}
