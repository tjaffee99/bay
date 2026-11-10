"""agriculture.geojson: where farms, orchards and vineyards were, and when.

Three kinds of evidence, best first:

  1. USGS 1939-56 topographic maps (green orchard dots / vineyard screen), extracted by
     pipeline/topo_farmsteads.py -> data/manual/farmsteads/topo_orchards.geojson (read-only
     here): exact orchard / vineyard extents just before the post-war suburbs.
  2. Broek (1932), "Landscape types of the Santa Clara Valley 1931" (traced by
     landscape_broek.py): orchard formation / orchards mixed with small crops / small crops /
     pastures, Palo Alto to Hollister.
  3. Farm districts (one per valley / township, seeds below) with researched eras - grazing,
     wheat, hay, dairies, vineyards, orchards, truck crops - painted on the valley-floor
     geology (USGS Quaternary maps: Holocene fans and levees = the well-drained loams of the
     wheat belt and later the orchards; basin clays near the bay = 'adobe' pasture, hay and
     dairies; Pleistocene upper fans = the gravelly foothill belt of the 1870s-90s vineyards).
     Geometry follows the real valley floors; dates and crops are researched per district;
     the district boundaries themselves are straight (Voronoi cells of the seeds) and
     ESTIMATED.

Ten-county extension (2026-11): districts for Sonoma, Napa, Solano, Santa Cruz, the Delta and
the Montezuma Hills carry a list of further eras ("eras": hops, prunes, apples, poultry, row
crops ... each on named soil classes with a share), today's vineyards and orchards come from
OpenStreetMap (layer osm_today: real outlines, dated by the district's replanting era), and
where no Quaternary map exists (Santa Cruz County) or the farm belt lies on low hills mapped as
bedrock (Gold Ridge, Montezuma Hills) the ground is data/manual/landscape/valley_floor_extra.geojson
(ESTIMATED from the terrain grid).

Each output feature is one (place, era): kind, crop, year_start, year_end (empty = until
urbanised), year_full (the conversion was complete by then: spread the start of each cell
between year_start and year_full), share (fraction of the cells to paint; the rest keeps the
previous era), layer, district, confidence, source, source_url, note.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import MultiPoint, Point, Polygon, box

from common import INTERIM, MANUAL, OVERTURE_RELEASE, RAW, log
from landscape import M, OUT, explode_polys, knudsen2000, witter2006, write_geojson
from landscape_broek import broek_1931

# --------------------------------------------------------------------------- valley-floor geology
FAN = {"Qhf", "Qhf1", "Qhf2", "Qhf3", "Qhf?", "Qhfy", "Qhl", "Qhl1", "Qhl2", "Qhl3", "Qhly", "Qht", "Qht1",
       "Qht2", "Qhty", "Qhty1", "Qhty2", "Qha", "Qha?", "Qhay", "Qa", "Qa?", "Qf", "Qbt", "Qbt?"}
UPPER = {"Qpf", "Qpf1", "Qpf2", "Qpf?", "Qof", "Qof?", "Qof2", "Qoa", "Qoa1", "Qoa2", "Qoa?", "Qpa", "Qpa?",
         "Qop", "Qot", "Qot1", "Qot2", "Qpt", "Qpt?", "Qt", "Qmt", "Qmt1", "Qmt2", "Qmt2?", "Qmt3", "Qmt4",
         "Qmt4?", "Qmt?"}
BASIN = {"Qhb", "Qb", "Qhff", "Qhfe", "Qhed", "Qhdm", "Qhfb", "Qhfp"}


def soil_of(p):
    p = str(p)
    if p in FAN:
        return "fan"
    if p in UPPER:
        return "upper_fan"
    if p in BASIN:
        return "basin"
    return None


def wet_1800():
    b18 = gpd.read_file(INTERIM / "baylands_1800.geojson").to_crs(M)
    return shapely.union_all(list(b18[b18["class"].isin(["deep_bay", "shallow_bay", "tidal_flat", "tidal_marsh",
                                                         "tidal_marsh_pan", "salt_pond", "lagoon"])].geometry.simplify(10)))


def valley_floor() -> gpd.GeoDataFrame:
    w = witter2006()
    k = knudsen2000()
    w = w.assign(soil=w.PTYPE.map(soil_of))
    # artificial fill over a natural unit counts as that unit (towns on fans)
    fill = w.soil.isna() & w.PTYPE.astype(str).str.startswith("a")
    w.loc[fill, "soil"] = w.loc[fill, "PTYPE2"].map(soil_of)
    w = w[w.soil.notna()]
    foot = shapely.union_all(list(witter2006().pipe(lambda d: d[d.PTYPE != "nm"]).to_crs(M).geometry.simplify(50)))
    k = k.assign(soil=k.PTYPE.map(soil_of))
    k = k[k.soil.notna()].to_crs(M)
    k = k[~k.geometry.representative_point().within(foot)]
    g = pd.concat([w.to_crs(M)[["soil", "geometry"]], k[["soil", "geometry"]]], ignore_index=True)
    g["geometry"] = g.geometry.simplify(25)
    # farm ground the Quaternary maps do not give: Santa Cruz County (not mapped in OF 00-444) and two
    # belts on low hills mapped as bedrock (Gold Ridge, Montezuma Hills) - ESTIMATED outlines from the
    # terrain grid, only where the geology gives no valley floor (valley_floor_extra.geojson, README)
    xp = OUT / "valley_floor_extra.geojson"
    if xp.exists():
        x = gpd.read_file(xp).to_crs(M)[["soil", "geometry"]]
        have = shapely.union_all(list(g.geometry.buffer(0)))
        x["geometry"] = x.geometry.buffer(0).difference(have)
        x = x[~x.geometry.is_empty]
        log(f"valley floor: + {len(x)} estimated outlines (valley_floor_extra.geojson)")
        g = pd.concat([g, x], ignore_index=True)
    g = g.dissolve("soil", as_index=False)
    # not on the c.1800 baylands (marsh, flats, bay, natural salt ponds): diked baylands are in
    # water_history.csv; causeway / bridge fills over the bay are not farmland
    g["geometry"] = g.geometry.difference(wet_1800())
    g = g.explode(index_parts=False)
    g = g[g.area > 5e4].reset_index(drop=True)   # >= 5 ha
    log("valley floor (km2): " + str(g.assign(a=g.area / 1e6).groupby("soil").a.sum().round(0).to_dict()))
    return g


# --------------------------------------------------------------------------- districts
BROEK = "https://dspace.library.uu.nl/handle/1874/302720"
LAFCO = "https://www.acgov.org/lafco/documents/AgHistory.pdf"
COCO = "https://www.cocohistory.org/contra-costa-county-history"
W = "https://en.wikipedia.org/wiki/"

# eras per district: grain = wheat / barley on the fans; basin = what the clay lowland was;
# orchard = (start, full) of the change to orchards on land that was orchard by 1931/1948;
# vine = (start, end, share) vineyards on the upper fans; veg = start of truck crops on Broek's
# 'small crops' / the basin; extra = special crops on hand-drawn rings (see SPECIAL)
D = {
    # ---- Santa Clara Valley (Broek 1932 unless noted)
    "scv_san_jose": dict(seed=(-121.915, 37.335), county="Santa Clara", grain=(1852, 1858), basin=("pasture_dairy", 1853),
                         orchard=(1872, 1890), veg=1868, src=BROEK,
                         note="Wheat and barley on the Yolo loams around Santa Clara and San Jose from the early 1850s (first "
                              "artesian well 1854); ~1,100 acres of orchard here by 1863, 'the Willows' south of San Jose cleared "
                              "for strawberries 1863 and planted to fruit trees 1868 - the first orchard district; general "
                              "conversion 1875-90 (by 1890 orchards ~ wheat, 19,000 acres each, county-wide)."),
    "scv_campbell_los_gatos": dict(seed=(-121.965, 37.265), county="Santa Clara", grain=(1853, 1860), basin=("pasture_dairy", 1855),
                                   orchard=(1878, 1895), vine=(1872, 1900, 0.35), src=BROEK,
                                   note="First foothill orchard 1875 near Los Gatos on land cleared of chaparral; the gravelly "
                                        "upper fans were vineyards from the late 1860s-70s, replaced by fruit trees after "
                                        "phylloxera c.1900."),
    "scv_west": dict(seed=(-122.06, 37.36), county="Santa Clara", grain=(1853, 1862), basin=("pasture_dairy", 1855),
                     orchard=(1886, 1905), vine=(1872, 1902, 0.35), src=BROEK,
                     note="Mountain View - Sunnyvale - Cupertino - Los Altos - Saratoga: wheat 1850s-80s (the Sunnyvale "
                          "site long stayed part of Murphy's stock ranch); 'foothill' grape belt on the Stevens / Permanente "
                          "fans by 1872; prunes and apricots from 1886 (dried-prune success), mostly planted in the 1890s; "
                          "vines -> fruit trees c.1900. Los Altos was laid out among apricot orchards (1907)."),
    "scv_bayside": dict(seed=(-121.975, 37.415), county="Santa Clara", grain=(1855, 1862), basin=("pasture_dairy", 1853),
                        orchard=(1900, 1920), veg=1868, src=BROEK,
                        note="Adobe lowland by the marshes (Alviso, Agnew, lower Milpitas): pasture and the first dairies in "
                             "the 1850s, hay grain; strawberries moved to Agnew's artesian wells in 1868; truck crops, "
                             "seeds and pears later (Broek's 'small crops' of 1931)."),
    "scv_milpitas_berryessa": dict(seed=(-121.875, 37.40), county="Santa Clara", grain=(1854, 1860), basin=("pasture_dairy", 1854),
                                   orchard=(1890, 1915), veg=1880, src=BROEK,
                                   note="Grain and hay 1850s-80s; orchards on the Berryessa fans from the 1890s and on the "
                                        "Milpitas lowland 1900s-20s; small crops and dairies on the clay."),
    "scv_evergreen": dict(seed=(-121.79, 37.32), county="Santa Clara", grain=(1855, 1862), basin=("pasture_dairy", 1855),
                          orchard=(1895, 1915), vine=(1880, 9999, 0.3), src=BROEK,
                          note="Grain on the east-side fans; vineyards in the Evergreen foothills from the 1880s (still on "
                               "the 1953 topo); orchards 1890s-1910s."),
    "scv_coyote": dict(seed=(-121.77, 37.235), county="Santa Clara", grain=(1865, 1880), basin=("pasture_dairy", 1850),
                       orchard=(1895, 1915), src=BROEK,
                       note="Edenvale - Coyote: rancho grants partly undivided and used as cattle range until c.1900; grain "
                            "from the 1860s; orchards 1890s-1910s."),
    "scv_morgan_hill": dict(seed=(-121.655, 37.125), county="Santa Clara", grain=(1868, 1885), basin=("pasture_dairy", 1850),
                            orchard=(1898, 1920), vine=(1885, 9999, 0.15), src=BROEK,
                            note="Madrone - Morgan Hill - San Martin: Rancho Ojo de Agua de la Coche range; grain from the "
                                 "1860s ('from San Jose to Gilroy an almost unbroken wheatfield', Cronise 1868 - an "
                                 "exaggeration, Broek); Morgan Hill subdivided 1892, town 1896; prunes / apricots 1900s-10s."),
    "scv_gilroy": dict(seed=(-121.56, 37.005), county="Santa Clara", grain=(1860, 1870), basin=("pasture_dairy", 1863),
                       eras=[dict(kind="vegetables", crop="seed farms, garlic, tomatoes and other row crops", on=("fan", "basin"),
                                  start=1945, full=1970, share=0.5, src=W + "Gilroy,_California",
                                  note="Garlic grown commercially around Gilroy from the 1920s (K. 'Jimmy' Hirasaki), flower "
                                       "and vegetable seed farms from the 1910s; after 1945 row crops took about half of "
                                       "the prune land (share and years ESTIMATED).")],
                       orchard=(1900, 1922), vine=(1880, 9999, 0.15), src=BROEK,
                       note="Grain from the early 1860s; dairy district (cheese) on the willow-covered Carnadero bottom from "
                            "1863; prunes 1900s-20s; vineyards in the warm foothills."),
    # ---- Peninsula (San Mateo County + Palo Alto)
    "pen_palo_alto": dict(seed=(-122.145, 37.425), county="Santa Clara", grain=(1853, 1860), basin=("pasture_dairy", 1853),
                          orchard=(1888, 1905), estate=(1876, "hay fields and horse paddocks of Stanford's Palo Alto Stock Farm (1876-1903)"),
                          src=W + "Palo_Alto_Stock_Farm",
                          note="Mayfield grain and hay farms from the 1850s; Leland Stanford's Palo Alto Stock Farm (1876, "
                               "~8,000 acres of hay and paddocks) became Stanford University land (1891); orchards in "
                               "Mayfield / Barron Park / College Terrace 1890s-1900s."),
    "pen_menlo_atherton": dict(seed=(-122.19, 37.455), county="San Mateo", grain=(1853, 1860), basin=("pasture_dairy", 1853),
                               estate=(1865, "country estates of San Francisco families: lawns, oak parks, gardens and hay fields"),
                               src=W + "Atherton,_California",
                               note="Grain and hay farms from the 1850s; country estates (Atherton's Valparaiso Park 1860, "
                                    "Menlo Park estates 1860s-80s) with gardens and hay."),
    "pen_redwood_city": dict(seed=(-122.24, 37.49), county="San Mateo", grain=(1855, 1862), basin=("hay", 1855),
                             src=W + "Redwood_City,_California",
                             note="Hay, dairies and tanneries around the redwood-lumber port (1850s); flower nurseries "
                                  "(see SPECIAL) from the 1900s."),
    "pen_san_mateo": dict(seed=(-122.315, 37.555), county="San Mateo", grain=(1855, 1862), basin=("pasture_dairy", 1855),
                          estate=(1868, "estates (San Mateo / Burlingame / Hillsborough) with hay fields and pasture"),
                          src=W + "Hillsborough,_California",
                          note="Dairies and hay; estates from the 1860s (Burlingame 1893)."),
    "pen_millbrae_san_bruno": dict(seed=(-122.41, 37.615), county="San Mateo", grain=(1858, 1865), basin=("pasture_dairy", 1858),
                                   dairy=1860, src=W + "Millbrae,_California",
                                   note="Dairy land: Darius Ogden Mills's Millbrae estate and dairy (1860s-1940s), San Bruno "
                                        "and Baden dairies and stock yards."),
    "pen_colma": dict(seed=(-122.455, 37.67), county="San Mateo", grain=(1858, 1865), basin=("pasture_dairy", 1858),
                      veg_all=1870, src=W + "Colma,_California",
                      note="Truck gardens (potatoes, cabbages; Italian and Irish growers) supplying San Francisco from the "
                           "1870s, flower growing later; cemeteries from 1887."),
    "pen_coast": dict(seed=(-122.44, 37.42), county="San Mateo", grain=(1855, 1865), basin=("pasture_dairy", 1855),
                      veg_all=1920, src=W + "Half_Moon_Bay,_California",
                      note="Coast terraces: grain and potatoes from the 1850s, artichokes and Brussels sprouts from the "
                           "1920s (estimated)."),
    # ---- Alameda County
    "eb_oakland_berkeley": dict(seed=(-122.255, 37.83), county="Alameda", grain=(1852, 1856), basin=("pasture_dairy", 1852),
                                src=W + "History_of_Oakland,_California",
                                note="Peralta rancho lands sold off from 1852: grain, hay and gardens until the towns grew."),
    "eb_san_leandro": dict(seed=(-122.14, 37.715), county="Alameda", grain=(1851, 1855), basin=("vegetables", 1880),
                           orchard=(1868, 1890), fallback_orchard=0.6,
                           src="https://www.haywardareahistory.org/agricultural-history",
                           note="First significant wheat and barley crop on the east shore 1851 (Broek); soil exhaustion "
                                "turned Eden Township to fruit: cherries (San Leandro 'Cherry City', festival 1909) and "
                                "apricots; vegetables on the lowland. The 1947 San Leandro / Hayward topos carry no "
                                "vegetation, so the orchard extent is ESTIMATED (share of the fans)."),
    "eb_hayward": dict(seed=(-122.09, 37.645), county="Alameda", grain=(1852, 1856), basin=("vegetables", 1880),
                       orchard=(1870, 1895), fallback_orchard=0.55,
                       src="https://www.haywardareahistory.org/agricultural-history",
                       note="Hayward / Mt Eden / San Lorenzo / Castro Valley: grain 1850s-70s; from 1876 orchards (apricots, "
                            "cherries, almonds; the Meek orchard 2,200 acres) and row crops (tomatoes, peas, cucumbers); "
                            "orchard extent ESTIMATED (no vegetation on the 1947 topos)."),
    "eb_washington": dict(seed=(-122.02, 37.56), county="Alameda", grain=(1853, 1858), basin=("vegetables", 1879),
                          orchard=(1885, 1910), vine=(1880, 1920, 0.35), src=W + "Washington_Township,_Alameda_County,_California",
                          note="Alvarado - Newark - Centerville - Irvington - Mission San Jose - Warm Springs: grain from 1853; "
                               "sugar beets and vegetables on the lowland (Alvarado sugar mill 1870, rebuilt 1879, ran until "
                               "the 1960s); vineyards at Mission San Jose / Warm Springs from the 1870s-80s (Gallegos' "
                               "Palmdale 1881) until phylloxera / Prohibition; orchards 1880s-1900s."),
    "eb_livermore": dict(seed=(-121.77, 37.675), county="Alameda", grain=(1865, 1872), basin=("pasture_dairy", 1860),
                         vine=(1882, 9999, 0.25), src=W + "Livermore_Valley_AVA",
                         note="Dry-farmed grain and hay on the valley floor from the 1860s (railroad 1869) to the 1950s; "
                              "vineyards on the gravelly south side from 1882 (Cresta Blanca 1882, Wente and Concannon "
                              "1883; 5,500-6,000 acres in the 1890s)."),
    "eb_pleasanton": dict(seed=(-121.885, 37.66), county="Alameda", grain=(1860, 1868), basin=("pasture_dairy", 1860),
                          src="https://www.pleasantonweekly.com/blogs/2019/11/26/talking-historical-hops-with-otis-nostrand/",
                          note="Grain and hay; hop yards on the wet bottom land 1880s-WWI (see SPECIAL)."),
    "eb_dublin_san_ramon": dict(seed=(-121.93, 37.74), county="Alameda", grain=(1860, 1868), basin=("pasture_dairy", 1860),
                                src=W + "Dublin,_California", note="Grain, hay and cattle until the 1960s suburbs."),
    # ---- Contra Costa County
    "cc_west": dict(seed=(-122.32, 37.965), county="Contra Costa", grain=(1855, 1862), basin=("pasture_dairy", 1855),
                    src=COCO, note="San Pablo - Pinole - El Cerrito: grain, hay and dairies on the Castro rancho lands."),
    "cc_martinez": dict(seed=(-122.13, 37.99), county="Contra Costa", grain=(1855, 1862), basin=("pasture_dairy", 1855),
                        orchard=(1880, 1900), vine=(1880, 1920, 0.3), src="https://www.nps.gov/jomu/learn/historyculture/index.htm",
                        note="Martinez / Alhambra Valley: grain, then pears, cherries and grapes (John Muir's Strentzel "
                             "fruit ranch, 1880s-1914)."),
    "cc_walnut_creek": dict(seed=(-122.065, 37.91), county="Contra Costa", grain=(1855, 1860), basin=("pasture_dairy", 1855),
                            orchard=(1895, 1925), fallback_orchard=0.5, src=COCO,
                            note="Walnut Creek - Pleasant Hill - Lafayette: wheat (the county's leading crop, peak 1880s); "
                                 "walnuts, pears and apricots from the 1890s; walnuts peaked 1946 (orchard extent ESTIMATED "
                                 "where the 1947 Walnut Creek topo has no vegetation)."),
    "cc_concord_clayton": dict(seed=(-121.96, 37.96), county="Contra Costa", grain=(1855, 1862), basin=("pasture_dairy", 1855),
                               orchard=(1900, 1925), vine=(1885, 1920, 0.35), src="https://www.goldennuggetlibrary.sfgenealogy.org/ccwal.htm",
                               note="Grain; vineyards from the 1880s (Concord / Clayton); walnuts replaced the vines after "
                                    "1919 (Prohibition)."),
    "cc_danville": dict(seed=(-121.99, 37.82), county="Contra Costa", grain=(1858, 1865), basin=("pasture_dairy", 1858),
                        orchard=(1900, 1925), src=COCO, note="San Ramon Valley: grain and hay, walnuts and pears from c.1900."),
    "cc_oakley_antioch": dict(seed=(-121.74, 38.0), county="Contra Costa", grain=(1870, 1880), basin=("pasture_dairy", 1870),
                              vine=(1895, 9999, 0.4), orchard=(1905, 1925), fallback_orchard=0.3,
                              src="https://eastcontracostahistory.org/our-communities/brentwood/",
                              note="Dry-farmed grain; on the Oakley sands vineyards and almond orchards from the 1890s "
                                   "(estimated)."),
    "cc_brentwood_byron": dict(seed=(-121.66, 37.91), county="Contra Costa", grain=(1870, 1880), basin=("pasture_dairy", 1870),
                               irrigated=(1916, "alfalfa and dairies (East Contra Costa Irrigation District, 1914-16)"),
                               orchard=(1916, 1930), fallback_orchard=0.3,
                               src="https://eastcontracostahistory.org/our-communities/brentwood/",
                               note="Dry-land grain until Balfour-Guthrie's irrigation system (planned 1913; ECCID ~20,000 "
                                    "acres): alfalfa and dairies, Balfour-Guthrie orchards 1922 (apricots, walnuts, "
                                    "peaches). Orchard extent ESTIMATED where the 1954 topo shows none."),
    # ---- Marin
    "mn_novato": dict(seed=(-122.575, 38.10), county="Marin", grain=(1856, 1862), basin=("pasture_dairy", 1856),
                      orchard=(1858, 1870), fallback_orchard=0.15, src="https://www.novatohistory.org/",
                      note="Rancho Novato sold to Sweetser and De Long 1856: grain, potatoes and a large apple / pear "
                           "orchard (dates LOW); dairies on the hills; baylands diked for hay 1880s-1910s."),
    "mn_san_rafael": dict(seed=(-122.54, 37.975), county="Marin", grain=(1855, 1860), basin=("pasture_dairy", 1855),
                          src="https://ucanr.edu/site/grown-marin/history-marin-agriculture",
                          note="Dairies and hay in the San Rafael / Ross valleys until the railroad suburbs."),
    "mn_west": dict(seed=(-122.80, 38.06), county="Marin", grain=None, basin=("pasture_dairy", 1857), dairy=1857,
                    src="https://home.nps.gov/pore/learn/historyculture/stories_ranching.htm",
                    note="West Marin dairy country: Shafter / Howard leases at Point Reyes from 1857 ('alphabet ranches'); "
                         "Marin led California in dairy output into the 1890s; potatoes in the 1860s."),
    # ================= ten-county extension (2026-11): Sonoma, Napa, Solano, the Delta, Santa Cruz =================
    # "eras": further eras in order, each dict(kind, crop, on=(soil classes), start, full, end, share[, orchard_share,
    # src, note]); shares are nested (one blob field), so a later era with a larger share replaces an earlier one
    # with a smaller share on the same soil - e.g. prunes over phylloxera / Prohibition vineyards.
    # "osm": today's vineyards / orchards (OpenStreetMap outlines) dated (start, full) by the modern planting era.
    # ---- Sonoma County
    "son_petaluma": dict(seed=(-122.64, 38.25), county="Sonoma", grain=(1852, 1858), basin=("pasture_dairy", 1855),
                         eras=[dict(kind="farm_mixed", crop="chicken ranches (leghorn egg farms: long hen houses, runs, kale "
                                    "and hay patches) and dairies", on=("fan", "upper_fan"), start=1885, full=1915, end=1965, share=0.6),
                               dict(kind="pasture_dairy", crop="dairy pasture, hay and silage (after the egg ranches)",
                                    on=("fan", "upper_fan"), start=1958, full=1975, share=0.8)],
                         osm=dict(vineyard=(1975, 2005)), src=W + "Petaluma,_California",
                         note="Vallejo's Rancho Petaluma cattle range (adobe 1836); from 1852 a river port shipping grain, hay, "
                              "potatoes and butter to San Francisco (grain milling); Lyman Byce's incubator (1879) made Petaluma the "
                              "'Egg Capital of the World' c.1900-1950 - hundreds of small chicken ranches, also at Penngrove and "
                              "Cotati (ranch subdivided 1892); the egg ranches closed in the 1950s-60s and the land went back to "
                              "dairy pasture (shares and the 1885 / 1958 starts ESTIMATED)."),
    "son_sonoma_valley": dict(seed=(-122.47, 38.30), county="Sonoma", grain=(1850, 1858), basin=("hay", 1860),
                              eras=[dict(kind="vineyard", crop="wine grapes", on=("upper_fan",), start=1858, full=1880, share=0.5),
                                    dict(kind="vineyard", crop="wine grapes", on=("fan",), start=1860, full=1880, share=0.25),
                                    dict(kind="farm_mixed", crop="prunes, pears, hay and dairies among the vineyards",
                                         on=("fan",), start=1895, full=1920, share=0.5, orchard_share=0.5),
                                    dict(kind="vineyard", crop="wine grapes (replanting)", on=("fan", "upper_fan"),
                                         start=1968, full=1995, share=0.55)],
                              osm=dict(vineyard=(1968, 1995)), src=W + "Sonoma_Valley_AVA",
                              note="Mission vineyard 1823; Vallejo's cattle and grain; Haraszthy's Buena Vista (1857) started the "
                                   "commercial vineyards (~500 acres at Buena Vista in the 1870s, ~4,000 acres in the valley by "
                                   "1900); phylloxera (first found here, 1870s) and Prohibition (1920) put prunes, pears and hay on "
                                   "much of the floor; replanting from the late 1960s (shares ESTIMATED)."),
    "son_santa_rosa_plain": dict(seed=(-122.74, 38.44), county="Sonoma", grain=(1853, 1860), basin=("pasture_dairy", 1855),
                                 eras=[dict(kind="vineyard", crop="hops (trellised hop yards on the creek bottoms)", on=("fan",),
                                            start=1880, full=1895, end=1950, share=0.1),
                                       dict(kind="orchard", crop="prunes, pears, apples, cherries", on=("fan", "upper_fan"),
                                            start=1890, full=1915, share=0.35),
                                       dict(kind="pasture_dairy", crop="dairy pasture, hay and rural homesteads (orchards pulled out)",
                                            on=("fan", "upper_fan"), start=1962, full=1980, share=0.3),
                                       dict(kind="vineyard", crop="wine grapes (Russian River Valley plantings)", on=("fan", "upper_fan"),
                                            start=1972, full=2000, share=0.12)],
                                 osm=dict(vineyard=(1972, 2000)), src=W + "Sonoma_County,_California",
                                 note="Santa Rosa Plain (Santa Rosa, Windsor, Fulton, Cotati, Rohnert Park): wheat and oats from the "
                                      "1850s; hop yards along Santa Rosa and Mark West creeks and the Laguna c.1880-1950; prunes and "
                                      "other orchard fruit from the 1890s (Sonoma County 'a leading producer of hops, grapes, prunes "
                                      "and apples, dairy and poultry products'); orchards gave way to pasture, houses and, from the "
                                      "1970s, vineyards (years and shares ESTIMATED; Rohnert Park was a seed farm until 1956)."),
    "son_gold_ridge": dict(seed=(-122.87, 38.41), county="Sonoma", grain=(1855, 1865), basin=("pasture_dairy", 1855),
                           eras=[dict(kind="orchard", crop="Gravenstein apples (also cherries, plums and berries)",
                                      on=("upper_fan", "fan"), start=1890, full=1915, share=0.6, src=W + "Gravenstein"),
                                 dict(kind="pasture_dairy", crop="pasture, hay and rural homesteads (apple orchards pulled out)",
                                      on=("upper_fan", "fan"), start=1975, full=2005, share=0.45, src=W + "Gravenstein")],
                           osm=dict(vineyard=(1985, 2010), orchard=(1890, 1915)), src=W + "Sebastopol,_California",
                           note="Gold Ridge (Sebastopol, Graton, Forestville, Twin Hills): potatoes, grain and hay on the sandy "
                                "loam from the 1850s; the railroad (1890) and Luther Burbank's Gold Ridge farm (1885) began the "
                                "'Gravenstein era' - Gravenstein was the main apple of western Sonoma County through the first "
                                "half of the 20th century (dried apples and apple sauce in both wars); most orchards went from the "
                                "1970s on, many to vineyards. Ground: ESTIMATED outline of the low hills "
                                "(valley_floor_extra.geojson), orchard share ESTIMATED."),
    "son_russian_river": dict(seed=(-122.86, 38.59), county="Sonoma", grain=(1856, 1862), basin=("pasture_dairy", 1856),
                              vine=(1872, 9999, 0.4),
                              eras=[dict(kind="vineyard", crop="hops (hop yards and kilns on the river bottom)", on=("fan",),
                                         start=1880, full=1895, end=1952, share=0.15),
                                    dict(kind="orchard", crop="prunes (also pears and apples)", on=("fan", "upper_fan"),
                                         start=1895, full=1925, share=0.5),
                                    dict(kind="vineyard", crop="wine grapes (replanting of the prune land)", on=("fan", "upper_fan"),
                                         start=1970, full=1995, share=0.6)],
                              osm=dict(vineyard=(1970, 1995)), src=W + "Healdsburg,_California",
                              note="Healdsburg - Windsor reach of the Russian River: grain on Rancho Sotoyome land from the 1850s "
                                   "(railroad 1872); by the 1880s grapes, lumber and hops were the main income; Prohibition "
                                   "collapsed the wine industry and in the 1920s most vineyards were replaced with fruit trees - "
                                   "'the Buckle of the Prune Belt' (1929); prunes were the largest crop until the 1970s, when "
                                   "vineyards replaced the orchards (hop and prune shares ESTIMATED)."),
    "son_dry_creek": dict(seed=(-122.95, 38.67), county="Sonoma", grain=(1858, 1865), basin=("pasture_dairy", 1858),
                          vine=(1870, 9999, 0.35),
                          eras=[dict(kind="orchard", crop="prunes (also pears)", on=("fan", "upper_fan"), start=1900, full=1925, share=0.6),
                                dict(kind="vineyard", crop="wine grapes (replanting of the prune land)", on=("fan", "upper_fan"),
                                     start=1972, full=1995, share=0.7)],
                          osm=dict(vineyard=(1972, 1995)), src=W + "Dry_Creek_Valley_AVA",
                          note="Dry Creek Valley: grain and stock from the 1850s; vineyards from 1868 (S. P. Hallengren), Zinfandel "
                               "field blends of the 1880s-1900s; prunes through Prohibition to the 1960s; wineries again from 1972 "
                               "(prune years as at Healdsburg, ESTIMATED)."),
    "son_alexander_valley": dict(seed=(-122.87, 38.74), county="Sonoma", grain=(1856, 1865), basin=("pasture_dairy", 1856),
                                 vine=(1881, 9999, 0.35),
                                 eras=[dict(kind="vineyard", crop="hops", on=("fan",), start=1885, full=1900, end=1950, share=0.1),
                                       dict(kind="orchard", crop="prunes (also pears)", on=("fan", "upper_fan"), start=1895, full=1925, share=0.5),
                                       dict(kind="vineyard", crop="wine grapes (replanting of the prune land)", on=("fan", "upper_fan"),
                                            start=1965, full=1995, share=0.65)],
                                 osm=dict(vineyard=(1965, 1995)), src=W + "Alexander_Valley_AVA",
                                 note="Alexander Valley - Geyserville - Cloverdale: Cyrus Alexander's ranch on Rancho Sotoyome "
                                      "(vines from Fort Ross cuttings, 1843), grain from the 1850s; the Italian Swiss Colony at Asti "
                                      "(1881, winery 1887); prunes and hops between the wars (Cloverdale Citrus Fair 1892); modern "
                                      "vineyards from the 1960s (Robert Young 1963). Hop and prune shares ESTIMATED."),
    "son_coast_dairy": dict(seed=(-122.93, 38.33), county="Sonoma", grain=(1853, 1860), basin=("pasture_dairy", 1855), dairy=1865,
                            src="https://archive.org/details/historicaldescri00thom",
                            note="Bodega - Valley Ford - Bloomfield - Two Rock (and the Tomales end of Marin): potatoes ('Bodega "
                                 "Reds'), oats and wheat on the small valley floors in the 1850s-60s (Bodega 1853, Bloomfield 1856), "
                                 "then the Marin - Sonoma coast dairy belt - butter shipped by schooner and, from 1876, by the North "
                                 "Pacific Coast Railroad (Thompson 1877; switch year ESTIMATED). The hills are grazing: no feature."),
    "son_coast_north": dict(seed=(-123.25, 38.55), county="Sonoma", basin=("pasture_dairy", 1860), dairy=1860,
                            src=W + "Fort_Ross,_California",
                            note="Sonoma coast terraces, Jenner to Gualala: the Russian colony's fields and orchard at Fort Ross "
                                 "(1812-41, a few hundred acres - not drawn), then sheep and cattle ranches (Benitz, Call) and "
                                 "lumber landings; pasture from c.1860 (ESTIMATED)."),
    # ---- Napa County (the 1860-95 vineyard / prune-era / 1965 vineyard rings of landcover_history.csv stay as they are)
    "napa_lower": dict(seed=(-122.29, 38.30), county="Napa", grain=(1850, 1856), basin=("hay", 1856), vine=(1868, 9999, 0.3),
                       eras=[dict(kind="orchard", crop="prunes, pears, cherries and walnuts", on=("fan", "upper_fan"),
                                  start=1890, full=1915, share=0.25)],
                       osm=dict(vineyard=(1968, 1995)), src=W + "Napa_County,_California",
                       note="Napa - Coombsville - Carneros - American Canyon: cattle and sheep range (Carneros = 'rams'), wheat "
                            "and hay from 1850 (Napa founded 1847 at the head of navigation); John Patchett's first commercial "
                            "vineyard 1858; by the 1900s over 500,000 fruit and nut trees in the county, especially plums and "
                            "pears; vineyards again from the late 1960s (shares ESTIMATED)."),
    "napa_valley_mid": dict(seed=(-122.42, 38.47), county="Napa", grain=(1852, 1858), basin=("pasture_dairy", 1855),
                            eras=[dict(kind="vineyard", crop="wine grapes (first boom)", on=("fan", "upper_fan"),
                                       start=1868, full=1885, share=0.5),
                                  dict(kind="orchard", crop="prunes and walnuts (after phylloxera and Prohibition), hay",
                                       on=("fan", "upper_fan"), start=1898, full=1925, share=0.2)],
                            osm=dict(vineyard=(1965, 1990)), src=W + "Napa_Valley_AVA",
                            note="Yountville - Oakville - Rutherford - St. Helena: George Yount's vines 1838, wheat the main crop "
                                 "of the 1850s-60s (Bale mill 1846); Charles Krug's winery 1861, railroad 1868; 443 vineyards of "
                                 "1,000+ vines by 1880; phylloxera (1890s), Prohibition (1920) and the Depression - prunes and "
                                 "walnuts on much of the floor; premium wine re-emerged in the 1960s (Mondavi 1966). Shares ESTIMATED."),
    "napa_calistoga": dict(seed=(-122.58, 38.585), county="Napa", grain=(1855, 1862), basin=("pasture_dairy", 1855),
                           eras=[dict(kind="vineyard", crop="wine grapes (first boom)", on=("fan", "upper_fan"), start=1875, full=1890, share=0.35),
                                 dict(kind="orchard", crop="prunes and walnuts", on=("fan", "upper_fan"), start=1900, full=1925, share=0.2)],
                           osm=dict(vineyard=(1968, 1995)), src=W + "Napa_Valley_AVA",
                           note="Upper Napa Valley and Knights Valley: grain and stock on Rancho Carne Humana; Calistoga founded "
                                "1868 with the railroad; vineyards 1870s-80s, prunes between the wars, vineyards again from the "
                                "late 1960s (years and shares ESTIMATED from the valley-wide history)."),
    "napa_pope_berryessa": dict(seed=(-122.36, 38.64), county="Napa", grain=(1866, 1872), basin=("pasture_dairy", 1860),
                                osm=dict(vineyard=(1975, 2000)), src=W + "Monticello,_California",
                                note="Pope, Chiles, Capell and Berryessa valleys: stock range; Rancho Las Putas was subdivided for "
                                     "wheat farmers in 1866 (Monticello). The floor of the Berryessa Valley has been under the lake "
                                     "since 1957 and is not drawn (no pre-dam map traced)."),
    # ---- Solano County
    "sol_benicia_vallejo": dict(seed=(-122.22, 38.11), county="Solano", grain=(1850, 1856), basin=("pasture_dairy", 1855),
                                src=W + "Vallejo,_California",
                                note="Vallejo - Benicia - Sulphur Springs valley: Rancho Suscol cattle, then hay, grain and dairies "
                                     "for the towns and the navy yard (ESTIMATED)."),
    "sol_suisun_green_valley": dict(seed=(-122.12, 38.25), county="Solano", grain=(1852, 1858), basin=("pasture_dairy", 1855),
                                    vine=(1860, 1920, 0.2),
                                    eras=[dict(kind="orchard", crop="cherries, pears, apricots, peaches and prunes",
                                               on=("fan", "upper_fan"), start=1880, full=1900, share=0.45)],
                                    osm=dict(vineyard=(1975, 2005), orchard=(1880, 1900)), src=W + "Suisun_Valley_AVA",
                                    note="Suisun and Green valleys (Rockville, Cordelia, Fairfield): Rancho Suisun grain from the "
                                         "1850s; first vineyards about 1860 (Votypke, Schultz; Mangels 1880), family wineries until "
                                         "Prohibition; fruit orchards were the valleys' main use from the 1880s until 'the change "
                                         "over from fruit orchards to vineyards' a century later (orchard start and share ESTIMATED)."),
    "sol_vaca_valley": dict(seed=(-121.99, 38.36), county="Solano", grain=(1851, 1858), basin=("pasture_dairy", 1855),
                            eras=[dict(kind="orchard", crop="early fruit: apricots, peaches, cherries, plums and table grapes",
                                       on=("fan", "upper_fan"), start=1875, full=1890, share=0.4),
                                  dict(kind="pasture_dairy", crop="pasture and hay (orchards pulled out)", on=("fan", "upper_fan"),
                                       start=1955, full=1980, share=0.3)],
                            osm=dict(orchard=(1875, 1890)), src=W + "Vacaville,_California",
                            note="Vaca, Lagoon and Pleasants valleys: Rancho Los Putos (1843) cattle; Vacaville laid out 1851, grain; "
                                 "the sheltered valleys ripened fruit earliest in the state - orchards from the 1870s, Leonard "
                                 "Buck's California Fruit Shipping Association 1880, Chinese and Japanese orchard labour; the fruit "
                                 "district faded after the 1950s (start and share ESTIMATED)."),
    "sol_dixon": dict(seed=(-121.82, 38.42), county="Solano", grain=(1855, 1865), basin=("pasture_dairy", 1860),
                      eras=[dict(kind="hay", crop="irrigated alfalfa, dairies, sugar beets, tomatoes and corn",
                                 on=("fan", "upper_fan"), start=1915, full=1965, share=0.6)],
                      osm=dict(orchard=(1965, 2005)), src=W + "Dixon,_California",
                      note="Dixon - Elmira - Maine Prairie plain: dry-farmed wheat and barley from the 1850s, shipped from the "
                           "Maine Prairie landing (post office 1862) and, from 1868-71, by rail (Silveyville moved to the depot "
                           "at Dixon in 1871); pump irrigation brought alfalfa and dairies in the 1910s-20s and the Solano "
                           "Project (Monticello Dam, 1957) row crops; today's walnut, almond and prune orchards are post-war. "
                           "Irrigation years and shares ESTIMATED - no dated source found for the district."),
    "sol_montezuma_hills": dict(seed=(-121.80, 38.14), county="Solano", basin=("pasture_dairy", 1860),
                                eras=[dict(kind="grain", crop="dry-farmed wheat and barley in rotation with sheep pasture",
                                           on=("upper_fan", "fan"), start=1862, full=1875, share=0.6)],
                                src=W + "Montezuma_Hills",
                                note="Montezuma Hills (Collinsville, Birds Landing, Denverton): sheep range, then dry-farmed grain "
                                     "shipped from the river landings (Collinsville c.1859, Denverton 1858) - still grain and "
                                     "sheep under the wind turbines. Years ESTIMATED (UNVERIFIED: no dated source found); ground: "
                                     "ESTIMATED outline of the rolling upland (valley_floor_extra.geojson)."),
    "sol_delta": dict(seed=(-121.70, 38.25), county="Solano", basin=("pasture_dairy", 1862),
                      eras=[dict(kind="vegetables", crop="asparagus, beans, corn, grain and pears on reclaimed river land",
                                 on=("basin", "fan"), start=1872, full=1915, share=0.9)],
                      src=W + "Sacramento%E2%80%93San_Joaquin_River_Delta",
                      note="Solano's Delta (Rio Vista, Ryer Island, Hastings and Egbert tracts, Cache Slough): swamp-and-overflow "
                           "land grazed in the 1860s; levees built by Chinese labourers from the 1850s-70s, reclamation districts "
                           "after 1861 and corporate reclamation after the 320-acre limit was lifted in 1868; most islands were "
                           "farmed by the 1910s (per-island years not researched: ESTIMATED spread 1872-1915)."),
    # ---- Contra Costa: the Delta tracts east of Oakley / Knightsen
    "cc_delta_islands": dict(seed=(-121.59, 38.01), county="Contra Costa", basin=("pasture_dairy", 1860),
                             eras=[dict(kind="vegetables", crop="asparagus, potatoes, beans, celery, corn and grain on reclaimed peat",
                                        on=("basin",), start=1872, full=1915, share=0.9)],
                             src=W + "Sacramento%E2%80%93San_Joaquin_River_Delta",
                             note="Jersey, Bradford, Webb, Holland, Palm, Orwood and Byron tracts, Bethel Island, Hotchkiss and "
                                  "Franks tracts: tule swamp; Bethel Island's levees 1859-70, the big clamshell-dredge reclamations "
                                  "1870s-1910s (Franks Tract 1902-06; reclamation district 1619, 1915); potatoes, beans, asparagus "
                                  "and celery on the peat. Franks Tract flooded in 1938 and stayed water. Per-tract years not "
                                  "researched: ESTIMATED spread 1872-1915."),
    # ---- Santa Cruz County (ground: ESTIMATED outlines, valley_floor_extra.geojson)
    "scz_pajaro_valley": dict(seed=(-121.76, 36.92), county="Santa Cruz", grain=(1852, 1858), basin=("pasture_dairy", 1855),
                              eras=[dict(kind="vegetables", crop="sugar beets (Western Beet Sugar Co., Watsonville, 1888-98)",
                                         on=("fan",), start=1888, full=1892, end=1900, share=0.3, src=W + "Claus_Spreckels"),
                                    dict(kind="orchard", crop="apples (Newtown Pippin, Bellflower)", on=("fan", "upper_fan"),
                                         start=1890, full=1910, share=0.5, src=W + "Martinelli%27s"),
                                    dict(kind="vegetables", crop="strawberries, bush berries, lettuce and other vegetables",
                                         on=("fan", "basin", "upper_fan"), start=1925, full=1965, share=0.4)],
                              osm=dict(orchard=(1890, 1910)), src=W + "Watsonville,_California",
                              note="Pajaro Valley (Watsonville laid out 1852): wheat, barley and potatoes in the 1850s-80s; Claus "
                                   "Spreckels's beet-sugar factory at Watsonville (1888, then the largest in the country; moved to "
                                   "Salinas 1898); apples from the 1890s (Martinelli's cider since 1868) - the valley's main crop "
                                   "until the 1950s; lettuce from the 1920s, strawberries and bush berries after 1945 - today's "
                                   "strawberries, raspberries, lettuce and cole crops. Apple and berry shares and years ESTIMATED."),
    "scz_soquel_aptos": dict(seed=(-121.93, 36.98), county="Santa Cruz", grain=(1855, 1865), basin=("pasture_dairy", 1855),
                             eras=[dict(kind="farm_mixed", crop="apple and apricot orchards, poultry ranches, bulb and flower fields",
                                        on=("upper_fan", "fan"), start=1900, full=1920, share=0.5, orchard_share=0.5)],
                             src=W + "Live_Oak,_Santa_Cruz_County,_California",
                             note="Live Oak - Soquel - Aptos terraces: rancho cattle (Rancho Soquel, Rancho Aptos 1833), grain and "
                                  "hay farms from the 1850s (Live Oak grange and school 1872; Claus Spreckels's Aptos ranch 1872), "
                                  "small orchards, chicken ranches and bulb farms in the early 20th century, suburbs after 1950 "
                                  "(years and shares ESTIMATED)."),
    "scz_north_coast": dict(seed=(-122.13, 36.99), county="Santa Cruz", basin=("pasture_dairy", 1860), dairy=1860,
                            eras=[dict(kind="vegetables", crop="Brussels sprouts and artichokes", on=("upper_fan", "fan"),
                                       start=1920, full=1940, share=0.55)],
                            src=W + "Wilder_Ranch_State_Park",
                            note="Coast terraces from Santa Cruz to Waddell Creek: mission pasture (1791), then coast dairies from "
                                 "the 1850s-60s (the Wilder dairy ran until 1969); Brussels sprouts and artichokes on the terraces "
                                 "from the 1920s (dairy start and vegetable years ESTIMATED)."),
    "scz_mountains": dict(seed=(-122.03, 37.10), county="Santa Cruz", basin=("pasture_dairy", 1860),
                          osm=dict(vineyard=(1970, 1995), orchard=(1885, 1905)), src=W + "Santa_Cruz_Mountains_AVA",
                          note="San Lorenzo Valley and the ridges: redwood logging 1840s-1920s (landcover_history.csv scz_* rows); "
                               "ridge-top vineyards from the 1860s (Jarvis; 38 wineries by the late 1880s), ended by Prohibition, "
                               "and apple / prune orchards on the cleared ridges (Skyline, Bonny Doon, Corralitos); vineyards "
                               "replanted from the 1960s-70s. Only today's mapped vineyards and orchards are drawn."),
}

# special crops on hand-drawn rings (lon/lat), ESTIMATED extents
SPECIAL = [
    dict(id="pleasanton_hops", kind="vineyard", crop="hops (trellised hop yards)", year_start=1888, year_full=1900,
         year_end=1925, share=0.6, ring=[(-121.905, 37.66), (-121.865, 37.685), (-121.835, 37.675), (-121.845, 37.645), (-121.89, 37.64)],
         src="https://www.pleasantonweekly.com/blogs/2019/11/26/talking-historical-hops-with-otis-nostrand/",
         note="Pleasanton Hop Company yards on the wet bottom land along today's Hopyard Road: ~1,900-2,000 acres at the "
              "1913 peak, 1880s to WWI, mostly gone by the 1920s. Drawn as 'vineyard' (tall trellis rows)."),
    dict(id="niles_nursery", kind="nursery", crop="California Nursery Co. (fruit trees, roses)", year_start=1884,
         year_full=1890, year_end=1970, share=0.8,
         ring=[(-121.995, 37.575), (-121.975, 37.585), (-121.96, 37.575), (-121.975, 37.562)],
         src=W + "California_Nursery_Company",
         note="John Rock's California Nursery Company at Niles (1884), once the largest nursery in the West; land sold "
              "for housing from the 1950s-60s (end year LOW)."),
    dict(id="redwood_city_nurseries", kind="nursery", crop="flower nurseries and greenhouses (chrysanthemums)",
         year_start=1905, year_full=1920, year_end=1965, share=0.25,
         ring=[(-122.27, 37.515), (-122.235, 37.505), (-122.20, 37.48), (-122.22, 37.465), (-122.265, 37.49)],
         src=W + "Redwood_City,_California",
         note="Japanese-American and other flower growers around Redwood City / San Carlos / Belmont ('chrysanthemum "
              "capital'), 1900s-1960s; share and extent ESTIMATED."),
    dict(id="bay_farm_asparagus", kind="vegetables", crop="asparagus and vegetables", year_start=1880, year_full=1890,
         year_end=None, share=0.9, ring=[(-122.26, 37.725), (-122.225, 37.725), (-122.225, 37.745), (-122.26, 37.745)],
         src=W + "Bay_Farm_Island",
         note="Bay Farm Island's sand ridges farmed for asparagus and vegetables from the 1880s until the 1950s fills "
              "(Harbor Bay Isle) - urbanisation dates the end."),
    dict(id="alvarado_sugar_beets", kind="vegetables", crop="sugar beets (Alvarado sugar mill)", year_start=1870,
         year_full=1885, year_end=1967, share=0.5,
         ring=[(-122.10, 37.61), (-122.05, 37.61), (-122.02, 37.575), (-122.06, 37.555), (-122.10, 37.575)],
         src=W + "Union_City,_California",
         note="E.H. Dyer's California Beet Sugar Co. at Alvarado (1870), the first successful beet-sugar factory in the "
              "US, rebuilt 1879 (Pacific Coast Sugar / Holly Sugar); beets grown on the surrounding lowland until the "
              "mill closed (1960s). Share ESTIMATED."),
]


def farm_region():
    """Where farm eras are painted: the farm belts of the five counties modelled first (hand outline; San
    Francisco excluded) plus, since the ten-county extension, the whole of Sonoma, Napa, Solano and Santa Cruz
    and the rest of Marin, Contra Costa and Santa Clara."""
    core = Polygon([(-123.05, 38.32), (-122.45, 38.32), (-122.45, 38.05), (-121.50, 38.10),
                    (-121.50, 36.95), (-121.75, 36.95), (-122.10, 37.10), (-122.55, 37.20),
                    (-122.55, 37.62), (-122.50, 37.71), (-122.39, 37.71), (-122.36, 37.76),
                    (-122.30, 37.83), (-122.55, 37.95), (-123.05, 37.95)])
    co = gpd.read_file(f"zip://{RAW / 'tiger' / 'tl_2024_us_county.zip'}")
    co = co[(co.STATEFP == "06") & co.NAME.isin(["Sonoma", "Napa", "Solano", "Marin", "Contra Costa", "Santa Clara",
                                                 "Santa Cruz"])].to_crs(4326)
    counties = shapely.union_all(list(co.geometry))
    new = shapely.union_all([box(-123.70, 38.03, -121.40, 38.95), box(-122.45, 36.80, -121.50, 37.30),
                             box(-121.50, 36.80, -121.28, 37.03)]).intersection(counties)   # not the Coe Park valleys
    return gpd.GeoSeries([shapely.union_all([core, new])], crs=4326).to_crs(M).iloc[0]


def osm_farms() -> gpd.GeoDataFrame:
    """Today's vineyards and orchards: OpenStreetMap landuse polygons (Overture base / land_use)."""
    p = RAW / "overture" / OVERTURE_RELEASE / "region5_land_use.parquet"
    if not p.exists():
        log("agriculture: no region5_land_use.parquet (download_overture.py) - no osm_today features")
        return gpd.GeoDataFrame({"class": []}, geometry=[], crs=M)
    g = gpd.read_parquet(p, columns=["class", "geometry"])
    g = g[g["class"].isin(["vineyard", "orchard"]) & g.geom_type.isin(["Polygon", "MultiPolygon"])]
    return g.set_crs(4326, allow_override=True).to_crs(M)


