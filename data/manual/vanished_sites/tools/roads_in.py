import sys, geopandas as gpd, pandas as pd, shapely
OV='/home/user/bay/data/raw/overture/2026-10-21.0/'
_C={}
def _load(f):
    if f not in _C:
        _C[f]=gpd.read_parquet(OV+f+'.parquet', columns=['id','class','name','geometry'])
    return _C[f]
def roads_in(poly, buf_m=0):
    """map road segments (roads_local + roads_region) intersecting poly (EPSG:4326)"""
    out=[]
    b=poly.bounds
    for f in ['roads_local','roads_region']:
        r=_load(f)
        r=r.iloc[r.sindex.query(poly,predicate='intersects')].copy()
        if len(r)==0: continue
        u=r.to_crs(32610)
        pu=gpd.GeoSeries([poly],crs=4326).to_crs(32610).iloc[0]
        r['len_m']=u.length.round(0); r['inside_m']=u.intersection(pu).length.round(0)
        r['file']=f
        out.append(r)
    return pd.concat(out) if out else None
if __name__=='__main__':
    lu=gpd.read_parquet('dl_ovt/ap_land_use.parquet'); ap=lu[lu.name=='Apple Park'].geometry.iloc[0]
    r=roads_in(ap)
    pd.set_option('display.width',250); pd.set_option('display.max_rows',200)
    print(r[['id','file','class','name','len_m','inside_m']].sort_values('inside_m',ascending=False).to_string())
