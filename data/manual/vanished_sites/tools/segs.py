"""Map road segments (Overture roads_local / roads_region) lying on vanished sites."""
import json, sys, geopandas as gpd, pandas as pd, shapely
from shapely.geometry import shape
sys.path.insert(0,'.')
from roads_in import roads_in
def site_segments(site_id, part_filter=None, min_inside=15):
    fc=json.load(open('sites.geojson'))
    gs=[shape(f['geometry']) for f in fc['features'] if f['properties']['site_id']==site_id and (part_filter is None or part_filter(f['properties']))]
    poly=shapely.union_all(gs).buffer(0)
    r=roads_in(poly)
    if r is None: return None
    r=r[r.inside_m>=min_inside]
    return r[['id','file','class','name','len_m','inside_m']]
if __name__=='__main__':
    pd.set_option('display.width',250); pd.set_option('display.max_rows',500)
    sid=sys.argv[1]
    r=site_segments(sid)
    print(r.sort_values('inside_m',ascending=False).to_string() if r is not None else 'none')