def districts(envelope) -> gpd.GeoDataFrame:
    seeds = gpd.GeoSeries([Point(v["seed"]) for v in D.values()], crs=4326).to_crs(M)
    vor = shapely.voronoi_polygons(MultiPoint(list(seeds)), extend_to=envelope)
    cells = []
    for name, s in zip(D, seeds):
        cell = next(c for c in vor.geoms if c.contains(s))
        cells.append(dict(district=name, geometry=cell.intersection(envelope)))
    return gpd.GeoDataFrame(cells, crs=M)


# --------------------------------------------------------------------------- build
def topo_orchards() -> gpd.GeoDataFrame:
    p = MANUAL / "farmsteads" / "topo_orchards.geojson"
    if not p.exists():
        log("agriculture: no topo_orchards.geojson yet (run pipeline/topo_farmsteads.py export)")
        return gpd.GeoDataFrame(columns=["kind", "map_year", "photo_year", "quad", "geometry"], geometry="geometry", crs=4326)
    o = gpd.read_file(p)
    return o


def feat(rows, geom, **kw):
    for p in explode_polys(geom):
        if p.area < 2e4:   # < 2 ha
            continue
        rows.append(dict(kw, geometry=p))


def agriculture():
    vf = valley_floor()
    region = farm_region()
    vf["geometry"] = vf.geometry.intersection(region)
    vf = vf[~vf.geometry.is_empty]
    dist = districts(region)
    pieces = gpd.overlay(vf, dist, how="intersection", keep_geom_type=True)
    log(f"agriculture: {len(pieces)} valley-floor pieces in {pieces.district.nunique()} districts")
    br = broek_1931().to_crs(M)
    br_area = shapely.union_all(list(br.geometry.buffer(0)))
    br_orch = shapely.union_all(list(br[br.cls.isin(["orchard"])].geometry))
    br_mix = shapely.union_all(list(br[br.cls.isin(["orchard_mixed"])].geometry))
    br_small = shapely.union_all(list(br[br.cls.isin(["small_crops"])].geometry))
    br_past = shapely.union_all(list(br[br.cls.isin(["pasture"])].geometry))
    br_nsc = shapely.union_all(list(br[br.cls.isin(["nsc_foothills"])].geometry))
    to = topo_orchards().to_crs(M)
    to = to[to.geometry.intersects(region)]
    t_orch = shapely.union_all(list(to[to.kind == "orchard"].geometry.buffer(0)))
    t_vine = shapely.union_all(list(to[to.kind == "vineyard"].geometry.buffer(0)))
    osm = osm_farms()
    rows = []
    for dname, v in D.items():
        dp = pieces[pieces.district == dname]
        if not len(dp) and not v.get("osm"):
            continue
        cell = dist[dist.district == dname].geometry.iloc[0]
        base = dict(district=dname, county=v["county"], source_url=v["src"])
        by = {s: shapely.union_all(list(dp[dp.soil == s].geometry)) for s in ("fan", "upper_fan", "basin")}
        allv = shapely.union_all([g for g in by.values() if g is not None and not g.is_empty])
        # 1. grain era on fans + upper fans
        if v.get("grain"):
            ys, yf = v["grain"]
            feat(rows, shapely.union_all([by["fan"], by["upper_fan"]]), layer="district_era", kind="grain",
                 crop="wheat and barley (dry-farmed), hay grain", year_start=ys, year_full=yf, year_end=None, share=1.0,
                 confidence="estimated", note=v["note"], **base)
        # 2. basin lowland
        bk, byr = v.get("basin") or ("pasture_dairy", 1860)
        crop = {"pasture_dairy": "pasture, hay and dairies on the clay lowland ('adobe')", "hay": "hay and pasture",
                "vegetables": "row crops and vegetables on the lowland"}[bk]
        feat(rows, by["basin"], layer="district_era", kind=bk, crop=crop, year_start=byr, year_full=byr + 8, year_end=None,
             share=1.0, confidence="estimated", note=v["note"], **base)
        if v.get("dairy"):  # whole valley floor in dairy pasture (west Marin, Millbrae)
            feat(rows, allv, layer="district_era", kind="pasture_dairy", crop="dairy pasture and hay",
                 year_start=v["dairy"], year_full=v["dairy"] + 10, year_end=None, share=1.0, confidence="estimated",
                 note=v["note"], **base)
        if v.get("estate"):
            ey, ecrop = v["estate"]
            feat(rows, allv, layer="district_era", kind="farm_mixed", crop=ecrop, year_start=ey, year_full=ey + 15,
                 year_end=None, share=0.5, confidence="estimated", note=v["note"], **base)
        if v.get("veg_all"):
            feat(rows, allv, layer="district_era", kind="vegetables", crop="truck crops / vegetables",
                 year_start=v["veg_all"], year_full=v["veg_all"] + 10, year_end=None, share=0.8, confidence="estimated",
                 note=v["note"], **base)
        if v.get("irrigated"):
            iy, icrop = v["irrigated"]
            feat(rows, allv, layer="district_era", kind="hay", crop=icrop, year_start=iy, year_full=iy + 8,
                 year_end=None, share=0.7, confidence="estimated", note=v["note"], **base)
        # 3. foothill vineyard belt on the upper fans
        if v.get("vine"):
            vs, ve, vsh = v["vine"]
            feat(rows, by["upper_fan"], layer="district_era", kind="vineyard", crop="wine grapes (foothill belt)",
                 year_start=vs, year_full=vs + 12, year_end=None if ve >= 9999 else ve, share=vsh,
                 confidence="estimated", note=v["note"], **base)
        # 3b. further researched eras of the district (ten-county extension), on named soil classes
        for e in v.get("eras", []):
            eg = shapely.union_all([by[s] for s in e["on"] if by[s] is not None and not by[s].is_empty])
            feat(rows, eg, layer="district_era", kind=e["kind"], crop=e["crop"], year_start=e["start"],
                 year_full=e["full"], year_end=e.get("end"), share=e["share"], orchard_share=e.get("orchard_share"),
                 confidence="estimated", note=e.get("note") or v["note"],
                 **dict(base, source_url=e.get("src") or v["src"]))
        # 4. Broek 1931 (Santa Clara Valley)
        cb = shapely.intersection(cell, br_area)
        if not cb.is_empty and cb.area > 1e6:
            o0, o1 = v.get("orchard") or (1895, 1915)
            note = ("Broek (1932) Map III, landscape types of 1931 (traced; georeference RMS ~0.7 km, schematic). "
                    "Start years from the district history: " + v["note"])
            bro = dict(source="broek_1932", source_url=BROEK, district=dname, county=v["county"], snapshot_year=1931)
            feat(rows, shapely.intersection(cell, br_orch).difference(t_orch), layer="broek_1931", kind="orchard",
                 crop="prunes, apricots, cherries, pears (orchard formation)", year_start=o0, year_full=o1, year_end=None,
                 share=1.0, confidence="mapped_1931", note=note, **bro)
            feat(rows, shapely.intersection(cell, br_mix).difference(t_orch), layer="broek_1931", kind="farm_mixed",
                 crop="orchards mixed with small crops (vegetables, berries, hay)", year_start=o0 + 5, year_full=o1 + 5,
                 year_end=None, share=0.6, orchard_share=0.6, confidence="mapped_1931", note=note, **bro)
            if v.get("veg"):
                feat(rows, shapely.intersection(cell, br_small).difference(t_orch), layer="broek_1931", kind="vegetables",
                     crop="small crops: vegetables, berries, seeds, hay grain", year_start=v["veg"], year_full=v["veg"] + 20,
                     year_end=None, share=0.8, confidence="mapped_1931", note=note, **bro)
            feat(rows, shapely.intersection(cell, br_past).difference(t_orch), layer="broek_1931", kind="pasture_dairy",
                 crop="pasture and hay (dairy and truck-farm lowland)", year_start=1855, year_full=1865, year_end=None,
                 share=1.0, confidence="mapped_1931", note=note, **bro)
            feat(rows, shapely.intersection(cell, br_nsc).difference(t_orch), layer="broek_1931", kind="farm_mixed",
                 crop="foothill orchards, vineyards and country homes", year_start=1880, year_full=1905, year_end=None,
                 share=0.5, orchard_share=0.4, confidence="mapped_1931", note=note, **bro)
        # 5. topo 1939-56 orchards / vineyards (exact extents)
        for kind, tg in (("orchard", t_orch), ("vineyard", t_vine)):
            g = shapely.intersection(cell, tg)
            if g.is_empty:
                continue
            o0, o1 = v.get("orchard") or (1900, 1925)
            if kind == "vineyard" and v.get("vine"):
                o0, o1 = v["vine"][0], v["vine"][0] + 12
            note = ("USGS 1:24,000 / 1:62,500 topographic maps of 1939-56 (green orchard dots / vineyard screen; "
                    "data/manual/farmsteads/topo_orchards.geojson): extent before the post-war suburbs. ")
            if kind == "orchard" and not cb.is_empty:
                # planted after Broek's 1931 survey where Broek shows small crops / pasture
                late = shapely.intersection(g, shapely.union_all([br_small, br_past]))
                g = g.difference(late)
                feat(rows, late, layer="topo_1940s", kind=kind, crop="orchard planted after 1931", year_start=1932,
                     year_full=1945, year_end=None, share=1.0, confidence="mapped_1940s", district=dname,
                     county=v["county"], source="usgs_htmc", source_url=MANUAL_URL,
                     note=note + "Not orchard on Broek's 1931 map: planted 1931-48 (ESTIMATED).")
            feat(rows, g, layer="topo_1940s", kind=kind, crop="orchard" if kind == "orchard" else "vineyard",
                 year_start=o0, year_full=o1, year_end=None, share=1.0, confidence="mapped_1940s", district=dname,
                 county=v["county"], source="usgs_htmc", source_url=MANUAL_URL,
                 note=note + "Start years from the district history (ESTIMATED): " + v["note"])
        # 5b. today's vineyards / orchards from OpenStreetMap (real outlines), dated by the district's
        #     modern planting era; where a topo orchard already gives the spot it wins
        for kind, (o0, o1) in (v.get("osm") or {}).items():
            og = osm[(osm["class"] == kind) & osm.geometry.intersects(cell)]
            if not len(og):
                continue
            geom = shapely.union_all(list(og.geometry.buffer(15))).buffer(-15).intersection(cell)
            if kind == "orchard":
                geom = geom.difference(t_orch)
            feat(rows, geom, layer="osm_today", kind=kind, crop="vineyard" if kind == "vineyard" else "orchard",
                 year_start=o0, year_full=o1, year_end=None, share=1.0, confidence="mapped_today", district=dname,
                 county=v["county"], source="osm_overture_" + OVERTURE_RELEASE[:7],
                 source_url="https://www.openstreetmap.org/copyright",
                 note="OpenStreetMap landuse=" + kind + " (Overture " + OVERTURE_RELEASE + "): the extent TODAY; planting "
                      "years from the district history (ESTIMATED): " + v["note"])
        # 6. fallback orchard share where the topos carry no vegetation (1947 East Bay sheets)
        if v.get("fallback_orchard") and v.get("orchard"):
            have = shapely.intersection(cell, t_orch)
            fans = shapely.union_all([by["fan"], by["upper_fan"]])
            if have.area < 0.05 * max(fans.area, 1):
                o0, o1 = v["orchard"]
                feat(rows, fans, layer="district_era", kind="orchard", crop="orchards (extent ESTIMATED)", year_start=o0,
                     year_full=o1, year_end=None, share=v["fallback_orchard"], confidence="estimated",
                     note="No orchard extent on the topos of this district (no vegetation printed): share of the fans "
                          "ESTIMATED. " + v["note"], **base)
    for s in SPECIAL:
        ring = gpd.GeoSeries([Polygon(s["ring"])], crs=4326).to_crs(M).iloc[0]
        g = shapely.intersection(ring, shapely.union_all(list(vf.geometry)))
        feat(rows, g, layer="special", kind=s["kind"], crop=s["crop"], year_start=s["year_start"],
             year_full=s["year_full"], year_end=s["year_end"], share=s["share"], confidence="estimated",
             district=s["id"], county=None, source_url=s["src"], note=s["note"])
    g = gpd.GeoDataFrame(rows, crs=M)
    for c in ("orchard_share", "snapshot_year", "source"):
        if c not in g:
            g[c] = None
    g["source"] = g["source"].fillna("landscape_district_history")
    # Broek's schematic units (georeference +-0.7 km) and the special rings must not spill onto the
    # c.1800 bay / marsh
    g["geometry"] = g.geometry.difference(wet_1800()).simplify(15)
    g = g[~g.geometry.is_empty]
    g["area_ha"] = (g.area / 1e4).round(1)
    g = g[g.area_ha >= 2].reset_index(drop=True)
    cols = ["layer", "kind", "crop", "year_start", "year_full", "year_end", "share", "orchard_share", "district", "county",
            "confidence", "snapshot_year", "area_ha", "source", "source_url", "note", "geometry"]
    g = g[cols]
    write_geojson(g, OUT / "agriculture.geojson", precision=5)
    log("agriculture (km2) by layer / kind:\n" + g.assign(a=g.area_ha / 100).groupby(["layer", "kind"]).a.sum().round(0).to_string())


MANUAL_URL = "https://www.usgs.gov/programs/national-geospatial-program/historical-topographic-maps-preserving-past"

if __name__ == "__main__":
    agriculture()
