"""Sites whose vanished buildings are traced from the USGS sheets (trace_vanished.py).

A target is a site of sites.geojson (its outline, founding and closing years are used) or a
zone of its own: `zone` = rings in the local metre frame of `frame` (lon, lat), read on the
sheet named in the note.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1].parent / "vanished_sites" / "tools"))
import vt  # noqa: E402


def zone(frame, *rings):
    out = []
    for ring in rings:
        lon, lat = vt.loc2ll([p[0] for p in ring], [p[1] for p in ring], *frame)
        out.append(list(zip(map(float, lon), map(float, lat))))
    return out


# ---- Kaiser's Richmond shipyards (Permanente Metals / Kaiser Co., 1941-46). Positions:
# en.wikipedia.org/wiki/Richmond_Shipyards (Yard 1: 700 Wright Ave on the Parr Canal,
# 37°55'15"N 122°21'47"W; Yard 2: north side of the Inner Harbor Basin, 37°54'55"N 122°20'58"W;
# Yard 3: Point Potrero, 37°54'19"N 122°21'55"W; Yard 4: 800 Wharf St, south side of the Santa
# Fe Channel, 37°55'13"N 122°22'19"W). Outlines read on the Richmond 1:24,000 sheet of 1947
# (1946 air photos, field check 1947: the yards as they stood when they closed), in the frame
# below; which building belonged to which yard is by position (ESTIMATED).
RF = (-122.3630, 37.9105)
KAISER_YARD1 = [(-360, 1620), (0, 1620), (0, 1330), (620, 1330), (620, 760), (40, 760), (40, 940), (-280, 940), (-360, 1020)]
KAISER_DOCKS = [(40, 760), (220, 760), (220, 400), (520, 400), (520, -220), (220, -220), (60, 120), (40, 400)]
KAISER_YARD2 = [(220, 740), (1200, 740), (1200, 960), (1720, 960), (1720, 520), (2040, 500), (2040, -220), (680, -220), (680, 400), (220, 400)]
KAISER_YARD3 = [(-740, -680), (0, -680), (0, 20), (-200, 40), (-280, -20), (-320, -20), (-740, -220)]
KAISER_YARD4 = [(-1150, 1240), (-1000, 1400), (-800, 1300), (-460, 1020), (-360, 960), (-600, 780), (-860, 820), (-1040, 960)]

TARGETS = [
    dict(site_id="kaiser_yards_1_2", zone_ll=zone(RF, KAISER_YARD1), label="Kaiser Richmond Shipyard No. 1", founded=1941.0, closed=1946.0),
    dict(site_id="kaiser_yards_1_2b", zone_ll=zone(RF, KAISER_YARD2), label="Kaiser Richmond Shipyard No. 2 and the prefabrication plant", founded=1941.3, closed=1946.0),
    dict(site_id="kaiser_yards_1_2c", zone_ll=zone(RF, KAISER_DOCKS), label="Richmond inner harbor (shipyard docks and shops beside the Ford plant)", founded=1941.0, closed=1946.0),
    dict(site_id="kaiser_yard3", zone_ll=zone(RF, KAISER_YARD3), label="Kaiser Richmond Shipyard No. 3", founded=1942.0, closed=1946.0),
    dict(site_id="kaiser_yard4", zone_ll=zone(RF, KAISER_YARD4), label="Kaiser Richmond Shipyard No. 4", founded=1942.8, closed=1945.6),
    # ---- other sites of sites.geojson whose ground stood empty on the map through their
    # working years (their own outline is the zone; closing years as in sites.geojson / README,
    # given here where the site's ground row runs on to today)
    dict(site_id="marinship", closed=1946.4),        # Marinship, Sausalito: 1942 - May 1946
    dict(site_id="moore_dry_dock", closed=1961.0),   # Moore Dry Dock, Oakland: closed 1961
    dict(site_id="bethlehem_alameda"),
    dict(site_id="basalt_rock_napa"),
    dict(site_id="pullman_richmond"),
    dict(site_id="selby_smelter"),
    dict(site_id="giant_powder"),
    dict(site_id="hercules_powder"),
    dict(site_id="dupont_oakley"),
    dict(site_id="skaggs_island"),
    dict(site_id="bayshore_yard"),
    dict(site_id="sp_oakland_mole", closed=1960.0),  # last train 1960; the train shed came down 1965
    dict(site_id="oakland_army_base", closed=1999.7),
    dict(site_id="camp_stoneman", closed=1954.0),
    dict(site_id="camp_parks"),
]
