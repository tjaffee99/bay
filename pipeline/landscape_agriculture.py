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
from shapely.geometry import MultiPoint, Point, Polygon

from common import MANUAL, log
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
    g = g.dissolve("soil", as_index=False)
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
                               orchard=(1916, 1930), fallback_orchard=0.4,
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
    # the five modelled counties' farm belts (+ the south Santa Clara Valley); San Francisco excluded
    region = gpd.GeoSeries([Polygon([(-123.05, 38.32), (-122.45, 38.32), (-122.45, 38.05), (-121.50, 38.10),
                                     (-121.50, 36.95), (-121.75, 36.95), (-122.10, 37.10), (-122.55, 37.20),
                                     (-122.55, 37.62), (-122.50, 37.71), (-122.39, 37.71), (-122.36, 37.76),
                                     (-122.30, 37.83), (-122.55, 37.95), (-123.05, 37.95)])], crs=4326).to_crs(M).iloc[0]
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
    rows = []
    for dname, v in D.items():
        dp = pieces[pieces.district == dname]
        if not len(dp):
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
        bk, byr = v["basin"]
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
    g["geometry"] = g.geometry.simplify(15)
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
